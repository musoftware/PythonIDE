# Contacts - Ruby (RAD IDE example)

An address book: add, edit, delete and search contacts, stored as JSON, with Arabic and English names.

## What it shows
- CRUD with validation (name, phone characters, email format)
- DataGridView: selecting a row fills the fields (`SelectedIndexChanged`)
- Live search with `TextChanged` (works with Arabic text)
- JSON persistence and CSV export in a module (`ContactStore.rb`, a Struct)
- Delete confirmation with InputBox; menus; StatusBar

## RAD IDE features
- A **Ruby GUI Bridge** project (`ruby-bridge`): the IDE draws the forms (designer + `Form*.form`), your Ruby code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Ruby; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`ContactStore.rb`).
- F5 run, Build > Publish.

## Files
- `Form1.rb` - event handlers
- `ContactStore.rb` - contacts.json, validation, search, CSV

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Ruby 3.x (RubyInstaller, or the IDE's toolchains\ruby).
3. Type a name and phone and press **Add**.
4. Search for `القاهرة`.
5. Select a row, change the phone, **Update**.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Ruby when one is available, otherwise the GUI Bridge host is bundled with the Ruby files.

---

<div dir="rtl">

# جهات الاتصال - Ruby (مثال من RAD IDE)

دفتر عناوين: إضافة وتعديل وحذف والبحث في جهات الاتصال، محفوظة بصيغة JSON، بأسماء عربية وإنجليزية.

## ماذا يعرض
- إضافة وتعديل وحذف مع التحقق (الاسم والهاتف والبريد)
- اختيار صف في الجدول يملأ الحقول
- بحث مباشر بحدث TextChanged (يعمل مع النص العربي)
- حفظ JSON وتصدير CSV في وحدة (`ContactStore.rb`)
- تأكيد الحذف عبر InputBox وقوائم وشريط حالة

## مزايا بيئة التطوير المستخدمة
- مشروع **Ruby GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Ruby يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Ruby 3.x (RubyInstaller أو toolchains\ruby الخاص بالبيئة).
3. اكتب الاسم والهاتف واضغط **Add**.
4. ابحث عن `القاهرة`.
5. اختر صفًا وعدّل الهاتف ثم **Update**.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
