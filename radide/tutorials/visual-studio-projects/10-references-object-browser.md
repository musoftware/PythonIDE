# الدرس 10: المراجع (DLL وCOM والمشاريع) ومستعرض الكائنات

في الدرس 6 عرفنا أن للمشروع ثلاثة أنواع من التبعيات. هنا نتعمق في **المراجع** (References): نافذة **Reference Manager** (مدير المراجع) كما في Visual Studio 2022، ومراجع COM، وملفات DLL الأصلية (native)، وخصائص المرجع، ثم **Object Browser** (مستعرض الكائنات) الذي يريك ما بداخل أي مكتبة.

> **تشبيه:** المرجع مثل **بطاقة مكتبة عامة**: لا تنسخ الكتب إلى بيتك، بل تكتب في دفترك «أستعير من مكتبة كذا». و**مستعرض الكائنات** هو **فهرس المكتبة**: تعرف منه ما فيها من كتب (أصناف) وفصول (دوال) قبل أن تستعيرها.

## فتح Reference Manager

انقر بالزر الأيمن على **Dependencies** (أو **References** في المشاريع القديمة) واختر أحد الأوامر:

| الأمر | الصفحة التي يفتحها |
|---|---|
| **Add Project Reference...** | **Projects > Solution**: مشاريع الحل الأخرى |
| **Add Shared Project Reference...** | **Shared Projects**: المشاريع المشتركة (الدرس 11) |
| **Add COM Reference...** | **COM > Type Libraries**: مكتبات COM المسجلة في Windows |
| **Add Assembly Reference...** | **Assemblies > Framework / Extensions** أو **Browse** |

والأوامر نفسها في الزر الأيمن على المشروع تحت **Add**.

في النافذة: شجرة الأقسام على اليسار، ومربعات اختيار للعناصر، ومربع بحث (`Ctrl+E`)، ولوحة تفاصيل على اليمين، وزر **Browse...** وزرا **OK** و**Cancel**. علّم ما تريد وألغِ تعليم ما لا تريده، ثم **OK**: تُكتب كل التغييرات في ملف المشروع مرة واحدة، ويعاد تحميل المشروع، ويعرف محرر الكود (IntelliSense) المراجع الجديدة فورًا.

## الصفحات بالتفصيل

### Assemblies > Framework

- في مشاريع **.NET Framework** القديمة: قائمة بمكتبات الإطار (مثل `System.Numerics` و`System.Windows.Forms`). علّم ما تحتاجه فيُضاف `<Reference Include="System.Numerics" />`.
- في المشاريع **الحديثة (SDK-style)** تظهر ملاحظة Visual Studio: مكتبات الإطار **مُضافة ضمنيًا** (implicitly) بالفعل. ويمكنك هنا إضافة إطار كامل آخر مثل `Microsoft.AspNetCore.App` أو `Microsoft.WindowsDesktop.App`، فيُكتب `<FrameworkReference Include="..." />`.

### Projects

مرجع إلى مشروع في نفس الحل: يُكتب `<ProjectReference Include="..\Billing\Billing.csproj" />`، وعند البناء يُبنى المشروع المرجعي أولًا.

> **مهم:** المرجع الدائري ممنوع. إذا كان `Billing` يرجع إلى `App`، فلا يمكن أن يرجع `App` إلى `Billing`. ستظهر رسالة Visual Studio نفسها: «A reference to 'App' could not be added. Adding this project as a reference would cause a circular dependency.»

### Browse

لملف `.dll` على جهازك. تتحقق الـ IDE أولًا من أن الملف **مكتبة .NET** (assembly)، ثم تكتب:

```xml
<Reference Include="Tools.Text">
  <HintPath>..\libs\Tools.Text.dll</HintPath>
</Reference>
```

والمسار في `HintPath` **نسبي** إلى مجلد المشروع، لذلك ضع ملفات الـ DLL داخل مجلد الحل. والملفات التي اخترتها تُحفظ في قائمة **Browse > Recent** لتجدها بسرعة لاحقًا.

### COM

مكتبات COM هي مكونات Windows القديمة (مثل `Microsoft Scripting Runtime` أو مكونات Office). عند اختيار واحدة يُكتب:

```xml
<COMReference Include="Scripting">
  <Guid>{420B2830-E718-11CF-893D-00A0C9054228}</Guid>
  <VersionMajor>1</VersionMajor>
  <VersionMinor>0</VersionMinor>
  <Lcid>0</Lcid>
  <WrapperTool>tlbimp</WrapperTool>
  <EmbedInteropTypes>True</EmbedInteropTypes>
</COMReference>
```

