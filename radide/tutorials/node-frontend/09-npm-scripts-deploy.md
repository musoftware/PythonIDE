# الدرس 9: سكربتات npm والحزم والنشر

**في هذا الدرس ستتعلم:**

- تشغيل **سكربتات npm** من قائمة **npm Scripts** ومن **Solution Explorer** دون كتابة أوامر.
- الفرق بين حزم التشغيل (`dependencies`) وحزم التطوير (`devDependencies`)، ودور `package-lock.json`.
- الإعدادات بمتغيرات البيئة (`process.env`) وملف `.env`، دون وضع أسرار في الكود.
- تجهيز نسخة الإنتاج: موقع ثابت من Vite، أو خادم Express أو NestJS.
- النشر: رفع الملفات بـ **Publish**، أو **Docker**، أو **Deploy to Cloud / Git / SSH**.

## السكربتات: أزرار جاهزة في `package.json`

**السكربت** (script) اسم مختصر لأمر طويل، تكتبه مرة واحدة في `package.json`:

```json
{
  "name": "shop-api",
  "scripts": {
    "dev": "nest start --watch",
    "build": "nest build",
    "start:prod": "node dist/main",
    "test": "jest"
  }
}
```

بدل أن تتذكر `nest start --watch` تكتب `npm run dev`. وفريقك كله يستخدم الأسماء نفسها.

> **تشبيه:** السكربتات مثل أزرار **الطلب السريع** في المطعم: «وجبة رقم 3» بدل أن تشرح للنادل كل مكوناتها في كل مرة.

### تشغيلها من RAD IDE

إذا كان في المشروع ملف `package.json` تظهر في شريط القوائم قائمة **npm Scripts** (سكربتات npm) فيها:

- كل سكربت باسمه (`dev` و`build` و`test` ...). مرّر الفأرة فوقه لترى الأمر الحقيقي. يعمل الأمر ويظهر ناتجه في **Output**.
- **npm install**: يثبّت كل الحزم المكتوبة في `package.json` (بعد أن تنسخ مشروعًا من زميل مثلًا).
- **Add Package...** (إضافة حزمة...): تكتب اسم الحزمة في **Package** (مثل `dayjs` أو `lodash@4`)، وتفعّل **Development dependency (--save-dev)** إن كانت للتطوير فقط.
- **Open package.json**.

والأوامر نفسها في **Solution Explorer**: انقر بالزر الأيمن على المشروع واختر **Run Script** (تشغيل سكربت)، أو انقر بالزر الأيمن على `package.json` نفسه. وإن كان المشروع يستخدم `yarn` أو `pnpm` أو `bun` (يُعرف من ملف القفل مثل `yarn.lock`) تستخدم RAD IDE الأداة نفسها بدل `npm`.

هذا برنامج صغير يقرأ كائن `package.json` ويطبع ما ستعرضه القائمة، والأمر الذي سيعمل لكل سكربت:

```js run
const pkg = {
    name: "shop-api",
    scripts: { dev: "nest start --watch", build: "nest build", "start:prod": "node dist/main" },
    dependencies: { "@nestjs/core": "^11.0.1", "@nestjs/common": "^11.0.1" },
    devDependencies: { typescript: "^5.7.3", jest: "^29.7.0" },
};

for (const [name, cmd] of Object.entries(pkg.scripts)) {
    console.log(`npm run ${name}  ->  ${cmd}`);
}
console.log("حزم التشغيل:", Object.keys(pkg.dependencies).length);
console.log("حزم التطوير:", Object.keys(pkg.devDependencies).join("، "));
```

```text output
npm run dev  ->  nest start --watch
npm run build  ->  nest build
npm run start:prod  ->  node dist/main
حزم التشغيل: 2
حزم التطوير: typescript، jest
```

## حزم التشغيل وحزم التطوير

| النوع | مثال | هل يحتاجها الخادم الحقيقي؟ |
|---|---|---|
| `dependencies` | `express` و`@nestjs/core` و`react` | نعم، البرنامج لا يعمل بدونها |
| `devDependencies` | `typescript` و`vite` و`jest` و`eslint` | لا، تُستخدم أثناء التطوير والبناء فقط |

على الخادم يكفي `npm ci --omit=dev`، فيثبّت حزم التشغيل فقط، والنتيجة أصغر وأسرع وأأمن.

وملف **`package-lock.json`** يسجّل الإصدار **الدقيق** لكل حزمة ثُبّتت. احفظه في Git دائمًا: هكذا يحصل زميلك والخادم على الحزم نفسها بالضبط. والأمر `npm ci` يثبّت من ملف القفل حرفيًا (مناسب للخوادم)، أما `npm install` فقد يحدّثه.

## الإعدادات بمتغيرات البيئة

