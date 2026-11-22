"""Extension views in RAD IDE: ``contributes.viewsContainers`` / ``views`` / ``viewsWelcome`` and the
``view/title`` / ``view/item/context`` menus (the host side is radide/vsx/host/treeview.js and webview.js).

  * where a view lives follows VS Code: a container in ``activitybar`` -> the primary side bar (left dock area),
    ``panel`` -> the bottom panel, ``secondarySidebar`` -> the secondary side bar (right); views contributed to the
    built-in containers (explorer, scm, debug, test, remote) go to the side bar next to the IDE's own window.
    Docks of one container are tabbed together; in the VS Code / Agent layouts every container is an Activity
    Bar / Panel / secondary side bar entry (radide.features.workbench.register_view).
  * a tree view is a ``TreePane``: message line, welcome content (viewsWelcome) while the tree is empty, the tree
    (icons: codicons / images / file icons, descriptions, tooltips with resolveTreeItem, checkboxes,
    multi-selection), a title row with the view/title actions ('navigation' as buttons, the rest under "..."),
    collapse all, the view/item/context menu (``viewItem`` = contextValue), reveal(), selection / visibility /
    expand / checkbox events.
  * ``when`` clauses of containers and views are re-evaluated when context keys change: a view whose clause
    turns false is hidden (and shown again when it turns true, if it was hidden for that reason).
"""
from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QDockWidget, QHBoxLayout, QLabel, QMenu, QPushButton, QSizePolicy, QToolButton,
                             QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QVBoxLayout, QWidget)

from . import menus as M
from . import when as W

BUILTIN_CONTAINERS = {"explorer": ("Explorer", "activitybar"), "scm": ("Source Control", "activitybar"),
                      "debug": ("Run and Debug", "activitybar"), "test": ("Testing", "activitybar"),
                      "remote": ("Remote Explorer", "activitybar")}
LOCATION_AREA = {"activitybar": Qt.DockWidgetArea.LeftDockWidgetArea,
                 "panel": Qt.DockWidgetArea.BottomDockWidgetArea,
                 "secondarySidebar": Qt.DockWidgetArea.RightDockWidgetArea}
LOCATION_WB = {"activitybar": "side", "panel": "panel", "secondarySidebar": "right"}
H_ROLE, CMD_ROLE, PATH_ROLE, LOADED_ROLE, CTX_ROLE, RES_ROLE = (Qt.ItemDataRole.UserRole + i for i in range(6))


def _alive(o) -> bool:
    try:
        from PyQt6 import sip
        return o is not None and not sip.isdeleted(o)
    except Exception:  # noqa: BLE001
        return o is not None


def _title(v) -> str:
    return (v.get("value") or v.get("original") or "") if isinstance(v, dict) else str(v or "")


# ============================================================================ title row (view/title actions)
class TitleRow(QWidget):
    """A thin row of view/title action buttons ('navigation' group) and a '...' menu for the other groups."""

    def __init__(self, views: "ViewsUI", view_id: str):
        super().__init__()
        self.views = views
        self.view_id = view_id
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 1, 2, 1)
        lay.setSpacing(1)
        self.label = QLabel("")
        self.label.setStyleSheet("font-size: 8pt; opacity: 0.8;")
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay.addWidget(self.label, 1)
        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(1)
        lay.addLayout(self.buttons)
        self.extra: list = []         # (icon name, tooltip, slot) of built-in buttons (collapse all)
        self.refresh()

    def refresh(self):
        while self.buttons.count():
            w = self.buttons.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        ctx = self.views.context_for_view(self.view_id)
        nav, rest = [], []
        for e in M.entries(self.views.svc, "view/title", ctx):
            (nav if e.group == "navigation" else rest).append(e)
        for e in nav:
            b = QToolButton()
            ic = M.qicon(e)
            if ic is not None:
                b.setIcon(ic)
            else:
                b.setText(M.label(e))
            b.setToolTip(M.label(e))
            b.setAutoRaise(True)
            b.setEnabled(e.enabled)
            b.clicked.connect(lambda _c=False, cid=e.command: self.views.run_title_command(self.view_id, cid))
            b.setProperty("vsxCommand", e.command)
            self.buttons.addWidget(b)
        for icon_name, tip, slot in self.extra:
            from . import codicon
            b = QToolButton()
            ic = codicon.icon(icon_name)
            if ic is not None:
                b.setIcon(ic)
            else:
                b.setText(tip[:1])
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.clicked.connect(slot)
            self.buttons.addWidget(b)
        if rest:
            b = QToolButton()
            b.setText("...")
            b.setAutoRaise(True)
            b.setToolTip("More Actions...")
            b.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            m = QMenu(b)
            last = None
            for e in rest:
                if last is not None and e.group != last:
                    m.addSeparator()
                last = e.group
                M._add(m, e, lambda cid: self.views.run_title_command(self.view_id, cid))
            b.setMenu(m)
            self.buttons.addWidget(b)
        self.setVisible(bool(nav or rest or self.extra or self.label.text()))

    def commands(self) -> list[str]:
        out = []
        for i in range(self.buttons.count()):
            w = self.buttons.itemAt(i).widget()
            if w is not None and w.property("vsxCommand"):
                out.append(w.property("vsxCommand"))
        return out


