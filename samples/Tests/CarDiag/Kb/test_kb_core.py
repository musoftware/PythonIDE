"""Fault knowledge base (radide/cardiag/kb) - no hardware, no IDE window.

Run:  .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\Kb\\test_kb_core.py

1. shard schema (every entry valid, English + Arabic everywhere), coverage counts, shards up to date with the build
2. lookup: generic codes, UDS failure-type byte, manufacturer-specific fallback, unknown generic fallback, packs
3. search in English and Arabic (incl. Egyptian colloquial symptom words), code prefixes, filters
4. warning lights: icons are valid SVG, picker -> likely codes, combinations, non-OBD modules
5. symptom wizard: data consistency, answers change the ranking, PIDs to watch
6. "Explain with AI": prompt building (grounding, safety, scope rules, Arabic), offline explanation, mock provider
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["RADIDE_CARDIAG_HOME"] = tempfile.mkdtemp(prefix="cardiag-kb-")

from radide.cardiag import kb  # noqa: E402
from radide.cardiag.kb import ai as kbai  # noqa: E402
from radide.cardiag.kb import lights as L  # noqa: E402
from radide.cardiag.kb import symptoms as S  # noqa: E402
from radide.cardiag.kb import vocab  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def top(q, n=5, **kw):
    return [c for c, _s in kb.search(q, **kw)[:n]]


# ------------------------------------------------------------------------------------------- 1. schema / coverage
errs = kb.validate()
check("every shard entry is valid (schema, Arabic, vocab ids)", not errs, errs[:10])
st = kb.stats()
bp = st["by_prefix"]
check("coverage: > 1000 generic codes", st["total"] > 1000, st["total"])
check("coverage: P0 >= 800", bp.get("P0", 0) >= 800, bp)
check("coverage: P2 >= 200", bp.get("P2", 0) >= 200, bp)
check("coverage: P34 cylinder deactivation >= 90", bp.get("P34", 0) >= 90, bp)
check("coverage: U0 / B0 / C0 present", bp.get("U0", 0) >= 20 and bp.get("B0", 0) >= 4 and bp.get("C0", 0) >= 10, bp)
check("all three severities used", all(st["by_severity"].get(s, 0) for s in kb.SEVERITIES), st["by_severity"])
check("safety-relevant codes flagged", st["safety"] >= 30, st["safety"])
check("no manufacturer-specific codes shipped as facts",
      not [c for c in kb.codes() if kb.manufacturer_specific(c)])
for sh in kb.SHARDS:
    d = json.loads((kb.DATA / f"{sh}.json").read_text(encoding="utf-8"))
    used = {t for e in d["codes"].values() for t in e["causes"] + e["checks"]}
    if not check(f"shard {sh}: every text id resolves", used <= set(d["texts"]), used - set(d["texts"])):
        break
r = subprocess.run([sys.executable, "-m", "radide.cardiag.kb.builder", "--check"], cwd=ROOT, capture_output=True,
                   text=True, encoding="utf-8", errors="replace")
check("shards on disk match the build sources (build --check)", r.returncode == 0, (r.stdout + r.stderr)[-400:])
red_yes = [c for c in kb.codes() if kb.lookup(c)["severity"] == "red" and kb.lookup(c)["drive"] == "yes"]
check("no red code says 'safe to drive'", not red_yes, red_yes[:5])

# ------------------------------------------------------------------------------------------- 2. lookup
i = kb.lookup("p0217")
check("lookup P0217 (case-insensitive): SAE title", i and "Coolant Over Temperature" in i["title"], i and i["title"])
check("P0217: Arabic title / explanation", i["title_ar"] and any("؀" <= ch <= "ۿ" for ch in i["explain_ar"]))
check("P0217: red, do not drive, safety-relevant", i["severity"] == "red" and i["drive"] == "no" and i["safety"])
check("P0217: ranked causes + step-by-step checks in both languages",
      len(i["causes"]) >= 3 and len(i["causes"]) == len(i["causes_ar"]) and len(i["checks"]) >= 3)
check("P0217: system cooling, live PIDs incl. coolant temperature", i["system"] == "cooling" and 0x05 in i["pids"])
check("P0217: related codes", i["related"] and all(kb.normalize_code(x) for x in i["related"]))
i = kb.lookup("P0420")
check("P0420: catalyst readiness monitor", i["monitor"] == "catalyst" and i["monitor_name_ar"], i["monitor"])
i = kb.lookup("C0035-1F")
check("UDS DTC with failure-type byte: base code + failure type",
      i["base"] == "C0035" and i["ftb"] == 0x1F and i["ftb_text"][0] and i["ftb_text"][1], i and i["ftb_text"])
check("normalize: 'C0035 1F' / 'c00351f'", kb.normalize_code("C0035 1F") == ("C0035", 0x1F)
      and kb.normalize_code("c00351f") == ("C0035", 0x1F))
check("not a DTC -> None", kb.lookup("hello") is None and kb.lookup("P9") is None)
i = kb.lookup("P1234")
check("manufacturer-specific fallback (P1234)", i["specific"] and not i["known"]
      and "meaning varies" in i["title"] and "يختلف" in i["title_ar"], i["title"])
check("manufacturer ranges: P30xx / B1 / C2 / U1", all(kb.lookup(c)["specific"] for c in ("P3050", "B1342", "C2100", "U1000")))
i = kb.lookup("P0BFF")
check("unknown generic code -> group fallback", i and not i["known"] and not i["specific"], i)
check("describe() one line", kb.describe("P0300").startswith("P0300 - ") and "ا" in kb.describe("P0300", "ar"))

# packs
csv_text = ("code,make,title,title_ar,explain,explain_ar,causes,causes_ar,severity,drive,system,tags\n"
            "P1234,DemoMake,Demo pump circuit,دائرة الطلمبة التجريبية,Demo explanation,شرح تجريبي,"
            "Cause A|Cause B,السبب أ|السبب ب,amber,caution,fuel-air,low-power\n"
            "B1342,DemoMake,ECU is defective,الوحدة تالفة,Demo,تجريبي,,,,,,\n")
p = Path(tempfile.mkdtemp()) / "demo_make.csv"
p.write_text(csv_text, encoding="utf-8")
pack = kb.import_pack(p, make="DemoMake")
check("import CSV pack (2 codes)", len(pack["codes"]) == 2 and pack["name"] == "demo_make")
i = kb.lookup("P1234", make="DemoMake")
check("pack entry used for the manufacturer code", i["known"] and i["title"] == "Demo pump circuit"
      and i["causes_ar"] == ["السبب أ", "السبب ب"] and i["source"] == "pack:demo_make", i)
check("pack codes are searchable", "P1234" in top("Demo pump"), kb.search("Demo pump"))
check("pack cannot override a generic code", kb.lookup("P0217")["source"] != "pack:demo_make")
bad = Path(p.parent) / "bad.json"
bad.write_text(json.dumps({"format": "radide-cardiag-dtc-pack", "codes": {"XYZ": {"title": ["a", "b"]}}}), "utf-8")
try:
    kb.import_pack(bad)
    check("invalid pack rejected", False)
except ValueError as e:
    check("invalid pack rejected with the problems listed", "XYZ" in str(e), e)
jp = Path(p.parent) / "j.json"
jp.write_text(json.dumps({"format": "radide-cardiag-dtc-pack", "name": "jpack", "make": "M2", "codes": {
    "U1000": {"title": ["Class 2 network", "شبكة الفئة 2"], "explain": ["x", "س"], "severity": "amber"}}},
    ensure_ascii=False), "utf-8")
kb.import_pack(jp)
check("import JSON pack", kb.lookup("U1000", "M2")["title"] == "Class 2 network")
check("stats list the packs", {n for n, _m, _c in kb.stats()["packs"]} == {"demo_make", "jpack"})
check("remove pack", kb.remove_pack("jpack") and not kb.lookup("U1000")["known"])
kb.remove_pack("demo_make")

# ------------------------------------------------------------------------------------------- 3. search
check("search code: exact first", top("P0171")[0] == "P0171")
check("search code prefix 'P030' -> misfire codes", set(top("P030", 20)) >= {"P0300", "P0301", "P0305"})
check("search 'overheating' -> P0217 near the top", "P0217" in top("overheating"), top("overheating"))
check("search Egyptian 'سخونية' -> P0217", "P0217" in top("سخونية"), top("سخونية"))
check("search 'الموتور بيسخن' -> cooling codes", any(kb.lookup(c)["system"] == "cooling" for c in top("الموتور بيسخن")),
      top("الموتور بيسخن"))
check("search 'misfire cylinder 3' -> P0303", "P0303" in top("misfire cylinder 3", 5), top("misfire cylinder 3"))
check("search 'بترج' (shakes) -> rough-idle / shaking codes",
      top("بترج", 10) and all({"rough-idle", "shaking", "misfire"} & set(kb.lookup(c)["tags"]) for c in top("بترج", 10)),
      top("بترج", 10))
check("search 'oxygen sensor heater' -> O2 heater codes", any(c in top("oxygen sensor heater", 10)
                                                               for c in ("P0030", "P0135", "P0036", "P0141")),
      top("oxygen sensor heater", 10))
check("search Arabic title words 'حساس الأكسجين'", any(kb.lookup(c)["system"] in ("emissions", "fuel-air")
                                                       for c in top("حساس الأكسجين")), top("حساس الأكسجين"))
check("search 'مش بتدور' (won't start)", len(top("مش بتدور", 10)) >= 3, top("مش بتدور"))
check("search 'battery light' -> charging", any(kb.lookup(c)["system"] == "charging" for c in top("battery light")),
      top("battery light"))
check("filter by system + severity", all(kb.lookup(c)["system"] == "cooling" and kb.lookup(c)["severity"] == "red"
                                         for c in top("", 50, system="cooling", severity="red"))
      and top("", 50, system="cooling", severity="red"))
check("symptom_tags: Arabic + English", "overheating" in kb.symptom_tags("العربية بتسخن")
      and "no-start" in kb.symptom_tags("car won't start"))
check("vocab: every tag has English + Arabic names and words", all(len(v) == 3 and v[1] and v[2]
                                                                    for v in vocab.TAGS.values()))

# ------------------------------------------------------------------------------------------- 4. warning lights
check("at least 18 warning lights", len(L.LIGHTS) >= 18, len(L.LIGHTS))
need = {"mil", "oil", "coolant", "battery", "abs", "airbag", "brake", "tpms", "esp", "glow", "dpf", "eps", "service"}
check("the required lights exist", need <= set(L.LIGHTS), need - set(L.LIGHTS))
bad_svg = []
for lid in L.ids():
    try:
        xml.dom.minidom.parseString(L.svg(lid, "red"))
    except Exception as e:  # noqa: BLE001
        bad_svg.append((lid, str(e)))
check("every icon is well-formed SVG and coloured", not bad_svg and "#d33a2c" in L.svg("oil", "red"), bad_svg)
check("every light: Arabic name, meaning and advice for each colour",
      all(l.name[1] and l.meaning[1] and all(c in l.do_now and l.do_now[c][1] for c in l.colours)
          for l in L.LIGHTS.values()))
check("every light (but service / TPMS) maps to known codes",
      all(any(c in set(kb.codes()) for c in l.codes) for l in L.LIGHTS.values() if l.id not in ("service", "tpms")))
r = L.pick(["coolant"])
check("picker: coolant -> P0217 first, stop", r["codes"][0][0] == "P0217" and r["stop"] and 0x05 in r["pids"], r["codes"][:3])
r = L.pick(["mil"], {"mil": "flashing"}, lang="ar")
check("picker: flashing MIL -> misfire, stop, Arabic advice", r["stop"] and r["codes"][0][0] == "P0300"
      and "تومض" in r["advice"][0], r["codes"][:3])
r = L.pick(["battery", "coolant"], lang="ar")
check("picker: battery + coolant -> belt hint (Arabic)", r["combos"] and "السير" in r["combos"][0])
r = L.pick(["abs"])
check("picker: ABS -> wheel-speed codes, needs the ABS unit", r["codes"][0][0].startswith("C00")
      and not r["scan"]["obd"] and r["scan"]["modules"], r)
r = L.pick(["mil"], present=["P0171"])
check("picker: codes the car reported come first", r["codes"][0][0] == "P0171")
check("find light by words (Arabic / English)", L.find("لمبه الزيت") == ["oil"] and "mil" in L.find("check engine"))

# ------------------------------------------------------------------------------------------- 5. symptoms
check("wizard data consistent", not S.validate(), S.validate())
check("at least 10 symptoms", len(S.SYMPTOMS) >= 10)
r0 = S.evaluate("overheating", {})
r1 = S.evaluate("overheating", {"when": "idle", "fan": "no"}, lang="ar")
check("overheating: no answers -> coolant first", r0["causes"][0]["id"] == "coolant-low", r0["causes"][:2])
check("overheating at idle + fan not running -> fan first (Arabic)", r1["causes"][0]["id"] == "fan"
      and "مروحة" in r1["causes"][0]["name"], r1["causes"][:2])
check("overheating: watch coolant temperature, P0217 among the codes, stop flag",
      r1["pids"][0] == 0x05 and "P0217" in [c for c, _t in r1["codes"][:5]] and r1["stop"], (r1["pids"], r1["codes"][:5]))
r = S.evaluate("smoke", {"colour": "white"})
check("white sweet smoke -> head gasket + note", r["causes"][0]["id"] == "head-gasket" and r["notes"])
r = S.evaluate("no-start", {"key": "yes"})
check("security light flashing -> key not recognised (no bypass advice)", r["causes"][0]["id"] == "immobiliser"
      and "bypass" not in r["causes"][0]["check"].lower())
r = S.evaluate("battery-light", {"temp": "yes"})
check("battery light + temperature rising -> stop (belt)", r["stop"] and r["causes"][0]["id"] == "water-pump")
check("match free text", S.match("الموتور بيسخن") == ["overheating"] and "no-start" in S.match("won't start"))
check("percentages add up to ~100", 95 <= sum(c["percent"] for c in S.evaluate("rough-idle", {}, limit=20)["causes"]) <= 105)

# ------------------------------------------------------------------------------------------- 6. AI
ctx = kbai.Context(dtcs=["P0217", {"code": "P1234", "ecu": "7E8", "kinds": ["stored"]}],
                   freeze=[{"dtc": "P0217", "values": [("Coolant temperature", 118, "°C"), ("Engine speed", 820, "rpm")]}],
                   live=[("Coolant temperature", 112.5, "°C")], vehicle={"vin": "WDB0000000TEST001", "year": 2014},
                   lights=["coolant"], symptoms=["overheating"], question="هل ينفع أسوق للشغل؟")
system, user = kbai.build_prompt(ctx, "ar")
check("prompt: Arabic answer requested", "Arabic" in system and "Egyptian" in system)
check("prompt: safety + uncertainty + scope rules", all(w in system for w in ("Safety first", "how sure",
                                                                              "immobiliser", "odometer", "DPF")))
check("prompt: KB grounding for P0217 (title, causes, severity)", "Engine Coolant Over Temperature" in user
      and "common causes" in user and "SAFETY-RELEVANT" in user)
check("prompt: manufacturer-specific code flagged, not guessed", "P1234" in user and "meaning varies" in user)
check("prompt: freeze frame, live data, VIN, light, symptom, question",
      all(s in user for s in ("Freeze frame", "118 °C", "112.5 °C", "WDB0000000TEST001", "Warning light on",
                              "Symptom reported", "هل ينفع")), user)
system_en, _u = kbai.build_prompt(ctx, "en")
check("prompt: English answer when asked", "Answer in English" in system_en)
off = kbai.offline_explanation(ctx, "ar")
check("offline explanation (no AI): Arabic, safety first, clear-after-repair note",
      off.startswith("تنبيه سلامة") and "P0217" in off and "بعد الإصلاح" in off, off[:200])
check("offline explanation English", "Likely causes" in kbai.offline_explanation(ctx, "en"))

from radide import ai  # noqa: E402


class MockProvider(ai.Provider):
    id = "mock-cardiag"
    name = "Mock"
    kind = "api"
    fallback_default = "mock-1"
    seen: list = []

    def _run_chat(self, job, system, messages, model, opts):
        MockProvider.seen.append((system, [m.content for m in messages], model))
        job.emit_delta("السبب الأرجح: ")
        job.emit_delta("المروحة لا تعمل.")
        return "السبب الأرجح: المروحة لا تعمل."


job = kbai.ask(ctx, "ar", provider=MockProvider())
text = ai.run_sync(job, timeout=10)
check("ask(): mock provider gets the system prompt + the data", MockProvider.seen
      and "Safety first" in MockProvider.seen[0][0] and "P0217" in MockProvider.seen[0][1][0], MockProvider.seen[:1])
check("ask(): Arabic answer streamed back", text == "السبب الأرجح: المروحة لا تعمل.", text)

ok = sum(1 for _, c_ in RESULTS if c_)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c_ in RESULTS if not c_] or 'none'}", flush=True)
os._exit(0 if ok == len(RESULTS) else 1)
