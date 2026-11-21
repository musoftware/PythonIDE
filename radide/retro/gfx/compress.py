"""Compressed graphics in ROMs: a pluggable codec layer for the Tile Editor (pure Python, no Qt).

Each codec decompresses a stream that starts at a ROM offset and tells how many ROM bytes it used, and
compresses edited bytes again. The Tile Editor opens a region (decompress -> edit -> recompress), checks that the
new stream still fits (the old stream + the free bytes after it) and writes it back.

==============  ================================================================================================
``pb53``        PB53 (Damian Yerrick's NES tile packer; Double Action Blaster Guys, many homebrews): per tile a
                control byte per plane (PB8 runs), $80/$81 solid plane, $82 repeat previous tile / plane, $83 the
                tile 4 KB back / the inverted plane, $84-$87 two solid planes. No length in the stream (raw form):
                give the number of tiles. ``pb53h`` = the form with the 2-byte tile count + seek points header.
``rle_konami``  Konami-style RLE: $01-$80 n = repeat the next byte n times, $81-$FE = copy n-$80 literal bytes,
                $FF = end (also $00 is read as the end)
``rle_shiru``   NES Screen Tool / neslib ``vram_unrle`` RLE (Shiru): first byte = tag; tag,n = repeat the last byte
                n times; tag,0 = end; any other byte is copied
``packbits``    PackBits (Apple; used on GB / SNES / PC): n 0-127 = n+1 literal bytes, n 129-255 = the next byte
                257-n times, 128 = no-op. No end marker: give the size.
``lz10``        GBA / DS BIOS LZ77 (type $10): header $10 + 24-bit size, flag bytes, 2-byte back references
                (12-bit distance, 4-bit length + 3)
==============  ================================================================================================

``decompress(key, data, offset, size=None) -> (bytes, used)``; ``compress(key, raw) -> bytes``;
``find_graphics(data, keys)`` scans for blocks that decompress into plausible tiles (CHR-RAM games keep all their
graphics compressed in the PRG ROM). New codecs: ``register(Codec(...))``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


class CodecError(ValueError):
    pass


@dataclass(frozen=True)
class Codec:
    key: str
    name: str
    decode: Callable          # (data, offset, size|None) -> (bytes, used)
    encode: Callable          # (raw) -> bytes
    needs_size: bool = False  # the stream has no end marker / length: the caller gives the output size
    scan: bool = True         # find_graphics tries it


CODECS: dict[str, Codec] = {}


def register(codec: Codec) -> Codec:
    CODECS[codec.key] = codec
    return codec


def decompress(key: str, data, offset: int = 0, size: int | None = None) -> tuple[bytes, int]:
    c = CODECS[key]
    if c.needs_size and not size:
        raise CodecError(f"{c.name}: the stream has no length - give the decompressed size")
    return c.decode(bytes(data), offset, size)


def compress(key: str, raw) -> bytes:
    return CODECS[key].encode(bytes(raw))


# ====================================================================== PB53
def _pb8_plane(plane: bytes, top=None) -> bytes:
    out = [0]
    last = top
    flag = 0
    for c in plane:
        flag <<= 1
        if c == last:
            flag |= 1
        else:
            out.append(c)
            last = c
    out[0] = flag & 0xFF
    return bytes(out)


def pb53_pack(chrdata: bytes) -> tuple[bytes, list[int]]:
    """The packer of pb53.py (Damian Yerrick), byte for byte: (stream, seek points at every 4 KB)."""
    out = bytearray()
    seek = []
    for i in range(0, len(chrdata), 16):
        if i > 0 and i % 4096 == 0:
            seek.append(len(out))
        tile = chrdata[i:i + 16]
        if len(tile) < 16:
            tile = tile + bytes(16 - len(tile))
        solid0 = tile[0] in (0x00, 0xFF) and all(x == tile[0] for x in tile[1:8])
        solid1 = tile[8] in (0x00, 0xFF) and all(x == tile[8] for x in tile[9:16])
        if solid0 and solid1:
            out.append(0x84 | (0x02 & tile[8]) | (0x01 & tile[0]))
            continue
        if i >= 16 and chrdata[i - 16:i] == tile:
            out.append(0x82)
            continue
        if i >= 4096 and chrdata[i - 4096:i - 4080] == tile:
            out.append(0x83)
            continue
        if solid0:
            out.append(0x80 | (0x01 & tile[0]))
        else:
            out += _pb8_plane(tile[0:8])
        if solid1:
            out.append(0x80 | (0x01 & tile[8]))
        elif tile[0:8] == tile[8:16]:
            out.append(0x82)
        elif all(a ^ b == 0xFF for a, b in zip(tile[0:8], tile[8:16])):
            out.append(0x83)
        else:
            out += _pb8_plane(tile[8:16])
    return bytes(out), seek


def _pb53_tiles(data: bytes, pos: int, tiles: int) -> tuple[bytes, int]:
    out = bytearray()
    n = len(data)

    def nxt():
        nonlocal pos
        if pos >= n:
            raise CodecError("PB53: the stream ends inside a tile")
        b = data[pos]
        pos += 1
        return b

    def plane(ctrl):
        if ctrl >= 0x80:
            return [0xFF if ctrl & 1 else 0x00] * 8
        row = [nxt()]
        while len(row) < 8:
            ctrl <<= 1
            row.append(row[-1] if ctrl & 0x80 else nxt())
        return row

    for _t in range(tiles):
        ctrl = nxt()
        if 0x84 <= ctrl <= 0x87:
            out += bytes([0xFF if ctrl & 1 else 0] * 8 + [0xFF if ctrl & 2 else 0] * 8)
            continue
        if ctrl == 0x82:
            if len(out) < 16:
                raise CodecError("PB53: 'repeat the previous tile' at the first tile")
            out += out[-16:]
            continue
        if ctrl == 0x83:
            if len(out) < 4096:
                raise CodecError("PB53: 'tile 4 KB back' before 4 KB of output")
            out += out[-4096:-4080]
            continue
        if ctrl > 0x87:
            raise CodecError(f"PB53: unknown control byte ${ctrl:02X}")
        out += bytes(plane(ctrl))
        ctrl = nxt()
        if ctrl in (0x82, 0x83):
            x = 0xFF if ctrl & 1 else 0
            out += bytes(c ^ x for c in out[-8:])
        elif ctrl > 0x81:
            raise CodecError(f"PB53: unknown control byte ${ctrl:02X}")
        else:
            out += bytes(plane(ctrl))
    return bytes(out), pos


def _pb53_dec(data: bytes, offset: int, size: int | None):
    tiles = -(-int(size) // 16)
    out, end = _pb53_tiles(data, offset, tiles)
    return out[:size], end - offset


def _pb53_enc(raw: bytes) -> bytes:
    return pb53_pack(raw)[0]


def _pb53h_dec(data: bytes, offset: int, size: int | None):
    if offset + 2 > len(data):
        raise CodecError("PB53: no header")
    num = (data[offset] << 8) | data[offset + 1]
    if num == 0:
        raise CodecError("PB53: zero tiles")
    start = offset + (-((-num) // 256)) * 2
    out, end = _pb53_tiles(data, start, num)
    return out, end - offset


def _pb53h_enc(raw: bytes) -> bytes:
    body, seek = pb53_pack(raw)
    words = [(len(raw) // 16) % 0x10000] + seek
    return b"".join(bytes(((v >> 8) & 0xFF, v & 0xFF)) for v in words) + body


# ====================================================================== Konami RLE
def _konami_dec(data: bytes, offset: int, size: int | None):
    out = bytearray()
    pos = offset
    n = len(data)
    limit = size or 0x10000
    while True:
        if pos >= n:
            raise CodecError("Konami RLE: no end byte ($FF)")
        c = data[pos]
        pos += 1
        if c in (0xFF, 0x00):
            break
        if c <= 0x80:
            if pos >= n:
                raise CodecError("Konami RLE: cut run")
            out += bytes([data[pos]]) * c
            pos += 1
        else:
            k = c - 0x80
            if pos + k > n:
                raise CodecError("Konami RLE: cut literal run")
            out += data[pos:pos + k]
            pos += k
        if len(out) > limit:
            raise CodecError("Konami RLE: more output than expected")
    return bytes(out[:size] if size else out), pos - offset


def _konami_enc(raw: bytes) -> bytes:
    out = bytearray()
    i, n = 0, len(raw)
    lit = bytearray()

    def flush():
        while lit:
            chunk = lit[:0x7E]
            out.append(0x80 + len(chunk))
            out.extend(chunk)
            del lit[:len(chunk)]
    while i < n:
        j = i
        while j < n and raw[j] == raw[i] and j - i < 0x80:
            j += 1
        if j - i >= 3 or (j - i >= 2 and not lit):
            flush()
            out += bytes((j - i, raw[i]))
            i = j
        else:
            lit.append(raw[i])
            i += 1
    flush()
    out.append(0xFF)
    return bytes(out)


# ====================================================================== Shiru RLE (NES Screen Tool / neslib)
def _shiru_dec(data: bytes, offset: int, size: int | None):
    if offset >= len(data):
        raise CodecError("RLE: empty")
    tag = data[offset]
    pos = offset + 1
    out = bytearray()
    last = None
    n = len(data)
    limit = size or 0x10000
    while True:
        if pos >= n:
            raise CodecError("RLE: no end mark (tag, 0)")
        b = data[pos]
        pos += 1
        if b == tag:
            if pos >= n:
                raise CodecError("RLE: cut")
            k = data[pos]
            pos += 1
            if k == 0:
                break
            if last is None:
                raise CodecError("RLE: run before the first byte")
            out += bytes([last]) * k
        else:
            out.append(b)
            last = b
        if len(out) > limit:
            raise CodecError("RLE: more output than expected")
    return bytes(out[:size] if size else out), pos - offset


def _shiru_enc(raw: bytes) -> bytes:
    counts = [0] * 256
    for b in raw:
        counts[b] += 1
    tag = min(range(256), key=lambda v: (counts[v], v))
    out = bytearray([tag])
    i, n = 0, len(raw)
    while i < n:
        b = raw[i]
        if b == tag:                          # the tag value itself: write it once, then a run of the rest
            raise CodecError("RLE: every byte value is used - this data cannot use Shiru's RLE")
        j = i + 1
        while j < n and raw[j] == b and j - i < 256:
            j += 1
        run = j - i
        out.append(b)
        if run >= 3:
            out += bytes((tag, run - 1))
        else:
            out += bytes([b]) * (run - 1)
        i = j
    out += bytes((tag, 0))
    return bytes(out)


# ====================================================================== PackBits
def _packbits_dec(data: bytes, offset: int, size: int | None):
    out = bytearray()
    pos = offset
    n = len(data)
    while len(out) < size:
        if pos >= n:
            raise CodecError("PackBits: the stream ends early")
        h = data[pos]
        pos += 1
        if h < 128:
            k = h + 1
            if pos + k > n:
                raise CodecError("PackBits: cut literal run")
            out += data[pos:pos + k]
            pos += k
        elif h > 128:
            if pos >= n:
                raise CodecError("PackBits: cut run")
            out += bytes([data[pos]]) * (257 - h)
            pos += 1
    if len(out) != size:
        raise CodecError("PackBits: the last run goes past the size")
    return bytes(out), pos - offset


def _packbits_enc(raw: bytes) -> bytes:
    out = bytearray()
    i, n = 0, len(raw)
    lit = bytearray()

    def flush():
        while lit:
            chunk = lit[:128]
            out.append(len(chunk) - 1)
            out.extend(chunk)
            del lit[:len(chunk)]
    while i < n:
        j = i
        while j < n and raw[j] == raw[i] and j - i < 128:
            j += 1
        if j - i >= 3:
            flush()
            out += bytes((257 - (j - i), raw[i]))
            i = j
        else:
            lit.append(raw[i])
            i += 1
    flush()
    return bytes(out)


# ====================================================================== GBA LZ77 (type 0x10)
def _lz10_dec(data: bytes, offset: int, size: int | None):
    n = len(data)
    if offset + 4 > n or data[offset] != 0x10:
        raise CodecError("LZ10: no $10 header")
    total = data[offset + 1] | (data[offset + 2] << 8) | (data[offset + 3] << 16)
    if total == 0 or total > (size or 1 << 20):
        raise CodecError("LZ10: bad size")
    pos = offset + 4
    out = bytearray()
    while len(out) < total:
        if pos >= n:
            raise CodecError("LZ10: the stream ends early")
        flags = data[pos]
        pos += 1
        for bit in range(8):
            if len(out) >= total:
                break
            if flags & (0x80 >> bit):
                if pos + 2 > n:
                    raise CodecError("LZ10: cut reference")
                b1, b2 = data[pos], data[pos + 1]
                pos += 2
                length = (b1 >> 4) + 3
                disp = (((b1 & 0x0F) << 8) | b2) + 1
                if disp > len(out):
                    raise CodecError("LZ10: reference before the start")
                for _k in range(length):
                    out.append(out[-disp])
            else:
                if pos >= n:
                    raise CodecError("LZ10: cut literal")
                out.append(data[pos])
                pos += 1
    return bytes(out[:total]), pos - offset


def _lz10_enc(raw: bytes) -> bytes:
    n = len(raw)
    out = bytearray((0x10, n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF))
    heads: dict[bytes, list[int]] = {}
    i = 0
    while i < n:
        flag_pos = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if i >= n:
                break
            best_len, best_d = 0, 0
            key = raw[i:i + 3]
            if len(key) == 3:
                for j in reversed(heads.get(key, [])[-48:]):
                    d = i - j
                    if d > 0x1000:
                        break
                    if d < 1:
                        continue
                    k = 0
                    while k < 18 and i + k < n and raw[j + k] == raw[i + k]:
                        k += 1
                    if k > best_len:
                        best_len, best_d = k, d
                        if k == 18:
                            break
            step = best_len if best_len >= 3 else 1
            if best_len >= 3:
                flags |= 0x80 >> bit
                v = ((best_len - 3) << 12) | (best_d - 1)
                out += bytes(((v >> 8) & 0xFF, v & 0xFF))
            else:
                out.append(raw[i])
            for p in range(i, min(i + step, n - 2)):
                heads.setdefault(raw[p:p + 3], []).append(p)
            i += step
        out[flag_pos] = flags
    while len(out) % 4:
        out.append(0)
    return bytes(out)


for _c in (Codec("pb53", "PB53 (NES tiles, raw: give the tile count)", _pb53_dec, _pb53_enc, needs_size=True),
           Codec("pb53h", "PB53 with tile-count header", _pb53h_dec, _pb53h_enc),
           Codec("rle_konami", "Konami-style RLE ($FF end)", _konami_dec, _konami_enc),
           Codec("rle_shiru", "NES Screen Tool RLE (Shiru, tag byte)", _shiru_dec, _shiru_enc),
           Codec("packbits", "PackBits RLE (give the size)", _packbits_dec, _packbits_enc, needs_size=True,
                 scan=False),
           Codec("lz10", "GBA / DS LZ77 (type $10)", _lz10_dec, _lz10_enc)):
    register(_c)


# ====================================================================== regions: edit and write back
def free_after(data, end: int, fill: int | None = None) -> tuple[int, int]:
    """(number of free bytes after *end*, fill byte): a run of $FF or $00 (the usual padding of a ROM)."""
    n = len(data)
    if end >= n:
        return 0, 0xFF
    f = data[end] if fill is None else fill
    if f not in (0x00, 0xFF):
        return 0, 0xFF
    k = end
    while k < n and data[k] == f:
        k += 1
    return k - end, f


@dataclass
class Region:
    """A compressed block in a ROM: where it is, how it was packed, the decompressed bytes."""
    codec: str
    offset: int
    used: int                 # ROM bytes of the original stream
    size: int                 # decompressed bytes
    raw: bytes

    @classmethod
    def open(cls, codec: str, data, offset: int, size: int | None = None) -> "Region":
        raw, used = decompress(codec, data, offset, size)
        return cls(codec, offset, used, len(raw), raw)

    def room(self, data) -> tuple[int, int]:
        """(bytes available for a new stream, fill byte for the rest)."""
        free, fill = free_after(data, self.offset + self.used)
        return self.used + free, fill

    def pack(self, raw) -> bytes:
        return compress(self.codec, raw)

    def write_back(self, data: bytearray, raw, allow_grow: bool = False) -> tuple[int, int, int]:
        """Recompress *raw* into *data* at the region. Returns (new stream size, room, old size).
        Raises CodecError when the new stream does not fit (unless *allow_grow*: the user accepted that the
        bytes after the old stream are overwritten)."""
        new = self.pack(raw)
        room, fill = self.room(data)
        if len(new) > room and not allow_grow:
            raise CodecError(f"the recompressed graphics need {len(new)} bytes, only {room} are free here "
                             f"({self.used} of the old stream + {room - self.used} free bytes after it)")
        back, _u = decompress(self.codec, new, 0, self.size if CODECS[self.codec].needs_size else None)
        if back[:len(raw)] != bytes(raw)[:len(back)]:
            raise CodecError("the codec did not give back the same bytes (internal error)")
        old = self.used
        data[self.offset:self.offset + len(new)] = new
        if len(new) < self.used:
            data[self.offset + len(new):self.offset + self.used] = bytes([fill]) * (self.used - len(new))
        self.used = len(new)
        self.raw = bytes(raw)
        return len(new), room, old


# ====================================================================== finding graphics in a ROM
@dataclass
class Candidate:
    offset: int
    codec: str
    used: int
    size: int
    tiles: int
    score: float

    def label(self) -> str:
        return (f"0x{self.offset:06X}  {CODECS[self.codec].name.split(' (')[0]}: {self.used} bytes -> "
                f"{self.size} bytes ({self.tiles} tiles, x{self.size / max(1, self.used):.1f})")


def _tile_score(raw: bytes, tile_bytes: int = 16) -> float:
    """0..1: how much *raw* looks like tile graphics (not all zero, varied, structured)."""
    if len(raw) < tile_bytes * 4:
        return 0.0
    tiles = [raw[i:i + tile_bytes] for i in range(0, len(raw) - tile_bytes + 1, tile_bytes)]
    empty = sum(1 for t in tiles if not any(t) or all(b == 0xFF for b in t))
    distinct = len(set(tiles))
    if empty == len(tiles) or distinct < 3:
        return 0.0
    # rows repeat inside real tiles (outlines, solid areas): count equal neighbouring bytes
    same = sum(1 for t in tiles for k in range(1, len(t)) if t[k] == t[k - 1])
    rep = same / max(1, len(tiles) * (tile_bytes - 1))
    return min(1.0, 0.3 + rep) * (1.0 - empty / len(tiles) * 0.5)


# how much a valid decode means: PB53 / LZ10 streams have structure that random bytes break quickly; any
# byte sequence is a valid RLE stream, so RLE hits need more evidence (whole tiles, a better ratio)
CONFIDENCE = {"pb53": 1.0, "pb53h": 0.9, "lz10": 0.8, "rle_konami": 0.3, "rle_shiru": 0.3, "packbits": 0.25}


def find_graphics(data, keys=None, min_tiles: int = 16, start: int = 0, end: int | None = None,
                  pb53_tiles: int = 64, max_results: int = 64, progress=None) -> list[Candidate]:
    """Blocks that decompress into plausible 2bpp tiles, best first (*keys*: the codecs to try, default all
    that can be scanned). PB53 has no length: it is tried with *pb53_tiles* tiles, then extended while it keeps
    compressing well. Overlapping hits are resolved in favour of the more convincing one.
    *progress(pos, end)* is called every 512 offsets; returning False stops the scan."""
    data = bytes(data)
    end = len(data) if end is None else min(end, len(data))
    keys = [k for k in (keys or CODECS) if k in CODECS and CODECS[k].scan]
    view = data[:end]
    cands: list[Candidate] = []
    for pos in range(start, end):
        if progress is not None and not (pos - start) % 512 and progress(pos, end) is False:
            break
        for k in keys:
            try:
                if k == "pb53":
                    hit = _scan_pb53(view, pos, pb53_tiles, end)
                    if hit is None:
                        continue
                    raw, used = hit
                else:
                    if k == "lz10" and view[pos] != 0x10:
                        continue
                    raw, used = decompress(k, view, pos, 0x8000 if k != "lz10" else None)
            except (CodecError, IndexError, ValueError):
                continue
            weak = CONFIDENCE.get(k, 0.5) < 0.6
            if len(raw) < min_tiles * 16 or len(raw) < used * (1.6 if weak else 1.3):
                continue
            if weak and len(raw) % 16:
                continue
            sc = _tile_score(raw)
            if sc < (0.6 if weak else 0.45):
                continue
            ratio = min(2.0 if weak else 3.0, len(raw) / max(1, used))
            size_bonus = min(1.0, len(raw) / 4096) * 0.5 + 0.5
            cands.append(Candidate(pos, k, used, len(raw), len(raw) // 16,
                                   round(CONFIDENCE.get(k, 0.5) * sc * ratio * size_bonus, 3)))
    # a hit that starts inside an earlier hit of the same codec is the same stream (a later tile boundary)
    kept: list[Candidate] = []
    last_end: dict[str, int] = {}
    for c in sorted(cands, key=lambda c: c.offset):
        if c.offset < last_end.get(c.codec, -1):
            continue
        kept.append(c)
        last_end[c.codec] = c.offset + c.used
    final: list[Candidate] = []
    for c in sorted(kept, key=lambda c: -c.score):
        if all(c.offset + c.used <= f.offset or f.offset + f.used <= c.offset for f in final):
            final.append(c)
        if len(final) >= max_results:
            break
    return final


def _scan_pb53(data: bytes, pos: int, tiles: int, end: int):
    # quick reject: 8 tiles of real graphics take less than their 128 raw bytes (random bytes break the
    # control-byte rules within a few tiles anyway)
    first, used8 = _pb53_tiles(data[:end], pos, 8)
    if used8 - pos >= 128 or not any(first):
        return None
    raw, p = _pb53_tiles(data[:end], pos, tiles)
    if len(raw) < (p - pos) * 1.2:
        return None
    total = tiles                       # extend in steps of 16 tiles while the stream stays valid and packed
    while total < 1024:
        try:
            more, p2 = _pb53_tiles(data[:end], pos, total + 16)
        except CodecError:
            break
        if p2 - p > 32 and _tile_score(more[-256:]) < 0.2:   # (empty tiles pack to 1 byte each: keep them)
            break
        raw, p, total = more, p2, total + 16
    return raw, p - pos


__all__ = ["CODECS", "Candidate", "Codec", "CodecError", "Region", "compress", "decompress", "find_graphics",
           "free_after", "pb53_pack", "register"]
