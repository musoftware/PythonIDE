// RAD IDE - GUI Bridge client for Java (copied into _build/<lang> when the program runs - do not edit this copy).
//
// Form classes extend <Form>Designer, which extends Rad, so these work without a prefix:
//   set(obj, prop, value)   get(obj, prop)   call(obj, method, args...)   msgbox(text)   input(prompt)
//   show(form) / hide(form) end()  radcall("Module.function", args...)  - call any project module (any language)
// and the control fields:  lblOut.setText("Hi");  lstLog.addItem("x");  txtIn.getText()
// Other classes use Rad.msgbox(...), Rad.radcall(...).
import java.io.BufferedReader;
import java.io.FileDescriptor;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.PrintStream;
import java.io.Writer;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

public class Rad {
    private static BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
    private static PrintStream out = System.out;
    private static final Object LOCK = new Object();

    /** Called by the generated main program: UTF-8 stdin/stdout. In worker mode System.out goes to stderr. */
    public static void init(boolean worker) {
        out = new PrintStream(new FileOutputStream(FileDescriptor.out), true, StandardCharsets.UTF_8);
        PrintStream err = new PrintStream(new FileOutputStream(FileDescriptor.err), true, StandardCharsets.UTF_8);
        System.setErr(err);
        System.setOut(worker ? err : out);
    }

    static String readLine() {
        try {
            return in.readLine();
        } catch (IOException e) {
            return null;
        }
    }

    static void send(String line) {
        synchronized (LOCK) {
            out.print(line + "\n");
            out.flush();
        }
    }

    private static String ask(String line) {
        synchronized (LOCK) {
            send(line);
            String answer = readLine();
            if (answer == null) System.exit(0);          // the IDE closed the program
            return answer;
        }
    }

    /** A value as bridge text (True/False for booleans, one line). */
    public static String str(Object v) {
        String s;
        if (v == null) s = "";
        else if (v instanceof Boolean) s = ((Boolean) v) ? "True" : "False";
        else if (v instanceof Double || v instanceof Float) {
            double d = ((Number) v).doubleValue();
            s = d == Math.rint(d) && Math.abs(d) < 1e15 ? Long.toString((long) d) : Double.toString(d);
        } else s = v.toString();
        return s.replace("\r\n", " ").replace('\n', ' ').replace('\r', ' ');
    }

    public static boolean toBool(String s) {
        return s != null && (s.equalsIgnoreCase("true") || s.equals("1") || s.equals("-1"));
    }

    public static double toNumber(String s) {
        try {
            return Double.parseDouble(s.trim());
        } catch (RuntimeException e) {
            return 0;
        }
    }

    public static int toInt(String s) {
        return (int) Math.round(toNumber(s));
    }

    // ------------------------------------------------------------------ GUI
    public static void set(String obj, String prop, Object value) { send("SET " + obj + " " + prop + " " + str(value)); }
    public static String get(String obj, String prop) { return ask("GET " + obj + " " + prop); }
    public static double getNumber(String obj, String prop) { return toNumber(get(obj, prop)); }

    public static String call(String obj, String method, Object... args) {
        StringBuilder b = new StringBuilder("CALL " + obj + " " + method);
        if (args != null && args.length > 0) {
            b.append(' ');
            for (int k = 0; k < args.length; k++) {
                if (k > 0) b.append('\t');
                b.append(str(args[k]));
            }
        }
        return ask(b.toString());
    }

    public static int msgbox(Object text) { return toInt(ask("MSGBOX " + str(text))); }
    public static String input(Object prompt) { return ask("INPUT " + str(prompt)); }
    public static void show(String form) { send("SHOW " + form); }
    public static void hide(String form) { send("HIDE " + form); }

    /** Close the program. */
    public static void end() {
        send("END");
        System.exit(0);
    }

    // ------------------------------------------------------------------ RAD Hub (cross-language calls)
    private static Socket hub;
    private static BufferedReader hubIn;
    private static Writer hubOut;
    private static long hubId;

    /** Call "Module.function" of any project module. Returns null, Boolean, Long, Double, String, List, Map. */
    public static Object radcall(String function, Object... args) {
        synchronized (LOCK) {
            try {
                if (hub == null) {
                    String addr = System.getenv("RAD_HUB");
                    if (addr == null || addr.isEmpty()) throw new RadCallException("RAD Hub is not running (RAD_HUB is not set)");
                    int c = addr.lastIndexOf(':');
                    hub = new Socket(addr.substring(0, c), Integer.parseInt(addr.substring(c + 1)));
                    hub.setTcpNoDelay(true);
                    hubIn = new BufferedReader(new InputStreamReader(hub.getInputStream(), StandardCharsets.UTF_8));
                    hubOut = new OutputStreamWriter(hub.getOutputStream(), StandardCharsets.UTF_8);
                }
                long id = ++hubId;
                Map<String, Object> req = new LinkedHashMap<>();
                req.put("id", id);
                req.put("call", function);
                req.put("args", args == null ? new Object[0] : Arrays.asList(args));
                hubOut.write(RadJson.stringify(req) + "\n");
                hubOut.flush();
                while (true) {
                    String line = hubIn.readLine();
                    if (line == null) throw new RadCallException("RAD Hub closed the connection");
                    Object o = RadJson.parse(line);
                    if (!(o instanceof Map)) continue;
                    Map<?, ?> m = (Map<?, ?>) o;
                    Object rid = m.get("id");
                    if (rid instanceof Number && ((Number) rid).longValue() != id) continue;
                    if (m.get("error") != null) throw new RadCallException(function + ": " + m.get("error"));
                    return m.get("result");
                }
            } catch (IOException e) {
                hub = null;
                throw new RadCallException("RAD Hub: " + e.getMessage());
            }
        }
    }

    /** radcall(...) converted to a number (0 for null). */
    public static double radcallNumber(String function, Object... args) {
        Object r = radcall(function, args);
        return r instanceof Number ? ((Number) r).doubleValue() : r == null ? 0 : toNumber(r.toString());
    }

    // Typed variants used by the generated reference proxies (<Lib>.ref.java, Add Reference).
    /** fixed arguments followed by a varargs array (proxies of variadic library functions). */
    public static Object[] refArgs(Object[] fixed, Object[] rest) {
        if (rest == null) rest = new Object[0];
        Object[] all = Arrays.copyOf(fixed, fixed.length + rest.length);
        System.arraycopy(rest, 0, all, fixed.length, rest.length);
        return all;
    }

    public static double radcallDouble(String function, Object... args) { return radcallNumber(function, args); }

    public static int radcallInt(String function, Object... args) { return (int) Math.round(radcallNumber(function, args)); }

    public static long radcallLong(String function, Object... args) { return Math.round(radcallNumber(function, args)); }

    public static String radcallString(String function, Object... args) {
        Object r = radcall(function, args);
        return r == null ? null : r instanceof String ? (String) r : str(r);
    }

    public static boolean radcallBool(String function, Object... args) {
        Object r = radcall(function, args);
        if (r instanceof Boolean) return (Boolean) r;
        if (r instanceof Number) return ((Number) r).doubleValue() != 0;
        return r != null && toBool(r.toString());
    }

    /** Raised when radcall() gets an error from the hub or from the called function. */
    public static class RadCallException extends RuntimeException {
        public RadCallException(String message) { super(message); }
    }
}
