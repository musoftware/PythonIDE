"""Symptom-based troubleshooting wizard (docs/CARDIAG.md "Fault knowledge base").

    from radide.cardiag.kb import symptoms
    symptoms.SYMPTOMS["overheating"]["questions"]          # questions with options
    r = symptoms.evaluate("overheating", {"when": "idle", "fan": "no"}, lang="ar")
    r["causes"]   # ranked likely causes with what to check
    r["pids"]     # OBD mode 01 PIDs to watch in Live Data (the scan tool selects them)
    r["codes"]    # fault codes that often come with this symptom

Each option adds weight to some causes (and can take weight away); the result ranks the causes. All texts are RAD IDE's
own (English + Arabic). The wizard narrows things down - it never replaces a measurement.
"""
from __future__ import annotations

# --------------------------------------------------------------------------------------------- causes
def _c(en, ar, explain_en, explain_ar, check_en, check_ar, pids=()):
    return {"name": (en, ar), "explain": (explain_en, explain_ar), "check": (check_en, check_ar), "pids": list(pids)}


CAUSES = {
    "coolant-low": _c("Low coolant / leak", "نقص سائل التبريد / تسريب",
                      "Without enough coolant the engine cannot get rid of its heat.",
                      "بدون سائل تبريد كافٍ لا يستطيع المحرك التخلص من حرارته.",
                      "With the engine cold, check the expansion tank level; look for wet spots, white crust or a sweet "
                      "smell at hoses, radiator, water pump and under the car.",
                      "والمحرك بارد افحص مستوى القربة؛ ابحث عن بقع مبللة أو ترسبات بيضاء أو رائحة حلوة عند الخراطيم "
                      "والردياتير وطلمبة المياه وتحت العربية.", (0x05,)),
    "fan": _c("Radiator fan not working", "مروحة الردياتير لا تعمل",
              "At low speed and idle there is no air through the radiator unless the fan runs.",
              "في السرعات البطيئة والوقوف لا يمر هواء في الردياتير إلا لو اشتغلت المروحة.",
              "Let the engine idle until about 100 °C (watch Coolant temperature): the fan must start. Check its fuse, "
              "relay and connector, or run the fan actuator test (Service functions).",
              "اترك المحرك دائرًا حتى حوالي 100 °م (راقب حرارة سائل التبريد): لازم المروحة تشتغل. افحص الفيوز "
              "والريلاي والفيشة، أو شغّل اختبار المروحة (وظائف الخدمة).", (0x05, 0x0C)),
    "thermostat-closed": _c("Thermostat stuck closed", "الثرموستات عالق مقفول",
                            "Coolant cannot reach the radiator, so the engine overheats quickly even with a full system.",
                            "السائل لا يصل للردياتير، فيسخن المحرك بسرعة حتى لو النظام مليان.",
                            "When the gauge is high but the upper radiator hose stays cool, the thermostat is not opening.",
                            "لو العداد عالي والخرطوم العلوي للردياتير بارد، فالثرموستات لا يفتح.", (0x05,)),
    "thermostat-open": _c("Thermostat stuck open", "الثرموستات عالق مفتوح",
                          "The engine never reaches its working temperature: weak heater, higher fuel use, P0128.",
                          "المحرك لا يصل لحرارة التشغيل: تدفئة ضعيفة واستهلاك وقود أعلى وكود P0128.",
                          "Watch Coolant temperature on a 15-minute drive: it should reach about 85-105 °C and stay there.",
                          "راقب حرارة سائل التبريد في مشوار 15 دقيقة: يجب أن تصل حوالي 85-105 °م وتثبت.", (0x05, 0x46)),
    "water-pump": _c("Water pump / belt", "طلمبة المياه / السير",
                     "A worn impeller or a slipping or broken belt stops the coolant from circulating.",
                     "ريشة متآكلة أو سير يزحلق أو مقطوع يوقف دوران السائل.",
                     "Check the belt; look for a leak or play at the pump shaft.",
                     "افحص السير؛ ابحث عن تسريب أو بوش في عمود الطلمبة.", (0x05,)),
    "radiator-clogged": _c("Radiator clogged", "الردياتير مسدود",
                           "Dirt outside or scale inside the radiator reduces cooling - worst at high speed or load.",
                           "الأتربة من الخارج أو الترسبات من الداخل تقلل التبريد - أسوأ في السرعات العالية والحمل.",
                           "Look at the fins (bent, dirty, leaves) and feel the radiator for cold spots after a drive.",
                           "انظر للزعانف (مثنية، متسخة، أوراق شجر) وتحسس الردياتير بعد مشوار بحثًا عن مناطق باردة.", (0x05,)),
    "head-gasket": _c("Head gasket", "جوان وش السلندر",
                      "Combustion gas pushed into the cooling system, or coolant burnt in the engine.",
                      "غازات الاحتراق تدخل نظام التبريد أو سائل التبريد يحترق داخل المحرك.",
                      "Signs: bubbles in the expansion tank, white sweet-smelling exhaust smoke, coolant loss without a "
                      "visible leak, milky oil. A workshop can do a block (CO2) test.",
                      "العلامات: فقاعات في القربة، دخان أبيض برائحة حلوة، نقص سائل التبريد بدون تسريب ظاهر، زيت لونه "
                      "لبني. الورشة تستطيع عمل اختبار CO2.", (0x05,)),
    "air-in-system": _c("Air trapped in the cooling system", "هواء محبوس في دورة التبريد",
                        "After coolant work an air pocket can stop circulation and give strange temperature jumps.",
                        "بعد العمل في دورة التبريد قد يمنع جيب هواء الدوران ويعطي قفزات غريبة في الحرارة.",
                        "Bleed the system: use the bleed screws or run the cooling-system bleed routine (Service "
                        "functions > cooling cycle) when the car supports it.",
                        "نفّس الدورة: استخدم مسامير التنفيس أو شغّل روتين تنفيس دورة التبريد (وظائف الخدمة > دورة "
                        "التبريد) لو العربية تدعمه.", (0x05,)),
    "ect-sensor": _c("Temperature sensor / gauge", "حساس الحرارة / العداد",
                     "A wrong reading makes the gauge or the fan behave wrongly although the engine is fine.",
                     "قراءة خاطئة تجعل العداد أو المروحة يتصرفان بشكل خاطئ رغم أن المحرك سليم.",
                     "Compare Coolant temperature in Live Data with the gauge and with an infrared thermometer.",
                     "قارن حرارة سائل التبريد في البيانات الحية مع العداد ومع ترمومتر بالأشعة.", (0x05,)),
    "vacuum-leak": _c("Air (vacuum) leak", "تهريب هواء (فاكيوم)",
                      "Unmetered air leans the mixture - worst at idle.",
                      "هواء غير محسوب يفقّر الخليط - أسوأ في الوضع الخامل.",
                      "Listen for hissing; watch the fuel trims: high positive short + long term at idle that improve "
                      "at 2500 rpm point to a leak.",
                      "استمع لصوت صفير؛ راقب تصحيح الوقود: قيم موجبة عالية في الخامل تتحسن عند 2500 لفة تشير لتهريب.",
                      (0x06, 0x07, 0x0B, 0x0C)),
    "spark-plugs": _c("Spark plugs / ignition coils", "البوجيهات / الموبينات",
                      "A weak or missing spark in one cylinder gives a misfire: shaking, power loss, flashing MIL.",
                      "شرارة ضعيفة أو غائبة في سلندر تعطي تقطيعًا ورجة وضعف عزم وقد تومض لمبة المحرك.",
                      "Read misfire codes (P0301-P0312 name the cylinder). Swap the coil with a neighbour cylinder and "
                      "see whether the misfire follows it; check the plugs' condition and age.",
                      "اقرأ أكواد التقطيع (P0301-P0312 تحدد السلندر). بدّل الموبينة مع سلندر مجاور وشوف هل التقطيع "
                      "ينتقل معها؛ افحص حالة وعمر البوجيهات.", (0x0C, 0x04)),
    "injector": _c("Fuel injector", "رشاش الوقود",
                   "A clogged, leaking or electrically faulty injector upsets one cylinder.",
                   "رشاش مسدود أو يسرّب أو به عطل كهربائي يخل بسلندر واحد.",
                   "Run the injector test (Service functions) if available; check the connector; listen to each injector "
                   "with a screwdriver.",
                   "شغّل اختبار الرشاشات (وظائف الخدمة) لو متاح؛ افحص الفيشة؛ استمع لكل رشاش بمفك.", (0x06, 0x07, 0x0C)),
    "throttle-dirty": _c("Dirty throttle body / idle control", "بوابة الهواء (الثروتل) متسخة",
                         "Carbon in the throttle body chokes the small idle air gap: unstable or low idle, stalling.",
                         "الكربون في بوابة الهواء يخنق فتحة هواء الخامل: خامل غير مستقر أو منخفض أو وقوف المحرك.",
                         "Clean the throttle body, then run the throttle / idle adaptation reset (Service functions).",
                         "نظّف بوابة الهواء ثم شغّل إعادة ضبط تعلم الثروتل / الخامل (وظائف الخدمة).", (0x11, 0x0C, 0x45)),
    "maf": _c("Air flow sensor (MAF)", "حساس كمية الهواء (MAF)",
              "A dirty MAF under-reads the air: lean running, hesitation, lack of power.",
              "حساس MAF المتسخ يقرأ هواء أقل: خليط فقير وتردد وضعف عزم.",
              "At idle a warm petrol engine usually shows about 2-7 g/s (depends on size); at full throttle it should rise "
              "smoothly. Clean with MAF cleaner only.",
              "في الخامل المحرك البنزين الساخن يعطي غالبًا حوالي 2-7 جم/ث (حسب السعة)؛ وعند الدواسة كاملة يرتفع بسلاسة. "
              "نظّفه بمنظف MAF فقط.", (0x10, 0x0C, 0x06, 0x07)),
    "fuel-pressure": _c("Low fuel pressure (pump / filter)", "ضغط وقود منخفض (طلمبة / فلتر)",
                        "Not enough fuel reaches the injectors - hard start, power loss under load, stalling.",
                        "الوقود الواصل للرشاشات غير كافٍ - صعوبة تشغيل، ضعف تحت الحمل، وقوف المحرك.",
                        "Listen for the pump humming 2 seconds after ignition on; measure fuel pressure with a gauge; "
                        "replace an old fuel filter.",
                        "استمع لصوت الطلمبة ثانيتين بعد فتح الكونتاكت؛ قس ضغط البنزين بساعة؛ غيّر الفلتر القديم.",
                        (0x0A, 0x23, 0x06, 0x07)),
    "battery-weak": _c("Weak or flat battery / bad terminals", "بطارية ضعيفة أو فارغة / أطراف سيئة",
                       "The starter needs a lot of current; a weak battery or corroded clamps cannot deliver it.",
                       "المارش يحتاج تيارًا كبيرًا؛ البطارية الضعيفة أو الأطراف المؤكسدة لا توفره.",
                       "Measure the battery: about 12.6 V resting, not below about 9.6 V while cranking. Clean and "
                       "tighten the terminals; check the ground strap.",
                       "قس البطارية: حوالي 12.6 فولت وهي واقفة، ولا تقل عن حوالي 9.6 فولت أثناء التدوير. نظّف وشد "
                       "الأطراف؛ افحص سلك الأرضي.", (0x42,)),
    "starter": _c("Starter motor / solenoid", "المارش / الأوتوماتيك",
                  "A single click with a good battery usually means the starter solenoid or motor is worn.",
                  "تكة واحدة مع بطارية سليمة غالبًا معناها أن أوتوماتيك المارش أو المارش نفسه تالف.",
                  "With a good battery, check the voltage at the starter signal wire while cranking.",
                  "مع بطارية سليمة، قس الجهد على سلك إشارة المارش أثناء التدوير.", ()),
    "immobiliser": _c("Key not recognised (immobiliser)", "المفتاح غير متعرَّف عليه (مانع السرقة)",
                      "The engine cranks and dies, or does not crank, with the key / security light on or flashing.",
                      "المحرك يدور ويقف أو لا يدور ولمبة المفتاح / الأمان منورة أو تومض.",
                      "Try the spare key and a new key battery. Key programming belongs to the dealer or an authorised "
                      "locksmith (not part of RAD IDE).",
                      "جرّب المفتاح الاحتياطي وبطارية مفتاح جديدة. برمجة المفاتيح عند الوكيل أو فني معتمد (ليست ضمن "
                      "RAD IDE).", ()),
    "crank-sensor": _c("Crankshaft position sensor", "حساس عمود الكرنك",
                       "Without the crank signal the computer does not fire injectors or plugs. Often fails when hot.",
                       "بدون إشارة الكرنك لا يشغّل الكمبيوتر الرشاشات ولا البوجيهات. كثيرًا ما يتعطل وهو ساخن.",
                       "While cranking, Engine RPM in Live Data should show about 150-300 rpm; 0 rpm points to this sensor.",
                       "أثناء التدوير يجب أن تظهر لفات المحرك في البيانات الحية حوالي 150-300 لفة؛ صفر يشير لهذا الحساس.",
                       (0x0C,)),
    "alternator": _c("Alternator / regulator", "الدينامو / المنظم",
                     "The alternator should keep the system at about 13.5-14.7 V with the engine running.",
                     "الدينامو يجب أن يحافظ على الجهد حوالي 13.5-14.7 فولت والمحرك دائر.",
                     "Watch Control module voltage at idle and at 2000 rpm with lights and A/C on.",
                     "راقب جهد وحدة التحكم في الخامل وعلى 2000 لفة والأنوار والتكييف شغالين.", (0x42, 0x0C)),
    "drain": _c("Something drains the battery when parked", "شيء يستهلك البطارية والعربية واقفة",
                "A module that does not go to sleep, a light, or an aftermarket device empties the battery overnight.",
                "وحدة لا تدخل وضع النوم أو لمبة أو جهاز مضاف يفرغ البطارية طول الليل.",
                "Measure the parked current (usually below about 50 mA after the car sleeps) and pull fuses one by one.",
                "قس تيار السحب والعربية واقفة (عادة أقل من حوالي 50 مللي أمبير بعد نوم العربية) واسحب الفيوزات واحدًا "
                "تلو الآخر.", ()),
    "o2-sensor": _c("Oxygen sensor", "حساس الأكسجين",
                    "A slow or wrong O2 sensor makes the fuel mixture wrong: more fuel used, emissions fail.",
                    "حساس أكسجين بطيء أو خاطئ يجعل الخليط غير مضبوط: استهلاك وقود أعلى وفشل في الانبعاثات.",
                    "Upstream sensor (B1S1) should switch quickly between about 0.1 and 0.9 V on a warm engine at 2500 rpm.",
                    "الحساس الأمامي (B1S1) يجب أن يتبدل بسرعة بين حوالي 0.1 و0.9 فولت والمحرك ساخن على 2500 لفة.",
                    (0x14, 0x15, 0x06, 0x07)),
    "tyres-brakes": _c("Tyres under-inflated / brake dragging", "ضغط الإطارات منخفض / فرامل ماسكة",
                       "Rolling resistance costs fuel; a sticking caliper also makes one wheel hot.",
                       "مقاومة الدوران تستهلك وقودًا؛ والفرامل الماسكة تجعل عجلة ساخنة.",
                       "Check tyre pressures cold; after a drive feel (carefully) whether one wheel rim is much hotter.",
                       "افحص ضغط الإطارات وهي باردة؛ بعد مشوار تحسس (بحذر) هل جنط عجلة أسخن بكثير.", ()),
    "turbo": _c("Turbo / boost leak", "التيربو / تهريب ضغط",
                "A split intercooler hose or a sticking turbo actuator means less boost: low power, sometimes whistling.",
                "خرطوم إنتركولر مشروخ أو مشغل تيربو عالق يعني ضغطًا أقل: ضعف عزم وأحيانًا صفير.",
                "Compare intake manifold pressure with the expected boost under load; check the hoses for oil and splits.",
                "قارن ضغط مجمع السحب بالضغط المتوقع تحت الحمل؛ افحص الخراطيم بحثًا عن زيت وشروخ.", (0x0B, 0x33, 0x0C)),
    "dpf-clogged": _c("Clogged particulate filter / catalyst", "فلتر الجزيئات أو الدبّة مسدود",
                      "A blocked exhaust chokes the engine - power drops, especially uphill.",
                      "العادم المسدود يخنق المحرك - يضعف العزم خاصة في الطلوع.",
                      "Read DPF / catalyst codes; diesel: check soot load and run a service regeneration only after "
                      "finding why it clogged.",
                      "اقرأ أكواد DPF / الدبّة؛ الديزل: افحص نسبة السناج وشغّل التجديد الخدمي فقط بعد معرفة سبب الانسداد.",
                      (0x0B, 0x3C)),
    "limp-mode": _c("Limp (safe) mode because of a fault", "وضع الطوارئ بسبب عطل",
                    "The computer limits power to protect the engine or gearbox after detecting a fault.",
                    "الكمبيوتر يحد القدرة لحماية المحرك أو الفتيس بعد اكتشاف عطل.",
                    "Read all codes - the fault that caused limp mode is stored.",
                    "اقرأ كل الأكواد - العطل الذي سبب وضع الطوارئ مسجّل.", (0x04, 0x11)),
    "oil-burning": _c("Engine burns oil", "المحرك يحرق زيت",
                      "Worn rings, valve seals or a leaking turbo seal - blue smoke, oil level drops.",
                      "شنابر أو جلب صبابات متآكلة أو تسريب في جوان التيربو - دخان أزرق ونقص في الزيت.",
                      "Check oil consumption between services; blue smoke at start-up points to valve seals.",
                      "تابع استهلاك الزيت بين الصيانات؛ الدخان الأزرق عند التشغيل يشير لجلب الصبابات.", ()),
    "rich-mixture": _c("Rich mixture (too much fuel)", "خليط غني (وقود زيادة)",
                       "Leaking injectors, high fuel pressure, a stuck thermostat or a wrong sensor reading - black smoke, "
                       "fuel smell.",
                       "رشاشات تسرب، ضغط وقود عالٍ، ثرموستات عالق، أو قراءة حساس خاطئة - دخان أسود ورائحة بنزين.",
                       "Fuel trims well below 0 % (negative) show the computer is taking fuel away.",
                       "تصحيح الوقود سالب بكثير يبين أن الكمبيوتر يسحب وقودًا.", (0x06, 0x07, 0x05, 0x10)),
    "trans-fluid": _c("Gearbox fluid low / old", "زيت الفتيس ناقص / قديم",
                      "Automatic gearboxes shift late, harsh or slip with low or worn fluid.",
                      "الفتيس الأوتوماتيك يغيّر متأخرًا أو بعنف أو يزحلق مع زيت ناقص أو قديم.",
                      "Check the level by the manufacturer's procedure (engine running, temperature); look for leaks.",
                      "افحص المستوى بطريقة الشركة (المحرك دائر، درجة الحرارة)؛ ابحث عن تسريب.", (0x0D, 0x0C)),
    "trans-solenoid": _c("Gearbox solenoid / control", "سولينويد / تحكم الفتيس",
                         "A faulty shift solenoid or valve body causes harsh or missing shifts and limp mode in one gear.",
                         "سولينويد تبديل أو بلف بودي تالف يسبب تبديلاً عنيفًا أو غيارات مفقودة ووضع طوارئ على غيار واحد.",
                         "Read the transmission control unit's codes (P07xx-P09xx).",
                         "اقرأ أكواد وحدة الفتيس (P07xx-P09xx).", (0x0D, 0x0C)),
    "adaptation": _c("Gearbox / throttle adaptation needed", "يحتاج إعادة تعلم (الفتيس / الثروتل)",
                     "After a battery disconnection or repair, learnt values can be lost or wrong.",
                     "بعد فصل البطارية أو إصلاح قد تضيع القيم المتعلَّمة أو تكون خاطئة.",
                     "Run the matching adaptation reset (Service functions) and do the learning drive.",
                     "شغّل إعادة ضبط التعلم المناسبة (وظائف الخدمة) واعمل مشوار التعلم.", ()),
    "heater-core": _c("Heater core / blend door", "رديتير التدفئة / بوابة الخلط",
                      "Hot engine but cold heater: blocked heater core, air in it, or a stuck blend door.",
                      "المحرك ساخن والتدفئة باردة: رديتير التدفئة مسدود أو به هواء، أو بوابة الخلط عالقة.",
                      "Feel both heater hoses at the bulkhead with the engine warm - both should be hot.",
                      "تحسس خرطومي التدفئة عند الحاجز والمحرك ساخن - الاثنان يجب أن يكونا ساخنين.", (0x05,)),
}

