# الدرس 20: القوالب (Templates)

تخيّل أنك كتبت دالة `maxInt(int, int)`، ثم احتجت `maxDouble(double, double)`، ثم `maxString`... نفس الكود بالضبط مع تغيير النوع فقط! **القوالب** (Templates) تسمح لك بكتابة الكود **مرة واحدة** لأي نوع، والمترجم يصنع النسخة المناسبة بنفسه.

> **تشبيه:** القالب مثل **قالب الطوب**: تصب فيه طينًا فيخرج طوب من طين، أو إسمنتًا فيخرج طوب إسمنتي. الشكل واحد، والمادة تختلف.

وأنت في الحقيقة تستخدم القوالب منذ دروس: `std::vector<int>` و`std::vector<std::string>` و`std::unique_ptr<Box>` كلها قوالب!

## قالب الدالة (Function Template)

```cpp run
#include <iostream>
#include <string>

template <typename T>
T biggest(T a, T b)
{
    return (a > b) ? a : b;
}

int main()
{
    std::cout << biggest(3, 9) << "\n";                    // T = int
    std::cout << biggest(2.5, 1.5) << "\n";                // T = double
    std::cout << biggest<std::string>("tea", "coffee") << "\n";  // T = std::string
    std::cout << biggest('a', 'z') << "\n";                // T = char
    return 0;
}
```

```text output
9
2.5
tea
z
```

- `template <typename T>` تعني «ما يلي قالب، و`T` اسم لنوع سيُحدد لاحقًا».
- عند الاستدعاء `biggest(3, 9)` يستنتج المترجم أن `T = int` ويصنع نسخة لها.
- يمكن تحديد النوع صراحة بين `< >` كما فعلنا مع `std::string` (لأن `"tea"` وحدها نص C قديم).
- `"tea" > "coffee"` لأن المقارنة أبجدية: `t` بعد `c`.

## قالب بأكثر من نوع

```cpp run
#include <iostream>
#include <string>
#include <vector>

template <typename K, typename V>
void printPair(const K& key, const V& value)
{
    std::cout << key << " => " << value << "\n";
}

template <typename T>
T sumAll(const std::vector<T>& items)
{
    T total{};          // قيمة صفرية لأي نوع
    for (const T& x : items)
        total += x;
    return total;
}

int main()
{
    printPair("العمر", 30);
    printPair(1, 2.5);
    printPair(std::string("Pi"), 3.14);

    std::vector<int> a = {1, 2, 3};
    std::vector<double> b = {0.5, 0.25};
    std::vector<std::string> c = {"C", "+", "+"};
    std::cout << sumAll(a) << " " << sumAll(b) << " " << sumAll(c) << "\n";
    return 0;
}
```

```text output
العمر => 30
1 => 2.5
Pi => 3.14
6 0.75 C++
```

لاحظ كيف عملت `sumAll` حتى مع النصوص، لأن `std::string` يدعم `+=`. القالب يعمل مع أي نوع يدعم العمليات المستخدمة بداخله.

## قالب الصنف (Class Template)

```cpp run
#include <iostream>
#include <string>
#include <vector>

template <typename T>
class Stack
{
private:
    std::vector<T> items;

public:
    void push(const T& item) { items.push_back(item); }
    void pop() { items.pop_back(); }
    const T& top() const { return items.back(); }
    bool empty() const { return items.empty(); }
    std::size_t size() const { return items.size(); }
};

int main()
{
    Stack<int> numbers;
    numbers.push(10);
    numbers.push(20);
    numbers.push(30);
    std::cout << "الأعلى: " << numbers.top() << "، العدد: " << numbers.size() << "\n";

    Stack<std::string> history;
    history.push("الصفحة الرئيسية");
    history.push("الأخبار");
    history.push("الرياضة");
    while (!history.empty())
    {
        std::cout << "رجوع من: " << history.top() << "\n";
        history.pop();
    }
    return 0;
}
```

```text output
الأعلى: 30، العدد: 3
رجوع من: الرياضة
رجوع من: الأخبار
رجوع من: الصفحة الرئيسية
```

> **تشبيه:** المكدّس (Stack) مثل كومة الأطباق: تضع الطبق في الأعلى، وتأخذ من الأعلى. آخر من يدخل أول من يخرج (LIFO).

## قيم في القالب (non-type parameters)

يمكن أن يكون معامل القالب **قيمة** ثابتة لا نوعًا:

```cpp run
#include <iostream>

template <typename T, int N>
class FixedArray
{
    T data[N] = {};

public:
    int size() const { return N; }
    T& operator[](int i) { return data[i]; }
};

int main()
{
    FixedArray<double, 3> scores;
    scores[0] = 9.5;
    scores[2] = 7;
    for (int i = 0; i < scores.size(); i++)
        std::cout << scores[i] << " ";
    std::cout << "\n";
    return 0;
}
```

```text output
9.5 0 7
```

وهكذا بالضبط تعمل `std::array<double, 3>` في المكتبة القياسية.

## المفاهيم (Concepts) في C++20: لمحة

في C++20 يمكنك تقييد القالب بأنواع معينة، فتصبح رسائل الخطأ أوضح بكثير:

```cpp
#include <concepts>

template <std::integral T>      // T يجب أن يكون عددًا صحيحًا
T half(T x) { return x / 2; }

// half(10) يعمل، أما half(2.5) فيعطي خطأ واضحًا: القيد غير متحقق
```

