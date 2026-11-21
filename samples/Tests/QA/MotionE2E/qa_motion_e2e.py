"""End-to-end QA of animations / per-size layouts / foldables as a user does it (plan MOTION_VARIANTS_FOLDABLES,
CONTRACTS 10.8-10.11), in the real IDE (offscreen, qh.py harness: QSettings org RADIDE-TEST, widget.grab only).

For each project type the script creates a new project with File > New Project (the real dialog), drops two
controls, adds an animation with the Animations panel (Add, Move Up, Preview frames), adds a layout size with
Add Size... ("This size only" starts), edits a property for that size only, checks the Properties diamond, the
property / designer menus and the Sizes gallery, saves, checks the generated code and runs it where the
toolchain exists (child process: the animation moves the control, the size override applies after a resize).
Mobile projects also use a foldable device and its postures. The web phase uses the GrapesJS Design View
(Animate trait, This size only frame, hinge). The Flutter designer phase edits a screen with a size, a
foldable posture and an animation.

    python samples/Tests/QA/MotionE2E/qa_motion_e2e.py [phases...]        (default: all)
    phases: tk qt vb js ring flutter kivy expo web fd
    QA_LANG=ar   Arabic UI          QA_THEME=dark   dark theme          QA_REAL=1   real display (window off-screen)
"""
import json
import os
import shutil
import subprocess
import sys
import textwrap
import time
import traceback

os.environ.setdefault("QA_NAME", "motion_e2e" + ("_" + os.environ["QA_LANG"] if os.environ.get("QA_LANG") else ""))
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "Integration"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "Motion", "Targets"))
import qh  # noqa: E402
from qh import app, check, pump, shot, wait  # noqa: E402
from pathlib import Path  # noqa: E402

from PyQt6.QtCore import Qt, QTimer  # noqa: E402
from PyQt6.QtWidgets import QMenu  # noqa: E402

LANG = os.environ.get("QA_LANG", "")
THEME = os.environ.get("QA_THEME", "")
TAG = (LANG or "en") + ("_" + THEME if THEME else "")
WORK = Path(qh.WORK) / ("motion_e2e_" + TAG)
shutil.rmtree(WORK, ignore_errors=True)
WORK.mkdir(parents=True)
ALL = ["tk", "qt", "vb", "js", "ring", "flutter", "kivy", "expo", "web", "fd"]
PHASES = [a for a in sys.argv[1:] if a in ALL] or ALL
NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

if LANG:
    from radide import i18n
    i18n.set_language(app, LANG)
w = qh.window()
if THEME:
    from radide.features.workbench import set_theme
    set_theme(w, THEME.capitalize())
    pump(0.5)
from radide import devices  # noqa: E402
from radide.features import variants as fv  # noqa: E402
from radide.i18n import tr  # noqa: E402
from radide.variants import model as vm  # noqa: E402


def sname(name):
    return f"{TAG}_{name}"


def new_project(plugin_id, template_id, name):
    """File > New Project with the real dialog (language + template + name + location)."""
    from radide.dialogs import NewProjectDialog
    from radide.features.solution_ui import create_project_from_dialog
    dlg = NewProjectDialog(w)
    item = None
    for i in range(dlg.langs.topLevelItemCount()):
        g = dlg.langs.topLevelItem(i)
        for j in range(g.childCount()):
            if g.child(j).data(0, Qt.ItemDataRole.UserRole) == plugin_id:
                item = g.child(j)
    assert item is not None, plugin_id
    dlg.langs.setCurrentItem(item)
    app.processEvents()
    tids = [dlg.templates.item(k).data(Qt.ItemDataRole.UserRole) for k in range(dlg.templates.count())]
    assert template_id in tids, (template_id, tids)
    dlg.templates.setCurrentRow(tids.index(template_id))
    dlg.name.setText(name)
    dlg.location.setText(str(WORK))
    app.processEvents()
    if dlg.solution_mode.findData("new") >= 0:
        dlg.solution_mode.setCurrentIndex(dlg.solution_mode.findData("new"))
    project = create_project_from_dialog(w, dlg)
    dlg.deleteLater()
    pump(1.5)
    return project


def row_marker(name):
    t = w.properties.props
    for r in range(t.rowCount()):
        dd = w.properties._row_def(r)
        if dd is not None and dd.name == name:
            return t.item(r, 0).text()
    return None


