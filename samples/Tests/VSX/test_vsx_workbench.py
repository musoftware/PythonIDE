"""Workbench APIs of VS Code extensions inside the real RAD IDE main window (the former no-op mocks).

    python samples/Tests/VSX/test_vsx_workbench.py <scratch folder> [Claude Code extension folder or .vsix]

Installs workbench-api (MIT, written for this test) into <scratch>/vsxroot and checks, through the IDE:
workspace.registerFileSystemProvider + workspace.fs + documents on the provider scheme (edit, save, reload),
vscode.diff of a file against a provider document - a Diff tab with the extension's editor/title buttons
(accept / reject like Claude Code), editing the proposed side, tabGroups (tabs, active tab, close from both
sides), virtual documents shown in an editable temp copy, registerUriHandler, file decorations, process /
pseudo terminals in the "Extension Terminals" dock (input, exit codes, environmentVariableCollection, links,
shell integration), tasks, authentication providers (consent dialog), notebooks, custom editors,
updateWorkspaceFolders, visible ranges, editor options and the no-UI objects (comments, tests, scm, chat).
With a Claude Code extension (folder or .vsix) it also checks that its file system providers / URI handler
register and that no API it uses at start-up is unsupported.
Screenshots via widget.grab() only; exit code = number of failures."""
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
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_workbench_test"
CLAUDE = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
os.environ["RADIDE_VSX_ROOT"] = str(SCRATCH / "vsxroot")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-logging --log-level=3")   # many web views offscreen
os.environ["CLAUDE_CONFIG_DIR"] = str(SCRATCH / "claude-config")     # Claude Code's lock files stay in the scratch dir
sys.path.insert(0, str(REPO))

RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:300]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:300]}]" if detail else ""), flush=True)


def pack(src: Path, out: Path, skip=()) -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/'
                   'json"/></Types>')
        for f in src.rglob("*"):
            rel = f.relative_to(src).as_posix()
            if f.is_file() and not any(rel.startswith(s) for s in skip):
                z.write(f, "extension/" + rel)
    return out


__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
QSettings().clear()

from radide.vsx import manager  # noqa: E402

exts = manager.install_vsix_file(pack(HERE / "workbench-api", SCRATCH / "radide-test.workbench-api-0.0.1.vsix"),
                                 with_dependencies=False)
check(exts and exts[0].enabled, "install workbench-api")
if CLAUDE is not None and CLAUDE.exists():
    vsix = CLAUDE
    if CLAUDE.is_dir():                          # an unpacked extension: pack it without the 370 MB CLI binary
        src = CLAUDE / "extension" if (CLAUDE / "extension" / "package.json").is_file() else CLAUDE
        vsix = pack(src, SCRATCH / "anthropic.claude-code.vsix", skip=("resources/native-binary",))
    ce = manager.install_vsix_file(vsix, with_dependencies=False)
    check(ce and ce[0].id == "anthropic.claude-code", "install Claude Code", ce and ce[0].id)

from radide.app import MainWindow  # noqa: E402

AUTO = {"answers": []}


def answer_dialogs():
    w = QApplication.activeModalWidget()
    if isinstance(w, QMessageBox):
        allow = [b for b in w.buttons() if b.text().replace("&", "") == "Allow"]
        AUTO["answers"].append(w.text())
        (allow[0] if allow else w.buttons()[0]).click()


timer = QTimer()
timer.timeout.connect(answer_dialogs)
timer.start(200)


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


def command(cmd, *args, timeout=20.0):
    box = {}
    svc.execute(cmd, list(args), lambda r: box.setdefault("v", r))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def run(step, *args, timeout=20.0):
    return command("wbTest.run", step, *args, timeout=timeout)


def report():
    return command("wbTest.report", timeout=10) or {}


def host_request(method, params, timeout=20.0):
    box = {}
    svc.host.request(method, params, lambda r: box.setdefault("v", r))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


