# الدرس 9: المكدس والإجراءات واتفاقية الاستدعاء

**في هذا الدرس ستتعلم:**

- **المكدس** (Stack) والمسجل `rsp`، و`push` و`pop`.
- كيف تعمل `call` و`ret` من الداخل.
- كتابة **إجراءاتك** (دوالك) الخاصة: المعاملات وقيمة الرجوع.
- **اتفاقية الاستدعاء في ويندوز x64**: مساحة الظل (Shadow Space)، ومحاذاة 16، والمسجلات المحفوظة.
- إطار المكدس بـ `rbp` والمتغيرات المحلية، والمعامل الخامس فما بعده، والاستدعاء الذاتي (Recursion).

## المكدس

المكدس منطقة من الذاكرة تعمل مثل **كومة أطباق**: آخر طبق تضعه هو أول طبق تأخذه (LIFO: Last In, First Out). المسجل `rsp` (Stack Pointer) يشير دائمًا إلى **قمة** المكدس.

في x86 ينمو المكدس **نحو العناوين الأصغر** (إلى الأسفل):

| التعليمة | ما تفعله بالضبط |
|---|---|
| `push rax` | `rsp = rsp - 8` ثم `[rsp] = rax` |
| `pop rax` | `rax = [rsp]` ثم `rsp = rsp + 8` |

```text
قبل push 1 / push 2 / push 3:        بعدها:
                                      rsp -> | 3 |   (أصغر عنوان)
                                             | 2 |
                                             | 1 |
rsp -> | ... |                               | ... |
```

```asm run
default rel
global main
extern printf

section .data
    fmt db "popped: %d %d %d", 10, 0

section .text
main:
    sub rsp, 40
    push 1
    push 2
    push 3
    pop rdx                  ; آخر ما دخل: 3
    pop r8                   ; 2
    pop r9                   ; 1
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
popped: 3 2 1
```

في الوضع 64 بت تعمل `push` و`pop` على 8 بايتات (يمكن `push` لرقم ثابت أو مسجل 64 بت أو ذاكرة qword؛ أما `push eax` فخطأ: `instruction not valid with 32-bit operand size`).

## call وret من الداخل

- `call f` = `push` لعنوان التعليمة التالية (**عنوان الرجوع**) ثم القفز إلى `f`.
- `ret` = `pop` لعنوان الرجوع إلى `rip`.

لذلك يجب أن يكون `rsp` عند `ret` في **نفس المكان** الذي كان فيه عند الدخول: إذا نسيت `pop` أو `add rsp` فستقرأ `ret` قيمة خاطئة وتقفز إلى المجهول، وينهار البرنامج.

## إجراءاتك الخاصة

الإجراء (Procedure) لافتة تنتهي بـ `ret`. اتفاقية ويندوز x64:

- المعاملات الأربعة الأولى (أعداد ومؤشرات): `rcx` ثم `rdx` ثم `r8` ثم `r9`.
- قيمة الرجوع في `rax`.

الدالة **الورقية** (Leaf: لا تستدعي غيرها) لا تحتاج أي تجهيز للمكدس:

```asm run
default rel
global main
extern printf

section .data
    fmt db "square(9)=%d  add3(1,2,3)=%d", 10, 0

section .text
; long square(long x)  - x في rcx، الناتج في rax
square:
    mov rax, rcx
    imul rax, rcx
    ret

; long add3(long a, long b, long c)
add3:
    lea rax, [rcx + rdx]
    add rax, r8
    ret

main:
    push rbx
    sub rsp, 32
    mov ecx, 9
    call square
    mov rbx, rax             ; احفظ النتيجة في مسجل محفوظ

    mov ecx, 1
    mov edx, 2
    mov r8d, 3
    call add3

    mov r8, rax
    mov rdx, rbx
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 32
    pop rbx
    ret
```

```text output
square(9)=81  add3(1,2,3)=6
```

## اتفاقية الاستدعاء في ويندوز x64

هذه القواعد هي سر الأرقام `40` و`32` التي نكتبها منذ الدرس الأول:

1. **مساحة الظل (Shadow Space):** قبل أي `call` يحجز المستدعي **32 بايتًا** فوق عنوان الرجوع. الدالة المستدعاة قد تحفظ فيها `rcx` و`rdx` و`r8` و`r9`.
2. **المحاذاة:** عند تنفيذ `call` يجب أن يكون `rsp` من مضاعفات **16**. (بعض الدوال تستخدم تعليمات SSE تنهار إذا لم يكن المكدس محاذيًا.)
3. **المسجلات المتطايرة** `rax` و`rcx` و`rdx` و`r8`-`r11`: يحق للدالة تغييرها.
4. **المسجلات المحفوظة** `rbx` و`rbp` و`rdi` و`rsi` و`r12`-`r15`: يجب أن تعيدها الدالة كما كانت إذا استخدمتها.
5. المعامل **الخامس** فما بعده: على المكدس بعد مساحة الظل، أي في `[rsp + 32]` و`[rsp + 40]` ... لحظة `call`.

