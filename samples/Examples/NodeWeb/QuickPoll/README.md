# QuickPoll (Node.js + Express web site)

Create polls, vote once per browser, see the results as bars. Created with File > New Project > Web >
Node.js Web Site (template "Node.js Express Site").

**What it shows**
- `server.js`: an Express JSON REST API - `GET/POST /api/polls`, `GET/DELETE /api/polls/:id`,
  `POST /api/polls/:id/vote` - with validation (400), not found (404) and "already voted" (409).
- `lib/store.js`: a small data store in `data/polls.json`, written atomically (temp file + rename); voter ids are
  stored hashed and never returned by the API.
- `public/`: a front end in plain JavaScript (`fetch`, DOM, `localStorage`), English / **Arabic RTL** switch.

**Third-party**: `express` (MIT) from npm, installed by the IDE (`npm install` runs on the first F5 because
`node_modules/` is not kept in the samples).

**IDE features**: F5 starts `node server.js` with `PORT` behind the IDE's dev server (request log, restart on
change), the REST client, Site > Publish with the "Local folder" profile (excludes `node_modules` and `data`;
run `npm install --omit=dev` on the server).

**Run**: open the folder, **F5**.

---

# تصويت سريع (موقع Node.js + Express)

أنشئ تصويتات، وصوّت مرة واحدة من كل متصفح، وشاهد النتائج كأشرطة. أُنشئ من ملف > مشروع جديد > ويب > موقع Node.js.

**ماذا يوضح**
- `server.js`: واجهة REST بصيغة JSON مع التحقق من المدخلات ورموز الأخطاء.
- `lib/store.js`: حفظ البيانات في `data/polls.json` بطريقة آمنة، ومعرفات المصوتين محفوظة مشفرة.
- `public/`: واجهة بجافاسكربت عادية، مع التبديل إلى **العربية من اليمين لليسار**.

**مكونات خارجية**: حزمة `express` (رخصة MIT)، وتثبتها بيئة التطوير تلقائيا عند أول تشغيل.

**التشغيل**: افتح المجلد واضغط **F5**.
**النشر**: Site > Publish بملف "Local folder" ثم `npm install --omit=dev` على الخادم.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
