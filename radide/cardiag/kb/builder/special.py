"""Hand-written entries for condition codes (misfire, lean / rich, catalyst, overheating, EVAP leaks ...).
All explanations, causes and checks are RAD IDE's own words (English + Arabic).

S(codes, title_ar, explain_en, explain_ar, causes, checks, sev, drive, ...) - `codes` is one code or a list; the
row's qualifier (" (Bank 2)") is added to the Arabic title by the builder. causes / checks: CAUSES / CHECKS ids from
faults.py or (en, ar) tuples, most likely first."""
from __future__ import annotations

SPECIAL: dict[str, dict] = {}


def S(codes, title_ar, en, ar, causes, checks, sev="amber", drive="caution", tags=(), related=(), monitor=None,
      safety=False, pids=None, emissions=None):
    if isinstance(codes, str):
        codes = [codes]
    for c in codes:
        SPECIAL[c] = dict(title_ar=title_ar, en=en, ar=ar, causes=list(causes), checks=list(checks), sev=sev, drive=drive,
                          tags=list(tags), related=[r for r in related if r != c], monitor=monitor, safety=safety,
                          pids=pids, emissions=emissions)


# ------------------------------------------------------------------ variable valve timing
S(["P0008", "P0009"], "أداء نظام وضع المحرك",
  "The computer compares the crankshaft and camshaft signals and sees that their relationship has drifted. On many "
  "engines this is the classic sign of a stretched timing chain.",
  "يقارن الكمبيوتر إشارتي الكرنك والكامة ويرى أن العلاقة بينهما انحرفت. في كثير من المحركات هذه علامة معروفة على "
  "تمطط سلسلة التوقيت.",
  ["timing_chain", ("Worn chain tensioner or guides", "شداد السلسلة أو مجاريها متآكلة"), "oil_level", "oil_dirty"],
  ["freeze", ("Listen for a rattle at cold start - typical for a worn chain.", "استمع لصوت خشخشة عند التشغيل على البارد - معتاد مع السلسلة الممطوطة."),
   ("Check cam/crank correlation values in live data if your car offers them.", "افحص قيم توافق الكامة والكرنك في البيانات الحية إن كانت متاحة."), "tsb"],
  tags=["noise", "rough-idle", "hard-start"], related=["P0016", "P0017", "P0018", "P0019"], pids=[0x0C])
_vvt = dict(causes=["oil_level", "oil_dirty", ("Sticking camshaft actuator solenoid or blocked screen", "سولينويد الكامة يعلق أو شبكته مسدودة"),
                    ("Faulty cam phaser", "مغيّر وضع الكامة (Phaser) تالف"), "timing_chain"],
            checks=[("Check oil level and condition; change oil if it is old.", "افحص مستوى الزيت وحالته وغيّره إن كان قديمًا."),
                    "actuator_test", ("Compare desired and actual cam angle in live data.", "قارن زاوية الكامة المطلوبة والفعلية في البيانات الحية."), "clear"],
            tags=["rough-idle", "low-power", "noise", "stalling"], pids=[0x0C, 0x05])
S(["P0011", "P0014", "P0021", "P0024"], "وضع عمود الكامات - توقيت مُقدَّم زيادة أو أداء النظام",
  "The camshaft is more advanced than the computer commanded, or it does not follow the command. Variable valve timing "
  "runs on engine oil, so oil level, oil quality and the control solenoid are the usual suspects.",
  "عمود الكامات متقدم أكثر مما طلبه الكمبيوتر، أو لا يتبع الأمر. توقيت الصبابات المتغير يعمل بزيت المحرك، لذلك "
  "مستوى الزيت وجودته وسولينويد التحكم هم المشتبه بهم المعتادون.", **_vvt)
S(["P0012", "P0015", "P0022", "P0025"], "وضع عمود الكامات - توقيت مُؤخَّر زيادة",
  "The camshaft is more retarded than commanded. Low or dirty oil, a sticking solenoid, a worn phaser or a stretched "
  "timing chain can cause it.",
  "عمود الكامات متأخر أكثر من المطلوب. الزيت المنخفض أو المتسخ أو سولينويد يعلق أو Phaser متآكل أو سلسلة توقيت ممطوطة قد تسببه.",
  **_vvt)
S(["P0016", "P0017", "P0018", "P0019"], "توافق وضع عمود الكرنك مع وضع عمود الكامات",
  "The camshaft signal is not where it should be compared with the crankshaft signal. The cause is mechanical (timing "
  "chain/belt) or a cam timing actuator stuck out of place, less often a sensor.",
  "إشارة الكامة ليست في مكانها الصحيح بالنسبة لإشارة الكرنك. السبب ميكانيكي (سلسلة/سير التوقيت) أو مشغّل الكامة عالق "
  "في غير مكانه، وأقل كثيرًا الحساس.",
  ["timing_chain", ("Cam phaser stuck (oil problem)", "الـ Phaser عالق (مشكلة زيت)"), "oil_level",
   ("Faulty cam or crank sensor / damaged tone wheel", "حساس كامة أو كرنك تالف / ترس الحساس تالف")],
  ["freeze", ("If the timing belt/chain was recently replaced, verify the timing marks.", "إذا تم تغيير السير/السلسلة مؤخرًا فتأكد من علامات التوقيت."),
   ("Check oil level and quality.", "افحص مستوى الزيت وجودته."), "clear"],
  tags=["hard-start", "rough-idle", "noise"], related=["P0008", "P0011", "P0335", "P0340"], pids=[0x0C])
S(["P0040", "P0041"], "إشارتا حساسي الأكسجين مبدّلتان",
  "The oxygen sensor of one bank reacts when the computer changes the fuel of the other bank - the connectors are "
  "usually swapped (often after a repair).",
  "حساس الأكسجين في بنك يتفاعل عندما يغيّر الكمبيوتر وقود البنك الآخر - غالبًا الفيشتان مبدّلتان (عادةً بعد إصلاح).",
  [("Sensor connectors swapped between bank 1 and bank 2", "فيشتا الحساسين مبدّلتان بين البنك 1 والبنك 2"), "aftermarket"],
  ["visual", "clear"], sev="green", drive="yes", tags=["fuel-consumption"], monitor="o2", emissions=True)
S("P0049", "سرعة توربين التيربو تجاوزت الحد",
  "The turbo turbine was calculated to spin faster than its safe limit - usually from too much boost.",
  "حُسبت سرعة توربين التيربو أعلى من حدها الآمن - غالبًا بسبب ضغط زائد.",
  ["wastegate", ("Faulty boost control solenoid or vane actuator", "سولينويد التحكم في الضغط أو مشغّل الريش تالف"), "boost_leak"],
  ["freeze", "live", "clear"], sev="amber", tags=["low-power", "limp-mode"], related=["P0234", "P0299"], pids=[0x0B, 0x70])
S("P0068", "عدم توافق MAP/MAF مع وضع الثروتل",
  "The airflow measured by the MAF/MAP sensor does not match what the throttle opening says should flow - an air leak "
  "or a sensor problem.",
  "كمية الهواء التي يقيسها حساس MAF/MAP لا تتفق مع ما يجب أن يمر حسب فتحة الثروتل - تسريب هواء أو مشكلة في حساس.",
  ["vacuum_leak", "maf_dirty", "throttle_dirty", ("Faulty MAP sensor", "حساس MAP تالف")],
  ["smoke_test", "live", "clear"], tags=["rough-idle", "stalling", "limp-mode"], related=["P0101", "P0106", "P0121"],
  pids=[0x10, 0x0B, 0x11])
S("P0069", "عدم توافق ضغط المنفولد مع الضغط الجوي",
  "With the engine off (or at start), manifold pressure should equal barometric pressure. The two readings disagree.",
  "والمحرك مطفأ (أو عند بدء التشغيل) يجب أن يساوي ضغط المنفولد الضغط الجوي. القراءتان لا تتفقان.",
  [("Faulty MAP or barometric sensor", "حساس MAP أو الضغط الجوي تالف"), ("Blocked or leaking MAP sensor hose", "خرطوم حساس MAP مسدود أو مسرّب"), "boost_leak"],
  ["live", "visual", "clear"], tags=["low-power"], related=["P0106", "P2227"], pids=[0x0B, 0x33])
# ------------------------------------------------------------------ fuel pressure
S("P0087", "ضغط مجرى/نظام الوقود منخفض جدًا",
  "The fuel pressure is lower than the computer asked for. The engine may lose power, stall or not start.",
  "ضغط الوقود أقل مما طلبه الكمبيوتر. قد يفقد المحرك القوة أو يطفئ أو لا يدور.",
  [("Clogged fuel filter (very common on diesels)", "فلتر وقود مسدود (شائع جدًا في الديزل)"), ("Weak lift pump or high-pressure pump", "طرمبة الرفع أو طرمبة الضغط العالي ضعيفة"),
   ("Faulty pressure regulator / volume control valve", "منظم الضغط أو صمام التحكم في الكمية تالف"), ("Fuel leak or air in the fuel lines", "تسريب وقود أو هواء في خطوط الوقود"),
   ("Faulty rail pressure sensor", "حساس ضغط المجرى تالف")],
  [("Compare desired and actual rail pressure in live data at idle and under load.", "قارن الضغط المطلوب والفعلي في البيانات الحية في الخامل وتحت الحمل."),
   ("Check when the fuel filter was last changed.", "تأكد متى تم تغيير فلتر الوقود آخر مرة."), "visual", "clear"],
  tags=["no-start", "stalling", "low-power", "limp-mode"], related=["P0088", "P0093", "P0190", "P0191"], pids=[0x23, 0x0A, 0x0C])
S("P0088", "ضغط مجرى/نظام الوقود مرتفع جدًا",
  "The fuel pressure is higher than commanded - usually a regulator or control valve that does not release pressure.",
  "ضغط الوقود أعلى من المطلوب - غالبًا منظم أو صمام تحكم لا يفرّغ الضغط.",
  [("Faulty pressure regulator / pressure control valve", "منظم الضغط أو صمام التحكم في الضغط تالف"), ("Blocked fuel return line", "خط رجوع الوقود مسدود"),
   ("Faulty rail pressure sensor", "حساس ضغط المجرى تالف")],
  [("Compare desired and actual rail pressure.", "قارن الضغط المطلوب والفعلي."), "visual", "clear"],
  tags=["stalling", "limp-mode", "noise"], related=["P0087", "P0190"], pids=[0x23])
S(["P0093", "P0094"], "تم اكتشاف تسريب في نظام الوقود",
  "The computer sees the fuel pressure drop faster than it should - a fuel leak is possible. Fuel leaks are a fire risk.",
  "يرى الكمبيوتر ضغط الوقود ينخفض أسرع من الطبيعي - قد يوجد تسريب وقود. تسريب الوقود خطر حريق.",
  [("External fuel leak (lines, injector seals, pump)", "تسريب وقود خارجي (خطوط أو جوانات رشاشات أو طرمبة)"), ("Leaking injector (internal)", "رشاش يسرّب داخليًا"),
   ("Faulty pressure regulator", "منظم الضغط تالف"), ("Faulty rail pressure sensor", "حساس ضغط المجرى تالف")],
  [("Look and smell for fuel around the engine and under the car; do not drive if fuel is dripping.", "ابحث عن أثر أو رائحة وقود حول المحرك وأسفل السيارة؛ لا تقُد إذا كان الوقود يقطر."),
   "live", "clear"], sev="red", drive="no", tags=["smell", "stalling"], related=["P0087"], safety=True, pids=[0x23])
