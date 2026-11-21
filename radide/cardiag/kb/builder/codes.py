"""The generic SAE J2012 powertrain codes (P0xxx, P2xxx, P34xx) as rows: code -> title, component, fault type.

Code titles are standard (facts); everything descriptive is generated from components.py / faults.py or written in
special.py. A row: dict(code, title_en, comp, fault, base_ar, q_ar)."""
from __future__ import annotations

import re

ROWS: list[dict] = []
_SEEN: set[str] = set()


def q_ar(q: str) -> str:
    """Arabic for a title qualifier such as ' (Bank 1 Sensor 2)' / ' - Cylinder 3'."""
    s = q
    for en, ar in (("Bank 1 or Single Sensor", "البنك 1 أو حساس واحد"), ("Bank 2", "البنك 2"), ("Bank 1", "البنك 1"),
                   ("Sensor 1", "الحساس 1"), ("Sensor 2", "الحساس 2"), ("Sensor 3", "الحساس 3"),
                   ("Sensor A", "الحساس A"), ("Sensor B", "الحساس B"), ("Unit 1", "الوحدة 1"),
                   ("Cylinder", "الأسطوانة"), ("Group", "المجموعة"), ("Single Sensor", "حساس واحد"),
                   ("Not Specified", "غير محددة")):
        s = s.replace(en, ar)
    return s


def R(code, comp, fault, base, suffix=None, q="", base_ar=None):
    if code in _SEEN:
        raise ValueError(f"duplicate {code}")
    _SEEN.add(code)
    from .faults import FAULTS
    sfx = suffix if suffix is not None else FAULTS[fault]["en"] if fault in FAULTS else ""
    title = (base + (" " + sfx if sfx else "") + q).strip()
    ROWS.append(dict(code=code, title_en=title, comp=comp, fault=fault, base_ar=base_ar, q_ar=q_ar(q), q=q,
                     sfx=sfx))


def code(n: int, prefix="P") -> str:
    return f"{prefix}{n:04X}" if prefix == "U" and False else f"{prefix}{n:04d}"


def fam(start: int, comp: str, base: str, faults=("circuit", "rp", "low", "high", "int"), q="", base_ar=None,
        suffixes=None):
    for i, f in enumerate(faults):
        R(code(start + i), comp, f, base, suffix=(suffixes[i] if suffixes else None), q=q, base_ar=base_ar)


def ctrl(start: int, comp: str, base: str, q="", base_ar=None, kinds=("open", "low", "high")):
    sfx = {"open": "Control Circuit/Open", "low": "Control Circuit Low", "high": "Control Circuit High",
           "rp": "Control Circuit Range/Performance", "circuit": "Control Circuit"}
    for i, f in enumerate(kinds):
        R(code(start + i), comp, f, base, suffix=sfx[f], q=q, base_ar=base_ar)


# ---------------------------------------------------------------- P0000 - P0099
R("P0001", "fvr", "open", "Fuel Volume Regulator", "Control Circuit/Open")
R("P0002", "fvr", "rp", "Fuel Volume Regulator", "Control Circuit Range/Performance")
R("P0003", "fvr", "low", "Fuel Volume Regulator", "Control Circuit Low")
R("P0004", "fvr", "high", "Fuel Volume Regulator", "Control Circuit High")
ctrl(5, "fso", "Fuel Shutoff Valve \"A\"")
R("P0008", "vvt", "special", "Engine Position System Performance", "", q=" (Bank 1)")
R("P0009", "vvt", "special", "Engine Position System Performance", "", q=" (Bank 2)")
for start, letter, bank in ((10, "A", 1), (13, "B", 1), (20, "A", 2), (23, "B", 2)):
    R(code(start), "vvt", "circuit", f"\"{letter}\" Camshaft Position Actuator", "Circuit", q=f" (Bank {bank})")
    R(code(start + 1), "vvt", "special", f"\"{letter}\" Camshaft Position", "- Timing Over-Advanced or System Performance",
      q=f" (Bank {bank})")
    R(code(start + 2), "vvt", "special", f"\"{letter}\" Camshaft Position", "- Timing Over-Retarded", q=f" (Bank {bank})")
for i, (b, s) in enumerate(((1, "A"), (1, "B"), (2, "A"), (2, "B"))):
    R(code(16 + i), "vvt", "special", "Crankshaft Position - Camshaft Position Correlation", "", q=f" (Bank {b} Sensor {s})")
R("P0026", "ivs", "rp", "Intake Valve Control Solenoid", q=" (Bank 1)")
R("P0027", "evs", "rp", "Exhaust Valve Control Solenoid", q=" (Bank 1)")
R("P0028", "ivs", "rp", "Intake Valve Control Solenoid", q=" (Bank 2)")
R("P0029", "evs", "rp", "Exhaust Valve Control Solenoid", q=" (Bank 2)")
for start, b, s in ((30, 1, 1), (36, 1, 2), (42, 1, 3), (50, 2, 1), (56, 2, 2), (62, 2, 3)):
    R(code(start), "ho2s_heater", "heater", "HO2S Heater Control", "Circuit", q=f" (Bank {b} Sensor {s})")
    R(code(start + 1), "ho2s_heater", "low", "HO2S Heater Control", "Circuit Low", q=f" (Bank {b} Sensor {s})")
    R(code(start + 2), "ho2s_heater", "high", "HO2S Heater Control", "Circuit High", q=f" (Bank {b} Sensor {s})")
R("P0033", "turbo_bypass", "circuit", "Turbo/Super Charger Bypass Valve", "Control Circuit")
R("P0034", "turbo_bypass", "low", "Turbo/Super Charger Bypass Valve", "Control Circuit Low")
R("P0035", "turbo_bypass", "high", "Turbo/Super Charger Bypass Valve", "Control Circuit High")
R("P0039", "turbo_bypass", "rp", "Turbo/Super Charger Bypass Valve", "Control Circuit Range/Performance")
R("P0040", "o2", "special", "O2 Sensor Signals Swapped", "Bank 1 Sensor 1 / Bank 2 Sensor 1")
R("P0041", "o2", "special", "O2 Sensor Signals Swapped", "Bank 1 Sensor 2 / Bank 2 Sensor 2")
R("P0045", "boost_ctrl", "open", "Turbo/Super Charger Boost Control \"A\"", "Circuit/Open")
R("P0046", "boost_ctrl", "rp", "Turbo/Super Charger Boost Control \"A\"", "Circuit Range/Performance")
R("P0047", "boost_ctrl", "low", "Turbo/Super Charger Boost Control \"A\"", "Circuit Low")
R("P0048", "boost_ctrl", "high", "Turbo/Super Charger Boost Control \"A\"", "Circuit High")
R("P0049", "boost_ctrl", "special", "Turbo/Super Charger Turbine Overspeed", "")
for c, b, s in ((53, 1, 1), (54, 1, 2), (55, 1, 3), (59, 2, 1), (60, 2, 2), (61, 2, 3)):
    R(code(c), "ho2s_heater", "heater_res", "HO2S", "Heater Resistance", q=f" (Bank {b} Sensor {s})")
