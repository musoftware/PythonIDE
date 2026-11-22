# FastApiTasks - FastAPI Tasks (REST + SQLite)

**Language / project type:** `python-fastapi` (created with File > New Project, then customised)

To-do REST API with Pydantic validation, SQLite and a fetch() page; /docs.

## What it shows
- GET/POST/PATCH/DELETE routes, query filter, status codes, HTTPException
- Pydantic models (Field, Literal), automatic /docs
- Jinja2 page + static JS that calls the API with fetch()
- TestClient tests (need httpx)

## Run
Open the folder, Ctrl+F5. Add tasks on the page or try the API in View > FastAPI > Open /docs.

## Publish
Site > Publish: "Local folder" profile (.venv / tasks.db excluded).

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py PythonWeb/FastApiTasks` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# مهام FastAPI (REST و SQLite)

واجهة REST لقائمة المهام مع تحقق Pydantic وقاعدة SQLite وصفحة تستخدم fetch().

## ماذا يوضح
- مسارات GET/POST/PATCH/DELETE ورموز الحالة
- نماذج Pydantic وتوثيق تلقائي /docs
- صفحة HTML تستخدم fetch()
- اختبارات TestClient

## التشغيل
افتح المجلد واضغط Ctrl+F5. أضف مهام من الصفحة أو جرّب الواجهة من /docs.

## النشر
Site > Publish: "Local folder" profile (.venv / tasks.db excluded).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
