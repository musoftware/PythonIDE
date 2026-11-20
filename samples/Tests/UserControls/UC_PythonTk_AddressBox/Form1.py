from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """Write your event handlers here."""

    def Form1_Load(self):
        pass

    def HomeAddress_Changed(self):
        self.lblLog.configure(text='HomeAddress changed' + ": " + self.HomeAddress.Street + " (" + str(self.HomeAddress.Changes) + " edits)")

    def WorkAddress_Changed(self):
        self.lblLog.configure(text='WorkAddress changed: ' + self.WorkAddress.Street)

    def Emergency_Edited(self):
        self.lblLog.configure(text='Emergency card edited: ' + self.Emergency.Address.Street)

    def btnShow_Click(self):
        self.lblLog.configure(text="Home: " + self.HomeAddress.Street + " | Work: " + self.WorkAddress.Street + " | " + self.Emergency.ContactName)

    def btnCopy_Click(self):
        self.WorkAddress.Street = self.HomeAddress.Street


if __name__ == "__main__":
    Form1().show()
