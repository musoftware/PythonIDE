"""Components named by the generic DTC families, described in RAD IDE's own words (English + Arabic).

Each entry: n / n_ar (name used in sentences), part / part_ar (short name for causes and checks), kind ("s" sensor,
"a" actuator), what / what_ar (one plain sentence), system, monitor (OBD readiness monitor or "components"),
sev (green / amber / red), drive (yes / caution / no), tags (symptom concepts), pids (OBD-II mode 01 PIDs to watch),
causes (extra component-specific causes: CAUSES ids or (en, ar) tuples, ranked first), checks (extra checks),
safety / emissions flags.
"""
from __future__ import annotations

C: dict[str, dict] = {}


def comp(key, n, n_ar, kind, what, what_ar, system, monitor="components", sev="amber", drive="caution", tags=(),
         pids=(), causes=(), checks=(), part=None, part_ar=None, safety=False, emissions=False):
    C[key] = dict(n=n, n_ar=n_ar, part=part or n, part_ar=part_ar or n_ar, kind=kind, what=what, what_ar=what_ar,
                  system=system, monitor=monitor, sev=sev, drive=drive, tags=list(tags), pids=list(pids),
                  causes=list(causes), checks=list(checks), safety=safety, emissions=emissions)


# ============================================================== fuel and air metering
comp("fvr", "fuel volume regulator", "منظم كمية الوقود", "a",
     "On diesel and direct-injection engines it meters how much fuel the high-pressure pump lets in.",
     "في محركات الديزل والحقن المباشر ينظّم كمية الوقود التي تدخل طرمبة الضغط العالي.",
     "fuel-air", tags=["no-start", "low-power", "stalling"], pids=[0x23, 0x0C], causes=["fuel_quality"])
comp("fso", "fuel shutoff valve \"A\"", "صمام قطع الوقود \"A\"", "a",
     "It opens to let fuel reach the engine and closes to stop the engine.",
     "يفتح ليسمح بوصول الوقود إلى المحرك ويغلق لإيقافه.", "fuel-air", tags=["no-start", "stalling"], pids=[0x0C])
comp("vvt", "camshaft position actuator (variable valve timing)", "مشغّل وضع عمود الكامات (توقيت الصبابات المتغير)", "a",
     "An oil-pressure solenoid turns the camshaft a little to change valve timing for power and economy.",
     "سولينويد يعمل بضغط الزيت يلف عمود الكامات قليلاً لتغيير توقيت الصبابات من أجل القوة والاقتصاد.",
     "vvt", tags=["rough-idle", "low-power", "noise", "fuel-consumption"], pids=[0x0C, 0x05, 0x04],
     causes=["oil_level", "oil_dirty", "timing_chain"],
     checks=[("Check oil level and condition first - VVT problems are very often oil problems.",
              "افحص مستوى الزيت وحالته أولاً - مشاكل VVT غالبًا سببها الزيت.")],
     part="camshaft actuator solenoid", part_ar="سولينويد مشغّل الكامة")
comp("ho2s_heater", "oxygen sensor heater", "سخان حساس الأكسجين", "a",
     "It heats the oxygen sensor so it can start measuring soon after a cold start.",
     "يسخّن حساس الأكسجين حتى يبدأ القياس بسرعة بعد التشغيل على البارد.",
     "emissions", monitor="o2-heater", sev="green", drive="yes", tags=["fuel-consumption"], pids=[0x14, 0x15],
     part="oxygen sensor", part_ar="حساس الأكسجين", emissions=True)
comp("turbo_bypass", "turbo/supercharger bypass valve", "صمام تحويل التيربو/السوبرتشارجر", "a",
     "It vents boost pressure when the throttle closes so the turbo is not stressed.",
     "يفرّغ ضغط التيربو عند غلق دواسة البنزين حتى لا يُجهد التيربو.",
     "turbo", tags=["low-power", "noise"], pids=[0x0B, 0x70], causes=["boost_leak"])
comp("boost_ctrl", "turbo/supercharger boost control \"A\"", "التحكم في ضغط التيربو \"A\"", "a",
     "A valve (often a solenoid on the wastegate or variable vanes) that sets how much boost the turbo makes.",
     "صمام (غالبًا سولينويد على الويست جيت أو الريش المتغيرة) يحدد مقدار الضغط الذي ينتجه التيربو.",
     "turbo", tags=["low-power", "limp-mode"], pids=[0x0B, 0x70, 0x0C], causes=["wastegate", "boost_leak", "turbo_wear"],
     part="boost control valve", part_ar="صمام التحكم في الضغط")
comp("air_assist_inj", "air assisted injector control", "التحكم في الرشاش بمساعدة الهواء", "a",
     "Some engines blow a little air into the injectors to atomize the fuel better.",
     "بعض المحركات تنفخ قليلاً من الهواء في الرشاشات لتفتيت الوقود بشكل أفضل.", "fuel-air", sev="green", drive="yes",
     tags=["rough-idle"], pids=[0x0C])
comp("aat", "ambient air temperature sensor", "حساس حرارة الهواء الخارجي", "s",
     "It measures the outside air temperature (used by the climate control and engine strategies).",
     "يقيس حرارة الهواء الخارجي (يستخدمه التكييف وبرامج المحرك).", "body", sev="green", drive="yes", tags=["ac"],
     pids=[0x46])
comp("ivs", "intake valve control solenoid", "سولينويد التحكم في صبابات السحب", "a",
     "It controls oil flow to the intake camshaft phaser (variable valve timing).",
     "يتحكم في تدفق الزيت إلى مغيّر وضع كامة السحب (توقيت الصبابات المتغير).",
     "vvt", tags=["rough-idle", "low-power"], pids=[0x0C, 0x05], causes=["oil_level", "oil_dirty"])
comp("evs", "exhaust valve control solenoid", "سولينويد التحكم في صبابات العادم", "a",
     "It controls oil flow to the exhaust camshaft phaser (variable valve timing).",
     "يتحكم في تدفق الزيت إلى مغيّر وضع كامة العادم (توقيت الصبابات المتغير).",
     "vvt", tags=["rough-idle", "low-power"], pids=[0x0C, 0x05], causes=["oil_level", "oil_dirty"])
comp("fpr1", "fuel pressure regulator 1", "منظم ضغط الوقود 1", "a",
     "It keeps the fuel rail at the pressure the engine computer asks for.",
     "يحافظ على ضغط مجرى الوقود عند القيمة التي يطلبها كمبيوتر المحرك.",
     "fuel-air", tags=["no-start", "stalling", "low-power"], pids=[0x23, 0x0A], causes=["fuel_pressure_low"])
comp("iat", "intake air temperature sensor", "حساس حرارة الهواء الداخل", "s",
     "It tells the engine computer how warm the incoming air is, so it can adjust fuel and ignition.",
     "يخبر كمبيوتر المحرك بحرارة الهواء الداخل ليضبط الوقود والإشعال.",
     "fuel-air", sev="green", drive="yes", tags=["fuel-consumption", "hard-start"], pids=[0x0F, 0x05],
     checks=["compare_sensors"], part="intake air temperature (IAT) sensor", part_ar="حساس حرارة الهواء (IAT)")
