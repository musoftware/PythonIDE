load "Form1_designer.ring"

# Show this form with:  Form1_Show()

# ---------------- Event handlers ----------------

func Form1_Load
    # runs after the form is created

func btnGreet_Click
    cName = txtName.text()
    if chkUpper.isChecked() cName = upper(cName) ok
    lblResult.setText("Hello, " + cName + "!")
    lstLog.addItem(cName)

func Timer1_Tick
    lblClock.setText(time())

func mnuFileClear_Click
    lstLog.clear()

func mnuFileExit_Click
    Form1.close()

func mnuHelpAbout_Click
    oMsg = new qMessageBox(Form1)
    oMsg.setWindowTitle("About")
    oMsg.setText("Made with RAD IDE")
    oMsg.show()

func Button1_Click
     
