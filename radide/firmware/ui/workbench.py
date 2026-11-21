"""Firmware & ECU workbench (Qt): one WinOLS-like layout for a firmware file or an ECU project.

    +-----------+---------------------------------------------+-------------+
    | Project   | [Getting Started|Hex|Map|2D|Disasm|Analysis] | Properties  |
    | original  |                                             |             |
    | working   |      hex view (radide/retro/rom/hexdoc)     |             |
    | versions  |      map editor / 2D / 3D                   |             |
    | maps      |                                             |             |
    | checksums |                                             |             |
    +-----------+---------------------------------------------+-------------+
    | Potential Maps | Differences | Checksum Report | Output                |
    +-----------------------------------------------------------------------+

The hex view, the map editor and the checksum fixer share one buffer (one undo stack). The original of an ECU
project is never written; EEPROM dumps and HEX / S-record files open read-only (Save Working Copy As... writes a
binary copy). Keys (docs/FIRMWARE.md "Keyboard"): F7 Build, Ctrl+M Find Maps, Ctrl+D Compare, Ctrl+Shift+A
Analyze, Ctrl+Shift+V Verify Checksums, K (hex view) map from the selection, + - = % T 2 3 in the map table.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, QRectF, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QPainter
from PyQt6.QtWidgets import (QApplication, QComboBox, QDockWidget, QFileDialog, QFormLayout, QFrame, QHBoxLayout,
                             QHeaderView, QInputDialog, QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox,
                             QPlainTextEdit, QPushButton, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
                             QTabWidget, QTextBrowser, QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import adapters as A
from . import eeprom as E
from .mapview import KEYS_HELP, MapEditor, WaveView

ROLE = Qt.ItemDataRole.UserRole
NOTICE_KEY = "firmware/safetyNoticeAccepted"          # shared with radide/firmware/project/notice.py
NOTICE_TEXT = ("Edits to vehicle software can affect safety, warranty and emissions legality. Keep the original "
               "file, work only on units you own or may service, and follow your local laws.")
WORKBENCH_KEYS = [("F7", "Build (working copy + corrected checksums)"),
                  ("Ctrl+Shift+V", "Verify checksums"),
                  ("Ctrl+D", "Compare with the original / another file"),
                  ("Ctrl+M", "Find potential maps"),
                  ("Ctrl+Shift+A", "Analyze the file (CPU, entropy, strings)"),
                  ("K", "Hex view: new map from the selected bytes"),
                  ("Ctrl+G / Ctrl+F", "Hex view: go to offset / find")] + KEYS_HELP

TAB_START, TAB_HEX, TAB_MAP, TAB_2D, TAB_DISASM, TAB_ANALYSIS = range(6)


def _settings() -> QSettings:
    from PyQt6.QtCore import QCoreApplication
    org = QCoreApplication.organizationName() or "RADIDE"
    return QSettings(org, QCoreApplication.applicationName() or org)


def notice_accepted() -> bool:
    try:
        from ..project import notice
        return notice.accepted()
    except Exception:  # noqa: BLE001
        return _settings().value(NOTICE_KEY, False) in (True, "true", "1", 1)


def set_notice_accepted() -> None:
    try:
        from ..project import notice
        notice.set_accepted(True)
        return
    except Exception:  # noqa: BLE001
        pass
    _settings().setValue(NOTICE_KEY, True)


# ================================================================================== getting started
START_EN = """
<h2>Firmware &amp; ECU Workbench - getting started</h2>
<p>The workbench opens control-unit firmware dumps (<b>.bin .ori .mod</b>), Intel HEX / Motorola S-record files
(<b>.hex .s19</b>), A2L map definitions and serial EEPROM dumps (24Cxx / 93Cxx / 95xxx sizes) for analysis and
calibration-map editing.</p>
<ol>
<li><b>Start a project</b> - <i>Tools &gt; Firmware &amp; ECU &gt; New ECU Project...</i> copies your file into
<code>original/</code> (never written again) and makes a <b>working copy</b> in <code>work/</code>.</li>
<li><b>Analyze</b> (Ctrl+Shift+A) - size, CPU guess, entropy and strings show where code, data and empty space are.</li>
<li><b>Find maps</b> (Ctrl+M) - the <i>Potential Maps</i> panel lists tables with axes found by their shape.
Double-click one to open it in the <b>Map Editor</b>; <i>Add to Project Maps</i> keeps it with a name, factor and unit.
You can also select bytes in the hex view and press <b>K</b>, or import an <b>A2L</b> file.</li>
<li><b>Edit</b> - in the map table: <b>+ / -</b> one step, <b>Page Up / Page Down</b> ten steps, <b>=</b> set,
<b>%</b> percent; <b>T / 2 / 3</b> switch Text / 2D / 3D. Changed cells are bold red; Ctrl+Z undoes.</li>
<li><b>Checksums</b> (Ctrl+Shift+V) - the profiles of the project are verified; <i>Correct Checksums</i> recalculates
them in the working copy. Profiles are generic algorithms you confirm on your own original.</li>
<li><b>Compare</b> (Ctrl+D) - every changed byte against the original (or any file) in <i>Differences</i>.</li>
<li><b>Versions</b> - <i>Save Version</i> keeps a named snapshot; double-click a version to compare.</li>
<li><b>Build</b> (F7) - working copy + corrected checksums are written to <code>build/</code> with a report.</li>
</ol>
<p><b>Safety:</b> edits to vehicle software can affect safety, warranty and emissions legality. Keep the original,
work only on units you own or may service and follow your local laws. RAD IDE has no immobilizer, emissions-system
or odometer functions.</p>
<p>Practice with <i>New ECU Project (Demo Firmware)</i>: a synthetic image written by RAD IDE (no vehicle data).
The course <i>Help &gt; Tutorials &gt; Firmware &amp; ECU</i> explains every step.</p>
"""

START_AR = """
<div dir="rtl" align="right">
<h2>منضدة البرامج الثابتة ووحدات التحكم (ECU) - البداية</h2>
<p>المنضدة تفتح ملفات برامج وحدات التحكم (<b>.bin .ori .mod</b>) وملفات Intel HEX و Motorola S-record
(<b>.hex .s19</b>) وتعريفات الخرائط A2L وملفات ذاكرة EEPROM التسلسلية (أحجام 24Cxx و93Cxx و95xxx)
للتحليل وتعديل خرائط المعايرة.</p>
<ol>
<li><b>ابدأ مشروعًا</b> - <i>أدوات &gt; البرامج الثابتة و ECU &gt; مشروع ECU جديد...</i> ينسخ ملفك إلى
<code>original/</code> (ولا يُكتب فيه أبدًا بعد ذلك) ويعمل <b>نسخة عمل</b> في <code>work/</code>.</li>
<li><b>حلّل</b> (Ctrl+Shift+A) - الحجم وتخمين المعالج والإنتروبيا والنصوص توضح أين الكود والبيانات والمساحة الفارغة.</li>
<li><b>ابحث عن الخرائط</b> (Ctrl+M) - لوحة <i>الخرائط المحتملة</i> تعرض الجداول ذات المحاور التي وُجدت من شكلها.
انقر مرتين على واحدة لفتحها في <b>محرر الخرائط</b>، و<i>إضافة إلى خرائط المشروع</i> يحفظها باسم ومعامل ووحدة.
ويمكنك أيضًا تحديد بايتات في عارض الـ Hex والضغط على <b>K</b>، أو استيراد ملف <b>A2L</b>.</li>
<li><b>عدّل</b> - في جدول الخريطة: <b>+ / -</b> خطوة واحدة، <b>Page Up / Page Down</b> عشر خطوات، <b>=</b> تعيين قيمة،
<b>%</b> نسبة مئوية؛ <b>T / 2 / 3</b> للتبديل بين النص و2D و3D. الخلايا المعدلة تظهر بخط عريض أحمر، وCtrl+Z يتراجع.</li>
<li><b>المجاميع الاختبارية</b> (Ctrl+Shift+V) - يتم التحقق من ملفات تعريف المشروع؛ و<i>تصحيح المجاميع الاختبارية</i>
يعيد حسابها في نسخة العمل. ملفات التعريف خوارزميات عامة تتأكد منها على ملفك الأصلي.</li>
<li><b>قارن</b> (Ctrl+D) - كل بايت تغيّر مقارنةً بالأصل (أو بأي ملف) في لوحة <i>الفروق</i>.</li>
<li><b>الإصدارات</b> - <i>حفظ إصدار</i> يحتفظ بلقطة باسم؛ انقر مرتين على إصدار لمقارنته.</li>
<li><b>البناء</b> (F7) - نسخة العمل مع المجاميع الاختبارية المصححة تُكتب في <code>build/</code> مع تقرير.</li>
</ol>
<p><b>السلامة:</b> تعديل برامج المركبات قد يؤثر على السلامة والضمان وقانونية الانبعاثات. احتفظ بالملف الأصلي،
واعمل فقط على وحدات تملكها أو مسموح لك بصيانتها، والتزم بقوانين بلدك. لا يحتوي RAD IDE على أي وظائف لنظام منع
التشغيل (immobilizer) أو أنظمة الانبعاثات أو عداد المسافات.</p>
<p>تدرّب باستخدام <i>مشروع ECU جديد (برنامج تجريبي)</i>: صورة اصطناعية كتبها RAD IDE (بدون بيانات مركبات).
ودورة <i>تعليمات &gt; الدروس &gt; البرامج الثابتة و ECU</i> تشرح كل خطوة.</p>
</div>
"""


def _keys_html(arabic: bool) -> str:
    rows = "".join(f"<tr><td><code>{k}</code></td><td>{_tr(v) if arabic else v}</td></tr>" for k, v in WORKBENCH_KEYS)
    head = "اختصارات لوحة المفاتيح" if arabic else "Keyboard"
    return (f"<div dir='{'rtl' if arabic else 'ltr'}'><h3>{head}</h3>"
            f"<table cellpadding='3'>{rows}</table></div>")


def _tr(text: str) -> str:
    try:
        from ...i18n import tr
        return tr(text)
    except Exception:  # noqa: BLE001
        return text


def _retranslate(w) -> None:
    """Items added after the widget was shown: translate them now (the getters keep the English text)."""
    try:
        from ... import i18n
        if i18n.language() != "en":
            i18n.translate_widget(w)
    except Exception:  # noqa: BLE001
        pass


def _arabic() -> bool:
    try:
        from ...i18n import language
        return language() == "ar"
    except Exception:  # noqa: BLE001
        return False


class StartPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        bar.setContentsMargins(6, 4, 6, 0)
        bar.addStretch(1)
        self.b_en = QPushButton("English")
        self.b_ar = QPushButton("العربية")
        self.b_en.setProperty("i18n_skip", True)
        self.b_ar.setProperty("i18n_skip", True)
        self.b_en.clicked.connect(lambda: self.show_language(False))
        self.b_ar.clicked.connect(lambda: self.show_language(True))
        bar.addWidget(self.b_en)
        bar.addWidget(self.b_ar)
        lay.addLayout(bar)
        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(False)
        self.text.setProperty("i18n_skip", True)
        lay.addWidget(self.text, 1)
        self.show_language(_arabic())

    def show_language(self, arabic: bool) -> None:
        self.arabic = arabic
        self.text.setHtml((START_AR if arabic else START_EN) + _keys_html(arabic))
        self.text.setLayoutDirection(Qt.LayoutDirection.RightToLeft if arabic else Qt.LayoutDirection.LeftToRight)


# ================================================================================== analysis widgets
class EntropyBar(QWidget):
    offsetClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values: list[float] = []
        self.block = 4096
        self.setMinimumHeight(70)
        self.setToolTip("Entropy per block: low = empty / tables, middle = code / data, high = compressed / encrypted")

    def set_values(self, values, block: int) -> None:
        self.values, self.block = list(values), block
        self.update()

    def mousePressEvent(self, e):  # noqa: N802
        if self.values:
            i = int(e.position().x() / max(1, self.width()) * len(self.values))
            self.offsetClicked.emit(max(0, i) * self.block)

    def paintEvent(self, _e):  # noqa: N802
        p = QPainter(self)
        p.fillRect(self.rect(), self.palette().base())
        if not self.values:
            return
        w = self.width() / len(self.values)
        h = self.height() - 4
        for i, v in enumerate(self.values):
            c = QColor(70, 130, 220) if v < 0.35 else QColor(90, 190, 120) if v < 0.8 else QColor(230, 110, 90)
            p.fillRect(QRectF(i * w, 2 + h * (1 - v), max(1.0, w), h * v), c)


# ================================================================================== workbench
class _KeyFilter(QObject):
    """Workbench keys win over the IDE's shortcuts while the focus is inside the workbench."""

    def __init__(self, wb):
        super().__init__(wb)
        self.wb = wb

    def eventFilter(self, obj, e):  # noqa: N802
        t = e.type()
        if t not in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            return False
        fw = QApplication.focusWidget()
        if fw is None or not (fw is self.wb or self.wb.isAncestorOf(fw)):
            return False
        combo = QKeySequence(e.keyCombination()).toString()
        fn = self.wb.keys.get(combo)
        if fn is None:
            return False
        from PyQt6.QtWidgets import QAbstractSpinBox
        if isinstance(fw, (QLineEdit, QPlainTextEdit, QAbstractSpinBox)) and not fw.isReadOnly() and \
                not combo.startswith("F"):
            return False                     # text fields keep Ctrl+Z / Ctrl+D ... for themselves
        if t == QEvent.Type.ShortcutOverride:
            e.accept()
            return True
        if obj is fw:
            fn()
            return True
        return False


