"""Dashboard warning-light guide (docs/CARDIAG.md "Fault knowledge base").

    from radide.cardiag.kb import lights
    lights.LIGHTS                       # id -> Light (names, colours, meaning, what to do, related systems / tags)
    lights.svg("coolant", "red")        # original SVG icon (drawn for RAD IDE), coloured
    lights.pick(["mil", "coolant"])     # the "What light is on?" picker: likely codes, advice, scan hint

Every icon is RAD IDE's own drawing (simple strokes on a 64 x 64 grid) that only follows the general idea of the
ISO 2575 symbols drivers know; every text is RAD IDE's own wording.
"""
from __future__ import annotations

from dataclasses import dataclass, field

COLOURS = {
    "red": ("#d33a2c", "Red - stop safely and check before driving on",
            "أحمر - توقف في مكان آمن وافحص قبل استكمال القيادة"),
    "amber": ("#e09a00", "Amber / yellow - have it checked soon; the car is usually drivable with care",
              "برتقالي / أصفر - افحصه قريبًا؛ غالبًا يمكن القيادة بحذر"),
    "flashing": ("#e09a00", "Flashing amber - a serious fault is happening right now: reduce load and speed",
                 "برتقالي يومض - عطل خطير يحدث الآن: خفف الحمل والسرعة"),
    "green": ("#2e9d4f", "Green - information only (a system is switched on)", "أخضر - معلومة فقط (نظام يعمل)"),
    "blue": ("#2f6fd6", "Blue - information only", "أزرق - معلومة فقط"),
}


@dataclass
class Light:
    id: str
    name: tuple                 # (en, ar)
    colours: tuple              # colour ids (COLOURS), most common first
    meaning: tuple              # (en, ar)
    do_now: dict                # colour -> (en, ar)
    systems: tuple = ()         # vocab.SYSTEMS ids whose codes may be behind it
    tags: tuple = ()            # vocab.TAGS ids
    codes: tuple = ()           # typical generic codes (shown first)
    prefixes: tuple = ()        # code prefixes ("C0", "B00") that belong to it
    obd: bool = True            # True: a generic OBD-II scan (engine computer) can see the related codes
    module: tuple = ("", "")    # control unit that holds the codes when not OBD (en, ar)
    svg_body: str = ""
    safety: bool = False
    keywords: tuple = field(default_factory=tuple)


