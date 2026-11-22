# (c) 2026 Musoftware - https://musoftwares.com - MIT License
r"""Layout of the Perl / Lua / Ruby / PowerShell example forms (samples/Examples/<Language>/<Name>).

    .venv\Scripts\python samples\Tests\Examples\make_scripts.py [name-filter ...]

A missing project is created the way File > New Project does (exlib.create, extra forms, Project > Add Module);
an existing one only gets its forms laid out again and its designer files regenerated - the hand-written code
files are never touched."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exlib  # noqa: E402
from radide.model import Project  # noqa: E402
from radide.workspace import add_module  # noqa: E402

E = exlib.EXAMPLES


def C(t, name, x, y, w=None, h=None, **kw):
    d = {"type": t, "name": name, "x": x, "y": y}
    if w is not None:
        d["w"], d["h"] = w, h
    if t == "TextBox":
        kw.setdefault("Text", "")
    d.update(kw)
    return d


def menu(*tops):
    items = []
    for text, name, subs in tops:
        items.append({"Text": text, "Name": name,
                      "Items": [{"Text": "-"} if s == "-" else {"Text": s[0], "Name": s[1]} for s in subs]})
    return C("MenuStrip", "MenuStrip1", 0, 0, Items=items)


F = dict(StartPosition="CenterScreen")
PROJECTS = {}

# ----------------------------------------------------------------- Perl
PROJECTS["Perl/TextStats"] = ("perl-bridge", {
    "Form1": (dict(F, Text="Text Statistics - Perl", Width=640, Height=500), [
        menu(("File", "mnuFile", [("Open...", "mnuFileOpen"), ("Clear", "mnuFileClear"), "-", ("Exit", "mnuFileExit")]),
             ("Help", "mnuHelp", [("About", "mnuHelpAbout")])),
        C("Label", "lblText", 12, 30, 200, 20, Text="Text (paste or File > Open):"),
        C("TextBox", "txtInput", 12, 52, 380, 200, Multiline=True, Text=""),
        C("Button", "cmdAnalyze", 12, 260, 110, 28, Text="Analyze"),
        C("Label", "lblStats", 130, 264, 262, 22, Text="Words: 0   Lines: 0   Chars: 0"),
        C("Label", "lblTop", 404, 30, 220, 20, Text="Top words:"),
        C("DataGridView", "grdWords", 404, 52, 220, 236, Columns="Rank;Word;Count", ReadOnly=True),
        C("Label", "lblPattern", 12, 302, 120, 20, Text="Regex pattern:"),
        C("TextBox", "txtPattern", 130, 300, 262, 24, Text=r"\b\w{6,}\b"),
        C("CheckBox", "chkIgnoreCase", 404, 300, 120, 24, Text="Ignore case", Checked=True),
        C("Button", "cmdFind", 530, 298, 94, 28, Text="Find"),
        C("ListBox", "lstMatches", 12, 334, 612, 100),
        C("StatusBar", "sbStatus", 0, 440, 640, 22, Text="Ready", Dock="Bottom"),
        C("OpenFileDialog", "dlgOpen", 0, 0, Title="Open a text file", Filter="Text files (*.txt)|*.txt|All files (*.*)|*.*"),
    ])}, ["TextTools.pl"])

PROJECTS["Perl/ExpenseTracker"] = ("perl-bridge", {
    "Form1": (dict(F, Text="Expense Tracker - Perl", Width=660, Height=500), [
        menu(("File", "mnuFile", [("Save", "mnuFileSave"), ("Reload", "mnuFileReload"), "-", ("Exit", "mnuFileExit")]),
             ("Report", "mnuReport", [("Totals by category", "mnuReportTotals")])),
        C("Label", "lblDate", 12, 32, 60, 20, Text="Date:"),
        C("TextBox", "txtDate", 70, 30, 100, 24),
        C("Label", "lblItem", 180, 32, 40, 20, Text="Item:"),
        C("TextBox", "txtItem", 222, 30, 160, 24),
        C("Label", "lblAmount", 392, 32, 60, 20, Text="Amount:"),
        C("TextBox", "txtAmount", 450, 30, 80, 24),
        C("ComboBox", "cboCategory", 70, 62, 160, 24, Items="Food;Transport;Bills;Shopping;Health;Other"),
        C("Label", "lblCat", 12, 64, 60, 20, Text="Category:"),
        C("Button", "cmdAdd", 540, 28, 100, 28, Text="Add"),
        C("Button", "cmdDelete", 540, 60, 100, 28, Text="Delete row"),
        C("DataGridView", "grdExpenses", 12, 98, 420, 320, Columns="Date;Item;Category;Amount", ReadOnly=True),
        C("Label", "lblByCat", 444, 98, 196, 20, Text="By category:"),
        C("ListBox", "lstTotals", 444, 120, 196, 260),
        C("Label", "lblTotal", 444, 390, 196, 28, Text="Total: 0.00", FontBold=True, FontSize=11),
        C("StatusBar", "sbStatus", 0, 440, 660, 22, Text="", Dock="Bottom"),
    ])}, ["ExpenseStore.pl"])

PROJECTS["Perl/LogViewer"] = ("perl-bridge", {
    "Form1": (dict(F, Text="Log Viewer - Perl", Width=680, Height=480), [
        menu(("File", "mnuFile", [("Clear view", "mnuFileClear"), "-", ("Exit", "mnuFileExit")]),
             ("Tools", "mnuTools", [("Write test lines", "mnuToolsSimulate"), ("Go to line...", "mnuToolsGoto")])),
        C("Label", "lblFilter", 12, 32, 50, 20, Text="Filter:"),
        C("TextBox", "txtFilter", 64, 30, 220, 24),
        C("ComboBox", "cboLevel", 294, 30, 110, 24, Items="ALL;INFO;WARN;ERROR"),
        C("CheckBox", "chkFollow", 414, 30, 120, 24, Text="Follow (tail)", Checked=True),
        C("Button", "cmdReload", 544, 28, 120, 28, Text="Reload"),
        C("ListBox", "lstLog", 12, 64, 652, 310, FontName="Consolas"),
        C("Label", "lblCounts", 12, 382, 652, 22, Text="INFO 0  WARN 0  ERROR 0"),
        C("StatusBar", "sbStatus", 0, 420, 680, 22, Text="", Dock="Bottom"),
        C("Timer", "tmrTail", 0, 0, Interval=1000, Enabled=False),
    ])}, [])

# ----------------------------------------------------------------- Lua
keys = []
lay = [("7", "8", "9", "/"), ("4", "5", "6", "*"), ("1", "2", "3", "-"), ("0", ".", "=", "+")]
names = {"/": "Div", "*": "Mul", "-": "Sub", "+": "Add", "=": "Eq", ".": "Dot"}
for r, row in enumerate(lay):
    for c, k in enumerate(row):
        keys.append(C("Button", "cmd" + names.get(k, k), 12 + c * 62, 100 + r * 50, 56, 44, Text=k, FontSize=14))
PROJECTS["Lua/Calculator"] = ("lua-bridge", {
    "Form1": (dict(F, Text="Calculator - Lua", Width=470, Height=360), [
        menu(("Edit", "mnuEdit", [("Clear", "mnuEditClear"), ("Clear history", "mnuEditClearHistory")]),
             ("Help", "mnuHelp", [("Keyboard keys", "mnuHelpKeys")])),
        C("TextBox", "txtDisplay", 12, 32, 242, 32, FontSize=16, Text="0", ReadOnly=True),
        C("Label", "lblExpr", 12, 70, 242, 22, Text=""),
        C("Button", "cmdClear", 260, 32, 56, 32, Text="C", FontSize=12),
        C("Button", "cmdBack", 260, 70, 56, 26, Text="<-"),
        *keys,
        C("Label", "lblHist", 326, 32, 120, 20, Text="History:"),
        C("ListBox", "lstHistory", 326, 54, 128, 240),
    ])}, ["calc.lua"])

PROJECTS["Lua/GuessGame"] = ("lua-bridge", {
    "Form1": (dict(F, Text="Guess the Number - Lua", Width=460, Height=420), [
        menu(("Game", "mnuGame", [("New game", "mnuGameNew"), "-", ("Exit", "mnuGameExit")]),
             ("Level", "mnuLevel", [("Easy (1-50)", "mnuLevelEasy"), ("Normal (1-100)", "mnuLevelNormal"), ("Hard (1-1000)", "mnuLevelHard")])),
        C("Label", "lblTitle", 12, 34, 420, 26, Text="I am thinking of a number from 1 to 100", FontSize=11, FontBold=True),
        C("Label", "lblGuess", 12, 72, 100, 22, Text="Your guess:"),
        C("TextBox", "txtGuess", 112, 70, 100, 26, FontSize=12),
        C("Button", "cmdGuess", 222, 68, 100, 30, Text="Guess"),
        C("Label", "lblHint", 12, 108, 420, 26, Text="", FontSize=12, ForeColor="#1F3D7A"),
        C("ProgressBar", "prgTries", 12, 140, 420, 18, Minimum=0, Maximum=10, Value=0),
        C("Label", "lblTime", 12, 166, 200, 22, Text="Time: 0 s"),
        C("Label", "lblBest", 222, 166, 210, 22, Text="Best: -"),
        C("ListBox", "lstHistory", 12, 194, 420, 160),
        C("Timer", "tmrClock", 0, 0, Interval=1000, Enabled=False),
    ])}, ["scores.lua"])

PROJECTS["Lua/Notes"] = ("lua-bridge", {
    "Form1": (dict(F, Text="Notes - Lua", Width=640, Height=460), [
        menu(("File", "mnuFile", [("New note", "mnuFileNew"), ("Save", "mnuFileSave"), ("Delete", "mnuFileDelete"), "-", ("Exit", "mnuFileExit")]),
             ("Edit", "mnuEdit", [("Find...", "mnuEditFind")])),
        C("ListBox", "lstNotes", 12, 32, 200, 360),
        C("Label", "lblTitle", 224, 32, 50, 22, Text="Title:"),
        C("TextBox", "txtTitle", 276, 30, 340, 24),
        C("TextBox", "txtBody", 224, 62, 392, 300, Multiline=True),
        C("Button", "cmdNew", 224, 368, 90, 28, Text="New"),
        C("Button", "cmdSave", 320, 368, 90, 28, Text="Save"),
        C("Button", "cmdDelete", 416, 368, 90, 28, Text="Delete"),
        C("Label", "lblCount", 512, 372, 104, 22, Text="0 notes"),
        C("StatusBar", "sbStatus", 0, 404, 640, 22, Text="", Dock="Bottom"),
    ]),
    "FindForm": (dict(F, Text="Find", Width=340, Height=150), [
        C("Label", "lblFind", 12, 16, 80, 22, Text="Find text:"),
        C("TextBox", "txtFind", 92, 14, 228, 24),
        C("CheckBox", "chkTitles", 92, 44, 200, 22, Text="Search titles only"),
        C("Button", "cmdOK", 136, 76, 88, 28, Text="Find"),
        C("Button", "cmdCancel", 232, 76, 88, 28, Text="Cancel"),
    ])}, ["notestore.lua"])

# ----------------------------------------------------------------- Ruby
PROJECTS["Ruby/Contacts"] = ("ruby-bridge", {
    "Form1": (dict(F, Text="Contacts - Ruby", Width=700, Height=500), [
        menu(("File", "mnuFile", [("Save", "mnuFileSave"), ("Export CSV", "mnuFileExport"), "-", ("Exit", "mnuFileExit")]),
             ("Help", "mnuHelp", [("About", "mnuHelpAbout")])),
        C("Label", "lblName", 12, 34, 60, 20, Text="Name:"),
        C("TextBox", "txtName", 76, 32, 180, 24),
        C("Label", "lblPhone", 266, 34, 50, 20, Text="Phone:"),
        C("TextBox", "txtPhone", 320, 32, 130, 24),
        C("Label", "lblEmail", 12, 66, 60, 20, Text="Email:"),
        C("TextBox", "txtEmail", 76, 64, 180, 24),
        C("Label", "lblCity", 266, 66, 50, 20, Text="City:"),
        C("TextBox", "txtCity", 320, 64, 130, 24),
        C("Button", "cmdAdd", 462, 30, 100, 28, Text="Add"),
        C("Button", "cmdUpdate", 572, 30, 110, 28, Text="Update"),
        C("Button", "cmdDelete", 462, 62, 100, 28, Text="Delete"),
        C("Button", "cmdClear", 572, 62, 110, 28, Text="Clear fields"),
        C("Label", "lblSearch", 12, 100, 60, 20, Text="Search:"),
        C("TextBox", "txtSearch", 76, 98, 374, 24),
        C("DataGridView", "grdContacts", 12, 130, 670, 280, Columns="#;Name;Phone;Email;City", ReadOnly=True),
        C("StatusBar", "sbStatus", 0, 440, 700, 22, Text="", Dock="Bottom"),
    ])}, ["ContactStore.rb"])

PROJECTS["Ruby/UnitConverter"] = ("ruby-bridge", {
    "Form1": (dict(F, Text="Unit Converter - Ruby", Width=520, Height=400), [
        menu(("Edit", "mnuEdit", [("Swap units", "mnuEditSwap"), ("Clear history", "mnuEditClear")]),
             ("Help", "mnuHelp", [("About", "mnuHelpAbout")])),
        C("Label", "lblCat", 12, 34, 80, 22, Text="Category:"),
        C("ComboBox", "cboCategory", 96, 32, 200, 24, Items="Length;Mass;Temperature;Data;Speed"),
        C("Label", "lblValue", 12, 70, 80, 22, Text="Value:"),
        C("TextBox", "txtValue", 96, 68, 200, 26, FontSize=12, Text="1"),
        C("Label", "lblFrom", 12, 106, 80, 22, Text="From:"),
        C("ComboBox", "cboFrom", 96, 104, 200, 24),
        C("Label", "lblTo", 12, 140, 80, 22, Text="To:"),
        C("ComboBox", "cboTo", 96, 138, 200, 24),
        C("Button", "cmdSwap", 306, 118, 80, 28, Text="Swap"),
        C("Button", "cmdConvert", 396, 118, 100, 28, Text="Convert"),
        C("Label", "lblResult", 12, 176, 484, 30, Text="", FontSize=14, FontBold=True, ForeColor="#1F3D7A"),
        C("ListBox", "lstHistory", 12, 214, 484, 130),
    ])}, ["Units.rb"])

PROJECTS["Ruby/Pomodoro"] = ("ruby-bridge", {
    "Form1": (dict(F, Text="Pomodoro Timer - Ruby", Width=420, Height=420), [
        menu(("Timer", "mnuTimer", [("Start", "mnuTimerStart"), ("Pause", "mnuTimerPause"), ("Reset", "mnuTimerReset"), "-", ("Exit", "mnuTimerExit")]),
             ("Tools", "mnuTools", [("Settings...", "mnuToolsSettings")])),
        C("Label", "lblPhase", 12, 34, 380, 26, Text="Work", FontSize=13, FontBold=True),
        C("Label", "lblClock", 12, 64, 380, 60, Text="25:00", FontSize=36, FontBold=True, TextAlign="Center"),
        C("ProgressBar", "prgPhase", 12, 130, 380, 20, Minimum=0, Maximum=100, Value=0),
        C("Button", "cmdStart", 12, 160, 120, 32, Text="Start"),
        C("Button", "cmdPause", 142, 160, 120, 32, Text="Pause"),
        C("Button", "cmdReset", 272, 160, 120, 32, Text="Reset"),
        C("Label", "lblDone", 12, 202, 380, 22, Text="Completed sessions:"),
        C("ListBox", "lstSessions", 12, 226, 380, 120),
        C("StatusBar", "sbStatus", 0, 360, 420, 22, Text="", Dock="Bottom"),
        C("Timer", "tmrTick", 0, 0, Interval=1000, Enabled=False),
    ]),
    "SettingsForm": (dict(F, Text="Settings", Width=360, Height=250), [
        C("Label", "lblWork", 12, 16, 160, 22, Text="Work minutes:"),
        C("NumericUpDown", "nudWork", 180, 14, 80, 24, Minimum=1, Maximum=90, Value=25),
        C("Label", "lblBreak", 12, 48, 160, 22, Text="Break minutes:"),
        C("NumericUpDown", "nudBreak", 180, 46, 80, 24, Minimum=1, Maximum=30, Value=5),
        C("Label", "lblLang", 12, 80, 160, 22, Text="Language / اللغة:"),
        C("ComboBox", "cboLang", 180, 78, 150, 24, Items="English;العربية"),
        C("CheckBox", "chkAutoBreak", 12, 112, 300, 22, Text="Start the break automatically"),
        C("Button", "cmdOK", 150, 160, 88, 30, Text="OK"),
        C("Button", "cmdCancel", 246, 160, 88, 30, Text="Cancel"),
    ])}, ["PomodoroSettings.rb"])

# ----------------------------------------------------------------- PowerShell
PROJECTS["PowerShell/SystemInfo"] = ("powershell-bridge", {
    "Form1": (dict(F, Text="System Info - PowerShell", Width=680, Height=500), [
        menu(("File", "mnuFile", [("Refresh", "mnuFileRefresh"), ("Save report...", "mnuFileSave"), "-", ("Exit", "mnuFileExit")]),
             ("View", "mnuView", [("Auto refresh", "mnuViewAuto")])),
        C("DataGridView", "grdInfo", 12, 32, 400, 250, Columns="Group;Property;Value", ReadOnly=True),
        C("Label", "lblProc", 424, 32, 240, 20, Text="Top processes (memory):"),
        C("ListBox", "lstProcesses", 424, 54, 240, 228, FontName="Consolas"),
        C("Label", "lblMem", 12, 294, 200, 20, Text="Memory in use:"),
        C("ProgressBar", "prgMemory", 12, 316, 400, 20, Minimum=0, Maximum=100),
        C("Label", "lblMemText", 424, 316, 240, 20, Text=""),
        C("Label", "lblDisk", 12, 346, 200, 20, Text="Drives:"),
        C("ListBox", "lstDrives", 12, 368, 400, 70, FontName="Consolas"),
        C("Button", "cmdRefresh", 424, 368, 120, 30, Text="Refresh"),
        C("Label", "lblClock", 554, 372, 110, 22, Text=""),
        C("StatusBar", "sbStatus", 0, 450, 680, 22, Text="", Dock="Bottom"),
        C("Timer", "tmrClock", 0, 0, Interval=1000, Enabled=True),
        C("SaveFileDialog", "dlgSave", 0, 0, Title="Save report", Filter="Text files (*.txt)|*.txt"),
    ])}, ["SysInfo.ps1"])

PROJECTS["PowerShell/FileOrganizer"] = ("powershell-bridge", {
    "Form1": (dict(F, Text="File Organizer (preview) - PowerShell", Width=700, Height=500), [
        menu(("File", "mnuFile", [("Choose folder...", "mnuFileBrowse"), ("Export plan (CSV)", "mnuFileExport"), "-", ("Exit", "mnuFileExit")]),),
        C("Label", "lblFolder", 12, 34, 60, 20, Text="Folder:"),
        C("TextBox", "txtFolder", 72, 32, 400, 24),
        C("Button", "cmdBrowse", 480, 30, 90, 28, Text="Browse..."),
        C("Button", "cmdScan", 580, 30, 100, 28, Text="Scan"),
        C("CheckBox", "chkRecurse", 72, 62, 200, 22, Text="Include sub-folders"),
        C("DataGridView", "grdTypes", 12, 92, 330, 320, Columns="Extension;Files;Size (KB);Target folder", ReadOnly=True),
        C("Label", "lblPlan", 352, 92, 328, 20, Text="Plan (nothing is moved - preview only):"),
        C("ListBox", "lstPlan", 352, 114, 328, 298, FontName="Consolas"),
        C("StatusBar", "sbStatus", 0, 440, 700, 22, Text="", Dock="Bottom"),
        C("FolderBrowserDialog", "dlgFolder", 0, 0),
    ])}, ["Organizer.ps1"])

PROJECTS["PowerShell/PasswordGen"] = ("powershell-bridge", {
    "Form1": (dict(F, Text="Password Generator - PowerShell", Width=520, Height=420), [
        menu(("Edit", "mnuEdit", [("Copy password", "mnuEditCopy"), ("Clear history", "mnuEditClear")]),
             ("Help", "mnuHelp", [("About", "mnuHelpAbout")])),
        C("Label", "lblLen", 12, 34, 80, 22, Text="Length:"),
        C("NumericUpDown", "nudLength", 96, 32, 70, 24, Minimum=4, Maximum=64, Value=16),
        C("CheckBox", "chkUpper", 12, 64, 140, 22, Text="A-Z", Checked=True),
        C("CheckBox", "chkLower", 160, 64, 140, 22, Text="a-z", Checked=True),
        C("CheckBox", "chkDigits", 12, 90, 140, 22, Text="0-9", Checked=True),
        C("CheckBox", "chkSymbols", 160, 90, 140, 22, Text="!@#$%", Checked=False),
        C("Button", "cmdGenerate", 320, 30, 170, 32, Text="Generate"),
        C("Button", "cmdCopy", 320, 70, 170, 32, Text="Copy to clipboard"),
        C("TextBox", "txtPassword", 12, 122, 478, 30, FontName="Consolas", FontSize=13),
        C("ProgressBar", "prgStrength", 12, 160, 300, 18, Minimum=0, Maximum=100),
        C("Label", "lblStrength", 320, 158, 170, 22, Text=""),
        C("Label", "lblStrengthAr", 12, 184, 478, 22, Text="قوة كلمة المرور: -"),
        C("ListBox", "lstHistory", 12, 212, 478, 130, FontName="Consolas"),
    ])}, ["PwTools.ps1"])


def main(only=()):
    for key, (lang, forms, modules) in PROJECTS.items():
        if only and not any(o in key for o in only):
            continue
        folder = E / key
        new = not (folder / "project.radproj").exists()
        if new:
            p = exlib.create(folder, folder.name, lang)
            for fname in forms:
                if fname != "Form1":
                    exlib.add_form(p, fname)
            for m in modules:
                add_module(p, Path(m).stem, filename=m)
        p = Project.load(folder)
        for fname, (props, controls) in forms.items():
            exlib.make_form(p, fname, props, controls, regen=False)
        exlib.regen_all(folder)
        print(("created " if new else "re-laid ") + key)


if __name__ == "__main__":
    main(sys.argv[1:])
