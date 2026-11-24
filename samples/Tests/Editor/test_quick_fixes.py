"""Alt+Enter / Ctrl+. Quick Actions in the real IDE (offscreen MainWindow, Monaco editors).

    python samples/Tests/Editor/test_quick_fixes.py [scratch folder] [--network]

* loose C# file: List<int> -> Alt+Enter -> "using System.Collections.Generic;" (preferred, selected), the preview
  shows the added line, Enter/trigger applies it; a mocked language server offering the same using -> it is shown
  once (dedup), its own action is applied through codeAction; Ctrl+. opens the same menu
* RAD C# form (csharp-bridge, GUI Bridge mode): MessageBox.Show("Hello") with a CS0103 squiggle -> the light bulb appears on the
  line, Alt+Enter -> "Use the RAD helper MsgBox(...)" first and "using System.Windows.Forms;" greyed out with the
  reason; applying rewrites the call and the squiggle goes away; the editor's right-click menu has the entry
* Python form: np.array -> "import numpy as np"; import yaml in a project with its own .venv -> "Install 'PyYAML'
  with pip" (dry run: the command uses the .venv's python, requirements.txt gets PyYAML). --network: the real pip
  install into a scratch venv (with pip), then "import yaml" works there
* JavaScript: import of lodash with no node_modules -> "Install 'lodash' with npm" (dry run); Rust: HashMap -> use
Exit code = number of failures."""
from __future__ import annotations

import os
import shutil
import subprocess
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
NETWORK = "--network" in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
SCRATCH = Path(ARGS[0] if ARGS else tempfile.mkdtemp(prefix="radide_quickfix_")) / "quick_fixes"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond), str(detail)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{str(detail)[:600]}]" if detail and not cond else ""), flush=True)
    return bool(cond)


__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, Qt  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST-QUICKFIX")
QCoreApplication.setApplicationName("RADIDE-TEST-QUICKFIX")
QSettings().clear()
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)

from radide.quickfix import installers  # noqa: E402

installers.DRY_RUN = True


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


def js(ed, code, timeout=10.0):
    box = []
    ed.page().runJavaScript(code, lambda v: box.append(v))
    wait(lambda: bool(box), timeout)
    return box[0] if box else None


def write(rel: str, text: str) -> Path:
    p = SCRATCH / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def put_caret(ed, line, col):
    ed.setCursorPosition(line, col)
    wait(lambda: js(ed, "radEditor.getPosition().lineNumber") == line + 1, 5)
    pump(0.1)


HOW = {}


def open_menu(win, ed, keys="alt+enter", timeout=20.0):
    """Press the shortcut in the editor (a real key event; a DOM key event if the offscreen view gets none)."""
    win._refactor_no_exec = True
    win._refactor_menu = None
    ed.setFocus()
    pump(0.2)
    target = ed.focusProxy() or ed
    key, mod = ((Qt.Key.Key_Return, Qt.KeyboardModifier.AltModifier) if keys == "alt+enter"
                else (Qt.Key.Key_Period, Qt.KeyboardModifier.ControlModifier))
    QTest.keyClick(target, key, mod)
    if wait(lambda: win._refactor_menu is not None, 4):
        HOW[keys] = "Qt key event"
        wait(lambda: getattr(win, "_quick_actions", None) is not None, timeout)
        return win._refactor_menu
    code = ("Enter", 13, "altKey") if keys == "alt+enter" else (".", 190, "ctrlKey")
    js(ed, "(function(){radEditor.focus();const t=document.querySelector('.monaco-editor textarea');"
           f"t.dispatchEvent(new KeyboardEvent('keydown',{{key:'{code[0]}',code:'{'Enter' if code[1] == 13 else 'Period'}',"
           f"keyCode:{code[1]},which:{code[1]},{code[2]}:true,bubbles:true,cancelable:true}}));return 1;}})()")
    if wait(lambda: win._refactor_menu is not None, timeout):
        HOW[keys] = "DOM key event"
        return win._refactor_menu
    return None


def entries(menu):
    return [a.text().strip().lstrip("★").strip() for a in menu.actions()] if menu else []


def action_for(win, menu, needle):
    for a in (menu.actions() if menu else []):
        qa = win._quick_menu_map.get(id(a))
        if qa is not None and needle in qa.title:
            return a, qa
    return None, None


from radide import workspace  # noqa: E402
from radide.app import MainWindow  # noqa: E402

win = MainWindow()
win.resize(1300, 850)
win.show()
pump(1.0)

