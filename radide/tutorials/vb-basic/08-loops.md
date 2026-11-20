# الدرس 8: حلقات التكرار

**في هذا الدرس ستتعلم:**

- التكرار بعدد معروف من المرات: `For ... Next` و`Step`.
- التكرار حتى يتحقق شرط: `Do While` و`Do Until` و`Do ... Loop While`.
- الحلقة القديمة `While ... Wend`.
- الخروج المبكر بـ `Exit For` و`Exit Do`، والحلقات المتداخلة.

## لماذا التكرار؟

لو طلب منك المعلم أن تكتب "لن أتكلم في الفصل" مئة مرة، ستتعب كثيرًا. أما الحاسوب فلا يتعب!
بدلًا من كتابة 100 سطر، نكتب الأمر مرة واحدة ونقول: **كرّره** 100 مرة. هذه هي **حلقة التكرار** (Loop).

## حلقة For ... Next

نستخدمها عندما نعرف **عدد المرات** مسبقًا. تشبه عدّاد خطوات: يبدأ من رقم، ويزيد واحدًا كل مرة، ويتوقف عند رقم النهاية.

```vb run
Sub Main()
    Dim i As Integer
    For i = 1 To 5
        Debug.Print "الدورة رقم " & i
    Next i
End Sub
```

```text output
الدورة رقم 1
الدورة رقم 2
الدورة رقم 3
الدورة رقم 4
الدورة رقم 5
```

- `i` يُسمّى **عدّاد الحلقة**.
- في البداية `i = 1`، وبعد كل دورة يزيد 1، وعندما يتجاوز 5 تنتهي الحلقة.
- كتابة `i` بعد `Next` اختيارية، لكنها توضّح أي حلقة نغلق.

### مثال: مجموع الأعداد من 1 إلى 100

```vb run
Sub Main()
    Dim i As Integer, total As Long
    total = 0
    For i = 1 To 100
        total = total + i
    Next i
    Debug.Print "المجموع = " & total
End Sub
```

```text output
المجموع = 5050
```

المتغير `total` هنا يُسمّى **مُراكِم** (Accumulator): مثل حصّالة نضيف إليها في كل دورة.

### الخطوة Step

`Step` تحدد مقدار الزيادة. ويمكن أن تكون سالبة للعدّ التنازلي. وفي هذا المثال نكتب `;` في آخر `Debug.Print` لنبقى على السطر نفسه:

```vb run
Sub Main()
    Dim i As Integer
    For i = 0 To 20 Step 5
        Debug.Print i & " ";
    Next i
    Debug.Print
    For i = 10 To 1 Step -1
        Debug.Print i & " ";
    Next i
    Debug.Print
    Debug.Print "انطلق!"
End Sub
```

```text output
0 5 10 15 20
10 9 8 7 6 5 4 3 2 1
انطلق!
```

## حلقة Do While ... Loop

نستخدمها عندما **لا نعرف** عدد المرات، بل نعرف **الشرط**: "استمر **طالما** ...". مثل: كُل **طالما** أنت جائع.

```vb run
Sub Main()
    Dim savings As Long, months As Integer
    savings = 0
    months = 0
    Do While savings < 1000
        savings = savings + 150
        months = months + 1
    Loop
    Debug.Print "تحتاج " & months & " شهور لتوفير " & savings & " جنيه"
End Sub
```

```text output
تحتاج 7 شهور لتوفير 1050 جنيه
```

### Do Until: "حتى"

`Do Until الشرط` تعني "كرّر **حتى** يصبح الشرط صحيحًا"، وهي عكس `While`:

```vb run
Sub Main()
    Dim n As Long
    n = 1
    Do Until n > 1000
        n = n * 2
    Loop
    Debug.Print "أول قوة للعدد 2 أكبر من 1000 هي " & n
End Sub
```

```text output
أول قوة للعدد 2 أكبر من 1000 هي 1024
```

### الشرط في النهاية: Do ... Loop While

إذا وضعنا الشرط بعد `Loop` تُنفَّذ الحلقة **مرة واحدة على الأقل** قبل فحص الشرط. مناسب جدًّا لسؤال المستخدم حتى يُدخل قيمة صحيحة:

<!-- test: {"inputs": ["150", "-3", "25"]} -->
```vb run
Sub Main()
    Dim age As Integer
    Do
        age = Val(InputBox("أدخل عمرك (من 1 إلى 120):"))
    Loop While age < 1 Or age > 120
    Debug.Print "شكرًا، عمرك " & age
End Sub
```

```text output
شكرًا، عمرك 25
```

(في هذا المثال افترضنا أن المستخدم أدخل 150 ثم -3 ثم 25، فرفض البرنامج أول إجابتين.)

## While ... Wend

صيغة قديمة تعمل مثل `Do While ... Loop` تمامًا. ستراها في البرامج القديمة:

```vb run
Sub Main()
    Dim k As Integer
    k = 3
    While k > 0
        Debug.Print "k = " & k
        k = k - 1
    Wend
End Sub
```

```text output
k = 3
k = 2
k = 1
```

## الخروج المبكر: Exit For و Exit Do

أحيانًا نجد ما نبحث عنه قبل نهاية الحلقة، فلا داعي للإكمال:

```vb run
Sub Main()
    Dim i As Integer
    For i = 2 To 100
        If i Mod 7 = 0 And i Mod 5 = 0 Then
            Debug.Print "أول عدد يقبل القسمة على 5 و 7: " & i
            Exit For
        End If
    Next i
End Sub
```

```text output
أول عدد يقبل القسمة على 5 و 7: 35
```

## الحلقات المتداخلة

حلقة داخل حلقة، مثل عقارب الساعة: عقرب الدقائق يدور دورة كاملة مقابل كل خطوة لعقرب الساعات.

```vb run
Sub Main()
    Dim row As Integer, col As Integer, line As String
    For row = 1 To 3
        line = ""
        For col = 1 To 4
            line = line & (row * col) & vbTab
        Next col
        Debug.Print line
    Next row
End Sub
```

```text output
1	2	3	4
2	4	6	8
3	6	9	12
```

(`vbTab` يضيف مسافة جدولة لترتيب الأعمدة.)

## أخطاء شائعة

- **الحلقة اللانهائية:** إذا نسيت تغيير المتغير داخل `Do While` لن يصبح الشرط خطأ أبدًا، فيدور البرنامج للأبد. اضغط **Shift+F5** لإيقافه.

  ```vb
  Do While x < 10
      Debug.Print x      ' نسينا x = x + 1
  Loop
  ```

- **تعديل عدّاد `For` داخل الحلقة:** يربك العد. اترك العدّاد للحلقة.
- **نسيان `Next` أو `Loop`** في نهاية الحلقة.
- **`Step` موجبة مع عدّ تنازلي:** `For i = 10 To 1` بدون `Step -1` لا تدور أبدًا.
- **نسيان تصفير المُراكِم** قبل الحلقة عند تكرار الحساب.

## تمارين

### تمرين 1: جدول الضرب

اطبع جدول ضرب العدد 7 من 1 إلى 10 بالصيغة `7 x 1 = 7`.

```vb exercise
Sub Main()
    Dim i As Integer
End Sub
```

```vb solution
Sub Main()
    Dim i As Integer
    For i = 1 To 10
        Debug.Print "7 x " & i & " = " & (7 * i)
    Next i
End Sub
```

```text output
7 x 1 = 7
7 x 2 = 14
7 x 3 = 21
7 x 4 = 28
7 x 5 = 35
7 x 6 = 42
7 x 7 = 49
7 x 8 = 56
7 x 9 = 63
7 x 10 = 70
```

### تمرين 2: المضروب (العاملي)

احسب مضروب العدد 6، أي 1 × 2 × 3 × 4 × 5 × 6.
تلميح: المُراكِم في الضرب يبدأ بـ 1 وليس بـ 0!

```vb exercise
Sub Main()
    Dim i As Integer, f As Long
End Sub
```

```vb solution
Sub Main()
    Dim i As Integer, f As Long
    f = 1
    For i = 1 To 6
        f = f * i
    Next i
    Debug.Print "6! = " & f
End Sub
```

```text output
6! = 720
```

### تمرين 3: مثلث النجوم

اطبع مثلثًا من النجوم من 4 أسطر (السطر الأول نجمة، والرابع أربع نجوم). استخدم حلقتين متداخلتين.

```vb exercise
Sub Main()
    Dim r As Integer, c As Integer, line As String
End Sub
```

```vb solution
Sub Main()
    Dim r As Integer, c As Integer, line As String
    For r = 1 To 4
        line = ""
        For c = 1 To r
            line = line & "*"
        Next c
        Debug.Print line
    Next r
End Sub
```

```text output
*
**
***
****
```

## اختبر نفسك

```quiz
{"question": "كم مرة تدور الحلقة  For i = 1 To 10 Step 2 ؟", "choices": ["10", "5", "2", "9"], "answer": 1, "explanation": "قيم i هي 1، 3، 5، 7، 9: خمس مرات."}
```

```quiz
{"question": "أي حلقة تُنفَّذ مرة واحدة على الأقل دائمًا؟", "choices": ["Do While ... Loop", "Do ... Loop While", "For ... Next", "While ... Wend"], "answer": 1, "explanation": "عندما يكون الشرط بعد Loop يُفحص بعد تنفيذ الدورة الأولى."}
```

```quiz
{"question": "ما الذي يسبب حلقة لانهائية غالبًا؟", "choices": ["استخدام Step", "عدم تغيير المتغير الذي يعتمد عليه الشرط", "كتابة Next i", "استخدام Exit For"], "answer": 1, "explanation": "إذا لم يتغير المتغير لن يتغير الشرط، فتستمر الحلقة للأبد."}
```

```quiz
{"question": "ما الأمر الذي يخرج من حلقة For فورًا؟", "choices": ["Stop", "End For", "Exit For", "Break"], "answer": 2, "explanation": "Exit For يخرج من حلقة For، وExit Do يخرج من حلقة Do."}
```

## الخلاصة

- `For ... Next` لعدد معروف من المرات، و`Step` للتحكم في الزيادة.
- `Do While` (طالما) و`Do Until` (حتى) عندما يتحكم شرط في التكرار.
- `Exit For` و`Exit Do` للخروج المبكر، واحذر الحلقة اللانهائية.
