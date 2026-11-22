# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Group "python": the python-tk and python-qt (PySide6) examples in samples/Examples/Python and PythonQt.

Steps per project (on a temporary copy):
  open    exlib.designer_check - every form in the real designer, no control lost
  build   py_compile of every .py file (generated designer files included)
  run     the scenario below in its own process (Tk: the real window of the program, found with EnumWindows,
          driven by calling its widgets / handlers; Qt: offscreen PySide6, widgets clicked with QTest,
          widget.grab only).  Message boxes and file dialogs are scripted; the user's clipboard is restored.
  publish exlib.publish - Build > Publish's build step (PyInstaller); kind / size / Python inside

Run one scenario by hand:  .venv\\Scripts\\python samples\\Tests\\Examples\\ex_python.py --run <scenario> <folder>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import exlib  # noqa: E402


# ============================================================================ scenarios (child process)
class Checks:
    def __init__(self):
        self.items: list[tuple[bool, str]] = []

    def __call__(self, cond, msg):
        self.items.append((bool(cond), msg))
        print(("    ok   " if cond else "    FAIL ") + msg, flush=True)
        return bool(cond)

    def result(self):
        bad = [m for ok, m in self.items if not ok]
        return {"ok": not bad and bool(self.items), "passed": sum(ok for ok, _ in self.items),
                "total": len(self.items), "failed": bad}


def _clipboard_guard(root):
    """Remember the user's clipboard text; returns a function that puts it back."""
    try:
        old = root.clipboard_get()
    except Exception:  # noqa: BLE001 - empty / not text
        old = None

    def restore():
        try:
            root.clipboard_clear()
            if old is not None:
                root.clipboard_append(old)
            root.update()
        except Exception:  # noqa: BLE001
            pass
    return restore


def _script_dialogs(answers: dict):
    """Replace Tk message boxes / file dialogs with scripted answers (recorded in answers['log'])."""
    from tkinter import colorchooser, filedialog, messagebox
    log = answers.setdefault("log", [])

    def make(name, default):
        def fn(*a, **k):
            log.append((name, a[1] if len(a) > 1 else k.get("message", "")))
            q = answers.get(name)
            return q.pop(0) if isinstance(q, list) and q else (q if q is not None and not isinstance(q, list)
                                                                 else default)
        return fn
    for name, default in (("askyesnocancel", False), ("askyesno", True), ("showinfo", "ok"),
                          ("showerror", "ok"), ("showwarning", "ok"), ("askokcancel", True)):
        setattr(messagebox, name, make(name, default))
    filedialog.askopenfilename = make("askopenfilename", "")
    filedialog.asksaveasfilename = make("asksaveasfilename", "")
    colorchooser.askcolor = make("askcolor", (None, None))
    return log


def tk_notepad(folder: Path, c: Checks):
    tmp = Path(tempfile.mkdtemp(prefix="np_"))
    out = tmp / "note.txt"
    answers = {"asksaveasfilename": [str(out)], "askopenfilename": [str(out)], "askyesnocancel": [False]}
    _script_dialogs(answers)
    d = exlib.TkDriver(folder)
    f = d.form
    restore = _clipboard_guard(f.root)
    try:
        c(d.window("RAD Notepad"), "the Notepad window appears (EnumWindows): " + str(d.window("RAD Notepad")))
        c(not f.pnlFind.winfo_ismapped(), "find bar hidden at start")
        f.txtEdit.insert("1.0", "Hello world from RAD IDE\nسطر عربي - Arabic line\nhello again")
        f._on_edit()
        d.pump(50)
        c("12 words" in f.sbStatus.cget("text"), "status bar counts words: " + f.sbStatus.cget("text"))
        c(f.root.title().startswith("*Untitled"), "title shows unsaved changes: " + f.root.title())
        f.mnuEditFind_Click()
        d.pump(50)
        c(f.pnlFind.winfo_ismapped(), "Edit > Find shows the find bar")
        f.txtFind_var.set("HELLO")
        f.txtEdit.mark_set("insert", "1.0")
        c(f.btnFindNext_Click() and f.txtEdit.get("sel.first", "sel.last") == "Hello", "Find Next selects 'Hello'")
        c(f.btnFindNext_Click() and f.txtEdit.index("sel.first") == "3.0", "Find Next again -> line 3 (no case)")
        f.chkMatchCase_var.set(True)
        f.txtEdit.mark_set("insert", "1.0")
        c(not f.btnFindNext_Click(), "Match case: 'HELLO' is not found")
        f.btnFindClose_Click()
        # clipboard: copy the first word, paste it at the end
        f.txtEdit.tag_remove("sel", "1.0", "end")
        f.txtEdit.tag_add("sel", "1.0", "1.5")
        f.mnuEditCopy_Click()
        d.pump(30)
        try:
            clip = f.root.clipboard_get()
        except Exception as e:  # noqa: BLE001
            clip = f"<{e}>"
        c(clip == "Hello", f"Edit > Copy puts the selection on the clipboard ({clip!r})")
        f.txtEdit.tag_remove("sel", "1.0", "end")
        f.txtEdit.mark_set("insert", "end-1c")
        f.mnuEditPaste_Click()
        c(f.text().endswith("hello againHello"), "Edit > Paste inserts it")
        f.txtEdit.tag_add("sel", "3.0", "3.5")
        f.mnuEditCut_Click()
        c(f.text().endswith(" againHello") and "hello again" not in f.text(), "Edit > Cut removes the selection")
        f.mnuFileSave_Click()                      # Untitled -> SaveFileDialog (scripted)
        c(out.exists() and "سطر عربي" in out.read_text("utf-8"), "File > Save writes UTF-8 (Arabic kept)")
        c(f.root.title() == "note.txt - RAD Notepad", "title after save: " + f.root.title())
        f.txtEdit.insert("end", "\nmore")
        f.mnuFileNew_Click()                       # asks to save -> scripted "No"
        c(f.text() == "" and f.path == "", "File > New after 'Don't save' clears the editor")
        f.mnuFileOpen_Click()
        c(f.text().startswith("Hello world") and f.path == str(out), "File > Open loads the saved file")
        f.mnuFormatWrap_Click()
        c(f.txtEdit.cget("wrap") == "none", "Format > Word Wrap toggles wrapping")
        f.mnuEditSelectAll_Click()
        c(f.txtEdit.get("sel.first", "sel.last") == f.text(), "Edit > Select All")
    finally:
        restore()
        d.close()