# ------------------------------------------------------------------ temperatures
S(["P0125", "P0126"], "حرارة سائل التبريد غير كافية",
  "The engine takes too long to reach the temperature the computer needs (for closed-loop fuel control or stable "
  "running). By far the most common cause is a thermostat stuck open.",
  "المحرك يستغرق وقتًا طويلاً للوصول إلى الحرارة التي يحتاجها الكمبيوتر (للتحكم المغلق في الوقود أو للتشغيل المستقر). "
  "أشهر سبب بفارق كبير هو ثرموستات عالق مفتوحًا.",
  ["thermostat_open", ("Faulty coolant temperature sensor reading too cold", "حساس حرارة المحرك تالف ويقرأ أبرد من الحقيقة"), "coolant_low"],
  [("Watch coolant temperature after a cold start: it should reach about 80-95 C within 10-15 minutes of driving.", "راقب حرارة المحرك بعد التشغيل على البارد: يجب أن تصل حوالي 80-95 درجة خلال 10-15 دقيقة قيادة."),
   "compare_sensors", "clear"], sev="green", drive="yes", tags=["fuel-consumption", "heater-cold"], related=["P0128", "P0117", "P0118"],
  pids=[0x05, 0x0F])
S("P0127", "حرارة الهواء الداخل مرتفعة جدًا",
  "The intake air is hotter than expected - on turbo engines this often points to the intercooler.",
  "الهواء الداخل أسخن من المتوقع - في محركات التيربو يشير هذا غالبًا إلى الإنتركولر.",
  [("Blocked or dirty intercooler", "إنتركولر مسدود أو متسخ"), ("Faulty intake air temperature sensor", "حساس حرارة الهواء تالف"), "boost_leak"],
  ["live", "visual", "clear"], tags=["low-power"], related=["P0113"], pids=[0x0F])
S("P0128", "ثرموستات التبريد (حرارة المحرك أقل من حرارة عمل الثرموستات)",
  "The engine did not warm up to its normal temperature in the expected time. Almost always the thermostat is stuck "
  "open, so coolant flows through the radiator too early. The car still drives, but uses more fuel and the heater may "
  "blow cold air.",
  "المحرك لم يسخن إلى حرارته الطبيعية في الوقت المتوقع. في أغلب الأحيان الثرموستات عالق مفتوحًا فيمر سائل التبريد في "
  "الرادياتير مبكرًا. السيارة تمشي لكن الاستهلاك يزيد وقد يخرج هواء بارد من الدفاية.",
  ["thermostat_open", ("Coolant temperature sensor reading lower than reality", "حساس حرارة المحرك يقرأ أقل من الحقيقة"),
   ("Radiator fan running all the time", "مروحة الرادياتير تعمل طوال الوقت"), "coolant_low"],
  [("Watch the coolant temperature graph from a cold start: a slow climb or a drop when driving fast points to the thermostat.", "راقب منحنى حرارة المحرك من التشغيل على البارد: الصعود البطيء أو الهبوط مع السرعة يشير إلى الثرموستات."),
   ("Check that the fan does not run on a cold engine.", "تأكد أن المروحة لا تعمل والمحرك بارد."), "compare_sensors",
   ("After replacing the thermostat, fill and bleed the cooling system (Service Functions > cooling system bleeding).", "بعد تغيير الثرموستات املأ دورة التبريد وفرّغ الهواء منها (وظائف الصيانة > تفريغ هواء دورة التبريد)."), "clear"],
  sev="green", drive="yes", tags=["fuel-consumption", "heater-cold"], related=["P0125", "P0116", "P2181"], pids=[0x05, 0x0F])
S("P0129", "الضغط الجوي منخفض جدًا",
  "The barometric pressure reading is lower than any real-world value.", "قراءة الضغط الجوي أقل من أي قيمة حقيقية ممكنة.",
  [("Faulty barometric / MAP sensor", "حساس الضغط الجوي / MAP تالف"), "conn"], ["live", "visual", "clear"], sev="green",
  drive="yes", related=["P2227"], pids=[0x33])
S("P0148", "خطأ في توصيل الوقود",
  "The fuel delivered (mainly diesel) does not match what the computer commanded.", "الوقود الذي تم توصيله (أساسًا ديزل) لا يطابق ما طلبه الكمبيوتر.",
  [("Clogged fuel filter or air in the fuel", "فلتر وقود مسدود أو هواء في الوقود"), ("Weak injection pump", "طرمبة حقن ضعيفة"), "fuel_quality"],
  ["live", "visual", "clear"], tags=["low-power", "stalling", "no-start"], related=["P0087"], pids=[0x23])
S("P0149", "خطأ في توقيت الوقود", "The injection timing differs from the target (mainly diesel injection pumps).",
  "توقيت الحقن يختلف عن المطلوب (أساسًا طرمبات حقن الديزل).",
  [("Faulty injection pump timing device", "جهاز توقيت طرمبة الحقن تالف"), "fuel_quality", ("Pump timing set wrong after repair", "توقيت الطرمبة مضبوط خطأ بعد إصلاح")],
  ["live", "clear"], tags=["smoke", "noise", "low-power"])
S("P0168", "حرارة الوقود مرتفعة جدًا", "The fuel is hotter than allowed (diesel return fuel can get very hot).",
  "الوقود أسخن من المسموح (وقود الرجوع في الديزل قد يسخن جدًا).",
  [("Low fuel level on a hot day", "مستوى وقود منخفض في يوم حار"), ("Faulty fuel cooler", "مبرد الوقود تالف"), ("Faulty fuel temperature sensor", "حساس حرارة الوقود تالف")],
  ["live", "clear"], sev="green", drive="yes", related=["P0180"])
S("P0169", "تركيب الوقود غير صحيح", "The fuel does not match what the engine expects (wrong fuel or water in the fuel).",
  "الوقود لا يطابق ما يتوقعه المحرك (وقود خاطئ أو ماء في الوقود).",
  ["fuel_quality", ("Wrong fuel filled (petrol in diesel or the opposite)", "تمويل وقود خاطئ (بنزين في ديزل أو العكس)"), ("Water in the fuel", "ماء في الوقود")],
  [("If wrong fuel was filled, do not start the engine - have the tank drained.", "إذا تم تمويل وقود خاطئ فلا تشغّل المحرك - اسحب التانك."), "clear"],
  sev="red", drive="no", tags=["no-start", "smoke", "low-power"])
# ------------------------------------------------------------------ fuel trim
_lean = dict(causes=["vacuum_leak", "maf_dirty", "fuel_pressure_low", "injector_dirty", "exhaust_leak",
                     ("PCV valve or hose leaking", "صمام PCV أو خرطومه يسرّب")],
             checks=["fuel_trims", ("If the trims fall at 2500 rpm, look for a vacuum leak; if they rise with load, suspect fuel supply or the MAF.",
                                    "إذا انخفض التصحيح على 2500 لفة فابحث عن تسريب هواء؛ وإذا زاد مع الحمل فاشتبه في تغذية الوقود أو MAF."),
                     "smoke_test", ("Check the fuel pressure with a gauge.", "افحص ضغط الوقود بعداد."), "clear"],
             tags=["rough-idle", "hesitation", "stalling", "low-power"], monitor="fuel", pids=[0x06, 0x07, 0x08, 0x09, 0x10, 0x14])
_rich = dict(causes=[("Leaking injector or too high fuel pressure", "رشاش يسرّب أو ضغط وقود مرتفع"), "maf_dirty",
                     ("Faulty coolant temperature sensor (reads too cold)", "حساس حرارة المحرك تالف (يقرأ أبرد)"), "air_filter",
                     "purge_valve", ("Oil diluted with fuel", "زيت المحرك مخفف بالوقود")],
             checks=["fuel_trims", "compare_sensors", ("Check the air filter and fuel pressure.", "افحص فلتر الهواء وضغط الوقود."), "clear"],
             tags=["fuel-consumption", "smoke", "smell", "rough-idle"], monitor="fuel", pids=[0x06, 0x07, 0x08, 0x09, 0x10, 0x05])
S(["P0170", "P0173"], "تصحيح الوقود",
  "The computer has corrected the fuel mixture up to its limit and still cannot reach the right air/fuel ratio.",
  "الكمبيوتر صحّح خليط الوقود حتى أقصى حد ولا يزال لا يصل إلى النسبة الصحيحة بين الهواء والوقود.",
  _lean["causes"][:3] + _rich["causes"][:2], _lean["checks"], tags=["rough-idle", "fuel-consumption"], monitor="fuel",
  related=["P0171", "P0172"], pids=_lean["pids"])
S(["P0171", "P0174"], "النظام فقير جدًا (خليط فقير)",
  "There is too much air or too little fuel - the computer had to add a lot of fuel (positive fuel trim) and hit its "
  "limit. The most common cause is an air leak after the air-flow sensor; low fuel pressure and a dirty MAF are next.",
  "يوجد هواء زائد أو وقود ناقص - اضطر الكمبيوتر لإضافة وقود كثير (تصحيح موجب) ووصل إلى حده. أشهر سبب تسريب هواء بعد "
  "حساس تدفق الهواء، يليه ضغط وقود منخفض وحساس MAF متسخ.",
  related=["P0171", "P0174", "P0101", "P0300"], **_lean)
S(["P0172", "P0175"], "النظام غني جدًا (خليط غني)",
  "There is too much fuel or too little air - the computer had to remove a lot of fuel (negative fuel trim) and hit its "
  "limit.",
  "يوجد وقود زائد أو هواء ناقص - اضطر الكمبيوتر لتقليل الوقود كثيرًا (تصحيح سالب) ووصل إلى حده.",
  related=["P0172", "P0175", "P0101", "P0420"], **_rich)
for codes, where_en, where_ar in ((["P2177", "P2179"], "away from idle (at cruise)", "بعيدًا عن الخامل (أثناء السير)"),
                                  (["P2187", "P2189"], "at idle", "في الوضع الخامل"),
                                  (["P2191", "P2193"], "at higher load", "عند الحمل العالي")):
    S(codes, f"النظام فقير جدًا {where_ar}",
      f"The mixture is too lean {where_en}. At idle an air leak is the usual cause; at higher load think of fuel supply "
      "(pump, filter, injectors) or the MAF sensor.",
      f"الخليط فقير جدًا {where_ar}. في الخامل يكون تسريب الهواء هو السبب المعتاد؛ وعند الحمل العالي فكّر في تغذية الوقود "
      "(الطرمبة أو الفلتر أو الرشاشات) أو حساس MAF.", related=["P0171", "P0174"], **_lean)
for codes, where_en, where_ar in ((["P2178", "P2180"], "away from idle (at cruise)", "بعيدًا عن الخامل (أثناء السير)"),
                                  (["P2188", "P2190"], "at idle", "في الوضع الخامل"),
                                  (["P2192", "P2194"], "at higher load", "عند الحمل العالي")):
    S(codes, f"النظام غني جدًا {where_ar}", f"The mixture is too rich {where_en}.", f"الخليط غني جدًا {where_ar}.",
      related=["P0172", "P0175"], **_rich)
