# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Open / build / run / publish every compiled-language example in samples/Examples (C, C++, C#, Java, Go, Rust,
Fortran) through RAD IDE's own code paths and print a results table.

    .venv\\Scripts\\python samples\\Tests\\Examples\\test_examples_compiled.py [filter ...] [options]

    filter            substring of a project key, e.g.  C/  CSharp/Notepad  Calculator
    --no-publish      skip Build > Publish
    --list            print the project keys and exit

Every project is checked in its own child process (a crash or a hung GUI cannot stop the run):

* open    - every form loads into the real designer (DesignerView, offscreen Qt) without losing a control
            (console projects: the project loads and its module has main)
* build   - the language plugin's own build command (gcc / g++ / dotnet / javac / go / cargo / gfortran), as F5 does
* run     - the program runs in the IDE's GUI Bridge host (radide.runtimes.bridge.BridgeRuntime, what F5 starts) and
            its main interaction is driven through the host: menu clicks, buttons, key / mouse events with
            arguments, timers; file dialogs, message and input boxes are scripted. Console tools run like F5
            (bridge console mode) and their output / exit code is checked.
* publish - Build > Publish's build step (radide.deploy.build.build): kind, exe size, Python inside or not; the exe
            is started (only that process is touched) and its window must appear; native radforms exes (C, C++,
            Fortran) are also driven with Win32 messages (controls found by their radforms.name property).

One more row, IDE/ExampleGallery, checks Help > Example Projects (radide/features/example_gallery.py): every example is
listed, its README renders, search works and Open opens the project.

