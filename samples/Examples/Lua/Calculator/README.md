# Calculator - Lua (RAD IDE example)

A calculator with operator precedence and parentheses, keyboard input and a history list.

## What it shows
- 16 buttons, each with its own one-line handler
- A hand-written expression parser in a module (`calc.lua`) - no `load()` of user text
- KeyPress on a read-only display: digits, + - * / ( ), Enter, Backspace, Esc
- Errors (division by zero) shown with MsgBox via `pcall`
- ListBox history: double-click reuses a result
- Menus (Edit, Help)

## RAD IDE features
- A **Lua GUI Bridge** project (`lua-bridge`): the IDE draws the forms (designer + `Form*.form`), your Lua code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Lua; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`calc.lua`).
- F5 run, Build > Publish.

## Files
- `Form1.lua` - event handlers
- `calc.lua` - tokenizer + recursive-descent evaluator

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Lua 5.4 (lua on PATH, or the LuaBinaries zip extracted into %LOCALAPPDATA%\RADIDE\toolchains\lua).
3. Click 7 * 6 - 2 = (shows 40).
4. Click the display and type `(1+2)*3` then Enter.
5. Try 1 / 0.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Lua when one is available, otherwise the GUI Bridge host is bundled with the Lua files.

---

<div dir="rtl">

# الآلة الحاسبة - Lua (مثال من RAD IDE)

آلة حاسبة تحترم أولوية العمليات والأقواس، مع إدخال من لوحة المفاتيح وسجل للعمليات.

## ماذا يعرض
- 16 زرًا لكل منها معالج من سطر واحد
- محلل تعابير مكتوب يدويًا في وحدة (`calc.lua`) بدون تنفيذ نص المستخدم
- KeyPress على شاشة للقراءة فقط: الأرقام والعمليات والأقواس وEnter وBackspace وEsc
- الأخطاء (القسمة على صفر) تظهر في رسالة عبر `pcall`
- سجل في ListBox والنقر المزدوج يعيد استخدام النتيجة
- قوائم (تحرير، مساعدة)

## مزايا بيئة التطوير المستخدمة
- مشروع **Lua GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Lua يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Lua 5.4 (في PATH أو LuaBinaries مستخرجة في %LOCALAPPDATA%\RADIDE\toolchains\lua).
3. اضغط 7 * 6 - 2 = لتظهر 40.
4. انقر الشاشة واكتب `(1+2)*3` ثم Enter.
5. جرّب 1 / 0.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