comp("iat2", "intake air temperature sensor 2", "حساس حرارة الهواء الداخل 2", "s",
     "A second air temperature sensor, often after the intercooler on turbo engines.",
     "حساس ثانٍ لحرارة الهواء، غالبًا بعد الإنتركولر في محركات التيربو.", "fuel-air", sev="green", drive="yes",
     tags=["low-power"], pids=[0x0F])
comp("maf", "mass air flow (MAF) sensor", "حساس كمية الهواء (MAF)", "s",
     "It measures how much air enters the engine so the computer can add the right amount of fuel.",
     "يقيس كمية الهواء الداخلة إلى المحرك ليضيف الكمبيوتر كمية الوقود المناسبة.",
     "fuel-air", tags=["rough-idle", "stalling", "low-power", "fuel-consumption", "hesitation"], pids=[0x10, 0x0C, 0x04],
     causes=["maf_dirty", "air_filter", "vacuum_leak"],
     checks=[("At warm idle the MAF should read roughly 2-7 g/s on small engines; it must rise smoothly with RPM.",
              "في الوضع الخامل والمحرك ساخن يقرأ MAF تقريبًا 2-7 جم/ث في المحركات الصغيرة، ويجب أن يرتفع بسلاسة مع اللفات."),
             ("Clean it only with MAF cleaner spray; never touch the hot wire.",
              "نظّفه فقط ببخاخ منظف MAF ولا تلمس السلك الساخن.")],
     part="MAF sensor", part_ar="حساس MAF")
comp("map", "manifold absolute pressure / barometric pressure sensor", "حساس ضغط المنفولد / الضغط الجوي", "s",
     "It measures the pressure (vacuum or boost) in the intake manifold, which tells the computer the engine load.",
     "يقيس الضغط (التفريغ أو ضغط التيربو) داخل المنفولد، وهذا يخبر الكمبيوتر بحمل المحرك.",
     "fuel-air", tags=["rough-idle", "low-power", "fuel-consumption", "smoke"], pids=[0x0B, 0x33, 0x0C],
     causes=["vacuum_leak", ("Cracked or blocked vacuum hose to the sensor", "خرطوم الفاكيوم الواصل للحساس مشروخ أو مسدود")],
     checks=[("Key on, engine off: MAP should equal the barometric pressure (about 100 kPa at sea level).",
              "المفتاح على التشغيل والمحرك مطفأ: يجب أن يساوي MAP الضغط الجوي (حوالي 100 كيلو باسكال عند سطح البحر).")],
     part="MAP sensor", part_ar="حساس MAP")
comp("ect", "engine coolant temperature sensor", "حساس حرارة سائل التبريد", "s",
     "It tells the engine computer (and often the temperature gauge) how hot the engine is.",
     "يخبر كمبيوتر المحرك (وغالبًا مؤشر الحرارة) بمدى سخونة المحرك.",
     "cooling", tags=["overheating", "hard-start", "fuel-consumption", "fan"], pids=[0x05, 0x0F],
     causes=["coolant_low"],
     checks=["compare_sensors",
             ("A sensor reading -40 C usually means an open circuit; a reading near +140 C usually means a short.",
              "قراءة -40 درجة غالبًا تعني دائرة مفتوحة، وقراءة قرب +140 درجة غالبًا تعني قصرًا.")],
     part="coolant temperature (ECT) sensor", part_ar="حساس حرارة المحرك (ECT)")
comp("ect2", "engine coolant temperature sensor 2", "حساس حرارة سائل التبريد 2", "s",
     "A second coolant temperature sensor, often at the radiator outlet or cylinder head.",
     "حساس ثانٍ لحرارة سائل التبريد، غالبًا عند مخرج الرادياتير أو رأس المحرك.",
     "cooling", tags=["overheating", "fan"], pids=[0x05, 0x67], causes=["coolant_low"])
for _L in "ABCDEF":
    comp(f"tps_{_L}", f"throttle/pedal position sensor \"{_L}\"", f"حساس وضع الثروتل/الدواسة \"{_L}\"", "s",
         "It reports how far the throttle valve or accelerator pedal is opened; modern cars use two signals that must agree.",
         "يبلغ عن مقدار فتح صمام الثروتل أو دواسة البنزين؛ السيارات الحديثة تستخدم إشارتين يجب أن تتفقا.",
         "fuel-air", tags=["limp-mode", "low-power", "hesitation", "rough-idle", "stalling"], pids=[0x11, 0x45, 0x49, 0x4C],
         causes=["throttle_dirty", "pedal"],
         checks=[("Watch the throttle/pedal percentage while pressing the pedal slowly: it must rise smoothly with no dropouts.",
                  "راقب نسبة الثروتل/الدواسة أثناء الضغط ببطء على الدواسة: يجب أن ترتفع بسلاسة دون انقطاع."),
                 ("After cleaning or replacement run the throttle adaptation (Service Functions).",
                  "بعد التنظيف أو التغيير شغّل تعليم الثروتل (وظائف الصيانة).")],
         part="throttle/pedal position sensor", part_ar="حساس وضع الثروتل/الدواسة")
comp("o2", "oxygen (O2) sensor", "حساس الأكسجين (O2)", "s",
     "It measures the oxygen left in the exhaust. Sensor 1 (before the catalyst) controls the fuel mixture; "
     "sensor 2 (after the catalyst) checks the catalyst.",
     "يقيس الأكسجين المتبقي في العادم. الحساس 1 (قبل الدبّة) يتحكم في خليط الوقود، والحساس 2 (بعد الدبّة) يراقب الدبّة.",
     "emissions", monitor="o2", sev="green", drive="yes", tags=["fuel-consumption", "smell"], pids=[0x14, 0x15, 0x06, 0x07],
     part="oxygen sensor", part_ar="حساس الأكسجين", emissions=True)
comp("fcs", "fuel composition sensor", "حساس تركيب الوقود", "s",
     "On flex-fuel vehicles it measures the ethanol content of the fuel.",
     "في سيارات الوقود المرن يقيس نسبة الإيثانول في الوقود.", "fuel-air", tags=["hard-start", "rough-idle"], pids=[0x52])
for _L in "AB":
    comp(f"fts_{_L}", f"fuel temperature sensor \"{_L}\"", f"حساس حرارة الوقود \"{_L}\"", "s",
         "It measures the fuel temperature so the computer can correct the injected quantity.",
         "يقيس حرارة الوقود ليصحح الكمبيوتر كمية الحقن.", "fuel-air", sev="green", drive="yes", tags=["hard-start"],
         pids=[0x05])
comp("frp", "fuel rail pressure sensor", "حساس ضغط مجرى الوقود", "s",
     "It measures the pressure in the fuel rail (very high on diesel and direct-injection engines).",
     "يقيس الضغط في مجرى الوقود (عالٍ جدًا في محركات الديزل والحقن المباشر).",
     "fuel-air", tags=["no-start", "stalling", "low-power", "limp-mode"], pids=[0x23, 0x0A, 0x0C],
     part="fuel rail pressure sensor", part_ar="حساس ضغط مجرى الوقود")
comp("eot", "engine oil temperature sensor", "حساس حرارة زيت المحرك", "s",
     "It measures the engine oil temperature.", "يقيس حرارة زيت المحرك.", "oil", sev="green", drive="yes",
     tags=["overheating"], pids=[0x5C, 0x05])
