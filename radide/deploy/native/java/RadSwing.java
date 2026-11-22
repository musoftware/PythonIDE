// RAD IDE - native Swing runtime for published Java programs (radide/deploy/native/java_native.py).
// The forms are real Swing frames generated from the .form files (RadForm_<Name>.initComponents); this class
// implements the VB-style property protocol of the GUI Bridge (Text, Value, ListIndex, AddItem ...) directly on the
// components, finds the handlers (static methods <Control>_<Event> of the project's classes) and wires the events.
import java.awt.*;
import java.awt.event.*;
import java.awt.font.TextAttribute;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.List;
import java.util.function.Supplier;
import javax.swing.*;
import javax.swing.border.BevelBorder;
import javax.swing.border.TitledBorder;
import javax.swing.event.*;
import javax.swing.text.JTextComponent;

public final class RadSwing {
    static String title = "";
    static final Map<String, Method> handlers = new HashMap<>();
    static final Map<String, Supplier<FormBase>> factories = new LinkedHashMap<>();
    static final Map<String, FormBase> forms = new HashMap<>();
    static final Map<String, Class<?>> classes = new HashMap<>();
    static FormBase startup;
    static boolean ending;
    /** optional observer (test builds): every fired event name */
    public static java.util.function.Consumer<String> trace;

    private RadSwing() { }

