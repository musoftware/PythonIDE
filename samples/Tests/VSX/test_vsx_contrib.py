"""VS Code declarative contributions end-to-end test (radide/vsx/contrib_*.py + radide/web/vsx/vsx-contrib.js).

Real extensions from Open VSX (downloaded into a cache, installed into a scratch RADIDE_VSX_ROOT):
    dracula-theme.theme-dracula      colour theme -> Monaco theme + the whole IDE chrome
    zhuangtongfa.material-theme      One Dark Pro (theme switching)
    nifty.nifty-toml                 TOML language + TextMate grammar + language configuration
    xabikos.JavaScriptSnippets       snippet pack
    PKief.material-icon-theme        file icon theme -> Solution Explorer icons
plus the local samples/Tests/VSX/contrib-test extension (grammar + injection, theme with "include",
snippets, keybindings, settings).

    python samples\\Tests\\VSX\\test_vsx_contrib.py [out_dir] [--onscreen]
"""
import json
import os
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile

ONSCREEN = "--onscreen" in sys.argv
if ONSCREEN:
    sys.argv.remove("--onscreen")
else:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if os.path.isdir(r"C:\Windows\Fonts"):                     # readable text in offscreen screenshots
        os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, ROOT)
OUT = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="radide_vsxc_out_")
os.makedirs(OUT, exist_ok=True)
WORK = tempfile.mkdtemp(prefix="radide_vsxc_")
os.environ["RADIDE_VSX_ROOT"] = os.path.join(WORK, "vsx")
CACHE = os.path.join(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir(), "RADIDE", "tools", "vsx-test-cache")
os.makedirs(CACHE, exist_ok=True)

EXTENSIONS = ["dracula-theme/theme-dracula", "zhuangtongfa/material-theme", "nifty/nifty-toml",
              "xabikos/JavaScriptSnippets", "PKief/material-icon-theme"]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def download(ext):
    meta = json.load(urllib.request.urlopen(f"https://open-vsx.org/api/{ext}", timeout=60))
    url = meta["files"]["download"]
    dest = os.path.join(CACHE, url.rsplit("/", 1)[1])
    if not os.path.isfile(dest):
        with urllib.request.urlopen(url, timeout=300) as r, open(dest + ".part", "wb") as f:
            shutil.copyfileobj(r, f)
        os.replace(dest + ".part", dest)
    return dest


def vsix_from_folder(folder, dest):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _dirs, files in os.walk(folder):
            for fn in files:
                p = os.path.join(base, fn)
                z.write(p, "extension/" + os.path.relpath(p, folder).replace("\\", "/"))
    return dest


# --------------------------------------------------------------------- 1. offline unit checks
from radide.vsx import contrib_common as CC  # noqa: E402

check("jsonc: comments + trailing commas", CC.read_jsonc(os.path.join(
    HERE, "contrib-test", "extension", "language-configuration.json"))["comments"]["lineComment"] == "--")
check("colour #RGBA / #RRGGBBAA blend", CC.solid("#FFFFFF80", "#000000") == "#808080" and CC.solid("#f00") == "#FF0000")
check("monaco colour keeps alpha", CC.monaco_color("#11223344") == "#11223344")

# --------------------------------------------------------------------- 2. install real extensions
from radide.vsx import manager as M  # noqa: E402

for e in EXTENSIONS:
    try:
        f = download(e)
        got = M.install_vsix_file(f, with_dependencies=False)
        check(f"install {e}", bool(got), os.path.basename(f))
    except Exception as ex:  # noqa: BLE001
        check(f"install {e}", False, str(ex))
local = vsix_from_folder(os.path.join(HERE, "contrib-test", "extension"), os.path.join(WORK, "contrib-test.vsix"))
check("install local contrib-test", bool(M.install_vsix_file(local, with_dependencies=False)))

from radide.vsx import contrib_themes as CT  # noqa: E402

