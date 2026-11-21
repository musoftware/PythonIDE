# الدرس 5: العمليات الحسابية والمنطقية

**في هذا الدرس ستتعلم:**

- الجمع والطرح: `add` و`sub` و`inc` و`dec` و`neg`.
- الضرب: `imul` و`mul`، والقسمة: `div` و`idiv` مع `cdq`/`cqo`.
- العمليات المنطقية على البتات: `and` و`or` و`xor` و`not`.
- الإزاحة: `shl` و`shr` و`sar`، والحيلة `lea` للحساب السريع.

## الجمع والطرح

معظم تعليمات الحساب تأخذ شكل `تعليمة الوجهة, المصدر` وتضع الناتج في **الوجهة**:

| التعليمة | المعنى (بأسلوب لغات أخرى) |
|---|---|
| `add eax, ebx` | `eax = eax + ebx` |
| `sub eax, 5` | `eax = eax - 5` |
| `inc ecx` | `ecx = ecx + 1` |
| `dec ecx` | `ecx = ecx - 1` |
| `neg eax` | `eax = -eax` |

```asm run
default rel
global main
extern printf

section .data
    fmt db "sum=%d diff=%d neg=%d", 10, 0

section .text
main:
    sub rsp, 40
    mov edx, 25
    add edx, 17          ; 42

    mov r8d, 100
    sub r8d, 58          ; 42
    inc r8d              ; 43
    dec r8d              ; 42

    mov r9d, 42
    neg r9d              ; -42

    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
sum=42 diff=42 neg=-42
```

> **حيلة شهيرة:** `xor eax, eax` تصفّر المسجل (أي عدد XOR نفسه = 0)، وهي أقصر في لغة الآلة من `mov eax, 0`. لهذا تراها في نهاية `main`.

## الضرب

- `imul` للأعداد **بإشارة**، ولها ثلاثة أشكال مريحة:
  - `imul eax, ebx` ← `eax = eax * ebx`
  - `imul eax, ecx, 10` ← `eax = ecx * 10`
  - `imul ecx` (معامل واحد) ← `edx:eax = eax * ecx`
- `mul` للأعداد **بلا إشارة**، وله شكل واحد: `mul rcx` ← `rdx:rax = rax * rcx`. الناتج قد يحتاج 128 بت، فالنصف الأعلى يوضع في `rdx`.

```asm run
default rel
global main
extern printf

section .data
    fmt1 db "6*7=%d  12*10=%d", 10, 0
    fmt2 db "high=%llX low=%llX", 10, 0

section .text
main:
    sub rsp, 40
    mov edx, 6
    mov eax, 7
    imul edx, eax            ; edx = 42
    mov ecx, 12
    imul r8d, ecx, 10        ; r8d = 120
    lea rcx, [fmt1]
    call printf

    mov rax, 0xFFFFFFFFFFFFFFFF
    mov rcx, 2
    mul rcx                  ; rdx:rax = الناتج 128 بت
    mov r8, rax              ; النصف الأدنى للمعامل الثالث
    lea rcx, [fmt2]          ; rdx فيه النصف الأعلى بالفعل
    call printf

    xor eax, eax
    add rsp, 40
    ret
```

```text output
6*7=42  12*10=120
high=1 low=FFFFFFFFFFFFFFFE
```

## القسمة

القسمة أكثر تعليمات الحساب «تطلّبًا»:

- المقسوم يكون في **زوج** مسجلات: `edx:eax` (لقسمة 32 بت) أو `rdx:rax` (لـ 64 بت).
- `div ecx` (بلا إشارة) أو `idiv ecx` (بإشارة) تقسم على `ecx`.
- الناتج: **خارج القسمة** في `eax`، و**الباقي** في `edx`.

لذلك يجب تجهيز `edx` قبل القسمة:

- بلا إشارة: صفّره بـ `xor edx, edx`.
- بإشارة: `cdq` تنسخ إشارة `eax` في كل `edx` (و`cqo` تفعل ذلك لـ `rax` و`rdx`).

