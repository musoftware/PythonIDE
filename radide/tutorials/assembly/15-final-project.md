# الدرس 15: المشروع النهائي: محلّل الأعداد

**في هذا المشروع ستجمع كل ما تعلمته:**

- قراءة مدخلات المستخدم بـ `scanf` في حلقة وتخزينها في مصفوفة (`.bss`).
- مشروع من **ملفين**: `main.asm` للبرنامج و`stats.asm` لمكتبة دوال مع `global` و`extern`.
- دوال حسابية: المجموع والأصغر والأكبر، وفحص العدد الأولي، والترتيب بالفقاعات (Bubble Sort).
- تقرير مطبوع ورسم بياني بالنجوم.

## ماذا سيفعل البرنامج؟

يسأل المستخدم عن عدد الأعداد (من 1 إلى 20)، ثم يقرؤها، ثم يطبع:

```text
Sorted: 5 7 9 12 21 33
Sum: 87
Min: 5  Max: 33
Average: 14 (remainder 3)
Primes: 5 7
Chart (* = 3):
  5 | *
 ...
```

## تصميم المشروع

| الملف | المحتوى |
|---|---|
| `main.asm` | `main`: القراءة والتقرير والرسم؛ يستدعي دوال `stats.asm` |
| `stats.asm` | `arr_sum` و`arr_min` و`arr_max` و`is_prime` و`bubble_sort` |

كل دوال `stats.asm` **ورقية** (لا تستدعي غيرها) وتستخدم المسجلات المتطايرة فقط، فلا تحتاج حفظ شيء ولا تجهيز مكدس. أما `main` فتستدعي `printf` و`scanf` كثيرًا، لذلك تضع ما تحتاجه في المسجلات المحفوظة:

| المسجل | المعنى في main |
|---|---|
| `rsi` | عنوان المصفوفة `nums` |
| `r12` | عدد الأعداد `n` |
| `rbx` | فهرس الحلقات |
| `rdi` | المجموع، ثم عدد النجوم في الرسم |

أربعة `push` تعني: 8 (الدخول) + 32 = 40، أي `rsp` = 16k + 8، فنطرح `40` لنعود إلى مضاعف 16 مع مساحة الظل.

## إضافة ملف إلى المشروع

في RAD IDE: **Project > Add Module...** (مشروع > إضافة وحدة) واكتب `stats`. الـ IDE تجمّع كل ملفات `.asm` في المشروع وتربطها معًا، و`global` في ملف و`extern` في الآخر يربطان الأسماء.

## الكود الكامل

