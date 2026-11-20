# الدرس 21: المجموعات - Collection

**في هذا الدرس ستتعلم:**

- الكائن `Collection`: قائمة مرنة تكبر وتصغر بسهولة.
- الطرق `Add` و`Remove` و`Item` والخاصية `Count`.
- **المفاتيح** (Keys) للوصول إلى العنصر باسمه بدل رقمه.
- المرور على العناصر بـ `For Each`.

## حقيبة مرنة بدل خزانة ثابتة

المصفوفة مثل **خزانة** بعدد أدراج ثابت: إذا أردت درجًا إضافيًّا تحتاج `ReDim Preserve`، وإذا حذفت عنصرًا من المنتصف يبقى مكانه فارغًا.
**المجموعة** (Collection) مثل **حقيبة مرنة**: تضع فيها ما تشاء فتكبر، وتُخرج منها فتصغر وتتراص العناصر تلقائيًّا. ويمكنك أن تعلّق على كل شيء فيها **بطاقة باسم** (مفتاح) لتجده بسرعة.

## إنشاء مجموعة والإضافة إليها

المجموعة **كائن**، لذلك ننشئها بالكلمة `New`:

```vb run
Sub Main()
    Dim fruits As New Collection
    fruits.Add "تفاح"
    fruits.Add "موز"
    fruits.Add "عنب"
    Debug.Print "عدد العناصر: " & fruits.Count
    Debug.Print "الأول: " & fruits(1)
    Debug.Print "الأخير: " & fruits.Item(fruits.Count)
End Sub
```

```text output
عدد العناصر: 3
الأول: تفاح
الأخير: عنب
```

> ⚠️ ترقيم عناصر المجموعة يبدأ من **1** (وليس من 0 كالمصفوفات).

`fruits(1)` اختصار لـ `fruits.Item(1)`.

## For Each: المرور على كل العناصر

`For Each` تمر على العناصر واحدًا واحدًا دون الحاجة لعدّاد. متغير الحلقة يكون من نوع `Variant`:

```vb run
Sub Main()
    Dim colors As New Collection, c As Variant
    colors.Add "أحمر"
    colors.Add "أخضر"
    colors.Add "أزرق"
    For Each c In colors
        Debug.Print "- " & c
    Next c
End Sub
```

```text output
- أحمر
- أخضر
- أزرق
```

## المفاتيح: الوصول بالاسم

الطريقة `Add` تقبل معاملًا ثانيًا هو **المفتاح** (Key): نص فريد يميّز العنصر. مثل دليل الهاتف: تبحث بالاسم وليس برقم الصفحة:

```vb run
Sub Main()
    Dim capitals As New Collection
    capitals.Add "القاهرة", "EG"
    capitals.Add "الرياض", "SA"
    capitals.Add "عمّان", "JO"
    capitals.Add "الرباط", "MA"

    Debug.Print "عاصمة السعودية: " & capitals("SA")
    Debug.Print "عاصمة المغرب: " & capitals.Item("MA")

    capitals.Remove "JO"          ' حذف بالمفتاح
    capitals.Remove 1             ' حذف بالرقم (الأول: القاهرة)
    Debug.Print "المتبقي: " & capitals.Count
    Debug.Print "الأول الآن: " & capitals(1)
End Sub
```

```text output
عاصمة السعودية: الرياض
عاصمة المغرب: الرباط
المتبقي: 2
الأول الآن: الرياض
```

لاحظ أنه بعد حذف العنصر الأول أصبح "الرياض" هو رقم 1؛ العناصر تتراص تلقائيًّا.

## هل المفتاح موجود؟

طلب مفتاح غير موجود يعطي خطأ (رقم 5)، وإضافة مفتاح مكرر تعطي خطأ (رقم 457). نستخدم `On Error` لكتابة دالة تفحص الوجود:

```vb run
Option Explicit

Sub Main()
    Dim stock As New Collection
    stock.Add 12, "pen"
    stock.Add 3, "book"
    Debug.Print "pen موجود؟ " & HasKey(stock, "pen")
    Debug.Print "bag موجود؟ " & HasKey(stock, "bag")
    If HasKey(stock, "book") Then Debug.Print "الكمية من book: " & stock("book")
End Sub

Function HasKey(col As Collection, ByVal key As String) As Boolean
    Dim tmp As Variant
    On Error GoTo NotThere
    tmp = col(key)
    HasKey = True
    Exit Function
NotThere:
    HasKey = False
End Function
```

```text output
pen موجود؟ True
bag موجود؟ False
الكمية من book: 3
```

## مثال: عدّ تكرار الكلمات

المجموعة بالمفاتيح مفيدة جدًّا للعدّ. لكن قيمة عنصر في المجموعة لا يمكن تعديلها مباشرة، فنحذفه ونضيفه من جديد بالقيمة الجديدة:

```vb run
Option Explicit

Sub Main()
    Dim words() As String, w As Variant, counts As New Collection, n As Long
    Dim seen As New Collection
    words = Split("red blue red green blue red", " ")
    For Each w In words
        On Error Resume Next
        n = 0
        n = counts(w)                ' إن لم يوجد يبقى 0
        counts.Remove w
        On Error GoTo 0
        If n = 0 Then seen.Add w     ' أول مرة نرى الكلمة: احفظ ترتيبها
        counts.Add n + 1, w
    Next w
    For Each w In seen
        Debug.Print w & ": " & counts(w)
    Next w
End Sub
```

```text output
red: 3
blue: 2
green: 1
```

## المجموعة في النموذج

مثال: دفتر درجات يحفظ الدرجات في مجموعة على مستوى النموذج:

<!-- test: {"steps": [["set", "txtMark", "Text", "80"], ["click", "cmdAdd"], ["set", "txtMark", "Text", "90"], ["click", "cmdAdd"], ["set", "txtMark", "Text", "70"], ["click", "cmdAdd"], ["click", "cmdStats"]], "expect": {"lblStats.Caption": "العدد 3 - المتوسط 80"}} -->
```vb form run
Begin VB.Form Form1
   Caption         =   "دفتر الدرجات"
   ClientWidth     =   4800
   ClientHeight    =   2000
   Begin VB.TextBox txtMark
      Left            =   240
      Top             =   240
      Width           =   1500
      Height          =   400
   End
   Begin VB.CommandButton cmdAdd
      Caption         =   "أضف"
      Left            =   1900
      Top             =   200
      Width           =   1200
      Height          =   500
   End
   Begin VB.CommandButton cmdStats
      Caption         =   "إحصاء"
      Left            =   3250
      Top             =   200
      Width           =   1200
      Height          =   500
   End
   Begin VB.Label lblStats
      Left            =   240
      Top             =   1000
      Width           =   4200
      Height          =   400
   End
End

Option Explicit
Private marks As New Collection

Private Sub cmdAdd_Click()
    marks.Add Val(txtMark.Text)
    txtMark.Text = ""
End Sub

Private Sub cmdStats_Click()
    Dim m As Variant, total As Double
    If marks.Count = 0 Then Exit Sub
    For Each m In marks
        total = total + m
    Next m
    lblStats.Caption = "العدد " & marks.Count & " - المتوسط " & total / marks.Count
End Sub
```

## مصفوفة أم مجموعة؟

| | المصفوفة | المجموعة |
|---|---|---|
| الحجم | ثابت (يتغير بـ `ReDim`) | مرن تلقائيًّا |
| الترقيم | من 0 عادة | من 1 |
| الوصول بالاسم | لا | نعم بالمفتاح |
| تعديل عنصر | `a(2) = 5` مباشرة | حذف ثم إضافة |
| السرعة مع الأرقام | أسرع | أبطأ قليلًا |

## أخطاء شائعة

- **نسيان `New`:** `Dim c As Collection` ثم `c.Add` تعطي الخطأ 91 لأن الكائن لم يُنشأ. اكتب `Dim c As New Collection` أو `Set c = New Collection`.
- **البدء من 0:** `c(0)` خطأ؛ الأول هو `c(1)`.
- **مفتاح مكرر:** الخطأ 457 "This key is already associated with an element of this collection".
- **مفتاح رقمي:** المفتاح يجب أن يكون **نصًّا**. `c.Add "x", 5` خطأ؛ اكتب `c.Add "x", "5"` أو `CStr(5)`.
- **محاولة تعديل العنصر مباشرة:** `c(1) = "جديد"` لا تعمل؛ احذف ثم أضف.

## تمارين

### تمرين 1: قائمة الضيوف

أنشئ مجموعة وأضف إليها: Sara، Adam، Laila، Yasser. احذف Adam، ثم اطبع العدد وكل الأسماء.

```vb exercise
Sub Main()
    Dim guests As New Collection
End Sub
```

```vb solution
Sub Main()
    Dim guests As New Collection, g As Variant
    guests.Add "Sara", "Sara"
    guests.Add "Adam", "Adam"
    guests.Add "Laila", "Laila"
    guests.Add "Yasser", "Yasser"
    guests.Remove "Adam"
    Debug.Print "عدد الضيوف: " & guests.Count
    For Each g In guests
        Debug.Print g
    Next g
End Sub
```

```text output
عدد الضيوف: 3
Sara
Laila
Yasser
```

### تمرين 2: أسعار المنتجات

خزّن أسعار المنتجات بمفاتيح: tea = 25، coffee = 60، juice = 35. ثم احسب ثمن طلب فيه: 2 tea و 1 coffee.

```vb exercise
Sub Main()
    Dim prices As New Collection
End Sub
```

```vb solution
Sub Main()
    Dim prices As New Collection
    prices.Add 25, "tea"
    prices.Add 60, "coffee"
    prices.Add 35, "juice"
    Debug.Print "ثمن الطلب = " & (2 * prices("tea") + 1 * prices("coffee"))
End Sub
```

```text output
ثمن الطلب = 110
```

## اختبر نفسك

```quiz
{"question": "من أين يبدأ ترقيم عناصر Collection؟", "choices": ["0", "1", "-1", "حسب الإعلان"], "answer": 1, "explanation": "المجموعات تبدأ من 1."}
```

```quiz
{"question": "ما الذي يجب كتابته لإنشاء المجموعة قبل استخدامها؟", "choices": ["ReDim", "New", "Open", "Load"], "answer": 1, "explanation": "المجموعة كائن، فننشئها بـ New."}
```

```quiz
{"question": "ما فائدة المعامل الثاني في  c.Add \"القاهرة\", \"EG\" ؟", "choices": ["ترتيب العنصر", "مفتاح للوصول إلى العنصر بالاسم", "لون العنصر", "عدد النسخ"], "answer": 1, "explanation": "المعامل الثاني مفتاح نصي فريد: c(\"EG\")."}
```

```quiz
{"question": "ماذا يحدث لرقم العنصر الثالث إذا حذفنا العنصر الأول؟", "choices": ["يبقى 3", "يصبح 2", "يصبح 0", "يُحذف أيضًا"], "answer": 1, "explanation": "العناصر تتراص بعد الحذف، فيصبح الثالث ثانيًا."}
```

## الخلاصة

- `Collection` قائمة مرنة: `Add` و`Remove` و`Item` و`Count`، والترقيم من 1.
- المفتاح النصي يسمح بالوصول بالاسم: `c("EG")`.
- `For Each` للمرور على العناصر، و`On Error` لفحص وجود مفتاح.
