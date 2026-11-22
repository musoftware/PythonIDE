"""Security: the QtWebEngine DevTools port (JavaScript debugging in the Preview) is opt-in and never inherited.

    python samples/Tests/Web/test_webengine_devtools_port.py

1. default IDE settings: enable_remote_debugging(settings) opens no port, no QTWEBENGINE_REMOTE_DEBUGGING is set;
   RADIDE_NO_JS_DEBUG wins over the setting; the Options page shows the box unchecked.
2. paths.clean_webengine_debug_environment: QTWEBENGINE_REMOTE_DEBUGGING removed, --remote-debugging-* switches
   removed from QTWEBENGINE_CHROMIUM_FLAGS, other switches kept.
3. in a child process that starts like radide.app.main() with web/js_debug turned on: the IDE's engine listens
   on the port (/json/version answers), but after seal_child_environment() the environment - and so every program
   the IDE starts (checked with a grandchild process) - has neither the variable nor the debug switches.
Exit code = number of failures."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
ORG = os.environ.get("RADIDE_TEST_ORG", "RADIDE-TEST-LEFTOVER")
results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond), str(detail)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{str(detail)[:400]}]" if detail and not cond else ""), flush=True)
    return bool(cond)


CHILD = r'''
import json, os, subprocess, sys, threading, time, urllib.request
sys.path.insert(0, sys.argv[1])
os.environ.pop("QTWEBENGINE_REMOTE_DEBUGGING", None)
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --remote-allow-origins=* --disable-gpu-compositing"
import PyQt6.QtWebEngineWidgets  # noqa: F401
from PyQt6.QtCore import QCoreApplication, QSettings
QCoreApplication.setOrganizationName(sys.argv[2]); QCoreApplication.setApplicationName(sys.argv[2] + "-DEVTOOLS")
s = QSettings(); s.setValue("web/js_debug", True); s.sync()
from radide.web_site import browser_debug as bd
port = bd.enable_remote_debugging(s)
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv[:1])
bd.seal_child_environment()                     # what radide.app.main() does right after QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
v = QWebEngineView(); v.setHtml("<p>preview</p>"); v.resize(300, 200); v.show()
box = {}
def fetch():
    for _ in range(40):
        try:
            box["v"] = urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2).read().decode()
            return
        except Exception as e:
            box["e"] = str(e); time.sleep(0.25)
t = threading.Thread(target=fetch, daemon=True); t.start()
end = time.time() + 20
while t.is_alive() and time.time() < end:
    app.processEvents(); time.sleep(0.02)
gc = subprocess.run([sys.executable, "-c", "import os, json; print(json.dumps({k: os.environ.get(k) for k in "
                     "('QTWEBENGINE_REMOTE_DEBUGGING', 'QTWEBENGINE_CHROMIUM_FLAGS')}))"], capture_output=True, text=True)
s.clear(); s.sync()
print("RESULT " + json.dumps({"port": port, "devtools_port": bd.devtools_port(), "answer": box.get("v", ""),
      "error": box.get("e", ""), "env": os.environ.get("QTWEBENGINE_REMOTE_DEBUGGING"),
      "flags": os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS"), "grandchild": json.loads(gc.stdout.strip() or "{}")}),
      flush=True)
os._exit(0)
'''

# ------------------------------------------------------------------ 1. default: off
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402

QCoreApplication.setOrganizationName(ORG)
QCoreApplication.setApplicationName(ORG + "-DEVTOOLS-DEFAULT")
st = QSettings()
st.clear()
for k in ("QTWEBENGINE_REMOTE_DEBUGGING", "RADIDE_JS_DEBUG", "RADIDE_NO_JS_DEBUG"):
    os.environ.pop(k, None)
from radide.web_site import browser_debug as bd  # noqa: E402
from radide import paths  # noqa: E402

ok("default settings: JavaScript debugging in the Preview is off", not bd.js_debug_enabled(st))
ok("default settings: no DevTools port", bd.enable_remote_debugging(st) == 0 and bd.devtools_port() == 0)
ok("default settings: QTWEBENGINE_REMOTE_DEBUGGING not set", "QTWEBENGINE_REMOTE_DEBUGGING" not in os.environ)
st.setValue("web/js_debug", True)
ok("turned on in Tools > Options > Web", bd.js_debug_enabled(st))
os.environ["RADIDE_NO_JS_DEBUG"] = "1"
ok("RADIDE_NO_JS_DEBUG wins", not bd.js_debug_enabled(st) and bd.enable_remote_debugging(st) == 0
   and "QTWEBENGINE_REMOTE_DEBUGGING" not in os.environ)
os.environ.pop("RADIDE_NO_JS_DEBUG")
st.clear()

# ------------------------------------------------------------------ 2. child environment cleaning
env = {"QTWEBENGINE_REMOTE_DEBUGGING": "127.0.0.1:9333", "PATH": "x",
       "QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu --remote-debugging-port=9333 --remote-debugging-address 0.0.0.0"}
paths.clean_webengine_debug_environment(env)
ok("child env: QTWEBENGINE_REMOTE_DEBUGGING removed", "QTWEBENGINE_REMOTE_DEBUGGING" not in env, env)
ok("child env: debug switches removed, --disable-gpu kept",
   env.get("QTWEBENGINE_CHROMIUM_FLAGS", "").startswith("--disable-gpu") and "remote-debugging" not in
   env.get("QTWEBENGINE_CHROMIUM_FLAGS", "") and env["PATH"] == "x", env)
env = {"QTWEBENGINE_CHROMIUM_FLAGS": "--remote-debugging-port=1"}
paths.clean_webengine_debug_environment(env)
ok("child env: a debug-only flags value is dropped", env == {}, env)

# ------------------------------------------------------------------ 3. the IDE keeps its port, children do not get it
cenv = dict(os.environ)
cenv.setdefault("QT_QPA_PLATFORM", "offscreen")
r = subprocess.run([sys.executable, "-c", CHILD, str(REPO), ORG], capture_output=True, text=True, env=cenv, timeout=180,
                   encoding="utf-8", errors="replace")
line = next((ln for ln in r.stdout.splitlines() if ln.startswith("RESULT ")), "")
res = json.loads(line[7:]) if line else {}
ok("opted in: the IDE's engine got a port", res.get("port", 0) > 0 and res.get("devtools_port") == res.get("port"),
   (res, r.stderr[-400:]))
ok("opted in: the IDE's DevTools port answers (/json/version)", '"Browser"' in res.get("answer", ""),
   res.get("error") or res.get("answer"))
ok("after start-up: QTWEBENGINE_REMOTE_DEBUGGING is gone from the IDE's environment", res.get("env") is None, res)
ok("after start-up: no debug switches in QTWEBENGINE_CHROMIUM_FLAGS",
   res.get("flags") == "--disable-gpu --disable-gpu-compositing", res.get("flags"))
gc = res.get("grandchild") or {}
ok("a program started by the IDE inherits neither", gc and gc.get("QTWEBENGINE_REMOTE_DEBUGGING") is None
   and "remote" not in (gc.get("QTWEBENGINE_CHROMIUM_FLAGS") or ""), gc)

# ------------------------------------------------------------------ 4. Options page shows it unchecked by default
from PyQt6.QtWidgets import QApplication, QCheckBox  # noqa: E402

app = QApplication(sys.argv[:1])
from radide.features import web_extras  # noqa: E402


class _Dlg:
    class win:  # noqa: N801
        settings = QSettings()


page, title, _apply = web_extras._options_page(_Dlg())
cb = page.findChild(QCheckBox)
ok("Options > Web: 'Debug JavaScript in the Preview' unchecked by default", title == "Web" and cb is not None
   and not cb.isChecked())
QSettings().clear()

fails = sum(1 for _n, c, _d in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
sys.exit(fails)
