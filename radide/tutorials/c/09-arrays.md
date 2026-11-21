# الدرس 9: المصفوفات

لو أردت تخزين درجات 30 طالبًا، هل ستعرّف 30 متغيرًا؟ **المصفوفة** (array) تخزن مجموعة قيم من **نفس النوع** تحت اسم واحد، وكل قيمة لها رقم ترتيب يسمى **الفهرس** (index).

> **تشبيه:** المصفوفة مثل **صف من الخزائن** في المدرسة، كلها بنفس الحجم ومرقمة. الخزانة الأولى رقمها **0** وليس 1!

## تعريف المصفوفة واستخدامها

```c run
#include <stdio.h>

int main(void)
{
    int scores[5] = {90, 75, 88, 60, 95};

    printf("الأولى: %d\n", scores[0]);
    printf("الأخيرة: %d\n", scores[4]);

    scores[1] = 80;     // تعديل عنصر
    for (int i = 0; i < 5; i++)
        printf("scores[%d] = %d\n", i, scores[i]);
    return 0;
}
```

```text output
الأولى: 90
الأخيرة: 95
scores[0] = 90
scores[1] = 80
scores[2] = 88
scores[3] = 60
scores[4] = 95
```

- `int scores[5]` مصفوفة من 5 أعداد صحيحة، فهارسها من `0` إلى `4`.
- `{90, 75, ...}` القيم الابتدائية.
- `scores[i]` العنصر رقم `i`.

## طرق التهيئة

```c run
#include <stdio.h>

int main(void)
{
    int a[5] = {1, 2};          // الباقي أصفار
    int b[] = {4, 8, 15, 16};   // الحجم يُحسب تلقائيًا (4)
    int zeros[3] = {0};         // كلها أصفار

    int n = sizeof(b) / sizeof(b[0]);
    printf("عدد عناصر b: %d\n", n);
    for (int i = 0; i < 5; i++)
        printf("%d ", a[i]);
    printf("\n%d %d %d\n", zeros[0], zeros[1], zeros[2]);
    return 0;
}
```

```text output
عدد عناصر b: 4
1 2 0 0 0 
0 0 0
```

الحيلة `sizeof(b) / sizeof(b[0])` تحسب عدد العناصر: حجم المصفوفة كلها بالبايت مقسومًا على حجم عنصر واحد.

## عمليات شائعة: المجموع والأكبر والبحث

```c run
#include <stdio.h>

int main(void)
{
    int nums[] = {12, 45, 7, 23, 56, 89, 34};
    int n = sizeof(nums) / sizeof(nums[0]);

    int sum = 0, max = nums[0];
    for (int i = 0; i < n; i++) {
        sum += nums[i];
        if (nums[i] > max)
            max = nums[i];
    }
    printf("المجموع = %d\n", sum);
    printf("المتوسط = %.2f\n", (double)sum / n);
    printf("الأكبر = %d\n", max);

    int target = 23, pos = -1;
    for (int i = 0; i < n; i++) {
        if (nums[i] == target) {
            pos = i;
            break;
        }
    }
    printf("موقع %d هو %d\n", target, pos);
    return 0;
}
```

```text output
المجموع = 266
المتوسط = 38.00
الأكبر = 89
موقع 23 هو 3
```

## تمرير المصفوفة لدالة

عند تمرير مصفوفة لدالة نمرر **عدد عناصرها** أيضًا، لأن الدالة لا تعرف حجمها:

```c run
#include <stdio.h>

void print_array(const int arr[], int n)
{
    for (int i = 0; i < n; i++)
        printf("%d ", arr[i]);
    printf("\n");
}

void double_all(int arr[], int n)
{
    for (int i = 0; i < n; i++)
        arr[i] *= 2;
}

int main(void)
{
    int v[] = {1, 2, 3, 4};
    print_array(v, 4);
    double_all(v, 4);
    print_array(v, 4);
    return 0;
}
```

```text output
1 2 3 4 
2 4 6 8 
```

> **مهم:** على عكس المتغيرات العادية، الدالة **تستطيع تعديل** المصفوفة الأصلية! السبب أن C تمرر عنوان أول عنصر، لا نسخة من المصفوفة. لهذا كتبنا `const` في `print_array` لنَعِد بأننا لن نعدلها.

## ترتيب مصفوفة (الفقاعات)

