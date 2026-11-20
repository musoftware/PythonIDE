# الدرس 27: الأدوات والأحداث: القوائم، والاختيارات، والمؤقت

في الدرس السابق استخدمنا الزر ومربع النص والعنوان. اليوم نتعرف على أدوات أكثر: **القائمة** (ListBox)، و**القائمة المنسدلة** (ComboBox)، و**مربع الاختيار** (CheckBox)، و**المؤقت** (Timer)، ونتعرف على أحداث غير الضغط مثل تغيّر النص وتغيّر الاختيار.

## الأدوات وأحداثها الافتراضية

عندما تنقر مرتين على أداة في المصمم، تنشئ الـ IDE دالة **حدثها الافتراضي**:

| الأداة | البادئة | الحدث الافتراضي | يقع عندما |
|---|---|---|---|
| `Button` | `btn` | `Click` | يُضغط الزر |
| `TextBox` | `txt` | `TextChanged` | يتغير النص (مع كل حرف) |
| `CheckBox` | `chk` | `CheckedChanged` | يُعلَّم أو يُلغى تعليمه |
| `RadioButton` | `opt` / `rdo` | `CheckedChanged` | يُختار |
| `ListBox` | `lst` | `SelectedIndexChanged` | يتغير العنصر المحدد |
| `ComboBox` | `cbo` | `SelectedIndexChanged` | يتغير الاختيار |
| `NumericUpDown` | `num` | `ValueChanged` | تتغير القيمة |
| `Timer` | `tmr` | `Tick` | يمر الزمن المحدد في `Interval` |

ولكل أداة أحداث أخرى يمكنك اختيارها من نافذة الخصائص (قسم الأحداث)، مثل `DoubleClick` و`KeyPress` و`MouseMove`.

## خصائص ودوال مفيدة

| الأداة | القراءة / التغيير | الدوال (`rad::call`) |
|---|---|---|
| `ListBox` / `ComboBox` | `Text` (العنصر المحدد)، `ListIndex` (رقمه، أو `-1`)، `ListCount` (العدد) | `AddItem`، `RemoveItem` (برقم)، `Clear`، `List` (نص العنصر رقم i) |
| `CheckBox` | `Value`: `1` معلَّم، `0` غير معلَّم | |
| `NumericUpDown` | `Value` | |
| `Timer` | `Enabled` (`True`/`False`)، `Interval` (بالمللي ثانية) | |
| كل الأدوات | `Text`، `Enabled`، `Visible`، `BackColor`، `ForeColor` | `SetFocus` |

## مثال 1: قائمة المشتريات

ارسم النموذج:

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtItem` | (فارغ) |
| `Button` | `btnAdd` | `إضافة` |
| `Button` | `btnRemove` | `حذف المحدد` |
| `Button` | `btnClear` | `مسح الكل` |
| `ListBox` | `lstItems` | |
| `Label` | `lblCount` | (فارغ) |

سنستخدم أسلوبًا احترافيًا: البيانات الحقيقية في `std::vector` داخل برنامجنا، والقائمة على الشاشة مجرد **عرض** لها، ودالة `refresh` تعيد رسمها. هكذا يبقى المنطق في C++ (الذي تتقنه الآن)، والواجهة مجرد مرآة:

<!-- gui-test: shopping -->
```cpp
#include <string>
#include <vector>
#include "radgui.hpp"

std::vector<std::string> items;          // البيانات الحقيقية

void refresh()                           // اعرض البيانات على الشاشة
{
    rad::call("lstItems", "Clear");
    for (const std::string& it : items)
        rad::call("lstItems", "AddItem", it);
    rad::set("lblCount", "Text", "عدد العناصر: " + std::to_string(items.size()));
}

void Form1_Load()
{
    items = {"خبز", "لبن"};
    refresh();
}

void btnAdd_Click()
{
    std::string item = rad::get("txtItem", "Text");
    if (item.empty())
    {
        rad::msgbox("اكتب اسم العنصر أولًا");
        return;
    }
    items.push_back(item);
    rad::set("txtItem", "Text", "");
    refresh();
}

