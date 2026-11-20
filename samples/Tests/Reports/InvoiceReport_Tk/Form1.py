from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Invoices report: pick a customer (empty = all), Show, Export PDF / Excel, Print, Arabic report."""

    def _status(self, text):
        self.Status.config(text=text)

    def Form1_Load(self):
        self._status("{n} page(s) - PageUp / PageDown, Ctrl+wheel zooms (Qt)".format(n=self.ReportViewer1.PageCount))

    def btnShow_Click(self):
        text = self.txtCustomer_var.get().strip()
        self.ReportViewer1.Parameters["CustomerId"] = int(text) if text.isdigit() else None
        self.ReportViewer1.Refresh()
        self._status(f"{self.ReportViewer1.PageCount} page(s)")

    def btnPdf_Click(self):
        path = self.ReportViewer1.ExportPdf(self._res("Invoices.pdf"))
        self._status("Saved " + path)

    def btnExcel_Click(self):
        path = self.ReportViewer1.ExportExcel(self._res("Invoices.xlsx"))
        self._status("Saved " + path)

    def btnPrint_Click(self):
        self.ReportViewer1.Print()

    def btnArabic_Click(self):
        self.ReportViewer1.LoadReport(self._res("ArabicSales.rpt.json"))
        self._status(f"{self.ReportViewer1.PageCount} page(s)")

    def ReportViewer1_PageChanged(self):
        self._status(f"Page {self.ReportViewer1.Page} of {self.ReportViewer1.PageCount}")


if __name__ == "__main__":
    Form1().show()