هذه الميزة تحتاج المعيار C++20، وهي موضوع متقدم يمكنك العودة إليه لاحقًا.

## أخطاء شائعة

### أنواع مختلفة لنفس المعامل `T`

<!-- compile-error -->
```cpp
template <typename T>
T add(T a, T b) { return a + b; }
int main()
{
    add(1, 2.5);
    return 0;
}
```

```text
main.cpp:5:8: error: no matching function for call to 'add(int, double)'
```

**المعنى:** «لا توجد دالة مطابقة لـ `add(int, double)`». القالب يقول إن المعاملين من **نفس** النوع `T`، لكنك أعطيته `int` و`double` فلم يعرف ماذا يختار. الحل: `add<double>(1, 2.5)` أو `add(1.0, 2.5)`.

### نوع لا يدعم العملية المطلوبة

إذا استدعيت `biggest` على صنف ليس له `operator>`، ستظهر رسالة طويلة جدًا تبدأ بـ `no match for 'operator>'` وفيها كلمات مثل `required from here`. ابحث عن السطر الذي فيه `required from here` لتعرف أين استدعيت القالب، ثم أضف العامل الناقص لصنفك.

## تمارين

### التمرين 1

اكتب قالب دالة `void swapValues(T& a, T& b)` يبدّل قيمتين من أي نوع، وجرّبه مع `int` و`std::string`.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

template <typename T>
void swapValues(T& a, T& b)
{
    T temp = a;
    a = b;
    b = temp;
}

int main()
{
    int x = 1, y = 2;
    swapValues(x, y);
    std::string s = "أول", t = "ثاني";
    swapValues(s, t);
    std::cout << x << " " << y << "\n" << s << " " << t << "\n";
    return 0;
}
```

```text output
2 1
ثاني أول
```

### التمرين 2

اكتب قالب دالة `int countEqual(const std::vector<T>& v, const T& value)` يعدّ مرات ظهور قيمة.

```cpp exercise
#include <iostream>
#include <string>
#include <vector>

int main()
{
    std::vector<int> nums = {1, 3, 1, 1, 5};
    std::vector<std::string> words = {"yes", "no", "yes"};
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>
#include <vector>

template <typename T>
int countEqual(const std::vector<T>& v, const T& value)
{
    int count = 0;
    for (const T& x : v)
        if (x == value)
            count++;
    return count;
}

int main()
{
    std::vector<int> nums = {1, 3, 1, 1, 5};
    std::vector<std::string> words = {"yes", "no", "yes"};
    std::cout << countEqual(nums, 1) << "\n";
    std::cout << countEqual(words, std::string("yes")) << "\n";
    return 0;
}
```

```text output
3
2
```

### التمرين 3

اكتب قالب صنف `Pair<A, B>` فيه عضوان `first` و`second` ودالة `print()`، وأنشئ زوجًا (اسم، درجة).

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    // Pair<std::string, int> p{"Laila", 97}; p.print();
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

template <typename A, typename B>
struct Pair
{
    A first;
    B second;
    void print() const { std::cout << first << ": " << second << "\n"; }
};

int main()
{
    Pair<std::string, int> p{"Laila", 97};
    p.print();
    Pair<char, double> q{'x', 1.5};
    q.print();
    return 0;
}
```

```text output
Laila: 97
x: 1.5
```

## اختبر نفسك

```quiz
{"question": "ما فائدة القوالب؟", "choices": ["تسريع الترجمة", "كتابة كود واحد يعمل مع أنواع مختلفة", "إخفاء البيانات", "التعامل مع الملفات"], "answer": 1, "explanation": "القالب يُكتب مرة، والمترجم يولّد نسخة لكل نوع مستخدم."}
```

```quiz
{"question": "في template <typename T>، ما هو T؟", "choices": ["متغير عدد صحيح", "اسم مؤقت لنوع يُحدد عند الاستخدام", "كلمة محجوزة تعني text", "دالة"], "answer": 1, "explanation": "T معامل نوع، يُستبدل بالنوع الفعلي مثل int أو std::string."}
```

```quiz
{"question": "لماذا يفشل add(1, 2.5) مع template <typename T> T add(T a, T b)؟", "choices": ["لأن القوالب لا تقبل الأعداد", "لأن المعاملين يجب أن يكونا من نفس النوع T", "لأن 2.5 كبير جدًا", "لا يفشل"], "answer": 1, "explanation": "المترجم استنتج int من الأول وdouble من الثاني فتعارض الاستنتاج."}
```

```quiz
{"question": "أي مما يلي مثال على قالب صنف من المكتبة القياسية؟", "choices": ["std::cout", "std::vector<int>", "main", "return"], "answer": 1, "explanation": "std::vector قالب صنف، و<int> يحدد نوع العناصر."}
```

## الخلاصة

- `template <typename T>` لكتابة دوال وأصناف عامة.
- المترجم يستنتج `T` من الوسائط، أو تحدده صراحة `f<double>(...)`.
- قوالب الأصناف مثل `Stack<T>` و`std::vector<T>`.
- معاملات القالب قد تكون قيمًا مثل `int N`.
- C++20 تضيف المفاهيم (concepts) لتقييد الأنواع.
