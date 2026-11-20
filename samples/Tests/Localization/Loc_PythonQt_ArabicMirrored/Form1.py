import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        self.lblStatus.setText("Language: " + (self.CurrentLanguage or "default (English)"))

    def btnSwitch_Click(self):
        order = ["", "ar", "fr"]
        nxt = order[(order.index(self.CurrentLanguage) + 1) % 3] if self.CurrentLanguage in order else ""
        self.ApplyLanguage(nxt)          # switch the whole form (and its user controls) live
        self.Form1_Load()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
