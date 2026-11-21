# الدرس 26: أول نافذة رسومية بـ C++ في مصمم النماذج

حتى الآن كانت كل برامجنا تعمل في الكونسول: نص يُطبع ونص يُقرأ. اليوم نبني برنامجًا حقيقيًا **بنافذة وأزرار ومربعات نص**، بنفس طريقة Visual Basic الشهيرة: ترسم النافذة بالسحب والإفلات، ثم تكتب كود C++ الذي يعمل عند الضغط على الأزرار.

## البرمجة بالأحداث (Event-Driven Programming)

في برامج الكونسول، البرنامج هو الذي يقود: يسأل، ثم ينتظر الإجابة، ثم يكمل بالترتيب. أما في البرامج الرسومية فـ **المستخدم** هو الذي يقود: قد يضغط أي زر في أي وقت. لذلك نكتب الكود على شكل **معالجات أحداث** (event handlers): دالة لكل حدث تقول «عندما يحدث كذا، افعل كذا».

> **تشبيه:** برنامج الكونسول مثل **موظف الاستقبال الذي يملأ استمارة معك**: يسألك سؤالًا بعد سؤال بترتيب ثابت. البرنامج الرسومي مثل **المطعم**: النادل لا يفعل شيئًا حتى تناديه، وعندما تطلب «عصير» يحضر العصير، وعندما تطلب «الحساب» يحضر الحساب.

## كيف يعمل «جسر الواجهة» (GUI Bridge) في هذه الـ IDE؟

مشاريع C++ في هذه الـ IDE تعمل بفكرة بسيطة وذكية اسمها **GUI Bridge**:

1. **الـ IDE ترسم النافذة** التي صممتها في مصمم النماذج (Form Designer).
2. **برنامجك بـ C++** يعمل في الخلفية وينتظر الأحداث.
3. عندما يضغط المستخدم زرًا اسمه `btnHello`، ترسل الـ IDE إلى برنامجك الحدث `btnHello_Click`، فتُستدعى دالتك `void btnHello_Click()`.
4. داخل الدالة تقرأ وتغير الأدوات عبر مكتبة صغيرة اسمها **`radgui.hpp`** (فضاء الأسماء `rad`).

ميزة هذا الأسلوب أنك لا تحتاج إلى تعلم مكتبة رسومية ضخمة لكي تبدأ؛ تكفيك بضع دوال.

## أهم دوال `rad`

| الدالة | وظيفتها | مثال |
|---|---|---|
| `rad::get(أداة, خاصية)` | تقرأ خاصية كنص `std::string` | `rad::get("txtName", "Text")` |
| `rad::set(أداة, خاصية, قيمة)` | تغير خاصية (نص أو رقم) | `rad::set("lblResult", "Text", "مرحبا")` |
| `rad::get_num(أداة, خاصية)` | تقرأ خاصية كرقم `double` | `rad::get_num("txtAge", "Text")` |
| `rad::call(أداة, دالة, وسيط)` | تستدعي دالة في الأداة | `rad::call("lstNames", "AddItem", "علي")` |
| `rad::msgbox(نص)` | تعرض رسالة منبثقة | `rad::msgbox("تم الحفظ")` |
| `rad::input(سؤال)` | تعرض مربع إدخال وتُرجع النص | `rad::input("ما اسمك؟")` |
| `rad::num(نص)` | تحوّل نصًا إلى `double` (صفر إذا لم يكن رقمًا) | `rad::num("3.5")` |
| `rad::str(رقم)` | تحوّل رقمًا إلى نص بدون أصفار زائدة | `rad::str(2.50)` تُرجع `"2.5"` |
| `rad::end()` | تنهي البرنامج | |

وأي شيء تطبعه بـ `std::cout` يظهر في نافذة **Output** في الـ IDE، وهذا مفيد جدًا لتتبع ما يحدث أثناء التطوير.

## مشروعك الأول خطوة بخطوة: برنامج الترحيب

### 1) إنشاء المشروع

