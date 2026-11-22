"""User actions replayed on the native exe (Win32 messages) and on the IDE's VB runtime (vbrun, in-process
Tk); the Debug.Print lines and the texts read back must be the same.

Steps:  ("set", ctl, text)  ("click", ctl)  ("select", ctl, index)  ("menu", item)  ("wait", seconds)
        ("read", ctl)  ("modal", ctl, [steps on the modal form])   ctl = "Name", "Arr(1)" or "Form2.Name"
"""

SCENARIOS = {
    "HelloVB": [
        ("set", "txtName", "Ann"), ("click", "btnGreet"), ("read", "lblResult"),
        ("click", "chkUpper"), ("click", "btnGreet"), ("read", "lblResult"),
        ("menu", "mnuFileClear"), ("set", "txtName", "Zed"), ("click", "btnGreet"), ("read", "lblResult"),
    ],
    "ControlsGallery": [
        ("set", "txtName", "Ann"), ("read", "lblStatus"), ("click", "cmdHello"), ("read", "staMain"),
        ("click", "chkBold"), ("click", "chkBold"), ("click", "optLarge"), ("click", "optSmall"),
        ("click", "optRed"), ("select", "cboFruit", 1), ("read", "cboFruit"),
        ("click", "cmdNum(1)"), ("read", "cmdNum(1)"), ("click", "cmdNum(2)"),
        ("click", "cmdColor"), ("click", "cmdColor"), ("menu", "mnuCheck"), ("menu", "mnuCheck"),
        ("click", "cmdPage2"), ("menu", "mnuClear"), ("wait", 1.5), ("read", "lstLog"),
    ],
    "MultiForm": [
        ("set", "txtName", "Lina"),
        ("modal", "cmdAsk", [("read", "Form2.lblQ"), ("set", "Form2.txtAnswer", "green"), ("click", "Form2.cmdOK")]),
        ("read", "lblResult"),
        ("modal", "cmdAsk", [("click", "Form2.cmdCancel")]),
        ("read", "lblResult"),
    ],
    "ArabicForm": [
        ("click", "cmdGreet"), ("read", "lblOut"), ("set", "txtName", "سارة"), ("click", "cmdGreet"),
        ("read", "lblOut"), ("click", "cmdN(2)"), ("read", "lblOut"),
    ],
    "VB_Form": [
        ("set", "txtYourName", "Omar"), ("click", "btnGreet"), ("read", "lbl1003"),
    ],
    "BASIC_Form": None,          # filled in by the test from the project's controls (first button)
}
