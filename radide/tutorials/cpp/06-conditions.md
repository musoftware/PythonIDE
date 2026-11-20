# الدرس 6: الشروط واتخاذ القرار

حتى الآن كانت برامجنا تنفذ كل السطور بالترتيب. لكن البرامج الحقيقية **تتخذ قرارات**: إذا كانت كلمة المرور صحيحة افتح الحساب، وإلا اعرض رسالة خطأ. هذا ما تفعله **الشروط**.

## الجملة `if`

```cpp
if (الشرط)
{
    // تُنفذ فقط إذا كان الشرط صحيحًا
}
```

> **تشبيه:** `if` مثل حارس البوابة: يسأل سؤالًا (الشرط)، فإن كانت الإجابة «نعم» سمح لك بالدخول إلى ما بين القوسين `{ }`.

## `if` و`else`

```cpp run
#include <iostream>

int main()
{
    int grade = 0;
    std::cout << "أدخل درجتك: ";
    std::cin >> grade;

    if (grade >= 50)
    {
        std::cout << "\nمبروك، نجحت!\n";
    }
    else
    {
        std::cout << "\nللأسف، حاول مرة أخرى.\n";
    }
    return 0;
}
```

```text input
73
```

```text output
أدخل درجتك:
مبروك، نجحت!
```

`else` معناها «وإلا»، وتُنفذ عندما يكون الشرط خاطئًا. جرّب المثال مرة أخرى بدرجة أقل من 50.

## عدة احتمالات: `else if`

```cpp run
#include <iostream>

int main()
{
    int grade = 0;
    std::cin >> grade;

    if (grade < 0 || grade > 100)
        std::cout << "درجة غير صحيحة\n";
    else if (grade >= 85)
        std::cout << "ممتاز\n";
    else if (grade >= 75)
        std::cout << "جيد جدًا\n";
    else if (grade >= 65)
        std::cout << "جيد\n";
    else if (grade >= 50)
        std::cout << "مقبول\n";
    else
        std::cout << "راسب\n";
    return 0;
}
```

```text input
78
```

```text output
جيد جدًا
```

- يفحص البرنامج الشروط **من أعلى إلى أسفل**، وينفذ **أول** شرط صحيح فقط ثم يتجاوز الباقي.
- إذا كان ما بعد `if` تعليمة واحدة فقط، يمكن حذف الأقواس `{ }`. لكن المحترفين ينصحون بكتابتها دائمًا لتجنب الأخطاء عند إضافة سطور لاحقًا.

## الشروط المتداخلة

يمكن وضع `if` داخل `if`:

```cpp run
#include <iostream>
#include <string>

int main()
{
    std::string user, password;
    std::cin >> user >> password;

    if (user == "admin")
    {
        if (password == "1234")
            std::cout << "مرحبًا أيها المدير\n";
        else
            std::cout << "كلمة المرور خاطئة\n";
    }
    else
    {
        std::cout << "المستخدم غير موجود\n";
    }
    return 0;
}
```

```text input
admin 1111
```

```text output
كلمة المرور خاطئة
```

لاحظ أن مقارنة النصوص `std::string` بـ `==` تعمل بشكل طبيعي في C++.

## الجملة `switch`

عندما نقارن متغيرًا واحدًا بعدة قيم ثابتة، تكون `switch` أوضح من سلسلة `else if`:

```cpp run
#include <iostream>

int main()
{
    int day = 0;
    std::cin >> day;

    switch (day)
    {
    case 1:
        std::cout << "السبت\n";
        break;
    case 2:
        std::cout << "الأحد\n";
        break;
    case 6:
    case 7:
        std::cout << "نهاية الأسبوع\n";
        break;
    default:
        std::cout << "يوم عمل عادي\n";
        break;
    }
    return 0;
}
```

```text input
7
```

```text output
نهاية الأسبوع
```

- كل `case` قيمة محتملة، و`default` لأي قيمة أخرى (مثل `else`).
- `break` تخرج من `switch`. **إذا نسيتها** يكمل البرنامج تنفيذ الحالة التالية أيضًا! (لاحظ كيف استفدنا من ذلك عمدًا في `case 6:` و`case 7:`).
- `switch` تعمل مع الأعداد الصحيحة والحروف `char`، لكن **ليس** مع `std::string`.

## العامل الثلاثي `? :`

اختصار لـ `if/else` البسيطة التي تختار بين قيمتين:

```cpp run
#include <iostream>
#include <string>

int main()
{
    int n = 7;
    std::string kind = (n % 2 == 0) ? "زوجي" : "فردي";
    std::cout << n << " عدد " << kind << "\n";

    int a = 12, b = 30;
    int biggest = (a > b) ? a : b;
    std::cout << "الأكبر: " << biggest << "\n";
    return 0;
}
```

```text output
7 عدد فردي
الأكبر: 30
```

الصيغة: `الشرط ? القيمة_إذا_صح : القيمة_إذا_خطأ`.

## `if` مع تهيئة (C++17)

في C++17 يمكن تعريف متغير داخل `if` نفسها، فيكون مرئيًا داخلها فقط:

```cpp
if (int remaining = 100 - score; remaining > 0)
    std::cout << "تبقى " << remaining << " نقطة\n";
```

## أخطاء شائعة

### `=` بدل `==` داخل الشرط

<!-- compile-error -->
```cpp
#include <iostream>
int main()
{
    int x = 5;
    if (x = 10)
        std::cout << "ten";
    return 0;
}
```