win = MainWindow()
win.resize(1400, 900)
win.show()
svc = getattr(win, "vsx_host", None)
check(svc is not None and hasattr(svc, "workbench"), "workbench UI installed (svc.workbench)")
check(wait(lambda: svc.host.running() and svc.host.init_result is not None, 30), "extension host started")
check(wait(lambda: "radide-test.workbench-api" in svc.activation, 30), "workbench-api activated", svc.activation)
wb = svc.workbench

ws = SCRATCH / "ws"
ws.mkdir()
notes = ws / "notes.txt"
notes.write_text("line one\nline two\nline three\n", "utf-8")

# ---------------------------------------------------------------- FileSystemProvider + workspace.fs
r = run("fs", str(ws / "copied.txt")) or {}
check(r.get("read") == "alpha" and r.get("stat") == 5, "workspace.fs writeFile / readFile / stat via the provider", r)
check("a.txt" in (r.get("dir") or []) and "dir" in (r.get("dir") or []), "workspace.fs.readDirectory via the provider", r.get("dir"))
check(r.get("renamed") and r.get("copied") == "alpha" and r.get("deleted"), "rename / copy / delete via the provider", r)
check(r.get("missing") == "FileNotFound", "FileSystemError from the provider reaches the caller", r.get("missing"))
check(r.get("writable") == [True, True, None], "isWritableFileSystem(provider / file / unknown)", r.get("writable"))
check((ws / "copied.txt").read_text("utf-8") == "alpha", "copy from a provider scheme to disk")
check("wbmem" in wb.fs_schemes, "fs/registered reached the IDE", wb.fs_schemes)

r = run("doc") or {}
check(r.get("text") == "one\ntwo\n" and r.get("scheme") == "wbmem", "openTextDocument on a provider scheme", r)
check(r.get("applied") and r.get("dirty") is True, "applyEdit on a provider document (dirty)", r)
check(r.get("saved") is True and r.get("provider") == "zero\none\ntwo\n" and r.get("saves", 0) >= 1,
      "TextDocument.save() -> FileSystemProvider.writeFile + onDidSaveTextDocument", r)
check(r.get("reloaded") is True, "provider onDidChangeFile reloads the open document", r)

# ---------------------------------------------------------------- vscode.diff + editor/title accept (Claude Code's flow)
ed_notes = win.open_any_file(notes)
check(ed_notes is not None and wait(lambda: ed_notes._ready, 30), "notes.txt opened in the IDE")
n_tabs = win.tabs.count()
r = run("diff", str(notes), "line one\nline 2 (proposed)\nline three\n") or {}
check(r.get("found") and r.get("label") == "Proposed (wb)", "vscode.diff -> TabInputTextDiff tab within 1 s", r)
check("wbmem" in (r.get("visible") or []), "visibleTextEditors show both diff sides", r.get("visible"))
view = next(iter(wb.diffs.values()), None)
check(view is not None and win.tabs.indexOf(view) >= 0 and win.tabs.count() == n_tabs + 1, "a Diff tab opened in the IDE",
      win.tabs.count())
right_uri = r.get("right")
if view is not None:
    check(wait(lambda: view.right.text == "line one\nline 2 (proposed)\nline three\n" and view.left.text.startswith("line one"), 10),
          "diff sides: file on disk / provider document", (view.left.text[:20], view.right.text[:30]))
    check(wait(lambda: "wbTest.acceptDiff" in view.title_commands(), 10),
          "editor/title buttons follow setContext + resourceScheme (Accept / Reject)", view.title_commands())
    wait(lambda: view._ready, 20)
    view._on_changed("right", "line one\nline 2 (edited by the user)\nline three\n")      # the user edits the proposal
    st = run("virtualText", right_uri) or {}
    check(st.get("text") == "line one\nline 2 (edited by the user)\nline three\n" and st.get("dirty"),
          "edits in the diff reach the extension's document", st)
    view.grab().save(str(SCRATCH / "diff_tab.png"))
    act = next((a for a in view._title_actions if a.objectName() == "vsxTitle:wbTest.acceptDiff"), None)
    if act is not None:
        act.trigger()
    st = {}
    check(wait(lambda: (st.update(run("diffState", timeout=5) or {}) or True) and st.get("result"), 15),
          "Accept button ran the extension command", st)
    res = st.get("result") or {}
    check(res.get("accepted") and res.get("viaUri") and res.get("text", "").find("edited by the user") > 0,
          "command got the resource Uri and the edited text", res)
    check(res.get("closed") is True and res.get("after") == 0, "tabGroups.close(diff tab) from the extension", res)
    check(wait(lambda: view.diff_id not in wb.diffs and all(win.tabs.widget(i) is not view for i in range(win.tabs.count())), 5),
          "the IDE closed the Diff tab")
    check(not any(t["kind"] == "diff" for t in st.get("tabs") or []), "diff tab gone from tabGroups", st.get("tabs"))

