# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Inventory - a PySide6 stock list on SQLite with a modal Add / Edit dialog (a second form of the project).

Shows: a DataGridView (QTableWidget) filled from SQLite (InventoryDb.py), search as you type, a "low stock"
filter with highlighted rows, Add / Edit (double-click a row) in the modal frmItem dialog with validation,
Delete with a confirmation, totals, CSV export through a SaveFileDialog and menu + button handlers.
"""
import csv
import sys

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidgetItem  # noqa: F401

from frmInventory_designer import frmInventoryDesigner, EventArgs  # noqa: F401
from frmItem import frmItem  # show with: self.f2 = frmItem(); self.f2.show()
import InventoryDb

COLUMNS = ["Id", "SKU", "Name", "Category", "Qty", "Price"]


class frmInventory(frmInventoryDesigner):
    """Event handlers of the inventory window."""

    def frmInventory_Load(self):
        self.db = InventoryDb.Inventory()
        self.grdItems.setColumnHidden(0, True)                 # the key stays hidden
        self.grdItems.setSelectionBehavior(self.grdItems.SelectionBehavior.SelectRows)
        self.grdItems.setSelectionMode(self.grdItems.SelectionMode.SingleSelection)
        self.grdItems.cellDoubleClicked.connect(lambda *_: self.btnEdit_Click())
        self.txtSearch.textChanged.connect(lambda _t: self.refresh())
        self.chkLowStock.toggled.connect(lambda _c: self.refresh())
        self.refresh()

    # ------------------------------------------------------------------ list
    def refresh(self, select_id=None):
        rows = self.db.items(self.txtSearch.text().strip(), self.chkLowStock.isChecked())
        g = self.grdItems
        g.setRowCount(len(rows))
        for r, item in enumerate(rows):
            for c, col in enumerate(COLUMNS):
                v = item[col]
                cell = QTableWidgetItem(f"{v:.2f}" if col == "Price" else str(v))
                if item["Qty"] < InventoryDb.LOW_STOCK:
                    cell.setBackground(QColor("#FFE3E3"))
                g.setItem(r, c, cell)
            if item["Id"] == select_id:
                g.selectRow(r)
        n, qty, value = self.db.totals()
        self.lblTotal.setText(f"{n} items in stock   |   {qty} units   |   value {value:,.2f}")
        self.sbInfo.setText(f"{len(rows)} shown" + ("  (low stock only)" if self.chkLowStock.isChecked() else ""))

    def selected_id(self):
        r = self.grdItems.currentRow()
        if r < 0 or self.grdItems.item(r, 0) is None:
            return None
        return int(self.grdItems.item(r, 0).text())

    # ------------------------------------------------------------------ add / edit / delete
    def btnAdd_Click(self):
        values = frmItem.ShowDialog(self, None, check_sku=lambda sku: self.db.sku_taken(sku))
        if values:
            new_id = self.db.add(values)
            self.refresh(new_id)
            self.sbInfo.setText(f"Added {values['SKU']}")

    def btnEdit_Click(self):
        item_id = self.selected_id()
        if item_id is None:
            self.sbInfo.setText("Select an item first")
            return
        item = self.db.get(item_id)
        values = frmItem.ShowDialog(self, item, check_sku=lambda sku: self.db.sku_taken(sku, item_id))
        if values:
            self.db.update(item_id, values)
            self.refresh(item_id)
            self.sbInfo.setText(f"Saved {values['SKU']}")

    def btnDelete_Click(self):
        item_id = self.selected_id()
        if item_id is None:
            return
        item = self.db.get(item_id)
        r = QMessageBox.question(self, "Inventory", f"Delete {item['SKU']} - {item['Name']}?")
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete(item_id)
            self.refresh()

    def mnuItemAdd_Click(self):
        self.btnAdd_Click()

    def mnuItemEdit_Click(self):
        self.btnEdit_Click()

    def mnuItemDelete_Click(self):
        self.btnDelete_Click()

    # ------------------------------------------------------------------ export / exit
    def mnuFileExport_Click(self):
        if self.dlgExport.ShowDialog() != "OK":
            return
        rows = self.db.items(self.txtSearch.text().strip(), self.chkLowStock.isChecked())
        with open(self.dlgExport.FileName, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
        self.sbInfo.setText(f"Exported {len(rows)} items")

    def mnuFileExit_Click(self):
        self.close()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = frmInventory()
    form.show()
    sys.exit(app.exec())
