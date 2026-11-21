# الدرس 6: تعديل الخرائط بالوحدات الفيزيائية وملفات A2L

**في هذا الدرس:**

- **القيمة الخام** و**القيمة الفيزيائية**: المعامل (Factor) والإزاحة (Offset).
- لماذا يُقرَّب كل تعديل إلى دقة التخزين ويُقصّ إلى حدود النوع.
- محرر الخرائط في RAD IDE: الجدول الملون و 2D و 3D والمفاتيح السريعة.
- ملفات **ASAP2 / A2L**: «القاموس» الذي يسمّي الخرائط ويعطي عناوينها ووحداتها.
- الفرق بين **الأصلي والمعدَّل** على مستوى الخريطة.

## الخام والفيزيائي

الخلية في الملف عدد صحيح (مثلًا 16 بت من 0 إلى 65535). المعنى الفيزيائي يأتي من معادلة خطية:

**القيمة الفيزيائية = الخام × المعامل + الإزاحة**

فإذا كان المعامل 0.1 والوحدة `%` فالخام 735 يعني 73.5 %. وعند التعديل نعكس المعادلة، **ونقرّب** لأن الملف لا يخزن كسورًا، **ونقصّ** إلى حدود النوع:

```python run
factor, offset = 0.1, 0.0
raw = [700, 735, 760, 802]


def to_phys(r):
    return r * factor + offset


def to_raw(p, lo=0, hi=65535):
    r = round((p - offset) / factor)
    return max(lo, min(hi, r))


print("physical:", [round(to_phys(r), 1) for r in raw])
plus = [to_raw(to_phys(r) * 1.05) for r in raw]           # +5 %
print("+5 % raw:", plus)
print("+5 % phys:", [round(to_phys(r), 1) for r in plus])
print("clamped:", to_raw(7000.0), "(the type stops at 65535)")
print("u8 clamp:", to_raw(30.0, 0, 255), "(an 8-bit cell stops at 255)")
```

```text output
physical: [70.0, 73.5, 76.0, 80.2]
+5 % raw: [735, 772, 798, 842]
+5 % phys: [73.5, 77.2, 79.8, 84.2]
clamped: 65535 (the type stops at 65535)
u8 clamp: 255 (an 8-bit cell stops at 255)
```

## محرر الخرائط

افتح الخريطة من لوحة الخرائط (منضدة العمل أو محرر الخرائط الكامل). ترى **جدولًا ملونًا كالخريطة الحرارية**، ورؤوسه قيم المحورين الفيزيائية. والقيم المعدلة تظهر **بخط عريض أحمر**، والقيمة الأصلية في التلميح.

| المفتاح / الزر | العمل |
|---|---|
| `+` / `-` | خطوة خام واحدة لكل الخلايا المحددة |
| `Page Up` / `Page Down` | عشر خطوات |
| `=` | تعيين قيمة |
| `%` | تغيير بنسبة مئوية |
| `T` / `2` / `3` | عرض الجدول / المنحنى 2D / السطح 3D (اسحب بالفأرة لتدويره) |
| `Ctrl+Z` / `Ctrl+Y` | تراجع / إعادة (التعديل على عدة خلايا خطوة واحدة) |
| نسخ / لصق | مع Excel مباشرة (يقبل الفاصلة العشرية) |

وفي المحرر الكامل أيضًا: **الاستيفاء** أفقيًا وعموديًا ومن الأركان، و**التنعيم** 3×3، وخصائص الخريطة (النوع والترتيب والمعامل والوحدة).

## A2L: قاموس الخرائط

مع البرامج التي لها توثيق (مشاريعك، أو rusEFI، أو وحدات تطوير) يوجد ملف **ASAP2** امتداده `.a2l`: نص يصف كل خريطة: اسمها، وعنوانها في ذاكرة المعالج، وشكل تخزينها (RECORD_LAYOUT)، ومعادلة التحويل (COMPU_METHOD)، ومحاورها. هذا ملف A2L صغير يصف خريطة 4×3 عند `0x80000020` (المقطع يبدأ عند `0x80000000`، فإزاحتها في الملف `0x20`)، ثم صورة 56 بايت فيها الخريطة نفسها:

