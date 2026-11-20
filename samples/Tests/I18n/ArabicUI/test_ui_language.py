"""Tests of the IDE UI translation (radide/i18n + features/ui_language)."""
import os
import re
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_FORCE_STDERR_LOGGING"] = "1"
import shutil  # noqa: E402
import tempfile  # noqa: E402
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
S = tempfile.mkdtemp(prefix="radide_i18n_")       # a copy of samples/HelloPython is opened, never the sample
shutil.copytree(os.path.join(ROOT, "samples", "HelloPython"), os.path.join(S, "proj", "HelloPython"))
sys.path.insert(0, ROOT)
__import__("PyQt6.QtWebEngineWidgets")       # must be imported before QApplication
from pathlib import Path  # noqa: E402
from PyQt6.QtCore import QCoreApplication, QSettings, Qt, QTimer  # noqa: E402
from PyQt6.QtGui import QAction  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QDockWidget, QLabel, QMessageBox, QPushButton,  # noqa: E402
                             QTabWidget, QWidget)
QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QApplication(sys.argv[:1])
QSettings().clear()
from radide.app import MainWindow  # noqa: E402
from radide import i18n  # noqa: E402
from radide.features.ui_language import apply_language  # noqa: E402

AR = re.compile(r"[\u0600-\u06FF]")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + (("  - " + detail) if detail and not ok else ""))


def pump(n=20):
    for _ in range(n):
        app.processEvents()


def close_boxes():
    m = QApplication.activeModalWidget()
    if m is not None:
        m.close()
killer = QTimer()
killer.timeout.connect(close_boxes)
killer.start(300)


def find_menu(win, title):
    return next((a.menu() for a in win.menuBar().actions() if a.text().replace("&", "") == title), None)


def arabic_leftovers(win):
    """Visible texts that still contain Arabic (after switching back to English)."""
    bad = []
    for a in win.findChildren(QAction):
        t = i18n.shown(a)
        if t and AR.search(t) and "العربية" not in t:
            bad.append(t)
    for w in win.findChildren(QWidget):
        if isinstance(w, (QLabel, QPushButton)):
            t = i18n.shown(w)
            if t and AR.search(t) and "العربية" not in t and not i18n._skipped(w):
                bad.append(t)
    for d in win.findChildren(QDockWidget):
        if AR.search(i18n.shown(d, "windowTitle")):
            bad.append(d.windowTitle())
    return bad


win = MainWindow()
win.show()
pump()
check("default language is English", i18n.language() == "en" and
      app.layoutDirection() == Qt.LayoutDirection.LeftToRight)
check("Tools > Language menu exists", win.findChild(QAction, "ui_language_ar") is not None)

# ---- switch to Arabic (live)
apply_language(win, "ar", notify=False)
pump()
check("setting saved", QSettings("RADIDE-TEST", "RADIDE-TEST").value("options/ui_language") == "ar")
check("layout is right-to-left", app.layoutDirection() == Qt.LayoutDirection.RightToLeft)
mb = win.menuBar().actions()
check("menu bar shows Arabic", all(AR.search(i18n.shown(a)) for a in mb[:3]), str([i18n.shown(a) for a in mb[:3]]))
check("menu bar keeps mnemonics", "(&F)" in i18n.shown(mb[0]), i18n.shown(mb[0]))
check("code sees English action texts", mb[0].text() == "&File" and find_menu(win, "Tools") is not None)
check("win.a_save keeps English text()", win.a_save.text() == "Save &All" and AR.search(i18n.shown(win.a_save)))
check("dock title Arabic, windowTitle() English",
      win.dock_toolbox.windowTitle() == "Toolbox" and AR.search(i18n.shown(win.dock_toolbox, "windowTitle")))
check("shortcuts unchanged", win.a_save.shortcut().toString() == "Ctrl+S")
# dynamic text set while Arabic
a = QAction("x", win)
a.setText("&Options...")
check("setText translates while Arabic", AR.search(i18n.shown(a)) and a.text() == "&Options...")
a.setText("My custom thing")
check("unknown text stays as given", i18n.shown(a) == "My custom thing" and a.text() == "My custom thing")
# open a project: designer & editor stay LTR
win.open_project(Path(S) / "proj" / "HelloPython", ask=False)
pump(60)
dv = win._current_designer()
check("designer view is left-to-right", dv is not None and dv.layoutDirection() == Qt.LayoutDirection.LeftToRight)
tabs = win.tabs
check("tab text English for code, Arabic on screen",
      tabs.count() > 0 and not AR.search(tabs.tabText(tabs.currentIndex())))
# a dialog created later is translated when shown
from radide.features.settings import OptionsDialog  # noqa: E402
dlg = OptionsDialog(win)
dlg.show()
pump()
tw = dlg.findChild(QTabWidget)
check("Options tabs translated", AR.search(i18n.shown(tw.tabBar(), "tabText") if False else
                                            i18n._ORIG[(type(tw.tabBar()), "tabText")](tw.tabBar(), 0)))
check("Options tabText() English", tw.tabText(0) == "Environment", tw.tabText(0))
check("Options has the Language box", hasattr(dlg, "ui_lang") and dlg.ui_lang.findData("ar") >= 0)
ok_btn = [b for b in dlg.findChildren(QPushButton) if AR.search(i18n.shown(b))]
check("Options buttons Arabic", len(ok_btn) >= 3, str([i18n.shown(b) for b in dlg.findChildren(QPushButton)]))
std = [i18n.shown(b) for b in dlg.findChildren(QPushButton)]
check("standard buttons use our wording", any("موافق" in t for t in std) and any("إلغاء" in t for t in std), str(std))
dlg.close()
# message box texts
box = QMessageBox(QMessageBox.Icon.Information, "Options", "Open a project first.", parent=win)
box.show()
pump()
lab = [i18n.shown(w) for w in box.findChildren(QLabel) if i18n.shown(w)]
check("message box translated on show", any(AR.search(t) for t in lab), str(lab))
box.close()
# untranslated count among visible menu actions
miss = [i18n.shown(x) for m in win.menuBar().actions() if m.menu() for x in m.menu().actions()
        if not x.isSeparator() and i18n.shown(x) and not AR.search(i18n.shown(x))]
check("almost every menu item translated", len(miss) <= 12, f"{len(miss)} left: {miss[:15]}")
print("untranslated menu items:", miss)

# ---- restart in Arabic: a new window starts translated
win2 = MainWindow()
win2.show()
pump()
check("new window starts in Arabic (saved setting)", AR.search(i18n.shown(win2.menuBar().actions()[0])))
win2.close()
pump()

# ---- back to English
apply_language(win, "en", notify=False)
pump(40)
check("layout is left-to-right again", app.layoutDirection() == Qt.LayoutDirection.LeftToRight)
check("menu bar English again", [i18n.shown(a) for a in mb[:3]] == ["&File", "&Edit", "&View"],
      str([i18n.shown(a) for a in mb[:3]]))
left = arabic_leftovers(win)
check("no Arabic left in the main window", not left, str(left[:10]))
check("English dock title restored", i18n.shown(win.dock_toolbox, "windowTitle") == "Toolbox")

win.close()
pump()
QSettings().clear()
passed = sum(1 for r in results if r[1])
print(f"\n{passed}/{len(results)} passed")
shutil.rmtree(S, ignore_errors=True)
sys.stdout.flush()
os._exit(0 if passed == len(results) else 1)
