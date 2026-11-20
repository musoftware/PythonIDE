"""WinForms forms of Visual Studio projects, opened IN PLACE (C#; VB.NET in winforms_vb.py).

``Form1.Designer.cs`` is the source of truth.  ``InitializeComponent`` is read statement by statement
(with the exact character span of every statement) into the neutral form model (radide/model.py) the
RAD designer edits, and written back by **patching only what changed**:

* a property that changed      -> that one statement is rewritten (left-hand side kept verbatim)
* a property reset to default  -> its statement is removed
* a new control                -> field declaration + ``new`` + a Visual-Studio style property block +
                                  ``Controls.Add`` (style follows the file: ``this.``/bare, full/short names)
* a deleted control            -> every statement that references it + its field declaration
* a renamed control            -> identifiers renamed in InitializeComponent and the fields (handlers
                                  keep their names, like Visual Studio)
* menus / tool bars / tab pages / list items / tool tips / images in the .resx

Everything the model does not understand (unknown statements and properties, comments, regions,
components such as ImageList / BindingSource, custom code outside InitializeComponent) stays
byte-identical; a form opened and saved without changes produces the identical file.

Public API (also used by radide.features.foreign_projects):
    STORE                       -> FORM_STORES entry (Form.load / Form.save of a Designer file)
    load_form(designer_path)    -> Form     (neutral model; extra["winforms"] carries the link)
    render_form(form)           -> str      (new Designer text, nothing written)
    save_form(form, path=None)  -> list[str] report lines
    add_event_handler(code, form, owner, event) -> (code, line)   handler in Form1.cs / Form1.vb
    PLUGIN (winforms-cs), see also winforms_vb.PLUGIN (winforms-vb): language plugins for
    project.form_languages - double-click creates handlers, Save writes the Designer file.

Designer hooks (optional plugin attributes, used by radide/properties.py and radide/toolbox.py):
    plugin.designer_profile          {"labels": {type: WinForms name}, "allowed": set} -> toolbox
    plugin.property_label(name, c)   .NET name of a neutral property (Location.X, Size.Width, Font.Bold)
    plugin.type_label(c)             System.Windows.Forms.Button ... in the Properties description
    form.extra["camel_names"]        model.Form.add names new controls button1 (C# files that do)

Layout: SplitContainer panels are pseudo Panel controls named "split1.Panel1" (hidden prop _wfp, never
written); children of TableLayoutPanel / FlowLayoutPanel keep their stored Location (no RAD dock/anchor);
the loaded form is run through radide/layout.relayout so the designer and the writer's baseline agree.
VB: deleting / renaming a control also fixes the Handles clauses of Form1.vb (disk + open editor).
"""
from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..controls import CONTROL_TYPES, FORM_EVENTS, format_anchor, menu_names, split_items
from ..importers.exe.dotnet import COLOR_NAMES, Parser, _lit, _match_brace
from ..languages.base import LanguagePlugin, RunSpec
from ..model import FORM_STORES, Control, Form
from .resx import ICON, ResxFile, image_ext, image_type_for

# ============================================================================ type tables
WF_TO_NEUTRAL = {
    "Button": "Button", "Label": "Label", "TextBox": "TextBox", "RichTextBox": "TextBox",
    "MaskedTextBox": "TextBox", "CheckBox": "CheckBox", "RadioButton": "RadioButton", "ListBox": "ListBox",
    "CheckedListBox": "ListBox", "ComboBox": "ComboBox", "PictureBox": "PictureBox",
    "ProgressBar": "ProgressBar", "NumericUpDown": "NumericUpDown", "TrackBar": "TrackBar",
    "Panel": "Panel", "FlowLayoutPanel": "Panel", "TableLayoutPanel": "Panel", "SplitContainer": "Panel",
    "GroupBox": "GroupBox", "Timer": "Timer", "MenuStrip": "MenuStrip", "ToolStrip": "ToolStrip",
    "StatusStrip": "StatusBar", "TabControl": "TabControl", "TreeView": "TreeView", "ListView": "ListView",
    "DataGridView": "DataGridView", "DateTimePicker": "DateTimePicker", "LinkLabel": "LinkLabel",
    "OpenFileDialog": "OpenFileDialog", "SaveFileDialog": "SaveFileDialog", "ColorDialog": "ColorDialog",
    "FontDialog": "FontDialog", "FolderBrowserDialog": "FolderBrowserDialog",
}
NEUTRAL_TO_WF = {
    "Button": "Button", "Label": "Label", "TextBox": "TextBox", "CheckBox": "CheckBox",
    "RadioButton": "RadioButton", "ListBox": "ListBox", "ComboBox": "ComboBox", "PictureBox": "PictureBox",
    "ProgressBar": "ProgressBar", "NumericUpDown": "NumericUpDown", "TrackBar": "TrackBar", "Panel": "Panel",
    "GroupBox": "GroupBox", "Timer": "Timer", "MenuStrip": "MenuStrip", "ToolStrip": "ToolStrip",
    "StatusBar": "StatusStrip", "TabControl": "TabControl", "TreeView": "TreeView", "ListView": "ListView",
    "DataGridView": "DataGridView", "DateTimePicker": "DateTimePicker", "LinkLabel": "LinkLabel",
    "OpenFileDialog": "OpenFileDialog", "SaveFileDialog": "SaveFileDialog", "ColorDialog": "ColorDialog",
    "FontDialog": "FontDialog", "FolderBrowserDialog": "FolderBrowserDialog",
}
# components created with (this.components) and kept in the tray (no Controls.Add)
COMPONENT_TYPES = {"Timer", "ToolTip", "ImageList", "ErrorProvider", "ContextMenuStrip", "BindingSource",
                   "NotifyIcon", "HelpProvider"}
NONVISUAL_WF = COMPONENT_TYPES | {"OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog",
                                  "FolderBrowserDialog", "BackgroundWorker", "PrintDocument", "PrintDialog",
                                  "PageSetupDialog", "PrintPreviewDialog", "FileSystemWatcher", "SerialPort",
                                  "DataSet", "EventLog", "Process"}
MENU_ITEM_TYPES = {"ToolStripMenuItem", "ToolStripButton", "ToolStripSeparator", "ToolStripLabel",
                   "ToolStripDropDownButton", "ToolStripSplitButton", "ToolStripStatusLabel",
                   "ToolStripComboBox", "ToolStripTextBox", "ToolStripProgressBar"}
MENU_OWNER_TYPES = {"MenuStrip", "ToolStrip", "StatusStrip", "ContextMenuStrip"}
UVSBC = {"Button", "CheckBox", "RadioButton", "TabPage"}   # UseVisualStyleBackColor = true in VS
# neutral event -> .NET event, (delegate, EventArgs) of the .NET event
EVENT_TO_NET = {"CellChanged": "CellValueChanged"}
EVENT_SIG = {
    "MouseDown": ("MouseEventHandler", "MouseEventArgs"), "MouseUp": ("MouseEventHandler", "MouseEventArgs"),
    "MouseMove": ("MouseEventHandler", "MouseEventArgs"), "MouseWheel": ("MouseEventHandler", "MouseEventArgs"),
    "MouseClick": ("MouseEventHandler", "MouseEventArgs"),
    "MouseDoubleClick": ("MouseEventHandler", "MouseEventArgs"),
    "KeyDown": ("KeyEventHandler", "KeyEventArgs"), "KeyUp": ("KeyEventHandler", "KeyEventArgs"),
    "KeyPress": ("KeyPressEventHandler", "KeyPressEventArgs"),
    "FormClosing": ("FormClosingEventHandler", "FormClosingEventArgs"),
    "FormClosed": ("FormClosedEventHandler", "FormClosedEventArgs"),
    "CellValueChanged": ("DataGridViewCellEventHandler", "DataGridViewCellEventArgs"),
    "CellClick": ("DataGridViewCellEventHandler", "DataGridViewCellEventArgs"),
    "LinkClicked": ("LinkLabelLinkClickedEventHandler", "LinkLabelLinkClickedEventArgs"),
    "AfterSelect": ("TreeViewEventHandler", "TreeViewEventArgs"),
}
FORMS_NS = "System.Windows.Forms"
DRAWING_NS = "System.Drawing"
HIDDEN = ("_wf", "_wft", "_wfp")  # hidden control props: original name / original .NET type / split panel of
LAYOUT_PANELS = {"TableLayoutPanel", "FlowLayoutPanel"}   # .NET places their children (cells / flow)
# neutral property -> how the Properties window names it for a WinForms form (.NET names)
NET_PROPERTY_LABELS = {
    "Left": "Location.X", "Top": "Location.Y", "Width": "Size.Width", "Height": "Size.Height",
    "FontName": "Font.Name", "FontSize": "Font.Size", "FontBold": "Font.Bold", "FontItalic": "Font.Italic",
    "ToolTip": "ToolTip on toolTip1", "Parent": "Parent (Controls.Add)", "TabPage": "Parent TabPage index",
}


def short(t: str) -> str:
    return t.split(".")[-1].split("<")[0]


def _color_hex(v) -> str:
    """Neutral colour of a literal value: #RRGGBB, '' for SystemColors / unknown names."""
    if isinstance(v, tuple) and v[0] == "color":
        return v[1]
    if isinstance(v, tuple) and v[0] == "enum":
        q = v[1]
        if "SystemColors" in q:
            return ""
        return COLOR_NAMES.get(q.split(".")[-1].lower(), "")
    return ""


_HEX_TO_NAME = {}
for _n, _h in COLOR_NAMES.items():
    _HEX_TO_NAME.setdefault(_h, _n)
_PROPER = {n.lower(): n for n in (
    "Black White Red Green Blue Yellow Gray DarkGray LightGray Silver Maroon Navy Purple Teal Olive Lime Aqua "
    "Cyan Fuchsia Magenta Orange DarkOrange Pink Brown Gold DarkBlue DarkRed DarkGreen LightBlue LightGreen "
    "LightYellow LightPink SteelBlue RoyalBlue DodgerBlue SkyBlue Crimson Indigo Violet Khaki Beige Ivory "
    "Lavender Salmon Tomato Coral Chocolate Tan Wheat SeaGreen").split()}


def _enum_last(v) -> str:
    if isinstance(v, tuple) and v[0] == "enum":
        return v[1].split("|")[-1].split(".")[-1]
    return ""


# ============================================================================ text scanning
def skip_string_cs(src: str, i: int) -> int:
    """Index after the C# string / char literal starting at src[i] (a quote, maybe after @ or $)."""
    n = len(src)
    j = i
    verbatim = False
    while j < n and src[j] in "@$":
        verbatim = verbatim or src[j] == "@"
        j += 1
    q = src[j]
    if q == '"' and src.startswith('"""', j):            # raw string literal
        k = src.find('"""', j + 3)
        return n if k < 0 else k + 3
    j += 1
    while j < n:
        c = src[j]
        if c == "\\" and not verbatim:
            j += 2
            continue
        if c == q:
            if verbatim and q == '"' and src.startswith('""', j):
                j += 2
                continue
            return j + 1
        if c == "\n" and not verbatim:
            return j
        j += 1
    return n


def mask_cs(src: str) -> str:
    """Same length as src with strings / chars / comments replaced by spaces (newlines kept)."""
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c == "/" and src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if c in "\"'" or (c in "@$" and i + 1 < n and src[i + 1] in "\"@$"):
            j = skip_string_cs(src, i)
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = max(j, i + 1)
            continue
        i += 1
    return "".join(out)


@dataclass
class Stmt:
    start: int                 # full span (line-based) in the file text
    end: int
    s0: int                    # exact statement span
    s1: int
    text: str
    kind: str = "other"        # comment | directive | new | prop | event | add | items | call | decl | other
    owner: str | None = None   # control / item name, "" = the form, None = unknown
    prop: str = ""             # .NET property path for kind == "prop"
    node: object = None        # value AST (C# parser of radide.importers.exe.dotnet)
    args: list = field(default_factory=list)
    wtype: str = ""
    method: str = ""
    indent: str = ""
    refs: set = field(default_factory=set)      # identifiers referenced (outside strings)


