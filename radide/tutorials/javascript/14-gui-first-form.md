# الدرس 14: أول نافذة بـ JavaScript في مصمم النماذج

**في هذا الدرس ستتعلم:**

- إنشاء مشروع **Windows Application** بلغة JavaScript.
- رسم **النموذج** (form) بالأدوات من **Toolbox**، وضبط خصائصها من **Properties**.
- كتابة **معالج الحدث** (event handler) مثل `btnHello_Click`.
- قراءة الخصائص وتغييرها بـ `ui.txtName.Text` و`get` و`set`.
- صناديق الرسائل `msgbox` و`input`.

## كيف تعمل النوافذ مع JavaScript في RAD IDE؟

Node.js لا يملك نوافذ وأزرارًا بنفسه. لذلك تستخدم RAD IDE فكرة اسمها **GUI Bridge** (جسر الواجهة الرسومية):

- **الـ IDE ترسم النافذة** التي صممتها في مصمم النماذج، بالأدوات نفسها التي تعرفها من Visual Basic.
- **برنامجك بلغة JavaScript** يعمل في Node.js، وعندما يضغط المستخدم زرًا يصله **حدث** (event)، فيُنفَّذ الدالة المناسبة.
- برنامجك يقرأ الخصائص ويغيّرها (نص خانة، عنوان تسمية...) برسائل قصيرة عبر الجسر.

> **تشبيه:** النافذة مثل **لوحة التحكم** في غرفة الأجهزة، وبرنامجك هو **المهندس** في الغرفة المجاورة. كل ضغطة زر على اللوحة تصل للمهندس كرسالة، فيقرر ماذا يفعل ويرسل أوامره: «اكتب على الشاشة كذا».

## الخطوة 1: إنشاء المشروع

1. **File > New Project** (ملف > مشروع جديد...) أو `Ctrl+Shift+N`.
2. اختر **Web & Script > JavaScript**.
3. من **Template:** اختر **Windows Application** (تطبيق Windows)، وسمِّ المشروع `HelloForm` ثم **OK**.

يفتح **المصمم** (Designer) وفيه نافذة فارغة اسمها `Form1`. ملفات المشروع:

| الملف | ما فيه |
|---|---|
| `Form1.form` | تصميم النافذة (الأدوات وأماكنها وخصائصها) بصيغة JSON |
| `Form1.js` | **كودك**: معالجات الأحداث |
| `project.radproj` | إعدادات المشروع |

## الخطوة 2: رسم الواجهة

من **Toolbox** (صندوق الأدوات) اسحب إلى النافذة هذه **الأدوات** (عناصر التحكم)، ثم غيّر خصائصها من نافذة **Properties** (الخصائص):

| الأداة | Name | Text |
|---|---|---|
| Label | `lblTitle` | `اكتب اسمك:` |
| TextBox | `txtName` | (فارغ) |
| Button | `btnHello` | `قل مرحبًا` |
| Label | `lblOut` | (فارغ) |

> **عادة جيدة:** سمِّ كل أداة باسم يبدأ ببادئة تدل على نوعها: `btn` للزر، و`txt` لخانة النص، و`lbl` للتسمية، و`lst` للقائمة، و`chk` لمربع الاختيار. هكذا تعرف نوع الأداة من اسمها في الكود.

## الخطوة 3: معالج الحدث

انقر نقرًا مزدوجًا على الزر `btnHello` في المصمم. تنتقل RAD IDE إلى الملف `Form1.js` (أو اضغط `F7`، **View > Code**) وتنشئ لك دالة فارغة:

```js
function btnHello_Click(e) {

}
```

اسم الدالة هو المهم: **اسم_الأداة** ثم `_` ثم **اسم_الحدث**. عندما يضغط المستخدم الزر `btnHello` يُرسَل الحدث `Click` فتُنفَّذ الدالة `btnHello_Click`. اكتب داخلها:

<!-- test: {"controls": [["Label", "lblTitle", {"Text": "اكتب اسمك:"}], ["TextBox", "txtName"], ["Button", "btnHello", {"Text": "قل مرحبًا"}], ["Label", "lblOut"]], "form": {"Text": "تطبيق الترحيب"}, "steps": [["set", "txtName", "Text", "سارة"], ["click", "btnHello"]], "expect": {"lblOut.Text": "مرحبًا يا سارة!"}} -->
```js form run
function btnHello_Click(e) {
    const name = ui.txtName.Text;
    ui.lblOut.Text = `مرحبًا يا ${name}!`;
}
```

اضغط `F5` (**Debug > Start Debugging / Continue**)، واكتب اسمك في الخانة، ثم اضغط الزر. أو اضغط «جرّبه» على المثال فتنشئ RAD IDE المشروع بالأدوات وتشغّله.

- `ui.txtName.Text` **تقرأ** النص المكتوب في الخانة `txtName`.
- `ui.lblOut.Text = ...` **تغيّر** نص التسمية `lblOut`.

## الحدث `Form1_Load`

