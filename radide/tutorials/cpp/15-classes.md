# الدرس 15: الأصناف والكائنات (Classes and Objects)

وصلنا إلى قلب C++: **البرمجة كائنية التوجه** (Object-Oriented Programming، واختصارها OOP). الفكرة أن نبني البرنامج من **كائنات** تشبه أشياء العالم الحقيقي: سيارة، وحساب بنكي، وطالب، وزر في نافذة.

## الصنف والكائن

- **الصنف** (class): **المخطط** أو التصميم. يصف ما هي البيانات وما هي الأفعال.
- **الكائن** (object): **نسخة حقيقية** مبنية من هذا المخطط.

> **تشبيه:** الصنف مثل **قالب الكعك**، والكائنات هي **الكعكات** نفسها. قالب واحد يصنع عددًا لا نهائيًا من الكعكات، وكل كعكة مستقلة: يمكن أن تزين إحداها بالشوكولاتة والأخرى بالفراولة.

## من `struct` إلى `class`

في C++ الفرق التقني بين `struct` و`class` صغير جدًا: أعضاء `struct` **عامة** افتراضيًا، وأعضاء `class` **خاصة** افتراضيًا. لكن بالعرف:

- `struct` لمجموعة بيانات بسيطة.
- `class` لكائن له سلوك وقواعد يحميها.

## التغليف (Encapsulation): `private` و`public`

**التغليف** يعني إخفاء البيانات الداخلية، والسماح بالوصول إليها فقط من خلال دوال آمنة نتحكم فيها.

> **تشبيه:** ماكينة الصرّاف الآلي: لا يمكنك فتحها وأخذ النقود مباشرة (`private`)، بل تتعامل معها عبر أزرار محددة: سحب، وإيداع، واستعلام (`public`). والماكينة تتأكد من كل عملية قبل تنفيذها.

```cpp run
#include <iostream>
#include <string>

class BankAccount
{
private:                 // لا يراها أحد من الخارج
    std::string owner;
    double balance = 0;

public:                  // الواجهة المتاحة للجميع
    void setOwner(const std::string& name) { owner = name; }
    std::string getOwner() const { return owner; }
    double getBalance() const { return balance; }

    void deposit(double amount)
    {
        if (amount <= 0)
        {
            std::cout << "مبلغ غير صالح\n";
            return;
        }
        balance += amount;
    }

    bool withdraw(double amount)
    {
        if (amount <= 0 || amount > balance)
        {
            std::cout << "تم رفض السحب\n";
            return false;
        }
        balance -= amount;
        return true;
    }
};

int main()
{
    BankAccount acc;          // كائن من الصنف BankAccount
    acc.setOwner("هاني");
    acc.deposit(1000);
    acc.deposit(-50);         // مرفوض
    acc.withdraw(5000);       // مرفوض
    acc.withdraw(200);
    std::cout << acc.getOwner() << ": " << acc.getBalance() << "\n";
    // acc.balance = 1000000;  // خطأ ترجمة: balance خاص!
    return 0;
}
```

```text output
مبلغ غير صالح
تم رفض السحب
هاني: 800
```

لاحظ الفائدة: لا يمكن لأي جزء من البرنامج أن يجعل الرصيد سالبًا أو يضع مبلغًا خاطئًا، لأن الطريق الوحيد إلى `balance` يمر عبر `deposit` و`withdraw` اللتين تفحصان كل شيء.

### دوال الجلب والتعيين (Getters and Setters)

الدوال مثل `getBalance()` تسمى **دوال الجلب** (getters)، ومثل `setOwner()` تسمى **دوال التعيين** (setters). لا تكتبها آليًا لكل عضو؛ اكتب فقط ما يحتاجه مستخدم الصنف فعلًا.

## عدة كائنات مستقلة

كل كائن له نسخته الخاصة من البيانات:

```cpp run
#include <iostream>
#include <string>

class Counter
{
private:
    std::string name;
    int value = 0;

public:
    void setName(const std::string& n) { name = n; }
    void increment() { value++; }
    void reset() { value = 0; }
    void show() const { std::cout << name << " = " << value << "\n"; }
};

int main()
{
    Counter visitors, downloads;
    visitors.setName("الزوار");
    downloads.setName("التحميلات");

    for (int i = 0; i < 5; i++)
        visitors.increment();
    downloads.increment();

    visitors.show();
    downloads.show();
    visitors.reset();
    visitors.show();
    return 0;
}
```

```text output
الزوار = 5
التحميلات = 1
الزوار = 0
```

## المؤشر `this`

داخل أي دالة عضو، الكلمة `this` مؤشر إلى **الكائن الحالي** الذي استُدعيت عليه الدالة. نحتاجها أحيانًا عندما يتشابه اسم المعامل مع اسم العضو:

```cpp
void setName(const std::string& name)
{
    this->name = name;   // عضو الكائن = المعامل
}
```

## تعريف الدوال خارج الصنف

في الأصناف الكبيرة نكتب **التصريح** داخل الصنف، و**التعريف** خارجه باستخدام `اسم_الصنف::`:

```cpp run
#include <iostream>

class Temperature
{
private:
    double celsius = 0;

public:
    void setCelsius(double c);
    double fahrenheit() const;
};

void Temperature::setCelsius(double c)
{
    if (c < -273.15)
        c = -273.15;   // لا شيء أبرد من الصفر المطلق
    celsius = c;
}

double Temperature::fahrenheit() const
{
    return celsius * 9 / 5 + 32;
}

int main()
{
    Temperature t;
    t.setCelsius(100);
    std::cout << t.fahrenheit() << " F\n";
    t.setCelsius(-500);
    std::cout << t.fahrenheit() << " F\n";
    return 0;
}
```

```text output
212 F
-459.67 F
```

`Temperature::` تعني «الدالة `setCelsius` التابعة للصنف `Temperature`». هذا الأسلوب يمهد لتقسيم الكود إلى ملفات `.h` و`.cpp` كما سنرى في درس الملفات المتعددة.

## أخطاء شائعة

### الوصول إلى عضو خاص

<!-- compile-error -->
```cpp
class Wallet
{
    int money = 0;
};
int main()
{
    Wallet w;
    return w.money;
}
```

```text
main.cpp:8:14: error: 'int Wallet::money' is private within this context
```

**المعنى:** «`Wallet::money` خاص في هذا السياق». أعضاء `class` خاصة افتراضيًا. إما أن تضيف دالة عامة مثل `getMoney()`، أو تضع العضو تحت `public:` إذا كان ذلك مقصودًا.

### تعديل كائن داخل دالة `const`

<!-- compile-error -->
```cpp
class Counter
{
    int value = 0;
public:
    void bump() const { value++; }
};
int main() { Counter c; c.bump(); }
```

```text
main.cpp:5:27: error: increment of member 'Counter::value' in read-only object
```

**المعنى:** «زيادة عضو في كائن للقراءة فقط». الدالة معلَّمة `const` أي وعدت ألا تغير الكائن. احذف `const` من الدوال التي تعدّل.

## تمارين

### التمرين 1

اكتب صنف `Rectangle` بعضوين خاصين `width` و`height`، ودالة `setSize(w, h)` ترفض القيم السالبة (تضع صفرًا بدلًا منها)، ودالة `area()`.

```cpp exercise
#include <iostream>

// class Rectangle { ... };

int main()
{
    // Rectangle r; r.setSize(5, 4); اطبع المساحة
    // r.setSize(-3, 4); اطبع المساحة
    return 0;
}
```

```cpp solution
#include <iostream>

class Rectangle
{
private:
    double width = 0;
    double height = 0;

public:
    void setSize(double w, double h)
    {
        width = (w < 0) ? 0 : w;
        height = (h < 0) ? 0 : h;
    }
    double area() const { return width * height; }
};

int main()
{
    Rectangle r;
    r.setSize(5, 4);
    std::cout << r.area() << "\n";
    r.setSize(-3, 4);
    std::cout << r.area() << "\n";
    return 0;
}
```

```text output
20
0
```

### التمرين 2

