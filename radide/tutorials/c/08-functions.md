# الدرس 8: الدوال

كلما كبر البرنامج صار من الصعب قراءته. **الدالة** (function) تجمع مجموعة تعليمات تحت اسم واحد، فنستدعيها كلما احتجناها بدل تكرار الكود.

> **تشبيه:** الدالة مثل **ماكينة العصير**: تضع فيها فاكهة (المدخلات أو **المعاملات**)، فتعطيك عصيرًا (**القيمة المرجعة**). لا يهمك ما يحدث بداخلها؛ يكفي أن تعرف ماذا تضع وماذا تأخذ.

## أول دالة

```c run
#include <stdio.h>

int square(int x)
{
    return x * x;
}

int main(void)
{
    printf("%d\n", square(4));
    printf("%d\n", square(9));
    int s = square(3) + square(4);
    printf("%d\n", s);
    return 0;
}
```

```text output
16
81
25
```

أجزاء الدالة:

- `int` قبل الاسم: **نوع القيمة المرجعة**.
- `square`: اسم الدالة.
- `(int x)`: **المعاملات** (parameters)، أي المدخلات وأنواعها.
- `return x * x;` ترجع النتيجة لمن استدعى الدالة.

## دوال لا ترجع شيئًا: `void`

```c run
#include <stdio.h>

void print_line(int length)
{
    for (int i = 0; i < length; i++)
        printf("-");
    printf("\n");
}

void greet(const char *name)
{
    printf("أهلًا يا %s\n", name);
}

int main(void)
{
    print_line(10);
    greet("ليلى");
    greet("يوسف");
    print_line(10);
    return 0;
}
```

```text output
----------
أهلًا يا ليلى
أهلًا يا يوسف
----------
```

`const char *name` هو طريقة C لاستقبال نص في دالة. سنفهم النجمة `*` في درس المؤشرات.

## النموذج الأولي (Prototype)

المترجم يقرأ الملف من أعلى لأسفل. إن استدعيت دالة قبل تعريفها يجب أن **تعلن** عنها أولًا بسطر ينتهي بـ `;`:

```c run
#include <stdio.h>

double average(double a, double b);   // النموذج الأولي

int main(void)
{
    printf("%.1f\n", average(8, 5));
    return 0;
}

double average(double a, double b)    // التعريف الكامل بعد main
{
    return (a + b) / 2;
}
```

```text output
6.5
```

هذا يسمح لنا بوضع `main` في أعلى الملف لتكون أول ما يقرؤه الإنسان.

## التمرير بالقيمة

عندما تمرر متغيرًا لدالة، تأخذ الدالة **نسخة** منه. تغيير النسخة لا يغير الأصل:

```c run
#include <stdio.h>

void try_to_change(int n)
{
    n = 100;
    printf("داخل الدالة: %d\n", n);
}

int main(void)
{
    int x = 5;
    try_to_change(x);
    printf("في main: %d\n", x);
    return 0;
}
```

```text output
داخل الدالة: 100
في main: 5
```

> **تشبيه:** كأنك أعطيت صديقك **صورة** من ورقة، فكتب عليها. الورقة الأصلية عندك لم تتغير. لكي تسمح له بتعديل الأصل، يجب أن تعطيه **عنوان** الورقة، وهذا ما ستفعله المؤشرات في الدرس 11.

## المتغيرات المحلية والعامة

- **المحلي:** يُعرّف داخل دالة، ولا يراه أحد غيرها، ويختفي عند انتهائها.
- **العام (global):** يُعرّف خارج كل الدوال، وتراه كل الدوال. استخدمه بحذر.
- `static` داخل دالة: متغير محلي **يحتفظ بقيمته** بين الاستدعاءات.

```c run
#include <stdio.h>

int calls = 0;            // متغير عام

void counter(void)
{
    static int count = 0; // يُهيأ مرة واحدة فقط
    count++;
    calls++;
    printf("count = %d\n", count);
}

int main(void)
{
    counter();
    counter();
    counter();
    printf("calls = %d\n", calls);
    return 0;
}
```

```text output
count = 1
count = 2
count = 3
calls = 3
```

## الاستدعاء الذاتي (Recursion)

الدالة يمكن أن تستدعي نفسها، بشرط وجود **حالة توقف**:

```c run
#include <stdio.h>

long long factorial(int n)
{
    if (n <= 1)               // حالة التوقف
        return 1;
    return n * factorial(n - 1);
}

int fib(int n)
{
    return n < 2 ? n : fib(n - 1) + fib(n - 2);
}

int main(void)
{
    printf("5! = %lld\n", factorial(5));
    printf("15! = %lld\n", factorial(15));
    for (int i = 0; i < 10; i++)
        printf("%d ", fib(i));
    printf("\n");
    return 0;
}
```

