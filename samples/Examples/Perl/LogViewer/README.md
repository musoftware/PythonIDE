# Log Viewer - Perl (RAD IDE example)

Follows a growing log file like `tail -f`, with a text filter, a level filter and live counters.

## What it shows
- A Timer that reads only the lines appended since the last tick
- TextBox `TextChanged` and ComboBox `SelectedIndexChanged` filters
- CheckBox to pause/resume the Timer
- InputBox (Tools > Go to line)
- Counting with Perl hashes; StatusBar

## RAD IDE features
- A **Perl GUI Bridge** project (`perl-bridge`): the IDE draws the forms (designer + `Form*.form`), your Perl code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Perl; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`sample.log`).
- F5 run, Build > Publish.

## Files
- `Form1.pl` - event handlers
- `sample.log` - the log file that is followed

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Perl 5 (perl.exe on PATH, e.g. Git for Windows / Strawberry Perl).
3. Tools > Write test lines appends three lines - they appear within a second.
4. Type `payment` in Filter, or choose ERROR in the level box.
5. Append to sample.log from any editor: the viewer follows it.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Perl when one is available, otherwise the GUI Bridge host is bundled with the Perl files.

---

<div dir="rtl">

# عارض السجلات - Perl (مثال من RAD IDE)

يتابع ملف سجل يكبر باستمرار مثل `tail -f` مع تصفية بالنص وبالمستوى وعدّادات مباشرة.

## ماذا يعرض
- مؤقت يقرأ الأسطر الجديدة فقط في كل نبضة
- تصفية بحدث TextChanged لمربع النص وSelectedIndexChanged للقائمة المنسدلة
- مربع اختيار لإيقاف المؤقت وتشغيله
- InputBox (أدوات > الذهاب إلى سطر)
- العد بجداول التجزئة في بيرل وشريط الحالة

## مزايا بيئة التطوير المستخدمة
- مشروع **Perl GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Perl يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج بيرل 5 (perl.exe في PATH، مثل Git for Windows أو Strawberry Perl).
3. أدوات > كتابة أسطر تجريبية تضيف ثلاثة أسطر تظهر خلال ثانية.
4. اكتب `payment` في التصفية أو اختر ERROR.
5. أضف أسطرًا إلى sample.log من أي محرر وسيتابعها العارض.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
