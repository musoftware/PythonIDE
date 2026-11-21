# الدرس 17: قاموس المصطلحات (إنجليزي - عربي)

هذا القاموس يجمع المصطلحات التي استخدمناها في الدورة، مرتبة حسب الموضوع. ارجع إليه كلما قابلت كلمة إنجليزية في رسالة خطأ أو في كتاب أو موقع.

## أساسيات

| الإنجليزية | العربية | مثال / شرح مختصر |
|---|---|---|
| Program | برنامج | مجموعة تعليمات ينفذها الحاسوب |
| Source code | الكود المصدري | ملفات `.java` التي تكتبها |
| Compiler | المترجم | `javac` يحوّل الكود إلى ملفات `.class` |
| Bytecode | الكود الوسيط | محتوى ملفات `.class` |
| JVM (Java Virtual Machine) | آلة Java الافتراضية | تشغّل الكود الوسيط على أي نظام |
| JDK (Java Development Kit) | حزمة تطوير Java | فيها `javac` و`java` والمكتبات |
| JRE / Runtime | بيئة التشغيل | ما يلزم لتشغيل برامج Java فقط |
| Compile error | خطأ ترجمة | مثل `cannot find symbol` |
| Statement | تعليمة | سطر ينتهي بـ `;` |
| Block | كتلة | ما بين `{ }` |
| Comment | تعليق | `//` و`/* */` و`/** */` |
| Entry point | نقطة البداية | `public static void main(String[] args)` |
| Case sensitive | حساس لحالة الأحرف | `Name` و`name` اسمان مختلفان |

## المتغيرات والأنواع

| الإنجليزية | العربية | مثال |
|---|---|---|
| Variable | متغير | `int age = 20;` |
| Data type | نوع البيانات | `int`، `double`، `String` |
| Primitive type | نوع أساسي | `int`، `double`، `boolean`، `char` |
| Reference type | نوع مرجعي | `String`، المصفوفات، الأصناف |
| Integer | عدد صحيح | `int`، `long` |
| Floating point | عدد عشري | `double` |
| Boolean | منطقي (صح / خطأ) | `boolean` |
| Character | حرف | `char` |
| String | نص | `String` |
| Constant | ثابت | `final double PI = 3.14;` |
| Type inference | استنتاج النوع | `var` |
| Casting | تحويل صريح | `(int) 9.8` |
| Parse | تحويل نص إلى رقم | `Integer.parseInt("5")` |
| Wrapper class | صنف مغلِّف | `Integer` و`Double` حول `int` و`double` |
| Escape sequence | رمز هروب | `\n`، `\t` |
| null | لا شيء (مرجع فارغ) | `String s = null;` |

## العمليات والتحكم

| الإنجليزية | العربية | مثال |
|---|---|---|
| Operator | عامل | `+`، `%`، `==` |
| Expression | تعبير | `a * b + 1` |
| Condition | شرط | `if (x > 0)` |
| Comparison | مقارنة | `<`، `>=`، `.equals()` |
| Logical operators | العوامل المنطقية | `&&`، `\|\|`، `!` |
| Switch expression | تعبير الاختيار | `switch (x) { case 1 -> ... }` |
| Loop | حلقة تكرار | `for`، `while`، `do-while` |
| Enhanced for | حلقة for المحسّنة | `for (int x : nums)` |
| Iteration | دورة / لفّة | كل مرة تنفذ فيها الحلقة |
| Infinite loop | حلقة لا نهائية | `while (true)` بلا `break` |
| break / continue | الخروج / التخطي | داخل الحلقات |

## الدوال

| الإنجليزية | العربية | مثال |
|---|---|---|
| Method | دالة (وتُسمّى أيضًا: طريقة، تابع) | `static int square(int x)` |
| Parameter | معامل | `x` في التعريف |
| Argument | وسيط | `5` في `square(5)` |
| Return value | القيمة المُرجعة | `return x * x;` |
| void | لا ترجع قيمة | `static void hello()` |
| Overloading | التحميل الزائد | دوال بنفس الاسم ومعاملات مختلفة |
| Recursion | الاستدعاء الذاتي | دالة تستدعي نفسها |
| Scope | نطاق المتغير | أين يُرى المتغير |
| Lambda | دالة لامدا | `x -> x * 2` |
| Method reference | مرجع دالة | `Book::title` |

## المصفوفات والمجموعات والنصوص

| الإنجليزية | العربية | مثال |
|---|---|---|
| Array | مصفوفة | `int[] nums = {1, 2, 3};` |
| Index | فهرس / رقم العنصر | يبدأ من `0` |
| Collection | مجموعة | `List`، `Set`، `Map` |
| List | قائمة | `ArrayList<String>` |
| Map / Dictionary | قاموس / خريطة | `HashMap<String, Integer>` |
| Key / Value | مفتاح / قيمة | `map.put("Ali", 90)` |
| Generics | الأنواع العامة | `<String>` في `List<String>` |
| Immutable | غير قابل للتغيير | `String` و`List.of(...)` |
| StringBuilder | باني النصوص | لبناء نص طويل بكفاءة |
| Concatenation | ربط النصوص | `"a" + "b"` |

