"""UDS (ISO 14229-1) / KWP2000 negative response codes, explained in English and Arabic with what the user
can do about them. The names are the standard's; the explanations are RAD IDE's own words."""
from __future__ import annotations

from .text import BiText

# code: (standard name, explanation EN, explanation AR, what to do EN, what to do AR)
NRC: dict[int, tuple[str, str, str, str, str]] = {
    0x10: ("generalReject", "The control unit rejected the request without a specific reason.",
           "رفضت وحدة التحكم الطلب بدون سبب محدد.",
           "Check the definition and try again; some units answer this way when the function is not available.",
           "راجع التعريف وأعد المحاولة؛ بعض الوحدات ترد هكذا عندما لا تتوفر الوظيفة."),
    0x11: ("serviceNotSupported", "This control unit does not support the requested service.",
           "وحدة التحكم هذه لا تدعم الخدمة المطلوبة.",
           "The function may live in another control unit, or the unit uses KWP2000 instead of UDS.",
           "قد تكون الوظيفة في وحدة تحكم أخرى، أو أن الوحدة تستخدم KWP2000 بدل UDS."),
    0x12: ("subFunctionNotSupported", "The service exists but this sub-function is not supported.",
           "الخدمة موجودة لكن هذه الوظيفة الفرعية غير مدعومة.",
           "Check the sub-function byte in the definition (start / stop / results).",
           "راجع بايت الوظيفة الفرعية في التعريف (بدء / إيقاف / نتائج)."),
    0x13: ("incorrectMessageLengthOrInvalidFormat", "The request has the wrong length or format.",
           "طول الطلب أو صيغته غير صحيحة.",
           "Check the parameters of the routine / identifier in the definition pack.",
           "راجع معاملات الروتين أو المعرّف في حزمة التعريفات."),
    0x14: ("responseTooLong", "The answer would be longer than the transport allows.",
           "الرد أطول مما يسمح به النقل.",
           "Use an adapter / protocol that supports longer frames.", "استخدم محولًا أو بروتوكولًا يدعم إطارات أطول."),
    0x21: ("busyRepeatRequest", "The control unit is busy. Repeat the request in a moment.",
           "وحدة التحكم مشغولة. أعد الطلب بعد لحظة.", "Wait a few seconds and try again.",
           "انتظر بضع ثوانٍ ثم أعد المحاولة."),
    0x22: ("conditionsNotCorrect", "The vehicle conditions for this function are not met.",
           "شروط السيارة اللازمة لهذه الوظيفة غير متحققة.",
           "Go through the preconditions again (engine state, temperature, speed, gear, battery voltage).",
           "راجع الشروط المسبقة مرة أخرى (حالة المحرك، درجة الحرارة، السرعة، ناقل الحركة، جهد البطارية)."),
    0x24: ("requestSequenceError", "The request came in the wrong order.",
           "جاء الطلب بترتيب خاطئ.",
           "Start the routine before asking for its results, or restart the function.",
           "ابدأ الروتين قبل طلب نتائجه، أو أعد تشغيل الوظيفة."),
    0x25: ("noResponseFromSubnetComponent", "A component behind this unit did not answer.",
           "مكوّن خلف هذه الوحدة لم يرد.",
           "Check the wiring / power of the component the function controls.",
           "افحص توصيلات وتغذية المكوّن الذي تتحكم فيه الوظيفة."),
    0x26: ("failurePreventsExecutionOfRequestedAction", "A stored fault prevents this function.",
           "عطل مخزن يمنع تنفيذ هذه الوظيفة.",
           "Read the fault memory, repair the cause, then try again.",
           "اقرأ ذاكرة الأعطال وأصلح السبب ثم أعد المحاولة."),
    0x31: ("requestOutOfRange", "The identifier or a parameter is not valid for this control unit.",
           "المعرّف أو أحد المعاملات غير صالح لوحدة التحكم هذه.",
           "The definition may be for another model / software version.",
           "قد يكون التعريف لموديل أو إصدار برنامج آخر."),
    0x33: ("securityAccessDenied", "This function needs security access first.",
           "هذه الوظيفة تحتاج إلى وصول أمني (Security Access) أولًا.",
           "Select a seed/key plug-in you are licensed to use for this control unit.",
           "اختر إضافة seed/key مرخّصًا لك باستخدامها لهذه الوحدة."),
    0x35: ("invalidKey", "The security key was not accepted.", "لم يُقبل المفتاح الأمني.",
           "Check that the plug-in matches this control unit and security level.",
           "تأكد أن الإضافة تناسب وحدة التحكم ومستوى الأمان هذا."),
    0x36: ("exceededNumberOfAttempts", "Too many wrong security keys.", "محاولات مفتاح أمني خاطئة كثيرة.",
           "Wait for the delay time (often 10 minutes, ignition on) before trying again.",
           "انتظر مدة التأخير (غالبًا 10 دقائق والإشعال يعمل) قبل المحاولة مرة أخرى."),
    0x37: ("requiredTimeDelayNotExpired", "The security delay time has not expired yet.",
           "لم تنتهِ مدة التأخير الأمني بعد.", "Leave the ignition on and wait, then try again.",
           "اترك الإشعال يعمل وانتظر ثم أعد المحاولة."),
    0x70: ("uploadDownloadNotAccepted", "Upload / download not accepted.", "لم يُقبل الرفع / التنزيل.",
           "Not used by service functions.", "غير مستخدم في وظائف الخدمة."),
    0x72: ("generalProgrammingFailure", "The control unit could not write the value to its memory.",
           "لم تستطع وحدة التحكم كتابة القيمة في ذاكرتها.",
           "Check the battery voltage and try again; do not switch the ignition off.",
           "افحص جهد البطارية وأعد المحاولة؛ لا تطفئ الإشعال."),
    0x78: ("requestCorrectlyReceived-ResponsePending", "The control unit is still working on the request.",
           "وحدة التحكم ما زالت تعالج الطلب.", "Wait.", "انتظر."),
    0x7E: ("subFunctionNotSupportedInActiveSession", "Not available in the current diagnostic session.",
           "غير متاحة في جلسة التشخيص الحالية.",
           "The definition must ask for the right session (often the extended session 0x03).",
           "يجب أن يطلب التعريف الجلسة الصحيحة (غالبًا الجلسة الموسعة 0x03)."),
    0x7F: ("serviceNotSupportedInActiveSession", "This service is not available in the current session.",
           "هذه الخدمة غير متاحة في الجلسة الحالية.",
           "The definition must ask for the right session (often the extended session 0x03).",
           "يجب أن يطلب التعريف الجلسة الصحيحة (غالبًا الجلسة الموسعة 0x03)."),
    0x81: ("rpmTooHigh", "Engine speed is too high.", "سرعة المحرك عالية جدًا.",
           "Let the engine idle.", "اترك المحرك على السرعة البطيئة (الرالنتي)."),
    0x82: ("rpmTooLow", "Engine speed is too low (or the engine is off).", "سرعة المحرك منخفضة جدًا (أو المحرك متوقف).",
           "Start the engine if the function needs it running.", "شغّل المحرك إذا كانت الوظيفة تحتاجه دائرًا."),
    0x83: ("engineIsRunning", "The engine must be off for this function.", "يجب أن يكون المحرك متوقفًا لهذه الوظيفة.",
           "Switch the engine off, ignition on.", "أطفئ المحرك واترك الإشعال يعمل."),
    0x84: ("engineIsNotRunning", "The engine must be running for this function.", "يجب أن يكون المحرك دائرًا لهذه الوظيفة.",
           "Start the engine.", "شغّل المحرك."),
    0x85: ("engineRunTimeTooLow", "The engine has not run long enough.", "لم يعمل المحرك مدة كافية.",
           "Let the engine run and try again.", "اترك المحرك يعمل ثم أعد المحاولة."),
    0x86: ("temperatureTooHigh", "A temperature is too high for this function.", "درجة الحرارة عالية جدًا لهذه الوظيفة.",
           "Let the engine / component cool down.", "اترك المحرك أو المكوّن يبرد."),
    0x87: ("temperatureTooLow", "A temperature is too low for this function.", "درجة الحرارة منخفضة جدًا لهذه الوظيفة.",
           "Warm the engine up to operating temperature.", "سخّن المحرك حتى درجة حرارة التشغيل."),
    0x88: ("vehicleSpeedTooHigh", "The vehicle is moving too fast.", "سرعة السيارة عالية جدًا.",
           "Stop the vehicle.", "أوقف السيارة."),
    0x89: ("vehicleSpeedTooLow", "The vehicle speed is too low.", "سرعة السيارة منخفضة جدًا.",
           "Follow the drive instructions of the function.", "اتبع تعليمات القيادة الخاصة بالوظيفة."),
    0x8A: ("throttle/PedalTooHigh", "The accelerator pedal is pressed too far.", "دواسة الوقود مضغوطة أكثر من اللازم.",
           "Release the accelerator pedal.", "ارفع قدمك عن دواسة الوقود."),
    0x8B: ("throttle/PedalTooLow", "The accelerator pedal must be pressed further.", "يجب الضغط على دواسة الوقود أكثر.",
           "Follow the instructions of the function.", "اتبع تعليمات الوظيفة."),
    0x8C: ("transmissionRangeNotInNeutral", "The gearbox must be in neutral.", "يجب أن يكون ناقل الحركة على الوضع المحايد (N).",
           "Put the gearbox in neutral.", "ضع ناقل الحركة على N."),
    0x8D: ("transmissionRangeNotInGear", "The gearbox must be in gear.", "يجب أن يكون ناقل الحركة معشّقًا.",
           "Follow the instructions of the function.", "اتبع تعليمات الوظيفة."),
    0x8F: ("brakeSwitch(es)NotClosed", "The brake pedal must be pressed.", "يجب الضغط على دواسة الفرامل.",
           "Press and hold the brake pedal.", "اضغط على دواسة الفرامل واستمر."),
    0x90: ("shifterLeverNotInPark", "The selector lever must be in P.", "يجب أن يكون ذراع ناقل الحركة على P.",
           "Put the selector lever in P.", "ضع ذراع ناقل الحركة على P."),
    0x91: ("torqueConverterClutchLocked", "The torque converter clutch is locked.", "قابض محول العزم مقفل.",
           "Let the engine idle in P / N.", "اترك المحرك على الرالنتي في P أو N."),
    0x92: ("voltageTooHigh", "The supply voltage is too high.", "جهد التغذية عالٍ جدًا.",
           "Check the charger / alternator.", "افحص الشاحن أو الدينامو."),
    0x93: ("voltageTooLow", "The battery voltage is too low.", "جهد البطارية منخفض جدًا.",
           "Connect a battery support charger and try again.", "وصّل شاحنًا داعمًا للبطارية وأعد المحاولة."),
}

