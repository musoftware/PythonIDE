"""IDE-level commands: projects (open / new through the real New Project dialog / info / save), the
Solution Explorer, tabs, run / debug state (Locals, Call Stack), breakpoints."""
from __future__ import annotations

import time
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QTreeWidgetItemIterator

from .registry import AutomationError, command
from . import widgets as W
from .commands_core import pump


def project_info(win) -> dict | None:
    p = win.project
    if p is None:
        return None
    sln = getattr(win, "sln", None)
    return {"name": p.name, "folder": str(p.folder), "language": p.language, "forms": list(p.forms),
            "modules": list(p.modules), "startup": p.startup,
            "solution": str(sln.file) if sln is not None and sln.file else None,
            "projects": [x.name for x in win.projects()] if hasattr(win, "projects") else [p.name]}


@command("project", doc="the active project: name, folder, language, forms, modules, startup, solution")
def _project(ctx):
    return project_info(ctx.win)


@command("open_project", doc="open a solution / project / folder like File > Open Project (ask=False: no "
                             "'save changes?' question)")
def _open_project(ctx, path: str, ask: bool = False):
    ctx.win.open_project(Path(path), ask=ask)
    pump(100)
    return project_info(ctx.win)


@command("open_path", doc="open any file / folder / project like Explorer 'Open with RAD IDE' "
                          "(single_instance.open_target)")
def _open_path(ctx, path: str, line: int | None = None):
    from ..single_instance import open_target
    open_target(ctx.win, Path(path), line)
    pump(100)
    return project_info(ctx.win)


@command("new_project", doc="File > New Project through the real dialog: language (plugin id, e.g. vb-basic, "
                            "python-tk), template (windows/dialog/data/console/library or the plugin's own), "
                            "name, location, solution_mode new|add")
def _new_project(ctx, language: str, name: str, location: str, template: str = "windows",
                 solution_mode: str = "new", same_dir: bool = False, timeout_s: float = 30):
    from ..dialogs import NewProjectDialog
    if not str(location).strip() or not Path(location).is_absolute():
        raise AutomationError(f"location must be an absolute folder, got {location!r}")
    state = {"error": None, "filled": False}

    def fill(tries=[0]):  # noqa: B006 - retry counter
        dlg = next((d for d in W.dialogs() if isinstance(d, NewProjectDialog)), None)
        if dlg is None:
            tries[0] += 1
            if tries[0] < 100:
                QTimer.singleShot(100, fill)
            else:
                state["error"] = "the New Project dialog did not open"
            return
        try:
            it = None
            itr = QTreeWidgetItemIterator(dlg.langs)
            while itr.value():
                if itr.value().data(0, Qt.ItemDataRole.UserRole) == language:
                    it = itr.value()
                    break
                itr += 1
            if it is None:
                raise AutomationError(f"language {language!r} is not in the New Project dialog")
            dlg.langs.setCurrentItem(it)
            pump()
            row = next((i for i in range(dlg.templates.count())
                        if dlg.templates.item(i).data(Qt.ItemDataRole.UserRole) == template), None)
            if row is None:
                have = [dlg.templates.item(i).data(Qt.ItemDataRole.UserRole) for i in range(dlg.templates.count())]
                raise AutomationError(f"template {template!r} not offered for {language}: {have}")
            dlg.templates.setCurrentRow(row)
            dlg.name.setText(name)
            dlg.location.setText(str(location))
            i = dlg.solution_mode.findData(solution_mode)
            if i >= 0:
                dlg.solution_mode.setCurrentIndex(i)
            dlg.same_dir.setChecked(bool(same_dir))
            pump()
            state["filled"] = True
            ok = next(b for b in dlg.findChildren(__import__("PyQt6.QtWidgets", fromlist=["QPushButton"]).QPushButton)
                      if W.clean(b.text()).lower() in ("ok", "موافق"))
            ok.click()
            QTimer.singleShot(500, lambda: _still_open(dlg))
        except Exception as e:  # noqa: BLE001
            state["error"] = f"{type(e).__name__}: {e}"
            dlg.reject()

    def _still_open(dlg):
        try:
            if dlg.isVisible():
                boxes = [W.describe_dialog(d) for d in W.dialogs() if d is not dlg]
                state["error"] = f"the dialog stayed open after OK: {boxes}"
        except RuntimeError:
            pass

    QTimer.singleShot(50, fill)
    ctx.win.new_project()               # the real File > New Project (modal dialog, filled by fill())
    end = time.monotonic() + timeout_s
    while state["error"] is None and not state["filled"] and time.monotonic() < end:
        pump(50)
    if state["error"]:
        raise AutomationError(state["error"])
    pump(200)
    return project_info(ctx.win)


