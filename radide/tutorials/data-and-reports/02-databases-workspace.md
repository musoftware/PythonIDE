# الدرس 2: مساحة قواعد البيانات (Databases)

**في هذا الدرس ستتعلم:**

- فتح نافذة **Databases** (قواعد البيانات) ورؤية الجداول شجرةً.
- إنشاء قاعدة SQLite جديدة، وإضافة اتصال بقاعدة موجودة.
- تحرير بيانات الجدول مثل Excel: تعديل خلية، وصف جديد، وحذف، و NULL، وتصفية، وترتيب.
- لسان **المخطط** (Schema)، وإنشاء جدول بالنافذة، واستيراد CSV وتصدير البيانات، و Adminer، ومخطط قاعدة البيانات.

## غرفة الأرشيف

نافذة **Databases** هي غرفة الأرشيف في مكتبك: ترى فيها كل الدفاتر (قواعد البيانات)، وتفتح أي صفحة (جدول)، وتعدّل سطرًا، وتضيف عمودًا، دون كتابة برنامج.

افتحها من **View > Databases** (عرض > قواعد البيانات) أو `Ctrl+Alt+D`، أو من **Tools > Databases > Databases**.

## ماذا تعرض الشجرة؟

- **اتصالات كل المشروعات المفتوحة** (محفوظة في `project.radproj` تحت `databases`، **بدون كلمات المرور**).
- **ملفات SQLite** الموجودة في مجلدات المشروعات تلقائيًا (`.db` و `.sqlite` ...).
- تحت كل قاعدة: **الجداول** و**طرق العرض** (Views). وسّع الجدول لترى أعمدته.

> 💡 جرّب المثال أسفل الدرس أولًا: يصنع ملف `school.db` في مجلد المشروع، فيظهر في نافذة Databases مباشرة.

## إنشاء قاعدة أو إضافة اتصال

| الأمر | الاسم العربي | ماذا يفعل؟ |
|---|---|---|
| **Tools > Databases > New SQLite Database...** | قاعدة بيانات SQLite جديدة... | ملف `.db` جديد فارغ |
| **Tools > Databases > Add Connection...** | إضافة اتصال... | اتصال بقاعدة SQLite أو MySQL أو PostgreSQL موجودة |

في نافذة الاتصال:

- **Type:** نوع القاعدة: SQLite أو MySQL أو PostgreSQL.
- لـ SQLite: **Database file:** مع **Open...** لملف موجود أو **New...** لملف جديد.
- للخوادم: **Server:** و **Port:** و **User:** و **Password:** و **Database:**، وزر **List Databases** يعرض القواعد الموجودة على الخادم.
- **Test Connection** (اختبار الاتصال) يجرّب قبل الحفظ.
- **Remember the password (in the IDE settings, never in the project)**: كلمة المرور تُحفظ **مشفّرة** في إعدادات البيئة (بتشفير ويندوز DPAPI)، ولا تُكتب أبدًا في ملفات المشروع التي قد ترفعها إلى Git.

## بيانات الجدول: مثل جدول Excel

انقر الجدول مرتين (أو بالزر الأيمن > **Open Data**: فتح البيانات). يفتح لسان فيه الصفوف:

| ما تريد | كيف |
|---|---|
| تعديل قيمة | انقر الخلية مرتين واكتب، ثم `Enter`. تُحفظ في القاعدة مباشرة |
| صف جديد | **New Row...** (صف جديد...) |
| حذف صفوف | حددها ثم **Delete Selected Rows** (حذف الصفوف المحددة) |
| قيمة فارغة | بالزر الأيمن > **Set to NULL** (تعيين إلى NULL) |
| تصفية | اكتب في خانة **Filter (WHERE):** شرط SQL مثل `Grade >= 90` ثم `Enter` |
| ترتيب | انقر عنوان العمود |
| صفحات | الأزرار `|<` و `<` و `>` و `>|` للتنقل بين صفحات الجداول الكبيرة |

> 💡 **NULL** تعني "لا توجد قيمة"، وهي غير الصفر وغير النص الفارغ. مثل خانة "رقم الهاتف" التي لم يملأها العميل أصلًا.

كل عملية تعمل **في الخلفية**: إذا كان الجدول كبيرًا يظهر شريط فيه الوقت المنقضي وزر **Cancel** لإيقافها، والبيئة لا تتجمد.

## لسان المخطط (Schema)

انقر الجدول بالزر الأيمن > **Schema** (المخطط). ترى:

- **الأعمدة**: الاسم، والنوع، و NOT NULL، والقيمة الافتراضية، والمفتاح الأساسي.
- **الفهارس** (Indexes) و**المفاتيح الأجنبية** (Foreign Keys).
- **جملة `CREATE TABLE`** الكاملة، تنسخها لتنشئ الجدول نفسه في مكان آخر.
- **Add Column...** (إضافة عمود...) و **Drop Column** (حذف عمود).

## إنشاء جدول بالنافذة

انقر القاعدة بالزر الأيمن > **New Table...** (جدول جديد...):

1. **Table name:** اسم الجدول، مثل `Students`.
2. **Add Column** لكل عمود: **Name** و **Type** (`INTEGER` و `TEXT` و `REAL` ...)، وخانات المفتاح الأساسي و **Not Null** و **Unique**، و **Default** للقيمة الافتراضية.
3. **Up** / **Down** لترتيب الأعمدة.
4. في الأسفل ترى جملة SQL التي ستُنفّذ، فتتعلم منها. اضغط **OK**.

## الاستيراد والتصدير