KWP_EXTRA = {0x23: ("routineNotComplete (KWP2000)", "The routine has not finished yet.", "لم ينتهِ الروتين بعد.",
                    "Wait and ask for the results again.", "انتظر واطلب النتائج مرة أخرى.")}


def nrc_name(code: int) -> str:
    row = NRC.get(code) or KWP_EXTRA.get(code)
    if row:
        return row[0]
    if 0x38 <= code <= 0x4F:
        return "reservedByExtendedDataLinkSecurityDocument"
    if 0x94 <= code <= 0xFE:
        return "vehicleManufacturerSpecificConditionsNotCorrect"
    return "unknown"


def explain(code: int) -> BiText:
    """'0x22 conditionsNotCorrect: <explanation> <what to do>' in English and Arabic."""
    row = NRC.get(code) or KWP_EXTRA.get(code)
    if row is None:
        if 0x94 <= code <= 0xFE:
            row = (nrc_name(code), "A manufacturer-specific condition is not met.",
                   "شرط خاص بالشركة المصنّعة غير متحقق.",
                   "See the manufacturer's service information for this function.",
                   "راجع معلومات الخدمة من الشركة المصنّعة لهذه الوظيفة.")
        else:
            row = (nrc_name(code), "The control unit answered with an unknown negative response.",
                   "ردّت وحدة التحكم برد سلبي غير معروف.", "Check the definition.", "راجع التعريف.")
    head = f"NRC 0x{code:02X} {row[0]}: "
    return BiText(head + row[1] + " " + row[3], head + row[2] + " " + row[4])
