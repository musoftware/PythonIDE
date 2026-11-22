# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Ring Contacts - a small address book (CRUD) in RingQt with an SQLite database.
# Shows: TextBoxes + ListBox + Buttons, live search (TextChanged), SQLite through Ring's sqlitelib,
# a modal Settings form (Form2), saved settings (settings.ini), an Arabic right-to-left interface,
# CSV export through the SaveFileDialog component, MsgBox-style questions with qMessageBox.

load "Form1_designer.ring"
load "sqlitelib.ring"

oDB = NULL              # the SQLite connection (contacts.db next to the program)
aIds = []               # contact id of every line of lstContacts
nCurrent = 0            # id of the selected contact (0 = none)
cLang = "en"            # "en" or "ar" (settings.ini)
lConfirm = true         # ask before deleting (settings.ini)

# ---------------- Event handlers ----------------

func Form1_Load
    LoadSettings()
    oDB = sqlite_init()
    sqlite_open(oDB, "contacts.db")
    sqlite_execute(oDB, "create table if not exists contacts (id integer primary key autoincrement, " +
                        "name text not null, phone text, email text)")
    if len(sqlite_execute(oDB, "select id from contacts limit 1")) = 0      # first run: sample data
        AddContact("Sara Adel", "+20 100 000 0001", "sara@example.com")
        AddContact("محمد علي", "+20 100 000 0002", "mohamed@example.com")
        AddContact("John Smith", "+44 20 0000 0003", "john@example.com")
    ok
    ApplyLanguage()
    Refresh()

func Form1_FormClosing oEvent
    if not isNull(oDB) sqlite_close(oDB) ok

func txtSearch_TextChanged
    Refresh()

func lstContacts_SelectedIndexChanged
    nRow = lstContacts.currentRow() + 1
    if nRow < 1 or nRow > len(aIds) return ok
    nCurrent = aIds[nRow]
    aRows = sqlite_execute(oDB, "select * from contacts where id = " + nCurrent)
    if len(aRows) = 0 return ok
    txtName.setText(aRows[1][:name])
    txtPhone.setText(aRows[1][:phone])
    txtEmail.setText(aRows[1][:email])

func cmdAdd_Click
    if not Valid() return ok
    AddContact(txtName.text(), txtPhone.text(), txtEmail.text())
    Status(T("Added ", "تمت إضافة ") + txtName.text())
    cmdClear_Click()
    Refresh()

func cmdUpdate_Click
    if nCurrent = 0 Status(T("Select a contact first", "اختر جهة اتصال أولاً")) return ok
    if not Valid() return ok
    sqlite_execute(oDB, "update contacts set name = " + Sql(txtName.text()) + ", phone = " + Sql(txtPhone.text()) +
                        ", email = " + Sql(txtEmail.text()) + " where id = " + nCurrent)
    Status(T("Updated ", "تم تعديل ") + txtName.text())
    Refresh()

func cmdDelete_Click
    if nCurrent = 0 Status(T("Select a contact first", "اختر جهة اتصال أولاً")) return ok
    if lConfirm
        oMsg = new qMessageBox(Form1)
        oMsg.setWindowTitle(T("Delete", "حذف"))
        oMsg.setText(T("Delete ", "حذف ") + txtName.text() + "?")
        oMsg.setStandardButtons(16384 | 65536)         # QMessageBox::Yes | QMessageBox::No
        if oMsg.exec() != 16384 return ok
    ok
    sqlite_execute(oDB, "delete from contacts where id = " + nCurrent)
    Status(T("Deleted ", "تم حذف ") + txtName.text())
    cmdClear_Click()
    Refresh()

func cmdClear_Click
    nCurrent = 0
    txtName.setText("")  txtPhone.setText("")  txtEmail.setText("")
    lstContacts.clearSelection()
    txtName.setFocus(0)

func cmdSettings_Click
    ShowSettings()

func mnuFileSettings_Click
    ShowSettings()

func mnuFileExport_Click
    if dlgExport.ShowDialog() = "OK"
        ExportCsv(dlgExport.FileName)
    ok

