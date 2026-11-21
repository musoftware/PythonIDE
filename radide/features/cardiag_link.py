"""Car connection tools in the IDE (radide/cardiag/link, docs/CARDIAG.md "Link layer").

Tools > Car Connection: Connect to Car... (adapter dialog with Test Connection), Disconnect, Bus Monitor (dock
with the raw adapter / bus traffic and a raw command line), Demo Car (Simulator) (dock: ignition / engine /
drive / overheat, warning lamps, TCP server for other OBD apps) and Find Control Units...
The connected link is shared through ``radide.cardiag.link.current_link()``.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDockWidget, QLabel


class CarDiagLink:
    def __init__(self, win):
        self.win = win
        self.dock_monitor = None
        self.dock_demo = None
        self.status = None
        win.cardiag_link = self
        QTimer.singleShot(0, self._menus)
        try:
            from ..cardiag.link.manager import on_link_changed
            on_link_changed(self._link_changed)
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def plain(text: str) -> str:
        return text.replace("&&", "\x00").replace("&", "").replace("\x00", "&")

    def _menu(self, title: str, parent=None):
        acts = parent.actions() if parent is not None else self.win.menuBar().actions()
        return next((a.menu() for a in acts if a.menu() is not None and self.plain(a.text()) == title), None)

    def _menus(self) -> None:
        tools = self._menu("Tools")
        if tools is None or self._menu("Car Connection", tools) is not None:
            return
        m = tools.addMenu("Car &Connection")
        m.setObjectName("CarConnectionMenu")
        m.addAction("&Connect to Car...", self.connect_dialog)
        self.a_disconnect = m.addAction("&Disconnect", self.disconnect)
        m.addSeparator()
        m.addAction("&Bus Monitor", self.show_monitor)
        m.addAction("&Demo Car (Simulator)", self.show_demo)
        m.addAction("&Find Control Units...", self.find_ecus)
        m.aboutToShow.connect(self._update_menu)
        self.menu = m

    def _update_menu(self) -> None:
        from ..cardiag.link import current_link
        self.a_disconnect.setEnabled(current_link() is not None)

    # ------------------------------------------------------------------ actions
    def connect_dialog(self):
        from ..cardiag.link.qt import ConnectDialog
        dlg = ConnectDialog(self.win)
        dlg.exec()
        return dlg

    def disconnect(self) -> None:
        from ..cardiag.link import set_current_link
        set_current_link(None)

    def _dock(self, title: str, name: str, widget, area=Qt.DockWidgetArea.BottomDockWidgetArea) -> QDockWidget:
        d = QDockWidget(title, self.win)
        d.setObjectName(name)
        d.setWidget(widget)
        self.win.addDockWidget(area, d)
        return d

    def show_monitor(self):
        from ..cardiag.link.qt import BusMonitor
        if self.dock_monitor is None:
            self.dock_monitor = self._dock("Bus Monitor", "CarDiagBusMonitorDock", BusMonitor())
        self.dock_monitor.show()
        self.dock_monitor.raise_()
        return self.dock_monitor.widget()

    def show_demo(self):
        from ..cardiag.link.qt import DemoCarPanel
        if self.dock_demo is None:
            self.dock_demo = self._dock("Demo Car", "CarDiagDemoCarDock", DemoCarPanel(),
                                        Qt.DockWidgetArea.RightDockWidgetArea)
        self.dock_demo.show()
        self.dock_demo.raise_()
        return self.dock_demo.widget()

    def find_ecus(self):
        from ..cardiag.link.qt import FindEcusDialog
        dlg = FindEcusDialog(self.win)
        dlg.show()
        return dlg

    def _link_changed(self, link) -> None:
        try:
            sb = self.win.statusBar()
        except (AttributeError, RuntimeError):
            return
        if self.status is None:
            self.status = QLabel("")
            self.status.setObjectName("CarConnectionStatus")
            sb.addPermanentWidget(self.status)
        self.status.setText("" if link is None else f"\U0001F697 {link.describe()}")
        self.status.setVisible(link is not None)


def install(win) -> None:
    CarDiagLink(win)
