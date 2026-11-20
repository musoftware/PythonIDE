# الدرس 14: التراكيب `struct`: تجميع البيانات المترابطة

تخيّل أنك تكتب برنامجًا لإدارة الطلاب. كل طالب له اسم، وعمر، ومعدل. يمكن أن تكتب ثلاثة متغيرات منفصلة لكل طالب، لكن مع مئة طالب ستضيع! الحل: **نوع جديد** من صنعك يجمع هذه البيانات معًا، وهذا هو **التركيب** `struct`.

> **تشبيه:** الـ `struct` مثل **استمارة** فيها خانات: الاسم، العمر، المعدل. كل طالب يملأ نسخة خاصة به من نفس الاستمارة.

## تعريف struct واستخدامه

```cpp run
#include <iostream>
#include <string>

struct Student
{
    std::string name;
    int age = 0;
    double gpa = 0.0;
};   // لا تنسَ الفاصلة المنقوطة!

int main()
{
    Student s1;
    s1.name = "مريم";
    s1.age = 20;
    s1.gpa = 3.7;

    Student s2{"يوسف", 22, 3.2};   // تهيئة كل الأعضاء مرة واحدة

    std::cout << s1.name << " - " << s1.age << " سنة - المعدل " << s1.gpa << "\n";
    std::cout << s2.name << " - " << s2.age << " سنة - المعدل " << s2.gpa << "\n";
    return 0;
}
```

```text output
مريم - 20 سنة - المعدل 3.7
يوسف - 22 سنة - المعدل 3.2
```

- `name` و`age` و`gpa` تسمى **أعضاء** (members) أو **حقول** (fields).
- نصل إلى العضو بالنقطة: `s1.name`.
- `int age = 0;` قيمة افتراضية للعضو إذا لم نعطه قيمة.
- `Student` الآن **نوع** مثل `int` تمامًا، ويمكن أن نصنع منه ما نشاء.

## struct مع الدوال

نمرر الـ struct إلى الدوال كما تعلمنا: `const&` للقراءة و`&` للتعديل:

```cpp run
#include <iostream>
#include <string>

struct Point
{
    double x = 0;
    double y = 0;
};

void printPoint(const Point& p)
{
    std::cout << "(" << p.x << ", " << p.y << ")\n";
}

void moveBy(Point& p, double dx, double dy)
{
    p.x += dx;
    p.y += dy;
}

Point middle(const Point& a, const Point& b)
{
    return Point{(a.x + b.x) / 2, (a.y + b.y) / 2};
}

int main()
{
    Point a{1, 2};
    Point b{5, 8};
    printPoint(middle(a, b));
    moveBy(a, 10, 10);
    printPoint(a);
    return 0;
}
```

```text output
(3, 5)
(11, 12)
```

## دوال داخل struct

يمكن أن نضع الدوال **داخل** الـ struct نفسها، فتصبح جزءًا منها وتصل إلى أعضائها مباشرة. تسمى **دوال أعضاء** (member functions):

```cpp run
#include <iostream>
#include <string>

struct Rectangle
{
    double width = 0;
    double height = 0;

    double area() const { return width * height; }
    double perimeter() const { return 2 * (width + height); }
    bool isSquare() const { return width == height; }
};

int main()
{
    Rectangle r{4, 3};
    std::cout << "المساحة: " << r.area() << "\n";
    std::cout << "المحيط: " << r.perimeter() << "\n";
    std::cout << "مربع؟ " << (r.isSquare() ? "نعم" : "لا") << "\n";
    return 0;
}
```

```text output
المساحة: 12
المحيط: 14
مربع؟ لا
```

كلمة `const` بعد اسم الدالة تعني «هذه الدالة لا تغير أعضاء الكائن». هذه بداية **البرمجة كائنية التوجه**، وسنتوسع فيها في الدرس القادم مع `class`.

## vector من struct: قاعدة بيانات صغيرة

```cpp run
#include <iostream>
#include <string>
#include <vector>

struct Product
{
    std::string name;
    double price = 0;
    int stock = 0;
};

int main()
{
    std::vector<Product> shop = {
        {"Laptop", 15000, 3},
        {"Mouse", 250, 0},
        {"Keyboard", 600, 12},
    };
    shop.push_back({"Monitor", 4000, 5});

    double inventoryValue = 0;
    for (const Product& p : shop)
    {
        if (p.stock == 0)
            std::cout << p.name << ": نفد من المخزن\n";
        inventoryValue += p.price * p.stock;
    }
    std::cout << "قيمة المخزون: " << inventoryValue << "\n";
    return 0;
}
```

```text output
Mouse: نفد من المخزن
قيمة المخزون: 72200
```

## struct داخل struct

```cpp
struct Date
{
    int day = 1, month = 1, year = 2000;
};

struct Employee
{
    std::string name;
    Date hired;           // عضو من نوع struct آخر
};

Employee e{"سامي", {15, 3, 2021}};
std::cout << e.hired.year;   // 2021
```

## الربط المهيكل (C++17)

يمكن «فك» struct إلى متغيرات منفصلة في سطر واحد:

```cpp run
#include <iostream>
#include <string>

struct Result
{
    std::string name;
    int score;
};

int main()
{
    Result r{"Team A", 87};
    auto [team, points] = r;   // structured binding
    std::cout << team << ": " << points << "\n";
    return 0;
}
```

