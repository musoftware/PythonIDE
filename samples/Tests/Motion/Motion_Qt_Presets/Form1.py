import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Same animations as Motion_Tk_Presets; on Qt the fades are real transparency."""

    def btnHide_Click(self):
        self._hidden = not getattr(self, "_hidden", False)
        self.SetVisible("lblInfo", not self._hidden)

    def lblTitle_Click(self):
        self.Animate("lblTitle", "pulse", durationMs=500)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
