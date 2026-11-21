# الدرس 4: التفكيك والمراجع و Ghidra

**في هذا الدرس:**

- **التفكيك** (Disassembly): تحويل البايتات إلى تعليمات المعالج.
- كيف تقرأ تعليمة Thumb بنفسك.
- **المراجع** (Cross references): أي تعليمة تقرأ جدولًا معينًا؟ هذا ما يؤكد أن الجدول خريطة حقيقية.
- **Ghidra**: أداة التحليل المفتوحة المصدر، وكيف يشغّلها RAD IDE بلا واجهة ليعطيك الدوال وكود C مفكوكًا.

## من البايتات إلى التعليمات

المعالج لا يعرف إلا أرقامًا. التعليمة `push {r4-r7, lr}` في نمط **Thumb** (معالجات Cortex-M) هي الكلمة 16 بت `0xB5F0`: البتات العليا `1011010` تعني PUSH، والبت 8 يعني «ومعها LR»، والبايت الأدنى قائمة السجلات r0..r7:

```python run
word = 0xB5F0          # البايتات في الملف: F0 B5 (Little Endian)

if word >> 9 == 0b1011010:
    regs = [f"r{i}" for i in range(8) if word & (1 << i)]
    if word & 0x100:
        regs.append("lr")
    print("push {" + ", ".join(regs) + "}")

ret = 0xBDF0           # POP مع PC = رجوع من الدالة
if ret >> 9 == 0b1011110:
    regs = [f"r{i}" for i in range(8) if ret & (1 << i)] + (["pc"] if ret & 0x100 else [])
    print("pop {" + ", ".join(regs) + "}")
```

```text output
push {r4, r5, r6, r7, lr}
pop {r4, r5, r6, r7, pc}
```

## كيف يجد الكود جداوله: الحمل النسبي لـ PC

في ARM يكتب المُترجم عنوان الجدول في **مستودع ثوابت** (Literal pool) بعد الدالة، ثم يقرؤه بتعليمة `ldr r0, [pc, #imm]`. العنوان الفعلي = (PC + 4 مقربًا إلى مضاعف 4) + الإزاحة. من يعرف هذا يتبع الكود إلى الجدول:

```python run
import struct

base = 0x08000000
flash = bytearray(b"\x00" * 0x40)
flash[0x10:0x12] = struct.pack("<H", 0x4803)          # ldr r0, [pc, #12]  (imm8 = 3 -> 3*4)
flash[0x20:0x24] = struct.pack("<I", 0x08009E40)      # مستودع الثوابت: عنوان جدول

pc = base + 0x10
ins = struct.unpack_from("<H", flash, 0x10)[0]
rd, imm = (ins >> 8) & 7, (ins & 0xFF) * 4
literal = ((pc + 4) & ~3) + imm
value = struct.unpack_from("<I", flash, literal - base)[0]
print(f"0x{pc:08X}: ldr r{rd}, [pc, #{imm}]")
print(f"literal at 0x{literal:08X} -> r{rd} = 0x{value:08X}")
print(f"table offset in the file: 0x{value - base:X}")
```

```text output
0x08000010: ldr r0, [pc, #12]
literal at 0x08000020 -> r0 = 0x08009E40
table offset in the file: 0x9E40
```

## المفكك في RAD IDE

في عارض التحليل (**Analyze Firmware File...**) تبويب **Disassembly**: قائمة بالتسميات وأهداف القفز والمراجع للبيانات - مستودعات ARM، وأزواج `lis`/`addi` في PowerPC، و`movh.a`/`lea` في TriCore، والحمل النسبي في SH-2. يستخدم مكتبة **Capstone** (ARM و Thumb و PowerPC و TriCore و 68K و SH و HC12 و MIPS). وفي منضدة العمل تبويب **Disassembly** يفكك من موضع المؤشر.

