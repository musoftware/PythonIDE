"""VS Code workbench commands that extensions execute, run by RAD IDE's own UI.

The extension host (radide/vsx/host/main.js + commands.js) implements the commands that need extension-host
state; everything else arrives as ``commands/executeIde`` and is routed by host_ide -> workbench_ui.exec_command
-> ``run(wb, command, args)`` here. Semantics (argument shapes, what is opened / focused / toggled) follow
microsoft/vscode at the commit in radide/vsx/reference/README.md; where RAD IDE has no such part (a second
editor group, an auxiliary window ...) the command does what VS Code does when the part is unavailable.

``COMMANDS`` (id -> handler(wb, args)) and ``NOOP`` are read by radide/vsx/reference/coverage.py.
A handler returns True / a value (handled), or ``Deferred(fn)`` whose fn(reply) answers later.
No Qt import at module level."""
from __future__ import annotations

import os
from pathlib import Path


class Deferred:
    """A command that answers asynchronously: fn(reply) must call reply(result) exactly once."""

    def __init__(self, fn):
        self.fn = fn


# ============================================================================ helpers
def _win(wb):
    return wb.win


def _workbench(win):
    return getattr(win, "workbench", None)


def _code_mode(win) -> bool:
    wb = _workbench(win)
    return wb is not None and getattr(wb, "mode", "vs") != "vs"


def show_dock(win, dock_attr: str, view_id: str | None = None, focus: bool = True) -> bool:
    """Show (and focus) one of the IDE's docks; in the VS Code / Agent layouts through the Activity Bar."""
    wb = _workbench(win)
    if view_id and _code_mode(win):
        try:
            wb.show_view(view_id)
        except Exception:  # noqa: BLE001
            pass
    d = getattr(win, dock_attr, None)
    if d is None:
        return False
    d.show()
    d.raise_()
    if focus and d.widget() is not None:
        d.widget().setFocus()
    return True


def _menu(win, *paths) -> bool:
    from . import contrib_keybindings as KB
    return any(KB._trigger_menu(win, p) for p in paths)


def _action(win, *names) -> bool:
    for n in names:
        a = getattr(win, n, None)
        if a is not None and a.isEnabled():
            a.trigger()
            return True
    return False


def _arg(args, i=0, default=None):
    return args[i] if isinstance(args, list) and len(args) > i else default


def _uri_path(u) -> str:
    if isinstance(u, dict):
        return str(u.get("path") or u.get("fsPath") or u.get("$uri") or "")
    return str(u or "")


# ============================================================================ settings
def open_settings(wb, query: str = "") -> bool:
    """workbench.action.openSettings(query): Tools > Options on the "VS Code Extensions" page with the extension
    the query names selected (``@ext:publisher.name``, a setting id such as ``claudeCode.useTerminal``, or text)."""
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QTabWidget

    win = _win(wb)
    q = (query or "").strip()

    def go():
        try:
            from ..features.settings import OptionsDialog
        except Exception:  # noqa: BLE001
            return
        dlg = OptionsDialog(win)
        win._options_dialog = dlg
        tabs = dlg.findChild(QTabWidget)
        if tabs is not None:
            for i in range(tabs.count()):
                if tabs.tabText(i) == "VS Code Extensions":
                    tabs.setCurrentIndex(i)
                    page = tabs.widget(i)
                    lst = getattr(page, "_vsx_list", None)
                    if lst is not None and q:
                        _select_extension(lst, q)
                    break
        dlg.exec()
    QTimer.singleShot(0, go)           # VS Code resolves once the editor opens: answer first, then show the dialog
    return True


def _select_extension(lst, q: str) -> None:
    from .contrib_common import enabled_extensions
    from .contrib_configuration import sections
    want = q[5:].strip().lower() if q.lower().startswith("@ext:") else ""
    exts = [e for e in enabled_extensions() if sections(e)]
    for row, e in enumerate(exts):
        keys = set()
        for sec in sections(e):
            props = sec.get("properties") if isinstance(sec, dict) else None
            keys.update((props or {}).keys())
        if (want and e.id.lower() == want) or (not want and (q in keys or any(k.startswith(q) for k in keys)
                                                              or q.lower() in e.label.lower())):
            lst.setCurrentRow(row)
            return


def _settings_json(wb, args):
    from . import contrib_configuration
    path = contrib_configuration.settings_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", "utf-8")
    wb.svc.open_path(str(path))
    return True


