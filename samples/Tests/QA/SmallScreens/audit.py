"""Small-screen audit of RAD IDE (run by run_audit.py; one screen configuration per process).

Environment (set by run_audit.py):
  SS_TAG      name of the configuration (e.g. 1280x720-en)
  SS_OUT      output folder (JSON report + screenshots)
  SS_LANG     en | ar
  SS_THEME    Light | Dark
  SS_DIALOGS  1 = walk every menu command and record each window/dialog it opens
  SS_SHOTS    1 = widget.grab() screenshots of the main window and the biggest dialogs
QT_QPA_PLATFORM is "offscreen:configfile=screen.json" (cwd = the folder of screen.json) and
QT_SCALE_FACTOR simulates Windows display scaling.
"""
import os, sys, time, json, traceback
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-logging --log-level=3")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get("SS_ROOT") or os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
TAG = os.environ.get("SS_TAG", "default")
OUT = os.environ.get("SS_OUT") or os.path.join(HERE, "out")
SHOTS = os.path.join(OUT, "shots")
os.makedirs(SHOTS, exist_ok=True)
LANG = os.environ.get("SS_LANG", "en")
THEME = os.environ.get("SS_THEME", "Light")
WALK = os.environ.get("SS_DIALOGS", "1") == "1"
TAKE_SHOTS = os.environ.get("SS_SHOTS", "0") == "1"
MATCH = [m.strip().lower() for m in os.environ.get("SS_MATCH", "").split(",") if m.strip()]   # walk only these

__import__("PyQt6.QtWebEngineWidgets")          # before QApplication
from PyQt6.QtCore import QCoreApplication, QSettings, QObject, QEvent, Qt  # noqa: E402
from PyQt6.QtGui import QFont, QColor  # noqa: E402
from PyQt6.QtWidgets import (QApplication, QMessageBox, QDialog, QFileDialog, QInputDialog, QMenu,  # noqa: E402
                             QColorDialog, QFontDialog, QToolBar, QDockWidget, QWidget, QToolButton,
                             )

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST-ss-" + TAG.replace("@", "_"))
app = QApplication(sys.argv[:1])
app.setStyle("Fusion")
app.setFont(QFont("Segoe UI", 9))
_s = QSettings()
_s.clear()
_s.setValue("options/ui_language", LANG)
_s.setValue("options/theme", THEME)
_s.setValue("options/show_start_page", True)
_s.setValue("options/single_instance", False)
_s.sync()


def pump(sec=0.3):
    t = time.time()
    while time.time() - t < sec:
        app.processEvents()
        time.sleep(0.01)


# ------------------------------------------------------------------ non-blocking modal patches
SEEN = []            # (widget, origin)
CURRENT = {"origin": "startup"}


class Watch(QObject):
    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow() \
                    and not isinstance(obj, QMenu) and obj.windowType() not in (
                        Qt.WindowType.ToolTip, Qt.WindowType.Popup, Qt.WindowType.SplashScreen):
                if not any(w is obj for w, _ in SEEN):
                    SEEN.append((obj, CURRENT["origin"]))
        except RuntimeError:
            pass
        return False


_watch = Watch()
app.installEventFilter(_watch)
MEASURED = {}


def avail_for(w):
    scr = w.screen() or app.primaryScreen()
    return scr.availableGeometry()


def measure(w, origin):
    """Size facts of one top-level window (logical pixels)."""
    try:
        av = avail_for(w)
        fg = w.frameGeometry()
        msh = w.minimumSizeHint()
        mn = w.minimumSize()
        need_w = max(msh.width(), mn.width())
        need_h = max(msh.height(), mn.height())
        lay = w.layout()
        if lay is not None:
            lm = lay.totalMinimumSize()
            need_w, need_h = max(need_w, lm.width()), max(need_h, lm.height())
        title = w.windowTitle() or type(w).__name__
        return {
            "class": type(w).__module__ + "." + type(w).__name__, "title": title, "origin": origin,
            "size": [w.width(), w.height()], "frame": [fg.x(), fg.y(), fg.width(), fg.height()],
            "min_needed": [need_w, need_h], "avail": [av.x(), av.y(), av.width(), av.height()],
            "too_big": need_w > av.width() or need_h > av.height(),
            "exceeds": fg.width() > av.width() or fg.height() > av.height(),
            "offscreen": not av.contains(fg),
            "wrapped": bool(w.property("_rad_screenfit_wrapped")) or bool(
                [c for c in w.findChildren(QWidget) if c.property("_rad_screenfit_wrapped")]),
        }
    except RuntimeError:
        return None


