# الدرس 15: حزم NuGet وتصحيح الأخطاء بـ netcoredbg

اليوم نتعلم مهارتين يستخدمهما كل مبرمج C# محترف يوميًا: **إضافة مكتبات جاهزة** من مستودع NuGet بدل كتابة كل شيء بنفسك، و**تصحيح الأخطاء** (debugging): إيقاف البرنامج عند سطر معين ومراقبة قيم المتغيرات خطوة بخطوة.

## الجزء الأول: حزم NuGet

**NuGet** (تُنطق «نيو جت») هو مستودع المكتبات الرسمي لـ .NET، وفيه مئات الآلاف من **الحزم** (packages) المجانية: قراءة ملفات Excel، وإرسال البريد، والتعامل مع JSON، وقواعد البيانات...

> **تشبيه:** NuGet مثل **متجر التطبيقات** في هاتفك: بدل أن تبرمج آلة حاسبة بنفسك، تنزّلها جاهزة. والحزمة تُنزَّل مرة واحدة إلى ذاكرة مؤقتة على جهازك (`%USERPROFILE%\.nuget\packages`)، ثم تستخدمها كل مشاريعك.

### إضافة حزمة إلى مشروع رسومي (GUI Bridge)

1. افتح مشروعك (مثلًا مشروع الدرس 13).
2. من القائمة: **Project > Manage Packages...** (مشروع > إدارة الحزم...).
3. اكتب اسم الحزمة في مربع البحث، مثل `Newtonsoft.Json`، واضغط بحث.
4. اختر الحزمة والإصدار ثم اضغط **Install**.

ماذا تفعل الـ IDE في الخلفية؟ تنفذ الأمر:

```text
dotnet add _build/csharp/RadApp.csproj package Newtonsoft.Json
```

أي أنها تضيف سطر `PackageReference` إلى ملف مشروع البناء `_build/csharp/RadApp.csproj` الذي تحتفظ به لمشروعك، ثم تنزل الحزمة عند البناء التالي.

### إضافة حزمة إلى مشروع Visual Studio (`.csproj`)

إذا كان مشروعك ملف `.csproj` (مثل مشاريع أمثلة هذه الدورة)، فانقر بالزر الأيمن على المشروع في **Solution Explorer** واختر **Manage NuGet Packages...** (إدارة حزم NuGet...)، أو أضف السطر بنفسك في ملف المشروع:

```xml
<ItemGroup>
  <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
</ItemGroup>
```

### مثال يعمل: تحويل كائن إلى JSON بحزمة Newtonsoft.Json

**JSON** صيغة نصية شهيرة لتبادل البيانات بين البرامج ومواقع الويب. هذا المثال فيه ملفان: `Program.cs` وملف المشروع `Lesson.csproj` الذي يطلب الحزمة (السطر `// #file:` يفصل بين الملفين في الدرس). يحتاج أول تشغيل إلى الإنترنت لتنزيل الحزمة إذا لم تكن على جهازك.

```csharp run
using Newtonsoft.Json;

var student = new Student { Name = "Salma", Age = 15, Grades = new[] { 90, 85, 99 } };
string json = JsonConvert.SerializeObject(student);
Console.WriteLine(json);

var back = JsonConvert.DeserializeObject<Student>("{\"Name\":\"Karim\",\"Age\":16,\"Grades\":[70,80]}");
Console.WriteLine($"{back.Name} عمره {back.Age} ومتوسطه {back.Grades.Average()}");

class Student
{
    public string Name { get; set; }
    public int Age { get; set; }
    public int[] Grades { get; set; }
}
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>disable</Nullable>
    <RollForward>Major</RollForward>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
</Project>
```

```text output
{"Name":"Salma","Age":15,"Grades":[90,85,99]}
Karim عمره 16 ومتوسطه 75
```

> **ملحوظة:** .NET نفسها فيها مكتبة JSON مدمجة اسمها `System.Text.Json`، فلا تحتاج إلى حزمة لأبسط الحالات. اخترنا `Newtonsoft.Json` هنا لأنها أشهر حزمة في NuGet ولنتعلم طريقة الإضافة.

### من سطر الأوامر

نفس الأوامر التي تنفذها الـ IDE يمكنك كتابتها في **Terminal**:

| الأمر | وظيفته |
|---|---|
| `dotnet add package Newtonsoft.Json` | إضافة حزمة |
| `dotnet add package Newtonsoft.Json --version 13.0.3` | إضافة إصدار محدد |
| `dotnet remove package Newtonsoft.Json` | حذف حزمة |
| `dotnet list package` | عرض حزم المشروع |
| `dotnet restore` | تنزيل كل الحزم المطلوبة |

