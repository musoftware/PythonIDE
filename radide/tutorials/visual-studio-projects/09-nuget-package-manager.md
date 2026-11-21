# الدرس 9: مدير حزم NuGet ووحدة تحكم الحزم

في الدرس 6 أضفنا حزمة واحدة بسرعة. هنا نتعرف على **مدير حزم NuGet** كاملًا كما في Visual Studio 2022: البحث والتثبيت والتحديث والإزالة، وتوحيد الإصدارات في كل الحل، و**وحدة تحكم مدير الحزم** (Package Manager Console) التي تكتب فيها أوامر مثل `Install-Package`.

> **تشبيه:** NuGet مثل **سوق جملة** للمكتبات. **مدير الحزم** هو الكتالوج المصوّر: تتصفح وتقرأ التفاصيل وتضغط «اشترِ». و**وحدة التحكم** هي الطلب بالتليفون: تقول اسم الصنف والكمية مباشرة فيصلك أسرع، إذا كنت تعرف ما تريد.

## فتح مدير الحزم

| من أين | ماذا يفتح |
|---|---|
| زر أيمن على المشروع > **Manage NuGet Packages...** | مستند **NuGet: اسم المشروع** لمشروع واحد |
| زر أيمن على الحل > **Manage NuGet Packages for Solution...** | مستند **NuGet - Solution** لكل مشاريع الحل |
| **Tools > NuGet Package Manager** | القائمة نفسها، ومعها **Package Manager Console** و**Package Manager Settings** |

يُفتح المستند كتبويب في منطقة المحرر، مثل Visual Studio تمامًا.

## التبويبات الأربعة

| التبويب | وظيفته |
|---|---|
| **Browse** (استعراض) | البحث في nuget.org والمصادر الأخرى. اكتب في مربع البحث (`Ctrl+L`) |
| **Installed** (المثبتة) | الحزم المثبتة: **Top-level** التي أضفتها أنت، و**Transitive** التي جاءت معها تلقائيًا |
| **Updates** (التحديثات) | الحزم التي لها إصدار أحدث، مع عدّاد بجانب الاسم، و**Select all packages** ثم **Update** |
| **Consolidate** (توحيد) | في مستند الحل فقط: حزمة واحدة بإصدارات مختلفة في مشاريع مختلفة |

وفي الأعلى:

- **Include prerelease** (تضمين الإصدارات التجريبية): لعرض إصدارات مثل `2.0.0-beta1`.
- **Package source** (مصدر الحزم): `nuget.org`، أو كل المصادر (**All**)، أو مجلد الحزم المحلي للعمل بلا إنترنت.
- زر الترس يفتح إعدادات المصادر.

## لوحة التفاصيل

عند اختيار حزمة يظهر على اليمين:

1. **Version** (الإصدار): أحدث إصدار مستقر أولًا، ويمكنك اختيار أي إصدار أقدم.
2. زر **Install** أو **Update** أو **Uninstall** حسب حالة الحزمة في المشروع.
3. تحذير أصفر إذا كانت الحزمة **مهملة** (deprecated) أو فيها **ثغرة أمنية** معروفة.
4. تبويب **Package Details**: الرخصة، وعدد التنزيلات، والتبعيات لكل إطار عمل.
5. تبويب **README**: وصف الحزمة من صاحبها.

وقبل التثبيت تظهر نافذة **Preview Changes** (معاينة التغييرات) بما سيُضاف، ونافذة **License Acceptance** (قبول الرخصة) إذا طلبت الحزمة ذلك. إذا ضغطت **I Decline** لا يتغير شيء.

## مثال يعمل: حزمة Humanizer

مكتبة `Humanizer.Core` تحوّل الأرقام والنصوص والأوقات إلى كلام مقروء:

```csharp run
using System.Globalization;
using Humanizer;

CultureInfo.CurrentUICulture = new CultureInfo("en-US");

Console.WriteLine(5.ToWords());
Console.WriteLine("order".ToQuantity(3));
Console.WriteLine("InvoiceTotalAmount".Humanize());
Console.WriteLine(TimeSpan.FromMinutes(90).Humanize(2));
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RollForward>Major</RollForward>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Humanizer.Core" Version="2.14.1" />
  </ItemGroup>
</Project>
```

```text output
five
3 orders
Invoice total amount
1 hour, 30 minutes
```

> **لماذا السطر `CultureInfo.CurrentUICulture`؟** Humanizer يكتب بلغة واجهة Windows. لو كان جهازك بالعربية لكتب «خمسة». ثبّتنا الإنجليزية هنا ليظهر الناتج نفسه على كل الأجهزة.

## وحدة تحكم مدير الحزم (Package Manager Console)

