"""The CPU view (OllyDbg style): four synchronised panes over one debugger backend.

    +-------------------------------------------+------------------+
    | Disassembly: arrows | address | bytes |   | Registers        |
    |   instruction | comment                   |  General / FPU / |
    | info line (jump taken? memory operand)    |  SSE, flag bits  |
    +-------------------------------------------+------------------+
    | Dump: address | 16 hex bytes | ASCII      | Stack            |
    +-------------------------------------------+------------------+

Keys (only while the CPU view has the focus - they do not steal the IDE's own F-keys elsewhere):
F2 breakpoint, F4 run to cursor, F7 step into, F8 step over, Ctrl+F9 execute till return, F9 run, Ctrl+G go to
address / expression, Space assemble, Ctrl+E binary edit, ';' comment, ':' label, Enter follow, '-' back,
'*' current instruction.
"""
from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import QEvent, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QKeySequence, QPainter, QPen, QPolygon
from PyQt6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout,
                             QHeaderView, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                             QMessageBox, QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTabWidget,
                             QToolButton, QVBoxLayout, QWidget)

from . import analysis as A
from .notes import CpuNotes, notes_path
from .texts import T, both

ROLE_ADDR = Qt.ItemDataRole.UserRole
MONO = "Consolas"


def mono(size: int = 9) -> QFont:
    f = QFont(MONO, size)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def dark() -> bool:
    try:
        from ... import theme
        return theme.is_dark()
    except Exception:  # noqa: BLE001
        return False


def colors() -> dict:
    if dark():
        return {"pc": QColor("#4b4b18"), "bp": QColor("#7a1f1f"), "changed": QColor("#ff6b6b"), "label": QColor("#ffcc66"),
                "jump": QColor("#a0a0a0"), "sel": QColor("#ffffff"), "taken": QColor("#ff5555"),
                "comment": QColor("#7fbf7f"), "sp": QColor("#1f3d5c"), "muted": QColor("#8a8a8a"),
                "call": QColor("#66b3ff"), "src": QColor("#9cdcfe")}
    return {"pc": QColor("#fff3a0"), "bp": QColor("#ffb3b3"), "changed": QColor("#d00000"), "label": QColor("#7a3e00"),
            "jump": QColor("#9a9a9a"), "sel": QColor("#000000"), "taken": QColor("#d00000"),
            "comment": QColor("#2e7d32"), "sp": QColor("#cfe3ff"), "muted": QColor("#8a8a8a"),
            "call": QColor("#0050b0"), "src": QColor("#1f4e9c")}


def _item(text: str, addr: int | None = None, editable: bool = False) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if addr is not None:
        it.setData(ROLE_ADDR, addr)
    flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
    if editable:
        flags |= Qt.ItemFlag.ItemIsEditable
    it.setFlags(flags)
    return it


def _table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.verticalHeader().setVisible(False)
    t.verticalHeader().setDefaultSectionSize(18)
    t.setFont(mono())
    t.setShowGrid(False)
    t.setWordWrap(False)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    t.horizontalHeader().setHighlightSections(False)
    t.setProperty("i18n_skip_items", True)
    t.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    return t


def parse_number(text: str) -> int | None:
    t = (text or "").strip().replace("_", "")
    if not t:
        return None
    try:
        if t.lower().endswith("h"):
            return int(t[:-1], 16)
        if t.lower().startswith(("0x", "-0x")):
            return int(t, 16)
        if re.fullmatch(r"-?\d+", t):
            return int(t)
        return int(t, 16)
    except ValueError:
        return None


# ====================================================================== disassembly
class DisasmTable(QTableWidget):
    """The disassembly grid; paints the jump arrows over column 0."""

    def __init__(self, pane: "DisasmPane"):
        super().__init__(0, 5)
        self.pane = pane

    def paintEvent(self, e):
        super().paintEvent(e)
        try:
            self._paint_arrows()
        except Exception:  # noqa: BLE001 - painting must never raise
            pass

    def _paint_arrows(self):
        rows = self.pane.rows
        if not rows:
            return
        index = {ins.address: i for i, ins in enumerate(rows)}
        col_w = self.columnWidth(0)
        if col_w < 8:
            return
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        c = colors()
        sel = self.currentRow()
        pc = self.pane.pc
        jumps = []
        for i, ins in enumerate(rows):
            if ins.kind in ("jmp", "jcc", "loop") and ins.target is not None:
                j = index.get(ins.target)
                if j is None:
                    j = -1 if rows and ins.target < rows[0].address else len(rows)
                jumps.append((i, j, ins))
        jumps.sort(key=lambda t: abs(t[1] - t[0]))
        lanes: list[list[tuple[int, int]]] = []
        h = self.rowHeight(0) if self.rowCount() else 18
        top_vis = self.rowAt(0)
        for i, j, ins in jumps:
            lo, hi = min(i, j), max(i, j)
            lane = next((k for k, used in enumerate(lanes) if all(hi < a or lo > b for a, b in used)), None)
            if lane is None:
                lanes.append([])
                lane = len(lanes) - 1
            lanes[lane].append((lo, hi))
            x = col_w - 6 - lane * 5
            if x < 3:
                x = 3
            y1 = self._row_y(i, h, top_vis)
            y2 = self._row_y(j, h, top_vis)
            hot = sel in (i, j)
            color = c["jump"]
            width = 1.0
            if ins.address == pc:
                taken = self.pane.taken
                color = c["taken"] if taken else c["muted"]
                width = 2.0
                if taken is False:
                    p.setPen(QPen(color, width, Qt.PenStyle.DashLine))
            if hot and ins.address != pc:
                color = c["sel"]
                width = 1.6
            if not (ins.address == pc and self.pane.taken is False):
                p.setPen(QPen(color, width))
            p.drawLine(col_w - 1, y1, x, y1)
            p.drawLine(x, y1, x, y2)
            if 0 <= j < len(rows):
                p.drawLine(x, y2, col_w - 2, y2)
                p.setBrush(QBrush(color))
                p.drawPolygon(QPolygon([QPoint(col_w - 1, y2), QPoint(col_w - 5, y2 - 3), QPoint(col_w - 5, y2 + 3)]))
                p.setBrush(Qt.BrushStyle.NoBrush)
        p.end()

    def _row_y(self, i: int, h: int, top_vis: int) -> int:
        if i < 0:
            return 0
        if i >= self.rowCount():
            return self.viewport().height()
        r = self.visualRect(self.model().index(i, 0))
        return r.top() + r.height() // 2


