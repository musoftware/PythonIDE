# الدرس 13: قاموس المصطلحات (إنجليزي - عربي)

أهم المصطلحات التي مرت بك في دورة Dart وFlutter، مع مثال لكل منها. ارجع إلى هذه الصفحة كلما نسيت معنى كلمة.

## أساسيات

| English | العربية | مثال في Dart |
|---|---|---|
| variable | متغير | `var count = 0;` |
| type | نوع | `int`، `double`، `String`، `bool` |
| type inference | استنتاج النوع | `var name = 'علي';` |
| final / const | قيمة لا تتغير / ثابت وقت الكتابة | `final x = 1;` / `const pi = 3.14;` |
| string interpolation | استيفاء النص | `'العمر: $age'`، `'${a + b}'` |
| comment | تعليق | `// ...` و`/* ... */` |
| integer division | قسمة صحيحة | `7 ~/ 2` |
| statement / semicolon | جملة / فاصلة منقوطة | `print('x');` |

## التحكم

| English | العربية | مثال |
|---|---|---|
| condition | شرط | `if (x > 0) { }` |
| conditional operator | العامل الشرطي | `a > b ? a : b` |
| switch expression | تعبير الاختيار | `switch (x) { 1 => 'واحد', _ => '؟' }` |
| loop | حلقة تكرار | `for`، `for-in`، `while`، `do-while` |
| break / continue | اخرج من الحلقة / تخطَّ للدورة التالية | |

## الدوال

| English | العربية | مثال |
|---|---|---|
| function | دالة | `int square(int x) { return x * x; }` |
| arrow function | دالة سهمية | `int square(int x) => x * x;` |
| parameter / argument | معامل / وسيط | |
| named parameter | معامل مسمى | `f({required String name})` |
| optional positional parameter | معامل موضعي اختياري | `f([int n = 1])` |
| default value | قيمة افتراضية | `int seats = 1` |
| anonymous function | دالة مجهولة | `(x) => x * 2` |
| return value | القيمة المرجعة | `return total;` |
| scope | نطاق | متغير محلي أو على مستوى الملف |

## المجموعات

| English | العربية | مثال |
|---|---|---|
| list | قائمة | `[1, 2, 3]` |
| index | فهرس (رقم العنصر) | `names[0]` |
| map | قاموس (مفتاح وقيمة) | `{'شاي': 10}` |
| set | مجموعة (بلا تكرار) | `{'أ', 'ب'}` |
| iterable | قابل للمرور عليه | ناتج `map` و`where` |
| spread operator | عامل النشر | `[...a, ...b]` |
| cascade operator | عامل التتالي | `list..add(1)..sort()` |
| generic type | نوع عام | `List<String>`، `Map<String, int>` |

## الأمان من القيم الفارغة

| English | العربية | مثال |
|---|---|---|
| null | لا شيء (قيمة غائبة) | `null` |
| null safety | الأمان من القيم الفارغة | `String` لا يقبل `null` |
| nullable type | نوع يقبل القيمة الفارغة | `String?` |
| if-null operator | عامل القيمة البديلة | `name ?? 'ضيف'` |
| null-aware access | الوصول الآمن | `name?.length` |
| null assertion | تأكيد عدم الفراغ | `value!` |
| late | سيُعطى قيمة لاحقًا | `late String msg;` |

## الفئات والكائنات

| English | العربية | مثال |
|---|---|---|
| class | فئة | `class Student { }` |
| object / instance | كائن / نسخة | `Student('مريم', 11)` |
| field / property | خاصية | `name` |
| method | دالة الكائن (طريقة) | `introduce()` |
| constructor | باني | `Student(this.name, this.grade);` |
| factory constructor | باني مصنع | `factory Task.fromJson(...)` |
| getter / setter | دالة قراءة / دالة كتابة | `double get area => w * h;` |
| private | خاص | `_balance` |
| encapsulation | التغليف | حماية البيانات بدوال |
| inheritance | الوراثة | `class Cat extends Animal` |
| override | إعادة تعريف | `@override void speak()` |
| abstract class | فئة مجردة | `abstract class Shape` |
| polymorphism | تعدد الأشكال | قائمة `Animal` فيها قطط وكلاب |
| enum | قائمة قيم محددة | `enum Level { easy, hard }` |

## الأخطاء والبرمجة غير المتزامنة

| English | العربية | مثال |
|---|---|---|
| exception | استثناء (خطأ أثناء التشغيل) | `FormatException` |
| try / catch / finally | جرّب / التقط / أخيرًا | `try { } catch (e) { }` |
| throw | ارمِ خطأ | `throw ArgumentError('...')` |
| asynchronous | غير متزامن | عمل ننتظره دون تجميد البرنامج |
| Future | قيمة مستقبلية (وعد) | `Future<String>` |
| async / await | دالة غير متزامنة / انتظر | `final d = await load();` |
| Stream | سلسلة قيم تصل تباعًا | `await for (final x in s)` |
| JSON | صيغة نصية للبيانات | `jsonEncode` / `jsonDecode` |

## الواجهات الرسومية و Flutter

| English | العربية | مثال |
|---|---|---|
| form | نموذج (نافذة) | `Form1` |
| control | أداة / عنصر تحكم | `Button`، `TextBox`، `Label` |
| event | حدث | `Click`، `Load`، `Tick` |
| event handler | معالج الحدث | `void btnOk_Click(RadEvent e)` |
| GUI Bridge | جسر الواجهة | الـ IDE ترسم النافذة وبرنامجك يستقبل الأحداث |
| form designer | مصمم النماذج | ترسم فيه النافذة أو شاشة الهاتف |
| widget | ودجة (عنصر واجهة) | `Text`، `Column`، `ElevatedButton` |
| widget tree | شجرة الودجات | ودجات داخل ودجات |
| state | الحالة | البيانات التي تتغير على الشاشة |
| StatelessWidget / StatefulWidget | ودجة بلا حالة / ودجة لها حالة | |
| setState | أعد الرسم بعد تغيير الحالة | `setState(() => count++)` |
| hot reload | إعادة التحميل السريع | ترى تعديلك فورًا دون إعادة التشغيل |
| package | حزمة (مكتبة) | `package:flutter/material.dart` |

## اختبر نفسك

```quiz
{"question": "ما معنى String? في Dart؟", "choices": ["نص طويل", "نص قد يكون null", "سؤال للمستخدم", "نص ثابت"], "answer": 1, "explanation": "علامة ? بعد النوع تعني أنه يقبل القيمة الفارغة null."}
```

```quiz
{"question": "ما المقابل العربي لكلمة widget في هذه الدورة؟", "choices": ["حدث", "ودجة (عنصر واجهة)", "متغير", "حلقة تكرار"], "answer": 1, "explanation": "الودجة هي أي جزء من واجهة Flutter."}
```

## ماذا بعد؟

- تابع **«دليل تطبيقات الموبايل بـ Flutter في RAD IDE»**: القوائم، والشاشات المتعددة، والمؤقتات، والصور، والبناء للهاتف.
- جرّب **Flutter Designer** لتصميم الشاشات بودجات Flutter الأصلية.
- اقرأ توثيق Dart الرسمي على `dart.dev` وتوثيق Flutter على `flutter.dev`.