لا تكتب المنفذ أو كلمة مرور قاعدة البيانات أو مفتاح API داخل الكود. اقرأها من **متغيرات البيئة** (environment variables) عبر `process.env`، مع قيمة افتراضية للتطوير:

```js run
function loadConfig(env) {
    return {
        port: Number(env.PORT) || 3000,
        mode: env.NODE_ENV === "production" ? "production" : "development",
        dbUrl: env.DATABASE_URL || "sqlite:dev.db",
        hasApiKey: Boolean(env.API_KEY),
    };
}

console.log(loadConfig({}));
console.log(loadConfig({ PORT: "8080", NODE_ENV: "production", API_KEY: "secret" }));
```

```text output
{
  port: 3000,
  mode: 'development',
  dbUrl: 'sqlite:dev.db',
  hasApiKey: false
}
{
  port: 8080,
  mode: 'production',
  dbUrl: 'sqlite:dev.db',
  hasApiKey: true
}
```

في البرنامج الحقيقي تستدعي `loadConfig(process.env)`. وRAD IDE تضع `PORT` بنفسها عند التشغيل، لذلك يقرأ قالبا Express وNestJS `process.env.PORT`.

أثناء التطوير تضع القيم في ملف **`.env`** في جذر المشروع:

```text
PORT=3000
DATABASE_URL=postgres://localhost/shop
API_KEY=dev-key-123
```

ويقرأه Node.js 22 بالخيار `node --env-file=.env server.js`، أو بحزمة `dotenv`. وتذكّر من الدرس 4 أن REST Client يقرأ القيم نفسها بـ `{{$dotenv API_KEY}}`.

> **أمان:** أضف `.env` إلى `.gitignore` فورًا، ولا ترفعه إلى Git ولا إلى خادم النشر. على الخادم تُضبط المتغيرات من لوحة الاستضافة أو من ملف الخدمة.

## نسخة الإنتاج

| نوع المشروع | أمر البناء | الناتج | كيف يعمل على الخادم |
|---|---|---|---|
| React / Vue / Svelte (Vite) | `npm run build` | المجلد `dist` | ملفات ثابتة، أي استضافة ملفات تكفي |
| Angular | `ng build` | `dist/<الاسم>/browser` | ملفات ثابتة |
| Express | لا يحتاج بناء | ملفات المشروع نفسها | `node server.js` |
| NestJS | `npm run build` | `dist/main.js` | `npm run start:prod` (أي `node dist/main`) |

في RAD IDE: **Site > Build Production (npm run build)** (بناء نسخة الإنتاج)، أو قائمة الإطار (**React > Build** أو **NestJS > Build**)، أو السكربت `build` من **npm Scripts**. وجرّب نسخة Vite المبنية قبل رفعها بـ **Preview the Build** من قائمة الإطار.

## النشر

### 1. موقع ثابت: Publish

لمشاريع Vite وAngular يكفي رفع محتوى المجلد `dist`. استخدم **Site > Publish...** (`Ctrl+Alt+P`، **الموقع > نشر...**) بملف تعريف FTP أو SFTP أو مجلد، واجعل مجلد المصدر هو `dist`. التفاصيل الكاملة في **دليل النشر**، الدرس 6.

### 2. Docker

**Site > Docker > Generate Dockerfile / Compose / Dev Container...** (إنشاء Dockerfile / Compose / حاوية تطوير...). تكتشف RAD IDE نوع مشروعك من `package.json`:

- **Node.js (Express / any server)**: صورة Node تشغّل الخادم.
- **NestJS**: مرحلتان: الأولى تبني بـ `npm run build`، والثانية تثبّت حزم التشغيل فقط وتشغّل `node dist/main.js`.
- **Node build -> static site (Vite / React / Vue / Angular)**: تبني بـ Node، ثم تقدّم `dist` بخادم **nginx** صغير.

ثم **Build Image** و**Compose Up** من القائمة نفسها، أو من **Docker Panel**. (تحتاج Docker أو Podman مثبتًا على جهازك.)

### 3. السحابة

**Site > Deploy to Cloud / Git / SSH...** (النشر إلى السحابة / Git / SSH...):

- **Vercel** و**Netlify** و**GitHub Pages**: مناسبة جدًا لمواقع Vite وAngular الثابتة.
- **Render** و**Railway** و**Azure App Service** وخادم **SSH**: للخوادم التي تعمل باستمرار مثل Express وNestJS.

لكل هدف **Preview / Dry Run** يعرض الأوامر قبل تنفيذها. RAD IDE لا تسجّل الدخول إلى حساباتك: سجّل أنت مرة واحدة في **Terminal** (مثل `vercel login`). التفاصيل في **دليل النشر**، الدرس 7.

## أخطاء شائعة

