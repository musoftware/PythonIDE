# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Example group "js": JavaScript / TypeScript / PHP forms (GUI Bridge) and the PHP + Node.js web sites.

    .venv\\Scripts\\python samples\\Tests\\Examples\\test_examples_scripting.py --group js [--no-publish]

open    = exlib.designer_check (every form in the real designer, no control lost)
build   = node --check / TypeScript type-stripping compile / php -l on every code file (the bridge runs the
          sources directly; F5 does the same check implicitly)
run     = the project in the IDE's bridge host (exlib.BridgeDriver): its window appears (EnumWindows on this
          process) and the main workflow is driven - inputs set, buttons / menu items clicked, results read
          back from the controls; MsgBox / InputBox answers are scripted, file dialogs are answered with
          files in the scratch copy.  Web sites: the IDE's DevServer (radide/web_site/server.py) on a free
          port + HTTP GET/POST.
publish = Build > Publish's build step (exlib.publish) on a scratch copy: kind, size, Python inside.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import exlib

NODE = shutil.which("node") or "node"
for _s in (sys.stdout, sys.stderr):            # Arabic in the test output
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


# ============================================================================ helpers
class Ev:
    """Event arguments as the bridge host sends them (X Y Button KeyCode KeyChar)."""

    def __init__(self, char="", keysym="", x=0, y=0, button=0):
        self.X, self.Y, self.Button = x, y, button
        self.KeyCode = keysym or (char if char.strip() else "space")
        self.KeyChar = char


def fake_file_dialogs(open_files: list, save_files: list):
    """Answer the Tk file dialogs of the bridge host with the given paths (in order)."""
    from tkinter import filedialog
    filedialog.askopenfilename = lambda **kw: str(open_files.pop(0)) if open_files else ""
    filedialog.asksaveasfilename = lambda **kw: str(save_files.pop(0)) if save_files else ""


def php_exe() -> str:
    from radide.languages import get_plugin
    return get_plugin("php").tool() or "php"


def syntax_check(folder: Path, lang: str) -> tuple[bool, str]:
    """The language's own syntax check on every code file of the project."""
    from radide.model import Project
    p = Project.load(folder)
    files = sorted({*(folder.glob("*.js")), *(folder.glob("*.ts")), *(folder.glob("*.php"))})
    files = [f for f in files if not f.name.startswith(("_rad", "radgui", "radworker")) and "_designer" not in f.name]
    bad = []
    for f in files:
        if f.suffix == ".js":
            r = subprocess.run([NODE, "--check", str(f)], capture_output=True, text=True)
        elif f.suffix == ".ts":
            code = ("const m=require('module');const fs=require('fs');const vm=require('vm');"
                    "const src=m.stripTypeScriptTypes(fs.readFileSync(process.argv[1],'utf8'),{mode:'transform'});"
                    "new vm.Script(src,{filename:process.argv[1]});")
            r = subprocess.run([NODE, "-e", code, str(f)], capture_output=True, text=True)
        else:
            r = subprocess.run([php_exe(), "-l", str(f)], capture_output=True, text=True)
        if r.returncode != 0:
            bad.append(f"{f.name}: {(r.stdout + r.stderr).strip()[-300:]}")
    n = len(files)
    return not bad, (f"{n} file(s) ok" if not bad else "; ".join(bad)) + f" [{len(p.forms)} form(s)]"


