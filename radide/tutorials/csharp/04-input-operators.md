# الدرس 4: الإدخال والعمليات الحسابية

حتى الآن كانت برامجنا تطبع فقط. اليوم نجعلها **تسأل** المستخدم وتقرأ إجابته، ثم **تحسب** بها.

## قراءة سطر من المستخدم: `Console.ReadLine()`

```csharp run
Console.Write("ما اسمك؟ ");
string name = Console.ReadLine();
Console.WriteLine($"أهلًا يا {name}!");
```

```text input
منى
```

```text output
ما اسمك؟ أهلًا يا منى!
```

- `Console.ReadLine()` تنتظر حتى يكتب المستخدم سطرًا ويضغط Enter، ثم **ترجع** النص الذي كتبه.
- عند الضغط على «جرّبه» تعمل البرامج التي تقرأ من لوحة المفاتيح كما يلي: الـ IDE ترسل المدخلات المكتوبة في الدرس (المربع «المدخلات»)، أو تسألك أنت أن تكتبها.

> **لماذا يظهر الاسم في نفس سطر السؤال؟** لأن ما يكتبه المستخدم لا يظهر في الناتج عندما تأتي المدخلات من ملف أو من الـ IDE، فيبقى المؤشر بعد `ما اسمك؟ ` مباشرة. وعند التشغيل في نافذة أوامر حقيقية سترى ما تكتبه وتنزل سطرًا.

## قراءة الأرقام

`ReadLine` ترجع **نصًا** دائمًا. فإذا أردت رقمًا يجب أن تحوّله:

```csharp run
Console.Write("العدد الأول: ");
int a = int.Parse(Console.ReadLine());
Console.Write("العدد الثاني: ");
int b = int.Parse(Console.ReadLine());
Console.WriteLine();
Console.WriteLine($"المجموع = {a + b}");
```

```text input
12
30
```

```text output
العدد الأول: العدد الثاني: 
المجموع = 42
```

## الحماية من الإدخال الخاطئ: `int.TryParse`

ماذا لو كتب المستخدم «عشرة» بدل `10`؟ الدالة `int.Parse` ستوقف البرنامج بخطأ. الأفضل استخدام `int.TryParse` التي **تحاول** التحويل وتخبرك هل نجحت:

```csharp run
Console.Write("كم عمرك؟ ");
string text = Console.ReadLine();

if (int.TryParse(text, out int age))
    Console.WriteLine($"بعد 10 سنوات سيصبح عمرك {age + 10}");
else
    Console.WriteLine($"«{text}» ليس رقمًا صحيحًا");
```

```text input
عشرون
```

```text output
كم عمرك؟ «عشرون» ليس رقمًا صحيحًا
```

`out int age` معناها: «إذا نجح التحويل فضع الرقم في متغير جديد اسمه `age`». وسنفهم `if` و`else` في الدرس القادم.

## العمليات الحسابية

| العامل | المعنى | مثال | الناتج |
|---|---|---|---|
| `+` | جمع | `7 + 2` | `9` |
| `-` | طرح | `7 - 2` | `5` |
| `*` | ضرب | `7 * 2` | `14` |
| `/` | قسمة | `7 / 2` | `3` (أعداد صحيحة!) |
| `%` | باقي القسمة | `7 % 2` | `1` |

```csharp run
int a = 17, b = 5;
Console.WriteLine(a + b);
Console.WriteLine(a - b);
Console.WriteLine(a * b);
Console.WriteLine(a / b);        // قسمة صحيحة
Console.WriteLine(a % b);        // الباقي
Console.WriteLine(17.0 / 5);     // قسمة عشرية
```

```text output
22
12
85
3
2
3.4
```

> **مهم جدًا:** إذا كان طرفا القسمة `/` عددين صحيحين فالناتج عدد صحيح ويُحذف الكسر: `17 / 5` تساوي `3`. اجعل أحد الطرفين عشريًا (`17.0`) أو حوّله بـ `(double)` لتحصل على `3.4`.

### أولوية العمليات

الضرب والقسمة والباقي قبل الجمع والطرح، والأقواس قبل الجميع، تمامًا كما في الرياضيات:

```csharp run
Console.WriteLine(2 + 3 * 4);
Console.WriteLine((2 + 3) * 4);
Console.WriteLine(10 - 4 / 2);
```

```text output
14
20
8
```

## الاختصارات: `+=` و`++`

```csharp run
int points = 10;
points += 5;    // points = points + 5
points -= 3;    // points = points - 3
points *= 2;    // points = points * 2
Console.WriteLine(points);

int count = 0;
count++;        // count = count + 1
count++;
count--;        // count = count - 1
Console.WriteLine(count);
```

```text output
24
1
```

## الدوال الرياضية: `Math`

```csharp run
Console.WriteLine(Math.Sqrt(16));        // الجذر التربيعي
Console.WriteLine(Math.Pow(2, 10));      // 2 أس 10
Console.WriteLine(Math.Abs(-7));         // القيمة المطلقة
Console.WriteLine(Math.Round(3.756, 2)); // التقريب لرقمين عشريين
Console.WriteLine(Math.Max(4, 9));       // الأكبر
Console.WriteLine(Math.Min(4, 9));       // الأصغر
```

```text output
4
1024
7
3.76
9
4
```

