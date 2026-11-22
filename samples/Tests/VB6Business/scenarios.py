# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Scripted user sessions for samples/VB6/Business - one function per sample, called by
test_vb6_business.py in a child process with a Driver (d) and check(cond, message)."""
from __future__ import annotations


def _num(s) -> float:
    try:
        return float(str(s).replace(",", ""))
    except ValueError:
        return float("nan")


# ---------------------------------------------------------------------------------------------- BankManager
def BankManager(d, check):
    d.start()
    check(d.loaded("frmSplash"), "BankManager: Sub Main opens the splash")
    check(d.wait_for(lambda: d.loaded("frmLogin"), 10000), "BankManager: the splash timer opens the login form")
    check(not d.loaded("frmSplash"), "BankManager: the splash unloaded itself")
    # wrong password, then the demo admin
    d.set("frmLogin", "txtUser", "admin")
    d.set("frmLogin", "txtPassword", "nope")
    d.click("frmLogin", "cmdOK")
    check(any("tries left" in m for m in d.msgs), "BankManager: a wrong password is refused")
    d.set("frmLogin", "txtPassword", "admin")
    d.click("frmLogin", "cmdOK")
    check(d.loaded("mdiMain") and not d.loaded("frmLogin"), "BankManager: admin/admin signs in, MDI parent shown")
    check("admin" in str(d.get("mdiMain", "sbMain", "simpletext")), "BankManager: status bar names the user")
    check(d.get("mdiMain", "mnuRptBalances", "enabled") is True, "BankManager: admin may open the report")
    # customers: the grid lists the 3 demo accounts
    d.click("mdiMain", "mnuCustAccounts")
    g = d.grid("frmCustomers", "grdCustomers")
    check(len(g) == 4 and g[0][1] == "Name" and g[1][0] == "1001", f"BankManager: grid shows 3 accounts ({len(g) - 1})")
    check(d.get("frmCustomers", "txtName") == g[1][1], "BankManager: first account shown in the details")
    # validation: KeyPress filters
    check(d.keypress("frmCustomers", "txtBalance", "x") == 0 and d.keypress("frmCustomers", "txtBalance", "7") == 55,
          "BankManager: balance box accepts digits only (KeyPress)")
    # new account
    d.click("frmCustomers", "cmdNew")
    check(d.get("frmCustomers", "txtAccNo") == "1004", "BankManager: New proposes account 1004")
    d.set("frmCustomers", "txtName", "Yo")
    d.click("frmCustomers", "cmdSave")
    check(any("at least 3" in m for m in d.msgs), "BankManager: too short name refused")
    d.set("frmCustomers", "txtName", "Test Customer")
    d.set("frmCustomers", "txtPhone", "0100-000-9999")
    d.set("frmCustomers", "txtAddress", "1 Sample Lane")
    d.set("frmCustomers", "cboType", "Current")
    d.set("frmCustomers", "txtBalance", "1000")
    d.click("frmCustomers", "cmdSave")
    g = d.grid("frmCustomers", "grdCustomers")
    check(len(g) == 5 and g[4][1] == "Test Customer" and _num(g[4][4]) == 1000,
          "BankManager: saved account appears in the grid")
    check(d.query("SELECT FullName FROM Customers WHERE AccountNo = 1004") == [["Test Customer"]],
          "BankManager: the row is in bank.mdb")
    # deposit / withdraw through clsAccount
    d.click("mdiMain", "mnuTxnPost")
    d.set("frmTransaction", "txtAccNo", "1004")
    d.click("frmTransaction", "cmdLookup")
    check(d.get("frmTransaction", "lblHolder", "caption") == "Test Customer", "BankManager: look-up finds the holder")
    d.set("frmTransaction", "txtAmount", "250")
    d.click("frmTransaction", "cmdPost")
    check(d.query("SELECT Balance FROM Customers WHERE AccountNo = 1004")[0][0] == 1250,
          "BankManager: deposit 250 -> balance 1250")
    d.set("frmTransaction", "optKind", True, "value", index=1)
    check(d.get("frmTransaction", "fraKind", "caption") == "Withdraw", "BankManager: option array Click(Index)")
    d.set("frmTransaction", "txtAmount", "900")
    d.click("frmTransaction", "cmdPost")
    check(any("Not enough balance" in m for m in d.msgs), "BankManager: withdrawal below the minimum is refused")
    d.set("frmTransaction", "chkCheque", 1, "value")
    d.set("frmTransaction", "txtReference", "CHQ 1")
    d.set("frmTransaction", "txtAmount", "500")
    d.click("frmTransaction", "cmdPost")
    check(d.query("SELECT Balance FROM Customers WHERE AccountNo = 1004")[0][0] == 750,
          "BankManager: withdraw 500 by cheque -> balance 750")
    g = d.grid("frmCustomers", "grdCustomers")
    check(_num(g[4][4]) == 750, "BankManager: the open account list was refreshed")
    # statement
    d.click("mdiMain", "mnuTxnStatement")
    d.set("frmStatement", "txtAccNo", "1004")
    d.click("frmStatement", "cmdShow")
    rows = d.listview("frmStatement", "lvwTxn")
    check(len(rows) == 2 and rows[0][1] == "Deposit" and rows[1][3] == "Cheque",
          f"BankManager: statement ListView has the 2 transactions ({rows})")
    check("net -250.00" in str(d.get("frmStatement", "lblTotals", "caption")), "BankManager: statement totals")
    path = d.call("frmStatement", "ExportStatement")
    text = open(str(path), encoding="cp1252").read() if path else ""
    check("Statement of account 1004" in text and "CHQ 1" in text, "BankManager: statement exported (Print #)")
    log = (d.folder / "bank.log").read_text(encoding="cp1252")
    check("signed in" in log and "withdraw 1004" in log, "BankManager: activity log appended")
    # find + delete
    d.answers = ["Test"]
    d.click("frmCustomers", "cmdFind")
    g = d.grid("frmCustomers", "grdCustomers")
    check(len(g) == 2 and g[1][0] == "1004", "BankManager: InputBox search filters the grid")
    d.answers = [6]
    d.click("frmCustomers", "cmdDelete")
    check(d.query("SELECT COUNT(*) FROM Transactions WHERE AccountNo = 1004")[0][0] == 0 and
          d.query("SELECT COUNT(*) FROM Customers")[0][0] == 3, "BankManager: delete removes account + transactions")
    # report
    d.click("mdiMain", "mnuRptBalances")
    rep = d.rt.interp.objects.get("rptbalances")
    check(rep is not None and rep.win is not None, "BankManager: DataReport rptBalances shown")
    d.click("mdiMain", "mnuHelpAbout")
    check("Version 1.0" in str(d.get("frmAbout", "lblInfo", "caption")), "BankManager: About box (vbModal)")


# ---------------------------------------------------------------------------------------- ElectricityBilling
def ElectricityBilling(d, check):
    d.start()
    check(d.loaded("frmLogin"), "ElectricityBilling: startup form frmLogin")
    d.set("frmLogin", "txtUser", "admin")
    d.set("frmLogin", "txtPwd", "x")
    d.click("frmLogin", "cmdLogin")
    check(any("wrong password" in m for m in d.msgs), "ElectricityBilling: wrong password refused")
    d.set("frmLogin", "txtPwd", "admin")
    d.click("frmLogin", "cmdLogin")
    check(d.loaded("frmMain") and not d.loaded("frmLogin"), "ElectricityBilling: admin/admin opens frmMain")
    stats = [str(d.get("frmMain", "lblStat", "caption", index=i)) for i in range(4)]
    check(stats[0].endswith(": 3") and stats[1].endswith(": 2") and stats[2].endswith(": 0"),
          f"ElectricityBilling: summary labels (control array) {stats}")
    d.pump(1200)
    check(":" in str(d.get("frmMain", "lblClock", "caption")), "ElectricityBilling: Timer clock ticks")
    # consumers: ListBox + ItemData
    d.click("frmMain", "cmdTool", index=0)
    items = d.listbox("frmConsumers", "lstConsumers")
    check(len(items) == 3 and items[2].startswith("60201"), f"ElectricityBilling: consumer ListBox ({items})")
    d.set("frmConsumers", "lstConsumers", 1, "listindex")
    check(d.get("frmConsumers", "txtName") == "Omar Zaki" and d.get("frmConsumers", "txtMeter") == "50102",
          "ElectricityBilling: ListBox ItemData -> consumer loaded")
    d.click("frmConsumers", "cmdNew")
    check(d.keypress("frmConsumers", "txtMeter", "a") == 0, "ElectricityBilling: meter box: digits only (Like)")
    d.set("frmConsumers", "txtMeter", "50103")
    d.set("frmConsumers", "txtName", "Test Household")
    d.set("frmConsumers", "txtAddress", "9 Sample St")
    d.set("frmConsumers", "mskPhone", "0111-222-0103")
    d.click("frmConsumers", "cmdSave")
    items = d.listbox("frmConsumers", "lstConsumers")
    check(len(items) == 4 and "Test Household" in items[2], "ElectricityBilling: new consumer saved and listed")
    d.set("frmConsumers", "txtMeter", "50101")
    d.set("frmConsumers", "txtMeter", False, "locked")
    d.click("frmConsumers", "cmdSave")
    check(any("already registered" in m for m in d.msgs), "ElectricityBilling: duplicate meter refused")
    # reading
    d.click("frmMain", "mnuReading")
    cons = d.listbox("frmReading", "cboConsumer")
    i = next(k for k, s in enumerate(cons) if s.startswith("50103"))
    d.set("frmReading", "cboConsumer", i, "listindex")
    check(d.get("frmReading", "lblPrev", "caption") == "0", "ElectricityBilling: new meter starts at 0")
    d.set("frmReading", "txtCurrent", "350")
    d.click("frmReading", "cmdSave")
    check(any("350 units" in m for m in d.msgs), "ElectricityBilling: reading saved (350 units)")
    g = d.grid("frmReading", "grdHistory")
    check(len(g) == 2 and g[1][3] == "350", f"ElectricityBilling: history grid ({g})")
    d.set("frmReading", "txtCurrent", "100")
    d.click("frmReading", "cmdSave")
    check(any("smaller than the previous" in m for m in d.msgs), "ElectricityBilling: smaller reading refused")
    # bill: 350 domestic units = 100x0.50 + 200x0.85 + 50x1.25 = 282.50; +15 fixed; 5% tax 14.88 -> 312.38
    d.click("frmMain", "mnuBill")
    rs = d.listbox("frmBill", "cboReading")
    check(len(rs) == 3, f"ElectricityBilling: 3 unbilled readings ({rs})")
    i = next(k for k, s in enumerate(rs) if "50103" in s)
    d.set("frmBill", "cboReading", i, "listindex")
    txt = str(d.get("frmBill", "txtBreakdown"))
    check("50 units x 1.25 = 62.50" in txt, f"ElectricityBilling: slab breakdown ({txt!r})")
    check(d.get("frmBill", "lblTotal", "caption") == "312.38",
          f"ElectricityBilling: total 312.38 ({d.get('frmBill', 'lblTotal', 'caption')})")
    d.click("frmBill", "cmdSave")
    row = d.query("SELECT Units, Energy, Tax, Total, Paid FROM Bills WHERE MeterNo = 50103")
    check(row and row[0][0] == 350 and float(row[0][3]) == 312.38 and not row[0][4],
          f"ElectricityBilling: bill row in billing.mdb ({row})")
    check(d.query("SELECT COUNT(*) FROM Readings WHERE NOT Billed")[0][0] == 2, "ElectricityBilling: reading marked billed")
    d.click("frmBill", "cmdPrint")
    rep = d.rt.interp.objects.get("rptbill")
    check(rep is not None and rep.win is not None and len(rep._rs()._rows) == 1,
          "ElectricityBilling: parameterised DataEnvironment command + DataReport")
    bill_no = d.query("SELECT BillNo FROM Bills WHERE MeterNo = 50103")[0][0]
    d.answers = [str(bill_no)]
    d.click("frmBill", "cmdPaid")
    check(d.query(f"SELECT Paid FROM Bills WHERE BillNo = {bill_no}")[0][0], "ElectricityBilling: InputBox marks paid")
    d.answers = ["999"]
    d.click("frmBill", "cmdPaid")
    check(any("no bill 999" in m for m in d.msgs), "ElectricityBilling: RecordsAffected = 0 detected")
    d.click("frmMain", "mnuRptUnpaid")
    check(d.rt.interp.objects["rptunpaid"].win is not None, "ElectricityBilling: unpaid bills report")
    d.click("frmMain", "mnuRptTariffs")
    t = (d.folder / "tariffs.txt").read_text(encoding="cp1252")
    check('"Domestic",101,300,0.85' in t and d.shelled, f"ElectricityBilling: Write # tariff file ({t[:80]!r})")


# ---------------------------------------------------------------------------------------------- FinanceLedger
def FinanceLedger(d, check):
    import datetime as dt
    d.start()
    check(d.loaded("frmStart"), "FinanceLedger: startup form frmStart")
    check(d.wait_for(lambda: d.get("frmStart", "fraLogin", "visible") is True, 15000),
          "FinanceLedger: Timer (changing its own Interval) fills the ProgressBar, then shows the sign-in frame")
    d.set("frmStart", "txtPwd", "admin")
    d.click("frmStart", "cmdSignIn")
    check(d.loaded("frmLedger"), "FinanceLedger: admin/admin opens the ledger")
    check(d.get("frmLedger", "tabMain", "tab") == 0, "FinanceLedger: SSTab starts on Members")
    m = d.listbox("frmLedger", "lstMembers")
    check(len(m) == 3, f"FinanceLedger: 3 members listed ({m})")
    d.set("frmLedger", "lstMembers", 1, "listindex")
    info = str(d.get("frmLedger", "lblMemberInfo", "caption"))
    check("Savings: 2,000.00" in info, f"FinanceLedger: member details with savings ({info!r})")
    # add a member through the modal dialog
    d.click("frmLedger", "cmdAddMember")
    check(d.loaded("frmMember") and "S-0003" in str(d.get("frmMember", "lblPreview", "caption")),
          "FinanceLedger: modal frmMember proposes S-0003")
    d.set("frmMember", "optCurrent", True, "value")
    check("C-0002" in str(d.get("frmMember", "lblPreview", "caption")), "FinanceLedger: option changes prefix to C-")
    d.set("frmMember", "optSaver", True, "value")
    d.set("frmMember", "txtName", "Test Member")
    d.click("frmMember", "cmdOK")
    m = d.listbox("frmLedger", "lstMembers")
    check(not d.loaded("frmMember") and any(s.startswith("S-0003  Test Member") for s in m),
          "FinanceLedger: new member saved, dialog closed")
    cash = lambda: float(d.query("SELECT CashInHand FROM Cash")[0][0])       # noqa: E731
    bank = lambda: float(d.query("SELECT BankBalance FROM Cash")[0][0])      # noqa: E731
    check(cash() == 2790, f"FinanceLedger: entry fee 50 into cash ({cash()})")
    # vouchers
    d.set("frmLedger", "tabMain", 1, "tab")
    mem = d.listbox("frmLedger", "cboMember")
    d.set("frmLedger", "cboMember", next(i for i, s in enumerate(mem) if s.startswith("S-0003")), "listindex")
    d.set("frmLedger", "cboCategory", 0, "listindex")
    d.set("frmLedger", "txtAmount", "500")
    d.click("frmLedger", "cmdPost")
    check(cash() == 3290, f"FinanceLedger: savings deposit 500 cash ({cash()})")
    d.set("frmLedger", "cboCategory", 1, "listindex")
    d.set("frmLedger", "txtAmount", "900")
    d.click("frmLedger", "cmdPost")
    check(any("only 500.00 savings" in s for s in d.msgs), "FinanceLedger: withdrawal above savings refused")
    d.set("frmLedger", "cboMember", 0, "listindex")
    d.set("frmLedger", "cboCategory", 4, "listindex")
    d.set("frmLedger", "optMode", True, "value", index=1)
    d.set("frmLedger", "txtAmount", "20000")
    d.click("frmLedger", "cmdPost")
    check(any("too low for this cheque" in s for s in d.msgs) and bank() == 11500,
          "FinanceLedger: cheque above the bank balance refused (UpdateBatch recordset)")
    d.set("frmLedger", "txtAmount", "250")
    d.set("frmLedger", "txtNarration", "Printer ink")
    d.click("frmLedger", "cmdPost")
    check(bank() == 11250, f"FinanceLedger: cheque expense 250 from the bank ({bank()})")
    check(d.keypress("frmLedger", "txtAmount", "x") == 0, "FinanceLedger: amount KeyPress filter")
    # loans
    d.set("frmLedger", "tabMain", 2, "tab")
    lm = d.listbox("frmLedger", "cboLoanMember")
    d.set("frmLedger", "cboLoanMember", next(i for i, s in enumerate(lm) if s.startswith("S-0003")), "listindex")
    d.set("frmLedger", "txtPrincipal", "5000")
    d.click("frmLedger", "cmdIssue")
    check(any("needs savings of at least 1,000.00" in s for s in d.msgs), "FinanceLedger: loan rule (20% savings)")
    d.set("frmLedger", "cboLoanMember", next(i for i, s in enumerate(lm) if s.startswith("S-0001")), "listindex")
    d.set("frmLedger", "txtPrincipal", "2000")
    d.click("frmLedger", "cmdIssue")
    g = d.grid("frmLedger", "grdLoans")
    check(len(g) == 2 and g[1][1] == "S-0001" and g[1][6] == "2,000.00", f"FinanceLedger: loan in the grid ({g})")
    check(cash() == 1290, f"FinanceLedger: loan paid out in cash ({cash()})")
    d.set("frmLedger", "grdLoans", 1, "row")
    d.answers = ["500"]
    d.click("frmLedger", "cmdRepay")
    g = d.grid("frmLedger", "grdLoans")
    check(g[1][5] == "500.00" and g[1][6] == "1,500.00" and cash() == 1790,
          f"FinanceLedger: InputBox repayment ({g[1]}, cash {cash()})")
    # interest: tiered rate by days
    d.set("frmLedger", "tabMain", 3, "tab")
    im = d.listbox("frmLedger", "cboIntMember")
    d.set("frmLedger", "cboIntMember", next(i for i, s in enumerate(im) if s.startswith("S-0001")), "listindex")
    since = dt.date.today() - dt.timedelta(days=100)
    d.set("frmLedger", "dtpSince", since.strftime("%Y-%m-%d"), "value")
    d.click("frmLedger", "cmdCalcInterest")
    expect = round(2000 * 100 * 5 / 365 / 100, 2)
    res = str(d.get("frmLedger", "lblIntResult", "caption"))
    check(f"100 days at 5%" in res and f"{expect:,.2f}" in res, f"FinanceLedger: interest {expect} ({res!r})")
    d.click("frmLedger", "cmdPayInterest")
    check(abs(float(d.query("SELECT SUM(Amount) FROM Ledger WHERE Category = 'Interest'")[0][0]) - expect) < 0.001
          and cash() == 1790, "FinanceLedger: interest credited, cash balanced by the expense")
    # day book
    d.set("frmLedger", "tabMain", 4, "tab")
    d.click("frmLedger", "cmdDayBook")
    today = d.grid("frmLedger", "grdDayBook")
    d.set("frmLedger", "chkAllDays", 1, "value")
    d.click("frmLedger", "cmdDayBook")
    allrows = d.grid("frmLedger", "grdDayBook")
    n_ledger = d.query("SELECT COUNT(*) FROM Ledger")[0][0]
    check(len(allrows) - 1 == n_ledger and 1 < len(today) < len(allrows),
          f"FinanceLedger: day book today {len(today) - 1} rows, all {len(allrows) - 1} rows")
    check("difference" in str(d.get("frmLedger", "lblDayTotals", "caption")), "FinanceLedger: day book totals")
    # P & L recomputed on the tab Click(PreviousTab)
    d.set("frmLedger", "tabMain", 5, "tab")
    d.pump(150)
    pl = [str(d.get("frmLedger", "lblPL", "caption", index=i)) for i in range(4)]
    check(pl[3].startswith("Net loss:") and "1,500.00" in pl[2], f"FinanceLedger: profit & loss ({pl})")


# ---------------------------------------------------------------------------------------- ScientificCalculator
def ScientificCalculator(d, check):
    F = "frmCalc"
    d.start()
    disp = lambda: str(d.get(F, "lblDisplay", "caption"))          # noqa: E731

    def keys(seq):
        for k in seq:
            if k.isdigit():
                d.click(F, "cmdDigit", index=int(k))
            elif k == ".":
                d.click(F, "cmdDot")
            elif k in "+-*/%^":
                d.click(F, "cmdOp", index="+-*/%^".index(k))
            elif k == "=":
                d.click(F, "cmdEquals")
    check(d.loaded(F) and disp() == "0", "ScientificCalculator: form shows 0")
    keys("12+30=")
    check(disp() == "42", f"ScientificCalculator: 12 + 30 = 42 ({disp()})")
    keys("2^10=")
    check(disp() == "1024", f"ScientificCalculator: 2 ^ 10 = 1024 ({disp()})")
    keys("7.5*4-10=")
    check(disp() == "20", f"ScientificCalculator: chained 7.5 * 4 - 10 = 20 ({disp()})")
    keys("17%5=")
    check(disp() == "2", f"ScientificCalculator: 17 Mod 5 = 2 ({disp()})")
    keys("30")
    d.click(F, "cmdFunc", index=0)
    check(disp() == "0.5", f"ScientificCalculator: sin(30 deg) = 0.5 ({disp()})")
    keys("180")
    d.click(F, "cmdFunc", index=0)
    check(disp() == "0", f"ScientificCalculator: sin(180 deg) = 0 ({disp()})")
    d.set(F, "optAngle", True, "value", index=1)
    check("radians" in str(d.get(F, "lblStatus", "caption")), "ScientificCalculator: option array -> radians")
    d.click(F, "cmdFunc", index=11)
    d.click(F, "cmdFunc", index=1)
    check(disp() == "-1", f"ScientificCalculator: cos(pi rad) = -1 ({disp()})")
    keys("5")
    d.click(F, "cmdFunc", index=9)
    check(disp() == "120", f"ScientificCalculator: 5! = 120 ({disp()})")
    keys("2.5")
    d.click(F, "cmdFunc", index=9)
    check(disp() == "Error" and "Invalid input" in str(d.get(F, "lblStatus", "caption")),
          "ScientificCalculator: 2.5! -> error 5 trapped")
    keys("1/0=")
    check(disp() == "Error" and "divide by zero" in str(d.get(F, "lblStatus", "caption")),
          "ScientificCalculator: 1 / 0 -> division by zero trapped")
    keys("1000")
    d.click(F, "cmdFunc", index=3)
    check(disp() == "3", f"ScientificCalculator: log(1000) = 3 ({disp()})")
    keys("200+10")
    d.click(F, "cmdFunc", index=10)
    check(disp() == "20", f"ScientificCalculator: 200 + 10 % -> 20 ({disp()})")
    keys("=")
    check(disp() == "220", f"ScientificCalculator: ... = 220 ({disp()})")
    d.click(F, "cmdMem", index=2)
    keys("5")
    d.click(F, "cmdMem", index=3)
    d.click(F, "cmdCE")
    d.click(F, "cmdMem", index=1)
    check(disp() == "225" and d.get(F, "lblMem", "caption") == "M", f"ScientificCalculator: MS, M+, MR -> 225 ({disp()})")
    # keyboard through Form_KeyPress (KeyPreview)
    for ch in "7*6\r":
        d.keypress(F, "Form", ch)
    check(disp() == "42", f"ScientificCalculator: keyboard 7*6 Enter = 42 ({disp()})")
    d.keypress(F, "Form", "\x1b")
    check(disp() == "0", "ScientificCalculator: Esc clears")
    keys("123")
    d.click(F, "cmdBack")
    d.click(F, "cmdSign")
    check(disp() == "-12", f"ScientificCalculator: backspace and +/- ({disp()})")
    hist = d.listbox(F, "lstHistory")
    check(len(hist) >= 10 and "12 + 30 = 42" in hist and "fact(5) = 120" in hist,
          f"ScientificCalculator: history ListBox ({len(hist)} lines)")
    d.click(F, "mnuSaveHistory")
    d.click(F, "mnuClearHistory")
    check(d.listbox(F, "lstHistory") == [], "ScientificCalculator: history cleared")
    d.click(F, "mnuLoadHistory")
    check(d.listbox(F, "lstHistory") == hist, "ScientificCalculator: history saved and loaded (Print # / Line Input #)")
    d.set(F, "lstHistory", 0, "listindex")
    d.event(F, "lstHistory_DblClick", event="DoubleClick")
    check(disp() == "42", f"ScientificCalculator: double-click a history line recalls 42 ({disp()})")
    d.click(F, "mnuCopy")
    keys("9")
    d.click(F, "mnuPaste")
    check(disp() == "42", f"ScientificCalculator: Clipboard copy / paste ({disp()})")
    d.pump(1100)
    check(str(d.get(F, "lblClock", "caption")).count(":") == 2, "ScientificCalculator: Timer clock")


# ---------------------------------------------------------------------------------------------- ClinicManager
def ClinicManager(d, check):
    F = "frmMain"
    d.answers = ["9999", "1234"]                 # a wrong PIN, then the demo PIN
    d.start()
    check(any("Unknown PIN" in m for m in d.msgs), "ClinicManager: wrong PIN refused (InputBox in Sub Main)")
    check(d.loaded(F), "ClinicManager: PIN 1234 opens frmMain")
    d.pump(300)
    check(d.get(F, "txtName") == "Mona Ibrahim" and d.get(F, "txtNo") == "1",
          "ClinicManager: Data control opened after Form_Load, bound TextBoxes show record 1")
    check(d.get(F, "lblPosition", "caption") == "Patient 1 of 3", f"ClinicManager: Reposition event "
          f"({d.get(F, 'lblPosition', 'caption')})")
    check(str(d.get(F, "lblAge", "caption")).endswith("years"), "ClinicManager: age computed (DateDiff)")
    dc = d.form(F).controls["datpatients"]
    dc.move_next()
    d.pump(50)
    check(d.get(F, "txtName") == "Youssef Nabil" and d.get(F, "lblPosition", "caption") == "Patient 2 of 3",
          "ClinicManager: Data control > arrow moves to record 2")
    # add a patient through the Data control (AddNew + bound controls + Update)
    d.click(F, "cmdAdd")
    check(d.get(F, "txtNo") == "4" and d.get(F, "txtName") == "", "ClinicManager: AddNew clears the bound controls")
    d.set(F, "txtName", "Test Patient")
    d.set(F, "cboGender", "M")
    d.set(F, "txtBirth", "2000-02-29")
    d.set(F, "txtPhone", "0122-000-0099")
    d.set(F, "cboBlood", "AB+")
    d.click(F, "cmdSave")
    row = d.query("SELECT FullName, Gender, BloodGroup FROM Patients WHERE PatientNo = 4")
    check(row == [["Test Patient", "M", "AB+"]], f"ClinicManager: new patient saved through the Data control ({row})")
    check(d.get(F, "lblPosition", "caption") == "Patient 4 of 4", "ClinicManager: Bookmark = LastModified")
    # edit a bound field and save
    d.set(F, "txtPhone", "0122-000-0100")
    d.click(F, "cmdSave")
    check(d.query("SELECT Phone FROM Patients WHERE PatientNo = 4") == [["0122-000-0100"]],
          "ClinicManager: Edit + Update writes the changed bound control")
    # find
    d.answers = ["Salma"]
    d.click(F, "cmdFind")
    check(d.get(F, "txtName") == "Salma Fouad", "ClinicManager: FindFirst LIKE through the Data control")
    d.answers = ["Nobody"]
    d.click(F, "cmdFind")
    check(any("No patient called" in m for m in d.msgs), "ClinicManager: NoMatch handled")
    # visits tab: patient 2 has 2 visits
    dc.move_next()
    d.pump(50)
    d.set(F, "tabClinic", 1, "tab")              # SSTab1.Tab = n fires tabClinic_Click
    d.pump(150)
    g = d.grid(F, "grdVisits")
    check(len(g) == 3 and g[1][2] == "135/88", f"ClinicManager: visits of patient 2 in the grid ({g})")
    d.click(F, "cmdNewVisit")
    check(d.loaded("frmVisit") and "Youssef Nabil" in str(d.get("frmVisit", "lblPatient", "caption")),
          "ClinicManager: modal frmVisit prepared by a Public Sub (StartFor)")
    d.set("frmVisit", "txtWeight", "abc")
    d.click("frmVisit", "cmdSave")
    check(any("Weight must be a number" in m for m in d.msgs), "ClinicManager: visit validation")
    d.set("frmVisit", "txtWeight", "86.4")
    d.set("frmVisit", "mskBP", "122/80")
    d.set("frmVisit", "txtPulse", "70")
    d.set("frmVisit", "txtTemp", "38.6")
    d.event("frmVisit", "txtTemp_Change", event="TextChanged")
    check(d.get("frmVisit", "lblWarn", "caption") == "Fever!", "ClinicManager: Change event warns about fever")
    d.set("frmVisit", "txtDiagnosis", "Test visit")
    d.set("frmVisit", "cboMedicine", "Cough syrup (demo)")
    d.click("frmVisit", "cmdSave")
    g = d.grid(F, "grdVisits")
    check(not d.loaded("frmVisit") and len(g) == 4 and g[3][5] == "Test visit",
          "ClinicManager: DAO AddNew / Update visit, grid refreshed")
    # statistics: Shape bar chart
    d.set(F, "tabClinic", 2, "tab")              # SSTab1.Tab = n fires tabClinic_Click
    d.pump(150)
    stats = str(d.get(F, "lblStats", "caption"))
    check("Patients: 4" in stats and "Visits: 4" in stats, f"ClinicManager: statistics ({stats!r})")
    hf, hm = d.get(F, "shpBar", "height", index=0), d.get(F, "shpBar", "height", index=1)
    check(abs(hf - hm) <= 30 and hf > 1000 and d.get(F, "lblBar", "caption", index=0) == "F: 2",
          f"ClinicManager: Shape bars sized from the counts ({hf}, {hm})")
    # remove patient 2 with its visits
    d.answers = ["2", 6]
    d.click(F, "cmdRemove")
    check(d.query("SELECT COUNT(*) FROM Visits WHERE PatientNo = 2")[0][0] == 0 and
          d.query("SELECT COUNT(*) FROM Patients")[0][0] == 3, "ClinicManager: patient + visits removed (DAO Delete loop)")
    check(d.get(F, "lblPosition", "caption") == "Patient 1 of 3", "ClinicManager: Data control refreshed")


# ---------------------------------------------------------------------------------------------- LogicGateLab
def LogicGateLab(d, check):
    F = "frmLab"
    d.start()
    GREEN, GREY = 0x00FF00, 0x404040
    col = lambda name: d.get(F, name, "backcolor")          # noqa: E731
    check(d.loaded(F) and d.get(F, "lblOut", "caption") == "0", "LogicGateLab: AND with A=0 B=0 -> 0")
    d.set(F, "chkA", 1, "value")
    d.set(F, "chkB", 1, "value")
    check(d.get(F, "lblOut", "caption") == "1" and col("shpOut") == GREEN and col("linOut") == GREEN
          and col("linA") == GREEN, "LogicGateLab: A=1 B=1 -> 1, lamp and wires (Line.BorderColor) green")
    check(d.get(F, "shpPulse", "visible") is True, "LogicGateLab: pulse dot shown while the output is 1")
    x0 = d.get(F, "shpPulse", "left")
    d.pump(400)
    x1 = d.get(F, "shpPulse", "left")
    check(x1 != x0, f"LogicGateLab: Timer moves the Shape along the wire ({x0} -> {x1})")
    lo, hi = d.get(F, "linOut", "x1"), d.get(F, "linOut", "x2")
    check(abs(lo - 6300) <= 15 and abs(hi - 7800) <= 15, f"LogicGateLab: Line X1 / X2 ({lo}, {hi})")
    expect = {0: "1", 1: "1", 2: "0", 3: "0", 4: "0", 5: "0", 6: "1"}       # with A=1, B=1
    got = {}
    for i in range(7):
        d.set(F, "optGate", True, "value", index=i)
        got[i] = d.get(F, "lblOut", "caption")
    check(got == expect, f"LogicGateLab: the 7 gates with A=B=1 via the option array ({got})")
    check(d.get(F, "lblGate", "caption") == "XNOR" and "NOT (A XOR B)" in str(d.get(F, "lblStatus", "caption")),
          "LogicGateLab: gate name and expression (clsGate)")
    d.set(F, "optGate", True, "value", index=5)
    d.set(F, "chkB", 0, "value")
    check(d.get(F, "lblOut", "caption") == "1" and col("linB") == GREY, "LogicGateLab: XOR 1,0 -> 1")
    # two-gate circuit: (A NAND B) AND C  with A=1 B=0 C=1 -> 1
    d.set(F, "cboOp1", 3, "listindex")
    d.set(F, "cboOp2", 0, "listindex")
    d.set(F, "chkC", 1, "value")
    lc = str(d.get(F, "lblCircuit", "caption"))
    check(lc == "(NOT (A AND B)) AND C = 1" and col("shpCircuitOut") == GREEN,
          f"LogicGateLab: circuit of two clsGate objects ({lc!r})")
    # clock: the Timer toggles A
    d.set(F, "hsbSpeed", 100, "value")
    check(d.get(F, "lblSpeed", "caption") == "100 ms", "LogicGateLab: HScrollBar Change event")
    seen = set()
    d.set(F, "chkClock", 1, "value")
    for _ in range(30):
        d.pump(40)
        seen.add(d.get(F, "chkA", "value"))
    d.set(F, "chkClock", 0, "value")
    check(seen == {0, 1}, f"LogicGateLab: clock Timer toggles input A ({seen})")
    # truth table window
    d.set(F, "optGate", True, "value", index=4)
    d.click(F, "cmdTruth")
    g = d.grid("frmTruth", "grdTruth")
    check(g[0] == ["A", "B", "NOR"] and [r[2] for r in g[1:]] == ["1", "0", "0", "0"],
          f"LogicGateLab: NOR truth table in the modeless window ({g})")
    check("1 of 4" in str(d.get("frmTruth", "lblOnes", "caption")), "LogicGateLab: truth table summary")
    d.set(F, "optGate", True, "value", index=2)
    d.click(F, "cmdTruth")
    g = d.grid("frmTruth", "grdTruth")
    check(len(g) == 3 and g[1][2] == "1" and g[2][2] == "0", f"LogicGateLab: NOT has 2 rows ({g})")
    path = d.call("frmTruth", "ExportAll")
    t = open(str(path), encoding="cp1252").read() if path else ""
    check(t.count("->") == 26 and "XNOR" in t, f"LogicGateLab: all tables exported ({t.count('->')} rows)")
    check(d.grid("frmTruth", "grdTruth")[0][2] == "NOT", "LogicGateLab: Property Get of another form (frmLab.CurrentKind)")
    # save / open the setup (the CommonDialog answers are scripted)
    setup = str(d.folder / "test.lgl")
    dlg = d.form(F).controls["dlgfile"]
    dlg._dialog_result = lambda method: (setattr(dlg.w, "FileName", setup), "OK")[1]
    d.set(F, "optGate", True, "value", index=6)
    d.set(F, "chkA", 1, "value")
    d.click(F, "mnuSave")
    check("LogicGateLab" in open(setup).read(), "LogicGateLab: Write # setup file")
    d.set(F, "optGate", True, "value", index=0)
    d.set(F, "chkA", 0, "value")
    d.click(F, "mnuOpen")
    check(d.get(F, "lblGate", "caption") == "XNOR" and d.get(F, "chkA", "value") == 1
          and d.get(F, "hsbSpeed", "value") == 100, "LogicGateLab: Input # restores the setup")
    dlg._dialog_result = lambda method: (_ for _ in ()).throw(__import__("radide.runtimes.vbinterp",
                                                                         fromlist=["err"]).err(32755, "Cancel"))
    d.click(F, "mnuOpen")
    check(not any("Could not open" in m for m in d.msgs), "LogicGateLab: CancelError (cdlCancel) ignored")


# ---------------------------------------------------------------------------------------------- PharmacyStore
def PharmacyStore(d, check):
    d.start()
    check(d.loaded("frmSplash"), "PharmacyStore: Sub Main shows the splash")
    check(d.query("SELECT COUNT(*) FROM StockLog")[0][0] == 0, "PharmacyStore: StockLog created at start-up (runtime DDL)")
    check(d.wait_for(lambda: d.loaded("frmLogin"), 10000) and not d.loaded("frmSplash"),
          "PharmacyStore: splash Timer -> Unload Me -> login (the program keeps running)")
    d.set("frmLogin", "txtUser", "admin")
    d.set("frmLogin", "txtPassword", "bad")
    d.click("frmLogin", "cmdLogin")
    check(any("Login failed" in m for m in d.msgs), "PharmacyStore: wrong login refused")
    d.set("frmLogin", "txtPassword", "admin")
    d.click("frmLogin", "cmdLogin")
    check(d.loaded("mdiStore") and "reorder: 2" in str(d.get("mdiStore", "lblStatus", "caption")),
          "PharmacyStore: MDI parent with status line (2 to reorder)")
    # medicines: ADO recordset navigation and editing
    M = "frmMedicines"
    d.click("mdiStore", "mnuMedicines")
    check(d.get(M, "txtCode") == "M001" and d.get(M, "lblRecord", "caption") == "1 / 5", "PharmacyStore: record 1 / 5")
    d.click(M, "cmdNav", index=2)
    check(d.get(M, "txtCode") == "M002" and "expires in" in str(d.get(M, "lblWarning", "caption")),
          "PharmacyStore: > moves to M002, expiry warning (DateDiff)")
    d.click(M, "cmdNav", index=3)
    check(d.get(M, "lblRecord", "caption") == "5 / 5", "PharmacyStore: >| last record")
    check(d.get(M, "txtName", "locked") is True, "PharmacyStore: fields locked while browsing (For Each + TypeOf)")
    d.click(M, "cmdAdd")
    check(d.get(M, "cmdAdd", "caption") == "&Save" and d.get(M, "txtName", "locked") is False,
          "PharmacyStore: Add -> the button becomes Save")
    d.set(M, "txtCode", "m006")
    d.set(M, "txtName", "Test bandage (demo)")
    d.set(M, "txtPrice", "1.25")
    d.set(M, "txtStock", "40")
    d.click(M, "cmdAdd")
    check(d.get(M, "cmdAdd", "caption") == "&Add" and d.get(M, "lblRecord", "caption") == "6 / 6"
          and d.query("SELECT MedName FROM Medicines WHERE Code = 'M006'") == [["Test bandage (demo)"]],
          "PharmacyStore: rs.AddNew / rs!Field / rs.Update")
    d.click(M, "cmdEdit")
    d.set(M, "txtPrice", "1.40")
    d.click(M, "cmdEdit")
    check(float(d.query("SELECT UnitPrice FROM Medicines WHERE Code = 'M006'")[0][0]) == 1.4,
          "PharmacyStore: Edit/Update state button")
    d.answers = [6]
    d.click(M, "cmdDelete")
    check(d.query("SELECT COUNT(*) FROM Medicines")[0][0] == 5 and d.get(M, "lblRecord", "caption") == "5 / 5",
          "PharmacyStore: rs.Delete + MoveNext")
    # purchase
    P = "frmPurchase"
    d.click("mdiStore", "mnuPurchase")
    meds = d.listbox(P, "cboMedicine")
    d.set(P, "cboMedicine", next(i for i, s in enumerate(meds) if s.startswith("M004")), "listindex")
    check(d.keypress(P, "txtQty", "x") == 0, "PharmacyStore: quantity KeyPress filter")
    d.set(P, "txtQty", "50")
    d.set(P, "txtCost", "2.10")
    d.set(P, "txtBatch", "B77")
    d.click(P, "cmdSave")
    check(d.query("SELECT Stock FROM Medicines WHERE Code = 'M004'")[0][0] == 59, "PharmacyStore: purchase adds stock")
    g = d.grid(P, "grdRecent")
    check(len(g) == 2 and g[1][1] == "M004" and g[1][4] == "B77", f"PharmacyStore: recent purchases grid ({g})")
    check("reorder: 1" in str(d.get("mdiStore", "lblStatus", "caption")), "PharmacyStore: status line refreshed")
    # sale
    S = "frmSale"
    d.click("mdiStore", "mnuNewSale")
    meds = d.listbox(S, "cboMedicine")
    pick = lambda code: d.set(S, "cboMedicine", next(i for i, s in enumerate(meds) if s.startswith(code)),  # noqa
                              "listindex")
    pick("M001")
    d.set(S, "txtQty", "10")
    d.click(S, "cmdAddItem")
    pick("M002")
    d.set(S, "txtQty", "30")
    d.click(S, "cmdAddItem")
    check(any("Only 18 in stock" in m for m in d.msgs), "PharmacyStore: stock check before adding a line")
    pick("M003")
    d.set(S, "txtQty", "2")
    d.click(S, "cmdAddItem")
    rows = d.listview(S, "lvwCart")
    check(len(rows) == 2 and rows[0][4] == "25.00" and rows[1][4] == "12.00", f"PharmacyStore: invoice lines ({rows})")
    d.set(S, "txtDiscount", "10")
    d.event(S, "txtDiscount_Change", event="TextChanged")
    check(d.get(S, "lblTotal", "caption") == "33.30", f"PharmacyStore: 37.00 - 10% = 33.30 ({d.get(S, 'lblTotal', 'caption')})")
    d.click(S, "cmdSave")
    sale = d.query("SELECT InvoiceNo, Total FROM Sales")
    check(len(sale) == 1 and float(sale[0][1]) == 33.3, f"PharmacyStore: invoice saved ({sale})")
    check(d.query("SELECT Stock FROM Medicines WHERE Code = 'M001'")[0][0] == 110, "PharmacyStore: sale lowers stock")
    check(d.query("SELECT COUNT(*) FROM StockLog")[0][0] == 3, "PharmacyStore: stock movements logged")
    d.click(S, "cmdPrint")
    rep = d.rt.interp.objects["rptinvoice"]
    check(rep.win is not None and len(rep._rs()._rows) == 2, "PharmacyStore: invoice DataReport (2 lines)")
    # alerts + public variables to the sale form
    A = "frmAlerts"
    d.click("mdiStore", "mnuAlerts")
    g = d.grid(A, "grdAlerts")
    check(len(g) == 3 and [r[0] for r in g[1:]] == ["M002", "M005"] and "reorder" in g[1][4],
          f"PharmacyStore: alerts grid ({g})")
    d.set(A, "txtDays", "10")
    d.event(A, "txtDays_Change", event="TextChanged")
    check(len(d.grid(A, "grdAlerts")) == 2, "PharmacyStore: fewer alerts within 10 days")
    d.set(A, "grdAlerts", 1, "row")
    d.click(A, "cmdSell")
    check(str(d.get(S, "cboMedicine")).startswith("M002"), "PharmacyStore: picked medicine passed through public variables")
    path = d.call(A, "ExportCsv")
    t = open(str(path), encoding="cp1252").read() if path else ""
    check(t.startswith('"Code","Medicine"') and '"M002"' in t, "PharmacyStore: CSV export")
    d.click("mdiStore", "mnuTodaySales")
    check(any("Invoices today: 1" in m for m in d.msgs), "PharmacyStore: nested menu Reports > More > Today's sales")


# ---------------------------------------------------------------------------------------------- OnlineExam
def OnlineExam(d, check):
    W, E = "frmWelcome", "frmExam"
    d.start()
    check(d.loaded(W) and d.listbox(W, "cboSubject") == ["VB6 basics"], "OnlineExam: welcome form lists the exams")
    d.set(W, "optRole", True, "value", index=1)
    check(d.get(W, "cboSubject", "enabled") is False, "OnlineExam: role option array disables the exam list")
    d.set(W, "txtUser", "student1")
    d.set(W, "txtPwd", "student1")
    d.click(W, "cmdSignIn")
    check(any("not an examiner account" in m for m in d.msgs), "OnlineExam: role is checked")
    d.set(W, "optRole", True, "value", index=0)
    d.click(W, "cmdSignIn")
    check(d.loaded(E) and d.fprop(W, "visible") is False, "OnlineExam: student starts the exam, welcome hidden")
    check(d.get(E, "lblProgress", "caption").startswith("Question 1 of 4") and d.get(E, "lblTime", "caption") == "10:00",
          "OnlineExam: 4 questions (UDT array), 10:00 countdown")
    check(str(d.get(E, "optAns", "caption", index=0)).endswith("Dim"), "OnlineExam: answers on the option array")
    d.set(E, "optAns", True, "value", index=0)        # Q1: A (right)
    d.click(E, "cmdNext")
    check(d.get(E, "optAns", "value", index=0) is False, "OnlineExam: options cleared for the next question")
    d.set(E, "optAns", True, "value", index=1)        # Q2: B (right)
    d.click(E, "cmdNext")
    d.set(E, "optAns", True, "value", index=2)        # Q3: C (wrong)
    d.click(E, "cmdNext")
    check(d.get(E, "cmdNext", "enabled") is False, "OnlineExam: last question disables Next")
    d.click(E, "cmdPrev")
    check(d.get(E, "optAns", "value", index=2) is True, "OnlineExam: the chosen answer comes back on Previous")
    check(d.get(E, "prgAnswered", "value") == 3, "OnlineExam: ProgressBar = answered questions")
    d.pump(1300)
    check(d.get(E, "lblTime", "caption") in ("09:59", "09:58"), f"OnlineExam: Timer counts down ({d.get(E, 'lblTime', 'caption')})")
    d.answers = [6]
    d.click(E, "cmdFinish")
    check(any("1 question(s) are not answered" in m for m in d.msgs), "OnlineExam: unanswered question warning")
    check(not d.loaded(E) and d.loaded("frmScore"), "OnlineExam: score card shown")
    det = str(d.get("frmScore", "lblDetails", "caption"))
    check("Score: 4 / 8  (50%)" in det and d.get("frmScore", "lblVerdict", "caption") == "PASS",
          f"OnlineExam: 2 of 4 right = 4/8 = 50% -> PASS ({det!r})")
    check(d.get("frmScore", "lblReview", "caption") == "Wrong or missing: question id 3, 4", "OnlineExam: review line")
    check(d.query("SELECT COUNT(*) FROM Answers")[0][0] == 4, "OnlineExam: answers saved (DAO AddNew)")
    d.click("frmScore", "cmdClose")
    check(d.fprop(W, "visible") is True, "OnlineExam: back to the welcome form")
    # time is up for student2
    d.set(W, "txtUser", "student2")
    d.set(W, "txtPwd", "student2")
    d.click(W, "cmdSignIn")
    d.set(E, "optAns", True, "value", index=3)
    d.form(E).vb_set("secondsleft", 2)                  # frmExam.SecondsLeft = 2 (Property Let of a form)
    check(d.wait_for(lambda: d.loaded("frmScore") and not d.loaded(E), 6000), "OnlineExam: time up ends the exam")
    check(any("Time is up" in m for m in d.msgs) and d.get("frmScore", "lblVerdict", "caption") == "FAIL",
          "OnlineExam: time-up result FAIL")
    d.click("frmScore", "cmdClose")
    # examiner
    d.set(W, "optRole", True, "value", index=1)
    d.set(W, "txtUser", "admin")
    d.set(W, "txtPwd", "admin")
    d.click(W, "cmdSignIn")
    check(d.loaded("mdiAdmin"), "OnlineExam: admin/admin opens the MDI administration")
    Q = "frmQuestions"
    d.click("mdiAdmin", "mnuQuestions")
    check(d.get(Q, "lblCount", "caption").startswith("5 questions") and
          d.get(Q, "lblNav", "caption").startswith("Question 1 of 5"), "OnlineExam: DAO question bank, 1 of 5")
    d.click(Q, "cmdNav", index=3)
    check(d.get(Q, "txtOpt", "text", index=1) == "&", "OnlineExam: >| shows the last question (TextBox array)")
    d.click(Q, "cmdNew")
    d.set(Q, "txtQuestion", "Which statement leaves a loop early?")
    for i, s in enumerate(["Exit Do", "Stop Loop", "Break", "Leave"]):
        d.set(Q, "txtOpt", s, index=i)
    d.set(Q, "txtOpt", "", index=3)
    d.click(Q, "cmdSave")
    check(any("Option D is empty" in m for m in d.msgs), "OnlineExam: empty option refused")
    d.set(Q, "txtOpt", "Leave", index=3)
    d.set(Q, "txtMarks", "3")
    d.click(Q, "cmdSave")
    check(d.get(Q, "lblNav", "caption").startswith("Question 6 of 6"), f"OnlineExam: new question saved, 6 of 6 "
          f"({d.get(Q, 'lblNav', 'caption')})")
    d.set(Q, "cboSubject", 1, "listindex")
    d.answers = ["planet"]
    d.click(Q, "cmdFind")
    check("Sun" in str(d.get(Q, "txtQuestion")), "OnlineExam: FindFirst LIKE in the other subject")
    d.set(Q, "cboSubject", 0, "listindex")
    d.click(Q, "cmdNav", index=0)
    d.click(Q, "cmdDelete")
    check(any("used in a question paper" in m for m in d.msgs), "OnlineExam: question on a paper cannot be deleted")
    # question paper for General knowledge
    P = "frmPaper"
    d.click("mdiAdmin", "mnuPaper")
    d.set(P, "cboSubject", 1, "listindex")
    check(len(d.listview(P, "lvwBank")) == 5 and d.listview(P, "lvwPaper") == [], "OnlineExam: GK paper is empty")
    for _ in range(3):
        d.click(P, "cmdAdd")
    check(len(d.listview(P, "lvwPaper")) == 3 and len(d.listview(P, "lvwBank")) == 2, "OnlineExam: >> moves 3 questions")
    d.click(P, "cmdRemove")
    check("2 questions, 2 marks" in str(d.get(P, "lblTotal", "caption")), "OnlineExam: << removes one")
    d.set(P, "txtDuration", "5")
    d.set(P, "txtPass", "60")
    d.click(P, "cmdSavePaper")
    check(d.query("SELECT DurationMin, PassPercent FROM Papers WHERE SubjectID = 2") == [[5, 60]],
          "OnlineExam: paper saved (UPDATE, RecordsAffected = 0 -> INSERT)")
    # results + report
    R = "frmResults"
    d.click("mdiAdmin", "mnuResults")
    g = d.grid(R, "grdResults")
    check(len(g) == 3 and g[1][5] == "PASS" and g[2][5] == "FAIL", f"OnlineExam: results grid ({g})")
    check("2 results, 1 passed (50%)" in str(d.get(R, "lblSummary", "caption")), "OnlineExam: pass rate")
    d.click(R, "cmdReport")
    check(d.rt.interp.objects["rptresults"].win is not None, "OnlineExam: results DataReport")
    # students (nested menu)
    d.answers = ["Student3", "Demo Student Three"]
    d.click("mdiAdmin", "mnuAddStudent")
    d.click("mdiAdmin", "mnuListStudents")
    check(any("student3 - Demo Student Three" in m for m in d.msgs), "OnlineExam: Exam > Students > Add / List")
