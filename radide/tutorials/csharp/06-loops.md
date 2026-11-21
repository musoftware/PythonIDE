# الدرس 6: حلقات التكرار

تخيّل أنك تريد طباعة الأرقام من 1 إلى 1000. هل ستكتب ألف سطر `Console.WriteLine`؟ بالطبع لا! **حلقة التكرار** (loop) تكرر مجموعة من التعليمات ما دام شرط معين صحيحًا.

> **تشبيه:** حلقة التكرار مثل **عدّاد اللفّات** في سباق الجري: العدّاء يجري لفّة، والعدّاد يزيد واحدًا، ويستمر حتى يصل العدد المطلوب.

## حلقة `for`

نستخدمها عندما نعرف **عدد المرات** مسبقًا:

```csharp run
for (int i = 1; i <= 5; i++)
{
    Console.WriteLine($"اللفّة رقم {i}");
}
```

```text output
اللفّة رقم 1
اللفّة رقم 2
اللفّة رقم 3
اللفّة رقم 4
اللفّة رقم 5
```

السطر `for (int i = 1; i <= 5; i++)` له ثلاثة أجزاء مفصولة بـ `;`:

1. **البداية** `int i = 1`: تُنفذ مرة واحدة في الأول.
2. **الشرط** `i <= 5`: يُفحص قبل كل لفّة، وإذا صار `false` تتوقف الحلقة.
3. **الخطوة** `i++`: تُنفذ بعد كل لفّة.

### العد التنازلي وبخطوات مختلفة

```csharp run
for (int i = 10; i >= 0; i -= 2)
    Console.Write(i + " ");
Console.WriteLine();
```

```text output
10 8 6 4 2 0
```

### جمع الأرقام

```csharp run
int sum = 0;
for (int i = 1; i <= 100; i++)
    sum += i;
Console.WriteLine($"مجموع الأرقام من 1 إلى 100 = {sum}");
```

```text output
مجموع الأرقام من 1 إلى 100 = 5050
```

المتغير `sum` يسمى **مُراكِم** (accumulator): نبدأ به من صفر ونضيف إليه في كل لفّة.

## حلقة `while`

نستخدمها عندما **لا نعرف** عدد المرات، بل نعرف شرط الاستمرار:

```csharp run
int money = 100;
int months = 0;
while (money < 200)
{
    money += money / 10;   // ربح 10% كل شهر
    months++;
}
Console.WriteLine($"بعد {months} شهرًا صار المبلغ {money}");
```

```text output
بعد 8 شهرًا صار المبلغ 212
```

## حلقة `do ... while`

مثل `while` لكنها تُنفذ **مرة واحدة على الأقل**، لأن الشرط يُفحص في النهاية. مناسبة جدًا لقوائم الاختيار وطلب الإدخال حتى يكون صحيحًا:

```csharp run
int number;
do
{
    Console.Write("أدخل رقمًا من 1 إلى 10: ");
    number = int.Parse(Console.ReadLine());
} while (number < 1 || number > 10);
Console.WriteLine();
Console.WriteLine($"شكرًا، اخترت {number}");
```

```text input
15
0
7
```

```text output
أدخل رقمًا من 1 إلى 10: أدخل رقمًا من 1 إلى 10: أدخل رقمًا من 1 إلى 10: 
شكرًا، اخترت 7
```

## `break` و`continue`

- `break`: اخرج من الحلقة فورًا.
- `continue`: اترك بقية هذه اللفّة وانتقل إلى اللفّة التالية.

```csharp run
for (int i = 1; i <= 10; i++)
{
    if (i % 3 == 0)
        continue;          // تخطَّ مضاعفات 3
    if (i > 8)
        break;             // توقف بعد 8
    Console.Write(i + " ");
}
Console.WriteLine();
```

```text output
1 2 4 5 7 8
```

## الحلقات المتداخلة

حلقة داخل حلقة: لكل لفّة من الخارجية تكتمل الداخلية كلها.

```csharp run
for (int row = 1; row <= 4; row++)
{
    for (int col = 1; col <= row; col++)
        Console.Write("*");
    Console.WriteLine();
}
```

```text output
*
**
***
****
```

### جدول الضرب

```csharp run
for (int i = 1; i <= 3; i++)
{
    for (int j = 1; j <= 5; j++)
        Console.Write($"{i * j,4}");
    Console.WriteLine();
}
```

```text output
   1   2   3   4   5
   2   4   6   8  10
   3   6   9  12  15
```

`{i * j,4}` تطبع الرقم في 4 خانات، فتصطف الأعمدة.

