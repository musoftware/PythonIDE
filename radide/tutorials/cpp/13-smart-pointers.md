# الدرس 13: المؤشرات الذكية (Smart Pointers)

في الدرس السابق رأينا أن `new` و`delete` قويان لكنهما خطيران: لو نسيت `delete` تسرّبت الذاكرة، ولو كررته انهار البرنامج. الحل في C++ الحديثة هو **المؤشرات الذكية** من المكتبة `<memory>`: مؤشرات **تحذف الذاكرة بنفسها** في الوقت المناسب.

> **تشبيه:** المؤشر العادي مثل مفتاح مخزن مستأجر عليك أن تتذكر إعادته. المؤشر الذكي مثل **مفتاح فندق إلكتروني**: يتوقف تلقائيًا ويُخلى المكان عندما تغادر، دون أن تفعل أي شيء.

## الفكرة: RAII

المؤشر الذكي **كائن** يحمل المؤشر الحقيقي بداخله، وعندما ينتهي نطاقه (عند `}`) يُستدعى **المُهدِّم** (destructor) الخاص به تلقائيًا فيستدعي `delete`. هذه الفكرة اسمها **RAII** (Resource Acquisition Is Initialization)، أي «حجز المورد يتم مع إنشاء الكائن، وتحريره مع زواله». وهي من أهم أفكار C++ على الإطلاق، وتعمل بها `std::vector` و`std::string` والملفات أيضًا.

## `std::unique_ptr`: مالك واحد فقط

`std::unique_ptr` يملك الذاكرة **وحده**. نصنعه بالدالة `std::make_unique`:

```cpp run
#include <iostream>
#include <memory>
#include <string>

int main()
{
    std::unique_ptr<int> score = std::make_unique<int>(90);
    std::cout << "الدرجة: " << *score << "\n";
    *score += 10;
    std::cout << "بعد الزيادة: " << *score << "\n";

    auto name = std::make_unique<std::string>("ليلى");
    std::cout << "الاسم: " << *name << "، الطول بالبايت: " << name->length() << "\n";

    return 0;
}   // هنا تُحذف الذاكرة تلقائيًا، لا حاجة لـ delete
```

```text output
الدرجة: 90
بعد الزيادة: 100
الاسم: ليلى، الطول بالبايت: 8
```

- `*score` المحتوى، كأي مؤشر.
- `name->length()` السهم `->` يستدعي دالة على الكائن الذي يشير إليه المؤشر، وهو اختصار لـ `(*name).length()`.

### نقل الملكية بـ `std::move`

لا يمكن **نسخ** `unique_ptr` (لأنه لا يكون للذاكرة مالكان)، لكن يمكن **نقل** ملكيته:

```cpp run
#include <iostream>
#include <memory>

int main()
{
    auto a = std::make_unique<int>(5);
    std::unique_ptr<int> b = std::move(a);   // a سلّم المفتاح إلى b

    std::cout << std::boolalpha;
    std::cout << "a فارغ؟ " << (a == nullptr) << "\n";
    std::cout << "b = " << *b << "\n";
    return 0;
}
```

```text output
a فارغ؟ true
b = 5
```

## إثبات أن الحذف تلقائي

لنرَ متى تُحذف الكائنات بالضبط. سنكتب `struct` صغيرة تطبع رسالة عند إنشائها وعند حذفها (ستتعلم `struct` والمُنشئ والمُهدِّم بالتفصيل في الدروس القادمة، فركّز الآن على ترتيب الرسائل):

```cpp run
#include <iostream>
#include <memory>
#include <string>

struct Box
{
    std::string label;
    Box(const std::string& l) : label(l) { std::cout << "إنشاء " << label << "\n"; }
    ~Box() { std::cout << "حذف " << label << "\n"; }
};

int main()
{
    auto outer = std::make_unique<Box>("الصندوق الخارجي");
    {
        auto inner = std::make_unique<Box>("الصندوق الداخلي");
        std::cout << "داخل النطاق\n";
    }   // inner يُحذف هنا
    std::cout << "خارج النطاق\n";
    return 0;
}   // outer يُحذف هنا
```

```text output
إنشاء الصندوق الخارجي
إنشاء الصندوق الداخلي
داخل النطاق
حذف الصندوق الداخلي
خارج النطاق
حذف الصندوق الخارجي
```

