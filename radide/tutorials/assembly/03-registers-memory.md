# الدرس 3: المعالج والمسجلات والذاكرة

**في هذا الدرس ستتعلم:**

- كيف ينفّذ المعالج التعليمات: **الجلب، الفك، التنفيذ**.
- **المسجلات** (Registers) في معالج x86-64 وأجزاؤها (`rax` و`eax` و`ax` و`al`).
- التعليمة `mov` وقواعدها.
- **الذاكرة** والعناوين والفرق بين `[msg]` و`msg`.
- ترتيب البايتات **Little Endian**.

## داخل المعالج

تخيّل المعالج **مطبخًا** صغيرًا جدًّا وسريعًا جدًّا:

- **الذاكرة** (RAM) هي **المخزن** الكبير: فيه كل شيء، لكن الذهاب إليه يأخذ وقتًا.
- **المسجلات** هي **سطح العمل** أمام الطاهي: أماكن قليلة جدًّا (16 مسجلًا عامًّا) لكنها داخل المعالج نفسه، والعمل عليها فوري.
- **وحدة الحساب والمنطق** (ALU) هي **الطاهي**: تجمع وتطرح وتقارن.
- **وحدة التحكم** تقرأ **الوصفة** (البرنامج) تعليمة تعليمة.

وفي كل دورة يكرر المعالج ثلاث خطوات بلا توقف:

1. **الجلب** (Fetch): يقرأ التعليمة التالية من الذاكرة، من العنوان الموجود في المسجل الخاص `rip`.
2. **الفك** (Decode): يفهم ما تطلبه التعليمة.
3. **التنفيذ** (Execute): ينفّذها، ثم يزيد `rip` ليشير إلى التعليمة التالية.

المسجل `rip` (Instruction Pointer) إذن هو «إصبع» المعالج على سطر الوصفة الحالي. تعليمات مثل `call` و`jmp` (الدرس 6) تعمل بتغيير `rip`.

## المسجلات العامة في x86-64

| المسجل (64) | 32 بت | 16 بت | 8 بت | الاستخدام المعتاد |
|---|---|---|---|---|
| `rax` | `eax` | `ax` | `al` | الحسابات وقيمة رجوع الدوال |
| `rbx` | `ebx` | `bx` | `bl` | عام (يجب حفظه) |
| `rcx` | `ecx` | `cx` | `cl` | المعامل الأول، العدّاد |
| `rdx` | `edx` | `dx` | `dl` | المعامل الثاني، القسمة |
| `rsi` | `esi` | `si` | `sil` | المصدر في عمليات النصوص |
| `rdi` | `edi` | `di` | `dil` | الوجهة في عمليات النصوص |
| `rbp` | `ebp` | `bp` | `bpl` | قاعدة إطار المكدس |
| `rsp` | `esp` | `sp` | `spl` | قمة المكدس (لا تعبث به) |
| `r8` .. `r15` | `r8d` .. | `r8w` .. | `r8b` .. | عامة؛ `r8` و`r9` المعاملان 3 و4 |

كل اسم أصغر هو **جزء** من نفس المسجل وليس مسجلًا جديدًا: `eax` هو النصف الأدنى من `rax`، و`ax` النصف الأدنى من `eax`، و`al` البايت الأدنى. (وهناك أيضًا `ah`: البايت الثاني من `ax`.)

```text
rax: [ ........ 32 بت عليا ........ ][ .......... eax .......... ]
                                     [ ... ][ ...... ax ...... ]
                                            [  ah  ][   al   ]
```

بالإضافة إلى المسجلات العامة هناك `rip` (عنوان التعليمة التالية) و`rflags` (الأعلام، الدرس 6).

## التعليمة mov

`mov الوجهة, المصدر` تنسخ المصدر إلى الوجهة (المصدر لا يتغير). القواعد:

- الوجهة مسجل أو ذاكرة؛ المصدر مسجل أو ذاكرة أو رقم ثابت.
- **لا** يمكن النسخ من ذاكرة إلى ذاكرة مباشرة (`mov [a], [b]` خطأ): مرّ بمسجل.
- الحجمان يجب أن يتساويا: `mov eax, bl` خطأ.

### قاعدة مهمة: الكتابة في جزء من المسجل

- الكتابة في **8 أو 16 بت** (`al` و`ax`) تترك باقي المسجل كما هو.
- الكتابة في **32 بت** (`eax`) **تصفّر** الـ 32 بت العليا تلقائيًّا.

لنرَ ذلك بأعيننا. `%llX` تطبع المسجل كاملًا (64 بت) بالسادس عشر:

