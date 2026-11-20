import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        # (python-tk) self.lblResult.config(text="Ready")
        pass

    def exitToolStripMenuItem_Click(self):
        # (python-tk) self.root.destroy()
        pass

    def btnGreet_Click(self):
        # (python-tk) text = self.txtName_var.get().strip()
        # (python-tk) if text == "":
        # (python-tk)     messagebox.showinfo("Hello", "Please type a name")
        # (python-tk)     return
        # (python-tk) if self.chkUpper_var.get():
        # (python-tk)     text = text.upper()
        # (python-tk) self.count += 1
        # (python-tk) self.lblResult.config(text="Hello, " + text + "! (" + str(self.count) + ")")
        # (python-tk) self.lstLog.insert("end", text)
        # (python-tk) messagebox.showinfo("Greeting", "Hello, " + text + "!")
        pass

    def lstLog_DoubleClick(self):
        # (python-tk) if (self.lstLog.curselection()[0] if self.lstLog.curselection() else -1) >= 0:
        # (python-tk)     self.txtName_var.set(str((self.lstLog.get(self.lstLog.curselection()[0]) if self.lstLog.curselection() else None)))
        # (python-tk) for i in range(3):
        # (python-tk)     self.count += i
        pass


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
