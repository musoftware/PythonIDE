# CityGuideSite - City Guide (static site, Arabic RTL page)

**Language / project type:** `static-web` (created with File > New Project, then customised)

Multi-page HTML/CSS/JS site: filterable list, favourites in localStorage, validated contact form, RTL Arabic page.

## What it shows
- Pages sharing one stylesheet; logical CSS properties (margin-inline) so the same CSS works LTR and RTL
- Data-driven list with filtering; favourites and form drafts in localStorage
- Contact form validated in JavaScript (no server)
- ar/index.html: lang="ar" dir="rtl"
- A hand-written SVG picture

## Run
Open the folder, F5: the IDE's built-in web server + preview with live reload. Try Design/Split view on a page.

## Publish
Site > Publish: "Local folder" profile (or add an FTP/SFTP profile).

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py Web/CityGuideSite` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# دليل المدينة (موقع ثابت وصفحة عربية)

موقع HTML/CSS/JS متعدد الصفحات: قائمة قابلة للتصفية ومفضلة محفوظة ونموذج اتصال وصفحة عربية من اليمين لليسار.

## ماذا يوضح
- صفحات بملف تنسيق واحد يعمل يمينًا ويسارًا
- قائمة من بيانات JavaScript مع تصفية ومفضلة محفوظة
- نموذج اتصال يُتحقق منه بـ JavaScript
- صفحة عربية dir=rtl
- صورة SVG

## التشغيل
افتح المجلد واضغط F5: خادم الويب المدمج مع معاينة وتحديث تلقائي.

## النشر
Site > Publish: "Local folder" profile (or add an FTP/SFTP profile).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
