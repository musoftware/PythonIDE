# الدرس 4: الشخصيات والخلفية وعصا التحكم

**في هذا الدرس:**

- **الجدار** (Playfield): المسجلات `PF0` و`PF1` و`PF2` وترتيب بتاتها الغريب، والانعكاس `CTRLPF`.
- **الشخصية** (Player): `GRP0` بايت واحد = 8 نقاط في السطر، واللون `COLUP0`.
- وضع الشخصية أفقيًا: `RESP0` و`HMP0` و`HMOVE`.
- عصا التحكم: `SWCHA` وزر الإطلاق `INPT4`.
- **محرر الجدار** في RAD IDE.

## الجدار: 40 مربعًا في السطر

نصف الشاشة الأيسر 20 «مربعًا» تأتي من 20 بتًا: 4 من `PF0` و8 من `PF1` و8 من `PF2`. والنصف الأيمن إما تكرار للأيسر أو **انعكاس** له (البت 0 في `CTRLPF`).

```text
 PF0: البتات 4 5 6 7   (من اليسار إلى اليمين)
 PF1: البتات 7 6 5 4 3 2 1 0
 PF2: البتات 0 1 2 3 4 5 6 7
```

نعم، ترتيب `PF1` عكس `PF0` و`PF2`! لهذا يوجد في RAD IDE **محرر الجدار**: **Tools > Retro > Graphics & Text > Atari 2600 Playfield Editor**. ترسم بالفأرة على شبكة 40 × N، ويظهر في شريط الحالة أي مسجل وأي بت يرسم المربع، ثم **Export** يكتب جداول `.byte %...` لـ DASM أو ca65 أو مصفوفة C، أو **Write to ROM** مباشرة في ملف.

## الشخصية: 8 نقاط

`GRP0` = نمط 8 نقاط في هذا السطر. لرسم وجه 8 × 8 نكتب 8 بايتات مختلفة في 8 أسطر متتالية. ولونها `COLUP0`. والوضع الأفقي لا يُكتب رقمًا: تكتب في `RESP0` **في اللحظة** التي يكون فيها الشعاع في المكان المطلوب، ثم تضبط بدقة بـ `HMP0` و`HMOVE`. الإجراء `SetHorizPos` في البرنامج يفعل ذلك: يقسم على 15 بحلقة (كل دورة منها 5 دورات معالج = 15 نقطة) ثم يحوّل الباقي إلى قيمة `HMP0`.

## عصا التحكم

`SWCHA`: البتات 7 6 5 4 لعصا اللاعب الأول: يمين، يسار، أسفل، أعلى. **صفر = مضغوط**. وزر الإطلاق في البت 7 من `INPT4` (صفر = مضغوط).

## البرنامج: وجه يتحرك داخل غرفة

