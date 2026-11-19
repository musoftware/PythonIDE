"""(Re)create the sample projects in samples/ - one per language plugin.

Usage: .venv\\Scripts\\python tools\\make_samples.py
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from radide.languages import get_plugin  # noqa: E402
from radide.model import Form  # noqa: E402
from radide.workspace import create_project  # noqa: E402

HANDLERS = {
    "python-tk": {
        "btnGreet_Click": [
            "name = self.txtName_var.get()",
            "if self.chkUpper_var.get():",
            "    name = name.upper()",
            "self.lblResult.config(text=f\"Hello, {name}!\")",
            "self.lstLog.insert(\"end\", name)"],
        "Timer1_Tick": [
            "import time",
            "self.lblClock.config(text=time.strftime(\"%H:%M:%S\"))"],
        "mnuFileClear_Click": ["self.lstLog.delete(0, \"end\")"],
        "mnuFileExit_Click": ["self.root.destroy()"],
        "mnuHelpAbout_Click": [
            "from tkinter import messagebox",
            "messagebox.showinfo(\"About\", \"Made with RAD IDE\")"],
    },
    "ring-qt": {
        "btnGreet_Click": [
            "cName = txtName.text()",
            "if chkUpper.isChecked() cName = upper(cName) ok",
            "lblResult.setText(\"Hello, \" + cName + \"!\")",
            "lstLog.addItem(cName)"],
        "Timer1_Tick": ["lblClock.setText(time())"],
        "mnuFileClear_Click": ["lstLog.clear()"],
        "mnuFileExit_Click": ["Form1.close()"],
        "mnuHelpAbout_Click": [
            "oMsg = new qMessageBox(Form1)",
            "oMsg.setWindowTitle(\"About\")",
            "oMsg.setText(\"Made with RAD IDE\")",
            "oMsg.show()"],
    },
}

MENU = [
    {"Text": "File", "Name": "mnuFile", "Items": [
        {"Text": "Clear", "Name": "mnuFileClear"}, {"Text": "-"},
        {"Text": "Exit", "Name": "mnuFileExit"}]},
    {"Text": "Help", "Name": "mnuHelp", "Items": [{"Text": "About", "Name": "mnuHelpAbout"}]},
]


def build(project_name: str, lang: str, skip_code: bool = False) -> Path:
    folder = ROOT / "samples" / project_name
    shutil.rmtree(folder, ignore_errors=True)
    p = create_project(folder, project_name, lang)
    plugin = get_plugin(lang)
    f = Form.load(p.form_path("Form1"))
    f.props.update(Text=f"Hello - {plugin.display_name}", Width=440, Height=300)

    def add(t, x, y, parent="", **kw):
        c = f.add(t, x, y, parent)
        c.props.update(kw)
        return c
    add("MenuStrip", 0, 0, Items=MENU)
    add("Panel", 8, 8, Name="pnlInput", Width=424, Height=48, BackColor="#DDE7F5")
    add("Label", 8, 14, "pnlInput", Name="lblPrompt", Text="Your name:", Width=72, Height=20)
    add("TextBox", 88, 12, "pnlInput", Name="txtName", Text="World", Width=200, Height=22)
    add("Button", 304, 10, "pnlInput", Name="btnGreet", Text="Greet", Width=104, Height=28,
        BackColor="#FFD75E")
    add("Label", 8, 64, Name="lblResult", Text="...", Width=424, Height=28, FontSize=14,
        ForeColor="#1F3D7A")
    add("ListBox", 8, 104, Name="lstLog", Width=260, Height=184)
    add("GroupBox", 280, 104, Name="grpOptions", Text="Options", Width=152, Height=72)
    add("CheckBox", 12, 28, "grpOptions", Name="chkUpper", Text="Upper case", Width=120, Height=22)
    add("Label", 280, 192, Name="lblClock", Text="--:--:--", Width=152, Height=32, FontSize=16)
    add("Timer", 0, 0, Interval=1000, Enabled=True)
    f.save(p.form_path("Form1"))
    if skip_code:
        return folder

    code_path = folder / plugin.code_file("Form1")
    code = code_path.read_text(encoding="utf-8")
    indent = "        " if lang == "python-tk" else "    "
    for handler, body in HANDLERS[lang].items():
        code, line = plugin.add_handler(code, handler, f)
        lines = code.splitlines()
        lines[line:line + 1] = [indent + b for b in body]
        code = "\n".join(lines) + "\n"
    code_path.write_text(code, encoding="utf-8")
    (folder / plugin.designer_file("Form1")).write_text(plugin.generate_designer(f, code), encoding="utf-8")
    return folder


VB_CODE = """Option Explicit
Private mCount As Integer

Private Sub Form_Load()
    lblResult.Caption = "Type a name and press Greet"
End Sub

Private Sub btnGreet_Click()
    Dim sName As String
    sName = txtName.Text
    If chkUpper.Value = vbChecked Then sName = UCase(sName)
    mCount = mCount + 1
    lblResult.Caption = "Hello, " & sName & "! (#" & mCount & ")"
    lstLog.AddItem sName
End Sub

Private Sub Timer1_Timer()
    lblClock.Caption = Format(Now, "hh:nn:ss")
End Sub

Private Sub mnuFileClear_Click()
    lstLog.Clear
End Sub

Private Sub mnuFileExit_Click()
    Unload Me
End Sub

Private Sub mnuHelpAbout_Click()
    MsgBox "Made with RAD IDE - VB6 lives again!", vbInformation, "About"
End Sub
"""


def build_vb() -> Path:
    folder = build("HelloVB", "vb-basic", skip_code=True)
    (folder / "Form1.bas").write_text(VB_CODE, encoding="utf-8")
    plugin = get_plugin("vb-basic")
    f = Form.load(folder / "Form1.form")
    (folder / plugin.designer_file("Form1")).write_text(plugin.generate_designer(f, VB_CODE), encoding="utf-8")
    return folder


if __name__ == "__main__":
    for name, lang in (("HelloPython", "python-tk"), ("HelloRing", "ring-qt")):
        print("created", build(name, lang))
    print("created", build_vb())
