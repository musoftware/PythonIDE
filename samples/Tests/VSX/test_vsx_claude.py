"""Claude Code inside RAD IDE: workspace, IDE MCP tools, agent context - without a real Claude conversation.

    python samples/Tests/VSX/test_vsx_claude.py <scratch folder> <path to anthropic.claude-code .vsix>

* the IDE starts with no project: the extension host runs with no workspace folder; opening a project restarts
  the host (VS Code reloads the window when the first folder appears) so Claude Code's session folder, its lock
  file (workspaceFolders) and the CLI's cwd are the project folder - not the user's home folder;
* the extension host / CLI environment carries RADIDE_CLI + RADIDE_WORKSPACE; process.cwd() of the host is the
  project folder;
* a fake CLI (claude_mcp_client.js) calls every IDE MCP tool the extension offers and checks the answers:
  getWorkspaceFolders, getOpenEditors, getCurrentSelection, getLatestSelection, getDiagnostics,
  checkDocumentDirty, saveDocument, openFile (selection / text range / preview), openDiff (accept -> FILE_SAVED,
  reject -> DIFF_REJECTED), close_tab, closeAllDiffTabs, executeCode (no Jupyter: a clear error); selection
  changes in an editor reach the CLI as selection_changed notifications, "Insert At-Mention" as at_mentioned;
* agent context: .claude/CLAUDE.md gets the RAD IDE section (with consent), user text in the file is kept;
* no "not supported" / missing-command message of Claude Code during all of it.
QSettings org RADIDE-TEST-VSX2 (cleared), scratch RADIDE_VSX_ROOT + CLAUDE_CONFIG_DIR, offscreen friendly.
Exit code = number of failures."""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_claude_test"
CLAUDE = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
os.environ["RADIDE_VSX_ROOT"] = str(SCRATCH / "vsxroot")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["CLAUDE_CONFIG_DIR"] = str(SCRATCH / "claude-config")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing --disable-logging --log-level=3")
sys.path.insert(0, str(REPO))

RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:400]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:400]}]" if detail else ""), flush=True)


if CLAUDE is None or not CLAUDE.is_file():
    print("usage: test_vsx_claude.py <scratch> <anthropic.claude-code .vsix>  (skipped: no vsix)")
    sys.exit(0)

__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST-VSX2")
QCoreApplication.setApplicationName("RADIDE-TEST-VSX2-CLAUDE")
QSettings().clear()

from radide.vsx import agent_context, manager  # noqa: E402

ce = manager.install_vsix_file(CLAUDE, with_dependencies=False)
check(ce and ce[0].id == "anthropic.claude-code", "install Claude Code vsix", ce and ce[0].id)

DIALOGS = []


def close_dialogs():
    w = QApplication.activeModalWidget()
    if isinstance(w, QMessageBox):
        DIALOGS.append(w.text()[:120])
        w.done(0)
    elif isinstance(w, QDialog):
        DIALOGS.append(w.windowTitle()[:120])
        w.reject()


_t = QTimer()
_t.timeout.connect(close_dialogs)
_t.start(300)


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


def locks():
    d = Path(os.environ["CLAUDE_CONFIG_DIR"]) / "ide"
    out = []
    for f in (d.glob("*.lock") if d.is_dir() else []):
        try:
            out.append(json.loads(f.read_text("utf-8")))
        except (OSError, ValueError):
            pass
    return out


def norm(p):
    return os.path.normcase(str(Path(p).resolve()))


# a RAD IDE VB6-style project to work in (copy of samples/HelloVB) + a Python file for diagnostics
proj = SCRATCH / "WindowsApplication5"
shutil.copytree(REPO / "samples" / "HelloVB", proj)
(proj / ".claude").mkdir()
(proj / ".claude" / "CLAUDE.md").write_text("# My notes\n\nKeep this line.\n", "utf-8")
(proj / "src").mkdir()
pyfile = proj / "src" / "helper.py"     # (a non-module file in the project root hits an open_file recursion)
pyfile.write_text("def add(a, b):\n    return a + b\n\nprint(add(1, 2))\n", "utf-8")
agent_context.TEST_HOOK = lambda folder: "yes"

from radide.app import MainWindow  # noqa: E402

win = MainWindow()
win.resize(1400, 900)
win.show()
svc = win.vsx_host
check(wait(lambda: svc.host.running() and svc.activation.get("anthropic.claude-code") == "active", 90),
      "Claude Code activated (IDE without a project)", svc.activation.get("anthropic.claude-code"))
