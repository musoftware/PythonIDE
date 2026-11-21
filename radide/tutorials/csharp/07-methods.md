# الدرس 7: الدوال (Methods)

كلما كبر البرنامج صار من الصعب قراءته في كتلة واحدة طويلة. **الدالة** (method) تجمع مجموعة تعليمات تحت اسم واحد، فنستدعيها كلما احتجنا إليها بدل تكرار الكود.

> **تشبيه:** الدالة مثل **ماكينة العصير**: تضع فيها فاكهة (المُدخلات أو **المعاملات**)، فتعطيك عصيرًا (**القيمة المُرجعة**). ولا تحتاج أن تعرف كيف تعمل من الداخل لكي تستخدمها.

## دالة بسيطة بلا مدخلات ولا مخرجات

```csharp run
static void SayHello()
{
    Console.WriteLine("مرحبًا بك في برنامجنا!");
    Console.WriteLine("-----------------------");
}

SayHello();
SayHello();
```

```text output
مرحبًا بك في برنامجنا!
-----------------------
مرحبًا بك في برنامجنا!
-----------------------
```

- `static void SayHello()` **تعريف** الدالة: `void` تعني أنها لا ترجع قيمة.
- `SayHello();` **استدعاء** الدالة، أي تشغيل ما بداخلها.

> **ملحوظة:** في البرامج المختصرة (top-level) نكتب الدوال في نفس الملف مع التعليمات. وفي الشكل الكامل تكون الدوال داخل `class Program` بجانب `Main`، كما سترى بعد قليل.

## المعاملات (Parameters)

```csharp run
static void Greet(string name, int age)
{
    Console.WriteLine($"أهلًا {name}، عمرك {age} سنة");
}

Greet("سلمى", 14);
Greet("يوسف", 9);
```

```text output
أهلًا سلمى، عمرك 14 سنة
أهلًا يوسف، عمرك 9 سنة
```

`name` و`age` **معاملات** (parameters): متغيرات تستقبل القيم التي نرسلها عند الاستدعاء. والقيم نفسها `"سلمى"` و`14` تسمى **وسائط** (arguments).

## إرجاع قيمة: `return`

```csharp run
static int Square(int x)
{
    return x * x;
}

static double Average(double a, double b, double c)
{
    return (a + b + c) / 3;
}

int s = Square(6);
Console.WriteLine(s);
Console.WriteLine(Square(3) + Square(4));
Console.WriteLine(Average(80, 90, 70));
```

```text output
36
25
80
```

النوع قبل اسم الدالة (`int`، `double`) هو نوع القيمة التي ترجعها. و`return` تنهي الدالة فورًا وترجع القيمة.

### الدالة ذات التعبير الواحد `=>`

إذا كانت الدالة تعليمة `return` واحدة، يمكن اختصارها:

```csharp run
static int Cube(int x) => x * x * x;
static bool IsEven(int n) => n % 2 == 0;

Console.WriteLine(Cube(3));
Console.WriteLine(IsEven(10));
```

```text output
27
True
```

## الشكل الكامل: الدوال داخل الصنف

```csharp run
class Program
{
    static void Main()
    {
        double c = 37;
        Console.WriteLine($"{c} مئوية = {ToFahrenheit(c)} فهرنهايت");
        PrintLine(20);
    }

    static double ToFahrenheit(double celsius)
    {
        return celsius * 9 / 5 + 32;
    }

    static void PrintLine(int length)
    {
        Console.WriteLine(new string('=', length));
    }
}
```

```text output
37 مئوية = 98.6 فهرنهايت
====================
```

## القيم الافتراضية والوسائط المسماة

```csharp run
static void Order(string item, int qty = 1, bool delivery = false)
{
    Console.WriteLine($"{qty} × {item}" + (delivery ? " (توصيل)" : ""));
}

Order("قهوة");
Order("شاي", 3);
Order("كعك", delivery: true);
```