specs = {s.label: s for s in CT.collect()}
check("themes collected", {"Dracula Theme", "One Dark Pro", "RAD Contrib Test Light"} <= set(specs), sorted(specs))
tl = specs.get("RAD Contrib Test Light")
if tl:
    m = CT.ScopeMatcher(tl.token_colors)
    check("theme include: base colours + override", tl.colors.get("editor.background") == "#FDF6E3" and
          tl.colors.get("statusBar.background") == "#6C71C4" and m.fg("comment") == "#93A1A1" and
          m.fg("keyword.control.radtest") == "#CB4B16", str(m.fg("keyword.control.radtest")))
    rules = {r["token"]: r for r in tl.monaco()["rules"]}
    check("semanticTokenColors -> Monaco rules", rules.get("function", {}).get("foreground") == "268BD2" and
          "italic" in rules.get("variable.readonly", {}).get("fontStyle", ""))
dr = specs.get("Dracula Theme")
tok = dr.tokens() if dr else {}
check("Dracula chrome tokens", tok.get("window") == "#21222C" and tok.get("tab_sel") == "#282A36" and
      tok.get("code", {}).get("comment") == "#6272A4" and tok.get("dark") is True, str({k: tok.get(k) for k in
                                                                                       ("window", "tab_sel")}))

# --------------------------------------------------------------------- 3. the IDE
__import__("PyQt6.QtWebEngineWidgets")                         # before QApplication
from pathlib import Path  # noqa: E402
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox, QStyle  # noqa: E402
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
QSettings().setValue("options/theme", "Dracula Theme")          # chosen in Options before
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes)
QMessageBox.warning = staticmethod(lambda *a, **k: print("WARNING BOX:", a[2:] if len(a) > 2 else a))
QMessageBox.information = staticmethod(lambda *a, **k: None)


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
    w.grab().save(os.path.join(OUT, name))


def js(ed, code, timeout=15.0):
    box = {}
    ed.page().runJavaScript(code, lambda v: box.setdefault("v", v))
    wait(lambda: "v" in box, timeout)
    return box.get("v")


def js_async(ed, code, timeout=20.0):
    """Run an expression that returns a Promise; poll its result."""
    key = f"__r{int(time.time() * 1000)}"
    js(ed, f"window.{key} = undefined; Promise.resolve({code}).then(v => window.{key} = JSON.stringify(v === undefined ? null : v))"
           f".catch(e => window.{key} = JSON.stringify({{error: String(e)}}));")
    wait(lambda: js(ed, f"window.{key} !== undefined") is True, timeout)
    v = js(ed, f"window.{key}")
    return json.loads(v) if v else None


from radide import theme as T  # noqa: E402
from radide.app import MainWindow  # noqa: E402

win = MainWindow()
win.resize(1400, 900)
win.show()
pump(1.0)
check("Dracula is an IDE theme", "Dracula Theme" in T.THEME_NAMES and "One Dark Pro" in T.THEME_NAMES)
check("Dracula applied at start-up", T.current_name() == "Dracula Theme", T.current_name())
check("palette from workbench colours", app.palette().window().color().name().upper() == "#21222C",
      app.palette().window().color().name())
check("status bar colour in the style sheet", "#191A21" in app.styleSheet())

# a web site with many file types (icons, languages)
site = Path(WORK) / "IconSite"
(site / "src" / "components").mkdir(parents=True)
(site / "assets").mkdir()
(site / "project.radproj").write_text(json.dumps({"name": "IconSite", "language": "static-web", "forms": [],
                                                   "startup": "", "modules": [], "kind": "website",
                                                   "web": {"root": ".", "start": "index.html"}}), "utf-8")
files = {"index.html": "<!doctype html>\n<h1>Hi</h1>\n", "style.css": "body { color: red; }\n",
         "app.js": "function main() {\n  \n}\n", "package.json": "{}\n", "README.md": "# Icons\n",
         "config.toml": "# TOML comment\n[server]\nport = 8080 # inline\nname = \"rad\"\nenabled = true\n",
         "Cargo.lock": "# lock\nversion = 3\n", "script.py": "print('x')\n",
         "demo.radt": "-- TODO: test the injection\nfunc hello(x)\n  return \"hi\\n\" 42\nend\n",
         "src/main.ts": "export const a = 1;\n", "src/components/App.vue": "<template></template>\n",
         "assets/logo.svg": "<svg xmlns='http://www.w3.org/2000/svg'/>\n", "data.json": "{\"a\": 1}\n"}