- **نسيان `npm install` بعد نسخ المشروع:** خطأ `Cannot find module 'express'`. شغّل **npm Scripts > npm install**.
- **رفع `node_modules` إلى الخادم أو Git:** مجلد ضخم. الخادم يثبّته بنفسه من `package.json` و`package-lock.json`.
- **وضع حزمة يحتاجها الخادم في `devDependencies`:** تعمل على جهازك، وتفشل على الخادم بعد `npm ci --omit=dev`.
- **رفع مجلد المشروع كله بدل `dist`** في المواقع الثابتة: المتصفح لا يفهم ملفات `.jsx` و`.vue` مباشرة.
- **كتابة الأسرار في الكود أو رفع `.env`:** استخدم متغيرات البيئة.

## تمرين

اكتب الدالة `checkDeploy(pkg, files)` التي تفحص المشروع قبل النشر وترجع مصفوفة بالمشاكل (أو `["جاهز للنشر"]` إن لم توجد مشاكل). المشاكل:

1. لا يوجد سكربت `build`: `ينقص سكربت build`.
2. الملف `.env` موجود في قائمة الملفات المرفوعة: `لا ترفع ملف .env`.
3. حزمة `express` موجودة في `devDependencies`: `express يجب أن تكون في dependencies`.

```js exercise
function checkDeploy(pkg, files) {
    const problems = [];
    // ...
    return problems.length ? problems : ["جاهز للنشر"];
}

const bad = { scripts: { dev: "node server.js" }, devDependencies: { express: "^5.1.0" } };
console.log(checkDeploy(bad, ["server.js", ".env"]).join("\n"));
const good = { scripts: { build: "vite build" }, dependencies: { express: "^5.1.0" } };
console.log(checkDeploy(good, ["dist/index.html"]).join("\n"));
```

```js solution
function checkDeploy(pkg, files) {
    const problems = [];
    if (!pkg.scripts || !pkg.scripts.build) problems.push("ينقص سكربت build");
    if (files.includes(".env")) problems.push("لا ترفع ملف .env");
    if (pkg.devDependencies && pkg.devDependencies.express) {
        problems.push("express يجب أن تكون في dependencies");
    }
    return problems.length ? problems : ["جاهز للنشر"];
}

const bad = { scripts: { dev: "node server.js" }, devDependencies: { express: "^5.1.0" } };
console.log(checkDeploy(bad, ["server.js", ".env"]).join("\n"));
const good = { scripts: { build: "vite build" }, dependencies: { express: "^5.1.0" } };
console.log(checkDeploy(good, ["dist/index.html"]).join("\n"));
```

```text output
ينقص سكربت build
لا ترفع ملف .env
express يجب أن تكون في dependencies
جاهز للنشر
```

## اختبر نفسك

```quiz
{"question": "أين تجد سكربتات package.json لتشغيلها بنقرة في RAD IDE؟", "choices": ["Help > About", "قائمة npm Scripts، أو Run Script بالزر الأيمن على المشروع", "Format > Align", "لا يمكن إلا بالطرفية"], "answer": 1, "explanation": "قائمة npm Scripts تعرض كل السكربتات، ومعها npm install وAdd Package...."}
```

```quiz
{"question": "حزمة `typescript` في مشروع NestJS، أين مكانها الصحيح؟", "choices": ["dependencies", "devDependencies", "لا تُكتب في package.json", "في ملف .env"], "answer": 1, "explanation": "TypeScript يُستخدم وقت البناء فقط، والخادم يشغّل `dist/main.js` المترجم."}
```

```quiz
{"question": "ما الذي يُرفع إلى استضافة ملفات ثابتة لنشر تطبيق React مبني بـ Vite؟", "choices": ["المجلد src", "المجلد node_modules", "محتوى المجلد dist بعد npm run build", "ملف package.json وحده"], "answer": 2, "explanation": "`npm run build` يجمع التطبيق في ملفات HTML وCSS وJavaScript داخل `dist`."}
```

```quiz
{"question": "أين تضع مفتاح API أثناء التطوير؟", "choices": ["داخل app.js مباشرة", "في ملف .env مضاف إلى .gitignore، وتقرؤه بـ process.env", "في package.json", "في README"], "answer": 1, "explanation": "الأسرار في متغيرات البيئة، و`.env` لا يُرفع إلى Git."}
```

## الخلاصة

- **npm Scripts** تشغّل سكربتات `package.json` بنقرة، ومعها **npm install** و**Add Package...**.
- `dependencies` للتشغيل و`devDependencies` للتطوير، واحفظ `package-lock.json` في Git.
- الإعدادات والأسرار في **متغيرات البيئة** و`.env`، لا في الكود.
- البناء: **Site > Build Production**. والنشر: **Site > Publish...** للمواقع الثابتة، أو **Docker**، أو **Deploy to Cloud / Git / SSH...**.

بهذا تكون أنهيت دليل Node.js والواجهات الأمامية: من أول موقع Node.js، إلى Express وREST Client والتصحيح، ثم React وVue وAngular وNestJS، وحتى النشر.
