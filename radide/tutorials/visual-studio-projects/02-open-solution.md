# الدرس 2: فتح .sln و.csproj ومستكشف الحلول

في هذا الدرس نفتح حلًا من Visual Studio، ونتعرف على **مستكشف الحلول** (Solution Explorer) وما يعرضه، ونضيف ملفات ومشاريع.

## الحل والمشروع: ما الفرق؟

- **المشروع** (Project): ملف `.csproj` (أو `.vbproj`) يصف برنامجًا واحدًا أو مكتبة واحدة: الملفات، والإطار المستهدف (`net8.0`)، والحزم، والمراجع.
- **الحل** (Solution): ملف `.sln` يجمع عدة مشاريع معًا، مثل تطبيق رسومي ومكتبة يستخدمها ومشروع اختبارات.

> **تشبيه:** **المشروع** مثل **كتاب**، و**الحل** مثل **رف المكتبة** الذي يجمع عدة كتب في موضوع واحد. يمكنك أن تأخذ كتابًا واحدًا من الرف (تفتح `.csproj` وحده)، أو تأخذ الرف كله (تفتح `.sln`).

## فتح الحل خطوة بخطوة

1. **File > Open Project...** (ملف > فتح مشروع...) أو `Ctrl+Shift+O`.
2. اختر الملف `.sln` (أو `.slnx`، أو `.csproj` / `.vbproj` وحده).
3. تفتح الـ IDE الحل **في مكانه** وتعرضه في **Solution Explorer** (مستكشف الحلول).

طريقة أخرى: **File > Open Folder...** (ملف > فتح مجلد...) واختر مجلد المشروع. تتعرف الـ IDE على نوعه تلقائيًا (حل Visual Studio، أو مشروع Maven، أو Node...) وتعرض عليك فتحه في مكانه.

> **نصيحة:** آخر المشاريع التي فتحتها تظهر في **File > Recent Projects and Solutions**، وفي صفحة البداية.

## ماذا يعرض مستكشف الحلول؟

يعرض الحل بنفس ترتيب Visual Studio تقريبًا:

```text
Solution 'Shop' (2 projects)
├── ShopApp                       ← مشروع بدء التشغيل (بخط عريض)
│   ├── Dependencies
│   │   ├── Frameworks            (Microsoft.NETCore.App، Microsoft.WindowsDesktop.App)
│   │   ├── Packages              (حزم NuGet مثل Newtonsoft.Json)
│   │   └── Projects              (ShopLib)
│   ├── Form1.cs
│   │   ├── Form1.Designer.cs
│   │   └── Form1.resx
│   └── Program.cs
└── ShopLib
    ├── Dependencies
    └── Product.cs
```

- **Dependencies** (التبعيات): الأطر والحزم والمشاريع المرتبطة. وفي المشاريع القديمة تظهر باسم **References** (المراجع).
- **Form1.cs** يظهر تحته ملفاه التابعان `Form1.Designer.cs` و`Form1.resx`، كما في Visual Studio.
- **الخط العريض** يميز **مشروع بدء التشغيل** (StartUp Project): المشروع الذي يعمل عند `F5`.
- **مجلدات الحل** (Solution Folders) تظهر كمجلدات تنظيمية.

## القوائم السياقية (الزر الأيمن)

| انقر بالزر الأيمن على | أهم الأوامر |
|---|---|
| الحل | **Build Solution** (بناء الحل)، **Rebuild Solution** (إعادة بناء الحل)، **Clean Solution** (تنظيف الحل)، **Set StartUp Project** (تعيين مشروع بدء التشغيل)، **Add > New Project... / Existing Project...**، **Open in Visual Studio** (فتح في Visual Studio)، **Migrate to a RAD IDE project...**، **Properties** (الخصائص) |
| مشروع | **Build** و**Rebuild** و**Clean**، **Set as StartUp Project** (تعيين كمشروع بدء التشغيل)، **Manage NuGet Packages...** (إدارة حزم NuGet...)، **Edit Project File**، **Reload Project**، **Remove from Solution** (إزالة من الحل)، **Properties** |
| Dependencies | **Add Project Reference...**، **Add Assembly Reference...**، **Manage NuGet Packages...** |
| مجلد أو مشروع | **Add > New Item...** (فئة، واجهة، Windows Form، User Control...)، **Existing Item...** (عنصر موجود...)، **New Folder** |
| ملف | **Open**، **View Code** (عرض الكود)، **View Designer** (عرض المصمم)، **Exclude From Project**، **Open Containing Folder** |

## إضافة ملف جديد

1. انقر بالزر الأيمن على المشروع واختر **Add > New Item...**.
2. اختر **Class** واكتب الاسم `Calculator.cs`.
3. تضيف الـ IDE الملف في المجلد. في المشاريع الحديثة (SDK-style) لا يلزم تعديل `.csproj` لأنها تضم كل ملفات `.cs` تلقائيًا، وفي المشاريع القديمة تضيف الـ IDE سطر `<Compile Include="Calculator.cs" />` في المكان المناسب.

هذا مثال لمشروع فيه ملفان، كما يصبح بعد إضافة الصنف (السطر `// #file:` يفصل بين الملفات في الدرس، والمثال الكامل فيه ملف المشروع `Lesson.csproj` أيضًا):