R("P0065", "air_assist_inj", "rp", "Air Assisted Injector Control", "Range/Performance")
R("P0066", "air_assist_inj", "low", "Air Assisted Injector Control", "Circuit or Circuit Low")
R("P0067", "air_assist_inj", "high", "Air Assisted Injector Control", "Circuit High")
R("P0068", "map", "special", "MAP/MAF - Throttle Position Correlation", "")
R("P0069", "map", "special", "Manifold Absolute Pressure - Barometric Pressure Correlation", "")
fam(70, "aat", "Ambient Air Temperature Sensor")
for start, comp, base, bank in ((75, "ivs", "Intake Valve Control Solenoid", 1), (78, "evs", "Exhaust Valve Control Solenoid", 1),
                                (81, "ivs", "Intake Valve Control Solenoid", 2), (84, "evs", "Exhaust Valve Control Solenoid", 2)):
    fam(start, comp, base, ("circuit", "low", "high"), q=f" (Bank {bank})")
R("P0087", "frp", "special", "Fuel Rail/System Pressure", "- Too Low")
R("P0088", "frp", "special", "Fuel Rail/System Pressure", "- Too High")
R("P0089", "fpr1", "perf", "Fuel Pressure Regulator 1", "Performance")
ctrl(90, "fpr1", "Fuel Pressure Regulator 1", kinds=("circuit", "low", "high"))
R("P0093", "frp", "special", "Fuel System Leak Detected", "- Large Leak")
R("P0094", "frp", "special", "Fuel System Leak Detected", "- Small Leak")
fam(95, "iat2", "Intake Air Temperature Sensor 2", suffixes=("Circuit", "Circuit Range/Performance", "Circuit Low",
                                                              "Circuit High", "Circuit Intermittent/Erratic"))
# ---------------------------------------------------------------- P0100 - P0199
fam(100, "maf", "Mass or Volume Air Flow \"A\"")
fam(105, "map", "Manifold Absolute Pressure/Barometric Pressure")
fam(110, "iat", "Intake Air Temperature Sensor 1", q=" (Bank 1)")
fam(115, "ect", "Engine Coolant Temperature Sensor 1")
fam(120, "tps_A", "Throttle/Pedal Position Sensor/Switch \"A\"")
R("P0125", "ect", "special", "Insufficient Coolant Temperature for Closed Loop Fuel Control", "")
R("P0126", "ect", "special", "Insufficient Coolant Temperature for Stable Operation", "")
R("P0127", "iat", "special", "Intake Air Temperature Too High", "")
R("P0128", "ect", "special", "Coolant Thermostat (Coolant Temperature Below Thermostat Regulating Temperature)", "")
R("P0129", "baro", "special", "Barometric Pressure Too Low", "")
for start, b, s in ((130, 1, 1), (136, 1, 2), (142, 1, 3), (150, 2, 1), (156, 2, 2), (162, 2, 3)):
    q = f" (Bank {b} Sensor {s})"
    R(code(start), "o2", "circuit", "O2 Sensor", "Circuit", q=q)
    R(code(start + 1), "o2", "o2_low", "O2 Sensor", q=q)
    R(code(start + 2), "o2", "o2_high", "O2 Sensor", q=q)
    R(code(start + 3), "o2", "o2_slow", "O2 Sensor", q=q)
    R(code(start + 4), "o2", "o2_noact", "O2 Sensor", q=q)
    R(code(start + 5), "ho2s_heater", "heater", "O2 Sensor", q=q)
R("P0148", "fvr", "special", "Fuel Delivery Error", "")
R("P0149", "inj_timing", "special", "Fuel Timing Error", "")
R("P0168", "fts_A", "special", "Fuel Temperature Too High", "")
R("P0169", "fcs", "special", "Incorrect Fuel Composition", "")
R("P0170", "maf", "special", "Fuel Trim", "", q=" (Bank 1)")
R("P0171", "maf", "special", "System Too Lean", "", q=" (Bank 1)")
R("P0172", "maf", "special", "System Too Rich", "", q=" (Bank 1)")
R("P0173", "maf", "special", "Fuel Trim", "", q=" (Bank 2)")
R("P0174", "maf", "special", "System Too Lean", "", q=" (Bank 2)")
R("P0175", "maf", "special", "System Too Rich", "", q=" (Bank 2)")
fam(176, "fcs", "Fuel Composition Sensor", ("circuit", "rp", "low", "high"))
fam(180, "fts_A", "Fuel Temperature Sensor \"A\"")
fam(185, "fts_B", "Fuel Temperature Sensor \"B\"")
fam(190, "frp", "Fuel Rail Pressure Sensor \"A\"")
fam(195, "eot", "Engine Oil Temperature Sensor")
# ---------------------------------------------------------------- P0200 - P0299
R("P0200", "inj", "open", "Injector Circuit/Open", "")
for n in range(1, 13):
    R(code(200 + n), "inj", "open", "Injector Circuit/Open", "", q=f" - Cylinder {n}")
R("P0213", "csinj", "circuit", "Cold Start Injector 1", "")
R("P0214", "csinj", "circuit", "Cold Start Injector 2", "")
R("P0215", "eng_shutoff", "circuit", "Engine Shutoff Solenoid", "")
R("P0216", "inj_timing", "circuit", "Injector/Injection Timing Control", "Circuit")
R("P0217", "ect", "special", "Engine Coolant Over Temperature Condition", "")
R("P0218", "tft", "special", "Transmission Fluid Over Temperature Condition", "")
R("P0219", "eng_spd_in", "special", "Engine Overspeed Condition", "")
fam(220, "tps_B", "Throttle/Pedal Position Sensor/Switch \"B\"")
fam(225, "tps_C", "Throttle/Pedal Position Sensor/Switch \"C\"")
R("P0230", "fuel_pump", "circuit", "Fuel Pump Primary", "Circuit")
R("P0231", "fuel_pump", "low", "Fuel Pump Secondary", "Circuit Low")
R("P0232", "fuel_pump", "high", "Fuel Pump Secondary", "Circuit High")
R("P0233", "fuel_pump", "int", "Fuel Pump Secondary", "Circuit Intermittent")
R("P0234", "boost_ctrl", "special", "Turbo/Super Charger Overboost Condition", "")
fam(235, "boost_sensor", "Turbocharger Boost Sensor \"A\"", ("circuit", "rp", "low", "high"))
fam(239, "boost_sensor", "Turbocharger Boost Sensor \"B\"", ("circuit", "rp", "low", "high"))
fam(243, "wastegate", "Turbocharger Wastegate Solenoid \"A\"", ("circuit", "rp", "low", "high"),
    suffixes=("", "Range/Performance", "Low", "High"))
fam(247, "wastegate", "Turbocharger Wastegate Solenoid \"B\"", ("circuit", "rp", "low", "high"),
    suffixes=("", "Range/Performance", "Low", "High"))
fam(251, "inj_pump", "Injection Pump Fuel Metering Control \"A\" (Cam/Rotor/Injector)",
    suffixes=("", "Range/Performance", "Low", "High", "Intermittent"))
fam(256, "inj_pump", "Injection Pump Fuel Metering Control \"B\" (Cam/Rotor/Injector)",
    suffixes=("", "Range/Performance", "Low", "High", "Intermittent"))
