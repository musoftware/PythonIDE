# الدرس 16: المُنشئ والمُهدِّم (Constructors and Destructors)

في الدرس السابق كنا نصنع الكائن ثم نستدعي `setName` و`setSize` لكي نعطيه قيمه. لكن ماذا لو نسي المبرمج ذلك؟ سيبقى الكائن في حالة ناقصة. الحل: **المُنشئ** (constructor)، دالة خاصة تعمل **تلقائيًا** لحظة ولادة الكائن.

> **تشبيه:** المُنشئ مثل **شهادة الميلاد**: لا يولد طفل بدون اسم وتاريخ ميلاد. والمُهدِّم (destructor) مثل **إجراءات المغادرة** في الفندق: تُنفذ تلقائيًا عند الرحيل، فتعيد المفتاح وتدفع الحساب.

## المُنشئ

- اسمه **نفس اسم الصنف**.
- **ليس له نوع مُرجَع**، ولا حتى `void`.
- يُستدعى تلقائيًا عند إنشاء الكائن.

```cpp run
#include <iostream>
#include <string>

class Student
{
private:
    std::string name;
    int grade;

public:
    Student(const std::string& n, int g)   // المُنشئ
        : name(n), grade(g)               // قائمة التهيئة
    {
        std::cout << "تم تسجيل " << name << "\n";
    }

    void print() const { std::cout << name << ": " << grade << "\n"; }
};

int main()
{
    Student a("نادين", 91);
    Student b{"طارق", 78};    // نفس الشيء بالأقواس المعقوصة
    a.print();
    b.print();
    return 0;
}
```

```text output
تم تسجيل نادين
تم تسجيل طارق
نادين: 91
طارق: 78
```

### قائمة التهيئة (Member Initializer List)

الجزء `: name(n), grade(g)` بعد القوسين يسمى **قائمة التهيئة**. هي الطريقة المفضلة لإعطاء الأعضاء قيمهم، لأنها **تُنشئ** العضو مباشرة بالقيمة الصحيحة بدلًا من إنشائه فارغًا ثم إسناد قيمة له. وهي **ضرورية** للأعضاء الثابتة `const` والمراجع.

## عدة مُنشئات (التحميل الزائد)

يمكن أن يكون للصنف أكثر من مُنشئ بمعاملات مختلفة، بما فيها **المُنشئ الافتراضي** (default constructor) الذي لا يأخذ معاملات:

```cpp run
#include <iostream>

class Time
{
private:
    int hours;
    int minutes;

public:
    Time() : hours(0), minutes(0) {}                   // افتراضي
    Time(int h, int m) : hours(h), minutes(m)
    {
        if (minutes >= 60)                             // تصحيح القيم
        {
            hours += minutes / 60;
            minutes %= 60;
        }
    }
    explicit Time(int totalMinutes) : Time(totalMinutes / 60, totalMinutes % 60) {}  // تفويض

    void print() const
    {
        std::cout << hours << ":" << (minutes < 10 ? "0" : "") << minutes << "\n";
    }
};

int main()
{
    Time midnight;          // Time()
    Time lunch(13, 5);      // Time(int, int)
    Time weird(1, 150);     // تُصحح إلى 3:30
    Time movie(135);        // Time(int) = 2:15
    midnight.print();
    lunch.print();
    weird.print();
    movie.print();
    return 0;
}
```

```text output
0:00
13:05
3:30
2:15
```

- `Time(int totalMinutes) : Time(...)` مُنشئ يفوّض العمل لمُنشئ آخر (delegating constructor).
- `explicit` تمنع التحويل التلقائي الخفي؛ فبدونها كان يمكن كتابة `Time t = 135;` بالخطأ.

> **ملحوظة مهمة:** إذا كتبت أي مُنشئ بنفسك، لا يصنع المترجم المُنشئ الافتراضي تلقائيًا. إذا أردته فاكتبه، أو اكتب `Time() = default;`.

## المُهدِّم (Destructor)

- اسمه `~` ثم اسم الصنف: `~Student()`.
- لا يأخذ معاملات، ولا يُرجع شيئًا.
- يُستدعى تلقائيًا عند **زوال** الكائن (نهاية النطاق، أو حذفه).

