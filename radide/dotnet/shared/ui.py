"""Shared Projects in the IDE window (radide/dotnet/shared/model.py is the model).

Hooks only (nothing in radide/foreign/vs_ui.py is restructured):

* Solution Explorer (``solution_ui.TREE_HOOKS``): every ``.shproj`` of the open .sln/.slnx is shown with its
  own icon, in its solution folder, with its folders and files (from the .projitems); consuming C#/VB
  projects get Dependencies > "Shared Projects" (old-style projects: under References, like VS).
* Context menus (``solution_ui.MENU_HOOKS``): shared project / folder / file menus (Add > New Item,
  Existing Item, New Folder, Class; Rename, Remove, Exclude From Project, Delete, Properties); project and
  Dependencies menus get "Shared Project Reference..."; the solution's Add > New Project... opens the
  VS2022 New Project wizard (radide/dotnet/templates/wizard.py) and Add > Existing Project... accepts .shproj.
* Double-click on a shared file opens it; the editor gets the project-context combo (ctxbar.py).
* File menu: "New Project (.NET, Visual Studio 2022)...".
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QInputDialog, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QStyle, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

from . import ctxbar as CTX
from . import model as SH

ROLE = Qt.ItemDataRole.UserRole
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"
KINDS = ("foreign_shproj", "foreign_shfolder", "foreign_shfile", "foreign_shgroup", "foreign_shref")


def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


def _project_role():
    from ...features.solution_ui import PROJECT_ROLE
    return PROJECT_ROLE


def _vs_solution(win):
    return CTX._vs_solution(win)


def _std(win, name):
    return win.style().standardIcon(getattr(QStyle.StandardPixmap, name))


_ICON = None


def shared_icon() -> QIcon:
    """Visual Studio's shared project glyph: two overlapping documents joined by a link."""
    global _ICON
    if _ICON is not None:
        return _ICON
    icon = QIcon()
    for size in (16, 32):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = size / 16.0
        pen = QPen(QColor("#68217A"))
        pen.setWidthF(1.2 * s)
        p.setPen(pen)
        p.setBrush(QColor("#F3E6F7"))
        p.drawRect(QRectF(1.5 * s, 1.5 * s, 8 * s, 10 * s))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRect(QRectF(6.5 * s, 4.5 * s, 8 * s, 10 * s))
        pen.setColor(QColor("#1E7BC4"))
        pen.setWidthF(1.6 * s)
        p.setPen(pen)
        p.drawLine(QPointF(8.5 * s, 8 * s), QPointF(12.5 * s, 8 * s))
        p.drawLine(QPointF(8.5 * s, 11 * s), QPointF(12.5 * s, 11 * s))
        p.end()
        icon.addPixmap(pm)
    _ICON = icon
    return icon


def shared_projects_of(win) -> list:
    return CTX.shared_projects(win)


def refresh(win) -> None:
    win._dotnet_shared = None
    try:
        win._fill_solution()
    except Exception as e:  # noqa: BLE001
        _log(win, f"*** {e}")
    try:
        from ...foreign import vs_ui
        vs_ui.refresh_config_ui(win)
    except Exception:  # noqa: BLE001
        pass
    CTX.refresh_all(win)


def _shared_by_path(win, path) -> SH.SharedProject | None:
    n = os.path.normcase(str(Path(path).resolve()))
    for sp in shared_projects_of(win):
        if os.path.normcase(str(sp.path)) == n or os.path.normcase(str(sp.projitems_path)) == n:
            return sp
    try:
        return SH.SharedProject(Path(path)) if Path(path).is_file() else None
    except (OSError, ValueError):
        return None


# ============================================================================ Solution Explorer
def _walk(item):
    yield item
    for i in range(item.childCount()):
        yield from _walk(item.child(i))


def _folder_item(root, names: list[str]):
    parent = root
    for n in names:
        nxt = None
        for i in range(parent.childCount()):
            ch = parent.child(i)
            d = ch.data(0, ROLE) or ("",)
            if d[0] == "foreign_slnfolder" and ch.text(0) == n:
                nxt = ch
                break
        if nxt is None:
            return parent
        parent = nxt
    return parent


