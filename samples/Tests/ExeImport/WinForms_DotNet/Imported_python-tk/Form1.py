from Form1_designer import Form1Designer, EventArgs  # noqa: F401
from tkinter import messagebox


class Form1(Form1Designer):
    """Write your event handlers here."""

    # fields of the original form
    count = 0

    def Form1_Load(self):
        self.lblResult.config(text="Ready")

    def exitToolStripMenuItem_Click(self):
        self.root.destroy()

    def btnGreet_Click(self):
        text = self.txtName_var.get().strip()
        if text == "":
            messagebox.showinfo("Hello", "Please type a name")
            return
        if self.chkUpper_var.get():
            text = text.upper()
        self.count += 1
        self.lblResult.config(text="Hello, " + text + "! (" + str(self.count) + ")")
        self.lstLog.insert("end", text)
        messagebox.showinfo("Greeting", "Hello, " + text + "!")

    def lstLog_DoubleClick(self):
        if (self.lstLog.curselection()[0] if self.lstLog.curselection() else -1) >= 0:
            self.txtName_var.set(str((self.lstLog.get(self.lstLog.curselection()[0]) if self.lstLog.curselection() else None)))
        for i in range(3):
            self.count += i


if __name__ == "__main__":
    Form1().show()