## `std::shared_ptr`: ملكية مشتركة

أحيانًا يحتاج أكثر من جزء في البرنامج إلى نفس الكائن، ولا نعرف من سينتهي آخرًا. `std::shared_ptr` يحتفظ **بعدّاد** للمالكين، ويحذف الكائن عندما يصل العداد إلى صفر:

> **تشبيه:** غرفة اجتماعات: آخر شخص يخرج يطفئ النور. العداد يعرف كم شخصًا ما زال في الغرفة.

```cpp run
#include <iostream>
#include <memory>
#include <string>

struct Song
{
    std::string title;
    Song(const std::string& t) : title(t) {}
    ~Song() { std::cout << "حُذفت الأغنية " << title << "\n"; }
};

int main()
{
    std::shared_ptr<Song> s1 = std::make_shared<Song>("Track 1");
    std::cout << "عدد المالكين: " << s1.use_count() << "\n";
    {
        std::shared_ptr<Song> s2 = s1;   // النسخ مسموح: مالك إضافي
        std::cout << "عدد المالكين: " << s1.use_count() << "\n";
    }
    std::cout << "عدد المالكين: " << s1.use_count() << "\n";
    std::cout << "نهاية main\n";
    return 0;
}
```

```text output
عدد المالكين: 1
عدد المالكين: 2
عدد المالكين: 1
نهاية main
حُذفت الأغنية Track 1
```

## أيهما أستخدم؟

| الحالة | الاختيار |
|---|---|
| مجموعة من العناصر | `std::vector` (لا مؤشرات أصلًا) |
| كائن واحد له مالك واحد واضح | `std::unique_ptr` (الاختيار الافتراضي) |
| كائن يتشاركه عدة مالكين فعلًا | `std::shared_ptr` |
| مجرد «النظر» إلى كائن يملكه غيرك | مرجع `T&` أو مؤشر عادي `T*` |

**قاعدة C++ الحديثة:** لا تكتب `new` و`delete` في الكود العادي. استخدم `std::make_unique` و`std::make_shared`.

## مؤشرات ذكية داخل vector

```cpp run
#include <iostream>
#include <memory>
#include <string>
#include <vector>

int main()
{
    std::vector<std::unique_ptr<std::string>> names;
    names.push_back(std::make_unique<std::string>("Omar"));
    names.push_back(std::make_unique<std::string>("Nour"));
    names.push_back(std::make_unique<std::string>("Yara"));

    for (const auto& p : names)
        std::cout << *p << " (" << p->size() << ")\n";
    return 0;
}   // كل العناصر تُحذف تلقائيًا
```

```text output
Omar (4)
Nour (4)
Yara (4)
```

سنرى في درس تعدد الأشكال كيف نستخدم هذا النمط لتخزين أشكال مختلفة (دائرة، مربع...) في vector واحد.

## أخطاء شائعة

### محاولة نسخ `unique_ptr`

<!-- compile-error -->
```cpp
#include <memory>
int main()
{
    auto a = std::make_unique<int>(1);
    auto b = a;
    return *b;
}
```

```text
main.cpp:5:14: error: use of deleted function 'std::unique_ptr<_Tp, _Dp>::unique_ptr(const std::unique_ptr<_Tp, _Dp>&) [with _Tp = int; _Dp = std::default_delete<int>]'
```

**المعنى:** «استخدام دالة محذوفة: مُنشئ النسخ لـ `unique_ptr`». رسالة مخيفة الشكل، لكن معناها بسيط: **لا يمكن نسخ unique_ptr**. إذا أردت نقل الملكية اكتب `auto b = std::move(a);`، وإذا أردت مالكين فاستخدم `shared_ptr`.

> **نصيحة:** رسائل الأخطاء مع القوالب (مثل `<_Tp, _Dp>`) تبدو طويلة ومعقدة. ابحث عن الكلمات المفتاحية فيها: هنا «deleted function» و«unique_ptr(const unique_ptr&)» أي النسخ.

### استخدام المؤشر بعد نقله

بعد `auto b = std::move(a);` يصبح `a` فارغًا (`nullptr`)، واستخدام `*a` يسبب انهيار البرنامج. المترجم لن يحذرك، فانتبه.

## تمارين

### التمرين 1

أنشئ `unique_ptr` لعدد `double` قيمته `3.5`، ثم ضاعفه واطبعه.

