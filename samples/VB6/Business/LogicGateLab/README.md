<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# LogicGateLab - a logic gate workbench drawn with Shape and Line controls

A digital logic trainer: switch inputs A and B, choose AND / OR / NOT / NAND / NOR / XOR / XNOR and watch the
wires and lamps light up; a clock can drive input A, a dot runs along the output wire while it is 1, a
two-gate circuit ((A gate1 B) gate2 C) shows its boolean expression, truth tables open in a tool window and
can be exported, and the setup is saved to / opened from a file.

**Demo sign-in:** no login.

## Forms and what each one shows

| File | What it demonstrates |
|---|---|
| `frmLab` | Shape lamps and Line wires whose colours follow the signals (`BackColor`, `BorderColor`, `FillColor`), graphical CheckBoxes, an OptionButton array, two Timers (clock and the moving dot: `Shape.Left`, `Line.X1 / X2`), an HScrollBar for the speed, two `clsGate` objects in an array, CommonDialog `ShowSave` / `ShowOpen` with `CancelError` / `cdlCancel`, `Write #` / `Input #`, a public `Property Get` read by another form |
| `frmTruth` | modeless tool window (`BorderStyle = 4`) with an MSFlexGrid truth table, the expression and the number of 1 rows; export of all seven tables with `Print #` and `Tab()` |
| `clsGate` | class module: `Public Enum GateKind`, `Property Get / Let` with validation, `Choose`, a counter property |
| `modLogic` | shared colours and `FillTruthTable` (nested `For` with `Exit For`) |

## VB6 features covered

Shape and Line controls changed at run time, control arrays, Timers, HScrollBar `Change`, class modules with Enums, object arrays (`mCircuit(1) As clsGate`), CommonDialog, `Write #` / `Input #`, modeless forms, `Array()` / `LBound` / `UBound`, boolean operators (`And`, `Or`, `Xor`, `Not`).


## Run it

* In RAD IDE: **File > Open Project** > `LogicGateLab.vbp`, then **F5**. The project opens in place: the VB6 files stay
  the real source and are edited in VB6 format.
* From a shell: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\LogicGateLab\LogicGateLab.vbp`
* In Visual Basic 6: open `LogicGateLab.vbp`. It references the controls it uses (MSCOMCTL, MSFLXGRD, ...) like any VB6 project.

Test: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py LogicGateLab` drives these workflows
on a copy of the folder.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. Every name, number and record in the data is fictional.

<div dir="rtl">

## بالعربية

معمل البوابات المنطقية: بدّل المدخلين A وB واختر البوابة (AND وOR وNOT وNAND وNOR وXOR وXNOR) لترى الأسلاك والمصابيح تضيء؛ ساعة تقود المدخل A، ونقطة تتحرك على سلك الخرج، ودائرة من بوابتين تعرض تعبيرها المنطقي، وجداول الصواب تُعرض وتُصدَّر، ويُحفظ الإعداد في ملف.

لا يحتاج تسجيل دخول.

يوضح: أدوات Shape وLine تتغير ألوانها ومواضعها أثناء التشغيل، مصفوفات الأدوات، المؤقتات، شريط التمرير، وحدة صنف بتعداد Enum وخصائص، مصفوفة كائنات، CommonDialog للحفظ والفتح، الملفات بـ Write # وInput #، ونافذة أدوات غير مشروطة.


### طريقة التشغيل

* من RAD IDE: ‏**File > Open Project** ثم اختر `LogicGateLab.vbp` واضغط **F5**.
* من سطر الأوامر: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\LogicGateLab\LogicGateLab.vbp`
* يفتح أيضًا في Visual Basic 6 نفسه.

حقوق النشر (c) 2026 Musoftware - ‏https://musoftwares.com - رخصة MIT. كل الأسماء والبيانات وهمية للتجربة فقط.

</div>
