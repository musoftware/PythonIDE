"""Visual Studio 2022 solutions (docs/DOTNET.md, "Solutions"): merging projects and solutions, solution
folders and items, Unload / Reload Project, Project Dependencies and Build Order, multiple startup
projects, Configuration Manager, .slnx read/write, the Project Properties document, launch profiles,
User Secrets, strong name keys and publish profiles.

* model.py      SolutionDoc - .sln / .slnx parse, edit, write (no Qt)
* msprops.py    MSBuild property edits (per configuration), usings, build events, Directory.Build.*
* launch.py     launchSettings.json profiles; secrets.py User Secrets; signing.py .snk; publish.py .pubxml
* ops.py        operations on the open solution (save + re-sync the IDE)
* dialogs.py    Configuration Manager, Project Dependencies, Solution Property Pages, Add New Project,
                Add Projects from Solution, New Solution from Folders, Publish
* properties.py the Project Properties document and the Launch Profiles window
* run.py        F5 / Ctrl+F5: launch profiles and multiple startup projects

``install(win)`` (called by radide/foreign/vs_ui.install) hooks the existing Visual Studio support
without restructuring it: Solution Explorer menus, tree decorations, drag & drop, run sessions.
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QAbstractItemView, QFileDialog, QInputDialog, QMenu, QMessageBox, QTreeWidgetItem

ROLE = Qt.ItemDataRole.UserRole
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
_INSTALLED = {"done": False}


def _log(win, text):
    from .ops import _log as log
    log(win, text)


def _vs(win):
    from . import ops
    return win.sln if ops.is_vs(getattr(win, "sln", None)) else None


def _guard(win, title, fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except (OSError, ValueError, KeyError) as e:
        _log(win, f"*** {title}: {e}")
        if not OFFSCREEN:
            QMessageBox.warning(win, title, str(e))
        return None


# ====================================================================== module-level hooks (once)
def _install_hooks() -> None:
    if _INSTALLED["done"]:
        return
    _INSTALLED["done"] = True
    from ...features import solution_ui
    from ...foreign import vs_ui
    from . import ops, run

    orig_run = vs_ui.run_session
    if not getattr(orig_run, "_radide_sln_wrapped", False):
        vs_ui.run_session = run.wrapped_run_session(orig_run)

    orig_load = vs_ui.load_vs

    def load_vs(path):
        sln = orig_load(path)
        try:
            gone = ops.apply_unloaded(sln)
            if gone and sln.startup and sln.project(sln.startup) is None:
                pass
        except Exception:  # noqa: BLE001
            pass
        return sln
    vs_ui.load_vs = load_vs

    orig_sol_menu = vs_ui.solution_menu
    vs_ui.solution_menu = lambda win, sln, item: _solution_menu(win, sln, item, orig_sol_menu(win, sln, item))
    orig_proj_menu = vs_ui.project_menu

    def project_menu(win, project, item, kind, name):
        m = orig_proj_menu(win, project, item, kind, name)
        if m is not None and kind == "project":
            _project_menu(win, project, item, name, m)
        return m
    vs_ui.project_menu = project_menu

    orig_build_menu = solution_ui.build_menu

    def build_menu(win, item):
        m = _special_menu(win, item)
        return m if m is not None else orig_build_menu(win, item)
    solution_ui.build_menu = build_menu

    orig_build = vs_ui.build

    def build(win, sln, only=None, wait=False, verb="build"):
        if sln is None:
            sln = win.sln
        if only is None and sln is not None and ops.unloaded_files(sln):
            only = [sln.name_of(p) for p in sln.all_projects()]
            _log(win, "(unloaded projects are not built)")
        return orig_build(win, sln, only=only, wait=wait, verb=verb)
    vs_ui.build = build

    orig_props = vs_ui.project_properties

    def project_properties(win, project, exec_=True):
        if exec_ and getattr(project, "ms", None) is not None and project.ms.language != "C++":
            from .properties import open_project_properties
            return open_project_properties(win, project)
        return orig_props(win, project, exec_)
    vs_ui.project_properties = project_properties

    def solution_properties(win, sln):
        from .dialogs import solution_property_pages
        return solution_property_pages(win, sln)
    vs_ui.solution_properties = solution_properties

    orig_refresh = vs_ui.refresh_config_ui

    def refresh_config_ui(win):
        orig_refresh(win)
        run.refresh_profile_combo(win)
        acts = getattr(win, "_sln_build_actions", None) or []
        for a in acts:
            try:
                a.setVisible(_vs(win) is not None)
            except RuntimeError:
                pass
    vs_ui.refresh_config_ui = refresh_config_ui

    solution_ui.TREE_HOOKS.append(decorate_tree)
    _patch_provider()


def _patch_provider() -> None:
    """Project menu (dynamic, radide/project_actions_providers/dotnet.py VisualStudio): solution commands."""
    try:
        from ...project_actions import Action, Separator
        from ...project_actions_providers.dotnet import VisualStudio
    except Exception:  # noqa: BLE001
        return
    orig = VisualStudio.actions
    if getattr(orig, "_radide_sln", False):
        return

    def actions(self, ctx):
        out = list(orig(self, ctx))
        win = ctx.win
        sln = _vs(win)
        if sln is None:
            return out
        from . import dialogs, ops
        has = ops.has_file(sln)
        out += [Separator(),
                Action("cfg-manager", "Configuration Manager...", lambda c: dialogs.configuration_manager(c.win, sln),
                       opens="none", enabled=lambda c: has),
                Action("project-deps", "Project Dependencies...",
                       lambda c: dialogs.project_dependencies(c.win, sln, getattr(c.project, "name", "")),
                       opens="none", enabled=lambda c: has),
                Action("build-order", "Project Build Order...",
                       lambda c: dialogs.project_dependencies(c.win, sln, getattr(c.project, "name", ""), tab=1),
                       opens="none", enabled=lambda c: has),
                Action("startup-projects", "Configure Startup Projects...",
                       lambda c: dialogs.solution_property_pages(c.win, sln), opens="none"),
                Action("publish-profile", "Publish...", lambda c: dialogs.publish_dialog(c.win, c.project),
                       opens="none", enabled=lambda c: getattr(c.project, "ms", None) is not None)]
        return out
    actions._radide_sln = True
    VisualStudio.actions = actions


# ====================================================================== per window
def install(win) -> None:
    _install_hooks()
    from . import run
    run.install_combo(win)
    _install_dnd(win)
    _extend_menus(win)


def _extend_menus(win) -> None:
    from PyQt6.QtCore import QTimer

    def later():
        acts = []
        bm = getattr(win, "build_menu", None)
        if bm is not None and not getattr(win, "_sln_build_actions", None):
            bm.addSeparator()
            a = bm.addAction("Configuration Manager...", lambda: _vs(win) and _guard(
                win, "Configuration Manager", _cfg_manager, win))
            acts.append(a)
            a = bm.addAction("Publish Selection...", lambda: _vs(win) and win.project is not None and
                             getattr(win.project, "ms", None) is not None and _publish(win, win.project))
            acts.append(a)
            win._sln_build_actions = acts
            for x in acts:
                x.setVisible(_vs(win) is not None)
        fm = getattr(win, "file_menu", None)
        if fm is not None and not getattr(win, "_sln_file_action", None):
            before = getattr(win, "recent_menu", None)
            a = fm.addAction("New Solution from Existing Folders...", lambda: _new_from_folders(win))
            if before is not None:
                fm.removeAction(a)
                fm.insertAction(before.menuAction(), a)
            win._sln_file_action = a
    QTimer.singleShot(0, later)


def _cfg_manager(win):
    from .dialogs import configuration_manager
    return configuration_manager(win, _vs(win))


def _publish(win, project):
    from .dialogs import publish_dialog
    return publish_dialog(win, project)


def _new_from_folders(win):
    from .dialogs import new_solution_from_folders
    return new_solution_from_folders(win)


# ====================================================================== Solution Explorer: decorations
def _walk(root):
    stack = [root]
    while stack:
        it = stack.pop()
        yield it
        stack.extend(it.child(i) for i in range(it.childCount()))


def decorate_tree(win, root) -> None:
    sln = _vs(win)
    if sln is None:
        return
    from . import ops, run
    unloaded = ops.unloaded_files(sln)
    model = sln.model
    # unloaded projects: greyed "(unloaded)" nodes
    if unloaded and model is not None:
        by_name = {e.name.lower(): e for e in model.projects()}
        for it in _walk(root):
            data = it.data(0, ROLE) or ("",)
            if data[0] != "missing":
                continue
            e = by_name.get(str(data[1]).lower())
            if e is not None and ops.rel_key(sln, model.folder / e.path) in unloaded:
                it.setText(0, f"{data[1]} (unloaded)")
                it.setData(0, ROLE, ("vs_unloaded", data[1]))
                it.setForeground(0, Qt.GlobalColor.gray)
                it.setIcon(0, win.style().standardIcon(win.style().StandardPixmap.SP_DirClosedIcon))
                it.setToolTip(0, f"{model.folder / e.path}\nThe project is unloaded: right-click > Reload Project")
        _nest_missing(win, sln, root)
    # multiple startup projects: bold, like VS
    try:
        plan = run.startup_plan(sln)
    except Exception:  # noqa: BLE001
        plan = []
    if plan:
        names = {sln.name_of(p).lower() for p, _a in plan}
        bold = QFont()
        bold.setBold(True)
        for it in _walk(root):
            data = it.data(0, ROLE) or ("",)
            if data[0] == "project":
                f = it.font(0)
                f.setBold(str(data[1]).lower() in names)
                it.setFont(0, f)
    if ops.has_file(sln):
        _other_projects(win, sln, root)
    _directory_build(win, sln, root)
    n = len(sln.projects)
    loaded = len(sln.all_projects())
    if unloaded or loaded != n:
        root.setText(0, f"Solution '{sln.name}' ({loaded} of {n} project{'s' if n != 1 else ''})")


def _folder_node(root, names):
    if not names:
        return root
    cur = root
    for n in names:
        nxt = None
        for i in range(cur.childCount()):
            ch = cur.child(i)
            d = ch.data(0, ROLE) or ("",)
            if d[0] == "foreign_slnfolder" and ch.text(0) == n:
                nxt = ch
                break
        if nxt is None:
            return None
        cur = nxt
    return cur


def _nest_missing(win, sln, root):
    """Unloaded/missing project nodes go into their solution folder (vs_ui only nests loaded ones)."""
    model = sln.model
    for i in reversed(range(root.childCount())):
        it = root.child(i)
        d = it.data(0, ROLE) or ("",)
        if d[0] not in ("vs_unloaded", "missing"):
            continue
        e = next((x for x in model.projects() if x.name.lower() == str(d[1]).lower()), None)
        path = model.folder_path(e) if e is not None else []
        target = _folder_node(root, path)
        if target is not None and target is not root:
            root.takeChild(i)
            target.addChild(it)


def _other_projects(win, sln, root):
    """Projects of types RAD IDE does not load (.sqlproj, .wapproj, .pyproj, .esproj ...) as nodes."""
    from . import ops
    try:
        doc = ops.doc_of(sln)
    except (OSError, ValueError):
        return
    shown = set()
    for it in _walk(root):
        d = it.data(0, ROLE) or ("", "")
        if isinstance(d, tuple) and len(d) > 1:
            shown.add(os.path.normcase(str(d[1])))
        tip = it.toolTip(0)
        if tip:
            shown.add(os.path.normcase(tip.split("\n")[0]))
    from ...foreign.vs_solution import PROJECT_EXTS
    for e in doc.real_projects():
        if e.ext in PROJECT_EXTS or e.ext in (".shproj", ".projitems", ".vcxitems"):
            continue
        pf = str((doc.folder / e.path).resolve())
        if os.path.normcase(pf) in shown:
            continue
        holder = _folder_node(root, doc.folder_path(e)) or root
        it = QTreeWidgetItem([f"{e.name} ({e.ext[1:]})"])
        it.setData(0, ROLE, ("vs_otherproj", pf))
        it.setToolTip(0, f"{pf}\nThis project type is built by MSBuild / Visual Studio; RAD IDE shows it only")
        it.setIcon(0, win.style().standardIcon(win.style().StandardPixmap.SP_FileDialogDetailedView))
        if not Path(pf).exists():
            it.setForeground(0, Qt.GlobalColor.gray)
        holder.addChild(it)


def _directory_build(win, sln, root):
    """Directory.Build.props / .targets / Directory.Packages.props that MSBuild imports for the
    solution's projects, shown at the top (italic) unless they are already solution items."""
    from .msprops import directory_build_files
    items = set()
    for it in _walk(root):
        d = it.data(0, ROLE) or ("",)
        if d[0] == "foreign_file":
            items.add(os.path.normcase(str(d[1])))
    found = []
    for p in directory_build_files(Path(sln.folder)):
        found.append(p)
    for proj in sln.all_projects():
        for p in directory_build_files(proj.folder, Path(sln.folder)):
            if p not in found:
                found.append(p)
    italic = QFont()
    italic.setItalic(True)
    pos = 0
    for p in found:
        if os.path.normcase(str(p.resolve())) in items:
            continue
        it = QTreeWidgetItem([p.name if p.parent == Path(sln.folder) else f"{p.name} ({p.parent.name})"])
        it.setData(0, ROLE, ("vs_dirbuild", str(p.resolve())))
        it.setFont(0, italic)
        it.setIcon(0, win.style().standardIcon(win.style().StandardPixmap.SP_FileIcon))
        it.setToolTip(0, f"{p}\nImported by MSBuild into every project below {p.parent} "
                         f"(right-click > Add to Solution Items)")
        root.insertChild(pos, it)
        pos += 1