# a second diff closed by the user = rejected
r = run("diff", str(notes), "another proposal\n") or {}
view2 = next(iter(wb.diffs.values()), None)
check(r.get("found") and view2 is not None, "second vscode.diff", r)
if view2 is not None:
    win._close_tab(win.tabs.indexOf(view2))
    st = {}
    check(wait(lambda: (st.update(run("diffState", timeout=5) or {}) or True)
               and not any(t["kind"] == "diff" for t in st.get("tabs") or []), 10),
          "closing the Diff tab in the IDE removes it from tabGroups (onDidChangeTabs)", st.get("tabs"))

# ---------------------------------------------------------------- tabGroups
r = run("tabs") or {}
names = [t["label"] for t in r.get("tabs") or []]
check("notes.txt" in names and r.get("events", 0) > 0, "tabGroups lists the IDE's text tabs + onDidChangeTabs fired", r)
win.tabs.setCurrentWidget(win.tabs.widget(next(i for i in range(win.tabs.count())
                                                 if wb._widget_editor(win.tabs.widget(i)) is ed_notes)))
check(wait(lambda: (run("tabs", timeout=5) or {}).get("active") == "notes.txt", 10), "active tab follows the IDE's current tab")

# ---------------------------------------------------------------- virtual document in an editable temp copy
r = run("showVirtual") or {}
check(r.get("tab") and r["tab"]["kind"] == "text" and r.get("active") == r.get("uri"),
      "showTextDocument(provider document): TabInputText + activeTextEditor", r)


def shown_editor():
    for v in svc.live_editors():
        if "shown.txt" in str(v.path) and getattr(v, "_ready", False):
            return v
    return None


check(wait(lambda: shown_editor() is not None and "shown text" in shown_editor().text(), 30), "temp copy opened in an IDE editor")
vpath = shown_editor()
if vpath is not None:
    vpath.setText("edited in the IDE\n")
    svc.sync_text(vpath.path, vpath.text())
    check(wait(lambda: ((run("virtualText", r.get("uri"), timeout=5) or {}).get("text") == "edited in the IDE\n"), 10),
          "editing the temp copy changes the extension's document")
    svc._saved(vpath)
    check(wait(lambda: ((run("virtualText", r.get("uri"), timeout=5) or {}).get("provider") == "edited in the IDE\n"), 10),
          "Ctrl+S in the temp copy writes through the FileSystemProvider")

# ---------------------------------------------------------------- URI handler
box = {}
wb.handle_uri("radide://radide-test.workbench-api/hello?name=RAD", lambda res: box.setdefault("v", res))
check(wait(lambda: "v" in box, 15) and (box.get("v") or {}).get("ok"), "radide:// URI delivered (uri/handle)", box)
rep = report()
check(any(u["path"] == "/hello" and u["query"] == "name=RAD" for u in rep.get("uris") or []), "UriHandler.handleUri got the Uri",
      rep.get("uris"))
box = {}
wb.handle_uri("radide://nobody.none/x", lambda res: box.setdefault("v", res))
check(wait(lambda: "v" in box, 10) and not (box.get("v") or {}).get("ok"), "unknown extension URI reports an error", box)

# ---------------------------------------------------------------- file decorations
box = {}
wb.file_decorations([str(notes.resolve())], lambda res: box.setdefault("v", res))
check(wait(lambda: "v" in box, 10) and (box["v"] or {}).get(str(notes.resolve()), {}).get("badge") == "W",
      "registerFileDecorationProvider -> badge / tooltip / colour", box)