```asm run
default rel
global main
extern printf

section .data
    fmt db "%016llX", 10, 0

section .text
main:
    sub rsp, 40

    mov rdx, 0x1122334455667788
    lea rcx, [fmt]
    call printf                  ; القيمة كاملة

    mov rdx, 0x1122334455667788
    mov dl, 0xFF                 ; البايت الأدنى فقط
    lea rcx, [fmt]
    call printf

    mov rdx, 0x1122334455667788
    mov dx, 0xAAAA               ; 16 بت الدنيا فقط
    lea rcx, [fmt]
    call printf

    mov rdx, 0x1122334455667788
    mov edx, 0x12345678          ; 32 بت: العليا تُصفَّر!
    lea rcx, [fmt]
    call printf

    xor eax, eax
    add rsp, 40
    ret
```

```text output
1122334455667788
11223344556677FF
112233445566AAAA
0000000012345678
```

(`%016llX` تعني: 64 بت، سادس عشري، 16 خانة مع أصفار على اليسار.)

لاحظ أننا نعيد ملء `rdx` و`rcx` قبل كل `call`: الدالة المستدعاة حرة في تغيير `rax` و`rcx` و`rdx` و`r8` إلى `r11` (تسمى المسجلات **المتطايرة** Volatile).

## الذاكرة والعناوين

الذاكرة صف طويل جدًّا من البايتات، لكل بايت **رقم** هو **عنوانه**. عندما تكتب في قسم البيانات:

```asm
section .data
    age dd 25
```

يحجز المجمّع 4 بايتات (dd = dword) في مكان ما، ويصبح الاسم `age` **عنوان** أول بايت منها. الآن:

| الكتابة | المعنى |
|---|---|
| `lea rax, [age]` | ضع **العنوان** نفسه في `rax` (أين يسكن المتغير) |
| `mov eax, [age]` | ضع **المحتوى** الموجود عند العنوان في `eax` (قيمة المتغير: 25) |
| `mov dword [age], 30` | اكتب 30 في الذاكرة عند ذلك العنوان |

الأقواس `[ ]` تعني «ما في الذاكرة عند هذا العنوان». وعندما لا يستطيع المجمّع معرفة الحجم (مثل `mov [age], 30`: هل هو بايت أم 4؟) نكتب الحجم صراحة: `byte` أو `word` أو `dword` أو `qword`.

```asm run
default rel
global main
extern printf

section .data
    age dd 25
    fmt db "age = %d", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    mov edx, [age]           ; اقرأ المتغير
    call printf

    mov dword [age], 30      ; غيّر قيمته في الذاكرة
    lea rcx, [fmt]
    mov edx, [age]
    call printf

    xor eax, eax
    add rsp, 40
    ret
```

```text output
age = 25
age = 30
```

## ترتيب البايتات: Little Endian

عندما يخزّن معالج x86 عددًا من عدة بايتات، يضع **البايت الأصغر أولًا** (في العنوان الأصغر). العدد `0x11223344` يُخزَّن هكذا:

| العنوان | num | num+1 | num+2 | num+3 |
|---|---|---|---|---|
| البايت | `44` | `33` | `22` | `11` |

التعليمة `movzx` (Move with Zero-Extend) تقرأ بايتًا واحدًا وتضعه في مسجل أكبر مع تصفير الباقي:

```asm run
default rel
global main
extern printf

section .data
    num dd 0x11223344
    fmt db "num[0]=%X num[1]=%X num[3]=%X", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    movzx edx, byte [num]        ; أول بايت
    movzx r8d, byte [num + 1]    ; البايت الثاني
    movzx r9d, byte [num + 3]    ; البايت الأخير
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
num[0]=44 num[1]=33 num[3]=11
```

> **تشبيه:** Little Endian مثل كتابة التاريخ «يوم/شهر/سنة»: الجزء الأصغر أولًا. عندما تنظر إلى نافذة **Memory** (الذاكرة) في المنقّح سترى الأعداد «مقلوبة» بهذا الشكل؛ هذا طبيعي.

## التبديل بـ xchg

`xchg a, b` تبدّل قيمتي مسجلين (أو مسجل وذاكرة) في خطوة واحدة:

```asm run
default rel
global main
extern printf

section .data
    fmt db "a=%d b=%d", 10, 0

section .text
main:
    sub rsp, 40
    mov edx, 5
    mov r8d, 9
    xchg edx, r8d
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
a=9 b=5
```

## أخطاء شائعة

