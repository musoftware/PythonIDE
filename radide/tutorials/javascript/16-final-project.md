# الدرس 16: المشروع النهائي: مدير المهام

حان وقت جمع كل ما تعلمته في برنامج حقيقي: **مدير مهام** بنافذة، تضيف فيه مهامك اليومية، وتعلّم المنجز منها، وتحذف ما لا تحتاجه، وتُحفظ المهام في ملف فتجدها كما هي عندما تفتح البرنامج مرة أخرى.

**ما الذي سنستخدمه؟**

- **الأصناف** (الدرس 9) لتمثيل قائمة المهام.
- **المصفوفات** و`filter` و`map` (الدرس 7).
- **JSON** والوحدة `fs` (الدرسان 8 و11) لحفظ المهام.
- **تقسيم البرنامج** إلى ملفين (الدرس 11).
- **النوافذ والأحداث** والقوائم (الدرسان 14 و15).

## الخطوة 1: التخطيط

قبل أي كود، نقسم البرنامج إلى جزأين منفصلين:

1. **منطق البرنامج** في الملف `tasks.js`: صنف `TaskList` يعرف كيف يضيف المهام ويحذفها ويحفظها. لا يعرف شيئًا عن النوافذ.
2. **الواجهة** في الملف `Form1.js`: تقرأ ما يكتبه المستخدم، وتنادي دوال `TaskList`، ثم تعرض النتيجة في النافذة.

> **لماذا الفصل؟** مثل المطعم: المطبخ (المنطق) لا يهمه شكل الصالة، والصالة (الواجهة) لا تطبخ. لو أردت لاحقًا صنع نسخة ويب أو نسخة سطر أوامر من البرنامج، تستخدم `tasks.js` كما هو وتغيّر الواجهة فقط. ويمكنك أيضًا اختبار المنطق وحده بسهولة.

## الخطوة 2: منطق البرنامج واختباره

أنشئ مشروع **Console Application** مؤقتًا لنجرّب الصنف وحده. شكل المهمة كائن بسيط: `{ text: "نص المهمة", done: false }`.

```js run
// #file: tasks.js
const fs = require("node:fs");

class TaskList {
    constructor(file) {
        this.file = file;
        this.items = [];
    }

    add(text) {
        text = String(text).trim();
        if (text === "") throw new Error("نص المهمة فارغ");
        if (this.items.some((t) => t.text === text)) throw new Error("المهمة موجودة بالفعل");
        this.items.push({ text, done: false });
    }

    toggle(index) {
        const t = this.items[index];
        if (t) t.done = !t.done;
    }

    remove(index) {
        this.items.splice(index, 1);
    }

    clearDone() {
        this.items = this.items.filter((t) => !t.done);
    }

    get remaining() {
        return this.items.filter((t) => !t.done).length;
    }

    lines() {
        return this.items.map((t) => (t.done ? "✔ " : "☐ ") + t.text);
    }

    save() {
        if (this.file) fs.writeFileSync(this.file, JSON.stringify(this.items, null, 2), "utf8");
    }

    load() {
        if (this.file && fs.existsSync(this.file)) {
            this.items = JSON.parse(fs.readFileSync(this.file, "utf8"));
        }
    }
}

module.exports = { TaskList };

// #file: Program.js
const list = new TaskList(null);          // null: بلا ملف أثناء الاختبار
list.add("مذاكرة الرياضيات");
list.add("شراء الخبز");
list.add("الاتصال بجدتي");
list.toggle(1);
console.log(list.lines().join("\n"));
console.log("المتبقي:", list.remaining);

try {
    list.add("شراء الخبز");
} catch (e) {
    console.log("خطأ:", e.message);
}

list.clearDone();
console.log(list.lines().join("\n"));
```

```text output
☐ مذاكرة الرياضيات
✔ شراء الخبز
☐ الاتصال بجدتي
المتبقي: 2
خطأ: المهمة موجودة بالفعل
☐ مذاكرة الرياضيات
☐ الاتصال بجدتي
```

