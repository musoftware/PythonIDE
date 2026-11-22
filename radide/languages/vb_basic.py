"""VB6-compatible BASIC language plugin (runs on the bundled interpreter)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ..controls import CONTROL_TYPES, FORM_EVENTS, menu_leaves
from ..model import Form
from .base import Completion, LanguagePlugin, RunSpec

from ..paths import python_root as _python_root  # noqa: E402
IDE_ROOT = _python_root()   # a real Python imports radide from here (not _internal in a release build)

VB_CLASS = {"Button": "CommandButton", "Label": "Label", "TextBox": "TextBox", "CheckBox": "CheckBox",
            "RadioButton": "OptionButton", "ListBox": "ListBox", "ComboBox": "ComboBox",
            "PictureBox": "PictureBox", "ProgressBar": "ProgressBar", "NumericUpDown": "UpDown",
            "TrackBar": "Slider", "Panel": "PictureBox", "GroupBox": "Frame", "Timer": "Timer",
            "TabControl": "TabDlg.SSTab", "TreeView": "MSComctlLib.TreeView", "ListView": "MSComctlLib.ListView",
            "DataGridView": "MSFlexGridLib.MSFlexGrid", "DateTimePicker": "MSComCtl2.DTPicker",
            "LinkLabel": "Label", "StatusBar": "MSComctlLib.StatusBar", "ActiveX": "VBControlExtender"}
DIALOG_TYPES = ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog", "FolderBrowserDialog")

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
    "Timer": ["Interval", "Enabled"],
    "TabControl": ["Tab", "Tabs", "Caption", "TabCaption", "SelectedIndex"],
    "TreeView": ["Nodes", "SelectedItem", "Text", "PathSeparator"],
    "ListView": ["ListItems", "ColumnHeaders", "SelectedItem", "ListIndex", "Text", "View"],
    "DataGridView": ["TextMatrix", "Rows", "Cols", "Row", "Col", "Text", "FixedRows", "FixedCols",
                     "AddItem", "RemoveItem", "Clear", "ReadOnly"],
    "DateTimePicker": ["Value", "Year", "Month", "Day", "Hour", "Minute", "Second", "Format", "Text"],
    "LinkLabel": ["Caption", "LinkColor"], "StatusBar": ["SimpleText", "Caption"],
    "ActiveX": ["Object", "ProgID"],
    **{d: ["ShowOpen", "ShowSave", "ShowColor", "ShowFont", "ShowFolder", "ShowDialog", "FileName", "FileTitle",
           "Filter", "DialogTitle", "InitDir", "Color", "FontName", "FontSize", "SelectedPath", "CancelError",
           "Flags", "Name", "Tag"]
       for d in ("OpenFileDialog", "SaveFileDialog", "ColorDialog", "FontDialog", "FolderBrowserDialog")},
    "ToolButton": ["Caption", "Enabled", "Visible"],
    "Nodes": ["Add", "Clear", "Count", "Item", "Remove"],
    "ListItems": ["Add", "Clear", "Count", "Item", "Remove"],
    "ColumnHeaders": ["Add", "Clear", "Count", "Item"],
    "Node": ["Text", "Key", "Index", "FullPath", "Parent", "Child", "Children", "Expanded", "Selected",
             "EnsureVisible", "Tag"],
    "ListItem": ["Text", "SubItems", "Key", "Index", "Selected", "EnsureVisible"],
    "Form": ["Caption", "Show", "Hide", "Width", "Height", "Left", "Top",
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
    "radcall": "RadCall(\"Module.Function\", [Args...]) - call code written in another language",
    "textmatrix": "TextMatrix(Row, Col) As String  (row 0 = column headers)",
    "subitems": "SubItems(Index) As String  (1 = second column)",
    "tabcaption": "TabCaption(Index) As String",
    "showopen": "ShowOpen  - fills FileName (CancelError = True raises error 32755 on Cancel)",
    "showsave": "ShowSave  - fills FileName", "showcolor": "ShowColor  - fills Color",
    "showfont": "ShowFont  - fills FontName, FontSize", "showfolder": "ShowFolder  - fills SelectedPath",
    "showdialog": "ShowDialog() As String  - \"OK\" or \"Cancel\"",
}
# Nodes.Add / ListItems.Add have different signatures: looked up by "<collection>.add"
COLLECTION_SIGNATURES = {
    "nodes": "Add([Relative], [Relationship As tvwChild=4], [Key], [Text]) As Node",
    "listitems": "Add([Index], [Key], [Text]) As ListItem",
    "columnheaders": "Add([Index], [Key], [Text], [Width])",
}
METHODS = {"AddItem", "RemoveItem", "Clear", "SetFocus", "Refresh", "Move", "ZOrder", "Show", "Hide", "Add",
           "Remove", "Item", "ShowOpen", "ShowSave", "ShowColor", "ShowFont", "ShowFolder", "ShowDialog",
           "EnsureVisible", "TextMatrix", "SubItems", "TabCaption"}

ARGS = {"KeyPress": "KeyAscii As Integer", "KeyDown": "KeyCode As Integer, Shift As Integer",
        "KeyUp": "KeyCode As Integer, Shift As Integer",
        "MouseDown": "Button As Integer, Shift As Integer, X As Single, Y As Single",
        "MouseUp": "Button As Integer, Shift As Integer, X As Single, Y As Single",
        "MouseMove": "Button As Integer, Shift As Integer, X As Single, Y As Single",
        "Unload": "Cancel As Integer", "QueryUnload": "Cancel As Integer, UnloadMode As Integer"}


def _vb_event(ctype, ev):
    from ..runtimes.vbevents import vb_event_name
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
    debug_bp_extras = True           # agent: hit counts, logpoints, expandable Locals (debug_extras)
    package_manager = None      # no package manager: Manage Packages explains how to add modules
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
                       "LoadPicture", "RadCall", "App", "Screen", "Clipboard", "Err", "vbCrLf", "vbNewLine", "vbTab",
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
        if ctrl is not None and ctrl.type in ("MenuStrip", "ToolStrip"):
            return f"{event}_Click"
        if ctrl is None:
            ev = _vb_event("Form", event)
            return f"Form_{ev}"
        # control arrays (VB6): one handler for all members - cmdDigit_Click(Index As Integer)
        return f"{ctrl.props.get('ArrayName') or ctrl.name}_{_vb_event(ctrl.type, event)}"

    def events_for(self, ctrl):
        if ctrl is None:
            return list(FORM_EVENTS)
        if ctrl.type in ("MenuStrip", "ToolStrip"):
            return [it["Name"] for it in menu_leaves(ctrl.props.get("Items", []))]
        return [e for e in CONTROL_TYPES[ctrl.type].all_events() if _vb_event(ctrl.type, e)]

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*(?:(?:Private|Public|Friend)\s+)?(?:Static\s+)?(?:Sub|Function)\s+"
                                     rf"{re.escape(name)}\b", re.I)

    def add_handler(self, code: str, name: str, form: Form, args: str | None = None) -> tuple[str, int]:
        event = name.rsplit("_", 1)[-1]
        params = ARGS.get(event, "")
        owner = name.rsplit("_", 1)[0].lower()
        if form is not None and any((c.props.get("ArrayName") or "").lower() == owner for c in form.controls):
            params = "Index As Integer" + (", " + params if params else "")     # control array (VB6)
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
        return (f"Attribute VB_Name = \"{name}\"\nOption Explicit\n\n"
                f"' Other languages of the project can call the Public Functions of this module:\n"
                f"'     Python: from radcall import radcall;  x = radcall(\"{name}.AddNumbers\", 2, 3)\n"
                f"'     Ring:   x = radcall(\"{name}.AddNumbers\", [2, 3])\n"
                f"' Call functions written in other languages with:\n"
                f"'     x = RadCall(\"OtherModule.function\", 2, 3)\n\n")

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        """RAD Hub worker: serves this module's Functions to the other languages."""
        return [sys.executable, "-u", str(IDE_ROOT / "radide" / "runtimes" / "clients" / "vb" / "vbworker.py"),
                module_file]

    # ------------------------------------------------------------ solution references (CONTRACTS 7.2)
    _PROC_RX = re.compile(r"^\s*(?:(Public|Private|Friend|Global)\s+)?(?:Static\s+)?(Function|Sub)\s+(\w+)\s*(.*)$",
                          re.I)

    @staticmethod
    def _join_continuations(text: str) -> list[tuple[int, str]]:
        """Logical lines (line continuations " _" joined) with their first physical line."""
        out, buf, start = [], "", 0
        for i, raw in enumerate(text.splitlines()):
            if not buf:
                start = i
            if re.search(r"\s_\s*$", raw):
                buf += re.sub(r"\s_\s*$", " ", raw)
                continue
            out.append((start, buf + raw))
            buf = ""
        if buf:
            out.append((start, buf))
        return out

    @staticmethod
    def _vb_params(rest: str) -> list[str] | None:
        """Parameter names of "(ByVal a As Long, Optional b = 2) As X"; None if unparsable."""
        rest = rest.strip()
        if not rest.startswith("("):
            return []
        depth, inner = 0, None
        for i, ch in enumerate(rest):
            depth += ch == "("
            depth -= ch == ")"
            if depth == 0:
                inner = rest[1:i]
                break
        if inner is None:
            return None
        parts, depth, cur, in_str = [], 0, "", False
        for ch in inner:
            if ch == '"':
                in_str = not in_str
            if not in_str and ch in "()":
                depth += 1 if ch == "(" else -1
            if ch == "," and depth == 0 and not in_str:
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        if cur.strip():
            parts.append(cur)
        names = []
        for p in parts:
            words = [w for w in p.split("=")[0].split() if w.lower() not in ("byval", "byref", "optional",
                                                                             "paramarray")]
            if not words:
                return None
            names.append(re.sub(r"[()$%&!#@]", "", words[0]))
        return names

    def exported_functions(self, path: Path, text: str) -> list:
        """Public Functions/Subs of a .bas module (no modifier = Public; Private/Friend skipped,
        event handlers and Property procedures skipped). ByVal/ByRef/Optional/As are stripped."""
        from . import _refs
        path = Path(path)
        if path.suffix.lower() != ".bas" or _refs.is_proxy_text(text) or path.name.startswith("_"):
            return []
        logical = self._join_continuations(text)
        physical = text.splitlines()
        out, seen = [], set()
        for idx, (lineno, line) in enumerate(logical):
            m = self._PROC_RX.match(line)
            if not m:
                continue
            vis, kind, name, rest = (m.group(1) or "public").lower(), m.group(2).lower(), m.group(3), m.group(4)
            if vis in ("private", "friend") or name.lower() in seen or _refs.is_event_handler(name):
                continue
            params = self._vb_params(rest.split("'", 1)[0] if '"' not in rest else rest)
            if params is None:
                continue
            seen.add(name.lower())
            doc = ""
            j = lineno - 1
            above = []
            while j >= 0 and physical[j].strip().startswith("'"):
                above.insert(0, physical[j].strip().lstrip("'").strip())
                j -= 1
            doc = next((a for a in above if a), "")
            if not doc:
                for nxt in physical[lineno + 1:lineno + 4]:
                    s = nxt.strip()
                    if s.startswith("'"):
                        doc = s.lstrip("'").strip()
                        break
                    if s:
                        break
            out.append(_refs.make_function(name, params, path.stem, doc, "sub" if kind == "sub" else "function"))
        return out

    def _vb_ident(self, name: str) -> str:
        s = re.sub(r"\W", "_", str(name)).lstrip("_") or "x"
        if s[0].isdigit():
            s = "n" + s
        return s + "_" if s.lower() in {k.lower() for k in self.keywords} else s

    def reference_proxy(self, lib: str, functions: list) -> dict[str, str]:
        """``<Lib>.ref.bas`` = a module named <Lib> in the consumer project:
        ``x = <Lib>.Add(2, 3)`` / ``<Lib>.Hello "x"``; each procedure forwards to RadCall."""
        mod = self._vb_ident(lib)
        builtins = {b.lower() for b in self.builtins}
        L = [self.proxy_header(lib).rstrip("\n"),
             f"Attribute VB_Name = \"{mod}\"",
             f"' {lib} - reference to the {lib} project of the solution.",
             f"'     x = {mod}.<Function>(args)      {mod}.<Sub> args",
             "' The procedures run in the library's own language; calls go through RAD Hub.",
             "Option Explicit", ""]
        seen = set()
        for f in functions:
            fn = self._vb_ident(f.name)
            if fn.lower() in seen:
                continue
            seen.add(fn.lower())
            params, used = [], set()
            for p in f.params:
                q = self._vb_ident(p)
                while q.lower() in used or q.lower() == fn.lower():
                    q += "_"
                used.add(q.lower())
                params.append(q)
            target = _vbstr(f"{f.module}.{f.name}")
            args = "".join(f", {p}" for p in params)
            # a name that is also a VB built-in must not hide it: Private, still callable as Lib.Name
            vis = "Private" if fn.lower() in builtins else "Public"
            doc = (f.doc or "").replace("\n", " ")
            L.append(f"' {doc}" if doc else f"' {lib}: {f.module}.{f.name}({', '.join(f.params)})")
            if f.kind == "sub":
                L += [f"{vis} Sub {fn}({', '.join(params)})", f"    Call RadCall({target}{args})", "End Sub", ""]
            else:
                L += [f"{vis} Function {fn}({', '.join(params)})", f"    {fn} = RadCall({target}{args})",
                      "End Function", ""]
        return {f"{lib}.ref.bas": "\n".join(L)}

    def example_function(self, name: str) -> str:
        """An example public function for a new Class Library module."""
        return (f"' Return a + b. Projects that reference this library call it as <Library>.{name}(a, b)\n"
                f"Public Function {name}(ByVal a As Variant, ByVal b As Variant) As Variant\n"
                f"    {name} = a + b\n"
                f"End Function\n")

    @staticmethod
    def proxy_module_name(filename: str) -> str:
        """VB module name of a reference proxy file ("MathLib.ref.bas" -> "MathLib")."""
        n = Path(filename).name
        return n[:-len(".ref.bas")] if n.lower().endswith(".ref.bas") else Path(n).stem

    def _modules_near(self, path) -> dict[str, list[tuple[str, str]]]:
        """{module name: [(procedure, signature)]} of the reference proxies and .bas modules next to *path*."""
        out: dict[str, list[tuple[str, str]]] = {}
        if not path:
            return out
        folder = Path(path).parent
        try:
            files = sorted(folder.glob("*.bas"))
        except OSError:
            return out
        for f in files:
            if f.name.startswith("_") or Path(path).name.lower() == f.name.lower()                     or (folder / f"{f.stem}.form").exists():
                continue
            try:
                text = f.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            procs = []
            doc = ""
            for _n, line in self._join_continuations(text):
                m = self._PROC_RX.match(line)
                if m and (m.group(1) or "").lower() not in ("private", "friend") or \
                        (m and f.name.lower().endswith(".ref.bas")):
                    sig = f"{m.group(3)}{m.group(4).split(chr(39))[0].strip() or '()'}"
                    procs.append((m.group(3), sig + (f"  - {doc}" if doc else "")))
                s = line.strip()
                doc = s.lstrip("'").strip() if s.startswith("'") else ""
            if procs:
                out[self.proxy_module_name(f.name)] = procs
        return out

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
                cls = VB_CLASS.get(c.type, "PictureBox")
                L.append(f"{pad}Begin {cls if '.' in cls else 'VB.' + cls} {c.name}")
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
            if t.type in DIALOG_TYPES:
                L += [f"   Begin MSComDlg.CommonDialog {t.name}", "   End"]
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
        # UTF-8: the IDE decodes the program output as UTF-8 (Debug.Print "مرحبا" must not crash on cp1252)
        env = dict(os.environ, PYTHONPATH=str(IDE_ROOT), PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
        env.update(extra or {})
        return env

    @staticmethod
    def _target(folder: Path) -> tuple[Path, Path]:
        """(what vbrun runs, working folder): a VB6 project opened in place (radide/foreign/vb6_project.py)
        runs its own .vbp - the native files, no conversion; other projects run their folder."""
        try:
            from ..foreign.vb6_project import native_project_file
            vbp = native_project_file(folder)
        except Exception:  # noqa: BLE001
            vbp = None
        if vbp is not None and vbp.is_file():
            return vbp, vbp.parent
        return Path(folder), Path(folder)

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        target, cwd = self._target(folder)
        return RunSpec(interpreter, ["-u", "-m", "radide.runtimes.vbrun", str(target)], cwd, self._env(folder))

    def debug_spec(self, folder, startup_form, interpreter, breakpoints) -> RunSpec:
        target, cwd = self._target(folder)
        return RunSpec(interpreter, ["-u", "-m", "radide.runtimes.vbrun", str(target), "--debug"], cwd,
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
            coll = {"nodes": "Nodes", "listitems": "ListItems", "columnheaders": "ColumnHeaders",
                    "selecteditem": None}.get(obj, "")
            if typ is None and coll is None:      # x.SelectedItem.  -> Node or ListItem
                owner = re.search(r"(\w+)\s*\.\s*selecteditem\s*\.\s*\w*$", before, re.I)
                otype = next((t for n, t in names.items() if owner and n.lower() == owner.group(1).lower()), "")
                coll = "ListItem" if otype == "ListView" else "Node"
            if typ is None and coll:
                return [Completion(x, "method" if x in METHODS else "property",
                                   COLLECTION_SIGNATURES.get(obj, "") if x == "Add" else SIGNATURES.get(x.lower(), ""))
                        for x in MEMBERS[coll]]
            if typ is None:
                mods = {k.lower(): v for k, v in self._modules_near(path).items()}
                return [Completion(n, "function", sig) for n, sig in mods.get(obj, [])]
            nonvisual = typ in ("Timer", "Form", "ToolButton", *DIALOG_TYPES)
            mem = MEMBERS.get(typ, []) + ([] if nonvisual else COMMON_MEMBERS)
            if typ == "Form":
                mem = mem + [n for n, t in names.items() if t != "Form"]
            return [Completion(x, "method" if x in METHODS else "property",
                               SIGNATURES.get(x.lower(), "")) for x in dict.fromkeys(mem)]
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(b, "function", SIGNATURES.get(b.lower(), "")) for b in self.builtins]
        out += [Completion(n, "control", t) for n, t in names.items()]
        out += [Completion(n, "module", f"Module {n} ({len(p)} procedures)")
                for n, p in self._modules_near(path).items()]
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
        if mm:
            return f"{m.group(1)}{mm.group(1)}"
        owner = re.search(r"(\w+)\s*\.\s*\w+\s*\(?[^()]*$", before)
        if owner:
            for mod, procs in self._modules_near(path).items():
                if mod.lower() == owner.group(1).lower():
                    for n, sig in procs:
                        if n.lower() == fn:
                            return f"{mod}.{sig}"
        return ""


PLUGIN = VBBasicPlugin()
