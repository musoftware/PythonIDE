# الدرس 5: أساسيات NES و Game Boy

**في هذا الدرس:**

- **NES**: المعالج 2A03 وشريحة الرسم **PPU**، والبلاطات (Tiles) في **CHR ROM**، والمخطط NROM.
- أول برنامج NES بالمجمِّع **ca65** والرابط **ld65**: لون الخلفية.
- **Game Boy**: المعالج SM83، والذاكرة VRAM، ورأس الخرطوشة والمجموع الاختباري.
- أول برنامج Game Boy بـ **RGBDS**: لوحة الألوان.

## NES في دقيقة

| الجزء | ماذا فيه |
|---|---|
| 2A03 | معالج 6502 (بلا الوضع العشري) + الصوت؛ 2 KB RAM عند `0000`-`07FF` |
| PPU | شريحة رسم لها ذاكرتها الخاصة: البلاطات وجداول الأسماء (الخلفية) والألوان و64 شخصية (Sprites) |
| PRG ROM | الكود عند `8000`-`FFFF` |
| CHR ROM | **البلاطات**: كل بلاطة 8 × 8 نقاط بأربعة ألوان = 16 بايت |

لا يكتب المعالج في ذاكرة PPU مباشرة: يكتب العنوان مرتين في `PPUADDR` (`$2006`) ثم البيانات في `PPUDATA` (`$2007`). والكتابة آمنة فقط أثناء **VBLANK** أو والرسم مطفأ.

**File > New Project... > Retro Games > NES Game (ca65 assembly)** ينشئ مشروعًا فيه `main.s` و`nes.inc` (أسماء المسجلات) و`nes.cfg` (خريطة ذاكرة NROM: رأس 16 بايت + 32 KB كود + 8 KB بلاطات). `F5` يبني بـ ca65 و ld65 ويشغّل في **Mesen**. ويوجد قالب بلغة **C** أيضًا (cc65).

## أول برنامج NES

<!-- test: {} -->
```ca65 run
.include "nes.inc"

.segment "HEADER"
        .byte "NES", $1A        ; رأس iNES
        .byte 2                 ; 2 × 16 KB كود
        .byte 1                 ; 1 × 8 KB بلاطات
        .byte $01, $00          ; المخطط 0 (NROM)، انعكاس رأسي
        .res 8, 0

.segment "CODE"
reset:
        sei
        cld
        ldx #$FF
        txs
        inx                     ; X = 0
        stx PPUCTRL             ; لا مقاطعة NMI بعد
        stx PPUMASK             ; الرسم مطفأ
@wait1: bit PPUSTATUS           ; انتظر أول VBLANK (الـ PPU يسخن)
        bpl @wait1
@wait2: bit PPUSTATUS           ; والثاني
        bpl @wait2

        lda #$3F                ; عنوان PPU = $3F00: لون الخلفية العام
        sta PPUADDR
        lda #$00
        sta PPUADDR
        lda #$11                ; أزرق
        sta PPUDATA
        lda #%00001000          ; أظهر الخلفية
        sta PPUMASK
forever:
        jmp forever

nmi:
irq:
        rti

.segment "VECTORS"
        .word nmi, reset, irq   ; FFFA: NMI ثم RESET ثم IRQ

.segment "CHARS"
        .res 8192, 0            ; بلاطات فارغة (8 KB)
```

المدقق يبني البرنامج ويقرأ رأس الملف الناتج:

```text output
iNES: mapper 0, PRG 32 KB, CHR 8 KB
```

لاحظ الفرق عن الأتاري: هنا لا نسابق الشعاع. الـ PPU يرسم الشاشة كلها من ذاكرته، والبرنامج يغيّر تلك الذاكرة أثناء VBLANK (عادة في مقاطعة **NMI** التي تأتي 60 مرة في الثانية). قالب RAD IDE الكامل يرسم شخصية تتحرك بالأسهم باستخدام **OAM DMA**.

