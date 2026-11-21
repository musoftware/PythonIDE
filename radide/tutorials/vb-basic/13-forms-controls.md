# الدرس 13: النماذج والأدوات الأساسية

**في هذا الدرس ستتعلم:**

- الثلاثي الأساسي: **الزر** (CommandButton)، و**مربع النص** (TextBox)، و**العنوان** (Label).
- الخصائص الأكثر استخدامًا: `Caption` و`Text` و`Enabled` و`Visible` و`BackColor` و`ForeColor`.
- الأحداث: `Form_Load` و`Click` و`Change`.
- الدوال (Methods) مثل `SetFocus`، وكيف تتعامل مع النموذج نفسه بـ `Me`.

## الكائن: خصائص وأحداث وطرق

كل أداة على النموذج **كائن** (Object)، مثل السيارة:

- **الخصائص** (Properties): صفاتها. لون السيارة، وعدد أبوابها. في الأداة: `Caption`، و`Width`، و`BackColor`.
- **الدوال** (Methods، وتُسمّى أيضًا «الطرق»): أفعال تستطيع القيام بها. السيارة "تسير" و"تتوقف". الأداة: `SetFocus`، و`AddItem`.
- **الأحداث** (Events): أشياء تحدث لها فتستجيب. "ضُغطت الفرامل". الأداة: `Click`، و`Change`.

نكتب الخاصية والطريقة بعد نقطة: `txtName.Text` و`txtName.SetFocus`.

## الأدوات الثلاث الأساسية

| الأداة | البادئة | أهم خاصية | أهم حدث |
|---|---|---|---|
| زر الأمر (CommandButton) | `cmd` | `Caption` | `Click` |
| مربع النص (TextBox) | `txt` | `Text` | `Change` |
| العنوان (Label) | `lbl` | `Caption` | (نادرًا ما نستخدم أحداثه) |

العنوان (Label) للعرض فقط؛ المستخدم لا يكتب فيه. ومربع النص للإدخال.

## حدث `Form_Load`

`Form_Load` يقع **مرة واحدة** عند تحميل النموذج، قبل أن يراه المستخدم. مكان مثالي لتجهيز القيم الابتدائية:

<!-- test: {"expect": {"lblWelcome.Caption": "أهلًا بك في برنامج الآلة الحاسبة", "Form1.Caption": "الآلة الحاسبة", "txtA.Text": "0"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "Form1"
   ClientWidth     =   4800
   ClientHeight    =   1600
   Begin VB.Label lblWelcome
      Left            =   240
      Top             =   240
      Width           =   4200
      Height          =   400
   End
   Begin VB.TextBox txtA
      Left            =   240
      Top             =   800
      Width           =   1500
      Height          =   400
   End
End

Private Sub Form_Load()
    Me.Caption = "الآلة الحاسبة"
    lblWelcome.Caption = "أهلًا بك في برنامج الآلة الحاسبة"
    txtA.Text = "0"
End Sub
```

`Me` تعني "النموذج الحالي"، أي هذا النموذج نفسه. `Me.Caption` تغيّر عنوان النافذة.

## الآلة الحاسبة البسيطة

نموذج كامل بأربعة أزرار للعمليات. لاحظ كيف يكتب كل زر في العنوان `lblResult`:

<!-- test: {"steps": [["set", "txtA", "Text", "12"], ["set", "txtB", "Text", "4"], ["click", "cmdDiv"]], "expect": {"lblResult.Caption": "12 ÷ 4 = 3"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "آلة حاسبة"
   ClientWidth     =   5400
   ClientHeight    =   2400
   Begin VB.TextBox txtA
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   400
   End
   Begin VB.TextBox txtB
      Left            =   2600
      Top             =   240
      Width           =   2000
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "+"
      Left            =   240
      Top             =   900
      Width           =   900
      Height          =   500
   End
   Begin VB.CommandButton cmdSub
      Caption         =   "-"
      Left            =   1300
      Top             =   900
      Width           =   900
      Height          =   500
   End
   Begin VB.CommandButton cmdMul
      Caption         =   "×"
      Left            =   2360
      Top             =   900
      Width           =   900
      Height          =   500
   End
   Begin VB.CommandButton cmdDiv
      Caption         =   "÷"
      Left            =   3420
      Top             =   900
      Width           =   900
      Height          =   500
   End
   Begin VB.Label lblResult
      Left            =   240
      Top             =   1700
      Width           =   4800
      Height          =   400
   End
End

Option Explicit

Private Sub ShowResult(ByVal op As String, ByVal value As Double)
    lblResult.Caption = txtA.Text & " " & op & " " & txtB.Text & " = " & value
End Sub

Private Sub cmdAdd_Click()
    ShowResult "+", Val(txtA.Text) + Val(txtB.Text)
End Sub

Private Sub cmdSub_Click()
    ShowResult "-", Val(txtA.Text) - Val(txtB.Text)
End Sub

Private Sub cmdMul_Click()
    ShowResult "×", Val(txtA.Text) * Val(txtB.Text)
End Sub

Private Sub cmdDiv_Click()
    If Val(txtB.Text) = 0 Then
        lblResult.Caption = "لا يمكن القسمة على صفر"
    Else
        ShowResult "÷", Val(txtA.Text) / Val(txtB.Text)
    End If
End Sub
```

لاحظ الإجراء المساعد `ShowResult`: بدلًا من تكرار سطر العرض في كل زر، كتبناه مرة واحدة (تذكّر الدرس 11).

## Enabled و Visible

- `Enabled = False` تجعل الأداة **معطّلة** (رمادية لا تستجيب).
- `Visible = False` تجعلها **مختفية** تمامًا.

مثال: زر "إرسال" لا يعمل إلا بعد كتابة الاسم. نستخدم حدث `Change` لمربع النص، الذي يقع **مع كل حرف** يُكتب أو يُمسح:

<!-- test: {"steps": [["set", "txtName", "Text", "علي"]], "expect": {"cmdSend.Enabled": "True", "lblHint.Visible": "False", "lblCount.Caption": "عدد الحروف: 3"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "التسجيل"
   ClientWidth     =   4800
   ClientHeight    =   2200
   Begin VB.TextBox txtName
      Left            =   240
      Top             =   240
      Width           =   2600
      Height          =   400
   End
   Begin VB.CommandButton cmdSend
      Caption         =   "إرسال"
      Left            =   3100
      Top             =   200
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblHint
      Caption         =   "اكتب اسمك أولًا"
      Left            =   240
      Top             =   900
      Width           =   4200
      Height          =   400
   End
   Begin VB.Label lblCount
      Left            =   240
      Top             =   1400
      Width           =   4200
      Height          =   400
   End
End

Private Sub Form_Load()
    cmdSend.Enabled = False
End Sub

Private Sub txtName_Change()
    cmdSend.Enabled = (Len(txtName.Text) > 0)
    lblHint.Visible = (Len(txtName.Text) = 0)
    lblCount.Caption = "عدد الحروف: " & Len(txtName.Text)
End Sub

Private Sub cmdSend_Click()
    MsgBox "تم التسجيل باسم " & txtName.Text
End Sub
```

لاحظ الحيلة: `cmdSend.Enabled = (Len(txtName.Text) > 0)` تضع نتيجة المقارنة (`True` أو `False`) مباشرة في الخاصية، بدلًا من `If` طويلة.

## الألوان

الخاصيتان `BackColor` (لون الخلفية) و`ForeColor` (لون النص) تقبلان ثوابت جاهزة مثل `vbRed` و`vbGreen` و`vbBlue` و`vbYellow` و`vbWhite` و`vbBlack`، أو الدالة `RGB(أحمر, أخضر, أزرق)` بقيم من 0 إلى 255:

<!-- test: {"steps": [["set", "txtAge", "Text", "15"], ["click", "cmdCheck"]], "expect": {"lblStatus.Caption": "غير مسموح", "lblStatus.BackColor": "255"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "الألوان"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.TextBox txtAge
      Left            =   240
      Top             =   240
      Width           =   1500
      Height          =   400
   End
   Begin VB.CommandButton cmdCheck
      Caption         =   "تحقق"
      Left            =   2000
      Top             =   200
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblStatus
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdCheck_Click()
    If Val(txtAge.Text) >= 18 Then
        lblStatus.Caption = "مسموح"
        lblStatus.BackColor = vbGreen
    Else
        lblStatus.Caption = "غير مسموح"
        lblStatus.BackColor = vbRed
    End If
    lblStatus.ForeColor = vbWhite
End Sub
```

## `SetFocus`: أين يكتب المستخدم؟

`txtName.SetFocus` تنقل مؤشر الكتابة إلى مربع النص، فيكتب المستخدم مباشرة دون أن ينقر عليه. استخدمها بعد مسح المربعات:

```vb
txtA.Text = ""
txtB.Text = ""
txtA.SetFocus
```

## أخطاء شائعة

- **كتابة `Caption` لمربع النص أو `Text` للعنوان:** مربع النص يستخدم `Text`، والعنوان والزر يستخدمان `Caption`.
- **نسيان `Val`** عند الحساب من مربعات النص.
- **كتابة كود ثقيل في `Change`:** هذا الحدث يقع مع كل حرف، فاجعله سريعًا.
- **الخلط بين `Enabled` و`Visible`:** المعطّل يظهر رماديًّا، والمختفي لا يظهر أبدًا.
- **تغيير الخاصية في `Change` لمربع النص نفسه:** `txtA.Text = ...` داخل `txtA_Change` يسبب حدث `Change` جديدًا، وقد يدخل البرنامج في دائرة لا تنتهي.

## تمارين

### تمرين 1: محوّل درجات الحرارة

نموذج فيه `txtC` وزر `cmdConvert` وعنوان `lblF`. عند الضغط يحسب الفهرنهايت: F = C × 9 / 5 + 32، ويكتب مثلًا `100 C = 212 F`.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "درجات الحرارة"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.TextBox txtC
      Left            =   240
      Top             =   240
      Width           =   1500
      Height          =   400
   End
   Begin VB.CommandButton cmdConvert
      Caption         =   "حوّل"
      Left            =   2000
      Top             =   200
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblF
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdConvert_Click()

End Sub
```

<!-- test: {"steps": [["set", "txtC", "Text", "100"], ["click", "cmdConvert"]], "expect": {"lblF.Caption": "100 C = 212 F"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "درجات الحرارة"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.TextBox txtC
      Left            =   240
      Top             =   240
      Width           =   1500
      Height          =   400
   End
   Begin VB.CommandButton cmdConvert
      Caption         =   "حوّل"
      Left            =   2000
      Top             =   200
      Width           =   1400
      Height          =   500
   End
   Begin VB.Label lblF
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdConvert_Click()
    Dim c As Double
    c = Val(txtC.Text)
    lblF.Caption = c & " C = " & (c * 9 / 5 + 32) & " F"
End Sub
```

### تمرين 2: زر المسح

أضف إلى نموذج فيه `txtA` و`txtB` زرًّا اسمه `cmdClear` يمسح المربعين ويعطّل نفسه، وزرًّا `cmdEnable` يعيد تفعيله.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "مسح"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.TextBox txtA
      Text            =   "abc"
      Left            =   240
      Top             =   240
      Width           =   1800
      Height          =   400
   End
   Begin VB.TextBox txtB
      Text            =   "xyz"
      Left            =   2400
      Top             =   240
      Width           =   1800
      Height          =   400
   End
   Begin VB.CommandButton cmdClear
      Caption         =   "امسح"
      Left            =   240
      Top             =   900
      Width           =   1400
      Height          =   500
   End
   Begin VB.CommandButton cmdEnable
      Caption         =   "فعّل"
      Left            =   2400
      Top             =   900
      Width           =   1400
      Height          =   500
   End
End

' اكتب cmdClear_Click و cmdEnable_Click
```

<!-- test: {"steps": [["click", "cmdClear"]], "expect": {"txtA.Text": "", "txtB.Text": "", "cmdClear.Enabled": "False"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "مسح"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.TextBox txtA
      Text            =   "abc"
      Left            =   240
      Top             =   240
      Width           =   1800
      Height          =   400
   End
   Begin VB.TextBox txtB
      Text            =   "xyz"
      Left            =   2400
      Top             =   240
      Width           =   1800
      Height          =   400
   End
   Begin VB.CommandButton cmdClear
      Caption         =   "امسح"
      Left            =   240
      Top             =   900
      Width           =   1400
      Height          =   500
   End
   Begin VB.CommandButton cmdEnable
      Caption         =   "فعّل"
      Left            =   2400
      Top             =   900
      Width           =   1400
      Height          =   500
   End
End

Private Sub cmdClear_Click()
    txtA.Text = ""
    txtB.Text = ""
    txtA.SetFocus
    cmdClear.Enabled = False
End Sub

Private Sub cmdEnable_Click()
    cmdClear.Enabled = True
End Sub
```

## اختبر نفسك

```quiz
{"question": "متى يقع حدث Form_Load؟", "choices": ["عند كل نقرة", "مرة واحدة عند تحميل النموذج", "عند إغلاق النموذج", "كل ثانية"], "answer": 1, "explanation": "Form_Load يقع مرة واحدة عند تحميل النموذج قبل ظهوره."}
```

```quiz
{"question": "متى يقع حدث Change لمربع النص؟", "choices": ["عند الضغط على Enter فقط", "مع كل تغيير في النص (كل حرف)", "عند إغلاق البرنامج", "عند النقر المزدوج"], "answer": 1, "explanation": "Change يقع مع كل حرف يُضاف أو يُحذف."}
```

```quiz
{"question": "ما معنى Me داخل كود النموذج؟", "choices": ["المستخدم", "النموذج الحالي نفسه", "آخر أداة ضُغطت", "البرنامج كله"], "answer": 1, "explanation": "Me تشير إلى النموذج الذي يُكتب فيه الكود."}
```

```quiz
{"question": "أي خاصية تجعل الزر رماديًّا لا يستجيب؟", "choices": ["Visible = False", "Enabled = False", "Caption = \"\"", "BackColor = vbGray"], "answer": 1, "explanation": "Enabled = False تعطّل الأداة، أما Visible = False فتخفيها."}
```

## الخلاصة

- لكل أداة **خصائص** و**طرق** و**أحداث**.
- الزر `Caption` + `Click`، ومربع النص `Text` + `Change`، والعنوان `Caption` للعرض.
- `Form_Load` للتجهيز، و`Enabled`/`Visible` للتحكم، و`Me` للنموذج الحالي.
