"""Editor extras: split editor, Diff tool, Hex editor, Snippets manager, macros and keymaps.

- **Split editor** (Window > Split Editor Right / Down, Ctrl+\\ in the editor): the same file in two views of
  one Monaco page. Both views share one text model, so typing in one shows in the other at once.
- **Diff tool** (Tools > Compare): two files, file vs clipboard, file vs saved, file vs Git HEAD, file vs
  another file. Monaco diff editor (radide/web/diff.html): side by side or inline, next / previous change,
  copy a change to the other side (revert / accept hunk), save either side, apply back to the open editor.
- **Hex editor** (File > Open in Hex Editor..., and binary files open there automatically): offset / hex / ASCII
  columns, overwrite or insert, undo / redo, find bytes or text, go to offset, data inspector, save.
- **Snippets** (Tools > Code Snippets Manager...): user snippets per language and global ones in the VS Code
  snippet JSON format (import / export, tab stops $1, placeholders ${1:name}, choices ${1|a,b|}, $0);
  project snippets from <project>/.vscode/*.code-snippets are used too. Edit > Insert Snippet... picks one.
- **Macros** (Tools > Macros): record the keystrokes / editor commands (Ctrl+Shift+R), run the temporary
  macro (Ctrl+Shift+Alt+P), save named macros, Macro Explorer.
- **Keymaps** (Tools > Options > Keyboard): Visual Studio, VS Code, Vim (monaco-vim, bundled in
  radide/web/monaco-vim) and basic Emacs. The multi-cursor keys are the same in every keymap except Vim.

JavaScript side: radide/web/editor_extras.js (window.radex), injected into every Monaco editor page.
"""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import tempfile
import time
import weakref
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QEvent, QObject, QPoint, Qt, QTimer, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QColor, QFont, QFontMetrics, QGuiApplication, QKeySequence, QPainter
from PyQt6.QtWidgets import (QAbstractScrollArea, QApplication, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit, QPushButton,
                             QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QToolBar, QVBoxLayout, QWidget)

WEB = Path(__file__).resolve().parent.parent / "web"
JS_FILE = WEB / "editor_extras.js"
DIFF_HTML = WEB / "diff.html"

KEYMAPS = [("vs", "Visual Studio"), ("vscode", "VS Code"), ("vim", "Vim"), ("emacs", "Emacs (basic)")]
KEYMAP_KEY = "editor/keymap"

_WINS: list = []              # weak references to the windows this feature is installed in
_JS_CACHE: dict = {}


# ============================================================================ helpers
def _is_test() -> bool:
    return QCoreApplication.organizationName().upper().startswith("RADIDE-TEST")


def user_dir() -> Path:
    """Where user snippets and macros live (%LOCALAPPDATA%\\RADIDE\\editor; a temp folder for tests)."""
    if _is_test():
        base = Path(tempfile.gettempdir()) / "RADIDE-TEST" / "editor"
    else:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE" / "editor"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _js_text() -> str:
    st = JS_FILE.stat().st_mtime
    if _JS_CACHE.get("mtime") != st:
        _JS_CACHE["text"] = JS_FILE.read_text(encoding="utf-8")
        _JS_CACHE["mtime"] = st
    return _JS_CACHE["text"]


def _monaco_class():
    try:
        from ..monaco_editor import MonacoEditor
        return MonacoEditor
    except Exception:  # noqa: BLE001 - no QtWebEngine: the builtin editor is used
        return None


def is_monaco(ed) -> bool:
    return ed is not None and hasattr(ed, "_js") and hasattr(ed, "page")


def rx(ed, code: str) -> None:
    """Run *code* in an editor page once window.radex exists (queued until editor_extras.js is injected)."""
    if not is_monaco(ed):
        return
    wrapped = (f"(function(){{var f=function(){{{code}}};"
               f"if(window.radex){{f();}}else{{(window.__radexQ=window.__radexQ||[]).push(f);}}}})();")
    ed._js(wrapped)


def rx_eval(ed, expr: str, callback) -> None:
    """Evaluate a JavaScript expression in a ready editor page and pass the result to *callback*."""
    if not is_monaco(ed):
        callback(None)
        return
    ed.page().runJavaScript(f"(function(){{try{{return {expr};}}catch(e){{return null;}}}})()", callback)


def _ext(win):
    return getattr(win, "_editor_extras", None)


def _win_for(widget):
    w = widget.window() if widget is not None else None
    if w is not None and _ext(w) is not None:
        return w
    for ref in reversed(_WINS):
        w = ref()
        if w is not None:
            return w
    return None


def _editors(win) -> list:
    cls = _monaco_class()
    if cls is None:
        return []
    return [e for e in win.findChildren(cls)]


def current_editor(win):
    """The editor of the current tab (CodeView / ModuleView / web file), or None."""
    w = win.tabs.currentWidget() if hasattr(win, "tabs") else None
    if w is None:
        return None
    ed = getattr(w, "editor", None)
    if ed is not None:
        return ed
    cls = _monaco_class()
    if cls is not None and isinstance(w, cls):
        return w
    return None


def _tab_widget_of(win, widget):
    w = widget
    while w is not None:
        if win.tabs.indexOf(w) >= 0:
            return w
        w = w.parentWidget()
    return None


def _language(path) -> str:
    try:
        from ..monaco_editor import language_for_path
        lang = language_for_path(Path(path))
    except Exception:  # noqa: BLE001
        lang = "plaintext"
    return "plaintext" if lang == "custom" else lang


def _read_text(path: Path) -> tuple[str, bool]:
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    crlf = "\r\n" in text
    return text.replace("\r\n", "\n"), crlf


def _write_text(path: Path, text: str, crlf: bool) -> None:
    data = text.replace("\r\n", "\n")
    if crlf:
        data = data.replace("\n", "\r\n")
    Path(path).write_bytes(data.encode("utf-8"))


def _theme_mod():
    from .. import theme
    return theme


def _style_toolbar(tb: QToolBar):
    tb.setIconSize(tb.iconSize())
    tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)


# ============================================================================ snippets
@dataclass
class Snippet:
    name: str
    prefix: str
    body: str
    description: str = ""
    scope: str = ""            # global snippets: "python,javascript" (empty = every language)
    source: str = "user"       # user | global | project


def _strip_jsonc(text: str) -> str:
    """VS Code snippet files are JSON with comments and trailing commas."""
    out, i, n = [], 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def parse_snippets(text: str, source: str = "user") -> list[Snippet]:
    data = json.loads(_strip_jsonc(text) or "{}")
    out = []
    if not isinstance(data, dict):
        return out
    for name, s in data.items():
        if not isinstance(s, dict) or "body" not in s:
            continue
        body = s.get("body")
        body = "\n".join(str(x) for x in body) if isinstance(body, list) else str(body)
        prefixes = s.get("prefix") or name
        prefixes = [str(p) for p in prefixes] if isinstance(prefixes, list) else [str(prefixes)]
        desc = s.get("description") or ""
        desc = "\n".join(desc) if isinstance(desc, list) else str(desc)
        scope = str(s.get("scope") or "")
        for p in prefixes:
            out.append(Snippet(name, p, body, desc, scope, source))
    return out


def snippets_to_json(snips: list[Snippet], with_scope: bool = False) -> str:
    data: dict = {}
    for s in snips:
        key = s.name
        if key in data:                 # the same name with several prefixes
            pre = data[key]["prefix"]
            data[key]["prefix"] = (pre if isinstance(pre, list) else [pre]) + [s.prefix]
            continue
        item = {"prefix": s.prefix, "body": s.body.split("\n"), "description": s.description}
        if with_scope and s.scope:
            item["scope"] = s.scope
        data[key] = item
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def snippets_dir() -> Path:
    d = user_dir() / "snippets"
    d.mkdir(parents=True, exist_ok=True)
    return d


GLOBAL = "global"


def snippet_file(lang: str) -> Path:
    return snippets_dir() / ("global.code-snippets" if lang == GLOBAL else f"{lang}.json")


def load_snippets(lang: str) -> list[Snippet]:
    p = snippet_file(lang)
    if not p.is_file():
        return []
    try:
        return parse_snippets(p.read_text(encoding="utf-8"), GLOBAL if lang == GLOBAL else "user")
    except (OSError, ValueError):
        return []


def save_snippets(lang: str, snips: list[Snippet]) -> Path:
    p = snippet_file(lang)
    p.write_text(snippets_to_json(snips, with_scope=(lang == GLOBAL)), encoding="utf-8")
    return p


def user_languages() -> list[str]:
    return sorted(p.stem for p in snippets_dir().glob("*.json"))


def project_snippets(folder) -> list[Snippet]:
    out = []
    if not folder:
        return out
    for f in sorted((Path(folder) / ".vscode").glob("*.code-snippets")):
        try:
            out += parse_snippets(f.read_text(encoding="utf-8"), "project")
        except (OSError, ValueError):
            continue
    return out


def snippet_map(project_folder=None) -> dict:
    """languageId ('*' = every language) -> [{name, prefix, body, description}] for editor_extras.js."""
    res: dict = {}

    def add(lang, s):
        res.setdefault(lang, []).append({"name": s.name, "prefix": s.prefix, "body": s.body,
                                         "description": s.description})
    for lang in user_languages():
        for s in load_snippets(lang):
            add(lang, s)
    for s in load_snippets(GLOBAL) + project_snippets(project_folder):
        scopes = [x.strip() for x in s.scope.split(",") if x.strip()] or ["*"]
        for sc in scopes:
            add(sc, s)
    return res


def snippets_for(lang: str, project_folder=None) -> list[dict]:
    m = snippet_map(project_folder)
    return m.get(lang, []) + m.get("*", [])


def known_languages() -> list[str]:
    try:
        from ..monaco_editor import MONACO_LANG
        langs = set(MONACO_LANG.values())
    except Exception:  # noqa: BLE001
        langs = {"python", "javascript", "typescript", "csharp", "java", "html", "css", "php"}
    try:
        from ..languages import all_plugins
        from ..monaco_editor import MONACO_LANG as ML
        for p in all_plugins():
            if ML.get(getattr(p, "code_ext", ""), "custom") == "custom":
                langs.add(f"rad-{p.id}")
    except Exception:  # noqa: BLE001
        pass
    langs.update(user_languages())
    langs.discard("custom")
    return sorted(langs)


