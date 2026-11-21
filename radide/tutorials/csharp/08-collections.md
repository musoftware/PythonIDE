# الدرس 8: المصفوفات والقوائم والقواميس

ماذا لو أردت تخزين درجات 30 طالبًا؟ هل تعرّف 30 متغيرًا؟ بالطبع لا. نحتاج إلى **مجموعة** (collection) تحمل قيمًا كثيرة تحت اسم واحد.

> **تشبيه:** المصفوفة مثل **خزانة أدراج مرقّمة**: كل درج له رقم يبدأ من **صفر**، وفي كل درج قيمة واحدة. والقائمة `List` خزانة **تتمدد** وحدها كلما أضفت درجًا.

## المصفوفات (Arrays)

```csharp run
int[] grades = { 85, 92, 78, 64, 99 };

Console.WriteLine(grades[0]);        // أول عنصر
Console.WriteLine(grades[4]);        // آخر عنصر
Console.WriteLine(grades.Length);    // عدد العناصر

grades[2] = 80;                      // تغيير عنصر
Console.WriteLine(grades[2]);
```

```text output
85
99
5
80
```

- النوع `int[]` معناه «مصفوفة أعداد صحيحة».
- **الفهرس** (index) يبدأ من `0`، فآخر عنصر فهرسه `Length - 1`.

### إنشاء مصفوفة بحجم محدد

```csharp run
string[] names = new string[3];
names[0] = "علي";
names[1] = "هدى";
names[2] = "مريم";

for (int i = 0; i < names.Length; i++)
    Console.WriteLine($"{i + 1}. {names[i]}");
```

```text output
1. علي
2. هدى
3. مريم
```

### المرور على المصفوفة بـ `foreach`

```csharp run
double[] prices = { 12.5, 30, 7.25, 50 };
double total = 0;
double max = prices[0];

foreach (double p in prices)
{
    total += p;
    if (p > max)
        max = p;
}
Console.WriteLine($"المجموع = {total}");
Console.WriteLine($"الأغلى = {max}");
Console.WriteLine($"المتوسط = {total / prices.Length:F2}");
```

```text output
المجموع = 99.75
الأغلى = 50
المتوسط = 24.94
```

### ترتيب المصفوفة والبحث فيها

```csharp run
int[] nums = { 42, 7, 19, 3, 25 };
Array.Sort(nums);
Console.WriteLine(string.Join(", ", nums));
Console.WriteLine(Array.IndexOf(nums, 19));
Array.Reverse(nums);
Console.WriteLine(string.Join(" ", nums));
```

```text output
3, 7, 19, 25, 42
2
42 25 19 7 3
```

`string.Join` تجمع عناصر المجموعة في نص واحد يفصل بينها الفاصل الذي تختاره.

## القوائم: `List<T>`

المصفوفة حجمها **ثابت**، أما `List` فتكبر وتصغر:

```csharp run
List<string> fruits = new List<string>();
fruits.Add("تفاح");
fruits.Add("موز");
fruits.Add("برتقال");
Console.WriteLine($"عدد الفواكه: {fruits.Count}");

fruits.Insert(1, "مانجو");       // في الموضع 1
fruits.Remove("موز");
Console.WriteLine(string.Join("، ", fruits));
Console.WriteLine(fruits.Contains("تفاح"));
Console.WriteLine(fruits[0]);
```

```text output
عدد الفواكه: 3
تفاح، مانجو، برتقال
True
تفاح
```

`<string>` تحدد نوع العناصر، فـ `List<int>` قائمة أعداد، و`List<double>` قائمة أعداد عشرية. ويمكنك اختصار الإنشاء: `List<int> nums = new() { 1, 2, 3 };`.

