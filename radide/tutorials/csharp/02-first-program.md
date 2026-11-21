# الدرس 2: برنامجك الأول سطرًا سطرًا

في الدرس السابق كتبنا سطرًا واحدًا فطبع رسالة. اليوم سنرى الشكل **الكامل** لبرنامج C#، ونفهم كل كلمة فيه، ونتعلم التعليقات ورموز الهروب ودمج القيم داخل النصوص.

## الشكل الكامل للبرنامج

السطر الواحد `Console.WriteLine("Hello");` الذي كتبناه يسمى **تعليمات المستوى الأعلى** (top-level statements)، وهو اختصار أضيف في الإصدارات الحديثة من C#. أما الشكل الكامل التقليدي فهو هذا، وستراه في كل الكتب والمشاريع القديمة:

```csharp run
using System;

namespace FirstApp
{
    class Program
    {
        static void Main()
        {
            Console.WriteLine("Hello, World!");
        }
    }
}
```

```text output
Hello, World!
```

## الشرح سطرًا سطرًا

### `using System;`

يقول للمترجم: «سأستخدم أدوات من **فضاء الأسماء** `System`». وفضاء الأسماء (namespace) مثل **مجلد** يجمع أدوات متقاربة. الأداة `Console` موجودة داخل `System`، فبدون هذا السطر كنا سنكتب `System.Console.WriteLine`.

> **ملحوظة:** مشاريع .NET الحديثة تفعّل خيارًا اسمه `ImplicitUsings`، فتضيف `using System;` وأشهر فضاءات الأسماء تلقائيًا. لذلك عمل مثال الدرس الأول دون أن نكتبه.

### `namespace FirstApp`

يضع الكود الذي كتبناه نحن داخل فضاء أسماء اسمه `FirstApp`، حتى لا تتعارض أسماؤنا مع أسماء الآخرين.

### `class Program`

في C# كل الكود يعيش داخل **صنف** (class). الصنف مثل **غرفة** في بيت البرنامج. سنتعلم الأصناف بالتفصيل في الدرس العاشر.

### `static void Main()`

هذه هي **نقطة البداية**: أول دالة تُنفذ عندما يبدأ البرنامج. يجب أن يكون اسمها `Main` بحرف M كبير.

- `static` تعني أنها تخص الصنف نفسه، ولا تحتاج إلى إنشاء كائن منه.
- `void` تعني أنها لا ترجع قيمة.
- `()` تعني أنها دالة. سنفهم الدوال في الدرس السابع.

### الأقواس المعقوصة `{ }`

كل زوج `{ }` يحدد **كتلة** (block): جسم الصنف، وجسم الدالة... تمامًا مثل الأقواس في الرياضيات.

### `Console.WriteLine("Hello, World!");`

- `Console` هي **نافذة الكونسول** (الشاشة النصية).
- `.WriteLine` دالة داخلها تكتب سطرًا ثم تنزل سطرًا جديدًا.
- `"Hello, World!"` نص (string) بين علامتي تنصيص.
- `;` تنهي التعليمة.

## `Write` و`WriteLine`

```csharp run
Console.Write("واحد ");
Console.Write("اثنان ");
Console.WriteLine("ثلاثة");
Console.WriteLine("سطر جديد");
```

```text output
واحد اثنان ثلاثة
سطر جديد
```

`Console.Write` تكتب **دون** النزول إلى سطر جديد، و`Console.WriteLine` تكتب ثم تنزل.

## رموز الهروب (Escape Sequences)

بعض الحروف لا نستطيع كتابتها مباشرة داخل النص، فنكتبها بشرطة مائلة عكسية `\`:

```csharp run
Console.WriteLine("السطر الأول\nالسطر الثاني");
Console.WriteLine("الاسم:\tسارة");
Console.WriteLine("قال: \"مرحبًا\"");
Console.WriteLine("C:\\Projects\\app");
Console.WriteLine(@"C:\Projects\app");
```

```text output
السطر الأول
السطر الثاني
الاسم:	سارة
قال: "مرحبًا"
C:\Projects\app
C:\Projects\app
```

| الرمز | معناه |
|---|---|
| `\n` | سطر جديد |
| `\t` | مسافة جدولة (Tab) |
| `\"` | علامة تنصيص داخل النص |
| `\\` | شرطة مائلة عكسية واحدة |

والعلامة `@` قبل النص تجعله **نصًا حرفيًا** (verbatim string): تُكتب فيه الشرطة `\` كما هي، وهذا مريح جدًا لمسارات الملفات.

## دمج القيم داخل النص: `$"..."`

نضع `$` قبل النص، ثم نكتب أي قيمة بين قوسين `{ }`، وهذا يسمى **استيفاء النصوص** (string interpolation):

```csharp run
string name = "ليلى";
int age = 12;
Console.WriteLine($"اسمي {name} وعمري {age} سنة");
Console.WriteLine($"بعد 5 سنوات سيكون عمري {age + 5}");
```

```text output
اسمي ليلى وعمري 12 سنة
بعد 5 سنوات سيكون عمري 17
```

لا تقلق من `string` و`int` الآن، فهي **متغيرات** وسنشرحها في الدرس القادم.

## التعليقات (Comments)

التعليق كلام للبشر، والمترجم يتجاهله تمامًا:

```csharp run
// تعليق من سطر واحد

/*
   تعليق
   من عدة أسطر
*/

