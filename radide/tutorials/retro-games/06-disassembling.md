# الدرس 6: تفكيك ROM إلى مشروع وإعادة بنائه مطابقًا

**في هذا الدرس:**

- ما هو **المفكِّك** (Disassembler) ولماذا يحتاج إلى «تتبّع» الكود.
- تكتب مفكِّكًا صغيرًا لـ 6502 بـ Python.
- **Disassemble ROM into Project** في RAD IDE: مشروع كامل يُعاد بناؤه **مطابقًا بايتًا ببايت**.
- `hints.json`: تخبر المفكِّك أين الكود وأين البيانات.

## من البايتات إلى التعليمات

المعالج 6502 يقرأ **رمز العملية** (Opcode) بايتًا واحدًا، ثم 0 أو 1 أو 2 بايت معامِلات حسب **طريقة العنونة**. مثلًا `A9 02` = `lda #$02`، و`85 01` = `sta $01`، و`D0 FB` = `bne` إلى الخلف 5 بايتات. المفكِّك يعكس عمل المجمِّع:

```python run
OPS = {  # رمز العملية: (الاسم، طريقة العنونة)
    0xA9: ("lda", "imm"), 0xA2: ("ldx", "imm"), 0x85: ("sta", "zp"), 0x8D: ("sta", "abs"),
    0xE8: ("inx", "imp"), 0xCA: ("dex", "imp"), 0xD0: ("bne", "rel"), 0x4C: ("jmp", "abs"),
    0x78: ("sei", "imp"), 0xD8: ("cld", "imp"),
}
SIZE = {"imp": 1, "imm": 2, "zp": 2, "rel": 2, "abs": 3}


def disassemble(code: bytes, org: int):
    pc = 0
    while pc < len(code):
        op = code[pc]
        if op not in OPS:
            print(f"{org + pc:04X}  {op:02X}        .byte ${op:02X}")
            pc += 1
            continue
        name, mode = OPS[op]
        raw = code[pc:pc + SIZE[mode]]
        if mode == "imm":
            arg = f"#${raw[1]:02X}"
        elif mode == "zp":
            arg = f"${raw[1]:02X}"
        elif mode == "abs":
            arg = f"${raw[1] | raw[2] << 8:04X}"
        elif mode == "rel":
            off = raw[1] - 256 if raw[1] >= 128 else raw[1]
            arg = f"${org + pc + 2 + off:04X}"
        else:
            arg = ""
        print(f"{org + pc:04X}  {raw.hex(' ').upper():8}  {name} {arg}".rstrip())
        pc += len(raw)


disassemble(bytes([0x78, 0xD8, 0xA2, 0x25, 0x85, 0x02, 0xCA, 0xD0, 0xFB, 0x4C, 0x00, 0xF0]), 0xF000)
```

```text output
F000  78        sei
F001  D8        cld
F002  A2 25     ldx #$25
F004  85 02     sta $02
F006  CA        dex
F007  D0 FB     bne $F004
F009  4C 00 F0  jmp $F000
```

هذه الحلقة هي 37 سطرًا من VBLANK في الدرس 3: `25` بالسادس عشر = 37، و`$02` = `WSYNC`.

## مشكلة: أين الكود وأين البيانات؟

في الـ ROM تختلط التعليمات بالرسوم والجداول. لو فككنا الرسوم كأنها كود لظهرت تعليمات بلا معنى. لذلك يبدأ مفكِّك RAD IDE من **المتجهات** (`RESET` و`NMI` و`IRQ`) ويتتبّع كل قفزة واستدعاء وتفرّع؛ ما وصل إليه = كود، وما لم يصل إليه = بيانات تُكتب `.byte`.

## Disassemble ROM into Project

**Tools > Retro > Retro Development > Disassemble ROM into Project...**:

1. اختر ملف ROM (لعبتك، أو تفريغك الشخصي) ومجلدًا للمشروع.
2. يكتشف RAD IDE النظام: Atari 2600 (2K / 4K / F8 / F6 / F4)، أو NES (iNES، وملف `chr.bin` للبلاطات)، أو Game Boy، أو C64 `.prg`، أو ZX Spectrum `.tap`.
3. يكتب `main.asm` (أو `main.s`) للمجمِّع المناسب (DASM أو ca65 أو RGBDS أو sjasmplus) مع أسماء مسجلات العتاد وشرحها، ونسخة من الأصل في `rom/`، و`hints.json`.
4. ثم **يبني المشروع فورًا ويقارن**: يظهر «**byte-identical**» بالأخضر، أو أول اختلاف بالأحمر.

