"""The object an extension's ``activate(api)`` receives (see docs/PLUGIN_API.md).

Everything an extension adds through this API (menu actions, tool-bar buttons, docks, status-bar widgets,
signal connections, themes, languages, AI providers) is removed again when the extension is disabled or
uninstalled, without restarting the IDE.
"""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QDockWidget, QMenu, QWidget


class ExtensionAPI:
    version = "1.0"

    def __init__(self, win, ext):
        self.win = win
        self._ext = ext
        self.id = ext.id
        self.path = Path(ext.path)
        self._actions: list[tuple[object, QAction]] = []
        self._menus: list[QMenu] = []
        self._docks: list[QDockWidget] = []
        self._widgets: list[QWidget] = []
        self._connections: list[tuple[object, object]] = []
        self._disposers: list = []

    # ------------------------------------------------------------ basics
    @property
    def manifest(self) -> dict:
        return self._ext.manifest

    @property
    def settings(self) -> QSettings:
        """Per-extension settings (QSettings group extensions/<id>/...)."""
        s = QSettings()
        s.beginGroup(f"extensions/{self.id}")
        return s

    def log(self, text: str) -> None:
        """Write a line to the Output window."""
        try:
            self.win.log(f"[{self._ext.name}] {text}")
        except Exception:  # noqa: BLE001
            print(f"[{self._ext.name}] {text}")

    def status(self, text: str, msec: int = 4000) -> None:
        try:
            self.win.statusBar().showMessage(text, msec)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------ menus / tool bars
    def menu(self, path: str) -> QMenu:
        """The menu at *path* ("Tools", "Tools/My Extension", "&Help"); created when missing."""
        parts = [p for p in path.replace("\\", "/").split("/") if p]
        if not parts:
            raise ValueError("empty menu path")
        bar = self.win.menuBar()
        current = None
        for i, name in enumerate(parts):
            container = bar if current is None else current
            found = None
            for act in container.actions():
                if act.menu() is not None and act.text().replace("&", "") == name.replace("&", ""):
                    found = act.menu()
                    act.setVisible(True)
                    break
            if found is None:
                found = QMenu(name, self.win)
                if current is None:
                    help_act = next((a for a in bar.actions() if a.text().replace("&", "") == "Help"), None)
                    if help_act is not None:
                        bar.insertMenu(help_act, found)
                    else:
                        bar.addMenu(found)
                else:
                    current.addMenu(found)
                self._menus.append(found)
            current = found
        return current

    def add_action(self, menu_path: str, text: str, callback, shortcut: str | None = None,
                   status_tip: str = "", icon=None) -> QAction:
        """Add a command to a menu (and to the Command Palette, which lists every menu action)."""
        m = self.menu(menu_path)
        act = QAction(text, self.win)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        if status_tip:
            act.setStatusTip(status_tip)
        if icon is not None:
            act.setIcon(icon)
        act.triggered.connect(lambda _checked=False: self._safe(callback))
        m.addAction(act)
        self._actions.append((m, act))
        return act

    def add_toolbar_action(self, text: str, callback, icon=None, tooltip: str = "") -> QAction:
        """A button on the IDE's main tool bar."""
        from PyQt6.QtWidgets import QToolBar
        bars = self.win.findChildren(QToolBar)
        bar = bars[0] if bars else self.win.addToolBar("Extensions")
        act = QAction(text, self.win)
        if icon is not None:
            act.setIcon(icon)
        act.setToolTip(tooltip or text)
        act.triggered.connect(lambda _checked=False: self._safe(callback))
        bar.addAction(act)
        self._actions.append((bar, act))
        return act

    # ------------------------------------------------------------ docks / status bar
    def add_dock(self, title: str, widget: QWidget, area: str = "right", object_name: str = "") -> QDockWidget:
        """A dockable tool window (area: left | right | bottom | top). It is tabbed with the Output window
        when area is "bottom"."""
        areas = {"left": Qt.DockWidgetArea.LeftDockWidgetArea, "right": Qt.DockWidgetArea.RightDockWidgetArea,
                 "bottom": Qt.DockWidgetArea.BottomDockWidgetArea, "top": Qt.DockWidgetArea.TopDockWidgetArea}
        dock = QDockWidget(title, self.win)
        dock.setObjectName(object_name or f"ext_{self.id}_{len(self._docks)}")
        dock.setWidget(widget)
        self.win.addDockWidget(areas.get(area, areas["right"]), dock)
        out = getattr(self.win, "dock_output", None)
        if area == "bottom" and out is not None:
            try:
                self.win.tabifyDockWidget(out, dock)
            except Exception:  # noqa: BLE001
                pass
        self._docks.append(dock)
        return dock

    def add_status_widget(self, widget: QWidget, permanent: bool = True) -> QWidget:
        sb = self.win.statusBar()
        (sb.addPermanentWidget if permanent else sb.addWidget)(widget)
        self._widgets.append(widget)
        return widget

    # ------------------------------------------------------------ IDE events
    def connect(self, signal, slot) -> None:
        """Connect to an IDE signal; disconnected automatically on disable. Example:
        api.connect(api.theme.changed, self.on_theme)."""
        signal.connect(slot)
        self._connections.append((signal, slot))

    def on_theme_changed(self, fn) -> None:
        from .. import theme
        self.connect(theme.changed, fn)

    def on_dispose(self, fn) -> None:
        """fn() runs when the extension is disabled / uninstalled."""
        self._disposers.append(fn)

    # ------------------------------------------------------------ registries
    @property
    def theme(self):
        """The radide.theme module: theme.color("text"), theme.role(label, "muted"), theme.changed ..."""
        from .. import theme
        return theme

    def register_theme(self, name: str, data: dict) -> str:
        from . import register_theme
        name = register_theme(name, data, self.id)
        self._ext.registered.setdefault("themes", []).append(name)
        return name

    def register_language(self, plugin) -> None:
        from ..languages import LanguagePlugin, _PLUGINS, all_plugins
        if not isinstance(plugin, LanguagePlugin):
            raise TypeError("plugin must be a LanguagePlugin instance")
        all_plugins()
        _PLUGINS[plugin.id] = plugin
        self._ext.registered.setdefault("languages", []).append(plugin.id)

    def register_ai_provider(self, provider) -> None:
        from .. import ai
        ai.register(provider)
        self._ext.registered.setdefault("aiProviders", []).append(provider.id)

    # ------------------------------------------------------------ helpers
    def current_editor_text(self) -> str | None:
        """Text of the active code editor, or None."""
        try:
            view = self.win._current_code()
            ed = getattr(view, "editor", None)
            if ed is None:
                return None
            for attr in ("text", "toPlainText"):
                fn = getattr(ed, attr, None)
                if callable(fn):
                    return fn()
        except Exception:  # noqa: BLE001
            return None
        return None

    def _safe(self, fn):
        try:
            return fn()
        except Exception:  # noqa: BLE001 - a broken command must not crash the IDE
            import traceback
            msg = traceback.format_exc()
            self._ext.errors.append(msg)
            self.log(f"command failed:\n{msg}")
            return None

    def _dispose(self) -> None:
        for fn in reversed(self._disposers):
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass
        for signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except (TypeError, RuntimeError):
                pass
        for container, act in self._actions:
            try:
                container.removeAction(act)
                act.deleteLater()
            except RuntimeError:
                pass
        for dock in self._docks:
            try:
                self.win.removeDockWidget(dock)
                dock.deleteLater()
            except RuntimeError:
                pass
        for w in self._widgets:
            try:
                self.win.statusBar().removeWidget(w)
                w.deleteLater()
            except RuntimeError:
                pass
        for m in reversed(self._menus):          # menus this extension created: hidden when empty
            try:
                if not any(a.isVisible() for a in m.actions()):
                    m.menuAction().setVisible(False)
            except RuntimeError:
                pass
        self._actions, self._docks, self._widgets, self._menus = [], [], [], []
        self._connections, self._disposers = [], []
