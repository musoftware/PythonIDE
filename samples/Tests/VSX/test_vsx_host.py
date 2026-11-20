"""End-to-end test of the VS Code extension host inside the real RAD IDE main window.

    python samples/Tests/VSX/test_vsx_host.py <scratch folder>

Packs the test extensions of this folder as .vsix files (mini-lsp gets its npm dependencies installed into
the scratch copy), installs them with radide.vsx.manager into <scratch>/vsxroot (RADIDE_VSX_ROOT), starts
MainWindow with RADIDE-TEST settings and checks: activation, contributed commands in the Command Palette,
status bar item, message / quick pick / input box dialogs, configuration round trip, completion / hover /
definition / formatting / code actions / diagnostics through editor.lsp, a vscode-languageclient extension,
F5-style debugging with a declarative adapter and an inline adapter. Writes screenshots (widget.grab()) and
prints PASS / FAIL lines; exit code = number of failures."""
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
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_host_test"
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
os.environ["RADIDE_VSX_ROOT"] = str(SCRATCH / "vsxroot")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
sys.path.insert(0, str(REPO))

RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:300]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:300]}]" if detail else ""), flush=True)


def pack(src: Path, out: Path) -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/'
                   'json"/><Default Extension="js" ContentType="application/javascript"/></Types>')
        for f in src.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".py":
                z.write(f, "extension/" + f.relative_to(src).as_posix())
    return out


def prepare_extensions() -> list[Path]:
    out = []
    for name in ("hello-commands", "mini-debug"):
        out.append(pack(HERE / name, SCRATCH / f"radide-test.{name}-0.0.1.vsix"))
    lsp = SCRATCH / "mini-lsp-src"
    shutil.copytree(HERE / "mini-lsp", lsp)
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    r = subprocess.run([npm, "install", "--prefix", str(lsp), "--no-audit", "--no-fund", "--ignore-scripts", "--no-save",
                        "vscode-languageclient@9.0.1", "vscode-languageserver@9.0.1",
                        "vscode-languageserver-textdocument@1.0.12"], capture_output=True, text=True, shell=False)
    check(r.returncode == 0 and (lsp / "node_modules" / "vscode-languageclient").is_dir(), "npm install vscode-languageclient",
          r.stderr[-200:])
    out.append(pack(lsp, SCRATCH / "radide-test.mini-lsp-0.0.1.vsix"))
    return out


VSIX = prepare_extensions()

__import__("PyQt6.QtWebEngineWidgets")  # before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QMessageBox  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
QSettings().clear()

from radide.vsx import manager  # noqa: E402

for v in VSIX:
    exts = manager.install_vsix_file(v, with_dependencies=False)
    check(exts and exts[0].enabled, f"install {v.name}")

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


def call(fn, timeout=10.0):
    """fn(cb) -> the value passed to cb."""
    box = {}
    fn(lambda *a: box.setdefault("v", a[0] if len(a) == 1 else a))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def js(ed, code, timeout=5.0):
    box = {}
    ed.page().runJavaScript(code, lambda v: box.setdefault("v", v))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


DIALOG_ANSWERS = []          # what the auto-answerer did


def answer_dialogs():
    from radide.vsx.host_ide import InputDialog, QuickPickDialog
    w = QApplication.activeModalWidget()
    if isinstance(w, QMessageBox):
        b = w.buttons()
        custom = [x for x in b if w.buttonRole(x) == QMessageBox.ButtonRole.AcceptRole]
        DIALOG_ANSWERS.append(("message", w.text()))
        (custom[0] if custom else b[0]).click()
    elif isinstance(w, QuickPickDialog):
        DIALOG_ANSWERS.append(("quickpick", [w.list.item(i).text() for i in range(w.list.count())]))
        w.list.setCurrentRow(1)
        w.accept()
    elif isinstance(w, InputDialog):
        DIALOG_ANSWERS.append(("input", w.windowTitle()))
        w.edit.setText("Ada")
        w.accept()
    elif isinstance(w, QDialog):
        w.reject()


timer = QTimer()
timer.timeout.connect(answer_dialogs)
timer.start(300)

win = MainWindow()
win.resize(1400, 900)
win.show()
svc = getattr(win, "vsx_host", None)
check(svc is not None, "feature installed (win.vsx_host)")
check(wait(lambda: svc.host.running() and svc.host.init_result is not None, 30), "extension host started",
      getattr(svc.host, "init_result", None))
check(wait(lambda: "radide-test.hello-commands" in svc.activation, 20), "hello-commands activated (onStartupFinished)",
      svc.activation)

from radide.features import command_palette as cp  # noqa: E402

ids = {c.id for c in cp.commands()}
check({"helloCommands.sayHello", "helloCommands.pick", "extension.mock-debug.x"} & ids >= {"helloCommands.sayHello",
      "helloCommands.pick"}, "contributed commands in the Command Palette")