# ============================================================================ extensions
def _extensions_view(win, query: str | None = None) -> bool:
    try:
        from ..features import vsx_market
        vsx_market.show_view(win)
        view = getattr(win, "vsx_view", None)
        if view is not None and query is not None:
            view.search.setText(query)
            view.do_search()
        return True
    except Exception:  # noqa: BLE001
        return False


def _install_extension(wb, args):
    """workbench.extensions.installExtension(id | Uri of a .vsix, options) - resolves when installed."""
    target = _arg(args)
    if target is None:
        return None
    vsix = _uri_path(target) if isinstance(target, dict) else ""

    def work(reply):
        import threading

        from PyQt6.QtCore import QTimer

        def run():
            err = None
            try:
                from . import manager
                if vsix:
                    manager.install_vsix_file(vsix)
                else:
                    manager.install(str(target))
            except Exception as e:  # noqa: BLE001
                err = str(e)

            def done():
                if err:
                    wb.svc.status(f"Install {target}: {err}", 8000)
                    reply({"$error": err})
                else:
                    wb.svc.status(f"Installed {target}", 5000)
                    reply(True)
            QTimer.singleShot(0, done)
        threading.Thread(target=run, daemon=True).start()
    wb.svc.status(f"Installing {target} ...", 5000)
    return Deferred(work)


def _uninstall_extension(wb, args):
    ext_id = _arg(args)
    if not ext_id:
        return None
    from . import manager
    manager.uninstall(str(ext_id))
    return True


def _show_extension(wb, args):
    eid = _arg(args)
    if isinstance(eid, list):
        eid = eid[0] if eid else None
    if not eid:
        return _extensions_view(_win(wb))
    try:
        from ..features import vsx_market
        vsx_market.show_view(_win(wb))
        vsx_market.open_details(_win(wb), str(eid))
        return True
    except Exception:  # noqa: BLE001
        return _extensions_view(_win(wb), str(eid))


# ============================================================================ layout parts
def _toggle_sidebar(wb, show=None):
    w = _workbench(_win(wb))
    if w is not None and _code_mode(_win(wb)):
        w.toggle_sidebar(show)
    else:
        d = getattr(_win(wb), "dock_solution", None)
        if d is not None:
            d.setVisible(not d.isVisible() if show is None else show)
    return True


def _toggle_panel(wb, show=None):
    win = _win(wb)
    w = _workbench(win)
    if w is not None and _code_mode(win):
        w.toggle_panel(show)
        return True
    d = getattr(win, "dock_output", None)
    if d is not None:
        d.setVisible(not d.isVisible() if show is None else show)
    return True


def _aux_docks(wb):
    """the secondary side bar: right-area docks of extension views (and Toolbox / Properties in Code mode)"""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QDockWidget
    win = _win(wb)
    out = []
    for d in win.findChildren(QDockWidget):
        if d.parent() is win and win.dockWidgetArea(d) == Qt.DockWidgetArea.RightDockWidgetArea and \
                (d.objectName().startswith(("vsxWebview_", "vsxView_", "vsxContainer_"))):
            out.append(d)
    return out


def _toggle_aux(wb, show=None):
    docks = _aux_docks(wb)
    if not docks:
        return True
    vis = any(d.isVisible() for d in docks)
    want = (not vis) if show is None else show
    for d in docks:
        if want:
            if d.property("vsxWasVisible") in (None, True):
                d.show()
        else:
            d.setProperty("vsxWasVisible", d.isVisible())
            d.hide()
    return True


def _focus_aux(wb):
    docks = [d for d in _aux_docks(wb) if d.isVisible()] or _aux_docks(wb)
    if docks:
        docks[0].show()
        docks[0].raise_()
        if docks[0].widget() is not None:
            docks[0].widget().setFocus()
    return True


def _full_screen(wb):
    win = _win(wb)
    win.showNormal() if win.isFullScreen() else win.showFullScreen()
    return True


def _zen(wb):
    w = _workbench(_win(wb))
    if w is not None:
        w.toggle_zen()
    return True


# ============================================================================ windows / editors
def _move_to_new_window(wb, args):
    """workbench.action.moveEditorToNewWindow: the active editor in its own window - a webview panel's dock
    floats as a separate window (RAD IDE text editors stay in the one editor group)."""
    p = wb.svc.webviews.active_panel() if hasattr(wb.svc.webviews, "active_panel") else None
    if p is not None:
        d = p.dock
        d.setFloating(True)
        d.resize(max(d.width(), 900), max(d.height(), 700))
        d.show()
        d.raise_()
        d.activateWindow()
    return True


