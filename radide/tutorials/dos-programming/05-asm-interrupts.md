# الدرس 5: التجميع 16 بت والمقاطعات

**في هذا الدرس ستتعلم:**

- مشروع **DOS Assembly (16-bit MASM)** يبنيه المجمّع الحر **JWasm** إلى `.EXE` أو `.COM`.
- مسجلات المعالج 8086 والمقاطع (`CS` و`DS` و`ES` و`SS`).
- خدمات DOS عبر `INT 21h`: طباعة نص وحرف وقراءة مفتاح والخروج.
- خدمات البيوس: الشاشة `INT 10h` ولوحة المفاتيح `INT 16h`.
- حلقة وطباعة عدد، وبرنامج `.COM` صغير.
- خطوة بخطوة في محاكي 8086 الخاص بـ RAD IDE.

> هذا الدرس مختصر لبرامج DOS. إن كانت لغة التجميع جديدة عليك تمامًا فابدأ بدورة **تعلّم لغة التجميع (Assembly) من الصفر** في نفس نافذة الدروس، وخاصة درس «معالج 8086 في المحاكي التعليمي».

## المسجلات والمقاطع

المعالج 8086 فيه مسجلات بطول 16 بت:

| المسجل | الاستعمال المعتاد |
|---|---|
| `AX` (وجزآه `AH` و`AL`) | الحساب، ورقم الخدمة عند المقاطعات (`AH`) |
| `BX` و`CX` و`DX` | عناوين وعدّاد الحلقات (`CX`) وبيانات |
| `SI` و`DI` | مؤشرات للنصوص والمصفوفات |
| `SP` و`BP` | المكدس |
| `CS` و`DS` و`ES` و`SS` | مقاطع: الكود والبيانات والإضافي والمكدس |

العنوان الكامل = مقطع × 16 + إزاحة، لذلك يبدأ كل برنامج `.EXE` بوضع مقطع بياناته في `DS`.

## أول برنامج

أنشئ مشروعًا من **File > New Project...** ثم **DOS** ثم **DOS Assembly (16-bit MASM)**. الملف `MAIN.ASM`:

<!-- test: {"keys": "k", "screen": true} -->

```dos-asm run
        .model small
        .stack 200h

        .data
msg     db 'Hello from 16-bit assembly!', 13, 10, '$'
ask     db 'Press a key: $'
got     db 13, 10, 'You pressed: $'

        .code
main    proc
        mov ax, @data           ; DS = our data segment
        mov ds, ax

        mov ah, 09h             ; DOS: print the $-terminated string at DS:DX
        mov dx, offset msg
        int 21h

        mov ah, 09h
        mov dx, offset ask
        int 21h
        mov ah, 01h             ; DOS: read a key with echo -> AL
        int 21h
        mov bl, al

        mov ah, 09h
        mov dx, offset got
        int 21h
        mov ah, 02h             ; DOS: print the character in DL
        mov dl, bl
        int 21h

        mov ax, 4C00h           ; DOS: exit with code 0
        int 21h
main    endp
        end main
```

```text output
Hello from 16-bit assembly!
Press a key: k
You pressed: k
```

| الخدمة | المدخلات | العمل |
|---|---|---|
| `AH = 09h` | `DS:DX` عنوان نص ينتهي بـ `$` | طباعة نص |
| `AH = 02h` | `DL` الحرف | طباعة حرف |
| `AH = 01h` | | قراءة مفتاح مع إظهاره، والناتج في `AL` |
| `AH = 4Ch` | `AL` رمز الخروج | إنهاء البرنامج |

- `.model small` نموذج الذاكرة، و`.stack 200h` حجم المكدس.
- `db` يعرّف بايتات. `13, 10` هما CR و LF (سطر جديد)، و`'$'` نهاية النص لخدمة 09h.
- `offset msg` إزاحة النص داخل مقطع البيانات.

اضغط `Ctrl+F5` للتشغيل في DOSBox-X. ومع **F5** تفتح RAD IDE البرنامج في **محاكي 8086** الخاص بها (عندما تفهم الكود): خطوة بخطوة، مع نوافذ المسجلات والذاكرة والشاشة. وبعد البناء تجد في `_build` ملف القائمة (listing) وخريطة الرموز، ويفتحها **Tools > Retro > DOS Programming > Open Symbol Map**.

## حلقة وطباعة عدد

لا توجد في DOS خدمة تطبع عددًا، فنحوّله إلى أرقام بأنفسنا: نقسم على 10 ونخزن البواقي في المكدس، ثم نطبعها بالعكس:

```dos-asm run
        .model small
        .stack 200h

        .data
title_  db 'Squares from 1 to 6:', 13, 10, '$'

        .code
; print AX as a decimal number
print_num proc
        push ax
        push bx
        push cx
        push dx
        mov bx, 10
        xor cx, cx
pn_div: xor dx, dx
        div bx                  ; AX = AX / 10, DX = remainder
        push dx
        inc cx
        or ax, ax
        jnz pn_div
pn_out: pop dx
        add dl, '0'
        mov ah, 02h
        int 21h
        loop pn_out
        pop dx
        pop cx
        pop bx
        pop ax
        ret
print_num endp

main    proc
        mov ax, @data
        mov ds, ax
        mov ah, 09h
        mov dx, offset title_
        int 21h
        mov si, 1
next:   mov ax, si
        mul si                  ; DX:AX = AX * SI
        call print_num
        mov ah, 02h
        mov dl, ' '
        int 21h
        inc si
        cmp si, 6
        jbe next
        mov ax, 4C00h
        int 21h
main    endp
        end main
```

