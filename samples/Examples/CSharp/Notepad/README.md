# Notepad - C#

A small text editor: open and save UTF-8 text files, cut / copy / paste with the Windows clipboard, find, find next and replace, insert the time, change the font and count words.

## What it shows

* MenuStrip with File / Edit / Format / Help menus (each item is a `<Item>_Click` handler)
* OpenFileDialog, SaveFileDialog and FontDialog (`ShowOpen` / `ShowSave` / `ShowFont`, then `FileName` / `FontName` / `FontSize`)
* a multi-line TextBox: the whole document goes through `Text` (line breaks included)
* `SelStart` / `SelLength` / `SelText` for Find, Replace, Cut / Copy / Paste and Time/Date
* a StatusBar, the window title (`*` when the text changed) and "discard the changes?" questions
* file I/O and error handling in the language itself
* Clipboard through P/Invoke to user32 (works in the console bridge program and in the WinForms exe).

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the C# code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed)

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs the .NET SDK (dotnet).
3. Try: F5, File > Open (any .txt), Edit > Find (`hello`), Edit > Replace, Format > Word count, File > Save As.

## Publish

Build > Publish: a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed). The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmMain.cs`
* `frmMain.form`
* `frmMain_designer.cs`
* `project.radproj`

---

## المفكرة - C#

محرر نصوص صغير: فتح وحفظ ملفات نصية UTF-8، قص ونسخ ولصق عبر حافظة ويندوز، بحث وبحث عن التالي واستبدال، إدراج الوقت، تغيير الخط وعدّ الكلمات.

### ماذا يعرض

* قائمة MenuStrip بقوائم ملف / تحرير / تنسيق / مساعدة (كل عنصر له معالج `<Item>_Click`)
* حوارات فتح وحفظ الملفات واختيار الخط (`ShowOpen` / `ShowSave` / `ShowFont`)
* مربع نص متعدد الأسطر: النص كله يمر عبر `Text` مع فواصل الأسطر
* `SelStart` / `SelLength` / `SelText` للبحث والاستبدال والقص والنسخ واللصق
* شريط الحالة، وعنوان النافذة (`*` عند تغيّر النص)، وسؤال "تجاهل التغييرات؟"
* قراءة وكتابة الملفات ومعالجة الأخطاء باللغة نفسها
* الحافظة عبر P/Invoke إلى user32 (تعمل في برنامج الجسر وفي ملف WinForms المنشور).

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود C# يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء)

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج .NET SDK (dotnet).
3. جرّب: F5 ثم ملف > فتح (أي ملف txt)، تحرير > بحث، تحرير > استبدال، تنسيق > عدد الكلمات، ملف > حفظ باسم.

### النشر

البناء > النشر: ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
