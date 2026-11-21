# الدرس 11: المشاريع المشتركة واستهداف عدة أطر عمل

أحيانًا تريد **نفس الكود** في برنامجين مختلفين: تطبيق .NET 8 حديث، وبرنامج قديم على .NET Framework 4.8 عند عميل لا يستطيع التحديث. لهذا يقدم Visual Studio طريقتين: **Shared Project** (المشروع المشترك)، و**Multi-targeting** (استهداف عدة أطر عمل). وفي الحالتين تكتب أجزاء خاصة بكل إطار بين `#if` و`#endif`.

> **تشبيه:** المشروع المشترك مثل **وصفة مكتوبة على ورقة** تصوّرها لكل مطبخ: كل مطبخ يطبخها بأدواته (كل مشروع يترجم الملفات بنفسه). أما مكتبة **multi-targeting** فهي **مطبخ مركزي** يطبخ الطبق مرتين، مرة لكل نوع من الفروع، ويرسل لكل فرع النسخة المناسبة له.

## المشروع المشترك (Shared Project)

المشروع المشترك **لا يُبنى وحده** ولا ينتج `.dll`. هو مجموعة ملفات، وكل مشروع يرجع إليه **يترجم ملفاته داخله** كأنها ملفاته هو.

يتكون من ملفين:

| الملف | محتواه |
|---|---|
| `SharedUtils.shproj` | ملف صغير يعرّف المشروع لـ Visual Studio |
| `SharedUtils.projitems` | قائمة الملفات المشتركة: `<Compile Include="$(MSBuildThisFileDirectory)Money.cs" />` |

والمشروع المستخدِم يضيف سطرًا واحدًا:

```xml
<Import Project="..\SharedUtils\SharedUtils.projitems" Label="Shared" />
```

### إنشاؤه واستخدامه في RAD IDE

1. زر أيمن على الحل > **Add > New Shared Project...**، أو **Add > New Project...** ثم ابحث عن `Shared Project` في المعالج.
2. يظهر في **Solution Explorer** بأيقونة خاصة. زر أيمن عليه > **Add > New Item...** أو **Existing Item...** أو **New Folder**.
3. في المشروع المستخدِم: زر أيمن على **Dependencies** > **Add Shared Project Reference...**، وعلّم المشروع المشترك، ثم **OK**.
4. يظهر تحت **Dependencies > Shared Projects** في المشروع المستخدِم.

> **مهم:** المشروع المشترك بلغة واحدة: مشروع C# المشترك لا يُستخدم إلا من مشاريع C#، ومشروع VB المشترك من مشاريع VB فقط.

### مثال يعمل

في الحل الحقيقي يكون المشروع المشترك في مجلده الخاص. في هذا المثال وضعنا كل الملفات في مجلد واحد، لذلك أضفنا `<Compile Remove="Greeter.cs" />` حتى لا يضيف المشروع الملف مرتين (مرة تلقائيًا ومرة من `Shared.projitems`):

```csharp run
using SharedCode;

Console.WriteLine($"Running on: {Greeter.Platform()}");
Console.WriteLine($"Edition: {Greeter.Edition}");
// #file: Greeter.cs
namespace SharedCode;

public static class Greeter
{
    public static string Platform()
    {
#if NETFRAMEWORK
        return ".NET Framework";
#elif NET8_0_OR_GREATER
        return ".NET 8 or later";
#else
        return "another .NET";
#endif
    }

#if SHOP_PRO
    public static string Edition => "Pro";
#else
    public static string Edition => "Basic";
#endif
}
// #file: Shared.projitems
<?xml version="1.0" encoding="utf-8"?>
<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup>
    <HasSharedItems>true</HasSharedItems>
    <SharedGUID>6f3c2a51-9d7e-4b8a-a1c4-2e5f7d9b0c13</SharedGUID>
  </PropertyGroup>
  <PropertyGroup Label="Configuration">
    <Import_RootNamespace>SharedCode</Import_RootNamespace>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="$(MSBuildThisFileDirectory)Greeter.cs" />
  </ItemGroup>
</Project>
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RollForward>Major</RollForward>
  </PropertyGroup>
  <ItemGroup>
    <Compile Remove="Greeter.cs" />
  </ItemGroup>
  <Import Project="Shared.projitems" Label="Shared" />
</Project>
```

