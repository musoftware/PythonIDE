"""Reverse-engineer an existing Python GUI program into a RAD IDE project.

1. The program runs in a subprocess under a capture script (tk_capture.py or
   qt_capture.py) that disables the event loop and dumps every window and
   widget (real geometry, so pack/grid/layouts become absolute positions).
2. This module maps the captured widgets to neutral controls, builds .form
   files, and moves the original callbacks into the new form class
   (widget/variable globals are rewritten to self.<Name>).
"""
from __future__ import annotations

import ast
import json
import keyword
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ..controls import CONTROL_TYPES
from ..languages import get_plugin
from ..model import Control, Form, Project

HERE = Path(__file__).resolve().parent

TK_MAP = {
    "Button": "Button", "TButton": "Button", "Label": "Label", "TLabel": "Label",
    "Entry": "TextBox", "TEntry": "TextBox", "Text": "TextBox",
    "Checkbutton": "CheckBox", "TCheckbutton": "CheckBox",
    "Radiobutton": "RadioButton", "TRadiobutton": "RadioButton",
    "Listbox": "ListBox", "TCombobox": "ComboBox",
    "Frame": "Panel", "TFrame": "Panel", "Labelframe": "GroupBox", "TLabelframe": "GroupBox",
    "Scale": "TrackBar", "TScale": "TrackBar", "Spinbox": "NumericUpDown", "TSpinbox": "NumericUpDown",
    "TProgressbar": "ProgressBar", "Canvas": "PictureBox", "TNotebook": "Panel",
    "Treeview": "ListBox", "Message": "Label",
}
# tk bind sequence -> neutral event
TK_EVENTS = {
    "<Button-1>": "MouseDown", "<ButtonPress-1>": "MouseDown", "<1>": "MouseDown",
    "<ButtonRelease-1>": "Click", "<Double-Button-1>": "DoubleClick", "<Double-1>": "DoubleClick",
    "<Motion>": "MouseMove", "<Enter>": "MouseEnter", "<Leave>": "MouseLeave",
    "<MouseWheel>": "MouseWheel", "<Key>": "KeyDown", "<KeyPress>": "KeyDown",
    "<KeyRelease>": "KeyUp", "<Return>": "KeyDown", "<FocusIn>": "GotFocus",
    "<FocusOut>": "LostFocus", "<<ComboboxSelected>>": "SelectedIndexChanged",
    "<<ListboxSelect>>": "SelectedIndexChanged", "<Configure>": "Resize",
}
COMMAND_EVENT = {"Button": "Click", "CheckBox": "CheckedChanged", "RadioButton": "CheckedChanged",
                 "NumericUpDown": "ValueChanged", "TrackBar": "ValueChanged"}
SKIP_CLASSES = {"Scrollbar", "TScrollbar", "TSeparator", "TSizegrip", "Menubutton", "TMenubutton"}


@dataclass
class ImportReport:
    project: Project | None = None
    forms: int = 0
    controls: int = 0
    handlers: int = 0
    warnings: list[str] = field(default_factory=list)

    def text(self) -> str:
        lines = [f"Imported {self.forms} form(s), {self.controls} control(s), {self.handlers} event handler(s)."]
        if self.warnings:
            lines.append("")
            lines.append("Notes:")
            lines += [f"  - {w}" for w in self.warnings]
        return "\n".join(lines)


# ======================================================================= capture
def detect_toolkit(source: str) -> str:
    if re.search(r"^\s*(from|import)\s+(PySide6|PySide2|PyQt5|PyQt6)\b", source, re.M):
        return "qt"
    if re.search(r"^\s*(from|import)\s+(tkinter|Tkinter|customtkinter|ttkbootstrap)\b", source, re.M):
        return "tk"
    return ""


