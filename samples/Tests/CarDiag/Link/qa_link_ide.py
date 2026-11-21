"""IDE test of Tools > Car Connection (Demo car simulator, no hardware), English then Arabic.

Covers: the menu, the Demo Car dock (ignition / engine / warning lamps / TCP server), the Connect to Car dialog
(Test Connection over Wi-Fi/TCP against the Demo car server, Connect with the Demo car), the shared current link and
its status-bar label, the Bus Monitor (live traffic, filter, raw command) and Find Control Units.

Run:  set RADIDE_NO_BROWSER=1 & .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\Link\\qa_link_ide.py
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ.setdefault("QA_NAME", "cardiag-link")
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, wait, shot, finish  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from radide.cardiag.link import current_link, set_current_link  # noqa: E402
from radide.cardiag.link.log import BUS_LOG  # noqa: E402
from radide.cardiag.link.manager import LinkConfig  # noqa: E402
from radide.cardiag.sim import LAMPS  # noqa: E402

w = qh.window()
pump(0.5)
feat = getattr(w, "cardiag_link", None)
check("feature installed", feat is not None)
tools = feat._menu("Tools")
menu = feat._menu("Car Connection", tools) if tools else None
check("Tools > Car Connection menu", menu is not None and menu.objectName() == "CarConnectionMenu")
names = [feat.plain(a.text()) for a in menu.actions() if not a.isSeparator()] if menu else []
check("menu items", names == ["Connect to Car...", "Disconnect", "Bus Monitor", "Demo Car (Simulator)",
                              "Find Control Units..."], names)

# ------------------------------------------------------------- Demo car dock
demo = feat.show_demo()
pump(0.3)
check("Demo Car dock shown", feat.dock_demo is not None and feat.dock_demo.isVisible())
check("one label per warning lamp", len(demo.lamp_labels) == len(LAMPS))
demo.c_eng.setChecked(True)
pump(0.8)
st = demo.car.state()
check("engine starts from the panel", st["engine_running"] and st["ignition"], st)
check("live values shown", "rpm" in demo.state.text() and "°C" in demo.state.text(), demo.state.text())
check("lamp labels follow the car", all(bool(lab.property("lamp_on")) == bool(st["lamps"].get(k))
                                        for k, lab in demo.lamp_labels.items()))
import socket  # noqa: E402
with socket.socket() as _s:          # a free port (35000 may be taken by a real Wi-Fi adapter tool)
    _s.bind(("127.0.0.1", 0))
    demo.srv_port.setValue(_s.getsockname()[1])
demo.toggle_server()
srv = demo.server
check("TCP server listening", srv is not None and srv.running and "Listening on 127.0.0.1:" in demo.srv_state.text(),
      demo.srv_state.text())
port = srv.port if srv is not None else 0
shot(demo, "cardiag_link_demo_en")

# ------------------------------------------------------------- Connect dialog: test over TCP, then Demo car
from radide.cardiag.link.qt import ConnectDialog  # noqa: E402
dlg = ConnectDialog(w, LinkConfig(kind="wifi", host="127.0.0.1", tcp_port=port))
dlg.show()
pump(0.2)
check("Wi-Fi page selected", dlg.pages.currentIndex() == 2 and dlg.host.text() == "127.0.0.1")
dlg.connect_link(test=True)
ok = wait(lambda: "OK - " in dlg.status.toPlainText() or "failed" in dlg.status.toPlainText(), 30)
check("Test Connection over TCP to the Demo car server", ok and "OK - " in dlg.status.toPlainText()
      and demo.car.vin in dlg.status.toPlainText(), dlg.status.toPlainText())
check("test does not change the current link", current_link() is None)
dlg.kind.setCurrentIndex(dlg.kind.findData("demo"))
pump(0.1)
check("Demo page selected, protocol locked", dlg.pages.currentIndex() == 0 and not dlg.protocol.isEnabled())
shot(dlg, "cardiag_link_connect_en")
dlg.connect_and_accept()
check("Connect with the Demo car", wait(lambda: current_link() is not None, 30), dlg.status.toPlainText())
pump(0.3)
check("status bar shows the connection", feat.status is not None and feat.status.isVisible()
      and "ELM327" in feat.status.text() and "CAN" in feat.status.text(), feat.status.text() if feat.status else None)
dlg.close()

# ------------------------------------------------------------- Bus monitor
mon = feat.show_monitor()
pump(0.3)
check("Bus Monitor dock shown", feat.dock_monitor.isVisible())
check("monitor shows the init traffic", "ATZ" in mon.view.toPlainText() or "ATE0" in mon.view.toPlainText())
mon.raw.setText("0902")
mon.send_raw()
check("raw command answered", wait(lambda: "49 02" in mon.view.toPlainText().upper()
                                   or "4902" in mon.view.toPlainText().upper().replace(" ", ""), 10))
mon.filter.setText("0902")
pump(0.2)
lines = [x for x in mon.view.toPlainText().splitlines() if x.strip()]
check("filter keeps only matching lines", lines and all("0902" in x.replace(" ", "") for x in lines), lines[:5])
mon.filter.clear()
n = len(BUS_LOG.snapshot())
mon.b_pause.setChecked(True)
before = mon.view.toPlainText()
mon.raw.setText("ATRV")
mon.send_raw()
wait(lambda: len(BUS_LOG.snapshot()) > n + 1, 10)
pump(0.2)
check("pause stops the live view", mon.view.toPlainText() == before)
mon.b_pause.setChecked(False)
shot(mon, "cardiag_link_monitor_en")

# ------------------------------------------------------------- Find control units
fd = feat.find_ecus()
pump(0.2)
check("Find Control Units uses the current link", fd.link is current_link() and fd.b_start.isEnabled())
fd.start()
check("scan finished", wait(lambda: fd.b_start.isEnabled() and fd.table.rowCount() > 0, 60), fd.note.text())
found = [fd.table.item(r, 1).text() for r in range(fd.table.rowCount())]
check("five Demo car control units found", fd.table.rowCount() >= 5 and "7E0" in found, found)
check("engine ECU marked as OBD", any(fd.table.item(r, 3).text() == "✓" for r in range(fd.table.rowCount())))
shot(fd, "cardiag_link_ecus_en")
fd.close()

# ------------------------------------------------------------- Arabic
from radide import i18n  # noqa: E402
i18n.set_language(qh.app, "ar")
pump(0.5)
check("menu title in Arabic", "الاتصال بالسيارة" in i18n.shown(menu, "title"), i18n.shown(menu, "title"))
check("lamp names in Arabic", "لمبة" in i18n.shown(demo.lamp_labels["mil"]), i18n.shown(demo.lamp_labels["mil"]))
dlg = ConnectDialog(w, LinkConfig(kind="demo"))
dlg.show()
pump(0.3)
check("Connect dialog in Arabic", "الاتصال بالسيارة" in i18n.shown(dlg, "windowTitle")
      and "اختبار" in i18n.shown(dlg.b_test), (i18n.shown(dlg, "windowTitle"), i18n.shown(dlg.b_test)))
check("adapter kinds in Arabic", "السيارة التجريبية" in dlg.kind.currentText(), dlg.kind.currentText())
dlg.connect_link(test=True)
check("status messages in Arabic", wait(lambda: "تم - " in dlg.status.toPlainText(), 30), dlg.status.toPlainText())
shot(dlg, "cardiag_link_connect_ar")
dlg.close()
fd = feat.find_ecus()
fd.start()
wait(lambda: fd.b_start.isEnabled() and fd.table.rowCount() > 0, 60)
pump(0.2)
check("Find Control Units result in Arabic", "وحدة تحكم" in i18n.shown(fd.note), i18n.shown(fd.note))
shot(fd, "cardiag_link_ecus_ar")
fd.close()
shot(demo, "cardiag_link_demo_ar")
i18n.set_language(qh.app, "en")

# ------------------------------------------------------------- disconnect + cleanup
feat.disconnect()
pump(0.3)
check("Disconnect clears the link and the status label", current_link() is None and not feat.status.isVisible())
demo.toggle_server()
check("TCP server stopped", demo.server is None and not srv.running)
demo.c_eng.setChecked(False)
set_current_link(None)
finish(w)