```asm run
; #file: main.asm
; محلّل الأعداد - البرنامج الرئيسي
default rel
global main
extern printf, scanf, putchar
extern arr_sum, arr_min, arr_max, is_prime, bubble_sort   ; من stats.asm

MAXN equ 20

section .data
    fmt_int    db "%d", 0
    msg_count  db "How many numbers (1-20)?", 10, 0
    msg_bad    db "Please enter 1 to 20 numbers.", 10, 0
    fmt_num    db "%d ", 0
    hdr_sorted db "Sorted: ", 0
    fmt_sum    db "Sum: %d", 10, 0
    fmt_minmax db "Min: %d  Max: %d", 10, 0
    fmt_avg    db "Average: %d (remainder %d)", 10, 0
    hdr_primes db "Primes: ", 0
    hdr_chart  db "Chart (* = 3):", 10, 0
    fmt_bar    db "%3d | ", 0

section .bss
    n    resd 1
    nums resd MAXN

section .text
main:
    push rbx
    push rsi
    push rdi
    push r12
    sub rsp, 40

    ; ---- كم عددًا؟
    lea rcx, [msg_count]
    call printf
    lea rcx, [fmt_int]
    lea rdx, [n]
    call scanf
    mov r12d, [n]
    cmp r12d, 1
    jl .bad
    cmp r12d, MAXN
    jg .bad

    ; ---- اقرأ الأعداد في nums
    lea rsi, [nums]
    xor ebx, ebx
.read:
    lea rcx, [fmt_int]
    lea rdx, [rsi + rbx*4]       ; عنوان nums[i]
    call scanf
    inc ebx
    cmp ebx, r12d
    jl .read

    ; ---- رتّب واطبع
    mov rcx, rsi
    mov edx, r12d
    call bubble_sort
    lea rcx, [hdr_sorted]
    call printf
    xor ebx, ebx
.print_sorted:
    lea rcx, [fmt_num]
    mov edx, [rsi + rbx*4]
    call printf
    inc ebx
    cmp ebx, r12d
    jl .print_sorted
    mov ecx, 10
    call putchar

    ; ---- المجموع
    mov rcx, rsi
    mov edx, r12d
    call arr_sum
    mov edi, eax                 ; نحتاجه للمتوسط
    lea rcx, [fmt_sum]
    mov edx, eax
    call printf

    ; ---- الأصغر والأكبر
    mov rcx, rsi
    mov edx, r12d
    call arr_min
    mov ebx, eax
    mov rcx, rsi
    mov edx, r12d
    call arr_max
    lea rcx, [fmt_minmax]
    mov edx, ebx
    mov r8d, eax
    call printf

    ; ---- المتوسط (قسمة بإشارة)
    mov eax, edi
    cdq
    idiv r12d
    lea rcx, [fmt_avg]
    mov r8d, edx                 ; الباقي
    mov edx, eax                 ; الخارج
    call printf

    ; ---- الأعداد الأولية
    lea rcx, [hdr_primes]
    call printf
    xor ebx, ebx
.primes:
    mov ecx, [rsi + rbx*4]
    call is_prime
    test eax, eax
    jz .not_prime
    lea rcx, [fmt_num]
    mov edx, [rsi + rbx*4]
    call printf
.not_prime:
    inc ebx
    cmp ebx, r12d
    jl .primes
    mov ecx, 10
    call putchar

    ; ---- الرسم البياني: نجمة لكل 3
    lea rcx, [hdr_chart]
    call printf
    xor ebx, ebx
.bar:
    lea rcx, [fmt_bar]
    mov edx, [rsi + rbx*4]
    call printf
    mov eax, [rsi + rbx*4]
    cdq
    mov ecx, 3
    idiv ecx
    mov edi, eax                 ; عدد النجوم
.star:
    test edi, edi
    jle .bar_end
    mov ecx, '*'
    call putchar
    dec edi
    jmp .star
.bar_end:
    mov ecx, 10
    call putchar
    inc ebx
    cmp ebx, r12d
    jl .bar
    jmp .done

.bad:
    lea rcx, [msg_bad]
    call printf
.done:
    xor eax, eax
    add rsp, 40
    pop r12
    pop rdi
    pop rsi
    pop rbx
    ret

; #file: stats.asm
; محلّل الأعداد - مكتبة الدوال (كلها ورقية: rax, rcx, rdx, r8-r10 فقط)
default rel
global arr_sum, arr_min, arr_max, is_prime, bubble_sort

section .text

; int arr_sum(const int *a, int n)
arr_sum:
    xor eax, eax
    xor r8d, r8d                 ; i
.next:
    cmp r8d, edx
    jge .done
    add eax, [rcx + r8*4]
    inc r8d
    jmp .next
.done:
    ret

; int arr_min(const int *a, int n)  (n >= 1)
arr_min:
    mov eax, [rcx]
    mov r8d, 1
.next:
    cmp r8d, edx
    jge .done
    mov r9d, [rcx + r8*4]
    cmp r9d, eax
    cmovl eax, r9d
    inc r8d
    jmp .next
.done:
    ret

; int arr_max(const int *a, int n)  (n >= 1)
arr_max:
    mov eax, [rcx]
    mov r8d, 1
.next:
    cmp r8d, edx
    jge .done
    mov r9d, [rcx + r8*4]
    cmp r9d, eax
    cmovg eax, r9d
    inc r8d
    jmp .next
.done:
    ret

; int is_prime(int n) -> 1 / 0 : جرّب القواسم d من 2 ما دام d*d <= n
is_prime:
    xor eax, eax
    cmp ecx, 2
    jl .done                     ; الأعداد الأصغر من 2 ليست أولية
    mov r8d, ecx                 ; n
    mov r9d, 2                   ; d
.try:
    mov eax, r9d
    imul eax, r9d
    cmp eax, r8d
    jg .prime                    ; d*d > n: لا قاسم
    mov eax, r8d
    xor edx, edx
    div r9d
    test edx, edx
    jz .composite                ; d يقسم n
    inc r9d
    jmp .try
.prime:
    mov eax, 1
    ret
.composite:
    xor eax, eax
.done:
    ret

; void bubble_sort(int *a, int n) - ترتيب تصاعدي في المكان
bubble_sort:
    mov r8d, edx
    dec r8d                      ; عدد المرات = n - 1
.outer:
    cmp r8d, 0
    jle .done
    xor r9d, r9d                 ; j
.inner:
    cmp r9d, r8d
    jge .next_pass
    mov eax, [rcx + r9*4]
    mov r10d, [rcx + r9*4 + 4]
    cmp eax, r10d
    jle .no_swap
    mov [rcx + r9*4], r10d       ; بدّل الجارين
    mov [rcx + r9*4 + 4], eax
.no_swap:
    inc r9d
    jmp .inner
.next_pass:
    dec r8d
    jmp .outer
.done:
    ret
```

```text input
6
12 7 33 5 21 9
```

```text output
How many numbers (1-20)?
Sorted: 5 7 9 12 21 33
Sum: 87
Min: 5  Max: 33
Average: 14 (remainder 3)
Primes: 5 7
Chart (* = 3):
  5 | *
  7 | **
  9 | ***
 12 | ****
 21 | *******
 33 | ***********
```

## كيف يعمل؟ أهم النقاط

