# الدرس 7: حلقات التكرار

تخيل أنك تريد طباعة الأرقام من 1 إلى 1000. هل ستكتب 1000 سطر؟ بالطبع لا! **حلقات التكرار** (Loops) تجعل الكمبيوتر يكرر العمل نيابة عنك، وهذا أكثر شيء يجيده الكمبيوتر.

## حلقة `while`

تكرر ما دام الشرط صحيحًا:

```cpp
while (الشرط)
{
    // يتكرر ما دام الشرط صحيحًا
}
```

> **تشبيه:** «ما دام الطبق فيه أكل، كُل لقمة». تفحص الطبق قبل كل لقمة، وتتوقف عندما يفرغ.

```cpp run
#include <iostream>

int main()
{
    int i = 1;
    while (i <= 5)
    {
        std::cout << "العدد " << i << "\n";
        i++;  // مهم جدًا! وإلا تكررت الحلقة إلى الأبد
    }
    std::cout << "انتهت الحلقة\n";
    return 0;
}
```

```text output
العدد 1
العدد 2
العدد 3
العدد 4
العدد 5
انتهت الحلقة
```

## حلقة `for`

عندما تعرف عدد مرات التكرار مسبقًا، تكون `for` أوضح، لأنها تجمع الأجزاء الثلاثة في سطر واحد:

```cpp
for (البداية; الشرط; الخطوة)
```

```cpp run
#include <iostream>

int main()
{
    // جدول ضرب العدد 7
    for (int i = 1; i <= 10; i++)
    {
        std::cout << "7 x " << i << " = " << 7 * i << "\n";
    }
    return 0;
}
```

```text output
7 x 1 = 7
7 x 2 = 14
7 x 3 = 21
7 x 4 = 28
7 x 5 = 35
7 x 6 = 42
7 x 7 = 49
7 x 8 = 56
7 x 9 = 63
7 x 10 = 70
```

ترتيب التنفيذ:

1. `int i = 1` مرة واحدة في البداية.
2. فحص الشرط `i <= 10`؛ إذا كان خاطئًا تنتهي الحلقة.
3. تنفيذ الجسم.
4. تنفيذ الخطوة `i++`، ثم العودة إلى الخطوة 2.

المتغير `i` المعرّف داخل `for` موجود داخل الحلقة فقط.

## المجموع والعداد: نمطان مهمان جدًا

```cpp run
#include <iostream>

int main()
{
    int sum = 0;     // المجمِّع يبدأ بصفر
    int evens = 0;   // العداد يبدأ بصفر

    for (int n = 1; n <= 100; n++)
    {
        sum += n;
        if (n % 2 == 0)
            evens++;
    }
    std::cout << "مجموع 1 إلى 100 = " << sum << "\n";
    std::cout << "عدد الأرقام الزوجية = " << evens << "\n";

    // العد التنازلي بخطوة 2
    for (int k = 10; k > 0; k -= 2)
        std::cout << k << " ";
    std::cout << "\n";
    return 0;
}
```

```text output
مجموع 1 إلى 100 = 5050
عدد الأرقام الزوجية = 50
10 8 6 4 2
```

## حلقة `do ... while`

تنفذ الجسم **مرة واحدة على الأقل**، ثم تفحص الشرط في النهاية. مناسبة للقوائم والتحقق من المدخلات:

```cpp run
#include <iostream>

int main()
{
    int choice = 0;
    do
    {
        std::cout << "1) ابدأ  2) إعدادات  0) خروج: ";
        std::cin >> choice;
        if (choice == 1)
            std::cout << "\nبدأت اللعبة!\n";
        else if (choice == 2)
            std::cout << "\nالإعدادات\n";
    } while (choice != 0);

    std::cout << "\nمع السلامة\n";
    return 0;
}
```

```text input
1
2
0
```

```text output
1) ابدأ  2) إعدادات  0) خروج:
بدأت اللعبة!
1) ابدأ  2) إعدادات  0) خروج:
الإعدادات
1) ابدأ  2) إعدادات  0) خروج:
مع السلامة
```

لاحظ الفاصلة المنقوطة بعد `while (...)` في نهاية `do ... while`.

## `break` و`continue`

- `break`: اخرج من الحلقة فورًا.
- `continue`: تجاهل باقي هذه الدورة وانتقل إلى الدورة التالية.

```cpp run
#include <iostream>

int main()
{
    // اطبع الأعداد الفردية فقط حتى نصل إلى أول عدد يقبل القسمة على 7
    for (int i = 1; i <= 20; i++)
    {
        if (i % 7 == 0)
            break;        // توقف تمامًا
        if (i % 2 == 0)
            continue;     // تخطَّ الزوجي
        std::cout << i << " ";
    }
    std::cout << "\n";
    return 0;
}
```

```text output
1 3 5
```

## الحلقات المتداخلة

حلقة داخل حلقة: الداخلية تكتمل بالكامل في كل دورة من دورات الخارجية، مثل عقرب الدقائق الذي يلف دورة كاملة مع كل ساعة.

```cpp run
#include <iostream>

int main()
{
    for (int row = 1; row <= 4; row++)
    {
        for (int col = 1; col <= row; col++)
            std::cout << "*";
        std::cout << "\n";
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

## قراءة عدد غير معروف من المدخلات

يمكن استخدام `while (std::cin >> x)` لقراءة الأرقام حتى تنتهي المدخلات:

```cpp run
#include <iostream>

