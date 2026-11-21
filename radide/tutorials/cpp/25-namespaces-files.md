# الدرس 25: فضاءات الأسماء وتقسيم البرنامج إلى ملفات

عندما يكبر البرنامج إلى آلاف الأسطر، لا يمكن أن يبقى في ملف واحد. وعندما تستخدم مكتبات كتبها آخرون، قد تتكرر الأسماء: دالتك اسمها `print` ودالة المكتبة اسمها `print` أيضًا! في هذا الدرس نتعلم حل المشكلتين: **فضاءات الأسماء** (namespaces) و**الملفات المتعددة**.

## فضاءات الأسماء (Namespaces)

> **تشبيه:** في الفصل طالبان اسمهما «محمد». المدرّس يقول «محمد أحمد» و«محمد علي». الاسم الثاني هو مثل **فضاء الأسماء**: يميز بين الأشياء التي تحمل نفس الاسم.

أنت تعرف فضاء أسماء واحدًا بالفعل: `std`. ولهذا نكتب `std::cout`. ويمكنك صنع فضاءاتك الخاصة:

```cpp run
#include <iostream>

namespace geometry
{
    const double PI = 3.14159;

    double circleArea(double r) { return PI * r * r; }
    double area(double w, double h) { return w * h; }
}

namespace finance
{
    double area(double total, double share) { return total * share; }   // نفس الاسم، معنى آخر
}

int main()
{
    std::cout << geometry::circleArea(2) << "\n";
    std::cout << geometry::area(3, 4) << "\n";
    std::cout << finance::area(1000, 0.25) << "\n";
    std::cout << geometry::PI << "\n";
    return 0;
}
```

```text output
12.5664
12
250
3.14159
```

العامل `::` يسمى **عامل تحديد النطاق** (scope resolution operator)، ويُقرأ «التابع لـ».

### فضاءات متداخلة و`using`

```cpp run
#include <iostream>
#include <string>

namespace school::grades     // فضاء متداخل بصيغة C++17
{
    std::string letter(int g)
    {
        if (g >= 85) return "A";
        if (g >= 75) return "B";
        if (g >= 65) return "C";
        return "F";
    }
}

int main()
{
    std::cout << school::grades::letter(90) << "\n";

    namespace sg = school::grades;     // اسم مختصر (alias)
    std::cout << sg::letter(70) << "\n";

    using school::grades::letter;      // أدخل اسمًا واحدًا فقط
    std::cout << letter(50) << "\n";
    return 0;
}
```

```text output
A
C
F
```

> **قاعدة مهمة:** لا تكتب `using namespace std;` في ملفات الترويسة `.h` أبدًا، لأنها ستُفرض على كل من يضمّن ملفك. وفي ملفات `.cpp` الصغيرة يمكن استخدامها بحذر، أو الأفضل استخدام `using` لأسماء محددة.

## لماذا نقسّم البرنامج إلى ملفات؟

- **التنظيم:** كل ملف مسؤول عن موضوع واحد (الطلاب، الملفات، الواجهة...).
- **إعادة الاستخدام:** تنقل ملف الأدوات إلى مشروع آخر كما هو.
- **العمل الجماعي:** كل مبرمج يعمل على ملفاته.
- **سرعة الترجمة:** عند تعديل ملف واحد، يُعاد ترجمة هذا الملف فقط.

## ملف الترويسة `.h` وملف التنفيذ `.cpp`

نقسم كل وحدة إلى ملفين:

- **ملف الترويسة** (header) `.h` أو `.hpp`: **التصريحات** فقط، أي «ماذا يوجد». مثل **فهرس الكتاب**.
- **ملف التنفيذ** `.cpp`: **التعريفات**، أي «كيف يعمل». مثل **فصول الكتاب**.

لنبنِ مثالًا من ثلاثة ملفات.

**الملف `mathutils.h`:**

```cpp
#pragma once          // لا تضمّن هذا الملف أكثر من مرة

#include <vector>

namespace mathutils
{
    double average(const std::vector<double>& values);
    double maxValue(const std::vector<double>& values);
    bool isPrime(int n);
}
```

**الملف `mathutils.cpp`:**

