import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Products (details + grid share one BindingSource) and Categories (a lookup ComboBox and a ListBox)."""

    def Form1_Load(self):
        self.Products_PositionChanged()

    def Products_PositionChanged(self):
        p = self.Products.Current
        if p is None:
            self.lblInfo.setText("No product")
            return
        i = self.Categories.Find("Id", p["CategoryId"])
        cat = self.Categories.Item(i)["Name"] if i >= 0 else "?"
        self.lblInfo.setText(f"{p['Name']} - category {cat} - {self.Products.Count} products")

    def btnSaveAll_Click(self):
        try:
            n = self.UpdateAll()
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "Save", str(e))
            return
        QMessageBox.information(self, "Save", f"{n} row(s) saved.")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