# ====================================================================== Solution Explorer: menus
def _act(menu, text):
    for a in menu.actions():
        if a.text().replace("&", "") == text:
            return a
        if a.menu() is not None:
            hit = _act(a.menu(), text)
            if hit is not None:
                return hit
    return None


def _retarget(menu, text, fn) -> None:
    a = _act(menu, text)
    if a is not None:
        try:
            a.triggered.disconnect()
        except TypeError:
            pass
        a.triggered.connect(lambda *_: fn())


def _solution_menu(win, sln, item, m):
    from . import dialogs, ops
    has = ops.has_file(sln)
    first = m.actions()[0] if m.actions() else None
    if has:
        add = None
        for a in m.actions():
            if a.menu() is not None and a.text().replace("&", "") == "Add":
                add = a.menu()
        if add is not None:
            _retarget(add, "New Project...", lambda: dialogs.add_new_project(win, sln))
            _retarget(add, "Existing Project...", lambda: add_existing_project_dialog(win, sln))
            add.addAction("Existing Solution's Projects...", lambda: dialogs.import_solution(win, sln))
            add.addAction("Existing RAD IDE Project...", lambda: add_rad_project_dialog(win, sln))
            add.addSeparator()
            add.addAction("New Item...", lambda: new_solution_item_dialog(win, sln, ""))
            add.addAction("Existing Item...", lambda: add_solution_items_dialog(win, sln, ""))
            add.addAction("New Solution Folder", lambda: new_folder_dialog(win, sln, ""))
        sub = QMenu("Solution Configuration", m)
        sub.addAction("Configuration Manager...", lambda: dialogs.configuration_manager(win, sln))
        m.insertMenu(first, sub) if first is not None else m.addMenu(sub)
        bd = QMenu("Project Dependencies", m)
        bd.addAction("Project Dependencies...", lambda: dialogs.project_dependencies(win, sln))
        bd.addAction("Project Build Order...", lambda: dialogs.project_dependencies(win, sln, tab=1))
        m.insertMenu(first, bd) if first is not None else m.addMenu(bd)
    a = _act(m, "Set StartUp Project")
    m.insertAction(a.menu().menuAction() if a is not None and a.menu() else None, m.addAction(
        "Configure Startup Projects...", lambda: dialogs.solution_property_pages(win, sln)))
    m.addSeparator()
    if has:
        other = ".slnx" if Path(sln.file).suffix.lower() == ".sln" else ".sln"
        m.addAction(f"Save Solution As {other}...", lambda: save_as_dialog(win, sln, other))
    else:
        m.addAction("Save Solution File (.sln)...", lambda: save_as_dialog(win, sln, ".sln"))
    m.addAction("New Solution from Existing Folders...", lambda: dialogs.new_solution_from_folders(win))
    return m


