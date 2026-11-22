# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Form layouts shared by the compiled-language examples (samples/Examples/<C|Cpp|CSharp|Java|Go|Rust|Fortran>).

Every example of the same kind (Notepad, Calculator, Contacts, SalesChart, StarCatcher, SettingsDemo) uses the same
neutral .form layout, so the same window works in every language and the examples are easy to compare.

    .venv\\Scripts\\python samples/Tests/Examples/compiled_layouts.py <Language> <Kind> [--force]

creates samples/Examples/<Language>/<Kind> exactly like File > New Project does (radide.workspace.create_project),
renames Form1, adds the other forms and lays them out through radide.model (Form.add = the toolbox defaults).
The code files are written by hand afterwards (an existing project is never overwritten without --force).
WordStats (console tools) has no form: make_console() creates the project with one module that has main().
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXAMPLES = ROOT / "samples" / "Examples"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LANG_IDS = {"C": "c-bridge", "Cpp": "cpp-bridge", "CSharp": "csharp-bridge", "Java": "java-bridge",
            "Go": "go-bridge", "Rust": "rust-bridge", "Fortran": "fortran-bridge"}

FONT = {"FontName": "Segoe UI", "FontSize": 9}


def C(type_, name, x=0, y=0, w=None, h=None, **props):
    d = {"type": type_, "name": name, "x": x, "y": y, **props}
    if w is not None:
        d["w"] = w
    if h is not None:
        d["h"] = h
    return d


def menu(*items):
    """menu(("&File", "mnuFile", [("&New", "mnuNew"), "-", ...]), ...) -> MenuStrip Items."""
    def conv(it):
        if it == "-":
            return {"Text": "-"}
        text, name, *sub = it
        d = {"Text": text, "Name": name}
        if sub:
            d["Items"] = [conv(s) for s in sub[0]]
        return d
    return [conv(i) for i in items]


# ============================================================================ Notepad
def notepad():
    items = menu(("&File", "mnuFile", [("&New", "mnuNew"), ("&Open...", "mnuOpen"), ("&Save", "mnuSave"),
                                       ("Save &As...", "mnuSaveAs"), "-", ("E&xit", "mnuExit")]),
                 ("&Edit", "mnuEdit", [("Cu&t", "mnuCut"), ("&Copy", "mnuCopy"), ("&Paste", "mnuPaste"), "-",
                                       ("Select &All", "mnuSelectAll"), ("&Find...", "mnuFind"),
                                       ("Find &Next", "mnuFindNext"), ("&Replace...", "mnuReplace"), "-",
                                       ("Time/&Date", "mnuTimeDate")]),
                 ("F&ormat", "mnuFormat", [("&Font...", "mnuFont"), ("&Word count", "mnuWordCount")]),
                 ("&Help", "mnuHelp", [("&About", "mnuAbout")]))
    form = {"Text": "Untitled - Notepad", "Width": 640, "Height": 460, "StartPosition": "CenterScreen"}
    ctrls = [C("MenuStrip", "mnuMain", Items=items),
             C("TextBox", "txtDoc", 0, 0, 624, 376, Multiline=True, Text="", FontName="Consolas", FontSize=11,
               Anchor="Top, Bottom, Left, Right"),
             C("StatusBar", "sbStatus", 0, 380, 624, 22, Text="Ready", Anchor="Bottom, Left, Right"),
             C("OpenFileDialog", "dlgOpen", Title="Open a text file", Filter="Text files|*.txt|All files|*.*"),
             C("SaveFileDialog", "dlgSave", Title="Save the text file", Filter="Text files|*.txt|All files|*.*"),
             C("FontDialog", "dlgFont")]
    return {"frmMain": (form, ctrls)}


# ============================================================================ Calculator
def calculator():
    form = {"Text": "Calculator", "Width": 300, "Height": 400, "StartPosition": "CenterScreen",
            "FormBorderStyle": "FixedSingle"}
    ctrls = [C("Label", "lblExpr", 12, 8, 260, 18, Text="", TextAlign="Right", ForeColor="#606060"),
             C("Label", "lblDisplay", 12, 28, 260, 40, Text="0", TextAlign="Right", FontSize=20,
               BackColor="#FFFFFF"),
             C("Label", "lblMemory", 12, 72, 260, 16, Text="", ForeColor="#2060C0", FontSize=8)]
    grid = [[("MC", "btnMC"), ("MR", "btnMR"), ("M+", "btnMPlus"), ("C", "btnClear")],
            [("7", "btn7"), ("8", "btn8"), ("9", "btn9"), ("/", "btnDiv")],
            [("4", "btn4"), ("5", "btn5"), ("6", "btn6"), ("*", "btnMul")],
            [("1", "btn1"), ("2", "btn2"), ("3", "btn3"), ("-", "btnSub")],
            [("0", "btn0"), (".", "btnDot"), ("=", "btnEquals"), ("+", "btnAdd")],
            [("+/-", "btnSign"), ("sqrt", "btnSqrt"), ("%", "btnPercent"), ("<-", "btnBack")]]
    for r, row in enumerate(grid):
        for col, (text, name) in enumerate(row):
            ctrls.append(C("Button", name, 12 + col * 66, 96 + r * 44, 60, 38, Text=text, FontSize=12))
    return {"frmCalc": (form, ctrls)}