def _insert_sorted(parent, item) -> None:
    """Among the projects of *parent* in name order (solution folders stay first)."""
    pos = parent.childCount()
    for i in range(parent.childCount()):
        ch = parent.child(i)
        d = ch.data(0, ROLE) or ("",)
        if d[0] in ("project", "foreign_shproj", "missing") and ch.text(0).split("  ")[0].lower() > item.text(0).lower():
            pos = i
            break
    parent.insertChild(pos, item)


def fill_shared(win, parent, sp: SH.SharedProject) -> QTreeWidgetItem:
    it = QTreeWidgetItem([sp.name])
    it.setData(0, ROLE, ("foreign_shproj", str(sp.path)))
    it.setIcon(0, shared_icon())
    it.setToolTip(0, f"Shared Project ({sp.language})\n{sp.path}\nIts files are compiled into every project that "
                     "references it (Dependencies > Shared Projects)")
    _insert_sorted(parent, it)
    folders: dict[str, QTreeWidgetItem] = {}

    def folder(rel: str):
        if not rel:
            return it
        if rel in folders:
            return folders[rel]
        up = folder(rel.rsplit("/", 1)[0] if "/" in rel else "")
        f = QTreeWidgetItem(up, [rel.rsplit("/", 1)[-1]])
        f.setData(0, ROLE, ("foreign_shfolder", f"{sp.path}|{rel}"))
        f.setIcon(0, _std(win, "SP_DirIcon"))
        folders[rel] = f
        return f
    for rel in sp.folders():
        folder(rel)
    for rel in sorted(sp.files(), key=lambda r: Path(r).name.lower()):
        par = folder(rel.rsplit("/", 1)[0] if "/" in rel else "")
        p = sp.abs_path(rel)
        fi = QTreeWidgetItem(par, [Path(rel).name])
        fi.setData(0, ROLE, ("foreign_shfile", str(p)))
        try:
            from ...features.solution_ui import file_icon
            fi.setIcon(0, file_icon(win, rel))
        except Exception:  # noqa: BLE001
            fi.setIcon(0, _std(win, "SP_FileIcon"))
        fi.setToolTip(0, f"{rel}\n(shared: compiled into each consuming project)")
        if not p.exists():
            fi.setForeground(0, Qt.GlobalColor.gray)
            fi.setToolTip(0, f"{rel} (file not found)")
    it.setExpanded(True)
    for f in folders.values():
        f.setExpanded(False)
    return it


def _dependencies_item(pi):
    for i in range(pi.childCount()):
        ch = pi.child(i)
        if (ch.data(0, ROLE) or ("",))[0] == "foreign_deps":
            return ch
    return None


def fill_consumer(win, pi, project) -> None:
    ms = project.ms
    if ms.language not in ("C#", "VB"):
        return
    imps = SH.shared_imports(ms.path)
    if not imps:
        return
    key = win._pkey(project)
    pr = _project_role()
    deps = _dependencies_item(pi)
    if deps is not None:                 # the Reference Manager slice (radide/dotnet/refs) listed them already
        theirs = [it for it in _walk(deps) if str((it.data(0, ROLE) or ("", ""))[1]).startswith("shared|")]
        if theirs:
            for it in theirs:
                it.setIcon(0, shared_icon())
            return
    if deps is None:
        title = "Dependencies" if ms.is_sdk else "References"
        deps = QTreeWidgetItem([title])
        deps.setData(0, ROLE, ("foreign_deps", title))
        deps.setData(0, pr, key)
        deps.setIcon(0, _std(win, "SP_FileLinkIcon"))
        pi.insertChild(0, deps)
    group = deps
    if ms.is_sdk:
        group = QTreeWidgetItem(deps, ["Shared Projects"])
        group.setData(0, ROLE, ("foreign_shgroup", "shared"))
        group.setData(0, pr, key)
        group.setIcon(0, _std(win, "SP_DirIcon"))
    for p in imps:
        ri = QTreeWidgetItem(group, [Path(p).stem])
        ri.setData(0, ROLE, ("foreign_shref", str(p)))
        ri.setData(0, pr, key)
        ri.setIcon(0, shared_icon())
        ri.setToolTip(0, f"Shared project {Path(p).stem}\n{p}")
        if not Path(p).is_file():
            ri.setForeground(0, Qt.GlobalColor.gray)
            ri.setToolTip(0, f"{p} (not found)")


