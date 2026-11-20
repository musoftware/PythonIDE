from frmAboutGreeter_designer import frmAboutGreeterDesigner, EventArgs  # noqa: F401


class frmAboutGreeter(frmAboutGreeterDesigner):
    """Write your event handlers here."""

    def frmAboutGreeter_Load(self):
        pass

    def btnOK_Click(self):
        self.root.destroy()


if __name__ == "__main__":
    frmAboutGreeter().show()
