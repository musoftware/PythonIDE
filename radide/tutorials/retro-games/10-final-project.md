# الدرس 10: المشروع النهائي - لعبة أتاري وتعديلها

**ستبني في هذا الدرس دورة حياة لعبة قديمة كاملة:**

1. تكتب لعبة **«الوصول إلى الجدار»** لأتاري 2600: وجه يتحرك بعصا التحكم داخل غرفة، وكلما لمس الجدار الأيمن زادت النقاط (بالعشري BCD) وتغير لون الغرفة.
2. تشغّلها في Stella وتصححها.
3. **تفككها** بـ RAD IDE إلى مشروع وتتأكد أنه يُعاد بناؤه مطابقًا.
4. تعاملها كأنها «لعبة قديمة» في **مشروع ROM Hacking**: تغيّر لونًا ورسمًا بمحرر السادس عشر و Tile Editor، وتنشر التعديل **رقعة BPS**.

## 1. اللعبة

**New Project > Retro Games > Atari 2600 Game (DASM)** باسم `ReachTheWall`، وضع في `main.asm`:

<!-- test: {"frames": 150, "hold": "right", "ram": ["$80"], "ramhex": ["$82"], "tia": ["COLUBK"]} -->
```dasm run
        processor 6502
        include "atari2600.h"

; ---------------------------------------------------------------- RAM
PlayerX = $80                   ; 16 - 140
PlayerY = $81
Score   = $82                   ; نقاط بالعشري (BCD): $00 - $99

; ---------------------------------------------------------------- ثوابت
LEFT_WALL  = 16
RIGHT_WALL = 140

        seg code
        org $F000
Reset:
        sei
        cld
        ldx #0
        txa
Clear:  sta $00,x
        inx
        bne Clear
        dex
        txs
        lda #76
        sta PlayerX
        lda #90
        sta PlayerY
        lda #1
        sta CTRLPF              ; جدار مرآة
        lda #$C6
        sta COLUPF
        lda #$1E
        sta COLUP0

; ---------------------------------------------------------------- الإطار
StartFrame:
        lda #2
        sta VBLANK
        sta VSYNC
        sta WSYNC
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC
        lda #43
        sta TIM64T

        jsr ReadJoystick
        jsr CheckWall
        lda Score               ; لون الغرفة يتغير مع النقاط
        asl
        asl
        asl
        asl
        ora #$04
        sta COLUBK

        lda PlayerX
        ldx #0
        jsr SetHorizPos
        sta WSYNC
        sta HMOVE

WaitVBlank:
        lda INTIM
        bne WaitVBlank
        sta WSYNC
        sta VBLANK

        ldy #192
Kernel:
        tya
        sec
        sbc PlayerY
        cmp #8
        bcc Draw
        lda #0
        beq Store
Draw:   tax
        lda Smiley,x
Store:  sta WSYNC
        sta GRP0
        cpy #185
        bcs Full
        cpy #9
        bcc Full
        lda #%00010000
        sta PF0
        lda #0
        sta PF1
        sta PF2
        jmp Next
Full:   lda #$FF
        sta PF0
        sta PF1
        sta PF2
Next:   dey
        bne Kernel

        lda #2
        sta VBLANK
        lda #0
        sta GRP0
        lda #35
        sta TIM64T
Overscan:
        lda INTIM
        bne Overscan
        jmp StartFrame

; ---------------------------------------------------------------- إجراءات
        SUBROUTINE              ; نطاق جديد للتسميات المحلية (.xxx)
ReadJoystick:
        lda SWCHA
        and #%10000000          ; يمين
        bne .noRight
        inc PlayerX
.noRight:
        lda SWCHA
        and #%01000000          ; يسار
        bne .noLeft
        lda PlayerX
        cmp #LEFT_WALL + 1
        bcc .noLeft
        dec PlayerX
.noLeft:
        rts

        SUBROUTINE              ; نطاق جديد للتسميات المحلية (.xxx)
CheckWall:
        lda PlayerX
        cmp #RIGHT_WALL
        bcc .done               ; لم يصل بعد
        sed                     ; نقطة جديدة بالعشري
        clc
        lda Score
        adc #1
        sta Score
        cld
        lda #LEFT_WALL          ; ارجع إلى اليسار
        sta PlayerX
.done:
        rts

        SUBROUTINE              ; نطاق جديد للتسميات المحلية (.xxx)
SetHorizPos:
        sta WSYNC
        sec
.div15: sbc #15
        bcs .div15
        eor #7
        asl
        asl
        asl
        asl
        sta HMP0,x
        sta RESP0,x
        rts

Smiley:
        .byte %00111100
        .byte %01000010
        .byte %10011001
        .byte %10100101
        .byte %10000001
        .byte %10100101
        .byte %01000010
        .byte %00111100

        org $FFFC
        .word Reset
        .word Reset
```

