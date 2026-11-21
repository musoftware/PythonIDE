# الدرس 15: قاموس المصطلحات (إنجليزي - عربي)

هذه أهم المصطلحات التي مرت بك في الدورة، مرتبة حسب الموضوع. ارجع إليها كلما قابلت كلمة في رسالة خطأ أو في مقال إنجليزي.

## أساسيات اللغة

| English | العربية | مثال في Ruby |
|---|---|---|
| variable | متغير | `age = 20` |
| constant | ثابت | `PI = 3.14` |
| string | نص | `"مرحبا"` |
| integer / float | عدد صحيح / عدد عشري | `42` / `3.5` |
| boolean | قيمة منطقية | `true` / `false` |
| nil | لا شيء (قيمة فارغة) | `nil` |
| symbol | رمز | `:title` |
| interpolation | استيفاء (وضع قيمة داخل نص) | `"#{x}"` |
| comment | تعليق | `# ...` |
| operator | عامل | `+` `==` `&&` |
| expression | تعبير | `a * 2 + 1` |

## التحكم في سير البرنامج

| English | العربية | مثال |
|---|---|---|
| condition | شرط | `if x > 0` |
| loop | حلقة تكرار | `while` / `each` / `times` |
| range | مدى | `1..10` |
| iteration | دورة (من دورات الحلقة) | |
| break / next | اخرج من الحلقة / تخطَّ الدورة | |
| infinite loop | حلقة لا نهائية | |

## المجموعات

| English | العربية | مثال |
|---|---|---|
| array | مصفوفة | `[1, 2, 3]` |
| index | فهرس (رقم العنصر) | `a[0]` |
| hash | قاموس (مفتاح وقيمة) | `{ name: "علي" }` |
| key / value | مفتاح / قيمة | |
| element | عنصر | |

## الدوال والكتل

| English | العربية | مثال |
|---|---|---|
| method / function | دالة | `def greet(name)` |
| parameter / argument | معامل / وسيط (القيمة الممررة) | `greet("سارة")` |
| return value | القيمة المرجعة | |
| keyword argument | معامل مسمّى | `size: "كبير"` |
| block | كتلة | `{ \|x\| x * 2 }` |
| yield | نفّذ الكتلة الممررة | |
| lambda | دالة مجهولة | `->(x) { x + 1 }` |
| scope | نطاق (مكان رؤية المتغير) | |

## البرمجة كائنية التوجه

| English | العربية | مثال |
|---|---|---|
| class | صنف | `class Book` |
| object / instance | كائن / نسخة | `Book.new` |
| constructor | مُنشئ | `initialize` |
| instance variable | متغير الكائن | `@title` |
| attribute / accessor | خاصية | `attr_accessor :title` |
| inheritance | وراثة | `class Cat < Animal` |
| polymorphism | تعدد الأشكال | |
| module / mixin | وحدة / خلط | `include Greeter` |

## الأخطاء والملفات

| English | العربية |
|---|---|
| exception | استثناء (خطأ أثناء التشغيل) |
| rescue / raise | التقاط الخطأ / إثارة خطأ |
| syntax error | خطأ في كتابة الكود (قواعد اللغة) |
| undefined method | دالة غير معرّفة |
| file / path | ملف / مسار |

## الواجهات الرسومية

| English | العربية |
|---|---|
| form | نموذج (نافذة) |
| control | أداة / عنصر تحكم |
| event / event handler | حدث / معالج حدث |
| property | خاصية (مثل `Text` و`Enabled`) |
| Form Designer | مصمم النماذج |
| Toolbox | صندوق الأدوات |
| GUI Bridge | جسر الواجهة |

## Ruby on Rails

| English | العربية |
|---|---|
| framework | إطار عمل |
| MVC: Model / View / Controller | نموذج / عرض / متحكم |
| route | مسار (رابط ومتحكمه) |
| action | إجراء (دالة في المتحكم) |
| generator / scaffold | مولّد / هيكل كامل |
| migration | ترحيل (تغيير في بنية قاعدة البيانات) |
| validation | قاعدة تحقق |
| association | علاقة (`has_many` / `belongs_to`) |
| seed | بيانات أولية |
| template / partial / layout | قالب / عرض جزئي / تخطيط |
| helper | دالة مساعدة |
| escape (HTML) | تهريب الرموز الخاصة |
| console | الطرفية التفاعلية |
| debugger / breakpoint | مصحح / نقطة توقف |
| test / assertion | اختبار / تأكيد |
| gem / bundle | حزمة Ruby / تثبيت حزم المشروع |
| credentials | الأسرار المشفرة |

## اختبر نفسك

```quiz
{"question": "ما معنى migration في Rails؟", "choices": ["نقل الموقع إلى خادم آخر", "ملف يصف تغييرًا في بنية قاعدة البيانات", "ترجمة الموقع", "نسخة احتياطية"], "answer": 1, "explanation": "الترحيل (migration) يصف تغييرًا مثل إنشاء جدول أو إضافة عمود، ويُنفذ بـ db:migrate."}
```

```quiz
{"question": "ما الترجمة الأنسب لـ event handler؟", "choices": ["معالج حدث", "مدير ملفات", "حلقة تكرار", "خاصية"], "answer": 0, "explanation": "event handler هو الدالة التي تعمل عند وقوع حدث، مثل btnSave_Click."}
```

## إلى أين بعد ذلك؟

- طوّر مشروع المهام (الدرس 10) أو تطبيق المكتبة (الدروس 11 إلى 14) بأفكارك.
- اقرأ دليل Rails الرسمي: guides.rubyonrails.org.
- جرّب دورات أخرى في **Help > Tutorials (Arabic lessons)...**، فكثير من الأفكار تتكرر بين اللغات.
