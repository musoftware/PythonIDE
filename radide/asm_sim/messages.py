"""Bilingual (English / Arabic) texts of the runtime checks (rule ids ``sim.*``).

Every rule has three parts in both languages:

* ``msg``  - one short line (the editor marker / Error List text);
* ``why``  - what happened inside the CPU, in plain words for a beginner;
* ``fix``  - a concrete change to make;

plus ``ref``: the instruction or topic that explains it (an asm_intel instruction name such as ``ret`` /
``div``, or a topic key of ``TOPICS``). Texts are original. ``{name}`` placeholders are filled by
``text(rule, part, lang, **args)``; a missing argument leaves the placeholder visible instead of failing.
"""
from __future__ import annotations

import string

RULES: dict[str, dict] = {
    # ------------------------------------------------------------------ stack
    "sim.stack_imbalance": {
        "severity": "error", "ref": "ret",
        "en": ("Stack not balanced at 'ret' of {proc}: {bytes} byte(s) {state}",
               "'ret' takes the return address from the top of the stack ([{sp}]). When {proc} started, the "
               "return address was at {sp_entry}; now {sp} = {sp_now}, so the CPU would return to {target} "
               "instead of the caller. Something was pushed and not popped (or 'sub {sp}' was not undone), or "
               "too much was popped.",
               "Make every 'push' have a matching 'pop' and undo 'sub {sp}, N' with 'add {sp}, N' (or 'leave') "
               "before 'ret'. Push count in this procedure: {pushes}, pop count: {pops}."),
        "ar": ("المكدس غير متوازن عند 'ret' في {proc}: {bytes} بايت {state_ar}",
               "التعليمة ret تأخذ عنوان الرجوع من قمة المكدس ([{sp}]). عند بداية {proc} كان عنوان الرجوع عند "
               "{sp_entry}، أما الآن فقيمة {sp} = {sp_now}، لذلك سيرجع المعالج إلى {target} بدلاً من الدالة التي "
               "استدعته. هذا يعني أن هناك push بلا pop مقابل (أو sub {sp} لم يُلغَ)، أو أن هناك pop زائداً.",
               "اجعل لكل push تعليمة pop مقابلة، وألغِ 'sub {sp}, N' بـ 'add {sp}, N' (أو leave) قبل ret. "
               "عدد push في هذا الإجراء: {pushes}، وعدد pop: {pops}."),
    },
    "sim.bad_return": {
        "severity": "error", "ref": "ret",
        "en": ("'ret' of {proc} would jump to {target} instead of back to the caller ({expected})",
               "The stack pointer is where it should be, but the return address stored there was overwritten "
               "(last write: line {writer_line}). Writing past the end of a local buffer, or storing to [{sp}+N] "
               "with the wrong N, destroys the return address.",
               "Check the writes into the stack in {proc}: local arrays must fit in the space reserved with "
               "'sub {sp}, N'; never write to the slot of the return address."),
        "ar": ("التعليمة ret في {proc} ستقفز إلى {target} بدلاً من الرجوع إلى المستدعي ({expected})",
               "مؤشر المكدس في مكانه الصحيح، لكن عنوان الرجوع المخزّن هناك تمت الكتابة فوقه (آخر كتابة: السطر "
               "{writer_line}). الكتابة بعد نهاية مصفوفة محلية، أو التخزين في [{sp}+N] بقيمة N خاطئة، يدمّر عنوان "
               "الرجوع.",
               "راجع الكتابات في المكدس داخل {proc}: يجب أن تتسع المصفوفات المحلية في المساحة المحجوزة بـ "
               "'sub {sp}, N'، ولا تكتب أبداً في خانة عنوان الرجوع."),
    },
    "sim.stack_overflow": {
        "severity": "error", "ref": "call",
        "en": ("Stack overflow: the stack grew past its {size} KB limit ({depth} nested calls)",
               "Every 'call' and 'push' uses stack space. A procedure that calls itself without a stop "
               "condition (or a loop that pushes without popping) uses it all up.",
               "Give the recursion a base case that returns without calling again, and make sure every loop "
               "iteration pops what it pushed."),
        "ar": ("فيضان المكدس: نما المكدس بعد حدّه البالغ {size} كيلوبايت ({depth} استدعاء متداخل)",
               "كل call وكل push يستهلك جزءاً من المكدس. الإجراء الذي يستدعي نفسه بلا شرط توقف (أو الحلقة التي "
               "تعمل push بلا pop) يستهلكه كله.",
               "ضع للاستدعاء الذاتي حالة أساس ترجع دون استدعاء جديد، وتأكد أن كل دورة في الحلقة تعمل pop لما "
               "عملت له push."),
    },
    "sim.callee_saved": {
        "severity": "warning", "ref": "abi",
        "en": ("{proc} changes {regs} and does not restore {them}",
               "The {abi} calling convention says {all_regs} belong to the caller: a procedure may use them "
               "only if it puts the old values back before 'ret'. The caller (for main: the C runtime) may "
               "still need them.",
               "Save them at the start ('push {first}') and restore them in reverse order before 'ret' "
               "('pop {first}'), or use registers the convention lets you change ({volatile})."),
        "ar": ("{proc} يغيّر {regs} ولا يعيد {them_ar} الأصلية",
               "اصطلاح الاستدعاء {abi} ينص على أن المسجلات {all_regs} ملك للمستدعي: يجوز للإجراء استخدامها فقط إذا "
               "أعاد قيمها القديمة قبل ret، لأن المستدعي (وفي حالة main: مكتبة C) قد يحتاجها بعد الرجوع.",
               "احفظها في البداية ('push {first}') واسترجعها بالترتيب العكسي قبل ret ('pop {first}')، أو استخدم "
               "مسجلات يسمح الاصطلاح بتغييرها ({volatile})."),
    },
    "sim.misaligned_call": {
        "severity": "warning", "ref": "abi",
        "en": ("{sp} is not 16-byte aligned at 'call {target}' ({sp} mod 16 = {mod})",
               "The 64-bit calling conventions require {sp} to be a multiple of 16 just before every 'call'. "
               "Library functions such as {target} use SSE instructions (movaps) that crash on a misaligned "
               "stack - sometimes only on another PC or Windows version.",
               "At the start of a procedure {sp} is 8 mod 16 (the return address). Make pushes*8 + 'sub {sp}, N' "
               "equal 8 mod 16: e.g. 'push rbp' + 'sub rsp, 32', or 'sub rsp, 40' without a push."),
        "ar": ("المسجل {sp} غير محاذٍ على 16 بايت عند 'call {target}' (باقي القسمة على 16 = {mod})",
               "اصطلاحات الاستدعاء في 64 بت تشترط أن تكون قيمة {sp} من مضاعفات 16 قبل كل call مباشرة. دوال المكتبة "
               "مثل {target} تستخدم تعليمات SSE (مثل movaps) تنهار عندما يكون المكدس غير محاذٍ - وأحياناً على جهاز "
               "أو إصدار ويندوز آخر فقط.",
               "في بداية الإجراء تكون {sp} = 8 (باقي 16) بسبب عنوان الرجوع. اجعل (عدد push × 8) + قيمة 'sub {sp}, N' "
               "يساوي 8 بباقي 16: مثلاً 'push rbp' ثم 'sub rsp, 32'، أو 'sub rsp, 40' بدون push."),
    },
    "sim.no_shadow_space": {
        "severity": "warning", "ref": "abi",
        "en": ("No 32-byte shadow space before 'call {target}'",
               "On Windows x64 the called function may use the 32 bytes above the return address ([rsp+8] .. "
               "[rsp+40]) as its own scratch space. Here those bytes cover {victim}, so {target} may overwrite it.",
               "Reserve the space before calling: 'sub rsp, 32' (or 40 to keep the alignment) after the pushes "
               "of the prologue, and 'add rsp, 32' / 'leave' at the end."),
        "ar": ("لا توجد مساحة ظل (shadow space) بحجم 32 بايت قبل 'call {target}'",
               "في ويندوز 64 بت يحق للدالة المستدعاة أن تستخدم الـ 32 بايت التي فوق عنوان الرجوع ([rsp+8] .. "
               "[rsp+40]) كمساحة عمل خاصة بها. هنا تغطي هذه البايتات {victim}، فقد تكتب {target} فوقها.",
               "احجز المساحة قبل الاستدعاء: 'sub rsp, 32' (أو 40 للحفاظ على المحاذاة) بعد push الموجودة في "
               "بداية الإجراء، ثم 'add rsp, 32' أو leave في النهاية."),
    },
    # ------------------------------------------------------------------ memory
    "sim.null_deref": {
        "severity": "error", "ref": "lea",
        "en": ("{access} address {addr} (a null pointer) in '{instr}'",
               "The first 64 KB of memory never belong to a program, so the CPU stops the program with an "
               "access violation. The address came from {regs}: a register that should hold an address held 0 "
               "or a small number. A classic cause is 'mov reg, [label]' (loads the VALUE stored at label) where "
               "'lea reg, [label]' (loads the ADDRESS) was meant.",
               "Make sure the register holds an address before using it in [ ]: 'lea {reg}, [variable]' (or "
               "'mov {reg}, variable' in 32-bit code), or check it for 0 first ('test {reg}, {reg}' / 'jz')."),
        "ar": ("{access_ar} العنوان {addr} (مؤشر فارغ null) في '{instr}'",
               "أول 64 كيلوبايت من الذاكرة لا تخص أي برنامج أبداً، لذلك يوقف المعالج البرنامج بخطأ وصول للذاكرة "
               "(Access Violation). العنوان جاء من {regs}: مسجل كان يفترض أن يحمل عنواناً لكنه يحمل صفراً أو رقماً "
               "صغيراً. سبب شائع: كتابة 'mov reg, [label]' (تحمّل القيمة المخزنة) بدلاً من 'lea reg, [label]' "
               "(تحمّل العنوان).",
               "تأكد أن المسجل يحمل عنواناً قبل استخدامه بين [ ]: 'lea {reg}, [variable]' (أو 'mov {reg}, variable' "
               "في 32 بت)، أو افحصه أولاً ('test {reg}, {reg}' ثم jz)."),
    },
    "sim.mem_violation": {
        "severity": "error", "ref": "mov",
        "en": ("{access} invalid address {addr} in '{instr}'",
               "No memory exists at {addr}: it is not inside the program's sections, its stack or its heap. The "
               "address was computed from {regs}. An index that grew too big, a pointer that was never set, or "
               "a value used as an address are the usual causes.",
               "Look at the registers inside [ ] at this line (Explain this line shows them) and trace back where "
               "they got their values; compare the index with the size of the array before the access."),
        "ar": ("{access_ar} عنواناً غير صالح {addr} في '{instr}'",
               "لا توجد ذاكرة عند {addr}: فهو ليس داخل أقسام البرنامج ولا المكدس ولا الكومة (heap). العنوان حُسب من "
               "{regs}. الأسباب المعتادة: فهرس كبر أكثر من اللازم، أو مؤشر لم يُضبط أبداً، أو قيمة استُخدمت كعنوان.",
               "انظر إلى المسجلات داخل [ ] في هذا السطر ('اشرح هذا السطر' يعرضها) وتتبّع من أين أخذت قيمها؛ وقارن "
               "الفهرس بحجم المصفوفة قبل الوصول."),
    },
    "sim.write_readonly": {
        "severity": "error", "ref": "section",
        "en": ("Write to read-only memory at {addr} ({where}) in '{instr}'",
               "{where} is in the section {section}, which the program may only read{why_extra}. Windows marks "
               "code and constant data read-only, so this write crashes the program.",
               "Put data you want to change in 'section .data' (initialised) or 'section .bss' (reserved), not in "
               "'.text' / '.rdata'."),
        "ar": ("كتابة في ذاكرة للقراءة فقط عند {addr} ({where}) في '{instr}'",
               "{where} موجود في القسم {section} الذي يسمح للبرنامج بالقراءة فقط{why_extra_ar}. ويندوز يجعل الكود "
               "والبيانات الثابتة للقراءة فقط، لذلك تنهار هذه الكتابة البرنامج.",
               "ضع البيانات التي ستغيّرها في 'section .data' (بقيمة أولية) أو 'section .bss' (محجوزة)، وليس في "
               "‎.text‎ أو ‎.rdata‎."),
    },
    "sim.buffer_overflow": {
        "severity": "error", "ref": "times",
        "en": ("Write past the end of '{label}': {target} is {past} byte(s) after its last byte "
               "('{label}' has {size} byte(s)){victim_en}",
               "'{label}' was reserved with {size} byte(s) (line {label_line}), but this instruction writes at "
               "offset {offset}. In assembly nothing checks array bounds: the write lands on whatever comes next "
               "in memory{victim_why}.",
               "Make the loop stop at the size of the array (e.g. 'cmp {index}, {count}' / 'jae done' before the "
               "write), or reserve more room ('{label} times N db 0' / 'resb N')."),
        "ar": ("كتابة بعد نهاية '{label}': العنوان {target} يقع بعد آخر بايت فيها بـ {past} بايت "
               "(حجم '{label}' هو {size} بايت){victim_ar}",
               "حُجز '{label}' بحجم {size} بايت (السطر {label_line})، لكن هذه التعليمة تكتب عند الإزاحة {offset}. "
               "في الأسمبلي لا يوجد ما يفحص حدود المصفوفات: الكتابة تقع على أي شيء يأتي بعدها في الذاكرة"
               "{victim_why_ar}.",
               "اجعل الحلقة تتوقف عند حجم المصفوفة (مثلاً 'cmp {index}, {count}' ثم 'jae done' قبل الكتابة)، أو احجز "
               "مساحة أكبر ('{label} times N db 0' أو 'resb N')."),
    },
    "sim.uninit_read": {
        "severity": "warning", "ref": "mov",
        "en": ("'{instr}' reads {where} before anything was stored there",
               "Stack memory is not cleared: a local variable contains whatever an earlier call left there "
               "(garbage). The program read {size} byte(s) at {where} in {proc} before writing them, so its result "
               "can change from run to run.",
               "Store a value first (e.g. 'mov {sizekw} [{where_short}], 0') at the start of {proc}, or check "
               "that the offset is the one you meant."),
        "ar": ("'{instr}' تقرأ {where} قبل أن يُخزَّن فيها أي شيء",
               "ذاكرة المكدس لا تُمسح تلقائياً: المتغير المحلي يحتوي على ما تركه استدعاء سابق (قيمة عشوائية). "
               "البرنامج قرأ {size} بايت عند {where} في {proc} قبل الكتابة فيها، لذلك قد تتغير النتيجة من تشغيل "
               "لآخر.",
               "خزّن قيمة أولاً (مثلاً 'mov {sizekw} [{where_short}], 0') في بداية {proc}، أو تأكد أن الإزاحة هي "
               "التي تقصدها."),
    },
    "sim.bad_pointer_arg": {
        "severity": "error", "ref": "lea",
        "en": ("{func} received an invalid pointer in {loc}: {value}",
               "Parameter '{param}' of {func} must be the ADDRESS of {what}, but {loc} = {value} is not a valid "
               "address. Usually the value stored at the label was loaded ('mov {reg}, [label]') instead of its "
               "address ('lea {reg}, [label]'), or the argument went into the wrong register / stack slot.",
               "Pass the address: 'lea {reg}, [label]' ({abi} puts parameter {index} in {loc})."),
        "ar": ("الدالة {func} استلمت مؤشراً غير صالح في {loc}: {value}",
               "المعامل '{param}' للدالة {func} يجب أن يكون عنوان {what_ar}، لكن {loc} = {value} ليس عنواناً صالحاً. "
               "غالباً تم تحميل القيمة المخزنة عند العنوان ('mov {reg}, [label]') بدلاً من العنوان نفسه "
               "('lea {reg}, [label]')، أو وُضع المعامل في مسجل أو خانة مكدس خاطئة.",
               "مرّر العنوان: 'lea {reg}, [label]' (في {abi} يوضع المعامل رقم {index} في {loc})."),
    },
    # ------------------------------------------------------------------ control flow
    "sim.exec_data": {
        "severity": "error", "ref": "ret",
        "en": ("Execution ran into data at {addr} ({where})",
               "The CPU does not know where code ends: after the last instruction it simply runs the next "
               "bytes. {how} The bytes there are data, not instructions, so Windows stops the program "
               "(DEP: data is not executable).",
               "End every procedure with 'ret' (main with the C runtime) or a call to ExitProcess / exit, and "
               "make sure jump targets are code labels."),
        "ar": ("وصل التنفيذ إلى بيانات عند {addr} ({where})",
               "المعالج لا يعرف أين ينتهي الكود: بعد آخر تعليمة ينفّذ البايتات التالية مباشرة. {how_ar} البايتات "
               "هناك بيانات وليست تعليمات، فيوقف ويندوز البرنامج (DEP: البيانات غير قابلة للتنفيذ).",
               "أنهِ كل إجراء بـ ret (و main مع مكتبة C)، أو باستدعاء ExitProcess أو exit، وتأكد أن أهداف القفز "
               "عناوين داخل الكود."),
    },
    "sim.ran_off_end": {
        "severity": "error", "ref": "ret",
        "en": ("The program ran past its last instruction (line {line_last})",
               "There is no 'ret', 'jmp' or exit call after the last instruction, so the CPU continued into "
               "the bytes after the code (address {addr}) - there is nothing valid there.",
               "Finish the program explicitly: 'ret' when main is called by the C runtime, otherwise "
               "'xor ecx, ecx' + 'call ExitProcess' (Windows) or the exit system call (Linux)."),
        "ar": ("استمر البرنامج بعد آخر تعليمة فيه (السطر {line_last})",
               "لا توجد ret ولا jmp ولا استدعاء خروج بعد آخر تعليمة، فاستمر المعالج في تنفيذ البايتات التي بعد "
               "الكود (العنوان {addr}) - ولا يوجد هناك شيء صالح.",
               "أنهِ البرنامج صراحةً: ret عندما تستدعي مكتبة C الدالة main، وإلا 'xor ecx, ecx' ثم "
               "'call ExitProcess' (ويندوز) أو نداء النظام exit (لينكس)."),
    },
    "sim.bad_jump": {
        "severity": "error", "ref": "jmp",
        "en": ("Jump to invalid address {addr} from '{instr}'",
               "The target of this jump / call came from {regs} and points nowhere: no code exists at {addr}.",
               "Jump to a label of the program, and check that the register holding the target was set."),
        "ar": ("قفز إلى عنوان غير صالح {addr} من '{instr}'",
               "هدف هذا القفز/الاستدعاء جاء من {regs} ولا يشير إلى أي مكان: لا يوجد كود عند {addr}.",
               "اقفز إلى عنوان (label) داخل البرنامج، وتأكد أن المسجل الذي يحمل الهدف قد ضُبطت قيمته."),
    },
    "sim.div_zero": {
        "severity": "error", "ref": "div",
        "en": ("Division by zero in '{instr}': the divisor {divisor} is 0",
               "'{mn}' divides {dividend} by {divisor}. Dividing by zero has no result, so the CPU raises a "
               "divide error (#DE) and Windows ends the program (STATUS_INTEGER_DIVIDE_BY_ZERO).",
               "Check the divisor before dividing: 'test {divisor}, {divisor}' / 'jz handle_zero'."),
        "ar": ("قسمة على صفر في '{instr}': المقسوم عليه {divisor} يساوي 0",
               "التعليمة '{mn}' تقسم {dividend} على {divisor}. القسمة على صفر ليس لها ناتج، فيرفع المعالج خطأ "
               "القسمة (#DE) وينهي ويندوز البرنامج.",
               "افحص المقسوم عليه قبل القسمة: 'test {divisor}, {divisor}' ثم 'jz handle_zero'."),
    },
    "sim.div_overflow": {
        "severity": "error", "ref": "div",
        "en": ("Divide overflow in '{instr}': {dividend} / {divisor_value} does not fit in {qreg}",
               "'{mn}' divides the double-size value {dividend} (= {dividend_value}) by {divisor} = {divisor_value}. "
               "The quotient must fit in {qreg}; it does not, so the CPU raises the same divide error as a "
               "division by zero. Most often {hi} still holds an old value: {hi} = {hi_value}.",
               "Before 'div' clear the high half: 'xor {hi32}, {hi32}'; before 'idiv' sign-extend: "
               "'{cdq}'."),
        "ar": ("فيضان القسمة في '{instr}': ناتج {dividend} ÷ {divisor_value} لا يتسع في {qreg}",
               "التعليمة '{mn}' تقسم القيمة مزدوجة الحجم {dividend} (= {dividend_value}) على {divisor} = "
               "{divisor_value}. يجب أن يتسع خارج القسمة في {qreg}؛ وهو لا يتسع، فيرفع المعالج نفس خطأ القسمة على "
               "صفر. غالباً ما يزال {hi} يحمل قيمة قديمة: {hi} = {hi_value}.",
               "قبل div صفّر النصف العلوي: 'xor {hi32}, {hi32}'؛ وقبل idiv وسّع الإشارة: '{cdq}'."),
    },
    "sim.infinite_loop": {
        "severity": "error", "ref": "loop",
        "en": ("The program did not finish after {steps} instructions: the loop at lines {first}-{last} "
               "seems endless",
               "Lines {first}-{last} ran {count} times. The jump at line {jump_line} ('{jump}') is always "
               "taken{cond_en}. {regs_en}",
               "Make sure something inside the loop changes the value the condition tests (increment / "
               "decrement the counter) and that the condition eventually becomes false."),
        "ar": ("لم ينتهِ البرنامج بعد {steps} تعليمة: يبدو أن الحلقة في الأسطر {first}-{last} لا نهائية",
               "الأسطر {first}-{last} نُفّذت {count} مرة. القفز في السطر {jump_line} ('{jump}') يتحقق دائماً"
               "{cond_ar}. {regs_ar}",
               "تأكد أن شيئاً داخل الحلقة يغيّر القيمة التي يختبرها الشرط (زيادة أو إنقاص العداد) وأن الشرط يصبح "
               "خاطئاً في النهاية."),
    },
    "sim.waiting_input": {
        "severity": "info", "ref": "int",
        "en": ("The program waits for more input than the check provided ({func})",
               "The check feeds the text of the 'Input' box to the program; it ended while {func} was still "
               "reading.",
               "Type more input lines in the Assembly Checks window and run the check again."),
        "ar": ("البرنامج ينتظر إدخالاً أكثر مما وفّره الفحص ({func})",
               "الفحص يعطي البرنامج نص مربع 'الإدخال'؛ وقد انتهى النص بينما كانت {func} ما تزال تقرأ.",
               "اكتب أسطر إدخال أكثر في نافذة فحوص الأسمبلي ثم أعد الفحص."),
    },
    "sim.unknown_extern": {
        "severity": "info", "ref": "extern",
        "en": ("'{name}' is not simulated: the check made it return 0",
               "The checker imitates common C runtime and Win32 functions. {name} is not one of them, so "
               "its real effect is missing from this run.",
               "Nothing to fix in your code; results after this call may differ from a real run."),
        "ar": ("الدالة '{name}' غير محاكاة: جعلها الفحص ترجع 0",
               "الفاحص يحاكي الدوال الشائعة في مكتبة C وويندوز. الدالة {name} ليست منها، لذلك تأثيرها الحقيقي "
               "غير موجود في هذا التشغيل.",
               "لا يوجد ما تصلحه في كودك؛ قد تختلف النتائج بعد هذا الاستدعاء عن التشغيل الحقيقي."),
    },
    "sim.bad_opcode": {
        "severity": "error", "ref": "jmp",
        "en": ("Invalid instruction bytes at {addr}",
               "The CPU found bytes that are not a valid instruction ({bytes}). The program probably jumped "
               "into data or into the middle of an instruction.",
               "Check the jump / call that led here and make sure the code ends with ret or an exit call."),
        "ar": ("بايتات تعليمة غير صالحة عند {addr}",
               "وجد المعالج بايتات لا تمثل تعليمة صالحة ({bytes}). غالباً قفز البرنامج إلى البيانات أو إلى منتصف "
               "تعليمة.",
               "راجع القفز أو الاستدعاء الذي أوصل إلى هنا، وتأكد أن الكود ينتهي بـ ret أو باستدعاء خروج."),
    },
}

