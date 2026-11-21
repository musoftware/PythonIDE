# الدرس 3: المتغيرات وأنواع البيانات

البرامج تتعامل مع **بيانات**: اسم المستخدم، وعمره، وسعر المنتج، وهل الطلب مدفوع أم لا. وحتى يتذكر البرنامج هذه البيانات نضعها في **متغيرات**.

## ما هو المتغير؟

> **تشبيه:** المتغير مثل **علبة عليها ملصق**. الملصق هو **اسم** المتغير، وما بداخل العلبة هو **القيمة**. ونوع العلبة يحدد ما يمكن وضعه فيها: علبة للأرقام الصحيحة، وعلبة للنصوص... ولا يمكنك وضع نص في علبة الأرقام.

في C# نعرّف المتغير هكذا: **النوع** ثم **الاسم** ثم (اختياريًا) `=` و**القيمة الابتدائية**:

```csharp run
int age = 25;
string name = "خالد";
double height = 1.75;
bool isStudent = true;

Console.WriteLine(name);
Console.WriteLine(age);
Console.WriteLine(height);
Console.WriteLine(isStudent);
```

```text output
خالد
25
1.75
True
```

## أهم أنواع البيانات

| النوع | يخزّن | مثال |
|---|---|---|
| `int` | عدد صحيح (حتى نحو 2 مليار) | `int count = 10;` |
| `long` | عدد صحيح كبير جدًا | `long population = 8000000000;` |
| `double` | عدد عشري | `double price = 19.99;` |
| `decimal` | عدد عشري دقيق للأموال | `decimal salary = 4500.50m;` |
| `bool` | صح أو خطأ: `true` / `false` | `bool done = false;` |
| `char` | حرف واحد بين `' '` | `char grade = 'A';` |
| `string` | نص بين `" "` | `string city = "طنطا";` |

لاحظ الحرف `m` بعد رقم `decimal`، فهو يقول للمترجم إن هذا الرقم من نوع `decimal` وليس `double`.

## تغيير قيمة المتغير

المتغير اسمه «متغير» لأن قيمته **تتغير**:

```csharp run
int score = 10;
Console.WriteLine($"النقاط: {score}");

score = 25;
Console.WriteLine($"النقاط: {score}");

score = score + 5;
Console.WriteLine($"النقاط: {score}");
```

```text output
النقاط: 10
النقاط: 25
النقاط: 30
```

السطر `score = score + 5;` يُقرأ هكذا: «خذ القيمة الحالية لـ `score`، وأضف إليها 5، ثم ضع الناتج في `score` من جديد».

## الكلمة `var`: دع المترجم يستنتج النوع

```csharp run
var city = "أسوان";   // المترجم يعرف أنها string
var year = 2026;       // int
var pi = 3.14;         // double

Console.WriteLine(city.GetType().Name);
Console.WriteLine(year.GetType().Name);
Console.WriteLine(pi.GetType().Name);
```

```text output
String
Int32
Double
```

`var` لا تعني «أي نوع»؛ النوع يُحدد مرة واحدة من القيمة الابتدائية ولا يتغير بعدها. والاسمان `Int32` و`String` هما الاسمان الكاملان في .NET لـ `int` و`string`.

## الثوابت: `const`

إذا كانت القيمة لا يجب أن تتغير أبدًا، فاجعلها **ثابتًا**:

```csharp run
const double Pi = 3.14159;
const int DaysInWeek = 7;

double r = 2;
Console.WriteLine($"مساحة الدائرة = {Pi * r * r}");
Console.WriteLine($"عدد أيام 3 أسابيع = {DaysInWeek * 3}");
```

```text output
مساحة الدائرة = 12.56636
عدد أيام 3 أسابيع = 21
```

## التحويل بين الأنواع

### من نص إلى رقم: `int.Parse` و`double.Parse`

```csharp run
string text = "42";
int number = int.Parse(text);
Console.WriteLine(number + 8);

string priceText = "12.5";
double price = double.Parse(priceText);
Console.WriteLine(price * 2);
```

```text output
50
25
```

### من رقم إلى نص: `ToString()`

```csharp run
int n = 7;
string s = n.ToString();
Console.WriteLine(s + s);   // دمج نصين وليس جمع رقمين
Console.WriteLine(n + n);   // جمع رقمين
```

```text output
77
14
```

### التحويل الصريح (Casting)

```csharp run
double d = 9.8;
int i = (int)d;            // يقطع الكسر ولا يقرّب
Console.WriteLine(i);

int a = 7, b = 2;
double avg = (double)a / b;
Console.WriteLine(avg);
```

```text output
9
3.5
```

> **مهم:** `(int)9.8` تعطي `9` وليس `10`، لأنها **تقطع** الجزء العشري. وإذا أردت التقريب فاستخدم `Math.Round(9.8)`.