```text output
Team A: 87
```

## أخطاء شائعة

### نسيان الفاصلة المنقوطة بعد struct

<!-- compile-error -->
```cpp
struct Point
{
    int x;
}
int main() { return 0; }
```

```text
main.cpp:4:2: error: expected ';' after struct definition
```

**المعنى:** «كنت أنتظر `;` بعد تعريف الـ struct». هذا خطأ شائع جدًا لأن الدوال لا تحتاج فاصلة بعد `}` لكن الـ struct والـ class تحتاجانها.

### الوصول إلى عضو غير موجود

<!-- compile-error -->
```cpp
struct Point
{
    int x = 0, y = 0;
};
int main()
{
    Point p;
    return p.z;
}
```

```text
main.cpp:8:14: error: 'struct Point' has no member named 'z'
```

**المعنى:** «`struct Point` ليس فيها عضو اسمه `z`». تحقق من الاسم وحالة الأحرف.

## تمارين

### التمرين 1

عرّف `struct Book` فيها العنوان والمؤلف وعدد الصفحات، وأنشئ كتابين واطبع الكتاب الأطول.

```cpp exercise
#include <iostream>
#include <string>

// struct Book { ... };

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

struct Book
{
    std::string title;
    std::string author;
    int pages = 0;
};

int main()
{
    Book a{"The Hobbit", "Tolkien", 310};
    Book b{"Dune", "Herbert", 412};
    const Book& longer = (a.pages > b.pages) ? a : b;
    std::cout << "الأطول: " << longer.title << " (" << longer.pages << " صفحة)\n";
    return 0;
}
```

```text output
الأطول: Dune (412 صفحة)
```

### التمرين 2

عرّف `struct BankAccount` فيها `owner` و`balance` ودالتان عضوتان: `deposit(double)` و`withdraw(double)` التي ترفض السحب إذا لم يكفِ الرصيد وتُرجع `bool`.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    // BankAccount acc{"رنا", 1000};
    // acc.deposit(500); acc.withdraw(2000); acc.withdraw(300);
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

struct BankAccount
{
    std::string owner;
    double balance = 0;

    void deposit(double amount) { balance += amount; }

    bool withdraw(double amount)
    {
        if (amount > balance)
            return false;
        balance -= amount;
        return true;
    }
};

int main()
{
    BankAccount acc{"رنا", 1000};
    acc.deposit(500);
    if (!acc.withdraw(2000))
        std::cout << "الرصيد لا يكفي\n";
    acc.withdraw(300);
    std::cout << acc.owner << ": " << acc.balance << "\n";
    return 0;
}
```

```text output
الرصيد لا يكفي
رنا: 1200
```

### التمرين 3

اقرأ عدد الطلاب `n`، ثم لكل طالب اسمه ودرجته، واطبع اسم صاحب أعلى درجة.

```cpp exercise
#include <iostream>
#include <string>
#include <vector>

struct Student
{
    std::string name;
    int grade = 0;
};

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>
#include <vector>

struct Student
{
    std::string name;
    int grade = 0;
};

int main()
{
    int n = 0;
    std::cin >> n;
    std::vector<Student> list(n);
    for (Student& s : list)
        std::cin >> s.name >> s.grade;

    Student best = list[0];
    for (const Student& s : list)
        if (s.grade > best.grade)
            best = s;
    std::cout << "الأول: " << best.name << " بدرجة " << best.grade << "\n";
    return 0;
}
```

```text input
3
Ali 81
Hoda 95
Karim 77
```

```text output
الأول: Hoda بدرجة 95
```

## اختبر نفسك

```quiz
{"question": "كيف نصل إلى العضو age في المتغير s من نوع Student؟", "choices": ["s->age", "s.age", "s[age]", "age(s)"], "answer": 1, "explanation": "نستخدم النقطة مع المتغير العادي، والسهم -> مع المؤشر."}
```

```quiz
{"question": "ما الذي ينقص هنا: struct P { int x; }", "choices": ["return", "فاصلة منقوطة بعد }", "main", "#include"], "answer": 1, "explanation": "تعريف struct أو class يجب أن ينتهي بـ ;."}
```

```quiz
{"question": "ماذا تعني const بعد اسم دالة عضو مثل double area() const؟", "choices": ["الدالة تُرجع ثابتًا", "الدالة لا تغير أعضاء الكائن", "الدالة لا تأخذ معاملات", "الدالة سريعة"], "answer": 1, "explanation": "const هنا وعد بأن الدالة لا تعدل بيانات الكائن."}
```

```quiz
{"question": "أي تمرير هو الأنسب لدالة تطبع struct كبيرة؟", "choices": ["بالقيمة", "const Student&", "Student&", "Student*"], "answer": 1, "explanation": "المرجع الثابت يمنع النسخ ويمنع التعديل."}
```

## الخلاصة

- `struct` تصنع نوعًا جديدًا يجمع بيانات مترابطة.
- نصل إلى الأعضاء بالنقطة، ونهيئها بـ `{...}`.
- يمكن أن تحتوي `struct` على دوال أعضاء.
- `std::vector<Struct>` تصنع قائمة سجلات بسهولة.
- لا تنسَ `;` بعد `}` في نهاية التعريف.
