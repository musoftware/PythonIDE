# الدرس 14: الملفات والمشاريع متعددة الملفات

عندما ينتهي البرنامج تضيع كل المتغيرات. لكي **نحفظ** البيانات (درجات، إعدادات، سجلات) نكتبها في **ملف** على القرص. وفي النصف الثاني من الدرس نتعلم تقسيم برنامجنا نفسه إلى عدة ملفات `.c` و`.h`.

## الكتابة في ملف

```c run
#include <stdio.h>

int main(void)
{
    FILE *f = fopen("notes.txt", "w");      // افتح للكتابة (ينشئ الملف أو يمسح محتواه)
    if (f == NULL) {
        printf("تعذر فتح الملف\n");
        return 1;
    }
    fprintf(f, "Ali,90\n");
    fprintf(f, "Mona,85\n");
    fprintf(f, "Omar,77\n");
    fclose(f);                               // لا تنسَ الإغلاق!
    printf("تم الحفظ\n");
    return 0;
}
```

```text output
تم الحفظ
```

- `FILE *` مؤشر يمثل الملف المفتوح.
- `fopen(الاسم, الوضع)` تفتح الملف وترجع `NULL` إن فشلت.
- `fprintf` مثل `printf` لكنها تكتب في الملف.
- `fclose` تغلق الملف وتضمن كتابة كل البيانات على القرص.

> **أين يُحفظ الملف؟** في **مجلد التشغيل الحالي**، وهو مجلد المشروع عندما تشغل من الـ IDE. افتح المجلد من **Solution Explorer** (مستكشف الحلول) لتراه.

| الوضع | معناه |
|---|---|
| `"r"` | قراءة (يجب أن يكون الملف موجودًا) |
| `"w"` | كتابة (يمسح المحتوى القديم) |
| `"a"` | إلحاق في آخر الملف |
| `"rb"` / `"wb"` | قراءة / كتابة ثنائية (binary) |

## الكتابة ثم القراءة

```c run
#include <stdio.h>
#include <string.h>

int main(void)
{
    FILE *f = fopen("scores.txt", "w");
    if (!f) return 1;
    fprintf(f, "Ali 90\nMona 85\nOmar 77\n");
    fclose(f);

    f = fopen("scores.txt", "r");
    if (!f) return 1;
    char name[32];
    int score, total = 0, count = 0;
    while (fscanf(f, "%31s %d", name, &score) == 2) {   // اقرأ حتى نهاية الملف
        printf("%s => %d\n", name, score);
        total += score;
        count++;
    }
    fclose(f);
    printf("المتوسط: %.2f\n", (double)total / count);
    return 0;
}
```

```text output
Ali => 90
Mona => 85
Omar => 77
المتوسط: 84.00
```

`fscanf` مثل `scanf` لكنها تقرأ من الملف، وترجع عدد القيم المقروءة؛ عندما تصل لنهاية الملف ترجع رقمًا أقل من 2 فتتوقف الحلقة. و`%31s` تمنع قراءة أكثر من 31 حرفًا في مصفوفة حجمها 32.

## القراءة سطرًا سطرًا بـ `fgets`

```c run
#include <stdio.h>

int main(void)
{
    FILE *f = fopen("log.txt", "w");
    if (!f) return 1;
    fputs("first line\n", f);
    fputs("second line\n", f);
    fclose(f);

    f = fopen("log.txt", "a");                // إلحاق
    fputs("added later\n", f);
    fclose(f);

    char line[100];
    int n = 0;
    f = fopen("log.txt", "r");
    while (fgets(line, sizeof(line), f) != NULL)
        printf("%d: %s", ++n, line);          // line فيه \n بالفعل
    fclose(f);
    return 0;
}
```

```text output
1: first line
2: second line
3: added later
```

> **ملحوظة:** إن كانت بيانات الملف عربية فاحفظها بترميز UTF-8 (وهو الافتراضي لنصوص برامجنا)، وافتح الملف في محرر يدعم UTF-8 مثل محرر الـ IDE نفسه.

## تقسيم البرنامج إلى عدة ملفات

البرامج الحقيقية تتكون من ملفات كثيرة. الطريقة المعتادة في C:

- **ملف ترويسة** `.h`: فيه **إعلانات** الدوال (النماذج الأولية) والأنواع.
- **ملف تنفيذ** `.c`: فيه **تعريفات** الدوال.
- أي ملف يريد استخدام الدوال يكتب `#include "اسم.h"` (بعلامات تنصيص، لأنه ملف من مشروعنا).

```c run
// #file: main.c
#include <stdio.h>
#include "mathutil.h"

int main(void)
{
    printf("max(4, 9) = %d\n", max_int(4, 9));
    printf("7 أولي؟ %d\n", is_prime(7));
    printf("مجموع 1..10 = %d\n", sum_to(10));
    return 0;
}
// #file: mathutil.h
#ifndef MATHUTIL_H
#define MATHUTIL_H

int max_int(int a, int b);
int is_prime(int n);
int sum_to(int n);

#endif
// #file: mathutil.c
#include "mathutil.h"

int max_int(int a, int b)
{
    return a > b ? a : b;
}

int is_prime(int n)
{
    if (n < 2) return 0;
    for (int d = 2; d * d <= n; d++)
        if (n % d == 0) return 0;
    return 1;
}

static int helper_add(int a, int b)   // static: خاصة بهذا الملف فقط
{
    return a + b;
}

int sum_to(int n)
{
    int s = 0;
    for (int i = 1; i <= n; i++)
        s = helper_add(s, i);
    return s;
}
```

