"""Performance harness for RAD IDE's classic forms designer (WinForms-style) and its surroundings.

Measures the user-visible operations with time.perf_counter (median / p95 of several runs), records the
longest UI freeze with a 5 ms QTimer heartbeat, settles the event loop after each action (deferred
QTimer work counts) and writes a cProfile top list for every operation slower than its budget
(interactive action > 100 ms, drag frame > 16 ms, start-up).

Run:
  .venv\\Scripts\\python samples\\Tests\\Performance\\Designer\\perf_designer.py [--runs 5] [--tag before]
         [--real] [--only startup,designer,drag,props,edit,view,monaco,run,codegen] [--profile]

  --real     use the normal Windows platform (real, visible windows; no screenshots) instead of offscreen
  --profile  write cProfile reports (top functions by cumulative time) for the slow operations
Results: <out>/results_<tag>_<platform>.json, a text table on stdout, profiles in <out>/prof_<tag>_<platform>/.
<out> defaults to %TEMP%\\radide-perf-designer (override: PERF_OUT).
Uses QSettings "RADIDE-TEST-PERF" (cleared before / after), RADIDE_NO_BROWSER=1, widget.grab only; closes
only the processes it starts.
"""
from __future__ import annotations

import argparse
import cProfile
import io
import json
import os
import pstats
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("--runs", type=int, default=5)
ap.add_argument("--tag", default="run")
ap.add_argument("--real", action="store_true")
ap.add_argument("--only", default="")
ap.add_argument("--profile", action="store_true")
ap.add_argument("--controls", type=int, default=400)
ap.add_argument("--child-startup", default="")      # internal: one cold start, results to this file
ap.add_argument("--child-profile", default="")
ARGS = ap.parse_args()

if not ARGS.real:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing")
os.environ["RADIDE_NO_BROWSER"] = "1"
# RADIDE_CODE_ROOT: measure another copy of the radide package (e.g. a baseline before a change) with the same
# samples; default = this repository
CODE_ROOT = Path(os.environ.get("RADIDE_CODE_ROOT") or ROOT)
sys.path.insert(0, str(CODE_ROOT))
PLATFORM = "real" if ARGS.real else "offscreen"
OUT = Path(os.environ.get("PERF_OUT") or Path(tempfile.gettempdir()) / "radide-perf-designer")
ORG = "RADIDE-TEST-PERF"


# ===================================================================== child: one cold start
def child_startup(result_file: str, prof_file: str) -> None:
    t0 = time.perf_counter()
    pr = cProfile.Profile() if prof_file else None
    if pr:
        pr.enable()
    marks = {}
    import PyQt6.QtWebEngineWidgets  # noqa: F401
    from PyQt6.QtCore import QCoreApplication, QSettings
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QApplication
    marks["import_qt"] = time.perf_counter() - t0
    QCoreApplication.setOrganizationName(ORG)
    QCoreApplication.setApplicationName(ORG)
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    marks["qapp"] = time.perf_counter() - t0
    t = time.perf_counter()
    import radide.controls  # noqa: F401  (loads the built-in component packages)
    from radide.components import REGISTRY
    REGISTRY.ensure_loaded()
    marks["components_registry"] = time.perf_counter() - t
    t = time.perf_counter()
    from radide.app import MainWindow
    marks["import_app"] = time.perf_counter() - t
    t = time.perf_counter()
    w = MainWindow()
    marks["mainwindow_init"] = time.perf_counter() - t
    t = time.perf_counter()
    w.resize(1400, 900)
    w.show()
    app.processEvents()
    marks["show"] = time.perf_counter() - t
    marks["usable"] = time.perf_counter() - t0          # window shown, first events processed
    # settle: deferred start-up work (QTimer.singleShot) until the loop is quiet for 300 ms
    t = time.perf_counter()
    last_busy = t
    while time.perf_counter() - last_busy < 0.3 and time.perf_counter() - t < 20:
        a = time.perf_counter()
        app.processEvents()
        if time.perf_counter() - a > 0.002:
            last_busy = time.perf_counter()
        else:
            time.sleep(0.002)
    marks["settled"] = last_busy - t0
    if pr:
        pr.disable()
        pr.dump_stats(prof_file)
    Path(result_file).write_text(json.dumps(marks), encoding="utf-8")
    try:                    # the processes this start-up launched (extension host ...)
        import psutil
        for c in psutil.Process().children(recursive=True):
            try:
                c.kill()
            except psutil.Error:
                pass
    except Exception:  # noqa: BLE001
        pass
    QSettings().clear()
    sys.stdout.flush()
    os._exit(0)


if ARGS.child_startup:
    child_startup(ARGS.child_startup, ARGS.child_profile)

# ===================================================================== main process
import PyQt6.QtWebEngineWidgets  # noqa: E402,F401
from PyQt6.QtCore import QCoreApplication, QEvent, QPoint, QPointF, QSettings, Qt, QTimer  # noqa: E402
from PyQt6.QtGui import QFont, QMouseEvent  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName(ORG)
QCoreApplication.setApplicationName(ORG)
app = QApplication(sys.argv[:1])
app.setStyle("Fusion")
app.setFont(QFont("Segoe UI", 9))
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))

