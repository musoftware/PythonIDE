"""Editor/IDE productivity tools: Find/Replace bar, Find in Files, Error List
(syntax checks per language), Go to Definition (F12), debugger hover values,
and auto-save backups. Installed into the main window by install_tools()."""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QRegularExpression, Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QDockWidget, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QToolButton, QToolTip, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)


# =================================================================== diagnostics
@dataclass
class Diag:
    severity: str      # Error | Warning
    message: str
    file: str
    line: int          # 1-based


def check_project(project, plugin, texts: dict[str, str]) -> list[Diag]:
    """texts: code file name -> current text (unsaved editor contents win)."""
    out: list[Diag] = []
    pid = plugin.id
    for fname, text in texts.items():
        if pid.startswith("python"):
            try:
                compile(text, fname, "exec")
            except SyntaxError as e:
                out.append(Diag("Error", f"SyntaxError: {e.msg}", fname, e.lineno or 1))
                continue
            try:
                from pyflakes import api as fl_api
                from pyflakes import reporter as fl_rep

                class _Rep(fl_rep.Reporter):
                    def __init__(self):
                        pass

                    def unexpectedError(self, filename, msg):
                        out.append(Diag("Error", str(msg), fname, 1))

                    def syntaxError(self, filename, msg, lineno, offset, text):
                        out.append(Diag("Error", str(msg), fname, lineno or 1))

                    def flake(self, m):
                        msg = m.message % m.message_args
                        if "imported but unused" in msg or "unable to detect undefined names" in msg:
                            return
                        sev = "Error" if "undefined name" in msg else "Warning"
                        out.append(Diag(sev, msg, fname, m.lineno))
                fl_api.check(text, fname, _Rep())
            except ImportError:
                pass
        elif pid == "vb-basic":
            from .runtimes.vbparse import VBSyntaxError, parse_module
            try:
                parse_module(text, Path(fname).stem)
            except VBSyntaxError as e:
                out.append(Diag("Error", f"Syntax error: {e.msg}", fname, e.line))
        elif pid == "ring-qt":
            ring = plugin.find_interpreter("")
            if not ring:
                continue
            path = project.folder / fname
            try:
                r = subprocess.run([ring, str(path), "-norun"], cwd=str(project.folder), capture_output=True,
                                   text=True, timeout=20, encoding="utf-8", errors="replace")
            except (OSError, subprocess.TimeoutExpired):
                continue
            for m in re.finditer(r"([^\r\n]*?)\s+Line \((\d+)\) Error \((\w+)\) : ([^\r\n]+)", r.stdout + r.stderr):
                out.append(Diag("Error", f"{m.group(4).strip()} ({m.group(3)})", Path(m.group(1)).name or fname,
                                int(m.group(2))))
        elif pid == "fortran-bridge":
            gf = plugin.compiler() if hasattr(plugin, "compiler") else ""
            if gf and fname != "radgui.f90":
                r = subprocess.run([gf, "-fsyntax-only", str(project.folder / "radgui.f90"), str(project.folder / fname)],
                                   cwd=str(project.folder), capture_output=True, text=True)
                for m in re.finditer(r"([\w.]+):(\d+):\d+:\s*\n(?:.*\n)*?\s*(Error|Warning): ([^\n]+)", r.stderr):
                    out.append(Diag(m.group(3), m.group(4), m.group(1), int(m.group(2))))
    for fname, text in texts.items():           # TODO / FIXME task list
        for i, ln in enumerate(text.splitlines(), 1):
            m = re.search(r"\b(TODO|FIXME|HACK)\b[:\s]*(.*)", ln)
            if m and any(c in ln[:m.start()] for c in ("#", "'", "!", "//")):
                out.append(Diag("Task", f"{m.group(1)}: {m.group(2).strip()}", fname, i))
    return out


