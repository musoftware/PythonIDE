# الدرس 17: قاموس المصطلحات (إنجليزي - عربي)

هذا القاموس يجمع المصطلحات التي استخدمناها في الدورة، مرتبة حسب الموضوع. ارجع إليه كلما قابلت كلمة إنجليزية في رسالة خطأ أو في كتاب أو موقع.

## أساسيات

| الإنجليزية | العربية | مثال / شرح مختصر |
|---|---|---|
| Program | برنامج | مجموعة تعليمات ينفذها الحاسوب |
| Source code | الكود المصدري | ملفات `.cs` التي تكتبها |
| Compiler | المترجم | يحوّل الكود إلى ملف `.dll` |
| Compile error | خطأ ترجمة | مثل `CS0103` |
| Runtime | وقت التشغيل / بيئة التشغيل | .NET Runtime |
| SDK | حزمة التطوير | .NET SDK |
| Statement | تعليمة | سطر ينتهي بـ `;` |
| Block | كتلة | ما بين `{ }` |
| Comment | تعليق | `//` و`/* */` |
| Namespace | فضاء أسماء | `System`، `System.IO` |
| Top-level statements | تعليمات المستوى الأعلى | برنامج بلا `Main` صريح |
| Entry point | نقطة البداية | `static void Main()` |

## المتغيرات والأنواع

| الإنجليزية | العربية | مثال |
|---|---|---|
| Variable | متغير | `int age = 20;` |
| Data type | نوع البيانات | `int`، `double`، `string` |
| Integer | عدد صحيح | `int` |
| Floating point | عدد عشري | `double` |
| Boolean | منطقي (صح / خطأ) | `bool` |
| Character | حرف | `char` |
| String | نص | `string` |
| Constant | ثابت | `const double Pi = 3.14;` |
| Type inference | استنتاج النوع | `var` |
| Casting | تحويل صريح | `(int)9.8` |
| Parse | تحليل / تحويل نص إلى رقم | `int.Parse("5")` |
| String interpolation | استيفاء النصوص | `$"عمري {age}"` |
| Escape sequence | رمز هروب | `\n`، `\t` |

## العمليات والتحكم

| الإنجليزية | العربية | مثال |
|---|---|---|
| Operator | عامل | `+`، `==`، `&&` |
| Expression | تعبير | `a + b * 2` |
| Condition | شرط | `if (x > 0)` |
| Logical operator | عامل منطقي | `&&`، `||`، `!` |
| Ternary operator | العامل الثلاثي | `x > 0 ? "موجب" : "سالب"` |
| Loop | حلقة تكرار | `for`، `while`، `foreach` |
| Iteration | لفّة / تكرار | تنفيذ واحد لجسم الحلقة |
| Infinite loop | حلقة لا نهائية | حلقة لا يصبح شرطها `false` |
| Accumulator | مُراكِم | `sum += x;` |

## الدوال

| الإنجليزية | العربية | مثال |
|---|---|---|
| Method / Function | دالة | `static int Square(int x)` |
| Parameter | معامل | `x` في التعريف |
| Argument | وسيط | `5` في `Square(5)` |
| Return value | القيمة المرجعة | `return x * x;` |
| Overloading | التحميل الزائد | دوال بنفس الاسم ومعاملات مختلفة |
| Optional parameter | معامل اختياري | `int qty = 1` |
| Named argument | وسيط مسمى | `delivery: true` |
| Recursion | الاستدعاء الذاتي | دالة تستدعي نفسها |
| Scope | النطاق | أين يُرى المتغير |
| Lambda expression | تعبير لامدا | `n => n * 2` |

## المجموعات

| الإنجليزية | العربية | مثال |
|---|---|---|
| Array | مصفوفة | `int[] a = { 1, 2 };` |
| Index | فهرس | `a[0]` |
| List | قائمة | `List<string>` |
| Dictionary | قاموس | `Dictionary<string, int>` |
| Key / Value | مفتاح / قيمة | `stock["أقلام"] = 120` |
| Generic | عام / قالبي | `List<T>` |
| LINQ | استعلامات LINQ | `Where`، `Select`، `Sum` |

