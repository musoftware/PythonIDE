# الدرس 2: صيغ الملفات: الخام و Intel HEX و S-record

**في هذا الدرس:**

- الفرق بين **الملف الخام** (`.bin`) والملفات النصية التي تحمل **العناوين** (`.hex` و`.s19`).
- سجلات **Intel HEX** من الداخل، ومجموعها الاختباري.
- سجلات **Motorola S-record** (S1 و S2 و S3).
- تقسيم ملف إلى نصفين **زوجي/فردي** (شريحتا EPROM) ودمجهما.
- **محوّل الصيغ** في RAD IDE.

## الملف الخام لا يعرف عنوانه

الملف الخام (`.bin` و`.ori`) هو صورة الفلاش بايتًا ببايت. البايت رقم 0 في الملف قد يكون في العنوان `0x08000000` داخل المعالج (ARM من ST) أو `0x80000000` (TriCore) أو `0x00000000` (PowerPC). **الملف لا يقول ذلك**؛ هذا ما نسميه **عنوان التحميل** (Base address) وموضوع الدرس القادم.

أما **Intel HEX** و**S-record** فنص، كل سطر فيه **سجل**: العنوان والبيانات ومجموع اختباري للسطر. لذلك يستطيع الملف أن يحتوي أجزاء متباعدة (فلاش داخلي وخارجي) بفراغات بينها.

## Intel HEX من الداخل

كل سطر يبدأ بـ `:` ثم أزواج سادس عشر:

```text
:LL AAAA TT DD...DD CC
 LL   عدد بايتات البيانات
 AAAA العنوان (16 بت)
 TT   النوع: 00 بيانات، 01 نهاية الملف، 04 «العنوان الأعلى» (أعلى 16 بت)، 05 عنوان البدء
 CC   المجموع: (256 - مجموع كل البايتات قبله) & FF
```

هذا برنامج يقرأ ملف HEX صغيرًا (مكتوب داخل البرنامج) ويبني منه الذاكرة:

```python run
hex_text = """:020000040800F2
:100000000000012009020008090200080902000896
:0400100048454C4CC7
:00000001FF"""

memory = {}
upper = 0
for line in hex_text.splitlines():
    rec = bytes.fromhex(line[1:])
    count, addr, kind = rec[0], (rec[1] << 8) | rec[2], rec[3]
    data = rec[4:4 + count]
    ok = sum(rec) & 0xFF == 0                   # مجموع كل البايتات مع CC = 0
    if kind == 0x04:
        upper = int.from_bytes(data, "big") << 16
    elif kind == 0x00:
        for i, b in enumerate(data):
            memory[upper + addr + i] = b
    print(f"type {kind:02X} at {addr:04X}: {count:2} bytes, checksum {'OK' if ok else 'BAD'}")

start = min(memory)
print(f"first address: 0x{start:08X}, {len(memory)} bytes")
print("text at the end:", bytes(memory[a] for a in range(start + 16, start + 20)).decode())
```

```text output
type 04 at 0000:  2 bytes, checksum OK
type 00 at 0000: 16 bytes, checksum OK
type 00 at 0010:  4 bytes, checksum OK
type 01 at 0000:  0 bytes, checksum OK
first address: 0x08000000, 20 bytes
text at the end: HELL
```

لاحظ السجل `04`: قيمته `0800` فصار كل عنوان بعده `0x0800xxxx`. هكذا يصل HEX إلى عناوين 32 بت رغم أن حقل العنوان 16 بت فقط.

### تمرين

اكتب الدالة `record(addr, data)` التي تُنشئ سطر بيانات (النوع 00) مع مجموعه الاختباري، ثم اطبع سطرًا للبايتات `48 45 4C 4C` عند العنوان `0x0010`. يجب أن يطابق السطر الثالث في المثال السابق.

```python exercise
def record(addr: int, data: bytes) -> str:
    rec = bytes([len(data), addr >> 8, addr & 0xFF, 0x00]) + data
    # احسب المجموع الاختباري وأضفه، ثم أرجع ":" + السادس عشر بحروف كبيرة
    return ""


print(record(0x0010, b"HELL"))
```

```python solution
def record(addr: int, data: bytes) -> str:
    rec = bytes([len(data), addr >> 8, addr & 0xFF, 0x00]) + data
    rec += bytes([(-sum(rec)) & 0xFF])
    return ":" + rec.hex().upper()


print(record(0x0010, b"HELL"))
```

```text output
:0400100048454C4CC7
```

## Motorola S-record

