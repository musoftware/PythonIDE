"""Common generic network (U), body (B) and chassis (C) codes, and the meaning of code ranges (fallback for unknown
codes). Explanations are RAD IDE's own words. `source`: "generic" (SAE J2012 generic) or "generic-common" (a widely used
assignment - verify with the manufacturer's information)."""
from __future__ import annotations

EXTRA: list[dict] = []


def X(code, en_title, ar_title, en, ar, causes, checks, sev="amber", drive="caution", system="network", tags=(),
      related=(), safety=False, source="generic", monitor="components"):
    EXTRA.append(dict(code=code, title_en=en_title, title_ar=ar_title, en=en, ar=ar, causes=list(causes), checks=list(checks),
                      sev=sev, drive=drive, system=system, tags=list(tags), related=list(related), safety=safety,
                      source=source, monitor=monitor))


# ------------------------------------------------------------------ U: lost communication
_lost_causes = ["module_power", "can_wiring", "battery", "module_failed", "aftermarket"]
_lost_checks = ["modules_online", ("Check the fuses and ground of the silent module.", "افحص فيوزات وأرضي الوحدة الصامتة."),
                "can_resistance", "battery_test", "clear"]
MODULES = [
    ("U0100", "ECM/PCM \"A\"", "كمبيوتر المحرك ECM/PCM \"A\"", "red", "no", ["no-start", "stalling", "limp-mode"], True),
    ("U0101", "TCM", "كمبيوتر الفتيس (TCM)", "amber", "caution", ["hard-shift", "limp-mode"], False),
    ("U0102", "Transfer Case Control Module", "وحدة التحكم في صندوق التوزيع", "amber", "caution", ["4wd"], False),
    ("U0103", "Gear Shift Control Module \"A\"", "وحدة التحكم في ذراع الفتيس \"A\"", "amber", "caution", ["hard-shift"], False),
    ("U0104", "Cruise Control Module", "وحدة مثبت السرعة", "green", "yes", ["cruise"], False),
    ("U0105", "Fuel Injector Control Module", "وحدة التحكم في الرشاشات", "amber", "caution", ["stalling"], False),
    ("U0106", "Glow Plug Control Module", "وحدة التحكم في بوجيهات التسخين", "green", "yes", ["hard-start"], False),
    ("U0107", "Throttle Actuator Control Module", "وحدة التحكم في مشغّل الثروتل", "amber", "caution", ["limp-mode"], False),
    ("U0109", "Fuel Pump Control Module", "وحدة التحكم في طرمبة البنزين", "amber", "caution", ["stalling", "no-start"], False),
    ("U0121", "Anti-Lock Brake System (ABS) Control Module", "وحدة التحكم في الفرامل ABS", "amber", "caution", ["abs", "brakes"], True),
    ("U0122", "Vehicle Dynamics Control Module", "وحدة التحكم في ثبات السيارة", "amber", "caution", ["esp", "abs"], True),
    ("U0123", "Yaw Rate Sensor Module", "وحدة حساس الانعراج (Yaw Rate)", "amber", "caution", ["esp"], True),
    ("U0124", "Lateral Acceleration Sensor Module", "وحدة حساس التسارع الجانبي", "amber", "caution", ["esp"], True),
    ("U0126", "Steering Angle Sensor Module", "وحدة حساس زاوية الدركسيون", "amber", "caution", ["esp", "steering"], True),
    ("U0127", "Tire Pressure Monitor Module", "وحدة مراقبة ضغط الإطارات", "green", "yes", ["tpms"], False),
    ("U0128", "Park Brake Control Module", "وحدة التحكم في فرامل اليد", "amber", "caution", ["brakes"], True),
    ("U0129", "Brake System Control Module", "وحدة التحكم في نظام الفرامل", "amber", "caution", ["brakes", "abs"], True),
    ("U0131", "Power Steering Control Module", "وحدة التحكم في الدركسيون الكهربائي", "amber", "caution", ["steering"], True),
    ("U0140", "Body Control Module", "وحدة التحكم في الهيكل (BCM)", "amber", "caution", ["electrical", "lights"], False),
    ("U0151", "Restraints Control Module", "وحدة التحكم في الوسائد الهوائية (Airbag)", "amber", "caution", ["airbag"], True),
    ("U0155", "Instrument Panel Cluster (IPC) Control Module", "وحدة لوحة العدادات", "amber", "caution", ["gauge", "warning-light"], False),
    ("U0164", "HVAC Control Module", "وحدة التحكم في التكييف", "green", "yes", ["ac"], False),
    ("U0167", "Vehicle Immobilizer Control Module", "وحدة منع السرقة (Immobilizer)", "amber", "caution", ["no-start"], False),
    ("U0184", "Radio", "الراديو", "green", "yes", [], False),
]
for code_, en_name, ar_name, sev, drive, tags, safety in MODULES:
    X(code_, f"Lost Communication With {en_name}", f"فقد الاتصال مع {ar_name}",
      f"Modules talk to each other over the CAN network. The module that stored this code stopped receiving messages from "
      f"the {en_name}. Either that module is not powered or is faulty, or the network wiring between them is damaged. "
      f"Several 'lost communication' codes at once usually point to a shared cause (low battery, a ground, a network fault).",
      f"الوحدات تتواصل مع بعضها عبر شبكة CAN. الوحدة التي سجّلت هذا الكود توقفت عن استقبال رسائل من {ar_name}. إما أن تلك "
      f"الوحدة بدون تغذية أو تالفة، أو أن أسلاك الشبكة بينهما تالفة. ظهور عدة أكواد \"فقد اتصال\" معًا يشير غالبًا إلى سبب "
      f"مشترك (بطارية ضعيفة أو أرضي أو عطل في الشبكة).",
      _lost_causes, _lost_checks + (["pro"] if safety else []), sev=sev, drive=drive, tags=tags + ["network"],
      related=["U0001", "U0073", "P0562"], safety=safety)