# --------------------------------------------------------------------------------------------- icons (original)
_ICON = {
    "mil": ('<path d="M14 26h6v-6h14v6h6l4 5h6v-5h4v18h-4v-5h-6v8H26l-6-6h-6z"/><path d="M24 20v-4h10v4"/>'
               '<path d="M8 30v10M8 35h6"/>'),
    "oil": ('<path d="M10 30h12l6-6h18l8 6 6-4"/><path d="M10 30v6h40l8-8"/><path d="M14 30v-5h6"/>'
               '<path d="M58 34c0 3-2 5-2 7a2 2 0 0 0 4 0c0-2-2-4-2-7z"/><path d="M22 36v8h24v-8"/>'),
    "coolant": ('<path d="M32 8v28"/><circle cx="32" cy="42" r="6"/><path d="M32 14h7M32 21h7M32 28h7"/>'
                   '<path d="M10 52c4-3 7 3 11 0s7 3 11 0 7 3 11 0 7 3 11 0"/>'),
    "battery": ('<rect x="10" y="20" width="44" height="28" rx="2"/><path d="M16 20v-5h8v5M40 20v-5h8v5"/>'
                   '<path d="M16 33h8M44 29v8M40 33h8"/>'),
    "abs": ('<circle cx="32" cy="32" r="16"/><path d="M12 18a24 24 0 0 0 0 28M52 18a24 24 0 0 1 0 28"/>'
               '<text x="32" y="37" font-size="13" font-family="Arial" font-weight="bold" text-anchor="middle" '
               'stroke="none" fill="currentColor">ABS</text>'),
    "brake": ('<circle cx="32" cy="32" r="16"/><path d="M12 18a24 24 0 0 0 0 28M52 18a24 24 0 0 1 0 28"/>'
                 '<path d="M32 23v12"/><circle cx="32" cy="41" r="1.6" fill="currentColor"/>'),
    "airbag": ('<circle cx="24" cy="12" r="5"/><path d="M22 20l-4 18h16l8 14"/><path d="M20 30l12 2"/>'
                  '<circle cx="44" cy="28" r="10"/><path d="M14 46h14"/>'),
    "tpms": ('<path d="M18 16c-6 10-6 22 0 32M46 16c6 10 6 22 0 32"/><path d="M18 48h28M18 16h4M42 16h4"/>'
                '<path d="M14 52l4-4M50 52l-4-4"/><path d="M32 22v14"/><circle cx="32" cy="42" r="1.6" '
                'fill="currentColor"/>'),
    "esp": ('<path d="M16 34l4-10h24l4 10v8H16z"/><circle cx="22" cy="42" r="3"/><circle cx="42" cy="42" r="3"/>'
               '<path d="M14 54c4-4 8 0 12-4M38 54c4-4 8 0 12-4"/>'),
    "glow": ('<path d="M10 20v24M54 20v24"/><path d="M10 32c4-12 8 12 12 0s8 12 12 0 8 12 12 0 6 8 8 0"/>'),
    "dpf": ('<rect x="14" y="20" width="36" height="24" rx="4"/><path d="M6 32h8M50 32h8"/>'
               '<circle cx="24" cy="28" r="1.6" fill="currentColor"/><circle cx="32" cy="34" r="1.6" '
               'fill="currentColor"/><circle cx="40" cy="28" r="1.6" fill="currentColor"/><circle cx="26" cy="38" '
               'r="1.6" fill="currentColor"/><circle cx="38" cy="38" r="1.6" fill="currentColor"/>'),
    "eps": ('<circle cx="30" cy="32" r="16"/><circle cx="30" cy="32" r="4"/><path d="M14 32h12M34 32h12M30 36v12"/>'
               '<path d="M54 18v14"/><circle cx="54" cy="38" r="1.6" fill="currentColor"/>'),
    "service": ('<path d="M40 10a10 10 0 0 0-12 13L12 39a4 4 0 0 0 6 6l16-16a10 10 0 0 0 13-12l-6 6-6-2-2-6z"/>'),
    "transmission": ('<circle cx="32" cy="32" r="8"/><path d="M32 12v6M32 46v6M12 32h6M46 32h6M18 18l4 4M42 42l4 4'
                        'M18 46l4-4M42 22l4-4"/><path d="M32 28v4"/><circle cx="32" cy="36" r="1.4" '
                        'fill="currentColor"/>'),
    "fuel": ('<rect x="14" y="14" width="22" height="38" rx="2"/><path d="M14 26h22"/>'
                '<path d="M36 24h6l6 6v16a3 3 0 0 0 6 0V22l-6-6"/><path d="M10 52h30"/>'),
    "key": ('<path d="M14 18l6-6h24l6 6-4 22H18z"/><circle cx="40" cy="44" r="6"/><path d="M36 48L24 60M28 56l-4-4"/>'),
    "adblue": ('<path d="M32 10c-8 12-14 20-14 28a14 14 0 0 0 28 0c0-8-6-16-14-28z"/>'
                  '<path d="M8 48c4-3 7 3 11 0M45 48c4-3 7 3 11 0"/>'),
    "water-fuel": ('<rect x="16" y="18" width="20" height="34" rx="2"/><path d="M36 26h6v14"/>'
                      '<path d="M26 26c-4 6-6 9-6 12a6 6 0 0 0 12 0c0-3-2-6-6-12z"/>'),
    "temp-blue": ('<path d="M32 8v28"/><circle cx="32" cy="42" r="6"/><path d="M32 14h7M32 21h7M32 28h7"/>'),
}

