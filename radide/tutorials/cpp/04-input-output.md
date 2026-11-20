# الدرس 4: الإدخال والإخراج

حتى الآن كانت برامجنا تطبع فقط. اليوم سنجعلها **تسأل المستخدم** وتستقبل إجابته، ثم نتعلم كيف ننسّق الناتج بشكل جميل.

## القراءة من لوحة المفاتيح: `std::cin`

إذا كانت `std::cout` هي الشاشة، فإن `std::cin` (تُنطق «سي-إن») هي **لوحة المفاتيح**. ونستخدم معها العامل `>>` (السهم متجه نحو المتغير، أي أن البيانات تدخل إليه).

> **تشبيه:** `std::cout <<` مثل فم يتكلم، و`std::cin >>` مثل أذن تسمع وتحفظ ما سمعته في المتغير.

```cpp run
#include <iostream>

int main()
{
    int age = 0;
    std::cout << "كم عمرك؟ ";
    std::cin >> age;
    std::cout << "بعد 10 سنوات سيكون عمرك " << age + 10 << " سنة\n";
    return 0;
}
```

عند الضغط على «جرّبه» اكتب عمرك في نافذة الإدخال ثم اضغط Enter. مثلًا لو أدخلت:

```text input
25
```

يكون الناتج:

```text output
كم عمرك؟ بعد 10 سنوات سيكون عمرك 35 سنة
```

> **لماذا ظهر الناتج على سطر واحد؟** لأن الرقم الذي تكتبه أنت (ومعه Enter) يظهر على الشاشة في الكونسول الحقيقي، لكنه ليس جزءًا من ناتج البرنامج نفسه. في كل الأمثلة سنعرض ناتج البرنامج فقط.

## قراءة عدة قيم مرة واحدة

يمكن ربط عدة متغيرات بـ `>>`، ويفصل المستخدم بينها بمسافة أو Enter:

```cpp run
#include <iostream>

int main()
{
    double width = 0, height = 0;
    std::cout << "أدخل العرض والارتفاع: ";
    std::cin >> width >> height;
    std::cout << "المساحة = " << width * height << "\n";
    std::cout << "المحيط = " << 2 * (width + height) << "\n";
    return 0;
}
```

```text input
4 2.5
```

```text output
أدخل العرض والارتفاع: المساحة = 10
المحيط = 13
```

## قراءة النصوص: `>>` مقابل `std::getline`

العامل `>>` يقرأ **كلمة واحدة** فقط ويتوقف عند أول مسافة. لقراءة سطر كامل (مثل الاسم الثلاثي) نستخدم `std::getline`:

```cpp run
#include <iostream>
#include <string>

int main()
{
    std::string firstWord;
    std::string fullLine;

    std::cout << "اكتب اسمك الكامل: ";
    std::cin >> firstWord;            // كلمة واحدة فقط
    std::getline(std::cin, fullLine); // باقي السطر

    std::cout << "الكلمة الأولى: " << firstWord << "\n";
    std::cout << "الباقي:" << fullLine << "\n";
    return 0;
}
```

```text input
محمد علي حسن
```

```text output
اكتب اسمك الكامل: الكلمة الأولى: محمد
الباقي: علي حسن
```

### الفخ الشهير: `>>` ثم `getline`

بعد `std::cin >> age` يبقى رمز السطر الجديد (Enter) في ذاكرة الإدخال. فإذا استدعيت `getline` بعدها مباشرة، قرأت سطرًا **فارغًا**! الحل: `std::cin >> std::ws` لتجاهل المسافات والأسطر الفارغة قبل القراءة:

```cpp run
#include <iostream>
#include <string>

int main()
{
    int age = 0;
    std::string name;

    std::cout << "العمر: ";
    std::cin >> age;
    std::cout << "الاسم الكامل: ";
    std::getline(std::cin >> std::ws, name); // تجاهل Enter المتبقي

    std::cout << "\nأهلًا يا " << name << "، عمرك " << age << " سنة\n";
    return 0;
}
```

