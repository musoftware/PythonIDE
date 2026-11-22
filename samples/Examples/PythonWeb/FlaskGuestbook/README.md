# FlaskGuestbook - Flask Guestbook (SQLite)

**Language / project type:** `python-flask` (created with File > New Project, then customised)

Sign/list/search/delete messages with validation, flash messages, SQLite and a JSON API.

## What it shows
- Application factory + two blueprints (pages, /api)
- sqlite3 per request (flask.g), `flask --app app init-db` command
- Form validation, flash messages, search + paging, POST delete
- 3 unit tests (View > Flask > Run tests); Local folder publish profile

## Run
Open the folder, Ctrl+F5 (the IDE creates .venv and installs Flask the first time). Sign the guestbook, search, delete.

## Publish
Site > Publish: profile "Local folder" (choose the destination; .venv/instance are excluded). For a real host use FTP/SFTP + a WSGI server.

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py PythonWeb/FlaskGuestbook` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# دفتر الزوار بـ Flask (SQLite)

إضافة الرسائل وعرضها والبحث والحذف مع التحقق ورسائل التنبيه وقاعدة SQLite وواجهة JSON.

## ماذا يوضح
- مصنع التطبيق ومخططان للصفحات وواجهة API
- SQLite لكل طلب وأمر init-db
- التحقق من النموذج والبحث والتقسيم لصفحات والحذف
- اختبارات وملف نشر إلى مجلد

## التشغيل
افتح المجلد واضغط Ctrl+F5 (أول مرة يُنشئ البيئة ويثبت Flask). وقّع في الدفتر وابحث واحذف.

## النشر
Site > Publish: profile "Local folder" (choose the destination; .venv/instance are excluded). For a real host use FTP/SFTP + a WSGI server.

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
