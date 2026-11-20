# الدرس 18: تعدد الأشكال والدوال الافتراضية (Polymorphism and virtual)

**تعدد الأشكال** (Polymorphism) كلمة يونانية معناها «أشكال كثيرة». الفكرة: أن تتعامل مع كائنات مختلفة **بنفس الطريقة**، وكل كائن يتصرف حسب نوعه الحقيقي.

> **تشبيه:** المدير يقول لكل الموظفين: «اعملوا!». المبرمج يكتب كودًا، والمصمم يرسم، والمحاسب يحسب. **أمر واحد**، وكل واحد ينفذه بطريقته. المدير لا يحتاج أن يعرف تفاصيل عمل كل واحد.

## المشكلة: بدون `virtual`

```cpp run
#include <iostream>

class Animal
{
public:
    void speak() const { std::cout << "...\n"; }
};

class Cat : public Animal
{
public:
    void speak() const { std::cout << "مياو\n"; }
};

void makeItSpeak(const Animal& a)
{
    a.speak();   // أي speak ستُستدعى؟
}

int main()
{
    Cat c;
    c.speak();        // مياو
    makeItSpeak(c);   // ... للأسف!
    return 0;
}
```

```text output
مياو
...
```

داخل `makeItSpeak` يرى المترجم مرجعًا من نوع `Animal`، فيستدعي `Animal::speak` رغم أن الكائن الحقيقي قطة! المترجم قرر **وقت الترجمة** بناءً على نوع المرجع.

## الحل: `virtual` و`override`

عندما نجعل الدالة **افتراضية** (`virtual`)، يتأخر القرار إلى **وقت التشغيل**، ويُستدعى إصدار النوع الحقيقي للكائن:

```cpp run
#include <iostream>

class Animal
{
public:
    virtual void speak() const { std::cout << "...\n"; }
    virtual ~Animal() = default;   // مُهدِّم افتراضي (مهم!)
};

class Cat : public Animal
{
public:
    void speak() const override { std::cout << "مياو\n"; }
};

class Dog : public Animal
{
public:
    void speak() const override { std::cout << "هاو هاو\n"; }
};

void makeItSpeak(const Animal& a)
{
    a.speak();
}

int main()
{
    Cat c;
    Dog d;
    Animal generic;
    makeItSpeak(c);
    makeItSpeak(d);
    makeItSpeak(generic);
    return 0;
}
```

```text output
مياو
هاو هاو
...
```

- `virtual` في الأساس: «هذه الدالة يمكن أن تُستبدل في المشتقات، واختر النسخة حسب الكائن الحقيقي».
- `override` في المشتق: «أنا أقصد استبدال دالة افتراضية». ليست إجبارية، لكنها **تحميك**: لو أخطأت في الاسم أو المعاملات أعطاك المترجم خطأ بدلًا من أن يصنع دالة جديدة بصمت.
- `virtual ~Animal()`: إذا كان للصنف دوال افتراضية فاجعل مُهدِّمه افتراضيًا، لكي يُهدم الكائن المشتق كاملًا عند حذفه عبر مؤشر للأساس.

## الأصناف المجردة (Abstract Classes)

أحيانًا لا يكون للدالة معنى في الأساس. ما هي مساحة «شكل» عام؟ لا نعرف! نجعلها **دالة افتراضية خالصة** (pure virtual) بكتابة `= 0`، فيصبح الصنف **مجردًا**: لا يمكن إنشاء كائن منه، ويُلزم المشتقات بكتابة الدالة.

> **تشبيه:** الصنف المجرد مثل **عقد عمل**: يقول «كل موظف يجب أن يكون له عمل»، لكنه لا يحدد العمل. كل وظيفة حقيقية تملأ التفاصيل.

```cpp run
#include <iostream>
#include <memory>
#include <string>
#include <vector>

class Shape
{
public:
    virtual double area() const = 0;            // افتراضية خالصة
    virtual std::string name() const = 0;
    virtual ~Shape() = default;

    void report() const                         // دالة عادية تستخدم الافتراضية
    {
        std::cout << name() << ": " << area() << "\n";
    }
};

class Circle : public Shape
{
    double r;

public:
    explicit Circle(double radius) : r(radius) {}
    double area() const override { return 3.14159 * r * r; }
    std::string name() const override { return "دائرة"; }
};

class Rect : public Shape
{
    double w, h;

public:
    Rect(double width, double height) : w(width), h(height) {}
    double area() const override { return w * h; }
    std::string name() const override { return "مستطيل"; }
};

int main()
{
    std::vector<std::unique_ptr<Shape>> shapes;
    shapes.push_back(std::make_unique<Circle>(1));
    shapes.push_back(std::make_unique<Rect>(3, 4));
    shapes.push_back(std::make_unique<Circle>(2));

    double total = 0;
    for (const auto& s : shapes)
    {
        s->report();          // كل شكل يتصرف حسب نوعه
        total += s->area();
    }
    std::cout << "المجموع: " << total << "\n";
    return 0;
}
```

