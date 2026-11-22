# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""Mobile journey - Python Kivy: a "Notes" app designed on the phone frame, run as a phone-size window.

    .venv\\Scripts\\python samples\\Tests\\E2E\\Mobile\\journey_kivy.py

Steps:
  toolchain      kivy importable by the interpreter the Kivy plugin resolves (else every step SKIPs)
  new project    File > New Project > Mobile > Python Kivy App
  design main    MainScreen: app bar title, label, note field, Add button, list (Shout switch deleted)
  add detail     Project > Add Form "DetailScreen": label + Back button
  code           MainScreen.py / DetailScreen.py typed in the editor: notes saved to notes.json (local storage),
                 list tap -> DetailScreen with the note
  devices        Device property: phone / tablet / Galaxy Z Fold6 (Flat / Folded) previews in the designer
  run            F5's run spec (python MainScreen.py) with the runtime's test hooks: the phone-size window appears
                 (PrintWindow screenshot), scripted input adds a note and opens it, notes.json is written
  arabic         SKIP: Kivy has no bidi / Arabic shaping (letters would be shown unjoined, left-to-right)
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

j = E.Journey("Mobile", "kivy", "Python Kivy Notes app")
STEPS = ["new project", "design main", "add detail", "code", "devices", "run", "arabic"]
INTERP = ""
with j.step("toolchain"):
    from radide.languages import get_plugin
    INTERP = get_plugin("kivy").find_interpreter("")
    code, out = E.run([INTERP, "-c", "import kivy; print('KIVY', kivy.__version__)"], timeout=120)
    if "KIVY" not in out:
        j.steps[-1:] = []
        for s in STEPS:
            with j.step(s):
                raise E.Skip(f"kivy is not importable by {INTERP}")
        j.finish(close=False)
    j.note(f"{INTERP}: {out.strip().splitlines()[-1]}")

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


with j.step("new project"):
    shutil.rmtree(j.work / "KivyNotes", ignore_errors=True)
    j.new_project("kivy", "kivy_app", "KivyNotes")
    folder = Path(win.project.folder)
    j.check("MainScreen" in win.project.forms, f"forms {win.project.forms}")
    j.shot(win, "ide_new_kivy_project")
    j.note(f"forms {win.project.forms}")

with j.step("design main"):
    need()
    v = designer("MainScreen")
    doc = v.doc
    for name, key, val in (("AppBar1", "Title", "Notes"), ("lblHello", "Text", "0 notes"), ("btnHello", "Text", "Add")):
        c = doc.form.find(name)
        j.check(c is not None, f"no {name}")
        doc.set_prop(c, key, val)
    sw = doc.form.find("swShout")
    if sw is not None:
        doc.select(sw)
        doc.delete_selected() if hasattr(doc, "delete_selected") else doc.remove_control(sw)
    j.check(doc.form.find("swShout") is None, "switch not deleted")
    E.pump(0.3)
    j.shot(v, "designer_main")
    j.note(f"controls {[c.name for c in doc.form.controls]}")

with j.step("add detail"):
    need()
    from PyQt6.QtCore import QPoint
    from radide.workspace import create_form
    win.save_all()
    create_form(win.project, "DetailScreen")
    win._fill_solution()
    v = designer("DetailScreen")
    for typ, name, text, top in (("AppBar", "AppBar1", "Note", 0), ("Label", "lblNote", "(note)", 80),
                                 ("Button", "btnBack", "Back", 160)):
        v.create_control(typ, QPoint(16, top + 8))
        E.pump(0.05)
        c = v.doc.selected
        j.check(c is not None and c.type == typ, f"Toolbox {typ}: {c}")
        v.doc.set_prop(c, "Name", name)
        v.doc.set_prop(c, "Title" if typ == "AppBar" else "Text", text)
    j.shot(v, "designer_detail")

MAIN_PY = '''# MainScreen - notes list (written in the RAD IDE code editor).
import json
import os

from MainScreen_designer import MainScreenDesigner, RadEvent, run_app  # noqa: F401

NOTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "notes.json")


class MainScreen(MainScreenDesigner):
    def MainScreen_Load(self):
        self.notes = json.load(open(NOTES, encoding="utf-8")) if os.path.exists(NOTES) else []
        self.lstGreetings.clear()
        for n in self.notes:
            self.lstGreetings.add_item(n)
        self.lblHello.text = f"{len(self.notes)} notes"

    def btnHello_Click(self):
        text = self.txtName.text.strip()
        if not text:
            self.Toast("Write a note first")
            return
        self.notes.append(text)
        with open(NOTES, "w", encoding="utf-8") as f:
            json.dump(self.notes, f)
        self.lstGreetings.add_item(text)
        self.lblHello.text = f"{len(self.notes)} notes"
        self.txtName.text = ""

    def lstGreetings_Tap(self, e):
        self.ShowForm("DetailScreen", self.lstGreetings.items[e.Index])

    def AppBar1_Click(self, e):
        self.MsgBox("Notes - made with RAD IDE and Kivy.", "About")


if __name__ == "__main__":
    run_app('MainScreen')
'''