ONLY = {s.strip() for s in ARGS.only.split(",") if s.strip()}
RESULTS: dict[str, dict] = {}
PROF_DIR = OUT / f"prof_{ARGS.tag}_{PLATFORM}"


def want(group: str) -> bool:
    return not ONLY or group in ONLY


# ------------------------------------------------------------------ heartbeat / settle
class Heartbeat:
    """A 5 ms timer; the longest gap between two ticks = the longest time the UI thread was blocked."""

    def __init__(self):
        self.timer = QTimer()
        self.timer.setInterval(5)
        self.timer.timeout.connect(self._tick)
        self.last = None
        self.max_gap = 0.0

    def _tick(self):
        now = time.perf_counter()
        if self.last is not None:
            self.max_gap = max(self.max_gap, now - self.last)
        self.last = now

    def start(self):
        self.last = time.perf_counter()
        self.max_gap = 0.0
        self.timer.start()

    def stop(self) -> float:
        self.timer.stop()
        if self.last is not None:
            self.max_gap = max(self.max_gap, time.perf_counter() - self.last)
        return self.max_gap


HB = Heartbeat()


def settle(quiet: float = 0.08, cap: float = 5.0) -> float:
    """Process events until nothing runs for *quiet* seconds; returns the end of the last busy pass."""
    t = time.perf_counter()
    last_busy = t
    while time.perf_counter() - last_busy < quiet and time.perf_counter() - t < cap:
        a = time.perf_counter()
        app.processEvents()
        if time.perf_counter() - a > 0.002:
            last_busy = time.perf_counter()
        else:
            time.sleep(0.001)
    return last_busy


def pump(n=2):
    for _ in range(n):
        app.processEvents()


