"""J3 (existing projects), J5 (debugger), J7 (language + theme), J8 (designer under load)."""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from radauto import Report, Skip, check
import e2e_common as C

REPO = Path(__file__).resolve().parent.parent.parent.parent


# ================================================================================================ J3
def j3_existing_projects(env: C.Env, rep: Report):
    C.portable_copy(env)
    root = env.scratch / "projects" / "J3"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    samples = {"BankManager (VB6)": REPO / "samples" / "VB6" / "Business" / "BankManager",
               "Contacts (Python Tk)": REPO / "samples" / "Examples" / "Python" / "Contacts",
               "C example": next((p for p in (REPO / "samples" / "Examples" / "C").iterdir() if p.is_dir()), None)}
    copies = {}
    for k, src in samples.items():
        if src is not None and src.is_dir():
            dst = root / src.name
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("Publish", "bin", "obj", "__pycache__", "build"))
            copies[k] = dst
    ide = C.launch(env, "J3")
    rep.ide = ide
    st: dict = {}

    def project_file(folder: Path) -> Path:
        for pat in ("*.radsln", "project.radproj", "*.vbp"):
            hits = sorted(folder.glob(pat))
            if hits:
                return hits[0]
        return folder

    for key, folder in copies.items():
        def open_it(folder=folder, key=key):
            target = project_file(folder)
            ide.call("file_dialog", answers=[str(target)])
            ide.call("trigger", path="File/Open Project...")
            def opened():
                p = ide.call("project")
                if not p:
                    return None
                inside = Path(p["folder"]).resolve().is_relative_to(folder.resolve())
                return p if inside or p["name"].lower() == folder.name.lower() else None
            info = ide.wait_for(opened, 60, desc=f"{key} opened")
            st[key] = info
            tree = ide.call("solution_tree")
            check(tree and len(tree) > 2, f"solution tree {tree}")
            return f"{info['name']} ({info['language']}): {len(info['forms'])} forms, {len(info['modules'])} modules"
        if not rep.step(f"open {key} (File > Open Project)", open_it, shot=True):
            continue

        def edit_save(key=key):
            info = st[key]
            if not info["forms"]:
                raise Skip("no forms")
            form = info["forms"][0]
            ide.call("open_form", name=form)
            ctrls = ide.call("designer_controls")["controls"]
            check(ctrls, "no controls on the form")
            c = next((x for x in ctrls if x["type"] in ("Button", "CommandButton", "Label")), ctrls[0])
            ide.call("designer_drag", name=c["name"], dx=16, dy=8)
            moved = ide.call("designer_controls")["controls"]
            m = next(x for x in moved if x["name"] == c["name"])
            check(m["props"].get("Left") != c["props"].get("Left") or m["props"].get("Top") != c["props"].get("Top"),
                  f"drag did not move {c['name']}: {c['props']} -> {m['props']}")
            check(ide.call("save_all"), "save failed")
            st[key + ":moved"] = (form, c["name"], m["props"].get("Left"), m["props"].get("Top"))
            return f"{form}.{c['name']} moved to {m['props'].get('Left')},{m['props'].get('Top')}"
        rep.step(f"{key}: move a control (mouse drag) + save", edit_save)

        def events(key=key):
            info = st[key]
            if not info["forms"]:
                raise Skip("no forms")
            btn = None
            for form in info["forms"]:                  # the first form with a button (a splash has none)
                ide.call("open_form", name=form)
                ctrls = ide.call("designer_controls")["controls"]
                btn = next((x for x in ctrls if x["type"] in ("Button", "CommandButton")), None)
                if btn is not None:
                    break
            if btn is None:
                raise Skip("no button on any form")
            rows = ide.call("events_tab", name=btn["name"])
            rep.shot(f"{key} events tab", sel="@properties")
            check(rows and any(r["event"] for r in rows), f"Events tab empty: {rows}")
            handled = [r for r in rows if r["handler"]]
            return f"{len(rows)} events, {len(handled)} with handlers: {[r['event'] for r in handled][:4]}"
        rep.step(f"{key}: Events tab lists the events", events)

    def reopen():
        ide.quit()
        ide2 = C.launch(env, "J3b")
        rep.ide = ide2
        st["ide2"] = ide2
        res = []
        for key, val in st.items():
            if not key.endswith(":moved"):
                continue
            k = key[:-6]
            ide2.call("open_project", path=str(project_file(copies[k])))
            form, name, left, top = val
            ide2.call("open_form", name=form)
            c = next(x for x in ide2.call("designer_controls")["controls"] if x["name"] == name)
            check(c["props"].get("Left") == left and c["props"].get("Top") == top,
                  f"{k}: after reopen {c['props']} != {left},{top}")
            res.append(k)
        recent = ide2.py("result = win.recent_projects()")
        check(recent, "recent projects list empty after reopen")
        return f"kept: {res}; recent: {len(recent)}"
    rep.step("restart the IDE, reopen: the edits are still there; Recent Projects filled", reopen)
    if st.get("ide2"):
        rep.step("no internal errors", lambda: C.no_internal_errors(st["ide2"]))
        st["ide2"].quit()