for n in range(1, 13):
    b = 261 + 3 * (n - 1)
    R(code(b), "inj", "low", f"Cylinder {n} Injector", "Circuit Low")
    R(code(b + 1), "inj", "high", f"Cylinder {n} Injector", "Circuit High")
    R(code(b + 2), "inj", "special", f"Cylinder {n} Contribution/Balance", "")
R("P0297", "vss", "special", "Vehicle Overspeed Condition", "")
R("P0298", "eot", "special", "Engine Oil Over Temperature", "")
R("P0299", "boost_ctrl", "special", "Turbo/Super Charger Underboost", "")
# ---------------------------------------------------------------- P0300 - P0399
R("P0300", "coil", "special", "Random/Multiple Cylinder Misfire Detected", "")
for n in range(1, 13):
    R(code(300 + n), "coil", "special", f"Cylinder {n} Misfire Detected", "")
R("P0313", "coil", "special", "Misfire Detected with Low Fuel", "")
R("P0314", "coil", "special", "Single Cylinder Misfire (Cylinder not Specified)", "")
R("P0315", "ckp", "special", "Crankshaft Position System Variation Not Learned", "")
R("P0316", "coil", "special", "Engine Misfire Detected on Startup (First 1000 Revolutions)", "")
fam(320, "ign_rpm", "Ignition/Distributor Engine Speed Input", ("circuit", "rp", "nosig", "int"),
    suffixes=("Circuit", "Circuit Range/Performance", "Circuit No Signal", "Circuit Intermittent"))
R("P0324", "knock", "special", "Knock Control System Error", "")
fam(325, "knock", "Knock Sensor 1", q=" (Bank 1 or Single Sensor)")
fam(330, "knock", "Knock Sensor 2", q=" (Bank 2)")
fam(335, "ckp", "Crankshaft Position Sensor \"A\"")
fam(340, "cmp", "Camshaft Position Sensor \"A\"", q=" (Bank 1 or Single Sensor)")
fam(345, "cmp", "Camshaft Position Sensor \"A\"", q=" (Bank 2)")
R("P0350", "coil", "circuit", "Ignition Coil Primary/Secondary", "Circuit")
for i, L in enumerate("ABCDEFGHIJKL"):
    R(code(351 + i), "coil", "circuit", f"Ignition Coil \"{L}\" Primary/Secondary", "Circuit")
R("P0363", "coil", "special", "Misfire Detected - Fueling Disabled", "")
fam(365, "cmp", "Camshaft Position Sensor \"B\"", q=" (Bank 1)")
for start, L in ((370, "A"), (375, "B")):
    fam(start, "timing_ref", f"Timing Reference High Resolution Signal \"{L}\"",
        ("circuit", "too_many", "too_few", "erratic", "no_pulse"), suffixes=("", "Too Many Pulses", "Too Few Pulses",
                                                                         "Intermittent/Erratic Pulses", "No Pulse"))
R("P0380", "glow", "circuit", "Glow Plug/Heater Circuit \"A\"", "")
R("P0381", "lamp", "circuit", "Glow Plug/Heater Indicator Circuit", "")
R("P0382", "glow", "circuit", "Glow Plug/Heater Circuit \"B\"", "")
fam(385, "ckp", "Crankshaft Position Sensor \"B\"")
fam(390, "cmp", "Camshaft Position Sensor \"B\"", q=" (Bank 2)")
# ---------------------------------------------------------------- P0400 - P0499
R("P0400", "egr", "perf", "Exhaust Gas Recirculation", "Flow")
R("P0401", "egr", "special", "Exhaust Gas Recirculation Flow Insufficient Detected", "")
R("P0402", "egr", "special", "Exhaust Gas Recirculation Flow Excessive Detected", "")
R("P0403", "egr", "circuit", "Exhaust Gas Recirculation Control", "Circuit")
R("P0404", "egr", "rp", "Exhaust Gas Recirculation Control", "Circuit Range/Performance")
R("P0405", "egr_sensor", "low", "Exhaust Gas Recirculation Sensor \"A\"", "Circuit Low")
R("P0406", "egr_sensor", "high", "Exhaust Gas Recirculation Sensor \"A\"", "Circuit High")
R("P0407", "egr_sensor", "low", "Exhaust Gas Recirculation Sensor \"B\"", "Circuit Low")
R("P0408", "egr_sensor", "high", "Exhaust Gas Recirculation Sensor \"B\"", "Circuit High")
R("P0409", "egr_sensor", "circuit", "Exhaust Gas Recirculation Sensor \"A\"", "Circuit")
R("P0410", "air", "perf", "Secondary Air Injection System", "")
R("P0411", "air", "perf", "Secondary Air Injection System", "Incorrect Flow Detected")
R("P0412", "air", "circuit", "Secondary Air Injection System Switching Valve \"A\"", "Circuit")
R("P0413", "air", "open", "Secondary Air Injection System Switching Valve \"A\"", "Circuit Open")
R("P0414", "air", "short", "Secondary Air Injection System Switching Valve \"A\"", "Circuit Shorted")
R("P0415", "air", "circuit", "Secondary Air Injection System Switching Valve \"B\"", "Circuit")
R("P0416", "air", "open", "Secondary Air Injection System Switching Valve \"B\"", "Circuit Open")
R("P0417", "air", "short", "Secondary Air Injection System Switching Valve \"B\"", "Circuit Shorted")
R("P0418", "air", "circuit", "Secondary Air Injection System Relay \"A\"", "Circuit")
R("P0419", "air", "circuit", "Secondary Air Injection System Relay \"B\"", "Circuit")
for start, bank in ((420, 1), (430, 2)):
    q = f" (Bank {bank})"
    R(code(start), "cat", "special", "Catalyst System Efficiency Below Threshold", "", q=q)
    R(code(start + 1), "cat", "special", "Warm Up Catalyst Efficiency Below Threshold", "", q=q)
    R(code(start + 2), "cat", "special", "Main Catalyst Efficiency Below Threshold", "", q=q)
    R(code(start + 3), "cat", "special", "Heated Catalyst Efficiency Below Threshold", "", q=q)
    R(code(start + 4), "cat", "special", "Heated Catalyst Temperature Below Threshold", "", q=q)
    fam(start + 5, "cat_temp", "Catalyst Temperature Sensor", ("circuit", "rp", "low", "high"), q=f" (Bank {bank} Sensor 1)",
        suffixes=("", "Range/Performance", "Low", "High"))
    R(code(start + 9), "cat_heater", "circuit", "Catalyst Heater Control", "Circuit", q=q)
R("P0440", "evap", "special", "Evaporative Emission System", "")
R("P0441", "purge", "special", "Evaporative Emission System Incorrect Purge Flow", "")
R("P0442", "evap", "special", "Evaporative Emission System Leak Detected (Small Leak)", "")
R("P0443", "purge", "circuit", "Evaporative Emission System Purge Control Valve \"A\"", "Circuit")
R("P0444", "purge", "open", "Evaporative Emission System Purge Control Valve \"A\"", "Circuit Open")
R("P0445", "purge", "short", "Evaporative Emission System Purge Control Valve \"A\"", "Circuit Shorted")
R("P0446", "vent", "special", "Evaporative Emission System Vent Control", "Circuit")
R("P0447", "vent", "open", "Evaporative Emission System Vent Control", "Circuit Open")
R("P0448", "vent", "short", "Evaporative Emission System Vent Control", "Circuit Shorted")
R("P0449", "vent", "circuit", "Evaporative Emission System Vent Valve/Solenoid", "Circuit")
fam(450, "evap_ps", "Evaporative Emission System Pressure Sensor/Switch",
    suffixes=("", "Range/Performance", "Low", "High", "Intermittent/Erratic"))
