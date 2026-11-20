"""Child process of test_single_instance.py: runs radide.app.main() with the RADIDE-TEST settings and a
test instance name (RADIDE_INSTANCE_NAME), off-screen, and reports what happened as JSON files.

    si_child.py primary   <outdir>                 the first IDE: reports every hand-over it receives
    si_child.py secondary <outdir> <tag> args...   a later launch: reports whether it opened a window"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QTimer  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")

from radide import app as A  # noqa: E402
from radide import single_instance as SI  # noqa: E402

mode, out = sys.argv[1], Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
threading.Timer(180, lambda: os._exit(3)).start()        # watchdog
if os.environ.get("SI_DUMP") and mode == "primary":         # debugging: where the primary spends its time
    import faulthandler
    faulthandler.dump_traceback_later(int(os.environ["SI_DUMP"]), repeat=True)


def write(name, data):
    tmp = out / (name + ".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, out / name)


def window_state(win):
    tabs = [win.tabs.tabText(i) for i in range(win.tabs.count())]
    ed = None
    w = win.tabs.currentWidget()
    e = getattr(w, "editor", None)
    try:
        line = e.getCursorPosition()[0] + 1 if e is not None and hasattr(e, "getCursorPosition") else None
    except Exception:  # noqa: BLE001
        line = None
    return {"tabs": tabs, "current": win.tabs.tabText(win.tabs.currentIndex()), "line": line, "editor": ed,
            "project": getattr(win.project, "name", None)}


created = []
orig_init = A.MainWindow.__init__


def init(self, *a, **k):
    orig_init(self, *a, **k)
    created.append(self)
    if mode == "secondary":                    # a separate window was opened: report and close it
        QTimer.singleShot(1500, lambda: (write(f"secondary_{sys.argv[3]}_window.json", window_state(self)),
                                         QCoreApplication.exit(0)))


A.MainWindow.__init__ = init

if mode == "primary":
    orig_start = SI.start_server

    def start(win, lock=None, name=None):
        srv = orig_start(win, lock, name)
        n = [0]
        orig_handle = srv._handle

        def handle(msg):
            orig_handle(msg)
            n[0] += 1
            write(f"handled_{n[0]}.json", {"msg": msg, **window_state(win)})
        srv._handle = handle
        write("ready.json", {"ok": srv.ok, "name": srv.name, "pid": os.getpid()})

        def poll():
            if (out / "quit").exists():
                t.stop()
                import faulthandler
                faulthandler.dump_traceback_later(25, exit=True)      # a hang on exit: show where
                win._confirm_close_project = lambda: True
                QCoreApplication.exit(0)
        t = QTimer(win)
        t.timeout.connect(poll)
        t.start(200)
        return srv
    SI.start_server = start
    A.start_server = start
    code = A.main([sys.argv[0]])
    write("primary_exit.json", {"code": code})
else:
    tag = sys.argv[3]
    code = A.main([sys.argv[0], *sys.argv[4:]])
    write(f"secondary_{tag}.json", {"code": code, "window": bool(created)})
os._exit(0)
