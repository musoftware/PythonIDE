# الدرس 15: المؤقت والأحداث

**في هذا الدرس ستتعلم:**

- معنى **البرمجة بالأحداث** (Event-driven programming).
- أداة **المؤقت** (Timer): الخاصيتان `Interval` و`Enabled` والحدث `Timer`.
- أحداث لوحة المفاتيح: `KeyPress` والمتغير `KeyAscii`.
- أحداث أخرى مهمة: `DblClick` و`GotFocus` و`LostFocus` و`Form_Unload`.

## البرنامج ينتظر

في برامج `Sub Main` ينفّذ الحاسوب الأوامر من أولها لآخرها ثم ينتهي. أما برامج النماذج فتعمل مثل **موظف الاستقبال**: يجلس منتظرًا، فإذا رنّ الهاتف ردّ عليه، وإذا دخل زائر رحّب به.
كل "رنّة" هي **حدث** (Event)، و"الرد" هو إجراء الحدث الذي تكتبه أنت. هذا هو **البرمجة بالأحداث**.

## المؤقت Timer

المؤقت أداة **غير مرئية** أثناء التشغيل (تظهر في وقت التصميم فقط)، تعمل مثل **منبّه يرنّ كل فترة**:

| الخاصية / الحدث | الوظيفة |
|---|---|
| `Interval` | الفترة بين كل رنّة بالمللي ثانية (1000 = ثانية واحدة) |
| `Enabled` | `True` يعمل، `False` متوقف |
| `Timer` (الحدث) | يقع كل `Interval` مللي ثانية |

### ساعة رقمية

