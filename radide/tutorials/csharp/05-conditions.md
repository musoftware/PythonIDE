# الدرس 5: الشروط واتخاذ القرار

البرنامج الذكي يتصرف بحسب الموقف: إذا كانت كلمة المرور صحيحة يدخل المستخدم، وإلا تظهر رسالة خطأ. هذا ما تفعله **الشروط**.

> **تشبيه:** الشرط مثل **إشارة المرور**: إذا كانت خضراء تمر، وإذا كانت حمراء تقف. البرنامج ينظر إلى «الإشارة» (الشرط) ثم يختار الطريق.

## عوامل المقارنة

كل مقارنة ناتجها `bool`: إما `true` أو `false`.

| العامل | المعنى | مثال | الناتج |
|---|---|---|---|
| `==` | يساوي | `5 == 5` | `True` |
| `!=` | لا يساوي | `5 != 3` | `True` |
| `>` | أكبر من | `5 > 8` | `False` |
| `<` | أصغر من | `5 < 8` | `True` |
| `>=` | أكبر من أو يساوي | `5 >= 5` | `True` |
| `<=` | أصغر من أو يساوي | `4 <= 3` | `False` |

> **انتبه:** `=` للإسناد (وضع قيمة)، و`==` للمقارنة. الخلط بينهما من أشهر الأخطاء.

## `if` و`else`

```csharp run
int temperature = 38;

if (temperature > 35)
{
    Console.WriteLine("الجو حار جدًا، اشرب ماءً كثيرًا");
}
else
{
    Console.WriteLine("الجو معتدل");
}
Console.WriteLine("انتهى البرنامج");
```

```text output
الجو حار جدًا، اشرب ماءً كثيرًا
انتهى البرنامج
```

- الشرط يُكتب بين قوسين `( )` بعد `if`.
- إذا كان الشرط `true` تُنفذ الكتلة الأولى، وإلا تُنفذ كتلة `else`.
- إذا كانت الكتلة تعليمة واحدة يمكن حذف `{ }`، لكن كتابتها عادة جيدة تمنع الأخطاء.

## سلسلة `else if`

```csharp run
int grade = 78;

if (grade >= 90)
    Console.WriteLine("ممتاز");
else if (grade >= 80)
    Console.WriteLine("جيد جدًا");
else if (grade >= 65)
    Console.WriteLine("جيد");
else if (grade >= 50)
    Console.WriteLine("مقبول");
else
    Console.WriteLine("راسب");
```

```text output
جيد
```

تُفحص الشروط بالترتيب من الأعلى، وأول شرط صحيح يُنفذ ثم **تُترك بقية السلسلة**.

## العوامل المنطقية: و / أو / ليس

| العامل | المعنى | يكون صحيحًا عندما |
|---|---|---|
| `&&` | و (AND) | الطرفان صحيحان |
| `||` | أو (OR) | أحد الطرفين على الأقل صحيح |
| `!` | ليس (NOT) | يقلب القيمة |

```csharp run
int age = 20;
bool hasTicket = true;

if (age >= 18 && hasTicket)
    Console.WriteLine("مسموح بالدخول");

string day = "الجمعة";
if (day == "الجمعة" || day == "السبت")
    Console.WriteLine("عطلة نهاية الأسبوع");

bool isRaining = false;
if (!isRaining)
    Console.WriteLine("يمكنك الخروج دون مظلة");
```

```text output
مسموح بالدخول
عطلة نهاية الأسبوع
يمكنك الخروج دون مظلة
```

## `switch`: الاختيار من قيم كثيرة

عندما نقارن متغيرًا واحدًا بقيم كثيرة، يكون `switch` أوضح من سلسلة `if`:

```csharp run
int day = 3;

switch (day)
{
    case 1:
        Console.WriteLine("الأحد");
        break;
    case 2:
        Console.WriteLine("الإثنين");
        break;
    case 3:
        Console.WriteLine("الثلاثاء");
        break;
    case 6:
    case 7:
        Console.WriteLine("عطلة");
        break;
    default:
        Console.WriteLine("يوم آخر");
        break;
}
```

```text output
الثلاثاء
```

