# Bubble Sort on the 8086 Emulator

A 16-bit .COM program for the IDE's own 8086 emulator: asks for the order, sorts signed words with early exit and prints every pass.

## What it shows

* INT 21h services 01h / 02h / 09h / 4Ch
* signed compares (`jle` / `jge`), `loop`, swapping words in memory, decimal printing with `div`
* F5 = the 8086 Emulator dock: step F10/F11, registers with flags, memory at `numbers`, Step Back

## Run / build / publish

Nothing to install. F5 steps it in the emulator dock; Ctrl+F5 runs it at full speed (press A or D).

Language / project type: `emu8086`. Files: `main.asm`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (RAD IDE's 8086 emulator, headless).

---

<div dir="rtl">

## الترتيب الفقاعي على محاكي 8086

برنامج COM بـ 16 بت لمحاكي 8086 المدمج في البيئة: يسأل عن اتجاه الترتيب ويرتب كلمات بإشارة مع الخروج المبكر ويطبع كل مرور.

### ماذا يعرض

* خدمات INT 21h رقم 01h و02h و09h و4Ch
* مقارنات بإشارة (`jle` و`jge`) و`loop` وتبديل الكلمات في الذاكرة وطباعة الأرقام العشرية بـ `div`
* F5 يفتح لوحة محاكي 8086: خطوة بـ F10/F11، المسجلات والأعلام، الذاكرة عند `numbers`، والرجوع خطوة

### التشغيل والبناء والنشر

لا شيء للتثبيت. F5 ينفذه خطوة بخطوة في لوحة المحاكي؛ Ctrl+F5 يشغله بأقصى سرعة (اضغط A أو D).

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
