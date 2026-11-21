# الدرس 8: المشروع الكامل: نسخ وتقارير ورقعة

**في هذا الدرس تجمع كل ما سبق في مشروع واحد:**

1. مشروع ECU من ملف (خام أو HEX)، والأصل محفوظ للقراءة فقط.
2. التحليل: المعالج وعنوان التحميل.
3. الخرائط: البحث، والتسمية من A2L، والتعديل في الجدول و 3D.
4. الفروق بين الأصلي والمعدَّل.
5. المجاميع الاختبارية: تحقق ثم تصحيح.
6. **Build** إلى `.bin` أو `.hex` أو `.s19`، مع **تقرير التعديل**.
7. **النسخ** (Versions) والمقارنة بينها، و**رقعة** IPS أو BPS.

## 1. أنشئ المشروع

**File > New Project > Firmware > ECU / Firmware Project** ثم **Project > ECU Project > Set Original...**، أو مباشرة **Tools > Firmware & ECU > New ECU Project...** واختر الملف. للتجربة بلا ملف: **New ECU Project (Demo Firmware)** أو أنشئ ملفًا من **Create Synthetic Test Firmware...**.

يظهر **تنبيه السلامة مرة واحدة** (الدرس 1). ثم ترى في **Solution Explorer** عقدة **ECU Project**: الأصل (للقراءة فقط)، ونسخة العمل، والنسخ، وكتل المجاميع، والناتج. وتُفتح **منضدة العمل**:

| المكان | ما فيه |
|---|---|
| يسار | شجرة المشروع: الأصل، نسخة العمل، النسخ، مجلدات الخرائط، ملفات تعريف المجاميع، الناتج |
| الوسط | تبويبات: البداية، Hex، محرر الخرائط، 2D، التفكيك، التحليل (و EEPROM لملفات EEPROM) |
| يمين | الخصائص: عنوان الخريطة وأبعادها ونوعها ومعاملها ووحدتها (قابلة للتعديل) |
| أسفل | الخرائط المحتملة، الفروق، تقرير المجاميع، المخرجات |

> **ملف HEX أو S-record أصلي** يُفتح مسطّحًا عند عنوانه (مثلًا `0x08000000`)، ويُبنى افتراضيًا بالصيغة نفسها وعند العنوان نفسه.

## 2-5. التحليل والخرائط والمجاميع

| الخطوة | في منضدة العمل |
|---|---|
| المعالج والعنوان | **Analyze** (`Ctrl+Shift+A`)، ثم تبويب Disassembly |
| البحث عن الخرائط | **Find Maps** (`Ctrl+M`) ثم Add to Map Pack |
| أسماء من A2L | **More > Import A2L**، أو افتح ملف `.a2l` |
| التعديل | افتح الخريطة؛ `+` و`PgUp` و`%` و`=`؛ ثم `3` للسطح ثلاثي الأبعاد |
| الفروق | **Compare** (`Ctrl+D`): لوحة Differences تذكر اسم الخريطة لكل مدى |
| المجاميع | **More > Load Profile** أو **Find Checksums**، ثم **Verify** (`Ctrl+Shift+V`) و**Correct** |

## 6. البناء والتقرير

**Build** (`F7` في منضدة العمل، أو **Project > ECU Project > Build ECU Project**):

1. يتحقق من بصمة الأصل (يرفض إن تغير).
2. يأخذ نسخة العمل ويصحح كل كتل المجاميع.
3. يكتب الناتج بالصيغة المختارة في **Build Settings...**: خام `.bin`، أو Intel HEX، أو S-record، أو «مثل الأصل»، مع **عنوان الإزاحة 0** (مثلًا `0x80000000`).
4. يكتب بجانبه **تقرير التعديل**: الأصل وبصمته، والخرائط التي تغيرت وكم خلية وأكبر تغيير بالوحدة الفيزيائية، والكتل التي أعيد حسابها (القديم والجديد)، وتنبيه السلامة. ومن **Export Modification Report...** تحصل عليه صفحة HTML أيضًا.

## 7. النسخ والرقعة

- **Save Version** في منضدة العمل (أو **Project > ECU Project > Versions...**): لقطة باسم وملاحظة. انقر مرتين على نسخة في الشجرة لتقارنها بنسخة العمل، أو اختر نسختين في نافذة Versions وقارن بينهما. **Restore** يحفظ نسخة العمل الحالية أولًا.
- **Export Patch (IPS / BPS)...**: رقعة بين الأصل والناتج (بعد تصحيح المجاميع). تحتوي تعديلاتك فقط، لا البرنامج. و**Import Patch...** يطبّق رقعة على الأصل ويجعلها نسخة العمل.

## المشروع كله بالكود

هذه الكتلة تفعل الخطوات نفسها بمكتبة RAD IDE على الملف الاصطناعي (64 KB، فيه 3 خرائط و 3 كتل مجاميع):

