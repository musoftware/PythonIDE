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
def _tv_ratio(z: np.ndarray, axis: int) -> float:
    """mean over lines of total-variation / span along *axis* (1 = monotonic lines)."""
    if z.shape[axis] < 2:
        return 1.0
    d = np.abs(np.diff(z, axis=axis)).sum(axis=axis)
    span = np.ptp(z, axis=axis)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(span > 0, d / np.where(span > 0, span, 1), 1.0)
    return float(r.mean())


def smoothness(z: np.ndarray, raw_lo: float | None = None, raw_hi: float | None = None) -> float:
    """0..1: how much *z* (rows, cols) looks like a calibration surface / curve."""
    z = np.asarray(z, dtype=np.float64)
    if z.size < 2 or not np.all(np.isfinite(z)):
        return 0.0
    rng = float(np.ptp(z))
    if rng == 0:
        v = float(z.flat[0])
        if v == 0 or (raw_lo is not None and v in (raw_lo, raw_hi)):
            return 0.03                       # fill (00 / FF ...)
        return 0.3
    rows, cols = z.shape
    ratios = []
    if cols > 1:
        ratios.append(_tv_ratio(z, 1))
    if rows > 1:
        ratios.append(_tv_ratio(z, 0))
    f1 = 1.0 / (sum(ratios) / len(ratios))
    steps = []
    if cols > 1:
        steps.append(float(np.abs(np.diff(z, axis=1)).mean()))
    if rows > 1:
        steps.append(float(np.abs(np.diff(z, axis=0)).mean()))
    m2 = (sum(steps) / len(steps)) / rng
    f2 = min(1.0, max(0.0, 1.0 - 2.5 * m2))
    s = 0.6 * f1 + 0.4 * f2
    # few distinct values in a big table: flags / bit fields rather than a calibration
    if z.size >= 16 and len(np.unique(z)) <= 2:
        s *= 0.5
    # values glued to the type's extremes: pointers / fill
    if raw_hi is not None and np.mean((z == raw_hi) | (z == raw_lo)) > 0.5:
        s *= 0.4
    return s


def axis_quality(a: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float64)
    n = len(a)
    if n < 2:
        return 0.0
    steps = np.diff(a)
    if np.any(steps <= 0):
        return 0.0
    q = 0.6 + 0.4 * min(1.0, n / 12.0)
    if np.all(steps == 1):
        q *= 0.45                             # 0,1,2,3...: an index table
    ratio = steps.max() / max(steps.min(), 1e-12)
    if ratio > 60:
        q *= 0.6
    if abs(a[-1]) > 1e9:
        q *= 0.3
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
            s = smoothness(z, lo, hi)
            if best is None or s > best[0] + 1e-9:
                best = (s, vdt, order, z)
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
    keep = lens >= MIN_AXIS
    return starts[keep], lens[keep]


def _view(data: bytes, dt: str, endian: str, align: int):
    size = dtype_size(dt)
    n = (len(data) - align) // size
    if n <= 0:
        return None, None
    arr = np.frombuffer(data, dtype=np_dtype(dt, endian), count=n, offset=align).astype(np.float64)
    valid = None
    if dt.startswith("f"):
        a = np.abs(arr)
        valid = np.isfinite(arr) & (a < 1e7) & ((a > 1e-6) | (arr == 0))
    return arr, valid