- كل `case` ينتهي بـ `break` (إلزامي في C#).
- عدة `case` متتالية تشترك في نفس الكود (6 و7 هنا).
- `default` تعمل إذا لم يطابق أي `case`.

## تعبير `switch` الحديث

في C# الحديثة يوجد شكل مختصر يرجع **قيمة**:

```csharp run
int month = 4;
string season = month switch
{
    12 or 1 or 2 => "الشتاء",
    3 or 4 or 5 => "الربيع",
    6 or 7 or 8 => "الصيف",
    _ => "الخريف"
};
Console.WriteLine(season);

int score = 72;
string level = score switch
{
    >= 90 => "A",
    >= 75 => "B",
    >= 60 => "C",
    _ => "F"
};
Console.WriteLine(level);
```

```text output
الربيع
C
```

الرمز `_` يعني «أي قيمة أخرى»، مثل `default`.

## العامل الثلاثي `? :`

اختصار لـ `if/else` صغير يرجع قيمة:

```csharp run
int n = 7;
string kind = n % 2 == 0 ? "زوجي" : "فردي";
Console.WriteLine($"{n} عدد {kind}");
```

```text output
7 عدد فردي
```

يُقرأ: «هل `n % 2 == 0`؟ إذا نعم فالقيمة `"زوجي"`، وإلا `"فردي"`».

## مثال: آلة حاسبة بسيطة

```csharp run
double a = double.Parse(Console.ReadLine());
string op = Console.ReadLine();
double b = double.Parse(Console.ReadLine());

switch (op)
{
    case "+": Console.WriteLine(a + b); break;
    case "-": Console.WriteLine(a - b); break;
    case "*": Console.WriteLine(a * b); break;
    case "/":
        if (b == 0)
            Console.WriteLine("لا يمكن القسمة على صفر");
        else
            Console.WriteLine(a / b);
        break;
    default:
        Console.WriteLine("عملية غير معروفة");
        break;
}
```

```text input
9
/
2
```

```text output
4.5
```

## أخطاء شائعة

### استخدام `=` بدل `==`

<!-- compile-error -->
```csharp
int x = 5;
if (x = 5)
    Console.WriteLine("خمسة");
```

```text
Program.cs(2,5): error CS0029: Cannot implicitly convert type 'int' to 'bool'
```

لحسن الحظ يكتشف مترجم C# هذا الخطأ، لأن الشرط يجب أن يكون `bool`.

### فاصلة منقوطة بعد `if`

```csharp
if (x > 10);
    Console.WriteLine("أكبر من 10");   // سيُطبع دائمًا!
```

الفاصلة المنقوطة بعد `if (...)` تنهي الشرط بتعليمة فارغة، فيصبح السطر التالي خارج الشرط. المترجم يعطيك تحذيرًا `CS0642`، فلا تتجاهله.

### نسيان `break` في `switch`

C# تمنعك من «السقوط» من `case` إلى التالي دون `break`، وتعطيك الخطأ `CS0163`.

## تمارين

### التمرين 1

اقرأ عددًا صحيحًا، واطبع هل هو موجب أم سالب أم صفر.

```csharp exercise
int n = int.Parse(Console.ReadLine());
// اطبع: موجب / سالب / صفر
```

```csharp solution
int n = int.Parse(Console.ReadLine());
if (n > 0)
    Console.WriteLine("موجب");
else if (n < 0)
    Console.WriteLine("سالب");
else
    Console.WriteLine("صفر");
```

```text input
-4
```

```text output
سالب
```

### التمرين 2

اقرأ سنة، واطبع هل هي **كبيسة**. السنة كبيسة إذا كانت تقبل القسمة على 4 ولا تقبل القسمة على 100، أو إذا كانت تقبل القسمة على 400.

```csharp exercise
int year = int.Parse(Console.ReadLine());
// اطبع: 2024 سنة كبيسة   أو   2023 سنة عادية
```

```csharp solution
int year = int.Parse(Console.ReadLine());
bool leap = (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
Console.WriteLine(leap ? $"{year} سنة كبيسة" : $"{year} سنة عادية");
```

```text input
2024
```

```text output
2024 سنة كبيسة
```

### التمرين 3

اقرأ رقم الشهر (1 إلى 12) واطبع عدد أيامه في سنة عادية باستخدام تعبير `switch`.

```csharp exercise
int month = int.Parse(Console.ReadLine());
// 2 -> 28،  4 و6 و9 و11 -> 30،  الباقي -> 31
```

```csharp solution
int month = int.Parse(Console.ReadLine());
int days = month switch
{
    2 => 28,
    4 or 6 or 9 or 11 => 30,
    _ => 31
};
Console.WriteLine(days);
```

```text input
9
```

```text output
30
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين = و== في C#؟", "choices": ["لا فرق", "= للإسناد و== للمقارنة", "= للمقارنة و== للإسناد", "== للنصوص فقط"], "answer": 1, "explanation": "x = 5 تضع القيمة 5 في x، أما x == 5 فتسأل: هل x يساوي 5؟"}
```

```quiz
{"question": "متى يكون الشرط (a > 0 && b > 0) صحيحًا؟", "choices": ["إذا كان a موجبًا فقط", "إذا كان أحدهما موجبًا", "إذا كان الاثنان موجبين", "دائمًا"], "answer": 2, "explanation": "&& يتطلب أن يكون الطرفان صحيحين معًا."}
```

```quiz
{"question": "ماذا يعني الرمز _ في تعبير switch؟", "choices": ["خطأ", "أي قيمة أخرى لم تطابق ما قبلها", "القيمة صفر", "النص الفارغ"], "answer": 1, "explanation": "_ هي الحالة الافتراضية مثل default."}
```

## الخلاصة

- المقارنات `== != > < >= <=` ناتجها `bool`.
- `if` / `else if` / `else` لاختيار طريق واحد من عدة طرق.
- `&&` و`||` و`!` لربط الشروط.
- `switch` وتعبير `switch` الحديث للمقارنة بقيم كثيرة، و`? :` لاختيار قيمة بسرعة.
