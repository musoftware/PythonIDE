# الدرس 8: المصفوفات وطرق العنونة

**في هذا الدرس ستتعلم:**

- طرق العنونة في x86-64: `[reg]` و`[reg + ثابت]` و`[أساس + فهرس × مقياس + ثابت]`.
- لماذا نحمّل عنوان المصفوفة بـ `lea` أولًا في برامج ويندوز 64 بت.
- المرور على مصفوفة: المجموع والمتوسط والأكبر وموضعه.
- عكس مصفوفة في مكانها، والمصفوفات ثنائية الأبعاد.

## المصفوفة في الذاكرة

المصفوفة ليست إلا عناصر متتالية في الذاكرة بنفس الحجم:

```asm
section .data
    arr dd 12, 7, 33, 5, 21, 9      ; 6 عناصر، كل عنصر 4 بايتات
    count equ ($ - arr) / 4         ; يحسبها المجمّع: 6
```

| الفهرس | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| العنوان | arr | arr+4 | arr+8 | arr+12 | arr+16 | arr+20 |
| القيمة | 12 | 7 | 33 | 5 | 21 | 9 |

عنوان العنصر رقم `i` = **عنوان البداية + i × حجم العنصر**.

## طرق العنونة

يستطيع المعالج حساب العنوان داخل التعليمة نفسها بالصيغة العامة:

```text
[ أساس + فهرس × مقياس + إزاحة ]
```

- **الأساس** (base) و**الفهرس** (index): أي مسجلين 64 بت.
- **المقياس** (scale): 1 أو 2 أو 4 أو 8 فقط (أحجام byte وword وdword وqword).
- **الإزاحة** (displacement): رقم ثابت.

| الكتابة | المعنى |
|---|---|
| `[rsi]` | العنصر الذي يشير إليه `rsi` |
| `[rsi + 8]` | بعده بـ 8 بايتات |
| `[rsi + rcx*4]` | العنصر رقم `rcx` من مصفوفة dword تبدأ عند `rsi` |
| `[rsi + rcx*8 + 16]` | مثلًا: حقل في سجل داخل مصفوفة qword |

## فخ ويندوز 64 بت: حمّل العنوان أولًا

تبدو هذه الكتابة منطقية:

```asm
    mov edx, [arr + rcx*4]
```

لكنها تفشل عند الربط:

```text
main.obj:main.asm:(.text+0xc): relocation truncated to fit: IMAGE_REL_AMD64_ADDR32 against `.data'
collect2.exe: error: ld returned 1 exit status
```

السبب: العنونة النسبية لـ `rip` (التي يفعّلها `default rel`) لا تقبل مسجل فهرس، فيعود NASM إلى عنوان مطلق 32 بت، وبرامج ويندوز 64 بت تُحمَّل في عناوين أكبر من ذلك. الحل دائمًا: **حمّل عنوان البداية في مسجل بـ `lea`** ثم استخدمه أساسًا:

```asm
    lea rsi, [arr]
    mov edx, [rsi + rcx*4]
```

## المجموع والمتوسط

```asm run
default rel
global main
extern printf

section .data
    arr   dd 12, 7, 33, 5, 21, 9
    count equ ($ - arr) / 4
    fmt   db "sum=%d count=%d average=%d", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]           ; عنوان البداية
    xor eax, eax             ; المجموع
    xor ecx, ecx             ; الفهرس i = 0
.next:
    add eax, [r10 + rcx*4]   ; sum += arr[i]
    inc ecx
    cmp ecx, count
    jl .next

    mov r10d, eax            ; احفظ المجموع
    cdq
    mov ecx, count
    idiv ecx                 ; eax = المتوسط (قسمة صحيحة)
    mov r9d, eax
    mov r8d, count
    mov edx, r10d
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
sum=87 count=6 average=14
```

استخدمنا `r10` للعنوان لأنه مسجل متطاير لا نحتاج إلى حفظه، ولا يوجد `call` داخل الحلقة يغيّره.

## الأكبر وموضعه: المرور بمؤشر

بدل الفهرس يمكن **تحريك المؤشر** نفسه: `add rsi, 4` ينقله إلى العنصر التالي:

```asm run
default rel
global main
extern printf

section .data
    arr   dd 12, 7, 33, 5, 21, 9
    count equ ($ - arr) / 4
    fmt   db "max=%d at index %d", 10, 0

section .text
main:
    push rsi
    sub rsp, 32
    lea rsi, [arr]
    mov edx, [rsi]           ; الأكبر حتى الآن = arr[0]
    xor r8d, r8d             ; موضعه
    mov ecx, 1               ; i
.next:
    add rsi, 4               ; المؤشر إلى العنصر التالي
    mov eax, [rsi]
    cmp eax, edx
    jle .skip
    mov edx, eax             ; وجدنا أكبر
    mov r8d, ecx
.skip:
    inc ecx
    cmp ecx, count
    jl .next
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 32
    pop rsi
    ret
```

```text output
max=33 at index 2
```

## عكس المصفوفة في مكانها

مؤشران: واحد من البداية وواحد من النهاية، نبدّل ما يشيران إليه ونقرّبهما حتى يلتقيا. ثم نطبع المصفوفة:

```asm run
default rel
global main
extern printf, putchar

section .data
    arr   dd 12, 7, 33, 5, 21, 9
    count equ ($ - arr) / 4
    fmt   db "%d ", 0

section .text
main:
    push rbx
    push rsi
    sub rsp, 40
    lea rsi, [arr]                       ; اليسار
    lea rdi, [arr + (count - 1) * 4]     ; اليمين: ثابت يحسبه المجمّع، بلا مسجل فهرس