    // ================================================================== program
    public static void init(String appTitle, String... classNames) {
        title = appTitle;
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception ignored) {
        }
        for (String cn : classNames) {
            Class<?> c;
            try {
                c = Class.forName(cn);
            } catch (Throwable t) {
                System.err.println("[rad] cannot load class " + cn + ": " + t);
                continue;
            }
            classes.put(cn.toLowerCase(Locale.ROOT), c);
            for (Method m : c.getDeclaredMethods()) {
                if (!Modifier.isStatic(m.getModifiers()) || m.getName().indexOf('_') < 0 || m.getParameterCount() > 1) continue;
                if (m.getParameterCount() == 1 && m.getParameterTypes()[0] != RadEvent.class) continue;
                m.setAccessible(true);
                handlers.putIfAbsent(m.getName().toLowerCase(Locale.ROOT), m);
            }
        }
    }

    static Class<?> classFor(String name) {
        Class<?> c = classes.get(name.toLowerCase(Locale.ROOT));
        if (c != null) return c;
        try {
            return Class.forName(name);
        } catch (Throwable t) {
            return null;
        }
    }

    public static void register(String name, Supplier<FormBase> make) { factories.put(name.toLowerCase(Locale.ROOT), make); }

    public static void run(String startupForm) {
        SwingUtilities.invokeLater(() -> {
            startup = getForm(startupForm);
            if (startup == null) {
                System.err.println("[rad] no form " + startupForm);
                System.exit(1);
            }
            startup.showForm();
        });
    }

    static FormBase getForm(String name) {
        String key = name.toLowerCase(Locale.ROOT);
        FormBase f = forms.get(key);
        if (f != null) return f;
        Supplier<FormBase> make = factories.get(key);
        if (make == null) return null;
        f = make.get();
        forms.put(key, f);
        return f;
    }

    static boolean has(String handler) { return handlers.containsKey(handler.toLowerCase(Locale.ROOT)); }

    static void fire(String owner, String ev, RadEvent e) {
        String name = owner + "_" + ev;
        if (trace != null) trace.accept(name);
        Method m = handlers.get(name.toLowerCase(Locale.ROOT));
        if (m == null) return;
        if (e == null) e = RadEvent.parse(owner, ev, "");
        try {
            if (m.getParameterCount() == 0) m.invoke(null);
            else m.invoke(null, e);
        } catch (InvocationTargetException ex) {
            report(name, ex.getCause() != null ? ex.getCause() : ex);
        } catch (Throwable ex) {
            report(name, ex);
        }
    }

    static void report(String where, Throwable ex) {
        String msg = (where.isEmpty() ? "" : "Error in " + where + ": ") + ex;
        System.err.println(msg);
        JOptionPane.showMessageDialog(owner(), msg, title.isEmpty() ? "Error" : title, JOptionPane.ERROR_MESSAGE);
    }

    public static void end() {
        ending = true;
        System.exit(0);
    }

    static Component owner() {
        Window w = KeyboardFocusManager.getCurrentKeyboardFocusManager().getActiveWindow();
        return w != null ? w : startup;
    }

    public static int msgbox(String text) {
        onEdt(() -> {
            JOptionPane.showMessageDialog(owner(), text, title, JOptionPane.PLAIN_MESSAGE);
            return null;
        });
        return 1;
    }

    public static String input(String prompt) {
        return onEdt(() -> {
            Object r = JOptionPane.showInputDialog(owner(), prompt, title, JOptionPane.PLAIN_MESSAGE);
            return r == null ? "" : r.toString();
        });
    }

    public static void showForm(String path, boolean show) {
        onEdt(() -> {
            Object o = resolve(path);
            if (o instanceof FormBase) {
                if (show) ((FormBase) o).showForm();
                else ((FormBase) o).setVisible(false);
            } else if (o != null) {
                set((Item) o, "visible", show ? "True" : "False");
            }
            return null;
        });
    }

    static <T> T onEdt(Supplier<T> f) {
        if (SwingUtilities.isEventDispatchThread()) return f.get();
        final Object[] box = new Object[1];
        try {
            SwingUtilities.invokeAndWait(() -> box[0] = f.get());
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
        @SuppressWarnings("unchecked") T t = (T) box[0];
        return t;
    }

    // ================================================================== objects
    /** A control / menu item / timer / dialog of a form. */
    public static final class Item {
        final String name, type;
        final Object comp;        // the component the properties work on (JTextArea, JList ...)
        final JComponent outer;   // the component that is laid out (the JScrollPane of a list ...)
        boolean shown = true;
        String tag = "";
        String kind = "";         // dialogs: OpenFileDialog ...
        final Map<String, String> data = new HashMap<>();
        boolean muteText;
        String lastText;

        Item(String name, String type, Object comp, JComponent outer) {
            this.name = name;
            this.type = type;
            this.comp = comp;
            this.outer = outer;
        }
    }

    /** "Form1", "Form1.lblOut" or "lblOut" (searched in the forms). */
    static Object resolve(String path) {
        if (path == null || path.isEmpty()) return null;
        String[] parts = path.split("\\.");
        String key = parts[0].toLowerCase(Locale.ROOT);
        if (factories.containsKey(key)) {
            FormBase f = getForm(parts[0]);
            if (parts.length == 1) return f;
            return f == null ? null : f.items.get(parts[1]);
        }
        for (FormBase f : forms.values()) {
            Item it = f.items.get(parts[0]);
            if (it != null) return it;
        }
        for (String n : new ArrayList<>(factories.keySet())) {
            FormBase f = getForm(n);
            Item it = f == null ? null : f.items.get(parts[0]);
            if (it != null) return it;
        }
        return null;
    }

    public static String getProp(String path, String prop) {
        return onEdt(() -> {
            Object o = resolve(path);
            if (o == null) {
                warn("unknown object '" + path + "'");
                return "";
            }
            try {
                String p = prop.trim().toLowerCase(Locale.ROOT);
                return o instanceof FormBase ? ((FormBase) o).getProp(p) : get((Item) o, p);
            } catch (RuntimeException e) {
                warn(path + "." + prop + ": " + e);
                return "";
            }
        });
    }

    public static void setProp(String path, String prop, String value) {
        onEdt(() -> {
            Object o = resolve(path);
            if (o == null) {
                warn("unknown object '" + path + "'");
                return null;
            }
            try {
                String p = prop.trim().toLowerCase(Locale.ROOT);
                if (o instanceof FormBase) ((FormBase) o).setProp(p, value == null ? "" : value);
                else set((Item) o, p, value == null ? "" : value);
            } catch (RuntimeException e) {
                warn(path + "." + prop + ": " + e);
            }
            return null;
        });
    }

    public static String callMethod(String path, String method, String[] args) {
        return onEdt(() -> {
            Object o = resolve(path);
            if (o == null) {
                warn("unknown object '" + path + "'");
                return "";
            }
            try {
                String m = method.trim().toLowerCase(Locale.ROOT);
                return o instanceof FormBase ? ((FormBase) o).call(m, args) : call((Item) o, m, args);
            } catch (RuntimeException e) {
                warn(path + "." + method + ": " + e);
                return "";
            }
        });
    }

    static void warn(String msg) { System.err.println("[rad] " + msg); }

    static String b(boolean v) { return v ? "True" : "False"; }

    static String n(double d) { return d == Math.rint(d) && Math.abs(d) < 1e15 ? Long.toString((long) d) : Double.toString(d); }

    static Color toColor(String v) {
        v = v == null ? "" : v.trim();
        if (v.isEmpty()) return null;
        try {
            if (v.startsWith("#")) return Color.decode(v);
            long x = (long) Double.parseDouble(v);
            return new Color((int) (x & 0xFF), (int) ((x >> 8) & 0xFF), (int) ((x >> 16) & 0xFF));
        } catch (RuntimeException e) {
            return null;
        }
    }

    static String fromColor(Color c) {
        return c == null ? "0" : Long.toString(((long) c.getBlue() << 16) | ((long) c.getGreen() << 8) | c.getRed());
    }

    static String windowsText(String s) { return s.replace("\r\n", "\n").replace("\n", "\r\n"); }

    @SuppressWarnings("unchecked")
    static String get(Item it, String p) {
        Object c = it.comp;
        switch (it.type) {
            case "Timer": {
                javax.swing.Timer t = (javax.swing.Timer) c;
                if (p.equals("interval")) return Integer.toString(t.getDelay());
                if (p.equals("enabled")) return b(t.isRunning());
                if (p.equals("name")) return it.name;
                return "";
            }
            case "Dialog":
                return it.data.getOrDefault(p, "");
            case "MenuItem": {
                JMenuItem m = (JMenuItem) c;
                if (p.equals("text") || p.equals("caption")) return m.getText();
                if (p.equals("enabled")) return b(m.isEnabled());
                if (p.equals("visible")) return b(m.isVisible());
                if (p.equals("checked") || p.equals("value")) return b(m.isSelected());
                if (p.equals("name")) return it.name;
                return "";
            }
            default:
                break;
        }
        JComponent jc = (JComponent) c;
        switch (p) {
            case "name": return it.name;
            case "tag": return it.tag;
            case "caption":
            case "text": return text(it);
            case "value":
                if (c instanceof JCheckBox) return ((JCheckBox) c).isSelected() ? "1" : "0";
                if (c instanceof JRadioButton) return b(((JRadioButton) c).isSelected());
                if (c instanceof JSpinner && it.type.equals("DateTimePicker"))
                    return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format((Date) ((JSpinner) c).getValue());
                if (c instanceof JSpinner) return n(((Number) ((JSpinner) c).getValue()).doubleValue());
                if (c instanceof JSlider) return Integer.toString(((JSlider) c).getValue());
                if (c instanceof JProgressBar) return Integer.toString(((JProgressBar) c).getValue());
                if (c instanceof JTabbedPane) return Integer.toString(((JTabbedPane) c).getSelectedIndex());
                return text(it);
            case "checked":
                return b(c instanceof AbstractButton && ((AbstractButton) c).isSelected());
            case "min":
            case "minimum":
                if (c instanceof JSpinner) return n(((Number) ((SpinnerNumberModel) ((JSpinner) c).getModel()).getMinimum()).doubleValue());
                if (c instanceof JSlider) return Integer.toString(((JSlider) c).getMinimum());
                if (c instanceof JProgressBar) return Integer.toString(((JProgressBar) c).getMinimum());
                return "0";
            case "max":
            case "maximum":
                if (c instanceof JSpinner) return n(((Number) ((SpinnerNumberModel) ((JSpinner) c).getModel()).getMaximum()).doubleValue());
                if (c instanceof JSlider) return Integer.toString(((JSlider) c).getMaximum());
                if (c instanceof JProgressBar) return Integer.toString(((JProgressBar) c).getMaximum());
                return "0";
            case "left": return Integer.toString(it.outer.getX());
            case "top": return Integer.toString(it.outer.getY());
            case "width": return Integer.toString(it.outer.getWidth());
            case "height": return Integer.toString(it.outer.getHeight());
            case "enabled": return b(jc.isEnabled());
            case "visible": return b(it.shown);
            case "backcolor": return fromColor(jc.getBackground());
            case "forecolor": return fromColor(jc.getForeground());
            case "listcount":
                if (c instanceof JList) return Integer.toString(((JList<?>) c).getModel().getSize());
                if (c instanceof JComboBox) return Integer.toString(((JComboBox<?>) c).getItemCount());
                if (c instanceof JTabbedPane) return Integer.toString(((JTabbedPane) c).getTabCount());
                return "0";
            case "listindex":
            case "selectedindex":
            case "tab":
                if (c instanceof JList) return Integer.toString(((JList<?>) c).getSelectedIndex());
                if (c instanceof JComboBox) return Integer.toString(((JComboBox<?>) c).getSelectedIndex());
                if (c instanceof JTabbedPane) return Integer.toString(((JTabbedPane) c).getSelectedIndex());
                return "-1";
            case "newindex": return Integer.toString(Rad.toInt(get(it, "listcount")) - 1);
            case "fontsize":
            case "size": return n(Math.round(jc.getFont().getSize2D() * 72f / 96f * 4) / 4.0);
            case "fontbold":
            case "bold": return b(jc.getFont().isBold());
            case "fontitalic":
            case "italic": return b(jc.getFont().isItalic());
            case "fontname": return jc.getFont().getFamily();
            case "tooltiptext": return jc.getToolTipText() == null ? "" : jc.getToolTipText();
            case "multiline": return b(c instanceof JTextArea);
            case "locked":
            case "readonly": return b(c instanceof JTextComponent && !((JTextComponent) c).isEditable());
            case "selstart": return c instanceof JTextComponent ? Integer.toString(((JTextComponent) c).getSelectionStart()) : "0";
            case "sellength":
                return c instanceof JTextComponent ? Integer.toString(((JTextComponent) c).getSelectionEnd() - ((JTextComponent) c).getSelectionStart()) : "0";
            case "seltext": return c instanceof JTextComponent && ((JTextComponent) c).getSelectedText() != null ? ((JTextComponent) c).getSelectedText() : "";
            default:
                warn("Object doesn't support property '" + p + "' (" + it.name + ")");
                return "";
        }
    }

    static String text(Item it) {
        Object c = it.comp;
        if (c instanceof JTextArea) return windowsText(((JTextArea) c).getText());
        if (c instanceof JTextComponent) return ((JTextComponent) c).getText();
        if (c instanceof AbstractButton) return ((AbstractButton) c).getText();
        if (c instanceof JLabel) return it.data.containsKey("text") ? it.data.get("text") : ((JLabel) c).getText();
        if (c instanceof JComboBox) {
            JComboBox<?> cb = (JComboBox<?>) c;
            if (cb.isEditable()) return String.valueOf(cb.getEditor().getItem() == null ? "" : cb.getEditor().getItem());
            return cb.getSelectedItem() == null ? "" : cb.getSelectedItem().toString();
        }
        if (c instanceof JList) {
            Object v = ((JList<?>) c).getSelectedValue();
            return v == null ? "" : v.toString();
        }
        if (c instanceof JTabbedPane) {
            JTabbedPane t = (JTabbedPane) c;
            return t.getSelectedIndex() >= 0 ? t.getTitleAt(t.getSelectedIndex()) : "";
        }
        if (c instanceof JPanel && ((JPanel) c).getBorder() instanceof TitledBorder) return ((TitledBorder) ((JPanel) c).getBorder()).getTitle();
        if (c instanceof JSpinner || c instanceof JSlider || c instanceof JProgressBar) return get(it, "value");
        return "";
    }

    static void setText(Item it, String v) {
        Object c = it.comp;
        if (c instanceof JTextComponent) {
            JTextComponent t = (JTextComponent) c;
            String nv = c instanceof JTextArea ? v.replace("\r\n", "\n") : v;
            if (nv.equals(t.getText())) return;
            it.muteText = true;
            try {
                t.setText(nv);
            } finally {
                it.muteText = false;
            }
            textChanged(it);
        } else if (c instanceof AbstractButton) ((AbstractButton) c).setText(v);
        else if (c instanceof JLabel) {
            if (it.type.equals("LinkLabel")) {
                it.data.put("text", v);
                ((JLabel) c).setText(v);
            } else ((JLabel) c).setText(v);
        } else if (c instanceof JComboBox) {
            JComboBox<?> cb = (JComboBox<?>) c;
            if (cb.isEditable()) cb.getEditor().setItem(v);
            else for (int i = 0; i < cb.getItemCount(); i++) if (String.valueOf(cb.getItemAt(i)).equals(v)) cb.setSelectedIndex(i);
        } else if (c instanceof JList) {
            JList<?> l = (JList<?>) c;
            for (int i = 0; i < l.getModel().getSize(); i++) if (String.valueOf(l.getModel().getElementAt(i)).equals(v)) l.setSelectedIndex(i);
        } else if (c instanceof JPanel && ((JPanel) c).getBorder() instanceof TitledBorder) {
            ((TitledBorder) ((JPanel) c).getBorder()).setTitle(v);
            ((JPanel) c).repaint();
        } else if (c instanceof JSpinner || c instanceof JSlider || c instanceof JProgressBar) set(it, "value", v);
    }

    /** TextChanged of a text component, once per change (typing or a program write). */
    static void textChanged(Item it) {
        String now = ((JTextComponent) it.comp).getText();
        if (now.equals(it.lastText)) return;
        it.lastText = now;
        if (it.data.containsKey("owner")) fire(it.data.get("owner"), "TextChanged", null);
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    static void set(Item it, String p, String v) {
        Object c = it.comp;
        switch (it.type) {
            case "Timer": {
                javax.swing.Timer t = (javax.swing.Timer) c;
                if (p.equals("interval")) {
                    t.setDelay(Math.max(1, Rad.toInt(v)));
                    t.setInitialDelay(Math.max(1, Rad.toInt(v)));
                    if (t.isRunning()) t.restart();
                } else if (p.equals("enabled")) {
                    if (Rad.toBool(v)) {
                        if (!t.isRunning()) t.start();
                    } else t.stop();
                }
                return;
            }
            case "Dialog":
                it.data.put(p, v);
                return;
            case "MenuItem": {
                JMenuItem m = (JMenuItem) c;
                if (p.equals("text") || p.equals("caption")) m.setText(v);
                else if (p.equals("enabled")) m.setEnabled(Rad.toBool(v));
                else if (p.equals("visible")) m.setVisible(Rad.toBool(v));
                else if (p.equals("checked") || p.equals("value")) m.setSelected(Rad.toBool(v));
                return;
            }
            default:
                break;
        }
        JComponent jc = (JComponent) c;
        switch (p) {
            case "tag": it.tag = v; return;
            case "caption":
            case "text": setText(it, v); return;
            case "value":
                if (c instanceof JCheckBox) ((JCheckBox) c).setSelected(Rad.toBool(v) || v.trim().equals("1"));
                else if (c instanceof JRadioButton) {
                    if (Rad.toBool(v)) ((JRadioButton) c).setSelected(true);
                } else if (c instanceof JSpinner && it.type.equals("DateTimePicker")) {
                    try {
                        ((JSpinner) c).setValue(new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").parse(v.length() == 10 ? v + " 00:00:00" : v));
                    } catch (Exception ignored) {
                    }
                } else if (c instanceof JSpinner) {
                    SpinnerNumberModel m = (SpinnerNumberModel) ((JSpinner) c).getModel();
                    double lo = ((Number) m.getMinimum()).doubleValue(), hi = ((Number) m.getMaximum()).doubleValue();
                    m.setValue((int) Math.max(lo, Math.min(hi, Rad.toNumber(v))));
                } else if (c instanceof JSlider) ((JSlider) c).setValue(Rad.toInt(v));
                else if (c instanceof JProgressBar) ((JProgressBar) c).setValue(Rad.toInt(v));
                else if (c instanceof JTabbedPane) set(it, "selectedindex", v);
                else setText(it, v);
                return;
            case "checked":
                if (c instanceof AbstractButton) ((AbstractButton) c).setSelected(Rad.toBool(v));
                return;
            case "min":
            case "minimum":
                if (c instanceof JSpinner) ((SpinnerNumberModel) ((JSpinner) c).getModel()).setMinimum(Rad.toInt(v));
                else if (c instanceof JSlider) ((JSlider) c).setMinimum(Rad.toInt(v));
                else if (c instanceof JProgressBar) ((JProgressBar) c).setMinimum(Rad.toInt(v));
                return;
            case "max":
            case "maximum":
                if (c instanceof JSpinner) ((SpinnerNumberModel) ((JSpinner) c).getModel()).setMaximum(Rad.toInt(v));
                else if (c instanceof JSlider) ((JSlider) c).setMaximum(Rad.toInt(v));
                else if (c instanceof JProgressBar) ((JProgressBar) c).setMaximum(Rad.toInt(v));
                return;
            case "left":
            case "top":
            case "width":
            case "height": {
                Rectangle r = it.outer.getBounds();
                int x = Rad.toInt(v);
                if (p.equals("left")) r.x = x;
                else if (p.equals("top")) r.y = x;
                else if (p.equals("width")) r.width = x;
                else r.height = x;
                RadLayout.fix(it.outer, r);
                return;
            }
            case "enabled":
                jc.setEnabled(Rad.toBool(v));
                if (it.outer != jc) it.outer.setEnabled(Rad.toBool(v));
                return;
            case "visible":
                it.shown = Rad.toBool(v);
                it.outer.setVisible(it.shown);
                return;
            case "backcolor": {
                Color col = toColor(v);
                jc.setBackground(col);
                jc.setOpaque(col != null || !(c instanceof JLabel));
                jc.repaint();
                return;
            }
            case "forecolor": jc.setForeground(toColor(v)); return;
            case "listindex":
            case "selectedindex":
            case "tab": {
                int i = Rad.toInt(v);
                if (c instanceof JList) {
                    JList<?> l = (JList<?>) c;
                    if (i < 0) l.clearSelection();
                    else if (i < l.getModel().getSize()) {
                        l.setSelectedIndex(i);
                        l.ensureIndexIsVisible(i);
                    }
                } else if (c instanceof JComboBox) {
                    JComboBox<?> cb = (JComboBox<?>) c;
                    cb.setSelectedIndex(i < cb.getItemCount() ? i : -1);
                } else if (c instanceof JTabbedPane && i >= 0 && i < ((JTabbedPane) c).getTabCount()) ((JTabbedPane) c).setSelectedIndex(i);
                return;
            }
            case "fontsize":
            case "size": jc.setFont(jc.getFont().deriveFont((float) (Rad.toNumber(v) * 96 / 72))); return;
            case "fontname": jc.setFont(new Font(v, jc.getFont().getStyle(), jc.getFont().getSize())); return;
            case "fontbold":
            case "bold": jc.setFont(jc.getFont().deriveFont(Rad.toBool(v) ? jc.getFont().getStyle() | Font.BOLD : jc.getFont().getStyle() & ~Font.BOLD)); return;
            case "fontitalic":
            case "italic": jc.setFont(jc.getFont().deriveFont(Rad.toBool(v) ? jc.getFont().getStyle() | Font.ITALIC : jc.getFont().getStyle() & ~Font.ITALIC)); return;
            case "tooltiptext": jc.setToolTipText(v.isEmpty() ? null : v); return;
            case "locked":
            case "readonly": if (c instanceof JTextComponent) ((JTextComponent) c).setEditable(!Rad.toBool(v)); return;
            case "selstart": if (c instanceof JTextComponent) ((JTextComponent) c).setCaretPosition(Math.min(Rad.toInt(v), ((JTextComponent) c).getText().length())); return;
            case "seltext": if (c instanceof JTextComponent) ((JTextComponent) c).replaceSelection(v); return;
            case "picture":
            case "image":
                if (c instanceof JLabel) ((JLabel) c).setIcon(v.isEmpty() ? null : new ImageIcon(res(v)));
                return;
            case "sellength": case "tabindex": case "tabstop": case "mousepointer": case "default": case "cancel":
            case "appearance": case "borderstyle": case "sorted": case "alignment": case "autosize": case "wordwrap":
                return;               // accepted but not applicable (like the GUI Bridge)
            default:
                warn("Object doesn't support property '" + p + "' (" + it.name + ")");
        }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    static String call(Item it, String m, String[] a) {
        Object c = it.comp;
        String a0 = a.length > 0 ? a[0] : "";
        if (it.type.equals("Timer")) {
            javax.swing.Timer t = (javax.swing.Timer) c;
            if (m.equals("start")) t.start();
            else if (m.equals("stop")) t.stop();
            else return get(it, m);
            return "";
        }
        if (it.type.equals("Dialog")) {
            if (m.equals("showdialog") || m.equals("show") || m.equals("showopen") || m.equals("showsave")) return showDialog(it);
            return get(it, m);
        }
        if (it.type.equals("MenuItem")) {
            if (m.equals("performclick") || m.equals("click")) ((JMenuItem) c).doClick(0);
            else return get(it, m);
            return "";
        }
        switch (m) {
            case "additem":
                if (c instanceof JList) {
                    DefaultListModel<String> model = (DefaultListModel<String>) ((JList) c).getModel();
                    if (a.length > 1) model.add(Rad.toInt(a[1]), a0);
                    else model.addElement(a0);
                } else if (c instanceof JComboBox) {
                    JComboBox<String> cb = (JComboBox<String>) c;
                    if (a.length > 1) cb.insertItemAt(a0, Rad.toInt(a[1]));
                    else cb.addItem(a0);
                }
                return "";
            case "removeitem":
                if (c instanceof JList) ((DefaultListModel<?>) ((JList) c).getModel()).remove(Rad.toInt(a0));
                else if (c instanceof JComboBox) ((JComboBox<?>) c).removeItemAt(Rad.toInt(a0));
                return "";
            case "clear":
                if (c instanceof JList) ((DefaultListModel<?>) ((JList) c).getModel()).clear();
                else if (c instanceof JComboBox) ((JComboBox<?>) c).removeAllItems();
                else if (c instanceof JTextComponent) setText(it, "");
                return "";
            case "list":
                if (c instanceof JList) return String.valueOf(((JList) c).getModel().getElementAt(Rad.toInt(a0)));
                if (c instanceof JComboBox) return String.valueOf(((JComboBox) c).getItemAt(Rad.toInt(a0)));
                return "";
            case "setfocus": ((JComponent) c).requestFocusInWindow(); return "";
            case "refresh": ((JComponent) c).repaint(); return "";
            case "move": {
                String[] keys = {"left", "top", "width", "height"};
                for (int i = 0; i < a.length && i < 4; i++) if (!a[i].isEmpty()) set(it, keys[i], a[i]);
                return "";
            }
            case "zorder": {
                Container parent = it.outer.getParent();
                if (parent != null) parent.setComponentZOrder(it.outer, a.length == 0 || Rad.toInt(a0) == 0 ? 0 : parent.getComponentCount() - 1);
                if (parent != null) parent.repaint();
                return "";
            }
            case "show": set(it, "visible", "True"); return "";
            case "hide": set(it, "visible", "False"); return "";
            case "performclick":
            case "click":
                if (c instanceof AbstractButton) ((AbstractButton) c).doClick(0);
                return "";
            case "animate":
                return "";
            default:
                return get(it, m);
        }
    }

    static String showDialog(Item it) {
        Component owner = owner();
        switch (it.kind) {
            case "OpenFileDialog":
            case "SaveFileDialog":
            case "FolderBrowserDialog": {
                JFileChooser fc = new JFileChooser();
                String dir = it.data.getOrDefault(it.kind.equals("FolderBrowserDialog") ? "selectedpath" : "initialdirectory", "");
                if (!dir.isEmpty()) fc.setCurrentDirectory(new java.io.File(dir));
                String t = it.data.getOrDefault("title", "");
                if (!t.isEmpty()) fc.setDialogTitle(t);
                if (it.kind.equals("FolderBrowserDialog")) fc.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
                else {
                    String fn = it.data.getOrDefault("filename", "");
                    if (!fn.isEmpty()) fc.setSelectedFile(new java.io.File(fn));
                    String[] f = it.data.getOrDefault("filter", "").split("\\|");
                    for (int i = 0; i + 1 < f.length; i += 2) {
                        final String desc = f[i], pat = f[i + 1];
                        if (pat.trim().equals("*.*")) continue;
                        final String[] exts = pat.replace("*.", "").split(";");
                        fc.addChoosableFileFilter(new javax.swing.filechooser.FileNameExtensionFilter(desc, exts));
                    }
                }
                int r = it.kind.equals("SaveFileDialog") ? fc.showSaveDialog(owner) : fc.showOpenDialog(owner);
                if (r != JFileChooser.APPROVE_OPTION) return "Cancel";
                it.data.put(it.kind.equals("FolderBrowserDialog") ? "selectedpath" : "filename", fc.getSelectedFile().getAbsolutePath());
                return "OK";
            }
            case "ColorDialog": {
                Color start = toColor(it.data.getOrDefault("color", "#000000"));
                Color col = JColorChooser.showDialog(owner, it.data.getOrDefault("title", "Color"), start == null ? Color.BLACK : start);
                if (col == null) return "Cancel";
                it.data.put("color", String.format("#%02X%02X%02X", col.getRed(), col.getGreen(), col.getBlue()));
                return "OK";
            }
            default:
                return "Cancel";
        }
    }

    static String res(String file) {
        if (file == null || file.isEmpty() || new java.io.File(file).isAbsolute()) return file;
        String base = System.getProperty("jpackage.app-path");
        java.io.File dir = base != null ? new java.io.File(base).getParentFile() : new java.io.File(".");
        java.io.File f = new java.io.File(dir, file);
        return f.exists() ? f.getAbsolutePath() : file;
    }

    // ================================================================== forms
    /** Base class of the generated forms (RadForm_Form1 ...). */
    public static class FormBase extends JFrame {
        public final String radName;
        final Map<String, Item> items = new TreeMap<>(String.CASE_INSENSITIVE_ORDER);
        protected final JPanel client = new JPanel(new RadLayout());
        protected final Map<Container, ButtonGroup> radioGroups = new HashMap<>();
        boolean loaded;
        String tag = "";

        protected FormBase(String name) {
            radName = name;
            setName(name);
            setContentPane(client);
            setDefaultCloseOperation(WindowConstants.DO_NOTHING_ON_CLOSE);
            addWindowListener(new WindowAdapter() {
                @Override
                public void windowClosing(WindowEvent e) { userClose(); }
            });
            String icon = System.getProperty("jpackage.app-path");
            if (icon != null) {
                try {
                    Icon ic = javax.swing.filechooser.FileSystemView.getFileSystemView().getSystemIcon(new java.io.File(icon));
                    if (ic instanceof ImageIcon) setIconImage(((ImageIcon) ic).getImage());
                } catch (RuntimeException ignored) {
                }
            }
        }

        void userClose() {
            RadEvent ev = RadEvent.parse(radName, "FormClosing", "");
            fire(radName, "FormClosing", ev);
            if (RadSwing.cancel(ev)) return;
            if (this == startup || ending) {
                fire(radName, "FormClosed", null);
                System.exit(0);
            }
            setVisible(false);
            fire(radName, "FormClosed", null);
        }

        public void showForm() {
            if (!loaded) {
                loaded = true;
                fire(radName, "Load", null);
            }
            setVisible(true);
            toFront();
        }

        // ---------------------------------------------------------- helpers for the generated code
        protected static Font font(String family, float pt, boolean bold, boolean italic) {
            return new Font(family == null || family.isEmpty() ? "Segoe UI" : family,
                    (bold ? Font.BOLD : 0) | (italic ? Font.ITALIC : 0), 1).deriveFont(pt * 96f / 72f);
        }

        protected static Color rgb(int r, int g, int b) { return new Color(r, g, b); }

        protected void place(JComponent c, Container parent, double x, double y, double w, double h,
                             double rx, double ry, double rw, double rh) {
            parent.add(c, new double[]{x, y, w, h, rx, ry, rw, rh});
        }

        protected Item reg(String name, String type, Object comp, JComponent outer) {
            Item it = new Item(name, type, comp, outer);
            if (comp instanceof JComponent) ((JComponent) comp).setName(name);
            items.put(name, it);
            return it;
        }

        protected Item dialog(String name, String kind, String... props) {
            Item it = new Item(name, "Dialog", null, null);
            it.kind = kind;
            for (int i = 0; i + 1 < props.length; i += 2) it.data.put(props[i].toLowerCase(Locale.ROOT), props[i + 1]);
            items.put(name, it);
            return it;
        }

        protected ButtonGroup radioGroup(Container parent) {
            return radioGroups.computeIfAbsent(parent, k -> new ButtonGroup());
        }

        protected void hidden(String name) {
            Item it = items.get(name);
            it.shown = false;
            it.outer.setVisible(false);
        }

        protected void setClientSize(int w, int h) {
            client.setPreferredSize(new Dimension(w, h));
            pack();
        }

        protected static JScrollPane scroll(JComponent c) {
            JScrollPane sp = new JScrollPane(c);
            sp.setName(c.getName());
            return sp;
        }

        protected static ImageIcon image(String file) {
            try {
                return new ImageIcon(res(file));
            } catch (RuntimeException e) {
                return null;
            }
        }

        protected static Font underline(Font f) {
            Map<TextAttribute, Object> a = new HashMap<>(f.getAttributes());
            a.put(TextAttribute.UNDERLINE, TextAttribute.UNDERLINE_ON);
            return f.deriveFont(a);
        }

        protected static BevelBorder sunken() { return new BevelBorder(BevelBorder.LOWERED); }

        // ---------------------------------------------------------- events
        static int button(MouseEvent e) {
            return SwingUtilities.isLeftMouseButton(e) ? 1 : SwingUtilities.isMiddleMouseButton(e) ? 2 : SwingUtilities.isRightMouseButton(e) ? 3 : 0;
        }

        static RadEvent mouse(String owner, String ev, MouseEvent e) {
            return RadEvent.parse(owner, ev, e.getX() + " " + e.getY() + " " + button(e) + " 0");
        }

        /** Java key codes -> Windows virtual keys (VB KeyCode) where they differ. */
        static int vk(int k) {
            switch (k) {
                case KeyEvent.VK_ENTER: return 13;
                case KeyEvent.VK_DELETE: return 46;
                case KeyEvent.VK_INSERT: return 45;
                case KeyEvent.VK_META: return 91;
                case KeyEvent.VK_SEMICOLON: return 186;
                case KeyEvent.VK_EQUALS: return 187;
                case KeyEvent.VK_COMMA: return 188;
                case KeyEvent.VK_MINUS: return 189;
                case KeyEvent.VK_PERIOD: return 190;
                case KeyEvent.VK_SLASH: return 191;
                case KeyEvent.VK_BACK_QUOTE: return 192;
                case KeyEvent.VK_OPEN_BRACKET: return 219;
                case KeyEvent.VK_BACK_SLASH: return 220;
                case KeyEvent.VK_CLOSE_BRACKET: return 221;
                case KeyEvent.VK_QUOTE: return 222;
                default: return k;
            }
        }

        /** Connect the events of a component that have a handler (<owner>_<event>). */
        @SuppressWarnings("rawtypes")
        protected void wire(Object target, String owner, String... events) {
            Item item = items.get(owner);
            for (String ev : events) {
                if (!has(owner + "_" + ev)) continue;
                final Component c = target instanceof Component ? (Component) target : null;
                switch (ev) {
                    case "Click":
                        if (target instanceof AbstractButton) ((AbstractButton) target).addActionListener(e -> fire(owner, ev, null));
                        else if (c != null) c.addMouseListener(new MouseAdapter() {
                            @Override
                            public void mouseClicked(MouseEvent e) { if (e.getClickCount() == 1 && SwingUtilities.isLeftMouseButton(e)) fire(owner, ev, null); }
                        });
                        break;
                    case "DoubleClick":
                        if (c != null) c.addMouseListener(new MouseAdapter() {
                            @Override
                            public void mouseClicked(MouseEvent e) { if (e.getClickCount() == 2) fire(owner, ev, null); }
                        });
                        break;
                    case "MouseDown":
                    case "MouseUp":
                    case "MouseEnter":
                    case "MouseLeave":
                        if (c != null) c.addMouseListener(new MouseAdapter() {
                            @Override
                            public void mousePressed(MouseEvent e) { if (ev.equals("MouseDown")) fire(owner, ev, mouse(owner, ev, e)); }

                            @Override
                            public void mouseReleased(MouseEvent e) { if (ev.equals("MouseUp")) fire(owner, ev, mouse(owner, ev, e)); }

                            @Override
                            public void mouseEntered(MouseEvent e) { if (ev.equals("MouseEnter")) fire(owner, ev, null); }

                            @Override
                            public void mouseExited(MouseEvent e) { if (ev.equals("MouseLeave")) fire(owner, ev, null); }
                        });
                        break;
                    case "MouseMove":
                        if (c != null) c.addMouseMotionListener(new MouseMotionAdapter() {
                            @Override
                            public void mouseMoved(MouseEvent e) { fire(owner, ev, mouse(owner, ev, e)); }

                            @Override
                            public void mouseDragged(MouseEvent e) { fire(owner, ev, mouse(owner, ev, e)); }
                        });
                        break;
                    case "MouseWheel":
                        if (c != null) c.addMouseWheelListener(e -> {
                            RadEvent r = mouse(owner, ev, e);
                            fire(owner, ev, r);
                        });
                        break;
                    case "KeyDown":
                    case "KeyUp":
                    case "KeyPress":
                        if (c != null) c.addKeyListener(new KeyAdapter() {
                            @Override
                            public void keyPressed(KeyEvent e) { if (ev.equals("KeyDown")) fire(owner, ev, RadEvent.parse(owner, ev, "0 0 0 " + vk(e.getKeyCode()))); }

                            @Override
                            public void keyReleased(KeyEvent e) { if (ev.equals("KeyUp")) fire(owner, ev, RadEvent.parse(owner, ev, "0 0 0 " + vk(e.getKeyCode()))); }

                            @Override
                            public void keyTyped(KeyEvent e) {
                                if (!ev.equals("KeyPress")) return;
                                char ch = e.getKeyChar();
                                RadEvent r = RadEvent.parse(owner, ev, "0 0 0 " + (int) ch);
                                r.keyChar = String.valueOf(ch);
                                fire(owner, ev, r);
                            }
                        });
                        break;
                    case "GotFocus":
                    case "LostFocus":
                        if (c != null) c.addFocusListener(new FocusAdapter() {
                            @Override
                            public void focusGained(FocusEvent e) { if (ev.equals("GotFocus")) fire(owner, ev, null); }

                            @Override
                            public void focusLost(FocusEvent e) { if (ev.equals("LostFocus")) fire(owner, ev, null); }
                        });
                        break;
                    case "TextChanged":
                        if (target instanceof JTextComponent && item != null) {
                            item.data.put("owner", owner);
                            item.lastText = ((JTextComponent) target).getText();
                            ((JTextComponent) target).getDocument().addDocumentListener(new DocumentListener() {
                                void later() {
                                    if (!item.muteText) SwingUtilities.invokeLater(() -> textChanged(item));
                                }

                                @Override
                                public void insertUpdate(DocumentEvent e) { later(); }

                                @Override
                                public void removeUpdate(DocumentEvent e) { later(); }

                                @Override
                                public void changedUpdate(DocumentEvent e) { }
                            });
                        } else if (target instanceof JComboBox) {
                            ((JComboBox) target).addActionListener(e -> fire(owner, ev, null));
                        }
                        break;
                    case "CheckedChanged":
                        if (target instanceof AbstractButton) ((AbstractButton) target).addItemListener(e -> fire(owner, ev, null));
                        break;
                    case "SelectedIndexChanged":
                        if (target instanceof JList) ((JList) target).addListSelectionListener(e -> {
                            if (!e.getValueIsAdjusting()) fire(owner, ev, null);
                        });
                        else if (target instanceof JComboBox) ((JComboBox) target).addItemListener(e -> {
                            if (e.getStateChange() == ItemEvent.SELECTED) fire(owner, ev, null);
                        });
                        else if (target instanceof JTabbedPane) ((JTabbedPane) target).addChangeListener(e -> fire(owner, ev, null));
                        break;
                    case "ValueChanged":
                        if (target instanceof JSpinner) ((JSpinner) target).addChangeListener(e -> fire(owner, ev, null));
                        else if (target instanceof JSlider) ((JSlider) target).addChangeListener(e -> fire(owner, ev, null));
                        break;
                    case "Tick":
                        if (target instanceof javax.swing.Timer) ((javax.swing.Timer) target).addActionListener(e -> fire(owner, ev, null));
                        break;
                    case "Resize":
                        if (c != null) c.addComponentListener(new ComponentAdapter() {
                            @Override
                            public void componentResized(ComponentEvent e) { fire(owner, ev, null); }
                        });
                        break;
                    case "Activated":
                    case "Deactivate":
                        if (target instanceof Window) ((Window) target).addWindowListener(new WindowAdapter() {
                            @Override
                            public void windowActivated(WindowEvent e) { if (ev.equals("Activated")) fire(owner, ev, null); }

                            @Override
                            public void windowDeactivated(WindowEvent e) { if (ev.equals("Deactivate")) fire(owner, ev, null); }
                        });
                        break;
                    default:
                        break;
                }
            }
        }

        // ---------------------------------------------------------- the form's own properties
        String getProp(String p) {
            switch (p) {
                case "caption":
                case "text": return getTitle();
                case "name": return radName;
                case "tag": return tag;
                case "left": return Integer.toString(getX());
                case "top": return Integer.toString(getY());
                case "width": return Integer.toString(client.getWidth());
                case "height": return Integer.toString(client.getHeight());
                case "visible": return b(isVisible());
                case "enabled": return b(isEnabled());
                case "backcolor": return fromColor(client.getBackground());
                case "windowstate": return (getExtendedState() & MAXIMIZED_BOTH) != 0 ? "Maximized" : (getExtendedState() & ICONIFIED) != 0 ? "Minimized" : "Normal";
                default:
                    warn("Form doesn't support property '" + p + "'");
                    return "";
            }
        }

        void setProp(String p, String v) {
            switch (p) {
                case "caption":
                case "text": setTitle(v); return;
                case "tag": tag = v; return;
                case "left": setLocation(Rad.toInt(v), getY()); return;
                case "top": setLocation(getX(), Rad.toInt(v)); return;
                case "width": client.setPreferredSize(new Dimension(Rad.toInt(v), client.getHeight())); pack(); return;
                case "height": client.setPreferredSize(new Dimension(client.getWidth(), Rad.toInt(v))); pack(); return;
                case "visible": if (Rad.toBool(v)) showForm(); else setVisible(false); return;
                case "enabled": setEnabled(Rad.toBool(v)); return;
                case "backcolor": client.setBackground(toColor(v)); return;
                case "windowstate": {
                    String s = v.toLowerCase(Locale.ROOT);
                    setExtendedState(s.startsWith("max") ? MAXIMIZED_BOTH : s.startsWith("min") ? ICONIFIED : NORMAL);
                    return;
                }
                default:
                    warn("Form doesn't support property '" + p + "'");
            }
        }

        String call(String m, String[] a) {
            switch (m) {
                case "show": showForm(); return "";
                case "hide": setVisible(false); return "";
                case "close":
                case "unload": userClose(); return "";
                case "refresh": repaint(); return "";
                default: return getProp(m);
            }
        }
    }

    static boolean cancel(RadEvent e) {
        try {
            return RadEvent.class.getField("cancel").getBoolean(e);
        } catch (ReflectiveOperationException ex) {
            return false;
        }
    }

    // ================================================================== layout
    /** Anchor / Dock layout (radide/layout.py Place): x + rx * W, y + ry * H, w + rw * W, h + rh * H. */
    static final class RadLayout implements LayoutManager2 {
        final Map<Component, double[]> places = new HashMap<>();

        static void fix(Component c, Rectangle r) {
            Container p = c.getParent();
            if (p != null && p.getLayout() instanceof RadLayout) {
                ((RadLayout) p.getLayout()).places.put(c, new double[]{r.x, r.y, r.width, r.height, 0, 0, 0, 0});
                p.revalidate();
                p.repaint();
            } else c.setBounds(r);
        }

        @Override
        public void addLayoutComponent(Component comp, Object constraints) {
            if (constraints instanceof double[]) places.put(comp, (double[]) constraints);
        }

        @Override
        public void addLayoutComponent(String name, Component comp) { }

        @Override
        public void removeLayoutComponent(Component comp) { places.remove(comp); }

        @Override
        public Dimension preferredLayoutSize(Container parent) {
            if (parent instanceof JComponent && ((JComponent) parent).isPreferredSizeSet()) return parent.getPreferredSize();
            int w = 0, h = 0;
            for (double[] p : places.values()) {
                w = (int) Math.max(w, p[0] + p[2]);
                h = (int) Math.max(h, p[1] + p[3]);
            }
            return new Dimension(w, h);
        }

        @Override
        public Dimension minimumLayoutSize(Container parent) { return new Dimension(0, 0); }

        @Override
        public Dimension maximumLayoutSize(Container target) { return new Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE); }

        @Override
        public void layoutContainer(Container parent) {
            double W = parent.getWidth(), H = parent.getHeight();
            for (Component c : parent.getComponents()) {
                double[] p = places.get(c);
                if (p == null) continue;
                c.setBounds((int) Math.round(p[0] + p[4] * W), (int) Math.round(p[1] + p[5] * H),
                        (int) Math.max(0, Math.round(p[2] + p[6] * W)), (int) Math.max(0, Math.round(p[3] + p[7] * H)));
            }
        }

        @Override
        public float getLayoutAlignmentX(Container target) { return 0; }

        @Override
        public float getLayoutAlignmentY(Container target) { return 0; }

        @Override
        public void invalidateLayout(Container target) { }
    }
}
