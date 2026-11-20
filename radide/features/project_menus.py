"""Dynamic project menus: the commands of the KIND of project that is open (radide/project_actions.py,
docs/PROJECT_ACTIONS.md) - Laravel's artisan, Django's manage.py, npm scripts, Makefile targets ...

* a top-level menu per detected provider, inserted after "Project" ("Laravel", "npm Scripts" ...), shown only
  while such a project is active (several can be active) and filled when it opens (scripts edited meanwhile
  show up at once),
* a dynamic section at the end of the Project menu: "<Provider> Commands" sub menus,
* Solution Explorer right-click: the provider's ``folder_actions`` / ``file_actions`` for the clicked folder /
  file at the top of the context menu - normal projects, website folder trees and foreign projects (one hook in
  ``solution_ui.MENU_HOOKS``),
* the "Project Actions" tool bar (actions with ``toolbar=True`` of the active providers + Stop),
* Command Palette entries "<Provider>: <Action>" (the menu copies are hidden from the palette).

``win.project_menus`` is the ProjectMenus controller: ``refresh(force=False)``, ``providers()``, ``context()``,
``stop_all()``, ``menus`` (provider id -> top-level QMenu), ``toolbar``.
"""
from __future__ import annotations

import os
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtWidgets import QMenu, QStyle, QToolBar, QToolButton

from .. import project_actions as pa

NO_PALETTE = "wbNoPalette"          # command_palette: skip this menu / tool bar copy


# ============================================================================ helpers
def _icon(win, spec) -> QIcon | None:
    if spec is None:
        return None
    if isinstance(spec, QIcon):
        return spec
    try:
        if isinstance(spec, (tuple, list)) and len(spec) >= 2:
            from .. import icons
            return icons.badge(str(spec[0]), str(spec[1]), 16)
        if isinstance(spec, str):
            if spec.startswith("SP_"):
                return win.style().standardIcon(getattr(QStyle.StandardPixmap, spec))
            from .. import icons
            ic = icons.icon(spec)
            return ic if not ic.isNull() else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _menu_by_title(win, title: str):
    return next((a.menu() for a in win.menuBar().actions()
                 if a.menu() is not None and a.text().replace("&", "") == title), None)


def _project_of_item(win, item):
    try:
        from .solution_ui import PROJECT_ROLE
        key = item.data(0, PROJECT_ROLE) if item is not None else None
        st = win._pstates.get(key) if key else None
        if st:
            return st["project"]
    except Exception:  # noqa: BLE001
        pass
    return getattr(win, "project", None)


PATH_ROLE = Qt.ItemDataRole.UserRole + 11        # web_workspace.PATH_ROLE


def item_path(win, item, project) -> Path | None:
    """The folder / file a Solution Explorer item stands for (None = not a file system item)."""
    if item is None or project is None:
        return None
    folder = Path(project.folder)
    p = item.data(0, PATH_ROLE)
    if isinstance(p, str) and p:
        return Path(p)
    data = item.data(0, Qt.ItemDataRole.UserRole)
    if not data or not isinstance(data, (tuple, list)) or len(data) < 2:
        return None
    kind, name = data[0], data[1]
    if kind == "project":
        return folder
    if kind in ("solution", "references", "reference", "missing", "missing_form", "design", "generated"):
        return None
    if kind == "code":
        try:
            from ..languages import plugin_for_form
            return folder / plugin_for_form(project, name).code_file(name)
        except Exception:  # noqa: BLE001
            return None
    if not isinstance(name, str) or not name:
        return None
    cand = Path(name)
    if cand.is_absolute():
        return cand if cand.exists() else None
    cand = folder / name
    return cand if cand.exists() else None


