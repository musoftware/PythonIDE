"""IDE test of Tools > Car Fault Guide (fault codes, warning lights, symptoms, explain with AI), English then Arabic.

Run:  set RADIDE_NO_BROWSER=1 & .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\Kb\\qa_help_ide.py
"""
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ["RADIDE_CARDIAG_HOME"] = tempfile.mkdtemp(prefix="cardiag-kb-ide-")
os.environ.setdefault("QA_NAME", "cardiag-guide")
sys.path.insert(0, str(HERE.parents[1] / "QA" / "Integration"))
import qh  # noqa: E402
from qh import check, pump, wait, shot, finish, MSGS  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from radide import ai  # noqa: E402


class MockProvider(ai.Provider):
    id = "mock-cardiag-ide"
    name = "Mock"
    fallback_default = "mock-1"
    prompts: list = []

    def _run_chat(self, job, system, messages, model, opts):
        MockProvider.prompts.append((system, messages[-1].content))
        job.emit_delta("الخلاصة: ")
        return "الخلاصة: المروحة لا تعمل غالبًا - افحص الفيوز والريلاي."


w = qh.window()
act = next((a for m in [a.menu() for a in w.menuBar().actions() if a.menu()] for a in m.actions()
            if a.objectName() == "CarFaultGuideAction"), None)
check("Tools > Car Fault Guide action", act is not None)
act.trigger()
pump(0.5)
feat = w.cardiag_guide
g = feat.guide
check("guide tab opened with 4 tabs", g is not None and g.tabs.count() == 4, g and g.tabs.count())
check("coverage label shows > 1000 codes", re.search(r"\d{4}", g.cov.text()) is not None, g.cov.text())

# ---- fault codes
g.q.setText("overheating")
g._qtimer.stop()
res = g.search("overheating")
codes = [g.results.topLevelItem(i).text(0) for i in range(min(8, g.results.topLevelItemCount()))]
check("search 'overheating' lists P0217", "P0217" in codes, codes)
g.show_code("P0217")
html = g.detail.toPlainText()
check("P0217 page: title, safe to drive, causes, checks", all(s in html for s in ("Coolant Over Temperature", "Safe to drive",
                                                                                 "Common causes", "What to check")), html[:400])
g.show_code("C0035-1F")
check("UDS DTC with failure type explained", "Failure type" in g.detail.toPlainText(), g.detail.toPlainText()[:300])
g.show_code("P1234")
check("manufacturer-specific fallback shown", "meaning varies" in g.detail.toPlainText())
csv = Path(tempfile.mkdtemp()) / "demo_make.csv"
csv.write_text("code,make,title,title_ar,explain,explain_ar\nP1234,Demo,Demo pump relay,ريلاي الطلمبة التجريبي,"
               "Demo text,نص تجريبي\n", encoding="utf-8")
pack = g.import_pack(str(csv))
g.show_code("P1234")
check("manufacturer pack imported and used", pack and "Demo pump relay" in g.detail.toPlainText(), g.detail.toPlainText()[:200])
g.q.setText("")
g._qtimer.stop()
g.f_sys.setCurrentIndex(g.f_sys.findData("cooling"))
g.f_sev.setCurrentIndex(g.f_sev.findData("red"))
n = g.results.topLevelItemCount()
check("filters (cooling + red) narrow the list", 0 < n < 20, n)
g.f_sys.setCurrentIndex(0)
g.f_sev.setCurrentIndex(0)
shot(g, "guide_codes_en")

# ---- warning lights
check("warning-light buttons with icons", len(g._light_buttons) >= 18
      and not g._light_buttons["mil"].icon().isNull())
r = g.select_lights(["battery", "coolant"])
txt = g.l_view.toPlainText()
check("lights battery + coolant -> stop, belt hint, P0217", r["stop"] and "belt" in txt and "P0217" in txt, txt[:500])
r = g.select_lights(["abs"])
check("ABS light -> wheel-speed codes, ABS unit named", r["codes"][0][0].startswith("C00") and "ABS" in g.l_view.toPlainText())
r = g.select_lights(["mil"], flashing=True)
check("flashing MIL -> P0300 first", r["codes"][0][0] == "P0300", r["codes"][:3])
shot(g, "guide_lights_en")

# ---- symptoms
g.select_symptom("overheating")
check("symptom questions built", g.s_qlay.count() >= 4, g.s_qlay.count())
g.answer("when", "idle")
r = g.answer("fan", "no")
check("answers -> fan first, coolant temperature to watch", r["causes"][0]["id"] == "fan" and r["pids"][0] == 5, r["causes"][:2])
from PyQt6.QtWidgets import QRadioButton  # noqa: E402
rb = g.findChild(QRadioButton, "CarGuideA_fan_no")
check("radio buttons reflect the answers", rb is not None and rb.isChecked())
found = g.find_symptom("بترج وهي واقفة")
check("free-text symptom (Arabic) -> rough idle", found and found[0] == "rough-idle", found)
pump(0.3)
shot(g, "guide_symptoms_en")