```text output
Squares from 1 to 6:
1 4 9 16 25 36
```

- `div bx` يقسم `DX:AX` على `BX`: الناتج في `AX` والباقي في `DX`.
- `loop` ينقص `CX` ويقفز ما دام لم يصبح صفرًا.
- `cmp` ثم `jbe` (اقفز إن كان أصغر أو يساوي، بلا إشارة).
- `proc` / `endp` إجراء، و`call` / `ret` لاستدعائه. نحفظ المسجلات بـ `push` ونعيدها بـ `pop` بالترتيب العكسي.

## البيوس: الشاشة ولوحة المفاتيح

خدمات DOS بسيطة لكنها لا تعرف الألوان. البيوس يعطيك تحكمًا أكبر:

<!-- test: {"keys": "x"} -->

```dos-asm run
        .model small
        .stack 200h

        .data
text    db 'Colours from the video BIOS', 0

        .code
main    proc
        mov ax, @data
        mov ds, ax
        mov ax, 0003h           ; INT 10h AH=00h: set video mode 3 (80x25 colour text, clears the screen)
        int 10h
        mov si, offset text
        mov dh, 5               ; row
        mov dl, 20              ; column
        mov bl, 1Eh             ; yellow on blue
nextc:  mov ah, 02h             ; INT 10h AH=02h: move the cursor to DH, DL
        mov bh, 0
        int 10h
        lodsb                   ; AL = [SI], SI = SI + 1
        or al, al
        jz waitk
        mov ah, 09h             ; INT 10h AH=09h: write AL with attribute BL
        mov cx, 1
        int 10h
        inc dl
        inc bl                  ; next colour
        and bl, 7Fh
        jmp nextc
waitk:  mov ah, 00h             ; INT 16h AH=00h: wait for a key -> AH scan code, AL ASCII
        int 16h
        mov ax, 4C00h
        int 21h
main    endp
        end main
```

```text output
                    Colours from the video BIOS
```

| المقاطعة والخدمة | العمل |
|---|---|
| `INT 10h`, `AH = 00h` | اختيار وضع الشاشة (`AL = 03h` نص، `AL = 13h` رسوم 320 × 200 بـ 256 لونًا) |
| `INT 10h`, `AH = 02h` | تحريك المؤشر إلى السطر `DH` والعمود `DL` |
| `INT 10h`, `AH = 09h` | كتابة الحرف `AL` بالسمة `BL`، `CX` مرة |
| `INT 16h`, `AH = 00h` | انتظار مفتاح: رمز المسح في `AH` وحرف ASCII في `AL` |
| `INT 16h`, `AH = 01h` | هل يوجد مفتاح؟ (العلم ZF = 1 إن لم يوجد) دون انتظار |
| `INT 33h`, `AX = 0000h` | هل يوجد مشغّل فأرة؟ ثم `AX = 0003h` لموضعها وأزرارها |

مرّر الفأرة فوق `int 10h` أو `int 21h` في المحرر: تقرأ RAD IDE قيمة `AH` من السطور التي فوقها وتعرض اسم الخدمة ومسجلاتها.

## برنامج .COM

ملف `.COM` أبسط: مقطع واحد للكود والبيانات يبدأ عند `100h`، فلا داعي لتحميل `DS`. اختر في **Project > DOS Project Settings...** المخرَج **.COM** (أو القالب **Tiny .COM Program**):

<!-- test: {"com": true} -->

```dos-asm run
        .model tiny
        .code
        org 100h
start:  mov ah, 09h
        mov dx, offset msg
        int 21h
        mov ax, 4C00h
        int 21h
msg     db 'A tiny .COM program', 13, 10, '$'
        end start
```

```text output
A tiny .COM program
```

حجم هذا البرنامج بضعة وثلاثون بايتًا فقط!

> **تمرين:** عدّل برنامج المربعات ليطبع جدول ضرب العدد 7 من 1 إلى 10، كل ناتج في سطر (`13, 10` بعد كل عدد).

```quiz
{"question": "ما الخدمة التي تطبع نصًّا ينتهي بالعلامة $ في INT 21h؟", "choices": ["AH = 02h", "AH = 09h", "AH = 4Ch"], "answer": 1, "explanation": "AH = 09h تطبع النص الذي عنوانه في DS:DX حتى العلامة $."}
```

```quiz
{"question": "لماذا يبدأ برنامج .EXE بالسطرين mov ax, @data ثم mov ds, ax؟", "choices": ["لتسريع البرنامج", "لأن DS لا يشير إلى مقطع بياناتنا عند البدء", "لمسح الشاشة"], "answer": 1, "explanation": "عند تشغيل .EXE يشير DS إلى مقدمة البرنامج (PSP)، فنضع فيه مقطع البيانات لنصل إلى متغيراتنا."}
```
