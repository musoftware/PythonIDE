# الدرس 23: التعامل مع الملفات (fstream)

كل ما يخزنه برنامجك في المتغيرات **يختفي** عند إغلاقه. لكي تبقى البيانات (الدرجات، والإعدادات، وأعلى نتيجة في اللعبة...) نحفظها في **ملفات** على القرص. المكتبة `<fstream>` تجعل ذلك سهلًا جدًا، لأنها تعمل بنفس أسلوب `std::cout` و`std::cin` الذي تعرفه.

> **تشبيه:** المتغيرات مثل **السبورة** في الفصل: تُمسح في آخر اليوم. والملف مثل **الكراسة**: ما تكتبه فيها يبقى حتى تفتحها غدًا.

## الأنواع الثلاثة

| النوع | الاستخدام | يشبه |
|---|---|---|
| `std::ofstream` | الكتابة في ملف (output) | `std::cout` |
| `std::ifstream` | القراءة من ملف (input) | `std::cin` |
| `std::fstream` | القراءة والكتابة معًا | الاثنين |

## الكتابة في ملف

```cpp run
#include <fstream>
#include <iostream>

int main()
{
    std::ofstream out("notes.txt");     // أنشئ الملف (أو امسح محتواه إن وُجد)
    if (!out)
    {
        std::cout << "تعذر فتح الملف!\n";
        return 1;
    }
    out << "السطر الأول\n";
    out << "الرقم: " << 42 << "\n";
    out << "Pi = " << 3.14 << "\n";
    out.close();                        // اختياري: يُغلق تلقائيًا عند نهاية النطاق

    std::cout << "تم الحفظ في notes.txt\n";
    return 0;
}
```

```text output
تم الحفظ في notes.txt
```

الملف يُنشأ في **مجلد العمل** الحالي للبرنامج، وهو عادة مجلد المشروع عند التشغيل من الـ IDE. ويُحفظ النص العربي بترميز UTF-8 كما هو في الكود.

## القراءة من ملف سطرًا سطرًا

```cpp run
#include <fstream>
#include <iostream>
#include <string>

int main()
{
    // أولًا نكتب ملفًا لنقرأه
    {
        std::ofstream out("todo.txt");
        out << "اشترِ خبزًا\n";
        out << "ذاكر C++\n";
        out << "اتصل بجدتك\n";
    }   // الملف يُغلق هنا تلقائيًا (RAII)

    std::ifstream in("todo.txt");
    if (!in)
    {
        std::cout << "الملف غير موجود\n";
        return 1;
    }
    std::string line;
    int n = 1;
    while (std::getline(in, line))      // حتى نهاية الملف
        std::cout << n++ << ". " << line << "\n";
    return 0;
}
```

```text output
1. اشترِ خبزًا
2. ذاكر C++
3. اتصل بجدتك
```

`while (std::getline(in, line))` هو النمط القياسي لقراءة ملف كامل: تتوقف الحلقة تلقائيًا عند نهاية الملف.

## قراءة أرقام من ملف

بالعامل `>>` تمامًا مثل `std::cin`:

```cpp run
#include <fstream>
#include <iostream>

int main()
{
    {
        std::ofstream out("scores.txt");
        out << "70 85 90\n95 60\n";
    }

    std::ifstream in("scores.txt");
    int score = 0, count = 0, total = 0;
    while (in >> score)
    {
        total += score;
        count++;
    }
    std::cout << "عدد الدرجات: " << count << "\n";
    std::cout << "المتوسط: " << static_cast<double>(total) / count << "\n";
    return 0;
}
```

```text output
عدد الدرجات: 5
المتوسط: 80
```

## الإضافة إلى آخر الملف (append)

`std::ofstream` العادي **يمسح** الملف ويبدأ من جديد. لإضافة سطور في آخره استخدم الوضع `std::ios::app`:

```cpp run
#include <fstream>
#include <iostream>
#include <string>

void logMessage(const std::string& msg)
{
    std::ofstream log("app_log.txt", std::ios::app);   // إضافة لا مسح
    log << msg << "\n";
}

int main()
{
    logMessage("بدأ البرنامج");
    logMessage("المستخدم سجّل الدخول");
    logMessage("انتهى البرنامج");

    std::ifstream in("app_log.txt");
    std::string line;
    while (std::getline(in, line))
        std::cout << "[سجل] " << line << "\n";
    return 0;
}
```