# =================================================================== find bar
class FindBar(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.find = QLineEdit(placeholderText="Find")
        self.repl = QLineEdit(placeholderText="Replace with")
        self.case = QCheckBox("Aa")
        self.case.setToolTip("Match case")
        self.word = QCheckBox("Word")
        self.regex = QCheckBox(".*")
        self.regex.setToolTip("Regular expression")
        self.info = QLabel()
        b = lambda text, slot, tip="": self._btn(text, slot, tip)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        for w in (QLabel("Find:"), self.find, b("Next", self.next, "F3"), b("Prev", self.prev, "Shift+F3"),
                  self.case, self.word, self.regex, QLabel("Replace:"), self.repl,
                  b("Replace", self.replace), b("All", self.replace_all), self.info, b("✕", self.close_bar)):
            lay.addWidget(w)
        self.find.returnPressed.connect(self.next)
        self.repl.returnPressed.connect(self.replace)
        self.find.textChanged.connect(lambda _t: self._count())
        self.setVisible(False)

    @staticmethod
    def _btn(text, slot, tip):
        bt = QToolButton(text=text)
        bt.setToolTip(tip)
        bt.clicked.connect(slot)
        return bt

    def editor(self):
        cv = self.win._current_code()
        return cv.editor if cv is not None else None

    def open(self, replace=False):
        ed = self.editor()
        if ed is None:
            return
        if hasattr(ed, "_js"):           # Monaco: use its built-in find / replace widget
            ed.setFocus()
            ed._js("radEditor.focus(); radEditor.trigger('rad', '%s');" %
                   ("editor.action.startFindReplaceAction" if replace else "actions.find"))
            return
        sel = ed.textCursor().selectedText()
        if sel and " " not in sel:
            self.find.setText(sel)
        self.setVisible(True)
        self.repl.setVisible(True)
        (self.repl if replace and self.find.text() else self.find).setFocus()
        self.find.selectAll()
        self._count()

    def close_bar(self):
        self.setVisible(False)
        ed = self.editor()
        if ed is not None:
            ed.setFocus()

    def _pattern(self):
        text = self.find.text()
        if not text:
            return None
        pat = text if self.regex.isChecked() else QRegularExpression.escape(text)
        if self.word.isChecked():
            pat = rf"\b{pat}\b"
        rx = QRegularExpression(pat)
        if not self.case.isChecked():
            rx.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
        return rx

    def _search(self, backward=False):
        ed, rx = self.editor(), self._pattern()
        if ed is None or rx is None or not rx.isValid():
            return False
        flags = QTextDocument.FindFlag.FindBackward if backward else QTextDocument.FindFlag(0)
        cur = ed.document().find(rx, ed.textCursor(), flags)
        if cur.isNull():                                # wrap around
            start = QTextCursor(ed.document())
            if backward:
                start.movePosition(QTextCursor.MoveOperation.End)
            cur = ed.document().find(rx, start, flags)
        if cur.isNull():
            self.info.setText("<span style='color:#b00'>not found</span>")
            return False
        ed.setTextCursor(cur)
        ed.centerCursor()
        return True

    def next(self):
        ed = self.editor()
        if ed is not None and hasattr(ed, "_js"):
            ed._js("radEditor.trigger('rad', 'editor.action.nextMatchFindAction');")
            return
        self._search()
        self._count()

    def prev(self):
        ed = self.editor()
        if ed is not None and hasattr(ed, "_js"):
            ed._js("radEditor.trigger('rad', 'editor.action.previousMatchFindAction');")
            return
        self._search(backward=True)

    def _count(self):
        ed, rx = self.editor(), self._pattern()
        if ed is None or rx is None or not rx.isValid():
            self.info.setText("")
            return
        n = 0
        it = rx.globalMatch(ed.toPlainText())
        while it.hasNext():
            it.next()
            n += 1
        self.info.setText(f"{n} match{'es' if n != 1 else ''}")

    def replace(self):
        ed, rx = self.editor(), self._pattern()
        if ed is None or rx is None:
            return
        cur = ed.textCursor()
        if cur.hasSelection() and rx.match(cur.selectedText()).hasMatch():
            cur.insertText(self._replacement(cur.selectedText(), rx))
        self.next()

    def _replacement(self, matched, rx):
        if not self.regex.isChecked():
            return self.repl.text()
        m = rx.match(matched)
        out = self.repl.text()
        for i in range(m.lastCapturedIndex(), -1, -1):
            out = out.replace(f"\\{i}", m.captured(i)).replace(f"${i}", m.captured(i))
        return out

    def replace_all(self):
        ed, rx = self.editor(), self._pattern()
        if ed is None or rx is None:
            return
        cur = QTextCursor(ed.document())
        n = 0
        cur.beginEditBlock()
        while True:
            found = ed.document().find(rx, cur)
            if found.isNull():
                break
            found.insertText(self._replacement(found.selectedText(), rx))
            cur = found
            n += 1
        cur.endEditBlock()
        self.info.setText(f"replaced {n}")


# =================================================================== find in files
class FindInFilesDialog(QDialog):
    def __init__(self, parent, text=""):
        super().__init__(parent)
        self.setWindowTitle("Find in Files")
        self.text = QLineEdit(text)
        self.case = QCheckBox("Match case")
        self.regex = QCheckBox("Use regular expressions")
        self.replace = QLineEdit()
        self.replace.setPlaceholderText("(leave empty to only find)")
        lay = QFormLayout(self)
        lay.addRow("Find what:", self.text)
        lay.addRow("Replace with:", self.replace)
        lay.addRow(self.case)
        lay.addRow(self.regex)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addRow(box)


# =================================================================== install
def install_tools(win) -> None:
    """Add Find/Replace, Find in Files, Error List, Go to Definition, hover values, auto-save."""
    # find bar above the tabs
    win.findbar = FindBar(win)
    central = QWidget()
    lay = QVBoxLayout(central)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    lay.addWidget(win.findbar)
    lay.addWidget(win.takeCentralWidget(), 1)
    win.setCentralWidget(central)

    # result docks
    win.find_results = QTreeWidget()
    win.find_results.setHeaderLabels(["File", "Line", "Text"])
    win.find_results.setRootIsDecorated(False)
    win.find_results.itemDoubleClicked.connect(lambda it, _c: _goto(win, it.text(0), int(it.text(1))))
    win.error_list = QTreeWidget()
    win.error_list.setHeaderLabels(["", "Description", "File", "Line"])
    win.error_list.setRootIsDecorated(False)
    win.error_list.setColumnWidth(0, 60)
    win.error_list.setColumnWidth(1, 520)
    win.error_list.itemDoubleClicked.connect(lambda it, _c: _goto(win, it.text(2), int(it.text(3))))
    B = Qt.DockWidgetArea.BottomDockWidgetArea
    win.dock_errors = QDockWidget("Error List", win)
    win.dock_errors.setObjectName("Error List")
    win.dock_errors.setWidget(win.error_list)
    win.addDockWidget(B, win.dock_errors)
    win.dock_find = QDockWidget("Find Results", win)
    win.dock_find.setObjectName("Find Results")
    win.dock_find.setWidget(win.find_results)
    win.addDockWidget(B, win.dock_find)
    win.tabifyDockWidget(win.dock_immediate, win.dock_errors)
    win.tabifyDockWidget(win.dock_errors, win.dock_find)
    win.dock_output.raise_()

    # menu entries
    edit_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Edit")
    edit_menu.addSeparator()
    for text, key, slot in (("Find...", "Ctrl+F", lambda: win.findbar.open(False)),
                            ("Replace...", "Ctrl+H", lambda: win.findbar.open(True)),
                            ("Find Next", "F3", win.findbar.next), ("Find Previous", "Shift+F3", win.findbar.prev),
                            ("Find in Files...", "Ctrl+Shift+F", lambda: find_in_files(win)),
                            ("Go to Line...", "Ctrl+G", lambda: goto_line_dialog(win)),
                            ("Go to Definition", "F12", lambda: goto_definition(win))):
        a = edit_menu.addAction(text, slot)
        a.setShortcut(QKeySequence(key))
    view_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "View")
    view_menu.addAction(win.dock_errors.toggleViewAction())
    view_menu.addAction(win.dock_find.toggleViewAction())
    QShortcut(QKeySequence("Escape"), win.findbar, win.findbar.close_bar)
    proj_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Project")
    proj_menu.addSeparator()
    a = proj_menu.addAction("Check for &Errors", lambda: run_checks(win, show=True))
    a.setShortcut(QKeySequence("Ctrl+Shift+B"))
    proj_menu.addAction("&Build EXE...", lambda: build_exe(win))

    # check after every save
    original_save = win.save_all

    def save_and_check():
        ok = original_save()
        if ok:
            QTimer.singleShot(0, lambda: run_checks(win))
        return ok
    win.save_all = save_and_check
    win.a_save.triggered.disconnect()
    win.a_save.triggered.connect(save_and_check)

    # debugger hover values
    win._hover_pending = []

    # auto-save backups every 60 s
    win._autosave = QTimer(win, interval=60_000)
    win._autosave.timeout.connect(lambda: autosave(win))
    win._autosave.start()