```text
main.cpp:5:11: warning: suggest parentheses around assignment used as truth value [-Wparentheses]
```

**المعنى:** «أقترح أقواسًا حول الإسناد المستخدم كقيمة صح/خطأ». المترجم يشك أنك تقصد `==`. الكود `x = 10` **يضع** 10 في `x`، والنتيجة 10 تُعتبر `true`، فيُنفذ الشرط دائمًا! صحّحها إلى `if (x == 10)`.

### فاصلة منقوطة بعد `if`

```cpp
if (grade >= 50);          // ← هذه الفاصلة تنهي الـ if هنا!
    std::cout << "نجحت";   // تُنفذ دائمًا
```

الفاصلة بعد القوس تعني «إذا تحقق الشرط فلا تفعل شيئًا»، والسطر التالي يصبح مستقلًا. الإصدارات الحديثة من g++ تحذرك بـ `-Wempty-body` في بعض الحالات.

### كتابة الشرط المركب بأسلوب الرياضيات

`if (0 < x < 10)` **لا** تعمل كما تتوقع! تُحسب `0 < x` أولًا (تعطي 0 أو 1) ثم تُقارن بـ 10 فتكون دائمًا صحيحة. الصواب: `if (x > 0 && x < 10)`.

## تمارين

### التمرين 1

اقرأ عددًا واطبع: «موجب» أو «سالب» أو «صفر».

```cpp exercise
#include <iostream>

int main()
{
    int n = 0;
    std::cin >> n;
    // أكمل
    return 0;
}
```

```cpp solution
#include <iostream>

int main()
{
    int n = 0;
    std::cin >> n;
    if (n > 0)
        std::cout << "موجب\n";
    else if (n < 0)
        std::cout << "سالب\n";
    else
        std::cout << "صفر\n";
    return 0;
}
```

```text input
-4
```

```text output
سالب
```

### التمرين 2

آلة حاسبة: اقرأ عددين وعملية (`+` أو `-` أو `*` أو `/`) واطبع الناتج باستخدام `switch`. لا تسمح بالقسمة على صفر.

```cpp exercise
#include <iostream>

int main()
{
    double a = 0, b = 0;
    char op = ' ';
    std::cin >> a >> op >> b;
    // أكمل باستخدام switch (op)
    return 0;
}
```

```cpp solution
#include <iostream>

int main()
{
    double a = 0, b = 0;
    char op = ' ';
    std::cin >> a >> op >> b;

    switch (op)
    {
    case '+':
        std::cout << a + b << "\n";
        break;
    case '-':
        std::cout << a - b << "\n";
        break;
    case '*':
        std::cout << a * b << "\n";
        break;
    case '/':
        if (b == 0)
            std::cout << "لا يمكن القسمة على صفر\n";
        else
            std::cout << a / b << "\n";
        break;
    default:
        std::cout << "عملية غير معروفة\n";
    }
    return 0;
}
```

```text input
9 / 2
```

```text output
4.5
```

### التمرين 3

السنة الكبيسة: تكون السنة كبيسة إذا قبلت القسمة على 4 ولم تقبل القسمة على 100، **أو** قبلت القسمة على 400. اقرأ سنة واطبع هل هي كبيسة.

```cpp exercise
#include <iostream>

int main()
{
    int year = 0;
    std::cin >> year;
    // استخدم % و && و ||
    return 0;
}
```

```cpp solution
#include <iostream>

int main()
{
    int year = 0;
    std::cin >> year;
    bool leap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    if (leap)
        std::cout << year << " سنة كبيسة\n";
    else
        std::cout << year << " ليست كبيسة\n";
    return 0;
}
```

```text input
2024
```

```text output
2024 سنة كبيسة
```

## اختبر نفسك

```quiz
{"question": "ماذا يحدث في سلسلة if / else if إذا تحقق أكثر من شرط؟", "choices": ["تُنفذ كل الشروط الصحيحة", "يُنفذ أول شرط صحيح فقط", "يُنفذ آخر شرط صحيح", "خطأ ترجمة"], "answer": 1, "explanation": "الفحص من أعلى لأسفل، وبعد أول شرط صحيح يُتجاوز الباقي."}
```

```quiz
{"question": "ماذا يحدث إذا نسيت break في إحدى حالات switch؟", "choices": ["خطأ ترجمة", "يكمل التنفيذ إلى الحالة التالية", "يتوقف البرنامج", "لا شيء"], "answer": 1, "explanation": "بدون break يستمر التنفيذ في الحالات التالية (fall-through)."}
```

```quiz
{"question": "ما قيمة r في: int r = (5 > 3) ? 10 : 20;؟", "choices": ["5", "3", "10", "20"], "answer": 2, "explanation": "الشرط 5 > 3 صحيح فتُختار القيمة الأولى 10."}
```

```quiz
{"question": "ما الطريقة الصحيحة لفحص أن x بين 1 و9؟", "choices": ["if (1 < x < 9)", "if (x > 1 && x < 9)", "if (x > 1 || x < 9)", "if (x between 1, 9)"], "answer": 1, "explanation": "نربط شرطين بـ &&. الصيغة الرياضية 1 < x < 9 لا تعمل كما نتوقع في C++."}
```

## الخلاصة

- `if` / `else if` / `else` لاتخاذ القرارات.
- `switch` لمقارنة متغير واحد بقيم ثابتة، ولا تنسَ `break`.
- `? :` لاختيار قيمة من اثنتين.
- احذر من `=` بدل `==`، والفاصلة المنقوطة بعد `if`.