R("P0455", "evap", "special", "Evaporative Emission System Leak Detected (Large Leak)", "")
R("P0456", "evap", "special", "Evaporative Emission System Leak Detected (Very Small Leak)", "")
R("P0457", "evap", "special", "Evaporative Emission System Leak Detected (Fuel Cap Loose/Off)", "")
R("P0458", "purge", "low", "Evaporative Emission System Purge Control Valve \"A\"", "Circuit Low")
R("P0459", "purge", "high", "Evaporative Emission System Purge Control Valve \"A\"", "Circuit High")
fam(460, "fuel_level", "Fuel Level Sensor \"A\"")
fam(465, "evap_flow", "EVAP Purge Flow Sensor")
fam(470, "exh_ps", "Exhaust Pressure Sensor \"A\"")
fam(475, "exh_pcv", "Exhaust Pressure Control Valve \"A\"", suffixes=("", "Range/Performance", "Low", "High",
                                                                     "Intermittent"))
R("P0480", "fan", "circuit", "Fan 1 Control", "Circuit")
R("P0481", "fan", "circuit", "Fan 2 Control", "Circuit")
R("P0482", "fan", "circuit", "Fan 3 Control", "Circuit")
R("P0483", "fan", "perf", "Fan Rationality Check", "")
R("P0484", "fan", "short", "Fan Circuit Over Current", "")
R("P0485", "fan", "circuit", "Fan Power/Ground", "Circuit")
R("P0486", "egr_sensor", "circuit", "Exhaust Gas Recirculation Sensor \"B\"", "Circuit")
R("P0487", "egr_thr", "circuit", "Exhaust Gas Recirculation Throttle Control \"A\"", "Circuit")
R("P0488", "egr_thr", "rp", "Exhaust Gas Recirculation Throttle Control \"A\"", "Range/Performance")
R("P0489", "egr", "low", "Exhaust Gas Recirculation \"A\"", "Control Circuit Low")
R("P0490", "egr", "high", "Exhaust Gas Recirculation \"A\"", "Control Circuit High")
R("P0491", "air", "special", "Secondary Air Injection System Insufficient Flow", "", q=" (Bank 1)")
R("P0492", "air", "special", "Secondary Air Injection System Insufficient Flow", "", q=" (Bank 2)")
R("P0493", "fan", "perf", "Fan Overspeed", "")
R("P0494", "fan", "low", "Fan Speed Low", "")
R("P0495", "fan", "high", "Fan Speed High", "")
R("P0496", "purge", "special", "Evaporative Emission System High Purge Flow", "")
R("P0497", "purge", "special", "Evaporative Emission System Low Purge Flow", "")
R("P0498", "vent", "low", "Evaporative Emission System Vent Valve Control", "Circuit Low")
R("P0499", "vent", "high", "Evaporative Emission System Vent Valve Control", "Circuit High")
# ---------------------------------------------------------------- P0500 - P0599
R("P0500", "vss", "circuit", "Vehicle Speed Sensor \"A\"", "")
R("P0501", "vss", "rp", "Vehicle Speed Sensor \"A\"", "Range/Performance")
R("P0502", "vss", "low", "Vehicle Speed Sensor \"A\"", "Circuit Low Input")
R("P0503", "vss", "int", "Vehicle Speed Sensor \"A\"", "Intermittent/Erratic/High")
R("P0504", "brake_sw", "special", "Brake Switch \"A\"/\"B\" Correlation", "")
R("P0505", "iac", "circuit", "Idle Air Control System", "")
R("P0506", "iac", "special", "Idle Air Control System", "RPM Lower Than Expected")
R("P0507", "iac", "special", "Idle Air Control System", "RPM Higher Than Expected")
R("P0508", "iac", "low", "Idle Air Control System", "Circuit Low")
R("P0509", "iac", "high", "Idle Air Control System", "Circuit High")
R("P0510", "tps_A", "circuit", "Closed Throttle Position Switch", "")
R("P0511", "iac", "circuit", "Idle Air Control", "Circuit")
R("P0512", "starter_relay", "circuit", "Starter Request", "Circuit")
R("P0513", "ecm", "special", "Invalid Immobilizer Key", "")
fam(515, "batt_temp", "Battery Temperature Sensor", ("circuit", "low", "high"))
fam(520, "oil_ps", "Engine Oil Pressure Sensor/Switch", ("circuit", "rp", "low", "high"))
R("P0524", "oil_ps", "special", "Engine Oil Pressure Too Low", "")
R("P0525", "cruise", "rp", "Cruise Control Servo Control", "Circuit Range/Performance")
fam(526, "fan_spd", "Fan Speed Sensor", ("circuit", "rp", "nosig", "int"),
    suffixes=("Circuit", "Circuit Range/Performance", "Circuit No Signal", "Circuit Intermittent"))
fam(530, "ac_ps", "A/C Refrigerant Pressure Sensor \"A\"", ("circuit", "rp", "low", "high"))
R("P0534", "ac_ps", "special", "Air Conditioner Refrigerant Charge Loss", "")
fam(535, "ac_evap_t", "A/C Evaporator Temperature Sensor")
fam(540, "iah", "Intake Air Heater \"A\"", ("circuit", "low", "high"))
fam(544, "egt", "Exhaust Gas Temperature Sensor", ("circuit", "low", "high"), q=" (Bank 1 Sensor 1)")
fam(547, "egt", "Exhaust Gas Temperature Sensor", ("circuit", "low", "high"), q=" (Bank 2 Sensor 1)")
fam(550, "ps_ps", "Power Steering Pressure Sensor/Switch")
fam(555, "bb_ps", "Brake Booster Pressure Sensor")
R("P0560", "voltage", "special", "System Voltage", "")
R("P0561", "voltage", "special", "System Voltage Unstable", "")
R("P0562", "voltage", "special", "System Voltage Low", "")
R("P0563", "voltage", "special", "System Voltage High", "")
R("P0564", "cruise", "circuit", "Cruise Control Multi-Function Input \"A\"", "Circuit")
for i, s in enumerate(("On", "Off", "Resume", "Set", "Coast", "Accel")):
    R(code(565 + i), "cruise", "circuit", f"Cruise Control {s} Signal", "")