class DisasmPane(QWidget):
    COUNT = 90
    selectionMoved = pyqtSignal(int)

    def __init__(self, cpu: "CpuView"):
        super().__init__()
        self.cpu = cpu
        self.rows: list[A.Ins] = []
        self.pc: int | None = None
        self.taken: bool | None = None
        self.history: list[int] = []
        self.follow_pc = True
        self.reload_from: int | None = None
        self._files: dict[str, list[str]] = {}
        self.table = DisasmTable(self)
        t = self.table
        t.setHorizontalHeaderLabels(["", T("col_address"), T("col_bytes"), T("col_instruction"), T("col_comment")])
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(18)
        t.setFont(mono())
        t.setShowGrid(False)
        t.setWordWrap(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        t.setProperty("i18n_skip_items", True)
        t.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        t.setColumnWidth(0, 44)
        t.setColumnWidth(1, 150)
        t.setColumnWidth(2, 130)
        t.setColumnWidth(3, 260)
        t.horizontalHeader().setStretchLastSection(True)
        t.customContextMenuRequested.connect(self._menu)
        t.currentCellChanged.connect(lambda r, _c, _pr, _pc: self._moved(r))
        t.cellDoubleClicked.connect(self._dclick)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setTextFormat(Qt.TextFormat.RichText)
        self.info.setFont(mono(9))
        self.info.setMinimumHeight(34)
        self.info.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(t, 1)
        lay.addWidget(self.info)

    # ------------------------------------------------------------ fetching
    def refresh(self, snap, gen: int):
        """A stop: keep the current listing when the pc is inside it (stable view), else fetch around the pc."""
        self.pc = snap.pc
        be = self.cpu.backend
        self.taken = None
        if snap.pc is None:
            self.rows = []
            self.render()
            return
        if self.reload_from is not None:            # memory was patched: decode the same range again
            start, keep = self.reload_from, self.current_address()
            self.reload_from = None
            self.fetch(start, gen, select=keep if keep is not None else snap.pc, snap=snap)
            return
        inside = self.rows and any(r.address == snap.pc for r in self.rows[:-8])
        if self.follow_pc and inside:
            self._evaluate_taken(snap)
            self.render(select=snap.pc)
            return
        self.follow_pc = True

        def got_start(start):
            if not self.cpu.gen_ok(gen):
                return
            self.fetch(start, gen, select=snap.pc, snap=snap)
        be.function_start(snap.pc, got_start)

    def fetch(self, start: int, gen: int | None = None, select: int | None = None, snap=None):
        be = self.cpu.backend
        gen = self.cpu.gen if gen is None else gen

        def got(rows):
            if not self.cpu.gen_ok(gen):
                return
            if select is not None and rows and not any(r.address == select for r in rows) and start != select:
                self.fetch(select, gen, select, snap)              # the function start was a guess
                return
            self.rows = rows
            if snap is not None:
                self._evaluate_taken(snap)
            self.render(select=select)
        be.disasm(start, self.COUNT, got, pc=self.pc)

    def goto(self, addr: int, remember: bool = True):
        if remember and self.rows:
            cur = self.current_address()
            if cur is not None:
                self.history.append(cur)
        self.follow_pc = False
        idx = next((i for i, r in enumerate(self.rows[:-8]) if r.address == addr), None)
        if idx is not None:
            self.table.setCurrentCell(idx, 3)
            self.table.scrollToItem(self.table.item(idx, 3), QAbstractItemView.ScrollHint.PositionAtCenter)
            return
        self.fetch(addr, select=addr)

    def back(self):
        if self.history:
            self.goto(self.history.pop(), remember=False)

    def origin(self):
        if self.pc is not None:
            self.follow_pc = True
            self.goto(self.pc, remember=True)

    def _evaluate_taken(self, snap):
        cur = next((r for r in self.rows if r.address == snap.pc), None)
        self.taken = None
        if cur is not None and cur.kind in ("jcc", "loop"):
            self.taken = A.jump_taken(cur.mnemonic, snap.flags, snap.fam, snap.bits)
        elif cur is not None and cur.kind == "jmp":
            self.taken = True

    # ------------------------------------------------------------ showing
    def _source_text(self, path: str, line: int) -> str:
        if path not in self._files:
            try:
                self._files[path] = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                self._files[path] = []
        lines = self._files[path]
        return lines[line - 1].strip() if 0 < line <= len(lines) else ""

    def _source_label(self, path: str, line: int) -> str:
        """The label written on *line* (1-based) or on the label-only lines just above it."""
        key = "labels:" + path
        if key not in self._files:
            names: dict[int, str] = {}
            try:
                from ..index import detect_dialect, parse
                text = Path(path).read_text(encoding="utf-8", errors="replace")
                dia = detect_dialect(path, text, None)
                for s in parse(text, dia).symbols:
                    if s.kind in ("label", "local", "proc"):
                        names[s.line] = s.name
            except Exception:  # noqa: BLE001
                names = {}
            self._files[key] = names               # type: ignore[assignment]
        names = self._files[key]
        lines = self._files.get(path) or []
        if not lines:
            self._source_text(path, line)
            lines = self._files.get(path) or []
        k = line - 1
        if k in names:
            return names[k]
        k -= 1
        while k >= 0:
            if k in names:
                return names[k]
            t = lines[k].strip() if k < len(lines) else ""
            if t and not t.startswith((";", "#", "//")):
                return ""
            k -= 1
        return ""

    def label_of(self, addr: int) -> str:
        be = self.cpu.backend
        user = self.cpu.notes.labels.get(be.static(addr)) if self.cpu.notes else None
        if user:
            return user
        return self.cpu.labels.get(addr, "")

    def ins_text(self, ins) -> str:
        text = ins.text
        if ins.target is not None and ins.kind in ("jmp", "jcc", "loop", "call"):
            name = self.label_of(ins.target) or getattr(ins, "target_name", "")
            if name:
                text = f"{ins.mnemonic} {name}"
        return text

    def auto_comment(self, ins) -> str:
        be = self.cpu.backend
        user = self.cpu.notes.comments.get(be.static(ins.address)) if self.cpu.notes else None
        if user:
            return user
        src = be.source_of(ins.address)
        if src:
            text = self._source_text(*src)
            if text:
                return f"{Path(src[0]).name}:{src[1]}  {text}"
        return self.cpu.auto_comments.get(ins.address, "")

    def render(self, select: int | None = None):
        t = self.table
        c = colors()
        bps = self.cpu.backend.breakpoints() if self.cpu.backend is not None else set()
        t.blockSignals(True)
        t.setRowCount(len(self.rows))
        sel_row = None
        be = self.cpu.backend
        prev_src = None
        for ins in self.rows:                      # names: gdb symbols, call / jump targets, source labels
            sym = getattr(ins, "symbol", "") or ""
            if sym and "+" not in sym and ins.address not in self.cpu.labels:
                self.cpu.labels[ins.address] = sym
            tn = getattr(ins, "target_name", "") or ""
            if ins.target is not None and tn and "+" not in tn and ins.target not in self.cpu.labels:
                self.cpu.labels[ins.target] = tn
            src = be.source_of(ins.address) if be is not None else None
            if src and src != prev_src and ins.address not in self.cpu.labels:
                name = self._source_label(*src)
                if name:
                    self.cpu.labels[ins.address] = name
            prev_src = src
        for i, ins in enumerate(self.rows):
            label = self.label_of(ins.address)
            addr_txt = be_fmt(self.cpu.backend, ins.address) + (f"  {label}" if label else "")
            items = [_item("", ins.address), _item(addr_txt, ins.address), _item(ins.hexbytes, ins.address),
                     _item(self.ins_text(ins), ins.address), _item(self.auto_comment(ins), ins.address)]
            if label:
                f = mono()
                f.setBold(True)
                items[1].setFont(f)
                items[1].setForeground(QBrush(c["label"]))
            if ins.kind == "call":
                items[3].setForeground(QBrush(c["call"]))
            elif ins.kind in ("jmp", "jcc", "loop", "ret"):
                f = mono()
                f.setBold(True)
                items[3].setFont(f)
            items[4].setForeground(QBrush(c["comment"]))
            if ins.address in bps:
                items[1].setBackground(QBrush(c["bp"]))
                items[0].setText("●")
                items[0].setForeground(QBrush(QColor("#e51400")))
            if ins.address == self.pc:
                for k in (0, 2, 3, 4):
                    items[k].setBackground(QBrush(c["pc"]))
                if ins.address not in bps:
                    items[1].setBackground(QBrush(c["pc"]))
                items[0].setText(("●" if ins.address in bps else "") + "➤")
            if ins.address == select:
                sel_row = i
            for k, it in enumerate(items):
                t.setItem(i, k, it)
        t.blockSignals(False)
        if sel_row is not None:
            t.setCurrentCell(sel_row, 3)
            t.scrollToItem(t.item(sel_row, 3), QAbstractItemView.ScrollHint.PositionAtCenter)
        self._moved(t.currentRow())
        t.viewport().update()

    def current(self):
        r = self.table.currentRow()
        return self.rows[r] if 0 <= r < len(self.rows) else None

    def current_address(self) -> int | None:
        ins = self.current()
        return ins.address if ins is not None else None

    def _moved(self, row: int):
        self.table.viewport().update()
        ins = self.rows[row] if 0 <= row < len(self.rows) else None
        self.info.setText(self.cpu.info_for(ins) if ins is not None else "")
        self.info.setToolTip(self.cpu.info_tip(ins) if ins is not None else "")
        if ins is not None:
            self.selectionMoved.emit(ins.address)

    def _dclick(self, row: int, col: int):
        ins = self.rows[row] if 0 <= row < len(self.rows) else None
        if ins is None:
            return
        if col in (0, 1):
            self.cpu.toggle_bp(ins.address)
        elif col == 2:
            self.cpu.binary_edit()
        elif col == 3:
            self.cpu.assemble()
        elif col == 4:
            self.cpu.comment()

    def _menu(self, pos):
        ins = self.current()
        m = QMenu(self)
        cpu = self.cpu
        if ins is not None:
            if ins.target is not None:
                m.addAction(T("m_follow") + "\tEnter", cpu.follow)
            ea = cpu.operand_address(ins)
            if ea is not None or ins.imms:
                m.addAction(T("m_follow_dump"), lambda: cpu.follow_dump_from(ins))
            m.addSeparator()
            m.addAction(T("m_bp") + "\tF2", lambda: cpu.toggle_bp(ins.address))
            m.addAction(T("m_run_cursor") + "\tF4", lambda: cpu.run_to(ins.address))
            m.addAction(T("m_assemble") + "\tSpace", cpu.assemble)
            m.addAction(T("m_binary_edit") + "\tCtrl+E", cpu.binary_edit)
            m.addSeparator()
            m.addAction(T("m_comment") + "\t;", cpu.comment)
            m.addAction(T("m_label") + "\t:", cpu.label)
            src = cpu.backend.source_of(ins.address) if cpu.backend else None
            if src:
                m.addAction(T("m_source"), lambda: cpu.goto_source(*src))
        m.addSeparator()
        m.addAction(T("m_goto") + "\tCtrl+G", cpu.goto_dialog)
        m.addAction(T("m_origin"), self.origin)
        sm = m.addMenu(T("m_search"))
        sm.addAction(T("m_search_cmd"), cpu.search_command)
        sm.addAction(T("m_search_const"), cpu.search_constant)
        sm.addAction(T("m_search_strings"), cpu.search_strings)
        m.addSeparator()
        m.addAction(T("m_step_into") + "\tF7", lambda: cpu.step(False))
        m.addAction(T("m_step_over") + "\tF8", lambda: cpu.step(True))
        m.addAction(T("m_till_return") + "\tCtrl+F9", cpu.till_return)
        m.addAction(T("m_run") + "\tF9", cpu.run)
        m.addSeparator()
        m.addAction(T("m_copy"), self.copy)
        m.exec(self.table.viewport().mapToGlobal(pos))

    def copy(self):
        ins = self.current()
        if ins is not None:
            QApplication.clipboard().setText(f"{be_fmt(self.cpu.backend, ins.address)}  {ins.hexbytes}  "
                                             f"{self.ins_text(ins)}")

    def clear(self):
        self.rows = []
        self.pc = None
        self.taken = None
        self._files.clear()
        self.table.setRowCount(0)
        self.info.setText("")


def be_fmt(be, a: int) -> str:
    return be.fmt(a) if be is not None else f"{a:X}"


# ====================================================================== registers
FLAG_DOC = {
    "CF": ("Carry: unsigned overflow / borrow of the last add / sub; also the bit shifted out.",
           "الحمل: فيضان بدون إشارة أو استلاف في آخر جمع/طرح؛ وأيضاً البت المُزاح للخارج."),
    "PF": ("Parity: the low byte of the result has an even number of 1 bits.",
           "التكافؤ: البايت الأدنى من النتيجة فيه عدد زوجي من البتات 1."),
    "AF": ("Auxiliary carry: carry out of bit 3 (BCD arithmetic).", "الحمل المساعد: حمل من البت 3 (حساب BCD)."),
    "ZF": ("Zero: the result was 0 (after CMP: the two values were equal).",
           "الصفر: النتيجة كانت 0 (بعد CMP: القيمتان متساويتان)."),
    "SF": ("Sign: the top bit of the result (1 = negative as a signed number).",
           "الإشارة: أعلى بت في النتيجة (1 = سالب كرقم بإشارة)."),
    "TF": ("Trap: single-step mode (used by debuggers).", "المصيدة: وضع الخطوة الواحدة (تستخدمه المصححات)."),
    "IF": ("Interrupt enable: hardware interrupts are allowed.", "تمكين المقاطعات: المقاطعات العتادية مسموحة."),
    "DF": ("Direction: string instructions go down (STD) or up (CLD).",
           "الاتجاه: تعليمات النصوص تتحرك للأسفل (STD) أو للأعلى (CLD)."),
    "OF": ("Overflow: signed overflow - the result does not fit as a signed number.",
           "الفيضان: فيضان بإشارة - النتيجة لا تتسع كرقم بإشارة."),
}


class RegistersPane(QWidget):
    def __init__(self, cpu: "CpuView"):
        super().__init__()
        self.cpu = cpu
        self.values: dict[str, int | None] = {}
        self.prev: dict[str, int | None] = {}
        self.snap = None
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.general = _table([T("registers"), T("col_value"), T("col_comment")])
        self.general.setColumnWidth(0, 60)
        self.general.setColumnWidth(1, 150)
        self.general.horizontalHeader().setStretchLastSection(True)
        self.general.cellDoubleClicked.connect(lambda r, _c: self.modify(self._name_at(self.general, r)))
        self.general.customContextMenuRequested.connect(lambda p: self._menu(self.general, p))
        gen_page = QWidget()
        gl = QVBoxLayout(gen_page)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.addWidget(self.general, 1)
        self.flag_buttons: dict[str, QToolButton] = {}
        fl = QHBoxLayout()
        fl.setSpacing(2)
        for name in A.FLAG_ORDER:
            b = QToolButton()
            b.setText(f"{name} 0")
            b.setCheckable(True)
            b.setFont(mono(8))
            b.setToolTip(f"{name}\n" + "\n".join(FLAG_DOC[name]) + "\n\n" + T("flags_hint"))
            b.clicked.connect(lambda _on, n=name: self.toggle_flag(n))
            self.flag_buttons[name] = b
            fl.addWidget(b)
        fl.addStretch(1)
        gl.addLayout(fl)
        self.fpu = _table([T("registers"), T("col_value")])
        self.fpu.horizontalHeader().setStretchLastSection(True)
        self.sse = _table([T("registers"), T("col_value")])
        self.sse.horizontalHeader().setStretchLastSection(True)
        for tb in (self.fpu, self.sse):
            tb.setColumnWidth(0, 70)
            tb.cellDoubleClicked.connect(lambda r, _c, tb=tb: self.modify(self._name_at(tb, r)))
        self.tabs.addTab(gen_page, T("page_general"))
        self.tabs.addTab(self.fpu, T("page_fpu"))
        self.tabs.addTab(self.sse, T("page_sse"))
        self.tabs.currentChanged.connect(lambda i: i > 0 and self.cpu.refresh())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.tabs)

    def extended(self) -> bool:
        return self.tabs.currentIndex() > 0

    def _name_at(self, table, row: int) -> str:
        it = table.item(row, 0)
        return it.text().split()[0].lower() if it is not None and it.text() else ""

    def fill(self, snap, new_stop: bool = True):
        if new_stop:
            self.prev = dict(self.values)
        self.values = dict(snap.regs)
        self.snap = snap
        c = colors()
        width = snap.bits // 4
        general = [n for n in snap.order if snap.groups.get(n) in ("General", "Segments", "Flags")
                   and not n.endswith("_base") and n not in ("fs_base", "gs_base", "k0")]
        g = self.general
        g.setRowCount(len(general))
        for i, n in enumerate(general):
            v = snap.regs.get(n)
            w = 4 if snap.groups.get(n) == "Segments" else (8 if n in ("eflags",) else width)
            if snap.bits == 16:
                w = 4
            text = f"{v:0{w}X}" if isinstance(v, int) else snap.texts.get(n, "")
            name_it = _item(n.upper())
            val_it = _item(text)
            com_it = _item(self.cpu.reg_comment(n, v))
            if n in ("eflags", "flags") and isinstance(v, int):
                com_it.setText(" ".join(f for f in A.FLAG_ORDER if A.flag(v, f)))
            if self.prev and self.prev.get(n) is not None and self.prev.get(n) != v:
                val_it.setForeground(QBrush(c["changed"]))
                name_it.setForeground(QBrush(c["changed"]))
            com_it.setForeground(QBrush(c["comment"]))
            g.setItem(i, 0, name_it)
            g.setItem(i, 1, val_it)
            g.setItem(i, 2, com_it)
        old_flags = self.prev.get("eflags", self.prev.get("flags"))
        for name, b in self.flag_buttons.items():
            bit = A.flag(snap.flags, name)
            b.blockSignals(True)
            b.setChecked(bool(bit))
            b.setText(f"{name} {bit}")
            changed = isinstance(old_flags, int) and A.flag(old_flags, name) != bit
            b.setStyleSheet(f"color: {c['changed'].name()}; font-weight: bold;" if changed else "")
            b.blockSignals(False)
        for table, group in ((self.fpu, "FPU"), (self.sse, "SSE")):
            names = [n for n in snap.order if snap.groups.get(n) == group]
            table.setRowCount(len(names))
            for i, n in enumerate(names):
                v = snap.regs.get(n)
                text = snap.texts.get(n, "") if group == "FPU" or not isinstance(v, int) else f"{v:032X}"
                if group == "SSE" and isinstance(v, int):
                    text = " ".join(text[k:k + 8] for k in range(0, 32, 8))
                ni, vi = _item(n.upper()), _item(text)
                if self.prev and self.prev.get(n) is not None and self.prev.get(n) != v:
                    vi.setForeground(QBrush(c["changed"]))
                table.setItem(i, 0, ni)
                table.setItem(i, 1, vi)

    def changed(self) -> set[str]:
        return {n for n, v in self.values.items() if n in self.prev and self.prev[n] != v}

    def toggle_flag(self, name: str):
        if self.snap is None:
            return
        reg = "eflags" if "eflags" in self.values else "flags"
        v = self.snap.flags ^ (1 << A.FLAG_BITS[name])
        self.cpu.set_register(reg, v)

    def modify(self, name: str):
        if not name or self.snap is None:
            return
        v = self.values.get(name)
        text, ok = QInputDialog.getText(self, T("m_modify"), T("modify_reg", reg=name.upper()),
                                        QLineEdit.EchoMode.Normal, f"0x{v:X}" if isinstance(v, int) else "")
        if not ok:
            return
        n = parse_number(text)
        if n is None:
            self.cpu.explain(T("err_value", text=text), "")
            return
        self.cpu.set_register(name, n)

    def _menu(self, table, pos):
        row = table.rowAt(pos.y())
        name = self._name_at(table, row) if row >= 0 else ""
        v = self.values.get(name)
        m = QMenu(self)
        if name:
            m.addAction(T("m_modify"), lambda: self.modify(name))
            if isinstance(v, int):
                m.addAction(T("m_increment"), lambda: self.cpu.set_register(name, v + 1))
                m.addAction(T("m_decrement"), lambda: self.cpu.set_register(name, v - 1))
                m.addAction(T("m_zero"), lambda: self.cpu.set_register(name, 0))
                m.addSeparator()
                m.addAction(T("m_follow_dump"), lambda: self.cpu.dump.goto(self.cpu.reg_linear(name, v)))
                m.addAction(T("m_follow_disasm"), lambda: self.cpu.disasm.goto(self.cpu.reg_linear(name, v)))
                m.addAction(T("m_follow_stack"), lambda: self.cpu.stack.select(self.cpu.reg_linear(name, v)))
        m.exec(table.viewport().mapToGlobal(pos))

    def clear(self):
        for tb in (self.general, self.fpu, self.sse):
            tb.setRowCount(0)
        self.values, self.prev, self.snap = {}, {}, None