```text input
30
سارة أحمد
```

```text output
العمر: الاسم الكامل:
أهلًا يا سارة أحمد، عمرك 30 سنة
```

## تنسيق الناتج: `<iomanip>`

المكتبة `<iomanip>` تعطينا أدوات للتحكم في شكل الأرقام:

- `std::fixed` و`std::setprecision(n)`: عدد الأرقام بعد الفاصلة العشرية.
- `std::setw(n)`: اجعل العنصر التالي يشغل `n` خانة على الأقل (مفيد للجداول).

```cpp run
#include <iomanip>
#include <iostream>

int main()
{
    double price = 12.5;
    double tax = price * 0.14;

    std::cout << std::fixed << std::setprecision(2);
    std::cout << "السعر:   " << price << "\n";
    std::cout << "الضريبة: " << tax << "\n";
    std::cout << "الإجمالي: " << price + tax << "\n\n";

    std::cout << std::setw(8) << "Item" << std::setw(8) << "Qty" << "\n";
    std::cout << std::setw(8) << "Pen" << std::setw(8) << 3 << "\n";
    std::cout << std::setw(8) << "Book" << std::setw(8) << 12 << "\n";
    return 0;
}
```

```text output
السعر:   12.50
الضريبة: 1.75
الإجمالي: 14.25

    Item     Qty
     Pen       3
    Book      12
```

> **ملحوظة:** `std::setw` يعدّ **البايتات** لا الحروف، والحرف العربي يشغل بايتين في ترميز UTF-8، لذلك استخدمناه هنا مع نصوص إنجليزية فقط لكي تستقيم الأعمدة.

## ماذا لو أدخل المستخدم شيئًا خاطئًا؟

إذا طلبت رقمًا وكتب المستخدم `abc`، تفشل القراءة وتبقى قيمة المتغير صفرًا، ويدخل `std::cin` في **حالة فشل**. يمكنك فحص ذلك:

```cpp run
#include <iostream>

int main()
{
    int n = 0;
    std::cout << "أدخل رقمًا: ";
    if (std::cin >> n)
        std::cout << "شكرًا، أدخلت " << n << "\n";
    else
        std::cout << "هذا ليس رقمًا!\n";
    return 0;
}
```

```text input
abc
```

```text output
أدخل رقمًا: هذا ليس رقمًا!
```

سنفهم `if` و`else` جيدًا في درس الشروط، لكن الفكرة هنا أن `std::cin >> n` نفسها تعطي «نجحت» أو «فشلت».

## أخطاء شائعة

### عكس اتجاه الأسهم

`std::cin << x` أو `std::cout >> x` من أشهر أخطاء المبتدئين. تذكّر: **الأسهم تشير إلى اتجاه حركة البيانات**. مع `cin` تذهب البيانات إلى المتغير `>>`، ومع `cout` تذهب إلى الشاشة `<<`. رسالة الخطأ في هذه الحالة طويلة جدًا وتبدأ بشيء مثل:

```text
error: no match for 'operator<<' (operand types are 'std::istream' ...
```

ومعناها: «لا يوجد عامل `<<` يناسب مدخلًا من نوع `istream`»، أي استخدمت السهم الخطأ.

### نسيان `#include <string>` أو `<iomanip>`

<!-- compile-error -->
```cpp
#include <iostream>
int main()
{
    std::cout << std::setprecision(2) << 3.14159;
    return 0;
}
```

```text
main.cpp:4:23: error: 'setprecision' is not a member of 'std'
```

**المعنى:** `setprecision` غير معروفة لأن مكتبتها `<iomanip>` لم تُضَف.

## تمارين

### التمرين 1

اطلب من المستخدم درجة الحرارة بالسيلزيوس، واطبعها بالفهرنهايت (F = C × 9 / 5 + 32) برقم واحد بعد الفاصلة.

```cpp exercise
#include <iomanip>
#include <iostream>

int main()
{
    // اقرأ C ثم اطبع F
    return 0;
}
```

