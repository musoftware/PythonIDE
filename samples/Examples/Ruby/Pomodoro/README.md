# Pomodoro Timer - Ruby (RAD IDE example)

A work/break timer with a progress bar, a modal settings dialog, saved settings and an English or Arabic interface.

## What it shows
- Timer (1 s) counting down, ProgressBar, work and break phases
- A modal settings dialog (SettingsForm, `CALL ShowDialog`) with NumericUpDown, ComboBox, CheckBox
- Settings saved to settings.json (`PomodoroSettings.rb`)
- UI language switch: all captions change to Arabic
- Menus, MsgBox at the end of a phase, ListBox of completed sessions

## RAD IDE features
- A **Ruby GUI Bridge** project (`ruby-bridge`): the IDE draws the forms (designer + `Form*.form`), your Ruby code handles the events.
- Designer: menus (MenuStrip editor), ToolBox controls, non-visual components (Timer / dialogs) in the component tray.
- Code editor with IntelliSense for Ruby; handlers named `<Control>_<Event>` (double-click a control to add one).
- Modules: Project > Add Module (`PomodoroSettings.rb`).
- F5 run, Build > Publish.

## Files
- `Form1.rb` - timer
- `SettingsForm.rb` - the settings dialog
- `PomodoroSettings.rb` - settings file and the two languages

## How to run
1. File > Open Project... and choose this folder (`project.radproj`).
2. Press **F5**. Needs Ruby 3.x (RubyInstaller, or the IDE's toolchains\ruby).
3. Press **Start**.
4. Tools > Settings...: set 1 minute and choose العربية, OK.
5. Wait a minute: the session is listed and the break starts.

## Publish
Build > Publish makes a Windows program folder (and optionally an installer). The IDE uses a native
builder for Ruby when one is available, otherwise the GUI Bridge host is bundled with the Ruby files.

---

<div dir="rtl">

# مؤقت بومودورو - Ruby (مثال من RAD IDE)

مؤقت للعمل والاستراحة مع شريط تقدم ونافذة إعدادات مشروطة وحفظ الإعدادات وواجهة إنجليزية أو عربية.

## ماذا يعرض
- مؤقت بالثواني وشريط تقدم ومرحلتا العمل والاستراحة
- نافذة إعدادات مشروطة فيها NumericUpDown وComboBox وCheckBox
- حفظ الإعدادات في settings.json (`PomodoroSettings.rb`)
- تبديل لغة الواجهة إلى العربية
- قوائم ورسالة عند نهاية المرحلة وقائمة الجلسات المكتملة

## مزايا بيئة التطوير المستخدمة
- مشروع **Ruby GUI Bridge**: البيئة ترسم النماذج في المصمم، وكود Ruby يعالج الأحداث.
- المصمم: القوائم وأدوات صندوق الأدوات والمكونات غير المرئية (المؤقت ومربعات الحوار).
- محرر الكود مع الإكمال التلقائي، والمعالجات بالاسم `<Control>_<Event>`.
- التشغيل بـ F5 والنشر من Build > Publish.

## طريقة التشغيل
1. من File > Open Project اختر هذا المجلد.
2. اضغط **F5**. يحتاج Ruby 3.x (RubyInstaller أو toolchains\ruby الخاص بالبيئة).
3. اضغط **Start**.
4. أدوات > الإعدادات: اختر دقيقة واحدة واللغة العربية ثم OK.
5. انتظر دقيقة لتُسجّل الجلسة وتبدأ الاستراحة.

## النشر
Build > Publish يُنشئ مجلد برنامج لويندوز (ومثبّتًا اختياريًا).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
