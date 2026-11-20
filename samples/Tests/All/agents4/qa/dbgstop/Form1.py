from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        nX = 42
        print('load', nX)

    def btnGreet_Click(self):
        name = self.txtName_var.get()
        if self.chkUpper_var.get():
            name = name.upper()
        self.lblResult.config(text=f"Hello, {name}!")
        self.lstLog.insert("end", name)

    def Timer1_Tick(self):
        import time
        self.lblClock.config(text=time.strftime("%H:%M:%S"))

    def mnuFileClear_Click(self):
        self.lstLog.delete(0, "end")

    def mnuFileExit_Click(self):
        self.root.destroy()

    def mnuHelpAbout_Click(self):
        from tkinter import messagebox
        messagebox.showinfo("About", "Made with RAD IDE")


if __name__ == "__main__":
    Form1().show()
