# الدرس 6: اختبارات الوحدة ومستكشف الاختبارات

**في هذا الدرس ستتعلم:**

- ما هو **اختبار الوحدة** (Unit test)، ولماذا يوفر عليك ساعات من التصحيح.
- كتابة اختبارات BASIC بالطريقة البسيطة التي تفهمها البيئة: وحدة `TestMath.bas` فيها `Sub TestAdd()` و `AssertEqual`.
- نافذة **Test Explorer** (مستكشف الاختبارات): تشغيل كل الاختبارات أو الفاشلة فقط، وقراءة سبب الفشل.
- الأطر المدعومة في اللغات الأخرى: pytest و Jest و go test و cargo test و dotnet test و PHPUnit ...

## جرس الإنذار

تخيّل أنك أصلحت حنفية في المطبخ فانقطعت المياه عن الحمام دون أن تنتبه. في البرمجة يحدث هذا كثيرًا: تعدّل دالة فتكسر دالة أخرى تعتمد عليها.
**اختبار الوحدة** كود صغير يتحقق من أن دالة واحدة تعطي النتيجة الصحيحة. مجموعة الاختبارات مثل **جرس إنذار**: بعد كل تعديل تضغط زرًّا، فإن انكسر شيء رنّ الجرس وأخبرك أين.

## اختبارات BASIC: الطريقة السهلة

البيئة تتعرف على اختبارات BASIC بقاعدة بسيطة:

1. **وحدة** (Module) اسم ملفها يبدأ بـ `Test` أو ينتهي بـ `Test` أو `Tests`، مثل `TestMath.bas` أو `MathTests.bas`.
2. فيها إجراءات عامة **بلا معاملات** يبدأ اسمها بـ `Test`، مثل `Sub TestAdd()`.
3. داخلها **تأكيدات** (Assertions):

| التأكيد | ينجح عندما |
|---|---|
| `AssertEqual expected, actual [, message]` | القيمتان متساويتان |
| `AssertTrue condition [, message]` / `Assert condition` | الشرط صحيح |
| `AssertFalse condition [, message]` | الشرط خطأ |
| `Fail message` | لا ينجح أبدًا (للحالات التي يجب ألا تصل إليها) |

الاختبار **يفشل** إذا فشل تأكيد أو حدث خطأ تشغيل. وحدات المشروع الأخرى تُحمّل معه، فتستطيع الاختبارات استدعاء دوالك.

## مثال: مكتبة حسابات واختباراتها

هذا مشروع فيه ثلاث وحدات: `MathLib.bas` (الدوال)، و `TestMath.bas` (الاختبارات)، و `Module1.bas` (البرنامج نفسه). اضغط «افتح في المحرر»، ثم افتح **Test > Test Explorer** (`Ctrl+E, T`) واضغط **Run All**:

<!-- test: {"vbtest": {"TestAdd": "passed", "TestTax": "passed", "TestIsEven": "passed"}} -->
```vb
'#file: MathLib.bas
Public Function Add(a As Long, b As Long) As Long
    Add = a + b
End Function

Public Function Tax(amount As Long) As Long
    Tax = amount * 14 \ 100
End Function

Public Function IsEven(n As Long) As Boolean
    IsEven = (n Mod 2 = 0)
End Function
'#file: TestMath.bas
Public Sub TestAdd()
    AssertEqual 5, Add(2, 3)
    AssertEqual 0, Add(-4, 4)
End Sub

Public Sub TestTax()
    AssertEqual 14, Tax(100), "ضريبة 100"
    AssertEqual 0, Tax(0)
End Sub

Public Sub TestIsEven()
    AssertTrue IsEven(10)
    AssertFalse IsEven(7)
End Sub
```

وهذه الدوال نفسها تعمل في برنامج عادي:

