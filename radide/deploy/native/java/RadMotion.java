// RAD IDE - animations, visual states and layout variants of the native Swing runtime (RadSwing.java).
//
// The same semantics as the IDE's Python runtime (radide/motion/runtime_py.py _RadFx, features/timeline.py
// _Storyboard, features/states.py _VisualStates, variants/runtime_py.py _RadVariants) and the C reference
// (radide/runtimes/native/radforms/radforms_motion.inc), driven by the records of radide/motion/native_plan.py
// (TAB-separated, one per line, \t \n \r \\ escaped) that the generated form passes to FormBase.motion(...):
//
//   XR respect                                  the form respects the reduced-motion setting
//   X  fx target count forever autorev delay restore   storyboard ("" target = the form)
//   XT on source interval after leave           its trigger (load click hover timer show hide after manual)
//   K  prop ms ease kind a b c d                keyframe; kind n number, c colour, b bool, s text,
//                                               r relative (start*a + b + d*start(c)), p parent colour,
//                                               v typewriter (start text up to fraction a)
//   Q  control state prop value                 visual state override ("" control = the form)
//   V  size minW maxW minH maxH orientation posture span fold     layout size
//   VL size control "x y w h rx ry rw rh"       place of the control on that size
//   VP size control prop value                  property on that size
//
// Program API (Rad.call on the form): BeginAnimation(name), StopAnimation(name), GoToState(state[, control])
// (also on a control: GoToState(state)), ApplySizeVariants(); properties CurrentSizes, CurrentState; events
// <Form>_SizeVariantChanged, <storyboard>_Completed. RADIDE_REDUCED_MOTION=1 ends every animation at once when
// the form respects reduced motion. RADIDE_POSTURE / RADIDE_SPAN / RADIDE_HINGE simulate a foldable.
import java.awt.*;
import java.awt.event.*;
import java.util.*;
import java.util.List;
import javax.swing.*;

final class RadMotion {
    static final int OVER = 1, PRESSED = 2, FOCUSED = 4, DISABLED = 8;
    static final int K_NUM = 0, K_COLOR = 1, K_BOOL = 2, K_TEXT = 3, K_REL = 4, K_PARENT = 5, K_REVEAL = 6;
    static final int P_NUM = 0, P_COLOR = 1, P_BOOL = 2, P_TEXT = 3;
    static final int T_LOAD = 0, T_CLICK = 1, T_HOVER = 2, T_TIMER = 3, T_SHOW = 4, T_HIDE = 5, T_AFTER = 6, T_MANUAL = 7;
    static final int E_LINEAR = 0, E_IN = 1, E_OUT = 2, E_INOUT = 3, E_SINE = 4, E_BACK = 5, E_ELASTIC = 6, E_BOUNCE = 7;
    static final String[] TRIGGERS = {"load", "click", "hover", "timer", "show", "hide", "after", "manual"};

    static final class Key {
        int ms, ease, kind;
        char of;                          // 0, 'W' (start Width), 'H' (start Height)
        double a, b, d;
        String s;                         // K_TEXT
        Color col;                        // K_COLOR
        double rv;                        // resolved number / bool
        Color rc;                         // resolved colour
        String rs;                        // resolved text
    }

    static final class Track {
        String prop;
        int pt;
        final List<Key> k = new ArrayList<>();
        double sNum;
        Color sCol;
        String sText;
        int lastBool = -1;
    }

    static final class Sb {
        String fx = "", tname = "", src = "", after = "";
        RadSwing.Item c;                  // null = the form
        int count = 1, delay, on = T_MANUAL, interval, leave, dur;
        boolean forever, autorev, restore;
        final List<Track> tr = new ArrayList<>();
        boolean playing, rev, hiding, saved, pending;
        double t0, pos;
        double[] pl0;
        javax.swing.Timer delayTimer, every;
    }

    static final class Q { RadSwing.Item c; boolean form; String state, prop, val; }
    static final class Ap { RadSwing.Item c; String prop, saved, val; Boolean opaque; }
    static final class Size { String id; double mnw, mxw, mnh, mxh; String orient = "", posture = "", span = "", fold = ""; }
    static final class VL { int size; RadSwing.Item c; double[] pl; }
    static final class VP { int size; RadSwing.Item c; String prop, val; }
    static final class BP { RadSwing.Item c; String prop, val; Boolean opaque; }

    final RadSwing.FormBase form;
    boolean respect = true, reduced, started;
    final List<Sb> sbs = new ArrayList<>();
    final List<Q> qs = new ArrayList<>();
    final List<Ap> aps = new ArrayList<>();
    final Map<RadSwing.Item, int[]> flags = new IdentityHashMap<>();
    final Map<RadSwing.Item, String> manual = new IdentityHashMap<>();
    String state = "";
    final List<Size> sizes = new ArrayList<>();
    final List<VL> vls = new ArrayList<>();
    final List<VP> vps = new ArrayList<>();
    final Map<RadSwing.Item, double[]> base = new IdentityHashMap<>();
    final List<BP> bps = new ArrayList<>();
    boolean[] cur;
    javax.swing.Timer frameTimer;
    int designW, designH;

    // ================================================================== helpers
    static double now() { return System.nanoTime() / 1e6; }

    static boolean ieq(String a, String b) { return a != null && b != null && a.equalsIgnoreCase(b); }

    static String lc(String s) { return s.toLowerCase(Locale.ROOT); }

    static int toInt(String s) { return (int) Math.round(Rad.toNumber(s == null ? "" : s)); }

    static boolean bool(String s) {
        s = s == null ? "" : s.trim().toLowerCase(Locale.ROOT);
        return s.equals("1") || s.equals("true") || s.equals("yes") || s.equals("on") || s.equals("-1");
    }