`Form1_Load` يُنفَّذ مرة واحدة عند ظهور النافذة، ومكانه المناسب لتجهيز القيم الأولى:

<!-- test: {"controls": [["Label", "lblClock"], ["Label", "lblCount"], ["Button", "btnCount", {"Text": "اضغطني"}]], "steps": [["click", "btnCount"], ["click", "btnCount"], ["click", "btnCount"]], "expect": {"lblCount.Text": "عدد الضغطات: 3", "lblClock.Text": "مرحبًا! اضغط الزر", "Form1.Caption": "عدّاد الضغطات"}} -->
```js form run
let clicks = 0;            // متغير عام: يحتفظ بقيمته بين الأحداث

function Form1_Load(e) {
    ui.Form1.Caption = "عدّاد الضغطات";
    ui.lblClock.Text = "مرحبًا! اضغط الزر";
    ui.lblCount.Text = "عدد الضغطات: 0";
}

function btnCount_Click(e) {
    clicks++;
    ui.lblCount.Text = `عدد الضغطات: ${clicks}`;
}
```

- `ui.Form1.Caption` عنوان النافذة نفسها (في نافذة الخصائص اسمه `Text`، وفي الكود `Caption` كما في Visual Basic 6).
- المتغير `clicks` معرَّف **خارج** الدوال، فيبقى موجودًا طوال عمل البرنامج ويحتفظ بقيمته بين ضغطة وأخرى. لو عرّفناه داخل `btnCount_Click` لعاد إلى الصفر مع كل ضغطة.

## ثلاث طرق للوصول إلى الخصائص

كلها تفعل الشيء نفسه، فاختر الأوضح لك:

| الطريقة | القراءة | الكتابة |
|---|---|---|
| الكائن `ui` | `ui.txtA.Text` | `ui.lblOut.Text = "Hi"` |
| الدالتان `get` و`set` | `get("txtA", "Text")` | `set("lblOut", "Text", "Hi")` |
| قراءة عدد مباشرة | `getNum("txtA", "Text")` | |

انتبه: كل ما يُقرأ من النافذة يصل **نصًا**. لقراءة عدد استخدم `getNum` أو `Number(ui.txtA.Text)`.

### مثال: آلة جمع

<!-- test: {"controls": [["TextBox", "txtA"], ["TextBox", "txtB"], ["Button", "btnAdd", {"Text": "اجمع"}], ["Label", "lblResult"]], "steps": [["set", "txtA", "Text", "12.5"], ["set", "txtB", "Text", "7.5"], ["click", "btnAdd"]], "expect": {"lblResult.Text": "المجموع = 20"}} -->
```js form run
function btnAdd_Click(e) {
    const a = getNum("txtA", "Text");
    const b = getNum("txtB", "Text");
    set("lblResult", "Text", `المجموع = ${a + b}`);
}
```

## صناديق الرسائل: `msgbox` و`input`

- `msgbox(نص)` تعرض رسالة في نافذة صغيرة وتنتظر حتى يضغط المستخدم **OK**.
- `input(سؤال)` تسأل المستخدم وترجع ما كتبه نصًا.

<!-- test: {"controls": [["Button", "btnAsk", {"Text": "ابدأ"}], ["Label", "lblOut"]], "inputs": ["خالد", "30"], "steps": [["click", "btnAsk"]], "msgbox": ["أهلًا يا خالد، عمرك بالأيام تقريبًا 10950"], "expect": {"lblOut.Text": "خالد (30)"}} -->
```js form run
function btnAsk_Click(e) {
    const name = input("ما اسمك؟");
    const age = Number(input("كم عمرك؟"));
    if (!name || Number.isNaN(age)) {
        msgbox("لم تكتب بيانات صحيحة");
        return;
    }
    msgbox(`أهلًا يا ${name}، عمرك بالأيام تقريبًا ${age * 365}`);
    ui.lblOut.Text = `${name} (${age})`;
}
```

## `console.log` في برامج النوافذ

`console.log` تعمل أيضًا، ويظهر ناتجها في نافذة **Output** (المخرجات) في RAD IDE. استخدمها لتتبّع ما يحدث أثناء التجربة، فالمستخدم لا يراها:

<!-- test: {"controls": [["Button", "btnGo", {"Text": "Go"}]], "steps": [["click", "btnGo"], ["click", "btnGo"]]} -->
```js form run
let n = 0;
function btnGo_Click(e) {
    n++;
    console.log("ضُغط الزر، المرة رقم", n);
}
```

```text output
ضُغط الزر، المرة رقم 1
ضُغط الزر، المرة رقم 2
```

## إنهاء البرنامج

الدالة `end()` تغلق البرنامج كله، مثل `End` في Visual Basic. مثلًا زر خروج:

```js
function btnExit_Click(e) {
    end();
}
```

## أخطاء شائعة

