"""Shared harness of the feature inventory (tools/feature_inventory.py) and the action crawler
(samples/Tests/Crawler/test_action_crawler.py).

* env()            the offscreen test environment (own QSettings org "RADIDE-TEST-CRAWL", no browser, no GPU)
* CONTEXTS         one sample project per project kind (copied into a sandbox before it is opened)
* boot()           QApplication + MainWindow (offscreen), menus that would pop up are captured, never shown
* open_context()   sandbox copy of a context's project, opened in the IDE
* harvest()        every user-facing entry point of the window as it is now: menu bar (aboutToShow emitted so
                   dynamic menus fill), tool bars, Command Palette commands, context menus (Solution Explorer
                   items, editor tabs, designer, editors, every dock with a custom context menu)
Nothing here starts external programs: os.startfile, webbrowser, QDesktopServices.openUrl and
QProcess.startDetached are recorded instead (RECORDED), and hh.exe / explorer.exe launches are refused by an
audit hook. Widget.grab only.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORG = "RADIDE-TEST-CRAWL"

ENV = {
    "PYTHONIOENCODING": "utf-8",
    "QT_QPA_PLATFORM": "offscreen",
    "QT_QPA_FONTDIR": r"C:\Windows\Fonts",
    "RADIDE_NO_BROWSER": "1",
    "RADIDE_NO_UPDATE_CHECK": "1",
    "QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu --disable-gpu-compositing",
    "QT_FORCE_STDERR_LOGGING": "1",
}

# context id -> (project folder relative to the repository | None, what it stands for)
CONTEXTS: dict[str, tuple[str | None, str]] = {
    "none": (None, "no project open (Start Page)"),
    "python-tk": ("samples/Tests/Languages/PythonTk_Form", "Python Tk form project"),
    "vb6": ("samples/Tests/Languages/VB_Form", "VB6 (vb-basic) form project"),
    "csharp": ("samples/HelloCSharp", "C# form project"),
    "web": ("samples/Tests/Web/StaticBootstrapSite", "static web site"),
    "flask": ("samples/Tests/Web/Flask_Todo", "Python Flask web project (project actions provider)"),
    "flutter": ("samples/Tests/Mobile/Flutter_Screens", "Flutter mobile project"),
    "retro": ("samples/Examples/Retro/NesStarCatcher", "retro console (NES) project"),
    "dos": ("samples/Tests/Retro/DesignTUI_Contacts", "DOS QBasic text-mode project"),
    "game": ("samples/Tests/Games/Pygame_Platformer", "pygame scene-designer game"),
    "asm": ("samples/Tests/Assembly/CoreNasmForms", "NASM assembly form project"),
    "firmware": ("@firmware-ecu", "firmware ECU project (created by the firmware-ecu plugin)"),
}
MODES = ("vs", "vscode", "agent")

COPY_IGNORE = shutil.ignore_patterns("__pycache__", ".radide*", "node_modules", ".venv", "build", "bin", "obj",
                                     ".dart_tool", "shots", "*.pyc")

RECORDED: list[tuple[str, str]] = []          # (kind, target) of programs / URLs the IDE wanted to open


def env() -> None:
    for k, v in ENV.items():
        os.environ.setdefault(k, v)
    os.environ["RADIDE_NO_BROWSER"] = "1"
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------------------------------------- no external programs
_BLOCK_EXE = re.compile(r"(^|[\\/\s\"'])(hh|explorer|rundll32|msiexec|mmc|control|ms-settings)(\.exe)?([\s\"']|$)",
                        re.I)


class _FakeProc:
    """Stands in for a refused external program (hh.exe, explorer ...): finished at once with exit code 0."""
    def __init__(self, argv):
        self.args, self.pid, self.returncode = argv, 0, 0
        self.stdin = self.stdout = self.stderr = None

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0

    def communicate(self, input=None, timeout=None):  # noqa: A002
        return ("", "")

    def kill(self):
        pass

    terminate = kill

    def send_signal(self, sig):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _blocked(argv, exe=None) -> str:
    text = " ".join(str(x) for x in (argv if isinstance(argv, (list, tuple)) else [argv]))
    if _BLOCK_EXE.search(str(exe or "")) or _BLOCK_EXE.search(text) or text.lower().rstrip("\"' ").endswith(".chm"):
        return text
    return ""


def no_external_programs() -> None:
    """External programs the IDE would show to the user are recorded in RECORDED instead of started: browsers,
    os.startfile (Explorer, a CHM ...), QDesktopServices.openUrl, QProcess.startDetached, and subprocess.Popen of
    hh.exe / explorer.exe / rundll32 ... (a finished fake process is returned)."""
    import subprocess
    import webbrowser
    webbrowser.open = lambda url, *a, **k: (RECORDED.append(("browser", str(url))), True)[1]
    webbrowser.open_new = webbrowser.open_new_tab = webbrowser.open
    os.startfile = lambda path, *a, **k: RECORDED.append(("startfile", str(path)[:300]))
    real_popen = subprocess.Popen

    class _Popen(real_popen):
        def __new__(cls, args=None, *a, **k):
            t = _blocked(args, k.get("executable"))
            if t:
                RECORDED.append(("popen-refused", t[:300]))
                return _FakeProc(args)
            return super().__new__(cls)

        def __init__(self, args=None, *a, **k):
            super().__init__(args, *a, **k)
    subprocess.Popen = _Popen
    from PyQt6.QtCore import QProcess
    from PyQt6.QtGui import QDesktopServices
    QDesktopServices.openUrl = staticmethod(lambda url: (RECORDED.append(("openUrl", url.toString())), True)[1])

    def _detached(*a, **k):
        RECORDED.append(("startDetached", " ".join(str(x) for x in a)[:300]))
        return (True, 0) if not a or not isinstance(a[0], QProcess) else True
    QProcess.startDetached = _detached


# ------------------------------------------------------------------------------------------- popup menus captured
CAPTURED_MENUS: list = []


def capture_menus() -> None:
    """QMenu.exec / popup never show a menu: the menu is kept in CAPTURED_MENUS (context menus)."""
    from PyQt6.QtWidgets import QMenu
    orig_exec = QMenu.exec

    def _exec(self_or_actions=None, *a, **k):
        if isinstance(self_or_actions, QMenu):
            CAPTURED_MENUS.append(self_or_actions)
            return None
        return None                          # static QMenu.exec(actions, pos): nothing chosen

    def _popup(self, *a, **k):
        CAPTURED_MENUS.append(self)
    QMenu.exec = _exec
    QMenu.popup = _popup
    QMenu._crawler_orig_exec = orig_exec


# ------------------------------------------------------------------------------------------- app + window
APP = None


def boot(app_name: str = "crawl", clear: bool = True):
    """QApplication with the crawler's own QSettings (org RADIDE-TEST-CRAWL), cleared."""
    global APP
    env()
    import PyQt6.QtWebEngineWidgets  # noqa: F401  (before the QApplication)
    from PyQt6.QtCore import QCoreApplication, QSettings
    from PyQt6.QtWidgets import QApplication
    QCoreApplication.setOrganizationName(ORG)
    QCoreApplication.setApplicationName(ORG + "-" + app_name)
    APP = QApplication.instance() or QApplication(sys.argv[:1])
    if clear:
        QSettings().clear()
        QSettings(ORG, ORG + "-" + app_name).clear()
    no_external_programs()
    capture_menus()
    return APP