def fake_exec(self, *a, **k):
    if isinstance(self, QMessageBox):
        return int(QMessageBox.StandardButton.No.value) if hasattr(QMessageBox.StandardButton.No, "value") else 0
    self.show()
    pump(0.35)
    rec = measure(self, CURRENT["origin"])
    if rec:
        MEASURED.setdefault(rec["class"] + "|" + rec["title"], rec)
        if TAKE_SHOTS and (rec["wrapped"] or rec["size"][0] * rec["size"][1] > 500000):
            try:
                self.grab().save(os.path.join(SHOTS, f"{TAG}-dlg-{type(self).__name__}.png"))
            except Exception:  # noqa: BLE001
                pass
    try:
        self.reject()
    except Exception:  # noqa: BLE001
        self.hide()
    return 0


QDialog.exec = fake_exec
QDialog.exec_ = fake_exec
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
for _n in ("warning", "critical", "information", "about", "aboutQt"):
    setattr(QMessageBox, _n, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
QMenu.exec = lambda self, *a, **k: None
QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ""))
QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ("", ""))
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
QInputDialog.getText = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getItem = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getInt = staticmethod(lambda *a, **k: (0, False))
QInputDialog.getMultiLineText = staticmethod(lambda *a, **k: ("", False))
QInputDialog.getDouble = staticmethod(lambda *a, **k: (0.0, False))
QColorDialog.getColor = staticmethod(lambda *a, **k: QColor())
QFontDialog.getFont = staticmethod(lambda *a, **k: (QFont(), False))
# ---- never start an external program from the audit (help viewers, browsers, emulators, Visual
# Studio, Explorer, terminals, database servers, pip ...): every process start fails instead
os.environ["RADIDE_NO_BROWSER"] = "1"
import subprocess  # noqa: E402
import webbrowser  # noqa: E402
BLOCKED = []


class _NoProcess(subprocess.Popen):
    def __init__(self, args, *a, **k):  # noqa: D401 - refuses every start
        BLOCKED.append(str(args)[:200])
        raise OSError("process start blocked by the small-screen audit")


subprocess.Popen = _NoProcess
os.system = lambda *a, **k: 1
for _n in ("spawnl", "spawnv", "spawnve", "spawnle", "execv", "execve"):
    if hasattr(os, _n):
        setattr(os, _n, lambda *a, **k: (_ for _ in ()).throw(OSError("blocked")))
from PyQt6.QtCore import QProcess  # noqa: E402
QProcess.start = lambda self, *a, **k: (BLOCKED.append("QProcess " + str(a)[:200]), self.errorOccurred.emit(
    QProcess.ProcessError.FailedToStart))[0] and None
QProcess.startDetached = lambda *a, **k: (BLOCKED.append("QProcess.startDetached " + str(a)[:200]), False)[1]
QProcess.startCommand = lambda self, *a, **k: BLOCKED.append("QProcess " + str(a)[:200])
webbrowser.open = lambda *a, **k: True
from PyQt6.QtGui import QDesktopServices  # noqa: E402
QDesktopServices.openUrl = staticmethod(lambda *a, **k: True)
os.startfile = lambda *a, **k: None

# commands that quit, start programs, touch the network/files or need a session
SKIP_WORDS = ("exit", "close", "new window", "start debugging", "without debugging", "stop", "restart",
              "step ", "run ", "run&", "build", "rebuild", "clean", "publish now", "deploy", "push", "pull",
              "fetch", "commit", "sync", "update", "install", "download", "check for", "uninstall", "reset",
              "delete", "remove", "save", "attach", "detach", "break all", "zen", "full screen", "full-screen",
              "exit", "quit", "sign in", "sign out", "log in", "share", "join", "record", "play",
              "toggle", "language", "english", "العربية", "theme", "dark", "light", "layout", "rescan",
              "restore", "kill", "terminate", "format document", "undo", "redo", "cut", "paste", "copy",
              "emulator", "device", "hot reload", "serve", "start server", "stop server", "test", "profile",
              "benchmark", "launch", "open in browser", "browser", "gc", "report issue", "venv", "freeze",
              "pip", "requirements", "kernel", "interpreter", "console", "terminal", "chm", "help files",
              "visual studio", "explorer", "external", "open folder in", "command prompt", "powershell",
              "start ", "database server", "server")


