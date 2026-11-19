import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from frmGreeter_designer import frmGreeterDesigner, EventArgs  # noqa: F401
from frmAboutGreeter import frmAboutGreeter  # show with: self.f2 = frmAboutGreeter(); self.f2.show()


class frmGreeter(frmGreeterDesigner):
    """Write your event handlers here."""

    def frmGreeter_Load(self):
        self.lbl1003.setText('Type a name and press Greet')

    def mnuHelpAbout_Click(self):
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(self, 'About Greeter', 'Greeter 1.0 - made with MinGW')

    def btnGreet_Click(self):
        your_name = self.txtYourName.text()
        text = 'Hello, %s!' % (your_name,)
        self.lbl1003.setText(text)
        self.lst1005.addItem(your_name)

    def mnuFileExit_Click(self):
        self.close()

    def btnClose_Click(self):
        self.close()

    def mnuFileClear_Click(self):
        self.lst1005.clear()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = frmGreeter()
    form.show()
    sys.exit(app.exec())
