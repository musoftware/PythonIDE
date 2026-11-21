"""Firmware Analysis view (PyQt6 - the only Qt module of radide/firmware/analysis): a document tab with

* Overview  - container, memory map, CPU guesses (with evidence) and base address guesses; CPU / base can be
  changed and the analysis re-run;
* Entropy   - entropy graph over the image coloured by region class (empty / text / calibration-like / code-like /
  compressed-encrypted-like); click = address, double-click = show in the hex editor; the region table;
* Strings   - ASCII / UTF-16 strings with identification-like tags, filter;
* Disassembly - Capstone listing at any address, labels, branch / data references; "References to" lists the
  instructions that use an address (e.g. a calibration table); double-click follows a target;
* Ghidra    - headless Ghidra run with the detected language / base: function list + decompiled C (read-only);
* Memory map - segments, gaps, ELF sections and symbols.

The heavy work (analysis, cross reference index, Ghidra) runs in a worker thread; the UI polls it.
A one-time notice bar reminds that edits to vehicle software can affect safety, warranty and emissions legality.
"""
from __future__ import annotations

import threading
from pathlib import Path

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QSplitter,
                             QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from ..formats import load
from ..formats.memmap import MemoryMap
from . import arch as _arch
from . import disasm, entropy

COLORS = {"empty": "#C8C8C8", "text": "#2E8B57", "calibration": "#E0A800", "data": "#6A8CAF", "code": "#C0392B",
          "random": "#6C3483"}
NOTICE = ("Edits to vehicle software can affect safety, warranty and emissions legality. Keep the original and "
          "follow your local laws.")


def _tr(text: str) -> str:
    """The IDE's UI translation for text painted by hand (QPainter is not translated automatically)."""
    try:
        from ...i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001 - no catalog: English
        return text


def _mono() -> QFont:
    f = QFont("Consolas")
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setPointSize(9)
    return f


class _Job:
    """A function run in a thread; ``done`` / ``result`` / ``error`` are polled from the UI thread."""
    def __init__(self, fn, *args, **kw):
        self.done = False
        self.result = None
        self.error = ""
        self.messages: list[str] = []

        def run():
            try:
                self.result = fn(*args, **kw)
            except Exception as e:  # noqa: BLE001 - reported in the view
                import traceback
                self.error = f"{type(e).__name__}: {e}"
                self.messages.append(traceback.format_exc())
            self.done = True
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()


