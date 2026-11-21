# الدرس 8: المشروع النهائي: مخزن صغير

**في هذا الدرس:**

- تبني برنامج مخزن يحفظ الأصناف في قاعدة SQLite: إضافة صنف، وبيع قطعة، وتنبيه بالأصناف التي قاربت على النفاد.
- تراجع كل ما تعلمته: الجداول، و SQL، و ADO، والنماذج، وفكرة التقرير.
- تعرف كيف تبني النسخة نفسها بالسحب والإفلات من **Data Sources** ومصمم التقارير.

## التصميم

| الأداة | Name | الوظيفة |
|---|---|---|
| `TextBox` | `txtName` | اسم الصنف الجديد |
| `TextBox` | `txtQty` | الكمية |
| `Button` | `cmdAdd` | "أضف" |
| `ListBox` | `lstItems` | الأصناف بكمياتها |
| `Button` | `cmdSell` | "بيع قطعة" من الصنف المحدد |
| `Button` | `cmdLow` | "قارب على النفاد": تقرير صغير |
| `Label` | `lblReport` | نتيجة التقرير |

## الجدول

```text
CREATE TABLE Items (
    Id   INTEGER PRIMARY KEY,
    Name TEXT NOT NULL UNIQUE,
    Qty  INTEGER NOT NULL DEFAULT 0
)
```

`UNIQUE` تمنع تكرار اسم الصنف، و `DEFAULT 0` قيمة افتراضية.

## البرنامج كاملًا

- `Form_Load` يجهز الجدول ببيانات بداية ويملأ القائمة.
- `RefreshList` يقرأ الأصناف من القاعدة ويعرضها، ونستدعيه بعد كل تغيير.
- `cmdSell_Click` ينفّذ `UPDATE ... SET Qty = Qty - 1` على الصنف المحدد، بشرط أن تكون الكمية أكبر من صفر.
- `cmdLow_Click` "تقرير": الأصناف التي كميتها أقل من 5.