# --------------------------------------------------------------------------------------------- symptoms
def _q(qid, en, ar, options):
    return {"id": qid, "text": (en, ar), "options": options}


def _o(oid, en, ar, w=None, note=None, stop=False):
    return {"id": oid, "text": (en, ar), "w": dict(w or {}), "note": note, "stop": stop}


SYMPTOMS = {
    "overheating": {
        "name": ("The engine overheats", "المحرك يسخن (سخونية)"), "tag": "overheating",
        "intro": ("Safety first: never open the radiator or expansion-tank cap while hot.",
                  "السلامة أولاً: لا تفتح غطاء الردياتير أو القربة والمحرك ساخن."),
        "causes": {"coolant-low": 3, "fan": 2, "thermostat-closed": 2, "water-pump": 1, "radiator-clogged": 1,
                   "head-gasket": 1, "air-in-system": 1, "ect-sensor": 1},
        "questions": [
            _q("when", "When does it get hot?", "امتى بتسخن؟", [
                _o("idle", "In traffic / at idle", "في الزحمة / وهي واقفة", {"fan": 4, "coolant-low": 1}),
                _o("speed", "At high speed or uphill", "على السرعة العالية أو الطلوع",
                   {"radiator-clogged": 3, "water-pump": 2, "thermostat-closed": 1, "head-gasket": 1}),
                _o("fast", "Within a few minutes of starting", "بعد دقائق من التشغيل",
                   {"thermostat-closed": 4, "coolant-low": 2, "air-in-system": 2}),
                _o("always", "All the time", "طول الوقت", {"coolant-low": 2, "water-pump": 2, "head-gasket": 1})]),
            _q("level", "Coolant level in the expansion tank (engine cold)?", "مستوى المياه في القربة (والمحرك بارد)؟", [
                _o("low", "Low / keeps dropping", "ناقص / بيقل باستمرار", {"coolant-low": 4, "head-gasket": 2}),
                _o("ok", "Correct", "مظبوط", {"coolant-low": -3, "fan": 1, "thermostat-closed": 1}),
                _o("unknown", "Not checked yet", "لسه ما اتفحصش")]),
            _q("fan", "Does the radiator fan run when the gauge is high?", "المروحة بتشتغل لما العداد يعلى؟", [
                _o("no", "No", "لا", {"fan": 5}),
                _o("yes", "Yes", "أيوه", {"fan": -3, "thermostat-closed": 1, "radiator-clogged": 1}),
                _o("unknown", "Not sure", "مش متأكد")]),
            _q("signs", "Any of these?", "فيه حاجة من دول؟", [
                _o("bubbles", "Bubbles in the tank / white sweet smoke", "فقاعات في القربة / دخان أبيض ريحته حلوة",
                   {"head-gasket": 5}),
                _o("repair", "Coolant work was done recently", "اتعمل شغل في دورة المياه قريب", {"air-in-system": 5}),
                _o("gauge", "Gauge jumps but the engine feels normal", "العداد بيقفز والمحرك طبيعي", {"ect-sensor": 4}),
                _o("none", "None of these", "ولا حاجة")]),
        ],
        "watch": [(0x05, ("Coolant temperature: normally about 85-105 °C when warm; the fan usually starts near 95-105 °C.",
                          "حرارة سائل التبريد: طبيعي حوالي 85-105 °م والمحرك ساخن؛ المروحة غالبًا تشتغل قرب 95-105 °م.")),
                  (0x0C, ("Engine speed - watch the temperature at idle and at 2000 rpm.",
                          "لفات المحرك - راقب الحرارة في الخامل وعلى 2000 لفة.")),
                  (0x46, ("Ambient temperature - for comparison.", "الحرارة الخارجية - للمقارنة.")),
                  (0x0D, ("Vehicle speed.", "سرعة العربية."))],
        "stop": True,
    },
    "rough-idle": {
        "name": ("Shakes at idle / rough idle", "بترج وهي واقفة (رجة في الخامل)"), "tag": "rough-idle",
        "intro": ("A rough idle is usually one cylinder not working well, an air leak or a dirty throttle body.",
                  "الرجة في الخامل غالبًا سلندر لا يعمل جيدًا أو تهريب هواء أو بوابة هواء متسخة."),
        "causes": {"spark-plugs": 3, "vacuum-leak": 2, "throttle-dirty": 2, "injector": 1, "maf": 1},
        "questions": [
            _q("mil", "Is the check-engine light on or flashing?", "لمبة المحرك منورة أو بتومض؟", [
                _o("flashing", "Flashing", "بتومض", {"spark-plugs": 4, "injector": 2},
                   note=("Flashing MIL = heavy misfire: drive as little as possible.",
                         "اللمبة اللي بتومض = تقطيع شديد: قلل القيادة لأقل حد.")),
                _o("on", "On (steady)", "منورة ثابتة", {"vacuum-leak": 1, "maf": 1, "spark-plugs": 1}),
                _o("off", "Off", "مطفية", {"throttle-dirty": 2, "spark-plugs": 1})]),
            _q("cold", "Worse when cold or warm?", "أسوأ على البارد ولا على السخن؟", [
                _o("cold", "Cold", "على البارد", {"vacuum-leak": 2, "injector": 1}),
                _o("warm", "Warm", "على السخن", {"spark-plugs": 1, "throttle-dirty": 1}),
                _o("same", "Same", "زي بعض")]),
            _q("ac", "Does it get worse with the A/C on?", "بتزيد مع تشغيل التكييف؟", [
                _o("yes", "Yes", "أيوه", {"throttle-dirty": 3}),
                _o("no", "No", "لا"),
            ]),
            _q("hiss", "Any hissing sound in the engine bay?", "فيه صوت صفير في الموتور؟", [
                _o("yes", "Yes", "أيوه", {"vacuum-leak": 5}),
                _o("no", "No", "لا", {"vacuum-leak": -1})]),
        ],
        "watch": [(0x0C, ("Engine speed - idle should be steady (about ±50 rpm).", "لفات المحرك - الخامل يجب أن يكون ثابتًا (حوالي ±50 لفة).")),
                  (0x06, ("Short-term fuel trim bank 1: around 0 % ±10 % is normal.", "تصحيح الوقود قصير المدى صف 1: حوالي 0 % ±10 % طبيعي.")),
                  (0x07, ("Long-term fuel trim bank 1: beyond about +10 % at idle suggests an air leak.",
                          "تصحيح الوقود طويل المدى صف 1: أكثر من حوالي +10 % في الخامل يشير لتهريب هواء.")),
                  (0x0B, ("Intake manifold pressure: a warm engine at idle is usually about 25-45 kPa.",
                          "ضغط مجمع السحب: المحرك الساخن في الخامل عادة حوالي 25-45 كيلوباسكال.")),
                  (0x04, ("Calculated load.", "الحمل المحسوب.")), (0x11, ("Throttle position.", "وضع الثروتل."))],
    },
    "no-start": {
        "name": ("Cranks but won't start", "بتدور (المارش بيلف) ومش بتشتغل"), "tag": "no-start",
        "intro": ("The engine needs fuel, spark, compression and the crank signal. Check the simple things first.",
                  "المحرك يحتاج وقود وشرارة وكبس وإشارة الكرنك. افحص الأشياء البسيطة أولاً."),
        "causes": {"fuel-pressure": 3, "crank-sensor": 2, "immobiliser": 2, "spark-plugs": 1, "battery-weak": 1},
        "questions": [
            _q("fuel", "Is there fuel in the tank (gauge not on empty)?", "فيه بنزين في التانك؟", [
                _o("yes", "Yes", "أيوه"),
                _o("low", "Near empty", "قرب الخلصان", {"fuel-pressure": 4})]),
            _q("pump", "Do you hear the fuel pump hum for 2 s after ignition on?", "بتسمع صوت الطلمبة ثانيتين بعد فتح الكونتاكت؟", [
                _o("no", "No", "لا", {"fuel-pressure": 4}),
                _o("yes", "Yes", "أيوه", {"fuel-pressure": -1}),
                _o("unknown", "Not sure", "مش متأكد")]),
            _q("key", "Is the key / security light flashing or on?", "لمبة المفتاح / الأمان بتومض أو منورة؟", [
                _o("yes", "Yes", "أيوه", {"immobiliser": 5}),
                _o("no", "No", "لا", {"immobiliser": -2})]),
            _q("hot", "Does it happen mostly when the engine is hot?", "بتحصل أكتر والمحرك سخن؟", [
                _o("yes", "Yes", "أيوه", {"crank-sensor": 4}),
                _o("no", "No", "لا")]),
            _q("crank", "Is the cranking speed normal?", "سرعة دوران المارش طبيعية؟", [
                _o("slow", "Slow", "بطيئة", {"battery-weak": 4}),
                _o("normal", "Normal", "طبيعية")]),
        ],
        "watch": [(0x0C, ("Engine speed while cranking: about 150-300 rpm; 0 rpm = no crank signal.",
                          "لفات المحرك أثناء التدوير: حوالي 150-300 لفة؛ صفر = لا توجد إشارة كرنك.")),
                  (0x42, ("Module voltage while cranking: should stay above about 9.6 V.", "جهد الوحدة أثناء التدوير: يجب أن يبقى أعلى من حوالي 9.6 فولت.")),
                  (0x05, ("Coolant temperature - a wrong value (e.g. -40 °C) upsets the start mixture.",
                          "حرارة سائل التبريد - قيمة خاطئة (مثل -40 °م) تفسد خليط التشغيل.")),
                  (0x0A, ("Fuel pressure (if the car reports it).", "ضغط الوقود (لو العربية تقرؤه)."))],
    },
    "no-crank": {
        "name": ("Starter does not turn / only clicks", "المارش مش بيلف / بيطقطق بس"), "tag": "no-crank",
        "intro": ("Most no-crank cases are the battery or its terminals.", "أغلب حالات عدم دوران المارش سببها البطارية أو أطرافها."),
        "causes": {"battery-weak": 4, "starter": 2, "immobiliser": 1},
        "questions": [
            _q("lights", "Do the dashboard lights dim or go out when you try?", "أنوار التابلوه بتضعف أو تطفي وانت بتدوّر؟", [
                _o("yes", "Yes", "أيوه", {"battery-weak": 4}),
                _o("no", "No, they stay bright", "لا، بتفضل قوية", {"starter": 3, "battery-weak": -1})]),
            _q("click", "What do you hear?", "بتسمع إيه؟", [
                _o("rapid", "Rapid clicking", "طقطقة سريعة", {"battery-weak": 4}),
                _o("single", "One click", "تكة واحدة", {"starter": 4}),
                _o("nothing", "Nothing", "ولا حاجة", {"immobiliser": 2, "starter": 1})]),
            _q("gear", "Automatic: does it crank in N instead of P? Manual: clutch fully pressed?",
               "أوتوماتيك: بتدور على N بدل P؟ عادي: الدبرياج مدعوس للآخر؟", [
                   _o("yes", "Yes, then it cranks", "أيوه، ساعتها بتدور",
                      note=("The gear-position / clutch switch is the likely cause.", "مفتاح وضع الفتيس / الدبرياج هو السبب المرجح.")),
                   _o("no", "No difference", "مفيش فرق")]),
        ],
        "watch": [(0x42, ("Module voltage with ignition on: about 12.2-12.7 V for a healthy battery.",
                          "جهد الوحدة والكونتاكت مفتوح: حوالي 12.2-12.7 فولت للبطارية السليمة."))],
    },
    "low-power": {
        "name": ("Lack of power / hesitation", "العربية ضعيفة / بتتردد في السحب"), "tag": "low-power",
        "intro": ("Power needs air, fuel and spark - and a free exhaust.", "القدرة تحتاج هواء ووقود وشرارة - وعادم مفتوح."),
        "causes": {"maf": 2, "fuel-pressure": 2, "spark-plugs": 2, "turbo": 1, "dpf-clogged": 1, "limp-mode": 2,
                   "vacuum-leak": 1},
        "questions": [
            _q("mil", "Is a warning light on?", "فيه لمبة منورة؟", [
                _o("yes", "Yes", "أيوه", {"limp-mode": 3}),
                _o("no", "No", "لا", {"limp-mode": -1, "fuel-pressure": 1})]),
            _q("turbo", "Does the engine have a turbo?", "المحرك تيربو؟", [
                _o("yes", "Yes", "أيوه", {"turbo": 3, "dpf-clogged": 1}),
                _o("no", "No", "لا", {"turbo": -3})]),
            _q("rev", "Does it stop at a certain rpm (e.g. 3000) as if limited?", "بتقف عند لفة معينة (مثلاً 3000) كأنها محددة؟", [
                _o("yes", "Yes", "أيوه", {"limp-mode": 4}),
                _o("no", "No", "لا")]),
            _q("load", "Worse uphill / fully loaded?", "أسوأ في الطلوع / وهي محملة؟", [
                _o("yes", "Yes", "أيوه", {"fuel-pressure": 2, "dpf-clogged": 2}),
                _o("no", "No", "لا")]),
        ],
        "watch": [(0x04, ("Calculated load.", "الحمل المحسوب.")), (0x10, ("Air flow (MAF) - should rise strongly at full throttle.",
                                                                           "كمية الهواء (MAF) - يجب أن ترتفع بقوة عند الدواسة كاملة.")),
                  (0x0B, ("Intake manifold pressure / boost.", "ضغط مجمع السحب / التيربو.")),
                  (0x11, ("Throttle position - should reach near full at full pedal.", "وضع الثروتل - يجب أن يقترب من الكامل مع الدواسة كاملة.")),
                  (0x06, ("Short-term fuel trim.", "تصحيح الوقود قصير المدى.")), (0x0C, ("Engine speed.", "لفات المحرك."))],
    },
    "stalling": {
        "name": ("The engine stalls", "العربية بتطفي لوحدها"), "tag": "stalling",
        "intro": ("Note when it stalls - at idle, when stopping, or while driving.", "لاحظ امتى بتطفي - في الخامل، عند الوقوف، أو أثناء السير."),
        "causes": {"throttle-dirty": 3, "vacuum-leak": 2, "fuel-pressure": 2, "crank-sensor": 1, "maf": 1},
        "questions": [
            _q("when", "When does it stall?", "بتطفي امتى؟", [
                _o("stop", "When slowing down / stopping", "وأنا بهدي / بقف", {"throttle-dirty": 4}),
                _o("drive", "While driving", "وأنا ماشي", {"fuel-pressure": 3, "crank-sensor": 3}),
                _o("cold", "Right after a cold start", "بعد التشغيل على البارد مباشرة", {"vacuum-leak": 2, "throttle-dirty": 2})]),
            _q("battery", "Was the battery disconnected or the throttle cleaned recently?", "البطارية اتفصلت أو الثروتل اتنضف قريب؟", [
                _o("yes", "Yes", "أيوه", {"adaptation": 5}),
                _o("no", "No", "لا")]),
        ],
        "watch": [(0x0C, ("Engine speed - watch the dip just before it stalls.", "لفات المحرك - راقب الهبوط قبل ما تطفي.")),
                  (0x11, ("Throttle position.", "وضع الثروتل.")), (0x07, ("Long-term fuel trim.", "تصحيح الوقود طويل المدى.")),
                  (0x42, ("Module voltage.", "جهد الوحدة."))],
    },
    "fuel-consumption": {
        "name": ("Uses more fuel than before", "بتصرف بنزين أكتر من الأول"), "tag": "fuel-consumption",
        "intro": ("Compare with a full-tank measurement; short trips and traffic raise consumption a lot.",
                  "قارن بقياس تانك كامل؛ المشاوير القصيرة والزحمة تزوّد الاستهلاك كثيرًا."),
        "causes": {"thermostat-open": 2, "o2-sensor": 2, "tyres-brakes": 2, "rich-mixture": 2, "maf": 1, "spark-plugs": 1},
        "questions": [
            _q("heater", "Is the heater weak / temperature gauge low?", "التدفئة ضعيفة / عداد الحرارة واطي؟", [
                _o("yes", "Yes", "أيوه", {"thermostat-open": 5}),
                _o("no", "No", "لا", {"thermostat-open": -1})]),
            _q("smell", "Fuel smell or black smoke?", "ريحة بنزين أو دخان أسود؟", [
                _o("yes", "Yes", "أيوه", {"rich-mixture": 4}),
                _o("no", "No", "لا")]),
            _q("pull", "Does the car pull to one side or a wheel get hot?", "العربية بتسحب لجنب أو فيه عجلة بتسخن؟", [
                _o("yes", "Yes", "أيوه", {"tyres-brakes": 5}),
                _o("no", "No", "لا")]),
        ],
        "watch": [(0x05, ("Coolant temperature - must reach about 85-105 °C.", "حرارة سائل التبريد - لازم توصل حوالي 85-105 °م.")),
                  (0x06, ("Short-term fuel trim.", "تصحيح الوقود قصير المدى.")), (0x07, ("Long-term fuel trim.", "تصحيح الوقود طويل المدى.")),
                  (0x14, ("O2 sensor bank 1 sensor 1 voltage - should switch quickly.", "جهد حساس الأكسجين صف 1 حساس 1 - يجب أن يتبدل بسرعة.")),
                  (0x10, ("Air flow (MAF).", "كمية الهواء (MAF)."))],
    },
    "smoke": {
        "name": ("Smoke from the exhaust", "دخان من الشكمان"), "tag": "smoke",
        "intro": ("Thin white vapour on a cold morning is normal water condensation.", "البخار الأبيض الخفيف في الصباح البارد طبيعي (تكثف مياه)."),
        "causes": {"oil-burning": 2, "head-gasket": 2, "rich-mixture": 2, "dpf-clogged": 1, "turbo": 1},
        "questions": [
            _q("colour", "What colour is the smoke?", "لون الدخان إيه؟", [
                _o("blue", "Blue-grey", "أزرق رمادي", {"oil-burning": 5, "turbo": 2}),
                _o("white", "Thick white, sweet smell", "أبيض كثيف ريحته حلوة", {"head-gasket": 5},
                   note=("Check the coolant level - burning coolant can overheat the engine.",
                         "افحص مستوى المياه - احتراق سائل التبريد قد يسخّن المحرك.")),
                _o("black", "Black", "أسود", {"rich-mixture": 4, "dpf-clogged": 1, "turbo": 1})]),
            _q("when", "When?", "امتى؟", [
                _o("start", "Only at start-up", "عند التشغيل بس", {"oil-burning": 2}),
                _o("accel", "When accelerating", "مع الدوس", {"rich-mixture": 1, "turbo": 2}),
                _o("always", "All the time", "طول الوقت", {"head-gasket": 1})]),
        ],
        "watch": [(0x05, ("Coolant temperature.", "حرارة سائل التبريد.")), (0x06, ("Short-term fuel trim.", "تصحيح الوقود قصير المدى.")),
                  (0x07, ("Long-term fuel trim.", "تصحيح الوقود طويل المدى.")), (0x0B, ("Intake / boost pressure.", "ضغط السحب / التيربو."))],
    },
    "battery-light": {
        "name": ("Battery light on / battery keeps going flat", "لمبة البطارية منورة / البطارية بتفضى"), "tag": "battery-light",
        "intro": ("Separate charging problems (light on while driving) from drain problems (flat after standing).",
                  "افصل بين مشاكل الشحن (اللمبة منورة وأنت ماشي) ومشاكل السحب (تفضى بعد الوقوف)."),
        "causes": {"alternator": 3, "battery-weak": 2, "drain": 2, "water-pump": 1},
        "questions": [
            _q("light", "Is the battery light on while driving?", "لمبة البطارية منورة وأنت ماشي؟", [
                _o("yes", "Yes", "أيوه", {"alternator": 4, "drain": -2}),
                _o("no", "No - it is just flat after standing", "لا - بتفضى بعد الوقوف بس", {"drain": 4, "battery-weak": 2, "alternator": -2})]),
            _q("age", "Is the battery older than about 4 years?", "البطارية عمرها أكتر من حوالي 4 سنين؟", [
                _o("yes", "Yes", "أيوه", {"battery-weak": 3}),
                _o("no", "No", "لا")]),
            _q("temp", "Is the temperature gauge rising too?", "عداد الحرارة بيعلى كمان؟", [
                _o("yes", "Yes", "أيوه", {"water-pump": 5},
                   note=("Probably a broken belt - stop the engine.", "غالبًا السير مقطوع - أطفئ المحرك."), stop=True),
                _o("no", "No", "لا")]),
        ],
        "watch": [(0x42, ("Module voltage: about 13.5-14.7 V with the engine running; below about 13 V = not charging.",
                          "جهد الوحدة: حوالي 13.5-14.7 فولت والمحرك دائر؛ أقل من حوالي 13 فولت = لا يشحن.")),
                  (0x0C, ("Engine speed - compare voltage at idle and 2000 rpm.", "لفات المحرك - قارن الجهد في الخامل وعلى 2000 لفة."))],
    },
    "hard-shift": {
        "name": ("Gearbox shifts hard / slips", "الفتيس بيغيّر بعنف / بيزحلق"), "tag": "hard-shift",
        "intro": ("Automatic gearboxes are sensitive to fluid level and condition.", "الفتيس الأوتوماتيك حساس لمستوى الزيت وحالته."),
        "causes": {"trans-fluid": 3, "trans-solenoid": 2, "adaptation": 2, "limp-mode": 1},
        "questions": [
            _q("stuck", "Does it stay in one gear (e.g. 3rd)?", "بيفضل على غيار واحد (مثلاً الثالث)؟", [
                _o("yes", "Yes", "أيوه", {"limp-mode": 4, "trans-solenoid": 3}),
                _o("no", "No", "لا")]),
            _q("slip", "Do the revs rise without the car accelerating?", "اللفات بتعلى والعربية مش بتسحب؟", [
                _o("yes", "Yes", "أيوه", {"trans-fluid": 4}),
                _o("no", "No", "لا")]),
            _q("battery", "Was the battery disconnected recently?", "البطارية اتفصلت قريب؟", [
                _o("yes", "Yes", "أيوه", {"adaptation": 4}),
                _o("no", "No", "لا")]),
        ],
        "watch": [(0x0C, ("Engine speed.", "لفات المحرك.")), (0x0D, ("Vehicle speed - compare with rpm to see slipping.",
                                                                    "سرعة العربية - قارنها باللفات لترى الزحلقة.")),
                  (0x04, ("Calculated load.", "الحمل المحسوب."))],
    },
    "heater-cold": {
        "name": ("Heater blows cold / gauge stays low", "التدفئة باردة / عداد الحرارة واطي"), "tag": "heater-cold",
        "intro": ("Usually the thermostat or the coolant level.", "غالبًا الثرموستات أو مستوى المياه."),
        "causes": {"thermostat-open": 3, "coolant-low": 2, "heater-core": 2, "air-in-system": 1, "ect-sensor": 1},
        "questions": [
            _q("gauge", "Does the temperature gauge reach the middle?", "عداد الحرارة بيوصل للنص؟", [
                _o("no", "No, stays low", "لا، بيفضل واطي", {"thermostat-open": 4, "ect-sensor": 1}),
                _o("yes", "Yes", "أيوه", {"heater-core": 3, "air-in-system": 2, "thermostat-open": -3})]),
            _q("level", "Coolant level?", "مستوى المياه؟", [
                _o("low", "Low", "ناقص", {"coolant-low": 4}),
                _o("ok", "Correct", "مظبوط", {"coolant-low": -2})]),
        ],
        "watch": [(0x05, ("Coolant temperature - should reach about 85-105 °C after 10-15 minutes.",
                          "حرارة سائل التبريد - يجب أن تصل حوالي 85-105 °م بعد 10-15 دقيقة.")),
                  (0x46, ("Ambient temperature.", "الحرارة الخارجية."))],
    },
    "high-idle": {
        "name": ("Idle too high", "الخامل عالي (اللفات عالية وهي واقفة)"), "tag": "high-idle",
        "intro": ("A fast idle for the first minute after a cold start is normal.", "الخامل العالي أول دقيقة بعد التشغيل على البارد طبيعي."),
        "causes": {"vacuum-leak": 3, "throttle-dirty": 1, "adaptation": 2, "ect-sensor": 2},
        "questions": [
            _q("warm", "Is it still high when fully warm?", "لسه عالي والمحرك سخن تمامًا؟", [
                _o("yes", "Yes", "أيوه", {"vacuum-leak": 2, "adaptation": 1}),
                _o("no", "No, only cold", "لا، على البارد بس", {"ect-sensor": 2})]),
            _q("hiss", "Any hissing sound?", "فيه صوت صفير؟", [
                _o("yes", "Yes", "أيوه", {"vacuum-leak": 4}),
                _o("no", "No", "لا")]),
            _q("battery", "Battery disconnected / throttle cleaned recently?", "البطارية اتفصلت / الثروتل اتنضف قريب؟", [
                _o("yes", "Yes", "أيوه", {"adaptation": 4}),
                _o("no", "No", "لا")]),
        ],
        "watch": [(0x0C, ("Engine speed - a warm idle is usually about 650-900 rpm.", "لفات المحرك - الخامل الساخن عادة حوالي 650-900 لفة.")),
                  (0x05, ("Coolant temperature (the computer raises idle when it thinks the engine is cold).",
                          "حرارة سائل التبريد (الكمبيوتر يرفع الخامل لو فاكر المحرك بارد).")),
                  (0x11, ("Throttle position.", "وضع الثروتل.")), (0x07, ("Long-term fuel trim.", "تصحيح الوقود طويل المدى."))],
    },
}