```asm run
default rel
global main
extern printf

section .data
    fmt db "%d / 5 = %d remainder %d", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 47
    xor edx, edx             ; المقسوم edx:eax = 47
    mov ecx, 5
    div ecx                  ; eax = 9، edx = 2
    mov r9d, edx
    mov r8d, eax
    mov edx, 47
    lea rcx, [fmt]
    call printf

    mov eax, -47
    cdq                      ; edx = 0xFFFFFFFF (إشارة سالبة)
    mov ecx, 5
    idiv ecx                 ; eax = -9، edx = -2
    mov r9d, edx
    mov r8d, eax
    mov edx, -47
    lea rcx, [fmt]
    call printf

    xor eax, eax
    add rsp, 40
    ret
```

```text output
47 / 5 = 9 remainder 2
-47 / 5 = -9 remainder -2
```

> **تحذير:** القسمة على صفر، أو نسيان تجهيز `edx` بحيث لا يتسع الخارج في `eax`، يوقف البرنامج بخطأ **Integer divide by zero** (رمز `0xC0000094`). هذا أشهر انهيار لدى المبتدئين.

## العمليات المنطقية على البتات

تعمل على كل بت على حدة:

| التعليمة | البت الناتج يكون 1 عندما... | استخدام شائع |
|---|---|---|
| `and` | البتان كلاهما 1 | **إطفاء** بتات (قناع): `and eax, 0xFF` |
| `or` | أحدهما على الأقل 1 | **تشغيل** بتات |
| `xor` | البتان مختلفان | **قلب** بتات، والتصفير |
| `not` | (معامل واحد) يقلب كل البتات | |

مثال على `12` (`1100`) و`10` (`1010`):

```text
  1100        1100        1100
& 1010      | 1010      ^ 1010
= 1000 (8)  = 1110 (14) = 0110 (6)
```

## الإزاحة

- `shl eax, n` يزيح البتات يسارًا n خانة: يساوي **الضرب** في 2^n.
- `shr eax, n` يزيح يمينًا ويُدخل أصفارًا: **قسمة** بلا إشارة على 2^n.
- `sar eax, n` يزيح يمينًا ويحافظ على **الإشارة**: قسمة بإشارة (مع تقريب نحو الأسفل).

```asm run
default rel
global main
extern printf

section .data
    fmt1 db "and=%d or=%d xor=%d", 10, 0
    fmt2 db "shl=%d shr=%d sar=%d", 10, 0

section .text
main:
    sub rsp, 40
    mov edx, 12
    and edx, 10
    mov r8d, 12
    or r8d, 10
    mov r9d, 12
    xor r9d, 10
    lea rcx, [fmt1]
    call printf

    mov edx, 12
    shl edx, 2               ; 12 * 4 = 48
    mov r8d, 12
    shr r8d, 2               ; 12 / 4 = 3
    mov r9d, -16
    sar r9d, 2               ; -16 / 4 = -4
    lea rcx, [fmt2]
    call printf

    xor eax, eax
    add rsp, 40
    ret
```

```text output
and=8 or=14 xor=6
shl=48 shr=3 sar=-4
```

## lea كآلة حاسبة

`lea` تحسب «عنوانًا» من الشكل `[أساس + فهرس × (1 أو 2 أو 4 أو 8) + ثابت]` **دون قراءة الذاكرة**. المترجمات تستخدمها للحساب السريع:

```asm run
default rel
global main
extern printf

section .data
    fmt db "x*5=%d  x*9+7=%d", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 6
    lea edx, [rax + rax*4]       ; 6 * 5 = 30
    lea r8d, [rax + rax*8 + 7]   ; 6 * 9 + 7 = 61
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
x*5=30  x*9+7=61
```

## الفيضان (Overflow)

