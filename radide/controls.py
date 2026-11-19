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
    kind: str        # str | int | bool | color | list | menu | enum | file | font | anchor
    default: object
    help: str = ""
    choices: tuple = ()          # for kind == "enum"
    category: str = "Misc"


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
        defs = [p for p in COMMON_PROPS if self.has_text or p.name != "Text"]
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


_ITEMS = _p("Items", "list", "", "Items separated by ;", category="Data")
_ALIGN = _p("TextAlign", "enum", "Left", choices=ALIGN, category="Appearance")
_VALUE = [_p("Minimum", "int", 0, category="Behavior"), _p("Maximum", "int", 100, category="Behavior"),
          _p("Value", "int", 0, category="Behavior")]

CONTROL_TYPES: dict[str, ControlType] = {t.name: t for t in [
    ControlType("Button", "Button", (75, 23), ["Click"], [_ALIGN],
                description="Raises an event when the user clicks it."),
    ControlType("Label", "Label", (60, 17), ["Click"], [_ALIGN],
                description="Displays read-only text."),
    ControlType("TextBox", "TextBox", (100, 20), ["TextChanged"],
                [_p("Multiline", "bool", False, "Allow several lines of text.", category="Behavior"),
                 _p("ReadOnly", "bool", False, category="Behavior"),
                 _p("PasswordChar", "str", "", "Character shown instead of the text (e.g. *).",
                    category="Behavior"),
                 _p("MaxLength", "int", 0, "Maximum characters (0 = no limit).", category="Behavior")],
                description="Lets the user enter text."),
    ControlType("CheckBox", "CheckBox", (90, 20), ["CheckedChanged"],
                [_p("Checked", "bool", False, category="Appearance")],
                description="An on/off option."),
    ControlType("RadioButton", "RadioButton", (90, 20), ["CheckedChanged"],
                [_p("Checked", "bool", False, category="Appearance")],
                description="One choice from a group."),
    ControlType("ListBox", "ListBox", (120, 95), ["SelectedIndexChanged"], [_ITEMS],
                has_text=False, description="A list of items to choose from."),
    ControlType("ComboBox", "ComboBox", (120, 21), ["SelectedIndexChanged", "TextChanged"],
                [_ITEMS, _p("DropDownStyle", "enum", "DropDownList",
                            choices=("DropDownList", "DropDown"), category="Behavior")],
                has_text=False, description="A drop-down list."),
    ControlType("PictureBox", "PictureBox", (100, 50), ["Click"],
                [_p("Image", "file", "", "Image file (.png / .gif).", category="Appearance")],
                has_text=False, description="Displays an image."),
    ControlType("ProgressBar", "ProgressBar", (100, 23), [], _VALUE, has_text=False,
                description="Shows the progress of an operation."),
    ControlType("NumericUpDown", "NumericUpDown", (120, 20), ["ValueChanged"], _VALUE,
                has_text=False, description="A number with up/down arrows."),
    ControlType("TrackBar", "TrackBar", (104, 45), ["ValueChanged"], _VALUE, has_text=False,
                description="A slider to pick a value."),
    ControlType("Panel", "Panel", (200, 100), ["Click"], has_text=False, container=True,
                description="Groups other controls."),
    ControlType("GroupBox", "GroupBox", (200, 100), [], container=True,
                description="A frame with a caption around other controls."),
    ControlType("Timer", "Timer", (0, 0), ["Tick"],
                [_p("Interval", "int", 100, "Milliseconds between Tick events.", category="Behavior"),
                 _p("Enabled", "bool", False, "Start the timer when the form loads.", category="Behavior")],
                has_text=False, nonvisual=True, common_events=False,
                description="Raises Tick at a regular interval."),
    ControlType("MenuStrip", "MenuStrip", (0, 0), [],
                [_p("Items", "menu", [], "Menu items - double-click to edit.", category="Data")],
                has_text=False, nonvisual=True, common_events=False,
                description="The form's menu bar."),
    ControlType("TabControl", "TabControl", (200, 100), ["SelectedIndexChanged"],
                [_p("TabPages", "list", "TabPage1;TabPage2", "Page captions separated by ;", category="Data"),
                 _p("SelectedIndex", "int", 0, "Index of the page shown (0 = first).", category="Behavior")],
                has_text=False, container=True,
                description="Pages of controls selected with tabs. Click a tab in the designer to edit it."),
    ControlType("TreeView", "TreeView", (121, 97), ["SelectedIndexChanged", "DoubleClick"],
                [_p("Nodes", "list", "", "Nodes separated by ; - use / for children "
                    "(Root;Root/Child;Root/Child2).", category="Data")],
                has_text=False, description="A hierarchy of nodes."),
    ControlType("ListView", "ListView", (200, 97), ["SelectedIndexChanged", "DoubleClick"],
                [_p("Columns", "list", "Column1;Column2", "Column headers separated by ;", category="Data"),
                 _p("Items", "list", "", "Rows separated by ; with cells separated by | (a|b;c|d).",
                    category="Data"),
                 _p("View", "enum", "Details", "Details shows columns with headers.", ("Details", "List"),
                    category="Appearance")],
                has_text=False, description="A list of items with columns."),
    ControlType("DataGridView", "DataGridView", (240, 150), ["SelectedIndexChanged", "CellChanged"],
                [_p("Columns", "list", "Column1;Column2", "Column headers separated by ;", category="Data"),
                 _p("Rows", "list", "", "Rows separated by ; with cells separated by | (a|b;c|d).",
                    category="Data"),
                 _p("ReadOnly", "bool", False, "Prevent editing the cells.", category="Behavior")],
                has_text=False, description="A grid of editable cells."),
    ControlType("DateTimePicker", "DateTimePicker", (200, 20), ["ValueChanged"],
                [_p("Value", "str", "", "Date as YYYY-MM-DD (time as HH:MM:SS); empty = today.",
                    category="Behavior"),
                 _p("Format", "enum", "Short", "Short = 2024-01-31, Long = Wednesday, 31 January 2024, "
                    "Time = 13:45:00.", ("Short", "Long", "Time"), category="Appearance")],
                has_text=False, description="Lets the user pick a date or a time."),
    ControlType("LinkLabel", "LinkLabel", (60, 17), ["Click"],
                [_p("LinkColor", "color", "#0066CC", "Colour of the link text.", category="Appearance")],
                description="A label that looks and acts like a hyperlink."),
    ControlType("StatusBar", "StatusBar", (200, 22), ["Click"], [],
                overrides=(("Dock", "Bottom"), ("Text", "Ready")),
                description="A status line, docked at the bottom of the form."),
    ControlType("ToolStrip", "ToolStrip", (0, 0), [],
                [_p("Items", "menu", [], "Tool bar buttons (Text \"-\" = separator) - double-click to edit.",
                    category="Data")],
                has_text=False, nonvisual=True, common_events=False,
                description="A tool bar under the menu; each button raises <ItemName>_Click."),
    ControlType("OpenFileDialog", "OpenFileDialog", (0, 0), [],
                [_p("Title", "str", "Open", category="Appearance"),
                 _p("Filter", "str", "All files|*.*", "Pairs of description|pattern, e.g. "
                    "Text files|*.txt|All|*.*", category="Behavior"),
                 _p("FileName", "str", "", "The chosen file (after ShowDialog).", category="Behavior"),
                 _p("InitialDirectory", "str", "", category="Behavior")],
                has_text=False, nonvisual=True, common_events=False,
                description="Asks the user for a file to open: ShowDialog() returns \"OK\" or \"Cancel\"."),
    ControlType("SaveFileDialog", "SaveFileDialog", (0, 0), [],
                [_p("Title", "str", "Save As", category="Appearance"),
                 _p("Filter", "str", "All files|*.*", "Pairs of description|pattern, e.g. "
                    "Text files|*.txt|All|*.*", category="Behavior"),
                 _p("FileName", "str", "", "The chosen file (after ShowDialog).", category="Behavior"),
                 _p("InitialDirectory", "str", "", category="Behavior")],
                has_text=False, nonvisual=True, common_events=False,
                description="Asks the user where to save a file: ShowDialog() returns \"OK\" or \"Cancel\"."),
    ControlType("ColorDialog", "ColorDialog", (0, 0), [],
                [_p("Color", "color", "#000000", "The chosen colour (after ShowDialog).", category="Behavior")],
                has_text=False, nonvisual=True, common_events=False,
                description="Lets the user pick a colour: ShowDialog() returns \"OK\" or \"Cancel\"."),
    ControlType("FontDialog", "FontDialog", (0, 0), [],
                [_p("FontName", "font", "Segoe UI", "The chosen font family.", category="Behavior"),
                 _p("FontSize", "int", 9, "The chosen size in points.", category="Behavior")],
                has_text=False, nonvisual=True, common_events=False,
                description="Lets the user pick a font: ShowDialog() returns \"OK\" or \"Cancel\"."),
    ControlType("FolderBrowserDialog", "FolderBrowserDialog", (0, 0), [],
                [_p("SelectedPath", "str", "", "The chosen folder (after ShowDialog).", category="Behavior")],
                has_text=False, nonvisual=True, common_events=False,
                description="Lets the user pick a folder: ShowDialog() returns \"OK\" or \"Cancel\"."),
    ControlType("ActiveX", "ActiveX", (100, 50), ["Click"],
                [_p("ProgID", "str", "Shell.Explorer.2", "COM ProgID of the ActiveX control "
                    "(e.g. Shell.Explorer.2, MSCAL.Calendar).", category="Behavior")],
                has_text=False, description="Hosts a Windows ActiveX (COM) control."),
]}


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
