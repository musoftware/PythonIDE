"""Editing operations on a map's physical values (pure numpy), the map-level write-back and ori/mod diffs.

Every operation takes the (rows, cols) physical array and a boolean *mask* of the selected cells and returns a
new array; :func:`apply` writes the result into a byte buffer (one undoable edit when the buffer is a
radide/retro/rom/buffer.HexBuffer).
"""
from __future__ import annotations

import numpy as np

from .model import MapDef, MapPack, parse_tsv


def full_mask(z) -> np.ndarray:
    return np.ones(np.shape(z), dtype=bool)


def rect_mask(z, r0: int, c0: int, r1: int, c1: int) -> np.ndarray:
    m = np.zeros(np.shape(z), dtype=bool)
    m[min(r0, r1):max(r0, r1) + 1, min(c0, c1):max(c0, c1) + 1] = True
    return m


def _m(z, mask):
    z = np.array(z, dtype=np.float64)
    return z, (full_mask(z) if mask is None else np.asarray(mask, dtype=bool))


def set_value(z, mask, v: float) -> np.ndarray:
    z, mask = _m(z, mask)
    z[mask] = v
    return z


def add(z, mask, v: float) -> np.ndarray:
    z, mask = _m(z, mask)
    z[mask] += v
    return z


def add_percent(z, mask, pct: float) -> np.ndarray:
    z, mask = _m(z, mask)
    z[mask] *= 1.0 + pct / 100.0
    return z


def multiply(z, mask, f: float) -> np.ndarray:
    z, mask = _m(z, mask)
    z[mask] *= f
    return z


def _bbox(mask):
    rs, cs = np.nonzero(mask)
    if not len(rs):
        return None
    return rs.min(), cs.min(), rs.max(), cs.max()


def interpolate(z, mask, direction: str = "auto") -> np.ndarray:
    """Linear interpolation inside the selection's bounding box from its edges: "h" (each row between its first
    and last selected cell), "v" (each column), "auto"/"2d" (bilinear from the four corners; a single row / column
    interpolates along it)."""
    z, mask = _m(z, mask)
    bb = _bbox(mask)
    if bb is None:
        return z
    r0, c0, r1, c1 = bb
    if direction == "auto":
        direction = "h" if r0 == r1 else ("v" if c0 == c1 else "2d")
    out = z.copy()
    if direction == "h" and c1 > c0:
        for r in range(r0, r1 + 1):
            out[r, c0:c1 + 1] = np.linspace(z[r, c0], z[r, c1], c1 - c0 + 1)
    elif direction == "v" and r1 > r0:
        for c in range(c0, c1 + 1):
            out[r0:r1 + 1, c] = np.linspace(z[r0, c], z[r1, c], r1 - r0 + 1)
    elif direction == "2d" and r1 > r0 and c1 > c0:
        ty = np.linspace(0, 1, r1 - r0 + 1)[:, None]
        tx = np.linspace(0, 1, c1 - c0 + 1)[None, :]
        a, b, c, d = z[r0, c0], z[r0, c1], z[r1, c0], z[r1, c1]
        out[r0:r1 + 1, c0:c1 + 1] = (a * (1 - tx) * (1 - ty) + b * tx * (1 - ty) + c * (1 - tx) * ty + d * tx * ty)
    res = z.copy()
    res[mask] = out[mask]
    return res


def smooth(z, mask, passes: int = 1) -> np.ndarray:
    """3x3 neighbourhood average (edges use the neighbours that exist) applied to the selected cells."""
    z, mask = _m(z, mask)
    cur = z.copy()
    for _ in range(max(1, passes)):
        p = np.pad(cur, 1, mode="edge") if cur.size > 1 else cur
        if cur.size <= 1:
            break
        acc = np.zeros_like(cur)
        h, w = cur.shape
        rows, cols = (range(-1, 2) if h > 1 else [0]), (range(-1, 2) if w > 1 else [0])
        n = 0
        for dr in rows:
            for dc in cols:
                acc += p[1 + dr:1 + dr + h, 1 + dc:1 + dc + w]
                n += 1
        nxt = cur.copy()
        nxt[mask] = (acc / n)[mask]
        cur = nxt
    return cur