# ============================================================================ tree pane
class TreePane(QWidget):
    def __init__(self, views: "ViewsUI", view_id: str):
        super().__init__()
        self.views = views
        self.view_id = view_id
        self.options: dict = {}
        self.has_items = False
        self.loaded = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.title_row = TitleRow(views, view_id)
        lay.addWidget(self.title_row)
        self.message = QLabel("")
        self.message.setWordWrap(True)
        self.message.setContentsMargins(8, 4, 8, 4)
        self.message.hide()
        lay.addWidget(self.message)
        self.welcome = QWidget()
        self.welcome_lay = QVBoxLayout(self.welcome)
        self.welcome_lay.setContentsMargins(10, 8, 10, 8)
        self.welcome.hide()
        lay.addWidget(self.welcome)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        self.tree.itemExpanded.connect(lambda it: self._expanded(it, True))
        self.tree.itemCollapsed.connect(lambda it: self._expanded(it, False))
        self.tree.itemClicked.connect(lambda it, _c=0: self.views.activate(self.view_id, it))
        self.tree.itemActivated.connect(lambda it, _c=0: self.views.activate(self.view_id, it))
        self.tree.itemSelectionChanged.connect(self._selection)
        self.tree.itemChanged.connect(self._item_changed)
        self.tree.setMouseTracking(True)
        self.tree.itemEntered.connect(self._hover)
        lay.addWidget(self.tree, 1)
        self._suppress = False

    # tree API kept for callers that used the bare QTreeWidget
    def topLevelItemCount(self):  # noqa: N802
        return self.tree.topLevelItemCount()

    def topLevelItem(self, i):  # noqa: N802
        return self.tree.topLevelItem(i)

    def set_options(self, o: dict):
        self.options = o or {}
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection if self.options.get("canSelectMany")
                                   else QTreeWidget.SelectionMode.SingleSelection)
        self.title_row.extra = [("collapse-all", "Collapse All", self.tree.collapseAll)] \
            if self.options.get("showCollapseAll") else []
        self.title_row.refresh()

    def _expanded(self, item, on: bool):
        if self._suppress:
            return
        if on and not item.data(0, LOADED_ROLE):
            item.setData(0, LOADED_ROLE, True)
            self.views.load(self.view_id, item)
        self.views.notify("tree/expand", {"viewId": self.view_id, "handle": item.data(0, H_ROLE), "expanded": on})

    def _selection(self):
        if self._suppress:
            return
        self.views.notify("tree/selection", {"viewId": self.view_id,
                                             "handles": [i.data(0, H_ROLE) for i in self.tree.selectedItems()]})

    def _item_changed(self, item, col):
        if self._suppress or item.data(0, Qt.ItemDataRole.CheckStateRole) is None:
            return
        st = 1 if item.checkState(0) == Qt.CheckState.Checked else 0
        self.views.notify("tree/checkbox", {"viewId": self.view_id, "items": [[item.data(0, H_ROLE), st]]})

    def _hover(self, item, _col):
        if item.data(0, RES_ROLE) or item.toolTip(0):
            return
        item.setData(0, RES_ROLE, True)

        def got(res, it=item):
            if res and _alive(self.tree) and res.get("tooltip"):
                try:
                    it.setToolTip(0, res["tooltip"])
                except RuntimeError:
                    pass
        self.views.request("tree/resolve", {"viewId": self.view_id, "handle": item.data(0, H_ROLE)}, got)

    def _context_menu(self, pos):
        it = self.tree.itemAt(pos)
        if it is None:
            return
        if it not in self.tree.selectedItems():
            self.tree.setCurrentItem(it)
        ctx = self.views.context_for_view(self.view_id, it)
        m = QMenu(self.tree)
        selected = [i.data(0, H_ROLE) for i in self.tree.selectedItems()]
        handle = it.data(0, H_ROLE)
        n = M.fill_menu(self.views.svc, m, "view/item/context", ctx,
                        lambda cid: self.views.run_item_command(self.view_id, cid, handle, selected))
        if n:
            self.views.last_menu = [a.text() for a in m.actions() if a.text()]
            m.popup(self.tree.viewport().mapToGlobal(pos))

    def show_welcome(self, show: bool):
        while self.welcome_lay.count():
            w = self.welcome_lay.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        blocks = self.views.welcome_for(self.view_id) if show else []
        for contents in blocks:
            for line in str(contents).split("\n"):
                line = line.strip()
                if not line:
                    continue
                m = re.fullmatch(r"\[([^\]]+)\]\((command:[^)\s]+|https?://[^)\s]+)(?:\s+\"[^\"]*\")?\)", line)
                if m:
                    b = QPushButton(m.group(1))
                    b.clicked.connect(lambda _c=False, href=m.group(2): self.views.open_link(href))
                    self.welcome_lay.addWidget(b)
                else:
                    html = re.sub(r"\[([^\]]+)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", r'<a href="\2">\1</a>', line)
                    lab = QLabel(html)
                    lab.setWordWrap(True)
                    lab.setTextFormat(Qt.TextFormat.RichText)
                    lab.linkActivated.connect(self.views.open_link)
                    self.welcome_lay.addWidget(lab)
        self.welcome.setVisible(bool(blocks))
        self.tree.setVisible(not blocks)


