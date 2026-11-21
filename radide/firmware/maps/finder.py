"""Map finder: heuristics that locate calibration tables in a firmware binary (the "Potential maps" list).

How it works (numpy, a few hundred ms per MB):

1. **Axis runs.** The file is read as 8-bit, 16-bit (LE / BE, unsigned / signed, both alignments) and 32-bit float
   (LE / BE, every alignment) cells; every strictly increasing run of 4..64 cells is a possible axis (breakpoints).
2. **Layouts** tried around each run:
   * Bosch-style header: ``[nx][ny][X axis][Y axis][values]`` (also ``[ny][nx]``) and ``[n][axis][values]`` for
     curves - the size cells have the axis' data type;
   * headerless: ``[X axis][Y axis][values]`` (two runs back to back) and ``[axis][values]`` (curve).
3. **Values.** The value block is read as unsigned and signed (same width as the axis) in row order (X fastest)
   and column order; a calibration surface is *smooth* (each row / column changes little and mostly in one
   direction), random code / data is not. The best interpretation wins.
4. **Score** 0..100 from smoothness, axis quality, size and how much the layout is backed by a header; overlapping
   candidates keep the best one.
5. **Axis-less blocks** (optional): regions whose rows look alike at a fixed row width - tables whose axes live
   elsewhere - are reported with a lower score.

:func:`find_maps` returns :class:`Candidate` objects (``.mapdef`` is a ready :class:`MapDef`).
:func:`value_profile` gives the down-sampled value graph of the whole file for the "2D view".
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import numpy as np

from .model import AxisDef, MapDef, dtype_size, np_dtype

MIN_AXIS = 4
MAX_AXIS = 64

# (axis dtype, endian, alignments); values are tried as the unsigned / signed type of the same width
SCAN_TYPES = [
    ("u8", "le", (0,)),
    ("u16", "le", (0, 1)), ("u16", "be", (0, 1)),
    ("s16", "le", (0, 1)), ("s16", "be", (0, 1)),
    ("f32", "le", (0, 1, 2, 3)), ("f32", "be", (0, 1, 2, 3)),
]
VALUE_TYPES = {"u8": ("u8", "s8"), "u16": ("u16", "s16"), "s16": ("s16", "u16"), "f32": ("f32",)}


@dataclass
class Candidate:
    mapdef: MapDef
    score: float
    layout: str = ""                  # "header", "header-curve", "axes", "curve", "axisless"
    details: dict = field(default_factory=dict)

    @property
    def address(self) -> int:
        return self.mapdef.address

    def span(self) -> tuple[int, int]:
        return self.mapdef.span()

    def label(self) -> str:
        m = self.mapdef
        dims = f"{m.cols}x{m.rows}" if m.rows > 1 else f"{m.cols}"
        return f"0x{m.address:X}  {dims}  {m.dtype}  {self.score:.0f}"


# ====================================================================== scoring helpers
def smoothness(z: np.ndarray, raw_lo: float | None = None, raw_hi: float | None = None) -> float:
    """0..1: how much *z* (rows, cols) looks like a calibration surface / curve.

    Mix of: monotony of the lines (total variation / span), small steps next to the value range, small curvature
    (|2nd differences| next to |1st differences|); penalties for jumps across the range (a signed table read
    unsigned, random data), two-valued tables (flags) and cells glued to the type's extremes (fill)."""
    z = np.asarray(z, dtype=np.float64)
    if z.size < 2 or not np.all(np.isfinite(z)):
        return 0.0
    zmin, zmax = float(z.min()), float(z.max())
    rng = zmax - zmin
    if rng == 0:
        v = zmin
        if v == 0 or (raw_lo is not None and v in (raw_lo, raw_hi)):
            return 0.03                       # fill (00 / FF ...)
        return 0.3
    rows, cols = z.shape
    tv, steps, curv, jumps = [], [], [], []
    for axis, n in ((1, cols), (0, rows)):
        if n < 2:
            continue
        d = np.diff(z, axis=axis)
        ad = np.abs(d)
        line_tv = ad.sum(axis=axis)
        span = z.max(axis=axis) - z.min(axis=axis)
        ok = span > 0
        tv.append(float(np.where(ok, line_tv / np.where(ok, span, 1), 1.0).mean()))
        tot = float(ad.sum())
        steps.append(tot / ad.size)
        jumps.append(float(ad.max()))
        if n > 2:
            curv.append(float(np.abs(np.diff(d, axis=axis)).sum()) / max(1e-12, tot))
    f1 = 1.0 / (sum(tv) / len(tv))
    f2 = min(1.0, max(0.0, 1.0 - 2.5 * (sum(steps) / len(steps)) / rng))
    f3 = min(1.0, max(0.0, 1.0 - (sum(curv) / len(curv)) / 1.4)) if curv else f1
    sc = 0.3 * f1 + 0.3 * f2 + 0.4 * f3
    jump = max(jumps) / rng
    if jump > 0.5:
        sc *= 1.0 - 0.9 * (jump - 0.5)
    if z.size >= 16 and len(np.unique(z)) <= 2:
        sc *= 0.5
    if raw_hi is not None and np.mean((z == raw_hi) | (z == raw_lo)) > 0.5:
        sc *= 0.4
    return sc