def find_maps(data, *, min_score: float = 35.0, max_results: int = 2000, types=None, axisless: bool = True,
              time_budget: float = 60.0, progress=None) -> list[Candidate]:
    """Find potential maps in *data* (bytes). Sorted best first, non-overlapping."""
    data = bytes(data)
    t0 = time.time()
    cands: list[Candidate] = []
    scan = [t for t in SCAN_TYPES if types is None or t[0] in types]
    total = sum(len(a) for _d, _e, a in scan) + (1 if axisless else 0)
    step = 0
    for dt, en, aligns in scan:
        size = dtype_size(dt)
        for align in aligns:
            step += 1
            if progress is not None:
                progress(step, total)
            if time.time() - t0 > time_budget:
                break
            arr, valid = _view(data, dt, en, align)
            if arr is None:
                continue
            starts, lens = _runs(arr, valid)
            run_at = dict(zip(starts.tolist(), lens.tolist()))
            n = len(arr)
            for s, L in zip(starts.tolist(), lens.tolist()):
                if L > MAX_AXIS + 2:
                    continue
                cands.extend(_around_run(data, arr, valid, n, s, L, dt, en, align, size, run_at))
    if axisless and time.time() - t0 < time_budget:
        step += 1
        if progress is not None:
            progress(step, total)
        cands.extend(find_axisless(data, time_budget=max(1.0, time_budget - (time.time() - t0))))
    cands = [c for c in cands if c.score >= min_score]
    cands.sort(key=lambda c: (-c.score, c.address))
    picked: list[Candidate] = []
    taken: list[tuple[int, int]] = []
    import bisect
    for c in cands:
        s, e = c.span()
        i = bisect.bisect_left(taken, (s, s))
        clash = False
        for j in (i - 1, i):
            if 0 <= j < len(taken) and taken[j][0] < e and s < taken[j][1]:
                clash = True
                break
        if not clash:
            # wider check (a candidate may cover several taken spans)
            k = i
            while k < len(taken) and taken[k][0] < e:
                if s < taken[k][1]:
                    clash = True
                    break
                k += 1
        if clash:
            continue
        bisect.insort(taken, (s, e))
        picked.append(c)
        if len(picked) >= max_results:
            break
    for i, c in enumerate(picked, 1):
        m = c.mapdef
        if not m.name:
            m.name = f"Map_{m.address:06X}" if m.rows > 1 else f"Curve_{m.address:06X}"
    return picked


def _is_int(v) -> bool:
    return float(v).is_integer()


def _around_run(data, arr, valid, n, s, L, dt, en, align, size, run_at):
    out = []
    off = lambda i: align + i * size  # noqa: E731
    is_f = dt.startswith("f")
    # ---- Bosch-style headers (the run may also have swallowed the last header cell: try trims 0..2)
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
                c = _make(data, arr, dt, en, size, off(i), nx, 1, off(i + nx), None, "header-curve", 1.0)
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
                if yi + ny > n:
                    continue
                ya = arr[yi:yi + ny]
                if not np.all(np.diff(ya) > 0):
                    continue
                c = _make(data, arr, dt, en, size, off(i), nx, ny, off(yi + ny), off(yi), "header", 1.0)
                if c:
                    out.append(c)
                break
    # ---- headerless: [X][Y][values] or [axis][values]
    for t in (0, 1):
        i = s + t
        nx = L - t
        if nx < MIN_AXIS or nx > MAX_AXIS:
            continue
        yi = i + nx
        ny = run_at.get(yi)
        if ny and MIN_AXIS - 1 <= ny <= MAX_AXIS:
            c = _make(data, arr, dt, en, size, off(i), nx, ny, off(yi + ny), off(yi), "axes", 0.55)
            if c:
                out.append(c)
        elif nx >= (6 if size == 1 else 5) and t == 0:
            c = _make(data, arr, dt, en, size, off(i), nx, 1, off(yi), None, "curve", 0.0)
            if c:
                out.append(c)
    return out


def _make(data, arr, dt, en, size, x_off, nx, ny, v_off, y_off, layout, hdr):
    xa = np.frombuffer(data, dtype=np_dtype(dt, en), count=nx, offset=x_off).astype(np.float64)
    qx = axis_quality(xa)
    if qx <= 0:
        return None
    qy = 1.0
    if y_off is not None:
        ya = np.frombuffer(data, dtype=np_dtype(dt, en), count=ny, offset=y_off).astype(np.float64)
        qy = axis_quality(ya)
        if qy <= 0:
            return None
    bv = best_values(data, v_off, nx, ny, dt, en)
    if bv is None:
        return None
    vs, vdt, order, z = bv
    cells = nx * ny
    size_f = min(1.0, math.log2(max(cells, 2)) / 7.0)
    score = 100.0 * (0.47 * vs + 0.18 * (qx * qy) ** 0.5 + 0.13 * size_f + 0.22 * hdr)
    if layout == "curve":
        score *= 0.9
    m = MapDef(name="", address=v_off, cols=nx, rows=ny, dtype=vdt, endian=en, order=order, source="finder")
    m.x_axis = AxisDef(name="X", address=x_off, count=nx, dtype=dt, endian=en)
    if y_off is not None:
        m.y_axis = AxisDef(name="Y", address=y_off, count=ny, dtype=dt, endian=en)
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