fam(571, "brake_sw", "Brake Switch \"A\"", ("circuit", "low", "high"))
R("P0574", "cruise", "special", "Cruise Control System - Vehicle Speed Too High", "")
fam(575, "cruise", "Cruise Control Input", ("circuit", "low", "high"))
# ---------------------------------------------------------------- P0600 - P0699
R("P0600", "ecm", "special", "Serial Communication Link", "")
R("P0601", "ecm", "special", "Internal Control Module Memory Check Sum Error", "")
R("P0602", "ecm", "special", "Control Module Programming Error", "")
R("P0603", "ecm", "special", "Internal Control Module Keep Alive Memory (KAM) Error", "")
R("P0604", "ecm", "special", "Internal Control Module Random Access Memory (RAM) Error", "")
R("P0605", "ecm", "special", "Internal Control Module Read Only Memory (ROM) Error", "")
R("P0606", "ecm", "special", "Control Module Processor", "")
R("P0607", "ecm", "special", "Control Module Performance", "")
R("P0608", "ecm", "circuit", "Control Module VSS Output \"A\"", "")
R("P0609", "ecm", "circuit", "Control Module VSS Output \"B\"", "")
R("P0610", "ecm", "special", "Control Module Vehicle Options Error", "")
R("P0611", "ecm", "special", "Fuel Injector Control Module Performance", "")
R("P0612", "ecm", "circuit", "Fuel Injector Control Module Relay Control", "")
R("P0613", "ecm", "special", "TCM Processor", "")
R("P0614", "ecm", "special", "ECM / TCM Incompatible", "")
fam(615, "starter_relay", "Starter Relay", ("circuit", "low", "high"))
R("P0620", "gen", "circuit", "Generator Control", "Circuit")
R("P0621", "lamp", "circuit", "Generator Lamp \"L\" Control", "Circuit")
R("P0622", "gen", "circuit", "Generator Field \"F\" Control", "Circuit")
R("P0623", "lamp", "circuit", "Generator Lamp Control", "Circuit")
R("P0624", "lamp", "circuit", "Fuel Cap Lamp Control", "Circuit")
R("P0625", "gen", "low", "Generator Field Terminal", "Circuit Low")
R("P0626", "gen", "high", "Generator Field Terminal", "Circuit High")
ctrl(627, "fp_ctrl", "Fuel Pump \"A\"")
R("P0630", "ecm", "special", "VIN Not Programmed or Incompatible - ECM/PCM", "")
R("P0631", "ecm", "special", "VIN Not Programmed or Incompatible - TCM", "")
R("P0633", "ecm", "special", "Immobilizer Key Not Programmed - ECM/PCM", "")
R("P0634", "ecm_temp", "special", "PCM/ECM/TCM Internal Temperature Too High", "")
R("P0638", "tac", "rp", "Throttle Actuator Control", "Range/Performance", q=" (Bank 1)")
R("P0639", "tac", "rp", "Throttle Actuator Control", "Range/Performance", q=" (Bank 2)")
R("P0640", "iah", "circuit", "Intake Air Heater Control", "Circuit")
for start, L in ((641, "A"), (651, "B"), (697, "C")):
    R(code(start), "ref", "open", f"Sensor Reference Voltage \"{L}\"", "Circuit/Open")
    R(code(start + 1), "ref", "low", f"Sensor Reference Voltage \"{L}\"", "Circuit Low")
    R(code(start + 2), "ref", "high", f"Sensor Reference Voltage \"{L}\"", "Circuit High")
R("P0644", "lamp", "circuit", "Driver Display Serial Communication", "Circuit")
fam(645, "ac_clutch", "A/C Clutch Relay Control", ("circuit", "low", "high"))
R("P0648", "lamp", "circuit", "Immobilizer Lamp Control", "Circuit")
R("P0649", "lamp", "circuit", "Speed Control Lamp Control", "Circuit")
R("P0650", "lamp", "circuit", "Malfunction Indicator Lamp (MIL) Control", "Circuit")
R("P0654", "ecm", "circuit", "Engine RPM Output", "Circuit")
R("P0655", "lamp", "circuit", "Engine Hot Lamp Output Control", "Circuit")
R("P0656", "fuel_level", "circuit", "Fuel Level Output", "Circuit")
ctrl(657, "act_supply", "Actuator Supply Voltage \"A\"", kinds=("open", "low", "high"))
for start, bank in ((660, 1), (663, 2)):
    ctrl(start, "imtv", "Intake Manifold Tuning Valve", q=f" (Bank {bank})")
fam(666, "ecm_temp", "PCM/ECM/TCM Internal Temperature Sensor", ("circuit", "rp", "low", "high"))
R("P0670", "glow", "circuit", "Glow Plug Module Control", "Circuit")
for n in range(1, 13):
    R(code(670 + n), "glow_cyl", "circuit", f"Cylinder {n} Glow Plug", "Circuit")
R("P0683", "glow", "special", "Glow Plug Control Module to PCM Communication", "Circuit")
R("P0684", "glow", "rp", "Glow Plug Control Module to PCM Communication", "Circuit Range/Performance")
ctrl(685, "ecm_relay", "ECM/PCM Power Relay")
R("P0688", "ecm_relay", "open", "ECM/PCM Power Relay Sense", "Circuit/Open")
R("P0689", "ecm_relay", "low", "ECM/PCM Power Relay Sense", "Circuit Low")
R("P0690", "ecm_relay", "high", "ECM/PCM Power Relay Sense", "Circuit High")
for i, n in enumerate((1, 2, 3)):
    R(code(691 + 2 * i), "fan", "low", f"Fan {n} Control", "Circuit Low")
    R(code(692 + 2 * i), "fan", "high", f"Fan {n} Control", "Circuit High")
# ---------------------------------------------------------------- P0700 - P0799
R("P0700", "gear", "special", "Transmission Control System (MIL Request)", "")
R("P0701", "gear", "special", "Transmission Control System Range/Performance", "")
R("P0702", "tcm_power", "circuit", "Transmission Control System", "Electrical")
R("P0703", "brake_sw", "circuit", "Brake Switch \"B\"", "Circuit")
R("P0704", "clutch_sw", "circuit", "Clutch Switch Input", "Circuit Malfunction")
fam(705, "tr_range", "Transmission Range Sensor \"A\" Circuit (PRNDL Input)", suffixes=("", "Range/Performance", "Low",
                                                                                      "High", "Intermittent"))
fam(710, "tft", "Transmission Fluid Temperature Sensor \"A\"")
fam(715, "iss", "Input/Turbine Speed Sensor \"A\"", ("circuit", "rp", "nosig", "int"),
    suffixes=("Circuit", "Circuit Range/Performance", "Circuit No Signal", "Circuit Intermittent"))
R("P0719", "brake_sw", "low", "Brake Switch \"B\"", "Circuit Low")
fam(720, "oss", "Output Shaft Speed Sensor", ("circuit", "rp", "nosig", "int"),
    suffixes=("Circuit", "Circuit Range/Performance", "Circuit No Signal", "Circuit Intermittent"))
R("P0724", "brake_sw", "high", "Brake Switch \"B\"", "Circuit High")
fam(725, "eng_spd_in", "Engine Speed Input", ("circuit", "rp", "nosig", "int"),
    suffixes=("Circuit", "Circuit Range/Performance", "Circuit No Signal", "Circuit Intermittent"))
R("P0729", "gear", "ratio", "Gear 6", "Incorrect Ratio")
R("P0730", "gear", "ratio", "Incorrect Gear Ratio", "")
for i, g in enumerate(("1", "2", "3", "4", "5")):
    R(code(731 + i), "gear", "ratio", f"Gear {g}", "Incorrect Ratio")
