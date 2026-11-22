# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Mobile journey - React Native (Expo): a "Notes" app built in the IDE's phone-frame form designer.

    .venv\\Scripts\\python samples\\Tests\\E2E\\Mobile\\journey_expo.py

Steps:
  toolchain      node + npx found
  new project    File > New Project > Mobile > React Native (Expo) App (MainScreen + DetailsScreen)
  design main    MainScreen in the designer: app bar title, label, note text field, Add button, list, About button
                 (Properties window edits through the designer document); the Shout switch is deleted
  add about      Project > Add Form "AboutScreen": Arabic labels aligned right (RTL text), app bar, Back button
  code           MainScreen.jsx / AboutScreen.jsx handlers typed in the code editor: notes kept in localStorage,
                 tap a note -> DetailsScreen, About -> AboutScreen
  generate       Save All: *_designer.jsx + App.js list the three screens
  run preview    F5 (Expo on the web, the IDE's ExpoSession): npm install + expo start --web, the Preview shows
                 the app; add a note through the page (DOM), it is listed and stored; reload keeps it;
                 tap it -> details; About -> Arabic screen (text-align right)
  export web     npx expo export --platform web; the bundle is served from 127.0.0.1 and loaded in a
                 QWebEngineView at phone size: same checks on the exported app
"""
from __future__ import annotations

import json
import os
import shutil
import sys

from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import e2e_lib as E  # noqa: E402

j = E.Journey("Mobile", "expo", "Expo / React Native Notes app")
STEPS = ["new project", "design main", "add about", "code", "generate", "run preview", "export web"]
NODE, NPX = shutil.which("node"), shutil.which("npx")
with j.step("toolchain"):
    if not (NODE and NPX):
        j.steps[-1:] = []
        for s in STEPS:
            with j.step(s):
                raise E.Skip("Node.js (node + npx) not found")
        j.finish(close=False)
    code, out = E.run([NODE, "--version"])
    j.note(f"node {out.strip()}")

win = j.window(1600, 1000)
folder: Path | None = None


def need():
    if folder is None:
        raise E.Skip("no project")


def designer(form):
    win.open_designer(form)
    E.pump(0.5)
    v = win._current_designer()
    j.check(v is not None, f"designer of {form} did not open")
    return v


def setp(v, name, key, value):
    c = v.doc.form.find(name) if name else None
    j.check(name is None or c is not None, f"no control {name}")
    v.doc.set_prop(c, key, value)
    E.pump(0.02)
    got = (c.props if c is not None else v.doc.form.props).get(key)
    j.check(got == value, f"{name}.{key} = {got!r}, wanted {value!r}")


# ============================================================================ 1. new project
with j.step("new project"):
    # node_modules of an earlier run is kept aside (npm install of Expo takes many minutes the first time)
    cache = j.out / "_node_modules_cache"
    old_nm = j.work / "NotesApp" / "NotesApp" / "node_modules"
    if old_nm.is_dir() and not cache.exists():
        shutil.move(str(old_nm), str(cache))
    shutil.rmtree(j.work / "NotesApp", ignore_errors=True)
    j.new_project("expo", "expo_app", "NotesApp")
    folder = Path(win.project.folder)
    if cache.is_dir() and not (folder / "node_modules").exists():
        shutil.move(str(cache), str(folder / "node_modules"))
        lock = folder / "node_modules" / ".package-lock.json"
        if lock.exists():
            os.utime(lock)                    # newer than package.json: the IDE skips npm install
        j.note("node_modules reused from the previous run")
    j.check((folder / "package.json").exists() and "MainScreen" in win.project.forms,
            f"forms {win.project.forms}")
    E.pump(0.5)
    j.shot(win, "ide_new_expo_project")
    j.note(f"forms {win.project.forms}")

# ============================================================================ 2. design MainScreen
with j.step("design main"):
    need()
    v = designer("MainScreen")
    setp(v, None, "Text", "Notes")
    setp(v, "AppBar1", "Title", "Notes")
    setp(v, "lblHello", "Text", "Write a note and tap Add.")
    setp(v, "txtName", "Hint", "Note text") if "Hint" in v.doc.form.find("txtName").props else None
    setp(v, "btnHello", "Text", "Add")
    setp(v, "btnDetails", "Text", "About (عن التطبيق)")
    sw = v.doc.form.find("swShout")
    if sw is not None:
        v.doc.select(sw)
        v.doc.delete_selected() if hasattr(v.doc, "delete_selected") else v.doc.remove_control(sw)
        E.pump(0.1)
    j.check(v.doc.form.find("swShout") is None, "Shout switch not deleted")
    dev = v.doc.form.props.get("Device")
    j.shot(v, "designer_main_phone")
    # device sizes: a foldable and back (the form follows the safe area)
    v.doc.set_prop(None, "Device", "galaxy_z_fold6")
    E.pump(0.3)
    fold = (v.doc.form.props["Width"], v.doc.form.props["Height"])
    j.shot(v, "designer_main_fold6")
    v.doc.set_prop(None, "Device", dev or "pixel")
    E.pump(0.3)
    phone = (v.doc.form.props["Width"], v.doc.form.props["Height"])
    j.check(fold[0] > phone[0], f"foldable {fold} vs phone {phone}")
    j.note(f"device {dev}: {phone}; Galaxy Z Fold6: {fold}")

# ============================================================================ 3. Add Form AboutScreen (Arabic)
with j.step("add about"):
    need()
    from radide.workspace import create_form
    win.save_all()
    create_form(win.project, "AboutScreen")          # Project > Add Form (dialog OK)
    win._reload_startup_code() if hasattr(win, "_reload_startup_code") else None
    win._fill_solution()
    v = designer("AboutScreen")
    j.check("AboutScreen" in win.project.forms, f"forms {win.project.forms}")
    v.doc.set_prop(None, "Text", "حول التطبيق")
    from PyQt6.QtCore import QPoint
    added = {}
    for typ, name, text, top in (("AppBar", "AppBar1", "حول التطبيق", 0), ("Label", "lblTitle", "تطبيق الملاحظات", 80),
                                 ("Label", "lblBody", "اكتب ملاحظاتك واحفظها على جهازك", 130),
                                 ("Button", "btnBack", "رجوع", 200)):
        v.create_control(typ, QPoint(16, top + 8))
        E.pump(0.05)
        c = v.doc.selected
        j.check(c is not None and c.type == typ, f"Toolbox {typ} not placed: {c}")
        v.doc.set_prop(c, "Name", name)
        if typ == "AppBar":
            v.doc.set_prop(c, "Title", text)
        else:
            v.doc.set_prop(c, "Text", text)
        if typ == "Label":
            v.doc.set_prop(c, "TextAlign", "Right")
            v.doc.set_prop(c, "Width", 360)
            v.doc.set_prop(c, "FontSize", 16 if name == "lblTitle" else 12)
        added[name] = c
    j.shot(v, "designer_about_arabic")
    j.note(f"controls {[c.name for c in v.doc.form.controls]}")

# ============================================================================ 4. code
MAIN_JSX = """// MainScreen - the notes list (written in the RAD IDE code editor).
import { MainScreenDesigner } from './MainScreen_designer';
import { RadApp } from './radapp';

const KEY = 'rad-notes';
const store = globalThis.localStorage;          // web; on a phone use AsyncStorage

export default class MainScreen extends MainScreenDesigner {
  MainScreen_Load(e) {
    this.notes = JSON.parse((store && store.getItem(KEY)) || '[]');
    this.lstGreetings.Clear();
    for (const n of this.notes) this.lstGreetings.AddItem(`note|${n}`);
    this.lblHello.Text = `${this.notes.length} notes`;
  }

  btnHello_Click(e) {
    const text = this.txtName.Text.trim();
    if (!text) {
      this.Toast('Write a note first');
      return;
    }
    this.notes.push(text);
    if (store) store.setItem(KEY, JSON.stringify(this.notes));
    this.lstGreetings.AddItem(`note|${text}`);
    this.lblHello.Text = `${this.notes.length} notes`;
    this.txtName.Text = '';
  }

  lstGreetings_Tap(e) {
    this.ShowForm('DetailsScreen', this.lstGreetings.Field(e.Index, 1));
  }

  btnDetails_Click(e) {
    this.ShowForm('AboutScreen');
  }

  AppBar1_Click(e) {
    this.MsgBox('Notes - made with RAD IDE and React Native (Expo).', 'About');
  }
}
"""

ABOUT_JSX = """// AboutScreen - Arabic page (written in the RAD IDE code editor).
import { AboutScreenDesigner } from './AboutScreen_designer';
import { RadApp } from './radapp';

export default class AboutScreen extends AboutScreenDesigner {
  AboutScreen_Load(e) {
  }

  btnBack_Click(e) {
    this.CloseForm();
  }
}
"""

with j.step("code"):
    need()
    win.save_all()
    E.pump(0.5)
    j.edit(folder / "MainScreen.jsx", MAIN_JSX)
    j.edit(folder / "AboutScreen.jsx", ABOUT_JSX)
    j.shot(win, "ide_code_main_jsx")
    j.note("MainScreen.jsx + AboutScreen.jsx")

# ============================================================================ 5. generate
with j.step("generate"):
    need()
    win.save_all()
    from radide.languages import get_plugin
    get_plugin("expo").regenerate_all(win.project)       # what Run does before starting Expo
    app = (folder / "App.js").read_text(encoding="utf-8")
    j.check(all(f"name=\"{n}\"" in app or f"name={json.dumps(n)}" in app for n in
                ("MainScreen", "DetailsScreen", "AboutScreen")), app[-900:])
    des = (folder / "AboutScreen_designer.jsx").read_text(encoding="utf-8")
    j.check("تطبيق الملاحظات" in des and 'align="right"' in des, "Arabic right-aligned labels not generated")
    j.check("swShout" not in (folder / "MainScreen_designer.jsx").read_text(encoding="utf-8"),
            "deleted switch still generated")
    code, out = E.run([NODE, "--check", str(folder / "radapp.js")])
    j.note("App.js has 3 screens; AboutScreen_designer.jsx right-aligned Arabic labels")


# ============================================================================ helpers for the running app (DOM)
SET_INPUT = """(function(v){var i=document.querySelector('input,textarea'); if(!i) return 'no input';
var set=Object.getOwnPropertyDescriptor(i.tagName=='INPUT'?HTMLInputElement.prototype:HTMLTextAreaElement.prototype,'value').set;
set.call(i,v); i.dispatchEvent(new Event('input',{bubbles:true})); return 'ok';})(%s)"""
CLICK_TEXT = """(function(t){var els=[...document.querySelectorAll('div,span,button,a')].filter(e=>e.childElementCount==0&&e.textContent.trim()==t);
if(!els.length) return 'no '+t; var e=els[els.length-1]; var b=e.closest('[role=button],button,[tabindex]')||e;
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(n=>b.dispatchEvent(new MouseEvent(n,{bubbles:true,cancelable:true,view:window})));
return 'ok';})(%s)"""


def body_text(page):
    return E.js(page, "document.body ? document.body.innerText : ''", 5) or ""


def reload(page):
    """Reload the page and wait until the app has rendered its text field again."""
    E.js(page, "window.__e2e_old = 1, location.reload(), 1")
    E.wait(lambda: E.js(page, "window.__e2e_old === undefined && !!document.querySelector('input')", 3) is True,
           90, 0.4)
    E.pump(0.5)


def exercise(view, label: str):
    """Add a note through the page, check list + localStorage, reload, details, About (RTL)."""
    page = view.page()
    ok = E.wait(lambda: "Notes" in body_text(page) and "Add" in body_text(page), 120, 0.5)
    j.check(ok, f"{label}: app did not render: {body_text(page)[:300]}")
    E.js(page, "localStorage.removeItem('rad-notes'), 1")
    reload(page)
    E.wait(lambda: "0 notes" in body_text(page), 60, 0.5)
    j.shot(view, f"{label}_notes_empty")
    r = E.js(page, SET_INPUT % json.dumps("Buy bread"))
    j.check(r == "ok", f"{label}: input: {r}")
    E.pump(0.3)
    r = E.js(page, CLICK_TEXT % json.dumps("Add"))
    j.check(r == "ok", f"{label}: Add: {r}")
    ok = E.wait(lambda: "1 notes" in body_text(page) and "Buy bread" in body_text(page), 15, 0.3)
    j.check(ok, f"{label}: note not listed: {body_text(page)[:300]}")
    stored = E.js(page, "localStorage.getItem('rad-notes')")
    j.check(stored and "Buy bread" in stored, f"{label}: localStorage {stored}")
    j.shot(view, f"{label}_note_added")
    reload(page)
    ok = E.wait(lambda: "Buy bread" in body_text(page), 60, 0.5)
    j.check(ok, f"{label}: note lost after reload")
    r = E.js(page, CLICK_TEXT % json.dumps("Buy bread"))
    ok = E.wait(lambda: "Details" in body_text(page) or "Back" in body_text(page), 15, 0.3)
    j.check(r == "ok" and ok and "Buy bread" in body_text(page), f"{label}: details: {r} {body_text(page)[:200]}")
    j.shot(view, f"{label}_details")
    E.js(page, CLICK_TEXT % json.dumps("Back"))
    E.wait(lambda: "About (عن التطبيق)" in body_text(page), 15, 0.3)
    r = E.js(page, CLICK_TEXT % json.dumps("About (عن التطبيق)"))
    ok = E.wait(lambda: "تطبيق الملاحظات" in body_text(page), 15, 0.3)
    j.check(r == "ok" and ok, f"{label}: About: {r} {body_text(page)[:200]}")
    align = E.js(page, """(function(){var e=[...document.querySelectorAll('div')].filter(x=>x.childElementCount==0&&
        x.textContent.trim()=='تطبيق الملاحظات').pop(); return e?getComputedStyle(e).textAlign:'none';})()""")
    j.check(align in ("right", "end"), f"{label}: Arabic label text-align {align}")
    j.shot(view, f"{label}_about_arabic")
    return align


# ============================================================================ 6. run in the IDE (F5, Expo web)
with j.step("run preview"):
    need()
    feat = win.expo
    dev = feat.current_device()
    j.check(dev.get("platform") == "web", f"expo device is {dev}")
    s = feat.run(debug=False)
    j.check(s is not None, f"Expo session not started: {j.msgs[-3:]}")
    view = win.web_preview.view
    ok = E.wait(lambda: view.url().toString().startswith("http"), 3000, 1.0)
    j.check(ok, f"no Preview URL from Expo: {j.output_text()[-1500:]}")
    j.note(f"Preview {view.url().toString()}")
    align = exercise(view, "preview")
    j.shot(win, "ide_expo_running")
    try:
        s.stop()
    except Exception:  # noqa: BLE001
        pass
    E.pump(2)
    j.note(f"add/list/localStorage/reload/details/About OK; Arabic text-align {align}")

# ============================================================================ 7. export web bundle
with j.step("export web"):
    need()
    if not (folder / "node_modules" / "expo").is_dir():
        code, out = E.run(["npm.cmd" if os.name == "nt" else "npm", "install", "--no-audit", "--no-fund"],
                          cwd=folder, timeout=1800)
        j.check(code == 0, f"npm install: {out[-800:]}")
    dist = folder / "dist"
    shutil.rmtree(dist, ignore_errors=True)
    code, out = E.run([NPX, "expo", "export", "--platform", "web", "--output-dir", "dist"], cwd=folder,
                      env=dict(os.environ, EXPO_NO_TELEMETRY="1", CI="1"), timeout=1800)
    (j.out / "expo_export.log").write_text(out, encoding="utf-8")
    j.check(code == 0 and (dist / "index.html").exists(), f"expo export: {out[-1200:]}")
    port = E.free_port()
    p = E.start([sys.executable, "-I", "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory",
                 str(dist)], log=j.work / "dist_server.log")
    j.check(E.http_up(f"http://127.0.0.1:{port}/", 30), "static server for dist/ did not start")
    from PyQt6.QtCore import QUrl
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    v = QWebEngineView()
    v.resize(412, 860)
    v.show()
    v.load(QUrl(f"http://127.0.0.1:{port}/"))
    align = exercise(v, "export")
    E.kill_tree(p)
    v.close()
    size = sum(f.stat().st_size for f in dist.rglob("*") if f.is_file())
    j.note(f"dist {size // 1024} KB, {len(list(dist.rglob('*.js')))} js files; same journey passes on the bundle")

j.finish()