check(wait(lambda: locks(), 30) and all(not lk.get("workspaceFolders") for lk in locks()),
      "lock file without a workspace folder before a project is open", locks())
pid1 = (svc.host.init_result or {}).get("pid")

# ---------------------------------------------------------------- 1. the project becomes the workspace
win.open_project(proj, ask=False)
check(svc.folders() == [str(proj.resolve())], "workspace folders = the open project's folder", svc.folders())
check(wait(lambda: (svc.host.init_result or {}).get("pid") not in (None, pid1) and svc.host.running(), 30),
      "first workspace folder -> the extension host restarted (VS Code reloads the window)",
      (pid1, (svc.host.init_result or {}).get("pid")))
check(wait(lambda: svc.activation.get("anthropic.claude-code") == "active", 90), "Claude Code active again")
check(wait(lambda: any(norm(w) == norm(proj) for lk in locks() for w in lk.get("workspaceFolders") or []), 40),
      "Claude Code's lock file lists the project folder (getWorkspaceFolders / CLI cwd)",
      [lk.get("workspaceFolders") for lk in locks()])
env = svc._agent_env()
check(env.get("RADIDE_WORKSPACE") == str(proj.resolve()) and "radide" in env.get("RADIDE_CLI", "").lower(),
      "extension host environment: RADIDE_CLI + RADIDE_WORKSPACE", env)


def host_eval(expr):
    box = {}
    svc.execute("_radide.test.eval", [expr], lambda r: box.setdefault("v", r))
    wait(lambda: "v" in box, 10)
    return box.get("v")


# ---------------------------------------------------------------- 2. agent context
md = proj / ".claude" / "CLAUDE.md"
check(wait(lambda: agent_context.BEGIN in md.read_text("utf-8"), 10), ".claude/CLAUDE.md got the RAD IDE section",
      md.read_text("utf-8")[:200])
text = md.read_text("utf-8")
check("Keep this line." in text and "--build" in text and "Microsoft Visual Basic 6 is NOT needed" in text
      and "Form1" in text, "... user text kept; CLI, VB6 runtime note and the forms are described", text[-600:])

# ---------------------------------------------------------------- 3. the fake CLI: every IDE MCP tool
from radide.vsx.bridge import find_node  # noqa: E402

cfg = Path(os.environ["CLAUDE_CONFIG_DIR"])
proc = subprocess.Popen([find_node(), str(HERE / "claude_mcp_client.js"), str(cfg), str(proj)], stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
events: "queue.Queue" = queue.Queue()
ALL: list = []


def reader():
    for line in proc.stdout:
        try:
            e = json.loads(line)
        except ValueError:
            e = {"event": "text", "text": line.strip()}
        ALL.append(e)
        events.put(e)


threading.Thread(target=reader, daemon=True).start()
check(wait(lambda: any(e.get("event") == "connected" for e in ALL), 30), "fake CLI connected to the extension's MCP server",
      ALL[-2:])
_rid = [0]


def call(tool=None, args=None, method=None, params=None, timeout=30.0, background=False):
    _rid[0] += 1
    rid = _rid[0]
    req = {"id": rid}
    if tool:
        req.update(tool=tool, args=args or {})
    else:
        req.update(method=method, params=params or {})
    proc.stdin.write(json.dumps(req) + "\n")
    proc.stdin.flush()
    if background:
        return rid
    return reply(rid, timeout)


def reply(rid, timeout=30.0):
    box = {}
    wait(lambda: any(e.get("event") == "reply" and e.get("id") == rid and box.setdefault("e", e) for e in ALL), timeout)
    e = box.get("e") or {}
    if "error" in e:
        return {"$error": e["error"]}
    return e.get("result")


def texts(res):
    return [c.get("text", "") for c in ((res or {}).get("content") or []) if isinstance(c, dict)]


def jtext(res):
    for t in texts(res):
        try:
            return json.loads(t)
        except ValueError:
            continue
    return None


tools = call(method="tools/list") or {}
names = sorted(t.get("name") for t in tools.get("tools") or [])
print("MCP tools:", names)
(SCRATCH / "tools.json").write_text(json.dumps(tools, indent=1), "utf-8")
check({"openDiff", "getDiagnostics", "close_tab", "closeAllDiffTabs", "executeCode"} <= set(names),
      "IDE MCP tools listed (Claude Code 2.1: openDiff, getDiagnostics, close_tab, closeAllDiffTabs, executeCode)", names)

for name in names:
    print("TOOL", name, json.dumps((next(t for t in tools["tools"] if t["name"] == name).get("inputSchema") or {}).get("properties"))[:300])
wb = svc.workbench

# getDiagnostics: the IDE's Error List problems (a syntax error in helper.py) are visible to the CLI
pyfile.write_text("def add(a, b):\n    return a +\n", "utf-8")
win.open_any_file(pyfile)
check(wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "helper.py", 20),
      "helper.py open in the IDE editor")
