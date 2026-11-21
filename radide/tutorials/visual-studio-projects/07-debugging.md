# الدرس 7: تصحيح الأخطاء بـ netcoredbg

البرنامج يُبنى بلا أخطاء، لكنه يعطي نتيجة خاطئة أو يتوقف فجأة باستثناء. هنا يأتي دور **المصحح** (debugger): توقف البرنامج عند سطر تختاره، وترى قيم المتغيرات، وتتقدم سطرًا سطرًا حتى تجد الخطأ.

> **تشبيه:** المصحح مثل **المحقق** في قصة بوليسية: بدل أن يخمّن من الفاعل، يذهب إلى مكان الحادث (نقطة التوقف)، ويفحص الأدلة (المتغيرات)، ويعيد تمثيل ما حدث خطوة بخطوة (F10)، حتى يكتشف الحقيقة.

## تجهيز المصحح

مشاريع .NET الحديثة (`.csproj` و`.vbproj` و`.fsproj` بإطار .NET 5 فما بعد) تُصحَّح بـ **netcoredbg**، وهو مصحح مفتوح المصدر من Samsung:

1. نزّل `netcoredbg-win64.zip` من صفحة المشروع `github.com/Samsung/netcoredbg` (قسم Releases).
2. فك الضغط بحيث يصبح الملف في `%LOCALAPPDATA%\RADIDE\tools\netcoredbg\netcoredbg.exe` (أو في أي مجلد ضمن `PATH`).
3. إذا لم تجده الـ IDE عند `F5` ستكتب ذلك في نافذة **Output**، ويمكنك التشغيل بلا تصحيح بـ `Ctrl+F5`.

> **ملحوظة:** مشاريع .NET Framework القديمة تُبنى وتُشغَّل في RAD IDE، لكن netcoredbg لا يصححها. صححها في Visual Studio، أو حدّث المشروع إلى .NET الحديث.

## برنامج فيه خطأ

هذا البرنامج يحسب الخصم على سلة مشتريات: 10% إذا تجاوز المجموع 500. لكن الناتج غير صحيح:

```csharp run
var prices = new List<decimal> { 200m, 150m, 180m };
decimal total = CartTotal(prices);
Console.WriteLine($"المجموع بعد الخصم: {total}");

static decimal CartTotal(List<decimal> items)
{
    decimal sum = 0;
    for (int i = 1; i < items.Count; i++)
    {
        sum += items[i];
    }
    if (sum > 500)
        sum -= sum * 0.10m;
    return sum;
}
```

```text output
المجموع بعد الخصم: 330
```

المتوقع: `200 + 150 + 180 = 530`، وبعد خصم 10% يصبح `477`. فلماذا ظهر `330`؟

## الخطوات

### 1) ضع نقطة توقف

افتح المثال في المحرر (زر «افتح في المحرر»)، وضع المؤشر على السطر `sum += items[i];` واضغط **F9** (**Debug > Toggle Breakpoint** / تصحيح الأخطاء > تبديل نقطة التوقف). تظهر دائرة حمراء في الهامش. ويمكنك أيضًا النقر في الهامش بجانب رقم السطر.

### 2) شغّل مع التصحيح

اضغط **F5** (**Debug > Start Debugging / Continue**). تبني الـ IDE المشروع بإعداد `Debug`، وتشغله تحت netcoredbg، فيتوقف البرنامج **قبل** تنفيذ السطر المعلّم ويظهر بلون مميز.

### 3) افحص الأدلة

| النافذة | الاسم العربي | ماذا ترى فيها |
|---|---|---|
| **Locals** | المتغيرات المحلية | `items` (3 عناصر)، و`sum = 0`، و`i = 1` |
| **Watch** | المراقبة | تعبيرات تكتبها بنفسك، مثل `items[i]` أو `items.Count` |
| **Call Stack** | مكدس الاستدعاءات | `CartTotal` ثم الدالة الرئيسية التي استدعتها |
| **Immediate** | الأوامر الفورية | اكتب تعبيرًا واضغط Enter، مثل `items[0]` فيظهر `200` |

لاحظ أن `i` تبدأ من `1`! أي أن العنصر الأول `items[0] = 200` لن يُجمع أبدًا. وجدنا الخطأ.

### 4) تأكد خطوة بخطوة

| المفتاح | الأمر | الاسم العربي |
|---|---|---|
| `F10` | Step Over | خطوة فوق |
| `F11` | Step Into | خطوة إلى الداخل |
| `Shift+F11` | Step Out | خطوة إلى الخارج |
| `F5` | Continue | متابعة |
| `Shift+F5` | Stop Debugging | إيقاف تصحيح الأخطاء |

