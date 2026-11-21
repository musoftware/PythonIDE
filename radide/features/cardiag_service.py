"""Car service functions in the IDE (radide/cardiag/service, docs/CARDIAG.md "Service functions").

Tools > Car Service Functions... opens a "Service Functions" tab; the Car Diagnostics workbench
(features/cardiag_scan.py) also gets a "Service" tab through its TAB_HOOKS.

* Connection: the built-in **Demo car** simulator, or the connection of the Car Diagnostics workbench (any
  adapter of radide/cardiag/link).
* Definition pack: the Demo car pack (simulator only) or the user's imported packs (JSON / CSV / ODX / PDX).
* Functions: routines (with a precondition checklist, progress, Stop), actuator tests (control is always
  returned to the ECU), service resets / adaptations / feature coding, and "Clear a specific fault"
  (explanation and safety warnings first, repair confirmation, single DTC or clear-all fallback).
* Vehicle profile by VIN with history; every request / answer and every confirmation goes to the audit log.
* Security access only with a seed/key plug-in the user selects (no algorithms included).
"""
from __future__ import annotations

import threading
import time

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
                             QProgressBar, QPushButton, QSpinBox, QSplitter, QTabWidget, QTextBrowser, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

ROLE = Qt.ItemDataRole.UserRole
SETTING_PLUGIN = "cardiag/service/seedkeyPlugin"


def tr(text: str) -> str:
    try:
        from ..i18n import tr as _t
        return _t(text)
    except Exception:  # noqa: BLE001
        return text


def _lang() -> str:
    try:
        from ..i18n import language
        return language() or "en"
    except Exception:  # noqa: BLE001
        return "en"


def _settings():
    from PyQt6.QtCore import QCoreApplication, QSettings
    org = QCoreApplication.organizationName() or "RADIDE"
    return QSettings(org, QCoreApplication.applicationName() or org)


class _Bridge(QObject):
    event = pyqtSignal(object)
    done = pyqtSignal(object, object)          # (result, error text)


