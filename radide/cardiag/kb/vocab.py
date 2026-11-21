"""Names of systems, readiness monitors, severities and symptom concepts (English + Arabic), and the words people
use for symptoms (including Egyptian colloquial Arabic) so a search for "سخونية" or "overheating" finds the codes."""
from __future__ import annotations

import re

SYSTEMS = {
    "fuel-air": ("Fuel and air metering", "الوقود والهواء"), "vvt": ("Valve timing", "توقيت الصبابات"),
    "ignition": ("Ignition / misfire", "الإشعال / الاحتراق"), "emissions": ("Emission controls", "التحكم في الانبعاثات"),
    "evap": ("Fuel vapour (EVAP)", "أبخرة الوقود (EVAP)"), "turbo": ("Turbo / boost", "التيربو / الضغط"),
    "cooling": ("Engine cooling", "تبريد المحرك"), "oil": ("Engine oil", "زيت المحرك"),
    "exhaust-aftertreatment": ("Exhaust after-treatment (DPF, NOx)", "معالجة العادم (DPF وNOx)"),
    "speed-idle": ("Speed and idle control", "السرعة والتحكم في الخامل"), "charging": ("Battery and charging", "البطارية والشحن"),
    "starting": ("Starting", "التشغيل (المارش)"), "ac": ("Air conditioning", "التكييف"), "steering": ("Steering", "التوجيه (الدركسيون)"),
    "abs-brakes": ("Brakes / ABS / ESP", "الفرامل / ABS / ESP"), "cruise": ("Cruise control", "مثبت السرعة"),
    "ecu": ("Control modules", "وحدات التحكم"), "transmission": ("Transmission", "ناقل الحركة (الفتيس)"),
    "electrical": ("Electrical", "الكهرباء"), "network": ("Network communication", "شبكة الاتصال"),
    "airbag": ("Airbags (SRS)", "الوسائد الهوائية (SRS)"), "body": ("Body", "الهيكل والكماليات"),
    "hybrid": ("Hybrid / electric", "الهجين / الكهربائي"), "powertrain": ("Powertrain", "المحرك وناقل الحركة"),
}
MONITORS = {
    "components": ("Comprehensive components (always tested)", "المكونات الشاملة (تُختبر باستمرار)"),
    "misfire": ("Misfire monitor", "مراقب الاحتراق الناقص"), "fuel": ("Fuel system monitor", "مراقب نظام الوقود"),
    "catalyst": ("Catalyst monitor", "مراقب الدبّة"), "heated-catalyst": ("Heated catalyst monitor", "مراقب الدبّة المسخّنة"),
    "evap": ("EVAP system monitor", "مراقب نظام EVAP"), "secondary-air": ("Secondary air monitor", "مراقب الهواء الثانوي"),
    "o2": ("Oxygen sensor monitor", "مراقب حساس الأكسجين"), "o2-heater": ("Oxygen sensor heater monitor", "مراقب سخان حساس الأكسجين"),
    "egr": ("EGR system monitor", "مراقب نظام EGR"), "nox": ("NOx after-treatment monitor", "مراقب معالجة NOx"),
    "pm": ("Particulate filter monitor", "مراقب فلتر الجزيئات"), "egt": ("Exhaust gas sensor monitor", "مراقب حساس العادم"),
    "boost": ("Boost pressure monitor", "مراقب ضغط التيربو"),
}
SEVERITY = {
    "green": ("Low - fix when convenient", "منخفضة - أصلحه في وقت مناسب"),
    "amber": ("Medium - get it checked soon", "متوسطة - افحصه قريبًا"),
    "red": ("High - stop and fix before driving", "عالية - توقف وأصلحه قبل القيادة"),
}
SEVERITY_COLOR = {"green": "#2e9d4f", "amber": "#d98a00", "red": "#d33a2c"}