X("U0001", "High Speed CAN Communication Bus", "شبكة الاتصال CAN عالية السرعة",
  "The high-speed CAN network has a fault (open, short or noise). Many modules may lose contact at once.",
  "شبكة CAN عالية السرعة بها عطل (انقطاع أو قصر أو تشويش). قد تفقد وحدات كثيرة الاتصال في نفس الوقت.",
  ["can_wiring", "module_failed", ("Water in a connector of the network", "مياه في فيشة من فيش الشبكة"), "aftermarket"],
  ["can_resistance", "modules_online", "clear"], sev="amber", tags=["network", "multiple-codes"], related=["U0073", "U0100"])
X("U0073", "Control Module Communication Bus \"A\" Off", "شبكة الاتصال \"A\" متوقفة (Bus Off)",
  "The module switched its CAN connection off because of too many communication errors.", "الوحدة أوقفت اتصالها بشبكة CAN بسبب كثرة أخطاء الاتصال.",
  ["can_wiring", "module_failed", "battery"], ["can_resistance", "modules_online", "clear"], tags=["network", "multiple-codes"],
  related=["U0001", "U0100"])
X("U0300", "Internal Control Module Software Incompatibility", "عدم توافق برمجة وحدة التحكم",
  "Two modules have software versions that do not match (often after replacing or updating one).",
  "وحدتان لهما إصدارات برمجة غير متوافقة (غالبًا بعد تغيير أو تحديث إحداهما).",
  ["software", ("A used or wrong module was fitted", "تم تركيب وحدة مستعملة أو خاطئة")], ["tsb", "clear"], tags=["network"])
