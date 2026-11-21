# الدرس 7: محرر الرسوم - البلاطات والشخصيات والخرائط

**في هذا الدرس:**

- كيف تُخزَّن الرسوم في ROM: **البلاطات** (Tiles) و«المستويات» (Bitplanes).
- تكتب بـ Python مفكِّكًا ومُرمِّزًا لبلاطة NES.
- **Tile Editor** في RAD IDE: يعدّل الرسوم داخل الملف نفسه، ويستورد ويصدّر PNG.
- محرر **خريطة البلاطات** (Tile Map) ومحرر **الجدار** للأتاري.

## البلاطة: 8 × 8 نقاط

في NES و Game Boy كل نقطة لها لون من 4 (رقم 0-3 = **2 بت**). البلاطة 64 نقطة × 2 بت = **16 بايت**. لكنها لا تُخزَّن نقطة بعد نقطة، بل في **مستويين**:

```text
 البايتات 0-7   : المستوى 0 = البت الأدنى من لون كل نقطة (سطر في كل بايت، البت 7 = أول نقطة يسارًا)
 البايتات 8-15  : المستوى 1 = البت الأعلى
 لون النقطة = بت المستوى 0 + 2 × بت المستوى 1
```

(في Game Boy المستويان متداخلان: بايت من كل مستوى لكل سطر. لهذا تختار «الصيغة» في المحرر.)

```python run
tile = bytes([0x3C, 0x42, 0xA5, 0x81, 0xA5, 0x99, 0x42, 0x3C,    # المستوى 0
              0x00, 0x00, 0x24, 0x00, 0x24, 0x00, 0x00, 0x00])   # المستوى 1


def decode_nes(t: bytes):
    rows = []
    for y in range(8):
        lo, hi = t[y], t[y + 8]
        rows.append([((lo >> (7 - x)) & 1) | (((hi >> (7 - x)) & 1) << 1) for x in range(8)])
    return rows


for row in decode_nes(tile):
    print("".join(".123"[c] for c in row))
```

```text output
..1111..
.1....1.
1.3..3.1
1......1
1.3..3.1
1..11..1
.1....1.
..1111..
```

العينان لونهما 3 لأن بتّيهما مضاءان في المستويين.

### تمرين: الاتجاه العكسي

اكتب `encode_nes(rows)` التي تحوّل 8 صفوف من الأرقام 0-3 إلى 16 بايت، وتحقق أنها تعيد البلاطة نفسها.

```python exercise
tile = bytes([0x3C, 0x42, 0xA5, 0x81, 0xA5, 0x99, 0x42, 0x3C,
              0x00, 0x00, 0x24, 0x00, 0x24, 0x00, 0x00, 0x00])


def decode_nes(t):
    return [[((t[y] >> (7 - x)) & 1) | (((t[y + 8] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(8)]


def encode_nes(rows):
    out = bytearray(16)
    # املأ المستويين هنا
    return bytes(out)


print(encode_nes(decode_nes(tile)) == tile)
```

```python solution
tile = bytes([0x3C, 0x42, 0xA5, 0x81, 0xA5, 0x99, 0x42, 0x3C,
              0x00, 0x00, 0x24, 0x00, 0x24, 0x00, 0x00, 0x00])


def decode_nes(t):
    return [[((t[y] >> (7 - x)) & 1) | (((t[y + 8] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(8)]


def encode_nes(rows):
    out = bytearray(16)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c & 1:
                out[y] |= 0x80 >> x
            if c & 2:
                out[y + 8] |= 0x80 >> x
    return bytes(out)


print(encode_nes(decode_nes(tile)) == tile)
print(encode_nes(decode_nes(tile)).hex(" ").upper())
```

```text output
True
3C 42 A5 81 A5 99 42 3C 00 00 24 00 24 00 00 00
```

## Tile Editor في RAD IDE

**Tools > Retro > Graphics & Text > Tile Editor (Open ROM / Binary)...** (أو افتح ملف `.chr` مباشرة، أو **View Current File as Tiles** من القائمة نفسها والملف مفتوح في محرر السادس عشر فيبدأ عند المؤشر):

| الجزء | العمل |
|---|---|
| الصيغة | 1bpp، NES 2bpp، Game Boy / SNES 2bpp، SNES 4bpp، Mega Drive 4bpp، GBA 4bpp، أحرف C64 الملونة، شخصيات C64، شخصيات Atari 2600 |
| الإزاحة | أين تبدأ الرسوم في الملف؛ لملفات `.nes` يبدأ تلقائيًا عند CHR ROM. انتقل ببايت أو بلاطة أو صف أو صفحة لتجد الرسوم في ROM لا تعرف صيغتها |
| اللوحة | ألوان NES و Game Boy و C64 و 2600 (NTSC / PAL) و EGA |
| الأدوات | قلم، تعبئة، خط، تحديد؛ كتلة من 1 × 1 إلى 8 × 8 بلاطات؛ قلب وتدوير؛ الزر الأيمن يلتقط لونًا؛ تراجع وإعادة |
| Write to File (`Ctrl+S`) | يكتب البايتات في الملف نفسه **دون تغيير حجمه**، وكل محرر مفتوح للملف نفسه (مثل محرر السادس عشر) يتحدث فورًا |
| PNG | **Export PNG** للرسم في برنامج آخر، و**Import PNG** يعيد كل نقطة إلى أقرب لون في اللوحة |

**سير عمل تعديل لعبة:** في مشروع ROM Hacking اضغط **Edit Working Copy**، ثم افتح نسخة العمل في Tile Editor، وارسم، و`Ctrl+S`، ثم **Capture Edits as Patch** و`F5`: ترى رسمك الجديد في المحاكي.

## الخرائط والجدار

- **Tile Map Editor** (ملف `.rtmap`): خريطة شاشة NES (مع جدول السمات يُحسب تلقائيًا) أو خريطة Game Boy، من بلاطات أي ملف؛ بلاطات كبيرة 2 × 2 (Metatiles)؛ تصدير بيانات ca65 أو DASM أو RGBDS أو C.
- **Playfield Editor** (ملف `.rtpf`) للأتاري 2600: رأيته في الدرس 4.

## اختبر فهمك

```quiz
{"question": "كم بايت تشغل بلاطة NES واحدة 8 × 8 بأربعة ألوان؟", "choices": ["8", "16", "32", "64"], "answer": 1, "explanation": "64 نقطة × 2 بت = 128 بت = 16 بايت (مستويان كل منهما 8 بايت)."}
```

```quiz
{"question": "لماذا يكتب Tile Editor في الملف دون تغيير حجمه؟", "choices": ["لأن تغيير الحجم يحرّك كل ما بعد الرسوم فتفسد العناوين في الـ ROM", "لأنه لا يستطيع", "لتوفير الذاكرة", "لا سبب"], "answer": 0, "explanation": "الكود يشير إلى عناوين ثابتة؛ الرسوم تُعدَّل في مكانها."}
```