```text output
دائرة: 3.14159
مستطيل: 12
دائرة: 12.5664
المجموع: 27.708
```

هذا هو النمط الذي وعدناك به في درس المؤشرات الذكية: `vector` واحد من `unique_ptr<Shape>` يحمل أشكالًا مختلفة، وحلقة واحدة تتعامل معها كلها. لو أضفت غدًا `Triangle` فلن تحتاج إلى تغيير الحلقة أبدًا!

## كيف يعمل `virtual` من الداخل؟ (للفضوليين)

كل صنف فيه دوال افتراضية يملك جدولًا مخفيًا اسمه **vtable** فيه عناوين دواله. وكل كائن يحمل مؤشرًا مخفيًا لجدول صنفه. عند استدعاء دالة افتراضية، يتبع البرنامج هذا المؤشر ليجد الدالة الصحيحة. التكلفة صغيرة جدًا، لذلك لا تخف من استخدام `virtual` عند الحاجة.

## مثال عملي: نظام رواتب

```cpp run
#include <iostream>
#include <memory>
#include <string>
#include <vector>

class Employee
{
protected:
    std::string name;

public:
    explicit Employee(const std::string& n) : name(n) {}
    virtual ~Employee() = default;
    virtual double salary() const = 0;
    const std::string& getName() const { return name; }
};

class Monthly : public Employee
{
    double fixed;

public:
    Monthly(const std::string& n, double f) : Employee(n), fixed(f) {}
    double salary() const override { return fixed; }
};

class Hourly : public Employee
{
    double rate;
    int hours;

public:
    Hourly(const std::string& n, double r, int h) : Employee(n), rate(r), hours(h) {}
    double salary() const override { return rate * hours; }
};

int main()
{
    std::vector<std::unique_ptr<Employee>> staff;
    staff.push_back(std::make_unique<Monthly>("Mona", 12000));
    staff.push_back(std::make_unique<Hourly>("Sameh", 150, 60));

    double payroll = 0;
    for (const auto& e : staff)
    {
        std::cout << e->getName() << ": " << e->salary() << "\n";
        payroll += e->salary();
    }
    std::cout << "إجمالي الرواتب: " << payroll << "\n";
    return 0;
}
```

```text output
Mona: 12000
Sameh: 9000
إجمالي الرواتب: 21000
```

## أخطاء شائعة

### إنشاء كائن من صنف مجرد

<!-- compile-error -->
```cpp
struct Shape
{
    virtual double area() const = 0;
};
int main()
{
    Shape s;
    return 0;
}
```

```text
main.cpp:7:11: error: cannot declare variable 's' to be of abstract type 'Shape'
```

**المعنى:** «لا يمكن تعريف المتغير `s` من النوع المجرد `Shape`». الصنف المجرد قالب ناقص؛ أنشئ كائنًا من صنف مشتق يكمل كل الدوال الخالصة.

### `override` على دالة لا تطابق

<!-- compile-error -->
```cpp
struct Base
{
    virtual void draw(int size) const {}
};
struct Child : Base
{
    void draw(double size) const override {}
};
int main() { return 0; }
```

```text
main.cpp:7:10: error: 'void Child::draw(double) const' marked 'override', but does not override
```

**المعنى:** «الدالة معلَّمة `override` لكنها لا تستبدل شيئًا». المعامل هنا `double` وفي الأساس `int`، فهي دالة مختلفة. بدون `override` لكان البرنامج يعمل بشكل خاطئ بصمت. لهذا اكتب `override` دائمًا.

### نسيان المُهدِّم الافتراضي

إذا حذفت كائنًا مشتقًا عبر مؤشر للأساس (`unique_ptr<Base>`) والمُهدِّم ليس `virtual`، فلن يعمل مُهدِّم المشتق، وقد تتسرب موارده. القاعدة: **صنف فيه `virtual` = مُهدِّم `virtual`**.

## تمارين

### التمرين 1

أضف صنفًا `Cow` إلى مثال الحيوانات، وضع قطة وكلبًا وبقرة في `vector<unique_ptr<Animal>>` واجعلها كلها تتكلم.

```cpp exercise
#include <iostream>
#include <memory>
#include <vector>

class Animal
{
public:
    virtual void speak() const = 0;
    virtual ~Animal() = default;
};

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <memory>
#include <vector>

class Animal
{
public:
    virtual void speak() const = 0;
    virtual ~Animal() = default;
};

class Cat : public Animal
{
public:
    void speak() const override { std::cout << "مياو\n"; }
};

class Dog : public Animal
{
public:
    void speak() const override { std::cout << "هاو هاو\n"; }
};

class Cow : public Animal
{
public:
    void speak() const override { std::cout << "مووو\n"; }
};

int main()
{
    std::vector<std::unique_ptr<Animal>> farm;
    farm.push_back(std::make_unique<Cat>());
    farm.push_back(std::make_unique<Dog>());
    farm.push_back(std::make_unique<Cow>());
    for (const auto& a : farm)
        a->speak();
    return 0;
}
```

