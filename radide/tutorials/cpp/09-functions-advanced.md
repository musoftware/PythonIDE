# الدرس 9: الدوال المتقدمة: المراجع، والتحميل الزائد، والقيم الافتراضية

في هذا الدرس سنتعلم ثلاث ميزات تجعل الدوال في C++ أقوى بكثير: **المراجع** (References)، و**التحميل الزائد** (Overloading)، و**القيم الافتراضية** (Default arguments). وفي النهاية نتعرف على **الاستدعاء الذاتي** (Recursion).

## المراجع: اسم ثانٍ لنفس المتغير

**المرجع** (Reference) اسم بديل لمتغير موجود. نعرّفه بإضافة `&` بعد النوع:

```cpp
int score = 10;
int& s = score;   // s اسم آخر لـ score
s = 50;           // score أصبحت 50 أيضًا!
```

> **تشبيه:** صديقك اسمه «محمد» وأصحابه ينادونه «حمادة». الاسمان لشخص واحد؛ إذا أعطيت «حمادة» كتابًا فقد أعطيته لـ «محمد».

## التمرير بالمرجع (pass by reference)

في الدرس السابق رأينا أن الدالة تأخذ **نسخة** من الوسيط. إذا أردنا أن تعدّل الدالة المتغير **الأصلي**، نمرره بالمرجع:

```cpp run
#include <iostream>

void addBonus(int& points)   // & تعني: أعطني المتغير نفسه
{
    points += 10;
}

void swapValues(int& a, int& b)
{
    int temp = a;
    a = b;
    b = temp;
}

int main()
{
    int myPoints = 50;
    addBonus(myPoints);
    std::cout << "النقاط: " << myPoints << "\n";

    int x = 1, y = 2;
    swapValues(x, y);
    std::cout << "x = " << x << "، y = " << y << "\n";
    return 0;
}
```

```text output
النقاط: 60
x = 2، y = 1
```

### إرجاع أكثر من قيمة

الدالة تُرجع قيمة واحدة بـ `return`، لكن بالمراجع يمكنها «إخراج» عدة نتائج:

```cpp run
#include <iostream>

void divide(int a, int b, int& quotient, int& remainder)
{
    quotient = a / b;
    remainder = a % b;
}

int main()
{
    int q = 0, r = 0;
    divide(17, 5, q, r);
    std::cout << "17 / 5 = " << q << " والباقي " << r << "\n";
    return 0;
}
```

```text output
17 / 5 = 3 والباقي 2
```

## المرجع الثابت `const&`: سريع وآمن

نسخ النصوص الطويلة (والبيانات الكبيرة عمومًا) يأخذ وقتًا وذاكرة. الحل: نمررها بـ **مرجع ثابت** `const std::string&`، فلا تحدث نسخة، ولا تستطيع الدالة تغييرها:

```cpp run
#include <iostream>
#include <string>

void printTitle(const std::string& title)
{
    std::cout << "=== " << title << " ===\n";
    // title += "!";   // خطأ ترجمة: المرجع ثابت
}

int main()
{
    std::string course = "دورة C++ الحديثة";
    printTitle(course);
    printTitle("الدرس التاسع");
    return 0;
}
```

```text output
=== دورة C++ الحديثة ===
=== الدرس التاسع ===
```

**القاعدة العملية:**

| الحالة | الطريقة |
|---|---|
| أنواع صغيرة (`int`، `double`، `char`، `bool`) للقراءة فقط | بالقيمة: `int x` |
| أنواع كبيرة (`std::string`، `std::vector`...) للقراءة فقط | `const std::string& s` |
| تريد أن تعدّل الدالة المتغير الأصلي | `int& x` |

## التحميل الزائد للدوال (Function Overloading)

يمكن أن تتشارك عدة دوال **نفس الاسم** بشرط أن تختلف في **المعاملات** (العدد أو الأنواع). المترجم يختار المناسبة حسب الوسائط:

```cpp run
#include <iostream>
#include <string>

int area(int side)                 // مربع
{
    return side * side;
}

int area(int width, int height)    // مستطيل
{
    return width * height;
}

double area(double radius)         // دائرة
{
    return 3.14159 * radius * radius;
}

void show(int n) { std::cout << "عدد صحيح: " << n << "\n"; }
void show(const std::string& s) { std::cout << "نص: " << s << "\n"; }

int main()
{
    std::cout << area(4) << "\n";
    std::cout << area(3, 5) << "\n";
    std::cout << area(1.0) << "\n";
    show(42);
    show("مرحبا");
    return 0;
}
```

