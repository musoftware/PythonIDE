"""VS Code extension (VSX / Open VSX) support.

Subsystems:
    package.py        .vsix unpacking, package.json model (Extension), install layout, extensions.json
    registry.py       Open VSX REST client (search, details, versions, download + SHA256, compatibility)
    manager.py        install / uninstall / update / enable / disable with dependency + pack resolution
    contrib_*.py      declarative contributions (themes, grammars, snippets, languages, icons, keys, config)
    host/, bridge.py  the Node extension host for extensions with code
    features/vsx_market.py   the Extensions view (Activity Bar, View menu, Tools > Extensions)

Event API for the contrib and host subsystems (callbacks run on the GUI thread when a Qt application
exists, otherwise synchronously)::

    from radide import vsx
    vsx.on_installed.connect(lambda ext: ...)       # ext: package.Extension (installed or updated)
    vsx.on_removed.connect(lambda ext: ...)         # the Extension that was uninstalled (folder is gone)
    vsx.on_enabled.connect(lambda ext, on: ...)     # enabled / disabled
    vsx.on_changed.connect(lambda: ...)             # anything above (refresh lists)
    vsx.on_reload_requested.connect(lambda: ...)    # user pressed "Reload" (restart the extension host)
    vsx.list_enabled()  -> [Extension]              vsx.list_installed() -> [Extension]
    vsx.get(ext_id)     -> Extension | None         vsx.root() -> Path
"""
from __future__ import annotations

import threading
import traceback
from pathlib import Path

from .package import Extension, VsixError, get_installed, installed, vsx_root

__all__ = ["API_LEVEL", "Event", "Extension", "VsixError", "on_installed", "on_removed", "on_enabled",
           "on_changed", "on_reload_requested", "root", "list_installed", "list_enabled", "get",
           "mark_restart", "restart_required", "request_reload"]

API_LEVEL = "1.90.0"          # the VS Code API level RAD IDE emulates (engines.vscode is checked against it)


class Event:
    """A tiny signal: connect(fn) / disconnect(fn) / emit(*args). Thread-safe; GUI-thread delivery."""

    def __init__(self, name: str):
        self.name = name
        self._subs: list = []

    def connect(self, fn) -> None:
        if fn not in self._subs:
            self._subs.append(fn)

    def disconnect(self, fn) -> None:
        try:
            self._subs.remove(fn)
        except ValueError:
            pass

    def emit(self, *args) -> None:
        if not _post(self._fire, args):
            self._fire(args)

    def _fire(self, args) -> None:
        for fn in list(self._subs):
            try:
                fn(*args)
            except Exception:  # noqa: BLE001 - a subscriber must not break the others
                traceback.print_exc()


_hub = None


def _post(fn, args) -> bool:
    """Run fn(args) on the GUI thread when called from another thread; False = call directly."""
    global _hub
    try:
        from PyQt6.QtCore import QCoreApplication, QObject, QThread, pyqtSignal
    except Exception:  # noqa: BLE001
        return False
    app = QCoreApplication.instance()
    if app is None or QThread.currentThread() is app.thread():
        return False
    if _hub is None:
        class _Hub(QObject):
            call = pyqtSignal(object, object)

        with _hub_lock:
            if _hub is None:
                h = _Hub()
                h.moveToThread(app.thread())
                h.call.connect(lambda f, a: f(a))
                _hub = h
    _hub.call.emit(fn, args)
    return True


_hub_lock = threading.Lock()

on_installed = Event("installed")
on_removed = Event("removed")
on_enabled = Event("enabled")
on_changed = Event("changed")
on_reload_requested = Event("reload_requested")

_pending_restart: dict[str, str] = {}      # id -> reason ("installed" / "removed" / "enabled" / "disabled")


def root() -> Path:
    return vsx_root()


def list_installed() -> list[Extension]:
    return installed()


def list_enabled() -> list[Extension]:
    return [e for e in installed() if e.enabled]


def get(ext_id: str) -> Extension | None:
    return get_installed(ext_id)


def mark_restart(ext: Extension, reason: str) -> None:
    """Extensions with code (main/browser) need the extension host reloaded to apply a change."""
    if ext.has_code:
        _pending_restart[ext.id] = reason


def restart_required() -> dict[str, str]:
    return dict(_pending_restart)


def request_reload() -> None:
    _pending_restart.clear()
    on_reload_requested.emit()
    on_changed.emit()
