# الدرس 11: النصوص `std::string`

النصوص موجودة في كل برنامج تقريبًا: أسماء، ورسائل، وعناوين، وكلمات مرور. في C++ الحديثة نستخدم `std::string` من المكتبة `<string>`، وهي سهلة وآمنة.

> **تشبيه:** النص مثل **قطار** من العربات، كل عربة فيها حرف واحد، ولكل عربة رقم يبدأ من صفر.

## الأساسيات

```cpp run
#include <iostream>
#include <string>

int main()
{
    std::string first = "Ahmed";
    std::string last = "Hassan";

    std::string full = first + " " + last;   // الدمج بـ +
    std::cout << full << "\n";
    std::cout << "الطول: " << full.length() << "\n";
    std::cout << "أول حرف: " << full[0] << "\n";
    std::cout << "آخر حرف: " << full.back() << "\n";

    full += "!";                               // إضافة في النهاية
    std::cout << full << "\n";

    std::cout << std::boolalpha << (first == "Ahmed") << "\n";
    std::cout << (std::string("apple") < std::string("banana")) << "\n";  // مقارنة أبجدية
    return 0;
}
```

```text output
Ahmed Hassan
الطول: 12
أول حرف: A
آخر حرف: n
Ahmed Hassan!
true
true
```

## أهم العمليات على النصوص

| العملية | مثال | المعنى |
|---|---|---|
| الطول | `s.length()` أو `s.size()` | عدد الحروف (البايتات) |
| فارغ؟ | `s.empty()` | `true` إذا لم يكن فيه شيء |
| جزء من النص | `s.substr(pos, len)` | `len` حرف بدءًا من `pos` |
| البحث | `s.find("abc")` | موقع أول ظهور أو `std::string::npos` |
| الاستبدال | `s.replace(pos, len, "x")` | استبدال جزء |
| الإدراج | `s.insert(pos, "x")` | إدراج نص |
| الحذف | `s.erase(pos, len)` | حذف جزء |

```cpp run
#include <iostream>
#include <string>

int main()
{
    std::string email = "student@school.edu";

    std::size_t at = email.find('@');
    if (at != std::string::npos)
    {
        std::string user = email.substr(0, at);
        std::string domain = email.substr(at + 1);
        std::cout << "المستخدم: " << user << "\n";
        std::cout << "النطاق: " << domain << "\n";
    }

    std::string msg = "I like Java";
    msg.replace(msg.find("Java"), 4, "C++");
    std::cout << msg << "\n";

    if (msg.find("Python") == std::string::npos)
        std::cout << "كلمة Python غير موجودة\n";
    return 0;
}
```

```text output
المستخدم: student
النطاق: school.edu
I like C++
كلمة Python غير موجودة
```

`std::string::npos` قيمة خاصة معناها «غير موجود».

## المرور على الحروف وتحليلها

المكتبة `<cctype>` فيها دوال لفحص الحروف الإنجليزية وتحويلها: `std::isdigit` و`std::isalpha` و`std::isupper` و`std::toupper` و`std::tolower`...

```cpp run
#include <cctype>
#include <iostream>
#include <string>

int main()
{
    std::string password = "Cpp2026rocks";
    int digits = 0, upper = 0, lower = 0;

    for (char c : password)
    {
        unsigned char u = static_cast<unsigned char>(c);
        if (std::isdigit(u))
            digits++;
        else if (std::isupper(u))
            upper++;
        else if (std::islower(u))
            lower++;
    }
    std::cout << "أرقام: " << digits << "، كبيرة: " << upper << "، صغيرة: " << lower << "\n";

    std::string shout = "hello";
    for (char& c : shout)
        c = static_cast<char>(std::toupper(static_cast<unsigned char>(c)));
    std::cout << shout << "\n";
    return 0;
}
```

```text output
أرقام: 4، كبيرة: 1، صغيرة: 7
HELLO
```

