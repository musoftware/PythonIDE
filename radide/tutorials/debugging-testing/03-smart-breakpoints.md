# الدرس 3: نقاط توقف ذكية: الشرط وعدد المرات ونقاط التسجيل

**في هذا الدرس ستتعلم:**

- **نقطة التوقف الشرطية**: توقف فقط عندما يكون شرط ما صحيحًا (`Alt+F9`).
- **عدد مرات الوصول** (Hit count): توقف في المرة العاشرة، أو كل خمس مرات.
- **نقطة التسجيل** (Logpoint): اكتب رسالة في نافذة المخرجات **دون أن تتوقف**.
- **التوقف عند الاستثناءات** (Break on Exceptions).

## الحارس الذكي

نقطة التوقف العادية حارس يوقف **كل** سيارة تمر. في حلقة تدور ألف مرة، ستضغط `F5` ألف مرة!
**نقطة التوقف الذكية** حارس لديه تعليمات: "أوقف السيارة الحمراء فقط"، أو "أوقف العاشرة"، أو "لا توقف أحدًا، فقط سجّل أرقام اللوحات".

## نقطة توقف شرطية

1. ضع المؤشر على السطر.
2. **Debug > Breakpoint Condition...** (تصحيح الأخطاء > شرط نقطة التوقف...) أو `Alt+F9`.
3. اكتب الشرط بلغة برنامجك، مثل `i = 437` أو `total > 1000` أو `name = "Omar"`.
4. اضغط **OK**. نقطة التوقف تظهر في الهامش، والبرنامج يتوقف عندها **فقط** إذا كان الشرط صحيحًا.

## نافذة إعدادات نقطة التوقف

لكل الخيارات معًا: **Debug > Breakpoint Settings (Condition, Hit Count, Log)...** (إعدادات نقطة التوقف (الشرط، عدد المرات، السجل)...). عنوان النافذة **Breakpoint Settings - line N**:

| الخانة | الاسم العربي | المعنى |
|---|---|---|
| **Condition (stop only when true):** | الشرط (التوقف فقط عندما يكون صحيحًا) | مثل `x > 3`. فارغ = دائمًا |
| **Hit count:** | عدد مرات الوصول | متى يتوقف حسب عدد مرات الوصول إلى السطر |
| **Log a message to the Output window and continue (do not stop)** | تسجيل رسالة في نافذة المخرجات والمتابعة (بدون توقف) | يحوّل النقطة إلى **نقطة تسجيل** |

خيارات **Hit count**:

| الخيار | معناه | مثال |
|---|---|---|
| **Always stop** | توقف كل مرة (الافتراضي) | |
| **When the hit count is equal to** | توقف في المرة رقم N فقط | المرة 10 |
| **When the hit count is a multiple of** | توقف كل N مرة | كل 100 دورة |
| **When the hit count is greater than or equal to** | توقف من المرة N فصاعدًا | بعد أول 50 |

يمكن الجمع بين الشرط وعدد المرات: "توقف عندما يكون `price = 0` للمرة الثالثة".

## نقطة التسجيل (Logpoint)

بدل أن تملأ الكود بأسطر `Debug.Print` للتجربة ثم تنسى حذفها، استخدم نقطة تسجيل:

1. افتح **Breakpoint Settings** على السطر.
2. فعّل **Log a message to the Output window and continue (do not stop)**.
3. اكتب الرسالة، والتعبيرات بين `{ }` تُستبدل بقيمها: `i = {i}, total = {total}`.
4. شغّل بـ `F5`: الرسائل تظهر في نافذة **Output**، والبرنامج **لا يتوقف**، والكود لم يتغير حرفًا.

> 💡 هذه الإعدادات تعمل في مصحح BASIC المدمج، وفي مصححات اللغات الأخرى في البيئة (Python و Lua و Perl و Go و Java ...).

## التوقف عند الاستثناءات

**Debug > Break on Exceptions** (التوقف عند الاستثناءات): عند تفعيله يتوقف المصحح **عند السطر الذي حدث فيه الخطأ** فورًا، فترى المتغيرات في تلك اللحظة، بدل أن ينتهي البرنامج برسالة خطأ.

## جرّب: إبرة في كومة قش

هذا البرنامج يجمع أسعار 1000 فاتورة. إحداها سعرها صفر بالخطأ. البحث بنقطة توقف عادية مستحيل تقريبًا.
ضع نقطة توقف على سطر `If price = 0 Then`، واضغط `Alt+F9` واكتب الشرط `price = 0`، ثم `F5`: يقف المصحح مباشرة عند الفاتورة المعطوبة، وترى `i` في Locals.

