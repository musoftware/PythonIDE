# الدرس 3: Express: المسارات وواجهة REST

**في هذا الدرس ستتعلم:**

- إنشاء مشروع **Express Site** وكيف تثبّت RAD IDE حزمه تلقائيًا.
- المسارات (routes) في Express: `app.get` و`app.post` و`app.put` و`app.delete`.
- بناء **واجهة REST** (REST API) لقائمة ملاحظات ترسل وتستقبل JSON.
- البرمجيات الوسيطة (middleware) والملفات الثابتة.

## لماذا Express؟

في الدرس السابق كتبنا الخادم بالوحدة `http` وحدها، وفحصنا المسارات بسلسلة `if`. هذا ممكن لموقع صغير، لكنه يصبح متعبًا مع عشرات المسارات وقراءة بيانات JSON والملفات الثابتة. **Express** أشهر حزمة خوادم في Node.js، تختصر كل ذلك في أسطر قليلة واضحة.

## الخطوة 1: إنشاء مشروع Express

1. **File > New Project > Web > Node.js Web Site (Express)**.
2. اختر القالب **Express Site**، وسمِّه `NotesApi`.
3. اضغط `Ctrl+F5`. في أول تشغيل ترى في **Output** الأمر `npm install` يعمل وحده (لأن `package.json` فيه `express` والمجلد `node_modules` غير موجود)، ثم يبدأ الخادم.

الملف الرئيسي `app.js` في القالب:

```js
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/time', (req, res) => res.json({ time: new Date().toISOString() }));

app.listen(PORT, () => console.log(`NotesApi listening on port ${PORT}`));
```

- `app.use(express.json())` **برمجية وسيطة** تقرأ جسم الطلب إن كان JSON وتضعه في `req.body`.
- `app.use(express.static(...))` ترسل ملفات المجلد `public` كما هي (HTML وCSS وصور).
- `app.get('/api/time', ...)` مسار: عند طلب `GET /api/time` تُنفَّذ الدالة، و`res.json(...)` ترسل كائنًا بصيغة JSON مع نوع المحتوى الصحيح.

## ما هي واجهة REST؟

**REST** طريقة متفق عليها لتصميم الواجهات البرمجية: كل «مورد» (مثل الملاحظات) له عنوان، والعملية تحددها **طريقة HTTP**:

| الطريقة | العنوان | المعنى |
|---|---|---|
| `GET` | `/api/notes` | اعرض كل الملاحظات |
| `GET` | `/api/notes/3` | اعرض الملاحظة رقم 3 |
| `POST` | `/api/notes` | أضف ملاحظة جديدة (البيانات في جسم الطلب) |
| `PUT` | `/api/notes/3` | عدّل الملاحظة رقم 3 |
| `DELETE` | `/api/notes/3` | احذف الملاحظة رقم 3 |

ورموز الحالة الشائعة: `200` نجاح، و`201` أُنشئ عنصر جديد، و`204` نجاح بلا محتوى، و`400` طلب غير صالح، و`404` غير موجود، و`500` خطأ في الخادم.

> **تشبيه:** REST مثل **أدراج مكتب** مرقّمة: `GET` تفتح الدرج وتنظر، و`POST` تضع ورقة جديدة، و`PUT` تستبدل الورقة، و`DELETE` ترميها.

## الخطوة 2: واجهة الملاحظات بـ Express

استبدل محتوى `app.js` بهذا الكود:

```js
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

let notes = [{ id: 1, text: 'أول ملاحظة', done: false }];
let nextId = 2;

app.get('/api/notes', (req, res) => {
    res.json(notes);
});

app.get('/api/notes/:id', (req, res) => {
    const note = notes.find((n) => n.id === Number(req.params.id));
    if (!note) return res.status(404).json({ error: 'غير موجودة' });
    res.json(note);
});

app.post('/api/notes', (req, res) => {
    const text = String(req.body.text || '').trim();
    if (!text) return res.status(400).json({ error: 'النص مطلوب' });
    const note = { id: nextId++, text, done: false };
    notes.push(note);
    res.status(201).json(note);
});

app.put('/api/notes/:id', (req, res) => {
    const note = notes.find((n) => n.id === Number(req.params.id));
    if (!note) return res.status(404).json({ error: 'غير موجودة' });
    if (req.body.text !== undefined) note.text = String(req.body.text);
    if (req.body.done !== undefined) note.done = Boolean(req.body.done);
    res.json(note);
});

app.delete('/api/notes/:id', (req, res) => {
    const before = notes.length;
    notes = notes.filter((n) => n.id !== Number(req.params.id));
    res.status(notes.length < before ? 204 : 404).end();
});

app.listen(PORT, () => console.log(`NotesApi listening on port ${PORT}`));
```

