"""Contact Book - a PySide6 app whose windows are designed in Qt Designer (.ui files loaded at run time)."""
import sys
from pathlib import Path

from PySide6.QtCore import QFile, QMetaObject
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow

HERE = Path(__file__).resolve().parent


def load_ui(name, parent=None):
    f = QFile(str(HERE / name))
    f.open(QFile.ReadOnly)
    w = QUiLoader().load(f, parent)
    f.close()
    return w


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = load_ui("mainwindow.ui")
        self.setCentralWidget(self.ui)
        self.setWindowTitle(self.ui.windowTitle())
        self.ui.addButton.clicked.connect(self.add_contact)
        QMetaObject.connectSlotsByName(self)

    def add_contact(self):
        name = self.ui.nameEdit.text().strip()
        if name:
            self.ui.contactList.addItem(f"{name} <{self.ui.emailEdit.text()}>")
            self.ui.nameEdit.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    if "--smoke" in sys.argv:
        print("contact book started:", w.windowTitle())
        sys.exit(0)
    sys.exit(app.exec())