# ============================================================================ the manager
class ViewsUI(QObject):
    def __init__(self, svc):
        super().__init__(svc)
        self.svc = svc
        self.win = svc.win
        self.panes: dict[str, TreePane] = {}
        self.docks: dict[str, QDockWidget] = {}      # tree view id -> dock
        self.registered_wb: set[str] = set()
        self.hidden_by_when: set[str] = set()
        self.last_menu: list[str] = []
        self.titles: dict[str, dict] = {}            # view id -> {title, description, badge}

    # ---------------------------------------------------------------- plumbing
    def notify(self, method, params):
        if self.svc.host.running():
            self.svc.host.notify(method, params)

    def request(self, method, params, cb=None, timeout_ms=15000):
        if self.svc.host.running():
            self.svc.before_request()
            self.svc.host.request(method, params, cb, timeout_ms=timeout_ms)
        elif cb is not None:
            cb(None)

    def handle(self, method: str, p: dict) -> bool:
        fn = getattr(self, "_n_" + method.replace("/", "_"), None)
        if fn is None:
            return False
        fn(p)
        return True

    def open_link(self, href: str):
        self.svc.webviews.open_link(href)

    # ---------------------------------------------------------------- model
    def view_info(self, view_id: str) -> dict | None:
        for ext in self.svc.extensions:
            for container, views in (ext.contributes.get("views") or {}).items():
                for v in views if isinstance(views, list) else []:
                    if isinstance(v, dict) and v.get("id") == view_id:
                        return {"id": view_id, "name": _title(v.get("name")) or "", "type": v.get("type", "tree"),
                                "container": container, "location": self.location_of(container), "when": v.get("when"),
                                "ext": ext, "icon": v.get("icon")}
        return None

    def all_views(self) -> list[tuple[str, dict]]:
        """(view id, view_info) of every contributed view whose when clause holds (Command Palette "view ")."""
        out = []
        for c in self.containers():
            for vid in c.get("views") or []:
                info = self.view_info(vid)
                if info is None:
                    continue
                try:
                    if not self.view_when(vid):
                        continue
                except Exception:  # noqa: BLE001
                    pass
                info = dict(info, container=c.get("title") or info.get("container"))
                out.append((vid, info))
        return out

    def container_info(self, cid: str) -> dict | None:
        if cid in BUILTIN_CONTAINERS:
            t, loc = BUILTIN_CONTAINERS[cid]
            return {"id": cid, "title": t, "location": loc, "icon": None, "ext": None, "when": None}
        for ext in self.svc.extensions:
            for loc, lst in (ext.contributes.get("viewsContainers") or {}).items():
                for c in lst if isinstance(lst, list) else []:
                    if isinstance(c, dict) and c.get("id") == cid:
                        return {"id": cid, "title": _title(c.get("title")) or cid, "location": loc,
                                "icon": c.get("icon"), "ext": ext, "when": c.get("when")}
        return None

    def location_of(self, container: str) -> str:
        info = self.container_info(container) if container not in BUILTIN_CONTAINERS else None
        if container in BUILTIN_CONTAINERS:
            return BUILTIN_CONTAINERS[container][1]
        return (info or {}).get("location") or "activitybar"

    def containers(self) -> list[dict]:
        out = {}
        for ext in self.svc.extensions:
            for container, views in (ext.contributes.get("views") or {}).items():
                ids = [v["id"] for v in views if isinstance(v, dict) and v.get("id")] if isinstance(views, list) else []
                if not ids:
                    continue
                info = out.get(container) or self.container_info(container) or \
                    {"id": container, "title": container, "location": "activitybar", "icon": None, "ext": ext, "when": None}
                info.setdefault("views", [])
                info["views"] = info["views"] + [i for i in ids if i not in info["views"]]
                out[container] = info
        return list(out.values())

    def area_for(self, view_id: str):
        info = self.view_info(view_id)
        return LOCATION_AREA.get((info or {}).get("location") or "secondarySidebar", Qt.DockWidgetArea.RightDockWidgetArea)

    def view_when(self, view_id: str) -> bool:
        info = self.view_info(view_id)
        if not info:
            return True
        cinfo = self.container_info(info["container"]) or {}
        ctx = self.svc.context_for()
        try:
            return W.evaluate(info.get("when"), ctx) and W.evaluate(cinfo.get("when"), ctx)
        except Exception:  # noqa: BLE001
            return True

    def welcome_for(self, view_id: str) -> list[str]:
        ctx = self.context_for_view(view_id)
        out = []
        for ext in self.svc.extensions:
            for w in ext.contributes_list("viewsWelcome"):
                if isinstance(w, dict) and w.get("view") == view_id and w.get("contents"):
                    try:
                        if W.evaluate(w.get("when"), ctx):
                            out.append(_title(w["contents"]))
                    except Exception:  # noqa: BLE001
                        pass
        return out

    def context_for_view(self, view_id: str, item=None) -> dict:
        ctx = self.svc.context_for()
        ctx["view"] = view_id
        if item is not None:
            ctx["viewItem"] = item.data(0, CTX_ROLE) or ""
            pane = self.panes.get(view_id)
            ctx["listMultiSelection"] = bool(pane and len(pane.tree.selectedItems()) > 1)
            res = item.data(0, PATH_ROLE)
            if res:
                p = Path(res)
                ctx.update({"resource": p.as_uri() if p.is_absolute() else res, "resourceScheme": "file",
                            "resourceFilename": p.name, "resourceExtname": p.suffix.lower(),
                            "resourcePath": str(p), "resourceDirname": str(p.parent)})
        return ctx

    # ---------------------------------------------------------------- docks
    def dock_title(self, view_id: str, default: str = "") -> str:
        info = self.view_info(view_id) or {}
        t = self.titles.get(view_id, {})
        name = t.get("title") or info.get("name") or default or view_id
        if not info.get("name") and info.get("container"):
            name = t.get("title") or (self.container_info(info["container"]) or {}).get("title") or name
        if t.get("description"):
            name += " - " + t["description"]
        if t.get("badge") and t["badge"].get("value"):
            name += f" ({t['badge']['value']})"
        return name

    def place(self, dock: QDockWidget, view_id: str):
        """Put a view's dock in its container's area and tab it with the other docks of that container."""
        win = self.win
        area = self.area_for(view_id)
        info = self.view_info(view_id) or {}
        dock.setProperty("vsxViewId", view_id)
        dock.setProperty("vsxContainer", info.get("container") or "")
        win.addDockWidget(area, dock)
        mates = [d for d in self._container_docks(info.get("container")) if d is not dock and d.isVisible()]
        if not mates and area == Qt.DockWidgetArea.LeftDockWidgetArea and info.get("container") == "explorer":
            sol = getattr(win, "dock_solution", None)
            mates = [sol] if sol is not None and sol.isVisible() else []
        if mates:
            win.tabifyDockWidget(mates[-1], dock)
        self.ensure_container(info.get("container"))

    def _container_docks(self, container) -> list[QDockWidget]:
        out = []
        if not container:
            return out
        for d in list(self.docks.values()) + list(self.svc.webviews.view_docks.values()):
            if _alive(d) and d.property("vsxContainer") == container:
                out.append(d)
        return out

    def tree_dock(self, view_id: str) -> QDockWidget:
        d = self.docks.get(view_id)
        if d is not None and _alive(d):
            return d
        d = QDockWidget(self.dock_title(view_id), self.win)
        d.setObjectName("vsxView_" + re.sub(r"\W+", "_", view_id))
        pane = TreePane(self, view_id)
        self.panes[view_id] = pane
        d.setWidget(pane)
        self.place(d, view_id)
        d.hide()
        d.visibilityChanged.connect(lambda vis, v=view_id: self._tree_visible(v, vis))
        self.docks[view_id] = d
        self.svc._view_docks = self.docks           # legacy name
        return d

    def tree(self, view_id: str) -> QTreeWidget | None:
        p = self.panes.get(view_id)
        return p.tree if p is not None else None

    def _tree_visible(self, view_id, vis):
        self.notify("tree/visible", {"viewId": view_id, "visible": bool(vis)})
        pane = self.panes.get(view_id)
        if vis and pane is not None and not pane.loaded:
            self.load(view_id, None)

    def show_view(self, view_id: str, focus: bool = True) -> bool:
        info = self.view_info(view_id)
        if info is None:
            return False
        if info["type"] == "webview":
            self.svc.webviews.show_view(view_id, focus=focus)
            return True
        self._reveal_container(info["container"])
        d = self.tree_dock(view_id)
        d.show()
        d.raise_()
        pane = self.panes[view_id]
        if not pane.loaded:
            self.load(view_id, None)
        if focus:
            pane.tree.setFocus()
        return True

    def show_container(self, cid: str) -> bool:
        """workbench.view.extension.<id>: open the container (its views whose when clause holds) and focus it."""
        c = next((x for x in self.containers() if x["id"] == cid), None)
        if c is None:
            return False
        shown = [v for v in c["views"] if self.view_when(v)] or c["views"][:1]
        for i, v in enumerate(shown):
            self.show_view(v, focus=(i == 0))
        return True

    def _reveal_container(self, cid):
        wb = getattr(self.win, "workbench", None)
        if wb is None or getattr(wb, "mode", "vs") == "vs" or not cid:
            return
        wid = "vsx." + cid
        if wid in self.registered_wb:
            try:
                wb.show_view(wid)
            except Exception:  # noqa: BLE001
                pass

    # ---------------------------------------------------------------- workbench (Activity Bar / Panel) entries
    def ensure_container(self, cid):
        """Register a container once with radide.features.workbench (VS Code / Agent layouts)."""
        if not cid or cid in self.registered_wb:
            return
        info = self.container_info(cid)
        if info is None:
            return
        try:
            from ..features import workbench as WBM
        except Exception:  # noqa: BLE001
            return
        icon = None
        if info.get("ext") is not None and isinstance(info.get("icon"), str) and not info["icon"].startswith("$("):
            f = Path(info["ext"].path) / info["icon"]
            icon = QIcon(str(f)) if f.is_file() else None
        elif isinstance(info.get("icon"), str) and info["icon"].startswith("$("):
            from . import codicon
            icon = codicon.icon(codicon.strip(info["icon"])[1] or "")
        if icon is None:
            icon = "puzzle"

        def factory(win, cid=cid):
            c = next((x for x in self.containers() if x["id"] == cid), None)
            if c is None:
                return None
            docks = []
            for v in c["views"]:
                if not self.view_when(v):
                    continue
                vi = self.view_info(v) or {}
                if vi.get("type") == "webview":
                    d = self.svc.webviews.placeholder_dock(v)      # resolved when it becomes visible
                else:
                    d = self.tree_dock(v)
                    if not self.panes[v].loaded:
                        QTimer.singleShot(0, lambda v=v: self.load(v, None))
                if d is not None:
                    docks.append(d)
            return docks or None
        self.registered_wb.add(cid)
        # views extensions add to a built-in container (explorer, scm ...) get their own entry next to the IDE's
        title = info["title"] + (" (extension views)" if cid in BUILTIN_CONTAINERS else "")
        try:
            WBM.register_view("vsx." + cid, title, icon=icon, factory=factory,
                              area=LOCATION_WB.get(info["location"], "side"), order=150, tooltip=title)
        except Exception as e:  # noqa: BLE001
            self.svc.log(f"views: register container {cid}: {e}")

    def register_containers(self):
        for c in self.containers():
            if c["id"] not in BUILTIN_CONTAINERS:
                self.ensure_container(c["id"])

    # ---------------------------------------------------------------- tree data
    def load(self, view_id: str, parent_item):
        pane = self.panes.get(view_id)
        if pane is None:
            return
        if parent_item is None:
            pane.loaded = True
        handle = parent_item.data(0, H_ROLE) if parent_item is not None else None

        def got(items, pane=pane, parent_item=parent_item):
            if not _alive(pane):
                return
            self._fill(pane, parent_item, items or [])
        self.request("tree/children", {"viewId": view_id, "handle": handle}, got)

    def _fill(self, pane: TreePane, parent_item, items: list):
        tree = pane.tree
        pane._suppress = True
        try:
            expanded = set()
            if parent_item is None:
                it = QTreeWidgetItemIterator(tree)
                while it.value():
                    if it.value().isExpanded():
                        expanded.add(it.value().data(0, H_ROLE))
                    it += 1
                tree.clear()
            else:
                try:
                    parent_item.takeChildren()
                except RuntimeError:
                    return
            for d in items:
                node = self._node(d)
                (parent_item.addChild if parent_item is not None else tree.addTopLevelItem)(node)
                if d.get("collapsible") == 2 or (d.get("collapsible") and d.get("handle") in expanded):
                    node.setData(0, LOADED_ROLE, True)
                    node.setExpanded(True)
                    self.load(pane.view_id, node)
        finally:
            pane._suppress = False
        if parent_item is None:
            pane.has_items = bool(items)
            pane.show_welcome(not items)

    def _node(self, d: dict) -> QTreeWidgetItem:
        from .host_ide import codicons
        label = codicons(d.get("label") or "")
        node = QTreeWidgetItem([label + (("   " + codicons(d["description"])) if d.get("description") else "")])
        node.setData(0, H_ROLE, d.get("handle"))
        node.setData(0, CMD_ROLE, d.get("command"))
        node.setData(0, PATH_ROLE, d.get("path") or d.get("resource"))
        node.setData(0, CTX_ROLE, d.get("contextValue") or "")
        if d.get("tooltip"):
            node.setToolTip(0, d["tooltip"])
            node.setData(0, RES_ROLE, True)
        if d.get("collapsible"):
            node.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
        if d.get("checkbox") is not None:
            node.setFlags(node.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            node.setCheckState(0, Qt.CheckState.Checked if d["checkbox"] else Qt.CheckState.Unchecked)
        ic = self._icon(d)
        if ic is not None:
            node.setIcon(0, ic)
        return node

    def _icon(self, d: dict):
        icon = d.get("icon") or {}
        if icon.get("codicon"):
            from . import codicon
            name = icon["codicon"]
            if name in ("file", "folder") and d.get("path"):
                return self._file_icon(d["path"], name == "folder")
            return codicon.icon(name)
        p = icon.get("path")
        if icon.get("light") or icon.get("dark"):
            try:
                from .. import theme as TH
                p = icon.get("dark") if TH.is_dark() else icon.get("light")
            except Exception:  # noqa: BLE001
                pass
            p = p or icon.get("dark") or icon.get("light")
        if p and Path(p).is_file():
            return QIcon(p)
        if not icon and d.get("path"):
            return self._file_icon(d["path"], bool(d.get("collapsible")))
        return None

    def _file_icon(self, path: str, folder: bool):
        try:
            from PyQt6.QtCore import QFileInfo
            from PyQt6.QtWidgets import QFileIconProvider
            prov = getattr(self, "_iconprov", None) or QFileIconProvider()
            self._iconprov = prov
            if folder:
                return prov.icon(QFileIconProvider.IconType.Folder)
            return prov.icon(QFileInfo(path))
        except Exception:  # noqa: BLE001
            return None

    def activate(self, view_id: str, item):
        cmd = item.data(0, CMD_ROLE)
        if isinstance(cmd, dict) and cmd.get("command"):
            self.svc.execute(cmd["command"], cmd.get("arguments") or [])

    def run_title_command(self, view_id: str, command: str):
        self.request("tree/command", {"viewId": view_id, "command": command, "handle": None, "selected": []}) \
            if view_id in self.panes else self.svc.execute(command, [])

    def run_item_command(self, view_id: str, command: str, handle, selected):
        self.request("tree/command", {"viewId": view_id, "command": command, "handle": handle,
                                      "selected": selected or []})

    def _find(self, view_id: str, handle):
        tree = self.tree(view_id)
        if tree is None:
            return None
        it = QTreeWidgetItemIterator(tree)
        while it.value():
            if it.value().data(0, H_ROLE) == handle:
                return it.value()
            it += 1
        return None

    # ---------------------------------------------------------------- host notifications
    def _n_tree_registered(self, p):
        vid = p.get("viewId")
        if not vid:
            return
        if self.view_info(vid) is None:
            return
        self.tree_dock(vid)
        self.panes[vid].set_options(p.get("options") or {})
        d = self.docks[vid]
        if d.isVisible():
            self.load(vid, None)

    def _n_tree_changed(self, p):
        vid = p.get("viewId")
        pane = self.panes.get(vid)
        if pane is None or not pane.loaded:
            return
        handles = p.get("handles")
        if not handles:
            self.load(vid, None)
            return
        for h in handles:
            it = self._find(vid, h)
            if it is not None and it.data(0, LOADED_ROLE):
                self.load(vid, it)

    def _n_tree_update(self, p):
        vid = p.get("viewId")
        t = self.titles.setdefault(vid, {})
        for k in ("title", "description", "badge"):
            if k in p:
                t[k] = p[k]
        d = self.docks.get(vid) or self.svc.webviews.view_docks.get(vid)
        if d is not None and _alive(d) and any(k in p for k in ("title", "description", "badge")):
            d.setWindowTitle(self.dock_title(vid, d.windowTitle()))
        pane = self.panes.get(vid)
        if pane is not None and "message" in p:
            pane.message.setText(p.get("message") or "")
            pane.message.setVisible(bool(p.get("message")))

    def _n_tree_reveal(self, p):
        vid = p.get("viewId")
        chain = p.get("chain") or []
        o = p.get("options") or {}
        self.show_view(vid, focus=bool(o.get("focus")))
        pane = self.panes.get(vid)
        if pane is None:
            return
        self._reveal_step(vid, list(chain), o, None, 0)

    def _reveal_step(self, vid, chain, o, parent, tries):
        if not chain:
            return
        it = self._find(vid, chain[0])
        if it is None:
            if tries < 40:
                QTimer.singleShot(100, lambda: self._reveal_step(vid, chain, o, parent, tries + 1))
            return
        if len(chain) > 1:
            if not it.data(0, LOADED_ROLE):
                it.setData(0, LOADED_ROLE, True)
                self.load(vid, it)
            it.setExpanded(True)
            QTimer.singleShot(50, lambda: self._reveal_step(vid, chain[1:], o, it, 0))
            return
        tree = self.tree(vid)
        tree.scrollToItem(it)
        if o.get("select", True):
            tree.setCurrentItem(it)
        if o.get("expand"):
            it.setExpanded(True)
        if o.get("focus"):
            tree.setFocus()

    def _n_tree_disposed(self, p):
        d = self.docks.get(p.get("viewId"))
        if d is not None and _alive(d):
            pane = self.panes.get(p.get("viewId"))
            if pane is not None:
                pane.tree.clear()
                pane.loaded = False

    # ---------------------------------------------------------------- context keys changed
    def context_changed(self):
        for vid, pane in list(self.panes.items()):
            if _alive(pane):
                pane.title_row.refresh()
                if pane.loaded and not pane.has_items:
                    pane.show_welcome(True)
        for vid, d in list(self.docks.items()) + list(self.svc.webviews.view_docks.items()):
            if not _alive(d):
                continue
            ok = self.view_when(vid)
            if not ok and d.isVisible():
                d.hide()
                self.hidden_by_when.add(vid)
            elif ok and vid in self.hidden_by_when:
                self.hidden_by_when.discard(vid)
                d.show()
        for wv in list(self.svc.webviews.items.values()):
            tr = getattr(wv, "title_row", None)
            if tr is not None and _alive(tr):
                tr.refresh()

    def reset(self):
        for pane in self.panes.values():
            if _alive(pane):
                pane.tree.clear()
                pane.loaded = False


__all__ = ["ViewsUI", "TreePane", "TitleRow", "BUILTIN_CONTAINERS", "LOCATION_AREA"]
