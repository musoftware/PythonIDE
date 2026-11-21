# الدرس 14: تصحيح الأخطاء: المسجلات والتفكيك والذاكرة

**في هذا الدرس ستتعلم:**

- نقاط التوقف والتنفيذ خطوة بخطوة في برامج لغة التجميع.
- نوافذ المنقّح: **Registers** و**Disassembly** و**Memory** و**Stack**.
- التنفيذ **تعليمة تعليمة** وتعديل المسجلات والأعلام أثناء التوقف.
- صيد خطأين حقيقيين: تجاوز حدود المصفوفة، والقسمة بإشارة دون `cdq`.
- قراءة رسائل الانهيار مثل **Access Violation**.

## لماذا المنقّح مهم في لغة التجميع؟

في لغة التجميع لا توجد رسائل مثل «المتغير غير معرّف» أثناء التشغيل: البرنامج إما يعطي ناتجًا خاطئًا بصمت، أو ينهار. المنقّح (Debugger) يجعلك ترى ما يراه المعالج: قيمة كل مسجل وكل بايت بعد كل تعليمة. RAD IDE تستخدم المنقّح **gdb** من حزمة MinGW، وتولّد معلومات الأسطر لملفات NASM، فتعمل نقاط التوقف على أسطر ملف `.asm` مباشرة.

## الأساسيات

| الأمر | الاختصار | العمل |
|---|---|---|
| Toggle Breakpoint | `F9` | نقطة توقف على السطر (دائرة حمراء في الهامش) |
| Start Debugging | `F5` | ابنِ وشغّل تحت المنقّح حتى أول نقطة توقف |
| Step Over | `F10` | نفّذ السطر، و`call` تُنفَّذ كاملة |
| Step Into | `F11` | نفّذ السطر وادخل إلى الدالة إذا كان `call` |
| Step Out | `Shift+F11` | أكمل حتى ترجع الدالة الحالية |
| Step Into Instruction | `Ctrl+Alt+F11` | تعليمة آلة واحدة (حتى داخل دوال بلا كود مصدري) |
| Step Over Instruction | `Ctrl+Alt+F10` | تعليمة واحدة، و`call` كاملة |
| Stop Debugging | `Shift+F5` | أوقف البرنامج |

## نوافذ المنقّح

افتحها من **Debug > Windows** (تصحيح > نوافذ) أثناء التوقف:

- **Registers** (`Alt+5`): كل المسجلات العامة، ومسجل الأعلام **مفكوكًا** بتًا بتًا (`CF` و`ZF` و`SF` و`OF` ...)، والمقاطع ومسجلات SSE (`xmm0`...). القيم التي تغيرت منذ آخر توقف تظهر **بالأحمر**. انقر مرتين على قيمة لتغييرها، أو على علم لقلبه.
- **Disassembly** (`Alt+8`): التعليمات بصياغة Intel حول التعليمة الحالية (سهم أصفر)، مع أسطر ملفك بينها وبايتات كل تعليمة. انقر في العمود الأيسر لنقطة توقف على **عنوان**.
- **Memory 1** (`Alt+6`): البايتات بالسادس عشر وبجانبها حروف ASCII، من أي عنوان أو تعبير: `0x404000` أو `$rsp` أو اسم لافتة مثل `arr`. اختر مجموعات 1 أو 2 أو 4 أو 8 بايتات، و«اتبع» مسجلًا لتتحرك النافذة معه.
- **Stack**: المكدس من `rsp` صاعدًا، كل سطر 8 بايتات، مع علامتي `RSP` و`RBP`، وإلى ماذا تشير كل قيمة (عنوان رجوع داخل `main` مثلًا).
- **Watch** (المراقبة): اكتب تعبيرًا مثل `$rax` أو `$rcx * 4` أو `*(int*)&arr` ليُحسب عند كل توقف.

> **تذكّر الدرس 3:** في نافذة Memory ترى الأعداد مقلوبة البايتات (Little Endian): العدد `0x0000000C` (12) يظهر `0C 00 00 00`.

