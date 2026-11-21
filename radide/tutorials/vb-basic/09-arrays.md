# الدرس 9: المصفوفات

**في هذا الدرس ستتعلم:**

- ما هي **المصفوفة** ولماذا نحتاجها.
- المصفوفة الثابتة، و`LBound` و`UBound`.
- المصفوفة الديناميكية بـ `ReDim` و`ReDim Preserve`.
- المصفوفة ثنائية الأبعاد، والدالتين `Array` و`Split`.

## صفّ من الصناديق

لو أردت تخزين درجات 30 طالبًا، هل ستعلن عن 30 متغيرًا: `grade1` و`grade2` ... `grade30`؟ هذا متعب جدًّا!
**المصفوفة** (Array) مثل خزانة فيها أدراج مرقّمة: اسم واحد للخزانة كلها، وكل درج له رقم يُسمّى **الفهرس** (Index).

```vb run
Sub Main()
    Dim grades(4) As Integer      ' خمسة أدراج: من 0 إلى 4
    grades(0) = 85
    grades(1) = 92
    grades(2) = 78
    grades(3) = 64
    grades(4) = 99
    Debug.Print "درجة الطالب الثالث: " & grades(2)
End Sub
```

```text output
درجة الطالب الثالث: 78
```

> ⚠️ **مهم:** `Dim grades(4)` تُنشئ **خمسة** عناصر، لأن الترقيم يبدأ من **صفر**: 0، 1، 2، 3، 4. الرقم 4 هو آخر فهرس، وليس عدد العناصر.

يمكن تحديد البداية والنهاية بنفسك باستخدام `To`:

```vb
Dim months(1 To 12) As String
```

## المصفوفات والحلقات صديقان

قوة المصفوفة تظهر مع حلقة `For`: الفهرس يمكن أن يكون متغيرًا! والدالتان `LBound` و`UBound` تُرجعان أول وآخر فهرس:

```vb run
Sub Main()
    Dim grades(1 To 5) As Integer, i As Integer, total As Integer
    grades(1) = 85: grades(2) = 92: grades(3) = 78: grades(4) = 64: grades(5) = 99

    For i = LBound(grades) To UBound(grades)
        total = total + grades(i)
    Next i
    Debug.Print "المجموع = " & total
    Debug.Print "المتوسط = " & total / 5
End Sub
```

```text output
المجموع = 418
المتوسط = 83.6
```

(النقطتان `:` تسمحان بكتابة أكثر من أمر في سطر واحد.)

### مثال: البحث عن الأكبر

```vb run
Sub Main()
    Dim prices(4) As Double, i As Integer, maxPrice As Double
    prices(0) = 45.5: prices(1) = 120: prices(2) = 33: prices(3) = 210.25: prices(4) = 99
    maxPrice = prices(0)
    For i = 1 To UBound(prices)
        If prices(i) > maxPrice Then maxPrice = prices(i)
    Next i
    Debug.Print "أغلى سعر: " & maxPrice
End Sub
```

```text output
أغلى سعر: 210.25
```

## المصفوفة الديناميكية: `ReDim`

أحيانًا لا نعرف الحجم مسبقًا (مثلًا: عدد الأسماء التي سيُدخلها المستخدم). نعلن عن المصفوفة بأقواس فارغة، ثم نحدد حجمها لاحقًا بـ `ReDim`:

```vb run
Sub Main()
    Dim names() As String, count As Integer, i As Integer
    count = 3
    ReDim names(1 To count)
    names(1) = "علي"
    names(2) = "منى"
    names(3) = "كريم"

    ReDim Preserve names(1 To 4)     ' كبّر المصفوفة مع الاحتفاظ بالقديم
    names(4) = "هدى"

    For i = 1 To UBound(names)
        Debug.Print i & ") " & names(i)
    Next i
End Sub
```

```text output
1) علي
2) منى
3) كريم
4) هدى
```

- `ReDim` وحدها **تمسح** المحتويات القديمة، مثل إفراغ الخزانة وتغييرها.
- `ReDim Preserve` تكبّر المصفوفة و**تحتفظ** بالقيم الموجودة.

## المصفوفة ثنائية الأبعاد

مثل جدول فيه صفوف وأعمدة، أو مقاعد في قاعة سينما: لكل مقعد رقم صف ورقم عمود.

```vb run
Sub Main()
    Dim table(1 To 3, 1 To 3) As Integer
    Dim r As Integer, c As Integer, line As String
    For r = 1 To 3
        For c = 1 To 3
            table(r, c) = r * c
        Next c
    Next r

    For r = 1 To 3
        line = ""
        For c = 1 To 3
            line = line & table(r, c) & " "
        Next c
        Debug.Print line
    Next r
    Debug.Print "العنصر في الصف 2 والعمود 3: " & table(2, 3)
End Sub
```

```text output
1 2 3
2 4 6
3 6 9
العنصر في الصف 2 والعمود 3: 6
```

## Array و Split

`Array(...)` تصنع مصفوفة جاهزة (في متغير `Variant`) بسرعة، و`Split` تقطع نصًّا إلى مصفوفة عند فاصل معيّن:

```vb run
Sub Main()
    Dim days As Variant, parts() As String, i As Integer
    days = Array("السبت", "الأحد", "الاثنين")
    Debug.Print "أول يوم: " & days(0)

    parts = Split("تفاح,موز,برتقال", ",")
    For i = 0 To UBound(parts)
        Debug.Print "- " & parts(i)
    Next i
    Debug.Print Join(parts, " + ")
End Sub
```

```text output
أول يوم: السبت
- تفاح
- موز
- برتقال
تفاح + موز + برتقال
```

`Join` تعمل العكس: تجمع عناصر المصفوفة في نص واحد بينها فاصل.

## أخطاء شائعة

- **تجاوز حدود المصفوفة:** `Dim a(4)` ثم `a(5) = 1` تعطي الخطأ "Subscript out of range" (الفهرس خارج النطاق).
- **نسيان أن البداية صفر:** `Dim a(10)` فيها 11 عنصرًا.
- **`ReDim` بدون `Preserve`** يمسح البيانات القديمة.
- **استخدام مصفوفة ديناميكية قبل `ReDim`:** لا توجد أدراج بعد!
- **كتابة الحد الأعلى ثابتًا في الحلقة:** استخدم `UBound(a)` بدلًا من رقم، حتى لا تنكسر الحلقة إذا تغيّر الحجم.

## تمارين

### تمرين 1: درجات الحرارة

خزّن درجات حرارة أسبوع (7 أيام): 30، 32، 35، 31، 29، 28، 32 في مصفوفة، ثم اطبع المتوسط وأقل درجة.

```vb exercise
Sub Main()
    Dim t(1 To 7) As Integer
End Sub
```

```vb solution
Sub Main()
    Dim t(1 To 7) As Integer, i As Integer, total As Integer, minT As Integer
    t(1) = 30: t(2) = 32: t(3) = 35: t(4) = 31: t(5) = 29: t(6) = 28: t(7) = 32
    minT = t(1)
    For i = 1 To 7
        total = total + t(i)
        If t(i) < minT Then minT = t(i)
    Next i
    Debug.Print "المتوسط = " & total / 7
    Debug.Print "أقل درجة = " & minT
End Sub
```

```text output
المتوسط = 31
أقل درجة = 28
```

### تمرين 2: اعكس المصفوفة

لديك المصفوفة `Array(1, 2, 3, 4, 5)`. اطبع عناصرها بالعكس في سطر واحد: `5 4 3 2 1`.

```vb exercise
Sub Main()
    Dim a As Variant
    a = Array(1, 2, 3, 4, 5)
End Sub
```

```vb solution
Sub Main()
    Dim a As Variant, i As Integer, line As String
    a = Array(1, 2, 3, 4, 5)
    For i = UBound(a) To LBound(a) Step -1
        line = line & a(i) & " "
    Next i
    Debug.Print Trim(line)
End Sub
```

```text output
5 4 3 2 1
```

### تمرين 3: عدد الكلمات

استخدم `Split` لحساب عدد كلمات الجملة "البرمجة ممتعة جدا مع BASIC".

```vb exercise
Sub Main()
    Dim words() As String
End Sub
```

```vb solution
Sub Main()
    Dim words() As String
    words = Split("البرمجة ممتعة جدا مع BASIC", " ")
    Debug.Print "عدد الكلمات = " & (UBound(words) + 1)
End Sub
```

```text output
عدد الكلمات = 5
```

## اختبر نفسك

```quiz
{"question": "كم عنصرًا في المصفوفة  Dim a(5) As Integer ؟", "choices": ["5", "6", "4", "10"], "answer": 1, "explanation": "الفهارس من 0 إلى 5، أي 6 عناصر."}
```

```quiz
{"question": "ما الفرق بين ReDim و ReDim Preserve؟", "choices": ["لا فرق", "Preserve تحتفظ بالقيم القديمة عند تغيير الحجم", "Preserve تمسح المصفوفة", "ReDim للنصوص فقط"], "answer": 1, "explanation": "ReDim وحدها تمسح المحتوى، وReDim Preserve تحتفظ به."}
```

```quiz
{"question": "ماذا تُرجع UBound(a)؟", "choices": ["عدد العناصر دائمًا", "آخر فهرس في المصفوفة", "أكبر قيمة في المصفوفة", "أول فهرس"], "answer": 1, "explanation": "UBound تُرجع آخر فهرس، وLBound أول فهرس."}
```

```quiz
{"question": "ما ناتج  Split(\"a-b-c\", \"-\")(1) ؟", "choices": ["a", "b", "c", "-"], "answer": 1, "explanation": "Split تعطي مصفوفة (\"a\", \"b\", \"c\") والعنصر رقم 1 هو \"b\"."}
```

## الخلاصة

- المصفوفة اسم واحد لمجموعة عناصر مرقّمة، والترقيم يبدأ من 0 ما لم تستخدم `To`.
- `LBound` و`UBound` لحدود المصفوفة، و`ReDim Preserve` لتكبيرها دون فقد البيانات.
- `Split` تقطع النص إلى مصفوفة، و`Join` تجمعها.
