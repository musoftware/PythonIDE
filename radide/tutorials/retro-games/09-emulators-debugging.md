# الدرس 9: المحاكيات والتصحيح

**في هذا الدرس:**

- **مدير المحاكيات** في RAD IDE: Stella و Mesen و FCEUX و mGBA و VICE و Atari800 و DOSBox-X.
- `F5` و Stop و**إعادة التحميل السريع**.
- **Retro Debugger**: مسجلات المعالج والذاكرة ونقاط التوقف من داخل RAD IDE (VICE و mGBA).
- مصحح Stella مع أسماء برنامجك (الرموز).
- خطأ شهير: الوضع العشري (BCD) لعداد النقاط.

## مدير المحاكيات

**Tools > Retro > Emulators...** جدول بكل محاكٍ: مثبَّت أم لا، والإصدار، والمسار.

- **Download** ينزّل نسخة محمولة (Portable) من **صفحة الإصدارات الرسمية** للمحاكي على GitHub، ويتحقق من بصمة SHA-256 المثبّتة، ويضعها في `%LOCALAPPDATA%\RADIDE\tools\<id>`، ويكتب مصدرها في `RADIDE-SOURCE.json`. لا صلاحيات مدير ولا winget.
- **Browse...** إن كان عندك المحاكي مثبتًا من قبل.
- إعدادات المحاكيات تبقى بعيدة عن ملفاتك الشخصية (وضع محمول لـ mGBA و Mesen، ومجلد `%LOCALAPPDATA%\RADIDE\retro` للبقية).

| النظام | المحاكي الافتراضي | الرخصة |
|---|---|---|
| Atari 2600 | Stella | GPL |
| NES | Mesen 2 (أو FCEUX) | GPL |
| Game Boy / GBA | mGBA | MPL 2.0 |
| Commodore 64 | VICE (x64sc) | GPL |
| Atari 8-bit | Atari800 | GPL |
| DOS | DOSBox-X | GPL |

## التشغيل والإيقاف

- `F5` في أي مشروع ألعاب: يبني ثم يشغّل المحاكي المناسب. وفي مشروع ROM Hacking: يبني الـ ROM المرقّعة ثم يشغّلها.
- زر **Stop** يغلق المحاكي أيضًا (المحاكي مربوط بعملية التشغيل في ويندوز، فلا يبقى معلقًا).
- **Tools > Retro > Reload ROM in Emulator** (`Ctrl+Shift+Alt+F5`): بعد تعديل وبناء جديد. في VICE تُعاد اللعبة **دون إعادة تشغيل المحاكي**؛ والبقية تُعاد بالخيارات نفسها.
- **Tools > Retro > Run ROM in Emulator...**: لأي ملف ROM أو برنامج أو قرص.

## Retro Debugger

**View > Retro Debugger**: نافذة فيها مسجلات المعالج، وعارض ذاكرة بالسادس عشر، ونقاط توقف بالعنوان أو **باسم من برنامجك**، وأزرار Break و Continue و Step و Step Over.

- **VICE** (C64): يتصل RAD IDE ببروتوكول المراقب الثنائي (Binary Monitor) للمحاكي: قراءة وكتابة الذاكرة، ونقاط التوقف، والتنفيذ خطوة خطوة.
- **mGBA** (GBA): عبر بروتوكول GDB الذي يفتحه المحاكي.
- **Stella** (2600) و **Mesen** (NES) لهما مصححات داخلية ممتازة؛ يمرّر RAD IDE لهما ملفات الرموز التي يكتبها البناء في `_build/` (`main.sym` و`main.lst` من DASM، و`.dbg` من ld65، و`.sym` من RGBDS) فتظهر أسماؤك بدل العناوين. في Stella اضغط `` ` `` (المفتاح فوق Tab) لفتح المصحح.

## خطأ شهير: عداد النقاط

الأتاري يعرض النقاط من أرقام 0-9، فيُخزَّن العداد بالصيغة **BCD**: كل نصف بايت رقم عشري، فـ `$12` تعني 12. التعليمة `sed` تجعل `adc` تجمع بالعشري. انسَ `sed` تحصل على `$0A` بعد 9 بدل `$10`!

هذا برنامج يضيف نقطة كل إطار لمدة 12 إطارًا، مرة بالثنائي ومرة بالعشري:

<!-- test: {"frames": 12, "ramhex": ["$80", "$81"]} -->
```dasm run
        processor 6502
        include "atari2600.h"

Binary  = $80
Decimal = $81

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
VBlank: sta WSYNC
        dex
        bne VBlank

        clc                     ; النقاط بالثنائي
        lda Binary
        adc #1
        sta Binary

        sed                     ; النقاط بالعشري (BCD)
        clc
        lda Decimal
        adc #1
        sta Decimal
        cld                     ; لا تنسَ العودة إلى الثنائي

        stx VBLANK              ; X = 0
        ldx #192
Picture:
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
$80 = $0C
$81 = $12
```

في Stella: افتح المصحح، وانظر إلى الخانتين `80` و`81` في نافذة الـ RAM إطارًا بعد إطار (زر **Frame +1**). ستجد `$81` تقفز من `$09` إلى `$10`.

## تمرين: الصورة تتدحرج

صديقك يقول إن صورته «تتدحرج» في Stella وعدّاد الأسطر في Stella يقول 263. اعثر على الخطأ وأصلحه:

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
        sta WSYNC
        lda #0
        sta VSYNC
        ldx #37
VBlank: sta WSYNC
        dex
        bne VBlank
        stx VBLANK
        ldx #192
Picture:
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
        sta WSYNC               ; VSYNC ثلاثة أسطر فقط
        sta WSYNC
        sta WSYNC
        lda #0
        sta VSYNC
        ldx #37
VBlank: sta WSYNC
        dex
        bne VBlank
        stx VBLANK
        ldx #192
Picture:
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

> **نصيحة:** في Stella اضغط `Alt+L` لإظهار عداد الأسطر والإطارات فوق الصورة.

## اختبر فهمك

```quiz
{"question": "ما قيمة A بعد sed ثم clc ثم lda #$09 ثم adc #$01؟", "choices": ["$0A", "$10", "$11", "$09"], "answer": 1, "explanation": "في الوضع العشري 09 + 01 = 10 (BCD) = $10."}
```

```quiz
{"question": "من أين ينزّل RAD IDE المحاكيات؟", "choices": ["من أي موقع فيه الملف", "من صفحات الإصدارات الرسمية فقط، مع التحقق من بصمة SHA-256", "من متجر ويندوز", "تأتي مع RAD IDE"], "answer": 1, "explanation": "التنزيل عند الطلب فقط، من الصفحة الرسمية، إلى مجلد المستخدم، دون صلاحيات مدير."}
```
