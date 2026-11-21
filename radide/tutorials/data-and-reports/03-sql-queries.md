# الدرس 3: استعلامات SQL ونافذة الاستعلام

**في هذا الدرس ستتعلم:**

- لسان **الاستعلام** (Query) في مساحة قواعد البيانات: كتابة SQL وتشغيله وقراءة الأخطاء.
- التصفية `WHERE` و `LIKE`، والترتيب `ORDER BY`، والتجميع `GROUP BY` مع `COUNT` و `SUM` و `AVG`.
- ربط جدولين بـ `JOIN`.
- `UPDATE` و `DELETE` بأمان، ولماذا لا تبني SQL بلصق نصوص المستخدم.

## اسأل الدفتر سؤالًا

**الاستعلام** (Query) سؤال توجهه لقاعدة البيانات: "من الطلاب الذين نجحوا؟ وما متوسط درجاتهم؟". والجواب جدول نتائج.

## نافذة الاستعلام خطوة بخطوة

1. في نافذة **Databases** انقر القاعدة بالزر الأيمن > **New Query** (استعلام جديد)، أو **Tools > Databases > New Query**.
2. يفتح لسان فيه محرر SQL، وفي شريطه اسم الاتصال المستخدم.
3. اكتب الاستعلام، ثم **Run** (`F5` أو `Ctrl+Enter`).
   - إذا **حددت** جزءًا من النص يُنفّذ المحدد فقط. مفيد عندما يكون في اللسان عدة استعلامات.
4. النتائج تظهر في الأسفل: **لسان لكل جدول نتائج**، ولسان **Messages** فيه عدد الصفوف المتأثرة والأخطاء **برقم السطر**.
5. **Cancel** (`Esc`) يوقف استعلامًا طويلًا.

خيارات أخرى في الشريط: **Open .sql...** و **Save .sql...** لحفظ استعلاماتك في ملفات، و **Stop on first error** للتوقف عند أول خطأ في ملف فيه أوامر كثيرة.

## SELECT بالتفصيل

```text
SELECT الأعمدة
FROM الجدول
WHERE الشرط
GROUP BY عمود التجميع
ORDER BY عمود الترتيب [DESC]
```

| الجزء | مثال | المعنى |
|---|---|---|
| `WHERE` | `WHERE Grade >= 50` | الصفوف التي تحقق الشرط فقط |
| `AND` / `OR` | `WHERE Grade >= 50 AND City = 'Cairo'` | شرطان معًا / أحدهما |
| `LIKE` | `WHERE Name LIKE 'M%'` | الاسم يبدأ بـ M (`%` = أي حروف) |
| `ORDER BY` | `ORDER BY Grade DESC` | ترتيب تنازلي (`ASC` تصاعدي، وهو الافتراضي) |
| `COUNT(*)` | `SELECT COUNT(*) FROM Students` | عدد الصفوف |
| `SUM` / `AVG` / `MIN` / `MAX` | `SELECT AVG(Grade) ...` | مجموع / متوسط / أصغر / أكبر |
| `GROUP BY` | `GROUP BY City` | صف واحد لكل مدينة مع حساباته |

## مثال: التجميع والترتيب

```vb run
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, City TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Mona', 'Cairo', 95)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Omar', 'Giza', 40)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Mazen', 'Cairo', 71)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Laila', 'Giza', 88)"

    Set rs = CreateObject("ADODB.Recordset")
    Debug.Print "-- الناجحون من الأعلى:"
    rs.Open "SELECT Name, Grade FROM Students WHERE Grade >= 50 ORDER BY Grade DESC", cn
    Do While Not rs.EOF
        Debug.Print rs("Name") & " " & rs("Grade")
        rs.MoveNext
    Loop
    rs.Close

    Debug.Print "-- لكل مدينة:"
    rs.Open "SELECT City, COUNT(*) AS N, MAX(Grade) AS Best FROM Students GROUP BY City ORDER BY City", cn
    Do While Not rs.EOF
        Debug.Print rs("City") & ": " & rs("N") & " طلاب، أعلى درجة " & rs("Best")
        rs.MoveNext
    Loop
    rs.Close
    cn.Close
End Sub
```

```text output
-- الناجحون من الأعلى:
Mona 95
Laila 88
Mazen 71
-- لكل مدينة:
Cairo: 2 طلاب، أعلى درجة 95
Giza: 2 طلاب، أعلى درجة 88
```

انسخ الاستعلامين إلى لسان **New Query** على `school.db` وشغّلهما بـ `F5`: سترى النتائج في جدولين.

## JOIN: ربط جدولين

البيانات المنظمة تُوزّع على جداول: جدول **العملاء**، وجدول **الطلبات** فيه عمود `CustomerId` يشير إلى العميل. هذا العمود اسمه **مفتاح أجنبي** (Foreign Key).
`JOIN` يجمع الجدولين في نتيجة واحدة:

```vb run
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=shop.db"
    cn.Execute "DROP TABLE IF EXISTS Orders"
    cn.Execute "DROP TABLE IF EXISTS Customers"
    cn.Execute "CREATE TABLE Customers (Id INTEGER PRIMARY KEY, Name TEXT)"
    cn.Execute "CREATE TABLE Orders (Id INTEGER PRIMARY KEY, CustomerId INTEGER REFERENCES Customers(Id), Total INTEGER)"
    cn.Execute "INSERT INTO Customers (Name) VALUES ('Ahmed')"
    cn.Execute "INSERT INTO Customers (Name) VALUES ('Sara')"
    cn.Execute "INSERT INTO Orders (CustomerId, Total) VALUES (1, 120)"
    cn.Execute "INSERT INTO Orders (CustomerId, Total) VALUES (2, 300)"
    cn.Execute "INSERT INTO Orders (CustomerId, Total) VALUES (1, 80)"

    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT c.Name, SUM(o.Total) AS Spent FROM Orders o JOIN Customers c ON c.Id = o.CustomerId " & _
            "GROUP BY c.Name ORDER BY Spent DESC", cn
    Do While Not rs.EOF
        Debug.Print rs("Name") & " اشترى بمبلغ " & rs("Spent")
        rs.MoveNext
    Loop
    rs.Close
    cn.Close
End Sub
```