void btnRemove_Click()
{
    int index = static_cast<int>(rad::get_num("lstItems", "ListIndex"));
    if (index < 0)                       // لا يوجد عنصر محدد
        return;
    items.erase(items.begin() + index);
    refresh();
}

void btnClear_Click()
{
    items.clear();
    refresh();
}
```

عند التشغيل تظهر «خبز» و«لبن» في القائمة. اكتب «شاي» واضغط **إضافة**، ثم حدد «خبز» واضغط **حذف المحدد**، فتبقى «لبن» و«شاي» ويظهر «عدد العناصر: 2».

## مثال 2: محوّل العملات (أحداث التغيير)

هنا لا يوجد زر «احسب»! النتيجة تتحدث تلقائيًا كلما تغير المبلغ أو العملة أو الخيار:

| الأداة | Name | خصائص |
|---|---|---|
| `TextBox` | `txtAmount` | Text = `100` |
| `ComboBox` | `cboCurrency` | Items = `USD;EUR;SAR` |
| `CheckBox` | `chkFee` | Text = `أضف عمولة 2%` |
| `Label` | `lblResult` | |

خاصية **Items** في نافذة الخصائص تُكتب عناصرها مفصولة بفاصلة منقوطة.

<!-- gui-test: converter -->
```cpp
#include <map>
#include <string>
#include "radgui.hpp"

// سعر الجنيه مقابل كل عملة (أرقام للتوضيح فقط)
const std::map<std::string, double> rates = {{"USD", 50.0}, {"EUR", 54.0}, {"SAR", 13.3}};

void update()
{
    double amount = rad::num(rad::get("txtAmount", "Text"));
    std::string currency = rad::get("cboCurrency", "Text");

    auto it = rates.find(currency);
    if (it == rates.end())
    {
        rad::set("lblResult", "Text", "اختر العملة");
        return;
    }
    double pounds = amount * it->second;
    if (rad::get("chkFee", "Value") == "1")
        pounds *= 1.02;
    rad::set("lblResult", "Text", rad::str(amount) + " " + currency + " = " + rad::str(pounds) + " جنيه");
}

void Form1_Load() { update(); }
void txtAmount_TextChanged() { update(); }
void cboCurrency_SelectedIndexChanged() { update(); }
void chkFee_CheckedChanged() { update(); }
```

جرّب: اختر `USD` فيظهر «100 USD = 5000 جنيه»، ثم علّم مربع العمولة فيصبح «100 USD = 5100 جنيه»، ثم غيّر المبلغ إلى `10` فيصبح «10 USD = 510 جنيه».

لاحظ أننا كتبنا الحساب مرة واحدة في `update()`، وكل الأحداث تستدعيها. هذا تطبيق مباشر لمبدأ «لا تكرر نفسك».

## مثال 3: ساعة إيقاف (المؤقت Timer)

المؤقت أداة **غير مرئية** (تظهر أسفل المصمم في شريط المكونات)، تطلق الحدث `Tick` كل `Interval` مللي ثانية ما دامت `Enabled` تساوي `True`.

| الأداة | Name | خصائص |
|---|---|---|
| `Timer` | `tmrClock` | Interval = `1000`، Enabled = `False` |
| `Label` | `lblTime` | Text = `00:00` |
| `Button` | `btnStart` | Text = `ابدأ` |
| `Button` | `btnStop` | Text = `إيقاف` |
| `Button` | `btnReset` | Text = `تصفير` |

<!-- gui-test: stopwatch -->
```cpp
#include <string>
#include "radgui.hpp"

int seconds = 0;

std::string twoDigits(int n)
{
    return (n < 10 ? "0" : "") + std::to_string(n);
}

void showTime()
{
    rad::set("lblTime", "Text", twoDigits(seconds / 60) + ":" + twoDigits(seconds % 60));
}

void tmrClock_Tick()          // كل ثانية
{
    seconds++;
    showTime();
}