# ============================================================================ dialect: C#
class CSharpDialect:
    lang = "cs"
    ext = ".cs"
    comment = "//"
    nl = "\r\n"

    # ---------------------------------------------------------------- structure
    def find_class(self, text: str, name_hint: str = ""):
        """(class name, body start (after '{'), body end (index of '}'), class header start)."""
        masked = mask_cs(text)
        for m in re.finditer(r"\bclass\s+(\w+)[^{;]*\{", masked):
            if name_hint and m.group(1) != name_hint and "partial" not in masked[max(0, m.start() - 40):m.start()]:
                continue
            end = _match_brace(text, m.end() - 1)
            if end > 0:
                return m.group(1), m.end(), end, m.start()
        return None

    def find_ic(self, text: str, b0: int, b1: int):
        """Span (body start, body end) of InitializeComponent inside the class body."""
        masked = mask_cs(text)
        m = re.compile(r"\bvoid\s+InitializeComponent\s*\(\s*\)\s*\{").search(masked, b0, b1)
        if not m:
            return None
        end = _match_brace(text, m.end() - 1)
        return (m.end(), end) if end > 0 else None

    def split(self, text: str, b0: int, b1: int) -> list[Stmt]:
        masked = mask_cs(text)
        out: list[Stmt] = []
        i = b0
        while i < b1:
            c = text[i]
            if c in " \t\r\n":
                i += 1
                continue
            s0 = i
            if text.startswith("//", i) or text.startswith("/*", i):
                if text.startswith("//", i):
                    j = text.find("\n", i)
                    s1 = b1 if j < 0 or j > b1 else j
                    if text[s1 - 1:s1] == "\r":
                        s1 -= 1
                else:
                    j = text.find("*/", i + 2)
                    s1 = b1 if j < 0 else j + 2
                out.append(self._stmt(text, s0, s1, b0, b1, "comment"))
                i = s1
                continue
            if c == "#":
                j = text.find("\n", i)
                s1 = b1 if j < 0 or j > b1 else j
                if text[s1 - 1:s1] == "\r":
                    s1 -= 1
                out.append(self._stmt(text, s0, s1, b0, b1, "directive"))
                i = s1
                continue
            depth = 0
            block = re.match(r"(if|for|foreach|while|using|try|lock|switch|do)\b|\{", text[i:i + 9]) is not None
            j = i
            while j < b1:
                ch = masked[j]
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
                    if depth == 0 and ch == "}" and block:
                        rest = masked[j + 1:b1].lstrip()
                        if not rest.startswith(("else", "catch", "finally", "while")):
                            j += 1
                            break
                elif ch == ";" and depth <= 0:
                    j += 1
                    break
                j += 1
            out.append(self._stmt(text, s0, j, b0, b1, "code"))
            i = j
        return out

    @staticmethod
    def _stmt(text, s0, s1, b0, b1, kind) -> Stmt:
        ls = text.rfind("\n", b0, s0) + 1
        if ls < b0 or text[ls:s0].strip():
            ls = s0
        le = s1
        k = s1
        while k < b1 and text[k] in " \t":
            k += 1
        if text.startswith("\r\n", k):
            le = k + 2
        elif text.startswith("\n", k):
            le = k + 1
        st = Stmt(ls, le, s0, s1, text[s0:s1], kind if kind != "code" else "other")
        st.indent = text[ls:s0] if ls < s0 else ""
        return st

    def to_cs(self, stmt_text: str) -> str:
        return stmt_text

    def field_decls(self, text: str, b0: int, b1: int, ic_span) -> dict:
        """name -> (type, line start, line end) of field declarations in the class body."""
        out = {}
        masked = mask_cs(text)
        rx = re.compile(r"(?m)^[ \t]*((?:(?:private|public|protected|internal|readonly|static|new)\s+)+)"
                        r"([\w.<>\[\]?,]+)\s+(\w+)\s*(?:=[^;]*)?;[ \t]*\r?\n?")
        for m in rx.finditer(masked, b0, b1):
            if ic_span and ic_span[0] <= m.start() <= ic_span[1]:
                continue
            # only at class depth (not inside methods)
            seg = masked[b0:m.start()]
            if seg.count("{") - seg.count("}") != 0:
                continue
            out[m.group(3)] = (m.group(2), m.start(), m.end())
        return out

    # ---------------------------------------------------------------- emission
    def end(self) -> str:
        return ";"

    def lit_str(self, s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n") \
            .replace("\t", "\\t") + '"'

    def lit_char(self, s: str) -> str:
        c = (s or "\0")[:1]
        return "'\\''" if c == "'" else "'\\\\'" if c == "\\" else f"'{c}'"

    def lit_bool(self, b: bool) -> str:
        return "true" if b else "false"

    def lit_float(self, v: float) -> str:
        s = repr(float(v))
        s = s[:-2] if s.endswith(".0") else s
        return s + "F"

    def new(self, typ: str, args: str = "") -> str:
        return f"new {typ}({args})"

    def enum_or(self, parts: list[str], typ: str) -> str:
        if len(parts) == 1:
            return parts[0]
        return f"(({typ})(({' | '.join(parts)})))" if self.style.qualified else " | ".join(parts)

    def new_array(self, typ: str, items: list[str], ind: str) -> str:
        if not items:
            return f"new {typ}[] {{}}"
        if getattr(self, "style", None) is not None and self.style.inline_arrays:
            return f"new {typ}[] {{ " + ", ".join(items) + " }"
        inner = (","+self.nl+ind).join(items)
        return f"new {typ}[] {{{self.nl}{ind}{inner}}}"

    def assign(self, target: str, value: str) -> str:
        return f"{target} = {value};"

    def call(self, target: str, args: str = "") -> str:
        return f"{target}({args});"

    def wire(self, owner_expr: str, event: str, handler: str, delegate: str) -> str:
        if self.style.me:
            return f"{owner_expr}.{event} += new {delegate}({self.style.me}{handler});"
        return f"{owner_expr}.{event} += {handler};"

    def field_decl(self, name: str, typ: str) -> str:
        return f"private {typ} {name};"

    def comment_line(self, text: str) -> str:
        sp = " " if getattr(getattr(self, "style", None), "comment_space", True) else ""
        return f"//{sp}{text}"

    def resources_decl(self, cls: str) -> str:
        t = "System.ComponentModel.ComponentResourceManager"
        return f"{t} resources = new {t}(typeof({cls}));"

    def get_object(self, key: str, typ: str) -> str:
        return f"(({typ})(resources.GetObject({self.lit_str(key)})))"

    def components_new(self) -> str:
        return f"{self.style.me}components = new System.ComponentModel.Container();"


@dataclass
class Style:
    me: str = "this."          # "this." / "Me." / ""
    qualified: bool = True     # System.Windows.Forms.Button vs Button
    inline_arrays: bool = False  # new T[] { a, b } on one line (VS 2022) vs one element per line (older VS)
    comment_space: bool = True   # block headers "// " + "// button1" (C#) vs "'" + "'Button1" (VB)


# ============================================================================ parsed designer file
class DesignerDoc:
    """One Form1.Designer.cs / .vb: text + statements of InitializeComponent + what they mean."""

    def __init__(self, path: Path, text: str, dialect):
        self.path = Path(path)
        self.text = text
        self.d = dialect
        self.ok = False
        self.problem = ""
        self.parse()

    # ---------------------------------------------------------------- parse
    def parse(self) -> None:
        d, text = self.d, self.text
        cls = d.find_class(text, self.path.name.split(".")[0])
        if cls is None:
            self.problem = "no class found"
            return
        self.cls_name, self.b0, self.b1, self.cls_start = cls
        ic = d.find_ic(text, self.b0, self.b1)
        if ic is None:
            self.problem = "no InitializeComponent method"
            return
        self.ic0, self.ic1 = ic
        self.stmts = d.split(text, self.ic0, self.ic1)
        self.fields = d.field_decls(text, self.b0, self.b1, ic)
        self.controls: dict[str, dict] = {}    # name -> {"wtype", "new", "props": {prop: idx}, "parent", ...}
        self.items: dict[str, dict] = {}       # menu/tool strip items
        self.tabpages: dict[str, dict] = {}
        self.order: list[str] = []
        self.form_props: dict[str, int] = {}
        self.events: list[tuple[str, str, str, int]] = []    # (owner, event, method, stmt idx)
        self.adds: dict[str, list[int]] = {}   # parent ("" = form) -> stmt idx of Controls.Add/AddRange
        self.children: dict[str, list[str]] = {}
        self.parent_of: dict[str, str] = {}
        self.parent_expr: dict[str, str] = {}  # child -> raw parent expression (SplitContainer panels)
        self.item_lists: dict[str, int] = {}   # owner -> stmt idx of Items/DropDownItems AddRange
        self.item_children: dict[str, list[str]] = {}
        self.list_items: dict[str, int] = {}   # ListBox/ComboBox owner -> Items.AddRange stmt idx
        self.tooltips: dict[str, tuple[str, int, str]] = {}  # control -> (text, idx, tooltip component)
        self.resources_idx = -1
        self.components_idx = -1
        self.suspend_idx = -1
        self.resume_idx = -1
        self.apply_res: dict[str, str] = {}    # owner -> resx key prefix (ApplyResources, localizable forms)
        known = set(self.fields)
        for i, st in enumerate(self.stmts):
            if st.kind != "other":
                continue
            self._classify(i, st, known)
        self.style = self._detect_style()
        d.style = self.style
        self.ok = True

    def _classify(self, i: int, st: Stmt, known: set) -> None:
        cs = self.d.to_cs(st.text)
        if cs is None:
            return
        st.refs = set(re.findall(r"\b[A-Za-z_]\w*\b", mask_cs(cs)))
        try:
            node = Parser(cs).statement()
        except Exception:  # noqa: BLE001 - unknown statements are simply kept
            return
        if node[0] == "decl":
            st.kind = "decl"
            if "ComponentResourceManager" in node[1]:
                self.resources_idx = i
            # locals (TreeNode treeNode1 = ..., ListViewItem ...): their assignments are not form props
            known.update(n for n, _init in node[2])
            return
        if node[0] != "expr":
            return
        e = node[1]
        if e[0] == "assign" and e[1] == "=":
            tgt, val = e[2], e[3]
            chain = _chain(tgt)
            if chain is None:
                return
            if len(chain) == 1 and val[0] == "new" and chain[0] in ("components",):
                st.kind, st.owner, st.wtype = "new", None, val[1]
                self.components_idx = i
                return
            if len(chain) == 1 and val[0] == "new" and (chain[0] in self.fields or
                                                        (short(val[1]) not in _VALUE_TYPES and
                                                         chain[0] not in _FORM_PROPS_GUESS)):
                name, wtype = chain[0], val[1]
                sw = short(wtype)
                st.kind, st.owner, st.wtype = "new", name, wtype
                st.args = list(val[2] or [])
                if sw in MENU_ITEM_TYPES:
                    self.items[name] = {"wtype": wtype, "new": i, "props": {}}
                elif sw == "TabPage":
                    self.tabpages[name] = {"wtype": wtype, "new": i, "props": {}, "parent": None}
                else:
                    self.controls[name] = {"wtype": wtype, "new": i, "props": {}}
                    self.order.append(name)
                known.add(name)
                return
            owner, prop = None, ""
            if chain[0] in self.controls or chain[0] in self.items or chain[0] in self.tabpages:
                owner, prop = chain[0], ".".join(chain[1:])
            elif chain[0] not in known or len(chain) == 1:
                owner, prop = "", ".".join(chain)
            if owner is None or not prop:
                return
            st.kind, st.owner, st.prop, st.node = "prop", owner, prop, val
            self._props_of(owner)[prop] = i
            if owner == "" and prop not in self.form_props:
                self.form_props[prop] = i
            return
        if e[0] == "assign" and e[1] in ("+=",):
            chain = _chain(e[2])
            if not chain:
                return
            owner = chain[0] if len(chain) > 1 else ""
            ev = chain[-1]
            meth = _handler_of(e[3])
            if meth is None:
                return
            st.kind, st.owner, st.method, st.prop = "event", owner, meth, ev
            self.events.append((owner, ev, meth, i))
            return
        if e[0] == "call":
            func = e[1]
            chain = _chain(func)
            if chain is None:
                st.kind = "call"
                return
            meth = chain[-1]
            recv = chain[:-1]
            st.kind, st.method = "call", meth
            if meth in ("Add", "AddRange") and recv and recv[-1] == "Controls":
                owner_chain = recv[:-1]
                parent = owner_chain[0] if owner_chain else ""
                st.kind, st.owner = "add", parent
                st.wtype = ".".join(owner_chain)               # raw parent expr e.g. split1.Panel2
                kids = []
                for a in e[2]:
                    if a[0] == "newarr":
                        kids += [_chain(x)[0] for x in a[3] or [] if _chain(x)]
                    else:
                        ch = _chain(a)
                        if ch:
                            kids.append(ch[0])
                        break                   # TableLayoutPanel: Add(ctrl, col, row)
                st.args = kids
                self.adds.setdefault(parent, []).append(i)
                for k in kids:
                    if parent in self.tabpages:
                        self.tabpages[parent].setdefault("kids", []).append(k)
                    if k in self.tabpages and parent in self.controls:
                        self.tabpages[k]["parent"] = parent      # tabControl1.Controls.Add(tabPage1)
                    self.children.setdefault(parent, []).append(k)
                    self.parent_of[k] = parent
                    self.parent_expr[k] = st.wtype
                return
            if meth in ("Add", "AddRange") and recv and recv[-1] == "TabPages" and len(recv) >= 2:
                st.kind, st.owner = "add", recv[0]
                kids = []
                for a in e[2]:
                    if a[0] == "newarr":
                        kids += [_chain(x)[0] for x in a[3] or [] if _chain(x)]
                    elif _chain(a):
                        kids.append(_chain(a)[0])
                st.args = kids
                st.wtype = "TabPages"
                for k in kids:
                    if k in self.tabpages:
                        self.tabpages[k]["parent"] = recv[0]
                return
            if meth in ("AddRange", "Add") and len(recv) >= 2 and recv[-1] in ("Items", "DropDownItems"):
                owner = recv[0]
                args = e[2]
                vals = args[0][3] if len(args) == 1 and args[0][0] == "newarr" else args
                refs = [_chain(x)[0] if _chain(x) and _chain(x)[0] in self.items else None for x in vals]
                if refs and all(refs):
                    st.kind, st.owner, st.args = "items", owner, refs
                    self.item_lists[owner] = i
                    self.item_children.setdefault(owner, []).extend(refs)
                else:
                    st.kind, st.owner, st.args = "listitems", owner, [_lit(x) for x in vals]
                    self.list_items[owner] = i
                return
            if meth == "SetToolTip" and len(recv) == 1 and len(e[2]) == 2:
                ch = _chain(e[2][0])
                v = _lit(e[2][1])
                if ch and isinstance(v, str):
                    st.kind, st.owner = "tooltip", ch[0]
                    self.tooltips[ch[0]] = (v, i, recv[0])
                return
            if meth == "ApplyResources" and len(e[2]) >= 2:
                ch = _chain(e[2][0])
                v = _lit(e[2][1])
                if ch and isinstance(v, str):
                    owner = "" if ch[0] in ("this", "Me", "$this") else ch[0]
                    st.kind, st.owner = "applyres", owner
                    self.apply_res[owner] = v
                return
            if not recv and meth == "SuspendLayout" and self.suspend_idx < 0:
                self.suspend_idx = i
            if not recv and meth == "ResumeLayout":
                self.resume_idx = i
            if recv and recv[0] in self.controls:
                st.owner = recv[0]

    def _props_of(self, owner: str) -> dict:
        if owner == "":
            return self.form_props
        for tbl in (self.controls, self.items, self.tabpages):
            if owner in tbl:
                return tbl[owner]["props"]
        return {}

    def _detect_style(self) -> Style:
        me_count = bare = 0
        qual = short_ = 0
        me = "Me." if self.d.lang == "vb" else "this."
        for st in self.stmts:
            if st.kind in ("comment", "directive"):
                continue
            t = st.text.lstrip()
            if t.startswith(me):
                me_count += 1
            elif st.kind in ("prop", "new", "event", "add"):
                bare += 1
            if st.kind == "new" and st.wtype:
                if "." in st.wtype:
                    qual += 1
                else:
                    short_ += 1
            if st.kind == "prop" and re.search(r"\bSystem\.Drawing\.(Point|Size)\b", st.text):
                qual += 1
            elif st.kind == "prop" and re.search(r"\bnew\s+(Point|Size)\s*\(|\bNew\s+(Point|Size)\s*\(", st.text):
                short_ += 1
        inline = multi = 0
        for st in self.stmts:
            if st.kind in ("items", "listitems", "add") and re.search(r"\[\]\s*\{", st.text):
                if re.search(r"\[\]\s*\{[ \t]*\r?\n", st.text):
                    multi += 1
                else:
                    inline += 1
        if not inline and not multi:
            inline = 0 if me_count >= bare and qual >= short_ else 1    # no example: follow the file's era
        spaced = tight = 0
        for st in self.stmts:
            if st.kind == "comment":
                t = st.text.rstrip("\r\n").lstrip()
                if t in ("'", "//"):
                    tight += 1
                elif t in ("' ", "// "):
                    spaced += 1
        space = spaced > tight if spaced != tight else self.d.lang != "vb"
        return Style(me if me_count >= bare else "", qual >= short_, inline > multi, space)

    def value(self, owner: str, prop: str):
        idx = self._props_of(owner).get(prop)
        if idx is None:
            return None
        return wf_value(self.stmts[idx].node)

    def node(self, owner: str, prop: str):
        idx = self._props_of(owner).get(prop)
        return None if idx is None else self.stmts[idx].node

    def is_split(self, name: str) -> bool:
        return short(self.controls.get(name, {}).get("wtype", "")) == "SplitContainer"

    def split_offset(self, split: str) -> tuple[int, int]:
        """Where Panel2 of a SplitContainer starts (RAD shows both panels' children in the container)."""
        dist = self.value(split, "SplitterDistance")
        width = self.value(split, "SplitterWidth")
        dist = _int(dist) if isinstance(dist, (int, float)) else 50
        width = _int(width) if isinstance(width, (int, float)) else 4
        if _enum_last(self.value(split, "Orientation")) == "Horizontal":
            return 0, dist + width
        return dist + width, 0


_VALUE_TYPES = {"Point", "PointF", "Size", "SizeF", "Font", "Padding", "Rectangle", "Icon", "Bitmap", "Cursor",
                "Color", "decimal", "Decimal"}
_FORM_PROPS_GUESS = {"Font", "Icon","BackgroundImage", "Cursor", "Padding", "Margin", "MinimumSize",
                     "MaximumSize", "ClientSize", "Size", "Location", "AutoScaleDimensions"}


def _chain(node) -> list[str] | None:
    """this.a.b.C -> ['a', 'b', 'C'];  a.b -> ['a', 'b'];  None for anything else."""
    parts = []
    while node is not None:
        if node[0] == "member":
            parts.append(node[2])
            node = node[1]
        elif node[0] == "name":
            if node[1] not in ("this", "Me", "base", "MyBase"):
                parts.append(node[1])
            break
        elif node[0] == "paren":
            node = node[1]
        elif node[0] == "cast":
            node = node[-1]
        else:
            return None
    return list(reversed(parts)) if parts else None


def _handler_of(val) -> str | None:
    if val[0] == "new" and val[2]:
        ch = _chain(val[2][0])
        return ch[-1] if ch else None
    if val[0] in ("name", "member"):
        ch = _chain(val)
        return ch[-1] if ch else None
    return None


def wf_value(node):
    """Literal value of a designer expression (dotnet._lit + resources)."""
    if node is None:
        return None
    n = node
    while n[0] in ("paren", "cast"):
        n = n[-1]
    if n[0] == "call":
        ch = _chain(n[1])
        if ch and ch[-1] in ("GetObject", "GetString") and n[2] and n[2][0][0] == "str":
            return ("res" if ch[-1] == "GetObject" else "resstr", n[2][0][1])
    try:
        return _lit(node)
    except Exception:  # noqa: BLE001
        return None


# ============================================================================ designer -> neutral form
def _cache_dir(path: Path) -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    h = hashlib.sha1(str(Path(path).resolve().parent).lower().encode("utf-8")).hexdigest()[:12]
    return Path(base) / "RADIDE" / "foreign" / h / "winforms"


def _default_font(doc: DesignerDoc) -> tuple[str, float]:
    v = doc.value("", "AutoScaleDimensions")
    if isinstance(v, tuple) and len(v) >= 3 and v[1] == 6 and v[2] == 13:
        return "Microsoft Sans Serif", 8.25
    return "Segoe UI", 9.0


def _font_of(v):
    """('Font', name, size, style...) -> (name, size, bold, italic) or None."""
    if not (isinstance(v, tuple) and v and v[0] == "Font"):
        return None
    name = v[1] if len(v) > 1 and isinstance(v[1], str) else None
    size = v[2] if len(v) > 2 and isinstance(v[2], (int, float)) else None
    style = " ".join(x[1] for x in v[3:] if isinstance(x, tuple) and x[0] == "enum")
    if name is None or size is None:
        return None
    return name, float(size), "Bold" in style, "Italic" in style


def _int(x) -> int:
    return int(round(x)) if isinstance(x, (int, float)) else 0


def menu_offset(doc: DesignerDoc) -> int:
    """Height of the top-level MenuStrip + ToolStrip docked at the top (RAD draws them outside the client)."""
    off = 0
    for name, c in doc.controls.items():
        sw = short(c["wtype"])
        if sw not in ("MenuStrip", "ToolStrip") or doc.parent_of.get(name, None) != "":
            continue
        dock = _enum_last(doc.value(name, "Dock"))
        if dock not in ("", "Top"):
            continue
        if doc.value(name, "Visible") is False:
            continue
        size = doc.value(name, "Size")
        h = _int(size[2]) if isinstance(size, tuple) and len(size) >= 3 else (24 if sw == "MenuStrip" else 25)
        off += h
    return off


class Loader:
    """Builds the neutral Form of a DesignerDoc (deterministic: also used for the baseline of a save)."""

    def __init__(self, doc: DesignerDoc, resx: ResxFile | None, extract: bool = True):
        self.doc, self.resx, self.extract = doc, resx, extract
        self.notes: list[str] = []

    def res_string(self, key):
        return self.resx.get_string(key) if self.resx is not None else None

    def res_file(self, key: str) -> str:
        if self.resx is None:
            return ""
        data = self.resx.get_bytes(key)
        if not data:
            return ""
        d = _cache_dir(self.doc.path) / self.doc.path.name.split(".")[0]
        f = d / (re.sub(r"[^\w.$-]", "_", key) + "_" + hashlib.sha1(data).hexdigest()[:8] + image_ext(data))
        if self.extract and not f.exists():
            try:
                d.mkdir(parents=True, exist_ok=True)
                f.write_bytes(data)
            except OSError:
                return ""
        return str(f)

    def val(self, owner: str, prop: str):
        v = self.doc.value(owner, prop)
        if v is None and owner in self.doc.apply_res and self.resx is not None:
            key = f"{self.doc.apply_res[owner]}.{prop}" if owner else f"$this.{prop}"
            e = self.resx.entry(key)
            if e is not None and e.value is not None:
                v = _resx_value(e)
        if isinstance(v, tuple) and v[0] == "resstr":
            return self.res_string(v[1])
        return v

    def build(self) -> Form:
        doc = self.doc
        offset = menu_offset(doc)
        fname, fsize = _default_font(doc)
        form_font = _font_of(self.val("", "Font")) or (fname, fsize, False, False)
        form = Form()
        fp = form.props
        fp["Name"] = doc.cls_name
        t = self.val("", "Text")
        fp["Text"] = t if isinstance(t, str) else ""
        cs = self.val("", "ClientSize")
        if isinstance(cs, tuple) and len(cs) >= 3:
            fp["Width"], fp["Height"] = _int(cs[1]), _int(cs[2]) - offset
        else:
            sz = self.val("", "Size")
            if isinstance(sz, tuple) and len(sz) >= 3:
                fp["Width"], fp["Height"] = _int(sz[1]) - 16, _int(sz[2]) - 39 - offset
            else:
                fp["Width"], fp["Height"] = 284, 261 - offset
        fp["BackColor"] = _color_hex(self.val("", "BackColor"))
        sp = _enum_last(self.val("", "StartPosition"))
        fp["StartPosition"] = "CenterScreen" if sp in ("CenterScreen", "CenterParent") else "Manual"
        fb = _enum_last(self.val("", "FormBorderStyle"))
        fp["FormBorderStyle"] = "FixedSingle" if fb.startswith("Fixed") or fb == "None" else "Sizable"
        fp["TopMost"] = self.val("", "TopMost") is True
        fp["WindowState"] = "Maximized" if _enum_last(self.val("", "WindowState")) == "Maximized" else "Normal"
        icon = self.val("", "Icon")
        fp["Icon"] = self.res_file(icon[1]) if isinstance(icon, tuple) and icon[0] == "res" else ""
        fonts: dict[str, tuple] = {}

        def font_for(name: str, depth=0):
            if name in fonts:
                return fonts[name]
            f = _font_of(self.val(name, "Font")) if name else None
            if f is None:
                par = doc.parent_of.get(name, "")
                if par in doc.tabpages:
                    par = doc.tabpages[par].get("parent") or ""
                f = font_for(par, depth + 1) if par and depth < 30 else form_font
            fonts[name] = f
            return f

        for name in doc.order:
            c = doc.controls[name]
            ctrl = self.control(name, c, offset, font_for(name))
            if ctrl is not None:
                form.controls.append(ctrl)
        self._split_panels(form)
        for ctrl in form.controls:
            par = doc.parent_of.get(ctrl.name, "")
            if par in doc.controls and short(doc.controls[par]["wtype"]) in LAYOUT_PANELS:
                # cells / flow: .NET computes the place; RAD shows the stored Location and
                # does not re-dock or re-anchor them
                if "Dock" in ctrl.props:
                    ctrl.props["Dock"] = "None"
                if "Anchor" in ctrl.props:
                    ctrl.props["Anchor"] = "Top, Left"
        # containers before children, original order otherwise
        by = {c.name: c for c in form.controls}
        ordered, seen = [], set()

        def place(c, depth=0):
            if c.name in seen or depth > 30:
                return
            par = c.props.get("Parent") or ""
            if par in by:
                place(by[par], depth + 1)
            seen.add(c.name)
            ordered.append(c)
        for c in form.controls:
            place(c)
        form.controls = ordered
        # the designer snaps docked / anchored controls (radide/layout.py): do it here so the form
        # the designer shows and the baseline the writer compares with are the same
        try:
            from ..layout import relayout
            relayout(form)
        except Exception:  # noqa: BLE001
            pass
        form.extra["winforms"] = {"designer": str(doc.path), "lang": doc.d.lang, "offset": offset,
                                  "class": doc.cls_name}
        if doc.d.lang == "cs":
            # Visual Studio names new C# controls button1 / textBox1 (VB: Button1) - follow the file
            names = [n for n in doc.controls if n != "components"]
            lower = sum(1 for n in names if n[:1].islower())
            form.extra["camel_names"] = lower * 2 >= len(names)
        return form

    def _split_panels(self, form: Form) -> None:
        """SplitContainer: its Panel1 / Panel2 become pseudo Panel controls ("split1.Panel1", hidden prop
        _wfp) so children keep their .NET coordinates and dock inside their panel; never written."""
        doc = self.doc
        for c in list(form.controls):
            if not doc.is_split(c.name):
                continue
            w, h = int(c.props.get("Width", 0)), int(c.props.get("Height", 0))
            ox, oy = doc.split_offset(c.name)
            dist = doc.value(c.name, "SplitterDistance")
            dist = _int(dist) if isinstance(dist, (int, float)) else 50
            if oy:
                rects = [(0, 0, w, dist), (0, oy, w, max(0, h - oy))]
                anchors = ["Top, Left, Right", "Top, Bottom, Left, Right"]
            else:
                rects = [(0, 0, dist, h), (ox, 0, max(0, w - ox), h)]
                anchors = ["Top, Bottom, Left", "Top, Bottom, Left, Right"]
            idx = form.controls.index(c) + 1
            for i, ((x, y, pw, ph), anc) in enumerate(zip(rects, anchors), 1):
                pn = f"{c.name}.Panel{i}"
                props = CONTROL_TYPES["Panel"].default_props(pn)
                props.update({"Parent": c.name, "Left": x, "Top": y, "Width": pw, "Height": ph, "_wfp": c.name})
                if "Anchor" in props:
                    props["Anchor"] = anc
                for k in ("FontName", "FontSize", "FontBold", "FontItalic"):
                    if k in props and k in c.props:
                        props[k] = c.props[k]
                form.controls.insert(idx, Control("Panel", props))
                idx += 1

    def control(self, name: str, c: dict, offset: int, font) -> Control | None:
        doc = self.doc
        wt = c["wtype"]
        sw = short(wt)
        nt = WF_TO_NEUTRAL.get(sw)
        if nt is None:
            if sw in NONVISUAL_WF or c.get("component") or sw in COMPONENT_TYPES:
                return None          # tray component RAD does not know: kept verbatim, not shown
            nt = "Panel"             # unknown visual control: a placeholder that round-trips unchanged
            self.notes.append(f"{name}: {sw} is shown as a placeholder (kept unchanged)")
        ct = CONTROL_TYPES[nt]
        p = ct.default_props(name)
        p["_wf"], p["_wft"] = name, wt
        v = self.val
        par = doc.parent_of.get(name, "")
        page = None
        if par in doc.tabpages:
            tp = doc.tabpages[par]
            tc = tp.get("parent") or ""
            pages = doc_tab_pages(doc, tc)
            page = pages.index(par) if par in pages else 0
            par = tc
        if par and par not in doc.controls:
            par = ""
        p["Parent"] = par
        if page is not None:
            p["TabPage"] = page
        if not ct.nonvisual:
            loc, size = v(name, "Location"), v(name, "Size")
            if isinstance(loc, tuple) and len(loc) >= 3:
                p["Left"], p["Top"] = _int(loc[1]), _int(loc[2]) - (offset if par == "" else 0)
            else:
                p["Left"], p["Top"] = 0, -offset if par == "" else 0
            if par and doc.is_split(par) and doc.parent_expr.get(name, "").endswith((".Panel1", ".Panel2")):
                p["Parent"] = f"{par}.{doc.parent_expr[name].rsplit('.', 1)[1]}"    # pseudo panel (build)
            if isinstance(size, tuple) and len(size) >= 3:
                p["Width"], p["Height"] = _int(size[1]), _int(size[2])
        if ct.has_text and not ct.nonvisual:
            t = v(name, "Text")
            p["Text"] = t if isinstance(t, str) else ""
        if "FontName" in p and font:
            p["FontName"], p["FontSize"] = font[0], _int(font[1])
            p["FontBold"], p["FontItalic"] = bool(font[2]), bool(font[3])
        for key in ("BackColor", "ForeColor"):
            if key in p:
                p[key] = _color_hex(v(name, key))
        if "Anchor" in p:
            a = v(name, "Anchor")
            if isinstance(a, tuple) and a[0] == "enum":
                edges = {x.split(".")[-1] for x in a[1].split("|")}
                p["Anchor"] = format_anchor(edges) if edges - {"None"} else "None"
            else:
                p["Anchor"] = "Top, Left"
        if "Dock" in p:
            dk = _enum_last(v(name, "Dock"))
            p["Dock"] = dk if dk in ("Top", "Bottom", "Left", "Right", "Fill") else "None"
            if nt == "StatusBar" and dk == "":
                p["Dock"] = "Bottom"
        for key in ("Enabled", "Visible", "ReadOnly", "Multiline", "Checked"):
            if key in p:
                x = v(name, key)
                p[key] = x if isinstance(x, bool) else (False if key in ("ReadOnly", "Multiline", "Checked")
                                                        or nt == "Timer" and key == "Enabled" else True)
        if nt == "TextBox" and sw == "RichTextBox":
            p["Multiline"] = True if v(name, "Multiline") is not False else False
        if "Checked" in p and v(name, "CheckState") is not None:
            p["Checked"] = _enum_last(v(name, "CheckState")) in ("Checked", "Indeterminate")
        if "TabIndex" in p:
            x = v(name, "TabIndex")
            p["TabIndex"] = x if isinstance(x, int) else 0
        if nt == "TextBox":
            pc = v(name, "PasswordChar")
            p["PasswordChar"] = pc[:1] if isinstance(pc, str) and pc.strip("\0") else ""
            if v(name, "UseSystemPasswordChar") is True and not p["PasswordChar"]:
                p["PasswordChar"] = "*"
            ml = v(name, "MaxLength")
            p["MaxLength"] = ml if isinstance(ml, int) and ml != 32767 else 0
        if "TextAlign" in p:
            al = _enum_last(v(name, "TextAlign"))
            if not al:
                p["TextAlign"] = "Center" if nt == "Button" else "Left"
            else:
                p["TextAlign"] = "Center" if "Center" in al else "Right" if "Right" in al else "Left"
        for key, dflt in (("Minimum", 0), ("Maximum", 100), ("Value", 0)):
            if key in p and nt != "DateTimePicker":
                x = v(name, key)
                p[key] = _int(x) if isinstance(x, (int, float)) else dflt
        if nt == "Timer":
            x = v(name, "Interval")
            p["Interval"] = x if isinstance(x, int) else 100
        if nt in ("ListBox", "ComboBox"):
            idx = doc.list_items.get(name)
            vals = [x for x in doc.stmts[idx].args] if idx is not None else []
            p["Items"] = ";".join(str(x).replace(";", ",") for x in vals if isinstance(x, (str, int, float)))
        if nt == "ComboBox":
            p["DropDownStyle"] = {"DropDownList": "DropDownList"}.get(_enum_last(v(name, "DropDownStyle")),
                                                                      "DropDown")
        if nt == "PictureBox":
            img = v(name, "Image")
            p["Image"] = self.res_file(img[1]) if isinstance(img, tuple) and img[0] == "res" else ""
        if nt in ("ListView", "DataGridView"):
            p["Columns"] = ""
        if nt == "ListView":
            p["View"] = "Details" if _enum_last(v(name, "View")) == "Details" else "List"
        if nt == "TabControl":
            pages = doc_tab_pages(doc, name)
            p["TabPages"] = ";".join(self._page_text(tp) for tp in pages)
            x = v(name, "SelectedIndex")
            p["SelectedIndex"] = x if isinstance(x, int) else 0
        if nt == "DateTimePicker":
            fmt = _enum_last(v(name, "Format"))
            p["Format"] = fmt if fmt in ("Short", "Time") else "Long"
        if nt == "LinkLabel" and _color_hex(v(name, "LinkColor")):
            p["LinkColor"] = _color_hex(v(name, "LinkColor"))
        if nt in ("OpenFileDialog", "SaveFileDialog"):
            for key, dflt in (("Filter", ""), ("Title", ""), ("FileName", ""), ("InitialDirectory", "")):
                x = v(name, key)
                p[key] = x if isinstance(x, str) else dflt
        if nt in ("MenuStrip", "ToolStrip"):
            p["Items"] = self.menu_tree(name)
        if nt == "StatusBar":
            labels = [k for k in doc.item_children.get(name, []) if k in doc.items]
            txt = next((v(k, "Text") for k in labels if isinstance(v(k, "Text"), str)), None)
            p["Text"] = txt if isinstance(txt, str) else ""
        if "ToolTip" in p:
            p["ToolTip"] = doc.tooltips.get(name, ("", -1, ""))[0]
        return Control(nt, p)

    def _page_text(self, tp: str) -> str:
        t = self.val(tp, "Text")
        return (t if isinstance(t, str) else tp).replace(";", ",")

    def menu_tree(self, owner: str, depth: int = 0) -> list:
        out = []
        for k in self.doc.item_children.get(owner, []):
            it = self.doc.items.get(k)
            if it is None or depth > 10:
                continue
            if short(it["wtype"]) == "ToolStripSeparator":
                out.append({"Text": "-", "Name": k})
                continue
            t = self.val(k, "Text")
            item = {"Text": t if isinstance(t, str) else "", "Name": k}
            kids = self.menu_tree(k, depth + 1)
            if kids:
                item["Items"] = kids
            out.append(item)
        return out


def doc_tab_pages(doc: DesignerDoc, tabcontrol: str) -> list[str]:
    return [n for n, tp in doc.tabpages.items() if tp.get("parent") == tabcontrol]


def _resx_value(e):
    """Value of a typed resx entry as a designer literal (Point / Size / string / int / bool)."""
    t, s = e.type, e.value or ""
    if not t:
        return s
    nums = [x.strip() for x in s.split(",")]
    try:
        if t.startswith("System.Drawing.Point"):
            return ("Point", int(nums[0]), int(nums[1]))
        if t.startswith("System.Drawing.Size"):
            return ("Size", int(nums[0]), int(nums[1]))
        if t.startswith("System.Int32"):
            return int(s)
        if t.startswith("System.Boolean"):
            return s.strip().lower() == "true"
    except (ValueError, IndexError):
        return None
    return None


# ============================================================================ neutral form -> designer text
class Renderer:
    """Patches the baseline Designer text so that it describes *form*."""

    def __init__(self, doc: DesignerDoc, form: Form, resx: ResxFile | None, code_text: str = ""):
        self.base_doc = doc
        self.form = form
        self.resx = resx
        self.code = code_text
        self.report: list[str] = []
        self.needs_resx = False

    # ---------------------------------------------------------------- top level
    def render(self) -> str:
        doc = self.base_doc
        d = doc.d
        # 1. renames (identifiers in InitializeComponent + fields), then re-parse as the new baseline
        renames = self._renames(doc)
        self.renamed = dict(renames)
        if renames:
            text = _apply_renames(doc, renames)
            if self.resx is not None:
                for old, new in renames.items():
                    for nm in list(self.resx.names()):
                        if nm.startswith(old + "."):
                            e = self.resx.entry(nm)
                            if e is not None and e.is_bytes:
                                self.resx.set_bytes(new + nm[len(old):], self.resx.get_bytes(nm) or b"", e.type)
                                self.resx.remove(nm)
                            elif e is not None and e.is_string and e.value is not None:
                                self.resx.set_string(new + nm[len(old):], e.value)
                                self.resx.remove(nm)
            doc = DesignerDoc(doc.path, text, d)
            ev = self.form.extra.get("winforms", {}).get("new_events") or {}
            for k in list(ev):
                o, _, e = k.rpartition(".")
                if o in renames:
                    ev[f"{renames[o]}.{e}"] = ev.pop(k)
        self.doc = doc
        d.style = doc.style
        self.nl = "\r\n" if "\r\n" in doc.text else "\n"
        d.nl = self.nl
        self.ind = self._indent()
        self.edits: list[tuple[int, int, str]] = []        # (start, end, replacement) on doc.text
        self.inserts: dict[int, list[str]] = {}            # position -> texts (in order)
        self.removed: set[int] = set()                     # stmt indexes removed / replaced
        base = Loader(doc, self.resx, extract=False).build()
        self.base_form = base
        self.offset = menu_offset(doc)
        cur = self.form
        bmap = {c.name: c for c in base.controls}
        cmap = {c.name: c for c in cur.controls}
        # pseudo panels of SplitContainers are not in the file (their geometry follows SplitterDistance)
        for c in list(cur.controls):
            if c.props.get("_wfp"):
                b = bmap.get(c.name)
                if b is not None and any(b.props.get(k) != c.props.get(k) for k in ("Left", "Top", "Width",
                                                                                      "Height")):
                    self.report.append(f"{c.name}: panel geometry follows SplitterDistance - not written")
        bmap = {n: c for n, c in bmap.items() if not c.props.get("_wfp")}
        cmap = {n: c for n, c in cmap.items() if not c.props.get("_wfp")}
        # 2. deleted controls
        self.deleted = [n for n in bmap if n not in cmap]
        for name in self.deleted:
            self._delete_control(name)
        # 3. form props
        self._form_props(base.props, cur.props)
        # 4. changed controls / reparenting
        new_names = []
        for c in cur.controls:
            if c.props.get("_wfp"):
                continue
            if c.name in bmap:
                self._update_control(bmap[c.name], c)
            elif c.type in NEUTRAL_TO_WF or (c.props.get("_wft") and c.type == "Panel"):
                new_names.append(c)
            else:
                self.report.append(f"{c.name}: {c.type} has no WinForms equivalent - not written")
        # 5. new controls
        if new_names:
            self._add_controls(new_names)
        # 6. new event wiring (C#: += in InitializeComponent; VB: Handles clauses in the code file)
        self._events()
        return self._apply()

    # ---------------------------------------------------------------- helpers
    def _indent(self) -> str:
        for st in self.doc.stmts:
            if st.indent:
                return st.indent
        for ln in self.doc.text[self.doc.ic0:].split("\n"):
            if ln.strip():
                return re.match(r"[ \t]*", ln).group(0) + "    "
        return "        "

    def me(self) -> str:
        return self.doc.style.me

    def T(self, typ: str, ns: str = FORMS_NS) -> str:
        if typ == "Timer":
            return f"{FORMS_NS}.Timer"
        return f"{ns}.{typ}" if self.doc.style.qualified else typ

    def ref(self, name: str) -> str:
        return f"{self.me()}{name}" if name else (self.me().rstrip(".") or ("Me" if self.doc.d.lang == "vb" else "this"))

    def target(self, owner: str, prop: str) -> str:
        if owner == "":
            return f"{self.me()}{prop}"
        return f"{self.ref(owner)}.{prop}"

    def line(self, code: str, ind: str | None = None) -> str:
        return f"{self.ind if ind is None else ind}{code}{self.nl}"

    def _remove(self, idx: int) -> None:
        if idx in self.removed or idx < 0:
            return
        st = self.doc.stmts[idx]
        self.removed.add(idx)
        self.edits.append((st.start, st.end, ""))

    def _replace(self, idx: int, code: str) -> None:
        st = self.doc.stmts[idx]
        if idx in self.removed:
            return
        self.removed.add(idx)
        if st.start < st.s0 and st.end > st.s1:          # whole line(s): keep the indentation
            self.edits.append((st.start, st.end, f"{st.indent}{code}{self.nl}"))
        else:
            self.edits.append((st.s0, st.s1, code))

    def _replace_value(self, idx: int, value: str) -> None:
        st = self.doc.stmts[idx]
        lhs = _lhs(st.text, self.doc.d.lang)
        if lhs is None:
            return
        new = self.doc.d.assign(lhs, value)
        if _norm(new) != _norm(st.text):
            self._replace(idx, new)

    def insert(self, pos: int, text: str) -> None:
        self.inserts.setdefault(pos, []).append(text)

    def _apply(self) -> str:
        text = self.doc.text
        ops = [(a, b, r, 1) for a, b, r in self.edits]
        for pos, texts in self.inserts.items():
            ops.append((pos, pos, "".join(str(t) for t in texts), 0))
        # apply from the end; at the same position the replacement (which extends to the right) goes
        # first, so the insertion lands in front of the replaced text
        ops.sort(key=lambda o: (o[0], o[3]), reverse=True)
        seen_spans = set()
        for a, b, r, _k in ops:
            if (a, b) in seen_spans and a != b:
                continue
            seen_spans.add((a, b))
            text = text[:a] + r + text[b:]
        return text

    # ---------------------------------------------------------------- positions
    def after_stmt(self, idx: int) -> int:
        return self.doc.stmts[idx].end

    def owner_block_end(self, owner: str) -> int | None:
        """Position after the last property / event statement of *owner*."""
        last = None
        for i, st in enumerate(self.doc.stmts):
            if st.owner == owner and st.kind in ("prop", "event", "items", "listitems", "applyres") \
                    and i not in self.removed:
                last = i
        if last is None:
            return None
        return self.doc.stmts[last].end

    def form_block_start(self) -> int:
        """Where a new control's property block goes: before the form's own block."""
        stmts = self.doc.stmts
        first = None
        for i, st in enumerate(stmts):
            if st.owner == "" and st.kind in ("prop", "add", "event"):
                first = i
                break
        if first is None:
            return self.end_pos()
        # include the "// \n // Form1 \n // " header above it
        j = first
        while j > 0 and stmts[j - 1].kind == "comment" and stmts[j - 1].end == stmts[j].start:
            j -= 1
        return stmts[j].start

    def end_pos(self) -> int:
        """Before ResumeLayout / PerformLayout at the end, else at the end of the method body."""
        stmts = self.doc.stmts
        for i, st in enumerate(stmts):
            if st.kind == "call" and st.method in ("ResumeLayout", "PerformLayout") and st.owner is None and \
                    all(s.kind in ("call", "comment", "directive") for s in stmts[i:]):
                return st.start
        return self.method_end()

    def method_end(self) -> int:
        d = self.doc
        if d.stmts:
            return d.stmts[-1].end
        if d.d.lang == "vb":
            return d.ic0
        # empty method: right after the opening line
        k = d.text.find("\n", d.ic0)
        return k + 1 if 0 <= k < d.ic1 else d.ic0

    def news_end(self) -> int:
        last = None
        for i, st in enumerate(self.doc.stmts):
            if st.kind == "new" or st.kind == "decl" or (st.kind == "call" and st.method in ("BeginInit",
                                                                                              "SuspendLayout")):
                if i not in self.removed:
                    last = i
            elif st.kind in ("prop", "add", "event"):
                break
        if last is None:
            first = next((i for i, st in enumerate(self.doc.stmts) if st.kind not in ("comment", "directive")),
                         None)
            return self.doc.stmts[first].start if first is not None else self.method_end()
        return self.doc.stmts[last].end

    def new_stmts_end(self) -> int:
        """After the last `x = new T()` of a control (VS puts all instantiations first)."""
        last = None
        for i, st in enumerate(self.doc.stmts):
            if st.kind in ("new", "decl") and i not in self.removed:
                last = i
        if last is None:
            return self.news_end()
        return self.doc.stmts[last].end

    # ---------------------------------------------------------------- renames
    def _renames(self, doc: DesignerDoc) -> dict[str, str]:
        base = Loader(doc, self.resx, extract=False).build()
        bnames = {c.name: c for c in base.controls if not c.props.get("_wfp")}
        cur = [c for c in self.form.controls if not c.props.get("_wfp")]
        cnames = {c.name for c in cur}
        removed = [n for n in bnames if n not in cnames]
        added = [c for c in cur if c.name not in bnames]
        out = {}
        for c in added:
            wf = c.props.get("_wf")
            if wf in removed and wf not in out:
                out[wf] = c.name
                removed.remove(wf)
        for c in added:
            if c.name in out.values():
                continue
            for r in removed:
                b = bnames[r]
                if b.type == c.type and all(b.props.get(k) == c.props.get(k)
                                            for k in ("Left", "Top", "Width", "Height", "Parent", "_wft")):
                    out[r] = c.name
                    removed.remove(r)
                    break
        return {o: n for o, n in out.items() if o != n and re.match(r"^[A-Za-z_]\w*$", n)}

    # ---------------------------------------------------------------- delete
    def _delete_control(self, name: str) -> None:
        doc = self.doc
        names = {name}
        c = doc.controls.get(name)
        if c is not None:
            # its items (menus) and tab pages go with it
            stack = [name]
            while stack:
                k = stack.pop()
                for it in doc.item_children.get(k, []):
                    if it not in names:
                        names.add(it)
                        stack.append(it)
            for tp in doc_tab_pages(doc, name):
                names.add(tp)
        self._delete_names(names)
        # its children are deleted by the designer too (they are absent from the form)

    def _delete_names(self, names: set[str]) -> None:
        doc = self.doc
        for i, st in enumerate(doc.stmts):
            if st.kind in ("comment", "directive") or not (st.refs & names):
                continue
            if st.kind in ("add", "items") and len(st.args) > 1 and not set(st.args) <= names:
                self._rewrite_list(i, [a for a in st.args if a not in names])
                continue
            self._remove(i)
            # the "// \n // name \n // " header of its block
            if st.kind == "prop" and st.owner in names:
                j = i
                hdr = []
                while j > 0 and doc.stmts[j - 1].kind == "comment" and len(hdr) < 3:
                    hdr.append(j - 1)
                    j -= 1
                if len(hdr) == 3 and doc.stmts[hdr[1]].text.strip(" /'") == st.owner:
                    for h in hdr:
                        self._remove(h)
        for n in names:
            f = doc.fields.get(n)
            if f is not None:
                self.edits.append((f[1], f[2], ""))
        if self.resx is not None:
            for n in names:
                for key in list(self.resx.names()):
                    if key.startswith(n + "."):
                        self.resx.remove(key)

    def _rewrite_list(self, idx: int, kids: list[str]) -> None:
        st = self.doc.stmts[idx]
        if st.kind == "add":
            parent = st.wtype
            recv = (f"{self.me()}{parent}." if parent else self.me()) + "Controls"
            if len(kids) == 1:
                self._replace(idx, self.doc.d.call(f"{recv}.Add", self.ref(kids[0])))
            else:
                arr = self.doc.d.new_array(self.T("Control"), [self.ref(k) for k in kids], st.indent)
                self._replace(idx, self.doc.d.call(f"{recv}.AddRange", arr))
        else:
            self._set_item_list(st.owner, kids, idx)

    # ---------------------------------------------------------------- property values
    def v_point(self, x, y) -> str:
        return self.doc.d.new(self.T("Point", DRAWING_NS), f"{int(x)}, {int(y)}")

    def v_size(self, w, h) -> str:
        return self.doc.d.new(self.T("Size", DRAWING_NS), f"{int(w)}, {int(h)}")

    def v_color(self, hexv: str) -> str:
        h = hexv.upper()
        name = _HEX_TO_NAME.get(h)
        if name and name in _PROPER:
            return f"{self.T('Color', DRAWING_NS)}.{_PROPER[name]}"
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        return f"{self.T('Color', DRAWING_NS)}.FromArgb({r}, {g}, {b})"

    def v_decimal(self, v: int) -> str:
        lo = int(v) & 0xFFFFFFFF
        lo = lo - (1 << 32) if lo >= 1 << 31 else lo
        neg = "-2147483648" if v < 0 else "0"
        if self.doc.d.lang == "vb":
            return f"New Decimal(New Integer() {{{abs(lo) if v >= 0 else -v}, 0, 0, {neg}}})"
        return f"new decimal(new int[] {{ {abs(lo) if v >= 0 else -v}, 0, 0, {neg} }})"

    def v_enum(self, typ: str, member: str, ns: str = FORMS_NS) -> str:
        return f"{self.T(typ, ns)}.{member}"

    def v_anchor(self, value: str) -> str:
        edges = [e.strip() for e in str(value).split(",") if e.strip() and e.strip() != "None"]
        if not edges:
            return self.v_enum("AnchorStyles", "None")
        order = [e for e in ("Top", "Bottom", "Left", "Right") if e in edges]
        return self.doc.d.enum_or([self.v_enum("AnchorStyles", e) for e in order], self.T("AnchorStyles"))

    def v_font(self, name: str, size: float, bold: bool, italic: bool) -> str:
        d = self.doc.d
        args = f"{d.lit_str(name)}, {d.lit_float(size)}"
        styles = [s for s, on in (("Bold", bold), ("Italic", italic)) if on]
        if styles:
            parts = [self.v_enum("FontStyle", s, DRAWING_NS) for s in styles]
            args += ", " + d.enum_or(parts, self.T("FontStyle", DRAWING_NS))
        return d.new(self.T("Font", DRAWING_NS), args)

    def set_prop(self, owner: str, prop: str, value: str | None, anchor_pos: int | None = None) -> None:
        """Set (value code) or remove (None) the statement `owner.prop = ...`."""
        doc = self.doc
        idx = doc._props_of(owner).get(prop)
        if idx is not None and idx in self.removed:
            idx = None
        if value is None:
            if idx is not None:
                self._remove(idx)
            return
        if idx is not None:
            self._replace_value(idx, value)
            return
        code = doc.d.assign(self.target(owner, prop), value)
        pos = anchor_pos if anchor_pos is not None else self.owner_block_end(owner)
        if pos is None:
            pos = self.form_block_start() if owner else self.end_pos()
        ind = self.ind
        self.insert(pos, self.line(code, ind))

    def set_resource(self, owner: str, prop: str, path: str, typ: str) -> None:
        """Image / Icon from a file into the .resx (+ the GetObject statement)."""
        key = f"{owner}.{prop}" if owner else f"$this.{prop}"
        if not path:
            self.set_prop(owner, prop, None)
            if self.resx is not None:
                self.resx.remove(key)
            return
        try:
            data = Path(path).read_bytes()
        except OSError:
            self.report.append(f"{owner or 'form'}.{prop}: cannot read {path}")
            return
        self.needs_resx = True
        if self.resx is None:
            self.resx = ResxFile.new(self.doc.path.with_name(self.doc.path.name.split(".")[0] + ".resx"))
        self.resx.set_bytes(key, data, ICON if prop == "Icon" else image_type_for(data))
        self._ensure_resources()
        cur = self.doc.value(owner, prop)
        if isinstance(cur, tuple) and cur[0] == "res" and cur[1] == key:
            return
        self.set_prop(owner, prop, self.doc.d.get_object(key, self.T("Icon" if prop == "Icon" else "Image",
                                                                         DRAWING_NS)))

    def _ensure_resources(self) -> None:
        if self.doc.resources_idx >= 0 or getattr(self, "_res_added", False):
            return
        self._res_added = True
        d = self.doc
        first = next((i for i, st in enumerate(d.stmts) if st.kind not in ("comment", "directive")), None)
        pos = d.stmts[first].start if first is not None else self.method_end()
        self.insert(pos, self.line(d.d.resources_decl(d.cls_name)))

    # ---------------------------------------------------------------- form
    def _form_props(self, b: dict, c: dict) -> None:
        d = self.doc.d
        off_changed = self.offset != self.form.extra.get("winforms", {}).get("offset", self.offset)
        if b.get("Text") != c.get("Text"):
            self.set_prop("", "Text", d.lit_str(str(c.get("Text", ""))))
        if (b.get("Width"), b.get("Height")) != (c.get("Width"), c.get("Height")) or off_changed:
            w, h = int(c["Width"]), int(c["Height"]) + self._new_offset()
            if "ClientSize" in self.doc.form_props or "Size" not in self.doc.form_props:
                self.set_prop("", "ClientSize", self.v_size(w, h))
            else:
                self.set_prop("", "Size", self.v_size(w + 16, h + 39))
        if b.get("BackColor") != c.get("BackColor"):
            self.set_prop("", "BackColor", self.v_color(c["BackColor"]) if c.get("BackColor") else None)
        if b.get("StartPosition") != c.get("StartPosition"):
            self.set_prop("", "StartPosition",
                          self.v_enum("FormStartPosition", c["StartPosition"]) if c["StartPosition"] != "Manual"
                          else self.v_enum("FormStartPosition", "Manual"))
        if b.get("FormBorderStyle") != c.get("FormBorderStyle"):
            self.set_prop("", "FormBorderStyle", None if c["FormBorderStyle"] == "Sizable"
                          else self.v_enum("FormBorderStyle", "FixedSingle"))
        if b.get("TopMost") != c.get("TopMost"):
            self.set_prop("", "TopMost", d.lit_bool(True) if c.get("TopMost") else None)
        if b.get("WindowState") != c.get("WindowState"):
            self.set_prop("", "WindowState", None if c.get("WindowState") != "Maximized"
                          else self.v_enum("FormWindowState", "Maximized"))
        if b.get("Icon") != c.get("Icon"):
            self.set_resource("", "Icon", c.get("Icon") or "", ICON)
        for k in ("Name",):
            if b.get(k) != c.get(k):
                self.report.append("Renaming the form class is not supported by the WinForms writer - "
                                   "rename it in the code (the Name was kept)")

    def _new_offset(self) -> int:
        """Menu/tool strip height of the CURRENT form (a menu added in the designer counts)."""
        off = 0
        cur = self.form
        for c in cur.controls:
            if c.type in ("MenuStrip", "ToolStrip") and not c.props.get("Parent"):
                if c.name in self.doc.controls:
                    size = self.doc.value(c.name, "Size")
                    if _enum_last(self.doc.value(c.name, "Dock")) not in ("", "Top"):
                        continue
                    off += _int(size[2]) if isinstance(size, tuple) and len(size) >= 3 else \
                        (24 if c.type == "MenuStrip" else 25)
                else:
                    off += 24 if c.type == "MenuStrip" else 25
        return off

    # ---------------------------------------------------------------- control update
    def _update_control(self, b: Control, c: Control) -> None:
        name = c.name
        doc = self.doc
        wt = short(doc.controls[name]["wtype"])
        bp, cp = b.props, c.props
        d = doc.d
        nt = c.type
        ct = CONTROL_TYPES[nt]
        changed = {k for k in set(bp) | set(cp) if k not in HIDDEN and bp.get(k) != cp.get(k)}
        new_off = self._new_offset()
        if new_off != self.offset and not cp.get("Parent") and not ct.nonvisual:
            changed |= {"Top"}
        if not changed:
            return
        dock = cp.get("Dock", "None")
        par = cp.get("Parent") or ""
        if par and doc.is_split(par) and ({"Left", "Top"} & changed) and                 self._net_parent(c) != doc.parent_expr.get(name):
            changed |= {"Parent"}          # moved to the other panel of a SplitContainer
        if {"Parent", "TabPage"} & changed:
            self._reparent(name, b, c)
            changed |= {"Left", "Top"}
        if not ct.nonvisual and ({"Left", "Top"} & changed) and dock == "None":
            self.set_prop(name, "Location", self.v_point(*self._native_xy(c)))
        if not ct.nonvisual and ({"Width", "Height"} & changed) and dock != "Fill":
            w, h = int(cp["Width"]), int(cp["Height"])
            old = doc.value(name, "Size")
            if dock in ("Top", "Bottom") and isinstance(old, tuple):
                w = _int(old[1])
            if dock in ("Left", "Right") and isinstance(old, tuple):
                h = _int(old[2])
            self.set_prop(name, "Size", self.v_size(w, h))
        if "Text" in changed and ct.has_text and nt != "StatusBar":
            self._set_text(name, str(cp.get("Text", "")))
        if {"FontName", "FontSize", "FontBold", "FontItalic"} & changed:
            old = _font_of(doc.value(name, "Font"))
            size = float(cp["FontSize"])
            if old and int(round(old[1])) == int(cp["FontSize"]):
                size = old[1]                 # keep 9.75F when only the style changed
            self.set_prop(name, "Font", self.v_font(cp["FontName"], size, cp["FontBold"], cp["FontItalic"]))
        for key in ("BackColor", "ForeColor"):
            if key in changed:
                self.set_prop(name, key, self.v_color(cp[key]) if cp.get(key) else None)
        if "Anchor" in changed:
            a = cp.get("Anchor") or "Top, Left"
            self.set_prop(name, "Anchor", None if a.replace(" ", "") in ("Top,Left", "Left,Top")
                          else self.v_anchor(a))
        if "Dock" in changed:
            self.set_prop(name, "Dock", None if dock == "None" else self.v_enum("DockStyle", dock))
        for key in ("Enabled", "Visible"):
            if key in changed:
                dflt = nt != "Timer" if key == "Enabled" else True
                self.set_prop(name, key, None if cp[key] == dflt else d.lit_bool(cp[key]))
        for key in ("ReadOnly", "Multiline"):
            if key in changed:
                dflt = wt == "RichTextBox" and key == "Multiline"
                self.set_prop(name, key, None if bool(cp[key]) == dflt else d.lit_bool(bool(cp[key])))
        if "Checked" in changed:
            if "CheckState" in doc.controls[name]["props"]:
                self.set_prop(name, "CheckState", self.v_enum("CheckState", "Checked" if cp["Checked"] else
                                                              "Unchecked"))
            self.set_prop(name, "Checked", d.lit_bool(True) if cp["Checked"] else None)
        if "TabIndex" in changed:
            self.set_prop(name, "TabIndex", str(int(cp["TabIndex"])))
        if "PasswordChar" in changed:
            self.set_prop(name, "UseSystemPasswordChar", None)
            self.set_prop(name, "PasswordChar", d.lit_char(cp["PasswordChar"]) if cp["PasswordChar"] else None)
        if "MaxLength" in changed:
            self.set_prop(name, "MaxLength", str(int(cp["MaxLength"])) if int(cp["MaxLength"] or 0) > 0 else None)
        if "TextAlign" in changed:
            self.set_prop(name, "TextAlign", self._align(nt, wt, cp["TextAlign"]))
        for key, dflt in (("Minimum", 0), ("Maximum", 100), ("Value", 0)):
            if key in changed and nt in ("ProgressBar", "NumericUpDown", "TrackBar"):
                v = int(cp[key])
                if nt == "NumericUpDown" and v != dflt:
                    self.set_prop(name, key, self.v_decimal(v))
                else:
                    self.set_prop(name, key, None if v == dflt else str(v))
        if "Interval" in changed:
            self.set_prop(name, "Interval", None if int(cp["Interval"]) == 100 else str(int(cp["Interval"])))
        if "Items" in changed and nt in ("ListBox", "ComboBox"):
            self._set_list_items(name, split_items(cp.get("Items", "")))
        if "Items" in changed and nt in ("MenuStrip", "ToolStrip"):
            self._menu_diff(name, bp.get("Items") or [], cp.get("Items") or [], nt)
        if "Text" in changed and nt == "StatusBar":
            self._status_text(name, str(cp.get("Text", "")))
        if "DropDownStyle" in changed:
            self.set_prop(name, "DropDownStyle", None if cp["DropDownStyle"] == "DropDown"
                          else self.v_enum("ComboBoxStyle", cp["DropDownStyle"]))
        if "Image" in changed and nt == "PictureBox":
            self.set_resource(name, "Image", cp.get("Image") or "", "")
        if "ToolTip" in changed:
            self._tooltip(name, cp.get("ToolTip") or "")
        if "TabPages" in changed and nt == "TabControl":
            self._tab_pages(name, split_items(cp.get("TabPages", "")))
        if "SelectedIndex" in changed and nt == "TabControl":
            self.set_prop(name, "SelectedIndex", None if not cp["SelectedIndex"] else str(int(cp["SelectedIndex"])))
        if "Format" in changed and nt == "DateTimePicker":
            self.set_prop(name, "Format", None if cp["Format"] == "Long"
                          else self.v_enum("DateTimePickerFormat", cp["Format"]))
        if "View" in changed and nt == "ListView":
            self.set_prop(name, "View", self.v_enum("View", cp["View"]))
        if "LinkColor" in changed and nt == "LinkLabel":
            self.set_prop(name, "LinkColor", self.v_color(cp["LinkColor"]) if cp.get("LinkColor") else None)
        for key in ("Filter", "Title", "FileName", "InitialDirectory"):
            if key in changed and nt in ("OpenFileDialog", "SaveFileDialog"):
                self.set_prop(name, key, d.lit_str(cp[key]) if cp[key] else None)
        handled = {"Left", "Top", "Width", "Height", "Text", "FontName", "FontSize", "FontBold", "FontItalic",
                   "BackColor", "ForeColor", "Anchor", "Dock", "Enabled", "Visible", "ReadOnly", "Multiline",
                   "Checked", "TabIndex", "PasswordChar", "MaxLength", "TextAlign", "Minimum", "Maximum", "Value",
                   "Interval", "Items", "DropDownStyle", "Image", "ToolTip", "TabPages", "SelectedIndex", "Format",
                   "View", "LinkColor", "Filter", "Title", "FileName", "InitialDirectory", "Parent", "TabPage",
                   "Name"}
        for k in sorted(changed - handled):
            self.report.append(f"{name}.{k}: no WinForms mapping - change not written")

    def _set_text(self, owner: str, text: str) -> None:
        cur = self.doc.value(owner, "Text")
        if isinstance(cur, tuple) and cur[0] == "resstr" and self.resx is not None:
            self.resx.set_string(cur[1], text)
            return
        if owner in self.doc.apply_res and "Text" not in self.doc._props_of(owner) and self.resx is not None:
            self.resx.set_string(f"{self.doc.apply_res[owner]}.Text", text)
            return
        self.set_prop(owner, "Text", self.doc.d.lit_str(text))

    def _align(self, nt: str, wt: str, al: str) -> str | None:
        if nt == "TextBox" or wt in ("TextBox", "MaskedTextBox", "NumericUpDown"):
            return None if al == "Left" else self.v_enum("HorizontalAlignment", al)
        member = {"Left": "MiddleLeft", "Center": "MiddleCenter", "Right": "MiddleRight"}[al]
        if nt == "Label" and al == "Left":
            return None
        if nt == "Button" and al == "Center":
            return None
        if nt == "Label":
            member = {"Center": "TopCenter", "Right": "TopRight"}.get(al, member)
        return self.v_enum("ContentAlignment", member, DRAWING_NS)

    def _set_list_items(self, owner: str, items: list[str]) -> None:
        d = self.doc.d
        idx = self.doc.list_items.get(owner)
        recv = f"{self.ref(owner)}.Items.AddRange"
        if not items:
            if idx is not None:
                self._remove(idx)
            return
        ind = self.doc.stmts[idx].indent if idx is not None else self.ind
        arr = d.new_array("object" if d.lang == "cs" else "Object", [d.lit_str(x) for x in items], ind)
        code = d.call(recv, arr)
        if idx is not None:
            self._replace(idx, code)
        else:
            pos = self.owner_block_end(owner) or self.form_block_start()
            # VS: Items.AddRange right after FormattingEnabled / before Location
            loc = self.doc._props_of(owner).get("Location")
            if loc is not None:
                pos = self.doc.stmts[loc].start
            self.insert(pos, self.line(code))

    def _tooltip(self, owner: str, text: str) -> None:
        d = self.doc.d
        cur = self.doc.tooltips.get(owner)
        if cur is not None:
            if text:
                self._replace(cur[1], d.call(f"{self.ref(cur[2])}.SetToolTip", f"{self.ref(owner)}, "
                                                                                   f"{d.lit_str(text)}"))
            else:
                self._remove(cur[1])
            return
        if not text:
            return
        tips = [n for n, c in self.doc.controls.items() if short(c["wtype"]) == "ToolTip"]
        if not tips:
            # create toolTip1 (a component of this.components)
            tips = ["toolTip1" if d.lang == "cs" else "ToolTip1"]
            self._new_component(tips[0], "ToolTip")
            self.doc.controls.setdefault(tips[0], {"wtype": "ToolTip", "new": -1, "props": {}})
        pos = self.owner_block_end(owner) or self.form_block_start()
        self.insert(pos, self.line(d.call(f"{self.ref(tips[0])}.SetToolTip", f"{self.ref(owner)}, "
                                                                              f"{d.lit_str(text)}")))

    def _new_component(self, name: str, typ: str) -> None:
        d = self.doc.d
        self._ensure_components()
        self.insert(self.new_stmts_end(), self.line(d.assign(self.ref(name),
                                                             d.new(self.T(typ), self.ref("components")))))
        self._add_field(name, self.T(typ))

    def _ensure_components(self) -> None:
        if self.doc.components_idx >= 0 or getattr(self, "_comp_added", False):
            return
        self._comp_added = True
        first = next((i for i, st in enumerate(self.doc.stmts) if st.kind not in ("comment", "directive")), None)
        pos = self.doc.stmts[first].start if first is not None else self.method_end()
        if self.doc.resources_idx >= 0:
            pos = self.doc.stmts[self.doc.resources_idx].end
        self.insert(pos, self.line(self.doc.d.components_new()))

    # ---------------------------------------------------------------- reparent
    def _reparent(self, name: str, b: Control, c: Control) -> None:
        doc = self.doc
        # remove from the old parent's Controls.Add
        for i, st in enumerate(doc.stmts):
            if st.kind == "add" and name in st.args and st.wtype != "TabPages":
                if len(st.args) > 1:
                    self._rewrite_list(i, [a for a in st.args if a != name])
                else:
                    self._remove(i)
        self._add_to_parent(name, self._net_parent(c))

    def _native_xy(self, c: Control) -> tuple[int, int]:
        """Location of a control in .NET coordinates (relative to its real parent)."""
        p = c.props
        x, y = int(p.get("Left", 0)), int(p.get("Top", 0))
        if not p.get("Parent"):
            return x, y + self._new_offset()
        np = self._net_parent(c)
        if self.doc.is_split(p["Parent"]) and np.endswith(".Panel2"):
            ox, oy = self.doc.split_offset(np.split(".")[0])
            return x - ox, y - oy
        return x, y

    def _net_parent(self, c: Control) -> str:
        par = c.props.get("Parent") or ""
        if not par:
            return ""
        pc = self.form.find(par)
        if pc is not None and pc.props.get("_wfp"):          # pseudo panel: split1.Panel2
            return f"{pc.props.get('Parent') or pc.props['_wfp']}.{par.rsplit('.', 1)[-1]}"
        if self.doc.is_split(par):
            # SplitContainer: children live on Panel1 / Panel2 (Controls.Add on the container throws)
            ox, oy = self.doc.split_offset(par)
            x, y = int(c.props.get("Left", 0)), int(c.props.get("Top", 0))
            return f"{par}.Panel2" if (ox and x >= ox) or (oy and y >= oy) else f"{par}.Panel1"
        pc = self.form.find(par)
        if pc is not None and pc.type == "TabControl":
            pages = doc_tab_pages(self.doc, par) + getattr(self, "_new_pages", {}).get(par, [])
            i = int(c.props.get("TabPage", 0) or 0)
            if pages:
                return pages[min(i, len(pages) - 1)]
        return par

    def _add_to_parent(self, name: str, parent: str, front: bool = True) -> None:
        d = self.doc.d
        recv = (f"{self.ref(parent)}." if parent else self.me()) + "Controls.Add"
        code = self.line(d.call(recv, self.ref(name)))
        base = parent.split(".")[0]
        adds = [i for i in self.doc.adds.get(base, []) if self.doc.stmts[i].wtype != "TabPages"
                and ("." not in parent or self.doc.stmts[i].wtype == parent)]
        parent = base if "." in parent and not adds else parent
        if adds:
            pos = self.doc.stmts[adds[-1]].end
        elif parent == "":
            cs = self.doc.form_props.get("ClientSize")
            pos = self.doc.stmts[cs].end if cs is not None else (self.owner_block_end("") or self.end_pos())
            nm = self.doc.form_props.get("Name")
            if cs is None and nm is not None:
                pos = self.doc.stmts[nm].start
        elif parent in getattr(self, "_new_blocks", {}):
            self._new_blocks[parent].append(code)
            return
        else:
            # first statement of the parent's block (after its comment header)
            idxs = [i for i, st in enumerate(self.doc.stmts) if st.owner == parent and st.kind == "prop"]
            pos = self.doc.stmts[idxs[0]].start if idxs else self.form_block_start()
        self.insert(pos, code)

    # ---------------------------------------------------------------- new controls
    def _add_field(self, name: str, typ: str) -> None:
        d = self.doc
        line = self.doc.d.field_decl(name, typ)
        fields = {n: f for n, f in d.fields.items() if n != "components"}
        if fields:
            last = max(fields.values(), key=lambda f: f[2])
            ind = re.match(r"[ \t]*", d.text[last[1]:]).group(0)
            pos = last[2]
            if d.text[pos - 1:pos] != "\n":
                line = self.nl + ind + line
                self.insert(pos, line)
                return
            self.insert(pos, f"{ind}{line}{self.nl}")
            return
        pos, prefix, ind = self.doc.d.field_insert_point(d, self.nl)
        if getattr(self, "_field_prefix_done", False):
            prefix = ""
        self._field_prefix_done = True
        self.insert(pos, f"{prefix}{ind}{line}{self.nl}")

    def _add_controls(self, ctrls: list[Control]) -> None:
        d = self.doc.d
        self._new_blocks: dict[str, list[str]] = {c.name: [] for c in ctrls}
        news, blocks = [], []
        if any(not CONTROL_TYPES[c.type].nonvisual for c in ctrls) and self.doc.suspend_idx < 0 and \
                not getattr(self, "_suspend_added", False):
            self._suspend_added = True
            self._layout_calls = True
        tab_next = max([int(c.props.get("TabIndex", 0) or 0) for c in self.form.controls
                        if c.name not in self._new_blocks] or [-1]) + 1
        new_names = {c.name for c in ctrls}
        for c in ctrls:
            wt = c.props.get("_wft") if c.props.get("_wft") and c.type == "Panel" else NEUTRAL_TO_WF[c.type]
            sw = short(wt)
            typ = self.T(sw) if "." not in wt else wt
            args = self.ref("components") if sw in COMPONENT_TYPES else ""
            if args:
                self._ensure_components()
            news.append(self.line(d.assign(self.ref(c.name), d.new(typ, args))))
            self._add_field(c.name, typ)
            extra_news, block = self._control_block(c, sw, tab_next)
            news += extra_news
            if not CONTROL_TYPES[c.type].nonvisual and c.props.get("TabIndex", 0) in (0, None):
                tab_next += 1
            blocks.append((c, block))
        # instantiations
        self.insert(self.new_stmts_end(), "".join(news))
        if getattr(self, "_layout_calls", False):
            self.insert(self.new_stmts_end(), self.line(d.call(f"{self.me()}SuspendLayout")))
            self._layout_calls = False
            self._resume_needed = True
        # property blocks, before the form's block; Controls.Add of children land in their parent's block
        out = []
        for c, block in blocks:
            par = self._net_parent(c)
            if not CONTROL_TYPES[c.type].nonvisual and c.type not in ("MenuStrip",) or c.type == "MenuStrip":
                if CONTROL_TYPES[c.type].nonvisual and c.type not in ("MenuStrip", "ToolStrip"):
                    pass
                elif par in new_names or par in getattr(self, "_new_page_names", set()):
                    self._new_blocks.setdefault(par, []).append(self.line(d.call(f"{self.ref(par)}.Controls.Add",
                                                                                  self.ref(c.name))))
                else:
                    self._add_to_parent(c.name, par)
            hdr = [self.line(d.comment_line("")), self.line(d.comment_line(c.name)), self.line(d.comment_line(""))]
            out.append((c, hdr, block))
        text = ""
        for c, hdr, block in out:
            adds = self._new_blocks.get(c.name, [])
            text += "".join(hdr) + "".join(adds) + "".join(block)
        text += "".join(str(x) for x in getattr(self, "_page_blocks", []))
        self.insert(self.form_block_start(), text)
        if any(c.type == "MenuStrip" for c in ctrls) and "MainMenuStrip" not in self.doc.form_props:
            m = next(c for c in ctrls if c.type == "MenuStrip")
            self.set_prop("", "MainMenuStrip", self.ref(m.name))
        if getattr(self, "_resume_needed", False) and self.doc.resume_idx < 0:
            self._resume_text = self.line(d.call(f"{self.me()}ResumeLayout", d.lit_bool(False))) +                 self.line(d.call(f"{self.me()}PerformLayout"))
            self._resume_pos = self.method_end()
            self.insert(self._resume_pos, self._resume_text)

    def _control_block(self, c: Control, sw: str, tab_next: int) -> tuple[list[str], list[str]]:
        """(extra instantiation lines, property lines) of a new control, VS order (alphabetical)."""
        d = self.doc.d
        p = c.props
        nt = c.type
        ct = CONTROL_TYPES[nt]
        props: dict[str, str] = {}
        extra_news: list[str] = []
        pre: list[str] = []
        if not ct.nonvisual or nt in ("MenuStrip", "ToolStrip"):
            nx, top = self._native_xy(c)
            if nt in ("MenuStrip", "ToolStrip"):
                props["Location"] = self.v_point(0, 24 if nt == "ToolStrip" and self.form.menu() else 0)
                props["Size"] = self.v_size(self.form.props.get("Width", 300), 24 if nt == "MenuStrip" else 25)
            else:
                if p.get("Dock", "None") == "None":
                    props["Location"] = self.v_point(nx, top)
                props["Size"] = self.v_size(p.get("Width", 75), p.get("Height", 23))
            ti = p.get("TabIndex", 0)
            props["TabIndex"] = str(int(ti) if ti else tab_next)
        if sw not in NONVISUAL_WF:           # components (Timer, ToolTip, dialogs...) have no Name property
            props["Name"] = d.lit_str(c.name)
        if ct.has_text and not ct.nonvisual and nt != "StatusBar":
            props["Text"] = d.lit_str(str(p.get("Text", "")))
        if nt in ("MenuStrip", "ToolStrip"):
            props["Text"] = d.lit_str(c.name)
        if sw in UVSBC:
            props["UseVisualStyleBackColor"] = d.lit_bool(True)
        # Label/LinkLabel: no AutoSize = true (VS default) - the RAD designer draws the fixed Size it stores
        if sw in ("ListBox", "ComboBox"):
            props["FormattingEnabled"] = d.lit_bool(True)
        if "FontName" in p:
            base_font = self._ambient_font(c)
            mine = (p["FontName"], int(p["FontSize"]), bool(p["FontBold"]), bool(p["FontItalic"]))
            dflt = ct.default_props(c.name)
            untouched = mine == (dflt.get("FontName"), int(dflt.get("FontSize", 0) or 0), False, False)
            if base_font != mine and not untouched:      # the toolbox default = inherit the form's font
                name, size = p["FontName"], float(p["FontSize"])
                if (name, int(size)) == (dflt.get("FontName"), int(dflt.get("FontSize", 0) or 0)):
                    name, size = base_font[0], float(base_font[1])     # only Bold / Italic was set
                    amb = _font_of(self.doc.value("", "Font"))
                    if amb is not None and int(round(amb[1])) == int(size):
                        size = amb[1]                                  # keep 8.25F
                    elif name == "Microsoft Sans Serif" and int(size) == 8:
                        size = 8.25
                props["Font"] = self.v_font(name, size, p["FontBold"], p["FontItalic"])
        for key in ("BackColor", "ForeColor"):
            if p.get(key):
                props[key] = self.v_color(p[key])
        if p.get("Anchor") and p["Anchor"].replace(" ", "") not in ("Top,Left", "Left,Top"):
            props["Anchor"] = self.v_anchor(p["Anchor"])
        if p.get("Dock", "None") not in ("None", None, "") and nt not in ("MenuStrip", "ToolStrip"):
            props["Dock"] = self.v_enum("DockStyle", p["Dock"])
        if nt == "StatusBar":
            props.pop("Location", None)
        if p.get("Enabled") is False and nt != "Timer":
            props["Enabled"] = d.lit_bool(False)
        if nt == "Timer" and p.get("Enabled"):
            props["Enabled"] = d.lit_bool(True)
        if p.get("Visible") is False:
            props["Visible"] = d.lit_bool(False)
        if p.get("ReadOnly"):
            props["ReadOnly"] = d.lit_bool(True)
        if p.get("Multiline"):
            props["Multiline"] = d.lit_bool(True)
        if p.get("Checked") and nt in ("CheckBox", "RadioButton"):
            props["Checked"] = d.lit_bool(True)
        if p.get("PasswordChar"):
            props["PasswordChar"] = d.lit_char(p["PasswordChar"])
        if int(p.get("MaxLength", 0) or 0) > 0:
            props["MaxLength"] = str(int(p["MaxLength"]))
        if "TextAlign" in p:
            al = self._align(nt, sw, p["TextAlign"])
            if al:
                props["TextAlign"] = al
        for key, dflt in (("Minimum", 0), ("Maximum", 100), ("Value", 0)):
            if key in p and nt in ("ProgressBar", "NumericUpDown", "TrackBar") and int(p[key]) != dflt:
                props[key] = str(int(p[key]))
        if nt == "Timer" and int(p.get("Interval", 100)) != 100:
            props["Interval"] = str(int(p["Interval"]))
        if nt == "ComboBox" and p.get("DropDownStyle") == "DropDownList":
            props["DropDownStyle"] = self.v_enum("ComboBoxStyle", "DropDownList")
        if nt == "DateTimePicker" and p.get("Format") in ("Short", "Time"):
            props["Format"] = self.v_enum("DateTimePickerFormat", p["Format"])
        if nt == "ListView":
            props["View"] = self.v_enum("View", p.get("View", "Details"))
        if nt in ("OpenFileDialog", "SaveFileDialog"):
            for key in ("Filter", "Title", "FileName", "InitialDirectory"):
                if p.get(key):
                    props[key] = d.lit_str(p[key])
            props.pop("Name", None)
        if nt == "PictureBox" and p.get("Image"):
            try:
                data = Path(p["Image"]).read_bytes()
                if self.resx is None:
                    self.resx = ResxFile.new(self.doc.path.with_name(self.doc.path.name.split(".")[0] + ".resx"))
                self.resx.set_bytes(f"{c.name}.Image", data, image_type_for(data))
                self._ensure_resources()
                props["Image"] = d.get_object(f"{c.name}.Image", self.T("Image", DRAWING_NS))
                self.needs_resx = True
            except OSError:
                self.report.append(f"{c.name}.Image: cannot read {p['Image']}")
        if nt in ("ListBox", "ComboBox") and split_items(p.get("Items", "")):
            arr = d.new_array("object" if d.lang == "cs" else "Object",
                              [d.lit_str(x) for x in split_items(p["Items"])], self.ind)
            pre.append(self.line(d.call(f"{self.ref(c.name)}.Items.AddRange", arr)))
        if nt in ("MenuStrip", "ToolStrip"):
            extra_news, item_blocks, top = self._new_menu_items(c.name, p.get("Items") or [], nt)
            if top:
                arr = d.new_array(self.T("ToolStripItem"), [self.ref(x) for x in top], self.ind)
                pre.append(self.line(d.call(f"{self.ref(c.name)}.Items.AddRange", arr)))
            self._page_blocks = getattr(self, "_page_blocks", []) + item_blocks
        if nt == "StatusBar":
            lbl = self._unique("toolStripStatusLabel")
            extra_news.append(self.line(d.assign(self.ref(lbl), d.new(self.T("ToolStripStatusLabel")))))
            self._add_field(lbl, self.T("ToolStripStatusLabel"))
            pre.append(self.line(d.call(f"{self.ref(c.name)}.Items.AddRange",
                                        d.new_array(self.T("ToolStripItem"), [self.ref(lbl)], self.ind))))
            self._page_blocks = getattr(self, "_page_blocks", []) + [
                self.line(d.comment_line("")), self.line(d.comment_line(lbl)), self.line(d.comment_line("")),
                self.line(d.assign(self.target(lbl, "Name"), d.lit_str(lbl))),
                self.line(d.assign(self.target(lbl, "Text"), d.lit_str(str(p.get("Text", "")))))]
        if nt == "TabControl":
            pages = split_items(p.get("TabPages", "")) or ["TabPage1"]
            names = []
            for i, txt in enumerate(pages):
                pn = self._unique("tabPage" if d.lang == "cs" else "TabPage")
                names.append(pn)
                extra_news.append(self.line(d.assign(self.ref(pn), d.new(self.T("TabPage")))))
                self._add_field(pn, self.T("TabPage"))
                pre.append(self.line(d.call(f"{self.ref(c.name)}.Controls.Add", self.ref(pn))))
            self._new_pages = getattr(self, "_new_pages", {})
            self._new_pages[c.name] = names
            self._new_page_names = getattr(self, "_new_page_names", set()) | set(names)
            for i, (pn, txt) in enumerate(zip(names, pages)):
                self._new_blocks.setdefault(pn, [])
                self._page_blocks = getattr(self, "_page_blocks", []) + [_Deferred(self, pn, txt, i)]
        if p.get("ToolTip"):
            self._tooltip(c.name, p["ToolTip"])
        lines = list(pre)
        for k in sorted(props):
            lines.append(self.line(d.assign(self.target(c.name, k), props[k])))
        lines += self._new_wires(c.name)
        return extra_news, lines

    def _ambient_font(self, c: Control):
        par = c.props.get("Parent") or ""
        pc = self.form.find(par) if par else None
        if pc is not None and "FontName" in pc.props:
            return (pc.props["FontName"], int(pc.props["FontSize"]), bool(pc.props["FontBold"]),
                    bool(pc.props["FontItalic"]))
        f = _font_of(self.doc.value("", "Font"))
        if f is None:
            n, s = _default_font(self.doc)
            f = (n, s, False, False)
        return (f[0], int(round(f[1])), f[2], f[3])

    def _unique(self, base: str) -> str:
        taken = {c.name.lower() for c in self.form.controls} | {n.lower() for n in self.doc.fields} | \
            {n.lower() for n in self.doc.items} | {n.lower() for n in self.doc.tabpages} | \
            {n.lower() for n in getattr(self, "_taken", set())} | \
            {n.lower() for c in self.form.controls if isinstance(c.props.get("Items"), list)
             for n in menu_names(c.props["Items"])}
        i = 1
        while f"{base}{i}".lower() in taken:
            i += 1
        name = f"{base}{i}"
        self._taken = getattr(self, "_taken", set()) | {name}
        return name

    # ---------------------------------------------------------------- menus
    def _item_name(self, it: dict) -> str:
        n = it.get("Name") or ""
        if n and re.match(r"^[A-Za-z_]\w*$", n):
            return n
        return self._unique("toolStripMenuItem")

    def _new_menu_items(self, owner: str, items: list, nt: str, depth: int = 0):
        """Declarations + blocks for items that do not exist in the file yet; returns (news, blocks, names)."""
        d = self.doc.d
        news, blocks, names = [], [], []
        for it in items or []:
            n = self._item_name(it)
            names.append(n)
            if n in self.doc.items:
                # existing item: only its new sub items need declarations and blocks
                kid_news, kid_blocks, _kids = self._new_menu_items(n, it.get("Items") or [], nt, depth + 1)
                news += kid_news
                blocks += kid_blocks
                continue
            sep = it.get("Text") == "-"
            typ = "ToolStripSeparator" if sep else ("ToolStripButton" if nt == "ToolStrip" and depth == 0
                                                    else "ToolStripMenuItem")
            news.append(self.line(d.assign(self.ref(n), d.new(self.T(typ)))))
            self._add_field(n, self.T(typ))
            kid_news, kid_blocks, kids = self._new_menu_items(n, it.get("Items") or [], nt, depth + 1)
            news += kid_news
            blk = [self.line(d.comment_line("")), self.line(d.comment_line(n)), self.line(d.comment_line(""))]
            if kids:
                blk.append(self.line(d.call(f"{self.ref(n)}.DropDownItems.AddRange",
                                            d.new_array(self.T("ToolStripItem"), [self.ref(k) for k in kids],
                                                        self.ind))))
            blk.append(self.line(d.assign(self.target(n, "Name"), d.lit_str(n))))
            if not sep:
                blk.append(self.line(d.assign(self.target(n, "Text"), d.lit_str(str(it.get("Text", ""))))))
                if typ == "ToolStripButton":
                    blk.append(self.line(d.assign(self.target(n, "DisplayStyle"),
                                                  self.v_enum("ToolStripItemDisplayStyle", "Text"))))
            blk += self._new_wires(n)
            blocks += blk + kid_blocks
        return news, blocks, names

    def _menu_diff(self, owner: str, old: list, new: list, nt: str) -> None:
        d = self.doc.d
        old_names = set(menu_names(old))
        new_names = set(menu_names(new))
        gone = {n for n in old_names - new_names if n in self.doc.items}
        if gone:
            self._delete_names(gone)
        # texts of kept items
        def walk(items):
            for it in items or []:
                yield it
                yield from walk(it.get("Items"))
        old_by = {it.get("Name"): it for it in walk(old)}
        for it in walk(new):
            n = it.get("Name")
            if n in old_by and n in self.doc.items and it.get("Text") != old_by[n].get("Text") and \
                    it.get("Text") != "-":
                self.set_prop(n, "Text", d.lit_str(str(it.get("Text", ""))))
        # new items + item lists
        news, blocks, top = self._new_menu_items(owner, new, nt)
        if news:
            self.insert(self.new_stmts_end(), "".join(news))
        if blocks:
            self.insert(self.form_block_start(), "".join(blocks))
        self._sync_lists(owner, new, top)

    def _sync_lists(self, owner: str, items: list, names: list[str]) -> None:
        cur = [n for n in self.doc.item_children.get(owner, [])]
        if names != cur:
            self._set_item_list(owner, names, self.doc.item_lists.get(owner))
        for it, n in zip(items or [], names):
            if n in self.doc.items and (it.get("Items") or self.doc.item_children.get(n)):
                kids = [self._item_name(k) if k.get("Name") else None for k in it.get("Items") or []]
                kids = [k for k in kids if k]
                self._sync_lists(n, it.get("Items") or [], kids)

    def _set_item_list(self, owner: str, names: list[str], idx: int | None) -> None:
        d = self.doc.d
        is_item = owner in self.doc.items
        recv = f"{self.ref(owner)}.{'DropDownItems' if is_item else 'Items'}.AddRange"
        if not names:
            if idx is not None:
                self._remove(idx)
            return
        ind = self.doc.stmts[idx].indent if idx is not None else self.ind
        code = d.call(recv, d.new_array(self.T("ToolStripItem"), [self.ref(n) for n in names], ind))
        if idx is not None:
            self._replace(idx, code)
        else:
            pos = None
            idxs = [i for i, st in enumerate(self.doc.stmts) if st.owner == owner and st.kind == "prop"]
            if idxs:
                pos = self.doc.stmts[idxs[0]].start
            self.insert(pos if pos is not None else self.form_block_start(), self.line(code))

    def _status_text(self, owner: str, text: str) -> None:
        labels = [k for k in self.doc.item_children.get(owner, []) if k in self.doc.items]
        if labels:
            self.set_prop(labels[0], "Text", self.doc.d.lit_str(text))
        else:
            self.report.append(f"{owner}: status text needs a ToolStripStatusLabel - add one in the code")

    # ---------------------------------------------------------------- tab pages
    def _tab_pages(self, owner: str, texts: list[str]) -> None:
        d = self.doc.d
        pages = doc_tab_pages(self.doc, owner)
        for pn, txt in zip(pages, texts):
            cur = self.doc.value(pn, "Text")
            if cur != txt:
                self.set_prop(pn, "Text", d.lit_str(txt))
        if len(texts) > len(pages):
            add_stmts = [i for i, st in enumerate(self.doc.stmts) if st.kind == "add" and st.owner == owner]
            pos_add = self.doc.stmts[add_stmts[-1]].end if add_stmts else None
            news, blocks, adds = [], [], []
            for i, txt in enumerate(texts[len(pages):], start=len(pages)):
                pn = self._unique("tabPage" if d.lang == "cs" else "TabPage")
                news.append(self.line(d.assign(self.ref(pn), d.new(self.T("TabPage")))))
                self._add_field(pn, self.T("TabPage"))
                adds.append(self.line(d.call(f"{self.ref(owner)}.Controls.Add", self.ref(pn))))
                blocks.append(_Deferred(self, pn, txt, i).text())
            self.insert(self.new_stmts_end(), "".join(news))
            if pos_add is not None:
                self.insert(pos_add, "".join(adds))
            else:
                self.insert(self.form_block_start(), "".join(adds))
            self.insert(self.form_block_start(), "".join(blocks))
        elif len(texts) < len(pages):
            gone = set(pages[len(texts):])
            kids = {k for pn in gone for k in self.doc.tabpages[pn].get("kids", [])}
            if kids & {c.name for c in self.form.controls}:
                self.report.append(f"{owner}: removed tab pages still had controls - pages kept")
            else:
                self._delete_names(gone)

    # ---------------------------------------------------------------- events
    def _wire_code(self, owner: str, event: str, meth: str) -> str:
        delegate = EVENT_SIG.get(event, ("EventHandler", ""))[0]
        dtype = "System.EventHandler" if delegate == "EventHandler" else self.T(delegate)
        return self.doc.d.wire(self.ref(owner), event, meth, dtype)

    def _new_wires(self, owner: str) -> list[str]:
        """Wiring lines of new handlers of a control created in this save (C# only)."""
        if self.doc.d.lang != "cs":
            return []
        ev = (self.form.extra.get("winforms") or {}).get("new_events") or {}
        out = []
        self._wired = getattr(self, "_wired", set())
        for key, meth in ev.items():
            o, _, event = key.rpartition(".")
            if o == owner and key not in self._wired:
                self._wired.add(key)
                out.append(self.line(self._wire_code(owner, event, meth)))
        return out

    def _events(self) -> None:
        wf = self.form.extra.get("winforms") or {}
        ev = wf.get("new_events") or {}
        if not ev or self.doc.d.lang != "cs":
            return
        have = {(o, e) for o, e, _m, _i in self.doc.events}
        names = {c.name for c in self.form.controls}
        items = set(self.doc.items) | {n for c in self.form.controls
                                       if isinstance(c.props.get("Items"), list)
                                       for n in menu_names(c.props["Items"])}
        done = getattr(self, "_wired", set())
        for key, meth in ev.items():
            owner, _, event = key.rpartition(".")
            if owner == self.form.name:
                owner = ""
            if (owner, event) in have or key in done:
                continue
            if owner and owner not in names and owner not in items:
                continue
            code = self._wire_code(owner, event, meth)
            pos = self.owner_block_end(owner)
            if pos is None:
                pos = self.form_block_start() if owner else self.end_pos()
            if pos == getattr(self, "_resume_pos", None) and self._resume_text in self.inserts.get(pos, []):
                # a ResumeLayout added by this save closes the method: the wiring goes in front of it
                lst = self.inserts[pos]
                lst.insert(lst.index(self._resume_text), self.line(code))
                continue
            self.insert(pos, self.line(code))


class _Deferred:
    """Property block of a new TabPage (text produced when the page list is known)."""

    def __init__(self, r: Renderer, name: str, text: str, index: int):
        self.r, self.name, self.title, self.index = r, name, text, index

    def text(self) -> str:
        r, d = self.r, self.r.doc.d
        lines = [r.line(d.comment_line("")), r.line(d.comment_line(self.name)), r.line(d.comment_line(""))]
        lines += r._new_blocks.get(self.name, []) if hasattr(r, "_new_blocks") else []
        lines += [r.line(d.assign(r.target(self.name, "Location"), r.v_point(4, 24))),
                  r.line(d.assign(r.target(self.name, "Name"), d.lit_str(self.name))),
                  r.line(d.assign(r.target(self.name, "Padding"),
                                  d.new(r.T("Padding"), "3"))),
                  r.line(d.assign(r.target(self.name, "TabIndex"), str(self.index))),
                  r.line(d.assign(r.target(self.name, "Text"), d.lit_str(self.title))),
                  r.line(d.assign(r.target(self.name, "UseVisualStyleBackColor"), d.lit_bool(True)))]
        return "".join(lines)

    def __str__(self):
        return self.text()

    def __add__(self, other):
        return self.text() + other

    def __radd__(self, other):
        return other + self.text()


def _lhs(stmt_text: str, lang: str) -> str | None:
    """Left-hand side of an assignment statement (text kept verbatim)."""
    masked = mask_cs(stmt_text) if lang == "cs" else _mask_vb(stmt_text)
    depth = 0
    for i, ch in enumerate(masked):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "=" and depth == 0 and masked[i + 1:i + 2] != "=" and masked[i - 1:i] not in "!<>+-=":
            return stmt_text[:i].rstrip()
    return None


def _mask_vb(s: str) -> str:
    out = list(s)
    i = 0
    while i < len(s):
        if s[i] == '"':
            j = i + 1
            while j < len(s):
                if s[j] == '"':
                    if s[j + 1:j + 2] == '"':
                        j += 2
                        continue
                    break
                j += 1
            for k in range(i, min(j + 1, len(s))):
                out[k] = " "
            i = j + 1
            continue
        if s[i] == "'":                      # comment: to the end of the line
            k = i
            while k < len(s) and s[k] != "\n":
                out[k] = " "
                k += 1
            i = k
            continue
        i += 1
    return "".join(out)


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s.rstrip(";"))


