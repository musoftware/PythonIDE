"""Hooks the references slice into the Visual Studio solution UI (radide/foreign/vs_ui.py).

* the Reference Manager replaces the basic Add Reference dialog (vs_ui.add_reference_dialog delegates here)
* Solution Explorer menus: Add Project / Shared Project / COM / Assembly Reference..., and on a reference
  Open in Object Browser + Properties
* Add > Existing Item... with Add / Add As Link (like VS's split button)
* View > Object Browser (Ctrl+Alt+J)
* the Properties window shows a selected reference's properties (props.py)
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QDialogButtonBox, QFileDialog, QMenu, QPushButton

from . import edits as ED

OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


def add_reference_dialog(win, project, tab=0, exec_: bool = True):
    from .manager import reference_manager
    return reference_manager(win, project, tab, exec_)


# ====================================================================== Solution Explorer > Dependencies
def fill_extra_deps(win, project, deps, key) -> None:
    """What vs_ui._fill_deps does not list: explicit FrameworkReferences, COM references, Shared Projects."""
    from PyQt6.QtWidgets import QTreeWidgetItem

    from ...foreign import vs_ui
    ms = project.ms
    role = Qt.ItemDataRole.UserRole
    coms = ms.explicit("COMReference")
    shared = ED.shared_imports(ms)
    fws = ms.explicit("FrameworkReference")
    if ms.is_sdk:
        fw_group = next((deps.child(i) for i in range(deps.childCount())
                         if (deps.child(i).data(0, role) or ("", ""))[1] == "frameworks"), None)
        if fw_group is not None:
            have = {fw_group.child(i).text(0).lower() for i in range(fw_group.childCount())}
            for it in fws:
                if it.include.lower() not in have:
                    vs_ui._set(QTreeWidgetItem(fw_group, [it.include]), "foreign_dep", f"framework|{it.include}",
                               key, "SP_ComputerIcon", win, "FrameworkReference")
    for title, items, kind, icon in (("COM", coms, "com", "SP_DesktopIcon"),
                                     ("Shared Projects", shared, "shared", "SP_DirLinkIcon")):
        if not items:
            continue
        parent = deps
        if ms.is_sdk:
            parent = vs_ui._set(QTreeWidgetItem(deps, [title]), "foreign_depgroup", kind, key, "SP_DirIcon", win)
        for it in items:
            inc = ED.xml_unescape(it.include if kind == "com" else it)
            text = inc if kind == "com" else Path(inc.replace("\\", "/")).stem
            tip = (f"COM: {{{it.metadata.get('Guid', '')}}} {it.metadata.get('VersionMajor', '')}."
                   f"{it.metadata.get('VersionMinor', '')}" if kind == "com" else inc)
            vs_ui._set(QTreeWidgetItem(parent, [text]), "foreign_dep", f"{kind}|{inc}", key, icon, win, tip)


# ====================================================================== menus
def _find_action(menu: QMenu, text: str):
    for a in menu.actions():
        if a.text().replace("&", "") == text:
            return a
    return None


def _insert_after(menu: QMenu, after_text: str, actions: list[tuple[str, object]]) -> None:
    anchor = _find_action(menu, after_text)
    acts = []
    for text, slot in actions:
        if _find_action(menu, text) is not None:
            continue
        a = QAction(text, menu)
        a.triggered.connect(lambda _c=False, s=slot: s())
        acts.append(a)
    if not acts:
        return
    idx = menu.actions().index(anchor) + 1 if anchor is not None else len(menu.actions())
    before = menu.actions()[idx] if idx < len(menu.actions()) else None
    for a in acts:
        menu.insertAction(before, a) if before is not None else menu.addAction(a)


def _dep_path(win, project, dkind: str, inc: str) -> str:
    from . import catalog as CAT
    item = {"assembly": "Reference", "com": "COMReference", "project": "ProjectReference",
            "framework": "FrameworkReference"}.get(dkind, "")
    md = {}
    for it in project.ms.explicit(item):
        if ED.xml_unescape(it.include).lower() == inc.lower():
            md = it.metadata
    if dkind == "project":
        try:
            from ...foreign.msbuild import MSBuildProject, guess_target_path
            target = (project.folder / inc.replace("\\", "/")).resolve()
            return str(guess_target_path(MSBuildProject.load(target)))
        except Exception:  # noqa: BLE001
            return ""
    if dkind == "package":
        from .object_browser import package_assemblies
        ver = next((it.metadata.get("Version", "") for it in project.ms.explicit("PackageReference")
                    if it.include.lower() == inc.lower()), "")
        dlls = package_assemblies(inc, ver, project.ms.target_frameworks)
        return dlls[0] if dlls else ""
    if dkind == "framework":
        return CAT.resolve_reference_path(project, "FrameworkReference", inc, md)
    if dkind == "com":                               # the interop assembly tlbimp made (after a build)
        obj = project.folder / "obj"
        hit = next(iter(obj.rglob(f"Interop.{inc}.dll")), None) if obj.is_dir() else None
        return str(hit) if hit else ""
    return CAT.resolve_reference_path(project, item, inc, md)


def open_in_object_browser(win, project, dkind: str, inc: str):
    from .object_browser import show_object_browser
    path = _dep_path(win, project, dkind, inc)
    ob = show_object_browser(win)
    if path and Path(path).is_dir():                 # a framework pack: select its node
        for i in range(ob.tree.topLevelItemCount()):
            it = ob.tree.topLevelItem(i)
            d = it.data(0, Qt.ItemDataRole.UserRole) or ()
            if d and os.path.normcase(d[1]) == os.path.normcase(path):
                ob.tree.setCurrentItem(it)
                it.setExpanded(True)
        return ob
    if path:
        ob.select_assembly(path)
    else:
        try:
            win.log(f"[Object Browser] '{inc}' is not resolved yet (build or restore the project first)")
        except Exception:  # noqa: BLE001
            pass
    return ob


def _wrap_project_menu(vs_ui) -> None:
    if getattr(vs_ui.project_menu, "_refs_wrapped", False):
        return
    orig = vs_ui.project_menu

    def project_menu(win, project, item, kind, name):
        m = orig(win, project, item, kind, name)
        try:
            m = _extend(win, project, item, kind, name, m)
        except Exception as e:  # noqa: BLE001 - never lose the menu over an extension
            try:
                win.log(f"[references] menu: {e}")
            except Exception:  # noqa: BLE001
                pass
        return m
    project_menu._refs_wrapped = True
    vs_ui.project_menu = project_menu


def _extend(win, project, item, kind, name, m):
    lang = project.ms.language
    dotnet = lang != "C++"
    if kind == "project" and m is not None:
        add = next((a.menu() for a in m.actions() if a.menu() is not None and a.text().replace("&", "") == "Add"),
                   None)
        if add is not None:
            extra = [("Shared Project Reference...", lambda: add_reference_dialog(win, project, "shared"))]
            if dotnet:
                extra.append(("COM Reference...", lambda: add_reference_dialog(win, project, "com")))
            _insert_after(add, "Project Reference...", extra)
        return m
    if m is not None and (kind == "foreign_deps" or (kind == "foreign_depgroup" and
                                                     name in ("project", "assembly", "frameworks"))):
        extra = [("Add Shared Project Reference...", lambda: add_reference_dialog(win, project, "shared"))]
        if dotnet:
            extra.append(("Add COM Reference...", lambda: add_reference_dialog(win, project, "com")))
        _insert_after(m, "Add Project Reference...", extra)
        return m
    if kind == "foreign_dep":
        dkind, _, inc = str(name).partition("|")
        if dkind == "framework" and inc.startswith(".NET Framework"):
            return m
        if m is None:
            m = QMenu(win)
        first = m.actions()[0] if m.actions() else None
        if dkind in ("assembly", "framework", "package", "project", "com"):
            a = QAction("Open in Object Browser", m)
            a.triggered.connect(lambda: open_in_object_browser(win, project, dkind, inc))
            (m.insertAction(first, a) if first is not None else m.addAction(a))
        if dkind == "shared":
            m.addAction("Remove", lambda: _remove_shared(win, project, inc))
        if dkind == "framework" and any(it.include.lower() == inc.lower()
                                        for it in project.ms.explicit("FrameworkReference")):
            m.addAction("Remove", lambda: (ED.remove_framework_reference(project.ms, inc), ED.commit(win, project)))
        m.addSeparator()
        props = m.addAction("Properties", lambda: _properties(win, item))
        props.setShortcut(QKeySequence("Alt+Return"))
        return m
    return m


def _remove_shared(win, project, inc: str) -> None:
    if ED.remove_shared_import(project.ms, inc):
        ED.commit(win, project)


def _properties(win, item) -> None:
    try:
        win.solution.setCurrentItem(item)
        win.show_reference_properties(item)
        win.dock_props.show()
        win.dock_props.raise_()
    except Exception:  # noqa: BLE001
        pass


# ====================================================================== Add Existing Item (Add / Add As Link)
def add_existing_item_dialog(win, project, rel_dir: str = "", files: list[str] | None = None,
                             as_link: bool | None = None):
    """VS's Add Existing Item: the Add button has a drop-down with Add As Link."""
    if files is None:
        dlg = QFileDialog(win, f"Add Existing Item - {project.name}", str(project.folder / rel_dir))
        dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dlg.setFileMode(QFileDialog.FileMode.ExistingFiles)
        ext = project.ms.code_ext
        dlg.setNameFilters([f"{ {'.cs': 'Visual C#', '.vb': 'Visual Basic', '.fs': 'Visual F#'}.get(ext, 'Code')} "
                            f"Files (*{ext} *.resx *.settings *.xaml)", "All Files (*.*)"])
        dlg.setLabelText(QFileDialog.DialogLabel.Accept, "Add")
        state = {"link": False}
        box = dlg.findChild(QDialogButtonBox)
        if box is not None:
            btn = QPushButton("Add As Link")
            btn.setToolTip("Add a link to the file instead of copying it into the project folder")
            box.addButton(btn, QDialogButtonBox.ButtonRole.ActionRole)

            def link():
                state["link"] = True
                dlg.accept()
            btn.clicked.connect(link)
        dlg.add_as_link_state = state
        if not dlg.exec():
            return []
        files = dlg.selectedFiles()
        as_link = state["link"]
    out = []
    for f in files:
        try:
            if as_link:
                inc = ED.add_as_link(project.ms, f, rel_dir)
                if inc:
                    out.append(f"{Path(f).name} (link)")
                    continue
            out.append(project.add_existing_item(Path(f), rel_dir))
        except OSError as e:
            try:
                win.log(f"*** {e}")
            except Exception:  # noqa: BLE001
                pass
    if as_link and out:
        ED.commit(win, project)
    elif out:
        try:
            from ...foreign import vs_ui
            vs_ui._refresh(win)
        except Exception:  # noqa: BLE001
            pass
    if out:
        try:
            win.log(f"{project.name}: added {', '.join(out)}")
        except Exception:  # noqa: BLE001
            pass
    return out