```vb run
'#file: Module1.bas
Sub Main()
    Debug.Print "2 + 3 = " & Add(2, 3)
    Debug.Print "ضريبة 250 = " & Tax(250)
    Debug.Print "10 زوجي؟ " & IsEven(10)
End Sub
'#file: MathLib.bas
Public Function Add(a As Long, b As Long) As Long
    Add = a + b
End Function

Public Function Tax(amount As Long) As Long
    Tax = amount * 14 \ 100
End Function

Public Function IsEven(n As Long) As Boolean
    IsEven = (n Mod 2 = 0)
End Function
```

```text output
2 + 3 = 5
ضريبة 250 = 35
10 زوجي؟ True
```

## نافذة Test Explorer

افتحها من **Test > Test Explorer** (اختبار > مستكشف الاختبارات) أو `Ctrl+E` ثم `T`.

- **الشجرة**: الملف ← المجموعة ← الاختبار، ولكل اختبار **لون حالته** ومدة تشغيله: أخضر نجح، وأحمر فشل.
- **الجزء السفلي**: رسالة الفشل وناتج الاختبار المحدد، وسجل التشغيل كله، وملخص التغطية.
- **انقر الاختبار مرتين** لتفتحه على سطره.

| الأمر | القائمة | الاختصار |
|---|---|---|
| تشغيل كل الاختبارات | **Test > Run All Tests** (تشغيل كل الاختبارات) | `Ctrl+R` ثم `A` |
| الفاشلة فقط | **Test > Run Failed Tests** (تشغيل الاختبارات الفاشلة) | — |
| اختبارات الملف الحالي | **Test > Run Tests in Current File** | `Ctrl+R` ثم `T` |
| تصحيح اختبار بالمصحح | **Test > Debug Selected Test** (في Python) | — |
| إعادة اكتشاف الاختبارات | **Test > Refresh Tests** | — |

وفي شريط النافذة نفسها: **Run All** و **Run** و **Run Failed** و **Debug** و **Coverage** و **Stop** و **Refresh**.

## عندما يفشل اختبار

لنفترض أن أحدًا "حسّن" دالة الضريبة فكتب `amount * 14 / 1000` بالخطأ. شغّل الاختبارات: `TestTax` يصبح **أحمر**، ورسالته:

```text
ضريبة 100: expected <14> but was <1>
```

الرسالة تخبرك **ما المتوقع** و**ما الذي حدث** واسم الحالة التي كتبتها. انقر الاختبار مرتين، وصحّح الدالة، ثم **Run Failed Tests**.

<!-- test: {"vbtest": {"TestTax": "failed", "TestAdd": "passed"}} -->
```vb
'#file: MathLib.bas
Public Function Add(a As Long, b As Long) As Long
    Add = a + b
End Function

Public Function Tax(amount As Long) As Long
    Tax = amount * 14 \ 1000
End Function
'#file: TestMath.bas
Public Sub TestAdd()
    AssertEqual 5, Add(2, 3)
End Sub

Public Sub TestTax()
    AssertEqual 14, Tax(100), "ضريبة 100"
End Sub
```

## اللغات الأخرى

Test Explorer يكتشف الأطر تلقائيًا من مجلد المشروع:

| اللغة | الإطار |
|---|---|
| Python | pytest و unittest (من بيئة `.venv` للمشروع) |
| JavaScript / TypeScript | Jest و Vitest و `node --test` |
| Go | `go test` |
| Rust | `cargo test` |
| C#‎ | `dotnet test` (xUnit و NUnit و MSTest) |
| PHP | PHPUnit |
| Dart / Flutter | `dart test` و `flutter test` |
| Java | JUnit 5 |
| Ruby | minitest و RSpec |
| Ring | ملفات `test_*.ring` بدوال `test...` |

## أخطاء شائعة

