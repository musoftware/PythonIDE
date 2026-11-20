# الدرس 3: المتغيرات وأنواع البيانات

البرامج تتعامل مع بيانات: أعمار، وأسعار، وأسماء، ودرجات. لكي نحفظ هذه البيانات نستخدم **المتغيرات** (Variables).

## ما هو المتغير؟

> **تشبيه:** المتغير مثل **علبة** عليها ملصق باسم. العلبة لها **نوع** محدد (علبة للأحذية لا تصلح للماء!)، وبداخلها **قيمة** يمكن تغييرها.

لتعريف متغير نكتب: **النوع** ثم **الاسم** ثم القيمة الأولى:

```cpp
int age = 20;
```

- `int` النوع: عدد صحيح.
- `age` الاسم.
- `20` القيمة الابتدائية.

## الأنواع الأساسية

| النوع | يخزّن | مثال |
|---|---|---|
| `int` | عدد صحيح | `int count = 15;` |
| `double` | عدد بكسور عشرية | `double price = 99.5;` |
| `char` | حرف واحد (إنجليزي) | `char grade = 'A';` |
| `bool` | صح أو خطأ | `bool passed = true;` |
| `std::string` | نص | `std::string name = "منى";` |

لاحظ أن الحرف الواحد `char` يُكتب بين علامتي تنصيص **مفردة** `'A'`، أما النص فبين علامتين **مزدوجتين** `"..."`. ولاستخدام `std::string` نضيف `#include <string>`.

```cpp run
#include <iostream>
#include <string>

int main()
{
    int age = 20;
    double height = 1.75;
    char grade = 'A';
    bool isStudent = true;
    std::string name = "منى";

    std::cout << "الاسم: " << name << "\n";
    std::cout << "العمر: " << age << "\n";
    std::cout << "الطول: " << height << " متر\n";
    std::cout << "التقدير: " << grade << "\n";
    std::cout << "طالبة؟ " << isStudent << "\n";
    return 0;
}
```

```text output
الاسم: منى
العمر: 20
الطول: 1.75 متر
التقدير: A
طالبة؟ 1
```

لاحظ أن `true` تُطبع `1` و`false` تُطبع `0`. لطباعتها كلمة، استخدم `std::boolalpha`:

```cpp
std::cout << std::boolalpha << isStudent; // يطبع true
```

## تغيير قيمة المتغير

اسمه «متغير» لأن قيمته تتغير:

```cpp run
#include <iostream>

int main()
{
    int score = 10;
    std::cout << "البداية: " << score << "\n";

    score = 25;            // قيمة جديدة
    std::cout << "بعد التغيير: " << score << "\n";

    score = score + 5;     // خذ القيمة الحالية وأضف 5
    std::cout << "بعد الإضافة: " << score << "\n";
    return 0;
}
```

```text output
البداية: 10
بعد التغيير: 25
بعد الإضافة: 30
```

> **انتبه:** العلامة `=` في البرمجة معناها **«ضَع»** (إسناد) وليس «يساوي» كما في الرياضيات. `score = score + 5` تعني: احسب `score + 5` ثم ضع الناتج في `score`.

## التهيئة بالأقواس المعقوصة `{}`

في C++ الحديثة يمكن تعريف المتغير بهذا الشكل:

```cpp
int count{5};
double rate{0.15};
std::string city{"الإسكندرية"};
int zero{};   // قيمته صفر
```

ميزة الأقواس `{}` أنها تمنعك من الأخطاء الخفية؛ مثلًا وضع عدد عشري في متغير صحيح (سنرى رسالة الخطأ بالأسفل).

## الكلمة `auto`

أحيانًا يستنتج المترجم النوع بنفسه من القيمة:

```cpp
auto x = 10;      // int
auto pi = 3.14;   // double
auto ok = true;   // bool
```

`auto` مفيدة جدًا مع الأنواع الطويلة لاحقًا، لكن في البداية اكتب النوع صراحة لكي تتعود عليه.

## الثوابت `const` و`constexpr`

