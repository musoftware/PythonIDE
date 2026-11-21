# الدرس 9: التعامل مع النصوص

النصوص في كل مكان: أسماء المستخدمين، والرسائل، والعناوين، ومحتوى الملفات. في C# النص من نوع `string`، ومعه عشرات الدوال الجاهزة.

> **تشبيه:** النص مثل **قطار** من العربات، وكل عربة فيها حرف واحد (`char`)، والعربات مرقمة من 0. يمكنك أن تعرف طول القطار، وتنظر في عربة معينة، وتقطع جزءًا منه... لكنك لا تستطيع تغيير عربة في مكانها: النصوص في C# **غير قابلة للتعديل** (immutable)، وكل دالة ترجع نصًا **جديدًا**.

## الطول والحروف

```csharp run
string word = "Programming";
Console.WriteLine(word.Length);
Console.WriteLine(word[0]);
Console.WriteLine(word[word.Length - 1]);
Console.WriteLine(word[^1]);       // من النهاية: آخر حرف
```

```text output
11
P
g
g
```

## أهم دوال النصوص

```csharp run
string s = "  Hello, C# World  ";
Console.WriteLine($"[{s.Trim()}]");          // حذف المسافات من الطرفين
Console.WriteLine(s.Trim().ToUpper());       // أحرف كبيرة
Console.WriteLine(s.Trim().ToLower());       // أحرف صغيرة
Console.WriteLine(s.Contains("C#"));         // هل يحتوي؟
Console.WriteLine(s.Trim().StartsWith("Hello"));
Console.WriteLine(s.Trim().EndsWith("World"));
Console.WriteLine(s.IndexOf("World"));       // أين يبدأ؟
Console.WriteLine(s.Replace("World", "Egypt").Trim());
```

```text output
[Hello, C# World]
HELLO, C# WORLD
hello, c# world
True
True
True
12
Hello, C# Egypt
```

| الدالة | وظيفتها |
|---|---|
| `Trim()` | تحذف المسافات من الطرفين |
| `ToUpper()` / `ToLower()` | أحرف كبيرة / صغيرة |
| `Contains(x)` | هل يحتوي النص على `x`؟ |
| `StartsWith(x)` / `EndsWith(x)` | هل يبدأ / ينتهي بـ `x`؟ |
| `IndexOf(x)` | موضع أول ظهور (أو `-1`) |
| `Replace(a, b)` | يستبدل كل `a` بـ `b` |
| `Substring(i, n)` | جزء طوله `n` يبدأ من `i` |
| `Split(c)` | يقسم النص إلى مصفوفة |

## اقتطاع جزء: `Substring`

```csharp run
string date = "2026-11-21";
string year = date.Substring(0, 4);
string month = date.Substring(5, 2);
string day = date.Substring(8);       // من 8 حتى النهاية
Console.WriteLine($"اليوم {day} الشهر {month} السنة {year}");
```

```text output
اليوم 21 الشهر 11 السنة 2026
```

## التقسيم والدمج: `Split` و`Join`

```csharp run
string line = "أحمد,25,القاهرة,مهندس";
string[] parts = line.Split(',');
Console.WriteLine($"الاسم: {parts[0]}");
Console.WriteLine($"العمر: {parts[1]}");
Console.WriteLine($"عدد الحقول: {parts.Length}");

string joined = string.Join(" | ", parts);
Console.WriteLine(joined);
```

```text output
الاسم: أحمد
العمر: 25
عدد الحقول: 4
أحمد | 25 | القاهرة | مهندس
```

## مقارنة النصوص

```csharp run
string a = "csharp";
string b = "CSharp";
Console.WriteLine(a == b);
Console.WriteLine(a.Equals(b, StringComparison.OrdinalIgnoreCase));
Console.WriteLine(string.Compare("apple", "banana") < 0);
Console.WriteLine(string.IsNullOrWhiteSpace("   "));
```

```text output
False
True
True
True
```

- `==` تقارن حرفًا حرفًا مع مراعاة حالة الأحرف.
- `StringComparison.OrdinalIgnoreCase` تتجاهل الفرق بين الكبير والصغير.
- `string.IsNullOrWhiteSpace` مفيدة جدًا للتأكد من أن المستخدم كتب شيئًا.

## المرور على الحروف

```csharp run
string text = "Hello World 2026";
int letters = 0, digits = 0, spaces = 0;
foreach (char c in text)
{
    if (char.IsLetter(c)) letters++;
    else if (char.IsDigit(c)) digits++;
    else if (char.IsWhiteSpace(c)) spaces++;
}
Console.WriteLine($"حروف {letters}، أرقام {digits}، مسافات {spaces}");
```

```text output
حروف 10، أرقام 4، مسافات 2
```

## عكس نص

```csharp run
string word = "level";
char[] chars = word.ToCharArray();
Array.Reverse(chars);
string reversed = new string(chars);
Console.WriteLine(reversed);
Console.WriteLine(word == reversed ? "متناظر (palindrome)" : "غير متناظر");
```

```text output
level
متناظر (palindrome)
```

## `StringBuilder`: بناء نص كبير بسرعة

