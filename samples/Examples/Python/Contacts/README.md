# Contacts - SQLite with data binding (python-tk)

An address book stored in `contacts.db` (SQLite), built with the IDE's **Data Sources** window
(VB 2005 style data binding).

**What it shows**
- Data > Add New Data Source (connection `ContactsDb` -> `contacts.db`, table `Contacts`), then the table dragged
  onto the form: the IDE generated the BindingNavigator (|< < "1 of 5" > >|) and the bound DataGridView.
- TextBoxes and a CheckBox bound to columns (Properties > Data: `DataSource = Contacts`, `DataMember = Name` ...),
  two-way: moving in the grid shows the record, typing edits it.
- New / Save / Delete with **validation** (`Validation.py`: name required, e-mail and phone format) before
  `Contacts.Update()` writes the changes in one transaction.
- Search as you type (`Contacts.Search`), a city filter that runs a **parameterized** SQL query
  (`Contacts.Fill("City = ?", city)`), `Contacts_PositionChanged` updating the status bar.
- Export to CSV with a SaveFileDialog; "save changes?" when closing.  Arabic names are stored and searched.

**Run**: open the folder, **F5**.  `python reset_db.py` restores the five sample contacts.
**Publish**: Build > Publish (PyInstaller); `contacts.db` is copied next to the program.

---

# جهات الاتصال - SQLite مع ربط البيانات (بايثون Tkinter)

دفتر عناوين محفوظ في قاعدة بيانات SQLite، مبني بنافذة **مصادر البيانات** في البيئة (ربط بيانات مثل VB 2005).

**ماذا يوضح**
- إضافة مصدر بيانات جديد ثم سحب الجدول على النموذج: البيئة أنشأت شريط التنقل وجدول البيانات المربوط تلقائياً.
- مربعات نص ومربع اختيار مربوطة بالأعمدة في الاتجاهين.
- جديد / حفظ / حذف مع **التحقق من صحة البيانات** قبل الحفظ (الاسم مطلوب، صيغة البريد والهاتف).
- البحث أثناء الكتابة، وتصفية حسب المدينة باستعلام SQL بمعاملات (آمن من حقن SQL).
- التصدير إلى ملف CSV، وسؤال حفظ التغييرات عند الإغلاق. الأسماء العربية تُحفظ ويُبحث فيها.

**التشغيل**: افتح المجلد واضغط **F5**. الأمر `python reset_db.py` يعيد البيانات الأصلية.
**النشر**: Build > Publish، ويتم نسخ `contacts.db` بجوار البرنامج.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
