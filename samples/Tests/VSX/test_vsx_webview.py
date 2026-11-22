"""Webviews of VS Code extensions inside the real RAD IDE main window.

    python samples/Tests/VSX/test_vsx_webview.py <scratch folder> [path to anthropic.claude-code .vsix]

Installs hello-webview (a sidebar WebviewView + a WebviewPanel whose page loads an ES module and a
stylesheet through webview.asWebviewUri) into <scratch>/vsxroot and checks: the view appears under
View > Extension Views, both pages load their module, messages flow both ways, the --vscode-* theme
variables and the body theme class are set, closing the panel disposes it. When a Claude Code .vsix is
given (or found in the market cache) it is installed too and its sidebar webview must render.
Screenshots via widget.grab(); exit code = number of failures."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_webview_test"
CLAUDE_VSIX = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
os.environ["RADIDE_VSX_ROOT"] = str(SCRATCH / "vsxroot")
os.environ["RADIDE_NO_BROWSER"] = "1"
sys.path.insert(0, str(REPO))

RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:300]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:300]}]" if detail else ""), flush=True)


def pack(src: Path, out: Path) -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/'
                   'json"/></Types>')
        for f in src.rglob("*"):
            if f.is_file():
                z.write(f, "extension/" + f.relative_to(src).as_posix())
    return out


__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
QSettings().clear()

from radide.vsx import manager  # noqa: E402

exts = manager.install_vsix_file(pack(HERE / "hello-webview", SCRATCH / "radide-test.hello-webview-0.0.1.vsix"),
                                 with_dependencies=False)
check(exts and exts[0].enabled, "install hello-webview")
if CLAUDE_VSIX and CLAUDE_VSIX.is_file():
    ce = manager.install_vsix_file(CLAUDE_VSIX, with_dependencies=False)
    check(ce and ce[0].id == "anthropic.claude-code", "install Claude Code vsix", ce and ce[0].id)

from radide.app import MainWindow  # noqa: E402


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


def js(web, code, timeout=5.0):
    box = {}
    web.page().runJavaScript(code, lambda v: box.setdefault("v", v))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def command(svc, cmd, args=None, timeout=10.0):
    box = {}
    svc.execute(cmd, args or [], lambda r: box.setdefault("v", r))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


DIALOGS = []


def close_dialogs():
    """Extensions (Claude Code) may show modal messages: record and dismiss them so the test never blocks."""
    from PyQt6.QtWidgets import QDialog, QMessageBox
    w = QApplication.activeModalWidget()
    if isinstance(w, QMessageBox):
        DIALOGS.append(w.text()[:120])
        w.reject() if w.escapeButton() is None else w.escapeButton().click()
        if w.isVisible():
            w.done(0)
    elif isinstance(w, QDialog):
        DIALOGS.append(w.windowTitle()[:120])
        w.reject()


from PyQt6.QtCore import QTimer  # noqa: E402

_dlg_timer = QTimer()
_dlg_timer.timeout.connect(close_dialogs)
_dlg_timer.start(300)

win = MainWindow()
win.resize(1400, 900)
win.show()
svc = getattr(win, "vsx_host", None)
check(svc is not None and hasattr(svc, "webviews"), "webview manager installed")
check(wait(lambda: svc.host.running() and svc.host.init_result is not None, 30), "extension host started")
check(wait(lambda: "radide-test.hello-webview" in svc.activation, 20), "hello-webview activated", svc.activation)
check(wait(lambda: "helloWebview.view" in svc.webviews.providers, 10), "webview view provider registered",
      svc.webviews.providers)

menu = getattr(svc, "_views_menu", None)
titles = [a.text() for a in menu.actions()] if menu else []
check("Hello View" in titles, "View > Extension Views lists the webview view", titles)

# ---------------------------------------------------------------- sidebar view
svc.webviews.show_view("helloWebview.view")
check(wait(lambda: "helloWebview.view" in svc.webviews.view_handles, 15), "view resolved (resolveWebviewView)")
vw = svc.webviews.items.get(svc.webviews.view_handles.get("helloWebview.view"))
check(vw is not None and vw.web is not None, "view has a QWebEngineView")
check(wait(lambda: js(vw.web, "document.getElementById('out') && document.getElementById('out').textContent", 2)
           == "echo: view hello", 20), "view: ES module loaded, ready -> echo round trip",
      js(vw.web, "document.body && document.body.innerText", 2))
msgs = []
check(wait(lambda: (msgs.append(command(svc, "helloWebview.messages", timeout=3)) or True)
           and any(m.get("type") == "echoed" and m.get("from") == "view" for m in (msgs[-1] or [])), 10),
      "view -> extension messages (ready, echoed)", msgs[-1:] if msgs else None)
echoed = next((m for m in (msgs[-1] or []) if m.get("type") == "echoed"), {})
check(echoed.get("bg", "").startswith("#") and ("vscode-dark" in echoed.get("kind", "")
                                                or "vscode-light" in echoed.get("kind", "")),
      "--vscode-* variables and body theme class", echoed)
check(js(vw.web, "getComputedStyle(document.getElementById('out')).borderTopStyle") == "solid",
      "stylesheet through asWebviewUri applied")
js(vw.web, "document.getElementById('btn').click()")
check(wait(lambda: any(m.get("type") == "clicked" for m in (command(svc, "helloWebview.messages", timeout=3) or [])), 10),
      "button click -> onDidReceiveMessage")
check(vw.state == {"last": "view hello"}, "setState kept on the IDE side", vw.state)
vw.dock.grab().save(str(SCRATCH / "webview_view.png"))

# ---------------------------------------------------------------- panel
n_before = len(svc.webviews.items)
check(command(svc, "helloWebview.openPanel") is True, "createWebviewPanel command ran")
check(wait(lambda: len(svc.webviews.items) > n_before, 10), "panel created in the IDE")
pw = next((w for w in svc.webviews.items.values() if w.kind == "panel"), None)
check(pw is not None and wait(lambda: js(pw.web, "document.getElementById('out').textContent", 2)
                              == "echo: panel hello", 20), "panel: module + message round trip")
check(pw is not None and pw.dock.windowTitle() == "Hello Panel", "panel title", pw and pw.dock.windowTitle())
if pw is not None:
    pw.dock.grab().save(str(SCRATCH / "webview_panel.png"))
    pw.dock.close()
check(wait(lambda: any(m.get("type") == "disposed" for m in (command(svc, "helloWebview.messages", timeout=3) or [])),
           10), "closing the panel dock fires onDidDispose")

# ---------------------------------------------------------------- resource server refuses other files
import urllib.request  # noqa: E402

try:
    urllib.request.urlopen(svc.webviews.server.base + "/f/" + str(REPO / "README.md").replace("\\", "/"), timeout=3)
    check(False, "files outside the extension roots are refused")
except Exception as e:  # noqa: BLE001
    check("404" in str(e), "files outside the extension roots are refused", e)
try:
    urllib.request.urlopen(svc.webviews.server.origin + "/f/x", timeout=3)
    check(False, "requests without the token are refused")
except Exception as e:  # noqa: BLE001
    check("404" in str(e), "requests without the token are refused", e)

# ---------------------------------------------------------------- Claude Code (optional)
if CLAUDE_VSIX and CLAUDE_VSIX.is_file():
    check(wait(lambda: svc.activation.get("anthropic.claude-code") == "active", 60), "Claude Code activated",
          svc.activation.get("anthropic.claude-code"))
    wviews = svc.contributed_webview_views()
    vid = next((v for v in wviews if v.startswith("claudeVSCodeSidebar")), None)
    check(vid is not None, "Claude Code sidebar view listed", wviews)
    if vid:
        svc.webviews.show_view(vid)
        check(wait(lambda: vid in svc.webviews.view_handles, 30), "Claude Code view resolved")
        cw = svc.webviews.items.get(svc.webviews.view_handles.get(vid))
        ok = cw is not None and wait(lambda: (js(cw.web, "document.body ? document.body.innerText.length : 0", 2) or 0)
                                     > 20, 40)
        check(ok, "Claude Code webview rendered text",
              cw and js(cw.web, "document.body ? document.body.innerText.slice(0,200) : ''", 2))
        if cw is not None:
            cw.dock.setFloating(True)
            cw.dock.resize(480, 760)
            wait(lambda: False, 4)
            cw.web.grab().save(str(SCRATCH / "claude_code.png"))
    # the Command Palette entries the user clicks: each must show a Claude webview
    for cmd in ("claude-vscode.sidebar.open", "claude-vscode.editor.open"):
        before = {h for h, w in svc.webviews.items.items() if w.dock.isVisible()}
        for w in svc.webviews.items.values():
            w.dock.hide()
        reply = {}
        svc.execute(cmd, [], lambda r, b=reply: b.setdefault("r", r))
        shown = wait(lambda: any(w.dock.isVisible() for w in svc.webviews.items.values()), 20)
        check(shown, f"{cmd} shows a Claude webview",
              (reply.get("r"), [(w.view_type, w.dock.isVisible()) for w in svc.webviews.items.values()], before))
    for ext, api in svc.unsupported:
        if ext == "anthropic.claude-code":
            print("  unsupported:", api)

if DIALOGS:
    print("  dialogs dismissed:", DIALOGS)
fails = [r for r in RESULTS if not r[0]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed; screenshots in {SCRATCH}", flush=True)
(SCRATCH / "results.json").write_text(json.dumps(RESULTS, indent=1), "utf-8")
QSettings().clear()
win.close()
QSettings().clear()
sys.stdout.flush()
os._exit(len(fails))