def _reload_webviews(wb, args):
    for w in list(wb.svc.webviews.items.values()):
        try:
            w.set_html(w.html)
        except Exception:  # noqa: BLE001
            pass
    return True


def _restart_host(wb, args):
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(100, wb.svc.restart)
    return True


def _reveal_in_explorer(wb, args):
    win = _win(wb)
    p = _uri_path(_arg(args))
    show_dock(win, "dock_solution", "explorer")
    if p:
        for name in ("reveal_in_solution", "select_in_solution", "locate_in_solution"):
            fn = getattr(win, name, None)
            if callable(fn):
                try:
                    fn(Path(p))
                    break
                except Exception:  # noqa: BLE001
                    pass
        wb.svc.status(str(p), 5000)
    return True


def _new_window(wb, args):
    win = _win(wb)
    if os.environ.get("RADIDE_NO_BROWSER"):      # tests: never start other programs
        return True
    fn = getattr(win, "new_window", None)
    if callable(fn):
        fn()
    return True


def _refresh_explorer(wb, args):
    win = _win(wb)
    for name in ("refresh_solution", "reload_solution_tree", "refresh_solution_explorer"):
        fn = getattr(win, name, None)
        if callable(fn):
            fn()
            return True
    sol = getattr(win, "solution", None)
    if sol is not None and callable(getattr(sol, "refresh", None)):
        sol.refresh()
    return True


def _quick_open(wb, args):
    from ..features import command_palette as cp
    prefix = _arg(args)          # workbench.action.quickOpen(prefix?): the quick input with that text
    cp.quick_open(_win(wb), str(prefix) if isinstance(prefix, str) else "")
    return True


def _terminal_tab(wb, step: int):
    panel = getattr(wb, "terminals", None)
    tabs = getattr(panel, "tabs", None)
    if tabs is not None and tabs.count():
        tabs.setCurrentIndex((tabs.currentIndex() + step) % tabs.count())
        d = panel.ensure_dock()
        d.show()
        d.raise_()
    return True


def _debug(*actions, menu=()):
    return lambda wb, args: True if (_action(_win(wb), *actions) or _menu(_win(wb), *menu)) else True


# ============================================================================ navigation / editors
def _nav(wb):
    nav = getattr(_win(wb), "vsx_nav", None)
    if nav is None:
        from . import navigation
        nav = navigation.install(_win(wb))
    return nav


def _palette(prefix: str):
    def run(wb, args):
        from ..features import command_palette as cp
        cp.quick_open(_win(wb), prefix)
        return True
    return run


def _keybindings_json(wb, args):
    from . import user_keybindings
    wb.svc.open_path(str(user_keybindings.ensure_file()))
    return True


def _keyboard_shortcuts(wb, args):
    """workbench.action.openGlobalKeybindings(query?): the Keyboard Shortcuts page (radide/vsx/settings_ui.py)."""
    from PyQt6.QtCore import QTimer
    q = _settings_query(args)

    def go():
        from . import settings_ui
        settings_ui.show_keyboard_shortcuts(_win(wb), q)
    QTimer.singleShot(0, go)
    return True


def _settings_ui(wb, args):
    from PyQt6.QtCore import QTimer
    q = _settings_query(args)

    def go():
        from . import settings_ui
        settings_ui.show_settings(_win(wb), q)
    QTimer.singleShot(0, go)
    return True


def _revert(wb, args):
    """workbench.action.files.revert: the active editor's file as it is on disk (unsaved changes dropped)."""
    win = _win(wb)
    ed = wb.svc.active_editor() if hasattr(wb.svc, "active_editor") else None
    if ed is None or not getattr(ed, "path", None):
        return True
    try:
        text = Path(ed.path).read_text("utf-8").replace("\r\n", "\n")
    except (OSError, UnicodeError):
        return True
    ed.setText(text)
    ed.setModified(False)
    win.statusBar().showMessage(f"Reverted {Path(ed.path).name}", 3000)
    return True


def _close_editor(wb, args):
    win = _win(wb)
    tabs = getattr(win, "tabs", None)
    if tabs is None or tabs.currentIndex() < 0:
        return True
    if _menu(win, "File/Close"):
        return True
    i = tabs.currentIndex()
    req = getattr(win, "_close_tab", None) or getattr(win, "close_tab", None)
    if callable(req):
        req(i)
    else:
        tabs.tabCloseRequested.emit(i)
    return True


def _new_file(wb, args):
    """workbench.action.files.newUntitledFile / welcome.showNewFileEntries: File > New File (IDE) or an
    untitled document through the host."""
    win = _win(wb)
    if _menu(win, "File/New File", "File/New/File..."):
        return True
    if wb.svc.host.running():
        wb.svc.execute("workbench.action.files.newUntitledFile", args)
    return True