<!-- test: {"steps": [["set", "txtName", "Text", "Ruler"], ["set", "txtQty", "Text", "2"], ["click", "cmdAdd"], ["set", "lstItems", "ListIndex", "0"], ["click", "cmdSell"], ["click", "cmdLow"]], "expect": {"lstItems.ListCount": "3", "lstItems.List(0)": "Bag (3)", "lstItems.List(2)": "Ruler (2)", "lblReport.Caption": "قارب على النفاد: Bag, Ruler", "txtName.Text": ""}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "المخزن"
   ClientWidth     =   6000
   ClientHeight    =   4200
   Begin VB.TextBox txtName
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.TextBox txtQty
      Left            =   2760
      Top             =   240
      Width           =   900
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "أضف"
      Left            =   3840
      Top             =   240
      Width           =   1200
      Height          =   400
   End
   Begin VB.ListBox lstItems
      Left            =   240
      Top             =   840
      Width           =   3420
      Height          =   2400
   End
   Begin VB.CommandButton cmdSell
      Caption         =   "بيع قطعة"
      Left            =   3840
      Top             =   840
      Width           =   1800
      Height          =   400
   End
   Begin VB.CommandButton cmdLow
      Caption         =   "قارب على النفاد"
      Left            =   3840
      Top             =   1440
      Width           =   1800
      Height          =   400
   End
   Begin VB.Label lblReport
      Left            =   240
      Top             =   3420
      Width           =   5400
      Height          =   400
   End
End

Option Explicit
Private cn As Object

Private Sub Form_Load()
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=store.db"
    cn.Execute "DROP TABLE IF EXISTS Items"
    cn.Execute "CREATE TABLE Items (Id INTEGER PRIMARY KEY, Name TEXT NOT NULL UNIQUE, Qty INTEGER NOT NULL DEFAULT 0)"
    cn.Execute "INSERT INTO Items (Name, Qty) VALUES ('Bag', 4)"
    cn.Execute "INSERT INTO Items (Name, Qty) VALUES ('Pen', 50)"
    RefreshList
End Sub

Private Sub RefreshList()
    Dim rs As Object
    lstItems.Clear
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Name, Qty FROM Items ORDER BY Name", cn
    Do While Not rs.EOF
        lstItems.AddItem rs("Name") & " (" & rs("Qty") & ")"
        rs.MoveNext
    Loop
    rs.Close
End Sub

Private Function SelectedName() As String
    Dim s As String
    s = lstItems.List(lstItems.ListIndex)
    SelectedName = Left(s, InStr(s, " (") - 1)
End Function

Private Sub cmdAdd_Click()
    If Trim(txtName.Text) = "" Or Not IsNumeric(txtQty.Text) Then Exit Sub
    cn.Execute "INSERT INTO Items (Name, Qty) VALUES ('" & Replace(Trim(txtName.Text), "'", "''") & "', " & _
               CLng(txtQty.Text) & ")"
    txtName.Text = ""
    txtQty.Text = ""
    RefreshList
End Sub

Private Sub cmdSell_Click()
    If lstItems.ListIndex < 0 Then Exit Sub
    cn.Execute "UPDATE Items SET Qty = Qty - 1 WHERE Name = '" & Replace(SelectedName(), "'", "''") & "' AND Qty > 0"
    RefreshList
End Sub

Private Sub cmdLow_Click()
    Dim rs As Object
    Dim names As String
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT Name FROM Items WHERE Qty < 5 ORDER BY Name", cn
    Do While Not rs.EOF
        If names <> "" Then names = names & ", "
        names = names & rs("Name")
        rs.MoveNext
    Loop
    rs.Close
    If names = "" Then names = "لا شيء"
    lblReport.Caption = "قارب على النفاد: " & names
End Sub
```

### لاحظ

- `Replace(..., "'", "''")` يضاعف علامة التنصيص المفردة داخل الاسم حتى لا تكسر جملة SQL (اسم مثل `Children's Books`). هذا حل بسيط؛ الحل الكامل هو الاستعلامات ذات المعاملات التي يولّدها **Data Sources**.
- `AND Qty > 0` يمنع أن تصبح الكمية سالبة، والقاعدة نفسها تحرس البيانات.
- `RefreshList` بعد كل تغيير يجعل القائمة صورة صادقة لما في القاعدة.

## النسخة "بدون كود"

البرنامج نفسه يمكن بناؤه بأدوات البيئة:

1. شغّل المثال مرة لتصنع `store.db`، أو أنشئ الجدول من **Databases > New Table...**.
2. **Data > Add New Data Source...** > جدول `Items`، واسحبه إلى النموذج: شبكة وشريط تنقل وإضافة وحذف وحفظ.
3. **Configure Data Source...**: ترتيب بـ `Name`.
4. **Project > Add Report...** (في مشروع Python): تقرير "الأصناف القاربة على النفاد" باستعلام `SELECT Name, Qty FROM Items WHERE Qty < :Limit`، ومعامل `Limit`.
5. زر "بيع" هو الوحيد الذي يحتاج سطر كود: `Items.SetValue "Qty", Items.Value("Qty") - 1` ثم `Items.Update`.

## تمرين

### تمرين 1: قيمة المخزن

أضف زرًّا `cmdTotal` يكتب في `lblReport` مجموع القطع في المخزن كله بهذا الشكل: `إجمالي القطع: 54` (حقيبة 4 + قلم 50). استخدم `SELECT SUM(Qty)`.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "المخزن"
   ClientWidth     =   6000
   ClientHeight    =   2000
   Begin VB.Label lblReport
      Left            =   240
      Top             =   1200
      Width           =   5400
      Height          =   400
   End
End

Option Explicit
Private cn As Object

Private Sub Form_Load()
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=store.db"
    cn.Execute "DROP TABLE IF EXISTS Items"
    cn.Execute "CREATE TABLE Items (Id INTEGER PRIMARY KEY, Name TEXT NOT NULL UNIQUE, Qty INTEGER NOT NULL DEFAULT 0)"
    cn.Execute "INSERT INTO Items (Name, Qty) VALUES ('Bag', 4)"
    cn.Execute "INSERT INTO Items (Name, Qty) VALUES ('Pen', 50)"
End Sub

' أضف الزر cmdTotal ومعالجه
```

<!-- test: {"steps": [["click", "cmdTotal"]], "expect": {"lblReport.Caption": "إجمالي القطع: 54"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "المخزن"
   ClientWidth     =   6000
   ClientHeight    =   2000
   Begin VB.CommandButton cmdTotal
      Caption         =   "الإجمالي"
      Left            =   240
      Top             =   240
      Width           =   1800
      Height          =   400
   End
   Begin VB.Label lblReport
      Left            =   240
      Top             =   1200
      Width           =   5400
      Height          =   400
   End
End

Option Explicit
Private cn As Object

Private Sub Form_Load()
    Set cn = CreateObject("ADODB.Connection")
    cn.Open "Driver=SQLite;Data Source=store.db"
    cn.Execute "DROP TABLE IF EXISTS Items"
    cn.Execute "CREATE TABLE Items (Id INTEGER PRIMARY KEY, Name TEXT NOT NULL UNIQUE, Qty INTEGER NOT NULL DEFAULT 0)"
    cn.Execute "INSERT INTO Items (Name, Qty) VALUES ('Bag', 4)"
    cn.Execute "INSERT INTO Items (Name, Qty) VALUES ('Pen', 50)"
End Sub

Private Sub cmdTotal_Click()
    Dim rs As Object
    Set rs = CreateObject("ADODB.Recordset")
    rs.Open "SELECT SUM(Qty) AS T FROM Items", cn
    lblReport.Caption = "إجمالي القطع: " & rs("T")
    rs.Close
End Sub
```

## اختبر نفسك

```quiz
{"question": "لماذا كتبنا `AND Qty > 0` في جملة البيع؟", "choices": ["لتسريع الاستعلام", "حتى لا تصبح الكمية سالبة", "لأن SQL يشترطه", "لحذف الصنف"], "answer": 1, "explanation": "الشرط يجعل القاعدة ترفض البيع عندما تكون الكمية صفرًا."}
```

```quiz
{"question": "ما فائدة `UNIQUE` على عمود `Name`؟", "choices": ["ترتيب الأسماء", "منع تكرار اسم الصنف", "تحويل الأسماء لحروف كبيرة", "لا فائدة"], "answer": 1, "explanation": "UNIQUE تجعل القاعدة ترفض إضافة صنف باسم موجود."}
```

```quiz
{"question": "ما الحل الأكمل لمشكلة علامات التنصيص وحقن SQL في الأسماء التي يكتبها المستخدم؟", "choices": ["حذف علامات التنصيص يدويًا", "الاستعلامات ذات المعاملات، كما يولّدها Data Sources", "كتابة الأسماء بالإنجليزية فقط", "عدم استخدام SQL"], "answer": 1, "explanation": "المعاملات ترسل القيمة منفصلة عن نص الاستعلام. Replace مع '' حل مؤقت فقط."}
```

## الخلاصة

- بنيت مخزنًا حقيقيًا: جدول بقيود (`NOT NULL` و `UNIQUE` و `DEFAULT`)، وإضافة، وبيع بـ `UPDATE` آمن، وتقرير صغير بـ `WHERE Qty < 5`.
- `RefreshList` بعد كل تغيير يبقي الواجهة صادقة.
- النسخة الاحترافية بأدوات البيئة: **Databases** للجدول، و **Data Sources** للنموذج، و **Add Report...** للتقرير.
- أنهيت دليل البيانات والتقارير. التالي: **دليل التصحيح والاختبار** لتعرف كيف تجد الأخطاء في برامج مثل هذا.
