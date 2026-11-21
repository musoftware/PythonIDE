"""ZX Spectrum .tap files: a BASIC loader + one CODE block (no Qt in here).

``make_tap(code, start, entry, name)`` -> bytes of a tape that, after LOAD "", runs
``10 CLEAR VAL "start-1": LOAD "" CODE : RANDOMIZE USR VAL "entry"``.
Numbers are written as VAL "..." so the BASIC line needs no hidden 5-byte floating point forms.
"""
from __future__ import annotations

TOK_CLEAR, TOK_VAL, TOK_LOAD, TOK_CODE, TOK_RANDOMIZE, TOK_USR = 0xFD, 0xB0, 0xEF, 0xAF, 0xF9, 0xC0


def _block(flag: int, payload: bytes) -> bytes:
    body = bytes([flag]) + payload
    chk = 0
    for b in body:
        chk ^= b
    body += bytes([chk])
    return len(body).to_bytes(2, "little") + body


def _header(kind: int, name: str, length: int, p1: int, p2: int) -> bytes:
    nm = name.encode("ascii", "replace")[:10].ljust(10, b" ")
    return _block(0x00, bytes([kind]) + nm + length.to_bytes(2, "little") + (p1 & 0xFFFF).to_bytes(2, "little") +
                  (p2 & 0xFFFF).to_bytes(2, "little"))


def basic_loader(start: int, entry: int) -> bytes:
    line = (bytes([TOK_CLEAR, TOK_VAL]) + f'"{start - 1}"'.encode() + b":" + bytes([TOK_LOAD]) + b'""' +
            bytes([TOK_CODE]) + b":" + bytes([TOK_RANDOMIZE, TOK_USR, TOK_VAL]) + f'"{entry}"'.encode() + b"\r")
    return (10).to_bytes(2, "big") + len(line).to_bytes(2, "little") + line


def make_tap(code: bytes, start: int, entry: int | None = None, name: str = "game") -> bytes:
    entry = start if entry is None else entry
    prog = basic_loader(start, entry)
    return (_header(0, name, len(prog), 10, len(prog)) + _block(0xFF, prog) +
            _header(3, name, len(code), start, 32768) + _block(0xFF, code))