int main()
{
    double x = 0, total = 0;
    int count = 0;
    while (std::cin >> x)
    {
        total += x;
        count++;
    }
    std::cout << "عدد القيم: " << count << "، المجموع: " << total << "\n";
    return 0;
}
```

```text input
5 10 15 20
```

```text output
عدد القيم: 4، المجموع: 50
```

## أخطاء شائعة

### الحلقة اللانهائية

```cpp
int i = 1;
while (i <= 5)
{
    std::cout << i;
    // نسينا i++ ← الحلقة لن تنتهي أبدًا!
}
```

لا يظهر أي خطأ من المترجم هنا، لكن البرنامج «يعلق». في الـ IDE اضغط زر **Stop** (أو Shift+F5) لإيقافه.

### الخطأ بمقدار واحد (Off-by-one)

`for (int i = 0; i <= 10; i++)` تتكرر **11** مرة وليس 10! فكّر جيدًا: هل تريد `<` أم `<=`؟ وهل تبدأ من 0 أم من 1؟

### فاصلة منقوطة بعد `for`

```cpp
for (int i = 0; i < 5; i++);   // ← الحلقة جسمها فارغ!
    std::cout << "مرحبا";       // تُطبع مرة واحدة فقط
```

## تمارين

### التمرين 1

اقرأ عددًا `n` واحسب مضروبه `n!` (مثلًا 5! = 1×2×3×4×5 = 120). استخدم `long long`.

```cpp exercise
#include <iostream>

int main()
{
    int n = 0;
    std::cin >> n;
    // احسب المضروب
    return 0;
}
```

```cpp solution
#include <iostream>

int main()
{
    int n = 0;
    std::cin >> n;
    long long factorial = 1;
    for (int i = 2; i <= n; i++)
        factorial *= i;
    std::cout << n << "! = " << factorial << "\n";
    return 0;
}
```

```text input
10
```

```text output
10! = 3628800
```

### التمرين 2

لعبة تخمين: الرقم السري 42. اقرأ تخمينات المستخدم واطبع «أكبر» أو «أصغر» حتى يصيب، ثم اطبع عدد المحاولات.

```cpp exercise
#include <iostream>

int main()
{
    const int secret = 42;
    // استخدم do ... while
    return 0;
}
```

```cpp solution
#include <iostream>

int main()
{
    const int secret = 42;
    int guess = 0, tries = 0;
    do
    {
        std::cin >> guess;
        tries++;
        if (guess < secret)
            std::cout << "أكبر\n";
        else if (guess > secret)
            std::cout << "أصغر\n";
    } while (guess != secret);
    std::cout << "أحسنت! عرفته في " << tries << " محاولات\n";
    return 0;
}
```

```text input
50
30
42
```

```text output
أصغر
أكبر
أحسنت! عرفته في 3 محاولات
```

### التمرين 3

اطبع الأعداد الأولية من 2 إلى 30. العدد الأولي لا يقبل القسمة إلا على 1 وعلى نفسه. (تلميح: حلقتان متداخلتان.)

```cpp exercise
#include <iostream>

int main()
{
    // لكل n من 2 إلى 30: جرّب القسمة على كل d من 2 حتى d * d <= n
    return 0;
}
```

```cpp solution
#include <iostream>

int main()
{
    for (int n = 2; n <= 30; n++)
    {
        bool prime = true;
        for (int d = 2; d * d <= n; d++)
        {
            if (n % d == 0)
            {
                prime = false;
                break;
            }
        }
        if (prime)
            std::cout << n << " ";
    }
    std::cout << "\n";
    return 0;
}
```

```text output
2 3 5 7 11 13 17 19 23 29
```

## اختبر نفسك

```quiz
{"question": "كم مرة تتكرر: for (int i = 0; i < 5; i++)؟", "choices": ["4", "5", "6", "لا نهائي"], "answer": 1, "explanation": "i تأخذ القيم 0 و1 و2 و3 و4، أي 5 مرات."}
```

```quiz
{"question": "ما الحلقة التي تنفذ جسمها مرة واحدة على الأقل؟", "choices": ["while", "for", "do ... while", "لا توجد"], "answer": 2, "explanation": "do ... while تفحص الشرط بعد تنفيذ الجسم."}
```

```quiz
{"question": "ماذا تفعل continue؟", "choices": ["تخرج من الحلقة نهائيًا", "تنهي البرنامج", "تنتقل مباشرة إلى الدورة التالية", "تعيد الحلقة من البداية بقيم جديدة"], "answer": 2, "explanation": "continue تتخطى باقي الدورة الحالية فقط."}
```

```quiz
{"question": "برنامجك يعلق ولا ينتهي وفيه حلقة while. ما السبب المحتمل؟", "choices": ["نسيت #include", "الشرط لا يصبح خاطئًا أبدًا (نسيت تغيير المتغير)", "استخدمت int", "خطأ في المترجم"], "answer": 1, "explanation": "هذه حلقة لا نهائية: تأكد أن شيئًا داخل الحلقة يغير الشرط."}
```

## الخلاصة

- `while` تكرر ما دام الشرط صحيحًا، و`for` عندما تعرف عدد المرات، و`do ... while` لمرة واحدة على الأقل.
- المجمِّع والعداد يبدآن بصفر.
- `break` للخروج، و`continue` للتخطي.
- احذر الحلقة اللانهائية والخطأ بمقدار واحد.