class SnippetsDialog(QDialog):
    """Tools > Code Snippets Manager: user snippets per language (VS Code JSON format)."""

    def __init__(self, ext, lang: str | None = None):
        super().__init__(ext.win)
        self.ext = ext
        self.setWindowTitle("Code Snippets Manager")
        self.resize(860, 560)
        self.snips: list[Snippet] = []
        self.dirty = False
        self._loading = False
        top = QHBoxLayout()
        top.addWidget(QLabel("Language:"))
        self.lang = QComboBox()
        self.lang.addItem("Global (all languages, with scope)", GLOBAL)
        for lid in known_languages():
            self.lang.addItem(lid, lid)
        top.addWidget(self.lang, 1)
        b_imp = QPushButton("Import...")
        b_exp = QPushButton("Export...")
        b_imp.clicked.connect(self.import_file)
        b_exp.clicked.connect(self.export_file)
        top.addWidget(b_imp)
        top.addWidget(b_exp)

        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._show)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(self.list, 1)
        row = QHBoxLayout()
        b_new, b_del = QPushButton("New"), QPushButton("Delete")
        b_new.clicked.connect(self.new)
        b_del.clicked.connect(self.delete)
        row.addWidget(b_new)
        row.addWidget(b_del)
        lv.addLayout(row)

        right = QWidget()
        f = QFormLayout(right)
        self.e_name, self.e_prefix, self.e_desc, self.e_scope = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.e_prefix.setPlaceholderText("what you type, e.g. forr  (several: forr, fori)")
        self.e_scope.setPlaceholderText("python,javascript  (empty = every language)")
        self.e_body = QPlainTextEdit()
        mono = QFont("Consolas", 10)
        self.e_body.setFont(mono)
        self.e_body.setPlaceholderText("for ${1:i} in range(${2:10}):\n    $0")
        f.addRow("Name:", self.e_name)
        f.addRow("Prefix:", self.e_prefix)
        f.addRow("Description:", self.e_desc)
        f.addRow("Scope:", self.e_scope)
        f.addRow("Body:", self.e_body)
        hint = QLabel("Tab stops: $1, $2 ... $0 (final caret). Placeholders: ${1:name}. Choices: ${1|one,two|}. "
                      "Variables: $TM_FILENAME, $TM_SELECTED_TEXT, $CLIPBOARD, $CURRENT_YEAR ... "
                      "Files: VS Code snippet JSON, stored in " + str(snippets_dir()))
        hint.setWordWrap(True)
        _theme_mod().role(hint, "muted")
        f.addRow(hint)
        for w in (self.e_name, self.e_prefix, self.e_desc, self.e_scope):
            w.textEdited.connect(self._edited)
        self.e_body.textChanged.connect(self._edited)

        split = QSplitter()
        split.addWidget(left)
        split.addWidget(right)
        split.setSizes([280, 580])
        box = QDialogButtonBox()
        self.b_insert = box.addButton("Insert into Editor", QDialogButtonBox.ButtonRole.ActionRole)
        self.b_save = box.addButton("Save", QDialogButtonBox.ButtonRole.ApplyRole)
        box.addButton(QDialogButtonBox.StandardButton.Close)
        self.b_insert.clicked.connect(self.insert)
        self.b_save.clicked.connect(self.save)
        box.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(split, 1)
        lay.addWidget(box)
        self.lang.currentIndexChanged.connect(self._load)
        if lang:
            i = self.lang.findData(lang)
            if i < 0:
                self.lang.addItem(lang, lang)
                i = self.lang.count() - 1
            self.lang.setCurrentIndex(i)
        self._load()

    # ---------------------------------------------------------------- data
    def current_lang(self) -> str:
        return self.lang.currentData() or GLOBAL

    def _load(self, *_):
        if self.dirty:
            self._commit()
        self.snips_lang = self.current_lang()
        self.snips = self._group(load_snippets(self.snips_lang))
        self.e_scope.setEnabled(self.current_lang() == GLOBAL)
        self._fill()

    def _fill(self, select: int = 0):
        self._loading = True
        self.list.clear()
        for s in self.snips:
            QListWidgetItem(f"{s.prefix}  -  {s.name}", self.list)
        self._loading = False
        if self.snips:
            self.list.setCurrentRow(max(0, min(select, len(self.snips) - 1)))
        else:
            self._show(-1)

    def _show(self, row: int):
        if self._loading:
            return
        self._loading = True
        s = self.snips[row] if 0 <= row < len(self.snips) else None
        for w, v in ((self.e_name, s.name if s else ""), (self.e_prefix, s.prefix if s else ""),
                     (self.e_desc, s.description if s else ""), (self.e_scope, s.scope if s else "")):
            w.setText(v)
        self.e_body.setPlainText(s.body if s else "")
        for w in (self.e_name, self.e_prefix, self.e_desc, self.e_body):
            w.setEnabled(s is not None)
        self._loading = False

    def _edited(self, *_):
        if self._loading:
            return
        row = self.list.currentRow()
        if not 0 <= row < len(self.snips):
            return
        s = self.snips[row]
        s.name = self.e_name.text().strip() or s.prefix
        s.prefix = self.e_prefix.text().strip()
        s.description = self.e_desc.text()
        s.scope = self.e_scope.text().strip()
        s.body = self.e_body.toPlainText()
        it = self.list.item(row)
        if it is not None:
            it.setText(f"{s.prefix}  -  {s.name}")
        self.dirty = True

    @staticmethod
    def _group(snips: list[Snippet]) -> list[Snippet]:
        """One row per snippet name; several prefixes are shown as 'log, clg'."""
        out: dict = {}
        for s in snips:
            if s.name in out:
                out[s.name].prefix += ", " + s.prefix
            else:
                out[s.name] = Snippet(s.name, s.prefix, s.body, s.description, s.scope, s.source)
        return list(out.values())

    @staticmethod
    def _ungroup(snips: list[Snippet]) -> list[Snippet]:
        out = []
        for s in snips:
            for p in [x.strip() for x in s.prefix.split(",") if x.strip()]:
                out.append(Snippet(s.name, p, s.body, s.description, s.scope, s.source))
        return out

    def _commit(self):
        save_snippets(self.snips_lang, self._ungroup([s for s in self.snips if s.prefix and s.body]))
        self.dirty = False
        self.ext.push_snippets()

    def save(self):
        self._commit()
        self.ext.win.statusBar().showMessage(f"Snippets saved: {snippet_file(self.snips_lang)}", 4000)

    def new(self):
        n = 1
        while any(s.prefix == f"snippet{n}" for s in self.snips):
            n += 1
        self.snips.append(Snippet(f"New snippet {n}", f"snippet{n}", "${1:text}$0", ""))
        self.dirty = True
        self._fill(len(self.snips) - 1)
        self.e_prefix.setFocus()

    def delete(self):
        row = self.list.currentRow()
        if 0 <= row < len(self.snips):
            del self.snips[row]
            self.dirty = True
            self._fill(row)

    def import_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Import Snippets", "", "VS Code snippets (*.json *.code-snippets);;All files (*)")
        if f:
            self.import_path(Path(f))

    def import_path(self, path: Path) -> int:
        try:
            new = parse_snippets(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Import Snippets", f"Cannot read {path.name}:\n{e}")
            return 0
        if any(s.scope for s in new) and self.current_lang() != GLOBAL:
            self.lang.setCurrentIndex(self.lang.findData(GLOBAL))
        have = {(s.name, s.prefix) for s in self._ungroup(self.snips)}
        added = [s for s in new if (s.name, s.prefix) not in have]
        self.snips = self._group(self._ungroup(self.snips) + added)
        self.dirty = True
        self.save()
        self._fill(len(self.snips) - 1)
        return len(added)

    def export_file(self):
        f, _ = QFileDialog.getSaveFileName(self, "Export Snippets", f"{self.current_lang()}.code-snippets",
                                           "VS Code snippets (*.code-snippets *.json)")
        if f:
            self.export_path(Path(f))

    def export_path(self, path: Path):
        path.write_text(snippets_to_json(self._ungroup(self.snips), with_scope=True), encoding="utf-8")

    def insert(self):
        row = self.list.currentRow()
        ed = current_editor(self.ext.win)
        if 0 <= row < len(self.snips) and is_monaco(ed):
            rx(ed, f"radex.insertSnippet({json.dumps(self.snips[row].body)});")

    def done(self, r):
        if self.dirty:
            self.save()
        super().done(r)


# ============================================================================ macros
def macros_file() -> Path:
    return user_dir() / "macros.json"


def load_macros() -> dict:
    try:
        data = json.loads(macros_file().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_macros(data: dict) -> None:
    macros_file().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def describe_step(e: dict) -> str:
    t = e.get("t")
    if t == "type":
        return "Type " + json.dumps(e.get("text", ""), ensure_ascii=False)
    if t == "paste":
        return "Paste " + json.dumps(e.get("text", "")[:60], ensure_ascii=False)
    if t in ("cut", "copy"):
        return t.capitalize()
    if t == "cmd":
        return "Command " + str(e.get("id")) + (f" {json.dumps(e['args'])}" if e.get("args") else "")
    return json.dumps(e)


class Macros(QObject):
    """Temporary macro (Ctrl+Shift+R / Ctrl+Shift+Alt+P, as in Visual Studio) and named macros."""
    recordingChanged = pyqtSignal(bool)
    recorded = pyqtSignal(list)

    def __init__(self, ext):
        super().__init__(ext.win)
        self.ext = ext
        self.temp: list = []
        self.rec_editor = None

    def recording(self) -> bool:
        from PyQt6 import sip
        if self.rec_editor is not None and sip.isdeleted(self.rec_editor):
            self.rec_editor = None
        return self.rec_editor is not None

    def toggle(self):
        if self.recording():
            self.stop()
        else:
            self.start()

    def start(self, ed=None):
        ed = ed or current_editor(self.ext.win)
        if not is_monaco(ed):
            self.ext.win.statusBar().showMessage("Macros need the Monaco editor: open a code file first", 4000)
            return False
        rx(ed, "radex.macroStart();")
        self.rec_editor = ed
        self.ext.rec_label.setText("  ● Recording macro (Ctrl+Shift+R to stop)  ")
        self.ext.rec_label.show()
        self.recordingChanged.emit(True)
        return True

    def stop(self, callback=None):
        ed = self.rec_editor
        if not self.recording():
            return
        self.rec_editor = None
        self.ext.rec_label.hide()

        def done(res):
            try:
                self.temp = json.loads(res or "[]")
            except ValueError:
                self.temp = []
            self.ext.win.statusBar().showMessage(f"Macro recorded: {len(self.temp)} step(s). "
                                                 "Ctrl+Shift+Alt+P runs it; Tools > Macros > Save Temporary Macro keeps it.", 6000)
            self.recordingChanged.emit(False)
            self.recorded.emit(self.temp)
            if callback:
                callback(self.temp)
        rx_eval(ed, "radex.macroStop()", done)

    def play(self, events: list | None = None, times: int = 1, ed=None):
        events = self.temp if events is None else events
        ed = ed or current_editor(self.ext.win)
        if not events:
            self.ext.win.statusBar().showMessage("No macro recorded yet (Tools > Macros > Record, Ctrl+Shift+R)", 4000)
            return False
        if not is_monaco(ed):
            return False
        rx(ed, f"radex.macroPlay({json.dumps(events)}, {int(max(1, times))});")
        return True

    def save_temp(self, name: str | None = None) -> str | None:
        if not self.temp:
            QMessageBox.information(self.ext.win, "Macros", "Record a macro first (Ctrl+Shift+R).")
            return None
        if name is None:
            name, ok = QInputDialog.getText(self.ext.win, "Save Temporary Macro", "Macro name:")
            if not ok or not name.strip():
                return None
        data = load_macros()
        data[name.strip()] = {"steps": self.temp, "saved": time.strftime("%Y-%m-%d %H:%M")}
        save_macros(data)
        return name.strip()


class MacroExplorer(QDialog):
    def __init__(self, ext):
        super().__init__(ext.win)
        self.ext = ext
        self.setWindowTitle("Macro Explorer")
        self.resize(720, 440)
        self.list = QListWidget()
        self.steps = QPlainTextEdit()
        self.steps.setReadOnly(True)
        self.steps.setFont(QFont("Consolas", 9))
        self.times = QSpinBox()
        self.times.setRange(1, 10000)
        self.times.setPrefix("x ")
        btns = QVBoxLayout()
        for text, fn in (("Run", self.run), ("Save Temporary As...", self.save_temp), ("Rename...", self.rename),
                         ("Delete", self.delete), ("Import...", self.import_file), ("Export...", self.export_file)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            btns.addWidget(b)
            if text == "Run":
                btns.addWidget(self.times)
        btns.addStretch(1)
        split = QSplitter()
        split.addWidget(self.list)
        split.addWidget(self.steps)
        split.setSizes([240, 420])
        lay = QHBoxLayout(self)
        lay.addWidget(split, 1)
        lay.addLayout(btns)
        self.list.currentRowChanged.connect(self._show)
        self.list.itemDoubleClicked.connect(lambda *_: self.run())
        self.refresh()

    def refresh(self, select: str | None = None):
        self.list.clear()
        QListWidgetItem("(Temporary macro)", self.list).setData(Qt.ItemDataRole.UserRole, None)
        for name in sorted(load_macros()):
            it = QListWidgetItem(name, self.list)
            it.setData(Qt.ItemDataRole.UserRole, name)
            if name == select:
                self.list.setCurrentItem(it)
        if self.list.currentRow() < 0:
            self.list.setCurrentRow(0)

    def _steps_of(self, name):
        return self.ext.macros.temp if name is None else load_macros().get(name, {}).get("steps", [])

    def _current(self):
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _show(self, *_):
        steps = self._steps_of(self._current())
        self.steps.setPlainText("\n".join(f"{i + 1:3}. {describe_step(e)}" for i, e in enumerate(steps)) or "(empty)")

    def run(self):
        steps = self._steps_of(self._current())
        self.ext.macros.play(steps, self.times.value())

    def save_temp(self):
        name = self.ext.macros.save_temp()
        if name:
            self.refresh(name)

    def rename(self):
        old = self._current()
        if old is None:
            return
        new, ok = QInputDialog.getText(self, "Rename Macro", "New name:", text=old)
        if ok and new.strip() and new.strip() != old:
            data = load_macros()
            data[new.strip()] = data.pop(old)
            save_macros(data)
            self.refresh(new.strip())

    def delete(self):
        name = self._current()
        if name is None:
            self.ext.macros.temp = []
        else:
            data = load_macros()
            data.pop(name, None)
            save_macros(data)
        self.refresh()

    def import_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Import Macros", "", "RAD IDE macros (*.json)")
        if f:
            try:
                new = json.loads(Path(f).read_text(encoding="utf-8"))
                data = load_macros()
                data.update({k: v for k, v in new.items() if isinstance(v, dict) and "steps" in v})
                save_macros(data)
            except (OSError, ValueError, AttributeError) as e:
                QMessageBox.warning(self, "Import Macros", str(e))
            self.refresh()

    def export_file(self):
        f, _ = QFileDialog.getSaveFileName(self, "Export Macros", "macros.json", "RAD IDE macros (*.json)")
        if f:
            Path(f).write_text(json.dumps(load_macros(), indent=2, ensure_ascii=False), encoding="utf-8")


# ============================================================================ keymaps
# keys the focused editor must get even when an IDE menu has the same shortcut (ShortcutOverride)
_MULTI = {"Ctrl+Alt+Up", "Ctrl+Alt+Down", "Shift+Alt+.", "Shift+Alt+;", "Shift+Alt+,", "Shift+Alt+I",
          "Ctrl+\\"}
RESERVED = {
    "vscode": _MULTI | {"Ctrl+D", "Ctrl+Shift+L", "Ctrl+U", "Ctrl+L", "Ctrl+Shift+K", "Ctrl+/", "Ctrl+]", "Ctrl+[",
                        "Ctrl+Shift+\\", "Ctrl+Return", "Ctrl+Shift+Return", "Ctrl+K", "Ctrl+I"},
    "vs": _MULTI | {"Ctrl+K", "Ctrl+M", "Ctrl+E", "Ctrl+L", "Ctrl+Shift+L", "Ctrl+D", "Ctrl+]", "Ctrl+U", "Ctrl+Shift+U",
                    "Ctrl+Return", "Ctrl+Shift+Return", "Ctrl+J", "Ctrl+I", "Shift+Alt+Up", "Shift+Alt+Down",
                    "Shift+Alt+Left", "Shift+Alt+Right", "Ctrl+G"},
    "vim": {"Esc", "Ctrl+R", "Ctrl+V", "Ctrl+D", "Ctrl+U", "Ctrl+F", "Ctrl+B", "Ctrl+O", "Ctrl+I", "Ctrl+W",
            "Ctrl+E", "Ctrl+Y", "Ctrl+A", "Ctrl+X", "Ctrl+N", "Ctrl+P", "Ctrl+[", "Ctrl+]", "Ctrl+H", "Ctrl+T",
            "Ctrl+G", "Ctrl+J", "Ctrl+K", "Ctrl+L", "Ctrl+M", "Ctrl+S"},
    "emacs": _MULTI | {"Ctrl+F", "Ctrl+B", "Ctrl+N", "Ctrl+P", "Ctrl+A", "Ctrl+E", "Ctrl+V", "Ctrl+D", "Ctrl+K",
                       "Ctrl+W", "Ctrl+Y", "Ctrl+Space", "Ctrl+G", "Ctrl+/", "Ctrl+X", "Ctrl+S", "Ctrl+R", "Ctrl+L",
                       "Ctrl+O", "Ctrl+T", "Ctrl+Shift+-", "Alt+F", "Alt+B", "Alt+V", "Alt+D", "Alt+W", "Alt+X",
                       "Alt+G", "Alt+U", "Alt+L", "Alt+;", "Alt+Backspace", "Shift+Alt+,", "Shift+Alt+.",
                       "Shift+Alt+5"},
}
# first keys of two-key chords: the second key then belongs to the editor too (Ctrl+K Ctrl+S ...)
CHORD_PREFIX = {"vscode": {"Ctrl+K"}, "vs": {"Ctrl+K", "Ctrl+M", "Ctrl+E"}, "vim": set(),
                "emacs": {"Ctrl+X", "Alt+G"}}

KEYMAP_DOCS = {
    "common": [("Add caret above / below", "Ctrl+Alt+Up / Ctrl+Alt+Down"),
               ("Add caret with the mouse", "Alt+Click"), ("Box (column) selection", "Shift+Alt+Drag"),
               ("Add caret at next match", "Shift+Alt+."), ("Carets at all matches", "Shift+Alt+;"),
               ("Remove last caret", "Shift+Alt+,"), ("Carets at line ends", "Shift+Alt+I"),
               ("Back to one caret", "Esc"), ("Split editor right", "Ctrl+\\")],
    "vscode": [("Add next match (VS Code)", "Ctrl+D"), ("Select all matches", "Ctrl+Shift+L"),
               ("Undo last cursor", "Ctrl+U"), ("Toggle comment", "Ctrl+/"), ("Delete line", "Ctrl+Shift+K"),
               ("Move line", "Alt+Up / Alt+Down"), ("Copy line", "Shift+Alt+Up / Down"),
               ("Command palette (editor)", "F1")],
    "vs": [("Comment / uncomment", "Ctrl+K Ctrl+C / Ctrl+K Ctrl+U"), ("Format document", "Ctrl+K Ctrl+D"),
           ("Line cut / delete", "Ctrl+L / Ctrl+Shift+L"), ("Duplicate", "Ctrl+D"), ("Matching brace", "Ctrl+]"),
           ("Outlining", "Ctrl+M Ctrl+M / Ctrl+M Ctrl+L / Ctrl+M Ctrl+O"), ("Lower / upper case", "Ctrl+U / Ctrl+Shift+U"),
           ("Open line above / below", "Ctrl+Enter / Ctrl+Shift+Enter"), ("List members", "Ctrl+J"),
           ("Insert snippet", "Ctrl+K Ctrl+X"), ("Snippets manager", "Ctrl+K Ctrl+B"),
           ("Box selection", "Shift+Alt+Arrows")],
    "vim": [("Normal / insert / visual", "Esc / i a o / v V Ctrl+V"), ("Save, quit", ":w  :q  :wq  :x"),
            ("Split", ":vs  :sp  :only"), ("Undo / redo", "u / Ctrl+R"), ("Search", "/ ? n N * #"),
            ("Macros (Vim)", "q{reg} ... q, @{reg}"), ("Multi-cursor", "not in Vim mode (use visual block)")],
    "emacs": [("Move", "C-f C-b C-n C-p, M-f M-b, C-a C-e"), ("Page / buffer", "C-v M-v, M-< M->"),
              ("Mark / region", "C-SPC, C-w kill, M-w copy, C-y yank"), ("Kill line", "C-k (repeat appends)"),
              ("Cancel", "C-g"), ("Undo", "C-/  C-x u"), ("Save / kill buffer", "C-x C-s / C-x k"),
              ("Windows", "C-x 2, C-x 3, C-x 1, C-x o"), ("Search / replace", "C-s C-r / M-%"),
              ("M-x / goto line", "M-x / M-g g"), ("Case / comment", "M-u M-l / M-;")],
}

_SHIFTED = {">": ".", "<": ",", ":": ";", '"': "'", "?": "/", "{": "[", "}": "]", "|": "\\", "_": "-", "+": "=",
            "~": "`", "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7", "*": "8", "(": "9",
            ")": "0"}
_MOD_KEYS = {Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta, Qt.Key.Key_AltGr}


def key_text(ev) -> str:
    """'Ctrl+Shift+L', 'Shift+Alt+.' ... for a QKeyEvent (shifted punctuation folded back to its key)."""
    key = ev.key()
    if key in _MOD_KEYS or key == 0:
        return ""
    mods = ev.modifiers()
    if key == Qt.Key.Key_Backtab:
        key = Qt.Key.Key_Tab
    name = QKeySequence(int(key)).toString(QKeySequence.SequenceFormat.PortableText)
    if mods & Qt.KeyboardModifier.ShiftModifier and name in _SHIFTED:
        name = _SHIFTED[name]
    if name == "Enter":
        name = "Return"
    parts = []
    if mods & Qt.KeyboardModifier.ControlModifier:
        parts.append("Ctrl")
    if mods & Qt.KeyboardModifier.ShiftModifier:
        parts.append("Shift")
    if mods & Qt.KeyboardModifier.AltModifier:
        parts.append("Alt")
    if mods & Qt.KeyboardModifier.MetaModifier:
        parts.append("Meta")
    return "+".join(parts + [name])


class _KeyFilter(QObject):
    """Gives the focused Monaco editor the keys of its keymap even when an IDE shortcut has them."""

    def __init__(self, ext):
        super().__init__(ext.win)
        self.ext = ext
        self.chord_until = 0.0

    def _in_editor(self, obj) -> bool:
        cls = _monaco_class()
        if cls is None:
            return False
        w = obj if isinstance(obj, QWidget) else None
        n = 0
        while w is not None and n < 6:
            if isinstance(w, cls):
                return True
            w = w.parentWidget()
            n += 1
        return False

    def eventFilter(self, obj, ev):
        et = ev.type()
        if et != QEvent.Type.ShortcutOverride and et != QEvent.Type.KeyPress:
            return False
        fw = QApplication.focusWidget()
        if fw is None or obj is not fw or not self._in_editor(fw):
            return False
        try:
            if fw.window() is not self.ext.win:
                return False
        except RuntimeError:
            return False
        k = key_text(ev)
        if not k:
            return False
        km = self.ext.keymap
        now = time.monotonic()
        if et == QEvent.Type.KeyPress:
            if k in CHORD_PREFIX.get(km, ()):
                self.chord_until = now + 2.0
            elif self.chord_until:
                self.chord_until = 0.0
            return False
        if self.chord_until and now < self.chord_until:
            ev.accept()                    # second key of an editor chord (Ctrl+K Ctrl+S ...)
            return True
        if k in RESERVED.get(km, ()):
            ev.accept()
            return True
        return False


# ============================================================================ Diff tool
@dataclass
class DiffSide:
    text: str
    title: str
    path: Path | None = None
    editable: bool = False
    editor: object = None          # the open editor of this buffer (changes can be applied back to it)
    crlf: bool = False


class _DiffBridge(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view

    @pyqtSlot()
    def jsReady(self):
        self.view._on_ready()

    @pyqtSlot(str, str)
    def jsChanged(self, side, text):
        self.view._on_changed(side, text)

    @pyqtSlot(str)
    def jsStats(self, js):
        self.view._on_stats(js)


class DiffView(QWidget):
    """A Diff tab: Monaco diff editor with side by side / inline, next / previous change and hunk copy."""
    statsChanged = pyqtSignal(dict)
    ready = pyqtSignal()

    def __init__(self, win, left: DiffSide, right: DiffSide, language: str = "plaintext"):
        super().__init__()
        from PyQt6.QtWebChannel import QWebChannel
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        self.win = win
        self.left, self.right = left, right
        self.language = language
        self.modified = {"left": False, "right": False}
        self.stats = {"count": 0, "current": -1, "added": 0, "removed": 0}
        self._ready = False
        self._pending: list[str] = []
        tb = QToolBar()
        _style_toolbar(tb)
        self.toolbar = tb
        self.a_side = self._act(tb, "Side by Side", self.set_side_by_side, checkable=True, checked=True,
                                tip="Side by side or inline view")
        self.a_ws = self._act(tb, "Ignore Whitespace", lambda on: self.js(f"rdIgnoreWs({json.dumps(on)});"),
                              checkable=True, tip="Ignore leading/trailing whitespace changes")
        tb.addSeparator()
        self._act(tb, "↑ Previous", lambda: self.js("rdNav('previous');"), "Shift+Alt+F5", "Previous change")
        self._act(tb, "↓ Next", lambda: self.js("rdNav('next');"), "Alt+F5", "Next change")
        tb.addSeparator()
        self.a_revert = self._act(tb, "Revert Change →", lambda: self.copy_hunk("toRight"), "Ctrl+Alt+Right",
                                  "Revert this change on the right side (copy the left text to the right)")
        self.a_accept = self._act(tb, "← Accept Change", lambda: self.copy_hunk("toLeft"), "Ctrl+Alt+Left",
                                  "Accept this change into the left side (copy the right text to the left)")
        tb.addSeparator()
        self._act(tb, "Swap Sides", self.swap, tip="Exchange the left and right side")
        self.a_save_left = self._act(tb, "Save Left", lambda: self.save_side("left"), tip="Write the left side to its file")
        self.a_save_right = self._act(tb, "Save Right", lambda: self.save_side("right"),
                                      tip="Write the right side to its file / apply it to the open editor")
        self.info = QLabel()
        self.info.setContentsMargins(8, 0, 8, 0)
        self.titles = QLabel()
        self.titles.setContentsMargins(6, 2, 6, 2)
        _theme_mod().role(self.titles, "muted")
        self.view = QWebEngineView()
        self.bridge = _DiffBridge(self)
        self.channel = QWebChannel(self)
        self.channel.registerObject("radDiff", self.bridge)
        self.view.page().setWebChannel(self.channel)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(tb, 1)
        bar.addWidget(self.info)
        lay.addLayout(bar)
        lay.addWidget(self.titles)
        lay.addWidget(self.view, 1)
        self._update_titles()
        self.view.load(QUrl.fromLocalFile(str(DIFF_HTML)))
        _theme_mod().changed.connect(self._on_theme)

    def _act(self, tb, text, fn, shortcut=None, tip="", checkable=False, checked=False):
        a = QAction(text, self)
        a.setCheckable(checkable)
        if checkable:
            a.setChecked(checked)
            a.toggled.connect(fn)
        else:
            a.triggered.connect(lambda *_: fn())
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
            a.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            tip = f"{tip} ({shortcut})"
        a.setToolTip(tip or text)
        tb.addAction(a)
        self.addAction(a)
        return a

    # ---------------------------------------------------------------- js plumbing
    def js(self, code: str, callback=None):
        if not self._ready:
            self._pending.append(code)
            return
        if callback is None:
            self.view.page().runJavaScript(code)
        else:
            self.view.page().runJavaScript(code, callback)

    def _on_ready(self):
        self._ready = True
        page = self.view.page()
        page.runJavaScript(f"rdSet({json.dumps(self.left.text)}, {json.dumps(self.right.text)}, "
                           f"{json.dumps(self.language)}, {json.dumps(self.left.editable)}, "
                           f"{json.dumps(self.right.editable)});")
        self._on_theme()
        try:
            from .settings import get
            fam, size = get(self.win, "editor_font"), get(self.win, "editor_font_size")
            page.runJavaScript(f"rdFont({json.dumps(fam)}, {int(size) + 3});")
        except Exception:  # noqa: BLE001
            pass
        for c in self._pending:
            page.runJavaScript(c)
        self._pending.clear()
        self.ready.emit()

    def _on_theme(self, *_):
        from PyQt6 import sip
        if sip.isdeleted(self) or not self._ready:
            return
        self.view.page().runJavaScript(f"rdTheme({json.dumps(_theme_mod().monaco_theme())});")

    def _on_changed(self, side, text):
        s = self.left if side == "left" else self.right
        if s.text == text:
            return
        s.text = text
        self.modified[side] = True
        self._update_titles()

    def _on_stats(self, js):
        try:
            self.stats = json.loads(js)
        except ValueError:
            return
        n, cur = self.stats.get("count", 0), self.stats.get("current", -1)
        where = f"change {cur + 1} of {n}" if n and cur >= 0 else ("no differences" if not n else f"{n} changes")
        self.info.setText(f"{where}   +{self.stats.get('added', 0)} -{self.stats.get('removed', 0)}")
        self.statsChanged.emit(self.stats)

    def _update_titles(self):
        def t(s, side):
            mark = "*" if self.modified[side] else ""
            ro = "" if s.editable else " (read-only)"
            return f"{s.title}{mark}{ro}"
        self.titles.setText(f"Left: {t(self.left, 'left')}      ↔      Right: {t(self.right, 'right')}")
        self.a_save_left.setEnabled(self.left.editable and (self.left.path is not None or self.left.editor is not None))
        self.a_save_right.setEnabled(self.right.editable and (self.right.path is not None or self.right.editor is not None))
        i = self.win.tabs.indexOf(self)
        if i >= 0:
            base = self.win.tabs.tabText(i).rstrip("*")
            self.win.tabs.setTabText(i, base + ("*" if self.is_modified() else ""))

    # ---------------------------------------------------------------- commands
    def set_side_by_side(self, on: bool):
        self.js(f"rdSideBySide({json.dumps(bool(on))});")

    def copy_hunk(self, direction: str, index: int | None = None):
        dst = self.right if direction == "toRight" else self.left
        if not dst.editable:
            if direction == "toLeft":            # read-only left (HEAD / saved): accept = keep it, go on
                self.js("rdNav('next');")
            return
        self.js(f"rdHunk({json.dumps(direction)}, {json.dumps(index)});")

    def swap(self):
        self.left, self.right = self.right, self.left
        self.modified = {"left": self.modified["right"], "right": self.modified["left"]}
        self.js(f"rdSet({json.dumps(self.left.text)}, {json.dumps(self.right.text)}, {json.dumps(self.language)}, "
                f"{json.dumps(self.left.editable)}, {json.dumps(self.right.editable)});")
        self._update_titles()

    def set_texts(self, left: str | None = None, right: str | None = None):
        if left is not None:
            self.left.text = left
            self.js(f"rdSetSide('left', {json.dumps(left)});")
        if right is not None:
            self.right.text = right
            self.js(f"rdSetSide('right', {json.dumps(right)});")

    def save_side(self, side: str) -> bool:
        s = self.left if side == "left" else self.right
        if not s.editable:
            return False
        ed = s.editor
        from PyQt6 import sip
        if ed is not None and not sip.isdeleted(ed):
            if ed.toPlainText() != s.text:
                bps = ed.breakpoints() if hasattr(ed, "breakpoints") else []
                ed.setText(s.text)
                if hasattr(ed, "set_breakpoints"):
                    ed.set_breakpoints([b for b in bps if b < ed.lines()])
            self.modified[side] = False
            self._update_titles()
            self.win.statusBar().showMessage(f"Applied to the editor of {s.title} (save it with Ctrl+S)", 4000)
            return True
        if s.path is None:
            return False
        try:
            _write_text(s.path, s.text, s.crlf)
        except OSError as e:
            QMessageBox.warning(self, "Diff", f"Cannot save {s.path}:\n{e}")
            return False
        self.modified[side] = False
        self._update_titles()
        self.win.statusBar().showMessage(f"Saved {s.path}", 3000)
        return True

    def is_modified(self) -> bool:
        return any(self.modified[k] and (self.left if k == "left" else self.right).editable for k in self.modified)

    def save(self):
        for side in ("left", "right"):
            if self.modified[side]:
                self.save_side(side)

    def maybe_close(self) -> bool:
        if not self.is_modified():
            return True
        r = QMessageBox.question(self, "Diff", "Save the changes made in the comparison?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        if r == QMessageBox.StandardButton.Save:
            self.save()
        return True


def git_head_text(path: Path) -> tuple[str | None, str]:
    """(text of the file at HEAD, error)."""
    path = Path(path).resolve()
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        r = subprocess.run(["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"], capture_output=True,
                           text=True, timeout=15, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, f"git is not available: {e}"
    if r.returncode != 0:
        return None, "This file is not in a Git repository."
    root = Path(r.stdout.strip()).resolve()
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return None, "The file is outside the repository."
    r = subprocess.run(["git", "-C", str(root), "show", f"HEAD:{rel}"], capture_output=True, timeout=15,
                       creationflags=flags)
    if r.returncode != 0:
        return None, (r.stderr.decode("utf-8", "replace").strip() or "The file is not in HEAD (new file?).")
    raw = r.stdout
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    return text.replace("\r\n", "\n"), ""


def open_diff(win, left: DiffSide, right: DiffSide, title: str | None = None, language: str | None = None) -> DiffView:
    lang = language or _language(right.path or left.path or "x.txt")
    view = DiffView(win, left, right, lang)
    title = title or f"{left.title} ↔ {right.title}"
    if hasattr(win, "_show_tab"):
        win._show_tab(view, title)
    else:
        win.tabs.setCurrentIndex(win.tabs.addTab(view, title))
    win.tabs.setTabToolTip(win.tabs.indexOf(view), f"Diff: {left.title}  ↔  {right.title}")
    return view


def _editor_path(ed):
    p = getattr(ed, "path", None)
    return Path(p) if p else None


def _buffer_side(ed, title_suffix=" (editor)") -> DiffSide:
    p = _editor_path(ed)
    return DiffSide(ed.toPlainText(), (p.name if p else "editor") + title_suffix, p, True, ed)


def compare_files(win, a: Path | None = None, b: Path | None = None):
    if a is None:
        start = str(win.project.folder) if getattr(win, "project", None) is not None else ""
        f1, _ = QFileDialog.getOpenFileName(win, "Compare Files - first (left) file", start, "All files (*)")
        if not f1:
            return None
        f2, _ = QFileDialog.getOpenFileName(win, "Compare Files - second (right) file", str(Path(f1).parent), "All files (*)")
        if not f2:
            return None
        a, b = Path(f1), Path(f2)
    ta, ca = _read_text(a)
    tb, cb = _read_text(b)
    return open_diff(win, DiffSide(ta, a.name, a, True, None, ca), DiffSide(tb, b.name, b, True, None, cb))


def _need_editor(win):
    ed = current_editor(win)
    if ed is None:
        QMessageBox.information(win, "Compare", "Open a code file in the editor first.")
    return ed


def compare_with_clipboard(win, clip: str | None = None):
    ed = _need_editor(win)
    if ed is None:
        return None
    clip = QGuiApplication.clipboard().text() if clip is None else clip
    return open_diff(win, DiffSide(clip.replace("\r\n", "\n"), "Clipboard", None, True), _buffer_side(ed),
                     title=f"Clipboard ↔ {(_editor_path(ed) or Path('editor')).name}")


def compare_with_saved(win):
    ed = _need_editor(win)
    if ed is None:
        return None
    p = _editor_path(ed)
    if p is None or not p.is_file():
        QMessageBox.information(win, "Compare", "This file has not been saved yet.")
        return None
    text, crlf = _read_text(p)
    return open_diff(win, DiffSide(text, f"{p.name} (saved)", p, False, None, crlf), _buffer_side(ed),
                     title=f"{p.name}: saved ↔ editor")


def compare_with_head(win):
    ed = _need_editor(win)
    if ed is None:
        return None
    p = _editor_path(ed)
    if p is None:
        return None
    text, err = git_head_text(p)
    if text is None:
        QMessageBox.information(win, "Compare with Git HEAD", err)
        return None
    return open_diff(win, DiffSide(text, f"{p.name} (HEAD)", None, False), _buffer_side(ed),
                     title=f"{p.name}: HEAD ↔ editor")


def compare_with_file(win, other: Path | None = None):
    ed = _need_editor(win)
    if ed is None:
        return None
    if other is None:
        p = _editor_path(ed)
        f, _ = QFileDialog.getOpenFileName(win, "Compare With...", str(p.parent) if p else "", "All files (*)")
        if not f:
            return None
        other = Path(f)
    text, crlf = _read_text(other)
    return open_diff(win, DiffSide(text, other.name, other, True, None, crlf), _buffer_side(ed))


# ============================================================================ Hex editor
BINARY_EXT = {".exe", ".dll", ".bin", ".dat", ".obj", ".o", ".a", ".lib", ".so", ".dylib", ".class", ".pyc", ".pyd",
              ".zip", ".7z", ".gz", ".tar", ".rar", ".jar", ".apk", ".ocx", ".sys", ".iso", ".img", ".wasm",
              ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp3", ".wav", ".ogg", ".mp4", ".avi", ".res", ".frx",
              ".ctx", ".pak", ".dex", ".cab", ".msi", ".pdb", ".exp", ".ilk", ".idb", ".beam", ".rlib"}
NOT_HEX_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg", ".tif", ".tiff",
               ".db", ".sqlite", ".sqlite3", ".db3", ".sdb", ".pdf"}


def is_binary(path: Path) -> bool:
    p = Path(path)
    if p.suffix.lower() in BINARY_EXT:
        return True
    try:
        with open(p, "rb") as f:
            head = f.read(8192)
    except OSError:
        return False
    return b"\0" in head


def should_open_hex(path) -> bool:
    p = Path(path)
    return p.is_file() and p.suffix.lower() not in NOT_HEX_EXT and is_binary(p)


def parse_hex(text: str) -> bytes:
    t = re.sub(r"0x", "", text.strip(), flags=re.I)
    t = re.sub(r"[\s,;:\-]", "", t)
    if len(t) % 2:
        raise ValueError("odd number of hex digits")
    return bytes.fromhex(t)


def parse_offset(text: str) -> int:
    t = text.strip().lower().replace("_", "")
    if t.startswith("0x"):
        return int(t[2:], 16)
    if t.endswith("h"):
        return int(t[:-1], 16)
    if re.fullmatch(r"[0-9]+", t):
        return int(t)
    return int(t, 16)


class HexView(QAbstractScrollArea):
    """Offset / hex / ASCII view with editing (overwrite or insert), selection, undo / redo."""
    changed = pyqtSignal()
    cursorMoved = pyqtSignal(int)
    requestFind = pyqtSignal()
    requestGoto = pyqtSignal()
    requestSave = pyqtSignal()
    findNext = pyqtSignal(bool)

    def __init__(self, data: bytes = b"", parent=None):
        super().__init__(parent)
        self.data = bytearray(data)
        self.cols = 16
        self.cursor = 0
        self.nibble = 0                  # 0 = high, 1 = low (hex pane)
        self.anchor: int | None = None
        self.pane = "hex"
        self.insert_mode = False
        self.undo_stack: list = []
        self.redo_stack: list = []
        self.saved_level = 0
        f = QFont("Consolas", 10)
        f.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(f)
        self.viewport().setFont(f)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
        self._metrics()
        _theme_mod().changed.connect(lambda *_: self.viewport().update())

    # ---------------------------------------------------------------- geometry
    def _metrics(self):
        fm = QFontMetrics(self.font())
        self.cw = fm.horizontalAdvance("0")
        self.lh = fm.height() + 2
        self.ascent = fm.ascent()
        self.x_off = 6
        self.x_hex = self.x_off + 10 * self.cw
        self.x_ascii = self.x_hex + (self.cols * 3 + 2) * self.cw
        self.header = self.lh + 4

    def rows(self) -> int:
        return len(self.data) // self.cols + 1

    def visible_rows(self) -> int:
        return max(1, (self.viewport().height() - self.header) // self.lh)

    def _update_scroll(self):
        sb = self.verticalScrollBar()
        sb.setRange(0, max(0, self.rows() - self.visible_rows()))
        sb.setPageStep(self.visible_rows())
        w = self.x_ascii + self.cols * self.cw + 12
        self.horizontalScrollBar().setRange(0, max(0, w - self.viewport().width()))
        self.horizontalScrollBar().setPageStep(self.viewport().width())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._update_scroll()

    def hex_x(self, col: int) -> int:
        return self.x_hex + col * 3 * self.cw + (self.cw if col >= 8 else 0)

    def sizeHint(self):
        from PyQt6.QtCore import QSize
        return QSize(self.x_ascii + self.cols * self.cw + 30, 400)

    # ---------------------------------------------------------------- painting
    def paintEvent(self, _e):
        T = _theme_mod()
        p = QPainter(self.viewport())
        p.setFont(self.font())
        vw, vh = self.viewport().width(), self.viewport().height()
        p.fillRect(0, 0, vw, vh, QColor(T.color("base")))
        dx = -self.horizontalScrollBar().value()
        p.translate(dx, 0)
        text, muted = QColor(T.color("text")), QColor(T.color("muted"))
        hl, hl_text = QColor(T.color("highlight")), QColor(T.color("highlight_text"))
        alt = QColor(T.color("alt_base"))
        p.fillRect(-dx, 0, vw, self.header - 2, QColor(T.color("header")))
        p.setPen(QColor(T.color("header_text")))
        p.drawText(self.x_off, self.ascent + 2, "Offset")
        for c in range(self.cols):
            p.drawText(self.hex_x(c), self.ascent + 2, f"{c:02X}")
        p.drawText(self.x_ascii, self.ascent + 2, "ASCII")
        first = self.verticalScrollBar().value()
        sel = self.selection()
        n = len(self.data)
        for r in range(self.visible_rows() + 1):
            row = first + r
            base = row * self.cols
            if base > n:
                break
            y = self.header + r * self.lh
            if row % 2:
                p.fillRect(-dx, y, vw, self.lh, alt)
            p.setPen(muted)
            p.drawText(self.x_off, y + self.ascent, f"{base:08X}")
            for c in range(self.cols):
                i = base + c
                if i > n or (i == n and i != self.cursor):
                    break
                hx, ax = self.hex_x(c), self.x_ascii + c * self.cw
                if sel and sel[0] <= i < sel[1]:
                    p.fillRect(hx - 1, y, 2 * self.cw + 2, self.lh, hl)
                    p.fillRect(ax, y, self.cw, self.lh, hl)
                if i == self.cursor:
                    cur = QColor(T.color("accent"))
                    if self.pane == "hex":
                        p.fillRect(hx + self.nibble * self.cw, y + self.lh - 3, self.cw, 2, cur)
                        p.setPen(cur)
                        p.drawRect(ax, y, self.cw - 1, self.lh - 1)
                    else:
                        p.fillRect(ax, y + self.lh - 3, self.cw, 2, cur)
                        p.setPen(cur)
                        p.drawRect(hx - 1, y, 2 * self.cw + 1, self.lh - 1)
                if i == n:
                    continue
                b = self.data[i]
                selected = bool(sel and sel[0] <= i < sel[1])
                p.setPen(hl_text if selected else (muted if b == 0 else text))
                p.drawText(hx, y + self.ascent, f"{b:02X}")
                ch = chr(b) if 32 <= b < 127 else "."
                p.setPen(hl_text if selected else (text if 32 <= b < 127 else muted))
                p.drawText(ax, y + self.ascent, ch)
        p.setPen(QColor(T.color("border")))
        p.drawLine(self.x_hex - self.cw, 0, self.x_hex - self.cw, vh)
        p.drawLine(self.x_ascii - self.cw, 0, self.x_ascii - self.cw, vh)
        p.end()

    # ---------------------------------------------------------------- selection / cursor
    def selection(self):
        if self.anchor is None or self.anchor == self.cursor:
            return None
        a, b = sorted((self.anchor, self.cursor))
        return (a, b + 1) if b < len(self.data) else (a, b)

    def set_cursor(self, i: int, extend: bool = False, nibble: int = 0):
        i = max(0, min(i, len(self.data)))
        if extend:
            if self.anchor is None:
                self.anchor = self.cursor
        else:
            self.anchor = None
        self.cursor = i
        self.nibble = nibble
        self.ensure_visible()
        self.viewport().update()
        self.cursorMoved.emit(i)

    def select(self, start: int, length: int):
        self.anchor = start
        self.cursor = max(start, start + length - 1)
        self.ensure_visible()
        self.viewport().update()
        self.cursorMoved.emit(self.cursor)

    def ensure_visible(self):
        row = self.cursor // self.cols
        sb = self.verticalScrollBar()
        self._update_scroll()
        if row < sb.value():
            sb.setValue(row)
        elif row >= sb.value() + self.visible_rows():
            sb.setValue(row - self.visible_rows() + 1)

    def _hit(self, pos: QPoint):
        x = pos.x() + self.horizontalScrollBar().value()
        row = self.verticalScrollBar().value() + max(0, (pos.y() - self.header)) // self.lh
        if x >= self.x_ascii - self.cw // 2:
            col = max(0, min(self.cols - 1, (x - self.x_ascii) // self.cw))
            return row * self.cols + col, "ascii", 0
        for c in range(self.cols):
            hx = self.hex_x(c)
            if x < hx + 2 * self.cw + self.cw // 2:
                return row * self.cols + c, "hex", 1 if x >= hx + self.cw else 0
        return row * self.cols + self.cols - 1, "hex", 0

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        i, pane, nib = self._hit(e.position().toPoint())
        self.pane = pane
        self.set_cursor(i, bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier), nib)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            i, _pane, _nib = self._hit(e.position().toPoint())
            self.set_cursor(i, True)

    def wheelEvent(self, e):
        sb = self.verticalScrollBar()
        sb.setValue(sb.value() - e.angleDelta().y() // 40)

    def scrollContentsBy(self, dx, dy):
        self.viewport().update()

    # ---------------------------------------------------------------- editing
    def replace(self, offset: int, old_len: int, new: bytes, merge: bool = False):
        old = bytes(self.data[offset:offset + old_len])
        if old == new:
            return
        self.data[offset:offset + old_len] = new
        self.undo_stack.append((offset, old, bytes(new)))
        self.redo_stack.clear()
        self._update_scroll()
        self.viewport().update()
        self.changed.emit()

    def undo(self):
        if not self.undo_stack:
            return
        off, old, new = self.undo_stack.pop()
        self.data[off:off + len(new)] = old
        self.redo_stack.append((off, old, new))
        self.set_cursor(off)
        self._update_scroll()
        self.changed.emit()

    def redo(self):
        if not self.redo_stack:
            return
        off, old, new = self.redo_stack.pop()
        self.data[off:off + len(old)] = new
        self.undo_stack.append((off, old, new))
        self.set_cursor(off + len(new))
        self._update_scroll()
        self.changed.emit()

    def is_modified(self) -> bool:
        return len(self.undo_stack) != self.saved_level or bool(self.redo_stack and self.saved_level > len(self.undo_stack))

    def mark_saved(self):
        self.saved_level = len(self.undo_stack)
        self.changed.emit()

    def delete_selection(self) -> bool:
        s = self.selection()
        if not s:
            return False
        self.replace(s[0], s[1] - s[0], b"")
        self.set_cursor(s[0])
        return True

    def type_hex(self, digit: int):
        if self.delete_selection() and not self.insert_mode:
            pass
        i = self.cursor
        if i >= len(self.data) or (self.insert_mode and self.nibble == 0):
            self.replace(i, 0, bytes([digit << 4]))
            self.set_cursor(i, nibble=1)
            return
        b = self.data[i]
        nb = (digit << 4) | (b & 0x0F) if self.nibble == 0 else (b & 0xF0) | digit
        self.replace(i, 1, bytes([nb]))
        if self.nibble == 0:
            self.set_cursor(i, nibble=1)
        else:
            self.set_cursor(i + 1, nibble=0)

    def type_char(self, ch: str):
        bs = ch.encode("latin-1", errors="replace")[:1]
        if not bs:
            return
        self.delete_selection()
        i = self.cursor
        if self.insert_mode or i >= len(self.data):
            self.replace(i, 0, bs)
        else:
            self.replace(i, 1, bs)
        self.set_cursor(i + 1)

    def selected_bytes(self) -> bytes:
        s = self.selection()
        return bytes(self.data[s[0]:s[1]]) if s else b""

    def copy(self):
        b = self.selected_bytes()
        if not b and self.cursor < len(self.data):
            b = bytes(self.data[self.cursor:self.cursor + 1])
        QGuiApplication.clipboard().setText(" ".join(f"{x:02X}" for x in b) if self.pane == "hex"
                                            else b.decode("latin-1"))

    def paste(self):
        t = QGuiApplication.clipboard().text()
        if not t:
            return
        try:
            bs = parse_hex(t) if self.pane == "hex" else t.encode("latin-1", errors="replace")
        except ValueError:
            bs = t.encode("utf-8")
        self.delete_selection()
        i = self.cursor
        if self.insert_mode:
            self.replace(i, 0, bs)
        else:
            self.replace(i, min(len(bs), len(self.data) - i), bs)
        self.set_cursor(i + len(bs))

    _OWN_KEYS = {"Ctrl+Z", "Ctrl+Y", "Ctrl+Shift+Z", "Ctrl+C", "Ctrl+V", "Ctrl+X", "Ctrl+A", "Ctrl+G", "Ctrl+F",
                 "F3", "Shift+F3", "Ctrl+S", "Ins", "Del", "Backspace", "Tab", "Home", "End", "Ctrl+Home", "Ctrl+End"}

    def event(self, e):
        if e.type() == QEvent.Type.ShortcutOverride and key_text(e) in self._OWN_KEYS:
            e.accept()
            return True
        return super().event(e)

    def focusNextPrevChild(self, _next):
        return False

    def keyPressEvent(self, e):
        k = key_text(e)
        cols = self.cols
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        nav = {"Left": -1, "Right": 1, "Up": -cols, "Down": cols,
               "PgUp": -cols * self.visible_rows(), "PgDown": cols * self.visible_rows()}
        base = k.replace("Shift+", "")
        if base in nav:
            if self.pane == "hex" and base in ("Left", "Right") and not shift:
                if base == "Right" and self.nibble == 0 and self.cursor < len(self.data):
                    self.set_cursor(self.cursor, nibble=1)
                    return
                if base == "Left" and self.nibble == 1:
                    self.set_cursor(self.cursor, nibble=0)
                    return
            self.set_cursor(self.cursor + nav[base], shift)
            return
        if base == "Home":
            self.set_cursor(self.cursor - self.cursor % cols, shift)
        elif base == "End":
            self.set_cursor(min(len(self.data), self.cursor - self.cursor % cols + cols - 1), shift)
        elif base == "Ctrl+Home":
            self.set_cursor(0, shift)
        elif base == "Ctrl+End":
            self.set_cursor(len(self.data), shift)
        elif k == "Tab":
            self.pane = "ascii" if self.pane == "hex" else "hex"
            self.nibble = 0
            self.viewport().update()
        elif k == "Ins":
            self.insert_mode = not self.insert_mode
            self.cursorMoved.emit(self.cursor)
        elif k in ("Del", "Backspace"):
            if self.delete_selection():
                return
            if k == "Backspace" and self.cursor > 0:
                self.replace(self.cursor - 1, 1, b"")
                self.set_cursor(self.cursor - 1)
            elif k == "Del" and self.cursor < len(self.data):
                self.replace(self.cursor, 1, b"")
                self.set_cursor(self.cursor)
        elif k in ("Ctrl+Z",):
            self.undo()
        elif k in ("Ctrl+Y", "Ctrl+Shift+Z"):
            self.redo()
        elif k == "Ctrl+C":
            self.copy()
        elif k == "Ctrl+X":
            self.copy()
            self.delete_selection()
        elif k == "Ctrl+V":
            self.paste()
        elif k == "Ctrl+A":
            self.anchor = 0
            self.set_cursor(len(self.data), True)
        elif k == "Ctrl+F":
            self.requestFind.emit()
        elif k == "Ctrl+G":
            self.requestGoto.emit()
        elif k == "Ctrl+S":
            self.requestSave.emit()
        elif k in ("F3", "Shift+F3"):
            self.findNext.emit(k == "Shift+F3")
        else:
            t = e.text()
            if t and not (e.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier)):
                if self.pane == "hex":
                    if t.lower() in "0123456789abcdef" and len(t) == 1:
                        self.type_hex(int(t, 16))
                elif t.isprintable():
                    self.type_char(t)
                return
            super().keyPressEvent(e)

    # ---------------------------------------------------------------- search
    def find(self, pattern: bytes, start: int | None = None, backwards: bool = False) -> int:
        if not pattern:
            return -1
        data = bytes(self.data)
        if backwards:
            s = self.cursor - 1 if start is None else start
            i = data.rfind(pattern, 0, max(0, s) + len(pattern) - 1) if s >= 0 else -1
            if i < 0:
                i = data.rfind(pattern)
        else:
            s = (self.cursor + 1 if self.selection() else self.cursor) if start is None else start
            i = data.find(pattern, s)
            if i < 0:
                i = data.find(pattern)
        if i >= 0:
            self.select(i, len(pattern))
        return i


class HexEditorView(QWidget):
    """Hex editor tab (File > Open in Hex Editor...). Has save() / maybe_close() for the IDE's File menu."""
    modificationChanged = pyqtSignal(bool)

    def __init__(self, win, path: Path):
        super().__init__()
        self.win = win
        self.path = Path(path)
        data = self.path.read_bytes()
        self.hex = HexView(data)
        tb = QToolBar()
        _style_toolbar(tb)
        tb.addAction("Save", self.save).setToolTip("Save (Ctrl+S)")
        tb.addAction("Save As...", self.save_as)
        tb.addSeparator()
        tb.addAction("Undo", self.hex.undo).setToolTip("Undo (Ctrl+Z)")
        tb.addAction("Redo", self.hex.redo).setToolTip("Redo (Ctrl+Y)")
        tb.addSeparator()
        tb.addAction("Go to Offset...", self.goto).setToolTip("Go to offset (Ctrl+G): 0x1F0, 1F0h or 496")
        tb.addSeparator()
        tb.addWidget(QLabel(" Find: "))
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("DE AD BE EF  or text")
        self.find_edit.setMaximumWidth(220)
        self.find_edit.returnPressed.connect(lambda: self.find_next(False))
        tb.addWidget(self.find_edit)
        self.find_mode = QComboBox()
        self.find_mode.addItems(["Hex bytes", "Text (UTF-8)", "Text (UTF-16 LE)"])
        tb.addWidget(self.find_mode)
        tb.addAction("Next", lambda: self.find_next(False)).setToolTip("Find next (F3)")
        tb.addAction("Previous", lambda: self.find_next(True)).setToolTip("Find previous (Shift+F3)")
        tb.addSeparator()
        self.a_insert = tb.addAction("Insert Mode")
        self.a_insert.setCheckable(True)
        self.a_insert.setToolTip("Overwrite or insert bytes (Ins)")
        self.a_insert.toggled.connect(self._set_insert)
        self.status = QLabel()
        self.status.setContentsMargins(6, 2, 6, 2)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        _theme_mod().role(self.status, "help")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(tb)
        lay.addWidget(self.hex, 1)
        lay.addWidget(self.status)
        self.hex.cursorMoved.connect(self._update_status)
        self.hex.changed.connect(self._on_changed)
        self.hex.requestFind.connect(lambda: (self.find_edit.setFocus(), self.find_edit.selectAll()))
        self.hex.requestGoto.connect(self.goto)
        self.hex.requestSave.connect(self.save)
        self.hex.findNext.connect(self.find_next)
        self._was_modified = False
        self._update_status()

    def _set_insert(self, on):
        self.hex.insert_mode = on
        self._update_status()

    def _on_changed(self):
        m = self.hex.is_modified()
        if m != self._was_modified:
            self._was_modified = m
            self.modificationChanged.emit(m)
        i = self.win.tabs.indexOf(self)
        if i >= 0:
            self.win.tabs.setTabText(i, f"{self.path.name} [Hex]" + ("*" if m else ""))
        self._update_status()

    def _update_status(self, *_):
        h = self.hex
        i = h.cursor
        d = bytes(h.data[i:i + 8])
        parts = [f"Offset 0x{i:08X} ({i})", f"Size {len(h.data):,} bytes"]
        s = h.selection()
        if s:
            parts.append(f"Selected {s[1] - s[0]} (0x{s[0]:X}-0x{s[1] - 1:X})")
        if len(d) >= 1:
            parts.append(f"u8 {d[0]}  i8 {struct.unpack('<b', d[:1])[0]}")
        if len(d) >= 2:
            parts.append(f"u16 {struct.unpack('<H', d[:2])[0]}  i16 {struct.unpack('<h', d[:2])[0]}")
        if len(d) >= 4:
            parts.append(f"u32 {struct.unpack('<I', d[:4])[0]}  i32 {struct.unpack('<i', d[:4])[0]}  "
                         f"f32 {struct.unpack('<f', d[:4])[0]:.6g}")
        if len(d) >= 8:
            parts.append(f"i64 {struct.unpack('<q', d[:8])[0]}  f64 {struct.unpack('<d', d[:8])[0]:.6g}")
        parts.append("INS" if h.insert_mode else "OVR")
        self.status.setText("   |   ".join(parts) + "   (little endian)")
        if self.a_insert.isChecked() != h.insert_mode:
            self.a_insert.blockSignals(True)
            self.a_insert.setChecked(h.insert_mode)
            self.a_insert.blockSignals(False)

    def pattern(self) -> bytes:
        t = self.find_edit.text()
        mode = self.find_mode.currentIndex()
        if mode == 0:
            return parse_hex(t)
        return t.encode("utf-8" if mode == 1 else "utf-16-le")

    def find_next(self, backwards: bool = False) -> int:
        try:
            pat = self.pattern()
        except ValueError as e:
            self.win.statusBar().showMessage(f"Find: {e}", 4000)
            return -1
        i = self.hex.find(pat, backwards=backwards)
        self.win.statusBar().showMessage(f"Found at 0x{i:X}" if i >= 0 else "Not found", 3000)
        self.hex.setFocus()
        return i

    def goto(self, offset: int | None = None):
        if offset is None:
            t, ok = QInputDialog.getText(self, "Go to Offset", f"Offset (0 - 0x{len(self.hex.data):X}): 0x1F0, 1F0h or 496")
            if not ok or not t.strip():
                return
            try:
                offset = parse_offset(t)
            except ValueError:
                QMessageBox.warning(self, "Go to Offset", f"Not an offset: {t}")
                return
        self.hex.set_cursor(offset)
        self.hex.setFocus()

    def is_modified(self) -> bool:
        return self.hex.is_modified()

    def save(self) -> bool:
        try:
            self.path.write_bytes(bytes(self.hex.data))
        except OSError as e:
            QMessageBox.warning(self, "Hex Editor", f"Cannot save {self.path}:\n{e}")
            return False
        self.hex.mark_saved()
        self.win.statusBar().showMessage(f"Saved {self.path}", 3000)
        return True

    def save_as(self):
        f, _ = QFileDialog.getSaveFileName(self, "Save As", str(self.path), "All files (*)")
        if f:
            self.path = Path(f)
            self.save()
            self._on_changed()

    def maybe_close(self) -> bool:
        if not self.is_modified():
            return True
        r = QMessageBox.question(self, "Hex Editor", f"Save changes to {self.path.name}?",
                                 QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        return self.save() if r == QMessageBox.StandardButton.Save else True


def open_hex(win, path: Path) -> HexEditorView | None:
    path = Path(path).resolve()
    views = win.__dict__.setdefault("_hex_views", {})
    v = views.get(str(path))
    from PyQt6 import sip
    if v is None or sip.isdeleted(v) or win.tabs.indexOf(v) < 0:
        size = path.stat().st_size
        if size > 512 * 1024 * 1024:
            QMessageBox.warning(win, "Hex Editor", f"{path.name} is {size / 2**20:.0f} MB - too big for the hex editor.")
            return None
        v = HexEditorView(win, path)
        views[str(path)] = v
    if hasattr(win, "_show_tab"):
        win._show_tab(v, f"{path.name} [Hex]")
    else:
        win.tabs.setCurrentIndex(win.tabs.addTab(v, f"{path.name} [Hex]"))
    win.tabs.setTabToolTip(win.tabs.indexOf(v), str(path))
    v.hex.setFocus()
    return v


# ============================================================================ channel object for editor pages
class _RadxBridge(QObject):
    """Published to each Monaco editor page as `radex` (editor_extras.js -> Python)."""

    def __init__(self, editor):
        super().__init__()
        self._ed = weakref.ref(editor)

    @pyqtSlot(str)
    def jsCommand(self, command):
        ed = self._ed()
        win = _win_for(ed)
        ext = _ext(win) if win is not None else None
        if ed is None or ext is None:
            return
        QTimer.singleShot(0, lambda: ext.command(ed, command))


# ============================================================================ the feature object
class EditorExtras(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.keymap = str(win.settings.value(KEYMAP_KEY, "vscode") or "vscode")
        if self.keymap not in dict(KEYMAPS):
            self.keymap = "vscode"
        self.macros = Macros(self)
        self.rec_label = QLabel()
        T = _theme_mod()
        T.role(self.rec_label, "error")
        self.rec_label.hide()
        win.statusBar().addPermanentWidget(self.rec_label)
        self.filter = _KeyFilter(self)
        QApplication.instance().installEventFilter(self.filter)
        win.destroyed.connect(lambda *_: self._uninstall())

    def _uninstall(self):
        try:
            QApplication.instance().removeEventFilter(self.filter)
        except RuntimeError:
            pass

    # ---------------------------------------------------------------- editor pages
    def config(self, ed=None) -> dict:
        proj = getattr(self.win, "project", None)
        folder = getattr(proj, "folder", None) if proj is not None else None
        return {"keymap": self.keymap, "snippets": snippet_map(folder)}

    def inject(self, ed):
        try:
            ed.page().runJavaScript(_js_text() + f"\n;window.radex && radex.init({json.dumps(self.config(ed))});")
        except Exception as e:  # noqa: BLE001 - extras must never break the editor
            self.win.log(f"[editor extras] {e}")

    def push_snippets(self):
        proj = getattr(self.win, "project", None)
        m = json.dumps(snippet_map(getattr(proj, "folder", None) if proj is not None else None))
        for ed in _editors(self.win):
            rx(ed, f"radex.setSnippets({m});")

    def set_keymap(self, name: str):
        if name not in dict(KEYMAPS):
            name = "vscode"
        self.keymap = name
        self.win.settings.setValue(KEYMAP_KEY, name)
        for ed in _editors(self.win):
            rx(ed, f"radex.setKeymap({json.dumps(name)});")
        self.win.statusBar().showMessage(f"Keymap: {dict(KEYMAPS)[name]}", 3000)

    def command(self, ed, command: str):
        win = self.win
        if command == "save":
            view = _tab_widget_of(win, ed)
            if view is not None:
                win.tabs.setCurrentWidget(view)
                win.save_current()
        elif command == "close":
            view = _tab_widget_of(win, ed)
            if view is not None:
                win._close_tab(win.tabs.indexOf(view))
        elif command == "insertSnippet":
            self.insert_snippet(ed)
        elif command == "snippetsManager":
            self.snippets_manager()
        elif command == "macroToggle":
            self.macros.toggle()
        elif command == "macroPlay":
            self.macros.play()

    # ---------------------------------------------------------------- commands
    def split(self, mode: str):
        ed = current_editor(self.win)
        if not is_monaco(ed):
            self.win.statusBar().showMessage("Split needs the Monaco editor and an open code file", 4000)
            return
        rx(ed, f"radex.setSplit({json.dumps(mode)});")

    def insert_snippet(self, ed=None):
        ed = ed or current_editor(self.win)
        if not is_monaco(ed):
            return
        proj = getattr(self.win, "project", None)
        items = snippets_for(ed.language_id(), getattr(proj, "folder", None) if proj is not None else None)
        m = QMenu(self.win)
        if not items:
            m.addAction("(no snippets for this language)").setEnabled(False)
        for s in items:
            a = m.addAction(f"{s['prefix']}\t{s['name']}")
            a.setToolTip(s["body"])
            a.triggered.connect(lambda _c=False, b=s["body"]: rx(ed, f"radex.insertSnippet({json.dumps(b)});"))
        m.addSeparator()
        m.addAction("Code Snippets Manager...", lambda: self.snippets_manager(ed.language_id()))
        self._snippet_menu = m

        def show(pt):
            x, y, h = (pt or [0, 0, 18]) if isinstance(pt, list) else (0, 0, 18)
            m.popup(ed.mapToGlobal(QPoint(int(x), int(y) + int(h))))
        rx_eval(ed, "radCaretPoint()", show)

    def snippets_manager(self, lang: str | None = None):
        if lang is None:
            ed = current_editor(self.win)
            lang = ed.language_id() if is_monaco(ed) else None
        dlg = SnippetsDialog(self, lang)
        self.win._snippets_dialog = dlg
        dlg.exec()

    def macro_explorer(self):
        dlg = MacroExplorer(self)
        self.win._macro_explorer = dlg
        dlg.exec()

    def open_hex_dialog(self):
        start = str(self.win.project.folder) if getattr(self.win, "project", None) is not None else ""
        f, _ = QFileDialog.getOpenFileName(self.win, "Open in Hex Editor", start, "All files (*)")
        if f:
            open_hex(self.win, Path(f))

    def open_current_hex(self):
        ed = current_editor(self.win)
        p = _editor_path(ed) if ed is not None else None
        w = self.win.tabs.currentWidget()
        p = p or (Path(w.path) if getattr(w, "path", None) else None)
        if p is None or not Path(p).is_file():
            self.open_hex_dialog()
            return
        open_hex(self.win, Path(p))


# ============================================================================ Options page
def _options_page(dlg):
    win = dlg.win
    ext = _ext(win)
    if ext is None:
        return None
    w = QWidget()
    lay = QVBoxLayout(w)
    f = QFormLayout()
    combo = QComboBox()
    for kid, title in KEYMAPS:
        combo.addItem(title, kid)
    combo.setCurrentIndex(max(0, combo.findData(ext.keymap)))
    f.addRow("Editor keymap:", combo)
    lay.addLayout(f)
    note = QLabel("Visual Studio adds the VS 2005-2022 editor keys (Ctrl+K Ctrl+D, Ctrl+L, Ctrl+M Ctrl+M ...). "
                  "VS Code is Monaco's own set. Vim uses monaco-vim (:w saves, :vs splits). Emacs is a basic set. "
                  "While the editor has focus its keymap keys win over IDE menu shortcuts.")
    note.setWordWrap(True)
    _theme_mod().role(note, "muted")
    lay.addWidget(note)
    table = QTableWidget(0, 2)
    table.setHorizontalHeaderLabels(["Command", "Keys"])
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    lay.addWidget(table, 1)

    def fill(*_):
        km = combo.currentData()
        rows = ([] if km == "vim" else [("Multi-cursor: " + a, b) for a, b in KEYMAP_DOCS["common"]]) + KEYMAP_DOCS[km]
        table.setRowCount(len(rows))
        for r, (a, b) in enumerate(rows):
            table.setItem(r, 0, QTableWidgetItem(a))
            table.setItem(r, 1, QTableWidgetItem(b))
    combo.currentIndexChanged.connect(fill)
    fill()
    dlg._keymap_combo = combo

    def apply():
        if combo.currentData() != ext.keymap:
            ext.set_keymap(combo.currentData())
    return w, "Keyboard", apply


# ============================================================================ install
def _find_menu(win, name: str):
    for a in win.menuBar().actions():
        if a.text().replace("&", "").lower() == name.lower() and a.menu() is not None:
            return a.menu()
    return None


class HexFallback:
    """DocumentProvider (radide/extension_points.py, priority FALLBACK): a binary file nobody else opens
    (File > Open, Solution Explorer) goes to the hex editor. Every file type's own editor is asked first -
    a .cur cursor is the image editor's. Like before, the hex editor returns None (the tab is opened)."""

    def __init__(self, win):
        self.win = win

    def can_open(self, path: Path) -> bool:
        try:
            return should_open_hex(path)
        except OSError:
            return False

    def open_document(self, path: Path):
        open_hex(self.win, Path(path))
        return None

    def save_documents(self) -> None:
        return None

    def has_modified_documents(self) -> bool:
        return False


def _wrap_open(win):
    """win.open_file (web_workspace, installed later) of binary files goes to the hex editor too.
    TODO(stage B): one way to open files in MainWindow; then this wrapper goes as well."""
    if getattr(win, "_hex_open_wrapped", False):
        return
    win._hex_open_wrapped = True
    orig_file = getattr(win, "open_file", None)
    if callable(orig_file):
        def open_file(path, *a, **k):
            try:
                p = Path(path)
                if not p.is_absolute() and getattr(win, "project", None) is not None:
                    p = Path(win.project.folder) / p
                if should_open_hex(p):
                    open_hex(win, p)
                    return None
            except OSError:
                pass
            return orig_file(path, *a, **k)
        win.open_file = open_file


def _on_editor_ready(ed):
    win = _win_for(ed)
    ext = _ext(win) if win is not None else None
    if ext is not None:
        ext.inject(ed)


def install(win) -> None:
    cls = _monaco_class()
    ext = EditorExtras(win)
    win._editor_extras = ext
    _WINS.append(weakref.ref(win))
    if cls is not None:
        if "radex" not in cls.channel_objects:
            cls.channel_objects["radex"] = lambda ed: _RadxBridge(ed)
        if _on_editor_ready not in cls.ready_hooks:
            cls.ready_hooks.append(_on_editor_ready)
        for ed in _editors(win):                       # editors that were ready before this feature
            if getattr(ed, "_ready", False):
                ext.inject(ed)

    from . import settings as S
    if _options_page not in S.PAGE_HOOKS:
        S.PAGE_HOOKS.append(_options_page)

    mb = win.menuBar()
    # Window menu (Visual Studio): split
    wm = _find_menu(win, "Window")
    if wm is None:
        help_menu = _find_menu(win, "Help")
        wm = QMenu("&Window", win)
        if help_menu is not None:
            mb.insertMenu(help_menu.menuAction(), wm)
        else:
            mb.addMenu(wm)
    else:
        wm.addSeparator()
    ext.a_split_right = wm.addAction("Split Editor &Right\tCtrl+\\", lambda: ext.split("right"))
    ext.a_split_down = wm.addAction("Split Editor &Down", lambda: ext.split("down"))
    ext.a_unsplit = wm.addAction("&Remove Split", lambda: ext.split("none"))

    # File: hex editor
    fm = getattr(win, "file_menu", None) or _find_menu(win, "File")
    if fm is not None:
        before = next((a for a in fm.actions() if a.menu() is getattr(win, "recent_menu", None)), None)
        hm = QMenu("Open in &Hex Editor", fm)
        hm.addAction("File...", ext.open_hex_dialog)
        hm.addAction("Current File", ext.open_current_hex)
        if before is not None:
            fm.insertMenu(before, hm)
        else:
            fm.addMenu(hm)
        ext.hex_menu = hm

    # Edit: snippets
    em = _find_menu(win, "Edit")
    if em is not None:
        em.addSeparator()
        em.addAction("Insert Snippet...", lambda: ext.insert_snippet())

    tools = _find_menu(win, "Tools")
    if tools is not None:
        cm = tools.addMenu("&Compare (Diff)")
        cm.addAction("Compare Files...", lambda: compare_files(win))
        cm.addAction("Compare Current File with Saved", lambda: compare_with_saved(win))
        cm.addAction("Compare Current File with Git HEAD", lambda: compare_with_head(win))
        cm.addAction("Compare Current File with Clipboard", lambda: compare_with_clipboard(win))
        cm.addAction("Compare Current File with...", lambda: compare_with_file(win))
        mm = tools.addMenu("&Macros")
        a = mm.addAction("&Record Temporary Macro / Stop", ext.macros.toggle)
        a.setShortcut(QKeySequence("Ctrl+Shift+R"))
        a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        ext.a_macro_record = a
        a = mm.addAction("R&un Temporary Macro", lambda: ext.macros.play())
        a.setShortcut(QKeySequence("Ctrl+Shift+Alt+P"))
        a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        ext.a_macro_play = a
        mm.addAction("&Save Temporary Macro...", lambda: ext.macros.save_temp())
        mm.addAction("Macro &Explorer...", ext.macro_explorer)
        tools.addAction("Code &Snippets Manager...", lambda: ext.snippets_manager())
        kmm = tools.addMenu("&Keymap")
        grp = []
        for kid, title in KEYMAPS:
            act = kmm.addAction(title)
            act.setCheckable(True)
            act.setChecked(kid == ext.keymap)
            act.triggered.connect(lambda _c=False, k=kid: ext.set_keymap(k))
            grp.append((kid, act))

        def sync():
            for kid, act in grp:
                act.setChecked(kid == ext.keymap)
        kmm.aboutToShow.connect(sync)
    from ..extension_points import FALLBACK
    win.extension_points.add_document_provider(HexFallback(win), FALLBACK)
    QTimer.singleShot(0, lambda: _wrap_open(win))   # after web_workspace installed win.open_file


__all__ = ["install", "DiffView", "DiffSide", "open_diff", "compare_files", "compare_with_clipboard",
           "compare_with_saved", "compare_with_head", "compare_with_file", "HexView", "HexEditorView", "open_hex",
           "SnippetsDialog", "Snippet", "parse_snippets", "snippets_to_json", "snippet_map", "Macros",
           "MacroExplorer", "KEYMAPS", "key_text", "git_head_text", "is_binary", "parse_hex", "parse_offset",
           "user_dir", "rx", "rx_eval"]
