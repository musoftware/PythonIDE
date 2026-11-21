# الدرس 4: البيانات والمتغيرات والأقسام

**في هذا الدرس ستتعلم:**

- أقسام البرنامج: `.text` و`.data` و`.bss` و`.rdata`.
- تعريف المتغيرات بـ `db` و`dw` و`dd` و`dq`، والحجز بـ `resb` وأخواتها.
- التكرار بـ `times`، والثوابت بـ `equ`، وحساب طول النص بـ `$`.
- قراءة الأعداد الصغيرة **بإشارة** و**بلا إشارة**: `movsx` و`movzx`.

## أقسام البرنامج

الملف التنفيذي مقسّم إلى **أقسام** (Sections)، لكل منها غرض وصلاحيات:

| القسم | ماذا فيه | الصلاحيات |
|---|---|---|
| `.text` | التعليمات (الكود) | قراءة وتنفيذ |
| `.data` | متغيرات لها قيمة أولية | قراءة وكتابة |
| `.bss` | متغيرات بلا قيمة أولية (تبدأ أصفارًا) | قراءة وكتابة |
| `.rdata` | ثوابت ونصوص لا تتغير | قراءة فقط |

لماذا `.bss`؟ لو أردت مصفوفة من مليون بايت فارغة فلا داعي لتخزين مليون صفر داخل ملف `.exe`؛ يكفي أن يسجل الملف «احجز مليون بايت»، ونظام التشغيل يجهزها أصفارًا عند التشغيل.

> **ملاحظة:** الكتابة في `.rdata` أو `.text` تجعل البرنامج ينهار بخطأ **Access Violation** (انتهاك الوصول)، لأن نظام التشغيل يحمي هذه الأقسام من الكتابة.

## تعريف المتغيرات

```asm
section .data
    small  db 200            ; بايت واحد
    medium dw 50000          ; word = بايتان
    big    dd 3000000000     ; dword = 4 بايتات
    huge   dq 9000000000000000000   ; qword = 8 بايتات
    list   dd 10, 20, 30     ; عدة قيم متتالية (مصفوفة)
    text   db "Hi", 10, 0    ; حروف وأعداد مختلطة
```

حرف الأمر يدل على الحجم: **b**yte و**w**ord و**d**ouble word و**q**uad word. الاسم في أول السطر لافتة لعنوان **أول** بايت.

لقراءة متغير أصغر من المسجل نستخدم `movzx` (يملأ الباقي بأصفار)؛ لا يوجد `movzx` من 32 إلى 64 بت لأن `mov` إلى مسجل 32 بت يصفّر النصف الأعلى تلقائيًّا (تذكّر الدرس السابق):

```asm run
default rel
global main
extern printf

section .data
    small  db 200
    medium dw 50000
    big    dd 3000000000
    huge   dq 9000000000000000000
    fmt1   db "%u %u %u", 10, 0
    fmt2   db "%llu", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt1]
    movzx edx, byte [small]
    movzx r8d, word [medium]
    mov r9d, [big]
    call printf

    lea rcx, [fmt2]
    mov rdx, [huge]
    call printf

    xor eax, eax
    add rsp, 40
    ret
```

```text output
200 50000 3000000000
9000000000000000000
```

## بإشارة أم بلا إشارة؟ movsx وmovzx

البايت `0xFB` يمكن أن يكون 251 (بلا إشارة) أو ‎-5 (بإشارة). عند توسيعه إلى مسجل أكبر:

- `movzx` (Zero eXtend) يملأ البتات الجديدة بأصفار: 251.
- `movsx` (Sign eXtend) ينسخ **بت الإشارة** في البتات الجديدة: ‎-5.

```asm run
default rel
global main
extern printf

section .data
    t   db -5
    fmt db "movzx=%d movsx=%d", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    movzx edx, byte [t]
    movsx r8d, byte [t]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
movzx=251 movsx=-5
```

## الثوابت بـ equ وطول النص بـ $

`equ` يعطي اسمًا لقيمة ثابتة **وقت التجميع** (لا تحجز ذاكرة، مثل `#define` في C). والرمز `$` يعني «العنوان الحالي» في القسم، فإذا كتبنا بعد النص مباشرة `$ - msg` حصلنا على عدد بايتاته:

```asm run
default rel
global main
extern printf

WIDTH  equ 80
HEIGHT equ 25
AREA   equ WIDTH * HEIGHT        ; يحسبها المجمّع: 2000

section .data
    msg    db "Hello", 0
    msglen equ $ - msg - 1       ; بدون الصفر الأخير = 5
    ar     db "سلام", 0
    arlen  equ $ - ar - 1        ; كل حرف عربي = 2 بايت في UTF-8
    fmt1   db "%s: %d bytes", 10, 0
    fmt2   db "area = %d", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt1]
    lea rdx, [msg]
    mov r8d, msglen
    call printf

    lea rcx, [fmt1]
    lea rdx, [ar]
    mov r8d, arlen
    call printf

    lea rcx, [fmt2]
    mov edx, AREA
    call printf

    xor eax, eax
    add rsp, 40
    ret
```

```text output
Hello: 5 bytes
سلام: 8 bytes
area = 2000
```

لاحظ أن `%s` تأخذ **عنوان** النص (`lea`)، و`%d` تأخذ **قيمة**.

