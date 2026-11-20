"""Delphi .dfm / Lazarus .lfm form files <-> the neutral form model (radide/model.py).

The parser builds a *concrete* syntax tree: every byte of the file belongs to exactly one
segment (object header, property, child object, ``end`` line), so rendering an unchanged
tree gives the original text back byte for byte.  The writer only touches what changed in
the designer (a property value, a new / deleted / moved / renamed component); every other
property, component, comment-free gap and the original formatting is kept verbatim.

Binary .dfm files (``TPF0`` signature) are converted to text (``binary_dfm_to_text``).

Used by radide/foreign/delphi.py (Delphi .dpr/.dproj/.groupproj) and
radide/foreign/lazarus.py (Lazarus .lpi/.lpr).
"""
from __future__ import annotations

import copy
import re
import struct
from dataclasses import dataclass, field

# =============================================================================== parser


class DfmError(ValueError):
    pass


@dataclass
class DProp:
    name: str
    kind: str            # str | int | float | ident | set | list | coll | bin
    value: object        # python value (see _parse_value)
    vstart: int          # raw value span in the text
    vend: int
    seg_start: int = 0   # segment: from the end of the previous item ...
    seg_end: int = 0     # ... to after the newline that ends this property

    @property
    def raw(self) -> str:      # filled by the parser
        return self._raw

    @raw.setter
    def raw(self, v: str) -> None:
        self._raw = v


@dataclass(eq=False)
class DObj:
    kind: str                       # object | inherited | inline
    name: str
    cls: str
    line_start: int = 0             # first char of the header line (its indentation)
    name_span: tuple | None = None
    hdr_end: int = 0                # after the newline of the header line
    end_seg_start: int = 0          # where the "end" segment starts (after the last item)
    end: int = 0                    # after the newline that follows "end"
    seg_start: int = 0              # segment inside the parent (gap before the header included)
    indent: str = ""
    props: list[DProp] = field(default_factory=list)
    children: list["DObj"] = field(default_factory=list)
    items: list = field(default_factory=list)       # props and children in file order
    parent: "DObj | None" = None

    def prop(self, name: str) -> DProp | None:
        low = name.lower()
        for p in self.props:
            if p.name.lower() == low:
                return p
        return None

    def value(self, name: str, default=None):
        p = self.prop(name)
        return default if p is None else p.value

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()

    def find(self, name: str) -> "DObj | None":
        low = name.lower()
        for o in self.walk():
            if o.name.lower() == low:
                return o
        return None