check(wait(lambda: any("Hello" in b.text() for b in svc.status_items.values() if b.isVisible()), 10),
      "status bar item rendered", [b.text() for b in svc.status_items.values()])

# ---------------------------------------------------------------- plain text editor + providers
ws = SCRATCH / "ws"
ws.mkdir()
txt = ws / "notes.txt"
txt.write_text("hello world   \nTODO fix\n", "utf-8")
ed = win.open_any_file(txt)
check(ed is not None and wait(lambda: ed._ready, 30), "editor opened (Monaco ready)")
from radide.vsx.lsp_client import CompositeClient, editor_lang  # noqa: E402

check(editor_lang(ed) == "plaintext", "VS Code language id of .txt", editor_lang(ed))
check(wait(lambda: isinstance(ed.lsp, CompositeClient), 15), "editor.lsp is a CompositeClient", type(ed.lsp))
items = call(lambda cb: ed.lsp.completion(ed.path, ed.text(), 0, 3, cb))
labels = [i.get("label") for i in items or []]
check("helloWorld" in labels, "completion from vscode.languages provider", labels[:8])
hello = next((i for i in items or [] if i.get("label") == "helloWorld"), {})
check(hello.get("snippet") and "hello(" in (hello.get("insertText") or ""), "snippet completion item", hello)
hov = call(lambda cb: ed.lsp.hover(ed.path, 0, 2, cb))
check("Word: **hello**" in (hov or ""), "hover provider", hov)
d = call(lambda cb: ed.lsp.definition(ed.path, 1, 1, cb))
check(d and Path(d[0]).name == "notes.txt" and d[1] == 0, "definition provider", d)
fmt = call(lambda cb: ed.lsp._request("textDocument/formatting", {"textDocument": {"uri": txt.resolve().as_uri()},
                                                                   "options": {"tabSize": 4, "insertSpaces": True}}, cb))
check(fmt and fmt[0]["newText"] == "hello world", "formatting provider (through formatting.py's LSP path)", fmt)
check(wait(lambda: svc.diagnostics_for(txt), 10), "diagnostics collection -> IDE", svc.diagnostics_for(txt))
markers = js(ed, "monaco.editor.getModelMarkers({owner: 'vsx'}).map(m => m.message + '@' + m.startLineNumber)")
check(markers and "TODO found@2" in markers, "diagnostics as Monaco markers", markers)
acts = call(lambda cb: ed.lsp._request("textDocument/codeAction", {
    "textDocument": {"uri": txt.resolve().as_uri()},
    "range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 4}},
    "context": {"diagnostics": [{"range": {"start": {"line": 1, "character": 0}, "end": {"line": 1, "character": 4}},
                                 "message": "TODO found", "severity": 2, "code": "todo"}]}}, cb))
check(acts and acts[0]["title"] == "Replace TODO with DONE", "code action provider", acts)
from radide import editkit  # noqa: E402

if acts:
    editkit.apply_workspace_edit(win, acts[0].get("edit"))
check(wait(lambda: "DONE fix" in ed.text(), 5), "code action edit applied", ed.text())

# ---------------------------------------------------------------- commands with UI
ed.setFocus()
r = call(lambda cb: svc.execute("helloCommands.sayHello", ["RAD"], cb), 15)
check(r == "Hello RAD!", "command with message box (items)", (r, DIALOG_ANSWERS[-1:] if DIALOG_ANSWERS else None))
r = call(lambda cb: svc.execute("helloCommands.pick", [], cb), 15)
check(r == "Banana", "quick pick", r)
r = call(lambda cb: svc.execute("helloCommands.ask", [], cb), 15)
check(r == "Ada", "input box + configuration.update", r)
from radide.vsx import contrib_configuration  # noqa: E402

check(contrib_configuration.load().get("helloCommands.greeting") == "Hi Ada", "setting stored by the IDE",
      contrib_configuration.load())
r = call(lambda cb: svc.execute("helloCommands.sayHello", [], cb), 15)
check(r == "Hi Ada World!", "configuration change reached the extension", r)
ed.setCursorPosition(0, 0)
ed._cursor = (0, 0)
ed._selection = (0, 0, 0, 0)
svc._active_sent = None
r = call(lambda cb: svc.execute("helloCommands.insertDate", [], cb), 15)
check(wait(lambda: ed.text().startswith("2026-01-01"), 5), "text editor command (TextEditorEdit -> applyEdit)", ed.text()[:40])
state = call(lambda cb: svc.execute("helloCommands.state", [], cb), 15)
check(isinstance(state, dict) and state.get("changes", 0) >= 1, "onDidChangeTextDocument fed from the IDE", state)
check(any(a == "window.createWebviewPanel" for _e, a in svc.unsupported), "unsupported API fails softly + logged",
      svc.unsupported)
