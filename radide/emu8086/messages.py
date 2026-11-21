"""Assembler / emulator messages in English and Arabic.

Every diagnostic has a short code (``E-UNDEF``...) so tests and the IDE can match it without depending on the
wording. ``text(code, lang, **args)`` formats one message; Arabic text keeps the English one in brackets so a
student can search the web for it.
"""
from __future__ import annotations

MESSAGES: dict[str, tuple[str, str]] = {
    # ------------------------------------------------------------------ assembler: syntax
    "E-SYNTAX": ("syntax error: {what}", "خطأ في الصياغة: {what}"),
    "E-UNKNOWN-INSTR": ("unknown instruction or directive '{name}'",
                        "تعليمة أو توجيه غير معروف '{name}'"),
    "E-OPERANDS": ("'{name}' expects {n} operand(s)", "التعليمة '{name}' تحتاج {n} معامل/معاملات"),
    "E-BAD-OPERAND": ("invalid operand '{op}' for '{name}'", "المعامل '{op}' غير صالح مع '{name}'"),
    "E-UNDEF": ("undefined symbol '{name}'", "الرمز '{name}' غير معرّف (هل نسيت تعريف المتغير أو العنوان؟)"),
    "E-REDEF": ("symbol '{name}' is already defined (line {line})",
                "الرمز '{name}' معرّف من قبل (السطر {line})"),
    "E-SIZE-MISMATCH": ("operand sizes do not match ({a} and {b} bits)",
                        "حجم المعاملين غير متساوٍ ({a} و {b} بت)"),
    "E-SIZE-UNKNOWN": ("operand size is unknown: write 'byte ptr' or 'word ptr'",
                       "حجم المعامل غير معروف: اكتب byte ptr أو word ptr"),
    "E-MEM-MEM": ("both operands are memory: move through a register (e.g. mov ax, a / mov b, ax)",
                  "لا يمكن أن يكون المعاملان كلاهما في الذاكرة: انقل عبر مسجّل (مثلاً mov ax, a ثم mov b, ax)"),
    "E-IMM-SREG": ("an immediate value cannot go to a segment register: use mov ax, value / mov {sreg}, ax",
                   "لا يمكن وضع قيمة مباشرة في مسجّل مقطع: استخدم mov ax, القيمة ثم mov {sreg}, ax"),
    "E-CS-DEST": ("CS cannot be changed with mov/pop: use a far jmp or call",
                  "لا يمكن تغيير CS بالتعليمة mov أو pop: استخدم jmp أو call بعيد"),
    "E-IMM-DEST": ("the destination cannot be an immediate value", "الوجهة لا يمكن أن تكون قيمة مباشرة"),
    "E-RANGE": ("value {value} does not fit in {bits} bits", "القيمة {value} لا تتسع في {bits} بت"),
    "E-JUMP-RANGE": ("jump target is too far ({dist} bytes; '{name}' reaches -128..+127)",
                     "هدف القفز بعيد جداً ({dist} بايت؛ '{name}' تصل فقط من -128 إلى +127)"),
    "E-BAD-ADDR": ("invalid address expression: {what}", "تعبير عنوان غير صالح: {what}"),
    "E-BAD-REGS": ("registers {regs} cannot be combined in an address (allowed: [bx|bp] + [si|di] + number)",
                   "لا يمكن جمع المسجلات {regs} في عنوان (المسموح: [bx أو bp] + [si أو di] + رقم)"),
    "E-EXPR": ("cannot evaluate expression: {what}", "تعذّر حساب التعبير: {what}"),
    "E-DIV0": ("division by zero in expression", "قسمة على صفر داخل التعبير"),
    "E-NUMBER": ("invalid number '{text}'", "رقم غير صالح '{text}'"),
    "E-STRING": ("string not allowed here ({what})", "النص غير مسموح هنا ({what})"),
    "E-ENDP": ("'{name} endp' without a matching proc", "'{name} endp' بدون proc مطابق"),
    "E-PROC-OPEN": ("procedure '{name}' is not closed with '{name} endp'",
                    "الإجراء '{name}' لم يُغلق بـ '{name} endp'"),
    "E-ENDS": ("'ends' without a matching segment", "'ends' بدون segment مطابق"),
    "E-MACRO-OPEN": ("macro '{name}' has no 'endm'", "الماكرو '{name}' بلا endm"),
    "E-MACRO-DEPTH": ("macros nested too deeply (recursive macro?)",
                      "الماكرو متداخل بعمق كبير (هل يستدعي نفسه؟)"),
    "E-INCLUDE": ("cannot read include file '{name}'", "تعذّر قراءة الملف المضمّن '{name}'"),
    "E-NOT-SUPPORTED": ("'{name}' is not supported by the 8086 emulator", "'{name}' غير مدعوم في محاكي 8086"),
    "E-COND": ("'{name}' without a matching IF", "'{name}' بدون IF مطابق"),
    "E-COND-OPEN": ("IF without ENDIF", "IF بدون ENDIF"),
    "E-STRUC-OPEN": ("structure '{name}' has no ENDS", "الهيكل '{name}' بدون ENDS"),
    "E-EXPORT-COM": ("this is not a COM program (use .model tiny / org 100h, or export an EXE)",
                     "هذا ليس برنامج COM (استخدم ‎.model tiny‎ أو org 100h، أو صدّره EXE)"),
    "E-NO-CODE": ("the program has no instructions", "البرنامج لا يحتوي على أي تعليمات"),
    "E-PASSES": ("the assembler could not settle the addresses (too many passes)",
                 "لم يستطع المجمّع تثبيت العناوين (تمريرات كثيرة)"),
    "E-DUP": ("invalid 'dup' count", "عدد التكرار في dup غير صالح"),
    "E-SHIFT-COUNT": ("shift count must be 1, CL or a number", "عدد الإزاحة يجب أن يكون 1 أو CL أو رقماً"),
    "E-PORT": ("port must be a number 0..255 or DX", "المنفذ يجب أن يكون رقماً من 0 إلى 255 أو DX"),
    "E-ACC": ("this form needs AL or AX", "هذه الصيغة تحتاج AL أو AX"),
    "E-REG16": ("a 16-bit register is required", "يلزم مسجّل 16 بت"),
    "E-NEED-MEM": ("a memory operand is required", "يلزم معامل في الذاكرة"),
    "E-LABEL": ("a label is required as the jump target", "يلزم عنوان (label) كهدف للقفز"),
    # ------------------------------------------------------------------ assembler: warnings
    "W-386": ("'{name}' ignored: the emulator runs 8086 (with 80186 extras) code only",
              "تم تجاهل '{name}': المحاكي يشغّل كود 8086 (مع إضافات 80186) فقط"),
    "W-NOSTACK": ("no stack segment: the emulator gives the program a 4 KB stack",
                  "لا يوجد مقطع مكدس: أعطى المحاكي البرنامج مكدساً بحجم 4 كيلوبايت"),
    "W-CHAR": ("character '{ch}' is not in the DOS code page and was replaced by '?'",
               "الحرف '{ch}' غير موجود في صفحة ترميز DOS واستُبدل بـ '?'"),
    "W-186": ("'{name}' is an 80186 instruction (works here, not on a real 8086)",
              "'{name}' تعليمة 80186 (تعمل هنا ولا تعمل على 8086 حقيقي)"),
    "W-JCC-LONG": ("conditional jump to '{name}' is too far: replaced by an opposite jump over a jmp",
                   "القفز الشرطي إلى '{name}' بعيد: استُبدل بقفز معاكس فوق jmp"),
    "W-IGNORED": ("'{name}' ignored", "تم تجاهل '{name}'"),
    # ------------------------------------------------------------------ emulator
    "R-DIV0": ("divide error (division by zero or the result does not fit) at {addr}",
               "خطأ قسمة (قسمة على صفر أو الناتج لا يتسع) عند {addr}"),
    "R-BAD-OPCODE": ("unknown opcode {op} at {addr} (the program jumped into data?)",
                     "كود تعليمة غير معروف {op} عند {addr} (هل قفز البرنامج إلى البيانات؟)"),
    "R-HALT": ("HLT executed at {addr}: the CPU stopped", "نُفذت HLT عند {addr}: توقف المعالج"),
    "R-INT": ("interrupt {num} function {fn} is not emulated (ignored)",
              "المقاطعة {num} الوظيفة {fn} غير مدعومة في المحاكي (تم تجاهلها)"),
    "R-LIMIT": ("stopped after {n} instructions (endless loop?)",
                "توقف بعد {n} تعليمة (حلقة لا نهائية؟)"),
    "R-INPUT": ("the program is waiting for keyboard input", "البرنامج ينتظر إدخالاً من لوحة المفاتيح"),
    "R-EXIT": ("program terminated with code {code}", "انتهى البرنامج برمز الخروج {code}"),
}


def text(code: str, lang: str = "en", **args) -> str:
    en, ar = MESSAGES.get(code, (code, code))
    try:
        en_t = en.format(**args)
    except (KeyError, IndexError, ValueError):
        en_t = en
    if lang != "ar":
        return en_t
    try:
        ar_t = ar.format(**args)
    except (KeyError, IndexError, ValueError):
        ar_t = ar
    return f"{ar_t}  ({en_t})"


def ui_language() -> str:
    """The IDE's UI language when it is running ("en" otherwise)."""
    try:
        from ..i18n import language
        return language() or "en"
    except Exception:  # noqa: BLE001 - the package also works without the IDE / Qt
        return "en"
