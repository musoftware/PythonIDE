"""F1 context help and the Help menu.

F1 looks at the word under the cursor in a code editor (or the selected control
in the designer) and opens the right documentation: a bundled VB6 reference for
VB keywords/functions, docs.python.org for Python, Tkinter / Qt / RingQt class
docs, and the Ring documentation (local copy if present, else ring-lang.github.io).
Help > RAD IDE Help shows radide/features/help/index.html."""
from __future__ import annotations

import builtins
import html
import keyword
import os
import re
import sys
import webbrowser
from pathlib import Path
from urllib.parse import quote_plus

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QPushButton, QTextBrowser,
                             QVBoxLayout)

HELP_DIR = Path(__file__).resolve().parent / "help"


def manual_page() -> Path:
    """index_<lang>.html for the IDE's display language (radide/i18n), else index.html."""
    from .. import i18n
    page = HELP_DIR / f"index_{i18n.language()}.html"
    return page if i18n.language() != "en" and page.exists() else HELP_DIR / "index.html"
RING_HOME = Path(r"C:\ring\ring")

# ------------------------------------------------------------------ VB6 reference (bundled)
# name: (syntax, description)
VB_REF: dict[str, tuple[str, str]] = {
    "Dim": ("Dim name [As type] [, name [As type]]...",
            "Declares variables and allocates storage. Types: Integer, Long, Single, Double, Currency, String, "
            "Boolean, Date, Variant, Object. <code>Dim a(10) As Integer</code> declares an array (0 to 10)."),
    "ReDim": ("ReDim [Preserve] name(subscripts) [As type]",
              "Changes the size of a dynamic array. <b>Preserve</b> keeps the existing values."),
    "Const": ("[Public | Private] Const name [As type] = expression", "Declares a constant."),
    "Private": ("Private name [As type]", "Declares a variable or procedure visible only in its module/form."),
    "Public": ("Public name [As type]", "Declares a variable or procedure visible to all modules."),
    "Static": ("Static name [As type]", "A local variable that keeps its value between calls."),
    "Option": ("Option Explicit | Option Base {0|1} | Option Compare {Binary|Text}",
               "<b>Option Explicit</b> forces every variable to be declared with Dim."),
    "Sub": ("[Private | Public] Sub name [(arglist)]\n    statements\nEnd Sub",
            "Declares a procedure that does not return a value. Call it with <code>name args</code> or "
            "<code>Call name(args)</code>. Event handlers are Subs named <code>Control_Event</code>."),
    "Function": ("[Private | Public] Function name [(arglist)] [As type]\n    name = value\nEnd Function",
                 "Declares a procedure that returns a value (assign the result to the function name)."),
    "Property": ("Property Get | Let | Set name [(arglist)]", "Declares a property procedure."),
    "ByVal": ("Sub name(ByVal arg As type)", "The argument is passed by value (the caller's variable is not changed)."),
    "ByRef": ("Sub name(ByRef arg As type)", "The argument is passed by reference (default)."),
    "Optional": ("Sub name(Optional arg As type = default)", "The argument may be omitted."),
    "If": ("If condition Then\n    statements\n[ElseIf condition Then\n    statements]\n[Else\n    statements]\nEnd If",
           "Conditional execution. Single-line form: <code>If x &gt; 0 Then y = 1 Else y = 2</code>."),
    "Select": ("Select Case expression\n    Case value1, value2\n    Case 1 To 5\n    Case Is &gt; 10\n"
               "    Case Else\nEnd Select", "Runs the block of the first matching Case."),
    "For": ("For counter = start To end [Step step]\n    statements\n    [Exit For]\nNext [counter]",
            "Repeats statements a given number of times."),
    "Each": ("For Each element In group\n    statements\nNext [element]",
             "Repeats statements for each item of an array or collection."),
    "Do": ("Do [{While | Until} condition]\n    statements\n    [Exit Do]\nLoop\n\nDo\n    statements\n"
           "Loop [{While | Until} condition]", "Repeats a block while/until a condition is true."),
    "While": ("While condition\n    statements\nWend", "Repeats while the condition is true (prefer Do...Loop)."),
    "Exit": ("Exit Do | For | Function | Property | Sub", "Leaves the loop or procedure immediately."),
    "GoTo": ("GoTo label", "Jumps to a label in the same procedure."),
    "On": ("On Error GoTo label | On Error Resume Next | On Error GoTo 0",
           "Enables error handling. Inside the handler use <code>Err.Number</code>, <code>Err.Description</code> "
           "and <code>Resume</code> / <code>Resume Next</code>."),
    "Err": ("Err.Number, Err.Description, Err.Raise number [, source, description], Err.Clear",
            "The error object filled when a run-time error occurs."),
    "Resume": ("Resume | Resume Next | Resume label", "Continues after an error handler."),
    "With": ("With object\n    .Property = value\nEnd With", "Runs statements on one object without repeating its name."),
    "Set": ("Set objectvar = object | Nothing", "Assigns an object reference."),
    "Call": ("Call name(args)", "Calls a Sub or Function (the result is discarded)."),
    "Type": ("[Private | Public] Type name\n    member As type\nEnd Type", "Declares a user-defined record type."),
    "Enum": ("[Public | Private] Enum name\n    member [= value]\nEnd Enum", "Declares a set of named constants."),
    "Unload": ("Unload object", "Unloads a form (Unload Me closes the current form)."),
    "Load": ("Load object", "Loads a form without showing it."),
    "Me": ("Me", "The form (or class) whose code is running."),
    "Nothing": ("Set x = Nothing", "Releases an object reference. Test with <code>x Is Nothing</code>."),
    "End": ("End | End Sub | End Function | End If ...", "<b>End</b> alone stops the program immediately."),
    "MsgBox": ("MsgBox(prompt [, buttons] [, title]) As VbMsgBoxResult",
               "Shows a message box. buttons: vbOKOnly, vbOKCancel, vbYesNo, vbYesNoCancel + vbInformation, "
               "vbExclamation, vbCritical, vbQuestion. Returns vbOK, vbCancel, vbYes, vbNo..."),
    "InputBox": ("InputBox(prompt [, title] [, default]) As String",
                 "Shows a dialog that asks for text. Returns \"\" when Cancel is pressed."),
    "Len": ("Len(string) As Long", "Number of characters in a string."),
    "Left": ("Left(string, length) As String", "The first <i>length</i> characters."),
    "Right": ("Right(string, length) As String", "The last <i>length</i> characters."),
    "Mid": ("Mid(string, start [, length]) As String", "Part of a string (start is 1-based)."),
    "InStr": ("InStr([start,] string1, string2 [, compare]) As Long",
              "Position of string2 inside string1 (1-based), 0 when not found."),
    "InStrRev": ("InStrRev(string1, string2 [, start]) As Long", "Like InStr, searching from the end."),
    "Replace": ("Replace(expression, find, replacewith) As String", "Replaces every occurrence of <i>find</i>."),
    "Trim": ("Trim(string) / LTrim(string) / RTrim(string)", "Removes leading and/or trailing spaces."),
    "UCase": ("UCase(string) As String", "Converts to upper case."),
    "LCase": ("LCase(string) As String", "Converts to lower case."),
    "Split": ("Split(expression [, delimiter]) As String()", "Splits a string into a 0-based array."),
    "Join": ("Join(array [, delimiter]) As String", "Joins the items of an array into one string."),
    "Format": ("Format(expression [, format]) As String",
               "Formats numbers and dates: <code>Format(3.5, \"0.00\")</code>, <code>Format(Now, \"yyyy-mm-dd hh:nn\")</code>."),
    "Str": ("Str(number) As String", "Converts a number to a string (with a leading space for positive numbers)."),
    "CStr": ("CStr(expression) As String", "Converts any value to a string."),
    "Val": ("Val(string) As Double", "Reads the number at the start of a string (\"12abc\" -&gt; 12)."),
    "CInt": ("CInt(expression) As Integer", "Converts to Integer (rounds to even). Also CLng, CDbl, CSng, CBool, CDate."),
    "CDbl": ("CDbl(expression) As Double", "Converts to Double."),
    "Int": ("Int(number)", "Rounds down to an integer. Fix() truncates towards zero."),
    "Abs": ("Abs(number)", "Absolute value."),
    "Sqr": ("Sqr(number) As Double", "Square root."),
    "Rnd": ("Rnd() As Single", "A random number in [0, 1). Call Randomize first. "
            "<code>Int(Rnd * 6) + 1</code> is a dice roll."),
    "Randomize": ("Randomize [seed]", "Initialises the random-number generator."),
    "Round": ("Round(number [, decimals])", "Rounds a number."),
    "Chr": ("Chr(code) As String", "The character with the given code (Chr(13) = carriage return)."),
    "Asc": ("Asc(string) As Integer", "The character code of the first character."),
    "IIf": ("IIf(condition, truepart, falsepart)", "Returns one of two values."),
    "IsNumeric": ("IsNumeric(expression) As Boolean", "True when the value can be read as a number."),
    "IsEmpty": ("IsEmpty(variant) As Boolean", "True for an uninitialised Variant."),
    "UBound": ("UBound(array [, dimension]) As Long", "The highest index of an array (LBound: the lowest)."),
    "LBound": ("LBound(array [, dimension]) As Long", "The lowest index of an array."),
    "Array": ("Array(item, item, ...) As Variant", "Creates a Variant array."),
    "Now": ("Now As Date", "The current date and time (Date: today, Time: the current time)."),
    "Date": ("Date As Date", "Today's date."),
    "Time": ("Time As Date", "The current time."),
    "DateAdd": ("DateAdd(interval, number, date)", "Adds an interval (\"d\" day, \"m\" month, \"yyyy\" year, \"h\", \"n\", \"s\")."),
    "DateDiff": ("DateDiff(interval, date1, date2)", "Number of intervals between two dates."),
    "Year": ("Year(date) / Month(date) / Day(date) / Hour / Minute / Second", "Parts of a date."),
    "Timer": ("Timer As Single", "Seconds since midnight. (The Timer <i>control</i> raises Timer events.)"),
    "DoEvents": ("DoEvents", "Lets the form process events during a long loop."),
    "CreateObject": ("CreateObject(class) As Object",
                     "Creates an ActiveX object, e.g. <code>CreateObject(\"Scripting.FileSystemObject\")</code>."),
    "Environ": ("Environ(name) As String", "The value of an environment variable."),
    "RGB": ("RGB(red, green, blue) As Long", "A colour value; QBColor(n) gives the 16 classic colours."),
    "Show": ("Form.Show [vbModal]", "Shows a form."),
    "Hide": ("Form.Hide", "Hides a form without unloading it."),
    "AddItem": ("ListBox.AddItem item [, index]", "Adds an item to a ListBox or ComboBox."),
    "RemoveItem": ("ListBox.RemoveItem index", "Removes the item at index (0-based)."),
    "Clear": ("ListBox.Clear", "Removes all items."),
    "ListIndex": ("ListBox.ListIndex", "Index of the selected item (-1 = none)."),
    "ListCount": ("ListBox.ListCount", "Number of items."),
    "Caption": ("object.Caption = text", "Text shown by a Label, Button, CheckBox, Frame or the form title."),
    "Text": ("TextBox.Text", "The contents of a TextBox or ComboBox."),
    "Enabled": ("object.Enabled = True | False", "Whether the control reacts to the user."),
    "Visible": ("object.Visible = True | False", "Whether the control is shown."),
    "SetFocus": ("object.SetFocus", "Moves the keyboard focus to the control."),
    "Click": ("Private Sub Command1_Click()", "Raised when the user clicks the control."),
    "Change": ("Private Sub Text1_Change()", "Raised when the text of a TextBox changes."),
    "Form_Load": ("Private Sub Form_Load()", "Raised once when the form is loaded, before it is shown."),
    "KeyPress": ("Private Sub Text1_KeyPress(KeyAscii As Integer)",
                 "Raised for each typed character; set KeyAscii = 0 to cancel the key."),
    "And": ("a And b", "Logical / bitwise AND. Also Or, Not, Xor, Eqv, Imp."),
    "Mod": ("a Mod b", "Remainder of an integer division. <code>a \\ b</code> is the integer division."),
    "Like": ("string Like pattern", "Pattern match: ? one char, * any chars, # one digit, [a-z] a range."),
    "Is": ("obj1 Is obj2", "True when both refer to the same object (or Nothing)."),
}
_VB_LOWER = {k.lower(): k for k in VB_REF}
VB_ALIASES = {"elseif": "If", "else": "If", "then": "If", "endif": "If", "wend": "While", "loop": "Do",
              "next": "For", "case": "Select", "to": "For", "step": "For", "exit": "Exit", "error": "On",
              "ltrim": "Trim", "rtrim": "Trim", "clng": "CInt", "csng": "CDbl", "cbool": "CInt", "cdate": "CInt",
              "fix": "Int", "month": "Year", "day": "Year", "hour": "Year", "minute": "Year", "second": "Year",
              "or": "And", "not": "And", "xor": "And", "qbcolor": "RGB", "vbmodal": "Show",
              "vbyesno": "MsgBox", "vbokonly": "MsgBox", "vbinformation": "MsgBox", "vbcritical": "MsgBox",
              "vbexclamation": "MsgBox", "vbquestion": "MsgBox", "vbyes": "MsgBox", "vbno": "MsgBox"}

