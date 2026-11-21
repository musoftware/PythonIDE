# الدرس 12: الاستثناءات والملفات

البرامج الحقيقية تواجه مواقف غير متوقعة: المستخدم يكتب حروفًا بدل رقم، أو الملف المطلوب غير موجود، أو القسمة على صفر. بدون استعداد، **يتوقف** البرنامج فجأة. **الاستثناءات** (exceptions) هي طريقة C# للتعامل مع هذه المواقف بأدب.

> **تشبيه:** الاستثناء مثل **جرس الإنذار** في المبنى: عندما يحدث شيء خطير يرن الجرس، وينتقل التنفيذ فورًا إلى «فريق الطوارئ» (`catch`) الذي يعرف ماذا يفعل. وإذا لم يوجد فريق طوارئ، يُخلى المبنى كله (يتوقف البرنامج).

## `try` و`catch`

```csharp run
string[] inputs = { "25", "abc", "7" };
foreach (string text in inputs)
{
    try
    {
        int n = int.Parse(text);
        Console.WriteLine($"ضعف {n} = {n * 2}");
    }
    catch (FormatException)
    {
        Console.WriteLine($"«{text}» ليس رقمًا");
    }
}
Console.WriteLine("البرنامج مستمر");
```

```text output
ضعف 25 = 50
«abc» ليس رقمًا
ضعف 7 = 14
البرنامج مستمر
```

- الكود الذي قد يفشل يوضع داخل `try`.
- إذا حدث استثناء، يقفز التنفيذ فورًا إلى `catch` المناسب، ثم يكمل بعده.

## أنواع الاستثناءات الشائعة

| الاستثناء | متى يحدث |
|---|---|
| `FormatException` | تحويل نص غير صالح إلى رقم |
| `DivideByZeroException` | قسمة عدد صحيح على صفر |
| `IndexOutOfRangeException` | فهرس خارج حدود المصفوفة |
| `NullReferenceException` | استخدام كائن قيمته `null` |
| `FileNotFoundException` | فتح ملف غير موجود |
| `InvalidOperationException` | عملية غير مسموحة في الحالة الحالية |

### عدة `catch` والرسالة `Message`

```csharp run
int[] data = { 10, 20, 30 };
int[] indexes = { 1, 5 };
foreach (int i in indexes)
{
    try
    {
        int divisor = i - 1;
        Console.WriteLine(data[i] / divisor);
    }
    catch (DivideByZeroException)
    {
        Console.WriteLine("قسمة على صفر!");
    }
    catch (IndexOutOfRangeException ex)
    {
        Console.WriteLine($"خطأ في الفهرس: {ex.Message}");
    }
}
```

```text output
قسمة على صفر!
خطأ في الفهرس: Index was outside the bounds of the array.
```

## `finally`: يعمل دائمًا

```csharp run
try
{
    Console.WriteLine("فتح الاتصال");
    throw new InvalidOperationException("انقطع الاتصال");
}
catch (Exception ex)
{
    Console.WriteLine($"حدث خطأ: {ex.Message}");
}
finally
{
    Console.WriteLine("إغلاق الاتصال");
}
```

```text output
فتح الاتصال
حدث خطأ: انقطع الاتصال
إغلاق الاتصال
```

كتلة `finally` تعمل سواء حدث استثناء أم لا، ومكانها المناسب لتحرير الموارد (إغلاق الملفات والاتصالات).

## رمي استثناء بنفسك: `throw`

```csharp run
static double SquareRoot(double x)
{
    if (x < 0)
        throw new ArgumentException("لا يوجد جذر حقيقي لعدد سالب");
    return Math.Sqrt(x);
}

try
{
    Console.WriteLine(SquareRoot(49));
    Console.WriteLine(SquareRoot(-4));
}
catch (ArgumentException ex)
{
    Console.WriteLine(ex.Message);
}
```

```text output
7
لا يوجد جذر حقيقي لعدد سالب
```

## التعامل مع الملفات

الصنف `File` في فضاء الأسماء `System.IO` يقرأ ويكتب الملفات بسطر واحد:

```csharp run
string path = "notes.txt";
File.WriteAllText(path, "السطر الأول\n");
File.AppendAllText(path, "السطر الثاني\n");

string all = File.ReadAllText(path);
Console.Write(all);
Console.WriteLine($"الملف موجود؟ {File.Exists(path)}");
```

```text output
السطر الأول
السطر الثاني
الملف موجود؟ True
```

- `WriteAllText` تنشئ الملف (أو تمسح محتواه القديم) وتكتب فيه.
- `AppendAllText` تضيف في نهايته.
- الملفات تُحفظ بترميز **UTF-8** افتراضيًا، فالعربية تعمل دون مشاكل.
- المسار `notes.txt` نسبي: الملف يُنشأ في **مجلد التشغيل** (مجلد المشروع عادة).

### القراءة والكتابة سطرًا سطرًا

```csharp run
string[] students = { "أمل,90", "باسم,75", "جنى,88" };
File.WriteAllLines("grades.csv", students);

int total = 0;
foreach (string line in File.ReadAllLines("grades.csv"))
{
    string[] parts = line.Split(',');
    int grade = int.Parse(parts[1]);
    total += grade;
    Console.WriteLine($"{parts[0]}: {grade}");
}
Console.WriteLine($"المتوسط: {total / 3.0:F1}");
```

