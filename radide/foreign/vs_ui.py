"""Visual Studio solutions in the IDE window (radide/foreign/vs_solution.py is the model).

Solution Explorer like Visual Studio (solution folders, Dependencies / References with frameworks,
packages, projects and assemblies, folders, Form1.cs > Form1.Designer.cs + Form1.resx, C++
filters), context menus (Build / Rebuild / Clean, Set as StartUp Project, Add > New Item /
Existing Item / New Folder / Reference, Manage NuGet Packages, Exclude From Project, Edit Project
File, Properties), the Configuration / Platform combos, Build/Rebuild/Clean Solution and Run /
Debug sessions (dotnet / MSBuild via vswhere / MinGW fallback for .vcxproj, netcoredbg).
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                             QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox,
                             QStyle, QTabWidget, QToolBar, QTreeWidgetItem, QVBoxLayout, QWidget)

from . import msbuild as MB
from .vs_solution import ITEM_TEMPLATES, LANG_NAME, PROJECT_EXTS, VsProject, VsSolution, load_vs

ROLE = Qt.ItemDataRole.UserRole
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


def _role():
    from ..features.solution_ui import PROJECT_ROLE
    return PROJECT_ROLE


def _icon(win, name: str):
    return win.style().standardIcon(getattr(QStyle.StandardPixmap, name))


def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


def _info(win, title: str, text: str) -> None:
    _log(win, text)
    if not OFFSCREEN:
        QMessageBox.information(win, title, text)


# ====================================================================== open
def open_in_window(win, path: Path) -> bool:
    sln = load_vs(path)
    projects = sln.all_projects()
    if not projects:
        raise ValueError(f"{Path(path).name}: no project of the solution could be loaded")
    if hasattr(win, "_confirm_close_project") and not win._confirm_close_project():
        return True                                    # handled: the user cancelled
    win.stop_project()
    win._reset()
    win.sln = sln
    for p in projects:
        win._state_for(p)
    target = None
    if Path(path).suffix.lower() in PROJECT_EXTS:
        target = next((p for p in projects if os.path.normcase(str(p.ms.path)) ==
                       os.path.normcase(str(Path(path).resolve()))), None)
    target = target or sln.startup_project() or projects[0]
    win.activate_project(target)
    try:
        win._remember(Path(path).resolve())
    except Exception:  # noqa: BLE001
        pass
    win._fill_solution()
    _open_first(win, target)
    try:
        win.toolbox.setEnabled(bool(target.forms))
    except Exception:  # noqa: BLE001
        pass
    win._update_title()
    win._update_actions()
    kind = "solution" if sln.model is not None else "project"
    _log(win, f"Opened Visual Studio {kind} '{sln.name}' in place ({len(projects)} project"
              f"{'s' if len(projects) != 1 else ''}): {sln.file}")
    for p in projects:
        ms = p.ms
        style = "SDK-style" if ms.is_sdk else "legacy (non-SDK)"
        tf = ", ".join(ms.target_frameworks) or ("native" if ms.language == "C++" else "?")
        _log(win, f"  {sln.name_of(p)}: {LANG_NAME.get(ms.language, ms.language)} {style} {ms.output_type} [{tf}]"
                  f" - {len(p.modules)} files, {len(p.forms)} form(s)")
        for n in p.notes:
            _log(win, f"    {n}")
    missing = [e.name for e in sln.projects if sln.project(e.name) is None]
    if missing:
        _log(win, f"*** Projects that could not be loaded: {', '.join(missing)}")
    tc = MB.toolchain_report()
    _log(win, f"  Toolchain: dotnet={tc['dotnet'] or 'not found'}; MSBuild={tc['msbuild'] or 'not found'}"
              f"{' (+ C++ tools)' if tc['vc_tools'] else ''}")
    _log(win, f"  IDE state (not in your folder): {sln.state}")
    refresh_config_ui(win)
    _watch(win, sln)
    return True


def _watch(win, sln: VsSolution) -> None:
    """Re-read project files changed outside the IDE (or in its text editor)."""
    from PyQt6.QtCore import QFileSystemWatcher
    old = getattr(win, "_vs_watcher", None)
    if old is not None:
        old.deleteLater()
    paths = [str(p.ms.path) for p in sln.all_projects()] + ([str(sln.file)] if sln.file else [])
    w = QFileSystemWatcher([p for p in paths if Path(p).exists()], win)
    win._vs_watcher = w

    def changed(path):
        if win.sln is not sln:
            return
        if Path(path).exists() and path not in w.files():
            w.addPath(path)                       # editors that replace the file
        QTimer.singleShot(300, lambda: _external_change(win, sln, Path(path)))
    w.fileChanged.connect(changed)


def _external_change(win, sln: VsSolution, path: Path) -> None:
    if win.sln is not sln:
        return
    for p in sln.all_projects():
        if os.path.normcase(str(p.ms.path)) == os.path.normcase(str(path)) and p.changed_on_disk():
            try:
                p.reload()
                _log(win, f"{p.name}: {path.name} changed on disk - reloaded")
            except Exception as e:  # noqa: BLE001 - half-written file: keep the old model
                _log(win, f"*** {p.name}: cannot re-read {path.name}: {e}")
                return
            _refresh(win)


def _open_first(win, project: VsProject) -> None:
    present = [f for f in project.forms if f not in project.missing_forms()]
    try:
        if present:
            win.open_designer(present[0])
            return
    except Exception as e:  # noqa: BLE001 - a form the designer cannot read: open code instead
        _log(win, f"*** {project.name}: the designer could not open {present[0]}: {e}")
    mods = project.modules
    main = next((m for m in mods if Path(m).stem.lower() in ("program", "main", "module1", "library")), None)
    code = main or next((m for m in mods if m.lower().endswith(project.ms.code_ext)), None)
    if code:
        win.open_module(code)


# ====================================================================== Solution Explorer
def _set(item, kind, name, key, icon=None, win=None, tip=""):
    item.setData(0, ROLE, (kind, name))
    item.setData(0, _role(), key)
    if icon and win is not None:
        item.setIcon(0, _icon(win, icon))
    if tip:
        item.setToolTip(0, tip)
    return item


def fill_project(win, project: VsProject, pi, name: str) -> None:
    if project.changed_on_disk():
        try:
            project.reload()
        except Exception as e:  # noqa: BLE001
            _log(win, f"*** {project.name}: cannot re-read {project.ms.path.name}: {e}")
    ms = project.ms
    key = win._pkey(project)
    pi.setText(0, name + ("" if not project.is_library else "  (library)"))
    pi.setToolTip(0, f"{LANG_NAME.get(ms.language, ms.language)} project ({'SDK-style' if ms.is_sdk else 'legacy'})"
                     f"\n{ms.path}" + ("\nStartUp Project" if win.sln is not None and
                                         win.sln.startup.lower() == name.lower() else ""))
    _fill_deps(win, project, pi, key)
    _fill_files(win, project, pi, key)


def _fill_deps(win, project: VsProject, pi, key) -> None:
    ms = project.ms
    pkgs, prefs, refs = ms.package_references, ms.project_references, ms.assembly_references
    if ms.language == "C++" and not (pkgs or prefs or refs):
        return
    title = "Dependencies" if ms.is_sdk else "References"
    deps = _set(QTreeWidgetItem(pi, [title]), "foreign_deps", title, key, "SP_FileLinkIcon", win)
    if ms.is_sdk:
        fw = _set(QTreeWidgetItem(deps, ["Frameworks"]), "foreign_depgroup", "frameworks", key, "SP_DirIcon", win)
        names = ["Microsoft.NETCore.App"]
        if ms.prop("UseWindowsForms").lower() == "true" or ms.prop("UseWPF").lower() == "true":
            names.append("Microsoft.WindowsDesktop.App")
        if "Web" in ms.sdk:
            names.append("Microsoft.AspNetCore.App")
        if ms.is_netframework:
            names = [f".NET Framework ({', '.join(ms.target_frameworks)})"]
        for n in names:
            _set(QTreeWidgetItem(fw, [n]), "foreign_dep", f"framework|{n}", key, "SP_ComputerIcon", win)
        groups = (("Packages", pkgs, "package"), ("Projects", prefs, "project"), ("Assemblies", refs, "assembly"))
        for title2, items, kind in groups:
            if not items:
                continue
            g = _set(QTreeWidgetItem(deps, [title2]), "foreign_depgroup", kind, key, "SP_DirIcon", win)
            for it in items:
                _dep_item(win, g, it, kind, key)
    else:
        for it in refs:
            _dep_item(win, deps, it, "assembly", key)
        for it in prefs:
            _dep_item(win, deps, it, "project", key)
        for it in pkgs:
            _dep_item(win, deps, it, "package", key)


def _dep_item(win, parent, it, kind, key):
    inc = MB.xml_unescape(it.include)
    if kind == "package":
        text = f"{inc} ({it.version})" if it.version else inc
        icon = "SP_DriveNetIcon"
    elif kind == "project":
        text = Path(inc.replace("\\", "/")).stem
        icon = "SP_DirLinkIcon"
    else:
        text = inc.split(",")[0]
        icon = "SP_FileLinkIcon"
    return _set(QTreeWidgetItem(parent, [text]), "foreign_dep", f"{kind}|{inc}", key, icon, win, inc)


def _fill_files(win, project: VsProject, pi, key) -> None:
    ms = project.ms
    items = [f for f in project.items if f.kind != "Folder"]
    filters = MB.read_filters(ms) if ms.language == "C++" else {}
    # nesting: DependentUpon (explicit or inferred) -> parent file
    by_low = {f.rel.lower(): f for f in items}
    parent_of: dict[str, str] = {}
    for f in items:
        dep = f.dependent_upon
        if dep:
            d = str(Path(f.rel).parent.as_posix())
            cand = (dep if d in ("", ".") else f"{d}/{dep}").replace("\\", "/")
            if cand.lower() in by_low and cand.lower() != f.rel.lower():
                parent_of[f.rel.lower()] = by_low[cand.lower()].rel
    for name, code in project.form_code.items():         # Form1.Designer.cs under Form1.cs (VS does this)
        des = project.form_designer.get(name, "")
        if des and des.lower() not in parent_of:
            parent_of[des.lower()] = code
    folders: dict[str, QTreeWidgetItem] = {}

    def folder_item(path: str):
        if not path:
            return pi
        if path in folders:
            return folders[path]
        parent = folder_item(path.rsplit("/", 1)[0] if "/" in path else "")
        it = _set(QTreeWidgetItem(parent, [path.rsplit("/", 1)[-1]]), "foreign_folder", path, key, "SP_DirIcon", win)
        folders[path] = it
        return it

    # folders first (VS order: Properties / My Project first, then alphabetical)
    def place(f):
        if filters:
            return filters.get(f.rel.lower(), "")
        return str(Path(f.rel).parent.as_posix()).strip(".").strip("/")
    dirs = sorted({place(f) for f in items if f.rel.lower() not in parent_of} - {""},
                  key=lambda d: (0 if d.split("/")[0].lower() in ("properties", "my project") else 1, d.lower()))
    for d in dirs:
        folder_item(d)
    for f in project.ms.explicit("Folder"):
        folder_item(f.rel.strip("/"))
    form_by_code = {v.lower(): k for k, v in project.form_code.items()} if project.forms else {}
    made: dict[str, QTreeWidgetItem] = {}

    def file_item(f, parent):
        rel = f.rel
        low = rel.lower()
        label = Path(rel).name
        if low in form_by_code:
            it = _set(QTreeWidgetItem(parent, [label]), "design", form_by_code[low], key, "SP_TitleBarNormalButton",
                      win, f"{rel}\nDouble-click: designer - right-click > View Code")
        elif rel in project.modules:
            it = _set(QTreeWidgetItem(parent, [label]), "module", rel, key, "SP_FileIcon", win, rel)
        else:
            it = _set(QTreeWidgetItem(parent, [label]), "foreign_file", str(project.folder / rel), key,
                      "SP_FileIcon", win, rel)
        if not (project.folder / rel).exists():
            it.setForeground(0, Qt.GlobalColor.gray)
            it.setToolTip(0, f"{rel} (file not found)")
        made[low] = it
        return it

    order = sorted(items, key=lambda f: Path(f.rel).name.lower())
    if ms.language == "F#":
        order = items                                        # F# compile order matters: keep it
    for f in order:
        if f.rel.lower() in parent_of:
            continue
        file_item(f, folder_item(place(f)))
    pending = [f for f in order if f.rel.lower() in parent_of]
    for _ in range(4):                                       # nested chains (a.cs > a.Designer.cs > ...)
        rest = []
        for f in pending:
            par = made.get(parent_of[f.rel.lower()].lower())
            if par is None:
                rest.append(f)
            else:
                file_item(f, par)
        pending = rest
    for f in pending:
        file_item(f, folder_item(place(f)))


def after_fill(win, sln: VsSolution, root) -> None:
    """Solution folders and solution items (VS 'Solution Items'), then collapse the dependency
    nodes like Visual Studio does."""
    model = sln.model
    n = len(sln.projects)
    root.setText(0, f"Solution '{sln.name}' ({n} of {n} project{'s' if n != 1 else ''})")
    root.setToolTip(0, str(sln.file))
    if model is not None:
        by_path: dict[tuple, QTreeWidgetItem] = {}

        def folder(names: list[str]):
            parent = root
            for i in range(len(names)):
                k = tuple(names[: i + 1])
                if k not in by_path:
                    it = QTreeWidgetItem([names[i]])
                    it.setData(0, ROLE, ("foreign_slnfolder", "/".join(k)))
                    it.setIcon(0, _icon(win, "SP_DirClosedIcon"))
                    idx = sum(1 for j in range(parent.childCount())
                              if (parent.child(j).data(0, ROLE) or ("",))[0] == "foreign_slnfolder")
                    parent.insertChild(idx, it)
                    by_path[k] = it
                parent = by_path[k]
            return parent
        for f in model.folders():
            fi = folder(model.folder_path(f) + [f.name])
            for rel in f.items:
                it = QTreeWidgetItem(fi, [Path(rel).name])
                it.setData(0, ROLE, ("foreign_file", str((model.folder / rel).resolve())))
                it.setIcon(0, _icon(win, "SP_FileIcon"))
        for i in reversed(range(root.childCount())):
            it = root.child(i)
            data = it.data(0, ROLE) or ("",)
            if data[0] != "project":
                continue
            proj = sln.project(data[1])
            entry = getattr(proj, "sln_entry", None)
            path = model.folder_path(entry) if entry is not None else []
            if path:
                root.takeChild(i)
                target = folder(path)
                target.addChild(it)

    def collapse():                       # the tree may have been refilled since: walk the current one
        try:
            tree = win.solution
            stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
            while stack:
                it = stack.pop()
                data = it.data(0, ROLE) or ("",)
                if data[0] in ("foreign_deps", "foreign_folder", "design"):
                    it.setExpanded(False)
                stack.extend(it.child(i) for i in range(it.childCount()))
        except RuntimeError:
            pass
    QTimer.singleShot(0, collapse)


# ====================================================================== activation
def activate(win, project: VsProject | None, item, kind: str, name) -> None:
    if kind == "foreign_file":
        p = Path(name)
        if p.suffix.lower() in PROJECT_EXTS + (".sln", ".slnx"):
            open_text(win, p)
        else:
            win.open_any_file(p)
    elif kind == "foreign_dep" and project is not None:
        dkind, _, inc = str(name).partition("|")
        if dkind == "project":
            target = (project.folder / inc.replace("\\", "/")).resolve()
            other = _project_by_file(win, target)
            if other is not None:
                win.activate_project(other)
                _open_first(win, other)
        elif dkind == "package":
            open_text(win, project.ms.path)
    elif kind in ("foreign_deps", "foreign_folder", "foreign_depgroup", "foreign_slnfolder") and item is not None:
        item.setExpanded(not item.isExpanded())


def open_text(win, path: Path):
    """A project/solution file in a text editor tab (saved as typed; the IDE re-reads it)."""
    return win.open_any_file(Path(path))


def _project_by_file(win, path: Path) -> VsProject | None:
    sln = win.sln
    if not isinstance(sln, VsSolution):
        return None
    for p in sln.all_projects():
        if os.path.normcase(str(p.ms.path)) == os.path.normcase(str(Path(path).resolve())):
            return p
    return None


def editor_for_file(win, sln: VsSolution, file):
    """MainWindow._editor_for_file hook: absolute or project-relative paths in any project."""
    p = Path(str(file))
    best, rel = None, ""
    if p.is_absolute():
        for proj in sln.all_projects():
            try:
                r = p.resolve().relative_to(Path(proj.folder).resolve()).as_posix()
            except (ValueError, OSError):
                continue
            if best is None or len(str(proj.folder)) > len(str(best.folder)):
                best, rel = proj, r
    else:
        best, rel = win.project if isinstance(win.project, VsProject) else None, p.as_posix()
    if best is None:
        return None
    low = rel.lower()
    form = next((n for n, c in best.form_code.items() if c.lower() == low), None)
    mod = next((m for m in best.modules if m.lower() == low), None)
    if form is None and mod is None:
        return None
    win.activate_project(best)
    if form is not None:
        win.open_code(form)
        return win.codeviews[form].editor
    win.open_module(mod)
    return win.modviews[mod].editor


# ====================================================================== menus
def solution_menu(win, sln: VsSolution, item):
    m = QMenu(win)
    m.addAction("Build Solution", lambda: build(win, sln))
    m.addAction("Rebuild Solution", lambda: build(win, sln, verb="rebuild"))
    m.addAction("Clean Solution", lambda: build(win, sln, verb="clean"))
    m.addSeparator()
    sub = m.addMenu("Set StartUp Project")
    for e in sln.projects:
        a = sub.addAction(e.name, lambda n=e.name: _set_startup(win, n))
        a.setCheckable(True)
        a.setChecked(sln.startup.lower() == e.name.lower())
    cfg = m.addMenu("Configuration")
    for c in sln.configurations():
        a = cfg.addAction(c, lambda c=c: set_configuration(win, c, None))
        a.setCheckable(True)
        a.setChecked(c == sln.configuration)
    if sln.model is not None:
        add = m.addMenu("Add")
        add.addAction("New Project...", lambda: new_project_dialog(win, sln))
        add.addAction("Existing Project...", lambda: add_existing_project_dialog(win, sln))
    m.addSeparator()
    m.addAction(win.a_run)
    m.addAction(win.a_run_nodebug)
    m.addSeparator()
    m.addAction("Save All", win.save_all)
    if sln.file is not None:
        m.addAction(f"Edit {sln.file.name}", lambda: open_text(win, sln.file))
    m.addAction("Open Folder in File Explorer", lambda: _explore(sln.folder))
    m.addAction("Open in Visual Studio", lambda: open_in_visual_studio(win, sln.file))
    m.addSeparator()
    m.addAction("Migrate to a RAD IDE project...", lambda: _migrate(win, sln))
    m.addAction("Properties", lambda: solution_properties(win, sln))
    return m


def project_menu(win, project: VsProject, item, kind, name):
    sln = win.sln if isinstance(win.sln, VsSolution) else None
    m = QMenu(win)
    if kind == "project":
        pname = name
        m.addAction("Build", lambda: build(win, sln, only=[pname]))
        m.addAction("Rebuild", lambda: build(win, sln, only=[pname], verb="rebuild"))
        m.addAction("Clean", lambda: build(win, sln, only=[pname], verb="clean"))
        m.addSeparator()
        a = m.addAction("Set as StartUp Project", lambda: _set_startup(win, pname))
        a.setEnabled(sln is not None and sln.startup.lower() != pname.lower() and not project.is_library)
        _add_menu(win, m, project, "")
        if project.plugin.package_manager is not None:
            m.addAction("Manage NuGet Packages...", lambda: manage_packages(win, project))
        m.addSeparator()
        m.addAction(f"Edit Project File ({project.ms.path.name})", lambda: open_text(win, project.ms.path))
        m.addAction("Reload Project", lambda: _reload(win, project))
        if sln is not None and sln.model is not None:
            m.addAction("Remove from Solution", lambda: remove_project(win, sln, project))
        m.addAction("Open Folder in File Explorer", lambda: _explore(project.folder))
        m.addSeparator()
        m.addAction("Properties", lambda: project_properties(win, project))
        return m
    if kind == "foreign_deps" or (kind == "foreign_depgroup" and name in ("project", "assembly", "frameworks")):
        m.addAction("Add Project Reference...", lambda: add_reference_dialog(win, project, 0))
        if project.ms.language != "C++":
            m.addAction("Add Assembly Reference...", lambda: add_reference_dialog(win, project, 1))
            m.addAction("Manage NuGet Packages...", lambda: manage_packages(win, project))
        return m
    if kind == "foreign_depgroup" and name == "package":
        m.addAction("Manage NuGet Packages...", lambda: manage_packages(win, project))
        return m
    if kind == "foreign_dep":
        dkind, _, inc = str(name).partition("|")
        if dkind == "framework":
            m.deleteLater()
            return None
        if dkind == "project":
            m.addAction("Open", lambda: activate(win, project, item, kind, name))
        mk = {"package": "PackageReference", "project": "ProjectReference", "assembly": "Reference"}[dkind]
        m.addAction("Remove", lambda: _remove_ref(win, project, mk, inc))
        return m
    if kind == "foreign_folder":
        _add_menu(win, m, project, "" if MB.read_filters(project.ms) else name)
        m.addAction("Open Folder in File Explorer", lambda: _explore(project.folder / name))
        return m
    if kind in ("module", "design", "foreign_file"):
        rel = name if kind == "module" else (project.form_code.get(name, "") if kind == "design" else
                                             _rel(project, Path(name)))
        if kind == "design":
            m.addAction("View Designer", lambda: win.open_designer(name))
            m.addAction("View Code", lambda: win.open_code(name))
        else:
            m.addAction("Open", lambda: activate(win, project, item, kind, name) if kind == "foreign_file"
                        else win.open_module(name))
        if rel:
            m.addSeparator()
            m.addAction("Exclude From Project", lambda: _exclude(win, project, rel))
            m.addAction("Open Containing Folder", lambda: _explore((project.folder / rel).parent))
        return m
    m.deleteLater()
    return None


def _rel(project: VsProject, p: Path) -> str:
    try:
        return p.resolve().relative_to(Path(project.folder).resolve()).as_posix()
    except (ValueError, OSError):
        return ""


def _add_menu(win, m, project: VsProject, rel_dir: str) -> None:
    add = m.addMenu("Add")
    add.addAction("New Item...", lambda: add_new_item_dialog(win, project, rel_dir))
    add.addAction("Existing Item...", lambda: add_existing_item_dialog(win, project, rel_dir))
    if project.ms.language != "C++":
        add.addAction("New Folder", lambda: new_folder(win, project, rel_dir))
    add.addSeparator()
    for t, _e in ITEM_TEMPLATES.get(project.ms.language, [])[:5]:
        add.addAction(f"{t}...", lambda t=t: add_new_item_dialog(win, project, rel_dir, t))
    add.addSeparator()
    add.addAction("Project Reference...", lambda: add_reference_dialog(win, project, 0))
    if project.ms.language != "C++":
        add.addAction("Assembly Reference...", lambda: add_reference_dialog(win, project, 1))


def _explore(folder) -> None:
    if folder and Path(folder).exists() and not OFFSCREEN:
        try:
            os.startfile(str(folder))          # noqa: S606 - Windows Explorer
        except (OSError, AttributeError):
            pass


def _refresh(win) -> None:
    win._fill_solution()
    refresh_config_ui(win)


def _reload(win, project: VsProject) -> None:
    project.reload()
    _refresh(win)
    _log(win, f"{project.name}: reloaded {project.ms.path.name}")


def _set_startup(win, name: str) -> None:
    from ..features.solution_ui import set_startup_project
    set_startup_project(win, name)


def _remove_ref(win, project: VsProject, kind: str, inc: str) -> None:
    if project.remove_reference(kind, inc):
        _log(win, f"{project.name}: removed {kind} {inc} from {project.ms.path.name}")
    _refresh(win)


def _exclude(win, project: VsProject, rel: str) -> None:
    if project.exclude(rel):
        _log(win, f"{project.name}: {rel} excluded from {project.ms.path.name} (the file stays on disk)")
    _refresh(win)


def _migrate(win, sln) -> None:
    try:
        from ..features import migrate_wizard
        fn = getattr(migrate_wizard, "show_wizard", None) or getattr(migrate_wizard, "migrate_dialog", None)
        if callable(fn):
            fn(win, sln.file)
            return
    except Exception as e:  # noqa: BLE001
        _log(win, f"[migrate] {e}")
    _info(win, "Migrate", "The migration wizard is not available in this build.")


def open_in_visual_studio(win, path) -> bool:
    found = MB._vswhere("-latest", "-property", "productPath")
    if not found or not path:
        _info(win, "Visual Studio", "Visual Studio was not found (vswhere).")
        return False
    if OFFSCREEN:
        return True
    subprocess.Popen([found[0], str(path)], creationflags=NO_WINDOW)      # noqa: S603
    return True


# ====================================================================== dialogs
def add_new_item_dialog(win, project: VsProject, rel_dir: str = "", template: str = "", exec_: bool = True):
    dlg = QDialog(win)
    dlg.setWindowTitle(f"Add New Item - {project.name}")
    lay = QVBoxLayout(dlg)
    lst = QListWidget()
    for t, ext in ITEM_TEMPLATES.get(project.ms.language, []):
        it = QListWidgetItem(f"{t}   ({ext})")
        it.setData(ROLE, t)
        lst.addItem(it)
    lst.setCurrentRow(0)
    for i in range(lst.count()):
        if lst.item(i).data(ROLE) == template:
            lst.setCurrentRow(i)
    lay.addWidget(lst)
    form = QFormLayout()
    name = QLineEdit()
    folder = QLineEdit(rel_dir)
    form.addRow("Name:", name)
    form.addRow("Folder:", folder)
    lay.addLayout(form)

    def suggest():
        t = lst.currentItem().data(ROLE) if lst.currentItem() else ""
        base = {"Windows Form": "Form", "User Control": "UserControl", "Interface": "IInterface",
                "Module": "Module", "Enum": "Enum"}.get(t, "Class" if "Class" in t else "File")
        i = 1
        while any(Path(m).stem.lower() == f"{base}{i}".lower() for m in project.modules + list(project.forms)):
            i += 1
        name.setText(f"{base}{i}")
    lst.currentItemChanged.connect(lambda *_: suggest())
    suggest()
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.template_list, dlg.name_edit, dlg.folder_edit = lst, name, folder
    if not exec_:
        return dlg
    if not dlg.exec():
        return None
    return do_add_new_item(win, project, lst.currentItem().data(ROLE), folder.text(), name.text())


def do_add_new_item(win, project: VsProject, template: str, rel_dir: str, name: str):
    try:
        created = project.add_new_item(template, rel_dir, name)
    except (OSError, ValueError) as e:
        if not OFFSCREEN:
            QMessageBox.warning(win, "Add New Item", str(e))
        _log(win, f"*** Add New Item: {e}")
        return None
    _log(win, f"{project.name}: added {', '.join(created)}")
    win.activate_project(project)
    _refresh(win)
    first = created[0]
    form = next((n for n, c in project.form_code.items() if c == first), None)
    try:
        if form is not None:
            win.open_designer(form)
        elif first in project.modules:
            win.open_module(first)
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** cannot open {first}: {e}")
    return created


def add_existing_item_dialog(win, project: VsProject, rel_dir: str = ""):
    files, _ = QFileDialog.getOpenFileNames(win, "Add Existing Item", str(project.folder / rel_dir), "All files (*)")
    out = []
    for f in files:
        try:
            out.append(project.add_existing_item(Path(f), rel_dir))
        except OSError as e:
            _log(win, f"*** {e}")
    if out:
        _log(win, f"{project.name}: added {', '.join(out)}")
        _refresh(win)
    return out


def new_folder(win, project: VsProject, rel_dir: str = "", name: str | None = None):
    if name is None:
        name, ok = QInputDialog.getText(win, "New Folder", "Folder name:", text="NewFolder")
        if not ok or not name.strip():
            return None
    rel = f"{rel_dir.strip('/')}/{name.strip()}".strip("/")
    (project.folder / rel).mkdir(parents=True, exist_ok=True)
    project.ms.add_item("Folder", MB.ms_path(rel) + "\\")
    project.ms.save()
    project.reload()
    _refresh(win)
    return rel


FRAMEWORK_ASSEMBLIES = ["System", "System.Core", "System.Data", "System.Drawing", "System.Windows.Forms",
                        "System.Xml", "System.Xml.Linq", "System.Net.Http", "System.Configuration",
                        "System.Deployment", "System.Runtime.Serialization", "System.ServiceModel",
                        "System.Web", "System.Numerics", "System.IO.Compression", "System.Management",
                        "Microsoft.CSharp", "Microsoft.VisualBasic", "PresentationCore", "PresentationFramework",
                        "WindowsBase"]


def add_reference_dialog(win, project: VsProject, tab: int = 0, exec_: bool = True):
    """Reference Manager: Projects (of the solution) / Assemblies / Browse (.dll)."""
    sln = win.sln if isinstance(win.sln, VsSolution) else None
    dlg = QDialog(win)
    dlg.setWindowTitle(f"Reference Manager - {project.name}")
    dlg.resize(520, 420)
    lay = QVBoxLayout(dlg)
    tabs = QTabWidget()
    lay.addWidget(tabs)
    plist = QListWidget()
    have = {os.path.normcase(str((project.folder / MB.xml_unescape(i.include).replace("\\", "/")).resolve()))
            for i in project.ms.project_references}
    for other in (sln.all_projects() if sln else []):
        if other is project:
            continue
        it = QListWidgetItem(f"{sln.name_of(other)}   [{LANG_NAME.get(other.ms.language, '')}]")
        it.setData(ROLE, other)
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        it.setCheckState(Qt.CheckState.Checked if os.path.normcase(str(other.ms.path)) in have
                         else Qt.CheckState.Unchecked)
        plist.addItem(it)
    tabs.addTab(plist, "Projects")
    alist = QListWidget()
    current = {MB.xml_unescape(i.include).split(",")[0].lower() for i in project.ms.assembly_references}
    for a in FRAMEWORK_ASSEMBLIES:
        it = QListWidgetItem(a)
        it.setData(ROLE, a)
        it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        it.setCheckState(Qt.CheckState.Checked if a.lower() in current else Qt.CheckState.Unchecked)
        alist.addItem(it)
    tabs.addTab(alist, "Assemblies")
    browse = QWidget()
    bl = QVBoxLayout(browse)
    blist = QListWidget()
    bl.addWidget(blist)
    btn = QDialogButtonBox()
    b = btn.addButton("Browse...", QDialogButtonBox.ButtonRole.ActionRole)

    def pick():
        fs, _ = QFileDialog.getOpenFileNames(dlg, "Browse", str(project.folder), "Assemblies (*.dll *.exe)")
        for f in fs:
            blist.addItem(f)
    b.clicked.connect(pick)
    bl.addWidget(btn)
    tabs.addTab(browse, "Browse")
    if project.ms.language == "C++":
        tabs.setTabEnabled(1, False)
        tabs.setTabEnabled(2, False)
    tabs.setCurrentIndex(tab)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.projects_list, dlg.assemblies_list, dlg.browse_list = plist, alist, blist

    def apply():
        changed = []
        for i in range(plist.count()):
            it = plist.item(i)
            other = it.data(ROLE)
            on = it.checkState() == Qt.CheckState.Checked
            was = os.path.normcase(str(other.ms.path)) in have
            if on and not was and project.add_project_reference(other):
                changed.append(f"+{other.name}")
            elif was and not on:
                inc = next((r.include for r in project.ms.project_references
                            if os.path.normcase(str((project.folder / MB.xml_unescape(r.include).replace("\\", "/"))
                                                    .resolve())) == os.path.normcase(str(other.ms.path))), None)
                if inc and project.remove_reference("ProjectReference", inc):
                    changed.append(f"-{other.name}")
        for i in range(alist.count()):
            it = alist.item(i)
            a = it.data(ROLE)
            on = it.checkState() == Qt.CheckState.Checked
            if on and a.lower() not in current and project.add_assembly_reference(a):
                changed.append(f"+{a}")
            elif not on and a.lower() in current:
                inc = next((r.include for r in project.ms.assembly_references
                            if MB.xml_unescape(r.include).split(",")[0].lower() == a.lower()), None)
                if inc and project.remove_reference("Reference", inc):
                    changed.append(f"-{a}")
        for i in range(blist.count()):
            f = Path(blist.item(i).text())
            if project.add_assembly_reference(f.stem, str(f)):
                changed.append(f"+{f.name}")
        if changed:
            _log(win, f"{project.name}: references {' '.join(changed)} ({project.ms.path.name} updated)")
        _refresh(win)
        return changed
    dlg.apply = apply
    if not exec_:
        return dlg
    if dlg.exec():
        return apply()
    return None


def manage_packages(win, project: VsProject):
    win.activate_project(project)
    try:
        from ..features.packages import manage_packages as mp
        dlg = mp(win, project.plugin)
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** NuGet: {e}")
        return None
    try:                                      # re-read the project file when the dialog closes
        if dlg is not None and hasattr(dlg, "finished"):
            dlg.finished.connect(lambda *_: (project.reload(), _refresh(win)))
    except Exception:  # noqa: BLE001
        pass
    return dlg


def project_properties(win, project: VsProject, exec_: bool = True):
    ms = project.ms
    dlg = QDialog(win)
    dlg.setWindowTitle(f"{project.name} Properties")
    lay = QFormLayout(dlg)
    fields = {}
    names = ["AssemblyName", "RootNamespace", "OutputType", "StartupObject"]
    if ms.language == "C++":
        names = ["RootNamespace", "ConfigurationType", "PlatformToolset", "CharacterSet"]
    elif ms.is_sdk:
        names.insert(2, "TargetFramework" if not ms.prop("TargetFrameworks") else "TargetFrameworks")
        names += ["Nullable", "ImplicitUsings", "Version"]
    else:
        names.insert(2, "TargetFrameworkVersion")
    for n in names:
        if n == "OutputType":
            w = QComboBox()
            w.addItems(["Exe", "WinExe", "Library"])
            w.setCurrentText(ms.prop(n) or "Library")
        else:
            w = QLineEdit(ms.prop(n))
        fields[n] = w
        lay.addRow(n + ":", w)
    lay.addRow("Project file:", QLabel(str(ms.path)))
    lay.addRow("Style:", QLabel("SDK-style (" + ms.sdk + ")" if ms.is_sdk else "legacy (non-SDK)"))
    lay.addRow("Configurations:", QLabel(", ".join(ms.configuration_names()) + "  |  " +
                                         ", ".join(ms.platform_names())))
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addRow(box)
    dlg.fields = fields

    def apply():
        changed = []
        for n, w in fields.items():
            val = w.currentText() if isinstance(w, QComboBox) else w.text().strip()
            cur = ms.prop(n) or (ms.output_type if n == "OutputType" else "")
            if val == cur or (not val and not cur):
                continue
            if ms.set_property(n, val):
                changed.append(n)
            elif ms.language == "C++":
                _log(win, f"*** {n} is per configuration in {ms.path.name}: edit the project file")
        if changed:
            ms.save()
            project.reload()
            _log(win, f"{project.name}: {', '.join(changed)} changed in {ms.path.name}")
            _refresh(win)
        return changed
    dlg.apply = apply
    if not exec_:
        return dlg
    if dlg.exec():
        return apply()
    return None


def solution_properties(win, sln: VsSolution) -> None:
    lines = [f"Solution: {sln.file}", f"Configuration: {sln.configuration} | {sln.platform}",
             f"StartUp Project: {sln.startup}", ""]
    for p in sln.all_projects():
        c, pl = sln.project_config(p)
        lines.append(f"{sln.name_of(p)}: {LANG_NAME.get(p.ms.language)} {p.ms.output_type} -> {c}|{pl}")
    _info(win, f"Solution '{sln.name}'", "\n".join(lines))


DOTNET_TEMPLATES = [("Console App", "console"), ("Class Library", "classlib"), ("Windows Forms App", "winforms"),
                    ("Windows Forms Class Library", "winformslib"), ("WPF Application", "wpf"),
                    ("xUnit Test Project", "xunit")]


def new_project_dialog(win, sln: VsSolution, exec_: bool = True, values: dict | None = None):
    """Add > New Project: dotnet new <template> -lang <C#|VB|F#>, then add it to the .sln."""
    dlg = QDialog(win)
    dlg.setWindowTitle("Add a new project")
    lay = QFormLayout(dlg)
    tmpl = QComboBox()
    for t, short in DOTNET_TEMPLATES:
        tmpl.addItem(t, short)
    lang = QComboBox()
    lang.addItems(["C#", "VB", "F#"])
    name = QLineEdit("NewProject")
    lay.addRow("Template:", tmpl)
    lay.addRow("Language:", lang)
    lay.addRow("Name:", name)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addRow(box)
    if values:
        tmpl.setCurrentIndex(max(0, tmpl.findData(values.get("template", "console"))))
        lang.setCurrentText(values.get("language", "C#"))
        name.setText(values.get("name", "NewProject"))
    if exec_ and not dlg.exec():
        return None
    return create_project(win, sln, tmpl.currentData(), lang.currentText(), name.text().strip())