```vb run
Function PriceOf(n As Integer) As Long
    If n = 437 Then
        PriceOf = 0
    Else
        PriceOf = 10 + (n Mod 7)
    End If
End Function

Sub Main()
    Dim i As Integer
    Dim price As Long
    Dim total As Long
    Dim bad As Integer
    For i = 1 To 1000
        price = PriceOf(i)
        If price = 0 Then
            bad = i
        End If
        total = total + price
    Next i
    Debug.Print "الإجمالي = " & total
    Debug.Print "الفاتورة المعطوبة رقم " & bad
End Sub
```

```text output
الإجمالي = 12990
الفاتورة المعطوبة رقم 437
```

ثم جرّب نقطة تسجيل على السطر `total = total + price` برسالة `i={i} total={total}` وعدد مرات **multiple of** 100: ترى عشرة أسطر في Output فقط.

## أخطاء شائعة

- **شرط بصيغة لغة أخرى:** في BASIC المساواة `=` وفي Python `==`. اكتب الشرط بلغة البرنامج.
- **ظن أن نقطة التسجيل توقف البرنامج:** هي لا توقفه أبدًا، فقط تكتب في Output.
- **نسيان الأقواس المعقوفة:** `total = total` تُطبع حرفيًا؛ الصحيح `total = {total}`.
- **ترك Break on Exceptions مفعّلًا في برنامج يعالج أخطاءه بنفسه:** قد يتوقف كثيرًا. أطفئه عند الحاجة.

## تمرين

### تمرين 1: أول فاتورة كبيرة

عدّل البرنامج ليطبع رقم **أول** فاتورة سعرها 16 بالضبط، ثم يخرج من الحلقة بـ `Exit For`. (هذا ما كنت ستجده بنقطة توقف شرطها `price = 16` بلا تعديل الكود.)

```vb exercise
Function PriceOf(n As Integer) As Long
    If n = 437 Then
        PriceOf = 0
    Else
        PriceOf = 10 + (n Mod 7)
    End If
End Function

Sub Main()
    Dim i As Integer
    Dim price As Long
    For i = 1 To 1000
        price = PriceOf(i)
        ' أكمل
    Next i
End Sub
```

```vb solution
Function PriceOf(n As Integer) As Long
    If n = 437 Then
        PriceOf = 0
    Else
        PriceOf = 10 + (n Mod 7)
    End If
End Function

Sub Main()
    Dim i As Integer
    Dim price As Long
    For i = 1 To 1000
        price = PriceOf(i)
        If price = 16 Then
            Debug.Print "أول فاتورة بسعر 16 رقمها " & i
            Exit For
        End If
    Next i
End Sub
```

```text output
أول فاتورة بسعر 16 رقمها 6
```

## اختبر نفسك

```quiz
{"question": "تريد أن يتوقف البرنامج في الدورة رقم 250 فقط من حلقة. ماذا تستخدم؟", "choices": ["F9 ثم الضغط على F5 مئتين وتسعة وأربعين مرة", "Hit count: When the hit count is equal to 250", "Ctrl+F5", "Break All"], "answer": 1, "explanation": "عدد مرات الوصول يوقف البرنامج في المرة المطلوبة مباشرة."}
```

```quiz
{"question": "ما الذي يميز نقطة التسجيل (Logpoint)؟", "choices": ["توقف البرنامج مرتين", "تكتب رسالة في Output ولا توقف البرنامج", "تحذف السطر", "تعمل فقط مع Ctrl+F5"], "answer": 1, "explanation": "نقطة التسجيل بديل نظيف عن Debug.Print المؤقت."}
```

```quiz
{"question": "كيف تكتب قيمة المتغير `total` داخل رسالة نقطة التسجيل؟", "choices": ["`total`", "`{total}`", "`[total]`", "`$total`"], "answer": 1, "explanation": "التعبيرات داخل { } تُستبدل بقيمها."}
```

## الخلاصة

- `Alt+F9` شرط سريع، و **Breakpoint Settings...** للشرط وعدد المرات والتسجيل معًا.
- Hit count: يساوي، أو مضاعف، أو أكبر من أو يساوي.
- نقطة التسجيل: رسالة بـ `{تعبير}` في Output بلا توقف وبلا تعديل الكود.
- **Break on Exceptions** يوقفك عند سطر الخطأ نفسه.
