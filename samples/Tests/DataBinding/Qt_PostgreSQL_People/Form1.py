import sys

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from Form1_designer import Form1Designer, EventArgs  # noqa: F401


class Form1(Form1Designer):
    """people lives on the IDE's local server; F5 from the IDE passes the password (RADIDE_DB_LOCALDB_PASSWORD)."""

    def btnReload_Click(self):
        self.People.Fill()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = Form1()
    form.show()
    sys.exit(app.exec())
