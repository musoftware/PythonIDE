# الدرس 10: المصفوفات و`std::vector`

لو أردت حفظ درجات 30 طالبًا، هل ستعرّف 30 متغيرًا `grade1` و`grade2` و...؟ بالطبع لا. نستخدم **مجموعة** واحدة تحمل كل القيم: المصفوفة أو `std::vector`.

> **تشبيه:** المصفوفة مثل **صف خزائن** في المدرسة، كل خزانة لها رقم يبدأ من **صفر**، وكلها من نفس النوع.

## المصفوفة التقليدية (C-style array)

```cpp
int grades[5] = {90, 75, 88, 60, 95};
```

- `5` حجم المصفوفة، وهو **ثابت** لا يتغير.
- نصل إلى العنصر بـ **الفهرس** (index) بين قوسين مربعين: `grades[0]` هو الأول، و`grades[4]` هو الأخير.

```cpp run
#include <iostream>

int main()
{
    int grades[5] = {90, 75, 88, 60, 95};

    std::cout << "الأول: " << grades[0] << "\n";
    std::cout << "الأخير: " << grades[4] << "\n";

    grades[1] = 80;   // تعديل عنصر

    int sum = 0;
    for (int i = 0; i < 5; i++)
        sum += grades[i];
    std::cout << "المجموع: " << sum << "\n";
    return 0;
}
```

```text output
الأول: 90
الأخير: 95
المجموع: 413
```

المصفوفات التقليدية موروثة من لغة C، ولها عيوب: حجمها ثابت، ولا تعرف حجمها بنفسها، ولا تحميك إذا تجاوزت حدودها. لذلك في C++ الحديثة نفضّل **`std::vector`**.

## `std::vector`: المصفوفة الذكية

`std::vector` مصفوفة **مرنة** تكبر وتصغر حسب الحاجة، وتعرف حجمها. نحتاج `#include <vector>`:

```cpp run
#include <iostream>
#include <vector>

int main()
{
    std::vector<int> numbers = {10, 20, 30};

    numbers.push_back(40);    // أضف في النهاية
    numbers.push_back(50);

    std::cout << "العدد: " << numbers.size() << "\n";
    std::cout << "الأول: " << numbers.front() << "، الأخير: " << numbers.back() << "\n";

    numbers.pop_back();       // احذف الأخير
    numbers[0] = 99;          // عدّل الأول

    for (std::size_t i = 0; i < numbers.size(); i++)
        std::cout << numbers[i] << " ";
    std::cout << "\n";
    return 0;
}
```

```text output
العدد: 5
الأول: 10، الأخير: 50
99 20 30 40
```

- `std::vector<int>` تعني «vector عناصره من نوع `int`». الأقواس `< >` تحدد نوع العناصر.
- `size()` تُرجع العدد بنوع `std::size_t` (عدد صحيح بدون إشارة)، لذلك استخدمناه في العداد `i`.

### أهم دوال `std::vector`

| الدالة | وظيفتها |
|---|---|
| `push_back(x)` | إضافة `x` في النهاية |
| `pop_back()` | حذف آخر عنصر |
| `size()` | عدد العناصر |
| `empty()` | هل هو فارغ؟ |
| `front()` / `back()` | أول / آخر عنصر |
| `clear()` | حذف كل العناصر |
| `at(i)` | العنصر `i` مع فحص الحدود |

## حلقة `for` على المدى (range-based for)

طريقة أسهل وأوضح للمرور على كل العناصر، بدون فهرس:

```cpp run
#include <iostream>
#include <string>
#include <vector>

int main()
{
    std::vector<std::string> fruits = {"تفاح", "موز", "برتقال"};

    for (const std::string& f : fruits)   // لكل f في fruits
        std::cout << "- " << f << "\n";

    std::vector<double> prices = {10, 20, 30};
    for (double& p : prices)   // & لكي نعدّل العناصر الأصلية
        p *= 1.1;
    for (double p : prices)
        std::cout << p << " ";
    std::cout << "\n";
    return 0;
}
```

```text output
- تفاح
- موز
- برتقال
11 22 33
```