def _apply_renames(doc: DesignerDoc, renames: dict[str, str]) -> str:
    """Rename identifiers in InitializeComponent + field declarations (strings: only "old" / "old.x")."""
    text = doc.text
    rx = re.compile(r"(?<![\w$])(" + "|".join(re.escape(o) for o in renames) + r")\b")
    is_vb = doc.d.lang == "vb"
    spans = [(doc.ic0, doc.ic1)] + [(f[1], f[2]) for n, f in doc.fields.items() if n in renames]
    out = text
    for a, b in sorted(spans, reverse=True):
        seg = out[a:b]
        masked = _mask_vb(seg) if is_vb else mask_cs(seg)

        def code_sub(m, seg=seg, masked=masked):
            return renames[m.group(1)] if masked[m.start():m.end()] == m.group(0) else m.group(0)
        seg2 = rx.sub(lambda m: code_sub(m) if (is_vb and True) else code_sub(m), seg) if not is_vb else \
            re.sub(r"(?i)(?<![\w$])(" + "|".join(re.escape(o) for o in renames) + r")\b",
                   lambda m: next((renames[o] for o in renames if o.lower() == m.group(1).lower()), m.group(1))
                   if masked[m.start():m.end()] == m.group(0) else m.group(0), seg)
        # strings: "old" and "old.Prop" (Name / resource keys)
        for o, n in renames.items():
            seg2 = re.sub(r'"' + re.escape(o) + r'(\.[\w.]+)?"', lambda m, n=n: f'"{n}{m.group(1) or ""}"', seg2)
            # the "// button1" / "'Button1" header of its property block
            seg2 = re.sub(r"(?m)^([ \t]*(?://|')[ \t]*)" + re.escape(o) + r"([ \t]*\r?)$",
                          lambda m, n=n: f"{m.group(1)}{n}{m.group(2)}", seg2)
        out = out[:a] + seg2 + out[b:]
    return out