TK_WIDGETS = {"tk", "button", "label", "entry", "text", "listbox", "frame", "canvas", "scrollbar", "checkbutton",
              "radiobutton", "scale", "spinbox", "menu", "menubutton", "toplevel", "panedwindow", "labelframe",
              "message", "stringvar", "intvar", "booleanvar", "doublevar", "photoimage", "after", "mainloop",
              "pack", "grid", "place", "config", "configure", "bind", "insert", "delete", "get"}
TK_MODULES = {"ttk", "messagebox", "filedialog", "simpledialog", "colorchooser", "font", "scrolledtext", "dnd"}
# designer control type -> (Tk widget, Qt class)
CONTROL_DOCS = {"Button": ("button", "QPushButton"), "Label": ("label", "QLabel"), "TextBox": ("entry", "QLineEdit"),
                "CheckBox": ("checkbutton", "QCheckBox"), "RadioButton": ("radiobutton", "QRadioButton"),
                "ListBox": ("listbox", "QListWidget"), "ComboBox": ("ttk.Combobox", "QComboBox"),
                "GroupBox": ("labelframe", "QGroupBox"), "Panel": ("frame", "QFrame"),
                "PictureBox": ("label", "QLabel"), "ProgressBar": ("ttk.Progressbar", "QProgressBar"),
                "TrackBar": ("scale", "QSlider"), "NumericUpDown": ("spinbox", "QSpinBox"),
                "Timer": ("after", "QTimer"), "MenuStrip": ("menu", "QMenuBar"), "TabControl": ("ttk.Notebook", "QTabWidget"),
                "TreeView": ("ttk.Treeview", "QTreeWidget"), "ListView": ("ttk.Treeview", "QTreeWidget"),
                "DataGridView": ("ttk.Treeview", "QTableWidget"), "DateTimePicker": ("entry", "QDateTimeEdit"),
                "LinkLabel": ("label", "QLabel"), "StatusBar": ("label", "QStatusBar"), "ToolStrip": ("frame", "QToolBar"),
                "OpenFileDialog": ("filedialog", "QFileDialog"), "SaveFileDialog": ("filedialog", "QFileDialog"),
                "ColorDialog": ("colorchooser", "QColorDialog"), "FontDialog": ("font", "QFontDialog"),
                "FolderBrowserDialog": ("filedialog", "QFileDialog"), "RichTextBox": ("text", "QTextEdit")}
