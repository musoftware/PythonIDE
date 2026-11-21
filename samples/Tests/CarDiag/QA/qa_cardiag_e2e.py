"""End-to-end QA of the car diagnostics tool as a car owner / mechanic would use it, in the real IDE, with the Demo
car through the simulated ELM327 adapter (one car for the scan tool, the fault guide and the service functions).

Run (English, then Arabic + dark):
    set RADIDE_NO_BROWSER=1 & .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\QA\\qa_cardiag_e2e.py
    set QA_LANG=ar & set QA_THEME=dark & .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\QA\\qa_cardiag_e2e.py

Journey: connect -> which warning lights are on and what they mean -> read faults (all control units) with
explanations and causes -> freeze frame -> live data (coolant temperature, rpm) -> symptom wizard ("العربية بتسخن")
-> explain with AI (mock provider) -> cooling-system bleed with its checklist and progress -> radiator fan test ->
clear one specific fault after confirming the repair and see it gone -> readiness -> diagnosis report (HTML) ->
none of the excluded functions exist.

qh.py: QSettings org RADIDE-TEST, screenshots only with widget.grab() into %TEMP%\\radide-qa\\shots\\e2e_<tag>_*.png.
"""
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
LANG = os.environ.get("QA_LANG", "")
THEME = os.environ.get("QA_THEME", "")
TAG = (LANG or "en") + ("_" + THEME if THEME else "")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ["RADIDE_CARDIAG_HOME"] = tempfile.mkdtemp(prefix="cardiag-e2e-")
os.environ.setdefault("QA_NAME", "cardiag-e2e-" + TAG)
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import MSGS, check, finish, pump, wait  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

AR = LANG == "ar"
ARABIC = re.compile(r"[؀-ۿ]")
if LANG:
    from radide import i18n
    i18n.set_language(qh.app, LANG)
w = qh.window()
if THEME:
    from radide.features.workbench import set_theme
    set_theme(w, THEME.capitalize())
    pump(0.5)


def shot(widget, name):
    return qh.shot(widget, f"e2e_{TAG}_{name}")


def lang_ok(text, en_word):
    return bool(ARABIC.search(text)) if AR else (en_word.lower() in text.lower())


from radide import ai  # noqa: E402


class MockProvider(ai.Provider):
    id = "mock-cardiag-e2e"
    name = "Mock"
    fallback_default = "mock-1"
    prompts: list = []

    def _run_chat(self, job, system, messages, model, opts):
        MockProvider.prompts.append((system, messages[-1].content))
        job.emit_delta("الخلاصة: ")
        return "الخلاصة: ابدأ بفحص مروحة الردياتير وترموستات المياه، ولا تفتح غطاء الردياتير والمحرك سخن."


# ============================================================================ connect (Demo car via ELM327 sim)
from radide.cardiag.sim.car import reset_demo_car  # noqa: E402
car = reset_demo_car(time_scale=2.0)
scan = w.cardiag_scan
w.findChild(type(w.menuBar()))
act = next((a for m in [a.menu() for a in w.menuBar().actions() if a.menu()] for a in m.actions()
            if a.objectName() == "CarDiagScanAction"), None)
check("Tools > Car Diagnostics... menu item", act is not None)
act.trigger()
pump(0.5)
wb = scan.wb
wb.adapter.setCurrentIndex(wb.adapter.findData("demo_elm"))
wb.toggle_connect()
check("connected to the Demo car through the ELM327 simulator",
      wait(lambda: wb.client is not None and wb.link is not None and wb._busy_n == 0, 30), wb.status.text())
wait(lambda: "VIN: -" not in wb.h_vin.text(), 15)
check("header shows the VIN", car.vin in wb.h_vin.text(), wb.h_vin.text())
check("header: check-engine lamp on", wb.mil_lamp.state is True, wb.h_mil.text())
shot(wb, "connected")

# ============================================================================ warning lights that are on
g = wb.guide
check("Guide tab inside the scan tool", g is not None and wb.tab_index("Guide") >= 0)
wb.tabs.setCurrentIndex(wb.tab_index("Guide"))
lit = g.read_car_lights() if hasattr(g, "read_car_lights") else None
wait(lambda: g.selected_lights(), 15)
sel = set(g.selected_lights())
check("lights read from the car: MIL, ABS, airbag lit", {"mil", "abs", "airbag"} <= sel, (lit, sel))
lv = g.l_view.toPlainText()
check("each lit light explained (what to do now) in the UI language",
      lang_ok(lv, "what to do now") and len(lv) > 300, lv[:300])