# ============================================================================ store / session
class _Session:
    def __init__(self, path: Path, dialect):
        self.path = Path(path)
        self.dialect = dialect
        self.reload()

    def reload(self) -> None:
        raw = self.path.read_bytes()
        self.bom = raw.startswith(b"\xef\xbb\xbf")
        self.text = raw.decode("utf-8-sig")
        self.doc = DesignerDoc(self.path, self.text, self.dialect)
        rp = self.resx_path()
        self.resx = ResxFile.load(rp) if rp.is_file() else None
        self.mtime = self.path.stat().st_mtime_ns

    def resx_path(self) -> Path:
        return self.path.with_name(self.path.name.split(".")[0] + ".resx")

    def fresh(self) -> None:
        try:
            if self.path.stat().st_mtime_ns != self.mtime:
                self.reload()
        except OSError:
            pass


_SESSIONS: dict[str, _Session] = {}


def dialect_for(path: Path):
    if str(path).lower().endswith(".vb"):
        from .winforms_vb import VBDialect
        return VBDialect()
    return CSharpDialect()


def session(path) -> _Session:
    path = Path(path).resolve()
    key = str(path).lower()
    s = _SESSIONS.get(key)
    if s is None:
        s = _SESSIONS[key] = _Session(path, dialect_for(path))
    else:
        s.fresh()
    return s


