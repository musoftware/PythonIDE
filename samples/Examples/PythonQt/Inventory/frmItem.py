# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""frmItem - the modal Add / Edit dialog of the Inventory sample.

    values = frmItem.ShowDialog(owner, item=None, check_sku=None)   # dict, or None when cancelled

The form is a normal RAD IDE form (designed in the designer); ShowDialog makes it application-modal and waits
in a local event loop until OK (after validation) or Cancel / the close box."""
import sys

from PySide6.QtCore import QEventLoop, Qt
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from frmItem_designer import frmItemDesigner, EventArgs  # noqa: F401


class frmItem(frmItemDesigner):
    """Event handlers of the item dialog."""

    def frmItem_Load(self):
        self.btnOK.setDefault(True)

    @classmethod
    def ShowDialog(cls, owner=None, item=None, check_sku=None):
        dlg = cls(owner)
        dlg.setWindowFlag(Qt.WindowType.Dialog, True)
        dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
        dlg.result, dlg.check_sku = None, check_sku
        dlg.setWindowTitle("Edit item" if item else "Add item")
        if item:
            dlg.txtSku.setText(item["SKU"])
            dlg.txtName.setText(item["Name"])
            dlg.cboCategory.setCurrentText(item.get("Category") or "Other")
            dlg.numQty.setValue(int(item["Qty"]))
            dlg.txtPrice.setText(f"{float(item['Price']):.2f}")
        dlg._loop = QEventLoop()
        dlg.show()
        dlg._loop.exec()                       # returns when the dialog closes (frmItem_FormClosed)
        return dlg.result

    def values(self) -> tuple[dict | None, str]:
        sku, name = self.txtSku.text().strip().upper(), self.txtName.text().strip()
        if not sku or not name:
            return None, "SKU and Name are required."
        try:
            price = round(float(self.txtPrice.text().replace(",", ".")), 2)
        except ValueError:
            return None, "Price must be a number, e.g. 12.50"
        if price < 0:
            return None, "Price cannot be negative."
        if self.check_sku and self.check_sku(sku):
            return None, f"SKU {sku} is already used by another item."
        return {"SKU": sku, "Name": name, "Category": self.cboCategory.currentText() or "Other",
                "Qty": self.numQty.value(), "Price": price}, ""

    def btnOK_Click(self):
        values, error = self.values()
        self.lblError.setText(error)
        if values is not None:
            self.result = values
            self.close()

    def btnCancel_Click(self):
        self.result = None
        self.close()

    def frmItem_FormClosed(self):
        loop = getattr(self, "_loop", None)
        if loop is not None:
            loop.quit()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    print(frmItem.ShowDialog())
