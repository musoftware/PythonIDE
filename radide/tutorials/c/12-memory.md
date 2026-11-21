# الدرس 12: الذاكرة الديناميكية: `malloc` و`free`

حتى الآن كان حجم المصفوفة ثابتًا نكتبه في الكود: `int a[10]`. لكن ماذا لو كان المستخدم هو من يحدد كم رقمًا سيُدخل؟ هنا نحتاج أن نطلب ذاكرة **أثناء التشغيل**، وهذا اسمه **الحجز الديناميكي**.

## المكدس والكومة

- **المكدس (stack):** هنا تعيش المتغيرات المحلية. سريع وتلقائي، يُحجز عند دخول الدالة ويُحرر عند خروجها. لكنه صغير وحجمه يُعرف وقت الترجمة.
- **الكومة (heap):** مساحة كبيرة نطلب منها ذاكرة بأي حجم وقت التشغيل، ونحن المسؤولون عن **إرجاعها**.

> **تشبيه:** المكدس مثل **الطاولة في المقهى**: تجلس عليها وتتركها عند الخروج تلقائيًا. الكومة مثل **استئجار مخزن**: تستأجر المساحة التي تريدها (`malloc`)، وعليك أن **تسلّم المفتاح** عند الانتهاء (`free`)، وإلا يظل المخزن محجوزًا باسمك.

## `malloc` و`free`

```c run
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int n = 5;
    int *arr = malloc(n * sizeof(int));   // احجز مكانًا لـ 5 أعداد
    if (arr == NULL) {                      // قد يفشل الحجز
        printf("لا توجد ذاكرة كافية\n");
        return 1;
    }
    for (int i = 0; i < n; i++)
        arr[i] = (i + 1) * 10;              // نستخدمه كمصفوفة عادية
    for (int i = 0; i < n; i++)
        printf("%d ", arr[i]);
    printf("\n");

    free(arr);                              // أرجع الذاكرة
    arr = NULL;                             // عادة جيدة
    return 0;
}
```

```text output
10 20 30 40 50 
```

- `malloc(عدد البايتات)` تحجز ذاكرة وترجع مؤشرًا لأولها، أو `NULL` إن فشلت.
- `n * sizeof(int)` عدد البايتات المطلوبة لـ `n` أعداد.
- `free(p)` تحرر الذاكرة. بعدها لا تستخدم `p` أبدًا.

## مصفوفة بحجم يحدده المستخدم

```c run
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int n;
    printf("كم درجة؟ ");
    scanf("%d", &n);
    printf("\n");

    double *marks = malloc(n * sizeof(double));
    if (!marks)
        return 1;

    double sum = 0;
    for (int i = 0; i < n; i++) {
        scanf("%lf", &marks[i]);
        sum += marks[i];
    }
    printf("المتوسط = %.2f\n", sum / n);
    free(marks);
    return 0;
}
```

```text input
4
80 90 70 100
```

```text output
كم درجة؟ 
المتوسط = 85.00
```

## `calloc` و`realloc`

- `calloc(n, size)` مثل `malloc` لكنها **تملأ الذاكرة بالأصفار**.
- `realloc(p, new_size)` تكبّر أو تصغّر حجزًا موجودًا، مع الاحتفاظ بالبيانات القديمة.

```c run
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int capacity = 2, count = 0;
    int *list = calloc(capacity, sizeof(int));
    if (!list)
        return 1;

    for (int value = 1; value <= 7; value++) {
        if (count == capacity) {              // امتلأت؟ ضاعف الحجم
            capacity *= 2;
            int *bigger = realloc(list, capacity * sizeof(int));
            if (!bigger) {
                free(list);
                return 1;
            }
            list = bigger;
            printf("السعة أصبحت %d\n", capacity);
        }
        list[count++] = value * value;
    }
    for (int i = 0; i < count; i++)
        printf("%d ", list[i]);
    printf("\n");
    free(list);
    return 0;
}
```

```text output
السعة أصبحت 4
السعة أصبحت 8
1 4 9 16 25 36 49 
```

هذه الفكرة (مضاعفة السعة عند الامتلاء) هي بالضبط ما يفعله `std::vector` في C++ من الداخل!

> **لاحظ:** نضع نتيجة `realloc` في مؤشر مؤقت `bigger` أولًا. لو كتبنا `list = realloc(list, ...)` وفشلت، لضاع عنوان الذاكرة القديمة ولم نعد نستطيع تحريرها.

