# الدرس 11: المؤشرات بهدوء وخطوة بخطوة

المؤشرات (pointers) هي أشهر موضوع في C، ويخافه المبتدئون كثيرًا. لكن الفكرة بسيطة جدًا إذا فهمنا الذاكرة أولًا. خذ نفسًا عميقًا، ولنبدأ.

## الذاكرة والعناوين

ذاكرة الحاسوب مثل **شارع طويل من البيوت**، لكل بيت **رقم** (عنوان). عندما تكتب `int age = 25;` يحجز البرنامج بيتًا، ويضع فيه 25، ويتذكر أن اسمه `age`.

- **قيمة** المتغير: ما بداخل البيت (25).
- **عنوان** المتغير: رقم البيت، ونحصل عليه بالعامل `&`.

```c run
#include <stdio.h>

int main(void)
{
    int age = 25;
    printf("القيمة: %d\n", age);
    printf("هل للمتغير عنوان؟ %s\n", &age != NULL ? "نعم" : "لا");
    return 0;
}
```

```text output
القيمة: 25
هل للمتغير عنوان؟ نعم
```

(العنوان نفسه رقم كبير يتغير في كل تشغيل، يمكنك طباعته بـ `printf("%p", (void *)&age)` لتراه.)

## ما هو المؤشر؟

**المؤشر متغير يخزن عنوانًا.** أي أنه ورقة مكتوب عليها رقم بيت آخر.

```c run
#include <stdio.h>

int main(void)
{
    int age = 25;
    int *p = &age;      // p مؤشر إلى int، ويحمل عنوان age

    printf("age = %d\n", age);
    printf("*p = %d\n", *p);   // * : اذهب إلى العنوان واقرأ ما فيه

    *p = 30;            // غيّر ما في العنوان
    printf("age الآن = %d\n", age);
    return 0;
}
```

```text output
age = 25
*p = 25
age الآن = 30
```

| الكتابة | معناها |
|---|---|
| `int *p;` | `p` مؤشر يستطيع حمل عنوان `int` |
| `p = &age;` | ضع في `p` عنوان `age` |
| `*p` | القيمة الموجودة في العنوان الذي يحمله `p` |

> **تشبيه:** `p` ورقة مكتوب عليها «البيت رقم 1000». و`*p` معناها «اذهب إلى البيت رقم 1000 وانظر ماذا بداخله». عندما كتبنا `*p = 30` دخلنا البيت وغيرنا محتواه، فتغير `age` نفسه لأنه هو ذلك البيت.

## لماذا نحتاج المؤشرات؟ (1) تعديل متغيرات من داخل دالة

تذكر من درس الدوال أن الدالة تأخذ **نسخة**. لكن إذا أعطيناها **العنوان** تستطيع تعديل الأصل:

```c run
#include <stdio.h>

void swap(int *a, int *b)
{
    int tmp = *a;
    *a = *b;
    *b = tmp;
}

int main(void)
{
    int x = 3, y = 8;
    swap(&x, &y);
    printf("x = %d, y = %d\n", x, y);
    return 0;
}
```

```text output
x = 8, y = 3
```

وهذا بالضبط سبب كتابة `&` في `scanf("%d", &n)`: نعطيها عنوان `n` لتكتب فيه.

## (2) إرجاع أكثر من قيمة

```c run
#include <stdio.h>

void min_max(const int a[], int n, int *min, int *max)
{
    *min = *max = a[0];
    for (int i = 1; i < n; i++) {
        if (a[i] < *min) *min = a[i];
        if (a[i] > *max) *max = a[i];
    }
}

int main(void)
{
    int data[] = {7, 2, 9, 4, 11, 1};
    int lo, hi;
    min_max(data, 6, &lo, &hi);
    printf("الأصغر %d والأكبر %d\n", lo, hi);
    return 0;
}
```

```text output
الأصغر 1 والأكبر 11
```

## المؤشرات والمصفوفات

اسم المصفوفة هو **عنوان أول عنصر** فيها. ويمكن التحرك في المصفوفة بالجمع على المؤشر:

```c run
#include <stdio.h>

int main(void)
{
    int a[] = {10, 20, 30, 40};
    int *p = a;             // مثل p = &a[0]

    printf("%d\n", *p);         // 10
    printf("%d\n", *(p + 2));   // 30 : تقدّم عنصرين
    p++;                        // انتقل للعنصر التالي
    printf("%d\n", *p);         // 20

    for (int *q = a; q < a + 4; q++)
        printf("%d ", *q);
    printf("\n");
    return 0;
}
```

```text output
10
30
20
10 20 30 40 
```

`p + 2` لا تعني «العنوان + 2 بايت»، بل «بعد عنصرين»، وC تحسب الحجم المناسب للنوع تلقائيًا. و`a[i]` في الحقيقة اختصار لـ `*(a + i)`.

## النصوص والمؤشرات

```c run
#include <stdio.h>

int length(const char *s)
{
    const char *start = s;
    while (*s != '\0')
        s++;
    return s - start;       // الفرق بين مؤشرين = عدد العناصر بينهما
}

int main(void)
{
    const char *msg = "pointer";
    printf("%d\n", length(msg));
    printf("%s\n", msg + 3);    // النص بدءًا من الحرف الرابع
    return 0;
}
```