wb.refresh_tab_decorations()
i_notes = next(i for i in range(win.tabs.count()) if wb._widget_editor(win.tabs.widget(i)) is ed_notes)
check(wait(lambda: "workbench test badge" in win.tabs.tabToolTip(i_notes), 10), "decoration shown on the editor tab",
      win.tabs.tabToolTip(i_notes))

# ---------------------------------------------------------------- terminals
r = run("termProc") or {}
check(r.get("pid") and r.get("name") == "WB Proc" and r.get("active"), "createTerminal(shellPath): real process, processId", r)
panel = wb.terminals
tv = next((v for v in panel.views.values() if v.info.get("name") == "WB Proc"), None)
check(tv is not None, "terminal tab in the Extension Terminals dock")
if tv is not None:
    check(wait(lambda: "hello-term fromCollection own" in tv.out.toPlainText(), 15),
          "process output + environmentVariableCollection + options.env", tv.out.toPlainText()[-200:])
    tv.input.setText("ping")
    tv.submit()
    check(wait(lambda: "echo:ping" in tv.out.toPlainText(), 10), "IDE input line -> process stdin", tv.out.toPlainText()[-200:])
    panel.dock.grab().save(str(SCRATCH / "terminals.png"))
    run("termSend", "bye")
    check(wait(lambda: ((run("termClosed", timeout=5) or {}).get("proc") or {}).get("code") == 3, 15),
          "sendText -> exit -> onDidCloseTerminal with exitStatus.code", run("termClosed", timeout=5))
    check(wait(lambda: "exited with code 3" in tv.out.toPlainText(), 5), "exit shown in the terminal tab")

run("termPty")
pv = next((v for v in panel.views.values() if v.info.get("name") == "WB Pty"), None)
check(pv is not None and wait(lambda: "pty ready" in pv.out.toPlainText(), 10), "Pseudoterminal: open() + onDidWrite",
      pv.out.toPlainText() if pv else None)
if pv is not None:
    pv.input.setText("abc")
    pv.submit()
    check(wait(lambda: "abc\r" in (report().get("ptyInput") or ""), 10), "IDE input -> Pseudoterminal.handleInput", report().get("ptyInput"))
    res = host_request("terminal/link", {"id": pv.id, "line": "see LINK: target1"})
    check(res is True and report().get("link") == "target1", "terminal link provider (double-click a line)", report().get("link"))
    pv.input.setText("quit")
    pv.submit()
    check(wait(lambda: ((run("termClosed", timeout=5) or {}).get("pty") or {}).get("code") == 7, 10),
          "Pseudoterminal onDidClose(code) -> exitStatus", run("termClosed", timeout=5))

r = run("termShell", timeout=40) or {}
check(r.get("integration") and r.get("started") and r.get("exitCode") == 0 and r.get("output"),
      "shell integration: executeCommand + read() + start / end events", r)
profiles = host_request("terminal/profiles", {}) or []
check(any(p["id"] == "wbTest.profile" for p in profiles), "contributed terminal profiles listed", profiles)
check(host_request("terminal/newFromProfile", {"id": "wbTest.profile"}) is True and
      wait(lambda: any("profile terminal" in v.out.toPlainText() for v in panel.views.values()), 15),
      "terminal from a profile provider")

# ---------------------------------------------------------------- tasks / authentication / notebooks / custom editor
r = run("task", timeout=30) or {}
check(r.get("count") == 1 and r.get("started") == "wb exit 4" and r.get("exitCode") == 4,
      "registerTaskProvider + fetchTasks + executeTask + onDidStartTask / onDidEndTaskProcess", r)
r = run("auth", timeout=30) or {}
check(r.get("silent") and r.get("created") == "User One" and r.get("again") == "s1" and r.get("accounts") == ["u1"],
      "authentication provider: silent / createIfNone (consent dialog) / getAccounts", r)
check(r.get("unknown") == "error" and r.get("unknownSilent") and "wbauth" in (r.get("changes") or []),
      "unknown provider + onDidChangeSessions", r)
