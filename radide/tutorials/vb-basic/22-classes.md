# الدرس 22: الأصناف - Class Modules

**في هذا الدرس ستتعلم:**

- ما هو **الصنف** (Class) و**الكائن** (Object).
- كتابة وحدة صنف (`.cls`) فيها حقول خاصة ودوال.
- **الخصائص** بـ `Property Get` و`Property Let` لحماية البيانات.
- الحدث `Class_Initialize`، وإنشاء الكائنات بـ `New` و`Set`.
- إطلاق أحداث من الصنف بـ `Event` و`RaiseEvent` واستقبالها بـ `WithEvents`.

## القالب والكعكة

**الصنف** مثل **قالب الكعك**: قالب واحد تصنع به كعكات كثيرة. كل **كعكة** هي **كائن** (Object)، أي نسخة حقيقية صُنعت من القالب، ويمكن أن تختلف كل كعكة عن الأخرى في الحشوة أو اللون.
في الدرس 20 جمعنا البيانات في `Type`. الصنف يجمع **البيانات** و**الأفعال** معًا: حساب البنك فيه **رصيد** (بيانات)، ويمكنه أن **يودِع** و**يسحب** (أفعال)، ويمنع السحب أكثر من الرصيد (حماية).

## أول صنف

الصنف يُكتب في ملف مستقل امتداده `.cls`، واسم الملف هو اسم الصنف. في الأمثلة نستخدم سطر `'#file:` لتحديد الملفات، وزر **جرّبه** يُنشئ الملفين.
(في مشروعك: أنشئ ملفًا نصيًّا باسم `CPerson.cls` في مجلد المشروع، ثم أضِفه من قائمة **Project** ثم **Add Existing Item...**.)

```vb run
'#file: Module1.bas
Sub Main()
    Dim p As CPerson
    Set p = New CPerson          ' اصنع كائنًا من الفئة
    p.FirstName = "Nour"
    p.BirthYear = 2005
    Debug.Print p.Greeting()
    Debug.Print "العمر في 2025: " & p.AgeIn(2025)
End Sub

'#file: CPerson.cls
Option Explicit

Public FirstName As String
Public BirthYear As Integer

Public Function Greeting() As String
    Greeting = "Hello, I am " & FirstName
End Function

Public Function AgeIn(ByVal year As Integer) As Integer
    AgeIn = year - BirthYear
End Function
```

```text output
Hello, I am Nour
العمر في 2025: 20
```

- `Dim p As CPerson` تُعلن متغيرًا يمكنه أن يشير إلى كائن من نوع `CPerson`.
- `Set p = New CPerson` **تصنع** الكائن فعلًا. مع الكائنات نستخدم `Set` في الإسناد.
- المتغيرات `Public` في الصنف تصبح خصائص، والدوال `Public` تصبح **دوالّ الكائن** (Methods، وتُسمّى أيضًا «طرقًا»).

## صناعة عدة كائنات

كل كائن له نسخته الخاصة من البيانات، مثل كل كعكة لها حشوتها:

```vb run
'#file: Module1.bas
Sub Main()
    Dim a As New CCounter, b As New CCounter
    a.Increase
    a.Increase
    a.Increase
    b.Increase
    Debug.Print "a = " & a.Value
    Debug.Print "b = " & b.Value
End Sub

'#file: CCounter.cls
Option Explicit
Private mValue As Long

Public Sub Increase()
    mValue = mValue + 1
End Sub

Public Function Value() As Long
    Value = mValue
End Function
```

```text output
a = 3
b = 1
```

`Dim a As New CCounter` اختصار يُعلن المتغير ويصنع الكائن معًا.

## الحماية: `Property Get` و `Property Let`

لو كان الرصيد `Public` لاستطاع أي جزء من البرنامج أن يكتب `acc.Balance = -1000000`! الحل: نجعل البيانات **`Private`** ونفتح لها **بوّابة** تتحقق من القيم:

- `Property Get` تُنفَّذ عند **قراءة** الخاصية.
- `Property Let` تُنفَّذ عند **الكتابة** فيها، ويمكنها رفض القيم الخاطئة.
- إذا كتبت `Property Get` فقط تصبح الخاصية **للقراءة فقط**.

