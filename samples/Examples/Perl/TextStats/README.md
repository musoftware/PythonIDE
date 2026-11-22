# Text Statistics - Perl (RAD IDE example)

Counts words, lines and characters, lists the most frequent words and searches the text with Perl regular expressions.

## What it shows
- Menus (File: Open / Clear / Exit, Help: About) and an OpenFileDialog
- A multi-line TextBox read and written with the bridge's `ESC` commands (multi-line text)
- DataGridView rows (`AddItem` with one argument per cell), ListBox, StatusBar
- Regular expressions with an invalid-pattern MsgBox
- KeyPress: Enter in the pattern box runs Find
- A second code module (`TextTools.pl`) called from the form

## RAD IDE features
- A **Perl GUI Bridge** project (`perl-bridge`): the IDE draws the forms (designer + `Form*.form`), your Perl code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Perl; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`TextTools.pl`).
- F5 run, Build > Publish.

## Files
- `Form1.pl` - event handlers
- `TextTools.pl` - text helpers (word counts, regex search, multi-line helpers)

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Perl 5 (perl.exe on PATH, e.g. Git for Windows / Strawberry Perl).
3. Press **Analyze**: the counts and the top-10 words appear.
4. Type a pattern such as `\bPerl\b` and press Enter.
5. File > Open... loads a .txt file.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Perl when one is available, otherwise the GUI Bridge host is bundled with the Perl files.

---

<div dir="rtl">

# إحصاءات النص - Perl (مثال من RAD IDE)

يعدّ الكلمات والأسطر والحروف، ويعرض أكثر الكلمات تكرارًا، ويبحث في النص بالتعابير النمطية في بيرل.

## ماذا يعرض
- قوائم (ملف: فتح / مسح / خروج، مساعدة: حول) ومربع حوار فتح ملف
- مربع نص متعدد الأسطر يُقرأ ويُكتب بأوامر `ESC` في الجسر
- صفوف DataGridView وقائمة ListBox وشريط الحالة
- تعابير نمطية مع رسالة عند النمط غير الصحيح
- حدث KeyPress: زر Enter في مربع النمط يبحث
- وحدة كود ثانية (`TextTools.pl`) يستدعيها النموذج

## مزايا بيئة التطوير المستخدمة
- مشروع **Perl GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Perl يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج بيرل 5 (perl.exe في PATH، مثل Git for Windows أو Strawberry Perl).
3. اضغط **Analyze** لتظهر الإحصاءات وأكثر 10 كلمات.
4. اكتب نمطًا مثل `\bPerl\b` واضغط Enter.
5. ملف > فتح لتحميل ملف نصي.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