```text output
max(4, 9) = 9
7 أولي؟ 1
مجموع 1..10 = 55
```

- الأسطر `#ifndef` و`#define` و`#endif` اسمها **حارس الترويسة** (include guard)، وتمنع تضمين الملف مرتين.
- الدالة `static` لا يراها إلا ملفها، مثل «الخصوصي» في اللغات الأخرى.

**في الـ IDE:** أضف الملفات من **Project ← Add Module...** (إضافة وحدة برمجية) أو بالضغط بالزر الأيمن على المشروع في **Solution Explorer**. كل ملفات `.c` في المشروع تُترجم معًا تلقائيًا عند التشغيل.

## أخطاء شائعة

- **عدم فحص `NULL` بعد `fopen`:** إن لم يوجد الملف ثم استخدمته ينهار البرنامج.
- **نسيان `fclose`:** قد لا تُكتب آخر البيانات على القرص.
- **فتح بوضع `"w"` بالخطأ:** يمسح الملف القديم كله! استخدم `"a"` للإلحاق.
- **تعريف دالة في ملف `.h`:** إن ضُمّن في ملفين ستظهر رسالة `multiple definition`. ضع الإعلان فقط في `.h` والتعريف في `.c`.

## تمارين

### التمرين 1

اكتب الأعداد من 1 إلى 5 في ملف `nums.txt` (كل عدد في سطر)، ثم اقرأها واطبع مجموعها:

```c exercise
#include <stdio.h>

int main(void)
{
    // 1) اكتب الأعداد
    // 2) اقرأها بـ fscanf واجمعها
    // اطبع: المجموع = 15
    return 0;
}
```

```c solution
#include <stdio.h>

int main(void)
{
    FILE *f = fopen("nums.txt", "w");
    if (!f) return 1;
    for (int i = 1; i <= 5; i++)
        fprintf(f, "%d\n", i);
    fclose(f);

    int x, sum = 0;
    f = fopen("nums.txt", "r");
    if (!f) return 1;
    while (fscanf(f, "%d", &x) == 1)
        sum += x;
    fclose(f);
    printf("المجموع = %d\n", sum);
    return 0;
}
```

```text output
المجموع = 15
```

### التمرين 2

انقل الدالة `square` إلى ملف منفصل `calc.c` مع ترويسة `calc.h`:

```c exercise
// #file: main.c
#include <stdio.h>
#include "calc.h"

int main(void)
{
    printf("%d\n", square(12));
    return 0;
}
// #file: calc.h
// اكتب حارس الترويسة والنموذج الأولي لـ square
// #file: calc.c
#include "calc.h"
// اكتب تعريف square
```

```c solution
// #file: main.c
#include <stdio.h>
#include "calc.h"

int main(void)
{
    printf("%d\n", square(12));
    return 0;
}
// #file: calc.h
#ifndef CALC_H
#define CALC_H
int square(int x);
#endif
// #file: calc.c
#include "calc.h"

int square(int x)
{
    return x * x;
}
```

```text output
144
```

## اختبر نفسك

```quiz
{"question": "ماذا يحدث عند فتح ملف موجود بالوضع \"w\"؟", "choices": ["يُضاف في آخره", "يُمسح محتواه ويُكتب من جديد", "خطأ دائمًا", "يُفتح للقراءة"], "answer": 1, "explanation": "الوضع w ينشئ الملف أو يفرغه؛ للإلحاق استخدم a."}
```

```quiz
{"question": "ما الذي يوضع عادةً في ملف .h؟", "choices": ["تعريفات الدوال الكاملة", "إعلانات الدوال والأنواع", "الدالة main", "البيانات"], "answer": 1, "explanation": "الترويسة للإعلانات، والتعريفات في ملفات .c."}
```

```quiz
{"question": "ما فائدة `#ifndef ... #define ... #endif` في الترويسة؟", "choices": ["تسريع الترجمة فقط", "منع تضمين الترويسة أكثر من مرة", "تعريف الثوابت", "التعليقات"], "answer": 1, "explanation": "حارس الترويسة يمنع تكرار الإعلانات إن ضُمّن الملف مرتين."}
```

## الخلاصة

- `fopen` و`fclose` لفتح وإغلاق الملفات، وافحص `NULL`.
- `fprintf`/`fputs` للكتابة، و`fscanf`/`fgets` للقراءة.
- قسّم البرنامج: إعلانات في `.h` وتعريفات في `.c`، و`static` للدوال الخاصة.
- كل ملفات `.c` في مشروع الـ IDE تُترجم معًا.