comp("inj", "fuel injector", "رشاش الوقود", "a",
     "The injector sprays fuel into the engine; the computer opens it for a few milliseconds each cycle.",
     "الرشاش يرش الوقود داخل المحرك، والكمبيوتر يفتحه لبضعة أجزاء من الثانية في كل دورة.",
     "fuel-air", tags=["misfire", "rough-idle", "low-power", "fuel-consumption"], pids=[0x0C, 0x06, 0x07],
     checks=[("Swap the injector connector with a neighbour cylinder (or listen with a screwdriver) to see if it clicks.",
              "بدّل فيشة الرشاش مع أسطوانة مجاورة (أو استمع بمفك) لترى هل يطقطق.")],
     part="injector", part_ar="الرشاش")
comp("csinj", "cold start injector", "رشاش التشغيل على البارد", "a",
     "Older engines use an extra injector to enrich the mixture for cold starts.",
     "المحركات القديمة تستخدم رشاشًا إضافيًا لزيادة الوقود عند التشغيل على البارد.", "fuel-air",
     tags=["hard-start"], pids=[0x05])
comp("eng_shutoff", "engine shutoff solenoid", "سولينويد إيقاف المحرك", "a",
     "On many diesels it cuts the fuel to stop the engine.", "في كثير من محركات الديزل يقطع الوقود لإيقاف المحرك.",
     "fuel-air", tags=["no-start", "stalling"])
comp("inj_timing", "injector/injection timing control circuit", "دائرة التحكم في توقيت الحقن", "a",
     "It sets when the fuel is injected (mainly diesel injection pumps).", "يحدد توقيت حقن الوقود (أساسًا في طرمبات حقن الديزل).",
     "fuel-air", tags=["smoke", "low-power", "noise"], pids=[0x0C])
comp("fuel_pump", "fuel pump", "طرمبة البنزين", "a",
     "The electric pump in the tank that sends fuel to the engine.", "الطرمبة الكهربائية في التانك التي ترسل الوقود إلى المحرك.",
     "fuel-air", tags=["no-start", "stalling", "low-power"], pids=[0x0A, 0x23], causes=["fuse_relay"],
     checks=[("Listen for the pump running for 2-3 seconds when you switch the key on.",
              "استمع لصوت الطرمبة لمدة 2-3 ثوانٍ عند تشغيل المفتاح.")], part="fuel pump", part_ar="طرمبة البنزين")
comp("boost_sensor", "turbocharger boost sensor", "حساس ضغط التيربو", "s",
     "It measures the boost pressure made by the turbocharger.", "يقيس ضغط الهواء الذي ينتجه التيربو.",
     "turbo", tags=["low-power", "limp-mode"], pids=[0x0B, 0x6F, 0x70], causes=["boost_leak"])
comp("wastegate", "turbocharger wastegate solenoid", "سولينويد الويست جيت للتيربو", "a",
     "It controls the wastegate, the valve that lets exhaust bypass the turbine to limit boost.",
     "يتحكم في الويست جيت، وهو الصمام الذي يسمح للعادم بتجاوز التوربين لتحديد الضغط.",
     "turbo", tags=["low-power", "limp-mode"], pids=[0x0B, 0x70], causes=["wastegate"])
comp("inj_pump", "injection pump fuel metering control", "التحكم في معايرة وقود طرمبة الحقن", "a",
     "It controls how much fuel the diesel injection pump delivers.", "يتحكم في كمية الوقود التي تضخها طرمبة حقن الديزل.",
     "fuel-air", tags=["low-power", "smoke", "stalling"], pids=[0x23, 0x0C])

# ============================================================== ignition / misfire / timing
comp("ckp", "crankshaft position sensor", "حساس وضع عمود الكرنك", "s",
     "It tells the computer the engine speed and the exact position of the pistons. Without it most engines will not run.",
     "يخبر الكمبيوتر بسرعة المحرك وبالوضع الدقيق للمكابس. بدونه لا تعمل معظم المحركات.",
     "ignition", tags=["no-start", "stalling", "misfire"], pids=[0x0C],
     causes=["tone_ring", ("Excess metal dust on the sensor tip", "برادة حديد زائدة على رأس الحساس")],
     checks=[("Watch RPM while cranking: 0 rpm while the engine turns points at this sensor or its wiring.",
              "راقب اللفات أثناء الإدارة: صفر لفة بينما المحرك يدور يشير إلى هذا الحساس أو أسلاكه.")],
     part="crankshaft sensor", part_ar="حساس الكرنك")
comp("cmp", "camshaft position sensor", "حساس وضع عمود الكامات", "s",
     "It tells the computer which cylinder is on its power stroke, for sequential injection and variable valve timing.",
     "يخبر الكمبيوتر أي أسطوانة في شوط القدرة، للحقن المتتابع وتوقيت الصبابات المتغير.",
     "ignition", tags=["hard-start", "no-start", "stalling", "rough-idle"], pids=[0x0C],
     causes=["timing_chain"], part="camshaft sensor", part_ar="حساس الكامة")
comp("knock", "knock sensor", "حساس الطرق (Knock)", "s",
     "A small microphone on the block that hears knocking so the computer can retard the ignition and protect the engine.",
     "ميكروفون صغير على البلوك يسمع الطرق (الصفقة) ليؤخر الكمبيوتر الإشعال ويحمي المحرك.",
     "ignition", sev="amber", drive="caution", tags=["low-power", "fuel-consumption", "noise"], pids=[0x0E, 0x0C],
     causes=[("Sensor not tightened to the correct torque", "الحساس غير مربوط بالعزم الصحيح"), "fuel_quality"])
comp("coil", "ignition coil", "ملف الإشعال (الموبينة)", "a",
     "The coil turns 12 V into the high voltage that fires the spark plug.",
     "الموبينة تحوّل 12 فولت إلى الجهد العالي الذي يُشعل البوجيه.",
     "ignition", tags=["misfire", "rough-idle", "low-power"], pids=[0x0C],
     checks=[("Swap the coil with another cylinder: if the misfire/code follows the coil, the coil is faulty.",
              "بدّل الموبينة مع أسطوانة أخرى: إذا انتقل العطل مع الموبينة فهي التالفة.")], part="ignition coil", part_ar="الموبينة")
comp("timing_ref", "timing reference high resolution signal", "إشارة مرجع التوقيت عالية الدقة", "s",
     "A fine-resolution engine position signal used for precise timing.", "إشارة دقيقة لوضع المحرك تُستخدم للتوقيت الدقيق.",
     "ignition", tags=["stalling", "misfire"], pids=[0x0C])
comp("ign_rpm", "ignition/distributor engine speed input", "إشارة سرعة المحرك من الإشعال/الموزع", "s",
     "On older systems the engine speed signal comes from the ignition module or distributor.",
     "في الأنظمة القديمة تأتي إشارة سرعة المحرك من وحدة الإشعال أو الموزع (الديلكو).", "ignition",
     tags=["no-start", "stalling"], pids=[0x0C])
comp("glow", "glow plug/heater circuit", "دائرة بوجيهات التسخين", "a",
     "Diesel glow plugs heat the cylinders so the engine starts easily when cold.",
     "بوجيهات التسخين في الديزل تسخّن الأسطوانات ليسهل تشغيل المحرك على البارد.",
     "ignition", sev="green", drive="yes", tags=["hard-start", "smoke"], pids=[0x05], causes=["glow_plug", "glow_module"],
     part="glow plug", part_ar="بوجيه التسخين")

