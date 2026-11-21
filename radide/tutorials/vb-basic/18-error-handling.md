# الدرس 18: معالجة الأخطاء - On Error

**في هذا الدرس ستتعلم:**

- أنواع الأخطاء: أخطاء الصياغة، وأخطاء وقت التشغيل، والأخطاء المنطقية.
- اصطياد أخطاء وقت التشغيل بـ `On Error GoTo`.
- الكائن `Err`: رقم الخطأ `Err.Number` ووصفه `Err.Description`.
- `Resume` و`Resume Next` و`On Error Resume Next`، وإطلاق خطأ بنفسك بـ `Err.Raise`.

## ثلاثة أنواع من الأخطاء

1. **خطأ صياغة** (Syntax error): كتابة لا تفهمها اللغة، مثل `Dim As x`. البيئة تكتشفه قبل التشغيل.
2. **خطأ وقت التشغيل** (Run-time error): الكود سليم لكن حدث شيء غير متوقع أثناء التشغيل: قسمة على صفر، أو ملف غير موجود، أو فهرس خارج المصفوفة.
3. **خطأ منطقي** (Logic error): البرنامج يعمل بدون رسائل، لكن النتيجة خاطئة، مثل كتابة `+` بدل `*`. هذا أصعبها، ونكتشفه بالاختبار ومصحّح الأخطاء (F9 وF10).

هذا الدرس عن النوع الثاني.

## ماذا يحدث بدون معالجة؟

إذا وقع خطأ وقت تشغيل ولم نعالجه، **يتوقف البرنامج** وتظهر رسالة مثل "Run-time error '9': Subscript out of range":

<!-- test: {"error": 9} -->
```vb run
Sub Main()
    Dim scores(2) As Integer
    scores(3) = 100        ' لا يوجد عنصر رقمه 3!
    Debug.Print "لن يصل البرنامج إلى هنا"
End Sub
```

بالنسبة للمستخدم، توقّف البرنامج فجأة تجربة سيئة. الأفضل أن نتوقع المشكلة ونتصرف بلطف.

## شبكة الأمان: `On Error GoTo`

تخيّل لاعب سيرك يمشي على الحبل وتحته **شبكة أمان**. إذا سقط، لا يصطدم بالأرض بل تلتقطه الشبكة.
`On Error GoTo اسم_علامة` تفرد شبكة الأمان: إذا وقع خطأ، يقفز التنفيذ إلى **العلامة** (Label)، وهي اسم يتبعه نقطتان `:`.

```vb run
Sub Main()
    On Error GoTo ErrorHandler
    Dim a As Integer, b As Integer
    a = 10
    b = 0
    Debug.Print "النتيجة: " & (a / b)
    Debug.Print "هذا السطر لن يُنفَّذ"
    Exit Sub

ErrorHandler:
    Debug.Print "حدث خطأ رقم " & Err.Number & ": " & Err.Description
End Sub
```

```text output
حدث خطأ رقم 11: Division by zero
```

لاحظ `Exit Sub` **قبل** العلامة: بدونها، إذا لم يقع خطأ، سيكمل البرنامج وينفّذ كود معالجة الخطأ أيضًا!

### أرقام أخطاء شائعة

| الرقم | الوصف | السبب المعتاد |
|---|---|---|
| 6 | Overflow | عدد أكبر من سعة النوع |
| 9 | Subscript out of range | فهرس خارج حدود المصفوفة |
| 11 | Division by zero | قسمة على صفر |
| 13 | Type mismatch | نوع غير مناسب، مثل `CInt("abc")` |
| 53 | File not found | الملف غير موجود |
| 91 | Object variable not set | كائن لم يُنشأ بعد |

## `Resume` و `Resume Next`

بعد معالجة الخطأ، أين نذهب؟

- `Resume Next`: أكمل من **السطر التالي** للسطر الذي سبّب الخطأ.
- `Resume`: أعِد تنفيذ **السطر نفسه** (بعد أن تصلح السبب، وإلا تدور في حلقة لا تنتهي).
- `Resume اسم_علامة`: اذهب إلى علامة معيّنة.

```vb run
Sub Main()
    On Error GoTo Fix
    Dim divisor As Integer
    divisor = 0
    Debug.Print "100 / " & divisor & " = " & (100 / divisor)
    Debug.Print "انتهى"
    Exit Sub

Fix:
    Debug.Print "المقسوم عليه صفر، سنستخدم 4 بدلًا منه"
    divisor = 4
    Resume                  ' أعِد السطر نفسه بعد الإصلاح
End Sub
```

```text output
المقسوم عليه صفر، سنستخدم 4 بدلًا منه
100 / 4 = 25
انتهى
```

## `On Error Resume Next`