def _tree_hook(win, root) -> None:
    sln = _vs_solution(win)
    if sln is None:
        return
    win._dotnet_shared = None
    shared = shared_projects_of(win) if sln.model is not None else []
    model = sln.model
    for sp in shared:
        names = model.folder_path(sp.sln_entry) if getattr(sp, "sln_entry", None) is not None else []
        fill_shared(win, _folder_item(root, names), sp)
    for it in list(_walk(root)):
        d = it.data(0, ROLE) or ("",)
        if d[0] != "project":
            continue
        proj = sln.project(d[1])
        if proj is not None and hasattr(proj, "ms"):
            try:
                fill_consumer(win, it, proj)
            except Exception as e:  # noqa: BLE001
                _log(win, f"[shared] {e}")
    if shared:
        n = len(sln.projects) + len(shared)
        root.setText(0, f"Solution '{sln.name}' ({n} of {n} projects)")


# ============================================================================ context menus
def _item_project(win, item):
    key = item.data(0, _project_role()) if item is not None else None
    st = win._pstates.get(key) if key else None
    return st["project"] if st else None


def _find_submenu(m: QMenu, title: str):
    for a in m.actions():
        sub = a.menu()
        if sub is not None and sub.title().replace("&", "") == title:
            return sub
    return None


def _menu_hook(win, item, m) -> None:
    data = item.data(0, ROLE) if item is not None else None
    kind, name = (data[0], data[1]) if data else ("solution", "")
    sln = _vs_solution(win)
    if sln is None:
        return
    if kind in KINDS:
        m.clear()
        _fill_menu(win, m, item, kind, name)
        return
    project = _item_project(win, item)
    lang_ok = project is not None and hasattr(project, "ms") and project.ms.language in ("C#", "VB")
    if kind == "project" and lang_ok:
        add = _find_submenu(m, "Add")
        if add is not None:
            add.addAction("Shared Project Reference...", lambda: add_shared_reference_dialog(win, project))
    elif lang_ok and (kind == "foreign_deps" or (kind == "foreign_depgroup" and name in ("project", "frameworks"))):
        m.addAction("Add Shared Project Reference...", lambda: add_shared_reference_dialog(win, project))
    elif kind == "solution" and sln.model is not None:
        add = _find_submenu(m, "Add")
        if add is None:
            return
        for a in add.actions():
            t = a.text().replace("&", "")
            if t == "New Project...":
                _rewire(a, lambda: new_project_wizard(win, add_to=sln))
            elif t == "Existing Project...":
                _rewire(a, lambda: add_existing_project_dialog(win))
        add.addAction("New Shared Project...", lambda: new_shared_project_dialog(win))


def _rewire(action, slot) -> None:
    try:
        action.triggered.disconnect()
    except (TypeError, RuntimeError):
        pass
    action.triggered.connect(lambda *_: slot())