لاحظ:

- `add` ترمي أخطاء بـ `throw` بدل أن تعرض رسائل بنفسها: المنطق لا يعرف شيئًا عن `msgbox`، والواجهة هي التي تقرر كيف تعرض الخطأ.
- `get remaining` خاصية محسوبة، و`lines()` تجهّز النصوص التي ستُعرض في القائمة.
- في مشروع RAD IDE يرى `Program.js` الصنف `TaskList` مباشرة (الطريقة 1 في الدرس 11)، و`module.exports` تسمح باستخدامه أيضًا بـ `require("./tasks")` خارج RAD IDE.

## الخطوة 3: تصميم النافذة

أنشئ مشروعًا جديدًا: **File > New Project > Web & Script > JavaScript > Windows Application** باسم `TaskManager`. ثم أضف الملف `tasks.js` من **Project > Add Module...** (مشروع > إضافة وحدة برمجية...) باسم `tasks` والصق فيه كود الصنف كما هو (بدون جزء `Program.js`).

ارسم النافذة بهذه الأدوات:

| الأداة | Name | Text | ملاحظة |
|---|---|---|---|
| TextBox | `txtTask` | (فارغ) | لكتابة المهمة الجديدة |
| Button | `btnAdd` | `إضافة` | |
| ListBox | `lstTasks` | | كبّرها لتعرض 8 مهام تقريبًا |
| Button | `btnToggle` | `تم / لم يتم` | يعلّم المهمة المختارة |
| Button | `btnDelete` | `حذف` | |
| Button | `btnClearDone` | `حذف المنجز` | |
| Label | `lblStats` | (فارغ) | الإحصائيات |

واجعل `Text` النافذة نفسها `مدير المهام`.

## الخطوة 4: كود النافذة