اقرأها هكذا: «لكل `f` في `fruits` افعل...». بدون `&` تعمل الحلقة على **نسخة** من كل عنصر، ومع `&` تعمل على العنصر نفسه.

## ملء `std::vector` من المدخلات

```cpp run
#include <iostream>
#include <vector>

int main()
{
    int n = 0;
    std::cin >> n;
    std::vector<int> marks;
    for (int i = 0; i < n; i++)
    {
        int m = 0;
        std::cin >> m;
        marks.push_back(m);
    }

    int best = marks[0];
    double sum = 0;
    for (int m : marks)
    {
        sum += m;
        if (m > best)
            best = m;
    }
    std::cout << "أعلى درجة: " << best << "\n";
    std::cout << "المتوسط: " << sum / marks.size() << "\n";
    return 0;
}
```

```text input
4
70 85 90 75
```

```text output
أعلى درجة: 90
المتوسط: 80
```

## إنشاء vector بحجم وقيمة ابتدائية

```cpp
std::vector<int> zeros(10);        // 10 عناصر قيمتها 0
std::vector<char> stars(5, '*');   // 5 عناصر قيمتها '*'
```

> **انتبه:** `std::vector<int> v(3);` تعني «3 أصفار»، أما `std::vector<int> v{3};` فتعني «عنصر واحد قيمته 3».

## المصفوفات ثنائية الأبعاد

جدول له صفوف وأعمدة: vector داخل vector:

```cpp run
#include <iostream>
#include <vector>

int main()
{
    std::vector<std::vector<int>> table = {
        {1, 2, 3},
        {4, 5, 6},
    };
    for (const auto& row : table)
    {
        for (int cell : row)
            std::cout << cell << "\t";
        std::cout << "\n";
    }
    std::cout << "الصف 1، العمود 2: " << table[1][2] << "\n";
    return 0;
}
```

```text output
1	2	3
4	5	6
الصف 1، العمود 2: 6
```

## تمرير vector إلى دالة

مرره بـ `const&` للقراءة، وبـ `&` للتعديل (تذكّر الدرس السابق):

```cpp run
#include <iostream>
#include <vector>

double average(const std::vector<double>& values)
{
    if (values.empty())
        return 0;
    double sum = 0;
    for (double v : values)
        sum += v;
    return sum / values.size();
}

void addPoint(std::vector<double>& values, double v)
{
    values.push_back(v);
}

int main()
{
    std::vector<double> temps = {30, 32, 34};
    addPoint(temps, 36);
    std::cout << "عدد القراءات: " << temps.size() << "\n";
    std::cout << "متوسط الحرارة: " << average(temps) << "\n";
    return 0;
}
```

```text output
عدد القراءات: 4
متوسط الحرارة: 33
```

## أخطاء شائعة

### الخروج عن حدود المصفوفة

إذا كان في `std::vector` خمسة عناصر، فالفهارس من `0` إلى `4`. الوصول إلى `v[5]` **سلوك غير معرّف** (undefined behavior): قد يطبع رقمًا عشوائيًا، أو ينهار البرنامج. استخدم `at()` لكي تحصل على خطأ واضح:

```cpp run
#include <iostream>
#include <vector>

int main()
{
    std::vector<int> v = {1, 2, 3};
    try
    {
        std::cout << v.at(5) << "\n";
    }
    catch (const std::out_of_range& e)
    {
        std::cout << "خطأ: الفهرس خارج الحدود\n";
    }
    return 0;
}
```

```text output
خطأ: الفهرس خارج الحدود
```

سنتعلم `try` و`catch` في درس الاستثناءات.

### مقارنة `int` مع `size()`

<!-- compile-error -->
```cpp
#include <vector>
int main()
{
    std::vector<int> v{1, 2};
    int c = 0;
    for (int i = 0; i < v.size(); i++)
        c++;
    return c;
}
```

```text
main.cpp:6:23: warning: comparison of integer expressions of different signedness: 'int' and 'std::vector<int>::size_type' {aka 'long long unsigned int'} [-Wsign-compare]
```

**المعنى:** «مقارنة بين عددين صحيحين مختلفين في الإشارة». `i` من نوع `int` (له إشارة) و`size()` بدون إشارة. الحل: `std::size_t i` أو حلقة على المدى.

