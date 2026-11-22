"""PE / MFC Resource Workbench in the IDE (radide/pe, docs/PE_MFC.md).

* Tools > PE / MFC Resource Workbench...  (open a Windows .exe / .dll / .ocx / .cpl)
* Opening a Windows program file (File > Open, Solution Explorer) opens it in the workbench instead of the
  text editor; every file has Open With > PE / MFC Resource Workbench in Solution Explorer.
* The workbench tab takes part in Save (asks for a new file name), "modified" checks and Edit > Undo / Redo.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QFileDialog, QLineEdit, QMessageBox, QPlainTextEdit

PE_EXTS = {".exe", ".dll", ".ocx", ".cpl", ".scr", ".mui", ".ax"}


def is_pe_file(path) -> bool:
    p = Path(path)
    if p.suffix.lower() not in PE_EXTS or not p.is_file():
        return False
    try:
        with open(p, "rb") as f:
            head = f.read(0x400)
        if head[:2] != b"MZ" or len(head) < 0x40:
            return False
        off = int.from_bytes(head[0x3C:0x40], "little")
        if off + 4 <= len(head):
            return head[off:off + 4] == b"PE\0\0"
        with open(p, "rb") as f:
            f.seek(off)
            return f.read(4) == b"PE\0\0"
    except OSError:
        return False


class PeWorkbenchFeature:
    def __init__(self, win):
        self.win = win
        self.docs: dict[str, object] = {}
        win.pe_workbench = self
        self._wrap()
        QTimer.singleShot(0, self._menus)
        QTimer.singleShot(0, lambda: QTimer.singleShot(0, self._wrap_openers))
        try:
            from . import solution_ui
            if self._menu_hook not in solution_ui.MENU_HOOKS:
                solution_ui.MENU_HOOKS.append(self._menu_hook)
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------------------- window glue
    def _wrap(self) -> None:
        win = self.win
        win.extension_points.add_document_provider(self)    # the closing question (radide/extension_points.py)
        for attr, op in (("a_undo", "undo"), ("a_redo", "redo")):
            act = getattr(win, attr, None)
            if act is not None:
                act.triggered.connect(lambda _c=False, op=op: self._edit(op))
        if getattr(win, "a_save", None) is not None:
            win.a_save.triggered.connect(lambda _c=False: self._save_current())

    def _wrap_openers(self) -> None:
        win = self.win
        for attr in ("open_any_file", "open_file", "open_module"):
            orig = getattr(win, attr, None)
            if not callable(orig) or getattr(orig, "_rad_pe", False):
                continue

            def make(orig):
                def opener(path, *a, **k):
                    try:
                        p = Path(path)
                        if not p.is_absolute() and getattr(win, "project", None) is not None:
                            p = Path(win.project.folder) / p
                        if is_pe_file(p):
                            return self.open_workbench(p)
                    except Exception as e:  # noqa: BLE001 - never break opening files
                        win.log(f"[pe] {e}")
                    return orig(path, *a, **k)
                opener._rad_pe = True
                return opener
            setattr(win, attr, make(orig))

    @staticmethod
    def _alive(w) -> bool:
        try:
            w.isVisible()
            return True
        except RuntimeError:
            return False

    # DocumentProvider (radide/extension_points.py) ------------------------------------------------------
    def can_open(self, path: Path) -> bool:
        return False                      # programs open by Tools > PE / MFC Workbench

    def open_document(self, path: Path):
        return None

    def save_documents(self) -> None:
        # Not saved by Save All: an edited program is always saved with Save As (never over the original
        # without asking). NOTE: the closing question still counts it as unsaved - after "Save" the IDE
        # closes and the edit is lost; see samples/Tests/Architecture/ExtensionPoints/test_save_participants.py
        return None

    def has_modified_documents(self) -> bool:
        return any(self._alive(d) and d.is_modified() for d in self.docs.values())

    def current(self):
        from ..pe.ui import PeWorkbench
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:
            return None
        return w if isinstance(w, PeWorkbench) else None

    def _edit(self, op: str) -> None:
        wb = self.current()
        if wb is None or isinstance(QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)):
            return
        getattr(wb, op)()

    def _save_current(self) -> None:
        wb = self.current()
        if wb is not None and wb.is_modified():
            wb.save()

    def _title(self, wb) -> None:
        i = self.win.tabs.indexOf(wb)
        if i >= 0:
            self.win.tabs.setTabText(i, f"{wb.path.name} [PE]" + ("*" if wb.is_modified() else ""))

    # ---------------------------------------------------------------- open
    def open_workbench(self, path):
        from ..pe.image import PEError
        from ..pe.ui import PeWorkbench
        p = Path(path).resolve()
        key = str(p).lower()
        w = self.docs.get(key)
        if w is not None and self._alive(w) and self.win.tabs.indexOf(w) >= 0:
            self.win._show_tab(w, f"{p.name} [PE]")
            return w
        if p.stat().st_size > 512 << 20:
            QMessageBox.warning(self.win, "PE / MFC Workbench", f"{p.name} is larger than 512 MB.")
            return None
        try:
            wb = PeWorkbench(p)
        except (PEError, OSError, ValueError) as e:
            QMessageBox.warning(self.win, "PE / MFC Workbench", f"Cannot open {p.name}:\n{e}")
            return None
        self.docs[key] = wb
        wb.modifiedChanged.connect(lambda _m, d=wb: self._title(d))
        wb.saved.connect(lambda _p, d=wb: self._title(d))
        wb.message.connect(lambda t: self.win.statusBar().showMessage(t, 6000))
        wb.setToolTip(str(p))
        self.win._show_tab(wb, f"{p.name} [PE]")
        try:
            self.win.log(f"PE / MFC workbench: {p.name}")
        except Exception:  # noqa: BLE001
            pass
        return wb

    def open_dialog(self) -> None:
        start = str(Path(self.win.project.folder)) if getattr(self.win, "project", None) is not None else ""
        path, _ = QFileDialog.getOpenFileName(self.win, "Open Windows Program (PE / MFC Workbench)", start,
                                              "Windows programs (*.exe *.dll *.ocx *.cpl *.mui);;All files (*.*)")
        if path:
            if not is_pe_file(path):
                QMessageBox.warning(self.win, "PE / MFC Workbench", "This is not a Windows PE program (.exe / .dll).")
                return
            self.open_workbench(path)

    # ---------------------------------------------------------------- menus
    @staticmethod
    def plain(text: str) -> str:
        return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")

    def _menu(self, title: str, parent=None):
        acts = parent.actions() if parent is not None else self.win.menuBar().actions()
        return next((a.menu() for a in acts if a.menu() is not None and self.plain(a.text()) == title), None)

    def _menus(self) -> None:
        tools = self._menu("Tools")
        if tools is None:
            return
        tools.addSeparator()
        self.a_open = tools.addAction("PE / MFC Resource &Workbench...", self.open_dialog)
        self.a_open.setStatusTip("Edit the resources (dialogs, menus, strings, icons, version) of a Windows "
                                 ".exe / .dll, view its code and MFC event handlers")
        self.a_help = None
        try:
            hm = self._menu("Help")
            if hm is not None:
                self.a_help = hm.addAction("PE / MFC Workbench Guide", self.show_guide)
        except Exception:  # noqa: BLE001
            pass

    def show_guide(self) -> None:
        doc = Path(__file__).resolve().parents[2] / "docs" / "PE_MFC.md"
        try:
            self.win.open_any_file(doc)
        except Exception:  # noqa: BLE001
            pass

    def _menu_hook(self, win, item, m) -> None:
        if win is not self.win or item is None:
            return
        from PyQt6.QtCore import Qt
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        try:
            cand = Path(str(data[1]))
            if not cand.is_absolute() and getattr(win, "project", None) is not None:
                cand = Path(win.project.folder) / cand
        except (TypeError, ValueError, IndexError):
            return
        if not is_pe_file(cand):
            return
        sub = next((a.menu() for a in m.actions() if a.menu() is not None and self.plain(a.text()) == "Open With"),
                   None)
        if sub is None:
            m.addSeparator()
            sub = m.addMenu("Open With")
        sub.addAction("PE / MFC Resource Workbench", lambda p=cand: self.open_workbench(p))


def install(win) -> None:
    win.pe_workbench_feature = PeWorkbenchFeature(win)
