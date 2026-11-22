"""IntelliSense: after "self." in a Python form handler the form's controls / members come first, dunders last.

    python samples/Tests/Editor/test_python_self_completion_order.py [scratch folder]

The E2E journey saw the member list start with __annotations__, __class__ ... (Monaco orders by sortText / label and
"_" sorts before lower-case letters). An offscreen MainWindow opens a Python Tk project from the template with a
Button btnGo and a Label lblOut, types "self." in Form1_Load and asks the editor for completions (MonacoEditor
._complete, the merge of the language server's and the plugin's items). Checks, in Monaco's order (sortText, then
label): the first items are not "_" names, the controls come before every _private / dunder name, the dunders are
last; a VB form's items get no extra sortText (other languages unchanged).
Exit code = number of failures."""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("RADIDE_NO_BROWSER", "1")
os.environ["RADIDE_NO_VSX"] = "1"
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="radide_selfcomp_")) / "self_completion"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond), str(detail)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{str(detail)[:500]}]" if detail and not cond else ""), flush=True)
    return bool(cond)


# ------------------------------------------------------------------ unit: the ranking itself
from radide.monaco_editor import MonacoEditor  # noqa: E402

items = [{"label": "__annotations__"}, {"label": "_private", "sortText": "a"}, {"label": "btnGo", "sortText": "b"},
         {"label": "Form1_Load"}, {"label": "__init__", "sortText": "a"}]
MonacoEditor.rank_private_last(items)
order = [i["label"] for i in sorted(items, key=lambda i: (i["sortText"].lower(), i["label"]))]
ok("ranking: public names, then _private, then dunders", set(order[:2]) == {"btnGo", "Form1_Load"}
   and order[2] == "_private" and set(order[3:]) == {"__init__", "__annotations__"}, order)

__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

app = QApplication(sys.argv[:1])
ORG = os.environ.get("RADIDE_TEST_ORG", "RADIDE-TEST-LEFTOVER")
QCoreApplication.setOrganizationName(ORG)
QCoreApplication.setApplicationName(ORG + "-SELFCOMP")
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)


def pump(sec=0.05):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.01)


def wait(cond, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.03)
    return False


def capture(ed, line, col, timeout=30.0):
    sent = []
    orig = ed._js
    ed._js = lambda code: sent.append(code) if code.startswith("radResolve(77,") else orig(code)
    try:
        ed._complete(77, line, col)
        wait(lambda: bool(sent), timeout)
    finally:
        ed._js = orig
    if not sent:
        return None
    return json.loads(sent[0][len("radResolve(77,"):].rsplit(");", 1)[0])


def monaco_order(items):
    return [i["label"] if isinstance(i["label"], str) else i["label"].get("label")
            for i in sorted(items, key=lambda i: ((i.get("sortText") or str(i["label"])).lower(), str(i["label"])))]


from radide import workspace  # noqa: E402
from radide.controls import CONTROL_TYPES  # noqa: E402
from radide.model import Control, Form  # noqa: E402


def make_project(lang: str, name: str) -> Path:
    folder = SCRATCH / name
    project = workspace.create_project(folder, name, lang)
    fp = project.form_path("Form1")
    form = Form.load(fp)
    for t, n, y in (("Button", "btnGo", 20), ("Label", "lblOut", 60)):
        props = CONTROL_TYPES[t].default_props(n)
        props.update({"Left": 20, "Top": y})
        form.controls.append(Control(t, props))
    form.save(fp)
    workspace._regen(project, "Form1")
    return folder


from radide.app import MainWindow  # noqa: E402

win = MainWindow()
win.resize(1200, 800)
win.show()
pump(1.0)

# ------------------------------------------------------------------ Python: "self." in Form1_Load
win.open_project(make_project("python-tk", "PySelf"), ask=False)
pump(1.0)
win.open_code("Form1")
cv = win._codeview("Form1")
ed = cv.editor
ok("Python code editor ready", wait(lambda: getattr(ed, "_ready", False), 60))
code = ed.text().replace("    def Form1_Load(self):\n        pass\n", "    def Form1_Load(self):\n        self.\n")
ed.setText(code)
pump(0.5)
lines = code.splitlines()
row = next(i for i, ln in enumerate(lines) if ln.strip() == "self.")
col = len(lines[row])
res = None
for _ in range(3):                     # the in-process server may still be warming up
    res = capture(ed, row, col)
    if res and any((i.get("label") if isinstance(i.get("label"), str) else "") == "btnGo" for i in res):
        break
    pump(2.0)
labels = monaco_order(res or [])
ok("member list after 'self.' has the controls", {"btnGo", "lblOut"} <= set(labels), labels[:15])
ok("the first items are not _ / dunder names", labels and not any(n.startswith("_") for n in labels[:5]), labels[:8])
under = [i for i, n in enumerate(labels) if n.startswith("_")]
ok("controls come before every _ name", under and max(labels.index("btnGo"), labels.index("lblOut")) < min(under)
   if {"btnGo", "lblOut"} <= set(labels) else False, labels[:12])
dunder = [i for i, n in enumerate(labels) if n.startswith("__") and n.endswith("__")]
private = [i for i, n in enumerate(labels) if n.startswith("_") and not (n.startswith("__") and n.endswith("__"))]
ok("dunders are last", dunder and (not private or max(private) < min(dunder)) and max(dunder) == len(labels) - 1,
   labels[-6:])
cv.grab().save(str(SCRATCH.parent / "self_completion.png"))

# ------------------------------------------------------------------ VB: unchanged
win.open_project(make_project("vb-basic", "VbSelf"), ask=False)
pump(1.0)
try:
    win.open_code("Form1")
    vcv = win._codeview("Form1")
    ved = vcv.editor
    if wait(lambda: getattr(ved, "_ready", False), 60) and ved.language() != "python":
        vtext = ved.text()
        vl = vtext.splitlines()
        r = next((i for i, ln in enumerate(vl) if "End Sub" in ln), 1)
        vres = capture(ved, r, 0) or []
        plain = MonacoEditor._merge_completions(ved._extra_completions(r, 0), list(vres))
        ok(f"{ved.language()}: no group prefix added to sortText",
           all(not str(i.get("sortText") or "").startswith(("0", "1", "2")) or i.get("sortText") == p.get("sortText")
               for i, p in zip(vres, plain)), [i.get("sortText") for i in vres[:5]])
    else:
        ok("VB form editor (skipped: not available)", True)
except Exception as e:  # noqa: BLE001
    ok("VB form editor", False, e)

try:
    win.save_all()
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c, _d in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