def clear_test_org() -> None:
    """Remove every QSettings of the crawler's org (registry HKCU, Software, RADIDE-TEST-CRAWL) and its WebEngine profiles."""
    if os.name == "nt":
        import winreg

        def rm(root, path):
            try:
                with winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS) as k:
                    while True:
                        try:
                            sub = winreg.EnumKey(k, 0)
                        except OSError:
                            break
                        rm(root, path + "\\" + sub)
                winreg.DeleteKey(root, path)
            except OSError:
                pass
        rm(winreg.HKEY_CURRENT_USER, "Software\\" + ORG)
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("APPDATA")):
        if base and (Path(base) / ORG).is_dir():
            shutil.rmtree(Path(base) / ORG, ignore_errors=True)


def clear_settings(app_name: str = "crawl") -> None:
    from PyQt6.QtCore import QSettings
    QSettings(ORG, ORG + "-" + app_name).clear()


def pump(sec: float = 0.3) -> None:
    t = time.time()
    while time.time() - t < sec:
        APP.processEvents()
        time.sleep(0.01)


def wait(pred, timeout: float = 10.0) -> bool:
    t = time.time()
    while time.time() - t < timeout:
        APP.processEvents()
        try:
            if pred():
                return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.02)
    return False


def window():
    from radide.app import MainWindow
    w = MainWindow()
    w.resize(1500, 950)
    w.show()
    pump(3)
    return w


