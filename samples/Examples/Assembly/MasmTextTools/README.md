# Text & Array Tools (MASM ml64)

ml64 console program: string length, reverse, upper case, vowels, words; array sum/min/max/average and insertion sort.

## What it shows

* MASM `proc`/`endp`, local labels, `extern ... : proc`
* byte loops (`movzx`, `stosb`-style copies), `rep movsq`, scaled indexing `[rcx + r8*8]`
* insertion sort on 64-bit signed numbers
* Visual Studio's ml64 + link (found by the IDE through vcvars64)

## Run / build / publish

Needs Visual Studio (C++ workload). Ctrl+F5, type a line of text. Build > Publish: a small exe without Python.

Language / project type: `asm-masm`. Files: `main.asm`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the form driven in the IDE's bridge host / the console program fed through stdin).

---

<div dir="rtl">

## أدوات النصوص والمصفوفات (MASM ml64)

برنامج طرفية بـ ml64: طول النص وعكسه وتحويله لحروف كبيرة وعدّ الحروف المتحركة والكلمات؛ ومجموع المصفوفة وأصغر وأكبر قيمة والمتوسط والترتيب بالإدراج.

### ماذا يعرض

* MASM بـ `proc`/`endp` والتسميات المحلية و`extern ... : proc`
* حلقات البايتات (`movzx` ونسخ البايتات) و`rep movsq` والفهرسة المضاعفة `[rcx + r8*8]`
* الترتيب بالإدراج لأعداد 64 بت بإشارة
* ml64 و link من Visual Studio (تجدهما البيئة عبر vcvars64)

### التشغيل والبناء والنشر

يحتاج Visual Studio (حزمة C++). Ctrl+F5 واكتب سطرا من النص. Build > Publish: ملف تنفيذي صغير بدون بايثون.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
