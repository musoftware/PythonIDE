# الدرس 15: الأدوات والأحداث: القوائم والاختيارات والمؤقت

**في هذا الدرس ستتعلم:**

- القائمة **ListBox**: الإضافة والحذف والاختيار.
- القائمة المنسدلة **ComboBox**.
- مربع الاختيار **CheckBox** وزر الخيار **RadioButton**.
- المؤقت **Timer** والحدث `Tick`.
- أحداث أخرى مثل `TextChanged` و`SelectedIndexChanged`.

## القائمة ListBox

**ListBox** تعرض قائمة عناصر يختار منها المستخدم. أهم ما تحتاجه منها:

| الكود | معناه |
|---|---|
| `ui.lstNames.AddItem("نص")` | إضافة عنصر في آخر القائمة |
| `ui.lstNames.RemoveItem(i)` | حذف العنصر رقم `i` (الترقيم من 0) |
| `ui.lstNames.Clear()` | حذف كل العناصر |
| `getNum("lstNames", "ListCount")` | عدد العناصر |
| `getNum("lstNames", "ListIndex")` | رقم العنصر المختار (`-1` إن لم يُختر شيء) |
| `ui.lstNames.Text` | نص العنصر المختار |
| `call("lstNames", "List", i)` | نص العنصر رقم `i` |

مثال: قائمة أسماء نضيف إليها ونحذف منها:

<!-- test: {"controls": [["TextBox", "txtName"], ["Button", "btnAdd", {"Text": "أضف"}], ["Button", "btnRemove", {"Text": "احذف المختار"}], ["ListBox", "lstNames"], ["Label", "lblCount"]], "steps": [["set", "txtName", "Text", "سارة"], ["click", "btnAdd"], ["set", "txtName", "Text", "  "], ["click", "btnAdd"], ["set", "txtName", "Text", "علي"], ["click", "btnAdd"], ["set", "txtName", "Text", "منى"], ["click", "btnAdd"], ["set", "lstNames", "ListIndex", "1"], ["click", "btnRemove"]], "msgbox": ["اكتب اسمًا أولًا"], "expect": {"lstNames.ListCount": "2", "lstNames.List(1)": "منى", "lblCount.Text": "العدد: 2", "txtName.Text": ""}} -->
```js form run
function updateCount() {
    ui.lblCount.Text = `العدد: ${getNum("lstNames", "ListCount")}`;
}

function Form1_Load(e) {
    updateCount();
}

function btnAdd_Click(e) {
    const name = ui.txtName.Text.trim();
    if (name === "") {
        msgbox("اكتب اسمًا أولًا");
        return;
    }
    ui.lstNames.AddItem(name);
    ui.txtName.Text = "";
    updateCount();
}

function btnRemove_Click(e) {
    const i = getNum("lstNames", "ListIndex");
    if (i < 0) {
        msgbox("اختر اسمًا من القائمة");
        return;
    }
    ui.lstNames.RemoveItem(i);
    updateCount();
}
```

لاحظ الدالة `updateCount`: ليست معالج حدث، بل دالة مساعدة عادية نستدعيها من أكثر من مكان. هذا يمنع تكرار الكود.

## الحدث `SelectedIndexChanged`

يُنفَّذ عندما يختار المستخدم عنصرًا آخر في القائمة:

<!-- test: {"controls": [["ListBox", "lstCities"], ["Label", "lblInfo"]], "steps": [["set", "lstCities", "ListIndex", "2"], ["event", "lstCities", "SelectedIndexChanged"]], "expect": {"lblInfo.Text": "أسوان: عدد السكان تقريبًا 1.6 مليون"}} -->
```js form run
const cities = [
    { name: "القاهرة", people: 10.1 },
    { name: "الإسكندرية", people: 5.4 },
    { name: "أسوان", people: 1.6 },
];

function Form1_Load(e) {
    for (const c of cities) {
        ui.lstCities.AddItem(c.name);
    }
}

function lstCities_SelectedIndexChanged(e) {
    const i = getNum("lstCities", "ListIndex");
    if (i < 0) return;
    const c = cities[i];
    ui.lblInfo.Text = `${c.name}: عدد السكان تقريبًا ${c.people} مليون`;
}
```

