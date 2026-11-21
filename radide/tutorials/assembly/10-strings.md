# الدرس 10: النصوص (Strings)

**في هذا الدرس ستتعلم:**

- النص في الذاكرة: مصفوفة بايتات تنتهي بصفر.
- حساب الطول، وتحويل الحروف إلى كبيرة، وعدّ الحروف، وعكس النص.
- تعليمات النصوص: `lodsb` و`stosb` و`movsb` و`scasb` مع البادئتين `rep` و`repne`.
- النصوص العربية وترميز UTF-8.

## النص = بايتات + صفر

```asm
    msg db "Hi!", 0
```

| العنوان | msg | msg+1 | msg+2 | msg+3 |
|---|---|---|---|---|
| البايت | `48` ('H') | `69` ('i') | `21` ('!') | `00` |

كل الدوال على النصوص تمشي بايتًا بايتًا حتى تجد الصفر. لنكتب `strlen` بأنفسنا:

```asm run
default rel
global main
extern printf

section .data
    text db "Hello, Assembly", 0
    fmt  db "length of '%s' = %d", 10, 0

section .text
; size_t my_strlen(const char *s) - s في rcx
my_strlen:
    xor eax, eax             ; العدّاد
.next:
    cmp byte [rcx + rax], 0  ; هل وصلنا إلى الصفر؟
    je .done
    inc rax
    jmp .next
.done:
    ret

main:
    sub rsp, 40
    lea rcx, [text]
    call my_strlen
    mov r8, rax
    lea rdx, [text]
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
length of 'Hello, Assembly' = 15
```

## الحروف الكبيرة

في جدول ASCII الفرق بين `'a'` (97) و`'A'` (65) هو 32 بالضبط، أي البت رقم 5. لتحويل حرف صغير إلى كبير: اطرح 32 (أو أطفئ ذلك البت بـ `and al, 0xDF`)، لكن **فقط** إذا كان بين `'a'` و`'z'`:

```asm run
default rel
global main
extern puts

section .data
    text db "Hello, Assembly!", 0

section .text
main:
    sub rsp, 40
    lea rcx, [text]
.next:
    mov al, [rcx]
    test al, al
    jz .done
    cmp al, 'a'
    jb .skip                 ; أصغر من 'a': ليس حرفًا صغيرًا
    cmp al, 'z'
    ja .skip                 ; أكبر من 'z'
    sub al, 32
    mov [rcx], al            ; اكتبه في مكانه
.skip:
    inc rcx
    jmp .next
.done:
    lea rcx, [text]
    call puts
    xor eax, eax
    add rsp, 40
    ret
```

```text output
HELLO, ASSEMBLY!
```

لاحظ أن النص في `.data` (قابل للكتابة). لو وضعناه في `.rdata` لانهار البرنامج عند `mov [rcx], al`.

## عدّ الحروف المتحركة

```asm run
default rel
global main
extern printf

section .data
    text   db "programming in assembly", 0
    vowels db "aeiou", 0
    fmt    db "'%s' has %d vowels", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [text]
    xor r8d, r8d             ; العدد
.next_char:
    mov al, [r10]
    test al, al
    jz .done
    lea r11, [vowels]        ; هل الحرف في "aeiou"؟
.next_vowel:
    mov dl, [r11]
    test dl, dl
    jz .not_vowel
    cmp al, dl
    je .is_vowel
    inc r11
    jmp .next_vowel
.is_vowel:
    inc r8d
.not_vowel:
    inc r10
    jmp .next_char
.done:
    lea rcx, [fmt]
    lea rdx, [text]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
'programming in assembly' has 6 vowels
```

## تعليمات النصوص

لمعالج x86 تعليمات خاصة بالنصوص تستخدم مسجلات ثابتة: `rsi` **المصدر** (Source Index) و`rdi` **الوجهة** (Destination Index) و`rcx` **العدّاد**، وتتقدم تلقائيًّا بعد كل بايت (إذا كان علم الاتجاه `DF = 0`، وتضمنه `cld`):

| التعليمة | المعنى |
|---|---|
| `lodsb` | `al = [rsi]`، ثم `rsi++` |
| `stosb` | `[rdi] = al`، ثم `rdi++` |
| `movsb` | `[rdi] = [rsi]`، ثم كلاهما `++` |
| `scasb` | قارن `al` مع `[rdi]`، ثم `rdi++` |
| `rep` + تعليمة | كررها `rcx` مرة |
| `repne scasb` | كرر حتى تجد `al` (أو ينتهي `rcx`) |

هناك أيضًا نسخ للـ word وdword وqword: `movsw` و`movsd` و`movsq` ...

نسخ نص بـ `rep movsb`، وحساب طوله بـ `repne scasb`:

```asm run
default rel
global main
extern printf

section .data
    src db "copy me, please", 0
    fmt db "copy: '%s' (%d bytes)", 10, 0

section .bss
    dst resb 64

section .text
main:
    push rsi                 ; rsi وrdi محفوظان: نحفظهما
    push rdi
    sub rsp, 40
    cld                      ; الاتجاه: للأمام

    ; الطول: ابحث عن الصفر بـ repne scasb
    lea rdi, [src]
    xor eax, eax             ; al = 0: نبحث عن البايت صفر
    mov rcx, -1              ; عدد "لا نهائي"
    repne scasb
    not rcx                  ; rcx = الطول + 1 (مع الصفر)
    mov r10, rcx

    ; النسخ: rcx بايت من rsi إلى rdi
    lea rsi, [src]
    lea rdi, [dst]
    rep movsb

    lea rcx, [fmt]
    lea rdx, [dst]
    lea r8, [r10 - 1]        ; بدون الصفر
    call printf
    xor eax, eax
    add rsp, 40
    pop rdi
    pop rsi
    ret
```