# ====================================================================== dump
class DumpPane(QWidget):
    ROWS = 16

    def __init__(self, cpu: "CpuView"):
        super().__init__()
        self.cpu = cpu
        self.base: int | None = None
        self.data = b""
        self.prev: dict[int, int] = {}
        self._filling = False
        self.table = _table([T("col_address")] + [f"{i:02X}" for i in range(16)] + [T("col_ascii")])
        t = self.table
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        t.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        t.setColumnWidth(0, 130)
        for i in range(1, 17):
            t.setColumnWidth(i, 24)
        t.horizontalHeader().setStretchLastSection(True)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        t.itemChanged.connect(self._edited)
        t.customContextMenuRequested.connect(self._menu)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(t)

    def goto(self, addr: int | None):
        if addr is None:
            return
        self.base = int(addr)
        self.refresh(self.cpu.gen, keep_prev=False)

    def refresh(self, gen: int, keep_prev: bool = True):
        be = self.cpu.backend
        if be is None or self.base is None:
            return
        base = self.base

        def got(data):
            if not self.cpu.gen_ok(gen) or base != self.base:
                return
            if keep_prev and self.data:
                self.prev = {self._base_of_data + i: b for i, b in enumerate(self.data)}
            elif not keep_prev:
                self.prev = {}
            self._base_of_data = base
            self.data = data
            self.render()
        be.read(base, self.ROWS * 16, got)

    _base_of_data = 0

    def render(self):
        t = self.table
        c = colors()
        self._filling = True
        t.setRowCount(self.ROWS)
        be = self.cpu.backend
        for r in range(self.ROWS):
            a = self.base + 16 * r
            t.setItem(r, 0, _item(be_fmt(be, a), a))
            chars = []
            for k in range(16):
                i = 16 * r + k
                if i < len(self.data):
                    b = self.data[i]
                    it = _item(f"{b:02X}", a + k, editable=True)
                    old = self.prev.get(a + k)
                    if old is not None and old != b:
                        it.setForeground(QBrush(c["changed"]))
                    chars.append(chr(b) if 32 <= b < 127 else ".")
                else:
                    it = _item("??", a + k)
                    chars.append(" ")
                t.setItem(r, k + 1, it)
            t.setItem(r, 17, _item("".join(chars), a))
        self._filling = False

    def _edited(self, it):
        if self._filling or it.column() < 1 or it.column() > 16:
            return
        a = it.data(ROLE_ADDR)
        v = parse_number(it.text().strip())
        if a is None or v is None or not 0 <= v <= 255:
            self.cpu.explain(T("err_hex", text=it.text()), "")
            self.render()
            return
        self.cpu.write_bytes(int(a), bytes([v]))

    def selected_address(self) -> int | None:
        it = self.table.currentItem()
        a = it.data(ROLE_ADDR) if it is not None else None
        return int(a) if a is not None else self.base

    def _menu(self, pos):
        m = QMenu(self)
        a = self.selected_address()
        m.addAction(T("m_goto") + "\tCtrl+G", lambda: self.cpu.goto_dialog(target="dump"))
        if a is not None:
            m.addAction(T("m_edit_bytes"), lambda: self.cpu.binary_edit(a))
            m.addAction(T("m_follow_disasm"), lambda: self.cpu.disasm.goto(a))
        m.exec(self.table.viewport().mapToGlobal(pos))

    def page(self, n: int):
        if self.base is not None:
            self.base = max(0, self.base + n * 16 * self.ROWS)
            self.refresh(self.cpu.gen, keep_prev=False)

    def clear(self):
        self.table.setRowCount(0)
        self.data, self.prev = b"", {}


