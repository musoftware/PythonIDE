"""The automation channel's local server: a QLocalServer (a named pipe on Windows) speaking JSON lines.

Request  (one line):  {"id": 1, "cmd": "trigger", "args": {"path": "File/New Project..."},
                       "token": "<secret>", "async": false}
Response (one line):  {"id": 1, "ok": true, "result": ...}
                      {"id": 1, "ok": false, "error": "...", "trace": "..."}

"async": true schedules the command on the GUI thread and answers {"ok": true, "result": {"job": N}} at
once - for anything that may open a modal dialog (dialog.exec() would otherwise hold the answer back).
The ``job`` command returns {"done": bool, "ok": bool, "result"/"error"}.

Every request must carry the token when the channel has one; commands registered with token=True
(exec / eval) are refused on a channel started without a token.
"""
from __future__ import annotations

import hmac
import itertools
import json
import os
import traceback

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from .registry import COMMANDS, AutomationError, Context


def _jsonable(v, depth=0):
    if depth > 8:
        return repr(v)
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    if isinstance(v, dict):
        return {str(k): _jsonable(x, depth + 1) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_jsonable(x, depth + 1) for x in v]
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return repr(v)


class AutomationServer(QObject):
    def __init__(self, win, app, name: str, token: str = ""):
        super().__init__(app)
        self.name = name
        self.token = token
        self.ctx = Context(win=win, app=app, server=self)
        self.jobs: dict[int, dict] = {}
        self._ids = itertools.count(1)
        self._buffers: dict[QLocalSocket, bytes] = {}
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        QLocalServer.removeServer(name)
        if not self.server.listen(name):
            raise AutomationError(f"cannot listen on {name!r}: {self.server.errorString()}")
        self.server.newConnection.connect(self._on_connection)

    # ------------------------------------------------------------------ sockets
    def _on_connection(self):
        while self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            self._buffers[sock] = b""
            sock.readyRead.connect(lambda s=sock: self._on_ready(s))
            sock.disconnected.connect(lambda s=sock: self._drop(s))

    def _drop(self, sock):
        self._buffers.pop(sock, None)
        sock.deleteLater()

    def _on_ready(self, sock):
        if sock not in self._buffers:
            return
        self._buffers[sock] += bytes(sock.readAll())
        while sock in self._buffers and b"\n" in self._buffers[sock]:
            line, rest = self._buffers[sock].split(b"\n", 1)
            self._buffers[sock] = rest
            if line.strip():
                reply = self.handle_line(line)
                if sock in self._buffers and sock.state() == QLocalSocket.LocalSocketState.ConnectedState:
                    sock.write((json.dumps(reply, ensure_ascii=False) + "\n").encode("utf-8"))
                    sock.flush()

    # ------------------------------------------------------------------ dispatch
    def handle_line(self, line: bytes) -> dict:
        try:
            req = json.loads(line.decode("utf-8"))
        except ValueError as e:
            return {"id": None, "ok": False, "error": f"bad JSON: {e}"}
        rid = req.get("id")
        if self.token and not hmac.compare_digest(str(req.get("token", "")), self.token):
            return {"id": rid, "ok": False, "error": "bad or missing token"}
        name = req.get("cmd", "")
        args = req.get("args") or {}
        cmd = COMMANDS.get(name)
        if cmd is None:
            return {"id": rid, "ok": False, "error": f"unknown command {name!r} (see 'help')"}
        if cmd.token and not self.token:
            return {"id": rid, "ok": False, "error": f"{name!r} needs a channel started with RADIDE_AUTOMATION=<token>"}
        self.ctx.has_token = bool(self.token)
        if req.get("async"):
            jid = next(self._ids)
            self.jobs[jid] = {"done": False, "cmd": name}
            QTimer.singleShot(0, lambda: self.jobs.__setitem__(jid, self.run(name, cmd, args)))
            return {"id": rid, "ok": True, "result": {"job": jid}}
        out = self.run(name, cmd, args)
        out["id"] = rid
        return out

    def run(self, name, cmd, args) -> dict:
        try:
            res = cmd.func(self.ctx, **args)
            return {"done": True, "ok": True, "result": _jsonable(res), "cmd": name}
        except Exception as e:  # noqa: BLE001 - every error goes back to the client
            return {"done": True, "ok": False, "cmd": name, "error": f"{type(e).__name__}: {e}",
                    "trace": traceback.format_exc()[-4000:]}


def write_ready_file(path: str, name: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"name": name, "pid": os.getpid()}, f)
    except OSError:
        pass
