# الدرس 19: التحميل الزائد للعوامل (Operator Overloading)

نحن نكتب `a + b` مع الأعداد و`s1 + s2` مع النصوص، و`std::cout << x` للطباعة. هل تساءلت كيف تعرف `std::string` معنى `+`؟ السر: **التحميل الزائد للعوامل**. يمكنك أن تعلّم أصنافك أنت أيضًا معنى `+` و`==` و`<<` وغيرها.

> **تشبيه:** علامة `+` تعني «اجمع» مع الأرقام، و«اخلط» مع ألوان الرسم، و«ادمج» مع النصوص. نفس الرمز، ومعنى يناسب كل نوع. أنت تقرر معنى الرمز لنوعك.

## الفكرة الأساسية

العامل في C++ مجرد **دالة** لها اسم خاص: `operator+` و`operator==` و`operator<<`... عندما تكتب `a + b` يحولها المترجم إلى `operator+(a, b)` أو `a.operator+(b)`.

## مثال: متجه ثنائي الأبعاد

```cpp run
#include <iostream>

struct Vec2
{
    double x = 0, y = 0;

    Vec2 operator+(const Vec2& other) const     // a + b
    {
        return {x + other.x, y + other.y};
    }
    Vec2 operator-(const Vec2& other) const     // a - b
    {
        return {x - other.x, y - other.y};
    }
    Vec2 operator*(double k) const              // a * 2
    {
        return {x * k, y * k};
    }
    Vec2& operator+=(const Vec2& other)         // a += b
    {
        x += other.x;
        y += other.y;
        return *this;
    }
    bool operator==(const Vec2& other) const    // a == b
    {
        return x == other.x && y == other.y;
    }
};

// الطباعة: std::cout << v  (دالة خارج الصنف)
std::ostream& operator<<(std::ostream& out, const Vec2& v)
{
    return out << "(" << v.x << ", " << v.y << ")";
}

int main()
{
    Vec2 a{1, 2};
    Vec2 b{3, 4};
    std::cout << "a + b = " << a + b << "\n";
    std::cout << "b - a = " << b - a << "\n";
    std::cout << "a * 3 = " << a * 3 << "\n";
    a += b;
    std::cout << "a بعد += : " << a << "\n";
    std::cout << std::boolalpha << "a == (4, 6)? " << (a == Vec2{4, 6}) << "\n";
    return 0;
}
```

```text output
a + b = (4, 6)
b - a = (2, 2)
a * 3 = (3, 6)
a بعد += : (4, 6)
a == (4, 6)? true
```

لاحظ:

- `operator+` تُرجع **كائنًا جديدًا** ولا تغير الأصل، لذلك هي `const`.
- `operator+=` **تعدّل** الكائن نفسه وتُرجع مرجعًا له `*this`، لكي يمكن كتابة `a += b += c`.
- `operator<<` تُكتب **خارج** الصنف لأن الطرف الأيسر هو `std::cout` (من نوع `std::ostream`) وليس كائننا. وتُرجع `out` لكي نستطيع ربط عدة `<<`.

## مثال: كسر رياضي

```cpp run
#include <iostream>
#include <numeric>

class Fraction
{
private:
    long long num, den;

    void simplify()
    {
        long long g = std::gcd(num, den);   // القاسم المشترك الأكبر (C++17)
        num /= g;
        den /= g;
        if (den < 0)
        {
            num = -num;
            den = -den;
        }
    }

public:
    Fraction(long long n = 0, long long d = 1) : num(n), den(d) { simplify(); }

    Fraction operator+(const Fraction& o) const { return {num * o.den + o.num * den, den * o.den}; }
    Fraction operator*(const Fraction& o) const { return {num * o.num, den * o.den}; }
    bool operator<(const Fraction& o) const { return num * o.den < o.num * den; }
    bool operator==(const Fraction& o) const { return num == o.num && den == o.den; }

    friend std::ostream& operator<<(std::ostream& out, const Fraction& f)
    {
        out << f.num;
        if (f.den != 1)
            out << "/" << f.den;
        return out;
    }
};

int main()
{
    Fraction half(1, 2), third(1, 3);
    std::cout << half << " + " << third << " = " << half + third << "\n";
    std::cout << half << " * " << third << " = " << half * third << "\n";
    std::cout << "2/4 = " << Fraction(2, 4) << "\n";
    std::cout << "3/3 = " << Fraction(3, 3) << "\n";
    std::cout << std::boolalpha << "1/3 < 1/2 ? " << (third < half) << "\n";
    return 0;
}
```