# ====================================================================== stack
class StackPane(QWidget):
    ABOVE = 3
    ROWS = 28

    def __init__(self, cpu: "CpuView"):
        super().__init__()
        self.cpu = cpu
        self.rows: list[tuple[int, int]] = []          # (address, value)
        self.comments: dict[int, str] = {}
        self.sp: int | None = None
        self.table = _table([T("col_address"), T("col_value"), T("col_comment")])
        t = self.table
        t.setColumnWidth(0, 140)
        t.setColumnWidth(1, 140)
        t.horizontalHeader().setStretchLastSection(True)
        t.cellDoubleClicked.connect(self._dclick)
        t.customContextMenuRequested.connect(self._menu)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(t)

    def refresh(self, snap, gen: int):
        be = self.cpu.backend
        if snap.sp is None:
            self.clear()
            return
        ptr = 2 if snap.bits == 16 else snap.bits // 8
        self.sp, self.bp = snap.sp, snap.bp
        start = snap.sp - self.ABOVE * ptr

        def got(data):
            if not self.cpu.gen_ok(gen):
                return
            self.rows = []
            for i in range(0, len(data) - ptr + 1, ptr):
                self.rows.append((start + i, int.from_bytes(data[i:i + ptr], "little")))
            self.comments = {}
            self.render()
            self._annotate(snap, gen, ptr)
        be.read(start, self.ROWS * ptr, got)

    def _annotate(self, snap, gen, ptr):
        be = self.cpu.backend
        code_seg = (snap.segs.get("cs", 0) << 4) if snap.bits == 16 else 0
        data_seg = (snap.segs.get("ds", 0) << 4) if snap.bits == 16 else 0
        for a, v in self.rows:
            if a < snap.sp:
                continue
            if snap.bits == 16:
                cands = [(code_seg + v, True), (data_seg + v, False)]
            else:
                if v < 0x10000:
                    continue
                cands = [(v, True)]
            for target, as_code in cands:
                def got(data, a=a, target=target, as_code=as_code):
                    if not self.cpu.gen_ok(gen) or a in self.comments or len(data) < 9:
                        return
                    before, at = data[:8], data[8:]
                    if as_code and A.is_return_address(before, snap.bits):
                        def named(name, a=a, target=target):
                            if not self.cpu.gen_ok(gen):
                                return
                            where = name or self.cpu.disasm.label_of(target) or be_fmt(be, target)
                            src = be.source_of(target - 1) or be.source_of(target)
                            if src:
                                where += f"  ({Path(src[0]).name}:{src[1]})"
                            self.comments[a] = T("return_to", where=where)
                            self.render()
                        be.symbol(target, named)
                        return
                    s = A.string_at(at)
                    if s is not None and not (snap.bits == 16 and as_code):
                        self.comments[a] = f'{s[0]} "{A.esc(s[1])}"'
                        self.render()
                be.read(target - 8, 48, got)

    def render(self):
        t = self.table
        c = colors()
        be = self.cpu.backend
        t.setRowCount(len(self.rows))
        width = 4 if be is not None and be.bits == 16 else (be.bits // 4 if be is not None else 16)
        sel = None
        for i, (a, v) in enumerate(self.rows):
            items = [_item(be_fmt(be, a), a), _item(f"{v:0{width}X}", a), _item(self.comments.get(a, ""), a)]
            if a == self.sp:
                for it in items:
                    it.setBackground(QBrush(c["sp"]))
                items[0].setText("➤ " + items[0].text())
                sel = i
            elif a == getattr(self, "bp", None):
                items[0].setText("BP " + items[0].text())
            if a < (self.sp or 0):
                for it in items:
                    it.setForeground(QBrush(c["muted"]))
            items[2].setForeground(QBrush(c["comment"]))
            for k, it in enumerate(items):
                t.setItem(i, k, it)
        if sel is not None and t.currentRow() < 0:
            t.scrollToItem(t.item(sel, 0), QAbstractItemView.ScrollHint.PositionAtTop)

    def value_at_row(self, row: int):
        return self.rows[row] if 0 <= row < len(self.rows) else None

    def select(self, addr: int | None):
        if addr is None:
            return
        for i, (a, _v) in enumerate(self.rows):
            if a <= addr < a + max(2, self.cpu.backend.bits // 8 if self.cpu.backend else 8):
                self.table.setCurrentCell(i, 0)
                return

    def _dclick(self, row, _col):
        rv = self.value_at_row(row)
        if rv is not None:
            self.cpu.dump.goto(self.cpu.stack_value_linear(rv[1]))

    def _menu(self, pos):
        row = self.table.rowAt(pos.y())
        rv = self.value_at_row(row)
        m = QMenu(self)
        if rv is not None:
            a, v = rv
            lin = self.cpu.stack_value_linear(v)
            m.addAction(T("m_follow_dump"), lambda: self.cpu.dump.goto(lin))
            m.addAction(T("m_follow_disasm"), lambda: self.cpu.disasm.goto(self.cpu.stack_value_linear(v, code=True)))
            m.addAction(T("m_modify"), lambda: self.cpu.modify_stack(a, v))
        m.exec(self.table.viewport().mapToGlobal(pos))

    def clear(self):
        self.rows, self.comments, self.sp = [], {}, None
        self.table.setRowCount(0)


# ====================================================================== assemble dialog
class AssembleDialog(QDialog):
    def __init__(self, parent, addr_text: str, current: str):
        super().__init__(parent)
        self.setWindowTitle(T("assemble_title", addr=addr_text))
        self.edit = QLineEdit(current)
        self.edit.setFont(mono(10))
        self.edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.fill = QCheckBox(T("assemble_fill"))
        self.fill.setChecked(True)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(T("assemble_prompt")))
        lay.addWidget(self.edit)
        lay.addWidget(self.fill)
        lay.addWidget(bb)
        self.resize(460, 120)


class ResultsDialog(QDialog):
    def __init__(self, cpu, title: str, rows: list[tuple[int, str, str]]):
        super().__init__(cpu)
        self.cpu = cpu
        self.setWindowTitle(T("search_results", what=title))
        self.list = QListWidget()
        self.list.setFont(mono())
        self.list.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        for a, text, comment in rows:
            it = QListWidgetItem(f"{be_fmt(cpu.backend, a)}  {text}" + (f"    ; {comment}" if comment else ""))
            it.setData(ROLE_ADDR, a)
            self.list.addItem(it)
        self.list.itemActivated.connect(self._go)
        self.list.itemDoubleClicked.connect(self._go)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(T("found_n", n=len(rows))))
        lay.addWidget(self.list)
        self.resize(640, 380)

    def _go(self, it):
        a = it.data(ROLE_ADDR)
        if a is not None:
            self.cpu.disasm.goto(int(a))


