# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Example projects of group "ring": Ring (RingQt forms, console, web, RingRayLib game), Dart (GUI Bridge forms)
and Flutter (visual designer).  Run with:

    .venv\\Scripts\\python samples\\Tests\\Examples\\test_examples_scripting.py --group ring

RingQt programs are driven through UI Automation (comtypes, already in .venv): the RingQt designer code gives every
widget its control name as Qt objectName, which Qt reports as the UIA AutomationId.  The game runs with the
RAD IDE game hooks (RADGAME_FRAMES / RADGAME_KEYS / RADGAME_SCREENSHOT of radgame.ring).  Dart forms run in the
IDE's GUI Bridge host (exlib.BridgeDriver).  Flutter: designer model check, flutter analyze + flutter test (widget
test that adds a task and switches to Arabic RTL), Build > Publish = flutter build windows.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import time
from pathlib import Path

import exlib

GROUP = "ring"


# ============================================================================ helpers
def ring_exe() -> str:
    from radide.languages import get_plugin
    return get_plugin("ring-qt").find_interpreter("")


def start(folder: Path, lang: str, args=(), env: dict | None = None, capture=True) -> subprocess.Popen:
    """Start the project like F5 (the plugin's run_spec with the located interpreter)."""
    from radide.languages import get_plugin
    from radide.model import Project
    p = Project.load(folder)
    plugin = get_plugin(lang)
    spec = plugin.run_spec(folder, p.startup, plugin.find_interpreter(""))
    e = dict(spec.env or os.environ)
    for k in ("QT_QPA_PLATFORM", "QT_QPA_FONTDIR"):     # the test's own offscreen Qt must not hide the program
        e.pop(k, None)
    e.update(env or {})
    return subprocess.Popen([spec.program, *spec.args, *args], cwd=str(spec.cwd or folder), env=e,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                            stderr=subprocess.STDOUT if capture else subprocess.DEVNULL, text=True,
                            encoding="utf-8", errors="replace")


def ring_syntax(folder: Path, lang: str) -> tuple[bool, str]:
    """Build step for Ring: every hand-written .ring file compiles (ring <file> -norun, the Error List check)."""
    from radide.languages import get_plugin
    plugin = get_plugin(lang)
    if lang == "ring-qt":                  # F5 writes _radqt.ring / _radfx.ring first; the designer files load them
        plugin.run_spec(folder, "Form1", plugin.find_interpreter(""))
    errs = []
    files = [f for f in folder.glob("*.ring") if not f.name.startswith("_") and f.name != "radgame.ring"]
    for f in files:
        errs += plugin.syntax_check(folder, f.name)
    return not errs, f"{len(files)} files compiled" + (f"; errors: {errs[:3]}" if errs else "")


