# الدرس 7: المجاميع الاختبارية (Checksums) والتحقق منها

**في هذا الدرس:**

- لماذا تحمي الوحدة برنامجها بمجاميع اختبارية، وماذا يحدث إذا لم تُصحَّح بعد التعديل.
- الأنواع العامة: **مجموع** 8/16/32 بت، و**XOR**، و**CRC-16** و**CRC-32**، ونسخة **المتمم**.
- **الكتلة**: مدى أو عدة مديات، ومناطق مستثناة، ومكان تخزين القيمة.
- **الباحث** عن المجاميع في الأصل، والتحقق المتقاطع بملف أصلي ثانٍ.
- التصحيح التلقائي عند الحفظ وعند **Build**.

## لماذا المجموع الاختباري؟

ذاكرة الفلاش قد تتلف، والبرمجة قد تنقطع. لذلك يحسب برنامج الإقلاع **مجموعًا** لكل جزء ويقارنه بقيمة مخزّنة. إذا اختلفا رفضت الوحدة تشغيل ذلك الجزء أو دخلت وضع الطوارئ. **أي تعديل في خريطة يغيّر المجموع**، فيجب إعادة حسابه وكتابته قبل الاستخدام. هذا جزء عادي من أي تعديل مشروع، مثل حفظ الملف.

## الأنواع العامة

```python run
import zlib

data = b"123456789"                         # النص المعياري لفحص خوارزميات CRC

s8 = sum(data) & 0xFF
s16 = sum(data) & 0xFFFF
x8 = 0
for b in data:
    x8 ^= b


def crc16_ccitt_false(buf: bytes) -> int:
    crc = 0xFFFF
    for b in buf:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


print(f"sum8  = {s8:02X}")
print(f"sum16 = {s16:04X}")
print(f"xor8  = {x8:02X}")
print(f"CRC-16/CCITT-FALSE = {crc16_ccitt_false(data):04X}")
print(f"CRC-32 (zip)       = {zlib.crc32(data):08X}")
c = crc16_ccitt_false(data)
print(f"complement copy    = {~c & 0xFFFF:04X}  (value + complement = {c + (~c & 0xFFFF):04X})")
```

```text output
sum8  = DD
sum16 = 01DD
xor8  = 31
CRC-16/CCITT-FALSE = 29B1
CRC-32 (zip)       = CBF43926
complement copy    = D64E  (value + complement = FFFF)
```

القيمتان `29B1` و`CBF43926` هما **قيم الفحص** المعروفة في كتالوج CRC؛ كل إعداد مسبق في RAD IDE (21 إعدادًا: CRC-8 و CRC-16 و CRC-32 بأشكالها، ومنها CCITT و MODBUS و XMODEM و CRC-32C و AUTOSAR) يُختبر عليها. وتستطيع تعريف أي CRC من 3 إلى 64 بت: الطول والمعادلة (Polynomial) والقيمة الابتدائية والعكس و XOR النهائي.

## الكتلة: ماذا يُجمَع وأين يُخزَّن

| الحقل | المعنى |
|---|---|
| المديات (Ranges) | من أين إلى أين يُحسب (قد تكون عدة مديات) |
| المستثنى (Skip) | منطقة لا تدخل، مثل منطقة **التكيّف** التي تتغير في السيارة |
| التخزين (Store) | عنوان القيمة، وعرضها 1/2/4 بايت، وترتيبها |
| المتمم (Complement) | نسخة ثانية = NOT القيمة، في عنوان آخر |

هذا برنامج يتحقق من كتلة sum16، ثم يعدّل بايتًا في «الخريطة»، فيصبح المجموع خطأ، ثم يصححه:

```python run
import struct

image = bytearray(bytes((i * 7) & 0xFF for i in range(0x100)))
START, END, STORE = 0x00, 0xFE, 0xFE          # المجموع 16 بت BE للمدى 00..FD مخزن في FE


def calc(buf):
    return sum(buf[START:END]) & 0xFFFF


struct.pack_into(">H", image, STORE, calc(image))
print("stored OK? ", struct.unpack_from(">H", image, STORE)[0] == calc(image))

image[0x40] += 5                              # تعديل خلية في «خريطة»
stored = struct.unpack_from(">H", image, STORE)[0]
print(f"after edit: stored {stored:04X}, computed {calc(image):04X} -> WRONG")

struct.pack_into(">H", image, STORE, calc(image))
print("corrected? ", struct.unpack_from(">H", image, STORE)[0] == calc(image))
```

```text output
stored OK?  True
after edit: stored 7D95, computed 7D9A -> WRONG
corrected?  True
```

## الباحث: من أين أعرف الكتل؟

