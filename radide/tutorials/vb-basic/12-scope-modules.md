# الدرس 12: نطاق المتغيرات والوحدات

**في هذا الدرس ستتعلم:**

- **النطاق** (Scope): من يستطيع رؤية المتغير؟
- المتغير المحلي، ومتغير مستوى الوحدة (`Private`)، والمتغير العام (`Public`).
- المتغير الساكن `Static` الذي يحتفظ بقيمته.
- تقسيم البرنامج إلى عدة **وحدات** (Modules).

## الغرف والبيت والمدينة

تخيّل أن المتغيرات أشياء في بيت:

- **محلي** (Local): شيء داخل غرفتك (داخل إجراء واحد). لا يراه أحد خارج الغرفة، ويختفي عندما تخرج منها (عند انتهاء الإجراء).
- **مستوى الوحدة** (`Private` أو `Dim` في أعلى الملف): شيء في صالة البيت. كل الغرف (كل إجراءات هذا الملف) تراه.
- **عام** (`Public`): شيء في ميدان المدينة. كل البيوت (كل ملفات المشروع) تراه.

## المتغير المحلي

المتغير المُعلن بـ `Dim` داخل إجراء يعيش فقط داخل هذا الإجراء. يمكن لإجراءين أن يستخدما الاسم نفسه دون أي تعارض، تمامًا كما يكون في كل غرفة "سرير" خاص بها:

```vb run
Sub Main()
    Dim x As Integer
    x = 1
    ChangeX
    Debug.Print "x في Main = " & x
End Sub

Sub ChangeX()
    Dim x As Integer      ' متغير آخر تمامًا بالاسم نفسه
    x = 99
    Debug.Print "x في ChangeX = " & x
End Sub
```

```text output
x في ChangeX = 99
x في Main = 1
```

## متغير مستوى الوحدة

إذا أعلنت عن المتغير **أعلى الملف** (خارج أي إجراء) يصبح مشتركًا بين كل إجراءات الملف. نستخدم `Private` (أو `Dim`) لذلك:

```vb run
Option Explicit
Private counter As Integer     ' تراه كل إجراءات هذا الملف

Sub Main()
    AddVisitor
    AddVisitor
    AddVisitor
    Debug.Print "عدد الزوار: " & counter
End Sub

Sub AddVisitor()
    counter = counter + 1
End Sub
```

```text output
عدد الزوار: 3
```

وهذا مهم جدًّا في النماذج: المتغير المعلن أعلى كود النموذج يحتفظ بقيمته بين نقرة وأخرى، بينما المتغير المحلي داخل `cmdCount_Click` يبدأ من الصفر في كل نقرة:

<!-- test: {"steps": [["click", "cmdCount"], ["click", "cmdCount"], ["click", "cmdCount"]], "expect": {"lblCount.Caption": "عدد النقرات: 3", "lblLocal.Caption": "المحلي: 1"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "عدّاد النقرات"
   ClientWidth     =   4200
   ClientHeight    =   2200
   Begin VB.CommandButton cmdCount
      Caption         =   "انقر هنا"
      Left            =   1200
      Top             =   200
      Width           =   1800
      Height          =   500
   End
   Begin VB.Label lblCount
      Caption         =   "عدد النقرات: 0"
      Left            =   240
      Top             =   900
      Width           =   3600
      Height          =   400
   End
   Begin VB.Label lblLocal
      Left            =   240
      Top             =   1400
      Width           =   3600
      Height          =   400
   End
End

Option Explicit
Private clicks As Integer           ' مستوى النموذج: يحتفظ بقيمته

Private Sub cmdCount_Click()
    Dim localClicks As Integer      ' محلي: يبدأ من 0 كل مرة
    clicks = clicks + 1
    localClicks = localClicks + 1
    lblCount.Caption = "عدد النقرات: " & clicks
    lblLocal.Caption = "المحلي: " & localClicks
End Sub
```

## Static: محلي لكن بذاكرة

`Static` بدل `Dim` داخل إجراء: المتغير يبقى **محليًّا** (لا يراه غير هذا الإجراء) لكنه **يحتفظ بقيمته** بين الاستدعاءات، مثل درج مقفول في غرفتك لا يُفرغ عند خروجك:

```vb run
Sub Main()
    Dim i As Integer
    For i = 1 To 3
        NextTicket
    Next i
End Sub

Sub NextTicket()
    Static number As Integer
    number = number + 1
    Debug.Print "تذكرة رقم " & number
End Sub
```

```text output
تذكرة رقم 1
تذكرة رقم 2
تذكرة رقم 3
```

## عدة وحدات في مشروع واحد

المشروع الكبير يُقسَّم إلى ملفات، مثل تقسيم كتاب إلى فصول: وحدة للحسابات، ووحدة للنصوص، وهكذا. أضف وحدة جديدة من قائمة **Project** ثم **Add Module...**.

- ما يُعلن بـ `Public` في وحدة يمكن استخدامه من أي وحدة أو نموذج آخر.
- ما يُعلن بـ `Private` يبقى داخل ملفه.
- يمكن كتابة اسم الوحدة قبل اسم الإجراء لتوضيح مصدره: `MathTools.Square(4)`.

في المثال التالي ملفان: `Module1.bas` و`MathTools.bas`. (سطر `'#file:` يوضح للمُشغّل اسم كل ملف، وعند الضغط على **جرّبه** ستجد الملفين في مستكشف الحل.)

```vb run
'#file: Module1.bas
Option Explicit

Sub Main()
    Debug.Print "مربع 7 = " & Square(7)
    Debug.Print "مكعب 3 = " & MathTools.Cube(3)
    Debug.Print "ثابت عام: " & APP_NAME
    CallCount = CallCount + 1
    Debug.Print "عدد الاستدعاءات = " & CallCount
End Sub

'#file: MathTools.bas
Option Explicit

Public Const APP_NAME As String = "حاسبتي"
Public CallCount As Integer

Public Function Square(ByVal n As Double) As Double
    Square = n * n
End Function

Public Function Cube(ByVal n As Double) As Double
    Cube = n * Square(n)
End Function

Private Sub HiddenHelper()
    ' Private: لا يمكن استدعاؤه من Module1
End Sub
```

```text output
مربع 7 = 49
مكعب 3 = 27
ثابت عام: حاسبتي
عدد الاستدعاءات = 1
```

## أي نطاق أختار؟

اختر **أضيق نطاق ممكن**. المتغيرات العامة مثل الأغراض في ميدان المدينة: أي أحد يمكن أن يغيّرها، وعندما يحدث خطأ يصعب معرفة من غيّرها.

| أين أُعلن؟ | الكلمة | من يراه؟ | متى يختفي؟ |
|---|---|---|---|
| داخل إجراء | `Dim` | هذا الإجراء فقط | عند انتهاء الإجراء |
| داخل إجراء | `Static` | هذا الإجراء فقط | عند انتهاء البرنامج |
| أعلى الملف | `Private` / `Dim` | كل إجراءات الملف | عند انتهاء البرنامج |
| أعلى وحدة | `Public` | كل المشروع | عند انتهاء البرنامج |

## أخطاء شائعة

- **إعلان متغير محلي بنفس اسم متغير الوحدة:** المحلي "يغطي" على متغير الوحدة داخل الإجراء، فتعدّل المحلي وتظن أنك عدّلت الآخر.
- **عدّاد داخل الإجراء بـ `Dim`:** يبدأ من الصفر كل مرة. استخدم متغير مستوى الوحدة أو `Static`.
- **استدعاء إجراء `Private` من ملف آخر:** خطأ "Sub or Function not defined".
- **الإكثار من `Public`:** يجعل البرنامج صعب الفهم والتصحيح.

## تمارين

### تمرين 1: رصيد الحصّالة

باستخدام متغير مستوى الوحدة `balance`، اكتب إجراءين `Deposit(amount)` و`Withdraw(amount)`. نفّذ: إيداع 100، إيداع 50، سحب 30، ثم اطبع الرصيد.

```vb exercise
Option Explicit
Private balance As Long

Sub Main()
    Deposit 100
    Deposit 50
    Withdraw 30
    Debug.Print "الرصيد: " & balance
End Sub
```

```vb solution
Option Explicit
Private balance As Long

Sub Main()
    Deposit 100
    Deposit 50
    Withdraw 30
    Debug.Print "الرصيد: " & balance
End Sub

Sub Deposit(ByVal amount As Long)
    balance = balance + amount
End Sub

Sub Withdraw(ByVal amount As Long)
    If amount <= balance Then balance = balance - amount
End Sub
```

```text output
الرصيد: 120
```

### تمرين 2: مولّد أرقام بـ Static

اكتب دالة `NextId()` تستخدم متغيرًا `Static` وتُرجع 101 ثم 102 ثم 103 في كل استدعاء.

```vb exercise
Sub Main()
    Debug.Print NextId()
    Debug.Print NextId()
    Debug.Print NextId()
End Sub
```

```vb solution
Sub Main()
    Debug.Print NextId()
    Debug.Print NextId()
    Debug.Print NextId()
End Sub

Function NextId() As Long
    Static lastId As Long
    If lastId = 0 Then lastId = 100
    lastId = lastId + 1
    NextId = lastId
End Function
```

```text output
101
102
103
```

### تمرين 3: وحدة للنصوص

أنشئ وحدة `TextTools.bas` فيها دالة عامة `Shout(s)` تُرجع النص بحروف كبيرة وبعده "!"، واستدعها من `Main` في `Module1.bas`.

```vb exercise
'#file: Module1.bas
Sub Main()
    Debug.Print Shout("hello")
End Sub

'#file: TextTools.bas
' اكتب الدالة Shout هنا
```

```vb solution
'#file: Module1.bas
Sub Main()
    Debug.Print Shout("hello")
End Sub

'#file: TextTools.bas
Public Function Shout(ByVal s As String) As String
    Shout = UCase(s) & "!"
End Function
```

```text output
HELLO!
```

## اختبر نفسك

```quiz
{"question": "متغير أُعلن بـ Dim داخل إجراء. من يراه؟", "choices": ["كل المشروع", "كل إجراءات الملف", "هذا الإجراء فقط", "النماذج فقط"], "answer": 2, "explanation": "المتغير المحلي يُرى داخل الإجراء الذي أُعلن فيه فقط."}
```

```quiz
{"question": "ما فائدة Static؟", "choices": ["تجعل المتغير عامًّا", "تجعل المتغير المحلي يحتفظ بقيمته بين الاستدعاءات", "تمنع تغيير المتغير", "تحذف المتغير"], "answer": 1, "explanation": "Static متغير محلي لا تضيع قيمته عند انتهاء الإجراء."}
```

```quiz
{"question": "كيف تجعل دالة في وحدة قابلة للاستدعاء من وحدة أخرى؟", "choices": ["Private Function", "Public Function", "Static Function", "Dim Function"], "answer": 1, "explanation": "Public تجعل الدالة مرئية في كل المشروع."}
```

```quiz
{"question": "عدّاد نقرات داخل cmdOK_Click أُعلن بـ Dim يظهر دائمًا 1. لماذا؟", "choices": ["خطأ في الزر", "المتغير المحلي يبدأ من الصفر في كل نقرة", "يجب استخدام Integer", "Click لا يعمل مرتين"], "answer": 1, "explanation": "انقل الإعلان إلى أعلى النموذج أو استخدم Static."}
```

## الخلاصة

- المحلي داخل الإجراء، و`Private` للملف، و`Public` للمشروع كله.
- `Static` متغير محلي بذاكرة دائمة.
- قسّم البرنامج إلى وحدات، واختر دائمًا أضيق نطاق ممكن.