def launch_window(title: str, env: dict | None = None):
    """Published-program check: the exe shows its window (then it is closed)."""
    def check(exe: Path):
        e = dict(os.environ)
        for k in ("QT_QPA_PLATFORM", "QT_QPA_FONTDIR"):
            e.pop(k, None)
        e.update(env or {})
        proc = subprocess.Popen([str(exe)], cwd=str(exe.parent), env=e, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        try:
            w = exlib.wait_window(proc, title, 60)
            return bool(w), f"published exe shows {w[1]!r}" if w else "published exe: no window"
        finally:
            exlib.stop_tree(proc)
    return check


def launch_output(expect: str, env: dict | None = None):
    def check(exe: Path):
        e = dict(os.environ)
        e.update(env or {})
        r = subprocess.run([str(exe)], cwd=str(exe.parent), env=e, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=120)
        return expect in r.stdout, f"published exe printed {expect!r}: {expect in r.stdout}"
    return check


def launch_http(path: str, expect: str):
    def check(exe: Path):
        port = exlib.free_port()
        proc = subprocess.Popen([str(exe)], cwd=str(exe.parent), env=dict(os.environ, PORT=str(port)),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            up = exlib.wait_http(f"http://127.0.0.1:{port}/", 30)
            st, body = exlib.http_get(f"http://127.0.0.1:{port}{path}") if up else (0, "")
            return st == 200 and expect in body, f"published exe serves {path}: {st}"
        finally:
            exlib.stop_tree(proc)
    return check


def do_publish(folder: Path, res, opts, tag: str, launch=None) -> None:
    if not opts.get("publish"):
        res.step("publish", "skipped", "--no-publish")
        return
    r = exlib.publish(folder, exlib.SCRATCH / "logs" / f"{tag}_publish.log")
    if r.get("ok"):
        res["size"] = f"{r['size_mb']} MB"
        ran, rnote = (True, "")
        if launch is not None:
            ran, rnote = launch(Path(r["dist"]) / r["exe"])
        res.step("publish", bool(ran), f"kind={r['kind']} exe={r['exe']} ({r['exe_mb']} MB) folder={r['size_mb']} MB "
                                       f"python_inside={r['python_inside']}; {rnote}")
        res["publish_info"] = {k: r[k] for k in ("kind", "exe", "size_mb", "exe_mb", "python_inside")}
    else:
        res.step("publish", False, r.get("error", "") + " | " + " / ".join(r.get("log_tail", [])[-4:]))


class Uia:
    """Minimal UI Automation over comtypes: find by AutomationId (= Qt objectName) / Name, invoke, values, menus."""

    def __init__(self):
        import comtypes.client
        comtypes.client.GetModule("UIAutomationCore.dll")
        from comtypes.gen import UIAutomationClient as U
        self.U = U
        self.uia = comtypes.client.CreateObject("{ff48dba4-60ef-4201-aa87-54103eef594e}", interface=U.IUIAutomation)

    def win(self, hwnd):
        return self.uia.ElementFromHandle(hwnd)

    def _first(self, root, prop, value, pid=0):
        cond = self.uia.CreatePropertyCondition(prop, value)
        if pid:
            cond = self.uia.CreateAndCondition(cond, self.uia.CreatePropertyCondition(
                self.U.UIA_ProcessIdPropertyId, pid))
        try:
            el = root.FindFirst(self.U.TreeScope_Descendants, cond)
        except Exception:  # noqa: BLE001
            return None
        return el if el else None

    def _by_id(self, root, aid):
        """Qt's AutomationId is the dotted objectName path (Form2.grpLang.rdoArabic): match the last part."""
        el = self._first(root, self.U.UIA_AutomationIdPropertyId, aid)
        if el is not None:
            return el
        allc = root.FindAll(self.U.TreeScope_Descendants, self.uia.CreateTrueCondition())
        for i in range(allc.Length):
            c = allc.GetElement(i)
            if str(c.CurrentAutomationId or "").endswith("." + aid):
                return c
        return None

    def by_id(self, root, aid, timeout=5.0):
        return exlib.wait(lambda: self._by_id(root, aid), timeout, 0.1)

    def by_name(self, root, name, pid=0, timeout=5.0):
        return exlib.wait(lambda: self._first(root, self.U.UIA_NamePropertyId, name, pid), timeout, 0.1)

    def name(self, el) -> str:
        return str(el.CurrentName or "")

    def pattern(self, el, pid, iface):
        p = el.GetCurrentPattern(pid)
        return p.QueryInterface(iface) if p else None

    def invoke(self, el):
        p = self.pattern(el, self.U.UIA_InvokePatternId, self.U.IUIAutomationInvokePattern)
        if p is None:
            raise RuntimeError(f"no Invoke pattern on {self.name(el)!r}")
        p.Invoke()

    def set_value(self, el, text: str):
        self.pattern(el, self.U.UIA_ValuePatternId, self.U.IUIAutomationValuePattern).SetValue(text)

    def value(self, el) -> str:
        p = self.pattern(el, self.U.UIA_ValuePatternId, self.U.IUIAutomationValuePattern)
        return str(p.CurrentValue or "") if p else ""

    def select(self, el):
        """Radio button / list item: SelectionItem.Select, else Invoke, else Toggle."""
        U = self.U
        p = self.pattern(el, U.UIA_SelectionItemPatternId, U.IUIAutomationSelectionItemPattern)
        if p is not None:
            p.Select()
            return
        try:
            self.invoke(el)
        except RuntimeError:
            self.pattern(el, U.UIA_TogglePatternId, U.IUIAutomationTogglePattern).Toggle()

    def click(self, el, hwnd):
        """A left click in the middle of *el*, posted to the top-level window (Qt widgets have no own HWND)."""
        import ctypes
        from ctypes import wintypes as wt
        r = el.CurrentBoundingRectangle
        pt = wt.POINT((r.left + r.right) // 2, (r.top + r.bottom) // 2)
        ctypes.windll.user32.ScreenToClient(wt.HWND(hwnd), ctypes.byref(pt))
        lp = (pt.y << 16) | (pt.x & 0xFFFF)
        exlib.user32.PostMessageW(hwnd, 0x0201, 1, lp)       # WM_LBUTTONDOWN (MK_LBUTTON)
        exlib.user32.PostMessageW(hwnd, 0x0202, 0, lp)       # WM_LBUTTONUP

    def children(self, el) -> list:
        walker = self.uia.ControlViewWalker
        out, c = [], walker.GetFirstChildElement(el)
        while c:
            out.append(c)
            c = walker.GetNextSiblingElement(c)
        return out

    def menu(self, window, path: list[str]) -> bool:
        """Open the menu bar item path[0] and invoke the item path[-1] (Qt menus are popups of the process)."""
        U = self.U
        pid = int(window.CurrentProcessId)
        top = self.by_name(window, path[0])
        if top is None:
            return False
        p = self.pattern(top, U.UIA_ExpandCollapsePatternId, U.IUIAutomationExpandCollapsePattern)
        if p is not None:
            p.Expand()
        else:
            self.invoke(top)
        time.sleep(0.3)
        item = self.by_name(self.uia.GetRootElement(), path[-1], pid=pid)
        if item is None:
            return False
        self.invoke(item)
        return True


def text_of(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n") if path.exists() else ""


# ============================================================================ Ring - RingQt forms
def t_ring_notepad(src: Path, res, opts):
    ok, note = exlib.designer_check(src)
    res.step("open", ok, note)
    d = exlib.temp_copy(src, GROUP)
    res.step("build", *ring_syntax(d, "ring-qt"))
    notes = d / "notes.txt"
    notes.write_text("hello ring\nسلام عليكم", encoding="utf-8")
    proc = start(d, "ring-qt", [str(notes)])
    try:
        w = exlib.wait_window(proc, "notes.txt", 40)
        if not w:
            res.step("run", False, "window 'Ring Notepad - notes.txt' did not appear: " + (proc.stdout.read()
                                                                                         if proc.poll() is not None
                                                                                         else ""))
            return
        u = Uia()
        win = u.win(w[0])
        status = u.by_id(win, "lblStatus")
        s1 = u.name(status)
        good = s1 == "Lines: 2   Words: 4   Chars: 21"
        u.invoke(u.by_name(win, "ABC"))                       # ToolStrip button = Edit > Upper Case
        dirty = exlib.wait(lambda: "*notes.txt" in exlib.window_title(w[0]), 5)
        u.invoke(u.by_name(win, "Save"))                      # = File > Save
        saved = exlib.wait(lambda: text_of(notes) == "HELLO RING\nسلام عليكم", 5)
        clean = exlib.wait(lambda: exlib.window_title(w[0]) == "Ring Notepad - notes.txt", 5)
        u.invoke(u.by_name(win, "Time"))                      # = Edit > Insert Date/Time
        grew = exlib.wait(lambda: u.name(status).startswith("Lines:") and u.name(status) != s1, 5)
        res.step("run", bool(good and dirty and saved and clean and grew),
                 f"window {w[1]!r}; status {s1!r}; toolbar ABC (Upper Case) dirty={bool(dirty)}; Save wrote "
                 f"{text_of(notes)!r}; Time -> {u.name(status)!r} (UI Automation)")
    finally:
        exlib.stop_tree(proc)
    do_publish(d, res, opts, "RingNotepad", launch_window("Ring Notepad"))


def t_ring_contacts(src: Path, res, opts):
    ok, note = exlib.designer_check(src)
    res.step("open", ok, note)
    d = exlib.temp_copy(src, GROUP)
    res.step("build", *ring_syntax(d, "ring-qt"))
    (d / "settings.ini").write_text("lang=en\nconfirm=0\n", encoding="utf-8")   # no Yes/No box for the delete
    db = d / "contacts.db"

    def count():
        c = sqlite3.connect(db)
        try:
            return c.execute("select count(*) from contacts").fetchone()[0]
        finally:
            c.close()
    proc = start(d, "ring-qt")
    try:
        w = exlib.wait_window(proc, "Contacts", 40)
        if not w:
            res.step("run", False, "the Contacts window did not appear")
            return
        u = Uia()
        win = u.win(w[0])
        lst = u.by_id(win, "lstContacts")
        seeded = len(u.children(lst))
        u.set_value(u.by_id(win, "txtName"), "Test User")
        u.set_value(u.by_id(win, "txtPhone"), "+20 111 222 333")
        u.set_value(u.by_id(win, "txtEmail"), "test@example.com")
        u.invoke(u.by_id(win, "cmdAdd"))
        added = exlib.wait(lambda: u.name(u.by_id(win, "lblCount")) == "4 contacts", 5) and count() == 4
        u.set_value(u.by_id(win, "txtSearch"), "Test")
        found = exlib.wait(lambda: [u.name(x) for x in u.children(lst)] == ["Test User  -  +20 111 222 333"], 5)
        u.click(u.children(lst)[0], w[0])                    # click the found contact
        picked = exlib.wait(lambda: u.value(u.by_id(win, "txtEmail")) == "test@example.com", 5)
        u.invoke(u.by_id(win, "cmdDelete"))
        deleted = exlib.wait(lambda: count() == 3, 5)
        u.set_value(u.by_id(win, "txtSearch"), "")
        # modal Settings form (Form2): Arabic, OK -> settings.ini + Arabic labels on Form1
        u.invoke(u.by_id(win, "cmdSettings"))
        w2 = exlib.wait(lambda: next(((h, t) for h, t in exlib.windows_of(exlib.process_tree(proc.pid))
                                      if "Settings" in t), None), 10)
        arabic = False
        if w2:
            win2 = u.win(w2[0])
            u.select(u.by_id(win2, "rdoArabic"))
            u.invoke(u.by_id(win2, "cmdOK"))
            arabic = exlib.wait(lambda: "lang=ar" in text_of(d / "settings.ini")
                                and u.name(u.by_id(win, "lblName")) == "الاسم:", 5)
        res.step("run", bool(seeded == 3 and added and found and picked and deleted and w2 and arabic),
                 f"seeded {seeded} rows; Add -> db {4 if added else '?'} rows; search 'Test' -> {bool(found)}; "
                 f"select fills fields {bool(picked)}; Delete -> {bool(deleted)}; Settings form {w2 and w2[1]!r}; "
                 f"Arabic UI + settings.ini {bool(arabic)} (UI Automation + sqlite3)")
    finally:
        exlib.stop_tree(proc)
    for f in ("settings.ini", "contacts.db"):         # the test's data must not be shipped
        exlib.wait(lambda: (d / f).unlink(missing_ok=True) or True, 10, 0.5)
    do_publish(d, res, opts, "RingContacts", launch_window("Contacts"))


# ============================================================================ Ring - console / web / game
def t_ring_datatool(src: Path, res, opts):
    from radide.model import Project
    p = Project.load(src)
    res.step("open", p.language == "ring-app" and (src / "main.ring").exists(), f"{p.language}, startup {p.startup}")
    d = exlib.temp_copy(src, GROUP)
    res.step("build", *ring_syntax(d, "ring-app"))
    proc = start(d, "ring-app")
    out, _ = proc.communicate(timeout=60)
    want = ["Count:            12", "Mean:             1384.58", "Median:           1375",
            "Std. deviation:   284.34", "1. Dec  1890", "Matrix A x B = [16 20; 13 25]"]
    missing = [x for x in want if x not in out]
    rep = text_of(d / "report.txt")
    res.step("run", not missing and "Dec  |####" in rep, "console output checked" +
             (f"; missing {missing}" if missing else "") + f"; report.txt {len(rep)} bytes")
    do_publish(d, res, opts, "RingDataTool", launch_output("Median:           1375"))


def t_ring_guestbook(src: Path, res, opts):
    from radide.model import Project
    p = Project.load(src)
    res.step("open", p.language == "ring-app" and (src / "templates" / "index.html").exists(), p.language)
    d = exlib.temp_copy(src, GROUP)
    res.step("build", *ring_syntax(d, "ring-app"))
    port = exlib.free_port()
    proc = start(d, "ring-app", env={"PORT": str(port)})
    base = f"http://127.0.0.1:{port}"
    try:
        if not exlib.wait_http(base + "/", 30):
            res.step("run", False, "the server did not answer")
            return
        st, home = exlib.http_get(base + "/")
        st2, after = exlib.http_post(base + "/sign", {"name": "Mona منى", "message": "Hello <b>Ring</b>"})
        st3, api = exlib.http_get(base + "/api/entries")
        entries = json.loads(api)
        st4, bad = exlib.http_post(base + "/sign", {"name": "", "message": ""})
        good = (st == 200 and "Ring Guestbook" in home and st2 == 200 and "Mona منى" in after
                and "&lt;b&gt;Ring&lt;/b&gt;" in after and st3 == 200 and len(entries) == 1
                and entries[0]["name"] == "Mona منى" and "Please write your name" in bad)
        res.step("run", good, f"GET / {st}; POST /sign -> 303 -> {st2} (escaped HTML, Arabic kept); "
                              f"/api/entries {entries}; empty form -> validation message; db guestbook.db")
    finally:
        exlib.stop_tree(proc)
    (d / "guestbook.db").unlink(missing_ok=True)
    do_publish(d, res, opts, "RingGuestbook", launch_http("/api/entries", "["))


def t_ring_pong(src: Path, res, opts):
    from radide.games import codegen
    from radide.games.model import validate
    from radide.model import Project
    p = Project.load(src)
    scene = codegen.scene_dict(src / "Court.scene")
    issues = validate(scene)
    objs = [o["name"] for o in codegen.scene_objects(scene)]
    res.step("open", not issues and len(objs) == 6 and p.language == "ring-game",
             f"scene Court: {len(objs)} objects {objs}" + (f" issues {issues}" if issues else ""))
    d = exlib.temp_copy(src, GROUP)
    res.step("build", *ring_syntax(d, "ring-game"))
    env = {"RADGAME_FRAMES": "900", "RADGAME_HIDDEN": "1", "RADGAME_FIXED_DT": "1", "RADGAME_KEYS": "down:1-30",
           "RADGAME_SCREENSHOT": "shot.png"}
    proc = start(d, "ring-game", env=env)
    out, _ = proc.communicate(timeout=120)
    shot = d / "shot.png"
    hits = out.count("hit ")
    scores = re.findall(r"score (\d+:\d+)", out)
    ok_frames = "radgame: 900 frames" in out and "radgame error" not in out
    # a visible run: the game's own window appears (then it quits by itself after 150 frames)
    proc2 = start(d, "ring-game", env={"RADGAME_FRAMES": "150"})
    w = exlib.wait_window(proc2, "Ring Pong", 30)
    try:
        proc2.wait(30)
    except subprocess.TimeoutExpired:
        exlib.stop_tree(proc2)
    res.step("run", bool(ok_frames and hits >= 2 and scores and shot.exists() and shot.stat().st_size > 2000 and w),
             f"900 frames (RADGAME hooks): {hits} paddle hits, scores {scores}, screenshot "
             f"{shot.stat().st_size if shot.exists() else 0} bytes; window {w and w[1]!r}")
    do_publish(d, res, opts, "RingPong", launch_window("Ring Pong", {"RADGAME_FRAMES": "600"}))


# ============================================================================ Dart (GUI Bridge)
def dart_analyze(d: Path) -> tuple[bool, str]:
    from radide.languages import get_plugin
    dart = get_plugin("dart-bridge").tool()
    r = subprocess.run([dart, "analyze", "--no-fatal-warnings"], cwd=str(d), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300)
    tail = (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]
    return r.returncode == 0, "dart analyze: " + tail[0]


def dart_path_env() -> dict:
    """A published GUI Bridge program runs `dart` from PATH (Build > Publish notes say so): put the SDK on it."""
    from radide.languages import get_plugin
    return {"PATH": str(Path(get_plugin("dart-bridge").tool()).parent) + os.pathsep + os.environ.get("PATH", "")}


def t_dart_tip(src: Path, res, opts):
    ok, note = exlib.designer_check(src)
    res.step("open", ok, note)
    d = exlib.temp_copy(src, GROUP)
    b = exlib.BridgeDriver(d)
    try:
        w = b.window("Tip Calculator")
        first = b.get("lblResult", "Caption")
        b.set("txtBill", "200")
        b.click("cmdCalc")
        r1 = b.get("lblResult", "Caption")
        b.set("trkTip", 20, "Value")
        b.event("trkTip", "ValueChanged")
        b.set("nudPeople", 3, "Value")
        b.set("chkRound", 1, "Value")
        b.click("cmdCalc")
        r2 = b.get("lblResult", "Caption")
        hist = b.list_items("lstHistory")
        b.set("txtBill", "abc")
        b.click("cmdCalc")
        b.click("mnuHelpAbout")
        b.pump(300)
        about = b.window("About Tip Calculator")
        good = (w and "Total E£287.50" in first and "Tip E£30.00" in r1 and "Total E£230.00" in r1
                and "Each E£80.00" in r2 and b.get("lblTipValue", "Caption") == "20 %" and len(hist) == 2
                and any("must be a number" in m for m in b.msgs) and about)
        res.step("run", bool(good), f"window {w and w[1]!r}; 200 @15% /2 -> {r1!r}; 20% /3 rounded -> {r2!r}; "
                                    f"history {len(hist)}; bad input -> MsgBox; Help>About opens Form2 "
                                    f"{bool(about)} (bridge host)")
    finally:
        b.close()
    res.step("build", *dart_analyze(d))
    do_publish(d, res, opts, "TipCalculator", launch_window("Tip Calculator", dart_path_env()))


def t_dart_words(src: Path, res, opts):
    ok, note = exlib.designer_check(src)
    res.step("open", ok, note)
    d = exlib.temp_copy(src, GROUP)
    words = [x.strip() for x in text_of(d / "words.txt").splitlines() if x.strip() and not x.startswith("#")]
    b = exlib.BridgeDriver(d)
    try:
        w = b.window("Word Scramble")
        scrambled = b.get("lblWord", "Caption")
        answer = next((x for x in words if sorted(x) == sorted(scrambled.lower())), "")
        b.set("txtGuess", "zzz")
        b.click("cmdCheck")
        wrong = b.get("lblMessage", "Caption")
        b.set("txtGuess", answer)
        b.click("cmdCheck")
        score = b.get("lblScore", "Caption")
        b.click("cmdHint")
        hint = b.get("lblMessage", "Caption")
        t0 = int(b.get("prgTime", "Value"))
        b.event("Timer1", "Tick")
        t1 = int(b.get("prgTime", "Value"))
        good = (w and answer and "try again" in wrong and score == "Score: 10" and hint.startswith("Starts with")
                and t1 == t0 - 1 and b.get("lblTime", "Caption") == f"Time: {t1}")
        res.step("run", bool(good), f"window {w and w[1]!r}; {scrambled} -> {answer} -> {score}; hint {hint!r}; "
                                    f"Timer1.Tick {t0}->{t1} (bridge host)")
    finally:
        b.close()
    res.step("build", *dart_analyze(d))
    do_publish(d, res, opts, "WordScramble", launch_window("Word Scramble", dart_path_env()))


# ============================================================================ Flutter (visual designer)
def flutter(d: Path, *args, timeout=900) -> subprocess.CompletedProcess:
    from radide.languages.flutter import flutter_exe
    return subprocess.run([flutter_exe(), *args], cwd=str(d), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, shell=True)


def t_flutter_todo(src: Path, res, opts):
    from radide.flutterdesign import codegen
    from radide.flutterdesign import model as M
    notes, ok = [], True
    for f in sorted((src / "screens").glob("*" + M.SCREEN_EXT)):
        raw = json.loads(f.read_text(encoding="utf-8"))
        scr = M.Screen.load(f)
        n_raw = len(list(M.walk_node(raw["tree"])))
        n = len(list(scr.walk()))
        gen = codegen.generate_screen(scr, text_of(src / "lib" / "screens" / f"{M.snake(scr.name)}_events.dart"))
        issues = scr.validate()
        named = sorted(scr.names())
        fields = [n["name"] for n, *_ in scr.walk() if n.get("name") and getattr(
            M.widget_spec(n.get("type", ""), n.get("ctor")), "needs_name", False)]
        lost = [x for x in fields if x not in gen.designer_code]
        ok &= n == n_raw and not issues and not lost
        notes.append(f"{scr.name}: {n}/{n_raw} widgets, names {named}" + (f" issues {issues}" if issues else "")
                     + (f" lost {lost}" if lost else ""))
    res.step("open", ok, "; ".join(notes))
    d = exlib.temp_copy(src, GROUP)
    from radide.languages import get_plugin
    from radide.model import Project
    get_plugin("flutter").write_project_files(Project.load(d))      # what Save / F5 regenerates
    codegen.write_all(d)
    r = flutter(d, "pub", "get")
    a = flutter(d, "analyze")
    tail = (a.stdout + a.stderr).strip().splitlines()[-1:] or [""]
    res.step("build", r.returncode == 0 and a.returncode == 0, "flutter pub get + analyze: " + tail[0])
    t = flutter(d, "test")
    tt = (t.stdout + t.stderr).strip().splitlines()[-1:] or [""]
    res.step("run", t.returncode == 0 and "All tests passed" in t.stdout,
             "flutter test (add task, tick it, Settings > Arabic -> RTL + Arabic labels): " + tt[0])
    do_publish(d, res, opts, "TodoDesigner", launch_window(""))


EXAMPLES = {
    "Ring/RingNotepad": {"lang": "ring-qt", "test": t_ring_notepad},
    "Ring/RingContacts": {"lang": "ring-qt", "test": t_ring_contacts},
    "Ring/RingDataTool": {"lang": "ring-app", "test": t_ring_datatool},
    "Ring/RingGuestbook": {"lang": "ring-app", "test": t_ring_guestbook},
    "Ring/RingPong": {"lang": "ring-game", "test": t_ring_pong},
    "Dart/TipCalculator": {"lang": "dart-bridge", "test": t_dart_tip},
    "Dart/WordScramble": {"lang": "dart-bridge", "test": t_dart_words},
    "Flutter/TodoDesigner": {"lang": "flutter", "test": t_flutter_todo},
}
