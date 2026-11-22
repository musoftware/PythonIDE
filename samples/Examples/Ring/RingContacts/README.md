<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# Ring Contacts (SQLite)

Address book CRUD with SQLite, live search, a modal Settings form, saved settings, Arabic RTL.

## What it shows

- Two forms: Form1 (contacts) and Form2 (Settings, shown modal with `setWindowModality`)
- SQLite through Ring's `sqlitelib.ring`: create table, insert / update / delete / search
- ListBox filled from a query, SelectedIndexChanged fills the TextBoxes
- Live search (TextChanged) with SQL LIKE, safe SQL quoting
- Saved settings in `settings.ini` (language, confirm before delete)
- Arabic interface: Arabic labels and right-to-left layout direction (`setLayoutDirection(1)`)
- qMessageBox Yes/No question, CSV export with the SaveFileDialog component

**Language / project type:** `ring-qt`

## Run

F5. `contacts.db` is created on the first run with three sample contacts. Settings... > العربية > OK.

## Publish

Build > Publish (ring2exe): `RingContacts.exe` + Qt + ring_sqlite.dll, no Python.

<div dir="rtl">

# جهات الاتصال بـ Ring و SQLite

دفتر عناوين بقاعدة SQLite وبحث مباشر ونافذة إعدادات مشروطة وحفظ الإعدادات وواجهة عربية.

## ماذا يوضح

- نافذتان: جهات الاتصال ونافذة الإعدادات المشروطة
- قاعدة SQLite عبر مكتبة sqlitelib: إنشاء وإضافة وتعديل وحذف وبحث
- قائمة تُملأ من استعلام واختيار عنصر يملأ الحقول
- بحث مباشر أثناء الكتابة
- حفظ الإعدادات في settings.ini
- واجهة عربية من اليمين لليسار
- رسالة تأكيد نعم/لا وتصدير CSV

## التشغيل

اضغط F5. يُنشأ contacts.db في أول تشغيل بثلاث جهات اتصال. الإعدادات > العربية > موافق.

## النشر

من القائمة Build > Publish لإنشاء ملف تنفيذي (انظر جدول النتائج).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License. Tested by `samples/Tests/Examples/test_examples_scripting.py --group ring`.
