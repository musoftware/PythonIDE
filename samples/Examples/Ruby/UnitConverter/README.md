# Unit Converter - Ruby (RAD IDE example)

Converts length, mass, temperature, data and speed units while you type.

## What it shows
- ComboBoxes filled from code; choosing a category reloads the unit lists
- Live conversion on `TextChanged`; Enter adds the result to the history
- Swap button / menu; ListBox history
- Conversion tables and temperature formulas (lambdas) in a module (`Units.rb`)
- Number formatting with thousands separators

## RAD IDE features
- A **Ruby GUI Bridge** project (`ruby-bridge`): the IDE draws the forms (designer + `Form*.form`), your Ruby code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Ruby; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`Units.rb`).
- F5 run, Build > Publish.

## Files
- `Form1.rb` - event handlers
- `Units.rb` - tables and formulas

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Ruby 3.x (RubyInstaller, or the IDE's toolchains\ruby).
3. Choose Temperature and type 100: `100 Celsius = 212 Fahrenheit`.
4. Press **Swap**.
5. Press Enter to keep a result in the history.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Ruby when one is available, otherwise the GUI Bridge host is bundled with the Ruby files.

---

<div dir="rtl">

# محوّل الوحدات - Ruby (مثال من RAD IDE)

يحوّل وحدات الطول والكتلة والحرارة والبيانات والسرعة أثناء الكتابة.

## ماذا يعرض
- قوائم منسدلة تُملأ من الكود؛ اختيار التصنيف يعيد تحميل الوحدات
- تحويل مباشر بحدث TextChanged؛ Enter يضيف النتيجة للسجل
- زر وقائمة للتبديل وسجل في ListBox
- جداول التحويل ومعادلات الحرارة في وحدة (`Units.rb`)
- تنسيق الأرقام بفواصل الآلاف

## مزايا بيئة التطوير المستخدمة
- مشروع **Ruby GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Ruby يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Ruby 3.x (RubyInstaller أو toolchains\ruby الخاص بالبيئة).
3. اختر Temperature واكتب 100.
4. اضغط **Swap**.
5. اضغط Enter لحفظ النتيجة في السجل.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
