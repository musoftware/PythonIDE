"""Native debugger windows (Visual Studio style) for every gdb session - C, C++, Fortran, Rust, Go
(gcc), assembly:

* **Registers** (Debug > Windows > Registers, Alt+5): general purpose registers, the flags register
  decoded bit by bit (CF PF AF ZF SF TF IF DF OF), segments, SSE/AVX (xmm as 128-bit hex) and FPU.
  Values that changed since the last stop are red; double-click a value to change it (a flag:
  double-click toggles it).
* **Disassembly** (Alt+8): Intel syntax around the current instruction (yellow arrow), with the source
  lines in between (C / Rust / ... debug information, or the line table of .asm files), code bytes,
  Step Into / Over Instruction, and breakpoints on addresses (click the left column or F9).
* **Memory 1** (Alt+6): hex + ASCII from an address or expression (0x401000, $rsp, &buf, a label),
  1 / 2 / 4 / 8-byte groups, "follow" a register, re-evaluated at every stop; changed bytes are red;
  double-click to write bytes.
* **Stack** : the machine stack from the stack pointer, one pointer per row, with RSP / RBP marked and
  what each value points to (symbol + offset).

Debug > Step Into Instruction (Ctrl+Alt+F11) / Step Over Instruction (Ctrl+Alt+F10) step one machine
instruction in any gdb session. The engine side is radide/nativedbg.py.
"""
from __future__ import annotations

import html
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QAction, QBrush, QColor, QFont, QKeySequence, QTextCursor
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDockWidget, QHBoxLayout, QInputDialog,
                             QLabel, QMenu, QMessageBox, QPushButton, QTextEdit, QToolButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import nativedbg as nd

MONO = "Consolas"
NOT_NATIVE = "Available while a native program (C, C++, Rust, Fortran, Go, assembly) is paused in gdb."


def _mono(size: int = 9) -> QFont:
    f = QFont(MONO, size)
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f


def _dark() -> bool:
    try:
        from .. import theme
        return theme.is_dark()
    except Exception:  # noqa: BLE001
        return False


def _changed_color() -> QColor:
    return QColor("#ff6b6b") if _dark() else QColor("#d00000")


def _hex(n: int, width: int = 16) -> str:
    return f"{n:0{width}X}"


class _View(QWidget):
    """A native window: refresh(d) when the program stops, stale() when it runs, clear() at the end."""
    title = ""

    def __init__(self, hub):
        super().__init__()
        self.hub = hub
        self.setProperty("i18n_skip_items", True)
        self.note = QLabel(NOT_NATIVE)
        self.note.setWordWrap(True)
        try:
            from .. import theme
            theme.role(self.note, "muted")
        except Exception:  # noqa: BLE001
            pass

    def d(self):
        return self.hub.dap()

    def gen_ok(self, gen) -> bool:
        return gen == self.hub.gen

    def refresh(self, d):
        pass

    def stale(self):
        pass

    def clear(self):
        pass