R("P0736", "gear", "ratio", "Reverse", "Incorrect Ratio")
TRANS5 = ("circuit", "stuck_off", "stuck_on", "electrical", "intermittent")
TRANS5_SFX = ("", "Performance or Stuck Off", "Stuck On", "Electrical", "Intermittent")
fam(740, "tcc", "Torque Converter Clutch Solenoid", TRANS5, suffixes=("Circuit/Open", "Circuit Performance or Stuck Off",
                                                                        "Circuit Stuck On", "Circuit Electrical",
                                                                        "Circuit Intermittent"))
for start, L in ((745, "A"), (775, "B"), (795, "C")):
    fam(start, "pcs", f"Pressure Control Solenoid \"{L}\"", TRANS5, suffixes=TRANS5_SFX)
for start, L in ((750, "A"), (755, "B"), (760, "C"), (765, "D"), (770, "E")):
    fam(start, "ss", f"Shift Solenoid \"{L}\"", TRANS5, suffixes=TRANS5_SFX)
R("P0780", "gear", "shift", "Shift Error", "")
for i, s in enumerate(("1-2", "2-3", "3-4", "4-5")):
    R(code(781 + i), "gear", "shift", f"{s} Shift", "")
fam(785, "shift_tim", "Shift/Timing Solenoid", suffixes=("", "Range/Performance", "Low", "High", "Intermittent"))
R("P0790", "gear", "circuit", "Normal/Performance Switch", "Circuit")
fam(791, "int_shaft", "Intermediate Shaft Speed Sensor \"A\"", ("circuit", "rp", "nosig", "int"),
    suffixes=("Circuit", "Circuit Range/Performance", "Circuit No Signal", "Circuit Intermittent"))
# ---------------------------------------------------------------- P0800 - P0999
R("P0801", "gear", "circuit", "Reverse Inhibit Control", "Circuit")
R("P0803", "ss", "circuit", "1-4 Upshift (Skip Shift) Solenoid Control", "Circuit")
R("P0804", "lamp", "circuit", "1-4 Upshift (Skip Shift) Lamp Control", "Circuit")
fam(805, "clutch_pos", "Clutch Position Sensor")
R("P0810", "clutch_act", "perf", "Clutch Position Control Error", "")
R("P0811", "clutch_act", "special", "Excessive Clutch Slippage", "")
R("P0812", "gear", "circuit", "Reverse Input", "Circuit")
R("P0813", "gear", "circuit", "Reverse Output", "Circuit")
R("P0814", "lamp", "circuit", "Transmission Range Display", "Circuit")
R("P0815", "gear", "circuit", "Upshift Switch", "Circuit")
R("P0816", "gear", "circuit", "Downshift Switch", "Circuit")
R("P0817", "starter_relay", "circuit", "Starter Disable", "Circuit")
fam(830, "clutch_sw", "Clutch Pedal Switch \"A\"", ("circuit", "low", "high"))
fam(833, "clutch_sw", "Clutch Pedal Switch \"B\"", ("circuit", "low", "high"))
fam(840, "tfps", "Transmission Fluid Pressure Sensor/Switch \"A\"")
fam(845, "tfps", "Transmission Fluid Pressure Sensor/Switch \"B\"")
fam(850, "pn_sw", "Park/Neutral Switch Input", ("circuit", "low", "high"))
R("P0856", "gear", "circuit", "Traction Control Input Signal", "")
R("P0857", "gear", "rp", "Traction Control Input Signal", "Range/Performance")
fam(880, "tcm_power", "TCM Power Input Signal", suffixes=("", "Range/Performance", "Low", "High", "Intermittent"))
ctrl(885, "tcm_relay", "TCM Power Relay")
R("P0894", "gear", "special", "Transmission Component Slipping", "")
R("P0897", "gear", "special", "Transmission Fluid Deteriorated", "")
fam(900, "clutch_act", "Clutch Actuator", ("open", "rp", "low", "high"),
    suffixes=("Circuit/Open", "Circuit Range/Performance", "Circuit Low", "Circuit High"))
for start, L in ((960, "A"), (964, "B"), (968, "C")):
    ctrl(start, "pcs", f"Pressure Control Solenoid \"{L}\"", kinds=("open", "rp", "low", "high"))
for start, L in ((972, "A"), (975, "B"), (978, "C"), (981, "D"), (984, "E")):
    ctrl(start, "ss", f"Shift Solenoid \"{L}\"", kinds=("rp", "low", "high"))

# ================================================================ P2xxx
for start, bank in ((2000, 1), (2001, 2)):
    R(f"P{start}", "nox_trap", "special", "NOx Trap Efficiency Below Threshold", "", q=f" (Bank {bank})")
R("P2002", "dpf", "special", "Diesel Particulate Filter Efficiency Below Threshold", "", q=" (Bank 1)")
R("P2003", "dpf", "special", "Diesel Particulate Filter Efficiency Below Threshold", "", q=" (Bank 2)")
R("P2004", "imrc", "stuck_on", "Intake Manifold Runner Control", "Stuck Open", q=" (Bank 1)")
R("P2005", "imrc", "stuck_on", "Intake Manifold Runner Control", "Stuck Open", q=" (Bank 2)")
R("P2006", "imrc", "stuck_off", "Intake Manifold Runner Control", "Stuck Closed", q=" (Bank 1)")
R("P2007", "imrc", "stuck_off", "Intake Manifold Runner Control", "Stuck Closed", q=" (Bank 2)")
for start, bank in ((2008, 1), (2011, 2)):
    R(f"P{start}", "imrc", "open", "Intake Manifold Runner Control", "Circuit/Open", q=f" (Bank {bank})")
    R(f"P{start + 1}", "imrc", "low", "Intake Manifold Runner Control", "Circuit Low", q=f" (Bank {bank})")
    R(f"P{start + 2}", "imrc", "high", "Intake Manifold Runner Control", "Circuit High", q=f" (Bank {bank})")
fam(2014, "imr_ps", "Intake Manifold Runner Position Sensor/Switch", q=" (Bank 1)")
fam(2019, "imr_ps", "Intake Manifold Runner Position Sensor/Switch", q=" (Bank 2)")
fam(2024, "evap_temp", "Evaporative Emissions (EVAP) Fuel Vapor Temperature Sensor", ("circuit", "rp", "low", "high", "int"),
    suffixes=("Circuit", "Performance", "Circuit Low Voltage", "Circuit High Voltage", "Circuit Intermittent"))
fam(2031, "egt", "Exhaust Gas Temperature Sensor", ("circuit", "low", "high"), q=" (Bank 1 Sensor 2)")
fam(2034, "egt", "Exhaust Gas Temperature Sensor", ("circuit", "low", "high"), q=" (Bank 2 Sensor 2)")
R("P2080", "egt", "rp", "Exhaust Gas Temperature Sensor", "Circuit Range/Performance", q=" (Bank 1 Sensor 1)")
R("P2084", "egt", "rp", "Exhaust Gas Temperature Sensor", "Circuit Range/Performance", q=" (Bank 1 Sensor 2)")
for i, (L, bank) in enumerate((("A", 1), ("B", 1), ("A", 2), ("B", 2))):
    R(f"P{2088 + 2 * i}", "vvt_ctrl", "low", f"\"{L}\" Camshaft Position Actuator", "Control Circuit Low", q=f" (Bank {bank})")
    R(f"P{2089 + 2 * i}", "vvt_ctrl", "high", f"\"{L}\" Camshaft Position Actuator", "Control Circuit High", q=f" (Bank {bank})")