ملف مجهول لا يقول أين مجاميعه. **الباحث** (Find Checksums) يجرّب على **الأصل** - حيث كل المجاميع صحيحة - كل الخوارزميات العامة على مديات تبدأ وتنتهي عند حدود معقولة، والقيمة مخزنة بعد المدى أو قبله (مجموع الرأس) أو بعد مدى فيه فجوة، ويلاحظ أزواج المتمم. ثم يرتب المرشحين.

> **التحقق المتقاطع:** القيمة 16 بت قد تطابق بالصدفة. إذا كان معك أصلٌ ثانٍ لنفس النوع (نسخة برنامج أخرى)، فعّل **Cross-check with other originals**: يبقى فقط المرشح الذي يصح في الملفين.

```fwpy run
from radide.firmware.checksum import find, verify, correct
from radide.firmware.project.synth import demo_blocks, image

data = image()                                   # 64 KB اصطناعي فيه 3 كتل معروفة
res = find(data, ["sum16-be", "crc16-ccitt-false", "crc32"], search_holes=True, holes=[(0xC000, 0xD000)])
known = {b.store for b in demo_blocks()}
for c in res.candidates[:3]:
    print(f"{c.algorithm:18} store 0x{c.store:04X}  {'known block' if c.store in known else ''}")
found = {c.store for c in res.candidates} & known
print(f"known blocks among the {len(res.candidates)} candidates: {len(found)} of {len(known)}")

mod = bytearray(data)
mod[0x8200] ^= 0x10                              # تعديل في المعايرة
print("after edit:", [r.ok for r in verify(bytes(mod), demo_blocks())])
correct(mod, demo_blocks())
print("corrected: ", [r.ok for r in verify(bytes(mod), demo_blocks())])
```

```text output
crc16-ccitt-false  store 0x7FFC  known block
crc32              store 0xFFFC  known block
crc16-ccitt-false  store 0x2400  
known blocks among the 17 candidates: 3 of 3
after edit: [True, True, False]
corrected:  [True, True, True]
```

## في RAD IDE

- **Project > ECU Project > Checksums...**: جدول الكتل، ومحرر كتلة (CRC مخصص، مجموع/XOR)، و**Verify** و**Correct**، وتصدير/استيراد **ملف تعريف** (Profile) JSON، وتبويب **Finder** يعمل في الخلفية مع شريط تقدم وإلغاء، ثم **Add Selected as Block**.
- منضدة العمل: **Verify Checksums** (`Ctrl+Shift+V`) ولوحة **Checksum Report** (المخزّن والمحسوب والحالة)، و**More > Correct Checksums** و**Load Profile** و**Find Checksums**.
- **التصحيح عند الحفظ**: احفظ نسخة العمل في محرر السادس عشر فيعيد RAD IDE حساب الكتل ويذكرها في Output. و**Build** يصحح دائمًا قبل كتابة الملف الناتج (من Build Settings).
- **Checksum Toolkit (any file)...** يعمل على أي ملف خارج مشروع.

> RAD IDE لا يحتوي خوارزميات خاصة بشركة معينة؛ الإعدادات المسبقة خوارزميات عامة من الكتالوج. وملف التعريف يذكّرك: **تحقق منه على أصلك أنت** قبل الاعتماد عليه.

## اختبر فهمك

```quiz
{"question": "عدّلت خريطة ولم تصحح المجموع الاختباري. ماذا يُتوقع؟", "choices": ["لا شيء", "تكتشف الوحدة اختلاف المجموع فترفض الجزء أو تدخل وضع الطوارئ", "يتحسن الأداء", "يُصحَّح وحده في السيارة"], "answer": 1, "explanation": "المجموع يحمي من التلف، وأي تعديل يغيره فيجب إعادة حسابه."}
```

```quiz
{"question": "لماذا تُستثنى منطقة التكيّف (Adaptation) من بعض الكتل؟", "choices": ["لأنها مشفرة", "لأن الوحدة تكتب فيها أثناء القيادة فتتغير، فلا يصح جمعها مع البرنامج الثابت", "لأنها فارغة دائمًا", "لأنها نص"], "answer": 1, "explanation": "البيانات المتغيرة توضع في فجوة (Skip) خارج المجموع."}
```

```quiz
{"question": "الباحث وجد مرشح sum16 يطابق في ملفك. كيف تتأكد أنه ليس صدفة؟", "choices": ["أثق به دائمًا", "أفعّل التحقق المتقاطع بأصل ثانٍ؛ يبقى المرشح إن صح في الملفين", "أغيّر الخوارزمية", "أحذف الملف"], "answer": 1, "explanation": "تطابق 16 بت بالصدفة وارد؛ الأصل الثاني يزيل المرشحين الوهميين."}
```
