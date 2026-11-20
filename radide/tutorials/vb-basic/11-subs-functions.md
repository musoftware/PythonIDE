# الدرس 11: الإجراءات والدوال - Sub و Function

**في هذا الدرس ستتعلم:**

- تقسيم البرنامج إلى أجزاء صغيرة: **الإجراء** (`Sub`) و**الدالة** (`Function`).
- تمرير **المعاملات** (Parameters) إلى الإجراء.
- الفرق بين `ByVal` و`ByRef`.
- المعاملات الاختيارية `Optional`، والخروج المبكر بـ `Exit Sub` و`Exit Function`.

## وصفة تُستخدم مرات كثيرة

في المطبخ، وصفة "عمل الصلصة" تُستخدم في المكرونة والبيتزا وغيرهما. بدل أن تكتب خطوات الصلصة في كل وصفة، تكتب في كل مكان: "اعمل الصلصة (انظر صفحة 10)".
في البرمجة نفعل الشيء نفسه: نجمع مجموعة أوامر تحت **اسم**، ثم **نستدعيها** بهذا الاسم متى احتجنا.

- **الإجراء** (`Sub`): ينفّذ عملًا ولا يُرجع قيمة. مثل: "اطبع الفاتورة".
- **الدالة** (`Function`): تحسب شيئًا و**تُرجع** النتيجة. مثل: "احسب سعر البيع" تُرجع رقمًا.

## الإجراء Sub

```vb run
Sub Main()
    PrintLine
    Debug.Print "  فاتورة متجر النور"
    PrintLine
    Greet "أحمد"
    Greet "فاطمة"
End Sub

Sub PrintLine()
    Debug.Print "===================="
End Sub

Sub Greet(personName As String)
    Debug.Print "مرحبا يا " & personName
End Sub
```

```text output
====================
  فاتورة متجر النور
====================
مرحبا يا أحمد
مرحبا يا فاطمة
```

- `PrintLine` إجراء بلا معاملات، نستدعيه بكتابة اسمه.
- `Greet` يستقبل **معاملًا** اسمه `personName`. عند الاستدعاء `Greet "أحمد"` تصبح قيمة `personName` هي "أحمد".
- القيمة التي نرسلها ("أحمد") تُسمّى **وسيطًا** (Argument).

يمكن أيضًا الاستدعاء بالكلمة `Call` مع أقواس: `Call Greet("أحمد")`. والصيغتان صحيحتان.

## الدالة Function

الدالة تُرجع قيمة: نكتب `As النوع` بعد الأقواس لتحديد نوع النتيجة، و**نضع النتيجة في اسم الدالة نفسه**:

```vb run
Sub Main()
    Debug.Print "مساحة الدائرة: " & CircleArea(10)
    Debug.Print "الأكبر: " & MaxOf(17, 42)
    Dim total As Double
    total = SellPrice(200) + SellPrice(50)
    Debug.Print "إجمالي سعر البيع: " & total
End Sub

Function CircleArea(radius As Double) As Double
    CircleArea = 3.14 * radius * radius
End Function

Function MaxOf(a As Long, b As Long) As Long
    If a > b Then
        MaxOf = a
    Else
        MaxOf = b
    End If
End Function

Function SellPrice(cost As Double) As Double
    SellPrice = cost * 1.5          ' ربح 50%
End Function
```

```text output
مساحة الدائرة: 314
الأكبر: 42
إجمالي سعر البيع: 375
```

لاحظ أن استدعاء الدالة يكون **بأقواس** لأننا نستخدم نتيجتها: `x = MaxOf(17, 42)`.

## ByVal و ByRef: نسخة أم الأصل؟

تخيّل أن المتغير ورقة مكتوب عليها قيمة. عندما ترسل متغيرًا إلى إجراء، هناك طريقتان:

- **`ByVal`** (بالقيمة): ترسل **صورة** من الورقة. إذا كتب الإجراء على الصورة، تبقى ورقتك الأصلية كما هي.
- **`ByRef`** (بالمرجع): ترسل **الورقة الأصلية** نفسها. أي تعديل يغيّر الأصل.