> **لماذا `unsigned char`؟** دوال `<cctype>` تتطلب قيمة غير سالبة، والحروف غير الإنجليزية قد تكون سالبة في `char`، فنحوّلها أولًا لتجنب السلوك غير المعرّف.

## التحويل بين النصوص والأرقام

```cpp run
#include <iostream>
#include <string>

int main()
{
    std::string ageText = "25";
    int age = std::stoi(ageText);           // نص ← int
    double price = std::stod("19.75");      // نص ← double

    std::string label = "العمر بعد 5 سنوات: " + std::to_string(age + 5);  // رقم ← نص
    std::cout << label << "\n";
    std::cout << "السعر × 2 = " << price * 2 << "\n";
    return 0;
}
```

```text output
العمر بعد 5 سنوات: 30
السعر × 2 = 39.5
```

إذا كان النص ليس رقمًا (مثل `"abc"`) فإن `std::stoi` ترمي **استثناءً** (`std::invalid_argument`)، وسنتعلم التعامل معه لاحقًا.

## النصوص العربية وUTF-8: معلومة مهمة

الحروف العربية في ترميز UTF-8 يأخذ كل منها **بايتين**، بينما الحرف الإنجليزي بايت واحد. و`std::string` يعدّ **البايتات** لا الحروف:

```cpp run
#include <iostream>
#include <string>

int main()
{
    std::string en = "Salam";
    std::string ar = "سلام";
    std::cout << en << ": " << en.length() << "\n";
    std::cout << ar << ": " << ar.length() << "\n";
    return 0;
}
```

```text output
Salam: 5
سلام: 8
```

لذلك:

- الدمج `+` والبحث `find` والمقارنة `==` تعمل مع العربية بشكل صحيح تمامًا.
- لكن `ar[0]` يعطيك **نصف** حرف عربي، و`substr` بأرقام عشوائية قد يقطع الحرف. تعامل مع النص العربي كقطعة واحدة، أو ابحث عن مواقع الكلمات بـ `find`.

## قراءة نص من المستخدم

تذكّر من درس الإدخال: `std::cin >> s` لكلمة واحدة، و`std::getline(std::cin, s)` لسطر كامل:

```cpp run
#include <iostream>
#include <string>

int main()
{
    std::string sentence;
    std::getline(std::cin, sentence);

    int words = 0;
    bool inWord = false;
    for (char c : sentence)
    {
        if (c == ' ')
            inWord = false;
        else if (!inWord)
        {
            inWord = true;
            words++;
        }
    }
    std::cout << "عدد الكلمات: " << words << "\n";
    return 0;
}
```

```text input
البرمجة   بلغة C++ ممتعة جدا
```

```text output
عدد الكلمات: 5
```

## أخطاء شائعة

### جمع نصين حرفيين مباشرة

<!-- compile-error -->
```cpp
#include <string>
int main()
{
    std::string s = "Hello, " + "World";
    return 0;
}
```

```text
main.cpp:4:31: error: invalid operands of types 'const char [8]' and 'const char [6]' to binary 'operator+'
```

**المعنى:** «معاملات غير صالحة للعامل `+`». النصوص بين علامات التنصيص ليست `std::string` بل مصفوفات حروف قديمة من لغة C، ولا يمكن جمعها مباشرة. الحل: اجعل أحدهما `std::string`:

```cpp
std::string s = std::string("Hello, ") + "World";
```

أو ببساطة اكتبهما نصًا واحدًا.

### وضع نص في متغير رقمي

<!-- compile-error -->
```cpp
int main()
{
    int n = "12";
    return n;
}
```

```text
main.cpp:3:13: error: invalid conversion from 'const char*' to 'int' [-fpermissive]
```

**المعنى:** «تحويل غير صالح من نص إلى `int`». `"12"` نص وليس رقمًا؛ استخدم `std::stoi("12")` أو اكتب `12` بدون علامات تنصيص.

### الخلط بين `'a'` و`"a"`

`'a'` حرف واحد من نوع `char`، و`"a"` نص. `s.find('@')` و`s.find("@")` كلاهما صحيح، لكن `char c = "a";` خطأ.

