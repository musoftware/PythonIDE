"""Core tests of the car-diagnostics service functions against the Demo car simulator (no Qt, no hardware).

Run:  .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\Service\\test_service_core.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
os.environ["RADIDE_CARDIAG_HOME"] = tempfile.mkdtemp(prefix="cardiag-svc-")

from radide.cardiag.service import definitions as D, demo_session  # noqa: E402
from radide.cardiag.service.adaptation import AdaptationWriter  # noqa: E402
from radide.cardiag.service.demo_ecu import SimClock  # noqa: E402
from radide.cardiag.service.dtc import ClearFaultFlow, parse_code, code_bytes, safety_topics  # noqa: E402
from radide.cardiag.service.iocontrol import ActuatorTest  # noqa: E402
from radide.cardiag.service.profiles import get_or_create, vin_valid  # noqa: E402
from radide.cardiag.service.runner import RoutineRunner  # noqa: E402
from radide.cardiag.service.security import load_plugin  # noqa: E402

RESULTS = []
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)


def session(**k):
    clk = SimClock()
    prof = get_or_create("RADDEM0CAR0000001")
    car, client, pack = demo_session(clock=clk, sleep=clk.sleep, audit=prof.audit, **k)
    return clk, car, client, pack, prof


events = []
emit = events.append

# ------------------------------------------------------------------ definitions
pack = D.demo_pack()
check("demo pack loads", pack["name"] and len(pack["routines"]) == 5 and len(pack["io_controls"]) == 2)
tpl, _, _ = D.normalize(json.loads(D.template_text()))
_, errs, _ = D.normalize(json.loads(D.template_text()))
check("template validates", not errs, [e.en for e in errs])
bad = json.loads(D.template_text())
bad["routines"][0]["name"] = "Immobilizer off"
_, errs, _ = D.normalize(bad)
check("policy: immobiliser rejected", any("immobiliser" in e.en for e in errs), [e.en for e in errs])
for txt, want in [("Odometer correction", "odometer"), ("DPF delete", "emissions defeat"), ("EGR off", "emissions defeat"),
                  ("AdBlue removal", "emissions defeat"), ("إلغاء الـ EGR", None), ("تعديل عداد المسافات", "odometer"),
                  ("Key programming", "key / PIN"), ("Fake readiness", "readiness faking"),
                  ("DPF service regeneration", None), ("Oil service km reset", None), ("EGR valve test", None),
                  ("Cooling fan test", None), ("Disable DTC P0420", "fault masking"), ("إلغاء DPF", "emissions defeat"),
                  ("تصفير عداد الصيانة", None), ("Mileage reset", "odometer")]:
    got = D.policy_reason(txt)
    if want is None and txt.startswith("إلغاء"):
        want = "emissions defeat"
    check(f"policy: {txt!r} -> {want}", got == want, got)
bad = json.loads(D.template_text())
bad["io_controls"][0]["did"] = "XYZ"
bad["routines"][0]["ecu"] = "nope"
bad["routines"][0]["preconditions"][1]["check"]["did"] = "1234"
_, errs, _ = D.normalize(bad)
check("validation catches bad DID / ECU / precondition DID", len(errs) >= 3, [e.en for e in errs])
check("validation errors are bilingual", all(e.ar for e in errs))
csv_text = ("kind,id,name,name_ar,category,ecu,tx,rx,session,identifier,data,timeout_s,preconditions,preconditions_ar\n"
            "routine,bleed,Coolant bleed,تنفيس التبريد,cooling,engine,7E0,7E8,extended,0203,01,60,Engine off|Cold,المحرك متوقف|بارد\n"
            "io,fan,Fan test,اختبار المروحة,actuator,engine,7E0,7E8,extended,F0A0,Off=00;Full=64,20,,\n"
            "adaptation,svc,Service reset,تصفير الصيانة,service,engine,7E0,7E8,extended,F1A0,000000,,,\n")
cp, _ = D.pack_from_csv(csv_text, "csv test")
check("CSV import", len(cp["routines"]) == 1 and cp["io_controls"][0]["states"][1]["value"] == "64"
      and cp["routines"][0]["preconditions"][1]["text_ar"] == "بارد", cp)
try:
    D.pack_from_csv(csv_text.replace("Coolant bleed", "Odometer reset"), "x")
    check("CSV import applies the policy", False)
except D.PackError as e:
    check("CSV import applies the policy", "odometer" in str(e), e)
p = Path(os.environ["RADIDE_CARDIAG_HOME"]) / "in.json"
p.write_text(D.template_text(), encoding="utf-8")
ip, dest, _ = D.import_pack(p)
check("import copies the pack", dest.is_file() and D.user_packs()[0][0] is not None)

# ------------------------------------------------------------------ routine: cooling bleed to completion
clk, car, client, pack, prof = session()
r = D.find(pack, "routines", "cooling_bleed")
events.clear()
res = RoutineRunner(client, pack, emit=emit).run(r, confirmed=[3, 4])
progs = [e.progress for e in events if e.kind == "progress"]
check("bleed completes", res.ok, res.status.en)
check("bleed reports rising progress to 100", progs and progs[-1] == 100 and progs == sorted(progs) and len(progs) >= 10, progs)
check("bleed shows instructions", sum(1 for e in events if e.kind == "instruction") == 3)
check("bleed interprets result bytes", res.values and res.values[0][1] == "0 %", res.values)
check("response pending handled", any(e.get("note") == "response pending" for e in prof.audit_entries()))
check("back to default session afterwards", car.engine.session == 1)
# missing confirmation
res = RoutineRunner(client, pack).run(r, confirmed=[3])
check("unconfirmed precondition blocks start", not res.ok and res.error.code == "preconditions", res.status.en)
# warm engine: automatic check
car.coolant_c = 85
res = RoutineRunner(client, pack).run(r, confirmed=[3, 4])
check("automatic precondition check (coolant 85 C) blocks", not res.ok and "Coolant" in res.status.en
      and "85" in res.status.en, res.status.en)
# the ECU refuses: NRC 0x22 shown in Arabic
res = RoutineRunner(client, pack).run(r, confirmed=[3, 4], enforce_checks=False)
check("NRC 0x22 from the ECU", not res.ok and getattr(res.error, "nrc", None) == 0x22, res.status.en)
check("NRC 0x22 explained in Arabic", "شروط السيارة" in res.status.get("ar") and "0x22" in res.status.get("ar"),
      res.status.get("ar"))
# engine running -> NRC 0x83
car.coolant_c, car.engine_running = 20, True
res = RoutineRunner(client, pack).run(r, confirmed=[3, 4], enforce_checks=False)
check("NRC 0x83 engine running in Arabic", getattr(res.error, "nrc", 0) == 0x83 and "متوقفًا" in res.status.get("ar"))
car.engine_running = False
# timeout: ECU stops answering results
car.stall_results = True
r2 = json.loads(json.dumps(r)); r2["poll"]["timeout_s"] = 10
res = RoutineRunner(client, pack).run(r2, confirmed=[3, 4])
check("timeout detected", not res.ok and res.error.code == "timeout", res.status.en)
check("timeout message in Arabic", "المهلة" in res.status.get("ar"))
check("routine stopped after timeout", any(e.get("note") == "stop routine" for e in prof.audit_entries()))
car.stall_results = False
# cancel mid-way stops the routine
clk, car, client, pack, prof = session()
n = {"i": 0}


def cancel_after(e):
    if e.kind == "progress":
        n["i"] += 1
        if n["i"] == 3:
            client.cancelled = True


res = RoutineRunner(client, pack, emit=cancel_after).run(r, confirmed=[3, 4])
check("cancel stops the routine", not res.ok and res.error.code == "cancelled" and car.engine._bleed_state()[0] == 3)
client.cancelled = False
# warming during bleed -> ECU aborts -> failed status
clk, car, client, pack, prof = session()


def warm(e):
    if e.kind == "progress" and e.progress >= 30:
        car.coolant_c = 60


res = RoutineRunner(client, pack, emit=warm).run(r, confirmed=[3, 4])
check("routine 'failed' status interpreted", not res.ok and res.error.code == "routine_failed" and "aborted" in res.status.en,
      res.status.en)
# one-shot routines
clk, car, client, pack, prof = session()
car.engine.throttle_learned = False
res = RoutineRunner(client, pack).run(D.find(pack, "routines", "throttle_reset"), confirmed=[1])
check("one-shot routine + enum result", res.ok and car.engine.throttle_learned and "switch the ignition" in res.values[0][1], res.values)
res = RoutineRunner(client, pack).run(D.find(pack, "routines", "brake_pads_open"), confirmed=[0, 1])
check("brake pad service mode on ABS", res.ok and car.abs.pad_mode)

# ------------------------------------------------------------------ IO control
clk, car, client, pack, prof = session()
io = D.find(pack, "io_controls", "fan_test")
seen = []
t = ActuatorTest(client, pack)


def watch(e):
    seen.append(car.engine.fan_duty())
    if e.kind == "progress" and e.progress >= 40 and t.next_value is None and car.engine.fan_duty() == 50:
        t.next_value = b"\x64"


t._emit = watch
res = t.run(io, "32", confirmed=[0, 1], duration_s=5)
check("fan test runs and switches state", res.ok and 50 in seen and 100 in seen, seen[:40])
check("fan control returned to the ECU", res.data.get("released") and 0xF0A0 not in car.engine.overrides
      and car.engine.fan_duty() == 0)
# error during the test still returns control
clk, car, client, pack, prof = session()
t = ActuatorTest(client, pack)


def boom(e):
    if e.kind == "progress" and e.progress > 20:
        client.cancelled = True


t._emit = boom
res = t.run(io, "64", confirmed=[0, 1], duration_s=10)
check("cancelled actuator test returns control", not res.ok and 0xF0A0 not in car.engine.overrides
      and any(e.get("note") == "return control to ECU" for e in prof.audit_entries()[-6:]))
client.cancelled = False
car.speed_kmh = 30
res = ActuatorTest(client, pack).run(io, "64", confirmed=[0, 1], duration_s=3)
check("fan test refused while driving (NRC 0x88)", not res.ok and getattr(res.error, "nrc", 0) == 0x88)
car.speed_kmh = 0

# ------------------------------------------------------------------ adaptations / security plug-in
clk, car, client, pack, prof = session()
car.engine.service_km = 12
res = AdaptationWriter(client, pack).write(D.find(pack, "adaptations", "service_reset"), confirmed=[0])
check("service reset", res.ok and car.engine.service_km == 15000 and res.data["old"] == "000c14", res.data)
res = AdaptationWriter(client, pack).write(D.find(pack, "adaptations", "battery_registration"), [80, "03"], confirmed=[])
check("battery registration with input fields", res.ok and (car.engine.battery_ah, car.engine.battery_type) == (80, 3)
      and res.data["verified"], res.status.en)
res = AdaptationWriter(client, pack).write(D.find(pack, "adaptations", "battery_registration"), [200, "03"])
check("input range checked (Arabic)", not res.ok and "بين" in res.status.get("ar"))
drl = D.find(pack, "adaptations", "drl_coding")
res = AdaptationWriter(client, pack).write(drl, ["01"])
check("security access without plug-in refused with message", not res.ok and res.error.code == "security"
      and "لا يحتوي RAD IDE" in res.status.get("ar"))
plug = load_plugin(str(HERE / "demo_seedkey.py"))
res = AdaptationWriter(client, pack, plugin=plug).write(drl, ["01"])
check("feature coding with user plug-in", res.ok and car.engine.coding_drl == 1, res.status.en)

# ------------------------------------------------------------------ clear a specific fault
clk, car, client, pack, prof = session()
eng = D.ecu_of(pack, "engine")
flow = ClearFaultFlow(client)
dtcs = flow.read(eng)
check("read DTCs", {d.code for d in dtcs} == {"P0217", "P0128"}, [d.code for d in dtcs])
plan = flow.plan(eng, "P0128")
check("plan explains first", "thermostat" in plan.explanation("en").lower() and "الأسباب" in plan.explanation("ar"))
check("emissions note", plan.emissions and "Readiness" in plan.explanation("ar"))
res = flow.clear(plan, repair_confirmed=False)
check("no clear without repair confirmation", not res.ok and len(flow.read(eng)) == 2)
res = flow.clear(plan, repair_confirmed=True)
check("specific DTC cleared (others kept)", res.ok and res.data["how"] == "single" and
      [d.code for d in flow.read(eng)] == ["P0217"], res.status.en)
plan = flow.plan(eng, "P0217")
check("overheating safety warning", "overheating" in plan.topics and plan.warnings)
car.coolant_c = 120
res = flow.clear(plan, repair_confirmed=True)
check("fault returns when cause present", not res.ok and res.data.get("returned"), res.status.en)
car.coolant_c = 25
air = D.ecu_of(pack, "airbag")
plan = flow.plan(air, "B0001-13")
check("airbag safety warning", "airbag" in plan.topics and plan.ftb == 0x13)
res = flow.clear(plan, repair_confirmed=True)
check("single clear unsupported -> asks for clear-all", not res.ok and res.data.get("needs_clear_all"))
res = flow.clear(plan, repair_confirmed=True, allow_clear_all=True)
check("fallback clear-all", res.ok and res.data["how"] == "all" and not car.airbag.dtcs)
abs_ = D.ecu_of(pack, "abs")
check("brake safety topic", "brakes" in safety_topics("C0035", abs_))
check("DTC codec", parse_code("c0035-1f") == ("C0035", 0x1F) and code_bytes("P0217") == b"\x02\x17\x00"
      and code_bytes("U0100", 0x87) == b"\xc1\x00\x87")
check("unknown manufacturer code labelled", "Manufacturer-specific" in flow.plan(eng, "P1234").info["title"])

# ------------------------------------------------------------------ profiles / audit
entries = prof.audit_entries()
check("audit log has every request with action/id", len(entries) > 5 and all("request" in e for e in entries)
      and any(e.get("action") == "clear_dtc" and e.get("repair_confirmed") for e in entries))
prof.add_history("repair", "Thermostat replaced", "تم تغيير الثرموستات", dtc="P0128")
check("vehicle history saved", get_or_create(prof.vin).history[-1]["dtc"] == "P0128")
n = prof.export_audit_csv(Path(os.environ["RADIDE_CARDIAG_HOME"]) / "audit.csv")
check("audit CSV export", n >= len(entries))
check("VIN check", vin_valid("RADDEM0CAR0000001") and not vin_valid("RADDEMO0CAR00001X"))

# ------------------------------------------------------------------ ODX
odx = HERE / "sample_service.odx"
op, warns = D.load_pack_file(odx)
check("ODX import: routine + io + adaptation + did", len(op["routines"]) == 1 and len(op["io_controls"]) == 1
      and len(op["io_controls"][0]["states"]) == 2 and len(op["adaptations"]) == 1 and len(op["dids"]) == 1, op)
check("ODX import: CAN ids from comparams", op["ecus"]["engine_demo"]["tx"] == "7E0" and op["ecus"]["engine_demo"]["rx"] == "7E8")
check("ODX import: blocked service skipped", any("Skipped" in w.en for w in warns) and
      not any("immo" in r["id"].lower() for r in op["routines"]))
clk, car, client, pack0, prof = session()
res = RoutineRunner(client, op).run(op["routines"][0], confirmed=[], enforce_checks=False)
check("ODX routine runs on the Demo car (one-shot start)", res.ok or getattr(res.error, "nrc", 0) == 0x22, res.status.en)

ok = sum(1 for _, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