> **ملاحظة:** بناء مراجع COM يحتاج **MSBuild الخاص بـ Visual Studio** (أو Build Tools)، لأن `dotnet build` لا يستطيع تشغيل الأداة `tlbimp`. ستظهر رسالة الخطأ `MSB4803` لو حاولت. الـ IDE تختار MSBuild المناسب وحدها إذا وجدته.

## ملف DLL ليس مكتبة .NET؟

ملفات مثل `kernel32.dll` أو مكتبة C++ مكتوبة لـ Windows هي **مكتبات أصلية** (native)، ولا تُضاف كمرجع. إذا اخترت واحدة في **Browse** تشرح لك الـ IDE ذلك، وتعرض نسخ الملف إلى مجلد الإخراج. وتستدعي دوالها من الكود بـ `DllImport`:

```csharp run
using System.Runtime.InteropServices;

uint fromWindows = Native.GetCurrentProcessId();
Console.WriteLine($"kernel32 says: {fromWindows == (uint)Environment.ProcessId}");
Console.WriteLine($"Pointer size matches: {Environment.Is64BitProcess == (IntPtr.Size == 8)}");

static class Native
{
    [DllImport("kernel32.dll")]
    public static extern uint GetCurrentProcessId();
}
```

```text output
kernel32 says: True
Pointer size matches: True
```

البرنامج يسأل Windows مباشرة عن رقم العملية (process) من `kernel32.dll`، ويقارنه بما يعرفه .NET، فيطبع `True`.

## خصائص المرجع (Properties)

اختر أي مرجع تحت **Dependencies** فتظهر في نافذة **Properties** خصائصه بعنوان «*الاسم* Reference Properties»:

| الخاصية | معناها |
|---|---|
| **Copy Local** | انسخ الـ DLL إلى مجلد الإخراج (`<Private>`). اجعلها `False` للمكتبات الموجودة على كل الأجهزة |
| **Specific Version** | لا تقبل إلا هذا الإصدار بالضبط. عند تفعيلها يُكتب الاسم الكامل للمكتبة (الاسم والإصدار والمفتاح العام) |
| **Aliases** | اسم بديل عند وجود صنفين بنفس الاسم في مكتبتين (`extern alias`) |
| **Embed Interop Types** | لمراجع COM: ضمّن أنواع COM داخل برنامجك بدل ملف interop منفصل |
| **Path** و**Version** و**Identity** و**Runtime Version** و**Strong Name** | للقراءة فقط |

## Add As Link: ملف واحد في مشروعين

من **Add > Existing Item...** اختر ملفًا، ثم من السهم بجانب زر **Add** اختر **Add As Link**. لا يُنسخ الملف، بل يُكتب:

```xml
<Compile Include="..\Common\SharedHelper.cs" Link="Shared\SharedHelper.cs" />
```

ويظهر في **Solution Explorer** بأيقونة سهم صغيرة. أي تعديل فيه يظهر في كل المشاريع التي تربطه. للمشاركة الأوسع استخدم **Shared Project** (الدرس 11).

## مستعرض الكائنات (Object Browser)

افتحه من **View > Object Browser** (`Ctrl+Alt+J`)، أو بالزر الأيمن على مرجع > **Open in Object Browser**.

- **Browse:** اختر **My Solution** (مكتبات الحل ومراجعه) أو **Custom Component Set** لمكتبات تختارها أنت.
- الشجرة على اليسار: المكتبة > مساحة الأسماء (namespace) > الصنف.
- القائمة على اليمين: أعضاء الصنف (الدوال والخصائص والأحداث) بتوقيع C#.
- اللوحة السفلية: التوقيع الكامل وتعليقات التوثيق (`/// <summary>`) إن وجدت.
- مربع البحث يجد أي صنف أو دالة بالاسم، و**Show Private Members** يعرض الأعضاء الخاصة.
- **Go To Definition** يفتح كود الصنف **مفكوكًا** (decompiled) بالأداة `ilspycmd` في تبويب للقراءة فقط. تسألك الـ IDE قبل تنزيل الأداة أول مرة.

### مثال يعمل: مستعرض كائنات صغير

مستعرض الكائنات يقرأ «البيانات الوصفية» (metadata) للمكتبة. ويمكنك قراءتها بنفسك بالانعكاس (Reflection):

