import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from ContactCard_designer import ContactCardDesigner, EventArgs  # noqa: F401


class ContactCard(ContactCardDesigner):
    """User control: write its event handlers here.
    Raise its own events with self.RaiseEvent("EventName") - the form that hosts it
    gets <instance>_EventName(). Custom properties are declared in the designer
    (Project > User Control Properties and Events)."""

    def ContactCard_Load(self):
        pass

    def Address_Changed(self):
        self.RaiseEvent("Edited")


if __name__ == "__main__":      # test the user control alone
    app = QApplication.instance() or QApplication(sys.argv)
    uc = ContactCard()
    uc.show()
    sys.exit(app.exec())