check("airbag / ABS codes live in other control units (named)", ("الوسائد" in lv or "ABS" in lv) if AR
      else ("Airbag" in lv or "ABS" in lv), lv[:600])
shot(wb, "lights")

# ============================================================================ faults with explanations
wb.tabs.setCurrentIndex(wb.tab_index("Faults"))
wb.read_codes()
wait(lambda: wb._busy_n == 0 and wb.dtc_tree.topLevelItemCount() > 0, 20)
codes = [wb.dtc_tree.topLevelItem(i).text(0) for i in range(wb.dtc_tree.topLevelItemCount())]
check("engine codes read (OBD-II)", {"P0301", "P0171", "P0420"} <= set(codes), codes)
check("fault summary translated", lang_ok(wb.fault_summary.text(), "code"), wb.fault_summary.text())
if hasattr(wb, "scan_all_units"):
    wb.scan_all_units()
    wait(lambda: wb._busy_n == 0 and any(wb.dtc_tree.topLevelItem(i).text(0).startswith("C0035")
                                         for i in range(wb.dtc_tree.topLevelItemCount())), 40)
codes = [wb.dtc_tree.topLevelItem(i).text(0) for i in range(wb.dtc_tree.topLevelItemCount())]
check("all control units scanned: ABS + airbag codes too", any(c.startswith("C0035") for c in codes)
      and any(c.startswith("B0") for c in codes), codes)
it = next(wb.dtc_tree.topLevelItem(i) for i in range(wb.dtc_tree.topLevelItemCount())
          if wb.dtc_tree.topLevelItem(i).text(0) == "P0171")
wb.dtc_tree.setCurrentItem(it)
pump(0.2)
view = wb.dtc_view.toPlainText()
check("P0171 explained with causes and checks", lang_ok(view, "lean") and
      (("الأسباب" in view) if AR else ("Possible causes" in view)), view[:400])
abs_it = next((wb.dtc_tree.topLevelItem(i) for i in range(wb.dtc_tree.topLevelItemCount())
               if wb.dtc_tree.topLevelItem(i).text(0).startswith("C0035")), None)
if abs_it is not None:
    wb.dtc_tree.setCurrentItem(abs_it)
    pump(0.2)
    v2 = wb.dtc_view.toPlainText()
    check("ABS fault flagged safety-relevant", ("السلامة" in v2 or "سلامة" in v2) if AR else ("Safety" in v2), v2[:400])
wb.dtc_tree.setCurrentItem(it)
shot(wb, "faults")

# ============================================================================ freeze frame
wb.read_freeze()
wait(lambda: wb._busy_n == 0 and bool(wb.freeze), 15)
wb.tabs.setCurrentIndex(wb.tab_index("Freeze"))
wb._show_freeze()
rows = [" | ".join(wb.ff_table.item(r, c).text() for c in range(wb.ff_table.columnCount()) if wb.ff_table.item(r, c))
        for r in range(wb.ff_table.rowCount())]
check("freeze frame tied to P0301 with rpm 812", "P0301" in wb.ff_head.text() and any("812" in r for r in rows),
      (wb.ff_head.text(), rows[:6]))
shot(wb, "freeze")

# ============================================================================ live data
wb.tabs.setCurrentIndex(wb.tab_index("Live"))
wait(lambda: len(list(wb._pid_items())) > 10, 15)
wb.select_pids([0x05, 0x0C, 0x0D, 0x42])
wb.rate.setValue(100)
wb.b_live.setChecked(True)
check("live coolant temperature and rpm", wait(lambda: wb.live_table.item(0, 1).text() not in ("-", "")
                                                and wb.live_table.item(1, 1).text() not in ("-", ""), 20),
      [wb.live_table.item(r, 1).text() for r in range(wb.live_table.rowCount())])
first = wb.live_table.item(1, 1).text()
wait(lambda: wb.live_table.item(1, 1).text() != first, 10)
check("live values update", wb.live_table.item(1, 1).text() != first, first)
shot(wb, "live")
wb.b_live.setChecked(False)
wait(lambda: wb._busy_n == 0, 10)

# ============================================================================ symptom wizard
found = g.find_symptom("العربية بتسخن")
check("symptom 'العربية بتسخن' -> overheating", found and found[0] == "overheating", found)
g.select_symptom("overheating")
g.answer("when", "idle")
r = g.answer("fan", "no")
check("wizard ranks the radiator fan first and watches coolant temperature", r["causes"][0]["id"] == "fan"
      and 5 in r["pids"], r["causes"][:2])