def designer_path_of(path) -> Path | None:
    """Form1.form / Form1.cs / Form1.Designer.cs -> the Designer file (or None)."""
    p = Path(path)
    low = p.name.lower()
    if low.endswith((".designer.cs", ".designer.vb")):
        return p
    stem = p.name.split(".")[0]
    for ext in (".Designer.cs", ".Designer.vb"):
        q = p.with_name(stem + ext)
        if q.is_file():
            return q
    return None


def register_plugins() -> None:
    """Make winforms-cs / winforms-vb known to radide.languages.get_plugin (after the normal discovery,
    so they are listed only once a WinForms form of a Visual Studio project was opened)."""
    from .. import languages
    languages.all_plugins()
    from .winforms_vb import PLUGIN as VBP
    for p in (PLUGIN, VBP):
        languages._PLUGINS.setdefault(p.id, p)


def load_form(path) -> Form:
    register_plugins()
    s = session(designer_path_of(path) or path)
    if not s.doc.ok:
        raise ValueError(f"{s.path.name}: {s.doc.problem}")
    ld = Loader(s.doc, s.resx)
    form = ld.build()
    form.extra["winforms"]["notes"] = ld.notes
    _load_vb_handles(form, s)
    return form


def _patch_handles(code: str, deleted: set, renames: dict) -> str:
    low_del = {n.lower() for n in deleted}
    low_ren = {o.lower(): n for o, n in renames.items()}

    def fix(m):
        kept = []
        for part in m.group(2).split(","):
            ref = part.strip()
            owner, _, ev = ref.rpartition(".")
            if owner.lower() in low_del:
                continue
            if owner.lower() in low_ren:
                ref = f"{low_ren[owner.lower()]}.{ev}"
            kept.append(ref)
        return f"{m.group(1)}Handles {', '.join(kept)}" if kept else m.group(1).rstrip(" \t")
    return re.sub(r"(?im)^([^'\n]*\)[ \t]*)Handles[ \t]+([\w.]+(?:[ \t]*,[ \t]*[\w.]+)*)", fix, code)