DETAIL_PY = '''# DetailScreen - one note (written in the RAD IDE code editor).
from DetailScreen_designer import DetailScreenDesigner, RadEvent  # noqa: F401


class DetailScreen(DetailScreenDesigner):
    def DetailScreen_Load(self):
        self.lblNote.text = str(self.FormArgs or "(no note)")

    def btnBack_Click(self):
        self.CloseForm()
'''

with j.step("code"):
    need()
    win.save_all()
    E.pump(0.5)
    j.edit(folder / "MainScreen.py", MAIN_PY)
    j.edit(folder / "DetailScreen.py", DETAIL_PY)
    win.save_all()
    from radide.languages import get_plugin
    get_plugin("kivy").regenerate_all(win.project)
    j.check((folder / "DetailScreen_designer.py").exists(), "DetailScreen_designer.py not generated")
    code, out = E.run([INTERP, "-m", "py_compile", str(folder / "MainScreen.py"), str(folder / "DetailScreen.py"),
                       str(folder / "MainScreen_designer.py"), str(folder / "DetailScreen_designer.py")])
    j.check(code == 0, out[-600:])
    j.shot(win, "ide_code_kivy")

with j.step("devices"):
    need()
    v = designer("MainScreen")
    doc = v.doc
    seen = {}
    for dev, posture in (("pixel", None), ("tablet", None), ("galaxy_z_fold6", "Flat"),
                         ("galaxy_z_fold6", "Folded")):
        from radide import devices as DV
        if dev not in DV.DEVICES:
            continue
        doc.set_prop(None, "Device", dev)
        if posture:
            doc.set_prop(None, "Posture", posture)
        E.pump(0.3)
        k = dev + (f"/{posture}" if posture else "")
        seen[k] = (doc.form.props["Width"], doc.form.props["Height"])
        j.shot(v, "device_" + k.replace("/", "_"))
    doc.set_prop(None, "Posture", "Flat")
    doc.set_prop(None, "Device", "pixel")
    win.save_all()
    j.check(len(seen) >= 3, seen)
    j.note(str(seen))

EXEC = r'''
import json, os
from kivy.clock import Clock
out = os.environ["E2E_KIVY_OUT"]
res = {}
def step1(dt):
    scr.txtName.text = "Buy milk"
    scr.btnHello_Click()
    res["count"] = scr.lblHello.text
    res["items"] = list(scr.lstGreetings.items)
    json.dump(res, open(out + ".part", "w"))
    Clock.schedule_once(step2, 1.0)
def step2(dt):
    scr.lstGreetings_Tap(type("E", (), {"Index": len(scr.lstGreetings.items) - 1})())
    Clock.schedule_once(step3, 1.5)
def step3(dt):
    cur = app.sm.current_screen
    res["screen"] = cur.name
    res["note"] = cur.lblNote.text
    json.dump(res, open(out, "w"))
step1(0)
'''

with j.step("run"):
    need()
    from radide.languages import get_plugin
    from radide.model import Project
    plugin = get_plugin("kivy")
    spec = plugin.run_spec(folder, Project.load(folder).startup or "MainScreen", INTERP)
    (folder / "notes.json").unlink(missing_ok=True)
    outp = j.work / "kivy_result.json"
    outp.unlink(missing_ok=True)
    env = dict(spec.env or os.environ)
    env.update(RADKIVY_EXEC=EXEC, RADKIVY_AUTOSTOP="14", E2E_KIVY_OUT=str(outp))
    p = E.start([spec.program, *spec.args], cwd=spec.cwd or folder, env=env, log=j.work / "kivy_run.log")
    w = E.wait_window(p, "", 60)
    j.check(w is not None, f"no Kivy window: {(j.work / 'kivy_run.log').read_text(errors='replace')[-800:]}")
    E.pump(2.5)
    j.shot_window(w[0], "kivy_window_main")
    ok = E.wait(lambda: outp.exists(), 25, 0.3)
    if w and p.poll() is None:
        j.shot_window(w[0], "kivy_window_detail")
    try:
        p.wait(20)
    except Exception:  # noqa: BLE001
        E.close_window(w[0])
        E.kill_tree(p)
    log = (j.work / "kivy_run.log").read_text(encoding="utf-8", errors="replace")
    j.check(ok, f"scripted run did not finish: {log[-1200:]}")
    res = json.loads(outp.read_text())
    j.check(res.get("count") == "1 notes" and "Buy milk" in res.get("items", []), f"after Add: {res}")
    j.check(res.get("screen") == "DetailScreen" and res.get("note") == "Buy milk", f"detail: {res}")
    stored = json.loads((folder / "notes.json").read_text(encoding="utf-8"))
    j.check(stored == ["Buy milk"], f"notes.json {stored}")
    j.note(f"window '{w[1]}'; {res}; notes.json saved")

with j.step("arabic"):
    raise E.Skip("Kivy renders text without bidi / Arabic shaping (no RTL support in Kivy or in the generated "
                 "code): an Arabic screen would show unjoined letters left-to-right")

j.finish()
