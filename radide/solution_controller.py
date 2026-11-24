"""The open solution and its projects (moved out of MainWindow): open / close a solution, which project is
active and the state each one keeps (documents, designers, code views, breakpoints), the language plugin of a
form / file, recent projects and the New / Open dialogs.

The state itself (win.sln, win.project, win.plugin, win.docs ...) still lives on the window - features read it
there; MainWindow keeps one-line methods with the same names and emits the lifecycle events around them
(project_opening / project_opened / project_activated: radide/extension_points.py). Calls between the steps go
through the window (``w.<name>``).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from . import APP_NAME
from .dialogs import NewProjectDialog
from .languages import get_plugin
from .languages import plugin_for_form as _form_plugin
from .languages import plugin_for_module as _module_plugin
from .model import Project
from .solution import EXT as SOLUTION_EXT
from .solution import Solution
from .start_page import StartPage


class SolutionController:
    def __init__(self, win):
        self.win = win

    def _open_project(self, folder: Path, ask: bool, activate):
        w = self.win
        path = Path(folder).resolve()
        try:                     # .sln / .csproj / .vbp / .dpr / pom.xml ... opened in place (foreign_projects.py)
            from .features.foreign_projects import is_foreign, open_foreign
            if is_foreign(path):
                if open_foreign(w, path, ask=ask):
                    return
        except Exception as e:  # noqa: BLE001 - fall back to the RAD IDE formats
            w.log(f"*** cannot open {path.name} as a foreign project: {e}")
        if ask and not w._confirm_close_project():
            return
        try:
            sln = Solution.open_any(path)
            projects = sln.all_projects()
            if not projects:
                raise ValueError(f"solution '{sln.name}' has no project that can be opened")
            for p in projects:
                get_plugin(p.language)
        except Exception as e:  # noqa: BLE001 - show any load error to the user
            QMessageBox.critical(w, APP_NAME, f"Cannot open project:\n{e}")
            return
        w.stop_project()
        w._reset()
        w.sln = sln
        for p in projects:
            w._state_for(p)
        target = None
        if activate is not None:
            target = sln.project(activate) if isinstance(activate, str) else sln.project_for_folder(Path(activate))
        if target is None and path.is_dir() and (path / Project.FILE).exists():
            target = sln.project_for_folder(path)          # the project the user asked for
        target = target or sln.startup_project() or projects[0]
        w.activate_project(target)
        w._remember(sln.file if sln.file is not None else Path(target.folder).resolve())
        w._fill_solution()
        project = w.project
        present = [f for f in project.forms if f not in project.missing_forms()]
        if present:
            w.open_designer(project.startup if project.startup in present else present[0])
        elif project.modules:
            w.open_module(project.modules[0])
        w._update_title()
        w._update_actions()
        if len(projects) > 1 or not sln.implicit:
            w.log(f"Opened solution '{sln.name}' ({len(projects)} project{'s' if len(projects) != 1 else ''})")
        else:
            w.log(f"Opened project '{project.name}' ({w.plugin.display_name})")
        missing = [e.name for e in sln.projects if sln.project(e.name) is None]
        if missing:
            w.log(f"*** Projects that could not be loaded: {', '.join(missing)}")
        for p in projects:                         # forms listed in project.radproj but not on disk
            for f in p.missing_forms():
                w.log(f"*** Warning: {p.name}: the form file '{f}.form' was not found "
                         f"(right-click it in Solution Explorer > Remove from Project)")
        from .tools import offer_restore
        offer_restore(w)
    def close_solution(self):
        """File > Close Solution: close every project (asks to save) and show the Start Page."""
        w = self.win
        if w.project is None and w.sln is None:
            return
        if not w._confirm_close_project():
            return
        active = w.project
        for st in list(w._pstates.values()):
            w.activate_project(st["project"])
            w._save_breakpoints()
        if active is not None:
            w.activate_project(active)
        w.stop_project()
        w._reset()
        w.sln, w.project, w.plugin = None, None, None
        w._fill_solution()
        w.solution.clear()
        w.tabs.addTab(StartPage(w), "Start Page")
        w.toolbox.setEnabled(False)
        w._update_title()
        w._update_actions()
        w.log("Solution closed")
    def _state_for(self, project) -> dict:
        w = self.win
        key = w._pkey(project)
        st = w._pstates.get(key)
        if st is None:
            st = {"project": project, "plugin": get_plugin(project.language), "docs": {}, "designers": {},
                  "codeviews": {}, "modviews": {}, "breakpoints": None}
            w._pstates[key] = st
        return st
    def project_states(self) -> list[dict]:
        """State of every open project: {"project", "plugin", "docs", "designers", "codeviews", ...}."""
        w = self.win
        return list(w._pstates.values())
    def projects(self) -> list[Project]:
        w = self.win
        return [st["project"] for st in w._pstates.values()]
    def _activate_project(self, project) -> bool:
        w = self.win
        if isinstance(project, str):
            project = w.sln.project(project) if w.sln is not None else None
        if project is None:
            return False
        key = w._pkey(project)
        if key == w._active_key and w.project is not None:
            return True
        st = w._state_for(project)
        w._active_key = key
        w.project, w.plugin = st["project"], st["plugin"]
        w.docs, w.designers = st["docs"], st["designers"]
        w.codeviews, w.modviews = st["codeviews"], st["modviews"]
        if st["breakpoints"] is None:
            w._load_breakpoints()
            st["breakpoints"] = w.breakpoints
        else:
            w.breakpoints = st["breakpoints"]
        w._update_title()
        return True
    def project_of_widget(self, widget) -> Project | None:
        win = self.win
        key = widget.property("radProject") if widget is not None else None
        st = win._pstates.get(key) if key else None
        return st["project"] if st else None

    def startup_project(self) -> Project | None:
        w = self.win
        return w.sln.startup_project() if w.sln is not None else w.project

    def _forget_project(self, project) -> None:
        """Close the tabs of a project and drop its state (Remove from solution)."""
        w = self.win
        key = w._pkey(project)
        for i in reversed(range(w.tabs.count())):
            tab = w.tabs.widget(i)
            if tab.property("radProject") == key:
                w.tabs.removeTab(i)
                tab.deleteLater()
        w._pstates.pop(key, None)
        if key == w._active_key:
            w._active_key, w.project = None, None
            nxt = w.startup_project()
            if nxt is not None and w._pkey(nxt) in w._pstates:
                w.activate_project(nxt)
            elif w._pstates:
                w.activate_project(next(iter(w._pstates.values()))["project"])
            else:
                w.plugin = None
                w.docs, w.designers, w.codeviews, w.modviews = {}, {}, {}, {}
                w.breakpoints = {}
    def plugin_for_form(self, name: str):
        """Language plugin of a form (project.form_languages, else the project language)."""
        w = self.win
        return _form_plugin(w.project, name) if w.project else w.plugin
    def plugin_for_file(self, filename: str):
        """Language plugin of a code file of the project (form code, designer or module)."""
        w = self.win
        if not w.project:
            return w.plugin
        base = Path(filename).name.lower()
        for name in w.project.forms:
            fp = w.plugin_for_form(name)
            if base in (fp.code_file(name).lower(), fp.designer_file(name).lower()):
                return fp
        return _module_plugin(w.project, base)
    def run_plugin(self):
        """The startup form's plugin: it runs and debugs the program."""
        w = self.win
        if not w.project:
            return w.plugin
        return w.plugin_for_form(w.project.startup) if w.project.startup else w.plugin
    def is_multi_language(self) -> bool:
        w = self.win
        if not w.project:
            return False
        ids = {w.plugin_for_form(f).id for f in w.project.forms}
        ids |= {w.plugin_for_file(m).id for m in w.project.modules}
        return len(ids) > 1
    def recent_projects(self) -> list[str]:
        """Recent solutions (.radsln files) and bare projects (folders), newest first."""
        w = self.win
        items = w.settings.value("recent", []) or []
        if isinstance(items, str):
            items = [items]
        tmp = str(Path(os.environ.get("TEMP", "~"))).lower()

        def ok(p: str) -> bool:
            path = Path(p)
            if p.lower().startswith(tmp):
                return False
            if path.suffix.lower() == SOLUTION_EXT:
                return path.is_file()
            return (path / Project.FILE).exists()
        return [p for p in items if ok(p)][:8]
    def _remember(self, path: Path):
        w = self.win
        items = [str(path)] + [p for p in w.recent_projects() if p.lower() != str(path).lower()]
        w.settings.setValue("recent", items[:8])
        w._refresh_recent()
    def new_project(self):
        """File > New Project: create a project in a new solution or add it to the open one."""
        w = self.win
        dlg = NewProjectDialog(w)
        if not dlg.exec():
            return None
        w._pending_template = None           # templates are applied here (also Class Library)
        from .features.solution_ui import create_project_from_dialog
        return create_project_from_dialog(w, dlg)
    def open_project_dialog(self):
        w = self.win
        filters = f"RAD IDE solution or project (*{SOLUTION_EXT} {Project.FILE})"
        try:                     # projects of other IDEs, opened in place (radide/features/foreign_projects.py)
            from .features.foreign_projects import file_filter
            filters = (f"All supported projects (*{SOLUTION_EXT} {Project.FILE} "
                       f"{file_filter(patterns_only=True)});;{filters};;{file_filter()}")
        except Exception as e:  # noqa: BLE001
            w.log(f"[foreign projects] {e}")
        f, _ = QFileDialog.getOpenFileName(w, "Open Project/Solution", "", filters)
        if f:
            w.open_project(Path(f))
    def new_window(self):
        """File > New Window: start another, independent RAD IDE window (its own process)."""
        w = self.win
        import subprocess
        if getattr(sys, "frozen", False):
            argv = [sys.executable, "--new-window"]
        else:
            exe = Path(sys.executable)
            pyw = exe.with_name("pythonw.exe")
            argv = [str(pyw if pyw.exists() else exe), "-m", "radide", "--new-window"]
        try:
            subprocess.Popen(argv, cwd=str(Path(__file__).resolve().parent.parent),
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if not getattr(
                                 sys, "frozen", False) else 0)
            w.statusBar().showMessage("Opening a new RAD IDE window...", 4000)
        except OSError as e:
            QMessageBox.warning(w, "New Window", f"Cannot start a new window:\n{e}")
    def open_folder_dialog(self):
        """File > Open Folder...: a RAD IDE project/solution folder, a foreign project folder (Visual Studio,
        VB6, Cargo, Laravel ...) opened in place, or any folder as a folder workspace (like VS Code)."""
        w = self.win
        start = str(w.project.folder.parent) if w.project is not None else ""
        d = QFileDialog.getExistingDirectory(w, "Open Folder", start)
        if not d:
            return
        from .single_instance import open_target
        open_target(w, Path(d))
        w._remember(str(Path(d)))
    def open_file_dialog(self):
        """File > Open File...: any file in an editor tab (the project's own editors for its code files)."""
        w = self.win
        start = str(w.project.folder) if w.project is not None else ""
        f, _ = QFileDialog.getOpenFileName(w, "Open File", start, "All files (*)")
        if f:
            w.open_any_file(Path(f))
    def _fill_recent_menu(self):
        w = self.win
        m = w.recent_menu
        m.clear()
        items = w.recent_projects()
        for i, path in enumerate(items, 1):
            p = Path(path)
            label = f"&{i}  {p.stem if p.suffix.lower() == SOLUTION_EXT else p.name}  -  {path}"
            m.addAction(label, lambda f=path: w.open_project(Path(f)))
        if not items:
            a = m.addAction("(no recent projects)")
            a.setEnabled(False)
        else:
            m.addSeparator()
            m.addAction("Clear List", lambda: (w.settings.remove("recent"), w._refresh_recent()))
    def _refresh_recent(self):
        w = self.win
        for i in range(w.tabs.count()):
            tab = w.tabs.widget(i)
            if isinstance(tab, StartPage):
                tab.refresh()