def _fix_vb_handles(code_path: Path, deleted: set, renames: dict) -> None:
    """Update the Handles clauses of Form1.vb on disk and in an open IDE editor of it."""
    try:
        from PyQt6.QtWidgets import QApplication
        wins = [w for w in QApplication.topLevelWidgets() if hasattr(w, "codeviews")] \
            if QApplication.instance() else []
    except Exception:  # noqa: BLE001
        wins = []
    for w in wins:
        for cv in list(getattr(w, "codeviews", {}).values()):
            if Path(str(getattr(cv, "path", ""))).resolve() != code_path.resolve():
                continue
            ed = cv.editor
            new = _patch_handles(ed.text(), deleted, renames)
            if new != ed.text():
                was = ed.isModified()
                w._replace_code(cv, new)
                ed.setModified(was)
    try:
        raw = code_path.read_bytes()
    except OSError:
        return
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8", errors="surrogateescape")
    new = _patch_handles(text, deleted, renames)
    if new != text:
        code_path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8", errors="surrogateescape"))


def _code_file_of(designer: Path) -> Path:
    stem = designer.name.split(".")[0]
    ext = ".vb" if designer.name.lower().endswith(".vb") else ".cs"
    return designer.with_name(stem + ext)


def _load_vb_handles(form: Form, s: _Session) -> None:
    """Event handlers of the form (C#: += in InitializeComponent; VB: also Handles clauses in Form1.vb)."""
    wf = form.extra["winforms"]
    events = {f"{o or form.name}.{e}": m for o, e, m, _i in s.doc.events}
    if s.dialect.lang == "vb":
        code = _code_file_of(s.path)
        if code.is_file():
            from .winforms_vb import handles_map
            events.update(handles_map(code.read_text(encoding="utf-8-sig", errors="replace"), form.name))
    wf["events"] = events