def _fill_menu(win, m: QMenu, item, kind: str, name: str) -> None:
    if kind == "foreign_shproj":
        sp = _shared_by_path(win, name)
        if sp is None:
            return
        _add_submenu(win, m, sp, "")
        m.addSeparator()
        m.addAction("Rename", lambda: rename_shared_dialog(win, sp))
        m.addAction("Remove", lambda: remove_shared_from_solution(win, sp))
        m.addSeparator()
        m.addAction(f"Edit {sp.projitems_path.name}", lambda: win.open_any_file(sp.projitems_path))
        m.addAction("Open Folder in File Explorer", lambda: _explore(sp.folder))
        m.addSeparator()
        m.addAction("Properties", lambda: shared_properties(win, sp))
    elif kind == "foreign_shfolder":
        shp, _, rel = str(name).partition("|")
        sp = _shared_by_path(win, shp)
        if sp is None:
            return
        _add_submenu(win, m, sp, rel)
        m.addSeparator()
        m.addAction("Delete", lambda: delete_item(win, sp, rel))
        m.addAction("Open Folder in File Explorer", lambda: _explore(sp.abs_path(rel)))
    elif kind == "foreign_shfile":
        sp = _owner_of_file(win, item)
        if sp is None:
            return
        rel = sp.contains(name) or ""
        m.addAction("Open", lambda: win.open_any_file(Path(name)))
        m.addSeparator()
        m.addAction("Exclude From Project", lambda: exclude_item(win, sp, rel))
        m.addAction("Delete", lambda: delete_item(win, sp, rel))
        m.addAction("Rename", lambda: rename_item_dialog(win, sp, rel))
        m.addSeparator()
        m.addAction("Open Containing Folder", lambda: _explore(Path(name).parent))
    elif kind == "foreign_shgroup":
        project = _item_project(win, item)
        if project is not None:
            m.addAction("Add Shared Project Reference...", lambda: add_shared_reference_dialog(win, project))
    elif kind == "foreign_shref":
        project = _item_project(win, item)
        m.addAction("Open", lambda: select_shared(win, name))
        if project is not None:
            m.addSeparator()
            m.addAction("Remove", lambda: remove_shared_reference(win, project, name))


def _owner_of_file(win, item):
    p = item.parent()
    while p is not None:
        d = p.data(0, ROLE) or ("",)
        if d[0] == "foreign_shproj":
            return _shared_by_path(win, d[1])
        p = p.parent()
    return None


def _add_submenu(win, m: QMenu, sp, rel_dir: str) -> None:
    add = m.addMenu("Add")
    add.addAction("New Item...", lambda: new_item_dialog(win, sp, rel_dir))
    add.addAction("Existing Item...", lambda: add_existing_item_dialog(win, sp, rel_dir))
    add.addAction("New Folder", lambda: new_folder(win, sp, rel_dir))
    add.addSeparator()
    first = "Class" if sp.language == "C#" else "Module"
    add.addAction("Class...", lambda: new_item_dialog(win, sp, rel_dir, "Class"))
    if first != "Class":
        add.addAction("Module...", lambda: new_item_dialog(win, sp, rel_dir, "Module"))


def _explore(folder) -> None:
    if folder and Path(folder).exists() and not OFFSCREEN:
        try:
            os.startfile(str(folder))          # noqa: S606 - Windows Explorer
        except (OSError, AttributeError):
            pass


def _warn(win, title: str, text: str) -> None:
    _log(win, f"*** {title}: {text}")
    if not OFFSCREEN:
        QMessageBox.warning(win, title, text)


# ============================================================================ activation
def _dclick(win, item) -> None:
    d = item.data(0, ROLE) if item is not None else None
    if not d or d[0] not in KINDS:
        return
    if d[0] == "foreign_shfile":
        open_shared_file(win, Path(d[1]))
    elif d[0] == "foreign_shref":
        select_shared(win, d[1])


def open_shared_file(win, path: Path):
    ed = win.open_any_file(Path(path))
    try:
        w = win.tabs.currentWidget()
        if w is not None:
            CTX.attach(win, w)
    except Exception as e:  # noqa: BLE001
        _log(win, f"[project context] {e}")
    return ed


def select_shared(win, projitems_or_shproj) -> bool:
    sp = _shared_by_path(win, projitems_or_shproj)
    if sp is None:
        return False
    tree = win.solution
    stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
    while stack:
        it = stack.pop()
        d = it.data(0, ROLE) or ("",)
        if d[0] == "foreign_shproj" and os.path.normcase(str(Path(d[1]).resolve())) == os.path.normcase(str(sp.path)):
            tree.setCurrentItem(it)
            it.setExpanded(True)
            tree.scrollToItem(it)
            return True
        stack.extend(it.child(i) for i in range(it.childCount()))
    return False