```text output
[سجل] بدأ البرنامج
[سجل] المستخدم سجّل الدخول
[سجل] انتهى البرنامج
```

## حفظ سجلات منظمة واستعادتها (CSV)

نمط شائع جدًا: نحفظ كل سجل في سطر، والحقول مفصولة بفاصلة. وللقراءة نستخدم `std::stringstream` من `<sstream>` لتقسيم السطر:

```cpp run
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

struct Student
{
    std::string name;
    int grade = 0;
};

void save(const std::vector<Student>& list, const std::string& file)
{
    std::ofstream out(file);
    for (const auto& s : list)
        out << s.name << "," << s.grade << "\n";
}

std::vector<Student> load(const std::string& file)
{
    std::vector<Student> list;
    std::ifstream in(file);
    std::string line;
    while (std::getline(in, line))
    {
        std::stringstream ss(line);
        Student s;
        std::string gradeText;
        std::getline(ss, s.name, ',');     // اقرأ حتى الفاصلة
        std::getline(ss, gradeText);       // الباقي
        s.grade = std::stoi(gradeText);
        list.push_back(s);
    }
    return list;
}

int main()
{
    save({{"نور", 95}, {"عمر", 82}, {"هدى", 88}}, "students.txt");

    std::vector<Student> loaded = load("students.txt");
    std::cout << "تم تحميل " << loaded.size() << " طلاب:\n";
    for (const auto& s : loaded)
        std::cout << s.name << " - " << s.grade << "\n";
    return 0;
}
```

```text output
تم تحميل 3 طلاب:
نور - 95
عمر - 82
هدى - 88
```

هذا هو الأسلوب الذي سنستخدمه في المشروع النهائي لحفظ درجات الطلاب.

## التحقق من وجود الملف: `<filesystem>`

C++17 تقدم مكتبة `<filesystem>` للتعامل مع الملفات والمجلدات:

```cpp run
#include <filesystem>
#include <fstream>
#include <iostream>

namespace fs = std::filesystem;

int main()
{
    {
        std::ofstream("data.txt") << "12345";
    }
    std::cout << std::boolalpha;
    std::cout << "data.txt موجود؟ " << fs::exists("data.txt") << "\n";
    std::cout << "الحجم: " << fs::file_size("data.txt") << " بايت\n";
    fs::remove("data.txt");
    std::cout << "بعد الحذف موجود؟ " << fs::exists("data.txt") << "\n";
    std::cout << "missing.txt موجود؟ " << fs::exists("missing.txt") << "\n";
    return 0;
}
```

```text output
data.txt موجود؟ true
الحجم: 5 بايت
بعد الحذف موجود؟ false
missing.txt موجود؟ false
```

## أخطاء شائعة

### عدم فحص فتح الملف

إذا كان الملف غير موجود أو المسار خطأ، فإن `std::ifstream in("x.txt");` **لا** يعطي خطأ، بل يبقى صامتًا وكل القراءات تفشل. افحص دائمًا: `if (!in) { ... }`.

### الخلط بين الكتابة والإضافة

`std::ofstream out("data.txt");` تمسح كل ما في الملف! إذا أردت الإضافة فاستخدم `std::ios::app`.

### المسارات في ويندوز

`"C:\data\new.txt"` خطأ، لأن `\n` داخلها تُفهم «سطرًا جديدًا»! اكتب `"C:\\data\\new.txt"` أو `"C:/data/new.txt"` (الشرطة المائلة الأمامية `/` تعمل في ويندوز أيضًا)، أو النص الخام `R"(C:\data\new.txt)"`.

### نسيان `#include <fstream>`

<!-- compile-error -->
```cpp
#include <iostream>
int main()
{
    std::ofstream out("a.txt");
    return 0;
}
```

```text
main.cpp:4:10: error: variable 'std::ofstream out' has initializer but incomplete type
```

**المعنى:** «المتغير له قيمة ابتدائية لكن نوعه غير مكتمل». المترجم يعرف أن `std::ofstream` موجود (مذكور في `<iostream>`) لكنه لا يعرف تفاصيله. أضف `#include <fstream>`.

## تمارين

### التمرين 1

اكتب الأعداد من 1 إلى 5 ومربعاتها في ملف `squares.txt` (كل سطر: العدد ومربعه)، ثم اقرأ الملف واطبع مجموع المربعات.