```cpp run
#include <iostream>
#include <string>

class Logger
{
private:
    std::string task;

public:
    explicit Logger(const std::string& t) : task(t)
    {
        std::cout << "[بدء] " << task << "\n";
    }
    ~Logger()
    {
        std::cout << "[انتهاء] " << task << "\n";
    }
};

void work()
{
    Logger log("تحميل البيانات");
    std::cout << "  ...جارٍ العمل\n";
}   // المُهدِّم يعمل هنا

int main()
{
    Logger app("البرنامج");
    work();
    {
        Logger a("المهمة أ");
        Logger b("المهمة ب");
    }   // b تُهدم أولًا ثم a (عكس ترتيب الإنشاء)
    std::cout << "قبل نهاية main\n";
    return 0;
}
```

```text output
[بدء] البرنامج
[بدء] تحميل البيانات
  ...جارٍ العمل
[انتهاء] تحميل البيانات
[بدء] المهمة أ
[بدء] المهمة ب
[انتهاء] المهمة ب
[انتهاء] المهمة أ
قبل نهاية main
[انتهاء] البرنامج
```

لاحظ أن الكائنات تُهدم **بعكس ترتيب إنشائها**، مثل كومة أطباق: آخر طبق وُضع هو أول طبق يُرفع.

### متى نحتاج إلى كتابة مُهدِّم؟

عندما يحجز الكائن **موردًا** يجب تحريره: ذاكرة بـ `new`، أو ملف مفتوح، أو اتصال بالشبكة. هذه هي فكرة **RAII** التي رأيناها مع المؤشرات الذكية: الحجز في المُنشئ، والتحرير في المُهدِّم.

لكن إذا كانت أعضاء الصنف من أنواع تدير نفسها (`std::string`، و`std::vector`، و`std::unique_ptr`) فلا تحتاج مُهدِّمًا أصلًا، لأن مُهدِّماتها تعمل تلقائيًا. هذه **قاعدة الصفر** (Rule of Zero): أفضل صنف هو الذي لا يحتاج مُهدِّمًا ولا نسخًا مخصصًا.

## الأعضاء الثابتة والأعضاء الساكنة

```cpp run
#include <iostream>
#include <string>

class Order
{
private:
    const int id;                 // ثابت: يُعطى قيمة في قائمة التهيئة فقط
    std::string item;
    static int count;             // ساكن: عضو واحد مشترك بين كل الكائنات

public:
    explicit Order(const std::string& it) : id(++count), item(it) {}
    void print() const { std::cout << "طلب #" << id << ": " << item << "\n"; }
    static int total() { return count; }
};

int Order::count = 0;             // تعريف العضو الساكن

int main()
{
    Order a("Pizza");
    Order b("Burger");
    Order c("Salad");
    a.print();
    c.print();
    std::cout << "عدد الطلبات: " << Order::total() << "\n";
    return 0;
}
```

```text output
طلب #1: Pizza
طلب #3: Salad
عدد الطلبات: 3
```

العضو `static` يخص **الصنف** نفسه لا كائنًا بعينه، مثل عداد على باب المطعم يعرف كم طلبًا خرج.

## أخطاء شائعة

### لا يوجد مُنشئ افتراضي

<!-- compile-error -->
```cpp
class Point
{
public:
    Point(int x, int y) : px(x), py(y) {}
private:
    int px, py;
};
int main()
{
    Point p;
    return 0;
}
```

```text
main.cpp:10:11: error: no matching function for call to 'Point::Point()'
```

**المعنى:** «لا توجد دالة مطابقة لاستدعاء `Point::Point()`». كتبت مُنشئًا يأخذ معاملين، فلم يعد المُنشئ الافتراضي موجودًا. إما أن تمرر القيم `Point p(1, 2);` أو تضيف `Point() : px(0), py(0) {}`.

### كتابة نوع مُرجَع للمُنشئ

<!-- compile-error -->
```cpp
class A
{
public:
    void A() {}
};
int main() { return 0; }
```

```text
main.cpp:4:12: error: return type specification for constructor invalid
```

**المعنى:** «تحديد نوع مُرجَع للمُنشئ غير صالح». المُنشئ لا يُكتب قبله `void` ولا أي نوع.

### ترتيب قائمة التهيئة

الأعضاء تُهيأ **بترتيب تعريفها في الصنف**، لا بترتيب كتابتها في قائمة التهيئة. إذا اختلف الترتيبان يحذرك g++ بالتحذير `-Wreorder`. اكتبها دائمًا بنفس الترتيب.

## تمارين

### التمرين 1

اكتب صنف `Circle` بمُنشئ يأخذ نصف القطر (ويجعله صفرًا إذا كان سالبًا)، ومُنشئ افتراضي بنصف قطر 1، ودالة `area()`.

```cpp exercise
#include <iostream>

int main()
{
    // Circle a; Circle b(2); Circle c(-5);
    return 0;
}
```