```csharp run
using System.Reflection;

var type = typeof(Invoice);
Console.WriteLine($"{type.Namespace}.{type.Name}");
foreach (var m in type.GetMembers(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                      .OrderBy(m => m.Name))
{
    string kind = m.MemberType switch
    {
        MemberTypes.Method => "method",
        MemberTypes.Property => "property",
        MemberTypes.Constructor => "constructor",
        _ => m.MemberType.ToString()
    };
    if (m is MethodInfo mi && mi.IsSpecialName) continue;
    Console.WriteLine($"  {kind,-11} {m.Name}");
}

namespace Shop
{
    public class Invoice
    {
        public decimal Total { get; set; }
        public void AddLine(decimal price) => Total += price;
        public string Describe() => $"Total: {Total}";
    }
}
// #file: Usings.cs
global using Shop;
```

```text output
Shop.Invoice
  constructor .ctor
  method      AddLine
  method      Describe
  property    Total
```

لاحظ أن `get_Total` و`set_Total` (الدالتان اللتان يولّدهما المترجم للخاصية) لا تظهران، لأننا تخطينا الدوال الخاصة (`IsSpecialName`)، تمامًا كما يعرض مستعرض الكائنات الخاصية `Total` مرة واحدة.

## أخطاء شائعة

- **`CS0246` بعد إضافة مرجع Browse:** أضفت المرجع لمشروع آخر، أو نسيت `using`. تأكد من أن المرجع يظهر تحت **Dependencies > Assemblies** في المشروع الصحيح.
- **`Could not load file or assembly` عند التشغيل:** المكتبة غير منسوخة بجانب البرنامج. تأكد من أن **Copy Local** = `True`.
- **`MSB4803: The task "ResolveComReference" is not supported`:** مرجع COM يُبنى بـ `dotnet build`. ثبّت Visual Studio أو Build Tools.
- **`DllNotFoundException`:** المكتبة الأصلية ليست بجانب البرنامج ولا في مسار Windows. انسخها إلى مجلد الإخراج.

## تمرين

البرنامج التالي لا يُبنى: المترجم لا يعرف `DllImport`. أضف السطر الناقص في أول الملف.

```csharp exercise
Console.WriteLine($"Ticks are positive: {Native.GetTickCount64() > 0}");

static class Native
{
    [DllImport("kernel32.dll")]
    public static extern ulong GetTickCount64();
}
```

```csharp solution
using System.Runtime.InteropServices;

Console.WriteLine($"Ticks are positive: {Native.GetTickCount64() > 0}");

static class Native
{
    [DllImport("kernel32.dll")]
    public static extern ulong GetTickCount64();
}
```

```text output
Ticks are positive: True
```

## اختبر نفسك

```quiz
{"question": "في مشروع SDK-style حديث، لماذا لا تحتاج إلى إضافة System.Linq من صفحة Framework؟", "choices": ["لأنه غير موجود", "لأن مكتبات الإطار مضافة ضمنيًا", "لأنه يحتاج حزمة NuGet", "لأنه يعمل في Release فقط"], "answer": 1, "explanation": "المشاريع الحديثة تضيف الإطار كله ضمنيًا، وصفحة Framework تعرض FrameworkReference لإطارات إضافية فقط."}
```

```quiz
{"question": "اخترت kernel32.dll من Browse. ماذا يحدث؟", "choices": ["يُضاف كمرجع عادي", "تشرح الـ IDE أنه مكتبة أصلية تُستدعى بـ DllImport وتعرض نسخه إلى مجلد الإخراج", "يتحول إلى حزمة NuGet", "يُحذف الملف"], "answer": 1, "explanation": "المكتبات الأصلية لا تُضاف كمرجع؛ تُستدعى دوالها بـ DllImport."}
```

```quiz
{"question": "ما الذي يعرضه Object Browser؟", "choices": ["ملفات المشروع فقط", "المكتبات ومساحات الأسماء والأصناف وأعضاءها مع التوثيق", "رسائل البناء", "حزم NuGet المتاحة"], "answer": 1, "explanation": "مستعرض الكائنات يقرأ البيانات الوصفية للمكتبات ويعرض محتواها."}
```

## الخلاصة

- **Reference Manager** بصفحاته: **Assemblies** و**Projects** و**Shared Projects** و**COM** و**Browse**، مع البحث والتعليم ثم **OK**.
- المراجع الدائرية ممنوعة، ومراجع COM تحتاج MSBuild الخاص بـ Visual Studio، والمكتبات الأصلية تُستدعى بـ `DllImport`.
- خصائص المرجع (**Copy Local** و**Specific Version** و...) في نافذة **Properties**، و**Add As Link** لمشاركة ملف واحد.
- **Object Browser** (`Ctrl+Alt+J`) يعرض محتوى أي مكتبة، و**Go To Definition** يفك كودها.
