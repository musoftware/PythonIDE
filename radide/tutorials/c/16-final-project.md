# الدرس 16: المشروع النهائي: دفتر الدرجات

حان وقت جمع كل ما تعلمناه في برنامج واحد حقيقي: **دفتر درجات** بنافذة، يضيف الطلاب إلى قائمة، ويحسب المتوسط وأعلى درجة، ويحفظ البيانات في ملف. سنستخدم: المتغيرات، والشروط، والحلقات، والدوال، والمصفوفات، والنصوص، والهياكل، والملفات، والنوافذ.

## الخطة

قبل كتابة أي كود، يفكر المبرمج المحترف في **التصميم**:

1. **البيانات:** هيكل `Student` فيه الاسم والدرجة، ومصفوفة من الطلاب مع عدّاد.
2. **الواجهة:** مربعا نص للاسم والدرجة، وأزرار: إضافة، حفظ، مسح، وقائمة، وعنوان للإحصائيات.
3. **الدوال المساعدة:** حساب الإحصائيات وعرضها، وتحديث القائمة.

## الجزء الأول: المنطق في الكونسول أولًا

فكرة ذكية: نختبر منطق البرنامج في الكونسول قبل ربطه بالنافذة. هكذا نكتشف الأخطاء بسهولة:

```c run
#include <stdio.h>
#include <string.h>

#define MAX_STUDENTS 100

typedef struct {
    char name[64];
    double mark;
} Student;

static Student book[MAX_STUDENTS];
static int count = 0;

int add_student(const char *name, double mark)
{
    if (count >= MAX_STUDENTS || name[0] == '\0' || mark < 0 || mark > 100)
        return 0;
    snprintf(book[count].name, sizeof(book[count].name), "%s", name);
    book[count].mark = mark;
    count++;
    return 1;
}

void stats(double *avg, double *best, int *passed)
{
    double sum = 0;
    *best = 0;
    *passed = 0;
    for (int i = 0; i < count; i++) {
        sum += book[i].mark;
        if (book[i].mark > *best) *best = book[i].mark;
        if (book[i].mark >= 50) (*passed)++;
    }
    *avg = count ? sum / count : 0;
}

const char *grade(double m)
{
    if (m >= 90) return "ممتاز";
    if (m >= 80) return "جيد جدًا";
    if (m >= 65) return "جيد";
    if (m >= 50) return "مقبول";
    return "راسب";
}

int main(void)
{
    add_student("Ali", 91);
    add_student("Mona", 78);
    add_student("Omar", 45);
    if (!add_student("Bad", 150))
        printf("رُفضت درجة غير صحيحة\n");

    for (int i = 0; i < count; i++)
        printf("%-6s %5.1f  %s\n", book[i].name, book[i].mark, grade(book[i].mark));

    double avg, best;
    int passed;
    stats(&avg, &best, &passed);
    printf("المتوسط %.2f، الأعلى %.1f، الناجحون %d من %d\n", avg, best, passed, count);
    return 0;
}
```

```text output
رُفضت درجة غير صحيحة
Ali     91.0  ممتاز
Mona    78.0  جيد
Omar    45.0  راسب
المتوسط 71.33، الأعلى 91.0، الناجحون 2 من 3
```

المنطق يعمل. لاحظ أننا استخدمنا مؤشرات (`double *avg`) لإرجاع ثلاث قيم من دالة واحدة.

## الجزء الثاني: النافذة