# --------------------------------------------------------------------------------------------- the lights
_L = [
    Light("mil", ("Check engine (MIL)", "لمبة فحص المحرك (Check Engine)"), ("amber", "flashing"),
          ("The engine computer found a fault that affects emissions or how the engine runs and stored a trouble code. "
           "It can be anything from a loose fuel cap to a misfiring cylinder.",
           "كمبيوتر المحرك اكتشف عطلاً يؤثر على الانبعاثات أو على أداء المحرك وسجّل كود عطل. ممكن يكون أي شيء من غطاء "
           "تانك البنزين غير محكم إلى سلندر لا يشتغل."),
          {"amber": ("Read the codes with the scan tool, look at the explanation and the freeze frame. Drive gently "
                     "until it is checked.",
                     "اقرأ الأكواد بجهاز الفحص واقرأ الشرح ولقطة التجميد (Freeze frame). قُد بهدوء حتى يتم الفحص."),
           "flashing": ("A flashing MIL means a heavy misfire that can overheat and ruin the catalytic converter. "
                        "Reduce speed and load straight away and avoid long drives until it is repaired.",
                        "اللمبة التي تومض معناها احتراق ناقص شديد قد يسخّن الدبّة (الكتلايزر) ويتلفها. خفف السرعة والحمل "
                        "فورًا وتجنب المشاوير الطويلة حتى الإصلاح.")},
          systems=("fuel-air", "ignition", "emissions", "evap", "vvt", "exhaust-aftertreatment", "turbo"),
          tags=("misfire", "rough-idle", "low-power", "fuel-consumption", "emissions-test"),
          codes=("P0300", "P0171", "P0420", "P0455", "P0101", "P0128", "P0442", "P0174"), prefixes=("P0", "P2"),
          keywords=("check engine", "engine light", "مكنه", "لمبه المكنه", "لمبه الموتور", "تشيك انجن", "check")),
    Light("oil", ("Oil pressure", "ضغط الزيت"), ("red", "amber"),
          ("Red: the oil pressure is too low to protect the engine. Amber (on some cars): the oil level is low or the "
           "oil sensor has a fault.",
           "أحمر: ضغط الزيت أقل من اللازم لحماية المحرك. أصفر (في بعض العربيات): مستوى الزيت منخفض أو حساس الزيت به عطل."),
          {"red": ("Stop as soon as it is safe and switch the engine off - running without oil pressure destroys the "
                   "engine within minutes. Check the oil level with the dipstick after a few minutes; do not drive "
                   "on if the light stays on.",
                   "توقف في أقرب مكان آمن وأطفئ المحرك - التشغيل بدون ضغط زيت يدمر المحرك في دقائق. افحص مستوى الزيت "
                   "بالعصا بعد دقائق، ولا تكمل القيادة لو اللمبة فضلت منورة."),
           "amber": ("Check the oil level and top up with the correct oil. If the level is fine, read the codes.",
                     "افحص مستوى الزيت وكمّله بالنوع الصحيح. لو المستوى سليم اقرأ الأكواد.")},
          systems=("oil",), tags=("oil-light",), codes=("P0520", "P0521", "P0522", "P0523", "P0524"),
          safety=True, keywords=("oil", "زيت", "لمبه الزيت", "ابريق")),
    Light("coolant", ("Coolant temperature", "حرارة المحرك (سائل التبريد)"), ("red", "amber"),
          ("Red: the engine is overheating. Amber (on some cars): the coolant level is low or the temperature sensor "
           "has a fault.",
           "أحمر: المحرك يسخن (سخونية). أصفر (في بعض العربيات): مستوى المياه / سائل التبريد منخفض أو حساس الحرارة به عطل."),
          {"red": ("Stop safely and switch the engine off. Do NOT open the radiator or expansion-tank cap while hot - "
                   "the coolant is under pressure and can burn you. Let it cool for at least 30 minutes, then check "
                   "the level, the fan and for leaks.",
                   "توقف بأمان وأطفئ المحرك. لا تفتح غطاء الردياتير أو قربة المياه وهو ساخن - السائل تحت ضغط وقد "
                   "يحرقك. اتركه يبرد 30 دقيقة على الأقل ثم افحص المستوى والمروحة والتسريب."),
           "amber": ("Check the coolant level when the engine is cold and top up with the right coolant. Watch the "
                     "temperature in Live Data.",
                     "افحص مستوى سائل التبريد والمحرك بارد وكمّله بالنوع الصحيح. راقب الحرارة في البيانات الحية.")},
          systems=("cooling",), tags=("overheating", "fan", "steam"),
          codes=("P0217", "P0118", "P0117", "P0128", "P0480", "P0115", "P2181", "P0116"), safety=True,
          keywords=("temperature", "temp", "حراره", "سخونيه", "ترمومتر", "مياه")),
    Light("temp-blue", ("Engine cold (blue temperature)", "المحرك بارد (حرارة زرقاء)"), ("blue",),
          ("The engine has not reached working temperature yet. It goes off after a few minutes of driving.",
           "المحرك لم يصل لدرجة حرارة التشغيل بعد. تنطفئ بعد دقائق من القيادة."),
          {"blue": ("Drive gently until it goes off. If it stays on for a long time the thermostat may be stuck open "
                    "(code P0128).",
                    "قُد بهدوء حتى تنطفئ. لو فضلت منورة وقت طويل قد يكون الثرموستات مفتوحًا باستمرار (كود P0128).")},
          systems=("cooling",), tags=("heater-cold",), codes=("P0128", "P0125", "P0116"),
          keywords=("blue", "cold", "ازرق", "بارد")),
    Light("battery", ("Battery / charging", "البطارية / الشحن"), ("red",),
          ("The charging system is not charging the battery: the car is running on the battery alone and will stop "
           "when it is empty.",
           "نظام الشحن لا يشحن البطارية: العربية تعمل على البطارية فقط وستقف عندما تفرغ."),
          {"red": ("Switch off what you do not need (A/C, heated seats, radio) and drive to a workshop or home "
                   "without stopping the engine. If the battery light comes with overheating, the belt may be broken "
                   "- stop.",
                   "أطفئ الأحمال غير الضرورية (التكييف، تدفئة الكراسي، الراديو) واذهب للورشة أو البيت بدون إطفاء "
                   "المحرك. لو جاءت لمبة البطارية مع سخونية فقد يكون السير مقطوعًا - توقف.")},
          systems=("charging",), tags=("battery-light", "battery", "electrical"),
          codes=("P0562", "P0563", "P0620", "P0622", "P0560", "P0561", "P065B"),
          keywords=("battery", "charging", "بطاريه", "دينامو", "شحن", "الكهربا")),
    Light("abs", ("ABS", "لمبة ABS"), ("amber",),
          ("The anti-lock braking system has switched itself off because of a fault. The normal brakes still work, "
           "but the wheels can lock under hard braking.",
           "نظام منع انغلاق الفرامل (ABS) أوقف نفسه بسبب عطل. الفرامل العادية تعمل، لكن العجل ممكن يقفل في الفرملة القوية."),
          {"amber": ("Drive carefully and leave more distance; avoid hard braking. Read the codes of the ABS / ESP "
                     "control unit (not visible to a generic OBD engine scan). A wheel-speed sensor is the most "
                     "common cause.",
                     "قُد بحذر واترك مسافة أكبر وتجنب الفرملة القوية. اقرأ أكواد وحدة ABS / ESP (لا تظهر في فحص "
                     "المحرك العادي). حساس سرعة العجل هو السبب الأكثر شيوعًا.")},
          systems=("abs-brakes",), tags=("abs", "esp"), prefixes=("C0",),
          codes=("C0035", "C0040", "C0045", "C0050", "C0036", "C0041"), obd=False,
          module=("ABS / ESP control unit", "وحدة التحكم ABS / ESP"), safety=True,
          keywords=("abs", "فرامل", "مانع انغلاق")),
    Light("brake", ("Brake system", "نظام الفرامل"), ("red",),
          ("The hand brake is on, the brake fluid level is low, or the brake system has a fault (on many cars also "
           "the electronic brake-force distribution).",
           "فرامل اليد مشدودة، أو مستوى زيت الفرامل منخفض، أو في نظام الفرامل عطل (في كثير من العربيات أيضًا توزيع "
           "قوة الفرامل الإلكتروني)."),
          {"red": ("Make sure the hand brake is fully released. If the light stays on, stop safely and check the brake "
                   "fluid level - a low level can mean worn pads or a leak. Do not drive if the pedal feels soft.",
                   "تأكد أن فرامل اليد منزلة بالكامل. لو فضلت اللمبة منورة توقف بأمان وافحص مستوى زيت الفرامل - "
                   "المستوى المنخفض قد يعني تيل فرامل متآكل أو تسريب. لا تقود لو الدواسة لينة.")},
          systems=("abs-brakes",), tags=("brakes",), codes=("C0110", "C0121", "C0161", "C0040"), obd=False,
          module=("ABS / brake control unit", "وحدة الفرامل / ABS"), safety=True, prefixes=("C0",),
          keywords=("brake", "handbrake", "فرامل", "فرامل اليد", "تيل")),
    Light("airbag", ("Airbag / SRS", "الوسادة الهوائية (Airbag)"), ("red", "amber"),
          ("The airbag control unit found a fault. Airbags and belt pretensioners may NOT deploy in a crash.",
           "وحدة الوسائد الهوائية وجدت عطلاً. قد لا تنفتح الوسائد ولا تشد الأحزمة في حالة حادث."),
          {"red": ("Have it checked soon. Do not disconnect airbag connectors yourself with the ignition on; read the "
                   "codes of the airbag unit (not visible to a generic OBD engine scan). A seat connector or the "
                   "steering-wheel clock spring are common causes.",
                   "افحصه قريبًا. لا تفصل أفيشات الوسائد بنفسك والكونتاكت شغال؛ اقرأ أكواد وحدة الوسائد (لا تظهر في "
                   "فحص المحرك العادي). فيشة تحت الكرسي أو الإسبرنج الحلزوني في الدركسيون أسباب شائعة."),
           "amber": ("Same as red: the passenger may not be protected. Have the airbag unit's codes read.",
                     "مثل الأحمر: قد لا تتوفر الحماية للركاب. اقرأ أكواد وحدة الوسائد.")},
          systems=("airbag",), tags=("airbag",), prefixes=("B00",), codes=("B0001", "B0002", "B0010", "B0011", "B0020", "B0028"),
          obd=False, module=("Airbag (SRS) control unit", "وحدة الوسائد الهوائية (SRS)"), safety=True,
          keywords=("airbag", "srs", "ايرباج", "وساده")),
    Light("tpms", ("Tyre pressure (TPMS)", "ضغط الإطارات (TPMS)"), ("amber",),
          ("At least one tyre is under-inflated. Flashing for about a minute and then steady: the TPMS system itself "
           "has a fault (sensor battery, sensor not learned).",
           "إطار واحد على الأقل ضغطه منخفض. لو تومض حوالي دقيقة ثم تثبت: نظام TPMS نفسه به عطل (بطارية حساس، حساس غير "
           "متعرَّف عليه)."),
          {"amber": ("Check all tyre pressures cold, including the spare if it has a sensor, and inflate to the value on "
                     "the door-pillar sticker. Look for a nail. Some cars need a TPMS reset after inflating.",
                     "افحص ضغط كل الإطارات وهي باردة (والاستبن لو فيه حساس) ونفخها حسب الملصق على عمود الباب. ابحث "
                     "عن مسمار. بعض العربيات تحتاج إعادة ضبط TPMS بعد النفخ.")},
          systems=("body",), tags=("tpms",), codes=(), obd=False,
          module=("TPMS / body control unit", "وحدة TPMS / الهيكل"), keywords=("tyre", "tire", "كاوتش", "اطار", "هوا")),
    Light("esp", ("Stability / traction control (ESP)", "التحكم في الثبات / الجر (ESP)"), ("amber", "flashing"),
          ("Flashing while driving: the system is working (a wheel was slipping) - normal. Steady: the stability "
           "system is off or has a fault.",
           "تومض أثناء القيادة: النظام يعمل (عجلة كانت تنزلق) - طبيعي. ثابتة: نظام الثبات مطفأ أو به عطل."),
          {"amber": ("Check that ESP was not switched off with its button. Drive carefully on wet roads. A steady "
                     "light with the ABS light usually points to a wheel-speed sensor; with the check-engine light "
                     "the engine computer may have disabled ESP because of an engine fault.",
                     "تأكد أن ESP لم يُطفأ من زراره. قُد بحذر على الطرق المبللة. اللمبة الثابتة مع لمبة ABS غالبًا "
                     "حساس سرعة عجل؛ ومع لمبة المحرك قد يكون كمبيوتر المحرك أوقف ESP بسبب عطل في المحرك."),
           "flashing": ("Ease off the accelerator - the car is close to losing grip.",
                        "خفف دواسة البنزين - العربية قريبة من فقد التماسك.")},
          systems=("abs-brakes", "steering"), tags=("esp", "abs"), prefixes=("C0",),
          codes=("C0035", "C0040", "C0045", "C0050", "C0051", "C0455"), obd=False,
          module=("ABS / ESP control unit", "وحدة التحكم ABS / ESP"), safety=True,
          keywords=("esp", "traction", "stability", "esc", "انزلاق", "ثبات")),
    Light("glow", ("Glow plugs (diesel)", "شمعات التسخين (ديزل)"), ("amber", "flashing"),
          ("Steady after switching on: the glow plugs are warming - wait until it goes off, then start. Flashing or on "
           "while driving: an engine-management or glow-plug fault (many diesels use this light instead of the MIL).",
           "ثابتة بعد فتح الكونتاكت: الشمعات تسخن - انتظر حتى تنطفئ ثم دوّر. تومض أو منورة أثناء القيادة: عطل في إدارة "
           "المحرك أو الشمعات (كثير من محركات الديزل تستخدمها بدل لمبة المحرك)."),
          {"amber": ("Wait for it to go off before cranking. If it stays on, read the engine codes.",
                     "انتظر حتى تنطفئ قبل التدوير. لو فضلت منورة اقرأ أكواد المحرك."),
           "flashing": ("Read the engine codes; drive gently - the engine may be in limp mode.",
                        "اقرأ أكواد المحرك وقُد بهدوء - قد يكون المحرك في وضع الطوارئ.")},
          systems=("starting", "fuel-air"), tags=("hard-start", "no-start", "limp-mode"),
          codes=("P0380", "P0381", "P0670", "P0671", "P0672", "P0683", "P0087"),
          keywords=("glow", "diesel", "شمعات", "سولار", "ديزل", "سوسته")),
    Light("dpf", ("Diesel particulate filter (DPF)", "فلتر الجزيئات (DPF)"), ("amber",),
          ("The particulate filter is filling with soot faster than it can burn it off during normal driving (often "
           "after many short trips).",
           "فلتر الجزيئات يمتلئ بالسناج أسرع مما يحرقه أثناء القيادة العادية (غالبًا بعد مشاوير قصيرة كثيرة)."),
          {"amber": ("Drive 15-20 minutes at a steady speed above about 60 km/h (motorway) so the filter can "
                     "regenerate. If the light stays on or limp mode starts, a workshop can run a service "
                     "regeneration (Service functions) after checking why it clogged.",
                     "قُد 15-20 دقيقة بسرعة ثابتة أعلى من حوالي 60 كم/س (طريق سريع) ليحرق الفلتر السناج. لو فضلت منورة "
                     "أو دخل المحرك وضع الطوارئ، تستطيع الورشة عمل تجديد خدمي (Service regeneration) من وظائف الخدمة "
                     "بعد فحص سبب الانسداد.")},
          systems=("exhaust-aftertreatment",), tags=("limp-mode", "low-power", "smoke"),
          codes=("P2002", "P2463", "P242F", "P2452", "P2453", "P244A", "P244B"),
          keywords=("dpf", "particulate", "فلتر", "شكمان", "سناج")),
    Light("eps", ("Power steering", "الدركسيون الكهربائي / الباور"), ("red", "amber"),
          ("The power steering assistance has a fault or is reduced. The car can still be steered but it is much "
           "heavier, especially when parking.",
           "مساعد التوجيه به عطل أو المساعدة مخفضة. يمكن توجيه العربية لكن الدركسيون يصبح ثقيلاً جدًا خاصة في الركن."),
          {"red": ("Drive slowly and carefully to a workshop; be ready for heavy steering. Check the battery voltage - "
                   "low voltage often switches electric steering off.",
                   "قُد ببطء وبحذر للورشة واستعد لدركسيون ثقيل. افحص جهد البطارية - الجهد المنخفض كثيرًا ما يوقف "
                   "التوجيه الكهربائي."),
           "amber": ("Restart the engine once; if it stays on, have the steering unit's codes read and check the "
                     "steering-angle calibration (Service functions) after alignment work.",
                     "أعد تشغيل المحرك مرة؛ لو فضلت منورة اقرأ أكواد وحدة التوجيه وافحص معايرة زاوية الدركسيون (وظائف "
                     "الخدمة) بعد ضبط الزوايا.")},
          systems=("steering",), tags=("steering",), codes=("U0131", "P0551", "C0455", "U0126"),
          obd=False, module=("Power steering control unit", "وحدة التوجيه الكهربائي"), safety=True,
          prefixes=("C04", "C05"), keywords=("steering", "eps", "دركسيون", "باور", "تقيل")),
    Light("service", ("Service due", "موعد الصيانة"), ("amber",),
          ("The service interval has expired (oil change / inspection). It is a reminder, not a fault.",
           "انتهى موعد الصيانة (تغيير زيت / فحص دوري). هذا تذكير وليس عطلاً."),
          {"amber": ("Do the service, then reset the reminder (Service functions > oil / service reset, or the "
                     "procedure in the owner's manual).",
                     "اعمل الصيانة ثم صفّر التذكير (وظائف الخدمة > تصفير الزيت / الصيانة، أو الطريقة الموجودة في كتيب "
                     "العربية).")},
          systems=("oil",), tags=("warning-light",), codes=(), obd=False,
          module=("Instrument cluster", "لوحة العدادات (التابلوه)"), keywords=("service", "wrench", "صيانه", "مفتاح")),
    Light("transmission", ("Transmission warning", "تحذير ناقل الحركة (الفتيس)"), ("amber", "red"),
          ("The automatic transmission has a fault or is too hot; it may be in a safe mode with only some gears.",
           "ناقل الحركة الأوتوماتيك به عطل أو حرارته عالية؛ قد يكون في وضع أمان ببعض السرعات فقط."),
          {"amber": ("Drive gently and read the transmission codes. Check the fluid if the car has a dipstick.",
                     "قُد بهدوء واقرأ أكواد الفتيس. افحص الزيت لو للفتيس عصا قياس."),
           "red": ("Stop and let the transmission cool (engine idling in P helps). Driving on can damage it.",
                   "توقف واترك الفتيس يبرد (ترك المحرك دائرًا على P يساعد). الاستمرار قد يتلفه.")},
          systems=("transmission",), tags=("hard-shift", "slipping", "limp-mode"),
          codes=("P0700", "P0715", "P0720", "P0730", "P0740", "P0218", "P0711"),
          keywords=("transmission", "gearbox", "فتيس", "جير", "اوتوماتيك")),
    Light("fuel", ("Low fuel", "الوقود منخفض"), ("amber",),
          ("The fuel level is low - usually about 50 km (30 miles) of range left.",
           "مستوى الوقود منخفض - غالبًا متبقٍ حوالي 50 كم."),
          {"amber": ("Refuel soon. Running a tank dry can damage the fuel pump and, on diesels, needs bleeding.",
                     "موّن قريبًا. تفريغ التانك تمامًا قد يتلف طلمبة البنزين، وفي الديزل يحتاج تنفيس.")},
          systems=("fuel-air",), tags=("fuel-filling",), codes=("P0460", "P0461", "P0462", "P0463"),
          keywords=("fuel", "petrol", "gas", "بنزين", "تانك", "سولار")),
    Light("key", ("Immobiliser / key", "مانع السرقة / المفتاح"), ("amber", "red"),
          ("The car did not recognise the key (key battery flat, wrong key, interference). Flashing with the "
           "ignition off is normal on many cars - the anti-theft system is armed.",
           "العربية لم تتعرف على المفتاح (بطارية المفتاح فارغة، مفتاح خطأ، تشويش). الوميض والكونتاكت مقفول طبيعي في "
           "كثير من العربيات - نظام مانع السرقة مفعّل."),
          {"amber": ("Try the spare key, replace the key battery, hold the key close to the start button / steering "
                     "column. Key programming is done by the dealer or an authorised locksmith - RAD IDE does not "
                     "include immobiliser functions.",
                     "جرّب المفتاح الاحتياطي، غيّر بطارية المفتاح، قرّب المفتاح من زر التشغيل / عمود الدركسيون. برمجة "
                     "المفاتيح تتم عند الوكيل أو فني معتمد - RAD IDE لا يحتوي وظائف مانع السرقة."),
           "red": ("Same as amber. If the engine starts and dies after a second, it is usually the immobiliser.",
                   "مثل البرتقالي. لو المحرك يدور ثم يقف بعد ثانية فالسبب غالبًا مانع السرقة.")},
          systems=("body",), tags=("no-start",), codes=("P0513", "P0633"), obd=True,
          keywords=("key", "immobilizer", "immobiliser", "مفتاح", "مانع سرقه")),
    Light("adblue", ("AdBlue / DEF", "سائل AdBlue (DEF)"), ("amber", "red"),
          ("The AdBlue (diesel exhaust fluid) tank is low or the SCR system has a fault. When it runs out many cars "
           "will not restart.",
           "تانك AdBlue (سائل العادم للديزل) منخفض أو نظام SCR به عطل. عند نفاده كثير من العربيات لا تدور مرة أخرى."),
          {"amber": ("Refill AdBlue soon (the counter shows the remaining distance). If it stays on after filling, "
                     "read the codes.",
                     "املأ AdBlue قريبًا (العداد يبين المسافة المتبقية). لو فضلت منورة بعد الملء اقرأ الأكواد."),
           "red": ("Refill now - the engine may not restart after it is switched off.",
                   "املأ الآن - قد لا يدور المحرك بعد إطفائه.")},
          systems=("exhaust-aftertreatment",), tags=("limp-mode",), codes=("P20EE", "P203F", "P20B9", "P2047", "P204F"),
          keywords=("adblue", "def", "urea", "يوريا")),
    Light("water-fuel", ("Water in fuel (diesel)", "مياه في الوقود (ديزل)"), ("amber",),
          ("The fuel filter's water separator is full of water.", "فاصل المياه في فلتر السولار امتلأ بالمياه."),
          {"amber": ("Drain the water from the fuel filter (see the owner's manual) or have the filter replaced soon - "
                     "water damages the injection pump and injectors.",
                     "صفِّ المياه من فلتر السولار (راجع الكتيب) أو غيّر الفلتر قريبًا - المياه تتلف طلمبة الحقن والرشاشات.")},
          systems=("fuel-air",), tags=("rough-idle", "low-power"), codes=("P2269", "P2264", "P2265"),
          keywords=("water", "fuel filter", "مياه", "فلتر سولار")),
]

