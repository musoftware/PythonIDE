# الدرس 2: إنشاء حل ومكتبة أصناف ومشروع البدء

**في هذا الدرس ستتعلم:**

- إنشاء حل جديد من نافذة **New Project**.
- إنشاء **مكتبة أصناف** (Class Library): مشروع بلا نوافذ، دوال فقط.
- إضافة مشروع جديد أو موجود إلى الحل.
- تعيين **مشروع البدء** وإزالة مشروع من الحل.

## الخطوة 1: الحل والمشروع الأول

افتح **File > New Project...** (`Ctrl+Shift+N`، بالعربية: **ملف > مشروع جديد...**). في النافذة:

| الجزء | ماذا تختار |
|---|---|
| شجرة اللغات (يسارًا) | اللغة، مثلًا **Python (Tkinter)** |
| القوالب (وسطًا) | **Windows Application** (تطبيق Windows)، أو **Console Application**، أو **Class Library** ... |
| **Name** (الاسم) | اسم المشروع، مثل `App` |
| **Location** (الموقع) | المجلد الذي يُنشأ فيه |
| **Solution** (الحل) | **Create new solution** (إنشاء حل جديد)، أو **Add to solution '...'** إذا كان عندك حل مفتوح |
| **Solution name** (اسم الحل) | مثل `Shop` |
| **Place solution and project in the same directory** | ضعها إذا أردت مجلدًا واحدًا (لحل بمشروع واحد) |

اضغط **OK**. يُنشأ مجلد `Shop` فيه `Shop.radsln` ومجلد `App`.

> **نصيحة:** في حل سيضم عدة مشاريع، **لا** تضع علامة «same directory»، ليكون لكل مشروع مجلده داخل مجلد الحل.

## الخطوة 2: مكتبة الأصناف

**مكتبة الأصناف** (Class Library، بالعربية في الواجهة: مكتبة أصناف، وتُسمّى أيضًا مكتبة فئات) مشروع **بلا نماذج**: ملف كود واحد فيه **دوال عامة** تستخدمها المشاريع الأخرى.

لإضافتها إلى الحل المفتوح:

- **File > Add > New Project...** (ملف > إضافة > مشروع جديد...)، أو
- بالزر الأيمن على **Solution 'Shop'** في Solution Explorer > **Add > New Project...**.