## البرمجة كائنية التوجه

| الإنجليزية | العربية | مثال |
|---|---|---|
| Class | صنف | `class Car` |
| Object / Instance | كائن / نسخة | `new Car()` |
| Field | حقل | `public string Brand;` |
| Property | خاصية | `public int Age { get; set; }` |
| Constructor | مُنشئ | `public Car(string brand)` |
| Encapsulation | التغليف | `private` + خصائص |
| Access modifier | معدّل الوصول | `public`، `private`، `protected` |
| Static member | عضو ثابت | `static int Count` |
| Inheritance | الوراثة | `class Dog : Animal` |
| Base / Derived class | صنف أساسي / مشتق | `Animal` / `Dog` |
| Polymorphism | تعدد الأشكال | `virtual` + `override` |
| Abstract class | صنف مجرد | `abstract class Shape` |
| Interface | واجهة | `interface IPayable` |
| Record | سجل | `record Person(string Name)` |

## الأخطاء والملفات

| الإنجليزية | العربية | مثال |
|---|---|---|
| Exception | استثناء | `FormatException` |
| Throw | يرمي | `throw new ArgumentException(...)` |
| Catch | يلتقط | `catch (Exception ex)` |
| Stack trace | تتبع المكدس | سلسلة الدوال عند حدوث الخطأ |
| File path | مسار الملف | `@"C:\data\notes.txt"` |
| Stream | تدفق | `StreamWriter` |
| Encoding | ترميز | UTF-8 |

## الواجهات الرسومية والأدوات

| الإنجليزية | العربية | مثال |
|---|---|---|
| Form | نموذج / نافذة | `Form1` |
| Control | أداة / عنصر تحكم | `Button`، `TextBox` |
| Form designer | مصمم النماذج | رسم النافذة بالفأرة |
| Toolbox | صندوق الأدوات | قائمة الأدوات للسحب |
| Properties window | نافذة الخصائص | `Name`، `Text` |
| Event | حدث | `Click`، `Load`، `Tick` |
| Event handler | معالج الحدث | `btnSave_Click` |
| Event-driven | البرمجة بالأحداث | البرنامج ينتظر أفعال المستخدم |
| GUI Bridge | جسر الواجهة | الـ IDE ترسم وبرنامجك يعالج الأحداث |
| Package | حزمة | من NuGet |
| Debugger | المصحح | netcoredbg |
| Breakpoint | نقطة توقف | `F9` |
| Step over / into / out | خطوة فوق / إلى الداخل / إلى الخارج | `F10` / `F11` / `Shift+F11` |
| Solution / Project | حل / مشروع | `.sln` / `.csproj` |

## اختبر نفسك

```quiz
{"question": "ما المصطلح العربي لـ Event handler؟", "choices": ["حدث", "معالج الحدث", "مصمم النماذج", "مُنشئ"], "answer": 1, "explanation": "معالج الحدث هو الدالة التي تعمل عند وقوع الحدث، مثل btnSave_Click."}
```

```quiz
{"question": "ما معنى Argument في الدوال؟", "choices": ["المعامل في التعريف", "القيمة المرسلة عند الاستدعاء", "نوع الإرجاع", "اسم الدالة"], "answer": 1, "explanation": "المعامل (parameter) في التعريف، والوسيط (argument) هو القيمة الفعلية عند الاستدعاء."}
```

```quiz
{"question": "أي كلمة تعني «تعدد الأشكال»؟", "choices": ["Inheritance", "Encapsulation", "Polymorphism", "Recursion"], "answer": 2, "explanation": "Polymorphism: كائنات مختلفة تستجيب لنفس الاستدعاء كلٌّ بطريقته."}
```