<!-- test: {"steps": [["event", "tmrClock", "Timer"]], "expect": {"lblClock.Caption": "re:\\d\\d:\\d\\d:\\d\\d"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الساعة"
   ClientWidth     =   3600
   ClientHeight    =   1400
   Begin VB.Label lblClock
      Caption         =   "--:--:--"
      Alignment       =   2  'Center
      Left            =   240
      Top             =   300
      Width           =   3100
      Height          =   600
      BeginProperty Font
         Name            =   "Segoe UI"
         Size            =   24
         Weight          =   700
      EndProperty
   End
   Begin VB.Timer tmrClock
      Interval        =   1000
      Left            =   0
      Top             =   0
   End
End

Private Sub tmrClock_Timer()
    lblClock.Caption = Format(Now, "hh:nn:ss")
End Sub
```

`Now` تُرجع التاريخ والوقت الحاليين، و`Format(..., "hh:nn:ss")` تعرض الساعة والدقائق والثواني (لاحظ: الدقائق `nn` وليس `mm`، لأن `mm` للشهر).

### عدّ تنازلي

المؤقت يمكن تشغيله وإيقافه من الكود بالخاصية `Enabled`:

<!-- test: {"steps": [["click", "cmdStart"], ["event", "tmrCount", "Timer"], ["event", "tmrCount", "Timer"], ["event", "tmrCount", "Timer"]], "expect": {"lblCount.Caption": "انطلق!", "tmrCount.Enabled": "False", "cmdStart.Enabled": "True"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "العدّ التنازلي"
   ClientWidth     =   3600
   ClientHeight    =   2000
   Begin VB.Label lblCount
      Caption         =   "3"
      Alignment       =   2  'Center
      Left            =   240
      Top             =   240
      Width           =   3100
      Height          =   600
   End
   Begin VB.CommandButton cmdStart
      Caption         =   "ابدأ"
      Left            =   1000
      Top             =   1100
      Width           =   1600
      Height          =   500
   End
   Begin VB.Timer tmrCount
      Interval        =   1000
      Enabled         =   0   'False
      Left            =   0
      Top             =   0
   End
End

Option Explicit
Private secondsLeft As Integer

Private Sub cmdStart_Click()
    secondsLeft = 3
    lblCount.Caption = secondsLeft
    cmdStart.Enabled = False
    tmrCount.Enabled = True
End Sub

Private Sub tmrCount_Timer()
    secondsLeft = secondsLeft - 1
    If secondsLeft > 0 Then
        lblCount.Caption = secondsLeft
    Else
        lblCount.Caption = "انطلق!"
        tmrCount.Enabled = False
        cmdStart.Enabled = True
    End If
End Sub
```

لاحظ أن `secondsLeft` متغير على **مستوى النموذج**، لأنه يجب أن يحتفظ بقيمته بين رنّة وأخرى (تذكّر الدرس 12).

### نص متحرك

المؤقت مفيد للحركة أيضًا: كل رنّة نحرّك العنوان قليلًا بتغيير خاصية `Left`:

<!-- test: {"steps": [["set", "tmrMove", "Enabled", "False"], ["set", "lblBall", "Left", "0"], ["event", "tmrMove", "Timer"], ["event", "tmrMove", "Timer"]], "expect": {"lblBall.Left": "300"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "حركة"
   ClientWidth     =   4800
   ClientHeight    =   1400
   Begin VB.Label lblBall
      Caption         =   "●"
      Left            =   0
      Top             =   400
      Width           =   400
      Height          =   400
   End
   Begin VB.Timer tmrMove
      Interval        =   50
      Left            =   0
      Top             =   0
   End
End

Private Sub tmrMove_Timer()
    lblBall.Left = lblBall.Left + 150
    If lblBall.Left > Me.ScaleWidth Then lblBall.Left = 0
End Sub
```

## أحداث لوحة المفاتيح: `KeyPress`

`KeyPress` يقع عندما يضغط المستخدم حرفًا في مربع النص، **قبل** ظهور الحرف. ويصل إلى الإجراء معامل اسمه `KeyAscii` فيه رمز الحرف.
إذا جعلت `KeyAscii = 0` يُلغى الحرف ولا يظهر، مثل حارس على الباب يمنع من لا يحمل تذكرة. هذا مربع نص يقبل الأرقام فقط:

<!-- test: {"steps": [["key", "txtPhone", "5"], ["key", "txtPhone", "a"], ["key", "txtPhone", "\b"]], "keys": [null, "break", null], "expect": {"lblInfo.Caption": "مسموح بالأرقام فقط"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "رقم الهاتف"
   ClientWidth     =   4800
   ClientHeight    =   1600
   Begin VB.TextBox txtPhone
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   400
   End
   Begin VB.Label lblInfo
      Left            =   240
      Top             =   900
      Width           =   4200
      Height          =   400
   End
End

Private Sub txtPhone_KeyPress(KeyAscii As Integer)
    If KeyAscii = 8 Then Exit Sub            ' 8 = مفتاح المسح Backspace: مسموح
    If KeyAscii < Asc("0") Or KeyAscii > Asc("9") Then
        KeyAscii = 0                         ' ألغِ الحرف
        lblInfo.Caption = "مسموح بالأرقام فقط"
    End If
End Sub
```

و`KeyAscii = 13` يعني أن المستخدم ضغط **Enter**؛ يمكنك استخدامه لتنفيذ البحث مثلًا دون الضغط على زر.

## أحداث أخرى مفيدة

| الحدث | متى يقع |
|---|---|
| `DblClick` | نقر مزدوج |
| `GotFocus` | دخول مؤشر الكتابة إلى الأداة |
| `LostFocus` | خروج المؤشر منها (مناسب للتحقق من المدخلات) |
| `MouseMove` | تحريك الفأرة فوق الأداة |
| `Form_Unload` | عند إغلاق النموذج |

مثال: سؤال تأكيد قبل الإغلاق. إذا جعلت `Cancel = 1` في `Form_Unload` يُلغى الإغلاق:

```vb
Private Sub Form_Unload(Cancel As Integer)
    If MsgBox("هل تريد الخروج فعلًا؟", vbYesNo + vbQuestion) = vbNo Then
        Cancel = 1
    End If
End Sub
```

ومثال النقر المزدوج على قائمة:

<!-- test: {"steps": [["set", "lstFruits", "ListIndex", "1"], ["event", "lstFruits", "DblClick"]], "msgbox": ["اخترت: موز"]} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "نقر مزدوج"
   ClientWidth     =   3600
   ClientHeight    =   2400
   Begin VB.ListBox lstFruits
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   1800
   End
End

Private Sub Form_Load()
    lstFruits.AddItem "تفاح"
    lstFruits.AddItem "موز"
    lstFruits.AddItem "عنب"
End Sub

Private Sub lstFruits_DblClick()
    MsgBox "اخترت: " & lstFruits.Text
End Sub
```

## أخطاء شائعة

- **`Interval = 0`:** المؤقت لا يعمل أبدًا. ضع قيمة أكبر من صفر.
- **الظن أن `Interval` بالثواني:** 1 تعني جزءًا من ألف من الثانية! للثانية اكتب 1000.
- **عمل طويل داخل حدث `Timer`:** يجعل البرنامج بطيئًا ومتجمدًا. اجعل كود المؤقت قصيرًا.
- **عدّاد المؤقت متغير محلي:** يبدأ من جديد في كل رنّة. استخدم متغيرًا على مستوى النموذج.
- **نسيان إيقاف المؤقت** بعد انتهاء مهمته (`Enabled = False`).

## تمارين

### تمرين 1: ساعة الإيقاف

نموذج فيه `lblTime` وزرّان `cmdStart` و`cmdStop` ومؤقت `tmrWatch` (Interval = 1000). الزر الأول يشغّل المؤقت، والثاني يوقفه، والمؤقت يزيد عدد الثواني ويعرضه بالصيغة `الوقت: 3 ثانية`.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "ساعة إيقاف"
   ClientWidth     =   4200
   ClientHeight    =   1800
   Begin VB.Label lblTime
      Caption         =   "الوقت: 0 ثانية"
      Left            =   240
      Top             =   240
      Width           =   3600
      Height          =   400
   End
   Begin VB.CommandButton cmdStart
      Caption         =   "ابدأ"
      Left            =   240
      Top             =   900
      Width           =   1500
      Height          =   500
   End
   Begin VB.CommandButton cmdStop
      Caption         =   "قف"
      Left            =   2000
      Top             =   900
      Width           =   1500
      Height          =   500
   End
   Begin VB.Timer tmrWatch
      Interval        =   1000
      Enabled         =   0   'False
   End
End

' اكتب الكود هنا
```

<!-- test: {"steps": [["click", "cmdStart"], ["event", "tmrWatch", "Timer"], ["event", "tmrWatch", "Timer"], ["event", "tmrWatch", "Timer"], ["click", "cmdStop"]], "expect": {"lblTime.Caption": "الوقت: 3 ثانية", "tmrWatch.Enabled": "False"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "ساعة إيقاف"
   ClientWidth     =   4200
   ClientHeight    =   1800
   Begin VB.Label lblTime
      Caption         =   "الوقت: 0 ثانية"
      Left            =   240
      Top             =   240
      Width           =   3600
      Height          =   400
   End
   Begin VB.CommandButton cmdStart
      Caption         =   "ابدأ"
      Left            =   240
      Top             =   900
      Width           =   1500
      Height          =   500
   End
   Begin VB.CommandButton cmdStop
      Caption         =   "قف"
      Left            =   2000
      Top             =   900
      Width           =   1500
      Height          =   500
   End
   Begin VB.Timer tmrWatch
      Interval        =   1000
      Enabled         =   0   'False
   End
End

Option Explicit
Private seconds As Long

Private Sub cmdStart_Click()
    tmrWatch.Enabled = True
End Sub

Private Sub cmdStop_Click()
    tmrWatch.Enabled = False
End Sub

Private Sub tmrWatch_Timer()
    seconds = seconds + 1
    lblTime.Caption = "الوقت: " & seconds & " ثانية"
End Sub
```

### تمرين 2: حروف كبيرة فقط

اكتب `txtCode_KeyPress` يحوّل أي حرف إنجليزي صغير إلى كبير أثناء الكتابة.
تلميح: `KeyAscii = Asc(UCase(Chr(KeyAscii)))`.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "كود الخصم"
   ClientWidth     =   4200
   ClientHeight    =   1200
   Begin VB.TextBox txtCode
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   400
   End
End

Private Sub txtCode_KeyPress(KeyAscii As Integer)

End Sub
```

<!-- test: {"steps": [["key", "txtCode", "a"]], "keys": [null]} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "كود الخصم"
   ClientWidth     =   4200
   ClientHeight    =   1200
   Begin VB.TextBox txtCode
      Left            =   240
      Top             =   240
      Width           =   3000
      Height          =   400
   End
End

Private Sub txtCode_KeyPress(KeyAscii As Integer)
    KeyAscii = Asc(UCase(Chr(KeyAscii)))
End Sub
```

## اختبر نفسك

```quiz
{"question": "لكي يرنّ المؤقت كل نصف ثانية، ما قيمة Interval؟", "choices": ["0.5", "5", "500", "5000"], "answer": 2, "explanation": "Interval بالمللي ثانية: نصف ثانية = 500."}
```

```quiz
{"question": "كيف توقف المؤقت من الكود؟", "choices": ["tmr.Stop", "tmr.Enabled = False", "tmr.Interval = -1", "Unload tmr"], "answer": 1, "explanation": "Enabled = False توقف المؤقت، وTrue تشغّله."}
```

```quiz
{"question": "ماذا يحدث إذا جعلت KeyAscii = 0 داخل KeyPress؟", "choices": ["يُغلق البرنامج", "يُلغى الحرف ولا يظهر", "يُكتب صفر", "يُمسح النص كله"], "answer": 1, "explanation": "KeyAscii = 0 يلغي الحرف المضغوط."}
```

```quiz
{"question": "ما رمز الدقائق في Format؟", "choices": ["mm", "nn", "mi", "min"], "answer": 1, "explanation": "nn للدقائق، وmm للشهر."}
```

## الخلاصة

- البرنامج المرئي ينتظر **الأحداث** ويستجيب لها.
- المؤقت: `Interval` بالمللي ثانية، و`Enabled` للتشغيل والإيقاف، والحدث `Timer`.
- `KeyPress` مع `KeyAscii` للتحكم في الكتابة، و`Form_Unload` مع `Cancel` لمنع الإغلاق.
