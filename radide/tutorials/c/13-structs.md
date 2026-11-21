# الدرس 13: الهياكل `struct` والتعدادات `enum`

الطالب له اسم وعمر ومعدل. بدل ثلاثة متغيرات منفصلة لكل طالب، نجمعها في **هيكل** (struct) واحد. هذا أقرب شيء في C إلى «الكائنات» في اللغات الأخرى.

> **تشبيه:** الـ `struct` مثل **استمارة** فيها خانات: الاسم، العمر، المعدل. تعريف الـ `struct` هو تصميم الاستمارة، وكل متغير منه استمارة مملوءة لطالب معين.

## تعريف هيكل واستخدامه

```c run
#include <stdio.h>
#include <string.h>

struct Student {
    char name[40];
    int age;
    double gpa;
};

int main(void)
{
    struct Student s1;
    strcpy(s1.name, "Mona");
    s1.age = 20;
    s1.gpa = 3.6;

    struct Student s2 = {"Omar", 22, 3.1};   // تهيئة مباشرة

    printf("%s (%d) GPA %.1f\n", s1.name, s1.age, s1.gpa);
    printf("%s (%d) GPA %.1f\n", s2.name, s2.age, s2.gpa);
    return 0;
}
```

```text output
Mona (20) GPA 3.6
Omar (22) GPA 3.1
```

- نصل إلى أعضاء الهيكل بالنقطة: `s1.age`.
- لاحظ الفاصلة المنقوطة بعد `}` في تعريف الهيكل. نسيانها خطأ شائع!

## `typedef`: اسم أقصر

كتابة `struct Student` في كل مرة مملة. `typedef` تعطي النوع اسمًا مختصرًا:

```c run
#include <stdio.h>

typedef struct {
    double x;
    double y;
} Point;

double dist2(Point a, Point b)
{
    double dx = a.x - b.x, dy = a.y - b.y;
    return dx * dx + dy * dy;
}

int main(void)
{
    Point p = {0, 0};
    Point q = {.x = 3, .y = 4};       // تهيئة بأسماء الأعضاء
    printf("مربع المسافة = %.0f\n", dist2(p, q));
    return 0;
}
```

```text output
مربع المسافة = 25
```

## مصفوفة من الهياكل

```c run
#include <stdio.h>

typedef struct {
    const char *name;
    int price;
    int qty;
} Item;

int main(void)
{
    Item cart[] = {
        {"Pen", 5, 10},
        {"Notebook", 25, 3},
        {"Bag", 300, 1},
    };
    int n = sizeof(cart) / sizeof(cart[0]);
    int total = 0;
    for (int i = 0; i < n; i++) {
        int line = cart[i].price * cart[i].qty;
        printf("%-10s %3d x %2d = %4d\n", cart[i].name, cart[i].price, cart[i].qty, line);
        total += line;
    }
    printf("الإجمالي: %d\n", total);
    return 0;
}
```

```text output
Pen          5 x 10 =   50
Notebook    25 x  3 =   75
Bag        300 x  1 =  300
الإجمالي: 425
```

`%-10s` تطبع النص في عرض 10 خانات محاذيًا لليسار، فتصطف الأعمدة.

## مؤشر إلى هيكل والعامل `->`

لكي تعدل دالة هيكلًا نمرر عنوانه. وللوصول للأعضاء عبر المؤشر نستخدم السهم `->`:

```c run
#include <stdio.h>

typedef struct {
    char owner[30];
    double balance;
} Account;

void deposit(Account *acc, double amount)
{
    acc->balance += amount;          // مثل (*acc).balance
}

int withdraw(Account *acc, double amount)
{
    if (amount > acc->balance)
        return 0;
    acc->balance -= amount;
    return 1;
}

int main(void)
{
    Account a = {"Sara", 1000};
    deposit(&a, 250);
    if (!withdraw(&a, 5000))
        printf("الرصيد لا يكفي\n");
    withdraw(&a, 200);
    printf("%s: %.2f\n", a.owner, a.balance);
    return 0;
}
```

```text output
الرصيد لا يكفي
Sara: 1050.00
```