def walk_menus(win, deadline):
    from radide import i18n
    done = set()
    count = 0
    base_tabs = max(1, win.tabs.count())

    def visit(menu, path):
        nonlocal count
        try:
            menu.aboutToShow.emit()
        except Exception:  # noqa: BLE001
            pass
        for a in list(menu.actions()):
            if time.time() > deadline:
                return
            try:
                if a.isSeparator():
                    continue
                eng = i18n.english(a, a.text()) if hasattr(i18n, "english") else a.text()
                name = eng.replace("&", "").strip()
                full = path + " > " + name
                if a.menu() is not None:
                    visit(a.menu(), full)
                    continue
                if id(a) in done or not a.isEnabled() or not a.isVisible():
                    continue
                done.add(id(a))
                low = name.lower()
                if a.isCheckable() or any(wd in low for wd in SKIP_WORDS):
                    continue
                if MATCH and not any(m in full.lower() for m in MATCH):
                    continue
                CURRENT["origin"] = full
                print("ACT", full, flush=True)
                before = len(SEEN)
                try:
                    a.trigger()
                except Exception as e:  # noqa: BLE001
                    print("ERR", full, e, flush=True)
                count += 1
                pump(0.25)
                # windows that stayed open (non-modal tool windows): measure and close them
                for w, origin in SEEN[before:]:
                    try:
                        if w is win or not w.isVisible():
                            continue
                        rec = measure(w, origin)
                        if rec:
                            MEASURED.setdefault(rec["class"] + "|" + rec["title"], rec)
                            if TAKE_SHOTS and (rec["wrapped"] or rec["size"][0] * rec["size"][1] > 500000):
                                w.grab().save(os.path.join(SHOTS, f"{TAG}-win-{type(w).__name__}.png"))
                        w.close()
                    except RuntimeError:
                        pass
                # the tab that a command opened: close it again (keeps the window small)
                while win.tabs.count() > base_tabs:
                    try:
                        win.tabs.removeTab(win.tabs.count() - 1)
                    except Exception:  # noqa: BLE001
                        break
            except RuntimeError:
                continue

    for top in win.menuBar().actions():
        if top.menu() is not None:
            visit(top.menu(), top.text().replace("&", ""))
    return count


def toolbar_report(win):
    out = []
    for tb in win.findChildren(QToolBar):
        if not tb.isVisible() or tb.parent() is not win:
            continue
        acts = [a for a in tb.actions() if a.isVisible()]
        hidden = 0
        for a in acts:
            wdg = tb.widgetForAction(a)
            if wdg is None:
                continue
            if not wdg.isVisible():
                hidden += 1
                continue
            r = wdg.geometry()
            if r.right() > tb.width() or r.bottom() > tb.height():
                hidden += 1
        ext = [b for b in tb.findChildren(QToolButton) if b.objectName() == "qt_toolbar_ext_button"]
        out.append({"name": tb.objectName() or tb.windowTitle(), "width": tb.width(),
                    "min_w": tb.minimumSizeHint().width(), "size_hint_w": tb.sizeHint().width(),
                    "actions": len(acts), "cut_off": hidden,
                    "chevron": bool(ext and ext[0].isVisible()), "area": int(win.toolBarArea(tb).value)})
    return out


def dock_report(win):
    out = []
    for d in win.findChildren(QDockWidget):
        if d.parent() is not win:
            continue
        m = d.minimumSizeHint()
        out.append({"name": d.objectName(), "visible": d.isVisible(), "floating": d.isFloating(),
                    "min": [max(m.width(), d.minimumWidth()), max(m.height(), d.minimumHeight())],
                    "size": [d.width(), d.height()], "area": int(win.dockWidgetArea(d).value)})
    return out


def main_report(win):
    av = avail_for(win)
    msh = win.minimumSizeHint()
    lay = win.layout()
    tot = lay.totalMinimumSize() if lay is not None else msh
    cw = win.centralWidget()
    fg = win.frameGeometry()
    return {"avail": [av.x(), av.y(), av.width(), av.height()], "size": [win.width(), win.height()],
            "frame": [fg.x(), fg.y(), fg.width(), fg.height()],
            "min_hint": [msh.width(), msh.height()], "layout_min": [tot.width(), tot.height()],
            "min_needed": [max(msh.width(), tot.width(), win.minimumWidth()),
                           max(msh.height(), tot.height(), win.minimumHeight())],
            "central_min": [cw.minimumSizeHint().width(), cw.minimumSizeHint().height()] if cw else None,
            "statusbar_min_w": win.statusBar().minimumSizeHint().width(),
            "menubar_min_w": win.menuBar().minimumSizeHint().width(),
            "offscreen": not av.contains(fg), "explicit_min": [win.minimumWidth(), win.minimumHeight()],
            "props_tabbed_with": [d.objectName() for d in win.tabifiedDockWidgets(win.dock_props)],
            "workbench_mode": getattr(getattr(win, "workbench", None), "mode", None),
            "maximized": bool(win.windowState() & Qt.WindowState.WindowMaximized)}