أنشئ مشروعًا جديدًا: **File > New Project > Native > C (GUI Bridge, gcc / MSVC)**، القالب **Windows Application**، والاسم `GradeBook`. ثم ارسم:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtName` | (فارغ) |
| `TextBox` | `txtMark` | (فارغ) |
| `Button` | `btnAdd` | `إضافة` |
| `Button` | `btnSave` | `حفظ` |
| `Button` | `btnClear` | `مسح الكل` |
| `ListBox` | `lstStudents` | |
| `Label` | `lblStats` | (فارغ) |

أضف أيضًا عنوانين (Label) بجانب مربعي النص مكتوبًا فيهما «الاسم» و«الدرجة».

## الجزء الثالث: الكود الكامل

انسخ المنطق نفسه إلى `Form1.c`، واربطه بالأحداث:

<!-- test: {"set": {"txtName.Text": "Sara", "txtMark.Text": "91"}, "events": ["btnAdd Click", {"txtName.Text": "Omar", "txtMark.Text": "45"}, "btnAdd Click", {"txtName.Text": "", "txtMark.Text": "70"}, "btnAdd Click"], "expect": {"lstStudents.Items": "Sara - 91.0 - ممتاز|Omar - 45.0 - راسب", "lblStats.Text": "العدد 2 | المتوسط 68.00 | الأعلى 91.0 | الناجحون 1", "txtMark.Text": "70"}, "msgbox": ["اكتب اسم الطالب"]} -->
```c form run
#include <stdio.h>
#include <string.h>
#include "radgui.h"

#define MAX_STUDENTS 100

typedef struct {
    char name[64];
    double mark;
} Student;

static Student book[MAX_STUDENTS];
static int count = 0;

static const char *grade(double m)
{
    if (m >= 90) return "ممتاز";
    if (m >= 80) return "جيد جدًا";
    if (m >= 65) return "جيد";
    if (m >= 50) return "مقبول";
    return "راسب";
}

static void show_stats(void)
{
    char text[200];
    double sum = 0, best = 0;
    int passed = 0;
    for (int i = 0; i < count; i++) {
        sum += book[i].mark;
        if (book[i].mark > best) best = book[i].mark;
        if (book[i].mark >= 50) passed++;
    }
    if (count == 0)
        snprintf(text, sizeof(text), "لا يوجد طلاب بعد");
    else
        snprintf(text, sizeof(text), "العدد %d | المتوسط %.2f | الأعلى %.1f | الناجحون %d",
                 count, sum / count, best, passed);
    rad_set("lblStats", "Text", text);
}

void Form1_Load(void)
{
    show_stats();
}

void btnAdd_Click(void)
{
    char name[64], line[160];
    snprintf(name, sizeof(name), "%s", rad_get("txtName", "Text"));   /* انسخ النص فورًا */
    double mark = rad_get_num("txtMark", "Text");

    if (name[0] == '\0') {
        rad_msgbox("اكتب اسم الطالب");
        return;
    }
    if (mark < 0 || mark > 100) {
        rad_msgbox("الدرجة يجب أن تكون بين 0 و 100");
        return;
    }
    if (count >= MAX_STUDENTS) {
        rad_msgbox("الدفتر ممتلئ");
        return;
    }
    strcpy(book[count].name, name);
    book[count].mark = mark;
    count++;

    snprintf(line, sizeof(line), "%s - %.1f - %s", name, mark, grade(mark));
    rad_call("lstStudents", "AddItem", line);
    rad_set("txtName", "Text", "");
    rad_set("txtMark", "Text", "");
    show_stats();
}

void btnSave_Click(void)
{
    FILE *f = fopen("grades.txt", "w");
    if (f == NULL) {
        rad_msgbox("تعذر إنشاء الملف");
        return;
    }
    for (int i = 0; i < count; i++)
        fprintf(f, "%s,%.1f\n", book[i].name, book[i].mark);
    fclose(f);
    rad_msgbox("تم الحفظ في grades.txt");
}

