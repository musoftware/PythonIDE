# الدرس 4: المتغيرات وأنواع البيانات

**في هذا الدرس ستتعلم:**

- ما هو **المتغير** وكيف تعلن عنه بـ `Dim`.
- أنواع البيانات: `Integer` و`Long` و`Double` و`String` و`Boolean` و`Variant`.
- الثوابت `Const`، والأمر `Option Explicit`.
- قواعد تسمية المتغيرات.

## المتغير صندوق له اسم

تخيّل مجموعة صناديق في مخزن، على كل صندوق **ملصق باسمه**، وبداخله شيء واحد. يمكنك أن تفتح الصندوق وتنظر ما فيه، أو تُخرج ما فيه وتضع شيئًا جديدًا.
**المتغير** (Variable) هو صندوق في ذاكرة الحاسوب: له **اسم**، وله **نوع** (ما الذي يصلح أن يوضع فيه)، وفيه **قيمة** يمكن أن تتغير أثناء التشغيل.

```vb run
Sub Main()
    Dim age As Integer       ' أنشئ صندوقًا اسمه age يقبل أعدادًا صحيحة
    age = 20                 ' ضع فيه 20
    Debug.Print "العمر: " & age
    age = age + 1            ' خذ القيمة القديمة وأضف إليها 1
    Debug.Print "بعد سنة: " & age
End Sub
```

```text output
العمر: 20
بعد سنة: 21
```

السطر `age = age + 1` قد يبدو غريبًا في الرياضيات، لكن علامة `=` هنا معناها **"ضع في"** (إسناد)، وليس "يساوي". اقرأه هكذا: "احسب age + 1 ثم ضع الناتج في age".

## الإعلان بـ Dim

الصيغة: `Dim الاسم As النوع`. ويمكن الإعلان عن عدة متغيرات في سطر واحد:

```vb
Dim firstName As String, lastName As String
```

> ⚠️ **انتبه:** `Dim a, b As Integer` تجعل `b` فقط من نوع `Integer`، أما `a` فتصبح `Variant`. اكتب النوع لكل متغير.

## أهم أنواع البيانات

| النوع | يخزّن | مثال | القيمة الابتدائية |
|---|---|---|---|
| `Integer` | عدد صحيح من -32,768 إلى 32,767 | `25` | `0` |
| `Long` | عدد صحيح كبير (حتى نحو 2 مليار) | `150000` | `0` |
| `Double` | عدد بكسور عشرية | `3.75` | `0` |
| `String` | نص | `"مرحبا"` | `""` (نص فارغ) |
| `Boolean` | صح أو خطأ فقط | `True` / `False` | `False` |
| `Variant` | أي شيء (النوع المرن) | أي قيمة | `Empty` (فارغ) |
| `Date` | تاريخ ووقت | `#1/15/2024#` | - |

اختيار النوع مثل اختيار الوعاء المناسب: لا تضع الحساء في طبق مسطّح! الأعداد التي قد تكبر (عدد السكان، المبالغ بالقروش) ضعها في `Long`، والأسعار والأوزان في `Double`.

```vb run
Sub Main()
    Dim students As Integer
    Dim population As Long
    Dim price As Double
    Dim city As String
    Dim isOpen As Boolean

    students = 35
    population = 10000000
    price = 12.75
    city = "القاهرة"
    isOpen = True

    Debug.Print "الطلاب: " & students
    Debug.Print "السكان: " & population
    Debug.Print "السعر: " & price
    Debug.Print "المدينة: " & city
    Debug.Print "المحل مفتوح؟ " & isOpen
End Sub
```

```text output
الطلاب: 35
السكان: 10000000
السعر: 12.75
المدينة: القاهرة
المحل مفتوح؟ True
```

## القيم الابتدائية

المتغير الجديد ليس "فارغًا تمامًا": الأعداد تبدأ بصفر، والنصوص بنص فارغ، و`Boolean` بـ `False`:

```vb run
Sub Main()
    Dim n As Integer
    Dim s As String
    Dim ok As Boolean
    Debug.Print "n = " & n
    Debug.Print "s = [" & s & "]"
    Debug.Print "ok = " & ok
End Sub
```

```text output
n = 0
s = []
ok = False
```

## النوع المرن Variant

إذا لم تكتب `As ...` يصبح المتغير `Variant`، يقبل أي قيمة. الدالة `TypeName` تخبرك بنوع ما بداخله الآن:

```vb run
Sub Main()
    Dim box As Variant
    Debug.Print TypeName(box)
    box = 10
    Debug.Print TypeName(box)
    box = "نص"
    Debug.Print TypeName(box)
    box = 2.5
    Debug.Print TypeName(box)
End Sub
```

```text output
Empty
Integer
String
Double
```

`Variant` مريح لكنه أبطأ ويُخفي الأخطاء، لذلك يفضّل المبرمجون تحديد النوع دائمًا.

## الأعداد الصحيحة تُقرَّب

إذا وضعت عددًا عشريًّا في متغير `Integer` أو `Long` يُقرَّب إلى أقرب عدد صحيح. وعند النصف بالضبط يُقرَّب إلى **العدد الزوجي** الأقرب (ما يسمى "تقريب المصرفيين"):

```vb run
Sub Main()
    Dim k As Integer
    k = 7.4
    Debug.Print k
    k = 7.6
    Debug.Print k
    k = 6.5
    Debug.Print k
    k = 7.5
    Debug.Print k
End Sub
```

```text output
7
8
6
8
```

## الثوابت Const

**الثابت** (Constant) صندوق مغلق: تضع قيمته مرة واحدة ولا تتغير. مفيد للقيم المعروفة مثل نسبة الضريبة:

```vb run
Sub Main()
    Const VAT As Double = 0.14
    Dim price As Double
    price = 1000
    Debug.Print "الضريبة: " & price * VAT
    Debug.Print "الإجمالي: " & price + price * VAT
End Sub
```

```text output
الضريبة: 140
الإجمالي: 1140
```

لو حاولت كتابة `VAT = 0.2` بعد ذلك سيرفض البرنامج.

## Option Explicit: حارس الأخطاء

إذا كتبت في أول الملف `Option Explicit` يصبح **الإعلان إجباريًّا**: أي متغير غير مُعلَن بـ `Dim` يُعتبر خطأ. هذا يحميك من أخطاء الإملاء:
بدونه، لو كتبت `totl` بدلًا من `total` سيُنشئ البرنامج متغيرًا جديدًا فارغًا بصمت، وستحصل على نتيجة خاطئة دون أن تعرف السبب.

```vb run
Option Explicit

Sub Main()
    Dim total As Integer
    total = 5 + 7
    Debug.Print "المجموع = " & total
End Sub
```

```text output
المجموع = 12
```

> 💡 **عادة ذهبية:** ابدأ كل ملف كود بـ `Option Explicit`. البيئة تكتبه لك تلقائيًّا في النماذج الجديدة.

## قواعد التسمية

- يبدأ الاسم بحرف إنجليزي، ثم حروف أو أرقام أو شرطة سفلية `_`: `total2`، `first_name`.
- لا مسافات ولا رموز: `my name` و`price$x` غير مقبولة.
- لا يصح استخدام الكلمات المحجوزة مثل `Dim` و`If` و`For` كأسماء.
- الحروف الكبيرة والصغيرة سواء: `Age` و`age` اسم واحد.
- اختر أسماء ذات معنى: `studentCount` أفضل بكثير من `x`.

## أخطاء شائعة

- **استخدام متغير قبل إعطائه قيمة** ثم التعجب من الصفر في النتيجة.
- **وضع نص في متغير عددي:** `Dim n As Integer` ثم `n = "abc"` يسبب خطأ عدم تطابق الأنواع (Type mismatch).
- **عدد كبير في `Integer`:** أكبر قيمة 32,767. لعدد مثل 50,000 استخدم `Long`.
- **أخطاء الإملاء في أسماء المتغيرات** بدون `Option Explicit`.

