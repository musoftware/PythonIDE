"""QA of VS Code extension (VSX) support through the real RAD IDE main window.

    python samples\\Tests\\VSX\\test_vsx_qa.py <out_dir> [--onscreen]

Starts MainWindow with an EMPTY scratch RADIDE_VSX_ROOT and RADIDE-TEST settings, then does everything live,
the way a user would:
  * Ctrl+Shift+X opens the Extensions view; search Open VSX; click Install on the cards
    (Dracula, One Dark Pro, nifty TOML, JavaScript snippets, Material Icon Theme); uninstall from the Installed tab
  * Tools > Options > colour theme -> Dracula: Monaco + IDE chrome change
  * TOML grammar highlights; JavaScript snippet offered by the suggest widget; icons in Solution Explorer
  * Install from VSIX (hello-commands, mini-lsp) -> "Restart required" banner -> Reload starts the extension host;
    the command runs from the Command Palette; status bar item; language server completions + diagnostics
  * the IDE's own extension system (samples/Tests/Extensions) still loads and is listed
  * Arabic UI: the Extensions view / details page / Options page strings are translated
Screenshots (widget.grab()) go to <out_dir>.  Exit code = number of failures.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ONSCREEN = "--onscreen" in sys.argv
if ONSCREEN:
    sys.argv.remove("--onscreen")
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if os.path.isdir(r"C:\Windows\Fonts"):
        os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="radide_vsxqa_out_"))
OUT.mkdir(parents=True, exist_ok=True)
WORK = Path(tempfile.mkdtemp(prefix="radide_vsxqa_"))
os.environ["RADIDE_VSX_ROOT"] = str(WORK / "vsxroot")
os.environ["RADIDE_EXTENSIONS_DIR"] = str(WORK / "radext")

RESULTS: list[tuple[bool, str, str]] = []


def check(ok, name, detail=""):
    RESULTS.append((bool(ok), name, str(detail)[:400]))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{str(detail)[:400]}]" if detail and not ok else ""), flush=True)


def note(msg):
    print("NOTE " + msg, flush=True)


# --------------------------------------------------------------------- test vsix files (local samples)
def pack(src: Path, out: Path) -> Path:
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in src.rglob("*"):
            if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".py":
                z.write(f, "extension/" + f.relative_to(src).as_posix())
    return out


HELLO_VSIX = pack(HERE / "hello-commands", WORK / "radide-test.hello-commands-0.0.1.vsix")
lsp_src = WORK / "mini-lsp-src"
shutil.copytree(HERE / "mini-lsp", lsp_src)
npm = shutil.which("npm") or shutil.which("npm.cmd")
r = subprocess.run([npm, "install", "--prefix", str(lsp_src), "--no-audit", "--no-fund", "--ignore-scripts",
                    "--no-save", "vscode-languageclient@9.0.1", "vscode-languageserver@9.0.1",
                    "vscode-languageserver-textdocument@1.0.12"], capture_output=True, text=True)
check(r.returncode == 0, "npm install for mini-lsp", r.stderr[-200:])
LSP_VSIX = pack(lsp_src, WORK / "radide-test.mini-lsp-0.0.1.vsix")

# --------------------------------------------------------------------- the IDE's own extensions (before start)
from radide import extensions as X  # noqa: E402

for name in ("SolarizedTheme", "WordCountTools"):
    try:
        X.install_from_folder(REPO / "samples" / "Tests" / "Extensions" / name)
    except Exception as ex:  # noqa: BLE001
        check(False, f"own extension {name} installs", ex)

# --------------------------------------------------------------------- Qt
__import__("PyQt6.QtWebEngineWidgets")
from PyQt6.QtCore import QCoreApplication, QSettings, Qt, QTimer  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox, QPushButton, QStyle  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
# org RADIDE-TEST (test settings, never the user's); an own application name so that other test runs that
# call QSettings().clear() on HKCU\Software\RADIDE-TEST\RADIDE-TEST at the same time cannot wipe ours
QCoreApplication.setApplicationName(os.environ.get("RADIDE_QA_APPNAME", "RADIDE-TEST-VSXQA"))
app = QApplication(sys.argv[:1])
QSettings().clear()

ANSWERS: list = []
_orig_question = QMessageBox.question


def _yes(*a, **k):
    ANSWERS.append(("question", a[2] if len(a) > 2 else ""))
    return QMessageBox.StandardButton.Yes


QMessageBox.question = staticmethod(_yes)
QMessageBox.warning = staticmethod(lambda *a, **k: ANSWERS.append(("warning", a[2] if len(a) > 2 else "")))
QMessageBox.information = staticmethod(lambda *a, **k: ANSWERS.append(("info", a[2] if len(a) > 2 else "")))


def answer_dialogs():
    w = QApplication.activeModalWidget()
    if isinstance(w, QMessageBox):
        b = w.buttons()
        acc = [x for x in b if w.buttonRole(x) == QMessageBox.ButtonRole.AcceptRole]
        ANSWERS.append(("box", w.text()))
        (acc[0] if acc else b[0]).click()
    elif isinstance(w, QDialog):
        ANSWERS.append(("dialog", w.windowTitle()))
        w.reject()


tmr = QTimer()
tmr.timeout.connect(answer_dialogs)
tmr.start(300)


def pump(sec=0.05):
    end = time.time() + sec
    while time.time() < end:
        app.processEvents()
        time.sleep(0.003)


def wait(cond, timeout=30.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        try:
            if cond():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.02)
    return False


def shot(w, name):
    pump(0.4)
    w.grab().save(str(OUT / name))


def js(ed, code, timeout=15.0):
    box = {}
    ed.page().runJavaScript(code, lambda v: box.setdefault("v", v))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def call(fn, timeout=15.0):
    box = {}
    fn(lambda *a: box.setdefault("v", a[0] if len(a) == 1 else a))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


# --------------------------------------------------------------------- a small web site project
site = WORK / "QaSite"
(site / "src").mkdir(parents=True)
(site / "project.radproj").write_text(json.dumps({"name": "QaSite", "language": "static-web", "forms": [],
                                                   "startup": "", "modules": [], "kind": "website",
                                                   "web": {"root": ".", "start": "index.html"}}), "utf-8")
for rel, text in {"index.html": "<!doctype html>\n<h1>Hi</h1>\n", "style.css": "body { color: red; }\n",
                  "app.js": "function main() {\n  \n}\n", "package.json": "{}\n", "README.md": "# QA\n",
                  "config.toml": "# TOML comment\n[server]\nport = 8080\nname = \"rad\"\n",
                  "src/main.ts": "export const a = 1;\n", "notes.txt": "hello world\nTODO fix\n",
                  "prog.mini": "let x = 1\nprint bad\n"}.items():
    (site / rel).write_text(text, "utf-8")

from radide import theme as T  # noqa: E402
from radide import vsx  # noqa: E402
from radide.app import MainWindow  # noqa: E402
from radide.features import vsx_market as VM  # noqa: E402

THEME_LOG: list[str] = []
if os.environ.get("RADIDE_QA_TRACE_THEME"):
    import traceback
    _orig_apply = T._manager.apply

    def _traced_apply(setting, _o=_orig_apply):
        THEME_LOG.append(f"apply({setting!r}) from:\n" + "".join(traceback.format_stack(limit=14)[:-1]))
        return _o(setting)
    T._manager.apply = _traced_apply

win = MainWindow()
win.resize(1400, 900)
win.show()
win.activateWindow()
pump(1.0)
check(vsx.list_installed() == [], "starts with an empty scratch VSX root", vsx.root())
win.open_project(site)
pump(1.0)

# own extensions loaded
own_ids = {e.id for e in X.installed()}
check({"radide.solarized-theme", "radide.word-count-tools"} & own_ids or len(own_ids) >= 2,
      "IDE's own extensions installed", own_ids)
check(any("Solarized" in n for n in T.THEME_NAMES), "own extension theme (Solarized) registered", T.THEME_NAMES)

# --------------------------------------------------------------------- 1. Ctrl+Shift+X -> Extensions view
QTest.keyClick(win, Qt.Key.Key_X, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
pump(0.5)
dock = getattr(win, "dock_vsx", None)
if not (dock is not None and dock.isVisible()):
    note("Ctrl+Shift+X key event did not reach the window shortcut (offscreen focus); triggering the action")
    win.a_vsx_extensions.trigger()
    pump(0.5)
    dock = getattr(win, "dock_vsx", None)
check(dock is not None and dock.isVisible(), "Extensions view visible")
view = win.vsx_view
check(wait(lambda: view.market.count() > 0, 60), "Marketplace lists extensions on open", view.status.text())


def search(q):
    view.search.clear()
    QTest.keyClicks(view.search, q)
    QTest.keyClick(view.search, Qt.Key.Key_Return)
    return wait(lambda: "Searching" not in view.status.text() and view.market.count() > 0, 60)


def card_for(eid):
    for i in range(view.market.count()):
        c = view.market.itemWidget(view.market.item(i))
        if isinstance(c, VM.ExtCard) and c.ext_id == eid.lower():
            return c
    return None


def click_action(card, name):
    for i in range(card.buttons.count()):
        b = card.buttons.itemAt(i).widget()
        if isinstance(b, QPushButton) and b.property("vsxAction") == name:
            QTest.mouseClick(b, Qt.MouseButton.LeftButton)
            return True
    return False


def install_via_ui(query, eid, timeout=240):
    search(query)
    c = card_for(eid)
    if c is None:
        note(f"'{query}' did not list {eid}; searching @id:{eid}")
        search("@id:" + eid)
        c = card_for(eid)
    if c is None:
        check(False, f"card for {eid}", view.status.text())
        return False
    view.market.scrollToItem(view.market.item(next(i for i in range(view.market.count())
                                                   if view.market.itemWidget(view.market.item(i)) is c)))
    ok = click_action(c, "install")
    t0 = time.time()
    got = wait(lambda: vsx.get(eid) is not None and eid.lower() not in view._busy, timeout)
    check(ok and got, f"Install button: {eid}", f"{view.status.text()} {ANSWERS[-2:]}")
    if got:
        note(f"installed {eid} {vsx.get(eid).version} in {time.time() - t0:.1f}s")
    return got


ok = search("dracula")
check(ok and card_for("dracula-theme.theme-dracula") is not None, "search 'dracula' lists Dracula Official",
      view.status.text())
shot(win, "01_extensions_view_search.png")
install_via_ui("dracula", "dracula-theme.theme-dracula")
check(wait(lambda: "Dracula Theme" in T.THEME_NAMES, 10), "Dracula registered live as an IDE theme", T.THEME_NAMES)
c = card_for("dracula-theme.theme-dracula")
btns = [c.buttons.itemAt(i).widget().property("vsxAction") for i in range(c.buttons.count())] if c else []
check({"toggle", "uninstall"} <= set(btns), "card shows Disable / Uninstall after install", btns)
install_via_ui("one dark pro", "zhuangtongfa.material-theme")
install_via_ui("toml", "nifty.nifty-toml")
install_via_ui("javascript snippets", "xabikos.javascriptsnippets")
install_via_ui("material icon theme", "pkief.material-icon-theme", timeout=400)
shot(win, "02_extensions_installed.png")

# uninstall One Dark Pro from the Installed tab
view.tabs.setCurrentWidget(view.installed)
pump(0.3)
ic = None
for i in range(view.installed.count()):
    w = view.installed.itemWidget(view.installed.item(i))
    if isinstance(w, VM.ExtCard) and w.ext_id == "zhuangtongfa.material-theme":
        ic = w
check(ic is not None, "Installed tab lists One Dark Pro")
def _texts(w):
    if w is None:
        return ""
    labels = ([w] if isinstance(w, VM.QLabel) else []) + list(w.findChildren(VM.QLabel))
    return " ".join(lb.text() for lb in labels)


inst_text = " ".join(_texts(view.installed.itemWidget(view.installed.item(i))) for i in range(view.installed.count()))
own_listed = "RAD IDE extensions" in inst_text and "Solarized" in inst_text
check(own_listed, "Installed tab has the 'RAD IDE extensions' section")
shot(view, "03_installed_tab.png")
odp = vsx.get("zhuangtongfa.material-theme")
odp_dir = Path(odp.path).parent if odp else None
if ic is not None:
    click_action(ic, "uninstall")
check(wait(lambda: vsx.get("zhuangtongfa.material-theme") is None, 15), "Uninstall button removes One Dark Pro")
check(odp_dir is not None and not (odp_dir / "extension" / "package.json").exists(), "extension folder removed",
      odp_dir)
check(wait(lambda: "One Dark Pro" not in T.THEME_NAMES, 5), "One Dark Pro theme unregistered live")
st = json.loads((Path(os.environ["RADIDE_VSX_ROOT"]) / "extensions.json").read_text("utf-8"))
check("zhuangtongfa.material-theme" not in json.dumps(st).lower() and "dracula" in json.dumps(st).lower(),
      "extensions.json state updated", list(st)[:5])

# details page
c = card_for("dracula-theme.theme-dracula") or None
view.open_details("dracula-theme.theme-dracula", None)
pump(2.0)
det = VM._details.get("dracula-theme.theme-dracula")
check(det is not None and win.tabs.indexOf(det) >= 0, "details page opens as an editor tab")
if det is not None:
    win.tabs.setCurrentWidget(det)
    shot(win, "04_details_page.png")

# --------------------------------------------------------------------- 2. theme via Tools > Options
from radide.features.settings import OptionsDialog  # noqa: E402

ed_toml = win.open_file(site / "config.toml")
check(ed_toml is not None and wait(lambda: ed_toml._ready, 30), "config.toml opens in Monaco")
dlg = OptionsDialog(win)
idx = dlg.theme.findText("Dracula Theme")
check(idx >= 0, "Options colour theme list offers Dracula Theme")
dlg.theme.setCurrentIndex(idx)
note(f"theme combo after select: {dlg.theme.currentText()!r} (idx {idx}, count {dlg.theme.count()})")
shot(dlg, "05_options_theme.png")
note(f"theme combo before apply: {dlg.theme.currentText()!r} (count {dlg.theme.count()})")
dlg.apply()
note(f"saved options/theme = {win.settings.value('options/theme')!r}")
dlg.close()
pump(1.5)
check(T.current_name() == "Dracula Theme", "Dracula applied", T.current_name())
if THEME_LOG:
    (OUT / "theme_trace.txt").write_text("\n\n".join(THEME_LOG), "utf-8")
check(app.palette().window().color().name().upper() == "#21222C", "IDE chrome palette = Dracula",
      app.palette().window().color().name())
bg = js(ed_toml, "getComputedStyle(document.querySelector('.monaco-editor .monaco-editor-background')).backgroundColor")
check(bg == "rgb(40, 42, 54)", "Monaco background = Dracula", bg)

# --------------------------------------------------------------------- 3. grammar
check(ed_toml.language_id() == "toml", "toml language id", ed_toml.language_id())
check(wait(lambda: js(ed_toml, "window.vsxInfo ? vsxInfo().providers.indexOf('toml') >= 0 : false") is True, 30),
      "TextMate tokenizer active for toml")
toks = js(ed_toml, "JSON.stringify(vsxTokens(1))") or ""
check("comment.line.number-sign.toml" in toks, "TOML grammar scopes", toks[:160])
pump(0.6)
color = js(ed_toml, """(function(){ const s = Array.from(document.querySelectorAll('.view-line span span'))
  .find(x => /TOML.comment/.test(x.textContent)); return s ? getComputedStyle(s).color : null; })()""")
check(color == "rgb(98, 114, 164)", "comment rendered in Dracula comment colour", color)
shot(win, "06_ide_dracula_toml.png")

# --------------------------------------------------------------------- 4. snippets in the suggest widget
ed_js = win.open_file(site / "app.js")
check(ed_js is not None and wait(lambda: ed_js._ready, 30), "app.js opens")
wait(lambda: js(ed_js, "!!(window.vsxState && vsxState.spec)") is True, 20)
js(ed_js, """(function(){ radEditor.setPosition({lineNumber: 2, column: 3}); radEditor.focus();
  radEditor.trigger('kb', 'type', {text: 'clg'}); radEditor.trigger('t', 'editor.action.triggerSuggest', {}); })()""")
rows = []
wait(lambda: rows.append(js(ed_js, "Array.from(document.querySelectorAll('.suggest-widget .monaco-list-row'))"
                                   ".map(r => r.getAttribute('aria-label') || r.textContent).join('|')")) or
     "clg" in (rows[-1] or ""), 15)
check(rows and "clg" in (rows[-1] or ""), "suggest widget offers snippet 'clg'", rows[-1:] if rows else "")
shot(ed_js, "07_js_snippet_suggest.png")
js(ed_js, "radEditor.trigger('t', 'acceptSelectedSuggestion', {})")
check(wait(lambda: "console.log(" in ed_js.text(), 5), "accepting inserts console.log(...)", ed_js.text()[:80])

# --------------------------------------------------------------------- 5. icon theme in Solution Explorer
from radide.vsx import contrib_icons as CI  # noqa: E402

check(CI.active() is not None, "Material icon theme active after install")
win.solution.expandAll()
pump(0.5)
plain = win.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(16, 16).toImage()
items = {}
stack = [win.solution.topLevelItem(i) for i in range(win.solution.topLevelItemCount())]
while stack:
    x = stack.pop()
    items[x.text(0)] = x
    stack.extend(x.child(i) for i in range(x.childCount()))
themed = [n for n in ("index.html", "app.js", "config.toml", "package.json")
          if n in items and items[n].icon(0).pixmap(16, 16).toImage() != plain]
check(len(themed) >= 3, "Solution Explorer shows themed file icons", (themed, sorted(items)[:20]))
check(items.get("app.js") is not None and items.get("index.html") is not None and
      items["app.js"].icon(0).pixmap(16, 16).toImage() != items["index.html"].icon(0).pixmap(16, 16).toImage(),
      "different icons per file type")
shot(win.solution, "08_solution_explorer_icons.png")

# --------------------------------------------------------------------- 6. command extension (Install from VSIX)
svc = getattr(win, "vsx_host", None)
check(svc is not None, "extension host service present")
# an installed extension with code (e.g. a marketplace one with a "main") starts the host at once, like VS Code;
# with only declarative extensions no host runs
code_exts = [e.id for e in svc.code_extensions()] if svc is not None else []
check(svc is not None and wait(lambda: svc.host.running() == bool(code_exts), 30),
      "extension host runs exactly when an installed extension has code", (code_exts, svc and svc.host.running()))
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(HELLO_VSIX), ""))
win.a_vsx_install_vsix.trigger()
check(wait(lambda: vsx.get("radide-test.hello-commands") is not None, 30), "Install from VSIX (hello-commands)",
      view.status.text())
pump(0.5)
check(view.banner.isVisible() and "Restart required" in view.banner_text.text(), "'Restart required' banner shown",
      view.banner_text.text())
shot(view, "09_restart_banner.png")
QTest.mouseClick(view.banner_btn, Qt.MouseButton.LeftButton)
check(wait(lambda: svc.host.running() and svc.host.init_result is not None, 40), "Reload starts the extension host",
      svc.output.texts.get("Extension Host", "")[-300:] if hasattr(svc.output, "texts") else "")
check(wait(lambda: "radide-test.hello-commands" in svc.activation, 20), "hello-commands activated", svc.activation)
check(wait(lambda: not view.banner.isVisible(), 5), "banner hidden after reload", view.banner_text.text())
check(wait(lambda: any("Hello" in b.text() for b in svc.status_items.values() if b.isVisible()), 10),
      "status bar item from the extension", [b.text() for b in svc.status_items.values()])
from radide.features import command_palette as CP  # noqa: E402

box = CP.show_palette(win, ">Say Hello")
pump(0.4)
labels = [it.label for it in box.current_items()]
check(any("Say Hello" in lb for lb in labels), "Command Palette lists 'Hello: Say Hello'", labels[:6])
shot(win, "10_palette_say_hello.png")
n = len(ANSWERS)
for i in range(box.list.count()):
    if "Say Hello" in box.list.item(i).data(CP.ROLE).label:
        box.list.setCurrentRow(i)
        break
box.accept()
check(wait(lambda: any(a[0] == "box" and "Hello" in str(a[1]) for a in ANSWERS[n:]), 15),
      "running it from the palette shows the extension's message", ANSWERS[n:])
sb = [b for b in svc.status_items.values() if b.isVisible() and "Hello" in b.text()]
if sb:
    n = len(ANSWERS)
    QTest.mouseClick(sb[0], Qt.MouseButton.LeftButton)
    check(wait(lambda: len(ANSWERS) > n, 15), "clicking the status bar item runs its command", ANSWERS[n:])
shot(win.statusBar(), "11_status_bar.png")

# --------------------------------------------------------------------- 7. LSP extension
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(LSP_VSIX), ""))
win.a_vsx_install_vsix.trigger()
check(wait(lambda: vsx.get("radide-test.mini-lsp") is not None, 60), "Install from VSIX (mini-lsp)")
pump(0.5)
if view.banner.isVisible():
    QTest.mouseClick(view.banner_btn, Qt.MouseButton.LeftButton)
else:
    note("no restart banner after mini-lsp install")
check(wait(lambda: svc.host.running() and svc.host.init_result is not None and
           any(e.id == "radide-test.mini-lsp" for e in svc.extensions), 40), "host reloaded with mini-lsp")
from radide.vsx.lsp_client import CompositeClient  # noqa: E402

ed_m = win.open_file(site / "prog.mini")
check(ed_m is not None and wait(lambda: ed_m._ready, 30), "prog.mini opens")
check(ed_m is not None and ed_m.language_id() == "minilang", ".mini mapped to minilang",
      ed_m.language_id() if ed_m else None)
check(wait(lambda: "radide-test.mini-lsp" in svc.activation, 20), "mini-lsp activated (onLanguage)")
markers = []
check(wait(lambda: (markers.append(js(ed_m, "monaco.editor.getModelMarkers({}).map(m => m.message + '@' + "
                                            "m.startLineNumber)", 2)) or markers[-1]), 25),
      "language server diagnostics shown as Monaco markers", markers[-1:] if markers else None)
note(f"markers: {markers[-1] if markers else None}")
check(wait(lambda: isinstance(ed_m.lsp, CompositeClient), 10), "editor.lsp is the combined client")
js(ed_m, """(function(){ const m = radEditor.getModel(); const n = m.getLineCount();
  radEditor.executeEdits('t', [{range: new monaco.Range(n, m.getLineMaxColumn(n), n, m.getLineMaxColumn(n)),
                                text: '\\npr'}]);
  radEditor.setPosition({lineNumber: n + 1, column: 3}); radEditor.focus();
  radEditor.trigger('t', 'editor.action.triggerSuggest', {}); })()""")
rows = []
wait(lambda: rows.append(js(ed_m, "Array.from(document.querySelectorAll('.suggest-widget .monaco-list-row'))"
                                  ".map(r => r.getAttribute('aria-label') || r.textContent).join('|')")) or
     "print" in (rows[-1] or ""), 15)
check(rows and "print" in (rows[-1] or ""), "suggest widget shows language-server completion 'print'",
      rows[-1:] if rows else "")
shot(win, "12_lsp_completion_diagnostics.png")

# --------------------------------------------------------------------- 8. own extension dialog still works
from radide.features.extensions import ExtensionsDialog  # noqa: E402

xd = ExtensionsDialog(win)
xd.show()
pump(0.5)
names = [xd.list.item(i).text() for i in range(xd.list.count())]
check(len(names) >= 2, "IDE's own Extensions dialog lists its extensions", names)
shot(xd, "13_own_extensions_dialog.png")
xd.close()

# --------------------------------------------------------------------- 9. Arabic UI
from radide import i18n  # noqa: E402
from radide.features.ui_language import apply_language  # noqa: E402

apply_language(win, "ar", notify=False)
pump(1.0)
i18n._missing.clear()
view.tabs.setCurrentWidget(view.market)
search("dracula")
view.refresh_installed()
view.refresh_updates()
view.tabs.setCurrentWidget(view.installed)
pump(0.5)
shot(win, "14_arabic_extensions_view.png")
view.open_details("dracula-theme.theme-dracula", None)
pump(2.0)
det = VM._details.get("dracula-theme.theme-dracula")
if det is not None:
    win.tabs.setCurrentWidget(det)
    pump(0.5)
    shot(win, "15_arabic_details.png")
dlg = OptionsDialog(win)
from PyQt6.QtWidgets import QTabWidget  # noqa: E402

tabs = dlg.findChild(QTabWidget)
for i in range(tabs.count()):
    if tabs.tabText(i) == "VS Code Extensions":
        tabs.setCurrentIndex(i)
dlg.show()
pump(0.5)
shot(dlg, "16_arabic_options_vsx.png")
dlg.close()
box = CP.show_palette(win, ">Extensions")
pump(0.4)
shot(win, "17_arabic_palette.png")
box.close_box()


def visible_texts(root):
    from PyQt6.QtWidgets import QAbstractButton, QLabel
    out = []
    for w in root.findChildren((QLabel, QAbstractButton)):
        if w.isVisible():
            out.append(i18n.shown(w))
    return out


ui_words = ["Marketplace", "Installed", "Updates", "Install", "Uninstall", "Disable", "Enable", "Reload",
            "Restart required", "Details", "Changelog", "Contributions", "Dependencies", "Load more", "Manage...",
            "VS Code extensions", "RAD IDE extensions", "Search Extensions in Open VSX"]
shown = " | ".join(visible_texts(view) + (visible_texts(det) if det is not None else []))
leaks = [w for w in ui_words if f"| {w} |" in f"| {shown} |"]
check(not leaks, "no English UI words left in the Arabic Extensions view / details page", leaks)
check(i18n.tr("Marketplace") != "Marketplace" and i18n.tr("Install from VSIX...") != "Install from VSIX...",
      "catalog translates Extensions view strings", i18n.tr("Marketplace"))
probe = VM.ExtCard("golang.go", "Go", "golang", "Snippets", None)
view.tabs.setCurrentWidget(view.installed)       # a visible list inside the (translated) view
view.installed.addItem("")
view.installed.setItemWidget(view.installed.item(view.installed.count() - 1), probe)
control = VM.QLabel("Snippets")
view.installed.addItem("")
view.installed.setItemWidget(view.installed.item(view.installed.count() - 1), control)
pump(0.3)
note(f"control label (no i18n_skip) shows: {i18n.shown(control)!r}")
check(i18n.shown(probe.desc) == "Snippets" and i18n.shown(probe.pub) == "golang",
      "extension content is not run through the UI translator ('Snippets' stays 'Snippets')",
      (i18n.shown(probe.desc), i18n.tr("Snippets")))
tab_info = [(type(win.tabs.widget(i)).__name__, win.tabs.tabBar().tabText(i)) for i in range(win.tabs.count())]
note(f"editor tabs in Arabic: {tab_info}")
check(all(t[1].strip() for t in tab_info), "every editor tab has a title in Arabic", tab_info)
miss = sorted(i18n.missing())
note(f"untranslated strings seen while showing VSX UI in Arabic ({len(miss)}): {miss[:80]}")
(OUT / "arabic_missing.json").write_text(json.dumps(miss, ensure_ascii=False, indent=1), "utf-8")
apply_language(win, "en", notify=False)
pump(0.5)

# --------------------------------------------------------------------- finish
try:
    texts = getattr(svc.output, "texts", {}) or {}
    (OUT / "extension_host_log.txt").write_text(
        f"activation: {json.dumps(svc.activation, default=str)}\nunsupported: {svc.unsupported}\n\n" +
        "\n\n".join(f"===== {k}\n{v}" for k, v in texts.items()), "utf-8")
    note(f"host activations: {sorted(svc.activation) if isinstance(svc.activation, (dict, set, list)) else svc.activation}")
except Exception as ex:  # noqa: BLE001
    note(f"host log: {ex}")
tmr.stop()
try:
    svc.stop()
except Exception:  # noqa: BLE001
    pass
check(svc is None or not svc.host.running(), "extension host stopped")
win.close()
pump(0.5)
QSettings().clear()
shutil.rmtree(WORK, ignore_errors=True)
fails = [x for x in RESULTS if not x[0]]
print(f"\n{len(RESULTS) - len(fails)}/{len(RESULTS)} passed; screenshots in {OUT}")
for f in fails:
    print("FAILED:", f[1], f[2])
sys.exit(len(fails))
