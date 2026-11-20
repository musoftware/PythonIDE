# الدرس 8: الدوال (Functions)

كلما كبر البرنامج، تكررت فيه أجزاء متشابهة وأصبح صعب القراءة. **الدالة** (Function) هي مجموعة تعليمات لها اسم، تكتبها مرة واحدة وتستدعيها كلما احتجت.

> **تشبيه:** الدالة مثل **ماكينة العصير**: تضع فيها فاكهة (المُدخلات)، فتعطيك عصيرًا (الناتج). لا يهمك ما يحدث بالداخل في كل مرة؛ يكفي أن تعرف ماذا تضع وماذا تأخذ.

## تعريف دالة واستدعاؤها

```cpp
النوع_المُرجَع اسم_الدالة(المعاملات)
{
    // الجسم
    return القيمة;
}
```

```cpp run
#include <iostream>

// دالة تأخذ عددين وتُرجع مجموعهما
int add(int a, int b)
{
    return a + b;
}

// دالة لا تُرجع شيئًا (void)
void greet()
{
    std::cout << "أهلًا بك!\n";
}

int main()
{
    greet();
    int result = add(3, 4);
    std::cout << "3 + 4 = " << result << "\n";
    std::cout << "10 + 20 = " << add(10, 20) << "\n";
    greet();
    return 0;
}
```

```text output
أهلًا بك!
3 + 4 = 7
10 + 20 = 30
أهلًا بك!
```

المصطلحات:

- **المعاملات** (Parameters): المتغيرات في تعريف الدالة، مثل `int a, int b`.
- **الوسائط** (Arguments): القيم الفعلية عند الاستدعاء، مثل `3` و`4`.
- **القيمة المُرجَعة** (Return value): ما تعطيه الدالة بالكلمة `return`.
- **`void`** تعني أن الدالة لا تُرجع قيمة؛ تقوم بعمل فقط (مثل الطباعة).

## لماذا نستخدم الدوال؟

1. **عدم التكرار:** اكتب الكود مرة واحدة واستخدمه مرات كثيرة.
2. **الوضوح:** `calculateTax(price)` أوضح بكثير من سطور الحساب نفسها.
3. **سهولة الإصلاح:** إذا وجدت خطأ تصلحه في مكان واحد.
4. **التقسيم:** تقسيم مشكلة كبيرة إلى مشكلات صغيرة.

## الدوال التي تُرجع `bool`

```cpp run
#include <iostream>

bool isEven(int n)
{
    return n % 2 == 0;
}

bool isPrime(int n)
{
    if (n < 2)
        return false;
    for (int d = 2; d * d <= n; d++)
        if (n % d == 0)
            return false;   // return تُنهي الدالة فورًا
    return true;
}

int main()
{
    for (int i = 1; i <= 10; i++)
    {
        std::cout << i << ": " << (isEven(i) ? "زوجي" : "فردي");
        if (isPrime(i))
            std::cout << "، أولي";
        std::cout << "\n";
    }
    return 0;
}
```

```text output
1: فردي
2: زوجي، أولي
3: فردي، أولي
4: زوجي
5: فردي، أولي
6: زوجي
7: فردي، أولي
8: زوجي
9: فردي
10: زوجي
```

لاحظ أن `return` تُنهي الدالة فورًا حتى لو كانت داخل حلقة.

## تصريح الدالة (Declaration) قبل `main`

المترجم يقرأ الملف من أعلى إلى أسفل، فلا بد أن يعرف الدالة قبل استدعائها. إذا أردت كتابة الدالة بعد `main`، ضع **تصريحًا** (النموذج الأولي، prototype) قبلها:

```cpp run
#include <iostream>

double average(double a, double b, double c);  // تصريح فقط

int main()
{
    std::cout << "المتوسط: " << average(70, 80, 96) << "\n";
    return 0;
}

double average(double a, double b, double c)   // التعريف الكامل
{
    return (a + b + c) / 3;
}
```

```text output
المتوسط: 82
```

## النطاق (Scope): المتغيرات المحلية

المتغيرات المعرّفة داخل دالة **محلية**: تُنشأ عند دخول الدالة وتختفي عند خروجها، ولا تراها أي دالة أخرى. حتى لو تشابهت الأسماء فهي متغيرات مختلفة:

```cpp run
#include <iostream>

void change(int x)
{
    x = 100;   // يغير النسخة المحلية فقط
    std::cout << "داخل الدالة: x = " << x << "\n";
}

int main()
{
    int x = 5;
    change(x);
    std::cout << "في main: x = " << x << "\n";
    return 0;
}
```

```text output
داخل الدالة: x = 100
في main: x = 5
```

هذا يسمى **التمرير بالقيمة** (pass by value): الدالة تأخذ **نسخة** من القيمة. في الدرس القادم سنتعلم كيف نجعل الدالة تغير المتغير الأصلي باستخدام **المراجع**.

## أخطاء شائعة

### نسيان `return` في دالة تُرجع قيمة

<!-- compile-error -->
```cpp
int square(int x)
{
    x * x;
}
int main() { return square(2); }
```