for rel, text in files.items():
    (site / rel).write_text(text, "utf-8")
win.open_project(site)
pump(1.5)

from radide import monaco_editor as ME  # noqa: E402
from radide.features import solution_ui as SU  # noqa: E402

check("file mapping .toml -> toml", ME.MONACO_LANG.get(".toml") == "toml", ME.MONACO_LANG.get(".toml"))
check("file name mapping Cargo.lock -> toml", ME.language_for_path(site / "Cargo.lock") == "toml")
check("new extension .radt -> radtest", ME.MONACO_LANG.get(".radt") == "radtest")
check("Language Mode menu lists TOML", any(lid == "toml" for _t, lid in ME.LANGUAGE_CHOICES))

# --------------------------------------------------------------------- 4. Solution Explorer icons
from radide.vsx import contrib_icons as CI  # noqa: E402

check("icon theme active (installed, never chosen)", CI.active() is not None and
      CI.active().info.theme_id == "pkief.material-icon-theme/material-icon-theme")
it = CI.active()
if it:
    check("icon resolution: file name / extension / folder", it.definition_for("package.json") == "nodejs" and
          it.definition_for("main.ts") == "typescript" and it.definition_for("src", is_dir=True) == "folder-src",
          f"{it.definition_for('package.json')} {it.definition_for('main.ts')} {it.definition_for('src', True)}")
plain = win.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(16, 16).toImage()
item = SU.find_item(win, "webfile", str((site / "index.html").resolve()))
if item is None:
    stack = [win.solution.topLevelItem(i) for i in range(win.solution.topLevelItemCount())]
    while stack and item is None:
        x = stack.pop()
        if x.text(0) == "index.html":
            item = x
        stack.extend(x.child(i) for i in range(x.childCount()))
check("Solution Explorer: themed file icon", item is not None and item.icon(0).pixmap(16, 16).toImage() != plain)
win.solution.expandAll()
pump(0.5)
shot(win.solution, "01_solution_explorer_material_icons.png")

# --------------------------------------------------------------------- 5. TOML grammar + Dracula in Monaco
ed = win.open_file(site / "config.toml")
check("config.toml opens in Monaco", ed is not None and hasattr(ed, "page"))
check("editor language toml", ed is not None and ed.language_id() == "toml", ed and ed.language_id())
wait(lambda: js(ed, "window.vsxInfo ? vsxInfo().providers.indexOf('toml') >= 0 : false") is True, 30)
info = js(ed, "JSON.stringify(vsxInfo())")
check("TextMate tokenizer for toml", info and "toml" in json.loads(info)["providers"], info)
toks = js(ed, "JSON.stringify(vsxTokens(1))")
check("TOML grammar scopes", toks and "comment.line.number-sign.toml" in toks, (toks or "")[:200])
wait(lambda: js(ed, "document.querySelectorAll('.view-line').length > 2") is True, 10)
pump(0.6)
color = js(ed, """(function(){ const spans = Array.from(document.querySelectorAll('.view-line span span'));
  const s = spans.find(x => /TOML.comment/.test(x.textContent)); return s ? getComputedStyle(s).color : null; })()""")
check("Dracula comment colour in the editor", color == "rgb(98, 114, 164)", color)
bg = js(ed, "getComputedStyle(document.querySelector('.monaco-editor .monaco-editor-background')).backgroundColor")
check("Dracula editor background", bg == "rgb(40, 42, 54)", bg)
comment_ok = js(ed, "(function(){ radEditor.setPosition({lineNumber: 2, column: 1}); "
                    "radEditor.trigger('t', 'editor.action.commentLine'); return radEditor.getModel().getLineContent(2); })()")