# ============================================================================================= panel
class ServicePanel(QWidget):
    """The whole service-functions UI (used as an IDE tab and as a tab of the Car Diagnostics workbench)."""

    def __init__(self, win, workbench=None, parent=None):
        super().__init__(parent)
        self.win = win
        self.wb = workbench
        self.setObjectName("CarServicePanel")
        self.bridge = _Bridge()
        self.bridge.event.connect(self._on_event)
        self.bridge.done.connect(self._on_done)
        self.car = None
        self.client = None
        self.pack = None
        self.profile = None
        self.plugin = None
        self.worker = None
        self.job = None
        self.current = None            # (kind, entry)
        self._packs: list = []
        self._plan = None
        self._last = ("service", "")
        self.inputs: list = []
        self._link = None              # the workbench's DiagLink when "Car Diagnostics connection" is chosen
        self._build()
        self._load_plugin_setting()
        self.connect_demo()

    # ------------------------------------------------------------------ layout
    def _build(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        bar = QHBoxLayout()
        bar.addWidget(QLabel(tr("Connection:")))
        self.conn = QComboBox()
        self.conn.setObjectName("svcConnection")
        self.conn.addItem(tr("Demo car (simulator)"), "demo")
        self.conn.addItem(tr("Car Diagnostics connection"), "link")
        self.conn.currentIndexChanged.connect(self._conn_changed)
        bar.addWidget(self.conn)
        bar.addWidget(QLabel(tr("Definitions:")))
        self.pack_box = QComboBox()
        self.pack_box.setObjectName("svcPack")
        self.pack_box.setMinimumWidth(220)
        self.pack_box.currentIndexChanged.connect(self._pack_changed)
        bar.addWidget(self.pack_box)
        b = QPushButton(tr("Import Pack..."))
        b.setObjectName("svcImport")
        b.clicked.connect(lambda: self.import_pack())
        bar.addWidget(b)
        b = QPushButton(tr("Template..."))
        b.clicked.connect(self.save_template)
        bar.addWidget(b)
        self.b_plugin = QPushButton(tr("Security Plug-in..."))
        self.b_plugin.setObjectName("svcPlugin")
        self.b_plugin.clicked.connect(lambda: self.choose_plugin())
        bar.addWidget(self.b_plugin)
        bar.addStretch(1)
        v.addLayout(bar)

        vbar = QHBoxLayout()
        vbar.addWidget(QLabel(tr("Vehicle (VIN):")))
        self.vin = QLineEdit()
        self.vin.setObjectName("svcVin")
        self.vin.setMaxLength(17)
        self.vin.setPlaceholderText(tr("17 characters"))
        self.vin.editingFinished.connect(lambda: self.set_vehicle(self.vin.text()))
        vbar.addWidget(self.vin)
        b = QPushButton(tr("Read VIN"))
        b.clicked.connect(self.read_vin)
        vbar.addWidget(b)
        self.veh_label = QLabel("")
        self.veh_label.setProperty("i18n_skip", True)
        vbar.addWidget(self.veh_label, 1)
        v.addLayout(vbar)

        # Demo car conditions
        self.demo_box = QGroupBox(tr("Demo car conditions"))
        self.demo_box.setObjectName("svcDemoBox")
        dl = QHBoxLayout(self.demo_box)
        self.d_ign = QCheckBox(tr("Ignition on"))
        self.d_eng = QCheckBox(tr("Engine running"))
        self.d_cool = QSpinBox()
        self.d_cool.setRange(-30, 130)
        self.d_cool.setSuffix(" °C")
        self.d_speed = QSpinBox()
        self.d_speed.setRange(0, 200)
        self.d_speed.setSuffix(" km/h")
        self.d_batt = QDoubleSpinBox()
        self.d_batt.setRange(9.0, 15.5)
        self.d_batt.setSingleStep(0.1)
        self.d_batt.setSuffix(" V")
        dl.addWidget(self.d_ign)
        dl.addWidget(self.d_eng)
        dl.addWidget(QLabel(tr("Coolant:")))
        dl.addWidget(self.d_cool)
        dl.addWidget(QLabel(tr("Speed:")))
        dl.addWidget(self.d_speed)
        dl.addWidget(QLabel(tr("Battery:")))
        dl.addWidget(self.d_batt)
        dl.addStretch(1)
        for w in (self.d_ign, self.d_eng):
            w.toggled.connect(self._demo_changed)
        for w in (self.d_cool, self.d_speed, self.d_batt):
            w.valueChanged.connect(self._demo_changed)
        v.addWidget(self.demo_box)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setObjectName("svcFunctions")
        self.tree.setHeaderLabels([tr("Service function")])
        self.tree.setProperty("i18n_skip_items", True)
        self.tree.currentItemChanged.connect(lambda cur, _old: self._select(cur))
        split.addWidget(self.tree)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(4, 0, 0, 0)
        self.title = QLabel("")
        f = QFont()
        f.setPointSize(f.pointSize() + 3)
        f.setBold(True)
        self.title.setFont(f)
        self.title.setWordWrap(True)
        rv.addWidget(self.title)
        self.desc = QLabel("")
        self.desc.setWordWrap(True)
        rv.addWidget(self.desc)
        self.safety = QLabel("")
        self.safety.setWordWrap(True)
        self.safety.setObjectName("svcSafety")
        self.safety.setStyleSheet("QLabel{background:#fff3cd;color:#664d03;border:1px solid #e0c060;padding:6px;}")
        self.safety.setVisible(False)
        rv.addWidget(self.safety)
        self.pre_label = QLabel(tr("Preconditions (tick each one when it is true):"))
        rv.addWidget(self.pre_label)
        self.pre = QListWidget()
        self.pre.setObjectName("svcPreconditions")
        self.pre.setProperty("i18n_skip_items", True)
        self.pre.setMaximumHeight(150)
        rv.addWidget(self.pre)
        self.b_check = QPushButton(tr("Check Conditions"))
        self.b_check.setObjectName("svcCheck")
        self.b_check.clicked.connect(self.check_conditions)
        rv.addWidget(self.b_check, 0, Qt.AlignmentFlag.AlignLeft)

        self.params = QGroupBox(tr("Values"))
        self.params_form = QFormLayout(self.params)
        rv.addWidget(self.params)

        # fault page
        self.fault_box = QWidget()
        fl = QVBoxLayout(self.fault_box)
        fl.setContentsMargins(0, 0, 0, 0)
        fr = QHBoxLayout()
        fr.addWidget(QLabel(tr("Control unit:")))
        self.f_ecu = QComboBox()
        self.f_ecu.setObjectName("svcFaultEcu")
        fr.addWidget(self.f_ecu, 1)
        b = QPushButton(tr("Read Faults"))
        b.setObjectName("svcReadFaults")
        b.clicked.connect(self.read_faults)
        fr.addWidget(b)
        fl.addLayout(fr)
        fr2 = QHBoxLayout()
        self.f_list = QListWidget()
        self.f_list.setObjectName("svcFaultList")
        self.f_list.setProperty("i18n_skip_items", True)
        self.f_list.currentItemChanged.connect(lambda cur, _o: self._fault_selected(cur))
        fr2.addWidget(self.f_list, 1)
        self.f_code = QLineEdit()
        self.f_code.setPlaceholderText(tr("or type a code, e.g. P0128"))
        self.f_code.editingFinished.connect(self._fault_typed)
        fl.addLayout(fr2)
        fl.addWidget(self.f_code)
        self.f_text = QTextBrowser()
        self.f_text.setObjectName("svcFaultText")
        self.f_text.setProperty("i18n_skip", True)
        fl.addWidget(self.f_text, 1)
        self.f_repaired = QCheckBox(tr("I confirm the cause was repaired"))
        self.f_repaired.setObjectName("svcRepaired")
        fl.addWidget(self.f_repaired)
        self.f_kb = QPushButton(tr("Open in the Fault Guide"))
        self.f_kb.clicked.connect(self._open_kb)
        fl.addWidget(self.f_kb, 0, Qt.AlignmentFlag.AlignLeft)
        rv.addWidget(self.fault_box)

        runbar = QHBoxLayout()
        self.b_run = QPushButton(tr("Run"))
        self.b_run.setObjectName("svcRun")
        self.b_run.clicked.connect(lambda: self.run_current())
        self.b_stop = QPushButton(tr("Stop"))
        self.b_stop.setObjectName("svcStop")
        self.b_stop.clicked.connect(self.stop)
        self.b_stop.setEnabled(False)
        runbar.addWidget(self.b_run)
        runbar.addWidget(self.b_stop)
        self.progress = QProgressBar()
        self.progress.setObjectName("svcProgress")
        self.progress.setRange(0, 100)
        runbar.addWidget(self.progress, 1)
        rv.addLayout(runbar)
        self.status = QLabel("")
        self.status.setObjectName("svcStatus")
        self.status.setWordWrap(True)
        self.status.setProperty("i18n_skip", True)
        rv.addWidget(self.status)
        rv.addStretch(1)
        split.addWidget(right)
        split.setSizes([300, 700])

        bottom = QTabWidget()
        bottom.setObjectName("svcBottom")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("svcLog")
        self.log.setProperty("i18n_skip", True)
        bottom.addTab(self.log, tr("Log"))
        aw = QWidget()
        al = QVBoxLayout(aw)
        al.setContentsMargins(0, 0, 0, 0)
        self.audit = QPlainTextEdit()
        self.audit.setReadOnly(True)
        self.audit.setObjectName("svcAudit")
        self.audit.setProperty("i18n_skip", True)
        al.addWidget(self.audit)
        ab = QHBoxLayout()
        b = QPushButton(tr("Refresh"))
        b.clicked.connect(self.refresh_audit)
        ab.addWidget(b)
        b = QPushButton(tr("Export CSV..."))
        b.clicked.connect(self.export_audit)
        ab.addWidget(b)
        ab.addStretch(1)
        al.addLayout(ab)
        bottom.addTab(aw, tr("Audit Log"))
        hw = QWidget()
        hl = QVBoxLayout(hw)
        hl.setContentsMargins(0, 0, 0, 0)
        self.history = QListWidget()
        self.history.setObjectName("svcHistory")
        self.history.setProperty("i18n_skip_items", True)
        hl.addWidget(self.history)
        hb = QHBoxLayout()
        self.h_note = QLineEdit()
        self.h_note.setPlaceholderText(tr("Repair note (what was replaced / fixed)"))
        hb.addWidget(self.h_note, 1)
        b = QPushButton(tr("Add Repair"))
        b.clicked.connect(self.add_repair)
        hb.addWidget(b)
        hl.addLayout(hb)
        bottom.addTab(hw, tr("Vehicle History"))

        vs = QSplitter(Qt.Orientation.Vertical)
        vs.addWidget(split)
        vs.addWidget(bottom)
        vs.setSizes([560, 220])
        v.addWidget(vs, 1)
        self._show_page(None)

    def changeEvent(self, ev) -> None:
        super().changeEvent(ev)
        if ev.type() == QEvent.Type.LanguageChange:
            QTimer.singleShot(0, self._retranslate)

    def _retranslate(self) -> None:
        """Texts made from the user's data / definitions follow the UI language (combo items, tree, page)."""
        try:
            self.conn.setItemText(0, tr("Demo car (simulator)"))
            self.conn.setItemText(1, tr("Car Diagnostics connection"))
            cur = self.tree.currentItem()
            data = cur.data(0, ROLE) if cur is not None else None
            if self.worker is None or not self.worker.is_alive():
                self.reload_packs(select_path=(self.pack or {}).get("_path", ""))
                if data:
                    self.select(*data)
        except RuntimeError:
            pass

    # ------------------------------------------------------------------ connection / packs / vehicle
    def _audit(self, entry: dict) -> None:
        if self.profile is not None:
            self.profile.audit(entry)

    def connect_demo(self) -> None:
        from ..cardiag.service.demo_ecu import DemoCar, DemoTransport
        from ..cardiag.service.transport import ServiceClient
        self.car = DemoCar(bleed_seconds=20.0)
        self.client = ServiceClient(DemoTransport(self.car), audit=self._audit)
        self.conn.blockSignals(True)
        self.conn.setCurrentIndex(0)
        self.conn.blockSignals(False)
        self.demo_box.setVisible(True)
        self._sync_demo_widgets()
        self.reload_packs()
        self.set_vehicle(self._demo_vin())
        self.log_line(tr("Connected to the Demo car (simulator)."))

    def _demo_vin(self) -> str:
        from ..cardiag.service.demo_ecu import VIN
        return VIN

    def connect_link(self) -> bool:
        link = getattr(self.wb, "link", None) if self.wb is not None else None
        if link is None:
            scan = getattr(self.win, "cardiag_scan", None)
            wb = getattr(scan, "wb", None)
            link = getattr(wb, "link", None)
        if link is None or not hasattr(link, "exchange"):
            QMessageBox.information(self, tr("Service Functions"),
                                    tr("Connect an adapter in the Car Diagnostics workbench first (Tools > Car "
                                       "Diagnostics...)."))
            self.connect_demo()
            return False
        from ..cardiag.service.transport import ServiceClient
        self.car = None
        self._link = link
        self.client = ServiceClient(link, audit=self._audit)
        self.demo_box.setVisible(False)
        self.reload_packs()
        if self._link_is_sim():
            try:
                from ..cardiag.sim.car import VIN as SIM_VIN
                self.set_vehicle(SIM_VIN)
            except Exception:  # noqa: BLE001
                pass
        self.log_line(tr("Using the Car Diagnostics connection."))
        return True

    def _link_is_sim(self) -> bool:
        """The service client talks to the workbench's Demo car simulator (not to a real vehicle)."""
        from ..cardiag.service.definitions import is_virtual_car_link
        if self.car is not None or self.client is None:
            return False
        return is_virtual_car_link(getattr(self, "_link", None))

    def _conn_changed(self, _i) -> None:
        if self.conn.currentData() == "demo":
            self.connect_demo()
        else:
            self.connect_link()

    def _sync_demo_widgets(self) -> None:
        c = self.car
        if c is None:
            return
        for w in (self.d_ign, self.d_eng, self.d_cool, self.d_speed, self.d_batt):
            w.blockSignals(True)
        self.d_ign.setChecked(c.ignition)
        self.d_eng.setChecked(c.engine_running)
        self.d_cool.setValue(int(c.coolant_c))
        self.d_speed.setValue(int(c.speed_kmh))
        self.d_batt.setValue(c.battery_v)
        for w in (self.d_ign, self.d_eng, self.d_cool, self.d_speed, self.d_batt):
            w.blockSignals(False)

    def _demo_changed(self, *_a) -> None:
        c = self.car
        if c is None:
            return
        c.ignition = self.d_ign.isChecked()
        c.engine_running = self.d_eng.isChecked()
        c.coolant_c = float(self.d_cool.value())
        c.speed_kmh = float(self.d_speed.value())
        c.battery_v = float(self.d_batt.value())

    def reload_packs(self, select_path: str = "") -> None:
        from ..cardiag.service import definitions as D
        demo = self.car is not None
        self._packs = []
        if demo:
            self._packs.append(D.demo_pack())
        elif self._link_is_sim():
            self._packs.append(D.workbench_pack())
        for pack, path, _probs in D.user_packs():
            if pack is not None:
                self._packs.append(pack)
        self.pack_box.blockSignals(True)
        self.pack_box.clear()
        sel = 0
        for i, p in enumerate(self._packs):
            name = (p.get("name_ar") if _lang() == "ar" else p.get("name")) or p.get("name") or "?"
            self.pack_box.addItem(name, i)
            if select_path and p.get("_path") == select_path:
                sel = i
        self.pack_box.blockSignals(False)
        if self._packs:
            self.pack_box.setCurrentIndex(sel)
        self._pack_changed(self.pack_box.currentIndex())

    def _pack_changed(self, i) -> None:
        self.pack = self._packs[i] if 0 <= i < len(self._packs) else None
        self.fill_tree()

    def set_vehicle(self, vin: str) -> None:
        from ..cardiag.service import profiles as P
        vin = P.clean_vin(vin)
        if self.profile is not None and self.profile.vin == vin:
            return
        info = {}
        if self.car is not None and vin == self._demo_vin():
            info = {"make": "RAD IDE", "model": "Demo car", "year": "2026"}
        self.profile = P.get_or_create(vin, **info)
        self.vin.setText("" if vin == P.UNKNOWN_VIN else vin)
        warn = "" if P.vin_valid(vin) else "  " + tr("(not a valid 17-character VIN)")
        self.veh_label.setText(self.profile.title + warn)
        self.refresh_history()
        self.refresh_audit()

    def read_vin(self) -> None:
        if self.pack is None:
            return
        from ..cardiag.service import definitions as D
        from ..cardiag.service.runner import ServiceBase
        base = ServiceBase(self.client, self.pack)
        for key in (self.pack.get("ecus") or {}):
            try:
                raw, _v, _i = base.read_did(D.ecu_of(self.pack, key), 0xF190)
                vin = raw.decode("ascii", "replace").strip("\x00 ")
                if vin:
                    self.set_vehicle(vin)
                    self.log_line(f"VIN: {vin}")
                    return
            except Exception:  # noqa: BLE001 - try the next control unit
                continue
        QMessageBox.information(self, tr("Service Functions"), tr("The VIN could not be read."))

    # ------------------------------------------------------------------ tree / pages
    def fill_tree(self) -> None:
        from ..cardiag.service import definitions as D
        self.tree.clear()
        p = self.pack
        if p is None:
            return
        ar = _lang() == "ar"
        groups = [("routines", tr("Routines")), ("io_controls", tr("Actuator tests")),
                  ("adaptations", tr("Resets, adaptations and coding"))]
        for kind, title in groups:
            entries = p.get(kind) or []
            if not entries:
                continue
            top = QTreeWidgetItem([title])
            top.setFlags(top.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.tree.addTopLevelItem(top)
            for e in entries:
                name = (e.get("name_ar") if ar else e.get("name")) or e.get("name") or e["id"]
                it = QTreeWidgetItem([name])
                it.setToolTip(0, f"{D.category_label(e.get('category', 'other'))} - {e['id']}")
                it.setData(0, ROLE, (kind, e["id"]))
                top.addChild(it)
            top.setExpanded(True)
        it = QTreeWidgetItem([tr("Clear a specific fault")])
        it.setData(0, ROLE, ("fault", ""))
        self.tree.addTopLevelItem(it)
        self.f_ecu.clear()
        for key, e in (p.get("ecus") or {}).items():
            self.f_ecu.addItem(((e.get("name_ar") if ar else e.get("name")) or key) + f"  ({e['tx']})", key)

    def select(self, kind: str, ident: str = "") -> bool:
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for it in [top] + [top.child(j) for j in range(top.childCount())]:
                if it.data(0, ROLE) == (kind, ident):
                    self.tree.setCurrentItem(it)
                    return True
        return False

    def _select(self, item) -> None:
        data = item.data(0, ROLE) if item is not None else None
        if not data:
            self._show_page(None)
            return
        kind, ident = data
        if kind == "fault":
            self.current = ("fault", None)
            self._show_page("fault")
            return
        from ..cardiag.service import definitions as D
        e = D.find(self.pack, kind, ident)
        self.current = (kind, e)
        self._show_page(kind, e)

    def _show_page(self, kind, e=None) -> None:
        from ..cardiag.service import definitions as D
        from ..cardiag.service.text import pick
        is_fault = kind == "fault"
        self.fault_box.setVisible(is_fault)
        for w in (self.pre_label, self.pre, self.b_check):
            w.setVisible(e is not None)
        self.params.setVisible(kind in ("io_controls", "adaptations"))
        self.b_run.setEnabled(kind is not None)
        self.b_run.setText(tr("Clear Fault") if is_fault else (tr("Start Test") if kind == "io_controls" else tr("Run")))
        self.progress.setValue(0)
        self.status.setText("")
        self.safety.setVisible(False)
        if kind is None:
            self.title.setText(tr("Choose a service function"))
            self.desc.setText(tr("Routines, actuator tests and resets come from the selected definition pack. "
                                 "Real vehicles need a pack you import (Template... shows the format)."))
            return
        if is_fault:
            self.title.setText(tr("Clear a specific fault"))
            self.desc.setText(tr("Read the faults, select one and read its explanation. Clear it only after the "
                                 "repair: if the cause is still there, the fault comes back."))
            self.f_text.clear()
            self.f_repaired.setChecked(False)
            return
        self.title.setText(pick(e, "name"))
        self.desc.setText(pick(e, "description"))
        warn = []
        if e.get("safety") in D.SAFETY:
            en, ar = D.SAFETY[e["safety"]]
            warn.append(ar if _lang() == "ar" else en)
        for w in e.get("warnings") or []:
            warn.append(pick(w, "text") if isinstance(w, dict) else str(w))
        if self.pack.get("imported_from") == "odx":
            warn.append(tr("Imported from ODX: check the identifiers and preconditions before use."))
        if warn:
            self.safety.setText("\n".join("⚠ " + w for w in warn))
            self.safety.setVisible(True)
        self.pre.clear()
        for i, pc in enumerate(e.get("preconditions") or []):
            pc = {"text": pc} if isinstance(pc, str) else pc
            it = QListWidgetItem(pick(pc, "text"))
            it.setData(ROLE, i)
            if pc.get("check"):
                it.setText(pick(pc, "text") + "   " + tr("(checked automatically)"))
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            else:
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Unchecked)
            self.pre.addItem(it)
        if not (e.get("preconditions") or []):
            self.pre.addItem(QListWidgetItem(tr("(no preconditions)")))
        self._build_params(kind, e)

    def _build_params(self, kind, e) -> None:
        from ..cardiag.service.adaptation import fields_of
        from ..cardiag.service.text import pick
        while self.params_form.rowCount():
            self.params_form.removeRow(0)
        self.inputs = []
        if kind == "io_controls":
            self.io_state = QComboBox()
            self.io_state.setObjectName("svcIoState")
            for st in e.get("states") or []:
                self.io_state.addItem(pick(st, "label"), st.get("value"))
            self.io_state.currentIndexChanged.connect(self._io_state_changed)
            self.params_form.addRow(tr("State:"), self.io_state)
            self.io_time = QSpinBox()
            self.io_time.setRange(1, int(e.get("max_duration_s", 30)))
            self.io_time.setValue(min(10, int(e.get("max_duration_s", 30))))
            self.io_time.setSuffix(" s")
            self.params_form.addRow(tr("Duration:"), self.io_time)
        elif kind in ("adaptations", "routines"):
            flds = fields_of(e)
            if not flds and kind == "adaptations":
                self.params_form.addRow(QLabel(tr("Writes the fixed value {}").replace("{}", str(e.get("value", "")))))
            for f in flds:
                if f.get("type") == "enum":
                    w = QComboBox()
                    for o in f.get("options") or []:
                        w.addItem(pick(o, "label"), o.get("value"))
                    if f.get("default") is not None:
                        i = w.findData(f.get("default"))
                        w.setCurrentIndex(max(0, i))
                else:
                    w = QLineEdit(str(f.get("default", "")))
                label = pick(f, "name") + (f" ({f.get('min')}..{f.get('max')} {f.get('unit', '')})"
                                           if f.get("type", "int") == "int" and f.get("min") is not None else "")
                self.params_form.addRow(label + ":", w)
                self.inputs.append(w)

    def _io_state_changed(self, _i) -> None:
        if self.job is not None and hasattr(self.job, "next_value"):
            from ..cardiag.service.definitions import hexbytes
            self.job.next_value = hexbytes(self.io_state.currentData())

    def _confirmed(self) -> list[int]:
        out = []
        for i in range(self.pre.count()):
            it = self.pre.item(i)
            if it.flags() & Qt.ItemFlag.ItemIsUserCheckable and it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(ROLE))
        return out

    def set_all_confirmed(self) -> None:
        for i in range(self.pre.count()):
            it = self.pre.item(i)
            if it.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                it.setCheckState(Qt.CheckState.Checked)

    # ------------------------------------------------------------------ actions
    def log_line(self, text) -> None:
        self.log.appendPlainText(time.strftime("%H:%M:%S ") + str(text))

    def _busy(self, on: bool) -> None:
        self.b_run.setEnabled(not on)
        self.b_stop.setEnabled(on)
        self.tree.setEnabled(not on)
        self.pack_box.setEnabled(not on)
        self.conn.setEnabled(not on)

    def _start(self, fn, label: str) -> None:
        if self.worker is not None and self.worker.is_alive():
            return
        self.client.cancelled = False
        self._busy(True)
        self.progress.setValue(0)
        self._label = label

        def work():
            res, err = None, None
            try:
                res = fn()
            except Exception as e:  # noqa: BLE001 - shown to the user
                err = str(e)
            self.bridge.done.emit(res, err)
        self.worker = threading.Thread(target=work, daemon=True, name="cardiag-service")
        self.worker.start()

    def _emit(self, ev) -> None:
        self.bridge.event.emit(ev)

    def _on_event(self, ev) -> None:
        text = str(ev.text)
        if ev.progress is not None:
            self.progress.setValue(int(ev.progress))
        if ev.kind in ("status", "progress"):
            self.status.setText(text)
        if ev.kind == "precondition":
            idx = ev.data.get("index")
            for i in range(self.pre.count()):
                it = self.pre.item(i)
                if it.data(ROLE) == idx and not it.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                    ok = ev.data.get("ok")
                    mark = "✔" if ok else ("✘" if ok is False else "?")
                    it.setText(text.split("  [")[0] + f"   {mark} {ev.data.get('value', '')}")
        if ev.kind != "progress":
            prefix = {"warning": "⚠ ", "instruction": "➜ ", "result": "= "}.get(ev.kind, "")
            self.log_line(prefix + text)
        if ev.kind == "instruction":
            self.status.setText("➜ " + text)

    def _on_done(self, res, err) -> None:
        self._busy(False)
        job, self.job = self.job, None
        if err:
            self.status.setText(err)
            self.log_line("✘ " + err)
            return
        if res is None:
            return
        self.status.setText(str(res.status))
        if not self.log.toPlainText().rstrip().endswith(str(res.status)):
            self.log_line(("✔ " if res.ok else "✘ ") + str(res.status))
        if job == "fault" and res.ok:
            QTimer.singleShot(0, self.read_faults)
            wb = self.wb
            if wb is not None and self._link is not None and getattr(wb, "link", None) is self._link:
                # the scan tool shows the same car: refresh its Faults tab too
                QTimer.singleShot(0, wb.scan_all_units if getattr(wb, "unit_entries", None) else wb.read_codes)
        if res.ok and self.profile is not None:
            kind, ident = getattr(self, "_last", ("service", ""))
            self.profile.add_history(kind, f"{ident}: {res.status.en}", f"{ident}: {res.status.get('ar')}",
                                     id=ident, data=res.data)
        if res.data.get("needs_clear_all") and job == "fault":
            self._ask_clear_all()
        self.refresh_audit()
        self.refresh_history()
        if self.car is not None:
            self._sync_demo_widgets()

    def run_current(self) -> None:
        if self.current is None or self.client is None:
            return
        kind, e = self.current
        if kind == "fault":
            self.clear_fault()
            return
        if e is None:
            return
        demo = self.pack.get("demo")
        if (demo == "workbench" and not self._link_is_sim()) or (demo and demo != "workbench" and self.car is None):
            QMessageBox.warning(self, tr("Service Functions"),
                                tr("The Demo car pack only works with the Demo car simulator."))
            return
        params = None
        if kind == "routines" and (e.get("input") or {}).get("fields"):
            from ..cardiag.service.adaptation import encode_input
            from ..cardiag.service.transport import ServiceError
            vals = [w.currentData() if isinstance(w, QComboBox) else w.text() for w in self.inputs]
            try:
                params = encode_input(e, vals)
            except ServiceError as err:
                QMessageBox.warning(self, tr("Service Functions"), err.text.get(_lang()))
                return
        if not self._ensure_notice():
            return
        confirmed = self._confirmed()
        self._audit({"action": "confirmation", "id": e["id"], "confirmation": f"preconditions {confirmed}"})
        self._last = ("service", e["id"])
        if kind == "routines":
            from ..cardiag.service.runner import RoutineRunner
            r = RoutineRunner(self.client, self.pack, plugin=self.plugin, emit=self._emit)
            self.job = r
            self._start(lambda: r.run(e, confirmed, params=params), e["id"])
        elif kind == "io_controls":
            from ..cardiag.service.iocontrol import ActuatorTest
            t = ActuatorTest(self.client, self.pack, plugin=self.plugin, emit=self._emit)
            self.job = t
            value = self.io_state.currentData()
            secs = self.io_time.value()
            self._start(lambda: t.run(e, value, confirmed, duration_s=secs), e["id"])
        elif kind == "adaptations":
            from ..cardiag.service.adaptation import AdaptationWriter
            vals = [w.currentData() if isinstance(w, QComboBox) else w.text() for w in self.inputs]
            if QMessageBox.question(self, tr("Service Functions"),
                                    tr("Write this value to the control unit?")) != QMessageBox.StandardButton.Yes:
                return
            self._audit({"action": "confirmation", "id": e["id"], "confirmation": f"write {vals}"})
            a = AdaptationWriter(self.client, self.pack, plugin=self.plugin, emit=self._emit)
            self.job = a
            self._start(lambda: a.write(e, vals, confirmed), e["id"])

    def stop(self) -> None:
        job = self.job
        if job is not None and hasattr(job, "stop_requested"):
            job.stop_requested = True             # actuator test: end gracefully (control returned)
        elif self.client is not None:
            self.client.cancelled = True
        self.log_line(tr("Stop requested."))

    def check_conditions(self) -> None:
        if not self.current or not self.current[1]:
            return
        from ..cardiag.service.runner import ServiceBase
        base = ServiceBase(self.client, self.pack)
        items = base.preconditions(self.current[1], check=True)
        for it in items:
            if it.automatic:
                from ..cardiag.service.runner import Event
                self._on_event(Event("precondition", it.text, None,
                                     {"index": it.index, "ok": it.ok, "value": it.value or it.error}))

    # ------------------------------------------------------------------ faults
    def _fault_ecu(self):
        from ..cardiag.service import definitions as D
        key = self.f_ecu.currentData()
        return D.ecu_of(self.pack, key) if key else None

    def read_faults(self) -> None:
        from ..cardiag.service.dtc import ClearFaultFlow
        ecu = self._fault_ecu()
        if ecu is None:
            return
        self.f_list.clear()
        try:
            dtcs = ClearFaultFlow(self.client).read(ecu)
        except Exception as e:  # noqa: BLE001
            self.status.setText(str(e))
            return
        from ..cardiag.service.dtc import lookup
        for d in dtcs:
            info = lookup(d.code)
            title = (info.get("title_ar") if _lang() == "ar" else info.get("title")) or info.get("title", "")
            it = QListWidgetItem(f"{d.label}  {title}")
            it.setData(ROLE, d.label)
            self.f_list.addItem(it)
        if not dtcs:
            self.f_list.addItem(QListWidgetItem(tr("No stored faults.")))
        self.log_line(tr("Faults read: {}").replace("{}", str(len(dtcs))))
        if self.profile is not None:
            self.profile.add_history("scan", f"{ecu.key}: {', '.join(d.label for d in dtcs) or 'no faults'}",
                                     f"{ecu.key}: {'، '.join(d.label for d in dtcs) or 'لا أعطال'}",
                                     ecu=ecu.key, dtcs=[d.label for d in dtcs])
            self.refresh_history()

    def _fault_selected(self, item) -> None:
        code = item.data(ROLE) if item is not None else None
        if code:
            self.f_code.setText(code)
            self.show_fault(code)

    def _fault_typed(self) -> None:
        if self.f_code.text().strip():
            self.show_fault(self.f_code.text().strip())

    def show_fault(self, code: str):
        from ..cardiag.service.dtc import ClearFaultFlow
        ecu = self._fault_ecu()
        if ecu is None:
            return None
        try:
            plan = ClearFaultFlow(self.client).plan(ecu, code)
        except ValueError:
            self.f_text.setPlainText(tr("Not a valid fault code (example: P0128 or C0035-1F)."))
            return None
        self._plan = plan
        self.f_text.setPlainText(plan.explanation(_lang()))
        self.f_repaired.setChecked(False)
        return plan

    def _open_kb(self) -> None:
        code = self.f_code.text().strip()
        for name in ("cardiag_kb", "cardiag_faults", "cardiag_guide"):
            feat = getattr(self.win, name, None)
            for meth in ("show_code", "open_code", "explain", "open"):
                fn = getattr(feat, meth, None)
                if callable(fn):
                    try:
                        fn(code) if code else fn()
                        return
                    except TypeError:
                        continue
        QMessageBox.information(self, tr("Service Functions"), tr("The fault guide is not available."))

    def clear_fault(self, allow_clear_all: bool = False) -> None:
        plan = getattr(self, "_plan", None)
        code = self.f_code.text().strip()
        if code and (plan is None or not code.upper().startswith(plan.code)):
            plan = self.show_fault(code)
        if plan is None:
            QMessageBox.information(self, tr("Clear Fault"), tr("Select or type a fault first."))
            return
        if not self.f_repaired.isChecked():
            QMessageBox.information(self, tr("Clear Fault"),
                                    tr("Read the explanation and confirm that the cause was repaired first."))
            return
        if plan.warnings and not allow_clear_all:
            msg = "\n".join("⚠ " + w.get(_lang()) for w in plan.warnings)
            if QMessageBox.question(self, tr("Clear Fault"), msg + "\n\n" + tr("Clear this safety-relevant fault now?")) \
                    != QMessageBox.StandardButton.Yes:
                return
        self._audit({"action": "confirmation", "id": plan.code, "confirmation": "repair done",
                     "repair_confirmed": True, "safety": plan.topics})
        from ..cardiag.service.dtc import ClearFaultFlow
        flow = ClearFaultFlow(self.client, emit=self._emit)
        self.job = "fault"
        self._last = ("clear_dtc", plan.code)
        self._start(lambda: flow.clear(plan, repair_confirmed=True, allow_clear_all=allow_clear_all), plan.code)

    def _ask_clear_all(self) -> None:
        if QMessageBox.question(self, tr("Clear Fault"),
                                tr("This control unit cannot clear a single fault. Clear ALL its faults instead? "
                                   "Every stored fault and its freeze-frame data of this unit will be erased.")) \
                == QMessageBox.StandardButton.Yes:
            self._audit({"action": "confirmation", "id": getattr(self._plan, "code", ""),
                         "confirmation": "clear all faults of the unit (fallback)"})
            QTimer.singleShot(0, lambda: self.clear_fault(allow_clear_all=True))

    # ------------------------------------------------------------------ packs / plug-in / audit
    def import_pack(self, path: str = "") -> bool:
        from ..cardiag.service import definitions as D
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, tr("Import Definition Pack"), "",
                                                  tr("Definition packs") + " (*.json *.csv *.odx *.odx-d *.pdx);;"
                                                  + tr("All files") + " (*)")
            if not path:
                return False
        try:
            pack, dest, warnings = D.import_pack(path)
        except D.PackError as e:
            QMessageBox.warning(self, tr("Import Definition Pack"), e.text(_lang()))
            self.log_line("✘ " + e.text(_lang()))
            return False
        except OSError as e:
            QMessageBox.warning(self, tr("Import Definition Pack"), str(e))
            return False
        self.log_line(tr("Pack imported: {}").replace("{}", str(dest)))
        for w in warnings[:20]:
            self.log_line("⚠ " + w.get(_lang()))
        self.reload_packs(select_path=str(dest))
        return True

    def save_template(self) -> None:
        from ..cardiag.service import definitions as D
        path, _ = QFileDialog.getSaveFileName(self, tr("Save Pack Template"), "service-pack-template.json",
                                              "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(D.template_text())
            self.log_line(tr("Template saved: {}").replace("{}", path))

    def _load_plugin_setting(self) -> None:
        try:
            path = _settings().value(SETTING_PLUGIN, "") or ""
        except Exception:  # noqa: BLE001
            path = ""
        if path:
            try:
                from ..cardiag.service.security import load_plugin
                self.plugin = load_plugin(path)
            except Exception:  # noqa: BLE001 - a moved plug-in is simply not loaded
                self.plugin = None
        self._plugin_label()

    def _plugin_label(self) -> None:
        self.b_plugin.setToolTip(tr("Seed/key plug-in: {}").replace("{}", self.plugin.describe()) if self.plugin
                                 else tr("No seed/key plug-in selected"))

    def choose_plugin(self, path: str = "", licensed: bool | None = None) -> bool:
        from ..cardiag.service.security import load_plugin
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, tr("Select Seed/Key Plug-in"), "",
                                                  tr("Seed/key plug-ins") + " (*.py *.dll)")
            if not path:
                return False
        if licensed is None:
            licensed = QMessageBox.question(
                self, tr("Security Plug-in"),
                tr("Use this plug-in only if you are licensed to use it for these control units. RAD IDE contains "
                   "no security algorithms and does not support immobiliser, key or odometer functions.\n\n"
                   "Are you licensed to use this plug-in?")) == QMessageBox.StandardButton.Yes
        if not licensed:
            return False
        try:
            self.plugin = load_plugin(path)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, tr("Security Plug-in"), str(e))
            return False
        try:
            _settings().setValue(SETTING_PLUGIN, path)
        except Exception:  # noqa: BLE001
            pass
        self._audit({"action": "confirmation", "id": "seedkey_plugin", "confirmation": f"licensed plug-in {path}"})
        self.log_line(tr("Seed/key plug-in: {}").replace("{}", self.plugin.describe()))
        self._plugin_label()
        return True

    def refresh_audit(self) -> None:
        if self.profile is None:
            return
        lines = []
        for e in self.profile.audit_entries(limit=300):
            what = e.get("confirmation") or f"{e.get('request', '')} -> {e.get('response', '') or e.get('error', '')}"
            lines.append(f"{e.get('time', '')}  {e.get('action', '')}/{e.get('id', '')}  {e.get('ecu', '')}  {what}")
        self.audit.setPlainText("\n".join(lines))
        self.audit.verticalScrollBar().setValue(self.audit.verticalScrollBar().maximum())

    def export_audit(self) -> None:
        if self.profile is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export Audit Log"), f"audit-{self.profile.vin}.csv", "CSV (*.csv)")
        if path:
            n = self.profile.export_audit_csv(path)
            self.log_line(tr("Audit log exported: {}").replace("{}", f"{path} ({n})"))

    def refresh_history(self) -> None:
        self.history.clear()
        if self.profile is None:
            return
        ar = _lang() == "ar"
        for h in reversed(self.profile.history[-200:]):
            self.history.addItem(f"{h.get('time', '')}  [{h.get('kind', '')}]  "
                                 f"{(h.get('summary_ar') if ar else h.get('summary')) or h.get('summary', '')}")

    def add_repair(self) -> None:
        note = self.h_note.text().strip()
        if not note or self.profile is None:
            return
        self.profile.add_history("repair", note, note)
        self._audit({"action": "repair_note", "id": "", "confirmation": note})
        self.h_note.clear()
        self.refresh_history()

    def _ensure_notice(self) -> bool:
        """The one-time notice: service functions change how the car behaves; keep to the instructions."""
        key = "cardiag/service/noticeAccepted"
        try:
            s = _settings()
            if s.value(key, False) in (True, "true", "1", 1):
                return True
        except Exception:  # noqa: BLE001
            return True
        ok = QMessageBox.question(
            self, tr("Service Functions"),
            tr("Service functions make the car's control units move parts (pumps, fans, brakes) and change stored "
               "values. Follow the preconditions, keep clear of moving parts, and only work on vehicles you own or "
               "are authorised to service.\n\nContinue?")) == QMessageBox.StandardButton.Yes
        if ok:
            s.setValue(key, True)
        return ok


