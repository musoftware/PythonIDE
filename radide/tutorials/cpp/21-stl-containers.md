# الدرس 21: حاويات المكتبة القياسية (STL Containers)

المكتبة القياسية في C++ (وتسمى غالبًا **STL**: Standard Template Library) تقدم لك مجموعة من **الحاويات** (containers) الجاهزة والمختبرة: أدوات لتخزين البيانات وتنظيمها. عرفنا منها `std::vector`، واليوم نتعرف على أهم الباقي.

> **تشبيه:** الحاويات مثل أدوات التخزين في البيت: **الرف** (`vector`) تضع عليه الأشياء بالترتيب، و**دفتر التليفونات** (`map`) تبحث فيه بالاسم لتجد الرقم، و**صندوق البطاقات الفريدة** (`set`) لا يقبل بطاقة مكررة.

## اختيار الحاوية المناسبة

| الحاوية | الفكرة | مثال استخدام |
|---|---|---|
| `std::vector<T>` | قائمة مرتبة بالفهرس | درجات الطلاب |
| `std::array<T, N>` | قائمة ثابتة الحجم | أيام الأسبوع السبعة |
| `std::map<K, V>` | مفتاح ← قيمة، مرتبة بالمفتاح | اسم الطالب ← درجته |
| `std::unordered_map<K, V>` | مفتاح ← قيمة، أسرع بلا ترتيب | عدّ الكلمات في نص كبير |
| `std::set<T>` | عناصر فريدة مرتبة | قائمة المدن بدون تكرار |
| `std::pair<A, B>` | قيمتان معًا | (الاسم، العمر) |
| `std::queue` / `std::stack` | طابور / كومة | طابور الطباعة / زر التراجع |

## `std::pair`: قيمتان معًا

```cpp run
#include <iostream>
#include <string>
#include <utility>

std::pair<int, int> minMax(int a, int b)
{
    if (a < b)
        return {a, b};
    return {b, a};
}

int main()
{
    std::pair<std::string, int> city{"Aswan", 1500000};
    std::cout << city.first << ": " << city.second << "\n";

    auto [low, high] = minMax(9, 4);   // structured binding
    std::cout << low << " " << high << "\n";
    return 0;
}
```

```text output
Aswan: 1500000
4 9
```

## `std::map`: القاموس

`std::map` يربط كل **مفتاح** (key) بـ **قيمة** (value)، ويبقي المفاتيح مرتبة دائمًا، ولا يسمح بتكرار المفتاح:

```cpp run
#include <iostream>
#include <map>
#include <string>

int main()
{
    std::map<std::string, int> phone;
    phone["Ali"] = 1234;          // إضافة
    phone["Sara"] = 5678;
    phone["Omar"] = 9999;
    phone["Ali"] = 1111;          // تعديل (المفتاح موجود)

    std::cout << "رقم Sara: " << phone["Sara"] << "\n";
    std::cout << "عدد الأسماء: " << phone.size() << "\n";

    // البحث الآمن: هل المفتاح موجود؟
    if (phone.count("Mona") == 0)
        std::cout << "Mona غير موجودة\n";

    auto it = phone.find("Omar");
    if (it != phone.end())
        std::cout << "وجدت " << it->first << ": " << it->second << "\n";

    phone.erase("Omar");          // حذف

    // المرور على الكل (مرتب أبجديًا حسب المفتاح)
    for (const auto& [name, number] : phone)
        std::cout << name << " -> " << number << "\n";
    return 0;
}
```

```text output
رقم Sara: 5678
عدد الأسماء: 3
Mona غير موجودة
وجدت Omar: 9999
Ali -> 1111
Sara -> 5678
```

> **انتبه:** `phone["Mona"]` إذا لم يكن المفتاح موجودًا **يضيفه** بقيمة صفر! للبحث فقط استخدم `find` أو `count` (أو `contains` في C++20).

### مثال كلاسيكي: عدّ التكرارات

```cpp run
#include <iostream>
#include <map>
#include <string>

int main()
{
    std::map<std::string, int> freq;
    std::string word;
    while (std::cin >> word)
        freq[word]++;            // إذا كان جديدًا يبدأ من 0 ثم يزيد

    for (const auto& [w, n] : freq)
        std::cout << w << ": " << n << "\n";
    return 0;
}
```

```text input
تفاح موز تفاح برتقال موز تفاح
```