## تنسيق الأرقام عند الطباعة

```csharp run
double price = 1234.5;
Console.WriteLine($"{price:F2}");     // رقمان عشريان
Console.WriteLine($"{price:N2}");     // فواصل الآلاف
Console.WriteLine($"{0.256:P1}");     // نسبة مئوية
Console.WriteLine($"[{42,6}]");       // عرض 6 خانات محاذاة لليمين
```

```text output
1234.50
1,234.50
25.6 %
[    42]
```

## مثال كامل: حساب الفاتورة

```csharp run
Console.Write("سعر القطعة: ");
double price = double.Parse(Console.ReadLine());
Console.Write("الكمية: ");
int qty = int.Parse(Console.ReadLine());

double total = price * qty;
double tax = total * 0.14;
Console.WriteLine();
Console.WriteLine($"الإجمالي قبل الضريبة: {total:F2}");
Console.WriteLine($"الضريبة 14%: {tax:F2}");
Console.WriteLine($"المطلوب: {total + tax:F2}");
```

```text input
25.5
4
```

```text output
سعر القطعة: الكمية: 
الإجمالي قبل الضريبة: 102.00
الضريبة 14%: 14.28
المطلوب: 116.28
```

## أخطاء شائعة

- **نسيان التحويل:** `int a = Console.ReadLine();` خطأ ترجمة، لأن `ReadLine` ترجع `string`.
- **القسمة الصحيحة دون قصد:** `double avg = (a + b) / 2;` ستحذف الكسر إذا كان `a` و`b` من نوع `int`. اكتب `/ 2.0`.
- **`int.Parse` مع نص غير رقمي** يوقف البرنامج برسالة `FormatException`. استخدم `int.TryParse` عندما يكتب المستخدم.

## تمارين

### التمرين 1

اقرأ طول المستطيل وعرضه (عددين صحيحين)، ثم اطبع المساحة والمحيط.

```csharp exercise
// اقرأ الطول ثم العرض
// اطبع: المساحة = ...  ثم  المحيط = ...
```

```csharp solution
int length = int.Parse(Console.ReadLine());
int width = int.Parse(Console.ReadLine());
Console.WriteLine($"المساحة = {length * width}");
Console.WriteLine($"المحيط = {2 * (length + width)}");
```

```text input
6
4
```

```text output
المساحة = 24
المحيط = 20
```

### التمرين 2

اقرأ عددًا من الثواني (مثل `3725`) واطبعه بالساعات والدقائق والثواني باستخدام `/` و`%`.

```csharp exercise
int total = int.Parse(Console.ReadLine());
// اطبع: 1 ساعة و 2 دقيقة و 5 ثانية
```

```csharp solution
int total = int.Parse(Console.ReadLine());
int hours = total / 3600;
int minutes = total % 3600 / 60;
int seconds = total % 60;
Console.WriteLine($"{hours} ساعة و {minutes} دقيقة و {seconds} ثانية");
```

```text input
3725
```

```text output
1 ساعة و 2 دقيقة و 5 ثانية
```

### التمرين 3

اقرأ ثلاث درجات عشرية، واطبع متوسطها برقمين عشريين.

```csharp exercise
// اقرأ ثلاث درجات ثم اطبع: المتوسط = ...
```

```csharp solution
double a = double.Parse(Console.ReadLine());
double b = double.Parse(Console.ReadLine());
double c = double.Parse(Console.ReadLine());
Console.WriteLine($"المتوسط = {(a + b + c) / 3:F2}");
```

```text input
85
90.5
77
```

```text output
المتوسط = 84.17
```

## اختبر نفسك

```quiz
{"question": "ما نوع القيمة التي ترجعها Console.ReadLine()؟", "choices": ["int", "double", "string", "bool"], "answer": 2, "explanation": "ReadLine ترجع النص الذي كتبه المستخدم دائمًا، ونحوله نحن إلى رقم عند الحاجة."}
```

```quiz
{"question": "ما ناتج 9 / 2 في C# إذا كان العددان int؟", "choices": ["4.5", "4", "5", "خطأ"], "answer": 1, "explanation": "قسمة عددين صحيحين تعطي عددًا صحيحًا ويُحذف الكسر."}
```

```quiz
{"question": "ما ناتج 20 % 6؟", "choices": ["3", "2", "3.33", "0"], "answer": 1, "explanation": "20 = 6 × 3 + 2، فالباقي 2."}
```

```quiz
{"question": "متى نستخدم int.TryParse بدل int.Parse؟", "choices": ["عندما نريد برنامجًا أسرع", "عندما قد يكتب المستخدم نصًا غير رقمي ولا نريد أن يتوقف البرنامج", "مع الأعداد العشرية فقط", "لا فرق بينهما"], "answer": 1, "explanation": "TryParse ترجع false بدل أن توقف البرنامج بخطأ."}
```

## الخلاصة

- `Console.ReadLine()` تقرأ سطرًا نصيًا، و`int.Parse` / `double.Parse` / `int.TryParse` تحوله إلى رقم.
- العوامل: `+ - * / %`، وانتبه للقسمة الصحيحة.
- `+=` و`++` اختصارات، و`Math` فيها الدوال الرياضية.
- التنسيق: `{x:F2}` و`{x:N2}` و`{x:P1}`.
