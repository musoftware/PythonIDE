"""The .form files of a VB6 project -> the vbCtls() table of the Win32 forms runtime (rt/vbrt_forms.bi).

Every form, control, menu item and dialog gets a numeric id (a Const in the generated code); the setup
procedure describes them with VBDefForm / VBDef / VBDefMenu plus field assignments, the geometry comes
from radide.layout (the same Anchor / Dock rules the designer and the Tk generator use), and the creation
order is the Tab order (parents first), like the Tk program the IDE runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ....model import Form
from ....layout import place_specs
from ....controls import CONTROL_TYPES

KIND = {"Button": "vbkButton", "Label": "vbkLabel", "TextBox": "vbkTextBox", "CheckBox": "vbkCheckBox",
        "RadioButton": "vbkOption", "ListBox": "vbkListBox", "ComboBox": "vbkComboBox", "GroupBox": "vbkFrame",
        "Panel": "vbkPanel", "PictureBox": "vbkPicture", "ProgressBar": "vbkProgress",
        "NumericUpDown": "vbkUpDown", "TrackBar": "vbkSlider", "Timer": "vbkTimer", "LinkLabel": "vbkLink",
        "StatusBar": "vbkStatus", "TabControl": "vbkTab", "OpenFileDialog": "vbkDlgOpen",
        "SaveFileDialog": "vbkDlgSave", "ColorDialog": "vbkDlgColor", "FontDialog": "vbkDlgFont",
        "FolderBrowserDialog": "vbkDlgFolder", "DateTimePicker": "vbkDate"}

# VB event names a control kind raises natively (Form: see FORM_EVENTS)
COMMON_EV = {"Click", "DblClick", "MouseDown", "MouseUp", "MouseMove", "KeyDown", "KeyUp", "KeyPress",
             "GotFocus", "LostFocus"}
EVENTS = {
    "Button": COMMON_EV, "Label": COMMON_EV - {"KeyDown", "KeyUp", "KeyPress", "GotFocus", "LostFocus"},
    "TextBox": COMMON_EV | {"Change"}, "CheckBox": COMMON_EV, "RadioButton": COMMON_EV,
    "ListBox": COMMON_EV, "ComboBox": COMMON_EV | {"Change"}, "GroupBox": {"Click", "DblClick", "MouseDown",
                                                                           "MouseUp", "MouseMove"},
    "Panel": {"Click", "DblClick", "MouseDown", "MouseUp", "MouseMove"},
    "PictureBox": COMMON_EV - {"KeyDown", "KeyUp", "KeyPress"}, "ProgressBar": {"MouseDown", "MouseUp", "MouseMove"},
    "NumericUpDown": COMMON_EV | {"Change"}, "TrackBar": COMMON_EV | {"Change"}, "Timer": {"Timer"},
    "LinkLabel": COMMON_EV - {"KeyDown", "KeyUp", "KeyPress", "GotFocus", "LostFocus"},
    "StatusBar": {"Click", "MouseDown", "MouseUp", "MouseMove"}, "TabControl": {"Click"},
    "DateTimePicker": {"Change", "Click", "GotFocus", "LostFocus", "KeyDown", "KeyUp", "KeyPress"},
}
FORM_EVENTS = {"Load", "Activate", "Deactivate", "Resize", "QueryUnload", "Unload", "Terminate", "Click",
               "DblClick", "MouseDown", "MouseUp", "MouseMove", "KeyDown", "KeyUp", "KeyPress"}
# all VB6 event names: a procedure Name_<one of these> on a control / the form is an event handler
KNOWN_EVENTS = FORM_EVENTS | COMMON_EV | {"Change", "Timer", "MouseEnter", "MouseLeave", "MouseWheel", "Scroll",
                                          "NodeClick", "ItemClick", "SelChange", "AfterEdit", "Validate",
                                          "OLEDragDrop", "DragDrop", "Paint", "Initialize"}

# event -> (runtime event constant, argument fields of VBEventArgs in VB order)
EVENT_ARGS = {
    "Click": ("vbeClick", ()), "DblClick": ("vbeDblClick", ()), "Change": ("vbeChange", ()),
    "GotFocus": ("vbeGotFocus", ()), "LostFocus": ("vbeLostFocus", ()),
    "KeyPress": ("vbeKeyPress", ("keyAscii",)), "KeyDown": ("vbeKeyDown", ("keyCode", "shift")),
    "KeyUp": ("vbeKeyUp", ("keyCode", "shift")),
    "MouseDown": ("vbeMouseDown", ("button", "shift", "x", "y")),
    "MouseUp": ("vbeMouseUp", ("button", "shift", "x", "y")),
    "MouseMove": ("vbeMouseMove", ("button", "shift", "x", "y")),
    "Timer": ("vbeTimer", ()), "Load": ("vbeLoad", ()), "Activate": ("vbeActivate", ()),
    "Deactivate": ("vbeDeactivate", ()), "Resize": ("vbeResize", ()),
    "QueryUnload": ("vbeQueryUnload", ("cancel", "unloadMode")), "Unload": ("vbeUnload", ("cancel",)),
    "Terminate": ("vbeTerminate", ()),
}
FIELD_TAG = {"keyAscii": "i", "keyCode": "i", "shift": "i", "button": "i", "x": "f", "y": "f", "cancel": "i",
             "unloadMode": "i", "prevTab": "i", "index": "i"}

# default property (a control used as a value): Text1 = "x"
DEFAULT_PROP = {"TextBox": "text", "ComboBox": "text", "ListBox": "text", "Label": "caption", "Button": "caption",
                "GroupBox": "caption", "LinkLabel": "caption", "CheckBox": "value", "RadioButton": "value",
                "NumericUpDown": "value", "TrackBar": "value", "ProgressBar": "value", "Timer": "enabled",
                "StatusBar": "simpletext", "TabControl": "tab", "PictureBox": "picture", "Panel": "caption", "DateTimePicker": "value",
                "OpenFileDialog": "filename", "SaveFileDialog": "filename", "ColorDialog": "color",
                "FontDialog": "fontname", "FolderBrowserDialog": "selectedpath"}

TEXT_KINDS = {"Button", "Label", "TextBox", "CheckBox", "RadioButton", "ComboBox", "GroupBox", "LinkLabel",
              "StatusBar", "ListBox"}
VALUE_TAG = {"CheckBox": "i", "RadioButton": "b", "ProgressBar": "i", "NumericUpDown": "i", "TrackBar": "i",
             "DateTimePicker": "d"}
VISUAL = set(KIND) - {"Timer", "OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog",
                      "FolderBrowserDialog"}
DIALOGS = {"OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog", "FolderBrowserDialog"}

# property name (lower) -> (runtime constant, tag, control types or None = every visual control)
_GEOM = None
PROPS = {
    "caption": ("vbpText", "s", TEXT_KINDS - {"TextBox", "ComboBox", "ListBox"}),
    "text": ("vbpText", "s", TEXT_KINDS | {"OpenFileDialog", "SaveFileDialog", "DateTimePicker"}),
    "simpletext": ("vbpText", "s", {"StatusBar"}),
    "value": ("vbpValue", "i", set(VALUE_TAG)),
    "left": ("vbpLeft", "f", None), "top": ("vbpTop", "f", None), "width": ("vbpWidth", "f", None),
    "height": ("vbpHeight", "f", None), "enabled": ("vbpEnabled", "b", None), "visible": ("vbpVisible", "b", None),
    "backcolor": ("vbpBackColor", "i", None), "forecolor": ("vbpForeColor", "i", None),
    "listindex": ("vbpListIndex", "i", {"ListBox", "ComboBox"}),
    "listcount": ("vbpListCount", "i", {"ListBox", "ComboBox"}),
    "newindex": ("vbpNewIndex", "i", {"ListBox", "ComboBox"}),
    "selstart": ("vbpSelStart", "i", {"TextBox", "ComboBox", "NumericUpDown"}),
    "sellength": ("vbpSelLength", "i", {"TextBox", "ComboBox", "NumericUpDown"}),
    "seltext": ("vbpSelText", "s", {"TextBox"}),
    "locked": ("vbpLocked", "b", {"TextBox"}), "maxlength": ("vbpMaxLength", "i", {"TextBox"}),
    "min": ("vbpMin", "i", {"ProgressBar", "NumericUpDown", "TrackBar"}),
    "max": ("vbpMax", "i", {"ProgressBar", "NumericUpDown", "TrackBar"}),
    "minimum": ("vbpMin", "i", {"ProgressBar", "NumericUpDown", "TrackBar"}),
    "maximum": ("vbpMax", "i", {"ProgressBar", "NumericUpDown", "TrackBar"}),
    "interval": ("vbpInterval", "i", {"Timer"}),
    "fontname": ("vbpFontName", "s", None), "fontsize": ("vbpFontSize", "f", None),
    "fontbold": ("vbpFontBold", "b", None), "fontitalic": ("vbpFontItalic", "b", None),
    "fontunderline": ("vbpFontUnderline", "b", None),
    "tooltiptext": ("vbpToolTipText", "s", None), "tag": ("vbpTag", "s", "all"),
    "hwnd": ("vbpHwnd", "i", None), "tabindex": ("vbpTabIndex", "i", None), "tabstop": ("vbpTabStop", "b", None),
    "picture": ("vbpPicture", "s", {"PictureBox"}),
    "filename": ("vbpFileName", "s", {"OpenFileDialog", "SaveFileDialog"}),
    "filetitle": ("vbpFileTitle", "s", {"OpenFileDialog", "SaveFileDialog"}),
    "filter": ("vbpFilter", "s", {"OpenFileDialog", "SaveFileDialog"}),
    "dialogtitle": ("vbpDialogTitle", "s", DIALOGS), "title": ("vbpDialogTitle", "s", DIALOGS),
    "initdir": ("vbpInitDir", "s", {"OpenFileDialog", "SaveFileDialog"}),
    "color": ("vbpColor", "i", {"ColorDialog", "FontDialog"}),
    "cancelerror": ("vbpCancelError", "b", DIALOGS),
    "selectedpath": ("vbpFileName", "s", {"FolderBrowserDialog"}),
    "name": ("vbpName", "s", "all"), "multiline": ("vbpMultiLine", "b", {"TextBox"}),
    "passwordchar": ("vbpPasswordChar", "s", {"TextBox"}), "index": ("vbpIndex", "i", "all"),
    "tab": ("vbpTab", "i", {"TabControl"}), "selectedindex": ("vbpTab", "i", {"TabControl"}),
    "tabs": ("vbpTabs", "i", {"TabControl"}), "alignment": ("vbpAlignment", "i", {"Label", "TextBox"}),
    "linkcolor": ("vbpLinkColor", "i", {"LinkLabel"}),
    "year": ("vbpYear", "i", {"DateTimePicker"}), "month": ("vbpMonth", "i", {"DateTimePicker"}),
    "day": ("vbpDay", "i", {"DateTimePicker"}), "hour": ("vbpHour", "i", {"DateTimePicker"}),
    "minute": ("vbpMinute", "i", {"DateTimePicker"}), "second": ("vbpSecond", "i", {"DateTimePicker"}),
    "format": ("vbpFormat", "i", {"DateTimePicker"}),
}
for _k in ("fontname", "fontsize", "fontbold", "fontitalic"):
    PROPS[_k] = (PROPS[_k][0], PROPS[_k][1], None)
FONT_DIALOG_PROPS = {"fontname", "fontsize", "fontbold", "fontitalic"}
# properties VB code may set that have no effect here (accepted like the IDE's runtime does)
IGNORED_SET = {"mousepointer", "appearance", "borderstyle", "sorted", "autosize", "wordwrap", "default",
               "cancel", "datasource", "datamember", "datafield", "flags", "filterindex", "maxfilesize",
               "defaultext", "helpfile", "scrollbars", "style", "righttoleft", "dragmode", "oledragmode"}

FORM_PROPS = {
    "caption": ("vbpText", "s"), "text": ("vbpText", "s"), "left": ("vbpLeft", "f"), "top": ("vbpTop", "f"),
    "width": ("vbpWidth", "f"), "height": ("vbpHeight", "f"), "visible": ("vbpVisible", "b"),
    "enabled": ("vbpEnabled", "b"), "backcolor": ("vbpBackColor", "i"), "windowstate": ("vbpWindowState", "i"),
    "scalewidth": ("vbpScaleWidth", "f"), "scaleheight": ("vbpScaleHeight", "f"), "name": ("vbpName", "s"),
    "hwnd": ("vbpHwnd", "i"), "tag": ("vbpTag", "s"), "forecolor": ("vbpForeColor", "i"),
}
FORM_IGNORED_SET = {"borderstyle", "mousepointer", "keypreview", "scalemode", "icon", "autoredraw",
                    "fontname", "fontsize", "fontbold"}
FORM_NOOP_METHODS = {"cls", "print", "line", "circle", "pset", "zorder", "refresh", "animate"}


@dataclass
class CtlInfo:
    name: str                    # VB name (original spelling)
    type: str                    # neutral control type (Button, TextBox ...)
    id: int
    const: str                   # Const name in the generated code
    form: "FormInfo"
    props: dict
    array: str = ""              # control array name (lower) or ""
    index: int = -1
    menu: bool = False

    @property
    def kind(self) -> str:
        return "vbkMenu" if self.menu else KIND[self.type]


@dataclass
class FormInfo:
    name: str
    id: int
    const: str
    model: Form
    ctls: dict = field(default_factory=dict)      # lower name -> CtlInfo (controls, menus, dialogs)
    arrays: dict = field(default_factory=dict)    # lower array name -> {index: CtlInfo}
    images: list = field(default_factory=list)    # picture files the form uses
    array_raw: dict = field(default_factory=dict) # lower array name -> spelling in the .form

    def array_const(self, low: str) -> str:
        return f"CTL_{_ident(self.name)}_{_ident(self.array_raw.get(low, low))}__arr"


def vb_color(c) -> str:
    """'#RRGGBB' -> FreeBASIC literal &hBBGGRR ('' when not set)."""
    c = str(c or "")
    if len(c) != 7 or not c.startswith("#"):
        return ""
    try:
        r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    except ValueError:
        return ""
    return f"&h{b:02X}{g:02X}{r:02X}"


def fb_str(s) -> str:
    """A FreeBASIC string literal (no escapes: "" for a quote; long texts split)."""
    s = str(s)
    if "\r" in s or "\n" in s or "\t" in s or "\0" in s:
        parts = []
        cur = ""
        for ch in s:
            if ch in "\r\n\t\0":
                if cur:
                    parts.append('"' + cur.replace('"', '""') + '"')
                    cur = ""
                parts.append(f"Chr({ord(ch)})")
            else:
                cur += ch
        if cur:
            parts.append('"' + cur.replace('"', '""') + '"')
        return "(" + " & ".join(parts) + ")" if len(parts) > 1 else parts[0]
    if len(s.encode("utf-8")) > 800:
        chunks = [s[i:i + 200] for i in range(0, len(s), 200)]
        return "(" + " & ".join('"' + c.replace('"', '""') + '"' for c in chunks) + ")"
    return '"' + s.replace('"', '""') + '"'


def _ident(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in s)


def tab_order(form: Form) -> list:
    out = []

    def visit(parent):
        for c in sorted(form.children(parent), key=lambda c: int(c.props.get("TabIndex", 0) or 0)):
            out.append(c)
            if c.ctype.container:
                visit(c.name)
    visit("")
    seen = {id(c) for c in out}
    out += [c for c in form.visual() if id(c) not in seen]       # orphans
    return out


def collect(forms: list[tuple[str, Form]], reasons: list, start_id: int = 1) -> list[FormInfo]:
    """FormInfo for every form (ids assigned); unsupported controls -> reasons."""
    out = []
    nid = start_id
    for fname, model in forms:
        fi = FormInfo(fname, nid, "FRM_" + _ident(fname), model)
        nid += 1
        out.append(fi)
        fp = model.props
        for key, what in (("animations", "animations"), ("storyboards", "storyboards (Expression Blend)"),
                          ("states", "visual states"), ("bindings", "data bindings"), ("datasources", "data sources"),
                          ("dbsources", "data sources"), ("motion", "motion presets"), ("physics", "physics"),
                          ("particles", "particles"), ("variants", "layout variants"), ("wiring", "event wiring")):
            if model.extra.get(key):
                reasons.append(f"{fname}.form: {what} are not supported by the native build yet")
        if fp.get("FormBorderStyle", "Sizable") not in ("Sizable", "FixedSingle"):
            reasons.append(f"{fname}.form: FormBorderStyle {fp.get('FormBorderStyle')} is not supported natively")
        for c in [*tab_order(model), *model.nonvisual()]:
            t = c.type
            if t == "MenuStrip":
                def walk(items, depth=0):
                    nonlocal nid
                    for it in items or []:
                        nm = str(it.get("Name") or "")
                        ci = CtlInfo(nm or f"_sep{nid}", "Menu", nid, f"MNU_{_ident(fname)}_{_ident(nm or str(nid))}",
                                     fi, dict(it), menu=True)
                        ci.props["_depth"] = depth
                        nid += 1
                        fi.ctls[(nm or f"_sep{ci.id}").lower()] = ci
                        walk(it.get("Items"), depth + 1)
                walk(c.props.get("Items"))
                continue
            if t not in KIND:
                ct = CONTROL_TYPES.get(t)
                what = "a component / user control" if ct is not None and ct.package is not None and \
                    t not in ("TreeView", "ListView", "DataGridView", "DateTimePicker", "ToolStrip", "ActiveX",
                              "ReportViewer") else "not supported natively yet"
                reasons.append(f"{fname}.form: control {c.name} ({t}) - {what}")
                continue
            ci = CtlInfo(c.name, t, nid, f"CTL_{_ident(fname)}_{_ident(c.name)}", fi, c.props)
            nid += 1
            arr = str(c.props.get("ArrayName") or "")
            if arr:
                ci.array = arr.lower()
                try:
                    ci.index = int(c.props.get("ArrayIndex", 0) or 0)
                except (TypeError, ValueError):
                    ci.index = 0
                fi.arrays.setdefault(ci.array, {})[ci.index] = ci
                fi.array_raw.setdefault(ci.array, arr)
            fi.ctls[c.name.lower()] = ci
            if t == "PictureBox" and c.props.get("Image"):
                fi.images.append(str(c.props["Image"]))
        if fp.get("Icon"):
            fi.images.append(str(fp["Icon"]))
    return out


def _b(v) -> str:
    return "-1" if v else "0"


def setup_code(fi: FormInfo, handlers: dict) -> list[str]:
    """FreeBASIC lines describing one form.  handlers: (ctl lower name | '' for the form, VB event) -> wrapper."""
    m = fi.model
    fp = m.props
    L = [f"    ' ---- {fi.name}",
         f"    VBDefForm({fi.const}, {fb_str(fi.name)}, {fb_str(fp.get('Text', fi.name))}, "
         f"{int(fp.get('Width', 400))}, {int(fp.get('Height', 300))})"]
    sets = []
    if vb_color(fp.get("BackColor")):
        sets.append(f".back = {vb_color(fp.get('BackColor'))}")
    if fp.get("StartPosition", "CenterScreen") != "CenterScreen":
        sets.append(".startPos = 0")
    if fp.get("FormBorderStyle") == "FixedSingle":
        sets.append(".border = 1")
    if fp.get("TopMost"):
        sets.append(".topMost = -1")
    if fp.get("WindowState") == "Maximized":
        sets.append(".winState = 2")
    if fp.get("ScaleMode") == "Twip":
        sets.append(".twips = -1")
    if fp.get("Icon"):
        sets.append(f".icon = {fb_str(fp['Icon'])}")
    if sets:
        L.append(f"    With vbCtls({fi.const}): " + ": ".join(sets) + ": End With")
    for ev, wrapper in sorted(handlers.get("", {}).items()):
        L.append(f"    VBOn({fi.const}, {EVENT_ARGS[ev][0]}, @{wrapper})")
    specs = place_specs(m)
    for key, ci in fi.ctls.items():
        p = ci.props
        if ci.menu:
            parent = "0"
            L.append(f"    VBDefMenu({ci.const}, {fi.const}, {{parent}}, {fb_str(ci.name if not ci.name.startswith('_sep') else '')}, "
                     f"{fb_str(p.get('Text', ''))})")
            continue
        parent = "0"
        if p.get("Parent"):
            pc = fi.ctls.get(str(p["Parent"]).lower())
            if pc is not None:
                parent = pc.const
        x, y = int(p.get("Left", 0) or 0), int(p.get("Top", 0) or 0)
        w, h = int(p.get("Width", 0) or 0), int(p.get("Height", 0) or 0)
        L.append(f"    VBDef({ci.const}, {fi.const}, {parent}, {ci.kind}, {fb_str(ci.name)}, "
                 f"{fb_str(p.get('Text', '') if ci.type in TEXT_KINDS or ci.type == 'Panel' else '')}, {x}, {y}, {w}, {h})")
        pl = specs.get(ci.name)
        if pl is not None and not pl.is_static():
            L.append(f"    VBPlaceSet({ci.const}, {pl.x:g}, {pl.y:g}, {pl.w:g}, {pl.h:g}, {pl.rx:g}, {pl.ry:g}, "
                     f"{pl.rw:g}, {pl.rh:g})")
        sets = []
        t = ci.type
        if t in VISUAL:
            fn, fs = p.get("FontName") or "Segoe UI", p.get("FontSize", 9)
            if fn != "Segoe UI" or float(fs or 9) != 9 or p.get("FontBold") or p.get("FontItalic"):
                L.append(f"    VBFontSet({ci.const}, {fb_str(fn)}, {float(fs or 9):g}, {_b(p.get('FontBold'))}, "
                         f"{_b(p.get('FontItalic'))})")
            if vb_color(p.get("BackColor")):
                sets.append(f".back = {vb_color(p.get('BackColor'))}")
            if vb_color(p.get("ForeColor")):
                sets.append(f".fore = {vb_color(p.get('ForeColor'))}")
            if p.get("Enabled") is False:
                sets.append(".enabled = 0")
            if p.get("Visible") is False:
                sets.append(".visible = 0")
            if p.get("ToolTip"):
                sets.append(f".tooltip = {fb_str(p['ToolTip'])}")
            if int(p.get("TabIndex", 0) or 0):
                sets.append(f".tabIndex = {int(p.get('TabIndex', 0) or 0)}")
            al = {"Left": 0, "Right": 1, "Center": 2}.get(str(p.get("TextAlign", "")), None)
            if al is not None and al != (2 if t == "Button" else 0):
                sets.append(f".align = {al}")
        if t == "TextBox":
            if p.get("Multiline"):
                sets.append(".multiline = -1")
            if p.get("ReadOnly"):
                sets.append(".readonly = -1")
            if p.get("PasswordChar"):
                sets.append(f".password = {fb_str(str(p['PasswordChar'])[:1])}")
            if int(p.get("MaxLength", 0) or 0):
                sets.append(f".maxlen = {int(p['MaxLength'])}")
        elif t in ("CheckBox", "RadioButton"):
            if p.get("Checked"):
                sets.append(".value = " + ("1" if t == "CheckBox" else "-1"))
        elif t in ("ListBox", "ComboBox"):
            if p.get("Items"):
                sets.append(f".items = {fb_str(p['Items'])}")
            if t == "ComboBox":
                st = {"DropDownList": 0, "DropDown": 1, "Simple": 2}.get(str(p.get("DropDownStyle", "DropDownList")), 0)
                if st:
                    sets.append(f".style = {st}")
        elif t in ("ProgressBar", "NumericUpDown", "TrackBar"):
            sets.append(f".vmin = {int(p.get('Minimum', 0) or 0)}: .vmax = {int(p.get('Maximum', 100) or 0)}: "
                        f".value = {int(p.get('Value', 0) or 0)}")
        elif t == "Timer":
            sets.append(f".interval = {int(p.get('Interval', 100) or 0)}: .timerOn = {_b(p.get('Enabled'))}: "
                        f".enabled = {_b(p.get('Enabled'))}")
        elif t == "PictureBox":
            if p.get("Image"):
                sets.append(f".picture = {fb_str(p['Image'])}")
        elif t == "DateTimePicker":
            st = {"Short": 0, "Long": 1, "Time": 2}.get(str(p.get("Format", "Short")), 0)
            if st:
                sets.append(f".style = {st}")
            if p.get("Value"):
                sets.append(f".text = {fb_str(p['Value'])}")
        elif t == "LinkLabel":
            if vb_color(p.get("LinkColor")):
                sets.append(f".linkColor = {vb_color(p.get('LinkColor'))}")
        elif t == "TabControl":
            sets.append(f".items = {fb_str(p.get('TabPages', ''))}")
            if int(p.get("SelectedIndex", 0) or 0):
                sets.append(f".curTab = {int(p.get('SelectedIndex', 0) or 0)}")
        elif t in ("OpenFileDialog", "SaveFileDialog"):
            for k, f in (("Title", "title"), ("Filter", "filter"), ("FileName", "filename"),
                         ("InitialDirectory", "initdir")):
                if p.get(k):
                    sets.append(f".{f} = {fb_str(p[k])}")
        elif t == "ColorDialog":
            if vb_color(p.get("Color")):
                sets.append(f".colour = {vb_color(p.get('Color'))}")
        elif t == "FontDialog":
            sets.append(f".fontName = {fb_str(p.get('FontName') or 'Segoe UI')}: .fontSize = {float(p.get('FontSize', 9) or 9):g}")
        elif t == "FolderBrowserDialog":
            if p.get("SelectedPath"):
                sets.append(f".filename = {fb_str(p['SelectedPath'])}")
        if p.get("Parent"):
            pc = fi.ctls.get(str(p["Parent"]).lower())
            if pc is not None and pc.type == "TabControl":
                sets.append(f".page = {int(p.get('TabPage', 0) or 0)}")
        if ci.array:
            sets.append(f".arrIndex = {ci.index}")
        if sets:
            L.append(f"    With vbCtls({ci.const}): " + ": ".join(sets) + ": End With")
        own = handlers.get(ci.name.lower(), {})
        if ci.array:
            own = {**handlers.get(ci.array, {}), **own}
        for ev, wrapper in sorted(own.items()):
            L.append(f"    VBOn({ci.const}, {EVENT_ARGS[ev][0]}, @{wrapper})")
    # menus: parents by nesting
    out, stack = [], []
    menu_items = [ci for ci in fi.ctls.values() if ci.menu]
    for line in L:
        if line.startswith("    VBDefMenu(") and "{parent}" in line:
            ci = menu_items.pop(0)
            depth = ci.props.get("_depth", 0)
            del stack[depth:]
            parent = stack[-1].const if stack else "0"
            stack.append(ci)
            line = line.replace("{parent}", parent)
            sets = []
            if ci.props.get("Enabled") is False:
                sets.append(".enabled = 0")
            if ci.props.get("Checked"):
                sets.append(".checked = -1")
            out.append(line)
            if sets:
                out.append(f"    With vbCtls({ci.const}): " + ": ".join(sets) + ": End With")
            for ev, wrapper in sorted(handlers.get(ci.name.lower(), {}).items()):
                out.append(f"    VBOn({ci.const}, {EVENT_ARGS[ev][0]}, @{wrapper})")
            txt = str(ci.props.get("Text", ""))
            if "	" in txt:
                out.append(f"    VBAccelAdd({fi.const}, {fb_str(txt.split(chr(9), 1)[1].strip())}, {ci.const})")
            continue
        out.append(line)
    return out


def accelerators(fi: FormInfo) -> list[tuple[str, str]]:
    """(shortcut text, menu const) for menu captions written "Save\\tCtrl+S"."""
    out = []
    for ci in fi.ctls.values():
        if ci.menu and "\t" in str(ci.props.get("Text", "")):
            out.append((str(ci.props["Text"]).split("\t", 1)[1].strip(), ci.const))
    return out


__all__ = ["CtlInfo", "DEFAULT_PROP", "DIALOGS", "EVENTS", "EVENT_ARGS", "FIELD_TAG", "FORM_EVENTS", "FORM_PROPS",
           "FormInfo", "IGNORED_SET", "KIND", "KNOWN_EVENTS", "PROPS", "VALUE_TAG", "collect", "fb_str",
           "setup_code", "tab_order", "vb_color"]