إذا كانت القيمة لا يجب أن تتغير أبدًا، اجعلها **ثابتًا**:

```cpp run
#include <iostream>

int main()
{
    constexpr double PI = 3.14159;  // ثابت معروف وقت الترجمة
    const int daysInWeek = 7;       // ثابت لا يتغير بعد تعريفه

    double r = 2.0;
    std::cout << "مساحة الدائرة: " << PI * r * r << "\n";
    std::cout << "أيام الأسبوع: " << daysInWeek << "\n";
    return 0;
}
```

```text output
مساحة الدائرة: 12.5664
أيام الأسبوع: 7
```

لاحظ أن `std::cout` يعرض الأعداد العشرية افتراضيًا بست أرقام معنوية فقط، لذلك ظهر `12.5664`.

## حجم الأنواع `sizeof`

كل نوع يحجز مساحة في الذاكرة تقاس بالبايت (byte):

```cpp run
#include <iostream>

int main()
{
    std::cout << "char:   " << sizeof(char) << " بايت\n";
    std::cout << "bool:   " << sizeof(bool) << " بايت\n";
    std::cout << "int:    " << sizeof(int) << " بايت\n";
    std::cout << "double: " << sizeof(double) << " بايت\n";
    std::cout << "long long: " << sizeof(long long) << " بايت\n";
    return 0;
}
```

```text output
char:   1 بايت
bool:   1 بايت
int:    4 بايت
double: 8 بايت
long long: 8 بايت
```

الـ `int` بحجم 4 بايت يتسع لأعداد من حوالي **سالب 2 مليار** إلى **موجب 2 مليار**. للأعداد الأكبر استخدم `long long`.

## قواعد تسمية المتغيرات

- يبدأ الاسم بحرف إنجليزي أو `_`، ولا يبدأ برقم: `total1` صحيح، `1total` خطأ.
- لا مسافات: `student name` خطأ، `studentName` أو `student_name` صحيح.
- لا تستخدم الكلمات المحجوزة مثل `int` و`return` و`class`.
- الأحرف الكبيرة تفرق: `Age` و`age` متغيران مختلفان.
- اختر أسماء واضحة: `price` أفضل بكثير من `p`.

## أخطاء شائعة

### استخدام متغير غير معرّف

<!-- compile-error -->
```cpp
#include <iostream>
int main()
{
    std::cout << total;
    return 0;
}
```

```text
main.cpp:4:18: error: 'total' was not declared in this scope
```

**المعنى:** «المتغير `total` لم يُعرَّف هنا». لا بد من تعريف المتغير بنوعه **قبل** استخدامه، وتأكد من كتابة الاسم بنفس الحروف.

### وضع عدد عشري في `int` بالأقواس `{}`

<!-- compile-error -->
```cpp
int main()
{
    int n{3.7};
    return n;
}
```

```text
main.cpp:3:11: error: narrowing conversion of '3.7000000000000002e+0' from 'double' to 'int' [-Wnarrowing]
```

**المعنى:** «تحويل مُضيِّق (narrowing) من `double` إلى `int`»، أي أنك ستفقد الجزء العشري `.7`. الأقواس `{}` تحميك هنا. لو كتبت `int n = 3.7;` لقبلها المترجم بصمت وأصبحت القيمة `3`!

### استخدام متغير بدون قيمة ابتدائية

<!-- compile-error -->
```cpp
#include <iostream>
int main()
{
    int x;
    std::cout << x;
    return 0;
}
```

```text
main.cpp:5:18: warning: 'x' is used uninitialized [-Wuninitialized]
```

**المعنى:** «المتغير `x` يُستخدم دون تهيئة». هذا **تحذير** وليس خطأ، فالبرنامج سيعمل، لكن `x` سيحتوي على قيمة عشوائية متبقية في الذاكرة. **أعطِ كل متغير قيمة ابتدائية دائمًا.**

## تمارين

### التمرين 1

عرّف متغيرات لمنتج: الاسم (`std::string`)، والسعر (`double`)، والكمية (`int`)، ثم اطبع الإجمالي (السعر × الكمية).

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    // المنتج: قلم، السعر 2.5، الكمية 4
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