def run_capture(script: Path, interpreter: str, toolkit: str, timeout: int = 60) -> dict:
    capture = HERE / ("tk_capture.py" if toolkit == "tk" else "qt_capture.py")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "capture.json"
        try:
            import os
            env = dict(os.environ, QT_QPA_PLATFORM="offscreen") if toolkit == "qt" else None
            proc = subprocess.run([interpreter, str(capture), str(script), str(out)],
                                  cwd=str(script.parent), capture_output=True, text=True, env=env,
                                  timeout=timeout, encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            return {"windows": [], "error": f"the program did not reach its event loop within {timeout} s"}
        if not out.exists():
            return {"windows": [], "error": (proc.stderr or proc.stdout or "capture failed")[-2000:]}
        return json.loads(out.read_text(encoding="utf-8"))


# ======================================================================= helpers
def _ident(name: str, fallback: str) -> str:
    name = (name or "").split(".")[-1]
    name = re.sub(r"\W", "_", name)
    if not name or name[0].isdigit() or keyword.iskeyword(name) or name.startswith("_"):
        name = name.lstrip("_")
        if not name or name[0].isdigit() or keyword.iskeyword(name):
            return fallback
    return name


def _hex_ok(c: str) -> str:
    return c if re.fullmatch(r"#[0-9A-Fa-f]{6}", c or "") else ""


DEFAULT_BG = {"#F0F0F0", "#D9D9D9", "#ECECEC", "#FFFFFF"}


# ======================================================================= conversion
class _Converter:
    def __init__(self, capture: dict, report: ImportReport):
        self.cap = capture
        self.report = report
        self.var_alias: dict[str, str] = {}   # python var name -> self.<Ctrl>_var
        self.widget_alias: dict[str, str] = {}  # python widget name -> Ctrl name
        self.handlers: list[tuple[str, str, str]] = []   # (form, handler, original callback)
        self.qt_names: dict[str, tuple[str, str]] = {}   # python name -> (Ctrl, type)
        self.action_names: dict[str, str] = {}             # QAction name -> menu item

    def form_from_window(self, win: dict, form_name: str) -> Form:
        form = Form()
        form.props.update(Name=form_name, Text=win.get("title") or form_name,
                          Width=int(win.get("width") or 400), Height=int(win.get("height") or 300))
        bg = _hex_ok(win.get("bg", ""))
        if bg and bg.upper() not in DEFAULT_BG:
            form.props["BackColor"] = bg
        if win.get("resizable") == [False, False] or win.get("resizable") == [0, 0]:
            form.props["FormBorderStyle"] = "FixedSingle"
        form.props["StartPosition"] = "CenterScreen"
        used: set[str] = {form_name.lower()}
        for ch in win.get("children", []):
            self._add(form, ch, "", used, form_name)
        if win.get("menu"):
            menu = form.add("MenuStrip", 0, 0)
            menu.props["Items"] = self._menu_items(win["menu"], used, form_name, [])
        if win.get("protocol_close"):
            self.handlers.append((form_name, f"{form_name}_FormClosing", win["protocol_close"]))
        for b in win.get("binds", []):
            ev = TK_EVENTS.get(b["sequence"])
            if ev and ev != "Resize" or b["sequence"] == "<Configure>":
                self.handlers.append((form_name, f"{form_name}_{ev or 'Resize'}", b["handler"]))
        return form

    def _menu_items(self, items, used, form_name, path):
        out = []
        for it in items:
            if it.get("Text") == "-":
                out.append({"Text": "-"})
                continue
            words = "".join(re.sub(r"\W", "", w.title()) for w in path + [it.get("Text", "")])
            name = "mnu" + (words or "Item")
            base, i = name, 2
            while name.lower() in used:
                name, i = f"{base}{i}", i + 1
            used.add(name.lower())
            d = {"Text": it.get("Text", ""), "Name": name}
            if it.get("Items"):
                d["Items"] = self._menu_items(it["Items"], used, form_name, path + [it.get("Text", "")])
            elif it.get("handler") and it["handler"] != "<lambda>":
                self.handlers.append((form_name, f"{name}_Click", it["handler"]))
            out.append(d)
        return out

    def _add(self, form: Form, w: dict, parent: str, used: set[str], form_name: str) -> None:
        cls = w.get("class", "")
        if cls in SKIP_CLASSES:
            return
        if not w.get("manager") and cls not in ("Toplevel",):
            return                       # created but never placed/packed/gridded
        ntype = TK_MAP.get(cls)
        if ntype is None:
            ntype = "Panel"
            self.report.warnings.append(f"'{w.get('name') or w.get('tkpath')}' ({cls}) is not supported "
                                        "yet - imported as a Panel placeholder")
        if cls == "Canvas":
            self.report.warnings.append(f"Canvas '{w.get('name') or w.get('tkpath')}' imported as PictureBox "
                                        "(drawings are not converted)")
        if cls == "Treeview":
            self.report.warnings.append(f"Treeview '{w.get('name') or w.get('tkpath')}' imported as ListBox")
        if cls == "TNotebook":
            self.report.warnings.append(f"Notebook '{w.get('name') or w.get('tkpath')}' imported as a Panel "
                                        "(only the visible tab's controls)")
        ctype = CONTROL_TYPES[ntype]
        if cls == "Text" and ntype == "TextBox":
            multiline = True
        else:
            multiline = False
        base = _ident(w.get("name", ""), "")
        name = base or form.unique_name(ctype.prefix)
        if name.lower() in used:
            name = form.unique_name(name)
        used.add(name.lower())
        props = ctype.default_props(name)
        props.update(Left=int(w.get("x", 0)), Top=int(w.get("y", 0)),
                     Width=max(8, int(w.get("width", 20))), Height=max(8, int(w.get("height", 20))),
                     Parent=parent)
        text = w.get("text", "")
        if "Text" in props:
            if ntype == "TextBox":
                text = w.get("current_text", text) if not multiline else w.get("text", "")
                if w.get("textvariable", {}).get("value") not in (None, ""):
                    text = w["textvariable"]["value"]
            props["Text"] = str(text or "")
        if multiline:
            props["Multiline"] = True
        if ntype == "TextBox" and w.get("show"):
            props["PasswordChar"] = w["show"][:1]
        if w.get("state") in ("disabled",):
            props["Enabled"] = False
        if w.get("state") == "readonly" and ntype == "TextBox":
            props["ReadOnly"] = True
        bg, fg = _hex_ok(w.get("bg", "")), _hex_ok(w.get("fg", ""))
        if bg and bg.upper() not in DEFAULT_BG and ntype not in ("TextBox", "ListBox"):
            props["BackColor"] = bg
        if fg and fg.upper() not in ("#000000", "#000000FF") and "ForeColor" in props:
            props["ForeColor"] = fg
        f = w.get("font") or {}
        if f:
            if f.get("family") and f["family"] not in ("Segoe UI", "TkDefaultFont"):
                props["FontName"] = f["family"]
            if f.get("size"):
                props["FontSize"] = int(f["size"])
            props["FontBold"] = bool(f.get("bold"))
            props["FontItalic"] = bool(f.get("italic"))
        if ntype in ("ListBox",) and w.get("items"):
            props["Items"] = ";".join(str(i) for i in w["items"])
        if ntype == "ComboBox":
            vals = w.get("values", "")
            if isinstance(vals, str):
                vals = re.findall(r"\{([^}]*)\}|(\S+)", vals)
                vals = [a or b for a, b in vals]
            props["Items"] = ";".join(str(v) for v in vals)
            props["DropDownStyle"] = "DropDownList" if w.get("state") == "readonly" else "DropDown"
        if ntype == "CheckBox":
            props["Checked"] = bool(w.get("checked"))
        if ntype in ("TrackBar", "NumericUpDown", "ProgressBar"):
            try:
                props["Minimum"] = int(float(w.get("from", 0)))
                props["Maximum"] = int(float(w.get("to", w.get("maximum", 100))))
                v = w.get("value", (w.get("variable") or {}).get("value", 0))
                props["Value"] = int(float(v or 0))
            except (TypeError, ValueError):
                pass
        if ntype == "Label":
            anchor = w.get("anchor", "")
            props["TextAlign"] = "Center" if anchor in ("center", "") else ("Right" if "e" in anchor else "Left")
        ctrl = Control(ntype, props)
        form.controls.append(ctrl)
        self.report.controls += 1
        # names used by the original code -> new names
        if w.get("name"):
            self.widget_alias[w["name"]] = name
        for key in ("textvariable", "variable"):
            v = w.get(key)
            if v and v.get("name") and ntype in ("TextBox", "CheckBox", "NumericUpDown", "TrackBar", "ComboBox"):
                self.var_alias[v["name"]] = f"self.{name}_var"
        # events
        if w.get("command") and w["command"] != "<lambda>":
            ev = COMMAND_EVENT.get(ntype, "Click")
            self.handlers.append((form_name, f"{name}_{ev}", w["command"]))
        elif w.get("command") == "<lambda>":
            self.report.warnings.append(f"'{name}': lambda callback not converted - write its Click handler")
        for b in w.get("binds", []):
            ev = TK_EVENTS.get(b["sequence"])
            if ev and b["handler"] != "<lambda>":
                self.handlers.append((form_name, f"{name}_{ev}", b["handler"]))
            elif not ev:
                self.report.warnings.append(f"'{name}': binding {b['sequence']} has no RAD event equivalent")
        if ctype.container:
            for ch in w.get("children", []):
                self._add(form, ch, name, used, form_name)
        elif w.get("children") and cls == "TNotebook":
            pass


# ======================================================================= Qt
QT_MAP = {
    "QPushButton": "Button", "QToolButton": "Button", "QCommandLinkButton": "Button",
    "QLabel": "Label", "QLineEdit": "TextBox", "QTextEdit": "TextBox", "QPlainTextEdit": "TextBox",
    "QTextBrowser": "TextBox", "QCheckBox": "CheckBox", "QRadioButton": "RadioButton",
    "QListWidget": "ListBox", "QListView": "ListBox", "QComboBox": "ComboBox",
    "QSpinBox": "NumericUpDown", "QDoubleSpinBox": "NumericUpDown", "QSlider": "TrackBar",
    "QDial": "TrackBar", "QProgressBar": "ProgressBar", "QGroupBox": "GroupBox",
    "QFrame": "Panel", "QWidget": "Panel", "QTabWidget": "Panel", "QScrollArea": "Panel",
    "QStackedWidget": "Panel", "QSplitter": "Panel", "QTableWidget": "ListBox", "QTableView": "ListBox",
    "QTreeWidget": "ListBox", "QTreeView": "ListBox", "QDateEdit": "TextBox", "QTimeEdit": "TextBox",
    "QDateTimeEdit": "TextBox", "QLCDNumber": "Label", "QCalendarWidget": "Panel",
}
QT_SIGNALS = {
    "clicked": "Click", "pressed": "MouseDown", "released": "MouseUp", "toggled": "CheckedChanged",
    "stateChanged": "CheckedChanged", "checkStateChanged": "CheckedChanged",
    "textChanged": "TextChanged", "textEdited": "TextChanged", "returnPressed": "KeyDown",
    "editingFinished": "LostFocus", "currentIndexChanged": "SelectedIndexChanged",
    "currentRowChanged": "SelectedIndexChanged", "currentTextChanged": "SelectedIndexChanged",
    "itemSelectionChanged": "SelectedIndexChanged", "activated": "SelectedIndexChanged",
    "itemClicked": "Click", "itemDoubleClicked": "DoubleClick", "doubleClicked": "DoubleClick",
    "valueChanged": "ValueChanged", "sliderMoved": "ValueChanged",
}
APPROX = {"QTableWidget", "QTableView", "QTreeWidget", "QTreeView", "QListView", "QDateEdit",
          "QTimeEdit", "QDateTimeEdit", "QCalendarWidget", "QTabWidget", "QScrollArea",
          "QStackedWidget", "QSplitter", "QLCDNumber", "QDial", "QDoubleSpinBox", "QToolButton"}


def qt_connections(tree: ast.Module) -> list[tuple[str, str, str]]:
    """(sender expression, signal, callback name) for every .signal.connect(callback)."""
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "connect"
                and isinstance(node.func.value, ast.Attribute) and node.args):
            sender = ast.unparse(node.func.value.value)
            signal = node.func.value.attr
            target = node.args[0]
            if isinstance(target, ast.Attribute):
                cb = target.attr
            elif isinstance(target, ast.Name):
                cb = target.id
            else:
                cb = "<lambda>"
            out.append((sender, signal, cb))
    return out