void btnStart_Click()
{
    rad::set("tmrClock", "Enabled", "True");
    rad::set("btnStart", "Enabled", "False");
}

void btnStop_Click()
{
    rad::set("tmrClock", "Enabled", "False");
    rad::set("btnStart", "Enabled", "True");
}

void btnReset_Click()
{
    seconds = 0;
    showTime();
}
```

## الحوار مع المستخدم: `rad::msgbox` و`rad::input`

```cpp
void btnAsk_Click()
{
    std::string name = rad::input("ما اسمك؟");     // مربع إدخال
    if (!name.empty())
        rad::msgbox("أهلًا يا " + name);            // رسالة منبثقة
}
```

استخدمهما باعتدال، فكثرة الرسائل المنبثقة تزعج المستخدم. غالبًا يكون العنوان `Label` أو شريط الحالة أفضل.

## نصائح لتصميم واجهة جيدة

1. **سمِّ كل أداة** باسم واضح ببادئة (`btnSave` وليس `Button3`).
2. **افصل المنطق عن الواجهة:** احسب في دوال C++ عادية، واستخدم دوال الأحداث فقط لقراءة المدخلات واستدعاء المنطق وعرض النتيجة.
3. **تحقق من المدخلات** قبل استخدامها (نص فارغ؟ رقم غير صالح؟ لا يوجد عنصر محدد؟).
4. **عطّل الأزرار** التي لا معنى لها في الحالة الحالية (مثل «ابدأ» أثناء العد).
5. استخدم `std::cout` للتتبع أثناء التطوير، فهو يظهر في نافذة Output.

## أخطاء شائعة

### استخدام `ListIndex` دون فحص `-1`

إذا لم يحدد المستخدم أي عنصر، فإن `ListIndex` تساوي `-1`. استخدامها مباشرة في `items.begin() + index` يسبب سلوكًا غير معرّف وقد ينهار البرنامج. افحص دائمًا `if (index < 0) return;`.

### مقارنة قيمة CheckBox بـ `"true"`

`rad::get("chkFee", "Value")` تُرجع النص `"1"` أو `"0"`، لا `"true"`. والمقارنة `== "true"` تكون دائمًا خاطئة دون أي رسالة.

### حلقة لا نهائية من الأحداث

إذا غيّرت `Text` لمربع نص **داخل** حدث `TextChanged` الخاص به، فقد يطلق التغيير الحدث مرة أخرى، وهكذا بلا نهاية. لا تغيّر الأداة نفسها داخل حدث تغيّرها، أو استخدم متغيرًا عامًا `bool updating` لمنع التكرار.

### برنامج «يعلق» في حدث طويل

النافذة تنتظر انتهاء دالة الحدث. إذا وضعت حلقة طويلة جدًا (أو `while (true)`) داخل `btnStart_Click`، تتجمد النافذة. للأعمال المتكررة استخدم **المؤقت** بدلًا من الحلقات.

## تمارين

### التمرين 1

برنامج «قائمة الأسماء المرتبة»: `txtName` و`btnAdd` و`lstNames`. كل إضافة تضع الاسم في `std::vector` ثم ترتبه بـ `std::sort` وتعيد عرض القائمة. لا تسمح بالأسماء المكررة.

```cpp exercise
#include <algorithm>
#include <string>
#include <vector>
#include "radgui.hpp"

std::vector<std::string> names;

void btnAdd_Click()
{
    // 1) اقرأ الاسم  2) إذا كان فارغًا أو مكررًا: اخرج  3) أضفه ورتب  4) أعد عرض القائمة
}
```

<!-- gui-test: sorted-names -->
```cpp solution
#include <algorithm>
#include <string>
#include <vector>
#include "radgui.hpp"

std::vector<std::string> names;