الفكرة نفسها بحروف مختلفة: `S1` عنوان 16 بت، و`S2` عنوان 24 بت، و`S3` عنوان 32 بت، و`S0` رأس (اسم الملف)، و`S7`/`S8`/`S9` عنوان البدء. والمجموع هنا **متمم الواحد** (Ones' complement) لمجموع البايتات بعد النوع:

```python run
def srec_line(kind: str, addr: int, data: bytes) -> str:
    alen = {"1": 2, "2": 3, "3": 4}[kind]
    body = bytes([alen + len(data) + 1]) + addr.to_bytes(alen, "big") + data
    return f"S{kind}" + (body + bytes([~sum(body) & 0xFF])).hex().upper()


print(srec_line("3", 0x80000000, b"\x00\x01\x02\x03"))
line = srec_line("2", 0x010000, b"RADIDE")
print(line)
raw = bytes.fromhex(line[2:])
print("valid?", (sum(raw) & 0xFF) == 0xFF)
```

```text output
S309800000000001020370
S20A0100005241444944454B
valid? True
```

## الشرائح الزوجية والفردية

في الوحدات القديمة (معالجات 16 بت مثل 68000 و C167) كان البرنامج على **شريحتي EPROM**: واحدة فيها البايتات الزوجية وأخرى الفردية. عند قراءتهما تحصل على ملفين، ويجب **دمجهما بالتناوب** (Interleave) قبل التحليل:

```python run
image = bytes(range(16))
even = image[0::2]                 # البايتات 0، 2، 4 ...
odd = image[1::2]                  # البايتات 1، 3، 5 ...
print("even:", even.hex(" "))
print("odd: ", odd.hex(" "))

merged = bytearray(len(even) + len(odd))
merged[0::2] = even
merged[1::2] = odd
print("merged = image?", bytes(merged) == image)

swapped = bytearray(image)
swapped[0::2], swapped[1::2] = image[1::2], image[0::2]      # تبديل بايتات كل كلمة 16 بت
print("byte-swapped:", bytes(swapped[:8]).hex(" "))
```

```text output
even: 00 02 04 06 08 0a 0c 0e
odd:  01 03 05 07 09 0b 0d 0f
merged = image? True
byte-swapped: 01 00 03 02 05 04 07 06
```

## المحوّل في RAD IDE

**Tools > Firmware & ECU > Firmware Converter (HEX / S-record / ELF / split / merge)...** يفعل كل ما سبق: يقرأ `.bin` و`.hex` و`.s19` و`.elf`، ويكتب أي صيغة منها، ويقسم إلى زوجي/فردي (أو أربع شرائح)، ويبدّل ترتيب البايتات 16 و 32 بت، ويدمج ملفات عند عناوين مختلفة مع تحذير من التداخل. وفي سطر الأوامر: `python -m radide.firmware.analysis convert in.bin out.hex --base 0x08000000`.

وهذه الأدوات نفسها مكتبة Python داخل RAD IDE (`radide.firmware.formats`). الكتلة التالية من نوع `fwpy`: كود يستخدم مكتبة RAD IDE، يفحصه مدقق الدورة (وتستطيع تشغيله من مجلد RAD IDE بـ `python`):

```fwpy run
from radide.firmware.formats import dumps, load_bytes
from radide.firmware.formats.memmap import MemoryMap

flat = bytes(range(64))
mm = MemoryMap.from_bytes(flat, base=0x08000000)
hex_text = dumps(mm, "ihex").decode()
s19_text = dumps(mm, "srec").decode()
print(hex_text.splitlines()[0])
print(s19_text.splitlines()[1][:20] + "...")

back = load_bytes(hex_text.encode(), "x.hex")
print(f"HEX back: 0x{back.min_address:08X}, {back.size} bytes, same = {back.to_flat() == flat}")
back2 = load_bytes(s19_text.encode(), "x.s19")
print(f"S19 back: 0x{back2.min_address:08X}, same = {back2.to_flat() == flat}")
```

```text output
:020000040800F2
S3250800000000010203...
HEX back: 0x08000000, 64 bytes, same = True
S19 back: 0x08000000, same = True
```

## اختبر فهمك

```quiz
{"question": "ملف .bin لا يحتوي عناوين. ماذا يحتوي ملف Intel HEX زيادة عليه؟", "choices": ["تشفيرًا للبيانات", "عنوان كل سجل ومجموعًا اختباريًا لكل سطر", "أسماء الخرائط", "لا شيء، هما متطابقان"], "answer": 1, "explanation": "كل سطر HEX يحمل عنوانه ومجموعه، والسجل 04 يعطي أعلى 16 بت من العنوان."}
```

```quiz
{"question": "لديك ملفان من شريحتي EPROM (زوجي وفردي). ماذا تفعل قبل التحليل؟", "choices": ["ألصق الثاني بعد الأول", "أدمجهما بالتناوب: بايت من الزوجي ثم بايت من الفردي", "أحلل كل واحد وحده", "أحذف الفردي"], "answer": 1, "explanation": "البرنامج الحقيقي هو البايتات بالتناوب (Interleave)."}
```