```csharp run
var calc = new Calculator();
Console.WriteLine($"5 + 3 = {calc.Add(5, 3)}");
Console.WriteLine($"عدد العمليات: {calc.Operations}");
// #file: Calculator.cs
public class Calculator
{
    public int Operations { get; private set; }

    public int Add(int a, int b)
    {
        Operations++;
        return a + b;
    }
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

</Project>
```

```text output
5 + 3 = 8
عدد العمليات: 1
```

لاحظ كم هو قصير ملف المشروع الحديث: لا يذكر `Program.cs` ولا `Calculator.cs`، فكل ملف `.cs` في المجلد جزء من المشروع تلقائيًا. الخاصية `RollForward` تسمح بتشغيله على إصدار .NET أحدث إذا لم يوجد الإصدار 8.

## خصائص المشروع

انقر بالزر الأيمن على المشروع واختر **Properties** (الخصائص). تظهر نافذة فيها أهم الخصائص، وتُكتب مباشرة في `.csproj`:

| الخاصية | معناها |
|---|---|
| `AssemblyName` | اسم الملف الناتج (`Lesson.dll` / `Lesson.exe`) |
| `RootNamespace` | فضاء الأسماء الافتراضي للملفات الجديدة |
| `TargetFramework` | الإطار المستهدف، مثل `net8.0` أو `net8.0-windows` لبرامج Windows Forms |
| `OutputType` | `Exe` (كونسول)، أو `WinExe` (نافذة بلا كونسول)، أو `Library` (مكتبة `.dll`) |
| `StartupObject` | الصنف الذي فيه `Main` إذا كان هناك أكثر من واحد |
| `Nullable` / `ImplicitUsings` | ميزات لغة C# الحديثة |

وفي النافذة أيضًا: مسار ملف المشروع، ونوعه (SDK-style أو legacy)، والإعدادات المتاحة (`Debug` و`Release`).

## إضافة مشروع إلى الحل

1. انقر بالزر الأيمن على الحل: **Add > New Project...**.
2. اختر القالب (مثلًا **Class Library**) واللغة (C# أو VB.NET) والاسم `ShopLib`.
3. تنشئ الـ IDE المشروع بـ `dotnet new` وتضيفه إلى ملف `.sln` (تعديل نصي صغير يحافظ على باقي الملف).
4. لكي يستخدم `ShopApp` المكتبة: انقر بالزر الأيمن على **Dependencies** في `ShopApp` ثم **Add Project Reference...** واختر `ShopLib`.

يظهر في `ShopApp.csproj`:

```xml
<ItemGroup>
  <ProjectReference Include="..\ShopLib\ShopLib.csproj" />
</ItemGroup>
```

## أخطاء شائعة

- **فتح المجلد الخطأ:** إذا اخترت مجلدًا داخليًا (مثل `ShopApp\bin`) فلن تجد الـ IDE مشروعًا. اختر المجلد الذي فيه `.sln`.
- **ملف ظاهر في المجلد لكنه ليس في المشروع:** في المشاريع القديمة الملف الذي لا يذكره `.csproj` لا يُترجم. انقر بالزر الأيمن على المشروع: **Add > Existing Item...** واختره.
- **`F5` يشغّل المشروع الخطأ:** غيّر مشروع بدء التشغيل: الزر الأيمن على المشروع الصحيح ثم **Set as StartUp Project**.

## اختبر نفسك

```quiz
{"question": "ما الفرق بين ملف .sln وملف .csproj؟", "choices": ["لا فرق", ".csproj يصف مشروعًا واحدًا، و.sln يجمع عدة مشاريع", ".sln للغة VB فقط", ".csproj للصور"], "answer": 1, "explanation": "المشروع كتاب، والحل رف يجمع الكتب."}
```

```quiz
{"question": "كيف تعرف مشروع بدء التشغيل في مستكشف الحلول؟", "choices": ["لونه أحمر", "اسمه بخط عريض", "يظهر أولًا دائمًا", "عليه علامة نجمة"], "answer": 1, "explanation": "كما في Visual Studio، مشروع بدء التشغيل يظهر بخط عريض ويعمل عند F5."}
```

```quiz
{"question": "أضفت ملف Calculator.cs إلى مشروع SDK-style حديث. هل يلزم تعديل .csproj؟", "choices": ["نعم دائمًا", "لا، المشروع الحديث يضم كل ملفات .cs في المجلد تلقائيًا", "يلزم حذف المشروع وإعادة إنشائه", "يلزم تعديل .sln"], "answer": 1, "explanation": "المشاريع الحديثة تستخدم globbing، أما القديمة فتحتاج سطر Compile Include."}
```

## الخلاصة

- **File > Open Project...** (`Ctrl+Shift+O`) يفتح `.sln` أو `.csproj` أو `.vbproj` في مكانه.
- **Solution Explorer** يعرض المشاريع والتبعيات والملفات وتوابعها، ومشروع بدء التشغيل بخط عريض.
- الزر الأيمن هو بوابتك: إضافة ملفات ومشاريع ومراجع، والخصائص، وحزم NuGet.