# ============================================================== emissions
comp("egr", "exhaust gas recirculation (EGR)", "إعادة تدوير غازات العادم (EGR)", "a",
     "The EGR valve lets a little exhaust back into the intake to lower combustion temperature and NOx.",
     "صمام EGR يُدخل قليلاً من العادم إلى السحب لخفض حرارة الاحتراق وأكاسيد النيتروجين.",
     "emissions", monitor="egr", tags=["rough-idle", "stalling", "knock", "low-power", "smoke"], pids=[0x2C, 0x2D, 0x0B],
     causes=["egr_carbon", "egr_valve", "egr_vacuum"], part="EGR valve", part_ar="صمام EGR", emissions=True)
comp("egr_sensor", "EGR sensor", "حساس EGR", "s",
     "It reports the EGR valve position (or EGR flow) back to the computer.", "يبلغ الكمبيوتر بوضع صمام EGR (أو تدفقه).",
     "emissions", monitor="egr", tags=["rough-idle"], pids=[0x2C, 0x2D], causes=["egr_carbon"], emissions=True)
comp("air", "secondary air injection", "حقن الهواء الثانوي", "a",
     "After a cold start a pump blows fresh air into the exhaust so the catalyst heats up faster.",
     "بعد التشغيل على البارد تنفخ طرمبة هواءً نقيًا في العادم لتسخن الدبّة أسرع.",
     "emissions", monitor="secondary-air", sev="green", drive="yes", tags=["noise"], pids=[0x12],
     causes=[("Water damage in the air pump or a stuck check valve", "تلف طرمبة الهواء بالمياه أو صمام عدم رجوع عالق")],
     part="secondary air pump/valve", part_ar="طرمبة/صمام الهواء الثانوي", emissions=True)
comp("cat", "catalytic converter", "المحوّل الحفزي (دبّة الشكمان)", "a",
     "It cleans the exhaust gases. The computer compares the oxygen sensors before and after it to judge how well it works.",
     "ينظّف غازات العادم. يقارن الكمبيوتر حساسي الأكسجين قبله وبعده ليحكم على كفاءته.",
     "emissions", monitor="catalyst", sev="green", drive="yes", tags=["smell", "low-power"], pids=[0x14, 0x15, 0x3C],
     part="catalytic converter", part_ar="الدبّة", emissions=True)
comp("cat_temp", "catalyst temperature sensor", "حساس حرارة الدبّة", "s",
     "It measures the catalytic converter temperature.", "يقيس حرارة المحوّل الحفزي.", "emissions", monitor="catalyst",
     sev="green", drive="yes", pids=[0x3C], emissions=True)
comp("cat_heater", "catalyst heater control circuit", "دائرة التحكم في سخان الدبّة", "a",
     "Some catalysts are electrically heated to start working sooner.", "بعض الدبّات تُسخَّن كهربائيًا لتبدأ العمل أسرع.",
     "emissions", monitor="heated-catalyst", sev="green", drive="yes", emissions=True)
comp("evap", "evaporative emission (EVAP) system", "نظام أبخرة الوقود (EVAP)", "a",
     "It stores fuel vapour from the tank in a charcoal canister and burns it in the engine instead of letting it escape.",
     "يخزن أبخرة الوقود من التانك في علبة فحم ويحرقها في المحرك بدلاً من خروجها للجو.",
     "evap", monitor="evap", sev="green", drive="yes", tags=["smell"], pids=[0x2E, 0x32, 0x2F],
     causes=["gas_cap", "evap_hose", "purge_valve", "vent_valve", "canister"], part="EVAP system", part_ar="نظام EVAP",
     emissions=True)
comp("purge", "EVAP purge control valve", "صمام التنقية (Purge) لنظام EVAP", "a",
     "The purge valve lets the stored fuel vapour be drawn into the engine.", "صمام التنقية يسمح بسحب الأبخرة المخزنة إلى المحرك.",
     "evap", monitor="evap", sev="green", drive="yes", tags=["rough-idle", "hard-start"], pids=[0x2E],
     part="purge valve", part_ar="صمام التنقية", emissions=True)
comp("vent", "EVAP vent control", "صمام التهوية لنظام EVAP", "a",
     "The vent valve lets fresh air into the canister and closes during the leak test.",
     "صمام التهوية يُدخل الهواء النقي إلى علبة الفحم ويُغلق أثناء اختبار التسريب.",
     "evap", monitor="evap", sev="green", drive="yes", tags=["fuel-filling"], pids=[0x32],
     part="vent valve", part_ar="صمام التهوية", emissions=True)
comp("evap_ps", "EVAP pressure sensor/switch", "حساس/مفتاح ضغط نظام EVAP", "s",
     "It measures the small pressure or vacuum in the fuel tank during the EVAP leak test.",
     "يقيس الضغط أو التفريغ البسيط في تانك الوقود أثناء اختبار تسريب EVAP.",
     "evap", monitor="evap", sev="green", drive="yes", pids=[0x32], emissions=True)
comp("evap_flow", "EVAP purge flow sensor", "حساس تدفق التنقية لنظام EVAP", "s",
     "It measures the vapour flow from the canister to the engine.", "يقيس تدفق الأبخرة من علبة الفحم إلى المحرك.",
     "evap", monitor="evap", sev="green", drive="yes", pids=[0x2E], emissions=True)
comp("ldp", "EVAP leak detection pump", "طرمبة كشف التسريب لنظام EVAP", "a",
     "A small pump pressurizes the fuel tank system to test it for leaks.", "طرمبة صغيرة تضغط نظام التانك لاختباره بحثًا عن تسريب.",
     "evap", monitor="evap", sev="green", drive="yes", emissions=True)
comp("evap_temp", "EVAP fuel vapour temperature sensor", "حساس حرارة أبخرة الوقود", "s",
     "It measures the temperature of the fuel vapour.", "يقيس حرارة أبخرة الوقود.", "evap", monitor="evap", sev="green",
     drive="yes", emissions=True)
comp("fuel_level", "fuel level sensor \"A\"", "حساس مستوى الوقود \"A\"", "s",
     "The float sender in the tank that drives the fuel gauge; the EVAP test also uses it.",
     "العوامة في التانك التي تحرك مؤشر الوقود؛ يستخدمه اختبار EVAP أيضًا.",
     "body", sev="green", drive="yes", tags=["gauge"], pids=[0x2F])
comp("exh_ps", "exhaust pressure sensor \"A\"", "حساس ضغط العادم \"A\"", "s",
     "It measures the back-pressure in the exhaust (often for the particulate filter or exhaust brake).",
     "يقيس الضغط الخلفي في العادم (غالبًا لفلتر الجزيئات أو فرملة العادم).", "exhaust-aftertreatment",
     tags=["low-power"], pids=[0x73])
comp("exh_pcv", "exhaust pressure control valve \"A\"", "صمام التحكم في ضغط العادم \"A\"", "a",
     "A valve that restricts the exhaust (warm-up or exhaust brake).", "صمام يضيّق العادم (للتسخين أو فرملة العادم).",
     "exhaust-aftertreatment", tags=["low-power"])
