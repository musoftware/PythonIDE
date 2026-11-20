Option Explicit

Private Sub Form_Load()
    ' (python-tk) self.lblResult.config(text="Ready")
    ' (Python) pass
End Sub

Private Sub exitToolStripMenuItem_Click()
    ' (python-tk) self.root.destroy()
    ' (Python) pass
End Sub

Private Sub btnGreet_Click()
    ' (python-tk) text = self.txtName_var.get().strip()
    ' (python-tk) if text == "":
    ' (python-tk)     messagebox.showinfo("Hello", "Please type a name")
    ' (python-tk)     return
    ' (python-tk) if self.chkUpper_var.get():
    ' (python-tk)     text = text.upper()
    ' (python-tk) self.count += 1
    ' (python-tk) self.lblResult.config(text="Hello, " + text + "! (" + str(self.count) + ")")
    ' (python-tk) self.lstLog.insert("end", text)
    ' (python-tk) messagebox.showinfo("Greeting", "Hello, " + text + "!")
    ' (Python) pass
End Sub

Private Sub lstLog_DblClick()
    ' (python-tk) if (self.lstLog.curselection()[0] if self.lstLog.curselection() else -1) >= 0:
    ' (python-tk)     self.txtName_var.set(str((self.lstLog.get(self.lstLog.curselection()[0]) if self.lstLog.curselection() else None)))
    ' (python-tk) for i in range(3):
    ' (python-tk)     self.count += i
    ' (Python) pass
End Sub