@command("save_all", doc="File > Save All")
def _save_all(ctx):
    return bool(ctx.win.save_all() is not False)


@command("solution_tree", doc="the Solution Explorer items")
def _solution_tree(ctx):
    return W.items_of(ctx.win.solution)


@command("open_item", doc="double-click an item of the Solution Explorer (text or 'Parent/Child' path)")
def _open_item(ctx, text: str):
    from .commands_widgets import _select_item
    return _select_item(ctx, ctx.win.solution, text, dclick=True, async_=False)


@command("tabs", doc="titles of the open document tabs and the current one")
def _tabs(ctx):
    tw = ctx.win.tabs
    return {"tabs": [tw.tabText(i) for i in range(tw.count())], "current": tw.currentIndex(),
            "current_title": tw.tabText(tw.currentIndex()) if tw.count() else "",
            "current_cls": type(tw.currentWidget()).__name__ if tw.currentWidget() else None}


@command("activate_tab", doc="bring a document tab to the front (title substring)")
def _activate_tab(ctx, title: str):
    tw = ctx.win.tabs
    for i in range(tw.count()):
        if title.lower() in tw.tabText(i).lower():
            tw.setCurrentIndex(i)
            pump()
            return {"index": i, "title": tw.tabText(i)}
    raise AutomationError(f"no tab {title!r}: {[tw.tabText(i) for i in range(tw.count())]}")


@command("open_form", doc="open a form in the designer (view='design') or its code (view='code')")
def _open_form(ctx, name: str, view: str = "design"):
    (ctx.win.open_code if view == "code" else ctx.win.open_designer)(name)
    pump()
    return _tabs(ctx)


@command("open_module", doc="open a module / file of the project in the editor")
def _open_module(ctx, filename: str):
    ctx.win.open_module(filename)
    pump()
    return _tabs(ctx)


# ------------------------------------------------------------------------------------ run / debug
def session_state(win) -> dict:
    s = getattr(win, "session", None)
    d = {"session": s is not None, "running": False, "paused": False}
    if s is not None:
        try:
            d["running"] = bool(s.running())
        except Exception:  # noqa: BLE001
            pass
        d["paused"] = bool(getattr(s, "paused", False))
        d["kind"] = type(s).__name__
        for attr in ("pid", "process_id"):
            v = getattr(s, attr, None)
            if isinstance(v, int):
                d["pid"] = v
        proc = getattr(s, "proc", None) or getattr(s, "process", None)
        try:
            if proc is not None and hasattr(proc, "processId"):
                d["pid"] = int(proc.processId())
        except Exception:  # noqa: BLE001
            pass
    try:
        d["status"] = win.statusBar().currentMessage()
    except Exception:  # noqa: BLE001
        pass
    return d


@command("run_state", doc="is a program running / paused at a breakpoint; its pid when known")
def _run_state(ctx):
    return session_state(ctx.win)


@command("debug_state", doc="Locals and Call Stack contents, the current line")
def _debug_state(ctx):
    w = ctx.win
    d = session_state(w)
    d["locals"] = W.items_of(w.locals)
    d["callstack"] = W.items_of(w.callstack)
    return d


@command("child_pids", doc="process ids of the IDE's child processes (recursive, Windows)")
def _child_pids(ctx):
    from .commands_win32 import descendants
    import os
    return descendants(os.getpid())


@command("breakpoint", doc="set / clear a breakpoint: file (code file of the project), line (1-based)")
def _breakpoint(ctx, file: str, line: int, on: bool = True):
    win = ctx.win
    form = win._form_for_file(file) if hasattr(win, "_form_for_file") else None
    ed = None
    if form:
        win.open_code(form)
        ed = win.codeviews[form].editor
    else:
        win.open_module(file)
        ed = win._editor_for_file(file)
    if ed is None:
        raise AutomationError(f"no editor for {file}")
    pump(100)

    def mine():                    # 1-based lines of this file, as the debugger gets them
        return sorted(int(x[1]) for x in win._all_breakpoints() if Path(str(x[0])).name.lower() == Path(file).name.lower())
    if (int(line) in mine()) != bool(on):
        ed.toggle_breakpoint(int(line) - 1)        # editors count lines from 0
    pump(100)
    return {"breakpoints": mine(), "all": [list(x) for x in win._all_breakpoints()]}


@command("app_info", doc="top-level windows of the IDE process (title, class, visible)")
def _app_info(ctx):
    return [{"title": w.windowTitle(), "cls": type(w).__name__, "visible": w.isVisible()}
            for w in QApplication.topLevelWidgets() if w.isVisible()]
