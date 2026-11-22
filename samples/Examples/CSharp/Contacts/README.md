# Contacts - C#

An address book: a list of contacts with a details panel; add, edit, delete and search, saved to a database file after every change.

## What it shows

* a ListBox filled from the records (`Clear`, `AddItem`, `ListIndex`, `SelectedIndexChanged`)
* a GroupBox with TextBoxes, a ComboBox (group) and a CheckBox (favourite)
* CRUD: New / Save (insert or update) / Delete (with a confirmation) and Search (Enter in the search box)
* validation (name required, e-mail needs @) and a StatusBar
* sample records are created on the first run
* Storage: `contacts.xml` with LINQ to XML (`XDocument`); LINQ queries for search and sorting.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the C# code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed)

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs the .NET SDK (dotnet).
3. Try: F5, New, type a name / phone / e-mail, Save; type part of a name in Search and press Enter; Delete.

## Publish

Build > Publish: a native WinForms exe (no Python); the default variant is a self-contained .NET exe (about 64 MB, needs nothing installed). The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `frmContacts.cs`
* `frmContacts.form`
* `frmContacts_designer.cs`
* `project.radproj`

---

## جهات الاتصال - C#

دفتر عناوين: قائمة جهات اتصال مع لوحة تفاصيل؛ إضافة وتعديل وحذف وبحث، وتُحفظ في ملف قاعدة بيانات بعد كل تغيير.

### ماذا يعرض

* قائمة ListBox تُملأ من السجلات (`Clear` و`AddItem` و`ListIndex` وحدث `SelectedIndexChanged`)
* إطار GroupBox فيه مربعات نص وقائمة منسدلة (المجموعة) ومربع اختيار (مفضّل)
* إضافة وحفظ (إدراج أو تعديل) وحذف (بتأكيد) وبحث (Enter في مربع البحث)
* التحقق من المدخلات (الاسم مطلوب، والبريد يحتاج @) وشريط الحالة
* تُنشأ سجلات تجريبية في أول تشغيل
* التخزين: `contacts.xml` عبر LINQ to XML ‏(`XDocument`)، واستعلامات LINQ للبحث والترتيب.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود C# يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر the generated control fields (`txtDoc.Text`, `lstContacts.AddItem(...)`) and `MsgBox` / `InputBox`
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء)

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج .NET SDK (dotnet).
3. جرّب: F5 ثم جديد، اكتب اسمًا ورقمًا وبريدًا ثم حفظ؛ اكتب جزءًا من اسم في البحث واضغط Enter؛ ثم حذف.

### النشر

البناء > النشر: ملف WinForms أصلي (بدون بايثون)؛ الافتراضي ملف .NET مستقل (حوالي 64 م.ب ولا يحتاج تثبيت شيء).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
