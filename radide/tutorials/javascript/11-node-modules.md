# الدرس 11: وحدات Node.js: الملفات والإدخال وتقسيم البرنامج

**في هذا الدرس ستتعلم:**

- ما هي **الوحدة** (module)، وكيف تستخدم وحدات Node.js الجاهزة بـ `require`.
- قراءة الملفات وكتابتها بالوحدة `fs`، والتعامل مع المسارات بـ `path`.
- قراءة ما يكتبه المستخدم من لوحة المفاتيح بالوحدة `readline`.
- تقسيم برنامجك إلى عدة ملفات في مشروع RAD IDE.

## ما هي الوحدة؟

**الوحدة** (module) ملف أو مكتبة فيها دوال جاهزة. يأتي Node.js ومعه عشرات الوحدات المدمجة، منها:

| الوحدة | وظيفتها |
|---|---|
| `fs` | قراءة الملفات وكتابتها (file system) |
| `path` | تركيب مسارات الملفات وتفكيكها |
| `readline` | قراءة الأسطر من لوحة المفاتيح |
| `os` | معلومات عن نظام التشغيل |
| `http` | إنشاء خادم ويب (في دليل Node.js والواجهات الأمامية) |
| `crypto` | التشفير وتوليد المعرّفات العشوائية |

نحمّل الوحدة بالدالة `require` ونضعها في ثابت. ويُفضَّل كتابة البادئة `node:` لتوضيح أنها وحدة مدمجة:

```js run
const path = require("node:path");

const file = path.join("data", "2025", "report.txt");
console.log(file.replaceAll("\\", "/"));
console.log(path.basename("C:/Projects/app/main.js"));
console.log(path.extname("photo.final.png"));
console.log(path.parse("notes.txt").name);
```

```text output
data/2025/report.txt
main.js
.png
notes
```

