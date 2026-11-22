# QBasic Art Menu (DOS)

Boxed text-mode menu: times table, SCREEN 13 drawing (LINE, CIRCLE, PAINT, PSET), prime/divisor/binary facts, a calendar from DATE$.

## What it shows

* QBasic SUBs and a FUNCTION, DEFINT, CONST, SHARED arrays, SELECT CASE, INKEY$ with arrow keys
* SCREEN 13 graphics and back to text mode
* PRINT USING, INPUT, DATA / READ / RESTORE
* built by FreeBASIC -lang qb (its DOS version runs inside DOSBox-X without a window)

## Run / build / publish

F5 / Ctrl+F5 builds QBASICAR.EXE and runs it in DOSBox-X (the IDE downloads FreeBASIC and DOSBox-X on request). Keys 1-5, arrows, Enter, Esc.

Language / project type: `dos-qbasic`. Files: `MAIN.BAS`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (DOSBox-X without a window, keys typed with RADKEYS, output and screen read back).

---

<div dir="rtl">

## قائمة الرسم بـ QBasic (دوس)

قائمة نصية بإطار: جدول الضرب، رسم بـ SCREEN 13 (LINE وCIRCLE وPAINT وPSET)، حقائق الأعداد الأولية والقواسم والثنائي، وتقويم من DATE$.

### ماذا يعرض

* إجراءات SUB ودالة FUNCTION وDEFINT وCONST ومصفوفات SHARED وSELECT CASE وINKEY$ مع الأسهم
* رسومات SCREEN 13 ثم الرجوع للوضع النصي
* PRINT USING وINPUT وDATA/READ/RESTORE
* يبنيه FreeBASIC -lang qb (نسخة دوس تعمل داخل DOSBox-X بدون نافذة)

### التشغيل والبناء والنشر

F5 أو Ctrl+F5 يبني QBASICAR.EXE ويشغله في DOSBox-X (تنزّل البيئة FreeBASIC وDOSBox-X عند الطلب). المفاتيح 1-5 والأسهم و Enter و Esc.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
