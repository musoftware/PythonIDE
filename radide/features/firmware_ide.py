"""Firmware & ECU workbench in the IDE (radide/firmware/ui, docs/FIRMWARE.md "Workbench").

* Tools > Firmware & ECU: Open Firmware in Workbench..., Open EEPROM Dump (read-only)..., New ECU Project...,
  New ECU Project (Demo Firmware), Compare Firmware Files..., Getting Started.
* Project > ECU Project > Open Workbench / Find Maps / Verify Checksums / Compare with Original / Analyze /
  Build in Workbench (added to the ECU Project menu of radide/features/firmware_project.py when it exists).
* Opening an ECU project (language "firmware-ecu", ecu.json) opens its workbench once per session.
* File associations: .s19 .srec .mot .a2l .ori, and .mod / .hex when their content is firmware (binary .mod,
  Intel HEX .hex) open in the workbench; .bin only inside an ECU project folder (ordinary .bin files keep their
  hex editor / ROM handling). Every file has Open With > Firmware & ECU Workbench in Solution Explorer.
* The workbench tab takes part in Save / Save All / "modified" checks and in Edit > Undo / Redo.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QFileSystemWatcher, Qt, QTimer
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QLineEdit, QMessageBox, QPlainTextEdit

ROLE = Qt.ItemDataRole.UserRole
LANG = "firmware-ecu"
ALWAYS_EXTS = {".s19", ".s28", ".s37", ".srec", ".mot", ".ori"}
CONTENT_EXTS = {".mod", ".hex"}                # only when the content is firmware (binary .mod, Intel HEX .hex)
EEPROM_EXTS = {".eep", ".e2p", ".eeprom"}


def _is_binary(p: Path) -> bool:
    try:
        with open(p, "rb") as f:
            head = f.read(4096)
    except OSError:
        return False
    return b"\x00" in head or sum(1 for b in head if b < 9 or 13 < b < 32) > len(head) // 10


class FirmwareIde:
    def __init__(self, win):
        self.win = win
        self.docs: dict[str, object] = {}
        self._auto_opened: set[str] = set()
        self.watcher = QFileSystemWatcher()
        self.watcher.fileChanged.connect(self._on_disk_change)
        self._wrap()
        QTimer.singleShot(0, self._menus)                      # after firmware_project.py made its menu
        QTimer.singleShot(0, lambda: QTimer.singleShot(0, self._wrap_openers))
        try:
            from . import solution_ui
            if self._menu_hook not in solution_ui.MENU_HOOKS:
                solution_ui.MENU_HOOKS.append(self._menu_hook)
        except Exception:  # noqa: BLE001
            pass

    # ================================================================== window glue
    def _wrap(self) -> None:
        win = self.win
        orig_save_all = win.save_all
        orig_any_modified = win._any_modified
        orig_fill = win._fill_solution

        def save_all(*a, **k):
            self.save_documents()
            return orig_save_all(*a, **k)

        def any_modified(*a, **k):
            return any(self._alive(d) and d.is_modified() for d in self.docs.values()) or orig_any_modified(*a, **k)

        def fill_solution(*a, **k):
            r = orig_fill(*a, **k)
            QTimer.singleShot(0, self._maybe_auto_open)
            return r

        win.save_all = save_all
        win._any_modified = any_modified
        win._fill_solution = fill_solution
        win.firmware_ide = self
        for attr, op in (("a_undo", "undo"), ("a_redo", "redo"), ("a_copy", "copy"), ("a_select_all", "select_all")):
            act = getattr(win, attr, None)
            if act is not None:
                act.triggered.connect(lambda _c=False, op=op: self._edit(op))
        if getattr(win, "a_save", None) is not None:
            win.a_save.triggered.connect(lambda _c=False: self._save_current())

    def _wrap_openers(self) -> None:
        win = self.win
        for attr in ("open_any_file", "open_file", "open_module"):
            orig = getattr(win, attr, None)
            if not callable(orig) or getattr(orig, "_rad_fw", False):
                continue

            def make(orig, attr):
                def opener(path, *a, **k):
                    p = Path(path)
                    if not p.is_absolute() and getattr(win, "project", None) is not None:
                        p = Path(win.project.folder) / p
                    try:
                        if p.is_file() and self.wants(p):
                            return self.open_file(p)
                    except Exception as e:  # noqa: BLE001 - never break opening files
                        win.log(f"[firmware] {e}")
                    return orig(path, *a, **k)
                opener._rad_fw = True
                return opener
            setattr(win, attr, make(orig, attr))

    @staticmethod
    def _alive(w) -> bool:
        try:
            w.isVisible()
            return True
        except RuntimeError:
            return False

    def current(self):
        from ..firmware.ui.workbench import FirmwareWorkbench
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:
            return None
        return w if isinstance(w, FirmwareWorkbench) else None

    def _edit(self, op: str) -> None:
        wb = self.current()
        if wb is None or isinstance(QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)):
            return
        if wb.doc.view.hasFocus():
            return                          # the hex view handles its own keys
        wb.edit_op(op)

    def _save_current(self) -> None:
        wb = self.current()
        if wb is not None and wb.is_modified():
            wb.save()

    def save_documents(self) -> None:
        for wb in list(self.docs.values()):
            if self._alive(wb) and wb.is_modified() and not wb.read_only:
                wb.save()

    def _title(self, wb) -> None:
        i = self.win.tabs.indexOf(wb)
        if i >= 0:
            self.win.tabs.setTabText(i, self._tab_name(wb) + ("*" if wb.is_modified() else ""))

    @staticmethod
    def _tab_name(wb) -> str:
        if wb.proj is not None:
            return f"ECU: {wb.proj.name}"
        return f"{wb.path.name} [Firmware" + (", read-only]" if wb.read_only else "]")

    def _log(self, text: str) -> None:
        try:
            self.win.statusBar().showMessage(text, 6000)
            self.win.log(text)
        except Exception:  # noqa: BLE001
            pass

    # ================================================================== associations
    def _ecu_folder_of(self, p: Path) -> Path | None:
        from ..firmware.ui.adapters import is_ecu_project
        for parent in list(p.resolve().parents)[:4]:
            if is_ecu_project(parent):
                return parent
        return None

    def wants(self, path) -> bool:
        """True when *path* should open in the workbench instead of the default editor."""
        p = Path(path)
        ext = p.suffix.lower()
        if ext in ALWAYS_EXTS:
            return True
        if ext == ".a2l":
            return self._active() is not None
        if ext == ".mod":
            return _is_binary(p)
        if ext == ".hex":
            from ..firmware.ui.adapters import sniff_format
            return sniff_format(p) == "ihex" and (self._in_ecu_project(p) or self._no_code_project())
        if ext in EEPROM_EXTS:
            return True
        if ext == ".bin":
            return self._in_ecu_project(p)
        return False

    def _no_code_project(self) -> bool:
        proj = getattr(self.win, "project", None)
        return proj is None or getattr(proj, "language", "") == LANG

    def _in_ecu_project(self, p: Path) -> bool:
        proj = getattr(self.win, "project", None)
        if proj is None or getattr(proj, "language", "") != LANG:
            return False
        try:
            p.resolve().relative_to(Path(proj.folder).resolve())
            return True
        except ValueError:
            return False

    def _active(self):
        wb = self.current()
        if wb is not None:
            return wb
        alive = [w for w in self.docs.values() if self._alive(w)]
        return alive[-1] if alive else None

    def open_file(self, path):
        """Route one file: an A2L joins the active workbench, project files open the project workbench."""
        p = Path(path)
        ext = p.suffix.lower()
        if ext == ".a2l":
            wb = self._active()
            if wb is not None:
                wb.import_a2l(p)
                self.win._show_tab(wb, self._tab_name(wb))
                return wb
        folder = self._ecu_folder_of(p) if ext == ".bin" else None
        if folder is not None:
            wb = self.open_project_workbench(folder)
            if wb is not None and wb.proj is not None and wb.proj.working_path is not None and \
                    wb.proj.working_path.resolve() != p.resolve():
                wb.compare(p)
            return wb
        return self.open_workbench(p, eeprom=True if ext in EEPROM_EXTS else None)

    # ================================================================== documents
    def _existing(self, key: str):
        w = self.docs.get(key)
        if w is not None and (not self._alive(w) or self.win.tabs.indexOf(w) < 0):
            self.docs.pop(key, None)
            return None
        return w

    def _show(self, key: str, wb):
        self.docs[key] = wb
        wb.modifiedChanged.connect(lambda _m, d=wb: self._title(d))
        wb.saved.connect(lambda d=wb: self._after_save(d))
        wb.message.connect(lambda t: self.win.statusBar().showMessage(t, 5000))
        wb.openInIde.connect(self._open_in_ide)
        wb.projectChanged.connect(lambda: QTimer.singleShot(0, self._refresh_solution))
        self._integrations(wb)
        wb.setToolTip(str(wb.proj.folder if wb.proj is not None else wb.path))
        self.win._show_tab(wb, self._tab_name(wb))
        self._title(wb)
        if wb.path is not None and Path(wb.path).is_file():
            self.watcher.addPath(str(wb.path))
        return wb

    def _integrations(self, wb) -> None:
        """Links to the full views of radide/features/firmware_maps.py and firmware_analysis.py (when installed)."""
        win = self.win
        maps = getattr(win, "firmware_maps", None)
        if maps is not None and callable(getattr(maps, "open_maps", None)):
            def open_maps(b):
                orig = b.proj.original_path if b.proj is not None else None
                return maps.open_maps(str(b.path), original=str(orig) if orig is not None else None)
            wb.integrations["maps"] = open_maps
        ana = getattr(win, "firmware_analysis", None)
        if ana is not None and callable(getattr(ana, "open_analysis", None)):
            def open_analysis(b):
                try:
                    base = int(b.base_edit.text().strip() or "0", 0)
                except ValueError:
                    base = None
                return ana.open_analysis(str(b.path), base=base or None, arch=b.arch.currentData() or "")
            wb.integrations["analysis"] = open_analysis
        wb.a_full_maps.setEnabled("maps" in wb.integrations)
        wb.a_full_analysis.setEnabled("analysis" in wb.integrations)

    def _refresh_solution(self) -> None:
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass

    def _after_save(self, wb) -> None:
        self._title(wb)
        try:
            from ..retro.filebus import file_changed
            file_changed(self.win, wb.path, source=wb)
        except Exception:  # noqa: BLE001
            pass

    def _open_in_ide(self, path: str, read_only: bool) -> None:
        rom = getattr(self.win, "rom_workbench", None)
        if rom is not None:
            rom.open_hex(path, read_only=read_only)

    def _on_disk_change(self, path: str) -> None:
        """The working copy changed on disk (Build / Correct of the ECU project menu): reload unmodified tabs."""
        for wb in list(self.docs.values()):
            if self._alive(wb) and wb.path is not None and str(wb.path) == path and not wb.is_modified():
                QTimer.singleShot(200, lambda w=wb: self._reload(w))
        if Path(path).is_file():
            self.watcher.addPath(path)

    def _reload(self, wb) -> None:
        try:
            data = Path(wb.path).read_bytes() if wb.img.fmt in ("binary", "raw") else None
        except OSError:
            return
        if data is not None and data != wb.data():
            from ..retro.rom.buffer import HexBuffer
            wb.doc.buf = HexBuffer(data, wb.path if wb.doc.path else None)
            wb.doc.view.set_buffer(wb.doc.buf)
            wb.mapedit.refresh()
            wb.verify_checksums(show=False)
            wb.compare(quiet=True, keep=True)
            wb.log(f"Reloaded {Path(wb.path).name} (changed on disk)")

    def open_workbench(self, path, eeprom: bool | None = None, read_only: bool | None = None):
        from ..firmware.ui.workbench import FirmwareWorkbench
        p = Path(path).resolve()
        key = f"file:{p}".lower()
        w = self._existing(key)
        if w is not None:
            self.win._show_tab(w, self._tab_name(w))
            return w
        if not p.is_file():
            QMessageBox.warning(self.win, "Firmware & ECU", f"File not found: {p}")
            return None
        if p.stat().st_size > 64 << 20:
            QMessageBox.warning(self.win, "Firmware & ECU", f"{p.name} is larger than 64 MB.")
            return None
        if eeprom is None:
            from ..firmware.ui.eeprom import is_eeprom_size
            eeprom = p.suffix.lower() in EEPROM_EXTS or (is_eeprom_size(p.stat().st_size) and
                                                         p.stat().st_size <= 8192)
        try:
            wb = FirmwareWorkbench(path=p, eeprom=eeprom, read_only=read_only)
        except Exception as e:  # noqa: BLE001 - unreadable file / format error: shown to the user
            QMessageBox.warning(self.win, "Firmware & ECU", f"Cannot open {p.name}:\n{e}")
            return None
        self._log(f"Firmware workbench: {p.name}")
        return self._show(key, wb)

    def open_project_workbench(self, folder=None):
        from ..firmware.ui.adapters import is_ecu_project
        from ..firmware.ui.workbench import FirmwareWorkbench
        if folder is None:
            proj = getattr(self.win, "project", None)
            folder = proj.folder if proj is not None else None
        if folder is None or not is_ecu_project(folder):
            QMessageBox.information(self.win, "ECU Project", "Open an ECU project first (File > New Project > "
                                    "Firmware, or Tools > Firmware & ECU > New ECU Project...).")
            return None
        f = Path(folder).resolve()
        key = f"project:{f}".lower()
        w = self._existing(key)
        if w is not None:
            self.win._show_tab(w, self._tab_name(w))
            return w
        try:
            wb = FirmwareWorkbench(project_folder=f)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self.win, "ECU Project", f"Cannot open the ECU project:\n{e}")
            return None
        self._auto_opened.add(str(f).lower())
        self._log(f"ECU workbench: {f.name}")
        return self._show(key, wb)

    def _maybe_auto_open(self) -> None:
        proj = getattr(self.win, "project", None)
        if proj is None or getattr(proj, "language", "") != LANG:
            return
        key = str(Path(proj.folder).resolve()).lower()
        if key in self._auto_opened:
            return
        self._auto_opened.add(key)
        from ..firmware.ui.adapters import is_ecu_project
        if is_ecu_project(proj.folder):
            self.open_project_workbench(proj.folder)

    # ================================================================== menus
    @staticmethod
    def plain(text: str) -> str:
        """Menu text without mnemonics ("&Firmware && ECU" -> "Firmware & ECU")."""
        return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")

    def _menu(self, title: str, parent=None):
        acts = (parent.actions() if parent is not None else self.win.menuBar().actions())
        return next((a.menu() for a in acts if a.menu() is not None and self.plain(a.text()) == title), None)

    def _menus(self) -> None:
        tools = self._menu("Tools")
        if tools is not None:
            m = self._menu("Firmware & ECU", tools) or tools.addMenu("&Firmware && ECU")
            m.addAction("&Open Firmware in Workbench...", self.open_dialog)
            m.addAction("Open &EEPROM Dump (read-only)...", self.open_eeprom_dialog)
            m.addSeparator()
            m.addAction("&New ECU Project...", self.new_project_dialog)
            m.addAction("New ECU Project (&Demo Firmware)...", lambda: self.new_project_dialog(demo=True))
            m.addSeparator()
            m.addAction("&Compare Firmware Files...", self.compare_dialog)
            m.addAction("&Getting Started", self.getting_started)
            self.tools_menu = m
        pm = self._menu("Project")
        if pm is not None:
            sub = self._menu("ECU Project", pm) or pm.addMenu("&ECU Project")
            sub.addSeparator()
            self.a_open = sub.addAction("Open &Workbench", self.open_project_workbench)
            self.a_find = sub.addAction("&Find Maps (workbench)", lambda: self._wb_call("find_maps"))
            self.a_verify = sub.addAction("&Verify Checksums (workbench)", lambda: self._wb_call("verify_checksums"))
            self.a_compare = sub.addAction("&Compare with Original (workbench)", lambda: self._wb_call("compare"))
            self.a_analyze = sub.addAction("&Analyze (workbench)", lambda: self._wb_call("analyze"))
            self.a_build = sub.addAction("&Build in Workbench", lambda: self._wb_call("build"))
            self.project_menu = sub
            sub.aboutToShow.connect(self._update_menu)

    def _update_menu(self) -> None:
        proj = getattr(self.win, "project", None)
        on = proj is not None and getattr(proj, "language", "") == LANG
        for a in (self.a_open, self.a_find, self.a_verify, self.a_compare, self.a_analyze, self.a_build):
            a.setEnabled(on)

    def _wb_call(self, name: str):
        wb = self.open_project_workbench()
        if wb is None:
            return None
        return getattr(wb, name)()

    def _start(self) -> str:
        p = getattr(self.win, "project", None)
        return str(p.folder) if p is not None else ""

    FILTER = ("Firmware (*.bin *.ori *.mod *.hex *.s19 *.srec *.mot *.rom *.dump *.eep *.e2p);;All files (*)")

    def open_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self.win, "Open Firmware in Workbench", self._start(), self.FILTER)
        return self.open_workbench(f) if f else None

    def open_eeprom_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self.win, "Open EEPROM Dump (read-only)", self._start(),
                                           "EEPROM dumps (*.bin *.eep *.e2p *.rom);;All files (*)")
        return self.open_workbench(f, eeprom=True, read_only=True) if f else None

    def compare_dialog(self):
        a, _ = QFileDialog.getOpenFileName(self.win, "Compare: original / first file", self._start(), self.FILTER)
        if not a:
            return None
        b, _ = QFileDialog.getOpenFileName(self.win, "Compare: modified / second file", str(Path(a).parent),
                                           self.FILTER)
        if not b:
            return None
        return self.compare_files(a, b)

    def compare_files(self, a, b):
        wb = self.open_workbench(b, read_only=True)
        if wb is not None:
            wb.compare(a)
        return wb

    def getting_started(self):
        wb = self._active()
        if wb is None:
            from ..firmware.ui.workbench import StartPage
            page = StartPage()
            page.setObjectName("FirmwareGettingStarted")
            self.win._show_tab(page, "Firmware & ECU - Getting Started")
            return page
        self.win._show_tab(wb, self._tab_name(wb))
        wb.tabs.setCurrentIndex(0)
        return wb

    def new_project_dialog(self, demo: bool = False, source=None, folder=None, name: str | None = None):
        """New ECU project from a firmware file (or the synthetic demo image); opens it in the IDE."""
        if not demo and source is None:
            source, _ = QFileDialog.getOpenFileName(self.win, "New ECU Project: choose the original file",
                                                    self._start(), self.FILTER)
            if not source:
                return None
        if name is None:
            base = "DemoEcu" if demo else Path(source).stem
            name, ok = QInputDialog.getText(self.win, "New ECU Project", "Project name:", text=base)
            if not ok or not name.strip():
                return None
            name = name.strip()
        if folder is None:
            parent = QFileDialog.getExistingDirectory(self.win, "New ECU Project: location", str(Path.home()))
            if not parent:
                return None
            folder = Path(parent) / name
        folder = Path(folder)
        if (folder / "ecu.json").exists():
            QMessageBox.warning(self.win, "New ECU Project", f"{folder} already holds an ECU project.")
            return None
        try:
            self._create_project(folder, name, source, demo)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self.win, "New ECU Project", str(e))
            return None
        try:
            self.win.open_project(folder, ask=False)
        except TypeError:
            self.win.open_project(folder)
        return self.open_project_workbench(folder)

    @staticmethod
    def _create_project(folder: Path, name: str, source, demo: bool) -> None:
        from ..firmware.ui import adapters as A
        try:
            from ..languages import get_plugin
            plugin = get_plugin(LANG)
        except Exception:  # noqa: BLE001
            plugin = None
        if plugin is not None:
            plugin.create_new_project(folder, name, "ecu_demo" if demo else "ecu_empty")
            if not demo:
                from ..firmware.project.model import EcuProject
                ep = EcuProject.load(folder)
                ep.set_original(source, copy=True)
                ep.work_bytes()
                ep.save()
            return
        if demo:
            from ..firmware.ui import demo as D
            data, maps, profiles = D.build_image()
            A.EcuProject.create(folder, name, data=data, checksums=profiles, maps=maps)
        else:
            A.EcuProject.create(folder, name, source=source)
        from ..model import Project
        Project(folder, name, LANG, [], "ecu.json", []).save()

    # ================================================================== Solution Explorer
    def _menu_hook(self, win, item, m) -> None:
        if win is not self.win or item is None:
            return
        data = item.data(0, ROLE)
        if not data:
            return
        path = None
        kind = str(data[0])
        if kind in ("ecuproj", "project") and self._project_item_is_ecu(item, kind):
            m.addSeparator()
            m.addAction("Open Firmware && ECU Workbench", self.open_project_workbench)
            return
        try:
            if kind in ("module", "file", "other", "folder_file", "webfile", "source", "proxy") or \
                    kind.endswith("_file") or kind.startswith(("romhack_", "ecuproj_")):
                cand = Path(str(data[1]))
                if not cand.is_absolute() and getattr(win, "project", None) is not None:
                    cand = Path(win.project.folder) / cand
                if cand.is_file():
                    path = cand
        except (TypeError, ValueError, IndexError):
            path = None
        if path is None:
            return
        sub = next((a.menu() for a in m.actions() if a.menu() is not None and
                    self.plain(a.text()) == "Open With"), None)
        if sub is None:
            m.addSeparator()
            sub = m.addMenu("Open With")
        sub.addAction("Firmware && ECU Workbench", lambda p=path: self.open_workbench(p))
        sub.addAction("Firmware && ECU Workbench (EEPROM, read-only)",
                      lambda p=path: self.open_workbench(p, eeprom=True, read_only=True))


    def _project_item_is_ecu(self, item, kind: str) -> bool:
        if kind == "ecuproj":
            return True
        try:
            from .solution_ui import PROJECT_ROLE
            st = getattr(self.win, "_pstates", {}).get(item.data(0, PROJECT_ROLE))
            proj = st.get("project") if st else None
            return proj is not None and getattr(proj, "language", "") == LANG
        except Exception:  # noqa: BLE001
            return False


def install(win) -> None:
    win.firmware_ide_feature = FirmwareIde(win)