## دالة تنشئ نصًا جديدًا

الذاكرة المحجوزة بـ `malloc` **تبقى** بعد انتهاء الدالة، لذلك نستطيع إرجاعها، بشرط أن يحررها من يستقبلها:

```c run
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char *repeat(const char *s, int times)
{
    size_t len = strlen(s);
    char *out = malloc(len * times + 1);    // +1 لـ '\0'
    if (!out)
        return NULL;
    out[0] = '\0';
    for (int i = 0; i < times; i++)
        strcat(out, s);
    return out;
}

int main(void)
{
    char *r = repeat("ab", 3);
    printf("%s\n", r);
    free(r);                                 // المستقبل يحرر
    return 0;
}
```

```text output
ababab
```

## أخطاء شائعة (وخطيرة)

| الخطأ | ماذا يحدث |
|---|---|
| **تسرب الذاكرة** (memory leak): نسيان `free` | البرنامج يستهلك ذاكرة أكثر فأكثر |
| **استخدام بعد التحرير** (use after free) | قراءة ذاكرة لم تعد لك: نتائج عشوائية أو انهيار |
| **التحرير مرتين** (double free) | انهيار البرنامج غالبًا |
| **نسيان فحص `NULL`** | انهيار إن فشل الحجز |
| **حجز أقل من اللازم** (مثلًا نسيان `+1` للنص) | كتابة خارج الحدود |

> **قاعدة ذهبية:** لكل `malloc` يوجد `free` واحد فقط. وبعد `free` اجعل المؤشر `NULL`.

## تمارين

### التمرين 1

احجز مصفوفة من `n` أعداد صحيحة، واملأها بمربعات الأعداد من 1 إلى `n`، واطبعها ثم حررها:

```c exercise
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int n = 6;
    // احجز، املأ، اطبع: 1 4 9 16 25 36
    return 0;
}
```

```c solution
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int n = 6;
    int *a = malloc(n * sizeof(int));
    if (!a)
        return 1;
    for (int i = 0; i < n; i++)
        a[i] = (i + 1) * (i + 1);
    for (int i = 0; i < n; i++)
        printf("%d ", a[i]);
    printf("\n");
    free(a);
    return 0;
}
```

```text output
1 4 9 16 25 36
```

### التمرين 2

اكتب دالة `copy_text` ترجع نسخة جديدة من نص في ذاكرة محجوزة (مثل الدالة القياسية `strdup`):

```c exercise
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char *copy_text(const char *s)
{
    // احجز strlen(s) + 1 ثم انسخ
    return NULL;
}

int main(void)
{
    char *c = copy_text("نسخة");
    printf("%s\n", c ? c : "(فارغ)");
    free(c);
    return 0;
}
```

```c solution
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char *copy_text(const char *s)
{
    char *out = malloc(strlen(s) + 1);
    if (out)
        strcpy(out, s);
    return out;
}

int main(void)
{
    char *c = copy_text("نسخة");
    printf("%s\n", c ? c : "(فارغ)");
    free(c);
    return 0;
}
```

```text output
نسخة
```

## اختبر نفسك

```quiz
{"question": "ماذا ترجع malloc إذا فشلت في الحجز؟", "choices": ["0 بايت", "NULL", "-1", "تنهي البرنامج"], "answer": 1, "explanation": "تُرجع NULL، لذلك نفحص النتيجة دائمًا."}
```

```quiz
{"question": "ما اسم مشكلة نسيان استدعاء free؟", "choices": ["Stack overflow", "Memory leak (تسرب الذاكرة)", "Syntax error", "Double free"], "answer": 1, "explanation": "الذاكرة تبقى محجوزة بلا فائدة: تسرب الذاكرة."}
```

```quiz
{"question": "ما الفرق بين calloc وmalloc؟", "choices": ["calloc أسرع دائمًا", "calloc تملأ الذاكرة بالأصفار", "malloc لا تحتاج free", "لا فرق"], "answer": 1, "explanation": "calloc تحجز وتصفّر الذاكرة."}
```

## الخلاصة

- `malloc` تحجز من الكومة وقت التشغيل، و`free` تحرر.
- افحص `NULL` بعد كل حجز.
- `calloc` تصفّر، و`realloc` تغير الحجم (استخدم مؤشرًا مؤقتًا).
- لكل `malloc` يوجد `free` واحد.