## Game Boy في دقيقة

| الجزء | ماذا فيه |
|---|---|
| SM83 | معالج قريب من Z80 (`ld a, [hl]` ...) بسرعة 4 MHz |
| الشاشة | 160 × 144، أربع درجات من الأخضر؛ `rLY` رقم السطر الحالي (144-153 = VBLANK) |
| VRAM | البلاطات عند `8000` والخلفية عند `9800` |
| الرأس | عند `0100`-`014F`: قفزة البداية، والشعار، والعنوان، والمجموعان الاختباريان |

جهاز Game Boy الحقيقي يرفض تشغيل خرطوشة شعارها أو مجموعها الاختباري خاطئ. الأداة **rgbfix** تكتبها بعد الربط، لذلك نترك في الكود مكانًا فارغًا: `ds $150 - @, 0`.

**New Project > Retro Games > Game Boy Game (RGBDS)**: `main.asm` و`gb.inc`. `F5` = rgbasm ثم rgblink ثم rgbfix ثم **mGBA**.

<!-- test: {} -->
```rgbds run
INCLUDE "gb.inc"

SECTION "Header", ROM0[$100]
        nop
        jp Start
        ds $150 - @, 0          ; rgbfix يكتب الشعار والعنوان والمجموع الاختباري هنا

SECTION "Main", ROM0
Start:
        di
        ld sp, $FFFE
.wait:  ldh a, [rLY]            ; انتظر VBLANK قبل إطفاء الشاشة
        cp 144
        jr c, .wait
        xor a
        ldh [rLCDC], a          ; أطفئ الشاشة
        ld a, %00011011         ; لوحة الخلفية: الدرجات معكوسة
        ldh [rBGP], a
        ld a, %10000001         ; الشاشة تعمل + الخلفية
        ldh [rLCDC], a
.loop:  jr .loop
```

```text output
Game Boy: title LESSON, logo OK, header checksum OK, global checksum OK
```

المدقق لا يخزن شعار نينتندو نفسه؛ بل يقارن مجموعه CRC32 بما يجب أن يكون، لأن الشعار من حقوق الشركة. ومحرر السادس عشر في RAD IDE يفحص المجموعين ويصلحهما في أي ملف `.gb` أو `.gbc` أو `.gba` أو SNES أو Mega Drive: **ROM Workbench > Fix Header Checksum**.

## مقارنة سريعة

| | Atari 2600 | NES | Game Boy |
|---|---|---|---|
| ذاكرة الشاشة | لا يوجد (سطر واحد) | جداول أسماء في PPU | خريطة في VRAM |
| البلاطات | لا يوجد | CHR ROM (2 بت للنقطة) | VRAM (2 بت للنقطة) |
| المجمِّع في RAD IDE | DASM | ca65 / ld65 (أو cc65 للغة C) | RGBDS |
| المحاكي | Stella | Mesen (أو FCEUX) | mGBA |

## اختبر فهمك

```quiz
{"question": "كيف يكتب برنامج NES لونًا في ذاكرة الـ PPU؟", "choices": ["sta $3F00 مباشرة", "يكتب العنوان في PPUADDR مرتين ثم البيانات في PPUDATA", "عبر OAM DMA فقط", "لا يستطيع"], "answer": 1, "explanation": "ذاكرة PPU منفصلة: عنوان 16 بت عبر $2006 (البايت الأعلى ثم الأدنى) ثم البيانات عبر $2007."}
```

```quiz
{"question": "لماذا نترك ds $150 - @, 0 في رأس برنامج Game Boy؟", "choices": ["لتسريع البرنامج", "لأن rgbfix سيكتب هناك الشعار والعنوان والمجاميع الاختبارية", "لأن المعالج لا يقرأ هذه المنطقة", "لا معنى له"], "answer": 1, "explanation": "المنطقة 0104-014F هي رأس الخرطوشة؛ rgbfix يملؤها بعد الربط."}
```
