"""ROM patch formats: IPS, UPS and BPS - create and apply (pure Python, no Qt).

* **IPS** - "PATCH", records ``offset(3, BE) size(2, BE) data`` or RLE ``offset 0 count(2) byte``, "EOF" and
  the optional 3-byte truncation size (Lunar IPS extension). Offsets up to 16 MiB; the offset 0x454F46 ("EOF")
  can not start a record, so the creator starts such a record one byte earlier.
* **UPS** - "UPS1", VLQ source / target sizes, hunks ``VLQ skip`` + XOR bytes ending with 0x00, then CRC32 of
  source, target and patch. Applying a UPS patch to the *target* gives the source back (UPS is symmetric).
* **BPS** - "BPS1", VLQ sizes + metadata, actions ``VLQ((length-1) << 2 | command)`` with SourceRead,
  TargetRead, SourceCopy and TargetCopy (signed relative offsets), then CRC32 of source, target and patch.

Every function works on ``bytes``; errors raise :class:`PatchError` with a message for the user.
Written from the published format descriptions (IPS: the de-facto format; UPS / BPS: byuu's specifications).
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass, field

IPS_MAGIC = b"PATCH"
IPS_EOF = b"EOF"
IPS_EOF_OFFSET = 0x454F46
IPS_MAX = 1 << 24
UPS_MAGIC = b"UPS1"
BPS_MAGIC = b"BPS1"

SOURCE_READ, TARGET_READ, SOURCE_COPY, TARGET_COPY = range(4)
BPS_ACTIONS = ("SourceRead", "TargetRead", "SourceCopy", "TargetCopy")


class PatchError(ValueError):
    """A patch can not be read, does not match the ROM, or can not be created."""


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def patch_format(patch: bytes) -> str:
    """"ips" | "ups" | "bps" | "" from the magic bytes."""
    if patch[:5] == IPS_MAGIC:
        return "ips"
    if patch[:4] == UPS_MAGIC:
        return "ups"
    if patch[:4] == BPS_MAGIC:
        return "bps"
    return ""


# ============================================================================ VLQ (byuu's encoding)
def vlq_encode(value: int) -> bytes:
    if value < 0:
        raise PatchError("negative number in a VLQ")
    out = bytearray()
    while True:
        x = value & 0x7F
        value >>= 7
        if value == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        value -= 1


def vlq_decode(data: bytes, pos: int) -> tuple[int, int]:
    """(value, new position)."""
    value, shift = 0, 1
    while True:
        if pos >= len(data):
            raise PatchError("the patch ends in the middle of a number")
        x = data[pos]
        pos += 1
        value += (x & 0x7F) * shift
        if x & 0x80:
            return value, pos
        shift <<= 7
        value += shift


def eq_run(a: bytes, b: bytes, i: int, end: int) -> int:
    """Length of the run of equal bytes of *a* and *b* from *i* (not past *end*), compared in growing blocks
    so multi-megabyte ROMs with few changes are scanned at C speed."""
    return eq_run_at(a, i, b, i, end - i)


def eq_run_at(a: bytes, ai: int, b: bytes, bi: int, limit: int) -> int:
    """Length of the equal run of a[ai:] and b[bi:] (at most *limit* bytes)."""
    n, step = 0, 64
    while True:
        k = min(step, limit - n)
        if k <= 0:
            return n
        if a[ai + n:ai + n + k] == b[bi + n:bi + n + k]:
            n += k
            step = min(step * 2, 1 << 16)
        elif k <= 16:
            while n < limit and a[ai + n] == b[bi + n]:
                n += 1
            return n
        else:
            step = k // 2


# ============================================================================ IPS
@dataclass
class IpsRecord:
    offset: int
    data: bytes = b""
    rle_count: int = 0          # > 0: RLE record (data = the single byte)
    patch_offset: int = 0       # where the record starts in the patch file

    @property
    def size(self) -> int:
        return self.rle_count if self.rle_count else len(self.data)


@dataclass
class IpsPatch:
    records: list[IpsRecord] = field(default_factory=list)
    truncate: int | None = None


def ips_parse(patch: bytes) -> IpsPatch:
    if patch[:5] != IPS_MAGIC:
        raise PatchError("not an IPS patch (no PATCH header)")
    pos, n = 5, len(patch)
    out = IpsPatch()
    while True:
        if pos + 3 > n:
            raise PatchError("the IPS patch has no EOF marker (truncated file?)")
        if patch[pos:pos + 3] == IPS_EOF:
            pos += 3
            if n - pos >= 3:
                out.truncate = int.from_bytes(patch[pos:pos + 3], "big")
            return out
        start = pos
        offset = int.from_bytes(patch[pos:pos + 3], "big")
        if pos + 5 > n:
            raise PatchError(f"truncated IPS record at patch offset {start:#x}")
        size = int.from_bytes(patch[pos + 3:pos + 5], "big")
        pos += 5
        if size:
            if pos + size > n:
                raise PatchError(f"truncated IPS record at patch offset {start:#x}")
            out.records.append(IpsRecord(offset, bytes(patch[pos:pos + size]), 0, start))
            pos += size
        else:
            if pos + 3 > n:
                raise PatchError(f"truncated IPS RLE record at patch offset {start:#x}")
            count = int.from_bytes(patch[pos:pos + 2], "big")
            out.records.append(IpsRecord(offset, bytes(patch[pos + 2:pos + 3]), count, start))
            pos += 3


def ips_apply(source: bytes, patch: bytes) -> bytes:
    p = ips_parse(patch)
    out = bytearray(source)
    for r in p.records:
        end = r.offset + r.size
        if end > len(out):
            out.extend(b"\x00" * (end - len(out)))
        out[r.offset:end] = (r.data * r.rle_count) if r.rle_count else r.data
    if p.truncate is not None:
        if p.truncate < len(out):
            del out[p.truncate:]
        elif p.truncate > len(out):
            out.extend(b"\x00" * (p.truncate - len(out)))
    return bytes(out)


def _ips_chunks(source: bytes, target: bytes):
    """(offset, length) of the byte runs where target differs from source (bytes past the end of the source
    always count as different)."""
    n, m = len(source), len(target)
    i = 0
    common = min(n, m)
    while i < m:
        if i < common and source[i] == target[i]:
            i += eq_run(source, target, i, common)
            continue
        start = i
        # extend while different; allow up to 5 equal bytes inside a run (cheaper than a new 5-byte header)
        same = 0
        j = i
        while j < m:
            if j < common and source[j] == target[j]:
                same += 1
                if same > 5:
                    j += 1                 # j - same = the first of the equal bytes
                    break
            else:
                same = 0
            j += 1
        end = j - same
        yield start, end - start
        i = end


def ips_create(source: bytes, target: bytes, rle_min: int = 9) -> bytes:
    """An IPS patch that turns *source* into *target* (RLE records for runs of >= *rle_min* equal bytes;
    a truncation size when the target is shorter)."""
    if len(target) > IPS_MAX:
        raise PatchError("IPS patches can not address files larger than 16 MiB - use BPS")
    out = bytearray(IPS_MAGIC)

    def emit(off: int, data: bytes) -> None:
        out.extend(off.to_bytes(3, "big"))
        out.extend(len(data).to_bytes(2, "big"))
        out.extend(data)

    def emit_rle(off: int, count: int, byte: int) -> None:
        out.extend(off.to_bytes(3, "big"))
        out.extend(b"\x00\x00")
        out.extend(count.to_bytes(2, "big"))
        out.append(byte)

    for start, length in _ips_chunks(source, target):
        pos, end = start, start + length
        while pos < end:
            b = target[pos]
            run = 1
            while pos + run < end and run < 0xFFFF and target[pos + run] == b:
                run += 1
            if run >= rle_min:
                if pos == IPS_EOF_OFFSET:            # "EOF" can not be an offset: one literal byte earlier
                    emit(pos - 1, bytes(target[pos - 1:pos + 1]))
                    pos += 1
                    continue
                emit_rle(pos, run, b)
                pos += run
                continue
            # a literal block up to the next long run (max 0xFFFF bytes)
            at_eof = pos == IPS_EOF_OFFSET
            lit_end = min(end, pos + (0xFFFE if at_eof else 0xFFFF))
            q = pos
            while q < lit_end:
                c = target[q]
                r = 1
                while q + r < lit_end and target[q + r] == c and r < rle_min:
                    r += 1
                if r >= rle_min:
                    break
                q += r
            q = max(q, pos + 1)
            if at_eof:
                emit(pos - 1, bytes(target[pos - 1:q]))
            else:
                emit(pos, bytes(target[pos:q]))
            pos = q
    out.extend(IPS_EOF)
    if len(target) < len(source):
        out.extend(len(target).to_bytes(3, "big"))
    return bytes(out)


# ============================================================================ UPS
@dataclass
class UpsInfo:
    source_size: int
    target_size: int
    source_crc: int
    target_crc: int
    patch_crc: int
    hunks: int


def _crc_footer(patch: bytes, magic: bytes) -> tuple[int, int, int]:
    if len(patch) < len(magic) + 12 or patch[:4] != magic:
        raise PatchError(f"not a {magic[:3].decode()} patch")
    src = int.from_bytes(patch[-12:-8], "little")
    tgt = int.from_bytes(patch[-8:-4], "little")
    pcrc = int.from_bytes(patch[-4:], "little")
    if crc32(patch[:-4]) != pcrc:
        raise PatchError("the patch file is damaged (patch CRC32 mismatch)")
    return src, tgt, pcrc


def ups_info(patch: bytes) -> UpsInfo:
    src_crc, tgt_crc, pcrc = _crc_footer(patch, UPS_MAGIC)
    pos = 4
    ssize, pos = vlq_decode(patch, pos)
    tsize, pos = vlq_decode(patch, pos)
    hunks = 0
    end = len(patch) - 12
    while pos < end:
        _skip, pos = vlq_decode(patch, pos)
        while pos < end and patch[pos] != 0:
            pos += 1
        pos += 1
        hunks += 1
    return UpsInfo(ssize, tsize, src_crc, tgt_crc, pcrc, hunks)


def ups_apply(source: bytes, patch: bytes, check: bool = True) -> bytes:
    src_crc, tgt_crc, _p = _crc_footer(patch, UPS_MAGIC)
    pos = 4
    ssize, pos = vlq_decode(patch, pos)
    tsize, pos = vlq_decode(patch, pos)
    in_crc = crc32(source)
    if check:
        if len(source) == ssize and in_crc == src_crc:
            pass
        elif len(source) == tsize and in_crc == tgt_crc:        # UPS is symmetric: patch back
            ssize, tsize, src_crc, tgt_crc = tsize, ssize, tgt_crc, src_crc
        else:
            raise PatchError(f"this UPS patch is for a different file (expected CRC32 {src_crc:08X}, "
                             f"{ssize} bytes; the file is {in_crc:08X}, {len(source)} bytes)")
    out = bytearray(source[:tsize])
    if len(out) < tsize:
        out.extend(b"\x00" * (tsize - len(out)))
    rel = 0
    end = len(patch) - 12
    while pos < end:
        skip, pos = vlq_decode(patch, pos)
        rel += skip
        while True:
            if pos >= end:
                raise PatchError("the UPS patch ends inside a hunk")
            x = patch[pos]
            pos += 1
            if rel < tsize:
                out[rel] = (source[rel] if rel < len(source) else 0) ^ x
            rel += 1
            if x == 0:
                break
    result = bytes(out)
    if check and crc32(result) != tgt_crc:
        raise PatchError(f"the patched file has a wrong CRC32 ({crc32(result):08X}, expected {tgt_crc:08X})")
    return result


def ups_create(source: bytes, target: bytes) -> bytes:
    out = bytearray(UPS_MAGIC)
    out += vlq_encode(len(source))
    out += vlq_encode(len(target))
    n = max(len(source), len(target))
    src = source + b"\x00" * (n - len(source))
    tgt = target + b"\x00" * (n - len(target))
    rel = 0
    i = 0
    while i < n:
        if src[i] == tgt[i]:
            i += eq_run(src, tgt, i, n)
            continue
        out += vlq_encode(i - rel)
        while i < n and src[i] != tgt[i]:
            out.append(src[i] ^ tgt[i])
            i += 1
        out.append(0)            # the terminator stands for one equal byte
        i += 1
        rel = i
    out += crc32(source).to_bytes(4, "little")
    out += crc32(target).to_bytes(4, "little")
    out += crc32(bytes(out)).to_bytes(4, "little")
    return bytes(out)


# ============================================================================ BPS
@dataclass
class BpsAction:
    command: int
    length: int
    offset: int = 0              # relative offset (copy commands) - signed
    output_offset: int = 0


@dataclass
class BpsInfo:
    source_size: int
    target_size: int
    metadata: str
    source_crc: int
    target_crc: int
    patch_crc: int
    actions: list[BpsAction]


def bps_info(patch: bytes, actions: bool = True) -> BpsInfo:
    src_crc, tgt_crc, pcrc = _crc_footer(patch, BPS_MAGIC)
    pos = 4
    ssize, pos = vlq_decode(patch, pos)
    tsize, pos = vlq_decode(patch, pos)
    msize, pos = vlq_decode(patch, pos)
    meta = patch[pos:pos + msize].decode("utf-8", errors="replace")
    pos += msize
    acts: list[BpsAction] = []
    end = len(patch) - 12
    out = 0
    while actions and pos < end:
        data, pos = vlq_decode(patch, pos)
        cmd, length = data & 3, (data >> 2) + 1
        rel = 0
        if cmd == TARGET_READ:
            pos += length
        elif cmd in (SOURCE_COPY, TARGET_COPY):
            d, pos = vlq_decode(patch, pos)
            rel = (-1 if d & 1 else 1) * (d >> 1)
        acts.append(BpsAction(cmd, length, rel, out))
        out += length
    return BpsInfo(ssize, tsize, meta, src_crc, tgt_crc, pcrc, acts)


def bps_apply(source: bytes, patch: bytes, check: bool = True) -> bytes:
    src_crc, tgt_crc, _p = _crc_footer(patch, BPS_MAGIC)
    pos = 4
    ssize, pos = vlq_decode(patch, pos)
    tsize, pos = vlq_decode(patch, pos)
    msize, pos = vlq_decode(patch, pos)
    pos += msize
    if check:
        if len(source) != ssize or crc32(source) != src_crc:
            raise PatchError(f"this BPS patch is for a different file (expected CRC32 {src_crc:08X}, "
                             f"{ssize} bytes; the file is {crc32(source):08X}, {len(source)} bytes)")
    out = bytearray()
    src_rel = 0
    tgt_rel = 0
    end = len(patch) - 12
    while pos < end:
        data, pos = vlq_decode(patch, pos)
        cmd, length = data & 3, (data >> 2) + 1
        o = len(out)
        if o + length > tsize:
            raise PatchError("the BPS patch writes past the end of the target")
        if cmd == SOURCE_READ:
            if o + length > len(source):
                raise PatchError("BPS SourceRead past the end of the source")
            out += source[o:o + length]
        elif cmd == TARGET_READ:
            if pos + length > end:
                raise PatchError("truncated BPS TargetRead")
            out += patch[pos:pos + length]
            pos += length
        else:
            d, pos = vlq_decode(patch, pos)
            delta = (-1 if d & 1 else 1) * (d >> 1)
            if cmd == SOURCE_COPY:
                src_rel += delta
                if src_rel < 0 or src_rel + length > len(source):
                    raise PatchError("BPS SourceCopy outside the source")
                out += source[src_rel:src_rel + length]
                src_rel += length
            else:
                tgt_rel += delta
                if tgt_rel < 0 or tgt_rel >= o:
                    raise PatchError("BPS TargetCopy outside the written target")
                if tgt_rel + length <= o:
                    out += out[tgt_rel:tgt_rel + length]
                else:                         # overlapping copy (repeats a pattern): byte by byte
                    for k in range(length):
                        out.append(out[tgt_rel + k])
                tgt_rel += length
    if len(out) != tsize:
        raise PatchError(f"the BPS patch produced {len(out)} bytes, expected {tsize}")
    result = bytes(out)
    if check and crc32(result) != tgt_crc:
        raise PatchError(f"the patched file has a wrong CRC32 ({crc32(result):08X}, expected {tgt_crc:08X})")
    return result


def _signed(delta: int) -> bytes:
    return vlq_encode((abs(delta) << 1) | (1 if delta < 0 else 0))


def bps_create(source: bytes, target: bytes, metadata: str = "", *, search: bool = True) -> bytes:
    """A BPS patch. Runs equal to the source at the same place become SourceRead, runs of one repeated byte
    TargetCopy, and (with *search*) blocks found elsewhere in the source SourceCopy; the rest TargetRead."""
    out = bytearray(BPS_MAGIC)
    meta = metadata.encode("utf-8")
    out += vlq_encode(len(source)) + vlq_encode(len(target)) + vlq_encode(len(meta)) + meta
    n, m = len(source), len(target)
    state = {"src_rel": 0, "tgt_rel": 0}
    pending = bytearray()        # TargetRead bytes not written yet

    def action(cmd: int, length: int) -> None:
        out.extend(vlq_encode(((length - 1) << 2) | cmd))

    def flush() -> None:
        if pending:
            action(TARGET_READ, len(pending))
            out.extend(pending)
            pending.clear()

    step = 8 * (1 + n // (4 << 20))          # sampled source index: one key every *step* bytes
    klen = max(16, 2 * step)
    index: dict | None = None

    def find_in_source(i: int) -> int:
        nonlocal index
        if index is None:
            index = {}
            for pos in range(0, n - klen + 1, step):
                index.setdefault(source[pos:pos + klen], pos)
        for d in range(step):
            j = index.get(target[i + d:i + d + klen])
            if j is not None and j - d >= 0 and source[j - d:j] == target[i:i + d]:
                return j - d
        return -1

    i = 0
    while i < m:
        # 1. SourceRead: same bytes at the same offset
        run = eq_run(source, target, i, min(m, n))
        if run >= 4 or (run and i + run == m):
            flush()
            action(SOURCE_READ, run)
            i += run
            continue
        # 2. TargetCopy: a run of one byte value (copies the previous output byte)
        b = target[i]
        rep = 1
        while i + rep < m and target[i + rep] == b:
            rep += 1
        if rep >= 6:
            pending.append(b)                # write the first byte, then copy it from the target
            flush()
            delta = i - state["tgt_rel"]
            action(TARGET_COPY, rep - 1)
            out.extend(_signed(delta))
            state["tgt_rel"] = i + rep - 1
            i += rep
            continue
        # 3. SourceCopy: the next bytes exist elsewhere in the source
        if search and i + klen + step <= m and n >= klen:
            j = find_in_source(i)
            if j >= 0:
                k = eq_run_at(source, j, target, i, min(n - j, m - i))
                flush()
                action(SOURCE_COPY, k)
                out.extend(_signed(j - state["src_rel"]))
                state["src_rel"] = j + k
                i += k
                continue
        pending.append(target[i])
        i += 1
    flush()
    out += crc32(source).to_bytes(4, "little")
    out += crc32(target).to_bytes(4, "little")
    out += crc32(bytes(out)).to_bytes(4, "little")
    return bytes(out)


# ============================================================================ generic
def apply_patch(source: bytes, patch: bytes, check: bool = True) -> bytes:
    fmt = patch_format(patch)
    if fmt == "ips":
        return ips_apply(source, patch)
    if fmt == "ups":
        return ups_apply(source, patch, check)
    if fmt == "bps":
        return bps_apply(source, patch, check)
    raise PatchError("unknown patch format (expected IPS, UPS or BPS)")


def create_patch(source: bytes, target: bytes, fmt: str, metadata: str = "") -> bytes:
    fmt = fmt.lower().lstrip(".")
    if fmt == "ips":
        return ips_create(source, target)
    if fmt == "ups":
        return ups_create(source, target)
    if fmt == "bps":
        return bps_create(source, target, metadata)
    raise PatchError(f"unknown patch format: {fmt}")


def describe_patch(patch: bytes) -> list[tuple[str, str]]:
    """(name, value) rows for the info panel."""
    fmt = patch_format(patch)
    rows: list[tuple[str, str]] = [("Format", fmt.upper() or "unknown"), ("Patch size", f"{len(patch):,} bytes")]
    try:
        if fmt == "ips":
            p = ips_parse(patch)
            rle = sum(1 for r in p.records if r.rle_count)
            rows += [("Records", f"{len(p.records)} ({rle} RLE)"),
                     ("Bytes written", f"{sum(r.size for r in p.records):,}")]
            if p.records:
                rows.append(("Highest offset", f"0x{max(r.offset + r.size for r in p.records) - 1:06X}"))
            if p.truncate is not None:
                rows.append(("Truncate to", f"{p.truncate:,} bytes"))
        elif fmt == "ups":
            u = ups_info(patch)
            rows += [("Source size", f"{u.source_size:,}"), ("Target size", f"{u.target_size:,}"),
                     ("Source CRC32", f"{u.source_crc:08X}"), ("Target CRC32", f"{u.target_crc:08X}"),
                     ("Hunks", str(u.hunks))]
        elif fmt == "bps":
            b = bps_info(patch)
            counts = [sum(1 for a in b.actions if a.command == c) for c in range(4)]
            rows += [("Source size", f"{b.source_size:,}"), ("Target size", f"{b.target_size:,}"),
                     ("Source CRC32", f"{b.source_crc:08X}"), ("Target CRC32", f"{b.target_crc:08X}"),
                     ("Actions", ", ".join(f"{BPS_ACTIONS[c]} {counts[c]}" for c in range(4)))]
            if b.metadata:
                rows.append(("Metadata", b.metadata[:200]))
    except PatchError as e:
        rows.append(("Error", str(e)))
    return rows


__all__ = ["PatchError", "apply_patch", "create_patch", "describe_patch", "patch_format", "crc32",
           "ips_apply", "ips_create", "ips_parse", "ups_apply", "ups_create", "ups_info",
           "bps_apply", "bps_create", "bps_info", "vlq_encode", "vlq_decode"]