الأهم: **References to**. اكتب عنوان جدول فترى كل تعليمة تقرؤه. الجدول الذي يقرؤه الكود معايرة حقيقية؛ أما نمط أرقام لا يقرؤه أحد فقد يكون صدفة.

```fwpy run
from radide.firmware.analysis import disasm
from radide.firmware.analysis.synth import make_image
from radide.firmware.formats.memmap import MemoryMap

img = make_image("arm-thumb", seed=11)
mm = MemoryMap.from_bytes(img.bytes(), img.base)
for ln in disasm.disassemble(mm, "arm-thumb", img.entry, 0x40, max_lines=5):
    print(f"{ln.address:08X}  {ln.mnemonic:6} {ln.ops}")

idx = disasm.build_xrefs(mm, "arm-thumb", [(img.base + 0x200, img.base + img.code_end)])
table = next(t for t in img.tables if t.kind == "map")
hits = idx.to(table.address)
print(f"{idx.instructions} instructions indexed")
print(f"references to {table.name} at 0x{table.address:08X}: {len(hits)}")
print("all known readers found:", set(img.xrefs[table.address]) <= {src for src, _ in hits})
```

```text output
08000200  push   {r4, r5, r6, r7, lr}
08000202  str    r1, [r5, #8]
08000204  bl     #0x8000464
08000208  lsls   r6, r7, #0x12
0800020A  bl     #0x800474c
18402 instructions indexed
references to map0 at 0x08009E38: 60
all known readers found: True
```

## Ghidra: تحليل أعمق وكود C

**Ghidra** أداة تحليل مفتوحة المصدر (Apache 2.0) من وكالة الأمن القومي الأمريكية، تعرف عشرات المعالجات (منها V850 و 8051 و PowerPC VLE التي لا يفككها Capstone)، وتعيد بناء **الدوال** و**كود C تقريبي** (Decompiler).

- في عارض التحليل تبويب **Ghidra** > **Analyze in Ghidra**: يشغّل RAD IDE نسخة Ghidra المثبتة **بلا واجهة** (Headless) باللغة المكتشفة وعنوان التحميل، وينشئ دوالًا عند مداخل جدول المتجهات، ثم يعرض قائمة الدوال والكود المفكوك للقراءة فقط. يستغرق ثوانيَ لملف 64 KB، ودقائق لملف 1 MB مثل rusEFI.
- في منضدة العمل **More > Open in Ghidra** يفتح واجهة Ghidra نفسها ويكتب لك إعدادات الاستيراد (اللغة والعنوان).
- إن لم يكن Ghidra مثبتًا ينزّله RAD IDE من صفحته الرسمية على GitHub إلى `%LOCALAPPDATA%\RADIDE\tools` بلا صلاحيات مدير (يحتاج Java JDK 21 أو أحدث).

> **نصيحة:** حدد المعالج والعنوان في تبويب Overview أولًا. Ghidra بعنوان خاطئ يعطي دوالًا بلا مراجع.

## اختبر فهمك

```quiz
{"question": "وجدت نمط أرقام يشبه خريطة في الملف. ما أقوى دليل على أنه خريطة معايرة فعلًا؟", "choices": ["أن أرقامه كبيرة", "أن تعليمات في الكود تقرأ عنوانه (References to)", "أنه في آخر الملف", "أن لونه في محرر السادس عشر أزرق"], "answer": 1, "explanation": "الجدول الذي يقرؤه الكود معايرة حقيقية؛ المراجع هي الدليل."}
```

```quiz
{"question": "متى تحتاج Ghidra بدل المفكك المدمج؟", "choices": ["أبدًا", "لمعالج لا يدعمه Capstone مثل V850 أو 8051، أو عندما تريد الدوال وكود C مفكوكًا", "لتعديل الخرائط", "لتصحيح المجموع الاختباري"], "answer": 1, "explanation": "Ghidra يعرف معالجات أكثر ويعيد بناء الدوال و C."}
```
