"""Project templates for File > New Project and the Start Page:
Windows Application, Dialog Application (OK / Cancel), Data Entry Form (fields,
list, Save / New / Delete with JSON file storage) and Console Application
(no form: a module with main).

Language-specific code is provided for python-tk, python-qt, vb-basic and ring-qt;
other languages get the same forms with empty event handlers."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QFormLayout, QGroupBox, QLabel, QPushButton, QVBoxLayout

from ..controls import event_args
from ..model import Form, Project

TEMPLATES = [
    ("windows", "Windows Application", "An application with an empty form."),
    ("dialog", "Dialog Application", "A fixed-size form with a message and OK / Cancel buttons."),
    ("data", "Data Entry Form", "Labels, text boxes, a list and Save / New / Delete buttons; "
                                "the records are stored in a JSON file (data.json)."),
    ("console", "Console Application", "No form: a code module with a main entry point. "
                                       "Output appears in the Output window."),
    ("library", "Class Library", "No form: one module with an example public function. Other projects of "
                                 "the solution use it through Add Reference and call it as their own code "
                                 "(e.g. MathLib.Add(2, 3)) - whatever their language."),
]
DEFAULT_NAMES = {"windows": "WindowsApplication", "dialog": "DialogApplication", "data": "DataEntry",
                 "console": "ConsoleApplication", "library": "ClassLibrary"}


# ===================================================================== forms
def _add(form: Form, ctype: str, name: str, x: int, y: int, w: int | None = None, h: int | None = None,
         **props):
    c = form.add(ctype, x, y)
    c.props["Name"] = name
    if "Text" in c.props:
        c.props["Text"] = props.pop("Text", name)
    if w is not None:
        c.props["Width"] = w
    if h is not None:
        c.props["Height"] = h
    c.props.update(props)
    return c


def dialog_form(form: Form) -> None:
    form.props.update(Text="Dialog", Width=380, Height=170, FormBorderStyle="FixedSingle")
    _add(form, "Label", "lblMessage", 20, 24, 330, 40, Text="Do you want to continue?")
    _add(form, "Button", "btnOK", 190, 92, 75, 25, Text="OK")
    _add(form, "Button", "btnCancel", 275, 92, 75, 25, Text="Cancel")


def data_form(form: Form) -> None:
    form.props.update(Text="Data Entry", Width=420, Height=330)
    for i, (field, label) in enumerate((("Name", "Name:"), ("Email", "E-mail:"), ("Phone", "Phone:"))):
        _add(form, "Label", f"lbl{field}", 16, 20 + 32 * i, 70, 17, Text=label)
        _add(form, "TextBox", f"txt{field}", 90, 17 + 32 * i, 300, 20, Text="")
    _add(form, "Button", "btnNew", 90, 115, 75, 25, Text="New")
    _add(form, "Button", "btnSave", 172, 115, 75, 25, Text="Save")
    _add(form, "Button", "btnDelete", 254, 115, 75, 25, Text="Delete")
    _add(form, "ListBox", "lstRecords", 16, 152, 374, 128)


# ===================================================================== code per language
def _h(plugin, form, ctrl_name, event):
    ctrl = form.find(ctrl_name) if ctrl_name else None
    return plugin.handler_for(form, ctrl, event)


def _py_insert(code: str, methods: str, imports: str = "", load_body: str | None = None, load_name="") -> str:
    """Insert methods into the form class (before `if __name__`), extra imports at the top,
    and replace the body of the Load handler."""
    if load_body is not None and load_name:
        stub = f"    def {load_name}(self):\n        pass\n"
        if stub in code:
            code = code.replace(stub, f"    def {load_name}(self):\n{load_body}")
    marker = "\n\nif __name__"
    i = code.find(marker)
    code = (code[:i].rstrip("\n") + "\n\n" + methods.rstrip("\n") + "\n" + code[i:]) if i >= 0 else \
        code.rstrip("\n") + "\n\n" + methods
    if imports:
        code = imports + code
    return code


def python_dialog(plugin, form, code: str, qt: bool) -> str:
    ok, cancel = _h(plugin, form, "btnOK", "Click"), _h(plugin, form, "btnCancel", "Click")
    load = _h(plugin, form, None, "Load")
    if qt:
        show = '        QMessageBox.information(self, "Dialog", "You clicked OK.")\n'
        close = "        self.close()\n"
    else:
        show = '        messagebox.showinfo("Dialog", "You clicked OK.", parent=self.root)\n'
        close = "        self.root.destroy()\n"
    methods = (f"    def {ok}(self):\n        self.result = \"OK\"\n{show}{close}\n"
               f"    def {cancel}(self):\n        self.result = \"Cancel\"\n{close}")
    return _py_insert(code, methods, "" if qt else "from tkinter import messagebox\n",
                      "        self.result = \"\"          # \"OK\" or \"Cancel\" after the dialog closes\n", load)


PY_STORAGE = '''    # ---------------------------------------------------------- storage (data.json)
    def load_records(self):
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (OSError, ValueError):
            return []

    def save_records(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)

'''


def python_data(plugin, form, code: str, qt: bool) -> str:
    H = lambda c, e: _h(plugin, form, c, e)  # noqa: E731
    load = H(None, "Load")
    if qt:
        get = lambda n: f"self.txt{n}.text().strip()"  # noqa: E731
        set_ = lambda n, v: f"self.txt{n}.setText({v})"  # noqa: E731
        clear_list, add_item = "self.lstRecords.clear()", "self.lstRecords.addItem"
        warn = 'QMessageBox.warning(self, "Save", "Please enter a name.")'
        ask = ('QMessageBox.question(self, "Delete", f"Delete {rec[\'name\']}?") != '
               'QMessageBox.StandardButton.Yes')
        sel_index = "self.lstRecords.currentRow()"
        unselect = "self.lstRecords.setCurrentRow(-1)"
        focus = "self.txtName.setFocus()"
    else:
        get = lambda n: f"self.txt{n}_var.get().strip()"  # noqa: E731
        set_ = lambda n, v: f"self.txt{n}_var.set({v})"  # noqa: E731
        clear_list, add_item = 'self.lstRecords.delete(0, "end")', 'self.lstRecords.insert("end", '
        warn = 'messagebox.showwarning("Save", "Please enter a name.", parent=self.root)'
        ask = 'not messagebox.askyesno("Delete", f"Delete {rec[\'name\']}?", parent=self.root)'
        sel_index = "(self.lstRecords.curselection() or [-1])[0]"
        unselect = 'self.lstRecords.selection_clear(0, "end")'
        focus = "self.txtName.focus_set()"
    add = (f"{add_item}self.record_text(r))" if not qt else f"{add_item}(self.record_text(r))")
    methods = PY_STORAGE + f'''    def record_text(self, r):
        return f"{{r.get('name', '')}}  <{{r.get('email', '')}}>  {{r.get('phone', '')}}"

    def show_records(self):
        {clear_list}
        for r in self.records:
            {add}

    def clear_fields(self):
        self.current = -1
        for name in ("Name", "Email", "Phone"):
            getattr(self, "txt" + name{'' if qt else ' + "_var"'}).set{'Text' if qt else ''}("")
        {unselect}

    # ---------------------------------------------------------- events
    def {H("btnSave", "Click")}(self):
        rec = {{"name": {get("Name")}, "email": {get("Email")}, "phone": {get("Phone")}}}
        if not rec["name"]:
            {warn}
            return
        if 0 <= self.current < len(self.records):
            self.records[self.current] = rec          # update the selected record
        else:
            self.records.append(rec)                  # add a new record
        self.save_records()
        self.show_records()
        self.clear_fields()

    def {H("btnNew", "Click")}(self):
        self.clear_fields()
        {focus}

    def {H("btnDelete", "Click")}(self):
        if not 0 <= self.current < len(self.records):
            return
        rec = self.records[self.current]
        if {ask}:
            return
        del self.records[self.current]
        self.save_records()
        self.show_records()
        self.clear_fields()

    def {H("lstRecords", "SelectedIndexChanged")}(self):
        i = {sel_index}
        if 0 <= i < len(self.records):
            self.current = i
            r = self.records[i]
            {set_("Name", "r.get('name', '')")}
            {set_("Email", "r.get('email', '')")}
            {set_("Phone", "r.get('phone', '')")}
'''
    imports = "import json\nimport os\n" + ("" if qt else "from tkinter import messagebox\n")
    if qt:
        imports = "import json\nimport os\n"
        code = code.replace("import sys\n\n", "import sys\n", 1)
    code = _py_insert(code, methods, imports,
                      "        self.records = self.load_records()\n        self.current = -1\n"
                      "        self.show_records()\n", load)
    # DATA_FILE after the imports
    lines = code.splitlines()
    last_import = max(i for i, ln in enumerate(lines) if ln.startswith(("import ", "from ")))
    lines[last_import + 1:last_import + 1] = ["", "DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "
                                              "\"data.json\")"]
    return "\n".join(lines) + "\n"


def vb_dialog(plugin, form, code: str) -> str:
    return ("Option Explicit\n\n"
            "' Dialog: OK shows a message, both buttons close the form.\n"
            "Public DialogResult As String\n\n"
            f"Private Sub {_h(plugin, form, None, 'Load')}()\n"
            "    DialogResult = \"\"\n"
            "End Sub\n\n"
            f"Private Sub {_h(plugin, form, 'btnOK', 'Click')}()\n"
            "    DialogResult = \"OK\"\n"
            "    MsgBox \"You clicked OK.\", vbInformation, \"Dialog\"\n"
            "    Unload Me\n"
            "End Sub\n\n"
            f"Private Sub {_h(plugin, form, 'btnCancel', 'Click')}()\n"
            "    DialogResult = \"Cancel\"\n"
            "    Unload Me\n"
            "End Sub\n")


VB_DATA = '''Option Explicit

' Data entry form - the records are kept in data.json in the program folder
' (written and read with Scripting.FileSystemObject, one record per line).

Private mNames() As String
Private mEmails() As String
Private mPhones() As String
Private mCount As Long
Private mCurrent As Long

Private Function DataFile() As String
    DataFile = App.Path & "\\data.json"
End Function

Private Function JsonEscape(ByVal s As String) As String
    s = Replace(s, "\\", "\\\\")
    s = Replace(s, """", "\\""")
    JsonEscape = s
End Function

Private Function JsonField(ByVal sLine As String, ByVal sKey As String) As String
    Dim p As Long, c As String, sOut As String
    p = InStr(sLine, """" & sKey & """:")
    If p = 0 Then Exit Function
    p = InStr(p + Len(sKey) + 3, sLine, """")
    If p = 0 Then Exit Function
    p = p + 1
    Do While p <= Len(sLine)
        c = Mid(sLine, p, 1)
        If c = "\\" Then
            p = p + 1
            c = Mid(sLine, p, 1)
            If c = "n" Then c = Chr(10)
            sOut = sOut & c
        ElseIf c = """" Then
            Exit Do
        Else
            sOut = sOut & c
        End If
        p = p + 1
    Loop
    JsonField = sOut
End Function

Private Sub GrowArrays(ByVal n As Long)
    ReDim Preserve mNames(n)
    ReDim Preserve mEmails(n)
    ReDim Preserve mPhones(n)
End Sub

Private Sub LoadRecords()
    Dim fso As Object, ts As Object, sLine As String
    mCount = 0
    GrowArrays 0
    Set fso = CreateObject("Scripting.FileSystemObject")
    If Not fso.FileExists(DataFile()) Then Exit Sub
    Set ts = fso.OpenTextFile(DataFile(), 1)
    Do While Not ts.AtEndOfStream
        sLine = ts.ReadLine
        If InStr(sLine, "{") > 0 Then
            mCount = mCount + 1
            GrowArrays mCount
            mNames(mCount) = JsonField(sLine, "name")
            mEmails(mCount) = JsonField(sLine, "email")
            mPhones(mCount) = JsonField(sLine, "phone")
        End If
    Loop
    ts.Close
End Sub

Private Sub SaveRecords()
    Dim fso As Object, ts As Object, i As Long, sLine As String
    Set fso = CreateObject("Scripting.FileSystemObject")
    Set ts = fso.CreateTextFile(DataFile(), True)
    ts.WriteLine "["
    For i = 1 To mCount
        sLine = "  {""name"": """ & JsonEscape(mNames(i)) & """, ""email"": """ & JsonEscape(mEmails(i))
        sLine = sLine & """, ""phone"": """ & JsonEscape(mPhones(i)) & """}"
        If i < mCount Then sLine = sLine & ","
        ts.WriteLine sLine
    Next i
    ts.WriteLine "]"
    ts.Close
End Sub

Private Sub ShowRecords()
    Dim i As Long
    lstRecords.Clear
    For i = 1 To mCount
        lstRecords.AddItem mNames(i) & "  <" & mEmails(i) & ">  " & mPhones(i)
    Next i
End Sub

Private Sub ClearFields()
    mCurrent = 0
    txtName.Text = ""
    txtEmail.Text = ""
    txtPhone.Text = ""
End Sub

Private Sub {LOAD}()
    LoadRecords
    ShowRecords
    ClearFields
End Sub

Private Sub {SAVE}()
    If Trim(txtName.Text) = "" Then
        MsgBox "Please enter a name.", vbExclamation, "Save"
        Exit Sub
    End If
    If mCurrent = 0 Then
        mCount = mCount + 1
        GrowArrays mCount
        mCurrent = mCount
    End If
    mNames(mCurrent) = Trim(txtName.Text)
    mEmails(mCurrent) = Trim(txtEmail.Text)
    mPhones(mCurrent) = Trim(txtPhone.Text)
    SaveRecords
    ShowRecords
    ClearFields
End Sub

Private Sub {NEW}()
    ClearFields
    txtName.SetFocus
End Sub

Private Sub {DELETE}()
    Dim i As Long
    If mCurrent = 0 Then Exit Sub
    If MsgBox("Delete " & mNames(mCurrent) & "?", vbYesNo + vbQuestion, "Delete") <> vbYes Then Exit Sub
    For i = mCurrent To mCount - 1
        mNames(i) = mNames(i + 1)
        mEmails(i) = mEmails(i + 1)
        mPhones(i) = mPhones(i + 1)
    Next i
    mCount = mCount - 1
    GrowArrays mCount
    SaveRecords
    ShowRecords
    ClearFields
End Sub

Private Sub {SELECT}()
    If lstRecords.ListIndex < 0 Then Exit Sub
    mCurrent = lstRecords.ListIndex + 1
    txtName.Text = mNames(mCurrent)
    txtEmail.Text = mEmails(mCurrent)
    txtPhone.Text = mPhones(mCurrent)
End Sub
'''


def vb_data(plugin, form, code: str) -> str:
    H = lambda c, e: _h(plugin, form, c, e)  # noqa: E731
    return (VB_DATA.replace("{LOAD}", H(None, "Load")).replace("{SAVE}", H("btnSave", "Click"))
            .replace("{NEW}", H("btnNew", "Click")).replace("{DELETE}", H("btnDelete", "Click"))
            .replace("{SELECT}", H("lstRecords", "SelectedIndexChanged")))


def ring_dialog(plugin, form, code: str) -> str:
    n = form.name
    return (f"load \"{plugin.designer_file(n)}\"\n\n"
            f"# Dialog: OK shows a message, both buttons close the form.\n"
            f"# Show this form with:  {n}_Show()\n\n"
            "# ---------------- Event handlers ----------------\n\n"
            f"func {_h(plugin, form, None, 'Load')}\n"
            "    # runs after the form is created\n\n"
            f"func {_h(plugin, form, 'btnOK', 'Click')}\n"
            f"    oMsg = new qMessageBox({n}) {{\n"
            "        setWindowTitle(\"Dialog\")\n"
            "        setText(\"You clicked OK.\")\n"
            "        exec()\n"
            "    }\n"
            f"    {n}.close()\n\n"
            f"func {_h(plugin, form, 'btnCancel', 'Click')}\n"
            f"    {n}.close()\n")


RING_DATA = '''load "{DESIGNER}"
load "jsonlib.ring"

# Data entry form - the records are kept in data.json in the program folder.
# Show this form with:  {FORM}_Show()

# ---------------- Event handlers ----------------

func {LOAD}
    ShowRecords()

func {SAVE}
    cName = trim(txtName.text())
    if cName = ""
        Message("Please enter a name.")
        return
    ok
    aRecords = LoadRecords()
    aRec = [ :name = cName, :email = trim(txtEmail.text()), :phone = trim(txtPhone.text()) ]
    nRow = lstRecords.currentRow() + 1
    if nRow >= 1 and nRow <= len(aRecords)
        aRecords[nRow] = aRec          # update the selected record
    else
        aRecords + aRec                # add a new record
    ok
    SaveRecords(aRecords)
    ShowRecords()
    ClearFields()

func {NEW}
    ClearFields()
    txtName.setFocus(0)

func {DELETE}
    nRow = lstRecords.currentRow() + 1
    aRecords = LoadRecords()
    if nRow < 1 or nRow > len(aRecords) return ok
    del(aRecords, nRow)
    SaveRecords(aRecords)
    ShowRecords()
    ClearFields()

func {SELECT}
    nRow = lstRecords.currentRow() + 1
    aRecords = LoadRecords()
    if nRow >= 1 and nRow <= len(aRecords)
        aRec = aRecords[nRow]
        txtName.setText(Field(aRec, "name"))
        txtEmail.setText(Field(aRec, "email"))
        txtPhone.setText(Field(aRec, "phone"))
    ok

# ---------------- Storage (data.json) ----------------

func DataFile
    return "data.json"

func LoadRecords
    if not fexists(DataFile()) return [] ok
    cJSON = trim(read(DataFile()))
    if cJSON = "" return [] ok
    aList = JSON2List(cJSON)
    if not isList(aList) return [] ok
    # JSON2List() wraps a top-level JSON array in one more list
    while len(aList) = 1 and isList(aList[1]) and not IsRecord(aList[1])
        aList = aList[1]
    end
    return aList

func IsRecord aItem
    return isList(aItem) and len(aItem) > 0 and isList(aItem[1]) and len(aItem[1]) = 2 and isString(aItem[1][1])

func SaveRecords aRecords
    cJSON = "[" + nl
    for i = 1 to len(aRecords)
        aRec = aRecords[i]
        cJSON += '  {"name": ' + JsonStr(Field(aRec, "name")) + ', "email": ' + JsonStr(Field(aRec, "email"))
        cJSON += ', "phone": ' + JsonStr(Field(aRec, "phone")) + "}"
        if i < len(aRecords) cJSON += "," ok
        cJSON += nl
    next
    write(DataFile(), cJSON + "]" + nl)

func JsonStr cText
    cText = substr(cText, "\\", "\\\\")
    cText = substr(cText, '"', '\\"')
    return '"' + cText + '"'

func Field aRec, cKey
    for aPair in aRec
        if isList(aPair) and len(aPair) = 2 and lower("" + aPair[1]) = cKey
            return "" + aPair[2]
        ok
    next
    return ""

func ShowRecords
    lstRecords.clear()
    for aRec in LoadRecords()
        lstRecords.addItem(Field(aRec, "name") + "  <" + Field(aRec, "email") + ">  " + Field(aRec, "phone"))
    next

func ClearFields
    txtName.setText("")
    txtEmail.setText("")
    txtPhone.setText("")
    lstRecords.setCurrentRow(-1)

func Message cText
    oMsg = new qMessageBox({FORM}) {
        setWindowTitle("Data Entry")
        setText(cText)
        exec()
    }
'''


def ring_data(plugin, form, code: str) -> str:
    H = lambda c, e: _h(plugin, form, c, e)  # noqa: E731
    return (RING_DATA.replace("{DESIGNER}", plugin.designer_file(form.name)).replace("{FORM}", form.name)
            .replace("{LOAD}", H(None, "Load")).replace("{SAVE}", H("btnSave", "Click"))
            .replace("{NEW}", H("btnNew", "Click")).replace("{DELETE}", H("btnDelete", "Click"))
            .replace("{SELECT}", H("lstRecords", "SelectedIndexChanged")))


def generic_handlers(plugin, form, code: str, owners: list[tuple[str, str]]) -> str:
    """Other languages: empty handlers for the template's events."""
    for owner, event in owners:
        name = _h(plugin, form, owner, event)
        if plugin.find_handler(code, name) < 0:
            try:
                code, _line = plugin.add_handler(code, name, form, event_args(event))
            except Exception:  # noqa: BLE001 - a plugin without add_handler support
                pass
    return code


CONSOLE = {
    ".py": '''"""{NAME} - console application. Output appears in the Output window."""


def main():
    print("Hello from {NAME}!")
    total = sum(range(1, 11))
    print(f"1 + 2 + ... + 10 = {total}")


if __name__ == "__main__":
    main()
''',
    ".bas": '''Attribute VB_Name = "{NAME}"
Option Explicit

' Console application: the program starts in Sub Main.
' Output (Debug.Print) appears in the Output window.

Sub Main()
    Dim i As Integer, total As Long
    Debug.Print "Hello from {NAME}!"
    For i = 1 To 10
        total = total + i
    Next i
    Debug.Print "1 + 2 + ... + 10 = " & total
End Sub
''',
    ".ring": '''# {NAME} - console application. Output appears in the Output window.

func main
    see "Hello from {NAME}!" + nl
    nTotal = 0
    for i = 1 to 10
        nTotal += i
    next
    see "1 + 2 + ... + 10 = " + nTotal + nl
''',
}


# ===================================================================== apply
def apply_template(folder: Path, template: str) -> Project:
    """Turn a freshly created project (create_project) into the chosen template."""
    from ..languages import get_plugin
    project = Project.load(folder)
    plugin = get_plugin(project.language)
    if template in ("", "windows"):
        return project
    if template == "console":
        return _make_console(project, plugin)
    if template == "library":
        return _make_library(project, plugin)
    name = project.startup or (project.forms[0] if project.forms else "Form1")
    form_path = project.form_path(name)
    form = Form.load(form_path)
    code_path = folder / plugin.code_file(name)
    code = code_path.read_text(encoding="utf-8")
    pid = plugin.id
    if template == "dialog":
        dialog_form(form)
        if pid in ("python-tk", "python-qt"):
            code = python_dialog(plugin, form, code, qt=pid == "python-qt")
        elif pid == "vb-basic":
            code = vb_dialog(plugin, form, code)
        elif pid == "ring-qt":
            code = ring_dialog(plugin, form, code)
        else:
            code = generic_handlers(plugin, form, code, [("btnOK", "Click"), ("btnCancel", "Click")])
    elif template == "data":
        data_form(form)
        if pid in ("python-tk", "python-qt"):
            code = python_data(plugin, form, code, qt=pid == "python-qt")
        elif pid == "vb-basic":
            code = vb_data(plugin, form, code)
        elif pid == "ring-qt":
            code = ring_data(plugin, form, code)
        else:
            code = generic_handlers(plugin, form, code, [("btnSave", "Click"), ("btnNew", "Click"),
                                                         ("btnDelete", "Click"),
                                                         ("lstRecords", "SelectedIndexChanged")])
    else:
        raise ValueError(f"unknown template {template!r}")
    form.save(form_path)
    code_path.write_text(code, encoding="utf-8")
    (folder / plugin.designer_file(name)).write_text(plugin.generate_designer(form, code), encoding="utf-8")
    return project


def _make_console(project: Project, plugin) -> Project:
    folder = project.folder
    for name in list(project.forms):
        for f in (project.form_path(name), folder / plugin.code_file(name), folder / plugin.designer_file(name)):
            if f.exists():
                f.unlink()
    project.forms, project.startup = [], ""
    stem = "Program"
    filename = f"{stem}{plugin.code_ext}"
    text = CONSOLE.get(plugin.code_ext)
    if text is None:
        text = plugin.module_template(stem) or ""
        text += _console_comment(plugin)
    (folder / filename).write_text(text.replace("{NAME}", stem), encoding="utf-8")
    project.modules = [filename]
    project.startup = stem
    project.save()
    return project


def _make_library(project: Project, plugin) -> Project:
    """Class Library: no form, one module <Name><ext> with an example public function
    (the same as workspace.create_library_project, for a project that already exists)."""
    folder = project.folder
    for name in list(project.forms):
        for f in (project.form_path(name), folder / plugin.code_file(name), folder / plugin.designer_file(name)):
            if f.exists():
                f.unlink()
    filename = f"{project.name}{plugin.code_ext}"
    path = folder / filename
    if not path.exists():
        maker = getattr(plugin, "library_template", None)
        path.write_text(maker(project.name) if maker else plugin.module_template(project.name), encoding="utf-8")
    project.forms, project.startup, project.form_languages = [], "", {}
    project.modules = [filename]
    project.kind = "library"
    project.save()
    return project


def _console_comment(plugin) -> str:
    c = (plugin.line_comments or ["#"])[0]
    return f"\n{c} Console application: write the program's entry point (main) here.\n"


# ===================================================================== New Project dialog hook
def extend_new_project_dialog(dlg) -> None:
    """Called at the end of NewProjectDialog.__init__ (radide/dialogs.py): adds a
    Template chooser and remembers the choice for the project that is created."""
    combo = QComboBox()
    for tid, title, desc in TEMPLATES:
        combo.addItem(title, tid)
        combo.setItemData(combo.count() - 1, desc, Qt.ItemDataRole.ToolTipRole)
    win = dlg.parent()
    pre = getattr(win, "_template_preselect", None)
    if pre:
        idx = combo.findData(pre)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        win._template_preselect = None
    info = QLabel()
    info.setWordWrap(True)
    info.setProperty("radRole", "muted")

    def changed(_i=0):
        tid = combo.currentData()
        info.setText(next(d for t, _n, d in TEMPLATES if t == tid))
        cur = dlg.name.text()
        if any(cur.startswith(base) and cur[len(base):].isdigit() for base in DEFAULT_NAMES.values()):
            base = DEFAULT_NAMES[tid]
            i = 1
            loc = Path(dlg.location.text())
            while (loc / f"{base}{i}").exists():
                i += 1
            dlg.name.setText(f"{base}{i}")
    combo.currentIndexChanged.connect(changed)
    lay = dlg.layout()
    form = None
    for i in range(lay.count()):
        item = lay.itemAt(i)
        if item.layout() is not None and isinstance(item.layout(), QFormLayout):
            form = item.layout()
            break
    if form is not None:
        form.insertRow(0, "Template:", combo)
        form.insertRow(1, "", info)
    else:
        lay.insertWidget(max(0, lay.count() - 1), combo)
    dlg.template_combo = combo
    dlg.template_id = lambda: combo.currentData()
    changed()

    def remember():
        if win is not None:
            win._pending_template = (str(dlg.folder().resolve()), combo.currentData())
    dlg.accepted.connect(remember)


def _start_page_templates(win):
    """Add a 'Templates' box with one button per template to the Start Page."""
    from ..app import StartPage
    for i in range(win.tabs.count()):
        page = win.tabs.widget(i)
        if isinstance(page, StartPage) and not getattr(page, "_rad_templates", False):
            lay = page.layout()
            box = QGroupBox("New project from a template")
            bl = QVBoxLayout(box)
            for tid, title, desc in TEMPLATES:
                b = QPushButton(title)
                b.setToolTip(desc)
                b.setStyleSheet("text-align:left; padding:4px 8px;")
                b.clicked.connect(lambda _=False, t=tid: new_from_template(win, t))
                bl.addWidget(b)
            lay.insertWidget(max(0, lay.count() - 1), box)
            page._rad_templates = True


def new_from_template(win, template: str):
    win._template_preselect = template
    win.new_project()
    win._template_preselect = None


def install(win) -> None:
    orig_open = win.open_project

    def open_project(folder, *args, **kw):
        pending = getattr(win, "_pending_template", None)
        if pending:
            win._pending_template = None
            try:
                if Path(folder).resolve() == Path(pending[0]) and pending[1] not in ("", "windows"):
                    apply_template(Path(folder), pending[1])
            except Exception as e:  # noqa: BLE001 - never block opening the project
                win.log(f"[templates] could not apply the template: {e}")
        return orig_open(folder, *args, **kw)
    win.open_project = open_project
    try:
        _start_page_templates(win)
    except Exception as e:  # noqa: BLE001
        win.log(f"[templates] start page: {e}")


__all__ = ["TEMPLATES", "apply_template", "extend_new_project_dialog", "new_from_template"]
