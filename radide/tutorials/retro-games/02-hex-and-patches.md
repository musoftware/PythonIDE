# الدرس 2: محرر السادس عشر والرقع IPS و BPS

**في هذا الدرس:**

- محرر السادس عشر (Hex Editor) في RAD IDE: الكتابة فوق البايتات، والإدراج، والبحث بالأنماط، ومفتش البيانات.
- **مشروع تعديل ROM**: نسخة عمل، والأصل لا يُلمس أبدًا.
- صيغة **IPS** من الداخل: تكتب برنامجًا يطبّقها ويُنشئها.
- صيغة **BPS** ولماذا هي الأفضل اليوم (CRC32 وأي حجم).

## محرر السادس عشر

افتح ملفًا ثنائيًا (File > Open). ترى ثلاثة أعمدة: **الإزاحة** (Offset)، و**البايتات** بالسادس عشر، و**النص**. أهم المفاتيح:

| المفتاح | العمل |
|---|---|
| اكتب `0`-`9` و`A`-`F` | تكتب فوق البايت (نصف بايت في كل ضغطة)؛ كل بايت خطوة تراجع واحدة |
| `Insert` | يبدّل بين الكتابة فوق (OVR) والإدراج (INS) |
| `Ctrl+F` | شريط البحث: سادس عشر مع `??` لأي بايت مثل `A9 ?? 8D`، أو نص (ومعه جدول حروف `.tbl`) |
| `Ctrl+G` | انتقل إلى إزاحة (سادس عشر، أو عشري، أو `+100` نسبيًا) |
| `Ctrl+F2` | علامة مرجعية |
| `Ctrl+Z` / `Ctrl+Y` | تراجع / إعادة |

وعلى اليمين **مفتش البيانات** (Data Inspector): قيمة البايتات عند المؤشر كعدد 8 و 16 و 32 بت (Little / Big Endian)، وكسور، وBCD، وتعليمة 6502 التي تبدأ عند المؤشر، وعنوانها في ذاكرة المعالج. ومن **Edit > Copy As** تنسخ التحديد بصيغة `db` أو `.byte` أو مصفوفة C أو Python.

## مشروع تعديل ROM: الأصل في أمان

**File > New Project > Retro > ROM Hacking Project** (أو القالب **Demo ROM** الذي فيه ROM أصلية صغيرة للتجربة):

1. **Set Source ROM...**: تختار الـ ROM (نسختك الشخصية). تُنسخ إلى `rom/` وتُفتح **للقراءة فقط**، ويُحفظ مجموعها CRC32 في `rom.json`.
2. **Edit Working Copy**: يكتب الـ ROM مع كل الرقع المفعّلة في `work/` ويفتحها في محرر السادس عشر. عدّل وحفظ.
3. **Capture Edits as Patch**: الفرق بين نسخة العمل والأصل يصبح رقعة جديدة في `patches/` (اختر IPS أو BPS).
4. **Build** (أو `F5`): يطبّق الرقع المفعّلة بالترتيب على الأصل ويكتب `build/<الاسم>_patched.nes`، ثم `F5` يشغّلها في المحاكي.

تستطيع تعطيل رقعة بمربع الاختيار، أو تغيير الترتيب، أو كتابة ملاحظة لها. ومن **Tools > Retro > ROM Workbench** تجد أيضًا **Create Patch** و**Apply Patch** لأي ملفين.

## صيغة IPS من الداخل

IPS (1993) أبسط صيغة رقع:

```text
"PATCH"                       5 بايتات في البداية
ثم سجلات، كل سجل:
  الإزاحة   3 بايتات (Big Endian)
  الطول     2 بايت
  البيانات  <الطول> بايت
  (إذا كان الطول 0: سجل RLE = طول 2 بايت ثم بايت واحد يتكرر)
"EOF"                         3 بايتات في النهاية
```

هذا برنامج يطبّق رقعة IPS على بيانات في الذاكرة:

```python run
def apply_ips(rom: bytes, patch: bytes) -> bytes:
    if patch[:5] != b"PATCH":
        raise ValueError("ليست رقعة IPS")
    out = bytearray(rom)
    i = 5
    while patch[i:i + 3] != b"EOF":
        offset = int.from_bytes(patch[i:i + 3], "big")
        size = int.from_bytes(patch[i + 3:i + 5], "big")
        i += 5
        if size:                                  # سجل عادي
            data = patch[i:i + size]
            i += size
        else:                                     # سجل RLE
            count = int.from_bytes(patch[i:i + 2], "big")
            data = patch[i + 2:i + 3] * count
            i += 3
        if offset + len(data) > len(out):         # الرقعة تستطيع تكبير الملف
            out.extend(b"\0" * (offset + len(data) - len(out)))
        out[offset:offset + len(data)] = data
    return bytes(out)


rom = b"HELLO WORLD....."
patch = (b"PATCH"
         + (6).to_bytes(3, "big") + (5).to_bytes(2, "big") + b"RADIO"   # اكتب RADIO عند 6
         + (11).to_bytes(3, "big") + (0).to_bytes(2, "big")             # RLE عند 11
         + (5).to_bytes(2, "big") + b"!"                                #   5 مرات "!"
         + b"EOF")
print(apply_ips(rom, patch).decode())
print(len(patch), "bytes in the patch")
```