    static boolean envTrue(String name, boolean[] set) {
        String v = System.getenv(name);
        set[0] = false;
        if (v == null || v.trim().isEmpty()) return false;
        set[0] = true;
        v = v.trim().toLowerCase(Locale.ROOT);
        return v.equals("1") || v.equals("true") || v.equals("yes") || v.equals("on");
    }

    static boolean reducedSystem() {
        boolean[] set = {false};
        boolean v = envTrue("RADIDE_REDUCED_MOTION", set);
        return set[0] && v;             // the Windows "Show animations" setting is not read from Java
    }

    static int easeOf(String s) {
        switch (s == null ? "" : lc(s)) {
            case "in": return E_IN;
            case "out": return E_OUT;
            case "inout": return E_INOUT;
            case "sine": return E_SINE;
            case "back": return E_BACK;
            case "elastic": return E_ELASTIC;
            case "bounce": return E_BOUNCE;
            default: return E_LINEAR;
        }
    }

    static double ease(double f, int e) {
        switch (e) {
            case E_IN: return f * f;
            case E_OUT: return 1 - (1 - f) * (1 - f);
            case E_INOUT: return f < 0.5 ? 2 * f * f : 1 - 2 * (1 - f) * (1 - f);
            case E_SINE: return -(Math.cos(Math.PI * f) - 1) / 2;
            case E_BACK: return 1 + 2.70158 * Math.pow(f - 1, 3) + 1.70158 * Math.pow(f - 1, 2);
            case E_ELASTIC:
                if (f <= 0 || f >= 1) return f >= 1 ? 1.0 : 0.0;
                return Math.pow(2, -10 * f) * Math.sin((f * 10 - 0.75) * (2 * Math.PI / 3)) + 1;
            case E_BOUNCE: {
                double n = 7.5625, d = 2.75;
                if (f < 1 / d) return n * f * f;
                if (f < 2 / d) { f -= 1.5 / d; return n * f * f + 0.75; }
                if (f < 2.5 / d) { f -= 2.25 / d; return n * f * f + 0.9375; }
                f -= 2.625 / d;
                return n * f * f + 0.984375;
            }
            default: return f;
        }
    }

    static int ptype(String p) {
        if (ieq(p, "BackColor") || ieq(p, "ForeColor")) return P_COLOR;
        if (ieq(p, "Visible") || ieq(p, "FontBold") || ieq(p, "FontItalic") || ieq(p, "Enabled") || ieq(p, "Checked")) return P_BOOL;
        if (ieq(p, "Text") || ieq(p, "Caption")) return P_TEXT;
        return P_NUM;
    }

    static boolean intProp(String p) {
        return ieq(p, "Left") || ieq(p, "Top") || ieq(p, "Width") || ieq(p, "Height") || ieq(p, "FontSize") || ieq(p, "Value");
    }

    static boolean geo(String p) { return ieq(p, "Left") || ieq(p, "Top") || ieq(p, "Width") || ieq(p, "Height"); }

    static Color parseColor(String s) {
        try {
            return s != null && s.trim().startsWith("#") ? Color.decode(s.trim()) : null;
        } catch (RuntimeException e) {
            return null;
        }
    }

