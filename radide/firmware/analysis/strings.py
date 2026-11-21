"""Strings and identification text in firmware: ASCII and UTF-16 (LE / BE) strings, and strings that *look like*
part / software / hardware numbers or version tags. The patterns are generic shapes (letters + digit groups,
long digit runs, dotted versions); RAD IDE does not know or decode any manufacturer's numbering scheme and shows
these only as hints for the user's own notes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# generic "identifier-like" shapes (no manufacturer database)
ID_PATTERNS: list[tuple[str, re.Pattern]] = [
    # letter + groups of digits separated by spaces: "A 123 456 78 90", "B 12 345 678"
    ("part-number-like", re.compile(r"\b[A-Z]{1,2} ?\d{3} \d{3} \d{2} \d{2}(?: \d{2})?\b")),
    ("part-number-like", re.compile(r"\b[A-Z]{1,2} \d{2,3} \d{3} \d{2,3}\b")),
    # digit groups "0 123 456 789" / "1 039 S12 345"
    ("part-number-like", re.compile(r"\b\d \d{3} [A-Z0-9]{3} \d{3}\b")),
    # long digit run (10-12) often used as software / hardware numbers
    ("number-like", re.compile(r"(?<![0-9A-Za-z])\d{10,12}(?![0-9A-Za-z])")),
    # alphanumeric with dashes / dots: "8E0-907-401", "12.34.56", "V1.02"
    ("part-number-like", re.compile(r"\b[0-9A-Z]{2,4}[-.][0-9A-Z]{3}[-.][0-9A-Z]{3}(?:[-.][0-9A-Z]{1,3})?\b")),
    ("version-like", re.compile(r"\b[Vv](?:er(?:sion)?)?[ ._]?\d{1,3}\.\d{1,3}(?:\.\d{1,4})?[a-z]?\b")),
    ("date-like", re.compile(r"\b(?:19|20)\d{2}[-/.](?:0[1-9]|1[0-2])[-/.](?:0[1-9]|[12]\d|3[01])\b")),
    ("build-tag-like", re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) [ 0-3]\d (?:19|20)\d{2}\b")),
]


@dataclass
class FoundString:
    offset: int
    text: str
    encoding: str          # "ascii" | "utf-16le" | "utf-16be"
    tags: tuple[str, ...] = ()

    @property
    def size(self) -> int:
        return len(self.text) * (1 if self.encoding == "ascii" else 2)


_ASCII = re.compile(rb"[\x20-\x7e\t]{%d,}")
_U16LE = re.compile(rb"(?:[\x20-\x7e]\x00){%d,}")
_U16BE = re.compile(rb"(?:\x00[\x20-\x7e]){%d,}")


def tags_for(text: str) -> tuple[str, ...]:
    out = []
    for name, rx in ID_PATTERNS:
        if rx.search(text) and name not in out:
            out.append(name)
    return tuple(out)


def find_strings(data: bytes, min_len: int = 5, utf16: bool = True, limit: int = 200000) -> list[FoundString]:
    out: list[FoundString] = []
    for m in re.finditer(_ASCII.pattern % min_len, data):
        t = m.group().decode("ascii")
        if t.strip():
            out.append(FoundString(m.start(), t, "ascii", tags_for(t)))
            if len(out) >= limit:
                break
    if utf16:
        le_spans: list[tuple[int, int]] = []
        for rx, enc in ((_U16LE, "utf-16le"), (_U16BE, "utf-16be")):
            for m in re.finditer(rx.pattern % min_len, data):
                start, end = m.start(), m.end()
                if enc == "utf-16be" and any(a <= start + 1 and end - 1 <= b + 1 and start < b for a, b in le_spans):
                    continue        # the same UTF-16LE text seen one byte later
                t = m.group().decode(enc, "replace")
                if t.strip():
                    out.append(FoundString(start, t, enc, tags_for(t)))
                    if enc == "utf-16le":
                        le_spans.append((start, end))
    out.sort(key=lambda s: s.offset)
    return out


def identification(strings: list[FoundString]) -> list[FoundString]:
    """Only the strings with an identifier-like tag (shown at the top of the Strings view)."""
    return [s for s in strings if s.tags]
