# الدرس 2: المتغيرات المحلية والمراقبة ومكدس الاستدعاءات

**في هذا الدرس ستتعلم:**

- نافذة **Locals** (المتغيرات المحلية): كل متغيرات الدالة الحالية وقيمها، وتوسيع المصفوفات والكائنات.
- نافذة **Watch** (المراقبة): تعبيرات تختارها أنت وتراقبها في كل خطوة.
- نافذة **Call Stack** (مكدس الاستدعاءات): من استدعى من؟
- نافذة **Immediate** (الأوامر الفورية): اسأل البرنامج المتوقف سؤالًا واحصل على الجواب فورًا.

## لوحة عدادات السيارة

عندما يتوقف البرنامج عند نقطة توقف، فهو مثل سيارة متوقفة في محطة: تستطيع أن تنظر إلى **لوحة العدادات** كلها:
السرعة، والوقود، والحرارة. نوافذ المصحح هي لوحة العدادات هذه.

| النافذة | القائمة | الاسم العربي | ماذا تعرض؟ |
|---|---|---|---|
| **Locals** | **Debug > Windows > Locals** | المتغيرات المحلية | متغيرات الدالة الحالية تلقائيًا |
| **Watch** | **Debug > Windows > Watch** | المراقبة | التعبيرات التي تكتبها أنت |
| **Call Stack** | **Debug > Windows > Call Stack** | مكدس الاستدعاءات | سلسلة الدوال من البداية حتى هنا |
| **Immediate** | **Debug > Windows > Immediate** | الأوامر الفورية | سطر تكتب فيه تعبيرًا فيُحسب |
| **Threads** | **Debug > Windows > Threads** (`Ctrl+Alt+H`) | الخيوط | خيوط البرنامج (للبرامج متعددة الخيوط) |

وفي تخطيط VS Code تجدها كلها معًا في عرض **Run and Debug** في شريط النشاط.

## Locals: كل شيء أمامك

- تتحدث **تلقائيًا** مع كل خطوة (`F10` و `F11`).
- المصفوفات، والقوائم، والكائنات، و `Type` في BASIC، و `Collection` تظهر **شجرة**: انقر السهم لتوسيعها ورؤية عناصرها.

## Watch: راقب ما يهمك

أحيانًا تهمك قيمة محسوبة، مثل `total / count` أو `UBound(scores)`، لا متغير بعينه.

1. افتح **Debug > Windows > Watch**.
2. في الخانة السفلية **Add a watch expression and press Enter** (أضف تعبير مراقبة واضغط Enter) اكتب التعبير، مثل `total > 100`، ثم `Enter`.
3. التعبير يُحسب من جديد في كل توقف.
4. **Remove** يحذف التعبير المحدد.

## Call Stack: من استدعى من؟

إذا كانت `Main` تستدعي `ProcessOrder`، و `ProcessOrder` تستدعي `CalcTax`، وتوقفت داخل `CalcTax`، فمكدس الاستدعاءات يعرض:

```text
CalcTax        <- أنت هنا
ProcessOrder
Main
```

مثل **كومة أطباق**: آخر دالة استُدعيت فوق، وعندما تنتهي تُرفع ونرجع للتي تحتها.
**انقر أي سطر مرتين** لتذهب إلى مكانه في الكود وترى متغيرات تلك الدالة في Locals.

## Immediate: اسأل سؤالًا

والبرنامج متوقف، اكتب في نافذة **Immediate** تعبيرًا واضغط `Enter`:

```text
> total * 2
30
> UCase(name)
SARA
```

مفيد لتجربة فكرة ("ماذا لو قسمت على 3؟") دون تعديل الكود. إذا لم يكن هناك برنامج متوقف تظهر الرسالة `(no program is running)`.

## جرّب: سلسلة استدعاءات

ضع نقطة توقف على السطر `CalcTax = amount * 14 \ 100` ثم اضغط `F5`:

- في **Call Stack**: `CalcTax` ثم `ProcessOrder` ثم `Main`.
- في **Locals**: `amount` داخل `CalcTax`. انقر `ProcessOrder` مرتين في Call Stack لترى `qty` و `price` و `subtotal`.
- في **Watch** أضف `amount > 500`.
- في **Immediate** اكتب `amount + 1` واضغط `Enter`.