## البرمجة كائنية التوجه

| الإنجليزية | العربية | مثال |
|---|---|---|
| Object-Oriented Programming (OOP) | البرمجة كائنية التوجه | أصناف وكائنات |
| Class | صنف (ويُسمّى أيضًا: فئة) | `class Car { }` |
| Object / Instance | كائن / نسخة | `new Car()` |
| Field | حقل | `String brand;` |
| Constructor | مُنشئ | `Car(String brand)` |
| this | هذا الكائن | `this.name = name;` |
| Encapsulation | التغليف | حقول `private` مع getters وsetters |
| Getter / Setter | دالة قراءة / دالة كتابة | `getBalance()` / `setText(...)` |
| Access modifier | معدّل الوصول | `public`، `private`، `protected` |
| static | ثابت (خاص بالصنف) | `static int count` |
| Record | سجل | `record Point(int x, int y)` |
| Inheritance | الوراثة | `class Dog extends Animal` |
| Superclass / Subclass | الصنف الأب / الصنف المشتق | `Animal` / `Dog` |
| super | الأب | `super(name)` |
| Override | إعادة التعريف | `@Override` |
| Annotation | علامة توضيحية | `@Override` |
| Polymorphism | تعددية الأشكال | متغير `Shape` يشير إلى `Circle` |
| Abstract class | صنف مجرد | `abstract class Employee` |
| Interface | واجهة | `interface Printable` |
| Package | حزمة (في الكود) | `package com.example;` |
| Import | استيراد | `import java.util.List;` |

## الأخطاء والملفات

| الإنجليزية | العربية | مثال |
|---|---|---|
| Exception | استثناء | `NumberFormatException` |
| Checked exception | استثناء مفحوص | `IOException` |
| Unchecked exception | استثناء غير مفحوص | `NullPointerException` |
| try / catch / finally | جرّب / التقط / أخيرًا | معالجة الاستثناءات |
| throw / throws | ارمِ / يرمي | `throw new IllegalArgumentException()` |
| Stack trace | تتبع المكدس | الأسطر `at Main.main(Main.java:4)` |
| try-with-resources | الإغلاق التلقائي للموارد | `try (BufferedReader r = ...)` |
| File / Path | ملف / مسار | `Path.of("notes.txt")` |
| CSV | قيم مفصولة بفواصل | `Salma,95` |

## الواجهات الرسومية والأدوات

| الإنجليزية | العربية | مثال |
|---|---|---|
| GUI (Graphical User Interface) | واجهة رسومية | نافذة وأزرار |
| Form | نموذج / نافذة | `Form1` |
| Form designer | مصمم النماذج | ترسم فيه النافذة |
| Control | أداة / عنصر تحكم | `Button`، `TextBox`، `Label` |
| Toolbox | صندوق الأدوات | قائمة الأدوات للسحب |
| Properties window | نافذة الخصائص | `Name`، `Text` |
| Event | حدث | `Click`، `Load`، `Tick` |
| Event handler | معالج الحدث | `btnSave_Click` |
| Event-driven | البرمجة بالأحداث | البرنامج ينتظر أفعال المستخدم |
| GUI Bridge | جسر الواجهة | الـ IDE ترسم وبرنامجك يعالج الأحداث |
| Build tool | أداة بناء | Maven وGradle |
| Dependency | مكتبة يعتمد عليها المشروع | `com.google.code.gson:gson:2.11.0` |
| Repository | مستودع | Maven Central |
| Wrapper | سكربت الأداة المرفق | `mvnw` و`gradlew` |
| JAR | ملف Java المضغوط | `libs/gson-2.11.0.jar` |
| Classpath | مسار الأصناف | أين يبحث `java` عن الأصناف والمكتبات |
| Debugger | المصحح | عبر JDWP |
| Breakpoint | نقطة توقف | `F9` |
| Step over / into / out | خطوة فوق / إلى الداخل / إلى الخارج | `F10` / `F11` / `Shift+F11` |

## اختبر نفسك

```quiz
{"question": "ما المصطلح العربي لـ Event handler؟", "choices": ["حدث", "معالج الحدث", "مصمم النماذج", "مُنشئ"], "answer": 1, "explanation": "معالج الحدث هو الدالة التي تعمل عند وقوع الحدث، مثل btnSave_Click."}
```

```quiz
{"question": "ما الفرق بين JDK وJVM؟", "choices": ["لا فرق", "JDK حزمة التطوير (فيها المترجم javac)، وJVM الآلة التي تشغّل الكود الوسيط", "JVM مترجم وJDK محرر نصوص", "JDK خاصة بـ Windows فقط"], "answer": 1, "explanation": "تحتاج JDK لتكتب وتترجم، وJVM (جزء منها) هي التي تشغّل ملفات .class."}
```

```quiz
{"question": "أي كلمة تعني «الوراثة»؟", "choices": ["Inheritance", "Encapsulation", "Polymorphism", "Recursion"], "answer": 0, "explanation": "Inheritance: صنف مشتق يرث حقول ودوال الصنف الأب بـ extends."}
```
