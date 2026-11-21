# الدرس 12: حزم npm وملف package.json

**في هذا الدرس ستتعلم:**

- ما هي **الحزمة** (package)، وما هو **npm**.
- ملف `package.json` ومعنى أهم أجزائه.
- تثبيت الحزم من RAD IDE: **Project > Manage Packages...** وقائمة **npm Scripts**.
- استخدام حزمة مثبّتة في برنامجك بـ `require`.
- السكربتات (scripts) والمجلد `node_modules`.

## ما هي الحزمة؟

**الحزمة** (package) مكتبة كتبها مبرمجون آخرون ونشروها ليستخدمها الجميع: حزمة للتواريخ، وأخرى لإنشاء خادم ويب، وثالثة لقراءة ملفات Excel... و**npm** هو مدير الحزم الذي يأتي مع Node.js، ومعه أكبر مستودع حزم في العالم على الموقع `https://www.npmjs.com`.

> **تشبيه:** بدل أن تصنع كل قطعة أثاث في بيتك بنفسك، تشتري الجاهز من المعرض وتركّبه. npm هو المعرض، والحزم هي قطع الأثاث، وملف `package.json` هو **فاتورة** تكتب فيها ما اشتريته.

## الملف `package.json`

كل مشروع Node.js فيه ملف `package.json` يصف المشروع والحزم التي يحتاجها. مثال:

```json
{
  "name": "my-shop",
  "version": "1.0.0",
  "description": "متجر صغير للتجربة",
  "main": "Program.js",
  "scripts": {
    "start": "node Program.js",
    "test": "node --test"
  },
  "dependencies": {
    "dayjs": "^1.11.13"
  },
  "devDependencies": {
    "typescript": "^5.6.0"
  }
}
```

| الجزء | معناه |
|---|---|
| `name` و`version` | اسم المشروع ورقم إصداره |
| `main` | الملف الرئيسي للمشروع |
| `scripts` | أوامر مختصرة تشغّلها بـ `npm run <الاسم>` |
| `dependencies` | الحزم التي يحتاجها البرنامج ليعمل |
| `devDependencies` | حزم يحتاجها المبرمج فقط أثناء التطوير (مثل TypeScript وأدوات الاختبار) |

وملف `package.json` ملف JSON عادي، فيمكن لبرنامجك نفسه أن يقرأه بـ `require`:

```js run
// #file: package.json
{
  "name": "my-shop",
  "version": "1.2.0",
  "scripts": { "start": "node Program.js", "test": "node --test" },
  "dependencies": { "dayjs": "^1.11.13", "express": "^4.21.2" }
}

// #file: Program.js
const pkg = require("./package.json");
console.log(`${pkg.name} الإصدار ${pkg.version}`);
console.log("السكربتات:", Object.keys(pkg.scripts).join("، "));
console.log("الحزم:", Object.keys(pkg.dependencies).length);
```

```text output
my-shop الإصدار 1.2.0
السكربتات: start، test
الحزم: 2
```

### معنى الرمز `^` في رقم الإصدار

أرقام الإصدارات على الصورة `رئيسي.فرعي.تصحيح`، مثل `1.11.13`. الرمز `^1.11.13` يعني: «أي إصدار من `1.x.x` بشرط ألا يقل عن `1.11.13`». أي أن npm يقبل التحديثات الصغيرة الآمنة، ولا يقفز إلى الإصدار `2.0.0` الذي قد يغيّر طريقة الاستخدام.

## تثبيت حزمة من RAD IDE

### الطريقة 1: نافذة إدارة الحزم

1. افتح مشروع JavaScript، ثم اختر **Project > Manage Packages...** (مشروع > إدارة الحزم...).
2. في تبويب **Browse** (استعراض) اكتب اسم الحزمة، مثلًا `dayjs`، واضغط **Search** (بحث).
3. اختر الإصدار (اتركه فارغًا لأحدث إصدار، `latest`) ثم اضغط **Install** (تثبيت).
4. تعمل الأوامر في مجلد المشروع ويظهر ناتجها أسفل النافذة. وإن لم يكن هناك `package.json` تنشئه النافذة أولًا (بالأمر `npm init -y`)، ويمكنك إنشاؤه بنفسك بالزر **Create Manifest** أعلى النافذة.
5. تبويب **Installed** (مثبّت) يعرض الحزم المثبّتة، ومنه تستطيع **Uninstall** (إلغاء التثبيت) أو **Update...** (تحديث...).