# ====================================================================== the view
class CpuView(QWidget):
    """Four panes on one backend; ``attach(backend)`` at a stop, ``refresh()`` re-reads everything."""
    refreshed = pyqtSignal()
    KEYS = {"F2", "F4", "F7", "F8", "F9", "Ctrl+F9", "Ctrl+G", "Space", ";", ":", "Ctrl+E", "Return", "Enter", "-",
            "*", "PgUp", "PgDown", "Shift+;"}

    def __init__(self, win=None, parent=None):
        super().__init__(parent)
        self.win = win
        self.backend = None
        self.notes: CpuNotes | None = None
        self.snap = None
        self.gen = 0
        self.refresh_count = 0
        self.labels: dict[int, str] = {}
        self.auto_comments: dict[int, str] = {}
        self.last_message = ""
        self.setProperty("i18n_skip_items", True)
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.title = QLabel(T("cpu"))
        f = self.title.font()
        f.setBold(True)
        self.title.setFont(f)
        bar = QHBoxLayout()
        bar.setContentsMargins(2, 2, 2, 0)
        bar.addWidget(self.title, 1)
        self.buttons = {}
        for key, text, fn in (("run", T("m_run") + " (F9)", self.run),
                              ("into", T("m_step_into") + " (F7)", lambda: self.step(False)),
                              ("over", T("m_step_over") + " (F8)", lambda: self.step(True)),
                              ("ret", T("m_till_return") + " (Ctrl+F9)", self.till_return),
                              ("goto", "Ctrl+G", lambda: self.goto_dialog()),
                              ("origin", "*", lambda: self.disasm.origin())):
            b = QPushButton(text)
            b.setAutoDefault(False)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(fn)
            self.buttons[key] = b
            bar.addWidget(b)
        self.note = QLabel(T("not_running"))
        self.note.setWordWrap(True)
        self.disasm = DisasmPane(self)
        self.regs = RegistersPane(self)
        self.dump = DumpPane(self)
        self.stack = StackPane(self)
        top = QSplitter(Qt.Orientation.Horizontal)
        top.addWidget(self.disasm)
        top.addWidget(self.regs)
        top.setStretchFactor(0, 3)
        top.setStretchFactor(1, 2)
        bottom = QSplitter(Qt.Orientation.Horizontal)
        bottom.addWidget(self.dump)
        bottom.addWidget(self.stack)
        bottom.setStretchFactor(0, 3)
        bottom.setStretchFactor(1, 2)
        self.split = QSplitter(Qt.Orientation.Vertical)
        self.split.addWidget(top)
        self.split.addWidget(bottom)
        self.split.setStretchFactor(0, 3)
        self.split.setStretchFactor(1, 2)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addLayout(bar)
        lay.addWidget(self.note)
        lay.addWidget(self.split, 1)
        for w in (self.disasm.table, self.regs.general, self.regs.fpu, self.regs.sse, self.dump.table,
                  self.stack.table):
            w.installEventFilter(self)
        self._set_enabled(False)

    # ------------------------------------------------------------ state
    def gen_ok(self, gen: int) -> bool:
        return gen == self.gen

    def _set_enabled(self, on: bool):
        self.note.setVisible(not on)
        self.split.setEnabled(on)
        for b in self.buttons.values():
            b.setEnabled(on)

    def attach(self, backend):
        if backend is not self.backend:
            self.backend = backend
            self.labels = dict(backend.labels()) if hasattr(backend, "labels") else {}
            self.auto_comments = {}
            self.disasm.rows = []
            self.disasm.history = []
            self.dump.base = None
            name, path = backend.program_key()
            self.notes = CpuNotes(notes_path(self.win, path), name)
        self._set_enabled(True)

    def refresh(self, new_stop: bool = False):
        be = self.backend
        if be is None or not be.alive():
            return
        self.gen += 1
        gen = self.gen

        def got(snap):
            if not self.gen_ok(gen) or snap is None:
                return
            self.snap = snap
            self.title.setText(T("cpu_title", where=f"{be_fmt(be, snap.pc)}" if snap.pc is not None else "?")
                               + ("  -  8086" if be.kind == "emu8086" else f"  -  x86-{snap.bits}"))
            self.regs.fill(snap, new_stop)
            self.disasm.table.setColumnWidth(1, 160 if snap.bits == 16 else 240)
            self.disasm.refresh(snap, gen)
            if self.dump.base is None:
                self.dump.base = self.initial_dump_address(snap)
            self.dump.refresh(gen)
            self.stack.refresh(snap, gen)
            self.refresh_count += 1
            self.refreshed.emit()
        be.snapshot(got, self.regs.extended())

    def initial_dump_address(self, snap) -> int | None:
        if self.backend.kind == "emu8086":
            return (snap.segs.get("ds", 0) << 4)
        return snap.sp

    def stale(self):
        self.gen += 1
        self.title.setText(T("cpu") + "  -  " + T("running"))
        self.disasm.pc = None
        self.disasm.table.viewport().update()

    def clear(self):
        self.gen += 1
        self.backend = None
        self.snap = None
        for p in (self.disasm, self.regs, self.dump, self.stack):
            p.clear()
        self.title.setText(T("cpu"))
        self._set_enabled(False)

    # ------------------------------------------------------------ helpers for the panes
    def reg_comment(self, name: str, v) -> str:
        if not isinstance(v, int) or self.backend is None:
            return ""
        lin = self.reg_linear(name, v)
        label = self.disasm.label_of(lin) if lin is not None else ""
        return f"<{label}>" if label else ""

    def reg_linear(self, name: str, v: int) -> int:
        """A register value as an address (16-bit: in its natural segment)."""
        if self.backend is None or self.backend.bits != 16 or self.snap is None:
            return v
        segs = self.snap.segs
        seg = {"ip": "cs", "sp": "ss", "bp": "ss"}.get(name, "ds")
        return ((segs.get(seg, 0) << 4) + (v & 0xFFFF)) & 0xFFFFF

    def stack_value_linear(self, v: int, code: bool = False) -> int:
        if self.backend is None or self.backend.bits != 16 or self.snap is None:
            return v
        return ((self.snap.segs.get("cs" if code else "ds", 0) << 4) + v) & 0xFFFFF

    def operand_address(self, ins) -> int | None:
        if self.snap is None or ins is None:
            return None
        return A.effective_address(ins, self.snap.fam, self.snap.bits, self.snap.segs)

    def info_for(self, ins) -> str:
        """The OllyDbg info line under the disassembly (rich text)."""
        import html
        if ins is None or self.snap is None:
            return ""
        parts = []
        snap = self.snap
        if ins.address == snap.pc and ins.kind in ("jcc", "loop"):
            taken = A.jump_taken(ins.mnemonic, snap.flags, snap.fam, snap.bits)
            color = colors()["taken"].name() if taken else colors()["muted"].name()
            parts.append(f"<b style='color:{color}'>{T('jump_taken') if taken else T('jump_not_taken')}</b>")
            parts.append(html.escape(self.jump_reason(ins)))
        if ins.target is not None and ins.kind in ("jmp", "jcc", "loop", "call"):
            name = self.disasm.label_of(ins.target) or getattr(ins, "target_name", "")
            parts.append(f"{T('dest')}: {be_fmt(self.backend, ins.target)}" + (f" &lt;{html.escape(name)}&gt;"
                                                                             if name else ""))
        ea = self.operand_address(ins) if ins.address == snap.pc or not any(
            m[1] or m[2] for m in ins.mems) else None
        if ea is not None:
            parts.append(f"{T('ea')}: {be_fmt(self.backend, ea)}")
        return "  |  ".join(parts)

    def info_tip(self, ins) -> str:
        if ins is None or self.snap is None or ins.kind not in ("jcc", "loop"):
            return ""
        return self.jump_reason(ins, both_langs=True)

    def jump_reason(self, ins, both_langs: bool = False) -> str:
        snap = self.snap
        mn = ins.mnemonic
        tr = both if both_langs else T
        if ins.kind == "loop":
            cx = {16: "CX", 32: "ECX"}.get(snap.bits, "RCX")
            v = snap.fam.get("rcx", 0) & ((1 << snap.bits) - 1)
            return tr("loop_why", mn=mn.upper(), cx=cx, value=v, after=(v - 1) & ((1 << snap.bits) - 1))
        cond = A.condition_text(mn)
        fl = [f for c, _d, fs, _a in A.isa.CONDITIONS if c == A.condition_of(mn) for f in fs.split()]
        flags = " ".join(f"{f}={A.flag(snap.flags, f)}" for f in fl)
        return tr("jump_why", mn=mn.upper(), cond=cond, flags=flags)

    def explain(self, message: str, why: str):
        """Errors of the view: a status message + a box with the reason and how to fix it."""
        self.last_message = message
        if self.win is not None and hasattr(self.win, "statusBar"):
            self.win.statusBar().showMessage(message.splitlines()[0], 8000)
        box = QMessageBox(QMessageBox.Icon.Warning, T("cpu"), message, QMessageBox.StandardButton.Ok, self)
        if why:
            box.setInformativeText(why)
        box.setModal(False)
        box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        box.show()
        QTimer.singleShot(15000, lambda: _close_quietly(box))

    def status(self, message: str):
        self.last_message = message
        if self.win is not None and hasattr(self.win, "statusBar"):
            self.win.statusBar().showMessage(message, 5000)

    # ------------------------------------------------------------ commands
    def _ok(self) -> bool:
        return self.backend is not None and self.backend.alive()

    def step(self, over: bool):
        if self._ok():
            self.backend.step(over)

    def run(self):
        if self._ok():
            self.backend.cont()

    def till_return(self):
        if self._ok():
            if self.backend.kind == "native":
                self.status(T("till_return_note"))
            self.backend.till_return()

    def run_to(self, addr: int | None = None):
        addr = self.disasm.current_address() if addr is None else addr
        if self._ok() and addr is not None:
            self.backend.run_to(addr)

    def toggle_bp(self, addr: int | None = None):
        addr = self.disasm.current_address() if addr is None else addr
        if self.backend is None or addr is None:
            return
        on = self.backend.toggle_bp(addr)
        if on is not None:
            self.status(T("bp_set" if on else "bp_removed", addr=be_fmt(self.backend, addr)))
        self.disasm.render(select=addr)

    def follow(self):
        ins = self.disasm.current()
        if ins is not None and ins.target is not None:
            self.disasm.goto(ins.target)
        elif ins is not None:
            self.follow_dump_from(ins)

    def follow_dump_from(self, ins):
        ea = self.operand_address(ins)
        if ea is None and ins.imms:
            ea = self.stack_value_linear(ins.imms[-1]) if self.backend.bits == 16 else ins.imms[-1]
        if ea is not None:
            self.dump.goto(ea)

    def set_register(self, name: str, value: int):
        if not self._ok():
            return
        bits = self.snap.bits if self.snap else 64
        value &= (1 << (16 if bits == 16 else 64)) - 1

        def done(ok, msg):
            if not ok:
                self.explain(T("err_write", addr=name.upper(), err=msg), "")
            self.refresh()
        self.backend.set_reg(name, value, done)

    def write_bytes(self, addr: int, data: bytes, then=None):
        if not self._ok():
            return

        def done(ok, msg):
            if not ok:
                self.explain(T("err_write", addr=be_fmt(self.backend, addr), err=msg or "?"), T("err_write_why"))
            else:
                self.status(T("patched", n=len(data), addr=be_fmt(self.backend, addr)))
                rows = self.disasm.rows
                if rows and rows[0].address <= addr <= rows[-1].address + 16:
                    self.disasm.reload_from = rows[0].address
            if then:
                then(ok)
            self.refresh()
        self.backend.write(addr, data, done)

    def modify_stack(self, addr: int, v: int):
        text, ok = QInputDialog.getText(self, T("m_modify"), T("modify_reg", reg=be_fmt(self.backend, addr)),
                                        QLineEdit.EchoMode.Normal, f"0x{v:X}")
        n = parse_number(text) if ok else None
        if ok and n is None:
            self.explain(T("err_value", text=text), "")
        if n is not None:
            size = 2 if self.backend.bits == 16 else self.backend.bits // 8
            self.write_bytes(addr, (n & ((1 << (8 * size)) - 1)).to_bytes(size, "little"))

    def goto_dialog(self, target: str = "disasm", expr: str | None = None):
        if not self._ok():
            return
        if expr is None:
            expr, ok = QInputDialog.getText(self, T("goto_title"), T("goto_prompt"))
            if not ok or not expr.strip():
                return
        self.goto_expression(expr, target)

    def goto_expression(self, expr: str, target: str = "disasm"):
        labels = {self.backend.dynamic(a): n for a, n in (self.notes.labels.items() if self.notes else [])}
        labels.update({a: n for a, n in self.labels.items() if n})

        def got(addr, err):
            if addr is None:
                self.explain(T("err_expr", expr=expr, err=err or "?"), T("err_expr_why"))
                return
            if target == "dump":
                self.dump.goto(addr)
            else:
                self.disasm.goto(addr)
        self.backend.eval(expr.strip(), got, labels)

    def assemble(self, text: str | None = None, fill: bool = True) -> bool:
        ins = self.disasm.current()
        if ins is None or not self._ok():
            return False
        if text is None:
            dlg = AssembleDialog(self, be_fmt(self.backend, ins.address), ins.text)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return False
            text, fill = dlg.edit.text(), dlg.fill.isChecked()
        code, err = self.backend.assemble(text, ins.address)
        if code is None:
            self.explain(T("err_assemble", err=err), T("err_assemble_why"))
            return False
        if len(code) > ins.size:
            if QMessageBox.question(self, T("cpu"), T("err_assemble_longer", new=len(code), old=ins.size)) \
                    != QMessageBox.StandardButton.Yes:
                return False
        elif fill and len(code) < ins.size:
            code += b"\x90" * (ins.size - len(code))
        self.write_bytes(ins.address, code)
        return True

    def binary_edit(self, addr: int | None = None, text: str | None = None) -> bool:
        if not self._ok():
            return False
        ins = self.disasm.current()
        if addr is None:
            if ins is None:
                return False
            addr, current = ins.address, ins.hexbytes
        else:
            current = ""
        if text is None:
            text, ok = QInputDialog.getText(self, T("binary_title", addr=be_fmt(self.backend, addr)),
                                            T("binary_prompt"), QLineEdit.EchoMode.Normal, current)
            if not ok:
                return False
        clean = re.sub(r"[\s,]", "", text)
        if not clean or len(clean) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", clean):
            self.explain(T("err_hex", text=text), "")
            return False
        self.write_bytes(addr, bytes.fromhex(clean))
        return True

    def comment(self, text: str | None = None, addr: int | None = None):
        addr = self.disasm.current_address() if addr is None else addr
        if addr is None or self.notes is None:
            return
        st = self.backend.static(addr)
        if text is None:
            text, ok = QInputDialog.getText(self, T("comment_title", addr=be_fmt(self.backend, addr)), T("m_comment"),
                                            QLineEdit.EchoMode.Normal, self.notes.comments.get(st, ""))
            if not ok:
                return
        self.notes.set_comment(st, text)
        self.disasm.render(select=addr)

    def label(self, text: str | None = None, addr: int | None = None):
        addr = self.disasm.current_address() if addr is None else addr
        if addr is None or self.notes is None:
            return
        st = self.backend.static(addr)
        if text is None:
            text, ok = QInputDialog.getText(self, T("label_title", addr=be_fmt(self.backend, addr)), T("m_label"),
                                            QLineEdit.EchoMode.Normal, self.notes.labels.get(st, ""))
            if not ok:
                return
        self.notes.set_label(st, re.sub(r"\s+", "_", text.strip()))
        self.disasm.render(select=addr)

    def goto_source(self, path: str, line: int):
        win = self.win
        if win is None:
            return
        ed = None
        try:
            ed = win._editor_for_file(path)
        except Exception:  # noqa: BLE001
            ed = None
        if ed is not None:
            ed.goto_line(int(line) - 1)

    # -- search
    def _search_region(self, cb):
        """cb(list of Ins) over the code around the current function (a few thousand bytes)."""
        be = self.backend
        start = self.disasm.rows[0].address if self.disasm.rows else (self.snap.pc if self.snap else 0)
        if be.kind == "emu8086" and be.s.program is not None and be.s.program.addr_line:
            start = min(be.s.program.addr_line)
        be.disasm(start, 1500, cb)

    def search_command(self, pattern: str | None = None, show: bool = True):
        if not self._ok():
            return None
        if pattern is None:
            pattern, ok = QInputDialog.getText(self, T("m_search"), T("search_cmd_prompt"))
            if not ok or not pattern.strip():
                return None
        try:
            rx = re.compile(pattern.strip(), re.I)
        except re.error:
            rx = re.compile(re.escape(pattern.strip()), re.I)
        out = []

        def got(rows):
            out[:] = [(i.address, self.disasm.ins_text(i), "") for i in rows if rx.search(i.text)
                      or rx.search(self.disasm.ins_text(i))]
            if show:
                ResultsDialog(self, pattern, out).show()
        self._search_region(got)
        return out

    def search_constant(self, value: int | None = None, show: bool = True):
        if not self._ok():
            return None
        if value is None:
            text, ok = QInputDialog.getText(self, T("m_search"), T("search_const_prompt"))
            value = parse_number(text) if ok else None
            if value is None:
                return None
        out = []

        def got(rows):
            out[:] = [(i.address, self.disasm.ins_text(i), "") for i in rows
                      if value in i.imms or any(m[4] == value for m in i.mems)]
            if show:
                ResultsDialog(self, hex(value), out).show()
        self._search_region(got)
        return out

    def search_strings(self, show: bool = True, done=None):
        if not self._ok():
            return None
        be = self.backend
        out: list = []

        def got(rows):
            cands = []
            for i in rows:
                a = None
                if i.mems and i.mems[0][1] in ("rip", "eip") and not i.mems[0][2]:
                    a = i.rip_next + i.mems[0][4]
                elif be.bits == 16 and i.imms and i.mnemonic == "mov":
                    a = self.stack_value_linear(i.imms[-1])
                elif i.imms and i.imms[-1] >= 0x10000:
                    a = i.imms[-1]
                if a is not None:
                    cands.append((i, a))
            if not cands:
                if show:
                    ResultsDialog(self, T("m_search_strings"), []).show()
                if done:
                    done(out)
                return
            pending = {"n": len(cands)}

            def one(i, a, data):
                s = A.string_at(data)
                if s is not None:
                    out.append((i.address, self.disasm.ins_text(i), f'{s[0]} "{A.esc(s[1], 60)}"'))
                    self.auto_comments[i.address] = f'{s[0]} "{A.esc(s[1])}"'
                pending["n"] -= 1
                if pending["n"] == 0:
                    out.sort()
                    self.disasm.render(select=self.disasm.current_address())
                    if show:
                        ResultsDialog(self, T("m_search_strings"), out).show()
                    if done:
                        done(out)
            for i, a in cands:
                be.read(a, 64, lambda data, i=i, a=a: one(i, a, data))
        self._search_region(got)
        return out

    # ------------------------------------------------------------ keys (only while the view has the focus)
    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            seq = QKeySequence(ev.keyCombination()).toString()
            text = ev.text()
            if seq in self.KEYS or text in (";", ":", "*", "-"):
                if isinstance(obj, QTableWidget) and obj.state() == QAbstractItemView.State.EditingState:
                    return False
                if t == QEvent.Type.ShortcutOverride:
                    ev.accept()
                    return True
                return self.handle_key(obj, seq, text)
        return super().eventFilter(obj, ev)

    def handle_key(self, obj, seq: str, text: str = "") -> bool:
        in_disasm = obj is self.disasm.table
        if seq == "F7":
            self.step(False)
        elif seq == "F8":
            self.step(True)
        elif seq == "F9":
            self.run()
        elif seq == "Ctrl+F9":
            self.till_return()
        elif seq == "Ctrl+G":
            self.goto_dialog(target="dump" if obj is self.dump.table else "disasm")
        elif seq == "F2" and in_disasm:
            self.toggle_bp()
        elif seq == "F4" and in_disasm:
            self.run_to()
        elif seq == "Space" and in_disasm:
            self.assemble()
        elif seq == "Ctrl+E" and in_disasm:
            self.binary_edit()
        elif seq == "Ctrl+E" and obj is self.dump.table:
            self.binary_edit(self.dump.selected_address())
        elif text == ";" and in_disasm:
            self.comment()
        elif text == ":" and in_disasm:
            self.label()
        elif seq in ("Return", "Enter") and in_disasm:
            self.follow()
        elif text == "-" and in_disasm:
            self.disasm.back()
        elif text == "*" and in_disasm:
            self.disasm.origin()
        elif seq == "PgDown" and obj is self.dump.table:
            self.dump.page(1)
        elif seq == "PgUp" and obj is self.dump.table:
            self.dump.page(-1)
        else:
            return False
        return True


def _close_quietly(w):
    try:
        w.close()
    except RuntimeError:
        pass


__all__ = ["CpuView", "DisasmPane", "RegistersPane", "DumpPane", "StackPane"]
