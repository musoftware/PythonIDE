# الدرس 6: الأعلام والمقارنة والقفزات

**في هذا الدرس ستتعلم:**

- مسجل الأعلام `rflags`: الأعلام `ZF` و`SF` و`CF` و`OF`.
- المقارنة بـ `cmp` والاختبار بـ `test`.
- القفز غير المشروط `jmp` والقفزات المشروطة (`je` و`jg` و`ja` ...).
- كتابة `if` و`if/else` و`else if` بلغة التجميع، واللافتات المحلية.
- الفرق بين المقارنة **بإشارة** و**بلا إشارة**، و`setcc` و`cmovcc`.

## مسجل الأعلام

بعد كل عملية حسابية أو منطقية يسجّل المعالج «ملاحظات» عن الناتج في بتات خاصة داخل المسجل `rflags`. أهمها:

| العلم | الاسم | يصبح 1 عندما... |
|---|---|---|
| `ZF` | Zero Flag | الناتج **صفر** |
| `SF` | Sign Flag | البت الأعلى للناتج 1 (سالب إذا قرأناه بإشارة) |
| `CF` | Carry Flag | حمل أو استلاف خارج الحجم (فيضان **بلا إشارة**) |
| `OF` | Overflow Flag | فيضان **بإشارة** (موجب + موجب = سالب مثلًا) |

> **مهم:** `mov` و`lea` و`push` و`call` لا تغيّر الأعلام. أما `add` و`sub` و`inc` و`dec` و`and` و`or` و`xor` و`cmp` و`test` فتغيّرها.

التعليمات `setz` و`setc` و`sets` و`seto` تضع 1 أو 0 في بايت حسب العلم، فنستطيع طباعة الأعلام:

```asm run
default rel
global main
extern printf

section .data
    fmt1 db "0xFFFFFFFF + 1 : ZF=%d CF=%d SF=%d", 10, 0
    fmt2 db "0x7FFFFFFF + 1 : ZF=%d OF=%d SF=%d", 10, 0

section .text
main:
    sub rsp, 40
    xor edx, edx             ; نصفّر قبل الجمع لأن xor نفسها تغيّر الأعلام
    xor r8d, r8d
    xor r9d, r9d
    mov eax, 0xFFFFFFFF
    add eax, 1               ; الناتج 0 مع حمل
    setz dl
    setc r8b
    sets r9b
    lea rcx, [fmt1]
    call printf

    xor edx, edx
    xor r8d, r8d
    xor r9d, r9d
    mov eax, 0x7FFFFFFF      ; أكبر عدد موجب في 32 بت
    add eax, 1               ; يصبح سالبًا: فيضان بإشارة
    setz dl
    seto r8b
    sets r9b
    lea rcx, [fmt2]
    call printf

    xor eax, eax
    add rsp, 40
    ret
```

```text output
0xFFFFFFFF + 1 : ZF=1 CF=1 SF=0
0x7FFFFFFF + 1 : ZF=0 OF=1 SF=1
```

## `cmp` و`test`

- `cmp a, b` تحسب `a - b` **وترمي الناتج**، وتحتفظ فقط بالأعلام. إذا كان `a == b` فـ `ZF = 1`.
- `test a, b` تحسب `a AND b` وترمي الناتج. `test eax, eax` تسأل: هل `eax` صفر؟ و`test eax, 1` تسأل: هل البت الأدنى 1 (عدد فردي)؟

## القفزات

`jmp label` تقفز دائمًا (تضع عنوان اللافتة في `rip`). والقفزات **المشروطة** تقفز فقط إذا تحقق شرط على الأعلام، وتُكتب عادة بعد `cmp`:

| القفزة | تقفز إذا (بعد `cmp a, b`) | النوع |
|---|---|---|
| `je` / `jz` | `a == b` | الكل |
| `jne` / `jnz` | `a != b` | الكل |
| `jg` / `jnle` | `a > b` | بإشارة |
| `jge` | `a >= b` | بإشارة |
| `jl` | `a < b` | بإشارة |
| `jle` | `a <= b` | بإشارة |
| `ja` | `a > b` | بلا إشارة (Above) |
| `jae` | `a >= b` | بلا إشارة |
| `jb` | `a < b` | بلا إشارة (Below) |
| `jbe` | `a <= b` | بلا إشارة |