def _project_texts(win) -> dict[str, str]:
    p = win.project
    texts = {}
    for name in p.forms:
        f = win.plugin_for_form(name).code_file(name) if hasattr(win, "plugin_for_form") else             win.plugin.code_file(name)
        texts[f] = win.codeviews[name].editor.text() if name in win.codeviews else \
            (p.folder / f).read_text(encoding="utf-8", errors="replace") if (p.folder / f).exists() else ""
    for mod in p.modules:
        texts[mod] = win.modviews[mod].editor.text() if mod in win.modviews else \
            (p.folder / mod).read_text(encoding="utf-8", errors="replace") if (p.folder / mod).exists() else ""
    return texts


def run_checks(win, show=False) -> list[Diag]:
    if not win.project:
        return []
    try:
        groups: dict = {}                 # multi-language projects: check each file with its language
        for fname, text in _project_texts(win).items():
            fp = win.plugin_for_file(fname) if hasattr(win, "plugin_for_file") else win.plugin
            groups.setdefault(fp.id, (fp, {}))[1][fname] = text
        diags = []
        for fp, texts in groups.values():
            diags += check_project(win.project, fp, texts)
    except Exception as e:  # noqa: BLE001 - never break saving
        diags = [Diag("Warning", f"checker failed: {e}", "", 1)]
    win.error_list.clear()
    for d in diags:
        it = QTreeWidgetItem([d.severity, d.message, d.file, str(d.line)])
        colour = {"Error": Qt.GlobalColor.darkRed, "Warning": Qt.GlobalColor.darkYellow}.get(d.severity)
        if colour is not None:
            it.setForeground(0, colour)
        win.error_list.addTopLevelItem(it)
    errors = sum(d.severity == "Error" for d in diags)
    warnings = sum(d.severity == "Warning" for d in diags)
    win.dock_errors.setWindowTitle(f"Error List ({errors} errors, {warnings} warnings)")
    if errors or show:
        win.dock_errors.show()
        win.dock_errors.raise_()
    win.statusBar().showMessage(f"{errors} error(s), {warnings} warning(s)", 4000)
    return diags


