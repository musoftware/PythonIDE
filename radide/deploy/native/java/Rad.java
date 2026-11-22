// RAD IDE - native build of a Java project (radide/deploy/native/java_native.py): the GUI Bridge client API
// (set/get/call/msgbox/input/show/hide/end/radcall ...) on real Swing forms (RadSwing) - no IDE, no Python.
// Form classes extend <Form>Designer, which extends Rad, so these work without a prefix, like in the IDE.
import java.lang.reflect.Array;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;

public class Rad {
    /** Kept for compatibility with the bridge client (nothing to initialise in a native program). */
    public static void init(boolean worker) { }

    static String readLine() { return null; }

    static void send(String line) { }

    /** A value as text (True/False for booleans, whole doubles without ".0"). */
    public static String str(Object v) {
        if (v == null) return "";
        if (v instanceof Boolean) return ((Boolean) v) ? "True" : "False";
        if (v instanceof Double || v instanceof Float) {
            double d = ((Number) v).doubleValue();
            return d == Math.rint(d) && Math.abs(d) < 1e15 ? Long.toString((long) d) : Double.toString(d);
        }
        return v.toString();
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
    public static void set(String obj, String prop, Object value) { RadSwing.setProp(obj, prop, str(value)); }
    public static String get(String obj, String prop) { return RadSwing.getProp(obj, prop); }
    public static double getNumber(String obj, String prop) { return toNumber(get(obj, prop)); }

    public static String call(String obj, String method, Object... args) {
        String[] a = new String[args == null ? 0 : args.length];
        for (int k = 0; k < a.length; k++) a[k] = str(args[k]);
        return RadSwing.callMethod(obj, method, a);
    }

    public static int msgbox(Object text) { return RadSwing.msgbox(str(text)); }
    public static String input(Object prompt) { return RadSwing.input(str(prompt)); }
    public static void show(String form) { RadSwing.showForm(form, true); }
    public static void hide(String form) { RadSwing.showForm(form, false); }

    /** Close the program. */
    public static void end() { RadSwing.end(); }

    // ------------------------------------------------------------------ project modules
    /** Call "Module.function": a public static method of a class of this program. */
    public static Object radcall(String function, Object... args) {
        if (args == null) args = new Object[0];
        int dot = function == null ? -1 : function.lastIndexOf('.');
        if (dot <= 0) throw new RadCallException("radcall: use \"Module.function\" (got '" + function + "')");
        String cls = function.substring(0, dot), fn = function.substring(dot + 1);
        Class<?> type = RadSwing.classFor(cls);
        if (type == null) throw new RadCallException(function + ": class '" + cls + "' is not part of this program");
        List<Method> cands = new ArrayList<>();
        for (Method m : type.getMethods())
            if (Modifier.isStatic(m.getModifiers()) && m.getName().equalsIgnoreCase(fn)) cands.add(m);
        if (cands.isEmpty()) throw new RadCallException(function + ": " + type.getSimpleName() + " has no public static method '" + fn + "'");
        final int n = args.length;
        cands.sort((x, y) -> Integer.compare(x.getParameterCount() == n ? 0 : 1, y.getParameterCount() == n ? 0 : 1));
        Throwable last = null;
        for (Method m : cands) {
            Class<?>[] ps = m.getParameterTypes();
            boolean varargs = m.isVarArgs();
            if (!varargs && ps.length != n) continue;
            if (varargs && n < ps.length - 1) continue;
            try {
                Object[] call = new Object[ps.length];
                for (int k = 0; k < ps.length; k++) {
                    if (varargs && k == ps.length - 1) {
                        call[k] = convert(Arrays.asList(args).subList(k, n), ps[k]);
                        break;
                    }
                    call[k] = convert(args[k], ps[k]);
                }
                return m.invoke(null, call);
            } catch (InvocationTargetException e) {
                Throwable c = e.getCause() != null ? e.getCause() : e;
                throw new RadCallException(function + ": " + c);
            } catch (IllegalArgumentException | ClassCastException | IllegalAccessException e) {
                last = e;
            }
        }
        throw new RadCallException(function + ": " + (last != null ? last.getMessage() : "wrong number of arguments (" + n + ")"));
    }

    static Object convert(Object v, Class<?> t) {
        if (v == null || t == Object.class || t.isInstance(v)) return v;
        if (t == String.class) return str(v);
        double d = v instanceof Number ? ((Number) v).doubleValue() : toNumber(str(v));
        if (t == int.class || t == Integer.class) return (int) Math.round(d);
        if (t == long.class || t == Long.class) return Math.round(d);
        if (t == double.class || t == Double.class) return d;
        if (t == float.class || t == Float.class) return (float) d;
        if (t == short.class || t == Short.class) return (short) Math.round(d);
        if (t == byte.class || t == Byte.class) return (byte) Math.round(d);
        if (t == boolean.class || t == Boolean.class) return v instanceof Boolean ? v : toBool(str(v));
        if (t == char.class || t == Character.class) return str(v).isEmpty() ? '\0' : str(v).charAt(0);
        if (t.isArray() && v instanceof Collection) {
            Collection<?> c = (Collection<?>) v;
            Object arr = Array.newInstance(t.getComponentType(), c.size());
            int k = 0;
            for (Object o : c) Array.set(arr, k++, convert(o, t.getComponentType()));
            return arr;
        }
        throw new IllegalArgumentException("cannot convert " + str(v) + " to " + t.getSimpleName());
    }

    /** radcall(...) converted to a number (0 for null). */
    public static double radcallNumber(String function, Object... args) {
        Object r = radcall(function, args);
        return r instanceof Number ? ((Number) r).doubleValue() : r == null ? 0 : toNumber(r.toString());
    }

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

    /** Raised when radcall() cannot find or run the called function. */
    public static class RadCallException extends RuntimeException {
        public RadCallException(String message) { super(message); }
    }
}