comp("egt", "exhaust gas temperature sensor", "حساس حرارة غازات العادم", "s",
     "It measures the exhaust temperature, mainly to protect the turbo, catalyst and particulate filter.",
     "يقيس حرارة العادم، أساسًا لحماية التيربو والدبّة وفلتر الجزيئات.", "exhaust-aftertreatment", monitor="egt",
     tags=["limp-mode"], pids=[0x78, 0x79])
comp("dpf_ps", "diesel particulate filter pressure sensor \"A\"", "حساس ضغط فلتر الجزيئات (DPF) \"A\"", "s",
     "It measures the pressure difference across the particulate filter to estimate how full of soot it is.",
     "يقيس فرق الضغط قبل وبعد فلتر الجزيئات لتقدير مدى امتلائه بالسناج.",
     "exhaust-aftertreatment", monitor="pm", tags=["limp-mode", "low-power"], pids=[0x7A, 0x7B],
     causes=["dpf_lines"], part="DPF pressure sensor", part_ar="حساس ضغط DPF")
comp("nox", "NOx sensor", "حساس أكاسيد النيتروجين (NOx)", "s",
     "It measures nitrogen oxides in the exhaust (for the NOx trap or SCR/AdBlue system).",
     "يقيس أكاسيد النيتروجين في العادم (لمصيدة NOx أو نظام SCR/AdBlue).", "exhaust-aftertreatment", monitor="nox",
     tags=["limp-mode"], pids=[0x83], causes=["nox_sensor"], emissions=True)

# ============================================================== speed / idle / electrical
comp("vss", "vehicle speed sensor", "حساس سرعة السيارة", "s",
     "It reports how fast the car is moving (speedometer, cruise control, gear shifting).",
     "يبلغ عن سرعة السيارة (العداد ومثبت السرعة وتبديل الغيارات).",
     "speed-idle", tags=["speedometer", "hard-shift", "cruise"], pids=[0x0D],
     causes=["wheel_sensor"], part="speed sensor", part_ar="حساس السرعة")
comp("iac", "idle air control", "التحكم في هواء الوضع الخامل (IAC)", "a",
     "It lets just enough air past the closed throttle to keep a steady idle.",
     "يسمح بمرور كمية هواء مناسبة حول الثروتل المغلق للحفاظ على دوران خامل ثابت.",
     "speed-idle", tags=["rough-idle", "stalling", "high-idle"], pids=[0x0C, 0x11],
     causes=["throttle_dirty", "vacuum_leak", "learn"], part="idle air control valve", part_ar="صمام هواء الخامل")
comp("batt_temp", "battery temperature sensor", "حساس حرارة البطارية", "s",
     "It lets the charging system adjust the charging voltage to the battery temperature.",
     "يسمح لنظام الشحن بضبط جهد الشحن حسب حرارة البطارية.", "charging", sev="green", drive="yes", tags=["battery"])
comp("oil_ps", "engine oil pressure sensor/switch", "حساس/مفتاح ضغط زيت المحرك", "s",
     "It warns when the engine oil pressure is too low - low oil pressure destroys an engine within minutes.",
     "ينبّه عندما يكون ضغط زيت المحرك منخفضًا جدًا - ضغط الزيت المنخفض يدمّر المحرك خلال دقائق.",
     "oil", sev="amber", drive="caution", tags=["oil-light", "noise"], pids=[0x0C, 0x5C],
     causes=["oil_level"],
     checks=[("Check the oil level with the dipstick first. If the red oil light is on, do not run the engine.",
              "افحص مستوى الزيت بالعصا أولاً. إذا كانت لمبة الزيت الحمراء مضاءة فلا تشغّل المحرك.")],
     part="oil pressure sensor", part_ar="حساس ضغط الزيت", safety=True)
comp("fan_spd", "fan speed sensor", "حساس سرعة المروحة", "s",
     "It reports the radiator fan speed.", "يبلغ عن سرعة مروحة الرادياتير.", "cooling", tags=["overheating", "fan"],
     pids=[0x05])
comp("ac_ps", "A/C refrigerant pressure sensor \"A\"", "حساس ضغط غاز التكييف \"A\"", "s",
     "It measures the air-conditioning refrigerant pressure and protects the compressor.",
     "يقيس ضغط غاز التكييف ويحمي الكمبروسر.", "ac", sev="green", drive="yes", tags=["ac", "fan"],
     causes=[("Refrigerant charge too low or too high", "كمية غاز التكييف أقل أو أكثر من اللازم")])
comp("ac_evap_t", "A/C evaporator temperature sensor", "حساس حرارة مبخّر التكييف", "s",
     "It stops the evaporator from freezing.", "يمنع تجمّد مبخّر التكييف (الثلاجة).", "ac", sev="green", drive="yes",
     tags=["ac"])
comp("iah", "intake air heater \"A\"", "سخان هواء السحب \"A\"", "a",
     "On some diesels a grid heater warms the intake air for cold starts.",
     "في بعض محركات الديزل يسخّن سخان شبكي هواء السحب للتشغيل على البارد.", "ignition", sev="green", drive="yes",
     tags=["hard-start", "smoke"])
comp("ps_ps", "power steering pressure sensor/switch", "حساس/مفتاح ضغط الدركسيون الهيدروليكي", "s",
     "It tells the engine computer when steering load rises so it can raise the idle.",
     "يخبر كمبيوتر المحرك بزيادة حمل الدركسيون ليرفع دوران الخامل.", "steering", sev="green", drive="yes",
     tags=["stalling", "steering"])
comp("bb_ps", "brake booster pressure sensor", "حساس ضغط مقوي الفرامل", "s",
     "It monitors the vacuum in the brake booster that makes the pedal light.",
     "يراقب التفريغ في مقوي الفرامل (الكرة) الذي يجعل الدواسة خفيفة.", "abs-brakes", tags=["brakes"],
     causes=[("Leaking booster hose or check valve", "خرطوم الكرة أو صمام عدم الرجوع مسرّب")], safety=True)
comp("voltage", "system voltage", "جهد النظام الكهربائي", "s",
     "The computer constantly watches the battery/charging voltage it receives.",
     "يراقب الكمبيوتر باستمرار جهد البطارية/الشحن الذي يصله.", "charging",
     tags=["battery", "no-start", "electrical"], pids=[0x42], causes=["battery", "alternator", "ground_strap", "belt"],
     checks=["battery_test"], part="battery/charging system", part_ar="البطارية/نظام الشحن")
comp("cruise", "cruise control input", "إشارة مثبت السرعة", "s",
     "A cruise control switch signal.", "إشارة من مفاتيح مثبت السرعة.", "cruise", sev="green", drive="yes", tags=["cruise"],
     causes=["clockspring"], part="cruise control switch", part_ar="مفتاح مثبت السرعة")
comp("brake_sw", "brake switch \"A\"", "مفتاح الفرامل \"A\"", "s",
     "The brake pedal switch turns on the brake lights and tells the computers that you are braking.",
     "مفتاح دواسة الفرامل يُشعل لمبات الفرامل ويخبر الكمبيوترات أنك تفرمل.", "abs-brakes", sev="amber",
     tags=["cruise", "brake-lights", "start-stop"], pids=[0x0D],
     checks=[("Ask someone to check that the brake lights work.", "اطلب من شخص التأكد من أن لمبات الفرامل تعمل.")],
     part="brake light switch", part_ar="مفتاح لمبة الفرامل", safety=True)
