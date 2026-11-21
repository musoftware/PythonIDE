# الدرس 3: خريطة الذاكرة وعنوان التحميل وتخمين المعالج

**في هذا الدرس:**

- **خريطة الذاكرة**: أين يقع الفلاش والذاكرة RAM في عالم المعالج.
- **ترتيب البايتات**: Little Endian و Big Endian.
- **جدول المتجهات** في معالجات ARM Cortex-M، وكيف يكشف عنوان التحميل.
- كيف يخمّن RAD IDE **نوع المعالج** و**عنوان التحميل** مع درجة ثقة ودليل.
- **الأنتروبيا**: خريطة سريعة للكود والمعايرة والفراغ.

## خريطة الذاكرة

المعالج يرى مساحة عناوين واحدة، وأجزاؤها موزعة على أجهزة مختلفة. مثال لمعالج STM32 (ARM Cortex-M) مثل الذي في مشروع rusEFI:

| العنوان | ما فيه |
|---|---|
| `0x08000000` | بداية **الفلاش**: هنا يوضع الملف الخام، بايته الأول عند هذا العنوان |
| `0x20000000` | **RAM**: المتغيرات والمكدس (Stack) |
| `0x40000000` | **المنافذ والأجهزة الطرفية** (Peripherals): المؤقتات و CAN و ADC |

لكل عائلة خريطتها: معالجات TriCore (AURIX) تبدأ الفلاش عادة عند `0x80000000`، و PowerPC (MPC5xxx) عند `0x00000000`. إذا حللت الملف بعنوان خاطئ فكل مؤشر في الكود سيشير إلى مكان خاطئ، ولن تجد أي مرجع لجدول أو نص.

## ترتيب البايتات

الرقم `0x12345678` يُخزَّن في 4 بايتات بترتيبين:

```python run
import struct

value = 0x12345678
le = struct.pack("<I", value)          # Little Endian: الأصغر أولًا (ARM و TriCore و x86)
be = struct.pack(">I", value)          # Big Endian: الأكبر أولًا (PowerPC و 68K و HC12)
print("little:", le.hex(" "))
print("big:   ", be.hex(" "))

two = bytes([0x03, 0xE8])
print("as BE 16-bit:", int.from_bytes(two, "big"))
print("as LE 16-bit:", int.from_bytes(two, "little"))
```

```text output
little: 78 56 34 12
big:    12 34 56 78
as BE 16-bit: 1000
as LE 16-bit: 59395
```

نفس البايتين `03 E8` تعني 1000 أو 59395 حسب الترتيب. لذلك تسأل أداة الخرائط دائمًا: **16 بت Hi-Lo أم Lo-Hi؟** (Hi-Lo = Big Endian).

## جدول المتجهات يكشف العنوان

في معالجات **ARM Cortex-M** أول كلمة في الفلاش هي قيمة **مؤشر المكدس** الابتدائية (عنوان في RAM)، والثانية **عنوان دالة البدء** (Reset handler) مع البت الأدنى 1 (علامة نمط Thumb). إذا كانت الكلمة الثانية `0x08000209` فالكود عند `0x08000208`، إذن الملف يبدأ غالبًا عند `0x08000000`:

```python run
import struct

# أول 16 بايت من صورة اصطناعية (كما في محرر السادس عشر)
head = bytes.fromhex("00 00 01 20 09 02 00 08 0b 02 00 08 0b 02 00 08".replace(" ", ""))
sp, reset, nmi, hard = struct.unpack("<4I", head)
print(f"initial SP : 0x{sp:08X}  (RAM? {0x20000000 <= sp < 0x20100000})")
print(f"reset      : 0x{reset:08X}  (Thumb bit = {reset & 1})")
print(f"handler at : 0x{reset & ~1:08X}")
base = (reset & ~1) & 0xFFF00000
print(f"base guess : 0x{base:08X}")
print(f"reset offset in the file: 0x{(reset & ~1) - base:X}")
```

```text output
initial SP : 0x20010000  (RAM? True)
reset      : 0x08000209  (Thumb bit = 1)
handler at : 0x08000208
base guess : 0x08000000
reset offset in the file: 0x208
```

## التخمين في RAD IDE

افتح الملف بـ **Tools > Firmware & ECU > Analyze Firmware File...** (أو زر **Analyze** في منضدة العمل `Ctrl+Shift+A`). في تبويب **Overview** جدولان:

- **CPU**: كل معالج معروف (Cortex-M و ARM و PowerPC و PowerPC VLE و TriCore و C166 و HC12 و SH-2 و V850 و 68K و 8051) مع **درجة ثقة** و**الدليل**: كم نمطًا نموذجيًا لتعليماته وُجد (مطروحًا منه ما يعطيه ملف عشوائي)، وجدول المتجهات أو رأس الإقلاع.
- **Load address**: العناوين المرشحة مرتبة بعدد الكلمات في الملف التي تشير **بالضبط** إلى بداية نص أو إلى مدخل في جدول المتجهات.

انقر مرتين على معالج أو عنوان لاعتماده. الكتلة التالية تفعل الشيء نفسه بمكتبة RAD IDE على صورة ARM اصطناعية:

```fwpy run
from radide.firmware.analysis.report import analyze
from radide.firmware.analysis.synth import make_image
from radide.firmware.formats.memmap import MemoryMap

img = make_image("arm-thumb", seed=11)               # ملف اصطناعي: كود Thumb + خرائط + نصوص
mm = MemoryMap.from_bytes(img.bytes(), 0)            # نفتحه كملف خام لا نعرف عنوانه
res = analyze(mm)
best = res.detection.arches[0]
print("CPU :", best.label, f"{best.confidence:.0%}")
print("base:", hex(res.base))
print("true base:", hex(img.base))
for b in res.detection.bases[:2]:
    print(f"  candidate 0x{b.base:08X}  {b.confidence:.0%}")
```

```text output
CPU : ARM Cortex-M (Thumb / Thumb-2) 90%
base: 0x8000000
true base: 0x8000000
  candidate 0x08000000  97%
  candidate 0x08008000  3%
```

## الأنتروبيا: خريطة سريعة للملف

**الأنتروبيا** تقيس «عشوائية» البايتات من 0 (كلها متشابهة) إلى 8 بت للبايت (عشوائية تمامًا). الفراغ `FF` قريب من 0، والنص حوالي 4، والكود 5-7، والبيانات المضغوطة أو المشفرة قريبة من 8:

```python run
import math
import random


def entropy(block: bytes) -> float:
    counts = [0] * 256
    for b in block:
        counts[b] += 1
    n = len(block)
    return abs(-sum(c / n * math.log2(c / n) for c in counts if c))


rnd = random.Random(1)
samples = {
    "empty (FF)": b"\xFF" * 1024,
    "text": b"SW 1234567890 CALIBRATION DATA " * 33,
    "map": bytes(100 + (i % 16) * 2 + (i // 64) for i in range(1024)),
    "random": bytes(rnd.randrange(256) for _ in range(1024)),
}
for name, block in samples.items():
    print(f"{name:11} {entropy(block[:1024]):.2f}")
```

```text output
empty (FF)  0.00
text        4.31
map         5.35
random      7.80
```

لاحظ أن الخريطة (5.35) قريبة من الكود؛ الأنتروبيا وحدها لا تفرق بينهما. لذلك يفحص RAD IDE أيضًا هل القيم المتجاورة تتغير ببطء.

في RAD IDE يرسم تبويب **Entropy** هذا لكل كتلة، ويلوّن المناطق: فارغة، نص، **شبيهة بالمعايرة** (قيم متجاورة تتغير ببطء)، شبيهة بالكود، بيانات، مضغوطة/مشفرة. انقر مرتين على منطقة لتفتحها في محرر السادس عشر.

## اختبر فهمك

```quiz
{"question": "الكلمة الثانية في ملف Cortex-M هي 0x08000209. ماذا تستنتج؟", "choices": ["الملف مشفر", "دالة البدء عند 0x08000208 بنمط Thumb، والملف يبدأ غالبًا عند 0x08000000", "حجم الملف 0x209", "المعالج PowerPC"], "answer": 1, "explanation": "البت الأدنى 1 علامة Thumb، والعنوان يقع في فلاش STM32 الذي يبدأ عند 0x08000000."}
```

```quiz
{"question": "منطقة في الملف أنتروبيتها قريبة من 8 بت للبايت. ماذا يُرجَّح أنها؟", "choices": ["فراغ FF", "نص", "بيانات مضغوطة أو مشفرة", "جدول معايرة ناعم"], "answer": 2, "explanation": "العشوائية الكاملة علامة الضغط أو التشفير؛ الجداول والنصوص أقل بكثير."}
```