```fwpy run
import os
import struct
from pathlib import Path

from radide.firmware.project.model import new_project
from radide.firmware.project.synth import MAP16_AT, demo_blocks, demo_maps, image

Path("stock.bin").write_bytes(image())
ep = new_project("DemoEcu", "DemoEcu", original="stock.bin")       # الأصل -> original/ للقراءة فقط
ep.checksums = demo_blocks()
ep.maps = demo_maps()
ep.save()
print("original read-only:", not os.access(ep.original_path, os.W_OK))

work = bytearray(ep.work_bytes())                                   # عدّل خلية: الصف 3، العمود 4
cell = MAP16_AT + 64 + 2 * (3 * 16 + 4)
struct.pack_into(">H", work, cell, struct.unpack_from(">H", work, cell)[0] + 15)
ep.write_work(bytes(work))
ep.snapshot("stage 1", "one cell +1.5")

d = ep.diff("original", "work")
print(d.summary())
for m in d.maps:
    print(" ", m.line())

ep.set_container("hex")
ep.image_base = 0x80000000
ep.save()
r = ep.build(log=lambda s: None)
print("output:", Path(r.output).name, "| recalculated:", [b.name for b in r.recalculated])
print("report:", r.report_path.name)
p = ep.export_patch("DemoEcu/build/stage1.ips")
print("patch:", p.name, p.stat().st_size, "bytes")
print("versions:", [v.id + " " + v.name for v in ep.versions])
```

```text output
original read-only: True
1 byte(s) changed in 1 range(s), 1 map(s)
  Demo map 16x16 (map @ 0x8140): 1/256 cells changed, largest change +1.5 units
output: stock_mod.hex | recalculated: ['Calibration CRC32']
report: stock_mod.report.txt
patch: stage1.ips 23 bytes
versions: ['v001 stage 1']
```

لاحظ أن الرقعة صغيرة جدًا: فيها الخلية المعدلة والمجموع الجديد فقط. ولاحظ أن المجموعين الآخرين لم يتغيرا لأن التعديل في منطقة المعايرة وحدها.

## تمرين: مقارنة نسختين

اكتب برنامجًا (Python عادي) يقارن نسختين من صورة ويطبع لكل مدى متغير: البداية والطول. استخدم الصورتين في الكود. المتوقع ثلاثة مديات.

```python exercise
v1 = bytes(64)
v2 = bytearray(v1)
v2[4] = 1
v2[10:13] = b"\x05\x06\x07"
v2[60] = 9


def changed_ranges(a: bytes, b: bytes):
    # أرجع قائمة (البداية، الطول) لكل مجموعة بايتات متتالية مختلفة
    return []


for start, length in changed_ranges(v1, bytes(v2)):
    print(f"0x{start:02X}: {length} byte(s)")
```

```python solution
v1 = bytes(64)
v2 = bytearray(v1)
v2[4] = 1
v2[10:13] = b"\x05\x06\x07"
v2[60] = 9


def changed_ranges(a: bytes, b: bytes):
    out, i = [], 0
    while i < len(a):
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        while i < len(a) and a[i] != b[i]:
            i += 1
        out.append((start, i - start))
    return out


for start, length in changed_ranges(v1, bytes(v2)):
    print(f"0x{start:02X}: {length} byte(s)")
```

```text output
0x04: 1 byte(s)
0x0A: 3 byte(s)
0x3C: 1 byte(s)
```

## قائمة المراجعة قبل استخدام أي ملف معدَّل

- [ ] الأصل محفوظ وبصمته لم تتغير (Build يتحقق).
- [ ] كل تعديل في خريطة تعرف معناها، وفي حدود القانون، ولوحدة تملكها أو مخوَّل بإصلاحها.
- [ ] المجاميع الاختبارية صحيحة (Verify بلا أخطاء).
- [ ] تقرير التعديل محفوظ مع المشروع، والنسخ لها أسماء وملاحظات.
- [ ] تنشر **رقعة** لا ملفًا كاملًا، ولا تنشر ملفات الشركات أبدًا.

## مبروك!

أنهيت الدورة. تعلمت ما بداخل ملف `.bin` لوحدة التحكم، والصيغ والعناوين، وتخمين المعالج، والتفكيك و Ghidra، والخرائط ووحداتها و A2L، والمجاميع الاختبارية، ومشروعًا كاملًا بنسخ وتقارير. للتوسع: جرّب ملف **rusEFI** المفتوح المصدر في عارض التحليل، واقرأ `docs/FIRMWARE.md` في مجلد RAD IDE.

## اختبر فهمك

```quiz
{"question": "ماذا يفعل Build في مشروع ECU قبل كتابة الملف الناتج؟", "choices": ["يحذف الأصل", "يتحقق من بصمة الأصل ويصحح كتل المجاميع ثم يكتب بالصيغة المختارة مع تقرير", "يرسل الملف إلى السيارة", "يضغط الملف"], "answer": 1, "explanation": "البناء: تحقق من الأصل، ثم تصحيح المجاميع، ثم الكتابة، ثم التقرير."}
```

```quiz
{"question": "لماذا تنشر رقعة IPS أو BPS بدل الملف المعدَّل كاملًا؟", "choices": ["لأنها أكبر", "لأنها تحتوي تعديلاتك فقط لا برنامج الشركة المحمي، ولا تفيد إلا من يملك الأصل", "لأنها مشفرة", "لا فرق"], "answer": 1, "explanation": "الرقعة فرق فقط، فلا تنشر بها برنامجًا محميًا."}
```
