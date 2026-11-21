"""Car Diagnostics workbench (Tools > Car Diagnostics...): an OBD-II scan tool inside the IDE (docs/CARDIAG.md).

Connect bar (adapter, port, protocol, Demo car), a vehicle header (VIN, protocol, control units, MIL, codes,
battery voltage) and tabs: Faults, Live Data, Freeze Frame, Readiness, Tests (06), Info (09), Log.

* Reading and explaining faults, live data, freeze frames, readiness monitors, mode 06 results and vehicle
  information; clearing codes (mode 04) only after a confirmation that lists what will be erased and warns about
  the readiness monitors and about safety-relevant faults.
* Other car-diagnostics slices add tabs through ``TAB_HOOKS`` (callables ``f(workbench)``) and use
  ``workbench.client`` (radide.cardiag.obd.ObdClient), ``workbench.link`` (the link-slice connection, or None)
  and ``workbench.transport``.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QFont
from PyQt6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QPlainTextEdit, QPushButton, QRadioButton, QSlider, QSpinBox, QSplitter, QTabWidget,
                             QTableWidget, QTableWidgetItem, QTextBrowser, QToolButton, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

TAB_HOOKS: list = []          # f(workbench) -> None, called once per workbench (other slices add tabs)
ROLE = Qt.ItemDataRole.UserRole

ADAPTERS = [("demo", "Demo car (no hardware)"),
            ("demo_elm", "Demo car through the ELM327 simulator (shared with the service functions)"),
            ("elm_serial", "ELM327 / STN - USB or Bluetooth (COM port)"),
            ("elm_wifi", "ELM327 Wi-Fi (192.168.0.10:35000)"), ("elm_ble", "ELM327 Bluetooth LE"),
            ("j2534", "J2534 PassThru device")]
PROTOCOLS = [("0", "Automatic"), ("6", "ISO 15765-4 CAN (11 bit, 500 kbaud)"),
             ("7", "ISO 15765-4 CAN (29 bit, 500 kbaud)"), ("8", "ISO 15765-4 CAN (11 bit, 250 kbaud)"),
             ("9", "ISO 15765-4 CAN (29 bit, 250 kbaud)"), ("5", "ISO 14230-4 KWP (fast init)"),
             ("4", "ISO 14230-4 KWP (5 baud init)"), ("3", "ISO 9141-2"), ("1", "SAE J1850 PWM"),
             ("2", "SAE J1850 VPW")]
PRESETS = {"Basic engine": [0x0C, 0x0D, 0x05, 0x04, 0x11, 0x42],
           "Fuel trims and mixture": [0x06, 0x07, 0x08, 0x09, 0x14, 0x15, 0x44, 0x03],
           "Temperatures": [0x05, 0x0F, 0x46, 0x5C, 0x3C, 0x3D],
           "Air intake": [0x10, 0x0B, 0x11, 0x45, 0x33, 0x4C],
           "Since codes cleared": [0x30, 0x31, 0x4E, 0x21, 0x4D]}

# what stored / pending / permanent mean (English, Arabic) - original text
KIND_EXPLAIN = {
    "stored": ("Stored (confirmed): the fault was seen on enough drive cycles for the computer to confirm it. "
               "For emissions faults the MIL (check engine lamp) is usually on.",
               "مخزّن (مؤكَّد): العطل ظهر في عدد كافٍ من دورات القيادة فأكّده الكمبيوتر. "
               "في أعطال الانبعاثات تكون لمبة المحرك (MIL) غالباً منوّرة."),
    "pending": ("Pending: the fault was seen once (on the current or last drive cycle) but is not confirmed yet. "
                "If it happens again on the next drive cycle it becomes stored and may turn the MIL on. "
                "It is an early warning - worth checking before it gets worse.",
                "معلّق: العطل ظهر مرة (في دورة القيادة الحالية أو السابقة) ولم يتأكد بعد. "
                "لو تكرر في الدورة التالية يصبح مخزّناً وقد تنوّر لمبة المحرك. "
                "هو إنذار مبكر يستحق الفحص قبل أن يتفاقم."),
    "permanent": ("Permanent: a copy of a confirmed emissions fault that a scan tool cannot erase. The computer "
                  "removes it by itself once the monitor has run again and passed (after the repair). Inspection "
                  "stations look at these codes.",
                  "دائم: نسخة من عطل انبعاثات مؤكَّد لا يمسحها جهاز الفحص. الكمبيوتر يمسحه بنفسه بعد أن "
                  "يعيد الاختبار وينجح (بعد الإصلاح). مراكز الفحص الفني تنظر إلى هذه الأكواد."),
}

CLEAR_WARNINGS = (
    ("Clear codes only after the cause has been found and repaired. Clearing does not repair anything: "
     "the lamp comes back if the fault is still there.",
     "امسح الأعطال فقط بعد معرفة السبب وإصلاحه. المسح لا يصلح شيئاً: اللمبة سترجع لو العطل ما زال موجوداً."),
    ("All readiness monitors are reset to \"incomplete\". The car will fail an emissions inspection until it "
     "has been driven enough to complete them again (often several days of normal driving).",
     "كل اختبارات الجاهزية ترجع \"غير مكتملة\". العربية سترسب في فحص الانبعاثات حتى تُقاد بما يكفي "
     "لإكمالها مرة أخرى (غالباً عدة أيام من القيادة العادية)."),
    ("Freeze frames, mode 06 test results, the distance / time with the MIL on and the counters since the last "
     "clear are erased too. Save or print them first if you still need them.",
     "تُمسح أيضاً لقطات التجميد (Freeze frame) ونتائج اختبارات mode 06 والمسافة / الزمن مع لمبة المحرك "
     "والعدادات منذ آخر مسح. احفظها أو اطبعها أولاً لو ما زلت تحتاجها."),
    ("Permanent codes are not erased by a scan tool; the engine computer removes them after the repair has been "
     "confirmed by its own test.",
     "الأكواد الدائمة لا يمسحها جهاز الفحص؛ كمبيوتر المحرك يمسحها بعد أن يتأكد اختباره الخاص من الإصلاح."),
    ("Switch the ignition on with the engine off before clearing (many cars refuse to clear with the engine "
     "running).",
     "شغّل الإشعال والمحرك مطفأ قبل المسح (كثير من العربيات ترفض المسح والمحرك دائر)."),
)


def _lang() -> str:
    try:
        from ..i18n import language
        return language()
    except Exception:  # noqa: BLE001
        return "en"


def _ar() -> bool:
    return _lang() == "ar"


def tr(text: str) -> str:
    try:
        from ..i18n import tr as _t
        return _t(text)
    except Exception:  # noqa: BLE001
        return text


def bi(pair) -> str:
    return pair[1] if _ar() else pair[0]


def _esc(s) -> str:
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ------------------------------------------------------------------------------------------- knowledge base
def kb_info(code: str) -> dict:
    """{"title", "explain", "causes": [...], "checks": [...], "severity", "manufacturer"} for a DTC from the fault
    knowledge base slice (radide/cardiag/kb) when it is installed; otherwise the code's group only."""
    from ..cardiag.obd import dtc as D
    out = {"title": "", "explain": "", "causes": [], "checks": [], "severity": "", "manufacturer": False}
    try:
        from ..cardiag import kb
        ar = _ar()
        f = None
        for name in ("lookup", "get_fault", "explain", "get", "find"):
            fn = getattr(kb, name, None)
            if callable(fn):
                try:
                    f = fn(code)
                except TypeError:
                    continue
                if f is not None:
                    break
        if f is not None:
            def pick(*names):
                for n in names:
                    v = f.get(n) if isinstance(f, dict) else getattr(f, n, None)
                    if callable(v) and not isinstance(v, str):
                        try:
                            v = v("ar" if ar else "en")
                        except Exception:  # noqa: BLE001
                            v = None
                    if v:
                        return v
                return None
            out["title"] = pick(*(("title_ar", "name_ar") if ar else ()), "title", "name") or ""
            out["explain"] = pick(*(("explain_ar", "what_ar", "description_ar") if ar else ()),
                                  "explain", "what", "description") or ""
            out["causes"] = list(pick(*(("causes_ar",) if ar else ()), "causes") or [])
            out["checks"] = list(pick(*(("checks_ar",) if ar else ()), "checks") or [])
            out["severity"] = str(pick("severity", "sev") or "")
            if isinstance(out["title"], (tuple, list)):
                out["title"] = out["title"][1 if ar else 0]
    except Exception:  # noqa: BLE001 - the knowledge base is optional
        pass
    out["manufacturer"] = D.manufacturer_specific(code)
    if not out["title"]:
        out["title"] = tr("Manufacturer-specific code") if out["manufacturer"] else ""
    out["group"] = tr(D.category(code))
    return out


# ------------------------------------------------------------------------------------------- helpers
class _Bridge(QObject):
    done = pyqtSignal(object, object, object)
    line = pyqtSignal(str)


def _item(text, data=None, align_right=False) -> QTableWidgetItem:
    it = QTableWidgetItem(str(text))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if data is not None:
        it.setData(ROLE, data)
    if align_right:
        it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    return it


def _table(headers) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels([tr(h) for h in headers])
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setAlternatingRowColors(True)
    t.horizontalHeader().setStretchLastSection(True)
    t.setProperty("i18n_skip_items", True)
    return t


