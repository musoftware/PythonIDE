"""Service functions through the Car Diagnostics connection layer: the workbench's Demo car (radide/cardiag/sim)
behind the simulated ELM327 adapter (radide/cardiag/link, ``demo_link``) and behind the virtual CAN bus with our
ISO-TP (``demo_can_link``), driven with the built-in pack ``service/packs/workbench_car.json``.

No Qt, no hardware. The simulator runs 4x faster than real time so the routines finish in seconds.

Run:  .venv\\Scripts\\python.exe samples\\Tests\\CarDiag\\Service\\test_service_workbench.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
os.environ["RADIDE_CARDIAG_HOME"] = tempfile.mkdtemp(prefix="cardiag-svc-wb-")

from radide.cardiag.link import demo_can_link, demo_link  # noqa: E402
from radide.cardiag.service import definitions as D  # noqa: E402
from radide.cardiag.service.dtc import ClearFaultFlow  # noqa: E402
from radide.cardiag.service.iocontrol import ActuatorTest  # noqa: E402
from radide.cardiag.service.profiles import get_or_create  # noqa: E402
from radide.cardiag.service.runner import RoutineRunner  # noqa: E402
from radide.cardiag.service.transport import ServiceClient  # noqa: E402
from radide.cardiag.sim.car import VIN, VirtualCar  # noqa: E402

RESULTS = []
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)


def settle():
    """Let the simulated car advance once after a state change (rpm / speed follow on its next model step)."""
    import time
    time.sleep(0.05)
    car.update()


def fresh(engine_running=False, can=False):
    car = VirtualCar(time_scale=4.0, engine_running=engine_running)
    link = demo_can_link(car) if can else demo_link(car)
    prof = get_or_create(VIN)
    client = ServiceClient(link, audit=prof.audit)
    return car, link, client, prof


pack = D.workbench_pack()
_, errs, _ = D.normalize(json.loads((ROOT / "radide/cardiag/service/packs/workbench_car.json").read_text("utf-8")))
check("workbench pack validates", not errs and pack.get("demo") == "workbench", [e.en for e in errs])
check("workbench pack: routines / actuators / adaptation", len(pack["routines"]) >= 8 and len(pack["io_controls"]) >= 5
      and pack["adaptations"])
check("pack texts bilingual", all(e.get("name_ar") for k in ("routines", "io_controls", "adaptations") for e in pack[k]))

# ------------------------------------------------------------------ link detection
car, link, client, prof = fresh()
check("demo ELM link detected as the simulator", D.is_virtual_car_link(link))
check("no link / other object is not the simulator", not D.is_virtual_car_link(None) and not D.is_virtual_car_link(object()))

# ------------------------------------------------------------------ cooling-system bleed to completion
bleed = D.find(pack, "routines", "cooling_bleed")
bleed_fast = json.loads(json.dumps(bleed))
bleed_fast["poll"]["interval_s"] = 0.2
events = []
res = RoutineRunner(client, pack, emit=events.append).run(bleed_fast, confirmed=[2, 3, 4])
progs = [e.progress for e in events if e.kind == "progress"]
check("bleed over ELM327 completes", res.ok, res.status.en)
check("bleed progress rises to 100", progs and progs[-1] == 100 and progs == sorted(progs) and len(progs) >= 4, progs)
check("bleed result bytes interpreted", any("pump" in n.en.lower() for n, _ in res.values), res.values)
check("bleed instructions shown", sum(1 for e in events if e.kind == "instruction") == 3)
check("ECU back in the default session", car.engine.session == 0x01)

# automatic precondition: engine running blocks before anything is sent
car.start_engine(); settle()
res = RoutineRunner(client, pack).run(bleed_fast, confirmed=[2, 3, 4])
check("automatic check (engine running) blocks the bleed", not res.ok and res.error.code == "preconditions", res.status.en)
# the ECU's own refusal: NRC 0x22 in Arabic
res = RoutineRunner(client, pack).run(bleed_fast, confirmed=[2, 3, 4], enforce_checks=False)
check("ECU refuses with NRC 0x22", not res.ok and getattr(res.error, "nrc", 0) == 0x22, res.status.en)
check("NRC 0x22 explained in Arabic", "0x22" in res.status.get("ar") and any("؀" <= c <= "ۿ" for c in res.status.get("ar")))
car.stop_engine(); settle()
# hot coolant: temperatureTooHigh (0x86)
car.coolant = 112.0
res = RoutineRunner(client, pack).run(bleed_fast, confirmed=[2, 3, 4])
check("hot coolant refused (NRC 0x86)", not res.ok and getattr(res.error, "nrc", 0) == 0x86, res.status.en)
car.coolant = 30.0
# engine started during the bleed -> ECU aborts -> failed status
def start_mid(e):
    if e.kind == "progress" and e.progress >= 20:
        car.start_engine(); settle()


res = RoutineRunner(client, pack, emit=start_mid).run(bleed_fast, confirmed=[2, 3, 4], enforce_checks=False)
check("engine start aborts the bleed (status 03)", not res.ok and res.error.code == "routine_failed", res.status.en)
car.stop_engine(); settle()

# ------------------------------------------------------------------ routine with input fields
res = RoutineRunner(client, pack).run(D.find(pack, "routines", "battery_registration"), confirmed=[],
                                      params=bytes([80, 3]))
check("battery registration (routine parameters)", res.ok and car.battery_info == bytes([80, 3]), (res.status.en, car.battery_info))
from radide.cardiag.service.adaptation import encode_input  # noqa: E402
check("routine input encoded / range checked", encode_input(D.find(pack, "routines", "injector_test"), [3]) == b"\x03")
try:
    encode_input(D.find(pack, "routines", "injector_test"), [9])
    check("cylinder 9 refused", False)
except Exception as e:  # noqa: BLE001
    check("cylinder 9 refused", getattr(e, "code", "") == "input" and getattr(e, "text", None) is not None
          and e.text.get("ar"), e)

# ------------------------------------------------------------------ oil service reset with response pending (cluster)
car.distance_to_service = -350.0
res = RoutineRunner(client, pack).run(D.find(pack, "routines", "service_reset"), confirmed=[0])
check("oil service reset on the cluster (response pending)", res.ok and car.distance_to_service > 14000, res.status.en)

# ------------------------------------------------------------------ steering angle calibration preconditions
sas = D.find(pack, "routines", "sas_calibration")
res = RoutineRunner(client, pack).run(sas, confirmed=[2])
check("SAS calibration needs the engine running (automatic check)", not res.ok and res.error.code == "preconditions")
car.start_engine(); settle()
car.steering_angle, car.sas_calibrated = 4.0, False
sas_fast = json.loads(json.dumps(sas)); sas_fast["poll"]["interval_s"] = 0.2
res = RoutineRunner(client, pack).run(sas_fast, confirmed=[2])
check("SAS calibration completes", res.ok and car.sas_calibrated, res.status.en)

# ------------------------------------------------------------------ actuator test returns control
car.stop_engine(); settle()
fan = D.find(pack, "io_controls", "fan_test")
t = ActuatorTest(client, pack)
seen = []


def watch(e):
    car.update()
    seen.append(car.fan_duty)
    if e.kind == "progress" and e.progress >= 40 and t.next_value is None and car.fan_duty == 50:
        t.next_value = b"\x64"


t._emit = watch
res = t.run(fan, "32", confirmed=[0], duration_s=2)
car.update()
check("fan test over ELM327 switches state", res.ok and 50 in seen and 100 in seen, seen[:30])
check("fan control returned to the ECU", res.data.get("released") and not car.engine.ios[0x4001].controlled
      and car.fan_duty == 0, (res.data, car.fan_duty))
res = ActuatorTest(client, pack).run(D.find(pack, "io_controls", "injector_cutoff_1"), "01", confirmed=[0],
                                     enforce_checks=False, duration_s=1)
check("injector cut-off refused with engine off (NRC 0x84)", not res.ok and getattr(res.error, "nrc", 0) == 0x84
      and not car.engine.ios[0x4010].controlled, res.status.en)

# ------------------------------------------------------------------ clear a specific fault
eng = D.ecu_of(pack, "engine")
flow = ClearFaultFlow(client)
codes = [d.code for d in flow.read(eng)]
check("engine faults read over ELM327", "P0171" in codes and "P0301" in codes, codes)
plan = flow.plan(eng, "P0171")
check("explanation before clearing", plan.explanation("en") and plan.explanation("ar") and plan.emissions)
res = flow.clear(plan, repair_confirmed=False)
check("no clear without repair confirmation", not res.ok and "P0171" in [d.code for d in flow.read(eng)])
res = flow.clear(plan, repair_confirmed=True)
after = [d.code for d in flow.read(eng)]
check("P0171 cleared alone (UDS 14 with the DTC)", res.ok and res.data.get("how") == "single" and "P0171" not in after
      and "P0301" in after, (res.status.en, after))
bag = D.ecu_of(pack, "airbag")
bag_codes = [d.code for d in flow.read(bag)]
plan = flow.plan(bag, bag_codes[0] if bag_codes else "B0001")
check("airbag safety warning", "airbag" in plan.topics and plan.warnings, plan.topics)
res = flow.clear(plan, repair_confirmed=True)
check("airbag unit: single clear unsupported -> asks for clear-all", not res.ok and res.data.get("needs_clear_all"), res.status.en)
abs_ = D.ecu_of(pack, "abs")
plan = flow.plan(abs_, "C0035")
check("brake safety topic on the ABS fault", "brakes" in plan.topics)
link.close()

# ------------------------------------------------------------------ the same over the virtual CAN bus (ISO-TP)
car, link, client, prof = fresh(can=True)
check("virtual CAN link detected as the simulator", D.is_virtual_car_link(link))
res = RoutineRunner(client, pack).run(D.find(pack, "routines", "throttle_reset") | {"poll": {**D.find(
    pack, "routines", "throttle_reset")["poll"], "interval_s": 0.2}}, confirmed=[1])
check("throttle adaptation reset over raw CAN / ISO-TP", res.ok, res.status.en)
link.close()

entries = prof.audit_entries()
check("audit log records the workbench session", len(entries) > 20 and any(e.get("action") == "clear_dtc" for e in entries))

ok = sum(1 for _, c in RESULTS if c)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c in RESULTS if not c] or 'none'}")
sys.exit(0 if ok == len(RESULTS) else 1)