The rows are kept in results_compiled.json, merged into results.json next to this file (rows of other runs are kept)
and printed as a table
(results_compiled.md). QSettings org/app "RADIDE-TEST-EX1" is cleared before and after; QT_QPA_PLATFORM=offscreen,
QT_QPA_FONTDIR=C:\\Windows\\Fonts, RADIDE_NO_BROWSER=1; nothing is captured from the screen (widget.grab only).
"""
from __future__ import annotations

import json
import re
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
os.environ.setdefault("RADIDE_EX_SCRATCH", str(Path(os.environ.get("TEMP", ".")) / "radide_examples1"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
import exlib  # noqa: E402

exlib.QORG = exlib.QAPP = "RADIDE-TEST-EX1"
exlib.setup_env()
RESULTS = HERE / "results.json"
RESULTS_OWN = HERE / "results_compiled.json"
TABLE = HERE / "results_compiled.md"
CHILD_TIMEOUT = int(os.environ.get("RADIDE_EX_TIMEOUT", "1500"))
LANGS = ("C", "Cpp", "CSharp", "Java", "Go", "Rust", "Fortran", "VBNet")
TITLES = {"Notepad": "Notepad", "Calculator": "Calculator", "Contacts": "Contacts", "SalesChart": "Sales Chart",
          "StarCatcher": "Star Catcher", "SettingsDemo": "Greeting"}
KINDS = ("Notepad", "Calculator", "Contacts", "SalesChart", "StarCatcher", "SettingsDemo", "WordStats")


def projects() -> dict[str, Path]:
    out = {}
    for lang in LANGS:
        d = exlib.EXAMPLES / lang
        if d.is_dir():
            for p in sorted(d.iterdir()):
                if (p / "project.radproj").is_file() or (p / "Cargo.toml").is_file() or any(p.glob("*.vbproj")):
                    out[f"{lang}/{p.name}"] = p
    return out


def kind_of(folder: Path) -> str:
    for k in KINDS:
        if folder.name.startswith(k):
            return k
    return folder.name


# ============================================================================ helpers
class Ev:
    """The event argument object the bridge host forwards (X Y Button KeyCode KeyChar)."""

    def __init__(self, X=0, Y=0, Button=0, KeyCode="", KeyChar=""):
        self.X, self.Y, self.Button, self.KeyCode, self.KeyChar = X, Y, Button, KeyCode, KeyChar


def num(s) -> float:
    try:
        return float(str(s).strip())
    except ValueError:
        return float("nan")


class Checks:
    def __init__(self):
        self.failed: list[str] = []
        self.passed = 0

    def __call__(self, name: str, cond, detail="") -> bool:
        if cond:
            self.passed += 1
            print(f"    ok   {name}", flush=True)
        else:
            self.failed.append(f"{name} [{detail}]" if detail != "" else name)
            print(f"    FAIL {name}  [{detail}]", flush=True)
        return bool(cond)

    def note(self) -> str:
        return f"{self.passed} checks" if not self.failed else "; ".join(self.failed)[:600]


def patch_dialogs(scratch: Path, color="#FF0000"):
    """Scripted answers for the Tk file / colour dialogs the bridge host shows."""
    import tkinter.colorchooser as cc
    import tkinter.filedialog as fd
    fd.askopenfilename = lambda **k: str(scratch / "in.txt")
    fd.asksaveasfilename = lambda **k: str(scratch / "out.txt")
    cc.askcolor = lambda **k: ((255, 0, 0), color)


# ============================================================================ run scenarios (GUI Bridge host)
def run_notepad(d, c: Checks, work: Path):
    (work / "in.txt").write_text("hello world\nsecond line hello\nمرحبا بالعالم\n", encoding="utf-8")
    c("title", "Notepad" in str(d.form("frmMain").vb_get("caption")), d.form("frmMain").vb_get("caption"))
    d.click("mnuOpen")
    text = d.get("txtDoc")
    c("File > Open loads a multi-line file", text.count("\r\n") == 3 and "مرحبا" in text, repr(text[:80]))
    c("status bar after open", "Opened" in d.get("sbStatus"), d.get("sbStatus"))
    d.answers = ["hello"]
    d.click("mnuFind")
    c("Find selects the word", (d.get("txtDoc", "SelStart"), d.get("txtDoc", "SelLength")) == ("0", "5"),
      (d.get("txtDoc", "SelStart"), d.get("txtDoc", "SelLength")))
    d.click("mnuFindNext")
    c("Find Next", d.get("txtDoc", "SelStart") == "25", d.get("txtDoc", "SelStart"))
    d.click("mnuCopy")
    d.click("mnuPaste")
    c("Copy / Paste keep the text", d.get("txtDoc") == text, repr(d.get("txtDoc")[:60]))
    d.answers = ["hello", "bye"]
    d.click("mnuReplace")
    c("Replace all", d.get("txtDoc").count("bye") == 2 and "hello" not in d.get("txtDoc"), repr(d.get("txtDoc")[:60]))
    d.click("mnuSaveAs")
    out = work / "out.txt"
    saved = out.read_text(encoding="utf-8") if out.exists() else ""
    c("File > Save As writes the file", "bye world" in saved and "مرحبا" in saved, repr(saved[:60]))
    c("title shows the file name", "out.txt" in str(d.form("frmMain").vb_get("caption")),
      d.form("frmMain").vb_get("caption"))
    d.msgs.clear()
    d.click("mnuWordCount")
    c("Word count", any("words" in m for m in d.msgs), d.msgs)


def run_calculator(d, c: Checks, work: Path):
    for b in ("btn1", "btn2", "btnAdd", "btn3", "btnEquals"):
        d.click(b)
    c("12 + 3 = 15 (buttons)", d.get("lblDisplay", "Caption") == "15", d.get("lblDisplay", "Caption"))
    d.click("btnClear")
    for code, ch in (("7", "7"), ("asterisk", "*"), ("6", "6"), ("Return", "\r")):
        d.event("frmCalc", "KeyPress", Ev(KeyCode=code, KeyChar=ch))
    c("7 * 6 = 42 (keyboard)", d.get("lblDisplay", "Caption") == "42", d.get("lblDisplay", "Caption"))
    for b in ("btn1", "btnDiv", "btn0", "btnEquals"):
        d.click(b)
    c("division by zero is an error", "rror" in d.get("lblDisplay", "Caption"), d.get("lblDisplay", "Caption"))
    d.click("btnClear")
    for b in ("btn9", "btnSqrt"):
        d.click(b)
    c("sqrt 9 = 3", d.get("lblDisplay", "Caption") == "3", d.get("lblDisplay", "Caption"))
    d.click("btnMPlus")
    d.click("btnClear")
    d.click("btnMR")
    c("memory M+ / MR", d.get("lblDisplay", "Caption") == "3", d.get("lblDisplay", "Caption"))


def run_contacts(d, c: Checks, work: Path):
    n0 = len(d.list_items("lstContacts"))
    c("sample contacts listed", n0 >= 3, n0)
    d.click("btnNew")
    d.set("txtName", "Test Person")
    d.set("txtPhone", "0100 999")
    d.set("txtEmail", "test@example.com")
    d.click("btnSave")
    items = d.list_items("lstContacts")
    c("Save adds a contact", len(items) == n0 + 1 and any("Test Person" in i for i in items), items)
    db = [p for p in work.iterdir() if p.suffix in (".tsv", ".db", ".csv", ".json", ".txt", ".sqlite", ".xml", ".dat")
          and p.name not in ("in.txt", "out.txt")]
    c("stored in the database file", any("Test Person" in p.read_text(encoding="utf-8", errors="replace")
                                         if p.suffix != ".sqlite" else p.stat().st_size > 0 for p in db),
      [p.name for p in db])
    d.set("txtPhone", "0100 777")
    d.click("btnSave")
    c("Save updates the contact", any("0100 777" in i for i in d.list_items("lstContacts")) or
      d.get("txtPhone") == "0100 777", d.list_items("lstContacts"))
    d.set("txtSearch", "test person")
    d.click("btnFind")
    c("Find filters the list", len(d.list_items("lstContacts")) == 1, d.list_items("lstContacts"))
    d.answers = ["YES"]
    d.click("btnDelete")
    d.click("btnShowAll")
    c("Delete removes it", len(d.list_items("lstContacts")) == n0, d.list_items("lstContacts"))


def run_saleschart(d, c: Checks, work: Path):
    d.pump(2500)                                  # the timer animates the bars to their values
    h1 = num(d.get("pnlBar1", "Height"))
    c("timer animation reaches the value (bar 1 = 50 -> 120 px)", abs(h1 - 120) <= 3, h1)
    d.set("chkAnimate", 0, "Value")
    d.event("chkAnimate", "CheckedChanged")
    d.event("pnlChart", "MouseDown", Ev(X=154, Y=100, Button=1))
    h3 = num(d.get("pnlBar3", "Height"))
    c("MouseDown sets bar 3 to 75 (180 px)", abs(h3 - 180) <= 3, h3)
    c("statistics label", "Total" in d.get("lblStats", "Caption"), d.get("lblStats", "Caption"))
    d.click("btnColor")
    c("ColorDialog colours the bars", str(d.get("pnlBar1", "BackColor")).upper() in ("#FF0000", "255"),
      d.get("pnlBar1", "BackColor"))
    d.click("btnSave")
    c("Save writes sales.csv", (work / "sales.csv").exists())
    d.click("btnRandom")
    d.click("btnLoad")
    c("Load restores the data", abs(num(d.get("pnlBar3", "Height")) - 180) <= 3, d.get("pnlBar3", "Height"))


def run_starcatcher(d, c: Checks, work: Path):
    d.click("btnStart")
    c("Start enables the game timer", str(d.ctl("tmrGame").vb_get("enabled")) in ("True", "1", "-1"),
      d.ctl("tmrGame").vb_get("enabled"))
    y0 = num(d.get("lblStar", "Top"))
    d.pump(800)
    y1 = num(d.get("lblStar", "Top"))
    c("the star falls (timer loop)", y1 != y0, (y0, y1))
    x0 = num(d.get("pnlPlayer", "Left"))
    d.event("frmGame", "KeyDown", Ev(KeyCode="Right"))
    d.pump(500)
    d.event("frmGame", "KeyUp", Ev(KeyCode="Right"))
    x1 = num(d.get("pnlPlayer", "Left"))
    c("Right arrow moves the paddle", x1 > x0, (x0, x1))
    d.event("pnlField", "MouseMove", Ev(X=60, Y=200))
    d.pump(200)
    c("MouseMove moves the paddle", num(d.get("pnlPlayer", "Left")) < x1, d.get("pnlPlayer", "Left"))
    d.click("btnPause")
    c("Pause", d.get("btnPause", "Caption") == "Resume", d.get("btnPause", "Caption"))


def run_settingsdemo(d, c: Checks, work: Path):
    c("main form shows a greeting", d.get("lblTitle", "Caption") != "", d.get("lblTitle", "Caption"))
    d.click("btnSettings")
    c("Settings dialog shown", bool(d.form("frmSettings").loaded) and
      bool(d.form("frmSettings").ui.root.winfo_viewable()))
    d.set("txtUser", "Mona", form="frmSettings")
    d.ctl("cboLang", "frmSettings").vb_set("listindex", 1)
    d.ctl("nudSize", "frmSettings").vb_set("value", 13)
    d.click("btnOK")
    d.pump(200)
    title = d.get("lblTitle", "Caption")
    c("OK applies Arabic settings", "Mona" in title and any("\u0600" <= ch <= "\u06ff" for ch in title), title)
    c("dialog closed after OK", not (d.form("frmSettings").loaded and d.form("frmSettings").ui.root.winfo_viewable()))
    files = [p for p in work.iterdir() if p.suffix.lower() in (".ini", ".cfg", ".txt", ".json", ".properties")
             and p.name not in ("in.txt", "out.txt")]
    c("settings saved to a file", any("Mona" in p.read_text(encoding="utf-8", errors="replace") for p in files),
      [p.name for p in files])
    d.ctl("cboOccasion").vb_set("listindex", 0)
    d.click("btnMake")
    c("Make card writes the card", len(d.get("txtCard")) > 10, d.get("txtCard")[:60])
    d.click("btnAbout")
    c("About form shown", bool(d.form("frmAbout").loaded) and bool(d.form("frmAbout").ui.root.winfo_viewable()))
    d.click("btnClose")


RUN = {"Notepad": run_notepad, "Calculator": run_calculator, "Contacts": run_contacts, "SalesChart": run_saleschart,
       "StarCatcher": run_starcatcher, "SettingsDemo": run_settingsdemo}


# ============================================================================ native exe scenarios (radforms)
def native_drive(kind: str, exe: Path, c: Checks):
    sys.path.insert(0, str(ROOT / "samples" / "Tests" / "Native"))
    import winauto as w
    startup = {"Notepad": "frmMain", "Calculator": "frmCalc", "Contacts": "frmContacts", "SalesChart": "frmChart",
               "StarCatcher": "frmGame", "SettingsDemo": "frmMain"}[kind]
    p = w.start(exe)
    form = None
    try:
        form = w.form_window(p.pid, startup, 15)
        if not c(f"native: {startup} shown", form):
            return
        ch = w.wait(lambda: w.children(form) or None) or {}
        t = lambda n: w.get_text(ch[n])  # noqa: E731
        if kind == "Calculator":
            for b in ("btn1", "btn2", "btnAdd", "btn3", "btnEquals"):
                w.click(ch[b])
                time.sleep(0.05)
            c("native: 12 + 3 = 15", w.wait(lambda: t("lblDisplay") == "15"), t("lblDisplay"))
        elif kind == "Notepad":
            w.set_text(ch["txtDoc"], "one two three")
            c("native: text box takes text", w.wait(lambda: "*" in w.get_text(form) or "Notepad" in w.get_text(form)),
              w.get_text(form))
        elif kind == "Contacts":
            c("native: contacts listed", w.wait(lambda: w.user32.SendMessageW(ch["lstContacts"], w.LB_GETCOUNT, 0, 0)
                                                >= 3), "")
        elif kind == "SalesChart":
            w.click(ch["btnRandom"])
            c("native: statistics", w.wait(lambda: "Total" in t("lblStats")), t("lblStats"))
        elif kind == "StarCatcher":
            w.click(ch["btnStart"])
            c("native: game started", w.wait(lambda: t("btnStart") == "Restart"), t("btnStart"))
        elif kind == "SettingsDemo":
            w.click(ch["btnAbout"])
            c("native: About form opens", w.form_window(p.pid, "frmAbout", 5))
    finally:
        for h in w.top_windows(p.pid):
            if w.class_name(h) == "#32770":
                w.click_dialog_button(h)
        if not w.stop(p, form, 8):
            print("    (native exe killed after timeout)", flush=True)


def gui_exe_starts(exe: Path, title: str, c: Checks, timeout=60):
    p = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        win = exlib.wait_window(p, title, timeout)
        c(f"published exe shows its window ({title})", win, "no window")
    finally:
        exlib.stop_tree(p)


# ============================================================================ one project (child process)
def find_child(top, text: str):
    """A child window of *top* with this exact text (WinForms controls are real Win32 windows)."""
    sys.path.insert(0, str(ROOT / "samples" / "Tests" / "Native"))
    import winauto as w
    found = []

    def cb(h, _l):
        if w.get_text(h) == text:
            found.append(h)
        return True
    w.user32.EnumChildWindows(top, w.WNDENUMPROC(cb), 0)
    return found[0] if found else None


def drive_winforms_calculator(exe: Path, c: Checks, label: str):
    """Start a WinForms calculator exe, click 1 2 + 3 = by the buttons' texts and read the display."""
    sys.path.insert(0, str(ROOT / "samples" / "Tests" / "Native"))
    import winauto as w
    p = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        win = exlib.wait_window(p, "Calculator", 60)
        if not c(f"{label}: the window is shown", win):
            return
        top = win[0]
        for t in ("1", "2", "+", "3", "="):
            b = w.wait(lambda t=t: find_child(top, t), 5)
            if b:
                w.click(b)
                time.sleep(0.15)
        c(f"{label}: 12 + 3 = 15", w.wait(lambda: find_child(top, "15"), 5), "no '15' on the form")
    finally:
        exlib.stop_tree(p)