```text
main.cpp:4:1: warning: no return statement in function returning non-void [-Wreturn-type]
```

**المعنى:** «لا توجد تعليمة return في دالة لا تُرجع void». البرنامج سيترجَم، لكن القيمة المُرجعة ستكون عشوائية وقد ينهار البرنامج! اكتب `return x * x;`.

### استدعاء الدالة قبل تعريفها أو التصريح عنها

<!-- compile-error -->
```cpp
#include <iostream>
int main()
{
    std::cout << twice(4);
    return 0;
}
int twice(int n) { return n * 2; }
```

```text
main.cpp:4:18: error: 'twice' was not declared in this scope
```

**المعنى:** عندما وصل المترجم إلى السطر 4 لم يكن قد رأى `twice` بعد. ضع الدالة قبل `main` أو أضف تصريحًا لها.

### عدد خاطئ من الوسائط

<!-- compile-error -->
```cpp
int add(int a, int b) { return a + b; }
int main()
{
    return add(1);
}
```

```text
main.cpp:4:15: error: too few arguments to function 'int add(int, int)'
```

**المعنى:** «وسائط أقل من اللازم للدالة». الدالة تحتاج عددين وأعطيتها عددًا واحدًا.

## تمارين

### التمرين 1

اكتب دالة `double circleArea(double r)` تُرجع مساحة الدائرة (π × r²) باستخدام `π = 3.14159`، واطبع مساحة دائرة نصف قطرها 10.

```cpp exercise
#include <iostream>

// اكتب الدالة هنا

int main()
{
    // std::cout << circleArea(10) << "\n";
    return 0;
}
```

```cpp solution
#include <iostream>

double circleArea(double r)
{
    const double PI = 3.14159;
    return PI * r * r;
}

int main()
{
    std::cout << "المساحة: " << circleArea(10) << "\n";
    return 0;
}
```

```text output
المساحة: 314.159
```

### التمرين 2

اكتب دالة `int maxOf3(int a, int b, int c)` تُرجع أكبر الأعداد الثلاثة، ثم اقرأ ثلاثة أعداد واطبع أكبرها.

```cpp exercise
#include <iostream>

// int maxOf3(int a, int b, int c)

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>

int maxOf3(int a, int b, int c)
{
    int m = a;
    if (b > m)
        m = b;
    if (c > m)
        m = c;
    return m;
}

int main()
{
    int a = 0, b = 0, c = 0;
    std::cin >> a >> b >> c;
    std::cout << "الأكبر: " << maxOf3(a, b, c) << "\n";
    return 0;
}
```

```text input
12 45 7
```

```text output
الأكبر: 45
```

### التمرين 3

اكتب دالة `void printLine(int n)` تطبع `n` من علامة `-` ثم سطرًا جديدًا، واستخدمها لرسم إطار حول كلمة.

```cpp exercise
#include <iostream>

int main()
{
    // ----------
    // C++ rocks
    // ----------
    return 0;
}
```

```cpp solution
#include <iostream>

void printLine(int n)
{
    for (int i = 0; i < n; i++)
        std::cout << "-";
    std::cout << "\n";
}

int main()
{
    printLine(10);
    std::cout << "C++ rocks\n";
    printLine(10);
    return 0;
}
```

```text output
----------
C++ rocks
----------
```

## اختبر نفسك

```quiz
{"question": "ماذا تعني void قبل اسم الدالة؟", "choices": ["الدالة فارغة", "الدالة لا تُرجع قيمة", "الدالة لا تأخذ معاملات", "الدالة خاصة"], "answer": 1, "explanation": "void تعني أن الدالة لا تُرجع أي قيمة."}
```

```quiz
{"question": "في الاستدعاء add(3, 4)، ماذا نسمي 3 و4؟", "choices": ["معاملات", "وسائط (Arguments)", "متغيرات عامة", "ثوابت عامة"], "answer": 1, "explanation": "القيم الفعلية التي نمررها عند الاستدعاء تسمى وسائط، أما المتغيرات في التعريف فتسمى معاملات."}
```

```quiz
{"question": "دالة تغير قيمة معاملها x (مُمرَّر بالقيمة). ماذا يحدث للمتغير الأصلي في main؟", "choices": ["يتغير", "لا يتغير", "يُحذف", "خطأ ترجمة"], "answer": 1, "explanation": "التمرير بالقيمة يعطي الدالة نسخة، فالأصل لا يتأثر."}
```

```quiz
{"question": "متى تنتهي الدالة؟", "choices": ["عند أول return أو عند القوس } الأخير", "بعد تنفيذ main", "لا تنتهي", "بعد 10 أسطر"], "answer": 0, "explanation": "return تُنهي الدالة فورًا، وإلا تنتهي عند نهاية جسمها."}
```

## الخلاصة

- الدالة: نوع مُرجَع، واسم، ومعاملات، وجسم.
- `return` تُرجع القيمة وتُنهي الدالة، و`void` لدالة لا تُرجع شيئًا.
- عرّف الدالة أو صرّح عنها قبل استدعائها.
- المتغيرات المحلية تعيش داخل دالتها فقط، والتمرير بالقيمة يعطي نسخة.