# ================================================================================================ J5
def j5_debugger(env: C.Env, rep: Report):
    C.portable_copy(env)
    ide = C.launch(env, "J5")
    rep.ide = ide
    root = env.scratch / "projects" / "J5"
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    cases = [("vb-basic", "VB6", 'Dim msg As String\nmsg = "Hi " & txtName.Text\nlblOut.Caption = msg'),
             ("python-tk", "PythonTk", 'msg = "Hi " + self.txtName.get()\nself.lblOut.config(text=msg)')]
    for lang, title, code in cases:
        P = f"{title}: "
        st: dict = {}

        def make(lang=lang, title=title, code=code):
            ide.call("new_project", language=lang, name=f"Dbg{title}", location=str(root))
            ide.call("designer_place", type="Button", x=24, y=24, name="btnGo")
            ide.call("designer_place", type="TextBox", x=24, y=72, name="txtName")
            ide.call("designer_place", type="Label", x=24, y=120, w=200, h=24, name="lblOut")
            ide.call("set_property", name="", prop="Text", value=f"DBG {title}")
            ide.call("designer_dclick", name="btnGo")
            text = ide.call("editor_text")["text"].splitlines()
            hl = next(i for i, ln in enumerate(text) if "btnGo" in ln and "lick" in ln)
            indent = re.match(r"\s*", text[hl]).group(0) + "    "
            body = [indent + x for x in code.splitlines()]
            nxt = hl + 1
            if nxt < len(text) and text[nxt].strip() in ("", "pass"):
                text[nxt:nxt + 1] = body
            else:
                text[nxt:nxt] = body
            ide.call("editor_set_text", text="\n".join(text) + "\n")
            ide.call("save_all")
            st["file"] = Path(ide.call("tabs")["current_title"].rstrip("*")).name
            st["bp_line"] = ide.call("editor_find", needle=code.splitlines()[-1].strip())[0]   # the label line
            return f"{st['file']} breakpoint line {st['bp_line']}"
        if not rep.step(P + "project with a handler", make):
            continue

        def bp():
            r = ide.call("breakpoint", file=st["file"], line=st["bp_line"], on=True)
            check(st["bp_line"] in (r["breakpoints"] or []), f"breakpoint not set: {r}")
            return r["breakpoints"]
        rep.step(P + "set breakpoint (F9 equivalent)", bp)

        def run_click(title=title):
            ide.call("output", clear=True)
            ide.call("key", keys="F5", sel="@tabs", async_=True)
            w = C.wait_window(ide, f"DBG {title}", timeout=180)
            st["w"] = w
            C.drive_hello(ide, rep, w, "Bob", "", breakpoint=True)
            d = ide.wait_for(lambda: (lambda s: s if s.get("paused") else None)(ide.call("debug_state")), 60,
                             desc="paused at the breakpoint")
            rep.shot(P + "paused")
            st["dbg"] = d
            return d.get("status")
        if not rep.step(P + "F5, click -> stops at the breakpoint", run_click):
            try:
                ide.call("trigger", path="Debug/Stop Debugging")
            except Exception:  # noqa: BLE001
                pass
            continue

        def locals_():
            loc = st["dbg"].get("locals") or []
            joined = " ".join(loc)
            check("msg" in joined.lower() and "Hi Bob" in joined, f"Locals: {loc}")
            return loc[:6]
        rep.step(P + "Locals show msg = 'Hi Bob'", locals_)
        rep.step(P + "Call Stack shows the handler",
                 lambda: check(any("btnGo" in x for x in (st["dbg"].get("callstack") or [])),
                               f"call stack {st['dbg'].get('callstack')}") and st["dbg"]["callstack"][:3])

        def cont():
            ide.call("key", keys="F5", sel="@tabs", async_=True)
            ide.wait_for(lambda: not ide.call("run_state")["paused"], 30, desc="resumed")
            t = C.wait_title(ide, st["w"]["hwnd"], f"DBG {title}", 5)
            ide.call("trigger", path="Debug/Stop Debugging")
            ide.wait_for(lambda: not ide.call("run_state")["running"], 30, desc="stopped")
            return t
        rep.step(P + "continue (F5) and stop", cont)
    rep.step("no internal errors", lambda: C.no_internal_errors(ide))
    ide.quit()