def ids() -> list[str]:
    return list(SYMPTOMS)


def text(pair, lang: str = "en") -> str:
    if not pair:
        return ""
    return pair[1] if lang == "ar" and len(pair) > 1 else pair[0]


def match(query: str) -> list[str]:
    """Symptom ids for free text ("الموتور بيسخن", "won't start") via the knowledge base's symptom words."""
    from .. import kb
    tags = kb.symptom_tags(query)
    out = [s for s, d in SYMPTOMS.items() if d["tag"] in tags]
    from . import vocab
    q = vocab.norm(query)
    for s, d in SYMPTOMS.items():
        if s not in out and q and (q in vocab.norm(d["name"][0]) or q in vocab.norm(d["name"][1])):
            out.append(s)
    return out


def evaluate(symptom: str, answers: dict | None = None, lang: str = "en", limit: int = 6) -> dict:
    """Rank the causes of *symptom* given *answers* ({question id: option id}).

    -> {"symptom", "name", "intro", "causes": [{"id", "name", "explain", "check", "score", "percent", "pids"}],
        "pids": [PIDs to watch], "watch": [(pid, hint)], "codes": [(code, title)], "notes": [str], "stop": bool,
        "answered": n, "questions": n}"""
    d = SYMPTOMS[symptom]
    answers = answers or {}
    score = {c: float(w) for c, w in d["causes"].items()}
    notes, stop = [], bool(d.get("stop"))
    for q in d["questions"]:
        oid = answers.get(q["id"])
        opt = next((o for o in q["options"] if o["id"] == oid), None)
        if opt is None:
            continue
        for c, w in opt["w"].items():
            score[c] = score.get(c, 0.0) + w
        if opt.get("note"):
            notes.append(text(opt["note"], lang))
        stop = stop or opt.get("stop", False)
    ranked = sorted(((c, s) for c, s in score.items() if s > 0 and c in CAUSES), key=lambda kv: (-kv[1], kv[0]))
    total = sum(s for _, s in ranked) or 1.0
    causes = []
    for c, s in ranked[:limit]:
        cd = CAUSES[c]
        causes.append({"id": c, "name": text(cd["name"], lang), "explain": text(cd["explain"], lang),
                       "check": text(cd["check"], lang), "score": s, "percent": round(100 * s / total),
                       "pids": list(cd["pids"])})
    pids: list[int] = []
    for p, _h in d["watch"]:
        if p not in pids:
            pids.append(p)
    for c in causes[:3]:
        for p in c["pids"]:
            if p not in pids:
                pids.append(p)
    from .. import kb
    sev_rank = {"red": 0, "amber": 1, "green": 2}
    found = []
    for c in kb.codes_for_tag(d["tag"]):
        info = kb.lookup(c)
        if info:
            found.append(((info["tags"].index(d["tag"]), sev_rank.get(info["severity"], 3), c), c, info))
    codes = [(c, kb.text(info, "title", lang)) for _k, c, info in sorted(found, key=lambda t: t[0])]
    return {"symptom": symptom, "name": text(d["name"], lang), "intro": text(d.get("intro"), lang), "causes": causes,
            "pids": pids[:8], "watch": [(p, text(h, lang)) for p, h in d["watch"]], "codes": codes[:20],
            "notes": notes, "stop": stop, "answered": sum(1 for q in d["questions"] if q["id"] in answers),
            "questions": len(d["questions"])}


def validate() -> list[str]:
    """Consistency problems of the wizard data (empty = fine)."""
    from . import vocab
    errs = []
    for s, d in SYMPTOMS.items():
        if d["tag"] not in vocab.TAGS:
            errs.append(f"{s}: unknown tag {d['tag']}")
        for c in d["causes"]:
            if c not in CAUSES:
                errs.append(f"{s}: unknown cause {c}")
        qids = set()
        for q in d["questions"]:
            if q["id"] in qids:
                errs.append(f"{s}: duplicate question {q['id']}")
            qids.add(q["id"])
            for o in q["options"]:
                for c in o["w"]:
                    if c not in CAUSES:
                        errs.append(f"{s}/{q['id']}/{o['id']}: unknown cause {c}")
                if not o["text"][1].strip():
                    errs.append(f"{s}/{q['id']}/{o['id']}: Arabic text missing")
        for p, h in d["watch"]:
            if not (0 < p < 0xE0) or not h[1]:
                errs.append(f"{s}: bad watch entry {p}")
    return errs