def tk_calculator(folder: Path, c: Checks):
    d = exlib.TkDriver(folder)
    f = d.form
    try:
        c(d.window("Calculator"), "the Calculator window appears (EnumWindows)")

        def keys(seq):
            names = {"+": "btnAdd", "-": "btnSub", "*": "btnMul", "/": "btnDiv", "=": "btnEquals", ".": "btnDot",
                     "C": "btnClear"}
            for ch in seq:
                getattr(f, names.get(ch, f"btn{ch}")).invoke()
            d.pump(20)
            return f.lblDisplay.cget("text")
        c(keys("C12+7=") == "19", "12 + 7 = 19 with the buttons")
        c(f.lblExpr.cget("text") == "12 + 7 =", "expression line: " + f.lblExpr.cget("text"))
        c(keys("=") == "26", "= again repeats + 7 -> 26")
        c(keys("C0.1+0.2=") == "0.3", "0.1 + 0.2 = 0.3 (decimal arithmetic)")
        c(keys("C2+3*4=") == "20", "2 + 3 * 4 = 20 (left to right, like a pocket calculator)")
        c(keys("C9/0=") == "Cannot divide by zero", "division by zero message")
        keys("C5")
        f.btnMPlus.invoke()
        keys("C")
        f.btnMR.invoke()
        d.pump(20)
        c(f.lblDisplay.cget("text") == "5" and f.lblMemory.cget("text") == "M", "M+ / MR memory and indicator")
        f.btnMC.invoke()
        d.pump(20)
        c(f.lblMemory.cget("text") == "", "MC clears the memory")

        class K:                                   # keyboard: the form-level key handler
            def __init__(self, ch="", sym=""):
                self.char, self.keysym = ch, sym or ch
        keys("C")
        for ch in "7*6":
            f._on_key(K(ch))
        f._on_key(K("", "Return"))
        c(f.lblDisplay.cget("text") == "42", "keyboard 7*6 Enter = 42")
        f._on_key(K("", "BackSpace"))
        f._on_key(K("", "Escape"))
        c(f.lblDisplay.cget("text") == "0", "Escape clears")
        import CalcEngine
        c(CalcEngine.evaluate("100/8") == "12.5", "CalcEngine.evaluate('100/8') = 12.5 (module for RAD Hub)")
    finally:
        d.close()


