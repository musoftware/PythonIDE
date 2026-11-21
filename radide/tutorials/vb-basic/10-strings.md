# الدرس 10: التعامل مع النصوص

**في هذا الدرس ستتعلم:**

- طول النص `Len`، وقصّ أجزاء منه بـ `Left` و`Right` و`Mid`.
- البحث داخل النص بـ `InStr`، والاستبدال بـ `Replace`.
- تحويل الحروف بـ `UCase` و`LCase`، وحذف المسافات بـ `Trim`.
- تنسيق الأعداد والتواريخ بـ `Format`.

## النص قطار من الحروف

تخيّل النص قطارًا، وكل حرف عربة مرقّمة: العربة الأولى رقمها 1. الكلمة `"Hello"` قطار من خمس عربات: H=1، e=2، l=3، l=4، o=5.
(لاحظ: في النصوص الترقيم يبدأ من **1**، وليس من 0 كالمصفوفات.)

## الطول والقص

| الدالة | الوظيفة | مثال | الناتج |
|---|---|---|---|
| `Len(s)` | عدد الحروف | `Len("Hello")` | 5 |
| `Left(s, n)` | أول n حرف | `Left("Hello", 2)` | `He` |
| `Right(s, n)` | آخر n حرف | `Right("Hello", 3)` | `llo` |
| `Mid(s, start, n)` | n حرف بداية من الموضع start | `Mid("Hello", 2, 3)` | `ell` |

```vb run
Sub Main()
    Dim s As String
    s = "Visual Basic"
    Debug.Print "الطول: " & Len(s)
    Debug.Print "أول 6 حروف: " & Left(s, 6)
    Debug.Print "آخر 5 حروف: " & Right(s, 5)
    Debug.Print "من الحرف 8 (3 حروف): " & Mid(s, 8, 3)
    Debug.Print "من الحرف 8 للنهاية: " & Mid(s, 8)
End Sub
```

```text output
الطول: 12
أول 6 حروف: Visual
آخر 5 حروف: Basic
من الحرف 8 (3 حروف): Bas
من الحرف 8 للنهاية: Basic
```

إذا حذفت العدد الأخير من `Mid` تأخذ كل الحروف حتى النهاية.

### المرور على النص حرفًا حرفًا

```vb run
Sub Main()
    Dim word As String, i As Integer, reversed As String
    word = "BASIC"
    For i = 1 To Len(word)
        Debug.Print i & ": " & Mid(word, i, 1)
    Next i
    For i = Len(word) To 1 Step -1
        reversed = reversed & Mid(word, i, 1)
    Next i
    Debug.Print "معكوسة: " & reversed
End Sub
```

```text output
1: B
2: A
3: S
4: I
5: C
معكوسة: CISAB
```

(توجد دالة جاهزة تفعل ذلك: `StrReverse("BASIC")`.)

## البحث: `InStr`

`InStr(s, part)` تبحث عن `part` داخل `s` وتُرجع **موضع** أول ظهور، أو **0** إذا لم تجده. مثل البحث عن كلمة في كتاب: تخبرك برقم الصفحة، أو "غير موجودة".

```vb run
Sub Main()
    Dim email As String, atPos As Integer
    email = "sara@example.com"
    atPos = InStr(email, "@")
    Debug.Print "موضع @ هو " & atPos
    Debug.Print "اسم المستخدم: " & Left(email, atPos - 1)
    Debug.Print "النطاق: " & Mid(email, atPos + 1)
    If InStr(email, " ") = 0 Then Debug.Print "لا توجد مسافات في البريد"
End Sub
```

```text output
موضع @ هو 5
اسم المستخدم: sara
النطاق: example.com
لا توجد مسافات في البريد
```

## الاستبدال والتحويل

```vb run
Sub Main()
    Dim s As String
    s = "  I love Java  "
    Debug.Print "[" & Trim(s) & "]"
    Debug.Print Replace(Trim(s), "Java", "BASIC")
    Debug.Print UCase("basic")
    Debug.Print LCase("BASIC")
    Debug.Print "[" & LTrim(s) & "]"
End Sub
```

```text output
[I love Java]
I love BASIC
BASIC
basic
[I love Java  ]
```

| الدالة | الوظيفة |
|---|---|
| `Trim(s)` | تحذف المسافات من البداية والنهاية (`LTrim` من اليسار فقط، و`RTrim` من اليمين فقط) |
| `Replace(s, old, new)` | تستبدل كل `old` بـ `new` |
| `UCase(s)` / `LCase(s)` | حروف إنجليزية كبيرة / صغيرة |
| `StrReverse(s)` | تعكس النص |
| `Space(n)` / `String(n, c)` | n مسافة / تكرار حرف n مرة |
| `Asc(c)` / `Chr(n)` | رمز الحرف / الحرف من رمزه |

## التنسيق: Format

`Format(قيمة, "نمط")` تحوّل العدد أو التاريخ إلى نص مرتّب، مثل قالب الحلوى: تصب فيه القيمة فتخرج بالشكل المطلوب.

