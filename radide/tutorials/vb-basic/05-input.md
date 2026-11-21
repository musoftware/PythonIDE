# الدرس 5: الإدخال - InputBox و TextBox

**في هذا الدرس ستتعلم:**

- أخذ بيانات من المستخدم بـ `InputBox`.
- قراءة ما كتبه المستخدم في **مربع نص** (TextBox).
- تحويل النص إلى عدد بـ `Val` و`CInt` و`CDbl`، والعكس بـ `CStr`.

## البرنامج يسأل والمستخدم يجيب

حتى الآن كانت قيم المتغيرات مكتوبة داخل البرنامج. لكن البرامج المفيدة تسأل المستخدم: ما اسمك؟ كم عمرك؟ كم سعر المنتج؟
هناك طريقتان: نافذة سؤال سريعة `InputBox`، أو مربع نص دائم على النموذج `TextBox`.

## `InputBox`

`InputBox` تعرض نافذة صغيرة فيها سؤال ومكان للكتابة، و**تُرجع** ما كتبه المستخدم كنص:

<!-- test: {"inputs": ["ليلى"]} -->
```vb run
Sub Main()
    Dim userName As String
    userName = InputBox("ما اسمك؟", "تعارف")
    Debug.Print "أهلًا يا " & userName & "!"
End Sub
```

```text output
أهلًا يا ليلى!
```

(في هذا المثال افترضنا أن المستخدم كتب "ليلى". جرّبه واكتب اسمك أنت.)

الصيغة: `InputBox(السؤال, العنوان, القيمة_الافتراضية)`. القيمة الافتراضية تظهر مكتوبة مسبقًا في المربع.
إذا ضغط المستخدم **إلغاء** تُرجع `InputBox` نصًّا فارغًا `""`.

## مشكلة: كل شيء نص!

ما يكتبه المستخدم يصل دائمًا **نصًّا**، حتى لو كتب أرقامًا. لاحظ ماذا يحدث إذا جمعنا نصّين:

```vb run
Sub Main()
    Dim a As String, b As String
    a = "5"
    b = "3"
    Debug.Print a + b
    Debug.Print Val(a) + Val(b)
End Sub
```

```text output
53
8
```

`"5" + "3"` ألصقت النصين فصارت `53`! الحل: نحوّل النص إلى عدد بالدالة `Val` قبل الحساب.

| الدالة | تحوّل إلى | ملاحظة |
|---|---|---|
| `Val(s)` | عدد | تقرأ الأرقام من بداية النص وتتوقف عند أول حرف: `Val("12abc")` = 12، و`Val("abc")` = 0 |
| `CInt(s)` | `Integer` | تعطي خطأ إذا لم يكن النص رقمًا |
| `CLng(s)` | `Long` | مثل `CInt` لأعداد أكبر |
| `CDbl(s)` | `Double` | للأعداد العشرية |
| `CStr(n)` | `String` | تحوّل العدد إلى نص |

```vb run
Sub Main()
    Debug.Print Val("12abc")
    Debug.Print Val("abc")
    Debug.Print CInt("7") + 1
    Debug.Print CDbl("2.5") * 2
    Debug.Print CStr(10) & "1"
End Sub
```

```text output
12
0
8
5
101
```

## مثال: جمع عددين بـ `InputBox`

<!-- test: {"inputs": ["15", "27"]} -->
```vb run
Sub Main()
    Dim x As Double, y As Double
    x = Val(InputBox("أدخل العدد الأول:"))
    y = Val(InputBox("أدخل العدد الثاني:"))
    Debug.Print x & " + " & y & " = " & (x + y)
End Sub
```

```text output
15 + 27 = 42
```

## مربع النص `TextBox`

في برامج النماذج نضع **مربع نص** (TextBox) يكتب فيه المستخدم متى شاء، ثم نقرأ خاصيته `Text` عند الضغط على زر.
هذا برنامج يحسب مربع العدد:

<!-- test: {"steps": [["set", "txtNumber", "Text", "9"], ["click", "cmdSquare"]], "expect": {"lblResult.Caption": "مربع العدد = 81"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "مربع العدد"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.TextBox txtNumber
      Text            =   ""
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   400
   End
   Begin VB.CommandButton cmdSquare
      Caption         =   "احسب المربع"
      Left            =   2500
      Top             =   200
      Width           =   2000
      Height          =   500
   End
   Begin VB.Label lblResult
      Caption         =   "اكتب عددًا ثم اضغط الزر"
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdSquare_Click()
    Dim n As Double
    n = Val(txtNumber.Text)
    lblResult.Caption = "مربع العدد = " & (n * n)
End Sub
```

يمكن أيضًا **الكتابة** في مربع النص من الكود: `txtNumber.Text = ""` تمسحه، و`txtNumber.SetFocus` تضع مؤشر الكتابة فيه.

## مثال: نموذج ترحيب كامل

<!-- test: {"steps": [["set", "txtFirst", "Text", "محمد"], ["set", "txtLast", "Text", "حسن"], ["click", "cmdGreet"]], "expect": {"lblGreeting.Caption": "مرحبا يا محمد حسن", "txtFirst.Text": "", "txtLast.Text": ""}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "ترحيب"
   ClientWidth     =   4800
   ClientHeight    =   2600
   Begin VB.Label lblFirst
      Caption         =   "الاسم الأول:"
      Left            =   240
      Top             =   240
      Width           =   1500
      Height          =   400
   End
   Begin VB.TextBox txtFirst
      Left            =   1900
      Top             =   200
      Width           =   2600
      Height          =   400
   End
   Begin VB.Label lblLast
      Caption         =   "اسم العائلة:"
      Left            =   240
      Top             =   800
      Width           =   1500
      Height          =   400
   End
   Begin VB.TextBox txtLast
      Left            =   1900
      Top             =   760
      Width           =   2600
      Height          =   400
   End
   Begin VB.CommandButton cmdGreet
      Caption         =   "رحّب"
      Left            =   1900
      Top             =   1350
      Width           =   1500
      Height          =   450
   End
   Begin VB.Label lblGreeting
      Left            =   240
      Top             =   2000
      Width           =   4300
      Height          =   400
   End
End

Private Sub cmdGreet_Click()
    lblGreeting.Caption = "مرحبا يا " & txtFirst.Text & " " & txtLast.Text
    txtFirst.Text = ""
    txtLast.Text = ""
End Sub
```

## أخطاء شائعة

- **نسيان `Val`** ثم الحصول على `53` بدلًا من `8`.
- **استخدام `CInt` مع نص غير رقمي:** `CInt("abc")` تعطي خطأ "Type mismatch". إذا لم تكن متأكدًا استخدم `Val`، أو تحقق أولًا بـ `IsNumeric`.
- **قراءة `txtName` بدلًا من `txtName.Text`:** الأوضح دائمًا أن تكتب اسم الخاصية.
- **كتابة الفاصلة العشرية كفاصلة عربية:** `Val("2,5")` تعطي 2. اكتب `2.5` بنقطة.

## تمارين

### تمرين 1: العمر بعد 10 سنوات

اسأل المستخدم عن عمره بـ `InputBox`، ثم اطبع: "بعد 10 سنوات سيكون عمرك X".

```vb exercise
Sub Main()
    Dim age As Integer
    ' age = ...
End Sub
```

<!-- test: {"inputs": ["17"]} -->
```vb solution
Sub Main()
    Dim age As Integer
    age = Val(InputBox("كم عمرك؟"))
    Debug.Print "بعد 10 سنوات سيكون عمرك " & (age + 10)
End Sub
```

```text output
بعد 10 سنوات سيكون عمرك 27
```

(بفرض أن المستخدم أدخل 17.)

### تمرين 2: محوّل العملة

نموذج فيه مربع نص `txtDollars` وزر `cmdConvert` وعنوان `lblPounds`. عند الضغط يُحسب المبلغ بالجنيه على أساس أن الدولار = 50 جنيهًا.

```vb form exercise
Begin VB.Form Form1
   Caption         =   "محوّل العملة"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.TextBox txtDollars
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   400
   End
   Begin VB.CommandButton cmdConvert
      Caption         =   "حوّل"
      Left            =   2500
      Top             =   200
      Width           =   1500
      Height          =   500
   End
   Begin VB.Label lblPounds
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdConvert_Click()
    ' اكتب هنا
End Sub
```

<!-- test: {"steps": [["set", "txtDollars", "Text", "12"], ["click", "cmdConvert"]], "expect": {"lblPounds.Caption": "12 دولار = 600 جنيه"}} -->
```vb form solution
Begin VB.Form Form1
   Caption         =   "محوّل العملة"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.TextBox txtDollars
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   400
   End
   Begin VB.CommandButton cmdConvert
      Caption         =   "حوّل"
      Left            =   2500
      Top             =   200
      Width           =   1500
      Height          =   500
   End
   Begin VB.Label lblPounds
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdConvert_Click()
    Const RATE As Double = 50
    Dim dollars As Double
    dollars = Val(txtDollars.Text)
    lblPounds.Caption = dollars & " دولار = " & (dollars * RATE) & " جنيه"
End Sub
```

### تمرين 3: متوسط ثلاث درجات

اسأل المستخدم عن ثلاث درجات بـ `InputBox` واطبع متوسطها.

```vb exercise
Sub Main()
    Dim d1 As Double, d2 As Double, d3 As Double
End Sub
```

<!-- test: {"inputs": ["80", "90", "100"]} -->
```vb solution
Sub Main()
    Dim d1 As Double, d2 As Double, d3 As Double
    d1 = Val(InputBox("الدرجة الأولى:"))
    d2 = Val(InputBox("الدرجة الثانية:"))
    d3 = Val(InputBox("الدرجة الثالثة:"))
    Debug.Print "المتوسط = " & (d1 + d2 + d3) / 3
End Sub
```

```text output
المتوسط = 90
```

## اختبر نفسك

```quiz
{"question": "ما نوع القيمة التي تُرجعها InputBox؟", "choices": ["Integer", "Double", "String (نص)", "Boolean"], "answer": 2, "explanation": "InputBox تُرجع دائمًا نصًّا، ولذلك نحوّله بـ Val قبل الحساب."}
```

```quiz
{"question": "ما ناتج Val(\"25kg\") ؟", "choices": ["0", "25", "خطأ", "25kg"], "answer": 1, "explanation": "Val تقرأ الأرقام من بداية النص وتتوقف عند أول حرف غير رقمي."}
```

```quiz
{"question": "ما الخاصية التي تحمل ما كتبه المستخدم في TextBox؟", "choices": ["Caption", "Name", "Text", "Value"], "answer": 2, "explanation": "الخاصية Text في مربع النص تحمل المحتوى المكتوب."}
```

```quiz
{"question": "ماذا تُرجع InputBox إذا ضغط المستخدم إلغاء؟", "choices": ["0", "نصًّا فارغًا \"\"", "False", "تغلق البرنامج"], "answer": 1, "explanation": "عند الإلغاء تُرجع InputBox نصًّا فارغًا."}
```

## الخلاصة

- `InputBox` لسؤال سريع، و`TextBox.Text` لإدخال دائم على النموذج.
- كل إدخال يصل نصًّا: حوّله بـ `Val` أو `CInt` أو `CDbl` قبل الحساب.
- `CStr` تحوّل العدد إلى نص.