اكتب صنف `Player` فيه الاسم والنقاط (خاصة)، ودوال: `setName` و`addPoints(int)` (لا تقبل السالب) و`getPoints()` و`level()` التي تُرجع «مبتدئ» إذا كانت النقاط أقل من 100، و«محترف» غير ذلك.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    // Player p; p.setName("Zizo"); p.addPoints(60); p.addPoints(-10); p.addPoints(50);
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

class Player
{
private:
    std::string name;
    int points = 0;

public:
    void setName(const std::string& n) { name = n; }
    std::string getName() const { return name; }
    void addPoints(int p)
    {
        if (p > 0)
            points += p;
    }
    int getPoints() const { return points; }
    std::string level() const { return points < 100 ? "مبتدئ" : "محترف"; }
};

int main()
{
    Player p;
    p.setName("Zizo");
    p.addPoints(60);
    std::cout << p.getName() << ": " << p.getPoints() << " - " << p.level() << "\n";
    p.addPoints(-10);
    p.addPoints(50);
    std::cout << p.getName() << ": " << p.getPoints() << " - " << p.level() << "\n";
    return 0;
}
```

```text output
Zizo: 60 - مبتدئ
Zizo: 110 - محترف
```

### التمرين 3

اكتب صنف `TodoList` يحتفظ داخليًا بـ `std::vector<std::string>` خاص، وفيه `add(task)` و`done(index)` (تحذف المهمة إذا كان الفهرس صحيحًا) و`print()`.

```cpp exercise
#include <iostream>
#include <string>
#include <vector>

int main()
{
    // TodoList t; t.add("Study"); t.add("Gym"); t.add("Read"); t.done(1); t.print();
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>
#include <vector>

class TodoList
{
private:
    std::vector<std::string> tasks;

public:
    void add(const std::string& task) { tasks.push_back(task); }

    void done(std::size_t index)
    {
        if (index < tasks.size())
            tasks.erase(tasks.begin() + index);
    }

    void print() const
    {
        for (std::size_t i = 0; i < tasks.size(); i++)
            std::cout << i + 1 << ". " << tasks[i] << "\n";
    }
};

int main()
{
    TodoList t;
    t.add("Study");
    t.add("Gym");
    t.add("Read");
    t.done(1);
    t.done(10);   // فهرس خاطئ: لا يحدث شيء
    t.print();
    return 0;
}
```

```text output
1. Study
2. Read
```

## اختبر نفسك

```quiz
{"question": "ما العلاقة بين الصنف والكائن؟", "choices": ["الكائن مخطط والصنف نسخة منه", "الصنف مخطط والكائن نسخة حقيقية منه", "لا علاقة بينهما", "هما نفس الشيء"], "answer": 1, "explanation": "الصنف كالقالب، والكائنات نسخ مصنوعة منه."}
```

```quiz
{"question": "ما الوصول الافتراضي لأعضاء class؟", "choices": ["public", "private", "protected", "global"], "answer": 1, "explanation": "أعضاء class خاصة افتراضيًا، وأعضاء struct عامة افتراضيًا."}
```

```quiz
{"question": "ما الهدف من التغليف (Encapsulation)؟", "choices": ["تسريع البرنامج", "حماية البيانات والتحكم في طريقة تعديلها", "تقليل عدد الأسطر", "إخفاء الكود عن المترجم"], "answer": 1, "explanation": "نخفي البيانات ونسمح بتعديلها عبر دوال تفحص صحة القيم."}
```

```quiz
{"question": "ماذا تعني void Car::start() خارج الصنف؟", "choices": ["دالة عامة اسمها Car", "تعريف الدالة start التابعة للصنف Car", "إنشاء كائن Car", "خطأ ترجمة"], "answer": 1, "explanation": "العامل :: يربط تعريف الدالة بالصنف الذي صُرِّح عنها فيه."}
```

## الخلاصة

- الصنف مخطط، والكائن نسخة منه.
- `private` للبيانات الداخلية، و`public` للواجهة.
- التغليف يحمي البيانات عبر دوال تتحقق من القيم.
- `this` مؤشر للكائن الحالي، و`Class::func` لتعريف الدوال خارج الصنف.