# ============================================================================ controller
class ProjectMenus(QObject):
    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.menus: dict[str, QMenu] = {}
        self._project_section: list[QAction] = []
        self._shortcuts: list[QAction] = []
        self._palette_ids: list[str] = []
        self._key = None
        self._pending = False
        self.toolbar = QToolBar("Project Actions", win)
        self.toolbar.setObjectName("ProjectActions")
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        win.addToolBar(self.toolbar)
        self.toolbar.hide()
        self.a_stop = QAction("Stop Running Command", self)
        self.a_stop.setIcon(win.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.a_stop.triggered.connect(self.stop_all)
        self.a_stop.setEnabled(False)

    # ---------------------------------------------------------------- state
    def project(self):
        return getattr(self.win, "project", None)

    def providers(self) -> list:
        p = self.project()
        if p is None or not getattr(p, "folder", None):
            return []
        return pa.detect(Path(p.folder), p)

    def context(self, provider=None, project=None, target=None) -> pa.ActionContext:
        project = project if project is not None else self.project()
        return pa.ActionContext(self.win, project, getattr(project, "folder", None), provider, target)

    def schedule(self, force: bool = False) -> None:
        if force:
            self._key = None
        if self._pending:
            return
        self._pending = True
        QTimer.singleShot(0, self._run_scheduled)

    def _run_scheduled(self):
        self._pending = False
        try:
            self.refresh()
        except Exception as e:  # noqa: BLE001
            self.win.log(f"[project actions] {e}")

    def refresh(self, force: bool = False) -> bool:
        """Rebuild the menus / tool bar / palette entries when the active project or its providers changed."""
        p = self.project()
        provs = self.providers()
        key = (os.path.normcase(str(getattr(p, "folder", ""))) if p is not None else "",
               tuple(x.id for x in provs))
        if key == self._key and not force:
            return False
        self._key = key
        self._rebuild_top_menus(provs)
        self._rebuild_project_section(provs)
        self._rebuild_toolbar(provs)
        self._rebuild_palette_and_shortcuts(provs)
        if getattr(self.win, "_others_native_menu", None) is not None:   # foreign "Native" menu: hide it when
            try:                                                          # no foreign project is open any more
                from ..foreign._others_base import install_native_menu
                install_native_menu(self.win)
            except Exception:  # noqa: BLE001
                pass
        for err in pa.LOAD_ERRORS:
            self.win.log(err)
        pa.LOAD_ERRORS.clear()
        return True

    # ---------------------------------------------------------------- building menus
    def run(self, provider, action, target=None, project=None):
        ctx = self.context(provider, project, target)
        return pa.run_action(ctx, action)

    def fill(self, menu: QMenu, provider, items, target=None, project=None, top: bool = False) -> int:
        """Add QActions for an action list to *menu*; returns the number of items added."""
        n = 0
        ctx = self.context(provider, project, target)
        pending_sep = False
        for it in items:
            if isinstance(it, pa.Separator):
                pending_sep = n > 0
                continue
            if pending_sep:
                menu.addSeparator()
                pending_sep = False
            if isinstance(it, pa.Submenu):
                sub = menu.addMenu(it.title)
                ic = _icon(self.win, it.icon)
                if ic is not None:
                    sub.setIcon(ic)
                sub.menuAction().setProperty(NO_PALETTE, True)
                self.fill(sub, provider, it.items, target, project)
                n += 1
            elif isinstance(it, pa.Action):
                text = it.title + (f"\t{it.shortcut}" if it.shortcut else "")
                a = menu.addAction(text)
                a.setProperty(NO_PALETTE, True)
                a.setObjectName(f"projact.{provider.id}.{it.id}")
                ic = _icon(self.win, it.icon)
                if ic is not None:
                    a.setIcon(ic)
                if it.tip:
                    a.setToolTip(it.tip)
                    a.setStatusTip(it.tip)
                a.setEnabled(it.is_enabled(ctx))
                a.triggered.connect(lambda _c=False, pr=provider, ac=it, t=target, pj=project:
                                    self.run(pr, ac, t, pj))
                n += 1
        if n:
            menu.setToolTipsVisible(True)
        return n

    def _fill_provider_menu(self, menu: QMenu, provider):
        menu.clear()
        ctx = self.context(provider)
        n = self.fill(menu, provider, pa.safe_items(provider.actions, ctx), top=True)
        if n:
            menu.addSeparator()
        menu.addAction(self.a_stop)
        self.a_stop.setEnabled(bool(pa.running(self.win)))
        for err in pa.LOAD_ERRORS:
            self.win.log(err)
        pa.LOAD_ERRORS.clear()

    def _rebuild_top_menus(self, provs):
        mb = self.win.menuBar()
        for m in self.menus.values():
            mb.removeAction(m.menuAction())
            m.deleteLater()
        self.menus = {}
        proj = _menu_by_title(self.win, "Project")
        acts = mb.actions()
        anchor = None
        if proj is not None and proj.menuAction() in acts:
            i = acts.index(proj.menuAction())
            anchor = acts[i + 1] if i + 1 < len(acts) else None
        for prov in provs:
            m = QMenu(prov.title, self.win)
            m.setObjectName(f"projact.menu.{prov.id}")
            m.menuAction().setProperty(NO_PALETTE, True)
            m.menuAction().setProperty("projactProvider", prov.id)
            m.aboutToShow.connect(lambda m=m, p=prov: self._fill_provider_menu(m, p))
            m.addAction(self.a_stop)          # never empty: Qt does not open empty menus
            mb.insertMenu(anchor, m) if anchor is not None else mb.addMenu(m)
            self.menus[prov.id] = m

    def _rebuild_project_section(self, provs):
        proj = _menu_by_title(self.win, "Project")
        for a in self._project_section:
            if proj is not None:
                proj.removeAction(a)
            m = a.menu()
            if m is not None:
                m.deleteLater()
        self._project_section = []
        if proj is None or not provs:
            return
        self._project_section.append(proj.addSeparator())
        for prov in provs:
            m = QMenu(f"{prov.title} Commands", proj)
            m.setObjectName(f"projact.section.{prov.id}")
            m.menuAction().setProperty(NO_PALETTE, True)
            ic = _icon(self.win, prov.icon)
            if ic is not None:
                m.setIcon(ic)
            m.aboutToShow.connect(lambda m=m, p=prov: self._fill_provider_menu(m, p))
            m.addAction(self.a_stop)
            proj.addMenu(m)
            self._project_section.append(m.menuAction())

    def _rebuild_toolbar(self, provs):
        tb = self.toolbar
        for a in tb.actions():
            if a is not self.a_stop:
                a.deleteLater()
        tb.clear()
        n = 0
        for prov in provs:
            ctx = self.context(prov)
            for _path, act in pa.flatten(pa.safe_items(prov.actions, ctx)):
                if not act.toolbar:
                    continue
                if n and not any(x.property("projactProvider") == prov.id for x in tb.actions()):
                    tb.addSeparator()
                a = QAction(act.title.replace("...", ""), tb)
                a.setProperty(NO_PALETTE, True)
                a.setProperty("projactProvider", prov.id)
                a.setObjectName(f"projact.tb.{prov.id}.{act.id}")
                ic = _icon(self.win, act.icon) or _icon(self.win, prov.icon)
                if ic is not None:
                    a.setIcon(ic)
                a.setToolTip(f"{prov.title}: {act.title}" + (f"\n{act.tip}" if act.tip else ""))
                a.setEnabled(act.is_enabled(ctx))
                a.triggered.connect(lambda _c=False, pr=prov, ac=act: self.run(pr, ac))
                tb.addAction(a)
                n += 1
        if n:
            tb.addSeparator()
            tb.addAction(self.a_stop)
            self.a_stop.setProperty(NO_PALETTE, True)
            for btn in tb.findChildren(QToolButton):
                btn.setAutoRaise(True)
        self._update_toolbar_visibility(n > 0)

    def _update_toolbar_visibility(self, has: bool | None = None):
        if has is None:
            has = any(a.property("projactProvider") for a in self.toolbar.actions())
        wb = getattr(self.win, "workbench", None)
        vs = wb is None or getattr(wb, "mode", "vs") == "vs"
        zen = wb is not None and callable(getattr(wb, "zen_active", None)) and wb.zen_active()
        self.toolbar.setVisible(bool(has) and vs and not zen)

    def _rebuild_palette_and_shortcuts(self, provs):
        try:
            from . import command_palette as cp
        except Exception:  # noqa: BLE001
            cp = None
        if cp is not None:
            for cid in self._palette_ids:
                cp.unregister_command(cid)
        self._palette_ids = []
        for a in self._shortcuts:
            self.win.removeAction(a)
            a.deleteLater()
        self._shortcuts = []
        for prov in provs:
            ctx = self.context(prov)
            for path, act in pa.flatten(pa.safe_items(prov.actions, ctx)):
                if cp is not None and act.palette:
                    cid = f"projact.{prov.id}.{act.id}"
                    title = ": ".join([*path, act.title.replace("&", "").replace("...", "")])
                    cp.register_command(cid, title, lambda pr=prov, ac=act: self.run(pr, ac), category=prov.title,
                                        shortcut=act.shortcut or "",
                                        enabled=(lambda pr=prov, ac=act: ac.is_enabled(self.context(pr))))
                    self._palette_ids.append(cid)
                if act.shortcut and not path:
                    s = QAction(act.title, self.win)
                    s.setShortcut(QKeySequence(act.shortcut))
                    s.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
                    s.setProperty(NO_PALETTE, True)
                    s.triggered.connect(lambda _c=False, pr=prov, ac=act: self.run(pr, ac))
                    self.win.addAction(s)
                    self._shortcuts.append(s)

    # ---------------------------------------------------------------- running commands
    def stop_all(self) -> int:
        runs = pa.running(self.win)
        for r in runs:
            r.cancel()
        self.runs_changed()
        return len(runs)

    def runs_changed(self):
        self.a_stop.setEnabled(bool(pa.running(self.win)))

    # ---------------------------------------------------------------- Solution Explorer
    def items_for(self, item) -> tuple[list[tuple[object, list]], object, Path | None]:
        """[(provider, items)] for a Solution Explorer item, its project and its path."""
        project = _project_of_item(self.win, item)
        if project is None or not getattr(project, "folder", None):
            return [], project, None
        path = item_path(self.win, item, project)
        if path is None:
            return [], project, None
        folder = Path(project.folder).resolve()
        try:
            rel = path.resolve().relative_to(folder).as_posix()
        except (ValueError, OSError):
            return [], project, path
        rel = "" if rel == "." else rel
        out = []
        for prov in pa.detect(folder, project):
            ctx = pa.ActionContext(self.win, project, folder, prov, path)
            items = pa.safe_items(prov.folder_actions, ctx, rel) if path.is_dir() else \
                pa.safe_items(prov.file_actions, ctx, rel)
            if items:
                out.append((prov, items))
        return out, project, path

    def augment_menu(self, item, menu: QMenu) -> int:
        """Put the provider actions of *item* at the top of a Solution Explorer context menu."""
        groups, project, path = self.items_for(item)
        if not groups:
            return 0
        first = menu.actions()[0] if menu.actions() else None
        tmp = QMenu(menu)
        n = 0
        for i, (prov, items) in enumerate(groups):
            if i:
                tmp.addSeparator()
            if len(groups) > 1:
                sec = tmp.addSection(prov.title)
                sec.setProperty(NO_PALETTE, True)
            n += self.fill(tmp, prov, items, target=path, project=project)
        acts = tmp.actions()
        for a in acts:
            tmp.removeAction(a)
            if a.isSeparator() or a.menu() is not None:
                a.setParent(menu)
            menu.insertAction(first, a) if first is not None else menu.addAction(a)
        if first is not None and n:
            menu.insertSeparator(first)
        return n


# ============================================================================ hooks
def get(win) -> ProjectMenus | None:
    return getattr(win, "project_menus", None)


def runs_changed(win) -> None:
    pm = get(win)
    if pm is not None:
        pm.runs_changed()


def _menu_hook(win, item, menu) -> None:
    pm = get(win)
    if pm is not None:
        pm.augment_menu(item, menu)


def install(win) -> None:
    pm = ProjectMenus(win)
    win.project_menus = pm
    try:
        from . import solution_ui
        hooks = getattr(solution_ui, "MENU_HOOKS", None)
        if hooks is not None and _menu_hook not in hooks:
            hooks.append(_menu_hook)
    except Exception as e:  # noqa: BLE001
        win.log(f"[project actions] Solution Explorer hook: {e}")
    # the active project changes: activate_project / open / close call _update_title; tree refreshes
    for name in ("_update_title", "_fill_solution"):
        orig = getattr(win, name, None)
        if not callable(orig):
            continue

        def wrapped(*a, _orig=orig, **k):
            res = _orig(*a, **k)
            pm.schedule()
            return res
        setattr(win, name, wrapped)

    def later():
        wb = getattr(win, "workbench", None)
        sig = getattr(wb, "modeChanged", None)
        if sig is not None:
            sig.connect(lambda _m: QTimer.singleShot(0, pm._update_toolbar_visibility))
        pm.refresh(force=True)
    QTimer.singleShot(0, later)


__all__ = ["ProjectMenus", "get", "install", "item_path", "runs_changed"]