<!-- test: {"frames": 10, "hold": "right", "ram": ["$80"], "tia": ["CTRLPF", "COLUP0"]} -->
```dasm run
        processor 6502
        include "atari2600.h"

PlayerX = $80                   ; 0 - 152
PlayerY = $81                   ; السطر الذي يبدأ عنده الوجه (من الأسفل)

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
        sta CTRLPF              ; النصف الأيمن من الجدار مرآة للأيسر
        lda #$C6
        sta COLUPF              ; جدار أخضر
        lda #$1E
        sta COLUP0              ; وجه أصفر
        lda #$84
        sta COLUBK              ; خلفية زرقاء

StartFrame:
        lda #2
        sta VBLANK
        sta VSYNC
        sta WSYNC
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC
        lda #43                 ; 37 سطرًا = 43 × 64 دورة تقريبًا
        sta TIM64T

        lda SWCHA               ; ---- منطق اللعبة والشعاع مطفأ
        and #%10000000          ; يمين؟ (0 = مضغوط)
        bne NoRight
        lda PlayerX
        cmp #140
        bcs NoRight
        inc PlayerX
NoRight:
        lda SWCHA
        and #%01000000          ; يسار؟
        bne NoLeft
        lda PlayerX
        cmp #13
        bcc NoLeft
        dec PlayerX
NoLeft:
        lda PlayerX
        ldx #0                  ; الشخصية 0
        jsr SetHorizPos
        sta WSYNC
        sta HMOVE               ; طبّق الضبط الدقيق

WaitVBlank:
        lda INTIM               ; انتظر انتهاء المؤقت
        bne WaitVBlank
        sta WSYNC
        sta VBLANK              ; A = 0: أشعل الشعاع

        ldy #192
Kernel:
        tya
        sec
        sbc PlayerY
        cmp #8                  ; هل هذا السطر من الوجه؟
        bcc Draw
        lda #0
        beq Store
Draw:   tax
        lda Smiley,x
Store:  sta WSYNC
        sta GRP0
        cpy #185                ; أعلى 8 أسطر وأسفل 8 أسطر: جدار كامل
        bcs Full
        cpy #9
        bcc Full
        lda #%00010000          ; وإلا: عمود واحد على الطرفين
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
        lda #35                 ; 30 سطرًا
        sta TIM64T
Overscan:
        lda INTIM
        bne Overscan
        jmp StartFrame

; A = الموضع (0-159)، X = الكائن (0 = الشخصية 0)
SetHorizPos:
        sta WSYNC
        sec
Div15:  sbc #15
        bcs Div15
        eor #7
        asl
        asl
        asl
        asl
        sta HMP0,x
        sta RESP0,x
        rts

Smiley:                         ; من السطر الأسفل إلى الأعلى
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

المدقق يضغط عصا التحكم **يمينًا** طوال 10 إطارات:

```text output
scanlines: 262
$80 = 86
CTRLPF = $01
COLUP0 = $1E
```

بدأ الوجه عند 76 وتحرك نقطة في كل إطار: `76 + 10 = 86`، والإطار ما زال 262 سطرًا رغم العمل الإضافي، لأن `TIM64T` يحسب وقت VBLANK مهما طال منطق اللعبة (ما دام أقل من 37 سطرًا).

## جرّب في RAD IDE

1. أنشئ مشروع Atari 2600 وضع الكود في `main.asm` واضغط `F5`: يتحرك الوجه بالأسهم في Stella (عصا اللاعب الأول).
2. أضف الحركة للأعلى والأسفل: البتان 4 و 5 من `SWCHA`، وغيّر `PlayerY` بين 9 و 176.
3. افتح **Atari 2600 Playfield Editor** وارسم جدارًا جديدًا، ثم **Export > DASM** والصق الجدول في برنامجك واقرأه بـ `lda Table,y`.
4. افتح الملف الناتج `.bin` في **Tile Editor (Open ROM / Binary)...** (Tools > Retro > Graphics & Text) واختر الصيغة **Atari 2600 player**: ستجد الوجه داخل الـ ROM، وتستطيع رسمه من جديد والحفظ في الملف نفسه.

## اختبر فهمك

```quiz
{"question": "في المسجل SWCHA، ماذا تعني قيمة 0 في البت 7؟", "choices": ["العصا متجهة يمينًا (مضغوط)", "العصا غير موصولة", "زر الإطلاق مضغوط", "لا شيء"], "answer": 0, "explanation": "بتات SWCHA منطقها معكوس: 0 = الاتجاه مضغوط، والبت 7 هو اليمين للاعب الأول."}
```

```quiz
{"question": "لماذا نستخدم TIM64T في فترة VBLANK بدل عدّ 37 أمر WSYNC؟", "choices": ["لأنه أسرع", "لكي نستطيع تنفيذ منطق اللعبة بطول متغير ثم ننتظر انتهاء الوقت فيبقى الإطار 262 سطرًا", "لأن WSYNC لا يعمل في VBLANK", "لتشغيل الصوت"], "answer": 1, "explanation": "المؤقت يقيس الوقت مهما كانت التعليمات، فننتظر INTIM = 0 ثم نبدأ الصورة."}
```
