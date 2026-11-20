# الدرس 28: المشروع النهائي: مدير درجات الطلاب

مبروك! وصلت إلى المشروع النهائي. سنبني برنامجًا حقيقيًا متكاملًا يجمع كل ما تعلمته تقريبًا: **مدير درجات الطلاب** بنافذة رسومية، يضيف الطلاب ويحذفهم، ويحسب الإحصائيات، ويرتب، ويحفظ البيانات في ملف ويستعيدها عند فتح البرنامج.

ما ستستخدمه من الدروس السابقة:

| المفهوم | أين يظهر في المشروع |
|---|---|
| `struct` و`class` والتغليف | `Student` و`GradeBook` |
| `std::vector` و`std::string` | قائمة الطلاب وأسماؤهم |
| الخوارزميات واللامدا | الترتيب، والبحث، والأعلى، والمتوسط |
| الملفات `fstream` و`stringstream` | الحفظ والتحميل بصيغة CSV |
| الاستثناءات | رفض الدرجات غير الصالحة |
| الأحداث وأدوات النموذج | الواجهة الرسومية |

## الخطوة 1: المنطق أولًا (برنامج كونسول)

القاعدة الذهبية: **ابنِ المنطق وجرّبه أولًا بعيدًا عن الواجهة**. سنكتب الصنف `GradeBook` ونختبره في برنامج كونسول عادي. اضغط «جرّبه»:

```cpp run
#include <algorithm>
#include <fstream>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Student
{
    std::string name;
    int grade = 0;
};

std::string letterFor(int grade)
{
    if (grade >= 85) return "ممتاز";
    if (grade >= 75) return "جيد جدًا";
    if (grade >= 65) return "جيد";
    if (grade >= 50) return "مقبول";
    return "راسب";
}

class GradeBook
{
private:
    std::vector<Student> students;

public:
    void add(const std::string& name, int grade)
    {
        if (name.empty())
            throw std::invalid_argument("اسم الطالب فارغ");
        if (grade < 0 || grade > 100)
            throw std::out_of_range("الدرجة يجب أن تكون من 0 إلى 100");
        auto it = std::find_if(students.begin(), students.end(),
                               [&name](const Student& s) { return s.name == name; });
        if (it != students.end())
            it->grade = grade;               // موجود: حدّث درجته
        else
            students.push_back({name, grade});
    }

    void removeAt(std::size_t index)
    {
        if (index < students.size())
            students.erase(students.begin() + index);
    }

    void sortByGrade()
    {
        std::sort(students.begin(), students.end(),
                  [](const Student& a, const Student& b) { return a.grade > b.grade; });
    }

    void sortByName()
    {
        std::sort(students.begin(), students.end(),
                  [](const Student& a, const Student& b) { return a.name < b.name; });
    }

    double average() const
    {
        if (students.empty())
            return 0;
        int sum = std::accumulate(students.begin(), students.end(), 0,
                                  [](int acc, const Student& s) { return acc + s.grade; });
        return static_cast<double>(sum) / students.size();
    }

    const Student* top() const
    {
        if (students.empty())
            return nullptr;
        return &*std::max_element(students.begin(), students.end(),
                                  [](const Student& a, const Student& b) { return a.grade < b.grade; });
    }

    long passedCount() const
    {
        return std::count_if(students.begin(), students.end(), [](const Student& s) { return s.grade >= 50; });
    }

    const std::vector<Student>& all() const { return students; }

    void save(const std::string& file) const
    {
        std::ofstream out(file);
        if (!out)
            throw std::runtime_error("تعذر الحفظ في " + file);
        for (const auto& s : students)
            out << s.name << "," << s.grade << "\n";
    }

    void load(const std::string& file)
    {
        std::ifstream in(file);
        if (!in)
            return;                          // أول تشغيل: لا يوجد ملف بعد
        students.clear();
        std::string line;
        while (std::getline(in, line))
        {
            std::stringstream ss(line);
            std::string name, gradeText;
            if (std::getline(ss, name, ',') && std::getline(ss, gradeText))
            {
                try
                {
                    add(name, std::stoi(gradeText));
                }
                catch (const std::exception&)
                {
                    // سطر تالف: تجاهله
                }
            }
        }
    }
};

int main()
{
    GradeBook book;
    book.add("سارة", 92);
    book.add("خالد", 67);
    book.add("منى", 45);
    book.add("خالد", 71);                   // تحديث درجة خالد

    try
    {
        book.add("وليد", 120);
    }
    catch (const std::exception& e)
    {
        std::cout << "مرفوض: " << e.what() << "\n";
    }

    book.sortByGrade();
    for (const auto& s : book.all())
        std::cout << s.name << ": " << s.grade << " (" << letterFor(s.grade) << ")\n";

    std::cout << "المتوسط: " << book.average() << "\n";
    std::cout << "الأول: " << book.top()->name << "\n";
    std::cout << "الناجحون: " << book.passedCount() << " من " << book.all().size() << "\n";

    book.save("grades.csv");
    GradeBook copy;
    copy.load("grades.csv");
    std::cout << "تم تحميل " << copy.all().size() << " طلاب من الملف\n";
    return 0;
}
```