# ============================================================================ actions
def new_item_dialog(win, sp, rel_dir: str = "", template: str = "", exec_: bool = True, name: str | None = None):
    """Add > New Item inside a shared project (writes the .projitems)."""
    dlg = QDialog(win)
    dlg.setWindowTitle(f"Add New Item - {sp.name}")
    dlg.resize(460, 380)
    lay = QVBoxLayout(dlg)
    lst = QListWidget()
    for t, ext in SH.ITEM_TEMPLATES.get(sp.language, []):
        li = QListWidgetItem(f"{t}   ({ext})")
        li.setData(ROLE, t)
        lst.addItem(li)
    lst.setCurrentRow(0)
    for i in range(lst.count()):
        if lst.item(i).data(ROLE) == template:
            lst.setCurrentRow(i)
    lay.addWidget(lst)
    form = QFormLayout()
    name_edit = QLineEdit()
    form.addRow("Name:", name_edit)
    lay.addLayout(form)

    def suggest():
        t = lst.currentItem().data(ROLE) if lst.currentItem() else "Class"
        base = {"Interface": "IInterface", "Module": "Module", "Enum": "Enum", "Text File": "TextFile",
                "JSON File": "JsonFile", "XML File": "XmlFile", "Code File": "CodeFile"}.get(t, "Class")
        i = 1
        have = {Path(r).stem.lower() for r in sp.files()}
        while f"{base}{i}".lower() in have:
            i += 1
        name_edit.setText(f"{base}{i}")
    lst.currentItemChanged.connect(lambda *_: suggest())
    suggest()
    if name:
        name_edit.setText(name)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.button(QDialogButtonBox.StandardButton.Ok).setText("Add")
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.template_list, dlg.name_edit = lst, name_edit
    dlg.apply = lambda: do_new_item(win, sp, lst.currentItem().data(ROLE), rel_dir, name_edit.text())
    if not exec_:
        return dlg
    if not dlg.exec():
        return None
    return dlg.apply()


def do_new_item(win, sp, template: str, rel_dir: str, name: str):
    try:
        created = sp.add_new_item(template, rel_dir, name)
    except (OSError, ValueError) as e:
        _warn(win, "Add New Item", str(e))
        return None
    _log(win, f"{sp.name}: added {', '.join(created)} ({sp.projitems_path.name} updated)")
    refresh(win)
    first = sp.abs_path(created[0])
    if first.suffix.lower() in (".cs", ".vb", ".txt", ".json", ".xml"):
        open_shared_file(win, first)
    return created


def add_existing_item_dialog(win, sp, rel_dir: str = "", files: list | None = None):
    if files is None:
        files, _ = QFileDialog.getOpenFileNames(win, "Add Existing Item", str(sp.items_folder / rel_dir),
                                                "All files (*)")
    out = []
    for f in files or []:
        try:
            out.append(sp.add_existing_item(Path(f), rel_dir))
        except OSError as e:
            _log(win, f"*** {e}")
    if out:
        _log(win, f"{sp.name}: added {', '.join(out)}")
        refresh(win)
    return out


def new_folder(win, sp, rel_dir: str = "", name: str | None = None):
    if name is None:
        name, ok = QInputDialog.getText(win, "New Folder", "Folder name:", text="NewFolder")
        if not ok or not name.strip():
            return None
    rel = f"{rel_dir.strip('/')}/{name.strip()}".strip("/")
    sp.new_folder(rel)
    _log(win, f"{sp.name}: new folder {rel}")
    refresh(win)
    return rel


def exclude_item(win, sp, rel: str) -> bool:
    ok = sp.exclude(rel)
    if ok:
        _log(win, f"{sp.name}: {rel} excluded from {sp.projitems_path.name} (the file stays on disk)")
    refresh(win)
    return ok