```text output
16
15
3.14159
عدد صحيح: 42
نص: مرحبا
```

> **ملحوظة:** لا يكفي أن يختلف **النوع المُرجَع** فقط؛ يجب أن تختلف المعاملات.

## القيم الافتراضية للمعاملات (Default Arguments)

يمكن إعطاء المعامل قيمة تُستخدم إذا لم يمرر المستدعي قيمة له. والقيم الافتراضية تكون دائمًا في **آخر** المعاملات:

```cpp run
#include <iostream>
#include <string>

void printReceipt(const std::string& item, double price, int qty = 1, double discount = 0.0)
{
    double total = price * qty * (1 - discount);
    std::cout << item << ": " << total << " جنيه\n";
}

int main()
{
    printReceipt("كتاب", 120);            // qty = 1, discount = 0
    printReceipt("قلم", 5, 10);           // discount = 0
    printReceipt("حقيبة", 400, 1, 0.25);  // كل القيم
    return 0;
}
```

```text output
كتاب: 120 جنيه
قلم: 50 جنيه
حقيبة: 300 جنيه
```

## الاستدعاء الذاتي (Recursion)

الدالة التي تستدعي نفسها تسمى **دالة تعاودية** (recursive). لا بد أن يكون لها **شرط توقف** وإلا استمرت للأبد:

```cpp run
#include <iostream>

long long factorial(int n)
{
    if (n <= 1)           // شرط التوقف
        return 1;
    return n * factorial(n - 1);   // نفس المشكلة لكن أصغر
}

int fibonacci(int n)
{
    if (n < 2)
        return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

int main()
{
    std::cout << "5! = " << factorial(5) << "\n";
    for (int i = 0; i < 10; i++)
        std::cout << fibonacci(i) << " ";
    std::cout << "\n";
    return 0;
}
```

```text output
5! = 120
0 1 1 2 3 5 8 13 21 34
```

> **تشبيه:** الدمى الروسية (ماتريوشكا): تفتح الدمية فتجد دمية أصغر، وهكذا حتى تصل إلى أصغر دمية لا تُفتح؛ هذا هو شرط التوقف.

## أخطاء شائعة

### تمرير قيمة ثابتة إلى معامل مرجع

<!-- compile-error -->
```cpp
void inc(int& x) { x++; }
int main()
{
    inc(5);
}
```

```text
main.cpp:4:9: error: cannot bind non-const lvalue reference of type 'int&' to an rvalue of type 'int'
```

**المعنى:** «لا يمكن ربط مرجع غير ثابت من نوع `int&` بقيمة مؤقتة (rvalue)». الرقم `5` ليس متغيرًا له مكان في الذاكرة يمكن تعديله. مرر متغيرًا: `int n = 5; inc(n);`، أو اجعل المعامل `const int&` إذا كانت الدالة لا تعدّله.

### استدعاء غامض (Ambiguous)

<!-- compile-error -->
```cpp
void f(int) {}
void f(double) {}
int main()
{
    f(2L);
}
```

```text
main.cpp:5:6: error: call of overloaded 'f(long int)' is ambiguous
```

**المعنى:** «استدعاء الدالة المحمّلة `f(long int)` غامض». `2L` من نوع `long`، ويمكن تحويله إلى `int` أو إلى `double` بنفس الدرجة، فلم يستطع المترجم الاختيار. اجعل النوع واضحًا: `f(2)` أو `f(2.0)`.

### تعديل معامل `const&`

<!-- compile-error -->
```cpp
#include <string>
void shout(const std::string& s)
{
    s += "!";
}
int main() { shout("hi"); }
```

```text
main.cpp:4:7: error: no match for 'operator+=' (operand types are 'const std::string' {aka 'const std::__cxx11::basic_string<char>'} and 'const char [2]')
```

**المعنى:** لا يوجد `+=` لنص ثابت `const std::string`. إذا أردت التعديل، خذ نسخة (`std::string s`) أو مرجعًا غير ثابت.

## تمارين

### التمرين 1

اكتب دالة `void minMax(int a, int b, int c, int& mn, int& mx)` تضع أصغر الأعداد في `mn` وأكبرها في `mx`.

```cpp exercise
#include <iostream>

// اكتب minMax هنا

int main()
{
    int mn = 0, mx = 0;
    // minMax(8, 3, 15, mn, mx);
    std::cout << "الأصغر: " << mn << "، الأكبر: " << mx << "\n";
    return 0;
}
```