def instantiate_classes(win):
    """Dialog classes the menu walk did not reach: build them directly (best effort)."""
    import importlib, re, pathlib
    rx = re.compile(r"^class (\w+)\((Q\w*Dialog|QWizard)\b", re.M)
    found = []
    for p in pathlib.Path(ROOT, "radide").rglob("*.py"):
        try:
            txt = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in rx.finditer(txt):
            mod = ".".join(p.relative_to(ROOT).with_suffix("").parts)
            found.append((mod, m.group(1)))
    seen_classes = {r["class"] for r in MEASURED.values()}
    for mod, cls in found:
        if f"{mod}.{cls}" in seen_classes:
            continue
        CURRENT["origin"] = f"direct {mod}.{cls}"
        try:
            C = getattr(importlib.import_module(mod), cls)
        except Exception as e:  # noqa: BLE001
            print("IMPORT", mod, cls, e)
            continue
        obj = None
        for args in ((win,), (), (None,)):
            try:
                obj = C(*args)
                break
            except Exception:  # noqa: BLE001
                continue
        if obj is None:
            continue
        try:
            fake_exec(obj)
            obj.deleteLater()
        except Exception as e:  # noqa: BLE001
            print("SHOW", cls, e)


def main():
    from radide.app import MainWindow
    report = {"tag": TAG, "lang": LANG, "theme": THEME,
              "screen": [app.primaryScreen().geometry().width(), app.primaryScreen().geometry().height()],
              "dpr": app.primaryScreen().devicePixelRatio()}
    t0 = time.time()
    win = MainWindow()
    # what a fresh install does (main(): no explicit size; MainWindow.__init__ resizes to 1280x800)
    if os.environ.get("SS_SAVED_BIG") == "1":       # geometry saved on a big monitor: restore it here
        win.resize(1900, 1040)
        win.move(1800, 900)
    win.show()
    pump(4)
    report["startup_s"] = round(time.time() - t0, 1)
    report["main"] = main_report(win)
    report["toolbars"] = toolbar_report(win)
    report["docks"] = dock_report(win)
    if TAKE_SHOTS:
        win.grab().save(os.path.join(SHOTS, f"{TAG}-main.png"))
    # the smallest the user can make it
    win.showNormal()
    pump(0.3)
    win.resize(200, 200)
    pump(0.6)
    report["main_min_after_shrink"] = [win.width(), win.height()]
    win.resize(min(1280, report["main"]["avail"][2]), min(800, report["main"]["avail"][3]))
    pump(0.5)
    if WALK and os.environ.get("SS_PROJECT", "HelloPython") != "0":
        # a copy of a sample project, so that the Project / Debug / Format commands are enabled
        import shutil, tempfile
        src = os.path.join(ROOT, "samples", os.environ.get("SS_PROJECT", "HelloPython"))
        dst = os.path.join(tempfile.mkdtemp(prefix="radide-ss-proj-"), os.path.basename(src))
        shutil.copytree(src, dst)
        try:
            from pathlib import Path
            win.open_project(Path(dst), ask=False)
            pump(3)
            report["project"] = os.path.basename(src)
        except Exception as e:  # noqa: BLE001
            print("PROJECT", e)
    if WALK:
        n = walk_menus(win, time.time() + float(os.environ.get("SS_WALK_SECONDS", "420")))
        report["commands_triggered"] = n
        if not MATCH:
            instantiate_classes(win)
    recs = sorted(MEASURED.values(), key=lambda r: r["class"])
    report["windows"] = recs
    report["blocked_process_starts"] = BLOCKED[:200]
    report["windows_too_big"] = [r for r in recs if r["too_big"]]
    report["windows_exceeding"] = [r for r in recs if r["exceeds"] or r["offscreen"]]
    with open(os.path.join(OUT, f"{TAG}.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    m = report["main"]
    print(f"[{TAG}] main min {m['min_needed']} avail {m['avail'][2:]} frame {m['frame']}; windows {len(recs)}, "
          f"too big {len(report['windows_too_big'])}, exceeding {len(report['windows_exceeding'])}", flush=True)
    QSettings().clear()
    QSettings().sync()
    os._exit(0)


try:
    main()
except Exception:  # noqa: BLE001
    traceback.print_exc()
    QSettings().clear()
    os._exit(2)
