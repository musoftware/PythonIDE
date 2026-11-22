# Coffee Order Form (DOS Text-Mode Designer)

A DOS forms app drawn in the Text-Mode Designer (Pascal target): text box, option buttons, check boxes, list, progress bar, menus, message boxes.

## What it shows

* `Main.tform` designed in the Text-Mode Designer; `MAIN.PAS` is generated, the event code lives in the USER CODE regions (kept on regeneration)
* TuiGetText / TuiGetValue / TuiSetValue / TuiAddItem / TuiClearList / TuiMsgBox
* Alt+letter hot keys, Tab order, F10 menus, mouse
* Free Pascal 16-bit DOS build, run in DOSBox-X

## Run / build / publish

Open Main.tform (Text-Mode Designer) and press F5 (Build & Run in DOSBox-X). Type a name, Alt+R Large, Alt+I milk, Alt+O orders.

Language / project type: `dos-tuiforms`. Files: `MAIN.PAS`, `Main.tform`, `project.radproj`.

Tested by `samples/Tests/Examples/test_examples_scripting.py --group lowlevel` (`ex_lowlevel.py`): open, build, run (DOSBox-X without a window, keys typed with RADKEYS, output and screen read back).

---

<div dir="rtl">

## نموذج طلب القهوة (مصمم الوضع النصي لدوس)

تطبيق نماذج لدوس مرسوم في مصمم الوضع النصي (هدف باسكال): مربع نص وأزرار خيارات ومربعات اختيار وقائمة وشريط تقدم وقوائم ورسائل.

### ماذا يعرض

* `Main.tform` مصمم في مصمم الوضع النصي؛ و`MAIN.PAS` يُولَّد، وكود الأحداث في مناطق USER CODE (تبقى عند إعادة التوليد)
* TuiGetText و TuiGetValue و TuiSetValue و TuiAddItem و TuiClearList و TuiMsgBox
* مفاتيح Alt مع الحرف وترتيب Tab وقوائم F10 والفأرة
* بناء Free Pascal لدوس 16 بت والتشغيل في DOSBox-X

### التشغيل والبناء والنشر

افتح Main.tform (مصمم الوضع النصي) واضغط F5 (بناء وتشغيل في DOSBox-X). اكتب اسما ثم Alt+R للحجم الكبير و Alt+I للحليب و Alt+O للطلب.

</div>

(c) 2026 Musoftware - https://musoftwares.com - MIT License