```text output
مرفوض: الدرجة يجب أن تكون من 0 إلى 100
سارة: 92 (ممتاز)
خالد: 71 (جيد)
منى: 45 (راسب)
المتوسط: 69.3333
الأول: سارة
الناجحون: 2 من 3
تم تحميل 3 طلاب من الملف
```

لاحظ:

- `add` ترمي استثناءً للبيانات الخاطئة بدل أن تقبلها بصمت؛ والواجهة ستلتقطه وتعرض الرسالة.
- `top()` تُرجع **مؤشرًا** يكون `nullptr` إذا كانت القائمة فارغة، وهذا مثال حقيقي على فائدة المؤشر (قيمة «لا شيء»).
- `load` تتجاهل الأسطر التالفة في الملف بدل أن ينهار البرنامج.

## الخطوة 2: تصميم النافذة

أنشئ مشروعًا جديدًا **C++ (GUI Bridge)** باسم `GradesManager`، وارسم على `Form1` (واجعل خاصية Text للنموذج «مدير الدرجات»):

| الأداة | Name | Text / خصائص |
|---|---|---|
| `Label` | `lblName` | `اسم الطالب:` |
| `TextBox` | `txtName` | |
| `Label` | `lblGrade` | `الدرجة:` |
| `TextBox` | `txtGrade` | |
| `Button` | `btnAdd` | `إضافة / تحديث` |
| `Button` | `btnRemove` | `حذف المحدد` |
| `CheckBox` | `chkByGrade` | `ترتيب حسب الدرجة` |
| `ListBox` | `lstStudents` | عرض كبير |
| `Label` | `lblStats` | |
| `Label` | `lblStatus` | |
| `Button` | `btnSave` | `حفظ` |

اقتراح للترتيب: مربعا النص والزران في الأعلى، والقائمة في الوسط، والإحصائيات والحالة وزر الحفظ في الأسفل.

## الخطوة 3: كود النموذج

ضع الصنف `GradeBook` (من الخطوة 1، **بدون** `main`) في أول `Form1.cpp`، ثم دوال الأحداث. هذا هو الملف كاملًا:

<!-- gui-test: grades -->
```cpp
// Form1.cpp - مدير درجات الطلاب
#include <algorithm>
#include <fstream>
#include <iostream>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include "radgui.hpp"

// ======================= المنطق =======================
struct Student
{
    std::string name;
    int grade = 0;
};

std::string letterFor(int grade)
{
    if (grade >= 85) return "ممتاز";
    if (grade >= 75) return "جيد جدًا";
    if (grade >= 65) return "جيد";
    if (grade >= 50) return "مقبول";
    return "راسب";
}

class GradeBook
{
private:
    std::vector<Student> students;

public:
    void add(const std::string& name, int grade)
    {
        if (name.empty())
            throw std::invalid_argument("اسم الطالب فارغ");
        if (grade < 0 || grade > 100)
            throw std::out_of_range("الدرجة يجب أن تكون من 0 إلى 100");
        auto it = std::find_if(students.begin(), students.end(),
                               [&name](const Student& s) { return s.name == name; });
        if (it != students.end())
            it->grade = grade;
        else
            students.push_back({name, grade});
    }

    void removeAt(std::size_t index)
    {
        if (index < students.size())
            students.erase(students.begin() + index);
    }

    void sortByGrade()
    {
        std::sort(students.begin(), students.end(),
                  [](const Student& a, const Student& b) { return a.grade > b.grade; });
    }

    void sortByName()
    {
        std::sort(students.begin(), students.end(),
                  [](const Student& a, const Student& b) { return a.name < b.name; });
    }

    double average() const
    {
        if (students.empty())
            return 0;
        int sum = std::accumulate(students.begin(), students.end(), 0,
                                  [](int acc, const Student& s) { return acc + s.grade; });
        return static_cast<double>(sum) / students.size();
    }

    const Student* top() const
    {
        if (students.empty())
            return nullptr;
        return &*std::max_element(students.begin(), students.end(),
                                  [](const Student& a, const Student& b) { return a.grade < b.grade; });
    }

    long passedCount() const
    {
        return std::count_if(students.begin(), students.end(), [](const Student& s) { return s.grade >= 50; });
    }

    const std::vector<Student>& all() const { return students; }

    void save(const std::string& file) const
    {
        std::ofstream out(file);
        if (!out)
            throw std::runtime_error("تعذر الحفظ في " + file);
        for (const auto& s : students)
            out << s.name << "," << s.grade << "\n";
    }

    void load(const std::string& file)
    {
        std::ifstream in(file);
        if (!in)
            return;
        students.clear();
        std::string line;
        while (std::getline(in, line))
        {
            std::stringstream ss(line);
            std::string name, gradeText;
            if (std::getline(ss, name, ',') && std::getline(ss, gradeText))
            {
                try
                {
                    add(name, std::stoi(gradeText));
                }
                catch (const std::exception&)
                {
                }
            }
        }
    }
};

// ======================= الواجهة =======================
const std::string DATA_FILE = "grades.csv";
GradeBook book;

void status(const std::string& text)
{
    rad::set("lblStatus", "Text", text);
}

void refresh()
{
    if (rad::get("chkByGrade", "Value") == "1")
        book.sortByGrade();
    else
        book.sortByName();

    rad::call("lstStudents", "Clear");
    for (const auto& s : book.all())
        rad::call("lstStudents", "AddItem",
                  s.name + " - " + std::to_string(s.grade) + " (" + letterFor(s.grade) + ")");

    std::string stats = "العدد: " + std::to_string(book.all().size());
    if (const Student* best = book.top())
    {
        stats += " | المتوسط: " + rad::str(book.average());
        stats += " | الأول: " + best->name;
        stats += " | الناجحون: " + std::to_string(book.passedCount());
    }
    rad::set("lblStats", "Text", stats);
}

void Form1_Load()
{
    book.load(DATA_FILE);
    refresh();
    status("تم تحميل " + std::to_string(book.all().size()) + " طالب");
}

void btnAdd_Click()
{
    std::string name = rad::get("txtName", "Text");
    std::string gradeText = rad::get("txtGrade", "Text");
    try
    {
        int grade = std::stoi(gradeText);       // قد ترمي invalid_argument
        book.add(name, grade);                  // قد ترمي invalid_argument أو out_of_range
        refresh();
        status("تمت إضافة " + name);
        rad::set("txtName", "Text", "");
        rad::set("txtGrade", "Text", "");
    }
    catch (const std::out_of_range& e)
    {
        status(e.what());
    }
    catch (const std::invalid_argument&)
    {
        status(name.empty() ? "اكتب اسم الطالب" : "الدرجة يجب أن تكون رقمًا");
    }
}

void btnRemove_Click()
{
    int index = static_cast<int>(rad::get_num("lstStudents", "ListIndex"));
    if (index < 0)
    {
        status("حدد طالبًا من القائمة أولًا");
        return;
    }
    book.removeAt(static_cast<std::size_t>(index));
    refresh();
    status("تم الحذف");
}

void chkByGrade_CheckedChanged()
{
    refresh();
}

void btnSave_Click()
{
    try
    {
        book.save(DATA_FILE);
        status("تم الحفظ في " + DATA_FILE);
        std::cout << "saved " << book.all().size() << " students\n";
    }
    catch (const std::exception& e)
    {
        rad::msgbox(e.what());
    }
}
```

