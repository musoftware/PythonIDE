<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# BankManager - a small bank (MDI, ADO, class module)

A bank counter program: customer accounts, deposits and withdrawals with a minimum-balance rule, account
statements between two dates, an export of the statement to a text file and a customer balances report.

**Demo sign-in:** `admin` / `admin` (may open the balances report) or `teller` / `teller`.

## Forms and what each one shows

| File | What it demonstrates |
|---|---|
| `frmSplash` | start-up screen: a Timer fills a ProgressBar, then opens the login |
| `frmLogin` | Users table, three wrong tries end the program (`End`) |
| `mdiMain` | MDI parent: menus with shortcuts, Window list, a StatusBar, role-based menu (`Enabled`) |
| `frmCustomers` | MDI child: MSFlexGrid list + details Frame, New / Save (INSERT or UPDATE) / Delete (asks first, removes the transactions too) / Find (InputBox), KeyPress filters, DTPicker |
| `frmTransaction` | Deposit / Withdraw with an OptionButton control array, the rules in `clsAccount` (Property Get, Enum, `Err.Raise vbObjectError + n`, BeginTrans / CommitTrans) |
| `frmStatement` | ListView (report view) of the transactions between two DTPickers, totals, export with `Open ... For Output` / `Print #` / `Tab()` |
| `frmAbout` | a modal dialog (`Show vbModal`) with `App.Major/Minor/Revision` |
| `deBank + rptBalances` | DataEnvironment command and DataReport |

## VB6 features covered

Sub Main start-up, MDIForm + MDIChild forms, splash with Timer + ProgressBar, menus, MSFlexGrid (`TextMatrix`, `Rows`, `ColWidth`), ListView (`ListItems.Add`, `SubItems`), DTPicker, OptionButton control array, CheckBox, Frame, Shape, StatusBar, class module, ADO Connection / Recordset / Execute, transactions, `For Each ctl In frm.Controls` + `TypeOf`, `For Each f In Forms`, public methods of another form (`frmCustomers.LoadGrid`), sequential files (`Append`, `Output`), `Shell`, MsgBox / InputBox, validation.

## Database

Tables: Users, Customers (AccountNo, FullName, Phone, Address, AccType, Opened, Balance), Transactions, Settings (BankName, MinBalance).


## Run it

* In RAD IDE: **File > Open Project** > `BankManager.vbp`, then **F5**. The project opens in place: the VB6 files stay
  the real source and are edited in VB6 format.
* From a shell: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\BankManager\BankManager.vbp`
* In Visual Basic 6: open `BankManager.vbp`. The DataEnvironment / DataReport `.Dsr` files are hand-written text (no .dsx/.dca companions), so VB6 may offer to rebuild them.

The Access database `bank.mdb` (Jet 4.0) is built from `bank.sql` with
`python samples\VB6\Business\_tools\make_mdb.py BankManager` (ADOX through the 32-bit Windows Script Host).
RAD IDE reaches Jet through its 32-bit ADO helper (radide/runtimes/vbado.py), so the program runs from the
64-bit IDE unchanged.

Test: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py BankManager` drives these workflows
on a copy of the folder.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. Every name, number and record in the data is fictional.

<div dir="rtl">

## بالعربية

برنامج لإدارة بنك صغير: حسابات العملاء، الإيداع والسحب مع حد أدنى للرصيد، كشف حساب بين تاريخين وتصديره لملف نصي، وتقرير بأرصدة العملاء.

الدخول التجريبي: `admin` / `admin` (يفتح تقرير الأرصدة) أو `teller` / `teller`.

يوضح: البدء من Sub Main، نافذة MDI ونوافذ أبناء، شاشة بداية بمؤقت وشريط تقدم، القوائم، MSFlexGrid وListView وDTPicker، مصفوفة أزرار اختيار، وحدة صنف (Class) بقواعد العمل ورفع الأخطاء، ADO مع المعاملات، الملفات النصية، MsgBox وInputBox والتحقق من المدخلات.


### طريقة التشغيل

* من RAD IDE: ‏**File > Open Project** ثم اختر `BankManager.vbp` واضغط **F5**.
* من سطر الأوامر: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\BankManager\BankManager.vbp`
* يفتح أيضًا في Visual Basic 6 نفسه.

حقوق النشر (c) 2026 Musoftware - ‏https://musoftwares.com - رخصة MIT. كل الأسماء والبيانات وهمية للتجربة فقط.

</div>
