# Greeting Cards (multi-form + settings) - Fortran

Makes greeting cards. A modal Settings dialog chooses the user name, the language (English / Arabic), the font size and a formal style; the settings are saved to a file; an About box. In Arabic the texts are right-aligned.

## What it shows

* three forms: frmMain, frmSettings (shown with `ShowDialog`) and frmAbout
* "Form.Control" names to fill / read another form's controls; `Hide` to close a dialog
* a code module shared by the forms (the settings) and a settings file
* Unicode / Arabic text in labels, combo boxes and a multi-line text box; `TextAlign` Right for RTL
* a menu and buttons that do the same thing
* `app_settings.f90` (a module the forms `use`) keeps the settings in `settings.ini`. Note: the Fortran bridge client sends values on one line, so in F5 the card shows its first line only; the published native exe shows the whole card.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the Fortran code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with `rad_set` / `rad_get` / `rad_call` / `rad_arg` (module radgui)
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native Win32 exe (gfortran + radforms), about 470 KB, no Python

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs gfortran (MinGW-w64; found or downloaded by the IDE).
3. Try: F5, Settings..., type your name, choose العربية, OK; choose an occasion and press Make card; About....

## Publish

Build > Publish: a native Win32 exe (gfortran + radforms), about 470 KB, no Python. The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `app_settings.f90`
* `frmAbout.f90`
* `frmAbout.form`
* `frmAbout_designer.f90`
* `frmMain.f90`
* `frmMain.form`
* `frmMain_designer.f90`
* `frmSettings.f90`
* `frmSettings.form`
* `frmSettings_designer.f90`
* `project.radproj`

---

## بطاقات التهنئة (عدة نماذج + إعدادات) - Fortran

يصنع بطاقات تهنئة. حوار إعدادات مشروط (Modal) لاختيار الاسم واللغة (الإنجليزية / العربية) وحجم الخط وأسلوب رسمي؛ تُحفظ الإعدادات في ملف؛ ونافذة "حول". في العربية تُحاذى النصوص لليمين.

### ماذا يعرض

* ثلاثة نماذج: frmMain وfrmSettings (يُعرض بـ `ShowDialog`) وfrmAbout
* أسماء "Form.Control" لملء عناصر نموذج آخر وقراءتها؛ و`Hide` لإغلاق الحوار
* وحدة كود مشتركة بين النماذج (الإعدادات) وملف إعدادات
* نص يونيكود / عربي في التسميات والقوائم المنسدلة ومربع نص متعدد الأسطر؛ و`TextAlign` = Right للكتابة من اليمين
* قائمة وأزرار تؤدي نفس العمل
* `app_settings.f90` (وحدة تستخدمها النماذج) تحفظ الإعدادات في `settings.ini`. ملاحظة: عميل Fortran للجسر يرسل القيم في سطر واحد، لذا يظهر السطر الأول فقط من البطاقة عند F5، بينما يعرض ملف exe الأصلي المنشور البطاقة كاملة.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود Fortran يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر `rad_set` / `rad_get` / `rad_call` / `rad_arg` (module radgui)
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف exe أصلي لويندوز (gfortran + radforms) بحجم 470 ك.ب تقريبًا، بدون بايثون

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج gfortran (MinGW-w64؛ يجده الـ IDE أو ينزّله).
3. جرّب: F5 ثم الإعدادات...، اكتب اسمك واختر العربية ثم موافق؛ اختر مناسبة واضغط اصنع بطاقة؛ ثم حول....

### النشر

البناء > النشر: ملف exe أصلي لويندوز (gfortran + radforms) بحجم 470 ك.ب تقريبًا، بدون بايثون.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