| الدالة / الخاصية | وظيفتها |
|---|---|
| `Add(x)` | تضيف في النهاية |
| `Insert(i, x)` | تضيف في الموضع `i` |
| `Remove(x)` | تحذف أول عنصر يساوي `x` |
| `RemoveAt(i)` | تحذف العنصر في الموضع `i` |
| `Count` | عدد العناصر |
| `Contains(x)` | هل العنصر موجود؟ |
| `Sort()` | ترتيب |
| `Clear()` | حذف الكل |

## القواميس: `Dictionary<TKey, TValue>`

القاموس يخزّن أزواجًا: **مفتاح** ← **قيمة**، مثل دليل الهاتف (الاسم ← الرقم):

```csharp run
Dictionary<string, int> stock = new Dictionary<string, int>();
stock["أقلام"] = 120;
stock["دفاتر"] = 45;
stock["مساطر"] = 30;

stock["دفاتر"] += 5;                 // تعديل قيمة
Console.WriteLine(stock["دفاتر"]);
Console.WriteLine(stock.ContainsKey("ممحاة"));

foreach (var pair in stock)
    Console.WriteLine($"{pair.Key}: {pair.Value}");
```

```text output
50
False
أقلام: 120
دفاتر: 50
مساطر: 30
```

> **انتبه:** قراءة مفتاح غير موجود مثل `stock["ممحاة"]` توقف البرنامج بخطأ `KeyNotFoundException`. افحص أولًا بـ `ContainsKey` أو استخدم `TryGetValue`.

### مثال: عدّ تكرار الكلمات

```csharp run
string text = "قط كلب قط عصفور كلب قط";
var counts = new Dictionary<string, int>();
foreach (string w in text.Split(' '))
{
    if (counts.ContainsKey(w))
        counts[w]++;
    else
        counts[w] = 1;
}
foreach (var p in counts)
    Console.WriteLine($"{p.Key} = {p.Value}");
```

```text output
قط = 3
كلب = 2
عصفور = 1
```

## لمحة عن LINQ

**LINQ** طريقة قوية لطرح «أسئلة» على المجموعات في سطر واحد:

```csharp run
List<int> nums = new() { 5, 12, 8, 3, 20, 15 };

Console.WriteLine(nums.Sum());
Console.WriteLine(nums.Max());
Console.WriteLine(nums.Average());

var big = nums.Where(n => n > 10).ToList();
Console.WriteLine(string.Join(", ", big));

var doubled = nums.Select(n => n * 2);
Console.WriteLine(string.Join(", ", doubled));

var sorted = nums.OrderByDescending(n => n);
Console.WriteLine(string.Join(", ", sorted));
```

```text output
63
20
10.5
12, 20, 15
10, 24, 16, 6, 40, 30
20, 15, 12, 8, 5, 3
```

`n => n > 10` تسمى **تعبير لامدا** (lambda): دالة صغيرة بلا اسم تقول «لكل `n`، هل `n > 10`؟».

## المصفوفات ثنائية الأبعاد

```csharp run
int[,] table = {
    { 1, 2, 3 },
    { 4, 5, 6 }
};
for (int r = 0; r < table.GetLength(0); r++)
{
    for (int c = 0; c < table.GetLength(1); c++)
        Console.Write(table[r, c] + " ");
    Console.WriteLine();
}
```

```text output
1 2 3
4 5 6
```

## أخطاء شائعة

### تجاوز حدود المصفوفة

```csharp
int[] a = { 1, 2, 3 };
Console.WriteLine(a[3]);   // لا يوجد عنصر رقم 3!
```

يتوقف البرنامج برسالة `IndexOutOfRangeException: Index was outside the bounds of the array`. تذكر أن آخر فهرس هو `Length - 1`.

### تعديل القائمة أثناء المرور عليها بـ `foreach`

حذف عنصر من `List` داخل `foreach` عليها يعطي `InvalidOperationException`. استخدم `for` تنازلية، أو `RemoveAll(x => ...)`.

## تمارين

### التمرين 1

