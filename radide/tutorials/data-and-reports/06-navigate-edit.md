# الدرس 6: التنقل والإضافة والحذف والقوائم المرتبطة

**في هذا الدرس ستتعلم:**

- دورة حياة السجل: **إضافة** ثم **تعديل** ثم **حفظ** أو **إلغاء**، ثم **حذف**.
- البحث والتصفية والترتيب في مصدر البيانات.
- **قائمة البحث** (Lookup): ComboBox يعرض اسم المدينة ويحفظ رقمها.
- **رئيسي/تفصيلي** (Master / Detail): اختيار عميل يعرض طلباته.

## دورة حياة السجل

تخيّل استمارة ورقية في مكتب:

1. **AddNew**: تأخذ استمارة فارغة.
2. تملأ الخانات (`SetValue` أو الكتابة في المربعات المربوطة).
3. **Update**: تسلّمها للأرشيف (تُحفظ في القاعدة).
4. أو **CancelEdit**: تمزقها قبل التسليم.
5. **RemoveCurrent** ثم **Update**: تسحب استمارة قديمة من الأرشيف.

في النموذج المربوط بمصدر بيانات، أزرار شريط التنقل تفعل هذا: **إضافة** = `AddNew`، **حذف** = `RemoveCurrent`، **حفظ** = `Update`.

> ⚠️ **الحفظ دفعة واحدة:** التعديلات تبقى في الذاكرة حتى `Update`. `HasChanges` يخبرك إن كان هناك ما لم يُحفظ، فاسأل المستخدم قبل إغلاق النافذة.

## البحث والتصفية والترتيب

| ما تريد | في مصدر البيانات المولَّد | بـ ADO في BASIC |
|---|---|---|
| تصفية | `FillBy` بشرط، أو خاصية **Filter** في **Configure Data Source...** | `rs.Filter = "Grade >= 80"` |
| ترتيب | `SortBy "Name"`، أو **Sort** في **Configure Data Source...** | `rs.Sort = "Name"` أو `ORDER BY` |
| بحث | `Find` / `Search` | `rs.Find "Name = 'Omar'"` |

## مثال: إضافة وتعديل وحذف وبحث بـ ADO

هذا ما يفعله شريط التنقل خلف الستار، مكتوبًا بـ ADO:

```vb run
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Mona', 95)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Omar', 78)"

    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Id, Name, Grade FROM Students ORDER BY Id", cn, 1, 3

    ' 1) إضافة
    rs.AddNew
    rs("Name") = "Laila"
    rs("Grade") = 88
    rs.Update
    Debug.Print "بعد الإضافة: " & rs.RecordCount & " طلاب"

    ' 2) بحث ثم تعديل
    rs.MoveFirst
    rs.Find "Name = 'Omar'"
    rs("Grade") = 82
    rs.Update
    Debug.Print "درجة Omar الآن: " & rs("Grade")

    ' 3) حذف
    rs.MoveFirst
    rs.Find "Name = 'Mona'"
    rs.Delete
    rs.Close

    ' 4) ماذا بقي في القاعدة؟
    rs.Open "SELECT Name, Grade FROM Students ORDER BY Name", cn
    Do While Not rs.EOF
        Debug.Print rs("Name") & " " & rs("Grade")
        rs.MoveNext
    Loop
    rs.Close
    cn.Close
End Sub
```

```text output
بعد الإضافة: 3 طلاب
درجة Omar الآن: 82
Laila 88
Omar 82
```

الرقمان `1, 3` في `rs.Open` معناهما "مؤشر يتحرك في كل الاتجاهات" و"قفل يسمح بالتعديل"، كما في Visual Basic 6.

## قائمة البحث (Lookup)

جدول الطلاب لا يحفظ اسم المدينة نصًّا في كل صف، بل **رقمها** `CityId`، والأسماء في جدول `Cities`. هذا يمنع الأخطاء الإملائية ("القاهره" و"القاهرة").
لكن المستخدم يريد أن يرى **الاسم** لا الرقم. الحل: `ComboBox` مربوط هكذا:

| الخاصية | القيمة | المعنى |
|---|---|---|
| `DataSource` | `Cities` | القائمة تأتي من جدول المدن |
| `DisplayMember` | `Name` | المستخدم يرى اسم المدينة |
| `ValueMember` | `Id` | الذي يُحفظ هو رقمها |
| `DataMember` | `Students.CityId` | ويُكتب في عمود `CityId` للطالب الحالي |

### خطوة بخطوة