**الافتراضي في فيجوال بيسك 6 هو `ByRef`** إذا لم تكتب شيئًا.

```vb run
Sub Main()
    Dim a As Integer, b As Integer
    a = 10
    b = 10
    AddOneByVal a
    AddOneByRef b
    Debug.Print "a بعد ByVal = " & a
    Debug.Print "b بعد ByRef = " & b
End Sub

Sub AddOneByVal(ByVal n As Integer)
    n = n + 1
End Sub

Sub AddOneByRef(ByRef n As Integer)
    n = n + 1
End Sub
```

```text output
a بعد ByVal = 10
b بعد ByRef = 11
```

`ByRef` مفيد عندما تريد أن يُرجع الإجراء **أكثر من نتيجة**:

```vb run
Sub Main()
    Dim q As Long, r As Long
    DivideWithRemainder 17, 5, q, r
    Debug.Print "17 / 5 = " & q & " والباقي " & r
End Sub

Sub DivideWithRemainder(ByVal a As Long, ByVal b As Long, ByRef quotient As Long, ByRef remainder As Long)
    quotient = a \ b
    remainder = a Mod b
End Sub
```

```text output
17 / 5 = 3 والباقي 2
```

> 💡 **قاعدة عملية:** اكتب `ByVal` للمعاملات التي لا يجب أن تتغير. هكذا يكون واضحًا من قراءة السطر الأول أن الإجراء لن يعبث بمتغيراتك.

## المعاملات الاختيارية Optional

`Optional` تجعل المعامل اختياريًّا، مع قيمة افتراضية تُستخدم إذا لم يُرسَل. يجب أن تكون المعاملات الاختيارية في **آخر** القائمة:

```vb run
Sub Main()
    Debug.Print Welcome("سارة")
    Debug.Print Welcome("Tom", "Hello")
    Debug.Print Power(5)
    Debug.Print Power(2, 8)
End Sub

Function Welcome(ByVal who As String, Optional ByVal word As String = "أهلًا") As String
    Welcome = word & " " & who
End Function

Function Power(ByVal base As Double, Optional ByVal exponent As Integer = 2) As Double
    Power = base ^ exponent
End Function
```

```text output
أهلًا سارة
Hello Tom
25
256
```

## الخروج المبكر

`Exit Sub` و`Exit Function` تُنهيان الإجراء فورًا. مفيدتان لرفض المدخلات الخاطئة في البداية:

```vb run
Sub Main()
    Debug.Print SafeDivide(10, 4)
    Debug.Print SafeDivide(10, 0)
End Sub

Function SafeDivide(ByVal a As Double, ByVal b As Double) As String
    If b = 0 Then
        SafeDivide = "لا يمكن القسمة على صفر"
        Exit Function
    End If
    SafeDivide = CStr(a / b)
End Function
```

```text output
2.5
لا يمكن القسمة على صفر
```

## أخطاء شائعة

- **نسيان إعطاء الدالة قيمة:** إذا لم تكتب `MaxOf = ...` تُرجع الدالة القيمة الافتراضية (0 أو نص فارغ).
- **أقواس في استدعاء Sub بدون Call:** `Greet("أحمد", "صباح")` خطأ صياغة. اكتب `Greet "أحمد", "صباح"` أو `Call Greet("أحمد", "صباح")`.
- **تغيير متغير بالخطأ بسبب `ByRef` الافتراضي:** إذا عدّل الإجراء معاملًا تتغير قيمة المتغير عند المستدعي. استخدم `ByVal`.
- **ترتيب الوسائط خطأ:** `DivideWithRemainder 5, 17, ...` تعطي نتيجة مختلفة. الترتيب مهم.
- **وضع `Optional` قبل معامل إجباري:** غير مسموح.

## تمارين

### تمرين 1: دالة المضروب

اكتب دالة `Factorial(n)` تُرجع مضروب العدد، ثم اطبع `Factorial(5)` و`Factorial(10)`.

```vb exercise
Sub Main()
    Debug.Print Factorial(5)
    Debug.Print Factorial(10)
End Sub

Function Factorial(ByVal n As Integer) As Long
    ' اكتب هنا
End Function
```