def render_form(form: Form, code_text: str = "") -> tuple[str, list[str], Renderer]:
    wf = form.extra.get("winforms") or {}
    path = wf.get("designer")
    if not path:
        raise ValueError("this form was not loaded from a WinForms Designer file")
    s = session(path)
    r = Renderer(s.doc, form, s.resx, code_text)
    text = r.render()
    return text, r.report, r


def save_form(form: Form, path=None) -> list[str]:
    """Write Form1.Designer.cs (+ .resx) when they changed; returns report lines."""
    wf = form.extra.get("winforms") or {}
    dp = Path(path) if path and str(path).lower().endswith((".designer.cs", ".designer.vb")) else \
        Path(wf.get("designer") or designer_path_of(path))
    form.extra.setdefault("winforms", {})["designer"] = str(dp)
    s = session(dp)
    r = Renderer(s.doc, form, s.resx)
    text = r.render()
    if text != s.text:
        data = text.encode("utf-8")
        dp.write_bytes((b"\xef\xbb\xbf" if s.bom else b"") + data)
    if r.resx is not None and r.resx.modified:
        r.resx.save()
    if s.dialect.lang == "vb" and (getattr(r, "deleted", None) or getattr(r, "renamed", None)):
        # like Visual Studio: Handles clauses of deleted controls go, renamed ones follow the rename
        _fix_vb_handles(_code_file_of(dp), set(r.deleted), r.renamed)
    if text != s.text or (r.resx is not None):
        s.reload()
    # after a save the file is the new baseline: original names / offset follow it
    for c in form.controls:
        if "_wf" in c.props or c.name in s.doc.controls:
            c.props["_wf"] = c.name
            if c.name in s.doc.controls:
                c.props["_wft"] = s.doc.controls[c.name]["wtype"]
    wf = form.extra["winforms"]
    wf["offset"] = menu_offset(s.doc)
    if wf.get("new_events"):
        if s.dialect.lang == "cs":
            have = {f"{o or form.name}.{e}" for o, e, _m, _i in s.doc.events}
            wf["new_events"] = {k: v for k, v in wf["new_events"].items() if k not in have}
        wf.setdefault("events", {}).update(wf.get("new_events") or {})
        if s.dialect.lang == "cs":
            wf["events"] = {f"{o or form.name}.{e}": m for o, e, m, _i in s.doc.events} | \
                (wf.get("new_events") or {})
    return r.report


