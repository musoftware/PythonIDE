"""Collaboration sessions over WebSocket (QWebSocketServer / QWebSocket - no threads, Qt event loop only).

The host is a hub: every guest talks to the host, the host relays document updates, cursors and chat to the
other guests.  Documents are pycrdt (Yjs) CRDTs, so the order updates arrive in never matters for the result;
a periodic Yjs sync step (state vector -> missing updates) repairs anything lost or left pending.

These classes know nothing about editors or windows (radide/features/live_share.py binds them to the IDE),
so two sessions can be driven from a plain script or a test.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtNetwork import QHostAddress

from . import protocol as P
from .textdoc import CRDT_ERROR, HAVE_CRDT, SharedText

try:
    from PyQt6.QtWebSockets import QWebSocket, QWebSocketProtocol, QWebSocketServer
    HAVE_WS = True
except Exception:  # noqa: BLE001 - reported by the UI
    HAVE_WS = False


def available() -> tuple[bool, str]:
    if not HAVE_WS:
        return False, "PyQt6.QtWebSockets is not available"
    if not HAVE_CRDT:
        return False, CRDT_ERROR
    return True, ""


@dataclass
class Participant:
    id: int
    name: str
    color: str
    host: bool = False
    readonly: bool = False
    path: str = ""               # file of the last cursor
    sel: tuple = (0, 0)          # anchor, head (code points)
    socket: object = None        # host side: the QWebSocket of this guest
    nonce: str = ""
    joined: bool = False
    resetting: set = field(default_factory=set)   # paths whose updates are ignored until the guest acks a reset

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "color": self.color, "host": self.host,
                "readonly": self.readonly, "path": self.path}


class SessionBase(QObject):
    participantsChanged = pyqtSignal()
    chatReceived = pyqtSignal(dict)            # {from, name, color, text, ts}
    terminalText = pyqtSignal(str)
    cursorChanged = pyqtSignal(int, str, int, int)     # peer, path, anchor, head
    docRemote = pyqtSignal(str, list)          # path, code-point ops made by others (apply to the editor)
    docOpened = pyqtSignal(str)                # a document became available here
    docReset = pyqtSignal(str)                 # the document was replaced (apply doc.value() to the editor)
    treeChanged = pyqtSignal()
    readonlyChanged = pyqtSignal(bool)
    ended = pyqtSignal(str)
    message = pyqtSignal(str)                  # status / log line for the UI

    is_host = False

    def __init__(self, name: str = "", parent=None):
        super().__init__(parent)
        self.name = name or "User"
        self.me = -1
        self.docs: dict[str, SharedText] = {}
        self.participants: dict[int, Participant] = {}
        self.tree: list[str] = []
        self.session_name = ""
        self.active = False
        self.readonly = False
        self.term_backlog = ""
        self.stats = {"sent": 0, "received": 0, "rejected_updates": 0}
        self._sync = QTimer(self)
        self._sync.setInterval(1500)
        self._sync.timeout.connect(self._sync_step)

    # ------------------------------------------------------------ shared API
    def participant(self, pid: int) -> Participant | None:
        return self.participants.get(pid)

    def color_of(self, pid: int) -> str:
        p = self.participants.get(pid)
        return p.color if p else "#888888"

    def local_edit(self, path: str, ops: list) -> None:
        """An edit made here (by the bound editor): apply to the CRDT and send the update."""
        doc = self.docs.get(path)
        if doc is None or not ops or not self.active:
            return
        upd = doc.local(ops)
        if upd:
            self._send_update(path, upd, origin=self.me)

    def send_cursor(self, path: str, anchor: int, head: int) -> None:
        if not self.active:
            return
        me = self.participants.get(self.me)
        if me is not None:
            me.path, me.sel = path, (anchor, head)
        self._send_presence({"t": "cursor", "from": self.me, "path": path, "a": int(anchor), "h": int(head)})

    def send_chat(self, text: str) -> None:
        text = (text or "").strip()
        if not text or not self.active:
            return
        me = self.participants.get(self.me)
        msg = {"t": "chat", "from": self.me, "name": me.name if me else self.name,
               "color": me.color if me else "#888", "text": text, "ts": time.time()}
        self.chatReceived.emit(msg)
        self._send_presence(msg)

    def stop(self, reason: str = "") -> None:
        raise NotImplementedError

    # ------------------------------------------------------------ helpers
    def _send(self, sock, msg: dict) -> None:
        if sock is None:
            return
        try:
            sock.sendTextMessage(P.dumps(msg))
            self.stats["sent"] += 1
        except RuntimeError:          # the socket was deleted
            pass

    def _apply_remote(self, path: str, u: bytes) -> None:
        doc = self.docs.get(path)
        if doc is None or not u:
            return
        ops = doc.remote(u)
        if ops:
            self.docRemote.emit(path, ops)

    def _on_cursor(self, msg: dict) -> None:
        p = self.participants.get(int(msg.get("from", -1)))
        if p is None or p.id == self.me:
            return
        p.path, p.sel = str(msg.get("path", "")), (int(msg.get("a", 0)), int(msg.get("h", 0)))
        self.cursorChanged.emit(p.id, p.path, p.sel[0], p.sel[1])

    def _set_participants(self, items: list[dict]) -> None:
        old = self.participants
        self.participants = {}
        for d in items:
            pid = int(d["id"])
            p = old.get(pid) or Participant(pid, d.get("name", "?"), d.get("color", "#888"))
            p.name, p.color = d.get("name", p.name), d.get("color", p.color)
            p.host, p.readonly = bool(d.get("host")), bool(d.get("readonly"))
            self.participants[pid] = p
        self.participantsChanged.emit()

    def _sync_step(self) -> None:
        pass


# ============================================================================ host
class CollabHost(SessionBase):
    """Share a folder.  host.start(root) -> invite link via host.link(); guests join with a CollabGuest."""
    is_host = True
    saveRequested = pyqtSignal(str)            # a guest pressed Save on a shared file

    def __init__(self, name: str = "", parent=None):
        super().__init__(name, parent)
        self.server = None
        self.root: Path | None = None
        self.code = ""
        self.port = 0
        self.password = ""
        self.guests_readonly = False
        self.text_provider = None              # callable(rel) -> str | None (an open editor's text)
        self._next_id = 1

    # ------------------------------------------------------------ lifecycle
    def start(self, root, port: int = P.DEFAULT_PORT, password: str = "", guests_readonly: bool = False,
              session_name: str = "") -> bool:
        ok, why = available()
        if not ok:
            self.message.emit(why)
            return False
        self.root = Path(root).resolve()
        self.password = password or ""
        self.guests_readonly = bool(guests_readonly)
        self.code = P.new_code()
        self.session_name = session_name or self.root.name
        self.server = QWebSocketServer("RADIDE-Collab", QWebSocketServer.SslMode.NonSecureMode, self)
        tried = [port + i for i in range(10)] + [0] if port else [0]
        for p in tried:
            if self.server.listen(QHostAddress(QHostAddress.SpecialAddress.AnyIPv4), p):
                break
        else:
            self.message.emit(f"Cannot listen: {self.server.errorString()}")
            return False
        self.port = self.server.serverPort()
        self.server.newConnection.connect(self._on_new_connection)
        self.me = 0
        self.participants = {0: Participant(0, self.name, P.color_for(0), host=True, joined=True)}
        self.tree = P.file_tree(self.root)
        self.active = True
        self.participantsChanged.emit()
        self.treeChanged.emit()
        self.message.emit(f"Collaboration session started on port {self.port}")
        return True

    def link(self, host: str | None = None) -> str:
        return P.invite_link(host or P.lan_addresses()[0], self.port, self.code)

    def stop(self, reason: str = "The host ended the session") -> None:
        if not self.active:
            return
        self.active = False
        for p in list(self.participants.values()):
            if p.socket is not None:
                self._send(p.socket, {"t": "end", "reason": reason})
                try:
                    p.socket.flush()
                    p.socket.close()
                except RuntimeError:
                    pass
        if self.server is not None:
            self.server.close()
            self.server.deleteLater()
            self.server = None
        self.participants = {}
        self.participantsChanged.emit()
        self.ended.emit(reason)

    # ------------------------------------------------------------ documents
    def ensure_doc(self, rel: str) -> SharedText | None:
        doc = self.docs.get(rel)
        if doc is not None:
            return doc
        text = None
        if callable(self.text_provider):
            try:
                text = self.text_provider(rel)
            except Exception:  # noqa: BLE001
                text = None
        if text is None:
            path = P.safe_rel(self.root, rel)
            if path is None or not path.is_file() or path.stat().st_size > P.MAX_FILE:
                return None
            raw = path.read_bytes()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("cp1252", errors="replace")
            text = text.replace("\r\n", "\n")
        doc = self.docs[rel] = SharedText.new(text)
        return doc

    def save_to_disk(self, rel: str) -> bool:
        doc, path = self.docs.get(rel), P.safe_rel(self.root, rel)
        if doc is None or path is None:
            return False
        path.write_text(doc.value(), encoding="utf-8")
        return True

    def refresh_tree(self) -> None:
        self.tree = P.file_tree(self.root)
        self._broadcast({"t": "tree", "tree": self.tree})
        self.treeChanged.emit()

    # ------------------------------------------------------------ permissions / terminal
    def set_readonly(self, pid: int, ro: bool) -> None:
        p = self.participants.get(pid)
        if p is None or p.host:
            return
        p.readonly = bool(ro)
        self._send(p.socket, {"t": "perm", "readonly": p.readonly})
        self._broadcast_participants()

    def set_all_readonly(self, ro: bool) -> None:
        self.guests_readonly = bool(ro)
        for p in list(self.participants.values()):
            if not p.host:
                self.set_readonly(p.id, ro)

    def send_terminal(self, text: str) -> None:
        if not text or not self.active:
            return
        self.term_backlog = (self.term_backlog + text)[-20000:]
        self._broadcast({"t": "term", "text": text})

    def kick(self, pid: int) -> None:
        p = self.participants.get(pid)
        if p is not None and p.socket is not None:
            self._send(p.socket, {"t": "end", "reason": "The host removed you from the session"})
            p.socket.close()

    # ------------------------------------------------------------ network
    def _broadcast(self, msg: dict, skip: int | None = None, only_joined: bool = True) -> None:
        text = P.dumps(msg)
        for p in list(self.participants.values()):
            if p.socket is None or p.id == skip or (only_joined and not p.joined):
                continue
            try:
                p.socket.sendTextMessage(text)
                self.stats["sent"] += 1
            except RuntimeError:
                pass

    def _broadcast_participants(self) -> None:
        items = [p.public() for p in self.participants.values() if p.joined]
        self._broadcast({"t": "participants", "list": items})
        self.participantsChanged.emit()

    def _send_update(self, path: str, upd: bytes, origin: int) -> None:
        self._broadcast({"t": "update", "path": path, "u": P.b64(upd)}, skip=origin)

    def _send_presence(self, msg: dict) -> None:
        self._broadcast(msg, skip=self.me)

    def _on_new_connection(self) -> None:
        while self.server is not None and self.server.hasPendingConnections():
            sock = self.server.nextPendingConnection()
            pid = self._next_id
            self._next_id += 1
            p = Participant(pid, "guest", P.color_for(pid), socket=sock, nonce=P.new_nonce(),
                            readonly=self.guests_readonly)
            self.participants[pid] = p
            sock.textMessageReceived.connect(lambda text, pid=pid: self._on_message(pid, text))
            sock.disconnected.connect(lambda pid=pid: self._on_gone(pid))
            self._send(sock, {"t": "challenge", "nonce": p.nonce, "password": bool(self.password),
                              "version": P.VERSION, "session": self.session_name})

    def _reject(self, p: Participant, reason: str) -> None:
        self._send(p.socket, {"t": "reject", "reason": reason})
        self.message.emit(f"Join refused ({reason})")
        sock = p.socket
        self.participants.pop(p.id, None)
        p.socket = None
        QTimer.singleShot(200, lambda: _close(sock))

    def _on_gone(self, pid: int) -> None:
        p = self.participants.pop(pid, None)
        if p is None:
            return
        if p.joined:
            try:
                self.message.emit(f"{p.name} left the session")
                self._broadcast_participants()
            except RuntimeError:      # the host object is already gone (sockets closing at shutdown)
                return
        try:
            p.socket.deleteLater()
        except (RuntimeError, AttributeError):
            pass

    def _on_message(self, pid: int, text: str) -> None:
        p = self.participants.get(pid)
        msg = P.loads(text)
        if p is None or msg is None:
            return
        self.stats["received"] += 1
        t = msg["t"]
        if not p.joined:
            if t != "hello":
                return
            if str(msg.get("code", "")).upper() != self.code:
                return self._reject(p, "bad-code")
            if self.password and not P.check_auth(self.password, p.nonce, str(msg.get("auth", ""))):
                return self._reject(p, "bad-password")
            p.name = (str(msg.get("name") or "") or f"Guest {pid}")[:40]
            p.joined = True
            self._send(p.socket, {"t": "welcome", "id": pid, "color": p.color, "session": self.session_name,
                                  "root": self.root.name, "tree": self.tree, "readonly": p.readonly,
                                  "participants": [x.public() for x in self.participants.values() if x.joined],
                                  "term": self.term_backlog,
                                  "cursors": [{"from": x.id, "path": x.path, "a": x.sel[0], "h": x.sel[1]}
                                              for x in self.participants.values() if x.path]})
            self.message.emit(f"{p.name} joined the session")
            self._broadcast_participants()
            return
        if t == "update":
            path, u = str(msg.get("path", "")), P.unb64(msg.get("u", ""))
            if path not in self.docs:
                return
            if p.readonly or path in p.resetting:
                self.stats["rejected_updates"] += 1
                if path not in p.resetting:          # undo the guest's local change: send a fresh document
                    p.resetting.add(path)
                    self._send(p.socket, {"t": "doc", "path": path, "u": P.b64(self.docs[path].state()),
                                          "reset": True})
                return
            self._apply_remote(path, u)
            self._broadcast({"t": "update", "path": path, "u": msg.get("u", "")}, skip=pid)
        elif t == "doc-ack":
            p.resetting.discard(str(msg.get("path", "")))
        elif t == "open":
            path = str(msg.get("path", ""))
            doc = self.ensure_doc(path)
            if doc is None:
                self._send(p.socket, {"t": "error", "path": path, "text": f"Cannot open {path}"})
            else:
                self._send(p.socket, {"t": "doc", "path": path, "u": P.b64(doc.state()), "reset": False})
                self.docOpened.emit(path)
        elif t == "sv":
            path = str(msg.get("path", ""))
            doc = self.docs.get(path)
            if doc is None or path in p.resetting:
                return
            missing = doc.missing_for(P.unb64(msg.get("sv", "")))
            if missing:
                self._send(p.socket, {"t": "update", "path": path, "u": P.b64(missing)})
            if not msg.get("reply") and not p.readonly:
                self._send(p.socket, {"t": "sv", "path": path, "sv": P.b64(doc.state_vector()), "reply": True})
        elif t == "cursor":
            msg["from"] = pid
            self._on_cursor(msg)
            self._broadcast(msg, skip=pid)
        elif t == "chat":
            out = {"t": "chat", "from": pid, "name": p.name, "color": p.color,
                   "text": str(msg.get("text", ""))[:4000], "ts": time.time()}
            self.chatReceived.emit(out)
            self._broadcast(out, skip=pid)
        elif t == "save":
            path = str(msg.get("path", ""))
            if path in self.docs and not p.readonly:
                self.saveRequested.emit(path)
        elif t == "bye":
            _close(p.socket)


def _close(sock) -> None:
    try:
        if sock is not None:
            sock.close()
    except RuntimeError:
        pass


# ============================================================================ guest
class CollabGuest(SessionBase):
    joined = pyqtSignal()
    rejected = pyqtSignal(str)
    docError = pyqtSignal(str, str)

    def __init__(self, name: str = "", parent=None):
        super().__init__(name, parent)
        self.sock = None
        self.password = ""
        self.code = ""
        self.address = ("", 0)
        self.root_name = ""
        self._opening: set[str] = set()
        self._closing = False

    def join(self, host: str, port: int, code: str, password: str = "") -> bool:
        ok, why = available()
        if not ok:
            self.message.emit(why)
            self.rejected.emit(why)
            return False
        self.address, self.code, self.password = (host, int(port)), code.upper(), password or ""
        self.sock = QWebSocket("", QWebSocketProtocol.Version.VersionLatest, self)
        self.sock.textMessageReceived.connect(self._on_message)
        self.sock.disconnected.connect(self._on_disconnected)
        err = getattr(self.sock, "errorOccurred", None) or getattr(self.sock, "error", None)
        if err is not None:
            err.connect(lambda *_: self.message.emit(f"Connection error: {self.sock.errorString()}"))
        self.sock.open(QUrl(f"ws://{host}:{int(port)}/"))
        return True

    def join_link(self, link: str, password: str = "") -> bool:
        parts = P.parse_invite(link)
        if parts is None:
            self.rejected.emit("bad-link")
            return False
        return self.join(parts[0], parts[1], parts[2], password)

    def open(self, path: str) -> None:
        if path in self.docs:
            self.docOpened.emit(path)
        elif path not in self._opening:
            self._opening.add(path)
            self._send(self.sock, {"t": "open", "path": path})

    def save(self, path: str) -> None:
        self._send(self.sock, {"t": "save", "path": path})

    def stop(self, reason: str = "You left the session") -> None:
        if self.sock is None:
            return
        was = self.active
        self.active = False
        self._closing = True
        self._sync.stop()
        if was:
            self._send(self.sock, {"t": "bye"})
            self.sock.flush()
        sock, self.sock = self.sock, None
        _close(sock)
        if was:
            self.ended.emit(reason)

    leave = stop

    # ------------------------------------------------------------ network
    def _send_update(self, path: str, upd: bytes, origin: int) -> None:
        self._send(self.sock, {"t": "update", "path": path, "u": P.b64(upd)})

    def _send_presence(self, msg: dict) -> None:
        self._send(self.sock, msg)

    def _sync_step(self) -> None:
        if not self.active:
            return
        for path, doc in list(self.docs.items()):
            self._send(self.sock, {"t": "sv", "path": path, "sv": P.b64(doc.state_vector())})

    def _on_disconnected(self) -> None:
        if self.active and not self._closing:
            self.active = False
            self._sync.stop()
            self.ended.emit("The connection to the host was lost")
        elif not self.active and self.me < 0 and not self._closing:
            self.rejected.emit("unreachable")

    def _on_message(self, text: str) -> None:
        msg = P.loads(text)
        if msg is None:
            return
        self.stats["received"] += 1
        t = msg["t"]
        if t == "challenge":
            self.session_name = str(msg.get("session", ""))
            self._send(self.sock, {"t": "hello", "code": self.code, "name": self.name,
                                   "auth": P.auth(self.password, str(msg.get("nonce", "")))})
        elif t == "reject":
            self._closing = True
            self.rejected.emit(str(msg.get("reason", "rejected")))
        elif t == "welcome":
            self.me = int(msg["id"])
            self.session_name = str(msg.get("session", ""))
            self.root_name = str(msg.get("root", ""))
            self.tree = list(msg.get("tree", []))
            self.readonly = bool(msg.get("readonly"))
            self.term_backlog = str(msg.get("term", ""))
            self.active = True
            self._set_participants(msg.get("participants", []))
            for c in msg.get("cursors", []):
                self._on_cursor(c)
            self._sync.start()
            self.joined.emit()
            self.treeChanged.emit()
            self.readonlyChanged.emit(self.readonly)
        elif t == "doc":
            path = str(msg.get("path", ""))
            self._opening.discard(path)
            reset = bool(msg.get("reset")) or path in self.docs
            self.docs[path] = SharedText.from_state(P.unb64(msg.get("u", "")))
            if reset:
                self._send(self.sock, {"t": "doc-ack", "path": path})
                self.docReset.emit(path)
            else:
                self.docOpened.emit(path)
        elif t == "update":
            self._apply_remote(str(msg.get("path", "")), P.unb64(msg.get("u", "")))
        elif t == "sv":
            path = str(msg.get("path", ""))
            doc = self.docs.get(path)
            if doc is not None and not self.readonly:
                missing = doc.missing_for(P.unb64(msg.get("sv", "")))
                if missing:
                    self._send(self.sock, {"t": "update", "path": path, "u": P.b64(missing)})
        elif t == "error":
            path = str(msg.get("path", ""))
            self._opening.discard(path)
            self.docError.emit(path, str(msg.get("text", "")))
        elif t == "cursor":
            self._on_cursor(msg)
        elif t == "chat":
            self.chatReceived.emit(msg)
        elif t == "term":
            text = str(msg.get("text", ""))
            self.term_backlog = (self.term_backlog + text)[-20000:]
            self.terminalText.emit(text)
        elif t == "tree":
            self.tree = list(msg.get("tree", []))
            self.treeChanged.emit()
        elif t == "participants":
            self._set_participants(msg.get("list", []))
            me = self.participants.get(self.me)
            if me is not None and me.readonly != self.readonly:
                self.readonly = me.readonly
                self.readonlyChanged.emit(self.readonly)
        elif t == "perm":
            self.readonly = bool(msg.get("readonly"))
            self.readonlyChanged.emit(self.readonly)
        elif t == "end":
            self._closing = True
            self.active = False
            self._sync.stop()
            self.ended.emit(str(msg.get("reason", "The host ended the session")))
