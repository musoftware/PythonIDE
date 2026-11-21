"""Checksum finder: try known algorithms over candidate ranges to locate stored checksums that match the
ORIGINAL file.  Every hit is only a candidate - the user confirms it (and should cross-check it on a second
original of the same family) before it becomes a verified checksum block.

Search geometry (offsets are file offsets; "boundaries" are 0, the file end, every multiple of the
granularity and any start / end hints):

* after  - value stored right after the covered range:      [s, p) stored at p        (p near a boundary)
           also with a complement copy just before the value: [s, p-w) ~v at p-w, v at p
* before - value stored right before the covered range:     v at p, [p+w, e)          (p just after a boundary)
* hole   - like "after" with one skipped hole inside the range: [s, h0) + [h1, p)  (option, or given holes)

Ranges start / end on boundaries; stored values sit within ``window`` bytes of a boundary, aligned to
``align``.  A hit stored next to its ones' complement gets ``complement_at``.  8-bit algorithms are left
out by default (too many accidental matches), as are stored values made of one repeated byte (00 00, FF FF).
Pure-Python CRCs (polynomials other than 0x04C11DB7 / 0x1021) and Fletcher run under a byte budget; skipped
work is listed in ``FindResult.notes``.
"""
from __future__ import annotations

import math
import zlib
from dataclasses import dataclass, field

from . import algorithms as A
from .blocks import ChecksumBlock, hx

DEFAULT_ALGORITHMS = [n for n, p in A.PRESETS.items()
                      if p["type"] != "fletcher16" and p["type"] != "fletcher32" and
                      A.resolve(n)["width"] >= 16]


@dataclass
class Candidate:
    algorithm: str
    ranges: list
    skip: list
    store: int
    width: int
    endian: str
    value: int
    mode: str
    complement_at: int = -1
    score: float = 0.0

    @property
    def length(self) -> int:
        return sum(e - s for s, e in self.ranges) - sum(e - s for s, e in self.skip)

    def describe(self) -> str:
        rng = ", ".join(f"{hx(s)}-{hx(e)}" for s, e in self.ranges)
        sk = (" skip " + ", ".join(f"{hx(s)}-{hx(e)}" for s, e in self.skip)) if self.skip else ""
        comp = f" + complement at {hx(self.complement_at)}" if self.complement_at >= 0 else ""
        return (f"{self.algorithm} over {rng}{sk} -> {self.value:0{self.width * 2}X} stored "
                f"{self.endian.upper()} at {hx(self.store)}{comp} [{self.mode}]")

    def to_block(self, name: str = "") -> ChecksumBlock:
        return ChecksumBlock(name or f"{self.algorithm} @ {hx(self.store)}", self.algorithm, list(self.ranges),
                             list(self.skip), self.store, self.width, self.endian, self.complement_at, "skip",
                             note=f"found by the checksum finder ({self.mode}); confirm before use")


@dataclass
class FindResult:
    candidates: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    tried: int = 0


def _trivial(raw: bytes) -> bool:
    return len(set(raw)) <= 1


class _Prefix:
    """Prefix sums / xors of the units of the file, for O(1) range sums."""

    def __init__(self, data: bytes):
        self.data = data
        self.cache = {}

    def get(self, kind: str, unit: int, endian: str):
        key = (kind, unit, endian)
        if key not in self.cache:
            import numpy as np
            n = len(self.data) - len(self.data) % unit
            u = A.units(self.data[:n], unit, endian) if unit > 1 else np.frombuffer(self.data, dtype=np.uint8)
            u = np.asarray(u, dtype=np.uint64)
            acc = np.cumsum(u, dtype=np.uint64) if kind == "sum" else np.bitwise_xor.accumulate(u)
            self.cache[key] = np.concatenate([np.zeros(1, dtype=np.uint64), acc])
        return self.cache[key]


def _is_fast(d: dict) -> bool:
    if d["type"] == "crc":
        return (d["width"], d["poly"]) in ((32, 0x04C11DB7), (16, 0x1021))
    return d["type"] in ("sum", "xor", "adler32")


