"""IDE test of Tools > Car Service Functions (Demo car simulator), English then Arabic.

Run:  set RADIDE_NO_BROWSER=1 & .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\Service\\qa_service_ide.py
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ["RADIDE_CARDIAG_HOME"] = tempfile.mkdtemp(prefix="cardiag-svc-ide-")
os.environ.setdefault("QA_NAME", "cardiag-service")
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, wait, shot, finish, MSGS  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

w = qh.window()
act = next((a for m in [a.menu() for a in w.menuBar().actions() if a.menu()] for a in m.actions()
            if a.objectName() == "CarDiagServiceAction"), None)
check("Tools > Car Service Functions action", act is not None)
act.trigger()
pump(0.5)
feat = w.cardiag_service
p = feat.panel
check("panel opened as a tab", p is not None and w.tabs.indexOf(p) >= 0)
check("Demo car connected with its pack", p.car is not None and p.pack and p.pack.get("demo"))
check("vehicle profile from the demo VIN", p.profile is not None and p.profile.vin == "RADDEM0CAR0000001")


def idle():
    return p.worker is None or not p.worker.is_alive()


def run_and_wait(timeout=30):
    p.b_run.click()
    pump(0.2)
    ok = wait(lambda: idle() and p.b_run.isEnabled(), timeout)
    pump(0.3)
    return ok


# ------------------------------------------------------------- cooling bleed routine
check("select cooling bleed", p.select("routines", "cooling_bleed"))
check("precondition checklist shown", p.pre.count() == 5 and "°" in p.pre.item(1).text())
check("overheating warning shown", p.safety.isVisible() and "Overheating" in p.safety.text())
p.car.bleed_seconds = 3.0
p.b_run.click()
wait(lambda: idle(), 10)
pump(0.3)
check("unconfirmed checklist blocks the start", "Confirm every precondition" in p.status.text(), p.status.text())
p.set_all_confirmed()
seen = []
p.progress.valueChanged.connect(seen.append)
check("bleed finished", run_and_wait(40), p.status.text())
check("bleed progress to 100 %", p.progress.value() == 100 and len(seen) >= 3 and "Completed" in p.status.text(),
      (seen, p.status.text()))
check("instructions in the log", "➜" in p.log.toPlainText())
shot(p, "service_bleed_en")
p.d_cool.setValue(70)
check("demo condition widgets drive the simulator", p.car.coolant_c == 70)
p.set_all_confirmed()
run_and_wait()
check("automatic precondition check stops a warm engine", "Preconditions not met" in p.status.text(), p.status.text())
p.d_cool.setValue(20)

# ------------------------------------------------------------- fan test with return control
check("select fan test", p.select("io_controls", "fan_test"))
p.set_all_confirmed()
p.io_time.setValue(3)
p.io_state.setCurrentIndex(1)
p.b_run.click()
wait(lambda: p.car.engine.fan_duty() == 50, 5)
check("fan running at 50 % during the test", p.car.engine.fan_duty() == 50)
p.io_state.setCurrentIndex(2)
wait(lambda: p.car.engine.fan_duty() == 100, 5)
check("state switched while running", p.car.engine.fan_duty() == 100)
wait(lambda: idle(), 15)
pump(0.3)
check("control returned to the ECU", not p.car.engine.overrides and "control returned" in p.status.text().lower(),
      p.status.text())

# ------------------------------------------------------------- adaptation + security plug-in
check("select DRL coding", p.select("adaptations", "drl_coding"))
p.inputs[0].setCurrentIndex(1)
run_and_wait()
check("coding without plug-in refused", p.car.engine.coding_drl == 0 and "security" in p.status.text().lower(),
      p.status.text())
check("plug-in selected", p.choose_plugin(str(HERE / "demo_seedkey.py"), licensed=True))
run_and_wait()
check("coding with the user's plug-in", p.car.engine.coding_drl == 1, p.status.text())
p.select("adaptations", "service_reset")
p.set_all_confirmed()
p.car.engine.service_km = 5
run_and_wait()
check("service reset", p.car.engine.service_km == 15000, p.status.text())

# ------------------------------------------------------------- clear a specific fault
check("select clear fault page", p.select("fault"))
p.f_ecu.setCurrentIndex(p.f_ecu.findData("engine"))
p.read_faults()
check("faults read", "P0128" in " ".join(p.f_list.item(i).text() for i in range(p.f_list.count())))
p.f_code.setText("P0128")
p.show_fault("P0128")
check("explanation shown before clearing", "thermostat" in p.f_text.toPlainText().lower()
      and "Possible causes" in p.f_text.toPlainText())
n = len(MSGS)
p.b_run.click()
pump(0.3)
check("clear refused without repair confirmation", len(MSGS) > n and
      any(k[:2] == b"\x01\x28" for k in p.car.engine.dtcs))
p.f_repaired.setChecked(True)
run_and_wait()
check("P0128 cleared, P0217 kept", not any(k[:2] == b"\x01\x28" for k in p.car.engine.dtcs) and
      any(k[:2] == b"\x02\x17" for k in p.car.engine.dtcs), p.status.text())
p.f_ecu.setCurrentIndex(p.f_ecu.findData("airbag"))
p.read_faults()
p.f_code.setText("B0001-13")
p.show_fault("B0001-13")
check("airbag safety warning in explanation", "Airbag" in p.f_text.toPlainText())
p.f_repaired.setChecked(True)
run_and_wait()
wait(lambda: not p.car.airbag.dtcs and idle(), 10)
check("single clear unsupported -> confirmed clear-all fallback", not p.car.airbag.dtcs, p.status.text())
shot(p, "service_fault_en")

# ------------------------------------------------------------- packs
bad = Path(os.environ["RADIDE_CARDIAG_HOME"]) / "bad.json"
import json  # noqa: E402
from radide.cardiag.service import definitions as D  # noqa: E402
t = json.loads(D.template_text())
t["adaptations"][0]["name"] = "Odometer correction"
bad.write_text(json.dumps(t), encoding="utf-8")
n = len(MSGS)
check("policy-violating pack refused", not p.import_pack(str(bad)) and len(MSGS) > n and "odometer" in str(MSGS[-1]))
good = Path(os.environ["RADIDE_CARDIAG_HOME"]) / "good.json"
good.write_text(D.template_text(), encoding="utf-8")
before = p.pack_box.count()
check("template pack imported", p.import_pack(str(good)) and p.pack_box.count() == before + 1)
check("imported pack selected", p.pack and p.pack.get("name") == "My vehicle (template)")
p.pack_box.setCurrentIndex(0)
check("ODX import", p.import_pack(str(HERE / "sample_service.odx")))
p.pack_box.setCurrentIndex(0)

# ------------------------------------------------------------- audit / history
p.refresh_audit()
check("audit log shown", "clear_dtc/P0128" in p.audit.toPlainText() and "repair done" in p.audit.toPlainText())
check("history has service + clear entries", any(h["kind"] == "clear_dtc" for h in p.profile.history)
      and p.history.count() > 3)

# ------------------------------------------------------------- Car Diagnostics workbench tab
scan = getattr(w, "cardiag_scan", None)
if scan is not None:
    wb = scan.open()
    pump(0.5)
    check("Service tab in the Car Diagnostics workbench", getattr(wb, "service_panel", None) is not None and
          any(wb.tabs.tabText(i) == "Service" for i in range(wb.tabs.count())))

# ------------------------------------------------------------- Arabic
from radide import i18n  # noqa: E402
i18n.set_language(qh.app, "ar")
pump(1)
w.tabs.setCurrentWidget(p)
p.fill_tree()
p.select("routines", "brake_pads_open")
p.set_all_confirmed()
p.d_speed.setValue(30)
run_and_wait()
check("NRC shown in Arabic (vehicle speed too high)", "سرعة السيارة" in p.status.text(), p.status.text())
p.d_speed.setValue(0)
check("UI translated", i18n.shown(p.b_run) != "Run" and i18n.tr("Service Functions") != "Service Functions",
      i18n.shown(p.b_run))
check("routine names in Arabic", "تنفيس" in " ".join(p.tree.topLevelItem(0).child(i).text(0)
                                                     for i in range(p.tree.topLevelItem(0).childCount())))
p.select("routines", "cooling_bleed")
shot(p, "service_bleed_ar")
src = (HERE.parents[3] / "radide" / "features" / "cardiag_service.py").read_text(encoding="utf-8")
missing = [m for m in i18n.missing() if any(f'"{m}{suf}"' in src for suf in ("", ":", "...", "."))]
check("no untranslated service strings seen", not missing, missing[:15])
i18n.set_language(qh.app, "en")
finish(w)