## حلقة `foreach`

تمر على كل عنصر في مجموعة. سنستخدمها كثيرًا مع المصفوفات والقوائم في الدرس الثامن، وهذا مثال على حروف نص:

```csharp run
string word = "C#.NET";
int letters = 0;
foreach (char c in word)
{
    if (char.IsLetter(c))
        letters++;
}
Console.WriteLine($"عدد الحروف الإنجليزية: {letters}");
```

```text output
عدد الحروف الإنجليزية: 4
```

## أخطاء شائعة

### الحلقة اللانهائية

```csharp
int i = 1;
while (i <= 5)
{
    Console.WriteLine(i);
    // نسينا i++ فالشرط لن يصبح false أبدًا!
}
```

إذا علق برنامجك، اضغط **Shift+F5** لإيقافه. وعند «تحقق» توقف الـ IDE البرنامج بعد مهلة وتخبرك.

### الخطأ بفارق واحد (off-by-one)

`for (int i = 0; i <= 10; i++)` تتكرر **11** مرة وليس 10. انتبه للفرق بين `<` و`<=`.

### تعريف متغير الحلقة واستخدامه خارجها

المتغير `i` المعرّف داخل `for` لا يوجد خارجها. إذا احتجت قيمته بعد الحلقة فعرّفه قبلها.

## تمارين

### التمرين 1

اطبع جدول ضرب العدد 7 من 1 إلى 5 بالشكل `7 x 1 = 7`.

```csharp exercise
// 7 x 1 = 7
// ...
// 7 x 5 = 35
```

```csharp solution
for (int i = 1; i <= 5; i++)
    Console.WriteLine($"7 x {i} = {7 * i}");
```

```text output
7 x 1 = 7
7 x 2 = 14
7 x 3 = 21
7 x 4 = 28
7 x 5 = 35
```

### التمرين 2

اقرأ عددًا صحيحًا موجبًا `n` واحسب **مضروبه** `n!` (1 × 2 × ... × n). استخدم النوع `long`.

```csharp exercise
int n = int.Parse(Console.ReadLine());
// اطبع: 10! = 3628800
```

```csharp solution
int n = int.Parse(Console.ReadLine());
long fact = 1;
for (int i = 2; i <= n; i++)
    fact *= i;
Console.WriteLine($"{n}! = {fact}");
```

```text input
10
```

```text output
10! = 3628800
```

### التمرين 3

اقرأ أرقامًا حتى يكتب المستخدم `0`، ثم اطبع مجموعها وعددها (دون الصفر).

```csharp exercise
// اقرأ حتى 0 ثم اطبع:
// العدد: ...
// المجموع: ...
```

```csharp solution
int count = 0, sum = 0;
while (true)
{
    int x = int.Parse(Console.ReadLine());
    if (x == 0)
        break;
    count++;
    sum += x;
}
Console.WriteLine($"العدد: {count}");
Console.WriteLine($"المجموع: {sum}");
```

```text input
5
12
3
0
```

```text output
العدد: 3
المجموع: 20
```

## اختبر نفسك

```quiz
{"question": "كم مرة تتكرر الحلقة for (int i = 0; i < 5; i++)؟", "choices": ["4", "5", "6", "لا نهائية"], "answer": 1, "explanation": "تبدأ i من 0 وتنتهي عند 4: أي 0 و1 و2 و3 و4، خمس مرات."}
```

```quiz
{"question": "ما الذي يميز do...while عن while؟", "choices": ["أسرع", "تُنفذ مرة واحدة على الأقل لأن الشرط يُفحص في النهاية", "لا تحتاج شرطًا", "تعمل مع النصوص فقط"], "answer": 1, "explanation": "في do...while يُنفذ الجسم أولًا ثم يُفحص الشرط."}
```

```quiz
{"question": "ماذا تفعل continue داخل الحلقة؟", "choices": ["تنهي البرنامج", "تخرج من الحلقة", "تتخطى بقية اللفّة الحالية وتنتقل إلى التالية", "تعيد الحلقة من البداية"], "answer": 2, "explanation": "continue تقفز إلى اللفّة التالية مباشرة، أما break فتخرج من الحلقة."}
```

## الخلاصة

- `for` عندما نعرف عدد المرات، و`while` عندما نعرف شرط الاستمرار، و`do...while` للتنفيذ مرة على الأقل.
- `foreach` للمرور على عناصر مجموعة.
- `break` للخروج، و`continue` للانتقال إلى اللفّة التالية.
- احذر الحلقة اللانهائية والخطأ بفارق واحد.