- `:id` في المسار **معامل**: في الطلب `/api/notes/7` تكون `req.params.id` هي النص `"7"`، لذلك نحوّلها بـ `Number`.
- `res.status(404).json(...)` تضبط رقم الحالة ثم ترسل JSON.
- `return` قبل `res.status(...)` تمنع إرسال ردّين لطلب واحد.

احفظ (يعيد RAD IDE تشغيل الخادم وحده)، ثم افتح في المعاينة العنوان `/api/notes`. لتجربة `POST` و`PUT` و`DELETE` نحتاج أداة ترسل طلبات، وهذا موضوع الدرس القادم (REST Client).

## ماذا يفعل Express خلف الكواليس؟

حتى تفهم ما توفره Express، هذا المنطق نفسه مختصرًا بالوحدة `http` وحدها، ويجرّب نفسه بـ `fetch` ثم يتوقف (هذا المثال يعمل بلا تثبيت أي حزمة، فاضغط «جرّبه»):

```js run
const http = require("node:http");

let notes = [{ id: 1, text: "أول ملاحظة" }];
let nextId = 2;

function send(res, status, data) {
    res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
    res.end(data === undefined ? "" : JSON.stringify(data));
}

function readJson(req) {
    return new Promise((resolve) => {
        let body = "";
        req.on("data", (chunk) => (body += chunk));
        req.on("end", () => {
            try { resolve(body ? JSON.parse(body) : {}); } catch { resolve(null); }
        });
    });
}

const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, "http://localhost");
    const m = url.pathname.match(/^\/api\/notes(?:\/(\d+))?$/);
    if (!m) return send(res, 404, { error: "مسار غير معروف" });
    const id = m[1] ? Number(m[1]) : null;

    if (req.method === "GET" && id === null) return send(res, 200, notes);
    if (req.method === "POST" && id === null) {
        const body = await readJson(req);
        if (!body || !body.text) return send(res, 400, { error: "النص مطلوب" });
        const note = { id: nextId++, text: body.text };
        notes.push(note);
        return send(res, 201, note);
    }
    if (req.method === "DELETE" && id !== null) {
        const before = notes.length;
        notes = notes.filter((n) => n.id !== id);
        return send(res, notes.length < before ? 204 : 404);
    }
    send(res, 405, { error: "طريقة غير مسموحة" });
});

server.listen(0, "127.0.0.1", async () => {
    const base = `http://127.0.0.1:${server.address().port}/api/notes`;
    const show = async (label, r) => console.log(label, r.status, await r.text());
    const json = { "Content-Type": "application/json" };

    await show("POST", await fetch(base, { method: "POST", headers: json, body: JSON.stringify({ text: "شراء خبز" }) }));
    await show("POST فارغ", await fetch(base, { method: "POST", headers: json, body: "{}" }));
    await show("DELETE 1", await fetch(base + "/1", { method: "DELETE" }));
    await show("GET", await fetch(base));
    server.close();
});
```

```text output
POST 201 {"id":2,"text":"شراء خبز"}
POST فارغ 400 {"error":"النص مطلوب"}
DELETE 1 204
GET 200 [{"id":2,"text":"شراء خبز"}]
```

لاحظ كم سطرًا وفّرته Express: قراءة JSON (`express.json()`)، ومطابقة المسارات ومعاملاتها (`:id`)، وإرسال JSON (`res.json`).

## البرمجيات الوسيطة (Middleware)

**البرمجية الوسيطة** دالة تمر عليها كل الطلبات قبل أن تصل إلى المسار، مثل حارس البوابة. مثال يسجّل كل طلب ويقيس زمنه:

```js
app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => console.log(`${req.method} ${req.url} ${res.statusCode} ${Date.now() - start}ms`));
    next();          // مرّر الطلب إلى ما بعدها
});
```

ومعالج أخطاء عام يُكتب **في آخر الملف** بأربعة معاملات:

```js
app.use((err, req, res, next) => {
    console.error(err);
    res.status(500).json({ error: 'حدث خطأ في الخادم' });
});
```

## تقسيم المسارات إلى ملفات

عندما تكثر المسارات، ضعها في مجلد `routes`. في مشاريع Express تظهر في شريط القوائم قائمة **Express** فيها **Start** و**Start with Auto Reload (node --watch)** و**New Route File...** الذي يسألك عن اسم المسار وينشئ ملف مسارات جاهزًا في المجلد `routes` (تجده أيضًا بالزر الأيمن على المجلد `routes` في **Solution Explorer**). شكل الملف:

```js
// routes/notes.js
const express = require('express');
const router = express.Router();

