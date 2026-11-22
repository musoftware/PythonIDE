# Contacts (JavaScript + SQLite)

An address book that stores its contacts in a SQLite database with Node's built-in `node:sqlite` module
(Node.js 22.5 or newer, no npm package).

**What it shows**
- CRUD: Add, Update, Delete (after an InputBox confirmation), Clear - prepared SQL statements in `ContactsDb.js`.
- A `DataGridView` filled from a query: `call("grdContacts", "AddItem", id, name, phone, email, group)` adds one
  row (one argument per cell); clicking a row (`SelectedIndexChanged`) reads `Row` and `TextMatrix(row, col)`
  and loads the contact into the text boxes.
- Live search with `TextChanged`, a `ComboBox` for the group, email validation with MsgBox.
- File > Export CSV (UTF-8 with BOM so Excel shows Arabic), File > Add Sample Data.
- Arabic names stored, sorted and searched (try searching for محمد).

**Run**: open the folder, **F5**. The database `contacts.db` is created next to the project on the first run.
**Publish**: Build > Publish (GUI Bridge program, Python inside; Node.js 22.5+ needed on the PC).

---

# جهات الاتصال (جافاسكربت + SQLite)

دفتر عناوين يحفظ جهات الاتصال في قاعدة بيانات SQLite باستخدام الوحدة المدمجة `node:sqlite` في Node.js (الإصدار 22.5
أو أحدث، بدون حزم npm).

**ماذا يوضح**
- الإضافة والتعديل والحذف (بعد التأكيد) بجمل SQL مجهزة في `ContactsDb.js`.
- جدول `DataGridView` يُملأ من الاستعلام، والنقر على صف يحمّل بياناته في مربعات النص.
- بحث فوري أثناء الكتابة، وقائمة منسدلة للمجموعة، والتحقق من البريد الإلكتروني.
- تصدير CSV يفتحه Excel بالعربية، وإضافة بيانات تجريبية.
- الأسماء العربية تُحفظ وتُرتب ويُبحث فيها.

**التشغيل**: افتح المجلد واضغط **F5**، وتُنشأ قاعدة البيانات `contacts.db` في أول تشغيل.
**النشر**: Build > Publish (برنامج GUI Bridge، يحتاج Node.js 22.5 أو أحدث على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
