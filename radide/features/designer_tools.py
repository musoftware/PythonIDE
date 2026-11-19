"""Designer commands: Format > Lock Controls and View > Tab Order (VS style)."""
from __future__ import annotations

from PyQt6.QtGui import QAction


def _menu(win, title: str):
    for a in win.menuBar().actions():
        m = a.menu()
        if m is not None and a.text().replace("&", "").lower() == title.lower():
            return m
    return None


def install(win) -> None:
    fmt = getattr(win, "format_menu", None) or _menu(win, "Format")
    view = _menu(win, "View")

    lock = QAction("&Lock Controls", win)
    lock.setCheckable(True)
    lock.setToolTip("Selected controls can no longer be moved or resized")

    def on_lock(checked):
        d = win._current_designer()
        if d is not None:
            d.set_locked(checked)
    lock.triggered.connect(on_lock)

    order = QAction("Ta&b Order", win)
    order.setCheckable(True)
    order.setToolTip("Click the controls in the order the Tab key should visit them (Esc to finish)")

    def on_order(checked):
        d = win._current_designer()
        if d is None:
            order.setChecked(False)
            return
        d.set_tab_order_mode(checked)
        if checked:
            win.statusBar().showMessage("Tab Order: click the controls in sequence - Esc or View > Tab Order "
                                        "to finish", 8000)
    order.triggered.connect(on_order)

    def sync(*_):
        d = win._current_designer()
        for a in (lock, order):
            a.setEnabled(d is not None)
        lock.setChecked(bool(d is not None and d.doc.locked))
        order.setChecked(bool(d is not None and d.tab_order_mode))
        if d is not None and not getattr(d, "_rad_tools_hooked", False):
            d._rad_tools_hooked = True
            d.tabOrderModeChanged.connect(lambda _on: sync())

    if fmt is not None:
        fmt.addSeparator()
        fmt.addAction(lock)
        fmt.aboutToShow.connect(sync)
    if view is not None:
        view.insertAction(view.actions()[2] if len(view.actions()) > 2 else None, order)
        view.aboutToShow.connect(sync)
    win.tabs.currentChanged.connect(sync)
    win.a_lock_controls = lock
    win.a_tab_order = order
    sync()
