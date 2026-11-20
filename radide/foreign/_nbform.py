"""NetBeans Swing GUI Builder forms (.form XML + the guarded blocks of the .java), opened in place.

* ``read_nbform(path) -> (Form, NbContext)``: components -> the neutral model. Positions come from
  AbsoluteLayout / null-layout constraints or from a small GroupLayout solver (Free Design).
* ``write_nbform(form_path, java_path, form) -> notes``: patches ONLY what changed into the .form
  (radide/foreign/_xmlspan.py keeps everything else byte for byte) and regenerates the
  ``//GEN-BEGIN:initComponents`` and ``//GEN-BEGIN:variables`` guarded blocks of the .java like
  NetBeans does (code outside the guarded blocks is never touched, except renames of a component).
  If the form uses something the generator does not know (custom code, resource bundles, unknown
  property editors...), structural edits are refused and only simple property edits are applied
  (to the .form and as literal patches inside initComponents) - reported in the notes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..controls import CONTROL_TYPES
from ..model import Control, Form
from . import _xmlspan as X
from ._others_base import read_text_keep, write_text_keep

SW = "javax.swing."
CLASS2TYPE = {
    "JButton": "Button", "JToggleButton": "Button", "JLabel": "Label", "JTextField": "TextBox",
    "JPasswordField": "TextBox", "JFormattedTextField": "TextBox", "JTextArea": "TextBox",
    "JEditorPane": "TextBox", "JTextPane": "TextBox", "JCheckBox": "CheckBox", "JRadioButton": "RadioButton",
    "JComboBox": "ComboBox", "JList": "ListBox", "JPanel": "Panel", "JScrollPane": "Panel",
    "JTabbedPane": "TabControl", "JProgressBar": "ProgressBar", "JSpinner": "NumericUpDown",
    "JSlider": "TrackBar", "JTree": "TreeView", "JTable": "DataGridView", "JMenuBar": "MenuStrip",
}
TYPE2CLASS = {"Button": "JButton", "Label": "JLabel", "TextBox": "JTextField", "CheckBox": "JCheckBox",
              "RadioButton": "JRadioButton", "ComboBox": "JComboBox", "ListBox": "JList", "Panel": "JPanel",
              "GroupBox": "JPanel", "ProgressBar": "JProgressBar", "NumericUpDown": "JSpinner",
              "TrackBar": "JSlider", "TreeView": "JTree", "DataGridView": "JTable", "LinkLabel": "JLabel",
              "PictureBox": "JLabel", "DateTimePicker": "JFormattedTextField", "TabControl": "JTabbedPane"}
TEXTLESS = {"JPanel", "JScrollPane", "JTabbedPane", "JProgressBar", "JSpinner", "JSlider", "JTree", "JTable",
            "JList", "JComboBox", "JMenuBar"}
# model prop -> (bean property, .form type)
SIMPLE = {"Enabled": ("enabled", "boolean"), "ToolTip": ("toolTipText", "java.lang.String"),
          "Checked": ("selected", "boolean")}
RANGE = {"Value": ("value", "int"), "Minimum": ("minimum", "int"), "Maximum": ("maximum", "int")}
# model event -> (listener, event method, event class)
EVENTS = {
    "Click": ("java.awt.event.ActionListener", "actionPerformed", "java.awt.event.ActionEvent"),
    "TextChanged": ("java.awt.event.KeyListener", "keyReleased", "java.awt.event.KeyEvent"),
    "CheckedChanged": ("java.awt.event.ItemListener", "itemStateChanged", "java.awt.event.ItemEvent"),
    "SelectedIndexChanged": ("java.awt.event.ActionListener", "actionPerformed", "java.awt.event.ActionEvent"),
    "ValueChanged": ("javax.swing.event.ChangeListener", "stateChanged", "javax.swing.event.ChangeEvent"),
    "DoubleClick": ("java.awt.event.MouseListener", "mouseClicked", "java.awt.event.MouseEvent"),
    "MouseClick": ("java.awt.event.MouseListener", "mouseClicked", "java.awt.event.MouseEvent"),
    "Load": ("java.awt.event.WindowListener", "windowOpened", "java.awt.event.WindowEvent"),
    "FormClosing": ("java.awt.event.WindowListener", "windowClosing", "java.awt.event.WindowEvent"),
}
LIST_SEL = ("javax.swing.event.ListSelectionListener", "valueChanged", "javax.swing.event.ListSelectionEvent")
ADAPTERS = {"java.awt.event.MouseListener": "java.awt.event.MouseAdapter",
            "java.awt.event.KeyListener": "java.awt.event.KeyAdapter",
            "java.awt.event.WindowListener": "java.awt.event.WindowAdapter",
            "java.awt.event.FocusListener": "java.awt.event.FocusAdapter",
            "java.awt.event.MouseMotionListener": "java.awt.event.MouseMotionAdapter",
            "java.awt.event.ComponentListener": "java.awt.event.ComponentAdapter"}
ABS = "org.netbeans.modules.form.compat2.layouts.DesignAbsoluteLayout"
SCROLL = "org.netbeans.modules.form.compat2.layouts.support.JScrollPaneSupportLayout"
TABBED = "org.netbeans.modules.form.compat2.layouts.support.JTabbedPaneSupportLayout"
CLOSE_OPS = {"0": "DO_NOTHING_ON_CLOSE", "1": "HIDE_ON_CLOSE", "2": "DISPOSE_ON_CLOSE", "3": "EXIT_ON_CLOSE"}
ALIGN = {"0": "LEADING", "1": "TRAILING", "2": "CENTER", "3": "BASELINE"}


@dataclass
class NbContext:
    data: bytes
    root: X.XNode
    comps: dict = field(default_factory=dict)       # name -> <Component>/<Container> node
    layout_of: dict = field(default_factory=dict)   # container name ("" = form) -> "group" | "abs" | "null" | other
    form_type: str = ""
    unsupported: list = field(default_factory=list)


def _short(cls: str) -> str:
    return cls.rsplit(".", 1)[-1]


def _props(node: X.XNode) -> dict:
    """name -> <Property> node."""
    out = {}
    ps = node.find("Properties")
    if ps is not None:
        for p in ps.findall("Property"):
            out[p.get("name", "")] = p
    return out


def _pval(p: X.XNode | None):
    if p is None:
        return None
    if "value" in p.attrib:
        return p.attrib["value"]
    return None


def _strings(p: X.XNode | None) -> list[str]:
    if p is None:
        return []
    sa = p.find("StringArray")
    if sa is None:
        return []
    return [i.get("value", "") for i in sa.findall("StringItem")]


def _title_border(p: X.XNode | None) -> X.XNode | None:
    if p is None:
        return None
    b = p.find("Border")
    if b is not None and "TitledBorder" in b.get("info", ""):
        return b.find("TitledBorder")
    return None


# ---------------------------------------------------------------- GroupLayout geometry

def _default_size(cls: str, text: str) -> tuple[int, int]:
    s = _short(cls)
    n = len(text or "")
    if s in ("JButton", "JToggleButton"):
        return max(7 * n + 32, 72), 23
    if s == "JLabel":
        return max(7 * n + 2, 10), 16
    if s in ("JCheckBox", "JRadioButton"):
        return 7 * n + 25, 20
    if s in ("JTextField", "JPasswordField", "JFormattedTextField"):
        return max(7 * n + 10, 64), 22
    if s == "JComboBox":
        return 72, 22
    if s in ("JSpinner",):
        return 64, 22
    if s in ("JSlider", "JProgressBar"):
        return 200, 20
    return 100, 100


class _Solver:
    """Positions of components in a GroupLayout from its <DimensionLayout> description."""

    def __init__(self, sizes: dict):
        self.sizes = sizes                # name -> (w, h) preferred
        self.pos: dict = {}               # (name, dim) -> (start, size)

    def comp_size(self, c: X.XNode, dim: int) -> int:
        pref = c.get("pref")
        if pref not in (None, "-1", "-2"):
            return int(pref)
        w, h = self.sizes.get(c.get("id", ""), (80, 22))
        return w if dim == 0 else h

    @staticmethod
    def gap(e: X.XNode, first_or_last: bool) -> int:
        pref = e.get("pref")
        if pref not in (None, "-1", "-2"):
            return int(pref)
        t = e.get("type")
        if t in ("separate", "unrelated"):
            return 12
        return 10 if first_or_last else 6

    def size(self, g: X.XNode, dim: int) -> int:
        if g.tag == "Component":
            return self.comp_size(g, dim)
        if g.tag == "EmptySpace":
            return self.gap(g, False)
        kids = [k for k in g.children if k.tag in ("Group", "Component", "EmptySpace")]
        if g.get("type") == "102":
            return sum(self.gap(k, i in (0, len(kids) - 1)) if k.tag == "EmptySpace" else self.size(k, dim)
                       for i, k in enumerate(kids))
        return max((self.size(k, dim) for k in kids), default=0)

    def place(self, g: X.XNode, dim: int, start: int, avail: int | None = None):
        if g.tag == "Component":
            sz = self.comp_size(g, dim)
            if avail is not None and g.get("max") == "32767":
                sz = max(sz, avail)
            self.pos[(g.get("id", ""), dim)] = (start, sz)
            return
        kids = [k for k in g.children if k.tag in ("Group", "Component", "EmptySpace")]
        if g.get("type") == "102":
            x = start
            for i, k in enumerate(kids):
                if k.tag == "EmptySpace":
                    x += self.gap(k, i in (0, len(kids) - 1))
                else:
                    self.place(k, dim, x)
                    x += self.size(k, dim)
            return
        total = avail if avail is not None else self.size(g, dim)
        galign = g.get("groupAlignment", "0")
        for k in kids:
            if k.tag == "EmptySpace":
                continue
            sz = self.size(k, dim)
            al = k.get("alignment", galign)
            off = total - sz if al == "1" else (total - sz) // 2 if al == "2" else 0
            self.place(k, dim, start + off, total if k.tag == "Group" or k.get("max") == "32767" else None)


def _group_positions(layout: X.XNode, sizes: dict) -> dict:
    s = _Solver(sizes)
    for dl in layout.findall("DimensionLayout"):
        dim = int(dl.get("dim", "0"))
        root = next((c for c in dl.children if c.tag == "Group"), None)
        if root is not None:
            s.place(root, dim, 0)
    out = {}
    for (name, dim), (st, sz) in s.pos.items():
        out.setdefault(name, [0, 0, 80, 22])
        if dim == 0:
            out[name][0], out[name][2] = st, sz
        else:
            out[name][1], out[name][3] = st, sz
    return out


def _layout_kind(cont: X.XNode) -> str:
    lay = cont.find("Layout")
    if lay is None:
        return "none"
    cls = lay.get("class")
    if cls is None:
        return "group"
    if cls == ABS:
        up = next((p for p in lay.findall("Property") if p.get("name") == "useNullLayout"), None)
        return "null" if up is not None and up.get("value") == "true" else "abs"
    if cls == SCROLL:
        return "scroll"
    if cls == TABBED:
        return "tabbed"
    return "other"


# ---------------------------------------------------------------- reading

def read_nbform(path: Path, name: str = "") -> tuple[Form, NbContext]:
    data = Path(path).read_bytes()
    root = X.parse(data)
    if root.tag != "Form":
        raise ValueError(f"{Path(path).name} is not a NetBeans form")
    ctx = NbContext(data, root, form_type=root.get("type", ""))
    form = Form()
    form.props["Name"] = name or Path(path).stem
    fp = _props(root)
    form.props["Text"] = _pval(fp.get("title")) or ""
    form.props["NativeClass"] = _short(ctx.form_type)
    events: dict = {}
    _collect_events(root, "", events)
    controls: list[Control] = []

    def walk(cont: X.XNode, parent: str, page=None):
        kind = _layout_kind(cont)
        ctx.layout_of[parent] = kind
        sub = cont.find("SubComponents")
        if sub is None:
            return
        kids = [k for k in sub.children if k.tag in ("Component", "Container", "MenuItem", "Menu")]
        sizes = {}
        for k in kids:
            pr = _props(k)
            sizes[k.get("name", "")] = _default_size(k.get("class", ""), _pval(pr.get("text")) or "")
        geo = {}
        lay = cont.find("Layout")
        if kind == "group" and lay is not None:
            geo = _group_positions(lay, sizes)
        for i, k in enumerate(kids):
            nm, cls = k.get("name", ""), k.get("class", "")
            ctx.comps[nm] = k
            short = _short(cls)
            pr = _props(k)
            tb = _title_border(pr.get("border"))
            mtype = CLASS2TYPE.get(short, "Panel")
            if short == "JPanel" and tb is not None:
                mtype = "GroupBox"
            ct = CONTROL_TYPES[mtype]
            props = ct.default_props(nm)
            props.update({"Parent": parent, "NativeId": nm, "NativeClass": cls})
            if page is not None:
                props["TabPage"] = i
            if mtype == "MenuStrip":
                props["Items"] = _menu(k)
            elif not ct.nonvisual:
                g = None
                if kind in ("abs", "null"):
                    ac = k.find("Constraints")
                    acn = next(ac.iter("AbsoluteConstraints"), None) if ac is not None else None
                    if acn is not None:
                        w, h = int(acn.get("width", "-1")), int(acn.get("height", "-1"))
                        dw, dh = sizes[nm]
                        g = [int(acn.get("x", "0")), int(acn.get("y", "0")), dw if w < 0 else w, dh if h < 0 else h]
                elif kind == "scroll":
                    pw, ph = 0, 0
                    pc = ctx.comps.get(parent)
                    pg = next((c for c in controls if c.name == parent), None)
                    if pg is not None:
                        pw, ph = pg.props["Width"], pg.props["Height"]
                    g = [0, 0, pw, ph] if pc is not None else None
                elif kind == "tabbed":
                    pg = next((c for c in controls if c.name == parent), None)
                    if pg is not None:
                        g = [0, 0, max(pg.props["Width"] - 10, 10), max(pg.props["Height"] - 30, 10)]
                else:
                    g = geo.get(nm)
                if g:
                    props["Left"], props["Top"], props["Width"], props["Height"] = g
                if kind not in ("abs", "null", "group"):
                    props["NativeLayout"] = True
            if ct.has_text and short not in TEXTLESS:
                props["Text"] = _pval(pr.get("text")) or ""
            if mtype == "GroupBox":
                props["Text"] = tb.get("title", "") if tb is not None else ""
            for mp, (bp, _t) in SIMPLE.items():
                if mp in props and _pval(pr.get(bp)) is not None:
                    v = _pval(pr.get(bp))
                    props[mp] = v if _t == "java.lang.String" else v == "true"
            for mp, (bp, _t) in RANGE.items():
                if mp in props and _pval(pr.get(bp)) is not None:
                    try:
                        props[mp] = int(_pval(pr.get(bp)))
                    except ValueError:
                        pass
            if short in ("JTextArea", "JEditorPane", "JTextPane"):
                props["Multiline"] = True
            if mtype in ("ComboBox", "ListBox"):
                props["Items"] = ";".join(_strings(pr.get("model")))
            controls.append(Control(mtype, props))
            if k.tag == "Container":
                walk(k, nm, page=True if _layout_kind(k) == "tabbed" else None)
                if _layout_kind(k) == "tabbed":
                    titles = []
                    for kk in (k.find("SubComponents").children if k.find("SubComponents") is not None else []):
                        c = kk.find("Constraints")
                        tn = next(c.iter("JTabbedPaneConstraints"), None) if c is not None else None
                        titles.append(tn.get("tabTitle", kk.get("name", "")) if tn is not None else kk.get("name", ""))
                    props["TabPages"] = ";".join(titles)

    walk(root, "")
    xs = [c for c in controls if not c.ctype.nonvisual and not c.parent]
    if xs:
        form.props["Width"] = max(c.props["Left"] + c.props["Width"] for c in xs) + 16
        form.props["Height"] = max(c.props["Top"] + c.props["Height"] for c in xs) + 40
    fs = _synthetic(root).get("formSize")
    if fs is not None:
        m = re.search(r"(\d+),\s*(\d+)", fs)
        if m:
            form.props["Width"], form.props["Height"] = int(m.group(1)), int(m.group(2))
    form.controls = controls
    form.extra["NativeEvents"] = events
    ctx.unsupported = _unsupported(root)
    return form, ctx


def _synthetic(root: X.XNode) -> dict:
    out = {}
    sp = root.find("SyntheticProperties")
    if sp is not None:
        for p in sp.findall("SyntheticProperty"):
            out[p.get("name", "")] = p.get("value")
    return out


def _collect_events(node: X.XNode, owner: str, out: dict) -> None:
    ev = node.find("Events")
    if ev is not None:
        for h in ev.findall("EventHandler"):
            out.setdefault(owner or "form", {})[h.get("event", "")] = {
                "listener": h.get("listener", ""), "parameters": h.get("parameters", ""),
                "handler": h.get("handler", "")}
    sub = node.find("SubComponents")
    if sub is not None:
        for k in sub.children:
            if k.tag in ("Component", "Container", "Menu", "MenuItem"):
                _collect_events(k, k.get("name", ""), out)


def _menu(node: X.XNode) -> list:
    items = []
    sub = node.find("SubComponents")
    for k in (sub.children if sub is not None else []):
        if k.tag not in ("Menu", "MenuItem", "Component"):
            continue
        pr = _props(k)
        if _short(k.get("class", "")) == "JPopupMenu$Separator":
            items.append({"Text": "-", "Name": "", "Items": []})
            continue
        items.append({"Text": _pval(pr.get("text")) or k.get("name", ""), "Name": k.get("name", ""),
                      "Items": _menu(k) if k.tag == "Menu" else []})
    return items


# ---------------------------------------------------------------- what the generator supports

_KNOWN_EDITOR_TAGS = {"Font", "Color", "StringArray", "Border", "ComponentRef"}


def _unsupported(root: X.XNode) -> list[str]:
    out = []
    for n in root.iter("AuxValue"):
        nm = n.get("name", "")
        if nm.startswith("JavaCodeGenerator_") and nm not in (
                "JavaCodeGenerator_VariableModifier", "JavaCodeGenerator_VariableLocal",
                "JavaCodeGenerator_TypeParameters", "JavaCodeGenerator_SerializeTo") and n.get("value") not in ("", None):
            out.append(f"custom code ({nm})")
        if nm == "FormSettings_listenerGenerationStyle" and n.get("value") not in ("0", None):
            out.append("listener generation style is not 'anonymous inner classes'")
        if nm == "FormSettings_layoutCodeTarget" and n.get("value") not in ("1", "0", None):
            out.append("layout code target")
    for p in root.iter("Property"):
        if p.parent is not None and p.parent.tag == "Layout":
            continue
        if "value" in p.attrib:
            continue
        kids = {c.tag for c in p.children}
        if not kids or not kids <= _KNOWN_EDITOR_TAGS:
            out.append(f"property '{p.get('name')}' ({', '.join(sorted(kids)) or 'custom editor'})")
        elif "Border" in kids and _title_border(p) is None:
            out.append(f"border of '{p.parent.parent.get('name') if p.parent and p.parent.parent else ''}'")
        elif "Font" in kids and p.find("Font").get("component"):
            pass
    for t in ("ResourceString", "Connection", "FontInfo", "Table", "SerializedValue", "Image"):
        if next(root.iter(t), None) is not None:
            out.append(f"<{t}> values")
    for c in root.iter("Container"):
        if _layout_kind(c) == "other":
            out.append(f"layout of {c.get('name')} ({c.find('Layout').get('class')})")
    if _layout_kind(root) == "other":
        out.append(f"form layout ({root.find('Layout').get('class')})")
    return sorted(set(out))


# ---------------------------------------------------------------- Java code generation

def _jstr(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t") + '"'


def _setter(name: str) -> str:
    return "set" + name[:1].upper() + name[1:]


def _prop_code(var: str, p: X.XNode) -> list[str]:
    """Java statements for one <Property> (var = "" for the form itself)."""
    nm, tp = p.get("name", ""), p.get("type", "")
    tgt = f"{var}." if var else ""
    v = p.get("value")
    if nm == "defaultCloseOperation" and v is not None:
        return [f"{tgt}setDefaultCloseOperation(javax.swing.WindowConstants.{CLOSE_OPS.get(v, 'EXIT_ON_CLOSE')});"]
    if v is not None:
        if tp == "java.lang.String":
            lit = _jstr(v)
        elif tp == "char":
            lit = "'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'"
        elif tp in ("float",):
            lit = v + "F"
        else:
            lit = v
        return [f"{tgt}{_setter(nm)}({lit});"]
    f = p.find("Font")
    if f is not None:
        return [f'{tgt}setFont(new java.awt.Font({_jstr(f.get("name", "Dialog"))}, {f.get("style", "0")}, '
                f'{f.get("size", "12")})); // NOI18N']
    c = p.find("Color")
    if c is not None:
        if c.get("type") == "palette" or c.get("id"):
            return [f'{tgt}{_setter(nm)}(javax.swing.UIManager.getDefaults().getColor({_jstr(c.get("id", ""))}));']
        rgb = [int(c.get(k, "0"), 16) for k in ("red", "green", "blue")]
        return [f"{tgt}{_setter(nm)}(new java.awt.Color({rgb[0]}, {rgb[1]}, {rgb[2]}));"]
    if p.find("StringArray") is not None:
        items = ", ".join(_jstr(s) for s in _strings(p))
        if "ListModel" in tp:
            return [f"{tgt}setModel(new javax.swing.AbstractListModel<String>() {{",
                    f"    String[] strings = {{ {items} }};",
                    "    public int getSize() { return strings.length; }",
                    "    public String getElementAt(int i) { return strings[i]; }",
                    "});"]
        return [f"{tgt}setModel(new javax.swing.DefaultComboBoxModel<>(new String[] {{ {items} }}));"]
    tb = _title_border(p)
    if tb is not None:
        return [f"{tgt}setBorder(javax.swing.BorderFactory.createTitledBorder({_jstr(tb.get('title', ''))}));"]
    cr = p.find("ComponentRef")
    if cr is not None:
        return [f"{tgt}{_setter(nm)}({cr.get('name', 'null')});"]
    return []


def _listener_code(var: str, handlers: list[tuple[str, str, str, str]]) -> list[str]:
    """handlers: (event method, listener, parameters, handler) of one component."""
    out = []
    tgt = f"{var}." if var else ""
    by_listener: dict = {}
    for ev, lis, par, h in handlers:
        by_listener.setdefault(lis, []).append((ev, par, h))
    for lis, evs in by_listener.items():
        simple = lis.rsplit(".", 1)[-1]
        cls = ADAPTERS.get(lis, lis) if (len(evs) < 2 or lis in ADAPTERS) else lis
        out.append(f"{tgt}add{simple}(new {cls}() {{")
        for ev, par, h in evs:
            out += [f"    public void {ev}({par} evt) {{", f"        {h}(evt);", "    }"]
        out.append("});")
    return out


def _size_arg(v: str | None) -> str:
    if v in (None, "-1"):
        return "javax.swing.GroupLayout.DEFAULT_SIZE"
    if v == "-2":
        return "javax.swing.GroupLayout.PREFERRED_SIZE"
    if v == "32767":
        return "Short.MAX_VALUE"
    return v


# components whose maximum size is their preferred size: NetBeans writes plain addComponent(c) for them
FIXED_SIZE = {"JLabel", "JButton", "JCheckBox", "JRadioButton", "JToggleButton"}


def _group_code(g: X.XNode, L: str, parent_align: str | None, depth: int, edge: bool,
                classes: dict | None = None) -> list[str]:
    classes = classes or {}
    ind = "    " * depth
    if g.get("type") == "102":
        head = f"{L}.createSequentialGroup()"
    else:
        al = ALIGN.get(g.get("groupAlignment", "0"), "LEADING")
        head = f"{L}.createParallelGroup(javax.swing.GroupLayout.Alignment.{al}" + \
            (", false" if g.get("max") == "-2" else "") + ")"
    lines = [head]
    kids = [k for k in g.children if k.tag in ("Group", "Component", "EmptySpace")]
    seq = g.get("type") == "102"
    galign = g.get("groupAlignment", "0")
    for i, k in enumerate(kids):
        alpre = ""
        if not seq and k.get("alignment") is not None and k.get("alignment") != galign:
            alpre = f"javax.swing.GroupLayout.Alignment.{ALIGN.get(k.get('alignment'), 'LEADING')}, "
        if k.tag == "Component":
            mn, pf, mx = k.get("min"), k.get("pref"), k.get("max")
            plain = pf is None and mn in (None, "-2") and mx in (None, "-2") and                 _short(classes.get(k.get("id"), "")) in FIXED_SIZE
            if (mn is None and pf is None and mx is None) or plain:
                lines.append(f"{ind}.addComponent({alpre}{k.get('id')})")
            else:
                lines.append(f"{ind}.addComponent({alpre}{k.get('id')}, {_size_arg(mn)}, {_size_arg(pf)}, "
                             f"{_size_arg(mx)})")
        elif k.tag == "EmptySpace":
            mn, pf, mx, t = k.get("min"), k.get("pref"), k.get("max"), k.get("type")
            if t in ("separate", "unrelated", "indent"):
                kind = {"separate": "UNRELATED", "unrelated": "UNRELATED", "indent": "INDENT"}[t]
                extra = "" if pf is None and mx in (None, "-2") else f", {_size_arg(pf)}, {_size_arg(mx)}"
                lines.append(f"{ind}.addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.{kind}{extra})")
            elif pf is None and seq:
                extra = "" if mx in (None, "-2") else f"{_size_arg(pf)}, {_size_arg(mx)}"
                if edge and i in (0, len(kids) - 1):
                    lines.append(f"{ind}.addContainerGap({extra})")
                else:
                    lines.append(f"{ind}.addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED"
                                 f"{', ' + extra if extra else ''})")
            else:
                p = pf if pf is not None else "0"
                a = p if mn in (None, "-2") else mn
                b = p if mx in (None, "-2") else _size_arg(mx)
                lines.append(f"{ind}.addGap({a}, {p}, {b})")
        else:
            sub = _group_code(k, L, galign, depth + 1, edge and not seq, classes)
            sub[0] = f"{ind}.addGroup({alpre}{sub[0]}"
            sub[-1] = sub[-1] + ")"
            lines += sub
    return lines


def _layout_code(cont: X.XNode, var: str, form_type: str) -> list[str]:
    kind = _layout_kind(cont)
    is_form = cont.tag == "Form"
    target = ("getContentPane()" if "Panel" not in form_type else "this") if is_form else var
    out = []
    sub = cont.find("SubComponents")
    kids = [k for k in (sub.children if sub is not None else []) if k.tag in ("Component", "Container")
            and CLASS2TYPE.get(_short(k.get("class", ""))) != "MenuStrip"]
    if kind == "group":
        L = "layout" if is_form else f"{var}Layout"
        out += [f"javax.swing.GroupLayout {L} = new javax.swing.GroupLayout({target});",
                f"{target}.setLayout({L});"]
        for dl in cont.find("Layout").findall("DimensionLayout"):
            root = next((c for c in dl.children if c.tag == "Group"), None)
            if root is None:
                continue
            setter = "setHorizontalGroup" if dl.get("dim") == "0" else "setVerticalGroup"
            classes = {c.get("name"): c.get("class", "") for c in _all_components(cont)}
            body = _group_code(root, L, None, 1, True, classes)
            out += [f"{L}.{setter}(", "    " + body[0]] + body[1:] + [");"]
    elif kind in ("abs", "null"):
        if kind == "abs":
            out.append(f"{target}.setLayout(new org.netbeans.lib.awtextra.AbsoluteLayout());")
        else:
            out.append(f"{target}.setLayout(null);")
        for k in kids:
            c = k.find("Constraints")
            a = next(c.iter("AbsoluteConstraints"), None) if c is not None else None
            x, y = (a.get("x", "0"), a.get("y", "0")) if a is not None else ("0", "0")
            w, h = (a.get("width", "-1"), a.get("height", "-1")) if a is not None else ("-1", "-1")
            n = k.get("name")
            if kind == "abs":
                out.append(f"{target}.add({n}, new org.netbeans.lib.awtextra.AbsoluteConstraints({x}, {y}, {w}, {h}));")
            else:
                ww = f"{n}.getPreferredSize().width" if w == "-1" else w
                hh = f"{n}.getPreferredSize().height" if h == "-1" else h
                out += [f"{target}.add({n});", f"{n}.setBounds({x}, {y}, {ww}, {hh});"]
    elif kind == "scroll" and kids:
        out.append(f"{var}.setViewportView({kids[0].get('name')});")
    elif kind == "tabbed":
        for k in kids:
            c = k.find("Constraints")
            t = next(c.iter("JTabbedPaneConstraints"), None) if c is not None else None
            title = t.get("tabTitle", "tab") if t is not None else k.get("name")
            out.append(f"{var}.addTab({_jstr(title)}, {k.get('name')});")
    return out


def _all_components(node: X.XNode) -> list[X.XNode]:
    out = []
    sub = node.find("SubComponents")
    for k in (sub.children if sub is not None else []):
        if k.tag in ("Component", "Container", "Menu", "MenuItem"):
            out.append(k)
            out += _all_components(k)
    return out


def _decl_type(k: X.XNode) -> str:
    cls = k.get("class", "")
    if _short(cls) in ("JComboBox", "JList"):
        tp = next((a.get("value") for a in k.iter("AuxValue") if a.get("name") == "JavaCodeGenerator_TypeParameters"),
                  None)
        return f"{cls}{tp or '<String>'}"
    return cls


def _comp_code(k: X.XNode) -> list[str]:
    """Properties, listeners, children and layout of one component (NetBeans order)."""
    var = k.get("name", "")
    out = []
    for p in _props(k).values():
        out += _prop_code(var, p)
    out += _listener_code(var, _handlers(k))
    kids = _direct(k)
    for c in kids:
        sub = _comp_code(c)
        if sub:
            out += sub
    if k.tag in ("Container", "Menu"):
        if CLASS2TYPE.get(_short(k.get("class", ""))) == "MenuStrip" or k.tag == "Menu":
            for c in kids:
                out.append(f"{var}.add({c.get('name')});")
        else:
            out += _layout_code(k, var, "")
    if out:
        out.append("")
    return out


def _direct(node: X.XNode) -> list[X.XNode]:
    sub = node.find("SubComponents")
    return [k for k in (sub.children if sub is not None else []) if k.tag in ("Component", "Container", "Menu",
                                                                            "MenuItem")]


def _handlers(node: X.XNode) -> list[tuple]:
    ev = node.find("Events")
    if ev is None:
        return []
    return [(h.get("event", ""), h.get("listener", ""), h.get("parameters", ""), h.get("handler", ""))
            for h in ev.findall("EventHandler")]


def generate_init(root: X.XNode) -> tuple[list[str], list[str]]:
    """(initComponents body lines, variable declaration lines) - indentation added by the caller."""
    ft = root.get("type", "")
    comps = _all_components(root)
    body = [""]
    for k in comps:
        cls = k.get("class", "")
        body.append(f"{k.get('name')} = new {_decl_type(k) if '<' not in _decl_type(k) else cls + '<>'}();")
    body.append("")
    fprops = [ln for p in _props(root).values() for ln in _prop_code("", p)]
    fl = _listener_code("", _handlers(root))
    if fprops or fl:
        body += fprops + fl + [""]
    menubar = None
    for k in _direct(root):
        if CLASS2TYPE.get(_short(k.get("class", ""))) == "MenuStrip":
            menubar = k
        body += _comp_code(k)
    if menubar is not None:
        body += [f"setJMenuBar({menubar.get('name')});", ""]
    body += _layout_code(root, "", ft)
    syn = _synthetic(root)
    if "Panel" not in ft:
        policy = syn.get("formSizePolicy", "1")
        if policy == "1":
            body += ["", "pack();"]
        elif policy == "0" and syn.get("formSize"):
            m = re.search(r"(\d+),\s*(\d+)", syn["formSize"])
            if m:
                body += ["", f"setSize(new java.awt.Dimension({m.group(1)}, {m.group(2)}));"]
        if syn.get("generateCenter") == "true":
            body.append("setLocationRelativeTo(null);")
    while body and body[-1] == "":
        body.pop()
    decls = []
    for k in sorted(comps, key=lambda n: n.get("name", "")):
        mod = next((a.get("value") for a in k.iter("AuxValue") if a.get("name") == "JavaCodeGenerator_VariableModifier"
                    and a.parent is not None and a.parent.parent is k), None)
        m = {"1": "public", "2": "private", "4": "protected", "0": ""}.get(mod or "2", "private")
        decls.append(f"{m + ' ' if m else ''}{_decl_type(k)} {k.get('name')};")
    return body, decls


def replace_guarded(java: str, body: list[str], decls: list[str]) -> str:
    """Replace the bodies of the initComponents and variables guarded blocks."""
    lines = java.split("\n")
    bi = next((i for i, ln in enumerate(lines) if "//GEN-BEGIN:initComponents" in ln), -1)
    ei = next((i for i, ln in enumerate(lines) if "//GEN-END:initComponents" in ln), -1)
    if bi < 0 or ei < bi:
        raise ValueError("the .java has no //GEN-BEGIN:initComponents ... //GEN-END:initComponents block")
    mi = next((i for i in range(bi, ei + 1) if re.search(r"\binitComponents\s*\(\s*\)\s*\{", lines[i])), bi)
    base = re.match(r"\s*", lines[mi]).group(0) if mi != bi else re.match(r"\s*", lines[bi]).group(0)
    inner = base + "    "
    new_body = [inner + ln if ln else "" for ln in body]
    end_line = lines[ei]
    head = lines[:mi + 1]
    if mi == bi:                          # "private void initComponents() {//GEN-BEGIN..." style
        head = lines[:bi + 1]
    lines = head + new_body + [end_line] + lines[ei + 1:]
    vb = next((i for i, ln in enumerate(lines) if "//GEN-BEGIN:variables" in ln), -1)
    ve = next((i for i, ln in enumerate(lines) if "//GEN-END:variables" in ln), -1)
    if vb >= 0 and ve > vb:
        vind = re.match(r"\s*", lines[vb]).group(0)
        lines = lines[:vb + 1] + [vind + d for d in decls] + lines[ve:]
    return "\n".join(lines)


def handler_stub(handler: str, params: str, indent: str = "    ") -> list[str]:
    return [f"{indent}private void {handler}({params} evt) {{//GEN-FIRST:event_{handler}",
            f"{indent}    // TODO add your handling code here:",
            f"{indent}}}//GEN-LAST:event_{handler}", ""]


# ---------------------------------------------------------------- writing

def _form_lines_for(c: Control, kind: str) -> list[str]:
    cls = c.props.get("NativeClass") or SW + TYPE2CLASS.get(c.type, "JPanel")
    short = _short(cls)
    tag = "Container" if c.ctype.container and short not in TEXTLESS - {"JPanel", "JScrollPane", "JTabbedPane"} \
        else "Component"
    if short not in ("JPanel", "JScrollPane", "JTabbedPane"):
        tag = "Component"
    props = []
    if c.type == "GroupBox":
        props += ['<Property name="border" type="javax.swing.border.Border" '
                  'editor="org.netbeans.modules.form.editors2.BorderEditor">',
                  ' <Border info="org.netbeans.modules.form.compat2.border.TitledBorderInfo">',
                  f'  <TitledBorder title="{X.escape_attr(c.props.get("Text", ""))}"/>', " </Border>", "</Property>"]
    elif c.ctype.has_text and short not in TEXTLESS:
        props.append(f'<Property name="text" type="java.lang.String" value="{X.escape_attr(c.props.get("Text", ""))}"/>')
    d = c.ctype.default_props(c.name)
    for mp, (bp, t) in {**SIMPLE, **RANGE}.items():
        if mp in c.props and c.props[mp] != d.get(mp):
            v = c.props[mp]
            v = ("true" if v else "false") if t == "boolean" else str(v)
            props.append(f'<Property name="{bp}" type="{t}" value="{X.escape_attr(v)}"/>')
    if c.type in ("ComboBox", "ListBox"):
        items = [s for s in str(c.props.get("Items", "")).split(";") if s]
        if items:
            props += _model_lines(c.type, items)
    lines = [f'<{tag} class="{cls}" name="{X.escape_attr(c.name)}">']
    if props:
        lines += [" <Properties>"] + ["  " + p for p in props] + [" </Properties>"]
    if short in ("JComboBox", "JList"):
        lines += [" <AuxValues>", '  <AuxValue name="JavaCodeGenerator_TypeParameters" type="java.lang.String" '
                  'value="&lt;String&gt;"/>', " </AuxValues>"]
    if kind in ("abs", "null"):
        lines += [" <Constraints>", f'  <Constraint layoutClass="{ABS}" value="{ABS}$AbsoluteConstraintsDescription">',
                  f'   <AbsoluteConstraints x="{int(c.props.get("Left", 0))}" y="{int(c.props.get("Top", 0))}" '
                  f'width="{int(c.props.get("Width", -1))}" height="{int(c.props.get("Height", -1))}"/>',
                  "  </Constraint>", " </Constraints>"]
    if tag == "Container":
        lines += [f' <Layout class="{ABS}">', '  <Property name="useNullLayout" type="boolean" value="false"/>',
                  " </Layout>"]
    lines.append(f"</{tag}>")
    return lines


def _model_lines(mtype: str, items: list[str]) -> list[str]:
    if mtype == "ComboBox":
        head = '<Property name="model" type="javax.swing.ComboBoxModel" ' \
               'editor="org.netbeans.modules.form.editors2.ComboBoxModelEditor">'
    else:
        head = '<Property name="model" type="javax.swing.ListModel" ' \
               'editor="org.netbeans.modules.form.editors2.ListModelEditor">'
    return [head, f' <StringArray count="{len(items)}">'] + \
        [f'  <StringItem index="{i}" value="{X.escape_attr(s)}"/>' for i, s in enumerate(items)] + \
        [" </StringArray>", "</Property>"]


def _abs_group_layout(children: list[Control]) -> list[str]:
    """A Free Design GroupLayout that places every child at its designer position."""
    out = ["<Layout>"]
    for dim, (pk, sk) in enumerate((("Left", "Width"), ("Top", "Height"))):
        out += [f' <DimensionLayout dim="{dim}">', '  <Group type="103" groupAlignment="0" attributes="0">']
        for c in children:
            p, s = int(c.props.get(pk, 0)), int(c.props.get(sk, 20))
            out += ['   <Group type="102" alignment="0" attributes="0">',
                    f'    <EmptySpace min="-2" pref="{p}" max="-2" attributes="0"/>',
                    f'    <Component id="{X.escape_attr(c.name)}" min="-2" pref="{s}" max="-2" attributes="0"/>',
                    '    <EmptySpace max="32767" attributes="0"/>', "   </Group>"]
        out += ["  </Group>", " </DimensionLayout>"]
    out.append("</Layout>")
    return out


def _set_property(patch: X.Patch, comp: X.XNode, bp: str, tp: str, value: str) -> None:
    pr = _props(comp)
    if bp in pr and "value" in pr[bp].attrib:
        patch.set_attr(pr[bp], "value", value)
        return
    line = f'<Property name="{bp}" type="{tp}" value="{X.escape_attr(value)}"/>'
    ps = comp.find("Properties")
    if bp in pr:
        patch.remove(pr[bp])
        patch.append_child(ps, [line])
    elif ps is not None:
        patch.append_child(ps, [line])
    else:
        patch.append_child(comp, ["<Properties>", " " + line, "</Properties>"],
                           before=comp.children[0] if comp.children else None)


def write_nbform(form_path: Path, java_path: Path | None, form: Form) -> list[str]:
    form_path = Path(form_path)
    old, ctx = read_nbform(form_path, form.name)
    notes: list[str] = []
    patch = X.Patch(ctx.data)
    old_by = {c.props["NativeId"]: c for c in old.controls if c.props.get("NativeId")}
    kept, new, seen = {}, [], set()
    for c in form.controls:
        nid = c.props.get("NativeId")
        if nid in old_by and nid not in seen:
            seen.add(nid)
            kept[nid] = c
        else:
            new.append(c)
    removed = [n for n in old_by if n not in kept]
    structural, simple_edits, renames = [], [], {}
    regroup: set = set()                      # containers whose GroupLayout is rebuilt
    literal: list[tuple[str, str, str]] = []  # (var, setter, java literal) for patch mode
    # --- form title
    if form.props.get("Text") != old.props.get("Text"):
        _set_property(patch, ctx.root, "title", "java.lang.String", form.props.get("Text", ""))
        literal.append(("", "setTitle", _jstr(form.props.get("Text", ""))))
        simple_edits.append("title")
    for nid, c in kept.items():
        o, comp = old_by[nid], ctx.comps[nid]
        short = _short(comp.get("class", ""))
        if c.name != nid:
            patch.set_attr(comp, "name", c.name)
            renames[nid] = c.name
            structural.append(f"rename {nid} -> {c.name}")
        if (c.parent, c.props.get("TabPage")) != (o.parent, o.props.get("TabPage")):
            notes.append(f"{form_path.name}: {c.name} moved to another container - not written")
        g_new = [int(c.props.get(k, 0) or 0) for k in ("Left", "Top", "Width", "Height")]
        g_old = [int(o.props.get(k, 0) or 0) for k in ("Left", "Top", "Width", "Height")]
        kind = ctx.layout_of.get(o.parent, "none")
        if g_new != g_old and not c.ctype.nonvisual:
            if kind in ("abs", "null"):
                ac = comp.find("Constraints")
                a = next(ac.iter("AbsoluteConstraints"), None) if ac is not None else None
                if a is not None:
                    for key, nv, ov in zip(("x", "y", "width", "height"), g_new, g_old):
                        if nv != ov:
                            patch.set_attr(a, key, str(nv))
                    structural.append(f"move {c.name}")
            elif kind == "group":
                regroup.add(o.parent)
                structural.append(f"move {c.name}")
            else:
                notes.append(f"{form_path.name}: {c.name} is placed by its container - position not written")
        if c.ctype.has_text and c.props.get("Text") != o.props.get("Text"):
            if c.type == "GroupBox":
                tb = _title_border(_props(comp).get("border"))
                if tb is not None:
                    patch.set_attr(tb, "title", c.props.get("Text", ""))
                    structural.append(f"border title of {c.name}")
            elif short not in TEXTLESS:
                _set_property(patch, comp, "text", "java.lang.String", c.props.get("Text", ""))
                literal.append((nid, "setText", _jstr(c.props.get("Text", ""))))
                simple_edits.append(f"{c.name}.text")
        for mp, (bp, t) in {**SIMPLE, **RANGE}.items():
            if mp in c.props and c.props.get(mp) != o.props.get(mp):
                v = c.props[mp]
                sv = ("true" if v else "false") if t == "boolean" else str(v)
                _set_property(patch, comp, bp, t, sv)
                literal.append((nid, _setter(bp), _jstr(sv) if t == "java.lang.String" else sv))
                simple_edits.append(f"{c.name}.{bp}")
        if c.type in ("ComboBox", "ListBox") and c.props.get("Items", "") != o.props.get("Items", ""):
            items = [s for s in str(c.props.get("Items", "")).split(";") if s]
            pm = _props(comp).get("model")
            lines = _model_lines(c.type, items)
            if pm is not None:
                patch.remove(pm)
            ps = comp.find("Properties")
            if ps is not None:
                patch.append_child(ps, lines)
            else:
                patch.append_child(comp, ["<Properties>"] + [" " + ln for ln in lines] + ["</Properties>"],
                                   before=comp.children[0] if comp.children else None)
            structural.append(f"items of {c.name}")
    # --- removed
    for nid in removed:
        comp = ctx.comps.get(nid)
        if comp is None or any(a.get("name") in removed for a in comp.ancestors() if a.tag == "Container"):
            continue
        patch.remove(comp)
        o = old_by[nid]
        if ctx.layout_of.get(o.parent) == "group":
            regroup.add(o.parent)
        structural.append(f"remove {nid}")
    # --- new
    for c in new:
        if c.ctype.nonvisual:
            notes.append(f"{form_path.name}: {c.type} {c.name} has no Swing GUI Builder equivalent - not written")
            continue
        par_id = next((n for n, k in kept.items() if k.name == c.parent), c.parent)
        host = ctx.root if not par_id else ctx.comps.get(par_id)
        kind = ctx.layout_of.get(par_id, "none")
        if host is None or kind not in ("abs", "null", "group", "none"):
            notes.append(f"{form_path.name}: no place for new control {c.name} - not written")
            continue
        lines = _form_lines_for(c, kind)
        sub = host.find("SubComponents")
        if sub is not None:
            patch.append_child(sub, lines)
        else:
            patch.append_child(host, ["<SubComponents>"] + [" " + ln for ln in lines] + ["</SubComponents>"])
        if kind in ("group", "none"):
            regroup.add(par_id)
        structural.append(f"add {c.name}")
    # --- events added in the designer (form.extra["NativeEvents"])
    new_ev = form.extra.get("NativeEvents") or {}
    old_ev = old.extra.get("NativeEvents") or {}
    for owner, evs in new_ev.items():
        for ev, info in evs.items():
            if ev in old_ev.get(owner, {}):
                continue
            node = ctx.root if owner == "form" else ctx.comps.get(next((n for n, k in kept.items() if k.name == owner),
                                                                       owner))
            if node is None:
                continue
            line = (f'<EventHandler event="{ev}" listener="{info["listener"]}" parameters="{info["parameters"]}" '
                    f'handler="{info["handler"]}"/>')
            evn = node.find("Events")
            if evn is not None:
                patch.append_child(evn, [line])
            else:
                before = next((ch for ch in node.children if ch.tag in ("AuxValues", "Constraints", "Layout",
                                                                         "SubComponents")), None)
                patch.append_child(node, ["<Events>", " " + line, "</Events>"], before=before)
            structural.append(f"event {info['handler']}")
    # --- renames inside layouts / component refs
    if renames:
        for n in ctx.root.iter("Component"):
            if n.get("id") in renames:
                patch.set_attr(n, "id", renames[n.get("id")])
        for n in ctx.root.iter("ComponentRef"):
            if n.get("name") in renames:
                patch.set_attr(n, "name", renames[n.get("name")])
    # --- rebuilt Free Design layouts
    for cont_id in regroup:
        host = ctx.root if not cont_id else ctx.comps.get(cont_id)
        if host is None:
            continue
        cname = next((k.name for n, k in kept.items() if n == cont_id), cont_id)
        kids = [k for k in form.controls if k.parent == cname and not k.ctype.nonvisual]
        lay = host.find("Layout")
        lines = _abs_group_layout(kids)
        if lay is not None:
            if renames or True:
                # the old layout's Component ids may have been patched above: replace the whole element
                patch.edits = [e for e in patch.edits if not (lay.s <= e[0] and e[1] <= lay.e)]
            patch.remove(lay)
        before = host.find("SubComponents")
        patch.append_child(host, lines, before=before)
        notes.append(f"{form_path.name}: the Free Design layout of {cname or 'the form'} was rebuilt from the "
                     "designer positions")
    if not patch.edits:
        return notes
    if ctx.unsupported and structural:
        notes.append(f"*** {form_path.name}: not saved - this form uses {', '.join(ctx.unsupported)} which RAD IDE "
                     f"cannot regenerate; only text/property edits can be saved here ({', '.join(structural[:5])} "
                     "need NetBeans)")
        return notes
    out = patch.apply()
    new_root = X.parse(out)
    java_new = None
    if java_path is not None and Path(java_path).exists():
        text, enc, nl = read_text_keep(java_path)
        if not ctx.unsupported:
            body, decls = generate_init(new_root)
            jt = replace_guarded(text, body, decls)
        else:
            jt = _patch_literals(text, literal)
        for old_n, new_n in renames.items():
            jt = re.sub(rf"\b{re.escape(old_n)}\b", new_n, jt)
        for owner, evs in new_ev.items():
            for ev, info in evs.items():
                if f"event_{info['handler']}" not in jt:
                    jt = _add_stub(jt, info["handler"], info["parameters"])
        java_new = (jt, enc, nl)
    form_path.write_bytes(out)
    if java_new is not None:
        write_text_keep(java_path, *java_new)
        notes.append(f"{Path(java_path).name}: initComponents() regenerated" if not ctx.unsupported else
                     f"{Path(java_path).name}: property literals updated in initComponents()")
    notes.append(f"{form_path.name}: saved ({', '.join((structural + simple_edits)[:6])})")
    return notes


def _patch_literals(java: str, edits: list[tuple[str, str, str]]) -> str:
    lines = java.split("\n")
    bi = next((i for i, ln in enumerate(lines) if "//GEN-BEGIN:initComponents" in ln), 0)
    ei = next((i for i, ln in enumerate(lines) if "//GEN-END:initComponents" in ln), len(lines) - 1)
    for var, setter, lit in edits:
        rx = re.compile(rf"^(\s*){re.escape(var + '.' if var else '')}{setter}\((.*)\);(.*)$")
        for i in range(bi, ei + 1):
            m = rx.match(lines[i])
            if m:
                lines[i] = f"{m.group(1)}{var + '.' if var else ''}{setter}({lit});{m.group(3)}"
                break
        else:
            # insert after the creation line block (before the first blank line after "<var> = new")
            for i in range(bi, ei + 1):
                if var and re.match(rf"\s*{re.escape(var)}\.set", lines[i]):
                    ind = re.match(r"\s*", lines[i]).group(0)
                    lines.insert(i, f"{ind}{var}.{setter}({lit});")
                    ei += 1
                    break
    return "\n".join(lines)


def _add_stub(java: str, handler: str, params: str) -> str:
    lines = java.split("\n")
    vi = next((i for i, ln in enumerate(lines) if "Variables declaration - do not modify" in ln or
               "//GEN-BEGIN:variables" in ln), -1)
    if vi < 0:
        vi = max(i for i, ln in enumerate(lines) if ln.strip() == "}")
    ind = re.match(r"\s*", lines[vi]).group(0) or "    "
    lines[vi:vi] = handler_stub(handler, params, ind)
    return "\n".join(lines)


def event_info(ctrl_cls: str, event: str) -> tuple[str, str, str]:
    if _short(ctrl_cls) == "JList" and event == "SelectedIndexChanged":
        return LIST_SEL
    return EVENTS.get(event, EVENTS["Click"])