```text output
1/2 + 1/3 = 5/6
1/2 * 1/3 = 1/6
2/4 = 1/2
3/3 = 1
1/3 < 1/2 ? true
```

- `friend` تسمح لدالة خارجية بالوصول إلى الأعضاء الخاصة `num` و`den`.
- المُنشئ `Fraction(long long n = 0, long long d = 1)` يسمح بكتابة `return {..., ...};` داخل العوامل.

## عامل المقارنة الشامل `<=>` (C++20)

في C++20 يكفي أن تكتب سطرًا واحدًا ليولد المترجم كل عوامل المقارنة (`<` و`<=` و`>` و`>=` و`==` و`!=`):

```cpp
#include <compare>

struct Version
{
    int major, minor;
    auto operator<=>(const Version&) const = default;  // C++20
};
// Version{1, 2} < Version{1, 10}  ← true
```

هذه الميزة تحتاج المعيار C++20. إذا كان مشروعك مضبوطًا على C++17، اكتب `operator<` و`operator==` بنفسك كما في مثال الكسر.

## عامل الفهرسة `[]`

```cpp run
#include <iostream>
#include <stdexcept>
#include <string>

class Week
{
    std::string days[7] = {"السبت", "الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة"};

public:
    const std::string& operator[](int i) const
    {
        if (i < 0 || i >= 7)
            throw std::out_of_range("رقم يوم غير صحيح");
        return days[i];
    }
};

int main()
{
    Week w;
    std::cout << w[0] << "\n" << w[6] << "\n";
    return 0;
}
```

```text output
السبت
الجمعة
```

## قواعد ذهبية

1. اجعل معنى العامل **بديهيًا**. لا تجعل `+` تطرح! إذا لم يكن المعنى واضحًا فاكتب دالة باسم واضح.
2. إذا عرّفت `+` فعرّف `+=` أيضًا، وإذا عرّفت `==` فالأفضل أن يكون هناك `!=` (C++20 يولدها تلقائيًا من `==`).
3. لا يمكنك اختراع عوامل جديدة (مثل `**`)، ولا تغيير أولوية العوامل.

## أخطاء شائعة

### طباعة كائن بدون `operator<<`

<!-- compile-error -->
```cpp
#include <iostream>
struct P { int x = 1; };
int main()
{
    P p;
    std::cout << p;
    return 0;
}
```

```text
main.cpp:6:15: error: no match for 'operator<<' (operand types are 'std::ostream' {aka 'std::basic_ostream<char>'} and 'P')
```

**المعنى:** «لا يوجد `operator<<` يناسب الطرفين `std::ostream` و`P`». المترجم لا يعرف كيف يطبع صنفك؛ عرّف `std::ostream& operator<<(std::ostream&, const P&)`. بعد هذا السطر يطبع g++ قائمة طويلة جدًا من المحاولات (candidates)، **تجاهلها** وركز على السطر الأول.

### نسيان `const` في العامل

إذا كتبت `Vec2 operator+(const Vec2& o)` بدون `const` في النهاية، فلن تستطيع جمع كائنين ثابتين (`const Vec2`)، وستظهر رسالة «passing 'const Vec2' as 'this' argument discards qualifiers». الحل: أضف `const` بعد القوسين للعوامل التي لا تعدّل الكائن.

## تمارين

### التمرين 1

اكتب `struct Money` فيه `pounds` (عدد صحيح) و`piasters` (قروش 0-99)، وعرّف `operator+` (مع ترحيل القروش الزائدة) و`operator<<` بشكل `12.05 جنيه`.

```cpp exercise
#include <iostream>

int main()
{
    // Money a{10, 75}, b{5, 50}; std::cout << a + b << "\n";  // 16.25 جنيه
    return 0;
}
```

