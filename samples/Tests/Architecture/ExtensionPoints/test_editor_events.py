"""Characterization of the features that follow designers, code editors, saving and window details, while they
move from wrapping MainWindow (open_designer, open_code, _save_form, _save_active_project, save_current,
_designer_menu, _editor_menu, _codeview, open_module, project_properties, _update_title, log, restoreState,
_confirm_close_project) to radide/extension_points.py.

Real MainWindow (offscreen), a Python Tk project:
  * open_designer: user controls folder registered BEFORE; after it: localization preview + variant bar on the
    designer, animations panel follows, mobile hinge watch, user controls Toolbox refresh
  * a damaged .form: open_designer / open_code show "Cannot open form" and return None (no exception)
  * _save_form: format-on-save BEFORE writing; after it: localization resources, file integrity remembers
  * _save_active_project: format-on-save of every open code editor BEFORE, VB6 mirror sync after
  * save_current: VB6 mirror sync after
  * designer context menu: Add Animation (a control), Layout Size (variants), localization entry (the form)
  * code editor context menu: "Send Selection to AI Web Chat"
  * _codeview / open_module: the language-server client is looked up for the new editor
  * project_properties of a VB6 mirror project: the VB6 dialog instead of the window's
  * _update_title: the agent panel follows a new default folder
  * restoreState: auto-hide docks and the dock tab-bar fix re-applied
  * open a foreign project without asking: no "save changes?" question

Run:  .venv\\Scripts\\python samples\\Tests\\Architecture\\ExtensionPoints\\test_editor_events.py [scratch]
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ["RADIDE_NO_BROWSER"] = "1"
os.environ["RADIDE_TEST_NO_DIALOGS"] = "1"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / "radide-editorevents"
shutil.rmtree(SCRATCH, ignore_errors=True)
SCRATCH.mkdir(parents=True, exist_ok=True)

__import__("PyQt6.QtWebEngineWidgets")          # must come before the QApplication
from PyQt6.QtCore import QCoreApplication, QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox  # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST-ARCH-EDITOR_EVENTS")      # own store: tests run in parallel
QCoreApplication.setApplicationName("RADIDE-TEST-ARCH-EDITOR_EVENTS")
app = QApplication(sys.argv[:1])
QSettings().clear()
ASKED: list[str] = []
ERRORS: list[str] = []
QMessageBox.question = staticmethod(lambda *a, **k: (ASKED.append(str(a[2] if len(a) > 2 else "")),
                                                     QMessageBox.StandardButton.Discard)[1])
QMessageBox.critical = staticmethod(lambda *a, **k: (ERRORS.append(str(a[1:3])), QMessageBox.StandardButton.Ok)[1])
QMessageBox.warning = staticmethod(lambda *a, **k: (ERRORS.append(str(a[1:3])), QMessageBox.StandardButton.Ok)[1])
QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

results: list[tuple[str, bool]] = []


def ok(name: str, cond, detail="") -> bool:
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:800]}]"), flush=True)
    return bool(cond)


def pump(n: int = 10) -> None:
    for _ in range(n):
        app.processEvents()


from radide import workspace  # noqa: E402
from radide.app import MainWindow  # noqa: E402

proj = SCRATCH / "EdEvents"
workspace.create_project(proj, "EdEvents", "python-tk")
win = MainWindow()
win.resize(1200, 800)
win.show()
pump()
win.open_project(proj, ask=False)
pump()

import radide.features.dock_tabbar_fix as dock_tabbar_fix  # noqa: E402
import radide.features.formatting as formatting  # noqa: E402
import radide.features.localization as localization  # noqa: E402
import radide.features.mobile as mobile  # noqa: E402
import radide.usercontrols as uc  # noqa: E402
from radide.foreign import vb6_project  # noqa: E402

vb6_project.install_hooks(win)              # installed when a VB6 project opens
COUNT: dict[str, int] = {}
ORDER: list[str] = []


def spy(name, ret=None):
    def f(*_a, **_k):
        COUNT[name] = COUNT.get(name, 0) + 1
        ORDER.append(name)
        return ret
    return f


SAVED: list = []


def patch(obj, attr, fn):
    SAVED.append((obj, attr, getattr(obj, attr)))
    setattr(obj, attr, fn)


def restore():
    while SAVED:
        obj, attr, val = SAVED.pop()
        setattr(obj, attr, val)


# ------------------------------------------------------------------ open_designer
try:
    patch(uc, "register_folder", spy("user controls folder"))
    patch(win.animations_panel, "bind", spy("animations follow"))
    patch(mobile, "watch_hinge", spy("mobile hinge"))
    patch(win.user_controls, "refresh_toolbox", spy("user controls Toolbox"))
    orig_open = win.open_designer
    COUNT.clear()
    ORDER.clear()
    patch(win, "_doc", (lambda real: (lambda n: (ORDER.append("window loads the form"), real(n))[1]))(win._doc))
    win.open_designer("Form1")
    pump()
    v = win.designers.get("Form1")
    ok("open_designer: the designer is open", v is not None)
    ok("open_designer: user controls folder registered before the form loads",
       "user controls folder" in ORDER and ORDER.index("user controls folder") < ORDER.index("window loads the form"),
       ORDER)
    ok("open_designer: localization preview attached", getattr(v, "_loc_preview", None) is not None)
    ok("open_designer: variant bar attached", getattr(v, "_variant_bar", None) is not None)
    for name in ("animations follow", "mobile hinge", "user controls Toolbox"):
        ok(f"open_designer: {name}", COUNT.get(name, 0) >= 1, COUNT)
finally:
    restore()

# a damaged form
try:
    bad = proj / "Broken.form"
    bad.write_text("{ this is not json", encoding="utf-8")
    win.project.forms.append("Broken")
    ERRORS.clear()
    try:
        r = win.open_designer("Broken")
        ok("damaged form: open_designer returns None (no exception)", r is None, r)
    except Exception as e:  # noqa: BLE001
        ok("damaged form: open_designer returns None (no exception)", False, repr(e))
    ok("damaged form: 'Cannot open form' is shown", any("Cannot open form" in m for m in ERRORS), ERRORS)
    ERRORS.clear()
    try:
        r = win.open_code("Broken")
        ok("damaged form: open_code returns None (no exception)", r is None, r)
    except Exception as e:  # noqa: BLE001
        ok("damaged form: open_code returns None (no exception)", False, repr(e))
    ok("damaged form: open_code shows 'Cannot open form'", any("Cannot open form" in m for m in ERRORS), ERRORS)
    win.project.forms.remove("Broken")
    bad.unlink()
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    ok("damaged form part", False, e)

# ------------------------------------------------------------------ saving
try:
    patch(formatting, "format_before_save", spy("format on save"))
    patch(localization, "write_resx", spy("localization resources"))
    patch(win.file_integrity, "remember", spy("file integrity remembers"))
    patch(vb6_project, "sync_project_of", spy("VB6 sync"))
    win.open_code("Form1")
    pump()
    doc = win.docs["Form1"]
    doc.form.props["Localizable"] = True
    COUNT.clear()
    ORDER.clear()
    win._save_form("Form1")
    pump()
    ok("_save_form: localization resources written", COUNT.get("localization resources") == 1, COUNT)
    ok("_save_form: file integrity remembers the form", COUNT.get("file integrity remembers", 0) >= 1, COUNT)
    doc.form.props.pop("Localizable", None)
    COUNT.clear()
    win._save_active_project()
    pump()
    ok("_save_active_project: VB6 mirror sync after", COUNT.get("VB6 sync") == 1, COUNT)
    COUNT.clear()
    win.save_current()
    pump()
    ok("save_current: VB6 mirror sync after", COUNT.get("VB6 sync", 0) >= 1, COUNT)
finally:
    restore()

# format on save (only when Tools > Options enables it): before the form is written
try:
    if hasattr(formatting, "format_before_save"):
        win.settings.setValue("format/on_save", True)
        patch(formatting, "format_before_save", spy("format on save"))
        COUNT.clear()
        win._save_active_project()
        pump()
        fos = COUNT.get("format on save", 0)
        ok("format on save: _save_active_project formats the open editors once (no second time per form)",
           fos == 1, COUNT)
        win.settings.setValue("format/on_save", False)
finally:
    restore()

# ------------------------------------------------------------------ context menus
try:
    win.open_designer("Form1")                  # variants add their entries for the current designer
    pump()
    v = win.designers["Form1"]
    btn = v.doc.add_control("Button", 20, 20)
    m = QMenu()
    win._designer_menu("Form1", m, btn)
    titles = [x.title() for x in m.findChildren(QMenu)]
    ok("designer menu of a control: Add Animation", "Add Animation" in titles, titles)
    ok("designer menu: Layout Size (variants)", any("Layout Size" in t for t in titles), titles)
    m2 = QMenu()
    win._designer_menu("Form1", m2, None)
    texts2 = [a.text() for a in m2.actions()]
    ok("designer menu of the form: a localization entry", any("ocaliz" in t or "anguage" in t for t in texts2),
       texts2)
    m3 = QMenu()
    win._editor_menu(m3, "Form1")
    ok("code editor menu: Send Selection to AI Web Chat",
       any("AI Web Chat" in a.text() for a in m3.actions()), [a.text() for a in m3.actions()])
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    ok("menus part", False, e)

# ------------------------------------------------------------------ editors get a language server
try:
    looked: list = []
    patch(win.lsp_manager, "client_for", lambda lang, root: looked.append(lang) or None)
    win.codeviews.pop("Form1", None)
    cv = win._codeview("Form1")
    import time
    t0 = time.time()
    while time.time() - t0 < 30 and not looked:
        pump()
    ok("_codeview: the language-server client is looked up for the new code editor", bool(looked), looked)
    (proj / "helper.py").write_text("x = 1\n", encoding="utf-8")
    win.project.modules.append("helper.py")
    looked.clear()
    win.open_module("helper.py")
    t0 = time.time()
    while time.time() - t0 < 30 and not looked:
        pump()
    ok("open_module: ... and for a module editor", bool(looked), looked)
finally:
    restore()

# ------------------------------------------------------------------ VB6 project properties, title, layout
try:
    patch(vb6_project, "is_mirror", lambda folder: True)
    patch(vb6_project, "project_properties_dialog", spy("VB6 properties dialog"))
    COUNT.clear()
    win.project_properties()
    ok("project_properties of a VB6 mirror project: the VB6 dialog", COUNT.get("VB6 properties dialog") == 1, COUNT)
finally:
    restore()
try:
    am = win.agent_manager
    patch(am, "default_folder", lambda: str(SCRATCH / "another"))
    patch(am, "project_opened", spy("agents follow the folder"))
    am._last_folder = None
    COUNT.clear()
    win._update_title()
    ok("_update_title: the agent panel follows a new default folder", COUNT.get("agents follow the folder") == 1, COUNT)
finally:
    restore()
try:
    patch(win.autohide, "after_restore_state", spy("auto-hide docks"))
    patch(dock_tabbar_fix, "schedule", spy("dock tab bars"))
    COUNT.clear()
    win.restoreState(win.saveState())
    ok("restoreState: auto-hide docks re-applied", COUNT.get("auto-hide docks") == 1, COUNT)
    ok("restoreState: dock tab-bar fix scheduled", COUNT.get("dock tab bars") == 1, COUNT)
finally:
    restore()

# ------------------------------------------------------------------ a foreign project without asking
try:
    win._doc("Form1").set_modified(True)
    vbp = SCRATCH / "Vb6" / "Hello.vbp"
    vbp.parent.mkdir(parents=True, exist_ok=True)
    (vbp.parent / "Form1.frm").write_text('VERSION 5.00\nBegin VB.Form Form1\n   Caption = "Hi"\nEnd\n',
                                          encoding="utf-8")
    vbp.write_text('Type=Exe\nForm=Form1.frm\nStartup="Form1"\nName="Hello"\n', encoding="utf-8")
    ASKED.clear()
    win.open_project(vbp, ask=False)
    pump()
    ok("a foreign project opened without asking: no 'save changes?' question", not ASKED, ASKED)
    ok("... and the window asks again afterwards (the skip was temporary)",
       "_confirm_close_project" not in vars(win) and getattr(win, "_no_save_questions", 0) == 0,
       getattr(win, "_no_save_questions", None))
except Exception as e:  # noqa: BLE001
    import traceback
    traceback.print_exc()
    ok("foreign project part", False, e)

try:
    for d in list(win.docs.values()):
        d.set_modified(False)
    win.close()
except Exception:  # noqa: BLE001
    pass
QSettings().clear()
fails = sum(1 for _n, c in results if not c)
print(f"\n{len(results) - fails}/{len(results)} passed", flush=True)
os._exit(fails)
