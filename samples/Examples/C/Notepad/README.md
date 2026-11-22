# Notepad - C

A small text editor: open and save UTF-8 text files, cut / copy / paste with the Windows clipboard, find, find next and replace, insert the time, change the font and count words.

## What it shows

* MenuStrip with File / Edit / Format / Help menus (each item is a `<Item>_Click` handler)
* OpenFileDialog, SaveFileDialog and FontDialog (`ShowOpen` / `ShowSave` / `ShowFont`, then `FileName` / `FontName` / `FontSize`)
* a multi-line TextBox: the whole document goes through `Text` (line breaks included)
* `SelStart` / `SelLength` / `SelText` for Find, Replace, Cut / Copy / Paste and Time/Date
* a StatusBar, the window title (`*` when the text changed) and "discard the changes?" questions
* file I/O and error handling in the language itself
* Clipboard: Win32 `OpenClipboard` / `SetClipboardData` (CF_UNICODETEXT) with UTF-8 <-> UTF-16 conversion.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the C code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with `rad_set` / `rad_get` / `rad_call` (radgui.h)
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native Win32 exe (MinGW-w64 + radforms), about 70-85 KB, no Python, no DLLs

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs gcc (MinGW-w64; the IDE finds or downloads it into %LOCALAPPDATA%\RADIDE\toolchains).
3. Try: F5, File > Open (any .txt), Edit > Find (`hello`), Edit > Replace, Format > Word count, File > Save As.

## Publish

Build > Publish: a native Win32 exe (MinGW-w64 + radforms), about 70-85 KB, no Python, no DLLs. The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmMain.c`
* `frmMain.form`
* `frmMain_designer.c`
* `project.radproj`

---

## المفكرة - C

محرر نصوص صغير: فتح وحفظ ملفات نصية UTF-8، قص ونسخ ولصق عبر حافظة ويندوز، بحث وبحث عن التالي واستبدال، إدراج الوقت، تغيير الخط وعدّ الكلمات.

### ماذا يعرض

* قائمة MenuStrip بقوائم ملف / تحرير / تنسيق / مساعدة (كل عنصر له معالج `<Item>_Click`)
* حوارات فتح وحفظ الملفات واختيار الخط (`ShowOpen` / `ShowSave` / `ShowFont`)
* مربع نص متعدد الأسطر: النص كله يمر عبر `Text` مع فواصل الأسطر
* `SelStart` / `SelLength` / `SelText` للبحث والاستبدال والقص والنسخ واللصق
* شريط الحالة، وعنوان النافذة (`*` عند تغيّر النص)، وسؤال "تجاهل التغييرات؟"
* قراءة وكتابة الملفات ومعالجة الأخطاء باللغة نفسها
* الحافظة: دوال Win32 مثل `OpenClipboard` و`SetClipboardData` مع تحويل UTF-8 إلى UTF-16.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود C يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر `rad_set` / `rad_get` / `rad_call` (radgui.h)
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف exe أصلي لويندوز (MinGW-w64 + radforms) بحجم 70-85 ك.ب تقريبًا، بدون بايثون وبدون DLL

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج gcc (MinGW-w64؛ يجده الـ IDE أو ينزّله في %LOCALAPPDATA%\RADIDE\toolchains).
3. جرّب: F5 ثم ملف > فتح (أي ملف txt)، تحرير > بحث، تحرير > استبدال، تنسيق > عدد الكلمات، ملف > حفظ باسم.

### النشر

البناء > النشر: ملف exe أصلي لويندوز (MinGW-w64 + radforms) بحجم 70-85 ك.ب تقريبًا، بدون بايثون وبدون DLL.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
