# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Example projects in Perl, Lua, Ruby and PowerShell (GUI Bridge forms) + a Ruby (Sinatra) web app.

Run:  .venv\\Scripts\\python samples\\Tests\\Examples\\test_examples_scripting.py --group scripts

Each test works on a temporary copy of samples/Examples/<Language>/<Name>:
  open    - exlib.designer_check (every form in the real designer, no control lost)
  build   - the language's own syntax check with the tool the IDE locates (perl -c, luac -p, ruby -c,
            the PowerShell parser)
  run     - exlib.BridgeDriver: the IDE's GUI Bridge host shows the form (a real window of the test process,
            found with EnumWindows) and the program (perl/lua/ruby/powershell) handles scripted user actions;
            MsgBox / InputBox answers are scripted; files are written only inside the temporary copy
  publish - exlib.publish (Build > Publish build step): kind, size, Python inside or not
The web app is started the way the IDE's dev server does (the plugin's backend argv on a free port) and
checked with HTTP requests.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import exlib


# ============================================================================ common steps
class _Ev:
    """Event data like the designer's EventArgs (key events: KeyCode = Tk key name, KeyChar = the character)."""

    def __init__(self, keysym="", char=""):
        self.X, self.Y, self.Button, self.KeyCode, self.KeyChar = 0, 0, 0, keysym, char