```text output
Running on: .NET 8 or later
Edition: Basic
```

## رموز المعالج المسبق (#if)

`#if` يقرر **وقت الترجمة** أي الأسطر تدخل البرنامج. الرموز (symbols) تأتي من مصدرين:

| المصدر | أمثلة |
|---|---|
| يضيفها الـ SDK تلقائيًا حسب الإطار | `NET8_0` و`NET8_0_OR_GREATER` و`NETCOREAPP` و`NETSTANDARD2_0` و`NETFRAMEWORK` و`NET48` و`WINDOWS` |
| حسب الإعداد | `DEBUG` في Debug، و`RELEASE` في Release، و`TRACE` |
| تضيفها أنت | `<DefineConstants>$(DefineConstants);SHOP_PRO</DefineConstants>` في ملف المشروع، أو من **Properties > Build > Conditional compilation symbols** |

وفي VB: `#If NET8_0_OR_GREATER Then ... #ElseIf ... #Else ... #End If`، و`#Const` لتعريف رمز في الملف.

### مثال يعمل: أي الرموز معرّفة؟

```csharp run
#if NET8_0
Console.WriteLine("NET8_0");
#endif
#if NET8_0_OR_GREATER
Console.WriteLine("NET8_0_OR_GREATER");
#endif
#if NET9_0_OR_GREATER
Console.WriteLine("NET9_0_OR_GREATER");
#endif
#if NETCOREAPP
Console.WriteLine("NETCOREAPP");
#endif
#if NETFRAMEWORK
Console.WriteLine("NETFRAMEWORK");
#endif
#if DEBUG
Console.WriteLine("DEBUG");
#endif
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

```text output
NET8_0
NET8_0_OR_GREATER
NETCOREAPP
DEBUG
```

`NET9_0_OR_GREATER` غير معرّف لأن المشروع يستهدف `net8.0`، حتى لو كان الـ SDK على جهازك إصدار 9.

## سياق المشروع في المحرر (Project context)

عندما تفتح ملفًا من مشروع مشترك، يظهر فوق المحرر شريط فيه قائمة **Project context**، مثل Visual Studio:

- القائمة فيها كل مشروع يستخدم الملف مع إطاره، مثل `WinApp (net8.0-windows)` و`FxConsole (net48)`.
- بجانبها الرموز المعرّفة في هذا السياق.
- الأسطر **غير الفعالة** (التي لن تُترجم في هذا السياق) تظهر **باهتة** (رمادية).

غيّر السياق إلى `FxConsole (net48)` فيبهت فرع `NET8_0_OR_GREATER` ويضيء فرع `NETFRAMEWORK`. هكذا ترى بالضبط ما سيترجمه كل مشروع، كما يحسبه MSBuild.

## استهداف عدة أطر عمل (Multi-targeting)

بدل المشروع المشترك، يمكنك جعل **مكتبة واحدة** تُبنى لعدة أطر. لاحظ `TargetFrameworks` بالجمع:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFrameworks>net8.0;netstandard2.0</TargetFrameworks>
    <LangVersion>latest</LangVersion>
  </PropertyGroup>

  <!-- حزمة تُضاف فقط عند البناء لـ netstandard2.0 -->
  <ItemGroup Condition="'$(TargetFramework)' == 'netstandard2.0'">
    <PackageReference Include="System.Text.Json" Version="8.0.5" />
  </ItemGroup>
</Project>
```

