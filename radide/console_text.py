"""Decoding the output of child processes (compilers, build tools, user programs) without ever crashing.

Tools write UTF-8 (gcc, cargo, go, node, Python with PYTHONIOENCODING), the console's OEM code page (MSVC cl /
link, cmd, many old tools: cp437 / cp720 Arabic / cp850 ...) or the ANSI code page (cp1252 / cp1256 Arabic).
``decode(data)`` tries UTF-8 first, then the OEM and ANSI code pages of this PC, and finally UTF-8 with
replacement characters - it never raises. No Qt import."""
from __future__ import annotations

import locale
import os


def _oem() -> str:
    if os.name == "nt":
        try:
            import ctypes
            return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
        except Exception:  # noqa: BLE001
            pass
    return ""


def _ansi() -> str:
    if os.name == "nt":
        try:
            import ctypes
            return f"cp{ctypes.windll.kernel32.GetACP()}"
        except Exception:  # noqa: BLE001
            pass
    return locale.getpreferredencoding(False) or ""


def candidates() -> list[str]:
    out = []
    for enc in ("utf-8", _ansi(), _oem()):
        if enc and enc.lower() not in [e.lower() for e in out]:
            out.append(enc)
    return out


def _score(text: str) -> int:
    """How much *text* looks like words: letters, digits, spaces and ASCII punctuation count; box drawing,
    control characters and symbols do not (cp1256 Arabic read as cp720 gives box characters)."""
    return sum(1 for ch in text if ch.isalnum() or ch.isspace() or (ch.isascii() and ch.isprintable()))


def decode(data: bytes | str | None, encodings: list[str] | None = None) -> str:
    """*data* as text: UTF-8 when it is valid UTF-8, else the code page (ANSI / OEM of this PC, or
    *encodings*) whose result looks most like text; never raises (U+FFFD as the last resort)."""
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    encs = encodings or candidates()
    best, best_score = None, -1
    for enc in encs:
        try:
            text = data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        if enc.replace("-", "").replace("_", "").lower() in ("utf8", "utf8sig"):
            return text
        sc = _score(text)
        if sc > best_score:
            best, best_score = text, sc
    return best if best is not None else data.decode("utf-8", errors="replace")


class StreamDecoder:
    """Incremental decode() for output that arrives in pieces: a UTF-8 character split between two reads is
    kept until its last byte arrives; other text (a code page) is decoded at once."""

    def __init__(self):
        self._buf = b""

    def feed(self, data: bytes) -> str:
        buf = self._buf + bytes(data)
        self._buf = b""
        try:
            return buf.decode("utf-8")
        except UnicodeDecodeError as e:
            if e.reason == "unexpected end of data" and e.start >= len(buf) - 3:
                try:
                    text = buf[:e.start].decode("utf-8")
                    self._buf = buf[e.start:]
                    return text
                except UnicodeDecodeError:
                    pass
        return decode(buf)

    def flush(self) -> str:
        chunk, self._buf = self._buf, b""
        return decode(chunk)


__all__ = ["StreamDecoder", "candidates", "decode"]