اكتب برنامجًا يطبع أكبر وأصغر عنصر في المصفوفة دون استخدام `Max` و`Min`.

```csharp exercise
int[] values = { 14, -3, 27, 8, 0, 19 };
// اطبع: الأكبر = 27  ثم  الأصغر = -3
```

```csharp solution
int[] values = { 14, -3, 27, 8, 0, 19 };
int max = values[0], min = values[0];
foreach (int v in values)
{
    if (v > max) max = v;
    if (v < min) min = v;
}
Console.WriteLine($"الأكبر = {max}");
Console.WriteLine($"الأصغر = {min}");
```

```text output
الأكبر = 27
الأصغر = -3
```

### التمرين 2

اقرأ أسماء حتى يكتب المستخدم سطرًا فارغًا، وأضفها إلى `List<string>`، ثم اطبعها مرتبة أبجديًا مرقمة.

```csharp exercise
var names = new List<string>();
// اقرأ حتى سطر فارغ ثم رتّب واطبع
```

```csharp solution
var names = new List<string>();
while (true)
{
    string line = Console.ReadLine();
    if (string.IsNullOrEmpty(line))
        break;
    names.Add(line);
}
names.Sort();
for (int i = 0; i < names.Count; i++)
    Console.WriteLine($"{i + 1}. {names[i]}");
```

```text input
Sara
Adam
Mona

```

```text output
1. Adam
2. Mona
3. Sara
```

### التمرين 3

لديك قاموس بأسعار المنتجات. اطبع المنتجات التي سعرها أقل من 20 باستخدام LINQ `Where`.

```csharp exercise
var prices = new Dictionary<string, double>
{
    ["خبز"] = 5, ["جبن"] = 45, ["لبن"] = 18, ["عسل"] = 120, ["بيض"] = 12
};
// اطبع: خبز ثم لبن ثم بيض
```

```csharp solution
var prices = new Dictionary<string, double>
{
    ["خبز"] = 5, ["جبن"] = 45, ["لبن"] = 18, ["عسل"] = 120, ["بيض"] = 12
};
foreach (var p in prices.Where(p => p.Value < 20))
    Console.WriteLine(p.Key);
```

```text output
خبز
لبن
بيض
```

## اختبر نفسك

```quiz
{"question": "ما فهرس آخر عنصر في مصفوفة طولها 10؟", "choices": ["10", "9", "11", "1"], "answer": 1, "explanation": "الفهارس تبدأ من 0، فآخرها Length - 1 = 9."}
```

```quiz
{"question": "ما الفرق الأساسي بين المصفوفة وList<T>؟", "choices": ["List أسرع دائمًا", "حجم المصفوفة ثابت أما List فتكبر وتصغر", "المصفوفة للنصوص فقط", "لا فرق"], "answer": 1, "explanation": "المصفوفة تُنشأ بحجم ثابت، وList تضيف وتحذف بحرية."}
```

```quiz
{"question": "ما المناسب لتخزين رقم هاتف لكل اسم؟", "choices": ["int[]", "List<string>", "Dictionary<string, string>", "string"], "answer": 2, "explanation": "القاموس يربط مفتاحًا (الاسم) بقيمة (الرقم)."}
```

```quiz
{"question": "ماذا يعطي nums.Where(n => n % 2 == 0)؟", "choices": ["عدد الأعداد الزوجية", "الأعداد الزوجية فقط من nums", "أول عدد زوجي", "true أو false"], "answer": 1, "explanation": "Where ترشّح العناصر وتُبقي التي يتحقق فيها الشرط."}
```

## الخلاصة

- المصفوفة `int[]` حجمها ثابت وفهارسها تبدأ من 0.
- `List<T>` قائمة مرنة: `Add` و`Remove` و`Count`.
- `Dictionary<TKey, TValue>` يربط المفاتيح بالقيم.
- LINQ: `Sum` و`Max` و`Where` و`Select` و`OrderBy` في سطر واحد.