## جلسة تصحيح كاملة

1. أنشئ مشروع **Assembly Console (x64 Windows, NASM)** والصق برنامج «مجموع المصفوفة» أدناه.
2. ضع نقطة توقف (`F9`) على سطر `add eax, [r10 + rcx*4]`.
3. اضغط `F5`. يتوقف البرنامج قبل تنفيذ السطر.
4. افتح **Registers**: `rcx` = 0 (الفهرس) و`rax` = 0 (المجموع).
5. افتح **Memory 1** واكتب `arr`: ترى `0C 00 00 00 07 00 00 00 21 00 00 00 ...`.
6. اضغط `F5` مرة بعد مرة: في كل توقف يزيد `rcx` بواحد ويزيد `rax` بالعنصر. راقب اللون الأحمر.
7. انتبه عندما يصبح `rcx` = 6 ...

## الخطأ الأول: تجاوز حدود المصفوفة

هذا البرنامج يجب أن يطبع 87 (مجموع العناصر الستة)، لكنه يطبع شيئًا آخر:

```asm run
default rel
global main
extern printf

section .data
    arr      dd 12, 7, 33, 5, 21, 9
    count    equ ($ - arr) / 4
    sentinel dd 1000             ; متغير آخر يأتي بعد المصفوفة مباشرة
    fmt      db "sum = %d", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]
    xor eax, eax
    xor ecx, ecx
.next:
    add eax, [r10 + rcx*4]
    inc ecx
    cmp ecx, count
    jle .next                    ; <-- الخطأ هنا
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
sum = 1087
```

في المنقّح ترى أن الحلقة دخلت مرة سابعة و`rcx` = 6، أي العنصر `arr[6]` غير الموجود، فقرأت `[r10 + 24]` وهو المتغير `sentinel` (1000). الشرط يجب أن يكون `jl` (أصغر من) لا `jle`. هذا الخطأ الشهير اسمه **Off-by-one** (الخطأ بواحد). والأسوأ أن البرنامج لم ينهر: قرأ ذاكرة صالحة لكنها ليست له.

بعد التصحيح:

```asm run
default rel
global main
extern printf

section .data
    arr      dd 12, 7, 33, 5, 21, 9
    count    equ ($ - arr) / 4
    sentinel dd 1000
    fmt      db "sum = %d", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]
    xor eax, eax
    xor ecx, ecx
.next:
    add eax, [r10 + rcx*4]
    inc ecx
    cmp ecx, count
    jl .next
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
sum = 87
```

## الانهيار: Access Violation

إذا قرأ البرنامج أو كتب في عنوان غير مسموح (صفر مثلًا، أو قسم للقراءة فقط) يوقفه ويندوز. تحت المنقّح يتوقف على التعليمة المذنبة مباشرة ويخبرك بالسبب، وخارج المنقّح ينتهي البرنامج برمز خروج مثل `0xC0000005`. أشهر الأسباب:

| الرمز | المعنى | السبب المعتاد |
|---|---|---|
| `0xC0000005` | Access Violation | مؤشر صفر أو خاطئ، كتابة في `.rdata`، مكدس غير متوازن عند `ret` |
| `0xC0000094` | Integer divide by zero | `div`/`idiv` على صفر |
| `0xC0000095` | Integer overflow | الخارج لا يتسع (نسيت تجهيز `edx`) |
| `0xC00000FD` | Stack overflow | استدعاء ذاتي بلا نهاية |

خطوات التحقيق: انظر إلى السهم الأصفر في **Disassembly**، ثم إلى المسجلات المستخدمة في العنوان (مثلًا `[rbx + 8]` و`rbx` = 0)، ثم إلى **Stack** لتعرف من استدعى من.

## أدوات أخرى

- **أوامر gdb مباشرة:** في نافذة **Immediate** (الفورية) أثناء التوقف اكتب تعبيرًا مثل `$rcx*4`، أو أمر gdb بعد `-exec`: `-exec info registers rax` و`-exec x/6dw &arr` (6 أعداد dword من `arr`).
- **ملف القائمة (Listing):** عند البناء تحفظ الـ IDE في المجلد `_build` ملف `main.lst`: كل سطر من كودك وعنوانه وبايتاته.
- **objdump:** `objdump -d -M intel _radapp.exe` يفكك البرنامج كله في الطرفية.