def set_mode(w, mode: str) -> bool:
    try:
        from radide.features import workbench
        wb = workbench.get(w)
    except Exception:  # noqa: BLE001
        wb = getattr(w, "workbench", None)
    if wb is None:
        return mode == "vs"
    if wb.mode != mode:
        wb.set_mode(mode)
        pump(1.0)
    return wb.mode == mode


def current_mode(w) -> str:
    wb = getattr(w, "workbench", None)
    return getattr(wb, "mode", "vs") if wb is not None else "vs"


# ------------------------------------------------------------------------------------------- contexts
def make_sandbox(ctx: str, sandbox: Path) -> Path | None:
    src, _ = CONTEXTS[ctx]
    if src is None:
        return None
    dst = sandbox / "projects" / ctx
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    n = 1
    while dst.exists():                     # files still locked by a killed run: use a fresh folder
        n += 1
        dst = sandbox / "projects" / f"{ctx}-{n}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.startswith("@"):
        from radide.languages import get_plugin
        get_plugin(src[1:]).create_new_project(dst, "CrawlEcu", "ecu_demo")
        return dst
    shutil.copytree(ROOT / src, dst, ignore=COPY_IGNORE)
    for junk in dst.glob("test_*.py"):
        junk.unlink()
    return dst


def open_context(w, ctx: str, sandbox: Path) -> Path | None:
    folder = make_sandbox(ctx, sandbox)
    if folder is None:
        return None
    if ctx == "firmware":                        # the one-time safety notice (modal) is accepted in the test settings
        try:
            from radide.firmware.project import notice
            notice.set_accepted(True)
        except Exception as e:  # noqa: BLE001
            print(f"[crawl] firmware notice: {e!r}", file=sys.stderr)
    w.open_project(folder, ask=False)
    pump(2.0)
    p = w.project
    try:                                         # a designer and a code editor open: their menus / context menus
        if p is not None and getattr(p, "forms", None):
            w.open_designer(p.forms[0])
            pump(0.8)
            w.open_code(p.forms[0])
            pump(0.8)
            w.open_designer(p.forms[0])
            pump(0.5)
        elif p is not None and getattr(p, "modules", None):
            w.open_module(p.modules[0])
            pump(0.8)
    except Exception as e:  # noqa: BLE001
        print(f"[crawl] open first document of {ctx}: {e}", file=sys.stderr)
    return folder


# ------------------------------------------------------------------------------------------- harvesting
DISMISSED: list[str] = []


def auto_dismiss(interval: int = 200):
    """A timer that rejects any modal dialog (titles kept in DISMISSED) - the inventory never waits for a user."""
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication, QDialog

    def tick():
        m = QApplication.activeModalWidget()
        if m is None:
            return
        DISMISSED.append(f"{type(m).__name__}: {m.windowTitle()}")
        try:
            m.reject() if isinstance(m, QDialog) else m.close()
        except Exception:  # noqa: BLE001
            pass
    t = QTimer()
    t.setInterval(interval)
    t.timeout.connect(tick)
    t.start()
    return t


def clean(text: str) -> str:
    text = (text or "").split("\t", 1)[0]
    return text.replace("&&", "\0").replace("&", "").replace("\0", "&").replace("...", "").strip()


def _shortcut(a) -> str:
    from PyQt6.QtGui import QKeySequence
    try:
        return ", ".join(s.toString(QKeySequence.SequenceFormat.PortableText) for s in a.shortcuts() if not s.isEmpty())
    except Exception:  # noqa: BLE001
        return ""


