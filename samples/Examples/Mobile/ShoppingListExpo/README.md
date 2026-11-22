# ShoppingListExpo - Shopping List (React Native / Expo)

**Language / project type:** `expo` (created with File > New Project, then customised)

Two-screen Expo app from the phone designer: list with icons, item editor with slider, shared store module.

## What it shows
- MainScreen / ItemScreen designed in the phone designer (JSX generated)
- MTextField, MListView (icon|title|subtitle), Switch, MSlider, Timer
- ShowForm(name, args), FormArgs, CloseForm, Toast, MsgBox, await Confirm
- store.js module shared by the screens

## Run
Needs Node.js. Open the folder, F5: the IDE runs npm install (first time, a few minutes) and expo start --web.

## Publish
`npx expo export --platform web` makes a static web build (tested); phone builds use EAS.

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py Mobile/ShoppingListExpo` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# قائمة التسوق (React Native / Expo)

تطبيق Expo من شاشتين مصمم في مصمم الهاتف: قائمة بأيقونات وشاشة تعديل وشريط تمرير ووحدة بيانات مشتركة.

## ماذا يوضح
- شاشتان مصممتان في مصمم الهاتف
- حقل نص وقائمة بأيقونات ومفتاح وشريط تمرير ومؤقت
- التنقل بين الشاشات والحوارات
- وحدة store.js مشتركة

## التشغيل
يحتاج Node.js. افتح المجلد واضغط F5: تثبيت الحزم أول مرة ثم تشغيل expo على الويب.

## النشر
`npx expo export --platform web` makes a static web build (tested); phone builds use EAS.

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