- **الاختبارات لا تظهر:** اسم الوحدة لا يبدأ ولا ينتهي بـ `Test`، أو الإجراء له معاملات، أو اسمه لا يبدأ بـ `Test`. ثم **Refresh Tests**.
- **وضع `expected` و `actual` بالعكس:** الاختبار يعمل، لكن الرسالة تصبح مربكة. المتوقع أولًا.
- **اختبار يعتمد على اختبار آخر:** كل اختبار يجب أن يعمل وحده وبأي ترتيب.
- **اختبار كل شيء في اختبار واحد ضخم:** اجعل كل اختبار يفحص فكرة واحدة باسم واضح.

## تمرين

### تمرين 1: أصلح الدالة حتى تنجح

الدالة `Discount` يجب أن تُرجع خصم 10% للمبالغ من 1000 فأكثر، وصفرًا لما دونها. لكنها تعطي الخصم لكل المبالغ. الاختبار في التعليق يوضح المطلوب. أصلحها حتى يطبع البرنامج النتائج الصحيحة.

```vb exercise
' TestDiscount:
'     AssertEqual 0, Discount(999)
'     AssertEqual 100, Discount(1000)
'     AssertEqual 250, Discount(2500)
Public Function Discount(amount As Long) As Long
    Discount = amount \ 10
End Function

Sub Main()
    Debug.Print Discount(999) & " " & Discount(1000) & " " & Discount(2500)
End Sub
```

```vb solution
Public Function Discount(amount As Long) As Long
    If amount >= 1000 Then
        Discount = amount \ 10
    Else
        Discount = 0
    End If
End Function

Sub Main()
    Debug.Print Discount(999) & " " & Discount(1000) & " " & Discount(2500)
End Sub
```

```text output
0 100 250
```

### مهمة عملية: أول مجموعة اختبارات

1. أنشئ مشروع **Console Application** بلغة BASIC.
2. **Project > Add Module...** باسم `MathLib` والصق دوال المثال، ثم وحدة أخرى باسم `TestMath` والصق الاختبارات.
3. `Ctrl+E, T` ثم **Run All**: ثلاثة اختبارات خضراء.
4. خرّب `Tax` عمدًا، واحفظ، و `Ctrl+R, A`: اقرأ رسالة الفشل، ثم أصلح و **Run Failed Tests**.

## اختبر نفسك

```quiz
{"question": "أي اسم وحدة تتعرف عليه البيئة كوحدة اختبارات BASIC؟", "choices": ["`Math.bas`", "`TestMath.bas`", "`Module1.bas`", "`Checks.bas`"], "answer": 1, "explanation": "اسم الملف يبدأ بـ Test أو ينتهي بـ Test أو Tests."}
```

```quiz
{"question": "ماذا تعني الرسالة `expected <14> but was <1>`؟", "choices": ["الاختبار نجح", "المتوقع 14 لكن الدالة أعطت 1", "خطأ في البيئة", "يجب حذف الاختبار"], "answer": 1, "explanation": "AssertEqual يذكر القيمة المتوقعة ثم الفعلية."}
```

```quiz
{"question": "بعد إصلاح الخطأ، ما أسرع طريقة لإعادة الاختبارات التي فشلت فقط؟", "choices": ["Run Failed Tests", "إعادة تشغيل الحاسوب", "حذف الاختبارات", "F9"], "answer": 0, "explanation": "Test > Run Failed Tests يعيد الفاشلة فقط."}
```

## الخلاصة

- اختبار الوحدة جرس إنذار لكل دالة: شغّله بعد كل تعديل.
- BASIC: وحدة `Test*.bas` فيها `Sub TestX()` و `AssertEqual` و `AssertTrue` و `AssertFalse` و `Fail`.
- **Test Explorer** (`Ctrl+E, T`): **Run All** (`Ctrl+R, A`)، و **Run Failed**، والرسالة تخبرك بالمتوقع والفعلي.
- أطر اللغات الأخرى تُكتشف تلقائيًا: pytest و Jest و go test و cargo test و dotnet test و PHPUnit و JUnit ...