# ------------------------------------------------------------------ overheating / over-temperature
S("P0217", "حالة ارتفاع حرارة سائل التبريد",
  "The engine has overheated. Continuing to drive can warp the cylinder head or blow the head gasket. Stop, let it cool "
  "down and find the cause before driving again.",
  "المحرك سخن زيادة (سخونية). الاستمرار في القيادة قد يؤدي إلى اعوجاج وش السلندر أو ضرب جوان الوش. توقف واترك المحرك "
  "يبرد وابحث عن السبب قبل القيادة مرة أخرى.",
  ["coolant_low", "fan", "thermostat_closed", "water_pump", "radiator", "air_in_cooling", "head_gasket"],
  [("Never open the radiator cap on a hot engine - wait until it is cold.", "لا تفتح غطاء الرادياتير والمحرك ساخن أبدًا - انتظر حتى يبرد."),
   ("Cold engine: check the coolant level in the reservoir and look for leaks.", "والمحرك بارد: افحص مستوى سائل التبريد في القربة وابحث عن تسريب."),
   ("Run the fan test (Service Functions) and check that the fan starts at about 95-105 C.", "شغّل اختبار المروحة (وظائف الصيانة) وتأكد أن المروحة تعمل عند حوالي 95-105 درجة."),
   ("After any repair, bleed the air out of the cooling system (Service Functions > cooling system bleeding).", "بعد أي إصلاح فرّغ الهواء من دورة التبريد (وظائف الصيانة > تفريغ هواء دورة التبريد)."),
   ("White smoke, bubbles in the reservoir or coolant loss without a visible leak point to the head gasket.", "الدخان الأبيض أو الفقاعات في القربة أو نقص سائل التبريد بدون تسريب ظاهر تشير إلى جوان الوش.")],
  sev="red", drive="no", tags=["overheating", "fan", "smoke", "steam"], related=["P0118", "P0480", "P2181", "P0128"], safety=True,
  pids=[0x05, 0x0C, 0x0D])
S("P0218", "حالة ارتفاع حرارة زيت الفتيس",
  "The automatic transmission fluid is too hot. Hot fluid wears the gearbox quickly.",
  "زيت الفتيس الأوتوماتيك ساخن جدًا. الزيت الساخن يستهلك الفتيس بسرعة.",
  ["trans_fluid", ("Blocked transmission cooler", "مبرد زيت الفتيس مسدود"), ("Heavy towing or long uphill driving", "جر أحمال ثقيلة أو صعود طويل"), "trans_internal"],
  ["fluid_level", "live", "clear"], sev="red", drive="no", tags=["hard-shift", "overheating"], related=["P0711"], safety=True)
S("P0219", "حالة تجاوز سرعة المحرك", "The engine speed went above its safe limit (for example a wrong downshift).",
  "سرعة المحرك تجاوزت حدها الآمن (مثلاً تنزيل غيار خاطئ).",
  [("Missed or wrong gear change", "تبديل غيار خاطئ"), ("Faulty engine speed signal", "إشارة سرعة المحرك تالفة")], ["freeze", "clear"],
  related=["P0335"])
S("P0234", "حالة زيادة ضغط التيربو",
  "The turbo makes more boost than the computer allows. The engine often goes into limp mode to protect itself.",
  "التيربو ينتج ضغطًا أعلى مما يسمح به الكمبيوتر. غالبًا يدخل المحرك وضع الطوارئ ليحمي نفسه.",
  ["wastegate", ("Sticking variable vanes (carbon)", "الريش المتغيرة عالقة (كربون)"), ("Faulty boost control solenoid or vacuum hose", "سولينويد التحكم في الضغط أو خرطوم الفاكيوم تالف"),
   ("Faulty boost pressure sensor", "حساس ضغط التيربو تالف")],
  [("Compare requested and actual boost in live data.", "قارن الضغط المطلوب والفعلي في البيانات الحية."), "visual", "clear"],
  tags=["limp-mode", "low-power"], related=["P0299", "P0049", "P0235"], pids=[0x0B, 0x70])
S("P0299", "ضغط التيربو/السوبرتشارجر أقل من المطلوب",
  "The turbo does not make the boost the computer asks for. You feel a lack of power; the engine may go into limp mode.",
  "التيربو لا ينتج الضغط الذي يطلبه الكمبيوتر. تشعر بضعف في القوة، وقد يدخل المحرك وضع الطوارئ.",
  ["boost_leak", "wastegate", "turbo_wear", ("Faulty boost control solenoid or vacuum supply", "سولينويد التحكم في الضغط أو مصدر الفاكيوم تالف"),
   ("Blocked exhaust (DPF / catalyst)", "عادم مسدود (DPF أو الدبّة)")],
  [("Compare requested and actual boost while accelerating.", "قارن الضغط المطلوب والفعلي أثناء التسارع."),
   ("Listen for hissing and check intercooler hoses and clamps.", "استمع لصوت تسريب (هسهسة) وافحص خراطيم الإنتركولر ومشابكها."), "clear"],
  tags=["low-power", "limp-mode", "smoke"], related=["P0234", "P0101", "P2463"], pids=[0x0B, 0x70, 0x0C])
S("P0297", "حالة تجاوز سرعة السيارة", "The vehicle speed exceeded the limit stored in the computer.",
  "سرعة السيارة تجاوزت الحد المخزن في الكمبيوتر.", [("Driven above the speed limiter", "قيادة فوق محدد السرعة"), ("Wrong speed signal", "إشارة سرعة خاطئة")],
  ["freeze", "clear"], sev="green", drive="yes", related=["P0500"])
S("P0298", "ارتفاع حرارة زيت المحرك",
  "The engine oil is too hot. Hot oil gets thin and protects the engine poorly.", "زيت المحرك ساخن جدًا. الزيت الساخن يخف ويحمي المحرك بشكل ضعيف.",
  ["oil_level", ("Cooling system problem (see overheating)", "مشكلة في دورة التبريد (انظر السخونية)"), ("Blocked oil cooler", "مبرد الزيت مسدود")],
  ["live", "fluid_level", "clear"], sev="red", drive="no", tags=["overheating"], related=["P0217", "P0196"], safety=True, pids=[0x5C, 0x05])
# ------------------------------------------------------------------ misfire
_mis_causes = ["spark_plug", "coil", "injector_dirty", "vacuum_leak", "compression", "fuel_quality"]
_mis_checks = [("A flashing check-engine light means heavy misfire: slow down and avoid high load - it can melt the catalyst.",
                "لمبة المحرك التي تومض تعني احتراقًا ناقصًا شديدًا: هدّئ السرعة وتجنب الحمل العالي - قد يذيب الدبّة."),
               ("Watch the misfire counters in live data (Mode 06) to see which cylinder misfires.", "راقب عدادات الاحتراق الناقص في البيانات الحية (Mode 06) لترى أي أسطوانة."),
               ("Swap the coil (then the plug) with another cylinder: does the misfire move?", "بدّل الموبينة (ثم البوجيه) مع أسطوانة أخرى: هل ينتقل العطل؟"),
               "fuel_trims", ("If plug and coil are fine, do a compression test.", "إذا كانت البوجيه والموبينة سليمتين فاعمل اختبار ضغط سلندرات.")]
S("P0300", "احتراق ناقص عشوائي/في أكثر من أسطوانة",
  "Several cylinders are misfiring (not burning properly). The engine shakes, loses power, and unburnt fuel can overheat "
  "and destroy the catalytic converter. When several cylinders misfire, look for something they share: fuel pressure, "
  "air leaks, the MAF, timing or fuel quality.",
  "عدة أسطوانات بها احتراق ناقص (لا تحترق بشكل صحيح). المحرك يرج ويفقد القوة، والوقود غير المحترق قد يسخّن الدبّة "
  "ويتلفها. عندما تتأثر عدة أسطوانات ابحث عن شيء مشترك بينها: ضغط الوقود أو تسريب الهواء أو MAF أو التوقيت أو جودة الوقود.",
  ["vacuum_leak", "fuel_pressure_low", "spark_plug", "fuel_quality", "maf_dirty", "timing_chain", "compression"], _mis_checks,
  tags=["misfire", "rough-idle", "shaking", "low-power"], related=["P0171", "P0174"] + [f"P{300 + n:04d}" for n in range(1, 9)],
  monitor="misfire", pids=[0x0C, 0x04, 0x06, 0x07, 0x05])
for n in range(1, 13):
    S(f"P{300 + n:04d}", f"احتراق ناقص في الأسطوانة {n}",
      f"Cylinder {n} is misfiring (the mixture does not burn properly). A single cylinder usually means a part of that "
      "cylinder: spark plug, coil, injector, or a mechanical problem such as low compression.",
      f"الأسطوانة {n} بها احتراق ناقص (الخليط لا يحترق بشكل صحيح). أسطوانة واحدة تعني غالبًا قطعة خاصة بها: البوجيه أو "
      "الموبينة أو الرشاش، أو مشكلة ميكانيكية مثل ضغط منخفض.",
      _mis_causes, _mis_checks, tags=["misfire", "rough-idle", "shaking", "low-power"],
      related=["P0300", f"P{350 + n:04d}", f"P{200 + n:04d}"], monitor="misfire", pids=[0x0C, 0x04])
S("P0313", "احتراق ناقص مع انخفاض الوقود",
  "Misfire was detected while the tank was nearly empty - the pump may have sucked air.", "تم اكتشاف احتراق ناقص والتانك شبه فارغ - ربما سحبت الطرمبة هواء.",
  [("Running the tank too low", "تشغيل السيارة والتانك شبه فارغ"), "fuel_pressure_low", "spark_plug"],
  [("Refuel, clear the code and see if it returns.", "موّل الوقود وامسح العطل وراقب هل يعود."), "clear"], tags=["misfire"], monitor="misfire",
  related=["P0300"], pids=[0x2F, 0x0C])
S("P0314", "احتراق ناقص في أسطوانة واحدة (غير محددة)", "One cylinder misfires but the computer cannot tell which one.",
  "أسطوانة واحدة بها احتراق ناقص لكن الكمبيوتر لا يستطيع تحديدها.", _mis_causes, _mis_checks, tags=["misfire", "rough-idle"],
  monitor="misfire", related=["P0300"], pids=[0x0C])
S("P0315", "تغيّر نظام وضع الكرنك لم يتم تعلّمه",
  "The computer has not learned the small tolerances of the crankshaft tone wheel, which it needs to detect misfires. "
  "This is common after replacing the ECU, crank sensor or flywheel.",
  "الكمبيوتر لم يتعلم الفروق الصغيرة في ترس حساس الكرنك والتي يحتاجها لاكتشاف الاحتراق الناقص. شائع بعد تغيير الكمبيوتر أو "
  "حساس الكرنك أو الحدافة.",
  ["learn", ("ECU, crank sensor or flywheel recently replaced", "تم تغيير الكمبيوتر أو حساس الكرنك أو الحدافة مؤخرًا")],
  [("Run the crankshaft variation (CKP) relearn in Service Functions if your car supports it.", "شغّل تعليم حساس الكرنك (CKP Relearn) من وظائف الصيانة إن كانت سيارتك تدعمه."), "clear"],
  sev="green", drive="yes", related=["P0335"], monitor="misfire")
S("P0316", "احتراق ناقص عند بدء التشغيل (أول 1000 لفة)",
  "A misfire happened right after starting. Damp plugs or coils, a leaking injector or low fuel pressure at start are typical.",
  "حدث احتراق ناقص بعد التشغيل مباشرةً. البوجيهات أو الموبينات الرطبة أو رشاش يسرّب أو ضغط وقود منخفض عند البدء أسباب معتادة.",
  ["spark_plug", "coil", ("Leaking injector or fuel pressure loss overnight", "رشاش يسرّب أو فقد ضغط الوقود طوال الليل"), "fuel_quality"],
  _mis_checks, tags=["misfire", "hard-start", "rough-idle"], monitor="misfire", related=["P0300"], pids=[0x0C, 0x05])