```text output
برتقال: 1
تفاح: 3
موز: 2
```

ترتيب الكلمات العربية هنا حسب ترتيب الحروف في الترميز، وهو يقارب الترتيب الأبجدي العربي (أ ب ت ث...).

## `std::unordered_map`: أسرع بدون ترتيب

نفس استخدام `map` تمامًا، لكنها تعتمد على **جدول التجزئة** (hash table) فتكون أسرع في البحث مع البيانات الكبيرة، ولا تضمن أي ترتيب عند المرور عليها:

```cpp run
#include <iostream>
#include <string>
#include <unordered_map>

int main()
{
    std::unordered_map<std::string, double> prices = {
        {"tea", 15.5},
        {"coffee", 30},
    };
    prices["juice"] = 25;
    std::cout << "coffee: " << prices["coffee"] << "\n";
    std::cout << "عدد المنتجات: " << prices.size() << "\n";
    return 0;
}
```

```text output
coffee: 30
عدد المنتجات: 3
```

## `std::set`: عناصر فريدة مرتبة

```cpp run
#include <iostream>
#include <set>
#include <string>

int main()
{
    std::set<int> numbers = {5, 1, 9, 1, 5, 3};   // التكرار يُحذف تلقائيًا
    numbers.insert(7);
    numbers.insert(3);                             // موجود: لا يحدث شيء

    for (int n : numbers)
        std::cout << n << " ";
    std::cout << "\nالعدد: " << numbers.size() << "\n";

    std::cout << std::boolalpha;
    std::cout << "9 موجود؟ " << (numbers.count(9) > 0) << "\n";
    std::cout << "4 موجود؟ " << (numbers.count(4) > 0) << "\n";

    std::set<std::string> visited;
    for (std::string c : {"Cairo", "Luxor", "Cairo", "Giza"})
        visited.insert(c);
    std::cout << "مدن زرتها: " << visited.size() << "\n";
    return 0;
}
```

```text output
1 3 5 7 9
العدد: 5
9 موجود؟ true
4 موجود؟ false
مدن زرتها: 3
```

## `std::queue` و`std::stack`

```cpp run
#include <iostream>
#include <queue>
#include <stack>
#include <string>

int main()
{
    std::queue<std::string> line;      // طابور: أول من يدخل أول من يخرج
    line.push("أحمد");
    line.push("بسمة");
    line.push("جمال");
    while (!line.empty())
    {
        std::cout << "دور: " << line.front() << "\n";
        line.pop();
    }

    std::stack<int> undo;              // كومة: آخر من يدخل أول من يخرج
    undo.push(1);
    undo.push(2);
    undo.push(3);
    std::cout << "تراجع عن: " << undo.top() << "\n";
    return 0;
}
```

```text output
دور: أحمد
دور: بسمة
دور: جمال
تراجع عن: 3
```

## المكرِّرات (Iterators): لمحة

كل حاوية تقدم `begin()` و`end()`: **مكرِّرات** (iterators) تعمل مثل مؤشر يتحرك على العناصر. `begin()` يشير إلى أول عنصر، و`end()` يشير إلى ما **بعد** آخر عنصر (لا يُقرأ). الحلقة على المدى `for (x : c)` تستخدمها من وراء الستار، والخوارزميات في الدرس القادم تعتمد عليها:

```cpp
std::vector<int> v = {4, 8, 15};
for (auto it = v.begin(); it != v.end(); ++it)
    std::cout << *it << " ";   // 4 8 15
```

## أخطاء شائعة

### البحث بـ `[]` يضيف عناصر بالخطأ

```cpp
std::map<std::string, int> stock;
if (stock["pen"] == 0)        // أضافت "pen" بقيمة 0!
    std::cout << "غير موجود";
std::cout << stock.size();    // 1 وليس 0
```

استخدم `stock.count("pen")` أو `stock.find("pen") != stock.end()`.

### استخدام `[]` مع map ثابتة

<!-- compile-error -->
```cpp
#include <map>
#include <string>
int get(const std::map<std::string, int>& m)
{
    return m["x"];
}
int main() { return 0; }
```

```text
main.cpp:5:13: error: passing 'const std::map<std::__cxx11::basic_string<char>, int>' as 'this' argument discards qualifiers [-fpermissive]
```