للتذكر: **g**reater و**l**ess للأعداد **بإشارة**، و**a**bove و**b**elow للأعداد **بلا إشارة** (والعناوين).

## `if`: أكبر العددين

لا توجد `if` في لغة التجميع؛ نصنعها بالمقارنة والقفز **فوق** الكود الذي لا نريده:

```asm run
default rel
global main
extern printf

section .data
    a   dd 17
    b   dd 42
    fmt db "max(%d, %d) = %d", 10, 0

section .text
main:
    sub rsp, 40
    mov r9d, [a]             ; نفترض أن a هو الأكبر
    mov eax, [b]
    cmp r9d, eax
    jge .done                ; إذا a >= b فالافتراض صحيح
    mov r9d, eax             ; وإلا فالأكبر b
.done:
    lea rcx, [fmt]
    mov edx, [a]
    mov r8d, [b]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
max(17, 42) = 42
```

اللافتة التي تبدأ بنقطة مثل `.done` **محلية**: تنتمي إلى آخر لافتة عادية قبلها (`main`)، فتستطيع استخدام `.done` مرة أخرى داخل دالة أخرى بلا تعارض.

## `if` / `else`: زوجي أم فردي

```asm run
default rel
global main
extern printf

section .data
    n    dd 7
    even db "even", 0
    odd  db "odd", 0
    fmt  db "%d is %s", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, [n]
    test eax, 1              ; البت الأدنى؟
    jz .is_even
    lea r8, [odd]            ; الفرع "else"
    jmp .print
.is_even:
    lea r8, [even]           ; الفرع "if"
.print:
    lea rcx, [fmt]
    mov edx, [n]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
7 is odd
```

لاحظ `jmp .print` في آخر الفرع الأول: بدونها «يسقط» التنفيذ إلى الفرع الثاني أيضًا.

## `else if`: التقدير

```text
if score >= 90: grade = 'A'
elif score >= 80: grade = 'B'
elif score >= 70: grade = 'C'
else: grade = 'F'
```

```asm run
default rel
global main
extern printf

section .data
    score dd 85
    fmt   db "score %d -> grade %c", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, [score]
    mov r8d, 'A'
    cmp eax, 90
    jge .print
    mov r8d, 'B'
    cmp eax, 80
    jge .print
    mov r8d, 'C'
    cmp eax, 70
    jge .print
    mov r8d, 'F'
.print:
    lea rcx, [fmt]
    mov edx, [score]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
score 85 -> grade B
```

## بإشارة أم بلا إشارة؟ فخ شهير

نفس البتات تعطي نتيجتين مختلفتين للمقارنة: `-1` هو `0xFFFFFFFF`. بإشارة: ‎-1 أصغر من 1. بلا إشارة: 4294967295 أكبر من 1!

```asm run
default rel
global main
extern printf

section .data
    fmt db "-1 > 1 ?  signed (jg): %d   unsigned (ja): %d", 10, 0

section .text
main:
    sub rsp, 40
    xor edx, edx
    xor r8d, r8d
    mov eax, -1
    cmp eax, 1
    setg dl                  ; الشرط الذي تختبره jg
    seta r8b                 ; الشرط الذي تختبره ja
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
-1 > 1 ?  signed (jg): 0   unsigned (ja): 1
```

القاعدة: الأعداد التي قد تكون سالبة قارنها بـ `jg`/`jl`، والعناوين والأحجام والأعداد الموجبة دائمًا بـ `ja`/`jb`.

## نقل مشروط بلا قفز: `cmovcc`

`cmovge eax, ecx` تنسخ فقط إذا تحقق الشرط. تغني أحيانًا عن القفز وتكون أسرع:

```asm run
default rel
global main
extern printf

section .data
    fmt db "min = %d", 10, 0

section .text
main:
    sub rsp, 40
    mov edx, 30
    mov eax, 12
    cmp edx, eax
    cmovg edx, eax           ; إذا كان edx > eax خذ eax
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
min = 12
```

## تمارين

### التمرين 1

اطبع القيمة المطلقة للعدد ‎-25: `|-25| = 25`. (إذا كان سالبًا استخدم `neg`.)

