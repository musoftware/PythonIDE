import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from frmAboutGreeter_designer import frmAboutGreeterDesigner, EventArgs  # noqa: F401


class frmAboutGreeter(frmAboutGreeterDesigner):
    """Write your event handlers here."""

    def frmAboutGreeter_Load(self):
        pass

    def btnOK_Click(self):
        self.close()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = frmAboutGreeter()
    form.show()
    sys.exit(app.exec())