### لماذا 40؟

عند الدخول إلى أي دالة يكون `rsp` قد نقص 8 بسبب `call` (عنوان الرجوع)، أي أنه **ليس** مضاعفًا لـ 16 (يساوي 16k + 8). نحتاج 32 للظل، و32 + 8 = 40 تعيده مضاعفًا لـ 16:

```text
عند الدخول:          rsp = 16k + 8
sub rsp, 40:          rsp = 16k - 32   (مضاعف لـ 16)، و[rsp .. rsp+31] مساحة الظل
مع push rbx أولًا:    push (8) + sub rsp, 32 = 40 أيضًا
```

**الدالة غير الورقية** (تستدعي غيرها) تحتاج نفس التجهيز. هذه دالة تطبع عددًا:

```asm run
default rel
global main
extern printf

section .data
    fmt db "value: %d", 10, 0

section .text
; void print_num(int n)
print_num:
    sub rsp, 40              ; ظل + محاذاة لـ call printf
    mov edx, ecx             ; n يصبح المعامل الثاني
    lea rcx, [fmt]
    call printf
    add rsp, 40
    ret

main:
    sub rsp, 40
    mov ecx, 7
    call print_num
    mov ecx, 2026
    call print_num
    xor eax, eax
    add rsp, 40
    ret
```

```text output
value: 7
value: 2026
```

## أكثر من أربعة معاملات

`printf` بخمس قيم بعد النص تحتاج 6 معاملات: الأربعة الأولى في المسجلات، والخامس والسادس في `[rsp + 32]` و`[rsp + 40]`. نحجز 32 (ظل) + 16 (معاملان) + 8 (محاذاة) = **56**:

```asm run
default rel
global main
extern printf

section .data
    fmt db "%d %d %d %d %d", 10, 0

section .text
main:
    sub rsp, 56
    lea rcx, [fmt]           ; 1
    mov edx, 10              ; 2
    mov r8d, 20              ; 3
    mov r9d, 30              ; 4
    mov qword [rsp + 32], 40 ; 5: أول مكان بعد مساحة الظل
    mov qword [rsp + 40], 50 ; 6
    call printf
    xor eax, eax
    add rsp, 56
    ret
```

```text output
10 20 30 40 50
```

## إطار المكدس والمتغيرات المحلية

الدوال الأكبر تحتاج متغيرات **محلية**. الطريقة التقليدية: `rbp` يثبت على بداية «إطار» الدالة، والمتغيرات تحته بإزاحات سالبة:

```asm
func:
    push rbp                 ; احفظ rbp لمن استدعانا
    mov rbp, rsp             ; rbp = قاعدة الإطار
    sub rsp, 48              ; محليات (16) + ظل (32)؛ push rbp ضبطت المحاذاة
    ...                      ; [rbp - 8] و[rbp - 16] متغيرات محلية
    leave                    ; = mov rsp, rbp ثم pop rbp
    ret
```

مثال: دالة تملأ مصفوفة محلية بمربعات 1..5 وتعيد مجموعها:

```asm run
default rel
global main
extern printf

section .data
    fmt db "1^2 + ... + 5^2 = %d", 10, 0

section .text
sum_squares:
    push rbp
    mov rbp, rsp
    sub rsp, 32              ; مصفوفة محلية: 5 × 4 = 20 بايتًا (نحجز 32 للمحاذاة)
    xor ecx, ecx
.fill:                       ; local[i] = (i + 1)^2
    lea eax, [rcx + 1]
    imul eax, eax
    mov [rbp - 32 + rcx*4], eax
    inc ecx
    cmp ecx, 5
    jl .fill
    xor eax, eax
    xor ecx, ecx
.add:
    add eax, [rbp - 32 + rcx*4]
    inc ecx
    cmp ecx, 5
    jl .add
    leave
    ret

main:
    sub rsp, 40
    call sum_squares
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
1^2 + ... + 5^2 = 55
```

## الاستدعاء الذاتي (Recursion)

الدالة تستدعي نفسها، وكل استدعاء له إطاره على المكدس. `fact(n) = n × fact(n - 1)` و`fact(1) = 1`. نحتاج `n` بعد عودة الاستدعاء، فنحفظه في `rbx` (ونحفظ `rbx` القديم بـ `push`):

```asm run
default rel
global main
extern printf

section .data
    fmt db "fact(%d) = %lld", 10, 0

section .text
; long long fact(long long n)
fact:
    push rbx
    sub rsp, 32              ; push + 32 = 40: محاذاة صحيحة
    mov rbx, rcx             ; احفظ n
    mov eax, 1
    cmp rcx, 1
    jle .done                ; fact(1) = 1
    lea rcx, [rbx - 1]
    call fact                ; rax = fact(n - 1)
    imul rax, rbx            ; n × fact(n - 1)
.done:
    add rsp, 32
    pop rbx
    ret

main:
    sub rsp, 40
    mov ecx, 20
    call fact
    lea rcx, [fmt]
    mov edx, 20
    mov r8, rax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
fact(20) = 2432902008176640000
```