- **`lea rdx, [rsi + rbx*4]`** في حلقة القراءة: `scanf` تحتاج **عنوان** العنصر `nums[i]`، و`lea` تحسبه دون قراءة.
- **الترتيب بالفقاعات:** في كل مرور نقارن كل جارين ونبدّلهما إذا كانا بترتيب خاطئ؛ بعد المرور الأول يصل الأكبر إلى آخر المصفوفة، فيقصر المرور التالي بواحد (`dec r8d`).
- **`is_prime`:** يكفي تجربة القواسم حتى الجذر التربيعي، أي ما دام `d * d <= n`.
- **`cmovl` و`cmovg`** في `arr_min` و`arr_max`: بلا قفزات داخل الحلقة.
- **`%3d`** في `printf` تحجز 3 خانات للعدد، فتصطف الأشرطة.
- **المسجلات:** `stats.asm` لا تلمس إلا المتطايرة، و`main` تحفظ `rbx` و`rsi` و`rdi` و`r12` وتعيدها بالترتيب العكسي.

## جرّبه في المنقّح

1. ضع نقطة توقف في `bubble_sort` على `cmp eax, r10d`.
2. اضغط `F5`، واكتب المدخلات في **Program Input**.
3. افتح **Memory 1** على `nums` (أو `$rcx`) واضغط `F5` مرة بعد مرة: سترى الأعداد تتبادل أماكنها.
4. في **Call Stack** ترى `bubble_sort` مستدعاة من `main`.

## تمرين: عدّ الأعداد الزوجية

أضف دالة `count_even(a, n)` تعيد عدد الأعداد الزوجية (البت الأدنى = 0). هنا نسخة صغيرة في ملف واحد لتختبر الدالة: للمصفوفة `12, 7, 33, 5, 21, 8` يطبع `Even numbers: 2`.

```asm exercise
default rel
global main
extern printf

section .data
    arr   dd 12, 7, 33, 5, 21, 8
    count equ ($ - arr) / 4
    fmt   db "Even numbers: %d", 10, 0

section .text
; int count_even(const int *a, int n)
count_even:
    xor eax, eax
    ; أكمل: لكل عنصر، test بالبت 1
    ret

main:
    sub rsp, 40
    lea rcx, [arr]
    mov edx, count
    call count_even
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
    arr   dd 12, 7, 33, 5, 21, 8
    count equ ($ - arr) / 4
    fmt   db "Even numbers: %d", 10, 0

section .text
count_even:
    xor eax, eax
    xor r8d, r8d
.next:
    cmp r8d, edx
    jge .done
    test dword [rcx + r8*4], 1
    jnz .odd
    inc eax
.odd:
    inc r8d
    jmp .next
.done:
    ret

main:
    sub rsp, 40
    lea rcx, [arr]
    mov edx, count
    call count_even
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
Even numbers: 2
```

## أفكار لتطوير المشروع

- انقل `count_even` إلى `stats.asm` واطبع عدد الزوجي والفردي في التقرير.
- اطبع **الوسيط** (Median): بعد الترتيب هو العنصر `nums[n / 2]` (لعدد فردي من العناصر).
- اقرأ الأعداد حتى يكتب المستخدم 0 بدل أن تسأله عن عددها أولًا.
- حوّل البرنامج إلى نموذج رسومي (الدرس 12): مربع نص للأعداد، وزر «حلّل»، وقائمة للنتائج.
- اكتب نسخة 8086 في المحاكي (الدرس 13) بـ `SCAN_NUM` و`PRINT_NUM`.

## اختبر نفسك

```quiz
{"question": "كيف يرى main الدالة arr_sum المعرّفة في stats.asm؟", "choices": ["تلقائيًّا", "global arr_sum في stats.asm وextern arr_sum في main.asm", "بـ %include فقط", "لا يمكن"], "answer": 1, "explanation": "global تصدّر الاسم من ملفه، وextern تعلن أنه في ملف آخر، والرابط يصل بينهما."}
```

```quiz
{"question": "لماذا لا تحتاج دوال stats.asm إلى push/pop أو sub rsp؟", "choices": ["لأنها قصيرة", "لأنها ورقية لا تستدعي غيرها وتستخدم المسجلات المتطايرة فقط", "لأن NASM يفعلها تلقائيًّا", "خطأ: تحتاجها"], "answer": 1, "explanation": "مساحة الظل والمحاذاة لازمة قبل call، والمسجلات المتطايرة لا تُحفظ."}
```

```quiz
{"question": "ما الحد الذي يكفي لتجربة القواسم عند فحص عدد أولي n؟", "choices": ["n", "n / 2", "حتى d * d > n", "10"], "answer": 2, "explanation": "إذا كان n = a × b فأحدهما لا يتجاوز الجذر التربيعي لـ n."}
```

## الخلاصة

- مشروع من عدة ملفات: `global` للتصدير و`extern` للاستيراد.
- `scanf` في حلقة مع `lea rdx, [rsi + rbx*4]`.
- الدوال الورقية بسيطة؛ و`main` تحفظ المسجلات المحفوظة التي تستخدمها.
- خوارزميات حقيقية بلغة التجميع: المجموع والأصغر والأكبر والأولي والترتيب بالفقاعات.

مبروك! أنهيت الدورة. أنت الآن تفهم ما يحدث **تحت** كل لغة برمجة: المسجلات، والذاكرة، والمكدس، واستدعاء الدوال. القاموس في الدرس التالي مرجع سريع للمصطلحات.
