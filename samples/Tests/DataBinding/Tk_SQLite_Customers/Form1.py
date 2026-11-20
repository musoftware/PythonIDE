from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Customers is filled when the form opens (Data Sources window: Fill when the form opens).
    The navigator's Save button calls Customers.Update(); double-click a cell to edit it."""

    def Form1_Load(self):
        self.cboSort.current(0)
        self.Customers_PositionChanged()

    def Customers_PositionChanged(self):
        cur = self.Customers.Current
        name = cur["Name"] if cur is not None else "-"
        changes = " - unsaved changes" if self.Customers.HasChanges else ""
        self.stsInfo.config(text=f"{self.Customers.Count} customers, current: {name}{changes}")

    def txtSearch_TextChanged(self):
        self.Customers.Search(self.txtSearch_var.get(), "Name", "Email", "City")

    def cboSort_SelectedIndexChanged(self):
        col = self.cboSort_var.get()
        self.Customers.SortBy("" if col == "(none)" else col)

    def btnCairo_Click(self):
        self.Customers.Fill("City = ?", "Cairo")

    def btnAll_Click(self):
        self.Customers.Fill()

    def Form1_FormClosing(self, e):
        if self.Customers.HasChanges:
            from tkinter import messagebox
            if messagebox.askyesno("Customers", "Save the changes?", parent=self.root):
                self.Customers.Update()


if __name__ == "__main__":
    Form1().show()