## الجزء الثاني: تصحيح الأخطاء (Debugging)

نوعان من الأخطاء:

- **أخطاء الترجمة** (compile errors): المترجم يرفض الكود ويخبرك بالسطر. سهلة نسبيًا.
- **الأخطاء المنطقية** (logic errors): البرنامج يعمل لكن الناتج خطأ. هنا نحتاج إلى **المصحح** (debugger).

> **تشبيه:** المصحح مثل **زر الإيقاف المؤقت وإعادة اللقطة** في مباراة كرة القدم: توقف اللعب عند لحظة معينة، وتنظر أين كان كل لاعب، ثم تتقدم لقطة لقطة لترى أين حدث الخطأ بالضبط.

### المصحح netcoredbg

الـ IDE تستخدم **netcoredbg**، وهو مصحح مفتوح المصدر لـ .NET من شركة Samsung. ضع ملفه `netcoredbg.exe` في `%LOCALAPPDATA%\RADIDE\tools\netcoredbg\` (نزّل `netcoredbg-win64.zip` من صفحة المشروع `github.com/Samsung/netcoredbg`)، أو في أي مجلد ضمن `PATH`. إذا لم تجده الـ IDE ستكتب لك ذلك في نافذة Output.

### برنامج فيه خطأ منطقي

هذا البرنامج يُفترض أن يحسب متوسط الدرجات، لكن الناتج غريب:

```csharp run
int[] grades = { 90, 80, 75 };
int sum = 0;
for (int i = 0; i < grades.Length; i++)
{
    sum += grades[i];
}
double average = sum / grades.Length;   // الخطأ هنا!
Console.WriteLine($"المتوسط = {average}");
```

```text output
المتوسط = 81
```

المتوسط الحقيقي `245 ÷ 3 = 81.67`، فلماذا ظهر `81`؟ لنستخدم المصحح لنكتشف ذلك.

### الخطوة 1: نقطة توقف (Breakpoint)

1. اضغط «افتح في المحرر» فوق المثال.
2. ضع المؤشر على السطر `double average = ...` واضغط **F9**: **Debug > Toggle Breakpoint** (تصحيح الأخطاء > تبديل نقطة التوقف). تظهر دائرة حمراء في الهامش.

### الخطوة 2: التشغيل مع التصحيح

اضغط **F5**: **Debug > Start Debugging / Continue** (تصحيح الأخطاء > بدء تصحيح الأخطاء / متابعة). تبني الـ IDE المشروع وتشغله تحت netcoredbg، ويتوقف البرنامج **قبل** تنفيذ السطر المعلّم، ويظهر السطر بلون مميز.

### الخطوة 3: راقب المتغيرات

- نافذة **Locals** (المتغيرات المحلية): تعرض كل المتغيرات وقيمها الآن: `sum = 245`، و`grades` مصفوفة من 3 عناصر.
- نافذة **Call Stack** (مكدس الاستدعاءات): تعرض سلسلة الدوال التي أوصلتنا إلى هذا السطر.
- نافذة **Immediate** (الأوامر الفورية): اكتب تعبيرًا مثل `sum / grades.Length` واضغط Enter لترى قيمته: `81`. ثم جرّب `sum / 3.0` فترى `81.666...`. وجدنا السبب: **قسمة عددين صحيحين**!

### الخطوة 4: التنقل خطوة بخطوة

| المفتاح | الأمر | الاسم العربي | ماذا يفعل |
|---|---|---|---|
| `F10` | Step Over | خطوة فوق | ينفذ السطر الحالي وينتقل إلى التالي |
| `F11` | Step Into | خطوة إلى الداخل | يدخل داخل الدالة المستدعاة في السطر |
| `Shift+F11` | Step Out | خطوة إلى الخارج | يكمل الدالة الحالية ويعود إلى من استدعاها |
| `F5` | Continue | متابعة | يكمل حتى نقطة التوقف التالية |
| `Shift+F5` | Stop Debugging | إيقاف | ينهي البرنامج |

### الإصلاح

```csharp run
int[] grades = { 90, 80, 75 };
int sum = 0;
for (int i = 0; i < grades.Length; i++)
{
    sum += grades[i];
}
double average = (double)sum / grades.Length;
Console.WriteLine($"المتوسط = {average:F2}");
```

```text output
المتوسط = 81.67
```

### تصحيح البرامج الرسومية

نفس الخطوات تعمل في مشاريع **C# (GUI Bridge)**: ضع نقطة توقف داخل `btnHello_Click` في `Form1.cs` واضغط F5، ثم اضغط الزر في نافذة برنامجك، فيتوقف التنفيذ عند السطر وترى قيمة `txtName.Text` وغيرها.

### نقطة توقف داخل حلقة

ضع نقطة توقف على السطر `sum += grades[i];` في المثال الأول، واضغط F5 ثم F5 مرة بعد مرة: في كل مرة يتوقف البرنامج في لفّة جديدة، وترى في Locals كيف تزيد `i` و`sum`. هذه أفضل طريقة لفهم أي حلقة لا تعمل كما تتوقع.

## نصائح للتصحيح

- **اقرأ رسالة الخطأ كاملة:** نوع الاستثناء (`NullReferenceException`...) ورقم السطر يدلانك على المكان مباشرة.
- **اطبع القيم** بـ `Console.WriteLine` في المواضع المشكوك فيها، فهي أبسط طرق التصحيح.
- **قسّم المشكلة:** علّق نصف الكود واختبر، ثم ضيّق الدائرة.
- **اشرح الكود بصوت عالٍ** لزميل (أو لدمية!)، فكثيرًا ما تجد الخطأ وأنت تشرح.

## تمارين

### التمرين 1

هذا البرنامج يجب أن يطبع الأعداد الزوجية من 2 إلى 10، لكنه يطبع شيئًا آخر. استخدم المصحح (أو فكّر) لتجد الخطأ وتصلحه.

```csharp exercise
for (int i = 1; i <= 10; i++)
{
    if (i % 2 == 1)
        Console.Write(i + " ");
}
Console.WriteLine();
```

```csharp solution
for (int i = 1; i <= 10; i++)
{
    if (i % 2 == 0)
        Console.Write(i + " ");
}
Console.WriteLine();
```

```text output
2 4 6 8 10
```

### التمرين 2

الدالة `CountVowels` يجب أن تعد الحروف المتحركة الإنجليزية (a e i o u) في النص، لكنها تعطي ناتجًا خاطئًا مع الحروف الكبيرة. أصلحها.

```csharp exercise
static int CountVowels(string s)
{
    int count = 0;
    foreach (char c in s)
        if ("aeiou".Contains(c))
            count++;
    return count;
}

