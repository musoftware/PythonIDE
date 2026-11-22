"""Characterization of closing the IDE while the features move from wrapping MainWindow.closeEvent to close
guards / shutdown steps (radide/extension_points.py).

Real MainWindow (offscreen), a Python project with an unsaved change, every feature's shutdown step replaced
by a counter (AI chat, AI web, Live Share, language servers, notebooks, terminal, workbench layout, VS Code
extension host, remote connections):
  1. the save question answered Cancel -> the IDE stays open, nothing is shut down
  2. a running agent task, "stop them and close?" answered No -> stays open, the task keeps running,
     nothing is shut down, the save question is not asked
  3. agent question Yes + save question Discard -> closed (win.close() returns True), the agent task is
     stopped, every shutdown step ran exactly once

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_close_flow.py [scratch]
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["RADIDE_TEST_NO_DIALOGS"] = "1"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-closeflow"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")          # must come before the QApplication
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtGui import QCloseEvent  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ARCH-CLOSE_FLOW")      # own store: tests run in parallel
QCoreApplication.setApplicationName("RADIDE-TEST-ARCH-CLOSE_FLOW")
app = QApplication(sys.argv[:1])
QSettings().clear()
SB = QMessageBox.StandardButton
ANSWER = {"agents": SB.Yes, "save": SB.Cancel}
ASKED: list[str] = []


def _question(*a, **k):
    text = str(a[2] if len(a) > 2 else k.get("text", ""))
    kind = "agents" if "agent task" in text else "save"
    ASKED.append(kind)
    return ANSWER[kind]


QMessageBox.question = staticmethod(_question)
for _n in ("warning", "critical", "information"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: SB.Ok))

results: list[tuple[str, bool]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:800]}]"), flush=True)
    return bool(cond)


def pump(n: int = 5) -> None:
    for _ in range(n):
        app.processEvents()


from radide import workspace  # noqa: E402
from radide.app import MainWindow  # noqa: E402

proj = SCRATCH / "CloseFlow"
workspace.create_project(proj, "CloseFlow", "python-tk")
win = MainWindow()
win.resize(1200, 800)
win.show()
pump()
win.open_project(proj, ask=False)
pump()
win._doc("Form1").set_modified(True)                     # an unsaved change: the save question is asked

import radide.features.remote as remote_mod  # noqa: E402

COUNT: dict[str, int] = {}


def spy(name):
    def f(*_a, **_k):
        COUNT[name] = COUNT.get(name, 0) + 1
    return f


STEPS = [("AI chat stop", lambda: win.ai_chat, "stop"), ("AI chat save", lambda: win.ai_chat, "save"),
         ("AI web shutdown", lambda: win.ai_web, "shutdown"), ("Live Share end", lambda: win.live_share, "end"),
         ("language servers", lambda: win.lsp_manager, "stop_all"),
         ("notebooks", lambda: win.notebook_feature, "shutdown_all"), ("terminal", lambda: win.terminal, "stop"),
         ("workbench layout", lambda: win.workbench, "save"), ("remote connections", lambda: remote_mod, "shutdown")]
if getattr(win, "vsx_host", None) is not None:
    STEPS.append(("VS Code extension host", lambda: win.vsx_host, "stop"))
for name, obj, attr in STEPS:
    setattr(obj(), attr, spy(name))


class FakeTask:
    def __init__(self, parent):
        self._parent, self.stopped = parent, 0

    def parent(self):
        return self._parent

    def stop(self):
        self.stopped += 1


mgr = win.agent_manager.mgr
task = FakeTask(mgr)

# 1. save question -> Cancel
ANSWER.update(agents=SB.Yes, save=SB.Cancel)
ASKED.clear()
e = QCloseEvent()
win.closeEvent(e)
pump()
ok("1. save question Cancel -> the IDE stays open", not e.isAccepted() and ASKED == ["save"], ASKED)
ok("1. ... nothing was shut down", not COUNT, COUNT)

# 2. running agent task -> No
mgr.running = lambda: [task]
ANSWER.update(agents=SB.No, save=SB.Discard)
ASKED.clear()
e = QCloseEvent()
win.closeEvent(e)
pump()
ok("2. 'agent tasks running - stop and close?' No -> stays open", not e.isAccepted(), ASKED)
ok("2. ... the save question is not asked after that", ASKED == ["agents"], ASKED)
ok("2. ... the task keeps running and nothing was shut down", task.stopped == 0 and not COUNT, (task.stopped, COUNT))

# 3. Yes + Discard -> closed through Qt (win.close)
ANSWER.update(agents=SB.Yes, save=SB.Discard)
ASKED.clear()
closed = win.close()
pump()
ok("3. agents Yes + save Discard -> the IDE closes", closed is True, (closed, ASKED))
ok("3. ... both questions were asked, agents first", ASKED == ["agents", "save"], ASKED)
ok("3. ... the running agent task was stopped", task.stopped == 1, task.stopped)
for name, _o, _a in STEPS:
    ok(f"3. ... shut down once: {name}", COUNT.get(name) == 1, COUNT.get(name))

QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