```vb solution
Sub Main()
    Debug.Print Factorial(5)
    Debug.Print Factorial(10)
End Sub

Function Factorial(ByVal n As Integer) As Long
    Dim i As Integer, f As Long
    f = 1
    For i = 2 To n
        f = f * i
    Next i
    Factorial = f
End Function
```

```text output
120
3628800
```

### تمرين 2: هل العدد أولي؟

اكتب دالة `IsPrime(n) As Boolean` (العدد الأولي لا يقبل القسمة إلا على 1 وعلى نفسه)، واستخدمها لطباعة الأعداد الأولية من 2 إلى 30 في سطر واحد.

```vb exercise
Sub Main()
    ' استخدم IsPrime داخل حلقة
End Sub

Function IsPrime(ByVal n As Long) As Boolean
End Function
```

```vb solution
Sub Main()
    Dim i As Long, line As String
    For i = 2 To 30
        If IsPrime(i) Then line = line & i & " "
    Next i
    Debug.Print Trim(line)
End Sub

Function IsPrime(ByVal n As Long) As Boolean
    Dim d As Long
    If n < 2 Then Exit Function
    For d = 2 To Int(Sqr(n))
        If n Mod d = 0 Then Exit Function
    Next d
    IsPrime = True
End Function
```

```text output
2 3 5 7 11 13 17 19 23 29
```

(لاحظ أن `Exit Function` قبل `IsPrime = True` تُرجع القيمة الافتراضية `False`.)

### تمرين 3: تبديل بإجراء

اكتب إجراء `Swap(a, b)` يبدّل قيمتي متغيرين (فكّر: `ByVal` أم `ByRef`؟).

```vb exercise
Sub Main()
    Dim x As Integer, y As Integer
    x = 1: y = 2
    Swap x, y
    Debug.Print "x = " & x & ", y = " & y
End Sub
```

```vb solution
Sub Main()
    Dim x As Integer, y As Integer
    x = 1: y = 2
    Swap x, y
    Debug.Print "x = " & x & ", y = " & y
End Sub

Sub Swap(ByRef a As Integer, ByRef b As Integer)
    Dim t As Integer
    t = a
    a = b
    b = t
End Sub
```

```text output
x = 2, y = 1
```

## اختبر نفسك

```quiz
{"question": "ما الفرق الأساسي بين Sub و Function؟", "choices": ["Sub أسرع", "Function تُرجع قيمة، وSub لا تُرجع", "Sub للنماذج فقط", "لا فرق"], "answer": 1, "explanation": "الدالة تُرجع نتيجة نضعها في اسمها، والإجراء ينفّذ عملًا فقط."}
```

```quiz
{"question": "ما طريقة التمرير الافتراضية في VB6 إذا لم تكتب شيئًا؟", "choices": ["ByVal", "ByRef", "Optional", "Static"], "answer": 1, "explanation": "الافتراضي في VB6 هو ByRef، أي يُرسل المتغير الأصلي."}
```

```quiz
{"question": "كيف تُرجع الدالة MyFunc القيمة 5؟", "choices": ["Return 5", "MyFunc = 5", "Exit 5", "Result = 5"], "answer": 1, "explanation": "في VB6 نضع النتيجة في اسم الدالة نفسه."}
```

```quiz
{"question": "أي استدعاء صحيح للإجراء  Sub Show(a As Integer, b As Integer) ؟", "choices": ["Show(1, 2)", "Show 1, 2", "Call Show 1, 2", "Show[1, 2]"], "answer": 1, "explanation": "بدون Call لا نضع أقواسًا: Show 1, 2. ومع Call نضعها: Call Show(1, 2)."}
```

## الخلاصة

- `Sub` لعمل، و`Function` لنتيجة تُوضع في اسم الدالة.
- `ByVal` يرسل نسخة، و`ByRef` (الافتراضي) يرسل الأصل.
- `Optional` لمعامل اختياري بقيمة افتراضية، و`Exit Sub`/`Exit Function` للخروج المبكر.