wb.tabs.setCurrentIndex(wb.tab_index("Guide"))
g.tabs.setCurrentIndex(2)
pump(0.2)
shot(wb, "symptoms")

# ============================================================================ explain with AI (mock)
g.provider = MockProvider()
check("use the car's data for the AI", g.use_car_data() and "P0301" in g.ai_codes.text(), g.ai_codes.text())
g.ai_symptoms = ["overheating"]
job = g.ask_ai()
wait(lambda: g._job is None, 20)
check("AI answer shown", "مروحة الردياتير" in g.ai_out.toPlainText(), g.ai_out.toPlainText()[:200])
sysmsg = MockProvider.prompts[-1][0] if MockProvider.prompts else ""
check("AI prompt refuses immobiliser / odometer / emissions-defeat help",
      all(k in sysmsg.lower() for k in ("immobili", "odometer")) and "emission" in sysmsg.lower(), sysmsg[:400])
g.tabs.setCurrentIndex(3)
shot(wb, "ai")

# ============================================================================ service: cooling-system bleed
sp = wb.service_panel
wb.tabs.setCurrentIndex(wb.tabs.indexOf(sp))
pump(0.3)
check("service tab follows the workbench connection (workbench pack)", sp._link is wb.link and sp.pack
      and sp.pack.get("demo") == "workbench", sp.pack and sp.pack.get("name"))
check("select cooling bleed", sp.select("routines", "cooling_bleed"))
check("bleed checklist shown", sp.pre.count() >= 4, sp.pre.count())
check("overheating safety warning shown", sp.safety.isVisible() and lang_ok(sp.safety.text(), "hot"),
      sp.safety.text())
sp.set_all_confirmed()
sp.b_run.click()
wait(lambda: sp.worker is None or not sp.worker.is_alive(), 20)
pump(0.3)
check("engine running: the car refuses the bleed (explained)", sp.progress.value() < 100 and sp.status.text(),
      sp.status.text())
car.stop_engine()          # the Demo Car panel (Tools > Car Connection > Demo Car) does the same
with car.lock:
    car.coolant = 60.0
wait(lambda: (car.update() or True) and car.rpm < 1, 15)
sp.set_all_confirmed()
seen = []
sp.progress.valueChanged.connect(seen.append)
sp.b_run.click()
check("bleed finished", wait(lambda: (sp.worker is None or not sp.worker.is_alive()) and sp.b_run.isEnabled(), 60),
      sp.status.text())
pump(0.3)
check("bleed progress reached 100 %", sp.progress.value() == 100 and len(seen) >= 3, (seen[-5:], sp.status.text()))
shot(wb, "bleed")

# ============================================================================ service: radiator fan test
check("select fan test", sp.select("io_controls", "fan_test"))
sp.set_all_confirmed()
sp.io_time.setValue(2)
sp.io_state.setCurrentIndex(sp.io_state.count() - 1)
sp.b_run.click()
check("fan runs during the test", wait(lambda: (car.update() or True) and car.fan_duty >= 50, 8), car.fan_duty)
wait(lambda: sp.worker is None or not sp.worker.is_alive(), 15)
pump(0.3)
car.update()
check("fan control returned to the ECU", not car.engine.ios[0x4001].controlled, sp.status.text())
shot(wb, "fan")

# ============================================================================ clear ONE fault after the repair
check("select clear fault page", sp.select("fault"))
sp.f_ecu.setCurrentIndex(sp.f_ecu.findData("engine"))
sp.read_faults()
listed = " ".join(sp.f_list.item(i).text() for i in range(sp.f_list.count()))
check("engine faults listed in the service tab", "P0171" in listed and "P0301" in listed, listed)
sp.f_code.setText("P0171")
sp.show_fault("P0171")
ft = sp.f_text.toPlainText()
check("explanation + causes shown before clearing", lang_ok(ft, "cause") and "P0171" in ft, ft[:300])
n = len(MSGS)
sp.b_run.click()
pump(0.3)
check("not cleared before the repair is confirmed", len(MSGS) > n and any(d.code >> 8 == 0x0171 and d.visible
                                                                         for d in car.engine.dtcs))
sp.f_repaired.setChecked(True)
sp.b_run.click()
wait(lambda: (sp.worker is None or not sp.worker.is_alive()) and sp.b_run.isEnabled(), 20)
pump(0.5)
check("P0171 cleared in the car, P0301 kept", not any(d.code >> 8 == 0x0171 and d.visible for d in car.engine.dtcs)
      and any(d.code >> 8 == 0x0301 for d in car.engine.dtcs), sp.status.text())