```vb run
'#file: Module1.bas
Sub Main()
    Dim acc As New CAccount
    acc.Owner = "Salma"
    acc.Deposit 500
    acc.Withdraw 200
    acc.Withdraw 1000
    Debug.Print acc.Owner & ": " & acc.Balance
End Sub

'#file: CAccount.cls
Option Explicit
Private mOwner As String
Private mBalance As Double

Public Property Get Owner() As String
    Owner = mOwner
End Property

Public Property Let Owner(ByVal value As String)
    If Trim(value) = "" Then Err.Raise 5, "CAccount", "اسم المالك مطلوب"
    mOwner = value
End Property

Public Property Get Balance() As Double      ' قراءة فقط: لا توجد Property Let
    Balance = mBalance
End Property

Public Sub Deposit(ByVal amount As Double)
    If amount > 0 Then mBalance = mBalance + amount
End Sub

Public Sub Withdraw(ByVal amount As Double)
    If amount > mBalance Then
        Debug.Print "الرصيد لا يكفي لسحب " & amount
    Else
        mBalance = mBalance - amount
    End If
End Sub
```

```text output
الرصيد لا يكفي لسحب 1000
Salma: 300
```

هذا المبدأ اسمه **التغليف** (Encapsulation): البيانات محفوظة داخل الكائن، ولا تتغير إلا عبر طرقه.

## `Class_Initialize`: لحظة الميلاد

الإجراء `Class_Initialize` يُنفَّذ تلقائيًّا لحظة صناعة الكائن، وهو مكان مناسب للقيم الابتدائية:

```vb run
'#file: Module1.bas
Sub Main()
    Dim t As New CTicket
    Debug.Print t.Describe()
    t.Seat = "B7"
    Debug.Print t.Describe()
End Sub

'#file: CTicket.cls
Option Explicit
Public Seat As String
Private mPrice As Double

Private Sub Class_Initialize()
    Seat = "غير محدد"
    mPrice = 120
End Sub

Public Function Describe() As String
    Describe = "مقعد: " & Seat & " - السعر: " & mPrice
End Function
```

```text output
مقعد: غير محدد - السعر: 120
مقعد: B7 - السعر: 120
```

## مجموعة من الكائنات

الكائنات والمجموعات (الدرس 21) يعملان معًا بشكل رائع:

```vb run
'#file: Module1.bas
Sub Main()
    Dim cart As New Collection, item As CItem, total As Double

    Set item = New CItem
    item.Init "Pen", 5, 4
    cart.Add item

    Set item = New CItem
    item.Init "Book", 80, 1
    cart.Add item

    For Each item In cart
        Debug.Print item.Title & ": " & item.Total
        total = total + item.Total
    Next item
    Debug.Print "الإجمالي: " & total
End Sub

'#file: CItem.cls
Option Explicit
Public Title As String
Public Price As Double
Public Qty As Integer

Public Sub Init(ByVal t As String, ByVal p As Double, ByVal q As Integer)
    Title = t
    Price = p
    Qty = q
End Sub

Public Function Total() As Double
    Total = Price * Qty
End Function
```

```text output
Pen: 20
Book: 80
الإجمالي: 100
```

لاحظ أننا كتبنا `Set item = New CItem` قبل كل إضافة؛ لو لم نصنع كائنًا جديدًا لأضفنا الكائن نفسه مرتين.

## الأحداث: الكائن يتكلم

الصنف يمكنه أن يُطلق **أحداثًا** مثل الأدوات. نُعلن الحدث بـ `Event`، ونطلقه بـ `RaiseEvent`. ومن يريد سماعه يعلن المتغير بـ `WithEvents` ويكتب إجراءً باسم `المتغير_الحدث`:

```vb run
'#file: Module1.bas
Private WithEvents tank As CTank

Sub Main()
    Set tank = New CTank
    tank.Fill 40
    tank.Fill 50
    tank.Fill 30
End Sub

Private Sub tank_Full(ByVal extra As Double)
    Debug.Print "تنبيه: الخزان امتلأ! فاض " & extra & " لتر"
End Sub

'#file: CTank.cls
Option Explicit
Public Event Full(ByVal extra As Double)
Private mLevel As Double
Private Const CAPACITY As Double = 100

Public Sub Fill(ByVal liters As Double)
    mLevel = mLevel + liters
    If mLevel > CAPACITY Then
        RaiseEvent Full(mLevel - CAPACITY)
        mLevel = CAPACITY
    End If
    Debug.Print "المستوى الآن: " & mLevel
End Sub
```

```text output
المستوى الآن: 40
المستوى الآن: 90
تنبيه: الخزان امتلأ! فاض 20 لتر
المستوى الآن: 100
```

`WithEvents` تُكتب على مستوى الوحدة (أعلى الملف)، وليس داخل إجراء.

## أخطاء شائعة

- **نسيان `Set` مع الكائنات:** `p = New CPerson` خطأ؛ الصحيح `Set p = New CPerson`.
- **استخدام المتغير قبل صناعة الكائن:** `Dim p As CPerson` ثم `p.FirstName = "x"` تعطي الخطأ 91 "Object variable not set".
- **جعل كل البيانات `Public`:** تفقد الحماية. اجعلها `Private` مع `Property`.
- **اسم الملف غير اسم الصنف:** الصنف اسمه اسم ملفه: `CPerson.cls` تعني `New CPerson`.
- **إضافة الكائن نفسه للمجموعة عدة مرات:** اصنع كائنًا جديدًا بـ `New` لكل عنصر.

