# الدرس 7: حلقات التكرار

**في هذا الدرس ستتعلم:**

- بناء حلقات `while` و`do-while` و`for` من المقارنة والقفز.
- التعليمة `loop` وعدّادها `rcx`.
- لماذا يضيع العدّاد بعد `call printf`، وكيف نحفظه في مسجل **محفوظ** (`rbx` و`rsi` و`rdi` ...).
- الحلقات المتداخلة.

## الحلقة = قفزة إلى الخلف

في الدرس السابق قفزنا **إلى الأمام** لنتخطى كودًا. إذا قفزنا **إلى الخلف** نكرر الكود: هذه هي الحلقة. مجموع الأعداد من 1 إلى 100:

```text
sum = 0
i = 1
while i <= 100:
    sum += i
    i += 1
```

```asm run
default rel
global main
extern printf

section .data
    fmt db "1 + 2 + ... + 100 = %d", 10, 0

section .text
main:
    sub rsp, 40
    xor eax, eax             ; sum = 0
    mov ecx, 1               ; i = 1
.while:
    cmp ecx, 100
    jg .end                  ; الشرط في الأعلى: while
    add eax, ecx             ; sum += i
    inc ecx                  ; i += 1
    jmp .while               ; ارجع إلى الشرط
.end:
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
1 + 2 + ... + 100 = 5050
```

## `do-while`: الشرط في الأسفل

إذا كنا متأكدين أن الحلقة تعمل مرة واحدة على الأقل نضع الشرط في الأسفل، فنوفر قفزة في كل دورة. هذا ما تفعله المترجمات عادة. مثال: عدد خانات العدد 1234567 ومجموعها، بالقسمة على 10 حتى يصبح صفرًا:

```asm run
default rel
global main
extern printf

section .data
    fmt db "%d has %d digits, their sum is %d", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 1234567
    xor r8d, r8d             ; عدد الخانات
    xor r9d, r9d             ; مجموع الخانات
    mov ecx, 10
.next_digit:
    xor edx, edx
    div ecx                  ; eax = eax / 10، edx = الخانة الأخيرة
    add r9d, edx
    inc r8d
    test eax, eax
    jnz .next_digit          ; ما زال هناك خانات
    lea rcx, [fmt]
    mov edx, 1234567
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
1234567 has 7 digits, their sum is 28
```

## التعليمة loop

`loop label` تساوي `dec rcx` ثم «اقفز إذا لم يصبح `rcx` صفرًا». مناسبة للعد التنازلي. مضروب 10 (‎10! = 10 × 9 × ... × 1):

```asm run
default rel
global main
extern printf

section .data
    fmt db "10! = %d", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, 1
    mov ecx, 10              ; عدد الدورات
.mul:
    imul eax, ecx
    loop .mul                ; rcx--، وإذا لم يصبح 0 كرر
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
10! = 3628800
```

> **ملاحظة:** `loop` تستخدم `rcx` كاملًا، وإذا بدأت و`rcx = 0` فستدور 2^64 مرة تقريبًا! والمعالجات الحديثة تنفذ `dec` + `jnz` أسرع منها، لذلك تراها المترجمات قليلًا.

## الطباعة داخل الحلقة: أين ذهب العدّاد؟

لو استخدمنا `ecx` عدّادًا واستدعينا `printf` داخل الحلقة، فستتغير قيمته: `printf` تملك الحق في تغيير المسجلات **المتطايرة** `rax` و`rcx` و`rdx` و`r8` إلى `r11`. الحل: نضع العدّاد في مسجل **محفوظ** (Non-volatile): `rbx` و`rsi` و`rdi` و`rbp` و`r12` إلى `r15`. أي دالة تستدعيها **تعيدها كما كانت**.

لكن العقد متبادل: `main` نفسها دالة، ومن استدعاها يتوقع أن تعيد `rbx` كما كان. لذلك نحفظه في أول `main` بـ `push` ونعيده في آخرها بـ `pop`:

```asm run
default rel
global main
extern printf

section .data
    fmt db "i = %d", 10, 0

section .text
main:
    push rbx                 ; احفظ rbx لمن استدعى main
    sub rsp, 32              ; المكدس الآن مضبوط على 16 (الدرس 9)
    mov ebx, 1               ; العدّاد في rbx: لا تغيّره printf
.loop:
    lea rcx, [fmt]
    mov edx, ebx
    call printf
    inc ebx
    cmp ebx, 5
    jle .loop
    xor eax, eax
    add rsp, 32
    pop rbx                  ; أعد rbx كما كان
    ret
```

```text output
i = 1
i = 2
i = 3
i = 4
i = 5
```

لاحظ أن `sub rsp, 40` أصبحت `sub rsp, 32`: الـ `push` أنزلت المكدس 8 بايتات بالفعل. القاعدة (وتفسيرها في الدرس 9): عدد البايتات المطروحة + 8 لكل `push` يجب أن يكون 8 زائد مضاعفًا لـ 16، أي `40` بلا `push`، و`32` مع `push` واحد، و`40` مع اثنين، و`32` مع ثلاثة.

## حلقات متداخلة

حلقة داخل حلقة: لكل سطر `i` من 1 إلى 4 نطبع `i` نجوم. نحتاج عدّادين محفوظين: `rbx` للسطر و`rsi` للنجوم. والدالة `putchar` تطبع حرفًا واحدًا (`rcx` = الحرف):