LIGHTS: dict[str, Light] = {l.id: l for l in _L}
for _l in _L:
    _l.svg_body = _ICON.get(_l.id, "")


def ids() -> list[str]:
    return [l.id for l in _L]


def get(light_id: str) -> Light | None:
    return LIGHTS.get(light_id)


def colour_hex(colour: str) -> str:
    return COLOURS.get(colour, COLOURS["amber"])[0]


def svg(light_id: str, colour: str = "", size: int = 64) -> str:
    """The light's icon as an SVG document (stroke icon coloured *colour*, default: its most common colour)."""
    l = LIGHTS.get(light_id)
    if l is None:
        return ""
    c = colour_hex(colour or l.colours[0])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 64 64" '
            f'fill="none" stroke="{c}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" '
            f'color="{c}">{l.svg_body.replace("currentColor", c)}</svg>')


def text(pair, lang: str = "en") -> str:
    return pair[1] if lang == "ar" and len(pair) > 1 else pair[0]


def find(query: str) -> list[str]:
    """Light ids whose name / keywords match *query* (English or Arabic)."""
    from . import vocab
    q = vocab.norm(query)
    if not q:
        return []
    out = []
    for l in _L:
        hay = " ".join(vocab.norm(x) for x in (l.name[0], l.name[1], *l.keywords))
        if q in hay or any(w and w in q for w in (vocab.norm(k) for k in l.keywords) if len(w) > 2):
            out.append(l.id)
    return out


