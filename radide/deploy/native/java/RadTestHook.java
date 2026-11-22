// RAD IDE - TEST BUILDS ONLY (java_native.py adds this file when RADIDE_NATIVE_TEST_HOOK=1 at build time;
// release builds never contain it). Swing has no native child windows to drive with Win32 messages, so the
// tests send commands on stdin and read "R <result>" lines on stdout:
//   windows | get <obj> <prop> | click <obj> | type <obj> <text> | menu <item> | close <form>
//   call <obj> <method> [a|b] | bounds <obj> | showing <obj> | color <obj> | hover <obj> 1|0 | resize <form> <w> <h>
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
            case "call": {           // call <obj> <method>[ <arg>|<arg>...]
                String[] q = p.length > 2 ? p[2].split(" ", 2) : new String[]{""};
                String[] args = q.length > 1 ? q[1].split("\\|", -1) : new String[0];
                return RadSwing.callMethod(p[1], q[0], args);
            }
            case "bounds": {         // x y w h of the laid-out component (in its container)
                Object o = RadSwing.resolve(p[1]);
                if (!(o instanceof RadSwing.Item) || ((RadSwing.Item) o).outer == null) return "ERROR no control " + p[1];
                java.awt.Rectangle r = ((RadSwing.Item) o).outer.getBounds();
                return r.x + " " + r.y + " " + r.width + " " + r.height;
            }
            case "showing": {
                Object o = RadSwing.resolve(p[1]);
                if (!(o instanceof RadSwing.Item) || ((RadSwing.Item) o).outer == null) return "ERROR no control " + p[1];
                return ((RadSwing.Item) o).outer.isShowing() ? "True" : "False";
            }
            case "color": {          // the background colour as #rrggbb (a form: its client area)
                Object o = RadSwing.resolve(p[1]);
                java.awt.Component c = o instanceof RadSwing.FormBase ? ((RadSwing.FormBase) o).getContentPane()
                        : o instanceof RadSwing.Item && ((RadSwing.Item) o).comp instanceof java.awt.Component
                        ? (java.awt.Component) ((RadSwing.Item) o).comp : null;
                if (c == null) return "ERROR no control " + p[1];
                java.awt.Color col = c.getBackground();
                return col == null ? "" : String.format("#%02x%02x%02x", col.getRed(), col.getGreen(), col.getBlue());
            }
            case "mouse": {          // mouse <obj> <x> <y>: a left click as AWT delivers it (pressed, released, clicked)
                Object c = comp(p[1]);
                if (!(c instanceof java.awt.Component)) return "ERROR no control " + p[1];
                java.awt.Component k = (java.awt.Component) c;
                String[] xy = p.length > 2 ? p[2].trim().split("\\s+") : new String[]{"2", "2"};
                int x = Integer.parseInt(xy[0]), y = Integer.parseInt(xy.length > 1 ? xy[1] : xy[0]);
                java.awt.EventQueue q = java.awt.Toolkit.getDefaultToolkit().getSystemEventQueue();
                long t = System.currentTimeMillis();
                int down = java.awt.event.InputEvent.BUTTON1_DOWN_MASK;
                q.postEvent(new java.awt.event.MouseEvent(k, java.awt.event.MouseEvent.MOUSE_ENTERED, t, 0, x, y, 0, false));
                q.postEvent(new java.awt.event.MouseEvent(k, java.awt.event.MouseEvent.MOUSE_PRESSED, t, down, x, y, 1, false,
                        java.awt.event.MouseEvent.BUTTON1));
                q.postEvent(new java.awt.event.MouseEvent(k, java.awt.event.MouseEvent.MOUSE_RELEASED, t + 1, 0, x, y, 1, false,
                        java.awt.event.MouseEvent.BUTTON1));
                q.postEvent(new java.awt.event.MouseEvent(k, java.awt.event.MouseEvent.MOUSE_CLICKED, t + 1, 0, x, y, 1, false,
                        java.awt.event.MouseEvent.BUTTON1));
                return "ok";
            }
            case "hover": {          // hover <obj> 1|0: the mouse enters / leaves the control
                Object c = comp(p[1]);
                if (!(c instanceof java.awt.Component)) return "ERROR no control " + p[1];
                java.awt.Component k = (java.awt.Component) c;
                boolean in = p.length < 3 || !p[2].trim().equals("0");
                k.dispatchEvent(new java.awt.event.MouseEvent(k, in ? java.awt.event.MouseEvent.MOUSE_ENTERED
                        : java.awt.event.MouseEvent.MOUSE_EXITED, System.currentTimeMillis(), 0, 2, 2, 0, false));
                return "ok";
            }
            case "resize": {         // resize <form> <clientW> <clientH>
                Object f = RadSwing.resolve(p[1]);
                if (!(f instanceof RadSwing.FormBase)) return "ERROR not a form";
                RadSwing.FormBase fb = (RadSwing.FormBase) f;
                String[] wh = p.length > 2 ? p[2].trim().split("\\s+") : new String[0];
                if (wh.length < 2) return "ERROR resize <form> <w> <h>";
                java.awt.Container cp = fb.getContentPane();
                int dw = fb.getWidth() - cp.getWidth(), dh = fb.getHeight() - cp.getHeight();
                fb.setSize(Integer.parseInt(wh[0]) + dw, Integer.parseInt(wh[1]) + dh);
                fb.validate();
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
