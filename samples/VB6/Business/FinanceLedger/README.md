<!-- (c) 2026 Musoftware - https://musoftwares.com - MIT License -->

# FinanceLedger - a savings & loan society on one SSTab

The books of a small savings and loan society: members, vouchers (savings deposits / withdrawals, share
capital, income, expenses; cash or cheque), loans with a savings rule and repayments, tiered interest on
savings, a day book in debit / credit columns and a profit & loss summary.

**Demo sign-in:** `admin` / `admin`.

## Forms and what each one shows

| File | What it demonstrates |
|---|---|
| `frmStart` | splash + sign-in on one form; the Timer changes its own `Interval` while it fills the ProgressBar |
| `frmLedger` | one SSTab with six tabs: Members (ListBox + details), Vouchers (Frame, OptionButton array, KeyPress filter), Loans (MSFlexGrid, InputBox repayment), Interest (DateDiff, tiered rate), Day book (debit / credit grid, totals), Profit && loss (recalculated in `tabMain_Click(PreviousTab)`, a Shape that turns green or red) |
| `frmMember` | modal dialog: the account type option decides the id prefix (S- / C-) and the entry fee |

## VB6 features covered

SSTab with controls on hidden tabs, ADO with `adLockBatchOptimistic` + `UpdateBatch`, `With rs ... !Field` blocks, `CursorLocation = adUseClient`, `Format("\#yyyy-mm-dd\#")`, `IIf` in Jet SQL, `Choose`, ListBox / ComboBox parsing, MSFlexGrid `AddItem`, Shape colours, modal dialogs (`Show vbModal, Me`), public procedures of a form called from another form, local variables named like built-ins (`dir`).

## Database

Tables: Users, Members (MemberID S-0001 / C-0001, AccType, Joined, EntryFee, Active), Ledger (EntryDate, MemberID, Category, Direction CR/DR, Amount, PayMode, Narration), Loans, Cash (one row: CashInHand, BankBalance), Rates (MinDays, RatePct).


## Run it

* In RAD IDE: **File > Open Project** > `FinanceLedger.vbp`, then **F5**. The project opens in place: the VB6 files stay
  the real source and are edited in VB6 format.
* From a shell: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\FinanceLedger\FinanceLedger.vbp`
* In Visual Basic 6: open `FinanceLedger.vbp`. It uses only standard VB6 references and controls.

The Access database `finance.mdb` (Jet 4.0) is built from `finance.sql` with
`python samples\VB6\Business\_tools\make_mdb.py FinanceLedger` (ADOX through the 32-bit Windows Script Host).
RAD IDE reaches Jet through its 32-bit ADO helper (radide/runtimes/vbado.py), so the program runs from the
64-bit IDE unchanged.

Test: `.venv\Scripts\python samples\Tests\VB6Business\test_vb6_business.py FinanceLedger` drives these workflows
on a copy of the folder.

(c) 2026 Musoftware - https://musoftwares.com - MIT License. Every name, number and record in the data is fictional.

<div dir="rtl">

## بالعربية

دفاتر جمعية ادخار وإقراض صغيرة: الأعضاء، السندات (إيداع وسحب ادخار، أسهم، إيرادات، مصروفات؛ نقدًا أو بشيك)، القروض وسدادها، فوائد الادخار المتدرجة، دفتر اليومية مدين/دائن وملخص الأرباح والخسائر.

الدخول التجريبي: `admin` / `admin`.

يوضح: أداة SSTab بست صفحات، مؤقت يغيّر Interval الخاص به، ADO مع UpdateBatch وكتل With، نوافذ حوار مشروطة (vbModal)، MSFlexGrid، ألوان الأشكال Shape، والاستدعاء بين النماذج.


### طريقة التشغيل

* من RAD IDE: ‏**File > Open Project** ثم اختر `FinanceLedger.vbp` واضغط **F5**.
* من سطر الأوامر: `.venv\Scripts\python -m radide.runtimes.vbrun samples\VB6\Business\FinanceLedger\FinanceLedger.vbp`
* يفتح أيضًا في Visual Basic 6 نفسه.

حقوق النشر (c) 2026 Musoftware - ‏https://musoftwares.com - رخصة MIT. كل الأسماء والبيانات وهمية للتجربة فقط.

</div>
