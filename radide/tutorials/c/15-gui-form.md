# الدرس 15: أول نافذة رسومية بلغة C في مصمم النماذج

كل برامجنا حتى الآن كانت في الكونسول. اليوم نصنع برنامجًا **بنافذة وأزرار ومربعات نص**، نرسمه بالسحب والإفلات مثل Visual Basic تمامًا، ثم نكتب كود C الذي يعمل عند الضغط على الأزرار.

## البرمجة بالأحداث

في الكونسول البرنامج يقود: يسأل ثم ينتظر. أما في النوافذ فـ **المستخدم** يقود: يضغط أي زر في أي وقت. لذلك نكتب **معالجات أحداث** (event handlers): دالة لكل حدث، مثل «عند الضغط على الزر btnHello».

> **تشبيه:** البرنامج الرسومي مثل **موظف خدمة العملاء**: لا يفعل شيئًا حتى يأتيه طلب. كل نوع طلب له إجراء معروف، وعندما يأتي الطلب يُنفذ إجراءه ثم يعود للانتظار.

## كيف يعمل GUI Bridge؟

1. **الـ IDE ترسم النافذة** التي صممتها في مصمم النماذج.
2. **برنامجك بلغة C** يعمل في الخلفية وينتظر الأحداث.
3. عندما يضغط المستخدم زرًا اسمه `btnHello` يُستدعى في برنامجك `void btnHello_Click(void)`.
4. داخل الدالة تقرأ وتغير الأدوات بدوال المكتبة الصغيرة **`radgui.h`**.

الـ IDE تولّد بنفسها ملف `_radmain.c` الذي فيه `main` وحلقة الأحداث، لذلك **لا تكتب `main`** في مشاريع النوافذ.

## أهم دوال `radgui.h`

| الدالة | وظيفتها | مثال |
|---|---|---|
| `rad_get(أداة, خاصية)` | تقرأ خاصية كنص | `rad_get("txtName", "Text")` |
| `rad_set(أداة, خاصية, نص)` | تغير خاصية | `rad_set("lblOut", "Text", "مرحبًا")` |
| `rad_get_num(أداة, خاصية)` | تقرأ خاصية كرقم `double` | `rad_get_num("txtA", "Text")` |
| `rad_set_num(أداة, خاصية, رقم)` | تكتب رقمًا في خاصية | `rad_set_num("lblOut", "Text", 3.5)` |
| `rad_call(أداة, دالة, وسيط)` | تستدعي دالة في الأداة | `rad_call("lstLog", "AddItem", "سطر")` |
| `rad_msgbox(نص)` | رسالة منبثقة | `rad_msgbox("تم الحفظ")` |
| `rad_input(سؤال)` | مربع إدخال يرجع نصًا | `rad_input("ما اسمك؟")` |
| `rad_print(نص)` | سطر في نافذة **Output** | `rad_print("وصلنا هنا")` |
| `rad_num(نص)` / `rad_str(رقم)` | تحويل بين النص والرقم | `rad_str(2.5)` |
| `rad_end()` | إنهاء البرنامج | |

> **مهم:** في مشاريع النوافذ لا تستخدم `printf` للتتبع، لأن البرنامج يتحدث مع الـ IDE عبر الإخراج القياسي. استخدم `rad_print` بدلًا منها.

> **ملحوظة:** النصوص التي ترجعها `rad_get` تُخزن في ذاكرة مؤقتة تُعاد كتابتها بعد عدة استدعاءات. إن أردت الاحتفاظ بالنص طويلًا فانسخه بـ `snprintf` أو `strcpy` إلى مصفوفة خاصة بك.

## مشروعك الأول خطوة بخطوة: برنامج الترحيب

### 1) إنشاء المشروع