check("language configuration: line comment '#'", comment_ok == "# [server]", comment_ok)
js(ed, "radEditor.trigger('t', 'undo')")
shot(win, "02_ide_dracula_toml.png")
shot(ed, "03_monaco_toml_dracula.png")

# --------------------------------------------------------------------- 6. local grammar with injection + keybindings
ed2 = win.open_file(site / "demo.radt")
wait(lambda: js(ed2, "window.vsxInfo ? vsxInfo().providers.indexOf('radtest') >= 0 : false") is True, 30)
t1 = js(ed2, "JSON.stringify(vsxTokens(1))") or ""
check("injection grammar (TODO in comments)", "keyword.todo.radtest" in t1, t1[:200])
t3 = js(ed2, "JSON.stringify(vsxTokens(3))") or ""
check("grammar: string escape + number", "constant.character.escape.radtest" in t3 and "constant.numeric.radtest" in t3)
r = js(ed2, "(function(){ radEditor.focus(); radEditor.setPosition({lineNumber: 2, column: 1}); "
            "const ok = vsxRunKeybinding('ctrl+alt+k'); return ok + '|' + radEditor.getModel().getLineContent(2); })()")
check("keybinding -> Monaco command (when: resourceExtname == .radt)", r == "true|-- func hello(x)", r)
js(ed2, "radEditor.trigger('t', 'undo')")
from radide.vsx import contrib_keybindings as CK  # noqa: E402
called = []
CK.COMMAND_HANDLERS.append(lambda c, a: called.append((c, a)) or c == "contribtest.hello")
js(ed2, "vsxRunKeybinding('ctrl+alt+j')")
wait(lambda: bool(called), 5)
check("keybinding -> IDE command handler with args", called and called[0] == ("contribtest.hello", {"who": "world"}),
      str(called))
check("chord keybinding parsed", js(ed2, "vsxParseKey('ctrl+k ctrl+alt+u') !== null") is True)
sn = js_async(ed2, "vsxSnippets('radtest')") or []
check("snippets for a contributed language (array prefix)", {s["prefix"] for s in sn} >= {"func", "fn", "if"})

# --------------------------------------------------------------------- 7. JavaScript snippets
ed3 = win.open_file(site / "app.js")
wait(lambda: js(ed3, "!!(window.vsxState && vsxState.spec && window.radEditor)") is True, 30)
sn = js_async(ed3, "vsxSnippets('javascript')") or []
check("JavaScriptSnippets: clg snippet", any(s["prefix"] == "clg" for s in sn), str(len(sn)))
js(ed3, "radEditor.setPosition({lineNumber: 2, column: 3})")
ok = js_async(ed3, "vsxInsertSnippet('clg')")
pump(0.5)
check("snippet inserted", ok is True and "console.log(" in ed3.text(), ed3.text()[:80])
# the completion list (suggest widget) offers the snippet while typing its prefix
js(ed3, """(function(){ const m = radEditor.getModel(); const n = m.getLineCount();
  radEditor.executeEdits('t', [{range: new monaco.Range(n, 1, n, 1), text: 'cl'}]);
  radEditor.setPosition({lineNumber: n, column: 3}); radEditor.focus();
  radEditor.trigger('t', 'editor.action.triggerSuggest', {}); })()""")
rows = []
wait(lambda: rows.append(js(ed3, "Array.from(document.querySelectorAll('.suggest-widget .monaco-list-row'))"
                                 ".map(r => r.getAttribute('aria-label') || r.textContent).join('|')")) or
     "clg" in (rows[-1] or ""), 10)
check("suggest widget offers the snippet", rows and "clg" in (rows[-1] or ""), (rows[-1] or "")[:120] if rows else "")
shot(ed3, "04_monaco_js_snippet.png")

# --------------------------------------------------------------------- 8. theme switching
from radide.features import settings as S  # noqa: E402
win.settings.setValue("options/theme", "One Dark Pro")
S.apply_all(win)
pump(1.0)
win.tabs.setCurrentWidget(ed.parentWidget() if win.tabs.indexOf(ed) < 0 else ed)
pump(0.8)
color = js(ed, """(function(){ const s = Array.from(document.querySelectorAll('.view-line span span'))
  .find(x => /TOML.comment/.test(x.textContent)); return s ? getComputedStyle(s).color : null; })()""")