def walk_menu(menu, path: list[str], out: list, source: str, seen: set, depth: int = 0) -> None:
    if depth > 7 or id(menu) in seen:
        return
    seen.add(id(menu))
    try:
        menu.aboutToShow.emit()
    except Exception as e:  # noqa: BLE001
        out.append({"source": source, "path": path, "text": "<aboutToShow failed>", "error": repr(e)[:300],
                    "kind": "error"})
    for a in list(menu.actions()):
        if a.isSeparator():
            continue
        t = clean(a.text())
        sub = a.menu()
        if sub is not None:
            walk_menu(sub, path + [t], out, source, seen, depth + 1)
            continue
        if not t and not a.icon():
            continue
        out.append({"source": source, "path": path, "text": t or a.toolTip() or a.objectName(),
                    "shortcut": _shortcut(a), "enabled": a.isEnabled(), "visible": a.isVisible(),
                    "checkable": a.isCheckable(), "kind": "action", "_action": a})


def menubar_entries(w) -> list[dict]:
    out: list[dict] = []
    seen: set = set()
    for a in w.menuBar().actions():
        m = a.menu()
        if m is None:
            if clean(a.text()):
                out.append({"source": "menubar", "path": [], "text": clean(a.text()), "shortcut": _shortcut(a),
                            "enabled": a.isEnabled(), "visible": a.isVisible(), "kind": "action", "_action": a})
            continue
        if not a.isVisible():
            continue
        walk_menu(m, [clean(a.text())], out, "menubar", seen)
    corner = None
    try:
        from PyQt6.QtCore import Qt
        corner = w.menuBar().cornerWidget(Qt.Corner.TopRightCorner)
    except Exception:  # noqa: BLE001
        pass
    if corner is not None:
        out.extend(_buttons(corner, "menubar-corner", ["Menu bar corner"]))
    return out


def _buttons(widget, source: str, path: list[str]) -> list[dict]:
    from PyQt6.QtWidgets import QAbstractButton
    out = []
    for b in widget.findChildren(QAbstractButton):
        t = clean(b.text()) or clean(b.toolTip()) or b.accessibleName() or b.objectName()
        if t and b.isVisibleTo(widget):
            out.append({"source": source, "path": path, "text": t, "shortcut": "", "enabled": b.isEnabled(),
                        "kind": "button", "_button": b})
    return out


def toolbar_entries(w) -> list[dict]:
    from PyQt6.QtWidgets import QToolBar, QToolButton
    out = []
    seen: set = set()
    for tb in w.findChildren(QToolBar):
        title = clean(tb.windowTitle()) or tb.objectName() or "Toolbar"
        shown = tb.isVisible()
        for a in tb.actions():
            if a.isSeparator():
                continue
            wid = tb.widgetForAction(a)
            t = clean(a.text()) or clean(a.toolTip()) or a.objectName()
            if a.menu() is not None:
                walk_menu(a.menu(), ["Toolbar " + title, t], out, "toolbar", seen)
                continue
            if wid is not None and not isinstance(wid, QToolButton):
                # a widget in the tool bar (combo box, device selector ...)
                out.append({"source": "toolbar", "path": ["Toolbar " + title], "text": t or type(wid).__name__,
                            "shortcut": "", "enabled": wid.isEnabled(), "kind": "widget",
                            "toolbar_visible": shown, "widget": type(wid).__name__})
                continue
            if not t:
                continue
            out.append({"source": "toolbar", "path": ["Toolbar " + title], "text": t, "shortcut": _shortcut(a),
                        "enabled": a.isEnabled(), "visible": a.isVisible(), "kind": "action",
                        "toolbar_visible": shown, "_action": a})
    return out


def palette_entries() -> list[dict]:
    out = []
    try:
        from radide.features import command_palette as cp
    except Exception:  # noqa: BLE001
        return out
    for c in cp.commands():
        try:
            en = bool(c.enabled()) if c.enabled else True
        except Exception:  # noqa: BLE001
            en = False
        out.append({"source": "palette", "path": ["Command Palette"] + ([c.category] if c.category else []),
                    "text": c.title, "id": c.id, "shortcut": c.shortcut or "", "enabled": en, "kind": "command",
                    "_command": c})
    return out


def _tree_items(tree):
    from PyQt6.QtWidgets import QTreeWidgetItemIterator
    it = QTreeWidgetItemIterator(tree)
    while it.value() is not None:
        yield it.value()
        it += 1