# ============================================================================ Contacts
def contacts():
    form = {"Text": "Contacts", "Width": 600, "Height": 420, "StartPosition": "CenterScreen"}
    ctrls = [C("Label", "lblSearch", 12, 15, 50, 17, Text="Search:"),
             C("TextBox", "txtSearch", 64, 12, 168, 20, Text=""),
             C("Button", "btnFind", 240, 10, 70, 24, Text="Find"),
             C("Button", "btnShowAll", 316, 10, 70, 24, Text="Show all"),
             C("ListBox", "lstContacts", 12, 44, 220, 300),
             C("GroupBox", "grpDetails", 244, 44, 330, 210, Text="Details"),
             C("Label", "lblName", 12, 28, 60, 17, Text="Name:", parent="grpDetails"),
             C("TextBox", "txtName", 80, 25, 230, 20, Text="", parent="grpDetails"),
             C("Label", "lblPhone", 12, 60, 60, 17, Text="Phone:", parent="grpDetails"),
             C("TextBox", "txtPhone", 80, 57, 230, 20, Text="", parent="grpDetails"),
             C("Label", "lblEmail", 12, 92, 60, 17, Text="E-mail:", parent="grpDetails"),
             C("TextBox", "txtEmail", 80, 89, 230, 20, Text="", parent="grpDetails"),
             C("Label", "lblGroup", 12, 124, 60, 17, Text="Group:", parent="grpDetails"),
             C("ComboBox", "cboGroup", 80, 121, 150, 21, Items="Family;Friends;Work;Other", parent="grpDetails"),
             C("CheckBox", "chkFavorite", 80, 156, 150, 20, Text="Favourite", parent="grpDetails"),
             C("Button", "btnNew", 244, 266, 100, 28, Text="New"),
             C("Button", "btnSave", 354, 266, 100, 28, Text="Save"),
             C("Button", "btnDelete", 464, 266, 100, 28, Text="Delete"),
             C("Label", "lblCount", 244, 310, 330, 17, Text=""),
             C("StatusBar", "sbStatus", 0, 360, 584, 22, Text="Ready", Anchor="Bottom, Left, Right")]
    return {"frmContacts": (form, ctrls)}


# ============================================================================ SalesChart
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]


def sales_chart():
    form = {"Text": "Sales Chart", "Width": 600, "Height": 400, "StartPosition": "CenterScreen"}
    ctrls = [C("Panel", "pnlChart", 12, 12, 380, 320, BackColor="#FFFFFF", BorderStyle="FixedSingle")]
    for i in range(6):
        x = 14 + i * 60
        ctrls += [C("Panel", f"pnlBar{i + 1}", x, 150, 44, 130, BackColor="#3B7DD8", parent="pnlChart"),
                  C("Label", f"lblVal{i + 1}", x - 4, 130, 52, 17, Text="50", TextAlign="Center",
                    BackColor="#FFFFFF", parent="pnlChart"),
                  C("Label", f"lblMon{i + 1}", x - 4, 288, 52, 17, Text=MONTHS[i], TextAlign="Center",
                    BackColor="#FFFFFF", parent="pnlChart")]
    ctrls += [C("Label", "lblMonth", 404, 16, 60, 17, Text="Month:"),
              C("ComboBox", "cboMonth", 470, 13, 100, 21, Items=";".join(MONTHS)),
              C("Label", "lblValue", 404, 48, 60, 17, Text="Value:"),
              C("NumericUpDown", "nudValue", 470, 45, 100, 20, Minimum=0, Maximum=100, Value=50),
              C("Button", "btnSet", 404, 78, 166, 26, Text="Set value"),
              C("Button", "btnRandom", 404, 112, 166, 26, Text="Random data"),
              C("Button", "btnColor", 404, 146, 166, 26, Text="Bar colour..."),
              C("Button", "btnSave", 404, 180, 80, 26, Text="Save"),
              C("Button", "btnLoad", 490, 180, 80, 26, Text="Load"),
              C("CheckBox", "chkAnimate", 404, 216, 166, 20, Text="Animate (timer)"),
              C("Label", "lblSpeed", 404, 242, 166, 17, Text="Speed:"),
              C("TrackBar", "trkSpeed", 404, 260, 166, 40, Minimum=1, Maximum=10, Value=5),
              C("Label", "lblStats", 12, 338, 560, 17, Text=""),
              C("Label", "lblHint", 404, 304, 176, 30, Text="Click inside the chart to set a bar.",
                ForeColor="#606060", FontSize=8),
              C("ColorDialog", "dlgColor", Color="#3B7DD8"),
              C("Timer", "tmrAnim", Interval=40, Enabled=False)]
    return {"frmChart": (form, ctrls)}


