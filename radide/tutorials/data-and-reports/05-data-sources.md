# الدرس 5: مصادر البيانات وربط DataGridView

**في هذا الدرس ستتعلم:**

- نافذة **Data Sources** (مصادر البيانات) على طريقة Visual Basic 2005.
- إضافة مصدر بيانات من جدول في SQLite أو MySQL أو PostgreSQL بمعالج **Add New Data Source**.
- **سحب جدول** إلى النموذج: `DataGridView` مع شريط تنقل، أو حقول **Details** (عنوان + مربع لكل عمود).
- خصائص الربط: `DataSource` و `DataMember` و `DisplayMember` و `ValueMember`، والكود الذي تولّده البيئة.

## السحب بدل الكتابة

في الدرسين السابقين كتبنا الكود بأيدينا: نفتح اتصالًا، وننفّذ `SELECT`، ونقرأ الصفوف في حلقة.
**نافذة مصادر البيانات** تفعل ذلك كله لك: تسحب جدولًا إلى النموذج، فتظهر شبكة فيها **بيانات حقيقية** وأزرار تنقل وحفظ، والبيئة تكتب كود القراءة والكتابة الآمن.
مثل الفرق بين أن تطبخ من الصفر أو تستخدم عجينة جاهزة: النتيجة واحدة، والوقت أقل بكثير.

> 💡 مصادر البيانات تعمل مع نماذج **Python (Tkinter)** و **Python (PySide6 / Qt)** و **Visual Basic 6 (BASIC)**.

## الخطوة 1: افتح النافذة

1. افتح نموذجًا في المصمم.
2. **Data > Show Data Sources** (البيانات > عرض مصادر البيانات) أو `Alt+Shift+D`. أو **View > Data Sources**.

## الخطوة 2: أضف مصدر بيانات

**Data > Add New Data Source...** (إضافة مصدر بيانات جديد...). النافذة من جزأين:

**1. Which data connection?** (أي اتصال؟)

- **Connection of the Databases workspace:** (اتصال مساحة عمل قواعد البيانات:) اختر اتصالًا من نافذة Databases.
  - **New Connection...** (اتصال جديد...) لإنشاء اتصال SQLite أو MySQL أو PostgreSQL الآن.
  - **SQLite File...** (ملف SQLite...) لاختيار ملف `.db` مباشرة.
- **ODBC connection string:** (نص اتصال ODBC:) لقواعد أخرى عبر ODBC (يحتاج مكتبة `pyodbc`).
- ثم **Connect** (اتصال).

**2. Choose your database objects** (اختر كائنات قاعدة البيانات)

- علّم **الجداول** و**طرق العرض** التي يحتاجها النموذج، أو اكتب **استعلامًا** (`SELECT ...`).
- اضغط **OK**.

كل جدول يصبح **مصدر بيانات** باسمه (مثل `Students`)، والبيئة تحفظ أعمدته وأنواعها ومفتاحه الأساسي.

## الخطوة 3: اسحب الجدول إلى النموذج

اسحب `Students` من نافذة Data Sources وأفلته على النموذج. يظهر:

- **`DataGridView`**: جدول فيه الصفوف **الحقيقية** من القاعدة، حتى في المصمم.
- **شريط تنقل** (BindingNavigator): الأول، والسابق، ورقم السجل، والتالي، والأخير، وإضافة، وحذف، وحفظ.

### Details: نموذج إدخال بدل الشبكة

انقر الجدول في نافذة Data Sources بالزر الأيمن واختر **Drop as Details (labels and text boxes)** بدل **Drop as DataGridView** (إسقاط كـ DataGridView)، ثم اسحبه. (وفي القائمة نفسها **Add to Form** يضعه على النموذج بدون سحب):
يظهر **`Label` و `TextBox`** لكل عمود (و `CheckBox` للأعمدة المنطقية)، مع شريط التنقل. وتستطيع سحب **عمود واحد** لتحصل على عنوان ومربع له فقط.

## خصائص الربط (فئة Data في نافذة الخصائص)

| الخاصية | لأي أداة | المعنى |
|---|---|---|
| `DataSource` | كل الأدوات المربوطة | اسم مصدر البيانات: `Students` |
| `DataMember` | `TextBox` و `Label` و `CheckBox` | العمود: `Name` |
| `DisplayMember` | `ListBox` و `ComboBox` | العمود الذي **يُعرض** للمستخدم: `CityName` |
| `ValueMember` | `ListBox` و `ComboBox` | العمود الذي **يُحفظ**: `CityId` |
| `Columns` | `DataGridView` | الأعمدة الظاهرة (فارغ = كلها) |

## أوامر أخرى في نافذة Data Sources

| الأمر | الاسم العربي | وظيفته |
|---|---|---|
| **Configure Data Source...** | ضبط مصدر البيانات... | تعديل الاستعلام، والتصفية، والترتيب |
| **Preview Data...** | معاينة البيانات... | رؤية الصفوف قبل وضعها على النموذج |
| **Refresh Data Sources** | تحديث مصادر البيانات | إعادة قراءة الأعمدة والصفوف بعد تعديل الجدول (من قائمة **Data**) |
| **Remove** | إزالة | حذف مصدر البيانات من النموذج |