## التكرار بـ times والحجز في .bss

- `times 5 db 0` يكرر التعريف 5 مرات (5 بايتات أصفار).
- في `.bss` نحجز بلا قيمة: `resb` (بايتات) و`resw` و`resd` و`resq`: `buf resd 10` = عشر dword.

```asm run
default rel
global main
extern printf

section .data
    sevens times 4 dd 7          ; 7, 7, 7, 7
    fmt    db "sevens[3]=%d result=%d", 10, 0

section .bss
    result resd 1                ; dword واحد يبدأ بصفر

section .text
main:
    sub rsp, 40
    mov eax, [sevens + 12]       ; العنصر الرابع: 3 × 4 بايت
    mov [result], eax
    add dword [result], 100      ; 7 + 100

    lea rcx, [fmt]
    mov edx, [sevens + 12]
    mov r8d, [result]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
sevens[3]=7 result=107
```

لاحظ كيف وصلنا للعنصر الرابع: العناصر من نوع dword (4 بايتات)، فالعنصر رقم `i` (من الصفر) عنوانه `sevens + i * 4`. الدرس 8 يتوسع في هذا.

## ثوابت للقراءة فقط

النصوص التي لا تتغير مكانها الأنسب `.rdata`. تعمل بنفس الطريقة، لكن أي محاولة للكتابة فيها توقف البرنامج:

```asm run
default rel
global main
extern puts

section .rdata
    title db "RAD IDE - Assembly", 0

section .text
main:
    sub rsp, 40
    lea rcx, [title]
    call puts
    xor eax, eax
    add rsp, 40
    ret
```

```text output
RAD IDE - Assembly
```

## أخطاء شائعة

- **نسيان أن `db` بايت واحد:** `x db 300` يعطي تحذيرًا لأن 300 لا تتسع في بايت (`warning: byte exceeds bounds [-w+number-overflow]`) ويخزّن 44 فقط (300 - 256).
- **قراءة بحجم خاطئ:** `mov eax, [small]` حيث `small db 200` يقرأ 4 بايتات: `small` وثلاثة بايتات بعده من متغيرات أخرى!
- **`$ - msg` في مكان خاطئ:** يجب أن يأتي **مباشرة** بعد النص؛ إذا عرّفت متغيرًا بينهما ستُحسب بايتاته أيضًا.

## تمارين

### التمرين 1

عرّف `year` كـ word و`month` و`day` كبايتين، ثم اطبع التاريخ بالشكل `2026-11-21`.

```asm exercise
default rel
global main
extern printf

section .data
    year  dw 2026
    ; month و day
    fmt   db "%d-%02d-%02d", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    ; edx و r8d و r9d
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
    year  dw 2026
    month db 11
    day   db 21
    fmt   db "%d-%02d-%02d", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    movzx edx, word [year]
    movzx r8d, byte [month]
    movzx r9d, byte [day]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
2026-11-21
```

### التمرين 2

احسب طول النص `"Assembly"` بـ `equ` و`$`، واطبع: `Assembly has 8 letters`.

```asm exercise
default rel
global main
extern printf

section .data
    word1 db "Assembly", 0
    ; len equ ...
    fmt   db "%s has %d letters", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    lea rdx, [word1]
    mov r8d, 0          ; ضع الطول هنا
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
    word1 db "Assembly", 0
    len   equ $ - word1 - 1
    fmt   db "%s has %d letters", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    lea rdx, [word1]
    mov r8d, len
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
Assembly has 8 letters
```

## اختبر نفسك

```quiz
{"question": "أي قسم يناسب مصفوفة كبيرة بلا قيم أولية؟", "choices": [".text", ".data", ".bss", ".rdata"], "answer": 2, "explanation": ".bss يحجز الذاكرة عند التشغيل أصفارًا دون أن يكبر حجم الملف."}
```

```quiz
{"question": "كم بايتًا يحجز السطر: arr dd 1, 2, 3 ؟", "choices": ["3", "6", "12", "24"], "answer": 2, "explanation": "ثلاث قيم dword، كل واحدة 4 بايتات."}
```

```quiz
{"question": "البايت 0xFF: ماذا تعطي movsx eax, byte [x] ؟", "choices": ["255", "-1", "0", "65535"], "answer": 1, "explanation": "movsx ينسخ بت الإشارة (1) في كل البتات الجديدة، فتصبح القيمة -1."}
```

```quiz
{"question": "هل يحجز السطر SIZE equ 10 أي ذاكرة؟", "choices": ["نعم، 10 بايتات", "نعم، بايتًا واحدًا", "لا، هو ثابت يستبدله المجمّع وقت التجميع"], "answer": 2, "explanation": "equ اسم لقيمة ثابتة فقط."}
```

## الخلاصة

- `.text` للكود، و`.data` للمتغيرات ذات القيم، و`.bss` للمحجوز بلا قيم، و`.rdata` للثوابت.
- `db`/`dw`/`dd`/`dq` تعرّف 1/2/4/8 بايتات، و`resb`/`resw`/`resd`/`resq` تحجز في `.bss`، و`times` تكرر.
- `equ` ثابت وقت التجميع، و`$ - label` طول ما بينهما.
- `movzx` للقيم بلا إشارة و`movsx` للقيم بإشارة عند توسيع حجم صغير.
