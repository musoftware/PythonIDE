# الدرس 22: الخوارزميات ودوال لامدا (Algorithms and Lambdas)

كم مرة كتبنا حلقة لنبحث عن عنصر، أو لنعدّ، أو لنجد الأكبر؟ المكتبة `<algorithm>` فيها عشرات **الخوارزميات** الجاهزة والسريعة والمختبرة لهذه المهام. ومعها **دوال لامدا** (lambdas): دوال صغيرة نكتبها في مكانها مباشرة.

> **تشبيه:** الخوارزميات مثل **أجهزة المطبخ**: بدل أن تعجن بيدك كل مرة، تستخدم العجانة. ودالة لامدا مثل **الوصفة الصغيرة** التي تعطيها للجهاز: «اخلط ببطء»، «قطّع شرائح رفيعة».

## الترتيب `std::sort`

```cpp run
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

int main()
{
    std::vector<int> nums = {42, 7, 19, 3, 25};
    std::sort(nums.begin(), nums.end());            // تصاعدي
    for (int n : nums)
        std::cout << n << " ";
    std::cout << "\n";

    std::sort(nums.begin(), nums.end(), std::greater<int>());   // تنازلي
    for (int n : nums)
        std::cout << n << " ";
    std::cout << "\n";

    std::vector<std::string> names = {"Sara", "Adam", "Mona", "Basel"};
    std::sort(names.begin(), names.end());
    for (const auto& s : names)
        std::cout << s << " ";
    std::cout << "\n";
    return 0;
}
```

```text output
3 7 19 25 42
42 25 19 7 3
Adam Basel Mona Sara
```

كل الخوارزميات تأخذ **مدى** (range) يحدده مكرِّران: `begin()` و`end()`، أي «من أول عنصر إلى النهاية».

## دوال لامدا

لامدا دالة بلا اسم تُكتب في مكانها:

```cpp
[](int a, int b) { return a > b; }
```

- `[]` **قائمة الالتقاط** (capture): أي متغيرات من الخارج تريد استخدامها بالداخل.
- `(int a, int b)` المعاملات.
- `{ ... }` الجسم.

```cpp run
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

struct Student
{
    std::string name;
    int grade;
};

int main()
{
    auto square = [](int x) { return x * x; };   // لامدا في متغير
    std::cout << "square(6) = " << square(6) << "\n";

    std::vector<Student> cls = {{"Hana", 85}, {"Ziad", 92}, {"Lina", 78}, {"Fady", 92}};

    // ترتيب حسب الدرجة تنازليًا، وعند التساوي حسب الاسم
    std::sort(cls.begin(), cls.end(), [](const Student& a, const Student& b) {
        if (a.grade != b.grade)
            return a.grade > b.grade;
        return a.name < b.name;
    });
    for (const auto& s : cls)
        std::cout << s.name << " " << s.grade << "\n";
    return 0;
}
```

```text output
square(6) = 36
Fady 92
Ziad 92
Hana 85
Lina 78
```

## الالتقاط (Capture)

اللامدا لا ترى المتغيرات المحلية الخارجية إلا إذا «التقطتها»:

| الصيغة | المعنى |
|---|---|
| `[]` | لا تلتقط شيئًا |
| `[limit]` | التقط نسخة من `limit` |
| `[&total]` | التقط `total` بالمرجع (يمكن تعديله) |
| `[=]` | التقط كل ما تستخدمه بالنسخ |
| `[&]` | التقط كل ما تستخدمه بالمرجع |

```cpp run
#include <algorithm>
#include <iostream>
#include <vector>

int main()
{
    std::vector<int> grades = {45, 80, 92, 50, 67, 99, 30};
    int passMark = 50;

    long passed = std::count_if(grades.begin(), grades.end(),
                                [passMark](int g) { return g >= passMark; });
    std::cout << "الناجحون: " << passed << "\n";

    int total = 0;
    std::for_each(grades.begin(), grades.end(), [&total](int g) { total += g; });
    std::cout << "المجموع: " << total << "\n";
    return 0;
}
```

```text output
الناجحون: 5
المجموع: 463
```

## أشهر الخوارزميات