def likely_codes(light_ids, limit: int = 40, present: list[str] | None = None) -> list[tuple[str, float]]:
    """[(code, score)] most likely behind these lights: codes the car reported (*present*) first, then each
    light's typical codes, then codes of its systems / symptom tags. Several lights together give codes that fit
    all of them a higher score (e.g. battery + coolant -> a broken belt / fan circuit)."""
    from .. import kb
    known = set(kb.codes())
    scores: dict[str, float] = {}
    sel = [LIGHTS[i] for i in light_ids if i in LIGHTS]
    present = [kb.normalize_code(c)[0] for c in (present or []) if kb.normalize_code(c)]
    for l in sel:
        for rank, c in enumerate(l.codes):
            scores[c] = scores.get(c, 0.0) + 30.0 - rank
        for tag in l.tags:
            for c in kb.codes_for_tag(tag):
                scores[c] = scores.get(c, 0.0) + 3.0
        for sys_ in l.systems:
            for c in kb.codes_for_system(sys_):
                scores[c] = scores.get(c, 0.0) + 1.0
        for p in l.prefixes:
            for c in kb.codes():
                if c.startswith(p):
                    scores[c] = scores.get(c, 0.0) + 0.5
    for c in list(scores):
        info = kb.lookup(c) if c in known else None
        if info is None:
            scores.pop(c)
            continue
        scores[c] += {"red": 2.0, "amber": 1.0}.get(info.get("severity", ""), 0.0)
    for c in present:
        fits = any(c in l.codes or any(c.startswith(p) for p in l.prefixes) for l in sel)
        scores[c] = scores.get(c, 0.0) + (1000.0 if fits else 500.0)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]


