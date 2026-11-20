"""One RAD IDE window per user: a second launch with a path (Explorer "Open with", a double-clicked
.radsln ...) hands the path to the running IDE and exits.

* The first instance holds a lock file (QLockFile, per user) and listens on a QLocalServer.
* A later instance that cannot take the lock connects (retrying while the first one is still starting),
  sends {"paths": [...], "line": N} as one JSON line, waits for "ok" and exits.
* ``open_target(win, path, line)`` opens anything: a solution / project / foreign project, a form or
  scene (its project is opened first), a .radext (asks to install it), a folder, or any file in a tab.

Disabled by --new-window or Tools > Options > Environment > "Open files in the running RAD IDE window".
The name is per user and per settings organisation (tests use their own: RADIDE_INSTANCE_NAME or
the "RADIDE-TEST..." organisation)."""
from __future__ import annotations

import getpass
import json
import os
import re
import time
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QDir, QLockFile, QObject, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

SETTING = "options/single_instance"
PROJECT_FILE_EXTS = {".radsln", ".sln", ".slnx", ".csproj", ".vbproj", ".fsproj", ".vcxproj", ".vbp", ".vbg",
                     ".dproj", ".dpr", ".dpk", ".groupproj", ".lpi", ".lpr", ".pro", ".code-workspace", ".iml",
                     ".pyproject"}
DOC_EXTS = (".form", ".scene", ".scene3d", ".rpt.json")


def instance_name() -> str:
    env = os.environ.get("RADIDE_INSTANCE_NAME", "").strip()
    if env:
        return env
    org = QCoreApplication.organizationName() or "RADIDE"
    if not org.upper().startswith("RADIDE-TEST"):
        org = "RADIDE"
    try:
        user = getpass.getuser()
    except Exception:  # noqa: BLE001
        user = "user"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", f"radide-{org}-{user}")


def acquire_primary(name: str | None = None) -> QLockFile | None:
    """The lock of the first instance, or None when another RAD IDE already holds it."""
    lock = QLockFile(os.path.join(QDir.tempPath(), (name or instance_name()) + ".lock"))
    lock.setStaleLockTime(0)                   # stale only when its process is gone
    if lock.tryLock(0):
        return lock
    if lock.removeStaleLockFile() and lock.tryLock(0):
        return lock
    return None


def _allow_foreground() -> None:
    try:                       # this process got the user's click: let the running IDE come to the front
        import ctypes
        ctypes.windll.user32.AllowSetForegroundWindow(-1)        # ASFW_ANY
    except Exception:  # noqa: BLE001
        pass


def send(paths: list[str], line: int | None = None, name: str | None = None, wait_s: float = 15.0) -> bool:
    """Hand *paths* to the running instance. False when none answers within *wait_s* seconds."""
    name = name or instance_name()
    msg = (json.dumps({"paths": [str(Path(p).resolve()) for p in paths], "line": line, "cwd": os.getcwd(),
                       "pid": os.getpid()}) + "\n").encode("utf-8")
    deadline = time.monotonic() + wait_s
    while True:
        sock = QLocalSocket()
        sock.connectToServer(name)
        if sock.waitForConnected(1000):
            _allow_foreground()
            sock.write(msg)
            sock.flush()
            sock.waitForBytesWritten(3000)
            reply = b""
            end = time.monotonic() + 10
            while b"\n" not in reply and time.monotonic() < end:
                if sock.waitForReadyRead(500):
                    reply += bytes(sock.readAll())
                elif sock.state() != QLocalSocket.LocalSocketState.ConnectedState:
                    break
            sock.disconnectFromServer()
            if reply.strip().startswith(b"ok"):
                return True
        sock.abort()
        if time.monotonic() > deadline:
            return False
        time.sleep(0.25)