```cpp solution
#include <iostream>

class Circle
{
private:
    double radius;

public:
    Circle() : radius(1) {}
    explicit Circle(double r) : radius(r < 0 ? 0 : r) {}
    double area() const { return 3.14159 * radius * radius; }
};

int main()
{
    Circle a;
    Circle b(2);
    Circle c(-5);
    std::cout << a.area() << "\n" << b.area() << "\n" << c.area() << "\n";
    return 0;
}
```

```text output
3.14159
12.5664
0
```

### التمرين 2

اكتب صنف `Room` يطبع «دخل X» في المُنشئ و«خرج X» في المُهدِّم، ثم أنشئ ثلاث غرف بحيث يكون الناتج كما يلي بالضبط.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    // المطلوب:
    // دخل 1
    // دخل 2
    // خرج 2
    // دخل 3
    // خرج 3
    // خرج 1
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

class Room
{
private:
    std::string name;

public:
    explicit Room(const std::string& n) : name(n) { std::cout << "دخل " << name << "\n"; }
    ~Room() { std::cout << "خرج " << name << "\n"; }
};

int main()
{
    Room r1("1");
    {
        Room r2("2");
    }
    {
        Room r3("3");
    }
    return 0;
}
```

```text output
دخل 1
دخل 2
خرج 2
دخل 3
خرج 3
خرج 1
```

### التمرين 3

اكتب صنف `Ticket` له رقم ثابت `const int` يُعطى تلقائيًا من عداد ساكن يبدأ من 100، واطبع أرقام ثلاث تذاكر.

```cpp exercise
#include <iostream>

int main()
{
    // Ticket a, b, c; اطبع a.number() ...
    return 0;
}
```

```cpp solution
#include <iostream>

class Ticket
{
private:
    static int next;
    const int num;

public:
    Ticket() : num(next++) {}
    int number() const { return num; }
};

int Ticket::next = 100;

int main()
{
    Ticket a, b, c;
    std::cout << a.number() << " " << b.number() << " " << c.number() << "\n";
    return 0;
}
```

```text output
100 101 102
```

## اختبر نفسك

```quiz
{"question": "متى يُستدعى المُنشئ؟", "choices": ["عندما نستدعيه يدويًا فقط", "تلقائيًا عند إنشاء الكائن", "عند نهاية البرنامج", "عند طباعة الكائن"], "answer": 1, "explanation": "المُنشئ يعمل تلقائيًا لحظة إنشاء الكائن."}
```

```quiz
{"question": "ما اسم المُهدِّم للصنف Car؟", "choices": ["Car()", "~Car()", "delete Car()", "Car::end()"], "answer": 1, "explanation": "المُهدِّم اسمه ~ ثم اسم الصنف، بلا معاملات ولا نوع مُرجَع."}
```

```quiz
{"question": "أنشأنا الكائنات a ثم b ثم c في نفس النطاق. بأي ترتيب تُهدم؟", "choices": ["a ثم b ثم c", "c ثم b ثم a", "عشوائي", "لا تُهدم"], "answer": 1, "explanation": "تُهدم الكائنات بعكس ترتيب إنشائها."}
```

```quiz
{"question": "كتبت مُنشئًا Point(int, int) فقط. ماذا يحدث عند Point p;؟", "choices": ["تعمل وقيمها صفر", "خطأ: no matching function for call to Point::Point()", "تعمل بقيم عشوائية", "تحذير فقط"], "answer": 1, "explanation": "بمجرد كتابة مُنشئ، لا يولّد المترجم المُنشئ الافتراضي تلقائيًا."}
```

```quiz
{"question": "ما فائدة قائمة التهيئة : name(n)؟", "choices": ["تجعل الكود أطول", "تُنشئ الأعضاء مباشرة بالقيمة الصحيحة وهي ضرورية لأعضاء const", "تحذف الكائن", "تجعل الأعضاء عامة"], "answer": 1, "explanation": "قائمة التهيئة تهيئ الأعضاء مباشرة، ولا يمكن إعطاء عضو const قيمته إلا بها."}
```

## الخلاصة

- المُنشئ يحمل اسم الصنف، بلا نوع مُرجَع، ويعمل عند الإنشاء.
- استخدم قائمة التهيئة `: a(x), b(y)`.
- يمكن تحميل المُنشئات، و`explicit` تمنع التحويلات الخفية.
- المُهدِّم `~Name()` يعمل عند الزوال، والكائنات تُهدم بعكس ترتيب إنشائها.
- RAII وقاعدة الصفر: دع الأعضاء الذكية تدير الموارد.