.swap:
    cmp rsi, rdi
    jae .print                           ; التقيا (عناوين: مقارنة بلا إشارة)
    mov eax, [rsi]
    mov edx, [rdi]
    mov [rsi], edx
    mov [rdi], eax
    add rsi, 4
    sub rdi, 4
    jmp .swap

.print:
    xor ebx, ebx                         ; i
    lea rsi, [arr]
.each:
    lea rcx, [fmt]
    mov edx, [rsi + rbx*4]
    call printf
    inc ebx
    cmp ebx, count
    jl .each
    mov ecx, 10
    call putchar
    xor eax, eax
    add rsp, 40
    pop rsi
    pop rbx
    ret
```

```text output
9 21 5 33 7 12
```

لاحظ `[arr + (count - 1) * 4]`: لا يوجد مسجل فهرس، فالعنوان ثابت ويقبل العنونة النسبية. واستخدمنا `rdi` بلا حفظ لأنه لا يُستخدم بعد أي `call`؛ أما `rsi` و`rbx` فيمرّان بـ `call printf` لذلك هما في مسجلات محفوظة ومحفوظان بـ `push`.

## مصفوفة ثنائية الأبعاد

الذاكرة خط واحد، فالجدول يُخزَّن **صفًّا بعد صف**. عنوان العنصر `[row][col]` في جدول بعرض `COLS`:

```text
base + (row * COLS + col) * size
```

```asm run
default rel
global main
extern printf

COLS equ 3

section .data
    m   dd 1, 2, 3
        dd 4, 5, 6
        dd 7, 8, 9
    fmt db "m[1][2]=%d  diagonal sum=%d", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [m]
    mov eax, 1               ; row
    imul eax, eax, COLS
    add eax, 2               ; + col
    mov edx, [r10 + rax*4]   ; m[1][2]

    xor r8d, r8d             ; مجموع القطر m[i][i]
    xor ecx, ecx
.diag:
    imul eax, ecx, COLS + 1  ; (i * COLS + i)
    add r8d, [r10 + rax*4]
    inc ecx
    cmp ecx, COLS
    jl .diag

    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
m[1][2]=6  diagonal sum=15
```

## تمارين

### التمرين 1

كم عددًا في المصفوفة أكبر من 10؟ اطبع: `3 numbers > 10`.

```asm exercise
default rel
global main
extern printf

section .data
    arr   dd 12, 7, 33, 5, 21, 9
    count equ ($ - arr) / 4
    fmt   db "%d numbers > 10", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]
    xor edx, edx             ; العدد
    ; مر على العناصر بالفهرس ecx

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
    arr   dd 12, 7, 33, 5, 21, 9
    count equ ($ - arr) / 4
    fmt   db "%d numbers > 10", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]
    xor edx, edx
    xor ecx, ecx
.next:
    cmp dword [r10 + rcx*4], 10
    jle .skip
    inc edx
.skip:
    inc ecx
    cmp ecx, count
    jl .next
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
3 numbers > 10
```

### التمرين 2

اطبع أصغر عدد في المصفوفة: `min=5`.

```asm exercise
default rel
global main
extern printf

section .data
    arr   dd 12, 7, 33, 5, 21, 9
    count equ ($ - arr) / 4
    fmt   db "min=%d", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]
    mov edx, [r10]
    ; أكمل

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
    arr   dd 12, 7, 33, 5, 21, 9
    count equ ($ - arr) / 4
    fmt   db "min=%d", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [arr]
    mov edx, [r10]
    mov ecx, 1
.next:
    mov eax, [r10 + rcx*4]
    cmp eax, edx
    cmovl edx, eax
    inc ecx
    cmp ecx, count
    jl .next
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
min=5
```

## اختبر نفسك

```quiz
{"question": "مصفوفة qword تبدأ عند rsi. أي كتابة تصل إلى العنصر رقم rcx؟", "choices": ["[rsi + rcx]", "[rsi + rcx*4]", "[rsi + rcx*8]", "[rcx*8]"], "answer": 2, "explanation": "حجم qword 8 بايتات، فالمقياس 8."}
```

```quiz
{"question": "لماذا تفشل mov eax, [arr + rcx*4] في برنامج ويندوز 64 بت؟", "choices": ["المقياس 4 غير مسموح", "لا يمكن الجمع بين عنوان نسبي لـ rip ومسجل فهرس، والعنوان المطلق لا يتسع في 32 بت", "rcx لا يصلح فهرسًا", "لأن arr في .data"], "answer": 1, "explanation": "حمّل العنوان أولًا: lea rsi, [arr] ثم [rsi + rcx*4]."}
```

```quiz
{"question": "أي القيم مسموحة للمقياس؟", "choices": ["أي عدد", "1 و2 و4 و8", "2 و4 فقط", "من 1 إلى 16"], "answer": 1, "explanation": "المقياس 1 أو 2 أو 4 أو 8 فقط."}
```

## الخلاصة

- المصفوفة عناصر متتالية؛ العنصر `i` عند `البداية + i × الحجم`، وعدد العناصر `($ - arr) / الحجم`.
- الصيغة العامة `[أساس + فهرس × (1|2|4|8) + إزاحة]`.
- في ويندوز 64 بت: `lea rsi, [arr]` أولًا، ثم `[rsi + rcx*4]`.
- المرور بفهرس أو بتحريك المؤشر (`add rsi, 4`)، وقارن العناوين بـ `jb`/`jae`.
- الجدول ثنائي الأبعاد: `(row × COLS + col) × size`.