comp("ecm", "engine control module (ECM/PCM)", "كمبيوتر المحرك (ECM/PCM)", "s",
     "The engine computer tests its own memory, processor and power supply.",
     "كمبيوتر المحرك يختبر ذاكرته ومعالجه وتغذيته الكهربائية بنفسه.", "ecu",
     tags=["no-start", "stalling", "limp-mode"], causes=["low_voltage_event", "ground_strap", "software"],
     checks=["battery_test", "tsb"], part="engine computer", part_ar="كمبيوتر المحرك")
comp("starter_relay", "starter relay circuit", "دائرة ريلاي المارش", "a",
     "The relay that powers the starter motor when you turn the key or press Start.",
     "الريلاي الذي يغذّي موتور المارش عند لف المفتاح أو ضغط زر التشغيل.", "starting", tags=["no-start", "no-crank"],
     causes=["battery"], part="starter relay", part_ar="ريلاي المارش")
comp("gen", "generator (alternator) control circuit", "دائرة التحكم في الدينامو", "a",
     "The engine computer controls how hard the alternator charges.", "كمبيوتر المحرك يتحكم في مقدار شحن الدينامو.",
     "charging", tags=["battery", "battery-light"], pids=[0x42], causes=["alternator", "belt"],
     checks=["battery_test"], part="alternator", part_ar="الدينامو")
comp("fp_ctrl", "fuel pump \"A\" control circuit", "دائرة التحكم في طرمبة البنزين \"A\"", "a",
     "The computer switches (or speed-controls) the fuel pump.", "الكمبيوتر يشغّل طرمبة البنزين (أو يتحكم في سرعتها).",
     "fuel-air", tags=["no-start", "stalling"], pids=[0x0A], causes=["fuse_relay"], part="fuel pump", part_ar="طرمبة البنزين")
comp("ref", "sensor reference voltage", "جهد المرجع للحساسات", "s",
     "The computer supplies a stable 5 V to several sensors; if one sensor shorts it, all of them report wrong values.",
     "الكمبيوتر يغذي عدة حساسات بجهد ثابت 5 فولت؛ إذا قصّر حساس واحد تبلغ كلها قيمًا خاطئة.",
     "ecu", tags=["limp-mode", "no-start", "multiple-codes"],
     checks=[("Unplug the sensors on this reference one by one: the one that brings the 5 V back is the culprit.",
              "افصل الحساسات التي على هذا المرجع واحدًا تلو الآخر: الحساس الذي يُرجع 5 فولت عند فصله هو السبب.")],
     part="5 V reference circuit", part_ar="دائرة المرجع 5 فولت")
comp("ac_clutch", "A/C clutch relay control circuit", "دائرة التحكم في ريلاي كلاتش التكييف", "a",
     "It engages the air-conditioning compressor clutch.", "يعشّق كلاتش كمبروسر التكييف.", "ac", sev="green", drive="yes",
     tags=["ac"], part="A/C clutch relay", part_ar="ريلاي كلاتش التكييف")
comp("act_supply", "actuator supply voltage", "جهد تغذية المشغّلات", "a",
     "A power feed controlled by the module for several actuators.", "تغذية كهربائية تتحكم فيها وحدة التحكم لعدة مشغّلات.",
     "ecu", tags=["limp-mode", "multiple-codes"], causes=["fuse_relay"], part="actuator supply", part_ar="تغذية المشغّلات")
comp("imtv", "intake manifold tuning valve", "صمام ضبط المنفولد", "a",
     "It changes the intake path length for more torque at low or high RPM.",
     "يغيّر طول مسار الهواء في المنفولد لزيادة العزم في اللفات المنخفضة أو العالية.",
     "fuel-air", sev="green", drive="yes", tags=["low-power"], causes=["actuator_mech"])
comp("ecm_temp", "control module internal temperature sensor", "حساس الحرارة الداخلي لوحدة التحكم", "s",
     "It measures the temperature inside the control module.", "يقيس الحرارة داخل وحدة التحكم.", "ecu", sev="green",
     drive="yes")
comp("glow_cyl", "glow plug circuit", "دائرة بوجيه التسخين", "a",
     "The heater plug of one diesel cylinder.", "بوجيه التسخين لأسطوانة ديزل واحدة.", "ignition", sev="green",
     drive="yes", tags=["hard-start", "smoke"], causes=["glow_plug"], part="glow plug", part_ar="بوجيه التسخين")
comp("ecm_relay", "ECM/PCM power relay", "ريلاي تغذية كمبيوتر المحرك", "a",
     "The relay that keeps the engine computer powered (also for a while after switching off).",
     "الريلاي الذي يحافظ على تغذية كمبيوتر المحرك (وأيضًا لفترة بعد الإطفاء).", "ecu",
     tags=["no-start", "stalling", "battery-drain"], causes=["fuse_relay"], part="main relay", part_ar="الريلاي الرئيسي")
comp("fan", "cooling fan", "مروحة التبريد", "a",
     "The radiator fan pulls air through the radiator when the car is slow or stopped.",
     "مروحة الرادياتير تسحب الهواء خلال الرادياتير عندما تكون السيارة بطيئة أو واقفة.",
     "cooling", sev="amber", drive="caution", tags=["overheating", "fan", "ac"], pids=[0x05],
     causes=["fuse_relay", ("Seized or worn fan motor", "موتور المروحة متيبّس أو متآكل")],
     checks=["actuator_test",
             ("Switch the A/C on: on most cars the fan should start.", "شغّل التكييف: في معظم السيارات يجب أن تعمل المروحة.")],
     part="radiator fan", part_ar="مروحة الرادياتير", safety=True)
comp("lamp", "warning lamp control circuit", "دائرة التحكم في لمبة التحذير", "a",
     "The module switches a warning lamp in the instrument cluster.", "وحدة التحكم تشغّل لمبة تحذير في لوحة العدادات.",
     "body", sev="green", drive="yes", tags=["warning-light"])
comp("coolant_pump", "coolant pump \"A\" control circuit", "دائرة التحكم في طرمبة المياه \"A\"", "a",
     "An electric water pump circulates the coolant (common on modern and hybrid engines).",
     "طرمبة مياه كهربائية تُدير سائل التبريد (شائعة في المحركات الحديثة والهجينة).", "cooling", sev="red", drive="no",
     tags=["overheating"], pids=[0x05], causes=["fuse_relay"], part="electric water pump",
     part_ar="طرمبة المياه الكهربائية", safety=True)

# ============================================================== transmission
comp("tr_range", "transmission range sensor \"A\" (PRNDL input)", "حساس وضع ذراع الفتيس \"A\" (P R N D)", "s",
     "It tells the computers which position (P, R, N, D) the selector is in.",
     "يخبر الكمبيوترات بوضع ذراع الفتيس (P أو R أو N أو D).", "transmission",
     tags=["no-start", "hard-shift", "reverse-lights"], part="range sensor", part_ar="حساس وضع الفتيس")
comp("tft", "transmission fluid temperature sensor \"A\"", "حساس حرارة زيت الفتيس \"A\"", "s",
     "It measures the transmission fluid temperature.", "يقيس حرارة زيت الفتيس.", "transmission",
     tags=["hard-shift"], causes=["trans_fluid"])
