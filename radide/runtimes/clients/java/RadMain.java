// RAD IDE - entry program for Java projects (GENERATED into _build/<lang> when the program runs - do not edit).
//   java RadMain                    GUI Bridge program: runs the static method <Object>_<Event> for each EVENT
//   java RadMain --worker <Module>  serves the public static methods of class <Module> to the RAD Hub (JSON lines)
import java.lang.reflect.Array;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class RadMain {
    static final String[] CLASSES = { /*CLASSES*/ };

    public static void main(String[] args) {
        if (args.length >= 2 && args[0].equals("--worker")) {
            Rad.init(true);
            System.exit(RadWorker.serve(args[1]));
        }
        Rad.init(false);
        Map<String, Method> handlers = new HashMap<>();
        for (String cn : CLASSES) {
            Class<?> c;
            try {
                c = Class.forName(cn);
            } catch (Throwable t) {
                System.err.println("[java] cannot load class " + cn + ": " + t);
                continue;
            }
            for (Method m : c.getDeclaredMethods()) {
                if (!Modifier.isStatic(m.getModifiers()) || m.getName().indexOf('_') < 0 || m.getParameterCount() > 1)
                    continue;
                m.setAccessible(true);
                handlers.putIfAbsent(m.getName().toLowerCase(), m);
            }
        }
        String line;
        while ((line = Rad.readLine()) != null) {
            if (line.equals("QUIT")) break;
            if (!line.startsWith("EVENT ")) continue;
            String[] p = line.substring(6).split(" ", 3);
            String obj = p[0], ev = p.length > 1 ? p[1] : "";
            try {
                Method m = handlers.get((obj + "_" + ev).toLowerCase());
                if (m != null) {
                    RadEvent e = RadEvent.parse(obj, ev, p.length > 2 ? p[2] : "");
                    if (m.getParameterCount() == 0) m.invoke(null);
                    else m.invoke(null, e);
                    if (e.cancel) Rad.set(obj, "Cancel", true);       // FormClosing: e.cancel = true keeps the form
                }
            } catch (Throwable t) {
                Throwable e = t instanceof InvocationTargetException && t.getCause() != null ? t.getCause() : t;
                System.err.println("Error in " + obj + "_" + ev + ": " + e);
                for (StackTraceElement st : e.getStackTrace()) {
                    if (st.getClassName().startsWith("jdk.internal") || st.getClassName().startsWith("java.lang.reflect")) break;
                    System.err.println("\tat " + st);
                }
            } finally {
                Rad.send("DONE");
            }
        }
        System.exit(0);
    }
}

/** RAD Hub worker: {"id":7,"func":"add","args":[2,3]} -> {"id":7,"result":5} */
class RadWorker {
    static int serve(String module) {
        Class<?> type = null;
        for (String cn : RadMain.CLASSES) {
            if (cn.equalsIgnoreCase(module)) {
                try {
                    type = Class.forName(cn);
                } catch (Throwable t) {
                    System.err.println("[java worker] cannot load class " + cn + ": " + t);
                }
            }
        }
        if (type == null) System.err.println("[java worker] class '" + module + "' was not found in the project");
        String line;
        while ((line = Rad.readLine()) != null) {
            if (line.trim().isEmpty()) continue;
            Object id = null;
            Map<String, Object> reply = new LinkedHashMap<>();
            try {
                Map<?, ?> req = (Map<?, ?>) RadJson.parse(line);
                id = req.get("id");
                String func = String.valueOf(req.get("func"));
                Object a = req.get("args");
                List<?> args = a instanceof List ? (List<?>) a : new ArrayList<>();
                if (type == null) throw new IllegalStateException("class '" + module + "' was not found");
                reply.put("id", id);
                reply.put("result", invoke(type, func, args));
            } catch (Throwable t) {
                Throwable e = t instanceof InvocationTargetException && t.getCause() != null ? t.getCause() : t;
                reply.clear();
                reply.put("id", id);
                reply.put("error", e.getClass().getSimpleName() + ": " + e.getMessage());
            }
            Rad.send(RadJson.stringify(reply));
        }
        return 0;
    }

    static Object invoke(Class<?> type, String func, List<?> args) throws Throwable {
        List<Method> cands = new ArrayList<>();
        for (Method m : type.getMethods())
            if (Modifier.isStatic(m.getModifiers()) && m.getName().equalsIgnoreCase(func)) cands.add(m);
        if (cands.isEmpty()) throw new NoSuchMethodException(type.getSimpleName() + " has no public static method '" + func + "'");
        cands.sort((x, y) -> Integer.compare(x.getParameterCount() == args.size() ? 0 : 1, y.getParameterCount() == args.size() ? 0 : 1));
        Throwable last = null;
        for (Method m : cands) {
            Class<?>[] ps = m.getParameterTypes();
            boolean varargs = m.isVarArgs();
            if (!varargs && ps.length != args.size()) continue;
            if (varargs && args.size() < ps.length - 1) continue;
            try {
                Object[] call = new Object[ps.length];
                for (int k = 0; k < ps.length; k++) {
                    if (varargs && k == ps.length - 1) {
                        call[k] = convert(args.subList(k, args.size()), ps[k]);
                        break;
                    }
                    call[k] = convert(args.get(k), ps[k]);
                }
                return m.invoke(null, call);
            } catch (IllegalArgumentException | ClassCastException e) {
                last = e;
            }
        }
        throw last != null ? last : new IllegalArgumentException(type.getSimpleName() + "." + func + ": wrong number of arguments (" + args.size() + ")");
    }

    static Object convert(Object v, Class<?> t) {
        if (t == Object.class) return v;
        if (v == null) {
            if (t.isPrimitive()) throw new IllegalArgumentException("null for " + t.getSimpleName());
            return null;
        }
        if (t == String.class) return v instanceof String ? v : RadJson.stringify(v);
        if (t == int.class || t == Integer.class) return num(v, t).intValue();
        if (t == long.class || t == Long.class) return num(v, t).longValue();
        if (t == double.class || t == Double.class) return num(v, t).doubleValue();
        if (t == float.class || t == Float.class) return num(v, t).floatValue();
        if (t == short.class || t == Short.class) return num(v, t).shortValue();
        if (t == byte.class || t == Byte.class) return num(v, t).byteValue();
        if (t == boolean.class || t == Boolean.class) {
            if (v instanceof Boolean) return v;
            throw new IllegalArgumentException("expected a boolean, got " + RadJson.stringify(v));
        }
        if (t == char.class || t == Character.class) {
            String s = v.toString();
            if (s.length() != 1) throw new IllegalArgumentException("expected one character");
            return s.charAt(0);
        }
        if (t.isArray() && v instanceof Collection) {
            Collection<?> c = (Collection<?>) v;
            Object arr = Array.newInstance(t.getComponentType(), c.size());
            int k = 0;
            for (Object o : c) Array.set(arr, k++, convert(o, t.getComponentType()));
            return arr;
        }
        if (t.isInstance(v)) return v;
        throw new IllegalArgumentException("cannot convert " + RadJson.stringify(v) + " to " + t.getSimpleName());
    }

    static Number num(Object v, Class<?> t) {
        if (v instanceof Number) return (Number) v;
        throw new IllegalArgumentException("expected a number for " + t.getSimpleName() + ", got " + RadJson.stringify(v));
    }
}
