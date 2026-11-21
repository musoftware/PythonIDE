"""The rule catalogue of the assembly analyzer: id, default severity, category and the bilingual texts.

Every rule has three texts in English and Arabic (written for beginners, original text):

* ``msg``  - the short message shown as the squiggle / Error List text (``{placeholders}`` are filled per issue);
* ``why``  - why this is a problem (what the CPU / assembler / operating system really does);
* ``fix``  - what to change, concretely.

``topic`` picks the "Learn more" reference (see TOPICS) and ``lesson`` the Arabic assembly course lesson
(radide/tutorials/assembly) that explains the subject.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..asm_intel import apis, isa

TOPICS = {
    "isa": isa.SDM_URL,
    "win64": apis.X64_ABI_URL,
    "sysv": apis.SYSV_ABI_URL,
    "x86": "https://learn.microsoft.com/en-us/cpp/cpp/argument-passing-and-naming-conventions",
    "dos": "https://en.wikipedia.org/wiki/DOS_API",
    "nasm": "https://www.nasm.us/doc/",
    "masm": "https://learn.microsoft.com/en-us/cpp/assembler/masm/microsoft-macro-assembler-reference",
    "fasm": "https://flatassembler.net/docs.php",
    "gas": "https://sourceware.org/binutils/docs/as/",
}


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str           # error | warning | info
    category: str           # operands | symbols | flow | data | abi | dos
    name: str               # short kebab-case name (configuration files may use it instead of the id)
    msg_en: str
    msg_ar: str
    why_en: str
    why_ar: str
    fix_en: str
    fix_ar: str
    topic: str = "isa"
    lesson: str = ""


_R: list[Rule] = []


def _rule(*args, **kw) -> None:
    _R.append(Rule(*args, **kw))


# ============================================================================ operands (encoding)
_rule("ASM101", "error", "operands", "operand-size-mismatch",
      "Operand sizes do not match: {a} is {sa}-bit but {b} is {sb}-bit",
      "حجم المعاملين غير متساوٍ: {a} حجمه {sa} بت لكن {b} حجمه {sb} بت",
      "Most two-operand instructions (MOV, ADD, CMP ...) work on two values of the SAME size. The CPU has no "
      "instruction that copies a 8-bit register into a 32-bit one with MOV, so the assembler refuses it.",
      "معظم التعليمات ذات المعاملين (MOV و ADD و CMP ...) تعمل على قيمتين بنفس الحجم. لا توجد في المعالج تعليمة "
      "MOV تنسخ مسجلاً حجمه 8 بت إلى مسجل حجمه 32 بت، لذلك يرفضها المجمّع.",
      "Use registers of the same size (EAX with EBX, AL with BL), or widen the small value with MOVZX "
      "(unsigned) / MOVSX (signed).",
      "استخدم مسجلات بنفس الحجم (EAX مع EBX و AL مع BL)، أو وسّع القيمة الصغيرة بالتعليمة MOVZX (بدون إشارة) أو "
      "MOVSX (بإشارة).", lesson="03-registers-memory")
_rule("ASM102", "error", "operands", "ambiguous-memory-size",
      "The size of the memory operand {op} is unknown: write {hint}",
      "حجم معامل الذاكرة {op} غير معروف: اكتب {hint}",
      "With only a memory address and a number (or no other operand) the assembler cannot know whether you mean "
      "1, 2, 4 or 8 bytes at that address - each size is a different instruction.",
      "عندما يكون في التعليمة عنوان ذاكرة ورقم فقط (أو لا يوجد معامل آخر) لا يستطيع المجمّع أن يعرف هل تقصد 1 أو 2 "
      "أو 4 أو 8 بايت عند هذا العنوان، فكل حجم تعليمة مختلفة.",
      "Say the size explicitly before the memory operand: byte / word / dword / qword (MASM: byte ptr ...).",
      "اكتب الحجم صراحة قبل معامل الذاكرة: byte أو word أو dword أو qword (وفي MASM: byte ptr ...).",
      lesson="04-data")
_rule("ASM103", "error", "operands", "memory-to-memory",
      "{mnem} cannot take two memory operands",
      "التعليمة {mnem} لا تقبل معاملين كلاهما في الذاكرة",
      "x86 instructions can read or write at most ONE memory location per instruction (string instructions "
      "such as MOVSB are the exception). Moving memory to memory needs a register in the middle.",
      "تعليمات x86 تقرأ أو تكتب موقعاً واحداً فقط في الذاكرة في التعليمة الواحدة (باستثناء تعليمات النصوص مثل MOVSB). "
      "النقل من ذاكرة إلى ذاكرة يحتاج مسجلاً وسيطاً.",
      "Load the source into a free register first, then store the register: mov eax, [a] / mov [b], eax.",
      "حمّل المصدر في مسجل فارغ أولاً ثم خزّن المسجل: mov eax, [a] ثم mov [b], eax.", lesson="03-registers-memory")
_rule("ASM104", "error", "operands", "immediate-too-large",
      "The value {value} does not fit in {bits} bits",
      "القيمة {value} لا تتسع في {bits} بت",
      "A {bits}-bit operand holds values from {lo} to {hi}. Bigger numbers are cut off (only the low bits are "
      "kept), so the program would use a different number than the one you wrote.",
      "المعامل ذو الـ {bits} بت يتسع للقيم من {lo} إلى {hi}. الرقم الأكبر يُقطع (تبقى البتات المنخفضة فقط)، فيستخدم "
      "البرنامج رقماً غير الذي كتبته.",
      "Use a bigger register / operand size, or a smaller value. In 64-bit code most instructions take only a "
      "32-bit signed immediate: load big constants with mov rax, value first.",
      "استخدم مسجلاً أو حجماً أكبر، أو قيمة أصغر. في كود 64 بت معظم التعليمات تقبل رقماً مباشراً بحجم 32 بت بإشارة "
      "فقط: حمّل الثوابت الكبيرة أولاً بالتعليمة mov rax, القيمة.", lesson="02-numbers")
_rule("ASM105", "error", "operands", "invalid-scale",
      "Invalid address {op}: {what}",
      "عنوان غير صالح {op}: {what_ar}",
      "A memory address can be base + index*scale + displacement, where scale is 1, 2, 4 or 8 and ESP/RSP can "
      "never be the scaled index. Anything else cannot be encoded by the CPU.",
      "العنوان في الذاكرة يكون بالشكل: أساس + فهرس*معامل + إزاحة، والمعامل 1 أو 2 أو 4 أو 8 فقط، ولا يمكن أن يكون "
      "ESP/RSP هو الفهرس المضروب. أي شكل آخر لا يستطيع المعالج ترميزه.",
      "Compute the address in a register first (lea / imul / shl), then use [register].",
      "احسب العنوان في مسجل أولاً (lea أو imul أو shl) ثم استخدم [المسجل].", lesson="08-arrays")
_rule("ASM106", "error", "operands", "invalid-16bit-address",
      "{op} is not a valid 16-bit address: only BX, BP, SI and DI can be used",
      "{op} ليس عنواناً صالحاً في وضع 16 بت: يمكن استخدام BX و BP و SI و DI فقط",
      "In 16-bit code (8086 / DOS) an address may contain at most one of BX/BP plus one of SI/DI plus a number. "
      "AX, CX, DX and SP can never appear inside [ ], and there is no scaling (*2, *4).",
      "في كود 16 بت (8086 / DOS) يحتوي العنوان على واحد على الأكثر من BX/BP وواحد من SI/DI ورقم. لا يمكن أبداً "
      "وضع AX أو CX أو DX أو SP داخل [ ]، ولا يوجد ضرب (*2 أو *4).",
      "Copy the value into BX, SI or DI first: mov bx, ax / mov dl, [bx]. For word arrays double the index "
      "yourself (shl si, 1).",
      "انسخ القيمة إلى BX أو SI أو DI أولاً: mov bx, ax ثم mov dl, [bx]. ولمصفوفات الكلمات ضاعف الفهرس بنفسك "
      "(shl si, 1).", lesson="13-emu8086")
_rule("ASM107", "error", "operands", "mixed-address-size",
      "The address {op} mixes {what}",
      "العنوان {op} يخلط {what_ar}",
      "All registers inside one address must have the same size (all 16-bit, all 32-bit or all 64-bit), and "
      "64-bit code cannot use 16-bit address registers at all.",
      "كل المسجلات داخل العنوان الواحد يجب أن تكون بنفس الحجم (كلها 16 أو 32 أو 64 بت)، وكود 64 بت لا يقبل مسجلات "
      "العنونة ذات الـ 16 بت إطلاقاً.",
      "Use registers of one size inside [ ]: [rbx+rsi*4] in 64-bit code, [ebx+esi*4] in 32-bit code.",
      "استخدم مسجلات بحجم واحد داخل [ ]: ‏[rbx+rsi*4] في كود 64 بت و [ebx+esi*4] في كود 32 بت.", lesson="08-arrays")
_rule("ASM108", "error", "operands", "register-not-in-mode",
      "{reg} does not exist in {mode} code",
      "المسجل {reg} غير موجود في كود {mode_ar}",
      "{why}",
      "{why_ar}",
      "Use the registers of this mode ({regs}), or change the mode (bits / .model / format) if you meant "
      "another kind of program.",
      "استخدم مسجلات هذا الوضع ({regs})، أو غيّر الوضع (bits أو ‎.model أو format) إن كنت تقصد نوعاً آخر من "
      "البرامج.", lesson="03-registers-memory")
_rule("ASM109", "error", "operands", "immediate-destination",
      "The first operand of {mnem} cannot be a number",
      "المعامل الأول للتعليمة {mnem} لا يمكن أن يكون رقماً",
      "The first operand is where the result goes (or, for CMP / TEST, the value being tested). A constant "
      "number is not a place in the CPU or in memory, so nothing can be stored into it.",
      "المعامل الأول هو مكان وضع النتيجة (أو القيمة التي تُختبر في CMP و TEST). الرقم الثابت ليس مكاناً في المعالج "
      "أو في الذاكرة، فلا يمكن التخزين فيه.",
      "Put a register or a memory operand first: mov eax, 5 (not mov 5, eax). For CMP write cmp eax, 5.",
      "ضع مسجلاً أو معامل ذاكرة أولاً: mov eax, 5 وليس mov 5, eax. وفي المقارنة اكتب cmp eax, 5.")
_rule("ASM110", "error", "operands", "segment-register-misuse",
      "{what}",
      "{what_ar}",
      "Segment registers (CS DS ES SS FS GS) are special: they can only be loaded from a general register or "
      "from memory, never from a number or another segment register, they take no arithmetic, and CS changes "
      "only through a far JMP / CALL / RET.",
      "مسجلات المقاطع (CS DS ES SS FS GS) خاصة: تُحمّل فقط من مسجل عام أو من الذاكرة، ولا تُحمّل من رقم أو من مسجل "
      "مقطع آخر، ولا تقبل العمليات الحسابية، و CS لا يتغير إلا بقفزة أو استدعاء أو رجوع بعيد (far).",
      "Go through a general register: mov ax, @data / mov ds, ax.",
      "مرّ عبر مسجل عام: mov ax, @data ثم mov ds, ax.", lesson="13-emu8086")
_rule("ASM111", "error", "operands", "movzx-movsx-sizes",
      "{mnem} needs a smaller source: {what}",
      "التعليمة {mnem} تحتاج مصدراً أصغر: {what_ar}",
      "MOVZX / MOVSX widen an 8-bit or 16-bit value into a bigger register. The source must be smaller than the "
      "destination; a 32-bit source into a 64-bit register is MOVSXD (signed) or a plain 32-bit MOV (unsigned: "
      "writing a 32-bit register clears the upper half).",
      "التعليمتان MOVZX و MOVSX توسّعان قيمة حجمها 8 أو 16 بت إلى مسجل أكبر. يجب أن يكون المصدر أصغر من الوجهة؛ "
      "ونقل مصدر 32 بت إلى مسجل 64 بت يكون بالتعليمة MOVSXD (بإشارة) أو بـ MOV عادية على 32 بت (بدون إشارة: "
      "الكتابة في مسجل 32 بت تصفّر النصف العلوي).",
      "Use a plain MOV for equal sizes, MOVSXD for signed 32 to 64 bits.",
      "استخدم MOV العادية للأحجام المتساوية، و MOVSXD للتوسيع بإشارة من 32 إلى 64 بت.")
_rule("ASM112", "error", "operands", "lea-needs-memory",
      "LEA needs a memory operand: write {hint}",
      "التعليمة LEA تحتاج معامل ذاكرة: اكتب {hint}",
      "LEA computes the ADDRESS of a memory operand (it does not read memory). Its source must be written as a "
      "memory reference in square brackets.",
      "التعليمة LEA تحسب عنوان معامل الذاكرة (ولا تقرأ الذاكرة)، فلا بد أن يُكتب مصدرها كمرجع ذاكرة بين قوسين "
      "مربعين.",
      "Use lea reg, [label] for an address, or mov reg, value to copy a value.",
      "استخدم lea reg, [label] للحصول على عنوان، أو mov reg, value لنسخ قيمة.", lesson="04-data")
_rule("ASM113", "error", "operands", "high-byte-with-rex",
      "{reg} cannot be used together with {other}",
      "لا يمكن استخدام {reg} مع {other} في نفس التعليمة",
      "AH, BH, CH and DH have no encoding in instructions that need a REX prefix: any use of SIL, DIL, SPL, BPL, "
      "R8-R15 or a 64-bit operand. The CPU would read SPL/BPL/SIL/DIL instead.",
      "المسجلات AH و BH و CH و DH لا يمكن ترميزها في تعليمة تحتاج البادئة REX: أي تعليمة فيها SIL أو DIL أو SPL أو "
      "BPL أو R8-R15 أو معامل 64 بت. سيقرأ المعالج SPL/BPL/SIL/DIL بدلاً منها.",
      "Copy through another register: movzx eax, ah / mov r8b, al.",
      "انسخ عبر مسجل آخر: movzx eax, ah ثم mov r8b, al.")
_rule("ASM114", "error", "operands", "push-pop-size",
      "{mnem} {op}: {what}",
      "{mnem} {op}: {what_ar}",
      "PUSH and POP move 2, 4 or 8 bytes: in 64-bit mode they work on 64-bit (or 16-bit) values, in 32-bit mode "
      "on 32-bit (or 16-bit) values. A byte can never be pushed alone.",
      "التعليمتان PUSH و POP تنقلان 2 أو 4 أو 8 بايت: في وضع 64 بت تعملان على قيم 64 بت (أو 16 بت)، وفي وضع "
      "32 بت على قيم 32 بت (أو 16 بت). لا يمكن دفع بايت واحد وحده.",
      "Push the full register of this mode, e.g. push rax in 64-bit code.",
      "ادفع المسجل الكامل لهذا الوضع، مثلاً push rax في كود 64 بت.", lesson="09-stack-procedures")
_rule("ASM115", "error", "operands", "not-in-64-bit",
      "{mnem} does not exist in 64-bit mode",
      "التعليمة {mnem} غير موجودة في وضع 64 بت",
      "Some old instructions (PUSHA, POPA, BCD instructions such as AAA / DAA, INTO, BOUND, LDS / LES) were "
      "removed from 64-bit mode; their opcodes mean something else there.",
      "بعض التعليمات القديمة (PUSHA و POPA وتعليمات BCD مثل AAA و DAA و INTO و BOUND و LDS/LES) حُذفت من وضع "
      "64 بت، وأرقامها تعني شيئاً آخر هناك.",
      "Write the equivalent instructions yourself (e.g. push each register you need).",
      "اكتب التعليمات المكافئة بنفسك (مثلاً ادفع كل مسجل تحتاجه على حدة).")
_rule("ASM116", "error", "operands", "operand-count",
      "{mnem} takes {expected}, not {got}",
      "التعليمة {mnem} تأخذ {expected_ar}، وليس {got}",
      "Each instruction has a fixed number of operands; a missing or extra operand usually means a typo "
      "(a forgotten comma, or a wrong instruction name).",
      "لكل تعليمة عدد ثابت من المعاملات؛ والمعامل الناقص أو الزائد يعني غالباً خطأً في الكتابة (فاصلة منسية أو اسم "
      "تعليمة خطأ).",
      "Check the instruction's operand forms in the hover (point the mouse at the instruction name).",
      "راجع أشكال معاملات التعليمة في التلميح (ضع مؤشر الفأرة على اسم التعليمة).")
_rule("ASM117", "error", "operands", "mul-div-immediate",
      "{mnem} cannot take a number directly",
      "التعليمة {mnem} لا تقبل رقماً مباشراً",
      "MUL, DIV and IDIV (one-operand forms) only accept a register or a memory operand; the other factor is "
      "always the accumulator (AL / AX / EAX / RAX).",
      "التعليمات MUL و DIV و IDIV (بمعامل واحد) تقبل مسجلاً أو معامل ذاكرة فقط؛ والقيمة الأخرى دائماً في المركم "
      "(AL أو AX أو EAX أو RAX).",
      "Load the number into a register first: mov {reg}, {value} / {mnem} {reg}.",
      "حمّل الرقم في مسجل أولاً: mov {reg}, {value} ثم {mnem} {reg}.", lesson="05-arithmetic")
_rule("ASM118", "info", "operands", "not-on-8086",
      "{what} is not available on a real 8086 (80186 and later)",
      "{what_ar} غير متاح في معالج 8086 الحقيقي (من 80186 وما بعده)",
      "The 8086 cannot push a number, shift by a count other than 1 except through CL, or use PUSHA / ENTER. "
      "The emulator accepts them, but real 8086 hardware and strict course assemblers do not.",
      "المعالج 8086 لا يستطيع دفع رقم مباشر، ولا الإزاحة بعدد غير 1 إلا عبر CL، ولا استخدام PUSHA أو ENTER. "
      "المحاكي يقبلها، لكن المعالج 8086 الحقيقي والمجمّعات الصارمة في المقررات لا تقبلها.",
      "Use the 8086 form: {fix}.",
      "استخدم صيغة 8086: {fix}.", lesson="13-emu8086")
_rule("ASM119", "warning", "operands", "32bit-address-in-64bit",
      "{op} uses 32-bit registers as an address in 64-bit code",
      "{op} يستخدم مسجلات 32 بت كعنوان في كود 64 بت",
      "In 64-bit programs addresses are 64 bits wide. A 32-bit register keeps only the low half of a pointer, "
      "so the instruction reads the wrong memory (usually an access violation).",
      "في برامج 64 بت العناوين بطول 64 بت. المسجل ذو الـ 32 بت يحمل النصف المنخفض فقط من المؤشر، فتقرأ التعليمة "
      "مكاناً خاطئاً في الذاكرة (وغالباً يحدث Access Violation).",
      "Use the 64-bit registers inside [ ]: {hint}.",
      "استخدم مسجلات 64 بت داخل [ ]: {hint}.", lesson="08-arrays")
_rule("ASM120", "warning", "operands", "address-in-small-register",
      "The address of '{sym}' does not fit in {reg}",
      "عنوان '{sym}' لا يتسع في {reg}",
      "In NASM / FASM a bare label is its ADDRESS, not the value stored there. Addresses are {abits} bits wide "
      "in this program, so a {rbits}-bit register keeps only part of it.",
      "في NASM و FASM الاسم وحده يعني عنوانه وليس القيمة المخزنة فيه. العناوين بطول {abits} بت في هذا البرنامج، "
      "فالمسجل ذو الـ {rbits} بت يحمل جزءاً منها فقط.",
      "To read the value write [{sym}] with a size; to get the address use {hint}.",
      "لقراءة القيمة اكتب [{sym}] مع الحجم؛ وللحصول على العنوان استخدم {hint}.", lesson="04-data")
_rule("ASM121", "warning", "operands", "segment-override-misuse",
      "{what}",
      "{what_ar}",
      "A segment override (es: fs: ...) only changes which segment a MEMORY operand uses. In 64-bit mode the CS, "
      "DS, ES and SS overrides are ignored (all of them start at 0); only FS and GS still work.",
      "تغيير المقطع (es: أو fs: ...) يغيّر فقط المقطع الذي يستخدمه معامل الذاكرة. في وضع 64 بت يتم تجاهل CS و DS "
      "و ES و SS (كلها تبدأ من الصفر)، ويبقى FS و GS فقط.",
      "Remove the override, or put it on a memory operand: mov al, es:[di].",
      "احذف تغيير المقطع، أو ضعه على معامل ذاكرة: mov al, es:[di].")
_rule("ASM122", "info", "operands", "bp-uses-stack-segment",
      "{op} is based on BP, so it uses the stack segment SS (not DS)",
      "{op} مبني على BP، لذلك يستخدم مقطع المكدس SS وليس DS",
      "In 16-bit code every address that contains BP is taken from SS by default. When SS is not equal to DS "
      "(EXE programs) this reads the stack instead of your variable.",
      "في كود 16 بت أي عنوان يحتوي BP يُؤخذ من المقطع SS افتراضياً. وعندما لا يساوي SS المقطع DS (برامج EXE) "
      "تقرأ التعليمة من المكدس بدلاً من متغيرك.",
      "Use BX, SI or DI to index data, or write ds: before the address.",
      "استخدم BX أو SI أو DI لفهرسة البيانات، أو اكتب ds: قبل العنوان.", lesson="13-emu8086")
_rule("ASM123", "warning", "operands", "shift-count-too-large",
      "Shifting a {bits}-bit operand by {count} {what}",
      "إزاحة معامل حجمه {bits} بت بمقدار {count} {what_ar}",
      "The CPU keeps only the low 5 bits of the count (6 bits for 64-bit operands), so a count of {bits} or more "
      "is reduced modulo 32 / 64 instead of clearing the value.",
      "المعالج يحتفظ بأقل 5 بتات فقط من عدد الإزاحة (6 بتات لمعاملات 64 بت)، فالعدد {bits} أو أكثر يُختصر بباقي "
      "القسمة على 32 أو 64 بدلاً من أن يصفّر القيمة.",
      "Use a count smaller than {bits}, or clear the register with xor / mov 0 if that is what you want.",
      "استخدم عدداً أصغر من {bits}، أو صفّر المسجل بـ xor أو mov 0 إن كان هذا هو المقصود.", lesson="05-arithmetic")
_rule("ASM124", "info", "operands", "useless-instruction",
      "{what}",
      "{what_ar}",
      "The instruction does not change anything, which usually means a typo (the wrong register).",
      "هذه التعليمة لا تغيّر شيئاً، وهذا يعني غالباً خطأً في الكتابة (مسجل خطأ).",
      "Check which register you meant, or delete the line.",
      "تأكد من المسجل الذي تقصده، أو احذف السطر.")
_rule("ASM125", "error", "operands", "dos-interrupt-in-windows",
      "int {num} is a {what} service: it does not work in a {kind} program",
      "المقاطعة int {num} خدمة {what_ar}: لا تعمل في برنامج {kind}",
      "Interrupt services belong to an operating system: INT 21h / 10h / 16h are DOS and BIOS (16-bit real "
      "mode); INT 80h is 32-bit Linux. A Windows program that executes them is stopped with an access "
      "violation.",
      "خدمات المقاطعات تتبع نظام تشغيل معيناً: INT 21h و 10h و 16h خاصة بـ DOS و BIOS (وضع 16 بت الحقيقي)، و "
      "INT 80h خاصة بلينكس 32 بت. وبرنامج ويندوز الذي ينفذها يتوقف بخطأ Access Violation.",
      "In Windows programs call the C runtime (printf, puts, getchar) or the Win32 API (WriteConsoleA, "
      "ExitProcess). For DOS programs create an 8086 Assembly (Emulator) project.",
      "في برامج ويندوز استدعِ دوال لغة C (printf و puts و getchar) أو واجهة Win32 (WriteConsoleA و ExitProcess). "
      "ولبرامج DOS أنشئ مشروع ‎8086 Assembly (Emulator)‎.", topic="dos", lesson="11-c-winapi")

# ============================================================================ symbols
_rule("ASM201", "error", "symbols", "undefined-label",
      "'{name}' is not defined",
      "'{name}' غير معرّف",
      "The jump / call target is not a label of this program, an external symbol or a known function, so the "
      "assembler (or the linker) cannot find its address.",
      "هدف القفز أو الاستدعاء ليس عنواناً (label) في هذا البرنامج ولا رمزاً خارجياً ولا دالة معروفة، فلا يستطيع "
      "المجمّع (أو الرابط) إيجاد عنوانه.",
      "Check the spelling (labels are case-sensitive in NASM, FASM and GNU as) or define the label{near}.",
      "تأكد من الإملاء (الأسماء حساسة لحالة الحروف في NASM و FASM و GNU as) أو عرّف العنوان{near_ar}.",
      lesson="06-flags-jumps")
_rule("ASM202", "error", "symbols", "missing-extern",
      "'{name}' is used but not declared {kw}",
      "'{name}' مستخدم لكنه غير معلن بـ {kw}",
      "{name} lives outside this file ({where}). NASM / MASM need to be told that the name is external, "
      "otherwise they report an undefined symbol.",
      "الدالة {name} موجودة خارج هذا الملف ({where_ar}). يجب إخبار NASM / MASM أن هذا الاسم خارجي، وإلا ظهر خطأ "
      "رمز غير معرّف.",
      "Add the declaration near the top of the file: {decl}.",
      "أضف الإعلان قرب بداية الملف: {decl}.", lesson="11-c-winapi")
_rule("ASM203", "error", "symbols", "duplicate-label",
      "'{name}' is already defined at line {first}",
      "'{name}' معرّف من قبل في السطر {first}",
      "Every label names one address. Two definitions with the same name are ambiguous: the assembler stops "
      "with a 'symbol redefined' error.",
      "كل عنوان (label) يسمّي مكاناً واحداً. تعريفان بنفس الاسم يسببان التباساً، فيتوقف المجمّع بخطأ إعادة تعريف "
      "الرمز.",
      "Rename one of them (for loops inside a function NASM / FASM local labels such as .loop help).",
      "غيّر اسم أحدهما (وللحلقات داخل الدالة تفيد العناوين المحلية في NASM و FASM مثل ‎.loop).",
      lesson="07-loops")
_rule("ASM204", "error", "symbols", "jump-to-data",
      "{mnem} jumps to '{name}', which is data, not code",
      "التعليمة {mnem} تقفز إلى '{name}' وهو بيانات وليس كوداً",
      "'{name}' is defined with a data directive ({directive}). Jumping there makes the CPU execute your data "
      "bytes as if they were instructions.",
      "'{name}' معرّف بتوجيه بيانات ({directive}). القفز إليه يجعل المعالج ينفذ بايتات البيانات كأنها تعليمات.",
      "Jump to a code label. To call through a pointer stored in a variable write call [{name}].",
      "اقفز إلى عنوان كود. وللاستدعاء عبر مؤشر مخزن في متغير اكتب call [{name}].", lesson="06-flags-jumps")
_rule("ASM205", "warning", "symbols", "write-to-readonly",
      "'{name}' is in a read-only section ({section}): writing to it crashes",
      "'{name}' في قسم للقراءة فقط ({section}): الكتابة فيه تسبب توقف البرنامج",
      "The operating system loads code and constant sections as read-only memory. Writing into '{name}' raises "
      "an access violation at run time.",
      "نظام التشغيل يحمّل أقسام الكود والثوابت كذاكرة للقراءة فقط. الكتابة في '{name}' تسبب خطأ Access Violation "
      "أثناء التشغيل.",
      "Move the variable into a writable section: section .data (NASM), .data (MASM), section '.data' data "
      "readable writeable (FASM).",
      "انقل المتغير إلى قسم قابل للكتابة: section .data في NASM أو ‎.data في MASM أو section '.data' data readable "
      "writeable في FASM.", lesson="04-data")
_rule("ASM206", "info", "symbols", "nasm-default-rel",
      "64-bit addresses of variables are absolute: add 'default rel'",
      "عناوين المتغيرات في كود 64 بت مطلقة: أضف 'default rel'",
      "Without 'default rel', NASM encodes [variable] as a 32-bit absolute address. 64-bit Windows programs "
      "can be loaded above 4 GB, and the linker then fails with 'relocation truncated' or the program crashes.",
      "بدون 'default rel' يرمّز NASM العنوان [variable] كعنوان مطلق بحجم 32 بت. برامج ويندوز 64 بت قد تُحمّل فوق "
      "4 جيجابايت، فيفشل الرابط برسالة relocation truncated أو يتوقف البرنامج.",
      "Put 'default rel' at the top of the file (or write [rel variable]).",
      "ضع 'default rel' في أول الملف (أو اكتب [rel variable]).", topic="nasm", lesson="04-data")
_rule("ASM207", "warning", "symbols", "executes-data",
      "Execution runs into the data '{name}'",
      "التنفيذ يصل إلى البيانات '{name}'",
      "The instruction before the data does not jump away or return, so the CPU continues with the next bytes "
      "- your data - and executes them as random instructions.",
      "التعليمة التي قبل البيانات لا تقفز ولا ترجع، فيكمل المعالج بالبايتات التالية (وهي بياناتك) وينفذها كتعليمات "
      "عشوائية.",
      "End the code first (ret, jmp, or the exit call), or move the data into a data section / after the "
      "program's exit.",
      "أنهِ الكود أولاً (ret أو jmp أو استدعاء الخروج)، أو انقل البيانات إلى قسم البيانات أو بعد خروج البرنامج.",
      lesson="04-data")

# ============================================================================ control flow
_rule("ASM301", "warning", "flow", "unreachable-code",
      "This code can never run (it follows {after})",
      "هذا الكود لن يُنفذ أبداً (لأنه يأتي بعد {after})",
      "The instruction before it always jumps away, returns or ends the program, and no label here is the "
      "target of a jump, so the CPU never gets to these lines.",
      "التعليمة التي قبله تقفز دائماً أو ترجع أو تنهي البرنامج، ولا يوجد هنا عنوان يقفز إليه أحد، فلا يصل المعالج "
      "إلى هذه الأسطر أبداً.",
      "Delete the code, or add a label and jump to it, or move it before the jump / return.",
      "احذف الكود، أو أضف عنواناً واقفز إليه، أو انقله قبل القفز أو الرجوع.", lesson="06-flags-jumps")
_rule("ASM302", "warning", "flow", "missing-return",
      "{where}: execution falls off the end without {need}",
      "{where_ar}: التنفيذ يتجاوز النهاية بدون {need_ar}",
      "When the last instruction is not a RET / JMP / exit call, the CPU simply continues with whatever bytes "
      "follow in memory (other code, data or garbage) - a classic cause of crashes.",
      "عندما لا تكون آخر تعليمة RET أو JMP أو استدعاء خروج، يكمل المعالج ببساطة بالبايتات التي بعدها في الذاكرة "
      "(كود آخر أو بيانات أو قيم عشوائية)، وهذا سبب شائع لتوقف البرامج.",
      "End the procedure with {need}.",
      "أنهِ الإجراء بـ {need}.", lesson="09-stack-procedures")
_rule("ASM303", "warning", "flow", "falls-into-next-procedure",
      "'{name}' does not return: execution continues into '{next}'",
      "'{name}' لا يرجع: التنفيذ يكمل داخل '{next}'",
      "There is no RET or JMP at the end of '{name}', so after its last line the CPU runs the code of '{next}' "
      "as if it was part of it.",
      "لا توجد RET أو JMP في نهاية '{name}'، فبعد آخر سطر فيه ينفذ المعالج كود '{next}' كأنه جزء منه.",
      "Add ret (or the jump you meant) at the end of '{name}'.",
      "أضف ret (أو القفزة المقصودة) في نهاية '{name}'.", lesson="09-stack-procedures")
_rule("ASM304", "error", "flow", "stack-not-balanced",
      "The stack is not balanced at {mnem}: {what}",
      "المكدس غير متوازن عند {mnem}: {what_ar}",
      "RET takes the return address from the top of the stack. If more was pushed than popped (or less), RET "
      "jumps to a wrong address and the program crashes.",
      "التعليمة RET تأخذ عنوان الرجوع من قمة المكدس. إذا دُفع أكثر مما سُحب (أو أقل)، تقفز RET إلى عنوان خاطئ "
      "ويتوقف البرنامج.",
      "Pop everything you pushed (in reverse order) and undo every sub rsp / esp before the return.",
      "اسحب كل ما دفعته (بالترتيب العكسي) وألغِ كل sub rsp / esp قبل الرجوع.", lesson="09-stack-procedures")
_rule("ASM305", "warning", "flow", "stack-depth-differs",
      "The stack depth differs between the paths that reach here ({a} vs {b} bytes)",
      "عمق المكدس مختلف بين المسارات التي تصل إلى هنا ({a} مقابل {b} بايت)",
      "One path pushes (or pops) more than the other. After this point the program cannot know where its saved "
      "values and its return address are - in a loop the stack grows every turn.",
      "أحد المسارات يدفع (أو يسحب) أكثر من الآخر. بعد هذه النقطة لا يعرف البرنامج أين قيمه المحفوظة وعنوان رجوعه "
      "- وفي الحلقة يكبر المكدس مع كل دورة.",
      "Make every path push and pop the same amount (a PUSH inside a loop needs a POP inside the loop too).",
      "اجعل كل المسارات تدفع وتسحب نفس الكمية (PUSH داخل الحلقة تحتاج POP داخل الحلقة أيضاً).",
      lesson="09-stack-procedures")
_rule("ASM306", "warning", "flow", "pop-without-push",
      "{mnem} takes more from the stack than this procedure pushed",
      "التعليمة {mnem} تسحب من المكدس أكثر مما دفعه هذا الإجراء",
      "The value on top of the stack here is the return address (or the caller's data). Popping it destroys "
      "the way back, so the next RET jumps somewhere wrong.",
      "القيمة الموجودة في قمة المكدس هنا هي عنوان الرجوع (أو بيانات المستدعي). سحبها يضيّع طريق العودة، فتقفز RET "
      "التالية إلى مكان خاطئ.",
      "Pop only what this procedure pushed, in reverse order.",
      "اسحب فقط ما دفعه هذا الإجراء، وبالترتيب العكسي.", lesson="09-stack-procedures")
_rule("ASM307", "warning", "flow", "jump-without-flags",
      "{mnem} tests {flags}, but {prev} does not set the flags",
      "التعليمة {mnem} تختبر {flags} لكن {prev} لا تغيّر الأعلام",
      "Conditional jumps look at the flags left by the last arithmetic / compare instruction. {prev_up} does not "
      "change any flag, so {mnem} decides based on an older, unrelated result.",
      "القفزات الشرطية تنظر إلى الأعلام التي تركتها آخر تعليمة حسابية أو مقارنة. التعليمة {prev_up} لا تغيّر أي "
      "علم، فتقرر {mnem} بناءً على نتيجة قديمة لا علاقة لها.",
      "Compare first: {hint}.",
      "قارن أولاً: {hint}.", lesson="06-flags-jumps")
_rule("ASM308", "warning", "flow", "jump-on-undefined-flags",
      "{mnem} tests {flags}, which {prev} leaves undefined",
      "التعليمة {mnem} تختبر {flags} والتعليمة {prev} تترك هذه الأعلام غير معرّفة",
      "After {prev_up} the value of {flags} is undefined (it can be anything, and differs between CPUs), so the "
      "jump is random.",
      "بعد {prev_up} تكون قيمة {flags} غير معرّفة (قد تكون أي شيء وتختلف بين المعالجات)، فيصبح القفز عشوائياً.",
      "Test the result explicitly before the jump: {hint}.",
      "اختبر النتيجة صراحة قبل القفز: {hint}.", lesson="06-flags-jumps")
_rule("ASM309", "info", "flow", "signed-unsigned-jump",
      "{mnem} is a {kind} jump, but {what}",
      "التعليمة {mnem} قفزة {kind_ar}، لكن {what_ar}",
      "JL / JG / JLE / JGE compare as signed numbers (they read SF and OF); JB / JA / JBE / JAE compare as unsigned "
      "numbers (they read CF). Addresses and sizes are unsigned; values that can be negative are signed.",
      "التعليمات JL و JG و JLE و JGE تقارن كأرقام بإشارة (تقرأ SF و OF)، والتعليمات JB و JA و JBE و JAE تقارن كأرقام "
      "بدون إشارة (تقرأ CF). العناوين والأحجام بدون إشارة، والقيم التي قد تكون سالبة بإشارة.",
      "Use {better} instead of {mnem}.",
      "استخدم {better} بدلاً من {mnem}.", lesson="06-flags-jumps")
_rule("ASM310", "warning", "flow", "carry-not-set-by-inc",
      "{mnem} tests CF, but {prev} does not change CF",
      "التعليمة {mnem} تختبر CF لكن {prev} لا تغيّر CF",
      "INC and DEC set ZF / SF / OF but deliberately leave the carry flag unchanged, so {mnem} sees the carry of "
      "an older instruction.",
      "التعليمتان INC و DEC تغيّران ZF و SF و OF لكنهما تتركان علم الحمل CF بدون تغيير عمداً، فترى {mnem} الحمل "
      "الخاص بتعليمة أقدم.",
      "Use add / sub 1 (they set CF), or test ZF / SF with jz / js.",
      "استخدم add أو sub بالقيمة 1 (تغيّران CF)، أو اختبر ZF أو SF بـ jz أو js.", lesson="06-flags-jumps")

# ============================================================================ data flow
_rule("ASM401", "warning", "data", "register-used-before-set",
      "{reg} is used before it gets a value",
      "المسجل {reg} مستخدم قبل أن يأخذ قيمة",
      "{reg} was never written since the program started{path}, so it holds whatever the loader or the "
      "operating system left there - the result changes from run to run.",
      "لم تُكتب أي قيمة في {reg} منذ بداية البرنامج{path_ar}، فهو يحتوي ما تركه المحمّل أو نظام التشغيل - والنتيجة "
      "تتغير من تشغيل لآخر.",
      "Give {reg} a value first (mov {reg}, ... or xor {reg}, {reg} for zero).",
      "أعطِ {reg} قيمة أولاً (mov {reg}, ... أو xor {reg}, {reg} للتصفير).", lesson="03-registers-memory")
_rule("ASM402", "warning", "data", "register-clobbered-by-call",
      "{reg} was changed by the call to '{callee}' (line {line})",
      "المسجل {reg} تغيّر بسبب استدعاء '{callee}' (السطر {line})",
      "{reason} Reading {reg} after the call gets whatever value the called code left there, not your value.",
      "{reason_ar} وقراءة {reg} بعد الاستدعاء تعطي القيمة التي تركها الكود المستدعى، وليس قيمتك.",
      "Keep the value in a register that survives calls ({keep}), or save it: push before the call and pop "
      "after it (or store it in a variable).",
      "احفظ القيمة في مسجل لا يتغير مع الاستدعاءات ({keep})، أو احفظها: push قبل الاستدعاء و pop بعده (أو خزنها "
      "في متغير).", lesson="09-stack-procedures")
_rule("ASM403", "warning", "data", "div-without-extend",
      "{mnem} divides {pair}, but {high} {state}",
      "التعليمة {mnem} تقسم {pair} لكن {high} {state_ar}",
      "{mnem} divides the double-size value {pair}, not just {low}. If {high} holds garbage the quotient is "
      "wrong or too big, and the CPU raises a divide error (the program crashes with 'integer overflow').",
      "التعليمة {mnem} تقسم القيمة المضاعفة {pair} وليس {low} فقط. إذا كان في {high} قيمة عشوائية تصبح النتيجة "
      "خاطئة أو كبيرة جداً، فيرفع المعالج خطأ القسمة (يتوقف البرنامج بخطأ integer overflow).",
      "Before {mnem} write {fixins}.",
      "قبل {mnem} اكتب {fixins}.", lesson="05-arithmetic")
_rule("ASM404", "error", "data", "divide-by-zero",
      "Division by zero: {reg} is 0 here",
      "قسمة على صفر: قيمة {reg} هنا تساوي 0",
      "The divisor {reg} was set to 0 (line {line}). Dividing by zero raises a CPU exception and the program "
      "stops.",
      "المقسوم عليه {reg} أُعطي القيمة 0 (السطر {line}). القسمة على صفر ترفع استثناءً في المعالج ويتوقف البرنامج.",
      "Put the real divisor in {reg} before the division.",
      "ضع المقسوم عليه الصحيح في {reg} قبل القسمة.", lesson="05-arithmetic")
_rule("ASM405", "warning", "data", "counter-not-set",
      "{mnem} uses {reg} as the counter, but {reg} {state}",
      "التعليمة {mnem} تستخدم {reg} كعدّاد، لكن {reg} {state_ar}",
      "{mnem} counts with {reg}: {how}. A counter that was never set (or is 0) makes it run a random number of "
      "times - with 0, LOOP runs {wrap} times.",
      "التعليمة {mnem} تعدّ بالمسجل {reg}: {how_ar}. العدّاد الذي لم يُضبط (أو قيمته 0) يجعلها تتكرر عدداً عشوائياً "
      "من المرات - ومع الصفر تتكرر LOOP عدد {wrap} مرة.",
      "Set the count before the loop: mov {reg}, N.",
      "اضبط العدد قبل الحلقة: mov {reg}, N.", lesson="07-loops")
_rule("ASM406", "warning", "data", "direction-flag-set",
      "{mnem} runs with the direction flag possibly set by STD (line {line})",
      "التعليمة {mnem} تعمل وعلم الاتجاه قد يكون مضبوطاً بـ STD (السطر {line})",
      "After STD the string instructions walk BACKWARDS through memory (SI / DI decrease). Calling other code "
      "with DF=1 also breaks it: every calling convention requires DF=0.",
      "بعد STD تمشي تعليمات النصوص إلى الخلف في الذاكرة (SI و DI تتناقص). واستدعاء كود آخر و DF=1 يفسده أيضاً، "
      "فكل اتفاقيات الاستدعاء تشترط DF=0.",
      "Write cld after the backwards copy (and before any call or return).",
      "اكتب cld بعد النسخ العكسي (وقبل أي استدعاء أو رجوع).", lesson="10-strings")
_rule("ASM407", "info", "data", "string-without-cld",
      "{mnem} depends on the direction flag, which this procedure never sets",
      "التعليمة {mnem} تعتمد على علم الاتجاه، وهذا الإجراء لا يضبطه أبداً",
      "Whether SI / DI go forwards or backwards depends on DF. In 16-bit DOS code nothing guarantees DF=0 when "
      "a procedure is entered.",
      "اتجاه حركة SI و DI (للأمام أو للخلف) يعتمد على العلم DF. وفي كود DOS ذي الـ 16 بت لا يوجد ما يضمن أن DF=0 "
      "عند الدخول إلى الإجراء.",
      "Write cld before the first string instruction.",
      "اكتب cld قبل أول تعليمة نصوص.", lesson="10-strings")
_rule("ASM408", "info", "data", "idiv-after-zero-extend",
      "IDIV is a signed division, but {high} was cleared with zero",
      "IDIV قسمة بإشارة، لكن {high} صُفّر",
      "For a negative dividend the high half must be all ones (the sign repeated), not zero. Clearing {high} "
      "turns a negative number into a huge positive one.",
      "إذا كان المقسوم سالباً يجب أن يكون النصف العلوي كله وحدات (تكرار الإشارة) وليس صفراً. تصفير {high} يحوّل "
      "الرقم السالب إلى رقم موجب ضخم.",
      "Use {ext} instead of clearing {high} (it copies the sign of {low} into {high}).",
      "استخدم {ext} بدلاً من تصفير {high} (تنسخ إشارة {low} إلى {high}).", lesson="05-arithmetic")

_rule("ASM409", "error", "data", "divide-overflow",
      "{mnem} overflows: {high} = {hv} is not smaller than the divisor {dv}",
      "التعليمة {mnem} ستفيض: {high} = {hv} ليس أصغر من المقسوم عليه {dv}",
      "The quotient of {pair} / divisor must fit in {low}. When the high half {high} is already greater than or "
      "equal to the divisor, the quotient is too big and the CPU raises a divide error - the same crash as "
      "dividing by zero.",
      "ناتج قسمة {pair} على المقسوم عليه يجب أن يتسع في {low}. وعندما يكون النصف العلوي {high} أكبر من أو يساوي "
      "المقسوم عليه يصبح الناتج كبيراً جداً فيرفع المعالج خطأ القسمة - نفس توقف القسمة على صفر.",
      "Clear {high} before an unsigned DIV (xor), or sign-extend with CWD / CDQ / CQO before IDIV.",
      "صفّر {high} قبل DIV بدون إشارة (xor)، أو وسّع الإشارة بـ CWD أو CDQ أو CQO قبل IDIV.", lesson="05-arithmetic")

# ============================================================================ calling conventions
_rule("ASM501", "warning", "abi", "win64-shadow-space",
      "The call to '{callee}' has no 32-byte shadow space ({have} bytes reserved)",
      "استدعاء '{callee}' بدون مساحة الظل 32 بايت (المحجوز {have} بايت فقط)",
      "The Microsoft x64 convention lets every called function use the 32 bytes just above the return address "
      "(the 'shadow space'). If the caller did not reserve them, the function overwrites your saved registers "
      "or your return address.",
      "اتفاقية الاستدعاء في ويندوز 64 بت تسمح لكل دالة مستدعاة باستخدام الـ 32 بايت التي فوق عنوان الرجوع مباشرة "
      "(مساحة الظل). إذا لم يحجزها المستدعي تكتب الدالة فوق مسجلاتك المحفوظة أو فوق عنوان الرجوع.",
      "Reserve the space before the call: sub rsp, 40 at the start (32 shadow + 8 to keep RSP 16-byte aligned), "
      "add rsp, 40 before ret.",
      "احجز المساحة قبل الاستدعاء: sub rsp, 40 في البداية (32 للظل + 8 لضبط محاذاة RSP على 16)، و add rsp, 40 "
      "قبل ret.", topic="win64", lesson="09-stack-procedures")
_rule("ASM502", "warning", "abi", "stack-misaligned",
      "RSP is not 16-byte aligned at the call to '{callee}' (it is {mod} bytes off)",
      "المسجل RSP غير محاذى على 16 بايت عند استدعاء '{callee}' (منحرف بمقدار {mod} بايت)",
      "{conv} requires RSP to be a multiple of 16 at every CALL. Functions such as printf use aligned SSE "
      "instructions and crash (or print garbage) when the stack is misaligned.",
      "{conv_ar} تشترط أن يكون RSP من مضاعفات 16 عند كل CALL. ودوال مثل printf تستخدم تعليمات SSE تحتاج المحاذاة، "
      "فتتوقف (أو تطبع قيماً خاطئة) إذا كان المكدس غير محاذى.",
      "Adjust the stack by 8 more (or less) bytes: on entry RSP is 8 bytes off, so push rbp / sub rsp, 32 "
      "or sub rsp, 40 keep it aligned.",
      "عدّل المكدس بمقدار 8 بايت إضافية (أو أقل): عند الدخول يكون RSP منحرفاً 8 بايت، لذلك push rbp ثم sub rsp, 32 "
      "أو sub rsp, 40 تحافظ على المحاذاة.", topic="win64", lesson="09-stack-procedures")
_rule("ASM503", "warning", "abi", "callee-saved-clobbered",
      "'{proc}' changes {reg} without saving it",
      "'{proc}' يغيّر {reg} بدون حفظه",
      "{reg} is callee-saved in the {conv} convention: whoever calls '{proc}' (the C runtime, Windows, another "
      "function) expects to find its old value after the return.",
      "المسجل {reg} من المسجلات التي يحفظها المستدعى في اتفاقية {conv}: من يستدعي '{proc}' (مكتبة C أو ويندوز أو "
      "دالة أخرى) يتوقع أن يجد قيمته القديمة بعد الرجوع.",
      "push {reg} at the start of '{proc}' and pop {reg} before each ret (or use a volatile register such as "
      "{alt}).",
      "اكتب push {reg} في بداية '{proc}' و pop {reg} قبل كل ret (أو استخدم مسجلاً متطايراً مثل {alt}).",
      topic="win64", lesson="09-stack-procedures")
_rule("ASM504", "warning", "abi", "api-argument-not-set",
      "Argument {n} of {api} ({param}) goes in {loc}, which is not set before the call",
      "الوسيط رقم {n} للدالة {api} ‏({param}) يوضع في {loc}، ولم يُضبط قبل الاستدعاء",
      "{conv} {api} reads {loc} as its argument number {n}; without a value it uses garbage left by earlier "
      "code (often the previous call).",
      "{conv_ar} تقرأ الدالة {api} القيمة من {loc} كوسيطها رقم {n}؛ وبدون قيمة تستخدم ما تركه كود سابق (غالباً "
      "الاستدعاء السابق).",
      "Set {loc} before the call: {sig}.",
      "اضبط {loc} قبل الاستدعاء: {sig}.", topic="win64", lesson="11-c-winapi")
_rule("ASM505", "warning", "abi", "api-push-count",
      "{api} takes {n} argument(s) but {pushed} value(s) are pushed before the call",
      "الدالة {api} تأخذ {n} وسيط/وسائط لكن تم دفع {pushed} قيمة قبل الاستدعاء",
      "In 32-bit code arguments are pushed right to left. A missing or extra push shifts every argument and "
      "{cleanup}",
      "في كود 32 بت تُدفع الوسائط من اليمين لليسار. الدفعة الناقصة أو الزائدة تزيح كل الوسائط و{cleanup_ar}",
      "Push exactly the arguments of {sig}.",
      "ادفع الوسائط تماماً كما في {sig}.", topic="x86", lesson="11-c-winapi")
_rule("ASM506", "error", "abi", "stdcall-double-cleanup",
      "{api} is stdcall: it already removed its {bytes} bytes of arguments",
      "الدالة {api} من نوع stdcall: لقد أزالت وسائطها ({bytes} بايت) بنفسها",
      "Win32 API functions use stdcall: they end with ret {bytes}, removing their own arguments. Adding to ESP "
      "again removes your own data (saved registers, the return address) from the stack.",
      "دوال واجهة Win32 تستخدم stdcall: تنتهي بـ ret {bytes} فتزيل وسائطها بنفسها. وإضافة قيمة إلى ESP مرة أخرى "
      "تزيل بياناتك أنت من المكدس (المسجلات المحفوظة وعنوان الرجوع).",
      "Delete this add esp, {bytes} line.",
      "احذف السطر add esp, {bytes}.", topic="x86", lesson="11-c-winapi")
_rule("ASM507", "warning", "abi", "cdecl-missing-cleanup",
      "{api} is cdecl: the caller must remove its arguments (add esp, {bytes})",
      "الدالة {api} من نوع cdecl: المستدعي يجب أن يزيل وسائطها (add esp, {bytes})",
      "C runtime functions (printf, scanf, puts ...) use cdecl: they return with the arguments still on the "
      "stack. Without add esp the stack keeps growing and RET jumps to a wrong address.",
      "دوال مكتبة C (printf و scanf و puts ...) تستخدم cdecl: ترجع والوسائط ما زالت في المكدس. وبدون add esp يظل "
      "المكدس يكبر وتقفز RET إلى عنوان خاطئ.",
      "Write add esp, {bytes} right after the call.",
      "اكتب add esp, {bytes} بعد الاستدعاء مباشرة.", topic="x86", lesson="11-c-winapi")
_rule("ASM508", "info", "abi", "sysv-variadic-al",
      "{api} is variadic: set AL to the number of vector registers used (xor eax, eax)",
      "الدالة {api} متغيرة الوسائط: اضبط AL على عدد مسجلات المتجهات المستخدمة (xor eax, eax)",
      "The System V convention passes the number of XMM registers used by a variadic call in AL. Garbage in AL "
      "can make printf read random XMM registers or crash.",
      "اتفاقية System V تمرر في AL عدد مسجلات XMM المستخدمة في استدعاء الدوال متغيرة الوسائط. القيمة العشوائية في "
      "AL قد تجعل printf تقرأ مسجلات XMM عشوائية أو تتوقف.",
      "Write xor eax, eax before the call when no floating-point argument is passed.",
      "اكتب xor eax, eax قبل الاستدعاء إذا لم تمرر وسيطاً عشرياً.", topic="sysv", lesson="11-c-winapi")

_rule("ASM509", "warning", "abi", "value-instead-of-address",
      "Argument {n} of {api} ({param}) must be an address, but {loc} holds the contents of '{sym}'",
      "الوسيط رقم {n} للدالة {api} ‏({param}) يجب أن يكون عنواناً، لكن {loc} يحمل محتوى '{sym}'",
      "{param} is a pointer: {api} reads memory at the address in {loc}. 'mov {loc}, [{sym}]' loads the first "
      "bytes of the text (its value) instead of where it is, so the function reads a random address and usually "
      "crashes.",
      "{param} مؤشر: الدالة {api} تقرأ الذاكرة عند العنوان الموجود في {loc}. والتعليمة 'mov {loc}, [{sym}]' تحمّل "
      "أول بايتات النص (قيمته) بدلاً من مكانه، فتقرأ الدالة عنواناً عشوائياً وغالباً يتوقف البرنامج.",
      "Load the address with LEA: lea {loc}, [{sym}].",
      "حمّل العنوان بالتعليمة LEA: ‏lea {loc}, [{sym}].", topic="win64", lesson="04-data")

# ============================================================================ DOS / 8086
_rule("ASM601", "error", "dos", "ds-not-initialized",
      "DS is used before it is set to the data segment (mov ax, {seg} / mov ds, ax)",
      "المسجل DS مستخدم قبل ضبطه على مقطع البيانات (mov ax, {seg} ثم mov ds, ax)",
      "When DOS starts an EXE program, DS points to the PSP (the program's header), not to your .data segment. "
      "Every variable access then reads the wrong memory and strings print as garbage.",
      "عندما يبدأ DOS برنامج EXE يشير DS إلى الـ PSP (رأس البرنامج) وليس إلى مقطع البيانات ‎.data الخاص بك. فكل "
      "وصول لمتغير يقرأ ذاكرة خاطئة وتظهر النصوص كرموز عشوائية.",
      "Start the program with: mov ax, {seg} / mov ds, ax.",
      "ابدأ البرنامج بالسطرين: mov ax, {seg} ثم mov ds, ax.", topic="dos", lesson="13-emu8086")
_rule("ASM602", "warning", "dos", "missing-dos-exit",
      "The program does not end with a DOS exit (mov ah, 4Ch / int 21h)",
      "البرنامج لا ينتهي باستدعاء الخروج إلى DOS ‏(mov ah, 4Ch ثم int 21h)",
      "A DOS program must give control back to DOS. Without the exit call the CPU keeps executing the bytes after "
      "your code (usually your data) and the machine hangs.",
      "برنامج DOS يجب أن يعيد التحكم إلى DOS. وبدون استدعاء الخروج يكمل المعالج تنفيذ البايتات التي بعد كودك "
      "(غالباً بياناتك) فيتجمد الجهاز.",
      "End the program with mov ah, 4Ch / int 21h.",
      "أنهِ البرنامج بالسطرين mov ah, 4Ch ثم int 21h.", topic="dos", lesson="13-emu8086")
_rule("ASM603", "warning", "dos", "int21-ah-not-set",
      "AH is not set before int {num}: the service number is unknown",
      "المسجل AH غير مضبوط قبل int {num}: رقم الخدمة غير معروف",
      "INT {num} chooses the service by the value in AH. Without setting AH it runs whatever service number "
      "happens to be there.",
      "المقاطعة INT {num} تختار الخدمة حسب القيمة الموجودة في AH. وبدون ضبط AH تنفذ أي خدمة يصادف رقمها هناك.",
      "Put the service number in AH first: mov ah, 09h (print a string), mov ah, 4Ch (exit) ...",
      "ضع رقم الخدمة في AH أولاً: mov ah, 09h (طباعة نص)، mov ah, 4Ch (خروج) ...", topic="dos",
      lesson="13-emu8086")
_rule("ASM604", "info", "dos", "int21-unknown-function",
      "int 21h function AH={ah} is not a common DOS service",
      "الخدمة AH={ah} في int 21h ليست من خدمات DOS المعروفة",
      "The value in AH selects the DOS service. {ah} is not one of the usual services (01h read key, 02h print "
      "char, 09h print string, 0Ah read line, 4Ch exit ...), which often means a typo such as a missing h "
      "(4Ch, not 4C).",
      "القيمة في AH تختار خدمة DOS. والقيمة {ah} ليست من الخدمات المعتادة (01h قراءة مفتاح، 02h طباعة حرف، 09h طباعة "
      "نص، 0Ah قراءة سطر، 4Ch خروج ...)، وهذا يعني غالباً خطأ كتابة مثل نسيان حرف h في 4Ch.",
      "Check the number (hexadecimal numbers end with h: 09h, 4Ch).",
      "راجع الرقم (الأرقام السداسية عشرية تنتهي بالحرف h مثل 09h و 4Ch).", topic="dos", lesson="13-emu8086")
_rule("ASM605", "warning", "dos", "missing-dollar",
      "The string '{name}' printed with AH=09h has no '$' at the end",
      "النص '{name}' الذي يُطبع بالخدمة AH=09h لا ينتهي بالرمز '$'",
      "DOS function 09h prints characters until it finds a '$'. Without it, DOS keeps printing whatever memory "
      "follows the string (other variables, garbage) until a '$' happens to appear.",
      "خدمة DOS رقم 09h تطبع الحروف حتى تجد الرمز '$'. وبدونه يظل DOS يطبع ما بعد النص في الذاكرة (متغيرات أخرى "
      "أو قيم عشوائية) حتى يصادف '$'.",
      "End the string with '$': {name} db '...', '$'.",
      "أنهِ النص بالرمز '$': {name} db '...', '$'.", topic="dos", lesson="13-emu8086")
_rule("ASM606", "warning", "dos", "int21-dx-not-set",
      "int 21h function 09h prints the string at DS:DX, but DX is not set",
      "خدمة int 21h رقم 09h تطبع النص الموجود في DS:DX لكن DX غير مضبوط",
      "Function 09h takes the address of the string from DX. Without it DOS prints from a random address.",
      "الخدمة 09h تأخذ عنوان النص من DX. وبدونه يطبع DOS من عنوان عشوائي.",
      "Load the address first: mov dx, offset msg (MASM / emu8086) or mov dx, msg (NASM).",
      "حمّل العنوان أولاً: mov dx, offset msg في MASM و emu8086 أو mov dx, msg في NASM.", topic="dos",
      lesson="13-emu8086")

RULES: dict[str, Rule] = {r.id: r for r in _R}
BY_NAME: dict[str, Rule] = {r.name: r for r in _R}
SEVERITIES = ("error", "warning", "info")


def rule(key: str) -> Rule | None:
    """A rule by id (ASM101) or name (operand-size-mismatch)."""
    k = (key or "").strip()
    return RULES.get(k.upper()) or BY_NAME.get(k.lower())