def _project_menu(win, project, item, name, m):
    from . import dialogs, ops
    sln = _vs(win)
    a_start = _act(m, "Set as StartUp Project")
    if sln is not None:
        extra = QMenu("Build Dependencies", m)
        extra.addAction("Project Dependencies...", lambda: dialogs.project_dependencies(win, sln, name))
        extra.addAction("Project Build Order...", lambda: dialogs.project_dependencies(win, sln, name, tab=1))
        extra.setEnabled(ops.has_file(sln))
        after = a_start
        idx = m.actions().index(after) + 1 if after in m.actions() else len(m.actions())
        before = m.actions()[idx] if idx < len(m.actions()) else None
        m.insertAction(before, m.addAction("Configure Startup Projects...",
                                           lambda: dialogs.solution_property_pages(win, sln)))
        m.insertMenu(before, extra)
    m.addSeparator()
    if project.ms.language != "C++":
        m.addAction("Publish...", lambda: dialogs.publish_dialog(win, project))
        m.addAction("Manage User Secrets", lambda: _secrets(win, project))
        m.addAction("Open debug launch profiles UI", lambda: _launch_ui(win, project))
    if sln is not None and ops.has_file(sln):
        m.addAction("Unload Project", lambda: ops.unload(win, sln, project))
        mv = m.addMenu("Move To Solution Folder")
        _fill_move_menu(win, sln, mv, project_file=project.ms.path)
        _retarget(m, "Remove from Solution", lambda: remove_project_confirm(win, sln, project))


