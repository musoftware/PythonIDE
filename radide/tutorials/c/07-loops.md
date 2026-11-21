# الدرس 7: حلقات التكرار

تخيل أنك تريد طباعة الأرقام من 1 إلى 1000. هل ستكتب 1000 سطر `printf`؟ بالطبع لا! **حلقة التكرار** (loop) تكرر الكود عددًا من المرات نيابةً عنك.

## حلقة `for`

```c run
#include <stdio.h>

int main(void)
{
    for (int i = 1; i <= 5; i++) {
        printf("الدورة رقم %d\n", i);
    }
    return 0;
}
```

```text output
الدورة رقم 1
الدورة رقم 2
الدورة رقم 3
الدورة رقم 4
الدورة رقم 5
```

حلقة `for` لها ثلاثة أجزاء بين القوسين، مفصولة بـ `;`:

1. **البداية:** `int i = 1` تُنفذ مرة واحدة.
2. **الشرط:** `i <= 5` يُفحص قبل كل دورة؛ إن كان خطأ تنتهي الحلقة.
3. **الخطوة:** `i++` تُنفذ بعد كل دورة.

> **تشبيه:** حلقة `for` مثل **العدّاء في المضمار**: يبدأ عند خط البداية (`i = 1`)، ويسأل قبل كل لفة «هل أكملت 5 لفات؟» (الشرط)، وبعد كل لفة يضيف لفة إلى العدّاد (`i++`).

## مثال: المجموع والمضروب

```c run
#include <stdio.h>

int main(void)
{
    int sum = 0;
    for (int i = 1; i <= 100; i++)
        sum += i;
    printf("مجموع 1..100 = %d\n", sum);

    long long fact = 1;
    for (int i = 1; i <= 10; i++)
        fact *= i;
    printf("10! = %lld\n", fact);
    return 0;
}
```

```text output
مجموع 1..100 = 5050
10! = 3628800
```

## حلقة `while`

تتكرر **ما دام** الشرط صحيحًا. مناسبة عندما لا نعرف عدد الدورات مسبقًا:

```c run
#include <stdio.h>

int main(void)
{
    int n = 12345;
    int digits = 0;
    while (n > 0) {
        n /= 10;      // احذف آخر رقم
        digits++;
    }
    printf("عدد الأرقام: %d\n", digits);
    return 0;
}
```

```text output
عدد الأرقام: 5
```

## حلقة `do ... while`

مثل `while`، لكنها تنفذ الجسم **مرة واحدة على الأقل** ثم تفحص الشرط في النهاية. مثالية لقوائم الاختيار وطلب المدخلات حتى تكون صحيحة:

```c run
#include <stdio.h>

int main(void)
{
    int n;
    do {
        printf("اكتب رقمًا من 1 إلى 10: ");
        scanf("%d", &n);
        printf("\n");
    } while (n < 1 || n > 10);
    printf("شكرًا، اخترت %d\n", n);
    return 0;
}
```

```text input
15
0
7
```

```text output
اكتب رقمًا من 1 إلى 10: 
اكتب رقمًا من 1 إلى 10: 
اكتب رقمًا من 1 إلى 10: 
شكرًا، اخترت 7
```

## `break` و`continue`

- `break` تخرج من الحلقة فورًا.
- `continue` تتخطى بقية الدورة الحالية وتنتقل للدورة التالية.

```c run
#include <stdio.h>

int main(void)
{
    // الأعداد الفردية فقط حتى 9
    for (int i = 1; i <= 10; i++) {
        if (i % 2 == 0)
            continue;
        printf("%d ", i);
    }
    printf("\n");

    // أول عدد يقبل القسمة على 7 بعد 50
    for (int i = 51; ; i++) {
        if (i % 7 == 0) {
            printf("وجدته: %d\n", i);
            break;
        }
    }
    return 0;
}
```

```text output
1 3 5 7 9 
وجدته: 56
```

لاحظ `for (int i = 51; ; i++)` بلا شرط: حلقة لا تنتهي إلا بـ `break`.

## الحلقات المتداخلة

حلقة داخل حلقة، مثل جدول الضرب:

```c run
#include <stdio.h>

int main(void)
{
    for (int row = 1; row <= 4; row++) {
        for (int col = 1; col <= 4; col++)
            printf("%4d", row * col);
        printf("\n");
    }
    return 0;
}
```

```text output
   1   2   3   4
   2   4   6   8
   3   6   9  12
   4   8  12  16
```

`%4d` تطبع العدد في عرض 4 خانات (تضيف مسافات من اليسار)، فتصطف الأعمدة.

## أخطاء شائعة

- **الحلقة اللانهائية بالخطأ:** نسيان تغيير المتغير داخل `while` (مثلًا نسيت `n /= 10`). إن علق برنامجك أوقفه بزر **Stop** (Shift+F5).
- **الخطأ بواحد (off-by-one):** `i < 5` تعطي 0..4، و`i <= 5` تعطي 0..5. فكر جيدًا في حدود الحلقة.
- **فاصلة منقوطة بعد `for`:** `for (i = 0; i < 5; i++);` حلقة فارغة، والسطر التالي يُنفذ مرة واحدة فقط.

## تمارين

### التمرين 1

اطبع جدول ضرب العدد 7 من 1 إلى 5:

```c exercise
#include <stdio.h>

int main(void)
{
    // 7 x 1 = 7
    // ...
    // 7 x 5 = 35
    return 0;
}
```

```c solution
#include <stdio.h>

int main(void)
{
    for (int i = 1; i <= 5; i++)
        printf("7 x %d = %d\n", i, 7 * i);
    return 0;
}
```

```text output
7 x 1 = 7
7 x 2 = 14
7 x 3 = 21
7 x 4 = 28
7 x 5 = 35
```

### التمرين 2

اطبع مثلثًا من النجوم بارتفاع 4 باستخدام حلقتين متداخلتين:

```c exercise
#include <stdio.h>

int main(void)
{
    int height = 4;
    // *
    // **
    // ***
    // ****
    return 0;
}
```

```c solution
#include <stdio.h>

int main(void)
{
    int height = 4;
    for (int i = 1; i <= height; i++) {
        for (int j = 0; j < i; j++)
            printf("*");
        printf("\n");
    }
    return 0;
}
```

```text output
*
**
***
****
```

### التمرين 3

اقرأ أعدادًا من المستخدم حتى يكتب `0`، ثم اطبع مجموعها:

```c exercise
#include <stdio.h>

int main(void)
{
    int n, sum = 0;
    // استخدم do-while أو while مع scanf
    printf("المجموع = %d\n", sum);
    return 0;
}
```

```c solution
#include <stdio.h>

int main(void)
{
    int n, sum = 0;
    do {
        scanf("%d", &n);
        sum += n;
    } while (n != 0);
    printf("المجموع = %d\n", sum);
    return 0;
}
```

```text input
5
10
20
0
```

```text output
المجموع = 35
```

## اختبر نفسك

```quiz
{"question": "كم مرة تُنفذ `for (int i = 0; i < 3; i++)`؟", "choices": ["2", "3", "4", "مرة واحدة"], "answer": 1, "explanation": "i تأخذ القيم 0 و1 و2، أي 3 مرات."}
```

```quiz
{"question": "ما الحلقة التي تنفذ جسمها مرة واحدة على الأقل؟", "choices": ["for", "while", "do ... while", "لا توجد"], "answer": 2, "explanation": "do ... while تفحص الشرط بعد تنفيذ الجسم."}
```

```quiz
{"question": "ماذا تفعل `continue`؟", "choices": ["تنهي البرنامج", "تخرج من الحلقة", "تتخطى بقية الدورة الحالية وتبدأ التالية", "تعيد الحلقة من البداية"], "answer": 2, "explanation": "continue تقفز إلى الدورة التالية مباشرة."}
```

## الخلاصة

- `for` عندما نعرف عدد التكرارات، و`while` عندما نكرر ما دام شرط صحيحًا.
- `do ... while` تنفذ مرة على الأقل.
- `break` للخروج، و`continue` للدورة التالية.
- انتبه للحلقات اللانهائية وأخطاء الحدود.
