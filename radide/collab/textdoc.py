"""One shared text file = one CRDT document (pycrdt, the Rust port of Yjs).

pycrdt counts Text positions in UTF-8 bytes; this wrapper talks Unicode code points (what Python strings
and the OT layer use) and converts at the boundary, so Arabic, accents and emoji are safe.

    st = SharedText.new("print('hi')")          # the host creates a document from a file
    upd = st.local([("i", 0, "# ")])           # local edit -> update bytes for the network
    other = SharedText.from_state(st.state())   # a guest starts from the full state
    ops = other.remote(upd)                     # remote update -> code-point ops for the editor
"""
from __future__ import annotations

try:
    import pycrdt as Y
    HAVE_CRDT = True
    CRDT_ERROR = ""
except Exception as _e:  # noqa: BLE001 - reported by the UI
    Y = None
    HAVE_CRDT = False
    CRDT_ERROR = f"pycrdt is not installed ({_e}); run: pip install pycrdt"

from . import ot


def _b2c(buf: bytes, byte_pos: int) -> int:
    return len(buf[:byte_pos].decode("utf-8", errors="ignore"))


class SharedText:
    def __init__(self):
        if not HAVE_CRDT:
            raise RuntimeError(CRDT_ERROR)
        self.doc = Y.Doc()
        self.text = Y.Text()
        self.doc["text"] = self.text
        self._shadow = ""                  # code-point mirror of self.text
        self._muted = False
        self._remote_ops: ot.Ops = []
        self._pending: list[bytes] = []
        self.doc.observe(self._on_update)
        self.text.observe(self._on_event)

    # ------------------------------------------------------------ construction
    @classmethod
    def new(cls, content: str) -> "SharedText":
        st = cls()
        if content:
            st.local([("i", 0, content)])
        st._pending.clear()
        return st

    @classmethod
    def from_state(cls, state: bytes) -> "SharedText":
        st = cls()
        st.remote(state)
        return st

    # ------------------------------------------------------------ queries
    def value(self) -> str:
        return self._shadow

    def state(self) -> bytes:
        """The whole document as one update (for a guest that opens the file)."""
        return self.doc.get_update()

    def state_vector(self) -> bytes:
        """Yjs sync step 1: what this replica has integrated."""
        return self.doc.get_state()

    def missing_for(self, state_vector: bytes) -> bytes:
        """Yjs sync step 2: everything the replica with `state_vector` has not integrated yet.  Applying it
        also completes updates that yrs left pending (an update can be integrated only partially when it
        arrives before the updates it depends on)."""
        return self.doc.get_update(state_vector)

    # ------------------------------------------------------------ edits
    def local(self, ops: ot.Ops) -> bytes:
        """Apply code-point ops made here; returns the update to broadcast (b"" when nothing changed)."""
        self._pending.clear()
        self._muted = True
        try:
            with self.doc.transaction():
                for op in ops:
                    p =max(0, min(op[1], len(self._shadow)))
                    bpos = len(self._shadow[:p].encode("utf-8"))
                    if op[0] == "i":
                        if op[2]:
                            self.text.insert(bpos, op[2])
                            self._shadow = self._shadow[:p] + op[2] + self._shadow[p:]
                    else:
                        n = max(0, min(op[2], len(self._shadow) - p))
                        if n:
                            blen = len(self._shadow[p:p + n].encode("utf-8"))
                            del self.text[bpos:bpos + blen]
                            self._shadow = self._shadow[:p] + self._shadow[p + n:]
        finally:
            self._muted = False
        upd = b"".join(self._pending) if len(self._pending) == 1 else (
            Y.merge_updates(*self._pending) if self._pending else b"")
        self._pending.clear()
        return upd

    def remote(self, update: bytes) -> ot.Ops:
        """Apply an update from another IDE; returns the code-point ops it made to this text."""
        before = self._shadow
        self._remote_ops = []
        self._pending.clear()
        self.doc.apply_update(update)
        self._pending.clear()
        ops, self._remote_ops = self._remote_ops, []
        cur = str(self.text)
        if cur != self._shadow or ot.apply(before, ops) != cur:   # never trust a drifted mirror: resync
            ops = ot.diff(before, cur)
            self._shadow = cur
        return ops

    # ------------------------------------------------------------ pycrdt callbacks
    def _on_update(self, event) -> None:
        self._pending.append(event.update)

    def _on_event(self, event) -> None:
        if self._muted:
            return
        buf = bytearray(self._shadow.encode("utf-8"))
        pos = 0
        for d in event.delta:
            if "retain" in d:
                pos += int(d["retain"])
            elif "insert" in d:
                s = d["insert"]
                if not isinstance(s, str):
                    continue
                sb = s.encode("utf-8")
                self._remote_ops.append(("i", _b2c(bytes(buf), pos), s))
                buf[pos:pos] = sb
                pos += len(sb)
            elif "delete" in d:
                n = int(d["delete"])
                cp = _b2c(bytes(buf), pos)
                cn = len(bytes(buf[pos:pos + n]).decode("utf-8", errors="ignore"))
                if cn:
                    self._remote_ops.append(("d", cp, cn))
                del buf[pos:pos + n]
        self._shadow = buf.decode("utf-8", errors="replace")