### الطريقة 2: قائمة npm Scripts

عندما يحتوي المشروع على `package.json` تظهر في شريط القوائم قائمة **npm Scripts** فيها:

- كل سكربت من `scripts` (مثل `start` و`test`) لتشغيله بضغطة.
- **npm install** لتثبيت كل الحزم المكتوبة في `package.json`.
- **Add Package...** لإضافة حزمة باسمها (مع خيار **Development dependency (--save-dev)**).
- **Open package.json** لفتح الملف.

وتجد السكربتات نفسها بالنقر بالزر الأيمن على `package.json` في **Solution Explorer** (مستكشف الحلول).

### الطريقة 3: الطرفية

من **View > Terminal** (عرض > الطرفية) اكتب الأوامر بنفسك:

```text
npm init -y                 أنشئ package.json
npm install dayjs           ثبّت حزمة وأضفها إلى dependencies
npm install -D typescript   ثبّت حزمة تطوير (devDependencies)
npm uninstall dayjs         احذف حزمة
npm install                 ثبّت كل ما في package.json (بعد تنزيل مشروع مثلًا)
npm run start               شغّل السكربت start
npm outdated                اعرض الحزم التي لها إصدارات أحدث
```

## استخدام الحزمة في برنامجك

بعد تثبيت `dayjs` (مكتبة صغيرة ومشهورة للتواريخ) تستخدمها بـ `require` باسمها مباشرة، بلا `./`:

```js
const dayjs = require("dayjs");

const exam = dayjs("2025-06-15");
const today = dayjs("2025-05-01");
console.log("باقي على الامتحان:", exam.diff(today, "day"), "يومًا");
console.log(exam.add(1, "month").format("YYYY-MM-DD"));
```

```text
باقي على الامتحان: 45 يومًا
2025-07-15
```

هذا المثال للقراءة فقط (ليس عليه زر «جرّبه») لأنه يحتاج أن تثبّت الحزمة أولًا، وهذا يحتاج اتصالًا بالإنترنت. ثبّتها في مشروعك ثم جرّبه بنفسك.

> **في مشاريع النوافذ أيضًا:** `require("dayjs")` تعمل في كود النماذج (مثل `Form1.js`) بالطريقة نفسها، لأن RAD IDE تبحث عن الحزم في المجلد `node_modules` الخاص بالمشروع.

## المجلد `node_modules`

عند التثبيت ينشئ npm المجلد `node_modules` ويضع فيه الحزمة **وكل الحزم التي تحتاجها هي**، فقد يصبح كبيرًا جدًا. لذلك:

- لا ترسل `node_modules` لأحد ولا تضعه في Git. أضف السطر `node_modules/` إلى الملف `.gitignore`.
- يكفي أن ترسل `package.json` و`package-lock.json`، ومن يستلم المشروع يكتب `npm install` فيعيد npm تنزيل كل شيء بالإصدارات نفسها.
- `package-lock.json` يحفظ الإصدارات الدقيقة التي ثُبّتت فعلًا. لا تعدّله بيدك.

## أشهر الحزم التي ستقابلها

| الحزمة | وظيفتها |
|---|---|
| `express` | إطار خوادم الويب الأشهر (في دليل Node.js والواجهات الأمامية) |
| `dayjs` | التواريخ والأوقات |
| `lodash` | دوال مساعدة كثيرة للمصفوفات والكائنات |
| `axios` | طلبات HTTP (بديل لـ `fetch`) |
| `chalk` | ألوان في نافذة الطرفية |
| `typescript` | مترجم TypeScript (الدرس القادم) |

> **انتبه للأمان:** أي شخص يستطيع نشر حزمة على npm. قبل التثبيت تأكد من الاسم الصحيح (حزم مزيفة بأسماء قريبة مثل `expresss` موجودة فعلًا)، وانظر إلى عدد التنزيلات الأسبوعية وتاريخ آخر تحديث. والأمر `npm audit` يبحث عن الثغرات المعروفة في حزم مشروعك.

## أخطاء شائعة

