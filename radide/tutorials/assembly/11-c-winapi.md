# الدرس 11: استدعاء دوال C وواجهة Win32

**في هذا الدرس ستتعلم:**

- قراءة مدخلات المستخدم بـ `scanf`.
- استدعاء دوال أخرى من مكتبة C: `strlen` و`qsort` (مع دالة مقارنة بلغة التجميع).
- واجهة **Win32** مباشرة: `GetStdHandle` و`WriteFile` و`MessageBoxA` و`ExitProcess`.
- متى تُفرَّغ المخرجات (`fflush`) ولماذا قد «تختفي» الطباعة.

## مكتبة C في خدمتك

برامجنا تُربط مع مكتبة C (CRT)، فكل دوالها متاحة: يكفي `extern` واتفاقية الاستدعاء التي تعلمناها. الدالة `scanf` تقرأ من لوحة المفاتيح، ومعاملاتها **عناوين** المتغيرات التي ستملؤها:

```asm run
default rel
global main
extern printf, scanf, puts

section .data
    ask    db "Enter two numbers:", 0
    fmt_in db "%d %d", 0
    fmt    db "%d + %d = %d", 10, 0

section .bss
    a resd 1
    b resd 1

section .text
main:
    sub rsp, 40
    lea rcx, [ask]
    call puts

    lea rcx, [fmt_in]        ; scanf("%d %d", &a, &b)
    lea rdx, [a]
    lea r8, [b]
    call scanf

    mov r9d, [a]
    add r9d, [b]
    lea rcx, [fmt]
    mov edx, [a]
    mov r8d, [b]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text input
12 30
```

```text output
Enter two numbers:
12 + 30 = 42
```

في الـ IDE اكتب المدخلات في شريط **Program Input** (مدخلات البرنامج) أسفل نافذة المخرجات ثم اضغط Enter.

> **لماذا `puts` للسؤال؟** `printf("...")` بلا سطر جديد قد يبقى في **ذاكرة مؤقتة** (Buffer) ولا يظهر قبل أن ينتظر `scanf`. إذا أردت السؤال على نفس السطر فاستدعِ بعده `fflush(NULL)` (`xor ecx, ecx` ثم `call fflush`).

## قراءة نص

`"%63s"` تقرأ كلمة (حتى 63 حرفًا، فالمخزن 64 بايتًا مع الصفر):

```asm run
default rel
global main
extern printf, scanf

section .data
    fmt_in db "%63s", 0
    fmt    db "Hello, %s!", 10, 0

section .bss
    name resb 64

section .text
main:
    sub rsp, 40
    lea rcx, [fmt_in]
    lea rdx, [name]          ; النص نفسه عنوان: بلا &
    call scanf
    lea rcx, [fmt]
    lea rdx, [name]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text input
Mona
```

```text output
Hello, Mona!
```

## دالة بلغة التجميع تستدعيها مكتبة C: `qsort`

`qsort(base, count, size, compare)` ترتب أي مصفوفة، وتطلب منك **عنوان دالة** تقارن عنصرين: تأخذ مؤشرين (`rcx` و`rdx`) وتعيد سالبًا أو صفرًا أو موجبًا. هذه أول مرة **نُعطي** فيها دالة من كودنا لمكتبة لتستدعيها (Callback):

```asm run
default rel
global main
extern qsort, printf, putchar

section .data
    arr   dd 42, 7, 19, 3, 25
    count equ ($ - arr) / 4
    fmt   db "%d ", 0

section .text
; int compare(const int *a, const int *b) -> *a - *b
compare:
    mov eax, [rcx]
    sub eax, [rdx]
    ret

main:
    push rbx
    push rsi
    sub rsp, 40
    lea rcx, [arr]           ; base
    mov edx, count           ; count
    mov r8d, 4               ; size
    lea r9, [compare]        ; عنوان الدالة
    call qsort

    lea rsi, [arr]
    xor ebx, ebx
.print:
    lea rcx, [fmt]
    mov edx, [rsi + rbx*4]
    call printf
    inc ebx
    cmp ebx, count
    jl .print
    mov ecx, 10
    call putchar
    xor eax, eax
    add rsp, 40
    pop rsi
    pop rbx
    ret
```

```text output
3 7 19 25 42
```

## واجهة Win32: الحديث مع ويندوز مباشرة

