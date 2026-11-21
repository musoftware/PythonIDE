# الدرس 12: حلول متعددة المشاريع: الدمج وبدء التشغيل والإعدادات والنشر

البرامج الحقيقية حل فيه مشاريع كثيرة: تطبيق، ومكتبات، ومشروع اختبارات، وربما خدمة تعمل في الخلفية. في هذا الدرس ننظم الحل كما في Visual Studio 2022: ندمج مشاريع من حل آخر، ونرتبها في مجلدات، ونختار ما يعمل عند `F5`، وننشئ إعدادات بناء جديدة، ونجهز **ملفات تعريف التشغيل** (launch profiles)، ثم **ننشر** البرنامج.

> **تشبيه:** الحل مثل **مطعم فيه عدة أقسام**. **مجلدات الحل** هي لافتات الأقسام. و**مشاريع بدء التشغيل** هي الأقسام التي تفتح أولًا صباحًا. و**Configuration Manager** هو جدول «في يوم الجمعة يعمل قسم الحلويات فقط». و**النشر** هو تغليف الطلبات للتوصيل.

## إضافة مشاريع إلى الحل

زر أيمن على الحل > **Add**:

| الأمر | وظيفته |
|---|---|
| **New Project...** | معالج المشروع الجديد (قوالب `dotnet new` وقوالب .NET Framework) |
| **Existing Project...** | ملف `.csproj` أو `.vbproj` أو `.fsproj` أو `.vcxproj` أو `.shproj` موجود |
| **Existing Solution's Projects...** | **دمج حل آخر**: تختار من قائمة مشاريعه ما تريد، وتُنشأ مجلداته كما هي |
| **Existing RAD IDE Project...** | مشروع C# من مشاريع RAD IDE (عبر ملفه `_build/csharp/RadApp.csproj`) |
| **New Solution Folder** | مجلد حل لتنظيم المشاريع (لا يُنشئ مجلدًا على القرص) |
| **New Item...** / **Existing Item...** | ملفات الحل (Solution Items) مثل `.editorconfig` و`README.md` |

بعد الدمج يُحفظ ملف الحل، وتظهر المشاريع الجديدة في **Solution Explorer**، وتُضاف إلى قوائم الإعدادات تلقائيًا. ويمكنك سحب أي مشروع وإفلاته على مجلد حل لنقله، أو استخدام **Move To Solution Folder**.

> **نصيحة:** **Unload Project** يخفي مشروعًا لا تعمل عليه الآن (يظهر رماديًا بكلمة «(unloaded)»، والعنوان يصبح مثلًا «5 of 6 projects»)، و**Reload Project** يعيده. هذا يسرّع الحلول الكبيرة.

## ترتيب البناء والتبعيات

- **ProjectReference** يحدد ترتيب البناء تلقائيًا: المكتبة قبل التطبيق.
- وإذا احتجت ترتيبًا دون مرجع (مثلًا أداة تولّد ملفات قبل البناء): زر أيمن على الحل > **Project Dependencies...**، وعلّم المشاريع التي يعتمد عليها المشروع. والتبويب **Build Order** يعرض الترتيب النهائي.
- الاعتماد الدائري مرفوض في الحالتين.

## مشاريع بدء التشغيل (Startup Projects)

زر أيمن على الحل > **Configure Startup Projects...**. تُفتح **Solution Property Pages**:

| الخيار | معناه |
|---|---|
| **Current selection** | المشروع المختار في **Solution Explorer** هو الذي يعمل |
| **Single startup project** | مشروع واحد ثابت (وهو أيضًا **Set as Startup Project** في قائمة المشروع) |
| **Multiple startup projects** | لكل مشروع: **None** أو **Start** أو **Start without debugging** |

مع **Multiple startup projects** يضغط `F5` فيُبنى كل مشروع مطلوب ويعمل، وأول مشروع **Start** يأخذ المصحح، وتظهر مخرجات كل مشروع في **Output** مسبوقة باسمه، مثل `[Worker] Hello, World!`. مثال: موقع ويب API وتطبيق سطح مكتب يتصل به.

## ملفات تعريف التشغيل (Launch Profiles)

ملف `Properties\launchSettings.json` يحفظ **كيف** يعمل المشروع: الوسائط، ومتغيرات البيئة، ومجلد العمل:

```json
{
  "profiles": {
    "App": {
      "commandName": "Project"
    },
    "Staging": {
      "commandName": "Project",
      "commandLineArgs": "--mode staging --verbose",
      "environmentVariables": {
        "DOTNET_ENVIRONMENT": "Staging"
      },
      "workingDirectory": "C:\\Shop\\data"
    }
  }
}
```