## تمارين

### التمرين 1

اقرأ كلمة إنجليزية واطبعها معكوسة، ثم اطبع هل هي «متناظرة» (palindrome) مثل `level`.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    std::string word;
    std::cin >> word;
    // اعكسها في متغير جديد
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

int main()
{
    std::string word;
    std::cin >> word;

    std::string reversed;
    for (int i = static_cast<int>(word.length()) - 1; i >= 0; i--)
        reversed += word[i];

    std::cout << reversed << "\n";
    if (reversed == word)
        std::cout << "كلمة متناظرة\n";
    else
        std::cout << "ليست متناظرة\n";
    return 0;
}
```

```text input
level
```

```text output
level
كلمة متناظرة
```

### التمرين 2

اكتب دالة `int countChar(const std::string& s, char c)` تعدّ مرات ظهور الحرف `c` في النص، واختبرها على `"programming"` والحرف `'m'`.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    // std::cout << countChar("programming", 'm') << "\n";
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

int countChar(const std::string& s, char c)
{
    int count = 0;
    for (char x : s)
        if (x == c)
            count++;
    return count;
}

int main()
{
    std::cout << countChar("programming", 'm') << "\n";
    std::cout << countChar("programming", 'g') << "\n";
    return 0;
}
```

```text output
2
2
```

### التمرين 3

اقرأ سطرًا فيه اسم ملف مثل `report.final.pdf` واطبع امتداده (ما بعد **آخر** نقطة). تلميح: `rfind` تبحث من النهاية.

```cpp exercise
#include <iostream>
#include <string>

int main()
{
    std::string file;
    std::getline(std::cin, file);
    // استخدم file.rfind('.')
    return 0;
}
```

```cpp solution
#include <iostream>
#include <string>

int main()
{
    std::string file;
    std::getline(std::cin, file);
    std::size_t dot = file.rfind('.');
    if (dot == std::string::npos)
        std::cout << "لا يوجد امتداد\n";
    else
        std::cout << "الامتداد: " << file.substr(dot + 1) << "\n";
    return 0;
}
```

```text input
report.final.pdf
```

```text output
الامتداد: pdf
```

## اختبر نفسك

```quiz
{"question": "ماذا تُرجع s.find(\"x\") إذا لم يوجد x في النص؟", "choices": ["0", "-1 دائمًا", "std::string::npos", "خطأ ترجمة"], "answer": 2, "explanation": "npos قيمة خاصة تعني «غير موجود»، فقارن بها دائمًا."}
```

```quiz
{"question": "ما ناتج std::string(\"abcdef\").substr(2, 3)؟", "choices": ["abc", "bcd", "cde", "cdef"], "answer": 2, "explanation": "تبدأ من الفهرس 2 (الحرف c) وتأخذ 3 حروف: cde."}
```

```quiz
{"question": "لماذا يعطي std::string(\"سلام\").length() القيمة 8؟", "choices": ["خطأ في المكتبة", "لأن كل حرف عربي يأخذ بايتين في UTF-8", "لأن العربية تُكتب من اليمين", "لأنها تعدّ المسافات"], "answer": 1, "explanation": "length() تعدّ البايتات، والحرف العربي بايتان في UTF-8."}
```

```quiz
{"question": "أي دالة تحوّل النص \"42\" إلى العدد 42؟", "choices": ["std::to_string", "std::stoi", "std::atoi_string", "static_cast<int>"], "answer": 1, "explanation": "std::stoi (string to int) تحوّل النص إلى int، وstd::to_string تفعل العكس."}
```

## الخلاصة

- `std::string`: الدمج `+`، والطول `length()`، والوصول `s[i]`.
- `find` و`substr` و`replace` و`erase` و`insert` لمعالجة النصوص.
- `std::stoi` و`std::stod` و`std::to_string` للتحويل.
- العربية في UTF-8: كل حرف بايتان، فاحذر من الفهارس.