هنا نحفظ البيانات الكاملة في مصفوفة كائنات، والقائمة تعرض الأسماء فقط. رقم العنصر المختار في القائمة هو نفسه فهرسه في المصفوفة.

## القائمة المنسدلة ComboBox

تشبه ListBox لكنها تأخذ سطرًا واحدًا وتنسدل عند الضغط. تستخدم الدوال نفسها: `AddItem` و`ListIndex` و`Text`:

<!-- test: {"controls": [["ComboBox", "cboSize"], ["Button", "btnOrder", {"Text": "اطلب"}], ["Label", "lblPrice"]], "steps": [["set", "cboSize", "ListIndex", "1"], ["click", "btnOrder"]], "expect": {"lblPrice.Text": "قهوة وسط: 35 جنيهًا", "cboSize.ListCount": "3"}} -->
```js form run
const prices = { "صغير": 25, "وسط": 35, "كبير": 45 };

function Form1_Load(e) {
    for (const size of Object.keys(prices)) {
        ui.cboSize.AddItem(size);
    }
    set("cboSize", "ListIndex", 0);
}

function btnOrder_Click(e) {
    const size = ui.cboSize.Text;
    ui.lblPrice.Text = `قهوة ${size}: ${prices[size]} جنيهًا`;
}
```

## مربع الاختيار CheckBox وزر الخيار RadioButton

- **CheckBox** خيار مستقل: يمكن تحديد أكثر من واحد. قيمته في الكود `Value`: `1` إن كان محددًا، و`0` إن لم يكن.
- **RadioButton** مجموعة خيارات لا يُحدَّد منها إلا **واحد** فقط. قيمته `Value`: `True` أو `False`.

في نافذة الخصائص اسم الخاصية `Checked`، أما في الكود فنقرأ `Value` كما في Visual Basic 6.

<!-- test: {"controls": [["RadioButton", "optSmall", {"Text": "بيتزا صغيرة (80)"}], ["RadioButton", "optLarge", {"Text": "بيتزا كبيرة (130)"}], ["CheckBox", "chkCheese", {"Text": "جبنة إضافية (+20)"}], ["CheckBox", "chkDelivery", {"Text": "توصيل (+15)"}], ["Button", "btnTotal", {"Text": "احسب"}], ["Label", "lblTotal"]], "steps": [["set", "optLarge", "Value", "True"], ["set", "chkCheese", "Value", "1"], ["click", "btnTotal"]], "expect": {"lblTotal.Text": "الإجمالي: 150 جنيهًا"}} -->
```js form run
function Form1_Load(e) {
    set("optSmall", "Value", true);
}

function btnTotal_Click(e) {
    let total = get("optLarge", "Value") === "True" ? 130 : 80;
    if (getNum("chkCheese", "Value") === 1) total += 20;
    if (getNum("chkDelivery", "Value") === 1) total += 15;
    ui.lblTotal.Text = `الإجمالي: ${total} جنيهًا`;
}
```

- `set("optSmall", "Value", true)` تحدد الخيار الصغير عند البداية. القيمة المنطقية `true` تُرسَل كـ `True`.
- القيم تصل نصوصًا: لذلك نقارن `get(...) === "True"`، أو نقرأ العدد بـ `getNum`.

## الحدث `TextChanged`

يُنفَّذ مع كل حرف يكتبه المستخدم في الخانة، فيصلح للتحقق الفوري:

<!-- test: {"controls": [["TextBox", "txtPassword"], ["Label", "lblStrength"]], "steps": [["set", "txtPassword", "Text", "abc"], ["event", "txtPassword", "TextChanged"], ["set", "txtPassword", "Text", "Abc12345"], ["event", "txtPassword", "TextChanged"]], "expect": {"lblStrength.Text": "قوية"}} -->
```js form run
function txtPassword_TextChanged(e) {
    const p = ui.txtPassword.Text;
    let strength = "ضعيفة";
    if (p.length >= 8 && /[0-9]/.test(p) && /[A-Z]/.test(p)) {
        strength = "قوية";
    } else if (p.length >= 6) {
        strength = "متوسطة";
    }
    ui.lblStrength.Text = strength;
}
```

`/[0-9]/.test(p)` **تعبير نمطي** (regular expression) يسأل: هل في النص رقم؟ و`/[A-Z]/` يسأل عن حرف إنجليزي كبير.