S("P0324", "خطأ في نظام التحكم في الطرق (Knock)",
  "The knock control system cannot work properly - often the knock sensor signal is implausible or there is real engine knock.",
  "نظام التحكم في الطرق لا يعمل بشكل سليم - غالبًا إشارة حساس الطرق غير منطقية أو يوجد طرق حقيقي في المحرك.",
  ["fuel_quality", ("Faulty knock sensor or its wiring", "حساس الطرق أو أسلاكه تالفة"), ("Mechanical engine noise", "صوت ميكانيكي في المحرك")],
  ["visual", "freeze", "clear"], tags=["low-power", "noise"], related=["P0325", "P0330"], pids=[0x0E])
S("P0363", "احتراق ناقص - تم إيقاف الوقود",
  "The misfire was so severe that the computer cut the fuel to that cylinder to protect the catalyst.",
  "الاحتراق الناقص كان شديدًا لدرجة أن الكمبيوتر قطع الوقود عن تلك الأسطوانة لحماية الدبّة.",
  _mis_causes, _mis_checks, sev="red", drive="no", tags=["misfire", "shaking", "low-power"], monitor="misfire", related=["P0300"],
  pids=[0x0C])
for i in range(12):
    L = "ABCDEFGHIJKL"[i]
    S(f"P{2302 + 3 * i}", f"الموبينة \"{L}\" - الدائرة الثانوية",
      f"The high-voltage (secondary) side of ignition coil {L} does not behave as expected - the spark may be weak or missing.",
      f"الجانب عالي الجهد (الثانوي) للموبينة {L} لا يعمل كما هو متوقع - قد تكون الشرارة ضعيفة أو مفقودة.",
      ["coil", "spark_plug", ("Damaged coil boot / plug lead", "جلبة الموبينة أو سلك البوجيه تالف"), "conn"],
      ["visual", ("Swap the coil with another cylinder and see if the code follows it.", "بدّل الموبينة مع أسطوانة أخرى وراقب هل ينتقل الكود معها."), "clear"],
      tags=["misfire", "rough-idle"], related=["P0300", f"P{351 + i:04d}"], pids=[0x0C])
for n in range(1, 13):
    S(f"P{263 + 3 * (n - 1):04d}", f"مساهمة/توازن الأسطوانة {n}",
      f"Cylinder {n} contributes less (or more) power than the others - the computer measures this from tiny changes in "
      "crankshaft speed. On diesels it usually means an injector that delivers the wrong amount.",
      f"الأسطوانة {n} تساهم بقوة أقل (أو أكثر) من الباقي - يقيس الكمبيوتر ذلك من تغيرات صغيرة في سرعة الكرنك. في الديزل "
      "يعني غالبًا رشاشًا يضخ كمية خاطئة.",
      ["injector_dirty", "compression", ("Injector coding/adaptation wrong after replacement", "ترميز أو تعليم الرشاش خاطئ بعد التغيير")],
      [("Read the injector correction (balance) values if available.", "اقرأ قيم تصحيح الرشاشات (التوازن) إن كانت متاحة."), "clear"],
      tags=["rough-idle", "shaking", "smoke"], related=[f"P{300 + n:04d}"], pids=[0x0C])
# ------------------------------------------------------------------ EGR / secondary air / catalyst
S("P0401", "تدفق EGR غير كافٍ",
  "Less exhaust gas flows back through the EGR than expected - very often carbon has clogged the valve or passages.",
  "كمية غازات العادم الراجعة عبر EGR أقل من المتوقع - غالبًا الكربون سدّ الصمام أو المجاري.",
  ["egr_carbon", "egr_valve", "egr_vacuum", ("Faulty EGR position or pressure (DPFE) sensor", "حساس وضع أو ضغط EGR (DPFE) تالف")],
  ["actuator_test", ("Watch commanded vs actual EGR in live data.", "راقب EGR المطلوب والفعلي في البيانات الحية."), "visual", "clear"],
  sev="green", drive="yes", tags=["knock", "low-power"], related=["P0400", "P0404", "P2413"], monitor="egr", pids=[0x2C, 0x2D],
  emissions=True)
S("P0402", "تدفق EGR زائد",
  "Too much exhaust gas flows back - the EGR valve may be stuck open. This can cause rough idle and stalling.",
  "كمية زائدة من غازات العادم ترجع - قد يكون صمام EGR عالقًا مفتوحًا. هذا يسبب رجّة في الخامل وانطفاء.",
  ["egr_valve", "egr_carbon", ("Faulty EGR control solenoid", "سولينويد التحكم في EGR تالف")], ["actuator_test", "live", "clear"],
  tags=["rough-idle", "stalling"], related=["P0401", "P0404"], monitor="egr", pids=[0x2C, 0x2D], emissions=True)
S("P2413", "أداء نظام EGR", "The EGR system does not deliver the effect the computer expects.",
  "نظام EGR لا يعطي التأثير الذي يتوقعه الكمبيوتر.", ["egr_carbon", "egr_valve", "egr_vacuum"], ["actuator_test", "live", "clear"],
  related=["P0401", "P0402"], monitor="egr", pids=[0x2C, 0x2D], emissions=True)
S("P2457", "أداء نظام تبريد EGR",
  "The EGR cooler does not cool the exhaust gas enough. A leaking EGR cooler can also lose coolant into the engine.",
  "مبرد EGR لا يبرد غازات العادم بشكل كافٍ. مبرد EGR المسرّب قد يفقد سائل التبريد داخل المحرك أيضًا.",
  [("Clogged or leaking EGR cooler", "مبرد EGR مسدود أو يسرّب"), "coolant_low", ("Faulty EGR temperature sensor", "حساس حرارة EGR تالف")],
  [("Watch the coolant level - unexplained coolant loss with white smoke points to a leaking cooler.", "راقب مستوى سائل التبريد - النقص بدون سبب ظاهر مع دخان أبيض يشير إلى تسريب المبرد."), "clear"],
  tags=["smoke", "overheating"], related=["P0401"], monitor="egr", emissions=True)
S(["P0491", "P0492"], "تدفق حقن الهواء الثانوي غير كافٍ",
  "After a cold start the secondary air pump should blow air into the exhaust; the computer saw too little effect.",
  "بعد التشغيل على البارد يجب أن تنفخ طرمبة الهواء الثانوي هواءً في العادم؛ رأى الكمبيوتر تأثيرًا قليلاً جدًا.",
  [("Air pump failed (often water damage)", "طرمبة الهواء تالفة (غالبًا بسبب المياه)"), ("Check/combination valve stuck", "صمام عدم الرجوع عالق"),
   ("Cracked air hose or blocked ports", "خرطوم هواء مشروخ أو فتحات مسدودة"), "fuse_relay"],
  ["actuator_test", "fuse", "visual", "clear"], sev="green", drive="yes", tags=["noise"], related=["P0410"], monitor="secondary-air",
  emissions=True)
_cat_causes = ["catalyst_worn", "exhaust_leak", "o2_aging", ("Earlier misfire or rich running damaged the catalyst", "احتراق ناقص أو خليط غني سابق أتلف الدبّة"),
               ("Oil or coolant burning in the engine", "حرق زيت أو سائل تبريد في المحرك")]
_cat_checks = [("Fix any misfire or fuel-trim codes first - they damage catalysts.", "أصلح أي أكواد احتراق ناقص أو تصحيح وقود أولاً - فهي تتلف الدبّة."),
               ("Compare the oxygen sensors: the one after the catalyst should stay fairly steady (about 0.6-0.8 V), not copy the one before it.",
                "قارن حساسي الأكسجين: الحساس بعد الدبّة يجب أن يبقى ثابتًا نسبيًا (حوالي 0.6 - 0.8 فولت) ولا يقلد الحساس الذي قبلها."),
               ("Check for exhaust leaks near the sensors.", "افحص وجود تسريب في الشكمان قرب الحساسات."), "clear"]
S(["P0420", "P0430"], "كفاءة نظام المحوّل الحفزي أقل من الحد",
  "The catalytic converter is not cleaning the exhaust as well as it should. The computer knows this because the oxygen "
  "sensor after the catalyst starts to switch like the one before it. The car drives normally, but the catalyst may be "
  "worn - first rule out exhaust leaks, sensor problems and misfires.",
  "المحوّل الحفزي (الدبّة) لا ينظّف العادم كما يجب. يعرف الكمبيوتر ذلك لأن حساس الأكسجين بعد الدبّة يبدأ بالتذبذب مثل الحساس "
  "الذي قبلها. السيارة تمشي عاديًا لكن الدبّة قد تكون منتهية - استبعد أولاً تسريب الشكمان ومشاكل الحساسات والاحتراق الناقص.",
  _cat_causes, _cat_checks, sev="green", drive="yes", tags=["smell", "emissions-test"], related=["P0300", "P0171", "P0136"],
  monitor="catalyst", pids=[0x14, 0x15, 0x18, 0x19], emissions=True)
S(["P0421", "P0431"], "كفاءة دبّة التسخين المبدئي أقل من الحد", "The warm-up (front) catalyst does not clean well enough.",
  "دبّة التسخين المبدئي (الأمامية) لا تنظّف بشكل كافٍ.", _cat_causes, _cat_checks, sev="green", drive="yes", related=["P0420"],
  monitor="catalyst", emissions=True)
S(["P0422", "P0432"], "كفاءة الدبّة الرئيسية أقل من الحد", "The main catalyst does not clean well enough.",
  "الدبّة الرئيسية لا تنظّف بشكل كافٍ.", _cat_causes, _cat_checks, sev="green", drive="yes", related=["P0420"],
  monitor="catalyst", emissions=True)
S(["P0423", "P0433"], "كفاءة الدبّة المسخّنة أقل من الحد", "The heated catalyst does not clean well enough.",
  "الدبّة المسخّنة لا تنظّف بشكل كافٍ.", _cat_causes, _cat_checks, sev="green", drive="yes", related=["P0420"],
  monitor="heated-catalyst", emissions=True)
S(["P0424", "P0434"], "حرارة الدبّة المسخّنة أقل من الحد", "The heated catalyst does not reach its working temperature.",
  "الدبّة المسخّنة لا تصل إلى حرارة عملها.", [("Faulty catalyst heater or its supply", "سخان الدبّة أو تغذيته تالفة")] + _cat_causes[:2],
  ["fuse", "clear"], sev="green", drive="yes", related=["P0429"], monitor="heated-catalyst", emissions=True)
S(["P2000", "P2001"], "كفاءة مصيدة NOx أقل من الحد", "The NOx storage catalyst no longer stores enough NOx.",
  "دبّة تخزين NOx لم تعد تخزن كمية كافية من أكاسيد النيتروجين.", ["catalyst_worn", "nox_sensor", "fuel_quality"], ["live", "clear"],
  sev="green", drive="yes", related=["P2200"], monitor="nox", emissions=True)
S(["P2002", "P2003"], "كفاءة فلتر الجزيئات أقل من الحد",
  "The particulate filter lets too much soot through - it may be cracked, or the pressure sensor reading is wrong.",
  "فلتر الجزيئات يسمح بمرور سناج كثير - قد يكون مشروخًا أو قراءة حساس الضغط خاطئة.",
  [("Cracked or damaged DPF", "فلتر DPF مشروخ أو تالف"), "dpf_lines", ("Faulty DPF pressure sensor", "حساس ضغط DPF تالف")],
  ["live", "visual", "clear"], related=["P2452", "P2463"], monitor="pm", emissions=True, tags=["smoke"])