```text output
أمل: 90
باسم: 75
جنى: 88
المتوسط: 84.3
```

### قراءة ملف غير موجود بأمان

```csharp run
try
{
    string text = File.ReadAllText("missing-file.txt");
    Console.WriteLine(text);
}
catch (FileNotFoundException)
{
    Console.WriteLine("الملف غير موجود، سننشئ ملفًا جديدًا");
}
```

```text output
الملف غير موجود، سننشئ ملفًا جديدًا
```

### `using` مع `StreamWriter`

للملفات الكبيرة نكتب سطرًا سطرًا بـ `StreamWriter`. والكلمة `using` تضمن إغلاق الملف تلقائيًا في النهاية حتى لو حدث استثناء:

```csharp run
using (var writer = new StreamWriter("squares.txt"))
{
    for (int i = 1; i <= 4; i++)
        writer.WriteLine($"{i} x {i} = {i * i}");
}
foreach (string line in File.ReadLines("squares.txt"))
    Console.WriteLine(line);
```

```text output
1 x 1 = 1
2 x 2 = 4
3 x 3 = 9
4 x 4 = 16
```

## أخطاء شائعة

- **`catch (Exception)` فارغ يبتلع كل الأخطاء:** لا تكتب `catch { }` بدون أي شيء، فتخفي المشكلة بدل حلها. اطبع الرسالة على الأقل.
- **نسيان إغلاق الملف:** استخدم `using` أو دوال `File.*` الجاهزة التي تغلق الملف بنفسها.
- **مسارات بشرطة واحدة:** `"C:\new\file.txt"` فيها `\n` و`\f` كرموز هروب! اكتب `@"C:\new\file.txt"`.

## تمارين

### التمرين 1

اكتب دالة `SafeDivide(int a, int b)` ترجع ناتج القسمة، وإذا كان `b` صفرًا ترجع `0` وتطبع `لا يمكن القسمة على صفر` باستخدام `try/catch`.

```csharp exercise
static int SafeDivide(int a, int b)
{
    return a / b;
}

Console.WriteLine(SafeDivide(20, 4));
Console.WriteLine(SafeDivide(5, 0));
```

```csharp solution
static int SafeDivide(int a, int b)
{
    try
    {
        return a / b;
    }
    catch (DivideByZeroException)
    {
        Console.WriteLine("لا يمكن القسمة على صفر");
        return 0;
    }
}

Console.WriteLine(SafeDivide(20, 4));
Console.WriteLine(SafeDivide(5, 0));
```

```text output
5
لا يمكن القسمة على صفر
0
```

### التمرين 2

اكتب الأسماء الثلاثة في ملف `names.txt` (كل اسم في سطر)، ثم اقرأ الملف واطبع عدد أسطره وأطول اسم فيه.

```csharp exercise
string[] names = { "Omar", "Fatima", "Ziad" };
// عدد الأسطر: 3
// أطول اسم: Fatima
```

```csharp solution
string[] names = { "Omar", "Fatima", "Ziad" };
File.WriteAllLines("names.txt", names);
string[] lines = File.ReadAllLines("names.txt");
string longest = lines[0];
foreach (string n in lines)
    if (n.Length > longest.Length)
        longest = n;
Console.WriteLine($"عدد الأسطر: {lines.Length}");
Console.WriteLine($"أطول اسم: {longest}");
```

```text output
عدد الأسطر: 3
أطول اسم: Fatima
```

## اختبر نفسك

```quiz
{"question": "متى تُنفذ كتلة finally؟", "choices": ["فقط عند حدوث استثناء", "فقط إذا لم يحدث استثناء", "دائمًا سواء حدث استثناء أم لا", "لا تُنفذ أبدًا"], "answer": 2, "explanation": "finally تعمل دائمًا، ولذلك نضع فيها كود تحرير الموارد."}
```

```quiz
{"question": "أي استثناء يحدث عند int.Parse(\"abc\")؟", "choices": ["DivideByZeroException", "FormatException", "FileNotFoundException", "NullReferenceException"], "answer": 1, "explanation": "النص لا يمثل رقمًا بالصيغة الصحيحة، فيحدث FormatException."}
```

```quiz
{"question": "ما فائدة using (var w = new StreamWriter(...)) { ... }؟", "choices": ["تسريع الكتابة", "إغلاق الملف تلقائيًا في نهاية الكتلة حتى لو حدث خطأ", "تشفير الملف", "قراءة الملف"], "answer": 1, "explanation": "using تستدعي Dispose في النهاية فيُغلق الملف دائمًا."}
```

## الخلاصة

- `try` / `catch` / `finally` للتعامل مع الأخطاء دون توقف البرنامج، و`throw` لرمي استثناء.
- `ex.Message` يعطي وصف الخطأ.
- `File.WriteAllText` و`AppendAllText` و`ReadAllText` و`WriteAllLines` و`ReadAllLines` للملفات.
- `using` يغلق الملف تلقائيًا.