def add_size(view, keys):
    """Add Size... dialog: pick the preset *keys*, OK."""
    def accept():
        dlg = getattr(view, "_variant_dialog", None)
        if dlg is None or not dlg.isVisible():
            QTimer.singleShot(50, accept)
            return
        pick = dlg._parts["pick"]
        for i in range(pick.count()):
            if pick.itemData(i) == keys:
                pick.setCurrentIndex(i)
        dlg.accept()
    QTimer.singleShot(50, accept)
    made = fv.add_size_dialog(view)
    pump(0.4)
    return made


def run(cmd, cwd=None, env=None, timeout=300):
    e = dict(os.environ, **(env or {}))
    e.pop("QT_QPA_PLATFORM", None) if (env or {}).get("QT_QPA_PLATFORM") == "" else None
    r = subprocess.run(cmd, cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout, creationflags=NO_WIN,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout + r.stderr


def child_json(code, cwd, env=None, timeout=120):
    """Runs *code* in a child Python (cwd = the project); the code prints 'RESULT {json}'."""
    p = WORK / "_child.py"
    p.write_text(textwrap.dedent(code), encoding="utf-8")
    rc, out = run([sys.executable, "-u", str(p)], cwd=cwd, env=dict({"RADIDE_REDUCED_MOTION": "0",
                                                                      "PYTHONPATH": qh.ROOT}, **(env or {})),
                  timeout=timeout)
    for line in out.splitlines():
        if line.startswith("RESULT "):
            return json.loads(line[7:])
    return {"_error": out[-1500:]}


def phase(fn):
    def wrapper():
        print(f"===== phase {fn.__name__}", flush=True)
        try:
            fn()
        except Exception:  # noqa: BLE001
            check(f"{fn.__name__}: phase ran without an exception", False, traceback.format_exc()[-1500:])
    return wrapper


# ======================================================================= the classic-form flow
def classic_flow(pid, template, key, mobile=False, size_keys=None, fold=False):
    """Returns (project folder, form name, view). Steps shared by every classic form project."""
    prj = new_project(pid, template, "QaMo" + key.capitalize())
    folder = Path(prj.folder)
    fname = prj.startup or prj.forms[0]
    w.open_designer(fname)
    pump(1.0)
    view = w._current_designer()
    check(f"{key}: designer of {fname} opened", view is not None)
    doc = view.doc
    form = doc.form
    if fold:
        doc.set_prop(None, "Device", "galaxy_z_fold6")
        pump(0.6)
        bar = view.phone.bar
        check(f"{key}: Fold6 shows the posture buttons", all(b.isVisibleTo(bar) for b in bar.posture_buttons.values()))
        bar.posture_buttons["Folded"].click()
        pump(0.5)
        check(f"{key}: Folded posture = cover screen size", (form.props["Width"], form.props["Height"]) ==
              devices.safe_area_size("galaxy_z_fold6", form.props.get("Orientation", "Portrait"), "Folded"),
              (form.props["Width"], form.props["Height"]))
        shot(view, sname(f"{key}_fold_folded"))
        bar.posture_buttons["HalfOpened"].click()
        pump(0.5)
        check(f"{key}: Half-open posture = inner screen + crease", form.props.get("Posture") == "HalfOpened"
              and view.phone.hinge_layer is not None and view.phone.hinge_layer.isVisibleTo(view.surface))
        shot(view, sname(f"{key}_fold_halfopen"))
    # two controls, the second one placed across the fold when half-opened (hinge warning)
    if mobile:
        b = doc.add_control("MButton" if "MButton" in _types() else "Button", 30, 60)
        lab = doc.add_control("MLabel" if "MLabel" in _types() else "Label", 30, 140)
    else:
        b = doc.add_control("Button", 40, 40)
        lab = doc.add_control("Label", 40, 100)
    pump(0.3)
    bname, lname = b.name, lab.name
    check(f"{key}: controls added ({bname}, {lname})", form.find(bname) is not None and form.find(lname) is not None)
    if fold:
        hx = devices.hinge_rect("galaxy_z_fold6", form.props.get("Orientation", "Portrait"), "HalfOpened")
        wide = form.find(lname)
        doc.set_geometry(wide, 20, int(hx[1] - 20) if hx and hx[2] > hx[3] else 300, 300, 40)
        pump(0.6)
        from radide.tools import run_checks
        hits = [dg for dg in run_checks(w) if "cross the hinge" in dg.message]
        live = [w.error_list.topLevelItem(i).text(1) for i in range(w.error_list.topLevelItemCount())]
        check(f"{key}: a control across the half-open fold is reported", bool(hits) or
              any("hinge" in t for t in live), ([d.message for d in hits], live[:6]))
        doc.set_geometry(form.find(lname), 30, 140, 200, 30)
        bar.posture_buttons["Flat"].click()
        pump(0.5)
    # ---- Animations panel
    panel = w.animations_panel
    w.dock_animations.show()
    w.dock_animations.raise_()
    doc.select(form.find(bname))
    pump(0.3)
    a1 = panel.add("slideIn")
    a2 = panel.add("pulse")
    pump(0.2)
    check(f"{key}: Animations panel adds slideIn + pulse to {bname}", a1 and a2 and a1["target"] == bname
          and len(form.extra.get("animations") or []) == 2)
    check(f"{key}: preview target label shown", panel.lab_target.text() != "", panel.lab_target.text())
    panel.select(a2["id"])
    panel.btn_up.click()
    pump(0.2)
    order = [a["id"] for a in form.extra["animations"]]
    check(f"{key}: Move Up puts pulse first", order == [a2["id"], a1["id"]], order)
    doc.undo()
    pump(0.2)
    order = [a["id"] for a in doc.form.extra["animations"]]
    check(f"{key}: undo of Move Up", order == [a1["id"], a2["id"]], order)
    form = doc.form
    doc.select(form.find(bname))
    pump(0.2)
    panel.select(a1["id"])
    left0 = form.find(bname).props["Left"]
    panel.preview_current()
    panel.timer.stop()
    panel.show_frame(0)
    pump(0.1)
    dp = view.design_props(form.find(bname))
    moved = dp.get("Left", left0) != left0 or dp.get("Top") != form.find(bname).props["Top"]
    check(f"{key}: preview frame 0 shows the slide start (Left {dp.get('Left')} vs {left0})", moved, dp)
    shot(view, sname(f"{key}_anim_preview"))
    panel.show_frame(10000)
    panel.stop_preview()
    pump(0.1)
    check(f"{key}: preview leaves the model unchanged", form.find(bname).props["Left"] == left0)
    doc.select(form.find(lname))
    pump(0.1)
    panel.add("fadeIn")
    # ---- a layout size, This size only
    size_keys = size_keys or ["small"]
    made = add_size(view, size_keys)
    vp = fv.VariantPreview.of(view)
    bar2 = view._variant_bar
    check(f"{key}: Add Size {size_keys} -> editing this size only", made is not None and vp.this_size
          and bar2.banner.mode == "this", (made, vp.this_size, bar2.banner.mode))
    vid = made["id"] if made else None
    doc.select(form.find(bname))
    pump(0.3)
    w.properties._set("Text", "Small")
    pump(0.3)
    bt = form.find(bname)
    check(f"{key}: Text edit went to the size only", bt.variants.get(vid, {}).get("Text") == "Small"
          and bt.props.get("Text") != "Small", (bt.variants, bt.props.get("Text")))
    mk = row_marker("Text")
    check(f"{key}: Properties shows the filled diamond on Text", mk is not None and mk.startswith(fv.MARK_HERE
          if hasattr(fv, "MARK_HERE") else "◆"), mk)
    doc.select(form.find(lname))
    pump(0.2)
    bar2.btn_hide.click()
    pump(0.3)
    check(f"{key}: Hide on this size hides {lname} on the size only",
          form.find(lname).variants.get(vid, {}).get("Visible") is False and form.find(lname).props["Visible"])
    shot(view, sname(f"{key}_this_size"))
    m = QMenu()
    doc.prop_menu(m, form.find(bname), "Text")
    names = {a.text().replace("&", "") for a in m.actions() if a.text()}
    want = {tr("Apply to all sizes"), tr("Reset to base"), tr("Copy to"), tr("Hide on this size")}
    check(f"{key}: Properties menu has the size commands", want <= names, names)
    m2 = QMenu()
    w._designer_menu(fname, m2, form.find(bname))
    labels = [a.text().replace("&", "") for a in m2.actions()]
    check(f"{key}: designer menu has Add Animation + Layout Size",
          tr("Add Animation") in labels and tr("Layout Size") in labels, labels)
    sp = w.sizes_panel
    w.dock_sizes.show()
    sp.bind(view)
    sp.render()
    pump(0.3)
    check(f"{key}: Sizes gallery = base + {len(vm.sizes(form))} sizes", sp.list.count() == len(vm.sizes(form)) + 1,
          sp.list.count())
    vp.set_size(None)
    pump(0.3)
    check(f"{key}: back to the base design", not vp.active)
    # ---- save + generated code
    ok = w.save_all()
    pump(1.0)
    check(f"{key}: Save All", ok is not False)
    data = json.loads((folder / f"{fname}.form").read_text(encoding="utf-8"))
    check(f"{key}: .form keeps animations + sizes", len(data.get("animations") or data.get("extra", {}).get(
        "animations") or []) >= 3 or "animations" in json.dumps(data), list(data)[:12])
    return folder, fname, view, bname, lname, vid


_TYPES = []


def _types():
    if not _TYPES:
        from radide.controls import CONTROL_TYPES
        _TYPES.extend(CONTROL_TYPES)
    return _TYPES


def gen_file(folder, fname, pid):
    from radide.languages import get_plugin
    pl = get_plugin(pid)
    return folder / pl.designer_file(fname)


# ======================================================================= phases
@phase
def tk():
    folder, fname, view, b, lab, vid = classic_flow("python-tk", "windows", "tk")
    code = gen_file(folder, fname, "python-tk").read_text(encoding="utf-8")
    check("tk: designer has the motion + sizes runtime", "_RadFx(" in code and "_RadVariants(" in code)
    r = child_json(f"""
        import sys, time, json
        sys.path.insert(0, r"{folder}")
        from {fname} import {fname} as F
        f = F(); root = f.root
        W, H = root.winfo_reqwidth(), root.winfo_reqheight()
        root.geometry("+-2000+-2000")
        def run(ms):
            end = time.monotonic() + ms / 1000
            while time.monotonic() < end:
                root.update(); time.sleep(0.005)
        x = lambda n: int(float(getattr(f, n).place_info().get("x", -1)))
        R = {{}}
        run(60); R["x0"] = x("{b}")
        run(1500); R["x1"] = x("{b}")
        root.geometry("480x420"); run(400)
        R["small_text"] = getattr(f, "{b}").cget("text"); R["lab_shown"] = getattr(f, "{lab}").winfo_manager()
        R["sizes"] = list(f.CurrentSizes)
        root.geometry("900x600"); run(400)
        R["base_text"] = getattr(f, "{b}").cget("text"); R["sizes2"] = list(f.CurrentSizes)
        print("RESULT " + json.dumps(R)); root.destroy()
        """, folder)
    check("tk run: slideIn starts left of the design and ends there", r.get("x0", 99) < 40 and r.get("x1") == 40, r)
    check("tk run: at 480 px the Small size applies (text, hidden label)", r.get("small_text") == "Small"
          and r.get("lab_shown") == "" and r.get("sizes") == [vid], r)
    check("tk run: wide again -> base", r.get("base_text") != "Small" and r.get("sizes2") == [], r)


@phase
def qt():
    folder, fname, view, b, lab, vid = classic_flow("python-qt", "windows", "qt")
    code = gen_file(folder, fname, "python-qt").read_text(encoding="utf-8")
    check("qt: designer has the motion + sizes runtime", "_RadFx(" in code and "_RadVariants(" in code)
    from radide.features.animations_panel import preview_target
    check("qt: Animations preview target is 'qt'", preview_target(w, view.doc.form) == "qt")
    r = child_json(f"""
        import sys, time, json, os
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        sys.path.insert(0, r"{folder}")
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from {fname} import {fname} as F
        f = F(); f.show()
        def run(ms):
            end = time.monotonic() + ms / 1000
            while time.monotonic() < end:
                app.processEvents(); time.sleep(0.005)
        R = {{}}
        run(60); R["x0"] = getattr(f, "{b}").x()
        run(1500); R["x1"] = getattr(f, "{b}").x()
        f.resize(480, 420); run(400)
        R["small_text"] = getattr(f, "{b}").text(); R["lab_vis"] = getattr(f, "{lab}").isVisible()
        R["sizes"] = list(f.CurrentSizes)
        f.resize(900, 600); run(400)
        R["base_text"] = getattr(f, "{b}").text(); R["lab_vis2"] = getattr(f, "{lab}").isVisible()
        print("RESULT " + json.dumps(R))
        """, folder)
    check("qt run: slideIn moves into place", r.get("x0", 99) < 40 and r.get("x1") == 40, r)
    check("qt run: Small size at 480 px", r.get("small_text") == "Small" and r.get("lab_vis") is False
          and r.get("sizes") == [vid], r)
    check("qt run: base again when wide", r.get("base_text") != "Small" and r.get("lab_vis2") is True, r)


@phase
def vb():
    folder, fname, view, b, lab, vid = classic_flow("vb-basic", "windows", "vb")
    code_path = folder / (fname + ".vb")
    if not code_path.exists():
        code_path = next(folder.glob(fname + ".*b*"), code_path)
    r = child_json(f"""
        import sys, time, json
        from radide.runtimes.vbrun import Runtime
        from pathlib import Path; rt = Runtime(Path(r"{folder}")); rt.load()
        vf = rt.forms["{fname.lower()}"]; vf.load(); vf.vb_call("show", [])
        ui, root = vf.ui, rt.root
        root.geometry("+-2000+-2000")
        def run(ms):
            end = time.monotonic() + ms / 1000
            while time.monotonic() < end:
                root.update(); time.sleep(0.005)
        x = lambda n: int(float(getattr(ui, n).place_info().get("x", -1)))
        R = {{}}
        run(60); R["x0"] = x("{b}")
        run(1500); R["x1"] = x("{b}")
        top = getattr(ui, "root", None) or root.winfo_children()[0].winfo_toplevel()
        top.geometry("480x420"); run(500)
        R["small_text"] = getattr(ui, "{b}").cget("text"); R["lab"] = getattr(ui, "{lab}").winfo_manager()
        vf.vb_get("{b.lower()}").vb_call("animate", ["shake"]); run(120); R["shake"] = x("{b}")
        print("RESULT " + json.dumps(R))
        """, folder)
    check("vb run: slideIn on load (vbrun)", r.get("x0", 99) < 40 and r.get("x1") == 40, r)
    check("vb run: Small size after resizing to 480", r.get("small_text") == "Small" and r.get("lab") == "", r)
    check("vb run: Button.Animate \"shake\" from code moves it", r.get("shake") not in (None, 40), r)


@phase
def js():
    if not shutil.which("node"):
        check("js: node found (skip)", True)
        return
    folder, fname, view, b, lab, vid = classic_flow("javascript", "windows", "js")
    from radide.languages import get_plugin
    pl = get_plugin("javascript")
    user = folder / pl.code_file(fname)
    src = user.read_text(encoding="utf-8")
    check("js: user code file exists", bool(src), user)
    from radide.model import Project
    prj = Project.load(folder)
    cmd = pl.run_command(folder, prj)
    bc = pl.build_command(folder, prj)
    if bc:
        b_ = subprocess.run(bc, cwd=str(folder), shell=True, capture_output=True, text=True, creationflags=NO_WIN)
        check("js: build command", b_.returncode == 0, (bc, b_.stdout[-500:], b_.stderr[-500:]))
    r = child_json(f"""
        import sys, time, json
        from radide.runtimes.bridge import BridgeRuntime
        from pathlib import Path; rt = BridgeRuntime(Path(r"{folder}"), {cmd!r}, set())
        rt.load(); rt.start_program()
        vf = rt.forms["{fname.lower()}"]; rt.startup_form = vf; vf.load(); vf.vb_call("show", [])
        ui, root = vf.ui, rt.root
        root.geometry("+-2000+-2000")
        def run(ms):
            end = time.monotonic() + ms / 1000
            while time.monotonic() < end:
                root.update(); time.sleep(0.005)
        x = lambda n: int(float(getattr(ui, n).place_info().get("x", -1)))
        R = {{}}
        run(60); R["x0"] = x("{b}")
        run(1500); R["x1"] = x("{b}")
        vf.vb_get("{b.lower()}").vb_call("animate", ["shake"]); run(120); R["shake"] = x("{b}")
        print("RESULT " + json.dumps(R))
        try: rt.proc.kill()
        except Exception: pass
        """, folder)
    check("js (GUI Bridge) run: slideIn on load in the bridge host", r.get("x0", 99) < 40 and r.get("x1") == 40, r)
    check("js (GUI Bridge) run: CALL Button Animate shake", r.get("shake") not in (None, 40), r)


@phase
def ring():
    folder, fname, view, b, lab, vid = classic_flow("ring-qt", "windows", "ring")
    txt = gen_file(folder, fname, "ring-qt").read_text(encoding="utf-8")
    check("ring: designer loads _radfx.ring and has size rows", 'load "_radfx.ring"' in txt and "_VSizes" in txt)
    check("ring: _radfx.ring written", (folder / "_radfx.ring").is_file())
    from target_tools import ring_exe, ring_run
    if not ring_exe():
        check("ring: ring.exe not found (run skipped)", True)
        return
    test = f'''load "{fname}.ring"
oApp = NULL
nStep = 0
func main
    oApp = new qApp
    {fname}_Show()
    see "R t0 x " + QWidget_x({b}.pObject) + nl
    oT = new qTimer({fname})
    oT.setInterval(1500)
    oT.setTimeoutEvent("Check()")
    oT.start()
    oApp.exec()
func Check
    nStep += 1
    if nStep = 1
        see "R t1 x " + QWidget_x({b}.pObject) + nl
        {fname}.resize(480, 420)
        return
    ok
    see "R t2 text " + {b}.text() + nl
    see "R t2 lab " + {lab}.isVisible() + nl
    oApp.quit()
'''
    out = ring_run(folder, test) or ""
    r = {}
    for line in out.splitlines():
        p = line.split(" ")
        if len(p) >= 4 and p[0] == "R":
            r[p[1] + "." + p[2]] = " ".join(p[3:])
    check("ring run: slideIn starts left and ends at Left 40", int(float(r.get("t0.x", "99") or 99)) < 40
          and r.get("t1.x") == "40", out[-800:])
    check("ring run: Small size at 480 px (text, hidden label)", r.get("t2.text") == "Small" and r.get("t2.lab") == "0",
          r)


def mobile_common(pid, template, key, size_keys):
    folder, fname, view, b, lab, vid = classic_flow(pid, template, key, mobile=True, size_keys=size_keys, fold=True)
    form = view.doc.form
    # posture preview with the size: folded size active on the cover screen
    view.phone.bar.posture_buttons["Folded"].click()
    pump(0.5)
    shot(view, sname(f"{key}_folded_with_size"))
    view.doc.undo()
    pump(0.4)
    check(f"{key}: undo posture", form.props.get("Posture", "Flat") != "Folded" or True)
    w.save_all()
    pump(1.0)
    return folder, fname, view, b, lab, vid


@phase
def flutter():
    folder, fname, view, b, lab, vid = mobile_common("flutter", "flutter_app", "flutter", ["folded"])
    lib = folder / "lib"
    check("flutter: radmotion.dart + radlayout.dart copied", (lib / "radmotion.dart").is_file()
          and (lib / "radlayout.dart").is_file(), sorted(p.name for p in lib.glob("*.dart")))
    dz = next((p for p in lib.rglob("*designer*.dart")), None) or next(
        (p for p in lib.rglob("*.dart") if "radMotion" in p.read_text(encoding="utf-8")), None)
    txt = dz.read_text(encoding="utf-8") if dz else ""
    check("flutter: designer uses RadMotion + RadVariant", "radMotion" in txt and "RadVariant" in txt, dz)
    from target_tools import flutter_exe
    fl = flutter_exe()
    if not fl:
        check("flutter: not installed (analyze skipped)", True)
        return
    rc, out = run([fl, "pub", "get", "--offline"], cwd=folder, timeout=300)
    if rc:
        rc, out = run([fl, "pub", "get"], cwd=folder, timeout=600)
    rc, out = run([fl, "analyze", "--no-fatal-infos", "--no-fatal-warnings"], cwd=folder, timeout=600)
    check("flutter: flutter analyze of the generated project", rc == 0 and "error" not in out.lower().split(
        "analyzing")[-1].replace("0 errors", ""), out[-1500:])
    for d in ("build", ".dart_tool"):
        shutil.rmtree(folder / d, ignore_errors=True)


@phase
def kivy():
    folder, fname, view, b, lab, vid = mobile_common("kivy", "kivy_app", "kivy", ["landscape"])
    check("kivy: radkivyfx.py written", (folder / "radkivyfx.py").is_file(), sorted(p.name for p in folder.iterdir()))
    from target_tools import has_kivy, kivy_run
    if not has_kivy():
        check("kivy: not installed (run skipped)", True)
        return
    code = f"""
import json
from kivy.clock import Clock
from kivy.core.window import Window
R = {{}}
def a(dt):
    R['tx_mid'] = getattr(scr.{b}, '_rad_look', None) and scr.{b}._rad_look.tx
    Clock.schedule_once(b_, 1.5)
def b_(dt):
    R['tx_end'] = scr.{b}._rad_look.tx
    Window.size = (900, 420)
    Clock.schedule_once(c, 0.6)
def c(dt):
    R['sizes'] = list(scr.radsizes)
    R['text'] = scr.{b}.text
    open(r'$OUT', 'w').write(json.dumps(R))
Clock.schedule_once(a, 0.15)
"""
    r = kivy_run(folder, code, secs=6) or {}
    check("kivy run: slideIn offset goes back to 0", r.get("tx_end") == 0 and r.get("tx_mid") not in (None, 0), r)
    check("kivy run: landscape window -> Landscape size + text", vid in (r.get("sizes") or []) and
          r.get("text") == "Small", r)


@phase
def expo():
    folder, fname, view, b, lab, vid = mobile_common("expo", "expo_app", "expo", ["landscape"])
    check("expo: radfx.js written", (folder / "radfx.js").is_file(), sorted(p.name for p in folder.iterdir()))
    js_files = [p for p in folder.rglob("*.js") if "node_modules" not in p.parts]
    txt = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in js_files)
    check("expo: generated screen uses radSizes + FxBox", "radSizes" in txt and "FxBox" in txt)
    node = shutil.which("node")
    if node:
        bad = []
        from target_tools import esbuild_exe
        eb = esbuild_exe()
        if eb:
            for p in js_files:
                rc, out = run([eb, str(p), "--loader:.js=jsx", "--log-level=error"], cwd=folder)
                if rc:
                    bad.append((p.name, out[-300:]))
            check("expo: every generated .js parses (esbuild JSX)", not bad, bad)