```c run
#include <stdio.h>

void bubble_sort(int a[], int n)
{
    for (int i = 0; i < n - 1; i++)
        for (int j = 0; j < n - 1 - i; j++)
            if (a[j] > a[j + 1]) {          // تبديل العنصرين
                int tmp = a[j];
                a[j] = a[j + 1];
                a[j + 1] = tmp;
            }
}

int main(void)
{
    int a[] = {5, 2, 9, 1, 7};
    bubble_sort(a, 5);
    for (int i = 0; i < 5; i++)
        printf("%d ", a[i]);
    printf("\n");
    return 0;
}
```

```text output
1 2 5 7 9 
```

## المصفوفات ثنائية الأبعاد

جدول من صفوف وأعمدة:

```c run
#include <stdio.h>

int main(void)
{
    int grid[2][3] = {
        {1, 2, 3},
        {4, 5, 6}
    };
    for (int r = 0; r < 2; r++) {
        for (int c = 0; c < 3; c++)
            printf("%d ", grid[r][c]);
        printf("\n");
    }
    printf("العنصر في الصف 1 والعمود 2: %d\n", grid[1][2]);
    return 0;
}
```

```text output
1 2 3 
4 5 6 
العنصر في الصف 1 والعمود 2: 6
```

## أخطاء شائعة

- **الخروج عن حدود المصفوفة:** `scores[5]` في مصفوفة حجمها 5 خطأ (آخر فهرس 4). C **لا تحذرك** وقت التشغيل، بل تقرأ أو تكتب ذاكرة لا تخصك، وهذا من أخطر أخطاء C.
- **نسيان أن الفهرس يبدأ من 0.**
- **استخدام `sizeof` على مصفوفة داخل دالة:** هناك تعطيك حجم المؤشر لا المصفوفة، لذلك مرر العدد دائمًا.

## تمارين

### التمرين 1

اطبع عناصر المصفوفة بترتيب عكسي:

```c exercise
#include <stdio.h>

int main(void)
{
    int a[] = {10, 20, 30, 40, 50};
    // اطبع: 50 40 30 20 10
    return 0;
}
```

```c solution
#include <stdio.h>

int main(void)
{
    int a[] = {10, 20, 30, 40, 50};
    for (int i = 4; i >= 0; i--)
        printf("%d ", a[i]);
    printf("\n");
    return 0;
}
```

```text output
50 40 30 20 10
```

### التمرين 2

اكتب دالة `count_above` ترجع عدد العناصر الأكبر من قيمة معينة:

```c exercise
#include <stdio.h>

int count_above(const int a[], int n, int limit)
{
    // أكمل
    return 0;
}

int main(void)
{
    int marks[] = {45, 78, 90, 33, 66, 81};
    printf("%d\n", count_above(marks, 6, 50));
    return 0;
}
```

```c solution
#include <stdio.h>

int count_above(const int a[], int n, int limit)
{
    int count = 0;
    for (int i = 0; i < n; i++)
        if (a[i] > limit)
            count++;
    return count;
}

int main(void)
{
    int marks[] = {45, 78, 90, 33, 66, 81};
    printf("%d\n", count_above(marks, 6, 50));
    return 0;
}
```

```text output
4
```

## اختبر نفسك

```quiz
{"question": "ما فهرس آخر عنصر في `int a[10]`؟", "choices": ["10", "9", "11", "1"], "answer": 1, "explanation": "الفهارس من 0 إلى 9."}
```

```quiz
{"question": "إذا عدلت دالة عناصر مصفوفة مُررت لها، ماذا يحدث للأصل؟", "choices": ["لا يتغير", "يتغير، لأن C تمرر عنوان المصفوفة", "خطأ ترجمة", "يتغير العنصر الأول فقط"], "answer": 1, "explanation": "المصفوفة تُمرر كعنوان أول عنصر، فالتعديل على الأصل."}
```

```quiz
{"question": "ماذا تعطي `sizeof(a) / sizeof(a[0])` لمصفوفة معرفة في نفس الدالة؟", "choices": ["حجم العنصر", "عدد العناصر", "آخر عنصر", "عنوان المصفوفة"], "answer": 1, "explanation": "الحجم الكلي مقسومًا على حجم عنصر واحد = عدد العناصر."}
```

## الخلاصة

- المصفوفة عناصر من نفس النوع، والفهرس يبدأ من `0`.
- مرر عدد العناصر مع المصفوفة إلى الدوال.
- الدالة تستطيع تعديل المصفوفة الأصلية.
- احذر الخروج عن حدود المصفوفة.
