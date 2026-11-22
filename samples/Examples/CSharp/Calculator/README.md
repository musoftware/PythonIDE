# Calculator - C#

A pocket calculator with + - * /, square root, percent, sign, backspace and a memory (MC / MR / M+), usable with the mouse or the keyboard.

## What it shows

* 24 buttons whose `Click` handlers share a few routines
* keyboard input: the form's `KeyPress` gets the keys of all its controls (digits, + - * /, Enter, Esc, Backspace)
* error handling: division by zero, square root of a negative number and overflow show an error instead of crashing
* number <-> text conversion and formatting
* the calculator logic is kept apart from the GUI code
* `decimal` arithmetic (0.1 + 0.2 = 0.3); `DivideByZeroException` / `OverflowException` handling.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the C# code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed)

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs the .NET SDK (dotnet).
3. Try: F5, click 1 2 + 3 =, then type 7 * 6 Enter on the keyboard, then 1 / 0 =.

## Publish

Build > Publish: a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed). The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmCalc.cs`
* `frmCalc.form`
* `frmCalc_designer.cs`
* `project.radproj`

---

## الآلة الحاسبة - C#

آلة حاسبة جيب: + - * /، الجذر التربيعي، النسبة المئوية، تغيير الإشارة، مسح آخر رقم وذاكرة (MC / MR / M+)، تعمل بالماوس أو بلوحة المفاتيح.

### ماذا يعرض

* 24 زرًا تتشارك معالجات `Click` في دوال قليلة
* إدخال من لوحة المفاتيح: حدث `KeyPress` للنموذج يستقبل مفاتيح كل عناصره (أرقام، + - * /، Enter، Esc، Backspace)
* معالجة الأخطاء: القسمة على صفر وجذر العدد السالب والفيض تُظهر رسالة خطأ بدل توقف البرنامج
* تحويل الأرقام إلى نص وتنسيقها
* منطق الآلة الحاسبة منفصل عن كود الواجهة
* حساب بنوع `decimal` ‏(0.1 + 0.2 = 0.3)، ومعالجة `DivideByZeroException` و`OverflowException`.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود C# يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء)

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج .NET SDK (dotnet).
3. جرّب: F5 ثم اضغط 1 2 + 3 = ثم اكتب 7 * 6 Enter من لوحة المفاتيح، ثم 1 / 0 =.

### النشر

البناء > النشر: ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