اختر اللغة (مثلًا **C# (GUI Bridge, .NET)**)، والقالب **Class Library**، والاسم `PriceLib`، وفي **Solution** اختر **Add to solution 'Shop'**.

تُنشئ البيئة الملف `PriceLib.cs` وفيه دالة مثال. في C#، **الدوال العامة الساكنة** (`public static`) داخل الصنف هي دوال المكتبة:

```csharp
// Class Library PriceLib. Its public static methods are the library's public functions:
// a project that references PriceLib (Add Reference) calls them as native code -
//     PriceLib.Add(2, 3)   in C#, Python, Java, JavaScript ...   PriceLib_Add(2, 3) in Ring
// Arguments and results are JSON values: numbers, strings, bools, null, lists, dictionaries.
public static class PriceLib
{
    ...
    /// <summary>Returns a greeting.</summary>
    public static string Greet(string name) => $"Hello, {name}!";
}
```

وفي Python مثلًا، الدوال العامة هي كل دالة في الملف لا يبدأ اسمها بشرطة سفلية `_`.

## الخطوة 3: مشروع البدء

مكتبة الأصناف **لا تعمل وحدها**. إذا جعلتها مشروع البدء وضغطت `F5`، تظهر رسالة: «A project with an Output Type of Class Library cannot be started directly»، تمامًا مثل Visual Studio.

لتعيين مشروع البدء: بالزر الأيمن على المشروع `App` > **Set as StartUp Project** (تعيين كمشروع بدء التشغيل)، أو **Project > Set as StartUp Project**. يظهر اسمه بخط عريض.

## إضافة مشروع موجود وإزالته

- **File > Add > Existing Project...** (مشروع موجود...): اختر مجلدًا فيه `project.radproj`. المشروع يبقى في مكانه، ويُضاف مساره إلى الحل.
- بالزر الأيمن على مشروع > **Remove from Solution** (إزالة من الحل): يُزال من الحل فقط، و**ملفاته تبقى** على القرص. والمشاريع التي كانت تستخدمه تُحذف منها مراجعه.

ولإغلاق الحل كله: **File > Close Solution**.

## مثال: هل يمكن تشغيل هذا المشروع؟

هذا مثال يتحقق من مشروع البدء قبل التشغيل، بنفس منطق البيئة: لا يوجد مشروع بدء، أو مشروع البدء مكتبة:

```python run
projects = {"App": "application", "PriceLib": "library"}

def can_start(startup):
    if startup not in projects:
        return "الحل ليس فيه مشروع للتشغيل"
    if projects[startup] == "library":
        return "مكتبة الأصناف لا تعمل وحدها: اختر مشروعًا آخر كمشروع البدء"
    return "يعمل: " + startup

print(can_start("App"))
print(can_start("PriceLib"))
print(can_start(""))
```

```text output
يعمل: App
مكتبة الأصناف لا تعمل وحدها: اختر مشروعًا آخر كمشروع البدء
الحل ليس فيه مشروع للتشغيل
```

## أخطاء شائعة

- **إنشاء المكتبة كحل جديد منفصل:** تأكد أن **Solution** هو **Add to solution '...'**، وإلا صار عندك حلان منفصلان.
- **F5 والمكتبة هي مشروع البدء:** عيّن مشروع التطبيق كمشروع البدء.
- **دالة خاصة في المكتبة:** في C# يجب أن تكون `public static`، وفي Python ألا يبدأ اسمها بـ `_`. غير ذلك لا يراه المشروع الآخر.
- **الظن أن Remove from Solution يحذف الملفات:** لا يحذفها، بل يزيل المشروع من الحل فقط.

## تمرين

### تمرين 1: الدوال العامة في مكتبة Python

في مكتبات Python، الدوال العامة هي التي لا يبدأ اسمها بـ `_`. اكتب برنامجًا يطبع أسماء الدوال العامة فقط من القائمة.

```python exercise
functions = ["add", "_helper", "greet", "__init__", "total"]
# اطبع الدوال العامة فقط
```

```python solution
functions = ["add", "_helper", "greet", "__init__", "total"]
for f in functions:
    if not f.startswith("_"):
        print(f)
```

```text output
add
greet
total
```

### تمرين 2 (عملي في البيئة)

أنشئ حلًا اسمه `Shop` فيه مشروع **Python (Tkinter)** اسمه `App`. ثم أضف إليه مكتبة **Class Library** بلغة **C# (GUI Bridge, .NET)** اسمها `PriceLib`. جرّب أن تجعل `PriceLib` مشروع البدء واضغط `F5` لترى الرسالة، ثم أرجع `App` مشروعًا للبدء.

## اختبر نفسك

```quiz
{"question": "ما مكتبة الأصناف (Class Library)؟", "choices": ["مشروع فيه نوافذ فقط", "مشروع بلا نماذج فيه دوال عامة تستخدمها المشاريع الأخرى", "ملف إعدادات", "مجلد صور"], "answer": 1, "explanation": "المكتبة دوال فقط، ولا تعمل وحدها."}
```

```quiz
{"question": "أي دالة C# تظهر لمشروع يستخدم المكتبة؟", "choices": ["private static", "public static داخل الصنف", "أي دالة", "الدوال التي تبدأ بـ _"], "answer": 1, "explanation": "الدوال العامة الساكنة هي دوال المكتبة."}
```

```quiz
{"question": "ماذا يحدث لملفات المشروع عند Remove from Solution؟", "choices": ["تُحذف", "تبقى على القرص، ويُزال المشروع من الحل فقط", "تنتقل إلى سلة المحذوفات", "تُضغط في zip"], "answer": 1, "explanation": "الإزالة من الحل لا تحذف الملفات."}
```

## الخلاصة

- **File > New Project...**: اللغة، والقالب، والاسم، و**Create new solution** أو **Add to solution**.
- **Class Library**: دوال عامة بلا نماذج، ولا تعمل وحدها.
- **Set as StartUp Project** يحدد ما يعمل عند `F5`.
- **File > Add > New/Existing Project...** و**Remove from Solution** لإدارة المشاريع.
