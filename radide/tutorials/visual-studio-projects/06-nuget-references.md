# الدرس 6: حزم NuGet والمراجع

نادرًا ما يُكتب برنامج .NET من الصفر: نستخدم **حزم NuGet** (مكتبات من الإنترنت)، و**مراجع** إلى مشاريع أخرى في الحل أو إلى ملفات `.dll`. هذا الدرس يشرح الأنواع الثلاثة وكيف تضيفها في RAD IDE.

> **تشبيه:** مشروعك مثل **مطبخ مطعم**. **حزمة NuGet** مثل مكونات تشتريها جاهزة من المورّد (صلصة جاهزة). **مرجع المشروع** مثل مطبخ فرعي في نفس المطعم يحضّر لك العجين. و**مرجع الـ dll** مثل علبة مكونات أعطاك إياها صديق، لا تعرف وصفتها لكنك تستخدمها.

## الأنواع الثلاثة في ملف المشروع

```xml
<ItemGroup>
  <!-- 1) حزمة من NuGet -->
  <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />

  <!-- 2) مشروع آخر في نفس الحل -->
  <ProjectReference Include="..\ShopLib\ShopLib.csproj" />

  <!-- 3) ملف dll (غالبًا في المشاريع القديمة) -->
  <Reference Include="LegacyTools">
    <HintPath>..\libs\LegacyTools.dll</HintPath>
  </Reference>
</ItemGroup>
```

وتظهر الثلاثة في **Solution Explorer** تحت **Dependencies** (التبعيات): **Packages** و**Projects** و**Assemblies**. وفي المشاريع القديمة تحت **References** (المراجع).

## 1) حزم NuGet

### من الواجهة

1. في **Solution Explorer** انقر بالزر الأيمن على المشروع (أو على **Dependencies**) واختر **Manage NuGet Packages...** (إدارة حزم NuGet...).
2. اكتب اسم الحزمة في البحث، مثل `Newtonsoft.Json`.
3. اختر الحزمة والإصدار واضغط **Install**. ولإزالتها اخترها من الحزم المثبتة واضغط **Uninstall**.
4. عند إغلاق النافذة تعيد الـ IDE قراءة ملف المشروع وتحدّث **Dependencies**.

ماذا يحدث خلف الكواليس؟

| نوع المشروع | الطريقة |
|---|---|
| SDK-style (حديث) | الأمر `dotnet add package Newtonsoft.Json` |
| قديم (non-SDK) | تعديل نصي يضيف `PackageReference` في ملف المشروع مع الحفاظ على تنسيقه |

### مثال يعمل

هذا مشروع Visual Studio فيه حزمة `Newtonsoft.Json` (يحتاج أول تشغيل إلى الإنترنت لتنزيلها إذا لم تكن على جهازك):

```csharp run
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

var order = new Order { Id = 7, Customer = "Mona", Items = new List<string> { "Pen", "Book" } };
string json = JsonConvert.SerializeObject(order, Formatting.Indented);
Console.WriteLine(json);

JObject obj = JObject.Parse("{\"city\": \"Alex\", \"temp\": 27}");
Console.WriteLine($"{obj["city"]}: {obj["temp"]} درجة");

class Order
{
    public int Id { get; set; }
    public string Customer { get; set; }
    public List<string> Items { get; set; }
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
{
  "Id": 7,
  "Customer": "Mona",
  "Items": [
    "Pen",
    "Book"
  ]
}
Alex: 27 درجة
```

### أوامر Terminal المقابلة

| الأمر | وظيفته |
|---|---|
| `dotnet add package Newtonsoft.Json` | إضافة أحدث إصدار |
| `dotnet add package Newtonsoft.Json --version 13.0.3` | إضافة إصدار محدد |
| `dotnet remove package Newtonsoft.Json` | إزالة |
| `dotnet list package` | عرض حزم المشروع |
| `dotnet list package --outdated` | الحزم التي لها إصدارات أحدث |
| `dotnet restore` | تنزيل كل الحزم المطلوبة |

## 2) مرجع إلى مشروع آخر في الحل

1. انقر بالزر الأيمن على **Dependencies** في المشروع المستخدِم واختر **Add Project Reference...**.
2. اختر المكتبة من مشاريع الحل (مثل `ShopLib`).
3. يُضاف السطر `<ProjectReference Include="..\ShopLib\ShopLib.csproj" />`، وعند البناء تُبنى المكتبة أولًا.

بعدها تستخدم أصناف المكتبة العامة (`public`) مع `using ShopLib;`.

