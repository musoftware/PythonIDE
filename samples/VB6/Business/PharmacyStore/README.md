<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# PharmacyStore - stock, purchases and invoices

A pharmacy shop: the medicine list edited record by record, purchases that add stock, invoices that check
and lower the stock with a discount, low-stock and expiry alerts, a CSV export and an invoice report. Every
stock movement is logged in a table the program creates itself on the first run. Products are fictional.

**Demo sign-in:** `admin` / `admin`.

## Forms and what each one shows

| File | What it demonstrates |
|---|---|
| `modStore` | `Sub Main`, `EnsureSchema` (runtime `CREATE TABLE` with `On Error Resume Next`), `ChangeStock` + log, public variables passed between forms, `While ... Wend` |
| `frmSplash` | borderless splash, Timer + ProgressBar, a green cross made of two Shapes; `Unload Me` then `frmLogin.Show` |
| `frmLogin` | Users table, `RecordCount` of a static recordset |
| `mdiStore` | MDI parent, a bottom-aligned PictureBox status bar, a second-level menu (Reports > More), `MDIForm_QueryUnload` |
| `frmMedicines` | updatable ADO Recordset: |< < > >| button array (`MoveFirst` ...), `AbsolutePosition / RecordCount`, `AddNew` / `rs!Field =` / `Update` / `Delete`, Add/Save and Edit/Update buttons driven by their `Caption`, `For Each` + `TypeOf` to lock the TextBoxes, expiry warning with `DateDiff`, `Form_Unload` with `Cancel` |
| `frmPurchase` | transaction (`BeginTrans` / `CommitTrans`), `SELECT TOP 10`, MSFlexGrid |
| `frmSale` | invoice lines in a ListView (`ListItems.Add`, `SubItems`, `Remove`, `For Each li In lvw.ListItems`), stock check, discount recalculated in `Change`, print through DataEnvironment + DataReport |
| `frmAlerts` | MSFlexGrid of problems, CSV export, "Sell selected" hands the medicine to frmSale through public variables |

## VB6 features covered

Runtime DDL, ADO recordset editing and navigation, state buttons, MDI with a PictureBox status bar, nested menus, ListView, MSFlexGrid, DTPicker, transactions, DataEnvironment with a three-table JOIN and a parameter, DataReport, CSV export.

## Database

Tables: Users, Medicines (Code, MedName, Category, UnitPrice, Stock, ReorderLevel, Expiry, Supplier), Purchases, Sales (InvoiceNo, SaleDate, Customer, DiscountPct, Total), SaleItems, StockLog (created at run time).


## Run it

* In RAD IDE: **File > Open Project** > `PharmacyStore.vbp`, then **F5**. The project opens in place: the VB6 files stay
  the real source and are edited in VB6 format.
* From a shell: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\PharmacyStore\PharmacyStore.vbp`
* In Visual Basic 6: open `PharmacyStore.vbp`. The DataEnvironment / DataReport `.Dsr` files are hand-written text (no .dsx/.dca companions), so VB6 may offer to rebuild them.

The Access database `pharmacy.mdb` (Jet 4.0) is built from `pharmacy.sql` with
`python samples\VB6\Business\_tools\make_mdb.py PharmacyStore` (ADOX through the 32-bit Windows Script Host).
RAD IDE reaches Jet through its 32-bit ADO helper (radide/runtimes/vbado.py), so the program runs from the
64-bit IDE unchanged.

Test: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py PharmacyStore` drives these workflows
on a copy of the folder.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. Every name, number and record in the data is fictional.

<div dir="rtl">

## بالعربية

صيدلية: قائمة الأدوية وتعديلها سجلًا سجلًا، المشتريات التي تزيد المخزون، الفواتير التي تتحقق من المخزون وتنقصه مع خصم، تنبيهات نقص المخزون وقرب انتهاء الصلاحية، تصدير CSV وتقرير الفاتورة. كل حركة مخزون تُسجل في جدول ينشئه البرنامج بنفسه أول مرة.

الدخول التجريبي: `admin` / `admin`.

يوضح: إنشاء جدول أثناء التشغيل (DDL)، التنقل والتعديل بسجلات ADO، أزرار تتغير حالتها، MDI بشريط حالة من PictureBox، قوائم متداخلة، ListView وMSFlexGrid، المعاملات، DataEnvironment بمعامل وDataReport.


### طريقة التشغيل

* من RAD IDE: ‏**File > Open Project** ثم اختر `PharmacyStore.vbp` واضغط **F5**.
* من سطر الأوامر: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\PharmacyStore\PharmacyStore.vbp`
* يفتح أيضًا في Visual Basic 6 نفسه.

حقوق النشر (c) 2026 Musoftware - ‏https://musoftwares.com - رخصة MIT. كل الأسماء والبيانات وهمية للتجربة فقط.

</div>
