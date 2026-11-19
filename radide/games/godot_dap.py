"""F5 debugging of Godot 4 game projects (GDScript) through Godot's own Debug Adapter (DAP).

Godot 4's editor has a DAP server (Editor Settings > Network > Debug Adapter, port 6006).  It also runs in a
headless editor, so RAD IDE starts ``godot --headless --editor --path <project>`` (no editor window), connects
to 127.0.0.1:6006 over TCP and sends ``launch`` - the editor then starts the game (a normal window) with its
debugger attached: breakpoints (F9 in .gd files), Continue / Step Into / Over / Out, Locals / Members / Globals,
the call stack and Immediate-window evaluation.  When the user's own Godot editor is already open on port 6006
the session uses that editor instead (and leaves it running).

``GodotDapSession`` has the signals and methods of radide.debugger.Session (via radide.dap.DapSession).
"""
from __future__ import annotations

import os
import socket
import subprocess
from pathlib import Path

from PyQt6.QtCore import QProcess, QTimer
from PyQt6.QtNetwork import QAbstractSocket, QTcpSocket

from ..dap import ADAPTERS, DapSession

DAP_HOST = "127.0.0.1"
DAP_PORT = 6006
CONNECT_TIMEOUT_MS = 90000          # first start of a project imports its assets
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def console_exe(godot: str) -> str:
    """godot_console.exe next to godot.exe (its output reaches pipes on Windows); else *godot* itself."""
    p = Path(godot)
    for name in (p.stem + "_console.exe", "godot_console.exe"):
        c = p.with_name(name)
        if c.exists():
            return str(c)
    try:                                   # WinGet "Links" are symlinks to the real package folder
        real = p.resolve()
        if real != p:
            return console_exe(str(real))
    except OSError:
        pass
    return str(p)


def port_open(port: int = DAP_PORT) -> bool:
    try:
        with socket.create_connection((DAP_HOST, port), timeout=0.3):
            return True
    except OSError:
        return False


# the DAP request arguments (DapSession builds them through ADAPTERS)
ADAPTERS.setdefault("godot", (lambda: ["godot"], lambda prog, args, cwd, env: {
    "project": cwd, "scene": "main", "platform": "host", "noDebug": False}))