# symptom concept id -> (English, Arabic, words that mean it - English and Arabic, normalized at load time)
TAGS = {
    "overheating": ("Engine overheats", "المحرك يسخن (سخونية)",
                    ["overheat", "overheating", "hot engine", "temperature high", "temp gauge high", "boiling", "steam",
                     "سخونيه", "سخونية", "بتسخن", "يسخن", "تسخين", "سخن", "الحراره عاليه", "حراره عاليه", "حرارة المحرك",
                     "الميه بتغلي", "بتغلي", "بخار", "فوران", "العداد بيعلى", "الحراره بتعلى"]),
    "rough-idle": ("Rough or shaking idle", "رجّة في الوضع الخامل",
                   ["rough idle", "shaking", "shakes", "vibration at idle", "unstable idle", "idle", "رجه", "رجة", "بترج",
                    "بتهز", "رعشه", "رعشة", "بترتعش", "تنتيش", "بتنتش", "الموتور بيرج", "خامل", "مش مستقره"]),
    "shaking": ("Engine shakes / vibrates", "المحرك يهتز",
                ["shake", "shaking", "vibrate", "vibration", "jerking", "رجه", "اهتزاز", "بتهز", "بترج", "بتنتع", "رعشه"]),
    "misfire": ("Misfire", "احتراق ناقص (تقطيع)",
                ["misfire", "missing", "stutter", "تقطيع", "بتقطع", "مقطعه", "احتراق ناقص", "سلندر واقع", "بوجيه",
                 "موبينه", "بتفوت"]),
    "no-start": ("Engine will not start", "المحرك لا يدور",
                 ["no start", "won't start", "wont start", "doesn't start", "cranks no start", "hard to start",
                  "مش بتدور", "مبتدورش", "مش راضيه تدور", "لا تدور", "لا يدور", "ما بتشتغلش", "مش بتشتغل", "بتدور ومش بتمسك",
                  "بتفضل تدور", "مش بيدور", "مبيدورش", "مش بيشتغل", "مبيشتغلش", "مش راضي يدور", "won t start"]),
    "no-crank": ("Starter does not turn", "المارش لا يلف",
                 ["no crank", "starter not turning", "click no start", "المارش مش بيلف", "مارش", "تكه ومش بتدور"]),
    "hard-start": ("Hard starting", "صعوبة في التشغيل",
                   ["hard start", "slow start", "long crank", "difficult to start", "صعوبه في التشغيل", "صعوبة التشغيل",
                    "بتاخد وقت", "تقيله في الدوران", "على البارد"]),
    "stalling": ("Engine stalls / dies", "المحرك يطفئ فجأة",
                 ["stall", "stalls", "dies", "cuts out", "engine off while driving", "بتطفي", "بتفصل", "بتموت",
                  "تطفي لوحدها", "بتقف", "بتفصل وهي ماشيه"]),
    "low-power": ("Lack of power", "ضعف في العزم (السحب)",
                  ["low power", "no power", "lack of power", "sluggish", "weak", "slow acceleration", "ضعف", "ضعيفه",
                   "مفيهاش سحب", "مش بتسحب", "تقيله", "سحب ضعيف", "عزم ضعيف", "مش طالعه"]),
    "limp-mode": ("Limp mode (reduced power)", "وضع الطوارئ (قدرة محدودة)",
                  ["limp", "limp mode", "reduced power", "safe mode", "emergency mode", "وضع الطوارئ", "طوارئ",
                   "مش بتعدي", "قافله على", "مش بتزود"]),
    "hesitation": ("Hesitation when accelerating", "تردد أو تأخر عند الدوس",
                   ["hesitation", "hesitate", "flat spot", "delay on throttle", "تردد", "بتتأخر", "بتشرق", "بتكح"]),
    "fuel-consumption": ("High fuel consumption", "استهلاك وقود عالي",
                         ["fuel consumption", "uses more fuel", "bad mileage", "economy", "استهلاك", "بتصرف", "بتشرب بنزين",
                          "صرف عالي", "بتاكل بنزين"]),
    "smoke": ("Smoke from the exhaust", "دخان من الشكمان",
              ["smoke", "black smoke", "white smoke", "blue smoke", "دخان", "شكمان بيطلع دخان", "دخان اسود",
               "دخان ابيض", "دخان ازرق", "بتدخن"]),
    "smell": ("Fuel or exhaust smell", "رائحة بنزين أو عادم",
              ["smell", "fuel smell", "rotten egg", "ريحه", "ريحة", "رائحه", "ريحة بنزين", "ريحه بيض"]),
    "noise": ("Unusual engine noise", "صوت غير طبيعي",
              ["noise", "rattle", "ticking", "knocking noise", "whine", "صوت", "تكتكه", "خشخشه", "طقطقه", "صفير"]),
    "knock": ("Pinging / knocking", "طرق (صفقة)", ["knock", "pinging", "pinking", "detonation", "صفقه", "طرق", "تخبيط"]),
    "hard-shift": ("Harsh or wrong gear shifting", "نقلات غيار عنيفة أو خاطئة",
                   ["hard shift", "harsh shift", "slipping gear", "no shift", "transmission", "gearbox", "نقلات",
                    "الفتيس", "بتخبط", "الغيارات", "مش بتغير", "رفسه", "جيربوكس"]),
    "slipping": ("Transmission slips", "الفتيس يفلت", ["slipping", "slip", "rpm flare", "بتفلت", "فلتان", "بيزحلق"]),
    "shudder": ("Shudder at cruise", "رعشة أثناء السير", ["shudder", "judder", "رعشه وهي ماشيه", "بترتعش"]),
    "speedometer": ("Speedometer problem", "مشكلة في عداد السرعة", ["speedometer", "speed gauge", "عداد السرعه", "العداد واقف"]),
    "cruise": ("Cruise control does not work", "مثبت السرعة لا يعمل", ["cruise", "cruise control", "مثبت السرعه", "كروز"]),
    "battery": ("Battery / charging problem", "مشكلة في البطارية أو الشحن",
                ["battery", "charging", "alternator", "voltage", "بطاريه", "البطاريه", "شحن", "دينامو", "بتفضي"]),
    "battery-light": ("Battery light on", "لمبة البطارية مضاءة", ["battery light", "charging light", "لمبة البطاريه"]),
    "battery-drain": ("Battery drains when parked", "البطارية تفرغ والسيارة واقفة", ["drain", "flat battery", "بتفضي", "تفريغ البطاريه"]),
    "electrical": ("Electrical problems", "مشاكل كهرباء", ["electrical", "electric", "كهربا", "كهرباء", "فيوز"]),
    "ac": ("Air conditioning problem", "مشكلة في التكييف", ["ac", "a/c", "air conditioning", "تكييف", "التكييف", "مش بيبرد"]),
    "fan": ("Radiator fan problem", "مشكلة في مروحة الرادياتير", ["fan", "radiator fan", "مروحه", "المروحه", "مراوح", "مروحة"]),
    "heater-cold": ("Heater blows cold / slow warm-up", "الدفاية باردة / المحرك يسخن ببطء",
                    ["heater cold", "no heat", "slow warm up", "دفايه", "الدفايه", "بتسخن ببطء", "مش بتسخن"]),
    "oil-light": ("Oil pressure light", "لمبة الزيت", ["oil light", "oil pressure", "لمبة الزيت", "ضغط الزيت", "الزيت"]),
    "abs": ("ABS light / ABS problem", "لمبة ABS", ["abs", "anti lock", "اي بي اس", "ابس", "لمبة abs"]),
    "esp": ("ESP / traction light", "لمبة ESP / التحكم في الجر", ["esp", "traction", "stability", "esc", "tcs", "لمبة esp"]),
    "brakes": ("Brake problem", "مشكلة في الفرامل", ["brake", "brakes", "فرامل", "الفرامل", "فرامل ضعيفه"]),
    "brake-lights": ("Brake lights", "لمبات الفرامل", ["brake light", "stop light", "لمبات الفرامل", "استوب"]),
    "airbag": ("Airbag light", "لمبة الإيرباج", ["airbag", "srs", "air bag", "ايرباج", "الوسايد", "وساده هوائيه"]),
    "steering": ("Steering problem", "مشكلة في الدركسيون", ["steering", "power steering", "دركسيون", "الدريكسيون", "تقيل"]),
    "tpms": ("Tyre pressure warning", "تحذير ضغط الإطارات", ["tpms", "tyre pressure", "tire pressure", "ضغط الكاوتش", "كاوتش"]),
    "network": ("Communication fault between modules", "عطل اتصال بين الوحدات", ["communication", "can bus", "network", "اتصال", "شبكه"]),
    "multiple-codes": ("Many codes at once", "أكواد كثيرة في نفس الوقت", ["many codes", "multiple codes", "اكواد كتير", "اعطال كتير"]),
    "warning-light": ("Warning light on", "لمبة تحذير مضاءة", ["warning light", "light on", "لمبه منوره", "لمبة منورة", "لمبه"]),
    "high-idle": ("Idle too high", "دوران خامل عالي", ["high idle", "idle high", "سرعه عاليه وهي واقفه", "عاليه في الخامل"]),
    "gauge": ("Gauge reads wrong", "مؤشر يقرأ خطأ", ["gauge", "fuel gauge", "عداد البنزين", "المؤشر"]),
    "fuel-filling": ("Trouble filling the tank", "صعوبة تمويل البنزين", ["filling", "refuel", "pump clicks off", "التمويل", "تفويل"]),
    "emissions-test": ("Failed emissions test", "رسوب في فحص العادم", ["emissions test", "smog", "فحص العادم", "الفحص الفني"]),
    "4wd": ("4x4 problem", "مشكلة الدفع الرباعي", ["4wd", "4x4", "awd", "دفع رباعي"]),
    "lights": ("Lights problem", "مشكلة في الإضاءة", ["lights", "headlight", "النور", "الفوانيس"]),
    "start-stop": ("Start-stop does not work", "نظام Start-Stop لا يعمل", ["start stop", "start-stop", "ستارت ستوب"]),
    "reverse-lights": ("Reverse lights", "لمبات الرجوع", ["reverse light", "لمبة الرجوع"]),
    "steam": ("Steam from the engine bay", "بخار من الكبوت", ["steam", "بخار", "بيطلع بخار"]),
}

_TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")


def norm(text: str) -> str:
    """Lower-case English, Arabic without diacritics / tatweel and with unified letters (أإآ->ا, ة->ه, ى->ي ...)."""
    t = _TASHKEEL.sub("", str(text or "")).lower()
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي"),
                 ("گ", "ك"), ("ڤ", "ف"), ("‎", ""), ("‏", "")):
        t = t.replace(a, b)
    t = re.sub(r"[^\w\s/+-]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tag_words() -> dict[str, list[str]]:
    return {k: [norm(w) for w in v[2]] + [norm(v[0]), norm(v[1])] for k, v in TAGS.items()}


def name(table: dict, key: str, lang: str = "en") -> str:
    v = table.get(key)
    if v is None:
        return key
    return v[1] if lang == "ar" else v[0]