```vb run
Sub Main()
    Debug.Print Format(1234567.891, "#,##0.00")
    Debug.Print Format(3.5, "0.00")
    Debug.Print Format(7, "000")
    Debug.Print Format(0.875, "0.0%")
    Debug.Print Format(#3/7/2024#, "yyyy-mm-dd")
    Debug.Print Format(#3/7/2024#, "dd/mm/yyyy")
End Sub
```

```text output
1,234,567.89
3.50
007
87.5%
2024-03-07
07/03/2024
```

| الرمز | المعنى |
|---|---|
| `0` | رقم إجباري (يضع صفرًا إذا لم يوجد) |
| `#` | رقم اختياري |
| `,` | فاصل الآلاف |
| `.` | الفاصلة العشرية |
| `%` | يضرب في 100 ويضيف علامة النسبة |
| `yyyy` `mm` `dd` | السنة والشهر واليوم |
| `hh` `nn` `ss` | الساعة والدقيقة والثانية |

## أخطاء شائعة

- **نسيان أن ترقيم النص يبدأ من 1:** `Mid(s, 0, 1)` خطأ.
- **طلب حروف أكثر من الموجود:** `Left("abc", 10)` لا تعطي خطأ بل تُرجع `"abc"` فقط. لا مشكلة، لكن انتبه للنتيجة.
- **اعتبار `InStr` تُرجع True/False:** هي تُرجع **رقمًا**. اكتب `If InStr(s, "x") > 0 Then`.
- **حالة الحروف:** `InStr("Hello", "h")` تُرجع 0. لتجاهل حالة الحروف حوّل الطرفين بـ `LCase` أولًا.
- **`Mid(s, i)` بدلًا من `Mid(s, i, 1)`** عند المرور حرفًا حرفًا: الأولى تأخذ باقي النص كله.

## تمارين

### تمرين 1: الاسم الأول

من النص `"Mohamed Salah"` استخرج الاسم الأول (قبل المسافة) والاسم الأخير (بعدها) باستخدام `InStr` و`Left` و`Mid`.

```vb exercise
Sub Main()
    Dim fullName As String
    fullName = "Mohamed Salah"
End Sub
```

```vb solution
Sub Main()
    Dim fullName As String, p As Integer
    fullName = "Mohamed Salah"
    p = InStr(fullName, " ")
    Debug.Print "الأول: " & Left(fullName, p - 1)
    Debug.Print "الأخير: " & Mid(fullName, p + 1)
End Sub
```

```text output
الأول: Mohamed
الأخير: Salah
```

### تمرين 2: عدّ الحرف

احسب كم مرة يظهر الحرف `a` في النص `"banana bread"`.

```vb exercise
Sub Main()
    Dim s As String, i As Integer, count As Integer
    s = "banana bread"
End Sub
```

```vb solution
Sub Main()
    Dim s As String, i As Integer, count As Integer
    s = "banana bread"
    For i = 1 To Len(s)
        If Mid(s, i, 1) = "a" Then count = count + 1
    Next i
    Debug.Print "عدد مرات a = " & count
End Sub
```

```text output
عدد مرات a = 4
```

### تمرين 3: كلمة متناظرة (Palindrome)

الكلمة المتناظرة تُقرأ من الجهتين بالشكل نفسه مثل `level`. اطبع هل `"Racecar"` متناظرة (بدون اعتبار حالة الحروف).

```vb exercise
Sub Main()
    Dim w As String
    w = "Racecar"
End Sub
```

```vb solution
Sub Main()
    Dim w As String
    w = LCase("Racecar")
    If w = StrReverse(w) Then
        Debug.Print "متناظرة"
    Else
        Debug.Print "غير متناظرة"
    End If
End Sub
```

```text output
متناظرة
```

## اختبر نفسك

```quiz
{"question": "ما ناتج  Mid(\"Programming\", 4, 4) ؟", "choices": ["gram", "Prog", "ramm", "ming"], "answer": 0, "explanation": "من الحرف الرابع (g) خذ 4 حروف: gram."}
```

```quiz
{"question": "ماذا تُرجع InStr إذا لم تجد النص؟", "choices": ["-1", "0", "False", "خطأ"], "answer": 1, "explanation": "تُرجع 0 عندما لا تجد ما تبحث عنه."}
```

```quiz
{"question": "ما ناتج  Format(5, \"000\") ؟", "choices": ["5", "500", "005", "5.00"], "answer": 2, "explanation": "الرمز 0 رقم إجباري، فتُكمل الخانات الناقصة بأصفار."}
```

```quiz
{"question": "أي دالة تحذف المسافات من بداية النص ونهايته؟", "choices": ["Trim", "Len", "Replace", "Space"], "answer": 0, "explanation": "Trim تحذف المسافات من الطرفين."}
```

## الخلاصة

- `Len` و`Left` و`Right` و`Mid` للطول والقص (الترقيم من 1).
- `InStr` للبحث (0 = غير موجود)، و`Replace` للاستبدال.
- `Trim` و`UCase` و`LCase` للتنظيف والتحويل، و`Format` للتنسيق.