Console.WriteLine("التعليقات لا تظهر في الناتج"); // تعليق في آخر السطر
// Console.WriteLine("هذا السطر معطّل");
```

```text output
التعليقات لا تظهر في الناتج
```

> **نصيحة:** في محرر الـ IDE اختر عدة أسطر واضغط `Ctrl+/` لتحويلها إلى تعليقات أو إرجاعها.

## ما هو الملف `RadUtf8.cs`؟

عندما يطبع برنامج كونسول نصًا عربيًا وناتجه يذهب إلى نافذة أخرى (مثل Output في الـ IDE)، تستخدم .NET في ويندوز ترميزًا قديمًا افتراضيًا، فتظهر الحروف العربية علامات `?`. الملف `RadUtf8.cs` في مشاريع الدروس يضبط الترميز على **UTF-8** قبل أن يبدأ `Main`. وفي برامجك الخاصة يكفيك أن تكتب هذا السطر في أول البرنامج:

```csharp
Console.OutputEncoding = System.Text.Encoding.UTF8;
```

## أخطاء شائعة

### نسيان علامة التنصيص

<!-- compile-error -->
```csharp
Console.WriteLine("مرحبا);
```

```text
Program.cs(1,19): error CS1010: Newline in constant
```

**المعنى:** «سطر جديد داخل ثابت نصي»، أي أن النص لم يُغلق قبل نهاية السطر. أضف `"` قبل القوس.

### كتابة `Writeline` بدل `WriteLine`

<!-- compile-error -->
```csharp
Console.Writeline("مرحبا");
```

```text
Program.cs(1,9): error CS0117: 'Console' does not contain a definition for 'Writeline'
```

**المعنى:** «الصنف `Console` لا يحتوي على شيء اسمه `Writeline`». تذكر أن C# حساسة لحالة الأحرف.

> **نصيحة:** رقمان بين القوسين `(1,19)` معناهما: السطر 1، العمود 19. انقر مرتين على رسالة الخطأ في نافذة Output لتنتقل إلى مكانه.

## تمارين

### التمرين 1

اطبع البطاقة التالية باستخدام `\t` بين العنوان والقيمة:

```csharp exercise
// الاسم:	سارة
// المادة:	C#
// الدرجة:	95
```

```csharp solution
Console.WriteLine("الاسم:\tسارة");
Console.WriteLine("المادة:\tC#");
Console.WriteLine("الدرجة:\t95");
```

```text output
الاسم:	سارة
المادة:	C#
الدرجة:	95
```

### التمرين 2

لديك المتغيران `city` و`year`. اطبع باستخدام `$"..."` الجملة: `أعيش في الإسكندرية منذ 2015`.

```csharp exercise
string city = "الإسكندرية";
int year = 2015;
// اطبع الجملة هنا
```

```csharp solution
string city = "الإسكندرية";
int year = 2015;
Console.WriteLine($"أعيش في {city} منذ {year}");
```

```text output
أعيش في الإسكندرية منذ 2015
```

### التمرين 3

اكتب البرنامج بالشكل الكامل (`namespace` و`class Program` و`static void Main`) واجعله يطبع مثلثًا من النجوم بثلاثة أسطر باستخدام `Console.Write` و`\n`.

```csharp exercise
namespace Stars
{
    class Program
    {
        static void Main()
        {
            // *
            // **
            // ***
        }
    }
}
```

```csharp solution
namespace Stars
{
    class Program
    {
        static void Main()
        {
            Console.Write("*\n**\n***\n");
        }
    }
}
```

```text output
*
**
***
```

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي يبدأ منها تنفيذ برنامج C# بالشكل الكامل؟", "choices": ["Start", "Main", "main", "Program"], "answer": 1, "explanation": "نقطة البداية هي static void Main بحرف M كبير."}
```

```quiz
{"question": "ما الفرق بين Console.Write وConsole.WriteLine؟", "choices": ["لا فرق", "WriteLine تنزل سطرًا جديدًا بعد الكتابة وWrite لا تنزل", "Write أسرع فقط", "WriteLine للأرقام فقط"], "answer": 1, "explanation": "Write تكتب في نفس السطر، وWriteLine تكتب ثم تنزل إلى سطر جديد."}
```

```quiz
{"question": "ماذا يطبع: Console.WriteLine($\"{2 + 3}\");؟", "choices": ["{2 + 3}", "2 + 3", "5", "خطأ ترجمة"], "answer": 2, "explanation": "داخل نص يبدأ بـ $ يُحسب ما بين القوسين { } ويوضع ناتجه في النص."}
```

```quiz
{"question": "لماذا نكتب @ قبل النص في @\"C:\\Projects\"؟", "choices": ["لتسريع البرنامج", "لكي تُكتب الشرطة المائلة العكسية كما هي دون رموز هروب", "لطباعة النص بخط عريض", "لجعله تعليقًا"], "answer": 1, "explanation": "النص الحرفي (verbatim) يعامل الشرطة \\ كحرف عادي."}
```

## الخلاصة

- الشكل الكامل: `namespace` ثم `class Program` ثم `static void Main()`، والشكل المختصر يكتب التعليمات مباشرة.
- `Console.Write` و`Console.WriteLine` للطباعة، ورموز الهروب مثل `\n` و`\t`.
- `$"...{قيمة}..."` لدمج القيم في النص، و`@"..."` للنصوص الحرفية.
- التعليقات `//` و`/* */` يتجاهلها المترجم.