```text output
Sara اشترى بمبلغ 300
Ahmed اشترى بمبلغ 200
```

`o` و `c` أسماء مختصرة (Aliases) للجدولين، و `ON c.Id = o.CustomerId` شرط الربط. والعلاقة تظهر خطًا بين الجدولين في **Tools > Databases > Database Diagram**.

## UPDATE و DELETE بحذر

```text
UPDATE Students SET Grade = Grade + 5 WHERE City = 'Giza'
DELETE FROM Students WHERE Grade < 50
```

> ⚠️ **لا تنسَ `WHERE`!** `DELETE FROM Students` وحدها تحذف **كل** الطلاب، و `UPDATE Students SET Grade = 0` تصفّر **كل** الدرجات. جرّب الشرط أولًا بـ `SELECT` ثم حوّله إلى `UPDATE` أو `DELETE`.

## لا تلصق نصوص المستخدم داخل SQL

لو كتبت في برنامجك:

```vb
sql = "SELECT * FROM Users WHERE Name = '" & txtName.Text & "'"
```

فمستخدم خبيث قد يكتب في المربع `' OR '1'='1` فيرى كل المستخدمين! هذا اسمه **حقن SQL** (SQL Injection).
الحل: **الاستعلامات ذات المعاملات** (Parameterized queries): تكتب `WHERE Name = ?` وترسل القيمة منفصلة. والكود الذي تولّده نافذة **Data Sources** (الدرس 5) يستخدم هذه الطريقة دائمًا.

## أخطاء شائعة

- **`=` مع النصوص بدون تنصيص:** `WHERE City = Cairo` خطأ؛ الصحيح `'Cairo'`.
- **عمود في SELECT ليس في GROUP BY ولا داخل دالة تجميع:** النتيجة غير مفهومة. اجمع به أو استخدم `COUNT` / `MAX` ...
- **تشغيل اللسان كله وأنت تريد سطرًا واحدًا:** حدد السطر قبل `F5`.
- **نسيان `WHERE` في `DELETE`:** يحذف كل شيء.

## تمرين

### تمرين 1: متوسط كل مدينة

باستخدام جدول الطلاب في المثال الأول، اطبع متوسط الدرجات لكل مدينة مرتبًا بالمدينة، بهذا الشكل: `Cairo: 83`.
(متوسط القاهرة (95 + 71) / 2 = 83، والجيزة (40 + 88) / 2 = 64). استخدم `AVG(Grade)`.

```vb exercise
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, City TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Mona', 'Cairo', 95)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Omar', 'Giza', 40)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Mazen', 'Cairo', 71)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Laila', 'Giza', 88)"
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
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, City TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Mona', 'Cairo', 95)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Omar', 'Giza', 40)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Mazen', 'Cairo', 71)"
    cn.Execute "INSERT INTO Students (Name, City, Grade) VALUES ('Laila', 'Giza', 88)"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT City, AVG(Grade) AS Average FROM Students GROUP BY City ORDER BY City", cn
    Do While Not rs.EOF
        Debug.Print rs("City") & ": " & rs("Average")
        rs.MoveNext
    Loop
    rs.Close
    cn.Close
End Sub
```

```text output
Cairo: 83
Giza: 64
```

## اختبر نفسك

```quiz
{"question": "حددت سطرًا واحدًا في لسان الاستعلام وضغطت F5. ماذا يُنفّذ؟", "choices": ["كل اللسان", "السطر المحدد فقط", "لا شيء", "آخر سطر"], "answer": 1, "explanation": "إذا وُجد تحديد يُنفّذ المحدد فقط."}
```

```quiz
{"question": "ماذا يفعل `DELETE FROM Students` بدون `WHERE`؟", "choices": ["يحذف آخر صف", "يحذف كل الصفوف", "يعطي خطأ دائمًا", "يحذف الجدول وأعمدته"], "answer": 1, "explanation": "بدون شرط يحذف كل الصفوف. اكتب WHERE دائمًا وجرّبه بـ SELECT أولًا."}
```

```quiz
{"question": "ما الذي يحمي من حقن SQL؟", "choices": ["الخط العريض", "الاستعلامات ذات المعاملات (`?`) بدل لصق النصوص", "حذف المسافات", "الحروف الكبيرة"], "answer": 1, "explanation": "القيمة تُرسل منفصلة عن نص الاستعلام فلا تُفهم كأوامر."}
```

## الخلاصة

- **New Query**: `F5` / `Ctrl+Enter` للتشغيل (المحدد فقط إن وُجد)، و `Esc` للإلغاء، و **Messages** للأخطاء بأرقام الأسطر.
- `WHERE` و `LIKE` و `ORDER BY` و `GROUP BY` مع `COUNT` و `SUM` و `AVG` و `MAX`.
- `JOIN ... ON` يربط جدولين بالمفتاح الأجنبي.
- `UPDATE` و `DELETE` مع `WHERE` دائمًا، والمعاملات `?` بدل لصق نصوص المستخدم.