check(any("wants to sign in" in a for a in AUTO["answers"]), "consent dialog shown", AUTO["answers"])
nbf = ws / "book.wbnb"
nbf.write_text(json.dumps({"cells": ["print(1)", "x = 2"]}), "utf-8")
r = run("notebook", str(nbf)) or {}
check(r.get("type") == "wbnb" and r.get("cells") == 2 and r.get("first") == "print(1)" and r.get("untitled") == 1,
      "openNotebookDocument through the notebook serializer", r)
cf = ws / "thing.wbc"
cf.write_text("custom content", "utf-8")
n_items = len(svc.webviews.items)
r = run("custom", str(cf)) or {}
check((r.get("resolved") or {}).get("text") == "custom content", "vscode.openWith -> resolveCustomTextEditor", r)
check((r.get("tab") or {}).get("viewType") == "wbTest.custom" and len(svc.webviews.items) > n_items,
      "custom editor in a webview panel, TabInputCustom", r.get("tab"))

# ---------------------------------------------------------------- misc
r = run("misc", str(notes), str(ws)) or {}
check(r.get("comment") and r.get("tests") and r.get("scm") and r.get("chat") and r.get("models") == 0,
      "comments / tests / scm / chat / lm objects without UI", r)
check(r.get("commands") == 4, "commands.getCommands lists the built-in commands", r.get("commands"))
check((r.get("env") or {}).get("uriScheme") == "radide" and (r.get("env") or {}).get("remoteName"), "env values", r.get("env"))
check(r.get("clipboard") == "wb-clip" and r.get("encode") == "héllo", "clipboard + workspace.encode / decode", r)
check(r.get("updateFolders") is True and r.get("foldersAdded") == 1 and r.get("folders") == 1,
      "updateWorkspaceFolders + onDidChangeWorkspaceFolders", r)
check(r.get("ext") == "radide-test.workbench-api" and r.get("storage") and r.get("secret") == "secret",
      "extensions.getExtension (case-insensitive) + ExtensionContext members", r)
check(r.get("breakpoints") == 1 and r.get("open") is True, "debug.addBreakpoints + env.openExternal(radide://)", r)
check(any(u["path"] == "/fromOpenExternal" for u in report().get("uris") or []), "openExternal routed to the URI handler")

# ---------------------------------------------------------------- visible ranges / options
long = ws / "long.txt"
long.write_text("".join(f"line {i}\n" for i in range(400)), "utf-8")
ed_long = win.open_any_file(long)
check(ed_long is not None and wait(lambda: ed_long._ready, 30), "long file opened")
ed_long.setFocus()
win.tabs.setCurrentIndex(win.tabs.count() - 1)
wb._current_changed()
ed_long._js("radEditor.setScrollTop(2000);")
check(wait(lambda: (run("visible", timeout=5) or {}).get("events", 0) > 0, 15),
      "Monaco scroll -> onDidChangeTextEditorVisibleRanges", run("visible", timeout=5))
r = {}
check(wait(lambda: (r.update(run("visible", timeout=5) or {}) or True) and r.get("file") == "long.txt" and r.get("ranges")
           and r["ranges"][0][0] > 10, 15), "TextEditor.visibleRanges follows the scroll", r)
check(run("setOptions") == 2, "TextEditor.options setter")

# ---------------------------------------------------------------- tabs closed by the extension
check(run("closeTab", "long.txt") is True and wait(lambda: win.tabs.indexOf(ed_long) < 0 and
                                                  all(win.tabs.widget(i) is not ed_long and getattr(win.tabs.widget(i), "editor", None) is not ed_long
                                                      for i in range(win.tabs.count())), 10),
      "tabGroups.close(text tab) closes the IDE tab")

# ---------------------------------------------------------------- nothing of this is "unsupported" any more
mine = [a for e, a in svc.unsupported if e == "radide-test.workbench-api"]
check(not mine, "no unsupported API used by workbench-api", mine)
win.grab().save(str(SCRATCH / "workbench_window.png"))

