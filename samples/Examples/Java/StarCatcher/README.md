# Star Catcher - Java

A small arcade game: move the paddle with the arrow keys or the mouse, catch the falling stars and dodge the red rocks; the game speeds up and keeps a best score.

## What it shows

* a Timer game loop (30 ms) that moves controls with `Left` / `Top`
* `KeyDown` / `KeyUp` on the form (it sees the keys of its controls) and `MouseMove` on a Panel
* rectangle collision, score / lives, levels, pause (P) and game over
* controls inside a Panel (coordinates relative to the panel)
* a best score saved to a file

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the Java code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with the generated control fields (`txtDoc.setText(...)`) and `msgbox` / `input` / `set` / `call`
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native Swing exe with a trimmed Java runtime (jlink + jpackage; the launcher is about 460 KB), no Python

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs a JDK 17+ (javac).
3. Try: F5, Start, then Left / Right (or move the mouse over the field); P pauses.

## Publish

Build > Publish: a native Swing exe with a trimmed Java runtime (jlink + jpackage; the launcher is about 460 KB), no Python. The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmGame.form`
* `frmGame.java`
* `frmGame_designer.java`
* `project.radproj`

---

## صائد النجوم - Java

لعبة أركيد صغيرة: حرّك المضرب بالأسهم أو بالماوس، التقط النجوم الساقطة وتجنّب الصخور الحمراء؛ تزداد السرعة ويُحفظ أفضل رقم.

### ماذا يعرض

* حلقة لعب بمؤقت (30 ملي ثانية) تحرّك العناصر عبر `Left` و`Top`
* حدثا `KeyDown` و`KeyUp` على النموذج (يستقبل مفاتيح عناصره) و`MouseMove` على Panel
* اكتشاف التصادم بالمستطيلات، النقاط والأرواح، المستويات، الإيقاف المؤقت (P) ونهاية اللعبة
* عناصر داخل Panel (الإحداثيات نسبة إلى الـ Panel)
* أفضل نتيجة تُحفظ في ملف

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود Java يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر the generated control fields (`txtDoc.setText(...)`) and `msgbox` / `input` / `set` / `call`
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف Swing أصلي مع بيئة Java مصغّرة (jlink + jpackage؛ المشغّل حوالي 460 ك.ب)، بدون بايثون

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج JDK 17 أو أحدث (javac).
3. جرّب: F5 ثم ابدأ، ثم الأسهم يمين ويسار (أو حرّك الماوس فوق الملعب)؛ P للإيقاف المؤقت.

### النشر

البناء > النشر: ملف Swing أصلي مع بيئة Java مصغّرة (jlink + jpackage؛ المشغّل حوالي 460 ك.ب)، بدون بايثون.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
