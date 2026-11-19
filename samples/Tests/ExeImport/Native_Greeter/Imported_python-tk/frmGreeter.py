from frmGreeter_designer import frmGreeterDesigner, EventArgs  # noqa: F401
from frmAboutGreeter import frmAboutGreeter  # show with: frmAboutGreeter(master=self.root)


class frmGreeter(frmGreeterDesigner):
    """Write your event handlers here."""

    def frmGreeter_Load(self):
        self.lblResult.config(text='Type a name and press Greet')

    def mnuHelpAbout_Click(self):
        from tkinter import messagebox
        messagebox.showinfo('About Greeter', 'Greeter 1.0 - made with MinGW')

    def btnGreet_Click(self):
        your_name = self.txtYourName_var.get()
        text = 'Hello, %s!' % (your_name,)
        self.lblResult.config(text=text)
        self.lstItems.insert('end', your_name)

    def mnuFileExit_Click(self):
        self.root.destroy()

    def btnClose_Click(self):
        self.root.destroy()

    def mnuFileClear_Click(self):
        self.lstItems.delete(0, 'end')


if __name__ == "__main__":
    frmGreeter().show()
