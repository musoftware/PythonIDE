"""Firmware analysis in the IDE (radide/firmware/analysis, docs/FIRMWARE.md "Formats and analysis"):

* Tools > Firmware & ECU: Analyze Firmware File... (raw .bin / .ori / .mod / .rom / .dump, Intel HEX, S-record,
  ELF), Firmware Converter... (convert formats, even / odd EPROM split and interleave, byte swap, cut, merge),
  Create Synthetic Test Firmware...
* Firmware / ECU Analysis projects (language "firmware-analysis", firmware.json): Project > Firmware Analysis
  (Set Original..., Analyze, Verify Original, Make Working Copy, Open Notes, Open Labels) and a "Firmware
  Analysis" node in Solution Explorer (original - read-only, working copy, report).
* ``win.firmware_analysis.open_analysis(path, base=None, arch="")`` opens the analysis view for any file (the
  ECU workbench and other features use it). "Show in hex" opens the IDE's hex editor at the address.

File associations stay with the ECU workbench (radide/features/firmware_ide.py) and the ROM workbench.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox, QTreeWidgetItem

ROLE = Qt.ItemDataRole.UserRole
LANG = "firmware-analysis"
OPEN_FILTER = ("Firmware (*.bin *.ori *.mod *.rom *.dump *.dmp *.img *.hex *.ihex *.s19 *.s28 *.s37 *.mot *.srec "
               "*.elf *.axf);;All files (*.*)")


class FirmwareAnalysisFeature:
    def __init__(self, win):
        self.win = win
        self.views: dict[str, object] = {}
        self._hexdocs: dict[str, object] = {}
        self.project_menu = None
        self._wrap()
        QTimer.singleShot(0, self._menus)          # after the other features created the Tools / Project menus
        try:
            win.solution.itemDoubleClicked.connect(self._on_tree_dclick)
        except Exception:  # noqa: BLE001
            pass
        try:
            from . import solution_ui
            if self._menu_hook not in solution_ui.MENU_HOOKS:
                solution_ui.MENU_HOOKS.append(self._menu_hook)
        except Exception:  # noqa: BLE001
            pass

    # ================================================================== glue
    def _wrap(self) -> None:
        win = self.win
        orig_fill = win._fill_solution

        def fill_solution(*a, **k):
            r = orig_fill(*a, **k)
            try:
                self._add_tree_nodes()
            except Exception as e:  # noqa: BLE001 - never break Solution Explorer
                win.log(f"[firmware analysis] {e}")
            return r
        win._fill_solution = fill_solution
        win.firmware_analysis = self

    def _log(self, text: str) -> None:
        try:
            self.win.statusBar().showMessage(text.replace("[firmware] ", ""), 6000)
            self.win.log(text)
        except Exception:  # noqa: BLE001
            pass

    def _find_menu(self, parent, words: tuple[str, ...]):
        acts = parent.actions() if parent is not None else self.win.menuBar().actions()
        for a in acts:
            m = a.menu()
            t = a.text().replace("&", "")
            if m is not None and all(w in t for w in words):
                return m
        return None

    def _menus(self) -> None:
        tools = self._find_menu(None, ("Tools",))
        if tools is not None:
            m = self._find_menu(tools, ("Firmware", "ECU"))
            if m is None:
                m = tools.addMenu("&Firmware && ECU")
            m.addSeparator()
            m.addAction("&Analyze Firmware File...", self.open_dialog)
            m.addAction("Firmware &Converter (HEX / S-record / ELF / split / merge)...", self.converter)
            m.addAction("Create &Synthetic Test Firmware...", self.synth_dialog)
            self.tools_menu = m
        pm = self._find_menu(None, ("Project",))
        if pm is not None:
            sub = pm.addMenu("Firmware &Analysis")
            self.a_set = sub.addAction("Set &Original...", self.set_original_dialog)
            self.a_analyze = sub.addAction("&Analyze", self.analyze_project)
            self.a_verify = sub.addAction("&Verify Original", self.verify_project)
            self.a_work = sub.addAction("Make &Working Copy", self.make_working_copy)
            sub.addSeparator()
            self.a_notes = sub.addAction("Open &Notes", lambda: self._open_project_file("notes.md"))
            self.a_labels = sub.addAction("Open &Labels", lambda: self._open_project_file("labels.json"))
            sub.aboutToShow.connect(self._update_menu)
            self.project_menu = sub

    def _update_menu(self) -> None:
        on = self._fwproject() is not None
        for a in (self.a_set, self.a_analyze, self.a_verify, self.a_work, self.a_notes, self.a_labels):
            a.setEnabled(on)

    # ================================================================== project helpers
    def _fwproject(self, project=None):
        p = project or getattr(self.win, "project", None)
        if p is None or getattr(p, "language", "") != LANG:
            return None
        from ..firmware.analysis.project import FirmwareProject
        try:
            return FirmwareProject.load(p.folder)
        except (OSError, ValueError):
            return None

    def _refresh_tree(self) -> None:
        try:
            self.win._fill_solution()
        except Exception:  # noqa: BLE001
            pass

    def _open_project_file(self, rel: str) -> None:
        fp = self._fwproject()
        if fp is None:
            return
        p = fp.path(rel)
        if p.is_file():
            try:
                self.win.open_any_file(p)
            except Exception:  # noqa: BLE001
                self.win.open_file(str(p))

    # ================================================================== documents
    @staticmethod
    def _alive(w) -> bool:
        try:
            w.isVisible()
            return True
        except RuntimeError:
            return False

    def open_analysis(self, path, base: int | None = None, arch: str = "", labels: dict | None = None,
                      workdir=None):
        """Open (or show) the analysis view of *path*; returns the view."""
        from ..firmware.analysis.view import FirmwareAnalysisView
        p = Path(path).resolve()
        key = str(p).lower()
        w = self.views.get(key)
        if w is not None and self._alive(w) and self.win.tabs.indexOf(w) >= 0:
            self.win._show_tab(w, f"Analysis: {p.name}")
            return w
        if not p.is_file():
            QMessageBox.warning(self.win, "Firmware Analysis", f"File not found: {p}")
            return None
        if p.stat().st_size > 256 << 20:
            QMessageBox.warning(self.win, "Firmware Analysis", f"{p.name} is larger than 256 MB.")
            return None
        try:
            w = FirmwareAnalysisView(p, base=base, arch=arch, labels=labels, workdir=workdir)
        except (OSError, ValueError, KeyError) as e:
            QMessageBox.warning(self.win, "Firmware Analysis", f"Cannot open {p.name}:\n{e}")
            return None
        w.setToolTip(str(p))
        w.message.connect(self._log)
        w.hexRequested.connect(lambda addr, v=w: self.show_hex(v, addr))
        self.views[key] = w
        self.win._show_tab(w, f"Analysis: {p.name}")
        return w

    def show_hex(self, view, address: int):
        """The IDE's hex editor at *address* of the analysed image (raw files: the file itself, read-only;
        HEX / S-record / ELF: a read-only flat image)."""
        off = address - view.base_address()
        fmt = view.mm0.meta.get("format", "raw")
        doc = None
        if fmt == "raw" and view.path is not None and callable(getattr(self.win, "open_hex", None)):
            doc = self.win.open_hex(view.path, read_only=True)
        else:
            try:
                from ..retro.rom.hexdoc import HexDocument
            except ImportError:
                return None
            key = str(view.path).lower() if view.path else str(id(view))
            doc = self._hexdocs.get(key)
            if doc is None or not self._alive(doc) or self.win.tabs.indexOf(doc) < 0:
                doc = HexDocument(data=view.mm.to_flat(0xFF), read_only=True)
                self._hexdocs[key] = doc
            self.win._show_tab(doc, f"{view.path.name if view.path else 'image'} [flat @0x{view.base_address():X}]")
        if doc is not None:
            try:
                doc.goto(max(0, off))
            except Exception:  # noqa: BLE001
                pass
        return doc

    # ================================================================== Tools menu
    def open_dialog(self) -> None:
        start = str(self.win.project.folder) if getattr(self.win, "project", None) is not None else ""
        fn, _ = QFileDialog.getOpenFileName(self.win, "Analyze Firmware File", start, OPEN_FILTER)
        if fn:
            self.open_analysis(fn)

    def converter(self, path: str = ""):
        from ..firmware.analysis.convert_dialog import FirmwareConverterDialog
        dlg = FirmwareConverterDialog(self.win, path)
        dlg.setModal(False)
        dlg.show()
        self._converter = dlg
        return dlg

    def synth_dialog(self) -> None:
        from ..firmware.analysis.synth import ARCHES, make_image
        arch, ok = QInputDialog.getItem(self.win, "Synthetic Test Firmware", "CPU:", ARCHES, 0, False)
        if not ok:
            return
        fn, _ = QFileDialog.getSaveFileName(self.win, "Save Synthetic Firmware", f"synthetic_{arch}.bin",
                                            "Raw binary (*.bin)")
        if not fn:
            return
        im = make_image(arch)
        Path(fn).write_bytes(im.bytes())
        self._log(f"[firmware] synthetic {arch} image written to {fn} (base 0x{im.base:X}, generated by RAD IDE - "
                  f"no manufacturer data)")
        self.open_analysis(fn)

    # ================================================================== project actions
    def set_original_dialog(self) -> None:
        fp = self._fwproject()
        if fp is None:
            QMessageBox.information(self.win, "Firmware Analysis", "Open a Firmware / ECU Analysis project first.")
            return
        fn, _ = QFileDialog.getOpenFileName(self.win, "Set Original", "", OPEN_FILTER)
        if fn:
            self.set_original(fn)

    def set_original(self, path):
        fp = self._fwproject()
        if fp is None:
            return None
        dst = fp.set_original(path)
        self._log(f"[firmware] original: {dst} (read-only, SHA-256 {fp.sha256[:16]}...), CPU guess "
                  f"{fp.arch or '-'}, base 0x{fp.base:X}")
        self._refresh_tree()
        return dst

    def analyze_project(self):
        fp = self._fwproject()
        if fp is None:
            return None
        ok, msg = fp.verify()
        if not ok:
            QMessageBox.warning(self.win, "Firmware Analysis", msg)
            return None
        labels = {x.address: x.name for x in fp.labels()}
        base = fp.base if fp.format in ("", "raw") else None
        return self.open_analysis(fp.original_path, base=base, arch=fp.extra.get("arch_fixed", ""), labels=labels,
                                  workdir=fp.path("build"))

    def verify_project(self) -> bool:
        fp = self._fwproject()
        if fp is None:
            return False
        ok, msg = fp.verify()
        (QMessageBox.information if ok else QMessageBox.warning)(self.win, "Firmware Analysis", msg)
        self._log(f"[firmware] {msg}")
        return ok

    def make_working_copy(self):
        fp = self._fwproject()
        if fp is None or fp.original_path is None:
            return None
        dst = fp.make_working_copy()
        self._log(f"[firmware] working copy: {dst}")
        self._refresh_tree()
        if callable(getattr(self.win, "open_hex", None)):
            self.win.open_hex(dst, read_only=False)
        return dst

    # ================================================================== Solution Explorer
    def _add_tree_nodes(self) -> None:
        win = self.win
        try:
            from .solution_ui import PROJECT_ROLE
        except ImportError:
            return
        tree = win.solution
        style = win.style()
        stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        while stack:
            it = stack.pop()
            stack.extend(it.child(i) for i in range(it.childCount()))
            data = it.data(0, ROLE)
            if not data or data[0] != "project":
                continue
            key = it.data(0, PROJECT_ROLE)
            st = getattr(win, "_pstates", {}).get(key)
            project = st["project"] if st else None
            fp = self._fwproject(project) if project is not None else None
            if fp is None:
                continue
            if any((it.child(i).data(0, ROLE) or ("",))[0] == "fwa" for i in range(it.childCount())):
                continue

            def node(text, kind, path, tip, icon):
                n = QTreeWidgetItem([text])
                n.setData(0, ROLE, (kind, str(path)))
                n.setData(0, PROJECT_ROLE, key)
                n.setToolTip(0, tip)
                n.setIcon(0, style.standardIcon(icon))
                return n
            root = node("Firmware Analysis", "fwa", project.folder, "Double-click: open the analysis view",
                        style.StandardPixmap.SP_FileDialogContentsView)
            if fp.original_path is not None:
                label = f"Original: {fp.original_path.name}  [{fp.arch or '?'} @ 0x{fp.base:X}]"
                root.addChild(node(label, "fwa_original", fp.original_path,
                                   f"Read-only. SHA-256 {fp.sha256}", style.StandardPixmap.SP_FileIcon))
            else:
                root.addChild(node("Original: (not set - Project > Firmware Analysis > Set Original...)",
                                   "fwa_set", project.folder, "Choose the firmware file",
                                   style.StandardPixmap.SP_FileDialogNewFolder))
            if fp.working_path is not None and fp.working_path.is_file():
                root.addChild(node(f"Working copy: {fp.working_path.name}", "fwa_work", fp.working_path,
                                   "Flat image for your own experiments (hex editor)", style.StandardPixmap.SP_FileIcon))
            rep = fp.path("build") / "analysis.txt"
            if rep.is_file():
                root.addChild(node("Report: build/analysis.txt", "fwa_report", rep, "Build output",
                                   style.StandardPixmap.SP_FileDialogDetailedView))
            pos = 1 if it.childCount() and (it.child(0).data(0, ROLE) or ("",))[0] == "references" else 0
            it.insertChild(pos, root)
            root.setExpanded(True)

    def _activate(self, item) -> None:
        try:
            from .solution_ui import PROJECT_ROLE
            key = item.data(0, PROJECT_ROLE)
            st = getattr(self.win, "_pstates", {}).get(key)
            if st and st.get("project") is not None and st["project"] is not self.win.project:
                self.win.activate_project(st["project"])
        except Exception:  # noqa: BLE001
            pass

    def _on_tree_dclick(self, item, _col) -> None:
        data = item.data(0, ROLE)
        if not data or not str(data[0]).startswith("fwa"):
            return
        self._activate(item)
        kind, path = data[0], data[1]
        if kind in ("fwa", "fwa_original"):
            self.analyze_project()
        elif kind == "fwa_set":
            self.set_original_dialog()
        elif kind == "fwa_work" and callable(getattr(self.win, "open_hex", None)):
            self.win.open_hex(path, read_only=False)
        elif kind == "fwa_report":
            try:
                self.win.open_any_file(Path(path))
            except Exception:  # noqa: BLE001
                pass

    def _menu_hook(self, win, item, m) -> None:
        if win is not self.win or item is None:
            return
        data = item.data(0, ROLE)
        if not data:
            return
        kind = str(data[0])
        if kind.startswith("fwa"):
            m.addSeparator()
            m.addAction("Analyze", self.analyze_project)
            m.addAction("Set Original...", self.set_original_dialog)
            m.addAction("Verify Original", self.verify_project)
            m.addAction("Make Working Copy", self.make_working_copy)
            return
        # any file node: Analyze Firmware
        path = data[1] if len(data) > 1 else ""
        try:
            p = Path(str(path))
        except TypeError:
            return
        from ..firmware.formats import FIRMWARE_EXTS
        if p.suffix.lower() in FIRMWARE_EXTS - {".s", ".out"} and p.is_file():
            m.addAction("Analyze Firmware", lambda: self.open_analysis(p))


def install(win) -> None:
    win.firmware_analysis_feature = FirmwareAnalysisFeature(win)