def _problem(step: int):
    """editor.action.marker.nextInFiles / prevInFiles (F8 / Shift+F8) and workbench problem navigation: the next
    entry of the Error List, opened at its line."""
    def run(wb, args):
        win = _win(wb)
        lst = getattr(win, "error_list", None)
        if lst is None or lst.topLevelItemCount() == 0:
            ed = wb.svc.active_editor() if hasattr(wb.svc, "active_editor") else None
            if ed is not None:
                from . import editor_commands as EC
                EC.run(ed, "editor.action.marker.next" if step > 0 else "editor.action.marker.prev", [])
            return True
        n = lst.topLevelItemCount()
        cur = lst.indexOfTopLevelItem(lst.currentItem()) if lst.currentItem() is not None else -1
        i = (cur + step) % n
        it = lst.topLevelItem(i)
        lst.setCurrentItem(it)
        try:
            from ..tools import _goto
            _goto(win, it.text(2), int(it.text(3) or 1))
        except Exception:  # noqa: BLE001
            pass
        return True
    return run


def _git(op: str):
    """git.* commands of VS Code's built-in Git extension that other extensions run, on RAD IDE's Git."""
    def run(wb, args):
        win = _win(wb)
        panel = getattr(win, "git_panel", None)
        full = getattr(win, "git_full", None)
        target = _uri_path(_arg(args))
        if isinstance(_arg(args), dict) and "resourceUri" in _arg(args):
            target = _uri_path(_arg(args)["resourceUri"])
        if op == "refresh":
            if panel is not None:
                panel.refresh()
            return True
        if op in ("fetch", "sync", "push") and full is not None:
            getattr(full, op)()
            return True
        if op == "pull" and full is not None and hasattr(full, "pull"):
            full.pull()
            return True
        if op == "openChange":
            p = Path(target) if target else (Path(wb.svc.active_editor().path) if wb.svc.active_editor() else None)
            if p is not None and full is not None and hasattr(full, "compare_path"):
                full.compare_path(p)
            return True
        if op in ("stage", "unstage") and panel is not None:
            git = getattr(panel, "git", None)
            paths = [target] if target else ([str(wb.svc.active_editor().path)] if wb.svc.active_editor() else [])
            if git is not None and paths:
                getattr(git, op)(paths)
                panel.refresh()
            return True
        if op == "stageAll" and panel is not None:
            panel.stage_all()
            return True
        if op in ("commit", "openRepository", "showOutput", "init", "clone", "checkout", "branch"):
            show_dock(win, "dock_git", "scm") or _action(win, "a_git")
            return True
        return True
    return run