## الكود الذي تولّده البيئة

البيئة تولّد كائنًا لكل مصدر بيانات باسمه (ومعه الاسمان البديلان `StudentsBindingSource` و `StudentsTableAdapter` لمن اعتاد Visual Basic 2005). من كود BASIC:

```vb
Private Sub cmdNext_Click()
    Students.MoveNext
    lblInfo.Caption = "السجل " & (Students.Position + 1) & " من " & Students.Count
End Sub

Private Sub cmdSave_Click()
    Students.Update          ' يحفظ كل التعديلات في قاعدة البيانات
End Sub
```

ومن Python الأسماء نفسها: `self.Students.MoveNext()` و `self.Students.Update()`.

| العضو | وظيفته |
|---|---|
| `Fill` / `FillBy` | تحميل الصفوف (بشرط في `FillBy`) |
| `MoveFirst` / `MovePrevious` / `MoveNext` / `MoveLast`، `Position` | التنقل |
| `Current`، `Value("Name")`، `SetValue "Name", "x"` | قراءة وكتابة السجل الحالي |
| `AddNew` / `RemoveCurrent` | سجل جديد / حذف الحالي |
| `Update` | حفظ التغييرات (INSERT و UPDATE و DELETE) |
| `CancelEdit` / `RejectChanges` / `HasChanges` | إلغاء التعديل / التراجع عن كل التغييرات / هل هناك تغييرات؟ |
| `Search` / `SortBy` / `Find` | بحث وترتيب |

والأهم: كل أوامر الكتابة **ذات معاملات** (Parameterized)، فلا خطر حقن SQL، وكلمة المرور لا تُكتب في الكود.

## ما الذي يحدث تحت الغطاء؟

شريط التنقل يقرأ الصفوف مرة واحدة ثم يعرض "السجل الحالي" في المربعات. هذا مثال BASIC يفعل الشيء نفسه يدويًا بـ ADO، لترى الفكرة:

<!-- test: {"steps": [["click", "cmdNext"], ["click", "cmdNext"]], "expect": {"txtName.Text": "Laila", "txtGrade.Text": "88", "lblPos.Caption": "3 / 3"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الطلاب"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.TextBox txtName
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.TextBox txtGrade
      Left            =   2880
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.CommandButton cmdPrev
      Caption         =   "<"
      Left            =   240
      Top             =   900
      Width           =   600
      Height          =   400
   End
   Begin VB.CommandButton cmdNext
      Caption         =   ">"
      Left            =   960
      Top             =   900
      Width           =   600
      Height          =   400
   End
   Begin VB.Label lblPos
      Left            =   1800
      Top             =   960
      Width           =   1200
      Height          =   400
   End
End

Private rs As Object

Private Sub Form_Load()
    Dim cn
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Mona', 95)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Omar', 78)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Laila', 88)"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Name, Grade FROM Students ORDER BY Id", cn
    ShowCurrent
End Sub

Private Sub ShowCurrent()
    txtName.Text = rs("Name")
    txtGrade.Text = rs("Grade")
    lblPos.Caption = rs.AbsolutePosition & " / " & rs.RecordCount
End Sub

Private Sub cmdNext_Click()
    rs.MoveNext
    If rs.EOF Then rs.MoveLast
    ShowCurrent
End Sub

Private Sub cmdPrev_Click()
    rs.MovePrevious
    If rs.BOF Then rs.MoveFirst
    ShowCurrent
End Sub
```

مع مصادر البيانات لا تكتب `Form_Load` ولا `ShowCurrent` ولا معالجات الأزرار: السحب والإفلات يكفي.

## أخطاء شائعة

- **أمر Add New Data Source معطّل أو لا يقبل النموذج:** النموذج بلغة غير مدعومة. استخدم Python (Tkinter أو Qt) أو BASIC.
- **تعديل في الشبكة لا يصل إلى القاعدة:** التعديلات تُحفظ بزر **الحفظ** في الشريط (أو `Update` في الكود).
- **تغيير أعمدة الجدول ثم الشبكة لا تتغير:** **Data > Refresh Data Sources**.
- **ComboBox يحفظ الاسم بدل الرقم:** اضبط `ValueMember` على عمود الرقم و `DisplayMember` على عمود الاسم.

## تمرين

### تمرين 1: زر "الأول"

أضف زرًّا `cmdFirst` نصه `|<` ينقل إلى أول سجل. ابدأ من المثال كما هو، والاختبار يضغط "التالي" مرتين ثم "الأول".

```vb form exercise
Begin VB.Form Form1
   Caption         =   "الطلاب"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.TextBox txtName
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.CommandButton cmdNext
      Caption         =   ">"
      Left            =   960
      Top             =   900
      Width           =   600
      Height          =   400
   End
   Begin VB.Label lblPos
      Left            =   1800
      Top             =   960
      Width           =   1200
      Height          =   400
   End
End

Private rs As Object

Private Sub Form_Load()
    Dim cn
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Mona', 95)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Omar', 78)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Laila', 88)"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Name, Grade FROM Students ORDER BY Id", cn
    ShowCurrent
