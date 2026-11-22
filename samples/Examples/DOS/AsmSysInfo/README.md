# System Info .COM (16-bit assembly, DOS)

Key-driven .COM menu asking DOS and the BIOS: DOS version, date with day name, time, memory/equipment, and an upper-case echo of a typed line.

## What it shows

* `.model tiny`, `org 100h`, JWasm `-bin` (MASM syntax)
* INT 21h 30h / 2Ah / 2Ch / 0Ah / 08h, INT 11h and INT 12h
* number printing with `div`, table lookup of day names
* F5 can step it in RAD IDE's 8086 emulator too

## Run / build / publish

Ctrl+F5 builds ASMSYSIN.COM (903 bytes) and runs it in DOSBox-X. Keys 1-5, Q quits.

Language / project type: `dos-asm`. Files: `MAIN.ASM`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (DOSBox-X without a window, keys typed with RADKEYS, output and screen read back).

---

<div dir="rtl">

## معلومات النظام .COM (تجميع 16 بت، دوس)

قائمة .COM بالمفاتيح تسأل دوس والبايوس: إصدار دوس، التاريخ مع اسم اليوم، الوقت، الذاكرة والأجهزة، وإعادة سطر مكتوب بحروف كبيرة.

### ماذا يعرض

* `.model tiny` و`org 100h` و JWasm `-bin` (صيغة MASM)
* INT 21h رقم 30h و2Ah و2Ch و0Ah و08h، و INT 11h و INT 12h
* طباعة الأرقام بـ `div` والبحث في جدول أسماء الأيام
* F5 يمكنه تنفيذه خطوة بخطوة في محاكي 8086 أيضا

### التشغيل والبناء والنشر

Ctrl+F5 يبني ASMSYSIN.COM (903 بايت) ويشغله في DOSBox-X. المفاتيح 1-5 و Q للخروج.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
