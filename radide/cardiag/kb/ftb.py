"""Failure-type byte (the 3rd byte of a UDS DTC, e.g. C0035-1F): what kind of failure the unit detected.

The category numbers follow the standard failure-type list used with UDS DTCs (SAE J2012 / ISO 15031-6 style);
the Arabic wording is RAD IDE's own."""
from __future__ import annotations

CATEGORIES = {
    0x0: ("General failure information", "معلومات عامة عن العطل"),
    0x1: ("General electrical failure", "عطل كهربائي عام"),
    0x2: ("General signal failure", "عطل عام في الإشارة"),
    0x3: ("Frequency / PWM signal failure", "عطل في إشارة التردد / PWM"),
    0x4: ("Control-unit internal failure", "عطل داخلي في وحدة التحكم"),
    0x5: ("Programming / configuration failure", "عطل في البرمجة / الإعداد"),
    0x6: ("Algorithm-based failure", "عطل مكتشف بالحساب (منطقي)"),
    0x7: ("Mechanical failure", "عطل ميكانيكي"),
    0x8: ("Bus signal / message failure", "عطل في رسائل الشبكة"),
    0x9: ("Component failure", "عطل في القطعة نفسها"),
}

FTB = {
    0x00: ("No sub-type information", "لا توجد معلومات تفصيلية"),
    0x01: ("General electrical failure", "عطل كهربائي عام"),
    0x02: ("General signal failure", "عطل عام في الإشارة"),
    0x04: ("System internal failure", "عطل داخلي في النظام"),
    0x11: ("Circuit short to ground", "قصر (شورت) في الدائرة مع الأرضي"),
    0x12: ("Circuit short to battery", "قصر (شورت) في الدائرة مع موجب البطارية"),
    0x13: ("Circuit open", "الدائرة مفتوحة (سلك مقطوع أو فيشة مفصولة)"),
    0x14: ("Circuit short to ground or open", "قصر مع الأرضي أو دائرة مفتوحة"),
    0x15: ("Circuit short to battery or open", "قصر مع موجب البطارية أو دائرة مفتوحة"),
    0x16: ("Circuit voltage below threshold", "جهد الدائرة أقل من الحد"),
    0x17: ("Circuit voltage above threshold", "جهد الدائرة أعلى من الحد"),
    0x18: ("Circuit current below threshold", "تيار الدائرة أقل من الحد"),
    0x19: ("Circuit current above threshold", "تيار الدائرة أعلى من الحد"),
    0x1A: ("Circuit resistance below threshold", "مقاومة الدائرة أقل من الحد"),
    0x1B: ("Circuit resistance above threshold", "مقاومة الدائرة أعلى من الحد"),
    0x1C: ("Circuit voltage out of range", "جهد الدائرة خارج المدى"),
    0x1D: ("Circuit current out of range", "تيار الدائرة خارج المدى"),
    0x1E: ("Circuit resistance out of range", "مقاومة الدائرة خارج المدى"),
    0x1F: ("Circuit intermittent", "الدائرة متقطعة (تفصل وتوصل)"),
    0x21: ("Signal amplitude below minimum", "قيمة الإشارة أقل من الحد الأدنى"),
    0x22: ("Signal amplitude above maximum", "قيمة الإشارة أعلى من الحد الأقصى"),
    0x23: ("Signal stuck low", "الإشارة ثابتة على قيمة منخفضة"),
    0x24: ("Signal stuck high", "الإشارة ثابتة على قيمة مرتفعة"),
    0x25: ("Invalid or incorrect signal waveform", "شكل الإشارة غير صحيح"),
    0x26: ("Signal rate of change below threshold", "الإشارة تتغير ببطء أكثر من اللازم"),
    0x27: ("Signal rate of change above threshold", "الإشارة تتغير بسرعة أكثر من اللازم"),
    0x28: ("Signal bias level out of range / zero adjustment failure", "نقطة الصفر للإشارة خارج المدى"),
    0x29: ("Signal invalid", "الإشارة غير صالحة"),
    0x2F: ("Signal erratic", "الإشارة غير منتظمة"),
    0x31: ("No signal", "لا توجد إشارة"),
    0x41: ("General checksum failure", "خطأ في المجموع الاختباري (Checksum)"),
    0x42: ("General memory failure", "عطل في الذاكرة"),
    0x44: ("Data memory failure", "عطل في ذاكرة البيانات"),
    0x45: ("Program memory failure", "عطل في ذاكرة البرنامج"),
    0x46: ("Calibration / parameter memory failure", "عطل في ذاكرة المعايرة"),
    0x47: ("Watchdog / safety processor failure", "عطل في معالج المراقبة / الأمان"),
    0x48: ("Supervision software failure", "عطل في برنامج المراقبة"),
    0x49: ("Internal electronic failure", "عطل إلكتروني داخلي"),
    0x4A: ("Incorrect component installed", "قطعة غير مناسبة مركّبة"),
    0x4B: ("Over temperature", "حرارة زائدة"),
    0x51: ("Not programmed", "غير مبرمج"),
    0x52: ("Not activated", "غير مفعّل"),
    0x53: ("Deactivated", "تم إلغاء تفعيله"),
    0x54: ("Missing calibration", "المعايرة ناقصة"),
    0x55: ("Not configured", "غير مُعدّ (يحتاج تكويد)"),
    0x61: ("Signal calculation failure", "خطأ في حساب الإشارة"),
    0x62: ("Signal compare failure", "الإشارة لا تتطابق مع إشارة أخرى"),
    0x63: ("Circuit / component protection time-out", "انتهاء مهلة حماية الدائرة / القطعة"),
    0x64: ("Signal plausibility failure", "الإشارة غير منطقية"),
    0x65: ("Signal has too few transitions / events", "الإشارة بها تغييرات أقل من المتوقع"),
    0x66: ("Signal has too many transitions / events", "الإشارة بها تغييرات أكثر من المتوقع"),
    0x67: ("Signal incorrect after event", "الإشارة غير صحيحة بعد حدث معيّن"),
    0x71: ("Actuator stuck", "المشغّل عالق"),
    0x72: ("Actuator stuck open", "المشغّل عالق مفتوحًا"),
    0x73: ("Actuator stuck closed", "المشغّل عالق مغلقًا"),
    0x74: ("Actuator slipping", "المشغّل ينزلق"),
    0x75: ("Emergency position not reachable", "لا يصل لوضع الطوارئ"),
    0x76: ("Wrong mounting position", "مركّب في وضع خاطئ"),
    0x77: ("Commanded position not reachable", "لا يصل للوضع المطلوب"),
    0x78: ("Alignment or adjustment incorrect", "الضبط أو المحاذاة غير صحيحة"),
    0x79: ("Mechanical linkage failure", "عطل في الوصلة الميكانيكية"),
    0x7A: ("Fluid leak or seal failure", "تسريب سائل أو تلف جوان"),
    0x7B: ("Low fluid level", "مستوى السائل منخفض"),
    0x81: ("Invalid serial data received", "استقبال بيانات شبكة غير صالحة"),
    0x82: ("Alive / sequence counter incorrect", "عداد تسلسل الرسائل غير صحيح"),
    0x83: ("Signal protection value incorrect", "قيمة حماية الرسالة غير صحيحة"),
    0x84: ("Signal below allowable range", "الإشارة أقل من المسموح"),
    0x85: ("Signal above allowable range", "الإشارة أعلى من المسموح"),
    0x86: ("Signal invalid", "الإشارة غير صالحة"),
    0x87: ("Missing message", "رسالة مفقودة على الشبكة"),
    0x88: ("Bus off", "الشبكة متوقفة (Bus off)"),
    0x8F: ("Erratic", "غير منتظم"),
    0x91: ("Parametric", "خارج القيم المعيارية"),
    0x92: ("Performance or incorrect operation", "أداء ضعيف أو تشغيل غير صحيح"),
    0x93: ("No operation", "لا يعمل"),
    0x94: ("Unexpected operation", "يعمل بدون طلب"),
    0x95: ("Incorrect assembly", "تجميع غير صحيح"),
    0x96: ("Component internal failure", "عطل داخلي في القطعة"),
    0x97: ("Component or system operation obstructed or blocked", "حركة القطعة أو النظام معاقة أو مسدودة"),
    0x98: ("Component or system over temperature", "حرارة زائدة في القطعة أو النظام"),
}


def ftb_text(ftb: int | None) -> list[str]:
    """[English, Arabic] for a failure-type byte (the category when the exact value is not listed)."""
    if ftb is None:
        return ["", ""]
    if ftb in FTB:
        return list(FTB[ftb])
    cat = CATEGORIES.get(ftb >> 4)
    if cat and ftb < 0xA0:
        return [f"{cat[0]} (sub-type {ftb:02X})", f"{cat[1]} (نوع فرعي {ftb:02X})"]
    return [f"Manufacturer-specific failure type {ftb:02X}", f"نوع عطل خاص بالشركة المصنّعة {ftb:02X}"]