```text output
HELLO RADIO!!!!!
26 bytes in the patch
```

وإنشاء رقعة يعني مقارنة الملفين وجمع البايتات المختلفة في سجلات:

```python run
def create_ips(old: bytes, new: bytes) -> bytes:
    out = bytearray(b"PATCH")
    i = 0
    while i < len(new):
        if i < len(old) and old[i] == new[i]:
            i += 1
            continue
        start = i                                 # بداية منطقة مختلفة
        while i < len(new) and (i >= len(old) or old[i] != new[i]) and i - start < 0xFFFF:
            i += 1
        out += start.to_bytes(3, "big") + (i - start).to_bytes(2, "big") + new[start:i]
    return bytes(out + b"EOF")


old = b"PRESS START TO PLAY"
new = b"PRESS FIRE  TO PLAY"
p = create_ips(old, new)
print(p)
```

```text output
b'PATCH\x00\x00\x06\x00\x05FIRE EOF'
```

لاحظ أن الرقعة 18 بايتًا فقط وفيها كلمة `FIRE ` وحدها، لا اللعبة.

### تمرين

عدّل `create_ips` لتطبع عدد السجلات وعدد البايتات المتغيرة. جرّب على `old = b"AAAAAAAA"` و`new = b"ABAAAABA"`.

```python exercise
def create_ips(old: bytes, new: bytes):
    out = bytearray(b"PATCH")
    i = 0
    # اكتب الحلقة هنا وعُدّ السجلات والبايتات
    return bytes(out + b"EOF")


create_ips(b"AAAAAAAA", b"ABAAAABA")
```

```python solution
def create_ips(old: bytes, new: bytes):
    out = bytearray(b"PATCH")
    i = records = changed = 0
    while i < len(new):
        if i < len(old) and old[i] == new[i]:
            i += 1
            continue
        start = i
        while i < len(new) and (i >= len(old) or old[i] != new[i]):
            i += 1
        out += start.to_bytes(3, "big") + (i - start).to_bytes(2, "big") + new[start:i]
        records += 1
        changed += i - start
    print("records:", records, "changed bytes:", changed)
    return bytes(out + b"EOF")


create_ips(b"AAAAAAAA", b"ABAAAABA")
```

```text output
records: 2 changed bytes: 2
```

## عيوب IPS ولماذا BPS

- IPS لا تتحقق من الملف الأصلي: إن طبّقتها على نسخة مختلفة من اللعبة أفسدتها بصمت.
- الإزاحة 3 بايتات: الحد الأقصى 16 MB، ولا تعرف تصغير الملف.

صيغة **BPS** (2012) تحل ذلك: فيها **CRC32** للملف الأصلي والناتج والرقعة، وتصف الملف الجديد بأوامر: «انسخ من الأصل» و«انسخ من الهدف» و«بيانات جديدة»، فتصغر الرقعة جدًا حتى لو تحركت أجزاء من الملف. RAD IDE يطبّق وينشئ IPS و UPS و BPS، وعند التطبيق يرفض BPS إذا لم يطابق CRC32 الأصل.

```python run
import zlib

rom = b"HELLO WORLD....."
fixed = b"HELLO RADIO!!!!!"
print(f"source CRC32 = {zlib.crc32(rom):08X}")
print(f"target CRC32 = {zlib.crc32(fixed):08X}")
other = b"HELLO world....."
print("same source?", zlib.crc32(other) == zlib.crc32(rom))
```

```text output
source CRC32 = 4126DA86
target CRC32 = 2BAEEC7C
same source? False
```

## اختبر فهمك

```quiz
{"question": "في سجل IPS، ماذا يعني أن الطول 0؟", "choices": ["نهاية الرقعة", "سجل RLE: طول التكرار ثم بايت واحد يُكرَّر", "خطأ في الرقعة", "حذف بايتات"], "answer": 1, "explanation": "الطول 0 يعني RLE: بايتان للعدد ثم البايت المكرر."}
```

```quiz
{"question": "لماذا يفضَّل BPS على IPS لنشر ترجمة لعبة؟", "choices": ["لأنه أقدم", "لأنه يتحقق بـ CRC32 أن الـ ROM الأصلية هي النسخة الصحيحة ويدعم أي حجم", "لأنه يضم الـ ROM كاملة", "لأنه نص عادي"], "answer": 1, "explanation": "CRC32 يمنع تطبيق الرقعة على نسخة خاطئة، ولا حد للحجم."}
```
