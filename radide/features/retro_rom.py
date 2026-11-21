"""ROM workbench in the IDE (radide/retro/rom, docs/RETRO.md "ROM workbench"):

* ROM / disk / tape / patch files (.nes .gb .sfc .md .a26 .xex .atr .d64 .tzx .ips .bps ...) open in the hex
  editor from File > Open, Solution Explorer and Open Folder; .bin / .rom / .prg / .tap open there when the
  content is binary.
* Tools > Retro > ROM Workbench: Open in Hex Editor, Compare Files, Create / Apply Patch, Fix Checksum, ROM Info.
* ROM Hacking projects (radide/languages/retro_romhack.py): Project > ROM Hacking (Set Source ROM, Patch
  Manager, Edit Working Copy, Capture Edits as Patch, Build, Open Output) and ROM / Patches / Build nodes in
  Solution Explorer. The source ROM always opens read-only.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QLineEdit, QMessageBox, QPlainTextEdit, QTreeWidgetItem

ROLE = Qt.ItemDataRole.UserRole
LANG = "retro-romhack"
PATCH_EXTS = {".ips", ".bps", ".ups"}
# opened in the hex editor only when the content looks binary
MAYBE_EXTS = {".bin", ".rom", ".prg", ".tap", ".z80", ".dat", ".sav", ".srm"}


def is_binary(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
    except OSError:
        return False
    return b"\x00" in head or sum(1 for b in head if b < 9 or 13 < b < 32) > len(head) // 10


def wants_hex(path) -> bool:
    from ..retro.rom.detect import HEX_DEFAULT_EXTENSIONS
    p = Path(path)
    ext = p.suffix.lower()
    if ext in HEX_DEFAULT_EXTENSIONS or ext in PATCH_EXTS:
        return p.is_file()
    return ext in MAYBE_EXTS and p.is_file() and is_binary(p)


class RomFeature:
    def __init__(self, win):
        self.win = win
        self.docs: dict[str, object] = {}       # key -> HexDocument / CompareView / PatchManager
        self._read_only_paths: set[str] = set()
        self._wrap()
        self._menus()
        try:
            win.solution.itemDoubleClicked.connect(self._on_tree_dclick)
        except Exception:  # noqa: BLE001
            pass

    # ================================================================== window glue
    def _wrap(self) -> None:
        win = self.win
        orig_save_all = win.save_all
        orig_any_modified = win._any_modified
        orig_fill = win._fill_solution
        orig_open_module = getattr(win, "open_module", None)

        def save_all(*a, **k):
            self.save_documents()
            return orig_save_all(*a, **k)

        def any_modified(*a, **k):
            return any(self._alive(d) and d.is_modified() for d in self.docs.values()) or orig_any_modified(*a, **k)

        def fill_solution(*a, **k):
            r = orig_fill(*a, **k)
            try:
                self._add_tree_nodes()
            except Exception as e:  # noqa: BLE001 - never break Solution Explorer
                win.log(f"[rom workbench] {e}")
            return r

        def open_module(filename, *a, **k):
            p = Path(win.project.folder) / filename if win.project is not None else Path(filename)
            if wants_hex(p) and p.is_file():
                return self.open_hex(p)
            return orig_open_module(filename, *a, **k)

        win.save_all = save_all
        win._any_modified = any_modified
        win._fill_solution = fill_solution
        if callable(orig_open_module):
            win.open_module = open_module
        win.open_hex = self.open_hex
        win.rom_workbench = self
        for attr, op in (("a_undo", "undo"), ("a_redo", "redo"), ("a_cut", "cut"), ("a_copy", "copy"),
                         ("a_paste", "paste"), ("a_delete", "delete"), ("a_select_all", "select_all")):
            act = getattr(win, attr, None)
            if act is not None:
                act.triggered.connect(lambda _c=False, op=op: self._edit(op))
        if getattr(win, "a_save", None) is not None:
            win.a_save.triggered.connect(lambda _c=False: self._save_current())
        # after web_workspace installs win.open_file and editor_extras wraps both for its generic hex view
        QTimer.singleShot(0, self._wrap_open_file)

    def _wrap_open_file(self) -> None:
        win = self.win
        orig_any = win.open_any_file
        if not getattr(orig_any, "_rad_rom", False):
            def open_any_file(path, *a, **k):
                if wants_hex(path):
                    return self.open_hex(path)
                return orig_any(path, *a, **k)
            open_any_file._rad_rom = True
            win.open_any_file = open_any_file
        orig = getattr(win, "open_file", None)
        if not callable(orig) or getattr(orig, "_rad_rom", False):
            return

        def open_file(path, *a, **k):
            p = Path(path)
            if not p.is_absolute() and getattr(win, "project", None) is not None:
                p = Path(win.project.folder) / p
            if wants_hex(p) and p.is_file():
                return self.open_hex(p)
            return orig(path, *a, **k)
        open_file._rad_rom = True
        win.open_file = open_file

    @staticmethod
    def _alive(w) -> bool:
        try:
            w.isVisible()
            return True
        except RuntimeError:
            return False

    def current(self):
        from ..retro.rom.hexdoc import HexDocument
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:
            return None
        return w if isinstance(w, HexDocument) else None

    def _edit(self, op: str) -> None:
        d = self.current()
        if d is None or isinstance(QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)):
            return
        d.edit_op(op)

    def _save_current(self) -> None:
        d = self.current()
        if d is not None and d.is_modified():
            d.save()

    def save_documents(self) -> None:
        for d in list(self.docs.values()):
            if self._alive(d) and d.is_modified() and not getattr(d, "read_only", False):
                d.save()

    def _title(self, w) -> None:
        i = self.win.tabs.indexOf(w)
        if i >= 0:
            name = Path(w.path).name if getattr(w, "path", None) else "Untitled"
            ro = " [read-only]" if getattr(w, "read_only", False) else ""
            self.win.tabs.setTabText(i, name + ro + ("*" if w.is_modified() else ""))

    def _log(self, text: str) -> None:
        try:
            self.win.statusBar().showMessage(text, 6000)
            self.win.log(text)
        except Exception:  # noqa: BLE001
            pass

    # ================================================================== documents
    def _show(self, key: str, w, title: str):
        self.docs[key] = w
        self.win._show_tab(w, title)
        self._title(w)
        return w

    def _existing(self, key: str):
        w = self.docs.get(key)
        if w is not None and (not self._alive(w) or self.win.tabs.indexOf(w) < 0):
            self.docs.pop(key, None)
            return None
        return w

    def open_hex(self, path, read_only: bool | None = None):
        from ..retro.rom.hexdoc import HexDocument
        p = Path(path).resolve()
        key = str(p).lower()
        if read_only is None:
            read_only = key in self._read_only_paths or self._is_source_rom(p)
        w = self._existing(key)
        if w is not None:
            self.win._show_tab(w, p.name)
            return w
        if not p.is_file():
            QMessageBox.warning(self.win, "Hex Editor", f"File not found: {p}")
            return None
        if p.stat().st_size > 512 << 20:
            QMessageBox.warning(self.win, "Hex Editor", f"{p.name} is larger than 512 MB.")
            return None
        try:
            w = HexDocument(p, read_only=read_only)
        except OSError as e:
            QMessageBox.warning(self.win, "Hex Editor", f"Cannot open {p.name}:\n{e}")
            return None
        w.setToolTip(str(p))
        w.modifiedChanged.connect(lambda _m, d=w: self._title(d))
        w.saved.connect(lambda d=w: self._after_save(d))
        w.message.connect(self._log)
        w.compareRequested.connect(self.compare)
        self._load_project_tables(w)
        self._show(key, w, p.name)
        w.view.setFocus()
        return w

    def _after_save(self, d) -> None:
        self._title(d)
        try:
            from ..retro.filebus import file_changed
            file_changed(self.win, d.path, source=d)
        except Exception:  # noqa: BLE001
            pass
        self._log(f"Saved {Path(d.path).name}")

    def _load_project_tables(self, doc) -> None:
        rp = self._romproject()
        if rp is None:
            return
        for t in rp.tables:
            p = rp.path(t)
            if p.is_file():
                try:
                    from ..retro.rom.tbl import Table
                    tbl = Table.load(p)
                    doc.tables.append(tbl)
                    idx = doc.textmode.count() - 1
                    doc.textmode.insertItem(idx, f"Table: {tbl.name}", ("table", len(doc.tables) - 1))
                except OSError:
                    pass

    def compare(self, left, right=None):
        from ..retro.rom.diffview import CompareView
        if right is None:
            right, _ = QFileDialog.getOpenFileName(self.win, "Compare With", str(Path(left).parent), "All files (*)")
            if not right:
                return None
        key = f"compare:{Path(left).resolve()}|{Path(right).resolve()}".lower()
        w = self._existing(key)
        if w is None:
            try:
                w = CompareView(left, right)
            except OSError as e:
                QMessageBox.warning(self.win, "Compare Files", str(e))
                return None
            self._show(key, w, f"{Path(left).name} vs {Path(right).name}")
            self.win.tabs.setTabText(self.win.tabs.indexOf(w), f"{Path(left).name} vs {Path(right).name}")
        else:
            self.win._show_tab(w, "")
        return w

    # ================================================================== menus
    def _menu(self, title: str):
        return next((a.menu() for a in self.win.menuBar().actions() if a.menu() is not None and
                     a.text().replace("&", "") == title), None)

    def _menus(self) -> None:
        try:
            from ..retro.menu import section
            m = section(self.win, "ROM &Workbench")
        except Exception:  # noqa: BLE001 - the shared menu helper is optional
            tools = self._menu("Tools")
            m = tools.addMenu("ROM &Workbench") if tools is not None else None
        if m is not None:
            m.addAction("Open in &Hex Editor...", self.open_dialog)
            m.addAction("&Compare Files...", self.compare_dialog)
            m.addSeparator()
            m.addAction("Create &Patch (IPS / BPS / UPS)...", self.create_patch)
            m.addAction("&Apply Patch...", self.apply_patch)
            m.addAction("Fix Header &Checksum of a File...", self.fix_checksum_file)
            m.addAction("ROM &Info...", self.rom_info_file)
            self.menu = m
        pm = self._menu("Project")
        if pm is not None:
            sub = pm.addMenu("ROM &Hacking")
            self.project_menu = sub
            self.a_set_rom = sub.addAction("Set &Source ROM...", lambda: self._pm_call("choose_rom"))
            self.a_manager = sub.addAction("&Patch Manager", self.open_manager)
            self.a_view_rom = sub.addAction("&View Source ROM (read-only)", self.view_source)
            sub.addSeparator()
            self.a_work = sub.addAction("Edit &Working Copy", lambda: self._pm_call("edit_work"))
            self.a_capture = sub.addAction("&Capture Edits as Patch...", lambda: self._pm_call("capture"))
            self.a_add_patch = sub.addAction("&Add Patch...", lambda: self._pm_call("add_patch"))
            sub.addSeparator()
            self.a_build = sub.addAction("&Build Patched ROM", self.build_project)
            self.a_output = sub.addAction("&Open Build Output", self.open_output)
            sub.aboutToShow.connect(self._update_menu)

    def _update_menu(self) -> None:
        on = self._romproject() is not None
        for a in (self.a_set_rom, self.a_manager, self.a_view_rom, self.a_work, self.a_capture, self.a_add_patch,
                  self.a_build, self.a_output):
            a.setEnabled(on)

    def _start(self) -> str:
        p = self.win.project
        return str(p.folder) if p is not None else ""

    def open_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self.win, "Open in Hex Editor", self._start(), "All files (*)")
        if f:
            self.open_hex(f, read_only=False if not self._is_source_rom(Path(f)) else None)

    def compare_dialog(self) -> None:
        a, _ = QFileDialog.getOpenFileName(self.win, "Compare: first file", self._start(), "All files (*)")
        if a:
            self.compare(a)

    def create_patch(self) -> None:
        from ..retro.rom.dialogs import CreatePatchDialog
        d = self.current()
        dlg = CreatePatchDialog(self.win, "", str(d.path) if d is not None and d.path else "")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._log(f"Patch written: {dlg.result_path} ({dlg.result_size:,} bytes)")

    def apply_patch(self) -> None:
        from ..retro.rom.dialogs import ApplyPatchDialog
        dlg = ApplyPatchDialog(self.win)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._log(f"Patched ROM written: {dlg.result_path}")
            self.open_hex(dlg.result_path)

    def fix_checksum_file(self) -> None:
        d = self.current()
        if d is not None and not d.read_only:
            d.fix_checksum()
            return
        f, _ = QFileDialog.getOpenFileName(self.win, "Fix Header Checksum", self._start(), "All files (*)")
        if f:
            doc = self.open_hex(f, read_only=False if not self._is_source_rom(Path(f)) else None)
            if doc is not None:
                doc.fix_checksum()

    def rom_info_file(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self.win, "ROM Info", self._start(), "All files (*)")
        if f:
            doc = self.open_hex(f, read_only=True)
            if doc is not None:
                doc.side.setCurrentIndex(0)

    # ================================================================== ROM Hacking projects
    def _romproject(self, project=None):
        p = project or self.win.project
        if p is None or getattr(p, "language", "") != LANG:
            return None
        from ..retro.rom.project import RomProject
        try:
            return RomProject.load(p.folder)
        except (OSError, ValueError):
            return None

    def _is_source_rom(self, path: Path) -> bool:
        for st in getattr(self.win, "_pstates", {}).values():
            proj = st.get("project") if isinstance(st, dict) else None
            rp = self._romproject(proj) if proj is not None else None
            if rp is not None and rp.rom_path is not None:
                try:
                    if rp.rom_path.resolve() == path.resolve():
                        return True
                except OSError:
                    pass
        rp = self._romproject()
        return bool(rp and rp.rom_path and rp.rom_path.resolve() == path.resolve())

    def open_manager(self):
        from ..retro.rom.projectui import PatchManager
        p = self.win.project
        if self._romproject() is None:
            QMessageBox.information(self.win, "ROM Hacking", "Open a ROM Hacking project first.")
            return None
        key = f"patchmanager:{Path(p.folder).resolve()}".lower()
        w = self._existing(key)
        if w is None:
            w = PatchManager(p.folder)
            w.openFile.connect(lambda path, ro: self.open_hex(path, read_only=ro))
            w.runRequested.connect(lambda: self.win.run_project(debug=False))
            w.changed.connect(self._refresh_tree)
            self.docs[key] = w
            self.win._show_tab(w, "Patch Manager")
        else:
            w.reload_from_disk()
            self.win._show_tab(w, "Patch Manager")
        return w

    def _pm_call(self, name: str):
        w = self.open_manager()
        if w is not None:
            return getattr(w, name)()
        return None

    def view_source(self):
        rp = self._romproject()
        if rp is None or rp.rom_path is None or not rp.rom_path.is_file():
            QMessageBox.information(self.win, "ROM Hacking", "Set the source ROM first.")
            return None
        return self.open_hex(rp.rom_path, read_only=True)

    def build_project(self):
        rp = self._romproject()
        if rp is None:
            return None
        self.win.save_all()
        try:
            out = rp.build(log=self.win.log)
        except Exception as e:  # noqa: BLE001 - PatchError / OSError: shown to the user
            self.win.log(f"*** Build failed: {e}")
            QMessageBox.warning(self.win, "Build", str(e))
            return None
        self._refresh_tree()
        return out

    def open_output(self):
        rp = self._romproject()
        if rp is None:
            return None
        if not rp.output_path.is_file():
            self.build_project()
        if rp.output_path.is_file():
            return self.open_hex(rp.output_path, read_only=True)
        return None

    def _refresh_tree(self) -> None:
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass

    def _add_tree_nodes(self) -> None:
        win = self.win
        try:
            from .solution_ui import PROJECT_ROLE
        except ImportError:
            return
        tree = win.solution
        stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        style = win.style()
        while stack:
            it = stack.pop()
            stack.extend(it.child(i) for i in range(it.childCount()))
            data = it.data(0, ROLE)
            if not data or data[0] != "project":
                continue
            key = it.data(0, PROJECT_ROLE)
            st = getattr(win, "_pstates", {}).get(key)
            project = st["project"] if st else None
            rp = self._romproject(project) if project is not None else None
            if rp is None:
                continue
            if any((it.child(i).data(0, ROLE) or ("",))[0] == "romhack" for i in range(it.childCount())):
                continue

            def node(text, kind, path, tip, icon):
                n = QTreeWidgetItem([text])
                n.setData(0, ROLE, (kind, str(path)))
                n.setData(0, PROJECT_ROLE, key)
                n.setToolTip(0, tip)
                n.setIcon(0, style.standardIcon(icon))
                return n
            root = node("ROM Hacking", "romhack", project.folder, "Double-click: Patch Manager",
                        style.StandardPixmap.SP_DriveFDIcon)
            if rp.rom_path is not None:
                root.addChild(node(f"Source ROM: {rp.rom_path.name}", "romhack_rom", rp.rom_path,
                                   "The clean ROM (opens read-only)", style.StandardPixmap.SP_FileIcon))
            pnode = node(f"Patches ({len(rp.patches)})", "romhack", project.folder, "Patch Manager",
                         style.StandardPixmap.SP_DirIcon)
            for e in rp.patches:
                pnode.addChild(node(Path(e.file).name + ("" if e.enabled else "  (disabled)"), "romhack_file",
                                    rp.path(e.file), e.note or e.file, style.StandardPixmap.SP_FileIcon))
            root.addChild(pnode)
            if rp.work_path is not None and rp.work_path.is_file():
                root.addChild(node(f"Working copy: {rp.work_path.name}", "romhack_file", rp.work_path,
                                   "Edit, save, then Capture Edits as Patch", style.StandardPixmap.SP_FileIcon))
            if rp.output_path.is_file():
                root.addChild(node(f"Build: {rp.output_path.name}", "romhack_out", rp.output_path,
                                   "The patched ROM (Build output)", style.StandardPixmap.SP_DialogApplyButton))
            pos = 1 if it.childCount() and (it.child(0).data(0, ROLE) or ("",))[0] == "references" else 0
            it.insertChild(pos, root)
            root.setExpanded(True)
            pnode.setExpanded(True)

    def _on_tree_dclick(self, item, _col) -> None:
        data = item.data(0, ROLE)
        if not data or not str(data[0]).startswith("romhack"):
            return
        try:
            from .solution_ui import PROJECT_ROLE
            key = item.data(0, PROJECT_ROLE)
            st = getattr(self.win, "_pstates", {}).get(key)
            if st and st.get("project") is not None and st["project"] is not self.win.project:
                self.win.activate_project(st["project"])
        except Exception:  # noqa: BLE001
            pass
        kind, path = data[0], data[1]
        if kind == "romhack":
            self.open_manager()
        elif kind in ("romhack_rom", "romhack_out"):
            self.open_hex(path, read_only=True)
        else:
            self.open_hex(path, read_only=False)


def install(win) -> None:
    win.rom_feature = RomFeature(win)
