"""Text tables (.tbl) used for game-text translation: which byte (or byte sequence) is which character.

Accepted lines (the common "Thingy"-style format):

==================  ===============================================================
``41=A``            one byte -> text (any length of hex: ``8140=あ`` is two bytes)
``/FF=<end>``       end-of-string code (the text after ``=`` is its label, default ``<end>``)
``*FE``             line break (decoded as a newline; ``*FE=<br>`` keeps a label)
``$80=<name>``      control code with a label (kept as-is in dumped text)
``# comment``       ignored, as are empty lines and ``;`` comments
==================  ===============================================================

Bytes that are not in the table are dumped as ``<$XX>`` and encoded back the same way, so a dump/insert
round trip never loses data.  Encoding uses the longest matching text first (``<end>``, multi-letter
entries such as ``the``), then single characters.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

RAW = re.compile(r"<\$([0-9A-Fa-f]{2})>")


@dataclass
class TextTable:
    entries: dict[bytes, str] = field(default_factory=dict)
    ends: dict[bytes, str] = field(default_factory=dict)
    breaks: dict[bytes, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    name: str = ""

    # ------------------------------------------------------------ parse / write
    @classmethod
    def parse(cls, text: str, name: str = "") -> "TextTable":
        t = cls(name=name)
        for n, raw in enumerate(text.splitlines(), 1):
            line = raw.rstrip("\r\n")
            if not line.strip() or line.lstrip()[0] in "#;":
                continue
            kind = ""
            if line[0] in "/*$":
                kind, line = line[0], line[1:]
            key, sep, val = line.partition("=")
            key = key.strip()
            if not re.fullmatch(r"(?:[0-9A-Fa-f]{2})+", key):
                t.errors.append(f"line {n}: '{raw.strip()}' - the left side must be hex bytes")
                continue
            b = bytes.fromhex(key)
            if kind == "/":
                t.ends[b] = val or "<end>"
            elif kind == "*":
                t.breaks[b] = val or "\n"
            else:
                if not sep:
                    t.errors.append(f"line {n}: '{raw.strip()}' - missing '='")
                    continue
                if b in t.entries:
                    t.errors.append(f"line {n}: {key} is defined twice")
                t.entries[b] = val
        return t

    @classmethod
    def load(cls, path) -> "TextTable":
        raw = Path(path).read_bytes()
        for enc in ("utf-8-sig", "utf-16", "cp1256", "shift_jis", "latin-1"):
            try:
                text = raw.decode(enc)
                if enc == "utf-16" and not raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                    continue
                return cls.parse(text, Path(path).name)
            except UnicodeDecodeError:
                continue
        return cls.parse(raw.decode("latin-1"), Path(path).name)

    def dumps(self) -> str:
        lines = []
        for b, v in sorted(self.entries.items(), key=lambda kv: (len(kv[0]), kv[0])):
            lines.append(f"{b.hex().upper()}={v}")
        for b, v in sorted(self.ends.items()):
            lines.append(f"/{b.hex().upper()}={v}")
        for b, v in sorted(self.breaks.items()):
            lines.append(f"*{b.hex().upper()}" + ("" if v == "\n" else f"={v}"))
        return "\n".join(lines) + "\n"

    def save(self, path) -> None:
        Path(path).write_text(self.dumps(), encoding="utf-8")

    # ------------------------------------------------------------ queries
    def _all(self) -> dict[bytes, tuple[str, str]]:
        d = {b: ("char", v) for b, v in self.entries.items()}
        d.update({b: ("break", v) for b, v in self.breaks.items()})
        d.update({b: ("end", v) for b, v in self.ends.items()})
        return d

    def max_key(self) -> int:
        return max((len(b) for b in self._all()), default=1)

    def duplicates(self) -> list[str]:
        """Texts that more than one code produces (encoding picks the first)."""
        seen: dict[str, bytes] = {}
        dup = []
        for b, v in self.entries.items():
            if v in seen and len(v) > 0:
                dup.append(f"'{v}' = {seen[v].hex().upper()} and {b.hex().upper()}")
            seen.setdefault(v, b)
        return dup

    # ------------------------------------------------------------ decode
    def decode(self, data: bytes, start: int = 0, end: int | None = None,
               stop_at_end: bool = True) -> tuple[str, int, bool]:
        """Text from ``data[start:end]``: returns (text, bytes consumed incl. the end code, end code seen)."""
        end = len(data) if end is None else min(end, len(data))
        allk = self._all()
        maxk = self.max_key()
        out: list[str] = []
        i = start
        while i < end:
            for k in range(min(maxk, end - i), 0, -1):
                hit = allk.get(bytes(data[i:i + k]))
                if hit is not None:
                    kind, val = hit
                    i += k
                    if kind == "end":
                        out.append(val)
                        if stop_at_end:
                            return "".join(out), i - start, True
                    elif kind == "break":
                        out.append(val if val == "\n" else val + "\n")
                    else:
                        out.append(val)
                    break
            else:
                out.append(f"<${data[i]:02X}>")
                i += 1
        return "".join(out), i - start, False

    # ------------------------------------------------------------ encode
    def encode(self, text: str) -> tuple[bytes, list[str]]:
        """Bytes for *text*; returns (bytes, problems) - a character that is not in the table is a problem."""
        rev: dict[str, bytes] = {}
        for b, v in self.entries.items():
            rev.setdefault(v, b)
        for b, v in self.breaks.items():
            rev.setdefault(v if v == "\n" else v + "\n", b)
            rev.setdefault(v, b)
        for b, v in self.ends.items():
            rev.setdefault(v, b)
        keys = sorted((k for k in rev if k), key=len, reverse=True)
        maxlen = len(keys[0]) if keys else 1
        out = bytearray()
        problems: list[str] = []
        i = 0
        text = text.replace("\r\n", "\n")
        while i < len(text):
            m = RAW.match(text, i)
            if m:
                out.append(int(m.group(1), 16))
                i = m.end()
                continue
            for n in range(min(maxlen, len(text) - i), 0, -1):
                b = rev.get(text[i:i + n])
                if b is not None:
                    out += b
                    i += n
                    break
            else:
                ch = text[i]
                problems.append(f"'{ch}' (U+{ord(ch):04X}) is not in the table")
                i += 1
        return bytes(out), problems

    def end_code(self) -> bytes | None:
        return next(iter(self.ends), None)

    def end_label(self) -> str:
        return next(iter(self.ends.values()), "<end>")


def ascii_table() -> TextTable:
    """A starting table: printable ASCII 20-7E, 0A = line break, 00 = end."""
    t = TextTable(name="ascii.tbl")
    for b in range(0x20, 0x7F):
        t.entries[bytes([b])] = chr(b)
    t.breaks[b"\x0a"] = "\n"
    t.ends[b"\x00"] = "<end>"
    return t
