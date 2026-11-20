"""Real-time collaboration (Live Share style) for RAD IDE.

    protocol.py  wire format, invite links, password challenge (HMAC-SHA256), shareable file tree
    textdoc.py   SharedText: one file = one pycrdt (Yjs) CRDT document, code-point API
    ot.py        Jupiter OT for the asynchronous Python <-> Monaco page link of one editor
    session.py   CollabHost (QWebSocketServer hub) / CollabGuest (QWebSocket) - no UI
    binding.py   bind a Monaco or built-in editor to a shared document; remote cursors as decorations

The IDE integration (Share menu, Live Share window, follow mode, chat, shared terminal) is
radide/features/live_share.py.
"""
from .protocol import DEFAULT_PORT, invite_link, parse_invite
from .session import CollabGuest, CollabHost, available

__all__ = ["DEFAULT_PORT", "invite_link", "parse_invite", "CollabGuest", "CollabHost", "available"]
