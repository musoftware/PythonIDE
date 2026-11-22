<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# Ring Guestbook (web)

RingHTTPLib web app: HTML form, SQLite storage, JSON API, Post/Redirect/Get, escaping.

## What it shows

- Routes: `GET /`, `POST /sign`, `GET /api/entries`, `GET /about`
- Page template `templates/index.html` with placeholders, HTML escaping
- SQLite (`guestbook.db`), server-side validation, 303 redirect after POST
- JSON output built by hand with string escaping; Arabic text kept as UTF-8
- Port from the `PORT` environment variable (default 8080)

**Language / project type:** `ring-app`

## Run

F5 / Ctrl+F5, then open http://localhost:8080 . Stop with Debug > Stop.

## Publish

Build > Publish (ring2exe) makes `RingGuestbook.exe`; copy `templates/` next to it.

<div dir="rtl">

# سجل زوار Ring (ويب)

تطبيق ويب بـ RingHTTPLib: نموذج HTML وتخزين SQLite وواجهة JSON وتحويل بعد الإرسال.

## ماذا يوضح

- مسارات GET و POST وواجهة JSON
- قالب صفحة مع حماية من حقن HTML
- قاعدة SQLite وتحقق من المدخلات وتحويل 303 بعد الإرسال
- دعم النص العربي UTF-8
- المنفذ من متغير البيئة PORT

## التشغيل

اضغط F5 ثم افتح http://localhost:8080 وأوقفه من Debug > Stop.

## النشر

من القائمة Build > Publish لإنشاء ملف تنفيذي (انظر جدول النتائج).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License. Tested by `samples/Tests/Examples/test_examples_scripting.py --group ring`.
