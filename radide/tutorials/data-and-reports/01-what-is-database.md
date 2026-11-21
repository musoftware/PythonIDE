# الدرس 1: ما هي قاعدة البيانات؟ أول جدول SQLite

**في هذا الدرس ستتعلم:**

- ما هي **قاعدة البيانات**، و**الجدول**، و**الصف** و**العمود**، و**المفتاح الأساسي**.
- لماذا نبدأ بـ **SQLite**: قاعدة بيانات كاملة في ملف واحد بلا تثبيت.
- أول أوامر **SQL**: `CREATE TABLE` و `INSERT` و `SELECT`.
- كيف يتصل برنامج BASIC بقاعدة البيانات عبر **ADO**.

## دفتر منظم جدًا

تخيّل دفتر حسابات محل بقالة: صفحة للمنتجات، وصفحة للعملاء، وصفحة للفواتير. كل صفحة جدول مسطّر بأعمدة ثابتة.
**قاعدة البيانات** هي هذا الدفتر، لكنها:

- لا تمتلئ مهما كثرت البيانات.
- تبحث في مليون صف في جزء من الثانية.
- يكتب فيها أكثر من برنامج في وقت واحد دون أن يفسد أحدهم عمل الآخر.

| المصطلح | بالإنجليزية | في الدفتر |
|---|---|---|
| قاعدة بيانات | Database | الدفتر كله |
| جدول | Table | صفحة: المنتجات مثلًا |
| عمود (حقل) | Column (Field) | عنوان عمود: الاسم، السعر، الكمية |
| صف (سجل) | Row (Record) | سطر واحد: منتج واحد بكل بياناته |
| مفتاح أساسي | Primary Key | رقم مسلسل فريد لكل سطر، لا يتكرر أبدًا |

## لماذا SQLite؟

- قاعدة البيانات كلها **ملف واحد** مثل `shop.db`، تنسخه وترسله كأي ملف.
- **لا تحتاج تثبيت خادم**: مدمجة في Python وفي بيئة RAD IDE.
- تفهم لغة **SQL** القياسية نفسها التي تفهمها MySQL و PostgreSQL، فما تتعلمه هنا ينفعك هناك.

## لغة SQL في سطور

**SQL** (تُنطق "سيكول" أو "إس كيو إل") لغة تكلّم بها قاعدة البيانات. أوامرها تشبه الجمل الإنجليزية:

| الأمر | معناه |
|---|---|
| `CREATE TABLE Products (...)` | أنشئ جدول المنتجات بهذه الأعمدة |
| `INSERT INTO Products (Name, Price) VALUES ('Pen', 5)` | أضف صفًّا |
| `SELECT Name, Price FROM Products` | اعرض هذه الأعمدة من الجدول |
| `SELECT * FROM Products WHERE Price > 10` | اعرض الصفوف التي تحقق الشرط |
| `UPDATE Products SET Price = 6 WHERE Id = 1` | عدّل |
| `DELETE FROM Products WHERE Id = 1` | احذف |

> 💡 النصوص في SQL بين علامتي تنصيص **مفردة** `'Pen'`، والأرقام بدونها.

## BASIC يتكلم مع قاعدة البيانات: ADO

في Visual Basic 6 نستخدم مكتبة **ADO** (ActiveX Data Objects)، وبيئة RAD IDE تدعمها:

- `ADODB.Connection`: **الاتصال**، مثل خط هاتف مفتوح مع قاعدة البيانات. `Open` يفتحه، و `Execute` ينفّذ أمر SQL.
- `ADODB.Recordset`: **مجموعة السجلات**، مثل ورقة نتائج تقرؤها سطرًا سطرًا: `EOF` (نهاية الملف)، و `MoveNext` (السطر التالي)، و `rs("Name")` (قيمة عمود).

نص الاتصال لملف SQLite: `Driver=SQLite;Data Source=shop.db`. الملف يُنشأ في مجلد البرنامج إذا لم يكن موجودًا.

## برنامجك الأول مع قاعدة البيانات

```vb run
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=shop.db"

    cn.Execute "DROP TABLE IF EXISTS Products"
    cn.Execute "CREATE TABLE Products (Id INTEGER PRIMARY KEY, Name TEXT, Price INTEGER, Qty INTEGER)"
    cn.Execute "INSERT INTO Products (Name, Price, Qty) VALUES ('Pen', 5, 100)"
    cn.Execute "INSERT INTO Products (Name, Price, Qty) VALUES ('Notebook', 25, 40)"
    cn.Execute "INSERT INTO Products (Name, Price, Qty) VALUES ('Bag', 150, 8)"

    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Id, Name, Price FROM Products ORDER BY Id", cn
    Do While Not rs.EOF
        Debug.Print rs("Id") & ") " & rs("Name") & " - " & rs("Price") & " جنيه"
        rs.MoveNext
    Loop
    rs.Close
    cn.Close
End Sub
```

