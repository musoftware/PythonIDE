# Contacts - C++

An address book: a list of contacts with a details panel; add, edit, delete and search, saved to a database file after every change.

## What it shows

* a ListBox filled from the records (`Clear`, `AddItem`, `ListIndex`, `SelectedIndexChanged`)
* a GroupBox with TextBoxes, a ComboBox (group) and a CheckBox (favourite)
* CRUD: New / Save (insert or update) / Delete (with a confirmation) and Search (Enter in the search box)
* validation (name required, e-mail needs @) and a StatusBar
* sample records are created on the first run
* A multi-language project: the data layer is the Python module `ContactsDb.py` (SQLite, `contacts.db`); the C++ form calls it through RAD Hub with `rad::invoke("ContactsDb.list_contacts", {...})`. The IDE starts RAD Hub for every Run.

## IDE features

* GUI Bridge: the IDE draws the form(s) from the .form files; the C++ code only handles the events (handlers named `<Control>_<Event>`) and talks to the controls with `rad::set` / `rad::get` / `rad::call` (radgui.hpp)
* the form designer: open the project and double-click a form (every control is in the .form file)
* Build > Publish makes a GUI Bridge program (the C++ exe + the IDE's bridge host, Python inside, about 12 MB): a project with a Python module (RAD Hub) cannot be a single native exe. Note: the published bridge program does not start RAD Hub, so the database calls need the IDE (see the test report)

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...).
2. Press F5. Needs g++ (MinGW-w64; found or downloaded by the IDE).
3. Try: F5, New, type a name / phone / e-mail, Save; type part of a name in Search and press Enter; Delete.

## Publish

Build > Publish: a GUI Bridge program (the C++ exe + the IDE's bridge host, Python inside, about 12 MB): a project with a Python module (RAD Hub) cannot be a single native exe. Note: the published bridge program does not start RAD Hub, so the database calls need the IDE (see the test report). The test `samples/Tests/Examples/test_examples_compiled.py` builds, runs and publishes this project and starts the published exe.

## Files

* `ContactsDb.py`
* `frmContacts.cpp`
* `frmContacts.form`
* `frmContacts_designer.cpp`
* `project.radproj`

---

## جهات الاتصال - C++

دفتر عناوين: قائمة جهات اتصال مع لوحة تفاصيل؛ إضافة وتعديل وحذف وبحث، وتُحفظ في ملف قاعدة بيانات بعد كل تغيير.

### ماذا يعرض

* قائمة ListBox تُملأ من السجلات (`Clear` و`AddItem` و`ListIndex` وحدث `SelectedIndexChanged`)
* إطار GroupBox فيه مربعات نص وقائمة منسدلة (المجموعة) ومربع اختيار (مفضّل)
* إضافة وحفظ (إدراج أو تعديل) وحذف (بتأكيد) وبحث (Enter في مربع البحث)
* التحقق من المدخلات (الاسم مطلوب، والبريد يحتاج @) وشريط الحالة
* تُنشأ سجلات تجريبية في أول تشغيل
* مشروع متعدد اللغات: طبقة البيانات وحدة بايثون `ContactsDb.py` (SQLite، الملف `contacts.db`)؛ ونموذج C++ يستدعيها عبر RAD Hub بـ `rad::invoke(...)`. يشغّل الـ IDE ‏RAD Hub مع كل تشغيل.

### مزايا الـ IDE المستخدمة

* جسر الواجهة (GUI Bridge): الـ IDE يرسم النماذج من ملفات ‎.form‎، وكود C++ يعالج الأحداث فقط (معالجات باسم `<Control>_<Event>`) ويتعامل مع العناصر عبر `rad::set` / `rad::get` / `rad::call` (radgui.hpp)
* مصمم النماذج: افتح المشروع وانقر نقرًا مزدوجًا على النموذج (كل العناصر محفوظة في ملف ‎.form‎)
* البناء > النشر يصنع برنامج جسر (ملف C++ مع مضيف الجسر، بداخله بايثون، حوالي 12 م.ب): مشروع فيه وحدة بايثون (RAD Hub) لا يمكن أن يكون exe أصليًا واحدًا. ملاحظة: البرنامج المنشور لا يشغّل RAD Hub، لذا تحتاج استدعاءات قاعدة البيانات إلى الـ IDE.

### التشغيل

1. ملف > فتح مشروع... واختر هذا المجلد (أو مساعدة > أمثلة المشاريع...).
2. اضغط F5. يحتاج g++ (MinGW-w64؛ يجده الـ IDE أو ينزّله).
3. جرّب: F5 ثم جديد، اكتب اسمًا ورقمًا وبريدًا ثم حفظ؛ اكتب جزءًا من اسم في البحث واضغط Enter؛ ثم حذف.

### النشر

البناء > النشر: برنامج جسر (ملف C++ مع مضيف الجسر، بداخله بايثون، حوالي 12 م.ب): مشروع فيه وحدة بايثون (RAD Hub) لا يمكن أن يكون exe أصليًا واحدًا. ملاحظة: البرنامج المنشور لا يشغّل RAD Hub، لذا تحتاج استدعاءات قاعدة البيانات إلى الـ IDE.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