```cpp run
#include <algorithm>
#include <iostream>
#include <numeric>
#include <vector>

int main()
{
    std::vector<int> v = {4, 8, 15, 16, 23, 42};

    // البحث عن قيمة
    auto it = std::find(v.begin(), v.end(), 16);
    if (it != v.end())
        std::cout << "16 في الموقع " << (it - v.begin()) << "\n";

    // البحث بشرط: أول عدد فردي
    auto odd = std::find_if(v.begin(), v.end(), [](int x) { return x % 2 != 0; });
    std::cout << "أول عدد فردي: " << *odd << "\n";

    // الأكبر والأصغر
    std::cout << "الأكبر: " << *std::max_element(v.begin(), v.end()) << "\n";
    std::cout << "الأصغر: " << *std::min_element(v.begin(), v.end()) << "\n";

    // المجموع (من <numeric>)
    std::cout << "المجموع: " << std::accumulate(v.begin(), v.end(), 0) << "\n";

    // هل كل العناصر موجبة؟ هل يوجد عنصر أكبر من 40؟
    std::cout << std::boolalpha;
    std::cout << "كلها موجبة؟ " << std::all_of(v.begin(), v.end(), [](int x) { return x > 0; }) << "\n";
    std::cout << "يوجد > 40؟ " << std::any_of(v.begin(), v.end(), [](int x) { return x > 40; }) << "\n";

    // العكس
    std::reverse(v.begin(), v.end());
    for (int x : v)
        std::cout << x << " ";
    std::cout << "\n";
    return 0;
}
```

```text output
16 في الموقع 3
أول عدد فردي: 15
الأكبر: 42
الأصغر: 4
المجموع: 108
كلها موجبة؟ true
يوجد > 40؟ true
42 23 16 15 8 4
```

## التحويل والحذف بشرط

```cpp run
#include <algorithm>
#include <iostream>
#include <vector>

int main()
{
    std::vector<double> prices = {100, 250, 80};
    // أضف ضريبة 14% لكل سعر
    std::transform(prices.begin(), prices.end(), prices.begin(),
                   [](double p) { return p * 1.14; });
    for (double p : prices)
        std::cout << p << " ";
    std::cout << "\n";

    std::vector<int> nums = {1, -2, 3, -4, 5, -6};
    // احذف كل الأعداد السالبة (نمط erase-remove)
    nums.erase(std::remove_if(nums.begin(), nums.end(), [](int x) { return x < 0; }), nums.end());
    for (int x : nums)
        std::cout << x << " ";
    std::cout << "\n";
    return 0;
}
```

```text output
114 285 91.2
1 3 5
```

`std::remove_if` لا تحذف فعليًا، بل تنقل العناصر المطلوبة إلى البداية وتُرجع موقع النهاية الجديدة، ثم `erase` تحذف الباقي. في C++20 يمكنك كتابة `std::erase_if(nums, شرط);` في سطر واحد.

## لمحة عن النطاقات (Ranges) في C++20

C++20 تسمح بتمرير الحاوية كلها بدلًا من `begin()` و`end()`:

```cpp
#include <ranges>
std::ranges::sort(nums);                               // بدل std::sort(nums.begin(), nums.end())
auto it = std::ranges::find(nums, 16);
```

هذه الصيغة تحتاج المعيار C++20.

## أخطاء شائعة

### استخدام متغير خارجي بدون التقاطه

<!-- compile-error -->
```cpp
#include <algorithm>
#include <vector>
int main()
{
    std::vector<int> v{3, 1};
    int k = 2;
    auto f = [](int x) { return x > k; };
    return (int)std::count_if(v.begin(), v.end(), f);
}
```

```text
main.cpp:7:37: error: 'k' is not captured
```

**المعنى:** «`k` غير ملتقط». اللامدا لا ترى `k` لأنك لم تضعه بين `[]`. الحل: `[k](int x) { return x > k; }`.

### استخدام نتيجة `find` دون فحصها

إذا لم تجد `std::find` القيمة فهي تُرجع `end()`، و`*end()` سلوك غير معرّف (غالبًا انهيار). افحص دائمًا: `if (it != v.end())`.

### دالة مقارنة خاطئة في `sort`

دالة المقارنة يجب أن تُرجع `true` إذا كان الأول **قبل** الثاني بشكل صارم. استخدام `<=` بدل `<` قد يسبب انهيار البرنامج مع بعض البيانات!

## تمارين

### التمرين 1

اقرأ أعدادًا حتى نهاية المدخلات، ثم اطبعها مرتبة تنازليًا باستخدام `std::sort` ولامدا.

