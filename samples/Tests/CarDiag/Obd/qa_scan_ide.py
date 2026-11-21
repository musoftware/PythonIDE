"""IDE test of Tools > Car Diagnostics... (OBD-II scan tool) against the Demo car, in the real IDE.

Run (English, then Arabic + dark):
    set RADIDE_NO_BROWSER=1 & .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\Obd\\qa_scan_ide.py
    set QA_LANG=ar & set QA_THEME=dark & .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\Obd\\qa_scan_ide.py

Uses samples/Tests/QA/Integration/qh.py (QSettings org RADIDE-TEST, screenshots only with widget.grab() into
%TEMP%\\radide-qa\\shots\\obd_<lang>[_dark]_*.png).
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANG = os.environ.get("QA_LANG", "")
THEME = os.environ.get("QA_THEME", "")
TAG = (LANG or "en") + ("_" + THEME if THEME else "")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ.setdefault("RADIDE_CARDIAG_HOME", tempfile.mkdtemp(prefix="cardiag-obd-ide-"))
os.environ.setdefault("QA_NAME", "cardiag-obd-" + TAG)
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import MSGS, check, finish, pump, wait  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from PyQt6.QtWidgets import QDialog  # noqa: E402

AR = LANG == "ar"
if LANG:
    from radide import i18n
    i18n.set_language(qh.app, LANG)
w = qh.window()
if THEME:
    from radide.features.workbench import set_theme
    set_theme(w, THEME.capitalize())
    pump(0.5)


def i18n_tr(text):
    from radide import i18n
    return i18n.tr(text)


def shot(widget, name):
    return qh.shot(widget, f"obd_{TAG}_{name}")


def texts(tree, col=0):
    out = []
    for i in range(tree.topLevelItemCount()):
        it = tree.topLevelItem(i)
        out.append(it.text(col))
        out.extend(it.child(j).text(col) for j in range(it.childCount()))
    return out


# --------------------------------------------------------------------------------------- open the workbench
act = next((a for m in [a.menu() for a in w.menuBar().actions() if a.menu()] for a in m.actions()
            if a.objectName() == "CarDiagScanAction"), None)
check("Tools > Car Diagnostics... action", act is not None)
act.trigger()
pump(0.5)
scan = getattr(w, "cardiag_scan", None)
wb = scan.wb if scan is not None else None
check("workbench opened as an IDE tab", wb is not None and w.tabs.indexOf(wb) >= 0)
names = [wb.tabs.widget(i).objectName() for i in range(wb.tabs.count())]
check("tabs Faults / Live / Freeze / Readiness / Tests / Info / Log",
      all(f"CarDiagTab_{t}" in names for t in ("Faults", "Live", "Freeze", "Readiness", "Tests", "Info", "Log")), names)
check("buttons disabled before connecting", not wb.b_read.isEnabled() and not wb.b_clear.isEnabled())
check("adapter list has the shared connection", wb.adapter.findData("shared") >= 0)

# --------------------------------------------------------------------------------------- Demo car
from radide.cardiag.obd.vehicle import DemoVehicle  # noqa: E402

car = DemoVehicle(realtime=False)
wb.connect_demo(car)
pump(0.5)
check("connected to the Demo car", wb.client is not None and wb.b_read.isEnabled())
from radide.cardiag.obd.vehicle import VIN  # noqa: E402
check("header: VIN", VIN in wb.h_vin.text(), wb.h_vin.text())
check("header: MIL on", wb.mil_lamp.state is True, wb.h_mil.text())
check("header: 2 control units", "2" in wb.h_ecus.text(), wb.h_ecus.text())
check("header: battery voltage", "V" in wb.h_volt.text(), wb.h_volt.text())

# --------------------------------------------------------------------------------------- Faults
wb.tabs.setCurrentIndex(wb.tab_index("Faults"))
wb.read_codes()
pump(0.3)
codes = [wb.dtc_tree.topLevelItem(i).text(0) for i in range(wb.dtc_tree.topLevelItemCount())]
check("stored / pending / permanent codes listed", {"P0301", "P0171", "P0420", "P0715"} <= set(codes), codes)
p0301 = next(wb.dtc_tree.topLevelItem(i) for i in range(wb.dtc_tree.topLevelItemCount())
             if wb.dtc_tree.topLevelItem(i).text(0) == "P0301")
check("P0301 status shows stored + permanent", p0301.text(1).count(",") == 1, p0301.text(1))
wb.dtc_tree.setCurrentItem(p0301)
pump(0.2)
view = wb.dtc_view.toPlainText()
check("explanation of P0301 shown", "P0301" in view and len(view) > 200, view[:300])
check("explanation in the UI language", (any("؀" <= ch <= "ۿ" for ch in view)) if AR else
      ("misfire" in view.lower()), view[:300])
check("status explained (stored / permanent)", ("دائم" in view) if AR else ("Permanent" in view), view[-400:])
shot(wb, "faults")

# --------------------------------------------------------------------------------------- Freeze frame
wb.read_freeze()
pump(0.3)
check("freeze frames for both ECUs", wb.ff_ecu.count() == 2, wb.ff_ecu.count())
i = wb.ff_ecu.findData("7E8")
wb.ff_ecu.setCurrentIndex(i)
wb._show_freeze()
check("freeze frame tied to P0301", "P0301" in wb.ff_head.text(), wb.ff_head.text())
rows = [" | ".join(wb.ff_table.item(r, c).text() for c in range(wb.ff_table.columnCount()) if wb.ff_table.item(r, c))
        for r in range(wb.ff_table.rowCount())]
check("freeze frame rpm 2150", any("2150" in v for v in rows), rows)
wb.dtc_tree.setCurrentItem(p0301)
check("fault view links to its freeze frame", "freeze" in wb.dtc_view.toHtml())
wb.tabs.setCurrentIndex(wb.tab_index("Freeze"))
shot(wb, "freeze")

# --------------------------------------------------------------------------------------- Readiness
wb.r_cycle.setChecked(False)
wb.read_readiness()
pump(0.3)
check("readiness monitors listed", wb.ready_table.rowCount() >= 8, wb.ready_table.rowCount())
check("all complete + MIL on summary", ("لمبة" in wb.ready_summary.text() or "MIL" in wb.ready_summary.text()),
      wb.ready_summary.text())
rv = wb.ready_view.toPlainText()
check("monitor explanation + drive cycle text", len(rv) > 200, rv[:200])
wb.tabs.setCurrentIndex(wb.tab_index("Readiness"))
shot(wb, "readiness_before")

# --------------------------------------------------------------------------------------- Tests (06) / Info (09)
wb.read_tests()
pump(0.3)
allt = texts(wb.tests_tree, 5)
check("mode 06 results with a failed test", wb.tests_tree.topLevelItemCount() >= 2 and i18n_tr("FAIL") in allt,
      (wb.tests_summary.text(), allt))
check("mode 06 limits shown", any(wb.tests_tree.topLevelItem(0).child(0).text(c) for c in (2, 3)))
wb.tabs.setCurrentIndex(wb.tab_index("Tests"))
shot(wb, "tests06")
wb.read_info()
pump(0.3)
info = wb.info_view.toPlainText()
check("mode 09 VIN", VIN in info, info[:300])
check("info has CALID / CVN / ECU names", "CALID" in info and "CVN" in info and len(wb.vinfo.names) >= 2, info[:600])
wb.tabs.setCurrentIndex(wb.tab_index("Info"))
shot(wb, "info09")

# --------------------------------------------------------------------------------------- Live data
wb.tabs.setCurrentIndex(wb.tab_index("Live"))
check("supported PIDs listed", len(list(wb._pid_items())) > 30, len(list(wb._pid_items())))
wb.select_pids([0x0C, 0x0D, 0x05, 0x04, 0x11, 0x42])
check("6 PIDs selected", len(wb._live_keys) == 6, wb._live_keys)
wb.rate.setValue(100)
wb.b_live.setChecked(True)
pump(0.2)
first_rpm = wb.live_table.item(0, 1).text()
first_temp = wb.live_table.item(2, 1).text()
for _ in range(25):
    car.advance(4.0)
    pump(0.12)
check("live values change (engine warming, driving)",
      wb.live_table.item(2, 1).text() != first_temp or wb.live_table.item(0, 1).text() != first_rpm,
      (first_rpm, first_temp, wb.live_table.item(0, 1).text(), wb.live_table.item(2, 1).text()))
check("min / max columns filled", wb.live_table.item(0, 3).text() not in ("-", "") and
      wb.live_table.item(0, 4).text() not in ("-", ""))
check("gauges show values", all(g.value is not None for g in wb.gauges if g.property("key") is not None))
log = Path(qh.WORK) / f"obd_{TAG}_live.csv"
wb.start_recording(str(log))
for _ in range(10):
    car.advance(1.0)
    pump(0.12)
wb.stop_recording()
check("CSV log written", log.exists() and log.read_text(encoding="utf-8").count("\n") >= 4,
      log.read_text(encoding="utf-8")[:200] if log.exists() else "missing")
shot(wb, "live")
wb.b_live.setChecked(False)
rec = wb.play_log(str(log))
check("playback started", rec is not None and wb._playback is not None and wb.play_bar.isVisible())
wb.play_speed.setCurrentIndex(wb.play_speed.count() - 1)
wait(lambda: wb.b_pause.isChecked(), 15)
check("playback reached the end", wb.b_pause.isChecked() and wb.live_table.item(0, 1).text() != "-")
shot(wb, "playback")
wb.stop_playback()
check("playback stopped, PID selection back", wb._playback is None and len(wb._live_keys) == 6)

# --------------------------------------------------------------------------------------- Clear codes
wb.tabs.setCurrentIndex(wb.tab_index("Faults"))
wb.read_codes()
pump(0.2)
dlg_seen = {}


def _exec(self):
    dlg_seen["text"] = self.view.toPlainText()
    dlg_seen["enabled_before"] = self.b_clear.isEnabled()
    dlg_seen["safety"] = list(self.safety)
    shot(self, "clear_dialog")
    self.ack.setChecked(True)
    dlg_seen["enabled_after"] = self.b_clear.isEnabled()
    return QDialog.DialogCode.Accepted


from radide.features import cardiag_scan as CS  # noqa: E402
_orig_exec = CS.ClearCodesDialog.exec
CS.ClearCodesDialog.exec = _exec
car_engine_on = car.rpm() > 300
wb.clear_codes()
pump(0.4)
CS.ClearCodesDialog.exec = _orig_exec
t = dlg_seen.get("text", "")
check("confirmation lists the codes to clear", all(c in t for c in ("P0301", "P0171", "P0420", "P0715")), t[:500])
check("confirmation warns about readiness monitors", ("الجاهزية" in t) if AR else ("readiness" in t.lower()), t[-800:])
check("permanent code mentioned as staying", t.count("P0301") >= 2, t)
check("Clear button only after the acknowledgement", dlg_seen.get("enabled_before") is False and
      dlg_seen.get("enabled_after") is True)
codes = [wb.dtc_tree.topLevelItem(i).text(0) for i in range(wb.dtc_tree.topLevelItemCount())]
if car_engine_on and any(m[0] == "warning" for m in MSGS[-2:]):
    check("engine running: clear refused and reported", True)
else:
    check("after clearing only the permanent code remains", codes == ["P0301"], codes)
    check("MIL off after clearing", wb.mil_lamp.state is False, wb.h_mil.text())
    st = [wb.ready_table.item(r, 1).text() for r in range(wb.ready_table.rowCount())]
    check("readiness reset to incomplete", st and st.count(i18n_tr("Incomplete")) >= 5, st)
    check("freeze frames erased", not wb.freeze)
wb.tabs.setCurrentIndex(wb.tab_index("Readiness"))
shot(wb, "readiness_after_clear")

# --------------------------------------------------------------------------------------- Log tab
wb.tabs.setCurrentIndex(wb.tab_index("Log"))
lt = wb.log_view.toPlainText()
check("log shows the traffic", "> " in lt and "7E8: 41 00" in lt and "7E9:" in lt, lt[:300])
shot(wb, "log")

# --------------------------------------------------------------------------------------- shared connection
from radide.cardiag.link import demo_link, set_current_link, current_link  # noqa: E402
link = demo_link()
set_current_link(link)
pump(0.2)
wb.adapter.setEnabled(True)
ok = wb.use_shared_link(ask=False)
wait(lambda: wb.vinfo is not None and wb.client is not None and wb._busy_n == 0, 15)
check("uses the Tools > Car Connection link", ok and wb.link is link and wb._shared)
wb.read_codes()
wait(lambda: wb._busy_n == 0 and wb.dtc_tree.topLevelItemCount() > 0, 15)
check("codes read through the ELM327 simulator", wb.dtc_tree.topLevelItemCount() > 0)
wb.disconnect()
check("disconnecting the workbench keeps the shared link open", current_link() is link)
wb.adapter.setCurrentIndex(wb.adapter.findData("shared"))
set_current_link(None)
set_current_link(link2 := demo_link())
pump(0.3)
wait(lambda: wb._busy_n == 0, 10)
check("follows a new shared connection", wb.link is link2)
set_current_link(None)
pump(0.3)
check("follows Tools > Car Connection > Disconnect", wb.client is None)
wb.connect_demo()
pump(0.3)

# --------------------------------------------------------------------------------------- translations
if AR:
    from radide import i18n
    check("tab titles in Arabic", wb.tabs.tabText(wb.tab_index("Faults")) != "Faults",
          [wb.tabs.tabText(i) for i in range(wb.tabs.count())])
    src = (HERE.parents[3] / "radide" / "features" / "cardiag_scan.py").read_text(encoding="utf-8")
    missing = [m for m in i18n.missing() if any(f'"{m}{suf}' in src for suf in ("", ":", "...", "."))]
    check("no untranslated scan-tool strings seen", not missing, missing[:20])
shot(wb, "final")
wb.disconnect()
finish(w)