```text output
copy: 'copy me, please' (15 bytes)
```

حيلة `not rcx`: بدأنا بـ ‎-1 ونقص `rcx` مرة لكل بايت فُحص (بما فيه الصفر)؛ `not` تعطي عدد ما فُحص.

## عكس النص في مكانه

نفس فكرة عكس المصفوفة: مؤشر من البداية ومؤشر من النهاية:

```asm run
default rel
global main
extern puts

section .data
    text db "stressed", 0
    len  equ $ - text - 1

section .text
main:
    sub rsp, 40
    lea r10, [text]
    lea r11, [text + len - 1]
.swap:
    cmp r10, r11
    jae .done
    mov al, [r10]
    mov dl, [r11]
    mov [r10], dl
    mov [r11], al
    inc r10
    dec r11
    jmp .swap
.done:
    lea rcx, [text]
    call puts
    xor eax, eax
    add rsp, 40
    ret
```

```text output
desserts
```

## النصوص العربية

ملفات الكود في RAD IDE تُحفظ بترميز **UTF-8**: الحرف الإنجليزي بايت واحد، والحرف العربي **بايتان**. لذلك:

- `puts` و`printf("%s")` تطبع العربية صحيحة (تنسخ البايتات كما هي).
- الطول بالبايتات ليس عدد الحروف: `"سلام"` = 8 بايتات (الدرس 4).
- عكس نص عربي بايتًا بايتًا **يفسده**، لأنه يقلب بايتي كل حرف. وتحويل الحروف الكبيرة لا يخصها (لا توجد حروف كبيرة في العربية أصلًا)، وشرط `'a'..'z'` يحميها.

## تمارين

### التمرين 1

احسب عدد الكلمات في `"the quick brown fox"` (عدد المسافات + 1) واطبع: `4 words`.

```asm exercise
default rel
global main
extern printf

section .data
    text db "the quick brown fox", 0
    fmt  db "%d words", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [text]
    mov edx, 1
    ; عدّ المسافات

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
    text db "the quick brown fox", 0
    fmt  db "%d words", 10, 0

section .text
main:
    sub rsp, 40
    lea r10, [text]
    mov edx, 1
.next:
    mov al, [r10]
    test al, al
    jz .done
    cmp al, ' '
    jne .skip
    inc edx
.skip:
    inc r10
    jmp .next
.done:
    lea rcx, [fmt]
    call printf
    xor eax, eax
    add rsp, 40
    ret
```

```text output
4 words
```

### التمرين 2

حوّل `"RAD IDE 2026"` إلى حروف صغيرة: `rad ide 2026` (أضف 32 للحروف من `'A'` إلى `'Z'` فقط).

```asm exercise
default rel
global main
extern puts

section .data
    text db "RAD IDE 2026", 0

section .text
main:
    sub rsp, 40
    lea rcx, [text]
    ; الحلقة هنا

    lea rcx, [text]
    call puts
    xor eax, eax
    add rsp, 40
    ret
```

```asm solution
default rel
global main
extern puts

section .data
    text db "RAD IDE 2026", 0

section .text
main:
    sub rsp, 40
    lea rcx, [text]
.next:
    mov al, [rcx]
    test al, al
    jz .done
    cmp al, 'A'
    jb .skip
    cmp al, 'Z'
    ja .skip
    add al, 32
    mov [rcx], al
.skip:
    inc rcx
    jmp .next
.done:
    lea rcx, [text]
    call puts
    xor eax, eax
    add rsp, 40
    ret
```

```text output
rad ide 2026
```

## اختبر نفسك

```quiz
{"question": "ماذا تفعل lodsb؟", "choices": ["[rdi] = al", "al = [rsi] ثم rsi++", "تقارن al مع [rdi]", "تنسخ rcx بايت"], "answer": 1, "explanation": "LODS = Load String: تحمل بايتًا من [rsi] إلى al وتتقدم."}
```

```quiz
{"question": "ما المسجلات التي تستخدمها rep movsb؟", "choices": ["rax وrbx وrcx", "rsi (المصدر) وrdi (الوجهة) وrcx (العدد)", "rdx وr8 وr9", "rsp وrbp"], "answer": 1, "explanation": "تنسخ rcx بايتًا من [rsi] إلى [rdi]."}
```

```quiz
{"question": "كم بايتًا يشغل حرف عربي واحد في UTF-8؟", "choices": ["1", "2", "4", "8"], "answer": 1, "explanation": "الحروف العربية في UTF-8 بايتان لكل حرف."}
```

## الخلاصة

- النص بايتات تنتهي بصفر؛ الحلقات تمشي حتى الصفر.
- `'a'` - `'A'` = 32: حوّل الحالة بالطرح أو الجمع مع فحص المدى.
- تعليمات النصوص: `lodsb`/`stosb`/`movsb`/`scasb` بـ `rsi`/`rdi`/`rcx`، و`rep`/`repne` للتكرار، و`cld` للاتجاه.
- `rsi` و`rdi` محفوظان: احفظهما بـ `push` إذا استخدمتهما.
- العربية بـ UTF-8: بايتان للحرف، فلا تعكسها بايتًا بايتًا.
