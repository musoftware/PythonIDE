"""Neutral control catalogue (VB-style names, properties and events).

Language plugins map these to their toolkits. Events marked with an
argument kind receive an event-args object `e`:
    mouse: e.X, e.Y, e.Button (1 left, 2 middle, 3 right), e.Delta (wheel)
    key:   e.KeyCode, e.KeyChar
    cancel: e.Cancel (set True to cancel, e.g. FormClosing)
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PropDef:
    name: str
    # str | int | bool | color | list | menu | enum | file | font | anchor | dbref, plus the component
    # package kinds of radide/components/proptypes.py (multiline, float, flags, image, columns, padding,
    # alignment, gradient, shadow, border, event, custom)
    kind: str
    default: object
    help: str = ""
    choices: tuple = ()          # for kind == "enum" / "flags"
    category: str = "Misc"
    editor: str = ""             # custom property editor id (a component package's editors.py)
    # extra schema data of a component package property (min, max, filter, displayName, ...)
    meta: dict = field(default=None, compare=False, hash=False, repr=False)


def _p(name, kind, default, help="", choices=(), category="Misc"):
    return PropDef(name, kind, default, help, tuple(choices), category)


# ------------------------------------------------------------------ events
EVENT_ARGS = {
    "MouseDown": "mouse", "MouseUp": "mouse", "MouseMove": "mouse", "MouseWheel": "mouse",
    "KeyDown": "key", "KeyUp": "key", "KeyPress": "key",
    "FormClosing": "cancel",
}
EVENT_HELP = {
    "Click": "Occurs when the control is clicked.",
    "DoubleClick": "Occurs when the control is double-clicked.",
    "MouseDown": "Mouse button pressed over the control (e.X, e.Y, e.Button).",
    "MouseUp": "Mouse button released over the control (e.X, e.Y, e.Button).",
    "MouseMove": "Mouse moved over the control (e.X, e.Y).",
    "MouseEnter": "Mouse pointer enters the control.",
    "MouseLeave": "Mouse pointer leaves the control.",
    "MouseWheel": "Mouse wheel moved (e.Delta).",
    "KeyDown": "A key is pressed while the control has focus (e.KeyCode).",
    "KeyUp": "A key is released while the control has focus (e.KeyCode).",
    "KeyPress": "A character key is pressed (e.KeyChar).",
    "GotFocus": "The control receives the focus.",
    "LostFocus": "The control loses the focus.",
    "TextChanged": "The Text property value changes.",
    "CheckedChanged": "The Checked property value changes.",
    "SelectedIndexChanged": "The selected item changes.",
    "ValueChanged": "The Value property changes.",
    "Tick": "The timer interval has elapsed.",
    "Load": "Occurs before the form is displayed for the first time.",
    "Activated": "The form becomes the active window.",
    "Deactivate": "The form loses focus and is no longer active.",
    "Resize": "The form is resized.",
    "FormClosing": "The form is closing; set e.Cancel = True to keep it open.",
    "FormClosed": "The form has been closed.",
    "CellChanged": "The user changed the value of a cell.",
    "PageChanged": "The report viewer shows another page.",
}

MOUSE_EVENTS = ["Click", "DoubleClick", "MouseDown", "MouseUp", "MouseMove",
                "MouseEnter", "MouseLeave", "MouseWheel"]
KEY_EVENTS = ["KeyDown", "KeyUp", "KeyPress"]
FOCUS_EVENTS = ["GotFocus", "LostFocus"]
COMMON_EVENTS = MOUSE_EVENTS + KEY_EVENTS + FOCUS_EVENTS

FORM_EVENTS = ["Load", "Activated", "Deactivate", "Resize", "FormClosing", "FormClosed",
               "Click", "DoubleClick", "MouseDown", "MouseUp", "MouseMove", "MouseWheel",
               "KeyDown", "KeyUp", "KeyPress"]


def event_args(event: str) -> str | None:
    return EVENT_ARGS.get(event)


# ------------------------------------------------------------------ properties
ALIGN = ("Left", "Center", "Right")
DOCKS = ("None", "Top", "Bottom", "Left", "Right", "Fill")
ANCHOR_EDGES = ("Top", "Bottom", "Left", "Right")

# Children of a TabControl live on a page: props["TabPage"] = page index and
# their Left/Top are relative to the page's client area, which starts
# TAB_PAGE_X / TAB_PAGE_Y pixels inside the TabControl (below the tabs).
TAB_PAGE_X = 2
TAB_PAGE_Y = 24
# a ToolStrip is drawn under the menu bar; the form's client area starts below it
TOOLSTRIP_H = 26
# menu-like components whose Items get "<ItemName>_Click" handlers
MENU_TYPES = ("MenuStrip", "ToolStrip")
# containers whose children live on pages (props["TabPage"]; the designer shows the SelectedIndex page)
PAGED_TYPES = ("TabControl", "RmTabStrip", "RmNavigationPane")
DIALOG_TYPES = ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog", "FolderBrowserDialog")


def parse_anchor(value) -> set[str]:
    """'Top, Left' -> {'Top', 'Left'} (unknown words ignored, case-insensitive)."""
    words = {w.strip().lower() for w in str(value or "").replace("|", ",").split(",")}
    return {e for e in ANCHOR_EDGES if e.lower() in words}


def format_anchor(edges) -> str:
    edges = set(edges)
    out = [e for e in ANCHOR_EDGES if e in edges]
    return ", ".join(out) if out else "None"

COMMON_PROPS = [
    _p("Name", "str", "", "Identifier used in code.", category="Design"),
    _p("Text", "str", "", "Caption / text shown on the control.", category="Appearance"),
    _p("Left", "int", 0, "Distance from the left edge of the container.", category="Layout"),
    _p("Top", "int", 0, "Distance from the top edge of the container.", category="Layout"),
    _p("Width", "int", 75, category="Layout"),
    _p("Height", "int", 23, category="Layout"),
    _p("BackColor", "color", "", "Background colour.", category="Appearance"),
    _p("ForeColor", "color", "", "Text colour.", category="Appearance"),
    _p("FontName", "font", "Segoe UI", "Font family.", category="Appearance"),
    _p("FontSize", "int", 9, "Font size in points.", category="Appearance"),
    _p("FontBold", "bool", False, category="Appearance"),
    _p("FontItalic", "bool", False, category="Appearance"),
    _p("Enabled", "bool", True, "Whether the user can interact with the control.", category="Behavior"),
    _p("Visible", "bool", True, "Whether the control is shown at run time.", category="Behavior"),
    _p("ToolTip", "str", "", "Text shown when the mouse rests on the control.", category="Behavior"),
    _p("TabIndex", "int", 0, "Order of the control in Tab navigation.", category="Behavior"),
    _p("Anchor", "anchor", "Top, Left", "Edges of the container the control stays attached to when the "
       "container is resized (Top, Bottom, Left, Right).", category="Layout"),
    _p("Dock", "enum", "None", "Edge of the container the control is docked to (Fill = the remaining space).",
       DOCKS, category="Layout"),
]

FORM_PROPS = {p.name: p for p in [
    _p("Name", "str", "Form1", "Form name (also the file name).", category="Design"),
    _p("Text", "str", "Form1", "Window title.", category="Appearance"),
    _p("Width", "int", 400, category="Layout"),
    _p("Height", "int", 300, category="Layout"),
    _p("BackColor", "color", "", category="Appearance"),
    _p("StartPosition", "enum", "CenterScreen", "Where the form appears when shown.",
       ("Manual", "CenterScreen"), category="Layout"),
    _p("FormBorderStyle", "enum", "Sizable", "Sizable lets the user resize the window.",
       ("Sizable", "FixedSingle"), category="Appearance"),
    _p("TopMost", "bool", False, "Keep the window above other windows.", category="Behavior"),
    _p("WindowState", "enum", "Normal", choices=("Normal", "Maximized"), category="Layout"),
    _p("Icon", "file", "", "Window icon (.ico / .png).", category="Appearance"),
    _p("ScaleMode", "enum", "Pixel", "Units used by VB code for Left/Top/Width/Height "
       "(Twip = VB6: 15 per pixel).", ("Pixel", "Twip"), category="Misc"),
]}


@dataclass(frozen=True)
class ControlType:
    name: str
    prefix: str
    size: tuple[int, int]
    events: list[str]                     # specific events (first = default event)
    extra: list[PropDef] = field(default_factory=list)
    has_text: bool = True
    container: bool = False               # can host child controls (Panel, GroupBox)
    nonvisual: bool = False               # lives in the component tray (Timer, MenuStrip)
    common_events: bool = True
    description: str = ""
    overrides: tuple = ()                 # (prop, value) defaults that differ from COMMON_PROPS
    # component package (radide/components) this type comes from; None for types made in code
    package: object = field(default=None, compare=False, hash=False, repr=False)
    category: str = ""                    # Toolbox group ("" = by kind)
    methods: tuple = ()                   # ({"name", "signature", "description"}, ...) for IntelliSense
    # common properties this type has (None = all of COMMON_PROPS); a component manifest's "commonProperties"
    common: tuple | None = None

    @property
    def default_event(self) -> str | None:
        return self.events[0] if self.events else ("Click" if self.common_events and not self.nonvisual else None)

    def all_events(self) -> list[str]:
        out = list(self.events)
        if self.common_events and not self.nonvisual:
            out += [e for e in COMMON_EVENTS if e not in out]
        return out

    def prop_defs(self) -> list[PropDef]:
        if self.nonvisual:
            return [COMMON_PROPS[0], *self.extra]
        defs = [p for p in COMMON_PROPS if (self.has_text or p.name != "Text") and
                (self.common is None or p.name in self.common)]
        return defs + list(self.extra)

    def default_props(self, name: str) -> dict:
        props = {p.name: copy.deepcopy(p.default) for p in self.prop_defs()}
        props["Name"] = name
        props["Parent"] = ""
        if self.has_text and not self.nonvisual:
            props["Text"] = name
        if not self.nonvisual:
            props["Width"], props["Height"] = self.size
        for k, v in self.overrides:
            props[k] = copy.deepcopy(v)
        return props


# The built-in controls are component packages like any other (radide/components/builtin/<Name>/
# component.json, docs/COMPONENTS.md). CONTROL_TYPES maps every control type name to its ControlType:
# built-in, mobile (below), user controls (radide/usercontrols.py) and installed component packages
# (radide/components registers them).
from .components import builtin_control_types as _builtin_control_types  # noqa: E402

CONTROL_TYPES: dict[str, ControlType] = _builtin_control_types()


def split_rows(value) -> list[list[str]]:
    """'a|b;c|d' -> [['a', 'b'], ['c', 'd']] (rows split by ;, cells by |)."""
    return [[cell.strip() for cell in row.split("|")] for row in str(value or "").split(";") if row.strip()]


def tree_paths(value) -> list[tuple[str, str]]:
    """TreeView Nodes 'Root;Root/Child' -> [(path, text), ...] with every parent path listed first."""
    out, seen = [], set()
    for path in split_items(value):
        parts = [x.strip() for x in path.split("/") if x.strip()]
        for i in range(len(parts)):
            sub = "/".join(parts[:i + 1])
            if sub not in seen:
                seen.add(sub)
                out.append((sub, parts[i]))
    return out


def split_items(value) -> list[str]:
    return [s.strip() for s in str(value).split(";") if s.strip()]


# ---------------------------------------------------------------- menu helpers
# Menu item: {"Text": "File", "Name": "mnuFile", "Items": [...]}; Text "-" = separator.

def menu_leaves(items: list) -> list[dict]:
    """Clickable items (those without children), in order."""
    out = []
    for it in items or []:
        if it.get("Text") == "-":
            continue
        if it.get("Items"):
            out += menu_leaves(it["Items"])
        else:
            out.append(it)
    return out


def menu_names(items: list) -> list[str]:
    out = []
    for it in items or []:
        if it.get("Name"):
            out.append(it["Name"])
        out += menu_names(it.get("Items", []))
    return out


# ---------------------------------------------------------------- mobile controls (CONTRACTS 10.4)
# AppBar, BottomNav, Fab, Card, MListView, Switch, MSlider, MTextField, MImage, MIcon, Drawer, MTabBar,
# MWebView, Column / Row / Stack - defined in radide/mobile/controls.py (imported last: it uses the
# names above).
from .mobile.controls import MOBILE_CONTROL_TYPES as _MOBILE_CONTROL_TYPES  # noqa: E402

CONTROL_TYPES.update(_MOBILE_CONTROL_TYPES)

# ---------------------------------------------------------------- data binding (radide/databinding_sql.py)
# DataSource / DataMember / DisplayMember / ValueMember (kind "dbref": the Properties window offers the
# form's data sources and their columns).
_DB_HELP = {
    "DataSource": "The data source (Data Sources window) the control is bound to.",
    "DataMember": "The bound column (Column or Source.Column); ListBox / ComboBox: the Source.Column that "
                  "receives the selected item's ValueMember.",
    "DisplayMember": "The column whose values the list shows.",
    "ValueMember": "The column that is the value of an item (usually the key).",
}
for _t, _names in (("DataGridView", ("DataSource",)),
                   ("ListBox", ("DataSource", "DisplayMember", "ValueMember", "DataMember")),
                   ("ComboBox", ("DataSource", "DisplayMember", "ValueMember", "DataMember")),
                   ("TextBox", ("DataSource", "DataMember")), ("Label", ("DataSource", "DataMember")),
                   ("CheckBox", ("DataSource", "DataMember"))):
    _have = {p.name for p in CONTROL_TYPES[_t].extra}
    CONTROL_TYPES[_t].extra.extend(_p(_n, "dbref", "", _DB_HELP[_n], category="Data")
                                   for _n in _names if _n not in _have)
