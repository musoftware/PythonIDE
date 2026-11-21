"""Friendly explanations of assembler / linker messages (NASM, MASM, FASM, GNU as, ld, MS link) in English and
Arabic, so the Error List and the Problems panel can tell a beginner what the terse message means.

``explain(message) -> AsmExplanation | None``; the original message is kept (it is what a web search finds).
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AsmExplanation:
    en: str
    ar: str
    why_en: str
    why_ar: str
    fix_en: str
    fix_ar: str
    rule: str = ""              # the analyzer rule about the same problem ("Learn more")

    def message(self, lang: str = "en") -> str:
        return self.ar if lang == "ar" else self.en

    def markdown(self, original: str, lang: str = "en") -> str:
        if lang == "ar":
            return (f"**{self.ar}**\n\n*{original}*\n\n**لماذا؟** {self.why_ar}\n\n**كيف أصلحه؟** {self.fix_ar}")
        return f"**{self.en}**\n\n*{original}*\n\n**Why?** {self.why_en}\n\n**How to fix:** {self.fix_en}"


# (pattern, en, ar, why_en, why_ar, fix_en, fix_ar, rule); {0} = the first group of the pattern
_TABLE = [
    (r"invalid combination of opcode and operands|invalid instruction operands|A2070|invalid operand\b|"
     r"operand type mismatch for `?([\w.]+)",
     "This instruction does not accept these operands",
     "هذه التعليمة لا تقبل هذه المعاملات",
     "The CPU has no form of the instruction with this combination: usually different sizes (EAX with BL), two "
     "memory operands, or a number where a register is needed.",
     "لا يوجد في المعالج شكل لهذه التعليمة بهذا التركيب من المعاملات: غالباً أحجام مختلفة (EAX مع BL) أو معاملان في "
     "الذاكرة أو رقم في مكان يحتاج مسجلاً.",
     "Point at the instruction name to see its operand forms, and check the sizes and kinds of both operands.",
     "ضع مؤشر الفأرة على اسم التعليمة لترى أشكال معاملاتها، وراجع حجم ونوع كل معامل.", "ASM101"),
    (r"operation size not specified|instruction operand must have size|A2023|operand size not specified|"
     r"ambiguous operand size|no instruction mnemonic suffix given",
     "The size of the memory operand is unknown",
     "حجم معامل الذاكرة غير معروف",
     "With a memory address and a number only, the assembler cannot know if you mean 1, 2, 4 or 8 bytes.",
     "مع عنوان ذاكرة ورقم فقط لا يعرف المجمّع هل تقصد 1 أو 2 أو 4 أو 8 بايت.",
     "Write the size: byte / word / dword / qword (MASM: dword ptr; GNU as AT&T: movl / movb ...).",
     "اكتب الحجم: byte أو word أو dword أو qword (وفي MASM: dword ptr، وفي GNU as بصيغة AT&T: movl أو movb ...).",
     "ASM102"),
    (r"mismatch in operand sizes|operand sizes do not match|instruction operands must be the same size|A2022|"
     r"incorrect register `?%?(\w+)'? used with",
     "The two operands have different sizes",
     "المعاملان مختلفان في الحجم",
     "MOV, ADD, CMP ... need both operands of the same size.",
     "التعليمات MOV و ADD و CMP ... تحتاج معاملين بنفس الحجم.",
     "Use registers of the same size, or MOVZX / MOVSX to widen a smaller value.",
     "استخدم مسجلات بنفس الحجم، أو MOVZX / MOVSX لتوسيع القيمة الأصغر.", "ASM101"),
    (r"symbol `?'?([\w.@?$]+)'? (?:not defined|undefined)|undefined symbol\s*:?\s*'?([\w.@?$]+)|A2006|"
     r"undefined symbol '?([\w.@?$]+)",
     "'{0}' is not defined",
     "'{0}' غير معرّف",
     "The assembler does not know this name: a typo, a label that was never written, or an external function "
     "without an extern declaration.",
     "المجمّع لا يعرف هذا الاسم: خطأ إملائي، أو عنوان لم يُكتب، أو دالة خارجية بدون إعلان extern.",
     "Check the spelling (case matters in NASM / FASM / GNU as), define the label, or add extern / PROTO.",
     "راجع الإملاء (حالة الحروف مهمة في NASM و FASM و GNU as)، أو عرّف العنوان، أو أضف extern أو PROTO.", "ASM201"),
    (r"undefined reference to `?'?([\w.@?$]+)|unresolved external symbol\s+_?_?(?:imp_)?([\w@?$]+)|LNK2019|LNK2001",
     "The linker cannot find '{0}'",
     "الرابط (linker) لا يجد '{0}'",
     "The code assembled, but no object file or library given to the linker contains this function.",
     "تم تجميع الكود، لكن لا يوجد في الملفات أو المكتبات المعطاة للرابط ملف يحتوي هذه الدالة.",
     "Check the name (and its decoration, e.g. _MessageBoxA@16 in 32-bit code) and that the library (kernel32, "
     "user32, msvcrt ...) is linked.",
     "راجع الاسم (وتزيينه مثل _MessageBoxA@16 في كود 32 بت) وتأكد من ربط المكتبة (kernel32 و user32 و msvcrt ...).",
     "ASM202"),
    (r"(?:label|symbol) `?'?([\w.@?$]+)'? (?:inconsistently )?redefined|symbol redefinition\s*:?\s*([\w.@?$]+)|"
     r"A2005|symbol already defined|symbol `?([\w.@?$]+)'? is already defined",
     "'{0}' is defined twice",
     "'{0}' معرّف مرتين",
     "Every label names one place; two definitions with one name are ambiguous.",
     "كل عنوان يسمّي مكاناً واحداً، وتعريفان بنفس الاسم يسببان التباساً.",
     "Rename one of them (local labels such as .loop help inside functions).",
     "غيّر اسم أحدهما (العناوين المحلية مثل ‎.loop تساعد داخل الدوال).", "ASM203"),
    (r"(?:signed |unsigned )?(?:dword|word|byte|qword) (?:value|data) exceeds bounds|value out of range|"
     r"constant value too large|A2084|initializer magnitude too large|A2071|value of \S+ too large",
     "The number does not fit in the operand",
     "الرقم لا يتسع في المعامل",
     "The value is bigger than the operand size can hold; only its low bits would be kept.",
     "القيمة أكبر مما يتسع له حجم المعامل؛ ستبقى البتات المنخفضة منها فقط.",
     "Use a bigger operand / register, or a smaller number.",
     "استخدم معاملاً أو مسجلاً أكبر، أو رقماً أصغر.", "ASM104"),
    (r"invalid effective address|impossible combination of address sizes|must be index or base register|A2031|"
     r"invalid address|`?([^']*)'? is not a valid base/index expression|A2032",
     "This memory address cannot be encoded",
     "لا يمكن ترميز عنوان الذاكرة هذا",
     "Addresses are base + index*scale + number, with scale 1, 2, 4 or 8; in 16-bit code only BX, BP, SI, DI.",
     "العنوان يكون أساس + فهرس*معامل + رقم، والمعامل 1 أو 2 أو 4 أو 8؛ وفي كود 16 بت فقط BX و BP و SI و DI.",
     "Compute the address in a register first, then use [register].",
     "احسب العنوان في مسجل أولاً، ثم استخدم [المسجل].", "ASM105"),
    (r"parser: instruction expected|no such instruction: `?([\w.]+)|illegal instruction|A2008|"
     r"label or instruction expected at start of line",
     "Unknown instruction (a typo?)",
     "تعليمة غير معروفة (خطأ في الكتابة؟)",
     "The first word of the line is not an instruction, directive or macro that the assembler knows.",
     "الكلمة الأولى في السطر ليست تعليمة أو توجيهاً أو ماكرو يعرفه المجمّع.",
     "Check the spelling of the instruction; a label needs a colon (name:).",
     "راجع كتابة التعليمة؛ والعنوان (label) يحتاج نقطتين (name:).", ""),
    (r"comma,? colon,? decorator or end of line expected|extra characters on line|junk `?([^']*)'? after expression|"
     r"expression syntax error|A2009|syntax error",
     "Syntax error in the operands",
     "خطأ في صياغة المعاملات",
     "Something in the operand list is not valid: a missing comma, an unknown word, or unbalanced brackets.",
     "شيء ما في قائمة المعاملات غير صالح: فاصلة ناقصة أو كلمة غير معروفة أو أقواس غير متوازنة.",
     "Check commas and brackets: mov eax, [ebx+4].",
     "راجع الفواصل والأقواس: mov eax, [ebx+4].", ""),
    (r"short jump is out of range|relative jump out of range|jump destination too far|A2075",
     "The jump target is too far for a short jump",
     "هدف القفزة بعيد جداً على القفزة القصيرة",
     "A short jump reaches only -128..+127 bytes.",
     "القفزة القصيرة تصل فقط من -128 إلى +127 بايت.",
     "Remove 'short' (or use 'near'), or reorganise the code.",
     "احذف كلمة short (أو استخدم near)، أو أعد ترتيب الكود.", ""),
    (r"instruction not supported in 64-bit mode|not supported in 64-bit|invalid instruction in 64-bit|"
     r"`?(\w+)'? is not supported in 64-bit mode",
     "This instruction does not exist in 64-bit mode",
     "هذه التعليمة غير موجودة في وضع 64 بت",
     "Some old instructions (PUSHA, AAA, LDS ...) were removed from 64-bit mode.",
     "بعض التعليمات القديمة (PUSHA و AAA و LDS ...) حُذفت من وضع 64 بت.",
     "Write the equivalent instructions yourself.",
     "اكتب التعليمات المكافئة بنفسك.", "ASM115"),
    (r"no instruction for this cpu level|instruction or register not accepted in current CPU mode|A2085",
     "This instruction / register is not available for the selected CPU",
     "هذه التعليمة أو المسجل غير متاح للمعالج المحدد",
     "The program targets an older CPU or mode (e.g. 16-bit 8086) that does not have it.",
     "البرنامج يستهدف معالجاً أو وضعاً أقدم (مثل 8086 ذي الـ 16 بت) لا يحتوي عليها.",
     "Use instructions of that CPU, or select a newer one (.386, cpu x64, bits 32).",
     "استخدم تعليمات هذا المعالج، أو اختر معالجاً أحدث (‎.386 أو cpu x64 أو bits 32).", "ASM108"),
    (r"unable to open include file|file not found|cannot open (?:include )?file|can't open",
     "The include file was not found",
     "لم يتم العثور على ملف التضمين",
     "The assembler looks for include files next to the source and in its include folders.",
     "المجمّع يبحث عن ملفات التضمين بجوار الملف وفي مجلدات التضمين الخاصة به.",
     "Check the file name and put the file in the project folder (or install the assembler's include files).",
     "راجع اسم الملف وضعه في مجلد المشروع (أو ثبّت ملفات التضمين الخاصة بالمجمّع).", ""),
    (r"relocation truncated to fit",
     "An address does not fit in the instruction (relocation truncated)",
     "العنوان لا يتسع في التعليمة (relocation truncated)",
     "In 64-bit code a 32-bit absolute address cannot reach every variable.",
     "في كود 64 بت العنوان المطلق ذو الـ 32 بت لا يصل إلى كل المتغيرات.",
     "Use RIP-relative addresses: 'default rel' in NASM, lea rax, [rel x].",
     "استخدم العناوين النسبية لـ RIP: ‏'default rel' في NASM، و lea rax, [rel x].", "ASM206"),
    (r"attempt to define a local label before any non-local labels",
     "A local label (.name) needs a normal label before it",
     "العنوان المحلي (‎.name) يحتاج عنواناً عادياً قبله",
     "NASM names local labels after the last normal label; there is none yet.",
     "يسمّي NASM العناوين المحلية بحسب آخر عنوان عادي، ولا يوجد واحد بعد.",
     "Add a normal label (main:) before it, or remove the dot.",
     "أضف عنواناً عادياً (main:) قبله، أو احذف النقطة.", ""),
    (r"label alone on a line without a colon",
     "A label without a colon",
     "عنوان بدون نقطتين",
     "NASM guesses that the lonely word is a label; it may also be a misspelt instruction.",
     "يخمّن NASM أن الكلمة الوحيدة عنوان؛ وقد تكون تعليمة مكتوبة خطأ.",
     "Add a colon after the label (name:) or fix the instruction name.",
     "أضف نقطتين بعد العنوان (name:) أو صحّح اسم التعليمة.", ""),
    (r"unterminated string|missing (?:closing )?quote|missing end quote",
     "A string is not closed",
     "النص غير مغلق",
     "A quote opens a string that never ends on this line.",
     "علامة الاقتباس تفتح نصاً لا ينتهي في هذا السطر.",
     "Add the closing quote.",
     "أضف علامة الاقتباس الختامية.", ""),
    (r"END directive required|missing end directive|unexpected end of file",
     "The file ends too early (END missing or a block not closed)",
     "الملف ينتهي مبكراً (END ناقصة أو كتلة غير مغلقة)",
     "MASM needs END at the end of the file; every PROC / MACRO / IF needs its ENDP / ENDM / ENDIF.",
     "يحتاج MASM إلى END في آخر الملف، وكل PROC أو MACRO أو IF تحتاج ENDP أو ENDM أو ENDIF.",
     "Add the missing END / ENDP / ENDM / ENDIF.",
     "أضف END أو ENDP أو ENDM أو ENDIF الناقصة.", ""),
    (r"too many memory references|A2070 two memory",
     "Two memory operands in one instruction",
     "معاملا ذاكرة في تعليمة واحدة",
     "x86 instructions can access only one memory location each.",
     "تعليمات x86 تصل إلى موقع واحد فقط في الذاكرة.",
     "Move one value through a register first.",
     "انقل إحدى القيمتين عبر مسجل أولاً.", "ASM103"),
    (r"bad register name `?%?(\w+)|invalid register|reserved word used as symbol",
     "Invalid register name",
     "اسم مسجل غير صالح",
     "The word is not a register of this CPU / mode, or a register name is used as a label.",
     "الكلمة ليست مسجلاً في هذا المعالج أو الوضع، أو تم استخدام اسم مسجل كاسم عنوان.",
     "Check the register name (and the % prefix in AT&T syntax).",
     "راجع اسم المسجل (والبادئة % في صيغة AT&T).", "ASM108"),
    (r"number of operands mismatch for `?(\w+)|expecting operand after ','",
     "Wrong number of operands",
     "عدد المعاملات خطأ",
     "The instruction takes a different number of operands.",
     "التعليمة تأخذ عدداً مختلفاً من المعاملات.",
     "Check the instruction's forms in the hover.",
     "راجع أشكال التعليمة في التلميح.", "ASM116"),
]
_COMPILED = [(re.compile(t[0], re.I), t) for t in _TABLE]


def explain(message: str) -> AsmExplanation | None:
    for rx, t in _COMPILED:
        m = rx.search(message or "")
        if m:
            arg = next((g for g in m.groups() if g), "") if m.groups() else ""
            return AsmExplanation(t[1].replace("{0}", arg), t[2].replace("{0}", arg), t[3], t[4], t[5], t[6], t[7])
    return None


def friendly(message: str, lang: str = "en") -> str:
    """'<friendly text> - <original>' (the original stays for web searches); the message itself when unknown."""
    e = explain(message)
    if e is None:
        return message
    return f"{e.message(lang)} — {message}"