def tk_contacts(folder: Path, c: Checks):
    import sqlite3
    tmp = Path(tempfile.mkdtemp(prefix="ct_"))
    csv_path = tmp / "contacts.csv"
    _script_dialogs({"asksaveasfilename": [str(csv_path)], "askyesno": [True]})
    d = exlib.TkDriver(folder)
    f = d.form
    db = folder / "contacts.db"

    def db_count():
        con = sqlite3.connect(db)
        n = con.execute("SELECT COUNT(*) FROM Contacts").fetchone()[0]
        con.close()
        return n
    try:
        c(d.window("Contacts"), "the Contacts window appears (EnumWindows)")
        c(f.Contacts.Count == 5 and f.ContactsDataGridView.RowCount == 5, "data source filled: 5 rows in the grid")
        c(f.txtName_var.get() == "Ahmed Hassan", "bound TextBox shows the current record")
        f.ContactsBindingNavigatorMoveNextItem.invoke()
        d.pump(30)
        c(f.txtName_var.get() == "Mona Adel" and "2 of 5" in f.ContactsBindingNavigatorPositionItem.cget("text"),
          "navigator > moves to record 2: " + f.ContactsBindingNavigatorPositionItem.cget("text"))
        f.txtSearch_var.set("giza")
        d.pump(30)
        c(f.Contacts.Count == 1 and f.txtName_var.get() == "سارة محمود", "search 'giza' -> the Arabic contact")
        f.txtSearch_var.set("")
        d.pump(30)
        f.btnNew_Click()
        d.pump(30)
        f.txtName_var.set("")
        c(f.btnSave_Click() is False and "Name is required" in f.lblError.cget("text"),
          "validation: empty name refused")
        f.txtName_var.set("Test Person")
        f.txtEmail_var.set("not-an-email")
        c(f.btnSave_Click() is False and "E-mail" in f.lblError.cget("text"), "validation: bad e-mail refused")
        f.txtEmail_var.set("test@example.com")
        f.txtPhone_var.set("+20 123 456")
        f.txtCity_var.set("Aswan")
        c(f.btnSave_Click() is True and db_count() == 6, "Save inserts the new contact into contacts.db")
        c("Aswan" in f.cboCity.cget("values"), "the city list is refreshed from the database")
        f.cboCity.set("Cairo")
        f.cboCity_SelectedIndexChanged()
        d.pump(30)
        c(f.Contacts.Count == 1, "city filter = parameterized Fill('City = ?', 'Cairo')")
        f.cboCity.set("(all cities)")
        f.cboCity_SelectedIndexChanged()
        f.Contacts.Position = f.Contacts.Find("Name", "Test Person")
        d.pump(30)
        f.txtPhone_var.set("+20 999 000")
        f.btnSave_Click()
        con = sqlite3.connect(db)
        phone = con.execute("SELECT Phone FROM Contacts WHERE Name='Test Person'").fetchone()[0]
        con.close()
        c(phone == "+20 999 000", "editing a bound TextBox + Save updates the row")
        f.btnExport_Click()
        lines = csv_path.read_text("utf-8-sig").splitlines() if csv_path.exists() else []
        c(len(lines) == 7 and lines[0].startswith("Id,Name"), f"Export CSV writes header + 6 rows ({len(lines)})")
        f.btnDelete_Click()                       # scripted "Yes"
        c(db_count() == 5 and f.Contacts.Count == 5, "Delete removes it from the database")
    finally:
        d.close()


def _drag(widget, pts, d):
    x0, y0 = pts[0]
    widget.event_generate("<ButtonPress-1>", x=x0, y=y0)
    for x, y in pts[1:]:
        widget.event_generate("<B1-Motion>", x=x, y=y, state=0x100)
    widget.event_generate("<ButtonRelease-1>", x=pts[-1][0], y=pts[-1][1])
    d.pump(30)


def tk_paint(folder: Path, c: Checks):
    tmp = Path(tempfile.mkdtemp(prefix="pt_"))
    _script_dialogs({"asksaveasfilename": [str(tmp / "drawing.ps")], "askcolor": [((0, 128, 0), "#008000")]})
    d = exlib.TkDriver(folder)
    f = d.form
    try:
        c(d.window("Paint"), "the Paint window appears (EnumWindows)")
        d.pump(200)
        _drag(f.canvas, [(20, 20), (60, 40), (100, 80), (140, 90)], d)
        n_pen = len(f.canvas.find_all())
        c(n_pen >= 4, f"mouse drag with the pen draws ({n_pen} canvas items)")
        f.cboColor.set("Red")
        f.cboColor_SelectedIndexChanged()
        f.optRect.invoke()
        f.trkSize_var.set(6)
        _drag(f.canvas, [(200, 100), (260, 150), (300, 200)], d)
        rects = [i for i in f.canvas.find_all() if f.canvas.type(i) == "rectangle"]
        c(len(rects) == 1 and f.canvas.itemcget(rects[0], "outline") == "#D62828"
          and float(f.canvas.itemcget(rects[0], "width")) == 6.0, "Box tool: one red rectangle, width 6")
        c(f.canvas.coords(rects[0]) == [200.0, 100.0, 300.0, 200.0], "rubber band ends at the mouse-up point")
        f.btnPickColor_Click()
        c(f.color == "#008000", "ColorDialog (scripted) sets the pen color")
        f.mnuEditUndo_Click()
        c(not [i for i in f.canvas.find_all() if f.canvas.type(i) == "rectangle"], "Undo removes the last stroke")
        f.mnuFileSave_Click()
        c((tmp / "drawing.ps").exists(), "File > Save writes the drawing (PostScript)")
        f.mnuEditClear_Click()
        c(not f.canvas.find_all(), "Clear Drawing")
        # live chart
        f.tabMain.select(1)
        f.numInterval_var.set(50)
        f.btnStart_Click()
        t_end = time.time() + 6
        while time.time() < t_end and len(f.samples) < 8:
            d.pump(100)
        c(len(f.samples) >= 8, f"Timer adds samples ({len(f.samples)} in a few seconds)")
        c("avg" in f.lblStats.cget("text") and float(f.prgLevel["value"]) > 0, "stats label + ProgressBar updated")
        c(len(f.chart.find_all()) > 10, "chart drawn on the canvas")
        f.btnStop_Click()
        n = len(f.samples)
        d.pump(300)
        c(len(f.samples) == n, "Stop stops the Timer")
    finally:
        d.close()