# ============================================================================ the table
COMMANDS = {
    # views / parts
    "workbench.view.explorer": lambda wb, a: show_dock(_win(wb), "dock_solution", "explorer"),
    "workbench.files.action.focusFilesExplorer": lambda wb, a: show_dock(_win(wb), "dock_solution", "explorer"),
    "workbench.explorer.fileView.focus": lambda wb, a: show_dock(_win(wb), "dock_solution", "explorer"),
    "workbench.files.action.refreshFilesExplorer": _refresh_explorer,
    "workbench.view.search": lambda wb, a: show_dock(_win(wb), "dock_find", "search") or _menu(_win(wb), "Edit/Find in Files..."),
    "workbench.view.search.focus": lambda wb, a: show_dock(_win(wb), "dock_find", "search"),
    "workbench.view.scm": lambda wb, a: show_dock(_win(wb), "dock_git", "scm") or _action(_win(wb), "a_git"),
    "workbench.scm.focus": lambda wb, a: show_dock(_win(wb), "dock_git", "scm"),
    "workbench.view.debug": lambda wb, a: show_dock(_win(wb), "dock_locals", "run"),
    "workbench.view.extensions": lambda wb, a: _extensions_view(_win(wb)),
    "workbench.view.testing.focus": lambda wb, a: show_dock(_win(wb), "dock_tests"),
    "workbench.actions.view.problems": lambda wb, a: show_dock(_win(wb), "dock_errors"),
    "workbench.action.problems.focus": lambda wb, a: show_dock(_win(wb), "dock_errors"),
    "workbench.panel.markers.view.focus": lambda wb, a: show_dock(_win(wb), "dock_errors"),
    "workbench.debug.action.focusRepl": lambda wb, a: show_dock(_win(wb), "dock_immediate"),
    "workbench.panel.repl.view.focus": lambda wb, a: show_dock(_win(wb), "dock_immediate"),
    "workbench.debug.action.toggleRepl": lambda wb, a: show_dock(_win(wb), "dock_immediate"),
    "workbench.action.togglePanel": lambda wb, a: _toggle_panel(wb),
    "workbench.action.closePanel": lambda wb, a: _toggle_panel(wb, False),
    "workbench.action.focusPanel": lambda wb, a: _toggle_panel(wb, True),
    "workbench.action.toggleMaximizedPanel": lambda wb, a: _toggle_panel(wb, True),
    "workbench.action.toggleSidebarVisibility": lambda wb, a: _toggle_sidebar(wb),
    "workbench.action.closeSidebar": lambda wb, a: _toggle_sidebar(wb, False),
    "workbench.action.focusSideBar": lambda wb, a: _toggle_sidebar(wb, True),
    "workbench.action.toggleAuxiliaryBar": lambda wb, a: _toggle_aux(wb),
    "workbench.action.closeAuxiliaryBar": lambda wb, a: _toggle_aux(wb, False),
    "workbench.action.focusAuxiliaryBar": lambda wb, a: _focus_aux(wb),
    "workbench.action.toggleZenMode": lambda wb, a: _zen(wb),
    "workbench.action.toggleFullScreen": lambda wb, a: _full_screen(wb),
    "workbench.action.showErrorsWarnings": lambda wb, a: show_dock(_win(wb), "dock_errors"),
    "workbench.action.terminal.focusNext": lambda wb, a: _terminal_tab(wb, +1),
    "workbench.action.terminal.focusPrevious": lambda wb, a: _terminal_tab(wb, -1),
    "workbench.action.replaceInFiles": lambda wb, a: _menu(_win(wb), "Edit/Replace in Files...", "Edit/Find in Files...") or True,
    "workbench.action.findInFiles": lambda wb, a: _menu(_win(wb), "Edit/Find in Files...") or True,
    "workbench.action.selectTheme": lambda wb, a: open_settings(wb, ""),
    "workbench.action.openWorkspaceConfigFile": _settings_json,
    # settings
    "workbench.action.openSettings": lambda wb, a: open_settings(wb, _settings_query(a)),
    "workbench.action.openSettings2": lambda wb, a: open_settings(wb, _settings_query(a)),
    "workbench.action.openGlobalSettings": lambda wb, a: open_settings(wb, _settings_query(a)),
    "workbench.action.openWorkspaceSettings": lambda wb, a: open_settings(wb, _settings_query(a)),
    "workbench.action.openUserSettings": lambda wb, a: open_settings(wb, _settings_query(a)),
    "workbench.action.openApplicationSettings": lambda wb, a: open_settings(wb, _settings_query(a)),
    "workbench.action.openFolderSettings": lambda wb, a: open_settings(wb, _settings_query(a)),
    "workbench.action.openSettingsJson": _settings_json,
    "workbench.action.openApplicationSettingsJson": _settings_json,
    "workbench.action.openWorkspaceSettingsFile": _settings_json,
    "workbench.action.openGlobalKeybindings": lambda wb, a: open_settings(wb, ""),
    # extensions
    "workbench.extensions.installExtension": _install_extension,
    "workbench.extensions.uninstallExtension": _uninstall_extension,
    "workbench.extensions.search": lambda wb, a: _extensions_view(_win(wb), str(_arg(a, 0, "") or "")),
    "workbench.extensions.action.showExtensionsWithIds": _show_extension,
    "workbench.extensions.action.showInstalledExtensions": lambda wb, a: _extensions_view(_win(wb)),
    "workbench.extensions.action.checkForUpdates": lambda wb, a: _extensions_view(_win(wb)),
    "extension.open": _show_extension,
    # window / host
    "workbench.action.restartExtensionHost": _restart_host,
    "workbench.action.webview.reloadWebviewAction": _reload_webviews,
    "workbench.action.moveEditorToNewWindow": _move_to_new_window,
    "workbench.action.copyEditorToNewWindow": _move_to_new_window,
    "vscode.newWindow": _new_window,
    "workbench.action.newWindow": _new_window,
    "revealInExplorer": _reveal_in_explorer,
    "workbench.action.quickOpen": _quick_open,
    "workbench.action.files.openFolder": lambda wb, a: _action(_win(wb), "a_open_folder") or True,
    "workbench.action.files.openFileFolder": lambda wb, a: _action(_win(wb), "a_open_folder") or True,
    "workbench.action.files.openFile": lambda wb, a: _action(_win(wb), "a_open_file") or True,
    "workbench.action.files.saveAs": lambda wb, a: _menu(_win(wb), "File/Save As...", "File/Save As") or True,
    "workbench.action.files.saveFiles": lambda wb, a: (getattr(_win(wb), "save_all", lambda: None)(), True)[1],
    "update.checkForUpdate": lambda wb, a: _menu(_win(wb), "Help/Check for Updates...", "Help/Check for Updates") or True,
    # debugging
    "workbench.action.debug.continue": _debug("a_run", menu=("Debug/Continue",)),
    "workbench.action.debug.stepOver": _debug("a_step_over"),
    "workbench.action.debug.stepInto": _debug("a_step_into"),
    "workbench.action.debug.stepOut": _debug("a_step_out"),
    "workbench.action.debug.restart": _debug(menu=("Debug/Restart",)),
    "workbench.action.debug.pause": _debug(menu=("Debug/Break All",)),
    "workbench.action.debug.stepIntoTarget": _debug("a_step_into"),
    "workbench.action.debug.selectandstart": _palette("debug "),
    "workbench.action.debug.configure": lambda wb, a: _launch_json(wb),
    # quick access (the Command Palette's prefixes)
    "workbench.action.showCommands": _palette(">"),
    "workbench.action.gotoLine": _palette(":"),
    "workbench.action.gotoSymbol": _palette("@"),
    "workbench.action.showAllSymbols": _palette("#"),
    "workbench.action.quickOpenView": _palette("view "),
    "workbench.action.showAllEditors": _palette("edt "),
    "workbench.action.showAllEditorsByMostRecentlyUsed": _palette("edt mru "),
    "workbench.action.showEditorsInActiveGroup": _palette("edt active "),
    "workbench.action.quickOpenTerm": _palette("term "),
    "workbench.action.tasks.showTasks": _palette("task "),
    "workbench.action.openRecent": _palette("recent "),
    "workbench.action.quickOpenPreviousRecentlyUsedEditor": _palette("edt mru "),
    "workbench.extensions.action.installExtensions": lambda wb, a: _extensions_view(_win(wb), ""),
    "workbench.extensions.action.listEnabledExtensions": lambda wb, a: _extensions_view(_win(wb)),
    # navigation history / closed editors
    "workbench.action.navigateBack": lambda wb, a: _nav(wb).navigate_back() or True,
    "workbench.action.navigateForward": lambda wb, a: _nav(wb).navigate_forward() or True,
    "workbench.action.navigateLast": lambda wb, a: _nav(wb).navigate_last() or True,
    "workbench.action.navigateToLastEditLocation": lambda wb, a: _nav(wb).last_edit() or True,
    "workbench.action.navigateBackInEditLocations": lambda wb, a: _nav(wb).last_edit() or True,
    "workbench.action.reopenClosedEditor": lambda wb, a: _nav(wb).reopen_closed() or True,
    # files / editors
    "workbench.action.files.revert": _revert,
    "workbench.action.files.save": lambda wb, a: _menu(_win(wb), "File/Save") or True,
    "workbench.action.files.saveAll": lambda wb, a: (getattr(_win(wb), "save_all", lambda: None)(), True)[1],
    "workbench.action.closeActiveEditor": _close_editor,
    "workbench.action.files.newUntitledFile": _new_file,
    "welcome.showNewFileEntries": _new_file,
    "workbench.action.files.newFile": _new_file,
    # problems
    "editor.action.marker.nextInFiles": _problem(+1),
    "editor.action.marker.prevInFiles": _problem(-1),
    "workbench.action.problems.next": _problem(+1),
    "workbench.action.problems.previous": _problem(-1),
    # preferences
    "workbench.action.openGlobalKeybindingsFile": _keybindings_json,
    "workbench.action.openDefaultKeybindingsFile": _keybindings_json,
    "workbench.action.openKeyboardLayoutPicker": lambda wb, a: True,
    "workbench.action.openRawDefaultSettings": _settings_json,
    "workbench.action.openSettingsUI": _settings_ui,
    # git (VS Code's built-in Git extension)
    "git.refresh": _git("refresh"), "git.fetch": _git("fetch"), "git.sync": _git("sync"), "git.push": _git("push"),
    "git.pull": _git("pull"), "git.openChange": _git("openChange"), "git.stage": _git("stage"),
    "git.unstage": _git("unstage"), "git.stageAll": _git("stageAll"), "git.commit": _git("commit"),
    "git.openRepository": _git("openRepository"), "git.showOutput": _git("showOutput"), "git.init": _git("init"),
    "git.clone": _git("clone"), "git.checkout": _git("checkout"), "git.branch": _git("branch"),
}
COMMANDS["workbench.action.openGlobalKeybindings"] = _keyboard_shortcuts