المدقق يمسك العصا يمينًا 150 إطارًا (ثانيتان ونصف):

```text output
scanlines: 262
$80 = 102
$82 = $01
COLUBK = $14
```

- وصل الوجه إلى 140 في الإطار 64: نقطة واحدة، ورجع إلى 16 في الإطار نفسه، ثم تحرك في الإطارات 86 الباقية: `16 + 86 = 102`.
- `COLUBK = $14`: النقاط `$01` منقولة إلى نصف البايت الأعلى (التدرج) مع إضاءة 4.
- في DASM التسمية التي تبدأ بنقطة مثل `.done` **محلية**: نطاقها من `SUBROUTINE` إلى `SUBROUTINE` التالية، فتستطيع تكرار الاسم نفسه في كل إجراء.

## 2. شغّل وصحح

- `F5`: تعمل في Stella. حرك العصا يمينًا وراقب تغير لون الغرفة.
- افتح مصحح Stella (`` ` ``): الرموز `PlayerX` و`Score` تظهر بأسمائها لأن RAD IDE نسخ `main.sym` بجانب الـ ROM.
- **تحدٍّ:** اجعل الجدار الأيسر يعطي نقطة أيضًا، ثم أضف صوتًا قصيرًا عند كل نقطة (`AUDC0` و`AUDF0` و`AUDV0`).

## 3. فككها

**Tools > Retro > Retro Development > Disassemble ROM into Project...** واختر `ReachTheWall.bin`: يجب أن يظهر **byte-identical**. افتح `main.asm` الناتج وقارنه بكودك: ستجد `sed` و`adc #$01` و`.byte` الوجه، وأسماء مثل `ram_82` بدل `Score`. غيّر `ram_82` إلى `Score` في الملف (بحث واستبدال)، وسمِّ عناوين الكود في `hints.json` (`"labels"`)، ثم **Rebuild Check**: ما زال مطابقًا لأن الأسماء لا تغيّر البايتات.

## 4. عدّلها كأنها لعبة قديمة

1. **New Project > Retro > ROM Hacking Project**، ثم **Set Source ROM...** واختر `ReachTheWall.bin` (لعبتك أنت؛ هكذا تتدرب بأمان).
2. **Edit Working Copy**، ثم `Ctrl+F` وابحث بالسادس عشر عن `A9 C6 85 08` (أي `lda #$C6` ثم `sta COLUPF`) وغيّر `C6` إلى `46`: جدار أحمر.
3. افتح نسخة العمل في **Tile Editor**، والصيغة **Atari 2600 player**، وابحث عن الوجه (8 بايتات) وارسم وجهًا حزينًا، و`Ctrl+S`.
4. **Capture Edits as Patch** بصيغة **BPS** واسمها `red_wall_sad_face`.
5. `F5`: يبني `build/..._patched.bin` ويشغّلها: جدار أحمر ووجه حزين.
6. انشر `patches/001_red_wall_sad_face.bps` وحده. من يملك `ReachTheWall.bin` الأصلي يطبّقه بـ **Tools > Retro > ROM Workbench > Apply Patch...** أو بأي أداة BPS، ويرفض BPS أي ملف أصلي آخر بفضل CRC32.

## ماذا تعلمت في الدورة؟

| الدرس | المهارة |
|---|---|
| 1 | ما هو ROM، والصيغ، والحدود القانونية |
| 2 | محرر السادس عشر، ومشروع ROM Hacking، وصيغتا IPS و BPS |
| 3-4 | برمجة أتاري 2600: الإطار، والألوان، والجدار، والشخصيات، وعصا التحكم |
| 5 | NES (ca65) و Game Boy (RGBDS) |
| 6 | التفكيك وإعادة البناء المطابق |
| 7 | البلاطات ومحرر الرسوم |
| 8 | جداول الحروف والترجمة العربية |
| 9 | المحاكيات والتصحيح |

```quiz
{"question": "بعد أن عدّلت لعبتك في مشروع ROM Hacking، ما الذي تنشره؟", "choices": ["الـ ROM المرقّعة كاملة", "ملف الرقعة BPS وحده", "مجلد المشروع كله مع rom/", "لقطة شاشة فقط"], "answer": 1, "explanation": "الرقعة تحتوي تعديلاتك فقط؛ وهي ما ينشره مجتمع تعديل الألعاب دائمًا."}
```

```quiz
{"question": "لماذا نكتب sed قبل جمع النقاط ثم cld بعده؟", "choices": ["sed يجعل adc تجمع بالعشري (BCD) لعرض الأرقام، و cld يعيد الجمع الثنائي لبقية البرنامج", "لتسريع البرنامج", "لإطفاء المقاطعات", "لا داعي لهما في 6502"], "answer": 0, "explanation": "النقاط تُخزَّن BCD لتُعرض أرقامًا عشرية؛ بقية الحسابات (المواضع) ثنائية."}
```
