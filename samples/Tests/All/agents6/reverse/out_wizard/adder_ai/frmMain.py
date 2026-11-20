from frmMain_designer import frmMainDesigner, EventArgs  # noqa: F401


class frmMain(frmMainDesigner):
    """Write your event handlers here."""

    def frmMain_Load(self):
        pass

    def btnAdd_Click(self):
        first_number = self.txtFirstNumber_var.get()
        second_number = self.txtSecondNumber_var.get()
        text = 'Sum = %d' % (int(first_number) + int(second_number),)
        self.lblResult.config(text=text)


if __name__ == "__main__":
    frmMain().show()
