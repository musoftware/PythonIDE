"""VS Code parity of RAD IDE's Command Palette, editor command mapping, keybindings and settings.

    python samples/Tests/VSX/test_vsx_palette.py <scratch folder>

* ">" commands: extension commands with category and keybinding, commandPalette `when` / `enablement` hide
  entries (and show them once the context key is set), VS Code's own palette commands RAD IDE runs
  ("Format Document", "Go Back", "View: Toggle Primary Side Bar Visibility" ...), recently used first, fuzzy
  match positions for the highlight;
* "@" document symbols, ":" go to line, "#" workspace symbols, "view ", "task " (tasks.json), "debug "
  (launch.json), "ext install", "edt ", "?" help; Ctrl+Shift+P / Ctrl+P actions;
* editor commands: vscode.commands.executeCommand('editor.action.commentLine' | 'type' | 'cursorDown' |
  'editor.action.toggleWordWrap' | 'editor.fold' | 'editor.action.selectAll' ...) from an extension and from
  the IDE (vscode_commands.execute) change the Monaco editor; reference/monaco_commands.json is sane;
* workbench commands: navigation history (navigateBack / Forward), reopenClosedEditor, quickOpen(prefix);
* keybindings.json (user rules + "-command" removal) changes the bindings, Keyboard Shortcuts page lists /
  filters them and writes rules; Settings page: search, @ext:, editing writes settings.json;
* the Extensions panel leaves no Arabic text after switching the UI language back to English.
QSettings org RADIDE-TEST-VSX2 (cleared), scratch RADIDE_VSX_ROOT, offscreen friendly. Exit code = failures."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SCRATCH = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TEMP", ".")) / "vsx_palette_test"
if SCRATCH.exists():
    shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True)
os.environ["RADIDE_VSX_ROOT"] = str(SCRATCH / "vsxroot")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-gpu-compositing --disable-logging --log-level=3")
sys.path.insert(0, str(REPO))

RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:400]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:400]}]" if detail else ""), flush=True)


def pack(src: Path, out: Path) -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.'
                   'openxmlformats.org/package/2006/content-types"><Default Extension="json" ContentType="application/'
                   'json"/></Types>')
        for f in src.rglob("*"):
            if f.is_file():
                z.write(f, "extension/" + f.relative_to(src).as_posix())
    return out


# ---------------------------------------------------------------- 0. reference data
mc = json.loads((REPO / "radide" / "vsx" / "reference" / "monaco_commands.json").read_text("utf-8"))
check(mc.get("monacoVersion") and len(mc["commands"]) > 200 and "editor.action.formatDocument" in mc["commands"]
      and "cursorDown" in mc["commands"] and "type" in mc["commands"], "monaco_commands.json: Monaco's editor command ids",
      (mc.get("monacoVersion"), len(mc.get("commands", []))))

__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication, QCheckBox, QDialog, QLabel, QMessageBox, QPushButton, QWidget  # noqa: E402

app = QApplication(sys.argv[:1])
QCoreApplication.setOrganizationName("RADIDE-TEST-VSX2")
QCoreApplication.setApplicationName("RADIDE-TEST-VSX2")
QSettings().clear()

from radide.vsx import manager  # noqa: E402

exts = manager.install_vsix_file(pack(HERE / "palette-test", SCRATCH / "radide-test.palette-test-0.0.1.vsix"),
                                 with_dependencies=False)
check(exts and exts[0].enabled, "install palette-test", exts and exts[0].id)

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


proj = SCRATCH / "HelloPython"
shutil.copytree(REPO / "samples" / "HelloPython", proj)
(proj / ".vscode").mkdir()
(proj / ".vscode" / "tasks.json").write_text('{\n // comment\n "version": "2.0.0",\n "tasks": [{"label": "echo hello",'
                                              ' "type": "shell", "command": "echo hello"},]\n}\n', "utf-8")
(proj / ".vscode" / "launch.json").write_text('{"version": "0.2.0", "configurations": [{"name": "Python: Current File",'
                                               ' "type": "python", "request": "launch", "program": "${file}"}]}', "utf-8")

from radide.app import MainWindow  # noqa: E402
from radide.features import command_palette as cp  # noqa: E402
from radide.vsx import vscode_commands as VC  # noqa: E402

win = MainWindow()
win.resize(1400, 900)
win.show()
win.open_project(proj, ask=False)
svc = win.vsx_host
check(wait(lambda: svc.host.running() and svc.activation.get("radide-test.palette-test") == "active", 60),
      "extension host + palette-test active", svc.activation)


def host(cmd, *args, timeout=15.0):
    box = {}
    svc.execute(cmd, list(args), lambda r: box.setdefault("v", r))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def exec_cmd(cid, *args):
    return host("paletteTest.exec", cid, *args) or {}


cp.open_path(win, proj / "Form1.py")
check(wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "Form1.py", 90),
      "Form1.py open in a Monaco editor", [win.tabs.tabText(k) for k in range(win.tabs.count())])
ed = svc.active_editor() or getattr(win.tabs.currentWidget(), "editor", None)
wait(lambda: getattr(ed, "_ready", False), 30)


def palette(text):
    box = cp.quick_open(win, text)
    wait(lambda: box.isVisible(), 5)
    app.processEvents()
    return box


def labels(box):
    return [it.label for it in box.current_items()]


def item(box, pred):
    return next((it for it in box.current_items() if pred(it)), None)


# ---------------------------------------------------------------- 1. ">" commands
box = palette(">")
ls = labels(box)
pt = item(box, lambda it: it.label == "PT: Always Visible")
check(pt is not None and pt.shortcut, "extension command with category and its keybinding", pt and (pt.label, pt.shortcut))
check("PT: Hidden By When" not in ls and "PT: Execute Command" not in ls and "PT: Needs Enablement" not in ls,
      "commandPalette when / enablement false -> not listed (VS Code)", [x for x in ls if x.startswith("PT")])
host("setContext", "paletteTest.show", True)
host("setContext", "paletteTest.enabled", True)
wait(lambda: False, 0.5)
box = palette(">")
ls = labels(box)
check("PT: Hidden By When" in ls and "PT: Needs Enablement" in ls, "... listed once the context keys are set",
      [x for x in ls if x.startswith("PT")])
for want in ("Format Document", "Go Back", "Reopen Closed Editor", "View: Toggle Primary Side Bar Visibility",
             "Toggle Line Comment", "Preferences: Open Keyboard Shortcuts (JSON)"):
    check(any(x == want or x.endswith(": " + want) or x.startswith(want) for x in ls), f"VS Code command in the palette: {want}",
          [x for x in ls if want.split()[0].lower() in x.lower()][:5])
n_builtin = len([it for it in box.current_items() if it.key.startswith("v:")])
check(n_builtin > 150, "VS Code built-in commands offered in the palette", n_builtin)
box.edit.setText(">ptav")
app.processEvents()
top = box.current_items()[0] if box.current_items() else None
check(top is not None and top.label == "PT: Always Visible" and top.pos, "fuzzy match 'ptav' -> PT: Always Visible with highlight",
      top and (top.label, top.pos))
box.accept()
check(wait(lambda: "visible" in (host("paletteTest.calls") or []), 10), "running it from the palette calls the extension")
box = palette(">")
first = box.current_items()[0] if box.current_items() else None
check(first is not None and first.label == "PT: Always Visible" and "recently used" in first.detail,
      "recently used command on top", first and (first.label, first.detail))
box.close_box()

# ---------------------------------------------------------------- 2. other prefixes
box = palette("@")
wait(lambda: any(it.label == "btnGreet_Click" for it in box.current_items()), 10)
sym = item(box, lambda it: it.label == "btnGreet_Click")
check(sym is not None, "@ lists the editor's symbols", labels(box)[:10])
box.edit.setText("@timer")
app.processEvents()
check(labels(box)[:1] == ["Timer1_Tick"], "@timer filters to Timer1_Tick", labels(box)[:3])
box.accept()
check(wait(lambda: ed._cursor[0] == next(i for i, ln in enumerate(ed.text().split("\n")) if "def Timer1_Tick" in ln), 5),
      "accepting a symbol moves the cursor there", ed._cursor)
box = palette(":5")
check(labels(box) and "5" in labels(box)[0], ": go to line", labels(box))
box.accept()
check(wait(lambda: ed._cursor[0] == 4, 5), "... cursor on line 5", ed._cursor)
box = palette("#mnuFile")
wait(lambda: any("mnuFileExit_Click" == it.label for it in box.current_items()), 10)
check(any("mnuFileExit_Click" == x for x in labels(box)), "# workspace symbols", labels(box)[:5])
box = palette("view ")
check(any("Solution Explorer" in x for x in labels(box)), "view: tool windows", labels(box)[:8])
box = palette("task ")
check("echo hello" in labels(box), "task: tasks.json (JSONC with comments / trailing comma)", labels(box))
box = palette("debug ")
check("Python: Current File" in labels(box) and any("Start Debugging" in x for x in labels(box)), "debug: launch.json configurations",
      labels(box))
box = palette("ext install prettier")
check(labels(box) and "prettier" in labels(box)[0], "ext install <name>", labels(box))
box = palette("edt ")
check(any("Form1.py" in x for x in labels(box)), "edt: open editors", labels(box))
box = palette("?")
check(len(labels(box)) >= 12 and any(x.startswith("@") for x in labels(box)), "? help lists the prefixes", labels(box))
box.close_box()
check(win.a_command_palette.shortcut().toString() == "Ctrl+Shift+P" and win.a_quick_open.shortcut().toString() == "Ctrl+P",
      "Ctrl+Shift+P / Ctrl+P")
VC.execute(win, "workbench.action.quickOpen", ["@"])
check(wait(lambda: win.command_palette.isVisible() and win.command_palette.edit.text() == "@", 5),
      "workbench.action.quickOpen('@') opens the quick input with that prefix", win.command_palette.edit.text())
win.command_palette.close_box()

# ---------------------------------------------------------------- 3. editor commands (extension -> Monaco)
ed.setCursorPosition(6, 0)                 # "    def Form1_Load(self):"
wait(lambda: False, 0.3)
r = exec_cmd("editor.action.commentLine")
check("error" not in r, "executeCommand('editor.action.commentLine') resolves", r)
check(wait(lambda: ed.text().split("\n")[6].lstrip().startswith("#"), 10), "... the line is commented in Monaco",
      ed.text().split("\n")[6])
exec_cmd("editor.action.commentLine")
check(wait(lambda: not ed.text().split("\n")[6].lstrip().startswith("#"), 10), "... and uncommented again")
ed.setCursorPosition(0, 0)
wait(lambda: False, 0.3)
exec_cmd("cursorDown")
check(wait(lambda: ed._cursor[0] == 1, 5), "cursorDown moves the cursor", ed._cursor)
exec_cmd("type", {"text": "ZZ"})
check(wait(lambda: "ZZ" in ed.text().split("\n")[1], 10), "type {text} inserts at the cursor", ed.text().split("\n")[1])
exec_cmd("undo")
check(wait(lambda: "ZZ" not in ed.text(), 10), "undo")
for cid in ("editor.fold", "editor.unfoldAll", "editor.action.toggleWordWrap", "editor.action.toggleMinimap",
            "editor.action.selectAll", "actions.find", "workbench.action.zoomIn", "workbench.action.zoomReset"):
    r = exec_cmd(cid)
    check("error" not in r, f"executeCommand('{cid}') resolves", r)
WRAP: list = []
wait(lambda: False, 0.5)
ed.page().runJavaScript("radEditor.getOption(monaco.editor.EditorOption.wordWrap)", lambda v: WRAP.append(v))
check(wait(lambda: WRAP, 5) and WRAP[-1] == "on", "toggleWordWrap switched Monaco's wordWrap on", WRAP)
VC.execute(win, "editor.action.toggleWordWrap")
WRAP.clear()
wait(lambda: False, 0.5)
ed.page().runJavaScript("radEditor.getOption(monaco.editor.EditorOption.wordWrap)", lambda v: WRAP.append(v))
check(wait(lambda: WRAP, 5) and WRAP[-1] == "off", "... and off again from the IDE side (vscode_commands.execute)", WRAP)
ed.setCursorPosition(6, 0)
wait(lambda: False, 0.3)
VC.execute(win, "editor.action.commentLine")
check(wait(lambda: ed.text().split("\n")[6].lstrip().startswith("#"), 10), "palette / keybinding path runs Monaco's commentLine")
VC.execute(win, "editor.action.commentLine")
r = exec_cmd("no.such.command.zz")
check(r.get("error") == "command 'no.such.command.zz' not found", "unknown command still rejects", r)

# ---------------------------------------------------------------- 4. navigation history / reopen closed editor
cp.open_path(win, proj / "Form1_designer.py")
check(wait(lambda: Path(svc.active_editor().path).name == "Form1_designer.py", 15), "second editor open")
wait(lambda: False, 0.5)
VC.execute(win, "workbench.action.navigateBack")
check(wait(lambda: Path(svc.active_editor().path).name == "Form1.py", 10), "workbench.action.navigateBack -> Form1.py",
      svc.active_editor() and svc.active_editor().path)
VC.execute(win, "workbench.action.navigateForward")
check(wait(lambda: Path(svc.active_editor().path).name == "Form1_designer.py", 10), "navigateForward -> Form1_designer.py")
tabs = win.tabs
i = tabs.currentIndex()
tabs.tabCloseRequested.emit(i)
wait(lambda: all(Path(getattr(getattr(tabs.widget(k), "editor", None), "path", "x")).name != "Form1_designer.py"
                 for k in range(tabs.count())), 5)
wait(lambda: False, 1.2)
VC.execute(win, "workbench.action.reopenClosedEditor")
check(wait(lambda: svc.active_editor() is not None and Path(svc.active_editor().path).name == "Form1_designer.py", 10),
      "workbench.action.reopenClosedEditor reopens it")

# ---------------------------------------------------------------- 5. keybindings.json / Keyboard Shortcuts / Settings
from radide.vsx import contrib_keybindings as KB, user_keybindings as UK, settings_ui  # noqa: E402

UK.ensure_file()
UK.path().write_text('// user\n[\n {"key": "ctrl+alt+shift+8", "command": "paletteTest.visible"},\n'
                     ' {"key": "ctrl+alt+shift+9", "command": "-paletteTest.visible"},\n]\n', "utf-8")
b = [x for x in KB.collect() if x["command"] == "paletteTest.visible"]
check([x["key"] for x in b] == ["ctrl+alt+shift+8"] and b[0].get("user"), "keybindings.json: user key added, '-command' removed the old one",
      b)
box = palette(">PT: Always")
it = item(box, lambda x: x.label == "PT: Always Visible")
check(it is not None and "8" in it.shortcut, "palette shows the user's key", it and it.shortcut)
box.close_box()
page = settings_ui.show_keyboard_shortcuts(win, "paletteTest.visible")
wait(lambda: page.tree.topLevelItemCount() > 0, 5)
check(page.tree.topLevelItemCount() >= 1 and any(page.tree.topLevelItem(k).text(4) == "paletteTest.visible"
                                                  for k in range(page.tree.topLevelItemCount())),
      "Keyboard Shortcuts page finds the command", page.tree.topLevelItemCount())
page.search.setText("ctrl+alt+shift+8")
check(page.tree.topLevelItemCount() >= 1, "... search by key", page.tree.topLevelItemCount())
page.tree.setCurrentItem(page.tree.topLevelItem(0))
page.change("ctrl+alt+shift+7")
rules = UK.load()
check({"key": "ctrl+alt+shift+7", "command": "paletteTest.visible"} in rules, "Change Keybinding writes keybindings.json", rules)
page.close()
VC.execute(win, "workbench.action.openGlobalKeybindingsFile")
check(wait(lambda: win.tabs.tabText(win.tabs.currentIndex()).rstrip("*").endswith("keybindings.json"), 10),
      "Preferences: Open Keyboard Shortcuts (JSON) opens keybindings.json",
      [win.tabs.tabText(k) for k in range(win.tabs.count())])
sp = settings_ui.show_settings(win, "@ext:radide-test.palette-test")
check(set(sp.editors) == {"paletteTest.flag", "paletteTest.mode"}, "Settings page: @ext: filter", list(sp.editors))
cb = sp.editors.get("paletteTest.flag")
if isinstance(cb, QCheckBox):
    cb.setChecked(True)
from radide.vsx import contrib_configuration as CC  # noqa: E402

check(CC.get("paletteTest.flag") is True, "Settings page edit -> settings.json", CC.load())
sp.search.setText("enum setting")
check(list(sp.editors) == ["paletteTest.mode"], "Settings page: text search in descriptions", list(sp.editors))
sp.search.setText("@modified")
check(list(sp.editors) == ["paletteTest.flag"], "Settings page: @modified", list(sp.editors))
sp.close()
v = host("paletteTest.exec", "workbench.action.openSettingsUI")
check(wait(lambda: getattr(win, "_vsx_settings_page", None) is not None and win._vsx_settings_page.isVisible(), 5),
      "workbench.action.openSettingsUI opens the Settings page", v)
win._vsx_settings_page.close()

# ---------------------------------------------------------------- 6. Extensions panel: language switch leaves no Arabic
from radide import i18n  # noqa: E402
from radide.features import vsx_market  # noqa: E402
from radide.features.ui_language import apply_language  # noqa: E402

vsx_market.show_view(win)
wait(lambda: getattr(win, "vsx_view", None) is not None, 5)
apply_language(win, "ar", notify=False)
wait(lambda: False, 0.8)
AR = re.compile(r"[؀-ۿ]")
view = win.vsx_view
check(any(AR.search(i18n.shown(b2) or "") for b2 in view.findChildren(QPushButton)), "Extensions panel in Arabic")
box = palette("?")
check(any(AR.search(x) for x in labels(box)), "palette help in Arabic", labels(box)[:3])
box.close_box()
apply_language(win, "en", notify=False)
wait(lambda: False, 1.0)
left = [i18n.shown(w) for w in view.findChildren(QWidget) if isinstance(w, (QLabel, QPushButton))
        and AR.search(i18n.shown(w) or "")]
check(not left, "Extensions panel: no Arabic left after switching back to English", left[:6])

win.grab().save(str(SCRATCH / "palette_ide.png"))
un = [a for e, a in svc.unsupported if e == "radide-test.palette-test"]
check(not un, "palette-test: nothing reported unsupported", un)
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
