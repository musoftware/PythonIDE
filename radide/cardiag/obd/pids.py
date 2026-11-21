"""SAE J1979 / ISO 15031-5 mode 01 (and mode 02) PIDs 0x00-0xC8: names, data lengths, formulas and units.

`decode(pid, data)` returns a list of `Value(label, value, unit)`; the first one is the PID's main value (what the
gauges and the graph use).  Values are floats / ints, or strings for enumerations and bit fields.  PIDs whose
layout is not described well enough in public sources are shown as raw bytes (``raw`` = True) - never guessed.

Formulas use the bytes A, B, C, ... of the response data (after the PID byte), as in SAE J1979.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Value:
    label: str
    value: object
    unit: str = ""

    def text(self, digits: int | None = None) -> str:
        v = self.value
        if isinstance(v, float):
            d = 2 if digits is None else digits
            s = f"{v:.{d}f}".rstrip("0").rstrip(".") if d else f"{v:.0f}"
            v = s if s not in ("", "-0") else "0"
        return f"{v} {self.unit}".strip()


@dataclass
class Pid:
    pid: int
    length: int                       # data bytes after the PID byte
    name: str
    unit: str = ""
    lo: float = 0.0                   # gauge range of the main value
    hi: float = 100.0
    fn: Callable[[bytes], list] | None = None
    raw: bool = False                 # layout not decoded (raw bytes shown)
    kind: str = "num"                 # num | enum | bits | bitmap | dtc | raw
    short: str = ""                   # short column / gauge label
    group: str = "Engine"
    tags: list = field(default_factory=list)


def _u16(d, i=0):
    return (d[i] << 8) | d[i + 1]


def _s16(d, i=0):
    v = _u16(d, i)
    return v - 0x10000 if v & 0x8000 else v


def _u32(d, i=0):
    return (d[i] << 24) | (d[i + 1] << 16) | (d[i + 2] << 8) | d[i + 3]


def pct(a):            # A*100/255
    return a * 100.0 / 255.0


def trim(a):           # A*100/128 - 100
    return a * 100.0 / 128.0 - 100.0


def temp(a):           # A - 40
    return a - 40


def _bits_list(byte, names):
    return [n for i, n in enumerate(names) if n and byte & (1 << i)]


FUEL_SYSTEM = {0: "Not present", 1: "Open loop: engine not yet warm", 2: "Closed loop: using oxygen sensor",
               4: "Open loop: engine load or fuel cut on deceleration", 8: "Open loop: system failure",
               16: "Closed loop: fault in at least one oxygen sensor"}
SECONDARY_AIR = {1: "Upstream", 2: "Downstream of catalytic converter", 4: "From the outside atmosphere or off",
                 8: "Pump commanded on for diagnostics"}
OBD_STANDARDS = {1: "OBD-II as defined by CARB", 2: "OBD as defined by the EPA", 3: "OBD and OBD-II", 4: "OBD-I",
                 5: "Not OBD compliant", 6: "EOBD (Europe)", 7: "EOBD and OBD-II", 8: "EOBD and OBD",
                 9: "EOBD, OBD and OBD II", 10: "JOBD (Japan)", 11: "JOBD and OBD II", 12: "JOBD and EOBD",
                 13: "JOBD, EOBD, and OBD II", 17: "Engine Manufacturer Diagnostics (EMD)",
                 18: "Engine Manufacturer Diagnostics Enhanced (EMD+)", 19: "Heavy Duty On-Board Diagnostics (Child/Partial)",
                 20: "Heavy Duty On-Board Diagnostics", 21: "World Wide Harmonized OBD (WWH OBD)",
                 23: "Heavy Duty Euro OBD Stage I without NOx control", 24: "Heavy Duty Euro OBD Stage I with NOx control",
                 25: "Heavy Duty Euro OBD Stage II without NOx control", 26: "Heavy Duty Euro OBD Stage II with NOx control",
                 28: "Brazil OBD Phase 1", 29: "Brazil OBD Phase 2", 30: "Korean OBD", 31: "India OBD I",
                 32: "India OBD II", 33: "Heavy Duty Euro OBD Stage VI"}
FUEL_TYPES = {0: "Not available", 1: "Gasoline", 2: "Methanol", 3: "Ethanol", 4: "Diesel", 5: "LPG", 6: "CNG",
              7: "Propane", 8: "Electric", 9: "Bifuel running Gasoline", 10: "Bifuel running Methanol",
              11: "Bifuel running Ethanol", 12: "Bifuel running LPG", 13: "Bifuel running CNG",
              14: "Bifuel running Propane", 15: "Bifuel running Electricity",
              16: "Bifuel running electric and combustion engine", 17: "Hybrid gasoline", 18: "Hybrid Ethanol",
              19: "Hybrid Diesel", 20: "Hybrid Electric", 21: "Hybrid running electric and combustion engine",
              22: "Hybrid Regenerative", 23: "Bifuel running diesel"}
EMISSION_REQ = {0x0E: "Heavy duty vehicles (EURO IV) B1", 0x0F: "Heavy duty vehicles (EURO V) B2",
                0x10: "Heavy duty vehicles (EURO EEV) C"}


def dtc_text(a: int, b: int) -> str:
    """Two DTC bytes -> "P0301" (SAE J2012: 2 bits letter, 2 bits first digit, then three hex digits)."""
    return "PCBU"[a >> 6] + str((a >> 4) & 3) + f"{a & 0x0F:X}{b >> 4:X}{b & 0x0F:X}"


# ----------------------------------------------------------------------------------------------- decoders
def _one(label, unit, f):
    return lambda d: [Value(label, f(d), unit)]


def _bitmap(base):
    def f(d):
        bits = _u32(d)
        sup = [base + i + 1 for i in range(32) if bits & (1 << (31 - i))]
        return [Value("Supported PIDs", " ".join(f"{p:02X}" for p in sup) or "none", "")]
    return f


def _monitor(d):
    from .readiness import decode_status
    st = decode_status(bytes(d))
    out = [Value("MIL", "ON" if st.mil else "OFF"), Value("Stored DTCs", st.dtc_count),
           Value("Engine type", "Compression ignition (diesel)" if st.diesel else "Spark ignition (petrol)")]
    for m in st.monitors:
        if m.supported:
            out.append(Value(m.name, "Complete" if m.complete else "Incomplete"))
    return out


def _monitor_drive(d):
    vals = _monitor(d)
    return vals[2:] if len(vals) > 2 else vals          # 41: byte A is reserved


def _fuel_system(d):
    return [Value("Fuel system 1", FUEL_SYSTEM.get(d[0], f"0x{d[0]:02X}")),
            Value("Fuel system 2", FUEL_SYSTEM.get(d[1], f"0x{d[1]:02X}"))]


def _o2_narrow(n):
    def f(d):
        out = [Value(f"O2 sensor {n} voltage", d[0] / 200.0, "V")]
        out.append(Value("Short term fuel trim", trim(d[1]) if d[1] != 0xFF else "not used for trim",
                         "%" if d[1] != 0xFF else ""))
        return out
    return f


def _o2_wide_v(n):
    return lambda d: [Value(f"O2 sensor {n} lambda", 2.0 / 65536 * _u16(d), "λ"),
                      Value("Voltage", 8.0 / 65536 * _u16(d, 2), "V")]


def _o2_wide_ma(n):
    return lambda d: [Value(f"O2 sensor {n} lambda", 2.0 / 65536 * _u16(d), "λ"),
                      Value("Current", _u16(d, 2) / 256.0 - 128.0, "mA")]


def _o2_present2(d):
    names = [f"B{b}S{s}" for b in (1, 2) for s in (1, 2, 3, 4)]       # bank / sensor, language neutral
    return [Value("O2 sensors present", ", ".join(_bits_list(d[0], names)) or "-")]


def _o2_present4(d):
    names = [f"B{b}S{s}" for b in (1, 2, 3, 4) for s in (1, 2)]
    return [Value("O2 sensors present", ", ".join(_bits_list(d[0], names)) or "-")]


def _max_values(d):
    return [Value("Max fuel-air equivalence ratio", d[0], ""), Value("Max O2 sensor voltage", d[1], "V"),
            Value("Max O2 sensor current", d[2], "mA"), Value("Max intake manifold pressure", d[3] * 10, "kPa")]


def _torque_points(d):
    return [Value("Idle", d[0] - 125, "%")] + [Value(f"Engine point {i}", d[i] - 125, "%") for i in range(1, 5)]


def _sup(d):
    return d[0]


def _pair(label, unit, f, size=1, names=("A", "B"), count=2, sup_bit0=0):
    """A = support bits, then `count` sensors of `size` bytes each."""
    def g(d):
        out = []
        for i in range(count):
            off = 1 + i * size
            if off + size > len(d):
                break
            if not d[0] & (1 << (sup_bit0 + i)):
                continue
            raw = d[off] if size == 1 else _u16(d, off)
            out.append(Value(f"{label} {names[i]}", f(raw), unit))
        return out or [Value(label, "not supported", "")]
    return g


def _maf_ab(d):
    return _pair("MAF sensor", "g/s", lambda v: v / 32.0, 2)(d)


def _ect_ab(d):
    return _pair("Coolant temperature sensor", "°C", temp, 1, ("1", "2"))(d)


def _iat_multi(d):
    return _pair("Intake air temperature sensor", "°C", temp, 1, ("bank 1 sensor 1", "bank 1 sensor 2",
                                                                       "bank 1 sensor 3", "bank 2 sensor 1",
                                                                       "bank 2 sensor 2", "bank 2 sensor 3"), 6)(d)


def _egr_cmd(d):
    out = []
    if d[0] & 1:
        out.append(Value("Commanded EGR A duty cycle", pct(d[1]), "%"))
    if d[0] & 2:
        out.append(Value("Actual EGR A duty cycle", pct(d[2]), "%"))
    if d[0] & 4:
        out.append(Value("EGR A error", trim(d[3]), "%"))
    if d[0] & 8:
        out.append(Value("Commanded EGR B duty cycle", pct(d[4]), "%"))
    if d[0] & 16:
        out.append(Value("Actual EGR B duty cycle", pct(d[5]), "%"))
    if d[0] & 32:
        out.append(Value("EGR B error", trim(d[6]), "%"))
    return out or [Value("EGR", "not supported")]


def _cmd_actual(label_cmd, label_act):
    def f(d):
        out = []
        for i, side in enumerate(("A", "B")):
            if d[0] & (1 << (2 * i)):
                out.append(Value(f"{label_cmd} {side}", pct(d[1 + 2 * i]), "%"))
            if d[0] & (1 << (2 * i + 1)):
                out.append(Value(f"{label_act} {side}", pct(d[2 + 2 * i]), "%"))
        return out or [Value(label_cmd, "not supported")]
    return f


def _four_temps(label, names=("bank 1 sensor 1", "bank 1 sensor 2", "bank 2 sensor 1", "bank 2 sensor 2")):
    return _pair(label, "°C", temp, 1, names, 4)


def _rail_ctrl(d):
    out = []
    if d[0] & 1:
        out.append(Value("Commanded fuel rail pressure A", _u16(d, 1) * 10, "kPa"))
    if d[0] & 2:
        out.append(Value("Fuel rail pressure A", _u16(d, 3) * 10, "kPa"))
    if d[0] & 4:
        out.append(Value("Fuel temperature A", temp(d[5]), "°C"))
    if d[0] & 8:
        out.append(Value("Commanded fuel rail pressure B", _u16(d, 6) * 10, "kPa"))
    if d[0] & 16:
        out.append(Value("Fuel rail pressure B", _u16(d, 8) * 10, "kPa"))
    if d[0] & 32:
        out.append(Value("Fuel temperature B", temp(d[10]), "°C"))
    return out or [Value("Fuel pressure control", "not supported")]


def _inj_ctrl(d):
    out = []
    for i, lab in enumerate(("Commanded injection control pressure A", "Injection control pressure A",
                             "Commanded injection control pressure B", "Injection control pressure B")):
        if d[0] & (1 << i):
            out.append(Value(lab, _u16(d, 1 + 2 * i) * 10, "kPa"))
    return out or [Value("Injection pressure control", "not supported")]


def _boost(d):
    out = []
    for i, lab in enumerate(("Commanded boost pressure A", "Boost pressure sensor A",
                             "Commanded boost pressure B", "Boost pressure sensor B")):
        if d[0] & (1 << i):
            out.append(Value(lab, _u16(d, 1 + 2 * i) * 0.03125, "kPa"))
    return out or [Value("Boost pressure control", "not supported")]


def _vgt(d):
    return _cmd_actual("Commanded VGT position", "VGT position")(d[:5])


def _wastegate(d):
    return _cmd_actual("Commanded wastegate position", "Wastegate position")(d)


def _exh_press(d):
    return _pair("Exhaust pressure", "kPa", lambda v: v * 0.01, 2, ("bank 1", "bank 2"))(d)


def _turbo_rpm(d):
    return _pair("Turbocharger speed", "rpm", lambda v: v * 10, 2, ("A", "B"))(d)


def _turbo_temp(side):
    def f(d):
        out = []
        if d[0] & 1:
            out.append(Value(f"Turbo {side} compressor inlet temperature", temp(d[1]), "°C"))
        if d[0] & 2:
            out.append(Value(f"Turbo {side} compressor outlet temperature", temp(d[2]), "°C"))
        if d[0] & 4:
            out.append(Value(f"Turbo {side} turbine inlet temperature", _u16(d, 3) / 10.0 - 40, "°C"))
        if d[0] & 8:
            out.append(Value(f"Turbo {side} turbine outlet temperature", _u16(d, 5) / 10.0 - 40, "°C"))
        return out or [Value(f"Turbo {side} temperature", "not supported")]
    return f


def _egt(bank):
    return _pair(f"Exhaust gas temperature bank {bank}", "°C", lambda v: v / 10.0 - 40, 2,
                 ("sensor 1", "sensor 2", "sensor 3", "sensor 4"), 4)


def _dpf(bank):
    def f(d):
        out = []
        for i, lab in enumerate(("delta pressure", "inlet pressure", "outlet pressure")):
            if d[0] & (1 << i):
                out.append(Value(f"DPF bank {bank} {lab}", _u16(d, 1 + 2 * i) * 0.01, "kPa"))
        return out or [Value(f"DPF bank {bank}", "not supported")]
    return f


def _dpf_temp(d):
    return _pair("DPF temperature", "°C", lambda v: v / 10.0 - 40, 2,
                 ("bank 1 inlet", "bank 1 outlet", "bank 2 inlet", "bank 2 outlet"), 4)(d)


def _run_time(d):
    out = [Value("Total engine run time", _u32(d, 1), "s")]
    if len(d) >= 9:
        out.append(Value("Total idle run time", _u32(d, 5), "s"))
    if len(d) >= 13:
        out.append(Value("Total run time with PTO active", _u32(d, 9), "s"))
    return out


def _nox(d):
    return _pair("NOx sensor concentration", "ppm", lambda v: v, 2, ("sensor 1", "sensor 2"))(d)


def _reagent(d):
    out = [Value("Average reagent consumption", _u16(d, 1) * 0.005, "L/h"),
           Value("Average demanded reagent consumption", _u16(d, 3) * 0.005, "L/h"),
           Value("Reagent tank level", pct(d[5]), "%")]
    if len(d) >= 10:
        out.append(Value("NOx warning and inducement system run time", _u32(d, 6), "s"))
    return out


def _pm(d):
    return _pair("Particulate matter sensor", "mg/m³", lambda v: v * 0.0125, 2, ("1", "2"))(d)


def _map_ab(d):
    return _pair("Intake manifold absolute pressure", "kPa", lambda v: v * 0.03125, 2)(d)


def _gear(d):
    if not d[0] & 0x03:
        return [Value("Transmission gear", "not supported")]
    g = d[1] >> 4
    return [Value("Actual gear", g if g else "neutral / park", ""), Value("Gear ratio", _u16(d, 2) / 1000.0, "")]


def _def_dosing(d):
    return [Value("Commanded DEF dosing", d[1] / 2.0, "%")]


def _odometer(d):
    return [Value("Odometer", _u32(d) / 10.0, "km")]


def _abs_switch(d):
    if not d[0] & 1:
        return [Value("ABS disable switch", "not supported")]
    return [Value("ABS disable switch", "ON (ABS disabled)" if d[1] & 1 else "OFF", "")]


def _fuel_rates(d):
    return [Value("Engine fuel rate", _u16(d) * 0.02, "g/s"), Value("Vehicle fuel rate", _u16(d, 2) * 0.02, "g/s")]


def _aux_io(d):
    names = ["Power take off (PTO) status", "Automatic transmission neutral drive status",
             "Manual transmission neutral gear status", "Glow plug lamp status"]
    out = []
    for i, n in enumerate(names):
        if d[0] & (1 << i):
            out.append(Value(n, "active" if d[1] & (1 << i) else "inactive"))
    return out or [Value("Auxiliary input / output", "not supported")]


def _ethanol(d):
    return [Value("Ethanol fuel", pct(d[0]), "%")]


def _sec_o2_trim(b1, b2):
    return lambda d: [Value(f"Short term secondary O2 trim bank {b1}", trim(d[0]), "%"),
                      Value(f"Short term secondary O2 trim bank {b2}", trim(d[1]), "%")]


def _lt_sec_o2_trim(b1, b2):
    return lambda d: [Value(f"Long term secondary O2 trim bank {b1}", trim(d[0]), "%"),
                      Value(f"Long term secondary O2 trim bank {b2}", trim(d[1]), "%")]


def _raw(d):
    return [Value("Raw data", " ".join(f"{b:02X}" for b in d) or "-", "")]


# ----------------------------------------------------------------------------------------------- the table
P: dict[int, Pid] = {}


def _add(pid, length, name, unit="", lo=0.0, hi=100.0, fn=None, kind="num", short="", group="Engine", raw=False):
    P[pid] = Pid(pid, length, name, unit, lo, hi, fn or _raw, raw or fn is None, "raw" if fn is None else kind,
                 short or name, group)


for _b in range(0x00, 0xE0, 0x20):
    _add(_b, 4, f"PIDs supported [{_b + 1:02X} - {_b + 0x20:02X}]", fn=_bitmap(_b), kind="bitmap", group="Support")

_add(0x01, 4, "Monitor status since DTCs cleared", fn=_monitor, kind="bits", short="Monitor status", group="Status")
_add(0x02, 2, "DTC that caused the freeze frame", fn=lambda d: [Value("Freeze frame DTC", dtc_text(d[0], d[1])
                                                                     if (d[0] or d[1]) else "none")],
     kind="dtc", short="Freeze DTC", group="Status")
_add(0x03, 2, "Fuel system status", fn=_fuel_system, kind="enum", short="Fuel system", group="Fuel")
_add(0x04, 1, "Calculated engine load", "%", 0, 100, _one("Calculated engine load", "%", lambda d: pct(d[0])),
     short="Load")
_add(0x05, 1, "Engine coolant temperature", "°C", -40, 215, _one("Engine coolant temperature", "°C",
                                                                   lambda d: temp(d[0])), short="Coolant")
for _i, (_n, _s) in enumerate((("Short term fuel trim - Bank 1", "STFT B1"), ("Long term fuel trim - Bank 1", "LTFT B1"),
                               ("Short term fuel trim - Bank 2", "STFT B2"), ("Long term fuel trim - Bank 2", "LTFT B2"))):
    _add(0x06 + _i, 1, _n, "%", -100, 99.2, _one(_n, "%", lambda d: trim(d[0])), short=_s, group="Fuel")
_add(0x0A, 1, "Fuel pressure (gauge pressure)", "kPa", 0, 765, _one("Fuel pressure", "kPa", lambda d: 3 * d[0]),
     short="Fuel press", group="Fuel")
_add(0x0B, 1, "Intake manifold absolute pressure", "kPa", 0, 255, _one("Intake manifold absolute pressure", "kPa",
                                                                         lambda d: d[0]), short="MAP", group="Air")
_add(0x0C, 2, "Engine speed", "rpm", 0, 8000, _one("Engine speed", "rpm", lambda d: _u16(d) / 4.0), short="RPM")
_add(0x0D, 1, "Vehicle speed", "km/h", 0, 255, _one("Vehicle speed", "km/h", lambda d: d[0]), short="Speed",
     group="Vehicle")
_add(0x0E, 1, "Timing advance", "° before TDC", -64, 63.5, _one("Timing advance", "° before TDC",
                                                                  lambda d: d[0] / 2.0 - 64), short="Timing")
_add(0x0F, 1, "Intake air temperature", "°C", -40, 215, _one("Intake air temperature", "°C", lambda d: temp(d[0])),
     short="IAT", group="Air")
_add(0x10, 2, "Mass air flow sensor (MAF) air flow rate", "g/s", 0, 655.35,
     _one("Mass air flow rate", "g/s", lambda d: _u16(d) / 100.0), short="MAF", group="Air")
_add(0x11, 1, "Throttle position", "%", 0, 100, _one("Throttle position", "%", lambda d: pct(d[0])), short="Throttle",
     group="Air")
_add(0x12, 1, "Commanded secondary air status", fn=lambda d: [Value("Secondary air", SECONDARY_AIR.get(d[0],
                                                                                                        f"0x{d[0]:02X}"))],
     kind="enum", group="Emissions")
_add(0x13, 1, "Oxygen sensors present (in 2 banks)", fn=_o2_present2, kind="bits", group="Oxygen sensors")
for _i in range(8):
    _add(0x14 + _i, 2, f"Oxygen sensor {_i + 1} (narrow band): voltage, short term fuel trim", "V", 0, 1.275,
         _o2_narrow(_i + 1), short=f"O2 S{_i + 1}", group="Oxygen sensors")
_add(0x1C, 1, "OBD standards this vehicle conforms to", fn=lambda d: [Value("OBD standard", OBD_STANDARDS.get(
    d[0], f"code {d[0]}"))], kind="enum", group="Status")
_add(0x1D, 1, "Oxygen sensors present (in 4 banks)", fn=_o2_present4, kind="bits", group="Oxygen sensors")
_add(0x1E, 1, "Auxiliary input status", fn=lambda d: [Value("Power take off (PTO)", "active" if d[0] & 1 else
                                                            "inactive")], kind="enum", group="Vehicle")
_add(0x1F, 2, "Run time since engine start", "s", 0, 65535, _one("Run time since engine start", "s", lambda d: _u16(d)),
     short="Run time", group="Vehicle")
_add(0x21, 2, "Distance traveled with malfunction indicator lamp (MIL) on", "km", 0, 65535,
     _one("Distance with MIL on", "km", lambda d: _u16(d)), short="Dist MIL on", group="Status")
_add(0x22, 2, "Fuel rail pressure (relative to manifold vacuum)", "kPa", 0, 5177.265,
     _one("Fuel rail pressure", "kPa", lambda d: 0.079 * _u16(d)), short="Rail press", group="Fuel")
_add(0x23, 2, "Fuel rail gauge pressure (diesel, or gasoline direct injection)", "kPa", 0, 655350,
     _one("Fuel rail gauge pressure", "kPa", lambda d: 10 * _u16(d)), short="Rail gauge", group="Fuel")
for _i in range(8):
    _add(0x24 + _i, 4, f"Oxygen sensor {_i + 1} (wide range): air-fuel equivalence ratio, voltage", "λ", 0, 2,
         _o2_wide_v(_i + 1), short=f"O2 S{_i + 1} λ", group="Oxygen sensors")
_add(0x2C, 1, "Commanded EGR", "%", 0, 100, _one("Commanded EGR", "%", lambda d: pct(d[0])), short="EGR cmd",
     group="Emissions")
_add(0x2D, 1, "EGR error", "%", -100, 99.2, _one("EGR error", "%", lambda d: trim(d[0])), short="EGR error",
     group="Emissions")
_add(0x2E, 1, "Commanded evaporative purge", "%", 0, 100, _one("Commanded evaporative purge", "%", lambda d: pct(d[0])),
     short="EVAP purge", group="Emissions")
_add(0x2F, 1, "Fuel tank level input", "%", 0, 100, _one("Fuel tank level", "%", lambda d: pct(d[0])),
     short="Fuel level", group="Fuel")
_add(0x30, 1, "Warm-ups since codes cleared", "", 0, 255, _one("Warm-ups since codes cleared", "", lambda d: d[0]),
     short="Warm-ups", group="Status")
_add(0x31, 2, "Distance traveled since codes cleared", "km", 0, 65535,
     _one("Distance since codes cleared", "km", lambda d: _u16(d)), short="Dist cleared", group="Status")
_add(0x32, 2, "Evap. system vapor pressure", "Pa", -8192, 8191.75,
     _one("Evap. system vapor pressure", "Pa", lambda d: _s16(d) / 4.0), short="EVAP press", group="Emissions")
_add(0x33, 1, "Absolute barometric pressure", "kPa", 0, 255, _one("Absolute barometric pressure", "kPa",
                                                                    lambda d: d[0]), short="Baro", group="Air")
for _i in range(8):
    _add(0x34 + _i, 4, f"Oxygen sensor {_i + 1} (wide range): air-fuel equivalence ratio, current", "λ", 0, 2,
         _o2_wide_ma(_i + 1), short=f"O2 S{_i + 1} λ/mA", group="Oxygen sensors")
for _i, _n in enumerate(("Catalyst temperature: Bank 1, Sensor 1", "Catalyst temperature: Bank 2, Sensor 1",
                         "Catalyst temperature: Bank 1, Sensor 2", "Catalyst temperature: Bank 2, Sensor 2")):
    _add(0x3C + _i, 2, _n, "°C", -40, 1000, _one(_n, "°C", lambda d: _u16(d) / 10.0 - 40),
         short=("Cat B1S1", "Cat B2S1", "Cat B1S2", "Cat B2S2")[_i], group="Emissions")
_add(0x41, 4, "Monitor status this drive cycle", fn=_monitor_drive, kind="bits", short="Monitors this cycle",
     group="Status")
_add(0x42, 2, "Control module voltage", "V", 0, 18, _one("Control module voltage", "V", lambda d: _u16(d) / 1000.0),
     short="Voltage", group="Vehicle")
_add(0x43, 2, "Absolute load value", "%", 0, 100, _one("Absolute load value", "%", lambda d: _u16(d) * 100.0 / 255),
     short="Abs load")
_add(0x44, 2, "Commanded air-fuel equivalence ratio (lambda)", "λ", 0, 2,
     _one("Commanded air-fuel equivalence ratio", "λ", lambda d: 2.0 / 65536 * _u16(d)), short="Cmd λ", group="Fuel")
_add(0x45, 1, "Relative throttle position", "%", 0, 100, _one("Relative throttle position", "%", lambda d: pct(d[0])),
     short="Rel throttle", group="Air")
_add(0x46, 1, "Ambient air temperature", "°C", -40, 215, _one("Ambient air temperature", "°C", lambda d: temp(d[0])),
     short="Ambient", group="Vehicle")
for _i, (_n, _s) in enumerate((("Absolute throttle position B", "Throttle B"), ("Absolute throttle position C", "Throttle C"),
                               ("Accelerator pedal position D", "Pedal D"), ("Accelerator pedal position E", "Pedal E"),
                               ("Accelerator pedal position F", "Pedal F"))):
    _add(0x47 + _i, 1, _n, "%", 0, 100, _one(_n, "%", lambda d: pct(d[0])), short=_s, group="Air")
_add(0x4C, 1, "Commanded throttle actuator", "%", 0, 100, _one("Commanded throttle actuator", "%", lambda d: pct(d[0])),
     short="Throttle cmd", group="Air")
_add(0x4D, 2, "Time run with MIL on", "min", 0, 65535, _one("Time run with MIL on", "min", lambda d: _u16(d)),
     short="Time MIL on", group="Status")
_add(0x4E, 2, "Time since trouble codes cleared", "min", 0, 65535,
     _one("Time since trouble codes cleared", "min", lambda d: _u16(d)), short="Time cleared", group="Status")
_add(0x4F, 4, "Maximum value for equivalence ratio, O2 voltage, O2 current and intake manifold pressure",
     fn=_max_values, kind="num", group="Oxygen sensors", short="Max values")
_add(0x50, 4, "Maximum value for air flow rate from mass air flow sensor", "g/s", 0, 2550,
     _one("Maximum air flow rate", "g/s", lambda d: d[0] * 10), short="Max MAF", group="Air")
_add(0x51, 1, "Fuel type", fn=lambda d: [Value("Fuel type", FUEL_TYPES.get(d[0], f"code {d[0]}"))], kind="enum",
     group="Fuel")
_add(0x52, 1, "Ethanol fuel %", "%", 0, 100, _ethanol, short="Ethanol", group="Fuel")
_add(0x53, 2, "Absolute evap system vapor pressure", "kPa", 0, 327.675,
     _one("Absolute evap system vapor pressure", "kPa", lambda d: _u16(d) / 200.0), short="EVAP abs", group="Emissions")
_add(0x54, 2, "Evap system vapor pressure", "Pa", -32768, 32767,
     _one("Evap system vapor pressure", "Pa", lambda d: _s16(d)), short="EVAP press 2", group="Emissions")
_add(0x55, 2, "Short term secondary oxygen sensor trim, bank 1 and bank 3", "%", -100, 99.2, _sec_o2_trim(1, 3),
     short="STST B1/B3", group="Oxygen sensors")
_add(0x56, 2, "Long term secondary oxygen sensor trim, bank 1 and bank 3", "%", -100, 99.2, _lt_sec_o2_trim(1, 3),
     short="LTST B1/B3", group="Oxygen sensors")
_add(0x57, 2, "Short term secondary oxygen sensor trim, bank 2 and bank 4", "%", -100, 99.2, _sec_o2_trim(2, 4),
     short="STST B2/B4", group="Oxygen sensors")
_add(0x58, 2, "Long term secondary oxygen sensor trim, bank 2 and bank 4", "%", -100, 99.2, _lt_sec_o2_trim(2, 4),
     short="LTST B2/B4", group="Oxygen sensors")
_add(0x59, 2, "Fuel rail absolute pressure", "kPa", 0, 655350, _one("Fuel rail absolute pressure", "kPa",
                                                                      lambda d: 10 * _u16(d)), short="Rail abs",
     group="Fuel")
_add(0x5A, 1, "Relative accelerator pedal position", "%", 0, 100,
     _one("Relative accelerator pedal position", "%", lambda d: pct(d[0])), short="Rel pedal", group="Air")
_add(0x5B, 1, "Hybrid battery pack remaining life", "%", 0, 100,
     _one("Hybrid battery pack remaining life", "%", lambda d: pct(d[0])), short="Hybrid batt", group="Hybrid / EV")
_add(0x5C, 1, "Engine oil temperature", "°C", -40, 210, _one("Engine oil temperature", "°C", lambda d: temp(d[0])),
     short="Oil temp")
_add(0x5D, 2, "Fuel injection timing", "°", -210, 301.992,
     _one("Fuel injection timing", "°", lambda d: _u16(d) / 128.0 - 210), short="Inj timing", group="Fuel")
_add(0x5E, 2, "Engine fuel rate", "L/h", 0, 3276.75, _one("Engine fuel rate", "L/h", lambda d: _u16(d) / 20.0),
     short="Fuel rate", group="Fuel")
_add(0x5F, 1, "Emission requirements to which vehicle is designed",
     fn=lambda d: [Value("Emission requirements", EMISSION_REQ.get(d[0], f"code 0x{d[0]:02X}"))], kind="enum",
     group="Status")
_add(0x61, 1, "Driver's demand engine - percent torque", "%", -125, 130,
     _one("Driver's demand engine torque", "%", lambda d: d[0] - 125), short="Demand torque", group="Torque")
_add(0x62, 1, "Actual engine - percent torque", "%", -125, 130,
     _one("Actual engine torque", "%", lambda d: d[0] - 125), short="Actual torque", group="Torque")
_add(0x63, 2, "Engine reference torque", "Nm", 0, 65535, _one("Engine reference torque", "Nm", lambda d: _u16(d)),
     short="Ref torque", group="Torque")
_add(0x64, 5, "Engine percent torque data", "%", -125, 130, _torque_points, short="Torque data", group="Torque")
_add(0x65, 2, "Auxiliary input / output supported", fn=_aux_io, kind="bits", group="Vehicle")
_add(0x66, 5, "Mass air flow sensor", "g/s", 0, 2048, _maf_ab, short="MAF A/B", group="Air")
_add(0x67, 3, "Engine coolant temperature (sensors 1 and 2)", "°C", -40, 215, _ect_ab, short="Coolant 1/2")
_add(0x68, 7, "Intake air temperature sensor", "°C", -40, 215, _iat_multi, short="IAT sensors", group="Air")
_add(0x69, 7, "Commanded EGR and EGR error", "%", 0, 100, _egr_cmd, short="EGR A/B", group="Emissions")
_add(0x6A, 5, "Commanded diesel intake air flow control and relative intake air flow position", "%", 0, 100,
     _cmd_actual("Commanded intake air flow control", "Relative intake air flow position"), short="Intake flow",
     group="Air")
_add(0x6B, 5, "Exhaust gas recirculation temperature", "°C", -40, 215, _four_temps("EGR temperature"),
     short="EGR temp", group="Emissions")
_add(0x6C, 5, "Commanded throttle actuator control and relative throttle position", "%", 0, 100,
     _cmd_actual("Commanded throttle actuator", "Relative throttle position"), short="Throttle A/B", group="Air")
_add(0x6D, 11, "Fuel pressure control system", "kPa", 0, 655350, _rail_ctrl, short="Fuel press ctrl", group="Fuel")
_add(0x6E, 9, "Injection pressure control system", "kPa", 0, 655350, _inj_ctrl, short="Inj press ctrl",
     group="Fuel")
_add(0x6F, 3, "Turbocharger compressor inlet pressure", "kPa", 0, 255,
     _pair("Turbocharger compressor inlet pressure", "kPa", lambda v: v, 1), short="Turbo inlet", group="Turbo")
_add(0x70, 10, "Boost pressure control", "kPa", 0, 2048, _boost, short="Boost", group="Turbo")
_add(0x71, 6, "Variable geometry turbo (VGT) control", "%", 0, 100, _vgt, short="VGT", group="Turbo")
_add(0x72, 5, "Wastegate control", "%", 0, 100, _wastegate, short="Wastegate", group="Turbo")
_add(0x73, 5, "Exhaust pressure", "kPa", 0, 655.35, _exh_press, short="Exh press", group="Emissions")
_add(0x74, 5, "Turbocharger RPM", "rpm", 0, 655350, _turbo_rpm, short="Turbo RPM", group="Turbo")
_add(0x75, 7, "Turbocharger temperature (turbo A)", "°C", -40, 215, _turbo_temp("A"), short="Turbo A temp",
     group="Turbo")
_add(0x76, 7, "Turbocharger temperature (turbo B)", "°C", -40, 215, _turbo_temp("B"), short="Turbo B temp",
     group="Turbo")
_add(0x77, 5, "Charge air cooler temperature (CACT)", "°C", -40, 215, _four_temps("Charge air cooler temperature"),
     short="CAC temp", group="Turbo")
_add(0x78, 9, "Exhaust gas temperature (EGT) bank 1", "°C", -40, 1000, _egt(1), short="EGT B1", group="Emissions")
_add(0x79, 9, "Exhaust gas temperature (EGT) bank 2", "°C", -40, 1000, _egt(2), short="EGT B2", group="Emissions")
_add(0x7A, 7, "Diesel particulate filter (DPF) bank 1", "kPa", 0, 655.35, _dpf(1), short="DPF B1", group="Emissions")
_add(0x7B, 7, "Diesel particulate filter (DPF) bank 2", "kPa", 0, 655.35, _dpf(2), short="DPF B2", group="Emissions")
_add(0x7C, 9, "Diesel particulate filter (DPF) temperature", "°C", -40, 1000, _dpf_temp, short="DPF temp",
     group="Emissions")
_add(0x7D, 1, "NOx NTE (not-to-exceed) control area status", kind="raw", group="Emissions")
_add(0x7E, 1, "PM NTE (not-to-exceed) control area status", kind="raw", group="Emissions")
_add(0x7F, 13, "Engine run time", "s", 0, 4294967295, _run_time, short="Engine run time", group="Vehicle")
_add(0x81, 21, "Engine run time for auxiliary emissions control device (AECD) #1 - #5", group="Emissions")
_add(0x82, 21, "Engine run time for auxiliary emissions control device (AECD) #6 - #10", group="Emissions")
_add(0x83, 9, "NOx sensor", "ppm", 0, 65535, _nox, short="NOx", group="Emissions")
_add(0x84, 1, "Manifold surface temperature", "°C", -40, 215,
     _one("Manifold surface temperature", "°C", lambda d: temp(d[0])), short="Manifold temp", group="Air")
_add(0x85, 10, "NOx reagent system", "L/h", 0, 327.675, _reagent, short="Reagent", group="Emissions")
_add(0x86, 5, "Particulate matter (PM) sensor", "mg/m³", 0, 819.1875, _pm, short="PM sensor", group="Emissions")
_add(0x87, 5, "Intake manifold absolute pressure (sensors A and B)", "kPa", 0, 2048, _map_ab, short="MAP A/B",
     group="Air")
_add(0x88, 13, "SCR induce system", group="Emissions")
_add(0x89, 41, "Run time for auxiliary emissions control device (AECD) #11 - #15", group="Emissions")
_add(0x8A, 41, "Run time for auxiliary emissions control device (AECD) #16 - #20", group="Emissions")
_add(0x8B, 7, "Diesel aftertreatment", group="Emissions")
_add(0x8C, 17, "O2 sensor (wide range)", group="Oxygen sensors")
_add(0x8D, 1, "Throttle position G", "%", 0, 100, _one("Throttle position G", "%", lambda d: pct(d[0])),
     short="Throttle G", group="Air")
_add(0x8E, 1, "Engine friction - percent torque", "%", -125, 130,
     _one("Engine friction torque", "%", lambda d: d[0] - 125), short="Friction torque", group="Torque")
_add(0x8F, 7, "Particulate matter (PM) sensor bank 1 and 2", group="Emissions")
_add(0x90, 3, "WWH-OBD vehicle OBD system information", group="Status")
_add(0x91, 5, "WWH-OBD vehicle OBD system information (ECU OBD system)", group="Status")
_add(0x92, 2, "Fuel system control", group="Fuel")
_add(0x93, 3, "WWH-OBD vehicle OBD counters support", group="Status")
_add(0x94, 12, "NOx warning and inducement system", group="Emissions")
_add(0x98, 9, "Exhaust gas temperature sensor (bank 1, sensors 5 - 8)", group="Emissions")
_add(0x99, 9, "Exhaust gas temperature sensor (bank 2, sensors 5 - 8)", group="Emissions")
_add(0x9A, 6, "Hybrid / EV vehicle system data, battery, voltage", group="Hybrid / EV")
_add(0x9B, 4, "Diesel exhaust fluid sensor data", group="Emissions")
_add(0x9C, 17, "O2 sensor data", group="Oxygen sensors")
_add(0x9D, 4, "Engine fuel rate (engine and vehicle)", "g/s", 0, 1310.7, _fuel_rates, short="Fuel rate g/s",
     group="Fuel")
_add(0x9E, 2, "Engine exhaust flow rate", "kg/h", 0, 13107,
     _one("Engine exhaust flow rate", "kg/h", lambda d: _u16(d) * 0.2), short="Exhaust flow", group="Emissions")
_add(0x9F, 9, "Fuel system percentage use", group="Fuel")
_add(0xA1, 9, "NOx sensor corrected data", group="Emissions")
_add(0xA2, 2, "Cylinder fuel rate", "mg/stroke", 0, 2048,
     _one("Cylinder fuel rate", "mg/stroke", lambda d: _u16(d) / 32.0), short="Cyl fuel", group="Fuel")
_add(0xA3, 9, "Evap system vapor pressure (extended)", group="Emissions")
_add(0xA4, 4, "Transmission actual gear", "", 0, 10, _gear, short="Gear", group="Vehicle")
_add(0xA5, 4, "Commanded diesel exhaust fluid (DEF) dosing", "%", 0, 127.5, _def_dosing, short="DEF dosing",
     group="Emissions")
_add(0xA6, 4, "Odometer", "km", 0, 429496729.5, _odometer, short="Odometer", group="Vehicle")
_add(0xA7, 4, "NOx sensor concentration sensors 3 and 4", group="Emissions")
_add(0xA8, 4, "NOx sensor corrected concentration sensors 3 and 4", group="Emissions")
_add(0xA9, 4, "ABS disable switch state", fn=_abs_switch, kind="enum", group="Vehicle")
for _p in range(0xC1, 0xC9):
    _add(_p, 0, f"PID {_p:02X} (reserved / not standardised in public sources)", group="Support")
for _p in range(0x00, 0xC9):           # gaps of the table (0x95-0x97, 0xAA-0xBF) are reserved
    if _p not in P:
        _add(_p, 0, f"PID {_p:02X} (reserved)", group="Support")

BITMAP_PIDS = tuple(range(0x00, 0xE0, 0x20))
DIAG_PIDS = (0x01, 0x02, 0x41)      # status PIDs (not graphed)


def get(pid: int) -> Pid:
    return P.get(pid) or Pid(pid, 0, f"PID {pid:02X}", fn=_raw, raw=True, kind="raw", short=f"PID {pid:02X}")


def decode(pid: int, data: bytes) -> list[Value]:
    p = get(pid)
    if p.length and len(data) < p.length:
        return [Value("Raw data (short response)", " ".join(f"{b:02X}" for b in data) or "-", "")]
    try:
        vals = p.fn(bytes(data[:p.length] if p.length else data))
    except Exception:  # noqa: BLE001 - a malformed answer must never crash the scan tool
        return _raw(data)
    return vals


def main_value(pid: int, data: bytes):
    """The PID's main value as a float (None for text / bit fields) - what gauges and the graph show."""
    vals = decode(pid, data)
    if not vals:
        return None
    v = vals[0].value
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def supported_from_bitmap(base: int, data: bytes) -> set[int]:
    bits = _u32(data)
    return {base + i + 1 for i in range(32) if bits & (1 << (31 - i))}


def is_graphable(pid: int) -> bool:
    p = get(pid)
    return p.kind == "num" and not p.raw and pid not in BITMAP_PIDS and pid not in DIAG_PIDS


def split_multi(data: bytes) -> list[tuple[int, bytes]]:
    """Payload of a multi-PID mode 01 answer (after 0x41): PID data PID data ... -> [(pid, data)]."""
    out, i = [], 0
    while i < len(data):
        pid = data[i]
        n = get(pid).length
        if n <= 0:                                     # unknown length: the rest belongs to it
            out.append((pid, bytes(data[i + 1:])))
            break
        out.append((pid, bytes(data[i + 1:i + 1 + n])))
        i += 1 + n
    return out