class _Algo:
    """One algorithm prepared for the search: range values from prefixes or incremental states."""

    def __init__(self, name: str, pre: _Prefix):
        self.name = name
        self.d = A.resolve(name)
        self.pre = pre
        self.w = (self.d["width"] + 7) // 8
        self.mask = (1 << (8 * self.w)) - 1
        t = self.d["type"]
        self.prefix = t in ("sum", "xor") and self.d["unit"] <= 4
        self.unit = self.d.get("unit", 2 if t == "fletcher32" else 1)
        self.fast = _is_fast(self.d)
        if self.prefix:
            self.arr = pre.get(t, self.unit, self.d["unit_endian"])

    def ok_pos(self, *offs) -> bool:
        return all(o % self.unit == 0 for o in offs)

    # -- prefix algorithms
    def raw(self, s: int, e: int) -> int:
        u = self.unit
        if self.d["type"] == "sum":
            return int(self.arr[e // u]) - int(self.arr[s // u])
        return int(self.arr[e // u]) ^ int(self.arr[s // u])

    def value_segments(self, segs) -> int:
        d = self.d
        if self.prefix:
            if d["type"] == "sum":
                return A.finish_sum(sum(self.raw(s, e) for s, e in segs), d)
            x = 0
            for s, e in segs:
                x ^= self.raw(s, e)
            if d["complement"] == "ones":
                x = ~x
            return x & self.mask
        st = self.start()
        for s, e in segs:
            st = self.update(st, self.pre.data[s:e])
        return self.finish(st)

    # -- incremental algorithms
    def start(self):
        t = self.d["type"]
        if t == "crc":
            return A.reflect(self.d["init"], self.d["width"]) if self.d["refin"] else self.d["init"]
        if t == "adler32":
            return 1
        return (0, 0)

    def update(self, st, chunk):
        t = self.d["type"]
        if t == "crc":
            return A.crc_register(chunk, self.d, st)
        if t == "adler32":
            return zlib.adler32(chunk, st)
        s1, s2 = st
        if t == "fletcher16":
            for b in chunk:
                s1 = (s1 + b) % 255
                s2 = (s2 + s1) % 255
            return (s1, s2)
        for w in A.units(chunk, 2, self.d["unit_endian"]):
            s1 = (s1 + int(w)) % 65535
            s2 = (s2 + s1) % 65535
        return (s1, s2)

    def finish(self, st) -> int:
        t = self.d["type"]
        if t == "crc":
            return A.crc_finish(st, self.d) & self.mask
        if t == "adler32":
            return st & 0xFFFFFFFF
        s1, s2 = st
        return ((s2 << 16) | s1) if t == "fletcher32" else ((s2 << 8) | s1)


def complement_pairs(data, widths=(2, 4), align: int = 2, limit: int = 2000) -> list[tuple[int, int, str]]:
    """Places where a value is directly followed by its ones' complement: [(offset, width, endian)].
    Endianness does not matter for the pair itself; 'be' is reported.  Repeated-byte values are skipped."""
    out = []
    import numpy as np
    arr = np.frombuffer(bytes(data), dtype=np.uint8)
    n = len(arr)
    for w in widths:
        if n < 2 * w:
            continue
        m = n - 2 * w + 1
        ok = np.ones(m, dtype=bool)
        for i in range(w):
            ok &= (arr[i:i + m] ^ arr[w + i:w + i + m]) == 0xFF
        for p in np.nonzero(ok)[0]:
            p = int(p)
            if p % align or _trivial(bytes(data[p:p + w])):
                continue
            out.append((p, w, "be"))
            if len(out) >= limit:
                return out
    return out


def find(data, algorithms=None, *, granularity: int | None = None, starts=None, ends=None, holes=None,
         search_holes: bool = False, window: int = 16, align: int | None = None, min_length: int = 16,
         include_8bit: bool = False, allow_trivial: bool = False, max_results: int = 50,
         slow_budget: int = 6_000_000, progress=None, cancel=None) -> FindResult:
    """Search *data* for stored checksums.  See the module docstring for the geometry."""
    data = bytes(data)
    n = len(data)
    res = FindResult()
    if n < 32:
        res.notes.append("file too small")
        return res
    names = list(algorithms or DEFAULT_ALGORITHMS)
    if not include_8bit:
        dropped = [x for x in names if A.resolve(x)["width"] < 16]
        names = [x for x in names if x not in dropped]
        if dropped:
            res.notes.append("8-bit algorithms skipped (enable 'include 8-bit' to try them): " + ", ".join(dropped))
    if granularity is None:
        granularity = 0x100
        while n // granularity > 64:
            granularity <<= 1
    bounds = set(range(0, n + 1, granularity)) | {0, n}
    starts_set = sorted({b for b in bounds if b < n} | {int(s) for s in starts or [] if 0 <= int(s) < n})
    ends_set = sorted({b for b in bounds if b > 0} | {int(e) for e in ends or [] if 0 < int(e) <= n})
    allb = sorted(set(starts_set) | set(ends_set))
    pre = _Prefix(data)
    found: dict = {}
    budget = [slow_budget]
    skipped_slow = set()

    def stored_at(p: int, w: int):
        raw = data[p:p + w]
        return raw, int.from_bytes(raw, "big"), int.from_bytes(raw, "little")

    def add(al: _Algo, ranges, skip, p, value, mode, endian, comp_at=-1):
        key = (al.name, p)
        length = sum(e - s for s, e in ranges) - sum(e - s for s, e in skip)
        score = math.log2(max(length, 2))
        end_of = ranges[-1][1]
        if (p + al.w) in bounds or p in bounds or end_of in bounds:
            score += 3
        if all(s in bounds for s, _ in ranges):
            score += 1
        if comp_at >= 0:
            score += 6
        if al.w >= 4:
            score += 3
        if mode == "hole":
            score -= 2
        seg = data[ranges[0][0]:ranges[0][1]]
        if len(set(seg[:4096])) <= 1:
            score -= 8                                   # an erased / constant range is weak evidence
        c = Candidate(al.name, list(ranges), list(skip), p, al.w, endian, value, mode, comp_at, round(score, 2))
        old = found.get(key)
        if old is None or c.score > old.score:
            found[key] = c

    def check(al: _Algo, value: int, p: int, ranges, skip, mode):
        raw, be, le = stored_at(p, al.w)
        if len(raw) < al.w or (not allow_trivial and _trivial(raw)):
            return
        for endian, v in (("be", be), ("le", le)):
            if v == value:
                comp_at = -1
                bo = "big" if endian == "be" else "little"
                nv = (~value & al.mask).to_bytes(al.w, bo)
                if data[p + al.w:p + 2 * al.w] == nv:
                    comp_at = p + al.w
                elif p >= al.w and data[p - al.w:p] == nv and ranges[-1][1] <= p - al.w:
                    comp_at = p - al.w
                add(al, ranges, skip, p, value, mode, endian, comp_at)
                if be == le:
                    break

    def positions_near(points, after_only=False):
        out = set()
        for b in points:
            lo = b if after_only else b - window
            for p in range(max(0, lo - lo % a), min(n, b + window), a):
                out.add(p)
        return sorted(out)

    def spend(al: _Algo, nbytes: int, mode: str) -> bool:
        if al.fast:
            return True
        if budget[0] - nbytes < 0:
            skipped_slow.add(f"{al.name} ({mode})")
            return False
        budget[0] -= nbytes
        return True

    algos = []
    for nm in names:
        try:
            algos.append(_Algo(nm, pre))
        except A.AlgorithmError as e:
            res.notes.append(f"{nm}: {e}")
    total = max(1, len(algos))
    for i, al in enumerate(algos):
        if cancel is not None and cancel():
            res.notes.append("cancelled")
            break
        if progress is not None:
            progress(i, total, al.name)
        a = align or (1 if al.w == 1 else 2)
        a = max(a, al.unit)
        w = al.w
        p_after = [p for p in positions_near(allb) if p + w <= n]
        # ---------------- after: [s, p) stored at p  (+ complement just before the value)
        for s in starts_set:
            ps = [p for p in p_after if p - s >= min_length and al.ok_pos(s, p)]
            if not ps:
                continue
            if al.prefix:
                for p in ps:
                    res.tried += 1
                    check(al, al.value_segments([(s, p)]), p, [(s, p)], [], "after")
                    if p - w - s >= min_length and al.ok_pos(p - w):
                        res.tried += 1
                        check(al, al.value_segments([(s, p - w)]), p, [(s, p - w)], [], "after")
                continue
            if not spend(al, ps[-1] - s, "after"):
                continue
            st, cur = al.start(), s
            for p in ps:
                for q in ((p - w,) if p - w - s >= min_length and p - w >= cur else ()):
                    st = al.update(st, data[cur:q])
                    cur = q
                    res.tried += 1
                    check(al, al.finish(st), p, [(s, q)], [], "after")
                st = al.update(st, data[cur:p])
                cur = p
                res.tried += 1
                check(al, al.finish(st), p, [(s, p)], [], "after")
        # ---------------- before: v at p, [p+w, e)  (or [p+2w, e) when a complement copy follows)
        for p in positions_near(starts_set, after_only=True):
            for gap in (w, 2 * w):
                s = p + gap
                es = [e for e in ends_set if e - s >= min_length and al.ok_pos(s, e)]
                if not es or p + w > n:
                    continue
                if al.prefix:
                    for e in es:
                        res.tried += 1
                        check(al, al.value_segments([(s, e)]), p, [(s, e)], [], "before")
                    continue
                if not spend(al, es[-1] - s, "before"):
                    continue
                st, cur = al.start(), s
                for e in es:
                    st = al.update(st, data[cur:e])
                    cur = e
                    res.tried += 1
                    check(al, al.finish(st), p, [(s, e)], [], "before")
        # ---------------- hole: [s, h0) + [h1, p) stored at p
        hole_list = [(int(h0), int(h1)) for h0, h1 in holes or [] if 0 <= int(h0) < int(h1) <= n]
        if search_holes:
            blocks_ = list(zip(allb, allb[1:]))
            hole_list += [h for h in blocks_ if h not in hole_list]
        if hole_list:
            for s in starts_set:
                for h0, h1 in hole_list:
                    if h0 <= s or not al.ok_pos(s, h0, h1):
                        continue
                    ps = [p for p in p_after if p > h1 and p - h1 >= 4 and al.ok_pos(p)]
                    if not ps or (h0 - s) < min_length:
                        continue
                    if al.prefix:
                        for p in ps:
                            res.tried += 1
                            check(al, al.value_segments([(s, h0), (h1, p)]), p, [(s, p)], [(h0, h1)], "hole")
                        continue
                    if not spend(al, (h0 - s) + (ps[-1] - h1), "hole"):
                        continue
                    st = al.update(al.start(), data[s:h0])
                    cur = h1
                    for p in ps:
                        st = al.update(st, data[cur:p])
                        cur = p
                        res.tried += 1
                        check(al, al.finish(st), p, [(s, p)], [(h0, h1)], "hole")
    if progress is not None:
        progress(total, total, "")
    if skipped_slow:
        res.notes.append("Pure-Python algorithms skipped over the byte budget (narrow the search with start / end "
                         "hints or a larger granularity): " + ", ".join(sorted(skipped_slow)))
    cands = sorted(found.values(), key=lambda c: (-c.score, c.store))
    # keep the best explanation per stored location (a value may match several algorithms only by chance)
    res.candidates = cands[:max_results]
    return res


def confirm(data, cand: Candidate) -> bool:
    """Re-compute a candidate from scratch as a ChecksumBlock (guards the finder's shortcuts)."""
    b = cand.to_block()
    return not b.problems(len(data)) and b.compute(data) == b.read_stored(data)


__all__ = ["find", "FindResult", "Candidate", "complement_pairs", "confirm", "DEFAULT_ALGORITHMS"]