def _secrets(win, project):
    from .properties import ProjectPropertiesDocument
    doc = ProjectPropertiesDocument(win, project)
    p = doc.manage_secrets(open_it=True)
    doc.deleteLater()
    return p


def _launch_ui(win, project):
    from .properties import launch_profiles_dialog
    return launch_profiles_dialog(win, project)


def _fill_move_menu(win, sln, mv, project_file=None, guid: str = ""):
    from . import ops
    try:
        doc = ops.doc_of(sln)
    except (OSError, ValueError):
        mv.setEnabled(False)
        return
    e = doc.by_file(project_file) if project_file else doc.entry(guid)
    if e is None:
        mv.setEnabled(False)
        return
    mv.addAction("(Solution root)", lambda: _guard(win, "Move", ops.move_entry, win, sln, e.guid, ""))
    for f in doc.folders():
        if f.guid == e.guid:
            continue
        label = "/".join(doc.folder_path(f) + [f.name])
        mv.addAction(label, lambda g=f.guid: _guard(win, "Move", ops.move_entry, win, sln, e.guid, g))


def _parent_folder_path(item) -> str:
    p = item.parent() if item is not None else None
    while p is not None:
        d = p.data(0, ROLE) or ("",)
        if d[0] == "foreign_slnfolder":
            return d[1]
        p = p.parent()
    return ""


