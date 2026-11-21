# الدرس 1: ما معنى «فتح المشروع في مكانه»؟

لديك مشروع كتبته في **Visual Studio** (أو نزّلته من GitHub)، وتريد أن تكمل العمل عليه في **RAD IDE**: تعدّل الكود، وتصمم النوافذ، وتبني وتشغّل وتصحح الأخطاء. هذا الدليل يشرح لك ذلك خطوة بخطوة.

> **تشبيه:** تخيّل أنك استعرت **دفتر محاضرات** من زميلك. هناك طريقتان: أن **تنسخ** الدفتر كله بخطك في دفتر جديد (هذا هو **الترحيل**)، أو أن **تكتب في نفس الدفتر** بقلم من نفس اللون، فيرجع إليه زميلك ولا يلاحظ أي فرق إلا ما أضفته أنت (هذا هو **الفتح في المكان**).

## الفتح في المكان (Open in place)

عندما تفتح ملف `.sln` أو `.csproj` أو `.vbproj` في RAD IDE:

- **لا تُنشأ أي ملفات خاصة بالـ IDE** داخل مجلد مشروعك: لا `project.radproj` ولا `.radsln`.
- إعدادات الـ IDE الخاصة (مشروع بدء التشغيل المختار، والإعداد الحالي `Debug` أو `Release`) تُحفظ بعيدًا في `%APPDATA%\RADIDE\foreign\`.
- عند تعديل ملف المشروع (إضافة ملف، أو حزمة NuGet، أو مرجع) يُعدَّل **النص** فقط في المكان المطلوب، وتبقى التعليقات والترتيب والمسافات كما هي.
- إذا فتحت نموذجًا وحفظته **دون تغيير** يبقى الملف مطابقًا **بايتًا ببايت** للأصل.

النتيجة: تستطيع أن تفتح نفس المشروع في Visual Studio وفي RAD IDE بالتناوب، أو يعمل عليه زميلك في Visual Studio وأنت في RAD IDE، ويبقى نظام التحكم بالإصدارات (Git) نظيفًا.

## الترحيل (Migration)

أحيانًا تريد العكس: **مشروعًا جديدًا** بلغة أو تقنية أخرى، مثل تحويل برنامج Windows Forms إلى Python، أو إلى مشروع **C# (GUI Bridge)** في RAD IDE. هذا عمل **معالج الترحيل** (**File > Migrate Project...** / ملف > ترحيل المشروع...)، وسنتعرف عليه في الدرس 8. الترحيل يكتب مشروعًا جديدًا ولا يلمس الأصل.

| | الفتح في المكان | الترحيل |
|---|---|---|
| الأمر | **File > Open Project...** | **File > Migrate Project...** |
| ملفات المشروع الأصلي | تبقى كما هي وتُعدَّل عند الحاجة | لا تُلمس |
| الناتج | نفس المشروع | مشروع جديد في مجلد جديد |
| يبقى صالحًا لـ Visual Studio؟ | نعم | الأصل نعم، والجديد مشروع RAD IDE |

## ماذا تدعم RAD IDE من مشاريع Visual Studio؟

| النوع | الملف | البناء | التصحيح |
|---|---|---|---|
| حل (Solution) | `.sln` و`.slnx` | كل المشاريع بالترتيب | - |
| C# حديث (SDK-style) | `.csproj` | `dotnet build` | netcoredbg |
| VB.NET حديث | `.vbproj` | `dotnet build` | netcoredbg |
| F# | `.fsproj` | `dotnet build` | netcoredbg |
| .NET Framework قديم (non-SDK) | `.csproj` / `.vbproj` | MSBuild من Visual Studio أو Build Tools | - |
| C++ | `.vcxproj` | MSBuild، أو MinGW إذا لم يوجد | - |

وفوق ذلك: نماذج **Windows Forms** (`Form1.cs` مع `Form1.Designer.cs`، أو `Form1.vb` مع `Form1.Designer.vb`) تُفتح في **مصمم النماذج** نفسه الذي تعرفه من RAD IDE (الدرس 4).

## ما تحتاجه على جهازك

- **.NET SDK** (الإصدار 8 أو أحدث): `winget install Microsoft.DotNet.SDK.8`. تأكد بالأمر `dotnet --version` في **Terminal** (الطرفية).
- للمشاريع القديمة (.NET Framework) و`.vcxproj`: **Visual Studio** أو **Build Tools for Visual Studio**. الـ IDE تجد MSBuild تلقائيًا عبر `vswhere`.
- للتصحيح: **netcoredbg** (الدرس 7).

## جرّب الآن: أصغر مشروع Visual Studio

كل مثال `csharp run` في هذا الدليل هو **مشروع Visual Studio حقيقي**: عند الضغط على «جرّبه» تنشئ الـ IDE مجلدًا فيه `Lesson.csproj` و`Program.cs`، ثم تفتحه في مكانه وتبنيه بـ `dotnet build`. افتح نفس المجلد لاحقًا في Visual Studio وسيعمل كما هو.

```csharp run
Console.WriteLine("مرحبًا من مشروع Visual Studio داخل RAD IDE");
Console.WriteLine($"نوع المشروع: {(OperatingSystem.IsWindows() ? "Windows" : "آخر")} / .NET");
Console.WriteLine($"اسم البرنامج: {typeof(Program).Assembly.GetName().Name}");
```

```text output
مرحبًا من مشروع Visual Studio داخل RAD IDE
نوع المشروع: Windows / .NET
اسم البرنامج: Lesson
```

> **ملحوظة:** اسم البرنامج `Lesson` يأتي من اسم ملف المشروع `Lesson.csproj` (الخاصية `AssemblyName` تساويه افتراضيًا).

## اختبر نفسك

```quiz
{"question": "ماذا يعني فتح مشروع Visual Studio «في مكانه»؟", "choices": ["نسخه إلى مشروع RAD IDE جديد", "العمل على نفس الملفات دون إضافة ملفات خاصة بالـ IDE", "تحويله إلى Python", "فتحه للقراءة فقط"], "answer": 1, "explanation": "الفتح في المكان يترك المشروع صالحًا لـ Visual Studio، وإعدادات الـ IDE تُحفظ في %APPDATA%\\RADIDE\\foreign."}
```

```quiz
{"question": "أي أمر يكتب مشروعًا جديدًا ولا يلمس الأصل؟", "choices": ["File > Open Project...", "File > Open Folder...", "File > Migrate Project...", "Build > Build Solution"], "answer": 2, "explanation": "معالج الترحيل يكتب مشروعًا جديدًا، أما Open Project فيفتح المشروع في مكانه."}
```

```quiz
{"question": "ماذا تستخدم الـ IDE لبناء مشروع .NET Framework قديم (non-SDK)؟", "choices": ["dotnet build دائمًا", "MSBuild من Visual Studio أو Build Tools", "javac", "لا يمكن بناؤه"], "answer": 1, "explanation": "المشاريع القديمة تحتاج MSBuild الخاص بـ Visual Studio، وتجده الـ IDE عبر vswhere."}
```

## الخلاصة

- **الفتح في المكان**: نفس الملفات، بلا ملفات إضافية، وتعديلات نصية دقيقة تحافظ على كل شيء.
- **الترحيل**: مشروع جديد بلغة أو تقنية أخرى، والأصل لا يُلمس.
- RAD IDE تدعم `.sln` و`.csproj` و`.vbproj` و`.fsproj` و`.vcxproj` ونماذج Windows Forms.
