# Reports tests

Banded reports (Report Designer, `.rpt.json`) and the **ReportViewer** control.

| Project | Language | What it tests |
| --- | --- | --- |
| `InvoiceReport_Tk` | python-tk | ReportViewer on a Tkinter form: invoices grouped by customer (new page each) and invoice (keep together), subtotals / tax / totals, running totals, Code 128 barcodes, QR code, bar + pie charts, page N of M, parameter `CustomerId` from a TextBox, Export PDF / Excel, Print, a second Arabic right-to-left report |
| `InvoiceReport_Qt` | python-qt (PySide6) | the same form and reports with the Qt ReportViewer (PageChanged event, Ctrl+wheel zoom) |

Data: `shop.db` (SQLite, 5 customers, 14 invoices, 57 lines; Arabic names). `make_db.py` re-creates it.
Reports: `Invoices.rpt.json` (5 pages), `ArabicSales.rpt.json` (Arabic, mirrored RTL layout, 3 pages).

Try it: open a project folder in the IDE, double-click *Reports > Invoices.rpt.json* in Solution Explorer
(Report Designer, *Preview* tab at the bottom), or press F5 to run the form. Type `1` in *Customer Id* and click
*Show* for one customer; *Export PDF* writes `Invoices.pdf` next to the form.
Without the IDE: `python radreport.py Invoices.rpt.json -o out.pdf -p CustomerId=2`.