> **في المنقّح:** نافذة **Call Stack** (مكدس الاستدعاءات) تعرض استدعاءات `fact` المتداخلة أثناء التنفيذ خطوة بخطوة، ونافذة **Memory** تعرض المكدس نفسه وعناوين الرجوع.

## أخطاء شائعة

- **`push` بلا `pop`** قبل `ret`: تقفز `ret` إلى عنوان خاطئ.
- **نسيان مساحة الظل:** الدالة المستدعاة تكتب فوق بياناتك أو عنوان رجوعك.
- **مكدس غير محاذٍ:** قد يعمل `puts` وينهار `printf` لاحقًا بلا سبب ظاهر. احسب: (`push` × 8 + ما تطرحه) يجب أن يساوي 16k + 8.
- **استخدام `rbx`/`rsi`/`rdi` بلا حفظ** في دالة يستدعيها غيرك.

## تمارين

### التمرين 1

اكتب الدالة `max3(a, b, c)` التي تعيد أكبر الثلاثة، واطبع `max3(7, 19, 4) = 19`.

```asm exercise
default rel
global main
extern printf

section .data
    fmt db "max3(7, 19, 4) = %d", 10, 0

section .text
; long max3(long a, long b, long c) - rcx, rdx, r8 -> rax
max3:
    mov rax, rcx
    ; أكمل
    ret

main:
    sub rsp, 40
    mov ecx, 7
    mov edx, 19
    mov r8d, 4
    call max3
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
    fmt db "max3(7, 19, 4) = %d", 10, 0

section .text
max3:
    mov rax, rcx
    cmp rdx, rax
    cmovg rax, rdx
    cmp r8, rax
    cmovg rax, r8
    ret

main:
    sub rsp, 40
    mov ecx, 7
    mov edx, 19
    mov r8d, 4
    call max3
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
max3(7, 19, 4) = 19
```

### التمرين 2

اكتب دالة ذاتية الاستدعاء `power(base, exp)`: `power(b, 0) = 1` و`power(b, e) = b × power(b, e - 1)`. اطبع `2^10 = 1024`.

```asm exercise
default rel
global main
extern printf

section .data
    fmt db "2^10 = %d", 10, 0

section .text
; long power(long base, long exp)
power:
    mov eax, 1
    ; أكمل (تحتاج حفظ base في مسجل محفوظ)
    ret

main:
    sub rsp, 40
    mov ecx, 2
    mov edx, 10
    call power
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
    fmt db "2^10 = %d", 10, 0

section .text
power:
    push rbx
    sub rsp, 32
    mov eax, 1
    test rdx, rdx
    jz .done                 ; exp = 0
    mov rbx, rcx             ; base
    dec rdx
    call power               ; rax = power(base, exp - 1)
    imul rax, rbx
.done:
    add rsp, 32
    pop rbx
    ret

main:
    sub rsp, 40
    mov ecx, 2
    mov edx, 10
    call power
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
2^10 = 1024
```

## اختبر نفسك

```quiz
{"question": "ماذا تفعل push rax؟", "choices": ["rsp += 8 ثم تكتب rax", "rsp -= 8 ثم تكتب rax في [rsp]", "تنسخ rax إلى rsp", "تكتب rax في [rbp]"], "answer": 1, "explanation": "المكدس ينمو للأسفل: ينقص rsp ثم تُكتب القيمة عند القمة الجديدة."}
```

```quiz
{"question": "كم بايتًا مساحة الظل في ويندوز x64؟", "choices": ["8", "16", "32", "64"], "answer": 2, "explanation": "32 بايتًا، مكان للمعاملات الأربعة الأولى."}
```

```quiz
{"question": "أي مجموعة كلها مسجلات محفوظة (Non-volatile)؟", "choices": ["rax, rcx, rdx", "rbx, rsi, rdi, r12", "r8, r9, r10, r11", "rcx, rbx, r8"], "answer": 1, "explanation": "rbx وrbp وrsi وrdi وr12-r15 محفوظة."}
```

```quiz
{"question": "أين يوضع المعامل الخامس لحظة call؟", "choices": ["r10", "[rsp]", "[rsp + 32]", "[rbp - 8]"], "answer": 2, "explanation": "بعد مساحة الظل (32 بايتًا) مباشرة."}
```

## الخلاصة

- المكدس LIFO ينمو للأسفل؛ `push` ينقص `rsp` 8، و`pop` يزيده 8.
- `call` تدفع عنوان الرجوع، و`ret` تسحبه: وازن كل `push` بـ `pop`.
- المعاملات في `rcx` و`rdx` و`r8` و`r9` ثم `[rsp + 32]` ...، والناتج في `rax`.
- قبل كل `call`: 32 بايت ظل و`rsp` مضاعف لـ 16 (لهذا `sub rsp, 40`).
- المسجلات المحفوظة تُحفظ بـ `push` وتُستعاد بـ `pop`؛ و`push rbp / mov rbp, rsp / leave` لإطار بمتغيرات محلية.