> **نصيحة:** قسّم البرنامج الكبير إلى **مكتبة** (Class Library) فيها المنطق والبيانات، و**تطبيق** (Windows Forms أو كونسول) فيه الواجهة فقط. هكذا يمكنك أن تكتب لاحقًا واجهة ثانية (موقع ويب مثلًا) تستخدم نفس المكتبة.

## 3) مرجع إلى ملف dll

للمكتبات التي ليست في NuGet (مكتبة قديمة من شركة، أو ملف أعطاك إياه زميل):

1. انقر بالزر الأيمن على **Dependencies** واختر **Add Assembly Reference...**.
2. اختر من أطر .NET المتاحة، أو اضغط **Browse...** واختر ملف `.dll`.
3. يُضاف `<Reference Include="..."><HintPath>...</HintPath></Reference>`.

> **مهم:** ضع ملفات `.dll` داخل مجلد الحل (مثل `libs\`)، ليبقى المسار النسبي في `HintPath` صحيحًا على كل جهاز.

## إزالة مرجع

انقر بالزر الأيمن على الحزمة أو المرجع تحت **Dependencies** واختر **Remove**. يُحذف السطر من ملف المشروع فقط، وتبقى باقي الأسطر كما هي.

## أخطاء شائعة

- **`error NU1101: Unable to find package`:** اسم الحزمة خطأ، أو لا يوجد اتصال بالإنترنت. تأكد من الاسم في `nuget.org`.
- **`CS0246: The type or namespace name 'JsonConvert' could not be found`:** الحزمة غير مضافة إلى **هذا** المشروع (ربما أضفتها لمشروع آخر في الحل)، أو نسيت `using Newtonsoft.Json;`.
- **مرجع دائري:** المشروع A يرجع إلى B، وB يرجع إلى A. هذا ممنوع؛ انقل الكود المشترك إلى مكتبة ثالثة.

## تمرين

البرنامج التالي يستخدم `JsonConvert` لكنه لا يُبنى. أضف السطر الناقص في ملف المشروع ليعمل ويطبع الناتج المتوقع.

```csharp exercise
using Newtonsoft.Json;

var data = JsonConvert.DeserializeObject<Dictionary<string, int>>("{\"apples\": 3, \"pears\": 5}");
Console.WriteLine($"المجموع: {data.Values.Sum()}");
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RollForward>Major</RollForward>
  </PropertyGroup>
</Project>
```

```csharp solution
using Newtonsoft.Json;

var data = JsonConvert.DeserializeObject<Dictionary<string, int>>("{\"apples\": 3, \"pears\": 5}");
Console.WriteLine($"المجموع: {data.Values.Sum()}");
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RollForward>Major</RollForward>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
</Project>
```

```text output
المجموع: 8
```

## اختبر نفسك

```quiz
{"question": "أي سطر في ملف المشروع يضيف حزمة NuGet؟", "choices": ["<ProjectReference Include=...>", "<PackageReference Include=\"Newtonsoft.Json\" Version=\"13.0.3\" />", "<Compile Include=...>", "<Reference Include=...>"], "answer": 1, "explanation": "PackageReference للحزم، وProjectReference للمشاريع، وReference لملفات dll."}
```

```quiz
{"question": "تريد أن يستخدم تطبيقك مكتبة ShopLib الموجودة في نفس الحل. ماذا تختار؟", "choices": ["Manage NuGet Packages...", "Add Project Reference...", "Add Assembly Reference...", "Open in Visual Studio"], "answer": 1, "explanation": "مرجع المشروع يجعل المكتبة تُبنى أولًا ويربطها بتطبيقك."}
```

```quiz
{"question": "ظهر الخطأ CS0246 لأن JsonConvert غير معروف رغم أنك أضفت الحزمة. ما السبب المحتمل؟", "choices": ["الحزمة أضيفت لمشروع آخر في الحل أو نسيت using", "الحاسوب بطيء", "يجب إعادة تثبيت Windows", "الحزمة تعمل في Release فقط"], "answer": 0, "explanation": "كل مشروع له حزمه الخاصة، ويلزم using Newtonsoft.Json في الملف."}
```

## الخلاصة

- **Manage NuGet Packages...** من الزر الأيمن على المشروع أو **Dependencies**، أو `dotnet add package`.
- **Add Project Reference...** لمشاريع الحل، و**Add Assembly Reference...** لملفات `.dll` والأطر.
- كل التعديلات نصية دقيقة في ملف المشروع، والمشروع يبقى صالحًا لـ Visual Studio.