```asm run
default rel
global main
extern putchar

section .text
main:
    push rbx
    push rsi
    sub rsp, 40              ; اثنان push + 40 = مضبوط
    mov ebx, 1               ; السطر
.row:
    xor esi, esi             ; عدد النجوم المطبوعة في هذا السطر
.star:
    mov ecx, '*'
    call putchar
    inc esi
    cmp esi, ebx
    jl .star                 ; ما زال في السطر نجوم
    mov ecx, 10              ; سطر جديد
    call putchar
    inc ebx
    cmp ebx, 4
    jle .row
    xor eax, eax
    add rsp, 40
    pop rsi                  ; بالترتيب العكسي
    pop rbx
    ret
```

```text output
*
**
***
****
```

## أخطاء شائعة

- **حلقة لا تنتهي:** نسيان `inc` أو القفز إلى لافتة خاطئة. في الـ IDE اضغط زر الإيقاف (**Debug > Stop Debugging** أو `Shift+F5`).
- **العدّاد في مسجل متطاير** مع `call` داخل الحلقة: يتغير العدّاد عشوائيًّا.
- **`pop` بترتيب خاطئ:** آخر ما دخل المكدس هو أول ما يخرج؛ إذا عكست الترتيب تتبادل القيم.

## تمارين

### التمرين 1

اطبع الأعداد الزوجية من 2 إلى 10 في سطر واحد: `2 4 6 8 10` (استخدم `"%d "` ثم `putchar(10)` في النهاية).

```asm exercise
default rel
global main
extern printf, putchar

section .data
    fmt db "%d ", 0

section .text
main:
    push rbx
    sub rsp, 32
    mov ebx, 2
    ; الحلقة هنا

    mov ecx, 10
    call putchar
    xor eax, eax
    add rsp, 32
    pop rbx
    ret
```

```asm solution
default rel
global main
extern printf, putchar

section .data
    fmt db "%d ", 0

section .text
main:
    push rbx
    sub rsp, 32
    mov ebx, 2
.loop:
    lea rcx, [fmt]
    mov edx, ebx
    call printf
    add ebx, 2
    cmp ebx, 10
    jle .loop
    mov ecx, 10
    call putchar
    xor eax, eax
    add rsp, 32
    pop rbx
    ret
```

```text output
2 4 6 8 10
```

### التمرين 2

اطبع أول 10 أعداد من متتالية **فيبوناتشي** (كل عدد = مجموع العددين قبله): `0 1 1 2 3 5 8 13 21 34`. تحتاج ثلاثة مسجلات محفوظة: العدّاد والعددين الأخيرين.

```asm exercise
default rel
global main
extern printf, putchar

section .data
    fmt db "%d ", 0

section .text
main:
    push rbx                 ; العدّاد
    push rsi                 ; a
    push rdi                 ; b
    sub rsp, 32
    ; a = 0، b = 1، كرر 10 مرات: اطبع a ثم (a, b) = (b, a + b)

    mov ecx, 10
    call putchar
    xor eax, eax
    add rsp, 32
    pop rdi
    pop rsi
    pop rbx
    ret
```

```asm solution
default rel
global main
extern printf, putchar

section .data
    fmt db "%d ", 0

section .text
main:
    push rbx
    push rsi
    push rdi
    sub rsp, 32
    mov ebx, 10
    xor esi, esi             ; a = 0
    mov edi, 1               ; b = 1
.next:
    lea rcx, [fmt]
    mov edx, esi
    call printf
    lea eax, [rsi + rdi]     ; a + b
    mov esi, edi             ; a = b
    mov edi, eax             ; b = a + b
    dec ebx
    jnz .next
    mov ecx, 10
    call putchar
    xor eax, eax
    add rsp, 32
    pop rdi
    pop rsi
    pop rbx
    ret
```

```text output
0 1 1 2 3 5 8 13 21 34
```

## اختبر نفسك

```quiz
{"question": "ماذا تفعل التعليمة loop .again ؟", "choices": ["تقفز دائمًا", "تنقص rcx وتقفز إذا لم يصبح صفرًا", "تزيد rcx وتقفز", "تكرر التعليمة التالية"], "answer": 1, "explanation": "loop = dec rcx ثم القفز إذا كان rcx لا يساوي صفرًا."}
```

```quiz
{"question": "أي مسجل يصلح عدّادًا لحلقة فيها call printf؟", "choices": ["rcx", "rdx", "rbx", "r8"], "answer": 2, "explanation": "rbx محفوظ: الدوال المستدعاة تعيده كما كان. rcx وrdx وr8 متطايرة."}
```

```quiz
{"question": "ما ميزة وضع شرط الحلقة في الأسفل (do-while)؟", "choices": ["تعمل الحلقة مرة على الأقل وبقفزة أقل في كل دورة", "لا تنتهي أبدًا", "لا تحتاج لافتات", "أبطأ"], "answer": 0, "explanation": "قفزة شرطية واحدة في كل دورة بدل قفزتين."}
```

## الخلاصة

- الحلقة قفزة إلى الخلف: `while` الشرط في الأعلى، و`do-while` الشرط في الأسفل.
- `loop` = `dec rcx` + `jnz`.
- مع `call` داخل الحلقة: العدّاد في `rbx`/`rsi`/`rdi`/`r12`-`r15`، و`push` في أول `main` و`pop` بالعكس في آخرها.
- حجز المكدس: `40` بلا `push`، و`32` مع واحد، و`40` مع اثنين، و`32` مع ثلاثة.