void btnAdd_Click()
{
    std::string name = rad::get("txtName", "Text");
    if (name.empty() || std::find(names.begin(), names.end(), name) != names.end())
        return;
    names.push_back(name);
    std::sort(names.begin(), names.end());

    rad::call("lstNames", "Clear");
    for (const auto& n : names)
        rad::call("lstNames", "AddItem", n);
    rad::set("txtName", "Text", "");
}
```

### التمرين 2

حاسبة مؤشر كتلة الجسم (BMI) تتحدث تلقائيًا: `txtWeight` (كجم) و`txtHeight` (سم) و`lblBmi`. المؤشر = الوزن ÷ (الطول بالمتر)². اعرض الرقم مقربًا لرقم عشري واحد، مع التصنيف: «نحافة» أقل من 18.5، و«طبيعي» أقل من 25، و«زيادة وزن» غير ذلك.

```cpp exercise
#include <cmath>
#include <string>
#include "radgui.hpp"

void update()
{
}

void txtWeight_TextChanged() { update(); }
void txtHeight_TextChanged() { update(); }
```

<!-- gui-test: bmi -->
```cpp solution
#include <cmath>
#include <string>
#include "radgui.hpp"

void update()
{
    double w = rad::num(rad::get("txtWeight", "Text"));
    double h = rad::num(rad::get("txtHeight", "Text")) / 100.0;
    if (w <= 0 || h <= 0)
    {
        rad::set("lblBmi", "Text", "أدخل الوزن والطول");
        return;
    }
    double bmi = std::round(w / (h * h) * 10) / 10;
    std::string label = bmi < 18.5 ? "نحافة" : (bmi < 25 ? "طبيعي" : "زيادة وزن");
    rad::set("lblBmi", "Text", rad::str(bmi) + " - " + label);
}

void txtWeight_TextChanged() { update(); }
void txtHeight_TextChanged() { update(); }
```

مثال: وزن `70` وطول `175` يعطي «22.9 - طبيعي».

## اختبر نفسك

```quiz
{"question": "ما الحدث الذي يقع مع كل حرف يكتبه المستخدم في مربع نص؟", "choices": ["Click", "TextChanged", "Tick", "Load"], "answer": 1, "explanation": "TextChanged هو الحدث الافتراضي لمربع النص ويقع عند كل تغيير."}
```

```quiz
{"question": "ماذا تُرجع rad::get(\"lstItems\", \"ListIndex\") إذا لم يُحدد أي عنصر؟", "choices": ["0", "-1", "نصًا فارغًا دائمًا", "عدد العناصر"], "answer": 1, "explanation": "-1 تعني لا يوجد تحديد، فافحصها قبل استخدام الرقم."}
```

```quiz
{"question": "كيف تجعل المؤقت tmrClock يبدأ العمل؟", "choices": ["rad::call(\"tmrClock\", \"Start\")", "rad::set(\"tmrClock\", \"Enabled\", \"True\")", "tmrClock_Tick()", "rad::show(\"tmrClock\")"], "answer": 1, "explanation": "المؤقت يطلق Tick ما دامت خاصية Enabled تساوي True."}
```

```quiz
{"question": "لماذا نحتفظ بالبيانات في std::vector بدل القائمة على الشاشة فقط؟", "choices": ["لأن ListBox لا تقبل النصوص", "لفصل المنطق عن الواجهة وتسهيل الترتيب والحفظ والحساب", "لأنه إجباري", "لتسريع الرسم فقط"], "answer": 1, "explanation": "البيانات في C++ يسهل معالجتها بالخوارزميات وحفظها في ملفات، والواجهة مجرد عرض."}
```

## الخلاصة

- لكل أداة حدث افتراضي: `Click` و`TextChanged` و`CheckedChanged` و`SelectedIndexChanged` و`Tick`...
- `rad::call(قائمة, "AddItem"/"RemoveItem"/"Clear", ...)` للقوائم، و`ListIndex` للعنصر المحدد.
- `CheckBox` قيمتها `"1"`/`"0"`، والمؤقت يعمل بـ `Enabled` و`Interval`.
- افصل المنطق عن الواجهة: بيانات في C++، ودالة `refresh`/`update` للعرض.