S("P2458", "مدة تجديد فلتر الجزيئات", "The last DPF regeneration took too long or was interrupted many times.",
  "آخر عملية تجديد لفلتر الجزيئات استغرقت وقتًا طويلاً أو انقطعت مرات كثيرة.",
  ["dpf_soot", ("Short trips interrupting the regeneration", "مشاوير قصيرة تقطع التجديد"), ("Faulty exhaust temperature sensor", "حساس حرارة العادم تالف")],
  [("Drive 20-30 minutes at steady speed on a highway, or run a service regeneration (Service Functions).", "قُد 20-30 دقيقة بسرعة ثابتة على طريق سريع، أو شغّل تجديدًا خدميًا (وظائف الصيانة)."), "clear"],
  tags=["limp-mode"], related=["P2463", "P2459"], monitor="pm", emissions=True, pids=[0x7A, 0x7C])
S("P2459", "تكرار تجديد فلتر الجزيئات", "The DPF needs to regenerate much more often than normal.",
  "فلتر الجزيئات يحتاج إلى التجديد أكثر بكثير من الطبيعي.",
  [("Engine producing too much soot (injectors, EGR, air leak, boost)", "المحرك ينتج سناجًا كثيرًا (رشاشات أو EGR أو تسريب هواء أو ضغط تيربو)"), "dpf_lines", "dpf_ash"],
  ["live", "clear"], related=["P2463", "P2458"], monitor="pm", emissions=True, tags=["smoke"])
S("P2463", "انسداد فلتر الجزيئات - تراكم السناج",
  "The particulate filter is heavily loaded with soot. The engine may go into limp mode. Regular highway drives normally "
  "burn the soot off; a workshop can run a service regeneration. If the load is extreme the filter may need cleaning.",
  "فلتر الجزيئات ممتلئ بالسناج بشدة. قد يدخل المحرك وضع الطوارئ. القيادة المنتظمة على الطريق السريع تحرق السناج عادةً، "
  "ويمكن للورشة عمل تجديد خدمي. إذا كان الامتلاء شديدًا جدًا قد يحتاج الفلتر إلى تنظيف.",
  ["dpf_soot", "dpf_lines", ("Faulty injector or EGR causing extra soot", "رشاش أو EGR تالف يسبب سناجًا زائدًا"), "dpf_ash"],
  [("Read the soot load and differential pressure in live data.", "اقرأ نسبة السناج وفرق الضغط في البيانات الحية."),
   ("If the load allows it, run a service regeneration (Service Functions) with the engine warm and the car parked outdoors.", "إذا سمحت النسبة فشغّل تجديدًا خدميًا (وظائف الصيانة) والمحرك ساخن والسيارة في مكان مفتوح."),
   "clear"], tags=["limp-mode", "low-power", "smoke"], related=["P2002", "P2452", "P2458"], monitor="pm", emissions=True,
  pids=[0x7A, 0x7B, 0x7C])
# ------------------------------------------------------------------ EVAP
_evap_checks = [("First check that the fuel cap is tight (it should click) and its seal is not cracked.", "أولاً تأكد أن غطاء التانك محكم (يُصدر تكّة) وأن جلدته غير مشروخة."),
                ("Inspect the EVAP hoses near the tank and the canister.", "افحص خراطيم EVAP قرب التانك وعلبة الفحم."),
                ("A smoke test finds small leaks reliably.", "اختبار الدخان يكشف التسريبات الصغيرة بشكل موثوق."), "clear"]
S("P0440", "نظام أبخرة الوقود (EVAP)", "The EVAP system self-test failed.", "فشل الاختبار الذاتي لنظام أبخرة الوقود.",
  ["gas_cap", "evap_hose", "purge_valve", "vent_valve", "canister"], _evap_checks, sev="green", drive="yes", tags=["smell"],
  related=["P0442", "P0455"], monitor="evap", emissions=True)
S("P0441", "تدفق تنقية غير صحيح في نظام EVAP", "The purge flow is not what the computer expects (none or too much).",
  "تدفق التنقية ليس كما يتوقع الكمبيوتر (معدوم أو زائد).", ["purge_valve", "evap_hose", "canister"], ["actuator_test", "visual", "clear"],
  sev="green", drive="yes", related=["P0496", "P0497"], monitor="evap", emissions=True)
S("P0442", "تسريب صغير في نظام EVAP",
  "The EVAP system has a small leak - fuel vapour can escape. It does not affect how the car drives. A loose or worn fuel "
  "cap is the most common cause.",
  "يوجد تسريب صغير في نظام EVAP - قد تخرج أبخرة الوقود. لا يؤثر على قيادة السيارة. غطاء التانك المفكوك أو التالف هو "
  "السبب الأكثر شيوعًا.", ["gas_cap", "evap_hose", "purge_valve", "vent_valve", "canister"], _evap_checks, sev="green", drive="yes",
  tags=["smell"], related=["P0455", "P0456"], monitor="evap", emissions=True)
S("P0446", "دائرة التحكم في تهوية نظام EVAP", "The vent valve circuit or function is not correct.", "دائرة أو وظيفة صمام التهوية غير سليمة.",
  ["vent_valve", "conn", "wire_open"], ["visual", "actuator_test", "clear"], sev="green", drive="yes", tags=["fuel-filling"],
  related=["P0449", "P2422"], monitor="evap", emissions=True)
S("P0455", "تسريب كبير في نظام EVAP",
  "The EVAP system cannot hold vacuum at all - often a missing or loose fuel cap, or a disconnected hose.",
  "نظام EVAP لا يحتفظ بالتفريغ إطلاقًا - غالبًا غطاء تانك مفقود أو مفكوك أو خرطوم مفصول.",
  ["gas_cap", "evap_hose", "purge_valve", "vent_valve", "canister"], _evap_checks, sev="green", drive="yes", tags=["smell"],
  related=["P0442", "P0457"], monitor="evap", emissions=True)
S("P0456", "تسريب صغير جدًا في نظام EVAP", "A very small EVAP leak (about 0.5 mm) - often a fuel cap seal or a tiny hose crack.",
  "تسريب صغير جدًا في نظام EVAP (حوالي 0.5 مم) - غالبًا جلدة غطاء التانك أو شرخ دقيق في خرطوم.",
  ["gas_cap", "evap_hose", "vent_valve", "canister"], _evap_checks, sev="green", drive="yes", related=["P0442"], monitor="evap",
  emissions=True)
S("P0457", "تسريب في نظام EVAP (غطاء التانك مفكوك/مفقود)", "The computer thinks the fuel cap is loose or missing.",
  "الكمبيوتر يعتقد أن غطاء التانك مفكوك أو مفقود.", ["gas_cap", "evap_hose"], _evap_checks, sev="green", drive="yes",
  related=["P0455"], monitor="evap", emissions=True)
S("P0496", "تدفق تنقية مرتفع في نظام EVAP",
  "Vapour is drawn into the engine when it should not be - usually a purge valve stuck open (can cause hard starting after refuelling).",
  "يتم سحب الأبخرة إلى المحرك في وقت لا يجب - غالبًا صمام التنقية عالق مفتوحًا (قد يسبب صعوبة التشغيل بعد التمويل).",
  ["purge_valve", "canister"], ["actuator_test", "clear"], sev="green", drive="yes", tags=["hard-start", "rough-idle"],
  related=["P0441"], monitor="evap", emissions=True)
S("P0497", "تدفق تنقية منخفض في نظام EVAP", "Too little vapour flows to the engine during purge.", "كمية قليلة جدًا من الأبخرة تتدفق إلى المحرك أثناء التنقية.",
  ["purge_valve", "evap_hose", "canister"], ["actuator_test", "visual", "clear"], sev="green", drive="yes", related=["P0441"],
  monitor="evap", emissions=True)
S("P2422", "صمام تهوية نظام EVAP عالق مغلقًا",
  "The vent valve stays closed - the tank can build vacuum and refuelling may click off early.",
  "صمام التهوية يبقى مغلقًا - قد يتكون تفريغ في التانك وقد يفصل مسدس التمويل مبكرًا.", ["vent_valve", "canister"],
  ["actuator_test", "clear"], sev="green", drive="yes", tags=["fuel-filling"], related=["P0446"], monitor="evap", emissions=True)
# ------------------------------------------------------------------ idle, brake switch
S("P0504", "عدم توافق مفتاحي الفرامل \"A\"/\"B\"",
  "The brake switch has two signals that must change together; they disagree. Brake lights, cruise control and start-stop "
  "can be affected.",
  "مفتاح الفرامل له إشارتان يجب أن تتغيرا معًا؛ وهما لا تتفقان. قد تتأثر لمبات الفرامل ومثبت السرعة ونظام Start-Stop.",
  [("Faulty or badly adjusted brake light switch", "مفتاح لمبة الفرامل تالف أو مضبوط بشكل سيئ"), ("Burnt brake light bulb (on some cars)", "لمبة فرامل محروقة (في بعض السيارات)"), "conn"],
  [("Check that the brake lights work.", "تأكد أن لمبات الفرامل تعمل."), "live", "clear"], tags=["cruise", "brake-lights"],
  related=["P0571"], safety=True)
S("P0506", "نظام هواء الخامل - اللفات أقل من المتوقع",
  "The idle speed is lower than the target. The engine may shake or stall at traffic lights.",
  "دوران الخامل أقل من المطلوب. قد يرج المحرك أو يطفئ عند الإشارات.",
  ["throttle_dirty", "learn", ("Blocked idle air passage", "مجرى هواء الخامل مسدود"), ("Extra engine load (A/C, alternator)", "حمل زائد على المحرك (تكييف أو دينامو)")],
  [("Clean the throttle body and run the idle/throttle adaptation (Service Functions).", "نظّف بوابة الثروتل وشغّل تعليم الخامل/الثروتل (وظائف الصيانة)."), "live", "clear"],
  tags=["rough-idle", "stalling"], related=["P0505", "P0507"], pids=[0x0C, 0x11])
S("P0507", "نظام هواء الخامل - اللفات أعلى من المتوقع",
  "The idle speed is higher than the target - extra air is getting in.", "دوران الخامل أعلى من المطلوب - يدخل هواء زائد.",
  ["vacuum_leak", "throttle_dirty", "learn", ("Sticking throttle or idle valve", "الثروتل أو صمام الخامل يعلق")],
  ["smoke_test", ("Clean the throttle body and run the idle/throttle adaptation (Service Functions).", "نظّف بوابة الثروتل وشغّل تعليم الخامل/الثروتل (وظائف الصيانة)."), "clear"],
  sev="green", drive="yes", tags=["high-idle"], related=["P0505", "P0506", "P0171"], pids=[0x0C, 0x11])
S(["P0513", "P0633"], "مشكلة في مفتاح/تعليم نظام منع السرقة (Immobilizer)",
  "The engine computer does not accept the key or is not paired with the immobilizer. This is an anti-theft function: RAD "
  "IDE explains the code only. Use the original keys and have an authorized dealer or locksmith check it with proof of ownership.",
  "كمبيوتر المحرك لا يقبل المفتاح أو غير مقترن بنظام منع السرقة. هذه وظيفة حماية من السرقة: RAD IDE يشرح الكود فقط. "
  "استخدم المفاتيح الأصلية واجعل وكيلاً معتمدًا أو فني مفاتيح معتمدًا يفحصها مع إثبات الملكية.",
  [("Key transponder or key battery problem", "مشكلة في شريحة المفتاح أو بطاريته"), ("Antenna ring around the ignition faulty", "حلقة الهوائي حول الكونتاكت تالفة"),
   "low_voltage_event", ("Module replaced without pairing", "تم تغيير وحدة بدون اقتران")],
  [("Try the spare key.", "جرّب المفتاح الاحتياطي."), "battery_test", ("Pairing is done only by an authorized dealer.", "الاقتران يتم فقط عند وكيل معتمد.")],
  sev="amber", drive="caution", tags=["no-start"], related=["U0167"])
