"""Design View hooks (CONTRACTS 8.2, Expression Web): a "Design" toolbar button for the active HTML/PHP file,
File > Open in Design View..., Save All / close-project integration. The view itself is
radide/web_site/design.py; the Solution Explorer menu entry comes from features/web_workspace.py."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QFileDialog, QToolBar


def _active_page(win) -> Path | None:
    """Path of the HTML/PHP file shown by the current code tab (None for other tabs)."""
    from ..web_site.design import DesignView, is_designable
    w = win.tabs.currentWidget()
    if w is None or isinstance(w, DesignView):
        return None
    ed = getattr(w, "editor", None)
    p = getattr(ed, "path", None) or getattr(w, "path", None)
    if p is None or not is_designable(p):
        return None
    return Path(p)


def open_active_in_design(win, mode: str = "design"):
    from ..web_site.design import open_design_view
    p = _active_page(win)
    if p is None:
        win.statusBar().showMessage("Open an .html / .php file first", 3000)
        return None
    return open_design_view(win, p, mode)


def open_dialog(win):
    from ..web_site.design import open_design_view
    start = str(getattr(getattr(win, "project", None), "folder", "") or "")
    fn, _ = QFileDialog.getOpenFileName(win, "Open in Design View", start,
                                        "Web pages (*.html *.htm *.php *.phtml);;All files (*)")
    if fn:
        return open_design_view(win, Path(fn))
    return None


def install(win) -> None:
    from ..web_site import design

    win.open_design_view = lambda path, mode="design": design.open_design_view(win, path, mode)

    a = QAction("Design", win)
    a.setToolTip("Open the active HTML / PHP page in Design View (Ctrl+Shift+D)")
    a.setShortcut(QKeySequence("Ctrl+Shift+D"))
    a.triggered.connect(lambda: open_active_in_design(win))
    win.a_design_view = a
    a2 = QAction("Split", win)
    a2.setToolTip("Open the active HTML / PHP page in Split view (design + code) (Ctrl+Shift+Alt+D)")
    a2.setShortcut(QKeySequence("Ctrl+Shift+Alt+D"))        # keyboard users: not a tool-bar-only command
    a2.triggered.connect(lambda: open_active_in_design(win, "split"))
    win.a_split_view = a2
    from ..icons import icon
    a.setIcon(icon("design"))
    a.setIconText("Design")
    a2.setIcon(icon("split"))
    a2.setIconText("Split")
    tb =next((t for t in win.findChildren(QToolBar) if t.objectName() == "Standard"), None)
    if tb is not None:
        tb.addSeparator()
        tb.addAction(a)
        tb.addAction(a2)
    else:
        win.addAction(a)

    def update(_i=None):
        on = _active_page(win) is not None
        a.setEnabled(on)
        a2.setEnabled(on)
    win.tabs.currentChanged.connect(update)
    update()

    def design_room(_i=None):
        """A website's Design View became the current tab: give it room (web_workspace.make_design_room)."""
        try:
            if not isinstance(win.tabs.currentWidget(), design.DesignView):
                return
            proj = getattr(win, "project", None)
            if proj is None or getattr(proj, "kind", "") != "website":
                return
            from .web_workspace import make_design_room
            make_design_room(win)
        except Exception as e:  # noqa: BLE001 - layout help must never break the tabs
            win.log(f"[design] {e}")
    win.tabs.currentChanged.connect(lambda i: QTimer.singleShot(0, design_room))

    for title in ("&View", "&File"):
        menu = next((m.menu() for m in win.menuBar().actions() if m.text() == title and m.menu()), None)
        if menu is None:
            continue
        if title == "&View":
            menu.addSeparator()
            menu.addAction(a)
        else:
            act = QAction("Open in Design &View...", win)
            act.triggered.connect(lambda: open_dialog(win))
            first = next((x for x in menu.actions() if x.isSeparator()), None)
            menu.insertAction(first, act) if first is not None else menu.addAction(act)

    # Save All also saves the design views; closing the project asks about them
    win.a_save.triggered.connect(lambda: design.save_design_views(win))
    orig_any, orig_save_all = win._any_modified, win.save_all

    def any_modified():
        return orig_any() or any(dv.isModified() for dv in design.design_views(win))

    def save_all():
        design.save_design_views(win)
        return orig_save_all()
    win._any_modified = any_modified
    win.save_all = save_all
