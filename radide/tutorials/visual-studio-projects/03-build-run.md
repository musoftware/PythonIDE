# الدرس 3: البناء والتشغيل والإعدادات (Debug / Release)

فتحنا الحل في الدرس السابق. الآن نبنيه ونشغّله، ونفهم ماذا يحدث خلف الكواليس، وما الفرق بين إعدادَي **Debug** و**Release**.

## البناء (Build): ماذا يعني؟

**البناء** هو تحويل ملفات الكود (`.cs` و`.vb`) إلى ملف قابل للتشغيل (`.exe` أو `.dll`)، مع تنزيل الحزم ونسخ الملفات المطلوبة إلى مجلد الإخراج.

> **تشبيه:** الكود مثل **وصفة الطبخ**، والبناء هو **الطبخ نفسه**: تجمع المكونات (الحزم والمراجع)، وتطبخ حسب الوصفة (الترجمة)، وتضع الطبق في مكانه (`bin\Debug\net8.0\`). وإذا كانت الوصفة فيها خطأ (خطأ ترجمة) يتوقف الطبخ ويخبرك أين المشكلة.

## أوامر البناء

| الأمر | الاختصار | ماذا يفعل |
|---|---|---|
| **Build > Build Solution** (بناء الحل) | `Ctrl+Shift+B` | يبني كل مشاريع الحل بالترتيب الصحيح (المكتبة قبل البرنامج الذي يستخدمها) |
| **Build > Build Project** | | يبني المشروع الحالي فقط |
| **Build > Rebuild Solution** (إعادة بناء الحل) | | ينظف ثم يبني كل شيء من الصفر |
| **Build > Clean Solution** (تنظيف الحل) | | يحذف ملفات الإخراج (`bin` و`obj`) |

وكلها موجودة أيضًا في القائمة السياقية للحل أو للمشروع في **Solution Explorer**.

### ماذا يحدث خلف الكواليس؟

| نوع المشروع | الأمر الذي تنفذه الـ IDE |
|---|---|
| SDK-style (`.csproj` / `.vbproj` / `.fsproj` حديث) | `dotnet build Shop.sln -c Debug` |
| .NET Framework قديم | `MSBuild.exe Shop.sln /p:Configuration=Debug` (من Visual Studio أو Build Tools، تجده الـ IDE عبر `vswhere`) |
| C++ (`.vcxproj`) | MSBuild، أو المترجم MinGW إذا لم يوجد Visual Studio |

تظهر رسائل البناء في نافذة **Output** (المخرجات)، والأخطاء والتحذيرات في **Error List** (قائمة الأخطاء). انقر مرتين على أي خطأ فتنتقل إلى ملفه وسطره.

## التشغيل

| الأمر | الاختصار | ماذا يفعل |
|---|---|---|
| **Debug > Start Debugging / Continue** (بدء تصحيح الأخطاء / متابعة) | `F5` | يبني ثم يشغّل **مشروع بدء التشغيل** مع المصحح |
| **Debug > Start Without Debugging** (بدء بدون تصحيح الأخطاء) | `Ctrl+F5` | يبني ثم يشغّل بلا مصحح (أسرع) |
| **Debug > Stop Debugging** (إيقاف تصحيح الأخطاء) | `Shift+F5` | ينهي البرنامج |

برامج الكونسول تكتب في نافذة **Output**، وتقرأ ما تكتبه أنت فيها إذا استخدم البرنامج `Console.ReadLine()`. أما برامج Windows Forms فتظهر نافذتها كالمعتاد.

## الإعدادات: Debug وRelease

في شريط الأدوات قائمتان منسدلتان كما في Visual Studio:

- **Solution Configurations**: `Debug` أو `Release` (أو أي إعداد آخر معرّف في الحل).
- **Solution Platforms**: `Any CPU` أو `x64` أو `x86`...

| | Debug | Release |
|---|---|---|
| الهدف | التطوير والتصحيح | التوزيع على المستخدمين |
| التحسين (optimization) | معطّل | مفعّل: البرنامج أسرع |
| معلومات التصحيح | كاملة | مختصرة |
| الرمز `DEBUG` معرّف؟ | نعم | لا |
| مجلد الإخراج | `bin\Debug\net8.0\` | `bin\Release\net8.0\` |

اختيارك يُحفظ في إعدادات الـ IDE الخاصة (`%APPDATA%\RADIDE\foreign\`)، وليس في ملفات المشروع.

### مثال: كود يعمل في Debug فقط

الرمز `DEBUG` يسمح بكتابة كود يُترجم في إعداد Debug فقط، مثل رسائل التتبع:

```csharp run
#if DEBUG
Console.WriteLine("الإعداد: Debug (رسائل التتبع مفعّلة)");
#else
Console.WriteLine("الإعداد: Release");
#endif

int total = 0;
for (int i = 1; i <= 4; i++)
{
    total += i * 10;
#if DEBUG
    Console.WriteLine($"  [تتبع] i = {i}, total = {total}");
#endif
}
Console.WriteLine($"المجموع = {total}");
```

```text output
الإعداد: Debug (رسائل التتبع مفعّلة)
  [تتبع] i = 1, total = 10
  [تتبع] i = 2, total = 30
  [تتبع] i = 3, total = 60
  [تتبع] i = 4, total = 100
المجموع = 100
```

جرّب: افتح المثال في المحرر، واختر `Release` من قائمة **Solution Configurations**، ثم `Ctrl+F5`. تختفي أسطر التتبع ويظهر `الإعداد: Release`.

## قراءة أخطاء البناء

إذا كتبت خطأ مثل `Console.WritLine("x");` يتوقف البناء وتظهر في **Error List** رسالة مثل:

```text
Program.cs(3,9): error CS0117: 'Console' does not contain a definition for 'WritLine'
```

| الجزء | معناه |
|---|---|
| `Program.cs(3,9)` | الملف، والسطر 3، والعمود 9 |
| `error` | خطأ يمنع البناء (و`warning` تحذير لا يمنعه) |
| `CS0117` | رقم الخطأ: ابحث عنه في الإنترنت لتجد شرحًا مفصلًا |
| باقي الرسالة | الشرح: `Console` ليس فيها شيء اسمه `WritLine` |

## تمرين

البرنامج التالي لا يُبنى. اقرأ رسالة الخطأ في Error List وأصلحه ليطبع الناتج المتوقع.

```csharp exercise
string[] items = { "قلم", "دفتر", "مسطرة" };
for (int i = 0; i < items.Length; i++)
{
    Console.WriteLine($"{i + 1}. {items[i]}")
}
Console.WriteLine($"العدد: {items.Count}");
```

```csharp solution
string[] items = { "قلم", "دفتر", "مسطرة" };
for (int i = 0; i < items.Length; i++)
{
    Console.WriteLine($"{i + 1}. {items[i]}");
}
Console.WriteLine($"العدد: {items.Length}");
```

```text output
1. قلم
2. دفتر
3. مسطرة
العدد: 3
```

الخطآن: الفاصلة المنقوطة الناقصة (`CS1002: ; expected`)، و`Count` غير موجودة في المصفوفة (`CS1061`)، والصحيح `Length`. ومع `using System.Linq` تصبح `items.Count()` بالأقواس صحيحة أيضًا.

## اختبر نفسك

```quiz
{"question": "ما اختصار Build Solution؟", "choices": ["F5", "Ctrl+F5", "Ctrl+Shift+B", "F9"], "answer": 2, "explanation": "Ctrl+Shift+B يبني الحل، وF5 يبني ويشغّل مع المصحح."}
```

```quiz
{"question": "أي إعداد تختار عند تسليم البرنامج للمستخدمين؟", "choices": ["Debug", "Release", "Any CPU", "Clean"], "answer": 1, "explanation": "Release مفعّل التحسين وأسرع، أما Debug فللتطوير والتصحيح."}
```

```quiz
{"question": "ماذا يعني Program.cs(3,9) في رسالة الخطأ؟", "choices": ["الإصدار 3.9", "الملف Program.cs، السطر 3، العمود 9", "3 أخطاء و9 تحذيرات", "رقم الخطأ"], "answer": 1, "explanation": "الرقمان بين القوسين هما السطر ثم العمود."}
```

## الخلاصة

- **Build Solution** (`Ctrl+Shift+B`)، و**Rebuild** و**Clean** من قائمة **Build** أو الزر الأيمن.
- `F5` تشغيل مع التصحيح، و`Ctrl+F5` بدونه، و`Shift+F5` إيقاف.
- **Debug** للتطوير و**Release** للتوزيع، من قائمة **Solution Configurations** في شريط الأدوات.
- **Error List**: الملف والسطر ورقم الخطأ، وانقر مرتين للانتقال إليه.
