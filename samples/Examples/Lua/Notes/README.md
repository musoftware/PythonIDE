# Notes - Lua (RAD IDE example)

A notes app with a list, a multi-line editor, a modal Find dialog and UTF-8 storage (Arabic notes included).

## What it shows
- Two forms: Form1 and a modal Find dialog (`CALL FindForm ShowDialog`); the dialog's OK/Cancel handlers do the work
- Multi-line text over the bridge (`ESC GET/SET`)
- ListBox selection opens a note; New / Save / Delete (InputBox confirmation)
- A UTF-8 text file format written by a module (`notestore.lua`), Arabic text
- Menus, StatusBar, KeyPress (Enter = Find)

## RAD IDE features
- A **Lua GUI Bridge** project (`lua-bridge`): the IDE draws the forms (designer + `Form*.form`), your Lua code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Lua; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`notestore.lua`).
- F5 run, Build > Publish.

## Files
- `Form1.lua` - list + editor
- `FindForm.lua` - the Find dialog
- `notestore.lua` - notes.txt format, search, multi-line helpers

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Lua 5.4 (lua on PATH, or the LuaBinaries zip extracted into %LOCALAPPDATA%\RADIDE\toolchains\lua).
3. Select the Arabic note to see right-to-left text.
4. New, type a title and text, Save.
5. Edit > Find..., type a word, press Find.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Lua when one is available, otherwise the GUI Bridge host is bundled with the Lua files.

---

<div dir="rtl">

# الملاحظات - Lua (مثال من RAD IDE)

تطبيق ملاحظات بقائمة ومحرر متعدد الأسطر ونافذة بحث مشروطة وحفظ UTF-8 (يشمل ملاحظات عربية).

## ماذا يعرض
- نموذجان: النموذج الرئيسي ونافذة بحث مشروطة؛ أزرار موافق / إلغاء في النافذة تنفذ العمل
- نص متعدد الأسطر عبر الجسر (`ESC GET/SET`)
- اختيار عنصر من القائمة يفتح الملاحظة؛ جديد / حفظ / حذف مع تأكيد
- ملف نصي UTF-8 تكتبه وحدة (`notestore.lua`) مع نص عربي
- قوائم وشريط حالة وKeyPress (Enter للبحث)

## مزايا بيئة التطوير المستخدمة
- مشروع **Lua GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Lua يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Lua 5.4 (في PATH أو LuaBinaries مستخرجة في %LOCALAPPDATA%\RADIDE\toolchains\lua).
3. اختر الملاحظة العربية لترى النص من اليمين لليسار.
4. جديد، اكتب العنوان والنص ثم حفظ.
5. تحرير > بحث، اكتب كلمة واضغط Find.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
