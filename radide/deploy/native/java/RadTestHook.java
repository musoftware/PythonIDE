// RAD IDE - TEST BUILDS ONLY (java_native.py adds this file when RADIDE_NATIVE_TEST_HOOK=1 at build time;
// release builds never contain it). Swing has no native child windows to drive with Win32 messages, so the
// tests send commands on stdin and read "R <result>" lines on stdout:
//   windows | get <obj> <prop> | click <obj> | type <obj> <text> | menu <item> | close <form>
import java.awt.Frame;
import java.awt.event.WindowEvent;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import javax.swing.AbstractButton;
import javax.swing.SwingUtilities;
import javax.swing.text.JTextComponent;

final class RadTestHook {
    private RadTestHook() { }

    static void start() {
        Thread t = new Thread(RadTestHook::loop, "rad-test-hook");
        t.setDaemon(true);
        t.start();
    }

    static void loop() {
        try (BufferedReader in = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8))) {
            String line;
            while ((line = in.readLine()) != null) {
                final String[] p = line.trim().split(" ", 3);
                final String[] out = {""};
                try {
                    SwingUtilities.invokeAndWait(() -> out[0] = run(p));
                } catch (Exception e) {
                    out[0] = "ERROR " + e;
                }
                System.out.println("R " + out[0].replace("\r", "\\r").replace("\n", "\\n"));
                System.out.flush();
            }
        } catch (Exception ignored) {
        }
    }

    static Object comp(String path) {
        Object o = RadSwing.resolve(path);
        return o instanceof RadSwing.Item ? ((RadSwing.Item) o).comp : o;
    }

    static String run(String[] p) {
        switch (p[0]) {
            case "windows": {
                StringBuilder b = new StringBuilder();
                for (Frame f : Frame.getFrames()) if (f.isVisible()) b.append(b.length() > 0 ? "|" : "").append(f.getTitle());
                return b.toString();
            }
            case "get": return RadSwing.getProp(p[1], p.length > 2 ? p[2] : "Text");
            case "click":
            case "menu": {
                Object c = comp(p[1]);
                if (!(c instanceof AbstractButton)) return "ERROR not a button: " + p[1];
                ((AbstractButton) c).doClick(0);
                return "ok";
            }
            case "type": {
                Object c = comp(p[1]);
                if (!(c instanceof JTextComponent)) return "ERROR not a text box: " + p[1];
                ((JTextComponent) c).setText(p.length > 2 ? p[2] : "");
                return "ok";
            }
            case "close": {
                Object f = RadSwing.resolve(p[1]);
                if (!(f instanceof RadSwing.FormBase)) return "ERROR not a form";
                ((RadSwing.FormBase) f).dispatchEvent(new WindowEvent((RadSwing.FormBase) f, WindowEvent.WINDOW_CLOSING));
                return "ok";
            }
            default: return "ERROR unknown command " + p[0];
        }
    }
}