## الخطوة 4: التشغيل والتجربة

اضغط **F5** وجرّب السيناريو التالي:

1. أضف «سارة» بدرجة `92`، و«خالد» بدرجة `67`، و«منى» بدرجة `45`. تظهر القائمة مرتبة أبجديًا.
2. جرّب درجة `abc` فيظهر «الدرجة يجب أن تكون رقمًا»، ودرجة `150` فيظهر «الدرجة يجب أن تكون من 0 إلى 100».
3. علّم «ترتيب حسب الدرجة» فتصبح سارة في الأعلى.
4. حدد «منى» واضغط **حذف المحدد**.
5. اضغط **حفظ**، ثم أغلق البرنامج وافتحه مرة أخرى بـ F5: البيانات ما زالت موجودة!

الملف `grades.csv` يُحفظ في مجلد المشروع، ويمكنك فتحه بالمفكرة أو حتى ببرنامج Excel.

## كيف يعمل البرنامج؟ (مراجعة التصميم)

- **فصل المنطق عن الواجهة:** الصنف `GradeBook` لا يعرف شيئًا عن الأزرار والقوائم؛ يمكنك نقله كما هو إلى برنامج كونسول أو إلى أي واجهة أخرى. والأحداث مجرد «غراء» يقرأ المدخلات، ويستدعي المنطق، ويعرض النتيجة.
- **مصدر واحد للحقيقة:** البيانات في `book` فقط، و`refresh()` ترسم الشاشة منها دائمًا. لذلك ترتيب القائمة على الشاشة يطابق ترتيب `students`، فيصبح `ListIndex` هو نفسه الفهرس في الـ vector.
- **الأخطاء لا توقف البرنامج:** كل مدخل خاطئ يتحول إلى استثناء يُلتقط ويُعرض في `lblStatus`.

## تحديات لتطوير المشروع

جرّب أن تطور المشروع بنفسك، فهذا أفضل تمرين على الإطلاق:

1. **تقسيم الملفات:** انقل `Student` و`GradeBook` إلى `GradeBook.h` و`GradeBook.cpp` (Project ← Add Module) كما تعلمت في الدرس 25، واترك في `Form1.cpp` الواجهة فقط.
2. **البحث:** أضف `txtSearch` يعرض في حدث `TextChanged` الطلاب الذين يحتوي اسمهم على النص المكتوب فقط (استخدم `find`). تنبيه: عندها لن يطابق `ListIndex` الفهرس في `students` مباشرة، فاحتفظ بقائمة الفهارس المعروضة.
3. **عدة مواد:** اجعل لكل طالب `std::map<std::string, int>` لدرجات المواد، واحسب المجموع.
4. **الحفظ التلقائي:** احفظ بعد كل تعديل، واعرض النجمة `*` في عنوان النافذة عند وجود تغييرات غير محفوظة.
5. **تقرير:** زر يكتب ملف `report.txt` فيه جدول منسق بـ `std::setw` والإحصائيات.

## تمرين

أضف إلى `GradeBook` دالة `std::vector<Student> failing() const` تُرجع الطلاب الراسبين فقط (أقل من 50)، واختبرها في برنامج كونسول.

```cpp exercise
#include <iostream>
#include <string>
#include <vector>

struct Student
{
    std::string name;
    int grade = 0;
};

class GradeBook
{
    std::vector<Student> students;

public:
    void add(const std::string& name, int grade) { students.push_back({name, grade}); }
    // std::vector<Student> failing() const
};

int main()
{
    GradeBook b;
    b.add("Ali", 40);
    b.add("Mai", 90);
    b.add("Tamer", 30);
    // اطبع الراسبين
    return 0;
}
```

