"""Qt windows of the Apollo AGC support: an original DSKY panel and the "Apollo AGC" debug dock
(DSKY + registers + erasable memory + channels + program variables).

The DSKY is drawn by RAD IDE (no images from elsewhere): the caution / status lamps on the left, the green
electroluminescent display (COMP ACTY, PROG, VERB, NOUN, R1-R3) on the right, the 19-key keyboard below.
It shows a ``DskyModel`` and emits ``keyPressed(name)`` / ``proChanged(pressed)``; the emulator session and the
yaAGC socket link (radide/agc/yaagc.py) both use it.
"""
from __future__ import annotations

from PyQt6.QtCore import QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QPushButton, QSplitter,
                             QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from .cpu import decimal
from .dsky_model import DskyModel

LAMP_GRID = [("UPLINK ACTY", "TEMP"), ("NO ATT", "GIMBAL LOCK"), ("STBY", "PROG"), ("KEY REL", "RESTART"),
             ("OPR ERR", "TRACKER"), ("PRIO DISP", "ALT"), ("NO DAP", "VEL")]
AMBER = {"TEMP", "GIMBAL LOCK", "PROG", "RESTART", "TRACKER", "ALT", "VEL", "PRIO DISP", "NO DAP"}
KEYPAD = [["VERB", "+", "7", "8", "9", "CLR", "ENTR"],
          ["NOUN", "-", "4", "5", "6", "PRO", "RSET"],
          ["", "0", "1", "2", "3", "KEY REL", ""]]
# segments a b c d e f g (top, top-right, bottom-right, bottom, bottom-left, top-left, middle)
SEGMENTS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc",
            "7": "abc", "8": "abcdefg", "9": "abcdfg", " ": "", "?": "g"}
GREEN = QColor(80, 255, 110)
GREEN_DIM = QColor(18, 48, 24)