class FirmwareWorkbench(QMainWindow):
    """A document tab of the IDE (``is_modified`` / ``save`` / ``path`` like the other documents)."""
    modifiedChanged = pyqtSignal(bool)
    saved = pyqtSignal()
    message = pyqtSignal(str)
    openInIde = pyqtSignal(str, bool)       # path, read-only (handled by the IDE feature: hex editor tab)
    projectChanged = pyqtSignal()           # ecu.json / versions / maps changed (the IDE refreshes Solution Explorer)

    def __init__(self, path=None, project_folder=None, eeprom: bool | None = None, read_only: bool | None = None,
                 parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.setObjectName("FirmwareWorkbench")
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks)
        self.proj: A.EcuProject | None = None
        self.maps: list[A.MapDef] = []
        self.potential: list[A.MapDef] = []
        self.profiles: list[dict] = []
        self.diffs: list[tuple[int, int]] = []
        self.compare_label = "original"
        self.last_report: list[dict] = []
        self.keys: dict[str, object] = {}
        self._last_modified = False
        if project_folder is not None:
            self.proj = A.EcuProject.load(project_folder)
            self.path = self.proj.working_path
            self.img = A.Image(bytearray(self.proj.work_bytes()), self.proj.base, "binary", str(self.path))
            try:
                self.original = bytes(self.proj.original_bytes())
            except Exception:  # noqa: BLE001 - original missing: compare against the working copy as loaded
                self.original = bytes(self.img.data)
            self.profiles = self.proj.checksums
            self.maps = self.proj.map_defs()
            self.read_only = bool(read_only)
        else:
            self.path = Path(path)
            self.img = A.load_image(self.path)
            self.original = bytes(self.img.data)
            ext = self.path.suffix.lower()
            self.read_only = bool(read_only) if read_only is not None else \
                (self.img.fmt not in ("binary", "raw") or ext == ".ori")
        # EEPROM tab: asked for, or a stand-alone file with an EEPROM size (flash dumps of the same size get the
        # tab too - the byte-order views are harmless); never for the image of an ECU project
        self.ee = E.guess(bytes(self.img.data), str(self.path)) \
            if eeprom or (eeprom is None and self.proj is None) else None
        self.is_eeprom = bool(eeprom) if eeprom is not None else False
        if self.is_eeprom:
            self.read_only = True
        self._build()
        self._load_sidecar_maps()
        self.refresh_tree()
        self.refresh_potential()
        self.verify_checksums(show=False)
        self.compare(quiet=True)
        self.tabs.setCurrentIndex(TAB_HEX if (self.proj is not None or notice_accepted()) else TAB_START)
        self._filter = _KeyFilter(self)
        QApplication.instance().installEventFilter(self._filter)

    # ------------------------------------------------------------------ document protocol
    @property
    def retro_path(self):
        return self.path

    def is_modified(self) -> bool:
        return self.doc.buf.modified

    def data(self) -> bytes:
        return bytes(self.doc.buf.data)

    def save(self) -> bool:
        if self.read_only:
            return self.save_as()
        try:
            if self.proj is not None:
                self.proj.write_work(self.data())
                self.doc.buf.mark_saved()
            else:
                self.doc.buf.save(self.path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Firmware & ECU", f"Cannot save:\n{e}")
            return False
        self._emit_modified()
        self.saved.emit()
        self.log(f"Saved {self.path.name}")
        return True

    def save_as(self, path=None) -> bool:
        if path is None:
            start = str(self.path.with_name(self.path.stem + "_copy.bin")) if self.path else ""
            path, _ = QFileDialog.getSaveFileName(self, "Save Working Copy As (binary)", start,
                                                  "Binary (*.bin);;All files (*)")
            if not path:
                return False
        Path(path).write_bytes(self.data())
        self.log(f"Binary copy written: {path}")
        return True

    def edit_op(self, op: str) -> None:
        self.doc.edit_op(op)

    def showEvent(self, e):  # noqa: N802
        super().showEvent(e)
        if not getattr(self, "_sized", False):
            self._sized = True
            QTimer.singleShot(0, self._size_docks)

    def _size_docks(self) -> None:
        w = max(800, self.width())
        side = max(170, min(260, w // 6))
        self.resizeDocks([self.d_project, self.d_props], [side, side + 20], Qt.Orientation.Horizontal)
        self.resizeDocks([self.d_pot], [max(150, self.height() // 4)], Qt.Orientation.Vertical)

    def closeEvent(self, e):  # noqa: N802
        try:
            QApplication.instance().removeEventFilter(self._filter)
        except Exception:  # noqa: BLE001
            pass
        super().closeEvent(e)

    def shutdown(self) -> None:
        try:
            QApplication.instance().removeEventFilter(self._filter)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ ui
    def _act(self, tb, text, slot, key="", tip=""):
        a = QAction(text, self)
        a.triggered.connect(lambda _c=False: slot())
        if key:
            self.keys[QKeySequence(key).toString()] = slot
            a.setToolTip(f"{_tr(tip or text)} ({key})")
        elif tip:
            a.setToolTip(tip)
        if tb is not None:
            tb.addAction(a)
        return a

    def _build(self) -> None:
        from ...retro.rom.hexdoc import HexDocument
        tb = QToolBar("Firmware")
        tb.setObjectName("fwToolbar")
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        tb.setMovable(False)
        self.addToolBar(tb)
        self.toolbar = tb
        self.a_build = self._act(tb, "Build", self.build, "F7", "Working copy + corrected checksums -> build/")
        self.a_verify = self._act(tb, "Verify Checksums", lambda: self.verify_checksums(True), "Ctrl+Shift+V")
        self.a_compare = self._act(tb, "Compare", lambda: self.compare(), "Ctrl+D", "Differences against the original")
        self.a_find = self._act(tb, "Find Maps", self.find_maps, "Ctrl+M", "Find potential maps")
        self.a_analyze = self._act(tb, "Analyze", self.analyze, "Ctrl+Shift+A", "CPU, entropy and strings")
        self.keys[QKeySequence("Ctrl+Z").toString()] = lambda: self.doc.edit_op("undo")
        self.keys[QKeySequence("Ctrl+Y").toString()] = lambda: self.doc.edit_op("redo")
        tb.addSeparator()
        self.a_newmap = self._act(tb, "Map from Selection", lambda: self.new_map_from_selection(), "",
                                  "New map from the bytes selected in the hex view (K)")
        self.a_version = self._act(tb, "Save Version", lambda: self.save_version(), "",
                                   "Keep a named snapshot of the working copy")
        more = QMenu(self)
        more.addAction("Correct Checksums", self.correct_checksums)
        more.addAction("Load Checksum Profile...", self.load_profile_dialog)
        more.addAction("Find Checksums (from the original)...", self.find_checksums)
        more.addSeparator()
        more.addAction("Import A2L...", self.import_a2l_dialog)
        more.addAction("Save Working Copy As (binary)...", lambda: self.save_as())
        more.addAction("Open Original (read-only hex editor)", self.open_original)
        more.addAction("Open in Ghidra", self.open_in_ghidra)
        more.addSeparator()
        # the full editors of the other firmware features (set by radide/features/firmware_ide.py)
        self.integrations: dict[str, object] = {}
        self.a_full_maps = more.addAction("Calibration Map Editor (full)", lambda: self.integrate("maps"))
        self.a_full_analysis = more.addAction("Detailed Firmware Analysis", lambda: self.integrate("analysis"))
        btn = QAction("More", self)
        btn.setMenu(more)
        tb.addAction(btn)
        try:
            from PyQt6.QtWidgets import QToolButton
            tw = tb.widgetForAction(btn)
            if isinstance(tw, QToolButton):
                tw.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        except Exception:  # noqa: BLE001
            pass
        self.more_menu = more
        tb.addSeparator()
        self.mode_label = QLabel()
        tb.addWidget(self.mode_label)

        # ---------------- central: notice + tabs
        central = QWidget()
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        self.notice = QFrame()
        self.notice.setObjectName("fwNotice")
        self.notice.setStyleSheet("#fwNotice { background: #6b4e00; } #fwNotice QLabel { color: #fff7d6; }")
        nl = QHBoxLayout(self.notice)
        nl.setContentsMargins(8, 4, 8, 4)
        self.notice_label = QLabel(NOTICE_TEXT)
        self.notice_label.setWordWrap(True)
        nl.addWidget(self.notice_label, 1)
        ok = QPushButton("I understand")
        ok.clicked.connect(self.accept_notice)
        nl.addWidget(ok)
        self.notice.setVisible(not notice_accepted())
        try:
            from ..project import notice as _notice
            _notice.on_accepted(self.notice)        # accepted elsewhere (ECU project dialog, other views) -> hide
        except Exception:  # noqa: BLE001
            pass
        cl.addWidget(self.notice)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        cl.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        self.start = StartPage()
        self.tabs.addTab(self.start, "Getting Started")
        self.doc = HexDocument(self.path if self.img.fmt in ("binary", "raw") else None, bytes(self.img.data),
                               read_only=self.read_only)
        if self.img.fmt in ("binary", "raw"):
            self.doc.path = self.path
        self.doc.view.edited.connect(self._on_hex_edited)
        self.doc.view.cursorMoved.connect(self._on_cursor)
        self.doc.view.selectionChanged.connect(lambda *_a: self._on_cursor(self.doc.view.cursor))
        self.doc.message.connect(self.log)
        self.doc.compareRequested.connect(lambda _l, r: self.compare(r))
        self.doc._keys[QKeySequence("K").toString()] = lambda: self.new_map_from_selection()
        self.doc.view.shortcut_keys = set(self.doc._keys)
        self.tabs.addTab(self.doc, "Hex")
        self.mapedit = MapEditor()
        self.mapedit.data_fn = self.data
        self.mapedit.original = self.original
        self.mapedit.write = self._write
        self.mapedit.read_only = self.read_only
        self.mapedit.message.connect(self.log)
        self.tabs.addTab(self.mapedit, "Map Editor")
        self.tabs.addTab(self._build_2d(), "2D View")
        self.tabs.addTab(self._build_disasm(), "Disassembly")
        self.tabs.addTab(self._build_analysis(), "Analysis")
        if self.ee is not None:
            self.tabs.addTab(self._build_eeprom(), "EEPROM")
        self.tabs.currentChanged.connect(self._on_tab)

        # ---------------- docks
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._on_tree_item)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        self.d_project = self._dock("Project", self.tree, Qt.DockWidgetArea.LeftDockWidgetArea, "fwDockProject")
        self.props = QTreeWidget()
        self.props.setHeaderLabels(["Property", "Value"])
        self.props.setRootIsDecorated(False)
        self.props.itemChanged.connect(self._on_prop_changed)
        self.d_props = self._dock("Properties", self.props, Qt.DockWidgetArea.RightDockWidgetArea, "fwDockProps")
        self.tree.setMinimumWidth(150)
        self.props.setMinimumWidth(160)

        self.pot = QTableWidget(0, 5)
        self.pot.setHorizontalHeaderLabels(["Score", "Address", "Size", "Type", "Name"])
        self.pot.verticalHeader().hide()
        self.pot.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.pot.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pot.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.pot.cellDoubleClicked.connect(lambda r, _c: self.open_potential(r))
        self.pot.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.pot.customContextMenuRequested.connect(self._pot_menu)
        potw = QWidget()
        pl = QVBoxLayout(potw)
        pl.setContentsMargins(0, 0, 0, 0)
        prow = QHBoxLayout()
        self.pot_label = QLabel("Press Find Maps (Ctrl+M) to search for tables with axes.")
        prow.addWidget(self.pot_label, 1)
        b = QPushButton("Add to Project Maps")
        b.clicked.connect(self.add_selected_potential)
        prow.addWidget(b)
        pl.addLayout(prow)
        pl.addWidget(self.pot, 1)
        self.d_pot = self._dock("Potential Maps", potw, Qt.DockWidgetArea.BottomDockWidgetArea, "fwDockPotential")

        self.difftree = QTreeWidget()
        self.difftree.setHeaderLabels(["Offset", "Length", "Before", "Now", "Map"])
        self.difftree.setRootIsDecorated(False)
        self.difftree.itemDoubleClicked.connect(lambda it, _c: self.goto(it.data(0, ROLE)))
        self.difftree.setProperty("i18n_skip_items", True)
        dw = QWidget()
        dl = QVBoxLayout(dw)
        dl.setContentsMargins(0, 0, 0, 0)
        self.diff_label = QLabel("")
        dl.addWidget(self.diff_label)
        dl.addWidget(self.difftree, 1)
        self.d_diff = self._dock("Differences", dw, Qt.DockWidgetArea.BottomDockWidgetArea, "fwDockDiff")

        self.cktree = QTreeWidget()
        self.cktree.setHeaderLabels(["Checksum", "Status", "Stored", "Computed", "Address"])
        self.cktree.setRootIsDecorated(False)
        self.cktree.itemDoubleClicked.connect(lambda it, _c: self.goto(it.data(0, ROLE)))
        cw = QWidget()
        ckl = QVBoxLayout(cw)
        ckl.setContentsMargins(0, 0, 0, 0)
        crow = QHBoxLayout()
        self.ck_label = QLabel("")
        crow.addWidget(self.ck_label, 1)
        for text, slot in (("Verify", lambda: self.verify_checksums(True)), ("Correct Checksums",
                                                                             self.correct_checksums),
                           ("Load Profile...", self.load_profile_dialog)):
            bb = QPushButton(text)
            bb.clicked.connect(lambda _c=False, s=slot: s())
            crow.addWidget(bb)
        ckl.addLayout(crow)
        ckl.addWidget(self.cktree, 1)
        self.d_ck = self._dock("Checksum Report", cw, Qt.DockWidgetArea.BottomDockWidgetArea, "fwDockChecksum")

        self.out = QPlainTextEdit()
        self.out.setReadOnly(True)
        self.out.setMaximumBlockCount(5000)
        self.d_out = self._dock("Output", self.out, Qt.DockWidgetArea.BottomDockWidgetArea, "fwDockOutput")
        for d in (self.d_diff, self.d_ck, self.d_out):
            self.tabifyDockWidget(self.d_pot, d)
        self.d_pot.raise_()
        self.resizeDocks([self.d_project, self.d_props], [230, 260], Qt.Orientation.Horizontal)
        self.resizeDocks([self.d_pot], [190], Qt.Orientation.Vertical)
        self._update_mode()

    def _dock(self, title, w, area, name) -> QDockWidget:
        d = QDockWidget(title, self)
        d.setObjectName(name)
        d.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                      QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        d.setWidget(w)
        self.addDockWidget(area, d)
        return d

    def _build_2d(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Cells:"))
        self.wave_cell = QComboBox()
        for k in ("u8", "u16be", "u16le", "s16be", "s16le", "u32be", "f32be"):
            self.wave_cell.addItem(_tr(A.CELL_TITLES[k]), k)
        self.wave_cell.setCurrentIndex(1)
        self.wave_cell.currentIndexChanged.connect(self._wave_settings)
        bar.addWidget(self.wave_cell)
        bar.addWidget(QLabel("Width:"))
        self.wave_width = QComboBox()
        for n in (256, 512, 1024, 2048, 4096):
            self.wave_width.addItem(str(n), n)
        self.wave_width.setCurrentIndex(2)
        self.wave_width.currentIndexChanged.connect(self._wave_settings)
        bar.addWidget(self.wave_width)
        hint = QLabel("Maps stand out as regular patterns. Mouse wheel scrolls, click moves the hex cursor.")
        hint.setWordWrap(True)
        bar.addWidget(hint, 1)
        lay.addLayout(bar)
        self.wave = WaveView()
        self.wave.offsetClicked.connect(self.goto)
        self.wave.set_data(self.data())
        lay.addWidget(self.wave, 1)
        return w

    def _wave_settings(self) -> None:
        self.wave.cell = self.wave_cell.currentData()
        self.wave.width_cells = self.wave_width.currentData()
        self.wave.show_at(self.doc.view.cursor)

    def _build_disasm(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QHBoxLayout()
        form.addWidget(QLabel("CPU:"))
        self.arch = QComboBox()
        for k, v in A.ARCHES.items():
            self.arch.addItem(v, k)
        form.addWidget(self.arch)
        form.addWidget(QLabel("Load address:"))
        self.base_edit = QLineEdit(f"0x{self.img.base:X}")
        self.base_edit.setMaximumWidth(110)
        form.addWidget(self.base_edit)
        form.addWidget(QLabel("Instructions:"))
        self.dis_count = QSpinBox()
        self.dis_count.setRange(16, 20000)
        self.dis_count.setValue(400)
        form.addWidget(self.dis_count)
        b = QPushButton("Disassemble at Cursor")
        b.clicked.connect(lambda: self.disassemble())
        form.addWidget(b)
        self.ghidra_btn = QPushButton("Open in Ghidra")
        self.ghidra_btn.clicked.connect(self.open_in_ghidra)
        form.addWidget(self.ghidra_btn)
        form.addStretch(1)
        lay.addLayout(form)
        self.dis_text = QPlainTextEdit()
        self.dis_text.setReadOnly(True)
        self.dis_text.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        f = QFont("Consolas")
        f.setStyleHint(QFont.StyleHint.Monospace)
        self.dis_text.setFont(f)
        self.dis_text.setProperty("i18n_skip", True)
        lay.addWidget(self.dis_text, 1)
        self.dis_note = QLabel("")
        lay.addWidget(self.dis_note)
        return w

    def _build_analysis(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        b = QPushButton("Analyze (Ctrl+Shift+A)")
        b.clicked.connect(self.analyze)
        top.addWidget(b)
        top.addStretch(1)
        lay.addLayout(top)
        split = QSplitter(Qt.Orientation.Vertical)
        self.facts = QTreeWidget()
        self.facts.setHeaderLabels(["Property", "Value"])
        self.facts.setRootIsDecorated(False)
        split.addWidget(self.facts)
        ew = QWidget()
        el = QVBoxLayout(ew)
        el.setContentsMargins(0, 0, 0, 0)
        ent_label = QLabel("Entropy (click to go there): blue = empty / tables, green = code / data, "
                           "red = compressed / encrypted")
        ent_label.setWordWrap(True)
        el.addWidget(ent_label)
        self.entropy = EntropyBar()
        self.entropy.offsetClicked.connect(self.goto)
        el.addWidget(self.entropy)
        split.addWidget(ew)
        self.strings = QTreeWidget()
        self.strings.setHeaderLabels(["Offset", "Text"])
        self.strings.setRootIsDecorated(False)
        self.strings.itemDoubleClicked.connect(lambda it, _c: self.goto(it.data(0, ROLE)))
        self.strings.setProperty("i18n_skip_items", True)
        split.addWidget(self.strings)
        split.setSizes([200, 90, 260])
        lay.addWidget(split, 1)
        return w

    def _build_eeprom(self) -> QWidget:
        from ...retro.rom.buffer import HexBuffer
        from ...retro.rom.hexview import HexView
        w = QWidget()
        lay = QVBoxLayout(w)
        ee = self.ee
        form = QFormLayout()
        form.addRow("Size:", QLabel(f"{ee.size:,} bytes"))
        chips = QLabel(", ".join(ee.chips) or "-")
        chips.setProperty("i18n_skip", True)
        form.addRow("Chips with this size:", chips)
        form.addRow("Blank (0x00 / 0xFF):", QLabel(f"{ee.blank:.0%}"))
        self.ee_mode = QComboBox()
        for k, (label, _fn) in E.VIEWS.items():
            self.ee_mode.addItem(_tr(label), k)
        self.ee_mode.currentIndexChanged.connect(self._ee_view)
        form.addRow("Byte order:", self.ee_mode)
        lay.addLayout(form)
        for n in ee.notes:
            lay.addWidget(QLabel(n))
        note = QLabel("Generic read-only view of the memory array. Use Save Working Copy As to write a byte-swapped "
                      "copy.")
        note.setWordWrap(True)
        lay.addWidget(note)
        self.ee_view = HexView(HexBuffer(bytes(self.img.data)))
        self.ee_view.read_only = True
        lay.addWidget(self.ee_view, 1)
        return w

    def _ee_view(self) -> None:
        from ...retro.rom.buffer import HexBuffer
        self.ee_view.set_buffer(HexBuffer(E.view(self.data(), self.ee_mode.currentData())))

    def eeprom_view_bytes(self) -> bytes:
        return bytes(self.ee_view.buf.data) if self.ee is not None else b""

    def _update_mode(self) -> None:
        parts = []
        if self.proj is not None:
            parts.append(_tr(f"ECU project: {self.proj.name}"))
        else:
            parts.append(self.path.name)
        parts.append(_tr(f"{self.img.fmt}, {len(self.img.data):,} bytes"))
        if self.is_eeprom:
            parts.append("EEPROM")
        if self.read_only:
            parts.append(_tr("read-only"))
        self.mode_label.setText("   " + " | ".join(parts))

    # ------------------------------------------------------------------ notice
    def accept_notice(self) -> None:
        set_notice_accepted()
        self.notice.hide()

    # ------------------------------------------------------------------ logging
    def log(self, text: str) -> None:
        self.out.appendPlainText(text)
        self.message.emit(text)

    # ------------------------------------------------------------------ editing glue
    def _write(self, addr: int, data: bytes, merge_key: str = "") -> None:
        if self.read_only:
            return
        self.doc.buf.overwrite(addr, data)
        self.doc.view.viewport().update()
        self.doc.view.edited.emit()

    def _emit_modified(self) -> None:
        m = self.is_modified()
        if m != self._last_modified:
            self._last_modified = m
            self.modifiedChanged.emit(m)

    def _on_hex_edited(self) -> None:
        self._emit_modified()
        if not hasattr(self, "_edit_timer"):
            self._edit_timer = QTimer(self, singleShot=True, interval=250)
            self._edit_timer.timeout.connect(self._after_edit)
        self._edit_timer.start()

    def _after_edit(self) -> None:
        if self.tabs.currentWidget() is self.mapedit:
            self.mapedit.refresh()
        self.wave.set_data(self.data())
        self.compare(quiet=True, keep=True)

    def _on_tab(self, i: int) -> None:
        if i == TAB_MAP:
            self.mapedit.refresh()
        elif i == TAB_2D:
            self.wave.set_data(self.data())
            self.wave.marks = [(m.address, m.size) for m in self.maps + self.potential]
            self.wave.show_at(self.doc.view.cursor)

    def goto(self, offset) -> None:
        if offset is None:
            return
        off = int(offset)
        self.tabs.setCurrentWidget(self.doc)
        self.doc.goto(off)

    def _on_cursor(self, off: int) -> None:
        if self.tabs.currentWidget() is self.mapedit:
            return
        self._prop_map = None
        d = self.data()
        rows = [("Offset", f"0x{off:X} ({off:,})"), ("Address", f"0x{self.img.base + off:08X}")]
        for cell in ("u8", "u16be", "u16le", "u32be", "u32le", "f32be"):
            v = A.read_cells(d, off, 1, cell)
            if v:
                rows.append((A.CELL_TITLES[cell], f"{v[0]:g}" if isinstance(v[0], float) else f"{v[0]} (0x{v[0]:X})"))
        m = self.map_at(off)
        if m is not None:
            rows.append(("In map", m.name))
        s, n = self.doc.view.selection()
        if n:
            rows.append(("Selection", f"0x{s:X} + {n} bytes"))
        self._fill_props(rows, editable=False)

    def _fill_props(self, rows, editable: bool) -> None:
        self.props.blockSignals(True)
        self.props.clear()
        for k, v in rows:
            it = QTreeWidgetItem([k, str(v)])
            it.setData(0, ROLE, k)
            if editable and k in self.EDITABLE:
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsEditable)
            self.props.addTopLevelItem(it)
        self.props.resizeColumnToContents(0)
        _retranslate(self.props)
        self.props.blockSignals(False)

    # ------------------------------------------------------------------ maps
    EDITABLE = {"Name", "Folder", "Address", "Rows", "Columns", "Cell type", "Factor", "Offset", "Unit",
                "X axis address", "Y axis address", "Comment"}

    def map_at(self, off: int) -> A.MapDef | None:
        return next((m for m in self.maps if m.address <= off < m.address + m.size), None)

    def open_map(self, m: A.MapDef) -> None:
        self.doc.view.select_range(m.address, m.size)
        self.mapedit.set_map(m)
        self.tabs.setCurrentWidget(self.mapedit)
        self.mapedit.table.setFocus()
        if self.mapedit.table.rowCount():
            self.mapedit.table.setCurrentCell(0, 0)
        self._show_map_props(m)

    def _show_map_props(self, m: A.MapDef) -> None:
        self._prop_map = m
        self._fill_props([("Name", m.name), ("Folder", m.folder), ("Kind", m.kind),
                          ("Address", f"0x{m.address:X}"), ("Rows", m.rows), ("Columns", m.cols),
                          ("Cell type", m.cell), ("Factor", f"{m.factor:g}"), ("Offset", f"{m.offset:g}"),
                          ("Unit", m.unit), ("X axis address", f"0x{m.x_addr:X}" if m.x_addr else ""),
                          ("Y axis address", f"0x{m.y_addr:X}" if m.y_addr else ""),
                          ("Size", f"{m.size} bytes"), ("Source", m.source), ("Comment", m.comment)], editable=True)

    def _on_prop_changed(self, it, col) -> None:
        m = getattr(self, "_prop_map", None)
        if m is None or col != 1:
            return
        k, v = it.data(0, ROLE), it.text(1).strip()
        try:
            if k == "Name":
                m.name = v or m.name
            elif k == "Folder":
                m.folder = v
            elif k == "Unit":
                m.unit = v
            elif k == "Comment":
                m.comment = v
            elif k == "Address":
                m.address = int(v, 0)
            elif k == "Rows":
                m.rows = max(1, int(v, 0))
            elif k == "Columns":
                m.cols = max(1, int(v, 0))
            elif k == "Cell type":
                if v not in A.CELL:
                    raise ValueError(f"cell type: one of {', '.join(A.CELL)}")
                m.cell = v
            elif k == "Factor":
                m.factor = float(v)
            elif k == "Offset":
                m.offset = float(v)
            elif k == "X axis address":
                m.x_addr = int(v, 0) if v else 0
                m.x_cell = m.x_cell or m.cell
            elif k == "Y axis address":
                m.y_addr = int(v, 0) if v else 0
                m.y_cell = m.y_cell or m.cell
        except ValueError as e:
            self.log(f"Property {k}: {e}")
        self.mapedit.set_map(m)
        if m in self.maps:
            self.save_maps()
            self.refresh_tree()
        QTimer.singleShot(0, lambda: self._show_map_props(m))

    def save_maps(self) -> None:
        if self.proj is not None:
            try:
                self.proj.save_maps(self.maps)
            except Exception as e:  # noqa: BLE001
                self.log(f"*** cannot save the maps: {e}")
        elif self.path is not None and not self.is_eeprom:
            try:
                p = self.path.with_name(self.path.name + ".maps.json")
                mm = None
                try:
                    from ..maps import model as mm
                except Exception:  # noqa: BLE001
                    mm = None
                if mm is not None:
                    mm.MapPack(self.path.name, [x.to_slice_map() for x in self.maps]).save(p)
                else:
                    import json
                    p.write_text(json.dumps({"maps": [x.to_dict() for x in self.maps]}, indent=2), encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                self.log(f"*** cannot save the maps: {e}")

    def _load_sidecar_maps(self) -> None:
        if self.proj is not None or self.path is None:
            return
        p = self.path.with_name(self.path.name + ".maps.json")
        if p.is_file():
            import json
            try:
                self.maps = [A.MapDef.from_any(m) for m in json.loads(p.read_text(encoding="utf-8")).get("maps", [])]
            except Exception as e:  # noqa: BLE001
                self.log(f"*** {p.name}: {e}")

    def add_map(self, m: A.MapDef, save: bool = True) -> A.MapDef:
        names = {x.name for x in self.maps}
        base, i = m.name, 2
        while m.name in names:
            m.name = f"{base}_{i}"
            i += 1
        if m.source == "finder":
            m.source = "user"
        self.maps.append(m)
        if save:
            self.save_maps()
        self.refresh_tree()
        return m

    def new_map_from_selection(self, name: str | None = None, cell: str | None = None, cols: int | None = None):
        s, n = self.doc.view.selection()
        if n <= 0:
            s, n = self.doc.view.cursor, 2
        if cell is None:
            cpu = A.cpu_guess(self.data()[:1 << 20])
            cell = "u16be" if cpu and cpu[0][0] in ("ppc", "m68k", "mips", "sh") else "u16le"
            if n == 1 or n % 2:
                cell = "u8"
        w = A.CELL[cell][1]
        count = max(1, n // w)
        if name is None:
            name, ok = QInputDialog.getText(self, "New Map", f"Name of the map ({count} cells at 0x{s:X}):",
                                            text=f"Map_{s:06X}")
            if not ok or not name.strip():
                return None
        cols = cols or (16 if count % 16 == 0 and count > 16 else count)
        rows = max(1, count // cols)
        m = A.MapDef(name.strip(), s, rows, cols, cell, source="user", folder="My maps")
        self.add_map(m)
        self.open_map(m)
        self.log(f"Map {m.name}: {rows}x{cols} {A.CELL_TITLES[cell]} at 0x{s:X}")
        return m

    def remove_map(self, m: A.MapDef) -> None:
        if m in self.maps:
            self.maps.remove(m)
            self.save_maps()
            self.refresh_tree()

    # ------------------------------------------------------------------ potential maps
    def find_maps(self) -> int:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.potential = A.find_maps(self.data())
        finally:
            QApplication.restoreOverrideCursor()
        known = {m.address for m in self.maps}
        self.potential = [p for p in self.potential if p.address not in known]
        self.refresh_potential()
        self.d_pot.raise_()
        self.log(f"Find maps: {len(self.potential)} potential map(s) ({A.backends().get('maps', '')})")
        return len(self.potential)

    def refresh_potential(self) -> None:
        t = self.pot
        t.setRowCount(len(self.potential))
        for r, m in enumerate(self.potential):
            vals = [f"{m.score * 50:.0f}", f"0x{m.address:06X}", f"{m.rows}x{m.cols}" if m.rows > 1 else f"{m.cols}",
                    _tr(A.CELL_TITLES.get(m.cell, m.cell)), m.name]
            for c, v in enumerate(vals):
                t.setItem(r, c, QTableWidgetItem(v))
        t.resizeColumnsToContents()
        _retranslate(t)
        if self.potential:
            self.pot_label.setText(f"{len(self.potential)} potential map(s) - double-click to open, "
                                   "Add to Project Maps to keep one.")

    def open_potential(self, row: int) -> None:
        if 0 <= row < len(self.potential):
            self.open_map(self.potential[row])

    def add_selected_potential(self) -> int:
        rows = sorted({i.row() for i in self.pot.selectedIndexes()})
        if not rows and self.pot.currentRow() >= 0:
            rows = [self.pot.currentRow()]
        added = 0
        for r in rows:
            if 0 <= r < len(self.potential):
                m = self.potential[r]
                if m not in self.maps:
                    m.folder = m.folder or "Found maps"
                    self.add_map(m, save=False)
                    added += 1
        if added:
            self.save_maps()
            self.potential = [p for p in self.potential if p not in self.maps]
            self.refresh_potential()
            self.log(f"{added} map(s) added to the project maps")
        return added

    def _pot_menu(self, pos) -> None:
        m = QMenu(self)
        m.addAction("Open in Map Editor", lambda: self.open_potential(self.pot.currentRow()))
        m.addAction("Add to Project Maps", self.add_selected_potential)
        m.addAction("Show in Hex View", lambda: self.potential and
                    self.goto(self.potential[max(0, self.pot.currentRow())].address))
        m.exec(self.pot.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------ A2L
    def import_a2l_dialog(self) -> int:
        f, _ = QFileDialog.getOpenFileName(self, "Import A2L", str(self.path.parent if self.path else ""),
                                           "ASAP2 (*.a2l);;All files (*)")
        return self.import_a2l(f) if f else 0

    def import_a2l(self, path) -> int:
        text = Path(path).read_text(encoding="latin-1", errors="replace")
        maps = A.parse_a2l(text)
        base = self.img.base
        n = 0
        size = len(self.data())
        for m in maps:
            for attr in ("address", "x_addr", "y_addr"):          # ECU addresses -> file offsets
                v = getattr(m, attr)
                if v and v >= base and v - base < size:
                    setattr(m, attr, v - base)
            if m.address + m.size <= size:
                m.folder = m.folder or "A2L"
                self.add_map(m, save=False)
                n += 1
        self.save_maps()
        self.log(f"A2L {Path(path).name}: {n} of {len(maps)} map(s) inside this file ({A.backends().get('a2l', '')})")
        return n

    # ------------------------------------------------------------------ checksums
    def verify_checksums(self, show: bool = True) -> list[dict]:
        res = A.verify(self.data(), self.profiles)
        self._fill_checksums(res)
        if show:
            self.d_ck.raise_()
            bad = sum(1 for r in res if not r["ok"])
            self.log(f"Checksums: {len(res)} profile(s), {bad} wrong" if res else
                     "Checksums: no profiles - load one or use Find Checksums")
        return res

    def _fill_checksums(self, res) -> None:
        self.last_report = res
        self.cktree.clear()
        for r in res:
            w = int(r.get("width") or 2) * 2
            st = "OK" if r["ok"] else ("ERROR: " + r["error"] if r.get("error") else "WRONG")
            if r.get("corrected"):
                st += " (corrected)"
            it = QTreeWidgetItem([str(r["name"]), st, f"{int(r['stored']):0{w}X}", f"{int(r['computed']):0{w}X}",
                                  f"0x{int(r['store']):X}"])
            it.setData(0, ROLE, int(r["store"]))
            it.setForeground(1, QColor(60, 170, 90) if r["ok"] else QColor(220, 80, 60))
            self.cktree.addTopLevelItem(it)
        for c in range(5):
            self.cktree.resizeColumnToContents(c)
        _retranslate(self.cktree)
        bad = sum(1 for r in res if not r["ok"])
        self.ck_label.setText(f"{len(res)} profile(s), {bad} wrong" if res else
                              "No checksum profiles. Load a profile or use More > Find Checksums.")

    def correct_checksums(self) -> list[dict]:
        if self.read_only:
            self.log("Read-only file: checksums are not corrected here (Build or Save As writes a copy).")
            return self.verify_checksums(True)
        new, res = A.fix(self.data(), self.profiles)
        old = self.data()
        for s, e in A.diff_ranges(old, new):
            self._write(s, new[s:s + e])
        self._fill_checksums(A.verify(self.data(), self.profiles))
        self.d_ck.raise_()
        self.log(f"Checksums corrected in the working copy ({A.backends().get('checksum_fix', '')})")
        return self.last_report

    def load_profile_dialog(self) -> int:
        f, _ = QFileDialog.getOpenFileName(self, "Load Checksum Profile", str(self.path.parent if self.path else ""),
                                           "Checksum profiles (*.json);;All files (*)")
        return self.load_profile(f) if f else 0

    def load_profile(self, path) -> int:
        import json
        profiles = []
        try:
            from ..checksum import load_profile
            _meta, blocks = load_profile(path)
            profiles = [b.to_dict() for b in blocks]
        except Exception:  # noqa: BLE001 - not a checksum-slice profile: plain JSON below
            profiles = []
        if not profiles:            # a JSON list, {"checksums": [...]} (ecu.json) or {"blocks": [...]}
            d = json.loads(Path(path).read_text(encoding="utf-8"))
            profiles = d.get("checksums", d.get("blocks", [])) if isinstance(d, dict) else d
        self.set_profiles(profiles)
        self.log(f"Checksum profile {Path(path).name}: {len(profiles)} block(s)")
        return len(profiles)

    def set_profiles(self, profiles: list) -> None:
        self.profiles = [A.norm_profile(p) for p in profiles]
        if self.proj is not None:
            self.proj.set_checksums(self.profiles)
            self.projectChanged.emit()
        self.verify_checksums(True)
        self.refresh_tree()

    def find_checksums(self) -> int:
        try:
            from ..checksum import find
        except Exception:  # noqa: BLE001
            QMessageBox.information(self, "Find Checksums", "The checksum finder (radide/firmware/checksum) is not "
                                    "available.")
            return 0
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            res = find(self.original)
        except Exception as e:  # noqa: BLE001
            self.log(f"*** checksum finder: {e}")
            return 0
        finally:
            QApplication.restoreOverrideCursor()
        cands = list(getattr(res, "candidates", res) or [])
        blocks = []
        for c in cands[:16]:
            b = getattr(c, "block", None)
            if b is not None and hasattr(b, "to_dict"):
                blocks.append(b.to_dict())
        self.log(f"Checksum finder: {len(cands)} candidate(s)")
        if blocks:
            if QMessageBox.question(self, "Find Checksums", f"Use the {len(blocks)} checksum block(s) found in the "
                                    "original as this file's profile?") == QMessageBox.StandardButton.Yes:
                self.set_profiles(blocks)
        return len(blocks)

    # ------------------------------------------------------------------ compare
    def compare(self, other=None, quiet: bool = False, keep: bool = False) -> int:
        from ...retro.rom.diffview import diff_ranges
        if other is False:
            other = None
        if other is None and keep and self.compare_label != "original":
            ref = getattr(self, "_compare_ref", self.original)
        elif other is None:
            ref, self.compare_label = self.original, "original"
        elif isinstance(other, (bytes, bytearray)):
            ref, self.compare_label = bytes(other), "version"
        else:
            p = Path(other)
            ref, self.compare_label = A.load_image(p).data, p.name
        self._compare_ref = bytes(ref)
        cur = self.data()
        ranges = diff_ranges(bytes(ref), cur)
        self.diffs = [(s, e - s) for s, e in ranges]
        self.doc.view.set_diff_ranges(ranges)
        self.difftree.clear()
        for s, n in self.diffs[:5000]:
            m = self.map_at(s)
            it = QTreeWidgetItem([f"0x{s:06X}", str(n), bytes(ref[s:s + min(n, 8)]).hex(" ").upper(),
                                  cur[s:s + min(n, 8)].hex(" ").upper(), m.name if m else ""])
            it.setData(0, ROLE, s)
            self.difftree.addTopLevelItem(it)
        changed = sum(n for _s, n in self.diffs)
        self.diff_label.setText(f"Against {self.compare_label}: {changed:,} byte(s) changed in {len(self.diffs)} "
                                f"range(s)" + (f", sizes differ ({len(ref):,} / {len(cur):,})"
                                               if len(ref) != len(cur) else ""))
        if not quiet:
            self.d_diff.raise_()
            self.log(self.diff_label.text())
        return len(self.diffs)

    # ------------------------------------------------------------------ versions / build
    def save_version(self, name: str | None = None, note: str = "") -> Path | None:
        if self.proj is None:
            QMessageBox.information(self, "Save Version", "Versions belong to an ECU project "
                                    "(Tools > Firmware & ECU > New ECU Project...).")
            return None
        if name is None:
            name, ok = QInputDialog.getText(self, "Save Version", "Name of this version:",
                                            text=f"v{len(self.proj.versions) + 1}")
            if not ok:
                return None
        p = self.proj.add_version(self.data(), name, note)
        self.refresh_tree()
        self.projectChanged.emit()
        self.log(f"Version saved: {name} ({p.name})")
        return p

    def build(self) -> Path | None:
        if self.proj is None:
            return self._build_copy()
        try:
            out, report = self.proj.build(self.data(), log=self.log)
        except Exception as e:  # noqa: BLE001 - shown to the user
            self.log(f"*** Build failed: {e}")
            QMessageBox.warning(self, "Build", str(e))
            return None
        self.doc.buf.mark_saved()
        self._emit_modified()
        self._fill_checksums(report)
        self.refresh_tree()
        self.projectChanged.emit()
        self.d_out.raise_()
        self.log(f"Build finished: {out}")
        self.built = out
        return out

    def _build_copy(self, path=None) -> Path | None:
        if path is None:
            start = str(self.path.with_name(self.path.stem + "_mod.bin"))
            path, _ = QFileDialog.getSaveFileName(self, "Build: save a copy with corrected checksums", start,
                                                  "Binary (*.bin);;All files (*)")
            if not path:
                return None
        new, report = A.fix(self.data(), self.profiles) if self.profiles else (self.data(), [])
        Path(path).write_bytes(new)
        self._fill_checksums(report)
        self.log(f"Build: {path} ({len(new):,} bytes)")
        self.built = Path(path)
        return Path(path)

    # ------------------------------------------------------------------ analysis / disassembly
    def analyze(self) -> dict:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            res = A.analyze(A.Image(bytearray(self.data()), self.img.base, self.img.fmt, str(self.path)))
        finally:
            QApplication.restoreOverrideCursor()
        self.facts.clear()
        for k, v in res["facts"].items():
            self.facts.addTopLevelItem(QTreeWidgetItem([k, str(v)]))
        if self.proj is not None:
            self.facts.addTopLevelItem(QTreeWidgetItem(["Project", str(self.proj.folder)]))
        self.facts.resizeColumnToContents(0)
        _retranslate(self.facts)
        n = len(self.data())
        ent = res["entropy"]
        self.entropy.set_values(ent, max(1, n // max(1, len(ent))))
        self.strings.clear()
        for off, s in res["strings"]:
            it = QTreeWidgetItem([f"0x{off:06X}", s])
            it.setData(0, ROLE, off)
            self.strings.addTopLevelItem(it)
        cpus = res.get("cpu") or []
        if cpus:
            i = self.arch.findData(cpus[0][0])
            if i >= 0:
                self.arch.setCurrentIndex(i)
        self.tabs.setCurrentIndex(TAB_ANALYSIS)
        self.analysis = res
        self.log("Analysis: " + "; ".join(f"{k} {v}" for k, v in list(res["facts"].items())[:5]))
        return res

    def disassemble(self, offset: int | None = None) -> int:
        off = self.doc.view.cursor if offset is None else int(offset)
        try:
            base = int(self.base_edit.text().strip() or "0", 0)
        except ValueError:
            base = 0
        rows = A.disassemble(self.data(), base, self.arch.currentData(), base + off, self.dis_count.value())
        self.dis_text.setPlainText("\n".join(f"{a:08X}  {b:<24} {mn:<8} {ops}" for a, b, mn, ops in rows))
        note = A.backends().get('disasm', '')
        try:
            from ..analysis.disasm import backend_label
            note += f" - decoder: {backend_label(self.arch.currentData())}"
        except Exception:  # noqa: BLE001 - the analysis slice is optional here
            pass
        self.dis_note.setText(f"{len(rows)} line(s) - {note}")
        self.tabs.setCurrentIndex(TAB_DISASM)
        return len(rows)

    def open_in_ghidra(self) -> bool:
        g = A.find_ghidra()
        if not g:
            QMessageBox.information(self, "Ghidra", "Ghidra is not installed. Download it from its official GitHub "
                                    "page (github.com/NationalSecurityAgency/ghidra) and extract it into "
                                    "%LOCALAPPDATA%\\RADIDE\\tools, or set GHIDRA_HOME.")
            return False
        run = Path(g).parent.parent / ("ghidraRun.bat" if Path(g).suffix == ".bat" else "ghidraRun")
        if not run.is_file():
            self.log(f"*** ghidraRun not found next to {g}")
            return False
        from PyQt6.QtCore import QProcess
        ok = QProcess.startDetached(str(run), [])
        self.log(f"Ghidra started ({run}). Import {self.path} as raw binary, language "
                 f"{self.arch.currentText()}, base {self.base_edit.text()}." if ok else "*** Ghidra did not start")
        return bool(ok)

    def integrate(self, name: str):
        """Open this file in another firmware feature's own view (map editor / analysis) - saved first."""
        fn = self.integrations.get(name)
        if fn is None:
            self.log(f"{name}: not available in this IDE")
            return None
        if self.is_modified() and not self.read_only:
            self.save()
        try:
            return fn(self)
        except Exception as e:  # noqa: BLE001
            self.log(f"*** {name}: {e}")
            return None

    def open_original(self) -> None:
        p = self.proj.original_path if self.proj is not None else self.path
        if p is not None:
            self.openInIde.emit(str(p), True)

    # ------------------------------------------------------------------ project tree
    def refresh_tree(self) -> None:
        t = self.tree
        t.clear()
        style = self.style()
        sp = style.StandardPixmap

        def node(parent, text, kind, payload=None, icon=sp.SP_FileIcon, tip=""):
            it = QTreeWidgetItem([text])
            it.setData(0, ROLE, (kind, payload))
            it.setIcon(0, style.standardIcon(icon))
            if tip:
                it.setToolTip(0, tip)
            (parent.addChild(it) if parent is not None else t.addTopLevelItem(it))
            return it
        if self.proj is not None:
            root = node(None, f"ECU Project: {self.proj.name}", "project", None, sp.SP_DriveHDIcon)
            op = self.proj.original_path
            node(root, f"Original: {op.name if op else '-'}", "original", str(op) if op else None,
                 sp.SP_FileDialogInfoView, "Kept read-only. Double-click: compare with the original")
            node(root, f"Working copy: {self.path.name}", "working", None, sp.SP_FileIcon,
                 "The file the hex and map editors change")
            vers = self.proj.versions
            vn = node(root, f"Versions ({len(vers)})", "versions", None, sp.SP_DirIcon)
            for v in vers:
                node(vn, f"{v['id']} {v['name']}" + (f" - {v['note']}" if v.get("note") else ""), "version",
                     v["id"], sp.SP_FileIcon, v.get("time", ""))
            vn.setExpanded(True)
        else:
            root = node(None, self.path.name, "file", None, sp.SP_FileIcon, str(self.path))
        mn = node(root, f"Maps ({len(self.maps)})", "maps", None, sp.SP_DirIcon)
        folders: dict[str, QTreeWidgetItem] = {}
        for m in self.maps:
            parent = mn
            if m.folder:
                if m.folder not in folders:
                    folders[m.folder] = node(mn, m.folder, "mapfolder", m.folder, sp.SP_DirIcon)
                    folders[m.folder].setExpanded(True)
                parent = folders[m.folder]
            node(parent, f"{m.name}  [{m.rows}x{m.cols}]" if m.kind == "map" else f"{m.name}  [{m.kind}]", "map", m,
                 sp.SP_FileDialogContentsView, f"0x{m.address:X} {A.CELL_TITLES.get(m.cell, m.cell)}")
        mn.setExpanded(True)
        cn = node(root, f"Checksum profiles ({len(self.profiles)})", "checksums", None, sp.SP_DialogApplyButton)
        for p in self.profiles:
            node(cn, str(p.get("name", "?")), "checksum", p, sp.SP_FileIcon, str(p.get("algorithm", "")))
        cn.setExpanded(True)
        if self.proj is not None and self.proj.output_path.is_file():
            node(root, f"Build: {self.proj.output_path.name}", "output", str(self.proj.output_path),
                 sp.SP_DialogSaveButton, "Double-click: open read-only in the hex editor")
        if self.ee is not None:
            node(root, "EEPROM view", "eeprom", None, sp.SP_DriveFDIcon, ", ".join(self.ee.chips))
        root.setExpanded(True)
        _retranslate(t)

    def _on_tree_item(self, it, _col=0) -> None:
        kind, payload = it.data(0, ROLE) or (None, None)
        if kind == "map":
            self.open_map(payload)
        elif kind == "original":
            self.compare()
        elif kind == "working":
            self.tabs.setCurrentWidget(self.doc)
        elif kind == "version" and self.proj is not None:
            self.compare(self.proj.version_bytes(payload))
            self.compare_label = f"version {payload}"
            self.diff_label.setText(self.diff_label.text().replace("Against version", f"Against version {payload}"))
        elif kind in ("checksum", "checksums"):
            self.verify_checksums(True)
        elif kind == "output":
            self.openInIde.emit(payload, True)
        elif kind == "eeprom":
            self.tabs.setCurrentIndex(self.tabs.count() - 1)

    def _tree_menu(self, pos) -> None:
        it = self.tree.itemAt(pos)
        kind, payload = it.data(0, ROLE) if it is not None and it.data(0, ROLE) else (None, None)
        m = QMenu(self)
        if kind == "map":
            m.addAction("Open in Map Editor", lambda: self.open_map(payload))
            m.addAction("Show in Hex View", lambda: self.goto(payload.address))
            m.addAction("Remove Map", lambda: self.remove_map(payload))
        elif kind == "version" and self.proj is not None:
            m.addAction("Compare with Working Copy", lambda: self._on_tree_item(it))
        elif kind in ("maps", "mapfolder"):
            m.addAction("Find Maps", self.find_maps)
            m.addAction("Import A2L...", self.import_a2l_dialog)
            m.addAction("New Map from Selection", lambda: self.new_map_from_selection())
        elif kind in ("checksums", "checksum"):
            m.addAction("Verify Checksums", lambda: self.verify_checksums(True))
            m.addAction("Correct Checksums", self.correct_checksums)
            m.addAction("Load Checksum Profile...", self.load_profile_dialog)
        m.addSeparator()
        m.addAction("Build", self.build)
        m.addAction("Save Version", lambda: self.save_version())
        m.exec(self.tree.viewport().mapToGlobal(pos))


__all__ = ["FirmwareWorkbench", "StartPage", "NOTICE_TEXT", "WORKBENCH_KEYS", "notice_accepted",
           "set_notice_accepted"]