class EntropyGraph(QWidget):
    """Entropy per block (0..8 bits) as bars coloured by region class."""
    clicked = pyqtSignal(int)            # offset
    activated = pyqtSignal(int)          # offset (double-click)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile: list[float] = []
        self.kinds: list[str] = []
        self.block = 1024
        self.size = 0
        self.base = 0
        self.marker = -1
        self.setMinimumHeight(170)
        self.setMouseTracking(True)
        self.setToolTip("Entropy (bits per byte) over the image. Click: address; double-click: hex editor.")

    def set_data(self, profile, regions, block: int, size: int, base: int):
        self.profile = list(profile)
        self.block = block
        self.size = size
        self.base = base
        kinds = []
        for i in range(len(self.profile)):
            off = i * block
            k = next((r.kind for r in regions if r.start <= off < r.end), "data")
            kinds.append(k)
        self.kinds = kinds
        self.update()

    def _plot(self) -> QRectF:
        return QRectF(36, 8, max(10, self.width() - 44), max(10, self.height() - 34))

    def offset_at(self, x: float) -> int:
        r = self._plot()
        if not self.profile:
            return 0
        frac = min(max((x - r.left()) / r.width(), 0.0), 0.999999)
        return int(frac * len(self.profile)) * self.block

    def paintEvent(self, _e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#FFFFFF"))
        r = self._plot()
        p.setPen(QPen(QColor("#888888")))
        p.drawRect(r)
        p.setFont(QFont("Segoe UI", 7))
        for v in (0, 2, 4, 6, 8):
            y = r.bottom() - r.height() * v / 8
            p.setPen(QPen(QColor("#E5E5E5")))
            p.drawLine(int(r.left()) + 1, int(y), int(r.right()) - 1, int(y))
            p.setPen(QPen(QColor("#555555")))
            p.drawText(2, int(y) + 4, f"{v}")
        n = len(self.profile)
        if n:
            w = r.width() / n
            for i, h in enumerate(self.profile):
                x = r.left() + i * w
                bh = max(r.height() * min(h, 8.0) / 8, 2.0)       # empty areas stay visible as a thin bar
                p.fillRect(QRectF(x, r.bottom() - bh, max(w, 1.0), bh), QColor(COLORS.get(self.kinds[i], "#6A8CAF")))
            if self.marker >= 0:
                x = r.left() + (self.marker / self.block) * w
                p.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.DashLine))
                p.drawLine(int(x), int(r.top()), int(x), int(r.bottom()))
            p.setPen(QPen(QColor("#333333")))
            p.drawText(int(r.left()), int(r.bottom()) + 14, f"0x{self.base:X}")
            end = f"0x{self.base + self.size:X}"
            p.drawText(int(r.right()) - 8 * len(end), int(r.bottom()) + 14, end)
        else:
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, _tr("Analyzing..."))
        # legend
        x = int(r.left()) + 90
        for k in ("empty", "text", "calibration", "data", "code", "random"):
            p.fillRect(x, int(r.bottom()) + 6, 10, 10, QColor(COLORS[k]))
            p.setPen(QPen(QColor("#333333")))
            label = _tr({"empty": "empty", "text": "text", "calibration": "calibration-like", "data": "data",
                         "code": "code-like", "random": "compressed/encrypted-like"}[k])
            p.drawText(x + 13, int(r.bottom()) + 15, label)
            x += 18 + 6 * len(label)
        p.end()

    def mousePressEvent(self, e):
        off = self.offset_at(e.position().x())
        self.marker = off
        self.update()
        self.clicked.emit(off)

    def mouseDoubleClickEvent(self, e):
        self.activated.emit(self.offset_at(e.position().x()))

    def mouseMoveEvent(self, e):
        if self.profile:
            off = self.offset_at(e.position().x())
            i = min(len(self.profile) - 1, off // self.block)
            self.setToolTip(f"0x{self.base + off:X}  entropy {self.profile[i]:.2f}  "
                            f"{entropy.CLASSES.get(self.kinds[i], '')}")


def _item(text, data=None) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if data is not None:
        it.setData(Qt.ItemDataRole.UserRole, data)
    return it


def _table(headers: list[str]) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    t.setProperty("i18n_skip_items", True)
    return t


class FirmwareAnalysisView(QWidget):
    """Document tab: analysis of one firmware file (never modifies it)."""
    message = pyqtSignal(str)
    hexRequested = pyqtSignal(int)          # address

    def __init__(self, path=None, mm: MemoryMap | None = None, base: int | None = None, arch: str = "",
                 parent=None, labels: dict[int, str] | None = None, workdir=None):
        super().__init__(parent)
        self.path = Path(path) if path else None
        self.read_only = True
        self.user_base = base
        self.user_arch = arch
        self.labels: dict[int, str] = dict(labels or {})
        self.workdir = Path(workdir) if workdir else None
        if mm is None:
            raw_base = base if base is not None else 0
            mm = load(self.path, base=raw_base)
        self.mm0 = mm                       # as loaded (raw files at 0 or at the user's base)
        self.mm = mm
        self.analysis = None
        self.xrefs: disasm.XrefIndex | None = None
        self._job: _Job | None = None
        self._xjob: _Job | None = None
        self._gjob: _Job | None = None
        self.ghidra_result = None
        self._build()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._poll)
        self.reanalyze()

    # ------------------------------------------------------------------ framework (IDE tab protocol)
    def is_modified(self) -> bool:
        return False

    def save(self) -> bool:
        return True

    @property
    def ready(self) -> bool:
        return self.analysis is not None

    # ------------------------------------------------------------------ UI
    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.notice = QWidget()
        nl = QHBoxLayout(self.notice)
        nl.setContentsMargins(6, 3, 6, 3)
        self.notice.setStyleSheet("background:#FFF4CE; border:1px solid #E0C060;")
        lab = QLabel(NOTICE)
        lab.setWordWrap(True)
        nl.addWidget(lab, 1)
        b = QPushButton("I understand")
        b.clicked.connect(self._accept_notice)
        nl.addWidget(b)
        lay.addWidget(self.notice)
        self.notice.setVisible(not self._notice_accepted())
        try:
            from ..project import notice as _notice
            _notice.on_accepted(self.notice)        # accepted elsewhere -> hide this bar too
        except Exception:  # noqa: BLE001 - the ECU project slice is optional
            pass

        bar = QHBoxLayout()
        self.title = QLabel(self.path.name if self.path else "Firmware")
        self.title.setStyleSheet("font-weight:bold")
        bar.addWidget(self.title)
        bar.addSpacing(12)
        bar.addWidget(QLabel("CPU:"))
        self.arch_combo = QComboBox()
        self.arch_combo.setMaximumWidth(300)
        self.arch_combo.addItem("Auto-detect", "")
        for k, v in _arch.ARCH_INFO.items():
            self.arch_combo.addItem(v["label"], k)
        for k in ("mips", "x86", "arm64"):
            self.arch_combo.addItem({"mips": "MIPS (big endian)", "x86": "x86 (32-bit)", "arm64": "ARM64"}[k], k)
        i = self.arch_combo.findData(self.user_arch)
        self.arch_combo.setCurrentIndex(max(0, i))
        bar.addWidget(self.arch_combo)
        bar.addWidget(QLabel("Base:"))
        self.base_edit = QLineEdit("" if self.user_base is None else f"0x{self.user_base:X}")
        self.base_edit.setPlaceholderText("auto")
        self.base_edit.setMinimumWidth(100)
        self.base_edit.setMaximumWidth(130)
        bar.addWidget(self.base_edit)
        self.btn_analyze = QPushButton("Re-analyze")
        self.btn_analyze.clicked.connect(self.reanalyze_from_ui)
        bar.addWidget(self.btn_analyze)
        self.btn_hex = QPushButton("Open in Hex Editor")
        self.btn_hex.clicked.connect(lambda: self.hexRequested.emit(self.base_address()))
        bar.addWidget(self.btn_hex)
        self.btn_report = QPushButton("Save Report...")
        self.btn_report.clicked.connect(self.save_report_dialog)
        bar.addWidget(self.btn_report)
        bar.addStretch(1)
        self.status = QLabel("")
        bar.addWidget(self.status)
        lay.addLayout(bar)

        self.tabs = QTabWidget()
        lay.addWidget(self.tabs, 1)

        # overview
        ov = QWidget()
        ol = QVBoxLayout(ov)
        sp = QSplitter(Qt.Orientation.Vertical)
        self.cpu_table = _table(["CPU (guess)", "Confidence", "Evidence"])
        self.cpu_table.itemDoubleClicked.connect(self._on_cpu_pick)
        self.base_table = _table(["Load address (guess)", "Confidence", "Why"])
        self.base_table.itemDoubleClicked.connect(self._on_base_pick)
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setFont(_mono())
        self.summary.setProperty("i18n_skip", True)
        sp.addWidget(self.cpu_table)
        sp.addWidget(self.base_table)
        sp.addWidget(self.summary)
        sp.setSizes([150, 120, 300])
        ol.addWidget(QLabel("Double-click a CPU or a load address to use it."))
        ol.addWidget(sp)
        self.tabs.addTab(ov, "Overview")

        # entropy
        en = QWidget()
        el = QVBoxLayout(en)
        self.graph = EntropyGraph()
        self.graph.clicked.connect(lambda off: self.status.setText(f"0x{self.base_address() + off:X}"))
        self.graph.activated.connect(lambda off: self.hexRequested.emit(self.base_address() + off))
        el.addWidget(self.graph, 2)
        self.region_table = _table(["Start", "End", "Size", "Region", "Entropy"])
        self.region_table.itemDoubleClicked.connect(self._on_region)
        el.addWidget(self.region_table, 3)
        self.tabs.addTab(en, "Entropy")

        # strings
        st = QWidget()
        sl = QVBoxLayout(st)
        row = QHBoxLayout()
        self.str_filter = QLineEdit()
        self.str_filter.setPlaceholderText("Filter strings")
        self.str_filter.textChanged.connect(self._fill_strings)
        self.str_ids = QCheckBox("Identification-like only")
        self.str_ids.toggled.connect(self._fill_strings)
        row.addWidget(self.str_filter, 1)
        row.addWidget(self.str_ids)
        sl.addLayout(row)
        self.str_table = _table(["Address", "Encoding", "Looks like", "Text"])
        self.str_table.itemDoubleClicked.connect(self._on_string)
        sl.addWidget(self.str_table)
        sl.addWidget(QLabel("Tags are generic shapes (letters + digit groups, long numbers, versions, dates) - "
                            "RAD IDE has no manufacturer database."))
        self.tabs.addTab(st, "Strings")

        # disassembly
        ds = QWidget()
        dl = QVBoxLayout(ds)
        row = QHBoxLayout()
        row.addWidget(QLabel("Address:"))
        self.dis_addr = QLineEdit()
        self.dis_addr.setMaximumWidth(140)
        self.dis_addr.returnPressed.connect(self.show_disassembly_from_ui)
        row.addWidget(self.dis_addr)
        b = QPushButton("Go")
        b.clicked.connect(self.show_disassembly_from_ui)
        row.addWidget(b)
        self.dis_entry = QComboBox()
        self.dis_entry.setMinimumWidth(220)
        self.dis_entry.activated.connect(lambda _i: self._go_entry())
        row.addWidget(QLabel("Entry points:"))
        row.addWidget(self.dis_entry)
        b = QPushButton("Show in Hex")
        b.clicked.connect(lambda: self.hexRequested.emit(self._dis_start))
        row.addWidget(b)
        self.dis_pcode = QCheckBox("Show P-code")
        self.dis_pcode.setToolTip("Ghidra's intermediate language under every instruction (SLEIGH CPUs)")
        self.dis_pcode.toggled.connect(lambda _on: self.show_disassembly(self._dis_start) if self._dis_lines else None)
        row.addWidget(self.dis_pcode)
        row.addStretch(1)
        self.dis_backend = QLabel("")
        self.dis_backend.setProperty("i18n_skip", True)
        row.addWidget(self.dis_backend)
        dl.addLayout(row)
        sp2 = QSplitter(Qt.Orientation.Horizontal)
        self.listing = QPlainTextEdit()
        self.listing.setReadOnly(True)
        self.listing.setFont(_mono())
        self.listing.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.listing.setProperty("i18n_skip", True)
        self.listing.mouseDoubleClickEvent = self._listing_dclick
        sp2.addWidget(self.listing)
        xr = QWidget()
        xl = QVBoxLayout(xr)
        xl.setContentsMargins(0, 0, 0, 0)
        row2 = QHBoxLayout()
        self.xref_addr = QLineEdit()
        self.xref_addr.setPlaceholderText("address, e.g. 0x0800A000")
        self.xref_addr.returnPressed.connect(self.find_xrefs_from_ui)
        b = QPushButton("References to")
        b.clicked.connect(self.find_xrefs_from_ui)
        row2.addWidget(self.xref_addr, 1)
        row2.addWidget(b)
        xl.addLayout(row2)
        self.xref_list = QListWidget()
        self.xref_list.setProperty("i18n_skip_items", True)
        self.xref_list.itemDoubleClicked.connect(lambda it: self.show_disassembly(it.data(Qt.ItemDataRole.UserRole)))
        xl.addWidget(self.xref_list)
        self.xref_status = QLabel("")
        self.xref_status.setWordWrap(True)
        xl.addWidget(self.xref_status)
        sp2.addWidget(xr)
        sp2.setSizes([700, 260])
        dl.addWidget(sp2, 1)
        self.tabs.addTab(ds, "Disassembly")
        self._dis_start = 0
        self._dis_lines: list = []
        self._dis_labels: dict[int, str] = {}

        # ghidra
        gh = QWidget()
        gl = QVBoxLayout(gh)
        row = QHBoxLayout()
        self.btn_ghidra = QPushButton("Analyze in Ghidra")
        self.btn_ghidra.clicked.connect(self.run_ghidra)
        row.addWidget(self.btn_ghidra)
        self.ghidra_status = QLabel("")
        self.ghidra_status.setWordWrap(True)
        row.addWidget(self.ghidra_status, 1)
        gl.addLayout(row)
        sp3 = QSplitter(Qt.Orientation.Horizontal)
        self.gfuncs = QListWidget()
        self.gfuncs.setProperty("i18n_skip_items", True)
        self.gfuncs.currentItemChanged.connect(self._on_gfunc)
        self.gcode = QPlainTextEdit()
        self.gcode.setReadOnly(True)
        self.gcode.setFont(_mono())
        self.gcode.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.gcode.setProperty("i18n_skip", True)
        sp3.addWidget(self.gfuncs)
        sp3.addWidget(self.gcode)
        sp3.setSizes([240, 700])
        gl.addWidget(sp3, 1)
        self.tabs.addTab(gh, "Ghidra")

        # memory map
        mp = QWidget()
        ml = QVBoxLayout(mp)
        self.seg_table = _table(["Start", "End", "Size", "Name / kind"])
        ml.addWidget(QLabel("Segments and gaps"))
        ml.addWidget(self.seg_table, 1)
        self.sym_table = _table(["Address", "Size", "Kind", "Symbol / section"])
        self.sym_table.itemDoubleClicked.connect(lambda it: self.show_disassembly(
            self.sym_table.item(it.row(), 0).data(Qt.ItemDataRole.UserRole)))
        ml.addWidget(QLabel("ELF sections and symbols"))
        ml.addWidget(self.sym_table, 1)
        self.tabs.addTab(mp, "Memory Map")

    # ------------------------------------------------------------------ notice
    @staticmethod
    def _notice_accepted() -> bool:
        try:
            from ..project import notice
            return notice.accepted()
        except Exception:  # noqa: BLE001 - the ECU project slice is optional
            from PyQt6.QtCore import QSettings
            return QSettings().value("firmware/safetyNoticeAccepted", False) in (True, "true", "1", 1)

    def _accept_notice(self) -> None:
        try:
            from ..project import notice
            notice.set_accepted(True)
        except Exception:  # noqa: BLE001
            from PyQt6.QtCore import QSettings
            QSettings().setValue("firmware/safetyNoticeAccepted", True)
        self.notice.setVisible(False)

    # ------------------------------------------------------------------ analysis
    def base_address(self) -> int:
        """Address of offset 0 of the flat image (raw files are moved to the guessed / chosen base)."""
        return self.mm.min_address

    def reanalyze_from_ui(self) -> None:
        t = self.base_edit.text().strip()
        try:
            self.user_base = int(t, 0) if t else None
        except ValueError:
            self.status.setText("Invalid base address")
            return
        self.user_arch = self.arch_combo.currentData() or ""
        self.reanalyze()

    def reanalyze(self) -> None:
        from .report import analyze
        if self._job is not None and not self._job.done:
            return
        mm = self.mm0
        if mm.meta.get("format", "raw") == "raw" and self.user_base is not None and mm.min_address != self.user_base:
            mm = mm.relocate(self.user_base - mm.min_address)
        self.mm = mm
        self.analysis = None
        self.xrefs = None
        self.status.setText("Analyzing...")
        self._job = _Job(analyze, mm, None, self.user_arch)
        self._timer.start()

    def _poll(self) -> None:
        busy = False
        if self._job is not None:
            if self._job.done:
                job, self._job = self._job, None
                if job.error:
                    self.status.setText("Analysis failed: " + job.error)
                    self.message.emit("[firmware] " + "\n".join(job.messages))
                else:
                    self._apply(job.result)
            else:
                busy = True
        if self._xjob is not None:
            if self._xjob.done:
                job, self._xjob = self._xjob, None
                self.xrefs = job.result if not job.error else disasm.XrefIndex()
                self.xref_status.setText(f"Index: {self.xrefs.instructions:,} instructions, "
                                         f"{len(self.xrefs.refs):,} referenced addresses")
                if self.xref_addr.text().strip():
                    self.find_xrefs_from_ui()
            else:
                busy = True
        if self._gjob is not None:
            if self._gjob.done:
                job, self._gjob = self._gjob, None
                self._apply_ghidra(job.result if not job.error else None, job.error)
            else:
                busy = True
                if self._gjob.messages:
                    self.ghidra_status.setText(self._gjob.messages[-1])
        if not busy:
            self._timer.stop()

    def _apply(self, res) -> None:
        self.analysis = res
        if self.mm0.meta.get("format", "raw") == "raw" and self.user_base is None and res.base != self.mm.min_address:
            self.mm = self.mm0.relocate(res.base - self.mm0.min_address)
        a = self.current_arch()
        self.status.setText(f"{_arch.ARCH_INFO.get(a, {}).get('label', a or 'unknown CPU')}  base 0x{self.base_address():X}")
        if not self.base_edit.text().strip():
            self.base_edit.setPlaceholderText(f"auto (0x{self.base_address():X})")
        # overview
        self.cpu_table.setRowCount(0)
        for g in [x for x in res.detection.arches if x.confidence >= 0.01][:10]:
            r = self.cpu_table.rowCount()
            self.cpu_table.insertRow(r)
            self.cpu_table.setItem(r, 0, _item(g.label, g.arch))
            self.cpu_table.setItem(r, 1, _item(f"{g.confidence:.0%}"))
            self.cpu_table.setItem(r, 2, _item("; ".join(g.evidence)))
        self.cpu_table.resizeColumnsToContents()
        self.base_table.setRowCount(0)
        for b in res.detection.bases[:8]:
            r = self.base_table.rowCount()
            self.base_table.insertRow(r)
            self.base_table.setItem(r, 0, _item(f"0x{b.base:08X}", b.base))
            self.base_table.setItem(r, 1, _item(f"{b.confidence:.0%}"))
            self.base_table.setItem(r, 2, _item(b.reason))
        self.base_table.resizeColumnsToContents()
        self.summary.setPlainText(res.text())
        # entropy
        base = self.base_address()
        self.graph.set_data(res.profile, res.regions, res.block, len(res.flat), base)
        self.region_table.setRowCount(0)
        for rg in res.regions[:5000]:
            r = self.region_table.rowCount()
            self.region_table.insertRow(r)
            self.region_table.setItem(r, 0, _item(f"0x{base + rg.start:08X}", base + rg.start))
            self.region_table.setItem(r, 1, _item(f"0x{base + rg.end - 1:08X}"))
            self.region_table.setItem(r, 2, _item(f"{rg.size:,}"))
            self.region_table.setItem(r, 3, _item(rg.label))
            self.region_table.setItem(r, 4, _item(f"{abs(rg.entropy):.2f}"))
        # strings
        self._fill_strings()
        # memory map
        self._fill_memmap()
        # disassembly entry points
        self.dis_entry.clear()
        for e in res.entry_points()[:200]:
            self.dis_entry.addItem(f"0x{e:X}  {self.labels.get(e, '')}".rstrip(), e)
        for s in self.mm.symbols[:2000]:
            if s.kind == "func":
                self.dis_entry.addItem(f"0x{s.address:X}  {s.name}", s.address)
        start = res.entry_points()[0] if res.entry_points() else base
        self.show_disassembly(start)
        self.message.emit(f"[firmware] {self.path.name if self.path else 'image'}: {self.status.text()}")

    def current_arch(self) -> str:
        if self.user_arch:
            return self.user_arch
        return self.analysis.arch if self.analysis is not None else ""

    def _fill_strings(self) -> None:
        if self.analysis is None:
            return
        flt = self.str_filter.text().strip().lower()
        only = self.str_ids.isChecked()
        base = self.base_address()
        self.str_table.setRowCount(0)
        rows = [s for s in self.analysis.strings if (not only or s.tags) and (not flt or flt in s.text.lower())]
        rows.sort(key=lambda s: (not s.tags, s.offset))
        self.str_table.setRowCount(min(len(rows), 5000))
        for r, s in enumerate(rows[:5000]):
            self.str_table.setItem(r, 0, _item(f"0x{base + s.offset:08X}", base + s.offset))
            self.str_table.setItem(r, 1, _item(s.encoding))
            self.str_table.setItem(r, 2, _item(", ".join(s.tags)))
            self.str_table.setItem(r, 3, _item(s.text[:200]))

    def _fill_memmap(self) -> None:
        mm = self.mm
        self.seg_table.setRowCount(0)
        rows = [(s.address, s.end, s.name or "segment") for s in mm.segments] + \
               [(a, b, "gap") for a, b in mm.gaps()]
        for a, b, name in sorted(rows):
            r = self.seg_table.rowCount()
            self.seg_table.insertRow(r)
            self.seg_table.setItem(r, 0, _item(f"0x{a:08X}", a))
            self.seg_table.setItem(r, 1, _item(f"0x{b - 1:08X}"))
            self.seg_table.setItem(r, 2, _item(f"{b - a:,}"))
            self.seg_table.setItem(r, 3, _item(name))
        self.sym_table.setRowCount(0)
        items = [(s.address, len(s), "section " + s.flags, s.name) for s in mm.sections] + \
                [(s.address, s.size, s.kind, s.name) for s in mm.symbols]
        self.sym_table.setRowCount(min(len(items), 5000))
        for r, (a, n, k, name) in enumerate(items[:5000]):
            self.sym_table.setItem(r, 0, _item(f"0x{a:08X}", a))
            self.sym_table.setItem(r, 1, _item(f"{n:,}"))
            self.sym_table.setItem(r, 2, _item(k))
            self.sym_table.setItem(r, 3, _item(name))

    # ------------------------------------------------------------------ navigation
    def _on_cpu_pick(self, it) -> None:
        a = self.cpu_table.item(it.row(), 0).data(Qt.ItemDataRole.UserRole)
        i = self.arch_combo.findData(a)
        if i >= 0:
            self.arch_combo.setCurrentIndex(i)
        self.reanalyze_from_ui()

    def _on_base_pick(self, it) -> None:
        b = self.base_table.item(it.row(), 0).data(Qt.ItemDataRole.UserRole)
        self.base_edit.setText(f"0x{b:X}")
        self.reanalyze_from_ui()

    def _on_region(self, it) -> None:
        self.hexRequested.emit(self.region_table.item(it.row(), 0).data(Qt.ItemDataRole.UserRole))

    def _on_string(self, it) -> None:
        self.hexRequested.emit(self.str_table.item(it.row(), 0).data(Qt.ItemDataRole.UserRole))

    def _go_entry(self) -> None:
        a = self.dis_entry.currentData()
        if a is not None:
            self.show_disassembly(a)

    def show_disassembly_from_ui(self) -> None:
        t = self.dis_addr.text().strip()
        try:
            self.show_disassembly(int(t, 0) if t else self.base_address())
        except ValueError:
            self.listing.setPlainText(f"Invalid address: {t}")

    def show_disassembly(self, address: int | None, length: int = 0x600) -> list:
        if address is None:
            return []
        a = self.current_arch()
        self._dis_start = address
        self.dis_addr.setText(f"0x{address:X}")
        self.dis_backend.setText(f"Decoder: {disasm.backend_label(a)}")
        sleigh = disasm.backend(a) == "sleigh"
        self.dis_pcode.setEnabled(sleigh)
        if not disasm.supported(a):
            self.listing.setPlainText(disasm.unsupported_reason(a) + "\n\nThe Ghidra tab can analyze this CPU when "
                                      "Ghidra knows it.")
            self._dis_lines = []
            return []
        try:
            lines = disasm.disassemble(self.mm, a, address, length, max_lines=1500,
                                       pcode=sleigh and self.dis_pcode.isChecked())
        except ValueError as e:
            self.listing.setPlainText(str(e))
            return []
        syms = {s.address: s.name for s in self.mm.symbols}
        syms.update(self.labels)
        labels = disasm.auto_labels(lines, syms)
        width = 8 if self.mm.max_address > 0xFFFF else 4
        out = []
        rows = []
        for ln in lines:
            if ln.address in labels:
                out.append("")
                out.append(f"{labels[ln.address]}:")
                rows += [None, None]
            out.append("    " + ln.text(labels, width))
            rows.append(ln)
            for t in ln.pcode:
                out.append("              | " + t)
                rows.append(None)
        self._dis_lines = rows
        self._dis_labels = labels
        self.listing.setPlainText("\n".join(out))
        if self.xrefs is None and self._xjob is None:
            self._start_xrefs()
        return lines

    def _listing_dclick(self, e) -> None:
        QPlainTextEdit.mouseDoubleClickEvent(self.listing, e)
        n = self.listing.cursorForPosition(e.position().toPoint()).blockNumber()
        if 0 <= n < len(self._dis_lines) and self._dis_lines[n] is not None:
            ln = self._dis_lines[n]
            if ln.target is not None:
                self.show_disassembly(ln.target)
            elif ln.refs:
                self.xref_addr.setText(f"0x{ln.refs[-1]:X}")
                self.hexRequested.emit(ln.refs[-1])

    def _start_xrefs(self) -> None:
        a = self.current_arch()
        if not disasm.supported(a) or self.analysis is None:
            return
        ranges = disasm.code_ranges(self.mm, self.analysis.regions, self.base_address()) or \
            [(s.address, s.end) for s in self.mm.segments]
        try:
            ranges = disasm.extend_to_entries(ranges, self.analysis.entry_points())
        except Exception:  # noqa: BLE001 - entry points are a hint
            pass
        self.xref_status.setText("Building the reference index...")
        self._xjob = _Job(disasm.build_xrefs, self.mm, a, ranges)
        self._timer.start()

    def find_xrefs_from_ui(self) -> list:
        t = self.xref_addr.text().strip()
        try:
            addr = int(t, 0)
        except ValueError:
            self.xref_status.setText("Enter an address (0x...)")
            return []
        return self.find_xrefs(addr)

    def find_xrefs(self, addr: int, size: int = 1) -> list:
        self.xref_list.clear()
        if self.xrefs is None:
            if self._xjob is None:
                self._start_xrefs()
            self.xref_status.setText("Building the reference index... (the list fills when it is ready)")
            return []
        hits = self.xrefs.to(addr, size)
        for src, kind in hits:
            it = QListWidgetItem(f"0x{src:08X}  {kind}")
            it.setData(Qt.ItemDataRole.UserRole, src)
            self.xref_list.addItem(it)
        self.xref_status.setText(f"{len(hits)} reference(s) to 0x{addr:X}")
        return hits

    # ------------------------------------------------------------------ Ghidra
    def run_ghidra(self) -> None:
        from . import ghidra
        if self._gjob is not None or self.analysis is None:
            return
        ok, info = ghidra.available()
        if not ok:
            self.ghidra_status.setText(info)
            return
        a = self.current_arch()
        if not ghidra.language_for(a) and self.mm0.meta.get("format") != "elf":
            self.ghidra_status.setText(f"Ghidra has no language for this CPU ({a or 'unknown'}).")
            return
        import tempfile
        work = self.workdir or Path(tempfile.mkdtemp(prefix="radide-fw-"))
        work.mkdir(parents=True, exist_ok=True)
        elf = self.mm0.meta.get("format") == "elf" and self.path is not None
        if elf:
            binary, raw, base = self.path, False, None
        else:
            binary = work / "image.bin"
            binary.write_bytes(self.analysis.flat)
            raw, base = True, self.base_address()
        self.ghidra_status.setText(f"Running Ghidra ({ghidra.language_for(a) or 'ELF loader'}, base "
                                   f"{'from ELF' if base is None else f'0x{base:X}'}) ... this can take minutes.")
        self.btn_ghidra.setEnabled(False)
        job = _Job(ghidra.analyze, binary, work, a, base, raw, self.analysis.entry_points(), 200, 1800, None)
        self._gjob = job
        self._timer.start()

    def _apply_ghidra(self, res, error: str = "") -> None:
        self.btn_ghidra.setEnabled(True)
        if res is None or res.error:
            self.ghidra_status.setText("Ghidra: " + (error or (res.error if res else "failed")))
            return
        self.ghidra_result = res
        self.gfuncs.clear()
        for f in res.functions:
            it = QListWidgetItem(f"{f.name}  (0x{f.address:X})" + ("" if f.name in res.decompiled else "  -"))
            it.setData(Qt.ItemDataRole.UserRole, f.name)
            self.gfuncs.addItem(it)
        self.gcode.setPlainText(res.c_text())
        self.ghidra_status.setText(f"Ghidra ({res.language}): {len(res.functions)} functions, "
                                   f"{len(res.decompiled)} decompiled in {res.seconds:.0f} s (read-only).")

    def _on_gfunc(self, cur, _prev) -> None:
        if cur is None:
            return
        name = cur.data(Qt.ItemDataRole.UserRole)
        doc = self.gcode.document()
        c = doc.find(f"// ---- {name} @")
        if not c.isNull():
            self.gcode.setTextCursor(c)
            self.gcode.centerCursor()

    # ------------------------------------------------------------------ report
    def save_report_dialog(self) -> None:
        if self.analysis is None:
            return
        start = str(self.path.with_suffix(".analysis.txt")) if self.path else "analysis.txt"
        fn, _ = QFileDialog.getSaveFileName(self, "Save Analysis Report", start, "Text (*.txt)")
        if fn:
            Path(fn).write_text(self.analysis.text() + "\n", encoding="utf-8")
            self.message.emit(f"[firmware] report saved: {fn}")