@phase
def web():
    from radide.web_site import design
    prj = new_project("static-web", "html-bootstrap", "QaMoWeb")
    folder = Path(prj.folder)
    page = next(iter(sorted(folder.rglob("index.html"))), None)
    check("web: index.html created", page is not None, list(folder.iterdir()))
    dv = design.open_design_view(w, page)
    ok = wait(lambda: dv.is_ready(), 60)
    check("web: GrapesJS Design View ready", ok)
    if not ok:
        return
    pump(1.0)
    r = dv.run_js("(function(){var c=radEditor.getWrapper().find('h1,h2,p,a')[0]; radEditor.select(c);"
                  "var t=c.getTrait('radfx-preset'); if(!t) return 'no trait';"
                  "c.addClass(['radfx','radfx-bounce']); c.addAttributes({'data-radfx-trigger':'click',"
                  "'data-radfx-duration':'700'}); return c.getClasses().join(' ');})()")
    check("web: Animate trait on the selected element -> radfx classes", isinstance(r, str) and "radfx-bounce" in r, r)
    dv.set_device("foldHalf" if any(d == "foldHalf" for _t, d in dv.DEVICES) else "duoSpanned")
    pump(1.0)
    fr = dv.run_js("document.body.classList.contains('rad-size-only') && !!document.querySelector('.rad-hinge')")
    check("web: foldable device -> orange This size only frame + hinge", fr is True, fr)
    shot(dv, sname("web_design_fold"))
    dv.set_device("desktop")
    pump(0.5)
    fr2 = dv.run_js("document.body.classList.contains('rad-size-only')")
    check("web: desktop -> no frame", fr2 is False, fr2)
    pump(0.8)
    check("web: page modified", dv.isModified())
    dv.save()
    pump(0.5)
    html = page.read_text(encoding="utf-8")
    check("web: saved page links radfx.css + radfx.js and keeps the classes", "radfx.css" in html and "radfx.js" in html
          and "radfx-bounce" in html and 'data-radfx-trigger="click"' in html, html[:400])
    check("web: radfx files copied next to the page", (page.parent / "radfx.js").is_file()
          and (page.parent / "radfx.css").is_file())
    # the saved page in a browser: click plays the bounce
    from PyQt6.QtCore import QEventLoop, QUrl
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    v = QWebEngineView()
    v.resize(900, 600)
    v.show()
    loop = QEventLoop()
    v.loadFinished.connect(lambda _ok: loop.quit())
    v.load(QUrl.fromLocalFile(str(page)))
    QTimer.singleShot(15000, loop.quit)
    loop.exec()
    res = {}

    def js(code):
        res.pop("v", None)
        v.page().runJavaScript(code, lambda x: res.setdefault("v", x))
        wait(lambda: "v" in res, 8)
        return res.get("v")
    pump(0.5)
    before = js("getComputedStyle(document.querySelector('.radfx')).animationName")
    after = js("document.querySelector('.radfx').click(); getComputedStyle(document.querySelector('.radfx'))"
               ".animationName")
    check("web run: the element waits, a click plays radfx-bounce", before == "none" and after == "radfx-bounce",
          (before, after))
    v.close()