1. أضف `Students` و `Cities` كمصدري بيانات من **Add New Data Source...**.
2. اسحب `Students` كـ **Details**.
3. احذف مربع النص `CityId`، وضع مكانه `ComboBox`.
4. اضبط خصائصه الأربع كما في الجدول.
5. شغّل: القائمة تعرض الأسماء، واختيار مدينة يحفظ رقمها.

## رئيسي/تفصيلي (Master / Detail)

عميل واحد له طلبات كثيرة. نريد: تختار عميلًا من قائمة، فتظهر طلباته فقط في الشبكة.

1. أضف `Customers` و `Orders` كمصدري بيانات.
2. ضع `ListBox` مربوطًا بـ `Customers` (`DisplayMember = Name`).
3. اسحب `Orders` كـ `DataGridView`، واجعل استعلامه في **Configure Data Source...** مصفّى بالعميل الحالي (مثل `CustomerId = :Id`)، أو استدعِ `Orders.FillBy` من حدث تغيّر اختيار القائمة.

المنطق نفسه مكتوبًا بـ SQL: "طلبات العميل المحدد" = `SELECT * FROM Orders WHERE CustomerId = ?`.

## أخطاء شائعة

- **إغلاق النافذة قبل الحفظ:** افحص `HasChanges` في حدث الإغلاق واسأل "هل تريد الحفظ؟".
- **حذف عميل له طلبات:** القاعدة قد ترفض بسبب المفتاح الأجنبي، أو تبقى طلبات "يتيمة". احذف التفاصيل أولًا أو استخدم `ON DELETE CASCADE`.
- **ComboBox يعرض أرقامًا:** `DisplayMember` غير مضبوط.
- **`rs.Find` ولم يجد شيئًا:** يصبح `rs.EOF = True`. افحصه قبل القراءة.

## تمرين

### تمرين 1: طالب جديد ثم المتوسط

ابدأ من جدول فيه `Mona` (95) و `Omar` (78). أضف بـ `AddNew` الطالب `Hany` بدرجة 81، ثم اطبع المتوسط بـ `SELECT AVG(Grade)`: `المتوسط: 84.67`.
استخدم `Round(قيمة, 2)` للتقريب إلى رقمين عشريين.

```vb exercise
Sub Main()
    Dim cn, rs
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Mona', 95)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Omar', 78)"
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
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Mona', 95)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Omar', 78)"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Id, Name, Grade FROM Students", cn, 1, 3
    rs.AddNew
    rs("Name") = "Hany"
    rs("Grade") = 81
    rs.Update
    rs.Close
    rs.Open "SELECT AVG(Grade) AS A FROM Students", cn
    Debug.Print "المتوسط: " & Round(rs("A"), 2)
    rs.Close
    cn.Close
End Sub
```

```text output
المتوسط: 84.67
```

## اختبر نفسك

```quiz
{"question": "متى تُحفظ التعديلات في القاعدة عند استخدام مصدر بيانات؟", "choices": ["مع كل حرف تكتبه", "عند استدعاء `Update` (زر الحفظ)", "عند إغلاق البيئة", "لا تُحفظ أبدًا"], "answer": 1, "explanation": "التعديلات في الذاكرة حتى Update، و HasChanges يخبرك بوجود ما لم يُحفظ."}
```

```quiz
{"question": "لماذا نحفظ `CityId` بدل اسم المدينة في جدول الطلاب؟", "choices": ["لأن الأسماء العربية ممنوعة", "لتجنب تكرار الأسماء وأخطائها الإملائية، والأسماء في جدول المدن", "لأن الأرقام أجمل", "لا سبب"], "answer": 1, "explanation": "كل مدينة مكتوبة مرة واحدة في جدولها، والطلاب يشيرون إليها برقمها."}
```

```quiz
{"question": "ماذا يحدث بعد `rs.Find` لم يجد سجلًا مطابقًا؟", "choices": ["يعطي خطأ دائمًا", "يصبح `rs.EOF = True`", "يضيف سجلًا جديدًا", "يحذف الجدول"], "answer": 1, "explanation": "افحص rs.EOF بعد البحث قبل قراءة الحقول."}
```

## الخلاصة

- `AddNew` ثم تعبئة الحقول ثم `Update`، و `CancelEdit` للإلغاء، و `RemoveCurrent` للحذف، و `HasChanges` قبل الإغلاق.
- التصفية والترتيب من **Configure Data Source...** أو `FillBy` و `SortBy` و `Find`.
- قائمة البحث: `DisplayMember` يُعرض، و `ValueMember` يُحفظ، و `DataMember` العمود الذي يستقبل القيمة.
- رئيسي/تفصيلي: اختيار في القائمة يصفّي جدول التفاصيل.