VB_CONTROL_TOPIC = {"Button": "Click", "TextBox": "Text", "ListBox": "AddItem", "ComboBox": "AddItem",
                    "Label": "Caption", "Timer": "Timer", "CheckBox": "Caption", "RadioButton": "Caption",
                    "GroupBox": "Caption", "MenuStrip": "Click"}


def ring_version() -> str:
    h = RING_HOME / "language" / "include" / "state.h"
    try:
        m = re.search(r'RING_STATE_VERSION\s+"([\d.]+)"', h.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    except OSError:
        pass
    return "1.24"


def ring_local_docs() -> Path | None:
    """A local Ring manual (HTML preferred, else CHM / PDF)."""
    docs = RING_HOME / "documents"
    for cand in (docs / "build" / "html" / "index.html", docs / "html" / "index.html",
                 docs / "ring.chm", docs / "ring.pdf"):
        if cand.exists():
            return cand
    return None


_SPHINX_CACHE: dict[str, dict] = {}


def sphinx_lookup(index_html: Path, word: str) -> str:
    """Find *word* in a local Sphinx manual (searchindex.js): returns 'page.html#anchor' or ''."""
    idx = index_html.parent / "searchindex.js"
    key = str(idx)
    if key not in _SPHINX_CACHE:
        try:
            import json
            t = idx.read_text(encoding="utf-8", errors="replace")
            _SPHINX_CACHE[key] = json.loads(t[t.index("(") + 1:t.rindex(")")])
        except (OSError, ValueError):
            _SPHINX_CACHE[key] = {}
    data = _SPHINX_CACHE[key]
    if not data or not word:
        return ""
    names = data.get("filenames") or [d + ".html" for d in data.get("docnames", [])]
    names = [re.sub(r"\.(rst|txt)$", ".html", n) for n in names]
    w = word.lower()
    best, best_score = "", 0
    for title, places in (data.get("alltitles") or {}).items():
        tl = title.lower().strip()
        if re.match(rf"^{re.escape(w)}\s*(\(\))?\s*(function|command|statement|keyword|class)?s?$", tl):
            score = 100
        elif tl.startswith(w + "(") or tl.startswith(w + " "):
            score = 60
        elif re.search(rf"{re.escape(w)}", tl) and not tl.startswith("why"):
            score = 20
        else:
            continue
        if score > best_score and places:
            doc, anchor = places[0][0], places[0][1]
            if 0 <= doc < len(names):
                best, best_score = names[doc] + (f"#{anchor}" if anchor else ""), score
    if best:
        return best
    for table in ("titleterms", "terms"):
        hit = (data.get(table) or {}).get(w)
        if hit is not None:
            doc = hit if isinstance(hit, int) else (hit[0] if hit else -1)
            if 0 <= doc < len(names):
                return names[doc]
    return ""


def qt_module(cls: str) -> str:
    for mod in ("QtWidgets", "QtCore", "QtGui"):
        try:
            m = __import__(f"PyQt6.{mod}", fromlist=[cls])
            if hasattr(m, cls):
                return mod
        except ImportError:
            pass
    return "QtWidgets"


# ------------------------------------------------------------------ resolver
def help_target(plugin_id: str, word: str, control_type: str = "") -> tuple[str, str]:
    """Return ("vb", <key>) for the bundled VB reference, ("url", <url>) to open, or ("", "")."""
    w = word.strip()
    if control_type and not w:
        try:                                   # a component package's help.md (radide/components)
            from ..components import help_file
            hf = help_file(control_type)
            if hf:
                return "local", hf
        except Exception:  # noqa: BLE001
            pass
        tk_name, qt_cls = CONTROL_DOCS.get(control_type, ("", ""))
        if plugin_id == "vb-basic" or not plugin_id:
            return "vb", VB_CONTROL_TOPIC.get(control_type, "Caption")
        if plugin_id == "python-qt" and qt_cls:
            return "url", f"https://doc.qt.io/qtforpython-6/PySide6/{qt_module(qt_cls)}/{qt_cls}.html"
        if plugin_id == "ring-qt" and qt_cls:
            return "url", f"https://doc.qt.io/qt-5/{qt_cls.lower()}.html"
        if plugin_id.startswith("python") and tk_name:
            mod = tk_name.split(".")[0]
            if mod in TK_MODULES:
                return "url", f"https://docs.python.org/3/library/tkinter.{mod}.html"
            return "url", f"https://docs.python.org/3/library/tkinter.html#{quote_plus(tk_name)}"
        w = control_type
    if not w:
        return "", ""
    lw = w.lower()
    if plugin_id == "vb-basic":
        key = _VB_LOWER.get(lw) or VB_ALIASES.get(lw)
        if key:
            return "vb", key
        return "url", ("https://learn.microsoft.com/en-us/search/?terms=" + quote_plus(f"VB6 {w}"))
    if plugin_id.startswith("python"):
        if re.match(r"^Q[A-Z]\w+$", w):
            return "url", f"https://doc.qt.io/qtforpython-6/PySide6/{qt_module(w)}/{w}.html"
        if plugin_id == "python-tk":
            if lw in TK_MODULES:
                return "url", f"https://docs.python.org/3/library/tkinter.{lw}.html"
            if lw in TK_WIDGETS or lw == "tkinter":
                return "url", "https://docs.python.org/3/library/tkinter.html#" + ("" if lw == "tkinter" else lw)
        if keyword.iskeyword(w) or w in ("match", "case", "type"):
            page = {"def": "compound_stmts.html#function-definitions", "class": "compound_stmts.html#class-definitions",
                    "if": "compound_stmts.html#the-if-statement", "elif": "compound_stmts.html#the-if-statement",
                    "else": "compound_stmts.html#the-if-statement", "for": "compound_stmts.html#the-for-statement",
                    "while": "compound_stmts.html#the-while-statement", "try": "compound_stmts.html#the-try-statement",
                    "except": "compound_stmts.html#the-try-statement", "finally": "compound_stmts.html#the-try-statement",
                    "with": "compound_stmts.html#the-with-statement", "match": "compound_stmts.html#the-match-statement",
                    "import": "simple_stmts.html#the-import-statement", "from": "simple_stmts.html#the-import-statement",
                    "return": "simple_stmts.html#the-return-statement", "pass": "simple_stmts.html#the-pass-statement",
                    "break": "simple_stmts.html#the-break-statement", "continue": "simple_stmts.html#the-continue-statement",
                    "global": "simple_stmts.html#the-global-statement", "nonlocal": "simple_stmts.html#the-nonlocal-statement",
                    "lambda": "expressions.html#lambda", "yield": "simple_stmts.html#the-yield-statement",
                    "raise": "simple_stmts.html#the-raise-statement", "del": "simple_stmts.html#the-del-statement",
                    "assert": "simple_stmts.html#the-assert-statement", "async": "compound_stmts.html#coroutines",
                    "await": "expressions.html#await"}.get(w, "lexical_analysis.html#keywords")
            return "url", f"https://docs.python.org/3/reference/{page}"
        if hasattr(builtins, w) and not w.startswith("_"):
            obj = getattr(builtins, w)
            if isinstance(obj, type) and issubclass(obj, BaseException):
                return "url", f"https://docs.python.org/3/library/exceptions.html#{w}"
            return "url", f"https://docs.python.org/3/library/functions.html#{w}"
        if w in getattr(sys, "stdlib_module_names", ()):
            return "url", f"https://docs.python.org/3/library/{w}.html"
        return "url", "https://docs.python.org/3/search.html?q=" + quote_plus(w)
    if plugin_id.startswith("ring"):            # ring-qt / ring-game / ring-web
        try:                                    # the exact page of the function / class / keyword (ring_index.py)
            from ..languages import ring_index
            topic = ring_index.doc_topic(w)
            dd = ring_index.docs_dir()
            if topic and dd is not None:
                return "local", str(dd / topic.split("#")[0]) + ("#" + topic.split("#", 1)[1] if "#" in topic else "")
            if topic:
                return "url", f"https://ring-lang.github.io/doc{ring_version()}/{topic}"
        except Exception:  # noqa: BLE001 - fall back to the search below
            pass
        if re.match(r"^q[A-Za-z]\w+$", w, re.I) and w[1:2].isalpha() and lw.startswith("q") and len(w) > 2:
            return "url", f"https://doc.qt.io/qt-5/{lw}.html"
        local = ring_local_docs()
        if local is not None and local.suffix == ".html":
            page = sphinx_lookup(local, w)
            if page:
                return "local", str(local.parent / page)
        return "url", f"https://ring-lang.github.io/doc{ring_version()}/search.html?q={quote_plus(w)}" \
                      "&check_keywords=yes&area=default"
    return "url", "https://www.google.com/search?q=" + quote_plus(f"{plugin_id.split('-')[0]} {w}")


def vb_topic_html(key: str) -> str:
    syntax, desc = VB_REF[key]
    related = sorted(k for k in VB_REF if k != key and k[0] == key[0])[:8]
    rel = ", ".join(f"<a href='vb:{k}'>{k}</a>" for k in related)
    return (f"<h2 style='color:#1F3D7A'>{html.escape(key)}</h2>"
            f"<pre style='background:#F4F4F4;color:#000;padding:6px;border:1px solid #ddd'>{syntax}</pre>"
            f"<p>{desc}</p>" + (f"<p><small>See also: {rel}</small></p>" if rel else "") +
            "<p><small><a href='vb:index'>All VB6 keywords and functions</a></small></p>")


def vb_index_html() -> str:
    items = " &middot; ".join(f"<a href='vb:{k}'>{k}</a>" for k in sorted(VB_REF, key=str.lower))
    return ("<h2 style='color:#1F3D7A'>VB6 language reference</h2><p>Keywords, statements and functions supported "
            f"by the bundled VB6-compatible interpreter:</p><p>{items}</p>")


# ------------------------------------------------------------------ viewer
class HelpViewer(QDialog):
    """Non-modal help window (QTextBrowser) for the IDE manual and the VB reference."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("RAD IDE Help")
        self.resize(820, 640)
        self.browser = QTextBrowser()
        self.browser.setOpenLinks(False)
        self.browser.anchorClicked.connect(self._link)
        self.search = QLineEdit(placeholderText="VB6 keyword or function (Enter)")
        self.search.returnPressed.connect(lambda: self.show_vb(self.search.text().strip()))
        home = QPushButton("Contents")
        home.clicked.connect(self.show_manual)
        keys = QPushButton("Keyboard Shortcuts")
        keys.clicked.connect(self.show_shortcuts)
        vb = QPushButton("VB6 Reference")
        vb.clicked.connect(lambda: self.show_vb("index"))
        ext = QPushButton("Open in Browser")
        ext.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual_page()))))
        bar = QHBoxLayout()
        for b in (home, keys, vb):
            bar.addWidget(b)
        bar.addWidget(self.search, 1)
        bar.addWidget(ext)
        lay = QVBoxLayout(self)
        lay.addLayout(bar)
        lay.addWidget(self.browser, 1)

    def _link(self, url: QUrl):
        s = url.toString()
        if s.startswith("vb:"):
            self.show_vb(s[3:])
        elif s.startswith("#"):
            self.browser.scrollToAnchor(s[1:])
        elif url.isLocalFile() or url.scheme() == "":
            path = Path(url.toLocalFile()) if url.isLocalFile() else HELP_DIR / s.split("#")[0]
            if path.suffix.lower() in (".html", ".htm") and path.exists():
                self.browser.setSource(QUrl.fromLocalFile(str(path)))
            else:
                QDesktopServices.openUrl(url)
        else:
            webbrowser.open(s)

    def show_manual(self):
        page = manual_page()
        if page.exists():
            self.browser.setSearchPaths([str(HELP_DIR)])
            self.browser.setSource(QUrl.fromLocalFile(str(page)))
        else:
            self.browser.setHtml("<h2>RAD IDE</h2><p>The help file is missing.</p>")
        self._raise()

    def show_file(self, target: str):
        """Show a local HTML page (optionally 'page.html#anchor') - the offline Ring manual."""
        path, _, anchor = target.partition("#")
        url = QUrl.fromLocalFile(path)
        if anchor:
            url.setFragment(anchor)
        self.browser.setSearchPaths([str(Path(path).parent)])
        self.browser.setSource(url)
        if anchor:
            self.browser.scrollToAnchor(anchor)
        self._raise()

    def show_vb(self, key: str):
        if key == "index" or not key:
            self.browser.setHtml(vb_index_html())
        else:
            k = _VB_LOWER.get(key.lower()) or VB_ALIASES.get(key.lower())
            if k:
                self.browser.setHtml(vb_topic_html(k))
            else:
                self.browser.setHtml(f"<p>No entry for <b>{html.escape(key)}</b> in the bundled reference.</p>"
                                     + vb_index_html())
        self._raise()

    def show_shortcuts(self):
        self.browser.setHtml(shortcuts_html(self.win))
        self._raise()

    def _raise(self):
        self.show()
        self.raise_()
        self.activateWindow()


def shortcuts_html(win) -> str:
    """Every menu command that has a keyboard shortcut (read live from the menus)."""
    rows = []

    def walk(menu, path):
        for a in menu.actions():
            if a.menu() is not None:
                walk(a.menu(), path + [a.text().replace("&", "")])
            elif not a.isSeparator() and not a.shortcut().isEmpty():
                rows.append((" > ".join(path + [a.text().replace("&", "")]),
                             a.shortcut().toString(QKeySequence.SequenceFormat.NativeText)))
    for top in win.menuBar().actions():
        if top.menu() is not None:
            walk(top.menu(), [top.text().replace("&", "")])
    extra = [("Editor > IntelliSense", "Ctrl+Space"), ("Editor > Parameter info", "Ctrl+Shift+Space"),
             ("Editor > Toggle comment", "Ctrl+/"), ("Terminal > Stop running command", "Ctrl+C"),
             ("Terminal > History", "Up / Down"), ("Git Changes > Commit", "Ctrl+Enter")]
    body = "".join(f"<tr><td>{html.escape(c)}</td><td><b>{html.escape(k)}</b></td></tr>" for c, k in rows + extra)
    return ("<h2 style='color:#1F3D7A'>Keyboard shortcuts</h2><table cellpadding='3' border='0'>"
            f"<tr><th align='left'>Command</th><th align='left'>Keys</th></tr>{body}</table>")


def viewer(win) -> HelpViewer:
    v = getattr(win, "_help_viewer", None)
    if v is None:
        v = win._help_viewer = HelpViewer(win)
    return v


# ------------------------------------------------------------------ F1
def word_at_cursor(editor) -> str:
    try:
        line, col = editor.getCursorPosition()
        text = editor.text(line)
    except Exception:  # noqa: BLE001
        return ""
    sel = ""
    try:
        sel = editor.textCursor().selectedText()
    except Exception:  # noqa: BLE001
        pass
    if sel and re.fullmatch(r"[\w.$]+", sel):
        return sel.split(".")[-1]
    for m in re.finditer(r"[A-Za-z_$][\w$]*", text):
        if m.start() <= col <= m.end():
            return m.group()
    return ""


def _plugin_for_editor(win, editor):
    plugin = getattr(editor, "plugin", None) or win.plugin
    return plugin.id if plugin is not None else ""


def context_help(win):
    """F1: help for the word under the cursor / the selected control."""
    cv = win._current_code() if hasattr(win, "_current_code") else None
    d = win._current_designer() if hasattr(win, "_current_designer") else None
    if cv is not None:
        word = word_at_cursor(cv.editor)
        pid = _plugin_for_editor(win, cv.editor)
        kind, target = help_target(pid, word)
    elif d is not None:
        sel = getattr(d.doc, "selected", None)
        ctype = sel.type if sel is not None else ""
        pid = win.plugin.id if win.plugin else ""
        kind, target = help_target(pid, "", ctype) if ctype else ("", "")
        word = ctype
    else:
        kind, target, word = "", "", ""
    if kind == "vb":
        viewer(win).show_vb(target)
    elif kind == "url":
        win.statusBar().showMessage(f"Help: {word} -> {target}", 6000)
        open_url(target)
    elif kind == "local":
        viewer(win).show_file(target)
    else:
        viewer(win).show_manual()
    return kind, target


def open_url(url: str):
    if os.environ.get("RADIDE_NO_BROWSER"):          # tests
        open_url.last = url
        return
    if url.startswith("file:"):
        QDesktopServices.openUrl(QUrl(url))
    else:
        webbrowser.open(url)


open_url.last = ""


def open_ring_docs(win):
    local = ring_local_docs()
    if local is not None:
        if os.environ.get("RADIDE_NO_BROWSER"):
            open_url.last = str(local)
        else:
            os.startfile(str(local))  # noqa: S606 - local CHM / PDF / HTML manual
    else:
        open_url(f"https://ring-lang.github.io/doc{ring_version()}/index.html")


def install(win) -> None:
    help_menu = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Help"), None)
    if help_menu is None:
        help_menu = win.menuBar().addMenu("&Help")
    first = help_menu.actions()[0] if help_menu.actions() else None

    def act(text, slot, key=None):
        a = QAction(text, win)
        if key:
            a.setShortcut(QKeySequence(key))
        a.triggered.connect(slot)
        return a
    items = [act("RAD IDE &Help", lambda: viewer(win).show_manual(), "Ctrl+F1"),
             act("&Context Help", lambda: context_help(win), "F1"),
             act("&Keyboard Shortcuts", lambda: viewer(win).show_shortcuts()),
             act("&VB6 Language Reference", lambda: viewer(win).show_vb("index")),
             None,
             act("&Python Documentation", lambda: open_url("https://docs.python.org/3/")),
             act("&Tkinter Documentation", lambda: open_url("https://docs.python.org/3/library/tkinter.html")),
             act("Qt for Python (PySide6) Documentation", lambda: open_url("https://doc.qt.io/qtforpython-6/")),
             act("&Ring Documentation", lambda: open_ring_docs(win)),
             act("RingQt / Qt 5 Class Reference", lambda: open_url("https://doc.qt.io/qt-5/classes.html")),
             None]
    for a in items:
        if a is None:
            help_menu.insertSeparator(first)
        else:
            help_menu.insertAction(first, a)
    win.a_context_help = items[1]
    win.addAction(items[1])          # F1 works everywhere in the window


__all__ = ["help_target", "context_help", "HelpViewer", "VB_REF", "word_at_cursor", "viewer"]
