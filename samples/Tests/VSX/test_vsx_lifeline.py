"""The extension host never outlives RAD IDE (radide/vsx/host/lifeline.js).

    python samples/Tests/VSX/test_vsx_lifeline.py <scratch folder>

Starts a real IDE process (MainWindow, offscreen) with a test extension that starts a long-running child process
(like a language server), then kills the IDE process hard (TerminateProcess - a crash / os._exit / Task Manager).
Checks: the extension host exits within 10 s and the extension's child process is killed with it; a normal
VsxService.stop() also ends the host and its child. Exit code = number of failures."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_lifeline_test"
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:300]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:300]}]" if detail else ""), flush=True)


def alive(pid: int) -> bool:
    if not pid:
        return False
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def wait_for(cond, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.25)
    return cond()


# a test extension whose activation starts a child that runs forever (MIT, written for this test)
ext = SCRATCH / "lifeline-ext"
ext.mkdir()
(ext / "package.json").write_text(json.dumps({
    "name": "lifeline-test", "publisher": "radide-test", "version": "0.0.1", "engines": {"vscode": "^1.80.0"},
    "main": "./extension.js", "activationEvents": ["*"]}), "utf-8")
(ext / "extension.js").write_text("""const cp = require('child_process'); const fs = require('fs'); const path = require('path');
exports.activate = () => {
  const child = cp.spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { stdio: 'ignore' });
  fs.writeFileSync(path.join(process.env.LIFELINE_OUT, 'child.pid'), String(child.pid));
};
exports.deactivate = () => {};
""", "utf-8")
vsix = SCRATCH / "radide-test.lifeline-test-0.0.1.vsix"
with zipfile.ZipFile(vsix, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.'
               'openxmlformats.org/package/2006/content-types"/>')
    for f in ext.rglob("*"):
        z.write(f, "extension/" + f.relative_to(ext).as_posix())

env = dict(os.environ, RADIDE_VSX_ROOT=str(SCRATCH / "vsxroot"), RADIDE_NO_BROWSER="1", QT_QPA_PLATFORM="offscreen",
           LIFELINE_OUT=str(SCRATCH), PYTHONIOENCODING="utf-8")
subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(REPO)!r}); from radide.vsx import manager; "
                f"manager.install_vsix_file({str(vsix)!r}, with_dependencies=False)"], env=env, check=True)

IDE = SCRATCH / "ide.py"
IDE.write_text(f"""import os, sys, time
sys.path.insert(0, {str(REPO)!r})
__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST-VSX2"); QCoreApplication.setApplicationName("RADIDE-TEST-VSX2-LIFE")
from radide.app import MainWindow
win = MainWindow(); win.show()
svc = win.vsx_host
mode = sys.argv[1]
def tick():
    r = svc.host.init_result
    if r and (os.path.exists(os.path.join(os.environ["LIFELINE_OUT"], "child.pid"))):
        open(os.path.join(os.environ["LIFELINE_OUT"], "host.pid"), "w").write(str(r.get("pid")))
        if mode == "stop":
            svc.stop()
            open(os.path.join(os.environ["LIFELINE_OUT"], "stopped"), "w").write("1")
            os._exit(0)
        return
    QTimer.singleShot(200, tick)
QTimer.singleShot(200, tick)
app.exec()
""", "utf-8")


def run(mode: str):
    for f in ("host.pid", "child.pid", "stopped"):
        (SCRATCH / f).unlink(missing_ok=True)
    p = subprocess.Popen([sys.executable, str(IDE), mode], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = wait_for(lambda: (SCRATCH / "host.pid").exists() or p.poll() is not None, 120)
    host = int((SCRATCH / "host.pid").read_text()) if (SCRATCH / "host.pid").exists() else 0
    child = int((SCRATCH / "child.pid").read_text()) if (SCRATCH / "child.pid").exists() else 0
    return p, ok, host, child


# 1. hard kill of the IDE
p, ok, host, child = run("kill")
check(ok and alive(host) and alive(child), "IDE started its extension host; the extension started a child", (host, child))
p.kill()                                   # TerminateProcess: no closeEvent, no stop()
p.wait(10)
t0 = time.time()
check(wait_for(lambda: not alive(host), 10), "host exits within 10 s after the IDE was killed", f"{time.time() - t0:.1f}s")
check(wait_for(lambda: not alive(child), 10), "... and the extension's child process is killed too", child)

# 2. normal stop
p, ok, host, child = run("stop")
check(ok and wait_for(lambda: (SCRATCH / "stopped").exists(), 30), "IDE stopped its host (VsxService.stop)")
check(wait_for(lambda: not alive(host), 10), "host gone after stop()", host)
check(wait_for(lambda: not alive(child), 10), "extension child gone after stop()", child)
for pid in (host, child):                 # never leave anything behind
    if alive(pid):
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True) if sys.platform == "win32" else None

fails = [r for r in RESULTS if not r[0]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed", flush=True)
sys.exit(len(fails))
