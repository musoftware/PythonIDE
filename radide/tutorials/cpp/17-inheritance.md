# الدرس 17: الوراثة (Inheritance)

كثير من الأشياء في الحياة تتشارك صفات: السيارة والدراجة النارية كلاهما **مركبة** لها سرعة ولون. الموظف والطالب كلاهما **شخص** له اسم وعمر. **الوراثة** تسمح لنا بكتابة الصفات المشتركة مرة واحدة في **صنف أساسي** (base class)، ثم نبني عليه **أصنافًا مشتقة** (derived classes) تضيف ما يميزها.

> **تشبيه:** الابن يرث من أبيه لون العينين وطول القامة، ثم تكون له مواهبه الخاصة. الصنف المشتق يرث بيانات ودوال الصنف الأساسي، ثم يضيف عليها.

العلاقة هنا هي «**هو نوع من**» (is-a): الموظف **هو نوع من** الأشخاص، والدائرة **هي نوع من** الأشكال.

## أول مثال

```cpp run
#include <iostream>
#include <string>

class Person                          // الصنف الأساسي
{
protected:                            // متاح للأصناف المشتقة
    std::string name;
    int age;

public:
    Person(const std::string& n, int a) : name(n), age(a) {}
    void introduce() const
    {
        std::cout << "أنا " << name << "، عمري " << age << " سنة\n";
    }
};

class Employee : public Person        // Employee يرث من Person
{
private:
    double salary;

public:
    Employee(const std::string& n, int a, double s)
        : Person(n, a), salary(s) {}  // استدعاء مُنشئ الأساسي أولًا

    void work() const
    {
        std::cout << name << " يعمل وراتبه " << salary << "\n";
    }
};

int main()
{
    Employee e("كريم", 30, 9000);
    e.introduce();   // موروثة من Person
    e.work();        // خاصة بـ Employee
    return 0;
}
```

```text output
أنا كريم، عمري 30 سنة
كريم يعمل وراتبه 9000
```

- `class Employee : public Person` تعني «Employee يرث علنًا من Person».
- `Person(n, a)` في قائمة التهيئة تستدعي مُنشئ الصنف الأساسي.
- `e.introduce()` تعمل رغم أننا لم نكتبها في `Employee`، لأنها موروثة.

## مستويات الوصول الثلاثة

| الكلمة | داخل الصنف نفسه | داخل الأصناف المشتقة | من الخارج |
|---|---|---|---|
| `public` | نعم | نعم | نعم |
| `protected` | نعم | نعم | لا |
| `private` | نعم | لا | لا |

استخدمنا `protected` لكي تستطيع `Employee` قراءة `name` مباشرة، مع بقائه مخفيًا عن باقي البرنامج.

## ترتيب الإنشاء والهدم

الأساس يُبنى **أولًا** ثم المشتق (مثل البيت: الأساس قبل الطوابق)، والهدم بالعكس:

```cpp run
#include <iostream>

class Base
{
public:
    Base() { std::cout << "بناء Base\n"; }
    ~Base() { std::cout << "هدم Base\n"; }
};

class Derived : public Base
{
public:
    Derived() { std::cout << "بناء Derived\n"; }
    ~Derived() { std::cout << "هدم Derived\n"; }
};

int main()
{
    Derived d;
    std::cout << "--- استخدام الكائن ---\n";
    return 0;
}
```

```text output
بناء Base
بناء Derived
--- استخدام الكائن ---
هدم Derived
هدم Base
```

## إعادة تعريف دالة في الصنف المشتق

يمكن للصنف المشتق أن يكتب دالة **بنفس اسم** دالة في الأساس، ليغير سلوكها. ويمكنه أيضًا استدعاء نسخة الأساس بـ `Base::`:

```cpp run
#include <iostream>
#include <string>

class Animal
{
protected:
    std::string name;

public:
    explicit Animal(const std::string& n) : name(n) {}
    void describe() const { std::cout << name << " حيوان"; }
};

class Bird : public Animal
{
private:
    bool canFly;

public:
    Bird(const std::string& n, bool fly) : Animal(n), canFly(fly) {}
    void describe() const
    {
        Animal::describe();   // نسخة الأساس أولًا
        std::cout << (canFly ? " يطير" : " لا يطير") << "\n";
    }
};

int main()
{
    Bird eagle("النسر", true);
    Bird penguin("البطريق", false);
    eagle.describe();
    penguin.describe();
    return 0;
}
```

```text output
النسر حيوان يطير
البطريق حيوان لا يطير
```

> **انتبه:** هذا يسمى «إخفاء» الدالة، وهو يعمل فقط عندما يعرف المترجم النوع الحقيقي للكائن. في الدرس القادم سنرى مشكلة تحدث مع المؤشرات والمراجع إلى الصنف الأساسي، وحلها السحري: `virtual`.

## سلسلة وراثة

```cpp run
#include <iostream>
#include <string>

class Vehicle
{
protected:
    int wheels;

public:
    explicit Vehicle(int w) : wheels(w) {}
    int getWheels() const { return wheels; }
};

class Car : public Vehicle
{
public:
    Car() : Vehicle(4) {}
};

class SportsCar : public Car
{
public:
    int topSpeed() const { return 300; }
};

int main()
{
    SportsCar s;
    std::cout << "عجلات: " << s.getWheels() << "، أقصى سرعة: " << s.topSpeed() << "\n";
    return 0;
}
```

```text output
عجلات: 4، أقصى سرعة: 300
```

## متى لا نستخدم الوراثة؟

ليست كل علاقة وراثة! إذا كانت العلاقة «**يملك**» (has-a) فاستخدم عضوًا بدلًا من الوراثة. السيارة **تملك** محركًا، فلا ترث `Car` من `Engine`؛ بل يكون لها عضو `Engine engine;`. هذا يسمى **التركيب** (composition)، والمحترفون يفضلونه عندما يكون مناسبًا.

## أخطاء شائعة

### الوصول إلى عضو خاص في الأساس

<!-- compile-error -->
```cpp
class Base
{
private:
    int secret = 42;
};
class Child : public Base
{
public:
    int reveal() const { return secret; }
};
int main() { Child c; return c.reveal(); }
```

```text
main.cpp:9:33: error: 'int Base::secret' is private within this context
```

**المعنى:** حتى الصنف المشتق لا يرى الأعضاء `private` في الأساس. اجعلها `protected` أو أضف دالة `public`/`protected` لقراءتها.

### نسيان استدعاء مُنشئ الأساس

<!-- compile-error -->
```cpp
class Base
{
public:
    explicit Base(int v) : value(v) {}
    int value;
};
class Child : public Base
{
public:
    Child() {}
};
int main() { Child c; return c.value; }
```

```text
main.cpp:10:13: error: no matching function for call to 'Base::Base()'
```

**المعنى:** الأساس ليس له مُنشئ افتراضي، والمشتق لم يستدعِ مُنشئه صراحة. الحل: `Child() : Base(0) {}`.

## تمارين

### التمرين 1

اكتب صنفًا أساسيًا `Shape` فيه اسم الشكل (`protected`) ودالة `printName()`، وصنفًا مشتقًا `Square` فيه طول الضلع ودالة `area()`.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    // Square s(5); s.printName(); std::cout << s.area();
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

class Shape
{
protected:
    std::string name;

public:
    explicit Shape(const std::string& n) : name(n) {}
    void printName() const { std::cout << "الشكل: " << name << "\n"; }
};

class Square : public Shape
{
private:
    double side;

public:
    explicit Square(double s) : Shape("مربع"), side(s) {}
    double area() const { return side * side; }
};