## تمارين

### تمرين 1: صنف المستطيل

اكتب الصنف `CRectangle` فيها `Width` و`Height` ودالتان `Area` و`Perimeter`. أنشئ مستطيلًا 5 × 3 واطبع مساحته ومحيطه.

```vb exercise
'#file: Module1.bas
Sub Main()
    Dim r As New CRectangle
    r.Width = 5
    r.Height = 3
    Debug.Print "المساحة = " & r.Area
    Debug.Print "المحيط = " & r.Perimeter
End Sub

'#file: CRectangle.cls
' اكتب الفئة هنا
```

```vb solution
'#file: Module1.bas
Sub Main()
    Dim r As New CRectangle
    r.Width = 5
    r.Height = 3
    Debug.Print "المساحة = " & r.Area
    Debug.Print "المحيط = " & r.Perimeter
End Sub

'#file: CRectangle.cls
Option Explicit
Public Width As Double
Public Height As Double

Public Function Area() As Double
    Area = Width * Height
End Function

Public Function Perimeter() As Double
    Perimeter = 2 * (Width + Height)
End Function
```

```text output
المساحة = 15
المحيط = 16
```

### تمرين 2: درجة محمية

اكتب الصنف `CStudent` فيها خاصية `Mark` محمية بـ `Property Let`: تقبل فقط القيم من 0 إلى 100، وتتجاهل غيرها. جرّب `Mark = 85` ثم `Mark = 150` واطبع الدرجة.

```vb exercise
'#file: Module1.bas
Sub Main()
    Dim s As New CStudent
    s.Mark = 85
    s.Mark = 150
    Debug.Print "الدرجة = " & s.Mark
End Sub

'#file: CStudent.cls
Option Explicit
Private mMark As Integer
```

```vb solution
'#file: Module1.bas
Sub Main()
    Dim s As New CStudent
    s.Mark = 85
    s.Mark = 150
    Debug.Print "الدرجة = " & s.Mark
End Sub

'#file: CStudent.cls
Option Explicit
Private mMark As Integer

Public Property Get Mark() As Integer
    Mark = mMark
End Property

Public Property Let Mark(ByVal value As Integer)
    If value >= 0 And value <= 100 Then mMark = value
End Property
```

```text output
الدرجة = 85
```

## اختبر نفسك

```quiz
{"question": "ما العلاقة بين الصنف والكائن؟", "choices": ["لا علاقة", "الصنف قالب، والكائن نسخة مصنوعة منه", "الكائن قالب، والصنف نسخة منه", "هما اسمان لشيء واحد"], "answer": 1, "explanation": "الصنف مثل قالب الكعك، وكل كائن كعكة مصنوعة منه."}
```

```quiz
{"question": "أي سطر يصنع كائنًا جديدًا بشكل صحيح؟", "choices": ["p = New CPerson", "Set p = New CPerson", "Dim p = CPerson", "New p As CPerson"], "answer": 1, "explanation": "الإسناد إلى متغيرات الكائنات يكون بـ Set."}
```

```quiz
{"question": "خاصية لها Property Get فقط بلا Property Let. ماذا يعني ذلك؟", "choices": ["خطأ", "الخاصية للقراءة فقط", "الخاصية للكتابة فقط", "الخاصية مخفية"], "answer": 1, "explanation": "بدون Property Let لا يمكن الكتابة في الخاصية من خارج الصنف."}
```

```quiz
{"question": "متى يُنفَّذ Class_Initialize؟", "choices": ["عند إغلاق البرنامج", "لحظة صناعة الكائن", "عند كل استدعاء طريقة", "لا يُنفَّذ تلقائيًّا"], "answer": 1, "explanation": "Class_Initialize يُنفَّذ تلقائيًّا عند إنشاء الكائن بـ New."}
```

```quiz
{"question": "كيف يستقبل البرنامج أحداث كائن؟", "choices": ["بإعلان المتغير بـ WithEvents على مستوى الوحدة", "بـ On Error", "بـ Static", "بـ ReDim"], "answer": 0, "explanation": "Private WithEvents x As CClass ثم إجراء باسم x_EventName."}
```

## الخلاصة

- الصنف (`.cls`) قالب، والكائن نسخة منه تُصنع بـ `New` وتُسند بـ `Set`.
- البيانات `Private`، والوصول عبر `Property Get`/`Property Let` (التغليف).
- `Class_Initialize` للقيم الابتدائية، و`Event`/`RaiseEvent`/`WithEvents` للأحداث.