لماذا المطابقة صعبة؟ لأن للتعليمة الواحدة أحيانًا ترميزين: `lda $0080` (3 بايتات) و`lda $80` (بايتان) لهما المعنى نفسه، والمجمِّع يختار الأقصر. لذلك يكتب المفكِّك `lda.w` عندما كان الأصل بالترميز الطويل، ويكتب التعليمات غير الموثّقة بايتات `.byte` مع اسمها في تعليق.

هذا شكل الناتج (جزء من تفكيك برنامج الدرس 3، مع أسماء المفكِّك `LF00A` و`ram_80`):

<!-- test: {"frames": 2, "ram": ["$80"]} -->
```dasm run
; Rainbow - disassembled by RAD IDE (Atari 2600, dasm)
        processor 6502

VSYNC = $00    ; Vertical sync
VBLANK = $01    ; Vertical blank
WSYNC = $02    ; Wait for the end of the scanline
COLUBK = $09    ; Background colour-luminance
ram_80 = $80    ; zero-page RAM variable

        seg code
        org $F000

Reset
        sei                                     ; F000
        cld                                     ; F001
        ldx #$00                                ; F002
        txa                                     ; F004
LF005
        sta VSYNC,x                             ; F005
        inx                                     ; F007
        bne LF005                               ; F008
        dex                                     ; F00A
        txs                                     ; F00B
LF00C
        lda #$02                                ; F00C
        sta VBLANK                              ; F00E
        sta VSYNC                               ; F010
        sta WSYNC                               ; F012
        sta WSYNC                               ; F014
        sta WSYNC                               ; F016
        lda #$00                                ; F018
        sta VSYNC                               ; F01A
        ldx #$25                                ; F01C
LF01E
        sta WSYNC                               ; F01E
        dex                                     ; F020
        bne LF01E                               ; F021
        lda #$00                                ; F023
        sta VBLANK                              ; F025
        ldx #$C0                                ; F027
        ldy ram_80                              ; F029
LF02B
        sty COLUBK                              ; F02B
        iny                                     ; F02D
        sta WSYNC                               ; F02E
        dex                                     ; F030
        bne LF02B                               ; F031
        lda #$02                                ; F033
        sta VBLANK                              ; F035
        ldx #$1E                                ; F037
LF039
        sta WSYNC                               ; F039
        dex                                     ; F03B
        bne LF039                               ; F03C
        inc ram_80                              ; F03E
        jmp LF00C                               ; F040

        org $FFFC
        .word Reset
        .word Reset
```

```text output
scanlines: 262
$80 = 2
```

المشروع الناتج مشروع عادي: غيّر `ram_80` إلى `Frame` و`LF02B` إلى `Picture` (أداة **Rename** أو بحث واستبدال)، وأضف تعليقاتك، ثم **Tools > Retro > Retro Development > Rebuild Check**: ما دمت لم تغيّر التعليمات يبقى الناتج مطابقًا.

## hints.json

إذا وصل البرنامج إلى كود عبر جدول قفزات أو مؤشر، لا يراه المتتبع فيبقى `.byte`. افتح `hints.json`:

```text
{
  "code": ["F200"],                        عناوين يبدأ عندها كود
  "data": [["F300", "F3FF"]],              مدى بيانات وإن بدا كودًا
  "labels": {"F02B": "Picture"},           أسماء تختارها
  "comments": {"F00C": "بداية الإطار"},
  "undocumented": false                    اتبع تعليمات 6502 غير الموثقة
}
```

ثم **Re-disassemble with Hints**: يكتب تفكيكًا جديدًا (ويحتفظ بالقديم `.bak`) ويتحقق من المطابقة مرة أخرى.

> **تذكير قانوني:** فكّك ألعابك وتفريغاتك الشخصية للتعلم. لا تنشر تفكيك لعبة تجارية كاملًا؛ انشر رقعة.

## اختبر فهمك

```quiz
{"question": "لماذا يبدأ المفكِّك من متجه RESET بدل أول بايت في الملف؟", "choices": ["لأن أول بايت دائمًا صفر", "لأنه يتتبع الكود من نقطة البداية الحقيقية حتى لا يفكّك البيانات كأنها تعليمات", "لأنه أسرع", "لا فرق"], "answer": 1, "explanation": "التتبع من المتجهات يفصل الكود عن البيانات (الرسوم والجداول)."}
```

```quiz
{"question": "لماذا يكتب المفكِّك أحيانًا lda.w $0080 بدل lda $80؟", "choices": ["خطأ في المفكِّك", "لأن الأصل استخدم الترميز ذا الثلاثة بايتات، والمجمِّع سيختار القصير لو كُتب lda $80 فيختلف الناتج", "لأن .w أسرع", "لأن $80 ليس عنوانًا"], "answer": 1, "explanation": "الهدف إعادة بناء مطابقة بايتًا ببايت، فيجب الحفاظ على الترميز نفسه."}
```