# words used inside the messages
ACCESS = {"read": ("Reading", "قراءة"), "write": ("Writing to", "كتابة في"), "fetch": ("Running code at", "تنفيذ كود عند")}

TOPICS = {
    "abi": ("Calling conventions (Windows x64 / System V / cdecl / stdcall)",
            "اصطلاحات الاستدعاء (ويندوز 64 / System V / cdecl / stdcall)",
            "https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention"),
    "section": ("Sections: .text (code), .data, .bss, .rdata", "الأقسام: ‎.text‎ (الكود) و ‎.data‎ و ‎.bss‎ و ‎.rdata‎",
                "https://www.nasm.us/doc/nasmdoc7.html"),
    "times": ("Reserving data: db / times / resb", "حجز البيانات: db و times و resb",
              "https://www.nasm.us/doc/nasmdoc3.html"),
    "extern": ("extern: functions of other modules / DLLs", "extern: دوال من وحدات أو مكتبات أخرى",
               "https://www.nasm.us/doc/nasmdoc6.html"),
}


class _Safe(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _fmt(template: str, args: dict) -> str:
    try:
        return string.Formatter().vformat(template, (), _Safe(args))
    except (ValueError, IndexError):
        return template


def text(rule: str, part: str, lang: str = "en", **args) -> str:
    """part: msg | why | fix."""
    r = RULES.get(rule)
    if not r:
        return rule
    idx = {"msg": 0, "why": 1, "fix": 2}[part]
    pair = r["ar" if lang == "ar" else "en"]
    return _fmt(pair[idx], args)


def severity(rule: str) -> str:
    return RULES.get(rule, {}).get("severity", "warning")


def ref_of(rule: str, override: str = "") -> dict:
    """{"topic", "title_en", "title_ar", "url", "doc"} for the rule's reference (an instruction or a topic)."""
    topic = override or RULES.get(rule, {}).get("ref", "")
    if topic in TOPICS:
        en, ar, url = TOPICS[topic]
        return {"topic": topic, "title_en": en, "title_ar": ar, "url": url, "doc": ""}
    try:
        from ..asm_intel import isa
        ins = isa.instruction(topic)
    except Exception:  # noqa: BLE001
        ins = None
    if ins is not None:
        return {"topic": topic, "title_en": f"{topic.upper()} - {ins.doc}", "title_ar": f"التعليمة {topic.upper()}",
                "url": isa.SDM_URL, "doc": ins.doc}
    return {"topic": topic, "title_en": topic, "title_ar": topic, "url": "", "doc": ""}
