"""Qt widgets of the link layer: the Bus Monitor (raw adapter / bus traffic, live), the Connect Adapter dialog
(Demo car, COM port with scan + automatic baud rate, Wi-Fi, Bluetooth LE, J2534, python-can; Test connection),
the Demo Car panel (ignition / engine / drive / overheat, warning lamps, TCP server for other apps) and the Find
Control Units dialog. UI text is English; radide/i18n translates it (Arabic in ar.json)."""
from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout,
                             QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QProgressBar,
                             QPushButton, QSpinBox, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
                             QWidget)

from . import protocols
from .base import LinkError
from .log import BUS_LOG, ERROR, INFO, RX, TX
from .manager import KINDS, LinkConfig, current_link, open_link, set_current_link

SETTINGS_KEY = "cardiag/link/config"


def _lang() -> str:
    try:
        from ...i18n import language
        return language()
    except Exception:  # noqa: BLE001
        return "en"


def tr(text: str) -> str:
    try:
        from ...i18n import tr as _tr
        return _tr(text)
    except Exception:  # noqa: BLE001
        return text


def err_text(e) -> str:
    if isinstance(e, LinkError):
        return e.ar if _lang() == "ar" else e.en
    return str(e)


def load_config() -> LinkConfig:
    import json
    raw = QSettings().value(SETTINGS_KEY, "")
    try:
        return LinkConfig.from_dict(json.loads(raw)) if raw else LinkConfig()
    except (ValueError, TypeError):
        return LinkConfig()


def save_config(cfg: LinkConfig) -> None:
    import json
    QSettings().setValue(SETTINGS_KEY, json.dumps(cfg.to_dict()))


class _Bridge(QObject):
    entry = pyqtSignal(object)
    done = pyqtSignal(object, object, object)       # callback, result, error
    progress = pyqtSignal(int, int, str)


def run_in_thread(bridge: _Bridge, work, done) -> threading.Thread:
    def thread():
        try:
            r, e = work(), None
        except Exception as ex:  # noqa: BLE001 - shown to the user
            r, e = None, ex
        bridge.done.emit(done, r, e)
    t = threading.Thread(target=thread, daemon=True, name="radide-cardiag-link")
    t.start()
    return t


