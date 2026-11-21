"""HexDocument - the hex editor document tab: hex view, Find / Replace bar, side panels (ROM Info with the
structure overlay and file listing, Data Inspector, Bookmarks, Search Results) and a status line."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QKeySequence
from PyQt6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QHeaderView,
                             QInputDialog, QLabel, QListWidget, QListWidgetItem, QMenu, QMessageBox, QSplitter,
                             QTableWidget, QTableWidgetItem, QTabWidget, QToolBar, QToolButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from .buffer import HexBuffer, PatternError, hex_pattern, parse_hex_bytes, text_pattern
from .detect import RomInfo, detect
from .dialogs import FindPanel, GotoDialog
from .formats import COPY_FORMATS
from .hexview import HexView
from .inspector import inspect

ROLE = Qt.ItemDataRole.UserRole
CODECS = [("Latin-1", "latin-1"), ("ASCII", "ascii"), ("Shift-JIS", "shift_jis"), ("CP437 (DOS)", "cp437"),
          ("EBCDIC", "cp037")]


class HexDocument(QWidget):
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()
    compareRequested = pyqtSignal(str, str)      # left path, right path
    message = pyqtSignal(str)

    def __init__(self, path=None, data: bytes | None = None, parent=None, read_only: bool = False):
        super().__init__(parent)
        self.read_only = read_only
        self.path = Path(path) if path else None
        self.buf = HexBuffer(data if data is not None else (self.path.read_bytes() if self.path else b""), self.path)
        self.info: RomInfo = RomInfo()
        self.tables: list = []
        self._last_modified = False
        self.view = HexView(self.buf)
        self.view.read_only = read_only
        self._build()
        self.view.cursorMoved.connect(self._on_cursor)
        self.view.selectionChanged.connect(lambda *_a: self._update_status())
        self.view.edited.connect(self._on_edited)
        self.view.modeChanged.connect(lambda _m: self._update_status())
        self._info_timer = QTimer(self, singleShot=True, interval=600)
        self._info_timer.timeout.connect(self.refresh_info)
        self.refresh_info()
        self._on_cursor(0)

    # ------------------------------------------------------------------ protocol used by the IDE feature
    @property
    def retro_path(self):          # radide/retro/filebus.py
        return self.path

    def is_modified(self) -> bool:
        return self.buf.modified

    def save(self) -> bool:
        if self.read_only:
            if self.buf.modified:
                QMessageBox.information(self, "Hex Editor", "This file is open read-only (the source ROM of a ROM "
                                        "Hacking project is never changed). Use Save As to write a copy.")
            return False
        if self.path is None:
            return self.save_as()
        try:
            self.buf.save(self.path)
        except OSError as e:
            QMessageBox.warning(self, "Hex Editor", f"Cannot save {self.path}:\n{e}")
            return False
        self._emit_modified()
        self.saved.emit()
        return True

    def save_as(self, path=None) -> bool:
        if path is None:
            start = str(self.path) if self.path else ""
            f, _ = QFileDialog.getSaveFileName(self, "Save As", start, "All files (*)")
            if not f:
                return False
            path = f
        self.path = Path(path)
        self.buf.path = self.path
        self.read_only = False
        self.view.read_only = False
        return self.save()

    def reload_from_disk(self) -> None:
        if self.path is None or not self.path.is_file():
            return
        cur = self.view.cursor
        self.buf = HexBuffer(self.path.read_bytes(), self.path)
        self.view.set_buffer(self.buf)
        self.view.set_cursor(min(cur, len(self.buf)))
        self.refresh_info()
        self._emit_modified()

    def edit_op(self, op: str) -> None:
        fn = {"undo": self.view.undo, "redo": self.view.redo, "copy": self.view.copy, "cut": self.view.cut,
              "paste": self.view.paste, "delete": self.view.delete_selection,
              "select_all": self.view.select_all}.get(op)
        if fn is not None:
            fn()

    def data(self) -> bytes:
        return bytes(self.buf.data)

    # ------------------------------------------------------------------ ui
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        tb = QToolBar()
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.toolbar = tb

        self._keys: dict[str, object] = {}

        def act(text, slot, shortcut=None, tip=""):
            a = QAction(text, self)
            a.triggered.connect(lambda _c=False: slot())
            if shortcut:          # handled by the view (HexView.shortcut_handler): no clash with the IDE's keys
                self._keys[QKeySequence(shortcut).toString()] = slot
            if tip:
                a.setToolTip(tip)
            tb.addAction(a)
            return a
        self.a_goto = act("Go To...", self.goto_dialog, "Ctrl+G", "Go to an offset (Ctrl+G)")
        self.a_find = act("Find...", self.show_find, "Ctrl+F", "Find / Replace hex or text (Ctrl+F)")
        self._keys[QKeySequence("F3").toString()] = lambda: self.find_next(False)
        self._keys[QKeySequence("Shift+F3").toString()] = lambda: self.find_next(True)
        self._keys[QKeySequence("Shift+F2").toString()] = lambda: self.goto_bookmark(True)
        self.a_insert = act("Overwrite", self.toggle_insert, None, "Insert / Overwrite mode (Insert key)")
        tb.addSeparator()
        self.a_bookmark = act("Bookmark", self.toggle_bookmark, "Ctrl+F2", "Toggle a bookmark (Ctrl+F2)")
        act("Next Bookmark", lambda: self.goto_bookmark(False), "F2")
        tb.addSeparator()
        copy_btn = QToolButton()
        copy_btn.setText("Copy As")
        copy_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(copy_btn)
        for key, label in COPY_FORMATS:
            m.addAction(label, lambda k=key: self.view.copy(k))
        copy_btn.setMenu(m)
        tb.addWidget(copy_btn)
        tb.addSeparator()
        tb.addWidget(QLabel(" Bytes/row: "))
        self.bpr = QComboBox()
        self.bpr.addItems(["8", "16", "32"])
        self.bpr.setCurrentText("16")
        self.bpr.currentTextChanged.connect(lambda t: self.view.set_bytes_per_row(int(t)))
        tb.addWidget(self.bpr)
        tb.addWidget(QLabel(" Text: "))
        self.textmode = QComboBox()
        for label, codec in CODECS:
            self.textmode.addItem(label, ("codec", codec))
        self.textmode.addItem("Load Table (.tbl)...", ("load", ""))
        self.textmode.activated.connect(self._on_textmode)
        tb.addWidget(self.textmode)
        tb.addSeparator()
        tools = QToolButton()
        tools.setText("ROM Tools")
        tools.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        tm = QMenu(tools)
        self.a_fix = tm.addAction("Fix Header Checksum", self.fix_checksum)
        tm.addAction("Compare With File...", self.compare_dialog)
        tm.addAction("Create Patch From This File...", self.create_patch_dialog)
        tm.addAction("Apply Patch To This File...", self.apply_patch_dialog)
        tm.addSeparator()
        tm.addAction("Relative Search...", self.relative_search_dialog)
        tm.addAction("Find Text Strings (table)", self.dump_strings)
        tm.addAction("Fill Selection...", self.fill_dialog)
        tools.setMenu(tm)
        tb.addWidget(tools)
        lay.addWidget(tb)
        self.view.shortcut_keys = set(self._keys)
        self.view.shortcut_handler = self._shortcut
        self.find_panel = FindPanel(self)
        self.find_panel.hide()
        self.find_panel.findRequested.connect(self.find_next)
        self.find_panel.findAllRequested.connect(self.find_all)
        self.find_panel.replaceRequested.connect(self.replace)
        self.find_panel.closed.connect(lambda: (setattr(self.view, "hit", None), self.view.viewport().update(),
                                                self.view.setFocus()))
        lay.addWidget(self.find_panel)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.view)
        self.side = QTabWidget()
        self.info_tree = QTreeWidget()
        self.info_tree.setHeaderLabels(["Property", "Value"])
        self.info_tree.setRootIsDecorated(False)
        self.info_tree.itemActivated.connect(self._on_info_item)
        self.info_tree.itemClicked.connect(self._on_info_item)
        self.listing = QTreeWidget()
        self.listing.setRootIsDecorated(False)
        self.listing.itemActivated.connect(self._on_info_item)
        self.listing.itemClicked.connect(self._on_info_item)
        info_box = QSplitter(Qt.Orientation.Vertical)
        info_box.addWidget(self.info_tree)
        info_box.addWidget(self.listing)
        info_box.setStretchFactor(0, 2)
        info_box.setStretchFactor(1, 1)
        self.side.addTab(info_box, "ROM Info")
        self.inspector = QTableWidget(0, 2)
        self.inspector.setHorizontalHeaderLabels(["Type", "Value"])
        self.inspector.verticalHeader().hide()
        self.inspector.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.inspector.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.side.addTab(self.inspector, "Inspector")
        self.bookmarks = QListWidget()
        self.bookmarks.itemActivated.connect(lambda it: self.view.set_cursor(it.data(ROLE)))
        self.bookmarks.itemClicked.connect(lambda it: self.view.set_cursor(it.data(ROLE)))
        self.side.addTab(self.bookmarks, "Bookmarks")
        self.results = QListWidget()
        self.results.itemActivated.connect(self._on_result)
        self.results.itemClicked.connect(self._on_result)
        self.side.addTab(self.results, "Results")
        split.addWidget(self.side)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        split.setSizes([800, 340])
        lay.addWidget(split, 1)
        self.status = QLabel()
        self.status.setContentsMargins(6, 2, 6, 2)
        lay.addWidget(self.status)

    def _shortcut(self, combo: str) -> bool:
        fn = self._keys.get(combo)
        if fn is None:
            return False
        fn()
        return True

    # ------------------------------------------------------------------ state
    def _emit_modified(self) -> None:
        m = self.buf.modified
        if m != self._last_modified:
            self._last_modified = m
            self.modifiedChanged.emit(m)

    def _on_edited(self) -> None:
        self._emit_modified()
        self._info_timer.start()
        self._on_cursor(self.view.cursor)

    def _on_cursor(self, off: int) -> None:
        cpu = None
        if self.info.cpu_address is not None:
            try:
                cpu = self.info.cpu_address(off)
            except Exception:  # noqa: BLE001
                cpu = None
        rows = inspect(self.buf.data, off, self.view.table, cpu if self.info.cpu in ("6502", "") else None)
        if cpu is not None:
            rows.insert(1, (f"CPU address ({self.info.cpu})", f"${cpu:X}"))
        f = self.view._field_at(off) if self.view.fields else None
        if f is not None:
            rows.insert(1, ("Header field", f"{f.name}: {f.value}"))
        self.inspector.setRowCount(len(rows))
        for r, (k, v) in enumerate(rows):
            self.inspector.setItem(r, 0, QTableWidgetItem(k))
            self.inspector.setItem(r, 1, QTableWidgetItem(v))
        self.inspector.resizeColumnToContents(0)
        self._update_status(cpu)

    def _update_status(self, cpu=None) -> None:
        s, n = self.view.selection()
        off = self.view.cursor
        parts = [f"Offset 0x{off:X} ({off:,})"]
        if cpu is not None:
            parts.append(f"CPU ${cpu:X}")
        if n:
            parts.append(f"Selection 0x{s:X}-0x{s + n - 1:X} ({n:,} bytes)")
        parts.append(f"Size {len(self.buf):,}")
        parts.append("INS" if self.view.insert_mode else "OVR")
        if self.view.table is not None:
            parts.append(f"Table: {self.view.table.name or 'custom'}")
        self.status.setText("    ".join(parts))
        self.a_insert.setText("Insert" if self.view.insert_mode else "Overwrite")

    def refresh_info(self) -> None:
        name = self.path.name if self.path else ""
        data = bytes(self.buf.data) if len(self.buf) <= 64 << 20 else bytes(self.buf.data[:1 << 20])
        self.info = detect(data, name)
        self.view.set_fields(self.info.fields)
        self.info_tree.clear()
        for k, v in self.info.rows:
            it = QTreeWidgetItem([k, v])
            f = next((f for f in self.info.fields if f.name == k), None)
            if f is not None:
                it.setData(0, ROLE, (f.offset, f.length))
                it.setForeground(0, QColor(f.color))
                it.setToolTip(1, f"0x{f.offset:X} - 0x{f.offset + f.length - 1:X} (click to select)")
            if "should be" in v:
                it.setForeground(1, QColor("#DC322F"))
            self.info_tree.addTopLevelItem(it)
        for w in self.info.warnings:
            it = QTreeWidgetItem(["Warning", w])
            it.setForeground(0, QColor("#CB4B16"))
            it.setToolTip(1, w)
            self.info_tree.addTopLevelItem(it)
        extra = [f for f in self.info.fields if f.name not in {k for k, _v in self.info.rows}]
        if extra:
            group = QTreeWidgetItem(["Header fields", f"{len(extra)} more (click to select)"])
            self.info_tree.addTopLevelItem(group)
            for f in extra[:3000]:
                it = QTreeWidgetItem([f"  {f.name}", f"{f.value}  @0x{f.offset:X}"])
                it.setData(0, ROLE, (f.offset, f.length))
                it.setForeground(0, QColor(f.color))
                self.info_tree.addTopLevelItem(it)
        self.info_tree.resizeColumnToContents(0)
        self.listing.clear()
        if self.info.listing:
            self.listing.setHeaderLabels(list(self.info.listing_header) or ["Item"])
            self.listing.setColumnCount(max(1, len(self.info.listing_header)))
            for row in self.info.listing[:20000]:
                it = QTreeWidgetItem(list(row))
                for c, v in enumerate(row):
                    if isinstance(v, str) and v.startswith("0x") and c == 0:
                        try:
                            it.setData(0, ROLE, (int(v, 16), 1))
                        except ValueError:
                            pass
                self.listing.addTopLevelItem(it)
            self.listing.show()
        else:
            self.listing.hide()
        self.listing.itemActivated.connect(self._on_info_item) if not getattr(self, "_listing_hooked", False) \
            else None
        self._listing_hooked = True
        self.a_fix.setEnabled(self.info.fixable)

    def _on_info_item(self, it, _col=0) -> None:
        d = it.data(0, ROLE)
        if d:
            off, length = d
            self.view.select_range(off, max(1, min(length, len(self.buf) - off)))
            self.view.scroll_to_offset(off)

    # ------------------------------------------------------------------ commands
    def goto(self, offset: int) -> None:
        self.view.set_cursor(offset)
        self.view.setFocus()

    def goto_dialog(self) -> None:
        dlg = GotoDialog(self, self.view.cursor, len(self.buf))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.goto(dlg.value)

    def toggle_insert(self) -> None:
        self.view.insert_mode = not self.view.insert_mode
        self.view.viewport().update()
        self._update_status()

    def toggle_bookmark(self, name: str = "") -> None:
        self.buf.toggle_bookmark(self.view.cursor, name)
        self._fill_bookmarks()
        self.view.viewport().update()

    def goto_bookmark(self, backward: bool = False) -> None:
        b = self.buf.next_bookmark(self.view.cursor, backward)
        if b is not None:
            self.view.set_cursor(b.offset)

    def _fill_bookmarks(self) -> None:
        self.bookmarks.clear()
        for b in self.buf.bookmarks:
            it = QListWidgetItem(f"0x{b.offset:08X}  {b.name}")
            it.setData(ROLE, b.offset)
            self.bookmarks.addItem(it)

    # ------------------------------------------------------------------ text / tables
    def _on_textmode(self, idx: int) -> None:
        kind, val = self.textmode.itemData(idx)
        if kind == "codec":
            self.view.codec = val
            self.view.set_table(None)
        elif kind == "table":
            self.view.set_table(self.tables[val])
        elif kind == "load":
            start = str(self.path.parent) if self.path else ""
            f, _ = QFileDialog.getOpenFileName(self, "Load Table", start, "Tables (*.tbl *.txt);;All files (*)")
            if f:
                self.load_table(f)
            else:
                self.textmode.setCurrentIndex(0)
        self._on_cursor(self.view.cursor)

    def load_table(self, path_or_table) -> None:
        from .tbl import Table
        t = path_or_table if isinstance(path_or_table, Table) else Table.load(path_or_table)
        self.tables.append(t)
        idx = self.textmode.count() - 1
        self.textmode.insertItem(idx, f"Table: {t.name or 'custom'}", ("table", len(self.tables) - 1))
        self.textmode.setCurrentIndex(idx)
        self.view.set_table(t)
        if t.errors:
            self.message.emit(f"{t.name}: {len(t.errors)} line(s) ignored ({t.errors[0]})")
        self._update_status()

    # ------------------------------------------------------------------ find / replace
    def show_find(self) -> None:
        self.find_panel.show()
        s, n = self.view.selection()
        if n and n <= 64 and not self.find_panel.find.text():
            self.find_panel.find.setText(" ".join(f"{b:02X}" for b in self.buf.read(s, n)))
        self.find_panel.find.setFocus()
        self.find_panel.find.selectAll()

    def pattern(self):
        fp = self.find_panel
        text = fp.find.text()
        mode = fp.mode.currentIndex()
        if mode == 0:
            return hex_pattern(text)
        return text_pattern(text, self.view.codec, fp.case.isChecked(),
                            self.view.table if mode == 2 else None, fp.wild.isChecked())

    def find_next(self, backward: bool = False) -> bool:
        try:
            pat = self.pattern()
        except PatternError as e:
            self.find_panel.status.setText(str(e))
            return False
        start = self.view.cursor if backward else (self.view.hit[0] + 1 if self.view.hit and
                                                  self.view.hit[0] == self.view.cursor else self.view.cursor)
        r = self.buf.find(pat, start, backward)
        if r is None:
            self.find_panel.status.setText("Not found")
            QApplication.beep()
            return False
        self.view.hit = r
        self.view.set_cursor(r[0])
        self.find_panel.status.setText(f"Found at 0x{r[0]:X}")
        return True

    def find_all(self) -> int:
        try:
            pat = self.pattern()
        except PatternError as e:
            self.find_panel.status.setText(str(e))
            return 0
        hits = self.buf.find_all(pat, 20000)
        self.results.clear()
        for off, n in hits:
            preview = " ".join(f"{b:02X}" for b in self.buf.read(off, min(n, 12)))
            it = QListWidgetItem(f"0x{off:08X}  {preview}")
            it.setData(ROLE, (off, n))
            self.results.addItem(it)
        self.side.setCurrentWidget(self.results)
        self.find_panel.status.setText(f"{len(hits):,} match(es)")
        return len(hits)

    def _replacement(self) -> bytes:
        fp = self.find_panel
        text = fp.replace.text()
        if fp.mode.currentIndex() == 0:
            return parse_hex_bytes(text)
        if fp.mode.currentIndex() == 2 and self.view.table is not None:
            data = self.view.table.encode(text)
            if data is None:
                raise PatternError("the table has no code for some replacement characters")
            return data
        return text.encode(self.view.codec)

    def replace(self, all_: bool = False) -> int:
        if self.read_only:
            self.find_panel.status.setText("read-only")
            return 0
        try:
            pat = self.pattern()
            new = self._replacement()
        except (PatternError, UnicodeEncodeError) as e:
            self.find_panel.status.setText(str(e))
            return 0
        if all_:
            n = self.buf.replace_all(pat, new)
            self.find_panel.status.setText(f"Replaced {n:,} match(es)")
            self.view.hit = None
            self._on_edited()
            self.view.viewport().update()
            return n
        hit = self.view.hit
        if hit is None or hit[0] != self.view.cursor:
            self.find_next(False)
            return 0
        self.buf.replace(hit[0], new, hit[1])
        self.view.hit = None
        self.view.set_cursor(hit[0] + len(new))
        self._on_edited()
        self.find_next(False)
        return 1

    def _on_result(self, it) -> None:
        d = it.data(ROLE)
        if d:
            off, n = d
            self.view.hit = (off, n)
            self.view.set_cursor(off)

    # ------------------------------------------------------------------ ROM tools
    def fix_checksum(self) -> bool:
        from .detect import fix_checksum
        if self.read_only:
            QMessageBox.information(self, "Fix Checksum", "The file is open read-only.")
            return False
        try:
            data, msg = fix_checksum(bytes(self.buf.data), self.path.name if self.path else "")
        except ValueError as e:
            QMessageBox.information(self, "Fix Checksum", str(e))
            return False
        old = bytes(self.buf.data)
        if data == old:
            self.message.emit("The checksum is already correct.")
            return True
        # one undo step per changed run (header bytes only)
        i = 0
        while i < len(data):
            if data[i] != old[i]:
                j = i
                while j < len(data) and data[j] != old[j]:
                    j += 1
                self.buf.overwrite(i, data[i:j])
                i = j
            else:
                i += 1
        self._on_edited()
        self.refresh_info()
        self.message.emit(f"Fixed: {msg} (save to keep it)")
        return True

    def compare_dialog(self) -> None:
        start = str(self.path.parent) if self.path else ""
        f, _ = QFileDialog.getOpenFileName(self, "Compare With", start, "All files (*)")
        if f and self.path is not None:
            self.compareRequested.emit(str(self.path), f)

    def create_patch_dialog(self) -> None:
        from .dialogs import CreatePatchDialog
        dlg = CreatePatchDialog(self, "", str(self.path or ""), modified_data=bytes(self.buf.data))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.message.emit(f"Patch written: {dlg.result_path} ({dlg.result_size:,} bytes)")

    def apply_patch_dialog(self) -> None:
        from .dialogs import ApplyPatchDialog
        dlg = ApplyPatchDialog(self, str(self.path or ""))
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.message.emit(f"Patched ROM written: {dlg.result_path}")

    def relative_search_dialog(self) -> None:
        from .tbl import relative_search, table_from_relative
        word, ok = QInputDialog.getText(self, "Relative Search",
                                        "A word you can see in the game (letters only, 3+ characters):")
        word = word.strip()
        if not ok or len(word) < 3 or not word.isalpha():
            return
        hits = relative_search(self.buf.data[:16 << 20], word)
        self.results.clear()
        for off, first in hits:
            it = QListWidgetItem(f"0x{off:08X}  '{word[0]}' = {first:02X}")
            it.setData(ROLE, (off, len(word)))
            it.setData(ROLE + 1, (first, word[0]))
            self.results.addItem(it)
        self.side.setCurrentWidget(self.results)
        if not hits:
            QMessageBox.information(self, "Relative Search", "No match.")
            return
        if QMessageBox.question(self, "Relative Search",
                                f"{len(hits)} match(es). Build a table from the first one "
                                f"('{word[0]}' = {hits[0][1]:02X})?") == QMessageBox.StandardButton.Yes:
            self.load_table(table_from_relative(hits[0][1], word[0]))

    def dump_strings(self) -> None:
        from .tbl import Table
        t = self.view.table or Table.ascii()
        found = t.find_strings(self.buf.data[:8 << 20], 5, 5000)
        self.results.clear()
        for off, text in found:
            it = QListWidgetItem(f"0x{off:08X}  {text[:80]}")
            it.setData(ROLE, (off, 1))
            self.results.addItem(it)
        self.side.setCurrentWidget(self.results)
        self.message.emit(f"{len(found):,} string(s) with table '{t.name}'")

    def fill_dialog(self) -> None:
        if self.read_only:
            return
        s, n = self.view.selection()
        if not n:
            QMessageBox.information(self, "Fill", "Select the bytes to fill first.")
            return
        text, ok = QInputDialog.getText(self, "Fill Selection", f"Hex pattern to repeat over {n:,} bytes:", text="FF")
        if not ok:
            return
        try:
            pat = parse_hex_bytes(text)
        except PatternError as e:
            QMessageBox.warning(self, "Fill", str(e))
            return
        self.buf.fill(s, n, pat)
        self._on_edited()


__all__ = ["HexDocument"]