افتحها من **Tools > NuGet Package Manager > Package Manager Console**، أو **View > Other Windows > Package Manager Console**. تظهر كنافذة سفلية بجانب **Output**، فيها:

- السطر `PM>` لكتابة الأوامر.
- قائمة **Default project** (المشروع الافتراضي): الأوامر تنفَّذ عليه ما لم تكتب `-ProjectName`.

| الأمر | مثال | وظيفته |
|---|---|---|
| `Install-Package` | `Install-Package Newtonsoft.Json -Version 13.0.3` | تثبيت حزمة |
| `Uninstall-Package` | `Uninstall-Package Newtonsoft.Json -RemoveDependencies` | إزالة حزمة (ومعها تبعياتها) |
| `Update-Package` | `Update-Package Newtonsoft.Json` | تحديث حزمة، أو كل الحزم إذا لم تكتب اسمًا |
| `Get-Package` | `Get-Package -Updates` | عرض الحزم المثبتة، أو التي لها تحديثات |
| `Find-Package` | `Find-Package Serilog -First 5` | البحث في المصدر |
| `Get-Project` | `Get-Project -All` | عرض مشاريع الحل |
| `Restore-Package` | `Restore-Package` | تنزيل الحزم الناقصة |
| `Get-Help` | `Get-Help Install-Package` | شرح الأمر |

ومع كل أوامر التثبيت تعمل الخيارات `-ProjectName` و`-Version` و`-Source` و`-IncludePrerelease`، و`-WhatIf` الذي يعرض ما **سيحدث** دون تنفيذه.

> **نصيحة:** اكتب أول حروف اسم الحزمة ثم اضغط `Tab`، فتكمل الوحدة الاسم من nuget.org. والسهم `↑` يعيد الأوامر السابقة.

## ثلاثة أنماط لتخزين الحزم

| النمط | أين تُكتب الحزم | متى تراه |
|---|---|---|
| **PackageReference** | داخل ملف المشروع `<PackageReference Include=... Version=... />` | كل المشاريع الحديثة (SDK-style) |
| **packages.config** | ملف منفصل بجانب المشروع، والحزم تُفك في مجلد `packages` بجانب الحل، ويُضاف `<Reference>` مع `HintPath` | مشاريع .NET Framework القديمة |
| **Central Package Management** | الإصدارات كلها في ملف واحد `Directory.Packages.props` بجانب الحل، والمشاريع تكتب الاسم فقط | الحلول الكبيرة التي تريد إصدارًا واحدًا لكل حزمة |

الـ IDE تعرف النمط وحدها: مع PackageReference تستخدم `dotnet add package`، ومع packages.config تفك الحزمة وتضيف المراجع بنفسها، ومع الإدارة المركزية تعدّل الملفين معًا.

### مثال يعمل: الإدارة المركزية للإصدارات

هنا ملف المشروع يذكر اسم الحزمة **بلا إصدار**، والإصدار في `Directory.Packages.props`:

```csharp run
using Newtonsoft.Json;

var prices = new Dictionary<string, decimal> { ["Pen"] = 2.5m, ["Book"] = 40m };
Console.WriteLine(JsonConvert.SerializeObject(prices));
Console.WriteLine(typeof(JsonConvert).Assembly.GetName().Version);
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RollForward>Major</RollForward>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" />
  </ItemGroup>
</Project>
// #file: Directory.Packages.props
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Newtonsoft.Json" Version="13.0.3" />
  </ItemGroup>
</Project>
```

```text output
{"Pen":2.5,"Book":40.0}
13.0.0.0
```

> **ملاحظة:** رقم إصدار الـ assembly (`13.0.0.0`) غير رقم إصدار الحزمة (`13.0.3`). صاحب الحزمة يختار الرقمين، وكثيرون يثبّتون رقم الـ assembly حتى لا تنكسر البرامج القديمة.

## توحيد الإصدارات (Consolidate)

إذا كان مشروع يستخدم `Newtonsoft.Json 13.0.1` ومشروع آخر يستخدم `13.0.3`، فقد تحدث أخطاء غريبة عند التشغيل لأن البرنامج يحمّل إصدارًا واحدًا فقط. لحل ذلك:

1. زر أيمن على الحل > **Manage NuGet Packages for Solution...**.
2. افتح تبويب **Consolidate**. العدّاد بجانبه يخبرك بعدد الحزم المختلفة.
3. اختر الحزمة، فتظهر المشاريع وإصدار كل منها.
4. اختر الإصدار الموحد، وعلّم المشاريع، واضغط **Install**.

## مصادر الحزم (Package Sources)

من **Tools > NuGet Package Manager > Package Manager Settings** ثم **Package Sources**:

- أضف مصدرًا جديدًا: رابط خادم شركتك، أو **مجلد** فيه ملفات `.nupkg`.
- فعّل أو عطّل مصدرًا، أو غيّر ترتيبه.
- إذا كان في مجلد الحل ملف `nuget.config` تُكتب التغييرات فيه (فتنتقل مع الحل إلى زملائك)، وإلا ففي إعدادات NuGet الخاصة بك.

ومن صفحة **General**: **Clear All NuGet Storage** يمسح ذاكرة الحزم المؤقتة إذا تلفت حزمة.

> **عن الإنترنت:** الـ IDE لا تتصل إلا بـ `api.nuget.org` والمصادر التي أضفتها أنت، وتحفظ نتائج البحث مؤقتًا، فتعمل التبويبات **Installed** والبحث في مجلد الحزم المحلي بلا إنترنت.

## أخطاء شائعة

- **`NU1605: Detected package downgrade`:** مشروع يطلب إصدارًا أقدم من الذي تطلبه حزمة أخرى. حدّث الحزمة أو وحّد الإصدارات من **Consolidate**.
- **`NU1010: The PackageReference items ... do not have corresponding PackageVersion`:** الإدارة المركزية مفعلة، وأضفت حزمة بلا سطر `PackageVersion`. أضفه في `Directory.Packages.props`، أو ثبّت الحزمة من الواجهة فتضيفه الـ IDE.
- **`Unable to uninstall ... because ... depends on it`:** في packages.config لا يمكن حذف حزمة تحتاجها حزمة أخرى. احذف الحزمة الأعلى أولًا، أو استخدم `-RemoveDependencies`.

## تمرين

الإدارة المركزية مفعلة، لكن البناء يفشل بالخطأ `NU1010`. أضف السطر الناقص في `Directory.Packages.props` (إصدار `Humanizer.Core` هو `2.14.1`).

```csharp exercise
using System.Globalization;
using Humanizer;

CultureInfo.CurrentUICulture = new CultureInfo("en-US");
Console.WriteLine("item".ToQuantity(2) + ", " + 12.ToWords());
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RollForward>Major</RollForward>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Humanizer.Core" />
  </ItemGroup>
</Project>
// #file: Directory.Packages.props
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
  </ItemGroup>
</Project>
```

```csharp solution
using System.Globalization;
using Humanizer;

CultureInfo.CurrentUICulture = new CultureInfo("en-US");
Console.WriteLine("item".ToQuantity(2) + ", " + 12.ToWords());
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RollForward>Major</RollForward>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Humanizer.Core" />
  </ItemGroup>
</Project>
// #file: Directory.Packages.props
<Project>
  <PropertyGroup>
    <ManagePackageVersionsCentrally>true</ManagePackageVersionsCentrally>
  </PropertyGroup>
  <ItemGroup>
    <PackageVersion Include="Humanizer.Core" Version="2.14.1" />
  </ItemGroup>
</Project>
```

```text output
2 items, twelve
```

## اختبر نفسك

```quiz
{"question": "في أي تبويب تجد حزمة مثبتة بإصدارين مختلفين في مشروعين؟", "choices": ["Browse", "Installed", "Updates", "Consolidate"], "answer": 3, "explanation": "Consolidate في مستند الحل يعرض الحزم ذات الإصدارات المختلفة ويوحدها."}
```

```quiz
{"question": "ماذا يفعل الأمر Install-Package Serilog -ProjectName Shop.Core -WhatIf ؟", "choices": ["يثبت Serilog في كل المشاريع", "يعرض ما سيحدث عند تثبيت Serilog في Shop.Core دون أن يثبته", "يحذف Serilog", "يبحث عن Serilog فقط"], "answer": 1, "explanation": "-WhatIf يعرض التغييرات دون تنفيذها، و-ProjectName يحدد المشروع."}
```

```quiz
{"question": "مع الإدارة المركزية للحزم (Central Package Management)، أين يُكتب رقم الإصدار؟", "choices": ["في كل ملف .csproj", "في packages.config", "في Directory.Packages.props", "في ملف .sln"], "answer": 2, "explanation": "المشاريع تكتب PackageReference بلا Version، والإصدارات في PackageVersion داخل Directory.Packages.props."}
```

## الخلاصة

- **Manage NuGet Packages** لمشروع، و**Manage NuGet Packages for Solution** لكل الحل، بأربعة تبويبات: **Browse** و**Installed** و**Updates** و**Consolidate**.
- **Package Manager Console**: الأوامر `Install-Package` و`Uninstall-Package` و`Update-Package` و`Get-Package` مع `-ProjectName` و`-Version` و`-WhatIf`.
- ثلاثة أنماط: PackageReference، وpackages.config للمشاريع القديمة، والإدارة المركزية بملف `Directory.Packages.props`.