1. **File > New Project**.
2. اختر **C++ (GUI Bridge, g++ / MSVC)**، وسمّ المشروع `HelloForm`.
3. ستفتح الـ IDE النموذج **Form1** في وضع التصميم، ومعه ملف الكود `Form1.cpp`.

### 2) رسم النافذة

من **صندوق الأدوات** (Toolbox) اسحب إلى النموذج الأدوات التالية، ثم غيّر خاصية **Name** لكل أداة من نافذة **الخصائص** (Properties):

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |
| `Label` | `lblResult` | (فارغ) |

> **نصيحة:** اعتد على البادئات في الأسماء: `txt` لمربع النص، و`btn` للزر، و`lbl` للعنوان، و`lst` للقائمة، و`chk` لمربع الاختيار. ستعرف نوع الأداة من اسمها فورًا في الكود.

### 3) كتابة الكود

**انقر مرتين** على الزر في المصمم، فتنشئ الـ IDE دالة الحدث `void btnHello_Click()` وتنقلك إليها. اكتب الكود التالي في `Form1.cpp`:

<!-- gui-test: hello -->
```cpp
// Event handlers for Form1.
#include <string>
#include "radgui.hpp"

void Form1_Load()                      // تعمل مرة واحدة عند ظهور النافذة
{
    rad::set("lblResult", "Text", "اكتب اسمك ثم اضغط الزر");
}

void btnHello_Click()                  // تعمل عند الضغط على الزر
{
    std::string name = rad::get("txtName", "Text");
    if (name.empty())
        rad::set("lblResult", "Text", "من فضلك اكتب اسمك أولًا");
    else
        rad::set("lblResult", "Text", "أهلًا يا " + name + "!");
}
```

### 4) التشغيل

اضغط **F5**. تترجم الـ IDE الكود بـ g++، ثم تظهر نافذتك. اكتب اسمك (مثلًا «ريم») واضغط الزر، فيظهر في العنوان: **أهلًا يا ريم!**

لاحظ أن:

- اسم الدالة يجب أن يكون بالضبط **`اسمالأداة_اسمالحدث`**، مثل `btnHello_Click`، وأن تكون `void` وبلا معاملات. هكذا تربطها الـ IDE بالحدث.
- `Form1_Load` حدث خاص بالنموذج يعمل عند ظهوره، ومكانه المناسب لضبط القيم الابتدائية.
- لا يوجد `main` في كودك! الـ IDE تولّد ملف `_radmain.cpp` فيه `main` وحلقة الأحداث وتربطه ببرنامجك تلقائيًا.

## مثال ثانٍ: آلة حاسبة

ارسم النموذج التالي:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtA` | `0` |
| `TextBox` | `txtB` | `0` |
| `Button` | `btnAdd` | `+` |
| `Button` | `btnSub` | `-` |
| `Button` | `btnMul` | `×` |
| `Button` | `btnDiv` | `÷` |
| `Label` | `lblResult` | (فارغ) |

ثم اكتب الكود. لاحظ كيف نستخدم دالة مساعدة عادية `calculate` لكي لا نكرر الكود في الأزرار الأربعة، تمامًا كما تعلمنا في درس الدوال:

<!-- gui-test: calc -->
```cpp
#include <iostream>
#include <string>
#include "radgui.hpp"

// دالة مساعدة عادية (ليست حدثًا): تقرأ الرقمين وتحسب وتعرض الناتج
void calculate(char op)
{
    double a = rad::num(rad::get("txtA", "Text"));
    double b = rad::num(rad::get("txtB", "Text"));
    double result = 0;

    switch (op)
    {
    case '+': result = a + b; break;
    case '-': result = a - b; break;
    case '*': result = a * b; break;
    case '/':
        if (b == 0)
        {
            rad::set("lblResult", "Text", "لا يمكن القسمة على صفر");
            return;
        }
        result = a / b;
        break;
    }
    rad::set("lblResult", "Text", "الناتج = " + rad::str(result));
    std::cout << a << " " << op << " " << b << " = " << result << "\n";   // يظهر في Output
}

