"""Document Outline: the control tree of the current form (View > Document Outline).

Containers show their children, a TabControl shows one node per page, non-visual
components are listed under "Components". Clicking a node selects the control
(and shows its TabControl page)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDockWidget, QTreeWidget, QTreeWidgetItem

from ..controls import split_items
from ..layout import tab_page
from ..toolbox import control_icon

ROLE = Qt.ItemDataRole.UserRole


class DocumentOutline(QTreeWidget):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.doc = None
        self.items: dict[str, QTreeWidgetItem] = {}
        self._syncing = False
        self.setHeaderHidden(True)
        self.itemClicked.connect(self._on_click)
        self.currentItemChanged.connect(lambda cur, _prev: self._on_click(cur))

    # ------------------------------------------------------------ binding
    def bind(self, doc) -> None:
        if doc is self.doc:
            return
        if self.doc is not None:
            for sig, slot in self._signals(self.doc):
                try:
                    sig.disconnect(slot)
                except TypeError:
                    pass
        self.doc = doc
        if doc is not None:
            for sig, slot in self._signals(doc):
                sig.connect(slot)
        self.rebuild()

    def _signals(self, doc):
        return [(doc.structureChanged, self.rebuild), (doc.selectionChanged, self._on_selection),
                (doc.controlChanged, self._on_changed)]

    def _on_changed(self, ctrl) -> None:
        if ctrl is None or ctrl.type == "TabControl":
            self.rebuild()

    # ------------------------------------------------------------ tree
    def _signature(self):
        """What the tree shows: the form name and each control's name / type / parent / page (TabPages)."""
        doc = self.doc
        if doc is None:
            return None
        form = doc.form
        return (id(doc), form.name, tuple((c.name, c.type, c.parent, tab_page(c), str(c.props.get("TabPages", "")))
                                          for c in form.controls))

    def _on_screen(self) -> bool:
        return self.isVisible() and not self.visibleRegion().isEmpty()

    def _dock_shown(self, visible: bool) -> None:
        if visible and getattr(self, "_dirty", False):
            self.rebuild(force=True)

    def rebuild(self, force: bool = False) -> None:
        # Undo, a form property, a drag of the form edge ... ask again for the same tree: rebuilt only when
        # what it shows changed, and not at all while the window is hidden behind another tab (it is
        # rebuilt when its tab is shown) - a 400-control form took ~0.3-4 s per rebuild
        sig = self._signature()
        if not force and self.doc is not None and not self._on_screen():
            self._dirty = True
            return
        if not force and not getattr(self, "_dirty", False) and sig is not None and sig == getattr(self, "_sig", None):
            self._on_selection(self.doc.selected)
            return
        self._dirty = False
        self._sig = sig
        self._syncing = True
        self.clear()
        self.items = {}
        doc = self.doc
        if doc is None:
            self._syncing = False
            return
        form = doc.form
        root = QTreeWidgetItem([f"{form.name} (Form)"])
        root.setData(0, ROLE, "")
        self.addTopLevelItem(root)

        def add(parent_item, ctrl):
            it = QTreeWidgetItem([f"{ctrl.name}  ({ctrl.type})"])
            it.setIcon(0, control_icon(ctrl.type))
            it.setData(0, ROLE, ctrl.name)
            parent_item.addChild(it)
            self.items[ctrl.name] = it
            kids = form.children(ctrl.name)
            if ctrl.type == "TabControl":
                pages = split_items(ctrl.props.get("TabPages", "")) or ["TabPage1"]
                used = max([len(pages) - 1] + [tab_page(k) for k in kids])
                for i in range(used + 1):
                    page = QTreeWidgetItem([pages[i] if i < len(pages) else f"(page {i})"])
                    page.setData(0, ROLE, f"{ctrl.name}#page{i}")
                    it.addChild(page)
                    for k in kids:
                        if tab_page(k) == i:
                            add(page, k)
            else:
                for k in kids:
                    add(it, k)

        for c in form.children(""):
            add(root, c)
        comps = form.nonvisual()
        if comps:
            group = QTreeWidgetItem(["Components"])
            group.setData(0, ROLE, None)
            self.addTopLevelItem(group)
            for c in comps:
                add(group, c)
        self.expandAll()
        self._syncing = False
        self._on_selection(doc.selected)

    def _on_selection(self, ctrl) -> None:
        self._syncing = True
        it = self.items.get(ctrl.name) if ctrl is not None else self.topLevelItem(0)
        if it is not None:
            self.setCurrentItem(it)
        self._syncing = False

    def _on_click(self, item) -> None:
        if self._syncing or item is None or self.doc is None:
            return
        name = item.data(0, ROLE)
        if name is None:
            return
        if "#page" in str(name):                          # a TabControl page: show it
            tc_name, _, idx = str(name).partition("#page")
            tc = self.doc.form.find(tc_name)
            if tc is not None:
                self.doc.select(tc)
                self.doc.set_prop(tc, "SelectedIndex", int(idx), record=False)
            return
        self.doc.select(self.doc.form.find(name) if name else None)


def install(win) -> None:
    outline = DocumentOutline(win)
    dock = QDockWidget("Document Outline", win)
    dock.setObjectName("Document Outline")
    dock.setWidget(outline)
    win.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
    if getattr(win, "dock_solution", None) is not None:
        win.tabifyDockWidget(win.dock_solution, dock)
        win.dock_solution.raise_()
    win.dock_outline = dock
    win.doc_outline = outline
    dock.visibilityChanged.connect(outline._dock_shown)
    for a in win.menuBar().actions():
        if a.menu() is not None and a.text().replace("&", "").lower() == "view":
            a.menu().addAction(dock.toggleViewAction())
            break

    def follow(*_):
        d = win._current_designer()
        if d is not None:
            outline.bind(d.doc)
        else:
            cur = win._current_form() if hasattr(win, "_current_form") else None
            outline.bind(win.docs.get(cur) if cur else None)
    win.tabs.currentChanged.connect(follow)
    follow()
