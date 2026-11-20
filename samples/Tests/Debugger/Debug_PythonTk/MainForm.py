from MainForm_designer import MainFormDesigner, EventArgs  # noqa: F401


class MainForm(MainFormDesigner):
    """Write your event handlers here."""

    def MainForm_Load(self):
        nX = 42
        print("load done", nX)

    def btnHello_Click(self):
        total = 0
        for i in range(10):
            total += i * i          # conditional breakpoint here: i == 5
        print("sum of squares", total)

    def mnuFileExit_Click(self):
        pass

    def Timer1_Tick(self):
        pass


if __name__ == "__main__":
    MainForm().show()