class InstanceServer(QObject):
    """Listens for paths sent by later launches and opens them in *win*."""

    def __init__(self, win, name: str | None = None, lock: QLockFile | None = None):
        super().__init__(win)
        self.win = win
        self.name = name or instance_name()
        self.lock = lock
        self.received: list[dict] = []
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        QLocalServer.removeServer(self.name)            # a stale socket file (POSIX); no-op on Windows
        self.ok = self.server.listen(self.name)
        self.server.newConnection.connect(self._accept)

    def _accept(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            buf = bytearray()

            def ready(s=sock, b=buf):
                b.extend(bytes(s.readAll()))
                if b"\n" not in b:
                    return
                raw = bytes(b).split(b"\n", 1)[0]
                b.clear()
                try:
                    msg = json.loads(raw.decode("utf-8"))
                except ValueError:
                    s.write(b"error\n")
                    s.flush()
                    return
                s.write(b"ok\n")
                s.flush()
                QTimer.singleShot(0, lambda m=msg: self._handle(m))
            sock.readyRead.connect(ready)
            sock.disconnected.connect(sock.deleteLater)
            if sock.bytesAvailable():           # the message arrived before readyRead was connected
                ready()

    def _handle(self, msg: dict):
        self.received.append(msg)
        from .app import bring_to_front
        bring_to_front(self.win)
        line = msg.get("line")
        for p in msg.get("paths") or []:
            try:
                open_target(self.win, Path(p), line)
            except Exception as e:  # noqa: BLE001 - a bad path must not break the server
                self.win.log(f"*** cannot open {p}: {e}")
        bring_to_front(self.win)

    def close(self):
        self.server.close()
        if self.lock is not None:
            self.lock.unlock()


def start_server(win, lock: QLockFile | None = None, name: str | None = None) -> InstanceServer:
    srv = InstanceServer(win, name, lock)
    win._instance_server = srv
    if not srv.ok:
        win.log(f"[single instance] cannot listen on '{srv.name}': {srv.server.errorString()}")
    return srv


# ------------------------------------------------------------------------------------- opening a path
def _project_folder_of(path: Path) -> Path | None:
    from .model import Project
    for folder in list(path.parents)[:4]:
        if (folder / Project.FILE).is_file():
            return folder
    return None


def _is_open_project(win, folder: Path) -> bool:
    try:
        key = os.path.normcase(str(folder.resolve()))
        for st in win.project_states() if hasattr(win, "project_states") else []:
            if os.path.normcase(str(Path(st["project"].folder).resolve())) == key:
                win.activate_project(st["project"])
                return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _goto(ed, line: int | None):
    if ed is not None and line and hasattr(ed, "goto_line"):
        try:
            ed.goto_line(int(line) - 1)
        except Exception:  # noqa: BLE001
            pass


def open_file_tab(win, path: Path, line: int | None = None):
    opener = getattr(win, "open_file", None)
    if win.project is not None and callable(opener):
        return opener(str(path), line)
    ed = win.open_any_file(path)
    _goto(ed, line)
    return ed


def open_target(win, path, line: int | None = None) -> None:
    """Open *path* the way Explorer users expect (see the module doc)."""
    p = Path(path)
    try:
        p = p.resolve()
    except OSError:
        pass
    if not p.exists():
        win.statusBar().showMessage(f"Not found: {p}", 5000)
        return
    from .model import Project
    if p.is_dir():
        if (p / Project.FILE).exists() or any(p.glob("*.radsln")):
            win.open_project(p)
            return
        try:
            from .features.foreign_projects import is_foreign
            if is_foreign(p):
                win.open_project(p)
                return
        except Exception:  # noqa: BLE001
            pass
        try:                                         # any folder: a folder workspace (files, tasks, Git)
            from .foreign.vscode_folder import open_folder
            if open_folder(win, p):
                return
        except Exception as e:  # noqa: BLE001
            win.log(f"*** cannot open the folder {p}: {e}")
        return
    name = p.name.lower()
    ext = p.suffix.lower()
    if ext in PROJECT_FILE_EXTS or name == Project.FILE:
        win.open_project(p)
        return
    if ext == ".radext":
        _install_extension(win, p)
        return
    if name.endswith(DOC_EXTS):                       # a form / scene / report: open its project first
        folder = _project_folder_of(p)
        if folder is not None and not _is_open_project(win, folder):
            win.open_project(folder, activate=folder)
        if ext == ".form" and win.project is not None:
            from .features.command_palette import open_path
            open_path(win, p, line)
            return
    open_file_tab(win, p, line)


def _install_extension(win, p: Path) -> None:
    from PyQt6.QtWidgets import QMessageBox
    if QMessageBox.question(win, "Install Extension", f"Install the extension in\n{p}?\n\n"
                            "Extensions run Python code with your permissions.") != QMessageBox.StandardButton.Yes:
        return
    try:
        from . import extensions as X
        ext = X.install_from_zip(p)
        X.load(ext.id, win)
        win.log(f"[extensions] installed {ext.name} {ext.version} into {ext.path}")
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(win, "Install Extension", f"Cannot install the extension:\n{e}")


__all__ = ["instance_name", "acquire_primary", "send", "InstanceServer", "start_server", "open_target",
           "SETTING"]