func mnuFileExit_Click
    Form1.close()

func mnuHelpAbout_Click
    oMsg = new qMessageBox(Form1)
    oMsg.setWindowTitle("About")
    oMsg.setText("Ring Contacts - a RAD IDE example (RingQt + SQLite)." + nl +
                 "(c) 2026 Musoftware - https://musoftwares.com - MIT License")
    oMsg.show()

# ---------------- helpers ----------------

func AddContact cName, cPhone, cEmail
    sqlite_execute(oDB, "insert into contacts (name, phone, email) values (" + Sql(cName) + ", " + Sql(cPhone) +
                        ", " + Sql(cEmail) + ")")

func Refresh
    cWhere = ""
    cFind = trim(txtSearch.text())
    if cFind != ""
        cLike = Sql("%" + cFind + "%")
        cWhere = " where name like " + cLike + " or phone like " + cLike + " or email like " + cLike
    ok
    aRows = sqlite_execute(oDB, "select id, name, phone from contacts" + cWhere + " order by name")
    lstContacts.clear()
    aIds = []
    for aRow in aRows
        lstContacts.addItem(aRow[:name] + "  -  " + aRow[:phone])
        aIds + number(aRow[:id])
    next
    lblCount.setText("" + len(aRows) + T(" contacts", " جهة اتصال"))

func Valid
    if trim(txtName.text()) = ""
        Status(T("The name is required", "الاسم مطلوب"))
        txtName.setFocus(0)
        return false
    ok
    return true

func Sql cText
    return "'" + substr(cText, "'", "''") + "'"           # an SQL string literal

func Status cText
    lblStatus.setText(cText)

func T cEnglish, cArabic
    if cLang = "ar" return cArabic ok
    return cEnglish

func ExportCsv cFile
    cOut = "name,phone,email" + nl
    for aRow in sqlite_execute(oDB, "select name, phone, email from contacts order by name")
        cOut += Csv(aRow[:name]) + "," + Csv(aRow[:phone]) + "," + Csv(aRow[:email]) + nl
    next
    write(cFile, cOut)
    Status(T("Exported to ", "تم التصدير إلى ") + cFile)

func Csv cText
    return '"' + substr(cText, '"', '""') + '"'

# ---- settings.ini: lang=en|ar, confirm=1|0
func LoadSettings
    if not fexists("settings.ini") return ok
    for cLine in str2list(read("settings.ini"))
        cLine = trim(substr(cLine, char(13), ""))
        n = substr(cLine, "=")
        if n > 0
            cKey = lower(trim(left(cLine, n - 1)))  cValue = trim(substr(cLine, n + 1))
            if cKey = "lang" cLang = cValue ok
            if cKey = "confirm" lConfirm = (cValue = "1") ok
        ok
    next

func SaveSettings
    write("settings.ini", "lang=" + cLang + nl + "confirm=" + iif(lConfirm, "1", "0") + nl)

func ApplyLanguage
    if cLang = "ar"
        Form1.setLayoutDirection(1)                     # Qt::RightToLeft - the whole form is mirrored
        Form1.setWindowTitle("جهات الاتصال")
        lblSearch.setText("بحث:")  lblName.setText("الاسم:")  lblPhone.setText("الهاتف:")
        lblEmail.setText("البريد:")
        cmdAdd.setText("إضافة")  cmdUpdate.setText("تعديل")  cmdDelete.setText("حذف")
        cmdClear.setText("مسح")  cmdSettings.setText("الإعدادات...")
    else
        Form1.setLayoutDirection(0)
        Form1.setWindowTitle("Contacts - جهات الاتصال")
        lblSearch.setText("Search:")  lblName.setText("Name:")  lblPhone.setText("Phone:")
        lblEmail.setText("Email:")
        cmdAdd.setText("Add")  cmdUpdate.setText("Update")  cmdDelete.setText("Delete")
        cmdClear.setText("Clear")  cmdSettings.setText("Settings...")
    ok
    Refresh()

func iif lCond, vYes, vNo
    if lCond return vYes ok
    return vNo