def solution_items(w) -> list[tuple[str, object]]:
    """A representative Solution Explorer item of every kind (data role) - the context menu differs per kind."""
    from PyQt6.QtCore import Qt
    picked: dict[str, object] = {}
    tree = w.solution
    for item in _tree_items(tree):
        d = item.data(0, Qt.ItemDataRole.UserRole)
        kind = d[0] if isinstance(d, (tuple, list)) and d else (str(d)[:20] if d else "")
        if not kind:
            kind = "folder" if item.childCount() else "item"
        kind = str(kind)
        if kind not in picked:
            picked[kind] = item
    return list(picked.items())


def capture(trigger) -> list:
    """Run *trigger* and return the menus it would have shown."""
    CAPTURED_MENUS.clear()
    try:
        trigger()
    except Exception as e:  # noqa: BLE001
        print(f"[crawl] context menu trigger: {e!r}", file=sys.stderr)
    pump(0.05)
    menus = list(CAPTURED_MENUS)
    CAPTURED_MENUS.clear()
    return menus


def _menu_entries(menus, path, source, extra=None) -> list[dict]:
    out: list[dict] = []
    seen: set = set()
    for m in menus:
        walk_menu(m, list(path), out, source, seen)
    if extra:
        for e in out:
            e.update(extra)
    return out


