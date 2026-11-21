# الدرس 2: أول موقع Node.js: التشغيل والمعاينة ونافذة الطلبات

**في هذا الدرس ستتعلم:**

- إنشاء مشروع **Node.js Empty Site** وفهم ملفاته.
- تشغيل الموقع في **Preview** (المعاينة) ومتابعة الطلبات في نافذة **Requests**.
- كيف يعمل خادم الويب: الطلب (request) والرد (response) والمسار (path).
- إعادة التحميل التلقائي (live reload)، و**Site Settings** (إعدادات الموقع).

## كيف يعمل الويب؟

عندما تكتب عنوانًا في المتصفح يحدث هذا:

1. المتصفح يرسل **طلبًا** (request) إلى الخادم: «أعطني الصفحة `/about`».
2. الخادم يقرأ الطلب، ويجهّز **ردًا** (response): رقم حالة مثل `200` (نجاح) أو `404` (غير موجود)، ونوع المحتوى، والمحتوى نفسه (HTML أو JSON أو صورة).
3. المتصفح يعرض الرد.

> **تشبيه:** الخادم مثل **موظف الاستقبال** في فندق. كل نزيل (متصفح) يأتي بطلب: «مفتاح الغرفة 12» أو «قائمة الطعام». الموظف يفهم الطلب ويرد بالشيء المناسب، أو يقول «آسف، غير موجود» (404).

## الخطوة 1: إنشاء الموقع

1. **File > New Project** (`Ctrl+Shift+N`).
2. من المجموعة **Web** (ويب) اختر **Node.js Web Site (Express)**.
3. من القوالب اختر **Node.js Empty Site**، واكتب الاسم `MySite`، ثم **OK**.

يظهر في **Solution Explorer** (مستكشف الحلول):

| الملف | ما فيه |
|---|---|
| `server.js` | الخادم: يرد على `/api/time` بـ JSON، ويرسل باقي الملفات من المجلد `public` |
| `public/index.html` | الصفحة الرئيسية |
| `public/css/site.css` | التنسيق |
| `package.json` | وصف المشروع، فيه `"main": "server.js"` والسكربت `start` |

هذا القالب لا يحتاج أي حزمة: يستخدم الوحدة المدمجة `http` فقط.

## الخطوة 2: التشغيل

اضغط `Ctrl+F5` (أو **Site > Run Site in Preview**). ستحدث ثلاثة أشياء:

1. تشغّل RAD IDE الأمر `node server.js` وتعطيه رقم منفذ (port) حرًّا في متغير البيئة `PORT`. لذلك يحتوي الكود على `process.env.PORT`.
2. تظهر نافذة **Preview** (معاينة) وفيها موقعك، وأعلاها شريط عنوان، وقائمة **أحجام الأجهزة** (لترى الموقع بحجم هاتف أو جهاز لوحي)، والزر **Rotate** لتدوير الشاشة، والخيار **Live reload**.
3. في نافذة **Requests** (الطلبات) يظهر كل طلب: `GET /` ثم `GET /css/site.css` ثم `GET /api/time`، مع الحالة والزمن والحجم. انقر على أي طلب لترى تفاصيله، وبالزر الأيمن تجد **Copy as curl** و**Open in Preview** و**Open in Browser**.

ورسائل `console.log` في الخادم تظهر في نافذة **Output** (المخرجات)، مثل: `MySite listening on port ...`.

## الخطوة 3: إعادة التحميل التلقائي

غيّر عنوان الصفحة في `public/index.html` واضغط `Ctrl+S` (**Save All**). تتحدث المعاينة وحدها دون أن تضغط شيئًا، لأن **Live reload** مفعّل. وعندما تغيّر ملفًا من ملفات الخادم (مثل `server.js`) تعيد RAD IDE تشغيل الخادم تلقائيًا. وإن احتجت ذلك بيدك فاختر **Site > Restart Web Server**.

## الخطوة 4: خادمك الأول بيدك

لنفهم ما يفعله `server.js`، هذا خادم صغير جدًا. ولأن أمثلة الدروس يجب أن تنتهي وحدها، يطلب المثال من نفسه بعض الصفحات بـ `fetch` ويطبع الردود، ثم يغلق الخادم. في موقعك الحقيقي لا تكتب الجزء الأخير، بل يبقى الخادم يعمل وتزوره من المعاينة:

```js run
const http = require("node:http");

const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    if (url.pathname === "/") {
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        res.end("<h1>مرحبًا من Node.js</h1>");
    } else if (url.pathname === "/api/hello") {
        const name = url.searchParams.get("name") || "زائر";
        res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
        res.end(JSON.stringify({ message: `أهلًا يا ${name}` }));
    } else {
        res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
        res.end("الصفحة غير موجودة");
    }
});

// نجرّب الخادم ثم نغلقه (في الموقع الحقيقي: server.listen(process.env.PORT || 3000))
server.listen(0, "127.0.0.1", async () => {
    const base = `http://127.0.0.1:${server.address().port}`;
    for (const path of ["/", "/api/hello?name=سارة", "/missing"]) {
        const r = await fetch(base + encodeURI(path));
        console.log(r.status, r.headers.get("content-type").split(";")[0], await r.text());
    }
    server.close();
});
```

```text output
200 text/html <h1>مرحبًا من Node.js</h1>
200 application/json {"message":"أهلًا يا سارة"}
404 text/plain الصفحة غير موجودة
```

- `http.createServer((req, res) => { ... })` تنشئ الخادم، والدالة تُنفَّذ مع **كل** طلب.
- `req.url` المسار المطلوب، و`new URL(...)` تفصله إلى `pathname` و`searchParams` (ما بعد `?`).
- `res.writeHead(الحالة, الترويسات)` ثم `res.end(المحتوى)` لإرسال الرد.
- `charset=utf-8` في نوع المحتوى ضرورية لتظهر العربية صحيحة في المتصفح.
- `server.listen(0)` يعني «اختر أي منفذ حر»، وهذا مفيد في الأمثلة فقط.

## الخطوة 5: إعدادات الموقع

من **Site > Site Settings...** (إعدادات الموقع...) تضبط:

| الإعداد | معناه |
|---|---|
| **Start file:** | ملف الخادم الذي يشغّله `node` (مثل `server.js` أو `app.js`) |
| **Port:** | المنفذ الثابت إن أردته (وإلا تختار RAD IDE منفذًا حرًا) |
| **Reload the browser when a file is saved (live reload)** | إعادة التحميل التلقائي |
| **Web root:** | المجلد الذي يُعتبر جذر الموقع |

## أخطاء شائعة

- **كتابة رقم منفذ ثابت فقط:** `server.listen(3000)` قد يتعارض مع برنامج آخر. اكتب `process.env.PORT || 3000` لتأخذ المنفذ من RAD IDE.
- **نسيان `res.end()`:** يبقى المتصفح ينتظر الرد إلى الأبد، وتظهر الحالة في Requests بلا نهاية.
- **العربية تظهر رموزًا:** أضف `charset=utf-8` إلى `Content-Type`، و`<meta charset="utf-8">` في ملفات HTML.
- **المنفذ مستخدم:** رسالة `EADDRINUSE` تعني أن خادمًا آخر يعمل على المنفذ نفسه. أوقفه من **Site > Stop Web Server** أو غيّر المنفذ.

## تمارين

### التمرين 1

أضف إلى الخادم المسار `/api/sum` الذي يقرأ العددين `a` و`b` من العنوان ويرد بـ JSON فيه مجموعهما، مثل `{"sum":12}` للعنوان `/api/sum?a=5&b=7`.

```js exercise
const http = require("node:http");

const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    // إن كان url.pathname هو "/api/sum" فاقرأ a و b وأرسل { sum: ... }
    res.writeHead(404);
    res.end();
});

server.listen(0, "127.0.0.1", async () => {
    const r = await fetch(`http://127.0.0.1:${server.address().port}/api/sum?a=5&b=7`);
    console.log(r.status, await r.text());
    server.close();
});
```

```js solution
const http = require("node:http");

const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    if (url.pathname === "/api/sum") {
        const a = Number(url.searchParams.get("a"));
        const b = Number(url.searchParams.get("b"));
        res.writeHead(200, { "Content-Type": "application/json" });
        return res.end(JSON.stringify({ sum: a + b }));
    }
    res.writeHead(404);
    res.end();
});

server.listen(0, "127.0.0.1", async () => {
    const r = await fetch(`http://127.0.0.1:${server.address().port}/api/sum?a=5&b=7`);
    console.log(r.status, await r.text());
    server.close();
});
```

```text output
200 {"sum":12}
```

### التمرين 2 (في RAD IDE)

1. أنشئ **Node.js Empty Site**، وشغّله بـ `Ctrl+F5`.
2. أضف إلى `server.js` المسار `/api/hello` من المثال أعلاه، واحفظ.
3. اكتب في شريط عنوان المعاينة `/api/hello?name=Ali` واضغط Enter.
4. افتح نافذة **Requests** وانقر على الطلب لترى حالته (`200`) ومحتواه.

## اختبر نفسك

```quiz
{"question": "لماذا نكتب `process.env.PORT` في الخادم؟", "choices": ["لأنه أسرع", "لأن RAD IDE تعطي الخادم منفذًا حرًا في متغير البيئة PORT", "لحماية الخادم من الاختراق", "لا داعي لذلك"], "answer": 1, "explanation": "RAD IDE تختار منفذًا حرًا وتمرره في `PORT`، فلا يتعارض الموقع مع برامج أخرى."}
```

```quiz
{"question": "ماذا يعني رقم الحالة 404؟", "choices": ["نجاح", "الصفحة غير موجودة", "خطأ في الخادم", "تحويل إلى صفحة أخرى"], "answer": 1, "explanation": "200 نجاح، و404 غير موجود، و500 خطأ داخل الخادم."}
```

```quiz
{"question": "عدّلت `public/index.html` وحفظت. ماذا يحدث في المعاينة؟", "choices": ["لا شيء حتى تعيد تشغيل الـ IDE", "تتحدث الصفحة وحدها بفضل Live reload", "يُحذف الملف", "يتوقف الخادم"], "answer": 1, "explanation": "Live reload يعيد تحميل الصفحة عند الحفظ، وتغيير ملفات الخادم يعيد تشغيله."}
```

## الخلاصة

- **Node.js Empty Site**: الملف `server.js` والمجلد `public`، بلا حزم.
- `Ctrl+F5` يشغّل الخادم ويعرض **Preview**، ونافذة **Requests** تعرض كل طلب.
- الخادم: `http.createServer((req, res) => ...)` ثم `res.writeHead` و`res.end`، والمنفذ من `process.env.PORT`.
- Live reload وإعادة التشغيل التلقائي و**Site Settings...** تجعل التجربة سريعة.
