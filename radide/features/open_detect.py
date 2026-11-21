"""File > Open Folder: detect the project type of a folder without a RAD IDE project file and offer
to create one (engine: radide/project_detect.py).

Called by ``radide.single_instance.open_target`` for every folder (File > Open Folder, "Open folder in
RAD IDE" from Explorer, the command line) and by Solution Explorer > "Detect Project Type..." on folder
workspaces / projects opened in place.

* one confident candidate -> a small dialog: "Detected: Laravel site (Laravel 11.x, PHP ^8.2)" with
  [Create RAD IDE project] [Open in place without project file] [Open as plain folder]; the default
  button is the natural choice (Visual Studio / Cargo / VB6 ... open in place, nothing is written);
* several projects (e.g. ``backend/`` Laravel + ``app/`` Flutter) -> a checkable list -> a ``.radsln``
  with one project per folder;
* nothing -> the folder opens as before (foreign project in place, else a plain folder workspace).

"Don't ask again for this folder" is kept in QSettings (``open_detect/choices``: folder -> action).

Tests answer the dialog through ``TEST_HOOK``: ``TEST_HOOK(detection) -> (action, [candidates],
remember)`` with action "create" | "inplace" | "plain" | "cancel" (or None = the dialog's default).
Without a hook, an offscreen application never shows the dialog (the old behaviour is kept)."""
from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                             QPushButton, QVBoxLayout)

SETTING = "open_detect/choices"
TEST_HOOK = None                      # callable(detection) -> (action, candidates, remember) | None
LAST: dict = {}                       # last detection / action (tests, diagnostics)


# ============================================================================ remembered choices
def _key(folder) -> str:
    return os.path.normcase(str(Path(folder).resolve()))


def _choices(win) -> dict:
    try:
        raw = win.settings.value(SETTING, "") or ""
        d = json.loads(raw) if isinstance(raw, str) and raw else (raw if isinstance(raw, dict) else {})
        return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def remembered(win, folder) -> str:
    return str(_choices(win).get(_key(folder)) or "")


def remember(win, folder, action: str | None) -> None:
    d = _choices(win)
    if action:
        d[_key(folder)] = action
    else:
        d.pop(_key(folder), None)
    try:
        win.settings.setValue(SETTING, json.dumps(d))
    except Exception:  # noqa: BLE001
        pass


# ============================================================================ dialog
def _foreign_ok(folder) -> bool:
    try:
        from .foreign_projects import is_foreign
        return bool(is_foreign(Path(folder)))
    except Exception:  # noqa: BLE001
        return False


