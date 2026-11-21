"""Map editing documents (Qt tabs of the IDE):

* :class:`MapsDocument` - one binary: map pack tree, "Potential maps" (map finder), "Differences" (ori vs mod),
  the map editor, the whole-file 2D view and the hex view - all on one undoable working copy.
* :class:`CompareDocument` - two binaries side by side: map-level differences, both versions of a map, and
  "Copy map from B to A".

Both keep the protocol of the IDE's document tabs: ``path``, ``is_modified()``, ``save()``, ``edit_op(op)``,
``modifiedChanged`` / ``saved`` / ``message`` signals.
"""
from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QMenu, QMessageBox, QPushButton, QSplitter, QTabWidget, QToolBar, QToolButton,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import ops
from .editor import MapEditor
from .model import MapDef, MapPack, fmt_hex, pack_from_csv, pack_path_for, pack_to_csv
from .views import FileGraph
from .views import tr_ui as _tr

ROLE = Qt.ItemDataRole.UserRole


def _notice_banner(parent) -> QFrame | None:
    """The one-time vehicle-software notice as a slim banner (accepting it hides it for good)."""
    try:
        from ..project import notice
    except Exception:  # noqa: BLE001 - the ECU project slice may be missing
        notice = None
    if notice is not None and notice.accepted():
        return None
    box = QFrame(parent)
    box.setObjectName("firmwareNoticeBanner")
    box.setFrameShape(QFrame.Shape.StyledPanel)
    box.setStyleSheet("#firmwareNoticeBanner { background: #fff4ce; color: #3b2f00; border: 1px solid #e0c060; }")
    lay = QHBoxLayout(box)
    lay.setContentsMargins(8, 4, 8, 4)
    lbl = QLabel("Edits to vehicle software can affect safety, warranty and emissions legality. Keep the original "
                 "file and follow your local laws.")
    lbl.setWordWrap(True)
    lay.addWidget(lbl, 1)
    btn = QPushButton("I understand")

    def ok():
        if notice is not None:
            notice.set_accepted(True)
        box.hide()
    btn.clicked.connect(ok)
    lay.addWidget(btn)
    if notice is not None and hasattr(notice, "on_accepted"):
        notice.on_accepted(box)             # accepted elsewhere (ECU project dialog, workbench) -> hide
    return box