def _special_menu(win, item):
    """Solution Explorer menus of nodes the VS support did not handle (solution folders, solution
    items, unloaded / other projects, Directory.Build files)."""
    sln = _vs(win)
    if sln is None or item is None:
        return None
    data = item.data(0, ROLE) or ("", "")
    kind, name = data[0], data[1] if len(data) > 1 else ""
    from . import dialogs, ops
    has = ops.has_file(sln)
    m = QMenu(win)
    if kind == "foreign_slnfolder" and has:
        g = ops.folder_guid_by_path(sln, name)
        add = m.addMenu("Add")
        add.addAction("New Project...", lambda: dialogs.add_new_project(win, sln, g))
        add.addAction("Existing Project...", lambda: add_existing_project_dialog(win, sln, g))
        add.addAction("Existing Solution's Projects...", lambda: dialogs.import_solution(win, sln, None, g))
        add.addSeparator()
        add.addAction("New Item...", lambda: new_solution_item_dialog(win, sln, g))
        add.addAction("Existing Item...", lambda: add_solution_items_dialog(win, sln, g))
        add.addAction("New Solution Folder", lambda: new_folder_dialog(win, sln, g))
        names = _projects_in_folder(sln, g)
        a = m.addAction("Build", lambda: _build_only(win, sln, names))
        a.setEnabled(bool(names))
        m.addSeparator()
        mv = m.addMenu("Move To Solution Folder")
        _fill_move_menu(win, sln, mv, guid=g)
        m.addAction("Rename", lambda: rename_folder_dialog(win, sln, g, item.text(0)))
        m.addAction("Remove", lambda: remove_folder_confirm(win, sln, g, item.text(0)))
        return m
    if kind == "vs_unloaded":
        m.addAction("Reload Project", lambda: ops.reload_project(win, sln, name))
        e = next((x for x in sln.model.projects() if x.name.lower() == str(name).lower()), None) if sln.model else None
        if e is not None:
            pf = (sln.model.folder / e.path)
            m.addAction(f"Edit Project File ({pf.name})", lambda: win.open_any_file(pf))
            m.addSeparator()
            m.addAction("Remove from Solution", lambda: _remove_by_file(win, sln, pf))
        return m
    if kind == "missing" and has:
        e = next((x for x in sln.model.projects() if x.name.lower() == str(name).lower()), None) if sln.model else None
        if e is not None:
            pf = (sln.model.folder / e.path)
            m.addAction("Remove from Solution", lambda: _remove_by_file(win, sln, pf))
            return m
    if kind == "vs_otherproj":
        m.addAction(f"Edit Project File ({Path(name).name})", lambda: win.open_any_file(Path(name)))
        m.addAction("Open in Visual Studio", lambda: _open_vs(win, sln))
        if has:
            m.addSeparator()
            m.addAction("Remove from Solution", lambda: _remove_by_file(win, sln, Path(name)))
        return m
    if kind == "vs_dirbuild":
        m.addAction("Open", lambda: win.open_any_file(Path(name)))
        if has:
            m.addAction("Add to Solution Items", lambda: _guard(win, "Solution Items", ops.add_solution_items,
                                                               win, sln, "", [Path(name)]))
        return m
    if kind == "foreign_file" and item.data(0, _project_role()) is None and has:
        folder = _parent_folder_path(item)
        if folder:
            g = ops.folder_guid_by_path(sln, folder)
            rel = os.path.relpath(name, sln.folder).replace("\\", "/")
            m.addAction("Open", lambda: win.open_any_file(Path(name)))
            m.addAction("Open Containing Folder", lambda: _explore(Path(name).parent))
            m.addSeparator()
            m.addAction("Remove", lambda: _guard(win, "Remove", ops.remove_solution_item, win, sln, g, rel))
            return m
    m.deleteLater()
    return None


