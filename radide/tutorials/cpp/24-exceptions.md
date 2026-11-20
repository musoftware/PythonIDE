# الدرس 24: الاستثناءات ومعالجة الأخطاء (Exceptions)

البرامج الحقيقية تواجه مواقف غير متوقعة: ملف غير موجود، أو مستخدم كتب حروفًا بدل رقم، أو قسمة على صفر، أو ذاكرة نفدت. **الاستثناءات** (Exceptions) طريقة منظمة لكي يقول جزء من البرنامج: «حدثت مشكلة لا أستطيع حلها هنا!»، وجزء آخر يلتقط هذه المشكلة ويتصرف.

> **تشبيه:** عامل في مصنع وجد قطعة معيبة. لا يحاول إصلاحها بنفسه، بل **يرمي** إنذارًا (`throw`). والمشرف المسؤول **يلتقط** الإنذار (`catch`) ويقرر: يعيد التصنيع أو يوقف الخط. خط الإنتاج لا ينهار، بل يتعامل مع المشكلة في المكان المناسب.

## `try` و`throw` و`catch`

```cpp run
#include <iostream>
#include <stdexcept>

double divide(double a, double b)
{
    if (b == 0)
        throw std::invalid_argument("لا يمكن القسمة على صفر");   // ارمِ استثناءً
    return a / b;
}

int main()
{
    try                                         // جرّب هذا الكود
    {
        std::cout << divide(10, 4) << "\n";
        std::cout << divide(5, 0) << "\n";      // هنا يُرمى الاستثناء
        std::cout << "هذا السطر لن يُنفذ\n";
    }
    catch (const std::invalid_argument& e)      // التقط هذا النوع من الأخطاء
    {
        std::cout << "خطأ: " << e.what() << "\n";
    }
    std::cout << "البرنامج مستمر بشكل طبيعي\n";
    return 0;
}
```

```text output
2.5
خطأ: لا يمكن القسمة على صفر
البرنامج مستمر بشكل طبيعي
```

ماذا حدث؟

1. `throw` أوقفت الدالة `divide` فورًا (لم تصل إلى `return`).
2. انتقل التنفيذ مباشرة إلى `catch` المناسبة، وتجاوز باقي أسطر `try`.
3. `e.what()` تُرجع رسالة الخطأ.
4. بعد `catch` يكمل البرنامج طبيعيًا.

**بدون** `try/catch` كان البرنامج سينتهي فجأة برسالة مثل `terminate called after throwing an instance of 'std::invalid_argument'`.

## أنواع الاستثناءات القياسية

المكتبة `<stdexcept>` فيها أنواع جاهزة، كلها مشتقة من `std::exception`:

| النوع | متى نستخدمه |
|---|---|
| `std::invalid_argument` | قيمة معامل غير صالحة |
| `std::out_of_range` | فهرس أو قيمة خارج الحدود (ترميها `at()`) |
| `std::runtime_error` | خطأ عام وقت التشغيل (ملف مفقود...) |
| `std::logic_error` | خطأ منطقي في البرنامج |
| `std::bad_alloc` | نفاد الذاكرة (يرميها `new`) |

## عدة كتل `catch`

```cpp run
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

int main()
{
    std::vector<std::string> inputs = {"2", "abc", "99999999999999", "7"};
    std::vector<int> table = {10, 20, 30};

    for (const auto& text : inputs)
    {
        try
        {
            int index = std::stoi(text);      // قد ترمي invalid_argument أو out_of_range
            int value = table.at(index);      // قد ترمي out_of_range
            std::cout << text << " -> " << value << "\n";
        }
        catch (const std::invalid_argument&)
        {
            std::cout << text << " -> ليس رقمًا\n";
        }
        catch (const std::out_of_range&)
        {
            std::cout << text << " -> خارج الحدود\n";
        }
    }
    return 0;
}
```

```text output
2 -> 30
abc -> ليس رقمًا
99999999999999 -> خارج الحدود
7 -> خارج الحدود
```

تُفحص كتل `catch` بالترتيب، وتُنفذ **أول** واحدة تناسب نوع الاستثناء.

> **لماذا حسبنا `value` قبل الطباعة؟** لو كتبنا `std::cout << text << " -> " << table.at(index);` لطُبع الجزء `text -> ` أولًا، ثم رُمي الاستثناء في منتصف السطر، فيظهر ناتج ناقص مثل `7 -> 7 -> خارج الحدود`. احسب القيم التي قد تفشل أولًا، ثم اطبع.

## التقاط أي استثناء

```cpp
catch (const std::exception& e)   // أي استثناء قياسي (بفضل الوراثة)
{
    std::cout << e.what();
}
catch (...)                       // أي شيء على الإطلاق
{
    std::cout << "خطأ غير معروف";
}
```