void btnAdd_Click() { calculate('+'); }
void btnSub_Click() { calculate('-'); }
void btnMul_Click() { calculate('*'); }
void btnDiv_Click() { calculate('/'); }
```

جرّب: اكتب `7` و`2` واضغط `÷`، فيظهر **الناتج = 3.5**، ويظهر في نافذة Output السطر `7 / 2 = 3.5`.

## تغيير شكل الأدوات من الكود

يمكنك تغيير أي خاصية تقريبًا أثناء التشغيل: النص `Text`، والتفعيل `Enabled`، والظهور `Visible`، ولون الخلفية `BackColor`، ولون الخط `ForeColor`...

<!-- gui-test: login -->
```cpp
#include <string>
#include "radgui.hpp"

int attempts = 0;   // متغير عام: يحتفظ بقيمته بين الأحداث

void btnLogin_Click()
{
    std::string pass = rad::get("txtPassword", "Text");
    if (pass == "cpp2026")
    {
        rad::set("lblStatus", "Text", "تم الدخول بنجاح");
        rad::set("lblStatus", "ForeColor", 32768);   // أخضر داكن
        return;
    }
    attempts++;
    rad::set("lblStatus", "Text", "كلمة مرور خاطئة (" + std::to_string(attempts) + " من 3)");
    rad::set("lblStatus", "ForeColor", 255);     // أحمر
    if (attempts >= 3)
    {
        rad::set("btnLogin", "Enabled", "False");   // عطّل الزر
        rad::set("lblStatus", "Text", "تم إيقاف المحاولات");
    }
}
```

الألوان تُكتب بصيغة Visual Basic: رقم يساوي `R + G × 256 + B × 65536`، فالأحمر `255`، والأخضر الداكن `32768`، والأزرق `16711680`، والأسود `0`، والأبيض `16777215`.

هنا رسمنا `TextBox` باسم `txtPassword` (واجعل خاصيته `PasswordChar` تساوي `*` لكي تُخفى الحروف)، و`Button` باسم `btnLogin`، و`Label` باسم `lblStatus`.

> **مهم:** برنامجك يظل يعمل طوال فترة ظهور النافذة، لذلك **المتغيرات العامة** (المعرّفة خارج الدوال مثل `attempts`) تحتفظ بقيمتها بين ضغطة وأخرى. أما المتغيرات المحلية داخل الدالة فتُنشأ من جديد مع كل حدث.

## أخطاء شائعة

### اسم الدالة لا يطابق اسم الأداة

إذا سمّيت الزر `btnHello` وكتبت الدالة `void btnhello_Click()` أو `void Button1_Click()`، **لن يحدث شيء** عند الضغط، ولن يظهر خطأ! لأن C++ حساسة لحالة الأحرف والاسم لا يطابق. الحل الأسهل: انقر مرتين على الأداة في المصمم ودع الـ IDE تكتب اسم الدالة بنفسها.

### كتابة معاملات لدالة الحدث

`void btnHello_Click(int x)` لن تُربط بالحدث. دوال الأحداث في جسر C++ تكون دائمًا `void` وبلا معاملات. وإذا احتجت معلومات إضافية عن الحدث (مثل إحداثيات الفأرة) فاستخدم `rad::arg(0)` و`rad::arg(1)`.

### نسيان `#include "radgui.hpp"`

<!-- compile-error -->
```cpp
#include <string>
void btnHello_Click()
{
    rad::set("lblResult", "Text", "Hi");
}
```

```text
main.cpp:4:5: error: 'rad' has not been declared
```

**المعنى:** «`rad` لم يُصرَّح عنه». أضف `#include "radgui.hpp"` في أول الملف (الـ IDE تضعه تلقائيًا في الملفات الجديدة).

### كتابة `main` بنفسك في مشروع له نموذج

الـ IDE تولّد `main` تلقائيًا في مشاريع النوافذ. إذا كتبت `int main()` في `Form1.cpp` سيظهر خطأ ربط مثل `multiple definition of 'main'`. احذف `main` من كود النموذج.

## تمارين

### التمرين 1

