"""Run blocking NuGet work (HTTP, dotnet CLI) off the GUI thread and get the result back on it."""
from __future__ import annotations

import threading
import traceback

from PyQt6.QtCore import QObject, pyqtSignal


class _Bridge(QObject):
    done = pyqtSignal(object, object, object)       # callback, result, error
    line = pyqtSignal(object, str)                  # log callback, text

    def __init__(self):
        super().__init__()
        self.done.connect(self._deliver)
        self.line.connect(lambda cb, s: cb(s))

    @staticmethod
    def _deliver(cb, result, error):
        if cb is not None:
            cb(result, error)


_bridge: _Bridge | None = None


def bridge() -> _Bridge:
    global _bridge
    if _bridge is None:
        _bridge = _Bridge()                         # created on the GUI thread (first call)
    return _bridge


def run_async(fn, callback=None, *args, **kwargs) -> threading.Thread:
    """fn(*args, **kwargs) in a daemon thread; callback(result, error) on the GUI thread."""
    b = bridge()

    def work():
        try:
            r = fn(*args, **kwargs)
        except Exception as e:  # noqa: BLE001
            e.trace = traceback.format_exc()        # type: ignore[attr-defined]
            b.done.emit(callback, None, e)
            return
        b.done.emit(callback, r, None)
    t = threading.Thread(target=work, daemon=True, name="nuget-worker")
    t.start()
    return t


def thread_log(callback):
    """A log function usable from a worker thread (lines reach `callback` on the GUI thread)."""
    b = bridge()
    return lambda s: b.line.emit(callback, str(s))


def alive(widget) -> bool:
    try:
        from PyQt6 import sip
        return widget is not None and not sip.isdeleted(widget)
    except Exception:  # noqa: BLE001
        return widget is not None


__all__ = ["run_async", "thread_log", "alive", "bridge"]