```cpp exercise
#include <fstream>
#include <iostream>

int main()
{
    return 0;
}
```

```cpp solution
#include <fstream>
#include <iostream>

int main()
{
    {
        std::ofstream out("squares.txt");
        for (int i = 1; i <= 5; i++)
            out << i << " " << i * i << "\n";
    }

    std::ifstream in("squares.txt");
    int n = 0, sq = 0, total = 0;
    while (in >> n >> sq)
        total += sq;
    std::cout << "مجموع المربعات: " << total << "\n";
    return 0;
}
```

```text output
مجموع المربعات: 55
```

### التمرين 2

اكتب برنامجًا يعدّ أسطر ملف وكلماته. أنشئ الملف أولًا بثلاثة أسطر من اختيارك.

```cpp exercise
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

int main()
{
    // تلميح: لكل سطر استخدم std::stringstream واقرأ الكلمات بـ >>
    return 0;
}
```

```cpp solution
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

int main()
{
    {
        std::ofstream out("poem.txt");
        out << "C++ لغة قوية\n";
        out << "تعلمها خطوة خطوة\n";
        out << "واستمتع\n";
    }

    std::ifstream in("poem.txt");
    std::string line, word;
    int lines = 0, words = 0;
    while (std::getline(in, line))
    {
        lines++;
        std::stringstream ss(line);
        while (ss >> word)
            words++;
    }
    std::cout << "أسطر: " << lines << "، كلمات: " << words << "\n";
    return 0;
}
```

```text output
أسطر: 3، كلمات: 7
```

### التمرين 3

برنامج «أعلى نتيجة»: اقرأ أعلى نتيجة من `best.txt` (إن لم يوجد الملف فهي 0)، ثم اقرأ نتيجة جديدة من المستخدم؛ إذا كانت أعلى فاحفظها واطبع «رقم قياسي جديد!».

```cpp exercise
#include <fstream>
#include <iostream>

int main()
{
    return 0;
}
```

```cpp solution
#include <fstream>
#include <iostream>

int main()
{
    int best = 0;
    {
        std::ifstream in("best.txt");
        if (in)
            in >> best;
    }

    int score = 0;
    std::cin >> score;
    if (score > best)
    {
        std::ofstream out("best.txt");
        out << score;
        std::cout << "رقم قياسي جديد! " << score << "\n";
    }
    else
    {
        std::cout << "أعلى نتيجة ما زالت " << best << "\n";
    }
    return 0;
}
```

```text input
120
```

```text output
رقم قياسي جديد! 120
```

## اختبر نفسك

```quiz
{"question": "أي نوع نستخدمه للكتابة في ملف؟", "choices": ["std::ifstream", "std::ofstream", "std::cin", "std::string"], "answer": 1, "explanation": "ofstream (output file stream) للكتابة، وifstream للقراءة."}
```

```quiz
{"question": "ماذا يحدث عند فتح ملف موجود بـ std::ofstream out(\"a.txt\");؟", "choices": ["يُضاف إلى آخره", "يُمسح محتواه ويبدأ من جديد", "خطأ ترجمة", "يُقرأ"], "answer": 1, "explanation": "الوضع الافتراضي يمسح الملف؛ للإضافة استخدم std::ios::app."}
```

```quiz
{"question": "ما النمط الصحيح لقراءة ملف سطرًا سطرًا حتى نهايته؟", "choices": ["while (true) getline(in, line);", "while (std::getline(in, line))", "for (int i = 0; i < 100; i++)", "in >> line فقط مرة واحدة"], "answer": 1, "explanation": "getline تُرجع الحالة، فتتوقف الحلقة تلقائيًا عند نهاية الملف."}
```

```quiz
{"question": "كيف تعرف أن الملف فُتح بنجاح؟", "choices": ["لا يمكن معرفة ذلك", "if (!in) يعني أن الفتح فشل", "بطباعة الملف", "باستخدام sizeof"], "answer": 1, "explanation": "كائن الملف يتحول إلى false إذا فشل الفتح."}
```

## الخلاصة

- `<fstream>`: `ofstream` للكتابة، و`ifstream` للقراءة، بنفس أسلوب `cout`/`cin`.
- افحص الفتح دائمًا بـ `if (!file)`.
- `while (std::getline(in, line))` لقراءة الملف كله، و`std::ios::app` للإضافة.
- `std::stringstream` لتقسيم السطور، و`<filesystem>` للتحقق من الملفات.
