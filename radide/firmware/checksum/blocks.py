"""User-defined checksum blocks: which bytes are covered, which algorithm, where the result is stored.

A block (JSON, in ecu.json "checksums" or in a shareable profile):

    {"name": "Calibration CRC", "algorithm": "crc32",            # preset name or algorithm dict (algorithms.py)
     "ranges": [["0x10000", "0x18000"], ["0x19000", "0x20000"]],  # [start, end) - end exclusive
     "skip":   [["0x17F00", "0x17F10"]],                         # bytes left out of the ranges
     "store": "0x1FFFC", "width": 4, "endian": "be",             # where the value lives
     "complement_at": "0x1FFF8",                                 # optional copy of ~value (complement pair)
     "store_mode": "skip",                                       # the stored bytes: "skip" | "fill00" | "fillFF"
     "repeat": {"count": 8, "stride": "0x100"},                  # optional: a multipoint list of equal blocks
     "enabled": true, "verified": false, "note": "..."}

Blocks are verified / corrected in list order, so a block whose ranges cover another block's stored value
comes after it.  A block is *verified* once the user confirmed it matches the original file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import algorithms as A

PROFILE_FORMAT = "radide-checksum-profile"


def to_int(v, default: int = 0) -> int:
    if v is None or v == "":
        return default
    if isinstance(v, str):
        return int(v.strip().replace("_", ""), 0)
    return int(v)


def hx(v: int) -> str:
    return f"0x{v:X}"


def _ranges(v) -> list[tuple[int, int]]:
    out = []
    for r in v or []:
        if isinstance(r, dict):
            s, e = to_int(r.get("start")), r.get("end")
            e = to_int(e) if e is not None else s + to_int(r.get("length"))
        else:
            s, e = to_int(r[0]), to_int(r[1])
        if e > s:
            out.append((s, e))
    return out


def subtract(ranges, holes) -> list[tuple[int, int]]:
    """*ranges* minus *holes* (both lists of [start, end)), order of *ranges* kept."""
    out = []
    holes = sorted(h for h in holes if h[1] > h[0])
    for s, e in ranges:
        cur = s
        for hs, he in holes:
            if he <= cur or hs >= e:
                continue
            if hs > cur:
                out.append((cur, hs))
            cur = max(cur, he)
        if cur < e:
            out.append((cur, e))
    return out


@dataclass
class ChecksumBlock:
    name: str = "Checksum"
    algorithm: object = "crc32"
    ranges: list = field(default_factory=list)
    skip: list = field(default_factory=list)
    store: int = 0
    width: int = 0                       # bytes; 0 = from the algorithm
    endian: str = "be"
    complement_at: int = -1
    store_mode: str = "skip"
    repeat_count: int = 1
    repeat_stride: int = 0
    enabled: bool = True
    verified: bool = False
    note: str = ""

    # ---------------------------------------------------------------- json
    @classmethod
    def from_dict(cls, d: dict) -> "ChecksumBlock":
        rep = d.get("repeat") or {}
        ca = d.get("complement_at")
        b = cls(str(d.get("name") or "Checksum"), d.get("algorithm") or "crc32", _ranges(d.get("ranges")),
                _ranges(d.get("skip")), to_int(d.get("store")), to_int(d.get("width")),
                "le" if str(d.get("endian", "be")).lower() == "le" else "be",
                -1 if ca in (None, "", -1) else to_int(ca),
                str(d.get("store_mode") or "skip"), max(1, to_int(rep.get("count"), 1)), to_int(rep.get("stride")),
                bool(d.get("enabled", True)), bool(d.get("verified", False)), str(d.get("note") or ""))
        A.resolve(b.algorithm)                 # raises AlgorithmError for a bad definition
        return b

    def to_dict(self) -> dict:
        d = {"name": self.name, "algorithm": self.algorithm,
             "ranges": [[hx(s), hx(e)] for s, e in self.ranges],
             "store": hx(self.store), "width": self.value_width, "endian": self.endian}
        if self.skip:
            d["skip"] = [[hx(s), hx(e)] for s, e in self.skip]
        if self.complement_at >= 0:
            d["complement_at"] = hx(self.complement_at)
        if self.store_mode != "skip":
            d["store_mode"] = self.store_mode
        if self.repeat_count > 1:
            d["repeat"] = {"count": self.repeat_count, "stride": hx(self.repeat_stride)}
        d.update({"enabled": self.enabled, "verified": self.verified})
        if self.note:
            d["note"] = self.note
        return d

    # ---------------------------------------------------------------- geometry
    @property
    def value_width(self) -> int:
        return self.width or A.width_bytes(self.algorithm)

    def expand(self) -> list["ChecksumBlock"]:
        """A multipoint block -> its single blocks (one element for a normal block)."""
        if self.repeat_count <= 1:
            return [self]
        out = []
        for i in range(self.repeat_count):
            k = i * self.repeat_stride
            out.append(ChecksumBlock(f"{self.name} #{i + 1}", self.algorithm,
                                     [(s + k, e + k) for s, e in self.ranges], [(s + k, e + k) for s, e in self.skip],
                                     self.store + k, self.width, self.endian,
                                     self.complement_at + k if self.complement_at >= 0 else -1, self.store_mode,
                                     1, 0, self.enabled, self.verified, self.note))
        return out

    def stored_spans(self) -> list[tuple[int, int]]:
        w = self.value_width
        spans = [(self.store, self.store + w)]
        if self.complement_at >= 0:
            spans.append((self.complement_at, self.complement_at + w))
        return spans

    def segments(self) -> list[tuple[int, int]]:
        holes = list(self.skip) + (self.stored_spans() if self.store_mode == "skip" else [])
        return subtract(self.ranges, holes)

    def problems(self, size: int) -> list[str]:
        out = []
        try:
            A.resolve(self.algorithm)
        except A.AlgorithmError as e:
            out.append(str(e))
        if not self.ranges:
            out.append("no ranges")
        for s, e in self.ranges:
            if e > size:
                out.append(f"range {hx(s)}-{hx(e)} is past the end of the file ({hx(size)})")
        for s, e in self.stored_spans():
            if e > size:
                out.append(f"stored value at {hx(s)} is past the end of the file")
        return out

    # ---------------------------------------------------------------- values
    def parts(self, data) -> list:
        mv = memoryview(data)
        segs = self.segments()
        if self.store_mode in ("fill00", "fillFF"):
            fill = 0 if self.store_mode == "fill00" else 0xFF
            spans = self.stored_spans()
            out = []
            for s, e in segs:
                chunk = bytes(mv[s:e])
                if any(ss < e and se > s for ss, se in spans):
                    ba = bytearray(chunk)
                    for ss, se in spans:
                        for i in range(max(ss, s), min(se, e)):
                            ba[i - s] = fill
                    chunk = bytes(ba)
                out.append(chunk)
            return out
        return [mv[s:e] for s, e in segs]

    def compute(self, data) -> int:
        v = A.compute_parts(self.parts(data), self.algorithm)
        return v & ((1 << (8 * self.value_width)) - 1)

    def _bo(self) -> str:
        return "little" if self.endian == "le" else "big"

    def read_stored(self, data) -> int:
        return int.from_bytes(bytes(data[self.store:self.store + self.value_width]), self._bo())

    def read_complement(self, data) -> int | None:
        if self.complement_at < 0:
            return None
        return int.from_bytes(bytes(data[self.complement_at:self.complement_at + self.value_width]), self._bo())

    def write(self, data: bytearray, value: int) -> None:
        w = self.value_width
        mask = (1 << (8 * w)) - 1
        data[self.store:self.store + w] = (value & mask).to_bytes(w, self._bo())
        if self.complement_at >= 0:
            data[self.complement_at:self.complement_at + w] = (~value & mask).to_bytes(w, self._bo())


@dataclass
class BlockResult:
    name: str
    store: int
    width: int
    stored: int = 0
    computed: int = 0
    complement_ok: bool | None = None
    error: str = ""
    corrected: bool = False
    old: int = 0

    @property
    def ok(self) -> bool:
        return not self.error and self.stored == self.computed and self.complement_ok is not False

    def value_text(self, v: int) -> str:
        return f"{v:0{self.width * 2}X}"

    def line(self) -> str:
        if self.error:
            return f"{self.name}: ERROR {self.error}"
        if self.corrected:
            return (f"{self.name} @ {hx(self.store)}: recalculated {self.value_text(self.old)} -> "
                    f"{self.value_text(self.computed)}")
        state = "OK" if self.ok else "MISMATCH"
        comp = "" if self.complement_ok is None else ("" if self.complement_ok else " (complement copy wrong)")
        return (f"{self.name} @ {hx(self.store)}: {state} stored {self.value_text(self.stored)} computed "
                f"{self.value_text(self.computed)}{comp}")


def _expand_all(blocks) -> list[ChecksumBlock]:
    out = []
    for b in blocks:
        if b.enabled:
            out.extend(b.expand())
    return out


def verify(data, blocks) -> list[BlockResult]:
    res = []
    for b in _expand_all(blocks):
        r = BlockResult(b.name, b.store, b.value_width)
        probs = b.problems(len(data))
        if probs:
            r.error = "; ".join(probs)
        else:
            r.stored = b.read_stored(data)
            r.computed = b.compute(data)
            comp = b.read_complement(data)
            if comp is not None:
                r.complement_ok = comp == (~r.stored & ((1 << (8 * b.value_width)) - 1))
        res.append(r)
    return res


def correct(data: bytearray, blocks) -> list[BlockResult]:
    """Recalculate every enabled block in order and write the values into *data* (a bytearray).
    Each result says whether the block changed (``corrected``) and its old / new value."""
    res = []
    for b in _expand_all(blocks):
        r = BlockResult(b.name, b.store, b.value_width)
        probs = b.problems(len(data))
        if probs:
            r.error = "; ".join(probs)
            res.append(r)
            continue
        r.old = b.read_stored(data)
        comp_before = b.read_complement(data)
        r.computed = b.compute(data)
        mask = (1 << (8 * b.value_width)) - 1
        if r.old != r.computed or (comp_before is not None and comp_before != (~r.computed & mask)):
            b.write(data, r.computed)
            r.corrected = True
        r.stored = b.read_stored(data)
        if b.complement_at >= 0:
            r.complement_ok = True
        res.append(r)
    return res


def report(results, title: str = "Checksums") -> str:
    if not results:
        return f"{title}: no checksum blocks defined."
    fixed = sum(1 for r in results if r.corrected)
    bad = sum(1 for r in results if not r.ok and not r.corrected)
    head = f"{title}: {len(results)} block(s), {fixed} recalculated, {bad} with problems"
    return "\n".join([head] + ["  " + r.line() for r in results])


# ---------------------------------------------------------------------------------------------- profiles
def blocks_from_json(items) -> list[ChecksumBlock]:
    return [ChecksumBlock.from_dict(d) for d in items or [] if isinstance(d, dict)]


def blocks_to_json(blocks) -> list[dict]:
    return [b.to_dict() for b in blocks]


def save_profile(path, blocks, name: str = "", description: str = "", file_size: int | None = None) -> Path:
    p = Path(path)
    d = {"format": PROFILE_FORMAT, "version": 1, "name": name or p.stem, "description": description,
         "disclaimer": "User-defined checksum profile. Verify it against your own original file before use; "
                       "it is not a manufacturer specification.",
         "blocks": blocks_to_json(blocks)}
    if file_size:
        d["file_size"] = file_size
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def load_profile(path) -> tuple[dict, list[ChecksumBlock]]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(d, list):
        return {"name": Path(path).stem}, blocks_from_json(d)
    if d.get("format") not in (None, PROFILE_FORMAT):
        raise ValueError(f"{Path(path).name} is not a RAD IDE checksum profile")
    return {k: v for k, v in d.items() if k != "blocks"}, blocks_from_json(d.get("blocks"))


__all__ = ["ChecksumBlock", "BlockResult", "verify", "correct", "report", "subtract", "save_profile",
           "load_profile", "blocks_from_json", "blocks_to_json", "to_int", "hx", "PROFILE_FORMAT"]