def _hbox(*widgets, stretch=True) -> QHBoxLayout:
    h = QHBoxLayout()
    h.setContentsMargins(0, 0, 0, 0)
    for w in widgets:
        if isinstance(w, int):
            h.addSpacing(w)
        elif w is None:
            h.addStretch(1)
        else:
            h.addWidget(w)
    if stretch:
        h.addStretch(1)
    return h


def _note(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setObjectName("cardiagNote")
    lab.setStyleSheet("color: palette(placeholder-text);")
    return lab


# ------------------------------------------------------------------------------------------- clear dialog
class ClearCodesDialog(QDialog):
    """Mode 04 confirmation: what will be cleared, the readiness warning and safety-relevant faults."""

    def __init__(self, entries, parent=None, ecu_names=None):
        super().__init__(parent)
        from ..cardiag.obd import dtc as D
        from ..cardiag.obd.client import ecu_title
        self.setWindowTitle(tr("Clear Trouble Codes"))
        self.setObjectName("CarDiagClearDialog")
        self.resize(640, 560)
        v = QVBoxLayout(self)
        head = QLabel(tr("Clear the trouble codes of all engine / emissions control units (OBD mode 04)?"))
        head.setWordWrap(True)
        f = head.font()
        f.setBold(True)
        head.setFont(f)
        v.addWidget(head)
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(False)
        ar = _ar()
        html = [f"<h4>{_esc(tr('These codes will be cleared'))}</h4>"]
        clearable = [e for e in entries if e.kinds & {"stored", "pending"}]
        permanent = [e for e in entries if e.kinds == {"permanent"}]
        safety = []
        if clearable:
            html.append("<ul>")
            for e in clearable:
                info = kb_info(e.code)
                why = D.safety_relevant(e.code)
                if why:
                    safety.append((e, why))
                st = ", ".join(tr(D.KIND_TITLES[k]) for k in ("stored", "pending") if k in e.kinds)
                title = info["title"] or info["group"]
                html.append(f"<li><b>{e.code}</b> - {_esc(title)} <i>({_esc(st)}, "
                            f"{_esc(ecu_title(e.ecu, ecu_names))})</i></li>")
            html.append("</ul>")
        else:
            html.append(f"<p>{_esc(tr('No stored or pending codes were read - clearing still resets the readiness monitors and the freeze frames.'))}</p>")
        if permanent:
            codes = ", ".join(e.code for e in permanent)
            html.append(f"<p>{_esc(tr('Permanent codes stay until the computer confirms the repair:'))} <b>{codes}</b></p>")
        if safety:
            html.append(f"<h4 style='color:#d64545'>{_esc(tr('Safety-relevant faults'))}</h4><ul>")
            for e, why in safety:
                html.append(f"<li style='color:#d64545'><b>{e.code}</b>: {_esc(tr(why))} - "
                            f"{_esc(tr('make sure the system works before driving.'))}</li>")
            html.append("</ul>")
        html.append(f"<h4>{_esc(tr('Before you clear'))}</h4><ul>")
        for w in CLEAR_WARNINGS:
            html.append(f"<li>{_esc(w[1] if ar else w[0])}</li>")
        html.append("</ul>")
        self.view.setHtml("".join(html))
        self.view.setProperty("i18n_skip", True)
        v.addWidget(self.view, 1)
        self.safety = safety
        self.ack = QCheckBox(tr("The fault has been repaired (or I only want to check whether it comes back), "
                                "and I understand that the readiness monitors will be reset."))
        self.ack.setObjectName("CarDiagClearAck")
        v.addWidget(self.ack)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.b_clear = bb.addButton(tr("Clear Codes"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.b_clear.setEnabled(False)
        self.ack.toggled.connect(self.b_clear.setEnabled)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)


# ------------------------------------------------------------------------------------------- workbench
class CarDiagWorkbench(QWidget):
    connected = pyqtSignal(bool)

    def __init__(self, win=None, parent=None):
        super().__init__(parent)
        from ..cardiag.obd import pids as P
        self.P = P
        self.win = win
        self.setObjectName("CarDiagWorkbench")
        self.client = None
        self.transport = None
        self.link = None
        self.vehicle = None                     # the demo vehicle when connected to the Demo car
        self.entries = []                       # last DTC read (DtcEntry)
        self.freeze = {}
        self.vinfo = None
        self.ecu_names: dict[str, str] = {}
        self.bridge = _Bridge()
        self.bridge.done.connect(self._done)
        self.bridge.line.connect(self.log_line)
        self._busy_n = 0
        self._polling = False
        self._live_keys: list = []              # [(ecu, pid)]
        self._stats: dict = {}                  # key -> [min, max, last, values]
        self._t0 = time.monotonic()
        self._logger = None
        self._playback = None
        self._log_lines = 0
        self._build()
        self._set_connected(False)
        for hook in list(TAB_HOOKS):
            try:
                hook(self)
            except Exception as e:  # noqa: BLE001 - another slice's tab must not break the scan tool
                self.log_line(f"[tab hook failed] {e}")

    # ================================================================== layout
    def _build(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        # connect bar
        bar = QFrame()
        bar.setObjectName("CarDiagConnectBar")
        bar.setFrameShape(QFrame.Shape.StyledPanel)
        h = QHBoxLayout(bar)
        h.setContentsMargins(6, 4, 6, 4)
        self.adapter = QComboBox()
        self.adapter.setObjectName("CarDiagAdapter")
        for k, t in ADAPTERS:
            self.adapter.addItem(tr(t), k)
        self.port = QComboBox()
        self.port.setEditable(True)
        self.port.setMinimumWidth(170)
        self.port.setObjectName("CarDiagPort")
        self.b_ports = QToolButton()
        self.b_ports.setText("⟳")
        self.b_ports.setToolTip(tr("Refresh the list of ports"))
        self.b_ports.clicked.connect(self.refresh_ports)
        self.protocol = QComboBox()
        self.protocol.setObjectName("CarDiagProtocol")
        for k, t in PROTOCOLS:
            self.protocol.addItem(tr(t), k)
        self.b_connect = QPushButton(tr("Connect"))
        self.b_connect.setObjectName("CarDiagConnect")
        self.b_connect.clicked.connect(self.toggle_connect)
        self.b_demo = QPushButton(tr("Demo Car"))
        self.b_demo.setToolTip(tr("Connect to the built-in demo car (no adapter needed)"))
        self.b_demo.clicked.connect(self.connect_demo)
        self.status = QLabel(tr("Not connected"))
        self.status.setObjectName("CarDiagStatus")
        for w in (QLabel(tr("Adapter:")), self.adapter, QLabel(tr("Port:")), self.port, self.b_ports,
                  QLabel(tr("Protocol:")), self.protocol, self.b_connect, self.b_demo):
            h.addWidget(w)
        h.addWidget(self.status, 1)
        self.adapter.currentIndexChanged.connect(self._adapter_changed)
        v.addWidget(bar)
        # vehicle header
        head = QFrame()
        head.setObjectName("CarDiagHeader")
        head.setFrameShape(QFrame.Shape.StyledPanel)
        hh = QHBoxLayout(head)
        hh.setContentsMargins(8, 4, 8, 4)
        from ..cardiag.obd.widgets import MilLamp
        self.mil_lamp = MilLamp()
        self.h_vin = QLabel("VIN: -")
        self.h_vin.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        fv = self.h_vin.font()
        fv.setBold(True)
        self.h_vin.setFont(fv)
        self.h_proto = QLabel("")
        self.h_ecus = QLabel("")
        self.h_mil = QLabel(tr("MIL: -"))
        self.h_dtc = QLabel("")
        self.h_volt = QLabel("")
        for w in (self.h_vin, self.h_proto, self.h_ecus):
            hh.addWidget(w)
            hh.addSpacing(14)
        hh.addStretch(1)
        for w in (self.mil_lamp, self.h_mil, self.h_dtc, self.h_volt):
            hh.addWidget(w)
            hh.addSpacing(10)
        v.addWidget(head)
        # tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("CarDiagTabs")
        self.tabs.addTab(self._build_faults(), tr("Faults"))
        self.tabs.addTab(self._build_live(), tr("Live Data"))
        self.tabs.addTab(self._build_freeze(), tr("Freeze Frame"))
        self.tabs.addTab(self._build_readiness(), tr("Readiness"))
        self.tabs.addTab(self._build_tests(), tr("Tests (06)"))
        self.tabs.addTab(self._build_info(), tr("Info (09)"))
        self.tabs.addTab(self._build_log(), tr("Log"))
        v.addWidget(self.tabs, 1)
        self._adapter_changed()

    def add_tab(self, widget: QWidget, title: str, before_log: bool = True) -> int:
        """For other slices: add a tab (before the Log tab)."""
        i = self.tabs.count() - 1 if before_log else self.tabs.count()
        return self.tabs.insertTab(i, widget, tr(title))

    def tab_index(self, title: str) -> int:
        for i in range(self.tabs.count()):
            if self.tabs.widget(i).objectName() == f"CarDiagTab_{title}" or self.tabs.tabText(i) in (title, tr(title)):
                return i
        return -1

    # ------------------------------------------------------------------ Faults
    def _build_faults(self) -> QWidget:
        w = QWidget()
        w.setObjectName("CarDiagTab_Faults")
        v = QVBoxLayout(w)
        self.b_read = QPushButton(tr("Read Codes"))
        self.b_read.setObjectName("CarDiagReadCodes")
        self.b_read.clicked.connect(self.read_codes)
        self.b_clear = QPushButton(tr("Clear Codes..."))
        self.b_clear.setObjectName("CarDiagClearCodes")
        self.b_clear.clicked.connect(lambda: self.clear_codes())
        self.b_ff = QPushButton(tr("Show Freeze Frame"))
        self.b_ff.clicked.connect(self._goto_freeze)
        self.fault_summary = QLabel(tr("Connect to a car and read the codes."))
        v.addLayout(_hbox(self.b_read, self.b_clear, self.b_ff, 12, self.fault_summary))
        sp = QSplitter(Qt.Orientation.Horizontal)
        self.dtc_tree = QTreeWidget()
        self.dtc_tree.setObjectName("CarDiagDtcTree")
        self.dtc_tree.setHeaderLabels([tr("Code"), tr("Status"), tr("Control unit"), tr("Description")])
        self.dtc_tree.setRootIsDecorated(False)
        self.dtc_tree.setAlternatingRowColors(True)
        self.dtc_tree.setProperty("i18n_skip_items", True)
        self.dtc_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.dtc_tree.currentItemChanged.connect(lambda *_: self._show_dtc())
        sp.addWidget(self.dtc_tree)
        self.dtc_view = QTextBrowser()
        self.dtc_view.setObjectName("CarDiagDtcView")
        self.dtc_view.setProperty("i18n_skip", True)
        self.dtc_view.setOpenLinks(False)
        self.dtc_view.anchorClicked.connect(self._dtc_link)
        sp.addWidget(self.dtc_view)
        sp.setSizes([520, 480])
        v.addWidget(sp, 1)
        v.addWidget(_note(tr("Stored = confirmed fault, Pending = seen once (early warning), Permanent = cleared "
                             "only by the car itself after the repair. Clearing a code does not repair the fault.")))
        return w

    # ------------------------------------------------------------------ Live data
    def _build_live(self) -> QWidget:
        from ..cardiag.obd.widgets import Gauge, Plot
        w = QWidget()
        w.setObjectName("CarDiagTab_Live")
        v = QVBoxLayout(w)
        self.b_live = QPushButton(tr("Start"))
        self.b_live.setObjectName("CarDiagLiveStart")
        self.b_live.setCheckable(True)
        self.b_live.toggled.connect(self.set_live)
        self.rate = QSpinBox()
        self.rate.setRange(50, 10000)
        self.rate.setSingleStep(50)
        self.rate.setValue(500)
        self.rate.setSuffix(" ms")
        self.rate.setObjectName("CarDiagRate")
        self.rate.valueChanged.connect(lambda ms: self.live_timer.setInterval(ms))
        self.b_rec = QPushButton(tr("Record CSV..."))
        self.b_rec.setObjectName("CarDiagRecord")
        self.b_rec.setCheckable(True)
        self.b_rec.toggled.connect(self._toggle_record)
        self.b_play = QPushButton(tr("Play Log..."))
        self.b_play.clicked.connect(lambda: self.play_log())
        self.b_reset = QPushButton(tr("Reset Min/Max"))
        self.b_reset.clicked.connect(self._reset_stats)
        self.live_info = QLabel("")
        v.addLayout(_hbox(self.b_live, QLabel(tr("Sample every")), self.rate, 10, self.b_rec, self.b_play,
                          self.b_reset, 10, self.live_info))
        # playback bar (hidden until a log is loaded)
        self.play_bar = QWidget()
        pb = QHBoxLayout(self.play_bar)
        pb.setContentsMargins(0, 0, 0, 0)
        self.b_pause = QPushButton(tr("Pause"))
        self.b_pause.setCheckable(True)
        self.play_speed = QComboBox()
        for s in ("0.5x", "1x", "2x", "4x", "10x"):
            self.play_speed.addItem(s, float(s[:-1]))
        self.play_speed.setCurrentIndex(1)
        self.play_pos = QSlider(Qt.Orientation.Horizontal)
        self.play_pos.sliderMoved.connect(self._seek)
        self.play_lab = QLabel("")
        self.b_stop_play = QPushButton(tr("Close Log"))
        self.b_stop_play.clicked.connect(self.stop_playback)
        for x in (QLabel(tr("Playback:")), self.b_pause, self.play_speed, self.play_pos, self.play_lab, self.b_stop_play):
            pb.addWidget(x, 1 if x is self.play_pos else 0)
        self.play_bar.hide()
        v.addWidget(self.play_bar)
        sp = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        self.preset = QComboBox()
        self.preset.addItem(tr("Choose a preset..."), "")
        for k in PRESETS:
            self.preset.addItem(tr(k), k)
        self.preset.activated.connect(self._apply_preset)
        self.pid_filter = QLineEdit()
        self.pid_filter.setPlaceholderText(tr("Filter PIDs"))
        self.pid_filter.textChanged.connect(self._filter_pids)
        self.pid_tree = QTreeWidget()
        self.pid_tree.setObjectName("CarDiagPidTree")
        self.pid_tree.setHeaderLabels([tr("PID"), tr("Control unit")])
        self.pid_tree.setProperty("i18n_skip_items", True)
        self.pid_tree.itemChanged.connect(self._pid_checked)
        lv.addWidget(self.preset)
        lv.addWidget(self.pid_filter)
        lv.addWidget(self.pid_tree, 1)
        sp.addWidget(left)
        right = QSplitter(Qt.Orientation.Vertical)
        gw = QWidget()
        self.gauge_grid = QGridLayout(gw)
        self.gauge_grid.setContentsMargins(0, 0, 0, 0)
        self.gauges = [Gauge() for _ in range(4)]
        for i, g in enumerate(self.gauges):
            g.setObjectName(f"CarDiagGauge{i}")
            self.gauge_grid.addWidget(g, 0, i)
            g.hide()
        right.addWidget(gw)
        self.live_table = _table(["Name", "Value", "Unit", "Min", "Max", "Control unit"])
        self.live_table.setObjectName("CarDiagLiveTable")
        self.live_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.live_table.horizontalHeader().setStretchLastSection(False)
        right.addWidget(self.live_table)
        self.plot = Plot()
        self.plot.setObjectName("CarDiagPlot")
        right.addWidget(self.plot)
        right.setSizes([200, 220, 240])
        sp.addWidget(right)
        sp.setSizes([300, 900])
        v.addWidget(sp, 1)
        self.live_timer = QTimer(self)
        self.live_timer.setInterval(500)
        self.live_timer.timeout.connect(self._poll)
        self.play_timer = QTimer(self)
        self.play_timer.setInterval(100)
        self.play_timer.timeout.connect(self._play_step)
        return w

    # ------------------------------------------------------------------ Freeze frame
    def _build_freeze(self) -> QWidget:
        w = QWidget()
        w.setObjectName("CarDiagTab_Freeze")
        v = QVBoxLayout(w)
        self.b_ff_read = QPushButton(tr("Read Freeze Frame"))
        self.b_ff_read.setObjectName("CarDiagReadFreeze")
        self.b_ff_read.clicked.connect(self.read_freeze)
        self.ff_ecu = QComboBox()
        self.ff_ecu.currentIndexChanged.connect(lambda *_: self._show_freeze())
        self.b_ff_fault = QPushButton(tr("Go to Fault"))
        self.b_ff_fault.clicked.connect(self._goto_fault)
        v.addLayout(_hbox(self.b_ff_read, QLabel(tr("Control unit:")), self.ff_ecu, self.b_ff_fault))
        self.ff_head = QLabel(tr("A freeze frame is a snapshot of the engine data taken at the moment a fault was "
                                 "stored - it shows the conditions (temperature, speed, load) when it happened."))
        self.ff_head.setWordWrap(True)
        self.ff_head.setObjectName("CarDiagFreezeHead")
        v.addWidget(self.ff_head)
        self.ff_table = _table(["PID", "Name", "Value", "Unit"])
        self.ff_table.setObjectName("CarDiagFreezeTable")
        self.ff_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ff_table.horizontalHeader().setStretchLastSection(False)
        v.addWidget(self.ff_table, 1)
        return w

    # ------------------------------------------------------------------ Readiness
    def _build_readiness(self) -> QWidget:
        w = QWidget()
        w.setObjectName("CarDiagTab_Readiness")
        v = QVBoxLayout(w)
        self.b_ready = QPushButton(tr("Read Readiness"))
        self.b_ready.setObjectName("CarDiagReadReadiness")
        self.b_ready.clicked.connect(self.read_readiness)
        self.r_since = QRadioButton(tr("Since codes cleared (01 01)"))
        self.r_cycle = QRadioButton(tr("This drive cycle (01 41)"))
        self.r_since.setChecked(True)
        grp = QButtonGroup(w)
        grp.addButton(self.r_since)
        grp.addButton(self.r_cycle)
        self.r_cycle.toggled.connect(lambda on: self.read_readiness() if self.client else None)
        v.addLayout(_hbox(self.b_ready, self.r_since, self.r_cycle))
        self.ready_summary = QLabel("")
        self.ready_summary.setObjectName("CarDiagReadySummary")
        self.ready_summary.setWordWrap(True)
        f = self.ready_summary.font()
        f.setBold(True)
        self.ready_summary.setFont(f)
        v.addWidget(self.ready_summary)
        sp = QSplitter(Qt.Orientation.Horizontal)
        self.ready_table = _table(["Monitor", "Status", "Type", "Control unit"])
        self.ready_table.setObjectName("CarDiagReadyTable")
        self.ready_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ready_table.horizontalHeader().setStretchLastSection(False)
        self.ready_table.currentCellChanged.connect(lambda *_: self._show_monitor())
        sp.addWidget(self.ready_table)
        self.ready_view = QTextBrowser()
        self.ready_view.setObjectName("CarDiagReadyView")
        self.ready_view.setProperty("i18n_skip", True)
        sp.addWidget(self.ready_view)
        sp.setSizes([520, 480])
        v.addWidget(sp, 1)
        return w

    # ------------------------------------------------------------------ Tests (06)
    def _build_tests(self) -> QWidget:
        w = QWidget()
        w.setObjectName("CarDiagTab_Tests")
        v = QVBoxLayout(w)
        self.b_tests = QPushButton(tr("Read Test Results"))
        self.b_tests.setObjectName("CarDiagReadTests")
        self.b_tests.clicked.connect(self.read_tests)
        self.tests_failed = QCheckBox(tr("Only failed tests"))
        self.tests_failed.toggled.connect(lambda *_: self._show_tests())
        self.tests_summary = QLabel("")
        v.addLayout(_hbox(self.b_tests, self.tests_failed, 12, self.tests_summary))
        self.tests_tree = QTreeWidget()
        self.tests_tree.setObjectName("CarDiagTestsTree")
        self.tests_tree.setHeaderLabels([tr("Monitor / test"), tr("Value"), tr("Min"), tr("Max"), tr("Unit"),
                                         tr("Result"), tr("Control unit")])
        self.tests_tree.setProperty("i18n_skip_items", True)
        self.tests_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tests_tree.header().setStretchLastSection(False)
        v.addWidget(self.tests_tree, 1)
        v.addWidget(_note(tr("Mode 06 shows the raw results of the computer's own self-tests with their limits. A "
                             "result just inside a limit points to a part that is wearing out before a code is set. "
                             "Tests that have not run since the last clear show zero.")))
        self.tests = {}
        return w

    # ------------------------------------------------------------------ Info (09)
    def _build_info(self) -> QWidget:
        w = QWidget()
        w.setObjectName("CarDiagTab_Info")
        v = QVBoxLayout(w)
        self.b_info = QPushButton(tr("Read Vehicle Info"))
        self.b_info.setObjectName("CarDiagReadInfo")
        self.b_info.clicked.connect(self.read_info)
        self.b_fw = QPushButton(tr("Firmware & ECU Workbench..."))
        self.b_fw.setToolTip(tr("Study an ECU firmware file (Tools > Firmware & ECU)"))
        self.b_fw.clicked.connect(self._open_firmware)
        v.addLayout(_hbox(self.b_info, self.b_fw))
        self.info_view = QTextBrowser()
        self.info_view.setObjectName("CarDiagInfoView")
        self.info_view.setProperty("i18n_skip", True)
        v.addWidget(self.info_view, 1)
        return w

    # ------------------------------------------------------------------ Log
    def _build_log(self) -> QWidget:
        w = QWidget()
        w.setObjectName("CarDiagTab_Log")
        v = QVBoxLayout(w)
        self.log_live = QCheckBox(tr("Log live data traffic"))
        b_clear = QPushButton(tr("Clear"))
        b_save = QPushButton(tr("Save Log..."))
        b_clear.clicked.connect(lambda: (self.log_view.clear(), setattr(self, "_log_lines", 0)))
        b_save.clicked.connect(self.save_log)
        v.addLayout(_hbox(self.log_live, b_clear, b_save))
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("CarDiagLogView")
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(20000)
        self.log_view.setFont(QFont("Consolas", 9))
        self.log_view.setProperty("i18n_skip", True)
        v.addWidget(self.log_view, 1)
        return w

    # ================================================================== background work
    def _sync(self) -> bool:
        from ..cardiag.obd.transport import DemoTransport
        return isinstance(self.transport, DemoTransport)

    def run(self, fn, cb=None, what: str = "") -> None:
        """Run fn() off the UI thread (inline for the Demo car); cb(result, error) on the UI thread."""
        if self._sync():
            try:
                r, e = fn(), None
            except Exception as ex:  # noqa: BLE001
                r, e = None, ex
            self._finish(cb, r, e)
            return
        self._busy(+1, what)

        def work():
            try:
                r, e = fn(), None
            except Exception as ex:  # noqa: BLE001
                r, e = None, ex
            self.bridge.done.emit(cb, r, e)
        threading.Thread(target=work, daemon=True, name="cardiag-obd").start()

    def _done(self, cb, r, e) -> None:
        self._busy(-1)
        self._finish(cb, r, e)

    def _finish(self, cb, r, e) -> None:
        if e is not None:
            self.log_line(f"! {e}")
            self.status.setText(tr("Error:") + f" {e}")
        if cb is not None:
            try:
                cb(r, e)
            except Exception as ex:  # noqa: BLE001
                self.log_line(f"! UI update failed: {ex}")

    def _busy(self, d: int, what: str = "") -> None:
        self._busy_n = max(0, self._busy_n + d)
        if d > 0 and what:
            self.status.setText(tr(what))
        if self._busy_n == 0 and self.client is not None and d < 0:
            self.status.setText(tr("Connected"))

    # ================================================================== connection
    def _adapter_changed(self) -> None:
        k = self.adapter.currentData()
        self.port.setEnabled(k in ("elm_serial", "elm_wifi", "elm_ble", "j2534"))
        self.b_demo.setEnabled(True)
        self.b_ports.setEnabled(k in ("elm_serial", "elm_ble", "j2534"))
        self.protocol.setEnabled(k not in ("demo", "demo_elm"))
        if k == "elm_wifi" and not self.port.currentText():
            self.port.setEditText("192.168.0.10:35000")
        if k in ("elm_serial", "j2534", "elm_ble") and self.port.count() == 0:
            self.refresh_ports()

    def refresh_ports(self) -> None:
        k = self.adapter.currentData()
        self.port.clear()
        items = []
        try:
            if k == "elm_serial":
                from ..cardiag.link import ports
                items = [(getattr(p, "label", p.device), p.device) for p in ports.list_ports()]
            elif k == "j2534":
                from ..cardiag.link import j2534
                items = [(f"{d.name} ({d.vendor})" if getattr(d, "vendor", "") else d.name, d.library)
                         for d in j2534.devices()]
            elif k == "elm_ble":
                from ..cardiag.link import ble
                lst = ble.scan(4.0)
                items = [(getattr(d, "name", str(d)) or getattr(d, "address", ""), getattr(d, "address", str(d)))
                         for d in lst]
        except Exception as e:  # noqa: BLE001
            self.log_line(f"[ports] {e}")
        for text, data in items:
            self.port.addItem(text, data)
        if not items and k == "elm_serial":
            self.port.setEditText("COM3")

    def toggle_connect(self) -> None:
        if self.client is not None:
            self.disconnect()
            return
        k = self.adapter.currentData()
        if k == "demo":
            self.connect_demo()
            return
        port = self.port.currentData() or self.port.currentText().split(":")[0].strip() if k == "elm_serial" else             (self.port.currentData() or self.port.currentText().strip())
        proto = self.protocol.currentData()
        self.status.setText(tr("Connecting..."))

        def work():
            return _open_link(k, port, proto)

        def done(link, err):
            if err is not None or link is None:
                self.status.setText(tr("Connection failed:") + f" {err}")
                self._msg("warning", "Car Diagnostics", tr("Could not connect to the adapter.") + f"\n\n{_err_text(err)}")
                return
            from ..cardiag.obd.transport import LinkTransport
            self._attach(LinkTransport(link), link=link)
            try:                                       # the service functions use the same connection
                from ..cardiag.link import set_current_link
                set_current_link(link)
            except Exception:  # noqa: BLE001
                pass
        # opening an adapter takes seconds: always in the background
        self._busy(+1, "Connecting...")

        def thread():
            try:
                r, e = work(), None
            except Exception as ex:  # noqa: BLE001
                r, e = None, ex
            self.bridge.done.emit(done, r, e)
        threading.Thread(target=thread, daemon=True, name="cardiag-connect").start()

    def connect_demo(self, vehicle=None):
        """Connect to the built-in demo car (radide/cardiag/obd/vehicle.py)."""
        from ..cardiag.obd.transport import DemoTransport
        from ..cardiag.obd.vehicle import DemoVehicle
        if self.client is not None:
            self.disconnect()
        self.adapter.setCurrentIndex(0)
        self.vehicle = vehicle or DemoVehicle()
        self._attach(DemoTransport(self.vehicle))
        return self.client

    def _attach(self, transport, link=None) -> None:
        from ..cardiag.obd.client import ObdClient
        self.transport, self.link = transport, link
        self.client = ObdClient(transport)
        self.client.listeners.append(self._traffic)
        self._set_connected(True)
        self.log_line(f"# {tr('Connected')}: {transport.describe()}")
        self.status.setText(tr("Connected"))
        self.h_proto.setText(getattr(transport, "protocol", "") or "")
        self.refresh_header(full=True)

    def disconnect(self) -> None:
        self.set_live(False)
        self.b_live.setChecked(False)
        if self.link is not None:
            try:
                from ..cardiag.link import current_link, set_current_link
                if current_link() is self.link:
                    set_current_link(None)
            except Exception:  # noqa: BLE001
                pass
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:  # noqa: BLE001
                pass
        self.client = self.transport = self.link = self.vehicle = None
        self._set_connected(False)
        self.log_line(f"# {tr('Disconnected')}")
        self.status.setText(tr("Not connected"))

    def _set_connected(self, on: bool) -> None:
        self.b_connect.setText(tr("Disconnect") if on else tr("Connect"))
        for b in (self.b_read, self.b_clear, self.b_live, self.b_ff_read, self.b_ready, self.b_tests, self.b_info,
                  self.b_rec):
            b.setEnabled(on)
        self.adapter.setEnabled(not on)
        if not on:
            self.h_vin.setText("VIN: -")
            self.h_ecus.setText("")
            self.h_dtc.setText("")
            self.h_volt.setText("")
            self.h_proto.setText("")
            self.mil_lamp.set_state(None)
            self.h_mil.setText(tr("MIL: -"))
        self.connected.emit(on)

    def refresh_header(self, full: bool = False) -> None:
        c = self.client
        if c is None:
            return

        def work():
            out = {"ready": c.readiness()}
            if full:
                out["sup"] = c.supported_pids(refresh=True)
                out["info"] = c.vehicle_info()
            v = getattr(self.transport, "voltage", None)
            out["volt"] = v() if callable(v) else None
            if out["volt"] is None:
                r = c.read_pid(0x42)
                out["volt"] = next((x.value for x in r.values()), None)
            return out

        def done(r, e):
            if e is not None or not r:
                return
            if "info" in r:
                self.vinfo = r["info"]
                self.ecu_names.update({k: v for k, v in r["info"].names.items() if v})
                self.h_vin.setText(f"VIN: {r['info'].vin or '-'}")
                self._fill_pids(r["sup"])
                self._show_info()
            ecus = sorted(set(r.get("sup", {}) or {}) | set(r["ready"]))
            if ecus:
                self.h_ecus.setText(tr("Control units:") + f" {len(ecus)}")
                self.h_ecus.setToolTip("\n".join(self._ecu(e) for e in ecus))
            mil = any(s.mil for s in r["ready"].values())
            n = sum(s.dtc_count for s in r["ready"].values())
            self.mil_lamp.set_state(mil if r["ready"] else None)
            self.h_mil.setText(tr("MIL: ON") if mil else tr("MIL: OFF"))
            self.h_dtc.setText(tr("Confirmed codes:") + f" {n}")
            if r.get("volt") is not None:
                self.h_volt.setText(tr("Battery:") + f" {r['volt']:.1f} V")
        self.run(work, done, "Reading vehicle data...")

    def _ecu(self, ecu: str) -> str:
        from ..cardiag.obd.client import ecu_title
        return ecu_title(ecu, self.ecu_names)

    # ================================================================== faults
    def read_codes(self) -> None:
        if self.client is None:
            return
        c = self.client

        def done(entries, e):
            if e is not None:
                return
            self.entries = entries or []
            self._fill_dtcs()
            self.refresh_header()
        self.run(c.read_all_dtcs, done, "Reading trouble codes...")

    def _fill_dtcs(self) -> None:
        from ..cardiag.obd import dtc as D
        self.dtc_tree.clear()
        for e in self.entries:
            info = kb_info(e.code)
            st = ", ".join(tr(D.KIND_TITLES[k]) for k in ("stored", "pending", "permanent") if k in e.kinds)
            it = QTreeWidgetItem([e.code, st, self._ecu(e.ecu), info["title"] or info["group"]])
            it.setData(0, ROLE, (e.ecu, e.code))
            f = it.font(0)
            f.setBold(True)
            it.setFont(0, f)
            if D.safety_relevant(e.code):
                it.setForeground(0, QColor("#d64545"))
                it.setToolTip(0, tr(D.safety_relevant(e.code)))
            elif "pending" in e.kinds and "stored" not in e.kinds:
                it.setForeground(0, QColor("#c98a00"))
            self.dtc_tree.addTopLevelItem(it)
        for i in range(3):
            self.dtc_tree.resizeColumnToContents(i)
        ecus = {e.ecu for e in self.entries}
        if self.entries:
            self.fault_summary.setText(tr(f"{len(self.entries)} code(s) from {len(ecus)} control unit(s)"))
            self.dtc_tree.setCurrentItem(self.dtc_tree.topLevelItem(0))
        else:
            self.fault_summary.setText(tr("No trouble codes stored - the engine computers report no faults."))
            self.dtc_view.setHtml(f"<p>{_esc(tr('No trouble codes stored - the engine computers report no faults.'))}</p>"
                                  f"<p>{_esc(tr('A warning lamp that is on without any code may belong to a system that is not part of OBD (ABS, airbag, service reminder): see the warning-light guide.'))}</p>")

    def _show_dtc(self) -> None:
        from ..cardiag.obd import dtc as D
        it = self.dtc_tree.currentItem()
        if it is None:
            return
        ecu, code = it.data(0, ROLE)
        e = next((x for x in self.entries if x.code == code and x.ecu == ecu), None)
        info = kb_info(code)
        h = [f"<h2 style='margin-bottom:2px'>{code}</h2>"]
        if info["title"]:
            h.append(f"<h3 style='margin-top:0'>{_esc(info['title'])}</h3>")
        h.append(f"<p><b>{_esc(tr('System:'))}</b> {_esc(tr(D.SYSTEMS.get(code[0], '')))}<br>"
                 f"<b>{_esc(tr('Group:'))}</b> {_esc(info['group'])}<br>"
                 f"<b>{_esc(tr('Control unit:'))}</b> {_esc(self._ecu(ecu))}</p>")
        why = D.safety_relevant(code)
        if why:
            h.append(f"<p style='color:#d64545'><b>{_esc(tr('Safety-relevant:'))}</b> {_esc(tr(why))}. "
                     f"{_esc(tr('Have it checked before driving on; do not clear it just to turn the lamp off.'))}</p>")
        if info["explain"]:
            h.append(f"<p>{_esc(info['explain'])}</p>")
        if info["causes"]:
            h.append(f"<h4>{_esc(tr('Possible causes'))}</h4><ul>"
                     + "".join(f"<li>{_esc(c)}</li>" for c in info["causes"]) + "</ul>")
        if info["checks"]:
            h.append(f"<h4>{_esc(tr('What to check'))}</h4><ol>"
                     + "".join(f"<li>{_esc(c)}</li>" for c in info["checks"]) + "</ol>")
        if info["manufacturer"] and not info["explain"]:
            h.append(f"<p>{_esc(tr('This is a manufacturer-specific code: its meaning depends on the make. Import the manufacturer definitions (CSV / JSON) to see a description.'))}</p>")
        elif not info["explain"]:
            h.append(f"<p>{_esc(tr('No detailed explanation for this code in the knowledge base yet.'))}</p>")
        if e is not None:
            h.append(f"<h4>{_esc(tr('Status'))}</h4><ul>")
            for k in ("stored", "pending", "permanent"):
                if k in e.kinds:
                    h.append(f"<li>{_esc(bi(KIND_EXPLAIN[k]))}</li>")
            h.append("</ul>")
        ff = self.freeze.get(ecu)
        if ff is not None and ff.dtc == code:
            h.append(f"<p><a href='freeze:{ecu}'>{_esc(tr('Show the freeze frame stored with this code'))}</a></p>")
        elif e is not None and "stored" in e.kinds:
            h.append(f"<p><a href='freeze:{ecu}'>{_esc(tr('Read the freeze frame'))}</a></p>")
        self.dtc_view.setHtml("".join(h))

    def _dtc_link(self, url) -> None:
        s = url.toString()
        if s.startswith("freeze:"):
            self._goto_freeze(s.split(":", 1)[1])

    def clear_codes(self, confirmed: bool | None = None) -> None:
        """Mode 04 after a confirmation (confirmed=True skips the dialog - tests / scripts)."""
        if self.client is None:
            return
        if confirmed is None:
            dlg = ClearCodesDialog(self.entries, self, self.ecu_names)
            self.last_clear_dialog = dlg
            confirmed = dlg.exec() == QDialog.DialogCode.Accepted
        if not confirmed:
            return
        c = self.client
        cleared_codes = [e.code for e in self.entries if e.kinds & {"stored", "pending"}]

        def done(r, e):
            if e is not None:
                return
            ok = [k for k, v in (r or {}).items() if v]
            bad = [k for k, v in (r or {}).items() if not v]
            self.log_line(f"# {tr('Clear codes')}: OK {ok} / refused {bad} - {', '.join(cleared_codes) or '-'}")
            if bad:
                self._msg("warning", "Clear Trouble Codes",
                          tr("Some control units refused to clear the codes (the engine may be running).")
                          + "\n" + ", ".join(self._ecu(b) for b in bad))
            elif not ok:
                self._msg("warning", "Clear Trouble Codes", tr("No control unit answered the clear request."))
            self.freeze = {}
            self._show_freeze()
            self.read_codes()
            self.read_readiness()
        self.run(c.clear_dtcs, done, "Clearing trouble codes...")

    # ================================================================== live data
    def _fill_pids(self, sup: dict) -> None:
        P = self.P
        checked = set(self._live_keys)
        self.pid_tree.blockSignals(True)
        self.pid_tree.clear()
        groups: dict[str, QTreeWidgetItem] = {}
        for ecu in sorted(sup):
            for pid in sorted(sup[ecu]):
                if pid in P.BITMAP_PIDS:
                    continue
                p = P.get(pid)
                g = groups.get(p.group)
                if g is None:
                    g = QTreeWidgetItem([tr(p.group), ""])
                    g.setFlags(g.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                    groups[p.group] = g
                    self.pid_tree.addTopLevelItem(g)
                it = QTreeWidgetItem([f"{pid:02X}  {tr(p.name)}", ecu])
                it.setData(0, ROLE, (ecu, pid))
                it.setToolTip(0, f"{tr(p.name)}  [{p.unit}]" if p.unit else tr(p.name))
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(0, Qt.CheckState.Checked if (ecu, pid) in checked else Qt.CheckState.Unchecked)
                g.addChild(it)
        self.pid_tree.expandAll()
        self.pid_tree.resizeColumnToContents(0)
        self.pid_tree.blockSignals(False)
        if not checked:
            self.select_pids(PRESETS["Basic engine"])

    def _pid_items(self):
        for i in range(self.pid_tree.topLevelItemCount()):
            g = self.pid_tree.topLevelItem(i)
            for j in range(g.childCount()):
                yield g.child(j)

    def select_pids(self, pids, ecu: str | None = None) -> None:
        """Tick these PIDs (first ECU that supports each one unless ecu is given) and untick the others."""
        want = list(pids)
        chosen = []
        for pid in want:
            for it in self._pid_items():
                e, p = it.data(0, ROLE)
                if p == pid and (ecu is None or e == ecu):
                    chosen.append((e, p))
                    break
        self.pid_tree.blockSignals(True)
        for it in self._pid_items():
            it.setCheckState(0, Qt.CheckState.Checked if it.data(0, ROLE) in chosen else Qt.CheckState.Unchecked)
        self.pid_tree.blockSignals(False)
        self._set_live_keys(chosen)

    def _apply_preset(self) -> None:
        k = self.preset.currentData()
        if k:
            self.select_pids(PRESETS[k])

    def _filter_pids(self, text: str) -> None:
        t = text.lower().strip()
        for i in range(self.pid_tree.topLevelItemCount()):
            g = self.pid_tree.topLevelItem(i)
            vis = 0
            for j in range(g.childCount()):
                c = g.child(j)
                hide = bool(t) and t not in c.text(0).lower() and t not in c.toolTip(0).lower()
                c.setHidden(hide)
                vis += not hide
            g.setHidden(vis == 0)

    def _pid_checked(self, it, col) -> None:
        if it.data(0, ROLE) is None:
            return
        keys = [x.data(0, ROLE) for x in self._pid_items() if x.checkState(0) == Qt.CheckState.Checked]
        order = [k for k in self._live_keys if k in keys] + [k for k in keys if k not in self._live_keys]
        self._set_live_keys(order)

    def _channel(self, key):
        """key -> (label, unit, lo, hi)."""
        P = self.P
        ecu, pid = key
        if isinstance(pid, int):
            p = P.get(pid)
            return tr(p.short), p.unit, p.lo, p.hi
        rec = self._playback
        lo = hi = None
        if rec is not None and key in rec.keys():
            vals = [v for v in rec.data[rec.keys().index(key)] if v is not None]
            if vals:
                lo, hi = min(vals), max(vals)
        return str(pid), "", lo or 0.0, hi if hi is not None and hi > (lo or 0) else (lo or 0) + 1

    def _set_live_keys(self, keys) -> None:
        self._live_keys = list(keys)
        P = self.P
        graph = [k for k in self._live_keys if not isinstance(k[1], int) or P.is_graphable(k[1])]
        for i, g in enumerate(self.gauges):
            if i < len(graph):
                lab, unit, lo, hi = self._channel(graph[i])
                g.label, g.unit, g.lo, g.hi = lab, unit, float(lo), float(hi if hi > lo else lo + 1)
                g.red_from = 6000.0 if isinstance(graph[i][1], int) and graph[i][1] == 0x0C else \
                    (110.0 if isinstance(graph[i][1], int) and graph[i][1] == 0x05 else None)
                g.setProperty("key", graph[i])
                g.reset()
                g.show()
            else:
                g.setProperty("key", None)
                g.hide()
        self.plot.set_channels([(k, *self._channel(k)) for k in graph[:8]])
        self.live_table.setRowCount(len(self._live_keys))
        for r, k in enumerate(self._live_keys):
            lab, unit, _lo, _hi = self._channel(k)
            name = tr(P.get(k[1]).name) if isinstance(k[1], int) else str(k[1])
            self.live_table.setItem(r, 0, _item(name, k))
            for c, txt in ((1, "-"), (2, unit), (3, "-"), (4, "-"), (5, self._ecu(k[0]) if k[0] else "")):
                self.live_table.setItem(r, c, _item(txt, align_right=c in (1, 3, 4)))
        self.live_table.resizeColumnsToContents()
        self.live_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._stats = {k: v for k, v in self._stats.items() if k in self._live_keys}

    def set_live(self, on: bool) -> None:
        if on and self.client is None:
            self.b_live.setChecked(False)
            return
        if on:
            self.stop_playback()
            self._t0 = time.monotonic()
            self._vt0 = getattr(self.vehicle, "t", 0.0)
            self.plot.clear()
            self.live_timer.start(self.rate.value())
            self._poll()
        else:
            self.live_timer.stop()
        self.b_live.setText(tr("Stop") if on else tr("Start"))

    def _poll(self) -> None:
        if self.client is None or self._polling or not self._live_keys:
            return
        self._polling = True
        c = self.client
        pids = sorted({p for _e, p in self._live_keys if isinstance(p, int)})
        quiet = not self.log_live.isChecked()

        def work():
            if quiet:
                c.listeners_paused = True
            try:
                return c.read_pids(pids)
            finally:
                c.listeners_paused = False

        def done(readings, e):
            self._polling = False
            if e is not None or readings is None:
                return
            t = self._now()
            by = {(r.ecu, r.pid): r for r in readings}
            vals = {}
            for k in self._live_keys:
                r = by.get(k)
                if r is not None:
                    vals[k] = r
            self._show_values(vals, t)
            if self._logger is not None:
                self._logger.write({k: r.value for k, r in vals.items()}, t)
                self.live_info.setText(tr("Recording:") + f" {self._logger.rows} " + tr("samples"))
        self.run(work, done)

    def _now(self) -> float:
        """Seconds since live data started (the demo car's own clock when it runs on sim time - tests)."""
        v = self.vehicle
        if v is not None and not getattr(v, "realtime", True):
            return v.t - getattr(self, "_vt0", 0.0)
        return time.monotonic() - self._t0

    def _show_values(self, vals: dict, t: float) -> None:
        """vals: key -> Reading (live) or float (playback)."""
        from ..cardiag.obd.widgets import fmt
        for r, k in enumerate(self._live_keys):
            x = vals.get(k)
            if x is None:
                continue
            if isinstance(x, (int, float)):
                num, text = float(x), fmt(float(x))
            else:
                num = x.value
                vs = x.values
                text = "; ".join(tr(str(v.value)) if not isinstance(v.value, (int, float)) else fmt(v.value)
                                 + (f" {v.unit}" if j else "") for j, v in enumerate(vs[:4])) if vs else "-"
                if num is not None and len(vs) == 1:
                    text = fmt(num)
            st = self._stats.setdefault(k, [None, None])
            if num is not None:
                st[0] = num if st[0] is None else min(st[0], num)
                st[1] = num if st[1] is None else max(st[1], num)
            self.live_table.item(r, 1).setText(text)
            self.live_table.item(r, 3).setText(fmt(st[0]))
            self.live_table.item(r, 4).setText(fmt(st[1]))
            self.plot.add(k, t, num)
            for g in self.gauges:
                if g.property("key") == k:
                    g.set_value(num)
        self.plot.update()

    def _reset_stats(self) -> None:
        self._stats = {}
        for g in self.gauges:
            g.vmin = g.vmax = None
        for r in range(self.live_table.rowCount()):
            for c in (3, 4):
                self.live_table.item(r, c).setText("-")

    # ------------------------------------------------------------------ CSV record / playback
    def _toggle_record(self, on: bool) -> None:
        if on:
            path = getattr(self, "_record_path", None)
            if not path:
                start = str(Path.home() / f"obd-log-{datetime.now():%Y%m%d-%H%M%S}.csv")
                path, _ = QFileDialog.getSaveFileName(self, tr("Record Live Data to CSV"), start, "CSV (*.csv)")
            self._record_path = None
            if not path:
                self.b_rec.setChecked(False)
                return
            self.start_recording(path)
        else:
            self.stop_recording()

    def start_recording(self, path: str):
        from ..cardiag.obd.logger import CsvLogger
        keys = [k for k in self._live_keys if isinstance(k[1], int)]
        self._logger = CsvLogger(path, keys)
        self.log_line(f"# {tr('Recording live data to')} {path}")
        self.b_rec.blockSignals(True)
        self.b_rec.setChecked(True)
        self.b_rec.setText(tr("Stop Recording"))
        self.b_rec.blockSignals(False)
        if not self.b_live.isChecked():
            self.b_live.setChecked(True)
        return self._logger

    def stop_recording(self) -> None:
        if self._logger is not None:
            self._logger.close()
            self.log_line(f"# {tr('Recording saved:')} {self._logger.path} ({self._logger.rows} " + tr("samples") + ")")
            self.live_info.setText(tr("Saved:") + f" {Path(self._logger.path).name}")
        self._logger = None
        self.b_rec.blockSignals(True)
        self.b_rec.setChecked(False)
        self.b_rec.setText(tr("Record CSV..."))
        self.b_rec.blockSignals(False)

    def play_log(self, path: str | None = None):
        from ..cardiag.obd import logger as L
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, tr("Play Live Data Log"), str(Path.home()), "CSV (*.csv);;All files (*)")
            if not path:
                return None
        try:
            rec = L.load(path)
        except Exception as e:  # noqa: BLE001
            self._msg("warning", "Play Log", tr("Cannot read the log:") + f" {e}")
            return None
        self.b_live.setChecked(False)
        self.stop_recording()
        self._playback = rec
        self._play_i = 0
        self._play_t = rec.times[0] if rec.times else 0.0
        self.plot.clear()
        self._stats = {}
        self._set_live_keys(rec.keys())
        self.play_pos.setRange(0, max(0, len(rec) - 1))
        self.play_bar.show()
        self.b_pause.setChecked(False)
        self.play_timer.start()
        self.live_info.setText(tr("Playing:") + f" {Path(path).name}")
        self.tabs.setCurrentIndex(1)
        return rec

    def _play_step(self) -> None:
        rec = self._playback
        if rec is None or not len(rec):
            return
        if self.b_pause.isChecked():
            return
        self._play_t += 0.1 * (self.play_speed.currentData() or 1.0)
        while self._play_i < len(rec) - 1 and rec.times[self._play_i + 1] <= self._play_t:
            self._play_i += 1
            self._show_values({k: v for k, v in rec.sample(self._play_i).items() if v is not None},
                              rec.times[self._play_i] - rec.times[0])
        if self._play_i == 0 and not self._stats:
            self._show_values({k: v for k, v in rec.sample(0).items() if v is not None}, 0.0)
        self.play_pos.blockSignals(True)
        self.play_pos.setValue(self._play_i)
        self.play_pos.blockSignals(False)
        self.play_lab.setText(f"{rec.times[self._play_i] - rec.times[0]:.1f} / {rec.duration:.1f} s")
        if self._play_i >= len(rec) - 1:
            self.b_pause.setChecked(True)

    def _seek(self, i: int) -> None:
        rec = self._playback
        if rec is None:
            return
        self._play_i = max(0, min(i, len(rec) - 1))
        self._play_t = rec.times[self._play_i]
        self.plot.clear()
        lo = max(0, self._play_i - 600)
        for j in range(lo, self._play_i + 1):
            self._show_values({k: v for k, v in rec.sample(j).items() if v is not None}, rec.times[j] - rec.times[0])

    def stop_playback(self) -> None:
        if self._playback is None:
            return
        self.play_timer.stop()
        self._playback = None
        self.play_bar.hide()
        self.live_info.setText("")
        keys = [x.data(0, ROLE) for x in self._pid_items() if x.checkState(0) == Qt.CheckState.Checked]
        self._set_live_keys(keys)

    # ================================================================== freeze frame
    def read_freeze(self) -> None:
        if self.client is None:
            return
        c = self.client

        def done(r, e):
            if e is not None:
                return
            self.freeze = r or {}
            self.ff_ecu.blockSignals(True)
            self.ff_ecu.clear()
            for ecu, ff in sorted(self.freeze.items()):
                self.ff_ecu.addItem(f"{self._ecu(ecu)} - {ff.dtc or tr('no DTC')}", ecu)
            self.ff_ecu.blockSignals(False)
            self._show_freeze()
            self._show_dtc()
        self.run(lambda: c.freeze_frames(0), done, "Reading freeze frames...")

    def _show_freeze(self) -> None:
        from ..cardiag.obd.widgets import fmt
        ecu = self.ff_ecu.currentData()
        ff = self.freeze.get(ecu) if ecu else None
        self.ff_table.setRowCount(0)
        if ff is None:
            if self.client is not None and not self.freeze and self.ff_ecu.count() == 0:
                self.ff_head.setText(tr("No freeze frame stored (freeze frames are erased when codes are cleared)."))
            return
        info = kb_info(ff.dtc) if ff.dtc else {"title": "", "group": ""}
        self.ff_head.setText(tr("Stored when this fault was set:") + f" {ff.dtc}  {info['title'] or info['group']}  "
                             f"({self._ecu(ecu)})")
        for r in ff.readings():
            vals = r.values
            p = self.P.get(r.pid)
            row = self.ff_table.rowCount()
            self.ff_table.insertRow(row)
            text = "; ".join((fmt(v.value) if isinstance(v.value, (int, float)) else tr(str(v.value)))
                             + (f" {v.unit}" if j and v.unit else "") for j, v in enumerate(vals))
            for c, t in enumerate((f"{r.pid:02X}", tr(p.name), text, vals[0].unit if vals else "")):
                self.ff_table.setItem(row, c, _item(t))
        self.ff_table.resizeColumnsToContents()
        self.ff_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

    def _goto_freeze(self, ecu=None) -> None:
        self.tabs.setCurrentWidget(self.tabs.findChild(QWidget, "CarDiagTab_Freeze"))
        if ecu is None or isinstance(ecu, bool):
            it = self.dtc_tree.currentItem()
            ecu = it.data(0, ROLE)[0] if it is not None else None
        if not self.freeze:
            self.read_freeze()
        i = self.ff_ecu.findData(ecu)
        if i >= 0:
            self.ff_ecu.setCurrentIndex(i)

    def _goto_fault(self) -> None:
        ecu = self.ff_ecu.currentData()
        ff = self.freeze.get(ecu) if ecu else None
        self.tabs.setCurrentIndex(0)
        if ff is None:
            return
        for i in range(self.dtc_tree.topLevelItemCount()):
            it = self.dtc_tree.topLevelItem(i)
            if it.data(0, ROLE) == (ecu, ff.dtc):
                self.dtc_tree.setCurrentItem(it)
                return

    # ================================================================== readiness
    def read_readiness(self) -> None:
        if self.client is None:
            return
        c = self.client
        cycle = self.r_cycle.isChecked()

        def done(r, e):
            if e is not None:
                return
            self.ready = r or {}
            self._show_readiness(cycle)
        self.run(lambda: c.readiness(cycle), done, "Reading readiness monitors...")

    def _show_readiness(self, cycle: bool) -> None:
        self.ready_table.setRowCount(0)
        rows = []
        for ecu, st in sorted(getattr(self, "ready", {}).items()):
            for m in st.monitors:
                if m.supported:
                    rows.append((ecu, st, m))
        for ecu, st, m in rows:
            r = self.ready_table.rowCount()
            self.ready_table.insertRow(r)
            status = tr("Complete") if m.complete else tr("Incomplete")
            kind = tr("Continuous") if m.continuous else tr("Non-continuous")
            self.ready_table.setItem(r, 0, _item(tr(m.name), (ecu, m.key)))
            it = _item(status)
            it.setForeground(QColor("#29a35a") if m.complete else QColor("#d68400"))
            f = it.font()
            f.setBold(True)
            it.setFont(f)
            self.ready_table.setItem(r, 1, it)
            self.ready_table.setItem(r, 2, _item(kind))
            self.ready_table.setItem(r, 3, _item(self._ecu(ecu)))
        self.ready_table.resizeColumnsToContents()
        self.ready_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        ready = getattr(self, "ready", {})
        if not ready:
            self.ready_summary.setText(tr("No readiness data."))
            return
        inc = [m for st in ready.values() for m in st.incomplete()]
        mil = any(st.mil for st in ready.values())
        n = sum(st.dtc_count for st in ready.values())
        parts = [tr("MIL: ON") if mil else tr("MIL: OFF"), tr("Confirmed codes:") + f" {n}"]
        if cycle:
            parts.append(tr("This drive cycle:") + " " + (tr("all monitors complete") if not inc else
                                                          tr(f"{len(inc)} monitor(s) not yet run")))
        elif not inc and mil:
            parts.append(tr("All monitors complete, but the MIL is on: the car fails an inspection until the fault is repaired."))
        elif not inc:
            parts.append(tr("All monitors complete - ready for an emissions inspection."))
        else:
            names = ", ".join(tr(m.name) for m in inc)
            parts.append(tr("Not ready:") + f" {names}")
        self.ready_summary.setText("   |   ".join(parts))
        if rows:
            self.ready_table.setCurrentCell(0, 0)
        self._show_monitor()

    def _show_monitor(self) -> None:
        from ..cardiag.obd import readiness as R
        ar = _ar()
        it = self.ready_table.item(self.ready_table.currentRow(), 0) if self.ready_table.rowCount() else None
        h = []
        if it is not None:
            ecu, key = it.data(ROLE)
            h.append(f"<h3>{_esc(it.text())}</h3><p>{_esc(R.explain(key, ar))}</p>")
        h.append(f"<h4>{_esc(tr('How to complete the monitors'))}</h4><p>{_esc(R.DRIVE_CYCLE[1 if ar else 0])}</p>")
        h.append(f"<h4>{_esc(tr('Inspection'))}</h4><p>{_esc(R.INSPECTION[1 if ar else 0])}</p>")
        self.ready_view.setHtml("".join(h))

    # ================================================================== mode 06
    def read_tests(self) -> None:
        if self.client is None:
            return
        c = self.client

        def done(r, e):
            if e is not None:
                return
            self.tests = r or {}
            self._show_tests()
        self.run(c.mode06, done, "Reading test results...")

    def _show_tests(self) -> None:
        from ..cardiag.obd.widgets import fmt
        self.tests_tree.clear()
        only_failed = self.tests_failed.isChecked()
        n = failed = notrun = 0
        for ecu, results in sorted(self.tests.items()):
            groups: dict[int, QTreeWidgetItem] = {}
            for t in results:
                not_run = t.value == 0 and t.minimum == 0 and t.maximum == 0
                n += 1
                failed += (not t.passed) and not not_run
                notrun += not_run
                if only_failed and (t.passed or not_run):
                    continue
                g = groups.get(t.mid)
                if g is None:
                    g = QTreeWidgetItem([f"{t.mid:02X}  {tr(t.mid_name)}", "", "", "", "", "", self._ecu(ecu)])
                    f = g.font(0)
                    f.setBold(True)
                    g.setFont(0, f)
                    groups[t.mid] = g
                    self.tests_tree.addTopLevelItem(g)
                res = tr("Not run") if not_run else (tr("Pass") if t.passed else tr("FAIL"))
                c = QTreeWidgetItem([f"{t.tid:02X}  {tr(t.tid_name)}", fmt(t.value), fmt(t.minimum), fmt(t.maximum),
                                     t.unit, res, ""])
                c.setForeground(5, QColor("#808080") if not_run else QColor("#29a35a") if t.passed else QColor("#d64545"))
                if not t.passed and not not_run:
                    g.setForeground(0, QColor("#d64545"))
                g.addChild(c)
        self.tests_tree.expandAll()
        for i in range(1, 7):
            self.tests_tree.resizeColumnToContents(i)
        self.tests_summary.setText(tr("Tests:") + f" {n}   " + tr("Failed:") + f" {failed}   " + tr("Not run:")
                                   + f" {notrun}")

    # ================================================================== mode 09
    def read_info(self) -> None:
        if self.client is None:
            return
        c = self.client

        def work():
            vi = c.vehicle_info()
            extra = {r.pid: r for r in c.read_pids([0x1C, 0x51])}
            return vi, extra

        def done(r, e):
            if e is not None or not r:
                return
            self.vinfo, self._info_extra = r
            self.ecu_names.update({k: v for k, v in self.vinfo.names.items() if v})
            self.h_vin.setText(f"VIN: {self.vinfo.vin or '-'}")
            self._show_info()
        self.run(work, done, "Reading vehicle information...")

    def _show_info(self) -> None:
        from ..cardiag.obd import mode09 as M9
        vi = self.vinfo
        if vi is None:
            return
        h = [f"<h3>{_esc(tr('Vehicle'))}</h3><table cellspacing=4>"]

        def row(k, v):
            h.append(f"<tr><td><b>{_esc(tr(k))}</b></td><td>{v}</td></tr>")
        row("VIN", f"<code>{_esc(vi.vin or '-')}</code>")
        if vi.vin:
            years = M9.vin_model_year(vi.vin)
            row("Region (WMI)", _esc(tr(M9.vin_region(vi.vin)) or "-"))
            row("Model year (VIN position 10)", " / ".join(str(y) for y in years) or "-")
            ok = M9.vin_check_digit_ok(vi.vin)
            row("Check digit (position 9)", _esc(tr("valid") if ok else tr("not valid (normal outside North America)")))
        for pid in (0x1C, 0x51):
            r = getattr(self, "_info_extra", {}).get(pid)
            if r is not None:
                row(self.P.get(pid).name, _esc(tr(str(r.values[0].value))))
        h.append("</table>")
        for ecu in sorted(set(vi.supported) | set(vi.calids) | set(vi.names)):
            h.append(f"<h3>{_esc(self._ecu(ecu))}</h3><table cellspacing=4>")
            if vi.names.get(ecu):
                row("ECU name", _esc(vi.names[ecu]))
            if vi.calids.get(ecu):
                row("Calibration IDs (CALID)", "<br>".join(f"<code>{_esc(c)}</code>" for c in vi.calids[ecu]))
            if vi.cvns.get(ecu):
                row("Calibration verification numbers (CVN)", "<br>".join(f"<code>{c}</code>" for c in vi.cvns[ecu]))
            h.append("</table>")
            if vi.ipt.get(ecu):
                h.append(f"<h4>{_esc(tr('In-use performance tracking'))}</h4><table border=1 cellspacing=0 cellpadding=3>"
                         f"<tr><th>{_esc(tr('Monitor'))}</th><th>{_esc(tr('Completions'))}</th>"
                         f"<th>{_esc(tr('Conditions'))}</th><th>{_esc(tr('Ratio'))}</th></tr>")
                cnt = vi.ipt[ecu]
                for name, val in cnt[:2]:
                    h.append(f"<tr><td colspan=3>{_esc(tr(name))}</td><td align=right>{val}</td></tr>")
                for name, comp, cond, ratio in M9.ipt_ratios(cnt):
                    if cond:
                        h.append(f"<tr><td>{_esc(tr(name))}</td><td align=right>{comp}</td><td align=right>{cond}</td>"
                                 f"<td align=right>{ratio:.3f}</td></tr>")
                h.append("</table>")
        h.append(f"<p style='color:gray'>{_esc(tr('The calibration ID names the software version in the control unit and the CVN is its checksum; a workshop compares them with the latest software released for the car. To study an ECU firmware file use Tools > Firmware & ECU.'))}</p>")
        self.info_view.setHtml("".join(h))

    def _open_firmware(self) -> None:
        fw = getattr(self.win, "firmware_ide", None) if self.win is not None else None
        if fw is not None and hasattr(fw, "getting_started"):
            fw.getting_started()
        else:
            self._msg("information", "Car Diagnostics", tr("The Firmware & ECU workbench is under Tools > Firmware & ECU."))

    # ================================================================== log
    def _traffic(self, direction, ecu, data) -> None:
        if getattr(self.client, "listeners_paused", False):
            return
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        if direction == "tx":
            line = f"{ts}  >  {data.hex(' ').upper()}"
        elif direction == "rx":
            line = f"{ts}  <  {ecu}: {data.hex(' ').upper()}"
        else:
            line = f"{ts}  !  {data.decode('utf-8', 'replace')}"
        if threading.current_thread() is threading.main_thread():
            self.log_line(line)
        else:
            self.bridge.line.emit(line)

    def log_line(self, text: str) -> None:
        self.log_view.appendPlainText(text)
        self._log_lines += 1

    def save_log(self, path: str | None = None):
        if not path:
            start = str(Path.home() / f"obd-session-{datetime.now():%Y%m%d-%H%M%S}.txt")
            path, _ = QFileDialog.getSaveFileName(self, tr("Save Log"), start, "Text (*.txt);;All files (*)")
            if not path:
                return None
        Path(path).write_text(self.log_view.toPlainText(), encoding="utf-8")
        return path

    def _msg(self, kind: str, title: str, text: str) -> None:
        from PyQt6.QtWidgets import QMessageBox
        getattr(QMessageBox, kind)(self, tr(title), text)

    def closeEvent(self, e):  # noqa: N802 - Qt API
        self.shutdown()
        super().closeEvent(e)

    def shutdown(self) -> None:
        self.live_timer.stop()
        self.play_timer.stop()
        self.stop_recording()
        if self.client is not None:
            self.disconnect()


def _err_text(err) -> str:
    if err is None:
        return ""
    t = getattr(err, "text", None)
    if callable(t):
        try:
            return t(_lang())
        except Exception:  # noqa: BLE001
            pass
    return str(err)


def _open_link(kind: str, port: str, protocol: str):
    """Open a link-slice connection (radide/cardiag/link) for this adapter kind."""
    from ..cardiag import link as L
    if kind == "demo_elm":
        return L.demo_link()
    for name in ("open_link", "connect", "create_link", "make_link"):
        fn = getattr(L, name, None)
        if callable(fn):
            return fn(kind=kind, port=port, protocol=protocol)
    raise RuntimeError(tr("The adapter layer (radide/cardiag/link) has no connect function."))


# ============================================================================================= IDE glue
class CarDiagScan:
    def __init__(self, win):
        self.win = win
        self.wb: CarDiagWorkbench | None = None
        win.cardiag_scan = self
        QTimer.singleShot(0, self._menus)

    @staticmethod
    def plain(text: str) -> str:
        return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")

    def _menu(self, title: str):
        return next((a.menu() for a in self.win.menuBar().actions()
                     if a.menu() is not None and self.plain(a.text()) == title), None)

    def _menus(self) -> None:
        tools = self._menu("Tools")
        if tools is None:
            return
        if any(a.objectName() == "CarDiagScanAction" for a in tools.actions()):
            return
        a = QAction("Car &Diagnostics...", tools)
        a.setObjectName("CarDiagScanAction")
        a.setToolTip("OBD-II scan tool: fault codes, live data, readiness, freeze frame")
        a.triggered.connect(lambda: self.open())
        tools.addAction(a)
        self.action = a

    def open(self, demo: bool = False) -> CarDiagWorkbench:
        try:
            alive = self.wb is not None and self.wb.parent() is not None or (self.wb is not None and self.wb.isVisible())
        except RuntimeError:
            alive = False
        if self.wb is None or not alive:
            self.wb = CarDiagWorkbench(self.win)
        show = getattr(self.win, "_show_tab", None)
        if callable(show):
            show(self.wb, tr("Car Diagnostics"))
        else:
            self.wb.show()
        if demo and self.wb.client is None:
            self.wb.connect_demo()
        return self.wb


def install(win) -> None:
    CarDiagScan(win)