for code_, en_name, ar_name in (("U0401", "ECM/PCM \"A\"", "كمبيوتر المحرك"), ("U0402", "TCM", "كمبيوتر الفتيس"),
                                ("U0415", "Anti-Lock Brake System (ABS) Control Module", "وحدة الفرامل ABS"),
                                ("U0416", "Vehicle Dynamics Control Module", "وحدة ثبات السيارة"),
                                ("U0422", "Body Control Module", "وحدة التحكم في الهيكل (BCM)"),
                                ("U0423", "Instrument Panel Control Module", "وحدة لوحة العدادات")):
    X(code_, f"Invalid Data Received From {en_name}", f"بيانات غير صالحة مستلمة من {ar_name}",
      f"Messages from the {en_name} arrive, but their content is invalid. Often that module has a fault of its own - scan it.",
      f"الرسائل من {ar_name} تصل لكن محتواها غير صالح. غالبًا لدى تلك الوحدة عطل خاص بها - افحصها.",
      [("A fault stored inside the sending module", "عطل مسجل داخل الوحدة المرسلة"), "software", "can_wiring", "battery"],
      ["modules_online", "tsb", "clear"], tags=["network"], related=["U0100"])

# ------------------------------------------------------------------ C: chassis (ABS / ESP)
_wss_causes = ["wheel_sensor", "conn", "tone_ring", "bearing", "wire_open"]
_wss_checks = [("Watch the four wheel speeds in live data while driving slowly: the faulty one drops out or reads differently.",
                "راقب سرعات العجلات الأربع في البيانات الحية أثناء القيادة ببطء: العجلة المعطلة تنقطع أو تقرأ بشكل مختلف."),
               ("Inspect the sensor wire near the wheel (it moves with the suspension) and clean the sensor tip.", "افحص سلك الحساس قرب العجلة (يتحرك مع العفشة) ونظّف رأس الحساس."),
               "pro", "clear"]
for i, (wh_en, wh_ar) in enumerate((("Left Front", "الأمامية اليسرى"), ("Right Front", "الأمامية اليمنى"),
                                    ("Left Rear", "الخلفية اليسرى"), ("Right Rear", "الخلفية اليمنى"))):
    base = 35 + 5 * i
    for off, sfx_en, sfx_ar in ((0, "Circuit", "الدائرة"), (1, "Circuit Range/Performance", "الدائرة - خارج المدى/أداء")):
        X(f"C{base + off:04d}", f"{wh_en} Wheel Speed Sensor {sfx_en}", f"حساس سرعة العجلة {wh_ar} - {sfx_ar}",
          f"Each wheel has a speed sensor used by ABS, traction control and ESP. The {wh_en.lower()} sensor signal is "
          "missing or wrong, so these systems are switched off - the normal brakes still work, but without ABS help on a "
          "slippery road.",
          f"لكل عجلة حساس سرعة تستخدمه أنظمة ABS والتحكم في الجر وESP. إشارة حساس العجلة {wh_ar} مفقودة أو خاطئة، لذلك "
          "تتوقف هذه الأنظمة - الفرامل العادية ما زالت تعمل لكن بدون مساعدة ABS على الطريق الزلق.",
          _wss_causes, _wss_checks, sev="amber", drive="caution", system="abs-brakes", tags=["abs", "esp", "brakes"],
          related=["C0035", "C0040", "C0045", "C0050", "P0500"], safety=True, source="generic-common")
X("C0110", "Pump Motor Circuit", "دائرة موتور طرمبة ABS",
  "The ABS hydraulic pump motor circuit has a fault, so ABS is switched off.", "دائرة موتور الطرمبة الهيدروليكية للـ ABS بها عطل، لذلك يتوقف ABS.",
  ["fuse_relay", ("Seized ABS pump motor", "موتور طرمبة ABS متيبّس"), "conn", "battery"], ["fuse", "pro", "clear"],
  system="abs-brakes", tags=["abs", "brakes"], safety=True, source="generic-common")
X("C0121", "Valve Relay Circuit", "دائرة ريلاي صمامات ABS", "The relay that powers the ABS valves has a fault; ABS is switched off.",
  "الريلاي الذي يغذي صمامات ABS به عطل؛ يتوقف ABS.", ["fuse_relay", "conn", "battery", "ecu"], ["fuse", "battery_test", "pro", "clear"],
  system="abs-brakes", tags=["abs", "brakes"], safety=True, source="generic-common")