class DetectDialog(QDialog):
    """The Open Folder question. ``action`` / ``chosen()`` / ``dont_ask`` after exec()."""

    def __init__(self, det, parent=None):
        super().__init__(parent)
        self.det = det
        self.action = "cancel"
        self.setWindowTitle("Detect Project Type")
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        root = Path(det.root)
        lay.addWidget(QLabel(f"Folder: {root}"))
        self._multi = det.single() is None and len(det.candidates()) > 1
        self.combo = None
        self.list = None
        if self._multi:
            lay.addWidget(self._wrap(QLabel(
                "Several projects were found in this folder. Check the ones to include in the RAD IDE solution "
                "(one project per folder):")))
            self.list = QListWidget()
            self.list.setProperty("i18n_skip_items", True)
            seen = set()
            for c in det.candidates():
                it = QListWidgetItem(c.label(root))
                it.setData(Qt.ItemDataRole.UserRole, c)
                flags = it.flags() | Qt.ItemFlag.ItemIsUserCheckable
                if not (c.can_create and c.language):
                    flags &= ~Qt.ItemFlag.ItemIsEnabled
                it.setFlags(flags)
                key = str(Path(c.folder).resolve()).lower()
                on = c.can_create and bool(c.language) and c.confidence >= 0.6 and key not in seen
                if on:
                    seen.add(key)
                it.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
                tip = [f"Language: {c.language or '-'}", f"Evidence: {', '.join(c.evidence) or '-'}"] + list(c.notes)
                it.setToolTip("\n".join(tip))
                self.list.addItem(it)
            self.list.itemChanged.connect(lambda _it: self._sync())
            lay.addWidget(self.list)
        else:
            cands = [det.single()] + [c for c in det.candidates() if c is not det.single()]
            if len(cands) > 1:
                row = QHBoxLayout()
                row.addWidget(QLabel("Detected:"))
                self.combo = QComboBox()
                self.combo.setProperty("i18n_skip_items", True)
                for c in cands:
                    self.combo.addItem(c.label(root), c)
                self.combo.currentIndexChanged.connect(lambda _i: self._sync())
                row.addWidget(self.combo, 1)
                lay.addLayout(row)
                self.title = None
            else:
                self.title = QLabel()
                f = self.title.font()
                f.setBold(True)
                self.title.setFont(f)
                lay.addWidget(self.title)
            self._cands = cands
            self.info = self._wrap(QLabel())
            self.info.setTextFormat(Qt.TextFormat.PlainText)
            lay.addWidget(self.info)
        self.dont = QCheckBox("Don't ask again for this folder")
        lay.addWidget(self.dont)
        btns = QHBoxLayout()
        self.b_create = QPushButton("Create RAD IDE project")
        self.b_inplace = QPushButton("Open in place without project file")
        self.b_plain = QPushButton("Open as plain folder")
        self.b_cancel = QPushButton("Cancel")
        self.b_create.setToolTip("Creates project.radproj (language, kind, start page, framework) - your files are "
                                 "not moved or changed.")
        self.b_plain.setToolTip("Files, terminal, Git and VS Code tasks only - no RAD IDE project.")
        for b, act in ((self.b_create, "create"), (self.b_inplace, "inplace"), (self.b_plain, "plain"),
                       (self.b_cancel, "cancel")):
            b.clicked.connect(lambda _=False, a=act: self._done(a))
            btns.addWidget(b)
        lay.addLayout(btns)
        self._sync()

    @staticmethod
    def _wrap(lbl: QLabel) -> QLabel:
        lbl.setWordWrap(True)
        return lbl

    def current(self):
        if self.combo is not None:
            return self.combo.currentData()
        return self._cands[0] if not self._multi else None

    def chosen(self) -> list:
        if self._multi:
            out = []
            for i in range(self.list.count()):
                it = self.list.item(i)
                if it.checkState() == Qt.CheckState.Checked:
                    out.append(it.data(Qt.ItemDataRole.UserRole))
            return out
        c = self.current()
        return [c] if c is not None else []

    def default_action(self) -> str:
        if self._multi:
            return "create" if self.chosen() else ("inplace" if _foreign_ok(self.det.root) else "plain")
        c = self.current()
        act = c.default_action if c is not None else "plain"
        if act == "inplace" and not (c.inplace or _foreign_ok(c.folder)):
            act = "plain"
        return act

    def _sync(self) -> None:
        if self._multi:
            n = len(self.chosen())
            self.b_create.setText(f"Create RAD IDE solution ({n} projects)" if n != 1 else
                                  "Create RAD IDE solution (1 project)")
            self.b_create.setEnabled(n > 0)
            self.b_inplace.setEnabled(_foreign_ok(self.det.root))
        else:
            c = self.current()
            if self.title is not None:
                self.title.setText(f"Detected: {c.title}")
            lines = []
            if c.language:
                lines.append(f"Project language: {c.language}" + (f" ({c.project_kind})" if c.project_kind != "app"
                                                                   else ""))
            if c.evidence:
                lines.append(f"Evidence: {', '.join(c.evidence)}")
            if c.web:
                bits = [f"{k} = {c.web[k]}" for k in ("root", "start", "framework", "command") if c.web.get(k)]
                if bits:
                    lines.append("Web: " + "; ".join(bits))
            if c.inplace:
                lines.append(f"Also opens in place natively ({c.inplace_file or c.inplace}).")
            if not c.can_create:
                lines.append("RAD IDE has no project language for this kind of project." if not c.language else
                             "This project opens best in place (no project file needed).")
            lines += list(c.notes)
            try:                                       # multi-line label: translate line by line
                from ..i18n import tr
                lines = [tr(x) for x in lines]
            except Exception:  # noqa: BLE001
                pass
            self.info.setText("\n".join(lines))
            self.b_create.setText("Create RAD IDE project")
            self.b_create.setEnabled(bool(c.can_create and c.language))
            ok = bool(c.inplace) or _foreign_ok(c.folder)
            self.b_inplace.setEnabled(ok)
            self.b_inplace.setToolTip("Opens the project with its own project file (nothing is written into the "
                                      "folder)." if ok else "No other IDE's project file opens this folder in place.")
        btn = {"create": self.b_create, "inplace": self.b_inplace, "plain": self.b_plain}.get(self.default_action())
        for b in (self.b_create, self.b_inplace, self.b_plain, self.b_cancel):
            b.setDefault(b is btn)
            b.setAutoDefault(b is btn)

    def _done(self, action: str) -> None:
        self.action = action
        if action == "cancel":
            self.reject()
        else:
            self.accept()

    @property
    def dont_ask(self) -> bool:
        return self.dont.isChecked()


# ============================================================================ actions
def _ask(win, det):
    """(action, candidates, remember) from the test hook or the dialog; None = do not ask (offscreen)."""
    if TEST_HOOK is not None:
        res = TEST_HOOK(det)
        if res is None:
            dlg = DetectDialog(det, win)
            return dlg.default_action(), dlg.chosen(), False
        action, chosen, rem = (list(res) + [None, None, False])[:3]
        if chosen is None:
            dlg = DetectDialog(det, win)
            chosen = dlg.chosen()
            action = action or dlg.default_action()
        return action, list(chosen), bool(rem)
    try:
        from PyQt6.QtGui import QGuiApplication
        if QGuiApplication.platformName() in ("offscreen", "minimal"):
            return None
    except Exception:  # noqa: BLE001
        pass
    dlg = DetectDialog(det, win)
    if not dlg.exec():
        return "cancel", [], False
    return dlg.action, dlg.chosen(), dlg.dont_ask