def delete_item(win, sp, rel: str, confirm: bool = True) -> bool:
    if confirm and not OFFSCREEN and QMessageBox.question(
            win, "Delete", f"'{rel}' will be deleted permanently.") != QMessageBox.StandardButton.Yes:
        return False
    ok = sp.delete(rel)
    if ok:
        _log(win, f"{sp.name}: deleted {rel}")
    refresh(win)
    return ok


def rename_item_dialog(win, sp, rel: str, new_name: str | None = None):
    if new_name is None:
        new_name, ok = QInputDialog.getText(win, "Rename", "New name:", text=Path(rel).name)
        if not ok or not new_name.strip() or new_name.strip() == Path(rel).name:
            return None
    try:
        new_rel = sp.rename_item(rel, new_name.strip())
    except (OSError, ValueError) as e:
        _warn(win, "Rename", str(e))
        return None
    _log(win, f"{sp.name}: renamed {rel} -> {new_rel}")
    refresh(win)
    return new_rel


def rename_shared_dialog(win, sp, new_name: str | None = None):
    sln = _vs_solution(win)
    if new_name is None:
        new_name, ok = QInputDialog.getText(win, "Rename", "Project name:", text=sp.name)
        if not ok or not new_name.strip() or new_name.strip() == sp.name:
            return None
    users = [p.ms.path for p in (sln.all_projects() if sln else []) if SH.references_shared(p.ms.path, sp)]
    try:
        sp.rename(new_name.strip(), users, sln.model if sln is not None else None)
    except (OSError, ValueError) as e:
        _warn(win, "Rename", str(e))
        return None
    for p in (sln.all_projects() if sln else []):
        if p.ms.path in users:
            try:
                p.reload()
            except Exception:  # noqa: BLE001
                pass
    _log(win, f"Renamed shared project to {sp.name} ({len(users)} consuming project(s) updated)")
    refresh(win)
    return sp


def remove_shared_from_solution(win, sp, confirm: bool = True) -> bool:
    sln = _vs_solution(win)
    if sln is None or sln.model is None:
        return False
    if confirm and not OFFSCREEN and QMessageBox.question(
            win, "Remove", f"'{sp.name}' will be removed from the solution (its files stay on disk; projects that "
                           "reference it keep their Import).") != QMessageBox.StandardButton.Yes:
        return False
    ok = SH.remove_from_solution(sln.model, sp)
    if ok:
        _log(win, f"Removed shared project {sp.name} from {sln.file.name}")
    refresh(win)
    return ok


def shared_properties(win, sp, exec_: bool = True):
    dlg = QDialog(win)
    dlg.setWindowTitle(f"{sp.name} Properties")
    lay = QFormLayout(dlg)
    ns = QLineEdit(sp.root_namespace)
    lay.addRow("Root namespace:", ns)
    lay.addRow("Language:", QLabel(sp.language))
    lay.addRow("Project file:", QLabel(str(sp.path)))
    lay.addRow("Items file:", QLabel(str(sp.projitems_path)))
    sln = _vs_solution(win)
    users = [sln.name_of(p) for p in (sln.all_projects() if sln else []) if SH.references_shared(p.ms.path, sp)]
    lay.addRow("Referenced by:", QLabel(", ".join(users) or "(no project)"))
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addRow(box)
    dlg.ns_edit = ns
    dlg.apply = lambda: sp.set_root_namespace(ns.text().strip()) if ns.text().strip() else False
    if not exec_:
        return dlg
    if dlg.exec():
        return dlg.apply()
    return None


