import sys

from PySide6.QtWidgets import QApplication

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """One design, three sizes (Phone / Tablet / Tabletop) made with Edit: This size only in the designer.
    Resize the window: the layout switches at 600 and 1024 pixels."""

    def Form1_Load(self):
        self.changes = 0
        self.lblStatus.setText(f"Sizes: {self.CurrentSizes or ['(designed size)']}")

    def Form1_SizeVariantChanged(self):
        self.changes = getattr(self, "changes", 0) + 1
        self.lblStatus.setText(f"Sizes: {self.CurrentSizes or ['(designed size)']}")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