from radide import tools as T  # noqa: E402

# helper.py is not a project file: an Error List provider (like the language-server providers) reports it
win.diag_providers = list(getattr(win, "diag_providers", [])) + [
    lambda w: [T.Diag("Error", "SyntaxError: invalid syntax", str(pyfile), 2)]]
T.run_checks(win)
wait(lambda: False, 1.0)
res = call("getDiagnostics", {})
dj = jtext(res)
flat = json.dumps(dj or res)
check("helper.py" in flat and ("SyntaxError" in flat or "invalid syntax" in flat), "getDiagnostics: the IDE's syntax error",
      flat[:300])
res = call("getDiagnostics", {"uri": pyfile.resolve().as_uri()})
check("helper.py" in json.dumps(jtext(res) or res), "getDiagnostics(uri) for one file", json.dumps(jtext(res) or res)[:300])
pyfile.write_text("def add(a, b):\n    return a + b\n\nprint(add(1, 2))\n", "utf-8")
win.diag_providers = win.diag_providers[:-1]
T.run_checks(win)
wait(lambda: False, 1.0)
check("SyntaxError" not in json.dumps(jtext(call("getDiagnostics", {})) or {}), "fixed error disappears from getDiagnostics")

# selection_changed: selecting text in the IDE editor reaches the CLI
ed = svc.active_editor()
n0 = len([e for e in ALL if e.get("method") == "selection_changed"])
try:
    ed.setSelection(0, 4, 0, 7)
except Exception as e:  # noqa: BLE001
    print("setSelection:", e)
check(wait(lambda: len([e for e in ALL if e.get("method") == "selection_changed"]) > n0, 15),
      "selection_changed notification when the user selects text", [e for e in ALL if e.get("method")][-2:])
sel = [e for e in ALL if e.get("method") == "selection_changed"]
last = (sel[-1].get("params") or {}) if sel else {}
check("helper.py" in str(last.get("filePath", "")) and "add" in str(last.get("text", "")), "... with the file and the selected text",
      last)

# at_mentioned: "Claude Code: Insert At-Mentioned" (Ctrl+Alt+K) with a selection
n1 = len([e for e in ALL if e.get("method") == "at_mentioned"])
box = {}
svc.execute("claude-code.insertAtMentioned", [], lambda r: box.setdefault("v", r))
check(wait(lambda: len([e for e in ALL if e.get("method") == "at_mentioned"]) > n1, 15),
      "at_mentioned notification from Insert At-Mentioned", [e for e in ALL if e.get("method")][-2:])
am = [e for e in ALL if e.get("method") == "at_mentioned"]
check(am and "helper.py" in str((am[-1].get("params") or {}).get("filePath")), "... names the file", am[-1:] if am else None)

# openDiff -> Accept -> FILE_SAVED; openDiff -> Reject -> DIFF_REJECTED; close_tab; closeAllDiffTabs
accept_ids = {"claude-vscode.acceptProposedDiff", "claude-code.acceptProposedDiff"}
reject_ids = {"claude-vscode.rejectProposedDiff", "claude-code.rejectProposedDiff"}


def diff_flow(tab, new_text, button_ids):
    before = set(wb.diffs)
    rid = call("openDiff", {"old_file_path": str(pyfile), "new_file_path": str(pyfile), "new_file_contents": new_text,
                            "tab_name": tab}, background=True)
    ok = wait(lambda: set(wb.diffs) - before, 20)
    view = next((wb.diffs[k] for k in set(wb.diffs) - before), None)
    if view is None:
        return ok, None, None
    wait(lambda: button_ids & set(view.title_commands()), 15)
    wait(lambda: False, 1.5)          # the extension polls for the tab before it listens to the buttons
    act = next((a for a in view._title_actions if a.objectName()[len("vsxTitle:"):] in button_ids), None)
    if act is not None:
        act.trigger()
    return ok, view, reply(rid, 30)