S("P0524", "ضغط زيت المحرك منخفض جدًا",
  "The engine oil pressure is too low. Without oil pressure the bearings are destroyed within minutes. Stop the engine "
  "and check the oil level before doing anything else.",
  "ضغط زيت المحرك منخفض جدًا. بدون ضغط زيت تتلف السبائك (الكراسي) خلال دقائق. أطفئ المحرك وافحص مستوى الزيت قبل أي شيء آخر.",
  ["oil_level", ("Oil leak", "تسريب زيت"), "oil_dirty", ("Worn oil pump or engine bearings", "طرمبة زيت أو سبائك محرك متآكلة"),
   ("Faulty oil pressure sensor (only after confirming with a mechanical gauge)", "حساس ضغط الزيت تالف (فقط بعد التأكد بعداد ميكانيكي)")],
  [("Check the oil level on the dipstick with the car on level ground.", "افحص مستوى الزيت بالعصا والسيارة على أرض مستوية."),
   ("Do not drive until a mechanic has measured the real oil pressure with a gauge.", "لا تقُد حتى يقيس الميكانيكي ضغط الزيت الحقيقي بعداد.")],
  sev="red", drive="no", tags=["oil-light", "noise"], related=["P0520", "P0521"], safety=True, pids=[0x0C, 0x5C])
S("P0534", "فقد شحنة غاز التكييف", "The A/C system is low on refrigerant - there is a leak.", "نظام التكييف به نقص في الغاز - يوجد تسريب.",
  [("Refrigerant leak (condenser, hoses, compressor seal)", "تسريب غاز (المكثف أو الخراطيم أو جلدة الكمبروسر)")],
  [("Have the A/C leak-tested before recharging.", "اختبر التكييف للتسريب قبل إعادة الشحن.")], sev="green", drive="yes", tags=["ac"],
  related=["P0530"])
# ------------------------------------------------------------------ system voltage
_volt_checks = ["battery_test", ("Clean and tighten the battery terminals and the engine ground strap.", "نظّف واربط أقطاب البطارية وسير الأرضي للمحرك."),
                ("Check the alternator belt.", "افحص سير الدينامو."), "clear"]
S("P0560", "جهد النظام", "The supply voltage the computer sees is out of range or implausible.", "الجهد الذي يراه الكمبيوتر خارج المدى أو غير منطقي.",
  ["battery", "alternator", "ground_strap"], _volt_checks, tags=["battery", "electrical"], related=["P0562", "P0563"], pids=[0x42])
S("P0561", "جهد النظام غير مستقر", "The supply voltage jumps up and down - often a loose connection or failing alternator.",
  "جهد التغذية يقفز صعودًا وهبوطًا - غالبًا توصيلة مفكوكة أو دينامو بدأ يتلف.", ["ground_strap", "alternator", "battery", "belt"], _volt_checks,
  tags=["battery", "electrical"], related=["P0560"], pids=[0x42])
S(["P0562", "P2503"], "جهد النظام منخفض",
  "The voltage reaching the computer is too low (usually below about 10-11 V). A weak battery or an alternator that does "
  "not charge is typical. Low voltage can trigger many unrelated codes in other modules.",
  "الجهد الواصل للكمبيوتر منخفض جدًا (عادةً أقل من حوالي 10-11 فولت). البطارية الضعيفة أو الدينامو الذي لا يشحن سبب معتاد. "
  "الجهد المنخفض قد يسجل أكوادًا كثيرة غير مرتبطة في وحدات أخرى.",
  ["battery", "alternator", "belt", "ground_strap", ("Battery drain (something stays on when parked)", "سحب للبطارية (شيء يبقى يعمل والسيارة واقفة)")],
  _volt_checks, tags=["battery", "battery-light", "no-start", "electrical"], related=["P0560", "P0563", "P2503"], pids=[0x42])
S(["P0563", "P2504"], "جهد النظام مرتفع",
  "The voltage is too high (above about 15.5-16 V). An overcharging alternator can damage the battery and electronics.",
  "الجهد مرتفع جدًا (أعلى من حوالي 15.5-16 فولت). الدينامو الذي يشحن زيادة قد يتلف البطارية والإلكترونيات.",
  [("Faulty alternator voltage regulator", "منظم جهد الدينامو تالف"), ("Jump-starting with a high-voltage charger", "اشتراك بشاحن عالي الجهد"), "ground_strap"],
  _volt_checks, sev="amber", tags=["battery", "electrical"], related=["P0562", "P2504"], pids=[0x42])
S("P2502", "جهد نظام الشحن", "The charging voltage is not what the computer expects.", "جهد الشحن ليس كما يتوقع الكمبيوتر.",
  ["alternator", "belt", "battery", "ground_strap"], _volt_checks, tags=["battery-light", "battery"], related=["P0562", "P0620"],
  pids=[0x42])
S("P0574", "مثبت السرعة - سرعة السيارة عالية جدًا", "Cruise control was switched off because the speed went above its limit.",
  "تم إلغاء مثبت السرعة لأن السرعة تجاوزت حده.", [("Driving downhill faster than the limit", "النزول من منحدر أسرع من الحد")], ["clear"], sev="green",
  drive="yes", tags=["cruise"])
# ------------------------------------------------------------------ control modules
_ecm_causes = ["low_voltage_event", "ground_strap", "software", ("Water damage in the module", "دخول مياه إلى الوحدة"), "ecu"]
_ecm_checks = ["battery_test", ("Check the module's power and ground connections.", "افحص توصيلات التغذية والأرضي للوحدة."), "tsb", "clear"]
for code_, tar, en, ar in (
        ("P0600", "رابط الاتصال التسلسلي", "Communication between control modules (or inside one) failed.", "فشل الاتصال بين وحدات التحكم (أو داخل وحدة)."),
        ("P0601", "خطأ مجموع التحقق لذاكرة وحدة التحكم", "The module found an error when checking its own program memory.", "الوحدة وجدت خطأً عند فحص ذاكرة برنامجها."),
        ("P0602", "خطأ في برمجة وحدة التحكم", "The module is not programmed or programming did not complete.", "الوحدة غير مبرمجة أو لم تكتمل البرمجة."),
        ("P0603", "خطأ ذاكرة KAM في وحدة التحكم", "The module lost its learned memory - often after the battery was disconnected or a power drop.", "الوحدة فقدت ذاكرتها المتعلَّمة - غالبًا بعد فصل البطارية أو انخفاض التغذية."),
        ("P0604", "خطأ ذاكرة RAM في وحدة التحكم", "The module found an error in its working memory.", "الوحدة وجدت خطأً في ذاكرة العمل."),
        ("P0605", "خطأ ذاكرة ROM في وحدة التحكم", "The module found an error in its read-only memory.", "الوحدة وجدت خطأً في ذاكرة القراءة فقط."),
        ("P0606", "معالج وحدة التحكم", "The module's processor self-test failed.", "فشل الاختبار الذاتي لمعالج الوحدة."),
        ("P0607", "أداء وحدة التحكم", "The module detected an internal performance problem.", "الوحدة اكتشفت مشكلة أداء داخلية."),
        ("P0610", "خطأ في خيارات السيارة بوحدة التحكم", "The module's vehicle configuration does not match the car.", "إعدادات السيارة المخزنة في الوحدة لا تطابق السيارة."),
        ("P0611", "أداء وحدة التحكم في الرشاشات", "The injector driver module reported an internal problem.", "وحدة تشغيل الرشاشات أبلغت عن مشكلة داخلية."),
        ("P0613", "معالج كمبيوتر الفتيس", "The transmission computer's processor self-test failed.", "فشل الاختبار الذاتي لمعالج كمبيوتر الفتيس."),
        ("P0614", "عدم توافق كمبيوتر المحرك وكمبيوتر الفتيس", "The engine and transmission computers do not match (wrong part or software).", "كمبيوتر المحرك وكمبيوتر الفتيس غير متوافقين (قطعة أو برمجة خاطئة)."),
        ("P0630", "رقم الشاسيه (VIN) غير مبرمج أو غير متوافق - كمبيوتر المحرك", "The VIN stored in the engine computer is missing or does not match.", "رقم الشاسيه المخزن في كمبيوتر المحرك مفقود أو غير مطابق."),
        ("P0631", "رقم الشاسيه (VIN) غير مبرمج أو غير متوافق - كمبيوتر الفتيس", "The VIN stored in the transmission computer is missing or does not match.", "رقم الشاسيه المخزن في كمبيوتر الفتيس مفقود أو غير مطابق."),
        ("P2610", "أداء مؤقت إطفاء المحرك الداخلي", "The module's internal timer that measures how long the engine was off is not plausible.", "المؤقت الداخلي الذي يقيس مدة إطفاء المحرك غير منطقي."),
):
    S(code_, tar, en + " Before suspecting the module itself, check battery voltage, grounds and software updates.",
      ar + " قبل الشك في الوحدة نفسها افحص جهد البطارية والأرضي وتحديثات البرمجة.", _ecm_causes, _ecm_checks,
      tags=["no-start", "stalling", "limp-mode"], related=["P0562"])
S("P0634", "حرارة وحدة التحكم الداخلية مرتفعة جدًا", "The inside of the control module is too hot.", "داخل وحدة التحكم ساخن جدًا.",
  [("Module mounted near a heat source / blocked cooling", "الوحدة قريبة من مصدر حرارة / تبريدها مسدود"), "ecu"], ["visual", "clear"],
  related=["P0666"])
S("P0683", "دائرة الاتصال بين وحدة بوجيهات التسخين وكمبيوتر المحرك",
  "The glow plug module and the engine computer cannot talk properly.", "وحدة بوجيهات التسخين وكمبيوتر المحرك لا يتواصلان بشكل سليم.",
  ["glow_module", "conn", "wire_open"], ["visual", "clear"], sev="green", drive="yes", tags=["hard-start"], related=["P0670"])
# ------------------------------------------------------------------ transmission general
S("P0700", "نظام التحكم في الفتيس (طلب إضاءة لمبة المحرك)",
  "The transmission computer has stored its own fault and asked the engine computer to turn on the check-engine light. "
  "This code is only a messenger: scan the transmission module to read the real code.",
  "كمبيوتر الفتيس سجّل عطلاً خاصًا به وطلب من كمبيوتر المحرك إضاءة لمبة المحرك. هذا الكود مجرد رسول: افحص وحدة الفتيس "
  "لقراءة الكود الحقيقي.",
  [("A fault stored in the transmission module", "عطل مسجل في وحدة الفتيس"), "trans_fluid"],
  [("Scan the transmission control module (TCM) for its own codes.", "افحص وحدة التحكم في الفتيس (TCM) لقراءة أكوادها."), "fluid_level"],
  tags=["hard-shift", "limp-mode"], related=["P0715", "P0730", "P0750"])
S("P0701", "نطاق/أداء نظام التحكم في الفتيس", "The transmission control system does not perform as expected.",
  "نظام التحكم في الفتيس لا يعمل كما هو متوقع.", ["trans_fluid", "solenoid", "software"], ["fluid_level", "tsb", "clear"],
  tags=["hard-shift"], related=["P0700"])