## قواعد تسمية المتغيرات

- يبدأ بحرف أو `_`، ولا يبدأ برقم: `total1` صحيح، و`1total` خطأ.
- بلا مسافات: اكتب `studentName` وليس `student name`.
- لا يكون كلمة محجوزة مثل `int` أو `class`.
- العُرف في C#: المتغيرات المحلية بأسلوب **camelCase** (`firstName`)، والثوابت والأصناف بأسلوب **PascalCase** (`MaxScore`).

## أخطاء شائعة

### استخدام متغير قبل إعطائه قيمة

<!-- compile-error -->
```csharp
int total;
Console.WriteLine(total);
```

```text
Program.cs(2,19): error CS0165: Use of unassigned local variable 'total'
```

C# لا تسمح لك بقراءة متغير محلي لم تضع فيه قيمة بعد. اكتب `int total = 0;`.

### وضع نص في متغير رقمي

<!-- compile-error -->
```csharp
int age = "عشرون";
```

```text
Program.cs(1,11): error CS0029: Cannot implicitly convert type 'string' to 'int'
```

### نسيان `m` مع `decimal`

<!-- compile-error -->
```csharp
decimal price = 10.5;
```

```text
error CS0664: Literal of type double cannot be implicitly converted to type 'decimal'; use an 'M' suffix
```

## تمارين

### التمرين 1

عرّف متغيرات لكتاب: العنوان `string`، وعدد الصفحات `int`، والسعر `double`، ومتوفر `bool`. ثم اطبعها كما في الناتج.

```csharp exercise
// عرّف المتغيرات ثم اطبع:
// الكتاب: البرمجة للجميع
// الصفحات: 320
// السعر: 150.5
// متوفر: True
```

```csharp solution
string title = "البرمجة للجميع";
int pages = 320;
double price = 150.5;
bool available = true;
Console.WriteLine($"الكتاب: {title}");
Console.WriteLine($"الصفحات: {pages}");
Console.WriteLine($"السعر: {price}");
Console.WriteLine($"متوفر: {available}");
```

```text output
الكتاب: البرمجة للجميع
الصفحات: 320
السعر: 150.5
متوفر: True
```

### التمرين 2

حوّل النصين `"15"` و`"27"` إلى أرقام، ثم اطبع مجموعهما.

```csharp exercise
string a = "15";
string b = "27";
// اطبع المجموع: 42
```

```csharp solution
string a = "15";
string b = "27";
int sum = int.Parse(a) + int.Parse(b);
Console.WriteLine(sum);
```

```text output
42
```

### التمرين 3

بدّل قيمتي المتغيرين `x` و`y` باستخدام متغير ثالث مؤقت `temp`.

```csharp exercise
int x = 3;
int y = 8;
// بدّل القيمتين هنا
Console.WriteLine($"x = {x}, y = {y}");
```

```csharp solution
int x = 3;
int y = 8;
int temp = x;
x = y;
y = temp;
Console.WriteLine($"x = {x}, y = {y}");
```

```text output
x = 8, y = 3
```

## اختبر نفسك

```quiz
{"question": "ما النوع المناسب لتخزين سعر منتج بدقة في برنامج محاسبة؟", "choices": ["int", "bool", "decimal", "char"], "answer": 2, "explanation": "decimal مصمم للأموال لأنه لا يفقد الدقة في الكسور العشرية مثل double."}
```

```quiz
{"question": "ما ناتج (int)7.9؟", "choices": ["8", "7", "7.9", "خطأ ترجمة"], "answer": 1, "explanation": "التحويل الصريح إلى int يقطع الجزء العشري ولا يقرّب."}
```

```quiz
{"question": "ماذا يطبع: Console.WriteLine(\"5\" + \"5\");؟", "choices": ["10", "55", "5 5", "خطأ"], "answer": 1, "explanation": "علامة + بين نصين تدمجهما ولا تجمع الأرقام."}
```

```quiz
{"question": "ما معنى var في C#؟", "choices": ["متغير يقبل أي نوع في أي وقت", "المترجم يستنتج النوع من القيمة الابتدائية ثم لا يتغير", "ثابت لا يتغير", "متغير عام"], "answer": 1, "explanation": "var مجرد اختصار: النوع يُحدد مرة واحدة وقت الترجمة."}
```

## الخلاصة

- المتغير علبة لها **نوع** و**اسم** و**قيمة**: `int age = 25;`.
- الأنواع الأساسية: `int` و`long` و`double` و`decimal` و`bool` و`char` و`string`.
- `var` يستنتج النوع، و`const` يمنع التغيير.
- التحويل: `int.Parse` و`double.Parse` و`ToString()` و`(int)`.
