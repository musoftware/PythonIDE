"""The byte buffer behind the hex editor: overwrite / insert / delete with undo-redo, a save point, bookmarks
and search (hex with ``??`` / ``?`` nibble wildcards, text in any codec or through a .tbl table). Pure Python.

Multi-megabyte files are fine: the data is one ``bytearray`` (C memmove for inserts), an undo step keeps only
the bytes it changed, and search compiles to a ``re`` byte pattern (C speed).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Edit:
    offset: int
    old: bytes
    new: bytes
    merge_key: str = ""              # typing in the same place merges into one undo step
    cursor_before: int = 0
    cursor_after: int = 0


@dataclass
class Bookmark:
    offset: int
    length: int = 1
    name: str = ""
    color: str = "#F5A623"


class HexBuffer:
    def __init__(self, data: bytes = b"", path: Path | None = None):
        self.data = bytearray(data)
        self.path = Path(path) if path else None
        self.undo_stack: list[Edit] = []
        self.redo_stack: list[Edit] = []
        self._save_point = 0          # len(undo_stack) at the last save (-1 = never reachable)
        self.bookmarks: list[Bookmark] = []
        self.listeners: list = []     # callables(offset, old_len, new_len)

    # ------------------------------------------------------------------ io
    @classmethod
    def load(cls, path) -> "HexBuffer":
        p = Path(path)
        return cls(p.read_bytes(), p)

    def save(self, path=None) -> Path:
        p = Path(path) if path else self.path
        if p is None:
            raise ValueError("no file name")
        tmp = p.with_name(p.name + ".radtmp")
        tmp.write_bytes(bytes(self.data))
        tmp.replace(p)
        self.path = p
        self._save_point = len(self.undo_stack)
        return p

    def __len__(self) -> int:
        return len(self.data)

    @property
    def modified(self) -> bool:
        return self._save_point != len(self.undo_stack)

    def mark_saved(self) -> None:
        self._save_point = len(self.undo_stack)

    # ------------------------------------------------------------------ edits
    def _notify(self, offset: int, old_len: int, new_len: int) -> None:
        for fn in list(self.listeners):
            fn(offset, old_len, new_len)

    def _do(self, e: Edit) -> None:
        self.data[e.offset:e.offset + len(e.old)] = e.new
        self._notify(e.offset, len(e.old), len(e.new))

    def _push(self, e: Edit) -> None:
        self._do(e)
        top = self.undo_stack[-1] if self.undo_stack else None
        if (e.merge_key and top is not None and top.merge_key == e.merge_key and
                len(self.undo_stack) != self._save_point and
                top.offset + len(top.new) == e.offset):
            # contiguous typing: one undo step
            self.undo_stack[-1] = Edit(top.offset, top.old + e.old, top.new + e.new, e.merge_key,
                                       top.cursor_before, e.cursor_after)
        else:
            if self._save_point > len(self.undo_stack):
                self._save_point = -1
            self.undo_stack.append(e)
        self.redo_stack.clear()

    def replace(self, offset: int, new: bytes, length: int | None = None, merge_key: str = "",
                cursor: int | None = None) -> None:
        """Replace *length* bytes (default len(new): overwrite) at *offset* with *new*. Writing past the end
        grows the file."""
        offset = max(0, min(offset, len(self.data)))
        length = len(new) if length is None else length
        old = bytes(self.data[offset:offset + length])
        if old == new and length == len(new):
            return
        after = offset + len(new) if cursor is None else cursor
        self._push(Edit(offset, old, bytes(new), merge_key, offset, after))

    def overwrite(self, offset: int, new: bytes, merge_key: str = "") -> None:
        self.replace(offset, new, None, merge_key)

    def insert(self, offset: int, new: bytes, merge_key: str = "") -> None:
        self.replace(offset, new, 0, merge_key)

    def delete(self, offset: int, length: int) -> None:
        if length > 0:
            self.replace(offset, b"", length, cursor=offset)

    def fill(self, offset: int, length: int, pattern: bytes) -> None:
        if length > 0 and pattern:
            data = (pattern * (length // len(pattern) + 1))[:length]
            self.replace(offset, data, length)

    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        return bool(self.redo_stack)

    def undo(self) -> Edit | None:
        if not self.undo_stack:
            return None
        e = self.undo_stack.pop()
        self.data[e.offset:e.offset + len(e.new)] = e.old
        self._notify(e.offset, len(e.new), len(e.old))
        self.redo_stack.append(e)
        return e

    def redo(self) -> Edit | None:
        if not self.redo_stack:
            return None
        e = self.redo_stack.pop()
        self._do(e)
        self.undo_stack.append(e)
        return e

    def read(self, offset: int, length: int) -> bytes:
        return bytes(self.data[offset:offset + length])

    # ------------------------------------------------------------------ bookmarks
    def toggle_bookmark(self, offset: int, name: str = "") -> bool:
        for b in self.bookmarks:
            if b.offset == offset:
                self.bookmarks.remove(b)
                return False
        self.bookmarks.append(Bookmark(offset, 1, name or f"Bookmark {len(self.bookmarks) + 1}"))
        self.bookmarks.sort(key=lambda b: b.offset)
        return True

    def next_bookmark(self, offset: int, backward: bool = False) -> Bookmark | None:
        if not self.bookmarks:
            return None
        if backward:
            prev = [b for b in self.bookmarks if b.offset < offset]
            return prev[-1] if prev else self.bookmarks[-1]
        nxt = [b for b in self.bookmarks if b.offset > offset]
        return nxt[0] if nxt else self.bookmarks[0]

    # ------------------------------------------------------------------ search
    def find(self, pattern: "re.Pattern[bytes]", start: int, backward: bool = False,
             wrap: bool = True) -> tuple[int, int] | None:
        """(offset, length) of the next match from *start* (exclusive when backward)."""
        data = self.data
        if not backward:
            m = pattern.search(data, start)
            if m is None and wrap and start > 0:
                m = pattern.search(data, 0)
            return (m.start(), m.end() - m.start()) if m else None
        last = None
        for m in pattern.finditer(data, 0, max(0, start)):
            last = m
        if last is None and wrap:
            for m in pattern.finditer(data, max(0, start)):
                last = m
        if last is None:
            return None
        return last.start(), last.end() - last.start()

    def find_all(self, pattern: "re.Pattern[bytes]", limit: int = 100_000) -> list[tuple[int, int]]:
        out = []
        for m in pattern.finditer(self.data):
            out.append((m.start(), m.end() - m.start()))
            if len(out) >= limit:
                break
        return out

    def replace_all(self, pattern: "re.Pattern[bytes]", new: bytes) -> int:
        """Replace every match (one undo step per match, newest first so offsets stay valid)."""
        hits = self.find_all(pattern)
        for off, length in reversed(hits):
            self.replace(off, new, length)
        return len(hits)


# ============================================================================ patterns
class PatternError(ValueError):
    pass


_HEX_TOKEN = re.compile(r"\?\?|\*|[0-9A-Fa-f?]{2}")


def hex_pattern(text: str) -> "re.Pattern[bytes]":
    """``"A9 ?? 8D 0? 20"`` -> a byte regex. ``??`` = any byte, ``A?`` / ``?F`` = a nibble wildcard,
    ``*`` = any run of bytes (shortest). Spaces / commas / ``0x`` / ``$`` are ignored."""
    cleaned = re.sub(r"0x|\$|[\s,]", "", text.strip(), flags=re.I)
    if not cleaned:
        raise PatternError("empty hex pattern")
    pos = 0
    parts: list[bytes] = []
    for m in _HEX_TOKEN.finditer(cleaned):
        if m.start() != pos:
            raise PatternError(f"not a hex byte: {cleaned[pos:m.start() + 2]!r}")
        tok = m.group(0)
        pos = m.end()
        if tok == "??":
            parts.append(b".")
        elif tok == "*":
            parts.append(b".*?")
        elif "?" in tok:
            hi, lo = tok[0], tok[1]
            if hi == "?":
                vals = [(h << 4) | int(lo, 16) for h in range(16)]
            else:
                vals = [(int(hi, 16) << 4) | v for v in range(16)]
            parts.append(b"[" + b"".join(re.escape(bytes([v])) for v in vals) + b"]")
        else:
            parts.append(re.escape(bytes([int(tok, 16)])))
    if pos != len(cleaned):
        raise PatternError(f"odd number of hex digits near {cleaned[pos:]!r}")
    return re.compile(b"".join(parts), re.S)


def parse_hex_bytes(text: str) -> bytes:
    """``"A9 01 8D"`` -> bytes (no wildcards)."""
    cleaned = re.sub(r"0x|\$|[\s,]", "", text.strip(), flags=re.I)
    if len(cleaned) % 2 or not re.fullmatch(r"[0-9A-Fa-f]*", cleaned):
        raise PatternError("hex bytes expected, e.g. A9 01 8D 00 20")
    return bytes.fromhex(cleaned)


def text_pattern(text: str, encoding: str = "latin-1", case_sensitive: bool = True, table=None,
                 wildcards: bool = False) -> "re.Pattern[bytes]":
    """Text search. *table* (a :class:`~radide.retro.rom.tbl.Table`) encodes game text; *wildcards*: ``?`` = any
    character (one byte), ``*`` = any run."""
    if not text:
        raise PatternError("empty search text")
    pieces: list[bytes] = []
    chunks = re.split(r"([?*])", text) if wildcards else [text]
    for ch in chunks:
        if not ch:
            continue
        if wildcards and ch == "?":
            pieces.append(b".")
            continue
        if wildcards and ch == "*":
            pieces.append(b".*?")
            continue
        if table is not None:
            enc = table.encode(ch)
            if enc is None:
                raise PatternError(f"the table has no code for some characters of {ch!r}")
            pieces.append(re.escape(enc))
            continue
        try:
            enc = ch.encode(encoding)
        except (UnicodeEncodeError, LookupError) as e:
            raise PatternError(str(e)) from e
        if not case_sensitive and encoding.lower().replace("-", "") in ("latin1", "ascii", "cp1252", "cp437"):
            pieces.append(b"".join(b"[" + re.escape(bytes([c])) + re.escape(bytes([c ^ 0x20])) + b"]"
                                   if 65 <= (c & 0xDF) <= 90 else re.escape(bytes([c])) for c in enc))
        else:
            pieces.append(re.escape(enc))
    return re.compile(b"".join(pieces), re.S)


__all__ = ["Bookmark", "Edit", "HexBuffer", "PatternError", "hex_pattern", "parse_hex_bytes", "text_pattern"]
