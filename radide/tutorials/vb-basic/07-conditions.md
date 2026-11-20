# الدرس 7: الشروط - If و Select Case

**في هذا الدرس ستتعلم:**

- اتخاذ القرار بـ `If ... Then ... Else ... End If`.
- الشروط المتعددة بـ `ElseIf`.
- الاختيار من بين حالات كثيرة بـ `Select Case`.
- الشروط المتداخلة والدالة `IIf`.

## البرنامج يتخذ قرارًا

في حياتنا نتخذ قرارات طوال الوقت: **إذا** كانت السماء تمطر **فـ**خذ المظلة، **وإلا** البس النظارة الشمسية.
البرنامج أيضًا يحتاج أن يختار طريقًا حسب الظروف. هذا هو **الشرط** (Condition).

## If ... Then ... End If

```vb run
Sub Main()
    Dim temperature As Integer
    temperature = 38
    If temperature > 35 Then
        Debug.Print "الجو حار جدًّا، اشرب ماء كثيرًا"
    End If
    Debug.Print "انتهى البرنامج"
End Sub
```

```text output
الجو حار جدًّا، اشرب ماء كثيرًا
انتهى البرنامج
```

الأوامر بين `If ... Then` و`End If` تُنفَّذ **فقط** إذا كان الشرط صحيحًا. جرّب تغيير `38` إلى `25`: لن تظهر الرسالة الأولى.

إذا كان هناك أمر واحد فقط يمكن كتابة الشرط في سطر واحد بدون `End If`:

```vb
If temperature > 35 Then Debug.Print "حار!"
```

## If ... Else

`Else` تعني "وإلا": الطريق البديل إذا كان الشرط خطأ.

```vb run
Sub Main()
    Dim grade As Integer
    grade = 45
    If grade >= 50 Then
        Debug.Print "ناجح"
    Else
        Debug.Print "راسب، حاول مرة أخرى"
    End If
End Sub
```

```text output
راسب، حاول مرة أخرى
```

## ElseIf: أكثر من طريقين

مثل إشارة المرور: أحمر = قف، أصفر = استعد، أخضر = انطلق.

```vb run
Sub Main()
    Dim score As Integer
    score = 82
    If score >= 90 Then
        Debug.Print "ممتاز"
    ElseIf score >= 80 Then
        Debug.Print "جيد جدًّا"
    ElseIf score >= 65 Then
        Debug.Print "جيد"
    ElseIf score >= 50 Then
        Debug.Print "مقبول"
    Else
        Debug.Print "راسب"
    End If
End Sub
```

```text output
جيد جدًّا
```

البرنامج يفحص الشروط **من الأعلى للأسفل**، وينفّذ أول شرط صحيح فقط ثم يقفز إلى `End If`. لذلك الترتيب مهم: لو بدأنا بـ `score >= 50` لحصل الكل على "مقبول"!

## Select Case: اختيار من قائمة

عندما نقارن **متغيرًا واحدًا** بقيم كثيرة، يكون `Select Case` أوضح من سلسلة `ElseIf`. تخيّل آلة بيع: تضغط رقمًا، فتعطيك منتجًا:

```vb run
Sub Main()
    Dim dayNumber As Integer
    dayNumber = 6
    Select Case dayNumber
        Case 1
            Debug.Print "السبت"
        Case 2
            Debug.Print "الأحد"
        Case 3, 4, 5
            Debug.Print "منتصف الأسبوع"
        Case 6
            Debug.Print "الخميس"
        Case Else
            Debug.Print "الجمعة: إجازة!"
    End Select
End Sub
```

```text output
الخميس
```

`Case` يقبل أشكالًا كثيرة:

| الصيغة | المعنى |
|---|---|
| `Case 5` | يساوي 5 |
| `Case 3, 4, 5` | أي قيمة من القائمة |
| `Case 1 To 10` | من 1 إلى 10 |
| `Case Is >= 90` | مقارنة باستخدام `Is` |
| `Case "نعم"` | نص |
| `Case Else` | أي شيء آخر |

```vb run
Sub Main()
    Dim age As Integer
    age = 15
    Select Case age
        Case 0 To 12
            Debug.Print "طفل"
        Case 13 To 19
            Debug.Print "مراهق"
        Case Is >= 60
            Debug.Print "كبير السن"
        Case Else
            Debug.Print "بالغ"
    End Select
End Sub
```

```text output
مراهق
```

## الشروط المتداخلة والمركّبة

يمكن وضع `If` داخل `If`، أو ربط الشروط بـ `And` و`Or`:

<!-- test: {"steps": [["set", "txtUser", "Text", "admin"], ["set", "txtPass", "Text", "1234"], ["click", "cmdLogin"]], "expect": {"lblStatus.Caption": "تم تسجيل الدخول"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "تسجيل الدخول"
   ClientWidth     =   4800
   ClientHeight    =   2400
   Begin VB.TextBox txtUser
      Left            =   240
      Top             =   240
      Width           =   2400
      Height          =   400
   End
   Begin VB.TextBox txtPass
      Left            =   240
      Top             =   800
      Width           =   2400
      Height          =   400
      PasswordChar    =   "*"
   End
   Begin VB.CommandButton cmdLogin
      Caption         =   "دخول"
      Left            =   2900
      Top             =   500
      Width           =   1500
      Height          =   500
   End
   Begin VB.Label lblStatus
      Left            =   240
      Top             =   1500
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdLogin_Click()
    If txtUser.Text = "" Or txtPass.Text = "" Then
        lblStatus.Caption = "اكتب اسم المستخدم وكلمة المرور"
    ElseIf txtUser.Text = "admin" And txtPass.Text = "1234" Then
        lblStatus.Caption = "تم تسجيل الدخول"
    Else
        lblStatus.Caption = "بيانات غير صحيحة"
    End If
End Sub
```

(الخاصية `PasswordChar = "*"` تُخفي ما يُكتب في مربع كلمة المرور.)

## الدالة IIf

`IIf(شرط, قيمة_إذا_صح, قيمة_إذا_خطأ)` اختصار مفيد لاختيار قيمة في سطر واحد:

```vb run
Sub Main()
    Dim n As Integer
    n = 7
    Debug.Print n & " عدد " & IIf(n Mod 2 = 0, "زوجي", "فردي")
End Sub
```

```text output
7 عدد فردي
```

## أخطاء شائعة

- **نسيان `End If`** في الشرط متعدد الأسطر، أو `End Select` في نهاية `Select Case`.
- **كتابة `Else If` بكلمتين:** الصحيح `ElseIf` كلمة واحدة.
- **ترتيب خاطئ للشروط في `ElseIf`:** ضع الشرط الأضيق أولًا (90 قبل 80 قبل 50).
- **مقارنة نص بعدد:** `If txtAge.Text > 18` قد تعطي نتيجة غير متوقعة؛ اكتب `If Val(txtAge.Text) > 18`.
- **الحروف الكبيرة والصغيرة:** `"Admin" = "admin"` خطأ (False). لتجاهل الفرق قارن `LCase(x) = "admin"`.

## تمارين

### تمرين 1: أكبر عددين

لديك `a = 14` و `b = 9`. اطبع الأكبر منهما بالصيغة: `الأكبر هو 14`.

```vb exercise
Sub Main()
    Dim a As Integer, b As Integer
    a = 14
    b = 9
End Sub
```

```vb solution
Sub Main()
    Dim a As Integer, b As Integer
    a = 14
    b = 9
    If a > b Then
        Debug.Print "الأكبر هو " & a
    Else
        Debug.Print "الأكبر هو " & b
    End If
End Sub
```

```text output
الأكبر هو 14
```

### تمرين 2: فصول السنة

بـ `Select Case` اطبع اسم الفصل لرقم الشهر `m = 4`: الشهور 12 و1 و2 شتاء، و3 إلى 5 ربيع، و6 إلى 8 صيف، و9 إلى 11 خريف.

```vb exercise
Sub Main()
    Dim m As Integer
    m = 4
End Sub
```

```vb solution
Sub Main()
    Dim m As Integer
    m = 4
    Select Case m
        Case 12, 1, 2
            Debug.Print "شتاء"
        Case 3 To 5
            Debug.Print "ربيع"
        Case 6 To 8
            Debug.Print "صيف"
        Case 9 To 11
            Debug.Print "خريف"
        Case Else
            Debug.Print "رقم شهر غير صحيح"
    End Select
End Sub
```

```text output
ربيع
```

### تمرين 3: السنة الكبيسة

السنة كبيسة إذا كانت تقبل القسمة على 4 ولا تقبل القسمة على 100، أو إذا كانت تقبل القسمة على 400. اسأل المستخدم عن سنة واطبع "كبيسة" أو "بسيطة".

```vb exercise
Sub Main()
    Dim y As Long
    y = Val(InputBox("أدخل السنة:"))
End Sub
```

<!-- test: {"inputs": ["2024"]} -->
```vb solution
Sub Main()
    Dim y As Long
    y = Val(InputBox("أدخل السنة:"))
    If (y Mod 4 = 0 And y Mod 100 <> 0) Or y Mod 400 = 0 Then
        Debug.Print y & " سنة كبيسة"
    Else
        Debug.Print y & " سنة بسيطة"
    End If
End Sub
```

```text output
2024 سنة كبيسة
```

## اختبر نفسك

```quiz
{"question": "ما الكلمة الصحيحة لشرط إضافي داخل If؟", "choices": ["Else If", "ElseIf", "OrIf", "ThenIf"], "answer": 1, "explanation": "ElseIf تُكتب كلمة واحدة."}
```

```quiz
{"question": "في سلسلة If/ElseIf، كم فرعًا يُنفَّذ إذا كان أكثر من شرط صحيحًا؟", "choices": ["كل الفروع الصحيحة", "أول فرع صحيح فقط", "آخر فرع صحيح", "لا شيء"], "answer": 1, "explanation": "يُنفَّذ أول فرع صحيح فقط ثم يقفز البرنامج إلى End If."}
```

```quiz
{"question": "أي صيغة في Select Case تعني \"من 1 إلى 10\"؟", "choices": ["Case 1-10", "Case 1 To 10", "Case 1..10", "Case Between 1, 10"], "answer": 1, "explanation": "الصيغة الصحيحة هي Case 1 To 10."}
```

```quiz
{"question": "ما ناتج  IIf(5 > 3, \"نعم\", \"لا\") ؟", "choices": ["نعم", "لا", "True", "خطأ"], "answer": 0, "explanation": "الشرط صحيح فتُرجع IIf القيمة الثانية: \"نعم\"."}
```

## الخلاصة

- `If ... Then ... ElseIf ... Else ... End If` لاتخاذ القرارات.
- `Select Case` لمقارنة متغير واحد بحالات كثيرة: قيم، ونطاقات `To`، ومقارنات `Is`.
- الترتيب مهم، و`IIf` اختصار لاختيار قيمة.