# ============================================================================ references
class SharedReferencesTab(QWidget):
    """The "Shared Projects" page of the Reference Manager: shared projects of the solution with the
    project's language, checked when imported. ``apply()`` writes the changes (list of '+Name' / '-Name')."""

    def __init__(self, win, project, parent=None):
        super().__init__(parent)
        self.win, self.project = win, project
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setObjectName("sharedProjectsList")
        lay.addWidget(self.list)
        self.empty = QLabel("No shared projects in this solution. Add one with right-click on the solution > "
                            "Add > New Shared Project...")
        self.empty.setWordWrap(True)
        self.empty.setStyleSheet("color: gray")
        lay.addWidget(self.empty)
        self.fill()

    def fill(self) -> None:
        self.list.clear()
        lang = self.project.ms.language
        for sp in shared_projects_of(self.win):
            ok, why = SH.can_reference(self.project.ms.path, sp)
            li = QListWidgetItem(shared_icon(), f"{sp.name}    {sp.folder}")
            li.setData(ROLE, sp)
            if not ok:
                li.setFlags(li.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                li.setToolTip(why)
                continue
            li.setFlags(li.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            li.setCheckState(Qt.CheckState.Checked if SH.references_shared(self.project.ms.path, sp)
                             else Qt.CheckState.Unchecked)
            self.list.addItem(li)
        self.empty.setVisible(self.list.count() == 0)
        self.setToolTip(f"Shared projects ({lang}) that {self.project.name} can import")

    def set_checked(self, name: str, on: bool = True) -> bool:
        for i in range(self.list.count()):
            li = self.list.item(i)
            if li.data(ROLE).name.lower() == name.lower():
                li.setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
                return True
        return False

    def apply(self) -> list[str]:
        changed = []
        sln = _vs_solution(self.win)
        model = sln.model if sln is not None else None
        for i in range(self.list.count()):
            li = self.list.item(i)
            sp = li.data(ROLE)
            on = li.checkState() == Qt.CheckState.Checked
            was = SH.references_shared(self.project.ms.path, sp)
            try:
                if on and not was and SH.add_shared_reference(self.project.ms.path, sp):
                    SH.record_sln_shared_reference(model, self.project.ms.path, sp)
                    changed.append(f"+{sp.name}")
                elif was and not on and SH.remove_shared_reference(self.project.ms.path, sp):
                    SH.drop_sln_shared_reference(model, self.project.ms.path, sp)
                    changed.append(f"-{sp.name}")
            except (OSError, ValueError) as e:
                _log(self.win, f"*** {e}")
        if changed:
            try:
                self.project.reload()
            except Exception:  # noqa: BLE001
                pass
            _log(self.win, f"{self.project.name}: shared project references {' '.join(changed)} "
                           f"({self.project.ms.path.name} updated)")
        return changed


def add_shared_reference_dialog(win, project, exec_: bool = True):
    """Add > Shared Project Reference... (Reference Manager, Shared Projects page)."""
    dlg = QDialog(win)
    dlg.setWindowTitle(f"Reference Manager - {project.name}")
    dlg.resize(560, 380)
    lay = QVBoxLayout(dlg)
    head = QLabel("<b>Shared Projects</b>")
    lay.addWidget(head)
    tab = SharedReferencesTab(win, project, dlg)
    lay.addWidget(tab, 1)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    box.accepted.connect(dlg.accept)
    box.rejected.connect(dlg.reject)
    lay.addWidget(box)
    dlg.tab = tab

    def apply():
        ch = tab.apply()
        refresh(win)
        return ch
    dlg.apply = apply
    if not exec_:
        return dlg
    if dlg.exec():
        return apply()
    return None


def remove_shared_reference(win, project, projitems: str) -> bool:
    sp = _shared_by_path(win, projitems)
    if sp is None:
        return False
    ok = SH.remove_shared_reference(project.ms.path, sp)
    if ok:
        sln = _vs_solution(win)
        SH.drop_sln_shared_reference(sln.model if sln is not None else None, project.ms.path, sp)
        _log(win, f"{project.name}: removed shared project reference {sp.name}")
        try:
            project.reload()
        except Exception:  # noqa: BLE001
            pass
    refresh(win)
    return ok


# ============================================================================ new / existing
def new_shared_project_dialog(win, name: str | None = None, language: str | None = None):
    """Solution > Add > New Shared Project... (the wizard's Shared Project template, preselected)."""
    sln = _vs_solution(win)
    if sln is None or sln.model is None:
        return None
    if name is None:
        return new_project_wizard(win, add_to=sln, preselect="rad:shared-cs" if language != "VB" else "rad:shared-vb")
    return add_new_shared(win, name, language or "C#")


def add_new_shared(win, name: str, language: str = "C#"):
    sln = _vs_solution(win)
    try:
        sp = SH.create_shared_project(sln.folder, name, language)
    except (OSError, ValueError) as e:
        _warn(win, "New Shared Project", str(e))
        return None
    SH.add_to_solution(sln.model, sp)
    _log(win, f"Added shared project {sp.name} ({language}) to {sln.file.name}")
    refresh(win)
    return sp


def add_existing_project_dialog(win, path: str | None = None):
    """Solution > Add > Existing Project...: .csproj / .vbproj / .fsproj / .vcxproj and .shproj."""
    sln = _vs_solution(win)
    if sln is None or sln.model is None:
        return None
    if path is None:
        path, _ = QFileDialog.getOpenFileName(win, "Add Existing Project", str(sln.folder),
                                              "Project files (*.csproj *.vbproj *.fsproj *.vcxproj *.shproj);;"
                                              "Shared projects (*.shproj);;All files (*)")
        if not path:
            return None
    p = Path(path)
    if p.suffix.lower() == ".shproj":
        sp = SH.SharedProject(p)
        SH.add_to_solution(sln.model, sp)
        _log(win, f"Added shared project {sp.name} to {sln.file.name}")
        refresh(win)
        return sp
    from ...foreign import vs_ui
    return vs_ui.add_project_file(win, sln, p)


def new_project_wizard(win, add_to=None, preselect: str = "", exec_: bool = True):
    try:
        from ..templates import wizard
    except ImportError:                 # the VS2022 wizard is not built yet: the basic dialog
        from ...foreign import vs_ui
        sln = add_to or _vs_solution(win)
        return vs_ui.new_project_dialog(win, sln, exec_=exec_) if sln is not None else None
    return wizard.show_wizard(win, add_to=add_to, preselect=preselect, exec_=exec_)


# ============================================================================ install
_HOOKS_DONE = False


def install(win) -> None:
    """Called once per main window (radide/foreign/vs_ui.py install)."""
    global _HOOKS_DONE
    if getattr(win, "_dotnet_shared_installed", False):
        return
    win._dotnet_shared_installed = True
    if not _HOOKS_DONE:
        from ...features import solution_ui
        solution_ui.TREE_HOOKS.append(_tree_hook)
        solution_ui.MENU_HOOKS.append(_menu_hook)
        _HOOKS_DONE = True
    try:
        win.solution.itemDoubleClicked.connect(lambda item, _c: _dclick(win, item))
    except AttributeError:
        pass
    CTX.install(win)
    QTimer.singleShot(0, lambda: _file_menu(win))


def _file_menu(win) -> None:
    fm = getattr(win, "file_menu", None)
    if fm is None or getattr(win, "_dotnet_new_project_action", None) is not None:
        return
    try:
        from PyQt6.QtGui import QAction
        a = QAction("New Project (.NET, Visual Studio 2022)...", win)
        a.setShortcut("Ctrl+Alt+Shift+N")
        a.triggered.connect(lambda *_: new_project_wizard(win, add_to=None))
        acts = fm.actions()
        anchor = getattr(win, "a_new", None)
        idx = acts.index(anchor) if anchor in acts else -1
        fm.insertAction(acts[idx + 1] if 0 <= idx < len(acts) - 1 else None, a)
        win._dotnet_new_project_action = a
    except Exception as e:  # noqa: BLE001
        _log(win, f"[dotnet] {e}")


__all__ = ["install", "shared_icon", "shared_projects_of", "refresh", "fill_shared", "fill_consumer",
           "SharedReferencesTab", "add_shared_reference_dialog", "remove_shared_reference", "new_item_dialog",
           "do_new_item", "add_existing_item_dialog", "new_folder", "exclude_item", "delete_item",
           "rename_item_dialog", "rename_shared_dialog", "remove_shared_from_solution", "shared_properties",
           "new_shared_project_dialog", "add_new_shared", "add_existing_project_dialog", "new_project_wizard",
           "open_shared_file", "select_shared"]