R("P2096", "o2", "special", "Post Catalyst Fuel Trim System Too Lean", "", q=" (Bank 1)")
R("P2097", "o2", "special", "Post Catalyst Fuel Trim System Too Rich", "", q=" (Bank 1)")
R("P2098", "o2", "special", "Post Catalyst Fuel Trim System Too Lean", "", q=" (Bank 2)")
R("P2099", "o2", "special", "Post Catalyst Fuel Trim System Too Rich", "", q=" (Bank 2)")
fam(2100, "tac", "Throttle Actuator Control Motor", ("open", "rp", "low", "high"),
    suffixes=("Circuit/Open", "Circuit Range/Performance", "Circuit Low", "Circuit High"))
R("P2104", "tac", "special", "Throttle Actuator Control System - Forced Idle", "")
R("P2105", "tac", "special", "Throttle Actuator Control System - Forced Engine Shutdown", "")
R("P2106", "tac", "special", "Throttle Actuator Control System - Forced Limited Power", "")
R("P2107", "tac", "special", "Throttle Actuator Control Module Processor", "")
R("P2108", "tac", "special", "Throttle Actuator Control Module Performance", "")
R("P2109", "tps_A", "rp", "Throttle/Pedal Position Sensor \"A\" Minimum Stop", "Performance")
R("P2110", "tac", "special", "Throttle Actuator Control System - Forced Limited RPM", "")
R("P2111", "tac", "special", "Throttle Actuator Control System - Stuck Open", "")
R("P2112", "tac", "special", "Throttle Actuator Control System - Stuck Closed", "")
R("P2118", "tac", "rp", "Throttle Actuator Control Motor Current", "Range/Performance")
R("P2119", "tac", "special", "Throttle Actuator Control Throttle Body", "Range/Performance")
fam(2120, "tps_D", "Throttle/Pedal Position Sensor/Switch \"D\"")
fam(2125, "tps_E", "Throttle/Pedal Position Sensor/Switch \"E\"")
fam(2130, "tps_F", "Throttle/Pedal Position Sensor/Switch \"F\"")
for i, pair in enumerate(("A\"/\"B", "A\"/\"C", "B\"/\"C", "D\"/\"E", "D\"/\"F", "E\"/\"F")):
    R(f"P{2135 + i}", "tps_A", "special", f"Throttle/Pedal Position Sensor/Switch \"{pair}\" Voltage Correlation", "")
R("P2141", "egr_thr", "low", "Exhaust Gas Recirculation Throttle Control", "Circuit Low")
R("P2142", "egr_thr", "high", "Exhaust Gas Recirculation Throttle Control", "Circuit High")
for start, L in ((2146, "A"), (2149, "B")):
    R(f"P{start}", "inj_grp", "open", f"Fuel Injector Group \"{L}\" Supply Voltage", "Circuit/Open")
    R(f"P{start + 1}", "inj_grp", "low", f"Fuel Injector Group \"{L}\" Supply Voltage", "Circuit Low")
    R(f"P{start + 2}", "inj_grp", "high", f"Fuel Injector Group \"{L}\" Supply Voltage", "Circuit High")
R("P2158", "vss", "circuit", "Vehicle Speed Sensor \"B\"", "")
R("P2159", "vss", "rp", "Vehicle Speed Sensor \"B\"", "Range/Performance")
R("P2160", "vss", "low", "Vehicle Speed Sensor \"B\"", "Circuit Low")
R("P2161", "vss", "int", "Vehicle Speed Sensor \"B\"", "Intermittent/Erratic")
R("P2162", "vss", "special", "Vehicle Speed Sensor \"A\"/\"B\" Correlation", "")
for start, where in ((2177, "Off Idle"), (2187, "at Idle"), (2191, "at Higher Load")):
    R(f"P{start}", "maf", "special", f"System Too Lean {where}", "", q=" (Bank 1)")
    R(f"P{start + 1}", "maf", "special", f"System Too Rich {where}", "", q=" (Bank 1)")
    R(f"P{start + 2}", "maf", "special", f"System Too Lean {where}", "", q=" (Bank 2)")
    R(f"P{start + 3}", "maf", "special", f"System Too Rich {where}", "", q=" (Bank 2)")
R("P2181", "ect", "special", "Cooling System Performance", "")
fam(2182, "ect2", "Engine Coolant Temperature Sensor 2")
for start, s in ((2195, 1), (2270, 2)):
    R(f"P{start}", "o2", "special", "O2 Sensor Signal Stuck Lean", "", q=f" (Bank 1 Sensor {s})")
    R(f"P{start + 1}", "o2", "special", "O2 Sensor Signal Stuck Rich", "", q=f" (Bank 1 Sensor {s})")
    R(f"P{start + 2}", "o2", "special", "O2 Sensor Signal Stuck Lean", "", q=f" (Bank 2 Sensor {s})")
    R(f"P{start + 3}", "o2", "special", "O2 Sensor Signal Stuck Rich", "", q=f" (Bank 2 Sensor {s})")
R("P2199", "iat", "special", "Intake Air Temperature Sensor 1 / 2 Correlation", "")
fam(2200, "nox", "NOx Sensor", q=" (Bank 1)")
R("P2226", "baro", "circuit", "Barometric Pressure", "Circuit")
R("P2227", "baro", "rp", "Barometric Pressure", "Circuit Range/Performance")
R("P2228", "baro", "low", "Barometric Pressure", "Circuit Low")
R("P2229", "baro", "high", "Barometric Pressure", "Circuit High")
R("P2230", "baro", "int", "Barometric Pressure", "Circuit Intermittent")
R("P2279", "map", "special", "Intake Air System Leak", "")
R("P2293", "fpr1", "perf", "Fuel Pressure Regulator 2", "Performance", base_ar="منظم ضغط الوقود 2")
for i, L in enumerate("ABCDEFGHIJKL"):
    b = 2300 + 3 * i
    R(f"P{b}", "coil", "low", f"Ignition Coil \"{L}\" Primary Control", "Circuit Low")
    R(f"P{b + 1}", "coil", "high", f"Ignition Coil \"{L}\" Primary Control", "Circuit High")
    R(f"P{b + 2}", "coil", "special", f"Ignition Coil \"{L}\" Secondary", "Circuit")
ctrl(2400, "ldp", "Evaporative Emission System Leak Detection Pump")
fam(2403, "ldp", "Evaporative Emission System Leak Detection Pump Sense", ("open", "rp", "low", "high", "int"),
    suffixes=("Circuit/Open", "Circuit Range/Performance", "Circuit Low", "Circuit High", "Circuit Intermittent"))