```vb run
Function CalcTax(amount As Long) As Long
    CalcTax = amount * 14 \ 100
End Function

Function ProcessOrder(qty As Integer, price As Long) As Long
    Dim subtotal As Long
    subtotal = qty * price
    ProcessOrder = subtotal + CalcTax(subtotal)
End Function

Sub Main()
    Dim prices(2) As Long
    Dim i As Integer
    prices(0) = 100
    prices(1) = 250
    prices(2) = 1000
    For i = 0 To 2
        Debug.Print "طلب " & (i + 1) & ": " & ProcessOrder(2, prices(i))
    Next i
End Sub
```

```text output
طلب 1: 228
طلب 2: 570
طلب 3: 2280
```

وسّع `prices` في **Locals** وأنت داخل `Main` لترى عناصرها الثلاثة.

## أخطاء شائعة

- **Locals فارغة:** البرنامج ليس متوقفًا. ضع نقطة توقف واضغط `F5` (وليس `Ctrl+F5`).
- **متغير لا يظهر في Locals:** هو متغير دالة أخرى. انقر تلك الدالة في **Call Stack**.
- **تعبير Watch فيه خطأ:** يظهر بجانبه رسالة خطأ بدل القيمة. صححه أو احذفه بـ **Remove**.
- **تعديل الكود أثناء التوقف وانتظار أثره فورًا:** أوقف البرنامج (`Shift+F5`) وشغّله من جديد.

## تمرين

### تمرين 1: خصم بدل الضريبة

أضف دالة `Discount(amount)` تُرجع 10% من المبلغ (بقسمة صحيحة `\`)، واجعل `ProcessOrder` تطرح الخصم بدل إضافة الضريبة. ستكون النتائج 180 و 450 و 1800.
بعد أن تنجح، ضع نقطة توقف داخل `Discount` وانظر إلى Call Stack.

```vb exercise
Function CalcTax(amount As Long) As Long
    CalcTax = amount * 14 \ 100
End Function

Function ProcessOrder(qty As Integer, price As Long) As Long
    Dim subtotal As Long
    subtotal = qty * price
    ProcessOrder = subtotal + CalcTax(subtotal)
End Function

Sub Main()
    Dim prices(2) As Long
    Dim i As Integer
    prices(0) = 100
    prices(1) = 250
    prices(2) = 1000
    For i = 0 To 2
        Debug.Print "طلب " & (i + 1) & ": " & ProcessOrder(2, prices(i))
    Next i
End Sub
```

```vb solution
Function Discount(amount As Long) As Long
    Discount = amount * 10 \ 100
End Function

Function ProcessOrder(qty As Integer, price As Long) As Long
    Dim subtotal As Long
    subtotal = qty * price
    ProcessOrder = subtotal - Discount(subtotal)
End Function

Sub Main()
    Dim prices(2) As Long
    Dim i As Integer
    prices(0) = 100
    prices(1) = 250
    prices(2) = 1000
    For i = 0 To 2
        Debug.Print "طلب " & (i + 1) & ": " & ProcessOrder(2, prices(i))
    Next i
End Sub
```

```text output
طلب 1: 180
طلب 2: 450
طلب 3: 1800
```

## اختبر نفسك

```quiz
{"question": "تريد مراقبة التعبير `total / count` في كل خطوة. أي نافذة تستخدم؟", "choices": ["Locals", "Watch", "Output", "Properties"], "answer": 1, "explanation": "Watch للتعبيرات التي تختارها، و Locals للمتغيرات تلقائيًا."}
```

```quiz
{"question": "توقفت داخل `CalcTax`. كيف ترى متغيرات الدالة التي استدعتها؟", "choices": ["أعد تشغيل البرنامج", "انقر الدالة مرتين في Call Stack", "اضغط F9", "افتح Tools > Options"], "answer": 1, "explanation": "النقر المزدوج على إطار في مكدس الاستدعاءات ينقلك إليه ويعرض متغيراته."}
```

```quiz
{"question": "ماذا تفعل نافذة Immediate؟", "choices": ["تحفظ المشروع", "تحسب تعبيرًا تكتبه والبرنامج متوقف", "تعرض الأخطاء فقط", "تشغّل البرنامج من البداية"], "answer": 1, "explanation": "اكتب تعبيرًا واضغط Enter أثناء التوقف لترى قيمته."}
```

## الخلاصة

- **Locals**: متغيرات الدالة الحالية تلقائيًا، والمصفوفات والكائنات شجرة.
- **Watch**: تعبيراتك أنت، تُحسب في كل توقف.
- **Call Stack**: كومة الدوال، والنقر المزدوج ينقلك إلى أي إطار.
- **Immediate**: سؤال سريع والبرنامج متوقف. كلها في **Debug > Windows**.