`path.join` تضع الفاصل الصحيح لنظام التشغيل (`\` في ويندوز و`/` في لينكس)، لذلك حوّلناه إلى `/` في الطباعة فقط ليكون الناتج واحدًا على كل الأجهزة.

## قراءة الملفات وكتابتها: `fs`

```js run
const fs = require("node:fs");

fs.writeFileSync("notes.txt", "السطر الأول\n", "utf8");
fs.appendFileSync("notes.txt", "السطر الثاني\n", "utf8");

const text = fs.readFileSync("notes.txt", "utf8");
console.log(text.trim());
console.log("عدد الأسطر:", text.trim().split("\n").length);
console.log("موجود؟", fs.existsSync("notes.txt"));

fs.unlinkSync("notes.txt");          // حذف الملف
console.log("موجود بعد الحذف؟", fs.existsSync("notes.txt"));
```

```text output
السطر الأول
السطر الثاني
عدد الأسطر: 2
موجود؟ true
موجود بعد الحذف؟ false
```

- `writeFileSync(اسم, نص, "utf8")` تنشئ الملف (أو تستبدل محتواه).
- `appendFileSync` تضيف إلى آخره.
- `readFileSync(اسم, "utf8")` ترجع المحتوى نصًا. لا تنسَ `"utf8"` وإلا رجعت بيانات خام (Buffer).
- الملفات تُنشأ في **مجلد المشروع** لأنه المجلد الحالي للبرنامج عند تشغيله من RAD IDE.

> **العربية في الملفات:** مع `"utf8"` تُحفظ العربية وتُقرأ بلا أي مشكلة، وأي محرر حديث يفتحها صحيحة.

### حفظ البيانات بـ JSON

أشهر استخدام: حفظ كائنات البرنامج في ملف JSON ثم قراءتها في المرة القادمة:

```js run
const fs = require("node:fs");
const FILE = "contacts.json";

const contacts = [
    { name: "أمل", phone: "0100" },
    { name: "طارق", phone: "0122" },
];
fs.writeFileSync(FILE, JSON.stringify(contacts, null, 2), "utf8");

const loaded = JSON.parse(fs.readFileSync(FILE, "utf8"));
loaded.push({ name: "رنا", phone: "0111" });
console.log(loaded.map((c) => c.name).join("، "));
fs.unlinkSync(FILE);
```

```text output
أمل، طارق، رنا
```

### النسخة غير المتزامنة

الدوال التي تنتهي بـ `Sync` توقف البرنامج حتى تنتهي. في الخوادم والبرامج الكبيرة نستخدم النسخة غير المتزامنة من `fs/promises` مع `await`:

```js run
const fsp = require("node:fs/promises");

async function main() {
    await fsp.writeFile("hello.txt", "مرحبًا من fs/promises", "utf8");
    const text = await fsp.readFile("hello.txt", "utf8");
    console.log(text);
    await fsp.rm("hello.txt");
}
main().catch((e) => console.log("خطأ:", e.message));
```

```text output
مرحبًا من fs/promises
```

## قراءة إدخال المستخدم: `readline`

الوحدة `readline` تقرأ ما يكتبه المستخدم سطرًا سطرًا. هذه دالة صغيرة `ask` سنستخدمها في كل برامج الإدخال، انسخها كما هي:

```js run
const readline = require("node:readline");
const rl = readline.createInterface({ input: process.stdin });
const lines = rl[Symbol.asyncIterator]();

async function ask(question) {
    process.stdout.write(question);
    const { value, done } = await lines.next();
    return done ? "" : value.trim();
}

async function main() {
    const name = await ask("ما اسمك؟ ");
    const age = Number(await ask("كم عمرك؟ "));
    console.log();
    console.log(`أهلًا يا ${name}! بعد 10 سنوات سيكون عمرك ${age + 10} سنة.`);
    rl.close();
}
main();
```

```text input
ياسمين
19
```

```text output
ما اسمك؟ كم عمرك؟
أهلًا يا ياسمين! بعد 10 سنوات سيكون عمرك 29 سنة.
```

- `process.stdout.write` تطبع **دون** النزول لسطر جديد، فيكتب المستخدم إجابته بجانب السؤال.
- `await lines.next()` تنتظر حتى يكتب المستخدم سطرًا ويضغط Enter.
- `rl.close()` في النهاية ضرورية، وإلا بقي البرنامج ينتظر مزيدًا من الإدخال.
- ما يكتبه المستخدم يصل **نصًا** دائمًا، فحوّله بـ `Number` عند الحاجة.

> **أين أكتب الإدخال؟** عند الضغط على «جرّبه» تسألك RAD IDE عن المدخلات في نافذة صغيرة (كل قيمة في سطر). وفي مشروعك الخاص الذي يقرأ من لوحة المفاتيح، شغّله من **View > Terminal** (عرض > الطرفية) بالأمر `node Program.js` لتكتب الإجابات بنفسك. لاحظ أن ما تكتبه في الطرفية يظهر على الشاشة، أما في الناتج المتوقع أعلاه فلا يظهر لأن المدخلات جاءت من ملف.

## تقسيم البرنامج إلى عدة ملفات

عندما يكبر البرنامج نقسمه إلى ملفات، كل ملف مسؤول عن شيء واحد.

### الطريقة 1: وحدات مشروع RAD IDE

أضف ملفًا جديدًا من **Project > Add Module...** (مشروع > إضافة وحدة برمجية...). كل ملفات `.js` في المشروع تُحمَّل معًا قبل `Program.js`، فالدوال المعرّفة في أي ملف يمكن استدعاؤها من الملفات الأخرى مباشرة.

في الأمثلة التالية يفصل السطر `// #file: اسم_الملف` بين الملفات، فتنشئ «جرّبه» مشروعًا فيه الملفان:

```js run
// #file: geometry.js
function circleArea(r) {
    return Math.PI * r * r;
}

function rectArea(w, h) {
    return w * h;
}

// #file: Program.js
console.log(circleArea(2).toFixed(2));
console.log(rectArea(3, 7));
```

```text output
12.57
21
```

### الطريقة 2: `module.exports` و`require` (طريقة Node.js القياسية)

هذه هي الطريقة التي ستجدها في كل مشاريع Node.js: الملف يصدّر ما يريد مشاركته بـ `module.exports`، والملف الآخر يستورده بـ `require("./اسم_الملف")`. وهي تعمل أيضًا داخل RAD IDE:

```js run
// #file: money.js
const RATE = 0.14;

function withTax(amount) {
    return Math.round(amount * (1 + RATE) * 100) / 100;
}

function format(amount) {
    return `${amount.toFixed(2)} جنيه`;
}

module.exports = { withTax, format };

// #file: Program.js
const money = require("./money");

const price = 250;
console.log(money.format(price));
console.log(money.format(money.withTax(price)));
```

```text output
250.00 جنيه
285.00 جنيه
```

- `./` في بداية الاسم تعني «من المجلد نفسه»، ولا نكتب الامتداد `.js`.
- `RATE` لم نصدّرها، فهي خاصة بالملف `money.js` ولا يراها غيره.
- في المشاريع الحديثة ستجد أيضًا صيغة `import` و`export` (ES Modules). فكرتها هي نفسها، وتستخدمها مشاريع React وVue في دليل Node.js والواجهات الأمامية.

## أخطاء شائعة

- **نسيان `"utf8"`:** `readFileSync("a.txt")` ترجع `<Buffer ...>` لا نصًا.
- **ملف غير موجود:** `readFileSync` لملف غير موجود ترمي `ENOENT: no such file or directory`. تحقق أولًا بـ `existsSync` أو استخدم `try/catch`.
- **نسيان `./`:** `require("money")` تبحث عن حزمة npm اسمها money، لا عن ملفك. اكتب `require("./money")`.
- **نسيان `rl.close()`:** يبقى البرنامج معلّقًا ينتظر الإدخال.
- **الاسم نفسه في ملفين من المشروع:** في الطريقة 1 تشترك ملفات المشروع في مكان واحد للأسماء، فلو كتب ملفان `const fs = require("node:fs");` يظهر الخطأ `SyntaxError: Identifier 'fs' has already been declared`. اكتب السطر في ملف واحد فقط، أو استخدم الطريقة 2 التي يكون فيها لكل ملف أسماؤه الخاصة داخل دواله.

## تمارين

### التمرين 1

اكتب الأعداد من 1 إلى 5 في ملف `nums.txt`، كل عدد في سطر، ثم اقرأ الملف واطبع مجموع الأعداد، ثم احذف الملف.

```js exercise
const fs = require("node:fs");
// الناتج المطلوب: المجموع: 15
```

```js solution
const fs = require("node:fs");
const lines = [];
for (let i = 1; i <= 5; i++) lines.push(i);
fs.writeFileSync("nums.txt", lines.join("\n"), "utf8");

const sum = fs.readFileSync("nums.txt", "utf8")
    .split("\n")
    .reduce((s, x) => s + Number(x), 0);
console.log("المجموع:", sum);
fs.unlinkSync("nums.txt");
```

```text output
المجموع: 15
```

### التمرين 2

اقرأ من المستخدم عددين (كل عدد في سطر) واطبع حاصل ضربهما.

```js exercise
const readline = require("node:readline");
const rl = readline.createInterface({ input: process.stdin });
const lines = rl[Symbol.asyncIterator]();
async function ask(q) {
    process.stdout.write(q);
    const { value, done } = await lines.next();
    return done ? "" : value.trim();
}
// اسأل: "العدد الأول: " و"العدد الثاني: " ثم اطبع في سطر جديد: 6 × 7 = 42
```

```js solution
const readline = require("node:readline");
const rl = readline.createInterface({ input: process.stdin });
const lines = rl[Symbol.asyncIterator]();
async function ask(q) {
    process.stdout.write(q);
    const { value, done } = await lines.next();
    return done ? "" : value.trim();
}
async function main() {
    const a = Number(await ask("العدد الأول: "));
    const b = Number(await ask("العدد الثاني: "));
    console.log();
    console.log(`${a} × ${b} = ${a * b}`);
    rl.close();
}
main();
```

```text input
6
7
```

```text output
العدد الأول: العدد الثاني:
6 × 7 = 42
```

### التمرين 3

قسّم البرنامج إلى ملفين: `text-tools.js` يصدّر دالة `countWords(s)` ترجع عدد كلمات النص، و`Program.js` يستوردها ويطبع عدد كلمات الجملة.

```js exercise
// #file: text-tools.js
// function countWords(s) { ... }
// module.exports = { countWords };

// #file: Program.js
// const tools = require("./text-tools");
// الناتج المطلوب: عدد الكلمات: 5
```

```js solution
// #file: text-tools.js
function countWords(s) {
    return s.trim().split(/\s+/).length;
}
module.exports = { countWords };

// #file: Program.js
const tools = require("./text-tools");
console.log("عدد الكلمات:", tools.countWords("  البرمجة ممتعة جدًا مع Node.js "));
```

```text output
عدد الكلمات: 5
```

## اختبر نفسك

```quiz
{"question": "ما الذي تفعله `require(\"node:fs\")`؟", "choices": ["تنشئ ملفًا جديدًا", "تحمّل وحدة نظام الملفات المدمجة في Node.js", "تحذف الملفات", "تثبّت حزمة من الإنترنت"], "answer": 1, "explanation": "`require` تحمّل وحدة، و`fs` وحدة مدمجة للتعامل مع الملفات."}
```

```quiz
{"question": "لماذا نكتب `\"utf8\"` مع `readFileSync`؟", "choices": ["لتسريع القراءة", "لكي ترجع نصًا بدل بيانات خام (Buffer)", "لحذف الملف بعد قراءته", "لا فائدة لها"], "answer": 1, "explanation": "بدون ترميز ترجع الدالة Buffer، ومع `\"utf8\"` ترجع نصًا تُقرأ فيه العربية صحيحة."}
```

```quiz
{"question": "كيف يشارك ملف دوالَّه مع الملفات الأخرى بطريقة Node.js القياسية؟", "choices": ["`module.exports = { ... }`", "`console.log(...)`", "`export.all()`", "لا يمكن ذلك"], "answer": 0, "explanation": "الملف يصدّر بـ `module.exports`، والملف الآخر يستورد بـ `require(\"./name\")`."}
```

## الخلاصة

- `require("node:اسم")` لتحميل وحدات Node.js المدمجة مثل `fs` و`path` و`readline`.
- `readFileSync` و`writeFileSync` مع `"utf8"`، و`fs/promises` مع `await` للنسخة غير المتزامنة.
- دالة `ask` مع `readline` لقراءة إدخال المستخدم، ولا تنسَ `rl.close()`.
- قسّم البرنامج: وحدات المشروع في RAD IDE، أو `module.exports` و`require("./file")`.