Console.WriteLine(CountVowels("Hello World"));
Console.WriteLine(CountVowels("AEIOU"));
```

```csharp solution
static int CountVowels(string s)
{
    int count = 0;
    foreach (char c in s.ToLower())
        if ("aeiou".Contains(c))
            count++;
    return count;
}

Console.WriteLine(CountVowels("Hello World"));
Console.WriteLine(CountVowels("AEIOU"));
```

```text output
3
5
```

## اختبر نفسك

```quiz
{"question": "من أين تنزّل حزم .NET الجاهزة؟", "choices": ["من npm", "من NuGet", "من Maven Central", "من PyPI"], "answer": 1, "explanation": "NuGet هو مستودع الحزم الرسمي لـ .NET."}
```

```quiz
{"question": "ما المفتاح الذي يضع أو يزيل نقطة توقف؟", "choices": ["F5", "F9", "F10", "F11"], "answer": 1, "explanation": "F9 = Toggle Breakpoint، وF5 للتشغيل مع التصحيح."}
```

```quiz
{"question": "ما الفرق بين F10 وF11 أثناء التصحيح؟", "choices": ["لا فرق", "F10 ينفذ السطر كاملًا، وF11 يدخل داخل الدالة المستدعاة فيه", "F11 يوقف البرنامج", "F10 يعيد التشغيل"], "answer": 1, "explanation": "Step Over (F10) يتخطى الدالة كوحدة واحدة، وStep Into (F11) يدخلها سطرًا سطرًا."}
```

```quiz
{"question": "أي نافذة تعرض قيم المتغيرات عند التوقف؟", "choices": ["Output", "Toolbox", "Locals", "Solution Explorer"], "answer": 2, "explanation": "نافذة Locals (المتغيرات المحلية) تعرض متغيرات الدالة الحالية وقيمها."}
```

## الخلاصة

- **NuGet**: **Project > Manage Packages...** في المشاريع الرسومية، و**Manage NuGet Packages...** في مشاريع `.csproj`، أو `dotnet add package`.
- المصحح **netcoredbg**: `F9` نقطة توقف، و`F5` تشغيل ومتابعة، و`F10` / `F11` / `Shift+F11` للتنقل.
- **Locals** و**Call Stack** و**Immediate** لمراقبة البرنامج أثناء التوقف.