| الأمر | أين؟ | ملاحظات |
|---|---|---|
| **Import CSV into New Table...** / **Import CSV...** | الزر الأيمن على القاعدة أو الجدول | **CSV file:** و **Into table:** و **Delimiter:** و **First row has the column names** و **Empty cells are NULL**، ومعاينة قبل الاستيراد |
| **Export to CSV...** | الزر الأيمن على الجدول | لفتحه في Excel |
| **Export to SQL...** | الزر الأيمن على الجدول | جمل `CREATE` و `INSERT` |
| **Export Database to SQL...** | الزر الأيمن على القاعدة | نسخة احتياطية كاملة |

## أدوات أخرى

- **Open in Adminer** (فتح في Adminer): واجهة ويب كاملة لإدارة القاعدة، مرفقة مع البيئة، وتدخل تلقائيًا. تحتاج PHP.
- **Tools > Databases > Database Diagram** (مخطط قاعدة البيانات): رسم للجداول والعلاقات بينها.
- **New Query** (استعلام جديد): لسان تكتب فيه SQL، وهو موضوع الدرس التالي.

## المثال: قاعدة مدرسة

اضغط «جرّبه»، ثم افتح **View > Databases**: ستجد `school.db` وفيه جدول `Students`. افتحه وعدّل درجة، ثم شغّل المثال مرة أخرى.

```vb run
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT NOT NULL, Grade INTEGER, Phone TEXT)"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Mona', 95, '0100')"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Omar', 78, NULL)"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Laila', 88, '0122')"

    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT COUNT(*) AS N FROM Students", cn
    Debug.Print "عدد الطلاب: " & rs("N")
    rs.Close

    rs.Open "SELECT COUNT(*) AS N FROM Students WHERE Phone IS NULL", cn
    Debug.Print "بدون رقم هاتف: " & rs("N")
    rs.Close
    cn.Close
End Sub
```

```text output
عدد الطلاب: 3
بدون رقم هاتف: 1
```

لاحظ `IS NULL`: لا نكتب `= NULL`، لأن NULL ليست قيمة تُقارن بعلامة `=`.

## أخطاء شائعة

- **لا يظهر ملف `.db` في الشجرة:** اضغط **Refresh** (تحديث) بالزر الأيمن، أو تأكد أنه داخل مجلد المشروع.
- **حذف عمود عليه بيانات مهمة:** **Drop Column** لا تراجع فيه. صدّر الجدول أولًا.
- **حفظ كلمة مرور الخادم في كود البرنامج:** استخدم خيار التذكر في البيئة، والبرنامج يقرؤها من متغيرات البيئة أو يسأل المستخدم.
- **كتابة `= NULL` في التصفية:** الصحيح `IS NULL` أو `IS NOT NULL`.

## تمرين

### تمرين 1: المتفوقون

استخدم القاعدة نفسها، واطبع عدد الطلاب الذين درجتهم 85 أو أكثر بهذا الشكل: `المتفوقون: 2`.

```vb exercise
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT NOT NULL, Grade INTEGER, Phone TEXT)"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Mona', 95, '0100')"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Omar', 78, NULL)"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Laila', 88, '0122')"
    Set rs = CreateObject("ADODB.Recordset")
    ' أكمل
    cn.Close
End Sub
```

```vb solution
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT NOT NULL, Grade INTEGER, Phone TEXT)"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Mona', 95, '0100')"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Omar', 78, NULL)"
    cn.Execute "INSERT INTO Students (Name, Grade, Phone) VALUES ('Laila', 88, '0122')"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT COUNT(*) AS N FROM Students WHERE Grade >= 85", cn
    Debug.Print "المتفوقون: " & rs("N")
    rs.Close
    cn.Close
End Sub
```

```text output
المتفوقون: 2
```

### مهمة عملية: جولة في الأرشيف

1. شغّل المثال، ثم `Ctrl+Alt+D`.
2. افتح بيانات `Students`، وغيّر درجة `Omar` إلى 82، وضع له رقم هاتف.
3. اكتب في **Filter (WHERE):** الشرط `Grade > 80` ثم `Enter`.
4. افتح لسان **Schema** وانسخ جملة `CREATE TABLE`.
5. انقر الجدول بالزر الأيمن > **Export to CSV...** وافتح الملف في Excel.

## اختبر نفسك

```quiz
{"question": "أين تُحفظ كلمة مرور خادم MySQL إذا اخترت تذكرها؟", "choices": ["في `project.radproj`", "مشفّرة في إعدادات البيئة، وليس في ملفات المشروع", "في كود البرنامج", "في ملف نصي على سطح المكتب"], "answer": 1, "explanation": "الاتصال يُحفظ في المشروع بدون كلمة مرور، وكلمة المرور مشفّرة بـ DPAPI في إعدادات البيئة."}
```

```quiz
{"question": "ما معنى NULL؟", "choices": ["الرقم صفر", "نص فارغ", "لا توجد قيمة أصلًا", "خطأ"], "answer": 2, "explanation": "NULL غياب القيمة، وتُفحص بـ IS NULL."}
```

```quiz
{"question": "تريد نسخة احتياطية كاملة من القاعدة كجمل SQL. أي أمر؟", "choices": ["Export to CSV...", "Export Database to SQL...", "Drop Column", "New Row..."], "answer": 1, "explanation": "Export Database to SQL يكتب CREATE و INSERT لكل الجداول."}
```

## الخلاصة

- **View > Databases** (`Ctrl+Alt+D`): اتصالات المشروعات وملفات SQLite شجرةً.
- **New SQLite Database...** و **Add Connection...** مع **Test Connection**، وكلمات المرور مشفّرة خارج المشروع.
- بيانات الجدول تُحرَّر كجدول Excel، و **Schema** للأعمدة والفهارس وجملة `CREATE`.
- **New Table...** و **Import CSV** و **Export** و **Adminer** و **Database Diagram**.