# ============================================================================ StarCatcher (game)
def star_catcher():
    form = {"Text": "Star Catcher", "Width": 480, "Height": 440, "StartPosition": "CenterScreen",
            "FormBorderStyle": "FixedSingle", "BackColor": "#1B2440"}
    ctrls = [C("Label", "lblScore", 10, 10, 90, 20, Text="Score: 0", ForeColor="#FFFFFF", BackColor="#1B2440",
               FontBold=True),
             C("Label", "lblLives", 104, 10, 80, 20, Text="Lives: 3", ForeColor="#FF8080", BackColor="#1B2440",
               FontBold=True),
             C("Label", "lblBest", 188, 10, 100, 20, Text="Best: 0", ForeColor="#FFD24A", BackColor="#1B2440"),
             C("Button", "btnStart", 300, 6, 80, 26, Text="Start"),
             C("Button", "btnPause", 386, 6, 80, 26, Text="Pause"),
             C("Panel", "pnlField", 10, 40, 456, 330, BackColor="#0E1428"),
             C("Label", "lblStar", 100, 0, 24, 24, Text="*", FontSize=16, FontBold=True, TextAlign="Center",
               ForeColor="#FFD24A", BackColor="#0E1428", parent="pnlField"),
             C("Label", "lblRock", 300, -40, 24, 24, Text="O", FontSize=14, FontBold=True, TextAlign="Center",
               ForeColor="#FF5050", BackColor="#0E1428", parent="pnlField"),
             C("Panel", "pnlPlayer", 190, 300, 76, 14, BackColor="#3BA3FF", parent="pnlField"),
             C("Label", "lblMessage", 78, 130, 300, 40, Text="Press Start (arrows / mouse move)",
               TextAlign="Center", ForeColor="#FFFFFF", BackColor="#0E1428", parent="pnlField"),
             C("Label", "lblHelp", 10, 376, 456, 17, Text="Left/Right or the mouse: move   P: pause   "
               "Catch the stars, dodge the red rocks.", ForeColor="#A0A8C0", BackColor="#1B2440", FontSize=8),
             C("Timer", "tmrGame", Interval=30, Enabled=False)]
    return {"frmGame": (form, ctrls)}