router.get('/', (req, res) => res.json([]));

module.exports = router;
```

وفي `app.js`:

```js
app.use('/api/notes', require('./routes/notes'));
```

## أخطاء شائعة

- **`Cannot find module 'express'`:** لم تكتمل `npm install`. انظر رسائل **Output**، أو اختر **npm Scripts > npm install**.
- **`req.body` تساوي `undefined`:** نسيت `app.use(express.json())`، أو أن الطلب لم يرسل الترويسة `Content-Type: application/json`.
- **`Cannot set headers after they are sent`:** أرسلت ردّين لطلب واحد. ضع `return` قبل كل `res.json` داخل `if`.
- **ترتيب المسارات:** Express يأخذ أول مسار يطابق. ضع المسارات الخاصة قبل العامة، ومعالج الأخطاء في الآخر.

## تمارين

### التمرين 1

اكتب الدالة `validateNote(body)` التي يستخدمها مسار `POST`: ترجع `null` إن كانت البيانات صالحة، أو نص الخطأ: «النص مطلوب» إن كان `text` فارغًا أو غير موجود، و«النص طويل جدًا» إن زاد على 100 حرف.

```js exercise
function validateNote(body) {
    // ...
}

console.log(validateNote({ text: "مذاكرة" }));
console.log(validateNote({}));
console.log(validateNote({ text: "   " }));
console.log(validateNote({ text: "x".repeat(101) }));
```

```js solution
function validateNote(body) {
    const text = String((body && body.text) || "").trim();
    if (!text) return "النص مطلوب";
    if (text.length > 100) return "النص طويل جدًا";
    return null;
}

console.log(validateNote({ text: "مذاكرة" }));
console.log(validateNote({}));
console.log(validateNote({ text: "   " }));
console.log(validateNote({ text: "x".repeat(101) }));
```

```text output
null
النص مطلوب
النص مطلوب
النص طويل جدًا
```

### التمرين 2 (في RAD IDE)

في مشروع Express أضف المسار `GET /api/notes/count` الذي يرد بـ `{ "total": ..., "done": ... }`. ضعه **قبل** المسار `/api/notes/:id`، وإلا اعتبر Express الكلمة `count` رقمًا لملاحظة! ثم افتح العنوان في المعاينة.

## اختبر نفسك

```quiz
{"question": "أي طريقة HTTP تُستخدم لإضافة عنصر جديد في REST؟", "choices": ["GET", "POST", "DELETE", "PUT"], "answer": 1, "explanation": "POST للإنشاء، وGET للقراءة، وPUT للتعديل، وDELETE للحذف."}
```

```quiz
{"question": "في المسار `/api/notes/:id` والطلب `/api/notes/7`، ما قيمة `req.params.id`؟", "choices": ["الرقم 7", "النص \"7\"", "undefined", "\":id\""], "answer": 1, "explanation": "معاملات المسار نصوص دائمًا، فنحوّلها بـ `Number`."}
```

```quiz
{"question": "ما فائدة `app.use(express.json())`؟", "choices": ["ترسل كل الردود بصيغة JSON", "تقرأ جسم الطلب المكتوب بـ JSON وتضعه في `req.body`", "تحفظ البيانات في ملف", "تشغّل الخادم"], "answer": 1, "explanation": "هي برمجية وسيطة لقراءة أجسام طلبات JSON."}
```

## الخلاصة

- **Express Site**: القالب يثبّت `express` تلقائيًا في أول تشغيل.
- المسارات: `app.get/post/put/delete(المسار, (req, res) => ...)`، و`req.params` و`req.query` و`req.body`.
- REST: الطريقة تحدد العملية، ورموز الحالة تخبر بالنتيجة.
- البرمجيات الوسيطة `app.use(...)` و`express.Router()` لتنظيم المسارات.