def _project_role():
    from ...features.solution_ui import PROJECT_ROLE
    return PROJECT_ROLE


def _explore(folder):
    from ...foreign.vs_ui import _explore as ex
    ex(folder)


def _open_vs(win, sln):
    from ...foreign.vs_ui import open_in_visual_studio
    open_in_visual_studio(win, sln.file)


def _projects_in_folder(sln, guid: str) -> list[str]:
    from . import ops
    doc = ops.doc_of(sln)
    out, stack = [], [guid]
    while stack:
        g = stack.pop()
        for c in doc.children(g):
            if c.is_folder:
                stack.append(c.guid)
            else:
                vp = ops.vs_project_by_file(sln, doc.folder / c.path)
                if vp is not None:
                    out.append(sln.name_of(vp))
    return out


def _build_only(win, sln, names):
    from ...foreign import vs_ui
    return vs_ui.build(win, sln, only=names)


def _remove_by_file(win, sln, pf):
    from . import ops
    doc = ops.doc_of(sln)
    e = doc.by_file(pf)
    if e is None:
        return []
    if not OFFSCREEN and QMessageBox.question(win, "Remove", f"'{e.name}' will be removed from the solution "
                                                             "(its files stay on disk).") != \
            QMessageBox.StandardButton.Yes:
        return []
    st = ops.load_state(sln)
    st["unloaded"] = [u for u in st["unloaded"] if u != ops.rel_key(sln, pf)]
    ops.save_state(sln, st)
    return ops.remove_entry(win, sln, e.guid)