# ---------------------------------------------------------------- Claude Code (optional)
if CLAUDE is not None and CLAUDE.exists():
    check(wait(lambda: "anthropic.claude-code" in svc.activation, 60), "Claude Code activated", svc.activation.get("anthropic.claude-code"))
    check(wait(lambda: {"_claude_vscode_fs_left", "_claude_vscode_fs_right", "_claude_fs_left", "_claude_fs_right"} <= wb.fs_schemes, 20),
          "Claude Code's diff file system providers registered", wb.fs_schemes)
    bad = [a for e, a in svc.unsupported if e == "anthropic.claude-code"]
    check(not any("registerFileSystemProvider" in a or "registerUriHandler" in a or "tabGroups" in a for a in bad),
          "Claude Code: no unsupported workbench API at start-up", bad)
    print("Claude Code unsupported at start-up:", bad)

    # the CLI's side of a proposed edit: MCP tool "openDiff" over the extension's WebSocket server
    import subprocess
    import threading
    from radide.vsx.bridge import find_node
    cfg = Path(os.environ["CLAUDE_CONFIG_DIR"])
    check(wait(lambda: list((cfg / "ide").glob("*.lock")), 30), "Claude Code wrote its IDE lock file (ideName RAD IDE)",
          [json.loads(f.read_text("utf-8")).get("ideName") for f in (cfg / "ide").glob("*.lock")] if (cfg / "ide").exists() else None)
    target = ws / "claude_target.py"
    target.write_text("def add(a, b):\n    return a + b\n", "utf-8")
    proposal = SCRATCH / "proposal.txt"
    proposal.write_text("def add(a, b):\n    \"\"\"Sum.\"\"\"\n    return a + b\n", "utf-8")
    events: list = []
    before = set(wb.diffs)
    proc = subprocess.Popen([find_node(), str(HERE / "claude_open_diff.js"), str(cfg), str(target), str(proposal), "radide-test"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8")

    def reader():
        for line in proc.stdout:
            try:
                events.append(json.loads(line))
            except ValueError:
                events.append({"event": "text", "text": line.strip()})
    threading.Thread(target=reader, daemon=True).start()
    check(wait(lambda: any(e.get("event") == "calling" for e in events), 30), "MCP client connected, openDiff called",
          events[-3:])
    check(wait(lambda: set(wb.diffs) - before, 20), "Claude Code's proposed change opened as a Diff tab", events[-2:])
    cview = next((wb.diffs[k] for k in set(wb.diffs) - before), None)
    if cview is not None:
        accept = {"claude-vscode.acceptProposedDiff", "claude-code.acceptProposedDiff"}     # (sidebar / CLI scheme)
        check(wait(lambda: accept & set(cview.title_commands()), 15),
              "Claude Code's Accept / Reject buttons on the Diff tab", cview.title_commands())
        check('"""Sum."""' in cview.right.text and "return a + b" in cview.left.text, "diff shows the file and the proposal",
              (cview.left.text, cview.right.text))
        cview.grab().save(str(SCRATCH / "claude_diff.png"))
        wait(lambda: False, 1.5)       # Claude Code starts listening for Accept / Reject after it saw the tab (100 ms poll)
        act = next((a for a in cview._title_actions if a.objectName()[len("vsxTitle:"):] in accept), None)
        if act is not None:
            act.trigger()
        check(wait(lambda: any(e.get("event") == "result" for e in events), 30), "openDiff answered after Accept", events[-3:])
        res = next((e["result"] for e in events if e.get("event") == "result"), {})
        texts = [c.get("text", "") for c in (res or {}).get("content", [])]
        check(any("FILE_SAVED" in t for t in texts) and any('"""Sum."""' in t for t in texts),
              "Claude Code got FILE_SAVED + the accepted contents", texts)
        check(wait(lambda: any(e.get("event") == "close_tab" for e in events), 15) and
              wait(lambda: all(win.tabs.widget(i) is not cview for i in range(win.tabs.count())), 10),
              "close_tab tool (as the CLI calls it) closed the Diff tab", events[-2:])
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        proc.kill()

svc.stop()
win.close()
QSettings().clear()
fails = [r for r in RESULTS if not r[0]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed")
sys.exit(len(fails))