```text output
1) Pen - 5 جنيه
2) Notebook - 25 جنيه
3) Bag - 150 جنيه
```

### سطرًا سطرًا

- `DROP TABLE IF EXISTS` يحذف الجدول القديم حتى يبدأ المثال نظيفًا كل مرة.
- `Id INTEGER PRIMARY KEY` عمود **ترقيم تلقائي**: لم نكتب قيمته، فأعطته SQLite القيم 1 و 2 و 3.
- `Do While Not rs.EOF ... rs.MoveNext ... Loop` هي الحلقة المعتادة لقراءة النتائج.
- `Close` يغلق مجموعة السجلات والاتصال. أغلق دائمًا ما فتحته.

بعد «افتح في المحرر» ستجد الملف `shop.db` في مجلد المشروع. في الدرس التالي سنفتحه في نافذة **Databases** ونراه جدولًا حقيقيًا.

## أخطاء شائعة

- **علامات التنصيص المزدوجة داخل SQL:** في BASIC النص كله بين `"..."`، فاكتب نصوص SQL بالمفردة: `'Pen'`.
- **نسيان `rs.MoveNext`:** حلقة لا تنتهي، لأن السجل الحالي لا يتغير أبدًا.
- **كتابة قيمة للمفتاح الأساسي مكررة:** `INSERT ... (Id, ...) VALUES (1, ...)` مرتين تعطي خطأ "UNIQUE constraint failed".
- **نسيان الفاصلة بين الأعمدة** في `CREATE TABLE`: خطأ صياغة SQL.

## تمرين

### تمرين 1: جدول العملاء

أنشئ جدول `Customers` فيه `Id` و `Name` و `City`، وأضف عميلين: (`Ahmed`، `Cairo`) و (`Sara`، `Alexandria`)، ثم اطبع كل عميل بهذا الشكل: `Ahmed - Cairo`.

```vb exercise
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=shop.db"
    cn.Execute "DROP TABLE IF EXISTS Customers"
    ' أكمل
    cn.Close
End Sub
```

```vb solution
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=shop.db"
    cn.Execute "DROP TABLE IF EXISTS Customers"
    cn.Execute "CREATE TABLE Customers (Id INTEGER PRIMARY KEY, Name TEXT, City TEXT)"
    cn.Execute "INSERT INTO Customers (Name, City) VALUES ('Ahmed', 'Cairo')"
    cn.Execute "INSERT INTO Customers (Name, City) VALUES ('Sara', 'Alexandria')"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Name, City FROM Customers ORDER BY Id", cn
    Do While Not rs.EOF
        Debug.Print rs("Name") & " - " & rs("City")
        rs.MoveNext
    Loop
    rs.Close
    cn.Close
End Sub
```

```text output
Ahmed - Cairo
Sara - Alexandria
```

## اختبر نفسك

```quiz
{"question": "ما هو المفتاح الأساسي (Primary Key)؟", "choices": ["كلمة مرور قاعدة البيانات", "عمود قيمته فريدة لكل صف ولا تتكرر", "أول عمود نصي", "اسم الجدول"], "answer": 1, "explanation": "المفتاح الأساسي يميّز كل صف، مثل رقم البطاقة الشخصية."}
```

```quiz
{"question": "أي أمر SQL يعرض البيانات؟", "choices": ["`INSERT`", "`SELECT`", "`DELETE`", "`CREATE`"], "answer": 1, "explanation": "SELECT يقرأ ويعرض، و INSERT يضيف، و DELETE يحذف، و CREATE ينشئ."}
```

```quiz
{"question": "لماذا نكتب `rs.MoveNext` داخل الحلقة؟", "choices": ["لحفظ السجل", "للانتقال إلى السجل التالي، وإلا لن تنتهي الحلقة", "لحذف السجل", "لإغلاق الاتصال"], "answer": 1, "explanation": "بدون MoveNext يبقى السجل الحالي كما هو ولا يصل rs.EOF أبدًا إلى True."}
```

## الخلاصة

- قاعدة البيانات دفتر منظم: جداول، وأعمدة، وصفوف، ومفتاح أساسي فريد.
- SQLite = قاعدة بيانات في ملف واحد بلا تثبيت.
- SQL: `CREATE TABLE` و `INSERT` و `SELECT` و `UPDATE` و `DELETE`.
- في BASIC: `ADODB.Connection` للاتصال و `Execute`، و `ADODB.Recordset` للقراءة بـ `EOF` و `MoveNext`.