class DskyDisplay(QWidget):
    """The lamps and the EL display (painted)."""

    def __init__(self, model: DskyModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.setMinimumSize(360, 250)
        self.setProperty("i18n_skip", True)

    def sizeHint(self) -> QSize:
        return QSize(430, 290)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(self.rect(), QColor(58, 60, 62))
        lw = w * 0.42
        self._lamps(p, QRectF(8, 8, lw - 16, h - 16))
        self._display(p, QRectF(lw + 4, 8, w - lw - 12, h - 16))
        p.end()

    def _lamps(self, p: QPainter, r: QRectF) -> None:
        p.fillRect(r, QColor(40, 41, 43))
        rows = len(LAMP_GRID)
        cw, ch = r.width() / 2, r.height() / rows
        f = QFont("Arial", max(6, int(ch * 0.2)))
        f.setBold(True)
        p.setFont(f)
        for i, pair in enumerate(LAMP_GRID):
            for j, name in enumerate(pair):
                cell = QRectF(r.x() + j * cw + 4, r.y() + i * ch + 4, cw - 8, ch - 8)
                on = self.model.lamps.get(name, False)
                if on:
                    col = QColor(255, 196, 40) if name in AMBER else QColor(245, 245, 235)
                else:
                    col = QColor(92, 86, 70) if name in AMBER else QColor(88, 88, 86)
                p.setPen(QPen(QColor(20, 20, 20), 1))
                p.setBrush(col)
                p.drawRoundedRect(cell, 3, 3)
                p.setPen(QColor(30, 30, 30) if on else QColor(150, 150, 140))
                p.drawText(cell, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, name)

    def _digit(self, p: QPainter, r: QRectF, ch: str) -> None:
        segs = SEGMENTS.get(ch, "")
        t = max(2.0, r.width() * 0.16)
        x0, y0, x1, y1 = r.left(), r.top(), r.right(), r.bottom()
        ym = (y0 + y1) / 2
        lines = {"a": ((x0 + t, y0), (x1 - t, y0)), "b": ((x1, y0 + t), (x1, ym - t / 2)),
                 "c": ((x1, ym + t / 2), (x1, y1 - t)), "d": ((x0 + t, y1), (x1 - t, y1)),
                 "e": ((x0, ym + t / 2), (x0, y1 - t)), "f": ((x0, y0 + t), (x0, ym - t / 2)),
                 "g": ((x0 + t, ym), (x1 - t, ym))}
        for s, ((ax, ay), (bx, by)) in lines.items():
            p.setPen(QPen(GREEN if s in segs else GREEN_DIM, t, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(int(ax), int(ay), int(bx), int(by))

    def _sign(self, p: QPainter, r: QRectF, sign: str) -> None:
        t = max(2.0, r.width() * 0.16)
        ym = (r.top() + r.bottom()) / 2
        xm = (r.left() + r.right()) / 2
        p.setPen(QPen(GREEN if sign in "+-" else GREEN_DIM, t, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(int(r.left() + t), int(ym), int(r.right() - t), int(ym))
        p.setPen(QPen(GREEN if sign == "+" else GREEN_DIM, t, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(int(xm), int(r.top() + r.height() * 0.22), int(xm), int(r.bottom() - r.height() * 0.22))

    def _display(self, p: QPainter, r: QRectF) -> None:
        p.fillRect(r, QColor(12, 14, 12))
        m = self.model
        pad = r.width() * 0.05
        dw = (r.width() - 2 * pad) / 6.6
        dh = r.height() / 7.0
        label_font = QFont("Arial", max(6, int(dh * 0.22)))
        label_font.setBold(True)
        p.setFont(label_font)

        def label(rect: QRectF, text: str, lit=True):
            p.fillRect(rect, GREEN if lit else GREEN_DIM)
            p.setPen(QColor(10, 20, 10))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        top = r.top() + pad * 0.6
        comp = QRectF(r.left() + pad, top, dw * 2, dh * 1.2)
        label(comp, "COMP\nACTY", m.lamps.get("COMP ACTY", False))
        label(QRectF(r.right() - pad - dw * 2, top, dw * 2, dh * 0.35), "PROG")
        self._digits(p, QRectF(r.right() - pad - dw * 2, top + dh * 0.45, dw * 2, dh * 0.85), m.prog)
        row2 = top + dh * 1.5
        vn_lit = not (m.lamps.get("VN FLASH") and (m.writes // 3) % 2)
        label(QRectF(r.left() + pad, row2, dw * 2, dh * 0.35), "VERB", vn_lit)
        label(QRectF(r.right() - pad - dw * 2, row2, dw * 2, dh * 0.35), "NOUN", vn_lit)
        self._digits(p, QRectF(r.left() + pad, row2 + dh * 0.45, dw * 2, dh * 0.85), m.verb)
        self._digits(p, QRectF(r.right() - pad - dw * 2, row2 + dh * 0.45, dw * 2, dh * 0.85), m.noun)
        y = row2 + dh * 1.45
        for reg in ("r1", "r2", "r3"):
            p.setPen(QPen(GREEN, 2))
            p.drawLine(int(r.left() + pad), int(y), int(r.right() - pad), int(y))
            rr = QRectF(r.left() + pad, y + dh * 0.12, r.width() - 2 * pad, dh * 0.95)
            text = getattr(m, reg)
            self._sign(p, QRectF(rr.left(), rr.top(), dw * 0.85, rr.height()), text[0])
            self._digits(p, QRectF(rr.left() + dw * 1.1, rr.top(), rr.width() - dw * 1.1, rr.height()), text[1:])
            y += dh * 1.2

    def _digits(self, p: QPainter, r: QRectF, text: str) -> None:
        n = max(1, len(text))
        cw = r.width() / n
        for i, ch in enumerate(text):
            cell = QRectF(r.left() + i * cw + cw * 0.14, r.top() + r.height() * 0.06, cw * 0.62, r.height() * 0.88)
            self._digit(p, cell, ch)


class DskyWidget(QWidget):
    """The whole DSKY: display + keyboard. Keys also work from the keyboard while it has focus:
    0-9, V (VERB), N (NOUN), Enter (ENTR), C / Backspace (CLR), R (RSET), P (PRO), K (KEY REL), + and -."""
    keyPressed = pyqtSignal(str)
    proChanged = pyqtSignal(bool)

    def __init__(self, model: DskyModel | None = None, parent=None):
        super().__init__(parent)
        self.model = model or DskyModel()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setProperty("i18n_skip", True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        self.display = DskyDisplay(self.model, self)
        lay.addWidget(self.display, 1)
        grid = QGridLayout()
        grid.setSpacing(3)
        self.buttons: dict[str, QPushButton] = {}
        for r, row in enumerate(KEYPAD):
            for c, name in enumerate(row):
                if not name:
                    continue
                b = QPushButton(name.replace(" ", "\n") if len(name) > 4 else name)
                b.setMinimumSize(44, 34)
                b.setStyleSheet("QPushButton{background:#d9d6cc;color:#111;font-weight:bold;border:1px solid #555;"
                                "border-radius:4px} QPushButton:pressed{background:#a9a59a}")
                b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                if name == "PRO":
                    b.pressed.connect(lambda: self.proChanged.emit(True))
                    b.released.connect(lambda: self.proChanged.emit(False))
                else:
                    b.clicked.connect(lambda _c=False, n=name: self.keyPressed.emit(n))
                grid.addWidget(b, r, c)
                self.buttons[name] = b
        lay.addLayout(grid)

    def set_model(self, model: DskyModel) -> None:
        self.model = model
        self.display.model = model
        self.display.update()

    def refresh(self) -> None:
        self.display.update()

    def keyPressEvent(self, e) -> None:
        key = e.key()
        text = e.text().upper()
        names = {"V": "VERB", "N": "NOUN", "C": "CLR", "R": "RSET", "K": "KEY REL", "+": "+", "-": "-"}
        if text.isdigit():
            self.keyPressed.emit(text)
        elif text in names:
            self.keyPressed.emit(names[text])
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_E):
            self.keyPressed.emit("ENTR")
        elif key == Qt.Key.Key_Backspace:
            self.keyPressed.emit("CLR")
        elif key == Qt.Key.Key_P and not e.isAutoRepeat():
            self.proChanged.emit(True)
        else:
            super().keyPressEvent(e)

    def keyReleaseEvent(self, e) -> None:
        if e.key() == Qt.Key.Key_P and not e.isAutoRepeat():
            self.proChanged.emit(False)
        else:
            super().keyReleaseEvent(e)


def _item(cols) -> QTreeWidgetItem:
    return QTreeWidgetItem([str(c) for c in cols])


class AgcPanel(QWidget):
    """The "Apollo AGC" dock: DSKY on the left, Registers / Erasable / Channels / Variables on the right."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        bar = QHBoxLayout()
        self.status = QLabel("Apollo AGC: not running")
        self.status.setProperty("i18n_skip", True)
        bar.addWidget(self.status, 1)
        self.b_pause = QPushButton("Pause")
        self.b_step = QPushButton("Step")
        self.b_reset = QPushButton("Reset")
        for b in (self.b_pause, self.b_step, self.b_reset):
            b.setEnabled(False)
            bar.addWidget(b)
        self.b_pause.clicked.connect(self._pause_clicked)
        self.b_step.clicked.connect(lambda: self.session and self.session.step_into())
        self.b_reset.clicked.connect(lambda: self.session and self.session.reload())
        lay.addLayout(bar)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.dsky = DskyWidget(parent=self)
        split.addWidget(self.dsky)
        self.tabs = QTabWidget()
        self.registers = QTreeWidget()
        self.registers.setHeaderLabels(["Register", "Octal", "Decimal"])
        self.registers.setRootIsDecorated(False)
        self.registers.setProperty("i18n_skip_items", True)
        self.tabs.addTab(self.registers, "Registers")
        mem = QWidget()
        ml = QVBoxLayout(mem)
        ml.setContentsMargins(0, 0, 0, 0)
        self.bank = QComboBox()
        self.bank.addItems([f"E{i}" for i in range(8)])
        self.bank.currentIndexChanged.connect(lambda _i: self.refresh(True))
        ml.addWidget(self.bank)
        self.memory = QTreeWidget()
        self.memory.setHeaderLabels(["Address"] + [str(i) for i in range(8)])
        self.memory.setRootIsDecorated(False)
        self.memory.setProperty("i18n_skip_items", True)
        self.memory.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.memory.setFont(QFont("Consolas", 9))
        ml.addWidget(self.memory)
        self.tabs.addTab(mem, "Erasable Memory")
        self.channels = QTreeWidget()
        self.channels.setHeaderLabels(["Channel", "Octal", "Meaning"])
        self.channels.setRootIsDecorated(False)
        self.channels.setProperty("i18n_skip_items", True)
        self.tabs.addTab(self.channels, "Channels")
        self.variables = QTreeWidget()
        self.variables.setHeaderLabels(["Name", "Address", "Octal", "Decimal"])
        self.variables.setRootIsDecorated(False)
        self.variables.setProperty("i18n_skip_items", True)
        self.tabs.addTab(self.variables, "Variables")
        split.addWidget(self.tabs)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        lay.addWidget(split, 1)

    def _pause_clicked(self) -> None:
        s = self.session
        if s is None:
            return
        if s.paused:
            s.cont()
        else:
            s.pause()

    def update_buttons(self, running: bool, paused: bool) -> None:
        self.b_pause.setEnabled(running)
        self.b_pause.setText("Continue" if paused else "Pause")
        self.b_step.setEnabled(running and paused and hasattr(self.session, "step_into"))
        self.b_reset.setEnabled(running and hasattr(self.session, "reload"))

    def refresh(self, heavy: bool = True) -> None:
        self.dsky.refresh()
        s = self.session
        cpu = getattr(getattr(s, "machine", None), "cpu", None)
        if cpu is None:
            return
        regs = cpu.registers()
        self.registers.clear()
        for name, v in regs.items():
            if name in ("A", "Q"):
                ov = " (overflow)" if ((v >> 15) & 1) != ((v >> 14) & 1) else ""
                self.registers.addTopLevelItem(_item([name, f"{v:06o}{ov}", decimal(((v & 0o37777) |
                                                                                    ((v >> 1) & 0o40000)))]))
            else:
                self.registers.addTopLevelItem(_item([name, f"{v:05o}", decimal(v)]))
        loc = cpu.location()
        self.registers.addTopLevelItem(_item(["Location", f"{loc[0]}{loc[1]:o},{cpu.Z:04o}", ""]))
        self.registers.addTopLevelItem(_item(["Interrupts", "inhibited" if cpu.inhibit else "enabled",
                                              "in RUPT" if cpu.in_rupt else ""]))
        self.registers.addTopLevelItem(_item(["MCT / instructions", str(cpu.mct), str(cpu.instructions)]))
        if not heavy:
            return
        bank = self.bank.currentIndex()
        self.memory.clear()
        base = bank * 0o400 if bank < 3 else 0o1400
        for row in range(0, 0o400, 8):
            vals = [f"{cpu.erasable[bank][row + k]:05o}" for k in range(8)]
            self.memory.addTopLevelItem(_item([f"{base + row:04o}"] + vals))
        from .isa import CHANNEL_DOCS
        self.channels.clear()
        for ch in sorted(set(cpu.channels) | {0o10, 0o11, 0o15, 0o32}):
            self.channels.addTopLevelItem(_item([f"{ch:03o}", f"{cpu.channels.get(ch, 0):05o}",
                                                 CHANNEL_DOCS.get(ch, ("", ""))[0][:70]]))
        self.variables.clear()
        prog = getattr(s.machine, "program", None)
        if prog is not None:
            for name, l in sorted(prog.symbols.items(), key=lambda kv: kv[1].pseudo()):
                if l.kind != "E" or (l.bank == 0 and l.off < 0o61):
                    continue
                v = cpu.read_erasable(l.bank, l.off)
                self.variables.addTopLevelItem(_item([name, str(l), f"{v:05o}", decimal(v)]))


__all__ = ["AgcPanel", "DskyDisplay", "DskyWidget"]