```text output
7
nter
```

## المؤشر الفارغ `NULL`

المؤشر الذي لا يشير إلى شيء نعطيه القيمة `NULL`. ويجب **دائمًا** التحقق منه قبل استخدام `*`:

```c run
#include <stdio.h>

void show(const int *p)
{
    if (p == NULL) {
        printf("لا توجد قيمة\n");
        return;
    }
    printf("القيمة %d\n", *p);
}

int main(void)
{
    int n = 5;
    show(&n);
    show(NULL);
    return 0;
}
```

```text output
القيمة 5
لا توجد قيمة
```

## أخطاء شائعة

- **مؤشر غير مهيأ:** `int *p; *p = 5;` يكتب في عنوان عشوائي فينهار البرنامج. هيئ المؤشر دائمًا بعنوان أو بـ `NULL`.
- **استخدام `*` على `NULL`:** انهيار فوري (Segmentation fault / Access violation).
- **الخلط بين `p` و`*p`:** `p` العنوان، و`*p` القيمة.
- **إرجاع عنوان متغير محلي من دالة:** المتغير يختفي بعد انتهاء الدالة فيصبح العنوان معلقًا.

> **نصيحة:** إذا انهار برنامجك بسبب مؤشر، شغّله بـ **F5** (Start Debugging) وسيتوقف المصحح على السطر المسبب للمشكلة، وترى قيم المتغيرات في نافذة **Locals** (المتغيرات المحلية).

## تمارين

### التمرين 1

اكتب دالة `add_ten` تزيد المتغير الأصلي بمقدار 10 عبر مؤشر:

```c exercise
#include <stdio.h>

void add_ten(int *n)
{
    // أكمل
}

int main(void)
{
    int score = 75;
    add_ten(&score);
    printf("%d\n", score);
    return 0;
}
```

```c solution
#include <stdio.h>

void add_ten(int *n)
{
    *n += 10;
}

int main(void)
{
    int score = 75;
    add_ten(&score);
    printf("%d\n", score);
    return 0;
}
```

```text output
85
```

### التمرين 2

اكتب دالة `divide` ترجع ناتج القسمة الصحيحة والباقي عبر مؤشرين:

```c exercise
#include <stdio.h>

void divide(int a, int b, int *q, int *r)
{
    // أكمل
}

int main(void)
{
    int q, r;
    divide(17, 5, &q, &r);
    printf("17 / 5 = %d والباقي %d\n", q, r);
    return 0;
}
```

```c solution
#include <stdio.h>

void divide(int a, int b, int *q, int *r)
{
    *q = a / b;
    *r = a % b;
}

int main(void)
{
    int q, r;
    divide(17, 5, &q, &r);
    printf("17 / 5 = %d والباقي %d\n", q, r);
    return 0;
}
```

```text output
17 / 5 = 3 والباقي 2
```

### التمرين 3

اجمع عناصر مصفوفة باستخدام مؤشر يتحرك عليها (بدون `a[i]`):

```c exercise
#include <stdio.h>

int sum(const int *p, int n)
{
    int total = 0;
    // استخدم *p و p++
    return total;
}

int main(void)
{
    int a[] = {3, 6, 9, 12};
    printf("%d\n", sum(a, 4));
    return 0;
}
```

```c solution
#include <stdio.h>

int sum(const int *p, int n)
{
    int total = 0;
    for (int i = 0; i < n; i++) {
        total += *p;
        p++;
    }
    return total;
}

int main(void)
{
    int a[] = {3, 6, 9, 12};
    printf("%d\n", sum(a, 4));
    return 0;
}
```

```text output
30
```

## اختبر نفسك

```quiz
{"question": "إذا كان `int *p = &x;` فماذا تعني `*p`؟", "choices": ["عنوان x", "قيمة x", "عنوان p", "حجم x"], "answer": 1, "explanation": "*p تذهب إلى العنوان المخزن في p وتعطي القيمة، أي قيمة x."}
```

```quiz
{"question": "لماذا تأخذ swap معاملات من نوع `int *`؟", "choices": ["لأنها أسرع فقط", "لتستطيع تعديل المتغيرات الأصلية عبر عناوينها", "لأن C لا تقبل int", "للطباعة"], "answer": 1, "explanation": "بتمرير العناوين تعدل الدالة الأصل لا النسخ."}
```

```quiz
{"question": "ماذا تساوي `a[2]` بلغة المؤشرات؟", "choices": ["*a + 2", "*(a + 2)", "&a + 2", "a * 2"], "answer": 1, "explanation": "a[i] هي اختصار *(a + i)."}
```

## الخلاصة

- `&x` عنوان `x`، والمؤشر متغير يخزن عنوانًا.
- `*p` القيمة الموجودة في العنوان.
- المؤشرات تسمح للدوال بتعديل الأصل وإرجاع أكثر من قيمة.
- اسم المصفوفة عنوان أول عنصر، و`a[i]` تساوي `*(a + i)`.
- هيئ المؤشرات دائمًا، وافحص `NULL` قبل الاستخدام.
