from MainForm_designer import MainFormDesigner, EventArgs  # noqa: F401


class MainForm(MainFormDesigner):
    """Write your event handlers here."""

    def MainForm_Load(self):
        nX = 42
        print("load done", nX)

    def btnHello_Click(self):
        pass

    def mnuFileExit_Click(self):
        pass

    def Timer1_Tick(self):
        pass


if __name__ == "__main__":
    MainForm().show()