X("C0161", "ABS/TCS Brake Switch Circuit", "دائرة مفتاح الفرامل لنظام ABS/TCS", "The ABS module sees an implausible brake switch signal.",
  "وحدة ABS ترى إشارة غير منطقية من مفتاح الفرامل.", [("Faulty brake light switch", "مفتاح لمبة الفرامل تالف"), ("Burnt brake light bulb", "لمبة فرامل محروقة"), "conn"],
  [("Check that the brake lights work.", "تأكد أن لمبات الفرامل تعمل."), "clear"], system="abs-brakes", tags=["abs", "brake-lights"],
  related=["P0571", "P0504"], safety=True, source="generic-common")
X("C0455", "Steering Wheel Position Sensor Circuit", "دائرة حساس وضع عجلة القيادة",
  "The steering angle sensor signal is faulty. ESP and some steering functions are switched off. After an alignment or "
  "replacing the sensor, the steering angle must be calibrated (Service Functions).",
  "إشارة حساس زاوية الدركسيون معطلة. يتوقف ESP وبعض وظائف التوجيه. بعد ضبط الزوايا أو تغيير الحساس يجب معايرة زاوية "
  "الدركسيون (وظائف الصيانة).",
  ["conn", "clockspring", ("Steering angle not calibrated after alignment", "زاوية الدركسيون غير معايرة بعد ضبط الزوايا"), "sensor"],
  [("Run the steering angle sensor calibration (Service Functions) with the wheels straight.", "شغّل معايرة حساس زاوية الدركسيون (وظائف الصيانة) والعجلات مستقيمة."), "pro", "clear"],
  system="steering", tags=["esp", "steering"], related=["U0126"], safety=True, source="generic-common")

# ------------------------------------------------------------------ B: body (airbag)
_srs_causes = ["seat_connector", "clockspring", "squib", "conn", "battery"]
_srs_checks = [("Airbag circuits are dangerous: switch the ignition off and disconnect the battery for a few minutes before touching "
                "any airbag connector. Never measure an airbag with an ohmmeter.",
                "دوائر الإيرباج خطيرة: أطفئ المفتاح وافصل البطارية لبضع دقائق قبل لمس أي فيشة إيرباج. لا تقِس الإيرباج بالأوميتر أبدًا."),
               ("Check the yellow connectors under the seats and at the steering wheel.", "افحص الفيش الصفراء تحت الكراسي وعند الدركسيون."),
               "pro", "clear"]
for code_, en_t, ar_t in (("B0001", "Driver Frontal Stage 1 Deployment Control", "التحكم في فتح الوسادة الأمامية للسائق - المرحلة 1"),
                          ("B0002", "Driver Frontal Stage 2 Deployment Control", "التحكم في فتح الوسادة الأمامية للسائق - المرحلة 2"),
                          ("B0010", "Passenger Frontal Stage 1 Deployment Control", "التحكم في فتح الوسادة الأمامية للراكب - المرحلة 1"),
                          ("B0011", "Passenger Frontal Stage 2 Deployment Control", "التحكم في فتح الوسادة الأمامية للراكب - المرحلة 2"),
                          ("B0020", "Left Side Airbag Deployment Control", "التحكم في فتح الوسادة الجانبية اليسرى"),
                          ("B0028", "Right Side Airbag Deployment Control", "التحكم في فتح الوسادة الجانبية اليمنى")):
    X(code_, en_t, ar_t,
      "The airbag computer found a fault in the circuit that fires this airbag. The airbag light stays on and this airbag "
      "(sometimes the whole system) may not deploy in a crash. Have it repaired soon by someone trained on airbags.",
      "كمبيوتر الإيرباج وجد عطلاً في الدائرة التي تفتح هذه الوسادة. تبقى لمبة الإيرباج مضاءة وقد لا تفتح هذه الوسادة (وأحيانًا "
      "النظام كله) عند الحادث. أصلحها قريبًا عند شخص مدرّب على الإيرباج.",
      _srs_causes, _srs_checks, sev="amber", drive="caution", system="airbag", tags=["airbag"], related=["U0151"], safety=True,
      source="generic-common")