## تمارين

### التمرين 1

اقرأ 5 أعداد في `std::vector<int>` ثم اطبعها بترتيب معكوس.

```cpp exercise
#include <iostream>
#include <vector>

int main()
{
    // اقرأ 5 أعداد ثم اطبعها من الأخير للأول
    return 0;
}
```

```cpp solution
#include <iostream>
#include <vector>

int main()
{
    std::vector<int> v;
    for (int i = 0; i < 5; i++)
    {
        int x = 0;
        std::cin >> x;
        v.push_back(x);
    }
    for (int i = static_cast<int>(v.size()) - 1; i >= 0; i--)
        std::cout << v[i] << " ";
    std::cout << "\n";
    return 0;
}
```

```text input
1 2 3 4 5
```

```text output
5 4 3 2 1
```

### التمرين 2

اكتب دالة `int countAbove(const std::vector<int>& v, int limit)` تُرجع عدد العناصر الأكبر من `limit`.

```cpp exercise
#include <iostream>
#include <vector>

int main()
{
    std::vector<int> grades = {45, 80, 92, 50, 67, 99};
    // اطبع عدد الدرجات الأكبر من 60
    return 0;
}
```

```cpp solution
#include <iostream>
#include <vector>

int countAbove(const std::vector<int>& v, int limit)
{
    int count = 0;
    for (int x : v)
        if (x > limit)
            count++;
    return count;
}

int main()
{
    std::vector<int> grades = {45, 80, 92, 50, 67, 99};
    std::cout << "عدد الناجحين: " << countAbove(grades, 60) << "\n";
    return 0;
}
```

```text output
عدد الناجحين: 4
```

### التمرين 3

اطبع جدول الضرب من 1 إلى 4 بعد تخزينه في vector ثنائي الأبعاد.

```cpp exercise
#include <iostream>
#include <vector>

int main()
{
    std::vector<std::vector<int>> t(4, std::vector<int>(4));
    // املأ t[i][j] = (i + 1) * (j + 1) ثم اطبعه
    return 0;
}
```

```cpp solution
#include <iostream>
#include <vector>

int main()
{
    std::vector<std::vector<int>> t(4, std::vector<int>(4));
    for (int i = 0; i < 4; i++)
        for (int j = 0; j < 4; j++)
            t[i][j] = (i + 1) * (j + 1);

    for (const auto& row : t)
    {
        for (int x : row)
            std::cout << x << "\t";
        std::cout << "\n";
    }
    return 0;
}
```

```text output
1	2	3	4
2	4	6	8
3	6	9	12
4	8	12	16
```

## اختبر نفسك

```quiz
{"question": "ما فهرس أول عنصر في المصفوفة؟", "choices": ["1", "0", "-1", "حسب الحجم"], "answer": 1, "explanation": "الفهارس في C++ تبدأ من صفر."}
```

```quiz
{"question": "vector فيه 4 عناصر. ما آخر فهرس صحيح؟", "choices": ["4", "3", "5", "0"], "answer": 1, "explanation": "الفهارس من 0 إلى size() - 1، أي من 0 إلى 3."}
```

```quiz
{"question": "أي دالة تضيف عنصرًا في نهاية std::vector؟", "choices": ["add()", "insert_end()", "push_back()", "append()"], "answer": 2, "explanation": "push_back تضيف العنصر في النهاية وتزيد الحجم بواحد."}
```

```quiz
{"question": "لماذا نكتب for (double& p : prices) بدل for (double p : prices)؟", "choices": ["لأنها أسرع في الطباعة", "لكي نعدّل العناصر الأصلية داخل الحلقة", "لأن double يحتاج & دائمًا", "لا فرق"], "answer": 1, "explanation": "بدون & يكون p نسخة، فالتعديل عليها لا يؤثر في الـ vector."}
```

## الخلاصة

- المصفوفة مجموعة عناصر من نوع واحد، والفهارس تبدأ من 0.
- فضّل `std::vector`: مرنة، وتعرف حجمها، و`push_back` و`size` و`at`.
- `for (const auto& x : v)` أسهل طريقة للمرور على العناصر.
- لا تخرج عن الحدود، و`at()` تفحصها لك.