```cpp solution
#include <algorithm>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

struct Student
{
    std::string name;
    int grade = 0;
};

class GradeBook
{
    std::vector<Student> students;

public:
    void add(const std::string& name, int grade) { students.push_back({name, grade}); }

    std::vector<Student> failing() const
    {
        std::vector<Student> out;
        std::copy_if(students.begin(), students.end(), std::back_inserter(out),
                     [](const Student& s) { return s.grade < 50; });
        return out;
    }
};

int main()
{
    GradeBook b;
    b.add("Ali", 40);
    b.add("Mai", 90);
    b.add("Tamer", 30);
    for (const auto& s : b.failing())
        std::cout << s.name << " " << s.grade << "\n";
    return 0;
}
```

```text output
Ali 40
Tamer 30
```

`std::copy_if` تنسخ العناصر التي تحقق الشرط، و`std::back_inserter` تجعلها تُضاف بـ `push_back`.

## اختبر نفسك

```quiz
{"question": "لماذا وضعنا المنطق في صنف GradeBook منفصل عن دوال الأحداث؟", "choices": ["لأن الأحداث لا تقبل الأصناف", "لسهولة الاختبار وإعادة الاستخدام وفصل المنطق عن الواجهة", "لتسريع الرسم", "لأنه إجباري في C++"], "answer": 1, "explanation": "المنطق المستقل يُختبر في الكونسول ويُنقل لأي واجهة، والأحداث تبقى بسيطة."}
```

```quiz
{"question": "ماذا يحدث إذا كتب المستخدم abc في خانة الدرجة؟", "choices": ["ينهار البرنامج", "std::stoi ترمي invalid_argument فنلتقطها ونعرض رسالة", "تُحفظ الدرجة صفرًا بصمت", "يُحذف الطالب"], "answer": 1, "explanation": "التقاط الاستثناء يحوّل الخطأ إلى رسالة مفهومة بدل الانهيار."}
```

```quiz
{"question": "لماذا تُرجع top() مؤشرًا وليس مرجعًا؟", "choices": ["لأن المؤشرات أسرع دائمًا", "لأن المؤشر يمكن أن يكون nullptr عندما تكون القائمة فارغة", "لأن المراجع ممنوعة في الأصناف", "لا سبب"], "answer": 1, "explanation": "المرجع لا يمكن أن يكون فارغًا، أما المؤشر فيعبّر عن «لا يوجد طالب»."}
```

```quiz
{"question": "لماذا يطابق ListIndex فهرس الطالب في الـ vector؟", "choices": ["صدفة", "لأن refresh() ترسم القائمة من الـ vector بنفس الترتيب دائمًا", "لأن ListBox ترتب نفسها", "لا يطابقه"], "answer": 1, "explanation": "مصدر واحد للحقيقة: الشاشة تُرسم من البيانات بنفس ترتيبها."}
```

## الخلاصة والخطوات التالية

لقد بنيت برنامجًا كاملًا بـ C++ الحديثة: أصناف، وحاويات، وخوارزميات، ولامدا، وملفات، واستثناءات، وواجهة رسومية. هذا إنجاز حقيقي!

إلى أين بعد ذلك؟

- **تعمق في المكتبة القياسية:** `std::optional` و`std::variant` و`std::chrono` و`std::thread`.
- **C++20 وما بعدها:** النطاقات (ranges)، والمفاهيم (concepts)، و`std::format`.
- **مكتبات رسومية كاملة:** Qt أو wxWidgets أو Dear ImGui لبرامج احترافية.
- **الألعاب:** SFML أو raylib لبرمجة الألعاب ثنائية الأبعاد.
- **التدريب المستمر:** حل المسائل في مواقع مثل Codeforces وLeetCode.

وراجع **قاموس المصطلحات** في الدرس التالي كلما احتجت.
