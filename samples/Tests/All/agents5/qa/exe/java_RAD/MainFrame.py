from MainFrame_designer import MainFrameDesigner, EventArgs  # noqa: F401
from tkinter import messagebox


class MainFrame(MainFrameDesigner):
    """Write your event handlers here."""

    # fields of the original form
    count = 0

    def MainFrame_Load(self):
        pass

    def btnGreet_Click(self):
        var1 = self.txtName_var.get().strip()
        if len(var1) == 0:
            messagebox.showinfo("", "Please type a name")
        else:
            if self.chkUpper_var.get():
                var1 = var1.upper()
            self.count += 1
            self.lblResult.config(text="Hello, " + var1 + "! (" + str(self.count) + ")")


if __name__ == "__main__":
    MainFrame().show()