# combinations worth a special hint (original advice)
COMBOS = [
    ({"battery", "coolant"}, ("Battery and temperature together often mean the accessory (serpentine) belt has "
                              "slipped off or broken: the alternator and, on many engines, the water pump stop. "
                              "Stop the engine and check the belt.",
                              "البطارية والحرارة معًا غالبًا معناهما أن سير الدينامو خرج أو انقطع: يقف الدينامو وفي "
                              "كثير من المحركات طلمبة المياه أيضًا. أطفئ المحرك وافحص السير.")),
    ({"abs", "brake"}, ("ABS and brake lights together: the brake-force distribution may be off as well. Drive very "
                        "carefully to a workshop or have the car towed.",
                        "لمبة ABS ولمبة الفرامل معًا: قد يكون توزيع قوة الفرامل متوقفًا أيضًا. قُد بحذر شديد للورشة أو "
                        "اطلب ونش.")),
    ({"abs", "esp"}, ("ABS and ESP together usually point to one wheel-speed sensor or its wiring: read the ABS unit.",
                      "ABS وESP معًا غالبًا يشيران لحساس سرعة عجل واحد أو أسلاكه: اقرأ أكواد وحدة ABS.")),
    ({"mil", "esp"}, ("Check engine with ESP: the engine computer often switches stability control off when it has "
                      "an engine fault. Start with the engine codes.",
                      "لمبة المحرك مع ESP: كمبيوتر المحرك كثيرًا ما يوقف نظام الثبات عند وجود عطل بالمحرك. ابدأ بأكواد "
                      "المحرك.")),
    ({"battery", "eps"}, ("Battery and steering together: low system voltage switches electric steering off. "
                          "Check the charging system first.",
                          "البطارية والدركسيون معًا: الجهد المنخفض يوقف التوجيه الكهربائي. افحص نظام الشحن أولاً.")),
    ({"mil", "glow"}, ("On many diesels the glow-plug light flashes instead of the MIL: read the engine codes.",
                       "في كثير من محركات الديزل تومض لمبة الشمعات بدل لمبة المحرك: اقرأ أكواد المحرك.")),
]


