# Greeting Cards (multi-form + settings) - C#

Makes greeting cards. A modal Settings dialog chooses the user name, the language (English / Arabic), the font size and a formal style; the settings are saved to a file; an About box. In Arabic the texts are right-aligned.

## What it shows

* three forms: frmMain, frmSettings (shown with `ShowDialog`) and frmAbout
* "Form.Control" names to fill / read another form's controls; `Hide` to close a dialog
* a code module shared by the forms (the settings) and a settings file
* Unicode / Arabic text in labels, combo boxes and a multi-line text box; `TextAlign` Right for RTL
* a menu and buttons that do the same thing
* `AppSettings.cs` (a static class module) keeps the settings in `settings.ini`.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the C# code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed)

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs the .NET SDK (dotnet).
3. Try: F5, Settings..., type your name, choose العربية, OK; choose an occasion and press Make card; About....

## Publish

Build > Publish: a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed). The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `AppSettings.cs`
* `frmAbout.cs`
* `frmAbout.form`
* `frmAbout_designer.cs`
* `frmMain.cs`
* `frmMain.form`
* `frmMain_designer.cs`
* `frmSettings.cs`
* `frmSettings.form`
* `frmSettings_designer.cs`
* `project.radproj`

---

## بطاقات التهنئة (عدة نماذج + إعدادات) - C#

يصنع بطاقات تهنئة. حوار إعدادات مشروط (Modal) لاختيار الاسم واللغة (الإنجليزية / العربية) وحجم الخط وأسلوب رسمي؛ تُحفظ الإعدادات في ملف؛ ونافذة "حول". في العربية تُحاذى النصوص لليمين.

### ماذا يعرض

* ثلاثة نماذج: frmMain وfrmSettings (يُعرض بـ `ShowDialog`) وfrmAbout
* أسماء "Form.Control" لملء عناصر نموذج آخر وقراءتها؛ و`Hide` لإغلاق الحوار
* وحدة كود مشتركة بين النماذج (الإعدادات) وملف إعدادات
* نص يونيكود / عربي في التسميات والقوائم المنسدلة ومربع نص متعدد الأسطر؛ و`TextAlign` = Right للكتابة من اليمين
* قائمة وأزرار تؤدي نفس العمل
* `AppSettings.cs` (وحدة فئة ثابتة) تحفظ الإعدادات في `settings.ini`.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود C# يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء)

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج .NET SDK (dotnet).
3. جرّب: F5 ثم الإعدادات...، اكتب اسمك واختر العربية ثم موافق؛ اختر مناسبة واضغط اصنع بطاقة؛ ثم حول....

### النشر

البناء > النشر: ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
