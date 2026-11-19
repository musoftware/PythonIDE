"""VB6-compatible BASIC language plugin (runs on the bundled interpreter)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ..controls import CONTROL_TYPES, FORM_EVENTS, menu_leaves
from ..model import Form
from .base import Completion, LanguagePlugin, RunSpec

IDE_ROOT = Path(__file__).resolve().parent.parent.parent

VB_CLASS = {"Button": "CommandButton", "Label": "Label", "TextBox": "TextBox", "CheckBox": "CheckBox",
            "RadioButton": "OptionButton", "ListBox": "ListBox", "ComboBox": "ComboBox",
            "PictureBox": "PictureBox", "ProgressBar": "ProgressBar", "NumericUpDown": "UpDown",
            "TrackBar": "Slider", "Panel": "PictureBox", "GroupBox": "Frame", "Timer": "Timer"}

COMMON_MEMBERS = ["Name", "Left", "Top", "Width", "Height", "Enabled", "Visible", "BackColor", "ForeColor",
                  "FontName", "FontSize", "FontBold", "ToolTipText", "Tag", "SetFocus", "Refresh", "Move", "ZOrder"]
MEMBERS = {
    "Button": ["Caption"], "Label": ["Caption", "Alignment"], "GroupBox": ["Caption"],
    "TextBox": ["Text", "Locked", "MaxLength", "PasswordChar", "SelStart", "SelLength", "SelText", "MultiLine"],
    "CheckBox": ["Caption", "Value"], "RadioButton": ["Caption", "Value"],
    "ListBox": ["AddItem", "RemoveItem", "Clear", "List", "ListCount", "ListIndex", "Text", "NewIndex"],
    "ComboBox": ["AddItem", "RemoveItem", "Clear", "List", "ListCount", "ListIndex", "Text"],
    "ProgressBar": ["Value", "Min", "Max"], "NumericUpDown": ["Value", "Min", "Max"],
    "TrackBar": ["Value", "Min", "Max"], "PictureBox": ["Picture"], "Panel": [],
    "Timer": ["Interval", "Enabled"], "Form": ["Caption", "Show", "Hide", "Width", "Height", "Left", "Top",
                                               "BackColor", "WindowState", "Visible", "Controls", "Refresh"],
}
SIGNATURES = {
    "msgbox": "MsgBox(Prompt, [Buttons As VbMsgBoxStyle = vbOKOnly], [Title]) As VbMsgBoxResult",
    "inputbox": "InputBox(Prompt, [Title], [Default]) As String",
    "left": "Left(String, Length) As String", "right": "Right(String, Length) As String",
    "mid": "Mid(String, Start, [Length]) As String", "len": "Len(Expression) As Long",
    "instr": "InStr([Start], String1, String2, [Compare]) As Long", "replace": "Replace(Expression, Find, Replace)",
    "format": "Format(Expression, [Format]) As String", "split": "Split(Expression, [Delimiter]) As String()",
    "join": "Join(SourceArray, [Delimiter]) As String", "ucase": "UCase(String) As String",
    "lcase": "LCase(String) As String", "trim": "Trim(String) As String", "val": "Val(String) As Double",
    "cint": "CInt(Expression) As Integer", "clng": "CLng(Expression) As Long", "cdbl": "CDbl(Expression) As Double",
    "cstr": "CStr(Expression) As String", "iif": "IIf(Expression, TruePart, FalsePart)",
    "dateadd": "DateAdd(Interval, Number, Date) As Date", "datediff": "DateDiff(Interval, Date1, Date2) As Long",
    "rgb": "RGB(Red, Green, Blue) As Long", "ubound": "UBound(Array, [Dimension]) As Long",
    "additem": "AddItem(Item As String, [Index])", "removeitem": "RemoveItem(Index As Integer)",
    "move": "Move(Left, [Top], [Width], [Height])", "show": "Show([Modal])",
}

ARGS = {"KeyPress": "KeyAscii As Integer", "KeyDown": "KeyCode As Integer, Shift As Integer",
        "KeyUp": "KeyCode As Integer, Shift As Integer",
        "MouseDown": "Button As Integer, Shift As Integer, X As Single, Y As Single",
        "MouseUp": "Button As Integer, Shift As Integer, X As Single, Y As Single",
        "MouseMove": "Button As Integer, Shift As Integer, X As Single, Y As Single",
        "Unload": "Cancel As Integer", "QueryUnload": "Cancel As Integer, UnloadMode As Integer"}


def _vb_event(ctype, ev):
    from ..runtimes.vbrun import vb_event_name
    return vb_event_name(ctype, ev)


def _twips(v) -> int:
    return int(v) * 15


def _vbstr(s) -> str:
    return '"' + str(s).replace('"', '""') + '"'


class VBBasicPlugin(LanguagePlugin):
    id = "vb-basic"
    display_name = "Visual Basic 6 (BASIC)"
    code_ext = ".bas"
    supports_debug = True
    case_sensitive = False
    line_comments = ["'"]
    block_comment = None
    string_quotes = ['"']
    keywords = """Dim Private Public Const Sub Function End If Then Else ElseIf For To Step Next Each In Do
        Loop While Wend Until Select Case Is With Exit Call Set Let New Nothing True False And Or Not Xor Mod
        Option Explicit As Integer Long String Double Single Boolean Variant Object Date Currency Byte
        ByVal ByRef Optional ParamArray ReDim Preserve On Error Resume GoTo Me Static Type Enum Property
        Get Like Unload Load Debug Print Stop Empty Null Erase Global Friend""".split()
    builtins = sorted({"MsgBox", "InputBox", "Len", "Left", "Right", "Mid", "UCase", "LCase", "Trim", "LTrim",
                       "RTrim", "InStr", "InStrRev", "Replace", "Space", "String", "StrReverse", "Chr", "Asc",
                       "Str", "CStr", "Val", "CInt", "CLng", "CDbl", "CSng", "CBool", "CDate", "Int", "Fix",
                       "Abs", "Sgn", "Sqr", "Exp", "Log", "Sin", "Cos", "Tan", "Atn", "Round", "Rnd",
                       "Randomize", "Hex", "Oct", "IsNumeric", "IsEmpty", "IsNull", "IsArray", "IsDate",
                       "IsObject", "TypeName", "VarType", "UBound", "LBound", "Split", "Join", "Array",
                       "IIf", "Format", "FormatNumber", "FormatCurrency", "FormatPercent", "Now", "Date",
                       "Time", "Timer", "Year", "Month", "Day", "Hour", "Minute", "Second", "Weekday",
                       "DateSerial", "TimeSerial", "DateAdd", "DateDiff", "DateValue", "MonthName",
                       "WeekdayName", "RGB", "QBColor", "DoEvents", "CreateObject", "Environ",
                       "LoadPicture", "App", "Screen", "Clipboard", "Err", "vbCrLf", "vbNewLine", "vbTab",
                       "vbYes", "vbNo", "vbOK", "vbCancel", "vbYesNo", "vbOKCancel", "vbYesNoCancel",
                       "vbInformation", "vbExclamation", "vbCritical", "vbQuestion", "vbChecked",
                       "vbUnchecked", "vbRed", "vbGreen", "vbBlue", "vbBlack", "vbWhite", "vbYellow"})

    def find_interpreter(self, configured: str = "") -> str:
        return sys.executable          # the BASIC interpreter is part of the IDE

    # ------------------------------------------------------------ files
    def designer_file(self, form_name: str) -> str:
        return f"{form_name}.frm"

    # ------------------------------------------------------------ events
    def handler_for(self, form, ctrl, event):
        if ctrl is not None and ctrl.type == "MenuStrip":
            return f"{event}_Click"
        if ctrl is None:
            ev = _vb_event("Form", event)
            return f"Form_{ev}"
        return f"{ctrl.name}_{_vb_event(ctrl.type, event)}"

    def events_for(self, ctrl):
        if ctrl is None:
            return list(FORM_EVENTS)
        if ctrl.type == "MenuStrip":
            return [it["Name"] for it in menu_leaves(ctrl.props.get("Items", []))]
        return [e for e in CONTROL_TYPES[ctrl.type].all_events() if _vb_event(ctrl.type, e)]

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*(?:(?:Private|Public|Friend)\s+)?(?:Static\s+)?(?:Sub|Function)\s+"
                                     rf"{re.escape(name)}\b", re.I)

    def add_handler(self, code: str, name: str, form: Form, args: str | None = None) -> tuple[str, int]:
        event = name.rsplit("_", 1)[-1]
        params = ARGS.get(event, "")
        lines = code.rstrip("\n").splitlines()
        lines += ["", f"Private Sub {name}({params})", "    ", "End Sub"]
        return "\n".join(lines) + "\n", len(lines) - 2

    # ------------------------------------------------------------ templates
    def new_code(self, form: Form, is_startup: bool) -> str:
        return ("Option Explicit\n\n"
                "Private Sub Form_Load()\n"
                "    \n"
                "End Sub\n")

    def module_template(self, name: str) -> str:
        return f"Attribute VB_Name = \"{name}\"\nOption Explicit\n\n"

    def generate_designer(self, form: Form, user_code: str) -> str:
        """A VB6-format .frm description of the form (for reading / VB6 export)."""
        fp = form.props
        L = ["VERSION 5.00", f"Begin VB.Form {form.name}",
             f"   Caption         =   {_vbstr(fp.get('Text', form.name))}",
             f"   ClientHeight    =   {_twips(fp['Height'])}",
             f"   ClientWidth     =   {_twips(fp['Width'])}",
             "   ScaleMode       =   1  'Twip" if fp.get("ScaleMode") == "Twip" else "   ScaleMode       =   3  'Pixel",
             "   StartUpPosition =   2  'CenterScreen" if fp.get("StartPosition", "CenterScreen") == "CenterScreen"
             else "   StartUpPosition =   0  'Manual"]

        def emit(parent, indent):
            for c in form.children(parent) if parent is not None else []:
                p = c.props
                pad = "   " * indent
                L.append(f"{pad}Begin VB.{VB_CLASS.get(c.type, 'PictureBox')} {c.name}")
                if "Text" in p and c.type not in ("TextBox", "ComboBox"):
                    L.append(f"{pad}   Caption         =   {_vbstr(p['Text'])}")
                if c.type == "TextBox":
                    L.append(f"{pad}   Text            =   {_vbstr(p.get('Text', ''))}")
                for k, v in (("Left", p["Left"]), ("Top", p["Top"]), ("Width", p["Width"]), ("Height", p["Height"])):
                    L.append(f"{pad}   {k:<16}=   {_twips(v)}")
                L.append(f"{pad}   TabIndex        =   {int(p.get('TabIndex', 0))}")
                if c.ctype.container:
                    emit(c.name, indent + 1)
                L.append(f"{pad}End")
        emit("", 1)
        for t in form.nonvisual():
            if t.type == "Timer":
                L += [f"   Begin VB.Timer {t.name}", f"      Interval        =   {int(t.props['Interval'])}",
                      f"      Enabled         =   {-1 if t.props.get('Enabled') else 0}  'True/False", "   End"]
            if t.type == "MenuStrip":
                def menu(items, indent):
                    for it in items:
                        pad = "   " * indent
                        if it.get("Text") == "-":
                            L.extend([f"{pad}Begin VB.Menu mnuSep{len(L)}", f"{pad}   Caption         =   \"-\"", f"{pad}End"])
                            continue
                        L.extend([f"{pad}Begin VB.Menu {it['Name']}", f"{pad}   Caption         =   {_vbstr(it['Text'])}"])
                        menu(it.get("Items", []), indent + 1)
                        L.append(f"{pad}End")
                menu(t.props.get("Items", []), 1)
        L += ["End", f"Attribute VB_Name = \"{form.name}\"",
              "' (generated by RAD IDE - the code lives in " + f"{form.name}.bas)", ""]
        return "\n".join(L)

    # ------------------------------------------------------------ run / debug
    def _env(self, folder, extra=None):
        env = dict(os.environ, PYTHONPATH=str(IDE_ROOT), PYTHONUNBUFFERED="1")
        env.update(extra or {})
        return env

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        return RunSpec(interpreter, ["-u", "-m", "radide.runtimes.vbrun", str(folder)], folder, self._env(folder))

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        return RunSpec(interpreter, ["-u", "-m", "radide.runtimes.vbrun", str(folder), "--debug"], folder,
                       self._env(folder, {"RADDBG_BP": self.breakpoints_env(breakpoints)}))

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"(\w+)\s*\.\s*(\w*)$", before)
        names = names or {}
        if m:
            obj = m.group(1).lower()
            typ = None
            for n, t in names.items():
                if n.lower() == obj:
                    typ = t
            if obj == "me":
                typ = "Form"
            if obj in ("app",):
                return [Completion(x, "property") for x in ("Title", "Path", "EXEName", "Major", "Minor")]
            if obj == "err":
                return [Completion(x, "property") for x in ("Number", "Description", "Source", "Clear", "Raise")]
            if obj == "debug":
                return [Completion("Print", "method", "Debug.Print expression")]
            if typ is None:
                return []
            mem = MEMBERS.get(typ, []) + ([] if typ in ("Timer", "Form") else COMMON_MEMBERS)
            if typ == "Form":
                mem = mem + [n for n, t in names.items() if t != "Form"]
            return [Completion(x, "method" if x in ("AddItem", "RemoveItem", "Clear", "SetFocus", "Refresh",
                                                    "Move", "ZOrder", "Show", "Hide") else "property",
                               SIGNATURES.get(x.lower(), "")) for x in dict.fromkeys(mem)]
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(b, "function", SIGNATURES.get(b.lower(), "")) for b in self.builtins]
        out += [Completion(n, "control", t) for n, t in names.items()]
        for mm in re.finditer(r"^\s*(?:Private\s+|Public\s+)?(?:Sub|Function)\s+(\w+)\s*(\([^)]*\))?",
                              code, re.I | re.M):
            out.append(Completion(mm.group(1), "function", mm.group(1) + (mm.group(2) or "()")))
        seen, uniq = set(), []
        for c in out:
            if c.name.lower() not in seen:
                seen.add(c.name.lower())
                uniq.append(c)
        return uniq

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"(\w+)\s*\(?[^()]*$", before)
        if not m:
            return ""
        fn = m.group(1).lower()
        if fn in SIGNATURES:
            return SIGNATURES[fn]
        mm = re.search(rf"^\s*(?:Private\s+|Public\s+)?(?:Sub|Function)\s+{re.escape(m.group(1))}\s*(\([^)]*\))",
                       code, re.I | re.M)
        return f"{m.group(1)}{mm.group(1)}" if mm else ""


PLUGIN = VBBasicPlugin()