class GodotDapSession(DapSession):
    """DapSession over TCP to a (headless) Godot editor."""

    def __init__(self, godot: str, folder: Path, breakpoints, env: dict | None = None, parent=None):
        super().__init__("godot", "", [], Path(folder), env, breakpoints, parent)
        self.godot = godot
        self.argv = [console_exe(godot), "--headless", "--editor", "--path", str(self.cwd)]
        try:                                  # the editor's stdout is its log, not the DAP stream
            self.proc.readyReadStandardOutput.disconnect(self._read)
        except TypeError:
            pass
        self.sock = QTcpSocket(self)
        self.sock.readyRead.connect(self._read)
        self.sock.connected.connect(self._on_connected)
        self.sock.disconnected.connect(lambda: self._finish(0))
        self.sock.errorOccurred.connect(self._on_sock_error)
        self.proc.readyReadStandardOutput.connect(self._editor_output)
        self._own_editor = False
        self._waited = 0
        self._poll = QTimer(self)
        self._poll.setInterval(400)
        self._poll.timeout.connect(self._try_connect)
        self._started = False

    # ------------------------------------------------------------ transport
    def start(self):
        if port_open():
            self.output.emit(f"Using the Godot editor that is already open (debug adapter on port {DAP_PORT}).\n")
        else:
            self._own_editor = True
            self.output.emit("Starting Godot's debug adapter (headless editor)...\n")
            self.proc.setProgram(self.argv[0])
            self.proc.setArguments(self.argv[1:])
            self.proc.start()                 # Qt starts console programs without a window from a GUI app
            if not self.proc.waitForStarted(10000):
                self.failed.emit(f"cannot start {self.argv[0]}")
                self.finished.emit(1)
                return
        self._poll.start()
        self._try_connect()

    def _try_connect(self):
        if self.sock.state() != QAbstractSocket.SocketState.UnconnectedState:
            return
        self._waited += self._poll.interval()
        if self._own_editor and self.proc.state() == QProcess.ProcessState.NotRunning:
            self._poll.stop()
            self.failed.emit("the Godot editor exited before its debug adapter started")
            self._finish(1)
            return
        if self._waited > CONNECT_TIMEOUT_MS:
            self._poll.stop()
            self.failed.emit(f"Godot's debug adapter did not answer on port {DAP_PORT}")
            self.stop()
            return
        if port_open():
            self.sock.connectToHost(DAP_HOST, DAP_PORT)

    def _on_connected(self):
        self._poll.stop()
        self._started = True
        self._request("initialize", {"clientID": "radide", "adapterID": "godot", "linesStartAt1": True,
                                     "columnsStartAt1": True, "pathFormat": "path",
                                     "supportsRunInTerminalRequest": False}, self._on_initialize)

    def _on_sock_error(self, _err):
        if not self._started:
            self.sock.abort()                 # not listening yet: the poll timer retries

    def _send(self, msg):
        import json
        body = json.dumps(msg).encode("utf-8")
        if self.sock.state() == QAbstractSocket.SocketState.ConnectedState:
            self.sock.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
            self.sock.flush()

    def _read(self):
        import json
        self._buf += bytes(self.sock.readAll())
        while True:
            end = self._buf.find(b"\r\n\r\n")
            if end < 0:
                return
            length = 0
            for line in self._buf[:end].split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":")[1])
            if len(self._buf) < end + 4 + length:
                return
            body, self._buf = self._buf[end + 4:end + 4 + length], self._buf[end + 4 + length:]
            try:
                self._dispatch(json.loads(body))
            except ValueError:
                continue

    def _editor_output(self):
        text = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        lines = [ln for ln in text.splitlines() if "ERROR" in ln or "SCRIPT ERROR" in ln or "Parse Error" in ln]
        if lines and not self.user_stopped:
            self.output.emit("\n".join(lines) + "\n")

    def _read_stderr(self):
        self._editor_output()

    # ------------------------------------------------------------ Session API
    def running(self) -> bool:
        return not self._done and (self.sock.state() != QAbstractSocket.SocketState.UnconnectedState or
                                   self.proc.state() != QProcess.ProcessState.NotRunning or self._poll.isActive())

    def _finish(self, code):
        if self._done:
            return
        super()._finish(code)
        self._poll.stop()
        QTimer.singleShot(300, self._shutdown_editor)

    def _shutdown_editor(self):
        if self.sock.state() != QAbstractSocket.SocketState.UnconnectedState:
            self.sock.abort()
        if self._own_editor and self.proc.state() != QProcess.ProcessState.NotRunning:
            pid = int(self.proc.processId() or 0)
            if os.name == "nt" and pid:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True,
                               creationflags=NO_WINDOW, timeout=15)
            if self.proc.state() != QProcess.ProcessState.NotRunning:
                self.proc.kill()
                self.proc.waitForFinished(3000)

    def stop(self):
        self.user_stopped = True
        if self.sock.state() == QAbstractSocket.SocketState.ConnectedState:
            self._request("disconnect", {"terminateDebuggee": True})
            self.sock.waitForBytesWritten(1000)
        self._finish(0)
        self._shutdown_editor()


def start_debugging(win, godot: str) -> GodotDapSession:
    """F5 for a Godot project: export the scenes, start the session, connect it to the IDE like Session."""
    from . import godot_export
    folder = Path(win.project.folder)
    godot_export.export_project(folder)
    win.output.clear()
    win.locals.clear()
    win.callstack.clear()
    win.dock_output.show()
    win.dock_output.raise_()
    win.log(f"------ Debug (Godot debug adapter): {folder.name} ------")
    s = GodotDapSession(godot, folder, win._all_breakpoints(), None, win)
    s.break_on_exception = False          # Godot's DAP has no exception filters
    s.output.connect(win._append_output)
    s.stopped.connect(win._on_stopped)
    s.resumed.connect(win._on_resumed)
    s.evalResult.connect(lambda txt: win.immediate.show_result(txt))
    s.finished.connect(win._on_finished)
    s.failed.connect(lambda err: win.log(f"*** Error: {err}"))
    win.session = s
    s.start()
    win.statusBar().showMessage("Debugging (Godot)...")
    win._update_actions()
    return s


__all__ = ["GodotDapSession", "start_debugging", "console_exe", "port_open", "DAP_PORT"]
