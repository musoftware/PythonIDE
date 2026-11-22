# Guestbook (PHP web site + SQLite)

A guestbook web site: visitors sign it, messages are listed newest first with pages, and you can delete your own
messages. Created with File > New Project > Web > PHP Web Site (template "PHP Empty Site"), then the web root was
moved to `public/`.

**What it shows**
- `public/` is the web root (`project.radproj` > `web.root`); the code (`app/bootstrap.php`) and the database
  (`data/guestbook.sqlite`, created on the first request) are outside it and cannot be downloaded.
- PDO + SQLite prepared statements, `LIMIT/OFFSET` paging (5 per page).
- A form with CSRF token, server-side validation, Post/Redirect/Get with a flash message.
- Delete only your own messages (ids kept in the PHP session).
- `?lang=ar` switches to an **Arabic, right-to-left** page (`<html dir="rtl">`); messages use `dir="auto"`.
- `public/api.php` returns the messages as JSON (try it with the IDE's REST client).

**IDE features**: F5 runs `php -S` behind the IDE's dev server with live reload and the request log,
View > Databases, Site > Publish with the "Local folder" profile (choose a destination folder first; FTP / SFTP
profiles can be added - the live database is never uploaded).

**Run**: open the folder, **F5**.

---

# سجل الزوار (موقع PHP مع SQLite)

موقع سجل زوار: يكتب الزائر رسالة، وتظهر الرسائل من الأحدث مع تقسيم إلى صفحات، ويمكن حذف رسائلك فقط. أُنشئ من
ملف > مشروع جديد > ويب > موقع PHP ثم نُقل جذر الموقع إلى `public/`.

**ماذا يوضح**
- جذر الموقع `public/`، والكود وقاعدة البيانات خارجه فلا يمكن تنزيلهما.
- PDO وSQLite بجمل مجهزة، وتقسيم الصفحات.
- نموذج برمز CSRF، والتحقق في الخادم، وإعادة التوجيه بعد الإرسال مع رسالة.
- حذف رسائلك فقط (المعرفات محفوظة في الجلسة).
- `?lang=ar` يحول الصفحة إلى **العربية من اليمين لليسار**.
- `public/api.php` يعيد الرسائل بصيغة JSON.

**التشغيل**: افتح المجلد واضغط **F5**.
**النشر**: Site > Publish بملف "Local folder" (اختر مجلد الوجهة أولا)، ولا تُرفع قاعدة البيانات الحية أبدا.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