    static String unescape(String s) {
        if (s.indexOf('\\') < 0) return s;
        StringBuilder b = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (ch == '\\' && i + 1 < s.length()) {
                char n = s.charAt(++i);
                b.append(n == 't' ? '\t' : n == 'n' ? '\n' : n == 'r' ? '\r' : n);
            } else b.append(ch);
        }
        return b.toString();
    }

    // ================================================================== property access
    Component compOf(RadSwing.Item c) {
        if (c == null) return form.client;
        return c.comp instanceof Component ? (Component) c.comp : null;
    }

    static double[] placeOf(RadSwing.Item c) {
        Container p = c.outer == null ? null : c.outer.getParent();
        if (p != null && p.getLayout() instanceof RadSwing.RadLayout) {
            double[] pl = ((RadSwing.RadLayout) p.getLayout()).places.get(c.outer);
            return pl == null ? null : pl.clone();
        }
        return null;
    }

    static void setPlace(RadSwing.Item c, double[] pl) {
        Container p = c.outer == null ? null : c.outer.getParent();
        if (pl == null || p == null || !(p.getLayout() instanceof RadSwing.RadLayout)) return;
        ((RadSwing.RadLayout) p.getLayout()).places.put(c.outer, pl.clone());
        double W = p.getWidth(), H = p.getHeight();
        c.outer.setBounds((int) Math.round(pl[0] + pl[4] * W), (int) Math.round(pl[1] + pl[5] * H),
                (int) Math.max(0, Math.round(pl[2] + pl[6] * W)), (int) Math.max(0, Math.round(pl[3] + pl[7] * H)));
        p.revalidate();
        p.repaint();
    }

    double opacity() {
        try {
            return form.getOpacity();
        } catch (Throwable t) {
            return 1.0;
        }
    }

    void setOpacity(double v) {
        try {
            form.setOpacity((float) Math.max(0, Math.min(1, v)));
        } catch (Throwable ignored) {    // decorated windows / no translucency: not supported
        }
    }

    double numGet(RadSwing.Item c, String p) {
        if (ieq(p, "Opacity")) return c == null ? opacity() : 1.0;
        return Rad.toNumber(c == null ? form.getProp(lc(p)) : RadSwing.get(c, lc(p)));
    }

    Color colorGet(RadSwing.Item c, String p) {
        Component comp = compOf(c);
        if (comp == null) return Color.BLACK;
        Color col = ieq(p, "ForeColor") ? comp.getForeground() : comp.getBackground();
        return col != null ? col : ieq(p, "ForeColor") ? Color.BLACK : Color.WHITE;
    }

    Color parentColor(RadSwing.Item c) {
        if (c == null || c.outer == null || c.outer.getParent() == null) return colorGet(null, "BackColor");
        Color col = c.outer.getParent().getBackground();
        return col != null ? col : Color.WHITE;
    }

    void write(RadSwing.Item c, String p, String v) {
        if (c == null) form.setProp(lc(p), v);
        else RadSwing.set(c, lc(p), v);
    }

    void numSet(RadSwing.Item c, String p, double v) {
        if (ieq(p, "Opacity")) {
            if (c == null) setOpacity(v);   // child controls have no transparency (expand() blends colours)
            return;
        }
        write(c, p, intProp(p) ? Long.toString(Math.round(v)) : Double.toString(v));
    }

    void colorSet(RadSwing.Item c, String p, Color col) {
        write(c, p, String.format("#%02X%02X%02X", col.getRed(), col.getGreen(), col.getBlue()));
    }

    String textGet(RadSwing.Item c) { return c == null ? form.getTitle() : RadSwing.text(c); }

    void textSet(RadSwing.Item c, String s) { write(c, "Text", s == null ? "" : s); }

    /** A property as text (visual states / variants save it to give it back later). */
    String getStr(RadSwing.Item c, String p) {
        if (ieq(p, "Opacity")) return c == null ? RadSwing.n(opacity()) : "1";
        if (c == null) return form.getProp(lc(p));
        if (ieq(p, "BackColor") && c.comp instanceof JComponent && !((JComponent) c.comp).isBackgroundSet()) return "";
        return RadSwing.get(c, lc(p));
    }

    Boolean opaqueOf(RadSwing.Item c) {
        return c != null && c.comp instanceof JComponent ? ((JComponent) c.comp).isOpaque() : null;
    }

    void setStr(RadSwing.Item c, String p, String v, Boolean opaque) {
        if (ieq(p, "Opacity")) {
            if (c == null) setOpacity(Rad.toNumber(v));
            return;
        }
        if (c != null && ieq(p, "BackColor") && (v == null || v.isEmpty()) && c.comp instanceof JComponent) {
            JComponent jc = (JComponent) c.comp;
            jc.setBackground(null);
            if (opaque != null) jc.setOpaque(opaque);
            jc.repaint();
            return;
        }
        write(c, p, v == null ? "" : v);
    }

    // ================================================================== set-up
    RadMotion(RadSwing.FormBase f, String text) {
        form = f;
        Dimension d = f.client.getPreferredSize();
        designW = d.width;
        designH = d.height;
        Sb sb = null;
        for (String line : text.split("\n")) {
            if (line.isEmpty()) continue;
            String[] raw = line.split("\t", -1);
            String[] F = new String[Math.max(10, raw.length)];
            Arrays.fill(F, "");
            for (int i = 0; i < raw.length; i++) F[i] = unescape(raw[i]);
            String k = F[0];
            switch (k) {
                case "XR":
                    respect = bool(F[1]);
                    break;
                case "X": {
                    sb = null;
                    RadSwing.Item c = item(F[2]);
                    if (!F[2].isEmpty() && c == null) continue;
                    sb = new Sb();
                    sb.fx = F[1];
                    sb.tname = F[2];
                    sb.c = c;
                    sb.count = Math.max(1, toInt(F[3]));
                    sb.forever = toInt(F[4]) != 0;
                    sb.autorev = toInt(F[5]) != 0;
                    sb.delay = toInt(F[6]);
                    sb.restore = toInt(F[7]) != 0;
                    sbs.add(sb);
                    break;
                }
                case "XT":
                    if (sb == null) break;
                    sb.on = T_MANUAL;
                    for (int i = 0; i < TRIGGERS.length; i++) if (ieq(F[1], TRIGGERS[i])) sb.on = i;
                    sb.src = F[2].isEmpty() ? sb.tname : F[2];
                    sb.interval = toInt(F[3]);
                    sb.after = F[4];
                    sb.leave = ieq(F[5], "stop") ? 1 : ieq(F[5], "none") ? 2 : 0;
                    break;
                case "K": {
                    if (sb == null) break;
                    Track t = sb.tr.isEmpty() ? null : sb.tr.get(sb.tr.size() - 1);
                    if (t == null || !ieq(t.prop, F[1])) {
                        t = new Track();
                        t.prop = F[1];
                        t.pt = ptype(t.prop);
                        sb.tr.add(t);
                    }
                    Key key = new Key();
                    key.ms = toInt(F[2]);
                    if (key.ms > sb.dur) sb.dur = key.ms;
                    key.ease = easeOf(F[3]);
                    key.a = Rad.toNumber(F[5]);
                    key.b = Rad.toNumber(F[6]);
                    key.d = Rad.toNumber(F[8]);
                    key.of = ieq(F[7], "Width") ? 'W' : ieq(F[7], "Height") ? 'H' : 0;
                    switch (F[4].isEmpty() ? 'n' : F[4].charAt(0)) {
                        case 'c': key.kind = K_COLOR; key.col = parseColor(F[5]); if (key.col == null) key.col = Color.BLACK; break;
                        case 'b': key.kind = K_BOOL; key.a = bool(F[5]) ? 1 : 0; break;
                        case 's': key.kind = K_TEXT; key.s = F[5]; break;
                        case 'r': key.kind = K_REL; break;
                        case 'p': key.kind = K_PARENT; break;
                        case 'v': key.kind = K_REVEAL; break;
                        default: key.kind = K_NUM; break;
                    }
                    t.k.add(key);
                    break;
                }
                case "Q": {
                    RadSwing.Item c = item(F[1]);
                    if (!F[1].isEmpty() && c == null) continue;
                    Q q = new Q();
                    q.c = c;
                    q.form = c == null;
                    q.state = F[2];
                    q.prop = F[3];
                    q.val = F[4];
                    qs.add(q);
                    break;
                }
                case "V": {
                    Size s = new Size();
                    s.id = F[1];
                    s.mnw = lim(F[2]);
                    s.mxw = lim(F[3]);
                    s.mnh = lim(F[4]);
                    s.mxh = lim(F[5]);
                    s.orient = lc(F[6]);
                    s.posture = postureNorm(F[7]);
                    s.span = lc(F[8]);
                    s.fold = lc(F[9]);
                    sizes.add(s);
                    break;
                }
                case "VL":
                case "VP": {
                    RadSwing.Item c = item(F[2]);
                    if (!F[2].isEmpty() && c == null) continue;
                    int si = -1;
                    for (int i = 0; i < sizes.size(); i++) if (ieq(sizes.get(i).id, F[1])) { si = i; break; }
                    if (si < 0) continue;
                    if (k.equals("VL")) {
                        String[] nums = F[3].trim().split("\\s+");
                        if (c == null || nums.length != 8) continue;
                        double[] pl = new double[8];
                        for (int i = 0; i < 8; i++) pl[i] = Rad.toNumber(nums[i]);
                        if (!base.containsKey(c)) {
                            double[] b0 = placeOf(c);
                            if (b0 == null) continue;
                            base.put(c, b0);
                        }
                        VL v = new VL();
                        v.size = si;
                        v.c = c;
                        v.pl = pl;
                        vls.add(v);
                    } else {
                        VP v = new VP();
                        v.size = si;
                        v.c = c;
                        v.prop = F[3];
                        v.val = F[4];
                        vps.add(v);
                        addBp(c, v.prop);
                    }
                    break;
                }
                default:
                    break;
            }
        }
        reduced = respect && reducedSystem();
        // events the triggers and the automatic states need (whatever handlers the program has)
        Set<RadSwing.Item> listen = Collections.newSetFromMap(new IdentityHashMap<>());
        boolean formSrc = false;
        for (Sb s : sbs) {
            if (s.on != T_CLICK && s.on != T_HOVER) continue;
            RadSwing.Item c = s.src.isEmpty() || ieq(s.src, form.radName) ? null : item(s.src);
            if (c != null) listen.add(c);
            else if (s.src.isEmpty() || ieq(s.src, form.radName)) formSrc = true;
        }
        for (Q q : qs) if (q.c != null) listen.add(q.c);
        for (RadSwing.Item c : listen) hook(c);
        if (formSrc) hook(null);
        for (RadSwing.Item c : listen)            // controls that start disabled are in their Disabled state
            if (hasStates(c) && c.comp instanceof Component && !((Component) c.comp).isEnabled()) flag(c, DISABLED, true);
        if (!sizes.isEmpty()) {
            form.client.addComponentListener(new ComponentAdapter() {
                @Override
                public void componentResized(ComponentEvent e) { variants(true); }
            });
        }
        variants(false);
    }

    RadSwing.Item item(String name) {
        if (name == null || name.isEmpty()) return null;
        RadSwing.Item it = form.items.get(name);
        return it != null && it.comp instanceof Component && it.outer != null ? it : null;
    }

    static double lim(String s) { return s == null || s.trim().isEmpty() ? -1 : Rad.toNumber(s); }

    void addBp(RadSwing.Item c, String prop) {
        for (BP b : bps) if (b.c == c && ieq(b.prop, prop)) return;
        BP b = new BP();
        b.c = c;
        b.prop = prop;
        b.val = getStr(c, prop);
        b.opaque = opaqueOf(c);
        bps.add(b);
    }

    void hook(RadSwing.Item c) {
        Component comp = compOf(c);
        if (comp == null) return;
        comp.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseEntered(MouseEvent e) { event(c, "MouseEnter"); }

            @Override
            public void mouseExited(MouseEvent e) { event(c, "MouseLeave"); }

            @Override
            public void mousePressed(MouseEvent e) { event(c, "MouseDown"); }

            @Override
            public void mouseReleased(MouseEvent e) { event(c, "MouseUp"); }

            @Override
            public void mouseClicked(MouseEvent e) {
                if (!(comp instanceof AbstractButton) && e.getClickCount() == 1 && SwingUtilities.isLeftMouseButton(e)) event(c, "Click");
            }
        });
        if (comp instanceof AbstractButton) ((AbstractButton) comp).addActionListener(e -> event(c, "Click"));
        comp.addFocusListener(new FocusAdapter() {
            @Override
            public void focusGained(FocusEvent e) { event(c, "GotFocus"); }

            @Override
            public void focusLost(FocusEvent e) { event(c, "LostFocus"); }
        });
    }

    // ================================================================== storyboards
    void forget(Sb sb) {
        for (Track t : sb.tr) {
            t.sText = null;
            for (Key k : t.k) k.rs = null;
        }
        sb.saved = false;
    }

    /** The values at Begin; relative keys made absolute against them (_Storyboard._remember). */
    void remember(Sb sb) {
        if (sb.saved) return;
        sb.saved = true;
        sb.pl0 = null;
        double sw = numGet(sb.c, "Width"), sh = numGet(sb.c, "Height");
        for (Track t : sb.tr) {
            t.lastBool = -1;
            if (sb.c != null && geo(t.prop) && sb.pl0 == null) sb.pl0 = placeOf(sb.c);   // Stop gives Anchor / Dock back
            switch (t.pt) {
                case P_COLOR: t.sCol = colorGet(sb.c, t.prop); break;
                case P_BOOL: t.sNum = Rad.toBool(sb.c == null ? form.getProp(lc(t.prop)) : RadSwing.get(sb.c, lc(t.prop))) ? 1 : 0; break;
                case P_TEXT: t.sText = textGet(sb.c); break;
                default: t.sNum = numGet(sb.c, t.prop); break;
            }
            for (Key k : t.k) {
                k.rs = null;
                switch (k.kind) {
                    case K_PARENT:
                        if (t.pt == P_COLOR) k.rc = parentColor(sb.c);
                        else k.rv = t.sNum;
                        break;
                    case K_REL:
                        if (t.pt == P_NUM) {
                            double v = t.sNum * k.a + k.b + (k.of == 'W' ? k.d * sw : k.of == 'H' ? k.d * sh : 0);
                            if (intProp(t.prop)) v = Math.floor(v + 0.5);
                            if (ieq(t.prop, "Opacity")) v = Math.max(0, Math.min(1, v));
                            k.rv = v;
                        } else if (t.pt == P_TEXT) k.rs = t.sText == null ? "" : t.sText;
                        else if (t.pt == P_COLOR) k.rc = t.sCol;            // colours / bools keep their start value
                        else k.rv = t.sNum;
                        break;
                    case K_REVEAL: {
                        String s = t.sText == null ? "" : t.sText;
                        double fr = Math.max(0, Math.min(1, k.a));
                        int n = (int) Math.floor(s.length() * fr + 0.5);
                        k.rs = s.substring(0, Math.min(s.length(), n));
                        break;
                    }
                    case K_TEXT: k.rs = k.s == null ? "" : k.s; break;
                    case K_COLOR: k.rc = k.col; break;
                    default: k.rv = k.a; break;       // n / b
                }
            }
        }
    }

    static Color mixColor(Color a, Color b, double fr) {
        if (a == null) a = b;
        if (b == null) return a;
        if (fr >= 1) return b;
        int r = (int) Math.floor(a.getRed() + (b.getRed() - a.getRed()) * fr + 0.5);
        int g = (int) Math.floor(a.getGreen() + (b.getGreen() - a.getGreen()) * fr + 0.5);
        int bl = (int) Math.floor(a.getBlue() + (b.getBlue() - a.getBlue()) * fr + 0.5);
        return new Color(Math.max(0, Math.min(255, r)), Math.max(0, Math.min(255, g)), Math.max(0, Math.min(255, bl)));
    }

    /** Text between two keys: typed / erased when one is a prefix of the other, else discrete. */
    static String mixText(String a, String b, double fr) {
        int la = a.length(), lb = b.length();
        String longer = la > lb ? a : b;
        if (fr <= 0) return a;
        if ((la <= lb && b.startsWith(a)) || (lb < la && a.startsWith(b))) {
            double x = la + ((double) lb - (double) la) * Math.min(1, fr);
            int n = (int) (x < 0 ? 0 : Math.floor(x + 0.5));
            return longer.substring(0, Math.min(longer.length(), n));
        }
        return fr >= 1 ? b : a;
    }

    void apply(Sb sb, double ms) {
        sb.pos = ms;
        for (Track t : sb.tr) {
            List<Key> k = t.k;
            if (k.isEmpty()) continue;
            Key k0 = null, k1 = null;
            double v0, v1, fr = 1;
            Color c0, c1;
            String s0, s1;
            boolean lead = k.get(0).ms > 0;     // the start value is the implicit key at 0
            String st = t.sText == null ? "" : t.sText;
            if (ms <= (lead ? 0 : k.get(0).ms)) {
                if (lead) { v0 = v1 = t.sNum; c0 = c1 = t.sCol; s0 = s1 = st; }
                else { Key f = k.get(0); v0 = v1 = f.rv; c0 = c1 = f.rc; s0 = s1 = f.rs == null ? "" : f.rs; }
            } else {
                for (int j = 0; j < k.size(); j++)
                    if (ms <= k.get(j).ms) { k1 = k.get(j); k0 = j > 0 ? k.get(j - 1) : null; break; }
                if (k1 == null) {
                    k1 = k.get(k.size() - 1);
                    v0 = v1 = k1.rv;
                    c0 = c1 = k1.rc;
                    s0 = s1 = k1.rs == null ? "" : k1.rs;
                } else {
                    int t0 = k0 != null ? k0.ms : 0;
                    v0 = k0 != null ? k0.rv : t.sNum;
                    c0 = k0 != null ? k0.rc : t.sCol;
                    s0 = k0 != null ? (k0.rs == null ? "" : k0.rs) : st;
                    v1 = k1.rv;
                    c1 = k1.rc;
                    s1 = k1.rs == null ? "" : k1.rs;
                    fr = k1.ms > t0 ? (ms - t0) / (double) (k1.ms - t0) : 1.0;
                    fr = ease(fr, k1.ease);
                }
            }
            switch (t.pt) {
                case P_COLOR: {
                    Color col = fr <= 0 ? c0 : mixColor(c0, c1, fr);
                    if (col != null) colorSet(sb.c, t.prop, col);
                    break;
                }
                case P_BOOL: {
                    int bv = fr >= 1 ? (v1 != 0 ? 1 : 0) : (v0 != 0 ? 1 : 0);
                    if (t.lastBool == bv && ieq(t.prop, "Visible")) break;     // re-showing every frame re-places
                    t.lastBool = bv;
                    write(sb.c, t.prop, bv != 0 ? "True" : "False");
                    break;
                }
                case P_TEXT: {
                    String w = mixText(s0, s1, fr);
                    if (!w.equals(textGet(sb.c))) textSet(sb.c, w);
                    break;
                }
                default:
                    numSet(sb.c, t.prop, fr <= 0 ? v0 : v0 + (v1 - v0) * fr);
                    break;
            }
        }
    }

    void frame() {
        boolean any = false;
        for (Sb sb : sbs) any |= sb.playing;
        if (any) {
            if (frameTimer == null) {
                frameTimer = new javax.swing.Timer(15, e -> {
                    for (int i = 0; i < sbs.size(); i++) if (sbs.get(i).playing) tick(sbs.get(i));
                    frame();
                });
                frameTimer.setCoalesce(true);
            }
            if (!frameTimer.isRunning()) frameTimer.start();
        } else if (frameTimer != null && frameTimer.isRunning()) frameTimer.stop();
    }

    void stop(Sb sb) {
        sb.playing = sb.rev = false;
        sb.pos = 0;
        if (sb.pending) {
            if (sb.delayTimer != null) sb.delayTimer.stop();
            sb.pending = false;
        }
        if (sb.saved) {
            for (Track t : sb.tr) {
                if (sb.c != null && geo(t.prop) && sb.pl0 != null) continue;
                switch (t.pt) {
                    case P_COLOR: if (t.sCol != null) colorSet(sb.c, t.prop, t.sCol); break;
                    case P_BOOL: write(sb.c, t.prop, t.sNum != 0 ? "True" : "False"); break;
                    case P_TEXT: textSet(sb.c, t.sText); break;
                    default: numSet(sb.c, t.prop, t.sNum); break;
                }
            }
            if (sb.c != null && sb.pl0 != null) setPlace(sb.c, sb.pl0);   // Anchor / Dock take the control back
            forget(sb);
        }
        frame();
    }

    void beginNow(Sb sb) {
        remember(sb);
        sb.playing = true;
        sb.rev = false;
        sb.t0 = now();
        apply(sb, 0);
        frame();
    }

    boolean sameNamePlaying(Sb sb) {
        for (Sb o : sbs) if (o != sb && o.playing && ieq(o.fx, sb.fx)) return true;
        return false;
    }

    /** The end of a storyboard: hide / give back / chains / <name>_Completed (_RadFx._done + Completed). */
    void completed(Sb sb) {
        sb.playing = false;
        if (sb.hiding) {
            sb.hiding = false;
            stop(sb);
            write(sb.c, "Visible", "False");
        } else if (sb.restore) {
            stop(sb);
        }
        for (int i = 0; i < sbs.size(); i++) {
            Sb o = sbs.get(i);
            if (o.on == T_AFTER && ieq(o.after, sb.fx)) fxBegin(o);
        }
        if (!sameNamePlaying(sb) && !sb.fx.startsWith("_fx_")) {
            final String name = sb.fx;
            SwingUtilities.invokeLater(() -> RadSwing.fire(name, "Completed", null));
        }
        frame();
    }

    void finish(Sb sb) {
        remember(sb);
        apply(sb, sb.autorev ? 0 : sb.dur);
        completed(sb);
    }

    void tick(Sb sb) {
        double ms = now() - sb.t0;
        boolean done = false;
        if (!sb.playing) return;
        if (sb.rev) {
            double pos = sb.dur - ms;
            if (pos <= 0) { stop(sb); return; }
            apply(sb, pos);
            return;
        }
        double span = (double) sb.dur * (sb.autorev ? 2 : 1), total = span * sb.count;
        if (span <= 0) { ms = 0; done = true; }
        else if (sb.forever) {
            if (ms >= span) { sb.t0 += Math.floor(ms / span) * span; ms = ms % span; }
        } else if (ms >= total) { ms = span; done = true; }
        else ms = ms % span;
        apply(sb, ms <= sb.dur ? ms : span - ms);
        if (done) completed(sb);
    }

    /** _RadFx.Begin: reduced motion jumps to the end; a delay shows the first frame, then waits. */
    void fxBegin(Sb sb) {
        if (reduced) {
            if (!sb.playing) forget(sb);
            finish(sb);
            return;
        }
        if (!sb.playing) forget(sb);              // start from the values the control has now
        if (sb.delay > 0) {
            remember(sb);
            apply(sb, 0);
            sb.pending = true;
            if (sb.delayTimer == null) {
                sb.delayTimer = new javax.swing.Timer(sb.delay, e -> {
                    if (sb.pending) { sb.pending = false; beginNow(sb); }
                });
                sb.delayTimer.setRepeats(false);
            }
            sb.delayTimer.restart();
        } else {
            beginNow(sb);
        }
    }

    void reverse(Sb sb) {
        if (sb.pending) {
            if (sb.delayTimer != null) sb.delayTimer.stop();
            sb.pending = false;
        }
        if (reduced) { stop(sb); return; }
        if (!sb.saved) return;
        sb.playing = true;
        sb.rev = true;
        sb.t0 = now() - (sb.dur - Math.min(sb.pos, sb.dur));
        frame();
    }

    int byName(String name, boolean stop) {
        int n = 0;
        String alt = "_fx_" + (name == null ? "" : name);
        for (Sb sb : sbs) {
            if (!ieq(sb.fx, name) && !ieq(alt, sb.fx)) continue;
            n++;
            if (stop) {
                if (sb.every != null) { sb.every.stop(); sb.every = null; }
                sb.hiding = false;
                stop(sb);
            } else fxBegin(sb);
        }
        return n;
    }

    // ================================================================== visual states
    boolean hasStates(RadSwing.Item c) {
        for (Q q : qs) if (!q.form && q.c == c) return true;
        return false;
    }

    void wantAdd(RadSwing.Item c, boolean isForm, String st, List<String[]> w) {
        for (Q q : qs) {
            if (q.form != isForm || (!isForm && q.c != c) || !ieq(q.state, st)) continue;
            String[] hit = null;
            for (String[] x : w) if (ieq(x[0], q.prop)) { hit = x; break; }
            if (hit == null) w.add(new String[]{q.prop, q.val});
            else hit[1] = q.val;
        }
    }

    /** _VisualStates._update: the wanted overrides of a control (null = the form) applied, the others given back. */
    void vsmUpdate(RadSwing.Item c) {
        List<String[]> w = new ArrayList<>();
        if (!state.isEmpty()) wantAdd(c, c == null, state, w);
        if (c != null) {
            int fl = flags.containsKey(c) ? flags.get(c)[0] : 0;
            String man = manual.getOrDefault(c, "");
            if (!man.isEmpty()) wantAdd(c, false, man, w);
            else if ((fl & DISABLED) != 0) wantAdd(c, false, "Disabled", w);
            else {
                if ((fl & FOCUSED) != 0) wantAdd(c, false, "Focused", w);
                if ((fl & OVER) != 0) wantAdd(c, false, "MouseOver", w);
                if ((fl & PRESSED) != 0) wantAdd(c, false, "Pressed", w);
            }
        }
        for (Iterator<Ap> i = aps.iterator(); i.hasNext(); ) {     // overrides no longer wanted: the saved value back
            Ap a = i.next();
            if (a.c != c) continue;
            boolean want = false;
            for (String[] x : w) if (ieq(x[0], a.prop)) { want = true; break; }
            if (!want) {
                setStr(c, a.prop, a.saved, a.opaque);
                i.remove();
            }
        }
        for (String[] x : w) {
            Ap a = null;
            for (Ap o : aps) if (o.c == c && ieq(o.prop, x[0])) { a = o; break; }
            if (a != null && x[1].equals(a.val)) continue;
            if (a == null) {
                a = new Ap();
                a.c = c;
                a.prop = x[0];
                a.saved = getStr(c, x[0]);
                a.opaque = opaqueOf(c);
                aps.add(a);
            }
            a.val = x[1];
            setStr(c, x[0], x[1], null);
        }
    }

    void flag(RadSwing.Item c, int flag, boolean on) {
        if (c == null || !hasStates(c)) return;
        int[] fl = flags.computeIfAbsent(c, k -> new int[1]);
        if (((fl[0] & flag) != 0) == on) return;
        if (on) fl[0] |= flag;
        else fl[0] &= ~flag;
        vsmUpdate(c);
    }

    boolean stateKnown(String s) {
        for (Q q : qs) if (ieq(q.state, s)) return true;
        return false;
    }

    boolean gotoState(RadSwing.Item c, String st) {
        String s = st != null && !st.isEmpty() && !ieq(st, "Base") ? st : "Normal";
        if (c != null) {
            manual.put(c, ieq(s, "Normal") ? "" : s);
            vsmUpdate(c);
            return true;
        }
        if (!ieq(s, "Normal") && !stateKnown(s)) return false;
        state = ieq(s, "Normal") ? "" : s;
        vsmUpdate(null);
        Set<RadSwing.Item> done = Collections.newSetFromMap(new IdentityHashMap<>());
        for (Q q : qs) if (!q.form && q.c != null && done.add(q.c)) vsmUpdate(q.c);
        return true;
    }

    // ================================================================== layout variants
    static String postureNorm(String in) {
        StringBuilder b = new StringBuilder();
        for (char ch : (in == null ? "" : in).toCharArray()) if (ch != '-' && ch != '_' && ch != ' ') b.append(Character.toLowerCase(ch));
        switch (b.toString()) {
            case "halfopened": case "halfopen": case "half": case "tabletop": case "book": return "half-opened";
            case "folded": case "closed": case "fold": case "cover": return "folded";
            case "flat": case "open": case "opened": return "flat";
            default: return "";
        }
    }

    /** {posture, span, fold} of a simulated foldable (RADIDE_POSTURE, RADIDE_SPAN, RADIDE_HINGE=x,y,w,h). */
    static String[] venv() {
        String posture = postureNorm(System.getenv("RADIDE_POSTURE"));
        String sp = System.getenv("RADIDE_SPAN");
        String span = "", fold = "";
        if (sp != null) {
            sp = sp.trim().toLowerCase(Locale.ROOT);
            span = sp.equals("dual") || sp.equals("2") || sp.equals("spanned") ? "dual" : sp.isEmpty() ? "" : "single";
        }
        int[] hx = null;
        String h = System.getenv("RADIDE_HINGE");
        if (h != null) {
            String[] parts = h.split(",");
            if (parts.length == 4) {
                try {
                    hx = new int[4];
                    for (int i = 0; i < 4; i++) hx[i] = (int) Double.parseDouble(parts[i].trim());
                } catch (RuntimeException e) {
                    hx = null;
                }
            }
        }
        if (hx != null && !posture.equals("folded")) fold = hx[2] <= hx[3] ? "vertical" : "horizontal";
        if (span.isEmpty())
            span = posture.equals("half-opened") || (hx != null && !posture.equals("folded") && Math.min(hx[2], hx[3]) > 0) ? "dual" : "single";
        return new String[]{posture, span, fold};
    }

    static boolean match(Size s, double w, double h, String[] env) {
        if (s.mnw >= 0 && w < s.mnw) return false;
        if (s.mxw >= 0 && w > s.mxw) return false;
        if (s.mnh >= 0 && h < s.mnh) return false;
        if (s.mxh >= 0 && h > s.mxh) return false;
        if (!s.orient.isEmpty() && !s.orient.startsWith(w > h ? "land" : "port")) return false;
        if (!s.posture.isEmpty() && !s.posture.equals(env[0])) return false;
        if (!s.span.isEmpty() && !s.span.equals(env[1].isEmpty() ? "single" : env[1])) return false;
        if (!s.fold.isEmpty() && !s.fold.equals(env[2])) return false;
        return true;
    }

    /** _RadVariants.update: which sizes apply; restore the designed values, apply the sizes in order. */
    boolean variants(boolean notify) {
        if (sizes.isEmpty()) return false;
        double cw = form.client.getWidth(), ch = form.client.getHeight();
        if (cw <= 1 || ch <= 1) { cw = designW; ch = designH; }
        String[] env = venv();
        boolean[] now = new boolean[sizes.size()];
        for (int i = 0; i < now.length; i++) now[i] = match(sizes.get(i), cw, ch, env);
        if (cur != null && Arrays.equals(now, cur)) return false;
        boolean first = cur == null;
        cur = now;
        for (Map.Entry<RadSwing.Item, double[]> e : base.entrySet()) setPlace(e.getKey(), e.getValue());
        for (BP b : bps) setStr(b.c, b.prop, b.val, b.opaque);
        for (int j = 0; j < now.length; j++) {
            if (!now[j]) continue;
            for (VL v : vls) if (v.size == j) setPlace(v.c, v.pl);
            for (VP v : vps) if (v.size == j && !ieq(v.prop, "Visible")) setStr(v.c, v.prop, v.val, null);
            for (VP v : vps) if (v.size == j && ieq(v.prop, "Visible")) setStr(v.c, v.prop, v.val, null);
        }
        form.client.revalidate();
        form.client.repaint();
        if (!first && notify) SwingUtilities.invokeLater(() -> RadSwing.fire(form.radName, "SizeVariantChanged", null));
        return true;
    }

    String currentSizes() {
        StringBuilder b = new StringBuilder();
        for (int i = 0; cur != null && i < cur.length; i++)
            if (cur[i]) b.append(b.length() > 0 ? "," : "").append(sizes.get(i).id);
        return b.toString();
    }

    // ================================================================== hooks called by RadSwing
    /** The form is shown for the first time (after <Form>_Load): "On load" begins, "On timer" timers start. */
    void start() {
        if (started) return;
        started = true;
        for (Sb sb : sbs) {
            if (sb.on == T_LOAD) fxBegin(sb);
            else if (sb.on == T_TIMER && sb.interval > 0 && sb.every == null) {
                sb.every = new javax.swing.Timer(sb.interval, e -> fxBegin(sb));
                sb.every.start();
            }
        }
    }

    /** Events of the controls (and the form, c == null): triggers and automatic states. */
    void event(RadSwing.Item c, String ev) {
        String obj = c == null ? form.radName : c.name;
        if (ev.equals("Click") || ev.equals("MouseEnter") || ev.equals("MouseLeave")) {
            for (int i = 0; i < sbs.size(); i++) {
                Sb sb = sbs.get(i);
                boolean src = c == null ? sb.src.isEmpty() || ieq(sb.src, obj) : ieq(sb.src, obj);
                if (!src) continue;
                if (sb.on == T_CLICK && ev.equals("Click")) fxBegin(sb);
                else if (sb.on == T_HOVER && ev.equals("MouseEnter")) fxBegin(sb);
                else if (sb.on == T_HOVER && ev.equals("MouseLeave")) {
                    if (sb.leave == 0) reverse(sb);
                    else if (sb.leave == 1) { sb.hiding = false; stop(sb); }
                }
            }
        }
        if (c == null) return;
        switch (ev) {
            case "MouseEnter": flag(c, OVER, true); break;
            case "MouseLeave": flag(c, PRESSED, false); flag(c, OVER, false); break;
            case "MouseDown": flag(c, PRESSED, true); break;
            case "MouseUp": flag(c, PRESSED, false); break;
            case "GotFocus": flag(c, FOCUSED, true); break;
            case "LostFocus": flag(c, FOCUSED, false); break;
            default: break;
        }
    }

    /** A property set by the program: Visible plays "On show" / "On hide" (true = handled here). */
    boolean setHook(RadSwing.Item c, String p, String v) {
        if (c == null || !p.equals("visible")) return false;
        boolean on = Rad.toBool(v);
        if (on == c.shown) return false;
        int want = on ? T_SHOW : T_HIDE, n = 0;
        for (Sb sb : sbs) if (sb.c == c && sb.on == want) n++;
        if (n == 0) return false;
        if (on) write(c, "Visible", "True");
        for (int i = 0; i < sbs.size(); i++) {
            Sb sb = sbs.get(i);
            if (sb.c != c || sb.on != want) continue;
            if (!on) sb.hiding = true;
            fxBegin(sb);
        }
        return true;
    }

    /** After a property set by the program: Enabled -> the Disabled state. */
    void afterSet(RadSwing.Item c, String p, String v) {
        if (c != null && p.equals("enabled")) flag(c, DISABLED, !Rad.toBool(v));
    }

    /** BeginAnimation, StopAnimation, GoToState, ApplySizeVariants, CurrentSizes, CurrentState (null = not ours). */
    static String call(RadSwing.FormBase f, RadSwing.Item c, String m, String[] a) {
        RadMotion fx = f == null ? null : f.motion;
        String a0 = a != null && a.length > 0 ? a[0] : "";
        switch (m) {
            case "beginanimation":
            case "stopanimation":
                return RadSwing.b(fx != null && fx.byName(a0, m.equals("stopanimation")) > 0);
            case "gotostate": {
                if (fx == null) return "False";
                RadSwing.Item t = c;
                String ctl = a != null && a.length > 1 ? a[1] : "";
                if (t == null && !ctl.isEmpty()) {
                    t = fx.item(ctl);
                    if (t == null) return "False";
                }
                return RadSwing.b(fx.gotoState(t, a0));
            }
            default:
                break;
        }
        if (c != null) return null;
        switch (m) {
            case "applysizevariants": return RadSwing.b(fx != null && fx.variants(true));
            case "currentsizes": return fx == null ? "" : fx.currentSizes();
            case "currentstate": return fx == null || fx.state.isEmpty() ? "Normal" : fx.state;
            default: return null;
        }
    }
}