`On Error Resume Next` تقول: "إذا وقع خطأ، تجاهله وأكمل". مفيدة في سطر واحد تتوقع فيه خطأ، ثم تفحص `Err.Number` بعده مباشرة:

```vb run
Sub Main()
    Dim n As Integer
    On Error Resume Next
    n = CInt("abc")
    If Err.Number <> 0 Then
        Debug.Print "لم يكن النص رقمًا (الخطأ " & Err.Number & ")"
        Err.Clear
    End If
    On Error GoTo 0          ' أوقف التجاهل
    Debug.Print "البرنامج مستمر"
End Sub
```

```text output
لم يكن النص رقمًا (الخطأ 13)
البرنامج مستمر
```

> ⚠️ **حذارِ:** `On Error Resume Next` في أول البرنامج كله تُخفي **كل** الأخطاء، فيعمل البرنامج بنتائج خاطئة دون أن تدري. استخدمها لسطر أو سطرين فقط، ثم `On Error GoTo 0` لإعادة الوضع الطبيعي.

## أطلق خطأك بنفسك: `Err.Raise`

يمكنك إطلاق خطأ من دالتك عندما تُعطى بيانات غير مقبولة، فيعرف المستدعي أن شيئًا خاطئًا حدث:

```vb run
Sub Main()
    On Error GoTo Problem
    Debug.Print "سعر 3 قطع: " & TotalPrice(3, 25)
    Debug.Print "سعر -2 قطعة: " & TotalPrice(-2, 25)
    Exit Sub
Problem:
    Debug.Print "خطأ: " & Err.Description
End Sub

Function TotalPrice(ByVal quantity As Integer, ByVal unitPrice As Double) As Double
    If quantity <= 0 Then
        Err.Raise 1000, "TotalPrice", "الكمية يجب أن تكون أكبر من صفر"
    End If
    TotalPrice = quantity * unitPrice
End Function
```

```text output
سعر 3 قطع: 75
خطأ: الكمية يجب أن تكون أكبر من صفر
```

لاحظ أن الخطأ وقع داخل `TotalPrice` (التي لا تحتوي على معالج)، فانتقل إلى معالج الإجراء الذي استدعاها `Main`.

## معالجة الأخطاء في النماذج

في النماذج، المعالج يمنع توقف البرنامج كله بسبب إدخال خاطئ في مربع نص:

<!-- test: {"steps": [["set", "txtA", "Text", "abc"], ["click", "cmdCalc"]], "expect": {"lblResult.Caption": "من فضلك أدخل عددًا صحيحًا"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "مقلوب العدد"
   ClientWidth     =   4800
   ClientHeight    =   1800
   Begin VB.TextBox txtA
      Left            =   240
      Top             =   240
      Width           =   2000
      Height          =   400
   End
   Begin VB.CommandButton cmdCalc
      Caption         =   "احسب 100 ÷ العدد"
      Left            =   2500
      Top             =   200
      Width           =   2000
      Height          =   500
   End
   Begin VB.Label lblResult
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Private Sub cmdCalc_Click()
    On Error GoTo BadInput
    Dim n As Integer
    n = CInt(txtA.Text)
    lblResult.Caption = "النتيجة = " & (100 / n)
    Exit Sub
BadInput:
    Select Case Err.Number
        Case 11
            lblResult.Caption = "لا يمكن القسمة على صفر"
        Case 13
            lblResult.Caption = "من فضلك أدخل عددًا صحيحًا"
        Case Else
            lblResult.Caption = "خطأ غير متوقع: " & Err.Description
    End Select
End Sub
```

## أخطاء شائعة

- **نسيان `Exit Sub` قبل المعالج:** فيُنفَّذ كود الخطأ حتى عند النجاح.
- **`Resume` بدون إصلاح السبب:** حلقة لا نهائية.
- **`On Error Resume Next` على البرنامج كله:** تُخفي المشاكل الحقيقية.
- **عدم مسح الخطأ:** بعد فحص `Err.Number` مع `Resume Next` استخدم `Err.Clear` حتى لا يبقى الرقم القديم.
- **الاعتماد على معالجة الأخطاء بدل التحقق:** إذا كان بالإمكان التحقق مسبقًا (`If b <> 0 Then`) فهذا أوضح من انتظار الخطأ.

## تمارين

### تمرين 1: قسمة آمنة

اكتب دالة `SafeDiv(a, b)` تستخدم `On Error GoTo` وتُرجع الناتج، أو `-1` إذا حدث خطأ. اطبع `SafeDiv(9, 3)` و`SafeDiv(9, 0)`.

```vb exercise
Sub Main()
    Debug.Print SafeDiv(9, 3)
    Debug.Print SafeDiv(9, 0)
End Sub

Function SafeDiv(ByVal a As Double, ByVal b As Double) As Double

End Function
```

```vb solution
Sub Main()
    Debug.Print SafeDiv(9, 3)
    Debug.Print SafeDiv(9, 0)
End Sub

Function SafeDiv(ByVal a As Double, ByVal b As Double) As Double
    On Error GoTo Failed
    SafeDiv = a / b
    Exit Function
Failed:
    SafeDiv = -1
End Function
```

```text output
3
-1
```

### تمرين 2: فهرس آمن

لديك مصفوفة من 3 أسماء. اكتب دالة `GetName(i)` تُرجع الاسم، أو "غير موجود" إذا كان الفهرس خارج الحدود (اصطد الخطأ رقم 9).

```vb exercise
Sub Main()
    Debug.Print GetName(1)
    Debug.Print GetName(7)
End Sub

Function GetName(ByVal i As Integer) As String
    Dim names(2) As String
    names(0) = "علي": names(1) = "سلمى": names(2) = "يوسف"
End Function
```

```vb solution
Sub Main()
    Debug.Print GetName(1)
    Debug.Print GetName(7)
End Sub

Function GetName(ByVal i As Integer) As String
    Dim names(2) As String
    names(0) = "علي": names(1) = "سلمى": names(2) = "يوسف"
    On Error GoTo NotFound
    GetName = names(i)
    Exit Function
NotFound:
    If Err.Number = 9 Then GetName = "غير موجود"
End Function
```

```text output
سلمى
غير موجود
```

### تمرين 3: تحقق من العمر

اكتب إجراء `SetAge(age)` يطلق خطأ برقم 2000 ووصف "عمر غير منطقي" إذا كان العمر أقل من 0 أو أكبر من 130، واستدعه في `Main` بالقيمتين 25 ثم 200 مع معالج يطبع الوصف.

```vb exercise
Sub Main()
    On Error GoTo Bad
    SetAge 25
    SetAge 200
    Exit Sub
Bad:
    Debug.Print Err.Description
End Sub
```

```vb solution
Sub Main()
    On Error GoTo Bad
    SetAge 25
    SetAge 200
    Exit Sub
Bad:
    Debug.Print Err.Description
End Sub

Sub SetAge(ByVal age As Integer)
    If age < 0 Or age > 130 Then Err.Raise 2000, "SetAge", "عمر غير منطقي"
    Debug.Print "تم حفظ العمر " & age
End Sub
```

```text output
تم حفظ العمر 25
عمر غير منطقي
```

## اختبر نفسك

```quiz
{"question": "ما نوع الخطأ في برنامج يعمل بدون رسائل لكن يعطي نتيجة خاطئة؟", "choices": ["خطأ صياغة", "خطأ وقت تشغيل", "خطأ منطقي", "ليس خطأ"], "answer": 2, "explanation": "الخطأ المنطقي لا يوقف البرنامج لكن النتيجة غير صحيحة."}
```

```quiz
{"question": "لماذا نكتب Exit Sub قبل علامة معالج الخطأ؟", "choices": ["لتسريع البرنامج", "حتى لا يُنفَّذ كود المعالجة عندما لا يقع خطأ", "لأن VB تشترط ذلك دائمًا", "لمسح الخطأ"], "answer": 1, "explanation": "بدون Exit Sub يكمل التنفيذ إلى كود المعالجة حتى عند النجاح."}
```

```quiz
{"question": "ما الفرق بين Resume و Resume Next؟", "choices": ["لا فرق", "Resume تعيد السطر نفسه، وResume Next تكمل من السطر التالي", "Resume Next تعيد السطر نفسه", "Resume تنهي البرنامج"], "answer": 1, "explanation": "Resume يعيد المحاولة، وResume Next يتخطى السطر المسبب للخطأ."}
```

```quiz
{"question": "ما رقم خطأ القسمة على صفر؟", "choices": ["6", "9", "11", "13"], "answer": 2, "explanation": "Division by zero رقمه 11."}
```

```quiz
{"question": "ما الذي يُعيد الوضع الطبيعي بعد On Error Resume Next؟", "choices": ["On Error Stop", "On Error GoTo 0", "Err.Clear", "Resume"], "answer": 1, "explanation": "On Error GoTo 0 يلغي معالجة الأخطاء الحالية."}
```

## الخلاصة

- `On Error GoTo علامة` شبكة أمان، و`Exit Sub` قبل العلامة.
- `Err.Number` و`Err.Description` يصفان الخطأ، و`Err.Raise` يطلق خطأ.
- `Resume` يعيد السطر، و`Resume Next` يكمل بعده، و`On Error Resume Next` لسطر أو اثنين فقط.