menu_items = []
from PyQt6.QtWidgets import QMenu  # noqa: E402

m = QMenu()
ed.contextMenuAboutToShow.emit(m)
menu_items = [a.text() for a in m.actions()]
check("Insert Date" in menu_items, "editor/context menu contribution", menu_items)
win.grab().save(str(SCRATCH / "vsx_host_editor.png"))

# ---------------------------------------------------------------- vscode-languageclient extension
mini = ws / "prog.mini"
mini.write_text("let x = 1   \nprint bad\n", "utf-8")
ed2 = win.open_any_file(mini)
check(ed2 is not None and wait(lambda: ed2._ready, 30), "minilang editor opened")
check(editor_lang(ed2) == "minilang", "contributed language mapped (.mini -> minilang)", ed2.language_id())
check(wait(lambda: "radide-test.mini-lsp" in svc.activation, 20), "mini-lsp activated (onLanguage)", svc.activation)
check(wait(lambda: svc.diagnostics_for(mini), 20), "language server diagnostics via vscode-languageclient",
      svc.diagnostics_for(mini))
check(wait(lambda: isinstance(ed2.lsp, CompositeClient), 10), "minilang editor.lsp wrapped")
items = call(lambda cb: ed2.lsp.completion(ed2.path, ed2.text(), 1, 0, cb))
check({"print", "let"} <= {i.get("label") for i in items or []}, "language server completions in the editor",
      [i.get("label") for i in items or []][:8])
hov = call(lambda cb: ed2.lsp.hover(ed2.path, 0, 1, cb))
check("mini-lsp" in (hov or ""), "language server hover", hov)
win.grab().save(str(SCRATCH / "vsx_host_lsp.png"))

# ---------------------------------------------------------------- debugger (declarative program/runtime)
prog = ws / "t.mdbg"
prog.write_text("a = 1\nb = 2\nc = 3\n", "utf-8")
ed3 = win.open_any_file(prog)
check(ed3 is not None and wait(lambda: ed3._ready, 30), "minidbg editor opened")
ed3.set_breakpoints([1])           # 0-based editor line = line 2
ed3.setFocus()
stops = []
check(svc.should_debug_with_extension(ed3), "F5 picks the extension debugger for this file")
ok = svc.debug_start(ed=ed3)
check(ok, "debug session started (declarative adapter)")
s = win.session
s.stopped.connect(lambda info: stops.append(info))
check(wait(lambda: stops, 15), "stopped at breakpoint", [(i.line, i.variables) for i in stops])
if stops:
    check(stops[0].line == 2 and ("a", "number", "1") in stops[0].variables, "stack + locals from the adapter",
          (stops[0].line, stops[0].variables))
done = []
s.finished.connect(lambda c: done.append(c))
s.cont()
check(wait(lambda: done, 15), "session finished", done)

# ---------------------------------------------------------------- inline adapter (in the extension host)
contrib_configuration.set_values({"miniDebug.inline": True})
svc.restart()
check(wait(lambda: svc.host.init_result is not None and svc.host.running(), 30), "host restarted")
wait(lambda: False, 1.5)
stops.clear()
ed3.setFocus()
ok = svc.debug_start(ed=ed3)
check(ok and win.session.argv and win.session.argv[-2] == "127.0.0.1", "inline adapter served via relay.js",
      getattr(win.session, "argv", None))
s = win.session
dbg_out = []
s.output.connect(lambda t: dbg_out.append(t))
s.stopped.connect(lambda info: stops.append(info))
check(wait(lambda: stops, 15), "inline adapter stopped at breakpoint")
done.clear()
s.finished.connect(lambda c: done.append(c))
wait(lambda: s.paused, 5)
s.cont()
check(wait(lambda: done, 15), "inline session finished", (s.paused, s.running(), dbg_out[-5:]))
out = svc.output.texts.get("Mini Debug", "")
check("custom event custom/finished" in out and "session started minidbg" in out,
      "debug events reach the extension (onDidStartDebugSession, custom events)", out[-300:])
win.grab().save(str(SCRATCH / "vsx_host_debug.png"))

# ---------------------------------------------------------------- shutdown
timer.stop()
pid = (svc.host.init_result or {}).get("pid")
svc.stop()
check(not svc.host.running(), "extension host stopped")
for e in list(svc.live_editors()):
    try:
        e.setModified(False)
    except Exception:  # noqa: BLE001
        pass
win.close()
QSettings().clear()
fails = [r for r in RESULTS if not r[0]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed; screenshots in {SCRATCH}")
(SCRATCH / "results.json").write_text(json.dumps(RESULTS, indent=1), "utf-8")
os._exit(len(fails))
