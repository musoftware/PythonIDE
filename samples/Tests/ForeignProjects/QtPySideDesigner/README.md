# QtPySideDesigner - foreign project test (Qt Designer .ui + PySide6)

`mainwindow.ui` (QMainWindow with nested layouts: QVBoxLayout > QGroupBox/QFormLayout, a QHBoxLayout with a
spacer, menu bar, actions, tab stops, buddies, connections) and `aboutdialog.ui` (absolute positions, a
custom widget `FancyLine`, an XML comment), loaded at run time by `main.py` (QUiLoader); `ContactBook.pyproject`
is the pyside6-project file.

Open `ContactBook.pyproject`, a `.ui` file or the folder: the forms open in the designer (widgets in layouts
show at their real positions and keep their layout); saving writes ONLY the changed spans back into the .ui
(open + save without changes = byte-identical). Targets: `main.py` and `Preview <form>.ui`.