```text output
5! = 120
15! = 1307674368000
0 1 1 2 3 5 8 13 21 34 
```

## دوال جاهزة من المكتبة: `math.h`

```c run
#include <stdio.h>
#include <math.h>

int main(void)
{
    printf("%.2f\n", sqrt(2.0));
    printf("%.0f\n", pow(2, 10));
    printf("%.2f\n", fabs(-3.75));
    printf("%.0f %.0f\n", floor(4.7), ceil(4.2));
    return 0;
}
```

```text output
1.41
1024
3.75
4 5
```

> **ملحوظة:** دوال `math.h` تحتاج أحيانًا الخيار `-lm` عند الترجمة بـ gcc. الـ IDE تضيفه تلقائيًا.

## أخطاء شائعة

- **نسيان `return`** في دالة غير `void`: تُرجع قيمة عشوائية، وgcc يحذرك بـ `control reaches end of non-void function`.
- **استدعاء دالة قبل تعريفها دون نموذج أولي.**
- **استدعاء ذاتي بلا حالة توقف:** يستهلك الذاكرة حتى ينهار البرنامج (stack overflow).

## تمارين

### التمرين 1

اكتب دالة `is_even` ترجع `1` إن كان العدد زوجيًا و`0` إن كان فرديًا:

```c exercise
#include <stdio.h>

// اكتب الدالة is_even هنا

int main(void)
{
    // printf("%d %d\n", is_even(4), is_even(7));  // أزل التعليق بعد كتابة الدالة
    return 0;
}
```

```c solution
#include <stdio.h>

int is_even(int n)
{
    return n % 2 == 0;
}

int main(void)
{
    printf("%d %d\n", is_even(4), is_even(7));
    return 0;
}
```

```text output
1 0
```

### التمرين 2

اكتب دالة `max3` ترجع أكبر ثلاثة أعداد صحيحة:

```c exercise
#include <stdio.h>

int max3(int a, int b, int c)
{
    // أكمل
    return 0;
}

int main(void)
{
    printf("%d\n", max3(4, 19, 7));
    printf("%d\n", max3(-1, -5, -3));
    return 0;
}
```

```c solution
#include <stdio.h>

int max3(int a, int b, int c)
{
    int m = a;
    if (b > m) m = b;
    if (c > m) m = c;
    return m;
}

int main(void)
{
    printf("%d\n", max3(4, 19, 7));
    printf("%d\n", max3(-1, -5, -3));
    return 0;
}
```

```text output
19
-1
```

### التمرين 3

اكتب دالة استدعاء ذاتي `power(base, exp)` تحسب القوة (أعداد صحيحة موجبة):

```c exercise
#include <stdio.h>

long long power(int base, int exp)
{
    // إذا كان exp يساوي 0 فالناتج 1
    return 0;
}

int main(void)
{
    printf("%lld\n", power(2, 10));
    printf("%lld\n", power(3, 4));
    return 0;
}
```

```c solution
#include <stdio.h>

long long power(int base, int exp)
{
    if (exp == 0)
        return 1;
    return base * power(base, exp - 1);
}

int main(void)
{
    printf("%lld\n", power(2, 10));
    printf("%lld\n", power(3, 4));
    return 0;
}
```

```text output
1024
81
```

## اختبر نفسك

```quiz
{"question": "ماذا يعني `void` كنوع للقيمة المرجعة؟", "choices": ["الدالة ترجع صفرًا", "الدالة لا ترجع قيمة", "الدالة لا تأخذ معاملات", "خطأ"], "answer": 1, "explanation": "void معناها لا شيء: الدالة تنفذ عملًا ولا ترجع قيمة."}
```

```quiz
{"question": "إذا غيرت الدالة قيمة معاملها العادي `int n`، هل يتغير المتغير الأصلي؟", "choices": ["نعم دائمًا", "لا، لأنها تعمل على نسخة", "فقط إن كان عامًا", "فقط مع return"], "answer": 1, "explanation": "C تمرر بالقيمة: الدالة تأخذ نسخة."}
```

```quiz
{"question": "ما الذي يميز متغير `static` داخل دالة؟", "choices": ["تراه كل الدوال", "يحتفظ بقيمته بين الاستدعاءات", "لا يمكن تغييره", "يُحذف بعد كل استدعاء"], "answer": 1, "explanation": "static المحلي يُهيأ مرة واحدة ويبقى بقيمته طوال عمر البرنامج."}
```

## الخلاصة

- الدالة: نوع مرجع، اسم، معاملات، جسم، و`return`.
- `void` للدوال التي لا ترجع قيمة.
- النموذج الأولي يسمح باستدعاء الدالة قبل تعريفها.
- C تمرر المعاملات بالقيمة (نسخة).
- الاستدعاء الذاتي يحتاج حالة توقف.
