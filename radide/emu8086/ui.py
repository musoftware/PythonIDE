"""Qt side of the 8086 emulator: the text screen, the debugger panels and the IDE run / debug session.

    Emu8086Panel     the "8086 Emulator" dock: screen + toolbar (run, pause, step, step over, step back,
                     reset, speed, Export .COM / .EXE for DOSBox) + Registers / Flags, Memory, Stack,
                     Variables and Listing views
    Emu8086Session   what MainWindow._make_session returns for an "8086 Assembly (Emulator)" project: it
                     speaks the IDE's Session interface (output / stopped / resumed / finished signals, cont,
                     step_into / step_over / step_out, set_breakpoint, evaluate, watch, children) and runs the
                     Machine in slices from a QTimer, so the IDE stays responsive.
"""
from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import QObject, QRect, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QImage, QPainter
from PyQt6.QtWidgets import (QCheckBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPlainTextEdit, QPushButton, QSizePolicy, QSlider, QSplitter, QTabWidget,
                             QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .cpu import FLAG_NAMES
from .machine import CGA, COLS, ROWS, TEXT_BASE, Machine
from .messages import ui_language

MONO = "Consolas"


def _hex(v: int, digits: int = 4) -> str:
    return f"{v:0{digits}X}"


# ============================================================================ screen
class ScreenWidget(QWidget):
    """80x25 colour text screen (or 320x200 mode 13h) of a Machine. Keys typed here go to the program."""

    keyTyped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.machine: Machine | None = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setProperty("i18n_skip", True)
        self.font_ = QFont(MONO, 11)
        self.font_.setStyleHint(QFont.StyleHint.Monospace)
        fm = QFontMetrics(self.font_)
        self.cw = max(7, fm.horizontalAdvance("W"))
        self.ch = max(12, fm.height())
        self.ascent = fm.ascent()
        self.setMinimumSize(COLS * 5, ROWS * 8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._blink = True
        self._last = None
        self._timer = QTimer(self, interval=60)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._blink_count = 0
        self.setToolTip("Click here and type: the keys go to the program")

    def sizeHint(self) -> QSize:
        return QSize(COLS * self.cw + 8, ROWS * self.ch + 8)

    def set_machine(self, m: Machine | None) -> None:
        self.machine = m
        self._last = None
        self.update()

    def _tick(self) -> None:
        self._blink_count += 1
        if self._blink_count % 8 == 0:
            self._blink = not self._blink
            self.update()
            return
        m = self.machine
        if m is None or not m.cpu.video_dirty and self._last == (tuple(m.cursor), m.video_mode):
            return
        m.cpu.video_dirty = False
        self._last = (tuple(m.cursor), m.video_mode)
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(40, 40, 40))           # around the 80x25 monitor area
        m = self.machine
        if m is None:
            p.end()
            return
        if m.video_mode == 0x13:
            self._paint_gfx(p, m)
            p.end()
            return
        # scale the 80x25 grid into the widget
        sx = self.width() / (COLS * self.cw)
        sy = self.height() / (ROWS * self.ch)
        s = min(sx, sy)
        p.translate((self.width() - COLS * self.cw * s) / 2, (self.height() - ROWS * self.ch * s) / 2)
        p.scale(s, s)
        p.fillRect(QRect(0, 0, COLS * self.cw, ROWS * self.ch), QColor(0, 0, 0))
        p.setFont(self.font_)
        mem = m.mem
        cw, ch = self.cw, self.ch
        for r in range(ROWS):
            base = TEXT_BASE + r * COLS * 2
            c = 0
            while c < COLS:
                attr = mem[base + c * 2 + 1]
                start = c
                chars = []
                while c < COLS and mem[base + c * 2 + 1] == attr:
                    chars.append(mem[base + c * 2])
                    c += 1
                bg = CGA[(attr >> 4) & (0x07 if m.blink else 0x0F)]
                fg = CGA[attr & 0x0F]
                if m.blink and attr & 0x80 and not self._blink:
                    fg = bg
                rect = QRect(start * cw, r * ch, (c - start) * cw, ch)
                if bg != (0, 0, 0):
                    p.fillRect(rect, QColor(*bg))
                text = bytes(chars).decode("cp437").replace("\0", " ")
                if text.strip():
                    p.setPen(QColor(*fg))
                    for k, glyph in enumerate(text):     # one cell per glyph keeps the grid exact
                        if glyph != " ":
                            p.drawText(QRect((start + k) * cw, r * ch, cw, ch), Qt.AlignmentFlag.AlignCenter, glyph)
        if m.cursor_visible and self._blink and self.hasFocus() or (m.cursor_visible and m.waiting and self._blink):
            row, col = m.cursor
            attr = mem[TEXT_BASE + (row * COLS + col) * 2 + 1]
            p.fillRect(QRect(col * cw, row * ch + ch - 3, cw, 2), QColor(*CGA[attr & 0x0F] if attr & 0x0F else CGA[7]))
        p.end()

    def _paint_gfx(self, p: QPainter, m: Machine) -> None:
        data = bytes(m.mem[0xA0000:0xA0000 + 64000])
        img = QImage(data, 320, 200, 320, QImage.Format.Format_Indexed8)
        img.setColorTable([QColor(*c).rgb() for c in m.palette])
        s = min(self.width() / 320, self.height() / 200)
        w, h = int(320 * s), int(200 * s)
        p.drawImage(QRect((self.width() - w) // 2, (self.height() - h) // 2, w, h), img)

    # -------------------------------------------------------------- keyboard
    KEYMAP = {Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down", Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right",
              Qt.Key.Key_Home: "home", Qt.Key.Key_End: "end", Qt.Key.Key_PageUp: "pgup",
              Qt.Key.Key_PageDown: "pgdn", Qt.Key.Key_Insert: "ins", Qt.Key.Key_Delete: "del",
              Qt.Key.Key_Escape: "esc", Qt.Key.Key_Return: "enter", Qt.Key.Key_Enter: "enter",
              Qt.Key.Key_Backspace: "backspace", Qt.Key.Key_Tab: "tab"}

    def event(self, e):
        # Tab must reach the program instead of moving the focus
        if e.type() == e.Type.KeyPress and e.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            self.keyPressEvent(e)
            return True
        return super().event(e)

    def keyPressEvent(self, e) -> None:
        m = self.machine
        if m is None:
            return super().keyPressEvent(e)
        key = e.key()
        for k in range(10):
            if key == getattr(Qt.Key, f"Key_F{k + 1}"):
                if k + 1 in (5, 9, 10, 11):               # keep the IDE's debugger keys
                    return super().keyPressEvent(e)
                m.press(f"f{k + 1}")
                self.keyTyped.emit()
                return
        if key in self.KEYMAP:
            m.press(self.KEYMAP[key])
        elif e.text():
            m.feed_keys(e.text())
        else:
            return super().keyPressEvent(e)
        self.keyTyped.emit()

    def mousePressEvent(self, e) -> None:
        self.setFocus()
        super().mousePressEvent(e)


# ============================================================================ registers / flags
class RegistersPanel(QWidget):
    """AX..DX with their H/L halves, SI DI BP SP, segment registers, IP and the flags as check boxes.
    Values are editable while the program is paused; changed values are shown in red."""

    edited = pyqtSignal()

    REGS = ("AX", "BX", "CX", "DX", "SI", "DI", "BP", "SP", "CS", "DS", "ES", "SS", "IP")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.machine: Machine | None = None
        self.setProperty("i18n_skip", True)
        g = QGridLayout(self)
        g.setContentsMargins(4, 4, 4, 4)
        g.setHorizontalSpacing(6)
        g.setVerticalSpacing(2)
        mono = QFont(MONO, 10)
        self.edits: dict[str, QLineEdit] = {}
        self.halves: dict[str, tuple[QLabel, QLabel]] = {}
        self.decs: dict[str, QLabel] = {}
        for col, text in enumerate(("", "hex", "H", "L", "dec")):
            lab = QLabel(text)
            lab.setStyleSheet("color: gray;")
            g.addWidget(lab, 0, col)
        for row, name in enumerate(self.REGS, start=1):
            lab = QLabel(name)
            lab.setFont(mono)
            g.addWidget(lab, row, 0)
            ed = QLineEdit("0000")
            ed.setFont(mono)
            ed.setMaxLength(4)
            ed.setFixedWidth(52)
            ed.setInputMask("HHHH")
            ed.editingFinished.connect(lambda n=name: self._edit(n))
            self.edits[name] = ed
            g.addWidget(ed, row, 1)
            if name in ("AX", "BX", "CX", "DX"):
                h, lo = QLabel("00"), QLabel("00")
                for w in (h, lo):
                    w.setFont(mono)
                h.setToolTip(name[0] + "H")
                lo.setToolTip(name[0] + "L")
                g.addWidget(h, row, 2)
                g.addWidget(lo, row, 3)
                self.halves[name] = (h, lo)
            d = QLabel("0")
            d.setFont(mono)
            g.addWidget(d, row, 4)
            self.decs[name] = d
        row = len(self.REGS) + 1
        fl = QLabel("Flags")
        fl.setStyleSheet("color: gray;")
        g.addWidget(fl, row, 0, 1, 5)
        self.flag_boxes: dict[str, QCheckBox] = {}
        box = QWidget()
        fg = QGridLayout(box)
        fg.setContentsMargins(0, 0, 0, 0)
        for k, (name, bit) in enumerate(FLAG_NAMES):
            cb = QCheckBox(name)
            cb.setFont(mono)
            cb.setToolTip({"OF": "Overflow", "DF": "Direction", "IF": "Interrupt enable", "TF": "Trap",
                           "SF": "Sign", "ZF": "Zero", "AF": "Auxiliary carry", "PF": "Parity",
                           "CF": "Carry"}[name])
            cb.clicked.connect(lambda on, b=bit: self._flag(b, on))
            fg.addWidget(cb, k // 3, k % 3)
            self.flag_boxes[name] = cb
        g.addWidget(box, row + 1, 0, 1, 5)
        g.setRowStretch(row + 2, 1)
        self._prev: dict[str, int] = {}
        self.editable = False

    def _value(self, name: str) -> int:
        regs = self.machine.registers()
        return regs[name]

    def refresh(self, editable: bool) -> None:
        m = self.machine
        if m is None:
            return
        self.editable = editable
        regs = m.registers()
        for name, ed in self.edits.items():
            v = regs[name]
            changed = name in self._prev and self._prev[name] != v
            if not ed.hasFocus():
                ed.setText(_hex(v))
            ed.setReadOnly(not editable)
            ed.setStyleSheet("color: #d00000; font-weight: bold;" if changed else "")
            if name in self.halves:
                h, lo = self.halves[name]
                h.setText(_hex(v >> 8, 2))
                lo.setText(_hex(v & 0xFF, 2))
            self.decs[name].setText(str(v))
        for name, bit in FLAG_NAMES:
            cb = self.flag_boxes[name]
            on = bool(regs["FLAGS"] & bit)
            changed = "FLAGS" in self._prev and bool(self._prev["FLAGS"] & bit) != on
            cb.blockSignals(True)
            cb.setChecked(on)
            cb.blockSignals(False)
            cb.setEnabled(editable)
            cb.setStyleSheet("color: #d00000; font-weight: bold;" if changed else "")
        self._prev = regs

    def mark(self) -> None:
        """Remember the current values: the next refresh shows what the step changed."""
        if self.machine is not None:
            self._prev = self.machine.registers()

    def _edit(self, name: str) -> None:
        m = self.machine
        if m is None or not self.editable:
            return
        try:
            v = int(self.edits[name].text() or "0", 16) & 0xFFFF
        except ValueError:
            return
        c = m.cpu
        idx16 = ("AX", "CX", "DX", "BX", "SP", "BP", "SI", "DI")
        if name in idx16:
            c.r[idx16.index(name)] = v
        elif name in ("ES", "CS", "SS", "DS"):
            c.s[("ES", "CS", "SS", "DS").index(name)] = v
        elif name == "IP":
            c.ip = v
        self.edited.emit()

    def _flag(self, bit: int, on: bool) -> None:
        if self.machine is not None and self.editable:
            self.machine.cpu.set_flag(bit, on)
            self.edited.emit()


# ============================================================================ memory / stack / variables / listing
def parse_address(text: str, m: Machine) -> int | None:
    """'DS:0100', '0700:0010', 'B800:0', '12345' (linear hex), 'ES:DI', 'msg' (a variable)."""
    s = text.strip().lower().rstrip("h")
    if not s:
        return None
    regs = {k.lower(): v for k, v in m.registers().items()}
    if m.program is not None:
        for v in m.program.variables:
            if v.name.lower() == s:
                return v.linear
        for name, (seg, off) in m.program.labels.items():
            if name.lower() == s:
                return ((seg << 4) + off) & 0xFFFFF

    def num(x: str) -> int:
        x = x.strip()
        if x in regs:
            return regs[x]
        return int(x.rstrip("h"), 16)
    try:
        if ":" in s:
            seg, off = s.split(":", 1)
            return ((num(seg) << 4) + num(off)) & 0xFFFFF
        return num(s) & 0xFFFFF
    except ValueError:
        return None


class MemoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.machine: Machine | None = None
        self.setProperty("i18n_skip", True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        row = QHBoxLayout()
        row.addWidget(QLabel("Address:"))
        self.addr = QLineEdit("DS:0000")
        self.addr.setToolTip("segment:offset (DS:0000, B800:0000, ES:DI), a linear hex address or a variable name")
        self.addr.returnPressed.connect(self.refresh)
        row.addWidget(self.addr, 1)
        lay.addLayout(row)
        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont(MONO, 9))
        self.text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        lay.addWidget(self.text, 1)

    def show_address(self, text: str) -> None:
        self.addr.setText(text)
        self.refresh()

    def refresh(self) -> None:
        m = self.machine
        if m is None:
            return
        start = parse_address(self.addr.text(), m)
        if start is None:
            self.text.setPlainText("(invalid address)")
            return
        start &= ~0xF
        lines = []
        for k in range(24):
            a = (start + k * 16) & 0xFFFFF
            data = bytes(m.mem[a:a + 16])
            seg = a >> 4
            asc = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
            lines.append(f"{seg:04X}:0000 {a:05X}  " + " ".join(f"{b:02X}" for b in data) + "  " + asc)
        sb = self.text.verticalScrollBar().value()
        self.text.setPlainText("\n".join(lines))
        self.text.verticalScrollBar().setValue(sb)


class StackView(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.machine: Machine | None = None
        self.setProperty("i18n_skip", True)
        self.setHeaderLabels(["SS:offset", "Value", "Note"])
        self.setRootIsDecorated(False)
        self.setFont(QFont(MONO, 9))

    def refresh(self) -> None:
        m = self.machine
        self.clear()
        if m is None:
            return
        c = m.cpu
        offs, vals = m.stack_words(24)
        bp = c.r[5]
        for off, v in zip(offs, vals):
            notes = []
            if off == c.r[4]:
                notes.append("<- SP")
            if off == bp:
                notes.append("<- BP")
            if m.program is not None:
                lin = ((c.s[1] << 4) + v) & 0xFFFFF
                if lin in m.program.addr_line and _after_call(m, lin):
                    f, ln = m.program.addr_line[lin]
                    notes.append(f"return to line {ln}")
            QTreeWidgetItem(self, [f"{c.s[2]:04X}:{off:04X}", _hex(v), "  ".join(notes)])
        self.resizeColumnToContents(0)


def _after_call(m: Machine, lin: int) -> bool:
    """True when the instruction just before *lin* is a CALL (a return address on the stack)."""
    mem = m.mem
    if mem[lin - 3] == 0xE8 or mem[lin - 5] == 0x9A:
        return True
    for k in (2, 3, 4):
        if mem[lin - k] == 0xFF and ((mem[lin - k + 1] >> 3) & 7) in (2, 3):
            return True
    return False


class VariablesView(QTreeWidget):
    """Data labels of the program: address, type and value (arrays expand, byte arrays also as text)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.machine: Machine | None = None
        self.setProperty("i18n_skip", True)
        self.setHeaderLabels(["Name", "Address", "Type", "Hex", "Decimal", "Text"])
        self.setFont(QFont(MONO, 9))
        self._expanded: set[str] = set()
        self.itemExpanded.connect(lambda it: self._expanded.add(it.text(0)))
        self.itemCollapsed.connect(lambda it: self._expanded.discard(it.text(0)))

    def refresh(self) -> None:
        m = self.machine
        self.clear()
        if m is None or m.program is None:
            return
        for v in m.program.variables:
            vals = m.read_var(v)
            typ = {1: "byte", 2: "word", 4: "dword", 8: "qword"}.get(v.size, f"{v.size} bytes")
            if v.count > 1:
                typ += f"[{v.count}]"
            digits = v.size * 2
            first = vals[0] if vals else 0
            text = ""
            if v.size == 1:
                raw = bytes(vals)
                text = "".join(chr(b) if 32 <= b < 127 else "." for b in raw)
            it = QTreeWidgetItem(self, [v.name, f"{v.segment:04X}:{v.offset:04X}", typ, _hex(first, digits),
                                        str(_signed(first, v.size)), text])
            if v.count > 1:
                for k, val in enumerate(vals):
                    QTreeWidgetItem(it, [f"[{k}]", f"{v.segment:04X}:{(v.offset + k * v.size) & 0xFFFF:04X}",
                                         typ.split("[")[0], _hex(val, digits), str(_signed(val, v.size)),
                                         chr(val) if v.size == 1 and 32 <= val < 127 else ""])
                if v.name in self._expanded:
                    it.setExpanded(True)
        for k in range(6):
            self.resizeColumnToContents(k)


def _signed(v: int, size: int) -> int:
    bits = size * 8
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


class ListingView(QTreeWidget):
    """Machine code of every source line; the current instruction is selected."""

    lineActivated = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("i18n_skip", True)
        self.setHeaderLabels(["Address", "Bytes", "Line", "Source"])
        self.setRootIsDecorated(False)
        self.setFont(QFont(MONO, 9))
        self._by_addr: dict[int, QTreeWidgetItem] = {}
        self.itemDoubleClicked.connect(self._dclick)

    def load(self, program) -> None:
        self.clear()
        self._by_addr = {}
        if program is None:
            return
        for f, line, seg, off, data, src in program.listing:
            hexs = data[:6].hex(" ").upper() + (" ..." if len(data) > 6 else "")
            it = QTreeWidgetItem(self, [f"{seg:04X}:{off:04X}", hexs, str(line), src.strip()])
            it.setData(0, Qt.ItemDataRole.UserRole, (f, line))
            self._by_addr.setdefault(((seg << 4) + off) & 0xFFFFF, it)
        for k in range(3):
            self.resizeColumnToContents(k)

    def select_linear(self, lin: int) -> None:
        it = self._by_addr.get(lin)
        if it is not None:
            self.setCurrentItem(it)
            self.scrollToItem(it)

    def _dclick(self, it, _c) -> None:
        data = it.data(0, Qt.ItemDataRole.UserRole)
        if data:
            self.lineActivated.emit(data[0], int(data[1]))


# ============================================================================ the panel
class Emu8086Panel(QWidget):
    """The emulator dock: screen, controls, registers and views. The session drives it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session: Emu8086Session | None = None
        self.machine: Machine | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        bar = QHBoxLayout()
        self.b_run = QPushButton("Run")
        self.b_pause = QPushButton("Pause")
        self.b_step = QPushButton("Step")
        self.b_over = QPushButton("Step Over")
        self.b_back = QPushButton("Step Back")
        self.b_reset = QPushButton("Reload")
        self.b_export = QPushButton("Export...")
        self.b_export.setToolTip("Write the program as a DOS .COM or MZ .EXE file next to the source "
                                 "(runs in DOSBox / FreeDOS)")
        self.b_run.setToolTip("Run / continue (F5)")
        self.b_step.setToolTip("Execute one source line, entering procedures (F11)")
        self.b_over.setToolTip("Execute one source line; CALL and INT run until they return (F10)")
        self.b_back.setToolTip("Undo the last step (reverse debugging)")
        self.b_reset.setToolTip("Load the program again and stop at the first instruction")
        for b in (self.b_run, self.b_pause, self.b_step, self.b_over, self.b_back, self.b_reset, self.b_export):
            b.setAutoDefault(False)
            bar.addWidget(b)
        from PyQt6.QtWidgets import QMenu
        menu = QMenu(self.b_export)
        menu.addAction("Export .COM / .EXE (the program's kind)", lambda: self.export_dos(""))
        menu.addAction("Export as .COM", lambda: self.export_dos("com"))
        menu.addAction("Export as MZ .EXE", lambda: self.export_dos("exe"))
        self.b_export.setMenu(menu)
        bar.addSpacing(10)
        bar.addWidget(QLabel("Speed:"))
        self.speed = QSlider(Qt.Orientation.Horizontal)
        self.speed.setRange(1, 100)
        self.speed.setValue(100)
        self.speed.setFixedWidth(130)
        self.speed.setToolTip("Left: slow motion (the current line moves in the editor); right: full speed")
        bar.addWidget(self.speed)
        self.speed_label = QLabel("max")
        self.speed_label.setMinimumWidth(70)
        bar.addWidget(self.speed_label)
        self.history = QCheckBox("Record history")
        self.history.setChecked(True)
        self.history.setToolTip("Keep the last 200000 steps so Step Back can undo them")
        bar.addWidget(self.history)
        bar.addStretch(1)
        lay.addLayout(bar)
        self.status = QLabel("")
        self.status.setProperty("i18n_skip", True)
        lay.addWidget(self.status)

        split = QSplitter(Qt.Orientation.Horizontal)
        left = QSplitter(Qt.Orientation.Vertical)
        self.screen = ScreenWidget()
        left.addWidget(self.screen)
        self.tabs = QTabWidget()
        self.memory = MemoryView()
        self.stack = StackView()
        self.variables = VariablesView()
        self.listing = ListingView()
        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.tabs.addTab(self.variables, "Variables")
        self.tabs.addTab(self.memory, "Memory")
        self.tabs.addTab(self.stack, "Stack")
        self.tabs.addTab(self.listing, "Listing")
        left.addWidget(self.tabs)
        left.setSizes([420, 220])
        split.addWidget(left)
        self.registers = RegistersPanel()
        split.addWidget(self.registers)
        split.setSizes([700, 230])
        split.setStretchFactor(0, 1)
        lay.addWidget(split, 1)
        self.speed.valueChanged.connect(self._speed_changed)
        self.b_run.clicked.connect(lambda: self.session and self.session.cont())
        self.b_pause.clicked.connect(lambda: self.session and self.session.pause())
        self.b_step.clicked.connect(lambda: self.session and self.session.step_into())
        self.b_over.clicked.connect(lambda: self.session and self.session.step_over())
        self.b_back.clicked.connect(lambda: self.session and self.session.step_back())
        self.b_reset.clicked.connect(lambda: self.session and self.session.reload())
        self.history.toggled.connect(self._history_toggled)
        self.registers.edited.connect(self._edited)
        self.screen.keyTyped.connect(lambda: self.session and self.session.key_typed())
        self.listing.lineActivated.connect(self._goto_line)
        self.update_buttons(False, False)

    def export_source(self) -> Path | None:
        """The 8086 source to export: the running session's program, else the active editor's file."""
        s = self.session
        if s is not None and getattr(s, "startup_file", ""):
            p = Path(s.startup_file)
            return p if p.is_absolute() else Path(s.folder) / p
        win = self.window()
        for name in ("current_path", "current_file"):
            f = getattr(win, name, None)
            try:
                f = f() if callable(f) else f
            except Exception:  # noqa: BLE001
                f = None
            if f and str(f).lower().endswith((".asm", ".8086", ".a86")):
                return Path(f)
        return None

    def export_dos(self, kind: str = "", source: Path | None = None) -> Path | None:
        """Export .COM / .EXE (radide/emu8086/dosexe.py); the result is shown in the status line."""
        from .dosexe import ExportError, export_file
        from .messages import text as msg_text
        src = source or self.export_source()
        if src is None:
            self.status.setText("Export: open or run an 8086 program first")
            return None
        try:
            out = export_file(src, kind=kind)
        except (ExportError, OSError) as e:
            why = str(e)
            self.status.setText("Export failed: " + (msg_text(why, ui_language()) if why.startswith("E-") else why))
            return None
        self.status.setText(f"Exported {out.name} ({out.stat().st_size} bytes) - run it in DOSBox: {out}")
        win = self.window()
        if hasattr(win, "log"):
            try:
                win.log(f"[8086] exported {out}")
            except Exception:  # noqa: BLE001
                pass
        return out

    def steps_per_second(self) -> float:
        v = self.speed.value()
        if v >= 100:
            return 0.0                    # unlimited
        return max(1.0, round(10 ** (v / 25.0)))

    def _speed_changed(self, _v) -> None:
        sps = self.steps_per_second()
        self.speed_label.setText("max" if not sps else f"{int(sps)} steps/s")
        if self.session is not None:
            self.session.speed_changed()

    def _history_toggled(self, on: bool) -> None:
        if self.machine is not None:
            self.machine.record_history = on
            if not on:
                self.machine.history.clear()
        self.update_buttons(self.session is not None and self.session.running(),
                            self.session is not None and self.session.paused)

    def _edited(self) -> None:
        if self.session is not None:
            self.session.state_edited()

    def _goto_line(self, f: str, line: int) -> None:
        win = self.session.win if self.session is not None else None
        if win is not None:
            ed = win._editor_for_file(Path(f).name)
            if ed is not None:
                ed.goto_line(line - 1)

    def attach(self, session, machine: Machine) -> None:
        self.session = session
        self.machine = machine
        for w in (self.screen, self.registers, self.memory, self.stack, self.variables):
            if isinstance(w, ScreenWidget):
                w.set_machine(machine)
            else:
                w.machine = machine
        machine.record_history = self.history.isChecked()
        self.listing.load(machine.program)
        if machine.program is not None and not machine.program.com:
            self.memory.addr.setText("DS:0000")
        else:
            self.memory.addr.setText("CS:0100")

    def update_buttons(self, running: bool, paused: bool) -> None:
        live = running and not paused
        self.b_run.setEnabled(running and paused)
        self.b_pause.setEnabled(live)
        self.b_step.setEnabled(running and paused)
        self.b_over.setEnabled(running and paused)
        self.b_back.setEnabled(bool(paused and self.machine is not None and self.machine.history))
        self.b_reset.setEnabled(self.session is not None and self.session.program is not None)

    def refresh(self, paused: bool, heavy: bool = True) -> None:
        m = self.machine
        if m is None:
            return
        self.registers.refresh(paused)
        if heavy:
            cur = self.tabs.currentWidget()
            if cur is self.memory:
                self.memory.refresh()
            elif cur is self.stack:
                self.stack.refresh()
            elif cur is self.variables:
                self.variables.refresh()
            self.listing.select_linear(m.linear_ip())
        c = m.cpu
        self.status.setText(f"CS:IP = {c.s[1]:04X}:{c.ip:04X}    steps: {c.cycles}    "
                            f"history: {len(m.history)}")


# ============================================================================ the IDE session
def _stop_info(file, line, reason, variables, frames, refs):
    from ..debugger import StopInfo
    return StopInfo(file, line, reason, variables, frames, refs)


class Emu8086Session(QObject):
    output = pyqtSignal(str)
    stopped = pyqtSignal(object)
    resumed = pyqtSignal()
    evalResult = pyqtSignal(str)
    finished = pyqtSignal(int)
    failed = pyqtSignal(str)

    SLICE_SECONDS = 0.03

    def __init__(self, win, folder: Path, startup_file: str, debug: bool, breakpoints, parent=None):
        super().__init__(parent or win)
        self.win = win
        self.folder = Path(folder)
        self.startup_file = startup_file
        self.debug = debug
        self.paused = False
        self.user_stopped = False
        self.caps = {"children"}
        self._bps: set[tuple[str, int]] = set()
        for bp in breakpoints or []:
            self._bps.add((Path(bp[0]).name.lower(), int(bp[1])))
        self.program = None
        self.machine: Machine | None = None
        self._alive = False
        self._goal = None                    # callable() -> True when a step / step over / step out is done
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._slice)
        self._out_len = 0
        self._fatal = False
        self._last_line = None
        self._refs: dict = {}
        self._finish_code = None
        self._skip_bp = False
        self._slice_start = 0.0
        self.panel: Emu8086Panel | None = None
        self.lang = ui_language()

    # ------------------------------------------------------------------ IDE interface
    def running(self) -> bool:
        return self._alive

    def start(self) -> None:
        QTimer.singleShot(0, self._start)

    def _start(self) -> None:
        from .assembler import assemble
        path = self.folder / self.startup_file
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            self.failed.emit(str(e))
            self.finished.emit(1)
            return
        prog = assemble(src, path.name, include_dir=self.folder)
        self.program = prog
        show_diagnostics(self.win, prog, self.lang)
        for d in prog.warnings:
            self.output.emit(f"{Path(d.file).name}({d.line}): warning: {d.text(self.lang)}\n")
        if not prog.ok:
            for d in prog.errors:
                self.output.emit(f"{Path(d.file).name}({d.line}): error: {d.text(self.lang)}\n")
            self.output.emit(f"\n*** {len(prog.errors)} assembly error(s) - see the Error List\n")
            self.finished.emit(2)
            return
        size = sum(len(b) for _a, b in prog.chunks)
        kind = "COM" if prog.com else "EXE"
        self.output.emit(f"Assembled {path.name}: {kind} program, {size} bytes, entry "
                         f"{prog.entry_cs:04X}:{prog.entry_ip:04X}\n")
        m = Machine()
        m.lang = self.lang
        m.realtime = True
        m.load(prog)
        self.machine = m
        self._apply_breakpoints()
        self.panel = ensure_panel(self.win)
        self.panel.attach(self, m)
        self._alive = True
        self.panel.update_buttons(True, False)
        dock = getattr(self.win, "_emu8086_dock", None)
        if dock is not None:
            dock.show()
            dock.raise_()
        stop_at_entry = self.debug and _setting(self.win, "emu8086/stop_at_entry", True)             and getattr(self.win, "_run_to", None) is None          # Run to Cursor goes straight to the line
        if stop_at_entry:
            self.output.emit("Paused at the first instruction: F10 / F11 step, F5 runs. "
                             "Click the emulator screen to type.\n")
            self._pause("entry")
        else:
            self._resume_running()

    def stop(self) -> None:
        if not self._alive:
            return
        self.user_stopped = True
        self._finish(0)

    def cont(self) -> None:
        if not self._alive:
            return
        if self._fatal or (self.machine is not None and self.machine.exited):
            self._finish(self.machine.exit_code if self.machine else 0)
            return
        self._goal = None
        self._resume_running(skip_bp=True)

    def pause(self) -> None:
        if self._alive and not self.paused:
            self._timer.stop()
            self._pause("pause")

    def step_into(self) -> None:
        if not self._can_step():
            return
        m = self.machine
        if self._first_step() is not None:
            return
        if m.current_line() is not None:
            self._pause("step")
            return
        self._goal = lambda: m.current_line() is not None      # ran into ROM / an interrupt handler
        self._resume_running(skip_bp=True, step=True)

    def step_over(self) -> None:
        if not self._can_step():
            return
        m = self.machine
        if not m._is_call_like():
            return self.step_into()
        c = m.cpu
        sp0, ss0, cs0 = c.r[4], c.s[2], c.s[1]
        info = self._first_step()
        if info is not None:
            return
        dec = (sp0 - c.r[4]) & 0xFFFF
        if dec in (2, 4, 6):
            ret_ip = c.rw(c.s[2], c.r[4])
            ret_cs = cs0 if dec == 2 else c.rw(c.s[2], c.r[4] + 2)
            target = ((ret_cs << 4) + ret_ip) & 0xFFFFF
            state = {"back": False}

            def goal():
                if not state["back"]:
                    if m.linear_ip() == target and c.s[2] == ss0 and c.r[4] >= sp0:
                        state["back"] = True
                    else:
                        return False
                return m.current_line() is not None
            self._goal = goal
        elif m.current_line() is not None:
            self._pause("step")
            return
        else:
            self._goal = lambda: m.current_line() is not None
        self._resume_running(skip_bp=True, step=True)

    def step_out(self) -> None:
        if not self._can_step():
            return
        m = self.machine
        c = m.cpu
        sp0 = c.r[4]
        state = {"out": False}

        def goal():
            if not state["out"]:
                op = m.mem[((c.op_cs << 4) + c.op_ip) & 0xFFFFF]
                if op in (0xC3, 0xC2, 0xCB, 0xCA, 0xCF) and c.r[4] > sp0:
                    state["out"] = True
                else:
                    return False
            return m.current_line() is not None
        self._goal = goal
        self._resume_running(skip_bp=True, step=True)

    def step_back(self) -> None:
        if not self._alive or not self.paused or self.machine is None:
            return
        m = self.machine
        if not m.history:
            return
        if self.panel is not None:
            self.panel.registers.mark()
        m.step_back()
        while m.history and m.current_line() is None:      # back through ROM / interrupt handler code
            m.step_back()
        self._fatal = False
        self._pause("step back")

    def reload(self) -> None:
        if self.program is None:
            return
        self._timer.stop()
        if not self._alive:
            return
        self.machine.load(self.program)
        self._fatal = False
        self._out_len = 0
        self.panel.attach(self, self.machine)
        self.output.emit("\n------ Reloaded ------\n")
        self._pause("entry")

    def evaluate(self, expr: str) -> None:
        self.evalResult.emit(self._eval_text(expr))

    def watch(self, expr: str, cb) -> None:
        if self.machine is None:
            cb("(not running)", "", 0)
            return
        cb(self._eval_text(expr), "", 0)

    def children(self, ref, cb) -> None:
        data = self._refs.get(ref)
        cb(data or [])

    def threads(self, cb) -> None:
        cb([(1, "8086 CPU")])

    def select_thread(self, tid) -> None:
        pass

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = "") -> None:
        key = (Path(filename).name.lower(), int(line))
        if on:
            self._bps.add(key)
        else:
            self._bps.discard(key)
        self._apply_breakpoints()

    def set_break_on_exception(self, on: bool) -> None:
        pass

    def send(self, cmd: str) -> None:
        pass

    # ------------------------------------------------------------------ panel callbacks
    def speed_changed(self) -> None:
        pass

    def state_edited(self) -> None:
        if self.paused:
            self._pause("edit", emit=False)

    def key_typed(self) -> None:
        m = self.machine
        if m is None or not self._alive:
            return
        if not self.paused and not self._timer.isActive():
            self._timer.start(0)

    # ------------------------------------------------------------------ internals
    def _apply_breakpoints(self) -> None:
        if self.machine is not None and self.debug:
            self.machine.set_breakpoint_lines(self._bps)

    def _can_step(self) -> bool:
        return self._alive and self.paused and self.machine is not None and not self._fatal \
            and not self.machine.exited

    def _first_step(self):
        """One instruction right away (so a step never stops on its own breakpoint)."""
        if self.panel is not None:
            self.panel.registers.mark()
        info = self.machine.step()
        if info is not None:
            self._handle_stop(info)
        return info

    def _resume_running(self, skip_bp: bool = False, step: bool = False) -> None:
        if self.paused:
            self.paused = False
            self.resumed.emit()
        if self.panel is not None:
            if not step:
                self.panel.registers.mark()
            self.panel.update_buttons(True, False)
        self._skip_bp = skip_bp
        self._slice_start = time.perf_counter()
        self._timer.start(0)

    def _slice(self) -> None:
        m = self.machine
        if m is None or not self._alive or self.paused:
            return
        if m.waiting and not m.keys:
            self._show_waiting()
            return
        sps = self.panel.steps_per_second() if self.panel is not None else 0
        goal = self._goal
        if sps:
            steps = max(1, int(sps * 0.05)) if sps > 20 else 1
            info = self._run_steps(steps, goal)
            animated = sps <= 60
            if info is None:
                if animated:
                    self._highlight(m.current_line())
                if self.panel is not None:
                    self.panel.refresh(False, heavy=animated)
                self._timer.start(int(1000 * steps / sps) if sps <= 20 else 50)
                self._emit_output()
                return
        else:
            deadline = time.perf_counter() + self.SLICE_SECONDS
            info = None
            while time.perf_counter() < deadline:
                info = self._run_steps(4000, goal)
                if info is not None:
                    break
            if info is None:
                self._emit_output()
                if self.panel is not None:
                    self.panel.refresh(False, heavy=False)
                self._timer.start(0)
                return
        self._handle_stop(info)

    def _run_steps(self, n: int, goal):
        """Up to n instructions. Returns a machine StopInfo, a 'goal' stop or None (still running)."""
        m = self.machine
        bps = m.breakpoints if self.debug else set()
        skip = self._skip_bp
        self._skip_bp = False
        from .machine import StopInfo as MStop
        for _ in range(n):
            if bps and not skip and m.linear_ip() in bps:
                return MStop("break")
            skip = False
            info = m.step()
            if info is not None:
                return info
            if goal is not None and goal():
                return MStop("step")
            if getattr(m, "pending_sleep_us", 0):
                us, m.pending_sleep_us = m.pending_sleep_us, 0
                self._emit_output()
                self._timer.start(min(5000, us // 1000))
                return None
        return None

    def _handle_stop(self, info) -> None:
        m = self.machine
        self._emit_output()
        if info.reason == "input":
            self._show_waiting()
            return
        if info.reason in ("break", "step"):
            self._goal = None
            self._pause("breakpoint" if info.reason == "break" else "step")
            return
        if info.reason == "exit":
            self._goal = None
            self.output.emit(f"\n[8086] program terminated with code {m.exit_code}\n")
            self._finish(m.exit_code)
            return
        if info.reason in ("error", "halt"):
            self._goal = None
            self._fatal = True
            self.output.emit(f"\n*** {info.message}\n")
            if self.debug:
                self._pause("error")
            else:
                self._finish(-1 if info.reason == "error" else 0)
            return

    def _show_waiting(self) -> None:
        if self.panel is not None:
            self.panel.status.setText(self.panel.status.text().split("   [")[0] +
                                      "   [waiting for keyboard input - click the screen and type]")
            self.panel.refresh(False, heavy=True)
            if not self.panel.screen.hasFocus():
                self.panel.screen.setFocus()
        line = self.machine.current_line() or self._last_line
        if line is not None:
            self._highlight(line)
        try:
            self.win._set_run_state("Running (waiting for keyboard input in the 8086 screen)")
        except Exception:  # noqa: BLE001
            pass

    def _emit_output(self) -> None:
        m = self.machine
        if m is None:
            return
        out = m.output
        if len(out) < self._out_len:
            self._out_len = len(out)
        if len(out) > self._out_len:
            chunk = out[self._out_len:]
            self._out_len = len(out)
            self.output.emit(chunk.replace("\r\n", "\n").replace("\r", ""))
        for note in m.log:
            self.output.emit(f"[8086] {note}\n")
        m.log.clear()

    def _highlight(self, line) -> None:
        if line is None:
            return
        self._last_line = line
        win = self.win
        try:
            win._clear_current_line()
            ed = win._editor_for_file(Path(line[0]).name)
            if ed is not None:
                ed.set_current_line(line[1] - 1)
                win.stopped_at = (ed, line[1] - 1)
        except Exception:  # noqa: BLE001 - the editor may be closing
            pass

    def _pause(self, reason: str, emit: bool = True) -> None:
        m = self.machine
        self._timer.stop()
        self.paused = True
        if self.panel is not None:
            self.panel.refresh(True)
            self.panel.update_buttons(True, True)
        line = m.current_line() or self._last_line or (self.startup_file, 1)
        self._last_line = line
        if not emit:
            return
        variables, refs = self._locals()
        frames = self._frames(line)
        self.stopped.emit(_stop_info(line[0], line[1], reason, variables, frames, refs))

    def _locals(self):
        m = self.machine
        regs = m.registers()
        out = []
        refs = {}
        self._refs = {}
        for name in ("AX", "BX", "CX", "DX", "SI", "DI", "BP", "SP", "CS", "DS", "ES", "SS", "IP"):
            v = regs[name]
            extra = f"  ({name[0]}H={v >> 8:02X} {name[0]}L={v & 0xFF:02X})" if name in ("AX", "BX", "CX", "DX") else ""
            out.append((name, "register", f"{v:04X}h = {v}{extra}"))
        flags = " ".join(n for n, b in FLAG_NAMES if regs["FLAGS"] & b) or "-"
        out.append(("FLAGS", "flags", f"{regs['FLAGS']:04X}h  {flags}"))
        if m.program is not None:
            for k, v in enumerate(m.program.variables):
                vals = m.read_var(v)
                typ = {1: "db", 2: "dw", 4: "dd", 8: "dq"}.get(v.size, "?")
                digits = v.size * 2
                if v.count > 1:
                    if v.size == 1:
                        raw = bytes(vals)
                        shown = "'" + "".join(chr(b) if 32 <= b < 127 else "." for b in raw[:40]) + "'"
                    else:
                        shown = "[" + ", ".join(str(x) for x in vals[:12]) + (", ..." if v.count > 12 else "") + "]"
                    ref = k + 1
                    refs[v.name] = ref
                    self._refs[ref] = [(f"[{i}]", typ, f"{x:0{digits}X}h = {x}", 0) for i, x in enumerate(vals)]
                else:
                    x = vals[0] if vals else 0
                    shown = f"{x:0{digits}X}h = {x}" + (f" '{chr(x)}'" if v.size == 1 and 32 <= x < 127 else "")
                out.append((v.name, f"{typ} @{v.segment:04X}:{v.offset:04X}", shown))
        return out, refs

    def _frames(self, line):
        """Call stack: the current procedure, then return addresses found on the stack."""
        m = self.machine
        prog = m.program
        frames = [(self._proc_at(m.linear_ip()) or "main", line[0], line[1])]
        c = m.cpu
        for k in range(48):
            v = c.rw(c.s[2], c.r[4] + 2 * k)
            lin = ((c.s[1] << 4) + v) & 0xFFFFF
            if prog is not None and lin in prog.addr_line and _after_call(m, lin):
                f, ln = prog.addr_line[lin]
                # the CALL is the line before the return address
                call_line = self._line_before(lin) or (f, ln)
                frames.append((self._proc_at(lin) or "main", call_line[0], call_line[1]))
            if len(frames) > 12:
                break
        return frames

    def _line_before(self, lin: int):
        prog = self.machine.program
        for k in range(1, 6):
            if lin - k in prog.addr_line:
                return prog.addr_line[lin - k]
        return None

    def _proc_at(self, lin: int) -> str:
        prog = self.machine.program
        best, best_lin = "", -1
        for name, (seg, off) in prog.labels.items():
            a = ((seg << 4) + off) & 0xFFFFF
            if best_lin < a <= lin and not name.startswith("??"):
                best, best_lin = name, a
        return best

    def _eval_text(self, expr: str) -> str:
        m = self.machine
        if m is None:
            return "(not running)"
        try:
            v, size = evaluate_watch(expr, m)
        except Exception as e:  # noqa: BLE001
            return f"(cannot evaluate: {e})"
        if isinstance(v, list):
            return "[" + ", ".join(str(x) for x in v[:32]) + "]"
        digits = 2 if size == 1 else 4 if size == 2 else 8
        return f"{v & ((1 << (size * 8)) - 1):0{digits}X}h = {v}"

    def _finish(self, code: int) -> None:
        if not self._alive:
            return
        self._alive = False
        self._timer.stop()
        self.paused = False
        self._emit_output()
        if self.panel is not None:
            self.panel.refresh(False)
            self.panel.update_buttons(False, False)
            self.panel.status.setText(self.panel.status.text() + "   [finished]")
        self.finished.emit(code)


def evaluate_watch(expr: str, m: Machine):
    """Watch / Immediate expressions: registers (ax, al ...), flags (zf ...), variables (their value; arrays
    give a list), [address] / byte ptr [address] / word ptr es:[di], numbers and + - * /."""
    import re

    from .assembler import REG8, REG16, SREG
    from .cpu import FLAG_NAMES as FN
    s = expr.strip()
    low = s.lower()
    size = 2
    mm = re.match(r"^(byte|word|dword)\s+ptr\s+(.*)$", low)
    if mm:
        size = {"byte": 1, "word": 2, "dword": 4}[mm.group(1)]
        low = mm.group(2).strip()
    regs = m.registers()
    c = m.cpu
    if m.program is not None and not mm:
        for v in m.program.variables:
            if v.name.lower() == low:
                vals = m.read_var(v)
                return (vals if v.count > 1 else vals[0]), v.size
    for name, bit in FN:
        if low == name.lower():
            return (1 if regs["FLAGS"] & bit else 0), 1
    seg = None
    mseg = re.match(r"^(es|cs|ss|ds)\s*:\s*(.*)$", low)
    if mseg:
        seg = c.s[SREG[mseg.group(1)]]
        low = mseg.group(2)
    memref = low.startswith("[") and low.endswith("]")
    inner = low[1:-1] if memref else low

    def subst(mt):
        w = mt.group(0)
        if w in REG16:
            return str(c.r[REG16[w]])
        if w in REG8:
            return str(c.get8(REG8[w]))
        if w in SREG:
            return str(c.s[SREG[w]])
        if w == "ip":
            return str(c.ip)
        if m.program is not None:
            for v in m.program.variables:
                if v.name.lower() == w:
                    return str(v.offset)
        return w
    text = re.sub(r"[a-z_][a-z0-9_]*", subst, inner)
    text = re.sub(r"\b([0-9][0-9a-f]*)h\b", lambda t: str(int(t.group(1), 16)), text)
    if not re.fullmatch(r"[0-9+\-*/() x]*", text):
        raise ValueError(expr)
    value = int(eval(text, {"__builtins__": {}}, {})) if text.strip() else 0  # noqa: S307 - digits/operators only
    if memref:
        if seg is None:
            seg = c.s[2] if re.search(r"\bbp\b", inner) else c.s[3]
        a = ((seg << 4) + (value & 0xFFFF)) & 0xFFFFF
        return int.from_bytes(m.mem[a:a + size], "little"), size
    if low in REG8:
        size = 1
    return value, size


# ============================================================================ IDE glue
def _setting(win, key: str, default):
    try:
        v = win.settings.value(key, default)
    except Exception:  # noqa: BLE001
        return default
    if isinstance(v, str):
        return v.lower() in ("1", "true", "yes")
    return bool(v)


def ensure_panel(win) -> Emu8086Panel:
    """The "8086 Emulator" dock of the main window (created once)."""
    panel = getattr(win, "_emu8086_panel", None)
    if panel is not None:
        return panel
    from PyQt6.QtWidgets import QDockWidget
    panel = Emu8086Panel(win)
    dock = QDockWidget("8086 Emulator", win)
    dock.setObjectName("8086 Emulator")
    dock.setWidget(panel)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    dock.setFloating(False)
    win._emu8086_panel = panel
    win._emu8086_dock = dock
    try:
        view_menu = next(a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "View")
        view_menu.addAction(dock.toggleViewAction())
    except StopIteration:
        pass
    return panel


def show_diagnostics(win, prog, lang: str = "en") -> None:
    """Assembler errors / warnings into the Error List (keeps rows of other sources)."""
    el = getattr(win, "error_list", None)
    if el is None:
        return
    old = getattr(win, "_emu8086_err_keys", set())
    for i in reversed(range(el.topLevelItemCount())):
        it = el.topLevelItem(i)
        if (it.text(0), it.text(1), it.text(2), it.text(3)) in old:
            el.takeTopLevelItem(i)
    keys = set()
    for d in list(prog.errors) + list(prog.warnings):
        row = [d.severity, d.text(lang), Path(d.file).name, str(d.line)]
        it = QTreeWidgetItem(row)
        it.setForeground(0, Qt.GlobalColor.darkRed if d.severity == "Error" else Qt.GlobalColor.darkYellow)
        el.addTopLevelItem(it)
        keys.add(tuple(row))
    win._emu8086_err_keys = keys
    errors = sum(el.topLevelItem(i).text(0) == "Error" for i in range(el.topLevelItemCount()))
    warnings = sum(el.topLevelItem(i).text(0) == "Warning" for i in range(el.topLevelItemCount()))
    try:
        win.dock_errors.setWindowTitle(f"Error List ({errors} errors, {warnings} warnings)")
        if prog.errors:
            win.dock_errors.show()
            win.dock_errors.raise_()
    except Exception:  # noqa: BLE001
        pass


__all__ = ["ScreenWidget", "RegistersPanel", "MemoryView", "StackView", "VariablesView", "ListingView",
           "Emu8086Panel", "Emu8086Session", "ensure_panel", "show_diagnostics", "evaluate_watch"]