def form_project(fn_run):
    """Standard open / build / run / publish flow for a GUI Bridge project; fn_run(driver, work, res)."""
    def test(folder: Path, res: exlib.Result, opts: dict):
        ok, note = exlib.designer_check(folder)
        res.step("open", ok, note)
        work = exlib.temp_copy(folder, "js")
        ok, note = syntax_check(work, res["language"])
        res.step("build", ok, note)
        d = None
        try:
            d = exlib.BridgeDriver(work)
            checks: list[tuple[bool, str]] = []
            fn_run(d, work, checks)
            bad = [m for c, m in checks if not c]
            res.step("run", not bad, f"{len(checks) - len(bad)}/{len(checks)} checks" +
                     (f"; failed: {bad}" if bad else ""))
        finally:
            if d is not None:
                d.close()
        if opts.get("publish"):
            pub_work = exlib.temp_copy(folder, "js_pub")
            pub = exlib.publish(pub_work, exlib.SCRATCH / "js_pub" / f"{folder.name}_publish.log")
            note = (f"kind={pub.get('kind')} exe={pub.get('exe', '')} size={pub.get('size_mb', 0)} MB "
                    f"python_inside={pub.get('python_inside')}" if pub.get("ok") else f"error: {pub.get('error')}")
            if pub.get("ok"):                     # the published program starts and shows its own window
                title =json.loads((folder / "Form1.form").read_text(encoding="utf-8"))["props"]["Text"]
                exe = Path(pub["dist"]) / pub["exe"]
                proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
                try:
                    win = exlib.wait_window(proc, title.split(" - ")[0], 60)
                finally:
                    exlib.stop_tree(proc)
                note += f"; published exe shows '{win[1]}'" if win else "; published exe showed NO window"
                pub["ok"] = bool(win)
            res.step("publish", bool(pub.get("ok")), note)
            res["size"] = f"{pub.get('size_mb', 0)} MB" if pub.get("ok") else "-"
            res["publish_info"] = {k: pub.get(k) for k in ("kind", "exe", "size_mb", "exe_mb", "python_inside")}
    return test


def nl(s: str) -> str:
    """A multi-line TextBox answers with Windows line ends (CR LF, like VB)."""
    return s.replace("\r\n", "\n")


def check(checks, cond, msg):
    checks.append((bool(cond), msg))
    print(("  ok   " if cond else "  FAIL ") + msg, flush=True)