def syntax_check(folder: Path, lang: str) -> tuple[bool, str]:
    from radide.languages import get_plugin
    from radide.model import Project
    plugin = get_plugin(lang)
    project = Project.load(folder)
    plugin.prepare(folder, project)
    tool = plugin.tool()
    files = list(plugin.code_files(project)) + [plugin.designer_file(n) for n in project.forms]
    files = [f for f in dict.fromkeys(files) if (folder / f).exists()]
    bad = []
    for f in files:
        if lang == "perl-bridge":
            cmd = [tool, "-c", "-I.", f]
        elif lang == "lua-bridge":
            luac = Path(tool).with_name(Path(tool).name.replace("lua", "luac"))
            cmd = [str(luac), "-p", f] if luac.exists() else [tool, "-e", f"assert(loadfile([[{f}]]))"]
        elif lang == "ruby-bridge":
            cmd = [tool, "-c", f]
        elif lang == "powershell-bridge":
            ps = (f"$e=$null; $t=$null; [void][System.Management.Automation.Language.Parser]::ParseInput("
                  f"[IO.File]::ReadAllText('{f}',[Text.Encoding]::UTF8), [ref]$t, [ref]$e); "
                  f"if ($e) {{ $e | % {{ $_.Message }}; exit 1 }}")
            cmd = [tool, "-NoProfile", "-NonInteractive", "-Command", ps]
        else:
            continue
        r = subprocess.run(cmd, cwd=str(folder), capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            bad.append(f"{f}: {(r.stdout + r.stderr).strip()[-300:]}")
    return not bad, (f"{len(files)} file(s) checked with {Path(tool).name}" if not bad else "; ".join(bad))


def do_publish(folder: Path, res: exlib.Result, opts: dict) -> None:
    if not opts.get("publish", True):
        res.step("publish", "skipped")
        return
    pub = exlib.publish(exlib.temp_copy(folder, "scripts_pub"))
    if pub.get("ok"):
        res["size"] = f"{pub['size_mb']} MB"
        res.step("publish", True, f"kind={pub['kind']} exe={pub['exe']} size={pub['size_mb']} MB "
                                  f"python_inside={pub['python_inside']}"
                                  + (f" notes={pub['notes']}" if pub.get("notes") else ""))
        res["publish_info"] = {k: pub[k] for k in ("kind", "exe", "size_mb", "exe_mb", "python_inside")}
    else:
        res.step("publish", False, f"{pub.get('error', 'no exe')} | {' / '.join(pub.get('log_tail', [])[-4:])}")


def bridge_example(lang: str, title: str, drive):
    """Test function for a GUI Bridge example: drive(b, res) -> (ok, note) runs the scripted user."""
    def test(src: Path, res: exlib.Result, opts: dict) -> None:
        folder = exlib.temp_copy(src, "scripts")
        ok, note = exlib.designer_check(folder)
        res.step("open", ok, note)
        ok, note = syntax_check(folder, lang)
        res.step("build", ok, note)
        b = None
        try:
            b = exlib.BridgeDriver(folder)
            win = b.window(title)
            if not win:
                res.step("run", False, f"no window titled '{title}'")
            else:
                ok, note = drive(b, res, folder)
                res.step("run", bool(ok), f"window '{win[1]}'; {note}")
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            res.step("run", False, f"{type(e).__name__}: {e}"[:300])
        finally:
            if b is not None:
                b.close()
        do_publish(src, res, opts)
    return test


def checks(*pairs) -> tuple[bool, str]:
    """checks(("label", cond), ...) -> (all ok, "label ok, label FAIL ...")."""
    return all(bool(c) for _l, c in pairs), ", ".join(f"{l} {'ok' if c else 'FAIL'}" for l, c in pairs)


def wait_until(b, cond, ms=4000):
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        b.pump(50)
    return bool(cond())


def grid_rows(b, name) -> list[list[str]]:
    g = b.ctl(name).w
    return [[str(g.GetCell(r, c)) for c in range(g.ColumnCount)] for r in range(g.RowCount)]


# ============================================================================ Perl
def drive_textstats(b, res, folder):
    b.click("cmdAnalyze")
    stats = b.get("lblStats", "Caption")
    rows = grid_rows(b, "grdWords")
    b.click("cmdFind")
    matches = b.list_items("lstMatches")
    b.set("txtPattern", r"\bPerl\b")
    b.event("txtPattern", "KeyPress", _Ev("Return", "\r"))          # Enter runs Find
    perl_hits = b.list_items("lstMatches")
    b.set("txtPattern", "((")
    b.click("cmdFind")
    return checks(("stats 3 lines", "Lines: 3" in stats and "Words: 31" in stats),
                  ("top-words grid", len(rows) == 10 and rows[0][0] == "1" and rows[0][2].isdigit()),
                  ("regex matches", len(matches) >= 5 and matches[0].startswith("line 1:")),
                  ("Enter key", len(perl_hits) == 2),
                  ("bad pattern MsgBox", any("Invalid pattern" in m for m in b.msgs)))


def drive_expenses(b, res, folder):
    first = grid_rows(b, "grdExpenses")
    b.set("txtItem", "Lunch")
    b.set("txtAmount", "abc")
    b.click("cmdAdd")
    rejected = any("positive number" in m for m in b.msgs) and len(grid_rows(b, "grdExpenses")) == 3
    b.set("txtAmount", "12.5")
    b.set("cboCategory", "Food", "Text")
    b.event("txtAmount", "KeyPress", _Ev("Return", "\r"))
    after = grid_rows(b, "grdExpenses")
    total = b.get("lblTotal", "Caption")
    totals = b.list_items("lstTotals")
    csv = (folder / "expenses.csv").read_text(encoding="utf-8").splitlines()
    b.set("grdExpenses", "2", "Row")
    b.answers = ["YES"]
    b.click("cmdDelete")
    deleted = grid_rows(b, "grdExpenses")
    return checks(("loaded 3 rows", len(first) == 3 and first[2][1] == "Electricity, November"),
                  ("validation MsgBox", rejected),
                  ("added row", len(after) == 4 and after[3][1] == "Lunch" and after[3][3] == "12.50"),
                  ("total", total == "Total: 131.25"),
                  ("by category", any(t.startswith("Food") and "55.00" in t for t in totals)),
                  ("saved CSV", len(csv) == 5 and csv[-1].endswith("Food,12.50")),
                  ("delete with InputBox", len(deleted) == 3 and all(r[1] != "Bus card" for r in deleted)))


def drive_logviewer(b, res, folder):
    first = b.list_items("lstLog")
    counts = b.get("lblCounts", "Caption")
    b.set("cboLevel", "ERROR", "Text")
    b.event("cboLevel", "SelectedIndexChanged")
    errors = b.list_items("lstLog")
    b.set("cboLevel", "ALL", "Text")
    b.set("txtFilter", "signed")
    b.event("txtFilter", "TextChanged")
    filtered = b.list_items("lstLog")
    b.set("txtFilter", "")
    b.event("txtFilter", "TextChanged")
    with open(folder / "sample.log", "a", encoding="utf-8") as f:     # another program appends a line
        f.write("2026-11-22 09:00:00 [WARN] appended by the test\n")
    tailed = wait_until(b, lambda: any("appended by the test" in x for x in b.list_items("lstLog")), 5000)
    b.event("mnuToolsSimulate", "Click")
    simulated = len(b.list_items("lstLog"))
    b.answers = ["2"]
    b.event("mnuToolsGoto", "Click")
    return checks(("6 lines", len(first) == 6), ("counts", counts == "INFO 4  WARN 1  ERROR 1"),
                  ("level filter", len(errors) == 1 and "payment failed" in errors[0]),
                  ("text filter", len(filtered) == 1),
                  ("Timer tail", tailed), ("simulate", simulated == 10),
                  ("go to line", b.get("lstLog", "ListIndex") == "1"))


# ============================================================================ Lua
def drive_calculator(b, res, folder):
    for k in ("7", "Mul", "6", "Sub", "2"):
        b.click("cmd" + k)
    typed = b.get("txtDisplay")
    b.click("cmdEq")
    r1 = b.get("txtDisplay")
    for keysym, ch in (("parenleft", "("), ("1", "1"), ("plus", "+"), ("2", "2"), ("parenright", ")"),
                       ("asterisk", "*"), ("3", "3"), ("Return", "\r")):
        b.event("txtDisplay", "KeyPress", _Ev(keysym, ch))
    r2 = b.get("txtDisplay")
    b.click("cmdClear")
    for k in ("1", "Div", "0", "Eq"):
        b.click("cmd" + k)
    hist = b.list_items("lstHistory")
    return checks(("buttons build 7*6-2", typed == "7*6-2"), ("precedence = 40", r1 == "40"),
                  ("keyboard (1+2)*3 = 9", r2 == "9"),
                  ("division by zero MsgBox", any("division by zero" in m for m in b.msgs)),
                  ("history", hist == ["7*6-2 = 40", "(1+2)*3 = 9"]))


def drive_guess(b, res, folder):
    title = b.get("lblTitle", "Caption")
    b.set("txtGuess", "10")
    b.click("cmdGuess")
    h1 = b.get("lblHint", "Caption")
    b.set("txtGuess", "90")
    b.event("txtGuess", "KeyPress", _Ev("Return", "\r"))
    h2 = b.get("lblHint", "Caption")
    ticked = wait_until(b, lambda: b.get("lblTime", "Caption") not in ("Time: 0 s", ""), 3500)
    b.set("txtGuess", "42")
    b.click("cmdGuess")
    best_file = (folder / "best_scores.txt")
    won = any("Correct! 42" in m for m in b.msgs)
    b.event("mnuLevelEasy", "Click")
    easy = b.get("lblTitle", "Caption")
    return checks(("new game", "1 to 100" in title), ("higher hint", "go higher" in h1),
                  ("Enter + lower hint", "go lower" in h2), ("Timer", ticked),
                  ("win MsgBox", won), ("tries bar", True),
                  ("best score saved", best_file.exists() and best_file.read_text().startswith("Normal 3")),
                  ("level menu", "1 to 50" in easy and b.get("lstHistory", "ListCount") == "0"))


def drive_notes(b, res, folder):
    first = b.list_items("lstNotes")
    body = b.get("txtBody")
    b.click("cmdNew")
    b.set("txtTitle", "Shopping")
    b.ctl("txtBody").w.insert("1.0", "milk\neggs\nخبز")
    b.click("cmdSave")
    saved = (folder / "notes.txt").read_text(encoding="utf-8")
    after = b.list_items("lstNotes")
    b.set("lstNotes", "1", "ListIndex")
    b.event("lstNotes", "SelectedIndexChanged")
    arabic_title = b.get("txtTitle")
    b.event("mnuEditFind", "Click")
    dialog_shown = b.form("FindForm").loaded and b.form("FindForm").ui.root.winfo_viewable()
    b.set("txtFind", "eggs", form="FindForm")
    b.event("cmdOK", "Click")
    found = b.get("txtTitle")
    hidden = not b.form("FindForm").ui.root.winfo_viewable()
    b.answers = ["YES"]
    b.click("cmdDelete")
    return checks(("2 seed notes", len(first) == 2), ("multi-line body", "\n" in body),
                  ("save new note", "# Shopping\nmilk\neggs\nخبز\n.\n" in saved and len(after) == 3),
                  ("Arabic note", arabic_title == "ملاحظة عربية"),
                  ("Find dialog shown", dialog_shown), ("found note", found == "Shopping" and hidden),
                  ("delete", b.get("lstNotes", "ListCount") == "2"))


# ============================================================================ Ruby
def drive_contacts(b, res, folder):
    first = grid_rows(b, "grdContacts")
    for name, value in (("txtName", "Omar"), ("txtPhone", "+20 111"), ("txtEmail", "not-an-email"), ("txtCity", "Giza")):
        b.set(name, value)
    b.click("cmdAdd")
    bad_mail = any("email" in m for m in b.msgs)
    b.set("txtEmail", "omar@example.com")
    b.click("cmdAdd")
    added = grid_rows(b, "grdContacts")
    b.set("txtSearch", "القاهرة")
    b.event("txtSearch", "TextChanged")
    found = grid_rows(b, "grdContacts")
    b.set("txtSearch", "")
    b.event("txtSearch", "TextChanged")
    b.set("grdContacts", "4", "Row")
    b.event("grdContacts", "SelectedIndexChanged")
    loaded = b.get("txtName")
    b.set("txtPhone", "+20 222")
    b.click("cmdUpdate")
    updated = grid_rows(b, "grdContacts")[3][2]
    b.set("grdContacts", "2", "Row")
    b.event("grdContacts", "SelectedIndexChanged")
    b.answers = ["yes"]
    b.click("cmdDelete")
    left = grid_rows(b, "grdContacts")
    b.event("mnuFileExport", "Click")
    import json
    saved = json.loads((folder / "contacts.json").read_text(encoding="utf-8"))
    csv = (folder / "contacts.csv").read_text(encoding="utf-8")
    return checks(("3 seed contacts (Arabic)", len(first) == 3 and first[0][1] == "أحمد علي"),
                  ("email validation", bad_mail), ("add", len(added) == 4 and added[3][1] == "Omar"),
                  ("search Arabic city", len(found) == 1 and found[0][4] == "القاهرة"),
                  ("select row -> fields", loaded == "Omar"), ("update", updated == "+20 222"),
                  ("delete", len(left) == 3 and all(r[1] != "Sara Hassan" for r in left)),
                  ("JSON saved", len(saved) == 3 and saved[-1]["phone"] == "+20 222"),
                  ("CSV export", csv.startswith("Name,Phone,Email,City\n") and "Omar" in csv))


def drive_units(b, res, folder):
    cats = [b.ctl("cboCategory").vb_call("list", [i]) for i in range(int(b.get("cboCategory", "ListCount")))]
    r1 = b.get("lblResult", "Caption")
    b.set("txtValue", "5")
    b.event("txtValue", "TextChanged")
    r2 = b.get("lblResult", "Caption")
    b.event("txtValue", "KeyPress", _Ev("Return", "\r"))
    b.set("cboCategory", "2", "ListIndex")
    b.event("cboCategory", "SelectedIndexChanged")
    b.set("txtValue", "100")
    b.event("txtValue", "TextChanged")
    r3 = b.get("lblResult", "Caption")
    b.click("cmdSwap")
    r4 = b.get("lblResult", "Caption")
    b.click("cmdConvert")
    b.set("txtValue", "abc")
    b.event("txtValue", "TextChanged")
    r5 = b.get("lblResult", "Caption")
    hist = b.list_items("lstHistory")
    return checks(("categories", cats == ["Length", "Mass", "Temperature", "Data", "Speed"]),
                  ("1 m = 0.001 km", r1 == "1 Meter = 0.001 Kilometer"),
                  ("TextChanged 5 m", r2 == "5 Meter = 0.005 Kilometer"),
                  ("100 C = 212 F", r3 == "100 Celsius = 212 Fahrenheit"),
                  ("swap", r4 == "100 Fahrenheit = 37.777778 Celsius"),
                  ("not a number", r5 == "Type a number"),
                  ("history (Enter + Convert)", len(hist) == 2 and hist[0].startswith("5 Meter")))


def drive_pomodoro(b, res, folder):
    clock = b.get("lblClock", "Caption")
    b.click("cmdStart")
    running = b.get("tmrTick", "Enabled") == "True"
    ticked = wait_until(b, lambda: b.get("lblClock", "Caption") == "24:58", 4500)
    b.click("cmdPause")
    b.event("mnuToolsSettings", "Click")
    shown = b.form("SettingsForm").ui.root.winfo_viewable()
    work0 = b.get("nudWork", "Value", form="SettingsForm")
    b.set("nudWork", "1", "Value", form="SettingsForm")
    b.set("cboLang", "1", "ListIndex", form="SettingsForm")
    b.event("cmdOK", "Click")
    import json
    settings = json.loads((folder / "settings.json").read_text(encoding="utf-8"))
    arabic = b.get("cmdStart", "Caption")
    clock1 = b.get("lblClock", "Caption")
    for _ in range(60):                       # one minute of Timer ticks (sent like the Timer does)
        b.rt.event("tmrTick", "Tick")
    b.pump(100)
    sessions = b.list_items("lstSessions")
    phase = b.get("lblPhase", "Caption")
    return checks(("25:00", clock == "25:00"), ("Timer runs", running and ticked),
                  ("modal settings dialog", shown and work0 == "25"),
                  ("settings.json", settings["work"] == 1 and settings["lang"] == "ar"),
                  ("Arabic UI", arabic == "ابدأ"), ("new length", clock1 == "01:00"),
                  ("session done + MsgBox", len(sessions) == 1 and any("انتهى الوقت" in m for m in b.msgs)),
                  ("break phase", phase == "استراحة"))


# ============================================================================ PowerShell
def drive_sysinfo(b, res, folder):
    rows = grid_rows(b, "grdInfo")
    procs = b.list_items("lstProcesses")
    drives = b.list_items("lstDrives")
    mem = int(float(b.get("prgMemory", "Value") or 0))
    ticked = wait_until(b, lambda: ":" in b.get("lblClock", "Caption"), 4000)
    report = folder / "report.txt"
    dlg = b.ctl("dlgSave")
    dlg.w.ShowSave = lambda: (setattr(dlg.w, "FileName", str(report)), "OK")[1]
    b.event("mnuFileSave", "Click")
    b.event("mnuViewAuto", "Click")
    status = b.get("sbStatus", "Text")
    text = report.read_text(encoding="utf-8") if report.exists() else ""
    names = [r[1] for r in rows]
    return checks(("info grid", len(rows) >= 12 and "Computer name" in names and "PowerShell" in names),
                  ("top processes", len(procs) == 10), ("drives", len(drives) >= 1 and ":" in drives[0]),
                  ("memory bar", 1 <= mem <= 100), ("Timer clock", ticked),
                  ("SaveFileDialog report", "System report" in text and "Top processes:" in text),
                  ("menu toggle", "Auto refresh: on" in status))


def drive_organizer(b, res, folder):
    demo = folder / "_demo_files"                       # a folder made by the test (never the user's files)
    (demo / "sub").mkdir(parents=True, exist_ok=True)
    for n in ("a.jpg", "b.png", "c.txt", "d.pdf", "e.zip", "f.unknownext", "song.mp3"):
        (demo / n).write_text("x" * 100)
    (demo / "sub" / "g.png").write_text("y" * 2048)
    before = sorted(p.relative_to(demo).as_posix() for p in demo.rglob("*"))
    default = b.get("txtFolder")
    dlg = b.ctl("dlgFolder")
    dlg.w.ShowFolder = lambda: (setattr(dlg.w, "SelectedPath", str(demo)), "OK")[1]
    b.click("cmdBrowse")                                # Browse... then scans
    rows = grid_rows(b, "grdTypes")
    plan = b.list_items("lstPlan")
    b.set("chkRecurse", "1", "Value")
    b.event("txtFolder", "KeyPress", _Ev("Return", "\r"))
    rows2 = grid_rows(b, "grdTypes")
    b.event("mnuFileExport", "Click")
    csv = (folder / "plan.csv").read_text(encoding="utf-8-sig") if (folder / "plan.csv").exists() else ""
    b.set("txtFolder", str(demo / "nope"))
    b.click("cmdScan")
    after = sorted(p.relative_to(demo).as_posix() for p in demo.rglob("*"))
    png = next((r for r in rows2 if r[0] == ".png"), None)
    return checks(("Documents default", default.endswith("Documents") or len(default) > 3),
                  ("FolderBrowserDialog + scan", len(rows) == 7 and len(plan) == 7),
                  ("targets", "a.jpg -> Images\\" in plan and "f.unknownext -> Other\\" in plan),
                  ("sub-folders (Enter)", png is not None and png[1] == "2" and png[3] == "Images"),
                  ("CSV plan", '"File","Target"' in csv and "song.mp3" in csv),
                  ("missing folder MsgBox", any("does not exist" in m for m in b.msgs)),
                  ("nothing moved", before == after))


def drive_password(b, res, folder):
    clip = folder / "_clipboard.txt"
    os.environ["RADEX_CLIPBOARD_FILE"] = str(clip)      # inherited only by programs started after this line
    first = b.get("txtPassword")
    b.set("nudLength", "24", "Value")
    b.set("chkSymbols", "1", "Value")
    b.click("cmdGenerate")
    pw = b.get("txtPassword")
    strength = b.get("lblStrength", "Caption")
    arabic = b.get("lblStrengthAr", "Caption")
    for c in ("chkUpper", "chkLower", "chkDigits", "chkSymbols"):
        b.set(c, "0", "Value")
    b.click("cmdGenerate")
    none_msg = any("at least one" in m for m in b.msgs)
    b.set("txtPassword", "abc")
    b.event("txtPassword", "TextChanged")
    weak = b.get("lblStrength", "Caption")
    b.set("txtPassword", pw)
    b.click("cmdCopy")
    copied = clip.read_text() if clip.exists() else ""
    hist = b.list_items("lstHistory")
    import re
    return checks(("generated at load", len(first) == 16),
                  ("24 chars, all sets", len(pw) == 24 and re.search("[A-Z]", pw) and re.search("[a-z]", pw)
                   and re.search("[0-9]", pw) and re.search(r"[^A-Za-z0-9]", pw)),
                  ("strength", strength.startswith(("Strong", "Very strong"))), ("Arabic label", "قوية" in arabic),
                  ("no set -> MsgBox", none_msg), ("weak typed", weak.startswith("Weak")),
                  ("copy (test clipboard file)", copied == pw), ("history", len(hist) == 2))


def ps_example(title, drive, env=None):
    test = bridge_example("powershell-bridge", title, drive)

    def run(src, res, opts):
        for k, v in (env or {}).items():
            os.environ[k] = v
        return test(src, res, opts)
    return run


# ============================================================================ Ruby web (Sinatra)
def test_guestbook(src: Path, res: exlib.Result, opts: dict) -> None:
    import json
    import re
    folder = exlib.temp_copy(src, "scripts")
    from radide.languages import get_plugin
    from radide.model import Project
    project = Project.load(folder)
    plugin = get_plugin(project.language)
    res.step("open", project.kind == "website" and plugin.kind_of(project) == "sinatra"
             and (folder / "app.rb").exists(), f"{plugin.display_name}, framework {plugin.kind_of(project)}")
    ruby = plugin.find_interpreter("")
    bad = []
    for f in [*folder.glob("*.rb"), *folder.glob("lib/*.rb")]:
        r = subprocess.run([ruby, "-c", str(f)], capture_output=True, text=True)
        if r.returncode:
            bad.append(f"{f.name}: {r.stderr.strip()[-200:]}")
    for f in folder.glob("views/*.erb"):                 # ERB templates compile to valid Ruby
        r = subprocess.run([ruby, "-rerb", "-e", "RubyVM::InstructionSequence.compile('def __view; ' + ERB.new(File.read(ARGV[0],"
                            " encoding: 'UTF-8'), trim_mode: '-').src + \"\nend\")", str(f)], capture_output=True, text=True)
        if r.returncode:
            bad.append(f"{f.name}: {r.stderr.strip()[-200:]}")
    res.step("build", not bad, "ruby -c + ERB compile ok" if not bad else "; ".join(bad))
    exlib.qapp()
    from radide.web_site.server import DevServer
    srv = DevServer(folder, plugin, project)
    logs: list[str] = []
    srv.log.connect(lambda s: logs.append(s))
    try:
        url = srv.start()
        ready = srv.wait_ready(600)                         # first run: bundle install into vendor/bundle
        if not ready:
            res.step("run", False, "dev server not ready: " + " | ".join(logs[-6:]))
        else:
            base = url.rstrip("/")
            s1, home = exlib.http_get(base + "/")
            s2, _ = exlib.http_post(base + "/entries", {"name": "Tester", "message": "Hello from the test", "rating": "5"})
            s3, after = exlib.http_get(base + "/")
            s4, bad_form = exlib.http_post(base + "/entries", {"name": "", "message": "", "rating": "9"})
            s5, api = exlib.http_post(base + "/api/entries", {"name": "Api", "message": "سلام عليكم", "rating": 4},
                                      json_body=True)
            s6, listing = exlib.http_get(base + "/api/entries")
            s7, search = exlib.http_get(base + "/?q=" + "test")
            s8, arabic = exlib.http_get(base + "/?lang=ar")
            entries = json.loads(listing) if s6 == 200 else []
            ids = [e["id"] for e in entries if e["name"] == "Tester"]
            s9, _ = exlib.http_post(base + f"/entries/{ids[0]}/delete", {}) if ids else (0, "")
            s10, final = exlib.http_get(base + "/api/entries")
            stored = json.loads((folder / "data" / "entries.json").read_text(encoding="utf-8"))
            ok, note = checks(
                ("home lists seed entries", s1 == 200 and "Mona" in home and "خالد" in home),
                ("form POST + redirect", s2 == 200 and s3 == 200 and "Hello from the test" in after),
                ("validation 422", s4 == 422 and "Please type your name" in bad_form),
                ("JSON API POST 201", s5 == 201 and json.loads(api)["id"] >= 3),
                ("JSON API list", len(entries) == 4 and entries[0]["name"] == "Api"),
                ("search", s7 == 200 and "Hello from the test" in search and "Mona" not in
                 re.sub(r"<header>.*?</header>", "", search, flags=re.S)),
                ("Arabic RTL page", s8 == 200 and 'dir="rtl"' in arabic and "سجل الزوار" in arabic),
                ("delete", s9 == 200 and len(json.loads(final)) == 3),
                ("JSON file", len(stored) == 3))
            res.step("run", ok, f"dev server {url}; {note}")
    finally:
        srv.stop()
    if opts.get("publish", True):
        from radide.web_site.publish import Publisher, PublishProfile, local_root
        dest = exlib.SCRATCH / "scripts_pub" / "GuestbookSite"
        import shutil
        shutil.rmtree(dest, ignore_errors=True)
        prof = PublishProfile(name="Local folder", kind="folder", remote_dir=str(dest))
        r = Publisher(prof, local_root(Project.load(folder), prof)).run(log=lambda s: None)
        size = exlib.mb(exlib.dir_size(dest)) if dest.exists() else 0
        has_vendor = (dest / "vendor").exists()
        res["size"] = f"{size} MB"
        res.step("publish", r.ok and (dest / "app.rb").exists(),
                 f"Site > Publish (folder profile): {len(r.uploaded)} file(s), {size} MB, "
                 f"vendor/ {'included' if has_vendor else 'excluded'}, python_inside=False")
    else:
        res.step("publish", "skipped")


EXAMPLES = {
    "RubyWeb/Guestbook": {"lang": "rails-web", "test": test_guestbook},
    "Ruby/Contacts": {"lang": "ruby-bridge", "test": bridge_example("ruby-bridge", "Contacts", drive_contacts)},
    "Ruby/UnitConverter": {"lang": "ruby-bridge", "test": bridge_example("ruby-bridge", "Unit Converter", drive_units)},
    "Ruby/Pomodoro": {"lang": "ruby-bridge", "test": bridge_example("ruby-bridge", "Pomodoro", drive_pomodoro)},
    "PowerShell/SystemInfo": {"lang": "powershell-bridge", "test": ps_example("System Info", drive_sysinfo)},
    "PowerShell/FileOrganizer": {"lang": "powershell-bridge", "test": ps_example("File Organizer", drive_organizer)},
    "PowerShell/PasswordGen": {"lang": "powershell-bridge", "test": ps_example(
        "Password Generator", drive_password,
        {"RADEX_CLIPBOARD_FILE": str(exlib.SCRATCH / "scripts" / "PasswordGen" / "_clipboard.txt")})},
    "Perl/TextStats": {"lang": "perl-bridge", "test": bridge_example("perl-bridge", "Text Statistics", drive_textstats)},
    "Perl/ExpenseTracker": {"lang": "perl-bridge", "test": bridge_example("perl-bridge", "Expense Tracker", drive_expenses)},
    "Perl/LogViewer": {"lang": "perl-bridge", "test": bridge_example("perl-bridge", "Log Viewer", drive_logviewer)},
    "Lua/Calculator": {"lang": "lua-bridge", "test": bridge_example("lua-bridge", "Calculator", drive_calculator)},
    "Lua/GuessGame": {"lang": "lua-bridge", "test": bridge_example("lua-bridge", "Guess the Number", drive_guess)},
    "Lua/Notes": {"lang": "lua-bridge", "test": bridge_example("lua-bridge", "Notes", drive_notes)},
}

os.environ.setdefault("RADEX_SECRET", "42")          # Lua/GuessGame: a known secret number for the test
