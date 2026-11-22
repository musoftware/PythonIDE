# الدرس 6: Anchor و Dock: نماذج تتغير مع حجم النافذة

**في هذا الدرس ستتعلم:**

- مشكلة النافذة التي يكبّرها المستخدم فتبقى أدواتها في زاوية.
- خاصية **`Anchor`** (الربط بالحواف): أداة تتحرك أو تتمدد مع الحافة.
- خاصية **`Dock`** (الالتصاق): أداة تملأ أعلى النافذة أو أسفلها أو جانبها أو ما تبقى منها.
- كيف تجرّب ذلك في المصمم نفسه، وما الحساب الذي يجري خلف الستار.

## المشكلة

صممت نافذة عرضها 400 نقطة، فيها مربع بحث وزر "بحث" على اليمين. المستخدم كبّر النافذة إلى ملء الشاشة. ماذا يحدث؟
بدون إعداد: المربع والزر يبقيان في مكانهما، وبجانبهما فراغ كبير قبيح.
المطلوب: المربع **يتمدد**، والزر **يلحق** بالحافة اليمنى.

## Anchor: حبال مربوطة بالحواف

تخيّل أن الأداة مربوطة بحبال مشدودة إلى حواف حاويتها. كل حبل يحافظ على **المسافة** بين الأداة وتلك الحافة.

| قيمة Anchor | ماذا يحدث عند تكبير النافذة عرضيًا؟ |
|---|---|
| `Top, Left` (الافتراضي) | لا شيء: الأداة ثابتة في مكانها من الأعلى واليسار |
| `Top, Right` | الأداة **تتحرك** مع الحافة اليمنى (مثل زر "بحث") |
| `Top, Left, Right` | الأداة **تتمدد** عرضيًا: حافتها اليسرى ثابتة واليمنى تلحق بالنافذة (مثل مربع البحث) |
| `Top, Bottom, Left, Right` | تتمدد في الاتجاهين (مثل مربع نص كبير أو جدول) |
| `Bottom, Right` | تلتصق بالزاوية السفلية اليمنى (مثل زرّي موافق وإلغاء) |
| بلا يسار ولا يمين | تبقى في **المنتصف** نسبيًا |

### تعديل Anchor في نافذة الخصائص

1. حدد الأداة.
2. في نافذة الخصائص انقر قيمة `Anchor` (مثل `Top, Left ▾`). تظهر نافذة صغيرة فيها مربع وأربعة أشرطة حوله.
3. انقر الأشرطة لتفعيلها أو إلغائها: الأعلى والأسفل واليسار واليمين.
4. القيمة تتغير مباشرة، مثل `Top, Left, Right`.

## Dock: الالتصاق بجانب

`Dock` يلصق الأداة بجانب كامل من حاويتها، ويمدّها على طوله:

| قيمة Dock | النتيجة | مثال |
|---|---|---|
| `None` | بلا التصاق (الافتراضي)، و Anchor هو الذي يعمل | |
| `Top` | شريط بعرض الحاوية في الأعلى | شريط أدوات أو لوحة عنوان |
| `Bottom` | شريط في الأسفل | شريط حالة |
| `Left` / `Right` | عمود على الجانب | قائمة تنقل جانبية |
| `Fill` | **ما تبقى** من المساحة كله | محرر النص في الوسط |

### ترتيب الالتصاق

إذا التصقت عدة أدوات، تأخذ الأداة **الأبعد إلى الخلف** شريطها أولًا، ثم التي بعدها من المساحة الباقية، وأداة `Fill` تأخذ آخر ما تبقى.
لتغيير الترتيب استخدم **Format > Order > Bring to Front** و **Send to Back** (تنسيق > إحضار إلى الأمام / إرسال إلى الخلف).

> 💡 **نمط شائع:** `Panel` بـ `Dock = Top` فيه أزرار، و `StatusBar` بـ `Dock = Bottom`، و `TextBox` متعدد الأسطر أو `DataGridView` بـ `Dock = Fill`. نافذة كاملة تتكيف مع أي حجم بدون سطر كود واحد.

## جرّب في المصمم

لا تحتاج تشغيل البرنامج لترى النتيجة: **اسحب حافة النموذج** في المصمم لتكبّره أو تصغّره، والأدوات المربوطة تتحرك وتتمدد أمامك.
وعند التشغيل يتصرف برنامجك بالطريقة نفسها في كل اللغات (BASIC و Python و غيرها)، لأن البيئة تولّد له الحساب نفسه.

## الحساب خلف الستار

البيئة تحوّل Anchor و Dock إلى معادلة بسيطة لكل أداة. لنفترض أن النافذة كانت بعرض `400` ثم صارت `600` (زادت `200`):

- زر بـ `Anchor = Top, Right`: الحافة اليسرى تزيد بمقدار الزيادة: `Left` الجديد = `Left` القديم + `200`.
- مربع بـ `Anchor = Top, Left, Right`: العرض يزيد بمقدار الزيادة: `Width` الجديد = `Width` القديم + `200`.
- أداة بلا يسار ولا يمين: تتحرك **نصف** الزيادة لتبقى في المنتصف.

هذا البرنامج يحسب ذلك بنفسه:

```vb run
Function NewLeft(oldLeft As Integer, anchorText As String, grow As Integer) As Integer
    If InStr(anchorText, "Left") > 0 Then
        NewLeft = oldLeft
    ElseIf InStr(anchorText, "Right") > 0 Then
        NewLeft = oldLeft + grow
    Else
        NewLeft = oldLeft + grow \ 2
    End If
End Function

Function NewWidth(oldWidth As Integer, anchorText As String, grow As Integer) As Integer
    If InStr(anchorText, "Left") > 0 And InStr(anchorText, "Right") > 0 Then
        NewWidth = oldWidth + grow
    Else
        NewWidth = oldWidth
    End If
End Function

Sub Main()
    Dim grow As Integer
    grow = 600 - 400
    Debug.Print "زر بحث (Top, Right): Left = " & NewLeft(300, "Top, Right", grow)
    Debug.Print "مربع بحث (Top, Left, Right): Width = " & NewWidth(260, "Top, Left, Right", grow)
    Debug.Print "شعار (Top): Left = " & NewLeft(150, "Top", grow)
End Sub
```

```text output
زر بحث (Top, Right): Left = 500
مربع بحث (Top, Left, Right): Width = 460
شعار (Top): Left = 250
```

> ⚠️ **في كود BASIC:** إذا غيّرت `Left` أو `Top` أو `Width` أو `Height` لأداة أثناء التشغيل، تتوقف تلك الأداة عن اتباع Anchor و Dock، لأنك أخذت قيادتها بيدك.

## أخطاء شائعة

- **تفعيل Left و Right لزر:** الزر يتمدد ويصبح عريضًا جدًا. الأزرار عادة `Right` فقط أو `Bottom, Right`.
- **أداة Fill تغطي الأدوات الأخرى:** ترتيب الالتصاق خطأ. أرسل أداة `Fill` إلى **الأمام** (Bring to Front) لتأخذ ما تبقى بعد غيرها.
- **ضبط Anchor والنموذج ثابت الحجم:** إذا كان `FormBorderStyle` ثابتًا فلن يكبّر المستخدم النافذة أصلًا.
- **نسيان الحاوية:** Anchor يُحسب بالنسبة **لحاوية الأداة** (`Panel` أو `GroupBox`)، لا للنموذج دائمًا.

## تمرين

### تمرين 1: زر في الزاوية السفلية

أضف دالة `NewTop` بالمنطق نفسه لكن للارتفاع: إذا كان في Anchor كلمة `Top` تبقى القيمة، وإلا إذا كان فيه `Bottom` تزيد بمقدار الزيادة.
النافذة ارتفاعها زاد من `300` إلى `450`. زر "موافق" مكانه `Top = 250` و `Anchor = Bottom, Right`. اطبع: `زر موافق: Top = 400`.

```vb exercise
Sub Main()
    Dim grow As Integer
    grow = 450 - 300
    ' اكتب الدالة NewTop واطبع النتيجة
End Sub
```

```vb solution
Function NewTop(oldTop As Integer, anchorText As String, grow As Integer) As Integer
    If InStr(anchorText, "Top") > 0 Then
        NewTop = oldTop
    ElseIf InStr(anchorText, "Bottom") > 0 Then
        NewTop = oldTop + grow
    Else
        NewTop = oldTop + grow \ 2
    End If
End Function

Sub Main()
    Dim grow As Integer
    grow = 450 - 300
    Debug.Print "زر موافق: Top = " & NewTop(250, "Bottom, Right", grow)
End Sub
```

```text output
زر موافق: Top = 400
```

### مهمة عملية: محرر يملأ النافذة

1. في مشروع جديد ضع `Panel` واجعل `Dock = Top` و `Height = 40`، وضع فيه زرّين.
2. ضع `StatusBar` واجعل `Dock = Bottom`.
3. ضع `TextBox`، واجعل `MultiLine = True`، ثم `Dock = Fill`.
4. اسحب حافة النموذج في المصمم: كل شيء يتكيف. شغّل البرنامج وكبّر النافذة.
5. إذا غطى مربع النص اللوحة، حدده واختر **Format > Order > Bring to Front**.

## اختبر نفسك

```quiz
{"question": "تريد أن يلحق زر \"بحث\" بالحافة اليمنى عند تكبير النافذة دون أن يتمدد. أي Anchor؟", "choices": ["`Top, Left`", "`Top, Right`", "`Top, Left, Right`", "`Dock = Fill`"], "answer": 1, "explanation": "Right وحده يحرك الأداة مع الحافة اليمنى، و Left + Right يمدها."}
```

```quiz
{"question": "أي قيمة Dock تجعل الأداة تأخذ كل المساحة الباقية؟", "choices": ["`Top`", "`None`", "`Fill`", "`Left`"], "answer": 2, "explanation": "Fill تأخذ ما تبقى بعد الأدوات الملتصقة الأخرى."}
```

```quiz
{"question": "مربع بعرض 200 وله `Anchor = Top, Left, Right`، والنافذة زاد عرضها 100. كم يصبح عرضه؟", "choices": ["200", "250", "300", "100"], "answer": 2, "explanation": "اليسار واليمين معًا يمدان الأداة بمقدار الزيادة: 200 + 100 = 300."}
```

## الخلاصة

- `Anchor` حبال إلى الحواف: `Right` يحرك، و `Left + Right` يمد، وبلا الاثنين يبقى في المنتصف.
- `Dock` يلصق بجانب كامل: `Top` و `Bottom` و `Left` و `Right` و `Fill` لما تبقى، والترتيب بـ Bring to Front / Send to Back.
- جرّب بسحب حافة النموذج في المصمم، والبرنامج يتصرف بالطريقة نفسها عند التشغيل.
