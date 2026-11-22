<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# ScientificCalculator - control arrays and maths

A scientific calculator: + - * / Mod and powers with chaining, sin / cos / tan in degrees or radians, log,
ln, square root, x^2, x^3, 1/x, n!, %, pi, memory keys, backspace / CE / C, keyboard input, a history list
that can be saved and loaded, clipboard copy / paste and a clock.

**Demo sign-in:** no login.

## Forms and what each one shows

| File | What it demonstrates |
|---|---|
| `frmCalc` | everything on one form: `cmdDigit(0-9)`, `cmdOp(0-5)`, `cmdFunc(0-11)`, `cmdMem(0-3)` and `optAngle(0-1)` control arrays with one `_Click(Index)` handler each, graphical (coloured) buttons, `KeyPreview` + `Form_KeyPress`, private `Property Get / Let Display`, a private Enum, `On Error GoTo` with friendly messages for error 11 (division by zero), 5 and 6, a history ListBox (`DblClick` recalls a result), Timer clock, Shape bezel, File / Edit / Help menus |
| `modMath` | `Const PI`, `Log10`, recursive `Factorial` that raises error 5, result formatting with scientific notation |

## VB6 features covered

Control arrays, `Choose`, `Select Case`, `Err.Raise`, `On Error GoTo`, recursion, `Format$` patterns, `InStrRev`, `Clipboard.SetText / GetText`, `Dir$`, `Line Input #`, `EOF()`, `Print #`, `Beep`, KeyPreview.


## Run it

* In RAD IDE: **File > Open Project** > `ScientificCalculator.vbp`, then **F5**. The project opens in place: the VB6 files stay
  the real source and are edited in VB6 format.
* From a shell: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\ScientificCalculator\ScientificCalculator.vbp`
* In Visual Basic 6: open `ScientificCalculator.vbp`. It references the controls it uses (MSCOMCTL, MSFLXGRD, ...) like any VB6 project.

Test: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py ScientificCalculator` drives these workflows
on a copy of the folder.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. Every name, number and record in the data is fictional.

<div dir="rtl">

## بالعربية

آلة حاسبة علمية: العمليات الأساسية والأسس وباقي القسمة، الدوال المثلثية بالدرجات أو الراديان، اللوغاريتمات والجذر والمضروب والنسبة المئوية وπ، مفاتيح الذاكرة، الإدخال من لوحة المفاتيح، سجل العمليات مع الحفظ والتحميل، والنسخ واللصق.

لا يحتاج تسجيل دخول.

يوضح: مصفوفات الأدوات بمعالج Click(Index) واحد، KeyPreview وForm_KeyPress، خصائص Property Get/Let داخل النموذج، معالجة الأخطاء On Error وErr.Raise، الدوال التكرارية، الملفات النصية والحافظة Clipboard.


### طريقة التشغيل

* من RAD IDE: ‏**File > Open Project** ثم اختر `ScientificCalculator.vbp` واضغط **F5**.
* من سطر الأوامر: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\ScientificCalculator\ScientificCalculator.vbp`
* يفتح أيضًا في Visual Basic 6 نفسه.

حقوق النشر (c) 2026 Musoftware - ‏https://musoftwares.com - رخصة MIT. كل الأسماء والبيانات وهمية للتجربة فقط.

</div>
