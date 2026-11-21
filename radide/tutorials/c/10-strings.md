# الدرس 10: النصوص في C

في C لا يوجد نوع جاهز اسمه «نص» كما في اللغات الأخرى. النص هو ببساطة **مصفوفة من الحروف** تنتهي بحرف خاص قيمته صفر: `'\0'`.

> **تشبيه:** النص في C مثل **قطار** من العربات (الحروف)، وفي آخره عربة حمراء مكتوب عليها «النهاية» (`'\0'`). كل دوال النصوص تمشي على العربات حتى تصل للعربة الحمراء.

## تعريف نص

```c run
#include <stdio.h>

int main(void)
{
    char word[] = "Hello";      // 5 حروف + '\0' = 6 بايت
    printf("%s\n", word);
    printf("الحرف الأول: %c\n", word[0]);
    printf("الحجم بالبايت: %zu\n", sizeof(word));

    word[0] = 'J';              // يمكن تعديل الحروف
    printf("%s\n", word);
    return 0;
}
```

```text output
Hello
الحرف الأول: H
الحجم بالبايت: 6
Jello
```

## دوال `string.h`

| الدالة | وظيفتها |
|---|---|
| `strlen(s)` | طول النص (بدون `'\0'`) |
| `strcpy(dst, src)` | نسخ نص |
| `strcat(dst, src)` | إلحاق نص بآخر |
| `strcmp(a, b)` | مقارنة: `0` إن تساويا |
| `strchr(s, c)` | البحث عن حرف |
| `strstr(s, sub)` | البحث عن نص داخل نص |

```c run
#include <stdio.h>
#include <string.h>

int main(void)
{
    char first[20] = "Ahmed";
    char full[50];

    printf("طول الاسم: %zu\n", strlen(first));

    strcpy(full, first);        // full = "Ahmed"
    strcat(full, " Ali");       // full = "Ahmed Ali"
    printf("%s\n", full);

    if (strcmp(first, "Ahmed") == 0)
        printf("الاسمان متطابقان\n");

    if (strstr(full, "Ali") != NULL)
        printf("وجدنا Ali\n");
    return 0;
}
```

```text output
طول الاسم: 5
Ahmed Ali
الاسمان متطابقان
وجدنا Ali
```

> **مهم جدًا:** لا يمكن مقارنة النصوص بـ `==` ولا نسخها بـ `=` في C! استخدم `strcmp` و`strcpy`. والسطر `full = first;` خطأ ترجمة.

## المرور على حروف النص

```c run
#include <stdio.h>
#include <ctype.h>

int main(void)
{
    char text[] = "Hello World 2024";
    int letters = 0, digits = 0, spaces = 0;

    for (int i = 0; text[i] != '\0'; i++) {
        if (isalpha(text[i])) letters++;
        else if (isdigit(text[i])) digits++;
        else if (text[i] == ' ') spaces++;
        text[i] = toupper(text[i]);
    }
    printf("%s\n", text);
    printf("حروف: %d، أرقام: %d، مسافات: %d\n", letters, digits, spaces);
    return 0;
}
```

```text output
HELLO WORLD 2024
حروف: 10، أرقام: 4، مسافات: 2
```

مكتبة `ctype.h` فيها دوال لفحص الحروف: `isalpha` (حرف؟) و`isdigit` (رقم؟) و`toupper` (حرف كبير).

## بناء النصوص بـ `snprintf`

`snprintf` مثل `printf`، لكنها تكتب في مصفوفة بدل الشاشة، مع حد أقصى آمن:

```c run
#include <stdio.h>

int main(void)
{
    char msg[64];
    int age = 30;
    double salary = 7500.5;
    snprintf(msg, sizeof(msg), "العمر %d والراتب %.1f", age, salary);
    printf("[%s]\n", msg);
    return 0;
}
```

```text output
[العمر 30 والراتب 7500.5]
```