_IDENT_RX = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
_NUM_RX = re.compile(r"-?(?:\$[0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
_HDR_RX = re.compile(r"(object|inherited|inline)\s+(?:([A-Za-z_][\w]*)\s*:\s*)?([A-Za-z_][\w.]*)"
                     r"(?:\s*\[\s*\d+\s*\])?", re.I)


class _Parser:
    def __init__(self, text: str):
        self.t = text
        self.i = 0
        self.n = len(text)

    def err(self, msg: str):
        line = self.t.count("\n", 0, self.i) + 1
        raise DfmError(f"line {line}: {msg}")

    def ws(self):
        t, n = self.t, self.n
        while self.i < n:
            c = t[self.i]
            if c in " \t\r\n\x0c﻿":
                self.i += 1
            elif c == "/" and t.startswith("//", self.i):           # tolerated (not written by IDEs)
                j = t.find("\n", self.i)
                self.i = n if j < 0 else j + 1
            else:
                break

    def eol(self, pos: int) -> int:
        """Position after the newline that ends the line of *pos* (only spaces may follow);
        *pos* itself when something else follows on the same line."""
        t, j, n = self.t, pos, self.n
        while j < n and t[j] in " \t":
            j += 1
        if j >= n:
            return n
        if t.startswith("\r\n", j):
            return j + 2
        if t[j] == "\n":
            return j + 1
        return pos

    def keyword_at(self, word: str) -> bool:
        t = self.t
        if t[self.i:self.i + len(word)].lower() != word:
            return False
        k = self.i + len(word)
        return k >= self.n or not (t[k].isalnum() or t[k] == "_" or t[k] == ".")

    # ------------------------------------------------------------- objects
    def parse_object(self, seg_start: int, parent: DObj | None) -> DObj:
        self.ws()
        m = _HDR_RX.match(self.t, self.i)
        if not m:
            self.err("'object' expected")
        start = m.start()
        line_start = self.t.rfind("\n", 0, start) + 1
        ind = self.t[line_start:start]
        if ind.strip():                       # something before the header on its line
            line_start, ind = start, ""
        obj = DObj(m.group(1).lower(), m.group(2) or "", m.group(3), line_start=line_start,
                   name_span=(m.start(2), m.end(2)) if m.group(2) else None, seg_start=seg_start,
                   indent=ind, parent=parent)
        self.i = m.end()
        obj.hdr_end = self.eol(self.i)
        self.i = obj.hdr_end
        prev = obj.hdr_end
        while True:
            self.ws()
            if self.i >= self.n:
                self.err(f"'end' of object {obj.name or obj.cls} missing")
            if self.keyword_at("end"):
                obj.end_seg_start = prev
                self.i += 3
                obj.end = self.eol(self.i)
                self.i = obj.end
                return obj
            if any(self.keyword_at(k) for k in ("object", "inherited", "inline")):
                child = self.parse_object(prev, obj)
                obj.children.append(child)
                obj.items.append(child)
                prev = child.end
                continue
            p = self.parse_prop(prev)
            obj.props.append(p)
            obj.items.append(p)
            prev = p.seg_end

    def parse_prop(self, seg_start: int) -> DProp:
        m = _IDENT_RX.match(self.t, self.i)
        if not m:
            self.err(f"property name expected, found {self.t[self.i:self.i + 20]!r}")
        name = m.group(0)
        self.i = m.end()
        self.ws()
        if self.i >= self.n or self.t[self.i] != "=":
            self.err(f"'=' expected after {name}")
        self.i += 1
        self.ws()
        vstart = self.i
        kind, value = self.parse_value()
        vend = self.i
        p = DProp(name, kind, value, vstart, vend, seg_start, 0)
        p.raw = self.t[vstart:vend]
        p.seg_end = self.eol(vend)
        self.i = p.seg_end
        return p

    # ------------------------------------------------------------- values
    def parse_value(self):
        t = self.t
        if self.i >= self.n:
            self.err("value expected")
        c = t[self.i]
        if c in "'#":
            return "str", self.parse_string()
        if c == "-" or c.isdigit() or c == "$":
            m = _NUM_RX.match(t, self.i)
            if not m:
                self.err("number expected")
            self.i = m.end()
            s = m.group(0)
            neg = s.startswith("-")
            body = s[1:] if neg else s
            if body.startswith("$"):
                v = int(body[1:], 16)
                return "int", -v if neg else v
            if any(ch in body for ch in ".eE"):
                return "float", float(s)
            return "int", int(s)
        if c == "[":
            self.i += 1
            vals = []
            while True:
                self.ws()
                if self.i < self.n and t[self.i] == "]":
                    self.i += 1
                    return "set", vals
                m = _IDENT_RX.match(t, self.i) or _NUM_RX.match(t, self.i)
                if not m:
                    self.err("set element expected")
                vals.append(m.group(0))
                self.i = m.end()
                self.ws()
                if self.i < self.n and t[self.i] == ",":
                    self.i += 1
        if c == "(":
            self.i += 1
            vals = []
            while True:
                self.ws()
                if self.i < self.n and t[self.i] == ")":
                    self.i += 1
                    return "list", vals
                vals.append(self.parse_value())
        if c == "<":
            self.i += 1
            items = []
            while True:
                self.ws()
                if self.i < self.n and t[self.i] == ">":
                    self.i += 1
                    return "coll", items
                if not self.keyword_at("item"):
                    self.err("'item' expected in collection")
                self.i += 4
                self.ws()
                if self.i < self.n and t[self.i] == "[":           # item [n]
                    j = t.find("]", self.i)
                    self.i = j + 1
                props = []
                while True:
                    self.ws()
                    if self.keyword_at("end"):
                        self.i += 3
                        break
                    props.append(self.parse_prop(self.i))
                items.append(props)
        if c == "{":
            j = t.find("}", self.i)
            if j < 0:
                self.err("'}' missing")
            data = re.sub(r"\s+", "", t[self.i + 1:j])
            self.i = j + 1
            return "bin", data
        m = _IDENT_RX.match(t, self.i)
        if m:
            self.i = m.end()
            return "ident", m.group(0)
        self.err(f"unexpected {c!r}")

    def parse_string(self) -> str:
        t, out = self.t, []
        while True:
            if self.i < self.n and t[self.i] == "'":
                j = self.i + 1
                buf = []
                while True:
                    k = t.find("'", j)
                    if k < 0:
                        self.err("unterminated string")
                    buf.append(t[j:k])
                    if k + 1 < self.n and t[k + 1] == "'":
                        buf.append("'")
                        j = k + 2
                        continue
                    self.i = k + 1
                    break
                out.append("".join(buf))
            elif self.i < self.n and t[self.i] == "#":
                m = re.compile(r"#(\$[0-9A-Fa-f]+|\d+)").match(t, self.i)
                if not m:
                    self.err("bad character code")
                s = m.group(1)
                out.append(chr(int(s[1:], 16) if s.startswith("$") else int(s)))
                self.i = m.end()
            else:
                break
            # concatenation:  'abc' +\n  'def'
            save = self.i
            self.ws()
            if self.i < self.n and t[self.i] == "+":
                self.i += 1
                self.ws()
                if self.i < self.n and t[self.i] in "'#":
                    continue
                self.err("string expected after '+'")
            self.i = save
            if self.i < self.n and t[self.i] in "'#":
                continue
            break
        return "".join(out)


def parse_dfm(text: str) -> DObj:
    """Parse a text .dfm / .lfm (raises DfmError)."""
    p = _Parser(text)
    p.ws()
    root = p.parse_object(0, None)
    root.seg_start = 0
    return root


def render(text: str, root: DObj) -> str:
    """Original text from an unchanged tree (used by the tests: must equal *text*)."""
    return text[:root.line_start] + text[root.line_start:root.end] + text[root.end:]


# =============================================================================== literals

def pascal_string(s: str, utf8: bool) -> str:
    """Encode a str as a DFM string literal. *utf8* (Lazarus) keeps non-ASCII characters inside
    the quotes; Delphi writes them as #nnnn codes."""
    if s == "":
        return "''"
    parts, buf = [], []

    def flush():
        if buf:
            parts.append("'" + "".join(buf).replace("'", "''") + "'")
            buf.clear()
    for ch in s:
        o = ord(ch)
        if o < 32 or (not utf8 and o > 126):
            flush()
            parts.append(f"#{o}")
        else:
            buf.append(ch)
    flush()
    return "".join(parts)


def string_list(items: list[str], indent: str, nl: str, utf8: bool) -> str:
    """TStrings like the IDEs write them: Delphi ``(\\n  'a'\\n  'b')``, Lazarus (utf8) puts the
    closing parenthesis on its own line. *indent* = indentation of the property line."""
    if not items:
        return "()"
    inner = indent + "  "
    body = "".join(nl + inner + pascal_string(x, utf8) for x in items)
    return "(" + body + (nl + indent + ")" if utf8 else ")")


# =============================================================================== VCL / LCL mapping

# VCL/LCL class -> neutral control type
CLASS_MAP = {
    "TButton": "Button", "TBitBtn": "Button", "TSpeedButton": "Button",
    "TLabel": "Label", "TStaticText": "Label",
    "TEdit": "TextBox", "TMaskEdit": "TextBox", "TLabeledEdit": "TextBox",
    "TMemo": "TextBox", "TRichEdit": "TextBox",
    "TCheckBox": "CheckBox", "TRadioButton": "RadioButton",
    "TListBox": "ListBox", "TCheckListBox": "ListBox",
    "TComboBox": "ComboBox",
    "TImage": "PictureBox", "TPaintBox": "PictureBox",
    "TProgressBar": "ProgressBar", "TTrackBar": "TrackBar",
    "TSpinEdit": "NumericUpDown", "TUpDown": "NumericUpDown",
    "TPanel": "Panel", "TScrollBox": "Panel", "TFlowPanel": "Panel", "TGridPanel": "Panel",
    "TGroupBox": "GroupBox", "TRadioGroup": "GroupBox",
    "TTimer": "Timer",
    "TMainMenu": "MenuStrip",
    "TPageControl": "TabControl",
    "TTreeView": "TreeView", "TListView": "ListView",
    "TStringGrid": "DataGridView", "TDrawGrid": "DataGridView",
    "TDateTimePicker": "DateTimePicker",
    "TStatusBar": "StatusBar",
    "TLinkLabel": "LinkLabel",
    "TOpenDialog": "OpenFileDialog", "TSaveDialog": "SaveFileDialog",
    "TColorDialog": "ColorDialog", "TFontDialog": "FontDialog",
    "TSelectDirectoryDialog": "FolderBrowserDialog",
}
# neutral type -> class written for NEW components
NEW_CLASS = {
    "Button": "TButton", "Label": "TLabel", "TextBox": "TEdit", "CheckBox": "TCheckBox",
    "RadioButton": "TRadioButton", "ListBox": "TListBox", "ComboBox": "TComboBox", "PictureBox": "TImage",
    "ProgressBar": "TProgressBar", "TrackBar": "TTrackBar", "NumericUpDown": "TSpinEdit", "Panel": "TPanel",
    "GroupBox": "TGroupBox", "Timer": "TTimer", "MenuStrip": "TMainMenu", "TabControl": "TPageControl",
    "TreeView": "TTreeView", "ListView": "TListView", "DataGridView": "TStringGrid",
    "DateTimePicker": "TDateTimePicker", "StatusBar": "TStatusBar", "OpenFileDialog": "TOpenDialog",
    "SaveFileDialog": "TSaveDialog", "ColorDialog": "TColorDialog", "FontDialog": "TFontDialog",
    "FolderBrowserDialog": "TSelectDirectoryDialog", "LinkLabel": "TLabel",
}
# unit (short name) that declares a class: used to complete the "uses" clause for new components
CLASS_UNIT = {
    "TButton": "StdCtrls", "TLabel": "StdCtrls", "TEdit": "StdCtrls", "TMemo": "StdCtrls",
    "TCheckBox": "StdCtrls", "TRadioButton": "StdCtrls", "TListBox": "StdCtrls", "TComboBox": "StdCtrls",
    "TGroupBox": "StdCtrls", "TPanel": "ExtCtrls", "TImage": "ExtCtrls", "TTimer": "ExtCtrls",
    "TProgressBar": "ComCtrls", "TTrackBar": "ComCtrls", "TPageControl": "ComCtrls", "TTabSheet": "ComCtrls",
    "TTreeView": "ComCtrls", "TListView": "ComCtrls", "TDateTimePicker": "ComCtrls", "TStatusBar": "ComCtrls",
    "TMainMenu": "Menus", "TMenuItem": "Menus", "TStringGrid": "Grids", "TSpinEdit": "Spin",
    "TOpenDialog": "Dialogs", "TSaveDialog": "Dialogs", "TColorDialog": "Dialogs", "TFontDialog": "Dialogs",
    "TSelectDirectoryDialog": "Dialogs",
}
VCL_NAMESPACE = {"StdCtrls": "Vcl.StdCtrls", "ExtCtrls": "Vcl.ExtCtrls", "ComCtrls": "Vcl.ComCtrls",
                 "Menus": "Vcl.Menus", "Grids": "Vcl.Grids", "Spin": "Vcl.Samples.Spin", "Dialogs": "Vcl.Dialogs"}

CAPTION_CLASSES = {"TButton", "TBitBtn", "TSpeedButton", "TLabel", "TStaticText", "TCheckBox", "TRadioButton",
                   "TGroupBox", "TRadioGroup", "TLinkLabel", "TTabSheet", "TMenuItem", "TPanel"}
TEXT_CLASSES = {"TEdit", "TMaskEdit", "TLabeledEdit", "TComboBox"}
LINES_CLASSES = {"TMemo", "TRichEdit"}
GRAPHIC_CLASSES = {"TLabel", "TImage", "TPaintBox", "TSpeedButton", "TShape", "TBevel", "TLinkLabel"}

NAMED_COLORS = {
    "clblack": "#000000", "clmaroon": "#800000", "clgreen": "#008000", "clolive": "#808000",
    "clnavy": "#000080", "clpurple": "#800080", "clteal": "#008080", "clgray": "#808080",
    "clsilver": "#C0C0C0", "clred": "#FF0000", "cllime": "#00FF00", "clyellow": "#FFFF00",
    "clblue": "#0000FF", "clfuchsia": "#FF00FF", "claqua": "#00FFFF", "clwhite": "#FFFFFF",
    "clmoneygreen": "#C0DCC0", "clskyblue": "#A6CAF0", "clcream": "#FFFBF0", "clmedgray": "#A4A0A0",
}
_COLOR_NAMES = {v: k for k, v in NAMED_COLORS.items()}
_PROPER = {"clblack": "clBlack", "clmaroon": "clMaroon", "clgreen": "clGreen", "clolive": "clOlive",
           "clnavy": "clNavy", "clpurple": "clPurple", "clteal": "clTeal", "clgray": "clGray",
           "clsilver": "clSilver", "clred": "clRed", "cllime": "clLime", "clyellow": "clYellow",
           "clblue": "clBlue", "clfuchsia": "clFuchsia", "claqua": "clAqua", "clwhite": "clWhite",
           "clmoneygreen": "clMoneyGreen", "clskyblue": "clSkyBlue", "clcream": "clCream",
           "clmedgray": "clMedGray"}

# neutral event -> Delphi/Lazarus event property, per class ("*" = default)
EVENT_PROPS = {
    "Click": "OnClick", "DoubleClick": "OnDblClick", "MouseDown": "OnMouseDown", "MouseUp": "OnMouseUp",
    "MouseMove": "OnMouseMove", "MouseEnter": "OnMouseEnter", "MouseLeave": "OnMouseLeave",
    "MouseWheel": "OnMouseWheel", "KeyDown": "OnKeyDown", "KeyUp": "OnKeyUp", "KeyPress": "OnKeyPress",
    "GotFocus": "OnEnter", "LostFocus": "OnExit", "TextChanged": "OnChange", "ValueChanged": "OnChange",
    "Tick": "OnTimer", "Load": "OnCreate", "Activated": "OnActivate", "Deactivate": "OnDeactivate",
    "Resize": "OnResize", "FormClosing": "OnCloseQuery", "FormClosed": "OnClose",
    "CellChanged": "OnSetEditText",
}
EVENT_PROPS_BY_TYPE = {
    ("CheckBox", "CheckedChanged"): "OnClick", ("RadioButton", "CheckedChanged"): "OnClick",
    ("ListBox", "SelectedIndexChanged"): "OnClick", ("ComboBox", "SelectedIndexChanged"): "OnSelect",
    ("TabControl", "SelectedIndexChanged"): "OnChange", ("TreeView", "SelectedIndexChanged"): "OnChange",
    ("ListView", "SelectedIndexChanged"): "OnClick", ("DataGridView", "SelectedIndexChanged"): "OnSelectCell",
}
LCL_EVENT_PROPS_BY_TYPE = {("CheckBox", "CheckedChanged"): "OnChange", ("RadioButton", "CheckedChanged"): "OnChange",
                           ("ListBox", "SelectedIndexChanged"): "OnSelectionChange"}

EVENT_PARAMS = {
    "OnMouseDown": "Sender: TObject; Button: TMouseButton; Shift: TShiftState; X, Y: Integer",
    "OnMouseUp": "Sender: TObject; Button: TMouseButton; Shift: TShiftState; X, Y: Integer",
    "OnMouseMove": "Sender: TObject; Shift: TShiftState; X, Y: Integer",
    "OnMouseWheel": "Sender: TObject; Shift: TShiftState; WheelDelta: Integer; MousePos: TPoint; "
                    "var Handled: Boolean",
    "OnKeyDown": "Sender: TObject; var Key: Word; Shift: TShiftState",
    "OnKeyUp": "Sender: TObject; var Key: Word; Shift: TShiftState",
    "OnKeyPress": "Sender: TObject; var Key: Char",
    "OnCloseQuery": "Sender: TObject; var CanClose: Boolean",
    "OnClose": "Sender: TObject; var Action: TCloseAction",
    "OnSelectCell": "Sender: TObject; ACol, ARow: Integer; var CanSelect: Boolean",
    "OnSetEditText": "Sender: TObject; ACol, ARow: Integer; const Value: string",
    "OnSelectionChange": "Sender: TObject; User: boolean",
}


def event_prop(ntype: str | None, event: str, lazarus: bool) -> str | None:
    """Delphi/Lazarus event property of a neutral event (None = not mapped)."""
    if ntype is not None:
        if lazarus and (ntype, event) in LCL_EVENT_PROPS_BY_TYPE:
            return LCL_EVENT_PROPS_BY_TYPE[(ntype, event)]
        if (ntype, event) in EVENT_PROPS_BY_TYPE:
            return EVENT_PROPS_BY_TYPE[(ntype, event)]
    return EVENT_PROPS.get(event)


def event_params(prop: str, lazarus: bool) -> str:
    if prop == "OnClose" and lazarus:
        return "Sender: TObject; var CloseAction: TCloseAction"
    return EVENT_PARAMS.get(prop, "Sender: TObject")


def color_in(v) -> str:
    if isinstance(v, str):
        return NAMED_COLORS.get(v.lower(), "")
    if isinstance(v, int) and 0 <= v <= 0xFFFFFF:
        return f"#{v & 0xFF:02X}{(v >> 8) & 0xFF:02X}{(v >> 16) & 0xFF:02X}"
    return ""


def color_out(c: str) -> str:
    c = (c or "").strip().upper()
    if not re.fullmatch(r"#[0-9A-F]{6}", c):
        return "clDefault"
    if c in _COLOR_NAMES:
        return _PROPER[_COLOR_NAMES[c]]
    r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    return f"$00{b:02X}{g:02X}{r:02X}"


_ALIGN_IN = {"altop": "Top", "albottom": "Bottom", "alleft": "Left", "alright": "Right", "alclient": "Fill"}
_ALIGN_OUT = {"None": "alNone", "Top": "alTop", "Bottom": "alBottom", "Left": "alLeft", "Right": "alRight",
              "Fill": "alClient"}
_TA_IN = {"tacenter": "Center", "tarightjustify": "Right"}
_TA_OUT = {"Left": "taLeftJustify", "Center": "taCenter", "Right": "taRightJustify"}


def font_size_in(obj: DObj, default: int) -> int:
    h = obj.value("Font.Height")
    if isinstance(h, int) and h != 0:
        return max(1, round(abs(h) * 72 / 96)) if h < 0 else max(1, round(h * 72 / 96 * 0.85))
    s = obj.value("Font.Size")
    if isinstance(s, int) and s > 0:
        return s
    return default


def _items_of(obj: DObj, prop: str) -> list[str]:
    v = obj.value(prop)
    if isinstance(v, list):
        return [x[1] for x in v if isinstance(x, tuple) and x[0] == "str"]
    return []


# =============================================================================== DFM -> neutral form

@dataclass
class LoadInfo:
    """What dfm_to_form found besides the neutral form (shown in the Output window)."""
    unknown: dict = field(default_factory=dict)       # component name -> class (kept verbatim, not designable)
    events: dict = field(default_factory=dict)        # component ("" = form) -> {neutral event: handler}
    font: tuple = ("Segoe UI", 9, False, False)


def _font_of(obj: DObj, parent_font: tuple) -> tuple:
    if obj.value("ParentFont") is True or obj.value("ParentFont") == "True":
        return parent_font
    name, size, bold, italic = parent_font
    has = any(p.name.lower().startswith("font.") for p in obj.props)
    if not has:
        return parent_font
    name = obj.value("Font.Name", name) or name
    size = font_size_in(obj, size)
    st = obj.value("Font.Style")
    if isinstance(st, list):
        bold = any(s.lower() == "fsbold" for s in st)
        italic = any(s.lower() == "fsitalic" for s in st)
    return str(name), int(size), bool(bold), bool(italic)


def _is_visual(obj: DObj) -> bool:
    # non-visual components (TActionList, TDataSource ...) store only their design-time Left/Top
    return any(obj.prop(k) is not None for k in ("Width", "Height", "Align", "ClientWidth"))


def dfm_to_form(root: DObj, lazarus: bool = False):
    """(Form, LoadInfo) for a parsed form file. Each control gets props["_dfm"] = the component
    name in the file (identity used by the writer even after a rename in the designer)."""
    from ..controls import CONTROL_TYPES, FORM_PROPS
    from ..model import Control, Form

    info = LoadInfo()
    form = Form()
    fp = form.props
    fp.update({k: p.default for k, p in FORM_PROPS.items()})
    fp["Name"] = root.name or root.cls.lstrip("T")
    fp["Text"] = str(root.value("Caption", ""))
    cw, ch = root.value("ClientWidth"), root.value("ClientHeight")
    w, h = root.value("Width"), root.value("Height")
    fp["Width"] = int(cw) if isinstance(cw, int) else (int(w) - 16 if isinstance(w, int) else 400)
    fp["Height"] = int(ch) if isinstance(ch, int) else (int(h) - 39 if isinstance(h, int) else 300)
    fp["BackColor"] = color_in(root.value("Color"))
    pos = str(root.value("Position", "") or "").lower()
    fp["StartPosition"] = "CenterScreen" if pos in ("poscreencenter", "podesktopcenter", "pomainformcenter",
                                                    "poownerformcenter", "poworkareacenter") else "Manual"
    bs = str(root.value("BorderStyle", "bsSizeable") or "").lower()
    fp["FormBorderStyle"] = "Sizable" if bs in ("bssizeable", "bssizetoolwin") else "FixedSingle"
    fp["TopMost"] = str(root.value("FormStyle", "")).lower() == "fsstayontop"
    fp["WindowState"] = "Maximized" if str(root.value("WindowState", "")).lower() == "wsmaximized" else "Normal"
    info.font = _font_of(root, ("Segoe UI", 9, False, False))
    _collect_events(root, "", None, info, lazarus)

    def add(obj: DObj, parent_name: str, font: tuple, tab_page: int | None = None):
        ntype = CLASS_MAP.get(obj.cls)
        cls_known = ntype is not None
        if ntype is None:
            if not _is_visual(obj):
                info.unknown[obj.name] = obj.cls
                return                         # kept verbatim (non-visual: TActionList, TDataSource ...)
            ntype = "Panel"
            info.unknown[obj.name] = obj.cls
        if not obj.name:
            return
        ct = CONTROL_TYPES[ntype]
        props = ct.default_props(obj.name)
        props["_dfm"] = obj.name
        props["Parent"] = parent_name
        if tab_page is not None:
            props["TabPage"] = tab_page
        if not ct.nonvisual:
            for k in ("Left", "Top", "Width", "Height"):
                v = obj.value(k)
                if isinstance(v, int):
                    props[k] = v
            cfont = _font_of(obj, font)
            props["FontName"], props["FontSize"], props["FontBold"], props["FontItalic"] = cfont
            props["Enabled"] = obj.value("Enabled", True) not in (False, "False")
            props["Visible"] = obj.value("Visible", True) not in (False, "False")
            props["BackColor"] = color_in(obj.value("Color"))
            props["ForeColor"] = color_in(obj.value("Font.Color"))
            props["ToolTip"] = str(obj.value("Hint", "") or "")
            to = obj.value("TabOrder")
            props["TabIndex"] = to if isinstance(to, int) else 0
            al = str(obj.value("Align", "") or "").lower()
            props["Dock"] = _ALIGN_IN.get(al, "None")
            an = obj.value("Anchors")
            if isinstance(an, list):
                edges = [e for e, k in (("Top", "aktop"), ("Bottom", "akbottom"), ("Left", "akleft"),
                                        ("Right", "akright")) if k in {a.lower() for a in an}]
                props["Anchor"] = ", ".join(edges) if edges else "None"
            if ct.has_text:
                if obj.cls in LINES_CLASSES:
                    props["Text"] = "\n".join(_items_of(obj, "Lines.Strings"))
                elif obj.cls in TEXT_CLASSES:
                    props["Text"] = str(obj.value("Text", "") or "")
                else:
                    props["Text"] = str(obj.value("Caption", "") or "")
        else:
            cfont = font
        if ntype == "TextBox":
            props["Multiline"] = obj.cls in LINES_CLASSES
            props["ReadOnly"] = obj.value("ReadOnly", False) in (True, "True")
            pc = obj.value("PasswordChar", "")
            props["PasswordChar"] = pc if isinstance(pc, str) and pc not in ("#0", "\x00") else ""
            ml = obj.value("MaxLength", 0)
            props["MaxLength"] = ml if isinstance(ml, int) else 0
        elif ntype in ("CheckBox", "RadioButton"):
            props["Checked"] = obj.value("Checked", False) in (True, "True") or \
                str(obj.value("State", "")).lower() == "cbchecked"
        elif ntype in ("ListBox", "ComboBox"):
            props["Items"] = ";".join(_items_of(obj, "Items.Strings"))
            if ntype == "ComboBox":
                props["DropDownStyle"] = "DropDownList" if str(obj.value("Style", "")).lower() == \
                    "csdropdownlist" else "DropDown"
        elif ntype == "Label":
            props["TextAlign"] = _TA_IN.get(str(obj.value("Alignment", "")).lower(), "Left")
        elif ntype in ("ProgressBar", "TrackBar"):
            props["Minimum"] = _int(obj.value("Min"), 0)
            props["Maximum"] = _int(obj.value("Max"), 100 if ntype == "ProgressBar" else 10)
            props["Value"] = _int(obj.value("Position"), 0)
        elif ntype == "NumericUpDown":
            if obj.cls == "TUpDown":
                props["Minimum"], props["Maximum"] = _int(obj.value("Min"), 0), _int(obj.value("Max"), 100)
                props["Value"] = _int(obj.value("Position"), 0)
            else:
                props["Minimum"], props["Maximum"] = _int(obj.value("MinValue"), 0), _int(obj.value("MaxValue"), 100)
                props["Value"] = _int(obj.value("Value"), 0)
        elif ntype == "Timer":
            props["Interval"] = _int(obj.value("Interval"), 1000)
            props["Enabled"] = obj.value("Enabled", True) not in (False, "False")
        elif ntype == "DataGridView":
            n = _int(obj.value("ColCount"), 5)
            props["Columns"] = ";".join(f"Col{i + 1}" for i in range(max(0, n)))
        elif ntype == "StatusBar":
            props["Text"] = str(obj.value("SimpleText", "") or "")
        elif ntype == "MenuStrip":
            props["Items"] = _menu_items(obj, info, lazarus)
        elif ntype in ("OpenFileDialog", "SaveFileDialog"):
            for k in ("Filter", "Title", "FileName"):
                if k in props and isinstance(obj.value(k), str):
                    props[k] = obj.value(k)
        if ntype == "TabControl":
            sheets = [c for c in obj.children if c.cls == "TTabSheet"]
            props["TabPages"] = ";".join(str(s.value("Caption", s.name) or s.name) for s in sheets)
            ap = str(obj.value("ActivePage", "") or "").lower()
            props["SelectedIndex"] = next((i for i, s in enumerate(sheets) if s.name.lower() == ap), 0)
        form.controls.append(Control(ntype, props))
        _collect_events(obj, obj.name, ntype, info, lazarus)
        if ntype == "MenuStrip":
            return
        if ntype == "TabControl":
            for i, s in enumerate(c for c in obj.children if c.cls == "TTabSheet"):
                for ch in s.children:
                    add(ch, obj.name, cfont, i)
            return
        if not cls_known or ct.container:
            for ch in obj.children:
                add(ch, obj.name, cfont)
        else:                                   # children of a non-container (rare): flatten to its parent
            for ch in obj.children:
                add(ch, parent_name, font)

    for ch in root.children:
        add(ch, "", info.font)
    form.extra["pascal_events"] = info.events
    return form, info


def _int(v, default: int) -> int:
    return v if isinstance(v, int) else default


def _menu_items(obj: DObj, info: LoadInfo, lazarus: bool) -> list:
    out = []
    for c in obj.children:
        if c.cls != "TMenuItem":
            continue
        it = {"Text": str(c.value("Caption", "") or ""), "Name": c.name}
        sub = _menu_items(c, info, lazarus)
        if sub:
            it["Items"] = sub
        h = c.value("OnClick")
        if isinstance(h, str):
            info.events.setdefault(c.name, {})["Click"] = h
        out.append(it)
    return out


def _collect_events(obj: DObj, owner: str, ntype: str | None, info: LoadInfo, lazarus: bool) -> None:
    from ..controls import CONTROL_TYPES, FORM_EVENTS
    events = FORM_EVENTS if ntype is None else CONTROL_TYPES[ntype].all_events()
    for ev in events:
        prop = event_prop(ntype, ev, lazarus)
        h = obj.value(prop) if prop else None
        if isinstance(h, str) and h:
            info.events.setdefault(owner, {})[ev] = h


# =============================================================================== writer

@dataclass(eq=False)
class GenNode:
    """A component created in the designer (written as a new object block)."""
    cls: str
    name: str
    props: list = field(default_factory=list)       # [(name, raw value or callable(indent) -> raw)]
    children: list = field(default_factory=list)    # GenNode | existing DObj (moved in)


class _Plan:
    def __init__(self):
        self.set: dict[int, dict[str, object]] = {}     # id(obj) -> {prop: raw | callable(indent)}
        self.delete_props: dict[int, set] = {}
        self.renames: dict[int, str] = {}
        self.removed: set[int] = set()                  # id(obj) removed from its parent
        self.add_children: dict[int, list] = {}         # id(obj) -> [GenNode | DObj]
        self.insert_before: dict[int, list] = {}        # id(existing sibling) -> [GenNode | DObj]
        self.notes: list[str] = []
        self.new_fields: list[tuple[str, str]] = []     # (name, class) for the .pas
        self.gone_fields: list[tuple[str, str]] = []
        self.renamed_fields: list[tuple[str, str]] = []
        self.used_classes: set[str] = set()

    def put(self, obj: DObj, prop: str, raw) -> None:
        self.set.setdefault(id(obj), {})[prop] = raw

    def drop(self, obj: DObj, prop: str) -> None:
        if obj.prop(prop) is not None:
            self.delete_props.setdefault(id(obj), set()).add(prop.lower())


def _reindent(block: str, old: str, new: str) -> str:
    if old == new:
        return block
    out = []
    for line in block.splitlines(keepends=True):
        if line.startswith(old):
            out.append(new + line[len(old):])
        elif line.strip():
            out.append(new + line.lstrip(" \t"))
        else:
            out.append(line)
    return "".join(out)


def _render_obj(text: str, obj: DObj, plan: _Plan, nl: str, indent: str | None = None) -> str:
    """Text of *obj* (header line .. end line) with the plan applied."""
    hdr = text[obj.line_start:obj.hdr_end]
    new_name = plan.renames.get(id(obj))
    if new_name and obj.name_span:
        a, b = obj.name_span[0] - obj.line_start, obj.name_span[1] - obj.line_start
        hdr = hdr[:a] + new_name + hdr[b:]
    if not hdr.endswith(("\n", "\r")):
        hdr += nl
    sets = dict(plan.set.get(id(obj), {}))
    lows = {k.lower(): k for k in sets}
    dels = plan.delete_props.get(id(obj), set())
    child_ind = obj.indent + "  "
    parts = [hdr]
    last_prop_idx = -1
    for idx, it in enumerate(obj.items):
        if isinstance(it, DProp):
            last_prop_idx = idx
    body: list[str] = []
    for idx, it in enumerate(obj.items):
        if isinstance(it, DProp):
            low = it.name.lower()
            if low in dels:
                continue
            seg = text[it.seg_start:it.seg_end]
            if low in lows:
                key = lows.pop(low)
                raw = sets[key]
                raw = raw(child_ind) if callable(raw) else raw
                a, b = it.vstart - it.seg_start, it.vend - it.seg_start
                seg = seg[:a] + raw + seg[b:]
            body.append(seg)
        else:
            for extra in plan.insert_before.get(id(it), []):     # new items placed before this one
                body.append(_render_extra(extra, child_ind, nl, plan, text))
            if id(it) in plan.removed:
                continue
            gap = text[it.seg_start:it.line_start]
            body.append(gap + _render_obj(text, it, plan, nl))
        if idx == last_prop_idx and lows:          # new properties after the last existing one
            body.append(_new_props(sets, lows, child_ind, nl))
            lows = {}
    if lows:                                       # object without properties
        body.insert(0, _new_props(sets, lows, child_ind, nl))
    for extra in plan.add_children.get(id(obj), []):
        body.append(_render_extra(extra, child_ind, nl, plan, text))
    parts.extend(body)
    end_seg = text[obj.end_seg_start:obj.end]
    if not end_seg.endswith(("\n", "\r")) and obj.parent is not None:
        end_seg += nl
    parts.append(end_seg)
    out = "".join(parts)
    if indent is not None and indent != obj.indent:
        out = _reindent(out, obj.indent, indent)
    return out


def _render_extra(extra, ind: str, nl: str, plan: _Plan, text: str) -> str:
    if isinstance(extra, DObj):
        return _reindent(_render_obj(text, extra, plan, nl), extra.indent, ind)
    return _gen_block(extra, ind, nl, plan, text)


def _new_props(sets: dict, lows: dict, ind: str, nl: str) -> str:
    out = []
    for low, key in lows.items():
        raw = sets[key]
        raw = raw(ind) if callable(raw) else raw
        out.append(f"{ind}{key} = {raw}{nl}")
    return "".join(out)


def _gen_block(node: GenNode, ind: str, nl: str, plan: _Plan, text: str) -> str:
    out = [f"{ind}object {node.name}: {node.cls}{nl}"]
    pind = ind + "  "
    for k, raw in node.props:
        raw = raw(pind) if callable(raw) else raw
        out.append(f"{pind}{k} = {raw}{nl}")
    for ch in node.children:
        if isinstance(ch, DObj):
            out.append(_reindent(_render_obj(text, ch, plan, nl), ch.indent, pind))
        else:
            out.append(_gen_block(ch, pind, nl, plan, text))
    out.append(f"{ind}end{nl}")
    return "".join(out)


class FormWriter:
    """Apply the designer's changes (base form -> new form) to the form file text."""

    def __init__(self, text: str, lazarus: bool, code: str = ""):
        self.text = text
        self.lazarus = lazarus
        self.root = parse_dfm(text)
        self.nl = "\r\n" if "\r\n" in text else "\n"
        self.code = code
        self.plan = _Plan()
        self.form_font = _font_of(self.root, ("Segoe UI", 9, False, False))

    # ------------------------------------------------------------- helpers
    def s(self, v: str) -> str:
        return pascal_string(v, self.lazarus)

    def obj(self, name: str) -> DObj | None:
        return self.root.find(name) if name else None

    def apply(self, base: dict, new: dict, handler_exists=None) -> str:
        """*base* / *new*: Form.to_dict() of the form as loaded and as edited.
        *handler_exists(name)*: True when the unit has a method with that name (event binding)."""
        plan = self.plan
        self._form_props(base.get("props", {}), new.get("props", {}))
        bctrls = {c["props"].get("_dfm"): c for c in base.get("controls", []) if c["props"].get("_dfm")}
        nctrls = new.get("controls", [])
        claimed: set[str] = set()
        live: list[tuple[dict, DObj | None]] = []
        for c in nctrls:
            key = c["props"].get("_dfm")
            o = self.obj(key) if key and key not in claimed and key in bctrls else None
            if o is not None:
                claimed.add(key)
            live.append((c, o))
        # deleted components
        for key, bc in bctrls.items():
            if key not in claimed:
                o = self.obj(key)
                if o is not None and o.parent is not None:
                    plan.removed.add(id(o))
                    plan.gone_fields.append((o.name, o.cls))
                    for sub in o.walk():
                        if sub is not o and sub.name:
                            plan.gone_fields.append((sub.name, sub.cls))
        names = {c["props"]["Name"]: (c, o) for c, o in live}
        gens: dict[str, GenNode] = {}
        # changed / renamed existing components
        for c, o in live:
            if o is None:
                continue
            bc = bctrls[c["props"]["_dfm"]]
            self._control(bc, c, o)
        # new components (created in order: a container before its children)
        for c, o in live:
            if o is None:
                g = self._gen(c)
                if g is not None:
                    gens[c["props"]["Name"]] = g
        # parents: existing moved / new placed
        for c, o in live:
            p = c["props"]
            target = self._target_parent(p, names, gens)
            if target is None:
                continue
            node = o if o is not None else gens.get(p["Name"])
            if node is None:
                continue
            if o is not None:
                bc = bctrls[p["_dfm"]]["props"]
                if o.parent is target or (bc.get("Parent", "") == p.get("Parent", "") and
                                          bc.get("TabPage") == p.get("TabPage")):
                    continue
                plan.removed.add(id(o))
            self._attach(target, node)
        # event bindings (handler in the unit, no OnXxx yet)
        if handler_exists is not None:
            self._events(new, live, gens, handler_exists)
        out = self.text[:self.root.line_start] + _render_obj(self.text, self.root, plan, self.nl) + \
            self.text[self.root.end:]
        return out

    def _attach(self, target, node) -> None:
        if isinstance(target, GenNode):
            target.children.append(node)
        else:
            self.plan.add_children.setdefault(id(target), []).append(node)

    def _target_parent(self, p: dict, names: dict, gens: dict):
        """DObj / GenNode the control must live in (None = leave where it is)."""
        par = p.get("Parent", "") or ""
        if not par:
            return self.root
        pc, po = names.get(par, (None, None))
        if pc is None:
            return self.root
        if pc.get("type") == "TabControl":
            page = int(p.get("TabPage", 0) or 0)
            sheets = self._sheets(pc, po, gens)
            return sheets[min(max(page, 0), len(sheets) - 1)] if sheets else (po or gens.get(par))
        return po if po is not None else gens.get(par)

    def _sheets(self, pc: dict, po: DObj | None, gens: dict) -> list:
        key = pc["props"]["Name"]
        cache = getattr(self, "_sheet_cache", None)
        if cache is None:
            cache = self._sheet_cache = {}
        if key in cache:
            return cache[key]
        if po is not None:
            sheets = [c for c in po.children if c.cls == "TTabSheet" and id(c) not in self.plan.removed]
        else:
            sheets = []
        g = gens.get(key)
        sheets = sheets + [ch for ch in (g.children if g else []) if isinstance(ch, GenNode)
                           and ch.cls == "TTabSheet"]
        sheets += self.plan.add_children.get(id(po), []) if po is not None else []
        sheets = [s for s in sheets if (isinstance(s, DObj) and s.cls == "TTabSheet") or
                  (isinstance(s, GenNode) and s.cls == "TTabSheet")]
        cache[key] = sheets
        return sheets

    # ------------------------------------------------------------- form level
    def _form_props(self, b: dict, n: dict) -> None:
        r, plan = self.root, self.plan
        if b.get("Name") != n.get("Name"):
            plan.notes.append("renaming the form itself is not written (rename it in Delphi/Lazarus)")
        if b.get("Text") != n.get("Text"):
            plan.put(r, "Caption", self.s(str(n.get("Text", ""))))
        for nk, dk, outer in (("Width", "ClientWidth", "Width"), ("Height", "ClientHeight", "Height")):
            if b.get(nk) != n.get(nk):
                if r.prop(dk) is not None or r.prop(outer) is None:
                    plan.put(r, dk, str(int(n[nk])))
                    if r.prop(outer) is not None and isinstance(r.value(outer), int):
                        delta = int(n[nk]) - int(b.get(nk, n[nk]))
                        plan.put(r, outer, str(int(r.value(outer)) + delta))
                else:
                    plan.put(r, outer, str(int(n[nk]) + (16 if nk == "Width" else 39)))
        if b.get("BackColor") != n.get("BackColor"):
            plan.put(r, "Color", color_out(n.get("BackColor", "")))
        if b.get("StartPosition") != n.get("StartPosition"):
            plan.put(r, "Position", "poScreenCenter" if n.get("StartPosition") == "CenterScreen" else "poDesigned")
        if b.get("FormBorderStyle") != n.get("FormBorderStyle"):
            plan.put(r, "BorderStyle", "bsSizeable" if n.get("FormBorderStyle") == "Sizable" else "bsSingle")
        if b.get("TopMost") != n.get("TopMost"):
            plan.put(r, "FormStyle", "fsStayOnTop" if n.get("TopMost") else "fsNormal")
        if b.get("WindowState") != n.get("WindowState"):
            plan.put(r, "WindowState", "wsMaximized" if n.get("WindowState") == "Maximized" else "wsNormal")
        for k in n:
            if k in ("Name", "Text", "Width", "Height", "BackColor", "StartPosition", "FormBorderStyle",
                     "TopMost", "WindowState"):
                continue
            if b.get(k) != n.get(k):
                plan.notes.append(f"form property {k} has no Delphi/Lazarus equivalent here (not written)")

    # ------------------------------------------------------------- controls
    def _control(self, bc: dict, nc: dict, o: DObj) -> None:
        plan = self.plan
        b, n = bc["props"], nc["props"]
        ntype = nc["type"]
        if b.get("Name") != n.get("Name"):
            plan.renames[id(o)] = n["Name"]
            plan.renamed_fields.append((b["Name"], n["Name"]))
        if bc["type"] != ntype:
            plan.notes.append(f"{n['Name']}: the control type cannot change in place (kept {o.cls})")
            return
        for k in sorted(set(b) | set(n)):
            if k in ("Name", "_dfm", "Parent", "TabPage") or b.get(k) == n.get(k):
                continue
            if not self._set_prop(o, ntype, k, n.get(k), n):
                plan.notes.append(f"{n['Name']}.{k} is not written (no {o.cls} equivalent)")
        if ntype == "MenuStrip" and b.get("Items") != n.get("Items"):
            self._menu(o, n.get("Items") or [])
        if ntype == "TabControl" and b.get("TabPages") != n.get("TabPages"):
            self._tabs(o, n)

    def _set_prop(self, o, ntype: str, k: str, v, props: dict) -> bool:
        plan, cls = self.plan, (o.cls if isinstance(o, DObj) else o.cls)
        put = (lambda name, raw: plan.put(o, name, raw)) if isinstance(o, DObj) else \
            (lambda name, raw: _gen_put(o, name, raw))
        if k in ("Left", "Top", "Width", "Height"):
            put(k, str(int(v)))
        elif k == "Text":
            if cls in LINES_CLASSES:
                lines = str(v).split("\n")
                put("Lines.Strings", lambda ind, ls=lines: string_list(ls, ind, self.nl, self.lazarus))
            elif cls in TEXT_CLASSES:
                put("Text", self.s(str(v)))
            elif cls == "TStatusBar":
                put("SimpleText", self.s(str(v)))
                put("SimplePanel", "True")
            elif cls in CAPTION_CLASSES or ntype in ("Button", "Label", "CheckBox", "RadioButton", "GroupBox"):
                put("Caption", self.s(str(v)))
            else:
                return False
        elif k == "BackColor":
            put("Color", color_out(v))
        elif k in ("ForeColor", "FontName", "FontSize", "FontBold", "FontItalic"):
            if k == "ForeColor":
                put("Font.Color", color_out(v))
            elif k == "FontName":
                put("Font.Name", self.s(str(v)))
            elif k == "FontSize":
                put("Font.Height", str(-round(int(v) * 96 / 72)))
                if isinstance(o, DObj) and o.prop("Font.Size") is not None:
                    plan.drop(o, "Font.Size")
            else:
                st = [s for s, on in (("fsBold", props.get("FontBold")), ("fsItalic", props.get("FontItalic")))
                      if on]
                put("Font.Style", "[" + ", ".join(st) + "]")
            put("ParentFont", "False")
        elif k in ("Enabled", "Visible"):
            put(k, "True" if v else "False")
        elif k == "ToolTip":
            put("Hint", self.s(str(v)))
            put("ShowHint", "True" if v else "False")
        elif k == "TabIndex":
            put("TabOrder", str(int(v)))
        elif k == "Dock":
            put("Align", _ALIGN_OUT.get(str(v), "alNone"))
        elif k == "Anchor":
            from ..controls import parse_anchor
            edges = parse_anchor(v)
            put("Anchors", "[" + ", ".join(a for e, a in (("Left", "akLeft"), ("Top", "akTop"),
                                                           ("Right", "akRight"), ("Bottom", "akBottom"))
                                            if e in edges) + "]")
        elif k == "Checked":
            if isinstance(o, DObj) and o.prop("State") is not None:
                put("State", "cbChecked" if v else "cbUnchecked")
            else:
                put("Checked", "True" if v else "False")
        elif k == "Items" and ntype in ("ListBox", "ComboBox"):
            items = [x.strip() for x in str(v).split(";") if x.strip()]
            put("Items.Strings", lambda ind, it=items: string_list(it, ind, self.nl, self.lazarus))
        elif k == "DropDownStyle":
            put("Style", "csDropDownList" if v == "DropDownList" else "csDropDown")
        elif k == "TextAlign" and ntype == "Label":
            put("Alignment", _TA_OUT.get(str(v), "taLeftJustify"))
        elif k == "ReadOnly":
            put("ReadOnly", "True" if v else "False")
        elif k == "PasswordChar":
            put("PasswordChar", self.s(str(v)[:1]) if v else "#0")
        elif k == "MaxLength":
            put("MaxLength", str(int(v or 0)))
        elif k in ("Minimum", "Maximum", "Value"):
            if cls == "TSpinEdit":
                put({"Minimum": "MinValue", "Maximum": "MaxValue", "Value": "Value"}[k], str(int(v)))
            else:
                put({"Minimum": "Min", "Maximum": "Max", "Value": "Position"}[k], str(int(v)))
        elif k == "Interval":
            put("Interval", str(int(v)))
        elif k == "Columns" and ntype == "DataGridView":
            put("ColCount", str(len([x for x in str(v).split(";") if x.strip()])))
        elif k in ("Filter", "Title", "FileName"):
            put(k, self.s(str(v)))
        elif k in ("Items", "TabPages", "SelectedIndex") and ntype in ("MenuStrip", "TabControl"):
            if k == "SelectedIndex" and isinstance(o, DObj):
                sheets = [c for c in o.children if c.cls == "TTabSheet"]
                if 0 <= int(v) < len(sheets):
                    put("ActivePage", sheets[int(v)].name)
            return True
        else:
            return False
        return True

    def _menu(self, menu: DObj, items: list) -> None:
        """Diff the menu tree by item Name."""
        plan = self.plan
        existing = {o.name.lower(): o for o in menu.walk() if o is not menu and o.cls == "TMenuItem" and o.name}
        seen: set[str] = set()

        def place(parent, node, rest: list) -> None:
            """New item: before the next existing sibling (menu order matters), else at the end."""
            if isinstance(parent, DObj):
                for nxt in rest:
                    o2 = existing.get(str(nxt.get("Name") or "").lower())
                    if o2 is not None and o2.parent is parent and id(o2) not in plan.removed:
                        plan.insert_before.setdefault(id(o2), []).append(node)
                        return
            self._attach(parent, node)

        def walk(lst: list, parent):
            for i, it in enumerate(lst):
                name = str(it.get("Name") or "")
                o = existing.get(name.lower()) if name else None
                if o is not None and name.lower() not in seen:
                    seen.add(name.lower())
                    cap = str(it.get("Text", ""))
                    if str(o.value("Caption", "")) != cap:
                        plan.put(o, "Caption", self.s(cap))
                    if o.parent is not parent and not (isinstance(parent, DObj) and o.parent is parent):
                        plan.removed.add(id(o))
                        self._attach(parent, o)
                    walk(it.get("Items") or [], o)
                else:
                    g = GenNode("TMenuItem", name or self._fresh("MenuItem"),
                                [("Caption", self.s(str(it.get("Text", ""))))])
                    plan.new_fields.append((g.name, "TMenuItem"))
                    plan.used_classes.add("TMenuItem")
                    place(parent, g, lst[i + 1:])
                    walk(it.get("Items") or [], g)
        walk(items, menu)
        for low, o in existing.items():
            if low not in seen and not any(id(a) in plan.removed for a in _ancestors(o)):
                plan.removed.add(id(o))
                plan.gone_fields.append((o.name, o.cls))

    def _tabs(self, pc: DObj, n: dict) -> None:
        plan = self.plan
        caps = [x.strip() for x in str(n.get("TabPages", "")).split(";") if x.strip()]
        sheets = [c for c in pc.children if c.cls == "TTabSheet"]
        for i, cap in enumerate(caps):
            if i < len(sheets):
                if str(sheets[i].value("Caption", "")) != cap:
                    plan.put(sheets[i], "Caption", self.s(cap))
            else:
                g = GenNode("TTabSheet", self._fresh("TabSheet"), [("Caption", self.s(cap))])
                plan.new_fields.append((g.name, "TTabSheet"))
                plan.used_classes.add("TTabSheet")
                self._attach(pc, g)
        for s in sheets[len(caps):]:
            if s.children:
                plan.notes.append(f"tab sheet {s.name} still has components: not removed")
                continue
            plan.removed.add(id(s))
            plan.gone_fields.append((s.name, "TTabSheet"))

    def _fresh(self, base: str) -> str:
        taken = {o.name.lower() for o in self.root.walk()} | {n.lower() for n, _ in self.plan.new_fields}
        i = 1
        while f"{base}{i}".lower() in taken:
            i += 1
        return f"{base}{i}"

    def _gen(self, c: dict) -> GenNode | None:
        ntype, p = c["type"], c["props"]
        cls = NEW_CLASS.get(ntype)
        if ntype == "TextBox" and p.get("Multiline"):
            cls = "TMemo"
        if ntype == "FolderBrowserDialog" and not self.lazarus:
            cls = "TFileOpenDialog"
        if cls is None:
            self.plan.notes.append(f"{p.get('Name')}: {ntype} has no Delphi/Lazarus class - not written")
            return None
        g = GenNode(cls, p["Name"])
        from ..controls import CONTROL_TYPES
        ct = CONTROL_TYPES[ntype]
        defaults = ct.default_props(p["Name"])
        if not ct.nonvisual:
            for k in ("Left", "Top", "Width", "Height"):
                g.props.append((k, str(int(p.get(k, 0)))))
        order = ["Text", "Items", "Checked", "ReadOnly", "PasswordChar", "MaxLength", "TextAlign", "DropDownStyle",
                 "Minimum", "Maximum", "Value", "Interval", "Enabled", "Visible", "BackColor", "ForeColor",
                 "FontName", "FontSize", "FontBold", "FontItalic", "ToolTip", "Dock", "Anchor", "Columns",
                 "Filter", "Title"]
        for k in order:
            if k not in p:
                continue
            v = p[k]
            if k == "Text" and ct.has_text:
                if cls not in LINES_CLASSES or v:
                    self._set_prop(g, ntype, k, v, p)
                continue
            if k in ("FontName", "FontSize", "FontBold", "FontItalic"):
                idx = ("FontName", "FontSize", "FontBold", "FontItalic").index(k)
                if v == self.form_font[idx]:
                    continue
            elif ntype == "Timer" and k == "Enabled":
                if not v:
                    g.props.append(("Enabled", "False"))      # a VCL/LCL TTimer is enabled by default
                continue
            elif ntype == "Timer" and k == "Interval":
                if int(v) != 1000:
                    g.props.append(("Interval", str(int(v))))
                continue
            elif v == defaults.get(k):
                continue
            self._set_prop(g, ntype, k, v, p)
        if ntype == "MenuStrip":
            for it in p.get("Items") or []:
                self._gen_menu(g, it)
        if ntype == "TabControl":
            for cap in [x.strip() for x in str(p.get("TabPages", "")).split(";") if x.strip()]:
                s = GenNode("TTabSheet", self._fresh("TabSheet"), [("Caption", self.s(cap))])
                self.plan.new_fields.append((s.name, "TTabSheet"))
                self.plan.used_classes.add("TTabSheet")
                g.children.append(s)
        # graphic controls (TLabel, TImage ...) are not TWinControls: they have no TabOrder
        if not ct.nonvisual and "TabIndex" in p and cls not in GRAPHIC_CLASSES:
            g.props.append(("TabOrder", str(int(p.get("TabIndex") or 0))))
        self.plan.new_fields.append((g.name, cls))
        self.plan.used_classes.add(cls)
        return g

    def _gen_menu(self, parent: GenNode, it: dict) -> None:
        g = GenNode("TMenuItem", str(it.get("Name") or self._fresh("MenuItem")),
                    [("Caption", self.s(str(it.get("Text", ""))))])
        self.plan.new_fields.append((g.name, "TMenuItem"))
        self.plan.used_classes.add("TMenuItem")
        parent.children.append(g)
        for sub in it.get("Items") or []:
            self._gen_menu(g, sub)

    # ------------------------------------------------------------- events
    def _events(self, new: dict, live, gens, handler_exists) -> None:
        from ..controls import CONTROL_TYPES, FORM_EVENTS, menu_leaves
        evmap = (new.get("extra") or {}).get("pascal_events") or new.get("pascal_events") or {}

        def bind(target, owner: str, ntype: str | None, events):
            for ev in events:
                prop = event_prop(ntype, ev, self.lazarus)
                if not prop:
                    continue
                handler = (evmap.get(owner) or {}).get(ev) or default_handler(owner, ev, ntype, self.lazarus)
                if not handler_exists(handler):
                    continue
                if isinstance(target, DObj):
                    if target.prop(prop) is None and prop not in self.plan.set.get(id(target), {}):
                        self.plan.put(target, prop, handler)
                elif all(k != prop for k, _ in target.props):
                    target.props.append((prop, handler))
        bind(self.root, "", None, FORM_EVENTS)
        for c, o in live:
            p = c["props"]
            node = o if o is not None else gens.get(p["Name"])
            if node is None:
                continue
            ntype = c["type"]
            if ntype == "MenuStrip":
                for leaf in menu_leaves(p.get("Items") or []):
                    nm = leaf.get("Name")
                    if not nm:
                        continue
                    t = self.obj(nm) if isinstance(node, DObj) else None
                    if t is None:
                        t = _find_gen(node, nm) if isinstance(node, GenNode) else self._find_new_menu(node, nm)
                    if t is not None:
                        bind(t, nm, "MenuItem", ["Click"])
                continue
            bind(node, p["Name"], ntype, CONTROL_TYPES[ntype].all_events())

    def _find_new_menu(self, menu: DObj, name: str):
        for lst in list(self.plan.add_children.values()) + list(self.plan.insert_before.values()):
            for g in lst:
                if isinstance(g, GenNode):
                    hit = _find_gen(g, name)
                    if hit is not None:
                        return hit
        return None


def _find_gen(g: GenNode, name: str):
    if g.name.lower() == name.lower():
        return g
    for ch in g.children:
        if isinstance(ch, GenNode):
            hit = _find_gen(ch, name)
            if hit is not None:
                return hit
    return None


def _gen_put(g: GenNode, name: str, raw) -> None:
    for i, (k, _) in enumerate(g.props):
        if k.lower() == name.lower():
            g.props[i] = (k, raw)
            return
    g.props.append((name, raw))


def _ancestors(o: DObj):
    p = o.parent
    while p is not None:
        yield p
        p = p.parent


def default_handler(owner: str, event: str, ntype: str | None, lazarus: bool) -> str:
    """Delphi naming: Button1Click, Edit1Change, FormCreate (the form is always "Form")."""
    if ntype == "MenuItem" or ntype in ("MenuStrip", "ToolStrip"):
        return f"{owner}Click"
    prop = event_prop(ntype, event, lazarus) or ("On" + event)
    return f"{owner or 'Form'}{prop[2:]}"


# =============================================================================== binary .dfm

def is_binary_dfm(data: bytes) -> bool:
    return data[:4] == b"TPF0" or (data[:1] == b"\xff" and b"TPF0" in data[:64])


def binary_dfm_to_text(data: bytes) -> str:
    """Convert a binary form file (TPF0 stream, optionally with a resource header) to text."""
    i = data.find(b"TPF0")
    if i < 0:
        raise DfmError("not a binary form file (TPF0 signature missing)")
    r = _BinReader(data, i + 4)
    out: list[str] = []
    r.read_object(out, "")
    return "\r\n".join(out) + "\r\n"


class _BinReader:
    def __init__(self, data: bytes, pos: int):
        self.d, self.p = data, pos

    def byte(self) -> int:
        b = self.d[self.p]
        self.p += 1
        return b

    def take(self, n: int) -> bytes:
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def sstr(self) -> str:
        n = self.byte()
        return self.take(n).decode("cp1252", errors="replace")

    def read_object(self, out: list[str], ind: str) -> None:
        flags = 0
        b = self.d[self.p]
        if b & 0xF0 == 0xF0:
            flags = self.byte() & 0x0F
            if flags & 2:
                self.read_value(ind)            # child position index
        cls, name = self.sstr(), self.sstr()
        kw = "inherited" if flags & 1 else ("inline" if flags & 4 else "object")
        out.append(f"{ind}{kw} {name}: {cls}" if name else f"{ind}{kw} {cls}")
        while self.d[self.p] != 0:
            pname = self.sstr()
            out.append(f"{ind}  {pname} = " + self.read_value(ind + "  "))
        self.p += 1
        while self.d[self.p] != 0:
            self.read_object(out, ind + "  ")
        self.p += 1
        out.append(f"{ind}end")

    def read_value(self, ind: str) -> str:
        t = self.byte()
        if t == 0:
            return "nil"
        if t == 1:                                       # list
            vals = []
            while self.d[self.p] != 0:
                vals.append(self.read_value(ind + "  "))
            self.p += 1
            return "(" + "".join("\r\n" + ind + "  " + v for v in vals) + ")"
        if t == 2:
            return str(struct.unpack("<b", self.take(1))[0])
        if t == 3:
            return str(struct.unpack("<h", self.take(2))[0])
        if t == 4:
            return str(struct.unpack("<i", self.take(4))[0])
        if t == 5:
            return _fmt_float(_extended(self.take(10)))
        if t in (6, 7):
            s = self.sstr()
            return pascal_string(s, False) if t == 6 else s
        if t == 8:
            return "False"
        if t == 9:
            return "True"
        if t == 10:
            n = struct.unpack("<i", self.take(4))[0]
            hx = self.take(n).hex().upper()
            rows = [hx[k:k + 64] for k in range(0, len(hx), 64)] or [""]
            return "{" + "".join("\r\n" + ind + "  " + row for row in rows) + "}"
        if t == 11:
            items = []
            while True:
                s = self.sstr()
                if not s:
                    break
                items.append(s)
            return "[" + ", ".join(items) + "]"
        if t == 12:
            n = struct.unpack("<i", self.take(4))[0]
            return pascal_string(self.take(n).decode("cp1252", errors="replace"), False)
        if t == 13:
            return "nil"
        if t == 14:                                      # collection
            items = []
            while self.d[self.p] != 0:
                if self.d[self.p] in (2, 3, 4):
                    self.read_value(ind)
                if self.d[self.p] == 1:
                    self.p += 1
                lines = []
                while self.d[self.p] != 0:
                    pname = self.sstr()
                    lines.append(f"{ind}    {pname} = " + self.read_value(ind + "    "))
                self.p += 1
                items.append("\r\n".join([f"{ind}  item"] + lines + [f"{ind}  end"]))
            self.p += 1
            return "<" + "".join("\r\n" + it for it in items) + ">"
        if t == 15:
            return _fmt_float(struct.unpack("<f", self.take(4))[0])
        if t == 16:
            return _fmt_float(struct.unpack("<q", self.take(8))[0] / 10000.0)
        if t in (17, 21):
            return _fmt_float(struct.unpack("<d", self.take(8))[0])
        if t == 18:
            n = struct.unpack("<i", self.take(4))[0]
            return pascal_string(self.take(n * 2).decode("utf-16-le", errors="replace"), False)
        if t == 19:
            return str(struct.unpack("<q", self.take(8))[0])
        if t == 20:
            n = struct.unpack("<i", self.take(4))[0]
            return pascal_string(self.take(n).decode("utf-8", errors="replace"), False)
        raise DfmError(f"unknown binary value type {t} at offset {self.p - 1}")


def _extended(b: bytes) -> float:
    mant = int.from_bytes(b[:8], "little")
    se = int.from_bytes(b[8:10], "little")
    sign = -1.0 if se & 0x8000 else 1.0
    exp = se & 0x7FFF
    if exp == 0 and mant == 0:
        return 0.0
    return sign * mant / (1 << 63) * 2.0 ** (exp - 16383)


def _fmt_float(x: float) -> str:
    s = repr(float(x))
    return s if "." in s or "e" in s else s + ".0"


# =============================================================================== Pascal source helpers

def _class_block(code: str, cls: str):
    """(start line, end line, first-section end line) of `TForm1 = class(...)` in *code* (0-based)."""
    lines = code.split("\n")
    rx = re.compile(rf"^\s*{re.escape(cls)}\s*=\s*class\b", re.I)
    start = next((i for i, ln in enumerate(lines) if rx.match(ln)), -1)
    if start < 0:
        return None
    sect_end = None
    for j in range(start + 1, len(lines)):
        s = lines[j].strip().lower()
        if re.match(r"^(private|protected|public|published|strict\s+private|strict\s+protected)\b", s) \
                and sect_end is None:
            sect_end = j
        if re.match(r"^end\s*;", s):
            return start, j, sect_end if sect_end is not None else j
    return None


def form_class_of(code: str, root_cls: str = "") -> str:
    if root_cls:
        return root_cls
    m = re.search(r"^\s*(T\w+)\s*=\s*class\s*\(\s*TForm\s*\)", code, re.I | re.M)
    return m.group(1) if m else "TForm1"


def find_method(code: str, cls: str, name: str) -> int:
    """0-based line of ``procedure TForm1.Name`` in the implementation (or -1)."""
    rx = re.compile(rf"^\s*(?:class\s+)?(?:procedure|function)\s+{re.escape(cls)}\s*\.\s*{re.escape(name)}\b",
                    re.I)
    impl = False
    for i, ln in enumerate(code.split("\n")):
        if re.match(r"^\s*implementation\b", ln, re.I):
            impl = True
        if impl and rx.match(ln):
            return i
    return -1


def has_method(code: str, name: str) -> bool:
    return re.search(rf"^\s*(?:procedure|function)\s+T\w+\s*\.\s*{re.escape(name)}\b", code, re.I | re.M) \
        is not None


def add_method(code: str, cls: str, name: str, params: str) -> tuple[str, int]:
    """Declare ``procedure Name(params);`` in the first section of *cls* and implement it before the
    final ``end.`` (or before initialization/finalization). Returns (code, 1-based body line)."""
    nl = "\r\n" if "\r\n" in code else "\n"
    work = code.replace("\r\n", "\n")
    lines = work.split("\n")
    blk = _class_block(work, cls)
    decl = f"    procedure {name}({params});"
    if blk is not None:
        start, end, sect = blk
        ins = sect
        # keep the declaration after the last field / method of the first section
        k = sect - 1
        while k > start and not lines[k].strip():
            k -= 1
        ins = k + 1
        ind = re.match(r"^\s*", lines[k]).group(0) if k > start else "    "
        decl = f"{ind or '    '}procedure {name}({params});"
        lines.insert(ins, decl)
    body = [f"procedure {cls}.{name}({params});", "begin", "  ", "end;", ""]
    endk = None
    for i in range(len(lines) - 1, -1, -1):
        if re.match(r"^\s*end\s*\.", lines[i], re.I):
            endk = i
            break
    if endk is None:
        base = len(lines) + 1
        lines += [""] + body
        body_line = base + body.index("  ") + 1
    else:
        ins = endk
        for i in range(endk - 1, -1, -1):
            if re.match(r"^\s*(initialization|finalization)\b", lines[i], re.I):
                ins = i
            elif re.match(r"^\s*implementation\b", lines[i], re.I):
                break
        if ins > 0 and lines[ins - 1].strip():
            body = [""] + body
        lines[ins:ins] = body
        body_line = ins + body.index("  ") + 1
    return nl.join(lines), body_line


def add_fields(code: str, cls: str, fields: list[tuple[str, str]]) -> str:
    if not fields:
        return code
    nl = "\r\n" if "\r\n" in code else "\n"
    lines = code.replace("\r\n", "\n").split("\n")
    blk = _class_block("\n".join(lines), cls)
    if blk is None:
        return code
    start, _end, sect = blk
    field_rx = re.compile(r"^\s*\w+\s*:\s*[\w.]+\s*;")
    last = start
    for j in range(start + 1, sect):
        if field_rx.match(lines[j]):
            last = j
        elif re.match(r"^\s*(procedure|function|constructor|destructor|property)\b", lines[j], re.I):
            break
    ind = re.match(r"^\s*", lines[last]).group(0) if last > start else "    "
    existing = {m.group(1).lower() for m in (re.match(r"^\s*(\w+)\s*:", ln) for ln in lines[start:sect]) if m}
    new = [f"{ind}{n}: {c};" for n, c in fields if n.lower() not in existing]
    lines[last + 1:last + 1] = new
    return nl.join(lines)


def remove_fields(code: str, cls: str, fields: list[tuple[str, str]]) -> str:
    if not fields:
        return code
    nl = "\r\n" if "\r\n" in code else "\n"
    lines = code.replace("\r\n", "\n").split("\n")
    blk = _class_block("\n".join(lines), cls)
    if blk is None:
        return code
    start, _end, sect = blk
    drop = set()
    for n, c in fields:
        rx = re.compile(rf"^\s*{re.escape(n)}\s*:\s*{re.escape(c)}\s*;\s*$", re.I)
        for j in range(start + 1, sect):
            if rx.match(lines[j]):
                drop.add(j)
    return nl.join(ln for j, ln in enumerate(lines) if j not in drop)


def add_uses(code: str, units: list[str]) -> str:
    """Add units to the interface ``uses`` clause (skips units already listed)."""
    if not units:
        return code
    m_int = re.search(r"^\s*interface\b", code, re.I | re.M)
    pos = m_int.end() if m_int else 0
    m = re.compile(r"\buses\b(.*?);", re.I | re.S).search(code, pos)
    if not m:
        return code
    have = {u.strip().lower() for u in re.sub(r"\{.*?\}|//[^\n]*", "", m.group(1)).replace("\n", " ").split(",")}
    add = [u for u in units if u.lower() not in have]
    if not add:
        return code
    return code[:m.end() - 1] + ", " + ", ".join(add) + code[m.end() - 1:]


def units_for_classes(code: str, classes: set[str], lazarus: bool) -> list[str]:
    vcl_ns = not lazarus and re.search(r"\bVcl\.\w+", code) is not None
    out = []
    for c in sorted(classes):
        u = CLASS_UNIT.get(c)
        if not u:
            continue
        if vcl_ns:
            u = VCL_NAMESPACE.get(u, u)
        if u not in out:
            out.append(u)
    return out


def deep(d):
    return copy.deepcopy(d)
