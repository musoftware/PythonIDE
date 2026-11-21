# الدرس 20: الأنواع المعرّفة - Type ... End Type

**في هذا الدرس ستتعلم:**

- تجميع عدة بيانات مترابطة في **نوع معرّف** (User-Defined Type) بـ `Type ... End Type`.
- الوصول إلى **الحقول** بالنقطة، واستخدام `With`.
- مصفوفات من الأنواع المعرّفة.
- تمرير نوع معرّف إلى إجراء.

## بطاقة الهوية

بطاقة الهوية فيها عدة معلومات عن شخص واحد: الاسم، وتاريخ الميلاد، والعنوان. كلها مكتوبة على **بطاقة واحدة**.
لو أردنا تخزين بيانات طالب بالمتغيرات العادية، سنحتاج متغيرًا للاسم، وآخر للعمر، وثالثًا للمعدل... ومع 30 طالبًا تصبح الفوضى كبيرة!
**النوع المعرّف** يصنع "بطاقة" جديدة تجمع هذه **الحقول** (Fields) معًا تحت اسم واحد.

## تعريف النوع واستخدامه

يُكتب `Type` في **أعلى الوحدة** (خارج أي إجراء):

```vb run
Option Explicit

Private Type Student
    Name As String
    Age As Integer
    Average As Double
End Type

Sub Main()
    Dim s As Student
    s.Name = "Omar"
    s.Age = 16
    s.Average = 91.5
    Debug.Print s.Name & " - " & s.Age & " سنة - المعدل " & s.Average
End Sub
```

```text output
Omar - 16 سنة - المعدل 91.5
```

- `Student` أصبح **نوعًا جديدًا** مثل `Integer` و`String`، نعلن به متغيرات: `Dim s As Student`.
- نصل إلى كل حقل بالنقطة: `s.Name`.
- `Private Type` يجعل النوع داخل هذه الوحدة فقط، و`Public Type` (في وحدة `.bas`) يجعله متاحًا للمشروع كله.

## With: اختصار الكتابة

عندما نكتب حقولًا كثيرة لمتغير واحد، تُوفّر `With` تكرار اسمه:

```vb run
Private Type Product
    Code As String
    Title As String
    Price As Double
    Quantity As Integer
End Type

Sub Main()
    Dim p As Product
    With p
        .Code = "P-100"
        .Title = "Keyboard"
        .Price = 350
        .Quantity = 4
    End With
    Debug.Print p.Title & ": " & p.Quantity & " x " & p.Price & " = " & (p.Quantity * p.Price)
End Sub
```

```text output
Keyboard: 4 x 350 = 1400
```

داخل `With p ... End With` تعني `.Price` نفسَ `p.Price`.

## مصفوفة من البطاقات

هنا تظهر القوة الحقيقية: مصفوفة كل عنصر فيها "بطاقة" كاملة، مثل درج فيه بطاقات كل الطلاب:

```vb run
Option Explicit

Private Type Student
    Name As String
    Grade As Integer
End Type

Sub Main()
    Dim cls(1 To 4) As Student
    Dim i As Integer, best As Integer

    cls(1).Name = "Ali":   cls(1).Grade = 78
    cls(2).Name = "Hoda":  cls(2).Grade = 95
    cls(3).Name = "Samir": cls(3).Grade = 88
    cls(4).Name = "Rana":  cls(4).Grade = 64

    best = 1
    For i = 1 To 4
        Debug.Print cls(i).Name & ": " & cls(i).Grade
        If cls(i).Grade > cls(best).Grade Then best = i
    Next i
    Debug.Print "الأول على الفصل: " & cls(best).Name
End Sub
```

```text output
Ali: 78
Hoda: 95
Samir: 88
Rana: 64
الأول على الفصل: Hoda
```

## تمرير النوع إلى إجراء

يمكن تمرير متغير من نوع معرّف إلى إجراء (ويُمرَّر دائمًا `ByRef`):

```vb run
Option Explicit

Private Type Rectangle
    Width As Double
    Height As Double
End Type

Sub Main()
    Dim r As Rectangle
    r.Width = 6
    r.Height = 4
    Describe r
    DoubleSize r
    Describe r
End Sub

Sub Describe(rc As Rectangle)
    Debug.Print rc.Width & " x " & rc.Height & ", المساحة = " & Area(rc)
End Sub

Function Area(rc As Rectangle) As Double
    Area = rc.Width * rc.Height
End Function

Sub DoubleSize(rc As Rectangle)
    rc.Width = rc.Width * 2
    rc.Height = rc.Height * 2
End Sub
```

```text output
6 x 4, المساحة = 24
12 x 8, المساحة = 96
```

## نسخ البطاقة

إسناد متغير من نوع معرّف إلى آخر **ينسخ** كل الحقول. بعدها كل نسخة مستقلة:

```vb run
Private Type Point
    X As Integer
    Y As Integer
End Type

Sub Main()
    Dim a As Point, b As Point
    a.X = 1: a.Y = 2
    b = a          ' نسخ
    b.X = 50
    Debug.Print "a = (" & a.X & ", " & a.Y & ")"
    Debug.Print "b = (" & b.X & ", " & b.Y & ")"
End Sub
```

```text output
a = (1, 2)
b = (50, 2)
```

## أخطاء شائعة

- **تعريف `Type` داخل إجراء:** يجب أن يكون في أعلى الوحدة.
- **`Public Type` في كود نموذج:** في النماذج والأصناف اكتب `Private Type`، أو ضع النوع في وحدة `.bas` بـ `Public Type`.
- **نسيان اسم المتغير قبل الحقل:** `Name = "Ali"` بدل `s.Name = "Ali"`.
- **محاولة طباعة النوع كله:** `Debug.Print s` لا يعمل؛ اطبع كل حقل على حدة.
- **الخلط بين اسم النوع واسم المتغير:** `Student.Name` خطأ؛ النوع `Student` قالب، والمتغير `s` هو البطاقة.

## تمارين

### تمرين 1: بطاقة كتاب

عرّف نوعًا `Book` فيه `Title` و`Author` و`Pages`، واملأ متغيرًا بالقيم: "Kalila wa Dimna"، "Ibn al-Muqaffa"، 320، ثم اطبعه بالصيغة: `Kalila wa Dimna by Ibn al-Muqaffa (320 pages)`.

```vb exercise
Private Type Book
    ' الحقول هنا
End Type

Sub Main()
End Sub
```

```vb solution
Private Type Book
    Title As String
    Author As String
    Pages As Integer
End Type

Sub Main()
    Dim b As Book
    With b
        .Title = "Kalila wa Dimna"
        .Author = "Ibn al-Muqaffa"
        .Pages = 320
    End With
    Debug.Print b.Title & " by " & b.Author & " (" & b.Pages & " pages)"
End Sub
```

```text output
Kalila wa Dimna by Ibn al-Muqaffa (320 pages)
```

### تمرين 2: فاتورة

عرّف `Item` (`Title` و`Price` و`Qty`)، وأنشئ مصفوفة من 3 أصناف: Pen 5×10، Notebook 20×3، Bag 150×1، ثم اطبع إجمالي الفاتورة.

```vb exercise
Private Type Item
    Title As String
    Price As Double
    Qty As Integer
End Type

Sub Main()
    Dim items(1 To 3) As Item
End Sub
```

```vb solution
Private Type Item
    Title As String
    Price As Double
    Qty As Integer
End Type

Sub Main()
    Dim items(1 To 3) As Item, i As Integer, total As Double
    items(1).Title = "Pen": items(1).Price = 5: items(1).Qty = 10
    items(2).Title = "Notebook": items(2).Price = 20: items(2).Qty = 3
    items(3).Title = "Bag": items(3).Price = 150: items(3).Qty = 1
    For i = 1 To 3
        total = total + items(i).Price * items(i).Qty
    Next i
    Debug.Print "الإجمالي = " & total
End Sub
```

```text output
الإجمالي = 260
```

## اختبر نفسك

```quiz
{"question": "أين يُكتب تعريف Type؟", "choices": ["داخل Sub Main", "في أعلى الوحدة خارج الإجراءات", "داخل حلقة", "في نافذة الخصائص"], "answer": 1, "explanation": "تعريف النوع يكون على مستوى الوحدة، خارج أي إجراء."}
```

```quiz
{"question": "كيف تصل إلى الحقل Age في المتغير p؟", "choices": ["p(Age)", "p.Age", "Age.p", "p!Age"], "answer": 1, "explanation": "نستخدم النقطة: p.Age."}
```

```quiz
{"question": "ماذا يحدث عند كتابة  b = a  حيث a و b من النوع نفسه؟", "choices": ["يصبحان متغيرًا واحدًا", "تُنسخ كل حقول a إلى b", "خطأ", "تُنسخ الحقول النصية فقط"], "answer": 1, "explanation": "الإسناد ينسخ كل الحقول، وتبقى النسختان مستقلتين."}
```

```quiz
{"question": "ما فائدة With ... End With؟", "choices": ["تكرار الكود", "تجنّب تكرار كتابة اسم المتغير قبل كل حقل", "إنشاء نوع جديد", "حذف الحقول"], "answer": 1, "explanation": "داخل With نكتب .Field بدل اسم_المتغير.Field."}
```

## الخلاصة

- `Type ... End Type` يصنع نوعًا جديدًا يجمع حقولًا مترابطة.
- نصل للحقول بالنقطة، و`With` تختصر الكتابة.
- مصفوفات الأنواع المعرّفة مناسبة جدًّا لقوائم السجلات (طلاب، منتجات، جهات اتصال).
