# DjangoLibrary - Django Library

**Language / project type:** `python-django` (created with File > New Project, then customised)

Books and authors: models, admin, ModelForm add/edit, lend/return with CSRF, search, JSON.

## What it shows
- Models Author/Book with a migration, Django admin with inline books + filters
- ModelForm with custom validation, function views, messages framework, CSRF forms
- Search + genre filter + Paginator, aggregate (Count), JSON endpoint
- `seed_library` management command, 2 tests (manage.py test core)

## Run
Open the folder, Ctrl+F5 (creates .venv, installs Django, runs migrate). View > Django > Run command... seed_library adds sample books. /admin needs `createsuperuser`.

## Publish
Site > Publish: "Local folder" profile (.venv and db.sqlite3 excluded).

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py PythonWeb/DjangoLibrary` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# مكتبة Django

كتب ومؤلفون: نماذج وإدارة ونموذج إضافة وتعديل وإعارة وإرجاع وبحث وواجهة JSON.

## ماذا يوضح
- نماذج مع ترحيل ولوحة إدارة
- نموذج ModelForm وتحقق مخصص ورسائل وحماية CSRF
- بحث وتصفية وتقسيم لصفحات
- أمر seed_library واختبارات

## التشغيل
افتح المجلد واضغط Ctrl+F5. لإضافة كتب تجريبية: View > Django > Run command ثم seed_library.

## النشر
Site > Publish: "Local folder" profile (.venv and db.sqlite3 excluded).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