- القائمة المنسدلة **بجانب قائمتي Debug / Any CPU** في شريط الأدوات تعرض ملفات التعريف. اختر `Staging` ثم `F5`.
- لتحريرها: **Project Properties > Debug > Open debug launch profiles UI**. نافذة **Launch Profiles** فيها زر لإضافة ملف تعريف من نوع **Project** أو **Executable** (تشغيل برنامج آخر مثل أداة اختبار).

هذا البرنامج يطبع ما يصله. عند `F5` مع `Staging` تظهر الوسائط والمتغير، وفي المدقق يعمل بلا وسائط:

```csharp run
string mode = Environment.GetEnvironmentVariable("DOTNET_ENVIRONMENT") ?? "Production";
Console.WriteLine($"Arguments: {(args.Length == 0 ? "(none)" : string.Join(" ", args))}");
Console.WriteLine($"Environment: {mode}");
```

```text output
Arguments: (none)
Environment: Production
```

## الإعدادات: Configuration Manager

القائمتان **Debug** و**Any CPU** في شريط الأدوات هما **إعداد الحل** و**منصة الحل**. ومن **Build > Configuration Manager...** أو بالزر الأيمن على الحل > **Configuration Manager...** تفتح النافذة:

- **Active solution configuration** و**Active solution platform** في الأعلى، ومنهما **<New...>** و**<Edit...>** لإنشاء إعداد جديد (مثل `Staging` منسوخًا من `Release`) أو إعادة تسميته أو حذفه.
- جدول فيه كل مشروع: **Configuration** و**Platform** الخاصان به في هذا الإعداد، ومربع **Build** (هل يُبنى؟) و**Deploy**.
- مثال مفيد: في إعداد `Staging` ألغِ **Build** لمشروع الاختبارات فيصبح البناء أسرع.

تُكتب الإعدادات في ملف الحل، ويُضاف الإعداد الجديد إلى المشاريع (`<Configurations>`). وكل ما تختاره هنا يستخدمه `F5` و**Build Solution**.

## إعدادات مشتركة لكل المشاريع: Directory.Build.props

ملف `Directory.Build.props` في مجلد الحل يُقرأ **تلقائيًا** في كل مشروع تحته. ضع فيه ما يتكرر: اسم الشركة، والإصدار، و`Nullable`، و`LangVersion`. ويظهر في **Solution Explorer**، وفي **Project Properties** تظهر بجانب القيمة الموروثة عبارة «Inherited from Directory.Build.props».

```csharp run
using System.Reflection;

var asm = typeof(Program).Assembly;
Console.WriteLine($"Company: {asm.GetCustomAttribute<AssemblyCompanyAttribute>()?.Company}");
Console.WriteLine($"Version: {asm.GetName().Version}");
#if DEBUG
Console.WriteLine("Configuration: Debug");
#else
Console.WriteLine("Configuration: Release");
#endif
// #file: Directory.Build.props
<Project>
  <PropertyGroup>
    <Company>Contoso</Company>
    <Version>2.1.0</Version>
  </PropertyGroup>
</Project>
```

```text output
Company: Contoso
Version: 2.1.0.0
Configuration: Debug
```

## خصائص المشروع (Project Properties)

زر أيمن على المشروع > **Properties** يفتح **مستند خصائص** كتبويب، مثل Visual Studio 2022: مربع بحث في الأعلى، وصفحات على اليسار: **Application** و**Global Usings** و**Build** و**Build Events** و**Package** و**Code Analysis** و**Debug** و**Resources** و**Settings** و**Signing**. وقائمتا **Configuration** و**Platform** تحددان أي إعداد تعدّله (أو **All configurations**). كل تغيير يُكتب في ملف المشروع فورًا.

## النشر (Publish)

زر أيمن على المشروع > **Publish...**:

| الخيار | معناه |
|---|---|
| **Target location** | مجلد الإخراج، مثل `bin\Release\publish\` |
| **Deployment mode** | **Framework-dependent** (يحتاج .NET على جهاز العميل، والملفات أصغر) أو **Self-contained** (يحمل .NET معه) |
| **Target runtime** | مثل `win-x64` |
| **Produce single file** | ملف `.exe` واحد |
| **Enable ReadyToRun compilation** | ترجمة مسبقة لبدء أسرع |
| **Trim unused code** | حذف ما لا يُستخدم (مع Self-contained) لتصغير الحجم |

يُحفظ ملف التعريف في `Properties\PublishProfiles\FolderProfile.pubxml`، ثم يُنفَّذ `dotnet publish` وتظهر النتيجة في **Output**. وفي المرة القادمة اختر ملف التعريف واضغط **Publish** مباشرة.

## ‏.sln أم ‎.slnx؟

`.slnx` هي صيغة الحلول الجديدة: XML قصير ومقروء بدل الصيغة القديمة الطويلة. من قائمة الحل **Save Solution As .slnx...** تحفظ نسخة جديدة وتُفتح مكانها (والعكس **Save Solution As .sln...**). الملف الناتج مطابق لما يكتبه الأمر `dotnet sln migrate`:

```xml
<Solution>
  <Configurations>
    <BuildType Name="Debug" />
    <BuildType Name="Release" />
    <BuildType Name="Staging" />
  </Configurations>
  <Folder Name="/src/">
    <Project Path="src/Shop.App/Shop.App.csproj" />
    <Project Path="src/Shop.Core/Shop.Core.csproj" />
  </Folder>
  <Folder Name="/tests/">
    <Project Path="tests/Shop.Tests/Shop.Tests.csproj" />
  </Folder>