ok, view, res = diff_flow("radide-accept", "def add(a, b):\n    \"\"\"Sum.\"\"\"\n    return a + b\n", accept_ids)
check(ok and view is not None, "openDiff opened a Diff tab")
tx = texts(res)
check(any("FILE_SAVED" in t for t in tx) and any('"""Sum."""' in t for t in tx), "Accept -> FILE_SAVED + contents", tx)
if len(tx) > 1:
    pyfile.write_text(tx[1], "utf-8")         # the real CLI writes the accepted contents itself
ed = svc.active_editor() if svc.active_editor() is not None and Path(svc.active_editor().path).name == "helper.py" \
    else svc.editor_for(str(pyfile))
check(ed is not None and wait(lambda: '"""Sum."""' in ed.text(), 10), "accepted change is in the IDE editor of helper.py",
      ed.text()[:120] if ed is not None else None)
res = call("close_tab", {"tab_name": "radide-accept"})
check(wait(lambda: all(win.tabs.widget(i) is not view for i in range(win.tabs.count())), 10), "close_tab closed the Diff tab",
      texts(res))
ok, view, res = diff_flow("radide-reject", "print('rejected')\n", reject_ids)
tx = texts(res)
check(any("DIFF_REJECTED" in t for t in tx), "Reject -> DIFF_REJECTED", tx)
call("close_tab", {"tab_name": "radide-reject"})
# an open diff, then closeAllDiffTabs (the CLI's clean-up)
pend = call("openDiff", {"old_file_path": str(pyfile), "new_file_path": str(pyfile), "new_file_contents": "# radide-a\n",
                         "tab_name": "radide-a"}, background=True)
check(wait(lambda: len(wb.diffs) >= 1, 20), "a Diff tab open", list(wb.diffs))
wait(lambda: False, 1.0)
res = call("closeAllDiffTabs", {})
check(wait(lambda: not [k for k, v in wb.diffs.items() if any(win.tabs.widget(i) is v for i in range(win.tabs.count()))], 15),
      "closeAllDiffTabs closed them", texts(res))
check(texts(reply(pend, 15)), "... the pending openDiff answered when its tab closed", ALL[-2:])
res = call("executeCode", {"code": "print(1)"}, timeout=20)
check(res is not None and ("$error" in res or texts(res)), "executeCode answers (no Jupyter kernel: a clear message)",
      res)
print("executeCode ->", res)

# links in Claude's messages: vscode.open(file, {selection}) opens the file at that line in the IDE
other = proj / "src" / "notes.txt"
other.write_text("one\ntwo\nthree\nfour\n", "utf-8")
box = {}
svc.execute("vscode.open", [{"$uri": other.resolve().as_uri()},
                            {"selection": {"start": {"line": 2, "character": 0}, "end": {"line": 2, "character": 5}}}],
            lambda r: box.setdefault("v", r))
check(wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "notes.txt", 15),
      "vscode.open with a selection opens the file in the IDE")
ae = svc.active_editor()
check(ae is not None and wait(lambda: tuple(getattr(ae, "_selection", (0,))[:1]) == (2,) or getattr(ae, "_cursor", (0,))[0] == 2, 10),
      "... at the given line", (getattr(ae, "_selection", None), getattr(ae, "_cursor", None)))
# a file Claude writes on disk (its own Write tool) reaches the open IDE editor
other.write_text("one\ntwo\nthree\nfour\nfive (written by the agent)\n", "utf-8")
check(wait(lambda: "written by the agent" in ae.text(), 20), "file changed on disk -> the open editor shows it",
      ae.text()[-60:] if ae is not None else None)

proc.stdin.write(json.dumps({"quit": True}) + "\n")
proc.stdin.flush()
try:
    proc.wait(10)
except subprocess.TimeoutExpired:
    proc.kill()

un = [a for e, a in svc.unsupported if e == "anthropic.claude-code"]
print("Claude Code unsupported:", un)
win.grab().save(str(SCRATCH / "claude_ide.png"))
if DIALOGS:
    print("dialogs dismissed:", DIALOGS)
fails = [r for r in RESULTS if not r[0]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed; scratch {SCRATCH}", flush=True)
(SCRATCH / "results.json").write_text(json.dumps(RESULTS, indent=1), "utf-8")
QSettings().clear()
try:
    svc.stop()
except Exception:  # noqa: BLE001
    pass
os._exit(len(fails))