1. **File > New Project...** (ملف ← مشروع جديد).
2. **Native** (أصلي) ← **C (GUI Bridge, gcc / MSVC)**، والقالب **Windows Application** (تطبيق Windows).
3. سمّ المشروع `HelloForm`. يفتح النموذج **Form1** في وضع التصميم، ومعه ملف الكود `Form1.c`.

### 2) رسم النافذة

من **Toolbox** (صندوق الأدوات) اسحب الأدوات التالية إلى النموذج، وغيّر خاصية **Name** لكل أداة من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |
| `Label` | `lblOut` | (فارغ) |

> **نصيحة:** البادئات تجعل الكود مقروءًا: `txt` لمربع النص، و`btn` للزر، و`lbl` للعنوان، و`lst` للقائمة، و`chk` لمربع الاختيار.

### 3) كتابة الكود

**انقر مرتين** على الزر في المصمم، فتنشئ الـ IDE الدالة `void btnHello_Click(void)` وتنقلك إليها في `Form1.c`. اكتب:

<!-- test: {"set": {"txtName.Text": "Mona"}, "events": ["btnHello Click"], "expect": {"lblOut.Text": "أهلًا يا Mona!"}} -->
```c form run
#include <stdio.h>
#include "radgui.h"

void Form1_Load(void)                 /* تعمل مرة واحدة عند ظهور النافذة */
{
    rad_set("lblOut", "Text", "اكتب اسمك ثم اضغط الزر");
}

void btnHello_Click(void)             /* تعمل عند الضغط على الزر */
{
    char msg[200];
    const char *name = rad_get("txtName", "Text");
    if (name[0] == '\0') {
        rad_set("lblOut", "Text", "من فضلك اكتب اسمك أولًا");
        return;
    }
    snprintf(msg, sizeof(msg), "أهلًا يا %s!", name);
    rad_set("lblOut", "Text", msg);
    rad_print(msg);                   /* يظهر في نافذة Output */
}
```

### 4) التشغيل

اضغط **F5**. تترجم الـ IDE الكود بـ gcc، ثم تظهر نافذتك. اكتب اسمك واضغط الزر فيظهر الترحيب.

لاحظ:

- اسم الدالة يجب أن يكون **`اسم الأداة_اسم الحدث`** بالضبط، مثل `btnHello_Click`، ونوعها `void` وبلا معاملات `(void)`.
- `Form1_Load` حدث النموذج عند ظهوره، والمكان المناسب للقيم الابتدائية.
- زر **«جرّبه»** هنا ينشئ المشروع ويضع الأدوات في النموذج تلقائيًا بنفس الأسماء التي يستخدمها الكود.

## مثال ثانٍ: آلة حاسبة

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtA` | `0` |
| `TextBox` | `txtB` | `0` |
| `Button` | `btnAdd` | `+` |
| `Button` | `btnSub` | `-` |
| `Button` | `btnMul` | `×` |
| `Button` | `btnDiv` | `÷` |
| `Label` | `lblResult` | (فارغ) |

لاحظ الدالة المساعدة `calculate` التي تمنع تكرار الكود في الأزرار الأربعة:

<!-- test: {"set": {"txtA.Text": "7", "txtB.Text": "2"}, "events": ["btnMul Click", {"txtB.Text": "0"}, "btnDiv Click"], "expect": {"lblResult.Text": "14"}, "msgbox": ["لا يمكن القسمة على صفر"]} -->
```c form run
#include "radgui.h"

static void calculate(char op)
{
    double a = rad_get_num("txtA", "Text");
    double b = rad_get_num("txtB", "Text");
    double r = 0;
    switch (op) {
    case '+': r = a + b; break;
    case '-': r = a - b; break;
    case '*': r = a * b; break;
    case '/':
        if (b == 0) {
            rad_msgbox("لا يمكن القسمة على صفر");
            return;
        }
        r = a / b;
        break;
    }
    rad_set("lblResult", "Text", rad_str(r));
}