**المعنى:** «تمرير map ثابتة كـ `this` يتجاهل `const`». لأن `[]` قد **تضيف** عنصرًا، فهي غير مسموحة على `const map`. استخدم `m.at("x")` (ترمي استثناءً إذا لم يوجد المفتاح) أو `find`.

## تمارين

### التمرين 1

اقرأ أسماء طلاب ودرجاتهم (حتى نهاية المدخلات) في `std::map<std::string, int>`، ثم اطبعهم مرتبين بالاسم مع المتوسط.

```cpp exercise
#include <iostream>
#include <map>
#include <string>

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <map>
#include <string>

int main()
{
    std::map<std::string, int> grades;
    std::string name;
    int g = 0;
    while (std::cin >> name >> g)
        grades[name] = g;

    double sum = 0;
    for (const auto& [n, grade] : grades)
    {
        std::cout << n << ": " << grade << "\n";
        sum += grade;
    }
    std::cout << "المتوسط: " << sum / grades.size() << "\n";
    return 0;
}
```

```text input
Zeina 90
Adam 70
Mostafa 80
```

```text output
Adam: 70
Mostafa: 80
Zeina: 90
المتوسط: 80
```

### التمرين 2

اقرأ أعدادًا واطبع عدد القيم **المختلفة** بينها، ثم اطبعها مرتبة. استخدم `std::set`.

```cpp exercise
#include <iostream>
#include <set>

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <set>

int main()
{
    std::set<int> unique;
    int x = 0;
    while (std::cin >> x)
        unique.insert(x);
    std::cout << "قيم مختلفة: " << unique.size() << "\n";
    for (int v : unique)
        std::cout << v << " ";
    std::cout << "\n";
    return 0;
}
```

```text input
4 2 4 8 2 2 6
```

```text output
قيم مختلفة: 4
2 4 6 8
```

### التمرين 3

قاموس صغير: خزّن 3 كلمات إنجليزية ومعانيها بالعربية في `std::map`، ثم اقرأ كلمة واطبع معناها أو «غير موجودة».

```cpp exercise
#include <iostream>
#include <map>
#include <string>

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <map>
#include <string>

int main()
{
    std::map<std::string, std::string> dict = {
        {"book", "كتاب"},
        {"pen", "قلم"},
        {"school", "مدرسة"},
    };
    std::string word;
    while (std::cin >> word)
    {
        auto it = dict.find(word);
        if (it != dict.end())
            std::cout << word << " = " << it->second << "\n";
        else
            std::cout << word << ": غير موجودة\n";
    }
    return 0;
}
```

```text input
pen car
```

```text output
pen = قلم
car: غير موجودة
```

## اختبر نفسك

```quiz
{"question": "أي حاوية تناسب تخزين رقم هاتف لكل اسم؟", "choices": ["std::vector<int>", "std::set<std::string>", "std::map<std::string, std::string>", "std::stack<int>"], "answer": 2, "explanation": "map تربط مفتاحًا (الاسم) بقيمة (الرقم)."}
```

```quiz
{"question": "أدخلنا القيم 3، 1، 3، 2 في std::set<int>. ماذا يحتوي؟", "choices": ["3 1 3 2", "1 2 3", "3 1 2", "1 2 3 3"], "answer": 1, "explanation": "set يحذف التكرار ويرتب العناصر."}
```

```quiz
{"question": "ماذا يحدث عند قراءة m[\"x\"] من map ليس فيها x؟", "choices": ["خطأ ترجمة", "يُضاف المفتاح x بقيمة افتراضية", "ينهار البرنامج", "يُرجع -1"], "answer": 1, "explanation": "العامل [] يضيف المفتاح إذا لم يكن موجودًا؛ استخدم find أو count للبحث فقط."}
```

```quiz
{"question": "طابور الطباعة: أول ملف يُرسل يُطبع أولًا. أي حاوية تناسبه؟", "choices": ["std::stack", "std::queue", "std::set", "std::map"], "answer": 1, "explanation": "queue تعمل بمبدأ أول من يدخل أول من يخرج (FIFO)."}
```

## الخلاصة

- `pair` لقيمتين، و`map`/`unordered_map` للمفتاح والقيمة، و`set` للعناصر الفريدة.
- `queue` (FIFO) و`stack` (LIFO).
- ابحث في `map` بـ `find` أو `count`، لا بـ `[]`.
- المكرِّرات `begin()`/`end()` أساس الخوارزميات.