comp("iss", "input/turbine speed sensor \"A\"", "حساس سرعة عمود الدخل/التوربين \"A\"", "s",
     "It measures the speed of the transmission input shaft.", "يقيس سرعة عمود الدخل في الفتيس.", "transmission",
     tags=["hard-shift", "limp-mode"], part="input speed sensor", part_ar="حساس سرعة الدخل")
comp("oss", "output speed sensor", "حساس سرعة عمود الخرج", "s",
     "It measures the speed of the transmission output shaft (often also used as the vehicle speed).",
     "يقيس سرعة عمود الخرج في الفتيس (غالبًا يُستخدم أيضًا كسرعة السيارة).", "transmission",
     tags=["hard-shift", "speedometer", "limp-mode"], pids=[0x0D], part="output speed sensor", part_ar="حساس سرعة الخرج")
comp("eng_spd_in", "engine speed input circuit", "دائرة إشارة سرعة المحرك", "s",
     "The transmission module receives the engine speed signal.", "وحدة الفتيس تستقبل إشارة سرعة المحرك.",
     "transmission", tags=["hard-shift"], pids=[0x0C])
comp("gear", "gear", "الغيار", "a",
     "The transmission computer checks that each gear has the right ratio between input and output speeds.",
     "كمبيوتر الفتيس يتأكد أن لكل غيار النسبة الصحيحة بين سرعة الدخل والخرج.", "transmission",
     tags=["hard-shift", "slipping", "limp-mode"], part="transmission", part_ar="الفتيس")
comp("tcc", "torque converter clutch solenoid", "سولينويد كلاتش محوّل العزم", "a",
     "It locks the torque converter at cruising speed to save fuel.", "يقفل محوّل العزم عند السرعة الثابتة لتوفير الوقود.",
     "transmission", tags=["shudder", "fuel-consumption", "stalling"], causes=["trans_fluid"],
     part="torque converter clutch solenoid", part_ar="سولينويد كلاتش المحوّل")
comp("pcs", "pressure control solenoid", "سولينويد التحكم في الضغط", "a",
     "It controls the hydraulic line pressure that applies the clutches inside an automatic gearbox.",
     "يتحكم في الضغط الهيدروليكي الذي يعشّق الديسكات داخل الفتيس الأوتوماتيك.", "transmission",
     tags=["hard-shift", "slipping", "limp-mode"], causes=["trans_fluid"], part="pressure control solenoid",
     part_ar="سولينويد الضغط")
comp("ss", "shift solenoid", "سولينويد التبديل", "a",
     "Shift solenoids route fluid inside the automatic gearbox to select the gears.",
     "سولينويدات التبديل توجّه الزيت داخل الفتيس الأوتوماتيك لاختيار الغيارات.", "transmission",
     tags=["hard-shift", "limp-mode"], causes=["trans_fluid"], part="shift solenoid", part_ar="سولينويد التبديل")
comp("shift_tim", "shift/timing solenoid", "سولينويد توقيت التبديل", "a",
     "It controls the timing of the shifts.", "يتحكم في توقيت التبديل.", "transmission", tags=["hard-shift"])
comp("int_shaft", "intermediate shaft speed sensor \"A\"", "حساس سرعة العمود الوسيط \"A\"", "s",
     "It measures the speed of an intermediate shaft in the gearbox.", "يقيس سرعة عمود وسيط في الفتيس.", "transmission",
     tags=["hard-shift"])
comp("clutch_pos", "clutch position sensor", "حساس وضع الكلاتش", "s",
     "It reports the clutch (pedal or actuator) position.", "يبلغ عن وضع الكلاتش (الدواسة أو المشغّل).", "transmission",
     tags=["hard-shift", "no-start"])
comp("clutch_sw", "clutch pedal switch", "مفتاح دواسة الكلاتش", "s",
     "It tells the computers that the clutch pedal is pressed (start permission, cruise control).",
     "يخبر الكمبيوترات أن دواسة الكلاتش مضغوطة (سماح التشغيل ومثبت السرعة).", "transmission", sev="green", drive="yes",
     tags=["no-crank", "cruise"])
comp("tfps", "transmission fluid pressure sensor/switch", "حساس/مفتاح ضغط زيت الفتيس", "s",
     "It reports hydraulic pressure inside the gearbox.", "يبلغ عن الضغط الهيدروليكي داخل الفتيس.", "transmission",
     tags=["hard-shift", "limp-mode"], causes=["trans_fluid"])
comp("pn_sw", "park/neutral switch input circuit", "دائرة مفتاح وضع P/N", "s",
     "It tells the engine computer that the gearbox is in Park or Neutral.", "يخبر كمبيوتر المحرك أن الفتيس على P أو N.",
     "transmission", tags=["no-crank", "rough-idle"])
comp("tcm_power", "TCM power input signal", "إشارة تغذية كمبيوتر الفتيس", "s",
     "The transmission computer checks its own supply voltage.", "كمبيوتر الفتيس يراقب جهد تغذيته.", "transmission",
     tags=["limp-mode"], causes=["battery", "fuse_relay"])
comp("tcm_relay", "TCM power relay", "ريلاي تغذية كمبيوتر الفتيس", "a",
     "The relay that feeds the transmission computer and solenoids.", "الريلاي الذي يغذي كمبيوتر الفتيس والسولينويدات.",
     "transmission", tags=["limp-mode"], causes=["fuse_relay"])
comp("clutch_act", "clutch actuator", "مشغّل الكلاتش", "a",
     "On automated manual and dual-clutch gearboxes an actuator works the clutch.",
     "في الفتيس اليدوي المؤتمت وثنائي الكلاتش يقوم مشغّل بتشغيل الكلاتش.", "transmission",
     tags=["hard-shift", "limp-mode", "no-start"])

# ============================================================== P2 extras
comp("nox_trap", "NOx trap", "مصيدة أكاسيد النيتروجين (NOx)", "a",
     "A catalyst that stores NOx on lean-burn and diesel engines and cleans it during short rich phases.",
     "دبّة تخزن أكاسيد النيتروجين في محركات الخليط الفقير والديزل وتنظفها في فترات غنية قصيرة.",
     "exhaust-aftertreatment", monitor="nox", sev="green", drive="yes", emissions=True)
comp("dpf", "diesel particulate filter (DPF)", "فلتر الجزيئات (DPF)", "a",
     "It traps diesel soot and burns it off from time to time (regeneration).",
     "يحتجز سناج الديزل ويحرقه من وقت لآخر (التجديد).", "exhaust-aftertreatment", monitor="pm",
     tags=["limp-mode", "low-power", "smoke"], pids=[0x7A, 0x7B, 0x7C],
     causes=["dpf_soot", "dpf_lines", "dpf_ash"],
     checks=[("Check the soot load and differential pressure in live data; a service regeneration (Service Functions) can "
              "help when the load is moderate.",
              "افحص نسبة السناج وفرق الضغط في البيانات الحية؛ التجديد الخدمي (وظائف الصيانة) يساعد عندما يكون "
              "الامتلاء متوسطًا.")], part="particulate filter", part_ar="فلتر الجزيئات", emissions=True)