# ===================================================================== Bus Monitor
class BusMonitor(QWidget):
    """Live raw traffic of every adapter (AT commands, requests, CAN frames, J2534 messages)."""
    COLORS = {TX: "#1565c0", RX: "#2e7d32", INFO: "#757575", ERROR: "#c62828"}

    def __init__(self, parent=None, log=None):
        super().__init__(parent)
        self.setObjectName("CarDiagBusMonitor")
        self.log = log or BUS_LOG
        self.bridge = _Bridge()
        self.bridge.entry.connect(self._append)
        self.bridge.done.connect(lambda cb, r, e: cb(r, e))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(2, 2, 2, 2)
        bar = QHBoxLayout()
        self.b_pause = QPushButton("Pause")
        self.b_pause.setCheckable(True)
        self.b_clear = QPushButton("Clear")
        self.b_save = QPushButton("Save Log...")
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter (e.g. 7E8, ATSH, 19 02)")
        self.only_errors = QCheckBox("Errors only")
        self.raw = QLineEdit()
        self.raw.setPlaceholderText("Send a raw command to the adapter (e.g. ATRV, 0100)")
        self.b_send = QPushButton("Send")
        for w in (self.b_pause, self.b_clear, self.b_save, self.filter, self.only_errors):
            bar.addWidget(w)
        lay.addLayout(bar)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(20000)
        self.view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.view.setProperty("i18n_skip", True)
        f = QFont("Consolas")
        f.setStyleHint(QFont.StyleHint.Monospace)
        self.view.setFont(f)
        lay.addWidget(self.view, 1)
        send = QHBoxLayout()
        send.addWidget(self.raw, 1)
        send.addWidget(self.b_send)
        lay.addLayout(send)
        self.b_clear.clicked.connect(self.clear)
        self.b_save.clicked.connect(self.save_dialog)
        self.filter.textChanged.connect(self.reload)
        self.only_errors.toggled.connect(self.reload)
        self.b_send.clicked.connect(self.send_raw)
        self.raw.returnPressed.connect(self.send_raw)
        self.log.subscribe(self._from_thread)
        self.destroyed.connect(lambda *_: self.log.unsubscribe(self._from_thread))
        self.reload()

    def _from_thread(self, entry) -> None:
        try:
            self.bridge.entry.emit(entry)
        except RuntimeError:
            self.log.unsubscribe(self._from_thread)

    def _match(self, e) -> bool:
        if self.only_errors.isChecked() and e.direction != ERROR:
            return False
        f = self.filter.text().strip().upper()
        return not f or f in e.text.upper() or f.replace(" ", "") in e.text.upper().replace(" ", "")

    def _append(self, e) -> None:
        if self.b_pause.isChecked() or not self._match(e):
            return
        cur = self.view.textCursor()
        cur.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(self.COLORS.get(e.direction, "#000000")))
        if self.view.document().characterCount() > 1:
            cur.insertText("\n")
        cur.insertText(e.line(), fmt)
        self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())

    def reload(self) -> None:
        self.view.clear()
        for e in self.log.snapshot()[-5000:]:
            self._append(e)

    def clear(self) -> None:
        self.log.clear()
        self.view.clear()

    def save_dialog(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Bus Log", "bus.log", "Log files (*.log *.txt)")
        if path:
            self.log.save(path)

    def send_raw(self) -> None:
        text = self.raw.text().strip()
        link = current_link()
        if not text:
            return
        if link is None or not hasattr(link, "raw"):
            self.log.error("ui", tr("Connect an ELM327 adapter (or the Demo car) first."))
            return
        self.raw.clear()

        def work():
            with link.lock:
                return link.raw(text, 5.0)
        run_in_thread(self.bridge, work, lambda r, e: e is not None and self.log.error("ui", err_text(e)))


# ===================================================================== Connect dialog
class ConnectDialog(QDialog):
    """Choose and test an adapter; on OK the link becomes the IDE's current car connection."""

    def __init__(self, parent=None, cfg: LinkConfig | None = None):
        super().__init__(parent)
        self.setWindowTitle("Connect to Car")
        self.setObjectName("CarDiagConnectDialog")
        self.resize(620, 460)
        self.bridge = _Bridge()
        self.bridge.done.connect(lambda cb, r, e: cb(r, e))
        self.link = None
        cfg = cfg or load_config()
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.kind = QComboBox()
        # (combo box items are not translated by radide/i18n: they are added in the UI language here)
        ar = _lang() == "ar"
        for k, en, ar_text in KINDS:
            self.kind.addItem(ar_text if ar and ar_text else en, k)
        form.addRow("Adapter:", self.kind)
        self.protocol = QComboBox()
        self.protocol.addItem(tr("Automatic (recommended)"), protocols.AUTO)
        for code in protocols.DETECT_ORDER:
            p = protocols.get(code)
            self.protocol.addItem(tr(p.name), code)
        form.addRow("Protocol:", self.protocol)
        lay.addLayout(form)
        self.pages = QStackedWidget()
        lay.addWidget(self.pages)
        # demo
        pg = QWidget()
        f = QFormLayout(pg)
        self.demo_proto = QComboBox()
        for code in ("6", "7", "8", "9", "3", "4", "5"):
            self.demo_proto.addItem(tr(protocols.get(code).name), code)
        self.demo_stn = QCheckBox("Identify as an STN chip (OBDLink-style)")
        f.addRow("Demo car bus:", self.demo_proto)
        f.addRow("", self.demo_stn)
        f.addRow(QLabel("A simulated car with five control units, live data, fault codes and service routines - "
                        "no hardware needed."))
        self.pages.addWidget(pg)
        # serial
        pg = QWidget()
        f = QFormLayout(pg)
        row = QHBoxLayout()
        self.port = QComboBox()
        self.port.setEditable(True)
        self.b_scan = QPushButton("Scan Ports")
        self.b_find = QPushButton("Find Adapter")
        row.addWidget(self.port, 1)
        row.addWidget(self.b_scan)
        row.addWidget(self.b_find)
        f.addRow("COM port:", row)
        self.baud = QComboBox()
        self.baud.addItem(tr("Automatic"), 0)
        for b in (9600, 38400, 57600, 115200, 230400, 500000):
            self.baud.addItem(str(b), b)
        f.addRow("Baud rate:", self.baud)
        f.addRow(QLabel("USB cables and paired Bluetooth (classic) adapters both appear as COM ports."))
        self.pages.addWidget(pg)
        # wifi
        pg = QWidget()
        f = QFormLayout(pg)
        self.host = QLineEdit()
        self.tcp_port = QSpinBox()
        self.tcp_port.setRange(1, 65535)
        f.addRow("Address:", self.host)
        f.addRow("Port:", self.tcp_port)
        f.addRow(QLabel("Join the adapter's Wi-Fi network first (usually 192.168.0.10, port 35000)."))
        self.pages.addWidget(pg)
        # ble
        pg = QWidget()
        f = QFormLayout(pg)
        row = QHBoxLayout()
        self.ble = QComboBox()
        self.ble.setEditable(True)
        self.b_ble = QPushButton("Scan Bluetooth LE")
        row.addWidget(self.ble, 1)
        row.addWidget(self.b_ble)
        f.addRow("Device:", row)
        self.pages.addWidget(pg)
        # j2534
        pg = QWidget()
        f = QFormLayout(pg)
        self.j2534 = QComboBox()
        self.j2534.setEditable(True)
        f.addRow("Device:", self.j2534)
        self.j2534_note = QLabel("")
        self.j2534_note.setWordWrap(True)
        f.addRow(self.j2534_note)
        self.pages.addWidget(pg)
        # python-can
        pg = QWidget()
        f = QFormLayout(pg)
        self.can_iface = QComboBox()
        self.can_iface.setEditable(True)
        self.can_iface.addItems(["pcan", "kvaser", "vector", "slcan", "ixxat", "gs_usb", "socketcan"])
        self.can_channel = QLineEdit()
        self.can_channel.setPlaceholderText("PCAN_USBBUS1 / 0 / COM7")
        f.addRow("Interface:", self.can_iface)
        f.addRow("Channel:", self.can_channel)
        self.pages.addWidget(pg)
        self.status = QPlainTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumHeight(110)
        self.status.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        lay.addWidget(self.status)
        self.busy = QProgressBar()
        self.busy.setRange(0, 0)
        self.busy.hide()
        lay.addWidget(self.busy)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.b_test = bb.addButton("Test Connection", QDialogButtonBox.ButtonRole.ActionRole)
        self.b_ok = bb.button(QDialogButtonBox.StandardButton.Ok)
        self.b_ok.setText("Connect")
        lay.addWidget(bb)
        bb.accepted.connect(self.connect_and_accept)
        bb.rejected.connect(self.reject)
        self.b_test.clicked.connect(lambda: self.connect_link(test=True))
        self.kind.currentIndexChanged.connect(self._kind_changed)
        self.b_scan.clicked.connect(self.scan_ports)
        self.b_find.clicked.connect(self.find_adapter)
        self.b_ble.clicked.connect(self.scan_ble)
        self.set_config(cfg)

    # ------------------------------------------------------------------ config
    def set_config(self, cfg: LinkConfig) -> None:
        self.kind.setCurrentIndex(max(0, self.kind.findData(cfg.kind)))
        self.protocol.setCurrentIndex(max(0, self.protocol.findData(cfg.protocol)))
        self.demo_proto.setCurrentIndex(max(0, self.demo_proto.findData(cfg.demo_protocol)))
        self.demo_stn.setChecked(cfg.demo_stn)
        self.port.setEditText(cfg.port)
        self.baud.setCurrentIndex(max(0, self.baud.findData(cfg.baud)))
        self.host.setText(cfg.host)
        self.tcp_port.setValue(cfg.tcp_port)
        self.ble.setEditText(cfg.ble_address)
        self.can_iface.setEditText(cfg.can_interface or "pcan")
        self.can_channel.setText(cfg.can_channel)
        self._kind_changed()
        if cfg.j2534_library:
            i = self.j2534.findData(cfg.j2534_library)
            if i >= 0:
                self.j2534.setCurrentIndex(i)

    def config(self) -> LinkConfig:
        return LinkConfig(
            kind=self.kind.currentData(), port=(self.port.currentData() or self.port.currentText()).strip(),
            baud=int(self.baud.currentData() or 0), host=self.host.text().strip(), tcp_port=self.tcp_port.value(),
            ble_address=(self.ble.currentData() or self.ble.currentText()).strip(),
            j2534_library=(self.j2534.currentData() or self.j2534.currentText()).strip(),
            can_interface=self.can_iface.currentText().strip(), can_channel=self.can_channel.text().strip(),
            protocol=self.protocol.currentData(), demo_protocol=self.demo_proto.currentData(),
            demo_stn=self.demo_stn.isChecked())

    def _kind_changed(self) -> None:
        k = self.kind.currentData()
        order = [x[0] for x in KINDS]
        self.pages.setCurrentIndex(order.index(k) if k in order else 0)
        self.protocol.setEnabled(k != "demo")
        if k == "serial" and self.port.count() == 0:
            self.scan_ports()
        if k == "j2534" and self.j2534.count() == 0:
            self.load_j2534()

    def say(self, text: str) -> None:
        self.status.appendPlainText(tr(text))

    # ------------------------------------------------------------------ discovery helpers
    def scan_ports(self) -> None:
        from .ports import list_ports
        cur = self.port.currentText()
        self.port.clear()
        try:
            found = list_ports()
        except LinkError as e:
            self.say(err_text(e))
            return
        for p in found:
            self.port.addItem(p.label, p.device)
        if not found:
            self.say("No COM ports found. Plug in the adapter or pair the Bluetooth adapter in Windows first.")
        if cur:
            self.port.setEditText(cur) if self.port.findData(cur) < 0 else self.port.setCurrentIndex(self.port.findData(cur))

    def find_adapter(self) -> None:
        from .ports import probe_ports
        self.say("Looking for an adapter on every COM port...")
        self.busy.show()

        def done(found, err):
            self.busy.hide()
            if err is not None:
                self.say(err_text(err))
                return
            if not found:
                self.say("No adapter answered.")
                return
            p, baud, ident = found[0]
            i = self.port.findData(p.device)
            self.port.setCurrentIndex(i) if i >= 0 else self.port.setEditText(p.device)
            self.baud.setCurrentIndex(max(0, self.baud.findData(baud)))
            self.say(f"{p.device}: {ident} @ {baud}")
        run_in_thread(self.bridge, probe_ports, done)

    def scan_ble(self) -> None:
        from .transport import ble_scan
        self.say("Scanning for Bluetooth LE adapters (5 s)...")
        self.busy.show()

        def done(found, err):
            self.busy.hide()
            if err is not None:
                self.say(err_text(err))
                return
            self.ble.clear()
            for addr, name in found or []:
                self.ble.addItem(f"{name} ({addr})", addr)
            self.say(f"{len(found or [])} device(s)")
        run_in_thread(self.bridge, ble_scan, done)

    def load_j2534(self) -> None:
        from .j2534 import devices
        import struct
        self.j2534.clear()
        devs = devices()
        for d in devs:
            self.j2534.addItem(d.label if d.usable else tr(f"{d.label} - not loadable"), d.library)
        bits = struct.calcsize("P") * 8
        if not devs:
            self.j2534_note.setText("No J2534 PassThru driver is installed (install your interface's driver).")
        elif not any(d.usable for d in devs):
            self.j2534_note.setText(f"The installed drivers are not {bits}-bit; RAD IDE's Python is {bits}-bit and "
                                    "cannot load them. Use the vendor's 64-bit driver.")
        else:
            self.j2534_note.setText("")

    # ------------------------------------------------------------------ connect
    def connect_link(self, test: bool = False, then=None) -> None:
        cfg = self.config()
        self.say(f"Connecting: {cfg.describe()} ...")
        self.busy.show()
        self.b_ok.setEnabled(False)
        self.b_test.setEnabled(False)

        def work():
            link = open_link(cfg)
            info = {"adapter": link.adapter_info, "protocol": link.protocol.name if link.protocol else "?",
                    "voltage": link.voltage()}
            try:
                from .obd import Obd
                info["vin"] = Obd(link).vin()
            except LinkError:
                info["vin"] = ""
            return link, info

        def done(r, err):
            self.busy.hide()
            self.b_ok.setEnabled(True)
            self.b_test.setEnabled(True)
            if err is not None:
                self.say("Connection failed: " + err_text(err))
                return
            link, info = r
            v = f"{info['voltage']:.1f} V" if info.get("voltage") else "-"
            self.say(f"OK - {info['adapter']} | {info['protocol']} | battery {v} | VIN {info.get('vin') or '-'}")
            save_config(cfg)
            if test:
                link.close()
            else:
                self.link = link
            if then is not None:
                then(link if not test else None)
        run_in_thread(self.bridge, work, done)

    def connect_and_accept(self) -> None:
        def then(link):
            if link is not None:
                set_current_link(link)
                self.accept()
        self.connect_link(test=False, then=then)


# ===================================================================== Demo car panel
class DemoCarPanel(QWidget):
    """Controls for the Demo car and its TCP server (so other OBD apps can connect to it)."""

    def __init__(self, parent=None, car=None):
        super().__init__(parent)
        from ..sim import LAMPS, demo_car
        self.setObjectName("CarDiagDemoCar")
        self.car = car or demo_car()
        self.server = None
        lay = QVBoxLayout(self)
        g = QGroupBox("Vehicle")
        gl = QGridLayout(g)
        self.c_ign = QCheckBox("Ignition on")
        self.c_eng = QCheckBox("Engine running")
        self.c_drive = QCheckBox("Driving")
        self.c_hot = QCheckBox("Overheating (thermostat stuck)")
        for i, w in enumerate((self.c_ign, self.c_eng, self.c_drive, self.c_hot)):
            gl.addWidget(w, i // 2, i % 2)
        self.state = QLabel("")
        self.state.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.state.setProperty("i18n_skip", True)
        gl.addWidget(self.state, 2, 0, 1, 2)
        lay.addWidget(g)
        g = QGroupBox("Warning lamps")
        gl = QGridLayout(g)
        self.lamp_labels = {}
        for i, (_bit, key, en, _ar) in enumerate(LAMPS):
            lab = QLabel(en)
            lab.setObjectName(f"lamp_{key}")
            self.lamp_labels[key] = lab
            gl.addWidget(lab, i // 2, i % 2)
        lay.addWidget(g)
        g = QGroupBox("TCP server (Wi-Fi adapter emulation)")
        gl = QHBoxLayout(g)
        self.srv_port = QSpinBox()
        self.srv_port.setRange(1, 65535)
        self.srv_port.setValue(35000)
        self.b_srv = QPushButton("Start Server")
        self.srv_state = QLabel("Stopped")
        gl.addWidget(QLabel("Port:"))
        gl.addWidget(self.srv_port)
        gl.addWidget(self.b_srv)
        gl.addWidget(self.srv_state, 1)
        lay.addWidget(g)
        lay.addStretch(1)
        self.c_ign.toggled.connect(lambda on: self.car.set_ignition(on))
        self.c_eng.toggled.connect(lambda on: self.car.start_engine() if on else self.car.stop_engine())
        self.c_drive.toggled.connect(lambda on: self.car.set_driving(on))
        self.c_hot.toggled.connect(lambda on: self.car.set_overheat(on))
        self.b_srv.clicked.connect(self.toggle_server)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)
        self.refresh()

    def refresh(self) -> None:
        s = self.car.state()
        for c, v in ((self.c_ign, s["ignition"]), (self.c_eng, s["engine_running"]), (self.c_drive, s["driving"])):
            if c.isChecked() != v:
                c.blockSignals(True)
                c.setChecked(v)
                c.blockSignals(False)
        self.state.setText(f"{s['rpm']} rpm   {s['speed']} km/h   {s['coolant']} °C   {s['battery']} V")
        for key, lab in self.lamp_labels.items():
            on = s["lamps"].get(key)
            lab.setStyleSheet("color: #c62828; font-weight: bold;" if on else "color: #9e9e9e;")
            lab.setProperty("lamp_on", bool(on))

    def toggle_server(self) -> None:
        from ..sim.server import DemoCarServer
        if self.server is not None and self.server.running:
            self.server.stop()
            self.server = None
            self.srv_state.setText("Stopped")
            self.b_srv.setText("Start Server")
            return
        self.server = DemoCarServer(self.car, "127.0.0.1", self.srv_port.value(), log=BUS_LOG)
        try:
            port = self.server.start()
        except OSError as e:
            self.server = None
            self.srv_state.setText(f"Cannot listen: {e}")
            return
        self.srv_state.setText(f"Listening on 127.0.0.1:{port}")
        self.b_srv.setText("Stop Server")

    def closeEvent(self, e) -> None:  # noqa: N802
        if self.server is not None:
            self.server.stop()
        super().closeEvent(e)


# ===================================================================== Find control units
class FindEcusDialog(QDialog):
    def __init__(self, parent=None, link=None):
        super().__init__(parent)
        self.setWindowTitle("Find Control Units")
        self.setObjectName("CarDiagFindEcus")
        self.resize(760, 420)
        self.link = link or current_link()
        self.bridge = _Bridge()
        self.bridge.done.connect(lambda cb, r, e: cb(r, e))
        self.bridge.progress.connect(self._progress)
        self._cancel = False
        self.ecus = []
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.full = QCheckBox("Full scan (every address - slower)")
        self.b_start = QPushButton("Scan")
        self.b_stop = QPushButton("Stop")
        row.addWidget(self.full)
        row.addStretch(1)
        row.addWidget(self.b_start)
        row.addWidget(self.b_stop)
        lay.addLayout(row)
        self.bar = QProgressBar()
        lay.addWidget(self.bar)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Control unit", "Request ID", "Response ID", "OBD", "Part number",
                                              "Software"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setProperty("i18n_skip_items", True)
        lay.addWidget(self.table, 1)
        self.note = QLabel("")
        lay.addWidget(self.note)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.b_start.clicked.connect(self.start)
        self.b_stop.clicked.connect(lambda: setattr(self, "_cancel", True))
        if self.link is None:
            self.note.setText("Not connected. Use Connect to Car first (or the Demo car).")
            self.b_start.setEnabled(False)

    def _progress(self, done: int, total: int, text: str) -> None:
        self.bar.setMaximum(max(1, total))
        self.bar.setValue(done)
        self.note.setText(text)

    def start(self) -> None:
        from .discovery import discover
        self._cancel = False
        self.b_start.setEnabled(False)
        link = self.link

        def work():
            with link.lock:
                return discover(link, full=self.full.isChecked(),
                                progress=lambda d, t, s: self.bridge.progress.emit(d, t, s),
                                cancelled=lambda: self._cancel)
        run_in_thread(self.bridge, work, self._done)

    def _done(self, ecus, err) -> None:
        self.b_start.setEnabled(True)
        if err is not None:
            self.note.setText(err_text(err))
            return
        self.ecus = ecus or []
        ar = _lang() == "ar"
        self.table.setRowCount(len(self.ecus))
        for i, e in enumerate(self.ecus):
            vals = [(e.name_ar if ar and e.name_ar else e.name) or "?", protocols.fmt_id(e.tx), protocols.fmt_id(e.rx),
                    "✓" if e.obd else "", e.ident.get(0xF187, ""), e.ident.get(0xF195, "")]
            for c, v in enumerate(vals):
                self.table.setItem(i, c, QTableWidgetItem(v))
        self.note.setText(f"{len(self.ecus)} control unit(s) found")