def tk_settings(folder: Path, c: Checks):
    tmp = Path(tempfile.mkdtemp(prefix="st_"))
    os.environ["RADEX_SETTINGS_DIR"] = str(tmp)
    _script_dialogs({})
    d = exlib.TkDriver(folder)
    f = d.form
    mod_settings = sys.modules["frmSettings"]
    opened = []
    orig = mod_settings.frmSettings.load_from

    def spy(self, settings):
        orig(self, settings)
        opened.append(self)
    mod_settings.frmSettings.load_from = spy
    try:
        c(d.window("Greeting Card"), "the main window appears (EnumWindows)")
        f.txtName_var.set("Ali")
        f.btnGreet.invoke()
        d.pump(30)
        c(f.lblGreeting.cget("text").startswith("Hello, Ali!"), "Greet: " + f.lblGreeting.cget("text").split("\n")[0])

        def choose(cancel=False):                 # runs while the modal dialog waits (wait_window)
            if not opened:
                f.root.after(50, lambda: choose(cancel))
                return
            dlg = opened[-1]
            c(bool(exlib.windows_of(os.getpid())) and dlg.root.winfo_viewable(), "Settings dialog is shown")
            c(dlg.root.grab_current() is not None, "Settings dialog is modal (grab)")
            if cancel:
                dlg.btnCancel.invoke()
                return
            dlg.cboLang.current(1)
            dlg.cboLang_SelectedIndexChanged()
            c(dlg.root.title() == "الإعدادات", "the dialog follows the chosen language (Arabic title)")
            dlg.cboColor.current(2)
            dlg.numFontSize_var.set(20)
            dlg.btnOK.invoke()
        f.root.after(100, choose)
        f.btnSettings_Click()
        data = json.loads((tmp / "settings.json").read_text("utf-8"))
        c(data["language"] == "ar" and data["color"] == "Sky" and data["font_size"] == 20 and data["name"] == "Ali",
          f"OK saves settings.json in the app data folder: {data}")
        c(f.lblTitle.cget("text") == "أهلاً وسهلاً" and f.lblTitle.cget("anchor") == "e", "Arabic UI, right aligned")
        c(f.lblGreeting.cget("text").startswith("أهلاً يا Ali"), "greeting re-rendered in Arabic")
        c(int(f.txtName.place_info()["x"]) == 560 - 140 - 250, "layout mirrored right-to-left (TextBox x)")
        c(f.lblGreeting.cget("bg").upper() == "#E3F2FD", "card color applied")
        opened.clear()
        f.root.after(100, lambda: choose(cancel=True))
        f.btnSettings_Click()
        c(json.loads((tmp / "settings.json").read_text("utf-8"))["language"] == "ar", "Cancel keeps the settings")
        f.mnuLangEn_Click()
        c(f.lblTitle.cget("text") == "Welcome" and f.lblTitle.cget("anchor") == "w", "Language > English switches back")
        f.mnuLangAr_Click()
        f2 = d.mod.frmMain()                       # a new start reads the saved settings
        d.pump(200)
        c(f2.lblTitle.cget("text") == "أهلاً وسهلاً" and f2.txtName_var.get() == "Ali",
          "restart: language and remembered name loaded")
        f2.root.destroy()
    finally:
        mod_settings.frmSettings.load_from = orig
        d.close()


# ---------------------------------------------------------------------------- Qt (PySide6, offscreen)
def _qt(folder: Path):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QApplication
    QCoreApplication.setOrganizationName(exlib.QORG)
    QCoreApplication.setApplicationName(exlib.QAPP)
    app = QApplication.instance() or QApplication([])
    sys.path.insert(0, str(folder))
    os.chdir(folder)
    return app


def _pump(app, ms=100):
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)