class _QtConverter(_Converter):
    def form_from_window(self, win: dict, form_name: str) -> Form:
        form = Form()
        form.props.update(Name=form_name, Text=win.get("title") or form_name,
                          Width=int(win.get("width") or 400), Height=int(win.get("height") or 300),
                          StartPosition="CenterScreen")
        if win.get("bg"):
            form.props["BackColor"] = win["bg"]
        used: set[str] = {form_name.lower()}
        if win.get("name"):
            self.widget_alias[win["name"]] = "self"
        for ch in win.get("children", []):
            self._add_qt(form, ch, "", used)
        if win.get("menu"):
            menu = form.add("MenuStrip", 0, 0)
            menu.props["Items"] = self._qt_menu(win["menu"], used, [])
        return form

    def _qt_menu(self, items, used, path):
        out = []
        for it in items:
            if it.get("Text") == "-":
                out.append({"Text": "-"})
                continue
            py = (it.get("pyname") or it.get("objectName") or "").split(".")[-1]
            name = _ident(py, "")
            if not name:
                words = "".join(re.sub(r"\W", "", w.title()) for w in path + [it.get("Text", "")])
                name = "mnu" + (words or "Item")
            base, i = name, 2
            while name.lower() in used:
                name, i = f"{base}{i}", i + 1
            used.add(name.lower())
            if it.get("pyname"):
                self.widget_alias[it["pyname"]] = name
                self.action_names[it["pyname"].split(".")[-1]] = name
            d = {"Text": it.get("Text", ""), "Name": name}
            if it.get("Items"):
                d["Items"] = self._qt_menu(it["Items"], used, path + [it.get("Text", "")])
            out.append(d)
        return out

    def _add_qt(self, form: Form, w: dict, parent: str, used: set[str]) -> None:
        cls = w.get("class", "")
        ntype = QT_MAP.get(cls, "Panel")
        label = w.get("name") or w.get("objectName") or cls
        if cls not in QT_MAP:
            self.report.warnings.append(f"'{label}' ({w.get('pyclass') or cls}) is not supported yet - "
                                        "imported as a Panel placeholder")
        elif cls in APPROX:
            self.report.warnings.append(f"'{label}' ({cls}) imported as {ntype} (approximation)")
        if cls == "QLabel" and w.get("has_pixmap"):
            ntype = "PictureBox"
        ctype = CONTROL_TYPES[ntype]
        name = _ident(w.get("name", ""), "") or _ident(w.get("objectName", ""), "")
        if not name or name.lower() in used:
            name = form.unique_name(name or ctype.prefix)
        used.add(name.lower())
        props = ctype.default_props(name)
        props.update(Left=int(w.get("x", 0)), Top=int(w.get("y", 0)),
                     Width=max(8, int(w.get("width", 20))), Height=max(8, int(w.get("height", 20))),
                     Parent=parent, Enabled=bool(w.get("enabled", True)), ToolTip=w.get("tooltip", ""))
        if "Text" in props:
            props["Text"] = str(w.get("text", "") or "")
        if cls in ("QTextEdit", "QPlainTextEdit", "QTextBrowser"):
            props["Multiline"] = True
        if ntype == "TextBox":
            props["ReadOnly"] = bool(w.get("readonly"))
            props["PasswordChar"] = "*" if w.get("password") else ""
            props["MaxLength"] = int(w.get("maxlength") or 0)
        if w.get("bg"):
            props["BackColor"] = w["bg"]
        if w.get("fg") and "ForeColor" in props:
            props["ForeColor"] = w["fg"]
        f = w.get("font") or {}
        if f:
            if f.get("family") and f["family"] not in ("Segoe UI", "MS Shell Dlg 2"):
                props["FontName"] = f["family"]
            props["FontSize"] = int(f.get("size") or 9)
            props["FontBold"] = bool(f.get("bold"))
            props["FontItalic"] = bool(f.get("italic"))
        if ntype in ("ListBox", "ComboBox") and w.get("items"):
            props["Items"] = ";".join(str(i) for i in w["items"])
        if ntype == "ComboBox":
            props["DropDownStyle"] = "DropDown" if w.get("editable") else "DropDownList"
        if ntype in ("CheckBox", "RadioButton"):
            props["Checked"] = bool(w.get("checked"))
        if ntype in ("NumericUpDown", "TrackBar", "ProgressBar"):
            for k in ("minimum", "maximum", "value"):
                if w.get(k) is not None:
                    props[k.capitalize()] = int(w[k])
        if ntype == "Label" and w.get("align"):
            props["TextAlign"] = w["align"]
        form.controls.append(Control(ntype, props))
        self.report.controls += 1
        for key in ("name", "objectName"):
            if w.get(key):
                self.widget_alias.setdefault(w[key], name)
                self.qt_names[w[key].split(".")[-1]] = (name, ntype)
        if ctype.container:
            for ch in w.get("children", []):
                self._add_qt(form, ch, name, used)

    def connect_handlers(self, tree: ast.Module, form_name: str) -> None:
        for sender, signal, cb in qt_connections(tree):
            key = sender.split(".")[-1]
            if signal == "triggered" and key in self.action_names:
                if cb == "<lambda>":
                    self.report.warnings.append(f"menu '{key}': lambda callback not converted")
                    continue
                self.handlers.append((form_name, f"{self.action_names[key]}_Click", cb))
                continue
            target = self.qt_names.get(key)
            ev = QT_SIGNALS.get(signal)
            if target is None or ev is None:
                if target is not None:
                    self.report.warnings.append(f"'{target[0]}': signal '{signal}' has no RAD event equivalent")
                continue
            if cb == "<lambda>":
                self.report.warnings.append(f"'{target[0]}.{signal}': lambda callback not converted")
                continue
            self.handlers.append((form_name, f"{target[0]}_{ev}", cb))