def _goto(win, file: str, line: int):
    if not file or not win.project:
        return
    ed = win._editor_for_file(file)
    if ed is not None:
        ed.goto_line(max(0, line - 1))


def goto_line_dialog(win):
    from PyQt6.QtWidgets import QInputDialog
    cv = win._current_code()
    if cv is None:
        return
    n, ok = QInputDialog.getInt(win, "Go to Line", f"Line (1 - {cv.editor.lines()}):", 1, 1, cv.editor.lines())
    if ok:
        cv.editor.goto_line(n - 1)


def find_in_files(win):
    if not win.project:
        return
    cv = win._current_code()
    sel = cv.editor.textCursor().selectedText() if cv else ""
    dlg = FindInFilesDialog(win, sel)
    if not dlg.exec() or not dlg.text.text():
        return
    flags = 0 if dlg.case.isChecked() else re.I
    pat = dlg.text.text() if dlg.regex.isChecked() else re.escape(dlg.text.text())
    try:
        rx = re.compile(pat, flags)
    except re.error as e:
        win.log(f"bad pattern: {e}")
        return
    texts = _project_texts(win)
    win.find_results.clear()
    hits = 0
    for fname, text in texts.items():
        lines = text.splitlines()
        changed = False
        for i, ln in enumerate(lines, 1):
            if rx.search(ln):
                hits += 1
                win.find_results.addTopLevelItem(QTreeWidgetItem([fname, str(i), ln.strip()[:200]]))
                if dlg.replace.text():
                    lines[i - 1] = rx.sub(dlg.replace.text(), ln)
                    changed = True
        if changed:
            new = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
            ed = win._editor_for_file(fname)
            if ed is not None:
                win._replace_code(type("CV", (), {"editor": ed})(), new)
    win.dock_find.setWindowTitle(f"Find Results ({hits} matches)")
    win.dock_find.show()
    win.dock_find.raise_()


