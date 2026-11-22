"""The first VS Code extension installed into a running IDE activates at once (like VS Code), without an IDE restart.

    python samples/Tests/VSX/test_vsx_install_activate.py [scratch folder] [<anthropic.claude-code .vsix>]

An offscreen MainWindow starts with an empty RADIDE_VSX_ROOT (so no extension host runs), then the Extensions view
installs samples/Tests/VSX/hello-commands as a .vsix the way the panel's "Install from VSIX..." does (in the
background). Checks: the host starts, the extension activates, its command runs, the "Restart required" banner is
gone; disabling + enabling keeps working. With a Claude Code .vsix (2nd argument or RADIDE_TEST_CLAUDE_VSIX) a second
IDE-less scratch root checks that Claude Code activates right after its install too.
Exit code = number of failures."""
from __future__ import annotations

import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_install_activate"
CLAUDE = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("RADIDE_TEST_CLAUDE_VSIX", "")
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
os.environ["RADIDE_VSX_ROOT"] = str(SCRATCH / "vsxroot")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["CLAUDE_CONFIG_DIR"] = str(SCRATCH / "claude-config")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(REPO))

RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:300]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:300]}]" if detail else ""), flush=True)


def pack(src: Path, out: Path) -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in src.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".py":
                z.write(f, "extension/" + f.relative_to(src).as_posix())
    return out


VSIX = pack(HERE / "hello-commands", SCRATCH / "radide-test.hello-commands-0.0.1.vsix")

__import__("PyQt6.QtWebEngineWidgets")  # before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

app = QApplication(sys.argv[:1])
ORG = os.environ.get("RADIDE_TEST_ORG", "RADIDE-TEST-LEFTOVER")
QCoreApplication.setOrganizationName(ORG)
QCoreApplication.setApplicationName(ORG + "-VSXINSTALL")
QSettings().clear()


def wait(cond, timeout=20.0, step=0.05):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(step)
    app.processEvents()
    return False


def call(fn, timeout=15.0):
    box = {}
    fn(lambda *a: box.setdefault("v", a[0] if len(a) == 1 else a))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def answer_dialogs():
    w = QApplication.activeModalWidget()
    if isinstance(w, QMessageBox):
        w.buttons()[0].click()
    elif isinstance(w, QDialog):
        w.reject()


timer = QTimer()
timer.timeout.connect(answer_dialogs)
timer.start(300)

from radide import vsx  # noqa: E402
from radide.app import MainWindow  # noqa: E402
from radide.features import vsx_market  # noqa: E402

win = MainWindow()
win.resize(1300, 850)
win.show()
svc = getattr(win, "vsx_host", None)
check(svc is not None, "feature installed (win.vsx_host)")
wait(lambda: False, 2.5)                                  # past the delayed start-up start (1.5 s)
check(not vsx.list_installed() and not svc.host.running(), "empty extensions root: no extension host",
      svc.host.running())

vsx_market.show_view(win)
view = vsx_market._view(win)
check(view is not None, "Extensions view")
view.install_from_vsix(str(VSIX))                          # the panel's "Install from VSIX..." (background thread)
check(wait(lambda: vsx.get("radide-test.hello-commands") is not None, 30), "installed through the Extensions view")
check(wait(lambda: svc.host.running() and svc.host.init_result is not None, 40),
      "extension host started after the install (no IDE restart)", svc.host.init_result)
check(wait(lambda: svc.activation.get("radide-test.hello-commands") == "active", 30), "hello-commands activated",
      svc.activation)
state = call(lambda cb: svc.execute("helloCommands.state", [], cb))
check(isinstance(state, dict) and state.get("runs") == 1, "its command runs", state)
check(wait(lambda: not vsx.restart_required() and view.banner.isHidden(), 5), "no 'Restart required' banner",
      vsx.restart_required())
from radide.features import command_palette as cp  # noqa: E402

check(wait(lambda: "helloCommands.sayHello" in {c.id for c in cp.commands()}, 5), "command in the Command Palette")
pid = (svc.host.init_result or {}).get("pid")

# a second install while the host runs keeps it (other extensions' sessions) and offers Reload
view.set_enabled("radide-test.hello-commands", False)
wait(lambda: False, 1.0)
check(svc.host.running() and (svc.host.init_result or {}).get("pid") == pid, "disable: running host kept")
view.set_enabled("radide-test.hello-commands", True)
wait(lambda: False, 1.0)
check(svc.host.running() and (svc.host.init_result or {}).get("pid") == pid, "enable with a running host: no restart")
win.grab().save(str(SCRATCH / "vsx_install_activate.png"))

# ---------------------------------------------------------------- Claude Code (optional, real .vsix)
if CLAUDE and Path(CLAUDE).is_file():
    svc.stop()
    from radide.vsx import manager as M  # noqa: E402

    M.uninstall("radide-test.hello-commands", force=True)
    wait(lambda: False, 1.0)
    check(not svc.host.running(), "host stopped (no extension with code left)")
    svc.activation.clear()
    view.install_from_vsix(CLAUDE)
    check(wait(lambda: vsx.get("anthropic.claude-code") is not None, 120), "Claude Code installed through the view")
    check(wait(lambda: svc.host.running() and svc.activation.get("anthropic.claude-code") == "active", 120),
          "Claude Code activated right after the install", svc.activation)
    ids = {c.id for c in cp.commands()}
    check(any(i.startswith("claude-vscode.") or i.startswith("claude-code.") for i in ids), "Claude Code commands",
          sorted(i for i in ids if "claude" in i)[:5])
else:
    print("SKIP Claude Code (no .vsix given)")

svc.stop()
timer.stop()
try:
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for ok, _n, _d in RESULTS if not ok)
print(f"\n{len(RESULTS) - fails}/{len(RESULTS)} passed", flush=True)
os._exit(fails)
