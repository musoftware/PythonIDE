# Calculator - VB.NET (Windows Forms App, .NET)

A pocket calculator with + - * /, square root, percent, sign, backspace and a memory (MC / MR / M+), usable with the
mouse or the keyboard - as a real Visual Studio-style VB.NET project (`Calculator.vbproj`, `Form1.Designer.vb`,
`Form1.vb`, `Program.vb`) that RAD IDE opens in place.

## What it shows

* File > New Project > .NET > Windows Forms App (Visual Basic): the project was made by the IDE's .NET templates
  (`dotnet new winforms -lang VB`, radide/dotnet/templates)
* the form laid out with RAD IDE's WinForms designer, which writes `Form1.Designer.vb` like Visual Studio does
  (27 controls; opening and saving the form leaves the file unchanged)
* one handler for many buttons: `Handles btn0.Click, btn1.Click, ...` (the button's `Text` says which digit)
* keyboard input with `KeyPreview = True` + `Form1_KeyPress`
* `Decimal` arithmetic and `Try / Catch` for `DivideByZeroException` / `OverflowException` in one place (`Act`)

## Run it

1. File > Open Project... and choose this folder (or Help > Example Projects...). It opens in place as a .NET project.
2. Press F5 (dotnet build + run). Needs the .NET SDK (8 or newer; the template targets the installed SDK).
3. Try: 1 2 + 3 =, then type 7 * 6 Enter, then 1 / 0 =.

## Publish

Project > dotnet CLI > Publish (`dotnet publish -c Release -o publish`) gives `publish\Calculator.exe` (152 KB,
framework-dependent; Project > Publish... can make self-contained / single-file profiles). No Python inside.
The test `samples/Tests/Examples/test_examples_compiled.py` checks the designer round trip, builds, clicks
1 2 + 3 = in the running exe and in the published exe.

## Files

* `Calculator.vbproj` - the SDK-style project
* `Form1.Designer.vb` - written by the form designer
* `Form1.vb` - the event handlers
* `Program.vb` - the entry point (from the template)

---

## الآلة الحاسبة - VB.NET (تطبيق Windows Forms على ‎.NET)

آلة حاسبة جيب (+ - * /، الجذر، النسبة، الإشارة، مسح آخر رقم، والذاكرة) تعمل بالماوس أو بلوحة المفاتيح، كمشروع
VB.NET حقيقي بنفس شكل Visual Studio يفتحه RAD IDE في مكانه.

### ماذا يعرض

* ملف > مشروع جديد > ‎.NET‎ > Windows Forms App (Visual Basic): أنشأه الـ IDE من قوالب ‎.NET‎
* تصميم النموذج بمصمم WinForms في RAD IDE الذي يكتب `Form1.Designer.vb` كما يفعل Visual Studio (27 عنصرًا)
* معالج واحد لأزرار كثيرة: `Handles btn0.Click, btn1.Click, ...`
* إدخال من لوحة المفاتيح عبر `KeyPreview = True` وحدث `KeyPress`
* حساب بنوع `Decimal` ومعالجة الأخطاء بـ `Try / Catch` في مكان واحد

### التشغيل والنشر

افتح المجلد من ملف > فتح مشروع (أو مساعدة > أمثلة المشاريع) واضغط F5 (يحتاج .NET SDK). للنشر: المشروع > dotnet CLI >
Publish ينتج `publish\Calculator.exe` (حوالي 152 ك.ب ويحتاج .NET مثبتًا؛ ويمكن عمل نسخة مستقلة من المشروع > نشر...). بدون بايثون.

(c) 2026 Musoftware - https://musoftwares.com - MIT License
