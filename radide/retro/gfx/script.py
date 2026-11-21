"""Script dump / insert for game-text translation.

*Dump* reads strings out of a ROM with a text table - either from **pointer tables** (``count`` pointers of
2, 3 or 4 bytes at ``table_offset``) or from **ranges** of the file split at end codes - into a sheet of
entries.  The translator fills the *translation* column (the sheet saves to / loads from UTF-8 CSV).

*Insert* encodes the translations with the table and writes them back:

* ``inplace`` - every string stays where it was and must fit in its original length (the rest is padded);
* ``repack`` - strings are written one after another into a free region (``region_start..region_end``,
  usually the original text block), identical strings are stored once, and every pointer is recalculated.

Nothing is written when a string does not fit or a character is missing from the table: the report lists
the problems first.  Pointer arithmetic: ``file offset = pointer value - base + add`` (e.g. a NES game with
a 16-byte header and the text bank mapped at $8000: base = $8000, add = $10 + bank * $4000).
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

from .textable import TextTable


@dataclass
class PointerSpec:
    table_offset: int
    count: int
    size: int = 2                    # 2, 3 or 4 bytes
    endian: str = "little"
    base: int = 0                    # subtract from the pointer value ...
    add: int = 0                     # ... and add this to get the file offset
    stride: int = 0                  # bytes between pointers (0 = size)

    def ptr_pos(self, i: int) -> int:
        return self.table_offset + i * (self.stride or self.size)

    def read(self, rom: bytes, i: int) -> int:
        p = self.ptr_pos(i)
        return int.from_bytes(rom[p:p + self.size], self.endian)

    def to_file(self, value: int) -> int:
        return value - self.base + self.add

    def to_pointer(self, file_offset: int) -> int:
        v = file_offset - self.add + self.base
        if v < 0 or v >= 1 << (8 * self.size):
            raise ValueError(f"offset {file_offset:#x} cannot be addressed by a {self.size}-byte pointer")
        return v


@dataclass
class Entry:
    index: int
    offset: int                      # file offset of the text
    length: int                      # original length in bytes, end code included
    original: str
    translation: str = ""
    ptr_pos: int | None = None       # where the pointer is (None for range dumps)
    note: str = ""

    def text_to_insert(self) -> str:
        return self.translation if self.translation.strip() else self.original


@dataclass
class Script:
    entries: list[Entry] = field(default_factory=list)
    pointers: PointerSpec | None = None

    # ------------------------------------------------------------ sheet I/O
    def to_csv(self) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(["index", "pointer", "offset", "length", "original", "translation", "note"])
        for e in self.entries:
            w.writerow([e.index, "" if e.ptr_pos is None else f"0x{e.ptr_pos:X}", f"0x{e.offset:X}", e.length,
                        e.original, e.translation, e.note])
        return buf.getvalue()

    def load_csv(self, text: str) -> int:
        """Take the translation column of a sheet saved earlier (matched by index); returns rows used."""
        by_index = {e.index: e for e in self.entries}
        rows = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
        n = 0
        for r in rows[1:]:
            if len(r) >= 6 and r[0].strip().isdigit() and int(r[0]) in by_index:
                by_index[int(r[0])].translation = r[5]
                if len(r) >= 7:
                    by_index[int(r[0])].note = r[6]
                n += 1
        return n

    @classmethod
    def from_csv(cls, text: str) -> "Script":
        s = cls()
        for r in list(csv.reader(io.StringIO(text.lstrip("﻿"))))[1:]:
            if len(r) < 6 or not r[0].strip().isdigit():
                continue
            s.entries.append(Entry(int(r[0]), int(r[2], 0), int(r[3]), r[4], r[5],
                                   int(r[1], 0) if r[1].strip() else None, r[6] if len(r) > 6 else ""))
        return s


# ===================================================================== dump
def dump_pointers(rom: bytes, table: TextTable, spec: PointerSpec, max_len: int = 4096) -> Script:
    s = Script(pointers=spec)
    for i in range(spec.count):
        pp = spec.ptr_pos(i)
        if pp + spec.size > len(rom):
            break
        off = spec.to_file(spec.read(rom, i))
        if not 0 <= off < len(rom):
            s.entries.append(Entry(i, off, 0, "", ptr_pos=pp, note="pointer outside the file"))
            continue
        text, n, _ended = table.decode(rom, off, min(len(rom), off + max_len))
        s.entries.append(Entry(i, off, n, text, ptr_pos=pp))
    return s


def dump_ranges(rom: bytes, table: TextTable, ranges: list[tuple[int, int]]) -> Script:
    """Strings of ``rom[start:end]`` (end exclusive), split after every end code."""
    s = Script()
    idx = 0
    for start, end in ranges:
        pos = start
        end = min(end, len(rom))
        while pos < end:
            text, n, _ended = table.decode(rom, pos, end)
            if n <= 0:
                break
            s.entries.append(Entry(idx, pos, n, text))
            idx += 1
            pos += n
    return s


# ===================================================================== insert
@dataclass
class InsertResult:
    ok: bool
    rom: bytearray
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    used: int = 0
    capacity: int = 0

    def report(self) -> str:
        lines = [("Inserted" if self.ok else "NOT inserted") +
                 (f": {self.used} of {self.capacity} bytes used" if self.capacity else "")]
        lines += [f"ERROR: {e}" for e in self.errors]
        lines += [f"warning: {w}" for w in self.warnings]
        return "\n".join(lines)


def _encode_all(script: Script, table: TextTable, prepare=None) -> tuple[list[bytes], list[str]]:
    encoded, errors = [], []
    end = table.end_code()
    for e in script.entries:
        text = e.text_to_insert()
        if prepare is not None and e.translation.strip():
            text = prepare(text)
        data, problems = table.encode(text)
        for p in problems:
            errors.append(f"#{e.index}: {p}")
        if end is not None and not data.endswith(end) and e.original.endswith(table.end_label()):
            data += end                          # the translator dropped the end code: add it back
        encoded.append(data)
    return encoded, errors


def insert(rom: bytes, table: TextTable, script: Script, mode: str = "inplace", region: tuple[int, int] | None = None,
           pad: int = 0x00, prepare=None, dedupe: bool = True) -> InsertResult:
    out = bytearray(rom)
    encoded, errors = _encode_all(script, table, prepare)
    res = InsertResult(False, out, errors)
    if mode == "inplace":
        for e, data in zip(script.entries, encoded):
            res.capacity += e.length
            res.used += len(data)
            if len(data) > e.length:
                res.errors.append(f"#{e.index} at 0x{e.offset:X}: {len(data)} bytes, only {e.length} fit "
                                  f"({len(data) - e.length} too many)")
        if res.errors:
            res.rom = bytearray(rom)
            return res
        for e, data in zip(script.entries, encoded):
            out[e.offset:e.offset + e.length] = data + bytes([pad]) * (e.length - len(data))
        res.ok = True
        return res
    # ---- repack into a region and rewrite the pointers
    spec = script.pointers
    if spec is None:
        res.errors.append("repacking needs a pointer table (dump with pointers)")
        res.rom = bytearray(rom)
        return res
    if region is None:
        valid = [e for e in script.entries if e.length]
        region = (min(e.offset for e in valid), max(e.offset + e.length for e in valid)) if valid else (0, 0)
    start, stop = region
    res.capacity = stop - start
    placed: dict[bytes, int] = {}
    layout: list[tuple[Entry, int, bytes]] = []
    pos = start
    for e, data in zip(script.entries, encoded):
        if e.ptr_pos is None:
            continue
        if dedupe and data in placed:
            layout.append((e, placed[data], data))
            continue
        layout.append((e, pos, data))
        placed[data] = pos
        pos += len(data)
    res.used = pos - start
    if pos > stop:
        res.errors.append(f"the script needs {pos - start} bytes but the region 0x{start:X}-0x{stop:X} has "
                          f"{stop - start} ({pos - stop} too many)")
    for e, at, _d in layout:
        try:
            spec.to_pointer(at)
        except ValueError as ex:
            res.errors.append(f"#{e.index}: {ex}")
    if res.errors:
        res.rom = bytearray(rom)
        return res
    out[start:stop] = bytes([pad]) * (stop - start)
    for e, at, data in layout:
        out[at:at + len(data)] = data
        v = spec.to_pointer(at)
        out[e.ptr_pos:e.ptr_pos + spec.size] = v.to_bytes(spec.size, spec.endian)
        e.offset, e.length = at, len(data)
    if dedupe and len(placed) < len(layout):
        res.warnings.append(f"{len(layout) - len(placed)} identical strings share one copy")
    res.ok = True
    return res
