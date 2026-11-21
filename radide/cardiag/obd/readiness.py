"""Readiness monitors (mode 01 PID 01 "since DTCs cleared" and PID 41 "this drive cycle").

A monitor is a self-test the engine computer runs on an emissions system.  After codes are cleared (or the
battery was disconnected) every monitor goes back to "incomplete" until the car has been driven in the
conditions that test needs.  The explanations below (English + Arabic) are original text written for RAD IDE.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Monitor:
    key: str
    name: str
    supported: bool
    complete: bool
    continuous: bool = False


@dataclass
class MonitorStatus:
    mil: bool = False
    dtc_count: int = 0
    diesel: bool = False
    monitors: list = field(default_factory=list)

    def incomplete(self) -> list:
        return [m for m in self.monitors if m.supported and not m.complete and not m.continuous]

    def supported(self) -> list:
        return [m for m in self.monitors if m.supported]


CONTINUOUS = (("misfire", "Misfire"), ("fuel", "Fuel system"), ("components", "Comprehensive components"))
SPARK = ("catalyst", "heated_catalyst", "evap", "secondary_air", "ac_refrigerant", "o2_sensor", "o2_heater", "egr")
DIESEL = ("nmhc_catalyst", "nox_scr", None, "boost", None, "exhaust_sensor", "pm_filter", "egr")
NAMES = {"catalyst": "Catalyst", "heated_catalyst": "Heated catalyst", "evap": "Evaporative system",
         "secondary_air": "Secondary air system", "ac_refrigerant": "A/C refrigerant",
         "o2_sensor": "Oxygen sensor", "o2_heater": "Oxygen sensor heater", "egr": "EGR / VVT system",
         "nmhc_catalyst": "NMHC catalyst", "nox_scr": "NOx / SCR aftertreatment", "boost": "Boost pressure",
         "exhaust_sensor": "Exhaust gas sensor", "pm_filter": "PM filter (DPF)",
         "misfire": "Misfire", "fuel": "Fuel system", "components": "Comprehensive components"}


def decode_status(d: bytes) -> MonitorStatus:
    """4 data bytes A B C D of PID 01 (or 41) -> MonitorStatus."""
    a, b, c, dd = (list(d) + [0, 0, 0, 0])[:4]
    st = MonitorStatus(mil=bool(a & 0x80), dtc_count=a & 0x7F, diesel=bool(b & 0x08))
    for i, (key, name) in enumerate(CONTINUOUS):
        st.monitors.append(Monitor(key, name, bool(b & (1 << i)), not (b & (1 << (i + 4))), True))
    for i, key in enumerate(DIESEL if st.diesel else SPARK):
        if key is None:
            continue
        st.monitors.append(Monitor(key, NAMES[key], bool(c & (1 << i)), not (dd & (1 << i))))
    return st


def encode_status(mil: bool, dtc_count: int, diesel: bool, supported: dict, complete: dict) -> bytes:
    """Inverse of decode_status (used by the demo vehicle): supported / complete map monitor key -> bool."""
    a = (0x80 if mil else 0) | (dtc_count & 0x7F)
    b = 0x08 if diesel else 0
    for i, (key, _n) in enumerate(CONTINUOUS):
        if supported.get(key):
            b |= 1 << i
            if not complete.get(key, True):
                b |= 1 << (i + 4)
    c = dd = 0
    for i, key in enumerate(DIESEL if diesel else SPARK):
        if key and supported.get(key):
            c |= 1 << i
            if not complete.get(key, False):
                dd |= 1 << i
    return bytes([a, b, c, dd])


# key -> (English, Arabic): what the monitor checks, and the driving that completes it
EXPLAIN = {
    "misfire": (
        "Watches crankshaft speed for the small slow-downs a cylinder causes when it does not fire. "
        "Runs all the time while the engine is running; it is normally complete within a short drive.",
        "يراقب سرعة عمود الكرنك ليلتقط التباطؤ الصغير الذي يحدث عندما لا يشتعل أحد السلندرات. "
        "يعمل باستمرار والمحرك دائر، وعادة يكتمل خلال مشوار قصير."),
    "fuel": (
        "Checks that the fuel trims stay within limits, i.e. the computer can keep the mixture right. "
        "Continuous; completes after the engine reaches closed loop on a normal drive.",
        "يتأكد أن تصحيحات الوقود (Fuel trim) داخل الحدود، أي أن الكمبيوتر قادر على ضبط الخليط. "
        "يعمل باستمرار، ويكتمل بعد أن يدخل المحرك وضع الـ closed loop في مشوار عادي."),
    "components": (
        "Checks sensors and actuators for open / short circuits and implausible readings. Continuous.",
        "يفحص الحساسات والمشغّلات (actuators) بحثاً عن قطع أو قصر في الدائرة أو قراءات غير منطقية. يعمل باستمرار."),
    "catalyst": (
        "Compares the oxygen sensors before and after the catalytic converter to judge how well it stores "
        "oxygen. Needs a fully warm engine and several minutes of steady cruising (about 60-90 km/h), "
        "usually over one or two drive cycles.",
        "يقارن حساسي الأكسجين قبل وبعد علبة البيئة (الكتلايزر) ليحكم على قدرتها على تخزين الأكسجين. "
        "يحتاج محركاً ساخناً تماماً وعدة دقائق من السير بسرعة ثابتة (حوالي 60-90 كم/س)، وغالباً على مشوار أو اثنين."),
    "heated_catalyst": (
        "Tests the heater of an electrically heated catalyst (rare). Needs a cold start followed by a normal drive.",
        "يختبر سخّان علبة البيئة المسخّنة كهربائياً (نادرة). يحتاج تشغيلاً على البارد ثم مشواراً عادياً."),
    "evap": (
        "Checks the fuel-vapour system (tank, charcoal canister, purge and vent valves) for leaks. It is the "
        "slowest monitor: it usually needs a cold start after the car stood for 8 hours or more, a fuel "
        "level between about 15% and 85%, and an ambient temperature that is not extreme. A loose fuel cap "
        "is a common reason it fails.",
        "يفحص نظام أبخرة البنزين (التانك، علبة الفحم، صمامات السحب والتهوية) بحثاً عن تسريب. هو أبطأ اختبار: "
        "غالباً يحتاج تشغيلاً على البارد بعد وقوف العربية 8 ساعات أو أكثر، ومستوى بنزين بين حوالي 15% و85%، "
        "وجو غير متطرف. غطاء التانك غير المحكم سبب شائع لفشله."),
    "secondary_air": (
        "Checks the air pump that blows air into the exhaust right after a cold start. Needs a cold start.",
        "يفحص طلمبة الهواء التي تنفخ هواءً في الشكمان بعد التشغيل على البارد مباشرة. يحتاج تشغيلاً على البارد."),
    "ac_refrigerant": (
        "Old monitor for A/C refrigerant (no longer used on modern cars).",
        "اختبار قديم لغاز التكييف (لم يعد مستخدماً في العربيات الحديثة)."),
    "o2_sensor": (
        "Checks the response speed and voltage range of the oxygen sensors. Needs a warm engine, a period of "
        "steady speed and a deceleration with the throttle closed.",
        "يفحص سرعة استجابة حساسات الأكسجين ومدى الجهد بتاعها. يحتاج محركاً ساخناً وفترة سرعة ثابتة ثم تهدئة "
        "مع رفع القدم عن البنزين."),
    "o2_heater": (
        "Checks the heaters inside the oxygen sensors. Usually completes within the first minutes after a start.",
        "يفحص السخّانات داخل حساسات الأكسجين. يكتمل غالباً خلال الدقائق الأولى بعد التشغيل."),
    "egr": (
        "Checks exhaust gas recirculation (and on some cars variable valve timing): that the commanded flow "
        "really happens. Needs a warm engine and decelerations / steady cruising at moderate speed.",
        "يفحص إعادة تدوير غازات العادم EGR (وفي بعض العربيات توقيت الصبابات المتغير VVT): أن التدفق المطلوب "
        "يحدث فعلاً. يحتاج محركاً ساخناً وتهدئات أو سيراً ثابتاً بسرعة متوسطة."),
    "nmhc_catalyst": (
        "Diesel: checks the oxidation catalyst that burns hydrocarbons. Needs a warm engine and a steady drive "
        "at moderate to high load.",
        "ديزل: يفحص الكتلايزر المؤكسد الذي يحرق الهيدروكربونات. يحتاج محركاً ساخناً ومشواراً ثابتاً بحمل متوسط إلى عالٍ."),
    "nox_scr": (
        "Diesel: checks the NOx after-treatment (SCR with AdBlue / DEF, or a NOx trap). Needs a long warm "
        "drive so the exhaust gets hot enough.",
        "ديزل: يفحص معالجة أكاسيد النيتروجين (SCR مع AdBlue / DEF أو مصيدة NOx). يحتاج مشواراً طويلاً ساخناً "
        "حتى يسخن العادم بما يكفي."),
    "boost": (
        "Diesel / turbo: checks that the boost pressure follows what the computer asks for. Needs accelerations "
        "under load.",
        "ديزل / تيربو: يتأكد أن ضغط التيربو يتبع ما يطلبه الكمبيوتر. يحتاج تسارعات تحت حمل."),
    "exhaust_sensor": (
        "Diesel: checks the exhaust gas sensors (oxygen / NOx sensors). Needs a warm engine and a steady drive.",
        "ديزل: يفحص حساسات غازات العادم (أكسجين / NOx). يحتاج محركاً ساخناً ومشواراً ثابتاً."),
    "pm_filter": (
        "Diesel: checks the particulate filter (DPF) and its pressure sensor. Needs a long drive at steady "
        "speed (often motorway); a regeneration may be part of the test.",
        "ديزل: يفحص فلتر الجزيئات (DPF) وحساس الضغط بتاعه. يحتاج مشواراً طويلاً بسرعة ثابتة (غالباً طريق سريع)، "
        "وقد يكون الحرق (regeneration) جزءاً من الاختبار."),
}

DRIVE_CYCLE = (
    "A generic drive cycle that completes most monitors (the car's service information has the exact one): "
    "1) cold start after standing overnight, idle 2-3 minutes with lights and A/C on; "
    "2) accelerate gently to 90 km/h and hold a steady speed for 3-5 minutes; "
    "3) slow down to about 30 km/h without braking hard and without touching the clutch; "
    "4) accelerate again and cruise at 70-90 km/h for 5 minutes; "
    "5) stop and idle for 2 minutes. Keep the fuel tank between a quarter and three quarters full. "
    "Never do this in a way that breaks traffic rules - drive normally on a suitable road.",
    "دورة قيادة عامة تُكمل أغلب الاختبارات (الدورة الدقيقة في معلومات الصيانة الخاصة بالعربية): "
    "1) تشغيل على البارد بعد وقوف طول الليل، وسيبها دايرة 2-3 دقايق والنور والتكييف شغالين؛ "
    "2) زوّد السرعة بهدوء لحد 90 كم/س واثبت عليها 3-5 دقايق؛ "
    "3) هدّي لحد حوالي 30 كم/س من غير فرملة قوية ومن غير ما تدوس الدبرياج؛ "
    "4) زوّد تاني واثبت على 70-90 كم/س لمدة 5 دقايق؛ "
    "5) اقف وسيبها دايرة دقيقتين. خلي البنزين بين الربع والثلاث أرباع. "
    "ولا تعمل ده بطريقة تخالف قواعد المرور - سوق عادي على طريق مناسب.")

INSPECTION = (
    "Many inspection programmes accept a car only when the readiness monitors are complete (often one "
    "incomplete monitor is tolerated for newer petrol cars, sometimes two for older ones). Clearing codes "
    "right before an inspection therefore makes the car fail - it does not hide anything.",
    "كثير من برامج الفحص الفني لا تقبل العربية إلا لو اختبارات الجاهزية مكتملة (غالباً يُسمح باختبار واحد غير "
    "مكتمل للعربيات البنزين الأحدث، وأحياناً اثنين للأقدم). لذلك مسح الأعطال قبل الفحص مباشرة يجعل العربية "
    "ترسب - لا يُخفي شيئاً.")


def explain(key: str, arabic: bool = False) -> str:
    t = EXPLAIN.get(key)
    if not t:
        return ""
    return t[1] if arabic else t[0]