shot(wb, "clear_one")
wb.tabs.setCurrentIndex(wb.tab_index("Faults"))
wait(lambda: wb._busy_n == 0, 10)
wb.read_codes()
wait(lambda: wb._busy_n == 0, 20)
pump(0.3)
codes = [wb.dtc_tree.topLevelItem(i).text(0) for i in range(wb.dtc_tree.topLevelItemCount())]
check("Faults tab: P0171 gone, P0301 still there", "P0171" not in codes and "P0301" in codes, codes)

# ============================================================================ readiness
wb.read_readiness()
wait(lambda: wb._busy_n == 0 and wb.ready_table.rowCount() > 0, 15)
wb.tabs.setCurrentIndex(wb.tab_index("Readiness"))
check("readiness monitors listed and explained", wb.ready_table.rowCount() >= 5 and len(wb.ready_view.toPlainText()) > 100,
      wb.ready_table.rowCount())
check("readiness summary in the UI language", lang_ok(wb.ready_summary.text(), "ready"), wb.ready_summary.text())
shot(wb, "readiness")

# ============================================================================ report
rep = Path(qh.WORK) / f"e2e_{TAG}_report.html"
ok = hasattr(wb, "save_report") and wb.save_report(str(rep))
txt = rep.read_text(encoding="utf-8") if rep.exists() else ""
check("diagnosis report saved (HTML)", ok and rep.exists(), rep)
check("report: VIN, codes with explanations, freeze frame, readiness, live values",
      car.vin in txt and "P0301" in txt and "C0035" in txt and "812" in txt and txt.count("<tr") > 10, txt[:300])
check("report in the UI language (rtl for Arabic)", ('dir="rtl"' in txt) == AR and lang_ok(txt, "Readiness"))

# ============================================================================ excluded functions
from radide.cardiag.service import definitions as D  # noqa: E402
bad = [name for name in ("Immobilizer key learning", "Odometer correction", "EGR delete", "Security access brute force",
                         "Readiness monitor faking", "DPF removal", "Mask P0420", "برمجة المفاتيح", "تعديل العداد")
       if not D.policy_problems({"routines": [{"id": "x", "name": name, "ecu": "engine"}]})]
check("policy filter refuses immobiliser / odometer / emissions-masking / brute-force definitions", not bad, bad)
allowed = [name for name in ("Cooling system bleed", "DPF service regeneration", "Oil service interval reset",
                             "Clear P0420 after repair") if D.policy_problems({"routines": [{"id": "x", "name": name}]})]
check("normal service routines are allowed", not allowed, allowed)
src = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in (REPO / "radide" / "cardiag").rglob("*.py")
                if "kb" not in p.parts)
hits = [m for m in re.findall(r"def\s+(\w*(?:immo|odometer_write|set_odometer|crack|brute|bypass|mask_monitor)\w*)", src, re.I)]
check("no immobiliser / odometer / cracking / masking functions in the code", not hits, hits)
from radide.cardiag.link.uds import UdsClient  # noqa: E402
check("UDS client has no built-in seed/key algorithm", not any(n for n in dir(UdsClient) if "algorithm" in n.lower()
                                                                or n.lower().startswith("compute_key")))

if AR:
    from radide import i18n
    mine = re.compile(r"Car's Lights|Diagnosis Report|Scan All|all control units|Read from the car|lamp")
    miss = [s for s in i18n.missing() if mine.search(s)]
    check("no untranslated strings seen for the new features", not miss, miss[:10])
    acts = {a.objectName(): i18n.shown(a) for m in [a.menu() for a in w.menuBar().actions() if a.menu()]
            for a in m.actions() if a.objectName() in ("CarDiagScanAction", "CarDiagServiceAction", "CarFaultGuideAction")}
    check("Tools menu: car diagnostics items in Arabic", len(acts) == 3 and all(ARABIC.search(t) for t in acts.values()),
          acts)
    check("Scan All / Save Report / Read the Car's Lights buttons in Arabic",
          all(ARABIC.search(i18n.shown(b)) for b in (wb.b_scan_all, wb.b_report, g.l_read)),
          [i18n.shown(b) for b in (wb.b_scan_all, wb.b_report, g.l_read)])
wb.tabs.setCurrentIndex(wb.tab_index("Faults"))
shot(w, "ide")
wb.disconnect()
finish(w)