```cpp exercise
#include <algorithm>
#include <iostream>
#include <vector>

int main()
{
    return 0;
}
```

```cpp solution
#include <algorithm>
#include <iostream>
#include <vector>

int main()
{
    std::vector<int> v;
    int x = 0;
    while (std::cin >> x)
        v.push_back(x);
    std::sort(v.begin(), v.end(), [](int a, int b) { return a > b; });
    for (int n : v)
        std::cout << n << " ";
    std::cout << "\n";
    return 0;
}
```

```text input
5 12 1 8 30
```

```text output
30 12 8 5 1
```

### التمرين 2

لديك قائمة كلمات. اطبع عدد الكلمات التي طولها أكبر من حد معين `minLen` يقرؤه البرنامج، باستخدام `std::count_if` ولامدا تلتقط `minLen`.

```cpp exercise
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

int main()
{
    std::vector<std::string> words = {"cpp", "lambda", "vector", "map", "algorithm"};
    std::size_t minLen = 0;
    std::cin >> minLen;
    return 0;
}
```

```cpp solution
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

int main()
{
    std::vector<std::string> words = {"cpp", "lambda", "vector", "map", "algorithm"};
    std::size_t minLen = 0;
    std::cin >> minLen;
    auto n = std::count_if(words.begin(), words.end(),
                           [minLen](const std::string& w) { return w.size() > minLen; });
    std::cout << n << "\n";
    return 0;
}
```

```text input
5
```

```text output
3
```

### التمرين 3

لديك `std::vector<Product>` (الاسم والسعر). رتّبها حسب السعر تصاعديًا، واطبع أغلى منتج باستخدام `std::max_element`.

```cpp exercise
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

struct Product
{
    std::string name;
    double price;
};

int main()
{
    std::vector<Product> items = {{"Phone", 8000}, {"Cable", 150}, {"Laptop", 22000}, {"Case", 300}};
    return 0;
}
```

```cpp solution
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

struct Product
{
    std::string name;
    double price;
};

int main()
{
    std::vector<Product> items = {{"Phone", 8000}, {"Cable", 150}, {"Laptop", 22000}, {"Case", 300}};
    auto byPrice = [](const Product& a, const Product& b) { return a.price < b.price; };

    std::sort(items.begin(), items.end(), byPrice);
    for (const auto& p : items)
        std::cout << p.name << " " << p.price << "\n";

    auto top = std::max_element(items.begin(), items.end(), byPrice);
    std::cout << "الأغلى: " << top->name << "\n";
    return 0;
}
```

```text output
Cable 150
Case 300
Phone 8000
Laptop 22000
الأغلى: Laptop
```

## اختبر نفسك

```quiz
{"question": "ماذا تُرجع std::find إذا لم تجد العنصر؟", "choices": ["nullptr", "-1", "end() للمدى", "0"], "answer": 2, "explanation": "تُرجع مكرِّر النهاية end()، فقارن به قبل استخدام النتيجة."}
```

```quiz
{"question": "في اللامدا [&total](int x) { total += x; }، ماذا يعني &total؟", "choices": ["نسخة من total", "التقاط total بالمرجع للتعديل عليه", "عنوان total في الذاكرة للطباعة", "خطأ ترجمة"], "answer": 1, "explanation": "& في قائمة الالتقاط تعني بالمرجع، فالتعديل يظهر خارج اللامدا."}
```

```quiz
{"question": "أي خوارزمية تعدّ العناصر التي تحقق شرطًا؟", "choices": ["std::find_if", "std::count_if", "std::sort", "std::accumulate"], "answer": 1, "explanation": "count_if تعدّ العناصر التي تُرجع اللامدا لها true."}
```

```quiz
{"question": "ما ناتج std::accumulate(v.begin(), v.end(), 0) للقائمة {1, 2, 3}؟", "choices": ["0", "3", "6", "123"], "answer": 2, "explanation": "accumulate تجمع العناصر بدءًا من القيمة الابتدائية 0."}
```

## الخلاصة

- `<algorithm>`: `sort` و`find` و`find_if` و`count_if` و`max_element` و`transform` و`remove_if`...
- `<numeric>`: `accumulate`.
- اللامدا `[التقاط](معاملات) { جسم }` دالة صغيرة في مكانها.
- `[x]` نسخة، و`[&x]` مرجع، وافحص نتيجة `find` قبل استخدامها.