# ------------------------------------------------------------------ loose C# file: List<int>
cs = "class A\n{\n    void F()\n    {\n        var l = new List<int>();\n    }\n}\n"
pa = write("loose/A.cs", cs)
ed = win.open_any_file(pa)
ok("C# editor ready", ed is not None and wait(lambda: getattr(ed, "_ready", False), 60))
wait(lambda: js(ed, "!!window.radQf") is True, 15)
ok("the quick-fix script (light bulb + Alt+Enter) is in the editor", js(ed, "!!window.radQf") is True)
put_caret(ed, 4, 22)
menu = open_menu(win, ed, "alt+enter")
ok("Alt+Enter opens Quick Actions", menu is not None, HOW)
print(f"  (Alt+Enter delivered as: {HOW.get('alt+enter')})")
ok("menu: using System.Collections.Generic; first and preferred",
   menu is not None and win._quick_actions and win._quick_actions[0].title == "using System.Collections.Generic;"
   and win._quick_actions[0].preferred, [a.title for a in getattr(win, "_quick_actions", [])])
ok("menu: grouped like VS (Quick Fixes) + Rename / Find All References",
   {"Quick Fixes", "Rename Symbol...", "Find All References"} <= {e.split("\t")[0] for e in entries(menu)}, entries(menu))
ok("menu: the preferred fix is the one Enter applies", getattr(win, "_quick_first", None) is not None and
   win._quick_menu_map.get(id(win._quick_first)).title == "using System.Collections.Generic;")
act, qa = action_for(win, menu, "using System.Collections.Generic;")
if act is not None:
    menu.hovered.emit(act)
    pv = getattr(win, "_quick_preview", None)
    ok("preview: the added line (+) is shown", pv is not None and "+    1  using System.Collections.Generic;" in pv.plain,
       pv and pv.plain)
    act.trigger()
    pump(0.5)
ok("applied: using System.Collections.Generic; on top", ed.text().startswith("using System.Collections.Generic;\n"),
   ed.text()[:120])
wait(lambda: js(ed, "radEditor.getValue()").startswith("using System.Collections.Generic;"), 5)
ok("applied in Monaco too (one undo step)", js(ed, "radEditor.getValue()").startswith("using System.Collections.Generic;"))
ok("undo removes it in one step", js(ed, "radEditor.trigger('t','undo');radEditor.getValue().startsWith('class A')")
   is True)
js(ed, "radEditor.trigger('t','redo');1")
wait(lambda: ed.text().startswith("using"), 5)


# a mocked language server: the same using (must be shown once) + an action of its own
class FakeLsp:
    raw_diagnostics: dict = {}
    capabilities = {"codeActionProvider": True}
    last_error = ""
    _initialized = False

    def __init__(self, path):
        self.path = path
        self.requests = []

    def running(self):
        return True

    def did_change(self, *a):
        pass

    def did_close(self, *a):
        pass

    def _request(self, method, params, cb):
        self.requests.append(method)
        uri = Path(self.path).resolve().as_uri()
        if method == "textDocument/codeAction":
            cb([{"title": "using System.Text;", "kind": "quickfix", "isPreferred": True,
                 "edit": {"changes": {uri: [{"range": {"start": {"line": 1, "character": 0},
                                                     "end": {"line": 1, "character": 0}},
                                           "newText": "using System.Text;\n"}]}}},
                {"title": "Server-only fix", "kind": "quickfix",
                 "edit": {"changes": {uri: [{"range": {"start": {"line": 0, "character": 0},
                                                     "end": {"line": 0, "character": 0}},
                                           "newText": "// server\n"}]}}}])
        else:
            cb(None)


text = ed.text().replace("var l = new List<int>();", "var sb = new StringBuilder();")
ed.setText(text)
pump(0.3)
row = next(i for i, s in enumerate(ed.text().split("\n")) if "StringBuilder" in s)
put_caret(ed, row, ed.text().split("\n")[row].index("StringBuilder") + 3)
fake = FakeLsp(pa)
ed.lsp = fake
menu = open_menu(win, ed, "ctrl+.")
ok("Ctrl+. opens Quick Actions (with the language server)", menu is not None and "textDocument/codeAction" in
   fake.requests, (HOW, fake.requests))
titles = [a.title for a in getattr(win, "_quick_actions", [])]
ok("dedup: 'using System.Text;' shown once (server + built-in)", titles.count("using System.Text;") == 1, titles)
ok("merge: the server's own action is there", "Server-only fix" in titles, titles)
act, qa = action_for(win, menu, "Server-only fix")
ok("merge: the server action keeps its LSP payload", qa is not None and qa.lsp is not None)
if act is not None:
    act.trigger()
    pump(0.5)
ok("the server's action is applied through codeAction", ed.text().startswith("// server\n"), ed.text()[:60])
ed.lsp = None