# ------------------------------------------------------------------ code ranges (fallback)
# (first, last, owner "sae" | "mfr", system, en, ar) - hex digits compare as strings of the same length
RANGES = [
    ("P0000", "P0099", "sae", "fuel-air", "Fuel and air metering and auxiliary emission controls", "قياس الوقود والهواء والتحكم المساعد في الانبعاثات"),
    ("P0100", "P0299", "sae", "fuel-air", "Fuel and air metering", "قياس الوقود والهواء"),
    ("P0300", "P0399", "sae", "ignition", "Ignition system or misfire", "نظام الإشعال أو الاحتراق الناقص"),
    ("P0400", "P0499", "sae", "emissions", "Auxiliary emission controls", "أنظمة التحكم المساعدة في الانبعاثات"),
    ("P0500", "P0599", "sae", "speed-idle", "Vehicle speed, idle control and auxiliary inputs", "سرعة السيارة والتحكم في الخامل والمدخلات المساعدة"),
    ("P0600", "P0699", "sae", "ecu", "Computer and auxiliary outputs", "الكمبيوتر والمخرجات المساعدة"),
    ("P0700", "P0999", "sae", "transmission", "Transmission", "ناقل الحركة (الفتيس)"),
    ("P0A00", "P0AFF", "sae", "hybrid", "Hybrid / electric propulsion", "أنظمة الدفع الهجين / الكهربائي"),
    ("P1000", "P1FFF", "mfr", "powertrain", "Manufacturer-specific powertrain code", "كود محرك/فتيس خاص بالمصنّع"),
    ("P2000", "P2FFF", "sae", "powertrain", "Generic powertrain (fuel, air, emissions, ignition, transmission)", "كود محرك/فتيس عام (وقود، هواء، انبعاثات، إشعال، فتيس)"),
    ("P3000", "P33FF", "mfr", "powertrain", "Manufacturer-specific powertrain code", "كود محرك/فتيس خاص بالمصنّع"),
    ("P3400", "P34FF", "sae", "vvt", "Cylinder deactivation", "إيقاف الأسطوانات"),
    ("P3500", "P3FFF", "sae", "powertrain", "Generic powertrain (reserved / newer assignments)", "كود محرك/فتيس عام (محجوز أو تخصيصات أحدث)"),
    ("B0000", "B0FFF", "sae", "body", "Generic body code (airbags, seats, climate, lighting ...)", "كود هيكل عام (وسائد هوائية، كراسي، تكييف، إضاءة ...)"),
    ("B1000", "B2FFF", "mfr", "body", "Manufacturer-specific body code", "كود هيكل خاص بالمصنّع"),
    ("B3000", "B3FFF", "sae", "body", "Generic body code (reserved)", "كود هيكل عام (محجوز)"),
    ("C0000", "C0FFF", "sae", "abs-brakes", "Generic chassis code (brakes, ABS, steering, suspension)", "كود شاسيه عام (فرامل، ABS، توجيه، تعليق)"),
    ("C1000", "C2FFF", "mfr", "abs-brakes", "Manufacturer-specific chassis code", "كود شاسيه خاص بالمصنّع"),
    ("C3000", "C3FFF", "sae", "abs-brakes", "Generic chassis code (reserved)", "كود شاسيه عام (محجوز)"),
    ("U0000", "U0FFF", "sae", "network", "Generic network communication code", "كود شبكة اتصال عام"),
    ("U1000", "U2FFF", "mfr", "network", "Manufacturer-specific network code", "كود شبكة خاص بالمصنّع"),
    ("U3000", "U3FFF", "sae", "network", "Generic network code (reserved)", "كود شبكة عام (محجوز)"),
]
