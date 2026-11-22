# CapitalsQuiz - Capitals Quiz (Kivy)

**Language / project type:** `kivy` (created with File > New Project, then customised)

Two-screen mobile quiz designed in the phone designer: buttons, progress bar, timer, result list.

## What it shows
- Kivy forms designed in RAD IDE's phone designer (MainScreen, ResultScreen)
- Button / Switch / ProgressBar / Timer / MListView / AppBar
- ShowForm(name, args), FormArgs, CloseForm + Form_Closed, Toast, MsgBox
- A code module (questions.py); buildozer.spec for Android

## Run
Open the folder, F5 (the window has the phone size). Switch on Hard mode for 10 seconds per question.

## Publish
Build > Publish: PyInstaller folder (~93 MB, Python inside); Android: buildozer (not tested here).

## Test
`.venv\Scripts\python samples\Tests\Examples\test_examples_scripting.py PythonGames/CapitalsQuiz` (group `pyweb`, see
`samples/Tests/Examples/ex_pyweb.py`).

---

<div dir="rtl">

# مسابقة العواصم (Kivy)

مسابقة للموبايل من شاشتين مصممة في مصمم الهاتف: أزرار وشريط تقدم ومؤقت وقائمة نتائج.

## ماذا يوضح
- شاشات Kivy مصممة في مصمم الهاتف
- أزرار ومفتاح وشريط تقدم ومؤقت وقائمة
- التنقل بين الشاشات مع تمرير البيانات
- وحدة كود منفصلة وملف buildozer لأندرويد

## التشغيل
افتح المجلد واضغط F5. فعّل الوضع الصعب لعشر ثوانٍ لكل سؤال.

## النشر
Build > Publish: PyInstaller folder (~93 MB, Python inside); Android: buildozer (not tested here).

</div>

---
(c) 2026 Musoftware - https://musoftwares.com - MIT License
