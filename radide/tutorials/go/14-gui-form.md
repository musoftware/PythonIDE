# الدرس 14: أول نافذة رسومية بـ Go في مصمم النماذج

حتى الآن كتبنا برامج كونسول. اليوم نرسم **نافذة** بأزرار ومربعات نص في مصمم النماذج، ونكتب منطقها بلغة Go، تمامًا كما في Visual Basic.

## الفكرة: GUI Bridge

1. **الـ IDE ترسم النافذة** التي صممتها.
2. **برنامج Go** يعمل في الخلفية وينتظر الأحداث.
3. عند الضغط على زر اسمه `btnHello` تُستدعى في برنامجك الدالة `btnHello_Click`.
4. داخلها تقرأ وتغير الأدوات بدوال جاهزة: `Get` و`Set` و`Call` و`MsgBox`.

> **تشبيه:** الـ IDE هي **واجهة المحل** التي يراها الزبون، وبرنامج Go هو **المخزن** في الخلف. عندما يطلب الزبون شيئًا من الواجهة، تصل ورقة الطلب إلى المخزن، فيجهزه ويرسله للواجهة.

الـ IDE تولّد بنفسها الملف `radmain_gen.go` الذي فيه `func main()` وجدول يربط أسماء الأحداث بدوالك، وتنسخ المكتبة `radlib.go`. لذلك **لا تكتب `main`** في مشروع النوافذ.

## دوال التعامل مع الأدوات

| الدالة | وظيفتها | مثال |
|---|---|---|
| `Get(أداة, خاصية) string` | تقرأ خاصية كنص | `Get("txtName", "Text")` |
| `GetNum(أداة, خاصية) float64` | تقرأ خاصية كرقم | `GetNum("txtAge", "Text")` |
| `Set(أداة, خاصية, قيمة)` | تغير خاصية (أي نوع) | `Set("lblOut", "Text", "مرحبًا")` |
| `Call(أداة, دالة, وسائط...)` | تستدعي دالة في الأداة | `Call("lstLog", "AddItem", "سطر")` |
| `MsgBox(نص)` | رسالة منبثقة | `MsgBox("تم")` |
| `Input(سؤال) string` | مربع إدخال | `Input("ما اسمك؟")` |
| `Show(نموذج)` / `Hide(نموذج)` | إظهار وإخفاء النماذج | `Show("Form2")` |
| `End()` | إنهاء البرنامج | |

> **مهم:** في مشروع النوافذ لا تستخدم `fmt.Println` للتتبع، لأن البرنامج يتحدث مع الـ IDE عبر الإخراج القياسي. استخدم `log.Println(...)` فتظهر رسالتك في نافذة **Output**.

## مشروعك الأول: برنامج الترحيب

### 1) إنشاء المشروع

1. **File > New Project...** > **Native** > **Go (GUI Bridge)**.
2. القالب **Windows Application** (تطبيق Windows)، والاسم `HelloForm`.
3. يفتح **Form1** في وضع التصميم، ومعه ملف الكود `Form1.go`.

### 2) رسم النافذة

من **Toolbox** (صندوق الأدوات) اسحب الأدوات، وغيّر **Name** و**Text** من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |
| `Label` | `lblOut` | (فارغ) |

### 3) كتابة الكود

انقر مرتين على الزر فتنشئ الـ IDE الدالة `btnHello_Click` وتنقلك إليها:

<!-- test: {"set": {"txtName.Text": "Mona"}, "events": ["btnHello Click"], "expect": {"lblOut.Text": "أهلًا يا Mona!"}} -->
```go form run
package main

import (
    "log"
    "strings"
)

// Form1_Load تعمل مرة واحدة عند ظهور النافذة.
func Form1_Load(e RadEvent) {
    Set("lblOut", "Text", "اكتب اسمك ثم اضغط الزر")
}

// btnHello_Click تعمل عند الضغط على الزر.
func btnHello_Click(e RadEvent) {
    name := strings.TrimSpace(Get("txtName", "Text"))
    if name == "" {
        Set("lblOut", "Text", "من فضلك اكتب اسمك أولًا")
        return
    }
    Set("lblOut", "Text", "أهلًا يا "+name+"!")
    log.Println("رحبنا بـ", name)            // يظهر في نافذة Output
}
```

### 4) التشغيل

اضغط **F5**: تترجم الـ IDE المشروع بـ `go build`، ثم تظهر النافذة. اكتب اسمك واضغط الزر.

قواعد ربط الأحداث:

- اسم الدالة **`اسمالأداة_اسمالحدث`** بالضبط، مثل `btnHello_Click`.
- الدالة تأخذ معاملًا واحدًا `e RadEvent` أو لا تأخذ شيئًا. والـ `RadEvent` فيه تفاصيل الحدث: `e.X` و`e.Y` لموقع الماوس، و`e.KeyCode` للمفتاح المضغوط.
- كل ملفات المشروع في `package main`، فدوالك المساعدة متاحة في كل مكان.