def pct(values, q):
    v = sorted(values)
    if not v:
        return 0.0
    k = (len(v) - 1) * q
    lo, hi = int(k), min(len(v) - 1, int(k) + 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def record(name: str, samples_ms: list, kind: str, freeze_ms: list | None = None, note: str = "",
           total_ms: list | None = None) -> dict:
    r = {"median": round(statistics.median(samples_ms), 2), "p95": round(pct(samples_ms, 0.95), 2),
         "min": round(min(samples_ms), 2), "n": len(samples_ms), "kind": kind}
    if freeze_ms:
        r["freeze_p95"] = round(pct(freeze_ms, 0.95), 2)
    if total_ms:
        r["settled_median"] = round(statistics.median(total_ms), 2)
    if note:
        r["note"] = note
    RESULTS[name] = r
    budget = {"interactive": 100, "frame": 16, "startup": 1500, "open": 300, "background": 1e9}.get(kind, 100)
    flag = "  SLOW" if r["median"] > budget else ""
    extra = f" settled {r['settled_median']:8.1f}" if total_ms else ""
    print(f"{name:42s} median {r['median']:9.2f} ms  p95 {r['p95']:9.2f}{extra}  [{kind}]{flag}", flush=True)
    return r


def profile(name: str, fn, setup=None):
    if not ARGS.profile:
        return
    PROF_DIR.mkdir(parents=True, exist_ok=True)
    if setup:
        setup()
    pr = cProfile.Profile()
    pr.enable()
    fn()
    settle()
    pr.disable()
    s = io.StringIO()
    st = pstats.Stats(pr, stream=s)
    st.sort_stats("cumulative").print_stats(35)
    st.sort_stats("tottime").print_stats(20)
    safe = "".join(ch if ch.isalnum() or ch in " .,()%+-_" else "_" for ch in name)
    (PROF_DIR / f"{safe}.txt").write_text(s.getvalue(), encoding="utf-8")


def measure(name: str, fn, runs: int | None = None, setup=None, kind="interactive", teardown=None,
            per: int = 1, prof=True):
    try:
        return _measure(name, fn, runs, setup, kind, teardown, per, prof)
    except Exception:  # noqa: BLE001 - one broken measurement must not end the run
        import traceback
        print(f"{name:42s} FAILED", flush=True)
        traceback.print_exc()
        sys.stderr.flush()
        return None


def _measure(name: str, fn, runs: int | None = None, setup=None, kind="interactive", teardown=None,
             per: int = 1, prof=True):
    """Time fn() (synchronous part) and fn() + settle (deferred work); *per*: fn does that many steps
    (a drag of 20 mouse moves -> the time per move)."""
    runs = runs or ARGS.runs
    sync, total, freeze = [], [], []
    for _ in range(runs):
        if setup:
            setup()
        settle(0.03)
        HB.start()
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        end = settle()
        freeze.append(HB.stop() * 1000)
        sync.append((t1 - t0) * 1000 / per)
        total.append((max(end, t1) - t0) * 1000 / per)
        if teardown:
            teardown()
    r = record(name, sync, kind, freeze, total_ms=total)
    budget = {"frame": 16, "open": 300}.get(kind, 100)
    if prof and (r["median"] > budget or r["settled_median"] > budget):
        profile(name, fn, setup)
        if teardown:
            teardown()
    return r


# ------------------------------------------------------------------ input helpers (as test_vs_parity.py)
L = Qt.MouseButton.LeftButton
NoMod = Qt.KeyboardModifier.NoModifier


def mouse(w, kind, pos, mods=NoMod, button=L, pump_after=True):
    t = {"press": QEvent.Type.MouseButtonPress, "move": QEvent.Type.MouseMove,
         "release": QEvent.Type.MouseButtonRelease}[kind]
    btn = Qt.MouseButton.NoButton if kind == "move" else button
    btns = button if kind in ("press", "move") else Qt.MouseButton.NoButton
    if kind == "move" and pos is not None and getattr(mouse, "hover", False):
        btns = Qt.MouseButton.NoButton
    p = QPointF(QPoint(*pos))
    ev = QMouseEvent(t, p, w.mapToGlobal(p), btn, btns, mods)
    QApplication.sendEvent(w, ev)
    if pump_after:
        app.processEvents()      # the repaint of that step (offscreen: the backing store)


# ------------------------------------------------------------------ test projects
def big_form_dict(n_target: int) -> dict:
    """A form with ~n_target controls: menu, tool strip, timer, panels with nested group boxes, a TabControl
    with 3 pages (group boxes inside) and a grid of loose controls; a ListBox with 1000 Items."""
    from radide.model import Form
    f = Form()
    f.props.update({"Name": "BigForm", "Text": "Big form", "Width": 1500, "Height": 1100})
    menu = f.add("MenuStrip", 0, 0)
    menu.props["Items"] = [{"Name": f"mnuTop{i}", "Text": f"Menu{i}",
                            "Items": [{"Name": f"mnuItem{i}_{j}", "Text": f"Item {j}"} for j in range(8)]}
                           for i in range(6)]
    tool = f.add("ToolStrip", 0, 0)
    tool.props["Items"] = [{"Name": f"tsb{i}", "Text": f"Tool{i}"} for i in range(8)]
    f.add("Timer", 0, 0)
    leaf = ["Button", "Label", "TextBox", "CheckBox", "ComboBox", "RadioButton", "NumericUpDown", "ProgressBar"]
    k = 0

    def leafc(parent, x, y):
        nonlocal k
        t = leaf[k % len(leaf)]
        k += 1
        c = f.add(t, x, y, parent)
        c.props["Width"], c.props["Height"] = 90, 24
        return c
    # 8 panels, each: 6 controls + a group box with 6 controls
    for p in range(8):
        pn = f.add("Panel", 8 + (p % 4) * 300, 8 + (p // 4) * 210, "")
        pn.props["Width"], pn.props["Height"] = 290, 200
        for i in range(6):
            leafc(pn.name, 8 + (i % 2) * 100, 8 + (i // 2) * 30)
        gb = f.add("GroupBox", 8, 100, pn.name)
        gb.props["Width"], gb.props["Height"] = 270, 92
        for i in range(6):
            leafc(gb.name, 8 + (i % 2) * 130, 18 + (i // 2) * 24)
    # TabControl: 3 pages x (12 controls + a group box with 8)
    tc = f.add("TabControl", 8, 440, "")
    tc.props["Width"], tc.props["Height"] = 600, 400
    tc.props["TabPages"] = "General;Details;Notes"
    for page in range(3):
        for i in range(12):
            c = leafc(tc.name, 8 + (i % 3) * 120, 8 + (i // 3) * 30)
            c.props["TabPage"] = page
        gb = f.add("GroupBox", 8, 140, tc.name)
        gb.props["Width"], gb.props["Height"] = 560, 200
        gb.props["TabPage"] = page
        for i in range(8):
            leafc(gb.name, 8 + (i % 4) * 130, 20 + (i // 4) * 30)
    lb = f.add("ListBox", 620, 440, "")
    lb.props["Width"], lb.props["Height"] = 200, 300
    lb.props["Items"] = ";".join(f"Item {i}" for i in range(1000))
    # loose controls on the form until n_target
    i = 0
    while len(f.controls) < n_target:
        leafc("", 840 + (i % 6) * 105, 440 + (i // 6) * 28)
        i += 1
    return f.to_dict()


def make_projects():
    shutil.rmtree(OUT / "projects", ignore_errors=True)
    (OUT / "projects").mkdir(parents=True, exist_ok=True)
    from radide.languages import get_plugin
    from radide.model import Form, Project
    out = {}
    for key, src in (("py", "samples/Tests/Languages/PythonTk_Form"), ("vb", "samples/Tests/Languages/VB_Form")):
        dst = OUT / "projects" / key
        shutil.copytree(ROOT / src, dst)
        proj = Project.load(dst)
        fp = get_plugin(proj.language)
        d = big_form_dict(ARGS.controls)
        form = Form.from_dict(d)
        form.save(dst / "BigForm.form")
        (dst / fp.code_file("BigForm")).write_text(fp.new_code(form, False), encoding="utf-8")
        (dst / fp.designer_file("BigForm")).write_text(fp.generate_designer(form, ""), encoding="utf-8")
        proj.forms.append("BigForm")
        proj.save()
        out[key] = dst
    # a 5000-line Python file for the code editor
    lines = []
    for i in range(1000):
        lines += [f"def func_{i}(a, b=1):", f"    '''Function {i}.'''", f"    x = a + b * {i}",
                  "    return x", ""]
    (out["py"] / "big5k.py").write_text("\n".join(lines), encoding="utf-8")
    return out


# ===================================================================== phases
def phase_startup():
    print("== start-up (separate process each run)", flush=True)
    vals: dict[str, list] = {}
    walls = []
    for i in range(max(3, ARGS.runs // 2 + 1)):
        res = OUT / f"startup_{i}.json"
        res.unlink(missing_ok=True)
        prof = str(PROF_DIR / "startup_cold.prof") if (ARGS.profile and i == 0) else ""
        if prof:
            PROF_DIR.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        t0 = time.perf_counter()
        p = subprocess.Popen([sys.executable, str(Path(__file__)), "--child-startup", str(res),
                              "--child-profile", prof] + (["--real"] if ARGS.real else []),
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        while not res.exists() and p.poll() is None and time.perf_counter() - t0 < 180:
            time.sleep(0.05)
        wall = time.perf_counter() - t0
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            p.kill()
        if not res.exists():
            print("   start-up child failed", flush=True)
            continue
        time.sleep(0.2)
        m = json.loads(res.read_text(encoding="utf-8"))
        walls.append(wall * 1000)
        for k, v in m.items():
            vals.setdefault(k, []).append(v * 1000)
    if walls:
        record("startup.process_wall_to_settled", walls, "startup",
               note="Popen -> child wrote its results (interpreter start + imports + window + settled)")
    for k in ("import_qt", "qapp", "components_registry", "import_app", "mainwindow_init", "show", "usable",
              "settled"):
        if k in vals:
            record(f"startup.{k}", vals[k], "startup" if k in ("usable", "settled") else "background")
    if ARGS.profile and (PROF_DIR / "startup_cold.prof").exists():
        s = io.StringIO()
        st = pstats.Stats(str(PROF_DIR / "startup_cold.prof"), stream=s)
        st.sort_stats("cumulative").print_stats(60)
        st.sort_stats("tottime").print_stats(30)
        (PROF_DIR / "startup_cold.txt").write_text(s.getvalue(), encoding="utf-8")


class Session:
    win = None


def ide():
    if Session.win is None:
        from radide.app import MainWindow
        w = MainWindow()
        w.resize(1600, 1000)
        w.show()
        settle(0.3)
        Session.win = w
    return Session.win


def close_form_views(w, names):
    """Close the designer / code tabs of *names* and forget their documents (a fresh open next time)."""
    for n in names:
        for d in (w.designers, w.codeviews):
            v = d.pop(n, None)
            if v is not None:
                i = w.tabs.indexOf(v)
                if i >= 0:
                    w.tabs.removeTab(i)
                v.setParent(None)
                v.deleteLater()
        doc = w.docs.pop(n, None)
        if doc is not None:
            doc.deleteLater()
    w.properties.set_document(None, None)
    settle(0.03)


def phase_designer(projects):
    print("== designer (IDE, in-process)", flush=True)
    w = ide()
    py = projects["py"]

    def open_proj():
        w.open_project(py, ask=False)
    measure("project.open (PythonTk, 2 forms)", open_proj, runs=max(3, ARGS.runs // 2), kind="open")

    def open_small():
        w.open_designer("Form1")

    def open_big():
        w.open_designer("BigForm")
    measure("designer.open small (Form1)", open_small, setup=lambda: close_form_views(w, ["Form1"]), kind="open")
    measure(f"designer.open big ({ARGS.controls} controls)", open_big,
            setup=lambda: close_form_views(w, ["BigForm"]), kind="open")
    w.open_designer("Form1")
    w.open_designer("BigForm")
    settle()
    d = w._current_designer()
    doc, ov, form = d.doc, d.overlay, d.doc.form
    print(f"   big form: {len(form.controls)} controls", flush=True)

    # ------------------------------------------------ selection
    loose = [c for c in form.controls if not c.parent and c.type == "Button"]
    loose_all = [c for c in form.controls if not c.parent and not c.ctype.nonvisual
                 and not c.ctype.container and c.type != "ListBox"]
    # an Undo rebuilds every Control object from its snapshot: look the controls up by name each time
    tgt_name = loose[0].name
    targets_names = [c.name for c in loose[:8]]
    multi_names = [c.name for c in loose_all[:50]]

    def T():
        return doc.form.find(tgt_name)

    def M():
        return [doc.form.find(n) for n in multi_names]

    def at(c, dx=5, dy=5):
        r = ov.abs_rect(c)
        return (r.x() + dx, r.y() + dy)
    state = {"i": 0}

    def click_select():
        c = doc.form.find(targets_names[state["i"] % len(targets_names)])
        state["i"] += 1
        mouse(ov, "press", at(c), pump_after=False)
        mouse(ov, "release", at(c), pump_after=False)
    w.properties.tabs.setCurrentIndex(0)
    measure("select.click control (Properties tab)", click_select)
    w.properties.tabs.setCurrentIndex(1)
    measure("select.click control (Events tab)", click_select)
    w.properties.tabs.setCurrentIndex(0)

    def select_form():
        doc.select(None)
    measure("select.form (Esc / click on the form)", select_form, setup=lambda: doc.select(T()))
    measure("select.multi 50 (rubber band result)", lambda: doc.select_many(M()), setup=lambda: doc.select(None))

    def tab_select():
        c = doc.form.find(targets_names[state["i"] % len(targets_names)])
        state["i"] += 1
        w.doc_outline.setCurrentItem(w.doc_outline.items.get(c.name))
    if hasattr(w, "doc_outline"):
        w.dock_outline.raise_()             # the outline tab shown (it shares the column with Solution Explorer)
        settle()
        measure("select.from Document Outline", tab_select)
        measure("edit.undo (property, Document Outline shown)", lambda: doc.undo(),
                setup=lambda: (doc.select(T()), settle(0.02), w.properties._set("BackColor", "#123456"),
                               settle(0.02)))
        w.dock_solution.raise_()
        settle()

    # ------------------------------------------------ hover
    def hover():
        mouse.hover = True
        for i in range(20):
            mouse(ov, "move", (850 + i * 13, 450 + (i % 5) * 20), pump_after=False)
            app.processEvents()
        mouse.hover = False
    measure("hover.mouse move over the form (per event)", hover, per=20, kind="frame")

    # ------------------------------------------------ drags
    def drag_steps(c_from, steps=20, dx=3, dy=2):
        a = at(c_from)
        mouse(ov, "press", a)
        for i in range(1, steps + 1):
            mouse(ov, "move", (a[0] + i * dx, a[1] + i * dy))
        return a, (a[0] + steps * dx, a[1] + steps * dy)

    def sel_one():
        doc.select(T())
        settle(0.02)

    def drag_one():
        a, b = drag_steps(T())
        state["end"] = b

    def release():
        mouse(ov, "release", state["end"])

    def undo_drag():
        release()
        doc.undo()
        settle(0.02)
    measure("drag.move 1 control (per mouse move)", drag_one, setup=sel_one, teardown=undo_drag, per=20,
            kind="frame")

    def drag_one_release():
        mouse(ov, "release", state["end"])

    def setup_rel1():
        sel_one()
        drag_one()
        settle(0.02)
    measure("drag.release 1 control", drag_one_release, setup=setup_rel1,
            teardown=lambda: (doc.undo(), settle(0.02)))

    def sel_group():
        m = M()
        doc.select_many(m[1:] + [m[0]])
        settle(0.02)

    def drag_group():
        a, b = drag_steps(M()[0])
        state["end"] = b
    measure("drag.move group of 50 (per mouse move)", drag_group, setup=sel_group, teardown=undo_drag, per=20,
            kind="frame")

    def setup_relg():
        sel_group()
        drag_group()
        settle(0.02)
    measure("drag.release group of 50", drag_one_release, setup=setup_relg,
            teardown=lambda: (doc.undo(), settle(0.02)))

    def resize_drag():
        r = ov.abs_rect(T())
        a = (r.right(), r.bottom())
        mouse(ov, "press", a)
        for i in range(1, 21):
            mouse(ov, "move", (a[0] + i * 3, a[1] + i * 2))
        state["end"] = (a[0] + 60, a[1] + 40)
    measure("drag.resize handle (per mouse move)", resize_drag, setup=sel_one, teardown=undo_drag, per=20,
            kind="frame")

    def band():
        a = (842, 1000)
        mouse(ov, "press", a)
        for i in range(1, 21):
            mouse(ov, "move", (a[0] - i * 1, a[1] - i * 25))
        state["end"] = (a[0] - 20, a[1] - 500)

    def band_release():
        mouse(ov, "release", state["end"])
        settle(0.02)
    measure("drag.rubber band (per mouse move)", band, setup=lambda: doc.select(None), teardown=band_release,
            per=20, kind="frame")

    def setup_band():
        doc.select(None)
        band()
    measure("drag.rubber band release (selects ~50)", band_release, setup=setup_band)

    def nudge(n=20, key=Qt.Key.Key_Right):
        ov.setFocus()
        for _ in range(n):
            QTest.keyClick(ov, key)
            app.processEvents()
    def nudge_back():           # back where they were (20 undos cost minutes on a slow build)
        nudge(20, Qt.Key.Key_Left)
        settle(0.02)
    measure("key.arrow nudge 1 control (per key)", nudge, setup=sel_one, per=20, teardown=nudge_back)
    measure("key.arrow nudge 50 controls (per key)", nudge, setup=sel_group, per=20, teardown=nudge_back)

    # ------------------------------------------------ properties
    pp = w.properties
    vals = {"n": 0}

    def set_text():
        vals["n"] += 1
        pp._set("Text", f"Caption {vals['n']}")
    measure("prop.Text (single)", set_text, setup=sel_one)

    def set_font():
        vals["n"] += 1
        pp._set("Font", "Arial" if vals["n"] % 2 else "Tahoma")
    measure("prop.Font (single)", set_font, setup=sel_one)

    def set_back():
        vals["n"] += 1
        pp._set("BackColor", "#FF%04X" % (vals["n"] * 97 % 65536))
    measure("prop.BackColor (single)", set_back, setup=sel_one)
    measure("prop.BackColor (50 selected)", set_back, setup=sel_group)

    def form_text():
        vals["n"] += 1
        doc.set_prop(None, "Text", f"Form caption {vals['n']}")
    measure("prop.form Text", form_text, setup=lambda: doc.select(None))

    def undo():
        doc.undo()

    def redo():
        doc.redo()
    measure("edit.undo (property)", undo, setup=lambda: (sel_one(), set_back(), settle(0.02)))
    measure("edit.redo (property)", redo, setup=lambda: (sel_one(), set_back(), settle(0.02), doc.undo(),
                                                          settle(0.02)))
    lb_name = next(c for c in form.controls if c.type == "ListBox").name

    def LB():
        return doc.form.find(lb_name)
    measure("select.ListBox with 1000 Items", lambda: doc.select(LB()), setup=lambda: doc.select(T()))

    def items_edit():
        vals["n"] += 1
        pp._set("Items", LB().props["Items"] + f";x{vals['n']}")
    measure("prop.Items (1000 lines)", items_edit, setup=lambda: (doc.select(LB()), settle(0.02)))

    # ------------------------------------------------ add / copy / paste / delete
    def add_button():
        d.add_default("Button")
    measure("edit.add control (Toolbox double-click)", add_button, setup=sel_one,
            teardown=lambda: (doc.undo(), settle(0.02)))

    def copy50():
        doc.copy()
    measure("edit.copy 50", copy50, setup=sel_group)

    def paste50():
        doc.paste()
    measure("edit.paste 50", paste50, setup=lambda: (sel_group(), doc.copy(), doc.select(None), settle(0.02)),
            teardown=lambda: (doc.undo(), settle(0.02)))

    def delete50():
        doc.remove_controls(list(doc.selection))
    measure("edit.delete 50", delete50, setup=sel_group, teardown=lambda: (doc.undo(), settle(0.02)))
    measure("edit.undo (delete 50)", undo, setup=lambda: (sel_group(), delete50(), settle(0.02)))

    # rebind after undos (controls were rebuilt from snapshots)
    form = doc.form

    # ------------------------------------------------ zoom / view switches / tabs / save
    measure("view.zoom 150%", lambda: d.set_zoom(1.5), setup=lambda: (d.set_zoom(1.0), settle(0.02)))
    measure("view.zoom back to 100%", lambda: d.set_zoom(1.0), setup=lambda: (d.set_zoom(1.5), settle(0.02)))

    def to_code():
        w.view_code()

    def to_design():
        w.view_designer()
    measure("view.F7 first time (create code view)", to_code,
            setup=lambda: (w.codeviews.pop("BigForm", None) and None, w.open_designer("BigForm"), settle(0.05)),
            runs=3)
    measure("view.F7 Design->Code", to_code, setup=lambda: (w.open_designer("BigForm"), settle(0.05)))
    measure("view.Shift+F7 Code->Design", to_design, setup=lambda: (w.open_code("BigForm"), settle(0.05)))

    def switch_small():
        w.open_designer("Form1")

    def switch_big():
        w.open_designer("BigForm")
    measure("view.switch tab -> small form", switch_small, setup=lambda: (switch_big(), settle(0.02)))
    measure("view.switch tab -> big form", switch_big, setup=lambda: (switch_small(), settle(0.02)))
    switch_big()
    settle()

    def save():
        w.save_all()
    measure("file.save all (big form modified)", save, setup=lambda: (doc.set_modified(True), settle(0.02)))

    # ------------------------------------------------ toolbox
    tb = w.toolbox

    def tb_search():
        for ch in "button":
            tb.search.setText(tb.search.text() + ch)
            app.processEvents()
    measure("toolbox.search typing 6 chars (per char)", tb_search, setup=lambda: tb.search.setText(""), per=6,
            teardown=lambda: tb.search.setText(""))
    measure("toolbox.rebuild", tb.rebuild)
    Session.d = d


def phase_vb6_forms():
    print("== VB6 forms (foreign .vbp projects)", flush=True)
    w = ide()
    folders = [p for p in (ROOT / "samples/VB6/Business").glob("*") if p.is_dir() and list(p.glob("*.vbp"))]
    folders += [p for p in (ROOT / "samples/Tests/VB6Compat").glob("*") if p.is_dir() and list(p.glob("*.frm"))]
    tmp = OUT / "vb6copies"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    opens, forms_n, worst = [], 0, (0, "")
    for src in folders[:6]:
        dst = tmp / src.name
        shutil.copytree(src, dst)
        t0 = time.perf_counter()
        try:
            w.open_project(dst, ask=False)
        except Exception as e:  # noqa: BLE001
            print(f"   {src.name}: open failed {e}", flush=True)
            continue
        settle()
        t_open = (time.perf_counter() - t0) * 1000
        proj = w.project
        names = list(getattr(proj, "forms", []) or [])
        for n in names:
            t0 = time.perf_counter()
            try:
                w.open_designer(n)
            except Exception as e:  # noqa: BLE001
                print(f"   {src.name}/{n}: designer failed {e}", flush=True)
                continue
            end = settle()
            ms = (end - t0) * 1000
            opens.append(ms)
            forms_n += 1
            dv = w.designers.get(n)
            cnt = len(dv.doc.form.controls) if dv is not None else 0
            if ms > worst[0]:
                worst = (ms, f"{src.name}/{n} ({cnt} controls)")
        print(f"   {src.name}: project open {t_open:.0f} ms, {len(names)} forms", flush=True)
    if opens:
        record("vb6.designer open (each .frm)", opens, "open", note=f"{forms_n} forms; slowest {worst[1]}")


def phase_codegen(projects):
    print("== code generation (big form)", flush=True)
    from radide.languages import get_plugin
    from radide.model import Form
    form = Form.load(projects["py"] / "BigForm.form")
    for pid in ("python-tk", "vb-basic", "python-qt", "csharp-bridge"):
        try:
            fp = get_plugin(pid)
        except Exception:  # noqa: BLE001
            continue
        try:
            fp.generate_designer(form, "")
        except Exception as e:  # noqa: BLE001
            print(f"   {pid}: {e}", flush=True)
            continue
        measure(f"codegen.{pid} generate_designer", lambda fp=fp: fp.generate_designer(form, ""), kind="interactive")
    measure("model.snapshot (undo checkpoint)", form.snapshot)
    snap = form.snapshot()
    measure("model.restore snapshot", lambda: Form.from_dict(json.loads(snap)))


def phase_monaco(projects):
    print("== Monaco code editor", flush=True)
    from radide.editor import make_editor, use_monaco
    from radide.languages import get_plugin
    if not use_monaco():
        print("   Monaco not available", flush=True)
        return
    path = projects["py"] / "big5k.py"
    text = path.read_text(encoding="utf-8")
    fp = get_plugin("python-tk")
    holder = {}

    def open_editor():
        ed = make_editor(fp, path)
        ed.resize(1000, 700)
        ed.show()
        ed.setText(text)
        holder["ed"] = ed
        t0 = time.perf_counter()
        while not ed._ready and time.perf_counter() - t0 < 30:
            app.processEvents()
            time.sleep(0.002)
        # wait until the text is really in the model
        done = {}
        ed.page().runJavaScript("window.radEditor ? window.radEditor.getModel().getLineCount() : -1",
                                lambda v: done.setdefault("v", v))
        while "v" not in done and time.perf_counter() - t0 < 30:
            app.processEvents()
            time.sleep(0.001)

    def close_editor():
        ed = holder.pop("ed", None)
        if ed is not None:
            ed.close()
            ed.deleteLater()
            settle(0.05)
    measure("monaco.open 5000-line file (until ready)", open_editor, runs=3, kind="open", teardown=close_editor,
            prof=False)
    open_editor()
    ed = holder["ed"]
    settle(0.3)

    def js(code):
        out = {}
        ed.page().runJavaScript(code, lambda v: out.setdefault("v", v))
        t0 = time.perf_counter()
        while "v" not in out and time.perf_counter() - t0 < 10:
            app.processEvents()
            time.sleep(0.0005)
        return out.get("v")
    js("radEditor.setPosition({lineNumber: 2500, column: 1}); radEditor.focus(); 1")
    got = {"n": 0}
    ed.textEdited.connect(lambda: got.__setitem__("n", got["n"] + 1))

    def keystroke():
        n = got["n"]
        js("radEditor.trigger('keyboard', 'type', {text: 'x'}); 1")
        t0 = time.perf_counter()
        while got["n"] == n and time.perf_counter() - t0 < 5:
            app.processEvents()
            time.sleep(0.0005)
    measure("monaco.keystroke round trip (JS -> Python copy)", keystroke, prof=False)

    def suggest():
        js("radEditor.trigger('keyboard', 'type', {text: '\\nfunc_'}); 1")
        js("radEditor.trigger('kb', 'editor.action.triggerSuggest', {}); 1")
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 5:
            v = js("(document.querySelector('.suggest-widget.visible .monaco-list-row') ? 1 : 0)")
            if v:
                break
            time.sleep(0.005)
        js("radEditor.trigger('kb', 'hideSuggestWidget', {}); 1")
    measure("monaco.IntelliSense list shown (built-in)", suggest, runs=3, prof=False)
    # runJavaScript does not await promises: poll a global instead
    js("""window.__radScroll = null; (async () => { const ed = radEditor; const t = []; let last = performance.now();
        for (let i = 0; i < 60; i++) { ed.setScrollTop(i * 1200); await new Promise(r => requestAnimationFrame(r));
          const now = performance.now(); t.push(now - last); last = now; }
        t.sort((a, b) => a - b); window.__radScroll = JSON.stringify(t); })(); 1""")
    t0 = time.perf_counter()
    res = None
    while time.perf_counter() - t0 < 20:
        res = js("window.__radScroll")
        if res:
            break
        time.sleep(0.02)
    if res:
        frames = json.loads(res)
        record("monaco.scroll 5000 lines (per frame, rAF)", frames, "frame",
               note="offscreen has no vsync: rAF pacing is Chromium's own timer" if not ARGS.real else "")
    close_editor()


def phase_run(projects):
    """F5 of a VB6 (vb-basic) and a Python Tk form project: time until the program's first visible top-level
    window (EnumWindows over the processes the IDE started). The child gets the normal platform."""
    print("== Run (F5) until the program window appears", flush=True)
    import ctypes
    from ctypes import wintypes
    import psutil
    user32 = ctypes.windll.user32
    w = ide()

    def windows_of(pids):
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(hwnd, _l):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value in pids and user32.IsWindowVisible(hwnd):
                n = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                if buf.value and "Default IME" not in buf.value and "MSCTFIME" not in buf.value:
                    found.append(buf.value)
            return True
        user32.EnumWindows(cb, 0)
        return found

    me = psutil.Process()
    for key, label, startup in (("vb", "VB6 (vb-basic, vbrun)", "frmGreeter"), ("py", "Python Tk", "Form1")):
        times, titles = [], set()
        for _ in range(max(2, ARGS.runs // 2)):
            w.open_project(projects[key], ask=False)
            settle()
            if w.project.startup != startup:
                w.project.startup = startup
            saved = os.environ.pop("QT_QPA_PLATFORM", None)
            try:
                before = {c.pid for c in me.children(recursive=True)}
                t0 = time.perf_counter()
                w.run_project(debug=False)
                seen = None
                while time.perf_counter() - t0 < 60:
                    app.processEvents()
                    kids = {c.pid for c in me.children(recursive=True)} - before
                    if kids:
                        wins = windows_of(kids)
                        if wins:
                            seen = time.perf_counter() - t0
                            titles.update(wins)
                            break
                    time.sleep(0.01)
            finally:
                if saved is not None:
                    os.environ["QT_QPA_PLATFORM"] = saved
            if seen is not None:
                times.append(seen * 1000)
            else:
                print(f"   {label}: no window seen (last output: {w.output.toPlainText()[-300:]!r})", flush=True)
            # close what the IDE started
            try:
                if w.session is not None:
                    w.session.stop() if hasattr(w.session, "stop") else None
            except Exception:  # noqa: BLE001
                pass
            for c in me.children(recursive=True):
                if c.pid not in before:
                    try:
                        c.kill()
                    except psutil.Error:
                        pass
            t1 = time.perf_counter()
            while w.session is not None and w.session.running() and time.perf_counter() - t1 < 10:
                app.processEvents()
                time.sleep(0.01)
            settle(0.2)
        if times:
            record(f"run.F5 {label} until window", times, "startup", note=f"window: {sorted(titles)}")
            print(f"   windows seen: {sorted(titles)}", flush=True)


# ===================================================================== main
def close_children():
    """Close the processes this run started (the IDE's extension host / language servers / programs)."""
    try:
        import psutil
        for c in psutil.Process().children(recursive=True):
            try:
                c.kill()
            except psutil.Error:
                pass
    except Exception:  # noqa: BLE001
        pass


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"RAD IDE designer performance  platform={PLATFORM}  runs={ARGS.runs}  tag={ARGS.tag}", flush=True)
    t_all = time.perf_counter()
    if want("startup"):
        phase_startup()
    projects = make_projects()
    try:
        for group, fn in (("codegen", phase_codegen), ("designer", phase_designer), ("vb6", phase_vb6_forms),
                          ("monaco", phase_monaco), ("run", phase_run)):
            if not want(group):
                continue
            try:
                fn(projects) if fn is not phase_vb6_forms else fn()
            except Exception:  # noqa: BLE001
                import traceback
                print(f"== phase {group} FAILED", flush=True)
                traceback.print_exc()
                sys.stderr.flush()
    finally:
        out = OUT / f"results_{ARGS.tag}_{PLATFORM}.json"
        out.write_text(json.dumps({"platform": PLATFORM, "runs": ARGS.runs, "controls": ARGS.controls,
                                   "results": RESULTS}, indent=1), encoding="utf-8")
        print(f"results: {out}  ({time.perf_counter() - t_all:.0f} s)", flush=True)
        close_children()
        QSettings().clear()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)


main()