def paste(z, text: str, r0: int = 0, c0: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Excel / TSV grid pasted with its top-left cell at (r0, c0); blank cells keep their value. Returns the new
    array and the mask of changed cells."""
    z = np.array(z, dtype=np.float64)
    mask = np.zeros(z.shape, dtype=bool)
    for i, row in enumerate(parse_tsv(text)):
        for j, v in enumerate(row):
            r, c = r0 + i, c0 + j
            if v is None or r >= z.shape[0] or c >= z.shape[1]:
                continue
            z[r, c] = v
            mask[r, c] = True
    return z, mask


def copy_text(z, mask=None, digits: int | None = None) -> str:
    from .model import fmt_value
    z = np.asarray(z)
    bb = _bbox(full_mask(z) if mask is None else mask)
    if bb is None:
        return ""
    r0, c0, r1, c1 = bb
    return "\n".join("\t".join(fmt_value(v, digits) for v in z[r, c0:c1 + 1]) for r in range(r0, r1 + 1)) + "\n"


# ====================================================================== write-back
def apply(buf, m: MapDef, z_phys) -> bool:
    """Write physical values into *buf* (a HexBuffer with ``replace``/``data``, or a bytearray). True when bytes
    changed."""
    new = m.encode_phys(z_phys)
    data = buf.data if hasattr(buf, "data") else buf
    old = bytes(data[m.address:m.address + len(new)])
    if old == new:
        return False
    if hasattr(buf, "replace"):
        buf.replace(m.address, new)
    else:
        buf[m.address:m.address + len(new)] = new
    return True


def apply_axis(buf, axis, phys_values) -> bool:
    from .model import encode_array
    if not axis.stored:
        return False
    raw = (np.asarray(phys_values, dtype=np.float64) - axis.offset) / (axis.factor or 1.0)
    new = encode_array(raw, axis.dtype, axis.endian)
    data = buf.data if hasattr(buf, "data") else buf
    a = int(axis.address)
    if bytes(data[a:a + len(new)]) == new:
        return False
    if hasattr(buf, "replace"):
        buf.replace(a, new)
    else:
        buf[a:a + len(new)] = new
    return True


# ====================================================================== diffs
def cell_diff(m: MapDef, ori, mod) -> np.ndarray:
    """(rows, cols) boolean array: cells whose raw value differs between *ori* and *mod*."""
    return m.raw(ori) != m.raw(mod)


def map_changed(m: MapDef, ori, mod) -> bool:
    return any(bytes(ori[s:e]) != bytes(mod[s:e]) for s, e in m.ranges())


def changed_maps(pack: MapPack | list, ori, mod) -> list[dict]:
    """Maps whose values or axes differ: [{map, cells, total, axes, min_pct, max_pct}]."""
    out = []
    for m in (pack.maps if isinstance(pack, MapPack) else pack):
        if not map_changed(m, ori, mod):
            continue
        a, b = m.phys(ori), m.phys(mod)
        d = a != b
        with np.errstate(divide="ignore", invalid="ignore"):
            pct = np.where(a != 0, (b - a) / np.abs(a) * 100.0, 0.0)
        axes = any(ax.stored and bytes(ori[int(ax.address):int(ax.address) + ax.nbytes()]) !=
                   bytes(mod[int(ax.address):int(ax.address) + ax.nbytes()]) for ax in (m.x_axis, m.y_axis))
        out.append({"map": m, "cells": int(d.sum()), "total": int(d.size), "axes": axes,
                    "min_pct": float(pct[d].min()) if d.any() else 0.0,
                    "max_pct": float(pct[d].max()) if d.any() else 0.0})
    return out


def diff_ranges(a, b, limit: int = 200_000) -> list[tuple[int, int]]:
    """Byte ranges [start, end) that differ (numpy; the tail of the longer file is one range)."""
    n = min(len(a), len(b))
    x = np.frombuffer(bytes(a[:n]), dtype=np.uint8)
    y = np.frombuffer(bytes(b[:n]), dtype=np.uint8)
    ne = np.concatenate(([False], x != y, [False]))
    edges = np.flatnonzero(ne[1:] != ne[:-1])
    out = [(int(edges[i]), int(edges[i + 1])) for i in range(0, min(len(edges), 2 * limit), 2)]
    if len(a) != len(b):
        out.append((n, max(len(a), len(b))))
    return out


def unmapped_changes(pack, ori, mod) -> list[tuple[int, int]]:
    """Changed byte ranges not covered by any map of *pack*."""
    maps = pack.maps if isinstance(pack, MapPack) else list(pack)
    cov = sorted(r for m in maps for r in m.ranges())
    out = []
    for s, e in diff_ranges(ori, mod):
        cur = s
        for cs, ce in cov:
            if ce <= cur or cs >= e:
                continue
            if cs > cur:
                out.append((cur, cs))
            cur = max(cur, ce)
            if cur >= e:
                break
        if cur < e:
            out.append((cur, e))
    return out


# ====================================================================== compare / copy between binaries
def locate_in(m: MapDef, src, dst) -> int | None:
    """Where the map *m* (defined for *src*) is in *dst*: the same address when the axes / layout match there,
    else the nearest place whose stored axis bytes equal the source's. Returns the address delta or None."""
    sig = []
    for ax in (m.x_axis, m.y_axis):
        if ax.stored:
            sig.append((int(ax.address), bytes(src[int(ax.address):int(ax.address) + ax.nbytes()])))
    if not sig:
        return 0 if m.end <= len(dst) else None
    if all(bytes(dst[a:a + len(b)]) == b for a, b in sig):
        return 0
    a0, b0 = sig[0]
    if len(b0) < 4:
        return None
    best = None
    start = 0
    raw = bytes(dst)
    while True:
        i = raw.find(b0, start)
        if i < 0:
            break
        delta = i - a0
        if all(bytes(dst[a + delta:a + delta + len(b)]) == b for a, b in sig[1:]) and m.end + delta <= len(dst):
            if best is None or abs(delta) < abs(best):
                best = delta
        start = i + 1
    return best


def copy_map(m: MapDef, src, dst_buf, delta: int | None = None, axes: bool = True) -> bool:
    """Copy the values (and stored axes) of *m* from *src* into *dst_buf* (HexBuffer or bytearray)."""
    if delta is None:
        delta = locate_in(m, src, dst_buf.data if hasattr(dst_buf, "data") else dst_buf)
        if delta is None:
            return False
    changed = False
    rngs = m.ranges() if axes else [(m.address, m.end)]
    for s, e in rngs:
        new = bytes(src[s:e])
        data = dst_buf.data if hasattr(dst_buf, "data") else dst_buf
        if bytes(data[s + delta:e + delta]) == new:
            continue
        if hasattr(dst_buf, "replace"):
            dst_buf.replace(s + delta, new)
        else:
            dst_buf[s + delta:e + delta] = new
        changed = True
    return changed
