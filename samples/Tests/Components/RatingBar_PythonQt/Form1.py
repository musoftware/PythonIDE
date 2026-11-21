import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        pass

    def rateFood_ValueChanged(self):
        self.lblResult.setText("Food %d/%d - Service %d/%d" % (self.rateFood.Value, self.rateFood.MaxStars, self.rateService.Value, self.rateService.MaxStars))

    def rateService_ValueChanged(self):
        self.lblResult.setText("Food %d/%d - Service %d/%d" % (self.rateFood.Value, self.rateFood.MaxStars, self.rateService.Value, self.rateService.MaxStars))

    def btnReset_Click(self):
        self.rateFood.Reset()
        self.rateService.SetValue(1)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