def check_dotnet(key: str, folder: Path, opts: dict) -> exlib.Result:
    """A .NET SDK project from File > New Project > .NET (VB.NET Windows Forms App), opened in place."""
    proj = next(folder.glob("*.vbproj"), None) or next(folder.glob("*.csproj"))
    res = exlib.Result(key, "vbnet-winforms" if proj.suffix == ".vbproj" else "csharp-winforms")
    from radide.features.foreign_projects import is_foreign
    from radide.foreign import winforms_cs as W
    designer = next(folder.glob("*.Designer.vb"), None) or next(folder.glob("*.Designer.cs"))
    text = designer.read_text(encoding="utf-8-sig")
    want = len(re.findall(r"(?m)^\s*(?:Friend WithEvents|private System\.Windows\.Forms\.)\s*(\w+)", text))
    form = W.load_form(designer)
    rendered, _report, _r = W.render_form(form, (folder / designer.name.replace(".Designer", "")).read_text(
        encoding="utf-8-sig"))
    res.step("open", is_foreign(folder) and len(form.controls) == want and rendered.replace("\r\n", "\n").strip()
             == text.replace("\r\n", "\n").strip(),
             f"{len(form.controls)}/{want} controls; the designer writes the file back unchanged")
    work = exlib.temp_copy(folder, "run_" + key.split("/")[0])
    from radide.dotnet.templates.catalog import find_dotnet
    dotnet = find_dotnet() or "dotnet"
    r = subprocess.run([dotnet, "build", "-c", "Release", "-nologo", "-v", "q"], cwd=str(work), capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=600)
    exe = next(iter(sorted((work / "bin" / "Release").rglob(proj.stem + ".exe"))), None)
    if not res.step("build", r.returncode == 0 and exe is not None, (r.stdout + r.stderr)[-400:] if r.returncode else
                    "dotnet build -c Release"):
        return res
    c = Checks()
    drive_winforms_calculator(exe, c, "run")
    res.step("run", not c.failed, c.note())
    if opts.get("publish"):
        # Project > dotnet CLI > Publish (radide/dotnet/tools/cli.py): dotnet publish -c Release -o publish
        r = subprocess.run([dotnet, "publish", str(work / proj.name), "-c", "Release", "-o", "publish", "--nologo"],
                           cwd=str(work), capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=900)
        pexe = work / "publish" / (proj.stem + ".exe")
        if not res.step("publish", r.returncode == 0 and pexe.is_file(), (r.stdout + r.stderr)[-300:] if r.returncode else ""):
            return res
        size = sum(f.stat().st_size for f in (work / "publish").rglob("*") if f.is_file())
        res["kind"], res["exe_kb"], res["python_inside"] = "dotnet publish", round(pexe.stat().st_size / 1024), False
        res["size"] = f"{exlib.mb(size)} MB (dotnet publish, framework-dependent)"
        c = Checks()
        drive_winforms_calculator(pexe, c, "published exe")
        res.step("publish", not c.failed, c.note())
    return res