# ============================================================================ JavaScript
def run_notepad(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Notepad"), "window 'Notepad' is shown")
    doc = "hello world\nsecond line مرحبا"
    d.set("txtDoc", doc)
    target = work / "note1.txt"
    fake_file_dialogs([], [target])
    d.click("mnuSaveAs")
    check(c, target.exists() and target.read_text(encoding="utf-8") == doc, "Save As writes the multi-line text")
    check(c, "note1.txt" in d.get("Form1", "Caption"), "caption shows the file name")
    d.click("mnuStats")
    check(c, d.msgs and "Words: 5" in d.msgs[-1] and "Lines: 2" in d.msgs[-1], f"statistics: {d.msgs[-1:]}")
    d.click("mnuUpper")
    check(c, nl(d.get("txtDoc")).startswith("HELLO WORLD\nSECOND"), "Format > UPPER CASE")
    d.answers = ["LINE"]
    d.click("mnuFind")
    check(c, "1 time" in d.msgs[-1], f"Find: {d.msgs[-1]}")
    d.answers = ["YES"]                          # discard the unsaved change
    d.click("mnuNew")
    check(c, d.get("txtDoc") == "", "New clears the document after confirming")
    fake_file_dialogs([target], [])
    d.click("mnuOpen")
    check(c, nl(d.get("txtDoc")) == doc, "Open reads the file back")
    s = json.loads((work / "notepad.settings.json").read_text(encoding="utf-8"))
    check(c, s.get("lastFile", "").endswith("note1.txt"), "last file saved in notepad.settings.json")


def run_calculator(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Calculator"), "window 'Calculator' is shown")
    for b in ("cmd1", "cmd2", "cmdAdd", "cmd3", "cmd0", "cmdEq"):
        d.click(b)
    check(c, d.get("txtDisplay") == "42", f"12 + 30 = {d.get('txtDisplay')}")
    check(c, d.list_items("lstHistory")[-1:] == ["12 + 30 = 42"], f"history {d.list_items('lstHistory')}")
    d.click("cmdClear")
    for ch in "6*7":
        d.event("txtDisplay", "KeyPress", Ev(ch))
    d.event("txtDisplay", "KeyPress", Ev("\r", "Return"))
    check(c, d.get("txtDisplay") == "42", f"keyboard 6*7 Enter = {d.get('txtDisplay')}")
    for b in ("cmd8", "cmd1", "cmdSqrt"):
        d.click(b)
    check(c, d.get("txtDisplay") == "9", f"sqrt(81) = {d.get('txtDisplay')}")
    for b in ("cmd1", "cmdDiv", "cmd0", "cmdEq"):
        d.click(b)
    check(c, d.get("txtDisplay") == "Error", "division by zero shows Error")
    for b in ("cmd0", "cmdDot", "cmd1", "cmdAdd", "cmd0", "cmdDot", "cmd2", "cmdEq"):
        d.click(b)
    check(c, d.get("txtDisplay") == "0.3", f"0.1 + 0.2 = {d.get('txtDisplay')}")
    d.click("mnuHistory")
    check(c, d.get("lstHistory", "Visible") in ("False", "0"), "View > History hides the list")


def run_contacts(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Contacts"), "window 'Contacts' is shown")
    for name, phone, email, grp in (("Sara Ahmed", "0101", "sara@example.com", "Work"),
                                    ("محمد علي", "0112", "mohamed@example.com", "Family")):
        d.set("txtName", name), d.set("txtPhone", phone), d.set("txtEmail", email), d.set("cboGroup", grp)
        d.click("cmdAdd")
    check(c, d.get("grdContacts", "Rows") == "3", f"grid has 2 contacts (Rows={d.get('grdContacts', 'Rows')})")
    check(c, "2 of 2" in d.get("lblCount", "Caption"), d.get("lblCount", "Caption"))
    d.set("txtName", "Bad"), d.set("txtEmail", "not-an-email")
    d.click("cmdAdd")
    check(c, "not valid" in d.msgs[-1], "invalid email is refused")
    d.set("txtSearch", "محمد")
    d.event("txtSearch", "TextChanged")
    check(c, d.get("grdContacts", "Rows") == "2" and d.call("grdContacts", "TextMatrix", 1, 1) == "محمد علي",
          "Arabic search finds 1 contact")
    d.set("txtSearch", "")
    d.event("txtSearch", "TextChanged")
    d.set("grdContacts", 1, "Row")               # sorted by name: row 1 = Sara Ahmed
    d.event("grdContacts", "SelectedIndexChanged")
    check(c, d.get("txtName") == "Sara Ahmed", f"row click loads the contact ({d.get('txtName')})")
    d.set("txtPhone", "0109")
    d.click("cmdUpdate")
    check(c, d.call("grdContacts", "TextMatrix", 1, 2) == "0109", "Update changes the phone in the grid")
    d.answers = ["YES"]
    d.click("cmdDelete")
    check(c, d.get("grdContacts", "Rows") == "2", "Delete removes the contact")
    d.click("mnuExport")
    csv = (work / "contacts.csv").read_text(encoding="utf-8-sig")
    check(c, "محمد علي" in csv and csv.startswith("Id,Name"), "CSV export with Arabic")
    check(c, (work / "contacts.db").exists(), "SQLite database contacts.db created")


def run_focustimer(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Focus Timer"), "window 'Focus Timer' is shown")
    check(c, d.get("lblTime", "Caption") == "25:00", "starts at 25:00")
    d.click("cmdSettings")
    st = d.form("Settings")
    check(c, st.loaded and st.ui.root.winfo_viewable(), "Settings dialog shown (ShowDialog)")
    d.set("numFocus", 1, "Value", form="Settings")
    d.set("chkArabic", 1, "Value", form="Settings")
    d.set("chkBeep", 0, "Value", form="Settings")
    d.click("cmdOK")
    check(c, not st.ui.root.winfo_viewable(), "OK hides the dialog")
    check(c, d.get("lblTime", "Caption") == "01:00", f"focus = 1 minute ({d.get('lblTime', 'Caption')})")
    check(c, "مؤقت" in d.get("Form1", "Caption") and d.get("cmdStart", "Caption") == "ابدأ", "Arabic interface")
    saved = json.loads((work / "focustimer.settings.json").read_text(encoding="utf-8"))
    check(c, saved.get("focus") == 1 and saved.get("arabic") is True, "settings saved to JSON")
    d.click("cmdStart")
    check(c, d.get("tmrTick", "Enabled") == "True", "Start enables the Timer")
    d.pump(2600)                                  # the real Timer ticks every second
    t = d.get("lblTime", "Caption")
    check(c, t in ("00:58", "00:57", "00:59"), f"the Timer counts down ({t})")
    for _ in range(int(t[-2:])):                  # run the rest of the period at once
        d.event("tmrTick", "Tick")
    check(c, "استراحة" in d.get("lblMode", "Caption") and d.list_items("lstLog"), "period ends -> break, logged")
    d.click("cmdReset")
    check(c, d.get("tmrTick", "Enabled") == "False", "Reset stops the Timer")


# ============================================================================ TypeScript
def run_unitconverter(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Unit Converter"), "window 'Unit Converter' is shown")
    d.set("txtValue", "2")
    d.set("cboFrom", "km"), d.set("cboTo", "m")
    d.event("cboTo", "SelectedIndexChanged")
    check(c, d.get("lblResult", "Caption") == "2 km = 2000.000 m", d.get("lblResult", "Caption"))
    d.set("optTemp", True, "Value")
    d.event("optTemp", "CheckedChanged")
    check(c, d.list_items("cboFrom") == ["C", "F", "K"], f"temperature units {d.list_items('cboFrom')}")
    d.set("txtValue", "100")
    d.set("cboFrom", "C"), d.set("cboTo", "F")
    d.set("trkDecimals", 1, "Value")
    d.event("trkDecimals", "ValueChanged")
    check(c, d.get("lblResult", "Caption") == "100 C = 212.0 F", d.get("lblResult", "Caption"))
    d.click("cmdSwap")
    check(c, d.get("lblResult", "Caption").startswith("100 F = 37.8 C"), d.get("lblResult", "Caption"))
    d.set("txtValue", "abc")
    d.event("txtValue", "TextChanged")
    check(c, d.get("lblResult", "Caption") == "Not a number", "bad input is reported")
    d.set("txtValue", "1")
    d.event("txtValue", "TextChanged")
    d.click("mnuLog")
    check(c, len(d.list_items("lstLog")) == 1, "File > Copy Result to Log")


def run_todolist(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Todo List"), "window 'Todo List' is shown")
    for title, prio in (("Write the report", "High"), ("Buy milk", "Normal"), ("اتصل بأحمد", "Low")):
        d.set("txtTask", title), d.set("cboPriority", prio)
        d.click("cmdAdd")
    d.set("txtTask", "Water the plants")
    d.event("txtTask", "KeyPress", Ev("\r", "Return"))
    items = d.list_items("lstTasks")
    check(c, items[:1] == ["[ ] (!) Write the report"] and len(items) == 4, f"4 tasks (Enter adds): {items}")
    d.set("lstTasks", 1, "ListIndex")
    d.click("cmdDone")
    check(c, d.list_items("lstTasks")[1] == "[x] Buy milk", "Done marks the task")
    d.set("chkHideDone", 1, "Value")
    d.event("chkHideDone", "CheckedChanged")
    check(c, len(d.list_items("lstTasks")) == 3, "the filter hides completed tasks")
    d.set("lstTasks", 2, "ListIndex")              # "Water the plants"
    d.click("cmdUp")
    check(c, d.list_items("lstTasks")[1] == "[ ] (low) Water the plants", f"Move Up {d.list_items('lstTasks')}")
    data = json.loads((work / "todos.json").read_text(encoding="utf-8"))
    check(c, len(data) == 4 and any(t["title"] == "اتصل بأحمد" for t in data), "todos.json saved (Arabic kept)")
    d.click("mnuPurge")
    check(c, "1 completed" in d.msgs[-1], f"Remove Completed: {d.msgs[-1:]}")
    check(c, "3 open, 0 done, 1 high" in d.get("lblSummary", "Caption"), d.get("lblSummary", "Caption"))


QUIZ_EN = {"Which planet is the largest?": "Jupiter", "How many bits are in a byte?": "8", "What is 7 x 8?": "56",
           "Which language runs in every web browser?": "JavaScript", "The longest river in Africa is the...": "Nile",
           "H2O is the formula of...": "Water", "How many sides has a hexagon?": "6"}


def run_quiz(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Quiz Game"), "window 'Quiz Game' is shown")
    d.click("cmdStart")
    check(c, d.get("tmrQuestion", "Enabled") == "True", "the question Timer runs")
    d.pump(1300)
    check(c, int(d.get("prgTime", "Value")) < 10, f"time bar counts down ({d.get('prgTime', 'Value')})")
    for i in range(5):
        q = d.get("lblQuestion", "Caption")
        want = QUIZ_EN.get(q)
        btn = next((b for b in ("cmdA", "cmdB", "cmdC", "cmdD") if d.get(b, "Caption") == want), None)
        if btn is None:
            check(c, False, f"unknown question {q!r}")
            return
        if i == 4:      # answer the last one wrong
            btn = next(b for b in ("cmdA", "cmdB", "cmdC", "cmdD") if b != btn)
        d.click(btn)
    res = d.form("Results")
    check(c, res.loaded and res.ui.root.winfo_viewable(), "Results form is shown")
    ans = d.list_items("lstAnswers", form="Results")
    check(c, len(ans) == 5 and sum(a.startswith("✔") for a in ans) == 4, f"4 of 5 right: {ans}")
    check(c, "New best" in d.get("lblBest", "Caption", form="Results"), "best score recorded")
    check(c, json.loads((work / "quiz.best.json").read_text())["best"] > 0, "quiz.best.json written")
    d.click("cmdClose")
    check(c, not res.ui.root.winfo_viewable(), "Close hides the Results form")
    d.click("mnuArabic")
    check(c, d.get("cmdStart", "Caption") == "ابدأ" and "لعبة" in d.get("Form1", "Caption"), "Arabic interface")
    d.click("cmdStart")
    check(c, "؟" in d.get("lblQuestion", "Caption") or "..." in d.get("lblQuestion", "Caption"),
          f"Arabic question: {d.get('lblQuestion', 'Caption')}")
    d.set("tmrQuestion", False, "Enabled")


# ============================================================================ PHP forms
def run_invoice(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Invoice"), "window 'Invoice' is shown")
    for item, qty, price in (("Laptop", 2, "450"), ("Mouse", 3, "12.50")):
        d.set("txtItem", item), d.set("numQty", qty, "Value"), d.set("txtPrice", price)
        d.click("cmdAddLine")
    d.set("txtItem", "Cable"), d.set("txtPrice", "5")
    d.event("txtPrice", "KeyPress", Ev("\r", "Return"))
    check(c, d.get("grdLines", "Rows") == "4", f"3 lines in the grid (Rows={d.get('grdLines', 'Rows')})")
    check(c, d.call("grdLines", "TextMatrix", 2, 3) == "37.50", f"line total 3 x 12.50 = {d.call('grdLines', 'TextMatrix', 2, 3)}")
    check(c, d.get("lblSubtotal", "Caption") == "Subtotal: 942.50", d.get("lblSubtotal", "Caption"))
    check(c, d.get("lblTotal", "Caption") == "Total: 1,074.45", f"VAT 14%: {d.get('lblTotal', 'Caption')}")
    d.set("txtItem", "Bad"), d.set("txtPrice", "abc")
    d.click("cmdAddLine")
    check(c, "positive number" in d.msgs[-1], "a bad price is refused")
    d.set("txtItem", "Monitor"), d.set("txtPrice", "100")
    d.click("cmdAddLine")
    d.set("chkDiscount", 1, "Value")
    d.event("chkDiscount", "CheckedChanged")
    check(c, "Discount: -104.25" in d.get("lblSubtotal", "Caption"), d.get("lblSubtotal", "Caption"))
    d.set("cboTax", "0")
    d.event("cboTax", "SelectedIndexChanged")
    check(c, d.get("lblTotal", "Caption") == "Total: 938.25", d.get("lblTotal", "Caption"))
    target = work / "inv.txt"
    fake_file_dialogs([], [target])
    d.click("mnuSave")
    txt = target.read_text(encoding="utf-8") if target.exists() else ""
    check(c, "TOTAL: 938.25" in txt and "Laptop" in txt, "invoice saved as text")
    d.click("cmdRemove")
    check(c, d.get("grdLines", "Rows") == "4", "Remove Last")


def run_phpcontacts(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Contacts"), "window 'Contacts' is shown")
    check(c, len(d.list_items("lstContacts")) == 2, f"2 sample contacts: {d.list_items('lstContacts')}")
    d.set("lstContacts", 0, "ListIndex")         # sorted by name: ليلى sorts after Omar in SQLite (byte order)
    d.event("lstContacts", "SelectedIndexChanged")
    check(c, d.get("txtName") == "Omar Hassan", f"select loads the contact ({d.get('txtName')})")
    d.set("lstContacts", 1, "ListIndex")
    d.event("lstContacts", "SelectedIndexChanged")
    check(c, nl(d.get("txtNotes")) == "سطر أول\nسطر ثان", f"multi-line Arabic notes: {d.get('txtNotes')!r}")
    d.click("cmdNew")
    d.set("txtName", "Nour Adel"), d.set("txtCity", "Giza"), d.set("txtNotes", "line 1\nline 2")
    d.click("cmdSave")
    check(c, len(d.list_items("lstContacts")) == 3 and "Added" in d.get("lblInfo", "Caption"), "Save inserts")
    d.set("txtPhone", "0100")
    d.click("cmdSave")
    check(c, "Saved contact" in d.get("lblInfo", "Caption"), "second Save updates")
    d.set("txtSearch", "Giza")
    d.event("txtSearch", "TextChanged")
    check(c, d.list_items("lstContacts") == ["Nour Adel (Giza)"], f"search: {d.list_items('lstContacts')}")
    d.set("txtSearch", "")
    d.event("txtSearch", "TextChanged")
    d.answers = ["YES"]
    d.click("cmdDelete")
    check(c, len(d.list_items("lstContacts")) == 2, "Delete after confirmation")
    d.click("cmdNew")
    d.click("cmdSave")
    check(c, "required" in d.msgs[-1], "an empty name is refused")
    check(c, (work / "contacts.sqlite").exists(), "contacts.sqlite created")


def run_texttools(d: exlib.BridgeDriver, work: Path, c):
    check(c, d.window("Text Tools"), "window 'Text Tools' is shown")
    d.click("mnuSampleEn")
    check(c, "3 lines" in d.get("lblStats", "Caption"), d.get("lblStats", "Caption"))
    d.set("cboOp", "Remove extra spaces")
    d.click("cmdRun")
    check(c, nl(d.get("txtOutput")).split("\n")[1] == "jumps over the lazy dog.", f"{d.get('txtOutput')!r}")
    d.click("mnuSampleAr")
    d.set("cboOp", "Reverse")
    d.click("cmdRun")
    check(c, nl(d.get("txtOutput")).endswith("ابحرم"), f"Arabic reversed by characters: {d.get('txtOutput')!r}")
    d.set("cboOp", "Word count")
    d.click("cmdRun")
    check(c, nl(d.get("txtOutput")).startswith("9 words"), f"{nl(d.get('txtOutput'))[:20]!r}")
    d.set("cboOp", "Slug")
    d.set("txtInput", "Hello, World! 2026")
    d.click("cmdRun")
    check(c, d.get("txtOutput") == "hello-world-2026", d.get("txtOutput"))
    d.set("cboOp", "Base64 decode")
    d.set("txtInput", "%%%")
    d.click("cmdRun")
    check(c, "not valid Base64" in d.msgs[-1], "bad Base64 is reported")
    d.set("chkAuto", 1, "Value")
    d.set("cboOp", "UPPER CASE")
    d.set("txtInput", "auto run")
    d.event("txtInput", "TextChanged")
    check(c, d.get("txtOutput") == "AUTO RUN", "Run when typing")
    d.set("chkAuto", 0, "Value")
    d.click("mnuSwap")
    check(c, d.get("txtInput") == "AUTO RUN" and d.get("txtOutput") == "", "Swap Input/Output")


# ============================================================================ web sites
class Http:
    """A tiny browser: keeps cookies (PHP session + CSRF), follows redirects, JSON helpers."""

    def __init__(self, base: str):
        import http.cookiejar
        import urllib.request
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def req(self, method: str, path: str, data=None, json_body=None, headers=None) -> tuple[int, str]:
        import urllib.error
        import urllib.parse
        import urllib.request
        body, h = None, dict(headers or {})
        if json_body is not None:
            body, h["Content-Type"] = json.dumps(json_body).encode(), "application/json"
        elif data is not None:
            body, h["Content-Type"] = urllib.parse.urlencode(data).encode(), "application/x-www-form-urlencoded"
        r = urllib.request.Request(self.base + path, data=body, method=method, headers=h)
        try:
            with self.opener.open(r, timeout=20) as resp:
                return resp.status, resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")


def start_devserver(work: Path, timeout=180):
    """The IDE's dev server (what F5 starts for a web site project), headless."""
    exlib.qapp()
    from radide.languages import get_plugin
    from radide.model import Project
    from radide.web_site.server import DevServer
    project = Project.load(work)
    srv = DevServer(work, get_plugin(project.language), project)
    url = srv.start()
    ok = srv.wait_ready(timeout)
    return srv, url, ok


def web_publish(work: Path, res: exlib.Result, excludes=()):
    """Site > Publish with a 'Local folder' profile into the scratch folder."""
    from radide.model import Project
    from radide.web_site.publish import DEFAULT_EXCLUDES, Publisher, PublishProfile, local_root
    project = Project.load(work)
    dest = exlib.SCRATCH / "js_pub" / (work.name + "_site")
    shutil.rmtree(dest, ignore_errors=True)
    prof = PublishProfile(name="Local folder", kind="folder", remote_dir=str(dest),
                          excludes=list(DEFAULT_EXCLUDES) + list(excludes))
    lines = []
    r = Publisher(prof, local_root(project, prof)).run(log=lines.append)
    size = exlib.dir_size(dest) if dest.exists() else 0
    res.step("publish", r.ok and not r.failed and len(r.uploaded) > 0,
             f"kind=site folder: {len(r.uploaded)} file(s), {exlib.mb(size)} MB, python_inside=False ({r.summary()})")
    res["size"] = f"{exlib.mb(size)} MB"
    res["publish_info"] = {"kind": "site-folder", "files": len(r.uploaded), "size_mb": exlib.mb(size),
                           "python_inside": False}
    return dest


def site_files_check(work: Path) -> tuple[bool, str]:
    bad, n = [], 0
    for f in work.rglob("*"):
        if "node_modules" in f.parts or f.suffix not in (".js", ".php"):
            continue
        n += 1
        cmd = [NODE, "--check", str(f)] if f.suffix == ".js" else [php_exe(), "-l", str(f)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            bad.append(f"{f.name}: {(r.stdout + r.stderr).strip()[-200:]}")
    return not bad, (f"{n} file(s) ok" if not bad else "; ".join(bad))


def web_open(folder: Path, res: exlib.Result):
    from radide.languages import get_plugin
    from radide.model import Project
    p = Project.load(folder)
    plugin = get_plugin(p.language)
    res.step("open", p.kind == "website" and getattr(plugin, "project_kind", "") == "website",
             f"website project ({p.language}, root={p.extra.get('web', {}).get('root')})")


def test_guestbook(folder: Path, res: exlib.Result, opts: dict):
    import re
    web_open(folder, res)
    work = exlib.temp_copy(folder, "js")
    shutil.rmtree(work / "data", ignore_errors=True)
    res.step("build", *site_files_check(work))
    srv, url, ready = start_devserver(work)
    c = []
    try:
        check(c, ready and url, f"dev server ready at {url}")
        b = Http(url)
        code, html = b.req("GET", "/")
        check(c, code == 200 and "Guestbook" in html and "No messages yet" in html, f"GET / -> {code}")
        tok = re.search(r'name="csrf" value="([0-9a-f]+)"', html).group(1)
        for i in range(7):
            name, msg = ("سارة", "رسالة رقم %d" % i) if i == 3 else (f"Guest {i}", f"Hello number {i}")
            code, html = b.req("POST", "/", {"csrf": tok, "action": "add", "name": name, "message": msg})
        check(c, code == 200 and "Thank you" in html and "Hello number 6" in html, "POST add -> redirect + flash")
        check(c, "Hello number 1" not in html and "1 / 2" in html, "5 per page, newest first, 2 pages")
        code, page2 = b.req("GET", "/?page=2")
        check(c, "Hello number 1" in page2 and "Hello number 0" in page2, "page 2 has the oldest")
        code, html = b.req("POST", "/", {"csrf": "bad", "action": "add", "name": "x", "message": "y"})
        check(c, "expired" in html, "a wrong CSRF token is refused")
        code, html = b.req("POST", "/", {"csrf": tok, "action": "add", "name": "", "message": "y"})
        check(c, "Please write your name" in html, "validation message")
        mid = re.findall(r'name="id" value="(\d+)"', html)
        check(c, len(mid) == 5, f"delete buttons only for own messages ({len(mid)})")
        code, html = b.req("POST", "/", {"csrf": tok, "action": "delete", "id": mid[0]})
        check(c, "was deleted" in html and "Hello number 6" not in html, "POST delete")
        other = Http(url)
        code, html2 = other.req("GET", "/")
        tok2 = re.search(r'name="csrf" value="([0-9a-f]+)"', html2).group(1)
        other.req("POST", "/", {"csrf": tok2, "action": "delete", "id": mid[1]})
        code, api = b.req("GET", "/api.php")
        data = json.loads(api)
        check(c, data["total"] == 6 and any(m["name"] == "سارة" for m in data["messages"]),
              "another visitor cannot delete; /api.php JSON with Arabic")
        code, ar = b.req("GET", "/?lang=ar")
        check(c, 'dir="rtl"' in ar and "سجل الزوار" in ar, "Arabic interface, RTL")
        code, _ = b.req("GET", "/../data/guestbook.sqlite")
        check(c, code == 404 or code == 400 or code == 403, f"the database is not downloadable ({code})")
        check(c, (work / "data" / "guestbook.sqlite").exists(), "data/guestbook.sqlite created")
    finally:
        srv.stop()
    bad = [m for ok, m in c if not ok]
    res.step("run", not bad, f"{len(c) - len(bad)}/{len(c)} checks" + (f"; failed: {bad}" if bad else ""))
    if opts.get("publish"):
        dest = web_publish(work, res)
        if not (dest / "public" / "index.php").exists() or (dest / "data" / "guestbook.sqlite").exists():
            res.step("publish", False, "published folder must have public/index.php and no live database")


def test_quickpoll(folder: Path, res: exlib.Result, opts: dict):
    web_open(folder, res)
    work = exlib.temp_copy(folder, "js")
    shutil.rmtree(work / "data", ignore_errors=True)
    res.step("build", *site_files_check(work))
    srv, url, ready = start_devserver(work)          # runs npm install first (node_modules is not in samples/)
    c = []
    try:
        check(c, ready and url, f"dev server ready at {url} (npm install + node server.js)")
        exlib.wait(lambda: Http(url).req("GET", "/api/polls")[0] == 200, 60, 0.5)
        b = Http(url)
        code, html = b.req("GET", "/")
        check(c, code == 200 and "QuickPoll" in html, f"GET / -> {code}")
        code, js = b.req("GET", "/js/app.js")
        check(c, code == 200 and "applyLanguage" in js, "static front end")
        code, body = b.req("POST", "/api/polls", json_body={"question": "Best language?",
                                                            "options": ["Python", "JavaScript", "العربية"]})
        poll = json.loads(body)
        check(c, code == 201 and poll["votes"] == [0, 0, 0], f"create poll -> {code}")
        code, body = b.req("POST", "/api/polls", json_body={"question": "x", "options": ["a"]})
        check(c, code == 400, "validation (400)")
        pid = poll["id"]
        for voter, opt in (("v1", 0), ("v2", 2), ("v3", 0)):
            code, body = b.req("POST", f"/api/polls/{pid}/vote", json_body={"option": opt}, headers={"X-Voter": voter})
        check(c, json.loads(body)["votes"] == [2, 0, 1], f"votes counted: {body[:80]}")
        code, _ = b.req("POST", f"/api/polls/{pid}/vote", json_body={"option": 1}, headers={"X-Voter": "v1"})
        check(c, code == 409, "a second vote of the same voter is refused (409)")
        code, body = b.req("GET", "/api/polls")
        check(c, code == 200 and json.loads(body)[0]["total"] == 3 and "voters" not in body, "list hides voters")
        code, _ = b.req("DELETE", f"/api/polls/{pid}")
        code2, _ = b.req("GET", f"/api/polls/{pid}")
        check(c, code == 204 and code2 == 404, "delete")
        check(c, (work / "data" / "polls.json").exists(), "data/polls.json written")
    finally:
        srv.stop()
    bad = [m for ok, m in c if not ok]
    res.step("run", not bad, f"{len(c) - len(bad)}/{len(c)} checks" + (f"; failed: {bad}" if bad else ""))
    if opts.get("publish"):
        web_publish(work, res, excludes=["node_modules", "data"])


# ============================================================================ registry
EXAMPLES = {
    "JavaScript/Notepad": {"lang": "javascript", "test": form_project(run_notepad)},
    "JavaScript/Calculator": {"lang": "javascript", "test": form_project(run_calculator)},
    "JavaScript/Contacts": {"lang": "javascript", "test": form_project(run_contacts)},
    "JavaScript/FocusTimer": {"lang": "javascript", "test": form_project(run_focustimer)},
    "TypeScript/UnitConverter": {"lang": "typescript", "test": form_project(run_unitconverter)},
    "TypeScript/TodoList": {"lang": "typescript", "test": form_project(run_todolist)},
    "TypeScript/QuizGame": {"lang": "typescript", "test": form_project(run_quiz)},
    "PHP/Invoice": {"lang": "php", "test": form_project(run_invoice)},
    "PHP/ContactsPDO": {"lang": "php", "test": form_project(run_phpcontacts)},
    "PHP/TextTools": {"lang": "php", "test": form_project(run_texttools)},
    "PHPWeb/Guestbook": {"lang": "php-web", "test": test_guestbook},
    "NodeWeb/QuickPoll": {"lang": "node-web", "test": test_quickpoll},
}