void btnAdd_Click(void) { calculate('+'); }
void btnSub_Click(void) { calculate('-'); }
void btnMul_Click(void) { calculate('*'); }
void btnDiv_Click(void) { calculate('/'); }
```

الدالة `static void calculate` ليست حدثًا (اسمها لا يحتوي `_Click`)، بل دالة عادية مثل التي تعلمناها في الدرس 8.

## أحداث أخرى مفيدة

| الحدث | متى يحدث |
|---|---|
| `Form1_Load` | عند ظهور النموذج |
| `btnX_Click` | عند الضغط على زر |
| `txtX_TextChanged` | عند تغير نص مربع النص |
| `chkX_CheckedChanged` | عند تغيير مربع الاختيار |
| `lstX_SelectedIndexChanged` | عند اختيار عنصر في القائمة |
| `tmrX_Tick` | كل فترة من مؤقت `Timer` (خاصية `Interval` بالملي ثانية) |

لمعرفة أحداث أي أداة: اخترها في المصمم، ثم افتح قائمة الأحداث في نافذة **Properties**، أو انقر مرتين لحدثها الافتراضي.

## أخطاء شائعة

- **اسم الأداة في الكود يختلف عن الخاصية Name:** `rad_get("txtname", ...)` لا تجد `txtName` لأن الأسماء حساسة لحالة الأحرف.
- **كتابة `main` في مشروع النوافذ:** يعطيك gcc خطأ `multiple definition of main`، لأن الـ IDE تولدها.
- **معالج بمعاملات:** `void btnHello_Click(int x)` لا يرتبط بالحدث. اكتب `(void)`.
- **استخدام `printf` للتتبع:** استخدم `rad_print`.

## تمرين

### التمرين 1

أضف زرًا `btnClear` يمسح مربعي النص `txtA` و`txtB` ويضع فيهما `0`، ويمسح `lblResult`:

```c form exercise
#include "radgui.h"

void btnClear_Click(void)
{
    /* اكتب الكود هنا */
}
```

<!-- test: {"set": {"txtA.Text": "5", "txtB.Text": "9", "lblResult.Text": "14"}, "events": ["btnClear Click"], "expect": {"txtA.Text": "0", "txtB.Text": "0", "lblResult.Text": ""}} -->
```c form solution
#include "radgui.h"

void btnClear_Click(void)
{
    rad_set("txtA", "Text", "0");
    rad_set("txtB", "Text", "0");
    rad_set("lblResult", "Text", "");
}
```

## اختبر نفسك

```quiz
{"question": "ما اسم الدالة التي تعمل عند الضغط على زر اسمه btnSave؟", "choices": ["Save_Click", "btnSave_Click", "click_btnSave", "btnSave"], "answer": 1, "explanation": "الصيغة: اسم الأداة ثم _ ثم اسم الحدث."}
```

```quiz
{"question": "لماذا لا نكتب main في مشروع C بنافذة؟", "choices": ["لأن C لا تحتاج main", "لأن الـ IDE تولد _radmain.c الذي فيه main وحلقة الأحداث", "لأن main ممنوعة في النوافذ", "لأن Form1_Load هي main"], "answer": 1, "explanation": "الـ IDE تولد main التي تستقبل الأحداث وتستدعي معالجاتك."}
```

```quiz
{"question": "كيف تطبع رسالة تتبع في نافذة Output من مشروع نوافذ C؟", "choices": ["printf", "rad_print", "rad_msgbox", "puts"], "answer": 1, "explanation": "rad_print ترسل السطر إلى نافذة Output دون أن تخلط بروتوكول الجسر."}
```

## الخلاصة

- مشاريع النوافذ: **Windows Application** في **C (GUI Bridge)**.
- ارسم الأدوات وسمّها، ثم اكتب `void اسمالأداة_الحدث(void)`.
- `rad_get` و`rad_set` و`rad_call` و`rad_msgbox` للتعامل مع الأدوات.
- لا `main` ولا `printf` في مشاريع النوافذ.
