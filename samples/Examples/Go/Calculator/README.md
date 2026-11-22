# Calculator - Go

A pocket calculator with + - * /, square root, percent, sign, backspace and a memory (MC / MR / M+), usable with the mouse or the keyboard.

## What it shows

* 24 buttons whose `Click` handlers share a few routines
* keyboard input: the form's `KeyPress` gets the keys of all its controls (digits, + - * /, Enter, Esc, Backspace)
* error handling: division by zero, square root of a negative number and overflow show an error instead of crashing
* number <-> text conversion and formatting
* the calculator logic is kept apart from the GUI code
* Errors are values (`error`) returned by the engine methods.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the Go code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with `Set` / `Get` / `Call` / `MsgBox` / `Input` (radlib.go)
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native exe (go build + radforms), about 1.8-2.9 MB, no Python

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs Go (go.exe; found or downloaded by the IDE).
3. Try: F5, click 1 2 + 3 =, then type 7 * 6 Enter on the keyboard, then 1 / 0 =.

## Publish

Build > Publish: a native exe (go build + radforms), about 1.8-2.9 MB, no Python. The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmCalc.form`
* `frmCalc.go`
* `frmCalc_designer.go`
* `project.radproj`

---

## الآلة الحاسبة - Go

آلة حاسبة جيب: + - * /، الجذر التربيعي، النسبة المئوية، تغيير الإشارة، مسح آخر رقم وذاكرة (MC / MR / M+)، تعمل بالماوس أو بلوحة المفاتيح.

### ماذا يعرض

* 24 زرًا تتشارك معالجات `Click` في دوال قليلة
* إدخال من لوحة المفاتيح: حدث `KeyPress` للنموذج يستقبل مفاتيح كل عناصره (أرقام، + - * /، Enter، Esc، Backspace)
* معالجة الأخطاء: القسمة على صفر وجذر العدد السالب والفيض تُظهر رسالة خطأ بدل توقف البرنامج
* تحويل الأرقام إلى نص وتنسيقها
* منطق الآلة الحاسبة منفصل عن كود الواجهة
* الأخطاء قيم (`error`) تُعيدها دوال المحرك.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود Go يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر `Set` / `Get` / `Call` / `MsgBox` / `Input` (radlib.go)
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف exe أصلي (go build + radforms) بحجم 1.8-2.9 م.ب تقريبًا، بدون بايثون

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج Go (يجده الـ IDE أو ينزّله).
3. جرّب: F5 ثم اضغط 1 2 + 3 = ثم اكتب 7 * 6 Enter من لوحة المفاتيح، ثم 1 / 0 =.

### النشر

البناء > النشر: ملف exe أصلي (go build + radforms) بحجم 1.8-2.9 م.ب تقريبًا، بدون بايثون.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