int main()
{
    std::string product = "قلم";
    double price = 2.5;
    int quantity = 4;

    std::cout << "المنتج: " << product << "\n";
    std::cout << "الإجمالي: " << price * quantity << "\n";
    return 0;
}
```

```text output
المنتج: قلم
الإجمالي: 10
```

### التمرين 2

لديك متغيران `a = 3` و`b = 8`. بدّل قيمتيهما (اجعل `a` تساوي 8 و`b` تساوي 3) باستخدام متغير ثالث مؤقت.

```cpp exercise
#include <iostream>

int main()
{
    int a = 3;
    int b = 8;
    // بدّل القيمتين هنا

    std::cout << "a = " << a << ", b = " << b << "\n";
    return 0;
}
```

```cpp solution
#include <iostream>

int main()
{
    int a = 3;
    int b = 8;

    int temp = a;  // احفظ a قبل أن نفقدها
    a = b;
    b = temp;

    std::cout << "a = " << a << ", b = " << b << "\n";
    return 0;
}
```

```text output
a = 8, b = 3
```

> **تشبيه:** لتبديل محتوى كوبين (عصير وماء) تحتاج كوبًا ثالثًا فارغًا. هذا هو `temp`.

### التمرين 3

عرّف ثابتًا `constexpr` لسعر الدولار بالجنيه `50.0`، ثم احسب كم جنيهًا يساوي 120 دولارًا.

```cpp exercise
#include <iostream>

int main()
{
    // عرّف الثابت ثم اطبع: 120 دولار = ... جنيه
    return 0;
}
```

```cpp solution
#include <iostream>

int main()
{
    constexpr double EGP_PER_USD = 50.0;
    int dollars = 120;
    std::cout << dollars << " دولار = " << dollars * EGP_PER_USD << " جنيه\n";
    return 0;
}
```

```text output
120 دولار = 6000 جنيه
```

## اختبر نفسك

```quiz
{"question": "أي نوع يناسب تخزين السعر 49.99؟", "choices": ["int", "char", "double", "bool"], "answer": 2, "explanation": "double يخزن الأعداد ذات الكسور العشرية."}
```

```quiz
{"question": "ما معنى السطر x = x + 1; في البرمجة؟", "choices": ["معادلة مستحيلة", "زِد قيمة x بمقدار واحد", "قارن x مع x + 1", "خطأ ترجمة"], "answer": 1, "explanation": "العلامة = إسناد: احسب الطرف الأيمن ثم ضعه في x."}
```

```quiz
{"question": "أي اسم متغير صحيح؟", "choices": ["2ndName", "student name", "studentName", "int"], "answer": 2, "explanation": "لا يبدأ الاسم برقم، ولا يحتوي مسافات، ولا يكون كلمة محجوزة."}
```

```quiz
{"question": "ماذا يحدث عند كتابة int n{9.5};؟", "choices": ["تصبح n تساوي 9", "تصبح n تساوي 10", "خطأ ترجمة narrowing conversion", "تصبح n تساوي 9.5"], "answer": 2, "explanation": "التهيئة بالأقواس {} تمنع التحويل المُضيِّق الذي يفقد بيانات."}
```

```quiz
{"question": "متى نستخدم const؟", "choices": ["لقيمة لن تتغير بعد تعريفها", "لتسريع الطباعة", "للنصوص فقط", "لتعريف دالة"], "answer": 0, "explanation": "const تمنع تغيير المتغير بعد تعريفه، والمترجم يعطي خطأ لو حاولت."}
```

## الخلاصة

- المتغير علبة لها نوع واسم وقيمة.
- الأنواع الأساسية: `int`، `double`، `char`، `bool`، `std::string`.
- `=` إسناد، و`{}` تهيئة آمنة، و`auto` يستنتج النوع.
- `const`/`constexpr` للقيم الثابتة.
- أعطِ كل متغير قيمة ابتدائية دائمًا.
