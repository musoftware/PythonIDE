# الدرس 16: مصفوفات الأدوات

**في هذا الدرس ستتعلم:**

- ما هي **مصفوفة الأدوات** (Control Array) ولماذا هي مفيدة.
- كيف تنشئها في المصمّم بالخاصية `Index`.
- إجراء حدث واحد لكل العناصر بالمعامل `Index As Integer`.
- المرور على عناصرها بحلقة باستخدام `LBound` و`UBound` و`Count`.

## فريق بقمصان مرقّمة

في فريق كرة القدم، كل اللاعبين يلبسون القميص نفسه، والفرق الوحيد هو **الرقم** على الظهر. المدرب يستطيع أن يقول "اللاعب رقم 7، تقدّم!".
**مصفوفة الأدوات** مجموعة أدوات من النوع نفسه لها **الاسم نفسه**، ويميّزها **رقم** في الخاصية `Index`: `cmdDigit(0)` و`cmdDigit(1)` و`cmdDigit(2)`...

الفائدة الكبرى: **إجراء حدث واحد** لكل الأزرار بدل عشرة إجراءات متشابهة!

## كيف تنشئها؟

مصفوفة الأدوات تُوصف في ملف النموذج (`.frm`): عدة أدوات بـ**الاسم نفسه**، ولكل منها `Index` مختلف (0، 1، 2...). هكذا تمامًا تراها في أمثلة هذا الدرس، وزر **جرّبه** يبني منها النموذج.
وعندما تفتح في RAD IDE مشروع فيجوال بيسك 6 قديمًا (`.vbp`) أو تستورد نموذجًا (`.frm`) فيه مصفوفات أدوات، تبقى المصفوفات كما هي ويعمل إجراء الحدث المشترك.

## إجراء واحد للجميع

يصل رقم الأداة التي ضُغطت في المعامل `Index`:

<!-- test: {"steps": [["click", "cmdDigit", 3], ["click", "cmdDigit", 1], ["click", "cmdDigit", 2]], "expect": {"lblDisplay.Caption": "312"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "لوحة الأرقام"
   ClientWidth     =   4200
   ClientHeight    =   2000
   Begin VB.Label lblDisplay
      Alignment       =   1  'Right
      Left            =   240
      Top             =   240
      Width           =   3600
      Height          =   400
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "0"
      Index           =   0
      Left            =   240
      Top             =   900
      Width           =   800
      Height          =   600
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "1"
      Index           =   1
      Left            =   1160
      Top             =   900
      Width           =   800
      Height          =   600
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "2"
      Index           =   2
      Left            =   2080
      Top             =   900
      Width           =   800
      Height          =   600
   End
   Begin VB.CommandButton cmdDigit
      Caption         =   "3"
      Index           =   3
      Left            =   3000
      Top             =   900
      Width           =   800
      Height          =   600
   End
End

Private Sub cmdDigit_Click(Index As Integer)
    lblDisplay.Caption = lblDisplay.Caption & cmdDigit(Index).Caption
End Sub
```

`cmdDigit(Index).Caption` تعني: "نص الزر الذي رقمه `Index`"، أي الزر المضغوط نفسه.

## `Select Case` مع `Index`

عندما تختلف وظيفة كل عنصر نستخدم `Select Case Index`. هذه آلة حاسبة بأزرار عمليات في مصفوفة واحدة:

<!-- test: {"steps": [["set", "txtA", "Text", "8"], ["set", "txtB", "Text", "2"], ["click", "cmdOp", 2]], "expect": {"lblResult.Caption": "16"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "حاسبة بمصفوفة أدوات"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.TextBox txtA
      Left            =   240
      Top             =   240
      Width           =   1800
      Height          =   400
   End
   Begin VB.TextBox txtB
      Left            =   2400
      Top             =   240
      Width           =   1800
      Height          =   400
   End
   Begin VB.CommandButton cmdOp
      Caption         =   "+"
      Index           =   0
      Left            =   240
      Top             =   900
      Width           =   900
      Height          =   500
   End
   Begin VB.CommandButton cmdOp
      Caption         =   "-"
      Index           =   1
      Left            =   1300
      Top             =   900
      Width           =   900
      Height          =   500
   End
   Begin VB.CommandButton cmdOp
      Caption         =   "×"
      Index           =   2
      Left            =   2360
      Top             =   900
      Width           =   900
      Height          =   500
   End
   Begin VB.CommandButton cmdOp
      Caption         =   "÷"
      Index           =   3
      Left            =   3420
      Top             =   900
      Width           =   900
      Height          =   500
   End
   Begin VB.Label lblResult
      Left            =   240
      Top             =   1700
      Width           =   4200
      Height          =   400
   End
End

Option Explicit

Private Sub cmdOp_Click(Index As Integer)
    Dim a As Double, b As Double
    a = Val(txtA.Text)
    b = Val(txtB.Text)
    Select Case Index
        Case 0: lblResult.Caption = a + b
        Case 1: lblResult.Caption = a - b
        Case 2: lblResult.Caption = a * b
        Case 3
            If b = 0 Then
                lblResult.Caption = "خطأ: قسمة على صفر"
            Else
                lblResult.Caption = a / b
            End If
    End Select
End Sub
```

قارن هذا بالدرس 13: هناك كتبنا أربعة إجراءات، وهنا إجراء واحد.

## المرور على العناصر بحلقة

مصفوفة الأدوات لها `LBound` (أول رقم) و`UBound` (آخر رقم) و`Count` (العدد)، فنستطيع المرور عليها بحلقة `For`. مثال: أزرار خيار للألوان، وزر يكتشف أيها محدد:

<!-- test: {"steps": [["set", "optColor_1", "Value", "True"], ["click", "cmdWhich"]], "expect": {"lblChoice.Caption": "اللون المختار: أخضر"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الألوان"
   ClientWidth     =   4800
   ClientHeight    =   2600
   Begin VB.OptionButton optColor
      Caption         =   "أحمر"
      Index           =   0
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   400
   End
   Begin VB.OptionButton optColor
      Caption         =   "أخضر"
      Index           =   1
      Left            =   240
      Top             =   700
      Width           =   2000
      Height          =   400
   End
   Begin VB.OptionButton optColor
      Caption         =   "أزرق"
      Index           =   2
      Left            =   240
      Top             =   1160
      Width           =   2000
      Height          =   400
      Value           =   -1  'True
   End
   Begin VB.CommandButton cmdWhich
      Caption         =   "أيها المختار؟"
      Left            =   2600
      Top             =   240
      Width           =   1800
      Height          =   500
   End
   Begin VB.Label lblChoice
      Left            =   240
      Top             =   1800
      Width           =   4200
      Height          =   400
   End
End

Option Explicit

Private Sub cmdWhich_Click()
    Dim i As Integer
    For i = optColor.LBound To optColor.UBound
        If optColor(i).Value Then
            lblChoice.Caption = "اللون المختار: " & optColor(i).Caption
        End If
    Next i
End Sub

Private Sub optColor_Click(Index As Integer)
    Select Case Index
        Case 0: Me.BackColor = vbRed
        Case 1: Me.BackColor = vbGreen
        Case 2: Me.BackColor = vbBlue
    End Select
End Sub
```

(فيجوال بيسك 6 الأصلي يسمح أيضًا بإنشاء عناصر جديدة أثناء التشغيل بالأمر `Load`، لكننا في هذا الدرس نكتفي بالعناصر المرسومة وقت التصميم.)

## أخطاء شائعة

- **نسيان المعامل `Index As Integer`** في إجراء الحدث: الإجراء الصحيح `cmdDigit_Click(Index As Integer)`.
- **كتابة `cmdDigit.Caption`** بدون رقم: يجب تحديد العنصر `cmdDigit(Index).Caption`.
- **أرقام `Index` غير متتالية:** إذا كانت 0 و1 و5 فإن الحلقة من `LBound` إلى `UBound` ستطلب العنصر 2 غير الموجود. اجعل الأرقام متتالية.
- **الخلط بين مصفوفة الأدوات ومصفوفة المتغيرات:** الأولى أدوات على النموذج لها `Index`، والثانية متغيرات في الذاكرة بـ `Dim a(5)`.

## تمارين

### تمرين 1: أزرار الأسئلة

نموذج فيه سؤال "ما عاصمة مصر؟" وثلاثة أزرار في مصفوفة `cmdAnswer`: الإسكندرية (0)، القاهرة (1)، أسوان (2). عند الضغط يكتب `lblResult` "إجابة صحيحة" للزر 1، و"حاول مرة أخرى" لغيره.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "سؤال"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.Label lblQuestion
      Caption         =   "ما عاصمة مصر؟"
      Left            =   240
      Top             =   240
      Width           =   4200
      Height          =   400
   End
   Begin VB.CommandButton cmdAnswer
      Caption         =   "الإسكندرية"
      Index           =   0
      Left            =   240
      Top             =   800
      Width           =   1400
      Height          =   500
   End
   Begin VB.CommandButton cmdAnswer
      Caption         =   "القاهرة"
      Index           =   1
      Left            =   1700
      Top             =   800
      Width           =   1400
      Height          =   500
   End
   Begin VB.CommandButton cmdAnswer
      Caption         =   "أسوان"
      Index           =   2
      Left            =   3160
      Top             =   800
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblResult
      Left            =   240
      Top             =   1600
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdAnswer_Click(Index As Integer)

End Sub
```

<!-- test: {"steps": [["click", "cmdAnswer", 1]], "expect": {"lblResult.Caption": "إجابة صحيحة"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "سؤال"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.Label lblQuestion
      Caption         =   "ما عاصمة مصر؟"
      Left            =   240
      Top             =   240
      Width           =   4200
      Height          =   400
   End
   Begin VB.CommandButton cmdAnswer
      Caption         =   "الإسكندرية"
      Index           =   0
      Left            =   240
      Top             =   800
      Width           =   1400
      Height          =   500
   End
   Begin VB.CommandButton cmdAnswer
      Caption         =   "القاهرة"
      Index           =   1
      Left            =   1700
      Top             =   800
      Width           =   1400
      Height          =   500
   End
   Begin VB.CommandButton cmdAnswer
      Caption         =   "أسوان"
      Index           =   2
      Left            =   3160
      Top             =   800
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblResult
      Left            =   240
      Top             =   1600
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdAnswer_Click(Index As Integer)
    If Index = 1 Then
        lblResult.Caption = "إجابة صحيحة"
    Else
        lblResult.Caption = "حاول مرة أخرى"
    End If
End Sub
```

### تمرين 2: تعطيل الكل

نموذج فيه ثلاثة مربعات نص في مصفوفة `txtField` وزر `cmdLock`. عند الضغط تُعطَّل كل المربعات بحلقة واحدة.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "قفل الحقول"
   ClientWidth     =   4200
   ClientHeight    =   2600
   Begin VB.TextBox txtField
      Index           =   0
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.TextBox txtField
      Index           =   1
      Left            =   240
      Top             =   740
      Width           =   2400
      Height          =   400
   End
   Begin VB.TextBox txtField
      Index           =   2
      Left            =   240
      Top             =   1240
      Width           =   2400
      Height          =   400
   End
   Begin VB.CommandButton cmdLock
      Caption         =   "اقفل"
      Left            =   2800
      Top             =   240
      Width           =   1200
      Height          =   500
   End
End

Private Sub cmdLock_Click()

End Sub
```

<!-- test: {"steps": [["click", "cmdLock"]], "expect": {"txtField_0.Enabled": "False", "txtField_2.Enabled": "False"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "قفل الحقول"
   ClientWidth     =   4200
   ClientHeight    =   2600
   Begin VB.TextBox txtField
      Index           =   0
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.TextBox txtField
      Index           =   1
      Left            =   240
      Top             =   740
      Width           =   2400
      Height          =   400
   End
   Begin VB.TextBox txtField
      Index           =   2
      Left            =   240
      Top             =   1240
      Width           =   2400
      Height          =   400
   End
   Begin VB.CommandButton cmdLock
      Caption         =   "اقفل"
      Left            =   2800
      Top             =   240
      Width           =   1200
      Height          =   500
   End
End

Private Sub cmdLock_Click()
    Dim i As Integer
    For i = txtField.LBound To txtField.UBound
        txtField(i).Enabled = False
    Next i
End Sub
```

## اختبر نفسك

```quiz
{"question": "ما الذي يميّز عناصر مصفوفة الأدوات عن بعضها؟", "choices": ["الاسم", "الخاصية Index", "اللون", "الحجم"], "answer": 1, "explanation": "كل العناصر لها الاسم نفسه، والفرق في رقم Index."}
```

```quiz
{"question": "ما الشكل الصحيح لإجراء النقر لمصفوفة أزرار اسمها cmdKey؟", "choices": ["cmdKey_Click()", "cmdKey_Click(Index As Integer)", "cmdKey(Index)_Click()", "Click_cmdKey(Index)"], "answer": 1, "explanation": "إجراء حدث مصفوفة الأدوات يستقبل رقم العنصر في Index As Integer."}
```

```quiz
{"question": "مصفوفة أدوات فيها العناصر 0 و1 و2 و3. ما قيمة UBound؟", "choices": ["4", "3", "0", "2"], "answer": 1, "explanation": "UBound أكبر رقم Index، وهو 3، بينما Count = 4."}
```

```quiz
{"question": "ما أهم فائدة لمصفوفة الأدوات؟", "choices": ["تسريع الرسم", "إجراء حدث واحد لعدة أدوات متشابهة", "توفير الذاكرة فقط", "تغيير الألوان تلقائيًّا"], "answer": 1, "explanation": "بدل كتابة إجراء لكل أداة، نكتب إجراءً واحدًا يستخدم Index."}
```

## الخلاصة

- مصفوفة الأدوات: أدوات من نوع واحد باسم واحد و`Index` مختلف.
- إجراء حدث واحد بمعامل `Index As Integer`، ومعه `Select Case Index` عند اختلاف الوظائف.
- `LBound` و`UBound` و`Count` للمرور على العناصر بحلقة.
