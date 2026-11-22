# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Qt Text Editor - a PySide6 editor designed in RAD IDE (python-qt).

Shows: MenuStrip -> QMenuBar/QAction handlers, Open/Save file dialogs, the Qt clipboard (cut / copy / paste,
undo / redo), Find Next and Replace All with a find bar, zoom, a right-to-left switch for Arabic text,
a status bar with line / column / word count and an "unsaved changes" question when closing (FormClosing).
"""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401

from frmEditor_designer import frmEditorDesigner, EventArgs  # noqa: F401

APP = "Qt Text Editor"


class frmEditor(frmEditorDesigner):
    """Event handlers of the editor window."""

    def frmEditor_Load(self):
        self.path = ""
        self.txtEdit.document().setModified(False)
        self.txtEdit.textChanged.connect(self.update_ui)
        self.txtEdit.cursorPositionChanged.connect(self.update_ui)
        self.txtFind.returnPressed.connect(self.btnFind_Click)
        for act, keys in ((self.mnuFileNew, "Ctrl+N"), (self.mnuFileOpen, "Ctrl+O"), (self.mnuFileSave, "Ctrl+S"),
                          (self.mnuEditUndo, "Ctrl+Z"), (self.mnuEditRedo, "Ctrl+Y"), (self.mnuEditCut, "Ctrl+X"),
                          (self.mnuEditCopy, "Ctrl+C"), (self.mnuEditPaste, "Ctrl+V"),
                          (self.mnuViewZoomIn, "Ctrl++"), (self.mnuViewZoomOut, "Ctrl+-")):
            act.setShortcut(keys)
        self.mnuViewRtl.setCheckable(True)
        self.update_ui()

    # ------------------------------------------------------------------ helpers
    def text(self) -> str:
        return self.txtEdit.toPlainText()

    @property
    def dirty(self) -> bool:
        return self.txtEdit.document().isModified()

    def update_ui(self):
        name = os.path.basename(self.path) if self.path else "Untitled"
        self.setWindowTitle(f"{'*' if self.dirty else ''}{name} - {APP}")
        cur = self.txtEdit.textCursor()
        text = self.text()
        self.sbStatus.setText(f"Ln {cur.blockNumber() + 1}, Col {cur.positionInBlock() + 1}    "
                              f"{len(text.split())} words    {len(text)} characters")

    def message(self, text: str):
        self.sbStatus.setText(text)

    def confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        r = QMessageBox.question(self, APP, "Save the changes?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No |
                                 QMessageBox.StandardButton.Cancel)
        if r == QMessageBox.StandardButton.Cancel:
            return False
        return self.save() if r == QMessageBox.StandardButton.Yes else True

    def load(self, path: str):
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            self.txtEdit.setPlainText(f.read())
        self.path = path
        self.txtEdit.document().setModified(False)
        self.update_ui()
        self.message(f"Opened {path}")

    def save(self, path: str = "") -> bool:
        path = path or self.path
        if not path:
            if self.dlgSave.ShowDialog() != "OK":
                return False
            path = self.dlgSave.FileName
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(self.text())
        self.path = path
        self.txtEdit.document().setModified(False)
        self.update_ui()
        self.message(f"Saved {path}")
        return True

    # ------------------------------------------------------------------ File
    def mnuFileNew_Click(self):
        if self.confirm_discard():
            self.path = ""
            self.txtEdit.clear()
            self.txtEdit.document().setModified(False)
            self.update_ui()

    def mnuFileOpen_Click(self):
        if self.confirm_discard() and self.dlgOpen.ShowDialog() == "OK":
            self.load(self.dlgOpen.FileName)

    def mnuFileSave_Click(self):
        self.save()

    def mnuFileSaveAs_Click(self):
        self.dlgSave.FileName = self.path
        if self.dlgSave.ShowDialog() == "OK":
            self.save(self.dlgSave.FileName)

    def mnuFileExit_Click(self):
        self.close()

    def frmEditor_FormClosing(self, e):
        if not self.confirm_discard():
            e.Cancel = True

    # ------------------------------------------------------------------ Edit
    def mnuEditUndo_Click(self):
        self.txtEdit.undo()

    def mnuEditRedo_Click(self):
        self.txtEdit.redo()

    def mnuEditCut_Click(self):
        self.txtEdit.cut()

    def mnuEditCopy_Click(self):
        self.txtEdit.copy()

    def mnuEditPaste_Click(self):
        self.txtEdit.paste()

    def _change_case(self, upper: bool):
        cur = self.txtEdit.textCursor()
        if not cur.hasSelection():
            cur.select(QTextCursor.SelectionType.WordUnderCursor)
        text = cur.selectedText()
        cur.insertText(text.upper() if upper else text.lower())

    def mnuEditUpper_Click(self):
        self._change_case(True)

    def mnuEditLower_Click(self):
        self._change_case(False)

    # ------------------------------------------------------------------ Find / Replace
    def btnFind_Click(self):
        what = self.txtFind.text()
        if not what:
            return False
        if self.txtEdit.find(what):
            self.message(f'Found "{what}"')
            return True
        self.txtEdit.moveCursor(QTextCursor.MoveOperation.Start)        # wrap around
        if self.txtEdit.find(what):
            self.message(f'Found "{what}" (from the top)')
            return True
        self.message(f'Cannot find "{what}"')
        return False

    def btnReplaceAll_Click(self):
        what, new = self.txtFind.text(), self.txtReplace.text()
        if not what:
            return 0
        doc = self.txtEdit.document()
        cur = QTextCursor(doc)
        cur.beginEditBlock()                         # one Undo step for the whole replace
        count = 0
        found = doc.find(what, 0, QTextDocument.FindFlag(0))
        while not found.isNull():
            found.insertText(new)
            count += 1
            found = doc.find(what, found.position(), QTextDocument.FindFlag(0))
        cur.endEditBlock()
        self.message(f"Replaced {count} occurrence(s)")
        return count

    # ------------------------------------------------------------------ View / Help
    def mnuViewZoomIn_Click(self):
        self.txtEdit.zoomIn(2)

    def mnuViewZoomOut_Click(self):
        self.txtEdit.zoomOut(2)

    def mnuViewRtl_Click(self):
        rtl = self.mnuViewRtl.isChecked()
        self.txtEdit.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        opt = self.txtEdit.document().defaultTextOption()
        opt.setTextDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        opt.setAlignment(Qt.AlignmentFlag.AlignRight if rtl else Qt.AlignmentFlag.AlignLeft)
        self.txtEdit.document().setDefaultTextOption(opt)
        self.message("Right to left" if rtl else "Left to right")

    def mnuHelpAbout_Click(self):
        QMessageBox.about(self, APP, "Qt Text Editor - a RAD IDE sample (PySide6).\n\n"
                                     "(c) 2026 Musoftware - https://musoftwares.com")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    form = frmEditor()
    form.show()
    sys.exit(app.exec())