def _list_cmd(op: str):
    """list.* (VS Code's list / tree navigation): on the focused Qt list or tree of the IDE."""
    def run(wb, args):
        from PyQt6.QtWidgets import QAbstractItemView, QApplication, QTreeView
        w = QApplication.focusWidget()
        while w is not None and not isinstance(w, QAbstractItemView):
            w = w.parentWidget()
        if w is None or w.model() is None:
            return True
        m = w.model()
        cur = w.currentIndex()
        if op in ("focusDown", "focusUp", "focusFirst", "focusLast", "focusPageDown", "focusPageUp"):
            action = {"focusDown": QAbstractItemView.CursorAction.MoveDown, "focusUp": QAbstractItemView.CursorAction.MoveUp,
                      "focusFirst": QAbstractItemView.CursorAction.MoveHome,
                      "focusLast": QAbstractItemView.CursorAction.MoveEnd,
                      "focusPageDown": QAbstractItemView.CursorAction.MovePageDown,
                      "focusPageUp": QAbstractItemView.CursorAction.MovePageUp}[op]
            idx = w.moveCursor(action, w.keyboardModifiers() if hasattr(w, "keyboardModifiers") else
                               QApplication.keyboardModifiers())
            if idx.isValid():
                w.setCurrentIndex(idx)
            elif m.rowCount() and not cur.isValid():
                w.setCurrentIndex(m.index(0, 0))
            return True
        if not cur.isValid():
            return True
        if op == "select":
            w.activated.emit(cur)
            w.doubleClicked.emit(cur)
        elif isinstance(w, QTreeView) and op == "collapse":
            if w.isExpanded(cur):
                w.collapse(cur)
            elif cur.parent().isValid():
                w.setCurrentIndex(cur.parent())
        elif isinstance(w, QTreeView) and op == "expand":
            w.expand(cur)
        elif isinstance(w, QTreeView) and op == "toggleExpand":
            w.setExpanded(cur, not w.isExpanded(cur))
        return True
    return run


