"""File watcher by polling (remote file systems have no change notifications that work everywhere):
a background thread stats the watched files and lists the watched folders every *interval* seconds and
emits fileChanged / dirChanged on the Qt thread."""
from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, pyqtSignal


class PollingWatcher(QObject):
    fileChanged = pyqtSignal(str, bool)       # path, still exists
    dirChanged = pyqtSignal(str)
    failed = pyqtSignal(str)                  # connection lost ...

    def __init__(self, fs, interval: float = 3.0, parent=None):
        super().__init__(parent)
        self.fs = fs
        self.interval = interval
        self._files: dict[str, tuple | None] = {}
        self._dirs: dict[str, frozenset | None] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread: threading.Thread | None = None
        self._failed = False

    @staticmethod
    def _sig(e) -> tuple | None:
        return None if e is None else (round(e.mtime, 3), e.size)

    def watch_file(self, path: str, entry=None) -> None:
        with self._lock:
            self._files[path] = self._sig(entry) if entry is not None else self._files.get(path, ("?",))

    def set_baseline(self, path: str, entry) -> None:
        """After our own upload: the new state is not a change."""
        with self._lock:
            if path in self._files:
                self._files[path] = self._sig(entry)

    def unwatch_file(self, path: str) -> None:
        with self._lock:
            self._files.pop(path, None)

    def watch_dir(self, path: str) -> None:
        with self._lock:
            self._dirs.setdefault(path, None)

    def unwatch_dir(self, path: str) -> None:
        with self._lock:
            self._dirs.pop(path, None)

    def watched(self) -> tuple[list[str], list[str]]:
        with self._lock:
            return list(self._files), list(self._dirs)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="radide-remote-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread is not None:
            self._thread.join(5)
        self._thread = None

    def poll_now(self) -> None:
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.check()
                self._failed = False
            except Exception as e:  # noqa: BLE001 - keep polling (the connection may come back)
                if not self._failed:
                    self._failed = True
                    try:
                        self.failed.emit(str(e))
                    except RuntimeError:
                        return
            self._wake.wait(self.interval)
            self._wake.clear()

    def check(self) -> None:
        """One polling pass (also called directly by tests)."""
        files, dirs = self.watched()
        for path in files:
            if self._stop.is_set():
                return
            e = self.fs.stat(path)
            sig = self._sig(e)
            with self._lock:
                if path not in self._files:
                    continue
                old = self._files[path]
                self._files[path] = sig
            if old == ("?",):
                continue
            if old != sig:
                self.fileChanged.emit(path, e is not None)
        for path in dirs:
            if self._stop.is_set():
                return
            try:
                names = frozenset((x.name, x.is_dir, round(x.mtime, 3) if not x.is_dir else 0)
                                  for x in self.fs.listdir(path))
            except Exception:  # noqa: BLE001 - folder deleted
                names = frozenset()
            with self._lock:
                if path not in self._dirs:
                    continue
                old = self._dirs[path]
                self._dirs[path] = names
            if old is not None and old != names:
                self.dirChanged.emit(path)


__all__ = ["PollingWatcher"]
