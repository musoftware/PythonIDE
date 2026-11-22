"""Calibration maps in the IDE (radide/firmware/maps, docs/FIRMWARE.md "Calibration maps"):

* Tools > Firmware & ECU > Calibration Maps: open a binary in the map editor (map pack, potential maps, differences,
  map table with 2D / 3D views, whole-file 2D view, hex), find maps, compare two binaries map by map, import an A2L,
  open a rusEFI / Speeduino tune (.msq + .ini) as a calibration image.
* The hex editor's context menu gets "Open in Map Editor".
* ``win.firmware_maps`` is the API for the other firmware features: ``open_maps(path, original=None, pack=None)``,
  ``compare_maps(a, b)``, ``open_tune(ini, msq)``.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QApplication, QFileDialog, QLineEdit, QMessageBox, QPlainTextEdit


def firmware_menu(win):
    """Tools > Firmware & ECU (shared with the other firmware features; created when missing)."""
    mb = win.menuBar()
    tools = next((a.menu() for a in mb.actions() if a.menu() is not None and a.text().replace("&", "") == "Tools"),
                 None)
    if tools is None:
        tools = mb.addMenu("&Tools")

    def norm(t: str) -> str:
        return t.replace("&", "").replace(" ", "").lower()
    for a in tools.actions():
        if a.menu() is not None and norm(a.text()) in ("firmwareecu", "firmware/ecu", "firmware"):
            return a.menu()
    return tools.addMenu("Firmware && &ECU")


class FirmwareMapsFeature:
    def __init__(self, win):
        self.win = win
        self.docs: list = []
        self._menus()
        self._glue()
        try:
            from ..retro.rom.hexdoc import HexDocument
            HexDocument.menu_hooks[:] = [h for h in HexDocument.menu_hooks if not getattr(h, "_rad_maps", False)]
            hook = self._hex_hook
            HexDocument.menu_hooks.append(hook)
        except Exception:  # noqa: BLE001 - the hex editor is optional
            pass
        win.firmware_maps = self

    # ------------------------------------------------------------------ window glue
    # DocumentProvider (radide/extension_points.py): Save All / closing question; maps open by own commands
    def can_open(self, path: Path) -> bool:
        return False

    def open_document(self, path: Path):
        return None

    def save_documents(self) -> None:
        for d in self.alive():
            if d.is_modified():
                d.save()

    def has_modified_documents(self) -> bool:
        return any(d.is_modified() for d in self.alive())

    def _glue(self) -> None:
        win = self.win
        win.extension_points.add_document_provider(self)
        orig_update = getattr(win, "_update_actions", None)
        if callable(orig_update):
            def update_actions(*a, **k):
                r = orig_update(*a, **k)
                self._update_actions()
                return r
            win._update_actions = update_actions
        try:
            win.tabs.currentChanged.connect(lambda _i: self._update_actions())
        except Exception:  # noqa: BLE001
            pass
        for attr, op in (("a_undo", "undo"), ("a_redo", "redo"), ("a_copy", "copy"), ("a_paste", "paste"),
                         ("a_select_all", "select_all")):
            act = getattr(win, attr, None)
            if act is not None:
                act.triggered.connect(lambda _c=False, op=op: self._edit(op))
                # the window re-evaluates its Edit actions from many places: keep ours while a map tab is current
                act.changed.connect(self._schedule_update)
        if getattr(win, "a_save", None) is not None:
            win.a_save.triggered.connect(lambda _c=False: self._save_current())

    def _schedule_update(self) -> None:
        if getattr(self, "_updating", False) or self.current() is None:
            return
        t = getattr(self, "_upd_timer", None)
        if t is None:
            from PyQt6.QtCore import QTimer
            t = self._upd_timer = QTimer(self.win, singleShot=True, interval=0)
            t.timeout.connect(self._update_actions)
        t.start()

    def _update_actions(self) -> None:
        """Edit menu state while a map document is the current tab (undo / redo follow its working copy)."""
        if getattr(self, "_updating", False):
            return
        d = self.current()
        if d is None:
            return
        buf = getattr(d, "buf", None)
        self._updating = True
        try:
            for attr, on in (("a_undo", bool(buf is not None and buf.can_undo())),
                             ("a_redo", bool(buf is not None and buf.can_redo())),
                             ("a_copy", True), ("a_paste", not getattr(d, "read_only", False)),
                             ("a_select_all", True)):
                a = getattr(self.win, attr, None)
                if a is not None and a.isEnabled() != on:
                    a.setEnabled(on)
        finally:
            self._updating = False

    def alive(self) -> list:
        out = []
        for d in list(self.docs):
            try:
                d.isVisible()
                if self.win.tabs.indexOf(d) >= 0:
                    out.append(d)
                    continue
            except RuntimeError:
                pass
            self.docs.remove(d)
        return out

    def current(self):
        try:
            w = self.win.tabs.currentWidget()
        except RuntimeError:
            return None
        return w if w in self.docs else None

    def _edit(self, op: str) -> None:
        d = self.current()
        if d is None or isinstance(QApplication.focusWidget(), (QLineEdit, QPlainTextEdit)):
            return
        d.edit_op(op)

    def _save_current(self) -> None:
        d = self.current()
        if d is not None and d.is_modified():
            d.save()

    def _title(self, d) -> None:
        i = self.win.tabs.indexOf(d)
        if i >= 0:
            base = d.property("radTitle") or "Maps"
            self.win.tabs.setTabText(i, base + ("*" if d.is_modified() else ""))

    def _log(self, text: str) -> None:
        try:
            self.win.statusBar().showMessage(text, 6000)
            self.win.log(text)
        except Exception:  # noqa: BLE001
            pass

    def _show(self, d, title: str):
        d.setProperty("radTitle", title)
        self.docs.append(d)
        d.modifiedChanged.connect(lambda _m, d=d: (self._title(d), self._schedule_update()))
        d.saved.connect(lambda d=d: self._title(d))
        d.message.connect(self._log)
        self.win._show_tab(d, title)
        self._title(d)
        return d

    # ------------------------------------------------------------------ menus
    def _menus(self) -> None:
        fm = firmware_menu(self.win)
        m = fm.addMenu("Calibration &Maps")
        self.menu = m
        m.addAction("&Open Binary in Map Editor...", self.open_dialog)
        m.addAction("&Find Maps in a Binary...", self.find_dialog)
        m.addAction("&Compare Two Binaries (Maps)...", self.compare_dialog)
        m.addSeparator()
        m.addAction("Open Binary with an &A2L...", self.open_with_a2l_dialog)
        m.addAction("Open rusEFI / Speeduino &Tune (msq + ini)...", self.open_tune_dialog)

    def _start(self) -> str:
        p = getattr(self.win, "project", None)
        return str(p.folder) if p is not None else ""

    def _hex_hook(self, doc, menu, offset, _sel) -> None:
        if getattr(doc, "path", None) is None:
            return
        menu.addSeparator()
        menu.addAction("Open in Map Editor", lambda: self.open_maps(doc.path, goto=offset))
    _hex_hook._rad_maps = True

    # ------------------------------------------------------------------ documents
    def open_maps(self, path, original=None, pack=None, goto: int | None = None):
        from ..firmware.maps.document import MapsDocument
        p = Path(path).resolve()
        for d in self.alive():
            if type(d).__name__ == "MapsDocument" and d.path is not None and d.path.resolve() == p:
                self.win._show_tab(d, d.property("radTitle"))
                return d
        if not p.is_file():
            QMessageBox.warning(self.win, "Map Editor", f"File not found: {p}")
            return None
        if p.stat().st_size > 64 << 20:
            QMessageBox.warning(self.win, "Map Editor", f"{p.name} is larger than 64 MB.")
            return None
        d = MapsDocument(p, original=original, pack=pack)
        d.compareRequested.connect(self.compare_maps)
        d.setToolTip(str(p))
        self._show(d, f"{p.name} [Maps]")
        if goto is not None:
            d.goto_hex(goto)
        return d

    def compare_maps(self, a, b, pack=None):
        from ..firmware.maps.document import CompareDocument
        d = CompareDocument(a, b, pack)
        d.hexCompareRequested.connect(self._hex_compare)
        return self._show(d, f"{Path(a).name} <> {Path(b).name}")

    def _hex_compare(self, a: str, b: str) -> None:
        rw = getattr(self.win, "rom_workbench", None)
        if rw is not None:
            rw.compare(a, b)

    def open_tune(self, ini, msq, out=None):
        """rusEFI / Speeduino: write the tune's pages image (``<msq>.bin``) and open it with the ini's maps."""
        from ..firmware.maps.tsini import load_ini, msq_to_image, msq_values
        res = load_ini(ini)
        img, written = msq_to_image(res, msq_values(msq))
        out = Path(out) if out else Path(msq).with_suffix(".bin")
        out.write_bytes(img)
        res.pack.save(out.with_name(out.name + ".maps.json"))
        self._log(f"Tune image written: {out.name} ({len(written)} values from {Path(msq).name})")
        return self.open_maps(out)

    # ------------------------------------------------------------------ dialogs
    def open_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self.win, "Open Binary in Map Editor", self._start(),
                                           "Firmware files (*.bin *.ori *.mod *.rom *.dump *.img);;All files (*)")
        if f:
            self.open_maps(f)

    def find_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self.win, "Find Maps in a Binary", self._start(), "All files (*)")
        if f:
            d = self.open_maps(f)
            if d is not None:
                d.find_maps_async()

    def compare_dialog(self) -> None:
        a, _ = QFileDialog.getOpenFileName(self.win, "Compare: file A (editable)", self._start(), "All files (*)")
        if not a:
            return
        b, _ = QFileDialog.getOpenFileName(self.win, "Compare: file B", str(Path(a).parent), "All files (*)")
        if b:
            self.compare_maps(a, b)

    def open_with_a2l_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self.win, "Open Binary", self._start(), "All files (*)")
        if not f:
            return
        d = self.open_maps(f)
        if d is not None:
            d.import_a2l_dialog()

    def open_tune_dialog(self) -> None:
        msq, _ = QFileDialog.getOpenFileName(self.win, "Open Tune (msq)", self._start(), "Tunes (*.msq);;All files (*)")
        if not msq:
            return
        ini, _ = QFileDialog.getOpenFileName(self.win, "Its TunerStudio ini", str(Path(msq).parent),
                                             "TunerStudio ini (*.ini);;All files (*)")
        if ini:
            try:
                self.open_tune(ini, msq)
            except Exception as e:  # noqa: BLE001 - shown to the user
                QMessageBox.warning(self.win, "Open Tune", f"Cannot read the tune:\n{e}")


def install(win) -> None:
    FirmwareMapsFeature(win)