```fwpy run
import struct

from radide.firmware.maps.a2l import parse_a2l
from radide.firmware.maps.model import read_array

A2L = """ASAP2_VERSION 1 71
/begin PROJECT DEMO ""
  /begin MODULE DEMO ""
    /begin MOD_COMMON "" BYTE_ORDER MSB_FIRST /end MOD_COMMON
    /begin MOD_PAR ""
      /begin MEMORY_SEGMENT FLASH "" DATA FLASH INTERN 0x80000000 0x38 -1 -1 -1 -1 -1 /end MEMORY_SEGMENT
    /end MOD_PAR
    /begin RECORD_LAYOUT RL_VAL_U16 FNC_VALUES 1 UWORD ROW_DIR DIRECT /end RECORD_LAYOUT
    /begin RECORD_LAYOUT RL_AX_U16 AXIS_PTS_X 1 UWORD INDEX_INCR DIRECT /end RECORD_LAYOUT
    /begin AXIS_PTS rpm "engine speed" 0x80000008 rpm RL_AX_U16 0 CM_1 4 0 65535 /end AXIS_PTS
    /begin AXIS_PTS load "load" 0x80000010 load RL_AX_U16 0 CM_1 3 0 65535 /end AXIS_PTS
    /begin CHARACTERISTIC KF_DEMO "demo map" MAP 0x80000020 RL_VAL_U16 0 CM_PCT 0 6553.5
      /begin AXIS_DESCR COM_AXIS rpm CM_1 4 0 65535 AXIS_PTS_REF rpm /end AXIS_DESCR
      /begin AXIS_DESCR COM_AXIS load CM_1 3 0 65535 AXIS_PTS_REF load /end AXIS_DESCR
    /end CHARACTERISTIC
    /begin COMPU_METHOD CM_PCT "" LINEAR "%.1" "%" COEFFS_LINEAR 0.1 0 /end COMPU_METHOD
    /begin COMPU_METHOD CM_1 "" LINEAR "%.0" "" COEFFS_LINEAR 1 0 /end COMPU_METHOD
  /end MODULE
/end PROJECT
"""

image = bytearray(0x38)
image[0x08:0x10] = struct.pack(">4H", 800, 1600, 2400, 3200)
image[0x10:0x16] = struct.pack(">3H", 20, 50, 80)
image[0x20:0x38] = struct.pack(">12H", *[700 + 25 * i for i in range(12)])

res = parse_a2l(A2L, bytes(image))
m = res.pack.maps[0]
print(f"{m.name}: {m.cols}x{m.rows} {m.dtype} {m.endian} at file offset 0x{m.address:X}, factor {m.factor} {m.unit}")
print("base from MEMORY_SEGMENT:", hex(res.pack.base_address))
z = read_array(image, m.address, m.cols * m.rows, m.dtype, m.endian) * m.factor + m.offset
print("first row (%):", [round(float(v), 1) for v in z[:4]])
```

```text output
KF_DEMO: 4x3 u16 be at file offset 0x20, factor 0.1 %
base from MEMORY_SEGMENT: 0x80000000
first row (%): [70.0, 72.5, 75.0, 77.5]
```

في RAD IDE: **Tools > Firmware & ECU > Calibration Maps > Open Binary with an A2L...**، أو افتح ملف `.a2l` (File > Open) ومنضدة العمل مفتوحة فتُستورد خرائطه إليها بأسمائها. يحوّل RAD IDE عناوين المعالج إلى إزاحات في الملف تلقائيًا من `MEMORY_SEGMENT` (أو من عنوان تحميل مشروعك). ويصدّر أيضًا حزمة خرائطك إلى A2L أو CSV.

> لمشاريع **rusEFI و Speeduino** المفتوحة المصدر: **Open rusEFI / Speeduino Tune (msq + ini)...** يقرأ ملف TunerStudio `.ini` (تعريف الجداول) وملف الضبط `.msq` ويعرض جداول VE والإشعال كخرائط.

## الأصلي والمعدَّل على مستوى الخريطة

مقارنة البايتات تقول «تغير 9 بايتات عند 0x9E7E». الأنفع: «في الخريطة KF_DEMO تغيرت 5 خلايا، أكبر تغيير +1.0 %». هكذا تعرض لوحة **Differences** ونافذة المقارنة (`Ctrl+D`) والتقرير:

```python run
import struct

ori = struct.pack(">12H", *[700 + 25 * i for i in range(12)])
mod = bytearray(ori)
struct.pack_into(">H", mod, 2 * 5, 700 + 25 * 5 + 10)      # الخلية (الصف 1، العمود 1)
struct.pack_into(">H", mod, 2 * 6, 700 + 25 * 6 + 10)

a = struct.unpack(">12H", ori)
b = struct.unpack(">12H", bytes(mod))
changed = [(i // 4, i % 4, (b[i] - a[i]) * 0.1) for i in range(12) if a[i] != b[i]]
print("bytes changed:", sum(x != y for x, y in zip(ori, mod)))
print(f"KF_DEMO: {len(changed)}/12 cells changed, largest {max(d for *_, d in changed):+.1f} %")
for r, c, d in changed:
    print(f"  row {r} col {c}: {d:+.1f} %")
```

```text output
bytes changed: 2
KF_DEMO: 2/12 cells changed, largest +1.0 %
  row 1 col 1: +1.0 %
  row 1 col 2: +1.0 %
```

## اختبر فهمك

```quiz
{"question": "خلية 8 بت بمعامل 0.5 وإزاحة 0، والقيمة 120.0. ماذا يحدث إذا طلبت 150.0؟", "choices": ["تُخزَّن 300", "تُقصّ إلى 255 خامًا = 127.5", "يتعطل البرنامج", "تُخزَّن 150"], "answer": 1, "explanation": "الخام = 150 / 0.5 = 300 أكبر من 255، فيُقص إلى حد النوع."}
```

```quiz
{"question": "ما فائدة ملف A2L؟", "choices": ["يصحح المجموع الاختباري", "يعطي أسماء الخرائط وعناوينها وأنواعها ووحداتها ومعادلات التحويل", "يشفّر الملف", "يفكك الكود"], "answer": 1, "explanation": "A2L هو القاموس الرسمي لخرائط المعايرة."}
```