# ================================================================================================ J7
ENGLISH_RX = re.compile(r"^[A-Za-z][A-Za-z .&/'-]{3,}$")
ALLOWED_EN = {"RAD IDE", "VS", "Code", "Agent", "Git", "Python", "BASIC", "Ring", "AI", "Pointer", "CSV", "SQL"}


SHOWN = ("from radide import i18n\n"
         "def shown(o, attr='text'):\n"
         "    try:\n"
         "        return i18n.shown(o, attr).replace('&', '')\n"
         "    except Exception:\n"
         "        return (o.text() if attr == 'text' else o.windowTitle()).replace('&', '')\n")


def shown_menus(ide) -> list[str]:
    """The menu bar texts as they are on the screen (QAction.text() keeps returning English by design)."""
    return ide.py(SHOWN + "result = [shown(m) for m in win.menuBar().actions() if m.isVisible()]")


def j7_language_theme(env: C.Env, rep: Report):
    C.portable_copy(env)
    ide = C.launch(env, "J7")
    rep.ide = ide
    root = env.scratch / "projects" / "J7"
    root.mkdir(parents=True, exist_ok=True)
    ide.call("new_project", language="vb-basic", name=f"Lang{int(time.time())}", location=str(root))
    rep.shot("english")

    def to_ar():
        ide.call("trigger", name="ui_language_ar")
        time.sleep(2)
        for d in ide.call("dialogs"):           # "the display language was changed" note
            ide.call("press", button=d["buttons"][0] if d["buttons"] else "OK")
        time.sleep(1)
        menus = shown_menus(ide)
        rtl = ide.py("from PyQt6.QtCore import Qt; result = app.layoutDirection() == Qt.LayoutDirection.RightToLeft")
        rep.shot("arabic")
        check(rtl, "layout is not right-to-left")
        check(any(re.search(r"[؀-ۿ]", m) for m in menus), f"menus not Arabic: {menus}")
        return menus[:8]
    rep.step("Tools > Language > Arabic: RTL + Arabic menus", to_ar)

    def leftovers():
        top = ide.py(SHOWN + "result = [shown(a) for m in win.menuBar().actions() if m.menu() "
                     "for a in [m] + [x for x in m.menu().actions() if not x.isSeparator()]]")
        en = sorted({t for t in top if ENGLISH_RX.match(t) and t not in ALLOWED_EN})
        en_docks = ide.py(SHOWN + "from PyQt6.QtWidgets import QDockWidget\n"
                          "result = [shown(d, 'windowTitle') for d in win.findChildren(QDockWidget) if d.isVisible()]")
        en_docks = [t for t in en_docks if ENGLISH_RX.match(t)]
        check(len(en) <= max(3, len(top) // 20) and not en_docks,
              f"{len(en)}/{len(top)} English menu items: {en[:30]}; docks: {en_docks}")
        return f"{len(top)} items, English leftovers: {en[:10]}"
    rep.step("no leftover English strings in menus / tool windows", leftovers)

    def designer_ar():
        ide.call("open_form", name="Form1")
        ide.call("designer_place", type="Button", x=40, y=40)
        rep.shot("arabic designer")
        return ide.call("designer_controls")["controls"][-1]["name"]
    rep.step("designer works in Arabic", designer_ar)

    def to_en():
        ide.call("trigger", name="ui_language_en")
        time.sleep(2)
        for d in ide.call("dialogs"):
            ide.call("press", button=d["buttons"][0] if d["buttons"] else "OK")
        menus = shown_menus(ide)
        rtl = ide.py("from PyQt6.QtCore import Qt; result = app.layoutDirection() == Qt.LayoutDirection.RightToLeft")
        check(not rtl and "File" in menus, f"not back to English: rtl={rtl} {menus[:6]}")
        rep.shot("english again")
        return menus[:6]
    rep.step("back to English: LTR + English menus", to_en)

    def dark():
        ide.call("trigger", path="Tools/Options...")
        ide.wait_dialog("Options", timeout=20)
        combos = ide.call("widgets", sel={"cls": "QComboBox", "title": "Options"}, full=True, limit=80)
        cb = next((c for c in combos if "Dark" in (c.get("items") or [])), None)
        check(cb is not None, "no colour theme combo in Options")
        ide.call("set_value", sel={"cls": "QComboBox", "title": "Options", "index": combos.index(cb)}, value="Dark")
        ide.call("press", button="OK", dialog="Options")
        time.sleep(2)
        bg = ide.py("result = win.palette().window().color().lightness()")
        rep.shot("dark theme")
        check(bg < 100, f"window colour lightness {bg} (not dark)")
        return f"lightness {bg}"
    rep.step("Tools > Options > Color theme Dark", dark)

    def dark_ar():
        ide.call("trigger", name="ui_language_ar")
        time.sleep(2)
        for d in ide.call("dialogs"):
            ide.call("press", button=d["buttons"][0] if d["buttons"] else "OK")
        rep.shot("dark arabic")
        ide.call("trigger", name="ui_language_en")
        time.sleep(1)
        for d in ide.call("dialogs"):
            ide.call("press", button=d["buttons"][0] if d["buttons"] else "OK")
        return "screenshots"
    rep.step("dark + Arabic screenshot", dark_ar)
    rep.step("no internal errors", lambda: C.no_internal_errors(ide))
    # the journeys share the portable copy's settings: back to the defaults for the next one
    ide.try_call("exec", code="from radide.features.workbench import set_theme\nset_theme(win, 'Light')")
    ide.quit()


# ================================================================================================ J8
def j8_designer_load(env: C.Env, rep: Report):
    C.portable_copy(env)
    ide = C.launch(env, "J8")
    rep.ide = ide
    root = env.scratch / "projects" / "J8"
    root.mkdir(parents=True, exist_ok=True)
    ide.call("new_project", language="vb-basic", name=f"Big{int(time.time())}", location=str(root))
    ide.call("set_property", name="", prop="Width", value="1600")
    ide.call("set_property", name="", prop="Height", value="1200")
    st = {}

    def place20():
        t = time.monotonic()
        kinds = ["Button", "TextBox", "Label", "CheckBox", "ComboBox"]
        for i in range(20):
            ide.call("designer_place", type=kinds[i % 5], x=16 + (i % 10) * 120, y=16 + (i // 10) * 40)
        dt = time.monotonic() - t
        return f"20 controls placed with the Toolbox in {dt:.1f}s ({dt / 20 * 1000:.0f} ms each)"
    rep.step("place 20 controls through the Toolbox", place20)

    def grow():
        t = time.monotonic()
        n = len(ide.call("designer_controls")["controls"])
        while n < 400:
            ide.call("key", keys="Ctrl+A", sel={"cls": "Overlay"})
            ide.call("key", keys="Ctrl+C", sel={"cls": "Overlay"})
            ide.call("key", keys="Ctrl+V", sel={"cls": "Overlay"})
            n2 = len(ide.call("designer_controls")["controls"])
            check(n2 > n, f"paste did not add controls ({n} -> {n2})")
            n = n2
        st["n"] = n
        dt = time.monotonic() - t
        rep.shot("big form")
        return f"{n} controls by copy / paste in {dt:.1f}s"
    rep.step("grow the form to 400+ controls (Ctrl+A, Ctrl+C, Ctrl+V)", grow)

    def responsive():
        times = []
        for _ in range(5):
            t = time.monotonic()
            ide.call("designer_place", type="Button", x=1400, y=1100)
            times.append(time.monotonic() - t)
        sel_t = time.monotonic()
        ctrls = ide.call("designer_controls")["controls"]
        ide.call("designer_select", name=ctrls[len(ctrls) // 2]["name"])
        sel_t = time.monotonic() - sel_t
        drag_t = time.monotonic()
        ide.call("designer_drag", name=ctrls[3]["name"], dx=24, dy=24)
        drag_t = time.monotonic() - drag_t
        worst = max(times)
        check(worst < 3.0 and sel_t < 3.0 and drag_t < 3.0,
              f"slow: place {worst:.2f}s select {sel_t:.2f}s drag {drag_t:.2f}s")
        return f"place max {worst * 1000:.0f} ms, select {sel_t * 1000:.0f} ms, drag {drag_t * 1000:.0f} ms"
    rep.step("responsive with 400+ controls (place / select / drag < 3 s incl. round trip)", responsive)

    def undo_redo():
        n0 = len(ide.call("designer_controls")["controls"])
        t = time.monotonic()
        for _ in range(5):
            ide.call("trigger", path="Edit/Undo", async_=False)
        n1 = len(ide.call("designer_controls")["controls"])
        for _ in range(5):
            ide.call("trigger", path="Edit/Redo", async_=False)
        n2 = len(ide.call("designer_controls")["controls"])
        dt = time.monotonic() - t
        check(n1 < n0 and n2 == n0, f"undo/redo counts {n0} -> {n1} -> {n2}")
        return f"{n0} -> {n1} -> {n2} in {dt:.1f}s"
    rep.step("undo x5 / redo x5", undo_redo)

    def save_big():
        t = time.monotonic()
        check(ide.call("save_all"), "save failed")
        return f"saved in {time.monotonic() - t:.1f}s"
    rep.step("save the big form", save_big)

    def autohide():
        ide.py("win.dock_toolbox.show(); win.dock_toolbox.raise_(); win.dock_toolbox.widget().setFocus()")
        ide.call("trigger", path="Window/Auto Hide All", async_=False)
        time.sleep(1)
        hidden = ide.py("ah = getattr(win, 'autohide', None)\n"
                        "result = [d.windowTitle() for d in win.findChildren(__import__('PyQt6.QtWidgets', fromlist=['QDockWidget']).QDockWidget) if ah is not None and ah.is_auto_hidden(d)]")
        rep.shot("auto hide all")
        check(hidden, "no tool window auto-hidden")
        ide.py("win.autohide.restore_all()")
        time.sleep(0.5)
        back = ide.py("ah = win.autohide\n"
                      "result = [d.windowTitle() for d in win.findChildren(__import__('PyQt6.QtWidgets', fromlist=['QDockWidget']).QDockWidget) if ah.is_auto_hidden(d)]")
        check(not back, f"still auto-hidden after restore: {back}")
        return f"{len(hidden)} auto-hidden, all restored"
    rep.step("Window > Auto Hide All / restore", autohide)

    def view_menu():
        acts = [a for a in ide.call("actions", filter="View/") if not a["submenu"] and a["enabled"]
                and a["path"].count("/") == 1]
        opened, errs = [], []
        before = len(ide.output())
        for a in acts:
            try:
                ide.call("trigger", path=a["path"])
                time.sleep(0.4)
                for d in ide.call("dialogs"):
                    ide.call("close_dialog")
                    time.sleep(0.2)
                opened.append(a["path"].split("/")[1])
            except Exception as e:  # noqa: BLE001
                errs.append(f"{a['path']}: {e}"[:200])
        rep.shot("after View menu")
        new_errs = C.output_errors(ide.output()[before:])
        check(not errs and not new_errs, f"errors: {errs[:5]} {new_errs[:5]}")
        return f"{len(opened)} View items opened"
    rep.step("every View menu item opens without an error", view_menu)
    rep.step("no internal errors", lambda: C.no_internal_errors(ide))
    ide.quit()


# ================================================================================================ J10
def j10_two_windows(env: C.Env, rep: Report):
    """Two RAD IDE processes of the same installation at once (File > New Window, or a second start with
    --new-window): both start, both work, closing one leaves the other alive."""
    C.portable_copy(env)
    st = {}

    def both():
        a = C.launch(env, "J10a", extra_env={"RADIDE_INSTANCE_NAME": "e2e-j10a"})
        rep.ide = a
        b = C.launch(env, "J10b", extra_env={"RADIDE_INSTANCE_NAME": "e2e-j10b"},
                     exe=None if env.source else [str(env.app / "RADIDE.exe"), "--new-window"])
        st["a"], st["b"] = a, b
        ha, hb = a.call("hello"), b.call("hello")
        check(ha["pid"] != hb["pid"], "same process")
        return f"pids {ha['pid']} + {hb['pid']}"
    if not rep.step("two IDE processes start side by side", both):
        return
    root = env.scratch / "projects" / "J10"
    root.mkdir(parents=True, exist_ok=True)

    def work():
        for k in ("a", "b"):
            st[k].call("new_project", language="vb-basic", name=f"Two{k.upper()}{int(time.time())}", location=str(root))
            st[k].call("designer_place", type="Button", x=30, y=30)
            st[k].call("designer_dclick", name="Button1")
            check("Button1_Click" in st[k].call("editor_text")["text"], f"{k}: no handler")
        return "both edit a project (Monaco editors in both)"
    rep.step("both work at the same time (designer + Monaco)", work)

    def close_one():
        st["a"].quit()
        time.sleep(3)
        h = st["b"].call("hello")
        C.no_internal_errors(st["b"])
        rep.ide = st["b"]
        return f"second IDE still answers ({h['title']})"
    rep.step("closing one leaves the other running", close_one)
    st["b"].quit()
    rep.ide = None
