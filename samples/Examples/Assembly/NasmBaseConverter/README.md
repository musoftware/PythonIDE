# Number Base Converter (NASM console)

x64 console tool: reads numbers and prints decimal, hex, octal, binary (own SHL loop), the number of 1 bits and power-of-two test.

## What it shows

* a console program: `main` called by the C runtime, `printf` / `scanf` / `fflush`
* bit loops: `shl` + carry flag, counting 1 bits, `x & (x-1)` power-of-two test
* callee-saved registers (RBX, R12) and stack alignment
* F5 debugging with gdb (the IDE adds DWARF line info for NASM)

## Run / build / publish

Ctrl+F5 runs it - type numbers in the Program Input bar, q to quit. F5 debugs (breakpoints by line). Build > Publish: a 60 KB exe without Python.

Language / project type: `asm-nasm`. Files: `main.asm`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (the form driven in the IDE's bridge host / the console program fed through stdin).

---

<div dir="rtl">

## محول أنظمة العد (NASM - طرفية)

أداة طرفية x64: تقرأ أعدادا وتطبعها بالعشري والست عشري والثماني والثنائي (حلقة SHL خاصة) مع عدد البتات 1 واختبار قوى العدد 2.

### ماذا يعرض

* برنامج طرفية: الدالة `main` تستدعيها مكتبة C، مع `printf` و`scanf` و`fflush`
* حلقات البتات: `shl` وعلم الحمل، عدّ البتات 1، واختبار `x & (x-1)`
* المسجلات المحفوظة (RBX و R12) ومحاذاة المكدس
* التنقيح بـ F5 عبر gdb (البيئة تضيف معلومات الأسطر DWARF لـ NASM)

### التشغيل والبناء والنشر

Ctrl+F5 يشغله - اكتب الأعداد في شريط إدخال البرنامج و q للخروج. F5 للتنقيح (نقاط توقف بالسطر). Build > Publish: ملف تنفيذي 60 كيلوبايت بدون بايثون.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
