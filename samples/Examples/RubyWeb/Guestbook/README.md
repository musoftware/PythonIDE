# Guestbook - Ruby / Sinatra (RAD IDE example)

A Sinatra web app: sign a guestbook with a form, search the messages, use the JSON API and switch to an Arabic
right-to-left page. Pure Ruby (sinatra + rackup + webrick gems) - no C compiler needed.

## What it shows
- Routes: `GET /`, `POST /entries` (form + server-side validation, HTTP 422 with the errors), `POST /entries/:id/delete`
- JSON API: `GET /api/entries?q=`, `POST /api/entries` (JSON body, 201 Created)
- ERB views with a layout, HTML escaping of user text, search, English / Arabic (`?lang=ar`, `dir="rtl"`)
- A JSON file "database" (`data/entries.json`) in `lib/entry_store.rb`: a Mutex for parallel requests and
  write-to-temp-then-rename

## RAD IDE features
- New Project > Web > **Ruby on Rails / Sinatra Web App**, template **Sinatra App (pure Ruby)** (`rails-web`)
- F5 / Ctrl+F5: the dev server runs `bundle install` into `vendor/bundle` the first time, then
  `bundle exec ruby app.rb -p <port>` behind the IDE's preview server (live reload)
- Routes / views IntelliSense, the Ruby CLI presets (bundle), F5 debugging with breakpoints in `app.rb`
- Site > Publish: folder / FTP / SFTP profiles

## How to run
1. File > Open Project... and choose this folder.
2. Press **Ctrl+F5** (Ruby 3.x needed; gems are installed per project). The preview opens `/`.
3. Sign the guestbook; try `/?lang=ar` and `/api/entries`.

## Publish
Site > Publish with a *Local folder* or FTP/SFTP profile copies the app (with `vendor/bundle`) to the server;
start it there with `bundle exec rackup -p 8080`.

---

<div dir="rtl">

# سجل الزوار - Ruby / Sinatra (مثال من RAD IDE)

تطبيق ويب بإطار Sinatra: وقّع في سجل الزوار بنموذج، وابحث في الرسائل، واستخدم واجهة JSON، وانتقل إلى صفحة
عربية من اليمين لليسار. Ruby خالص بدون مترجم C.

## ماذا يعرض
- مسارات GET وPOST ونموذج مع تحقق في الخادم (رمز 422 مع الأخطاء) وحذف الرسائل
- واجهة JSON للقراءة والإضافة
- قوالب ERB مع تخطيط، وحماية النص من HTML، وبحث، وصفحة عربية `?lang=ar`
- ملف JSON كقاعدة بيانات مع قفل Mutex للطلبات المتوازية

## مزايا بيئة التطوير المستخدمة
- مشروع جديد > Web > Sinatra App
- Ctrl+F5 يثبّت الحزم أول مرة ثم يشغّل الخادم خلف خادم المعاينة
- النشر من Site > Publish إلى مجلد أو FTP/SFTP

## طريقة التشغيل
1. افتح المجلد من File > Open Project.
2. اضغط **Ctrl+F5** (يحتاج Ruby 3.x).
3. وقّع في السجل وجرّب `/?lang=ar` و`/api/entries`.

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