```cpp
#include "mathutils.h"   // علامات تنصيص لملفاتنا، و< > لمكتبات النظام

#include <algorithm>
#include <numeric>

namespace mathutils
{
    double average(const std::vector<double>& values)
    {
        if (values.empty())
            return 0;
        return std::accumulate(values.begin(), values.end(), 0.0) / values.size();
    }

    double maxValue(const std::vector<double>& values)
    {
        return values.empty() ? 0 : *std::max_element(values.begin(), values.end());
    }

    bool isPrime(int n)
    {
        if (n < 2)
            return false;
        for (int d = 2; d * d <= n; d++)
            if (n % d == 0)
                return false;
        return true;
    }
}
```

**الملف `main.cpp`:**

```cpp
#include <iostream>
#include "mathutils.h"

int main()
{
    std::vector<double> marks = {70, 85, 92, 64};
    std::cout << "المتوسط: " << mathutils::average(marks) << "\n";
    std::cout << "الأعلى: " << mathutils::maxValue(marks) << "\n";
    std::cout << "هل 97 أولي؟ " << (mathutils::isPrime(97) ? "نعم" : "لا") << "\n";
    return 0;
}
```

الناتج:

```text
المتوسط: 77.75
الأعلى: 92
هل 97 أولي؟ نعم
```

### كيف تُبنى الملفات معًا؟

1. **الترجمة:** كل ملف `.cpp` يُترجم وحده إلى ملف كائني (`.o`). عندما يرى `main.cpp` السطر `#include "mathutils.h"` فإنه ينسخ محتوى الترويسة مكانه، فيعرف أن `average` موجودة (التصريح يكفي للترجمة).
2. **الربط (Linking):** **الرابط** (linker) يجمع الملفات الكائنية في ملف `.exe` واحد، ويصل كل استدعاء بتعريفه الحقيقي.

بسطر الأوامر يكون الأمر هكذا:

```text
g++ -std=c++20 main.cpp mathutils.cpp -o app.exe
```

### في الـ IDE

1. من قائمة **Project** اختر **Add Module** واكتب `mathutils`، فتُنشأ `mathutils.cpp` وتُضاف إلى المشروع.
2. أنشئ ملف `mathutils.h` في مجلد المشروع نفسه (**Project > Open Project Folder**).
3. عند الضغط على **F5** تترجم الـ IDE كل ملفات `.cpp` في المشروع وتربطها معًا تلقائيًا.

### `#pragma once` (حارس الترويسة)

إذا ضُمّنت الترويسة مرتين في نفس الملف (مباشرة أو عبر ترويسة أخرى) قد يشتكي المترجم من تكرار التعريفات. `#pragma once` تمنع ذلك. وستجد في الكود القديم الطريقة التقليدية المكافئة:

```cpp
#ifndef MATHUTILS_H
#define MATHUTILS_H
// ... التصريحات ...
#endif
```

## ماذا نضع في الترويسة؟

| في الترويسة `.h` | في ملف التنفيذ `.cpp` |
|---|---|
| تصريحات الدوال | تعريفات الدوال |
| تعريفات الأصناف `class` (مع تصريحات دوالها) | تعريفات دوال الأصناف `Class::func` |
| القوالب كاملة (لأن المترجم يحتاج كودها) | المتغيرات العامة (إن وُجدت) |
| الثوابت `constexpr` و`inline` | |

## أخطاء شائعة

### خطأ الرابط: undefined reference

إذا صرّحت عن دالة ولم تعرّفها، أو نسيت إضافة ملف `.cpp` إلى المشروع، فالترجمة تنجح لكن **الربط** يفشل:

```text
undefined reference to `mathutils::average(std::vector<double, std::allocator<double> > const&)'
collect2.exe: error: ld returned 1 exit status
```

**المعنى:** «مرجع غير معرّف إلى `mathutils::average`». الرابط (`ld`) لم يجد جسم الدالة في أي ملف. تأكد أن `mathutils.cpp` مضاف إلى المشروع، وأن توقيع الدالة في `.cpp` يطابق التصريح تمامًا (نفس الأنواع و`const` و`&`).

### التعريف المتعدد: multiple definition

إذا كتبت **جسم** دالة عادية داخل ملف `.h` وضمّنته في ملفين `.cpp`، يجد الرابط تعريفين:

```text
multiple definition of `mathutils::isPrime(int)'
```

**الحل:** ضع الجسم في `.cpp` فقط، أو اجعل الدالة `inline` إذا أردت إبقاءها في الترويسة.

### استخدام اسم من فضاء دون تحديده