def _run_selected_text(wb, args):
    """workbench.action.terminal.runSelectedText: the editor's selection (or line) to the active terminal."""
    ed = wb.svc.active_editor() if hasattr(wb.svc, "active_editor") else None
    if ed is None:
        return True
    text = ed.selectedText() if hasattr(ed, "selectedText") else ""
    if not text:
        line = getattr(ed, "_cursor", (0, 0))[0]
        lines = ed.text().split("\n")
        text = lines[line] if 0 <= line < len(lines) else ""
    if text and wb.svc.host.running():
        wb.svc.execute("workbench.action.terminal.sendSequence", [{"text": text.rstrip("\n") + "\r"}])
    return True


def _toggle_breakpoint(wb, args):
    ed = wb.svc.active_editor() if hasattr(wb.svc, "active_editor") else None
    if ed is not None and hasattr(ed, "toggle_breakpoint"):
        ed.toggle_breakpoint()
        return True
    return _action(_win(wb), "a_toggle_breakpoint") or _menu(_win(wb), "Debug/Toggle Breakpoint") or True


def _compare_with(wb, args):
    """workbench.files.action.compareFileWith: pick a file, open a Diff with the active one."""
    from PyQt6.QtWidgets import QFileDialog
    ed = wb.svc.active_editor() if hasattr(wb.svc, "active_editor") else None
    if ed is None or os.environ.get("RADIDE_TEST_NO_DIALOGS"):
        return True
    other, _ = QFileDialog.getOpenFileName(_win(wb), "Select File to Compare", str(Path(ed.path).parent))
    if other and wb.svc.host.running():
        wb.svc.execute("vscode.diff", [{"$uri": Path(ed.path).resolve().as_uri()}, {"$uri": Path(other).resolve().as_uri()},
                                       f"{Path(ed.path).name} ↔ {Path(other).name}"])
    return True


def _palette_move(step: int):
    def run(wb, args):
        box = getattr(_win(wb), "command_palette", None)
        if box is not None and box.isVisible() and box.list.count():
            box.list.setCurrentRow((box.list.currentRow() + step) % box.list.count())
        else:
            from ..features import command_palette as cp
            cp.quick_open(_win(wb), "edt mru ")
        return True
    return run