def _grab_ok(widget) -> bool:
    img = widget.grab().toImage()
    if img.isNull():
        return False
    colors = {img.pixel(x, y) for x in range(0, img.width(), max(1, img.width() // 25))
              for y in range(0, img.height(), max(1, img.height() // 25))}
    return len(colors) > 2


def qt_editor(folder: Path, c: Checks):
    app = _qt(folder)
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QMessageBox
    import frmEditor as mod
    tmp = Path(tempfile.mkdtemp(prefix="qe_"))
    out = tmp / "doc.txt"
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    f = mod.frmEditor()
    f.show()
    _pump(app, 200)
    c(f.isVisible() and f.windowTitle() == "Untitled - Qt Text Editor", "the editor window is shown: " + f.windowTitle())
    QTest.keyClicks(f.txtEdit, "the cat sat on the mat")
    _pump(app, 50)
    c(f.windowTitle().startswith("*") and "6 words" in f.sbStatus.text(), "typing: dirty title + word count")
    f.txtFind.setText("at")
    f.txtEdit.moveCursor(f.txtEdit.textCursor().MoveOperation.Start)
    QTest.mouseClick(f.btnFind, Qt.MouseButton.LeftButton)
    c(f.txtEdit.textCursor().selectedText() == "at", "Find Next (button click) selects the match")
    f.txtFind.setText("the")
    f.txtReplace.setText("a")
    QTest.mouseClick(f.btnReplaceAll, Qt.MouseButton.LeftButton)
    c(f.txtEdit.toPlainText() == "a cat sat on a mat" and "Replaced 2" in f.sbStatus.text(), "Replace All (2)")
    f.mnuEditUndo.trigger()
    c(f.txtEdit.toPlainText() == "the cat sat on the mat", "Undo reverts Replace All in one step")
    f.txtEdit.selectAll()
    f.mnuEditCopy.trigger()
    c(app.clipboard().text() == "the cat sat on the mat", "Edit > Copy -> clipboard (offscreen clipboard)")
    f.txtEdit.moveCursor(f.txtEdit.textCursor().MoveOperation.End)
    f.mnuEditPaste.trigger()
    c(f.txtEdit.toPlainText().count("cat") == 2, "Edit > Paste")
    f.txtEdit.selectAll()
    f.mnuEditUpper.trigger()
    c(f.txtEdit.toPlainText().startswith("THE CAT"), "Edit > Upper Case")
    f.dlgSave.ShowDialog = lambda: (setattr(f.dlgSave, "FileName", str(out)), "OK")[1]
    f.mnuFileSave.trigger()
    c(out.exists() and out.read_text("utf-8").startswith("THE CAT") and not f.windowTitle().startswith("*"),
      "File > Save (scripted dialog) writes the file")
    f.mnuViewRtl.setChecked(False)
    f.mnuViewRtl.trigger()
    c(f.txtEdit.layoutDirection() == Qt.LayoutDirection.RightToLeft, "View > Right to Left")
    f.txtEdit.setPlainText("نص عربي")
    f.mnuFileNew.trigger()                       # asks -> scripted No
    c(f.txtEdit.toPlainText() == "", "File > New after 'No'")
    f.dlgOpen.ShowDialog = lambda: (setattr(f.dlgOpen, "FileName", str(out)), "OK")[1]
    f.mnuFileOpen.trigger()
    c(f.txtEdit.toPlainText().startswith("THE CAT") and f.windowTitle() == "doc.txt - Qt Text Editor", "File > Open")
    c(_grab_ok(f), "widget.grab paints the form")
    f.close()


def qt_inventory(folder: Path, c: Checks):
    tmp = Path(tempfile.mkdtemp(prefix="qi_"))
    os.environ["RADEX_INVENTORY_DB"] = str(tmp / "inventory.db")
    app = _qt(folder)
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMessageBox
    import frmInventory as mod
    import frmItem as item_mod
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
    f = mod.frmInventory()
    f.show()
    _pump(app, 200)
    c(f.isVisible() and f.grdItems.rowCount() == 6, f"window shown, 6 seeded items ({f.grdItems.rowCount()})")
    QTest.keyClicks(f.txtSearch, "HW")
    _pump(app, 50)
    c(f.grdItems.rowCount() == 2, "search 'HW' -> 2 rows")
    f.txtSearch.clear()
    f.chkLowStock.setChecked(True)
    _pump(app, 50)
    c(f.grdItems.rowCount() == 2, "low stock filter -> 2 rows")
    f.chkLowStock.setChecked(False)
    _pump(app, 50)

    def in_dialog(steps):
        """Run steps(dlg) once the modal frmItem is open (it runs a local event loop)."""
        def poll():
            dlg = next((w for w in QApplication.topLevelWidgets()
                        if isinstance(w, item_mod.frmItem) and w.isVisible()), None)
            if dlg is None:
                QTimer.singleShot(50, poll)
                return
            steps(dlg)
        QTimer.singleShot(50, poll)

    seen = {}

    def add_steps(dlg):
        seen["modal"] = dlg.windowModality() == Qt.WindowModality.ApplicationModal
        dlg.txtSku.setText("hw-001")
        dlg.txtName.setText("Duplicate")
        QTest.mouseClick(dlg.btnOK, Qt.MouseButton.LeftButton)
        seen["dup"] = dlg.lblError.text()
        dlg.txtSku.setText("ny-500")
        dlg.txtName.setText("Notebook")
        dlg.txtPrice.setText("abc")
        QTest.mouseClick(dlg.btnOK, Qt.MouseButton.LeftButton)
        seen["price"] = dlg.lblError.text()
        dlg.txtPrice.setText("2,75")
        dlg.numQty.setValue(3)
        dlg.cboCategory.setCurrentText("Office")
        QTest.mouseClick(dlg.btnOK, Qt.MouseButton.LeftButton)
    in_dialog(add_steps)
    QTest.mouseClick(f.btnAdd, Qt.MouseButton.LeftButton)
    _pump(app, 50)
    c(seen.get("modal"), "frmItem opens application-modal")
    c("already used" in seen.get("dup", ""), "duplicate SKU refused: " + seen.get("dup", ""))
    c("number" in seen.get("price", ""), "bad price refused: " + seen.get("price", ""))
    row = f.db.items("NY-500")
    c(len(row) == 1 and row[0]["Price"] == 2.75 and row[0]["Qty"] == 3 and f.grdItems.rowCount() == 7,
      "OK adds NY-500 (qty 3, price 2.75) to SQLite and the grid")
    c("Added NY-500" in f.sbInfo.text() and "7 items" in f.lblTotal.text(), "status + totals: " + f.lblTotal.text())
    # edit the selected row (double-click handler = Edit)
    sel = f.selected_id()

    def edit_steps(dlg):
        seen["prefill"] = dlg.txtSku.text()
        dlg.numQty.setValue(50)
        QTest.mouseClick(dlg.btnOK, Qt.MouseButton.LeftButton)
    in_dialog(edit_steps)
    f.mnuItemEdit.trigger()
    c(seen.get("prefill") == "NY-500" and f.db.get(sel)["Qty"] == 50, "Edit pre-fills the dialog and saves qty 50")

    def cancel_steps(dlg):
        dlg.txtName.setText("changed")
        QTest.mouseClick(dlg.btnCancel, Qt.MouseButton.LeftButton)
    in_dialog(cancel_steps)
    f.btnEdit_Click()
    c(f.db.get(sel)["Name"] == "Notebook", "Cancel changes nothing")
    QTest.mouseClick(f.btnDelete, Qt.MouseButton.LeftButton)
    c(f.db.get(sel) is None and f.grdItems.rowCount() == 6, "Delete (confirmed) removes the item")
    out = tmp / "inv.csv"
    f.dlgExport.ShowDialog = lambda: (setattr(f.dlgExport, "FileName", str(out)), "OK")[1]
    f.mnuFileExport.trigger()
    c(out.exists() and len(out.read_text("utf-8-sig").splitlines()) == 7, "File > Export CSV")
    c(_grab_ok(f), "widget.grab paints the form")
    f.close()


def qt_dashboard(folder: Path, c: Checks):
    app = _qt(folder)
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    import frmDashboard as mod
    f = mod.frmDashboard()
    f.show()
    _pump(app, 200)
    c(f.isVisible() and f.tmrRefresh.isActive(), "dashboard shown, Timer running")
    t0 = f.ticks
    _pump(app, 1600)
    c(f.ticks - t0 >= 2, f"Timer ticks refresh the readings ({f.ticks - t0} in 1.6 s)")
    c(0 < f.prgMem.value() <= 100 and 0 < f.prgDisk.value() <= 100, f"memory {f.prgMem.value()} %, "
                                                                     f"disk {f.prgDisk.value()} %")
    c(":" in f.lblClock.text() and "refreshes" in f.lblUptime.text(), "clock + uptime labels")
    c(_grab_ok(f.picGauge), "gauges painted (QPainter on the PictureBox, widget.grab)")
    f.tabMain.setCurrentIndex(1)
    _pump(app, 100)
    c(_grab_ok(f.picHistory) and "CPU last" in f.lblHistory.text(), "history chart painted")
    f.tabMain.setCurrentIndex(2)
    QTest.keyClicks(f.txtTask, "Write the report")
    QTest.mouseClick(f.btnAddTask, Qt.MouseButton.LeftButton)
    c(f.lstTasks.count() == 3 and f.lstTasks.item(2).text() == "Write the report", "Add task")
    f.lstTasks.setCurrentRow(0)
    QTest.mouseClick(f.btnDoneTask, Qt.MouseButton.LeftButton)
    c(f.lstTasks.count() == 2 and "Done: Check the backups" in f.sbInfo.text(), "Done removes the task")
    QTest.mouseClick(f.btnPause, Qt.MouseButton.LeftButton)
    c(not f.tmrRefresh.isActive() and f.btnPause.text() == "Resume", "Pause stops the Timer")
    QTest.mouseClick(f.btnPause, Qt.MouseButton.LeftButton)
    f.chkFast.setChecked(True)
    c(f.tmrRefresh.isActive() and f.tmrRefresh.interval() == 200, "Resume + Fast refresh (200 ms)")
    f.close()


def nb_kernel(folder: Path, c: Checks):
    """Run every code cell of SalesAnalysis.ipynb in a real Jupyter kernel through the IDE's KernelSession
    (radide/notebook/kernel.py - what the notebook editor's Run All uses)."""
    from PyQt6.QtCore import QCoreApplication
    from radide.notebook.kernel import KernelChoice, KernelSession
    from radide.notebook.model import Notebook
    app = QCoreApplication.instance() or QCoreApplication([])
    nb = Notebook.load(folder / "SalesAnalysis.ipynb")
    k = KernelSession(KernelChoice(id=f"py:{sys.executable}", label="test", kind="python", python=sys.executable),
                      cwd=folder)
    out: dict[str, list[str]] = {}
    errors: list[str] = []
    replies: set[str] = set()

    def on_iopub(m):
        pid = (m.get("parent_header") or {}).get("msg_id", "")
        t, content = m.get("msg_type"), m.get("content") or {}
        if t == "stream":
            out.setdefault(pid, []).append(content.get("text", ""))
        elif t == "execute_result":
            out.setdefault(pid, []).append(str((content.get("data") or {}).get("text/plain", "")))
        elif t == "error":
            errors.append(f"{content.get('ename')}: {content.get('evalue')}")
    k.iopub.connect(on_iopub)
    k.shellReply.connect(lambda m: replies.add((m.get("parent_header") or {}).get("msg_id", "")))
    k.start()

    def until(cond, timeout):
        end = time.time() + timeout
        while time.time() < end and not cond():
            app.processEvents()
            time.sleep(0.02)
        return cond()
    try:
        c(until(lambda: k.status == "idle", 90), f"kernel started ({k.status} {k.last_error})")
        ids = [k.execute(cell.source) for cell in nb.cells if cell.cell_type == "code"]
        c(until(lambda: all(i in replies for i in ids), 60), f"all {len(ids)} code cells executed")
        until(lambda: k.status == "idle", 5)
        text = "".join("".join(out.get(i, [])) for i in ids)
        c(not errors, f"no cell raised ({errors[:2]})")
        c("54 rows, 6 months" in text, "cell 1 reads sales.csv")
        c("best month:" in text and "#" in text, "best month + text bar chart printed")
        c("'Cairo'" in "".join(out.get(ids[-1], [])), "last cell's value is displayed (execute_result)")
    finally:
        k.shutdown()


SCENARIOS = {"nb_kernel": nb_kernel, "tk_notepad": tk_notepad, "tk_calculator": tk_calculator, "tk_contacts": tk_contacts,
             "tk_paint": tk_paint, "tk_settings": tk_settings, "qt_editor": qt_editor,
             "qt_inventory": qt_inventory, "qt_dashboard": qt_dashboard}


def run_scenario(name: str, folder: str) -> None:
    exlib.setup_env()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    c = Checks()
    try:
        SCENARIOS[name](Path(folder), c)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        c(False, f"exception: {e!r}"[:300])
    print("@@RUN@@" + json.dumps(c.result(), ensure_ascii=False), flush=True)
    os._exit(0)


# ============================================================================ steps (runner child)
def _compile(folder: Path) -> tuple[bool, str]:
    bad = []
    files = [p for p in folder.rglob("*.py") if "Publish" not in p.parts]
    for p in files:
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as e:
            bad.append(f"{p.name}:{e.lineno}: {e.msg}")
    return not bad, f"{len(files)} files compiled" + (f"; errors: {bad}" if bad else "")


def _run(name: str, folder: Path, timeout=180) -> tuple[bool, str]:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    env.pop("QT_QPA_PLATFORM", None) if name.startswith("tk_") else None
    p = subprocess.run([sys.executable, "-u", str(Path(__file__).resolve()), "--run", name, str(folder)],
                       cwd=str(folder), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, env=env)
    out = p.stdout + p.stderr
    for line in out.splitlines():
        if not line.startswith("@@RUN@@"):
            print("  " + line, flush=True)
    row = next((json.loads(line[7:]) for line in out.splitlines() if line.startswith("@@RUN@@")), None)
    if row is None:
        return False, "scenario gave no result: " + out[-600:]
    return row["ok"], f"{row['passed']}/{row['total']} checks" + (f"; failed: {row['failed']}" if row["failed"] else "")


def _f5(work: Path, title: str) -> tuple[bool, str]:
    """Start the project exactly like F5 (plugin.run_spec + the IDE's interpreter, real window), wait for its
    window (EnumWindows over the started process tree), then close it with WM_CLOSE."""
    saved = os.environ.pop("QT_QPA_PLATFORM", None)
    env_extra = {"RADEX_SETTINGS_DIR": str(work / "_settings"), "RADEX_INVENTORY_DB": str(work / "_inv.db")}
    try:
        p = exlib.run_spec_proc(work, env_extra=env_extra)
    finally:
        if saved:
            os.environ["QT_QPA_PLATFORM"] = saved
    try:
        found = exlib.wait_window(p, title, 60)
    finally:
        exlib.stop_tree(p)
    return bool(found), f"F5: window {found[1]!r}" if found else "F5: no window (exit %s) %s" % (
        p.poll(), (p.stdout.read() if p.stdout else "")[-300:])


def _test(scenario: str, title: str):
    def test(folder: Path, res, opts):
        work = exlib.temp_copy(folder, "python")
        ok, note = exlib.designer_check(work)
        res.step("open", ok, note)
        ok, note = _compile(work)
        res.step("build", ok, note)
        ok, note = _run(scenario, work)
        ok2, note2 = _f5(work, title)
        res.step("run", ok and ok2, f"{note}; {note2}")
        if opts.get("publish"):
            pub_dir = exlib.temp_copy(folder, "python_pub")
            r = exlib.publish(pub_dir, log_file=pub_dir / "publish.log")
            if r.get("ok"):
                res["size"] = f"{r['size_mb']} MB ({'python' if r['python_inside'] else 'no python'})"
                exe = Path(r["dist"]) / r["exe"]          # the published program starts and shows its window
                env = dict(os.environ, RADEX_SETTINGS_DIR=str(pub_dir / "_settings"),
                           RADEX_INVENTORY_DB=str(pub_dir / "_inv.db"))
                env.pop("QT_QPA_PLATFORM", None)
                proc = subprocess.Popen([str(exe)], cwd=str(exe.parent), env=env)
                try:
                    found = exlib.wait_window(proc, title, 90)
                finally:
                    exlib.stop_tree(proc)
                res.step("publish", bool(found), f"kind={r['kind']} exe={r['exe']} {res['size']}; "
                                                 f"published exe window: {found[1] if found else 'NONE'}")
            else:
                res.step("publish", False, r.get("error", "") + " | " + " / ".join(r.get("log_tail", [])[-4:]))
    return test


def _test_notebook(folder: Path, res, opts):
    from radide.notebook.model import Notebook
    work = exlib.temp_copy(folder, "python")
    nb = Notebook.load(work / "SalesAnalysis.ipynb")
    kinds = [cell.cell_type for cell in nb.cells]
    res.step("open", nb.validate() is None and kinds.count("code") == 5 and kinds.count("markdown") == 5,
             f"nbformat {nb.to_json().get('nbformat')}.{nb.to_json().get('nbformat_minor')}: {len(kinds)} cells, "
             f"validate() = {nb.validate()}")
    try:
        compile(nb.to_py(), "SalesAnalysis.py", "exec")
        res.step("build", True, "File > Export as .py compiles")
    except SyntaxError as e:
        res.step("build", False, str(e))
    ok, note = _run("nb_kernel", work)
    res.step("run", ok, note)
    res["publish"] = "n/a"


EXAMPLES = {
    "Python/DataNotebook": {"lang": "notebook (.ipynb)", "test": _test_notebook},
    "Python/Notepad": {"lang": "python-tk", "test": _test("tk_notepad", "RAD Notepad")},
    "Python/Calculator": {"lang": "python-tk", "test": _test("tk_calculator", "Calculator")},
    "Python/Contacts": {"lang": "python-tk", "test": _test("tk_contacts", "Contacts")},
    "Python/PaintChart": {"lang": "python-tk", "test": _test("tk_paint", "Paint")},
    "Python/SettingsMultiForm": {"lang": "python-tk", "test": _test("tk_settings", "Greeting Card")},
    "PythonQt/TextEditor": {"lang": "python-qt", "test": _test("qt_editor", "Qt Text Editor")},
    "PythonQt/Inventory": {"lang": "python-qt", "test": _test("qt_inventory", "Inventory")},
    "PythonQt/Dashboard": {"lang": "python-qt", "test": _test("qt_dashboard", "Dashboard")},
}

if __name__ == "__main__":
    if "--run" in sys.argv:
        i = sys.argv.index("--run")
        run_scenario(sys.argv[i + 1], sys.argv[i + 2])