void btnClear_Click(void)
{
    count = 0;
    rad_call("lstStudents", "Clear", "");
    show_stats();
}
```

## شرح أهم النقاط

- **البيانات العامة الخاصة بالملف:** `static Student book[...]` و`static int count` متغيرات خارج الدوال، فتحتفظ بقيمها بين الأحداث. كل ضغطة زر تستدعي دالة جديدة، لكن البيانات تبقى.
- **نسخ نص `rad_get` فورًا:** لأن نصوصها مؤقتة؛ نسخناها إلى `name` بـ `snprintf`.
- **التحقق من المدخلات:** لا نثق في المستخدم: اسم فارغ أو درجة خارج المدى نرفضها برسالة.
- **دوال مساعدة `static`:** مثل `grade` و`show_stats`؛ ليست أحداثًا لأن أسماءها بلا `_Click`.
- **الملف:** زر الحفظ يكتب سطرًا لكل طالب بصيغة CSV، يمكن فتحها في Excel.

## تصحيح الأخطاء (Debugging)

إذا لم يعمل شيء كما تتوقع:

1. انقر في الهامش الأيسر بجانب سطر في `btnAdd_Click` لتضع **نقطة توقف** (Toggle Breakpoint = تبديل نقطة التوقف، F9).
2. شغّل بـ **F5** (Start Debugging).
3. أضف طالبًا: يتوقف البرنامج عند نقطة التوقف، وترى قيم `name` و`mark` و`count` في نافذة **Locals** (المتغيرات المحلية).
4. تقدم سطرًا سطرًا بـ **F10** (Step Over = خطوة فوق)، أو ادخل في دالة بـ **F11** (Step Into = خطوة إلى الداخل).

## أفكار لتطوير المشروع

- زر **تحميل** يقرأ `grades.txt` بـ `fgets` ويعيد ملء القائمة (استخدم `strchr` لإيجاد الفاصلة).
- زر **حذف** يحذف الطالب المختار: اقرأ `rad_get_num("lstStudents", "ListIndex")`، وأزح عناصر المصفوفة، ثم `rad_call("lstStudents", "RemoveItem", ...)`.
- ترتيب الطلاب حسب الدرجة بخوارزمية الفقاعات من الدرس 9 قبل عرضهم.

## تمرين

### التمرين 1

أضف إلى نسخة الكونسول دالة `print_failed` تطبع أسماء الراسبين فقط (أقل من 50):

```c exercise
#include <stdio.h>

typedef struct {
    const char *name;
    double mark;
} Student;

void print_failed(const Student s[], int n)
{
    // أكمل
}

int main(void)
{
    Student cls[] = {{"Ali", 91}, {"Sami", 30}, {"Mona", 78}, {"Rana", 49}};
    print_failed(cls, 4);
    return 0;
}
```

```c solution
#include <stdio.h>

typedef struct {
    const char *name;
    double mark;
} Student;

void print_failed(const Student s[], int n)
{
    for (int i = 0; i < n; i++)
        if (s[i].mark < 50)
            printf("%s\n", s[i].name);
}

int main(void)
{
    Student cls[] = {{"Ali", 91}, {"Sami", 30}, {"Mona", 78}, {"Rana", 49}};
    print_failed(cls, 4);
    return 0;
}
```

```text output
Sami
Rana
```

## اختبر نفسك

```quiz
{"question": "لماذا جعلنا book وcount متغيرات خارج الدوال؟", "choices": ["لأن C تمنع المصفوفات المحلية", "لتبقى البيانات محفوظة بين الأحداث المختلفة", "لتسريع الطباعة", "لأن rad_set تحتاج ذلك"], "answer": 1, "explanation": "كل حدث دالة مستقلة، والمتغيرات المحلية تختفي بانتهائها؛ أما متغيرات الملف فتبقى."}
```

```quiz
{"question": "ما الفائدة من اختبار المنطق في الكونسول أولًا؟", "choices": ["لا فائدة", "اكتشاف أخطاء المنطق بسهولة قبل ربطه بالواجهة", "لأن النوافذ لا تقبل الدوال", "لتصغير حجم البرنامج"], "answer": 1, "explanation": "فصل المنطق عن الواجهة يجعل الاختبار والتصحيح أسهل."}
```

## الخلاصة وماذا بعد؟

مبروك! أكملت دورة C. أصبحت تعرف أساسيات اللغة التي بُنيت بها أنظمة التشغيل:

- المتغيرات والأنواع، والإدخال والإخراج، والشروط والحلقات.
- الدوال والمصفوفات والنصوص.
- المؤشرات والذاكرة الديناميكية.
- الهياكل والملفات وتقسيم المشروع.
- برامج النوافذ بمصمم النماذج.

**الخطوة التالية:** ادرس **دورة C++** في نفس قائمة الدروس لتتعلم الكائنات و`std::string` و`std::vector`، أو **دورة Rust** لترى كيف تحل لغة حديثة مشاكل الذاكرة التي واجهناها في C.