<!-- compile-error -->
```cpp
namespace tools
{
    int twice(int x) { return x * 2; }
}
int main()
{
    return twice(4);
}
```

```text
main.cpp:7:12: error: 'twice' was not declared in this scope; did you mean 'tools::twice'?
```

**المعنى:** `twice` موجودة داخل `tools` فقط. اكتب `tools::twice(4)` كما يقترح المترجم.

## تمارين

### التمرين 1

أنشئ فضاءين `celsius` و`fahrenheit`، في كل منهما دالة `toKelvin(double)`، واطبع تحويل 100 من كل منهما. (كلفن = سيلزيوس + 273.15، وسيلزيوس = (فهرنهايت - 32) × 5 / 9.)

```cpp exercise
#include <iostream>

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>

namespace celsius
{
    double toKelvin(double c) { return c + 273.15; }
}

namespace fahrenheit
{
    double toKelvin(double f) { return (f - 32) * 5 / 9 + 273.15; }
}

int main()
{
    std::cout << celsius::toKelvin(100) << "\n";
    std::cout << fahrenheit::toKelvin(100) << "\n";
    return 0;
}
```

```text output
373.15
310.928
```

### التمرين 2

حوّل البرنامج التالي إلى فضاء أسماء `shop` يحتوي على `struct Item` ودالة `total`، ثم استخدم اسمًا مختصرًا (alias) في `main`.

```cpp exercise
#include <iostream>
#include <string>
#include <vector>

struct Item
{
    std::string name;
    double price;
    int qty;
};

double total(const std::vector<Item>& items)
{
    double t = 0;
    for (const auto& i : items)
        t += i.price * i.qty;
    return t;
}

int main()
{
    std::vector<Item> cart = {{"Pen", 5, 4}, {"Book", 60, 1}};
    std::cout << total(cart) << "\n";
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>
#include <vector>

namespace shop
{
    struct Item
    {
        std::string name;
        double price;
        int qty;
    };

    double total(const std::vector<Item>& items)
    {
        double t = 0;
        for (const auto& i : items)
            t += i.price * i.qty;
        return t;
    }
}

int main()
{
    namespace s = shop;
    std::vector<s::Item> cart = {{"Pen", 5, 4}, {"Book", 60, 1}};
    std::cout << s::total(cart) << "\n";
    return 0;
}
```

```text output
80
```

## اختبر نفسك

```quiz
{"question": "ما فائدة فضاءات الأسماء؟", "choices": ["تسريع البرنامج", "تمييز الأسماء المتشابهة ومنع تعارضها", "حفظ الملفات", "إخفاء الأخطاء"], "answer": 1, "explanation": "geometry::area وfinance::area دالتان مختلفتان رغم تشابه الاسم."}
```

```quiz
{"question": "ماذا نضع عادة في ملف الترويسة .h؟", "choices": ["الدالة main", "التصريحات وتعريفات الأصناف", "كل الكود دائمًا", "ملفات الصور"], "answer": 1, "explanation": "الترويسة مثل الفهرس: تصريحات، والتعريفات في ملف .cpp."}
```

```quiz
{"question": "ظهر الخطأ undefined reference to ... ld returned 1 exit status. ما السبب الأرجح؟", "choices": ["خطأ إملائي في التعليقات", "الدالة مُصرَّح عنها لكن تعريفها غير موجود أو ملف .cpp غير مضاف", "نسيت return 0", "استخدمت namespace"], "answer": 1, "explanation": "هذا خطأ ربط: الرابط لم يجد جسم الدالة."}
```

```quiz
{"question": "ما وظيفة #pragma once؟", "choices": ["تشغيل البرنامج مرة واحدة", "منع تضمين الترويسة أكثر من مرة في نفس الملف", "تسريع الحلقات", "تعريف main"], "answer": 1, "explanation": "حارس الترويسة يمنع تكرار التصريحات عند التضمين المتعدد."}
```

## الخلاصة

- `namespace` يجمع الأسماء ويمنع التعارض، و`::` للوصول إليها.
- `namespace x = a::b;` اسم مختصر، و`using a::f;` لإدخال اسم واحد.
- الترويسة `.h` للتصريحات، و`.cpp` للتعريفات، و`#pragma once` في أول كل ترويسة.
- الترجمة لكل ملف على حدة ثم الربط؛ و`undefined reference` خطأ ربط.
