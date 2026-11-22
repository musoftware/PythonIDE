# Calculator - Rust

A pocket calculator with + - * /, square root, percent, sign, backspace and a memory (MC / MR / M+), usable with the mouse or the keyboard.

## What it shows

* 24 buttons whose `Click` handlers share a few routines
* keyboard input: the form's `KeyPress` gets the keys of all its controls (digits, + - * /, Enter, Esc, Backspace)
* error handling: division by zero, square root of a negative number and overflow show an error instead of crashing
* number <-> text conversion and formatting
* the calculator logic is kept apart from the GUI code
* Engine methods return `Result<(), String>`; state in a `thread_local!` `RefCell`.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the Rust code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with `set` / `get` / `call` / `msgbox` / `input` / `event_arg` (module radgui)
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native exe (cargo + radforms), about 320-380 KB, no Python

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs Rust (cargo, from rustup).
3. Try: F5, click 1 2 + 3 =, then type 7 * 6 Enter on the keyboard, then 1 / 0 =.

## Publish

Build > Publish: a native exe (cargo + radforms), about 320-380 KB, no Python. The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmCalc.form`
* `frmCalc.rs`
* `frmCalc_designer.rs`
* `project.radproj`

---

## الآلة الحاسبة - Rust

آلة حاسبة جيب: + - * /، الجذر التربيعي، النسبة المئوية، تغيير الإشارة، مسح آخر رقم وذاكرة (MC / MR / M+)، تعمل بالماوس أو بلوحة المفاتيح.

### ماذا يعرض

* 24 زرًا تتشارك معالجات `Click` في دوال قليلة
* إدخال من لوحة المفاتيح: حدث `KeyPress` للنموذج يستقبل مفاتيح كل عناصره (أرقام، + - * /، Enter، Esc، Backspace)
* معالجة الأخطاء: القسمة على صفر وجذر العدد السالب والفيض تُظهر رسالة خطأ بدل توقف البرنامج
* تحويل الأرقام إلى نص وتنسيقها
* منطق الآلة الحاسبة منفصل عن كود الواجهة
* دوال المحرك تُعيد `Result<(), String>`، والحالة في `RefCell` داخل `thread_local!`.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود Rust يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر `set` / `get` / `call` / `msgbox` / `input` / `event_arg` (module radgui)
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف exe أصلي (cargo + radforms) بحجم 320-380 ك.ب تقريبًا، بدون بايثون

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج Rust (cargo من rustup).
3. جرّب: F5 ثم اضغط 1 2 + 3 = ثم اكتب 7 * 6 Enter من لوحة المفاتيح، ثم 1 / 0 =.

### النشر

البناء > النشر: ملف exe أصلي (cargo + radforms) بحجم 320-380 ك.ب تقريبًا، بدون بايثون.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