def open_plain(win, folder) -> bool:
    from ..foreign.vscode_folder import open_folder
    return bool(open_folder(win, Path(folder)))


def open_inplace(win, folder, cands=()) -> bool:
    from .foreign_projects import open_foreign
    for c in cands or ():
        if c.inplace == "loose":                     # loose C# / Java / Go programs (no project file)
            from ..foreign.loose_sources import open_loose
            if open_loose(win, c.folder, c.kind):
                return True
            continue
        if c.inplace_file and (Path(c.folder) / c.inplace_file).exists():
            if open_foreign(win, Path(c.folder) / c.inplace_file):
                return True
    return bool(open_foreign(win, Path(folder)))


def perform(win, det, action: str, chosen: list) -> bool:
    """Carry out a choice; True when the folder was handled (opened or the user cancelled)."""
    from ..project_detect import create_projects
    root = Path(det.root)
    LAST.update(action=action, chosen=list(chosen), detection=det)
    if action == "cancel":
        return True
    if action == "create":
        chosen = [c for c in chosen if c.can_create and c.language]
        if not chosen:
            action = "inplace" if _foreign_ok(root) else "plain"
        else:
            try:
                path = create_projects(det, chosen)
            except Exception as e:  # noqa: BLE001
                win.log(f"*** Detect Project Type: cannot create the project file: {e}\n{traceback.format_exc()}")
                return False
            for c in chosen:
                where = c.rel(root)
                win.log(f"[open folder] created project.radproj for {c.title} in "
                        f"{root if where == '.' else root / where} (language {c.language})")
                for n in c.notes:
                    win.log(f"  {n}")
            if len(chosen) > 1 or Path(chosen[0].folder).resolve() != root:
                win.log(f"[open folder] solution: {sorted(root.glob('*.radsln'))[0].name if any(root.glob('*.radsln')) else '-'}")
            LAST["created"] = path
            win.open_project(path, ask=False)
            return True
    if action == "inplace":
        if open_inplace(win, root, chosen):
            return True
        action = "plain"
    if action == "plain":
        return open_plain(win, root)
    return False


def open_folder_detect(win, folder, force: bool = False) -> bool:
    """open_target's folder step: True = handled here, False = continue with the old logic."""
    from ..project_detect import detect, is_rad_folder
    folder = Path(folder)
    if is_rad_folder(folder):
        return False
    if not force:
        choice = remembered(win, folder)
        if choice in ("inplace", "plain"):
            det = detect(folder) if choice == "inplace" else None
            if choice == "inplace" and open_inplace(win, folder, det.candidates() if det else ()):
                return True
            return open_plain(win, folder)
    det = detect(folder)
    LAST.clear()
    LAST["detection"] = det
    if not det.candidates():
        if force:
            win.log(f"[open folder] nothing detected in {folder}: it stays a plain folder workspace.")
            try:
                from PyQt6.QtWidgets import QMessageBox
                if TEST_HOOK is None:
                    QMessageBox.information(win, "Detect Project Type",
                                            "Nothing detected in this folder: it opens as a plain folder workspace.")
            except Exception:  # noqa: BLE001
                pass
            return True
        return False
    win.log(f"[open folder] detected in {folder}: {det.summary()}")
    res = _ask(win, det)
    if res is None:
        return False                             # offscreen without a test hook: the old behaviour
    action, chosen, rem = res
    if rem and action in ("inplace", "plain"):
        remember(win, folder, action)
    return perform(win, det, action, chosen)


# ============================================================================ Solution Explorer menu
def _menu_hook(win, item, menu) -> None:
    sln = getattr(win, "sln", None)
    project = getattr(win, "project", None)
    native = getattr(sln, "foreign_native", None)
    if native is None and not getattr(project, "foreign", False):
        return
    root = Path(native) if native is not None else Path(project.folder)
    if root.is_file() or root.name == ".vscode":
        root = root.parent
    if root.suffix.lower() == ".code-workspace":
        root = root.parent
    menu.addSeparator()
    menu.addAction("Detect Project Type...", lambda r=root: detect_project_type(win, r))


def detect_project_type(win, folder=None) -> bool:
    """Solution Explorer > Detect Project Type...: detect the open folder again and offer the choices."""
    if folder is None:
        sln = getattr(win, "sln", None)
        folder = getattr(sln, "foreign_native", None) or getattr(getattr(win, "project", None), "folder", None)
    if folder is None:
        return False
    folder = Path(folder)
    if folder.is_file():
        folder = folder.parent
    remember(win, folder, None)
    return open_folder_detect(win, folder, force=True)


def install(win) -> None:
    try:
        from .solution_ui import MENU_HOOKS
        if _menu_hook not in MENU_HOOKS:
            MENU_HOOKS.append(_menu_hook)
    except Exception:  # noqa: BLE001
        win.log(f"[open detect] {traceback.format_exc()}")
    win.detect_project_type = lambda folder=None: detect_project_type(win, folder)