# ------------------------------------------------------------------ loose JavaScript: npm
write("web/package.json", '{"name": "w"}')
pj = write("web/app.js", "import _ from 'lodash';\n\nconsole.log(_.chunk([1, 2], 1));\n")
jed = win.open_any_file(pj)
ok("JS editor ready", jed is not None and wait(lambda: getattr(jed, "_ready", False), 60))
put_caret(jed, 0, 17)
menu = open_menu(win, jed)
act, qa = action_for(win, menu, "Install 'lodash' with npm")
ok("JS: Install 'lodash' with npm offered", act is not None, entries(menu))
installers.LAST.clear()
if act is not None:
    act.trigger()
    pump(0.3)
ok("JS: npm install lodash (dry run) in the package.json folder", installers.LAST and installers.LAST[-1]["argv"][1:]
   == ["install", "lodash"] and Path(installers.LAST[-1]["cwd"]) == SCRATCH / "web", installers.LAST)

# ------------------------------------------------------------------ loose Rust: use std::collections::HashMap
pr = write("rs/main.rs", "fn main() {\n    let m: HashMap<i32, i32> = HashMap::new();\n}\n")
red = win.open_any_file(pr)
ok("Rust editor ready", red is not None and wait(lambda: getattr(red, "_ready", False), 60))
put_caret(red, 1, 12)
menu = open_menu(win, red)
act, qa = action_for(win, menu, "use std::collections::HashMap;")
if act is not None:
    act.trigger()
    pump(0.3)
ok("Rust: use std::collections::HashMap; added", red.text().startswith("use std::collections::HashMap;\n"),
   red.text()[:80])

# ------------------------------------------------------------------ RAD C# form: MessageBox
rad = SCRATCH / "RadCs"
try:
    workspace.create_project(rad, "RadCs", "csharp-bridge")
    from radide.dotnet import native_project as _NP      # these checks are about the GUI Bridge mode (no WinForms);
    _NP.set_mode(rad, _NP.BRIDGE)                       # native mode: samples/Tests/Editor/test_quickfix_providers.py
    win.open_project(rad, ask=False)
    pump(1.0)
    win.open_code("Form1")
    cv = win._codeview("Form1")
    ced = cv.editor
    ok("RAD C# code editor ready", wait(lambda: getattr(ced, "_ready", False), 60))
    code = ced.text()
    idx = code.rindex("}")
    handler = ("    static void RmButton1_Click(RadEvent e)\n    {\n        MessageBox.Show(\"Hello\");\n    }\n")
    ced.setText(code[:idx] + handler + code[idx:])
    pump(0.5)
    lines = ced.text().split("\n")
    row = next(i for i, s in enumerate(lines) if "MessageBox.Show" in s)
    c0 = lines[row].index("MessageBox")
    ced.set_diagnostics([{"line": row, "col": c0, "endLine": row, "endCol": c0 + 10, "severity": "error",
                          "message": "The name 'MessageBox' does not exist in the current context"}])
    wait(lambda: js(ced, "!!window.radQf") is True, 15)
    put_caret(ced, row, c0 + 3)
    js(ced, "radQf.schedule(0);1")
    ok("light bulb on the MessageBox line", wait(lambda: js(ced, "radQf.line()") == row, 10), js(ced, "radQf.line()"))
    ok("light bulb drawn in the glyph margin", wait(lambda: js(ced, "!!document.querySelector('.rad-bulb')") is True, 5))
    put_caret(ced, row + 1, 4)
    js(ced, "radQf.schedule(0);1")
    ok("no light bulb on the line with nothing to fix", wait(lambda: js(ced, "radQf.line()") == -1, 10),
       js(ced, "radQf.line()"))
    put_caret(ced, row, c0 + 3)
    menu = open_menu(win, ced)
    titles = [a.title for a in getattr(win, "_quick_actions", [])]
    ok("RAD C#: 'Use the RAD helper MsgBox(...)' first", titles and titles[0].startswith("Use the RAD helper MsgBox(...)"),
       titles)
    act, qa = action_for(win, menu, "using System.Windows.Forms")
    ok("RAD C#: 'using System.Windows.Forms;' greyed out with the reason", act is not None and not act.isEnabled()
       and "console process" in qa.title and act.toolTip(), (titles, act and act.toolTip()))
    act, qa = action_for(win, menu, "Use the RAD helper MsgBox")
    if act is not None:
        menu.hovered.emit(act)
        pv = win._quick_preview.plain
        ok("RAD C#: preview shows - MessageBox.Show / + MsgBox", "- " in pv and "MessageBox.Show" in pv and
           "+ " in pv and 'MsgBox("Hello");' in pv, pv)
        act.trigger()
        pump(0.5)
    ok("RAD C#: the call is now MsgBox(\"Hello\");", 'MsgBox("Hello");' in ced.text() and "MessageBox" not in ced.text(),
       ced.text()[-200:])
    ok("RAD C#: the squiggle is gone", not getattr(ced, "_diagnostics", []) and
       wait(lambda: js(ced, "monaco.editor.getModelMarkers({owner:'rad'}).length") == 0, 5))
    m = QMenu()
    ced.contextMenuAboutToShow.emit(m)
    ok("right-click menu: Quick Actions and Refactorings...", any(a.text().startswith("Quick Actions and Refactorings")
                                                                 for a in m.actions()), [a.text() for a in m.actions()])
    cv.grab().save(str(SCRATCH / "rad_csharp_quickfix.png"))
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    ok("RAD C# part", False, e)