</Solution>
```

## أخطاء شائعة

- **`F5` يشغّل المشروع الخطأ:** اختر **Single startup project** أو **Set as Startup Project**، أو تأكد من أن **Current selection** غير مفعّل.
- **مشروع لا يُبنى أبدًا:** في **Configuration Manager** مربع **Build** غير معلّم له في الإعداد الحالي.
- **إعدادات launch profile لا تُطبَّق:** اخترت ملف تعريف في القائمة لكن المشروع الذي يعمل مشروع آخر. ملف التعريف خاص بكل مشروع.
- **الملف المنشور لا يعمل على جهاز العميل:** نشرته **Framework-dependent** والجهاز بلا .NET. انشر **Self-contained**.

## تمرين

غيّر **ملف `Directory.Build.props` فقط** ليطبع البرنامج الإصدار `3.0.0.0` والشركة `Fabrikam`.

```csharp exercise
using System.Reflection;

var asm = typeof(Program).Assembly;
Console.WriteLine($"{asm.GetCustomAttribute<AssemblyCompanyAttribute>()?.Company} {asm.GetName().Version}");
// #file: Directory.Build.props
<Project>
  <PropertyGroup>
    <Company>Contoso</Company>
    <Version>2.1.0</Version>
  </PropertyGroup>
</Project>
```

```csharp solution
using System.Reflection;

var asm = typeof(Program).Assembly;
Console.WriteLine($"{asm.GetCustomAttribute<AssemblyCompanyAttribute>()?.Company} {asm.GetName().Version}");
// #file: Directory.Build.props
<Project>
  <PropertyGroup>
    <Company>Fabrikam</Company>
    <Version>3.0.0</Version>
  </PropertyGroup>
</Project>
```

```text output
Fabrikam 3.0.0.0
```

## اختبر نفسك

```quiz
{"question": "تريد إضافة كل مشاريع حل آخر (Tools.slnx) إلى حلك مع مجلداته. أي أمر تختار؟", "choices": ["Add > Existing Item...", "Add > Existing Solution's Projects...", "Add > New Solution Folder", "Open in Visual Studio"], "answer": 1, "explanation": "Existing Solution's Projects يعرض قائمة بمشاريع الحل الآخر، ويضيف ما تختاره مع مجلداته."}
```

```quiz
{"question": "في Multiple startup projects: المشروع API = Start والمشروع Desktop = Start without debugging. ماذا يحدث عند F5؟", "choices": ["يعمل API فقط", "يعمل الاثنان، وAPI مع المصحح", "يعمل Desktop فقط مع المصحح", "لا يعمل شيء"], "answer": 1, "explanation": "كل مشروع Start أو Start without debugging يعمل، وأول Start يأخذ المصحح."}
```

```quiz
{"question": "أين تُحفظ وسائط سطر الأوامر ومتغيرات البيئة لملف تعريف التشغيل؟", "choices": ["في ملف الحل .sln", "في Properties\\launchSettings.json", "في Directory.Build.props", "في .editorconfig"], "answer": 1, "explanation": "launchSettings.json يحفظ ملفات تعريف التشغيل لكل مشروع."}
```

```quiz
{"question": "أي خيار نشر يجعل البرنامج يعمل على جهاز ليس عليه .NET؟", "choices": ["Framework-dependent", "Self-contained", "ReadyToRun فقط", "Debug"], "answer": 1, "explanation": "Self-contained يحمل بيئة .NET مع البرنامج."}
```

## الخلاصة

- **Add > Existing Solution's Projects...** لدمج حل آخر، و**New Solution Folder** والسحب والإفلات للتنظيم، و**Unload / Reload** للحلول الكبيرة.
- **Configure Startup Projects...**: مشروع واحد أو عدة مشاريع، كل منها **Start** أو **Start without debugging**.
- **Launch profiles** في `launchSettings.json` وتُختار من القائمة بجانب Debug / Any CPU.
- **Configuration Manager** لإنشاء إعدادات مثل `Staging` واختيار ما يُبنى فيها، و`Directory.Build.props` للإعدادات المشتركة.
- **Publish...** بملف تعريف `.pubxml`، و**Save Solution As .slnx...** للصيغة الجديدة.