- **اسم الدالة لا يطابق اسم الأداة:** إن غيّرت `Name` الزر إلى `btnSave` بعد إنشاء `btnHello_Click` فلن تُستدعى الدالة. غيّر اسم الدالة أيضًا، أو انقر مرتين على الزر من جديد.
- **نسيان أن القيم نصوص:** `ui.txtA.Text + ui.txtB.Text` تعطي `"57"` إذا كتب المستخدم `5` و`7`. استخدم `getNum`.
- **خطأ في اسم الأداة:** `ui.txtNmae.Text` باسم غير موجود يظهر في نافذة **Output** كرسالة `unknown object 'txtNmae'` وترجع قيمة فارغة.
- **دوال `async` في الأحداث:** معالجات الأحداث يجب أن تكون عادية (متزامنة). إن كتبت `async function btnGo_Click` تظهر رسالة تحذير في Output لأن الجسر لا ينتظرها.

## تمارين

### التمرين 1

نافذة فيها خانة `txtC` لدرجة الحرارة المئوية، وزر `btnConvert`، وتسمية `lblF`. عند الضغط تُكتب الدرجة بالفهرنهايت في التسمية بالشكل `77 فهرنهايت`.

```js form exercise
function btnConvert_Click(e) {
    // اقرأ txtC واكتب الناتج في lblF
}
```

<!-- test: {"controls": [["TextBox", "txtC"], ["Button", "btnConvert", {"Text": "حوّل"}], ["Label", "lblF"]], "steps": [["set", "txtC", "Text", "25"], ["click", "btnConvert"]], "expect": {"lblF.Text": "77 فهرنهايت"}} -->
```js form solution
function btnConvert_Click(e) {
    const c = getNum("txtC", "Text");
    ui.lblF.Text = `${c * 9 / 5 + 32} فهرنهايت`;
}
```

### التمرين 2

زران `btnPlus` و`btnMinus` وتسمية `lblValue` تبدأ من `0` عند تحميل النافذة. كل ضغطة على `btnPlus` تزيد القيمة 1، وعلى `btnMinus` تنقصها 1، لكن لا تنزل تحت الصفر.

```js form exercise
let value = 0;

function Form1_Load(e) {
    // اكتب 0 في lblValue
}

// function btnPlus_Click(e) { ... }
// function btnMinus_Click(e) { ... }
```

<!-- test: {"controls": [["Button", "btnPlus", {"Text": "+"}], ["Button", "btnMinus", {"Text": "-"}], ["Label", "lblValue"]], "steps": [["click", "btnPlus"], ["click", "btnPlus"], ["click", "btnMinus"], ["click", "btnMinus"], ["click", "btnMinus"], ["click", "btnPlus"]], "expect": {"lblValue.Text": "1"}} -->
```js form solution
let value = 0;

function Form1_Load(e) {
    ui.lblValue.Text = value;
}

function btnPlus_Click(e) {
    value++;
    ui.lblValue.Text = value;
}

function btnMinus_Click(e) {
    if (value > 0) value--;
    ui.lblValue.Text = value;
}
```

## اختبر نفسك

```quiz
{"question": "متى تُنفَّذ الدالة `btnSave_Click`؟", "choices": ["عند بدء البرنامج", "عندما يضغط المستخدم الأداة التي اسمها `btnSave`", "كل ثانية", "عند إغلاق النافذة"], "answer": 1, "explanation": "اسم المعالج = اسم الأداة + `_` + اسم الحدث، والحدث هنا `Click`."}
```

```quiz
{"question": "كتب المستخدم `4` في `txtA` و`6` في `txtB`. ما ناتج `ui.txtA.Text + ui.txtB.Text`؟", "choices": ["10", "\"46\"", "NaN", "خطأ"], "answer": 1, "explanation": "الخصائص تصل نصوصًا، و`+` بين نصين تربطهما. استخدم `getNum` للأعداد."}
```

```quiz
{"question": "أين تضع كود تجهيز النافذة قبل ظهورها؟", "choices": ["في `Form1_Load`", "في `Form1_Click`", "في أي دالة", "في ملف `Form1.form`"], "answer": 0, "explanation": "`Form1_Load` يُنفَّذ مرة واحدة عند تحميل النافذة."}
```

```quiz
{"question": "لماذا عرّفنا `let clicks = 0;` خارج الدوال؟", "choices": ["لأن ذلك أسرع", "لكي تبقى قيمته محفوظة بين الأحداث", "لأن المتغيرات لا تُعرَّف داخل الدوال", "لا سبب"], "answer": 1, "explanation": "المتغير داخل الدالة يُنشأ من جديد مع كل استدعاء، أما العام فيبقى."}
```

## الخلاصة

- **Windows Application** بلغة JavaScript: الـ IDE ترسم النافذة، وكودك في `Form1.js` يستقبل الأحداث عبر GUI Bridge.
- معالج الحدث: `function اسمالأداة_اسمالحدث(e) { ... }`، و`Form1_Load` للتجهيز.
- `ui.txtA.Text` و`get` و`set` و`getNum` للخصائص، و`msgbox` و`input` للحوار، و`end()` للإنهاء.
- المتغيرات العامة تحفظ الحالة بين الأحداث.