# ============================================================================================= IDE glue
class CarDiagService:
    def __init__(self, win):
        self.win = win
        self.panel: ServicePanel | None = None
        win.cardiag_service = self
        QTimer.singleShot(0, self._menus)
        try:
            from . import cardiag_scan
            if self._hook not in cardiag_scan.TAB_HOOKS:
                cardiag_scan.TAB_HOOKS.append(self._hook)
        except Exception:  # noqa: BLE001 - the scan tool is optional
            pass

    def _hook(self, wb) -> None:
        tabs = getattr(wb, "tabs", None)
        if tabs is None:
            return
        panel = ServicePanel(self.win, workbench=wb)
        tabs.addTab(panel, tr("Service"))
        wb.service_panel = panel

        def follow(on: bool) -> None:
            """The workbench connected through an adapter / the ELM327 Demo car: use that connection here too."""
            busy = panel.worker is not None and panel.worker.is_alive()
            if busy:
                return
            if on and getattr(wb, "link", None) is not None:
                if panel.conn.currentData() != "link" or panel._link is not wb.link:
                    panel.conn.setCurrentIndex(panel.conn.findData("link"))
                    if panel.conn.currentData() == "link" and panel._link is not wb.link:
                        panel.connect_link()
            elif not on and panel.conn.currentData() == "link":
                panel._link = None
                panel.connect_demo()
        try:
            wb.connected.connect(follow)
        except Exception:  # noqa: BLE001
            pass

    def _menus(self) -> None:
        tools = next((a.menu() for a in self.win.menuBar().actions()
                      if a.menu() is not None and a.text().replace("&", "") == "Tools"), None)
        if tools is None or any(a.objectName() == "CarDiagServiceAction" for a in tools.actions()):
            return
        a = QAction("Car &Service Functions...", tools)
        a.setObjectName("CarDiagServiceAction")
        a.setToolTip("Service routines, actuator tests, resets and clearing a specific fault")
        a.triggered.connect(lambda: self.open())
        tools.addAction(a)
        self.action = a

    def open(self) -> ServicePanel:
        alive = False
        if self.panel is not None:
            try:
                self.panel.objectName()
                alive = True
            except RuntimeError:
                alive = False
        if not alive:
            self.panel = ServicePanel(self.win)
        show = getattr(self.win, "_show_tab", None)
        if callable(show):
            show(self.panel, tr("Service Functions"))
        else:
            self.panel.show()
        return self.panel


def install(win) -> None:
    CarDiagService(win)
