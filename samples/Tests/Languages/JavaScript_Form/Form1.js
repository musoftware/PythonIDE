// Event handlers for Form1. A handler is a function named <Control>_<Event>(e).
// Controls: get("txtA", "Text"), set("lblOut", "Caption", x), call("lstLog", "AddItem", x)
//   or ui.txtA.Text, ui.lblOut.Caption = x, ui.lstLog.AddItem(x). Also msgbox, input, end.
// Other modules: radcall("Module.func", ...args). npm packages: require("name").

function Form1_Load(e) {
    // runs when the form is shown
}
    // (python-tk) self.lblResult.config(text="Ready")
    // pass
function exitToolStripMenuItem_Click(e) {
    // (python-tk) self.root.destroy()
    // pass
}

function btnGreet_Click(e) {
    // (python-tk) text = self.txtName_var.get().strip()
    // (python-tk) if text == "":
    // (python-tk)     messagebox.showinfo("Hello", "Please type a name")
    // (python-tk)     return
    // (python-tk) if self.chkUpper_var.get():
    // (python-tk)     text = text.upper()
    // (python-tk) self.count += 1
    // (python-tk) self.lblResult.config(text="Hello, " + text + "! (" + str(self.count) + ")")
    // (python-tk) self.lstLog.insert("end", text)
    // (python-tk) messagebox.showinfo("Greeting", "Hello, " + text + "!")
    // pass
}

function lstLog_DoubleClick(e) {
    // (python-tk) if (self.lstLog.curselection()[0] if self.lstLog.curselection() else -1) >= 0:
    // (python-tk)     self.txtName_var.set(str((self.lstLog.get(self.lstLog.curselection()[0]) if self.lstLog.curselection() else None)))
    // (python-tk) for i in range(3):
    // (python-tk)     self.count += i
    // pass
}
