"""Writes the VB6 test projects of the native (FreeBASIC) build that are made in code:

    ControlsGallery  every control type the native forms runtime supports + their events (log to lstLog)
    MultiForm        two forms: modal Form2, cross-form access, Unload / QueryUnload Cancel, a module
    ArabicForm       Arabic captions / text, Len / Mid on Arabic, Format, a control array
    AnchorsDock      Anchor / Dock on resize (the geometry must follow like in the designer)

    .venv\\Scripts\\python samples\\Tests\\Native\\VB6\\make_projects.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from radide.model import Form  # noqa: E402


def ctl(form, typ, name, x, y, w, h, parent="", **props):
    c = form.add(typ, x, y, parent)
    c.props["Name"] = name
    if "Width" in c.props:
        c.props["Width"], c.props["Height"] = w, h
    if "Text" in c.props and "Text" not in props:
        c.props["Text"] = name
    c.props.update(props)
    return c


def write(name, forms, code, modules=None, startup=None):
    d = HERE / name
    d.mkdir(exist_ok=True)
    for fname, form in forms:
        form.props["Name"] = fname
        form.save(d / f"{fname}.form")
        (d / f"{fname}.bas").write_text(code[fname].strip("\n") + "\n", encoding="utf-8")
    for mname, src in (modules or {}).items():
        (d / mname).write_text(src.strip("\n") + "\n", encoding="utf-8")
    (d / "project.radproj").write_text(json.dumps({
        "name": name, "language": "vb-basic", "forms": [f for f, _ in forms],
        "startup": startup or forms[0][0], "modules": list(modules or {})}, indent=2), encoding="utf-8")


def gallery():
    f = Form()
    f.props.update(Text="Controls Gallery", Width=640, Height=460)
    ctl(f, "MenuStrip", "MenuStrip1", 0, 0, 0, 0, Items=[
        {"Text": "&File", "Name": "mnuFile", "Items": [{"Text": "&Clear log	Ctrl+L", "Name": "mnuClear"},
                                                       {"Text": "-"}, {"Text": "E&xit", "Name": "mnuExit"}]},
        {"Text": "&Options", "Name": "mnuOptions", "Items": [{"Text": "&Checked item", "Name": "mnuCheck"}]}])
    ctl(f, "Label", "lblTitle", 8, 6, 300, 24, Text="All controls", FontSize=12, FontBold=True, ForeColor="#1F3D7A")
    ctl(f, "Button", "cmdHello", 8, 36, 96, 28, Text="&Hello", ToolTip="Says hello")
    ctl(f, "Button", "cmdColor", 112, 36, 96, 28, Text="Colour", BackColor="#FFD75E")
    ctl(f, "TextBox", "txtName", 8, 72, 200, 22, Text="World", MaxLength=20)
    ctl(f, "TextBox", "txtPass", 8, 100, 200, 22, Text="secret", PasswordChar="*")
    ctl(f, "TextBox", "txtMulti", 8, 128, 200, 60, Text="line 1\r\nline 2", Multiline=True)
    ctl(f, "TextBox", "txtRO", 8, 194, 200, 22, Text="read only", ReadOnly=True)
    ctl(f, "CheckBox", "chkBold", 8, 222, 120, 20, Text="Bold title")
    ctl(f, "GroupBox", "fraSize", 8, 246, 200, 70, Text="Size")
    ctl(f, "RadioButton", "optSmall", 10, 20, 80, 20, parent="fraSize", Text="Small", Checked=True)
    ctl(f, "RadioButton", "optLarge", 100, 20, 80, 20, parent="fraSize", Text="Large")
    ctl(f, "Panel", "pnlColors", 8, 322, 200, 56, BackColor="#DDE7F5")
    ctl(f, "RadioButton", "optRed", 8, 6, 80, 20, parent="pnlColors", Text="Red")
    ctl(f, "RadioButton", "optBlue", 8, 28, 80, 20, parent="pnlColors", Text="Blue", Checked=True)
    ctl(f, "Label", "lblPanel", 100, 16, 90, 20, parent="pnlColors", Text="in a panel")
    ctl(f, "ListBox", "lstLog", 220, 36, 200, 150, Items="ready")
    ctl(f, "ComboBox", "cboFruit", 220, 192, 200, 21, Items="Apple;Banana;Cherry", DropDownStyle="DropDownList")
    ctl(f, "ComboBox", "cboFree", 220, 220, 200, 21, Items="one;two", DropDownStyle="DropDown", Text="typed")
    ctl(f, "ProgressBar", "prgDone", 220, 250, 200, 18, Value=30)
    ctl(f, "NumericUpDown", "updCount", 220, 274, 90, 22, Minimum=0, Maximum=10, Value=3)
    ctl(f, "TrackBar", "trkLevel", 220, 300, 200, 40, Minimum=0, Maximum=20, Value=5)
    ctl(f, "LinkLabel", "lnkSite", 220, 346, 150, 20, Text="Visit the site")
    ctl(f, "DateTimePicker", "dtpWhen", 220, 372, 200, 22, Value="2024-03-05", Format="Short")
    ctl(f, "PictureBox", "picLogo", 430, 36, 96, 96, Image="logo.png", BackColor="#FFFFFF")
    ctl(f, "TabControl", "tabMain", 430, 140, 200, 130, TabPages="First;Second")
    ctl(f, "Label", "lblPage1", 8, 8, 150, 20, parent="tabMain", Text="on page one", TabPage=0)
    ctl(f, "Button", "cmdPage2", 8, 8, 120, 26, parent="tabMain", Text="Page two button", TabPage=1)
    for i in range(3):
        ctl(f, "Button", f"cmdNum{i}", 430 + i * 66, 280, 60, 26, Text=f"#{i}", ArrayName="cmdNum", ArrayIndex=i)
    ctl(f, "Label", "lblStatus", 430, 312, 200, 20, Text="-")
    ctl(f, "StatusBar", "staMain", 0, 438, 640, 22, Text="Status: ready", Dock="Bottom")
    ctl(f, "Timer", "tmrTick", 0, 0, 0, 0, Interval=200, Enabled=False)
    ctl(f, "OpenFileDialog", "dlgOpen", 0, 0, 0, 0, Filter="Text files|*.txt|All files|*.*")
    code = r'''
Option Explicit
Private ticks As Integer

Private Sub Log(ByVal s As String)
    lstLog.AddItem s
    lstLog.ListIndex = lstLog.ListCount - 1
    Debug.Print s
End Sub

Private Sub Form_Load()
    Log "load " & Me.Caption
    Log "date " & Format(dtpWhen.Value, "yyyy-mm-dd") & " " & dtpWhen.Year
    lblStatus.Caption = "count=" & updCount.Value
End Sub

Private Sub cmdHello_Click()
    Log "Hello, " & txtName.Text & " (" & Len(txtName.Text) & ")"
    staMain.SimpleText = "said hello"
End Sub

Private Sub cmdColor_Click()
    If lblTitle.ForeColor = RGB(200, 0, 0) Then
        lblTitle.ForeColor = RGB(31, 61, 122)
    Else
        lblTitle.ForeColor = RGB(200, 0, 0)
    End If
    Log "colour " & lblTitle.ForeColor
End Sub

Private Sub chkBold_Click()
    lblTitle.FontBold = (chkBold.Value = vbChecked)
    Log "bold " & chkBold.Value
End Sub

Private Sub optSmall_Click()
    Log "small"
End Sub

Private Sub optLarge_Click()
    Log "large"
End Sub

Private Sub optRed_Click()
    pnlColors.BackColor = RGB(255, 220, 220)
    Log "red"
End Sub

Private Sub optBlue_Click()
    pnlColors.BackColor = RGB(221, 231, 245)
    Log "blue"
End Sub

Private Sub txtName_Change()
    lblStatus.Caption = "typed " & txtName.Text
End Sub

Private Sub txtName_KeyPress(KeyAscii As Integer)
    If KeyAscii >= 97 And KeyAscii <= 122 Then KeyAscii = KeyAscii - 32
End Sub

Private Sub cboFruit_Click()
    Log "fruit " & cboFruit.Text & " #" & cboFruit.ListIndex
End Sub

Private Sub lstLog_DblClick()
    Log "dbl " & lstLog.Text
End Sub

Private Sub updCount_Change()
    lblStatus.Caption = "count=" & updCount.Value
    prgDone.Value = updCount.Value * 10
End Sub

Private Sub trkLevel_Change()
    lblStatus.Caption = "level=" & trkLevel.Value
End Sub

Private Sub dtpWhen_Change()
    Log "date changed " & dtpWhen.Day
End Sub

Private Sub lnkSite_Click()
    Log "link"
End Sub

Private Sub picLogo_MouseDown(Button As Integer, Shift As Integer, X As Single, Y As Single)
    Log "mouse " & Button & " " & X & "," & Y
End Sub

Private Sub cmdNum_Click(Index As Integer)
    Log "num " & Index & " " & cmdNum(Index).Caption
    cmdNum(Index).Caption = "*" & Index
End Sub

Private Sub cmdPage2_Click()
    tabMain.Tab = 0
    Log "page2 button, tab=" & tabMain.Tab
End Sub

Private Sub tabMain_Click(PreviousTab As Integer)
    Log "tab " & PreviousTab & "->" & tabMain.Tab
End Sub

Private Sub tmrTick_Timer()
    ticks = ticks + 1
    If ticks >= 3 Then
        tmrTick.Enabled = False
        Log "ticks " & ticks
    End If
End Sub

Private Sub mnuClear_Click()
    lstLog.Clear
    Log "cleared"
    tmrTick.Enabled = True
End Sub

Private Sub mnuCheck_Click()
    mnuCheck.Checked = Not mnuCheck.Checked
    Log "checked " & mnuCheck.Checked
End Sub

Private Sub mnuExit_Click()
    Unload Me
End Sub

Private Sub Form_Resize()
    lblStatus.Caption = "size " & Me.ScaleWidth & "x" & Me.ScaleHeight
End Sub
'''
    write("ControlsGallery", [("Form1", f)], {"Form1": code})
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        dr.ellipse((4, 4, 60, 60), fill=(31, 61, 122, 255))
        dr.rectangle((24, 18, 40, 46), fill=(255, 215, 94, 255))
        img.save(HERE / "ControlsGallery" / "logo.png")
    except ImportError:
        pass


def multiform():
    f1 = Form()
    f1.props.update(Text="Main form", Width=360, Height=200)
    ctl(f1, "Label", "lblPrompt", 12, 14, 80, 20, Text="Name:")
    ctl(f1, "TextBox", "txtName", 96, 12, 160, 22, Text="Sam")
    ctl(f1, "Button", "cmdAsk", 264, 10, 84, 26, Text="Ask...")
    ctl(f1, "Label", "lblResult", 12, 52, 336, 20, Text="(nothing yet)")
    ctl(f1, "CheckBox", "chkKeep", 12, 84, 200, 20, Text="Refuse to close")
    ctl(f1, "Button", "cmdClose", 264, 160, 84, 26, Text="Close")
    f2 = Form()
    f2.props.update(Text="Question", Width=300, Height=140, FormBorderStyle="FixedSingle")
    ctl(f2, "Label", "lblQ", 12, 12, 276, 20, Text="?")
    ctl(f2, "TextBox", "txtAnswer", 12, 40, 276, 22, Text="")
    ctl(f2, "Button", "cmdOK", 120, 100, 80, 26, Text="OK")
    ctl(f2, "Button", "cmdCancel", 208, 100, 80, 26, Text="Cancel")
    code1 = r'''
Option Explicit

Private Sub cmdAsk_Click()
    Form2.lblQ.Caption = "Favourite colour of " & txtName.Text & "?"
    Form2.Show vbModal
    lblResult.Caption = "answer: " & Answer & " (shown " & ShownCount & ")"
    Debug.Print lblResult.Caption
End Sub

Private Sub cmdClose_Click()
    Unload Me
End Sub

Private Sub Form_QueryUnload(Cancel As Integer, UnloadMode As Integer)
    Debug.Print "queryunload " & UnloadMode
    If chkKeep.Value = vbChecked Then
        Cancel = 1
        lblResult.Caption = "refused"
    End If
End Sub

Private Sub Form_Unload(Cancel As Integer)
    Debug.Print "unload main"
End Sub
'''
    code2 = r'''
Option Explicit

Private Sub Form_Load()
    ShownCount = ShownCount + 1
    Me.Caption = "Question #" & ShownCount
    txtAnswer.Text = ""
End Sub

Private Sub cmdOK_Click()
    Answer = txtAnswer.Text
    Form1.lblResult.Caption = "set by Form2"
    Unload Me
End Sub

Private Sub cmdCancel_Click()
    Answer = "(cancelled)"
    Unload Me
End Sub
'''
    mod = r'''
Public Answer As String
Public ShownCount As Integer
'''
    write("MultiForm", [("Form1", f1), ("Form2", f2)], {"Form1": code1, "Form2": code2}, {"Module1.bas": mod})


def arabic():
    f = Form()
    f.props.update(Text="برنامج عربي", Width=380, Height=220, BackColor="#F7F3E8")
    ctl(f, "Label", "lblTitle", 12, 10, 356, 28, Text="مرحبا بكم في البرنامج", FontSize=14, TextAlign="Right")
    ctl(f, "TextBox", "txtName", 120, 48, 248, 24, Text="محمد", TextAlign="Right")
    ctl(f, "Label", "lblName", 12, 50, 100, 20, Text="الاسم:")
    ctl(f, "Button", "cmdGreet", 268, 84, 100, 28, Text="ترحيب")
    ctl(f, "Label", "lblOut", 12, 124, 356, 24, Text="", TextAlign="Right")
    for i, cap in enumerate(["واحد", "اثنان", "ثلاثة"]):
        ctl(f, "Button", f"cmdN{i}", 12 + i * 84, 160, 78, 28, Text=cap, ArrayName="cmdN", ArrayIndex=i)
    code = r'''
Option Explicit

Private Sub cmdGreet_Click()
    Dim s As String
    s = txtName.Text
    lblOut.Caption = "أهلا يا " & s & " (" & Len(s) & " حروف)، أول حرف: " & Left(s, 1)
    Debug.Print lblOut.Caption
End Sub

Private Sub cmdN_Click(Index As Integer)
    lblOut.Caption = "اخترت " & cmdN(Index).Caption & " = " & (Index + 1)
    Debug.Print lblOut.Caption
End Sub
'''
    write("ArabicForm", [("Form1", f)], {"Form1": code})


def anchors():
    f = Form()
    f.props.update(Text="Anchors and Dock", Width=400, Height=300)
    ctl(f, "Panel", "pnlTop", 0, 0, 400, 40, Dock="Top", BackColor="#DDE7F5")
    ctl(f, "Label", "lblTop", 8, 10, 200, 20, parent="pnlTop", Text="docked at the top")
    ctl(f, "TextBox", "txtWide", 8, 52, 384, 22, Anchor="Top, Left, Right", Text="stretches")
    ctl(f, "ListBox", "lstFill", 8, 82, 300, 160, Anchor="Top, Bottom, Left, Right", Items="a;b;c")
    ctl(f, "Button", "cmdRight", 316, 82, 76, 26, Anchor="Top, Right", Text="Right")
    ctl(f, "Button", "cmdCorner", 316, 216, 76, 26, Anchor="Bottom, Right", Text="Corner")
    ctl(f, "StatusBar", "staBottom", 0, 278, 400, 22, Dock="Bottom", Text="bottom")
    code = r'''
Private Sub cmdRight_Click()
    Me.Width = Me.Width + 100
    Me.Height = Me.Height + 50
    Debug.Print Me.ScaleWidth, Me.ScaleHeight, txtWide.Width, lstFill.Height, cmdCorner.Left, cmdCorner.Top
End Sub
'''
    write("AnchorsDock", [("Form1", f)], {"Form1": code})


if __name__ == "__main__":
    gallery()
    multiform()
    arabic()
    anchors()
    print("written")