```cpp solution
#include <iomanip>
#include <iostream>

int main()
{
    double c = 0;
    std::cout << "درجة الحرارة (سيلزيوس): ";
    std::cin >> c;
    double f = c * 9 / 5 + 32;
    std::cout << std::fixed << std::setprecision(1);
    std::cout << c << " C = " << f << " F\n";
    return 0;
}
```

```text input
37
```

```text output
درجة الحرارة (سيلزيوس): 37.0 C = 98.6 F
```

### التمرين 2

اطلب اسم المستخدم الكامل (قد يحتوي مسافات) ومدينته، ثم اطبع رسالة ترحيب.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    // استخدم std::getline
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

int main()
{
    std::string name, city;
    std::cout << "اسمك الكامل: ";
    std::getline(std::cin, name);
    std::cout << "مدينتك: ";
    std::getline(std::cin, city);
    std::cout << "\nمرحبًا " << name << " من " << city << "!\n";
    return 0;
}
```

```text input
خالد محمود
المنصورة
```

```text output
اسمك الكامل: مدينتك:
مرحبًا خالد محمود من المنصورة!
```

### التمرين 3

اقرأ ثلاث درجات (أعداد صحيحة) واطبع مجموعها ومتوسطها برقمين بعد الفاصلة.

```cpp exercise
#include <iomanip>
#include <iostream>

int main()
{
    // انتبه: قسمة int على int تحذف الكسر!
    return 0;
}
```

```cpp solution
#include <iomanip>
#include <iostream>

int main()
{
    int a = 0, b = 0, c = 0;
    std::cout << "أدخل ثلاث درجات: ";
    std::cin >> a >> b >> c;
    int sum = a + b + c;
    double average = sum / 3.0;   // 3.0 وليس 3 لكي نحصل على كسر
    std::cout << "\nالمجموع: " << sum << "\n";
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "المتوسط: " << average << "\n";
    return 0;
}
```

```text input
80 95 90
```

```text output
أدخل ثلاث درجات:
المجموع: 265
المتوسط: 88.33
```

## اختبر نفسك

```quiz
{"question": "أي سطر يقرأ عددًا من المستخدم إلى المتغير x؟", "choices": ["std::cout >> x;", "std::cin << x;", "std::cin >> x;", "std::read(x);"], "answer": 2, "explanation": "مع cin نستخدم >> لأن البيانات تتجه إلى المتغير."}
```

```quiz
{"question": "المستخدم كتب: أحمد علي. ماذا تحفظ std::cin >> name؟", "choices": ["أحمد علي", "أحمد", "علي", "لا شيء"], "answer": 1, "explanation": "العامل >> يتوقف عند أول مسافة، فيقرأ كلمة واحدة فقط. لقراءة السطر كله استخدم std::getline."}
```

```quiz
{"question": "ماذا يطبع: std::cout << std::fixed << std::setprecision(2) << 3.14159;؟", "choices": ["3.14159", "3.1", "3.14", "3"], "answer": 2, "explanation": "fixed مع setprecision(2) يعرض رقمين بعد الفاصلة العشرية."}
```

```quiz
{"question": "لماذا قد تقرأ getline سطرًا فارغًا بعد cin >> age؟", "choices": ["لأن getline معطلة", "لأن رمز Enter بقي في ذاكرة الإدخال", "لأن age ليست نصًا", "لأننا نسينا return 0"], "answer": 1, "explanation": "العامل >> يترك رمز السطر الجديد، والحل std::getline(std::cin >> std::ws, s)."}
```

## الخلاصة

- `std::cin >> x` يقرأ قيمة، و`std::getline(std::cin, s)` يقرأ سطرًا كاملًا.
- استخدم `std::cin >> std::ws` قبل `getline` إذا سبقتها قراءة بـ `>>`.
- `<iomanip>`: `std::fixed` و`std::setprecision` و`std::setw` لتنسيق الناتج.
- `if (std::cin >> n)` يتحقق من نجاح القراءة.