S("P0811", "انزلاق زائد في الكلاتش", "The clutch slips: engine speed rises without the car accelerating accordingly.",
  "الكلاتش يفلت: سرعة المحرك ترتفع دون أن تتسارع السيارة بنفس القدر.",
  [("Worn clutch disc", "أسطوانة (ديسك) الكلاتش متآكلة"), ("Oil on the clutch", "زيت على الكلاتش"), ("Clutch actuator adjustment", "ضبط مشغّل الكلاتش")],
  ["live", "clear"], tags=["slipping", "low-power"], related=["P0810"])
S("P0894", "انزلاق مكوّن في الفتيس", "Something inside the gearbox is slipping.", "شيء داخل الفتيس يفلت.",
  ["trans_fluid", "trans_internal", "solenoid"], ["fluid_level", "live", "clear"], tags=["slipping", "hard-shift"], related=["P0730"])
S("P0897", "تدهور زيت الفتيس", "The transmission fluid is worn out or overheated.", "زيت الفتيس منتهي أو تعرض لسخونة زائدة.",
  ["trans_fluid", ("Fluid overheated (towing, slipping)", "الزيت سخن زيادة (جر أحمال أو انزلاق)")],
  [("Change the transmission fluid and filter, then reset the fluid ageing counter if the car has one.", "غيّر زيت وفلتر الفتيس ثم صفّر عداد عمر الزيت إن وُجد.")],
  sev="green", drive="yes", tags=["hard-shift"], related=["P0218"])
S("P2544", "إشارة طلب إدارة العزم \"A\"",
  "Another module (often the transmission) asked the engine to reduce torque and the request was invalid or a fault is stored there.",
  "وحدة أخرى (غالبًا الفتيس) طلبت من المحرك تقليل العزم وكان الطلب غير صالح أو يوجد عطل مسجل هناك.",
  [("Fault stored in the transmission or ABS module", "عطل مسجل في وحدة الفتيس أو ABS"), "can_wiring"], ["modules_online", "clear"],
  tags=["limp-mode"], related=["P0700"])
# ------------------------------------------------------------------ throttle actuator
_tac_causes = ["throttle_dirty", ("Faulty electronic throttle body", "بوابة الثروتل الإلكترونية تالفة"), "pedal", "conn", "learn"]
_tac_checks = [("Compare pedal %, commanded throttle % and actual throttle % in live data.", "قارن نسبة الدواسة والثروتل المطلوب والفعلي في البيانات الحية."),
               ("Clean the throttle body (ignition off) and run the throttle adaptation (Service Functions).", "نظّف بوابة الثروتل (والمفتاح مطفأ) وشغّل تعليم الثروتل (وظائف الصيانة)."), "visual", "clear"]
for code_, tar, en, ar, sev, drive in (
        ("P2104", "نظام الثروتل - خامل إجباري", "The throttle system detected a fault and forced the engine to idle only.", "نظام الثروتل اكتشف عطلاً وأجبر المحرك على الخامل فقط.", "red", "no"),
        ("P2105", "نظام الثروتل - إيقاف المحرك إجباريًا", "The throttle system detected a serious fault and shut the engine down for safety.", "نظام الثروتل اكتشف عطلاً خطيرًا وأوقف المحرك للأمان.", "red", "no"),
        ("P2106", "نظام الثروتل - قدرة محدودة إجباريًا", "The throttle system limits the engine power (limp mode).", "نظام الثروتل يحد من قدرة المحرك (وضع الطوارئ).", "amber", "caution"),
        ("P2107", "معالج وحدة التحكم في الثروتل", "The throttle control processor failed its self-test.", "معالج التحكم في الثروتل فشل في الاختبار الذاتي.", "amber", "caution"),
        ("P2108", "أداء وحدة التحكم في الثروتل", "The throttle control module reported an internal problem.", "وحدة التحكم في الثروتل أبلغت عن مشكلة داخلية.", "amber", "caution"),
        ("P2110", "نظام الثروتل - لفات محدودة إجباريًا", "The throttle system limits the engine speed (limp mode).", "نظام الثروتل يحد من سرعة المحرك (وضع الطوارئ).", "amber", "caution"),
        ("P2111", "نظام الثروتل - عالق مفتوحًا", "The throttle opens more than commanded - it may be sticking.", "الثروتل يفتح أكثر من المطلوب - قد يكون عالقًا.", "red", "no"),
        ("P2112", "نظام الثروتل - عالق مغلقًا", "The throttle does not open as commanded - often carbon or ice.", "الثروتل لا يفتح كما هو مطلوب - غالبًا كربون أو ثلج.", "amber", "caution"),
        ("P2119", "بوابة الثروتل - نطاق/أداء", "The throttle plate does not reach the commanded position in time.", "صمام الثروتل لا يصل إلى الوضع المطلوب في الوقت المناسب.", "amber", "caution")):
    S(code_, tar, en, ar, _tac_causes, _tac_checks, sev=sev, drive=drive, tags=["limp-mode", "low-power", "stalling"],
      related=["P2101", "P2135", "P0121"], safety=(sev == "red"), pids=[0x11, 0x49, 0x4C, 0x45])
for i, pair in enumerate(("A/B", "A/C", "B/C", "D/E", "D/F", "E/F")):
    S(f"P{2135 + i}", f"عدم توافق جهد حساسي وضع الثروتل/الدواسة {pair}",
      f"Throttle and pedal sensors use two signals ({pair}) that must always agree. They disagree, so the computer cannot "
      "trust the throttle or pedal position and usually limits power.",
      f"حساسات الثروتل والدواسة تستخدم إشارتين ({pair}) يجب أن تتفقا دائمًا. هما لا تتفقان، فلا يثق الكمبيوتر بوضع الثروتل "
      "أو الدواسة وغالبًا يحد من القدرة.",
      ["conn", ("Worn throttle body or pedal sensor track", "مسار حساس الثروتل أو الدواسة متآكل"), "pedal", "wire_open", "ref5v"],
      ["wiggle", ("Watch both signals while pressing the pedal slowly: they must move together without jumps.", "راقب الإشارتين أثناء الضغط ببطء على الدواسة: يجب أن تتحركا معًا دون قفزات."), "visual", "clear"],
      tags=["limp-mode", "low-power", "hesitation"], related=["P2138", "P0121", "P2122"], pids=[0x11, 0x49, 0x4A, 0x45])
S("P2162", "عدم توافق حساسي سرعة السيارة \"A\"/\"B\"", "Two speed signals disagree.", "إشارتا السرعة لا تتفقان.",
  ["wheel_sensor", "conn", ("Wrong tyre sizes", "مقاسات إطارات مختلفة")], ["live", "clear"], tags=["speedometer"], related=["P0500"])
# ------------------------------------------------------------------ cooling performance
S("P2181", "أداء نظام التبريد",
  "The engine temperature does not behave as the computer's model expects - it heats too slowly, too fast or runs too "
  "hot or too cold. The thermostat, low coolant, trapped air or the fan are usual causes.",
  "حرارة المحرك لا تتصرف كما يتوقع نموذج الكمبيوتر - تسخن ببطء أو بسرعة زائدة أو تعمل ساخنة أو باردة جدًا. الثرموستات أو نقص "
  "سائل التبريد أو الهواء المحبوس أو المروحة أسباب معتادة.",
  ["thermostat_open", "coolant_low", "air_in_cooling", "fan", "thermostat_closed", ("Faulty coolant temperature sensor", "حساس حرارة المحرك تالف")],
  [("Check the coolant level (engine cold).", "افحص مستوى سائل التبريد (والمحرك بارد)."), ("Watch the coolant temperature graph during warm-up.", "راقب منحنى حرارة المحرك أثناء التسخين."),
   ("After work on the cooling system run the cooling-system bleeding routine (Service Functions).", "بعد العمل على دورة التبريد شغّل روتين تفريغ هواء دورة التبريد (وظائف الصيانة)."), "clear"],
  tags=["overheating", "heater-cold", "fan"], related=["P0128", "P0217", "P0116"], safety=True, pids=[0x05, 0x0F])
S("P2560", "مستوى سائل التبريد منخفض",
  "The coolant level sensor reports low coolant. Low coolant leads to overheating.", "حساس مستوى سائل التبريد يبلغ عن نقص. نقص سائل التبريد يؤدي إلى السخونية.",
  ["coolant_low", ("Faulty level sensor in the reservoir", "حساس المستوى في القربة تالف"), "head_gasket"],
  [("With the engine cold, check and top up the coolant with the correct type.", "والمحرك بارد افحص سائل التبريد وكمّله بالنوع الصحيح."),
   ("Look for leaks; if it keeps dropping, have the system pressure-tested.", "ابحث عن تسريب؛ إذا استمر النقص فاعمل اختبار ضغط للدورة.")],
  sev="amber", drive="caution", tags=["overheating"], related=["P0217", "P2181"], safety=True, pids=[0x05])
# ------------------------------------------------------------------ O2 stuck / post-cat trim / misc
S(["P2195", "P2197", "P2270", "P2272"], "إشارة حساس الأكسجين عالقة على الفقير",
  "The oxygen sensor keeps reporting a lean mixture even when the computer adds fuel. Either the mixture really is lean "
  "(air or exhaust leak, low fuel pressure) or the sensor is lazy.",
  "حساس الأكسجين يستمر في الإبلاغ عن خليط فقير حتى عندما يضيف الكمبيوتر وقودًا. إما أن الخليط فقير فعلاً (تسريب هواء أو عادم، "
  "ضغط وقود منخفض) أو أن الحساس كسول.", ["exhaust_leak", "vacuum_leak", "o2_aging", "fuel_pressure_low"],
  ["live", "fuel_trims", "smoke_test", "clear"], sev="green", drive="yes", tags=["fuel-consumption"], related=["P0171", "P0131"],
  monitor="o2", pids=[0x14, 0x15, 0x06, 0x07], emissions=True)
S(["P2196", "P2198", "P2271", "P2273"], "إشارة حساس الأكسجين عالقة على الغني",
  "The oxygen sensor keeps reporting a rich mixture even when the computer removes fuel.", "حساس الأكسجين يستمر في الإبلاغ عن خليط غني حتى عندما يقلل الكمبيوتر الوقود.",
  ["injector_dirty", "o2_aging", ("Sensor contaminated by oil or coolant", "حساس ملوث بالزيت أو سائل التبريد"), "purge_valve"],
  ["live", "fuel_trims", "clear"], sev="green", drive="yes", tags=["fuel-consumption", "smell"], related=["P0172", "P0132"],
  monitor="o2", pids=[0x14, 0x15, 0x06, 0x07], emissions=True)
S(["P2096", "P2098"], "تصحيح الوقود بعد الدبّة - فقير جدًا", "The sensor after the catalyst keeps asking for a richer mixture.",
  "الحساس بعد الدبّة يستمر في طلب خليط أغنى.", ["exhaust_leak", "o2_aging", "vacuum_leak", "catalyst_worn"], ["live", "fuel_trims", "clear"],
  sev="green", drive="yes", related=["P0171", "P0420"], monitor="o2", pids=[0x14, 0x15], emissions=True)
S(["P2097", "P2099"], "تصحيح الوقود بعد الدبّة - غني جدًا", "The sensor after the catalyst keeps asking for a leaner mixture.",
  "الحساس بعد الدبّة يستمر في طلب خليط أفقر.", ["injector_dirty", "o2_aging", "catalyst_worn"], ["live", "fuel_trims", "clear"],
  sev="green", drive="yes", related=["P0172", "P0420"], monitor="o2", pids=[0x14, 0x15], emissions=True)
