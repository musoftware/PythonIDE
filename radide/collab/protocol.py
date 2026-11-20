"""Wire format of a collaboration session (one JSON object per WebSocket text message).

Handshake
    host  -> guest  {"t": "challenge", "nonce", "password": bool, "version"}
    guest -> host   {"t": "hello", "code", "name", "auth": hmac_sha256(password, nonce) | ""}
    host  -> guest  {"t": "welcome", "id", "color", "session", "root", "tree", "participants", "readonly",
                     "term"}  |  {"t": "reject", "reason": "bad-password" | "bad-code" | ...}
Documents (pycrdt / Yjs updates, base64 in "u")
    guest -> host   {"t": "open", "path"}               host -> guest {"t": "doc", "path", "u", "reset": bool}
    any   -> any    {"t": "update", "path", "u"}        (the host relays guests' updates)
    any   -> any    {"t": "sv", "path", "sv", "reply"}  (Yjs sync step 1; the answer is an "update")
    guest -> host   {"t": "save", "path"}
Presence and the rest
    any   -> host   {"t": "cursor", "path", "a", "h"}   host relays with "from" (code points)
    any   -> host   {"t": "chat", "text"}               host relays with "from", "name", "color", "ts"
    host  -> guest  {"t": "term", "text"} | {"t": "tree", "tree"} | {"t": "participants", "list"}
    host  -> guest  {"t": "perm", "readonly"}
    guest -> host   {"t": "bye"}                         host -> guest {"t": "end", "reason"}
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from pathlib import Path

VERSION = 1
DEFAULT_PORT = 47820
SCHEME = "radide-collab"
COLORS = ["#e8590c", "#1c7ed6", "#2f9e44", "#ae3ec9", "#f08c00", "#0c8599", "#e03131", "#5f3dc4",
          "#66a80f", "#d6336c"]
SKIP_DIRS = {".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "__pycache__", ".idea", ".vs",
             "bin", "obj", "build", "dist", ".mypy_cache", ".pytest_cache", "vendor", ".radide"}
MAX_TREE = 3000
MAX_FILE = 4 * 1024 * 1024


def color_for(index: int) -> str:
    return COLORS[index % len(COLORS)]


def new_code() -> str:
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def new_nonce() -> str:
    return secrets.token_hex(16)


def auth(password: str, nonce: str) -> str:
    if not password:
        return ""
    return hmac.new(password.encode("utf-8"), nonce.encode("ascii"), hashlib.sha256).hexdigest()


def check_auth(password: str, nonce: str, given: str) -> bool:
    return hmac.compare_digest(auth(password, nonce), given or "")


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii")) if text else b""


def dumps(msg: dict) -> str:
    return json.dumps(msg, ensure_ascii=False, separators=(",", ":"))


def loads(text: str) -> dict | None:
    try:
        msg = json.loads(text)
    except (TypeError, ValueError):
        return None
    return msg if isinstance(msg, dict) and isinstance(msg.get("t"), str) else None


def invite_link(host: str, port: int, code: str) -> str:
    return f"{SCHEME}://{host}:{port}/{code}"


def parse_invite(text: str) -> tuple[str, int, str] | None:
    """'radide-collab://192.168.1.5:47820/ABC123', 'ws://host:port/CODE' or 'host:port/CODE' -> parts."""
    s = (text or "").strip()
    s = re.sub(r"^[a-zA-Z][\w+.-]*://", "", s)
    m = re.match(r"^\[?([^\]/\s]+?)\]?(?::(\d+))?/+([A-Za-z0-9]+)/?$", s)
    if not m:
        return None
    return m.group(1), int(m.group(2) or DEFAULT_PORT), m.group(3).upper()


def lan_addresses() -> list[str]:
    """IPv4 addresses other IDEs on the network can reach (first = best guess)."""
    found: list[tuple[int, str]] = []
    virtual = re.compile(r"vEthernet|Hyper-V|VirtualBox|VMware|WSL|Docker|Loopback|TAP|Bluetooth", re.I)
    try:
        from PyQt6.QtNetwork import QAbstractSocket, QNetworkInterface
        for iface in QNetworkInterface.allInterfaces():
            flags = iface.flags()
            if not (flags & QNetworkInterface.InterfaceFlag.IsUp) or flags & QNetworkInterface.InterfaceFlag.IsLoopBack:
                continue
            is_virtual = bool(virtual.search(iface.humanReadableName() + " " + iface.name()))
            for e in iface.addressEntries():
                ip = e.ip()
                if ip.protocol() == QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
                    a = ip.toString()
                    if a.startswith("169.254."):
                        continue
                    rank = (0 if a.startswith("192.168.") else 1 if a.startswith("10.") else
                            2 if re.match(r"172\.(1[6-9]|2\d|3[01])\.", a) else 3)
                    found.append((rank + (10 if is_virtual else 0), a))
    except Exception:  # noqa: BLE001
        pass
    found.sort()
    return [a for _r, a in found] or ["127.0.0.1"]


def file_tree(root: Path) -> list[str]:
    """Relative POSIX paths of the shareable files under root (folders that never matter are skipped)."""
    root = Path(root)
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        rel = Path(dirpath).relative_to(root)
        for f in sorted(filenames):
            out.append((rel / f).as_posix())
            if len(out) >= MAX_TREE:
                return out
    return out


def safe_rel(root: Path, rel: str) -> Path | None:
    """root/rel only when it stays inside root (a guest must never read files outside the shared folder)."""
    if not rel or "\x00" in rel:
        return None
    try:
        p = (Path(root) / rel).resolve()
        p.relative_to(Path(root).resolve())
    except (ValueError, OSError):
        return None
    return p


def rel_of(root: Path, path) -> str | None:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except (ValueError, OSError):
        return None