- **`Cannot find module 'dayjs'`:** الحزمة غير مثبّتة في هذا المشروع. ثبّتها من **Manage Packages** أو بـ `npm install dayjs` في مجلد المشروع.
- **التثبيت في المجلد الخطأ:** تأكد أن الطرفية مفتوحة على مجلد المشروع (حيث `package.json`) قبل `npm install`.
- **حزمة ES Modules فقط:** بعض الحزم الحديثة لا تعمل مع `require` وتعطي خطأ `ERR_REQUIRE_ESM`. في Node.js 22 يعمل `require` مع أغلبها، وإلا فاختر إصدارًا أقدم من الحزمة أو حزمة أخرى.
- **تعديل ملفات داخل `node_modules`:** أي تعديل يضيع عند إعادة التثبيت.

## تمارين

### التمرين 1

اكتب ملف `package.json` لمشروع اسمه `notes-app` إصداره `0.1.0` فيه سكربتان `start` و`dev` وحزمة واحدة، ثم اطبع من `Program.js` اسم المشروع وعدد السكربتات.

```js exercise
// #file: package.json
// {
//   "name": "notes-app",
//   ...
// }

// #file: Program.js
// الناتج المطلوب:
// notes-app 0.1.0
// عدد السكربتات: 2
```

```js solution
// #file: package.json
{
  "name": "notes-app",
  "version": "0.1.0",
  "scripts": { "start": "node Program.js", "dev": "node --watch Program.js" },
  "dependencies": { "dayjs": "^1.11.13" }
}

// #file: Program.js
const pkg = require("./package.json");
console.log(pkg.name, pkg.version);
console.log("عدد السكربتات:", Object.keys(pkg.scripts).length);
```

```text output
notes-app 0.1.0
عدد السكربتات: 2
```

### التمرين 2

اكتب دالة `satisfiesMajor(range, version)` تتحقق (بطريقة مبسطة) من أن الإصدار له الرقم الرئيسي نفسه في المدى الذي يبدأ بـ `^`. مثلًا `^1.11.13` مع `1.20.0` يعطي `true`، ومع `2.0.0` يعطي `false`.

```js exercise
// console.log(satisfiesMajor("^1.11.13", "1.20.0"));  // true
// console.log(satisfiesMajor("^1.11.13", "2.0.0"));   // false
```

```js solution
function satisfiesMajor(range, version) {
    const wanted = range.replace("^", "").split(".")[0];
    const actual = version.split(".")[0];
    return wanted === actual;
}
console.log(satisfiesMajor("^1.11.13", "1.20.0"));
console.log(satisfiesMajor("^1.11.13", "2.0.0"));
```

```text output
true
false
```

## اختبر نفسك

```quiz
{"question": "ما الفرق بين `dependencies` و`devDependencies`؟", "choices": ["لا فرق", "الأولى يحتاجها البرنامج ليعمل، والثانية يحتاجها المبرمج أثناء التطوير فقط", "الأولى للحزم المجانية والثانية للمدفوعة", "الثانية تُحذف تلقائيًا"], "answer": 1, "explanation": "مثلًا `express` من dependencies، و`typescript` وأدوات الاختبار من devDependencies."}
```

```quiz
{"question": "استلمت مشروعًا فيه `package.json` بلا مجلد `node_modules`. ماذا تفعل؟", "choices": ["تنسخ `node_modules` من مشروع آخر", "تكتب `npm install` في مجلد المشروع", "تحذف `package.json`", "لا شيء، سيعمل كما هو"], "answer": 1, "explanation": "`npm install` يقرأ `package.json` وينزّل كل الحزم المطلوبة."}
```

```quiz
{"question": "كيف تستورد حزمة npm مثبّتة اسمها `dayjs`؟", "choices": ["`require(\"./dayjs\")`", "`require(\"dayjs\")`", "`import dayjs.js`", "`npm dayjs`"], "answer": 1, "explanation": "الحزم تُستورد باسمها مباشرة بدون `./`، أما ملفاتك أنت فتبدأ بـ `./`."}
```

## الخلاصة

- npm مدير الحزم، و`package.json` يصف المشروع وحزمه وسكربتاته.
- ثبّت الحزم من **Project > Manage Packages...** أو قائمة **npm Scripts** أو الطرفية بـ `npm install`.
- استورد الحزمة بـ `require("اسمها")`، وملفاتك بـ `require("./اسم_الملف")`.
- لا تشارك `node_modules`، بل `package.json` و`package-lock.json`.