def remove_project_confirm(win, sln, project, confirm: bool = True):
    from . import ops
    doc = ops.doc_of(sln)
    e = doc.by_file(project.ms.path)
    if e is None:
        return []
    if confirm and not OFFSCREEN and QMessageBox.question(
            win, "Remove", f"'{e.name}' will be removed from the solution (its files stay on disk).") != \
            QMessageBox.StandardButton.Yes:
        return []
    return ops.remove_entry(win, sln, e.guid)


def remove_folder_confirm(win, sln, guid, name, confirm: bool = True):
    from . import ops
    if confirm and not OFFSCREEN and QMessageBox.question(
            win, "Remove", f"'{name}' and everything in it will be removed from the solution (files stay on "
                           "disk).") != QMessageBox.StandardButton.Yes:
        return []
    return ops.remove_entry(win, sln, guid)


def new_folder_dialog(win, sln, parent_guid: str = "", name: str | None = None):
    from . import ops
    if name is None:
        doc = ops.doc_of(sln)
        i = 1
        while any(f.is_folder and f.parent == parent_guid and f.name == f"NewFolder{i}" for f in doc.projects):
            i += 1
        name, ok = QInputDialog.getText(win, "New Solution Folder", "Name:", text=f"NewFolder{i}")
        if not ok or not name.strip():
            return None
    return _guard(win, "New Solution Folder", ops.add_folder, win, sln, name, parent_guid)


def rename_folder_dialog(win, sln, guid, old, name: str | None = None):
    from . import ops
    if name is None:
        name, ok = QInputDialog.getText(win, "Rename", "Name:", text=old)
        if not ok or not name.strip() or name == old:
            return None
    return _guard(win, "Rename", ops.rename_folder, win, sln, guid, name)


def add_existing_project_dialog(win, sln, folder_guid: str = "", path=None):
    from . import ops
    if path is None:
        path, _ = QFileDialog.getOpenFileName(
            win, "Add Existing Project", str(sln.folder),
            "All Project Files (*.csproj *.vbproj *.fsproj *.vcxproj *.shproj *.sqlproj *.wapproj *.pyproj *.njsproj "
            "*.esproj *.dcproj *.wixproj *.proj);;All files (*)")
        if not path:
            return None
    return _guard(win, "Add Existing Project", ops.add_existing_project, win, sln, Path(path), folder_guid)


def add_rad_project_dialog(win, sln, folder=None):
    from . import ops
    if folder is None:
        f, _ = QFileDialog.getOpenFileName(win, "Add RAD IDE Project", str(sln.folder), "RAD IDE project (project.radproj)")
        if not f:
            return None
        folder = Path(f).parent
    return _guard(win, "Add RAD IDE Project", ops.add_rad_project, win, sln, Path(folder))


def add_solution_items_dialog(win, sln, folder_guid: str = "", files=None):
    from . import ops
    if files is None:
        files, _ = QFileDialog.getOpenFileNames(win, "Add Existing Item", str(sln.folder), "All files (*)")
        if not files:
            return None
    return _guard(win, "Add Existing Item", ops.add_solution_items, win, sln, folder_guid, [Path(f) for f in files])


SOLUTION_ITEM_TEMPLATES = {"Text File": ("TextFile1.txt", ""),
                           "Directory.Build.props": ("Directory.Build.props", "<Project>\n  <PropertyGroup>\n"
                                                     "  </PropertyGroup>\n</Project>\n"),
                           "Directory.Build.targets": ("Directory.Build.targets", "<Project>\n</Project>\n"),
                           "Directory.Packages.props": ("Directory.Packages.props",
                                                        "<Project>\n  <PropertyGroup>\n    <ManagePackageVersionsCentrally>"
                                                        "true</ManagePackageVersionsCentrally>\n  </PropertyGroup>\n"
                                                        "  <ItemGroup>\n  </ItemGroup>\n</Project>\n"),
                           "editorconfig File (.NET)": (".editorconfig", "root = true\n\n[*.cs]\nindent_style = space\n"
                                                        "indent_size = 4\n"),
                           "global.json": ("global.json", '{\n  "sdk": {\n    "rollForward": "latestFeature"\n  }\n}\n'),
                           "NuGet Config": ("nuget.config", '<?xml version="1.0" encoding="utf-8"?>\n<configuration>\n'
                                            '  <packageSources>\n    <add key="nuget.org" '
                                            'value="https://api.nuget.org/v3/index.json" />\n  </packageSources>\n'
                                            '</configuration>\n')}


