# الدرس 3: أتاري 2600 - أول برنامج بـ DASM وسباق الشعاع

**في هذا الدرس:**

- عتاد أتاري 2600: المعالج 6507 و**128 بايت** فقط من الذاكرة، وشريحة الرسم **TIA**، وشريحة **RIOT**.
- لماذا يسمى برنامج 2600 «**سباقًا مع الشعاع**» (Racing the Beam).
- إطار NTSC: **3 + 37 + 192 + 30 = 262** سطرًا.
- مشروع **Atari 2600 Game (DASM)** في RAD IDE، والبناء، والتشغيل في **Stella**.
- أول برنامج: ألوان متحركة على كل سطر.

## جهاز بلا ذاكرة شاشة

أغلب الأجهزة فيها «ذاكرة شاشة» يرسم فيها البرنامج ثم تعرضها الدائرة. أما **2600** فلا! شريحة **TIA** تعرف سطرًا واحدًا فقط: الخلفية، والجدار (Playfield)، وشخصيتين (Players) وقذيفتين وكرة. البرنامج يجب أن يغيّر مسجلات TIA **أثناء** رسم التلفاز لكل سطر. لهذا يقال: البرنامج يسابق شعاع الشاشة.

| الشريحة | ماذا فيها |
|---|---|
| 6507 | معالج 6502 بعنوان 13 بت (8 KB)؛ الخرطوشة عند `F000`-`FFFF` (4 KB) |
| RIOT (6532) | **128 بايت RAM** عند `80`-`FF` (والمكدس فيها أيضًا!)، ومؤقت `TIM64T` / `INTIM`، وعصا التحكم `SWCHA` |
| TIA | الرسم والصوت: `COLUBK` لون الخلفية، `WSYNC` انتظر نهاية السطر، `VSYNC` و`VBLANK` ... |

## الإطار: 262 سطرًا

التلفاز (NTSC) يرسم 60 إطارًا في الثانية، كل إطار **262** سطرًا، وكل سطر **76 دورة** من دورات المعالج:

```text
   3 أسطر   VSYNC     إشارة بداية الإطار
  37 سطرًا  VBLANK    الشعاع مطفأ: هنا منطق اللعبة (القراءة، الحركة...)
 192 سطرًا  الصورة    هنا ترسم سطرًا سطرًا
  30 سطرًا  Overscan  الشعاع مطفأ مرة أخرى: منطق إضافي
 ---
 262
```

الكتابة في `WSYNC` (أي قيمة) توقف المعالج حتى نهاية السطر الحالي. هكذا نعدّ الأسطر: كل `sta WSYNC` = سطر. إن أخطأت في العدد (261 أو 263) تهتز الصورة أو «تتدحرج» في التلفاز الحقيقي.

## أنشئ المشروع

1. **File > New Project... > Retro Games > Atari 2600 Game (DASM)** وسمّه `Rainbow`.
2. في المشروع ملفان: `main.asm` (الكود) و`atari2600.h` (أسماء مسجلات TIA و RIOT، مكتوبة لـ RAD IDE).
3. `F5` يبني `Rainbow.bin` بالمجمِّع **DASM** (ينزّله RAD IDE أول مرة من إصداراته الرسمية على GitHub) ثم يشغّله في **Stella** (نزّله من Tools > Retro > Emulators...).
4. أي خطأ يظهر في **Error List** باسم الملف ورقم السطر.

ضع الكود التالي مكان محتوى `main.asm`:

<!-- test: {"frames": 4, "ram": ["$80"], "tia": ["COLUBK"]} -->
```dasm run
        processor 6502
        include "atari2600.h"

Frame   = $80                   ; عداد الإطارات (أول بايت في الـ RAM)

        seg code
        org $F000               ; الخرطوشة 4 KB تبدأ من F000

Reset:
        sei                     ; لا مقاطعات
        cld                     ; الوضع الثنائي لا العشري
        ldx #0
        txa
Clear:
        sta $00,x               ; صفّر مسجلات TIA والـ RAM كلها
        inx
        bne Clear
        dex                     ; X = $FF
        txs                     ; المكدس في آخر الـ RAM

StartFrame:
        lda #2
        sta VBLANK              ; أطفئ الشعاع
        sta VSYNC               ; ابدأ إشارة VSYNC
        sta WSYNC               ; 3 أسطر
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC

        ldx #37                 ; 37 سطرًا من VBLANK
VBlankLoop:
        sta WSYNC
        dex
        bne VBlankLoop

        lda #0
        sta VBLANK              ; أشعل الشعاع
        ldx #192                ; 192 سطرًا من الصورة
        ldy Frame               ; أول لون يتغير مع كل إطار فتتحرك الألوان
Picture:
        sty COLUBK              ; لون الخلفية لهذا السطر
        iny
        sta WSYNC
        dex
        bne Picture

        lda #2
        sta VBLANK
        ldx #30                 ; 30 سطرًا من Overscan
Overscan:
        sta WSYNC
        dex
        bne Overscan

        inc Frame
        jmp StartFrame

        org $FFFC
        .word Reset             ; متجه التشغيل RESET
        .word Reset             ; متجه IRQ / BRK
```

