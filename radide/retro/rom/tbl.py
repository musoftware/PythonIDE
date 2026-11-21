"""Character tables (.tbl) - how a game stores its text. The common ROM-hacking format:

    41=A            one byte -> text
    8081=the        several bytes -> text (dictionary / DTE entries)
    /FF=<end>       end-of-string code ("/XX" or "/XX=text")
    *FE=<br>        line break code ("*XX" or "*XX=text")
    $XX=...         same as XX=... (some tools write a $)
    ; or # comments, blank lines ignored

``Table.decode`` is greedy (longest byte sequence first), ``Table.encode`` greedy on the text side.
"""
from __future__ import annotations

import re
from pathlib import Path


class Table:
    def __init__(self):
        self.to_text: dict[bytes, str] = {}
        self.to_bytes: dict[str, bytes] = {}
        self.end_codes: set[bytes] = set()
        self.newline_codes: set[bytes] = set()
        self.max_key = 1
        self.max_text = 1
        self.name = ""
        self.errors: list[str] = []

    # ------------------------------------------------------------------ io
    @classmethod
    def parse(cls, text: str, name: str = "") -> "Table":
        t = cls()
        t.name = name
        for n, raw in enumerate(text.splitlines(), 1):
            line = raw.rstrip("\r\n")
            if not line.strip() or line.lstrip().startswith((";", "#", "//")):
                continue
            kind = ""
            if line[0] in "/*":
                kind, line = line[0], line[1:]
            if line.startswith("$"):
                line = line[1:]
            key, eq, value = line.partition("=")
            key = key.strip()
            if not re.fullmatch(r"(?:[0-9A-Fa-f]{2})+", key):
                t.errors.append(f"line {n}: bad hex code {key!r}")
                continue
            code = bytes.fromhex(key)
            if kind == "/":
                t.end_codes.add(code)
                value = value if eq else "<end>"
            elif kind == "*":
                t.newline_codes.add(code)
                value = value if eq else "\n"
            elif not eq:
                t.errors.append(f"line {n}: missing '='")
                continue
            value = value.replace("\\n", "\n")
            t.add(code, value)
        return t

    @classmethod
    def load(cls, path) -> "Table":
        p = Path(path)
        raw = p.read_bytes()
        for enc in ("utf-8-sig", "shift_jis", "cp1252"):
            try:
                return cls.parse(raw.decode(enc), p.name)
            except UnicodeDecodeError:
                continue
        return cls.parse(raw.decode("latin-1"), p.name)

    @classmethod
    def ascii(cls) -> "Table":
        t = cls()
        t.name = "ASCII"
        for c in range(0x20, 0x7F):
            t.add(bytes([c]), chr(c))
        return t

    def add(self, code: bytes, value: str) -> None:
        self.to_text[code] = value
        if value and value not in self.to_bytes:
            self.to_bytes[value] = code
        self.max_key = max(self.max_key, len(code))
        self.max_text = max(self.max_text, len(value))

    def dumps(self) -> str:
        lines = []
        for code, value in sorted(self.to_text.items()):
            prefix = "/" if code in self.end_codes else "*" if code in self.newline_codes else ""
            lines.append(f"{prefix}{code.hex().upper()}={value.replace(chr(10), chr(92) + 'n')}")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------ conversion
    def char_at(self, data, offset: int) -> tuple[str, int]:
        """(text, byte length) of the longest entry at *offset*; ("", 1) when nothing matches."""
        for k in range(min(self.max_key, len(data) - offset), 0, -1):
            v = self.to_text.get(bytes(data[offset:offset + k]))
            if v is not None:
                return v, k
        return "", 1

    def single(self, byte: int) -> str | None:
        return self.to_text.get(bytes([byte]))

    def decode(self, data, start: int = 0, end: int | None = None, stop_at_end: bool = False,
               unknown: str = "[{:02X}]") -> str:
        end = len(data) if end is None else min(end, len(data))
        out = []
        i = start
        while i < end:
            text, k = self.char_at(data, i)
            code = bytes(data[i:i + k])
            if text == "" and code not in self.to_text:
                out.append(unknown.format(data[i]))
                i += 1
                continue
            out.append(text)
            i += k
            if stop_at_end and code in self.end_codes:
                break
        return "".join(out)

    def encode(self, text: str) -> bytes | None:
        """Bytes for *text* (greedy longest match; ``[XX]`` writes a raw byte). None when a character has no
        code."""
        out = bytearray()
        i = 0
        while i < len(text):
            m = re.match(r"\[([0-9A-Fa-f]{2})\]", text[i:])
            if m:
                out.append(int(m.group(1), 16))
                i += 4
                continue
            for k in range(min(self.max_text, len(text) - i), 0, -1):
                code = self.to_bytes.get(text[i:i + k])
                if code is not None:
                    out += code
                    i += k
                    break
            else:
                return None
        return bytes(out)

    def find_strings(self, data, min_len: int = 4, limit: int = 2000) -> list[tuple[int, str]]:
        """(offset, text) of runs of >= *min_len* table characters (a quick "dump script")."""
        out = []
        i, n = 0, len(data)
        while i < n and len(out) < limit:
            j = i
            chars = []
            while j < n:
                text, k = self.char_at(data, j)
                if not text or bytes(data[j:j + k]) in self.end_codes:
                    break
                chars.append(text)
                j += k
            if len(chars) >= min_len:
                out.append((i, "".join(chars)))
                i = j
            else:
                i += 1
        return out


def relative_search(data, word: str, limit: int = 50) -> list[tuple[int, int]]:
    """Relative search: find *word* stored with an unknown letter encoding where letters keep their order
    (A=n, B=n+1, ...). Returns (offset, value of the first letter) hits; the hex editor then offers a table
    built from the difference."""
    letters = [ord(c) for c in word]
    if len(letters) < 3:
        return []
    diffs = bytes((letters[k + 1] - letters[k]) & 0xFF for k in range(len(letters) - 1))
    out = []
    d = bytes(data)
    n = len(d)
    # differences of consecutive bytes, compared with the word's differences
    deltas = bytes((d[i + 1] - d[i]) & 0xFF for i in range(n - 1)) if n > 1 else b""
    start = 0
    while len(out) < limit:
        j = deltas.find(diffs, start)
        if j < 0:
            break
        out.append((j, d[j]))
        start = j + 1
    return out


def table_from_relative(first_byte: int, first_char: str) -> Table:
    """A table for A-Z / a-z placed relative to a relative-search hit."""
    t = Table()
    base = first_byte - (ord(first_char.upper()) - ord("A")) if first_char.isupper() else \
        first_byte - (ord(first_char) - ord("a"))
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if first_char.isupper() else "abcdefghijklmnopqrstuvwxyz"
    for k, ch in enumerate(alphabet):
        v = base + k
        if 0 <= v <= 0xFF:
            t.add(bytes([v]), ch)
    t.name = "relative"
    return t


__all__ = ["Table", "relative_search", "table_from_relative"]
