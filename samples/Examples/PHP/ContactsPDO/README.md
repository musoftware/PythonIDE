# Contacts with PDO (PHP desktop form)

A desktop address book in PHP with a SQLite database through PDO.

**What it shows**
- PDO + SQLite with prepared statements (module `Db.php`: `db_open`, `db_find`, `db_save`, `db_delete`), the table
  created on the first start with two sample contacts.
- Master / detail: a `ListBox` of names (the record ids are kept in a PHP array) and a detail panel; selecting a
  line (`SelectedIndexChanged`) loads the record.
- One Save button for insert and update, Delete after an InputBox confirmation, live search on `TextChanged`.
- A multi-line Notes `TextBox` - line breaks survive the bridge in both directions.
- UTF-8 Arabic names, cities and notes.

**Run**: open the folder, **F5** (PHP with the `pdo_sqlite` extension). The database is `contacts.sqlite`.
**Publish**: Build > Publish (GUI Bridge program, Python inside; PHP needed on the PC).

---

# جهات الاتصال بـ PDO (نموذج سطح مكتب بلغة PHP)

دفتر عناوين لسطح المكتب بلغة PHP مع قاعدة بيانات SQLite عبر PDO.

**ماذا يوضح**
- PDO وSQLite بجمل مجهزة في الوحدة `Db.php`، وإنشاء الجدول في أول تشغيل مع بيانات تجريبية.
- قائمة رئيسية بالأسماء وتفاصيل السجل المختار.
- زر حفظ واحد للإضافة والتعديل، وحذف بعد التأكيد، وبحث فوري.
- مربع ملاحظات متعدد الأسطر، والنصوص العربية.

**التشغيل**: افتح المجلد واضغط **F5** (PHP مع إضافة pdo_sqlite).
**النشر**: Build > Publish (برنامج GUI Bridge، يحتاج PHP على الجهاز).

(c) 2026 Musoftware - https://musoftwares.com - MIT License