# ====================================================================== Registers
class RegistersView(_View):
    title = "Registers"
    GROUPS = ("General", "Flags", "Segments", "SSE / AVX", "FPU", "Other")

    def __init__(self, hub):
        super().__init__(hub)
        self.prev: dict[str, str] = {}
        self.values: dict[str, tuple[str, int | None]] = {}
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["CPU Register", "Value", "Description"])
        self.tree.setFont(_mono())
        self.tree.setColumnWidth(0, 110)
        self.tree.setColumnWidth(1, 260)
        self.tree.setUniformRowHeights(True)
        self.tree.itemDoubleClicked.connect(self._edit)
        self.hex = QCheckBox("Hexadecimal")
        self.hex.setChecked(True)
        self.hex.toggled.connect(lambda _on: self._fill())
        self.extended = QCheckBox("SSE / FPU")
        self.extended.setToolTip("Also show the xmm (128-bit, hex) and x87 FPU registers")
        self.extended.toggled.connect(lambda _on: self.hub.refresh_all())
        top = QHBoxLayout()
        top.addWidget(self.hex)
        top.addWidget(self.extended)
        top.addStretch(1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addLayout(top)
        lay.addWidget(self.note)
        lay.addWidget(self.tree, 1)
        self.groups: dict[str, QTreeWidgetItem] = {}
        self.expanded = {"General": True, "Flags": True, "SSE / AVX": True, "FPU": True}

    def refresh(self, d):
        gen = self.hub.gen

        def got(regs):
            if not self.gen_ok(gen):
                return
            self.prev = {k: v[0] for k, v in self.values.items()}
            self.values = {name: (val, num) for name, val, num, _ref in regs}
            self.tree.setEnabled(True)
            self._fill()
        nd.read_registers(d, got, ("sse", "float") if self.extended.isChecked() else ())

    def _text(self, name: str, val: str, num: int | None) -> str:
        if nd.register_group(name) in ("SSE / AVX", "FPU") and name.lower().startswith(("xmm", "ymm", "st")):
            return val
        if name.lower() in nd.FLAGS:
            return (f"{num:#x}  {val}" if num is not None else val) if self.hex.isChecked() else \
                (f"{num}  {val}" if num is not None else val)
        if num is None:
            return val
        if self.hex.isChecked():
            width = 16 if abs(num) > 0xFFFFFFFF or name.lower().startswith("r") else 8
            tail = val[val.find("<"):] if "<" in val else ""
            return f"{_hex(num & ((1 << 64) - 1), width)} {tail}".rstrip()
        return str(num)

    def _fill(self):
        for g, it in self.groups.items():
            self.expanded[g] = it.isExpanded()
        self.tree.clear()
        self.groups = {}
        self.note.setVisible(not self.values)
        red = QBrush(_changed_color())
        for name, (val, num) in self.values.items():
            g = nd.register_group(name)
            parent = self.groups.get(g)
            if parent is None:
                parent = QTreeWidgetItem([g])
                f = parent.font(0)
                f.setBold(True)
                parent.setFont(0, f)
                parent.setFirstColumnSpanned(True)
                self.groups[g] = parent
            it = QTreeWidgetItem(parent, [name, self._text(name, val, num), ""])
            it.setData(0, Qt.ItemDataRole.UserRole, name)
            if name in self.prev and self.prev[name] != val:
                it.setForeground(1, red)
                it.setForeground(0, red)
            if name.lower() in nd.FLAGS and num is not None and name.lower() != "cpsr":
                old = nd.flags_value(self.prev.get(name, "")) if name in self.prev else None
                for flag, bit, desc in nd.FLAG_BITS:
                    on = (num >> bit) & 1
                    child = QTreeWidgetItem(it, [flag, str(on), desc])
                    child.setData(0, Qt.ItemDataRole.UserRole, f"{name}:{bit}")
                    if old is not None and ((old >> bit) & 1) != on:
                        child.setForeground(1, red)
                        child.setForeground(0, red)
                it.setExpanded(True)
        order = {g: i for i, g in enumerate(self.GROUPS)}
        for g in sorted(self.groups, key=lambda g: order.get(g, 99)):
            self.tree.addTopLevelItem(self.groups[g])
            self.groups[g].setExpanded(self.expanded.get(g, False))
            self.groups[g].setFirstColumnSpanned(True)

    def _edit(self, item, _col):
        key = item.data(0, Qt.ItemDataRole.UserRole)
        d = self.d()
        if not key or d is None or not d.paused:
            return
        if ":" in key:                                      # a flag bit: toggle it
            reg, bit = key.split(":")
            num = self.values.get(reg, ("", None))[1]
            if num is None:
                return
            nd.set_register(d, reg, hex(num ^ (1 << int(bit))), lambda _t, ok: self._after_edit(ok, _t))
            return
        val, num = self.values.get(key, ("", None))
        cur = hex(num) if num is not None else val
        text, ok = QInputDialog.getText(self, "Edit Register", f"New value of {key} (0x... hex or decimal):", text=cur)
        if ok and text.strip():
            nd.set_register(d, key, text.strip(), lambda t, ok2: self._after_edit(ok2, t))

    def _after_edit(self, ok, msg):
        if not ok:
            QMessageBox.warning(self, "Edit Register", str(msg))
        self.hub.refresh_all()

    def stale(self):
        self.tree.setEnabled(False)

    def clear(self):
        self.tree.clear()
        self.groups = {}
        self.values = {}
        self.prev = {}
        self.note.setVisible(True)

    def showEvent(self, e):
        super().showEvent(e)
        self.tree.setEnabled(True)


# ====================================================================== Disassembly
class DisassemblyView(_View):
    title = "Disassembly"
    COUNT = 96

    def __init__(self, hub):
        super().__init__(hub)
        self.addr = QComboBox()
        self.addr.setEditable(True)
        self.addr.setMinimumWidth(180)
        self.addr.lineEdit().setPlaceholderText("$pc  (address, label or expression)")
        self.addr.lineEdit().returnPressed.connect(self.go)
        go = QPushButton("Go")
        go.clicked.connect(self.go)
        self.show_src = QCheckBox("Show source")
        self.show_src.setChecked(True)
        self.show_bytes = QCheckBox("Show code bytes")
        self.show_src.toggled.connect(lambda _o: self._render())
        self.show_bytes.toggled.connect(lambda _o: self._render())
        self.b_into = QToolButton(text="Step Into Instruction")
        self.b_over = QToolButton(text="Step Over Instruction")
        self.b_pc = QToolButton(text="Show Next Statement")
        self.b_into.clicked.connect(lambda: self.hub.step(False))
        self.b_over.clicked.connect(lambda: self.hub.step(True))
        self.b_pc.clicked.connect(self.show_pc)
        top = QHBoxLayout()
        top.addWidget(QLabel("Address:"))
        top.addWidget(self.addr, 1)
        top.addWidget(go)
        top.addWidget(self.show_src)
        top.addWidget(self.show_bytes)
        bar = QHBoxLayout()
        for b in (self.b_into, self.b_over, self.b_pc):
            bar.addWidget(b)
        bar.addStretch(1)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["", "Address", "Code bytes", "Instruction"])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setFont(_mono())
        self.tree.setColumnWidth(0, 34)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 150)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.itemClicked.connect(self._clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._menu)
        f9 = QAction(self.tree)
        f9.setShortcut(QKeySequence("F9"))
        f9.setShortcutContext(Qt.ShortcutContext.WidgetShortcut)
        f9.triggered.connect(self.toggle_bp_at_selection)
        self.tree.addAction(f9)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addLayout(top)
        lay.addLayout(bar)
        lay.addWidget(self.note)
        lay.addWidget(self.tree, 1)
        self.instrs: list[dict] = []
        self.pc: int | None = None
        self._files: dict[str, list[str]] = {}

    # ------------------------------------------------------------ fetching
    def go(self):
        d = self.d()
        if d is None:
            return
        self.refresh(d, keep_address=True)

    def show_pc(self):
        self.addr.setEditText("")
        d = self.d()
        if d is not None:
            self.refresh(d)

    def refresh(self, d, keep_address: bool = False):
        gen = self.hub.gen
        expr = self.addr.currentText().strip() if keep_address else ""
        if not keep_address:
            self.addr.setEditText("")                     # a stop: follow the current instruction again
        if expr in ("$pc", "$rip", "$eip"):
            expr = ""

        def fetch_from(start, pc):
            def got(instrs):
                if not self.gen_ok(gen):
                    return
                if pc is not None and instrs and not any(i["address"] == pc for i in instrs) and start != pc:
                    fetch_from(pc, pc)              # the function start was a guess: start at the pc
                    return
                self.instrs = instrs
                self.pc = pc
                self._render()
            nd.disassemble(d, start, self.COUNT, got)

        def got_pc(pc):
            if not self.gen_ok(gen):
                return
            if expr:
                def got_addr(a, err):
                    if not self.gen_ok(gen):
                        return
                    if a is None:
                        self.note.setText(f"{expr}: {err}")
                        self.note.setVisible(True)
                        return
                    if self.addr.findText(expr) < 0:
                        self.addr.insertItem(0, expr)
                    fetch_from(a, pc)
                nd.eval_address(d, expr, got_addr)
            elif pc is None:
                self.clear()
            else:
                nd.function_start(d, pc, lambda start: self.gen_ok(gen) and fetch_from(start, pc))
        nd.current_pc(d, got_pc)

    # ------------------------------------------------------------ showing
    def _source_line(self, path: str, line: int) -> str:
        if path not in self._files:
            self._files[path] = []
            cands = [Path(path)]
            if not Path(path).is_absolute():          # gdb names sources as they were compiled (relative)
                d = nd.dap_of(self.hub.win.session)
                proj = getattr(self.hub.win, "project", None)
                cands = [Path(base) / path for base in (getattr(d, "cwd", None),
                                                        getattr(proj, "folder", None)) if base] + cands
            for p in cands:
                try:
                    self._files[path] = p.read_text(encoding="utf-8", errors="replace").splitlines()
                    break
                except OSError:
                    continue
        lines = self._files[path]
        return lines[line - 1] if 0 < line <= len(lines) else ""

    def _where(self, ins) -> tuple[str, int]:
        if ins.get("file") and ins.get("line"):
            return ins["file"], int(ins["line"])
        d = self.d()
        lm = getattr(d, "linemap", None)
        if lm:
            hit = lm.line_for(ins["address"] - getattr(d, "slide", 0))
            if hit:
                return hit
        return "", 0

    def _render(self):
        self.tree.clear()
        self.note.setVisible(not self.instrs)
        self.note.setText(NOT_NATIVE)
        bps = nd.address_breakpoints(self.hub.win.session)
        last = None
        cur_item = None
        red = QBrush(QColor("#e51400"))
        pc_bg = QBrush(QColor("#5a5a1e") if _dark() else QColor("#fff3a0"))
        src_fg = QBrush(QColor("#9cdcfe") if _dark() else QColor("#1f4e9c"))
        for ins in self.instrs:
            if self.show_src.isChecked():
                where = self._where(ins)
                if where[0] and where != last:
                    text = self._source_line(*where)
                    s = QTreeWidgetItem(["", "", "", f"{Path(where[0]).name}:{where[1]}   {text.strip()}"])
                    s.setForeground(3, src_fg)
                    s.setData(0, Qt.ItemDataRole.UserRole + 1, where)
                    self.tree.addTopLevelItem(s)
                last = where
            a = ins["address"]
            sym = f"  <{ins['symbol']}>" if ins.get("symbol") and not ins["text"].endswith(">") else ""
            row = QTreeWidgetItem(["", f"{a:016X}", ins["bytes"].upper() if self.show_bytes.isChecked() else "",
                                   ins["text"] + sym])
            row.setData(0, Qt.ItemDataRole.UserRole, a)
            marks = ("●" if a in bps else "") + ("➤" if a == self.pc else "")
            row.setText(0, marks)
            if a in bps:
                row.setForeground(0, red)
            if a == self.pc:
                for c in range(4):
                    row.setBackground(c, pc_bg)
                cur_item = row
            self.tree.addTopLevelItem(row)
        self.tree.setColumnHidden(2, not self.show_bytes.isChecked())
        if cur_item is not None:
            self.tree.scrollToItem(cur_item, QAbstractItemView.ScrollHint.PositionAtCenter)

    # ------------------------------------------------------------ breakpoints / menu
    def _clicked(self, item, col):
        if col == 0 and item.data(0, Qt.ItemDataRole.UserRole) is not None:
            self.toggle_bp(int(item.data(0, Qt.ItemDataRole.UserRole)))

    def toggle_bp(self, address: int):
        on = nd.toggle_address_breakpoint(self.hub.win.session, address)
        if on is None:
            self.hub.win.statusBar().showMessage(NOT_NATIVE, 5000)
            return
        self.hub.win.statusBar().showMessage(f"Breakpoint at address 0x{address:X} {'set' if on else 'removed'}", 4000)
        self._render()

    def toggle_bp_at_selection(self):
        it = self.tree.currentItem()
        if it is not None and it.data(0, Qt.ItemDataRole.UserRole) is not None:
            self.toggle_bp(int(it.data(0, Qt.ItemDataRole.UserRole)))

    def _menu(self, pos):
        it = self.tree.itemAt(pos)
        m = QMenu(self)
        if it is not None and it.data(0, Qt.ItemDataRole.UserRole) is not None:
            a = int(it.data(0, Qt.ItemDataRole.UserRole))
            m.addAction("Toggle Breakpoint", lambda: self.toggle_bp(a))
            m.addAction("Show Memory at This Address", lambda: self.hub.show_memory(hex(a)))
            where = self._where(next((i for i in self.instrs if i["address"] == a), {"address": a}))
            if where[0]:
                m.addAction("Go To Source Code", lambda: self.hub.goto_source(*where))
        elif it is not None and it.data(0, Qt.ItemDataRole.UserRole + 1):
            where = it.data(0, Qt.ItemDataRole.UserRole + 1)
            m.addAction("Go To Source Code", lambda: self.hub.goto_source(*where))
        m.addAction("Copy", self._copy)
        m.addAction("Show Next Statement", self.show_pc)
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def _copy(self):
        from PyQt6.QtWidgets import QApplication
        rows = self.tree.selectedItems() or [self.tree.currentItem()]
        QApplication.clipboard().setText("\n".join("  ".join(r.text(c) for c in range(1, 4) if r.text(c))
                                                   for r in rows if r is not None))

    def stale(self):
        self.pc = None
        if self.instrs:
            self._render()

    def clear(self):
        self.tree.clear()
        self.instrs = []
        self.pc = None
        self._files.clear()
        self.note.setText(NOT_NATIVE)
        self.note.setVisible(True)