int main()
{
    Square s(5);
    s.printName();
    std::cout << "المساحة: " << s.area() << "\n";
    return 0;
}
```

```text output
الشكل: مربع
المساحة: 25
```

### التمرين 2

اكتب `Account` فيه الرصيد ودالة `deposit`، و`SavingsAccount` يرث منه ويضيف `addInterest(double rate)` التي تضيف الفائدة إلى الرصيد.

```cpp exercise
#include <iostream>

int main()
{
    // SavingsAccount s(1000); s.deposit(500); s.addInterest(0.1); اطبع الرصيد
    return 0;
}
```

```cpp solution
#include <iostream>

class Account
{
protected:
    double balance;

public:
    explicit Account(double b) : balance(b) {}
    void deposit(double amount) { balance += amount; }
    double getBalance() const { return balance; }
};

class SavingsAccount : public Account
{
public:
    explicit SavingsAccount(double b) : Account(b) {}
    void addInterest(double rate) { balance += balance * rate; }
};

int main()
{
    SavingsAccount s(1000);
    s.deposit(500);
    s.addInterest(0.1);
    std::cout << "الرصيد: " << s.getBalance() << "\n";
    return 0;
}
```

```text output
الرصيد: 1650
```

### التمرين 3

توقّع ناتج البرنامج التالي قبل تشغيله:

```cpp exercise
#include <iostream>

class A
{
public:
    A() { std::cout << "A "; }
    ~A() { std::cout << "~A "; }
};

class B : public A
{
public:
    B() { std::cout << "B "; }
    ~B() { std::cout << "~B "; }
};

int main()
{
    {
        B b;
    }
    std::cout << "\n";
    return 0;
}
```

```cpp solution
#include <iostream>

class A
{
public:
    A() { std::cout << "A "; }
    ~A() { std::cout << "~A "; }
};

class B : public A
{
public:
    B() { std::cout << "B "; }
    ~B() { std::cout << "~B "; }
};

int main()
{
    {
        B b;   // يُبنى A ثم B، ويُهدم B ثم A
    }
    std::cout << "\n";
    return 0;
}
```

```text output
A B ~B ~A
```

## اختبر نفسك

```quiz
{"question": "ما معنى class Dog : public Animal؟", "choices": ["Animal يرث من Dog", "Dog يرث من Animal", "Dog يحتوي على Animal كعضو", "خطأ ترجمة"], "answer": 1, "explanation": "الصنف المذكور بعد النقطتين هو الأساس الذي يُورث منه."}
```

```quiz
{"question": "عضو protected في الصنف الأساسي يمكن الوصول إليه من:", "choices": ["أي مكان", "الصنف نفسه والأصناف المشتقة فقط", "الصنف نفسه فقط", "main فقط"], "answer": 1, "explanation": "protected مخفي عن الخارج لكنه متاح للأصناف المشتقة."}
```

```quiz
{"question": "عند إنشاء كائن من صنف مشتق، أي مُنشئ يعمل أولًا؟", "choices": ["مُنشئ المشتق", "مُنشئ الأساس", "حسب الترتيب في الملف", "يعملان معًا"], "answer": 1, "explanation": "الأساس يُبنى أولًا ثم المشتق، والهدم بالعكس."}
```

```quiz
{"question": "السيارة تملك محركًا. ما التصميم الأفضل؟", "choices": ["class Car : public Engine", "عضو Engine داخل Car (تركيب)", "class Engine : public Car", "متغير عام"], "answer": 1, "explanation": "علاقة «يملك» تُنفذ بالتركيب، والوراثة لعلاقة «هو نوع من»."}
```

## الخلاصة

- الوراثة: `class Derived : public Base` لعلاقة «هو نوع من».
- المشتق يرث بيانات ودوال الأساس، ويضيف عليها.
- `protected` متاح للمشتقات فقط.
- استدعِ مُنشئ الأساس في قائمة التهيئة، والبناء من الأساس للمشتق والهدم بالعكس.
- علاقة «يملك» تكون بالتركيب لا بالوراثة.
