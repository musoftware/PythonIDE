# الدرس 15: نافذة رسومية بـ Rust في مصمم النماذج

كل برامجنا حتى الآن كانت في الطرفية. اليوم نرسم **نافذة** حقيقية بأزرار ومربعات نص في **مصمم النماذج**، تمامًا كما في Visual Basic، ونكتب منطقها بلغة Rust.

## الفكرة: GUI Bridge

1. **الـ IDE ترسم النافذة** التي صممتها بالسحب والإفلات.
2. **برنامج Rust** يعمل في الخلفية وينتظر **الأحداث**.
3. عند الضغط على زر اسمه `btnHello` تستدعي الـ IDE في برنامجك الدالة `btnHello_Click`.
4. داخل الدالة تقرأ وتغير الأدوات بدوال جاهزة من الوحدة `radgui`: `get` و`set` و`call` و`msgbox`.

> **تشبيه:** النافذة مثل **لوحة تحكم المصعد**، وبرنامجك هو **المحرك** في الأسفل. عندما يضغط أحد زر «الدور 3» تصل إشارة للمحرك فيتحرك، ثم يرسل إشارة للوحة لتضيء الرقم 3.

الـ IDE تولّد بنفسها الملف `_radmain.rs` الذي فيه `fn main()` وحلقة الأحداث، وتنسخ `radgui.rs`، وتدير جداول `[[bin]]` في `Cargo.toml`. لذلك **لا تكتب `main`** في مشروع النوافذ.

## دوال التعامل مع الأدوات

| الدالة | وظيفتها | مثال |
|---|---|---|
| `get(أداة, خاصية) -> String` | تقرأ خاصية كنص | `get("txtName", "Text")` |
| `get_num(أداة, خاصية) -> f64` | تقرأ خاصية كرقم | `get_num("txtAge", "Text")` |
| `set(أداة, خاصية, قيمة)` | تغير خاصية (نص أو رقم) | `set("lblOut", "Text", "مرحبًا")` |
| `call(أداة, دالة, &[وسائط])` | تستدعي دالة في الأداة | `call("lstLog", "AddItem", &["سطر"])` |
| `msgbox(نص)` | رسالة منبثقة | `msgbox("تم الحفظ")` |
| `input(سؤال) -> String` | مربع إدخال | `input("ما اسمك؟")` |
| `print(نص)` | سطر في نافذة **Output** | `print("وصلنا هنا")` |
| `show(نموذج)` / `hide(نموذج)` | إظهار وإخفاء النماذج | `show("Form2")` |
| `end()` | إنهاء البرنامج | |

> **مهم:** لا تستخدم `println!` في مشروع النوافذ، لأن البرنامج يتحدث مع الـ IDE عبر الإخراج القياسي. استخدم `print(...)` أو `eprintln!` فتظهر رسالتك في نافذة **Output** (المخرجات).

## مشروعك الأول: برنامج الترحيب

### 1) إنشاء المشروع

1. **File > New Project...** (ملف ← مشروع جديد...).
2. **Native** > **Rust (Cargo)** ← القالب **GUI App (RAD form)**. (أو **Native** > **Rust (GUI Bridge, cargo)** > **Windows Application**.)
3. سمّ المشروع `HelloForm`. يفتح **Form1** في وضع التصميم، ومعه ملف الكود `Form1.rs`.

### 2) رسم النافذة

من **Toolbox** (صندوق الأدوات) اسحب الأدوات إلى النموذج، وغيّر **Name** و**Text** من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtName` | (فارغ) |
| `Button` | `btnHello` | `رحّب بي` |
| `Label` | `lblOut` | (فارغ) |

### 3) كتابة الكود

انقر مرتين على الزر في المصمم، فتنشئ الـ IDE الدالة `btnHello_Click` في `Form1.rs` وتنقلك إليها:

<!-- test: {"set": {"txtName.Text": "Mona"}, "events": ["btnHello Click"], "expect": {"lblOut.Text": "أهلًا يا Mona!"}} -->
```rust form run
use crate::radgui::*;

// تعمل مرة واحدة عند ظهور النافذة
pub fn Form1_Load() {
    set("lblOut", "Text", "اكتب اسمك ثم اضغط الزر");
}

// تعمل عند الضغط على الزر
pub fn btnHello_Click() {
    let name = get("txtName", "Text");
    let name = name.trim();
    if name.is_empty() {
        set("lblOut", "Text", "من فضلك اكتب اسمك أولًا");
        return;
    }
    set("lblOut", "Text", format!("أهلًا يا {name}!"));
    print(format!("رحبنا بـ {name}"));        // يظهر في نافذة Output
}
```

### 4) التشغيل

اضغط **F5**: تترجم الـ IDE المشروع بـ `cargo build` (أول مرة تأخذ ثواني أطول)، ثم تظهر النافذة. اكتب اسمك واضغط الزر.

قواعد ربط الأحداث:

- اسم الدالة **`اسمالأداة_اسمالحدث`** بالضبط، مثل `btnHello_Click`، وهي `pub fn` **بلا معاملات**.
- تفاصيل الحدث (موقع الماوس، المفتاح المضغوط) تقرؤها بـ `event_arg(i)`: 0 = X، 1 = Y، 2 = زر الماوس، 3 = رمز المفتاح.
- المترجم لا يشتكي من الأسماء مثل `btnHello_Click` رغم أنها ليست بأسلوب snake_case، لأن الـ IDE تضيف `#[allow(non_snake_case)]` للوحدة.