```text output
1 × قهوة
3 × شاي
1 × كعك (توصيل)
```

- `int qty = 1` قيمة **افتراضية**: إذا لم نرسل `qty` تكون 1.
- `delivery: true` وسيط **مسمى**: نذكر اسم المعامل فنتخطى ما قبله.

## التحميل الزائد (Overloading)

يمكن أن تتشارك عدة دوال **نفس الاسم** إذا اختلفت معاملاتها:

```csharp run
class Program
{
    static int Add(int a, int b) => a + b;
    static double Add(double a, double b) => a + b;
    static int Add(int a, int b, int c) => a + b + c;

    static void Main()
    {
        Console.WriteLine(Add(2, 3));
        Console.WriteLine(Add(2.5, 3.1));
        Console.WriteLine(Add(1, 2, 3));
    }
}
```

```text output
5
5.6
6
```

المترجم يختار الدالة المناسبة بحسب أنواع الوسائط وعددها.

> **ملحوظة:** التحميل الزائد يعمل مع دوال **الصنف** كما في هذا المثال. أما الدوال المكتوبة مباشرة بين تعليمات البرنامج المختصر (top-level) فهي دوال محلية، ولا يُسمح بأن يتكرر اسمها.

## `ref` و`out`: تعديل متغيرات المستدعي

عادة ترسل C# **نسخة** من القيمة، فلا يتأثر المتغير الأصلي. مع `ref` ترسل المتغير نفسه:

```csharp run
static void DoubleIt(ref int n)
{
    n = n * 2;
}

static void MinMax(int a, int b, out int min, out int max)
{
    min = Math.Min(a, b);
    max = Math.Max(a, b);
}

int x = 5;
DoubleIt(ref x);
Console.WriteLine(x);

MinMax(8, 3, out int lo, out int hi);
Console.WriteLine($"الأصغر {lo} والأكبر {hi}");
```

```text output
10
الأصغر 3 والأكبر 8
```

`out` تعني أن الدالة **ستضع** قيمة في المتغير، وهي طريقة لإرجاع أكثر من قيمة (مثل `int.TryParse` التي رأيناها).

## نطاق المتغيرات (Scope)

المتغير المعرّف داخل دالة **محلي** لها: لا يُرى خارجها، ويُنشأ من جديد في كل استدعاء.

```csharp run
static void Counter()
{
    int count = 0;
    count++;
    Console.WriteLine(count);
}

Counter();
Counter();
```

```text output
1
1
```

## الاستدعاء الذاتي (Recursion)

الدالة يمكنها أن تستدعي نفسها، بشرط وجود **حالة توقف**:

```csharp run
static long Factorial(int n)
{
    if (n <= 1)
        return 1;              // حالة التوقف
    return n * Factorial(n - 1);
}

Console.WriteLine(Factorial(5));
Console.WriteLine(Factorial(15));
```

```text output
120
1307674368000
```

## أخطاء شائعة

### نسيان `return` في دالة ترجع قيمة

<!-- compile-error -->
```csharp
static int Twice(int x)
{
    int y = x * 2;
}
```

```text
error CS0161: 'Twice(int)': not all code paths return a value
```

### عدد الوسائط أو نوعها خطأ

`Greet("سلمى")` خطأ إذا كانت الدالة تحتاج معاملين، والمترجم يقول `CS7036: There is no argument given that corresponds to the required parameter 'age'`.

### نسيان الأقواس عند الاستدعاء

`SayHello;` بدون `()` لا تستدعي الدالة، وتعطي خطأ ترجمة.

## تمارين

### التمرين 1

اكتب دالة `Max3` ترجع أكبر عدد من ثلاثة أعداد صحيحة.

```csharp exercise
static int Max3(int a, int b, int c)
{
    // اكتب الكود هنا
    return 0;
}

Console.WriteLine(Max3(4, 9, 2));
Console.WriteLine(Max3(-1, -5, -3));
```