class MapsDocument(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()
    message = pyqtSignal(str)
    compareRequested = pyqtSignal(str, str)       # this file, other file
    findFinished = pyqtSignal()

    def __init__(self, path=None, data: bytes | None = None, original=None, pack=None, parent=None,
                 read_only: bool = False):
        super().__init__(parent)
        from ...retro.rom.buffer import HexBuffer
        self.path = Path(path) if path else None
        raw = data if data is not None else (self.path.read_bytes() if self.path else b"")
        self.buf = HexBuffer(raw, self.path)
        self.read_only = read_only
        if isinstance(original, (str, Path)):
            original = Path(original).read_bytes()
        self.original: bytes = bytes(original) if original is not None else bytes(raw)
        self.original_label = "file as opened" if original is None else "original file"
        if isinstance(pack, (str, Path)):
            pack = MapPack.load(pack)
        if pack is None and self.path is not None and pack_path_for(self.path).is_file():
            try:
                pack = MapPack.load(pack_path_for(self.path))
            except (OSError, ValueError):
                pack = None
        self.pack: MapPack = pack or MapPack(name=self.path.stem if self.path else "Map pack")
        if self.pack.path is None and self.path is not None:
            self.pack.path = pack_path_for(self.path)
        self.pack_dirty = False
        self.candidates: list = []
        self._last_modified = False
        self._find_thread = None
        self._find_result = None
        self._build()
        self.buf.listeners.append(self._on_buffer)
        self._refresh_timer = QTimer(self, singleShot=True, interval=250)
        self._refresh_timer.timeout.connect(self._deferred_refresh)
        self.fill_pack_tree()
        self.refresh_differences()
        self.graph.set_data(self.buf.data)
        self._update_bands()

    # ------------------------------------------------------------------ protocol
    @property
    def retro_path(self):
        return self.path

    def data(self) -> bytes:
        return bytes(self.buf.data)

    def is_modified(self) -> bool:
        return self.buf.modified or self.pack_dirty

    def save(self) -> bool:
        if self.read_only:
            return False
        if self.path is None:
            return self.save_as()
        try:
            if self.buf.modified:
                self._backup_original()
                self.buf.save(self.path)
            if self.pack_dirty or (self.pack.maps and self.pack.path is not None):
                self.save_pack()
        except OSError as e:
            QMessageBox.warning(self, "Map Editor", f"Cannot save {self.path.name}:\n{e}")
            return False
        self._emit_modified()
        self.saved.emit()
        self.message.emit(f"Saved {self.path.name}")
        return True

    def save_as(self, path=None) -> bool:
        if path is None:
            f, _ = QFileDialog.getSaveFileName(self, "Save Binary As", str(self.path or ""), "All files (*)")
            if not f:
                return False
            path = f
        self.path = Path(path)
        self.buf.path = self.path
        self.pack.path = pack_path_for(self.path)
        self.pack_dirty = True
        return self.save()

    def _backup_original(self) -> None:
        """First save of a file opened without an original: keep the bytes as opened next to it."""
        if self.path is None or self.original_label != "file as opened":
            return
        bak = self.path.with_name(self.path.stem + ".original" + self.path.suffix)
        if not bak.exists():
            bak.write_bytes(self.original)
            self.message.emit(f"The original is kept as {bak.name}")

    def save_pack(self, path=None) -> Path | None:
        p = Path(path) if path else self.pack.path
        if p is None:
            return None
        self.pack.save(p)
        self.pack_dirty = False
        self._emit_modified()
        return p

    def edit_op(self, op: str) -> None:
        if op == "undo":
            self.undo()
        elif op == "redo":
            self.redo()
        elif op == "copy":
            self.editor.copy()
        elif op == "paste":
            self.editor.paste()
        elif op == "select_all":
            self.editor.select_all()

    def undo(self) -> None:
        if self.buf.undo() is not None:
            self.message.emit("Undo")

    def redo(self) -> None:
        if self.buf.redo() is not None:
            self.message.emit("Redo")

    def _emit_modified(self) -> None:
        m = self.is_modified()
        if m != self._last_modified:
            self._last_modified = m
        self.modifiedChanged.emit(m)

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.banner = _notice_banner(self)
        if self.banner is not None:
            lay.addWidget(self.banner)
        tb = QToolBar("Maps")
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.toolbar = tb
        self.acts: dict[str, QAction] = {}

        def act(key, text, slot, tip=""):
            a = QAction(text, self)
            a.triggered.connect(lambda _c=False: slot())
            if tip:
                a.setToolTip(tip)
            self.acts[key] = a
            return a
        tb.addAction(act("save", "Save", self.save, "Save the working copy and the map pack"))
        tb.addAction(act("undo", "Undo", self.undo))
        tb.addAction(act("redo", "Redo", self.redo))
        tb.addSeparator()
        tb.addAction(act("find", "Find Maps", self.find_maps_async, "Search the file for calibration tables"))
        tb.addAction(act("new", "New Map...", self.new_map_at_cursor, "Define a map at the hex cursor"))
        imp = QToolButton()
        imp.setText("Import")
        imp.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        im = QMenu(imp)
        im.addAction(act("imp_a2l", "ASAP2 / A2L...", lambda: self.import_a2l_dialog()))
        im.addAction(act("imp_ini", "TunerStudio ini (rusEFI / Speeduino)...", lambda: self.import_ini_dialog()))
        im.addAction(act("imp_csv", "CSV...", lambda: self.import_csv_dialog()))
        im.addAction(act("imp_pack", "Map Pack (JSON)...", lambda: self.import_pack_dialog()))
        imp.setMenu(im)
        tb.addWidget(imp)
        exp = QToolButton()
        exp.setText("Export")
        exp.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        em = QMenu(exp)
        em.addAction(act("exp_a2l", "ASAP2 / A2L...", lambda: self.export_a2l_dialog()))
        em.addAction(act("exp_csv", "CSV...", lambda: self.export_csv_dialog()))
        em.addAction(act("exp_pack", "Map Pack (JSON)...", lambda: self.export_pack_dialog()))
        exp.setMenu(em)
        tb.addWidget(exp)
        tb.addSeparator()
        tb.addAction(act("ori", "Set Original...", lambda: self.set_original_dialog(),
                         "The file the differences are measured against"))
        tb.addAction(act("compare", "Compare With...", lambda: self.compare_dialog(),
                         "Compare this file with another binary map by map"))
        lay.addWidget(tb)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.left = QTabWidget()
        # map pack tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Map", "Address", "Size", "Type"])
        self.tree.setProperty("i18n_skip_items", True)
        self.tree.itemDoubleClicked.connect(self._on_tree_item)
        self.tree.itemActivated.connect(self._on_tree_item)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        self.left.addTab(self.tree, "Map Pack")
        # potential maps
        pot = QWidget()
        pl = QVBoxLayout(pot)
        pl.setContentsMargins(0, 2, 0, 0)
        row = QHBoxLayout()
        self.b_find = QPushButton("Find Maps")
        self.b_find.clicked.connect(self.find_maps_async)
        self.b_add = QPushButton("Add to Map Pack")
        self.b_add.clicked.connect(self.add_selected_candidates)
        row.addWidget(self.b_find)
        row.addWidget(self.b_add)
        row.addStretch(1)
        pl.addLayout(row)
        self.find_status = QLabel("Press Find Maps to search the file for tables.")
        self.find_status.setWordWrap(True)
        pl.addWidget(self.find_status)
        self.pot = QTreeWidget()
        self.pot.setHeaderLabels(["Score", "Address", "Size", "Type", "Layout"])
        self.pot.setProperty("i18n_skip_items", True)
        self.pot.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.pot.setRootIsDecorated(False)
        self.pot.itemDoubleClicked.connect(self._on_candidate)
        self.pot.itemActivated.connect(self._on_candidate)
        pl.addWidget(self.pot, 1)
        self.left.addTab(pot, "Potential Maps")
        # differences
        dif = QWidget()
        dl = QVBoxLayout(dif)
        dl.setContentsMargins(0, 2, 0, 0)
        self.diff_label = QLabel("")
        self.diff_label.setWordWrap(True)
        dl.addWidget(self.diff_label)
        self.diff = QTreeWidget()
        self.diff.setHeaderLabels(["Map / range", "Cells", "Change"])
        self.diff.setProperty("i18n_skip_items", True)
        self.diff.setRootIsDecorated(False)
        self.diff.itemDoubleClicked.connect(self._on_diff_item)
        self.diff.itemActivated.connect(self._on_diff_item)
        dl.addWidget(self.diff, 1)
        self.left.addTab(dif, "Differences")
        for t in (self.tree, self.pot, self.diff):
            t.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        split.addWidget(self.left)

        self.center = QTabWidget()
        self.editor = MapEditor(self.buf, self.original, read_only=self.read_only)
        self.editor.message.connect(self.message)
        self.editor.propertiesRequested.connect(lambda: self.edit_properties())
        self.center.addTab(self.editor, "Map")
        g = QWidget()
        gl = QVBoxLayout(g)
        gl.setContentsMargins(0, 2, 0, 0)
        grow = QHBoxLayout()
        grow.addWidget(QLabel("Values:"))
        self.graph_type = QComboBox()
        for label, dt, en in FileGraph.TYPES:
            self.graph_type.addItem(_tr(label), (dt, en))
        self.graph_type.currentIndexChanged.connect(lambda _i: self.graph.set_type(*self.graph_type.currentData()))
        grow.addWidget(self.graph_type)
        grow.addWidget(QLabel("Zoom:"))
        self.graph_zoom = QComboBox()
        for n in (1, 2, 4, 8, 16, 64, 256, 1024, 4096):
            self.graph_zoom.addItem(_tr(f"{n} byte/px"), n)
        self.graph_zoom.setCurrentIndex(2)
        self.graph_zoom.currentIndexChanged.connect(lambda _i: self.graph.set_zoom(self.graph_zoom.currentData()))
        grow.addWidget(self.graph_zoom)
        grow.addStretch(1)
        gl.addLayout(grow)
        self.graph = FileGraph()
        self.graph.offsetClicked.connect(self._on_graph_click)
        gl.addWidget(self.graph, 1)
        self.center.addTab(g, "2D View")
        from ...retro.rom.hexview import HexView
        self.hex = HexView(self.buf)
        self.hex.read_only = self.read_only
        self.center.addTab(self.hex, "Hex")
        split.addWidget(self.center)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 3)
        split.setSizes([330, 900])
        lay.addWidget(split, 1)

    # ------------------------------------------------------------------ buffer changes
    def _on_buffer(self, _offset, _old_len, _new_len) -> None:
        # the buffer notifies before it records the undo step: report the modified state once it has
        QTimer.singleShot(0, self._emit_modified_safe)
        self._refresh_timer.start()
        try:
            self.hex.viewport().update()
        except RuntimeError:
            pass

    def _emit_modified_safe(self) -> None:
        try:
            self._emit_modified()
        except RuntimeError:
            pass

    def _deferred_refresh(self) -> None:
        try:
            self.editor.refresh()
            self.refresh_differences()
            self.graph.set_data(self.buf.data)
            self._mark_tree()
        except RuntimeError:
            pass

    def flush(self) -> None:
        """Run the pending refresh now (tests / after scripted edits)."""
        if self._refresh_timer.isActive():
            self._refresh_timer.stop()
        self._deferred_refresh()

    # ------------------------------------------------------------------ pack tree
    def fill_pack_tree(self) -> None:
        self.tree.clear()
        folders: dict[str, QTreeWidgetItem] = {}
        for m in sorted(self.pack.maps, key=lambda x: (x.folder.lower(), x.address)):
            parent = self.tree.invisibleRootItem()
            if m.folder:
                if m.folder not in folders:
                    fi = QTreeWidgetItem([m.folder])
                    fi.setData(0, ROLE, ("folder", m.folder))
                    self.tree.addTopLevelItem(fi)
                    fi.setExpanded(True)
                    folders[m.folder] = fi
                parent = folders[m.folder]
            dims = {"value": "1", "curve": f"{m.cols}", "map": f"{m.cols}x{m.rows}"}[m.kind]
            it = QTreeWidgetItem([m.name, fmt_hex(m.address), dims,
                                  m.dtype + ("" if m.cell_size == 1 else " " + m.endian.upper())])
            it.setData(0, ROLE, ("map", m.name))
            it.setToolTip(0, m.description or m.name)
            parent.addChild(it)
        self._mark_tree()
        self.left.setTabText(0, f"Map Pack ({len(self.pack)})")
        self._update_bands()

    def _mark_tree(self) -> None:
        changed = {d["map"].name for d in ops.changed_maps(self.pack, self.original, self.buf.data)} \
            if len(self.original) else set()
        bold = QFont()
        bold.setBold(True)
        stack = [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        while stack:
            it = stack.pop()
            stack.extend(it.child(i) for i in range(it.childCount()))
            d = it.data(0, ROLE)
            if d and d[0] == "map":
                on = d[1] in changed
                it.setFont(0, bold if on else QFont())
                it.setText(0, d[1] + ("  *" if on else ""))

    def tree_items(self) -> list[QTreeWidgetItem]:
        out, stack = [], [self.tree.topLevelItem(i) for i in range(self.tree.topLevelItemCount())]
        while stack:
            it = stack.pop(0)
            out.append(it)
            stack.extend(it.child(i) for i in range(it.childCount()))
        return out

    def _on_tree_item(self, it, _col=0) -> None:
        d = it.data(0, ROLE)
        if d and d[0] == "map":
            self.open_map(d[1])

    def _tree_menu(self, pos) -> None:
        it = self.tree.itemAt(pos)
        d = it.data(0, ROLE) if it is not None else None
        m = QMenu(self)
        if d and d[0] == "map":
            m.addAction("Open", lambda: self.open_map(d[1]))
            m.addAction("Properties...", lambda: self.edit_properties(self.pack.get(d[1])))
            m.addAction("Show in Hex", lambda: self.goto_hex(self.pack.get(d[1]).address))
            m.addAction("Show in 2D View", lambda: self.goto_graph(self.pack.get(d[1]).address))
            m.addSeparator()
            m.addAction("Remove from Map Pack", lambda: self.remove_map(d[1]))
        m.addAction("New Map...", self.new_map_at_cursor)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def open_map(self, m) -> MapDef | None:
        if isinstance(m, str):
            m = self.pack.get(m)
        if m is None:
            return None
        self.editor.set_map(m)
        self.center.setCurrentWidget(self.editor)
        self.graph.cursor = m.address
        return m

    def add_map(self, m: MapDef, open_it: bool = True) -> MapDef:
        m = self.pack.add(m, replace=False)
        self.pack_dirty = True
        self.fill_pack_tree()
        self._emit_modified()
        if open_it:
            self.open_map(m)
        return m

    def remove_map(self, name: str) -> bool:
        ok = self.pack.remove(name)
        if ok:
            self.pack_dirty = True
            if self.editor.m is not None and self.editor.m.name == name:
                self.editor.set_map(None)
            self.fill_pack_tree()
            self._emit_modified()
        return ok

    def edit_properties(self, m: MapDef | None = None) -> bool:
        from .dialogs import MapPropertiesDialog
        m = m or self.editor.m
        if m is None:
            return False
        dlg = MapPropertiesDialog(m, self, self.pack.folders())
        if dlg.exec() != MapPropertiesDialog.DialogCode.Accepted:
            return False
        return self.replace_map(m, dlg.result_map())

    def replace_map(self, old: MapDef, new: MapDef) -> bool:
        if old in self.pack.maps:
            self.pack.maps[self.pack.maps.index(old)] = new
        else:
            self.pack.add(new, replace=False)
        self.pack_dirty = True
        self.fill_pack_tree()
        self.open_map(new)
        self._emit_modified()
        return True

    def new_map_at_cursor(self, m: MapDef | None = None) -> MapDef | None:
        from .dialogs import MapPropertiesDialog
        start, length = self.hex.selection()
        if length <= 0:
            start = self.hex.cursor if hasattr(self.hex, "cursor") else 0
        base = m or MapDef(name=f"Map_{start:06X}", address=start, cols=max(1, min(64, length or 8)), rows=1,
                           source="manual")
        if m is None:
            dlg = MapPropertiesDialog(base, self, self.pack.folders())
            if dlg.exec() != MapPropertiesDialog.DialogCode.Accepted:
                return None
            base = dlg.result_map()
        return self.add_map(base)

    # ------------------------------------------------------------------ map finder
    def find_maps(self, **kw) -> list:
        from .finder import find_maps
        self.candidates = find_maps(self.buf.data, **kw)
        self._fill_candidates()
        return self.candidates

    def find_maps_async(self) -> None:
        if self._find_thread is not None and self._find_thread.is_alive():
            return
        self.b_find.setEnabled(False)
        self.acts["find"].setEnabled(False)
        self.find_status.setText("Searching...")
        self.left.setCurrentIndex(1)
        data = bytes(self.buf.data)
        self._find_result = None

        def work():
            from .finder import find_maps
            try:
                self._find_result = find_maps(data)
            except Exception as e:  # noqa: BLE001 - reported in the panel
                self._find_result = e
        self._find_thread = threading.Thread(target=work, daemon=True)
        self._find_thread.start()
        self._poll = QTimer(self, interval=100)
        self._poll.timeout.connect(self._poll_find)
        self._poll.start()

    def _poll_find(self) -> None:
        if self._find_thread is not None and self._find_thread.is_alive():
            return
        self._poll.stop()
        self.b_find.setEnabled(True)
        self.acts["find"].setEnabled(True)
        res = self._find_result
        if isinstance(res, Exception):
            self.find_status.setText(f"The search failed: {res}")
        else:
            self.candidates = res or []
            self._fill_candidates()
        self.findFinished.emit()

    def _fill_candidates(self) -> None:
        self.pot.clear()
        in_pack = {(m.address, m.cols, m.rows) for m in self.pack.maps}
        for i, c in enumerate(self.candidates):
            m = c.mapdef
            dims = f"{m.cols}x{m.rows}" if m.rows > 1 else f"{m.cols}"
            it = QTreeWidgetItem([f"{c.score:.0f}", fmt_hex(m.address), dims,
                                  m.dtype + ("" if m.cell_size == 1 else " " + m.endian.upper()) +
                                  (" col" if m.order == "col" and m.rows > 1 else ""), c.layout])
            it.setData(0, ROLE, i)
            if (m.address, m.cols, m.rows) in in_pack:
                for k in range(5):
                    it.setForeground(k, self.palette().placeholderText())
            self.pot.addTopLevelItem(it)
        self.find_status.setText(f"{len(self.candidates)} potential map(s) - best first. Double-click to view, "
                                 "Add to Map Pack to keep.")
        self.left.setTabText(1, f"Potential Maps ({len(self.candidates)})")
        self._update_bands()

    def _on_candidate(self, it, _col=0) -> None:
        i = it.data(0, ROLE)
        if i is not None and 0 <= i < len(self.candidates):
            self.preview_candidate(i)

    def preview_candidate(self, i: int) -> MapDef:
        m = self.candidates[i].mapdef
        self.editor.set_map(m)
        self.center.setCurrentWidget(self.editor)
        return m

    def add_selected_candidates(self) -> int:
        items = self.pot.selectedItems()
        if not items and self.pot.currentItem() is not None:
            items = [self.pot.currentItem()]
        n = 0
        for it in items:
            i = it.data(0, ROLE)
            if i is None:
                continue
            m = self.candidates[i].mapdef.copy()
            self.pack.add(m, replace=False)
            n += 1
        if n:
            self.pack_dirty = True
            self.fill_pack_tree()
            self._fill_candidates()
            self._emit_modified()
            self.message.emit(f"{n} map(s) added to the map pack")
        return n

    def add_candidates(self, indices) -> int:
        for i in indices:
            self.pack.add(self.candidates[i].mapdef.copy(), replace=False)
        self.pack_dirty = True
        self.fill_pack_tree()
        self._fill_candidates()
        self._emit_modified()
        return len(list(indices))

    # ------------------------------------------------------------------ differences
    def refresh_differences(self) -> None:
        self.diff.clear()
        cur = self.buf.data
        maps = ops.changed_maps(self.pack, self.original, cur)
        for d in maps:
            m = d["map"]
            change = f"{d['min_pct']:+.1f}% .. {d['max_pct']:+.1f}%" if d["cells"] else ""
            if d["axes"]:
                change += " (axis changed)"
            it = QTreeWidgetItem([m.name, f"{d['cells']} / {d['total']}", change])
            it.setData(0, ROLE, ("map", m.name))
            self.diff.addTopLevelItem(it)
        rest = ops.unmapped_changes(self.pack, self.original, cur)
        for s, e in rest[:2000]:
            it = QTreeWidgetItem([f"{fmt_hex(s)} .. {fmt_hex(e - 1)}", f"{e - s} byte(s)", "outside the maps"])
            it.setData(0, ROLE, ("range", s))
            self.diff.addTopLevelItem(it)
        total = sum(e - s for s, e in ops.diff_ranges(self.original, cur))
        self.diff_label.setText(f"Compared with the {self.original_label}: {total:,} byte(s) changed, "
                                f"{len(maps)} map(s) changed, {len(rest)} range(s) outside the maps.")
        self.left.setTabText(2, f"Differences ({len(maps) + len(rest)})")
        self.changed = maps

    def _on_diff_item(self, it, _col=0) -> None:
        d = it.data(0, ROLE)
        if not d:
            return
        if d[0] == "map":
            self.open_map(d[1])
        else:
            self.goto_hex(d[1])

    def set_original(self, data_or_path, label: str = "original file") -> None:
        if isinstance(data_or_path, (str, Path)):
            data_or_path = Path(data_or_path).read_bytes()
        self.original = bytes(data_or_path)
        self.original_label = label
        self.editor.original = self.original
        self.editor.refresh(reset=True)
        self.refresh_differences()
        self._mark_tree()

    def set_original_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Choose the Original File", str(self.path.parent if self.path else ""),
                                           "All files (*)")
        if f:
            self.set_original(f, f"original file {Path(f).name}")

    # ------------------------------------------------------------------ navigation
    def goto_hex(self, offset: int) -> None:
        self.center.setCurrentWidget(self.hex)
        self.hex.set_cursor(offset)
        self.hex.ensure_visible(offset)

    def goto_graph(self, offset: int) -> None:
        self.center.setCurrentIndex(1)
        self.graph.goto(offset)

    def _on_graph_click(self, off: int) -> None:
        m = self.pack.at(off)
        if m is not None:
            self.open_map(m)
            self.center.setCurrentIndex(1)
        self.hex.set_cursor(off)
        self.message.emit(f"Offset {fmt_hex(off)}" + (f" - {m.name}" if m is not None else ""))

    def _update_bands(self) -> None:
        bands = [(m.span()[0], m.span()[1], m.name) for m in self.pack.maps]
        names = {(b[0], b[1]) for b in bands}
        bands += [(c.span()[0], c.span()[1], f"? {c.score:.0f}") for c in self.candidates[:500]
                  if (c.span()[0], c.span()[1]) not in names]
        self.graph.bands = bands
        self.graph.viewport().update()

    # ------------------------------------------------------------------ import / export
    def _merge(self, pack: MapPack, replace: bool) -> int:
        if replace:
            self.pack.maps = []
        for m in pack.maps:
            self.pack.add(m, replace=True)
        self.pack_dirty = True
        self.fill_pack_tree()
        self._emit_modified()
        return len(pack.maps)

    def import_a2l(self, path, base: int | None = None, replace: bool = False):
        from .a2l import load_a2l
        res = load_a2l(path, self.buf.data, base)
        self.pack.base_address = res.pack.base_address
        n = self._merge(res.pack, replace)
        self.message.emit(f"A2L: {n} map(s) imported (base {fmt_hex(res.pack.base_address)})" +
                          (f", {len(res.warnings)} note(s)" if res.warnings else ""))
        return res

    def import_a2l_dialog(self, path=None) -> bool:
        from .a2l import load_a2l
        from .dialogs import ImportOptionsDialog
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import ASAP2 / A2L", str(self.path.parent if self.path else ""),
                                                  "A2L files (*.a2l *.A2L);;All files (*)")
            if not path:
                return False
        try:
            guess = load_a2l(path, self.buf.data).pack.base_address
        except Exception as e:  # noqa: BLE001 - shown to the user
            QMessageBox.warning(self, "Import A2L", f"Cannot read {Path(path).name}:\n{e}")
            return False
        dlg = ImportOptionsDialog("Import A2L", guess, self, "A2L addresses are ECU addresses. The address of file "
                                  "offset 0 turns them into offsets in this file.")
        if dlg.exec() != ImportOptionsDialog.DialogCode.Accepted:
            return False
        res = self.import_a2l(path, dlg.base_address(), dlg.replace.isChecked())
        if res.warnings:
            QMessageBox.information(self, "Import A2L", "\n".join(res.warnings[:30]))
        return True

    def import_ini(self, path, base: int = 0, replace: bool = False, include_scalars: bool = False):
        from .tsini import load_ini
        res = load_ini(path, base=base, include_scalars=include_scalars)
        n = self._merge(res.pack, replace)
        self.message.emit(f"TunerStudio ini: {n} map(s) imported ({res.signature or Path(path).name})")
        return res

    def import_ini_dialog(self, path=None) -> bool:
        from .dialogs import ImportOptionsDialog
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Import TunerStudio ini", str(self.path.parent if self.path
                                                                                      else ""),
                                                  "TunerStudio ini (*.ini);;All files (*)")
            if not path:
                return False
        dlg = ImportOptionsDialog("Import TunerStudio ini", 0, self,
                                  "Offsets in the ini are relative to the configuration pages (page 1 first). Use "
                                  "the offset where the pages start in this file.", scalars=False)
        if dlg.exec() != ImportOptionsDialog.DialogCode.Accepted:
            return False
        self.import_ini(path, dlg.base_address(), dlg.replace.isChecked(), dlg.scalars.isChecked())
        return True

    def import_csv(self, path, replace: bool = False) -> int:
        pack = pack_from_csv(Path(path).read_text(encoding="utf-8-sig"))
        return self._merge(pack, replace)

    def import_csv_dialog(self) -> bool:
        path, _ = QFileDialog.getOpenFileName(self, "Import Map List (CSV)", "", "CSV (*.csv *.txt);;All files (*)")
        if path:
            n = self.import_csv(path)
            self.message.emit(f"CSV: {n} map(s) imported")
        return bool(path)

    def import_pack(self, path, replace: bool = False) -> int:
        return self._merge(MapPack.load(path), replace)

    def import_pack_dialog(self) -> bool:
        path, _ = QFileDialog.getOpenFileName(self, "Import Map Pack", "", "Map packs (*.json);;All files (*)")
        if path:
            self.import_pack(path)
        return bool(path)

    def export_a2l(self, path) -> Path:
        from .a2l import export_a2l
        p = Path(path)
        p.write_text(export_a2l(self.pack, segment_size=len(self.buf.data)), encoding="utf-8")
        self.message.emit(f"A2L written: {p.name} ({len(self.pack)} map(s))")
        return p

    def export_a2l_dialog(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Export A2L", str(self.path.with_suffix(".a2l") if self.path
                                                                       else "maps.a2l"), "A2L files (*.a2l)")
        if path:
            self.export_a2l(path)
        return bool(path)

    def export_csv(self, path) -> Path:
        p = Path(path)
        p.write_text(pack_to_csv(self.pack), encoding="utf-8")
        return p

    def export_csv_dialog(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Export Map List (CSV)", "maps.csv", "CSV (*.csv)")
        if path:
            self.export_csv(path)
        return bool(path)

    def export_pack_dialog(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Export Map Pack", str(self.pack.path or "maps.maps.json"),
                                              "Map packs (*.json)")
        if path:
            self.pack.save(path)
        return bool(path)

    def compare_dialog(self) -> None:
        f, _ = QFileDialog.getOpenFileName(self, "Compare With", str(self.path.parent if self.path else ""),
                                           "All files (*)")
        if f and self.path is not None:
            self.compareRequested.emit(str(self.path), f)


# ====================================================================== compare two binaries
class CompareDocument(QWidget):
    """File A (editable) against file B (read-only): which maps differ, both versions, copy B -> A."""
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()
    message = pyqtSignal(str)
    hexCompareRequested = pyqtSignal(str, str)

    def __init__(self, path_a, path_b, pack: MapPack | None = None, parent=None):
        super().__init__(parent)
        from ...retro.rom.buffer import HexBuffer
        self.path = Path(path_a)
        self.path_b = Path(path_b)
        self.buf = HexBuffer(self.path.read_bytes(), self.path)
        self.data_b = self.path_b.read_bytes()
        if pack is None and pack_path_for(self.path).is_file():
            pack = MapPack.load(pack_path_for(self.path))
        self.from_finder = False
        if pack is None or not pack.maps:
            from .finder import find_maps
            pack = MapPack(name="found maps", maps=[c.mapdef for c in find_maps(self.buf.data, max_results=300)])
            self.from_finder = True
        self.pack = pack
        self._build()
        self.buf.listeners.append(lambda *_a: self._changed())
        self.fill()

    @property
    def retro_path(self):
        return self.path

    def is_modified(self) -> bool:
        return self.buf.modified

    def save(self) -> bool:
        try:
            self.buf.save(self.path)
        except OSError as e:
            QMessageBox.warning(self, "Compare", f"Cannot save {self.path.name}:\n{e}")
            return False
        self.modifiedChanged.emit(False)
        self.saved.emit()
        return True

    def edit_op(self, op: str) -> None:
        if op == "undo":
            self.buf.undo()
        elif op == "redo":
            self.buf.redo()
        elif op == "copy":
            self.ed_a.copy()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        top.setContentsMargins(6, 4, 6, 4)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        top.addWidget(self.summary, 1)
        self.only_diff = QCheckBox("Only maps that differ")
        self.only_diff.setChecked(True)
        self.only_diff.toggled.connect(lambda _v: self.fill())
        top.addWidget(self.only_diff)
        self.b_copy = QPushButton("Copy Map from B to A")
        self.b_copy.clicked.connect(lambda: self.copy_current())
        top.addWidget(self.b_copy)
        self.b_copy_all = QPushButton("Copy All Different Maps")
        self.b_copy_all.clicked.connect(lambda: self.copy_all())
        top.addWidget(self.b_copy_all)
        b_hex = QPushButton("Hex Compare")
        b_hex.clicked.connect(lambda: self.hexCompareRequested.emit(str(self.path), str(self.path_b)))
        top.addWidget(b_hex)
        lay.addLayout(top)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QTreeWidget()
        self.list.setHeaderLabels(["Map", "Address", "In B", "Cells"])
        self.list.setProperty("i18n_skip_items", True)
        self.list.setRootIsDecorated(False)
        self.list.currentItemChanged.connect(lambda it, _p: self._on_item(it))
        self.list.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        split.addWidget(self.list)
        right = QSplitter(Qt.Orientation.Horizontal)
        boxa, boxb = QWidget(), QWidget()
        la, lb = QVBoxLayout(boxa), QVBoxLayout(boxb)
        la.setContentsMargins(0, 0, 0, 0)
        lb.setContentsMargins(0, 0, 0, 0)
        la.addWidget(QLabel(f"A: {self.path.name} (editable)"))
        lb.addWidget(QLabel(f"B: {self.path_b.name} (read-only)"))
        self.ed_a = MapEditor(self.buf, self.data_b)
        self.ed_a.colour.setCurrentIndex(1)
        self.ed_a.message.connect(self.message)
        self.ed_b = MapEditor(bytearray(self.data_b), bytes(self.buf.data), read_only=True)
        self.ed_b.colour.setCurrentIndex(1)
        la.addWidget(self.ed_a)
        lb.addWidget(self.ed_b)
        right.addWidget(boxa)
        right.addWidget(boxb)
        split.addWidget(right)
        split.setStretchFactor(1, 4)
        lay.addWidget(split, 1)

    def rows(self) -> list[dict]:
        out = []
        a = self.buf.data
        for m in self.pack.maps:
            delta = ops.locate_in(m, a, self.data_b)
            if delta is None:
                out.append({"map": m, "delta": None, "cells": None})
                continue
            mb = m.copy()
            mb.address += delta
            for ax in (mb.x_axis, mb.y_axis):
                if ax.stored:
                    ax.address = int(ax.address) + delta
            za, zb = m.raw(a), mb.raw(self.data_b)
            out.append({"map": m, "delta": delta, "cells": int((za != zb).sum()), "map_b": mb})
        return out

    def fill(self) -> None:
        cur = self.list.currentItem()
        cur_name = cur.data(0, ROLE) if cur is not None else None
        self.list.clear()
        rows = self.rows()
        self._rows = {r["map"].name: r for r in rows}
        diff_maps = 0
        for r in rows:
            m = r["map"]
            differs = r["cells"] is None or r["cells"] > 0
            diff_maps += 1 if differs else 0
            if self.only_diff.isChecked() and not differs:
                continue
            where = "-" if r["delta"] is None else ("same address" if r["delta"] == 0 else f"{r['delta']:+#x}")
            cells = "?" if r["cells"] is None else f"{r['cells']} / {m.cells}"
            it = QTreeWidgetItem([m.name, fmt_hex(m.address), where, cells])
            it.setData(0, ROLE, m.name)
            self.list.addTopLevelItem(it)
            if m.name == cur_name:
                self.list.setCurrentItem(it)
        total = sum(e - s for s, e in ops.diff_ranges(self.buf.data, self.data_b))
        src = "maps found by the map finder" if self.from_finder else "the map pack of A"
        self.summary.setText(f"{total:,} byte(s) differ. {diff_maps} of {len(rows)} map(s) differ ({src}).")
        if self.list.currentItem() is None and self.list.topLevelItemCount():
            self.list.setCurrentItem(self.list.topLevelItem(0))

    def _on_item(self, it) -> None:
        if it is None:
            return
        r = self._rows.get(it.data(0, ROLE))
        if r is None:
            return
        self.ed_a.set_map(r["map"])
        self.ed_b.set_map(r.get("map_b"))

    def current_map(self) -> MapDef | None:
        it = self.list.currentItem()
        return self._rows[it.data(0, ROLE)]["map"] if it is not None else None

    def copy_map(self, name: str) -> bool:
        r = self._rows.get(name)
        if r is None or r["delta"] is None:
            return False
        m = r["map"]
        mb = r["map_b"]
        changed = False
        for (sa, ea), (sb, _eb) in zip(m.ranges(), mb.ranges()):
            new = self.data_b[sb:sb + (ea - sa)]
            if bytes(self.buf.data[sa:ea]) != new:
                self.buf.replace(sa, new)
                changed = True
        if changed:
            self.message.emit(f"{name} copied from {self.path_b.name}")
        return changed

    def copy_current(self) -> bool:
        m = self.current_map()
        return self.copy_map(m.name) if m is not None else False

    def copy_all(self) -> int:
        n = sum(1 for name, r in list(self._rows.items()) if r["cells"] and self.copy_map(name))
        return n

    def _changed(self) -> None:
        QTimer.singleShot(0, self._refresh_after_edit)

    def _refresh_after_edit(self) -> None:
        try:
            self.modifiedChanged.emit(self.buf.modified)
            self.ed_b.original = bytes(self.buf.data)
            self.fill()
            self.ed_a.refresh()
            self.ed_b.refresh()
        except RuntimeError:
            pass