<!-- test: {"controls": [["TextBox", "txtTask"], ["Button", "btnAdd", {"Text": "إضافة"}], ["ListBox", "lstTasks", {"Height": 160}], ["Button", "btnToggle", {"Text": "تم / لم يتم"}], ["Button", "btnDelete", {"Text": "حذف"}], ["Button", "btnClearDone", {"Text": "حذف المنجز"}], ["Label", "lblStats"]], "form": {"Text": "مدير المهام"}, "steps": [["set", "txtTask", "Text", "مذاكرة"], ["click", "btnAdd"], ["set", "txtTask", "Text", "رياضة"], ["click", "btnAdd"], ["set", "txtTask", "Text", "قراءة"], ["click", "btnAdd"], ["set", "txtTask", "Text", "رياضة"], ["click", "btnAdd"], ["set", "lstTasks", "ListIndex", "1"], ["click", "btnToggle"], ["set", "lstTasks", "ListIndex", "0"], ["click", "btnDelete"]], "msgbox": ["المهمة موجودة بالفعل"], "expect": {"lstTasks.ListCount": "2", "lstTasks.List(0)": "✔ رياضة", "lstTasks.List(1)": "☐ قراءة", "lblStats.Text": "المهام: 2 · المتبقي: 1 · المنجز: 1", "lstTasks.ListIndex": "0"}} -->
```js form run
// #file: tasks.js
const fs = require("node:fs");

class TaskList {
    constructor(file) {
        this.file = file;
        this.items = [];
    }
    add(text) {
        text = String(text).trim();
        if (text === "") throw new Error("نص المهمة فارغ");
        if (this.items.some((t) => t.text === text)) throw new Error("المهمة موجودة بالفعل");
        this.items.push({ text, done: false });
    }
    toggle(index) {
        const t = this.items[index];
        if (t) t.done = !t.done;
    }
    remove(index) {
        this.items.splice(index, 1);
    }
    clearDone() {
        this.items = this.items.filter((t) => !t.done);
    }
    get remaining() {
        return this.items.filter((t) => !t.done).length;
    }
    lines() {
        return this.items.map((t) => (t.done ? "✔ " : "☐ ") + t.text);
    }
    save() {
        if (this.file) fs.writeFileSync(this.file, JSON.stringify(this.items, null, 2), "utf8");
    }
    load() {
        if (this.file && fs.existsSync(this.file)) {
            this.items = JSON.parse(fs.readFileSync(this.file, "utf8"));
        }
    }
}

module.exports = { TaskList };

// #file: Form1.js
const tasks = new TaskList("tasks.json");

function refresh(selected = -1) {
    ui.lstTasks.Clear();
    for (const line of tasks.lines()) {
        ui.lstTasks.AddItem(line);
    }
    if (selected >= 0 && selected < tasks.items.length) {
        set("lstTasks", "ListIndex", selected);
    }
    const done = tasks.items.length - tasks.remaining;
    ui.lblStats.Text = `المهام: ${tasks.items.length} · المتبقي: ${tasks.remaining} · المنجز: ${done}`;
    tasks.save();
}

function selectedIndex() {
    const i = getNum("lstTasks", "ListIndex");
    if (i < 0) msgbox("اختر مهمة من القائمة أولًا");
    return i;
}

function Form1_Load(e) {
    try {
        tasks.load();
    } catch (err) {
        msgbox("تعذّرت قراءة ملف المهام: " + err.message);
    }
    refresh();
}

function btnAdd_Click(e) {
    try {
        tasks.add(ui.txtTask.Text);
        ui.txtTask.Text = "";
        refresh(tasks.items.length - 1);
    } catch (err) {
        msgbox(err.message);
    }
}

function btnToggle_Click(e) {
    const i = selectedIndex();
    if (i < 0) return;
    tasks.toggle(i);
    refresh(i);
}

function btnDelete_Click(e) {
    const i = selectedIndex();
    if (i < 0) return;
    tasks.remove(i);
    refresh(Math.min(i, tasks.items.length - 1));
}

function btnClearDone_Click(e) {
    tasks.clearDone();
    refresh();
}
```

اضغط `F5` وجرّب: أضف مهام، وعلّم بعضها، ثم أغلق البرنامج وشغّله من جديد: ستجد مهامك محفوظة في الملف `tasks.json` داخل مجلد المشروع.

## الخطوة 5: فهم الكود

- **`refresh`** هي قلب الواجهة: تمسح القائمة وتعيد ملأها من `tasks`، وتحدّث الإحصائيات، وتحفظ الملف. كل معالج حدث يغيّر البيانات ثم يستدعيها. هذا النمط («غيّر البيانات ثم أعد الرسم») يجعل الواجهة متطابقة دائمًا مع البيانات، وهو الفكرة نفسها التي تقوم عليها React وVue.
- **`selectedIndex`** دالة مساعدة تمنع تكرار فحص «هل اختار المستخدم شيئًا؟» في ثلاثة أزرار.
- **`try/catch`** في `btnAdd_Click` تحوّل الأخطاء التي يرميها `TaskList` إلى رسائل للمستخدم.
- الثابت `tasks` عام، فيبقى موجودًا بين الأحداث.

## الخطوة 6: النشر

عندما يعجبك البرنامج جهّزه للتوزيع من **Build > Publish / Create Installer...** (بناء > نشر / إنشاء برنامج تثبيت...) أو `Ctrl+Alt+F5`: تجمع RAD IDE برنامجك مع ما يحتاجه للتشغيل في مجلد **Publish** داخل المشروع، ويمكنها أيضًا إنشاء برنامج تثبيت لويندوز. ومن **Build > Open Publish Folder** تفتح ذلك المجلد. لاحظ أن الجهاز الذي سيشغّل البرنامج يحتاج Node.js مثبتًا.

## تحديات إضافية

جرّب تطوير البرنامج بنفسك، فهذه أفضل طريقة للتعلم:

1. أضف مربع اختيار `chkHideDone` يخفي المهام المنجزة من القائمة. (تلميح: احتفظ بمصفوفة تربط رقم السطر في القائمة برقم المهمة في `tasks.items`.)
2. أضف **أولوية** لكل مهمة (عالية/عادية) بـ ComboBox، واعرض المهام العالية أولًا.
3. انقل المشروع إلى **TypeScript**: أنشئ مشروع TypeScript وعرّف `interface Task { text: string; done: boolean }`.
4. اختصر إضافة المهمة بزر Enter: الحدث `txtTask_KeyDown` والخاصية `e.KeyCode` (رقم المفتاح Enter هو `13`).

## تمرين

أضف إلى الصنف `TaskList` دالة `search(word)` ترجع نصوص المهام التي تحتوي الكلمة، ثم جرّبه.

```js exercise
// #file: tasks.js
class TaskList {
    constructor() { this.items = []; }
    add(text) { this.items.push({ text, done: false }); }
    // search(word) { ... }
}

// #file: Program.js
const list = new TaskList();
list.add("قراءة كتاب");
list.add("إرسال تقرير");
list.add("شراء كتاب جديد");
// console.log(list.search("كتاب"));
// [ 'قراءة كتاب', 'شراء كتاب جديد' ]
```

```js solution
// #file: tasks.js
class TaskList {
    constructor() { this.items = []; }
    add(text) { this.items.push({ text, done: false }); }
    search(word) {
        return this.items.filter((t) => t.text.includes(word)).map((t) => t.text);
    }
}

// #file: Program.js
const list = new TaskList();
list.add("قراءة كتاب");
list.add("إرسال تقرير");
list.add("شراء كتاب جديد");
console.log(list.search("كتاب"));
```

```text output
[ 'قراءة كتاب', 'شراء كتاب جديد' ]
```

## اختبر نفسك

```quiz
{"question": "لماذا وضعنا منطق المهام في ملف منفصل `tasks.js`؟", "choices": ["لأن RAD IDE تشترط ذلك", "لفصل المنطق عن الواجهة، فيسهل اختباره وإعادة استخدامه", "لتسريع البرنامج", "لأن الأصناف لا تعمل في `Form1.js`"], "answer": 1, "explanation": "المنطق المنفصل يمكن اختباره وحده واستخدامه مع واجهة أخرى."}
```

```quiz
{"question": "ماذا تفعل الدالة `refresh` في المشروع؟", "choices": ["تعيد تشغيل البرنامج", "تعيد ملء القائمة من البيانات وتحدّث الإحصائيات وتحفظ الملف", "تحذف كل المهام", "تغلق النافذة"], "answer": 1, "explanation": "نمط «غيّر البيانات ثم أعد الرسم» يبقي الواجهة متطابقة مع البيانات."}
```

```quiz
{"question": "أين تُحفظ المهام بين مرات التشغيل؟", "choices": ["في الذاكرة فقط", "في الملف `tasks.json` داخل مجلد المشروع", "في الإنترنت", "في `Form1.form`"], "answer": 1, "explanation": "`save` يكتب المصفوفة بصيغة JSON بـ `fs.writeFileSync`، و`load` يقرؤها عند فتح النافذة."}
```

## مبروك!

أنهيت دورة JavaScript! تعلمت المتغيرات والشروط والحلقات والدوال والمصفوفات والكائنات والأصناف والأخطاء والبرمجة غير المتزامنة ووحدات Node.js وحزم npm وTypeScript، وبنيت برامج بنوافذ حقيقية.

**ماذا بعد؟** تابع مع دليل **Node.js والواجهات الأمامية** في قائمة الدروس: ستبني خادم ويب بـ Express، وواجهة برمجية (REST API) وتختبرها بـ REST Client، ثم مشروع React أو Vue أو Angular، وتتعلم تصحيح أخطاء JavaScript في المتصفح.