اضغط `F5` عدة مرات: يتوقف البرنامج في كل لفّة من الحلقة، وترى في **Locals** أن `sum` تصبح `150` ثم `330` فقط. وإذا وضعت نقطة التوقف على سطر الاستدعاء `CartTotal(prices)` فاضغط `F11` لتدخل إلى الدالة، و`Shift+F11` لتخرج منها.

### 5) الإصلاح

```csharp run
var prices = new List<decimal> { 200m, 150m, 180m };
decimal total = CartTotal(prices);
Console.WriteLine($"المجموع بعد الخصم: {total}");

static decimal CartTotal(List<decimal> items)
{
    decimal sum = 0;
    for (int i = 0; i < items.Count; i++)
    {
        sum += items[i];
    }
    if (sum > 500)
        sum -= sum * 0.10m;
    return sum;
}
```

```text output
المجموع بعد الخصم: 477.00
```

لماذا `477.00` وليس `477`؟ النوع `decimal` يحتفظ بعدد الخانات العشرية من العملية: `530 × 0.10m = 53.00` (خانتان مثل `0.10m`)، ثم `530 - 53.00 = 477.00`. ولتتحكم في الشكل بنفسك اكتب `{total:F0}` أو `{total:F2}`.

## تصحيح برامج Windows Forms

نفس الخطوات: ضع نقطة توقف داخل `btnHello_Click` في `Form1.cs` (أو `Form1.vb`)، واضغط `F5`، ثم اضغط الزر في نافذة البرنامج. يتوقف التنفيذ عند السطر، وتعود الـ IDE إلى المقدمة، وترى قيمة `txtName.Text` في **Locals** أو **Watch**.

## الاستثناءات أثناء التصحيح

إذا رمى البرنامج استثناءً لا يعالجه (مثل `NullReferenceException` أو `ArgumentOutOfRangeException`) أثناء التصحيح، يتوقف المصحح عند السطر الذي حدث فيه، فترى السبب في الحال بدل رسالة طويلة في نهاية التشغيل.

## تمرين

البرنامج التالي يجب أن يطبع أطول كلمة في الجملة، لكنه يطبع كلمة خاطئة. ضع نقطة توقف داخل الحلقة وراقب `longest` و`word` لتجد الخطأ، ثم أصلحه.

```csharp exercise
string sentence = "البرمجة ممتعة جدا مع المصحح";
string longest = "";
foreach (string word in sentence.Split(' '))
{
    if (word.Length < longest.Length)
        longest = word;
}
Console.WriteLine($"أطول كلمة: {longest}");
```

```csharp solution
string sentence = "البرمجة ممتعة جدا مع المصحح";
string longest = "";
foreach (string word in sentence.Split(' '))
{
    if (word.Length > longest.Length)
        longest = word;
}
Console.WriteLine($"أطول كلمة: {longest}");
```

```text output
أطول كلمة: البرمجة
```

## اختبر نفسك

```quiz
{"question": "أي مصحح تستخدمه RAD IDE لمشاريع .NET الحديثة؟", "choices": ["gdb", "netcoredbg", "JDWP", "pdb"], "answer": 1, "explanation": "netcoredbg مصحح .NET مفتوح المصدر من Samsung، ويُوضع في %LOCALAPPDATA%\\RADIDE\\tools\\netcoredbg."}
```

```quiz
{"question": "توقف البرنامج على سطر فيه استدعاء دالة، وتريد الدخول إليها. أي مفتاح تضغط؟", "choices": ["F10", "F11", "Shift+F11", "F9"], "answer": 1, "explanation": "F11 = Step Into يدخل الدالة، وF10 ينفذها كوحدة واحدة."}
```

```quiz
{"question": "أين تكتب تعبيرًا مثل items.Count لتراقب قيمته باستمرار أثناء التصحيح؟", "choices": ["Output", "Watch", "Toolbox", "Error List"], "answer": 1, "explanation": "نافذة Watch (المراقبة) تعرض قيم التعبيرات التي تضيفها كلما توقف البرنامج."}
```

## الخلاصة

- ضع `netcoredbg.exe` في `%LOCALAPPDATA%\RADIDE\tools\netcoredbg\`.
- `F9` نقطة توقف، و`F5` تشغيل مع التصحيح ومتابعة، و`F10` / `F11` / `Shift+F11` للتنقل، و`Shift+F5` للإيقاف.
- **Locals** و**Watch** و**Call Stack** و**Immediate** لفحص البرنامج أثناء التوقف.
- نفس الخطوات للكونسول وWindows Forms، وC# وVB.NET.