S(["P2414", "P2415"], "خطأ في عينة العادم لحساس الأكسجين",
  "The oxygen sensor sees outside air instead of exhaust gas - typically an exhaust leak near the sensor.",
  "حساس الأكسجين يرى هواءً خارجيًا بدلاً من غازات العادم - غالبًا تسريب في الشكمان قرب الحساس.",
  ["exhaust_leak", ("Sensor not tightened / damaged thread", "الحساس غير مربوط جيدًا / سنّه تالف"), "sensor"], ["visual", "clear"],
  sev="green", drive="yes", tags=["noise"], related=["P0171"], monitor="o2", emissions=True)
S("P2199", "عدم توافق حساسي حرارة الهواء 1 و2", "Two intake air temperature readings disagree too much.", "قراءتا حرارة الهواء الداخل مختلفتان أكثر من اللازم.",
  [("One of the two sensors is faulty", "أحد الحساسين تالف"), "conn"], ["compare_sensors", "clear"], sev="green", drive="yes",
  related=["P0110", "P0095"], pids=[0x0F])
S("P2279", "تسريب في نظام سحب الهواء",
  "The computer detects unmetered air entering the intake - an air leak. This makes the engine run lean.",
  "الكمبيوتر يكتشف هواءً غير محسوب يدخل المنفولد - تسريب هواء. هذا يجعل الخليط فقيرًا.",
  ["vacuum_leak", ("Loose intake duct or clamp after the MAF", "مجرى الهواء أو مشبكه مفكوك بعد MAF")], ["smoke_test", "fuel_trims", "clear"],
  tags=["rough-idle", "stalling"], related=["P0171", "P0174"], pids=[0x06, 0x07, 0x10])
S("P2635", "تدفق/أداء طرمبة البنزين \"A\" منخفض", "The fuel pump does not deliver enough fuel.", "طرمبة البنزين لا توصل كمية كافية من الوقود.",
  [("Weak fuel pump", "طرمبة بنزين ضعيفة"), ("Clogged fuel filter or pump strainer", "فلتر الوقود أو شبكة الطرمبة مسدودة"), "battery"],
  [("Check fuel pressure with a gauge.", "افحص ضغط الوقود بعداد."), "clear"], tags=["low-power", "stalling", "no-start"], related=["P0087", "P0171"],
  pids=[0x0A, 0x23])
S(["P3400", "P3497"], "نظام إيقاف الأسطوانات",
  "The system that switches off cylinders to save fuel does not work properly. The engine usually stays on all cylinders; "
  "low oil level or dirty oil are common causes.",
  "النظام الذي يوقف الأسطوانات لتوفير الوقود لا يعمل بشكل سليم. غالبًا يبقى المحرك على كل الأسطوانات؛ نقص الزيت أو اتساخه أسباب شائعة.",
  ["oil_level", "oil_dirty", ("Faulty deactivation solenoid or lifter", "سولينويد الإيقاف أو التاكيه تالف")],
  [("Check oil level and use the specified oil grade.", "افحص مستوى الزيت واستخدم النوع المحدد."), "clear"],
  tags=["misfire", "noise", "fuel-consumption"])


# ------------------------------------------------------------------ added: SCR / AdBlue, water in fuel, DPF ash / pressure
S("P203F", "مستوى سائل التنقية (AdBlue) منخفض جدًا",
  "The AdBlue (diesel exhaust fluid) tank is almost empty. Most cars count down the remaining distance and will not "
  "restart once it reaches zero, so refill soon.",
  "تانك AdBlue (سائل عادم الديزل) شبه فارغ. أغلب العربيات تعد تنازليًا المسافة المتبقية ولا تدور مرة أخرى عندما تصل "
  "للصفر، لذلك املأه قريبًا.",
  [("AdBlue tank simply needs refilling", "تانك AdBlue يحتاج ملء فقط"), ("Faulty AdBlue level sensor", "حساس مستوى AdBlue تالف"),
   ("Leak in the AdBlue lines", "تسريب في خطوط AdBlue")],
  [("Refill with ISO 22241 AdBlue / DEF and drive a few minutes; the warning should go out.",
    "املأ بسائل AdBlue / DEF مطابق لمواصفة ISO 22241 وقُد بضع دقائق؛ يجب أن ينطفئ التحذير."),
   ("If it stays on after filling, check the level sensor reading and look for white crystals at leaks.",
    "لو فضل منورًا بعد الملء افحص قراءة حساس المستوى وابحث عن تبلور أبيض عند أماكن التسريب."), "clear"],
  sev="amber", drive="caution", tags=["limp-mode"], related=["P204F", "P20EE"], monitor="nox", emissions=True)
S("P204F", "أداء نظام سائل التنقية (AdBlue)",
  "The AdBlue system does not reach the pressure or dosing the computer expects.",
  "نظام AdBlue لا يصل للضغط أو كمية الحقن التي يتوقعها الكمبيوتر.",
  [("Crystallised or blocked AdBlue injector", "رشاش AdBlue متبلور أو مسدود"), ("Weak AdBlue pump or blocked filter", "طلمبة AdBlue ضعيفة أو فلتر مسدود"),
   ("Frozen or contaminated fluid", "سائل متجمد أو ملوث"), ("Leaking line", "خط يسرب")],
  ["live", ("Check the AdBlue quality and look for crystals at the injector and lines.", "افحص جودة AdBlue وابحث عن تبلور عند الرشاش والخطوط."), "clear"],
  sev="amber", drive="caution", tags=["limp-mode"], related=["P203F", "P20EE", "P2047"], monitor="nox", emissions=True)
S("P20EE", "كفاءة دبّة SCR لأكاسيد النيتروجين أقل من الحد",
  "The NOx sensors show that the SCR catalyst removes less NOx than it should. The AdBlue dosing or quality is the most "
  "common reason, less often a worn catalyst or a faulty NOx sensor.",
  "حساسات NOx تبين أن دبّة SCR تزيل أكاسيد نيتروجين أقل من المطلوب. السبب الأشهر حقن AdBlue أو جودته، وأقل من ذلك دبّة "
  "متآكلة أو حساس NOx تالف.",
  [("Poor quality or diluted AdBlue", "سائل AdBlue رديء أو مخفف"), ("Blocked or crystallised AdBlue injector", "رشاش AdBlue مسدود أو متبلور"),
   ("Faulty NOx sensor", "حساس NOx تالف"), ("Exhaust leak before the SCR catalyst", "تسريب عادم قبل دبّة SCR"), ("Aged SCR catalyst", "دبّة SCR قديمة")],
  ["live", ("Compare the NOx readings before and after the SCR catalyst in live data with the engine warm.",
            "قارن قراءات NOx قبل وبعد دبّة SCR في البيانات الحية والمحرك ساخن."), "clear"],
  sev="amber", drive="caution", tags=["limp-mode"], related=["P204F", "P203F", "P2047"], monitor="nox", emissions=True)
S("P2269", "حالة وجود مياه في الوقود",
  "The fuel filter's water separator is full. Water in diesel damages the high-pressure pump and the injectors, so drain "
  "it soon.",
  "فاصل المياه في فلتر السولار ممتلئ. المياه في السولار تتلف طلمبة الضغط العالي والرشاشات، لذلك صفّها قريبًا.",
  [("Water collected in the fuel filter (normal over time)", "تجمع مياه في فلتر السولار (طبيعي مع الوقت)"), ("Contaminated fuel from a filling station", "وقود ملوث من محطة البنزين"),
   ("Faulty water-in-fuel sensor", "حساس المياه في الوقود تالف")],
  [("Drain the water from the fuel filter (see the owner's manual) or replace the filter.", "صفِّ المياه من فلتر السولار (راجع كتيب العربية) أو غيّر الفلتر."),
   ("If it comes back quickly, suspect the fuel source or a leaking tank seal.", "لو رجعت بسرعة اشتبه في مصدر الوقود أو جلدة تانك تسرب."), "clear"],
  sev="amber", drive="caution", tags=["rough-idle", "low-power"], related=["P2264", "P2265"], pids=[0x0C])
S("P242F", "انسداد فلتر الجزيئات - تراكم الرماد",
  "Ash (from engine oil additives) builds up in the particulate filter and, unlike soot, cannot be burnt off. After a high "
  "mileage the filter needs professional cleaning or replacement; regeneration does not help.",
  "الرماد (من إضافات زيت المحرك) يتراكم في فلتر الجزيئات ولا يحترق مثل السناج. بعد مسافة كبيرة يحتاج الفلتر تنظيفًا "
  "احترافيًا أو تغييرًا؛ التجديد لا يفيد.",
  ["dpf_ash", ("Engine burning oil (raises ash)", "المحرك يحرق زيت (يزوّد الرماد)"), ("Wrong engine oil (not low-SAPS)", "زيت محرك غير مناسب (ليس low-SAPS)"), "dpf_lines"],
  [("Read the ash load / distance since the last DPF replacement in live data if the car offers it.", "اقرأ نسبة الرماد / المسافة منذ آخر تغيير للفلتر في البيانات الحية لو متاحة."),
   ("Check oil consumption and that the oil meets the manufacturer's specification.", "افحص استهلاك الزيت وأن الزيت مطابق لمواصفة الشركة."), "clear"],
  tags=["limp-mode", "low-power"], related=["P2463", "P2002"], monitor="pm", emissions=True, pids=[0x7A, 0x7B])
S(["P244A"], "فرق ضغط فلتر الجزيئات منخفض جدًا",
  "The pressure difference across the particulate filter is lower than possible for a working filter: the filter may be "
  "cracked or removed, or the pressure sensor lines are off or leaking.",
  "فرق الضغط على فلتر الجزيئات أقل مما يمكن لفلتر سليم: قد يكون الفلتر مشروخًا، أو خراطيم حساس الضغط مفصولة أو تسرب.",
  ["dpf_lines", ("Cracked filter element", "عنصر الفلتر مشروخ"), ("Faulty DPF pressure sensor", "حساس ضغط الفلتر تالف"), ("Exhaust leak before the filter", "تسريب عادم قبل الفلتر")],
  [("Check both pressure-sensor hoses for splits, disconnection and the right orientation.", "افحص خرطومي حساس الضغط بحثًا عن شروخ أو فصل وتأكد من الاتجاه الصحيح."),
   "live", "clear"],
  tags=["smoke"], related=["P244B", "P2452", "P2002"], monitor="pm", emissions=True, pids=[0x7A])
S(["P244B"], "فرق ضغط فلتر الجزيئات مرتفع جدًا",
  "The pressure difference across the particulate filter is too high: it is heavily loaded with soot or ash, or the "
  "sensor reading is wrong.",
  "فرق الضغط على فلتر الجزيئات مرتفع جدًا: الفلتر ممتلئ بالسناج أو الرماد، أو قراءة الحساس خاطئة.",
  ["dpf_soot", "dpf_ash", "dpf_lines", ("Faulty DPF pressure sensor", "حساس ضغط الفلتر تالف")],
  [("Read the soot load and differential pressure in live data.", "اقرأ نسبة السناج وفرق الضغط في البيانات الحية."),
   ("If the soot load allows it, run a service regeneration (Service Functions) after finding why it loaded up.", "لو نسبة السناج تسمح، شغّل تجديدًا خدميًا (وظائف الصيانة) بعد معرفة سبب الامتلاء."),
   "clear"],
  tags=["limp-mode", "low-power", "smoke"], related=["P2463", "P244A", "P2452"], monitor="pm", emissions=True, pids=[0x7A, 0x7B])
