# Guess the Number - Lua (RAD IDE example)

A small game: guess the secret number with hints, a timer, a limited number of tries and saved best scores.

## What it shows
- Game state kept between events
- Timer (seconds) and ProgressBar (tries used)
- Level menu (Easy / Normal / Hard) and Game menu
- Enter in the guess box
- Best scores per level saved to a text file by a module (`scores.lua`)
- MsgBox when you win or lose

## RAD IDE features
- A **Lua GUI Bridge** project (`lua-bridge`): the IDE draws the forms (designer + `Form*.form`), your Lua code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Lua; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`scores.lua`).
- F5 run, Build > Publish.

## Files
- `Form1.lua` - game logic
- `scores.lua` - best scores file (best_scores.txt)

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Lua 5.4 (lua on PATH, or the LuaBinaries zip extracted into %LOCALAPPDATA%\RADIDE\toolchains\lua).
3. Type a number and press Enter; follow the higher / lower hints.
4. Level > Hard for 1-1000.
5. Set the environment variable RADEX_SECRET=42 to make the secret fixed (used by the test).

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Lua when one is available, otherwise the GUI Bridge host is bundled with the Lua files.

---

<div dir="rtl">

# خمّن الرقم - Lua (مثال من RAD IDE)

لعبة صغيرة: خمّن الرقم السري مع تلميحات ومؤقت وعدد محاولات محدود وحفظ أفضل النتائج.

## ماذا يعرض
- حالة اللعبة محفوظة بين الأحداث
- مؤقت بالثواني وشريط تقدم لعدد المحاولات
- قائمة المستويات (سهل / عادي / صعب) وقائمة اللعبة
- زر Enter في خانة التخمين
- حفظ أفضل نتيجة لكل مستوى في ملف نصي عبر وحدة (`scores.lua`)
- رسالة عند الفوز أو الخسارة

## مزايا بيئة التطوير المستخدمة
- مشروع **Lua GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Lua يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Lua 5.4 (في PATH أو LuaBinaries مستخرجة في %LOCALAPPDATA%\RADIDE\toolchains\lua).
3. اكتب رقمًا واضغط Enter واتبع تلميحات أكبر / أصغر.
4. المستوى > صعب للأرقام 1-1000.
5. المتغير RADEX_SECRET=42 يثبّت الرقم السري (يستخدمه الاختبار).

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