## المؤقت Timer

**Timer** أداة غير مرئية (تظهر أسفل النافذة في المصمم، في منطقة المكونات). تنفّذ الحدث `Tick` كل فترة:

- `Interval`: المدة بين كل `Tick` والذي يليه بالملي ثانية (`1000` = ثانية).
- `Enabled`: `true` للتشغيل و`false` للإيقاف.

مثال: ساعة إيقاف بسيطة:

<!-- test: {"controls": [["Label", "lblTime"], ["Button", "btnStart", {"Text": "ابدأ"}], ["Button", "btnStop", {"Text": "قف"}], ["Timer", "tmrClock", {"Interval": 100000, "Enabled": false}]], "steps": [["click", "btnStart"], ["tick", "tmrClock"], ["tick", "tmrClock"], ["tick", "tmrClock"], ["click", "btnStop"]], "expect": {"lblTime.Text": "00:03", "tmrClock.Enabled": "False"}} -->
```js form run
let seconds = 0;

function show() {
    const m = String(Math.floor(seconds / 60)).padStart(2, "0");
    const s = String(seconds % 60).padStart(2, "0");
    ui.lblTime.Text = `${m}:${s}`;
}

function Form1_Load(e) {
    set("tmrClock", "Interval", 1000);
    show();
}

function btnStart_Click(e) {
    set("tmrClock", "Enabled", true);
}

function btnStop_Click(e) {
    set("tmrClock", "Enabled", false);
}

function tmrClock_Tick(e) {
    seconds++;
    show();
}
```

> **لماذا لا نستخدم `setInterval`؟** في برامج النوافذ ينتظر برنامجك الأحداث القادمة من الـ IDE، فلا تُنفَّذ دوال `setTimeout` و`setInterval` في الوقت المتوقع. استخدم أداة **Timer** دائمًا للأعمال الدورية في النوافذ.

## إظهار الأدوات وإخفاؤها وتعطيلها

كل أداة لها الخاصيتان `Visible` (ظاهرة أم مخفية) و`Enabled` (مفعّلة أم معطّلة):

<!-- test: {"controls": [["CheckBox", "chkAgree", {"Text": "أوافق على الشروط"}], ["Button", "btnNext", {"Text": "التالي"}], ["Label", "lblHint"]], "steps": [["set", "chkAgree", "Value", "1"], ["event", "chkAgree", "CheckedChanged"]], "expect": {"btnNext.Enabled": "True", "lblHint.Visible": "False"}} -->
```js form run
function Form1_Load(e) {
    set("btnNext", "Enabled", false);
    ui.lblHint.Text = "يجب الموافقة على الشروط أولًا";
}

function chkAgree_CheckedChanged(e) {
    const agreed = getNum("chkAgree", "Value") === 1;
    set("btnNext", "Enabled", agreed);
    set("lblHint", "Visible", !agreed);
}
```

## أخطاء شائعة

- **نسيان أن الترقيم يبدأ من 0:** العنصر الأول في القائمة رقمه `0`، و`ListIndex` تساوي `-1` إن لم يُختر شيء. افحصها قبل الحذف.
- **مقارنة `Value` بقيمة منطقية:** `get("optA", "Value") === true` دائمًا `false` لأن القيمة تصل نصًا `"True"`.
- **نسيان تشغيل المؤقت:** إن كانت `Enabled` في نافذة الخصائص `False` فلن يحدث `Tick` حتى تكتب `set("tmrX", "Enabled", true)`.
- **عمل ثقيل داخل `Tick`:** الكود الطويل داخل المؤقت يجعل النافذة بطيئة الاستجابة. اجعله قصيرًا.

## تمارين

### التمرين 1

قائمة مشتريات: خانة `txtItem` وزر `btnAdd` يضيف العنصر إلى `lstItems` (إن لم يكن فارغًا)، وزر `btnClear` يمسح القائمة كلها، وتسمية `lblCount` تعرض `3 عناصر` مثلًا بعد كل عملية.

```js form exercise
function btnAdd_Click(e) {
    // ...
}

function btnClear_Click(e) {
    // ...
}
```