- عند البناء يُنتج المشروع مجلدين: `bin\Debug\net8.0\` و`bin\Debug\netstandard2.0\`.
- المشروع الذي يرجع إليه يأخذ **أنسب نسخة** تلقائيًا: تطبيق .NET 8 يأخذ نسخة `net8.0`، وبرنامج .NET Framework 4.8 يأخذ نسخة `netstandard2.0`.
- في RAD IDE: **Project Properties > Application** فيه خانة **Target multiple frameworks** لكتابة أكثر من إطار (مثل `net8.0;net48`).

### متى أستخدم أيهما؟

| | Shared Project | Multi-targeting |
|---|---|---|
| ينتج `.dll` خاصًا به | لا، الكود يدخل كل مشروع | نعم، `.dll` لكل إطار |
| يمكن نشره كحزمة NuGet | لا | نعم |
| يستطيع الوصول إلى أصناف المشروع المستخدِم | نعم (الكود يُترجم داخله) | لا |
| مناسب لـ | كود صغير بين تطبيقين (مثل كود واجهة مشترك) | مكتبة تُستخدم من أماكن كثيرة |

## أخطاء شائعة

- **`CS0246` في ملف مشترك:** الملف يستخدم صنفًا موجودًا في مشروع واحد فقط من المستخدِمين. انقل الصنف إلى المشروع المشترك، أو ضعه بين `#if`.
- **`NETSDK1022: Duplicate 'Compile' items were included`:** الملف المشترك داخل مجلد المشروع المستخدِم فيُضاف مرتين. ضع المشروع المشترك في مجلد مستقل.
- **أخطاء مثل `CS8630: Invalid 'nullable' value` عند netstandard2.0:** ميزات اللغة الحديثة تحتاج `<LangVersion>latest</LangVersion>` مع الأطر القديمة.

## تمرين

نريد أن يطبع البرنامج `Edition: Pro`. لا تغيّر الكود؛ أضف الرمز `SHOP_PRO` في ملف المشروع (`<DefineConstants>$(DefineConstants);SHOP_PRO</DefineConstants>` داخل `PropertyGroup`).

```csharp exercise
#if SHOP_PRO
Console.WriteLine("Edition: Pro");
#else
Console.WriteLine("Edition: Basic");
#endif
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
#if SHOP_PRO
Console.WriteLine("Edition: Pro");
#else
Console.WriteLine("Edition: Basic");
#endif
// #file: Lesson.csproj
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <RollForward>Major</RollForward>
    <DefineConstants>$(DefineConstants);SHOP_PRO</DefineConstants>
  </PropertyGroup>
</Project>
```

```text output
Edition: Pro
```

## اختبر نفسك

```quiz
{"question": "ماذا ينتج المشروع المشترك (Shared Project) عند البناء؟", "choices": ["ملف .dll خاصًا به", "لا شيء وحده: ملفاته تُترجم داخل كل مشروع يرجع إليه", "حزمة NuGet", "ملف .exe"], "answer": 1, "explanation": "المشروع المشترك قائمة ملفات تُستورد في المشاريع المستخدمة بسطر Import Label=\"Shared\"."}
```

```quiz
{"question": "مشروع يستهدف net8.0. أي رمز من هذه غير معرّف؟", "choices": ["NET8_0", "NETCOREAPP", "NET8_0_OR_GREATER", "NETFRAMEWORK"], "answer": 3, "explanation": "NETFRAMEWORK معرّف فقط عند استهداف .NET Framework مثل net48."}
```

```quiz
{"question": "تريد مكتبة واحدة تُنشر على NuGet وتعمل مع .NET 8 و.NET Framework 4.8. ماذا تختار؟", "choices": ["Shared Project", "Multi-targeting بـ TargetFrameworks", "نسخ الملفات يدويًا", "Add As Link"], "answer": 1, "explanation": "Multi-targeting ينتج .dll لكل إطار، ويمكن تغليفه في حزمة NuGet واحدة."}
```

## الخلاصة

- **Shared Project**: ملفا `.shproj` و`.projitems`، ويُستخدم بـ **Add Shared Project Reference...** الذي يكتب `<Import ... Label="Shared" />`.
- `#if` مع رموز الإطار (`NET8_0_OR_GREATER` و`NETFRAMEWORK`...) والإعداد (`DEBUG`) ورموزك في `DefineConstants`.
- شريط **Project context** فوق المحرر يبهت الأسطر غير الفعالة لكل مشروع.
- **Multi-targeting**: `TargetFrameworks` بالجمع، ومجلد إخراج لكل إطار.