## مثال ثانٍ: محوّل درجات الحرارة

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtValue` | `0` |
| `RadioButton` | `optToF` | `مئوي ← فهرنهايت` |
| `RadioButton` | `optToC` | `فهرنهايت ← مئوي` |
| `Button` | `btnConvert` | `حوّل` |
| `Label` | `lblResult` | (فارغ) |
| `ListBox` | `lstHistory` | |

<!-- test: {"events": [{"txtValue.Text": "100", "optToF.Checked": "True"}, "btnConvert Click", {"txtValue.Text": "abc"}, "btnConvert Click"], "expect": {"lblResult.Text": "212.0 F", "lstHistory.Items": "100.0 => 212.0 F"}, "msgbox": ["اكتب رقمًا صحيحًا"]} -->
```go form run
package main

import (
    "fmt"
    "strconv"
    "strings"
)

func convert(v float64, toF bool) (float64, string) {
    if toF {
        return v*9/5 + 32, "F"
    }
    return (v - 32) * 5 / 9, "C"
}

func Form1_Load(e RadEvent) {
    Set("optToF", "Checked", true)
}

func btnConvert_Click(e RadEvent) {
    v, err := strconv.ParseFloat(strings.TrimSpace(Get("txtValue", "Text")), 64)
    if err != nil {
        MsgBox("اكتب رقمًا صحيحًا")
        return
    }
    toF := Get("optToF", "Checked") == "True"
    r, unit := convert(v, toF)
    text := fmt.Sprintf("%.1f %s", r, unit)
    Set("lblResult", "Text", text)
    Call("lstHistory", "AddItem", fmt.Sprintf("%.1f => %s", v, text))
}
```

لاحظ أن الدالة `convert` عادية (ليست حدثًا) وترجع قيمتين كما تعلمنا في الدرس 6. وقيمة الخاصية `Checked` تصل كنص `"True"` أو `"False"`.

> **نصيحة للتصحيح:** ضع نقطة توقف (F9) داخل `btnConvert_Click` وشغّل بـ **F5**؛ عند الضغط على الزر يتوقف البرنامج وترى قيم `v` و`toF` في نافذة **Locals** (المتغيرات المحلية).

## أحداث مفيدة

| الحدث | متى يحدث |
|---|---|
| `Form1_Load` | ظهور النموذج |
| `btnX_Click` | الضغط على زر |
| `txtX_TextChanged` | تغير نص مربع النص |
| `chkX_CheckedChanged` | تغير مربع الاختيار |
| `lstX_SelectedIndexChanged` | اختيار عنصر من القائمة |
| `tmrX_Tick` | كل فترة من المؤقت `Timer` |

## أخطاء شائعة

- **الاسم في الكود لا يطابق Name:** `Get("txtname", ...)` لا تجد `txtName`.
- **كتابة `func main()` في مشروع النوافذ:** خطأ `main redeclared`، لأن الـ IDE تولدها.
- **`fmt.Println` في مشروع النوافذ:** يربك الاتصال بالـ IDE؛ استخدم `log.Println`.
- **نسيان `package main`** في أول الملف.

## تمرين

### التمرين 1

أضف زرًا `btnClear` يمسح القائمة `lstHistory` بالدالة `Clear` ويفرغ `lblResult`:

```go form exercise
package main

func btnClear_Click(e RadEvent) {
    // اكتب الكود هنا
}
```

<!-- test: {"items": {"lstHistory": ["a", "b"]}, "set": {"lblResult.Text": "x"}, "events": ["btnClear Click"], "expect": {"lstHistory.ListCount": "0", "lblResult.Text": ""}} -->
```go form solution
package main

func btnClear_Click(e RadEvent) {
    Call("lstHistory", "Clear")
    Set("lblResult", "Text", "")
}
```

## اختبر نفسك

```quiz
{"question": "ما الشكل الصحيح لمعالج الضغط على زر اسمه btnSave في Go؟", "choices": ["func Save_Click()", "func btnSave_Click(e RadEvent)", "func (btnSave) Click()", "func click(btnSave)"], "answer": 1, "explanation": "اسم الأداة ثم _ ثم الحدث، ومعامل اختياري من نوع RadEvent."}
```

```quiz
{"question": "كيف تكتب رسالة تتبع تظهر في نافذة Output من مشروع نوافذ Go؟", "choices": ["fmt.Println", "log.Println", "MsgBox", "Set"], "answer": 1, "explanation": "log.Println تكتب في stderr الذي تعرضه الـ IDE، دون أن تربك بروتوكول الجسر."}
```

## الخلاصة

- مشروع **Windows Application** في **Go (GUI Bridge)**: ارسم ثم اكتب `func اسمالأداة_الحدث(e RadEvent)`.
- `Get` و`Set` و`Call` و`MsgBox` و`Input` للتعامل مع الأدوات.
- لا `main` في مشروع النوافذ، و`log.Println` للتتبع.