<!-- test: {"controls": [["TextBox", "txtItem"], ["Button", "btnAdd", {"Text": "أضف"}], ["Button", "btnClear", {"Text": "امسح"}], ["ListBox", "lstItems"], ["Label", "lblCount"]], "steps": [["set", "txtItem", "Text", "خبز"], ["click", "btnAdd"], ["set", "txtItem", "Text", "لبن"], ["click", "btnAdd"], ["set", "txtItem", "Text", ""], ["click", "btnAdd"], ["click", "btnClear"], ["set", "txtItem", "Text", "جبن"], ["click", "btnAdd"], ["set", "txtItem", "Text", "شاي"], ["click", "btnAdd"], ["set", "txtItem", "Text", "سكر"], ["click", "btnAdd"]], "expect": {"lstItems.ListCount": "3", "lstItems.List(0)": "جبن", "lblCount.Text": "3 عناصر"}} -->
```js form solution
function showCount() {
    ui.lblCount.Text = `${getNum("lstItems", "ListCount")} عناصر`;
}

function btnAdd_Click(e) {
    const item = ui.txtItem.Text.trim();
    if (item === "") return;
    ui.lstItems.AddItem(item);
    ui.txtItem.Text = "";
    showCount();
}

function btnClear_Click(e) {
    ui.lstItems.Clear();
    showCount();
}
```

### التمرين 2

عدّاد تنازلي: عند الضغط على `btnGo` تبدأ التسمية `lblLeft` من `5` وينقص المؤقت `tmrDown` العدد كل ثانية، وعندما يصل إلى `0` يكتب «انطلق!» ويتوقف المؤقت.

```js form exercise
let left = 5;

function btnGo_Click(e) {
    // ...
}

function tmrDown_Tick(e) {
    // ...
}
```

<!-- test: {"controls": [["Label", "lblLeft"], ["Button", "btnGo", {"Text": "ابدأ"}], ["Timer", "tmrDown", {"Interval": 100000, "Enabled": false}]], "steps": [["click", "btnGo"], ["tick", "tmrDown"], ["tick", "tmrDown"], ["tick", "tmrDown"], ["tick", "tmrDown"], ["tick", "tmrDown"]], "expect": {"lblLeft.Text": "انطلق!", "tmrDown.Enabled": "False"}} -->
```js form solution
let left = 5;

function btnGo_Click(e) {
    left = 5;
    ui.lblLeft.Text = left;
    set("tmrDown", "Interval", 1000);
    set("tmrDown", "Enabled", true);
}

function tmrDown_Tick(e) {
    left--;
    if (left <= 0) {
        set("tmrDown", "Enabled", false);
        ui.lblLeft.Text = "انطلق!";
    } else {
        ui.lblLeft.Text = left;
    }
}
```

## اختبر نفسك

```quiz
{"question": "ما قيمة `ListIndex` عندما لا يكون أي عنصر مختارًا؟", "choices": ["0", "-1", "null", "1"], "answer": 1, "explanation": "`-1` تعني لا يوجد اختيار، والعنصر الأول رقمه 0."}
```

```quiz
{"question": "أي أداة تسمح باختيار خيار واحد فقط من مجموعة؟", "choices": ["CheckBox", "RadioButton", "ListBox", "Timer"], "answer": 1, "explanation": "أزرار الخيار RadioButton في المجموعة الواحدة لا يُحدَّد منها إلا واحد."}
```

```quiz
{"question": "كيف تجعل المؤقت `tmrX` ينفّذ `Tick` كل نصف ثانية؟", "choices": ["`set(\"tmrX\", \"Interval\", 500)`", "`set(\"tmrX\", \"Interval\", 0.5)`", "`setInterval(500)`", "`ui.tmrX.Tick(500)`"], "answer": 0, "explanation": "`Interval` بالملي ثانية، ونصف الثانية 500 ملي ثانية. ولا تنسَ `Enabled = true`."}
```

## الخلاصة

- ListBox وComboBox: `AddItem` و`RemoveItem` و`Clear` و`ListCount` و`ListIndex` و`Text`، والحدث `SelectedIndexChanged`.
- CheckBox قيمته `1/0`، وRadioButton قيمته `True/False`، عبر الخاصية `Value`.
- Timer: `Interval` و`Enabled` والحدث `Tick`، وهو البديل الصحيح لـ `setInterval` في النوافذ.
- `Visible` و`Enabled` لإظهار الأدوات وتفعيلها، و`TextChanged` للتحقق الفوري.