```csharp solution
static int Max3(int a, int b, int c)
{
    int m = a;
    if (b > m) m = b;
    if (c > m) m = c;
    return m;
}

Console.WriteLine(Max3(4, 9, 2));
Console.WriteLine(Max3(-1, -5, -3));
```

```text output
9
-1
```

### التمرين 2

اكتب دالة `IsPrime` ترجع `true` إذا كان العدد أوليًا، ثم اطبع الأعداد الأولية من 2 إلى 30.

```csharp exercise
static bool IsPrime(int n)
{
    // العدد الأولي لا يقبل القسمة إلا على 1 وعلى نفسه
    return false;
}

for (int i = 2; i <= 30; i++)
    if (IsPrime(i))
        Console.Write(i + " ");
Console.WriteLine();
```

```csharp solution
static bool IsPrime(int n)
{
    if (n < 2)
        return false;
    for (int d = 2; d * d <= n; d++)
        if (n % d == 0)
            return false;
    return true;
}

for (int i = 2; i <= 30; i++)
    if (IsPrime(i))
        Console.Write(i + " ");
Console.WriteLine();
```

```text output
2 3 5 7 11 13 17 19 23 29
```

### التمرين 3

اكتب دالة `Power(double b, int e = 2)` تحسب الأس بحلقة (دون `Math.Pow`)، والقيمة الافتراضية للأس 2.

```csharp exercise
static double Power(double b, int e = 2)
{
    return 0;
}

Console.WriteLine(Power(5));
Console.WriteLine(Power(2, 10));
Console.WriteLine(Power(1.5, 3));
```

```csharp solution
static double Power(double b, int e = 2)
{
    double result = 1;
    for (int i = 0; i < e; i++)
        result *= b;
    return result;
}

Console.WriteLine(Power(5));
Console.WriteLine(Power(2, 10));
Console.WriteLine(Power(1.5, 3));
```

```text output
25
1024
3.375
```

## اختبر نفسك

```quiz
{"question": "ماذا تعني void قبل اسم الدالة؟", "choices": ["الدالة فارغة", "الدالة لا ترجع قيمة", "الدالة خاصة", "الدالة ترجع صفرًا"], "answer": 1, "explanation": "void تعني أن الدالة تنفذ عملًا لكنها لا ترجع قيمة."}
```

```quiz
{"question": "ما المقصود بالتحميل الزائد (overloading)؟", "choices": ["دالة طويلة جدًا", "عدة دوال بنفس الاسم ومعاملات مختلفة", "استدعاء الدالة لنفسها", "دالة بلا معاملات"], "answer": 1, "explanation": "المترجم يميز بينها بعدد المعاملات وأنواعها."}
```

```quiz
{"question": "لماذا يطبع المثال Counter() الرقم 1 في كل مرة؟", "choices": ["خطأ في C#", "لأن count متغير محلي يُنشأ من جديد بقيمة 0 في كل استدعاء", "لأن ++ لا تعمل", "لأن الدالة static"], "answer": 1, "explanation": "المتغيرات المحلية لا تحتفظ بقيمتها بين الاستدعاءات."}
```

```quiz
{"question": "ما الذي يجب أن تحتويه كل دالة تستدعي نفسها (recursive)؟", "choices": ["حلقة for", "حالة توقف", "متغير عام", "return void"], "answer": 1, "explanation": "بدون حالة توقف تستدعي الدالة نفسها إلى ما لا نهاية حتى يمتلئ المكدس (StackOverflow)."}
```

## الخلاصة

- الدالة: نوع القيمة المرجعة ثم الاسم ثم المعاملات، و`return` ترجع القيمة.
- `=>` لدوال التعبير الواحد، والقيم الافتراضية والوسائط المسماة تسهّل الاستدعاء.
- التحميل الزائد: نفس الاسم بمعاملات مختلفة.
- `ref` و`out` لتعديل متغيرات المستدعي، والمتغيرات المحلية تخص دالتها فقط.