check("One Dark Pro comment colour", T.current_name() == "One Dark Pro" and color == "rgb(127, 132, 142)", color)
shot(win, "05_ide_one_dark_pro.png")
win.settings.setValue("options/theme", "Dark")
S.apply_all(win)
pump(1.0)
color = js(ed, """(function(){ const s = Array.from(document.querySelectorAll('.view-line span span'))
  .find(x => /TOML.comment/.test(x.textContent)); return s ? getComputedStyle(s).color : null; })()""")
check("built-in Dark theme: TextMate tokens with Dark+ colours", color == "rgb(106, 153, 85)", color)
win.settings.setValue("options/theme", "RAD Contrib Test Light")
S.apply_all(win)
pump(1.0)
check("light VS Code theme -> light IDE", not T.is_dark() and T.color("status") == "#6C71C4", T.color("status"))
shot(win, "06_ide_contrib_test_light.png")

# --------------------------------------------------------------------- 9. Options page + settings
from radide.features.settings import OptionsDialog  # noqa: E402
from radide.vsx import contrib_configuration as CF  # noqa: E402
dlg = OptionsDialog(win)
from PyQt6.QtWidgets import QTabWidget  # noqa: E402
tabs = dlg.findChild(QTabWidget)
titles = [tabs.tabText(i) for i in range(tabs.count())]
check("Options: VS Code Extensions page", "VS Code Extensions" in titles, str(titles))
check("Options: colour theme list has VS Code themes", dlg.theme.findText("Dracula Theme") >= 0)
page = tabs.widget(titles.index("VS Code Extensions")) if "VS Code Extensions" in titles else None
lst = getattr(page, "_vsx_list", None)
names = [lst.item(i).text() for i in range(lst.count())] if lst else []
check("settings page per extension", "RAD Contrib Test" in names, str(names))
if lst and "RAD Contrib Test" in names:
    tabs.setCurrentWidget(page)
    lst.setCurrentRow(names.index("RAD Contrib Test"))
    pump(0.3)
    shot(dlg, "07_options_vscode_extensions.png")
    from PyQt6.QtWidgets import QComboBox, QSpinBox  # noqa: E402
    combos = [c for c in page.findChildren(QComboBox) if c.findText("fast") >= 0]
    spins = [s for s in page.findChildren(QSpinBox) if s.maximum() == 10]
    if combos and spins:
        combos[0].setCurrentIndex(combos[0].findText("fast"))
        spins[0].setValue(7)
dlg.apply()
dlg.close()
check("settings saved to settings.json", CF.load().get("contribTest.mode") == "fast" and
      CF.get("contribTest.count") == 7 and CF.get("contribTest.name") == "RAD", str(CF.load()))

# --------------------------------------------------------------------- 10. disable / enable (refresh)
from radide import vsx  # noqa: E402
win.settings.setValue("options/theme", "Dracula Theme")
S.apply_all(win)
M.set_enabled("dracula-theme.theme-dracula", False)
pump(1.0)
check("disabled theme removed -> Light", "Dracula Theme" not in T.THEME_NAMES and T.current_name() == "Light",
      T.current_name())
M.set_enabled("dracula-theme.theme-dracula", True)
pump(1.0)
check("enabled again -> Dracula back", T.current_name() == "Dracula Theme", T.current_name())
M.set_enabled("pkief.material-icon-theme", False)
pump(0.8)
check("icon theme disabled -> IDE icons", CI.active() is None)
M.set_enabled("pkief.material-icon-theme", True)
pump(0.8)

failed = [r for r in results if not r[1]]
win.close()
pump(0.3)
QSettings().clear()
shutil.rmtree(WORK, ignore_errors=True)
print(f"\n{len(results) - len(failed)}/{len(results)} passed; screenshots in {OUT}")
sys.exit(1 if failed else 0)