مكتبة C نفسها مبنية فوق **Win32 API**: دوال ويندوز في `kernel32.dll` و`user32.dll` وغيرهما. ونستدعيها بنفس الطريقة تمامًا (نفس اتفاقية x64). هذا برنامج يكتب على الشاشة **بلا** `printf`:

- `GetStdHandle(-11)` يعطي «مقبض» المخرجات القياسية (`STD_OUTPUT_HANDLE = -11`).
- `WriteFile(handle, buffer, length, &written, NULL)` يكتب البايتات. له **خمسة** معاملات: الخامس في `[rsp + 32]`.

```asm run
default rel
global main
extern GetStdHandle, WriteFile

STD_OUTPUT_HANDLE equ -11

section .data
    msg     db "Hello from WriteFile (kernel32.dll)", 13, 10
    msg_len equ $ - msg

section .bss
    written resd 1

section .text
main:
    sub rsp, 56              ; ظل 32 + معامل خامس 8 + محاذاة
    mov ecx, STD_OUTPUT_HANDLE
    call GetStdHandle        ; rax = المقبض

    mov rcx, rax             ; 1: المقبض
    lea rdx, [msg]           ; 2: البايتات
    mov r8d, msg_len         ; 3: عددها
    lea r9, [written]        ; 4: أين يكتب العدد المكتوب
    mov qword [rsp + 32], 0  ; 5: NULL
    call WriteFile

    xor eax, eax
    add rsp, 56
    ret
```

```text output
Hello from WriteFile (kernel32.dll)
```

لاحظ أن نص `WriteFile` لا يحتاج صفرًا في آخره: نعطيه الطول صراحة. و`13, 10` هما `CR LF`، نهاية السطر في ويندوز.

## نافذة رسالة: `MessageBoxA`

`MessageBoxA(hwnd, text, caption, type)` من `user32.dll` تعرض نافذة وتعيد رقم الزر الذي ضغطه المستخدم:

<!-- test: {"norun": true} -->
```asm run
default rel
global main
extern MessageBoxA, printf

MB_YESNO        equ 0x04
MB_ICONQUESTION equ 0x20

section .data
    text    db "Do you like assembly?", 0
    caption db "RAD IDE", 0
    fmt     db "MessageBoxA returned %d (6 = Yes, 7 = No)", 10, 0

section .text
main:
    sub rsp, 40
    xor ecx, ecx             ; بلا نافذة أم
    lea rdx, [text]
    lea r8, [caption]
    mov r9d, MB_YESNO | MB_ICONQUESTION
    call MessageBoxA
    lea rcx, [fmt]
    mov edx, eax
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

اضغط «جرّبه» لترى النافذة. (الـ IDE تربط `user32.dll` تلقائيًّا.) أسماء الدوال التي تنتهي بـ `A` تأخذ نصوص ANSI، والتي تنتهي بـ `W` تأخذ نصوص Unicode (UTF-16)؛ للعربية في النوافذ استخدم `MessageBoxW` مع نص `dw` بترميز UTF-16 أو مصمم النماذج في الدرس القادم.

## `ExitProcess` وذاكرة الطباعة المؤقتة

`ExitProcess(code)` تنهي البرنامج فورًا. لكن انتبه: `printf` تجمع النص في ذاكرة مؤقتة وتكتبه عند نهاية `main` الطبيعية. إذا استدعيت `ExitProcess` مباشرة بعد `printf` (والمخرجات موجّهة إلى نافذة الـ IDE أو ملف) فقد **يضيع** النص. الحل: `ret` من `main` كما نفعل دائمًا، أو `fflush(NULL)` قبل `ExitProcess`، أو `exit(code)` من مكتبة C (تفرّغ المخازن ثم تنهي).

## كيف أعرف معاملات دالة Win32؟

ابحث عن اسم الدالة في توثيق مايكروسوفت الرسمي (learn.microsoft.com). ترتيب المعاملات هناك هو نفسه: الأول `rcx` والثاني `rdx` والثالث `r8` والرابع `r9` والباقي على المكدس. وفي محرر RAD IDE: مرّر الفأرة فوق اسم الدالة أو اكتب `call MessageBoxA` لترى تلميحًا بمعاملاتها.

## تمارين

### التمرين 1

اقرأ عددًا واطبع مربعه ومكعبه: للمدخل 5 يطبع `5^2 = 25, 5^3 = 125`. (تحتاج 4 معاملات لـ `printf` بعد النص: الخامس في `[rsp + 32]`، فاحجز 56.)

```asm exercise
default rel
global main
extern printf, scanf