```cpp exercise
#include <iostream>
#include <memory>

int main()
{
    // auto p = std::make_unique<double>(...);
    return 0;
}
```

```cpp solution
#include <iostream>
#include <memory>

int main()
{
    auto p = std::make_unique<double>(3.5);
    *p *= 2;
    std::cout << *p << "\n";
    return 0;
}
```

```text output
7
```

### التمرين 2

اكتب دالة `std::unique_ptr<std::string> makeGreeting(const std::string& name)` تُرجع مؤشرًا ذكيًا إلى نص «مرحبًا يا » + الاسم.

```cpp exercise
#include <iostream>
#include <memory>
#include <string>

int main()
{
    // auto g = makeGreeting("سلمى");
    // std::cout << *g << "\n";
    return 0;
}
```

```cpp solution
#include <iostream>
#include <memory>
#include <string>

std::unique_ptr<std::string> makeGreeting(const std::string& name)
{
    return std::make_unique<std::string>("مرحبًا يا " + name);
}

int main()
{
    auto g = makeGreeting("سلمى");
    std::cout << *g << "\n";
    return 0;
}
```

```text output
مرحبًا يا سلمى
```

إرجاع `unique_ptr` من دالة مسموح بدون `std::move`، لأن المترجم ينقل الملكية تلقائيًا عند الإرجاع.

### التمرين 3

أنشئ `shared_ptr<int>` واحدًا، ثم ثلاث نسخ منه داخل `std::vector`، واطبع `use_count()` قبل وبعد مسح الـ vector بـ `clear()`.

```cpp exercise
#include <iostream>
#include <memory>
#include <vector>

int main()
{
    auto p = std::make_shared<int>(100);
    std::vector<std::shared_ptr<int>> copies;
    // أضف 3 نسخ ثم اطبع use_count، ثم clear واطبع مرة أخرى
    return 0;
}
```

```cpp solution
#include <iostream>
#include <memory>
#include <vector>

int main()
{
    auto p = std::make_shared<int>(100);
    std::vector<std::shared_ptr<int>> copies;
    for (int i = 0; i < 3; i++)
        copies.push_back(p);
    std::cout << "قبل: " << p.use_count() << "\n";
    copies.clear();
    std::cout << "بعد: " << p.use_count() << "\n";
    return 0;
}
```

```text output
قبل: 4
بعد: 1
```

## اختبر نفسك

```quiz
{"question": "متى يحذف std::unique_ptr الذاكرة؟", "choices": ["عند استدعاء delete يدويًا فقط", "تلقائيًا عند انتهاء نطاقه", "لا يحذفها أبدًا", "عند نهاية البرنامج فقط"], "answer": 1, "explanation": "مُهدِّم unique_ptr يستدعي delete تلقائيًا عند الخروج من النطاق (RAII)."}
```

```quiz
{"question": "كيف تنقل ملكية unique_ptr من a إلى b؟", "choices": ["auto b = a;", "auto b = std::move(a);", "auto b = &a;", "auto b = *a;"], "answer": 1, "explanation": "unique_ptr لا يُنسخ، لكن يُنقل بـ std::move، ويصبح a فارغًا."}
```

```quiz
{"question": "ثلاثة shared_ptr تشير إلى نفس الكائن. متى يُحذف الكائن؟", "choices": ["عند حذف أول واحد", "عند حذف آخر واحد", "فورًا", "لا يُحذف"], "answer": 1, "explanation": "shared_ptr يعدّ المالكين ويحذف الكائن عندما يصل العدد إلى صفر."}
```

```quiz
{"question": "ما الطريقة المفضلة لإنشاء unique_ptr؟", "choices": ["new", "malloc", "std::make_unique", "std::make_pointer"], "answer": 2, "explanation": "std::make_unique أوضح وأأمن من new."}
```

## الخلاصة

- المؤشرات الذكية تحذف الذاكرة تلقائيًا (فكرة RAII).
- `std::unique_ptr` + `std::make_unique`: مالك واحد، يُنقل بـ `std::move` ولا يُنسخ.
- `std::shared_ptr` + `std::make_shared`: عدة مالكين وعدّاد.
- `->` لاستدعاء دوال الكائن عبر المؤشر.
- لا تكتب `new`/`delete` في الكود الحديث العادي.