# ====================================================================== Memory
class MemoryView(_View):
    title = "Memory 1"
    ROWS = 16
    WIDTH = 16

    def __init__(self, hub):
        super().__init__(hub)
        self.addr = QComboBox()
        self.addr.setEditable(True)
        self.addr.setMinimumWidth(180)
        self.addr.lineEdit().setPlaceholderText("Address: 0x..., $rsp, &buf, a label")
        self.addr.lineEdit().returnPressed.connect(self.go)
        self.group = QComboBox()
        for n in (1, 2, 4, 8):
            self.group.addItem(f"{n}-byte", n)
        self.group.currentIndexChanged.connect(lambda _i: self._render())
        self.follow = QComboBox()
        self.follow.addItem("(no register)", "")
        for r in ("rsp", "rbp", "rip", "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "r8", "r9"):
            self.follow.addItem(r, r)
        self.follow.currentIndexChanged.connect(self._follow_changed)
        self.live = QCheckBox("Re-evaluate at each stop")
        self.live.setChecked(True)
        up, down = QToolButton(text="▲"), QToolButton(text="▼")
        up.setToolTip("Previous page")
        down.setToolTip("Next page")
        up.clicked.connect(lambda: self.page(-1))
        down.clicked.connect(lambda: self.page(1))
        go = QPushButton("Go")
        go.clicked.connect(self.go)
        top = QHBoxLayout()
        top.addWidget(QLabel("Address:"))
        top.addWidget(self.addr, 1)
        top.addWidget(go)
        top.addWidget(up)
        top.addWidget(down)
        top2 = QHBoxLayout()
        top2.addWidget(QLabel("Columns:"))
        top2.addWidget(self.group)
        top2.addWidget(QLabel("Follow:"))
        top2.addWidget(self.follow)
        top2.addWidget(self.live)
        top2.addStretch(1)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        self.view.setFont(_mono())
        self.view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.view.viewport().installEventFilter(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addLayout(top)
        lay.addLayout(top2)
        lay.addWidget(self.note)
        lay.addWidget(self.view, 1)
        self.base: int | None = None
        self.data: bytes = b""
        self.readable: list[bool] = []
        self.prev: dict[int, int] = {}
        self.offset = 0

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if obj is self.view.viewport() and ev.type() == QEvent.Type.MouseButtonDblClick:
            self._edit_at(self.view.cursorForPosition(ev.position().toPoint()))
            return True
        return super().eventFilter(obj, ev)

    def _follow_changed(self, _i):
        reg = self.follow.currentData()
        if reg:
            self.addr.setEditText("$" + reg)
            self.offset = 0
            self.go()

    def go(self):
        self.offset = 0
        d = self.d()
        if d is not None:
            self.refresh(d, force=True)

    def page(self, n: int):
        self.offset += n * self.ROWS * self.WIDTH
        d = self.d()
        if d is not None:
            self.refresh(d, force=True)

    def show_address(self, expr: str):
        self.addr.setEditText(expr)
        self.go()

    def refresh(self, d, force: bool = False):
        expr = self.addr.currentText().strip()
        if not expr:
            return
        if not force and not self.live.isChecked() and self.base is not None:
            self._read(d, self.base)
            return
        gen = self.hub.gen

        def got(a, err):
            if not self.gen_ok(gen):
                return
            if a is None:
                self.note.setText(f"{expr}: {err}")
                self.note.setVisible(True)
                return
            if self.addr.findText(expr) < 0:
                self.addr.insertItem(0, expr)
            self._read(d, max(0, a + self.offset))
        nd.eval_address(d, expr, got)

    def _read(self, d, base: int):
        gen = self.hub.gen
        size = self.ROWS * self.WIDTH
        if base != self.base:
            self.prev = {}
        else:
            self.prev = {self.base + i: b for i, b in enumerate(self.data) if self.readable[i]}

        def done(data: bytes, ok_rows: list[bool]):
            if not self.gen_ok(gen):
                return
            self.base, self.data = base, data
            self.readable = [ok_rows[i // self.WIDTH] for i in range(len(data))]
            self.note.setVisible(False)
            self._render()

        def whole(data, ok):
            if ok and len(data) == size:
                done(data, [True] * self.ROWS)
                return
            rows: list[bytes | None] = [None] * self.ROWS      # part of it unreadable: row by row
            left = [self.ROWS]
            for r in range(self.ROWS):
                def one(chunk, ok2, r=r):
                    rows[r] = chunk if ok2 and len(chunk) == self.WIDTH else None
                    left[0] -= 1
                    if left[0] == 0:
                        done(b"".join(c if c is not None else b"\0" * self.WIDTH for c in rows),
                             [c is not None for c in rows])
                nd.read_memory(d, base + r * self.WIDTH, self.WIDTH, one)
        nd.read_memory(d, base, size, whole)

    def _render(self):
        if self.base is None:
            return
        g = int(self.group.currentData() or 1)
        red = _changed_color().name()
        out = []
        for r in range(0, len(self.data), self.WIDTH):
            addr = self.base + r
            parts = []
            for i in range(r, min(r + self.WIDTH, len(self.data)), g):
                chunk = self.data[i:i + g]
                if not all(self.readable[i:i + g]):
                    cell = "??" * len(chunk)
                    changed = False
                else:
                    cell = int.from_bytes(chunk, "little").to_bytes(len(chunk), "big").hex().upper()
                    changed = any(self.base + i + k in self.prev and self.prev[self.base + i + k] != chunk[k]
                                  for k in range(len(chunk)))
                parts.append(f'<span style="color:{red}">{cell}</span>' if changed else cell)
            asc = "".join((chr(b) if 32 <= b < 127 else ".") if self.readable[r + k] else "?"
                          for k, b in enumerate(self.data[r:r + self.WIDTH]))
            out.append(f"{addr:016X}  " + " ".join(parts) + "  " + html.escape(asc))
        self.view.setHtml('<pre style="margin:0">' + "\n".join(out) + "</pre>")

    def byte_at(self, cursor: QTextCursor) -> int | None:
        """The address under a text cursor (hex area or ASCII area)."""
        if self.base is None:
            return None
        row = cursor.blockNumber()
        col = cursor.positionInBlock()
        g = int(self.group.currentData() or 1)
        hex_start = 18
        cell_w = 2 * g + 1
        n_cells = self.WIDTH // g
        hex_end = hex_start + n_cells * cell_w - 1
        if hex_start <= col < hex_end:
            idx = (col - hex_start) // cell_w * g
        elif col >= hex_end + 2:
            idx = min(self.WIDTH - 1, col - hex_end - 2)
        else:
            idx = 0
        return self.base + row * self.WIDTH + idx

    def _edit_at(self, cursor):
        d = self.d()
        a = self.byte_at(cursor)
        if d is None or a is None or not d.paused:
            return
        text, ok = QInputDialog.getText(self, "Edit Memory", f"Bytes to write at 0x{a:X} (hex, e.g. 90 90 CC, "
                                        'or text in quotes, e.g. "Hi"):')
        if not ok or not text.strip():
            return
        t = text.strip()
        try:
            data = t[1:-1].encode("utf-8") if len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'" else \
                bytes.fromhex(t.replace(",", " "))
        except ValueError:
            QMessageBox.warning(self, "Edit Memory", "Write hex bytes (90 90 CC) or text in quotes.")
            return
        nd.write_memory(d, a, data, lambda ok2, msg: (None if ok2 else QMessageBox.warning(self, "Edit Memory", msg),
                                                      self.hub.refresh_all()))

    def clear(self):
        self.view.clear()
        self.base = None
        self.data = b""
        self.prev = {}
        self.note.setText(NOT_NATIVE)
        self.note.setVisible(True)


# ====================================================================== Stack (raw memory from the stack pointer)
class StackView(_View):
    title = "Stack"
    ROWS = 32
    ABOVE = 4

    def __init__(self, hub):
        super().__init__(hub)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["", "Address", "Value", "Points to"])
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)
        self.tree.setFont(_mono())
        self.tree.setColumnWidth(0, 60)
        self.tree.setColumnWidth(1, 150)
        self.tree.setColumnWidth(2, 150)
        self.tree.itemDoubleClicked.connect(self._dclick)
        self.prev: dict[int, int] = {}
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.addWidget(self.note)
        lay.addWidget(self.tree, 1)

    def refresh(self, d):
        gen = self.hub.gen

        def got_regs(regs):
            if not self.gen_ok(gen):
                return
            vals = {n.lower(): num for n, _v, num, _r in regs}
            ptr = 8 if "rsp" in vals else 4
            sp = vals.get("rsp", vals.get("esp", vals.get("sp")))
            bp = vals.get("rbp", vals.get("ebp", vals.get("fp")))
            if sp is None:
                self.clear()
                return
            start = max(0, sp - self.ABOVE * ptr)

            def got_mem(data, ok):
                if not self.gen_ok(gen):
                    return
                self.tree.clear()
                self.note.setVisible(False)
                if not ok:
                    self.note.setText(f"The stack at 0x{start:X} cannot be read.")
                    self.note.setVisible(True)
                    return
                red = QBrush(_changed_color())
                old, self.prev = self.prev, {}
                for i in range(0, len(data) - ptr + 1, ptr):
                    a = start + i
                    v = int.from_bytes(data[i:i + ptr], "little")
                    self.prev[a] = v
                    mark = "RSP ➤" if a == sp else ("RBP ➤" if a == bp else "")
                    if ptr == 4:
                        mark = mark.replace("RSP", "ESP").replace("RBP", "EBP")
                    it = QTreeWidgetItem([mark, f"{a:0{ptr * 2}X}", f"{v:0{ptr * 2}X}", ""])
                    it.setData(0, Qt.ItemDataRole.UserRole, v)
                    if a in old and old[a] != v:
                        it.setForeground(2, red)
                    if a < sp:
                        for c in range(4):
                            it.setForeground(c, QBrush(QColor("#888888")))
                    self.tree.addTopLevelItem(it)
                    if v >= 0x10000:
                        def got_sym(name, off, it=it):
                            if self.gen_ok(gen) and name:
                                try:
                                    it.setText(3, f"{name}+{off}" if off else name)
                                except RuntimeError:
                                    pass
                        nd.symbol_at(d, v, got_sym)
            nd.read_memory(d, start, self.ROWS * ptr, got_mem)
        nd.read_registers(d, got_regs)

    def _dclick(self, item, _col):
        v = item.data(0, Qt.ItemDataRole.UserRole)
        if v is not None:
            self.hub.show_memory(hex(int(v)))

    def clear(self):
        self.tree.clear()
        self.prev = {}
        self.note.setText(NOT_NATIVE)
        self.note.setVisible(True)


# ====================================================================== hub: stop / resume hooks
class NativeHub(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.gen = 0
        self.views: dict[str, _View] = {}
        self.docks: dict[str, QDockWidget] = {}
        self._auto_shown = None

    def dap(self):
        d = nd.dap_of(self.win.session)
        return d if nd.is_gdb(d) and getattr(d, "paused", False) else None

    def add(self, key: str, view: _View, dock: QDockWidget):
        self.views[key] = view
        self.docks[key] = dock
        dock.visibilityChanged.connect(lambda vis, k=key: vis and self._refresh_one(k))

    def _refresh_one(self, key):
        d = self.dap()
        if d is not None:
            self.views[key].refresh(d)

    def refresh_all(self):
        d = self.dap()
        if d is None:
            return
        self.gen += 1
        for k, v in self.views.items():
            if self.docks[k].isVisible():
                v.refresh(d)

    def on_stopped(self, info):
        d = self.dap()
        if d is None:
            return
        s = self.win.session
        if s is not self._auto_shown:                    # assembly: Registers come up at the first stop
            self._auto_shown = s
            if getattr(d, "linemap", None) is not None:
                self.docks["registers"].show()
        if not getattr(info, "file", "") and "disassembly" in self.docks:   # no source here: VS shows disassembly
            self.docks["disassembly"].show()
            self.docks["disassembly"].raise_()
        QTimer.singleShot(0, self.refresh_all)           # after the Locals / Watch requests

    def on_resumed(self):
        self.gen += 1
        for v in self.views.values():
            v.stale()

    def on_finished(self):
        self.gen += 1
        for v in self.views.values():
            v.clear()

    # ------------------------------------------------------------ commands
    def step(self, over: bool):
        if not nd.step_instruction(self.win.session, over):
            self.win.statusBar().showMessage(NOT_NATIVE, 5000)

    def show_memory(self, expr: str):
        dock = self.docks.get("memory")
        if dock is None:
            return
        dock.show()
        dock.raise_()
        self.views["memory"].show_address(expr)

    def show_disassembly(self):
        dock = self.docks.get("disassembly")
        if dock is not None:
            dock.show()
            dock.raise_()
            self.views["disassembly"].show_pc()

    def goto_source(self, path: str, line: int):
        ed = self.win._editor_for_file(path)
        if ed is not None:
            ed.goto_line(int(line) - 1)


# ====================================================================== start a session (for language plugins)
def start_session(win, s, title: str = "") -> object:
    """Wire a ready debug session (e.g. nativedbg.asm_debug_session) into the IDE like F5 does, start it."""
    win.locals.clear()
    win.callstack.clear()
    win.dock_output.show()
    win.log(f"------ Debug: {title or getattr(s, 'launch_args', {}).get('program', '')} ------")
    s.output.connect(win._append_output)
    s.stopped.connect(lambda info: win._on_stopped(info))
    s.resumed.connect(lambda: win._on_resumed())
    from ..tools import on_eval_result
    s.evalResult.connect(lambda txt: on_eval_result(win, txt) or win.immediate.show_result(txt))
    s.finished.connect(lambda code, s=s: win._on_finished(code, s))
    s.failed.connect(lambda err: win.log(f"*** Error: {err}"))
    win.session = s
    s.start()
    win._set_run_state("Running...")
    win._update_actions()
    return s


# ====================================================================== install
def _dock(win, title: str, name: str, widget) -> QDockWidget:
    dock = QDockWidget(title, win)
    dock.setObjectName(name)
    dock.setWidget(widget)
    win.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
    anchor = getattr(win, "dock_stack", None)
    if anchor is not None:
        win.tabifyDockWidget(anchor, dock)
    dock.hide()
    return dock


def install(win) -> None:
    hub = NativeHub(win)
    win.native_debug = hub
    for key, cls, name in (("registers", RegistersView, "Registers"), ("disassembly", DisassemblyView, "Disassembly"),
                           ("memory", MemoryView, "Memory1"), ("stack", StackView, "NativeStack")):
        view = cls(hub)
        hub.add(key, view, _dock(win, cls.title, name, view))
    win.dock_registers = hub.docks["registers"]
    win.dock_disassembly = hub.docks["disassembly"]
    win.dock_memory = hub.docks["memory"]
    win.dock_native_stack = hub.docks["stack"]

    orig_stopped, orig_resumed, orig_finished = win._on_stopped, win._on_resumed, win._on_finished

    def on_stopped(info):
        orig_stopped(info)
        try:
            hub.on_stopped(info)
        except Exception as e:  # noqa: BLE001 - the windows must never break debugging
            win.log(f"[native debug] {e}")
    win._on_stopped = on_stopped

    def on_resumed():
        orig_resumed()
        hub.on_resumed()
    win._on_resumed = on_resumed

    def on_finished(code, session=None):
        orig_finished(code, session)
        if win.session is None:
            hub.on_finished()
    win._on_finished = on_finished
    QTimer.singleShot(60, lambda: _build_menu(win, hub))      # after debug_views' Debug > Windows


def _build_menu(win, hub):
    menu = next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == "Debug"), None)
    if menu is None:
        return
    a_into = QAction("Step Into &Instruction", win)
    a_into.setShortcut(QKeySequence("Ctrl+Alt+F11"))
    a_into.triggered.connect(lambda: hub.step(False))
    a_over = QAction("Step Over Instructio&n", win)
    a_over.setShortcut(QKeySequence("Ctrl+Alt+F10"))
    a_over.triggered.connect(lambda: hub.step(True))
    a_dis = QAction("&Go To Disassembly", win)
    a_dis.triggered.connect(hub.show_disassembly)
    win.a_step_into_instruction, win.a_step_over_instruction, win.a_goto_disassembly = a_into, a_over, a_dis
    anchor = getattr(win, "a_step_out", None)
    acts = menu.actions()
    after = next((i for i, a in enumerate(acts) if a is anchor), None)
    before = acts[after + 1] if after is not None and after + 1 < len(acts) else None
    for a in (a_into, a_over, a_dis):
        menu.insertAction(before, a) if before is not None else menu.addAction(a)
    windows = next((a.menu() for a in menu.actions() if a.menu() is not None
                    and a.text().replace("&", "") == "Windows"), None)
    if windows is None:
        windows = menu.addMenu("&Windows")
    windows.addSeparator()
    for key, keys in (("registers", "Alt+5"), ("memory", "Alt+6"), ("disassembly", "Alt+8"), ("stack", "")):
        act = hub.docks[key].toggleViewAction()
        if keys:
            act.setShortcut(QKeySequence(keys))
        windows.addAction(act)


__all__ = ["install", "start_session", "NativeHub", "RegistersView", "DisassemblyView", "MemoryView", "StackView"]