section .data
    fmt_in db "%d", 0
    fmt    db "%d^2 = %d, %d^3 = %d", 10, 0

section .bss
    n resd 1

section .text
main:
    sub rsp, 56
    lea rcx, [fmt_in]
    lea rdx, [n]
    call scanf
    ; احسب واطبع

    xor eax, eax
    add rsp, 56
    ret
```

```asm solution
default rel
global main
extern printf, scanf

section .data
    fmt_in db "%d", 0
    fmt    db "%d^2 = %d, %d^3 = %d", 10, 0

section .bss
    n resd 1

section .text
main:
    sub rsp, 56
    lea rcx, [fmt_in]
    lea rdx, [n]
    call scanf
    mov eax, [n]
    imul eax, eax            ; n^2
    mov r8d, eax
    imul eax, [n]            ; n^3
    mov [rsp + 32], rax      ; المعامل الخامس
    lea rcx, [fmt]
    mov edx, [n]
    mov r9d, [n]
    call printf
    xor eax, eax
    add rsp, 56
    ret
```

```text input
5
```

```text output
5^2 = 25, 5^3 = 125
```

### التمرين 2

اقرأ كلمة واطبع عدد حروفها باستخدام `strlen` من مكتبة C: للمدخل `Assembly` يطبع `Assembly: 8 letters`.

```asm exercise
default rel
global main
extern printf, scanf, strlen

section .data
    fmt_in db "%63s", 0
    fmt    db "%s: %d letters", 10, 0

section .bss
    word1 resb 64

section .text
main:
    sub rsp, 40
    lea rcx, [fmt_in]
    lea rdx, [word1]
    call scanf
    ; strlen ثم printf

    xor eax, eax
    add rsp, 40
    ret
```

```asm solution
default rel
global main
extern printf, scanf, strlen

section .data
    fmt_in db "%63s", 0
    fmt    db "%s: %d letters", 10, 0

section .bss
    word1 resb 64

section .text
main:
    sub rsp, 40
    lea rcx, [fmt_in]
    lea rdx, [word1]
    call scanf
    lea rcx, [word1]
    call strlen              ; rax = الطول
    mov r8, rax
    lea rdx, [word1]
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text input
Assembly
```

```text output
Assembly: 8 letters
```

## اختبر نفسك

```quiz
{"question": "في scanf(\"%d\", &x) ماذا نضع في rdx؟", "choices": ["قيمة x: mov edx, [x]", "عنوان x: lea rdx, [x]", "الرقم 0", "طول x"], "answer": 1, "explanation": "scanf تحتاج عنوان المتغير لتكتب فيه."}
```

```quiz
{"question": "دالة Win32 لها خمسة معاملات. أين الخامس لحظة call؟", "choices": ["r10", "[rsp + 32]", "[rsp]", "rax"], "answer": 1, "explanation": "مثل أي دالة: بعد مساحة الظل."}
```

```quiz
{"question": "لماذا قد يضيع نص printf إذا استدعينا ExitProcess بعدها مباشرة؟", "choices": ["لأن printf لا تعمل مع Win32", "لأن النص ما زال في ذاكرة الطباعة المؤقتة ولم يُكتب بعد", "لأن ExitProcess تمسح الشاشة", "لا يضيع أبدًا"], "answer": 1, "explanation": "استخدم ret من main أو fflush(NULL) أو exit()."}
```

```quiz
{"question": "ما الفرق بين MessageBoxA وMessageBoxW؟", "choices": ["A للنوافذ الكبيرة", "A تأخذ نصوص ANSI وW تأخذ نصوص Unicode (UTF-16)", "W أسرع", "لا فرق"], "answer": 1, "explanation": "أغلب دوال Win32 النصية لها نسختان: A وW."}
```

## الخلاصة

- كل دوال مكتبة C متاحة بـ `extern`: `scanf` تأخذ **عناوين**، و`"%63s"` لقراءة كلمة بأمان.
- يمكن إعطاء المكتبة **عنوان دالة** منك (`lea r9, [compare]`) لتستدعيها: Callback.
- Win32 بنفس الاتفاقية: `GetStdHandle` و`WriteFile` و`MessageBoxA`، والمعامل الخامس في `[rsp + 32]`.
- انتهِ بـ `ret` من `main` (أو `fflush`/`exit`) حتى لا تضيع المخرجات المؤقتة.