```cpp solution
#include <iostream>

void minMax(int a, int b, int c, int& mn, int& mx)
{
    mn = a;
    mx = a;
    if (b < mn) mn = b;
    if (c < mn) mn = c;
    if (b > mx) mx = b;
    if (c > mx) mx = c;
}

int main()
{
    int mn = 0, mx = 0;
    minMax(8, 3, 15, mn, mx);
    std::cout << "الأصغر: " << mn << "، الأكبر: " << mx << "\n";
    return 0;
}
```

```text output
الأصغر: 3، الأكبر: 15
```

### التمرين 2

اكتب دالتين بنفس الاسم `describe`: الأولى تأخذ `int` وتطبع «عدد: ...»، والثانية تأخذ `bool` وتطبع «نعم» أو «لا».

```cpp exercise
#include <iostream>

int main()
{
    // describe(7);
    // describe(true);
    return 0;
}
```

```cpp solution
#include <iostream>

void describe(int n)
{
    std::cout << "عدد: " << n << "\n";
}

void describe(bool b)
{
    std::cout << (b ? "نعم" : "لا") << "\n";
}

int main()
{
    describe(7);
    describe(true);
    describe(false);
    return 0;
}
```

```text output
عدد: 7
نعم
لا
```

### التمرين 3

اكتب دالة تعاودية `int sumDigits(int n)` تُرجع مجموع أرقام العدد (مثلًا 1234 ← 10). تلميح: آخر رقم هو `n % 10`، وباقي العدد `n / 10`.

```cpp exercise
#include <iostream>

int sumDigits(int n)
{
    // شرط التوقف: إذا كان n == 0
    return 0;
}

int main()
{
    std::cout << sumDigits(1234) << "\n";
    return 0;
}
```

```cpp solution
#include <iostream>

int sumDigits(int n)
{
    if (n == 0)
        return 0;
    return n % 10 + sumDigits(n / 10);
}

int main()
{
    std::cout << sumDigits(1234) << "\n";
    std::cout << sumDigits(90817) << "\n";
    return 0;
}
```

```text output
10
25
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين void f(int x) و void f(int& x)؟", "choices": ["لا فرق", "الأولى تأخذ نسخة والثانية تعمل على المتغير الأصلي", "الثانية أبطأ دائمًا", "الأولى للأعداد السالبة فقط"], "answer": 1, "explanation": "& تجعل المعامل مرجعًا للمتغير الأصلي، فأي تعديل يظهر عند المستدعي."}
```

```quiz
{"question": "ما أفضل طريقة لتمرير std::string كبير إلى دالة تقرؤه فقط؟", "choices": ["std::string s", "std::string& s", "const std::string& s", "int s"], "answer": 2, "explanation": "المرجع الثابت يمنع النسخ ويمنع التعديل في نفس الوقت."}
```

```quiz
{"question": "متى يكون تحميل الدوال (overloading) صحيحًا؟", "choices": ["عندما يختلف النوع المُرجَع فقط", "عندما تختلف المعاملات في العدد أو النوع", "عندما يختلف اسم المعامل فقط", "لا يُسمح به في C++"], "answer": 1, "explanation": "المترجم يميز الدوال المحمّلة بمعاملاتها، لا بالنوع المُرجَع ولا بأسماء المعاملات."}
```

```quiz
{"question": "أي تعريف للقيم الافتراضية صحيح؟", "choices": ["void f(int a = 1, int b)", "void f(int a, int b = 2)", "void f(int = a, b)", "void f(default int a)"], "answer": 1, "explanation": "القيم الافتراضية يجب أن تكون في آخر المعاملات."}
```

```quiz
{"question": "ما أهم شيء في الدالة التعاودية؟", "choices": ["أن تكون void", "أن يكون لها شرط توقف", "أن تأخذ معاملين", "أن تستخدم حلقة for"], "answer": 1, "explanation": "بدون شرط توقف تستدعي الدالة نفسها بلا نهاية حتى تمتلئ الذاكرة (stack overflow)."}
```

## الخلاصة

- المرجع `int&` اسم ثانٍ للمتغير، والتمرير بالمرجع يسمح بتعديل الأصل.
- `const T&` لتمرير البيانات الكبيرة دون نسخ ودون تعديل.
- التحميل الزائد: نفس الاسم بمعاملات مختلفة.
- القيم الافتراضية تكون في آخر المعاملات.
- الدالة التعاودية تحتاج شرط توقف.