نسخ من ذاكرة إلى ذاكرة:

```asm
    mov [a], [b]
```

```text
main.asm:12: error: invalid combination of opcode and operands
```

حجمان مختلفان:

```asm
    mov eax, bl
```

```text
main.asm:12: error: invalid combination of opcode and operands
```

حجم غير مكتوب: هذا أخطر الثلاثة لأنه قد يمر بلا رسالة:

```asm
    mov [age], 30
```

الإصدارات القديمة من NASM ترفضه برسالة `error: operation size not specified`، أما NASM 3 (الذي تنزّله الـ IDE) فيقبله بصمت ويكتب **بايتًا واحدًا** فقط! إذا كانت قيمة `age` هي 300 (`0x12C`) فستصبح بعده `0x11E` = 286 بدل 30. القاعدة: عند الكتابة في الذاكرة برقم ثابت اكتب الحجم دائمًا (`mov dword [age], 30`).

## تمارين

### التمرين 1

بدّل قيمتي المتغيرين `a` و`b` **في الذاكرة** (استخدم مسجلين مساعدين)، ثم اطبعهما: `a=9 b=5`.

```asm exercise
default rel
global main
extern printf

section .data
    a   dd 5
    b   dd 9
    fmt db "a=%d b=%d", 10, 0

section .text
main:
    sub rsp, 40
    ; بدّل a و b هنا

    lea rcx, [fmt]
    mov edx, [a]
    mov r8d, [b]
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
    a   dd 5
    b   dd 9
    fmt db "a=%d b=%d", 10, 0

section .text
main:
    sub rsp, 40
    mov eax, [a]
    mov r10d, [b]
    mov [a], r10d
    mov [b], eax

    lea rcx, [fmt]
    mov edx, [a]
    mov r8d, [b]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
a=9 b=5
```

### التمرين 2

المتغير `val` قيمته `0x0102030405060708` (qword). اطبع أول بايت فيه في الذاكرة وآخر بايت: `first=08 last=01`.

```asm exercise
default rel
global main
extern printf

section .data
    val dq 0x0102030405060708
    fmt db "first=%02X last=%02X", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    ; edx = أول بايت، r8d = آخر بايت (val + 7)
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
    val dq 0x0102030405060708
    fmt db "first=%02X last=%02X", 10, 0

section .text
main:
    sub rsp, 40
    lea rcx, [fmt]
    movzx edx, byte [val]
    movzx r8d, byte [val + 7]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
first=08 last=01
```

## اختبر نفسك

```quiz
{"question": "ما الجزء الأدنى 32 بت من المسجل rbx؟", "choices": ["bx", "ebx", "bl", "rbx32"], "answer": 1, "explanation": "rbx (64) ثم ebx (32) ثم bx (16) ثم bl (8)."}
```

```quiz
{"question": "إذا كان rax = 0xFFFFFFFFFFFFFFFF ونفّذنا mov eax, 1 فما قيمة rax؟", "choices": ["0xFFFFFFFF00000001", "0x0000000000000001", "0xFFFFFFFFFFFFFF01", "لا تتغير"], "answer": 1, "explanation": "الكتابة في مسجل 32 بت تصفّر الـ 32 بت العليا."}
```

```quiz
{"question": "ما الفرق بين lea rax, [x] و mov rax, [x]؟", "choices": ["لا فرق", "lea تضع عنوان x، وmov تضع ما في الذاكرة عند x", "lea أسرع فقط", "mov تضع العنوان"], "answer": 1, "explanation": "lea = Load Effective Address: تحسب العنوان ولا تقرأ الذاكرة."}
```

```quiz
{"question": "كيف يُخزَّن العدد 0x1234 (word) في الذاكرة على معالج x86؟", "choices": ["12 34", "34 12", "43 21", "21 43"], "answer": 1, "explanation": "Little Endian: البايت الأصغر 34 أولًا ثم 12."}
```

## الخلاصة

- المعالج يجلب التعليمة من العنوان في `rip`، يفكها، ينفذها، ويتقدم.
- 16 مسجلًا عامًّا 64 بت، ولكل منها أجزاء: `rax`/`eax`/`ax`/`al`.
- الكتابة في 32 بت تصفّر النصف الأعلى؛ في 8 و16 بت لا.
- `[x]` = محتوى الذاكرة عند العنوان x؛ `lea` تحسب العنوان فقط؛ حدد الحجم بـ `dword` وأخواتها عند الحاجة.
- x86 يخزن الأعداد Little Endian: البايت الأصغر أولًا.