## تمارين

### تمرين 1: مساحة المستطيل

أعلن عن متغيرين `length` و`width` من نوع `Double` وأعطهما 8 و 5.5، ثم احسب المساحة في متغير ثالث `area` واطبعها.

```vb exercise
Option Explicit

Sub Main()
    ' Dim ...
End Sub
```

```vb solution
Option Explicit

Sub Main()
    Dim length As Double
    Dim width As Double
    Dim area As Double
    length = 8
    width = 5.5
    area = length * width
    Debug.Print "المساحة = " & area
End Sub
```

```text output
المساحة = 44
```

### تمرين 2: تبديل قيمتين

لديك `a = 3` و `b = 9`. بدّل القيمتين بحيث يصبح `a = 9` و `b = 3`.
تلميح: كيف تبدّل محتوى كوبين؟ تحتاج كوبًا ثالثًا فارغًا!

```vb exercise
Sub Main()
    Dim a As Integer, b As Integer
    a = 3
    b = 9
    ' بدّل هنا
    Debug.Print "a = " & a & ", b = " & b
End Sub
```

```vb solution
Sub Main()
    Dim a As Integer, b As Integer, temp As Integer
    a = 3
    b = 9
    temp = a
    a = b
    b = temp
    Debug.Print "a = " & a & ", b = " & b
End Sub
```

```text output
a = 9, b = 3
```

### تمرين 3: الراتب السنوي

الراتب الشهري 7500. احسب الراتب السنوي في متغير من نوع `Long` واطبعه.

```vb exercise
Sub Main()
    ' تذكّر: 7500 × 12 أكبر من 32767
End Sub
```

```vb solution
Sub Main()
    Dim monthly As Long
    Dim yearly As Long
    monthly = 7500
    yearly = monthly * 12
    Debug.Print "الراتب السنوي: " & yearly
End Sub
```

```text output
الراتب السنوي: 90000
```

## اختبر نفسك

```quiz
{"question": "أي نوع مناسب لتخزين سعر مثل 19.99؟", "choices": ["Integer", "Boolean", "Double", "Long"], "answer": 2, "explanation": "Double يخزّن الأعداد ذات الكسور العشرية."}
```

```quiz
{"question": "ما معنى  x = x + 1 ؟", "choices": ["x يساوي x + 1 (معادلة مستحيلة)", "زِد قيمة x بمقدار 1", "اطبع x", "خطأ في الصياغة"], "answer": 1, "explanation": "علامة = هنا إسناد: احسب الطرف الأيمن ثم ضعه في المتغير."}
```

```quiz
{"question": "ما القيمة الابتدائية لمتغير من نوع String؟", "choices": ["0", "نص فارغ \"\"", "False", "Null"], "answer": 1, "explanation": "النصوص تبدأ بنص فارغ، والأعداد بصفر، وBoolean بـ False."}
```

```quiz
{"question": "ما فائدة Option Explicit؟", "choices": ["تسريع البرنامج", "إجبار الإعلان عن المتغيرات لاكتشاف أخطاء الإملاء", "طباعة المتغيرات", "حذف المتغيرات"], "answer": 1, "explanation": "مع Option Explicit يرفض البرنامج أي متغير غير مُعلن، فتكتشف الأخطاء مبكرًا."}
```

```quiz
{"question": "في السطر  Dim a, b As Long  ما نوع a؟", "choices": ["Long", "Variant", "Integer", "String"], "answer": 1, "explanation": "النوع يخص المتغير الذي كُتب بعده فقط، فيصبح a من نوع Variant."}
```

## الخلاصة

- المتغير صندوق له اسم ونوع وقيمة: `Dim name As Type`.
- `=` في الكود معناها "ضع في".
- اختر النوع المناسب، واستخدم `Const` للقيم الثابتة، و`Option Explicit` في كل ملف.