```asm exercise
default rel
global main
extern printf

section .data
    x   dd -25
    fmt db "|%d| = %d", 10, 0

section .text
main:
    sub rsp, 40
    mov r8d, [x]
    ; إذا كان r8d سالبًا اقلب إشارته
    lea rcx, [fmt]
    mov edx, [x]
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
    x   dd -25
    fmt db "|%d| = %d", 10, 0

section .text
main:
    sub rsp, 40
    mov r8d, [x]
    test r8d, r8d
    jns .positive            ; علم الإشارة 0: موجب
    neg r8d
.positive:
    lea rcx, [fmt]
    mov edx, [x]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
|-25| = 25
```

### التمرين 2

السنة **كبيسة** إذا قبلت القسمة على 4، ولم تقبل القسمة على 100، إلا إذا قبلت القسمة على 400. اطبع للسنة 2024: `2024 is a leap year`.

```asm exercise
default rel
global main
extern printf

section .data
    year db 0                ; غيّرها إلى dd 2024
    yes  db "%d is a leap year", 10, 0
    no   db "%d is not a leap year", 10, 0

section .text
main:
    sub rsp, 40
    ; اقسم على 4 و100 و400 وانظر إلى الباقي في edx
    lea rcx, [no]
    mov edx, 2024
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
    year dd 2024
    yes  db "%d is a leap year", 10, 0
    no   db "%d is not a leap year", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, [year]
    xor edx, edx
    mov ecx, 4
    div ecx
    test edx, edx
    jnz .not_leap            ; لا تقبل القسمة على 4

    mov eax, [year]
    xor edx, edx
    mov ecx, 100
    div ecx
    test edx, edx
    jnz .leap                ; تقبل 4 ولا تقبل 100

    mov eax, [year]
    xor edx, edx
    mov ecx, 400
    div ecx
    test edx, edx
    jz .leap                 ; تقبل 400
.not_leap:
    lea rcx, [no]
    jmp .print
.leap:
    lea rcx, [yes]
.print:
    mov edx, [year]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
2024 is a leap year
```

## اختبر نفسك

```quiz
{"question": "ماذا تفعل cmp eax, ebx؟", "choices": ["تنسخ ebx إلى eax", "تحسب eax - ebx وتغيّر الأعلام دون تخزين الناتج", "تقفز إذا تساويا", "تبدّل القيمتين"], "answer": 1, "explanation": "cmp طرح بلا تخزين: النتيجة في الأعلام فقط."}
```

```quiz
{"question": "أي قفزة تستخدم لمقارنة عددين قد يكونان سالبين (أكبر من)؟", "choices": ["ja", "jg", "jb", "jc"], "answer": 1, "explanation": "jg للمقارنة بإشارة، وja لبلا إشارة."}
```

```quiz
{"question": "ماذا تعني test eax, eax ثم jz؟", "choices": ["اقفز إذا كان eax صفرًا", "اقفز إذا كان eax سالبًا", "اقفز دائمًا", "اقفز إذا كان eax فرديًا"], "answer": 0, "explanation": "AND العدد مع نفسه يعطي العدد نفسه، فيصبح ZF = 1 إذا كان صفرًا."}
```

```quiz
{"question": "هل تغيّر mov الأعلام؟", "choices": ["نعم دائمًا", "لا", "فقط إذا كانت القيمة صفرًا"], "answer": 1, "explanation": "mov وlea لا تغيّران الأعلام، لذلك يمكن وضعهما بين cmp والقفزة."}
```

## الخلاصة

- الأعلام `ZF` و`SF` و`CF` و`OF` تصف ناتج آخر عملية حسابية أو منطقية.
- `cmp` = طرح بلا تخزين، و`test` = AND بلا تخزين.
- `jmp` قفز دائم؛ `je`/`jne`/`jg`/`jl`/`ja`/`jb` وأخواتها قفز مشروط.
- `if`: قارن ثم اقفز فوق ما لا تريد؛ وفي `if/else` لا تنس `jmp` في آخر الفرع الأول.
- `g`/`l` بإشارة، و`a`/`b` بلا إشارة؛ و`setcc`/`cmovcc` بدائل بلا قفز.