ضع الأنواع **المحددة** أولًا ثم العامة، لأن `std::exception` تلتقط كل الأنواع المشتقة منها.

## صنع نوع استثناء خاص بك

```cpp run
#include <iostream>
#include <stdexcept>
#include <string>

class InsufficientFunds : public std::runtime_error
{
public:
    double needed;
    explicit InsufficientFunds(double n)
        : std::runtime_error("الرصيد غير كافٍ"), needed(n) {}
};

class Account
{
    double balance = 0;

public:
    void deposit(double amount)
    {
        if (amount <= 0)
            throw std::invalid_argument("مبلغ الإيداع يجب أن يكون موجبًا");
        balance += amount;
    }
    void withdraw(double amount)
    {
        if (amount > balance)
            throw InsufficientFunds(amount - balance);
        balance -= amount;
    }
    double getBalance() const { return balance; }
};

int main()
{
    Account acc;
    try
    {
        acc.deposit(500);
        acc.withdraw(200);
        acc.withdraw(1000);
    }
    catch (const InsufficientFunds& e)
    {
        std::cout << e.what() << "، ينقصك " << e.needed << "\n";
    }
    catch (const std::exception& e)
    {
        std::cout << "خطأ: " << e.what() << "\n";
    }
    std::cout << "الرصيد: " << acc.getBalance() << "\n";
    return 0;
}
```

```text output
الرصيد غير كافٍ، ينقصك 700
الرصيد: 300
```

## الاستثناءات وRAII: لا تسرّب أبدًا

عندما يُرمى استثناء، تُهدم كل الكائنات المحلية في الطريق تلقائيًا (وهذا يسمى **فك المكدّس** stack unwinding). لذلك الملفات والمؤشرات الذكية والـ vector تُغلق وتُحرر حتى عند حدوث خطأ:

```cpp run
#include <iostream>
#include <memory>
#include <stdexcept>

struct Resource
{
    Resource() { std::cout << "حجز المورد\n"; }
    ~Resource() { std::cout << "تحرير المورد\n"; }
};

void risky()
{
    auto r = std::make_unique<Resource>();
    throw std::runtime_error("مشكلة مفاجئة");
}   // r يُحرر تلقائيًا رغم الاستثناء

int main()
{
    try
    {
        risky();
    }
    catch (const std::exception& e)
    {
        std::cout << "التقطنا: " << e.what() << "\n";
    }
    return 0;
}
```

```text output
حجز المورد
تحرير المورد
التقطنا: مشكلة مفاجئة
```

لو استخدمنا `new` و`delete` يدويًا، لما وصل البرنامج إلى `delete` أبدًا وحدث تسرّب. سبب إضافي لاستخدام المؤشرات الذكية!

## متى نستخدم الاستثناءات؟

- **نعم:** للمواقف الاستثنائية فعلًا: ملف مفقود، أو بيانات تالفة، أو معامل مستحيل.
- **لا:** للتحكم العادي في سير البرنامج. إذا كان «عدم العثور على عنصر» متوقعًا، فأرجِع `bool` أو `end()` بدلًا من رمي استثناء.

## أخطاء شائعة

### استثناء لم يُلتقط

إذا رُمي استثناء ولم توجد `catch` مناسبة، ينتهي البرنامج فورًا ويظهر في نافذة Output شيء مثل:

```text
terminate called after throwing an instance of 'std::invalid_argument'
  what():  stoi
```

**المعنى:** «تم إنهاء البرنامج بعد رمي استثناء من النوع `std::invalid_argument`»، و`what()` تقول إن مصدره `stoi`. ضع الكود الذي قد يفشل داخل `try` والتقط النوع المناسب.

### الالتقاط بالقيمة بدل المرجع

اكتب دائمًا `catch (const std::exception& e)` بالمرجع. الالتقاط بالقيمة `catch (std::exception e)` ينسخ الكائن ويقطع منه الجزء المشتق (slicing)، فقد تفقد الرسالة أو البيانات الإضافية. ويحذرك g++ بـ `-Wcatch-value`.

### ترتيب `catch` الخاطئ

<!-- compile-error -->
```cpp
#include <stdexcept>
int main()
{
    try { throw std::out_of_range("x"); }
    catch (const std::exception&) {}
    catch (const std::out_of_range&) {}
    return 0;
}
```

```text
main.cpp:6:5: warning: exception of type 'std::out_of_range' will be caught by earlier handler [-Wexceptions]
```

**المعنى:** «الاستثناء من نوع `out_of_range` سيُلتقط بمعالج سابق». الكتلة الثانية لن تُنفذ أبدًا لأن الأولى العامة تلتقط كل شيء. ضع المحدد قبل العام.

## تمارين

### التمرين 1

اكتب دالة `int parseAge(const std::string& s)` ترمي `std::invalid_argument` إذا لم يكن النص رقمًا، و`std::out_of_range` إذا كان العمر خارج 0 إلى 150. جرّبها على `"25"` و`"abc"` و`"200"`.