def _tasks_json(wb, args):
    folders = wb.svc.folders() if hasattr(wb.svc, "folders") else []
    if not folders:
        return True
    p = Path(folders[0]) / ".vscode" / "tasks.json"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{\n  "version": "2.0.0",\n  "tasks": []\n}\n', "utf-8")
    wb.svc.open_path(str(p))
    return True


COMMANDS.update({
    "list.focusDown": _list_cmd("focusDown"), "list.focusUp": _list_cmd("focusUp"),
    "list.focusFirst": _list_cmd("focusFirst"), "list.focusLast": _list_cmd("focusLast"),
    "list.focusPageDown": _list_cmd("focusPageDown"), "list.focusPageUp": _list_cmd("focusPageUp"),
    "list.select": _list_cmd("select"), "list.collapse": _list_cmd("collapse"), "list.expand": _list_cmd("expand"),
    "list.toggleExpand": _list_cmd("toggleExpand"),
    "workbench.action.terminal.runSelectedText": _run_selected_text,
    "editor.debug.action.toggleBreakpoint": _toggle_breakpoint,
    "editor.debug.action.runToCursor": lambda wb, a: _action(_win(wb), "a_run_to_cursor") or
    _menu(_win(wb), "Debug/Run To Cursor") or True,
    "workbench.files.action.compareFileWith": _compare_with,
    "workbench.action.quickOpenNavigateNextInRecentFilesPicker": _palette_move(+1),
    "workbench.action.quickOpenNavigatePreviousInRecentFilesPicker": _palette_move(-1),
    "workbench.action.quickOpenSelectNext": _palette_move(+1),
    "workbench.action.quickOpenSelectPrevious": _palette_move(-1),
    "workbench.action.tasks.configureTaskRunner": _tasks_json,
    "workbench.action.tasks.configureDefaultBuildTask": _tasks_json,
    "filesExplorer.findInFolder": lambda wb, a: _menu(_win(wb), "Edit/Find in Files...") or True,
    "breadcrumbs.focusAndSelect": _palette("@"),
    "workbench.action.closeWindow": lambda wb, a: (_win(wb).close(), True)[1],
})


def _launch_json(wb):
    """workbench.action.debug.configure: .vscode/launch.json of the first workspace folder."""
    folders = wb.svc.folders() if hasattr(wb.svc, "folders") else []
    if not folders:
        return True
    p = Path(folders[0]) / ".vscode" / "launch.json"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{\n  "version": "0.2.0",\n  "configurations": []\n}\n', "utf-8")
    wb.svc.open_path(str(p))
    return True

# accepted, nothing to do in RAD IDE (one editor group, one window, no editor locking ...)
NOOP = {
    "workbench.action.lockEditorGroup", "workbench.action.unlockEditorGroup", "workbench.action.splitEditor",
    "workbench.action.splitEditorRight", "workbench.action.splitEditorDown", "workbench.action.moveEditorToNextGroup",
    "workbench.action.moveEditorToPreviousGroup", "workbench.action.newGroupRight", "workbench.action.newGroupBelow",
    "workbench.action.focusSecondEditorGroup", "workbench.action.focusThirdEditorGroup", "workbench.action.joinAllGroups",
    "workbench.action.evenEditorWidths", "workbench.action.toggleMaximizeEditorGroup",
    "workbench.action.terminal.scrollToBottom", "workbench.action.terminal.scrollToTop",
    "workbench.action.focusNextGroup", "workbench.action.focusPreviousGroup", "vscode.setEditorLayout",
    "workbench.action.editorLayoutSingle", "workbench.action.toggleEditorGroupLayout", "workbench.action.resetViewLocations",
    "workbench.action.toggleDevTools", "workbench.action.closeEditorsInOtherGroups", "workbench.action.closeEditorsInGroup",
}


NOOP.update({"noop", "workbench.action.movePanelToSecondarySideBar", "outline.expand", "explorer.openAndPassFocus"})


def _settings_query(args) -> str:
    a = _arg(args)
    if isinstance(a, dict):
        return str(a.get("query") or "")
    return str(a or "")


def handles(command: str) -> bool:
    return command in COMMANDS or command in NOOP


def run(wb, command: str, args):
    """-> True / value / Deferred when handled, None when this module does not know the command."""
    if command in NOOP:
        return True
    fn = COMMANDS.get(command)
    if fn is None:
        return None
    return fn(wb, args if isinstance(args, list) else [args])


__all__ = ["COMMANDS", "NOOP", "Deferred", "run", "handles", "open_settings", "show_dock"]
