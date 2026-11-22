<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# Todo app (Flutter designer)

Two screens made in the Flutter visual designer: task list + Settings with Arabic RTL.

## What it shows

- New Project > Flutter App (visual designer): `screens/Todo.fscreen.json`, `screens/Settings.fscreen.json`
- Designer widgets: AppBar actions, TextField (named -> controller), ElevatedButton, ListView.builder with a Code item template, SwitchListTile (named -> bool field), FilledButton
- Dart values in the designer (`store.t('Add', 'إضافة')`, `store.summary()`) + Screen Imports
- Event handlers in `lib/screens/*_events.dart`, navigation with `Navigator.pushNamed`
- Arabic / right-to-left: `Directionality` around the designed screen (override of `build`)
- `test/widget_test.dart`: flutter test adds a task, ticks it and switches to Arabic

**Language / project type:** `flutter`

## Run

F5 runs the app (Chrome / Windows device from the Mobile toolbar). `flutter test` runs the widget test.

## Publish

Build > Publish runs `flutter build windows --release` (adds the Windows runner when missing).

<div dir="rtl">

# تطبيق المهام (مصمم Flutter)

شاشتان بمصمم Flutter المرئي: قائمة مهام وإعدادات مع العربية من اليمين لليسار.

## ماذا يوضح

- مشروع Flutter بالمصمم المرئي بشاشتين
- عناصر المصمم: شريط علوي وحقل نص وأزرار وقائمة ومفاتيح تبديل
- قيم Dart داخل المصمم وملف بيانات مشترك
- الأحداث في ملفات events والتنقل بين الشاشات
- العربية من اليمين لليسار
- اختبار واجهة تلقائي بـ flutter test

## التشغيل

اضغط F5 لتشغيل التطبيق، و flutter test لتشغيل الاختبار.

## النشر

من القائمة Build > Publish لإنشاء ملف تنفيذي (انظر جدول النتائج).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License. Tested by `samples/Tests/Examples/test_examples_scripting.py --group ring`.