## التعداد `enum`

`enum` يعطي أسماءً واضحة لمجموعة ثوابت صحيحة:

```c run
#include <stdio.h>

typedef enum { RED, YELLOW, GREEN } Light;

const char *action(Light l)
{
    switch (l) {
    case RED: return "قف";
    case YELLOW: return "استعد";
    case GREEN: return "انطلق";
    }
    return "?";
}

int main(void)
{
    for (Light l = RED; l <= GREEN; l++)
        printf("%d: %s\n", l, action(l));
    return 0;
}
```

```text output
0: قف
1: استعد
2: انطلق
```

القيم تبدأ من 0 تلقائيًا. الكود `if (light == GREEN)` أوضح بكثير من `if (light == 2)`.

## أخطاء شائعة

- **نسيان `;` بعد تعريف `struct`.**
- **استخدام `.` مع مؤشر:** إن كان `p` مؤشرًا إلى هيكل استخدم `p->x` لا `p.x`.
- **نسخ النصوص بالإسناد:** `s.name = "Ali";` خطأ إن كان `name` مصفوفة؛ استخدم `strcpy`.
- **تمرير هيكل كبير بالقيمة:** يُنسخ كله. مرر مؤشرًا (`const Student *`) للسرعة.

## تمارين

### التمرين 1

عرّف هيكل `Rect` له `width` و`height` (أعداد صحيحة)، واكتب دالة `area` ترجع المساحة:

```c exercise
#include <stdio.h>

// عرّف Rect هنا

int main(void)
{
    // Rect r = {7, 3};
    // printf("%d\n", area(r));
    return 0;
}
```

```c solution
#include <stdio.h>

typedef struct {
    int width;
    int height;
} Rect;

int area(Rect r)
{
    return r.width * r.height;
}

int main(void)
{
    Rect r = {7, 3};
    printf("%d\n", area(r));
    return 0;
}
```

```text output
21
```

### التمرين 2

ابحث في مصفوفة الطلاب عن صاحب أعلى درجة واطبع اسمه:

```c exercise
#include <stdio.h>

typedef struct {
    const char *name;
    int mark;
} Student;

int main(void)
{
    Student cls[] = {{"Ali", 71}, {"Huda", 94}, {"Karim", 88}};
    // اطبع: الأول: Huda (94)
    return 0;
}
```

```c solution
#include <stdio.h>

typedef struct {
    const char *name;
    int mark;
} Student;

int main(void)
{
    Student cls[] = {{"Ali", 71}, {"Huda", 94}, {"Karim", 88}};
    int best = 0;
    for (int i = 1; i < 3; i++)
        if (cls[i].mark > cls[best].mark)
            best = i;
    printf("الأول: %s (%d)\n", cls[best].name, cls[best].mark);
    return 0;
}
```

```text output
الأول: Huda (94)
```

## اختبر نفسك

```quiz
{"question": "كيف نصل إلى العضو age عبر مؤشر p إلى هيكل؟", "choices": ["p.age", "p->age", "*p.age", "&p.age"], "answer": 1, "explanation": "السهم -> للوصول عبر المؤشر، وهو اختصار (*p).age."}
```

```quiz
{"question": "ما فائدة typedef؟", "choices": ["تسريع البرنامج", "إعطاء النوع اسمًا مختصرًا", "حجز الذاكرة", "طباعة الهيكل"], "answer": 1, "explanation": "typedef تعطي اسمًا جديدًا للنوع لنكتب Point بدل struct Point."}
```

```quiz
{"question": "في `enum { A, B, C }` ما قيمة C؟", "choices": ["1", "2", "3", "'C'"], "answer": 1, "explanation": "القيم تبدأ من 0: A=0 وB=1 وC=2."}
```

## الخلاصة

- `struct` يجمع بيانات مختلفة الأنواع في وحدة واحدة، و`typedef` يختصر اسمه.
- `.` للوصول للأعضاء، و`->` عبر المؤشر.
- مرر مؤشرًا للهيكل لتعديله أو لتجنب النسخ.
- `enum` يعطي أسماء واضحة لثوابت صحيحة.
