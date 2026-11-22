<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# VB6 business samples

Eight complete Visual Basic 6 programs written by Musoftware as learning examples and as a test corpus for RAD IDE's
VB6 runtime, designer and native builders. Each folder is a normal VB6 project (`.vbp`, `.frm`, `.bas`, `.cls`,
`.Dsr`) with its own Access database where needed and a README (English + Arabic). Open the `.vbp` with
**File > Open Project** and press **F5**.

| Sample | What it is | Sign in | Main VB6 features |
|---|---|---|---|
| [`BankManager`](BankManager/) | a small bank (MDI, ADO, class module) | `admin` / `admin` (may open the balances report) or `teller` / `teller` | MDI, splash, ADO, class module, MSFlexGrid, ListView, DTPicker, DataReport, text export |
| [`ElectricityBilling`](ElectricityBilling/) | meter readings and slab tariffs | `admin` / `admin` (or `reader` / `reader`) | slab tariff maths, UDT, ItemData, MaskEdBox, parameterised DataEnvironment + DataReport |
| [`FinanceLedger`](FinanceLedger/) | a savings & loan society on one SSTab | `admin` / `admin` | SSTab (6 tabs), UpdateBatch, With blocks, modal dialog, Timer with changing Interval |
| [`ScientificCalculator`](ScientificCalculator/) | control arrays and maths | no login | control arrays, KeyPreview, error trapping, recursion, Clipboard, files |
| [`ClinicManager`](ClinicManager/) | patients and visits with DAO and the Data control | staff PIN `1234` (asked with an InputBox) | DAO + Data control, bound controls, Reposition, FindFirst, Shape bar chart |
| [`LogicGateLab`](LogicGateLab/) | a logic gate workbench drawn with Shape and Line controls | no login | Shape / Line drawing at run time, class + Enum, Timers, CommonDialog, Write # / Input # |
| [`PharmacyStore`](PharmacyStore/) | stock, purchases and invoices | `admin` / `admin` | runtime CREATE TABLE, ADO recordset editing, state buttons, ListView invoice, DataReport |
| [`OnlineExam`](OnlineExam/) | question bank, papers, timed exams and results | student `student1` / `student1` (or `student2`), examiner `admin` / `admin` | DAO, nested menus, UDT arrays, ReDim Preserve, countdown Timer, ListViews, DataReport |

Databases: `_tools/make_mdb.py` rebuilds every `.mdb` from the `.sql` script next to it (Jet 4.0 through the 32-bit
Windows Script Host). RAD IDE runs them with its 32-bit ADO helper (`radide/runtimes/vbado.py`).

Tests: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py` opens every form in the designer
(VB6 importer) and drives each program as a user would (sign in, add records, read the grids, run the
calculations, open the reports) on a temporary copy.

Known limits of RAD IDE's VB6 runtime that these samples avoid (also listed in samples/Tests/README.md): the graphics methods
`Line` / `Circle` / `PSet` / `Print` on forms and PictureBoxes, the `Printer` object, `PopupMenu`, menus hidden
with `Visible = False`, `Load` of new control-array elements at run time, OptionButton groups per Frame (one
group per form), `SaveSetting` / `GetSetting`.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. All names and data in the samples are fictional.

<div dir="rtl">

## بالعربية

ثمانية برامج كاملة بلغة Visual Basic 6 كتبتها Musoftware كأمثلة تعليمية وكمجموعة اختبار لمشغّل VB6 ومصمم النماذج في RAD IDE:
إدارة بنك، فواتير كهرباء، دفاتر جمعية ادخار وإقراض، آلة حاسبة علمية، إدارة عيادة، معمل البوابات المنطقية، صيدلية، ونظام امتحانات.
افتح ملف `.vbp` من **File > Open Project** ثم اضغط **F5**. لكل مثال ملف README بالإنجليزية والعربية يشرح الشاشات وطريقة الدخول التجريبي
وما يوضحه من خصائص VB6. كل الأسماء والبيانات وهمية.

</div>