def context_targets(w) -> list[tuple[str, list[str], object, dict]]:
    """(source, path, trigger, extra) for every context menu we can open."""
    from PyQt6.QtCore import QPoint, Qt
    from PyQt6.QtWidgets import QAbstractScrollArea, QWidget
    out = []
    tree = w.solution
    for kind, item in solution_items(w):
        def trig(item=item):
            tree.setCurrentItem(item)
            r = tree.visualItemRect(item)
            if r.isEmpty():
                tree.scrollToItem(item)
                r = tree.visualItemRect(item)
            tree.customContextMenuRequested.emit(r.center())
        out.append(("context", ["Solution Explorer", f"({kind})"], trig, {"item_kind": kind,
                                                                            "item_text": item.text(0)}))
    bar = w.tabs.tabBar()
    if bar.count():
        def trig_tab():
            bar.customContextMenuRequested.emit(bar.tabRect(bar.currentIndex()).center())
        out.append(("context", ["Editor tab"], trig_tab, {}))
    dv = w._current_designer() if hasattr(w, "_current_designer") else None
    if dv is not None and hasattr(dv, "show_context_menu"):
        out.append(("context", ["Designer", "(form)"], lambda dv=dv: dv.show_context_menu(None, QPoint(10, 10)), {}))
        try:
            ctrls = [c for c in dv.doc.form.ordered() if not c.ctype.nonvisual]
            if ctrls:
                c0 = ctrls[0]
                out.append(("context", ["Designer", "(control)"],
                            lambda dv=dv, c0=c0: dv.show_context_menu(c0, QPoint(10, 10)), {"control": c0.type}))
        except Exception as e:  # noqa: BLE001
            print(f"[crawl] designer control menu: {e!r}", file=sys.stderr)
    # every other widget with a custom context menu (docks: Output, Toolbox, Properties, Error List, ...)
    seen = {id(tree), id(bar)}
    for wd in w.findChildren(QWidget):
        if id(wd) in seen or not wd.isVisible():
            continue
        if wd.contextMenuPolicy() != Qt.ContextMenuPolicy.CustomContextMenu:
            continue
        seen.add(id(wd))
        name = _widget_name(wd)

        def trig_w(wd=wd):
            target = wd
            if isinstance(wd, QAbstractScrollArea):
                target = wd
            wd.customContextMenuRequested.emit(QPoint(max(1, target.width() // 2), max(1, min(10, target.height() // 2))))
        out.append(("context", [name], trig_w, {"widget": type(wd).__name__}))
    return out


def _widget_name(wd) -> str:
    from PyQt6.QtWidgets import QDockWidget
    p = wd
    while p is not None:
        if isinstance(p, QDockWidget):
            return f"{clean(p.windowTitle()) or p.objectName()} ({type(wd).__name__})"
        p = p.parentWidget()
    return f"{wd.objectName() or type(wd).__name__} ({type(wd).__name__})"


def context_entries(w) -> list[dict]:
    out = []
    for source, path, trig, extra in context_targets(w):
        menus = capture(trig)
        ents = _menu_entries(menus, path, source, extra)
        for e in ents:
            e["_trigger"] = trig
        out.extend(ents)
    return out


def action_attrs(w) -> dict[int, str]:
    """id(QAction) -> "win.a_run" for actions kept as attributes of the window or of its feature objects."""
    from PyQt6.QtGui import QAction
    out: dict[int, str] = {}
    for name, v in list(vars(w).items()):
        if isinstance(v, QAction):
            out.setdefault(id(v), name)
        elif hasattr(v, "__dict__") and not isinstance(v, type) and type(v).__module__.startswith("radide"):
            try:
                for n2, v2 in list(vars(v).items()):
                    if isinstance(v2, QAction):
                        out.setdefault(id(v2), f"{name}.{n2}")
            except TypeError:
                pass
    return out


def harvest(w, context: bool = True) -> list[dict]:
    ents = menubar_entries(w) + toolbar_entries(w) + palette_entries()
    if context:
        ents += context_entries(w)
    attrs = action_attrs(w)
    for e in ents:
        e["key"] = entry_key(e)
        a = e.get("_action")
        if a is not None and id(a) in attrs:
            e["attr"] = attrs[id(a)]
    return ents


def entry_key(e: dict) -> str:
    extra = e.get("id") or ""
    return f"{e['source']}|{' > '.join(e['path'])}|{e['text']}" + (f"|{extra}" if extra else "")


def strip(e: dict) -> dict:
    return {k: v for k, v in e.items() if not k.startswith("_")}


def docks(w) -> list[dict]:
    from PyQt6.QtWidgets import QDockWidget
    out = []
    for d in w.findChildren(QDockWidget):
        out.append({"title": clean(d.windowTitle()), "object": d.objectName(), "visible": d.isVisible(),
                    "floating": d.isFloating(), "widget": type(d.widget()).__name__ if d.widget() else ""})
    return out


def shortcuts(w) -> list[dict]:
    """Every QShortcut of the window (actions' shortcuts are in the action entries)."""
    from PyQt6.QtGui import QKeySequence, QShortcut
    out = []
    for s in w.findChildren(QShortcut):
        k = s.key().toString(QKeySequence.SequenceFormat.PortableText)
        if k:
            par = s.parent()
            out.append({"key": k, "parent": type(par).__name__ if par is not None else "", "enabled": s.isEnabled(),
                        "what": s.whatsThis() or s.objectName()})
    return out


def dialog_controls(dlg) -> dict:
    """Pages / options of a dialog: tabs, list items, combo items, check boxes, radio buttons, buttons."""
    from PyQt6.QtWidgets import (QAbstractButton, QCheckBox, QComboBox, QListWidget, QRadioButton, QTabWidget,
                                 QTreeWidget)
    info: dict = {"title": dlg.windowTitle(), "class": type(dlg).__name__, "tabs": [], "lists": [], "combos": [],
                  "checks": [], "radios": [], "buttons": []}
    for t in dlg.findChildren(QTabWidget):
        info["tabs"].append([clean(t.tabText(i)) for i in range(t.count())])
    for lw in dlg.findChildren(QListWidget):
        items = [lw.item(i).text() for i in range(lw.count())]
        if items:
            info["lists"].append(items[:400])
    for tw in dlg.findChildren(QTreeWidget):
        items = [it.text(0) for it in _tree_items(tw)]
        if items:
            info["lists"].append(items[:400])
    for c in dlg.findChildren(QComboBox):
        items = [c.itemText(i) for i in range(c.count())]
        if items:
            info["combos"].append(items[:200])
    for c in dlg.findChildren(QCheckBox):
        info["checks"].append(clean(c.text()))
    for r in dlg.findChildren(QRadioButton):
        info["radios"].append(clean(r.text()))
    for b in dlg.findChildren(QAbstractButton):
        if not isinstance(b, (QCheckBox, QRadioButton)) and clean(b.text()):
            info["buttons"].append(clean(b.text()))
    return info