# ====================================================================== View menu
def _view_menu(win) -> None:
    if getattr(win, "a_object_browser", None) is not None:
        return
    mb = win.menuBar()
    view = next((a.menu() for a in mb.actions() if a.menu() is not None and a.text().replace("&", "") == "View"),
                None)
    a = QAction("Object Browser", win)
    a.setShortcut(QKeySequence("Ctrl+Alt+J"))
    a.triggered.connect(lambda: _show_ob(win))
    win.a_object_browser = a
    if view is not None:
        acts = view.actions()
        # after Code / Designer, like VS (View > Object Browser sits with the other tool windows)
        before = next((x for x in acts if x.isSeparator()), None)
        view.insertAction(before, a) if before is not None else view.addAction(a)
    else:
        win.addAction(a)


def _show_ob(win):
    from .object_browser import show_object_browser
    return show_object_browser(win)


# ====================================================================== install
def _wrap_remove_ref(vs_ui) -> None:
    """Solution Explorer > reference > Remove: also reload the C# language server."""
    if getattr(vs_ui._remove_ref, "_refs_wrapped", False):
        return
    orig = vs_ui._remove_ref

    def _remove_ref(win, project, kind, inc):
        orig(win, project, kind, inc)
        try:
            from .lsp_reload import project_file_changed
            project_file_changed(win, project.ms.path)
        except Exception:  # noqa: BLE001
            pass
    _remove_ref._refs_wrapped = True
    vs_ui._remove_ref = _remove_ref


def install(win) -> None:
    from ...foreign import vs_ui
    _wrap_project_menu(vs_ui)
    _wrap_remove_ref(vs_ui)
    vs_ui.add_existing_item_dialog = add_existing_item_dialog
    try:
        from . import props
        props.install(win)
    except Exception as e:  # noqa: BLE001
        print(f"[references] properties: {e}")
    QTimer.singleShot(0, lambda: _view_menu(win))


__all__ = ["install", "add_reference_dialog", "add_existing_item_dialog", "open_in_object_browser"]