def create_project(win, sln: VsSolution, template: str, language: str, name: str):
    dn = MB.find_dotnet()
    if not dn or not name:
        _info(win, "New Project", "The .NET SDK (dotnet) was not found.")
        return None
    out = sln.folder / name
    r = subprocess.run([dn, "new", template, "-lang", language, "-n", name, "-o", str(out)], capture_output=True,
                       text=True, cwd=str(sln.folder), creationflags=NO_WINDOW, timeout=300,
                       env={**os.environ, "DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"})
    _log(win, (r.stdout or "") + (r.stderr or ""))
    pf = next((p for p in out.glob(f"{name}.*proj")), None) if out.exists() else None
    if r.returncode != 0 or pf is None:
        _log(win, f"*** dotnet new {template} failed")
        return None
    return add_project_file(win, sln, pf)


def add_existing_project_dialog(win, sln: VsSolution):
    f, _ = QFileDialog.getOpenFileName(win, "Add Existing Project", str(sln.folder),
                                       "Project files (*.csproj *.vbproj *.fsproj *.vcxproj)")
    return add_project_file(win, sln, Path(f)) if f else None


def add_project_file(win, sln: VsSolution, pf: Path):
    from .vs_solution import MSBuildProject, VsProject as VP, _add
    entry = sln.model.add_project(pf)
    sln.model.save()
    vp = VP(MSBuildProject.load(pf), sln, entry.name)
    vp.sln_entry = entry
    _add(sln, vp)
    win._state_for(vp)
    _refresh(win)
    _log(win, f"Added project {entry.name} to {sln.file.name}")
    return vp