R("P2413", "egr", "special", "Exhaust Gas Recirculation System Performance", "")
R("P2414", "o2", "special", "O2 Sensor Exhaust Sample Error", "", q=" (Bank 1 Sensor 1)")
R("P2415", "o2", "special", "O2 Sensor Exhaust Sample Error", "", q=" (Bank 2 Sensor 1)")
R("P2422", "vent", "special", "Evaporative Emission System Vent Valve Stuck Closed", "")
for i, bank in enumerate((1, 2)):
    R(f"P{2440 + 2 * i}", "air", "stuck_on", "Secondary Air Injection System Switching Valve", "Stuck Open", q=f" (Bank {bank})")
    R(f"P{2441 + 2 * i}", "air", "stuck_off", "Secondary Air Injection System Switching Valve", "Stuck Closed", q=f" (Bank {bank})")
    R(f"P{2444 + 2 * i}", "air", "stuck_on", "Secondary Air Injection System Pump", "Stuck On", q=f" (Bank {bank})")
    R(f"P{2445 + 2 * i}", "air", "stuck_off", "Secondary Air Injection System Pump", "Stuck Off", q=f" (Bank {bank})")
fam(2452, "dpf_ps", "Diesel Particulate Filter Pressure Sensor \"A\"")
R("P2457", "egr", "special", "Exhaust Gas Recirculation Cooling System Performance", "")
R("P2458", "dpf", "special", "Diesel Particulate Filter Regeneration Duration", "")
R("P2459", "dpf", "special", "Diesel Particulate Filter Regeneration Frequency", "")
R("P2463", "dpf", "special", "Diesel Particulate Filter Restriction - Soot Accumulation", "")
R("P2500", "lamp", "low", "Generator Lamp/L-Terminal", "Circuit Low", base_ar="لمبة الدينامو / الطرف L")
R("P2501", "lamp", "high", "Generator Lamp/L-Terminal", "Circuit High", base_ar="لمبة الدينامو / الطرف L")
R("P2502", "voltage", "special", "Charging System Voltage", "")
R("P2503", "voltage", "special", "Charging System Voltage Low", "")
R("P2504", "voltage", "special", "Charging System Voltage High", "")
fam(2505, "ecm_pwr", "ECM/PCM Power Input Signal", suffixes=("", "Range/Performance", "Low", "High", "Intermittent"))
R("P2510", "ecm_relay", "rp", "ECM/PCM Power Relay Sense", "Circuit Range/Performance")
R("P2511", "ecm_relay", "int", "ECM/PCM Power Relay Sense", "Circuit Intermittent")
R("P2530", "ign_sw", "circuit", "Ignition Switch Run Position", "Circuit")
R("P2544", "gear", "special", "Torque Management Request Input Signal \"A\"", "")
R("P2560", "ect", "special", "Engine Coolant Level Low", "")
fam(2562, "tbp", "Turbocharger Boost Control Position Sensor \"A\"")
fam(2600, "coolant_pump", "Coolant Pump \"A\" Control", ("open", "rp", "low", "high"),
    suffixes=("Circuit/Open", "Circuit Range/Performance", "Circuit Low", "Circuit High"))
R("P2610", "ecm", "special", "ECM/PCM Internal Engine Off Timer Performance", "")
R("P2635", "fuel_pump", "special", "Fuel Pump \"A\" Low Flow/Performance", "")
R("P2646", "rocker", "stuck_off", "\"A\" Rocker Arm Actuator System", "Performance or Stuck Off", q=" (Bank 1)")
R("P2647", "rocker", "stuck_on", "\"A\" Rocker Arm Actuator System", "Stuck On", q=" (Bank 1)")
R("P2648", "rocker", "low", "\"A\" Rocker Arm Actuator Control", "Circuit Low", q=" (Bank 1)")
R("P2649", "rocker", "high", "\"A\" Rocker Arm Actuator Control", "Circuit High", q=" (Bank 1)")
ctrl(2669, "act_supply", "Actuator Supply Voltage \"B\"", kinds=("open", "low", "high"))
for i, L in enumerate("ABCDEF"):
    R(f"P{2700 + i}", "friction", "perf", f"Transmission Friction Element \"{L}\" Apply Time", "Range/Performance")
fam(2714, "pcs", "Pressure Control Solenoid \"D\"", TRANS5[1:], suffixes=TRANS5_SFX[1:])
ctrl(2718, "pcs", "Pressure Control Solenoid \"D\"", kinds=("open", "rp", "low", "high"))

# ================================================================ P34xx cylinder deactivation
R("P3400", "cyl_deact", "special", "Cylinder Deactivation System", "", q=" (Bank 1)")
for n in range(1, 13):
    b = 3401 + 8 * (n - 1)
    for j, (valve, f, sfx) in enumerate((("Deactivation/Intake Valve Control", "open", "Circuit/Open"),
                                         ("Deactivation/Intake Valve Control", "perf", "Performance"),
                                         ("Deactivation/Intake Valve Control", "low", "Circuit Low"),
                                         ("Deactivation/Intake Valve Control", "high", "Circuit High"),
                                         ("Exhaust Valve Control", "open", "Circuit/Open"),
                                         ("Exhaust Valve Control", "perf", "Performance"),
                                         ("Exhaust Valve Control", "low", "Circuit Low"),
                                         ("Exhaust Valve Control", "high", "Circuit High"))):
        R(f"P{b + j}", "cyl_deact", f, f"Cylinder {n} {valve}", sfx)
R("P3497", "cyl_deact", "special", "Cylinder Deactivation System", "", q=" (Bank 2)")


# ---------------------------------------------------------------- added: DPF, water in fuel, SCR, generator
R("P065B", "gen", "rp", "Generator Control", "Circuit Range/Performance")
R("P2047", "scr", "open", "Reductant Injector", "Circuit/Open", q=" (Bank 1 Unit 1)", base_ar="رشاش AdBlue")
R("P203F", "scr", "special", "Reductant Level Too Low", "")
R("P204F", "scr", "special", "Reductant System Performance", "", q=" (Bank 1)")
R("P20B9", "scr", "open", "Reductant Heater \"A\" Control", "Circuit/Open", base_ar="سخان AdBlue \"A\" - التحكم")
R("P20EE", "scr", "special", "SCR NOx Catalyst Efficiency Below Threshold", "", q=" (Bank 1)")
R("P2264", "wif", "circuit", "Water in Fuel Sensor", "Circuit")
R("P2265", "wif", "rp", "Water in Fuel Sensor", "Circuit Range/Performance")
R("P2266", "wif", "low", "Water in Fuel Sensor", "Circuit Low")
R("P2267", "wif", "high", "Water in Fuel Sensor", "Circuit High")
R("P2269", "wif", "special", "Water in Fuel Condition", "")
R("P242F", "dpf", "special", "Diesel Particulate Filter Restriction - Ash Accumulation", "")
R("P244A", "dpf", "special", "Diesel Particulate Filter Differential Pressure Too Low", "", q=" (Bank 1)")
R("P244B", "dpf", "special", "Diesel Particulate Filter Differential Pressure Too High", "", q=" (Bank 1)")


def by_code() -> dict[str, dict]:
    return {r["code"]: r for r in ROWS}


_CODE = re.compile(r"^[PBCU][0-3][0-9A-F]{3}$")
assert all(_CODE.match(r["code"]) for r in ROWS)
