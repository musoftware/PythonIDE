"""Project file integrity in the IDE (forms of RAD projects).

* A .form that cannot be read (empty, truncated JSON, git merge conflict markers, not UTF-8, not a form)
  opens nothing and shows why (radide.model.ProjectFileError) - the file is never written afterwards.
* Problems found while loading (a form saved by a newer RAD IDE, repaired names / positions) go to the
  Output window when the form is opened.
* Files changed outside the IDE (another editor, git checkout / pull): when the IDE gets the focus again (and
  every few seconds) the open forms' .form and code files are compared with the disk; a changed file asks
  "Reload?" like Visual Studio (a document with unsaved changes says those changes would be lost). A file
  that changed to something unreadable keeps the IDE's version and says so. Saves of the IDE itself do not
  ask.

Tests: samples/Tests/Robustness/Files/test_files_ide.py."""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

from ..document import FormDocument
from ..model import Form, ProjectFileError

POLL_MS = 2500
LOAD_ERRORS = (ProjectFileError, OSError, UnicodeError, ValueError, KeyError, TypeError)


def _stamp(path: Path):
    try:
        st = path.stat()
        return st.st_mtime_ns, st.st_size
    except OSError:
        return None


class FileIntegrity:
    def __init__(self, win):
        self.win = win
        self.stamps: dict[str, tuple] = {}        # path -> stamp of what the IDE last read / wrote
        self._asking = False
        self.timer = QTimer(win)
        self.timer.setInterval(POLL_MS)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_app_state)

    # ------------------------------------------------------------ helpers
    def _quiet(self) -> bool:
        return bool(os.environ.get("RADIDE_TEST_NO_DIALOGS"))

    def error(self, title: str, text: str) -> None:
        self.win.log("*** " + text.replace("\n", " "))
        try:
            self.win.statusBar().showMessage(text.splitlines()[0], 8000)
        except Exception:  # noqa: BLE001
            pass
        QMessageBox.critical(self.win, title, text)

    def files_of(self, name: str) -> list[tuple[str, Path]]:
        """("form" | "code", path) of an open form of the active project."""
        p = self.win.project
        if p is None:
            return []
        out = []
        doc = self.win.docs.get(name)
        if isinstance(doc, FormDocument) and getattr(doc, "path", None) and str(doc.path).endswith(".form"):
            out.append(("form", Path(doc.path)))
        if name in self.win.codeviews and out:
            try:
                out.append(("code", p.folder / self.win.plugin_for_form(name).code_file(name)))
            except Exception:  # noqa: BLE001
                pass
        return out

    def remember(self, name: str) -> None:
        for _kind, path in self.files_of(name):
            self.stamps[str(path)] = _stamp(path)

    def remember_all(self) -> None:
        for name in set(self.win.docs) | set(self.win.codeviews):
            self.remember(name)

    # ------------------------------------------------------------ open
    def loaded(self, name: str) -> None:
        doc = self.win.docs.get(name)
        if doc is None:
            return
        for w in getattr(doc.form, "warnings", None) or []:
            self.win.log(f"Warning: {name}.form: {w}")
        self.remember(name)

    # ------------------------------------------------------------ external changes
    def _tick(self) -> None:
        """Polling only while the IDE is the active application (like Visual Studio, which asks when it gets
        the focus back) - never a dialog over another program."""
        from PyQt6.QtCore import Qt
        if QApplication.applicationState() == Qt.ApplicationState.ApplicationActive:
            self.check()

    def _on_app_state(self, state) -> None:
        from PyQt6.QtCore import Qt
        if state == Qt.ApplicationState.ApplicationActive:
            QTimer.singleShot(0, self.check)

    def check(self) -> list[str]:
        """Compare the open forms' files with the disk; returns the names that were reloaded."""
        if self._asking or self.win.project is None or getattr(self.win.project, "load_form", None):
            return []
        reloaded = []
        try:
            names = sorted(set(self.win.docs) | set(self.win.codeviews), key=str)
        except Exception:  # noqa: BLE001
            return []
        for name in names:
            try:
                files = self.files_of(name)
            except Exception:  # noqa: BLE001 - a document of another kind: never break the timer
                continue
            for kind, path in files:
                key = str(path)
                now = _stamp(path)
                if key not in self.stamps:
                    self.stamps[key] = now
                    continue
                if now == self.stamps[key]:
                    continue
                self.stamps[key] = now
                if now is None:
                    self.win.log(f"Warning: {path.name} was deleted outside the IDE; Save writes it again.")
                    continue
                if not self._differs(name, kind, path):
                    continue
                if self._ask(name, kind, path) and self.reload(name, kind, path):
                    reloaded.append(name)
        return reloaded

    def _differs(self, name: str, kind: str, path: Path) -> bool:
        try:
            raw = path.read_bytes()
        except OSError:
            return False
        if kind == "form":
            doc = self.win.docs.get(name)
            src = getattr(doc.form, "source", None) if doc is not None else None
            return not (src and src.get("raw") == raw)
        cv = self.win.codeviews.get(name)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return True
        return cv is None or cv.editor.text().replace("\r\n", "\n") != text.replace("\r\n", "\n")

    def _ask(self, name: str, kind: str, path: Path) -> bool:
        if kind == "form":
            doc = self.win.docs.get(name)
            dirty = bool(doc is not None and doc.modified)
        else:
            cv = self.win.codeviews.get(name)
            dirty = bool(cv is not None and cv.editor.isModified())
        text = f"{path}\n\nThis file has been modified outside of RAD IDE.\n\n"
        text += ("It also has unsaved changes in the IDE. Reload it and lose those changes?" if dirty
                 else "Do you want to reload it?")
        self._asking = True
        try:
            r = QMessageBox.question(self.win, "File Modification Detected", text,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        finally:
            self._asking = False
        if r != QMessageBox.StandardButton.Yes:
            self.win.log(f"{path.name} changed on disk: the IDE's version is kept (Save overwrites the file).")
            return False
        return True

    def reload(self, name: str, kind: str, path: Path) -> bool:
        if kind == "code":
            cv = self.win.codeviews.get(name)
            if cv is None:
                return False
            try:
                text = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as e:
                self.error("Reload", f"{path.name} cannot be reloaded: {e}\nThe IDE's version is kept.")
                return False
            cv.editor.setText(text)
            cv.editor.setModified(False)
            self.win._update_tab_titles(name)
            self.win.log(f"Reloaded {path.name} (changed outside the IDE)")
            return True
        doc = self.win.docs.get(name)
        if doc is None:
            return False
        try:
            new = Form.load(path)
        except LOAD_ERRORS as e:
            self.error("Reload", f"{path.name} changed on disk but cannot be reloaded:\n{e}\n"
                                 f"The IDE's version is kept; saving it overwrites the file.")
            return False
        reload_document(doc, new)
        self.win._update_tab_titles(name)
        self.win.log(f"Reloaded {path.name} (changed outside the IDE)")
        for w in new.warnings:
            self.win.log(f"Warning: {name}.form: {w}")
        return True


def reload_document(doc, new: Form) -> None:
    """Replace the form of an open FormDocument with *new* (read from disk): undo history cleared, not
    modified, every view refreshed."""
    names = [c.name for c in doc.selection]
    doc._live = None
    f = doc.form
    f.props, f.controls, f.extra = new.props, new.controls, new.extra
    f.warnings, f.source_version, f.source = new.warnings, new.source_version, new.source
    doc.selection = [c for c in (f.find(n) for n in names) if c]
    doc._undo.clear()
    doc._redo.clear()
    doc.structureChanged.emit()
    doc.controlChanged.emit(None)
    doc.selectionChanged.emit(doc.selected)
    doc.set_modified(False)
    doc.undoStateChanged.emit()


def install(win) -> None:
    feat = FileIntegrity(win)
    win.file_integrity = feat

    def guarded(orig):
        def run(name, *a, **kw):
            known = name in win.docs
            try:
                r = orig(name, *a, **kw)
            except LOAD_ERRORS as e:
                path = win.project.form_path(name) if win.project is not None else Path(f"{name}.form")
                reason = str(e) if isinstance(e, ProjectFileError) else f"{path.name}: {type(e).__name__}: {e}"
                feat.error("Cannot open form", f"The form '{name}' cannot be opened.\n\n{reason}\n\n"
                                               f"The file was not changed.")
                return None
            if not known and name in win.docs:
                feat.loaded(name)
            elif name in win.codeviews:
                feat.remember(name)
            return r
        return run

    win.open_designer = guarded(win.open_designer)
    win.open_code = guarded(win.open_code)

    orig_save = win._save_form

    def save_form(name, *a, **kw):
        try:
            return orig_save(name, *a, **kw)
        finally:
            feat.remember(name)
    win._save_form = save_form
