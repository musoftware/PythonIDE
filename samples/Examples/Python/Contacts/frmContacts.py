# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Contacts - a SQLite address book bound with the IDE's Data Sources window (VB 2005 style data binding).

The form has a data source "Contacts" (connection ContactsDb -> contacts.db, table Contacts).  The IDE generated
the BindingNavigator (|< < "1 of 5" > >|) and the DataGridView when the table was dropped on the form; the
TextBoxes / CheckBox in the "Contact" box are bound to columns (DataSource = Contacts, DataMember = Name ...).

This code adds: New / Save / Delete with validation (Validation.py), search as you type (Contacts.Search),
a city filter that runs a parameterized SQL query (Contacts.Fill("City = ?", city)), CSV export with a
SaveFileDialog and a status bar that follows the current record (Contacts_PositionChanged).
"""
from tkinter import messagebox

from frmContacts_designer import frmContactsDesigner, EventArgs  # noqa: F401
import Validation

ALL = "(all cities)"


class frmContacts(frmContactsDesigner):
    """Event handlers of the Contacts window."""

    def frmContacts_Load(self):
        self.fill_cities()
        self.cboCity.set(ALL)
        self.Contacts_PositionChanged()

    # ------------------------------------------------------------------ data source events
    def Contacts_PositionChanged(self):
        """Raised by the data source when the current record or the list changes."""
        cur = self.Contacts.Current
        who = cur["Name"] if cur is not None else "-"
        pending = "  (unsaved changes)" if self.Contacts.HasChanges else ""
        self.sbInfo.config(text=f"{self.Contacts.Count} contacts    current: {who}{pending}")
        self.lblError.config(text="")

    def fill_cities(self):
        rows = self.ContactsDbConnection.Query(
            "SELECT DISTINCT City FROM Contacts WHERE City <> '' ORDER BY City")
        self.cboCity.configure(values=[ALL] + [r["City"] for r in rows])

    # ------------------------------------------------------------------ search / filter
    def txtSearch_TextChanged(self):
        self.Contacts.Search(self.txtSearch_var.get(), "Name", "Phone", "Email", "City")

    def cboCity_SelectedIndexChanged(self):
        city = self.cboCity_var.get()
        if self.Contacts.HasChanges and not self.ask_save():
            return
        if city == ALL:
            self.Contacts.Fill()
        else:
            self.Contacts.Fill("City = ?", city)          # parameterized: no SQL injection

    # ------------------------------------------------------------------ editing
    def btnNew_Click(self):
        city = self.cboCity_var.get()
        self.Contacts.AddNew(City="" if city == ALL else city)
        self.txtName.focus_set()

    def btnSave_Click(self):
        """Validate what is typed, then write every change to contacts.db (one transaction)."""
        problems = Validation.check_contact(self.txtName_var.get(), self.txtPhone_var.get(),
                                            self.txtEmail_var.get())
        if problems:
            self.lblError.config(text="\n".join(problems))
            self.root.bell()
            return False
        self.Contacts.EndEdit()
        saved = self.Contacts.Update()
        self.fill_cities()
        self.Contacts_PositionChanged()
        self.sbInfo.config(text=self.sbInfo.cget("text") + f"    saved {saved} change(s)")
        return True

    def btnDelete_Click(self):
        cur = self.Contacts.Current
        if cur is None:
            return
        if messagebox.askyesno("Contacts", f"Delete {cur['Name'] or 'this contact'}?", parent=self.root):
            self.Contacts.RemoveCurrent()
            self.Contacts.Update()
            self.fill_cities()

    def ask_save(self) -> bool:
        answer = messagebox.askyesnocancel("Contacts", "Save the changes first?", parent=self.root)
        if answer is None:
            return False
        if answer:
            return self.btnSave_Click()
        self.Contacts.RejectChanges()
        return True

    # ------------------------------------------------------------------ export
    def btnExport_Click(self):
        if self.dlgExport.ShowDialog() != "OK":
            return
        cols = self.Contacts.Columns
        with open(self.dlgExport.FileName, "w", encoding="utf-8-sig", newline="") as f:
            f.write(Validation.csv_line(cols) + "\r\n")
            for row in self.Contacts.Rows:                 # the rows shown (search / filter applied)
                f.write(Validation.csv_line(row[c] for c in cols) + "\r\n")
        self.sbInfo.config(text=f"Exported {self.Contacts.Count} contacts to {self.dlgExport.FileName}")

    def frmContacts_FormClosing(self, e):
        if self.Contacts.HasChanges and not self.ask_save():
            e.Cancel = True


if __name__ == "__main__":
    frmContacts().show()