def axis_quality(a: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    n = len(a)
    if n < 2:
        return 0.0
    steps = np.diff(a)
    if np.any(steps <= 0):
        return 0.0
    q = 0.6 + 0.4 * min(1.0, n / 12.0)
    if np.all(steps == 1) and a[0] in (0, 1):
        q *= 0.45                             # 0,1,2,3...: an index table
    ratio = steps.max() / max(steps.min(), 1e-12)
    if ratio > 60:
        q *= 0.6
    if abs(a[-1]) > 1e9:
        q *= 0.3
    if n >= 4:                                # an irregular first / last step: a cell that is not part of it
        for s0, s1 in ((steps[0], steps[1]), (steps[-1], steps[-2])):
            r = max(s0, s1) / max(min(s0, s1), 1e-12)
            if r > 4:
                q *= 0.75
    return q


def _value_options(dt):
    return VALUE_TYPES.get(dt, (dt,))


def _rng(dt):
    from .model import DTYPES
    return DTYPES[dt][2], DTYPES[dt][3]


def best_values(data: bytes, off: int, cols: int, rows: int, axis_dt: str, endian: str):
    """Best (score, dtype, order, z) interpretation of the value block at *off*."""
    best = None
    for vdt in _value_options(axis_dt):
        size = dtype_size(vdt)
        n = cols * rows
        if off < 0 or off + n * size > len(data):
            continue
        flat = np.frombuffer(data, dtype=np_dtype(vdt, endian), count=n, offset=off).astype(np.float64)
        lo, hi = _rng(vdt)
        orders = [("row", flat.reshape(rows, cols))]
        if rows > 1 and cols > 1:
            orders.append(("col", flat.reshape(cols, rows).T))
        for order, z in orders:
            sc = smoothness(z, lo, hi)
            if best is None or sc > best[0] + 1e-9:
                best = (sc, vdt, order, z)
    return best


# ====================================================================== the finder
def _runs(arr: np.ndarray, valid: np.ndarray | None):
    inc = arr[1:] > arr[:-1]
    if valid is not None:
        inc &= valid[1:] & valid[:-1]
    pad = np.concatenate(([False], inc, [False])).astype(np.int8)
    d = np.diff(pad)
    starts = np.flatnonzero(d == 1)
    ends = np.flatnonzero(d == -1)           # element indices: run = starts..ends (inclusive)
    lens = ends - starts + 1
    keep = (lens >= MIN_AXIS) & (lens <= MAX_AXIS + 2)
    return starts[keep], lens[keep]


def _as_float(data: bytes, dt: str, endian: str, align: int, n: int) -> np.ndarray:
    raw = np.frombuffer(data, dtype=np_dtype(dt, endian), count=n, offset=align)
    if dt.startswith("f"):
        with np.errstate(invalid="ignore", over="ignore"):
            raw = np.where(np.isfinite(raw), raw, 0)
    return raw.astype(np.float64)


class _Scan:
    """One view of the file (type, byte order, alignment) + cumulative sums for the fast smoothness pre-check."""

    def __init__(self, data: bytes, dt: str, en: str, align: int):
        self.data, self.dt, self.en, self.align = data, dt, en, align
        self.size = dtype_size(dt)
        self.n = (len(data) - align) // self.size
        self.arr = _as_float(data, dt, en, align, self.n) if self.n > 0 else np.zeros(0)
        self.valid = None
        if dt.startswith("f") and self.n:
            a = np.abs(self.arr)
            self.valid = (a < 1e7) & ((a > 1e-6) | (self.arr == 0))
        self.cums = []
        self.diffs = []
        for vdt in _value_options(dt):
            v = self.arr if vdt == dt else _as_float(data, vdt, en, align, self.n)
            if dt.startswith("f"):
                v = np.clip(v, -1e9, 1e9)
            d1 = np.abs(np.diff(v)) if self.n > 1 else np.zeros(0)
            d2 = np.abs(v[2:] - 2 * v[1:-1] + v[:-2]) if self.n > 2 else np.zeros(0)
            self.cums.append((np.concatenate(([0.0], np.cumsum(d1))), np.concatenate(([0.0], np.cumsum(d2)))))
            self.diffs.append((d1, d2))

    def off(self, i: int) -> int:
        return self.align + i * self.size

    def smooth_hint(self, i: int, count: int) -> float:
        """sum|2nd diff| / sum|1st diff| over cells i..i+count (stored order); smooth data < 0.8, noise ~1.4."""
        if count < 3 or i < 0 or i + count > self.n:
            return 9.0
        best = 9.0
        for c1, c2 in self.cums:
            s1 = c1[i + count - 1] - c1[i]
            s2 = c2[i + count - 2] - c2[i]
            r = 0.0 if s1 == 0 else s2 / s1
            best = min(best, r)
        return best


    def smooth_hint_2d(self, i: int, cols: int, rows: int) -> float:
        """Like smooth_hint for a cols x rows block, leaving out the jumps between rows (row order) or columns
        (column order); the better of the two."""
        n = cols * rows
        if rows <= 1:
            return self.smooth_hint(i, n)
        if n < 3 or i < 0 or i + n > self.n:
            return 9.0
        best = 9.0
        for (c1, c2), (d1, d2) in zip(self.cums, self.diffs):
            s1 = c1[i + n - 1] - c1[i]
            s2 = c2[i + n - 2] - c2[i]
            for seg in (cols, rows):
                if seg < 3:
                    continue
                b = i + np.arange(1, n // seg) * seg          # first cell of each later row
                s1b = s1 - d1[b - 1].sum()
                s2b = s2 - d2[b - 2].sum() - d2[b[b - 1 < i + n - 2] - 1].sum()
                r = 0.0 if s1b <= 0 else max(0.0, s2b) / s1b
                best = min(best, r)
        return best


PRE_CURVE = 0.95
PRE_MAP = 1.0


def _pre(n: int, base: float) -> float:
    """Pre-check threshold: stricter for small blocks (few cells make the estimate noisy)."""
    return base * (0.7 if n < 16 else 0.85 if n < 32 else 1.0)


def find_maps(data, *, min_score: float = 35.0, max_results: int = 2000, types=None, axisless: bool = True,
              time_budget: float = 60.0, progress=None, dedupe: bool = True) -> list[Candidate]:
    """Find potential maps in *data* (bytes). Sorted best first, non-overlapping."""
    data = bytes(data)
    t0 = time.time()
    cands: list[Candidate] = []
    scan = [t for t in SCAN_TYPES if types is None or t[0] in types]
    total = sum(len(a) for _d, _e, a in scan) + (1 if axisless else 0)
    step = 0
    for dt, en, aligns in scan:
        for align in aligns:
            step += 1
            if progress is not None:
                progress(step, total)
            if time.time() - t0 > time_budget:
                break
            sc = _Scan(data, dt, en, align)
            if sc.n < MIN_AXIS * 2:
                continue
            starts, lens = _runs(sc.arr, sc.valid)
            if dt.startswith("s"):            # all-positive runs were already seen by the unsigned scan
                neg = np.array([sc.arr[s] < 0 for s in starts.tolist()], dtype=bool)
                starts, lens = starts[neg] if len(neg) else starts, lens[neg] if len(neg) else lens
            run_at = dict(zip(starts.tolist(), lens.tolist()))
            for s, L in zip(starts.tolist(), lens.tolist()):
                cands.extend(_around_run(sc, s, L, run_at))
    if axisless and time.time() - t0 < time_budget:
        step += 1
        if progress is not None:
            progress(step, total)
        cands.extend(find_axisless(data, time_budget=max(1.0, time_budget - (time.time() - t0))))
    cands = [c for c in cands if c.score >= min_score]
    cands.sort(key=lambda c: (-c.score, c.address))
    if not dedupe:
        return cands
    picked: list[Candidate] = []
    taken: list[tuple[int, int]] = []
    import bisect
    for c in cands:
        s, e = c.span()
        i = bisect.bisect_left(taken, (s, s))
        clash = 0 < i and taken[i - 1][1] > s
        k = i
        while not clash and k < len(taken) and taken[k][0] < e:
            clash = s < taken[k][1]
            k += 1
        if clash:
            continue
        bisect.insort(taken, (s, e))
        picked.append(c)
        if len(picked) >= max_results:
            break
    for c in picked:
        m = c.mapdef
        if not m.name:
            m.name = f"Map_{m.address:06X}" if m.rows > 1 else f"Curve_{m.address:06X}"
    return picked


def _is_int(v) -> bool:
    return float(v).is_integer()


def _around_run(sc: _Scan, s: int, L: int, run_at: dict) -> list:
    out = []
    arr, n = sc.arr, sc.n
    is_f = sc.dt.startswith("f")
    # ---- Bosch-style headers (the run may also have swallowed the last header cells: try trims 0..2)
    if not is_f:
        for t in range(0, 3):
            i = s + t
            avail = L - t
            if avail < MIN_AXIS or i < 1:
                continue
            # curve: [n][axis n][values n]
            h = arr[i - 1]
            if MIN_AXIS <= h <= min(avail, MAX_AXIS) and _is_int(h):
                nx = int(h)
                if sc.smooth_hint(i + nx, nx) < _pre(nx, PRE_CURVE):
                    c = _make(sc, i, nx, 1, i + nx, None, "header-curve", 1.0)
                    if c:
                        out.append(c)
            if i < 2:
                continue
            h1, h2 = arr[i - 2], arr[i - 1]
            for nx, ny in ((h1, h2), (h2, h1)):
                if not (_is_int(nx) and _is_int(ny)):
                    continue
                nx, ny = int(nx), int(ny)
                if not (MIN_AXIS <= nx <= min(avail, MAX_AXIS) and 2 <= ny <= MAX_AXIS):
                    continue
                yi = i + nx
                if yi + ny + nx * ny > n:
                    continue
                if not np.all(np.diff(arr[yi:yi + ny]) > 0):
                    continue
                if sc.smooth_hint_2d(yi + ny, nx, ny) >= _pre(nx * ny, PRE_MAP):
                    continue
                c = _make(sc, i, nx, ny, yi + ny, yi, "header", 1.0)
                if c:
                    out.append(c)
                break
    # ---- headerless: [X][Y][values] or [axis][values]; the X run may start one or two cells early
    for t in range(0, 4):
        i = s + t
        nx = L - t
        if nx < MIN_AXIS or nx > MAX_AXIS:
            continue
        yi = i + nx
        ylen = run_at.get(yi)
        if ylen and ylen >= MIN_AXIS - 1:
            # the Y run may have swallowed the first values (values[0] > Y[-1]): try the lengths that pass
            best = None
            for ny in range(MIN_AXIS - 1, min(ylen, MAX_AXIS) + 1):
                if sc.smooth_hint_2d(yi + ny, nx, ny) >= _pre(nx * ny, PRE_MAP):
                    continue
                c = _make(sc, i, nx, ny, yi + ny, yi, "axes", 0.55, t)
                if c and (best is None or c.score > best.score):
                    best = c
            if best:
                out.append(best)
        elif nx >= (6 if sc.size == 1 else 5) and sc.smooth_hint(yi, nx) < _pre(nx, PRE_CURVE):
            c = _make(sc, i, nx, 1, yi, None, "curve", 0.2, t)
            if c:
                out.append(c)
    return out


def _make(sc: _Scan, xi: int, nx: int, ny: int, vi: int, yi, layout: str, hdr: float, trim: int = 0):
    arr = sc.arr
    if vi + nx * ny > sc.n:
        return None
    qx = axis_quality(arr[xi:xi + nx])
    if qx <= 0:
        return None
    qy = 1.0
    if yi is not None:
        qy = axis_quality(arr[yi:yi + ny])
        if qy <= 0:
            return None
    bv = best_values(sc.data, sc.off(vi), nx, ny, sc.dt, sc.en)
    if bv is None:
        return None
    vs, vdt, order, _z = bv
    cells = nx * ny
    vs *= 0.5 + 0.5 * min(1.0, (cells - 2) / 10.0)        # few cells: smoothness says little
    if ny == 1:
        hdr *= min(1.0, (nx - 2) / 6.0)
    elif layout == "axes":
        hdr *= min(1.0, (nx - 2) / 5.0) * min(1.0, (ny - 1) / 5.0)
    size_f = min(1.0, math.log2(max(cells, 2)) / 7.0)
    score = 100.0 * (0.47 * vs + 0.18 * (qx * qy) ** 0.5 + 0.13 * size_f + 0.22 * hdr) * (1 - 0.03 * trim)
    m = MapDef(name="", address=sc.off(vi), cols=nx, rows=ny, dtype=vdt, endian=sc.en, order=order,
               source="finder")
    m.x_axis = AxisDef(name="X", address=sc.off(xi), count=nx, dtype=sc.dt, endian=sc.en)
    if yi is not None:
        m.y_axis = AxisDef(name="Y", address=sc.off(yi), count=ny, dtype=sc.dt, endian=sc.en)
    if layout.startswith("header"):
        m.description = "Bosch-style header (axis sizes before the axes)"
    return Candidate(m, round(score, 1), layout, {"smooth": round(vs, 3), "axis": round(qx * qy, 3)})


# ====================================================================== axis-less blocks
AXISLESS_WIDTHS = (6, 8, 10, 12, 16, 20, 24, 32)


def find_axisless(data: bytes, time_budget: float = 10.0, min_rows: int = 6) -> list[Candidate]:
    """Blocks whose consecutive rows (at a fixed width) are nearly equal while the values change along the row:
    calibration tables without stored axes. Lower scores than tables with axes."""
    t0 = time.time()
    out = []
    for dt, en in (("u8", "le"), ("u16", "le"), ("u16", "be")):
        size = dtype_size(dt)
        n = len(data) // size
        if n < 64:
            continue
        a = np.frombuffer(data, dtype=np_dtype(dt, en), count=n).astype(np.float64)
        lo, hi = _rng(dt)
        hd = np.abs(np.diff(a))
        for w in AXISLESS_WIDTHS:
            if time.time() - t0 > time_budget:
                return out
            if n < w * min_rows:
                continue
            vd = np.abs(a[w:] - a[:-w])
            # per position: vertical change small, value not fill, horizontal change exists nearby
            scale = np.maximum(np.abs(a[w:]), 8.0 if size == 1 else 64.0)
            good = (vd <= 0.12 * scale) & (a[w:] != hi) & (a[w:] != lo) & (hd[w - 1:] <= 0.35 * scale)
            # need w*min_rows consecutive good cells
            pad = np.concatenate(([False], good, [False])).astype(np.int8)
            d = np.diff(pad)
            starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
            lens = ends - starts
            for st, ln in zip(starts[lens >= w * (min_rows - 1)].tolist(), lens[lens >= w * (min_rows - 1)].tolist()):
                first = st                        # element index in a (block starts one row earlier)
                rows = min(ln // w + 1, MAX_AXIS)
                if rows < min_rows:
                    continue
                z = a[first:first + rows * w].reshape(rows, w)
                if np.ptp(z) == 0:
                    continue
                vs = smoothness(z, lo, hi)
                if vs < 0.55 or len(np.unique(z)) < 4:
                    continue
                score = 100.0 * (0.47 * vs + 0.18 * 0.35 + 0.13 * min(1.0, math.log2(z.size) / 7.0)) * 0.85
                m = MapDef(name="", address=first * size, cols=w, rows=rows, dtype=dt, endian=en, source="finder",
                           description="no axes found (the row width is a guess)")
                out.append(Candidate(m, round(score, 1), "axisless", {"smooth": round(vs, 3), "width": w}))
    return out


# ====================================================================== 2D view
def value_profile(data, dt: str = "u8", endian: str = "le", start: int = 0, end: int | None = None,
                  width: int = 2000) -> tuple[np.ndarray, np.ndarray, int]:
    """Min / max of the cells in each of *width* buckets between *start* and *end* (the "2D view" graph).
    Returns (mins, maxs, cells_per_bucket)."""
    data = bytes(data)
    end = len(data) if end is None else min(end, len(data))
    size = dtype_size(dt)
    n = max(0, (end - start) // size)
    if n == 0:
        return np.zeros(0), np.zeros(0), 1
    a = np.frombuffer(data, dtype=np_dtype(dt, endian), count=n, offset=start).astype(np.float64)
    if dt.startswith("f"):
        a = np.nan_to_num(a, nan=0.0, posinf=0.0, neginf=0.0)
    per = max(1, math.ceil(n / max(1, width)))
    pad = (-n) % per
    if pad:
        a = np.concatenate((a, np.full(pad, a[-1])))
    a = a.reshape(-1, per)
    return a.min(axis=1), a.max(axis=1), per