comp("imrc", "intake manifold runner control", "التحكم في مجاري المنفولد", "a",
     "Flaps in the intake manifold that change the air path for better torque and cleaner combustion.",
     "بوابات (فلابات) داخل المنفولد تغيّر مسار الهواء لعزم أفضل واحتراق أنظف.", "fuel-air",
     sev="green", drive="yes", tags=["low-power", "rough-idle"], causes=["egr_carbon", "actuator_mech"],
     part="intake runner flaps", part_ar="فلابات المنفولد")
comp("imr_ps", "intake manifold runner position sensor/switch", "حساس/مفتاح وضع مجاري المنفولد", "s",
     "It reports the position of the intake manifold flaps.", "يبلغ عن وضع فلابات المنفولد.", "fuel-air", sev="green",
     drive="yes", causes=["egr_carbon"])
comp("vvt_ctrl", "camshaft position actuator control circuit", "دائرة التحكم في مشغّل وضع الكامة", "a",
     "The electrical side of the variable valve timing solenoid.", "الجزء الكهربائي من سولينويد توقيت الصبابات المتغير.",
     "vvt", tags=["rough-idle", "low-power"], pids=[0x0C], part="camshaft actuator solenoid",
     part_ar="سولينويد مشغّل الكامة")
comp("tac", "throttle actuator control", "التحكم في مشغّل الثروتل", "a",
     "On drive-by-wire cars an electric motor opens the throttle according to the pedal.",
     "في السيارات ذات الدواسة الإلكترونية يفتح موتور كهربائي الثروتل حسب الدواسة.",
     "fuel-air", sev="amber", drive="caution", tags=["limp-mode", "low-power", "stalling", "rough-idle"],
     pids=[0x11, 0x4C, 0x49], causes=["throttle_dirty", "learn"],
     checks=[("Clean the throttle body and run the throttle adaptation (Service Functions).",
              "نظّف بوابة الثروتل وشغّل تعليم الثروتل (وظائف الصيانة).")], part="electronic throttle body",
     part_ar="بوابة الثروتل الإلكترونية")
comp("egr_thr", "EGR throttle control", "التحكم في ثروتل EGR", "a",
     "A throttle flap (mainly diesel) that creates a little vacuum to pull EGR gas in.",
     "بوابة (أساسًا في الديزل) تصنع تفريغًا بسيطًا لسحب غازات EGR.", "emissions", monitor="egr",
     tags=["low-power"], causes=["egr_carbon"], emissions=True)
comp("inj_grp", "fuel injector group supply voltage", "جهد تغذية مجموعة الرشاشات", "a",
     "The module supplies a group of injectors (high voltage on many diesels and direct-injection engines).",
     "وحدة التحكم تغذي مجموعة من الرشاشات (بجهد عالٍ في كثير من محركات الديزل والحقن المباشر).",
     "fuel-air", tags=["misfire", "stalling", "no-start"], part="injector wiring", part_ar="أسلاك الرشاشات")
comp("baro", "barometric pressure sensor", "حساس الضغط الجوي", "s",
     "It measures the outside air pressure (altitude correction).", "يقيس ضغط الهواء الخارجي (تصحيح الارتفاع).",
     "fuel-air", sev="green", drive="yes", pids=[0x33])
comp("tbp", "turbocharger boost control position sensor \"A\"", "حساس وضع التحكم في ضغط التيربو \"A\"", "s",
     "It reports the position of the turbo wastegate or variable vanes.", "يبلغ عن وضع الويست جيت أو الريش المتغيرة في التيربو.",
     "turbo", tags=["low-power", "limp-mode"], causes=["turbo_wear"])
comp("rocker", "\"A\" rocker arm actuator", "مشغّل ذراع التاكيهات \"A\"", "a",
     "An oil-pressure switch-over system (e.g. variable valve lift) that changes the cam profile.",
     "نظام تحويل بضغط الزيت (مثل الرفع المتغير للصبابات) يغيّر شكل الكامة المستخدم.", "vvt",
     tags=["low-power", "rough-idle"], causes=["oil_level", "oil_dirty"])
comp("friction", "transmission friction element", "عنصر الاحتكاك في الفتيس", "a",
     "A clutch pack or band inside the automatic gearbox; the module measures how long it takes to apply.",
     "مجموعة ديسكات أو حزام داخل الفتيس الأوتوماتيك؛ تقيس وحدة التحكم الوقت الذي يستغرقه للتعشيق.", "transmission",
     tags=["hard-shift", "slipping"], causes=["trans_fluid", "trans_internal"])
comp("cyl_deact", "cylinder deactivation", "إيقاف الأسطوانات", "a",
     "To save fuel at light load some engines switch off cylinders by keeping their valves closed (oil-pressure lifters).",
     "لتوفير الوقود في الأحمال الخفيفة تُوقف بعض المحركات أسطوانات عن طريق إبقاء صماماتها مغلقة (تاكيهات بضغط الزيت).",
     "vvt", tags=["misfire", "noise", "fuel-consumption"], causes=["oil_level", "oil_dirty"],
     part="deactivation solenoid", part_ar="سولينويد الإيقاف")
comp("ign_sw", "ignition switch run position circuit", "دائرة وضع التشغيل في مفتاح الكونتاكت", "s",
     "The module checks the RUN signal from the ignition switch.", "وحدة التحكم تراقب إشارة وضع التشغيل من الكونتاكت.",
     "electrical", tags=["no-start", "stalling"])
comp("ecm_pwr", "ECM/PCM power input signal", "إشارة تغذية كمبيوتر المحرك", "s",
     "The engine computer checks its own supply voltage.", "كمبيوتر المحرك يراقب جهد تغذيته.", "ecu",
     tags=["stalling", "no-start"], pids=[0x42], causes=["battery", "fuse_relay", "ground_strap"])


# ============================================================== added: water in fuel, SCR / AdBlue (diesel)
comp("wif", "water-in-fuel sensor", "حساس المياه في الوقود", "s",
     "It sits in the diesel fuel filter and reports when the water separator is full of water.",
     "موجود في فلتر السولار ويبلغ عندما يمتلئ فاصل المياه بالمياه.", "fuel-air", sev="green", drive="yes",
     tags=["rough-idle", "low-power"], pids=[0x0C],
     checks=[("Drain the water from the fuel filter as the owner's manual describes, then clear the code.",
              "صفِّ المياه من فلتر السولار كما يشرح كتيب العربية ثم امسح الكود.")],
     part="water-in-fuel sensor", part_ar="حساس المياه في الوقود")
comp("scr", "SCR reductant (AdBlue / DEF) system", "نظام سائل التنقية SCR (AdBlue / DEF)", "a",
     "Diesel engines inject AdBlue into the exhaust so a catalyst can turn NOx into nitrogen and water.",
     "محركات الديزل تحقن AdBlue في العادم لتحوّل دبّة خاصة أكاسيد النيتروجين إلى نيتروجين ومياه.",
     "exhaust-aftertreatment", monitor="nox", tags=["limp-mode"], pids=[0x0C],
     checks=[("Check the AdBlue level and quality (old or diluted fluid, crystals at the injector).",
              "افحص مستوى وجودة AdBlue (سائل قديم أو مخفف، تبلور عند الرشاش).")],
     part="AdBlue system", part_ar="نظام AdBlue", emissions=True)