def check_project(key: str, folder: Path, opts: dict) -> exlib.Result:
    from radide.model import Project
    if not (folder / "project.radproj").is_file() and (any(folder.glob("*.vbproj")) or any(folder.glob("*.csproj"))):
        return check_dotnet(key, folder, opts)
    kind = kind_of(folder)
    cargo = (folder / "Cargo.toml").is_file() and not (folder / "project.radproj").is_file()
    project = None if cargo else Project.load(folder)
    lang = "rust-cargo" if cargo else (project.form_languages.get(project.startup, project.language)
                                      if project.startup else project.language)
    res = exlib.Result(key, lang)
    # ------------------------------------------------------------------ open
    if cargo or not project.forms:
        ok =(folder / "src" / "main.rs").exists() if cargo else bool(project.modules)
        res.step("open", ok, "console project")
    else:
        ok, note = exlib.designer_check(folder)
        res.step("open", ok, note)
    work = exlib.temp_copy(folder, "run_" + key.split("/")[0])
    # ------------------------------------------------------------------ build + run
    if cargo or not project.forms:
        run_console(work, res, lang)
    else:
        patch_dialogs(work)
        c = Checks()
        hub = start_hub(work, project)
        try:
            d = exlib.BridgeDriver(work)
        except Exception as e:  # noqa: BLE001
            res.step("build", False, str(e)[-500:])
            return res
        res.step("build", True)
        try:
            c("the program's window is shown", d.window(TITLES[kind]), TITLES[kind])
            # then park the windows off-screen: the real mouse / keyboard of whoever uses this PC must not
            # send MouseMove / key events into the scripted run
            for vf in d.rt.forms.values():
                if vf.loaded:
                    vf.ui.root.geometry("+-6000+-6000")
            d.pump(100)
            RUN[kind](d, c, work)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            c("scenario finished", False, repr(e)[:200])
        finally:
            d.close()
            if hub is not None:
                hub.stop()
        res.step("run", not c.failed, c.note())
    # ------------------------------------------------------------------ publish
    if opts.get("publish"):
        pub = exlib.temp_copy(folder, "pub_" + key.split("/")[0])
        r = exlib.publish(pub, pub.parent / f"{folder.name}_publish.log", app_name=folder.name)
        if not r.get("ok"):
            res.step("publish", False, r.get("error", "") + " " + " | ".join(r.get("log_tail", [])[-4:]))
            return res
        exe = Path(r["dist"]) / r["exe"]
        res["kind"], res["exe_kb"], res["python_inside"] = r["kind"], round(exe.stat().st_size / 1024), \
            r["python_inside"]
        res["size"] = f"{r['size_mb']} MB ({r['kind']}{', Python' if r['python_inside'] else ''})"
        c = Checks()
        if cargo or not project.forms:
            p = subprocess.run([str(exe), "--top", "3", str(work / "sample.txt")], cwd=str(exe.parent),
                               capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            c("published console exe runs", p.returncode == 0 and "Top" in p.stdout, (p.returncode, p.stdout[-200:]))
            p = subprocess.run([str(exe), "no-such-file.txt"], cwd=str(exe.parent), capture_output=True, text=True,
                               timeout=60)
            c("exit code 2 for a missing file", p.returncode == 2, p.returncode)
        elif r["kind"] == "native" and lang in ("c-bridge", "cpp-bridge", "fortran-bridge"):
            native_drive(kind, exe, c)
        else:
            gui_exe_starts(exe, TITLES[kind], c)
        res.step("publish", not c.failed, c.note())
    return res


def start_hub(work: Path, project):
    """A multi-language project (a module of another language): start RAD Hub like the IDE does for a Run
    (radide/app.py _start_hub) and give the program RAD_HUB / RAD_PROJECT."""
    from radide.languages import get_plugin
    ext = get_plugin(project.language).code_ext.lower()
    if not any(Path(m).suffix.lower() != ext for m in project.modules):
        return None
    from radide.runtimes.radhub import RadHub
    hub = RadHub(work, log=lambda s: print("    [hub] " + str(s).rstrip(), flush=True))
    hub.start()
    os.environ.update(hub.env())
    return hub


def run_console(work: Path, res: exlib.Result, lang: str):
    """F5 of a console project: the plugin's run spec (bridge console mode: build, then the program)."""
    p = exlib.run_spec_proc(work)
    try:
        out, _ = p.communicate(timeout=900)
    except subprocess.TimeoutExpired:
        p.kill()
        out = "timeout"
    built = p.returncode == 0 or "Top" in out
    res.step("build", built, "" if built else out[-500:])
    ok = p.returncode == 0 and "Top" in out and "words" in out.lower()
    res.step("run", ok, out.strip().splitlines()[-1][:120] if ok and out.strip() else out[-400:])


GALLERY_KEY = "IDE/ExampleGallery"


def check_gallery(key: str) -> exlib.Result:
    """Help > Example Projects (radide/features/example_gallery.py): every compiled example is listed, its README
    renders, Open opens the project through the main window's open_project (offscreen, widget.grab only)."""
    res = exlib.Result(key, "IDE")
    exlib.qapp()
    from PyQt6.QtWidgets import QWidget
    from radide.features import example_gallery as g
    found = g.discover()
    mine = {k for k in projects()}
    listed = {f"{lang}/{p.name}" for lang, ps in found.items() for p in ps}
    res.step("open", mine <= listed, f"{len(listed)} examples listed" if mine <= listed else
             f"missing {sorted(mine - listed)[:5]}")

    class Win(QWidget):
        opened = None

        def open_project(self, f):
            Win.opened = Path(f)
    w = Win()
    dlg = g.ExampleGallery(w, "Rust")
    cur = dlg.tree.currentItem()
    ok = cur is not None and "Rust" in dlg.readme.toPlainText() and not dlg.grab().isNull()
    res.step("build", ok, cur.text(0) if cur else "no selection")
    dlg.search.setText("star")
    shown = [dlg.tree.topLevelItem(i).child(j).text(0) for i in range(dlg.tree.topLevelItemCount())
             for j in range(dlg.tree.topLevelItem(i).childCount()) if not dlg.tree.topLevelItem(i).child(j).isHidden()]
    dlg._open(copy=False)
    res.step("run", bool(shown) and Win.opened is not None and (Win.opened / "project.radproj").exists(),
             f"search 'star': {len(shown)} shown, opened {Win.opened}")
    res["publish"] = "-"
    return res


def child(key: str, opts: dict) -> int:
    exlib.clear_qsettings()
    t0 = time.time()
    if key == GALLERY_KEY:
        res = check_gallery(key)
        res["seconds"] = round(time.time() - t0, 1)
        exlib.emit(res)
        exlib.clear_qsettings()
        os._exit(0)
    folder = projects()[key]
    try:
        res = check_project(key, folder, opts)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        res = exlib.Result(key, "")
        res["notes"].append(f"exception: {e!r}"[:400])
        res["open"] = "FAIL"
    res["seconds"] = round(time.time() - t0, 1)
    exlib.emit(res)
    sys.stdout.flush()
    exlib.clear_qsettings()
    os._exit(0)


def table(rows: list[dict]) -> str:
    head = ("| Project | Language | Open | Build | Run | Publish | Kind | Exe size | Python inside | Result |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n")
    return head + "".join(
        f"| {r['project']} | {r.get('language', '')} | {r['open']} | {r['build']} | {r['run']} | {r['publish']} | "
        f"{r.get('kind', '-')} | {str(r.get('exe_kb', '-')) + ' KB' if r.get('exe_kb') else '-'} | "
        f"{'yes' if r.get('python_inside') else ('no' if r.get('kind') else '-')} | {r['result']} |\n" for r in rows)


def main(argv: list[str]) -> int:
    opts = {"publish": "--no-publish" not in argv}
    if "--child" in argv:
        return child(argv[argv.index("--child") + 1], opts)
    filters = [a for a in argv if not a.startswith("--")]
    keys = [k for k in [*projects(), GALLERY_KEY] if not filters or any(f.lower() in k.lower() for f in filters)]
    if "--list" in argv:
        print("\n".join(keys))
        return 0
    exlib.clear_qsettings()
    rows = []
    for key in keys:
        print(f"\n===== {key}", flush=True)
        cmd = [sys.executable, "-u", str(Path(__file__).resolve()), "--child", key] + \
              ([] if opts["publish"] else ["--no-publish"])
        row = None
        p = subprocess.Popen(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace")
        t0 = time.time()
        try:
            for line in p.stdout:
                if line.startswith("@@RESULT@@"):
                    row = json.loads(line[len("@@RESULT@@"):])
                else:
                    print("  " + line.rstrip(), flush=True)
                if time.time() - t0 > CHILD_TIMEOUT:
                    break
            p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        if p.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        if row is None:
            row = exlib.Result(key, "").finish()
            row.update(open="FAIL", result="FAIL", notes=["child crashed or timed out"])
        rows.append(row)
    exlib.clear_qsettings()
    # results.json is shared with test_examples_scripting.py (both merge their rows into it); this test's own
    # rows are also kept in results_compiled.json, which only this test writes
    mine_all = {}
    if RESULTS_OWN.exists():
        try:
            mine_all = {r["project"]: r for r in json.loads(RESULTS_OWN.read_text(encoding="utf-8"))}
        except (ValueError, KeyError):
            mine_all = {}
    for r in rows:
        mine_all[r["project"]] = r
    order = {k: i for i, k in enumerate([*projects(), GALLERY_KEY])}
    mine = sorted(mine_all.values(), key=lambda r: order.get(r["project"], 999))
    RESULTS_OWN.write_text(json.dumps(mine, ensure_ascii=False, indent=1), encoding="utf-8")
    old = {}
    if RESULTS.exists():
        try:
            old = {r["project"]: r for r in json.loads(RESULTS.read_text(encoding="utf-8"))}
        except (ValueError, KeyError):
            old = {}
    for r in mine:
        old[r["project"]] = r
    RESULTS.write_text(json.dumps(list(old.values()), ensure_ascii=False, indent=1), encoding="utf-8")
    TABLE.write_text("# Compiled-language examples - results\n\n" + table(mine), encoding="utf-8")
    print("\n" + table(rows))
    for r in rows:
        for n in r.get("notes", []):
            if r["result"] != "ok":
                print(f"  {r['project']}: {n}")
    return sum(1 for r in rows if r["result"] != "ok")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