```text output
مياو
هاو هاو
مووو
```

### التمرين 2

أضف صنف `Triangle` (القاعدة والارتفاع، المساحة = نصف القاعدة × الارتفاع) إلى مثال الأشكال، واطبع تقريره.

```cpp exercise
#include <iostream>
#include <string>

class Shape
{
public:
    virtual double area() const = 0;
    virtual std::string name() const = 0;
    virtual ~Shape() = default;
    void report() const { std::cout << name() << ": " << area() << "\n"; }
};

int main()
{
    // Triangle t(6, 4); t.report();
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

class Shape
{
public:
    virtual double area() const = 0;
    virtual std::string name() const = 0;
    virtual ~Shape() = default;
    void report() const { std::cout << name() << ": " << area() << "\n"; }
};

class Triangle : public Shape
{
    double base, height;

public:
    Triangle(double b, double h) : base(b), height(h) {}
    double area() const override { return 0.5 * base * height; }
    std::string name() const override { return "مثلث"; }
};

int main()
{
    Triangle t(6, 4);
    t.report();
    return 0;
}
```

```text output
مثلث: 12
```

### التمرين 3

اكتب صنفًا مجردًا `Payment` فيه `virtual double fee(double amount) const = 0`، وصنفين: `Cash` (بلا رسوم) و`Card` (رسوم 2%). اطبع رسوم دفع 500 بكل طريقة.

```cpp exercise
#include <iostream>
#include <memory>
#include <vector>

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <memory>
#include <string>
#include <vector>

class Payment
{
public:
    virtual double fee(double amount) const = 0;
    virtual std::string name() const = 0;
    virtual ~Payment() = default;
};

class Cash : public Payment
{
public:
    double fee(double) const override { return 0; }
    std::string name() const override { return "نقدًا"; }
};

class Card : public Payment
{
public:
    double fee(double amount) const override { return amount * 0.02; }
    std::string name() const override { return "بطاقة"; }
};

int main()
{
    std::vector<std::unique_ptr<Payment>> methods;
    methods.push_back(std::make_unique<Cash>());
    methods.push_back(std::make_unique<Card>());
    for (const auto& m : methods)
        std::cout << m->name() << ": " << m->fee(500) << "\n";
    return 0;
}
```

```text output
نقدًا: 0
بطاقة: 10
```

## اختبر نفسك

```quiz
{"question": "ما فائدة virtual؟", "choices": ["تسريع الدالة", "اختيار نسخة الدالة حسب النوع الحقيقي للكائن وقت التشغيل", "منع الوراثة", "جعل الدالة خاصة"], "answer": 1, "explanation": "الدالة الافتراضية تُختار حسب الكائن الحقيقي حتى عبر مرجع أو مؤشر للأساس."}
```

```quiz
{"question": "ماذا تعني virtual double area() const = 0;؟", "choices": ["دالة تُرجع صفرًا", "دالة افتراضية خالصة تجعل الصنف مجردًا", "دالة محذوفة", "خطأ ترجمة"], "answer": 1, "explanation": "= 0 تعني أن الأساس لا يعرّفها، وعلى المشتقات تعريفها."}
```

```quiz
{"question": "لماذا نكتب override؟", "choices": ["إجبارية دائمًا", "ليتأكد المترجم أننا نستبدل دالة افتراضية فعلًا", "لتسريع البرنامج", "لجعل الدالة virtual في الأساس"], "answer": 1, "explanation": "لو لم تطابق الدالة دالة افتراضية في الأساس أعطى المترجم خطأ بدل السلوك الخاطئ الصامت."}
```

```quiz
{"question": "صنف فيه دوال virtual. كيف يجب أن يكون مُهدِّمه؟", "choices": ["خاص", "افتراضي virtual", "محذوف", "لا يهم"], "answer": 1, "explanation": "المُهدِّم الافتراضي يضمن هدم الكائن المشتق كاملًا عند حذفه عبر مؤشر للأساس."}
```

## الخلاصة

- تعدد الأشكال: أمر واحد، وكل كائن ينفذه بطريقته.
- `virtual` في الأساس، و`override` في المشتق.
- `= 0` دالة خالصة تجعل الصنف مجردًا لا يُنشأ منه كائن.
- `vector<unique_ptr<Base>>` لتخزين أنواع مختلفة معًا.
- صنف فيه `virtual` يحتاج مُهدِّمًا `virtual`.