# ============================================================================ SettingsDemo (multi-form)
def settings_demo():
    main_items = menu(("&File", "mnuFile", [("&Settings...", "mnuSettings"), "-", ("E&xit", "mnuExit")]),
                      ("&Help", "mnuHelp", [("&About...", "mnuAbout")]))
    main = {"Text": "Greeting Cards", "Width": 520, "Height": 340, "StartPosition": "CenterScreen"}
    mctrls = [C("MenuStrip", "mnuMain", Items=main_items),
              C("Label", "lblTitle", 20, 16, 470, 30, Text="Hello!", FontSize=16, FontBold=True),
              C("Label", "lblMessage", 20, 56, 470, 40, Text=""),
              C("Label", "lblOccasion", 20, 112, 90, 17, Text="Occasion:"),
              C("ComboBox", "cboOccasion", 116, 109, 180, 21, Items="Birthday;New Year;Eid;Success"),
              C("Button", "btnMake", 310, 106, 180, 26, Text="Make card"),
              C("TextBox", "txtCard", 20, 144, 470, 100, Multiline=True, ReadOnly=True, Text="", FontSize=11),
              C("Button", "btnSettings", 20, 256, 140, 28, Text="Settings..."),
              C("Button", "btnAbout", 170, 256, 140, 28, Text="About..."),
              C("StatusBar", "sbStatus", 0, 296, 504, 22, Text="Ready", Anchor="Bottom, Left, Right")]
    settings = {"Text": "Settings", "Width": 360, "Height": 260, "StartPosition": "CenterScreen",
                "FormBorderStyle": "FixedDialog"}
    sctrls = [C("Label", "lblUser", 16, 20, 100, 17, Text="Your name:"),
              C("TextBox", "txtUser", 120, 17, 210, 20, Text=""),
              C("Label", "lblLang", 16, 54, 100, 17, Text="Language:"),
              C("ComboBox", "cboLang", 120, 51, 210, 21, Items="English;العربية"),
              C("Label", "lblSize", 16, 88, 100, 17, Text="Font size:"),
              C("NumericUpDown", "nudSize", 120, 85, 80, 20, Minimum=8, Maximum=24, Value=11),
              C("CheckBox", "chkFormal", 120, 118, 210, 20, Text="Formal greeting"),
              C("Button", "btnOK", 150, 180, 85, 28, Text="OK"),
              C("Button", "btnCancel", 245, 180, 85, 28, Text="Cancel")]
    about = {"Text": "About", "Width": 340, "Height": 200, "StartPosition": "CenterScreen",
             "FormBorderStyle": "FixedDialog"}
    actrls = [C("Label", "lblAboutTitle", 16, 16, 300, 24, Text="Greeting Cards", FontSize=13, FontBold=True),
              C("Label", "lblAboutText", 16, 48, 300, 60, Text="A RAD IDE example: three forms, a modal "
                "settings dialog, settings saved to a file and Arabic (right-to-left) text.\n"
                "(c) 2026 Musoftware - MIT License"),
              C("Label", "lblArabic", 16, 112, 300, 20, Text="مثال من RAD IDE - بطاقات التهنئة",
                TextAlign="Right"),
              C("Button", "btnClose", 236, 132, 80, 26, Text="Close")]
    return {"frmMain": (main, mctrls), "frmSettings": (settings, sctrls), "frmAbout": (about, actrls)}


KINDS = {"Notepad": notepad, "Calculator": calculator, "Contacts": contacts, "SalesChart": sales_chart,
         "StarCatcher": star_catcher, "SettingsDemo": settings_demo}


def make(language: str, kind: str, force: bool = False, folder: Path | None = None) -> Path:
    """Create samples/Examples/<language>/<kind> (or *folder*) with its forms laid out."""
    import shutil
    from radide import workspace
    from radide.model import Form, Project
    folder = Path(folder or EXAMPLES / language / kind)
    if folder.exists():
        if not force:
            raise SystemExit(f"{folder} exists (use --force)")
        shutil.rmtree(folder)
    lang = LANG_IDS[language]
    project = workspace.create_project(folder, kind, lang)
    forms = KINDS[kind]()
    names = list(forms)
    workspace.rename_form(project, "Form1", names[0])
    project = Project.load(folder)
    for extra in names[1:]:
        workspace.create_form(project, extra)
    project = Project.load(folder)
    for name, (fprops, ctrls) in forms.items():
        path = project.form_path(name)
        f = Form.load(path)
        f.controls = []
        f.props.update(fprops)
        f.props["Name"] = name
        for spec in ctrls:
            spec = dict(spec)
            t, cname = spec.pop("type"), spec.pop("name")
            x, y = int(spec.pop("x", 0)), int(spec.pop("y", 0))
            parent = spec.pop("parent", "")
            c = f.add(t, x, y, parent)
            c.props["Name"] = cname
            if "w" in spec:
                c.props["Width"] = int(spec.pop("w"))
            if "h" in spec:
                c.props["Height"] = int(spec.pop("h"))
            c.props.update(spec)
        f.save(path)
        workspace._regen(project, name)
    return folder


def make_console(language: str, name: str = "WordStats", main_file: str | None = None, force: bool = False) -> Path:
    """A console project (no forms, one module with its own main) - the C/C++/Go/Fortran console template."""
    import shutil
    from radide.languages import get_plugin
    from radide.model import Project
    folder = EXAMPLES / language / name
    if folder.exists():
        if not force:
            raise SystemExit(f"{folder} exists (use --force)")
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    lang = LANG_IDS[language]
    plugin = get_plugin(lang)
    main_file = main_file or f"{name}{plugin.code_ext}"
    project = Project(folder, name, lang)
    (folder / main_file).write_text("", encoding="utf-8")
    project.modules.append(main_file)
    project.save()
    return folder


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) == 2 and args[1] == "WordStats":
        print(make_console(args[0], force="--force" in sys.argv))
    else:
        print(make(args[0], args[1], force="--force" in sys.argv))