## مثال ثانٍ: آلة حاسبة صغيرة

| الأداة | Name | Text |
|---|---|---|
| `TextBox` | `txtA` | `0` |
| `TextBox` | `txtB` | `0` |
| `ComboBox` | `cboOp` | |
| `Button` | `btnCalc` | `احسب` |
| `Label` | `lblResult` | (فارغ) |
| `ListBox` | `lstHistory` | |

<!-- test: {"set": {"txtA.Text": "6", "txtB.Text": "3"}, "events": [{"cboOp.ListIndex": "2"}, "btnCalc Click", {"txtB.Text": "0", "cboOp.ListIndex": "3"}, "btnCalc Click"], "expect": {"lblResult.Text": "لا يمكن القسمة على صفر", "lstHistory.Items": "6 × 3 = 18", "cboOp.ListCount": "4"}} -->
```rust form run
use crate::radgui::*;

fn calc(a: f64, b: f64, op: &str) -> Result<f64, String> {
    match op {
        "+" => Ok(a + b),
        "-" => Ok(a - b),
        "×" => Ok(a * b),
        "÷" if b == 0.0 => Err(String::from("لا يمكن القسمة على صفر")),
        "÷" => Ok(a / b),
        _ => Err(String::from("اختر عملية")),
    }
}

pub fn Form1_Load() {
    for op in ["+", "-", "×", "÷"] {
        call("cboOp", "AddItem", &[op]);
    }
    set("cboOp", "ListIndex", 0);
}

pub fn btnCalc_Click() {
    let a = get("txtA", "Text").trim().parse::<f64>();
    let b = get("txtB", "Text").trim().parse::<f64>();
    let (a, b) = match (a, b) {
        (Ok(a), Ok(b)) => (a, b),
        _ => {
            msgbox("اكتب رقمين صحيحين");
            return;
        }
    };
    let op = get("cboOp", "Text");
    match calc(a, b, &op) {
        Ok(r) => {
            let line = format!("{a} {op} {b} = {r}");
            set("lblResult", "Text", &line);
            call("lstHistory", "AddItem", &[line.as_str()]);
        }
        Err(e) => set("lblResult", "Text", e),
    }
}
```

لاحظ كيف نستخدم كل ما تعلمناه: `Result` و`match` مع الشروط و`parse`. الدالة `calc` عادية (ليست حدثًا)، ويمكنك اختبارها بـ `#[test]` مثل أي دالة.

> **نصيحة للتصحيح:** ضع نقطة توقف (**F9**) داخل `btnCalc_Click` وشغّل بـ **F5**. عند الضغط على الزر يتوقف البرنامج، وترى قيم `a` و`b` و`op`.

## إضافة وحدة مساعدة

**Project > Add Module...** (مشروع ← إضافة وحدة...) ثم اكتب `helpers.rs`. تضيف الـ IDE السطر `mod helpers;` في البرنامج المولّد، فتستخدم دوالها من النموذج بـ `crate::helpers::اسم_الدالة()`.

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

- **الاسم في الكود لا يطابق Name:** `get("txtname", ...)` لا تجد `txtName` (الأسماء حساسة لحالة الأحرف).
- **كتابة `fn main()` في `Form1.rs`:** لا داعي لها؛ الـ IDE تولدها في `_radmain.rs`.
- **نسيان `pub` قبل `fn btnX_Click`:** البرنامج المولّد لا يرى الدالة، فلا يحدث شيء عند الضغط (أو خطأ `function is private`).
- **`println!` في مشروع النوافذ:** يربك الاتصال بالـ IDE؛ استخدم `print(...)`.

## تمرين

### التمرين 1

أضف زرًا `btnClear` يمسح القائمة `lstHistory` بالدالة `Clear` ويفرغ `lblResult`:

```rust form exercise
use crate::radgui::*;

pub fn btnClear_Click() {
    // اكتب الكود هنا
}
```

<!-- test: {"items": {"lstHistory": ["a", "b"]}, "set": {"lblResult.Text": "x"}, "events": ["btnClear Click"], "expect": {"lstHistory.ListCount": "0", "lblResult.Text": ""}} -->
```rust form solution
use crate::radgui::*;

pub fn btnClear_Click() {
    call("lstHistory", "Clear", &[]);
    set("lblResult", "Text", "");
}
```

## اختبر نفسك

```quiz
{"question": "ما الشكل الصحيح لمعالج الضغط على زر اسمه btnSave في Rust؟", "choices": ["fn save_click()", "pub fn btnSave_Click()", "pub fn btnSave_Click(e: Event)", "impl btnSave { fn click() }"], "answer": 1, "explanation": "pub fn ثم اسم الأداة و_ والحدث، بلا معاملات."}
```

```quiz
{"question": "كيف تضيف عنصرًا إلى ListBox اسمه lstLog؟", "choices": ["set(\"lstLog\", \"Text\", x)", "call(\"lstLog\", \"AddItem\", &[x])", "lstLog.push(x)", "msgbox(x)"], "answer": 1, "explanation": "call تستدعي دالة الأداة AddItem مع الوسائط."}
```

## الخلاصة

- مشروع **GUI App (RAD form)**: ارسم النافذة ثم اكتب `pub fn اسمالأداة_الحدث()`.
- `get` و`set` و`call` و`msgbox` و`input` من `crate::radgui` للتعامل مع الأدوات.
- لا `main` في مشروع النوافذ، و`print(...)` للتتبع في نافذة **Output**.