## تحويل النص إلى رقم

```c run
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int n = atoi("123");
    double d = atof("3.75");
    printf("%d %.2f\n", n + 1, d * 2);
    return 0;
}
```

```text output
124 7.50
```

## ماذا عن العربية؟

النصوص العربية تعمل مع `printf("%s")` بلا مشكلة، لكن تذكر أن الحرف العربي في UTF-8 يأخذ **بايتين**، فـ `strlen` تحسب البايتات لا الحروف:

```c run
#include <stdio.h>
#include <string.h>

int main(void)
{
    char ar[] = "سلام";
    printf("%s: %zu بايت\n", ar, strlen(ar));
    return 0;
}
```

```text output
سلام: 8 بايت
```

## أخطاء شائعة

- **مصفوفة صغيرة جدًا:** `char s[5] = "Hello";` لا يتسع لـ `'\0'`. اجعل الحجم دائمًا أكبر من النص بواحد على الأقل.
- **`strcpy` و`strcat` بلا حدود:** إن كان النص المنسوخ أطول من المصفوفة تُكتب ذاكرة لا تخصك (buffer overflow). عند الشك استخدم `snprintf`.
- **المقارنة بـ `==`:** تقارن العناوين لا المحتوى.

## تمارين

### التمرين 1

اكتب دالة `reverse` تعكس نصًا في مكانه:

```c exercise
#include <stdio.h>
#include <string.h>

void reverse(char s[])
{
    // بدّل الحرف الأول مع الأخير، ثم الثاني مع قبل الأخير ...
}

int main(void)
{
    char w[] = "programming";
    reverse(w);
    printf("%s\n", w);
    return 0;
}
```

```c solution
#include <stdio.h>
#include <string.h>

void reverse(char s[])
{
    int n = strlen(s);
    for (int i = 0; i < n / 2; i++) {
        char tmp = s[i];
        s[i] = s[n - 1 - i];
        s[n - 1 - i] = tmp;
    }
}

int main(void)
{
    char w[] = "programming";
    reverse(w);
    printf("%s\n", w);
    return 0;
}
```

```text output
gnimmargorp
```

### التمرين 2

احسب عدد مرات ظهور الحرف `a` في النص:

```c exercise
#include <stdio.h>

int main(void)
{
    char s[] = "banana and papaya";
    int count = 0;
    // أكمل
    printf("%d\n", count);
    return 0;
}
```

```c solution
#include <stdio.h>

int main(void)
{
    char s[] = "banana and papaya";
    int count = 0;
    for (int i = 0; s[i] != '\0'; i++)
        if (s[i] == 'a')
            count++;
    printf("%d\n", count);
    return 0;
}
```

```text output
7
```

## اختبر نفسك

```quiz
{"question": "كم بايت يحتاج النص \"Cat\" في مصفوفة char؟", "choices": ["3", "4", "2", "6"], "answer": 1, "explanation": "3 حروف + الحرف الختامي '\\0' = 4."}
```

```quiz
{"question": "كيف نقارن نصين في C؟", "choices": ["a == b", "strcmp(a, b) == 0", "a = b", "strlen(a) == strlen(b)"], "answer": 1, "explanation": "strcmp تقارن المحتوى وترجع 0 عند التطابق."}
```

```quiz
{"question": "ماذا ترجع `strlen(\"سلام\")` مع ملفات UTF-8؟", "choices": ["4", "8", "5", "2"], "answer": 1, "explanation": "كل حرف عربي بايتان في UTF-8، وstrlen تعد البايتات."}
```

## الخلاصة

- النص في C مصفوفة `char` تنتهي بـ `'\0'`.
- `string.h`: `strlen` و`strcpy` و`strcat` و`strcmp` و`strstr`.
- لا تقارن بـ `==` ولا تنسخ بـ `=`.
- `snprintf` لبناء النصوص بأمان، و`atoi`/`atof` للتحويل لأرقام.