صمم نموذجًا فيه `TextBox` باسم `txtCelsius` و`Button` باسم `btnConvert` و`Label` باسم `lblResult`. عند الضغط يحوّل الدرجة إلى فهرنهايت ويعرض مثلًا `100 C = 212 F`.

```cpp exercise
#include <string>
#include "radgui.hpp"

void btnConvert_Click()
{
    // اقرأ txtCelsius، واحسب F = C * 9 / 5 + 32، واعرض النتيجة في lblResult
}
```

<!-- gui-test: convert -->
```cpp solution
#include <string>
#include "radgui.hpp"

void btnConvert_Click()
{
    double c = rad::num(rad::get("txtCelsius", "Text"));
    double f = c * 9 / 5 + 32;
    rad::set("lblResult", "Text", rad::str(c) + " C = " + rad::str(f) + " F");
}
```

عند كتابة `100` والضغط يظهر: `100 C = 212 F`.

### التمرين 2

عدّاد نقرات: زر `btnClick` وعنوان `lblCount`. كل ضغطة تزيد العداد وتعرض «عدد النقرات: N»، وزر `btnReset` يعيده إلى صفر.

```cpp exercise
#include <string>
#include "radgui.hpp"

// تلميح: تحتاج متغيرًا عامًا

void btnClick_Click()
{
}

void btnReset_Click()
{
}
```

<!-- gui-test: counter -->
```cpp solution
#include <string>
#include "radgui.hpp"

int clicks = 0;

void showCount()
{
    rad::set("lblCount", "Text", "عدد النقرات: " + std::to_string(clicks));
}

void Form1_Load()
{
    showCount();
}

void btnClick_Click()
{
    clicks++;
    showCount();
}

void btnReset_Click()
{
    clicks = 0;
    showCount();
}
```

بعد ثلاث نقرات يظهر «عدد النقرات: 3»، وبعد Reset يظهر «عدد النقرات: 0».

## اختبر نفسك

```quiz
{"question": "زر اسمه btnSave. ما اسم الدالة التي تعمل عند الضغط عليه؟", "choices": ["void Save()", "void btnSave_Click()", "void Click(btnSave)", "void onSave()"], "answer": 1, "explanation": "اسم معالج الحدث هو اسم الأداة ثم شرطة سفلية ثم اسم الحدث."}
```

```quiz
{"question": "كيف تقرأ النص المكتوب في مربع النص txtCity؟", "choices": ["std::cin >> txtCity", "rad::get(\"txtCity\", \"Text\")", "txtCity.Text", "rad::set(\"txtCity\")"], "answer": 1, "explanation": "rad::get تقرأ خاصية من أداة وتُرجعها كنص std::string."}
```

```quiz
{"question": "أين يظهر ما تطبعه بـ std::cout في مشروع نوافذ؟", "choices": ["في عنوان النافذة", "في نافذة Output في الـ IDE", "لا يظهر أبدًا", "في رسالة منبثقة"], "answer": 1, "explanation": "أي سطر يطبعه البرنامج غير أوامر الجسر يظهر في نافذة Output، وهو مفيد للتتبع."}
```

```quiz
{"question": "لماذا نستخدم متغيرًا عامًا لعدّاد النقرات؟", "choices": ["لأن المتغيرات المحلية تُنشأ من جديد في كل حدث", "لأن المتغيرات العامة أسرع", "لأن rad::set يحتاجها", "لا يوجد سبب"], "answer": 0, "explanation": "البرنامج يبقى يعمل، والمتغير العام يحتفظ بقيمته بين الأحداث."}
```

## الخلاصة

- البرامج الرسومية تعمل بالأحداث: دالة `void أداة_حدث()` لكل حدث.
- الـ IDE ترسم النافذة، وبرنامج C++ يستقبل الأحداث عبر GUI Bridge.
- `rad::get` و`rad::set` و`rad::num` و`rad::str` و`rad::msgbox` هي أدواتك الأساسية.
- `Form1_Load` للقيم الابتدائية، والمتغيرات العامة تحفظ الحالة بين الأحداث.
- لا تكتب `main` في مشروع النوافذ؛ الـ IDE تولّده.