مدقق الدروس في RAD IDE يشغّل هذا البرنامج في محاكي 6502 صغير ويعدّ الأسطر بين كل `VSYNC` والذي يليه، ويقرأ الذاكرة بعد 4 إطارات:

```text output
scanlines: 262
$80 = 4
COLUBK = $C2
```

- **262**: الإطار سليم.
- `$80 = 4`: البرنامج زاد عداد الإطارات 4 مرات.
- آخر لون كُتب في `COLUBK` (في الإطار الرابع، والعداد ما زال 3) هو `3 + 191 = 194` = `$C2`.

## اقرأ الكود

| السطر | المعنى |
|---|---|
| `processor 6502` | المجمِّع DASM يدعم معالجات كثيرة؛ هذا يختار 6502 |
| `org $F000` | عنوان أول بايت بعده |
| `Frame = $80` | اسم لعنوان في الـ RAM (ليس متغيرًا بالمعنى الحديث؛ مجرد عنوان) |
| `lda #2` | حمّل الرقم 2 (العلامة `#` تعني «قيمة فورية» لا عنوان) |
| `sta VSYNC` | خزّن المركم A في المسجل `VSYNC` (عنوانه `$00`) |
| `bne Clear` | اقفز إن لم تكن النتيجة صفرًا (Branch if Not Equal) |
| `.word Reset` | آخر 4 بايتات في الخرطوشة: من أين يبدأ المعالج |

مرّر الفأرة فوق أي تعليمة في المحرر: يظهر شرحها وعدد دوراتها والأعلام التي تغيرها وطرق العنونة، وفوق `COLUBK` يظهر شرح المسجل. و`F12` على أي اسم ينقلك إلى تعريفه.

## الألوان

لون الأتاري بايت واحد: النصف الأعلى **التدرج** (Hue: 16 لونًا) والنصف الأدنى **الإضاءة** (Luminance). لذلك `iny` في كل سطر يمر على كل الألوان. جرّب `$1E` (أصفر) و`$84` (أزرق) و`$C6` (أخضر) و`$46` (أحمر).

## تمرين: سطر ناقص

هذا البرنامج يرسم 191 سطرًا فقط في الصورة. أصلحه ليصبح الإطار 262 سطرًا بالضبط:

```dasm exercise
        processor 6502
        include "atari2600.h"

        seg code
        org $F000
Reset:
        ldx #$FF
        txs
StartFrame:
        lda #2
        sta VBLANK
        sta VSYNC
        sta WSYNC
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC
        ldx #37
VBlankLoop:
        sta WSYNC
        dex
        bne VBlankLoop
        stx VBLANK              ; X = 0
        ldx #191                ; <- هنا الخطأ
Picture:
        stx COLUBK
        sta WSYNC
        dex
        bne Picture
        lda #2
        sta VBLANK
        ldx #30
Overscan:
        sta WSYNC
        dex
        bne Overscan
        jmp StartFrame

        org $FFFC
        .word Reset
        .word Reset
```

<!-- test: {"frames": 3} -->
```dasm solution
        processor 6502
        include "atari2600.h"

        seg code
        org $F000
Reset:
        ldx #$FF
        txs
StartFrame:
        lda #2
        sta VBLANK
        sta VSYNC
        sta WSYNC
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC
        ldx #37
VBlankLoop:
        sta WSYNC
        dex
        bne VBlankLoop
        stx VBLANK              ; X = 0
        ldx #192                ; 192 سطرًا
Picture:
        stx COLUBK
        sta WSYNC
        dex
        bne Picture
        lda #2
        sta VBLANK
        ldx #30
Overscan:
        sta WSYNC
        dex
        bne Overscan
        jmp StartFrame

        org $FFFC
        .word Reset
        .word Reset
```

```text output
scanlines: 262
```

## اختبر فهمك

```quiz
{"question": "كم سطرًا في إطار NTSC لأتاري 2600؟", "choices": ["192", "240", "262", "312"], "answer": 2, "explanation": "3 VSYNC + 37 VBLANK + 192 صورة + 30 Overscan = 262 (و PAL = 312)."}
```

```quiz
{"question": "ماذا تفعل الكتابة في WSYNC؟", "choices": ["تمسح الشاشة", "توقف المعالج حتى نهاية السطر الحالي", "تبدّل البنك", "تقرأ عصا التحكم"], "answer": 1, "explanation": "WSYNC تزامن المعالج مع بداية السطر التالي: الطريقة الأساسية لعدّ الأسطر."}
```

```quiz
{"question": "كم بايت RAM في أتاري 2600؟", "choices": ["128", "1024", "2048", "64 KB"], "answer": 0, "explanation": "128 بايت فقط في شريحة RIOT من 80 إلى FF، ومنها المكدس."}
```