class WinFormsStore:
    """FORM_STORES entry: Form.load / Form.save of WinForms Designer files."""

    def handles(self, path: Path) -> bool:
        low = path.name.lower()
        if low.endswith((".designer.cs", ".designer.vb")):
            return path.is_file()
        if low.endswith(".form") and not path.exists():
            return designer_path_of(path) is not None
        return False

    def load(self, path: Path) -> Form:
        return load_form(path)

    def save(self, path: Path, form: Form) -> None:
        save_form(form, path)


STORE = WinFormsStore()
if not any(isinstance(s, WinFormsStore) for s in FORM_STORES):
    FORM_STORES.append(STORE)


# ============================================================================ event handlers in Form1.cs
def handler_signature(event: str) -> str:
    net = EVENT_TO_NET.get(event, event)
    return EVENT_SIG.get(net, ("EventHandler", "EventArgs"))[1]


def add_event_handler_cs(code: str, form_name: str, method: str, event: str) -> tuple[str, int]:
    """Insert `private void method(object sender, XEventArgs e) { }` before the end of the form class."""
    nl = "\r\n" if "\r\n" in code else "\n"
    masked = mask_cs(code)
    m = None
    for mm in re.finditer(r"\bclass\s+(\w+)[^{;]*\{", masked):
        if mm.group(1) == form_name or m is None:
            m = mm
            if mm.group(1) == form_name:
                break
    args = handler_signature(event)
    if m is None:
        body = f"private void {method}(object sender, {args} e){nl}{{{nl}{nl}}}{nl}"
        return code + nl + body, code.count("\n") + 3
    end = _match_brace(code, m.end() - 1)
    cls_line_start = code.rfind("\n", 0, m.start()) + 1
    cls_ind = re.match(r"[ \t]*", code[cls_line_start:]).group(0)
    ind = cls_ind + "    "
    mi = re.search(r"\n([ \t]+)\S", code[m.end():end])
    if mi:
        ind = mi.group(1)
    line_start = code.rfind("\n", 0, end) + 1
    before = code[:line_start]
    sep = "" if before.rstrip().endswith("{") else nl
    stub = (f"{sep}{ind}private void {method}(object sender, {args} e){nl}{ind}{{{nl}{ind}    {nl}"
            f"{ind}}}{nl}")
    new = before + stub + code[line_start:]
    line = before.count("\n") + (1 if sep else 0) + 3
    return new, line


def find_handler_cs(code: str, name: str) -> int:
    rx = re.compile(r"^\s*(?:(?:public|private|internal|protected|static|async|override|virtual)\s+)*"
                    rf"(?:void|Task)\s+{re.escape(name)}\s*\(")
    for i, ln in enumerate(code.splitlines()):
        if rx.search(ln):
            return i
    return -1


# ============================================================================ language plugin
class WinFormsCSPlugin(LanguagePlugin):
    """Form language for WinForms forms of opened Visual Studio C# projects (project.form_languages)."""
    id = "winforms-cs"
    display_name = "C# WinForms (Visual Studio project)"
    code_ext = ".cs"
    interpreter_names = ["dotnet"]
    keywords = ("abstract as base bool break byte case catch char checked class const continue decimal default "
                "delegate do double else enum event explicit extern false finally fixed float for foreach goto if "
                "implicit in int interface internal is lock long namespace new null object operator out override "
                "params private protected public readonly ref return sbyte sealed short sizeof stackalloc static "
                "string struct switch this throw true try typeof uint ulong unchecked unsafe ushort using virtual "
                "void volatile while var async await partial get set value").split()
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'"]
    dialect_lang = "cs"
    # Toolbox (radide/toolbox.py TOOL_STATE.set_profile): the WinForms names of the controls the
    # writer can create; the others (no WinForms equivalent) are hidden while a WinForms form is shown
    designer_profile = {"name": "Windows Forms", "labels": dict(NEUTRAL_TO_WF), "allowed": set(NEUTRAL_TO_WF)}

    def __init__(self):
        self._pending: dict[str, tuple] = {}

    # Properties window: .NET property names for the neutral model's properties
    def property_label(self, name: str, ctrl: Control | None) -> str | None:
        if ctrl is not None and ctrl.type == "StatusBar" and name == "Text":
            return "Items[0].Text"
        if ctrl is not None and ctrl.type == "Timer" and name == "Enabled":
            return "Enabled"
        return NET_PROPERTY_LABELS.get(name)

    def type_label(self, ctrl: Control) -> str:
        wt = ctrl.props.get("_wft") or NEUTRAL_TO_WF.get(ctrl.type) or ctrl.type
        return wt if "." in wt else f"{FORMS_NS}.{wt}"

    def code_file(self, form_name: str) -> str:
        return f"{form_name}{self.code_ext}"

    def designer_file(self, form_name: str) -> str:
        return f"{form_name}.Designer{self.code_ext}"

    def generate_designer(self, form: Form, user_code: str) -> str:
        if (form.extra.get("winforms") or {}).get("designer"):
            text, _rep, _r = render_form(form, user_code)
            return text
        return new_designer_text(form, self.dialect_lang)

    def new_code(self, form: Form, is_startup: bool) -> str:
        return new_code_text(form, self.dialect_lang)

    # events: the real wired method names of the file; new ones are recorded for the Designer
    def handler_for(self, form: Form, ctrl: Control | None, event: str) -> str:
        if ctrl is not None and ctrl.type in ("MenuStrip", "ToolStrip"):
            owner, ev = event, "Click"
        else:
            owner, ev = (ctrl.name if ctrl else form.name), event
        net = EVENT_TO_NET.get(ev, ev)
        wf = form.extra.get("winforms") or {}
        key = f"{owner}.{net}"
        meth = (wf.get("events") or {}).get(key) or (wf.get("new_events") or {}).get(key)
        if meth is None:
            meth = f"{owner}_{net}"
        self._pending[meth] = (form, owner, net)
        return meth

    def events_for(self, ctrl):
        if ctrl is None:
            return list(FORM_EVENTS)
        return super().events_for(ctrl)

    def rename_symbol(self, code: str, old: str, new: str) -> str:
        # like Visual Studio: the field is renamed, handlers keep their names
        return re.sub(rf"\b{re.escape(old)}\b", new, code)

    def find_handler(self, code: str, name: str) -> int:
        return find_handler_cs(code, name)

    def add_handler(self, code: str, name: str, form: Form, args: str | None = None) -> tuple[str, int]:
        pend = self._pending.get(name)
        owner, event = (pend[1], pend[2]) if pend else (name.rsplit("_", 1) + [""])[:2]
        out = add_event_handler_cs(code, form.name, name, event)
        wf = form.extra.setdefault("winforms", {})
        wf.setdefault("new_events", {})[f"{owner}.{event}"] = name
        return out

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        return RunSpec(interpreter or "dotnet", ["run"], folder)


def add_event_handler(code: str, form: Form, owner: str, event: str) -> tuple[str, int, str]:
    """Create (or find) the handler of owner.event in the code-behind text; returns (code, line, method)."""
    lang = (form.extra.get("winforms") or {}).get("lang", "cs")
    plugin = PLUGIN if lang == "cs" else __import__("radide.foreign.winforms_vb", fromlist=["PLUGIN"]).PLUGIN
    ctrl = form.find(owner) if owner and owner != form.name else None
    if ctrl is None and owner and owner != form.name:
        # a menu / tool strip item: the designer convention is handler_for(form, strip, item_name)
        strip = next((c for c in form.controls if isinstance(c.props.get("Items"), list)
                      and owner in menu_names(c.props["Items"])), None)
        if strip is not None:
            ctrl, event = strip, owner
    meth = plugin.handler_for(form, ctrl, event)
    line = plugin.find_handler(code, meth)
    if line >= 0:
        return code, line + 1, meth
    code, line = plugin.add_handler(code, meth, form)
    return code, line, meth


# ============================================================================ brand-new forms
def new_designer_text(form: Form, lang: str = "cs", namespace: str = "") -> str:
    """A Designer file for a form that has none (template + the form's controls)."""
    name = form.name
    if lang == "vb":
        from .winforms_vb import VB_TEMPLATE
        base = VB_TEMPLATE.format(name=name)
    else:
        ns_open = f"namespace {namespace};\r\n\r\n" if namespace else ""
        base = CS_TEMPLATE.replace("{ns}", ns_open).replace("{name}", name)
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="radwf")) / f"{name}.Designer.{lang}"
    tmp.write_text(base, encoding="utf-8")
    doc = DesignerDoc(tmp, base, dialect_for(tmp))
    f2 = Form.from_dict(form.to_dict())
    f2.extra["winforms"] = {"designer": str(tmp), "lang": lang, "offset": 0}
    r = Renderer(doc, f2, None)
    text = r.render()
    try:
        tmp.unlink()
        tmp.parent.rmdir()
    except OSError:
        pass
    return text


def new_code_text(form: Form, lang: str = "cs", namespace: str = "") -> str:
    if lang == "vb":
        return f"Public Class {form.name}\r\n\r\nEnd Class\r\n"
    ns = f"namespace {namespace};\r\n\r\n" if namespace else ""
    return (f"{ns}public partial class {form.name} : Form\r\n{{\r\n    public {form.name}()\r\n    {{\r\n"
            f"        InitializeComponent();\r\n    }}\r\n}}\r\n")


CS_TEMPLATE = """{ns}partial class {name}\r
{\r
    /// <summary>\r
    ///  Required designer variable.\r
    /// </summary>\r
    private System.ComponentModel.IContainer components = null;\r
\r
    /// <summary>\r
    ///  Clean up any resources being used.\r
    /// </summary>\r
    /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>\r
    protected override void Dispose(bool disposing)\r
    {\r
        if (disposing && (components != null))\r
        {\r
            components.Dispose();\r
        }\r
        base.Dispose(disposing);\r
    }\r
\r
    #region Windows Form Designer generated code\r
\r
    /// <summary>\r
    ///  Required method for Designer support - do not modify\r
    ///  the contents of this method with the code editor.\r
    /// </summary>\r
    private void InitializeComponent()\r
    {\r
        this.components = new System.ComponentModel.Container();\r
        this.AutoScaleMode = System.Windows.Forms.AutoScaleMode.Font;\r
        this.ClientSize = new System.Drawing.Size(800, 450);\r
        this.Text = "{name}";\r
    }\r
\r
    #endregion\r
}\r
"""


def _cs_field_insert_point(doc: DesignerDoc, nl: str):
    """(position, prefix, indent) for the first field declaration: after #endregion, else before '}'."""
    text = doc.text
    m = None
    for mm in re.finditer(r"(?m)^([ \t]*)#endregion[^\n]*\n", text[doc.b0:doc.b1]):
        m = mm
    ind = re.match(r"[ \t]*", text[doc.ic0:]).group(0)
    cls_line = text.rfind("\n", 0, doc.cls_start) + 1
    ind = re.match(r"[ \t]*", text[cls_line:]).group(0) + "    "
    if m:
        return doc.b0 + m.end(), nl, ind
    line_start = text.rfind("\n", 0, doc.b1) + 1
    return line_start, nl, ind


CSharpDialect.field_insert_point = staticmethod(_cs_field_insert_point)
PLUGIN = WinFormsCSPlugin()
