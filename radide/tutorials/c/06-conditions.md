# الدرس 6: الشروط و`switch`

البرامج الذكية **تتخذ قرارات**: إذا كانت الدرجة 50 فأكثر فالطالب ناجح، وإلا فهو راسب. هذا ما تفعله جمل الشرط.

## `if` و`else`

```c run
#include <stdio.h>

int main(void)
{
    int score = 72;
    if (score >= 50) {
        printf("ناجح\n");
    } else {
        printf("راسب\n");
    }
    printf("انتهى\n");
    return 0;
}
```

```text output
ناجح
انتهى
```

> **تشبيه:** `if` مثل **مفترق طرق** عليه لافتة: «إن كان الشرط صحيحًا فاذهب يمينًا، وإلا فاذهب يسارًا». وفي النهاية يلتقي الطريقان من جديد عند `printf("انتهى")`.

- الشرط يُكتب بين قوسين `( )`.
- الكود الذي يُنفذ بين `{ }`. إن كان سطرًا واحدًا يمكن حذف الأقواس، لكن وضعها عادة جيدة.
- في C أي قيمة **غير الصفر** تعتبر صحيحة، والصفر خطأ.

## سلسلة `else if`

```c run
#include <stdio.h>

int main(void)
{
    int score = 83;
    if (score >= 90)
        printf("ممتاز\n");
    else if (score >= 80)
        printf("جيد جدًا\n");
    else if (score >= 65)
        printf("جيد\n");
    else if (score >= 50)
        printf("مقبول\n");
    else
        printf("راسب\n");
    return 0;
}
```

```text output
جيد جدًا
```

تُفحص الشروط بالترتيب من أعلى، وأول شرط صحيح يُنفذ ويتجاهل الباقي.

## شروط مركبة

```c run
#include <stdio.h>

int main(void)
{
    int age = 25;
    int has_license = 1;

    if (age >= 18 && has_license)
        printf("يمكنك القيادة\n");

    char ch = 'e';
    if (ch == 'a' || ch == 'e' || ch == 'i' || ch == 'o' || ch == 'u')
        printf("%c حرف علة\n", ch);

    int year = 2024;
    if ((year % 4 == 0 && year % 100 != 0) || year % 400 == 0)
        printf("%d سنة كبيسة\n", year);
    return 0;
}
```

```text output
يمكنك القيادة
e حرف علة
2024 سنة كبيسة
```

## `switch`: الاختيار من قائمة

عندما نقارن متغيرًا واحدًا بقيم ثابتة كثيرة، تكون `switch` أوضح من سلسلة `else if`:

```c run
#include <stdio.h>

int main(void)
{
    int day = 6;
    switch (day) {
    case 1:
        printf("السبت\n");
        break;
    case 2:
        printf("الأحد\n");
        break;
    case 6:
    case 7:
        printf("نهاية الأسبوع قريبة\n");
        break;
    default:
        printf("يوم عمل\n");
    }
    return 0;
}
```

```text output
نهاية الأسبوع قريبة
```

- `case` قيمة ثابتة (عدد أو حرف)، ولا تصلح مع النصوص.
- `break` تخرج من `switch`. **إن نسيتها** يكمل التنفيذ في الحالة التالية! (وهذا ما استخدمناه عمدًا مع `case 6` و`case 7`).
- `default` تعمل إن لم تطابق أي حالة.

## العامل الثلاثي `? :`

اختصار لـ `if/else` الصغيرة التي تختار قيمة:

```c run
#include <stdio.h>

int main(void)
{
    int n = 7;
    printf("%d %s\n", n, n % 2 == 0 ? "زوجي" : "فردي");
    int a = 12, b = 30;
    int max = a > b ? a : b;
    printf("الأكبر: %d\n", max);
    return 0;
}
```

```text output
7 فردي
الأكبر: 30
```

## آلة حاسبة صغيرة

```c run
#include <stdio.h>

int main(void)
{
    double a, b;
    char op;
    printf("اكتب العملية (مثل 6 * 7): ");
    scanf("%lf %c %lf", &a, &op, &b);
    printf("\n");
    switch (op) {
    case '+': printf("%.2f\n", a + b); break;
    case '-': printf("%.2f\n", a - b); break;
    case '*': printf("%.2f\n", a * b); break;
    case '/':
        if (b == 0)
            printf("لا يمكن القسمة على صفر\n");
        else
            printf("%.2f\n", a / b);
        break;
    default:
        printf("عملية غير معروفة\n");
    }
    return 0;
}
```

```text input
6 * 7
```

```text output
اكتب العملية (مثل 6 * 7): 
42.00
```

## أخطاء شائعة

- **`=` بدل `==`:** `if (x = 0)` لا يقارن، بل يجعل `x` صفرًا والشرط دائمًا خطأ.
- **فاصلة منقوطة بعد الشرط:** `if (x > 5);` تنهي جملة `if` فورًا، ويُنفذ ما بعدها دائمًا!
- **نسيان `break` في `switch`.**
- **نسيان الأقواس مع أكثر من سطر:** بدون `{ }` يتبع `if` السطر الأول فقط.

## تمارين

### التمرين 1

اكتب برنامجًا يطبع إن كان العدد `n` موجبًا أو سالبًا أو صفرًا:

```c exercise
#include <stdio.h>

int main(void)
{
    int n = -4;
    // اطبع: سالب
    return 0;
}
```

```c solution
#include <stdio.h>

int main(void)
{
    int n = -4;
    if (n > 0)
        printf("موجب\n");
    else if (n < 0)
        printf("سالب\n");
    else
        printf("صفر\n");
    return 0;
}
```

```text output
سالب
```

### التمرين 2

حوّل رقم الشهر إلى عدد أيامه باستخدام `switch` (افترض أن فبراير 28 يومًا):

```c exercise
#include <stdio.h>

int main(void)
{
    int month = 4;
    // اطبع: الشهر 4 فيه 30 يومًا
    return 0;
}
```

```c solution
#include <stdio.h>

int main(void)
{
    int month = 4;
    int days;
    switch (month) {
    case 2:
        days = 28;
        break;
    case 4: case 6: case 9: case 11:
        days = 30;
        break;
    default:
        days = 31;
    }
    printf("الشهر %d فيه %d يومًا\n", month, days);
    return 0;
}
```

```text output
الشهر 4 فيه 30 يومًا
```

## اختبر نفسك

```quiz
{"question": "ماذا يحدث إذا نسيت `break` في إحدى حالات switch؟", "choices": ["خطأ ترجمة", "يكمل التنفيذ في الحالة التالية", "يتوقف البرنامج", "لا شيء"], "answer": 1, "explanation": "بدون break يستمر التنفيذ إلى الحالة التالية (fall-through)."}
```

```quiz
{"question": "ما قيمة `x` بعد `int x = 5 > 3 ? 10 : 20;`؟", "choices": ["5", "10", "20", "3"], "answer": 1, "explanation": "الشرط صحيح فتُختار القيمة الأولى 10."}
```

```quiz
{"question": "في C، متى يعتبر الشرط صحيحًا؟", "choices": ["إذا كان 1 فقط", "إذا كان أي قيمة غير الصفر", "إذا كان موجبًا فقط", "إذا كان نصًا"], "answer": 1, "explanation": "أي قيمة غير الصفر تعتبر صحيحة، والصفر وحده خطأ."}
```

## الخلاصة

- `if / else if / else` لاتخاذ القرارات.
- `&&` و`||` لربط الشروط.
- `switch` للاختيار بين قيم ثابتة، ولا تنسَ `break`.
- `شرط ? أ : ب` لاختيار قيمة بسرعة.
