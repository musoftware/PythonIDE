<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# ElectricityBilling - meter readings and slab tariffs

An electricity company office: consumers and their meters, monthly meter readings, bills calculated with
slab tariffs (each block of units has its own rate), a fixed charge and a tax, printing a bill and an
unpaid-bills report. Example: 350 domestic units = 100 x 0.50 + 200 x 0.85 + 50 x 1.25 = 282.50, + 15 fixed,
+ 5% tax = 312.38.

**Demo sign-in:** `admin` / `admin` (or `reader` / `reader`).

## Forms and what each one shows

| File | What it demonstrates |
|---|---|
| `frmLogin` | startup form, opens the database in Form_Load, Shape logo |
| `frmMain` | menus with F5 / F6 shortcuts, a top-aligned PictureBox "toolbar" with a CommandButton array, a Label array summary, a Timer clock, `Write #` file export |
| `frmConsumers` | ListBox with `ItemData` = meter number, MaskEdBox phone, DTPicker, CheckBox, INSERT / UPDATE, duplicate check, `Like` key filter |
| `frmReading` | ComboBox + ItemData, previous reading lookup, MSFlexGrid history with `AddItem` and tabs, validation (new reading >= previous), `Beep` |
| `frmBill` | the slab calculation returns a user-defined `Type`, JOIN queries, `DateAdd`, `RecordsAffected`, InputBox "mark paid", print through a parameterised DataEnvironment command + DataReport |

## VB6 features covered

Startup form, menus with function-key shortcuts, ADO with SQL strings, `Public Type` (UDT) as a function result, ListBox / ComboBox `ItemData` + `NewIndex`, MaskEdBox, DTPicker, MSFlexGrid, control arrays (CommandButton, Label), PictureBox as a container, Timer, DataEnvironment with a parameter (`deBilling.cmdBill n`), DataReport, `Write #`, `Shell`, the VB6 rule that `And` does not short-circuit (see `EnergyCharge`).

## Database

Tables: Users, Tariffs (Category, FromUnit, ToUnit, Rate), Consumers (MeterNo, ...), Readings (PrevReading, CurrReading, Billed), Bills (Units, Energy, FixedCharge, Tax, Total, DueDate, Paid), Settings.


## Run it

* In RAD IDE: **File > Open Project** > `ElectricityBilling.vbp`, then **F5**. The project opens in place: the VB6 files stay
  the real source and are edited in VB6 format.
* From a shell: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\ElectricityBilling\ElectricityBilling.vbp`
* In Visual Basic 6: open `ElectricityBilling.vbp`. The DataEnvironment / DataReport `.Dsr` files are hand-written text (no .dsx/.dca companions), so VB6 may offer to rebuild them.

The Access database `billing.mdb` (Jet 4.0) is built from `billing.sql` with
`python samples\VB6\Business\_tools\make_mdb.py ElectricityBilling` (ADOX through the 32-bit Windows Script Host).
RAD IDE reaches Jet through its 32-bit ADO helper (radide/runtimes/vbado.py), so the program runs from the
64-bit IDE unchanged.

Test: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py ElectricityBilling` drives these workflows
on a copy of the folder.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. Every name, number and record in the data is fictional.

<div dir="rtl">

## بالعربية

برنامج فواتير كهرباء: المشتركون وعداداتهم، قراءات العدادات الشهرية، حساب الفاتورة بالشرائح (لكل شريحة سعر) مع رسم ثابت وضريبة، طباعة الفاتورة وتقرير الفواتير غير المدفوعة.

الدخول التجريبي: `admin` / `admin`.

يوضح: نموذج بدء، قوائم باختصارات لوحة المفاتيح، ADO، نوع معرف من المستخدم (Type) كنتيجة دالة، ItemData في القوائم، MaskEdBox وDTPicker وMSFlexGrid، مصفوفات أدوات، مؤقت، DataEnvironment بمعامل وDataReport، والكتابة بـ Write #.


### طريقة التشغيل

* من RAD IDE: ‏**File > Open Project** ثم اختر `ElectricityBilling.vbp` واضغط **F5**.
* من سطر الأوامر: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\ElectricityBilling\ElectricityBilling.vbp`
* يفتح أيضًا في Visual Basic 6 نفسه.

حقوق النشر (c) 2026 Musoftware - ‏https://musoftwares.com - رخصة MIT. كل الأسماء والبيانات وهمية للتجربة فقط.

</div>