```cpp solution
#include <iomanip>
#include <iostream>

struct Money
{
    int pounds = 0;
    int piasters = 0;

    Money operator+(const Money& o) const
    {
        int total = (pounds + o.pounds) * 100 + piasters + o.piasters;
        return {total / 100, total % 100};
    }
};

std::ostream& operator<<(std::ostream& out, const Money& m)
{
    return out << m.pounds << "." << std::setw(2) << std::setfill('0') << m.piasters
               << std::setfill(' ') << " جنيه";
}

int main()
{
    Money a{10, 75}, b{5, 50};
    std::cout << a + b << "\n";
    std::cout << Money{3, 2} << "\n";
    return 0;
}
```

```text output
16.25 جنيه
3.02 جنيه
```

### التمرين 2

أضف إلى `Vec2` العامل `operator-()` الأحادي (يعكس الإشارة: `-v`) والعامل `!=`.

```cpp exercise
#include <iostream>

struct Vec2
{
    double x = 0, y = 0;
};

int main()
{
    // Vec2 v{3, -1}; Vec2 n = -v;  // (-3, 1)
    return 0;
}
```

```cpp solution
#include <iostream>

struct Vec2
{
    double x = 0, y = 0;
    Vec2 operator-() const { return {-x, -y}; }
    bool operator==(const Vec2& o) const { return x == o.x && y == o.y; }
    bool operator!=(const Vec2& o) const { return !(*this == o); }
};

std::ostream& operator<<(std::ostream& out, const Vec2& v)
{
    return out << "(" << v.x << ", " << v.y << ")";
}

int main()
{
    Vec2 v{3, -1};
    Vec2 n = -v;
    std::cout << n << "\n";
    std::cout << std::boolalpha << (v != n) << "\n";
    return 0;
}
```

```text output
(-3, 1)
true
```

### التمرين 3

اكتب `struct Student { std::string name; int grade; }` وعرّف `operator<` بحيث يكون الطالب «أصغر» إذا كانت درجته أقل، ثم اطبع اسم صاحب الدرجة الأعلى من ثلاثة طلاب.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

struct Student
{
    std::string name;
    int grade = 0;
    bool operator<(const Student& o) const { return grade < o.grade; }
};

int main()
{
    Student a{"Rana", 88}, b{"Adel", 93}, c{"Mai", 79};
    Student best = a;
    if (best < b)
        best = b;
    if (best < c)
        best = c;
    std::cout << best.name << "\n";
    return 0;
}
```

```text output
Adel
```

## اختبر نفسك

```quiz
{"question": "ماذا يحوّل المترجم إليه التعبير a + b إذا كان a كائنًا من صنفك؟", "choices": ["خطأ دائمًا", "a.operator+(b) أو operator+(a, b)", "add(a, b)", "a.plus(b)"], "answer": 1, "explanation": "العوامل دوال بأسماء خاصة تبدأ بـ operator."}
```

```quiz
{"question": "لماذا نكتب operator<< خارج الصنف؟", "choices": ["لأنه أسرع", "لأن الطرف الأيسر هو std::ostream وليس كائننا", "لأنه لا يمكن كتابة دوال داخل الصنف", "لا سبب"], "answer": 1, "explanation": "في std::cout << obj الطرف الأيسر cout، فالدالة العضو في صنفنا لا تناسب."}
```

```quiz
{"question": "ماذا يجب أن تُرجع operator+=؟", "choices": ["void", "مرجعًا للكائن نفسه *this", "كائنًا جديدًا", "bool"], "answer": 1, "explanation": "تُرجع *this بالمرجع لتسمح بالسلاسل مثل a += b += c."}
```

```quiz
{"question": "أي مما يلي غير مسموح؟", "choices": ["تحميل + لصنف كسر", "تحميل == لصنف تاريخ", "اختراع عامل جديد `**` للأس", "تحميل [] لصنف قائمة"], "answer": 2, "explanation": "يمكن فقط تحميل العوامل الموجودة، ولا يمكن اختراع رموز جديدة."}
```

## الخلاصة

- العامل دالة اسمها `operator+` أو `operator==` أو `operator<<`...
- العوامل التي لا تعدّل الكائن تكون `const` وتُرجع كائنًا جديدًا.
- `+=` تعدّل وتُرجع `*this`، و`<<` تُكتب خارج الصنف وتُرجع `std::ostream&`.
- اجعل معنى العامل بديهيًا، و`<=>` في C++20 يولّد المقارنات تلقائيًا.