def pick(light_ids, colours: dict | None = None, present: list[str] | None = None, lang: str = "en",
         limit: int = 25) -> dict:
    """The "What light is on?" result for the selected lights.

    -> {"lights": [ids], "stop": bool (a red light / flashing MIL), "advice": [str], "combos": [str],
        "codes": [(code, score)], "scan": {"obd": bool, "modules": [str]}, "pids": [OBD PIDs to watch]}"""
    from .. import kb
    colours = colours or {}
    sel = [LIGHTS[i] for i in light_ids if i in LIGHTS]
    advice, modules, stop = [], [], False
    for l in sel:
        col = colours.get(l.id) or l.colours[0]
        if col not in l.do_now:
            col = l.colours[0]
        if col == "red" or (l.id == "mil" and col == "flashing"):
            stop = True
        advice.append(f"{text(l.name, lang)}: {text(l.do_now[col], lang)}")
        if not l.obd and l.module[0]:
            m = text(l.module, lang)
            if m not in modules:
                modules.append(m)
    ids_ = {l.id for l in sel}
    combos = [text(t, lang) for need, t in COMBOS if need <= ids_]
    codes = likely_codes([l.id for l in sel], limit, present)
    pids: list[int] = []
    for c, _s in codes[:8]:
        for p in (kb.lookup(c) or {}).get("pids", []):
            if p not in pids:
                pids.append(p)
    return {"lights": [l.id for l in sel], "stop": stop, "advice": advice, "combos": combos, "codes": codes,
            "scan": {"obd": any(l.obd for l in sel) or not sel, "modules": modules}, "pids": pids[:8]}