def goto_definition(win):
    cv = win._current_code()
    if cv is None or not win.project:
        return
    ed = cv.editor
    line, col = ed.getCursorPosition()
    text = ed.text(line)
    m = None
    for mm in re.finditer(r"\w+", text):
        if mm.start() <= col <= mm.end():
            m = mm
    if m is None:
        return
    word = m.group()
    if (getattr(ed, "plugin", None) or win.plugin).id.startswith("python"):
        try:
            import jedi
            script = jedi.Script(ed.text(), path=str(ed.path), project=jedi.Project(str(win.project.folder)))
            names = script.goto(line + 1, col, follow_imports=True)
            for n in names:
                if n.module_path and n.line:
                    p = Path(n.module_path)
                    if p.parent.resolve() == win.project.folder.resolve():
                        if p.stem.endswith("_designer"):
                            win.open_generated(p.stem[:-9])
                        else:
                            _goto(win, p.name, n.line)
                        return
                    win.statusBar().showMessage(f"{word}: defined in {p} line {n.line}", 6000)
                    return
        except Exception:  # noqa: BLE001
            pass
    rx = re.compile(rf"^\s*(?:(?:private|public|friend|static)\s+)*(?:def|func|function|sub|subroutine|class|"
                    rf"property\s+get)\s+{re.escape(word)}\b", re.I)
    for fname, t in _project_texts(win).items():
        for i, ln in enumerate(t.splitlines(), 1):
            if rx.search(ln):
                _goto(win, fname, i)
                return
    obj = next((c for d in win.docs.values() for c in d.form.controls if c.name.lower() == word.lower()), None)
    if obj is not None:
        for name, d in win.docs.items():
            if obj in d.form.controls:
                win.open_designer(name)
                d.select(obj)
                return
    win.statusBar().showMessage(f"No definition found for '{word}'", 4000)


def autosave(win):
    """Write modified editors to .radide_backup (crash recovery) without touching the real files."""
    if not win.project:
        return
    backup = win.project.folder / ".radide_backup"
    views = [((getattr(cv.editor, "plugin", None) or win.plugin).code_file(n), cv.editor)
             for n, cv in win.codeviews.items()]
    views += [(m, mv.editor) for m, mv in win.modviews.items()]
    for fname, ed in views:
        if ed.isModified() and not Path(fname).is_absolute() and ".." not in Path(fname).parts:
            (backup / fname).parent.mkdir(parents=True, exist_ok=True)   # website files: css/site.css
            (backup / fname).write_text(ed.text(), encoding="utf-8")


def offer_restore(win):
    """Called after a project opens: restore backups newer than the files."""
    from PyQt6.QtWidgets import QMessageBox
    backup = win.project.folder / ".radide_backup"
    if not backup.exists():
        return
    def name(b):                     # relative path (website files live in sub-folders)
        return b.relative_to(backup).as_posix()
    files = [b for b in backup.rglob("*") if b.is_file()]
    newer = [b for b in files
             if (win.project.folder / name(b)).is_file() and
             b.stat().st_mtime > (win.project.folder / name(b)).stat().st_mtime
             and b.read_text(encoding="utf-8") != (win.project.folder / name(b)).read_text(encoding="utf-8")]
    if newer and QMessageBox.question(
            win, "Recover", "Unsaved changes from a previous session were found for:\n  " +
            "\n  ".join(name(b) for b in newer) + "\n\nRestore them?") == QMessageBox.StandardButton.Yes:
        for b in newer:
            ed = win._editor_for_file(b.name) if "/" not in name(b) else None
            if ed is None and hasattr(win, "open_file"):          # website files (CONTRACTS 8.1)
                ed = win.open_file(win.project.folder / name(b))
            if ed is not None:
                ed.setText(b.read_text(encoding="utf-8"))
    import shutil
    for b in backup.iterdir():
        if b.is_dir():
            shutil.rmtree(b, ignore_errors=True)
        else:
            b.unlink()