# ---- explain with AI (mock provider) + offline
g.provider = MockProvider()
g.ai_codes.setText("P0217, P0128")
g.ai_symptoms = ["overheating"]
off = g.explain_offline()
check("offline explanation (Arabic default)", "P0217" in off and "الأسباب المحتملة" in off, off[:200])
job = g.ask_ai()
check("AI job started", job is not None)
wait(lambda: g._job is None, 15)
check("AI answer shown (Arabic)", "المروحة لا تعمل" in g.ai_out.toPlainText(), g.ai_out.toPlainText()[:300])
check("AI prompt has KB grounding + Arabic instruction", MockProvider.prompts
      and "Arabic" in MockProvider.prompts[-1][0] and "Engine Coolant Over Temperature" in MockProvider.prompts[-1][1])
shot(g, "guide_ai_en")

# ---- the scan tool: Guide tab, use the car's data, watch live data
scan = w.cardiag_scan
wb = scan.open(demo=True)
wait(lambda: wb.client is not None, 15)
check("scan workbench has the Guide tab", getattr(wb, "guide", None) is not None and wb.tab_index("Guide") >= 0)
wb.read_codes()
wait(lambda: bool(wb.entries), 15)
wb.read_freeze()
wait(lambda: bool(wb.freeze), 15)
gg = wb.guide
check("use the car's data -> codes + freeze frame", gg.use_car_data() and gg.ai_codes.text() and gg.ai_freeze,
      (gg.ai_codes.text(), len(gg.ai_freeze)))
ctx = gg.context()
check("context carries the ECU / status of the car's codes", any(isinstance(d, dict) and d["ecu"] for d in ctx.dtcs), ctx.dtcs)
wait(lambda: wb.pid_tree.topLevelItemCount() > 0, 15)
ok = gg.watch([0x05, 0x0C])
keys = [k[1] for k in wb._live_keys]
check("watch in Live Data selects the PIDs", ok and 0x05 in keys and 0x0C in keys, keys)
gg.select_lights(["coolant"])
check("lights picker marks codes reported by the car", "P0217" not in [e.code for e in wb.entries]
      or "reported by the car" in gg.l_view.toPlainText())
shot(wb, "guide_in_scan_en")

# service slice hook
g2 = feat.show_code("P0300")
check("win.cardiag_guide.show_code (used by the service functions)", g2.results.topLevelItem(0).text(0) == "P0300")

# ---- Arabic
from radide import i18n  # noqa: E402
i18n.set_language(qh.app, "ar")
pump(1.0)
check("Arabic: light names", g._light_buttons["oil"].text() == "ضغط الزيت", g._light_buttons["oil"].text())
check("Arabic: symptom list", g.s_list.item(0).text() == "المحرك يسخن (سخونية)", g.s_list.item(0).text())
g.show_code("P0217")
check("Arabic: code page", "حالة ارتفاع حرارة سائل التبريد" in g.detail.toPlainText()
      and "هل القيادة آمنة" in g.detail.toPlainText(), g.detail.toPlainText()[:300])
g.q.setText("مش بتدور")
g._qtimer.stop()
res = g.search("مش بتدور")
check("Arabic: filters and coverage translated", g.f_sev.itemText(0) == "أي خطورة" and "قاعدة المعارف" in g.cov.text(),
      (g.f_sev.itemText(0), g.cov.text()))
check("Arabic colloquial search 'مش بتدور'", len(res) >= 3)
g.select_lights(["coolant"])
check("Arabic: light advice", "لا تفتح غطاء الردياتير" in g.l_view.toPlainText())
g.select_symptom("no-start")
check("Arabic: wizard questions", any("المفتاح" in (g.s_qlay.itemAt(i).widget().title() if g.s_qlay.itemAt(i).widget() else "")
                                      for i in range(g.s_qlay.count())))
mine = re.compile(r"Fault Codes|Warning Lights|Symptoms|Explain with AI|Watch in Live Data|Scan the Car|Use the Car|"
                  r"Ask AI|Knowledge base|Import Manufacturer|Answer language|Likely|light is|Car Fault Guide")
miss = [s for s in i18n.missing() if mine.search(s)]
check("Arabic: no untranslated guide strings", not miss, miss[:10])
pump(0.3)
shot(g, "guide_symptoms_ar")
g.tabs.setCurrentIndex(1)
shot(g, "guide_lights_ar")
g.tabs.setCurrentIndex(0)
shot(g, "guide_codes_ar")
i18n.set_language(qh.app, "en")
pump(0.5)
check("no unexpected warnings", not [m for m in MSGS if m[0] in ("warning", "critical")], MSGS)
finish(w)