# ======================================================================= code transplant
class _Rewriter(ast.NodeTransformer):
    """Rewrite references to widget/variable globals into self.<Name>."""

    def __init__(self, aliases: dict[str, str]):
        self.aliases = aliases      # "entry" -> "self.txtName" / "self.entry_var"

    def visit_Name(self, node: ast.Name):
        target = self.aliases.get(node.id)
        if target and isinstance(node.ctx, ast.Load):
            expr = ast.parse(target, mode="eval").body
            return ast.copy_location(expr, node)
        return node

    def visit_Attribute(self, node: ast.Attribute):
        dotted = ast.unparse(node)
        if dotted in self.aliases and "." in dotted and isinstance(node.ctx, ast.Load):
            return ast.copy_location(ast.parse(self.aliases[dotted], mode="eval").body, node)
        self.generic_visit(node)
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            target = self.aliases.get(f"self.{node.attr}")
            if target:
                return ast.copy_location(ast.parse(target, mode="eval").body, node)
        return node


def _functions(tree: ast.Module) -> dict[str, tuple[ast.AST, str]]:
    """name -> (node, kind) for module functions and methods of classes."""
    out: dict[str, tuple[ast.AST, str]] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, (node, "function"))
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.setdefault(sub.name, (sub, "method"))
    return out


