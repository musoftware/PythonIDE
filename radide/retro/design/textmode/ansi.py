"""ANSI / ASCII art files <-> CellBuffer. No Qt in here (PNG export is in glyphs.py).

* ``.ANS``  ANSI escape sequences (SGR colours, cursor movement, clear) with an optional SAUCE record
            (title, author, group, width, iCE colours) - read and written.
* ``.BIN``  raw video memory (character, attribute) per cell, width from SAUCE (default 80 columns).
* ``.TXT``  plain text in CP437 (UTF-8 is accepted when the file is valid UTF-8 and not plain ASCII).

The ANSI reader uses deferred wrapping (a full 80-column line followed by CR LF is one line, as in
ANSI art viewers) and grows the canvas downward as needed.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path

from .buffer import CellBuffer
from .cp437 import decode, encode

CGA_TO_ANSI = [0, 4, 2, 6, 1, 5, 3, 7]
ANSI_TO_CGA = [0, 4, 2, 6, 1, 5, 3, 7]          # the mapping is its own inverse
ESC = 0x1B
SUB = 0x1A
MAX_ROWS = 2000


@dataclass
class Sauce:
    title: str = ""
    author: str = ""
    group: str = ""
    date: str = ""
    width: int = 80
    rows: int = 25
    ice_colors: bool = False
    font: str = "IBM VGA"
    data_type: int = 1          # 1 character, 5 binary text
    file_type: int = 1          # character: 0 ASCII, 1 ANSi ; binary text: width / 2
    comments: tuple = ()

    def to_bytes(self, file_size: int) -> bytes:
        def f(s: str, n: int) -> bytes:
            return encode(s)[:n].ljust(n, b" ")
        date = self.date or _dt.date.today().strftime("%Y%m%d")
        tflags = 1 if self.ice_colors else 0
        tinfo1, tinfo2 = (self.width, self.rows) if self.data_type == 1 else (0, 0)
        out = bytearray(b"SAUCE00")
        out += f(self.title, 35) + f(self.author, 20) + f(self.group, 20) + f(date, 8)
        out += file_size.to_bytes(4, "little") + bytes([self.data_type, self.file_type])
        out += tinfo1.to_bytes(2, "little") + tinfo2.to_bytes(2, "little") + bytes(4)
        out += bytes([len(self.comments), tflags]) + encode(self.font)[:22].ljust(22, b"\0")
        assert len(out) == 128
        comnt = b""
        if self.comments:
            comnt = b"COMNT" + b"".join(f(c, 64) for c in self.comments)
        return comnt + bytes(out)


def read_sauce(data: bytes) -> tuple[Sauce | None, bytes]:
    """(SAUCE record or None, the file content without SAUCE / COMNT / EOF)."""
    if len(data) >= 128 and data[-128:-121] == b"SAUCE00":
        r = data[-128:]

        def s(a: int, b: int) -> str:
            return decode(r[a:b]).rstrip(" \0")
        sc = Sauce(title=s(7, 42), author=s(42, 62), group=s(62, 82), date=s(82, 90))
        sc.data_type, sc.file_type = r[94], r[95]
        sc.width = int.from_bytes(r[96:98], "little") or 80
        sc.rows = int.from_bytes(r[98:100], "little") or 25
        ncom = r[104]
        sc.ice_colors = bool(r[105] & 1)
        sc.font = r[106:128].split(b"\0")[0].decode("latin-1", "replace") or "IBM VGA"
        if sc.data_type == 5:
            sc.width = max(1, sc.file_type) * 2
        body = data[:-128]
        if ncom:
            start = len(body) - 5 - 64 * ncom
            if start >= 0 and body[start:start + 5] == b"COMNT":
                sc.comments = tuple(decode(body[start + 5 + 64 * i:start + 69 + 64 * i]).rstrip()
                                    for i in range(ncom))
                body = body[:start]
        if body.endswith(bytes([SUB])):
            body = body[:-1]
        return sc, body
    i = data.find(bytes([SUB]))
    return None, (data[:i] if i >= 0 else data)


# ------------------------------------------------------------------ ANSI reader
class _Canvas:
    def __init__(self, cols: int):
        self.cols = cols
        self.rows: list[tuple[bytearray, bytearray]] = []
        self.x = 0
        self.y = 0
        self.fg, self.bg, self.bold, self.blink, self.rev = 7, 0, False, False, False
        self.saved = (0, 0)

    def ensure(self, y: int) -> None:
        while len(self.rows) <= y and len(self.rows) < MAX_ROWS:
            self.rows.append((bytearray(b" " * self.cols), bytearray([7]) * self.cols))

    def attr(self) -> int:
        fg = self.fg + (8 if self.bold else 0)
        bg = self.bg
        if self.rev:
            fg, bg = bg, fg & 7
        return (bg << 4 | fg) | (0x80 if self.blink else 0)

    def put(self, b: int) -> None:
        if self.x >= self.cols:                  # deferred wrap
            self.x = 0
            self.y += 1
        if self.y >= MAX_ROWS:
            return
        self.ensure(self.y)
        ch, at = self.rows[self.y]
        ch[self.x] = b
        at[self.x] = self.attr()
        self.x += 1

    def sgr(self, params: list[int]) -> None:
        if not params:
            params = [0]
        for p in params:
            if p == 0:
                self.fg, self.bg, self.bold, self.blink, self.rev = 7, 0, False, False, False
            elif p == 1:
                self.bold = True
            elif p in (5, 6):
                self.blink = True
            elif p == 7:
                self.rev = True
            elif p in (21, 22):
                self.bold = False
            elif p == 25:
                self.blink = False
            elif p == 27:
                self.rev = False
            elif 30 <= p <= 37:
                self.fg = ANSI_TO_CGA[p - 30]
            elif p == 39:
                self.fg = 7
            elif 40 <= p <= 47:
                self.bg = ANSI_TO_CGA[p - 40]
            elif p == 49:
                self.bg = 0
            elif 90 <= p <= 97:
                self.fg = ANSI_TO_CGA[p - 90]
                self.bold = True
            elif 100 <= p <= 107:
                self.bg = ANSI_TO_CGA[p - 100]
                self.blink = True

    def buffer(self, min_rows: int = 1) -> CellBuffer:
        n = max(min_rows, len(self.rows), 1)
        b = CellBuffer(self.cols, n)
        for y, (ch, at) in enumerate(self.rows):
            b.chars[y * self.cols:(y + 1) * self.cols] = ch
            b.attrs[y * self.cols:(y + 1) * self.cols] = at
        return b


_CSI = re.compile(rb"\x1b\[([?=]?)([0-9;]*)([@-~])")


def parse_ansi(data: bytes, cols: int = 80) -> CellBuffer:
    cv = _Canvas(cols)
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if b == ESC:
            m = _CSI.match(data, i)
            if m is None:
                i += 1
                continue
            priv, ps, cmd = m.group(1), m.group(2), m.group(3)
            nums = [int(p) if p else 0 for p in ps.split(b";")] if ps else []
            v = nums[0] if nums else 0
            if priv:
                pass
            elif cmd == b"m":
                cv.sgr(nums)
            elif cmd in (b"H", b"f"):
                cv.y = max(0, (nums[0] if nums and nums[0] else 1) - 1)
                cv.x = max(0, min(cols - 1, (nums[1] if len(nums) > 1 and nums[1] else 1) - 1))
            elif cmd == b"A":
                cv.y = max(0, cv.y - (v or 1))
            elif cmd == b"B":
                cv.y += v or 1
            elif cmd == b"C":
                cv.x = min(cols - 1, min(cv.x, cols - 1) + (v or 1))
            elif cmd == b"D":
                cv.x = max(0, min(cv.x, cols) - (v or 1))
            elif cmd == b"J":
                if v == 2:
                    cv.rows.clear()
                    cv.x = cv.y = 0
            elif cmd == b"K":
                cv.ensure(cv.y)
                ch, at = cv.rows[cv.y]
                for x in range(min(cv.x, cols), cols):
                    ch[x] = 0x20
                    at[x] = cv.attr()
            elif cmd == b"s":
                cv.saved = (cv.x, cv.y)
            elif cmd == b"u":
                cv.x, cv.y = cv.saved
            i = m.end()
            continue
        if b == 0x0D:
            cv.x = 0
        elif b == 0x0A:
            cv.y += 1
            if cv.x >= cols:
                cv.x = 0
        elif b == SUB:
            break
        elif b == 0x09:
            cv.x = min(cols, (cv.x // 8 + 1) * 8)
        else:
            cv.put(b)
        i += 1
    if cv.y < MAX_ROWS:
        cv.ensure(min(cv.y, MAX_ROWS - 1) if cv.x else max(0, cv.y - 1))
    return cv.buffer()


def to_ansi(buf: CellBuffer, ice: bool = False) -> bytes:
    """ANSI escape stream of *buf* (CR LF after every row; trailing blank cells with attribute 7 are dropped)."""
    out = bytearray(b"\x1b[0m")
    cur = None
    for y in range(buf.rows):
        last = buf.cols
        while last > 0 and buf.get(last - 1, y) == (0x20, 0x07):
            last -= 1
        for x in range(last):
            ch, a = buf.get(x, y)
            if a != cur:
                fg, bg, bl = a & 15, (a >> 4) & 7, bool(a & 0x80)
                seq = "0"
                if fg > 7:
                    seq += ";1"
                if bl:
                    seq += ";5"
                seq += f";{30 + CGA_TO_ANSI[fg & 7]};{40 + CGA_TO_ANSI[bg]}"
                out += f"\x1b[{seq}m".encode("ascii")
                cur = a
            out.append(ch if ch not in (0x1B, 0x1A, 0x0D, 0x0A, 0x09, 0x00, 0x08) else 0x20)
        out += b"\x1b[0m\r\n"
        cur = None
    return bytes(out)


# ------------------------------------------------------------------ files
def load_art(path, cols: int = 80) -> CellBuffer:
    """Read .ans / .bin / .txt (or anything with a SAUCE record) into a CellBuffer."""
    path = Path(path)
    data = path.read_bytes()
    sauce, body = read_sauce(data)
    ext = path.suffix.lower()
    if ext == ".bin" or (sauce is not None and sauce.data_type == 5):
        width = sauce.width if sauce is not None else (160 if len(body) >= 4000 else cols)
        if sauce is None and len(body) in (4000, 6880, 8000):
            width = 80
        return CellBuffer.from_bin(body, width)
    width = sauce.width if sauce is not None and sauce.data_type == 1 and sauce.width else cols
    if ext in (".txt", ".asc", ".nfo", ".diz") or (sauce is not None and sauce.file_type == 0):
        return parse_text(body, width)
    return parse_ansi(body, width)


def parse_text(data: bytes, cols: int = 80) -> CellBuffer:
    text = None
    if any(b > 0x7F for b in data):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = None
    lines = (text.splitlines() if text is not None else data.split(b"\n"))
    b = CellBuffer(cols, max(1, len(lines)))
    for y, line in enumerate(lines):
        if isinstance(line, bytes):
            line = line.rstrip(b"\r")
            b.text(0, y, line[:cols], 0x07)
        else:
            b.text(0, y, line[:cols], 0x07)
    return b


def save_art(buf: CellBuffer, path, sauce: Sauce | None = None) -> Path:
    path = Path(path)
    ext = path.suffix.lower()
    sc = sauce or Sauce()
    sc.width, sc.rows = buf.cols, buf.rows
    if ext == ".bin":
        body = buf.to_bin()
        sc.data_type, sc.file_type = 5, buf.cols // 2
    elif ext in (".txt", ".asc", ".nfo"):
        body = b"\r\n".join(bytes(buf.chars[r * buf.cols:(r + 1) * buf.cols]).rstrip(b" ")
                            for r in range(buf.rows)) + b"\r\n"
        path.write_bytes(body)
        return path
    else:
        body = to_ansi(buf, sc.ice_colors)
        sc.data_type, sc.file_type = 1, 1
    path.write_bytes(body + bytes([SUB]) + sc.to_bytes(len(body)))
    return path


def art_sauce(path) -> Sauce | None:
    try:
        return read_sauce(Path(path).read_bytes())[0]
    except OSError:
        return None