# ------------------------------------------------------------------ Python form: numpy alias, pip install
pyp = SCRATCH / "PyQf"
try:
    workspace.create_project(pyp, "PyQf", "python-tk")
    (pyp / "requirements.txt").write_text("requests\n", encoding="utf-8")
    venv_args = [sys.executable, "-m", "venv"] + ([] if NETWORK else ["--without-pip"]) + [str(pyp / ".venv")]
    r = subprocess.run(venv_args, capture_output=True, text=True, timeout=600)
    vpy = pyp / ".venv" / "Scripts" / "python.exe"
    ok("project .venv created", r.returncode == 0 and vpy.is_file(), r.stderr[-300:])
    win.open_project(pyp, ask=False)
    pump(1.0)
    win.open_code("Form1")
    pcv = win._codeview("Form1")
    ped = pcv.editor
    ok("Python code editor ready", wait(lambda: getattr(ped, "_ready", False), 60))
    code = ped.text()
    lines = code.split("\n")
    load = next(i for i, s in enumerate(lines) if "def Form1_Load" in s)
    body = next(i for i in range(load + 1, len(lines)) if lines[i].strip())
    ind = lines[body][:len(lines[body]) - len(lines[body].lstrip())]
    lines[body] = ind + "x = np.array([1, 2])"
    ped.setText("\n".join(lines))
    pump(0.3)
    put_caret(ped, body, len(ind) + 5)
    menu = open_menu(win, ped)
    titles = [a.title for a in getattr(win, "_quick_actions", [])]
    ok("Python: np -> 'import numpy as np' first", titles and titles[0] == "import numpy as np", titles)
    ok("Python: numpy not in the .venv -> 'Install numpy with pip' too", any("Install 'numpy' with pip" in t
                                                                             for t in titles), titles)
    act, qa = action_for(win, menu, "import numpy as np")
    if act is not None:
        act.trigger()
        pump(0.4)
    ok("Python: import numpy as np added to the imports", "\nimport numpy as np\n" in "\n" + ped.text(),
       ped.text()[:300])
    ped.setText("import yaml\n" + ped.text())
    pump(0.3)
    put_caret(ped, 0, 9)
    menu = open_menu(win, ped)
    act, qa = action_for(win, menu, "Install 'PyYAML' with pip")
    ok("Python: import yaml -> Install 'PyYAML' with pip", act is not None, entries(menu))
    ok("Python: the preview names the .venv's python", qa is not None and str(vpy) in qa.detail, qa and qa.detail)
    if act is not None:
        menu.hovered.emit(act)
        ok("Python: preview of the pip action", "pip install PyYAML" in win._quick_preview.plain, win._quick_preview.plain)
        installers.LAST.clear()
        installers.DRY_RUN = not NETWORK
        act.trigger()
        if NETWORK:
            done = wait(lambda: "PyYAML" in (pyp / "requirements.txt").read_text(encoding="utf-8"), 600)
            chk = subprocess.run([str(vpy), "-c", "import yaml; print(yaml.__version__)"], capture_output=True,
                                 text=True, timeout=60)
            ok("network: pip installed PyYAML into the project's .venv (with progress)", done and chk.returncode == 0,
               (chk.stdout, chk.stderr[-300:]))
        pump(0.3)
        installers.DRY_RUN = True
    ok("Python: pip ran with the .venv's python", installers.LAST and Path(installers.LAST[-1]["argv"][0]) == vpy
       and installers.LAST[-1]["argv"][1:] == ["-m", "pip", "install", "PyYAML"], installers.LAST)
    ok("Python: requirements.txt has PyYAML", "PyYAML" in (pyp / "requirements.txt").read_text(encoding="utf-8"))
    pcv.grab().save(str(SCRATCH / "python_quickfix.png"))
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    ok("Python part", False, e)

try:
    for e in (ed, jed, red):
        if e is not None:
            e.setModified(False)
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c, _d in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