GUI_CALL = re.compile(r"\b(tk|ttk|tkinter|Tk|Toplevel|Q\w+)\s*[.(]")


def _module_support(tree: ast.Module, handler_names: set[str], source: str) -> tuple[list[str], list[str]]:
    """Imports and helper functions/constants to keep at module level."""
    imports, helpers = [], []
    for node in tree.body:
        seg = ast.get_source_segment(source, node) or ""
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imports.append(seg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name not in handler_names:
            if not re.search(r"\b(tk|ttk)\.\w+\(|\bTk\(\)|mainloop\(", seg):
                helpers.append(seg)
        elif isinstance(node, ast.Assign) and not GUI_CALL.search(seg) and "Var(" not in seg:
            if all(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets):
                helpers.append(seg)       # CONSTANTS
    return imports, helpers


def _method_source(fn: ast.AST, kind: str, aliases: dict[str, str], new_name: str) -> str:
    fn = ast.parse(ast.unparse(fn)).body[0]           # copy
    fn.name = new_name
    args = fn.args
    if kind == "function":                             # becomes a method: add self
        args.args.insert(0, ast.arg(arg="self"))
    # names assigned inside the function (or its parameters) stay local
    local = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
    if fn.args.vararg:
        local.add(fn.args.vararg.arg)
    if fn.args.kwarg:
        local.add(fn.args.kwarg.arg)
    declared_global = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            local.add(n.id)
        elif isinstance(n, ast.Global):
            declared_global |= set(n.names)
    local -= declared_global
    body = _Rewriter({k: v for k, v in aliases.items() if k.split('.')[0] not in local or k.startswith('self.')}).visit(fn)
    ast.fix_missing_locations(body)
    return ast.unparse(body)


def _indent(code: str, n: int = 4) -> str:
    pad = " " * n
    return "\n".join(pad + ln if ln.strip() else ln for ln in code.splitlines())


# ======================================================================= main entry
def import_python_program(script: Path, dest_folder: Path, interpreter: str | None = None,
                          language: str = "python-tk") -> ImportReport:
    report = ImportReport()
    source = script.read_text(encoding="utf-8-sig", errors="replace")
    toolkit = detect_toolkit(source)
    if not toolkit:
        report.warnings.append("No Tkinter or Qt import found in the file.")
        return report
    cap = run_capture(script, interpreter or sys.executable, toolkit)
    if cap.get("error") and not cap.get("windows"):
        report.warnings.append(cap["error"])
        return report
    if cap.get("error"):
        report.warnings.append(cap["error"].splitlines()[-1] if cap["error"] else "")
    if toolkit == "qt" and language == "python-tk":
        language = "python-qt"     # keep Qt code working as-is
    conv = _QtConverter(cap, report) if toolkit == "qt" else _Converter(cap, report)
    windows = cap.get("windows", [])
    forms: list[Form] = []
    for i, win in enumerate(windows):
        forms.append(conv.form_from_window(win, f"Form{i + 1}"))
    report.forms = len(forms)

    # ---- write the project
    dest_folder.mkdir(parents=True, exist_ok=True)
    orig = dest_folder / "_original"
    orig.mkdir(exist_ok=True)
    shutil.copy2(script, orig / script.name)
    plugin = get_plugin(language)
    project = Project(dest_folder, _ident(script.stem, "Imported"), language)
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        tree = ast.Module(body=[], type_ignores=[])
        report.warnings.append(f"could not parse the source for handler code: {e}")
    funcs = _functions(tree)
    if toolkit == "qt":
        for form in forms:
            conv.connect_handlers(tree, form.name)
            break
    aliases: dict[str, str] = {}
    for old, new in conv.widget_alias.items():
        aliases[old] = f"self.{new}"
    aliases.update(conv.var_alias)
    callback_names = {cb for _f, _h, cb in conv.handlers}
    imports, helpers = _module_support(tree, callback_names, source)
    imports = [i for i in imports if not re.match(r"^import\s+tkinter\s+as\s+tk\s*$", i)]
    if toolkit == "qt":
        imports = [i for i in imports if not re.match(r"^(import sys|from (PySide6|PyQt\d|PySide2)\.uic)", i)]

    for form in forms:
        name = form.name
        form.save(project.form_path(name))
        code = plugin.new_code(form, not project.forms)
        project.forms.append(name)
        if not project.startup:
            project.startup = name
        # module level: imports + helpers (first form only)
        if name == forms[0].name and (imports or helpers):
            head = "\n".join(imports) + ("\n\n\n" if imports else "") + "\n\n\n".join(helpers)
            code = code.replace("\n\n\nclass ", "\n" + head.rstrip() + "\n\n\nclass ", 1) if head.strip() else code
        # transplanted callbacks become methods; handlers call them
        added_methods: set[str] = set()
        methods_src: list[str] = []
        for fname, handler, cb in conv.handlers:
            if fname != name:
                continue
            node = funcs.get(cb)
            from ..controls import event_args
            ev = handler.split("_")[-1]
            args = event_args(ev)
            if node is None and cb in ("destroy", "quit"):
                code, line = plugin.add_handler(code, handler, form, args)
                lines = code.splitlines()
                lines[line] = "        self.root.destroy()"
                code = "\n".join(lines) + "\n"
                report.handlers += 1
                continue
            if node is None:
                report.warnings.append(f"{handler}: callback '{cb}' not found in the source")
                continue
            fn, kind = node
            if cb not in added_methods:
                methods_src.append(_method_source(fn, kind, aliases, cb))
                added_methods.add(cb)
            n_params = len(fn.args.args) - (1 if kind == "method" else 0)
            call_arg = "e.raw" if args else "None"
            ctrl_name = handler.rsplit("_", 1)[0]
            ctrl_obj = form.find(ctrl_name)
            if toolkit == "qt" and ctrl_obj is not None and ctrl_obj.type == "ListBox" and not args:
                call_arg = f"self.{ctrl_name}.currentItem()"   # Qt item signals pass the item
            call = f"self.{cb}({call_arg})" if n_params >= 1 else f"self.{cb}()"
            code, line = plugin.add_handler(code, handler, form, args)
            lines = code.splitlines()
            lines[line] = "        " + call
            code = "\n".join(lines) + "\n"
            report.handlers += 1
        if methods_src:
            block = "\n\n    # ---- code moved from the original program ----\n\n" + \
                    "\n\n".join(_indent(m) for m in methods_src) + "\n"
            idx = code.find("\n\nif __name__")
            code = code[:idx] + "\n" + block + code[idx:] if idx >= 0 else code + block
        (dest_folder / plugin.code_file(name)).write_text(code, encoding="utf-8")
        (dest_folder / plugin.designer_file(name)).write_text(plugin.generate_designer(form, code),
                                                             encoding="utf-8")
    project.save()
    report.project = project
    if len(forms) > 1:
        report.warnings.append("Several windows were found; each became a form (Form1 is the startup form).")
    return report