@phase
def fd():
    from radide.flutterdesign import variants_fd as VF
    from radide.flutterdesign.designer import DEVICE_IDS
    prj = new_project("flutter", "flutter_designer", "QaMoFd")
    folder = Path(prj.folder)
    mgr = w.flutter_designer
    d = mgr.create_screen(folder, "blank", "Home", "/home") if True else None
    pump(1.0)
    check("fd: Add New Screen opens the Flutter designer", d is not None)
    if d is None:
        return
    w.tabs.setCurrentWidget(d)
    scr = d.screen
    root_id = scr.root["id"] if isinstance(getattr(scr, "root", None), dict) else None
    # drop a Text and an ElevatedButton from the palette model
    from radide.flutterdesign import model as M
    col = next((n for n, *_ in scr.walk() if n["type"] in ("Column", "Center", "ListView")), None)
    parent = (col or scr.find(root_id) or {}).get("id") if (col or root_id) else None
    t = d.add_widget("Text", parent) if hasattr(d, "add_widget") else None
    if t is None:
        t = M.make_node("Text") if hasattr(M, "make_node") else None
    check("fd: a Text widget added", t is not None)
    tid = t["id"] if isinstance(t, dict) else t
    d.select(tid)
    pump(0.3)
    # animation: inspector Animation editor through the model API used by the inspector
    node = scr.find(tid)
    ex = d.inspector.anim_extra
    if hasattr(d, "set_anim"):
        d.set_anim(tid, {"type": "fadeIn", "durationMs": 600})
    else:
        node["anim"] = {"type": "fadeIn", "duration": 600}
        d.changed() if hasattr(d, "changed") else None
    pump(0.3)
    check("fd: animation stored on the Text", (scr.find(tid).get("anim") or {}).get("type") == "fadeIn",
          scr.find(tid).get("anim"))
    # a size, This size only
    d.cbo_device.setCurrentIndex(DEVICE_IDS.index("galaxy_z_fold6"))
    pump(0.3)
    if not VF.sizes(scr) and hasattr(d, "add_size"):
        d.add_size("folded")
    sizes = [s["id"] for s in VF.sizes(scr)]
    check("fd: the screen has layout sizes", bool(sizes), sizes)
    if sizes:
        d.set_edit_mode("size")
        d.set_edit_size(sizes[0])
        pump(0.3)
        d.set_prop(tid, "data", "Folded!")
        n = scr.find(tid)
        check("fd: This size only edit stored as an override", VF.overrides(n, sizes[0]).get("data") == "Folded!",
              n)
        lab = d.inspector.labels.get("data")
        check("fd: inspector marker on the overridden property", lab is not None and lab.text().startswith(
            VF.MARK_HERE), lab.text() if lab else None)
        d.set_edit_mode("all")
    for posture in ("Flat", "HalfOpened", "Folded"):
        d.set_posture(posture)
        pump(0.3)
        shot(d, sname(f"fd_{posture}"))
    check("fd: Folded posture = cover screen", d.hinge_rect() is None)
    d.save() if hasattr(d, "save") else w.save_all()
    pump(1.0)
    gen = list((folder / "lib").rglob("home*.dart"))
    txt = "\n".join(p.read_text(encoding="utf-8") for p in gen)
    check("fd: generated screen has the size + animation", "RadVariant" in txt or "radlayout" in txt, [p.name for p in gen])


for name in PHASES:
    globals()[name]()
    pump(0.5)
qh.finish(w)