def remove_project(win, sln: VsSolution, project: VsProject, confirm: bool = True) -> bool:
    if confirm and not OFFSCREEN and QMessageBox.question(
            win, "Remove", f"Remove '{project.name}' from the solution? (its files stay on disk)") != \
            QMessageBox.StandardButton.Yes:
        return False
    entry = getattr(project, "sln_entry", None)
    if entry is None or not sln.model.remove_project(entry.guid):
        return False
    sln.model.save()
    from ..solution import Solution
    Solution.remove_project(sln, sln.name_of(project))
    win._forget_project(project)
    _refresh(win)
    _log(win, f"Removed {project.name} from {sln.file.name}")
    return True


# ====================================================================== build
def _steps_for(project: VsProject, cfg: str, plat: str, verb: str = "build") -> tuple[list, str]:
    """Build steps for one project + a note (why a fallback is used)."""
    from ._others_base import Step
    ms = project.ms
    env = {"DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
    if MB.uses_dotnet_cli(ms):
        argv = MB.build_argv(ms.path, cfg, plat, sdk=True, verb=verb, project=ms)
        if argv is None:
            return [], "the .NET SDK (dotnet) was not found: winget install Microsoft.DotNet.SDK.9"
        return [Step(argv, ms.folder, env, " ".join(Path(argv[0]).stem if i == 0 else a for i, a in enumerate(argv)))], ""
    msb = MB.find_msbuild()
    if ms.language == "C++":
        if msb and MB.msbuild_is_full(msb) and MB.has_vc_tools():
            argv = MB.build_argv(ms.path, cfg, plat, sdk=False, verb=verb, project=ms)
            argv = [a for a in argv if a != "-restore"]
            return [Step(argv, ms.folder, {}, f"MSBuild {ms.path.name} ({cfg}|{MB.project_platform(plat, ms)})")], ""
        gpp = MB.find_mingw_gpp()
        if gpp and verb != "clean":
            exe = _mingw_exe(project, cfg)
            exe.parent.mkdir(parents=True, exist_ok=True)
            srcs = [str(project.folder / f.rel) for f in ms.files() if f.kind == "ClCompile"]
            flags = (["-g", "-O0"] if cfg.lower() == "debug" else ["-O2"]) + ["-static-libgcc", "-static-libstdc++"]
            return [Step([gpp, *flags, "-o", str(exe), *srcs], ms.folder, {"PATH": str(Path(gpp).parent) + os.pathsep +
                                                                         os.environ.get("PATH", "")},
                         f"g++ (MinGW) -> {exe.name}")], \
                "Visual C++ build tools were not found: the sources are compiled with MinGW g++ (fallback)"
        return [], ("cannot build a .vcxproj: install Visual Studio Build Tools with the C++ workload (MSBuild + "
                    "cl) or MinGW-w64 (g++)")
    if msb:
        argv = MB.build_argv(ms.path, cfg, plat, sdk=False, verb=verb, project=ms)
        if not MB.msbuild_is_full(msb):
            argv = [a for a in argv if a != "-restore"]
        return [Step(argv, ms.folder, env, f"MSBuild {ms.path.name} ({cfg}|{MB.project_platform(plat, ms)})")], \
            "" if MB.msbuild_is_full(msb) else "using the .NET Framework 4 MSBuild (install VS Build Tools for full support)"
    return [], ("this is a .NET Framework project: it needs MSBuild from Visual Studio / Build Tools "
                "(winget install Microsoft.VisualStudio.2022.BuildTools)")


def _mingw_exe(project: VsProject, cfg: str) -> Path:
    return project.state / "mingw" / cfg / (project.ms.prop("TargetName") or project.ms.name + ".exe")


def solution_steps(sln: VsSolution, verb: str = "build", only=None) -> tuple[list, list[str]]:
    """Steps that build the whole solution (one dotnet/MSBuild call on the .sln when possible)."""
    from ._others_base import Step
    notes: list[str] = []
    projects = sln.all_projects()
    if only:
        names = {n.lower() for n in only}
        projects = [p for p in projects if sln.name_of(p).lower() in names]
    elif sln.model is not None and sln.file is not None:
        all_sdk = all(MB.uses_dotnet_cli(p.ms) for p in projects)
        msb = MB.find_msbuild()
        env = {"DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
        if all_sdk and MB.find_dotnet():
            argv = MB.build_argv(sln.file, sln.configuration, sln.platform, sdk=True, verb=verb)
            return [Step(argv, sln.folder, env, f"dotnet {verb} {sln.file.name} ({sln.configuration}|{sln.platform})")], []
        cpp = any(p.ms.language == "C++" for p in projects)
        if msb and MB.msbuild_is_full(msb) and (not cpp or MB.has_vc_tools()):
            argv = MB.build_argv(sln.file, sln.configuration, sln.platform, sdk=False, verb=verb)
            return [Step(argv, sln.folder, env, f"MSBuild {sln.file.name} ({sln.configuration}|{sln.platform})")], []
        notes.append("no tool builds the whole solution at once: building project by project")
    steps = []
    for p in projects:
        cfg, plat = sln.project_config(p)
        st, note = _steps_for(p, cfg, plat, verb)
        if note:
            notes.append(f"{sln.name_of(p)}: {note}")
        steps += st
    return steps, notes


def build(win, sln: VsSolution | None, only=None, wait: bool = False, verb: str = "build"):
    """Build / Rebuild / Clean the solution (or *only* some projects) with the native toolchain.
    Output goes to the Output window. *wait*: run here and return {target: exit code}."""
    if sln is None:
        sln = win.sln
    win.save_all()
    steps, notes = solution_steps(sln, verb, only)
    for n in notes:
        _log(win, f"*** {n}")
    title = f"{verb.capitalize()} {'solution' if not only else 'project'} '{sln.name if not only else ', '.join(only)}'"
    if not steps:
        _log(win, f"========== {title}: nothing to do ==========")
        return {} if wait else None
    if wait:
        results = {}
        for s in steps:
            _log(win, f"> {s.title}")
            try:
                r = subprocess.run([str(a) for a in s.argv], cwd=str(s.cwd), capture_output=True,
                                   creationflags=NO_WINDOW, timeout=1200, env={**os.environ, **s.env})
                text = (r.stdout + r.stderr).decode("utf-8", errors="replace")
                if text.strip():
                    _log(win, text.rstrip())
                results[s.title] = r.returncode
            except (OSError, subprocess.TimeoutExpired) as e:
                _log(win, f"*** {e}")
                results[s.title] = -1
        ok = sum(1 for c in results.values() if c == 0)
        _log(win, f"========== {title}: {ok} succeeded, {len(results) - ok} failed ==========")
        return results
    from ._others_base import ChainSession
    s = ChainSession(list(steps), None, win)
    s.output.connect(lambda t: win._append_output(t) if hasattr(win, "_append_output") else _log(win, t))
    s.failed.connect(lambda e: _log(win, f"*** {e}"))
    s.finished.connect(lambda c: _log(win, f"========== {title}: {'succeeded' if c == 0 else 'FAILED'} =========="))
    win._vs_build = s
    try:
        win.dock_output.show()
        win.dock_output.raise_()
    except Exception:  # noqa: BLE001
        pass
    _log(win, f"------ {title}: {sln.configuration}|{sln.platform} ------")
    s.start()
    return s


# ====================================================================== run / debug
def _register_netcoredbg():
    from .. import dap
    if "netcoredbg" in dap.ADAPTERS:
        return
    from ..bridgedebug import find_netcoredbg
    dap.ADAPTERS["netcoredbg"] = (
        lambda: [find_netcoredbg(), "--interpreter=vscode"] if find_netcoredbg() else None,
        lambda prog, args, cwd, env: {"name": ".NET Launch", "type": "coreclr", "request": "launch",
                                      "program": prog, "args": args, "cwd": cwd, "env": env,
                                      "stopAtEntry": False, "console": "internalConsole", "justMyCode": True})


def all_breakpoints(win) -> list[tuple[str, int, str]]:
    """Breakpoints of every open project of the solution, as absolute paths (1-based lines)."""
    try:
        win._sync_breakpoints()
    except Exception:  # noqa: BLE001
        pass
    conds = getattr(win, "bp_conditions", {})
    out = []
    for st in win.project_states():
        proj = st["project"]
        bps = dict(st.get("breakpoints") or {})
        for mod, mv in st.get("modviews", {}).items():
            try:
                bps[mod] = set(mv.editor.breakpoints())
            except Exception:  # noqa: BLE001
                pass
        for form, cv in st.get("codeviews", {}).items():
            code = getattr(proj, "form_code", {}).get(form)
            if code:
                try:
                    bps[code] = set(cv.editor.breakpoints())
                except Exception:  # noqa: BLE001
                    pass
        for f, lines in bps.items():
            p = Path(f) if Path(f).is_absolute() else Path(proj.folder) / f
            for ln in lines:
                out.append((str(p.resolve()), int(ln) + 1, conds.get((f, ln), "")))
    return out


def _netcoredbg_session(win, project: VsProject, cfg: str, plat: str):
    from ..dap import DapSession
    _register_netcoredbg()
    props = MB.get_properties(project.ms, ["TargetPath", "RunWorkingDirectory"], cfg, plat)
    target = props.get("TargetPath") or str(MB.guess_target_path(project.ms, cfg, plat))
    cwd = props.get("RunWorkingDirectory") or str(Path(target).parent)

    class NetDap(DapSession):
        def set_breakpoint(self, filename, line, on, cond=""):
            if not os.path.isabs(filename) and win.project is not None:
                filename = str(Path(win.project.folder) / filename)
            return DapSession.set_breakpoint(self, filename, line, on, cond)

    s = NetDap("netcoredbg", target, [], Path(project.folder), {}, all_breakpoints(win), win)
    s.launch_args["cwd"] = cwd
    s.break_on_exception = False
    return s


def _gdb_session(win, project: VsProject, exe: Path):
    """gdb -i dap (MinGW) for a .vcxproj built by the MinGW fallback; breakpoints as absolute paths."""
    from ..dap import DapSession
    from ._others_base import find_gdb
    gdb = find_gdb()
    from ..bridgedebug import gdb_env               # WinLibs gdb: PYTHONHOME for its embedded Python (-i dap)

    class GdbDap(DapSession):                     # MinGW debug info uses C:/forward/slashes
        def set_breakpoint(self, filename, line, on, cond=""):
            if not os.path.isabs(filename) and win.project is not None:
                filename = str(Path(win.project.folder) / filename)
            path = Path(filename).resolve().as_posix()
            lines = self.breakpoints.setdefault(path, set())
            (lines.add if on else lines.discard)(line)
            self._request("setBreakpoints", {"source": {"path": path}, "breakpoints": self._bp_list(path, lines)})

    s = GdbDap("gdb", str(exe), [], Path(project.folder), gdb_env(gdb) or None, all_breakpoints(win), win)
    s.breakpoints = {Path(k).as_posix(): v for k, v in s.breakpoints.items()}
    s.conditions = {(Path(k).as_posix(), n): c for (k, n), c in s.conditions.items()}
    s.argv = [gdb, "-i", "dap"]
    s.launch_args["cwd"] = str(exe.parent)
    s.break_on_exception = False
    return s


def run_session(win, project: VsProject, debug: bool, sln: VsSolution | None):
    from ._others_base import ChainSession, Step
    cfg, plat = sln.project_config(project) if sln is not None else ("Debug", "Any CPU")
    pre, note = _steps_for(project, cfg, plat, "build")
    if note:
        _log(win, f"*** {project.name}: {note}")
    if not pre and note and "fallback" not in note:
        return ChainSession([Step(["cmd.exe", "/c", "exit", "1"], project.folder, {}, "build tool missing")], None, win)
    ms = project.ms
    if debug:
        from ..bridgedebug import find_netcoredbg
        if MB.uses_dotnet_cli(ms) and find_netcoredbg():
            return ChainSession(pre, lambda: _netcoredbg_session(win, project, cfg, plat), win)
        if ms.language == "C++" and pre and "g++" in pre[0].title:
            from ._others_base import find_gdb
            if find_gdb():
                exe = _mingw_exe(project, cfg)
                return ChainSession(pre, lambda: _gdb_session(win, project, exe), win)
        why = ("netcoredbg was not found (%LOCALAPPDATA%\\RADIDE\\tools\\netcoredbg)" if MB.uses_dotnet_cli(ms) else
               ".NET Framework / MSVC programs need Visual Studio's debugger (right-click the solution > "
               "Open in Visual Studio)")
        _log(win, f"{project.name}: running without breakpoints - {why}")
    if MB.uses_dotnet_cli(ms):
        dn = MB.find_dotnet()
        argv = [dn, "run", "--no-build", "--project", str(ms.path), "-c", cfg]
        pp = MB.project_platform(plat, ms)
        if pp and pp != "AnyCPU":
            argv.append(f"-p:Platform={pp}")
        run = Step(argv, ms.folder, {"DOTNET_NOLOGO": "1"}, "")
    else:
        if pre and "g++" in pre[0].title:
            exe = _mingw_exe(project, cfg)
        else:
            props = MB.get_properties(ms, ["TargetPath"], cfg, plat)
            exe = Path(props.get("TargetPath") or MB.guess_target_path(ms, cfg, plat))
        run = Step([str(exe)], exe.parent, {}, "")
    return ChainSession(pre + [run], None, win)


# ====================================================================== configuration combos
EDITOR_LANGS = {".vb": "vb", ".fs": "fsharp", ".fsx": "fsharp", ".fsi": "fsharp", ".csproj": "xml",
                ".vbproj": "xml", ".fsproj": "xml", ".vcxproj": "xml", ".filters": "xml", ".props": "xml",
                ".targets": "xml", ".resx": "xml", ".config": "xml", ".slnx": "xml", ".xaml": "xml",
                ".settings": "xml", ".manifest": "xml", ".natvis": "xml", ".cxx": "cpp", ".hxx": "cpp", ".rc": "cpp"}


def install(win) -> None:
    try:                                          # Monaco language ids of Visual Studio file types
        from ..monaco_editor import MONACO_LANG
        for k, v in EDITOR_LANGS.items():
            MONACO_LANG.setdefault(k, v)
    except Exception:  # noqa: BLE001 - the built-in editor is used
        pass
    tb = QToolBar("Solution Configurations", win)
    tb.setObjectName("vsSolutionConfigurations")
    cfg = QComboBox()
    cfg.setToolTip("Solution Configurations")
    cfg.setMinimumContentsLength(8)
    plat = QComboBox()
    plat.setToolTip("Solution Platforms")
    plat.setMinimumContentsLength(8)
    tb.addWidget(QLabel(" "))
    tb.addWidget(cfg)
    tb.addWidget(plat)
    win.addToolBar(tb)
    tb.setVisible(False)
    win.vs_config_toolbar, win.vs_config_combo, win.vs_platform_combo = tb, cfg, plat
    cfg.activated.connect(lambda _i: set_configuration(win, cfg.currentText(), None))
    plat.activated.connect(lambda _i: set_configuration(win, None, plat.currentText()))
    try:
        m = win.solution.model()
        m.modelReset.connect(lambda: QTimer.singleShot(0, lambda: refresh_config_ui(win)))
        m.rowsInserted.connect(lambda *_: QTimer.singleShot(0, lambda: refresh_config_ui(win)))
    except Exception:  # noqa: BLE001
        pass
    QTimer.singleShot(0, lambda: _extend_build_menu(win))


def _extend_build_menu(win) -> None:
    menu = getattr(win, "build_menu", None)
    if menu is None or getattr(win, "_vs_build_actions", None):
        return
    acts = []
    menu.addSeparator()
    for text, verb in (("Rebuild Solution", "rebuild"), ("Clean Solution", "clean")):
        a = menu.addAction(text, lambda v=verb: isinstance(win.sln, VsSolution) and build(win, win.sln, verb=v))
        acts.append(a)
    win._vs_build_actions = acts
    for a in acts:
        a.setVisible(isinstance(win.sln, VsSolution))


def refresh_config_ui(win) -> None:
    try:
        _refresh_config_ui(win)
    except RuntimeError:                  # the window is being destroyed
        pass


def _refresh_config_ui(win) -> None:
    tb = getattr(win, "vs_config_toolbar", None)
    if tb is None:
        return
    sln = win.sln if isinstance(win.sln, VsSolution) else None
    for a in getattr(win, "_vs_build_actions", []) or []:
        a.setVisible(sln is not None)
    if sln is None:
        tb.setVisible(False)
        return
    for combo, values, cur in ((win.vs_config_combo, sln.configurations(), sln.configuration),
                               (win.vs_platform_combo, sln.platforms(), sln.platform)):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(values)
        combo.setCurrentText(cur)
        combo.blockSignals(False)
    tb.setVisible(True)


def set_configuration(win, configuration: str | None, platform: str | None) -> None:
    sln = win.sln if isinstance(win.sln, VsSolution) else None
    if sln is None:
        return
    if configuration:
        sln.configuration = configuration
    if platform:
        sln.platform = platform
    sln.save()
    refresh_config_ui(win)
    _log(win, f"Active configuration: {sln.configuration}|{sln.platform}")


__all__ = ["open_in_window", "fill_project", "after_fill", "activate", "editor_for_file", "solution_menu",
           "project_menu", "add_new_item_dialog", "do_add_new_item", "add_reference_dialog", "manage_packages",
           "project_properties", "build", "run_session", "install", "refresh_config_ui", "set_configuration",
           "new_project_dialog", "create_project", "add_project_file", "remove_project", "new_folder"]