## تمرين: القسمة على عدد سالب

هذا البرنامج يجب أن يطبع متوسط ‎-10 و‎-20 و‎-30 أي ‎-20، لكنه يطبع رقمًا ضخمًا. شغّله بالمنقّح، وضع نقطة توقف على `idiv`، وانظر إلى `edx` و`eax` في نافذة **Registers**. ثم أصلحه.

```asm exercise
default rel
global main
extern printf

section .data
    arr   dd -10, -20, -30
    count equ ($ - arr) / 4
    fmt   db "average = %d", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]
    xor eax, eax
    xor ecx, ecx
.next:
    add eax, [r10 + rcx*4]
    inc ecx
    cmp ecx, count
    jl .next
    xor edx, edx                 ; هل هذا صحيح للأعداد السالبة؟
    mov ecx, count
    idiv ecx
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```asm solution
default rel
global main
extern printf

section .data
    arr   dd -10, -20, -30
    count equ ($ - arr) / 4
    fmt   db "average = %d", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]
    xor eax, eax
    xor ecx, ecx
.next:
    add eax, [r10 + rcx*4]
    inc ecx
    cmp ecx, count
    jl .next
    cdq                          ; edx = إشارة eax (0xFFFFFFFF هنا)
    mov ecx, count
    idiv ecx
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
average = -20
```

مع `xor edx, edx` كان المقسوم `edx:eax` = `0x00000000FFFFFFC4`، أي العدد الموجب 4294967236، فخارج القسمة على 3 = 1431655745. هذا ما تراه في نافذة Registers قبل `idiv`.

## اختبر نفسك

```quiz
{"question": "أي أمر ينفّذ تعليمة آلة واحدة حتى داخل دالة من مكتبة؟", "choices": ["F5", "F10", "Step Into Instruction (Ctrl+Alt+F11)", "Shift+F5"], "answer": 2, "explanation": "التنفيذ تعليمة تعليمة لا يحتاج كودًا مصدريًا."}
```

```quiz
{"question": "في نافذة Registers ماذا يعني اللون الأحمر؟", "choices": ["خطأ في المسجل", "القيمة تغيرت منذ آخر توقف", "مسجل محفوظ", "قيمة سالبة"], "answer": 1, "explanation": "الأحمر يبرز ما غيّرته آخر خطوة."}
```

```quiz
{"question": "ما رمز الانهيار عند القسمة على صفر؟", "choices": ["0xC0000005", "0xC0000094", "0xC00000FD", "0"], "answer": 1, "explanation": "0xC0000094 = Integer divide by zero."}
```

```quiz
{"question": "حلقة على 6 عناصر بالفهرس من 0 تستخدم cmp ecx, 6 ثم jle. ما المشكلة؟", "choices": ["لا مشكلة", "تدور 7 مرات وتقرأ عنصرًا بعد نهاية المصفوفة", "تدور 5 مرات فقط", "لا تدور أبدًا"], "answer": 1, "explanation": "jle تسمح بـ ecx = 6: خطأ بواحد. الصحيح jl."}
```

## الخلاصة

- `F9` نقطة توقف، و`F5` تشغيل بالمنقّح، و`F10`/`F11` خطوات، و`Ctrl+Alt+F11` تعليمة واحدة.
- **Registers** (`Alt+5`) و**Disassembly** (`Alt+8`) و**Memory 1** (`Alt+6`) و**Stack** و**Watch**.
- الأحمر = تغيّر؛ وانقر مرتين لتغيير مسجل أو قلب علم.
- الأخطاء الصامتة (Off-by-one، القسمة بلا `cdq`) تظهر بمراقبة المسجلات خطوة بخطوة.
- `0xC0000005` وصول خاطئ للذاكرة، و`0xC0000094` قسمة على صفر.