def new_solution_item_dialog(win, sln, folder_guid: str = "", template: str | None = None):
    from . import ops
    if template is None:
        template, ok = QInputDialog.getItem(win, "Add New Item", "Template:", list(SOLUTION_ITEM_TEMPLATES), 0, False)
        if not ok:
            return None
    name, text = SOLUTION_ITEM_TEMPLATES[template]
    p = _guard(win, "Add New Item", ops.new_solution_item, win, sln, folder_guid, name, text)
    if p is not None:
        try:
            win.open_any_file(p)
        except Exception:  # noqa: BLE001
            pass
    return p


def save_as_dialog(win, sln, ext: str, target=None):
    from . import ops
    if target is None:
        target, _ = QFileDialog.getSaveFileName(win, "Save Solution As", str(Path(sln.folder) / (sln.name + ext)),
                                                "Solution (*.sln);;XML Solution (*.slnx)" if ext == ".sln" else
                                                "XML Solution (*.slnx);;Solution (*.sln)")
        if not target:
            return None
    return _guard(win, "Save Solution As", ops.save_solution_as, win, sln, Path(target))


# ====================================================================== drag & drop between solution folders
class _DropFilter(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def _target(self, ev):
        tree = self.win.solution
        pos = ev.position().toPoint()
        it = tree.itemAt(pos)
        if it is None:
            return None
        d = it.data(0, ROLE) or ("",)
        if d[0] in ("foreign_slnfolder", "solution"):
            return it
        return None

    def _source(self):
        it = self.win.solution.currentItem()
        d = it.data(0, ROLE) if it is not None else None
        return it if d and d[0] in ("project", "foreign_slnfolder", "vs_unloaded", "vs_otherproj") else None

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t not in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop):
            return False
        if ev.source() is not self.win.solution:
            return False                     # files from Explorer etc.: not ours
        sln = _vs(self.win)
        from . import ops
        if sln is None or not ops.has_file(sln):
            ev.ignore()                      # no visual-only moves in other solutions
            return True
        src, target = self._source(), self._target(ev) if t != QEvent.Type.DragEnter else None
        if t == QEvent.Type.DragEnter:
            if src is not None:
                ev.acceptProposedAction()
            else:
                ev.ignore()
            return True
        if src is None or target is None or target is src:
            ev.ignore()
            return True
        if t == QEvent.Type.DragMove:
            ev.acceptProposedAction()
            return True
        ev.acceptProposedAction()
        drop_on(self.win, src, target)
        return True


def drop_on(win, src_item, target_item):
    """Move the project / folder of *src_item* into the solution folder *target_item* (or the root)."""
    from . import ops
    sln = _vs(win)
    doc = ops.doc_of(sln)
    d = src_item.data(0, ROLE)
    if d[0] == "foreign_slnfolder":
        e = doc.folder_by_path([x for x in d[1].split("/") if x])
    elif d[0] == "project":
        p = sln.project(d[1])
        e = doc.by_file(p.ms.path) if p is not None else None
    elif d[0] == "vs_otherproj":
        e = doc.by_file(d[1])
    else:
        e = doc.find(d[1])
    td = target_item.data(0, ROLE)
    g = ops.folder_guid_by_path(sln, td[1]) if td[0] == "foreign_slnfolder" else ""
    if e is None:
        return False
    _guard(win, "Move", ops.move_entry, win, sln, e.guid, g)
    return True


def _install_dnd(win) -> None:
    tree = getattr(win, "solution", None)
    if tree is None or getattr(win, "_sln_dnd", None) is not None:
        return
    if tree.dragDropMode() == QAbstractItemView.DragDropMode.NoDragDrop:
        tree.setDragEnabled(True)
        tree.setAcceptDrops(True)
        tree.viewport().setAcceptDrops(True)
        tree.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        tree.setDefaultDropAction(Qt.DropAction.MoveAction)
    f = _DropFilter(win)
    tree.viewport().installEventFilter(f)
    win._sln_dnd = f
