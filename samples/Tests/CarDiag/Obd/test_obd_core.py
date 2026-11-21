"""OBD-II scan tool core (radide/cardiag/obd) - no Qt, no hardware.

Run:  python samples\\Tests\\CarDiag\\Obd\\test_obd_core.py

1. every decoded mode 01 PID formula against hand-computed values (the test fails if a decoded PID has no case)
2. supported-PID bitmaps, multi-PID answers, DTC bytes (CAN / K-line), mode 06 scaling, mode 09 parsing, readiness
3. end to end against the demo vehicle: multi-ECU answers, read / clear DTCs (permanent stays, readiness resets and
   completes while driving), live data changes, freeze frame tied to its DTC, mode 06 limits, mode 09, CSV log
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from radide.cardiag.obd import dtc as D  # noqa: E402
from radide.cardiag.obd import logger as L  # noqa: E402
from radide.cardiag.obd import mode06 as M6  # noqa: E402
from radide.cardiag.obd import mode09 as M9  # noqa: E402
from radide.cardiag.obd import pids as P  # noqa: E402
from radide.cardiag.obd import readiness as R  # noqa: E402
from radide.cardiag.obd import CallableTransport, DemoTransport, DemoVehicle, ObdClient  # noqa: E402

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def vals(pid, data):
    out = []
    for v in P.decode(pid, bytes(data)):
        x = v.value
        out.append(round(x, 4) if isinstance(x, float) else x)
    return out


def near(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if isinstance(y, float) or isinstance(x, float):
            if not isinstance(x, (int, float)) or abs(float(x) - float(y)) > 1e-3:
                return False
        elif x != y:
            return False
    return True


# ------------------------------------------------------------------------------------------- 1. formulas
A, B, C, Dd = 0x7B, 0xC8, 0x12, 0x34          # generic bytes
CASES = {
    # pid: (data, expected values - computed by hand from SAE J1979 formulas)
    0x02: ([0x03, 0x01], ["P0301"]),
    0x03: ([0x02, 0x00], ["Closed loop: using oxygen sensor", "Not present"]),
    0x04: ([0xFF], [100.0]),
    0x05: ([0x7B], [123 - 40]),
    0x06: ([0x80], [0.0]), 0x07: ([0x8C], [140 * 100 / 128 - 100]), 0x08: ([0x00], [-100.0]),
    0x09: ([0xFF], [255 * 100 / 128 - 100]),
    0x0A: ([0x64], [300]),
    0x0B: ([0x65], [101]),
    0x0C: ([0x1A, 0xF8], [(26 * 256 + 248) / 4]),            # 1726 rpm
    0x0D: ([0x50], [80]),
    0x0E: ([0x90], [0x90 / 2 - 64]),
    0x0F: ([0x46], [30]),
    0x10: ([0x01, 0xF4], [5.0]),
    0x11: ([0x33], [51 * 100 / 255]),
    0x12: ([0x04], ["From the outside atmosphere or off"]),
    0x13: ([0x13], ["B1S1, B1S2, B2S1"]),
    0x1C: ([0x07], ["EOBD and OBD-II"]),
    0x1D: ([0x05], ["B1S1, B2S1"]),
    0x1E: ([0x01], ["active"]),
    0x1F: ([0x01, 0x2C], [300]),
    0x21: ([0x00, 0x7B], [123]),
    0x22: ([0x01, 0x00], [0.079 * 256]),
    0x23: ([0x01, 0x00], [2560]),
    0x2C: ([0x80], [128 * 100 / 255]), 0x2D: ([0x40], [64 * 100 / 128 - 100]),
    0x2E: ([0x1A], [26 * 100 / 255]), 0x2F: ([0xC0], [192 * 100 / 255]),
    0x30: ([0x29], [41]),
    0x31: ([0x07, 0x51], [1873]),
    0x32: ([0xFF, 0xF0], [-16 / 4]),
    0x33: ([0x65], [101]),
    0x3C: ([0x12, 0x34], [(0x12 * 256 + 0x34) / 10 - 40]), 0x3D: ([0x0F, 0xA0], [360.0]),
    0x3E: ([0x00, 0x00], [-40.0]), 0x3F: ([0x27, 0x10], [960.0]),
    0x42: ([0x37, 0x46], [(0x37 * 256 + 0x46) / 1000]),
    0x43: ([0x00, 0xFF], [100.0]),
    0x44: ([0x80, 0x00], [1.0]),
    0x45: ([0x80], [128 * 100 / 255]), 0x46: ([0x44], [28]),
    0x47: ([0x20], [32 * 100 / 255]), 0x48: ([0x21], [33 * 100 / 255]), 0x49: ([0x22], [34 * 100 / 255]),
    0x4A: ([0x23], [35 * 100 / 255]), 0x4B: ([0x24], [36 * 100 / 255]), 0x4C: ([0x25], [37 * 100 / 255]),
    0x4D: ([0x00, 0x9A], [154]), 0x4E: ([0x01, 0x00], [256]),
    0x4F: ([0x02, 0x05, 0x10, 0x0A], [2, 5, 16, 100]),
    0x50: ([0x19, 0, 0, 0], [250]),
    0x51: ([0x04], ["Diesel"]),
    0x52: ([0x26], [38 * 100 / 255]),
    0x53: ([0x4E, 0x20], [100.0]),
    0x54: ([0xFF, 0x9C], [-100]),
    0x55: ([0x80, 0x90], [0.0, 0x90 * 100 / 128 - 100]), 0x56: ([0x70, 0x80], [0x70 * 100 / 128 - 100, 0.0]),
    0x57: ([0x81, 0x7F], [0x81 * 100 / 128 - 100, 0x7F * 100 / 128 - 100]),
    0x58: ([0x00, 0xFF], [-100.0, 255 * 100 / 128 - 100]),
    0x59: ([0x0B, 0xB8], [30000]),
    0x5A: ([0x40], [64 * 100 / 255]), 0x5B: ([0xE6], [230 * 100 / 255]), 0x5C: ([0x82], [90]),
    0x5D: ([0x69, 0x00], [0x6900 / 128 - 210]),
    0x5E: ([0x00, 0xC8], [10.0]),
    0x5F: ([0x0F], ["Heavy duty vehicles (EURO V) B2"]),
    0x61: ([0x96], [25]), 0x62: ([0x7D], [0]), 0x63: ([0x01, 0x2C], [300]),
    0x64: ([0x7D, 0x8C, 0xA0, 0xB4, 0xC8], [0, 15, 35, 55, 75]),
    0x65: ([0x05, 0x04], ["inactive", "active"]),
    0x66: ([0x03, 0x01, 0x40, 0x00, 0x20], [10.0, 1.0]),
    0x67: ([0x01, 0x7B, 0x00], [83]),
    0x68: ([0x03, 0x46, 0x47, 0, 0, 0, 0], [30, 31]),
    0x69: ([0x07, 0x80, 0x40, 0x90, 0, 0, 0], [128 * 100 / 255, 64 * 100 / 255, 0x90 * 100 / 128 - 100]),
    0x6A: ([0x03, 0xFF, 0x80, 0, 0], [100.0, 128 * 100 / 255]),
    0x6B: ([0x05, 0x96, 0x00, 0xA0, 0x00], [110, 120]),
    0x6C: ([0x03, 0x33, 0x34, 0, 0], [51 * 100 / 255, 52 * 100 / 255]),
    0x6D: ([0x07, 0x13, 0x88, 0x13, 0x24, 0x50, 0, 0, 0, 0, 0], [50000, 49000, 40]),
    0x6E: ([0x03, 0x00, 0x64, 0x00, 0x63, 0, 0, 0, 0], [1000, 990]),
    0x6F: ([0x01, 0x62, 0x00], [98]),
    0x70: ([0x03, 0x0C, 0x80, 0x0C, 0x00, 0, 0, 0, 0, 0], [0x0C80 * 0.03125, 0x0C00 * 0.03125]),
    0x71: ([0x03, 0x80, 0x7F, 0, 0, 0], [128 * 100 / 255, 127 * 100 / 255]),
    0x72: ([0x01, 0x40, 0, 0, 0], [64 * 100 / 255]),
    0x73: ([0x01, 0x27, 0x10, 0, 0], [100.0]),
    0x74: ([0x01, 0x27, 0x10, 0, 0], [100000]),
    0x75: ([0x0F, 0x46, 0x82, 0x1F, 0x40, 0x1B, 0x58], [30, 90, 760.0, 660.0]),
    0x76: ([0x01, 0x50, 0, 0, 0, 0, 0], [40]),
    0x77: ([0x01, 0x5A, 0, 0, 0], [50]),
    0x78: ([0x03, 0x1F, 0x40, 0x1B, 0x58, 0, 0, 0, 0], [760.0, 660.0]),
    0x79: ([0x01, 0x0F, 0xA0, 0, 0, 0, 0, 0, 0], [360.0]),
    0x7A: ([0x07, 0x01, 0xF4, 0x27, 0x10, 0x25, 0x1C], [5.0, 100.0, 95.0]),
    0x7B: ([0x01, 0x00, 0x64, 0, 0, 0, 0], [1.0]),
    0x7C: ([0x03, 0x1F, 0x40, 0x22, 0x60, 0, 0, 0, 0], [760.0, 840.0]),
    0x7F: ([0x07, 0, 0, 0x0E, 0x10, 0, 0, 0x03, 0x84, 0, 0, 0, 0x3C], [3600, 900, 60]),
    0x83: ([0x03, 0x00, 0xC8, 0x00, 0x32, 0, 0, 0, 0], [200, 50]),
    0x84: ([0x5A], [50]),
    0x85: ([0x07, 0x00, 0x64, 0x00, 0xC8, 0x80, 0, 0, 0x01, 0x00], [0.5, 1.0, 128 * 100 / 255, 256]),
    0x86: ([0x01, 0x03, 0x20, 0, 0], [10.0]),
    0x87: ([0x01, 0x0C, 0x80, 0, 0], [100.0]),
    0x8D: ([0x80], [128 * 100 / 255]),
    0x8E: ([0x87], [10]),
    0x9D: ([0x01, 0xF4, 0x03, 0xE8], [10.0, 20.0]),
    0x9E: ([0x01, 0xF4], [100.0]),
    0xA2: ([0x01, 0x40], [10.0]),
    0xA4: ([0x03, 0x30, 0x05, 0x5A], [3, 1.37]),
    0xA5: ([0x01, 0x64, 0, 0], [50.0]),
    0xA6: ([0x00, 0x07, 0x5B, 0xCD], [0x00075BCD / 10]),   # 48225.3 km
    0xA9: ([0x01, 0x01, 0, 0], ["ON (ABS disabled)"]),
}
# narrow-band O2 sensors 14-1B: A/200 V, B*100/128-100 % (FF = not used for trim)
for i in range(8):
    CASES[0x14 + i] = ([0x5A, 0x80], [0.45, 0.0]) if i % 2 == 0 else ([0x8C, 0xFF], [0.7, "not used for trim"])
# wide-range O2 24-2B: lambda 2/65536*(256A+B), voltage 8/65536*(256C+D); 34-3B: current (256C+D)/256-128 mA
for i in range(8):
    CASES[0x24 + i] = ([0x80, 0x00, 0x40, 0x00], [1.0, 2.0])
    CASES[0x34 + i] = ([0x80, 0x00, 0x81, 0x00], [1.0, 1.0])
# monitor status 01: MIL on, 3 codes, spark, misfire/fuel/components supported+complete, catalyst+evap supported,
# evap incomplete
CASES[0x01] = ([0x83, 0x07, 0x05, 0x04], ["ON", 3, "Spark ignition (petrol)", "Complete", "Complete", "Complete",
                                          "Complete", "Incomplete"])
CASES[0x41] = ([0x00, 0x07, 0x05, 0x01], ["Spark ignition (petrol)", "Complete", "Complete", "Complete", "Incomplete", "Complete"])
for base in P.BITMAP_PIDS:
    if base in P.P and not P.P[base].raw:
        CASES[base] = ([0xBE, 0x1F, 0xA8, 0x13], [" ".join(f"{base + n:02X}" for n in
                                                            (1, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 19, 21, 28, 31, 32))])

decoded = sorted(p for p in P.P if not P.P[p].raw)
missing = [f"{p:02X}" for p in decoded if p not in CASES]
check("every decoded PID 00-C8 has a hand-computed case", not missing, missing)
for pid in decoded:
    if pid in CASES:
        data, want = CASES[pid]
        got = vals(pid, data)
        check(f"PID {pid:02X} {P.P[pid].short}", near(got, want), f"got {got} want {want}")
check("table covers PIDs 00-C8", all(p in P.P for p in range(0xC9)))
check("raw PIDs show raw bytes (never guessed)", vals(0x9A, [1, 2, 3, 4, 5, 6]) == ["01 02 03 04 05 06"])
check("short answer does not crash", "short" in P.decode(0x0C, b"\x1a")[0].label)
check("data length table (multi-PID split)", P.split_multi(bytes([0x0C, 0x1A, 0xF8, 0x0D, 0x50, 0x05, 0x7B])) ==
      [(0x0C, b"\x1a\xf8"), (0x0D, b"\x50"), (0x05, b"\x7b")])
check("supported bitmap 01 00 BE 1F A8 13", P.supported_from_bitmap(0, bytes([0xBE, 0x1F, 0xA8, 0x13])) ==
      {1, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 19, 21, 28, 31, 32})
check("gauge flags", P.is_graphable(0x0C) and not P.is_graphable(0x01) and not P.is_graphable(0x20))

# ------------------------------------------------------------------------------------------- 2. DTC / 06 / 09 / readiness
check("DTC P0301", P.dtc_text(0x03, 0x01) == "P0301" and D.encode("P0301") == b"\x03\x01")
check("DTC letters C/B/U", [P.dtc_text(a, b) for a, b in ((0x41, 0x23), (0x80, 0x01), (0xC1, 0x00))] ==
      ["C0123", "B0001", "U0100"])
check("DTC encode round trip", all(P.dtc_text(*D.encode(c)) == c for c in ("P2A3F", "U3FFF", "B1234", "C0561")))
check("mode 03 CAN with count", D.parse(bytes([0x43, 0x02, 0x03, 0x01, 0x01, 0x71]), True) == ["P0301", "P0171"])
check("mode 03 K-line padded", D.parse(bytes([0x43, 0x03, 0x01, 0x00, 0x00, 0x00, 0x00]), False) == ["P0301"])
check("mode 0A permanent", D.parse(bytes([0x4A, 0x01, 0x04, 0x20]), True) == ["P0420"])
check("categories", D.category("P0301") == "Ignition system or misfire" and D.manufacturer_specific("P1234")
      and not D.manufacturer_specific("P0420") and D.category("U0100") == "Network (generic)")
check("safety-relevant faults", D.safety_relevant("C0035") and D.safety_relevant("B0001") and
      D.safety_relevant("P0217") and D.safety_relevant("C0460") == "Steering" and not D.safety_relevant("P0420"))
recs = M6.parse(bytes([0x46, 0x01, 0x01, 0x0A, 0x0F, 0x1A, 0x0B, 0xB8, 0x11, 0x94,
                       0x21, 0x80, 0x20, 0x00, 0xA8, 0x00, 0x00, 0x00, 0x99]))
check("mode 06 mV scaling", abs(recs[0].value - 0x0F1A * 0.122) < 1e-6 and recs[0].unit == "mV" and recs[0].passed)
check("mode 06 ratio fail", recs[1].unit == "ratio" and not recs[1].passed and recs[1].mid_name == "Catalyst monitor bank 1")
check("mode 06 signed", M6.scale(0x96, 0xFF9C) == (-10.0, "°C"))
check("mode 06 temperature offset", M6.scale(0x16, 1000) == (60.0, "°C"))
check("mode 06 bitmap", M6.supported_from_bitmap(0, bytes([0x46, 0x00, 0xC0, 0x00, 0x00, 0x01])) == {1, 2, 32})
check("mode 09 VIN", M9.vin(b"\x49\x02\x01" + b"XRDSM1C25T0000417") == "XRDSM1C25T0000417")
check("mode 09 CALIDs", M9.calids(b"\x49\x04\x02" + b"CAL-A".ljust(16, b"\0") + b"CAL-B".ljust(16, b"\0")) ==
      ["CAL-A", "CAL-B"])
check("mode 09 CVNs", M9.cvns(b"\x49\x06\x02\x1a\x2b\x3c\x4d\x00\xc0\xff\xee") == ["1A2B3C4D", "00C0FFEE"])
check("mode 09 ECU name", M9.ecu_name(b"\x49\x0a\x01" + b"ECM\0-EngineControl".ljust(20, b"\0")) == "ECM-EngineControl")
check("VIN check digit", M9.vin_check_digit_ok("1M8GDM9AXKP042788") is True and
      M9.vin_check_digit_ok("1M8GDM9A1KP042788") is False)
check("VIN year / region", M9.vin_model_year("XRDSM1C25T0000417") == [1996, 2026] and
      M9.vin_region("WVWZZZ1JZXW000001") == "Europe" and M9.vin_region("JH4KA") == "Asia")
st = R.decode_status(bytes([0x83, 0x07, 0x65, 0x24]))
check("readiness decode", st.mil and st.dtc_count == 3 and not st.diesel and
      [m.key for m in st.incomplete()] == ["evap", "o2_sensor"])
dz = R.decode_status(bytes([0x00, 0x0F, 0xC0, 0x40]))
check("readiness diesel", dz.diesel and [m.key for m in dz.incomplete()] == ["pm_filter"])
enc = R.encode_status(True, 2, False, {"misfire": True, "catalyst": True}, {"misfire": True, "catalyst": False})
check("readiness encode round trip", R.decode_status(enc).incomplete()[0].key == "catalyst")
check("readiness explanations (EN + AR) for every monitor", all(R.explain(k) and R.explain(k, True) for k in R.NAMES))

# ------------------------------------------------------------------------------------------- 3. demo vehicle end to end
veh = DemoVehicle(realtime=False)
veh.advance(5)
c = ObdClient(DemoTransport(veh))
sup = c.supported_pids()
check("two ECUs answer 01 00", set(sup) == {"7E8", "7E9"}, sup)
check("engine supports A6 (bitmap chain to A0)", 0xA6 in sup["7E8"] and 0xA4 in sup["7E9"])
cool0 = c.read_pid(0x05)["7E8"].value
rpm0 = c.read_pid(0x0C)["7E8"].value
veh.advance(17)
cool1 = c.read_pid(0x05)["7E8"].value
rpm1 = c.read_pid(0x0C)["7E8"].value
check("live data changes (warming up, accelerating)", cool1 > cool0 and rpm1 != rpm0, (cool0, cool1, rpm0, rpm1))
multi = c.read_pids([0x0C, 0x0D, 0x05, 0x04, 0x11, 0x42])
check("multi-PID request (6 per frame on CAN)", {(r.ecu, r.pid) for r in multi} >=
      {("7E8", 0x0C), ("7E8", 0x0D), ("7E9", 0x0C), ("7E9", 0x0D)})
before = veh.requests
c.read_pids([0x0C, 0x0D, 0x05, 0x04, 0x11, 0x42, 0x10])
check("7 PIDs = 2 requests", veh.requests - before == 2)
ent = c.read_all_dtcs()
codes = {(e.ecu, e.code): e.kinds for e in ent}
check("stored / pending / permanent", codes.get(("7E8", "P0301")) == {"stored", "permanent"} and
      codes.get(("7E8", "P0420")) == {"pending"} and codes.get(("7E9", "P0715")) == {"stored"}, codes)
ff = c.freeze_frames()
check("freeze frame tied to its DTC", ff["7E8"].dtc == "P0301" and ff["7E9"].dtc == "P0715")
ffv = {r.pid: r.value for r in ff["7E8"].readings()}
check("freeze frame values", ffv.get(0x0C) == 2150 and ffv.get(0x05) == 88 and ffv.get(0x0D) == 72, ffv)
rd = c.readiness()
check("MIL on, 2 codes, all complete before clear", rd["7E8"].mil and rd["7E8"].dtc_count == 2 and
      not rd["7E8"].incomplete())
t6 = c.mode06()
fails = [(t.mid, t.tid) for t in t6["7E8"] if not t.passed]
check("mode 06: catalyst + cylinder 1 misfire fail", (0x21, 0x80) in fails and (0xA1, 0x0B) in fails, fails)
vi = c.vehicle_info()
check("mode 09 VIN / CALID / CVN / names", vi.vin == "XRDSM1C25T0000417" and vi.calids["7E9"] == ["RADDEMO-TCM-0007"]
      and vi.cvns["7E8"][0] == "1A2B3C4D" and vi.names["7E8"].startswith("ECM") and len(vi.ipt["7E8"]) == 20)
res = c.clear_dtcs()
check("mode 04 acknowledged by both ECUs", res == {"7E8": True, "7E9": True})
ent = c.read_all_dtcs()
check("after clear only the permanent code remains", [(e.code, e.kinds) for e in ent] == [("P0301", {"permanent"})])
check("freeze frames erased", c.freeze_frames() == {})
inc = [m.key for m in c.readiness()["7E8"].incomplete()]
check("readiness reset to incomplete", set(inc) == {"catalyst", "evap", "o2_sensor", "o2_heater", "egr"}, inc)
check("MIL off + counters reset", not c.readiness()["7E8"].mil and c.read_pid(0x31)["7E8"].value == 0)
veh.advance(600)
inc = [m.key for m in c.readiness()["7E8"].incomplete()]
check("driving completes monitors (EVAP needs a cold start)", inc == ["evap"], inc)
check("permanent code removed after the monitor passed", c.read_all_dtcs() == [])
check("distance since clear counts up", c.read_pid(0x31)["7E8"].value > 3)

# K-line style transport (one PID per request, codes in groups of three)
kl = CallableTransport(lambda d: [("10", bytes([0x43, 0x03, 0x01, 0x01, 0x71, 0x00, 0x00]))] if d == b"\x03" else
                       [("10", b"\x41\x0c\x1a\xf8")] if d == b"\x01\x0c" else [], is_can=False)
kc = ObdClient(kl)
check("K-line DTCs", kc.read_dtcs("stored") == {"10": ["P0301", "P0171"]})
check("K-line one PID per request", kc.read_pids([0x0C])[0].value == 1726)
neg = ObdClient(CallableTransport(lambda d: [("7E8", b"\x7f\x04\x22")]))
check("negative answer to clear", neg.clear_dtcs() == {"7E8": False})

# CSV log round trip
tmp = Path(tempfile.mkdtemp(prefix="obdlog"))
lg = L.CsvLogger(tmp / "log.csv", [("7E8", 0x0C), ("7E8", 0x05)])
for i in range(5):
    lg.write({("7E8", 0x0C): 800.0 + i * 100, ("7E8", 0x05): 80 + i}, t=i * 0.5)
lg.close()
rec = L.load(str(tmp / "log.csv"))
check("CSV header keeps PID numbers", rec.keys() == [("7E8", 0x0C), ("7E8", 0x05)] and len(rec) == 5)
check("CSV values / time", rec.data[0][-1] == 1200.0 and rec.duration == 2.0 and rec.index_at(1.2) == 2)
(tmp / "other.csv").write_text("Time,Boost psi,Note\n0,1.5,a\n1,2.5,b\n", encoding="utf-8")
oth = L.load(str(tmp / "other.csv"))
check("foreign CSV plays back (numeric columns only)", oth.keys() == [("", "Boost psi")] and oth.data[0] == [1.5, 2.5])

# ------------------------------------------------------------------------------------------- 4. through the link slice
# the same client over the ELM327 stack of radide/cardiag/link + its shared Demo car simulator (radide/cardiag/sim)
try:
    from radide.cardiag.link import demo_link
    from radide.cardiag.obd import LinkTransport
    link = demo_link()
except Exception as e:  # noqa: BLE001 - the link slice is optional for this file
    link = None
    print("SKIP link-slice checks:", e)
if link is not None:
    lc = ObdClient(LinkTransport(link))
    check("ELM327 stack: CAN, engine ECU answers", lc.is_can and "7E8" in lc.supported_pids())
    rr = {r.pid: r.value for r in lc.read_pids([0x0C, 0x0D, 0x05, 0x04, 0x11, 0x42, 0x10])}
    check("ELM327 stack: 7 PIDs decoded", len(rr) == 7 and rr[0x0C] > 0, rr)
    check("ELM327 stack: DTCs", any(e.code.startswith("P") for e in lc.read_all_dtcs()))
    check("ELM327 stack: readiness + VIN", lc.readiness() and len(lc.vehicle_info().vin) == 17)
    link.close()

ok = sum(1 for _, c_ in RESULTS if c_)
print(f"{ok}/{len(RESULTS)} passed; FAILED: {[n for n, c_ in RESULTS if not c_] or 'none'}", flush=True)
os._exit(0 if ok == len(RESULTS) else 1)
