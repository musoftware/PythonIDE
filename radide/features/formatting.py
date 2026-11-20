"""Format Document / Format on Save for every language (Edit > Format Document, Shift+Alt+F, Ctrl+K Ctrl+D).

Formatters (the first one found is used when a language is set to "Automatic"):
  Python      ruff format, black                       (project .venv first, then the IDE's)
  JS/TS/HTML/CSS/SCSS/Less/JSON/Markdown/YAML           Prettier (project node_modules, the IDE's private
                                                        npm folder %LOCALAPPDATA%\\RADIDE\\lsp, or npx)
  C / C++ / Java / C#  clang-format                     (PATH, LLVM, MinGW toolchains, the IDE's venv)
  Go gofmt, Rust rustfmt, Dart dart format, PHP php-cs-fixer
  any language whose Language Server can format (textDocument/formatting), else Monaco's own formatter.
The result is applied as ONE undo step (Ctrl+Z undoes the whole format). Tools > Options > Formatting
chooses the formatter per language and "Format on save".
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PyQt6.QtCore import QEventLoop, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                             QTableWidget, QVBoxLayout, QWidget)

from .. import editkit

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LOCAL = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE"
LSP_HOME = LOCAL / "lsp"

PRETTIER_LANGS = ("javascript", "typescript", "html", "css", "scss", "less", "json", "markdown", "yaml")
CLANG_LANGS = ("c", "cpp", "java", "csharp")

# Monaco language -> formatter ids in "Automatic" order
CHAIN = {
    "python": ["ruff", "black", "lsp"],
    **{lang: ["prettier", "lsp", "builtin"] for lang in PRETTIER_LANGS},
    **{lang: ["clang-format", "lsp"] for lang in CLANG_LANGS},
    "go": ["gofmt", "lsp"], "rust": ["rustfmt", "lsp"], "dart": ["dart", "lsp"],
    "php": ["php-cs-fixer", "lsp"],
}
LANG_TITLES = {"python": "Python", "javascript": "JavaScript", "typescript": "TypeScript", "html": "HTML",
               "css": "CSS", "scss": "SCSS", "less": "Less", "json": "JSON", "markdown": "Markdown",
               "yaml": "YAML", "c": "C", "cpp": "C++", "java": "Java", "csharp": "C#", "go": "Go",
               "rust": "Rust", "dart": "Dart", "php": "PHP"}
TITLES = {"auto": "Automatic", "ruff": "Ruff", "black": "Black", "prettier": "Prettier",
          "prettier-npx": "Prettier (npx, downloads on first use)", "clang-format": "clang-format",
          "gofmt": "gofmt", "rustfmt": "rustfmt", "dart": "dart format", "php-cs-fixer": "PHP CS Fixer",
          "lsp": "Language Server", "builtin": "Monaco built-in", "none": "None"}
BUILTIN_LANGS = {"javascript", "typescript", "html", "css", "scss", "less", "json"}


class FormatError(Exception):
    pass


# ============================================================================ tool lookup
def _which(*names, dirs=(), path_first=True):
    exts = (".exe", ".cmd", ".bat", "") if os.name == "nt" else ("",)

    def in_dirs():
        for d in dirs:
            for n in names:
                for e in exts:
                    p = Path(d) / (n + e)
                    if p.is_file():
                        return str(p)
        return ""
    if not path_first:
        found = in_dirs()
        if found:
            return found
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return in_dirs()


def _venv_bins(root):
    out = []
    if root:
        out += [Path(root) / ".venv" / "Scripts", Path(root) / ".venv" / "bin", Path(root) / "venv" / "Scripts"]
    out.append(Path(sys.executable).parent)
    return out


def _tool_dirs():
    out = [LOCAL / "toolchains" / "go" / "bin", LOCAL / "toolchains" / "mingw64" / "bin",
           Path(r"C:\Program Files\LLVM\bin"), Path(r"C:\msys64\ucrt64\bin"), Path(r"C:\msys64\clang64\bin"),
           Path(sys.executable).parent]
    for base in (LOCAL / "tools", LOCAL / "toolchains"):
        if base.is_dir():
            for d in base.iterdir():
                if d.is_dir():
                    out += [d / "bin", d]
    return out


def _prettier(root):
    node = shutil.which("node")
    if not node:
        return None
    for base in ([Path(root)] if root else []) + [LSP_HOME]:
        cli = base / "node_modules" / "prettier" / "bin" / "prettier.cjs"
        if cli.is_file():
            return [node, str(cli)]
    return None


def tool_argv(fid: str, path: Path, root) -> list | None:
    """argv reading the source on stdin and writing the result to stdout (None = not available).
    php-cs-fixer works on a file: its argv ends with the placeholder "{file}"."""
    p = str(path)
    if fid == "ruff":
        exe = _which("ruff", dirs=_venv_bins(root), path_first=False)   # project .venv, the IDE's, PATH
        return [exe, "format", "--stdin-filename", p, "-"] if exe else None
    if fid == "black":
        exe = _which("black", dirs=_venv_bins(root), path_first=False)
        return [exe, "-q", "--stdin-filename", p, "-"] if exe else None
    if fid == "prettier":
        base = _prettier(root)
        return [*base, "--stdin-filepath", p] if base else None
    if fid == "prettier-npx":
        npx = shutil.which("npx")
        return ["cmd.exe", "/d", "/c", npx, "--yes", "prettier@3", "--stdin-filepath", p] if npx else None
    if fid == "clang-format":
        exe = _which("clang-format", dirs=_tool_dirs())
        return [exe, f"--assume-filename={p}"] if exe else None
    if fid == "gofmt":
        exe = _which("gofmt", dirs=_tool_dirs())
        return [exe] if exe else None
    if fid == "rustfmt":
        exe = _which("rustfmt", dirs=[Path.home() / ".cargo" / "bin"])
        return [exe, "--edition", "2021", "--emit", "stdout"] if exe else None
    if fid == "dart":
        exe = _which("dart", dirs=[Path(r"C:\flutter\bin")])
        if not exe:
            return None
        return ["cmd.exe", "/d", "/c", exe, "format"] if exe.lower().endswith(".bat") else [exe, "format"]
    if fid == "php-cs-fixer":
        cands = ([Path(root) / "vendor" / "bin" / "php-cs-fixer"] if root else [])
        for c in cands:
            if c.exists() and shutil.which("php"):
                return [shutil.which("php"), str(c), "fix", "--using-cache=no", "--quiet", "{file}"]
        phar = LOCAL / "tools" / "php-cs-fixer" / "php-cs-fixer.phar"     # official phar (cs.symfony.com)
        if phar.is_file() and shutil.which("php"):
            return [shutil.which("php"), str(phar), "fix", "--using-cache=no", "--quiet", "{file}"]
        exe = _which("php-cs-fixer", dirs=_tool_dirs())
        if exe:
            base = ["cmd.exe", "/d", "/c", exe] if exe.lower().endswith((".bat", ".cmd")) else [exe]
            return [*base, "fix", "--using-cache=no", "--quiet", "{file}"]
        return None
    return None


def run_tool(fid: str, text: str, path: Path, root, timeout=30) -> str:
    argv = tool_argv(fid, path, root)
    if not argv:
        raise FormatError(f"{TITLES.get(fid, fid)} is not installed")
    cwd = str(root or Path(path).parent)
    if "{file}" in argv:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td) / Path(path).name
            tmp.write_text(text, encoding="utf-8")
            argv = [str(tmp) if a == "{file}" else a for a in argv]
            p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=timeout, creationflags=NOWIN)
            if p.returncode not in (0, 8):          # php-cs-fixer: 8 = some files fixed (dry-run)
                raise FormatError((p.stderr or p.stdout).strip()[-2000:] or f"exit code {p.returncode}")
            return tmp.read_text(encoding="utf-8")
    p = subprocess.run(argv, input=text, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, creationflags=NOWIN)
    if p.returncode != 0 or (not p.stdout and text.strip()):
        raise FormatError((p.stderr or p.stdout).strip()[-2000:] or f"exit code {p.returncode}")
    return p.stdout.replace("\r\n", "\n")


# ============================================================================ settings
def _settings(win):
    return win.settings


def chosen(win, lang: str) -> str:
    return str(_settings(win).value(f"format/tool/{lang}", "auto") or "auto")


def on_save_enabled(win, lang: str) -> bool:
    s = _settings(win)
    master = s.value("format/on_save", False) in (True, "true")
    per = s.value(f"format/on_save/{lang}", True) in (True, "true")
    return master and per


def _root_for(win, ed):
    if getattr(win, "project", None) is not None:
        try:
            folder = Path(win.project.folder).resolve()
            if folder in Path(ed.path).resolve().parents:
                return folder
        except (OSError, AttributeError):
            pass
    try:
        return Path(ed.path).resolve().parent
    except (OSError, AttributeError):
        return None


def _lsp_can_format(ed) -> bool:
    c = getattr(ed, "lsp", None)
    return bool(c is not None and (getattr(c, "capabilities", {}) or {}).get("documentFormattingProvider"))


def resolve_formatter(win, ed, lang: str | None = None) -> str:
    """The formatter id used for this editor: a tool id, "lsp", "builtin" or "none"."""
    lang = lang or (ed.language_id() if hasattr(ed, "language_id") else "")
    want = chosen(win, lang)
    if want == "none":
        return "none"
    root = _root_for(win, ed)
    if want != "auto":
        return want
    for fid in CHAIN.get(lang, ["lsp", "builtin"]):
        if fid == "lsp":
            if _lsp_can_format(ed):
                return "lsp"
        elif fid == "builtin":
            if lang in BUILTIN_LANGS:
                return "builtin"
        elif tool_argv(fid, Path(getattr(ed, "path", "x")), root):
            return fid
    if lang in BUILTIN_LANGS:
        return "builtin"
    return "lsp" if _lsp_can_format(ed) else "none"


def provider_languages(win) -> set:
    """Languages whose Monaco Format Document goes through our provider (all but builtin/none)."""
    out = set()
    for lang in CHAIN:
        want = chosen(win, lang)
        if want in ("builtin", "none"):
            continue
        if want == "auto" and lang in BUILTIN_LANGS and not _prettier(getattr(getattr(win, "project", None), "folder", None)):
            continue                          # no Prettier: let Monaco (or the language server) format
        out.add(lang)
    return out


# ============================================================================ formatting
class _Signals(QObject):
    done = pyqtSignal(object, object)        # callback, (ok, value)


_SIG = None


def _sig():
    global _SIG
    if _SIG is None:
        _SIG = _Signals()
        _SIG.done.connect(lambda cb, res: cb(*res), Qt.ConnectionType.QueuedConnection)
    return _SIG


def format_async(win, ed, cb, fid: str | None = None):
    """cb(ok, new_text_or_error) on the GUI thread."""
    lang = ed.language_id() if hasattr(ed, "language_id") else ""
    fid = fid or resolve_formatter(win, ed, lang)
    text = ed.text()
    if fid == "none":
        cb(False, f"No formatter for {LANG_TITLES.get(lang, lang)} (Tools > Options > Formatting)")
        return
    if fid == "builtin":
        cb(False, "builtin")
        return
    if fid == "lsp":
        c = getattr(ed, "lsp", None)
        if c is None:
            cb(False, "no language server is attached")
            return
        c.did_change(ed.path, text)
        tab = getattr(win, "settings", None)
        size = int(tab.value("options/tab_width", 4) or 4) if tab is not None else 4

        def got(res):
            if res is None and getattr(c, "last_error", ""):
                cb(False, c.last_error)
                return
            cb(True, editkit.apply_edits_to_text(text, editkit.lsp_edits(res or [])))
        c._request("textDocument/formatting", {"textDocument": {"uri": Path(ed.path).resolve().as_uri()},
                                                "options": {"tabSize": size, "insertSpaces": True}}, got)
        return
    root = _root_for(win, ed)
    path = Path(ed.path)

    def work():
        try:
            res = (True, run_tool(fid, text, path, root))
        except subprocess.TimeoutExpired:
            res = (False, f"{TITLES.get(fid, fid)} took too long")
        except (FormatError, OSError) as e:
            res = (False, f"{TITLES.get(fid, fid)}: {e}")
        _sig().done.emit(cb, res)
    threading.Thread(target=work, daemon=True).start()


def format_sync(win, ed, timeout_ms=20000) -> tuple[bool, str]:
    loop = QEventLoop()
    box = {}

    def cb(ok, val):
        box["r"] = (ok, val)
        loop.quit()
    format_async(win, ed, cb)
    if "r" not in box:
        QTimer.singleShot(timeout_ms, loop.quit)
        loop.exec()
    return box.get("r", (False, "timeout"))


def format_editor(win, ed, quiet=False) -> None:
    """Edit > Format Document."""
    if ed is None:
        return
    fid = resolve_formatter(win, ed)
    if fid == "builtin" and editkit.is_monaco(ed):
        ed._js("radEditor.getAction('editor.action.formatDocument').run();")
        return
    win.statusBar().showMessage(f"Formatting with {TITLES.get(fid, fid)}...", 3000)

    def done(ok, val):
        if not ok:
            if val == "builtin" and editkit.is_monaco(ed):
                ed._js("radEditor.getAction('editor.action.formatDocument').run();")
                return
            win.statusBar().showMessage(f"Format Document: {val.splitlines()[0] if val else 'failed'}", 8000)
            if not quiet:
                win.log(f"[format] {val}")
            return
        try:
            changed = editkit.apply_text(ed, val)
        except RuntimeError:              # editor closed meanwhile
            return
        win.statusBar().showMessage(f"Formatted with {TITLES.get(fid, fid)}" + ("" if changed else " (no changes)"),
                                    4000)
    format_async(win, ed, done, fid)


def format_before_save(win, editors, force=False) -> int:
    n = 0
    for ed in editors:
        try:
            if ed is None or not (force or ed.isModified()) or not hasattr(ed, "language_id"):
                continue
            lang = ed.language_id()
            if not on_save_enabled(win, lang):
                continue
            fid = resolve_formatter(win, ed, lang)
            if fid in ("none", "builtin"):
                continue
            ok, val = format_sync(win, ed)
            if ok and editkit.apply_text(ed, val):
                n += 1
            elif not ok:
                win.log(f"[format on save] {Path(ed.path).name}: {val}")
        except RuntimeError:
            continue
    return n


# ============================================================================ Monaco provider
def _provider(win):
    def handle(ed, req, _payload):
        def done(ok, val):
            if not ok:
                if val != "builtin":
                    win.statusBar().showMessage(f"Format Document: {val.splitlines()[0] if val else 'failed'}", 8000)
                editkit.resolve(ed, req, None)
                return
            editkit.resolve(ed, req, editkit.diff_edits(ed.text(), val))
            win.statusBar().showMessage("Document formatted", 3000)
        format_async(win, ed, done)
    return handle


# ============================================================================ Options page
def _options_page(dlg):
    win = dlg.win
    page = QWidget()
    lay = QVBoxLayout(page)
    master = QCheckBox("Format the document when it is saved (Format on Save)")
    master.setChecked(win.settings.value("format/on_save", False) in (True, "true"))
    lay.addWidget(master)
    note = QLabel("Choose the formatter of each language. <i>Automatic</i> uses the first one installed; "
                  "Format Document is Shift+Alt+F or Ctrl+K, Ctrl+D and is undone with one Ctrl+Z.")
    note.setWordWrap(True)
    lay.addWidget(note)
    table = QTableWidget(len(CHAIN), 4)
    table.setHorizontalHeaderLabels(["Language", "Formatter", "On save", "Found"])
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
    root = getattr(getattr(win, "project", None), "folder", None)
    combos, checks = {}, {}
    from PyQt6.QtWidgets import QTableWidgetItem
    for row, lang in enumerate(CHAIN):
        table.setItem(row, 0, QTableWidgetItem(LANG_TITLES.get(lang, lang)))
        cb = QComboBox()
        opts = ["auto", *CHAIN[lang]]
        if lang in PRETTIER_LANGS:
            opts.insert(2, "prettier-npx")
        if lang in BUILTIN_LANGS and "builtin" not in opts:
            opts.append("builtin")
        opts.append("none")
        for o in opts:
            cb.addItem(TITLES.get(o, o), o)
        i = cb.findData(chosen(win, lang))
        cb.setCurrentIndex(max(0, i))
        table.setCellWidget(row, 1, cb)
        chk = QCheckBox()
        chk.setChecked(win.settings.value(f"format/on_save/{lang}", True) in (True, "true"))
        w = QWidget()
        hl = QHBoxLayout(w)
        hl.setContentsMargins(6, 0, 0, 0)
        hl.addWidget(chk)
        table.setCellWidget(row, 2, w)
        found = [TITLES[f] for f in CHAIN[lang] if f not in ("lsp", "builtin") and tool_argv(f, Path("x"), root)]
        table.setItem(row, 3, QTableWidgetItem(", ".join(found) or "-"))
        combos[lang], checks[lang] = cb, chk
    lay.addWidget(table, 1)
    row = QHBoxLayout()
    inst = QPushButton("Install Prettier")
    inst.setToolTip(f"npm install prettier into {LSP_HOME} (used for JS/TS/HTML/CSS/JSON/Markdown/YAML)")
    inst.setEnabled(_prettier(None) is None and bool(shutil.which("npm")))
    status = QLabel("")

    def install_prettier():
        inst.setEnabled(False)
        status.setText("Installing Prettier with npm...")

        def work():
            npm = shutil.which("npm")
            LSP_HOME.mkdir(parents=True, exist_ok=True)
            p = subprocess.run(["cmd.exe", "/d", "/c", npm, "install", "--prefix", str(LSP_HOME), "--no-fund",
                                "--no-audit", "prettier@3"], capture_output=True, text=True, creationflags=NOWIN)
            _sig().done.emit(lambda ok, msg: status.setText(msg), (True, "Prettier installed." if p.returncode == 0
                                                                     else "npm failed: " + p.stderr[-300:]))
        threading.Thread(target=work, daemon=True).start()
    inst.clicked.connect(install_prettier)
    row.addWidget(inst)
    row.addWidget(status, 1)
    lay.addLayout(row)

    def apply():
        win.settings.setValue("format/on_save", master.isChecked())
        for lang in CHAIN:
            win.settings.setValue(f"format/tool/{lang}", combos[lang].currentData())
            win.settings.setValue(f"format/on_save/{lang}", checks[lang].isChecked())
        if getattr(win, "a_format_on_save", None) is not None:
            win.a_format_on_save.setChecked(master.isChecked())
        editkit.sync_format_languages(provider_languages(win))
    return page, "Formatting", apply


# ============================================================================ install
def install(win) -> None:
    _sig()                                   # created on the GUI thread (worker threads emit into it)
    editkit.install_monaco()
    editkit.REQUESTS["format"] = _provider(win)
    editkit.sync_format_languages(provider_languages(win))
    win.format_editor = lambda ed=None: format_editor(win, ed or _current_editor(win))
    win.format_before_save = lambda eds: format_before_save(win, eds)

    edit = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Edit"), None)
    a = QAction("&Format Document", win)
    a.setShortcuts([QKeySequence("Shift+Alt+F"), QKeySequence("Ctrl+K, Ctrl+D")])
    a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
    a.setStatusTip("Format the whole document with the language's formatter (one undo step)")
    a.triggered.connect(lambda: format_editor(win, _current_editor(win)))
    win.a_format_document = a
    fos = QAction("Format on &Save", win)
    fos.setCheckable(True)
    fos.setChecked(win.settings.value("format/on_save", False) in (True, "true"))
    fos.toggled.connect(lambda on: win.settings.setValue("format/on_save", on))
    win.a_format_on_save = fos
    if edit is not None:
        edit.addSeparator()
        edit.addAction(a)
        edit.addAction(fos)
    win.addAction(a)

    # format on save. Save All and form code: before the files are written (the IDE's own writers are
    # wrapped, so features that wrap save_all keep working); File > Save of a code file: right after it,
    # then saved again when the formatter changed something.
    def enabled():
        return win.settings.value("format/on_save", False) in (True, "true")
    busy = {"on": False}
    orig_sap = getattr(win, "_save_active_project", None)
    if orig_sap is not None:
        def save_active_project(*a, **k):
            if enabled() and not busy["on"]:
                busy["on"] = True
                try:
                    format_before_save(win, [v.editor for v in list(win.codeviews.values()) +
                                             list(win.modviews.values())])
                except Exception as e:  # noqa: BLE001 - saving must still happen
                    win.log(f"[format on save] {e}")
                finally:
                    busy["on"] = False
            busy["on"] = True
            try:
                return orig_sap(*a, **k)
            finally:
                busy["on"] = False
        win._save_active_project = save_active_project
    orig_sf = getattr(win, "_save_form", None)
    if orig_sf is not None:
        def save_form(name, *a, **k):
            if enabled() and not busy["on"] and name in win.codeviews:
                try:
                    format_before_save(win, [win.codeviews[name].editor])
                except Exception as e:  # noqa: BLE001
                    win.log(f"[format on save] {e}")
            return orig_sf(name, *a, **k)
        win._save_form = save_form

    def after_save_current(*_a):
        if not enabled() or busy["on"]:
            return
        w = win.tabs.currentWidget() if getattr(win, "tabs", None) is not None else None
        ed = getattr(w, "editor", None)
        if ed is None or w in win.codeviews.values() or ed.isModified() or not hasattr(ed, "language_id"):
            return                                   # forms were formatted before; unsaved = save failed
        lang = ed.language_id()
        if not on_save_enabled(win, lang) or resolve_formatter(win, ed, lang) in ("none", "builtin"):
            return

        def done(ok, val):                       # asynchronous: no nested event loop inside the Save action
            try:
                if not ok:
                    win.log(f"[format on save] {Path(ed.path).name}: {val}")
                    return
                if editkit.apply_text(ed, val) and win.tabs.currentWidget() is w:
                    busy["on"] = True
                    try:
                        win.save_current()
                    finally:
                        busy["on"] = False
            except RuntimeError:                 # the editor was closed meanwhile
                pass
        format_async(win, ed, done)
    if getattr(win, "a_save_file", None) is not None:
        win.a_save_file.triggered.connect(after_save_current)

    try:
        from .settings import PAGE_HOOKS
        PAGE_HOOKS.append(_options_page)
    except ImportError:
        pass

    # the editor's own right-click "Format Document" goes through the same path
    def on_menu(menu, ed):
        for act in menu.actions():
            if act.text() == "Format Document":
                try:
                    act.triggered.disconnect()
                except (TypeError, RuntimeError):
                    pass
                act.setText("Format Document	Shift+Alt+F")
                act.triggered.connect(lambda: format_editor(win, ed))
    editkit.READY.append(lambda ed: ed.contextMenuAboutToShow.connect(lambda m, e=ed: on_menu(m, e))
                         if ed.window() is win else None)


def _current_editor(win):
    try:
        cv = win._current_code()
    except Exception:  # noqa: BLE001
        cv = None
    if cv is not None and getattr(cv, "editor", None) is not None:
        return cv.editor
    w = win.tabs.currentWidget() if getattr(win, "tabs", None) is not None else None
    return getattr(w, "editor", None)