def hover_value(win, editor, word: str, global_pos):
    """While paused in the debugger: show the value of the word under the mouse."""
    s = win.session
    if s is None or not s.paused or not word:
        return
    win._hover_pending.append((word, global_pos))
    s.evaluate(word)


def on_eval_result(win, text: str) -> bool:
    """Route an eval result to a pending hover (returns True if consumed)."""
    if win._hover_pending:
        word, pos = win._hover_pending.pop(0)
        QToolTip.showText(pos, f"{word} = {text}")
        return True
    return False


# =================================================================== build exe
def build_exe(win):
    """Project > Build EXE: PyInstaller for Python, ring2exe for Ring."""
    from PyQt6.QtWidgets import QMessageBox

    from .debugger import Session
    from .languages import RunSpec
    if not win.project:
        return
    win.save_all()
    p = win.project
    plugin = win.run_plugin() if hasattr(win, "run_plugin") else win.plugin    # the startup form's language
    folder = p.folder
    interp = win._interpreter()
    if plugin.id.startswith("python"):
        probe = subprocess.run([interp, "-m", "PyInstaller", "--version"], capture_output=True, text=True)
        if probe.returncode != 0:
            if QMessageBox.question(win, "Build EXE", "PyInstaller is not installed for\n" + interp +
                                    "\n\nInstall it now with pip (needs internet)?") != QMessageBox.StandardButton.Yes:
                return
            spec = RunSpec(interp, ["-m", "pip", "install", "pyinstaller"], folder)
            _run_build(win, Session(spec, False, win), then=lambda: build_exe(win))
            return
        args = ["-m", "PyInstaller", "--noconfirm", "--windowed", "--onefile", "--name", p.name,
                "--distpath", str(folder / "dist"), "--workpath", str(folder / "build"),
                "--specpath", str(folder / "build"), "--paths", str(folder)]
        res = folder / "Resources"
        if res.exists():
            args += ["--add-data", f"{res}{';' if sys.platform == 'win32' else ':'}Resources"]
        args.append(str(folder / plugin.code_file(p.startup)))
        _run_build(win, Session(RunSpec(interp, args, folder), False, win),
                   done_msg=f"EXE created: {folder / 'dist' / (p.name + '.exe')}")
    elif plugin.id == "ring-qt":
        spec = plugin.run_spec(folder, p.startup, interp)          # writes _radide_run.ring
        ring2exe = Path(interp).with_name("ring2exe.exe")
        if not ring2exe.exists():
            QMessageBox.warning(win, "Build EXE", f"ring2exe was not found next to {interp}")
            return
        _run_build(win, Session(RunSpec(str(ring2exe), [spec.args[0], "-dist", "-allruntime", "-gui", "-qt"],
                                        folder), False, win),
                   done_msg=f"EXE created in {folder / 'target'}")
    else:
        QMessageBox.information(win, "Build EXE", f"Building an EXE is not available yet for {plugin.display_name}.")


def _run_build(win, session, then=None, done_msg=""):
    win.output.clear()
    win.dock_output.show()
    win.dock_output.raise_()
    win.log(f"------ Build: {session._spec.program} {' '.join(session._spec.args)}")
    session.output.connect(win._append_output)

    def finished(code):
        win.log(f"------ Build {'succeeded' if code == 0 else f'failed (exit code {code})'}")
        if code == 0 and done_msg:
            win.log(done_msg)
            win.statusBar().showMessage(done_msg, 8000)
        if code == 0 and then is not None:
            then()
    session.finished.connect(finished)
    win._build_session = session
    session.start()


__all__ = ["install_tools", "check_project", "run_checks", "hover_value", "on_eval_result", "offer_restore"]