المسجل له حجم محدود. إذا تجاوز الناتج الحجم «يلتف» العدد كعداد السيارة: في 32 بت بلا إشارة `0xFFFFFFFF + 1 = 0`، وبإشارة `2147483647 + 1 = -2147483648`. المعالج لا يتوقف، لكنه يرفع **علمًا** يخبرك بما حدث؛ هذا موضوع الدرس القادم.

## تمارين

### التمرين 1

حوّل 37 درجة مئوية إلى فهرنهايت بالقانون `F = C * 9 / 5 + 32` (قسمة صحيحة) واطبع: `37C = 98F`.

```asm exercise
default rel
global main
extern printf

section .data
    fmt db "%dC = %dF", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 37
    ; اضرب في 9، اقسم على 5، أضف 32
    mov r8d, eax
    mov edx, 37
    lea rcx, [fmt]
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
    fmt db "%dC = %dF", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 37
    imul eax, eax, 9         ; 333
    cdq
    mov ecx, 5
    idiv ecx                 ; 66
    add eax, 32              ; 98
    mov r8d, eax
    mov edx, 37
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
37C = 98F
```

### التمرين 2

حوّل 3725 ثانية إلى ساعات ودقائق وثوانٍ: `1:02:05`. (اقسم على 3600 ثم اقسم الباقي على 60.)

```asm exercise
default rel
global main
extern printf

section .data
    fmt db "%d:%02d:%02d", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 3725
    ; edx = الساعات، r8d = الدقائق، r9d = الثواني
    lea rcx, [fmt]
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
    fmt db "%d:%02d:%02d", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 3725
    xor edx, edx
    mov ecx, 3600
    div ecx                  ; eax = 1 ساعة، edx = 125
    mov r10d, eax            ; احفظ الساعات
    mov eax, edx
    xor edx, edx
    mov ecx, 60
    div ecx                  ; eax = 2 دقيقة، edx = 5 ثوان
    mov r9d, edx
    mov r8d, eax
    mov edx, r10d
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
1:02:05
```

## اختبر نفسك

```quiz
{"question": "بعد div ecx، أين يوضع الباقي؟", "choices": ["eax", "ecx", "edx", "ebx"], "answer": 2, "explanation": "الخارج في eax والباقي في edx."}
```

```quiz
{"question": "ما فائدة cdq قبل idiv؟", "choices": ["تصفير eax", "نسخ إشارة eax إلى edx ليصبح edx:eax مقسومًا صحيحًا", "تحويل إلى عدد عشري", "لا فائدة"], "answer": 1, "explanation": "idiv تقسم edx:eax، فيجب أن يحمل edx إشارة eax."}
```

```quiz
{"question": "ما ناتج shl eax, 3 إذا كان eax = 5؟", "choices": ["8", "15", "40", "53"], "answer": 2, "explanation": "الإزاحة يسارًا 3 خانات = الضرب في 8: 5 × 8 = 40."}
```

```quiz
{"question": "أي تعليمة تطفئ كل البتات ما عدا البايت الأدنى من eax؟", "choices": ["or eax, 0xFF", "and eax, 0xFF", "xor eax, 0xFF", "not eax"], "answer": 1, "explanation": "AND مع قناع 0xFF يُبقي البتات الثمانية الدنيا ويصفّر الباقي."}
```

## الخلاصة

- `add`/`sub`/`inc`/`dec`/`neg` تضع الناتج في الوجهة.
- `imul` بإشارة (بأشكال مريحة)، و`mul` بلا إشارة في `rdx:rax`.
- القسمة تقسم `edx:eax`: جهّز `edx` بـ `xor edx, edx` (بلا إشارة) أو `cdq` (بإشارة)؛ الخارج في `eax` والباقي في `edx`.
- `and` لإطفاء البتات، و`or` لتشغيلها، و`xor` لقلبها، و`shl`/`shr`/`sar` للضرب والقسمة على قوى 2.
- `lea` تحسب `أساس + فهرس × مقياس + ثابت` بلا قراءة للذاكرة.