End Sub

Private Sub ShowCurrent()
    txtName.Text = rs("Name")
    lblPos.Caption = rs.AbsolutePosition & " / " & rs.RecordCount
End Sub

Private Sub cmdNext_Click()
    rs.MoveNext
    If rs.EOF Then rs.MoveLast
    ShowCurrent
End Sub

' أضف cmdFirst في التصميم واكتب معالجه
```

<!-- test: {"steps": [["click", "cmdNext"], ["click", "cmdNext"], ["click", "cmdFirst"]], "expect": {"txtName.Text": "Mona", "lblPos.Caption": "1 / 3"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "الطلاب"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.TextBox txtName
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.CommandButton cmdFirst
      Caption         =   "|<"
      Left            =   240
      Top             =   900
      Width           =   600
      Height          =   400
   End
   Begin VB.CommandButton cmdNext
      Caption         =   ">"
      Left            =   960
      Top             =   900
      Width           =   600
      Height          =   400
   End
   Begin VB.Label lblPos
      Left            =   1800
      Top             =   960
      Width           =   1200
      Height          =   400
   End
End

Private rs As Object

Private Sub Form_Load()
    Dim cn
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=school.db"
    cn.Execute "DROP TABLE IF EXISTS Students"
    cn.Execute "CREATE TABLE Students (Id INTEGER PRIMARY KEY, Name TEXT, Grade INTEGER)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Mona', 95)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Omar', 78)"
    cn.Execute "INSERT INTO Students (Name, Grade) VALUES ('Laila', 88)"
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Name, Grade FROM Students ORDER BY Id", cn
    ShowCurrent
End Sub

Private Sub ShowCurrent()
    txtName.Text = rs("Name")
    lblPos.Caption = rs.AbsolutePosition & " / " & rs.RecordCount
End Sub

Private Sub cmdNext_Click()
    rs.MoveNext
    If rs.EOF Then rs.MoveLast
    ShowCurrent
End Sub

Private Sub cmdFirst_Click()
    rs.MoveFirst
    ShowCurrent
End Sub
```

### مهمة عملية: شبكة بدون كود

1. أنشئ مشروع **Python (Tkinter)** أو **BASIC**، وشغّل مثال الدرس 2 لتصنع `school.db` في مجلد المشروع (أو أنشئ قاعدة من نافذة Databases).
2. `Alt+Shift+D`، ثم **Add New Data Source...** > **SQLite File...** > اختر `school.db` > **Connect** > علّم `Students` > **OK**.
3. اسحب `Students` إلى النموذج: شبكة وشريط تنقل ببيانات حقيقية.
4. انقر `Students` بالزر الأيمن > **Drop as Details (labels and text boxes)**، واسحبه إلى نموذج ثانٍ.
5. شغّل البرنامج، وعدّل درجة، واضغط زر الحفظ في الشريط، ثم افتح الجدول في نافذة Databases لتتأكد.

## اختبر نفسك

```quiz
{"question": "ماذا يظهر عند سحب جدول من نافذة Data Sources إلى النموذج (الوضع الافتراضي)؟", "choices": ["زر واحد", "DataGridView بالبيانات الحقيقية وشريط تنقل وحفظ", "رسالة خطأ", "ملف CSV"], "answer": 1, "explanation": "الوضع الافتراضي DataGridView + BindingNavigator، و Drop as Details يعطي عنوانًا ومربعًا لكل عمود."}
```

```quiz
{"question": "في ComboBox للمدن: أي خاصية تحدد العمود الذي يُحفظ في القاعدة؟", "choices": ["`DisplayMember`", "`ValueMember`", "`Text`", "`Name`"], "answer": 1, "explanation": "DisplayMember ما يراه المستخدم، و ValueMember القيمة المحفوظة (مثل رقم المدينة)."}
```

```quiz
{"question": "أي عضو يحفظ تعديلات مصدر البيانات في القاعدة؟", "choices": ["`MoveNext`", "`Update`", "`Fill`", "`Position`"], "answer": 1, "explanation": "Update يكتب الإضافات والتعديلات والحذف بأوامر ذات معاملات."}
```

## الخلاصة

- **Data > Show Data Sources** (`Alt+Shift+D`) و **Add New Data Source...**: اتصال ثم جداول أو استعلام.
- اسحب الجدول: **DataGridView** + شريط تنقل، أو **Drop as Details** لعنوان ومربع لكل عمود، والبيانات حقيقية في المصمم.
- `DataSource` و `DataMember` و `DisplayMember` و `ValueMember` في فئة Data.
- الكود المولَّد: `Students.MoveNext` و `Students.Update` و `AddNew` و `RemoveCurrent`، بأوامر ذات معاملات.