```cpp exercise
#include <iostream>
#include <stdexcept>
#include <string>

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <stdexcept>
#include <string>

int parseAge(const std::string& s)
{
    int age = std::stoi(s);   // ترمي invalid_argument إذا لم يكن رقمًا
    if (age < 0 || age > 150)
        throw std::out_of_range("عمر غير منطقي");
    return age;
}

int main()
{
    for (std::string s : {"25", "abc", "200"})
    {
        try
        {
            int age = parseAge(s);    // احسب أولًا ثم اطبع
            std::cout << s << ": " << age << "\n";
        }
        catch (const std::invalid_argument&)
        {
            std::cout << s << ": ليس رقمًا\n";
        }
        catch (const std::out_of_range& e)
        {
            std::cout << s << ": " << e.what() << "\n";
        }
    }
    return 0;
}
```

```text output
25: 25
abc: ليس رقمًا
200: عمر غير منطقي
```

### التمرين 2

اقرأ أرقامًا (كنصوص) من المستخدم حتى نهاية المدخلات، واجمع الصالح منها فقط، واعدّ المدخلات غير الصالحة.

```cpp exercise
#include <iostream>
#include <stdexcept>
#include <string>

int main()
{
    // استخدم std::stod داخل try
    return 0;
}
```

```cpp solution
#include <iostream>
#include <stdexcept>
#include <string>

int main()
{
    std::string token;
    double sum = 0;
    int bad = 0;
    while (std::cin >> token)
    {
        try
        {
            sum += std::stod(token);
        }
        catch (const std::exception&)
        {
            bad++;
        }
    }
    std::cout << "المجموع: " << sum << "، مدخلات خاطئة: " << bad << "\n";
    return 0;
}
```

```text input
10 x 2.5 hello 7.5
```

```text output
المجموع: 20، مدخلات خاطئة: 2
```

### التمرين 3

اكتب دالة `std::string readFirstLine(const std::string& file)` ترمي `std::runtime_error` برسالة «الملف غير موجود: » + الاسم إذا تعذر فتح الملف.

```cpp exercise
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

int main()
{
    return 0;
}
```

```cpp solution
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

std::string readFirstLine(const std::string& file)
{
    std::ifstream in(file);
    if (!in)
        throw std::runtime_error("الملف غير موجود: " + file);
    std::string line;
    std::getline(in, line);
    return line;
}

int main()
{
    std::ofstream("hello.txt") << "مرحبا من الملف\n";
    for (std::string f : {"hello.txt", "nothing.txt"})
    {
        try
        {
            std::cout << readFirstLine(f) << "\n";
        }
        catch (const std::runtime_error& e)
        {
            std::cout << e.what() << "\n";
        }
    }
    return 0;
}
```

```text output
مرحبا من الملف
الملف غير موجود: nothing.txt
```

## اختبر نفسك

```quiz
{"question": "ماذا يحدث للأسطر الباقية في try بعد رمي استثناء؟", "choices": ["تُنفذ عادي", "تُتجاوز وينتقل التنفيذ إلى catch المناسبة", "تُنفذ مرتين", "يتوقف الكمبيوتر"], "answer": 1, "explanation": "throw تقطع التنفيذ فورًا وتنتقل إلى أول catch مناسبة."}
```

```quiz
{"question": "ما الدالة التي تُرجع رسالة الاستثناء؟", "choices": ["e.message()", "e.what()", "e.text()", "e.error()"], "answer": 1, "explanation": "كل الاستثناءات القياسية فيها what() التي تُرجع الرسالة."}
```

```quiz
{"question": "أي ترتيب لكتل catch صحيح؟", "choices": ["std::exception ثم std::out_of_range", "std::out_of_range ثم std::exception", "الترتيب لا يهم", "لا يجوز أكثر من catch"], "answer": 1, "explanation": "المحدد قبل العام، وإلا التقطت العامة كل شيء."}
```

```quiz
{"question": "لماذا تتحرر الموارد في المؤشرات الذكية حتى عند رمي استثناء؟", "choices": ["لأن الاستثناء يحذف كل الذاكرة", "لأن الكائنات المحلية تُهدم تلقائيًا أثناء فك المكدّس", "لأن catch تحذفها", "لا تتحرر"], "answer": 1, "explanation": "فك المكدّس يستدعي مُهدِّمات الكائنات المحلية، وهذا جوهر RAII."}
```

## الخلاصة

- `throw` ترمي، و`try` تحيط بالكود الخطر، و`catch` تلتقط.
- التقط بالمرجع الثابت `const T&`، والمحدد قبل العام.
- الأنواع القياسية في `<stdexcept>`، ويمكنك الاشتقاق منها.
- RAII يضمن تحرير الموارد حتى عند الأخطاء.