لأن النص لا يتغير، فكل `+=` في حلقة تنشئ نصًا جديدًا كاملًا. مع آلاف التكرارات يصبح هذا بطيئًا. الحل `StringBuilder`:

```csharp run
using System.Text;

var sb = new StringBuilder();
for (int i = 1; i <= 5; i++)
{
    sb.Append(i);
    if (i < 5)
        sb.Append(" - ");
}
sb.AppendLine();
sb.Append("انتهى");
Console.WriteLine(sb.ToString());
```

```text output
1 - 2 - 3 - 4 - 5
انتهى
```

## التنسيق المتقدم

```csharp run
string name = "Laptop";
double price = 15499.5;
int qty = 3;
Console.WriteLine($"|{name,-10}|{qty,5}|{price,12:N2}|");
Console.WriteLine(string.Format("{0} x {1} = {2:F1}", qty, price, qty * price));
Console.WriteLine("7".PadLeft(3, '0'));
```

```text output
|Laptop    |    3|   15,499.50|
3 x 15499.5 = 46498.5
007
```

- `{x,-10}` محاذاة لليسار في 10 خانات، و`{x,5}` محاذاة لليمين.
- `PadLeft(3, '0')` يكمل النص من اليسار بالأصفار حتى يصبح طوله 3.

## أخطاء شائعة

- **نسيان أن الدوال ترجع نصًا جديدًا:** `s.ToUpper();` وحدها لا تغير `s`. اكتب `s = s.ToUpper();`.
- **`Substring` خارج الحدود:** `"abc".Substring(2, 5)` توقف البرنامج بـ `ArgumentOutOfRangeException`.
- **المقارنة بـ `==` بين نصين مختلفين في حالة الأحرف** تعطي `False`. استخدم `OrdinalIgnoreCase` عند الحاجة.

## تمارين

### التمرين 1

اقرأ جملة واطبع عدد كلماتها (الكلمات مفصولة بمسافة واحدة).

```csharp exercise
string sentence = Console.ReadLine();
// اطبع: عدد الكلمات: 5
```

```csharp solution
string sentence = Console.ReadLine();
string[] words = sentence.Trim().Split(' ');
Console.WriteLine($"عدد الكلمات: {words.Length}");
```

```text input
أنا أحب تعلم لغة C#
```

```text output
عدد الكلمات: 5
```

### التمرين 2

اكتب دالة `Capitalize` تجعل أول حرف من كل كلمة إنجليزية كبيرًا.

```csharp exercise
static string Capitalize(string s)
{
    return s;
}

Console.WriteLine(Capitalize("hello world from csharp"));
```

```csharp solution
static string Capitalize(string s)
{
    string[] words = s.Split(' ');
    for (int i = 0; i < words.Length; i++)
        if (words[i].Length > 0)
            words[i] = char.ToUpper(words[i][0]) + words[i].Substring(1);
    return string.Join(" ", words);
}

Console.WriteLine(Capitalize("hello world from csharp"));
```

```text output
Hello World From Csharp
```

### التمرين 3

اقرأ بريدًا إلكترونيًا، واطبع اسم المستخدم (قبل `@`) واسم النطاق (بعدها). وإذا لم يحتوِ على `@` اطبع `بريد غير صحيح`.

```csharp exercise
string email = Console.ReadLine();
// المستخدم: sara
// النطاق: example.com
```

```csharp solution
string email = Console.ReadLine();
int at = email.IndexOf('@');
if (at <= 0)
{
    Console.WriteLine("بريد غير صحيح");
}
else
{
    Console.WriteLine($"المستخدم: {email.Substring(0, at)}");
    Console.WriteLine($"النطاق: {email.Substring(at + 1)}");
}
```

```text input
sara@example.com
```

```text output
المستخدم: sara
النطاق: example.com
```

## اختبر نفسك

```quiz
{"question": "ماذا يطبع: string s = \"abc\"; s.ToUpper(); Console.WriteLine(s);؟", "choices": ["ABC", "abc", "Abc", "خطأ"], "answer": 1, "explanation": "ToUpper ترجع نصًا جديدًا ولا تغير s، لأن النصوص غير قابلة للتعديل."}
```

```quiz
{"question": "ما ناتج \"Hello\".IndexOf(\"z\")؟", "choices": ["0", "-1", "5", "خطأ"], "answer": 1, "explanation": "IndexOf ترجع -1 عندما لا تجد النص."}
```

```quiz
{"question": "متى نستخدم StringBuilder؟", "choices": ["لمقارنة نصين", "عند بناء نص كبير بإضافات كثيرة في حلقة", "لقراءة الملفات", "لتحويل الأرقام"], "answer": 1, "explanation": "StringBuilder يعدّل في نفس الذاكرة بدل إنشاء نص جديد مع كل إضافة."}
```

## الخلاصة

- `Length` والفهرسة `s[i]` و`s[^1]`.
- `Trim` و`ToUpper` و`Contains` و`IndexOf` و`Replace` و`Substring` و`Split` و`string.Join`.
- النصوص غير قابلة للتعديل: الدوال ترجع نصًا جديدًا.
- `StringBuilder` لبناء النصوص الكبيرة، و`{x,-10:N2}` للتنسيق.
