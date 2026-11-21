"""Entropy and region classification of a firmware image.

The Shannon entropy of fixed-size blocks (0..8 bits per byte) separates the typical areas of an ECU / embedded
image: empty flash (0xFF / 0x00 fill, entropy ~0), calibration data (tables of 8 / 16-bit values: low-to-medium
entropy, many repeated / smoothly changing values), machine code (medium-high, 5.5-7.2) and compressed or
encrypted data (~7.5-8). The classes are heuristics shown as hints, never as facts.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

CLASSES = {
    "empty": "Empty / fill",
    "text": "Text / strings",
    "calibration": "Calibration-like data (tables)",
    "data": "Data",
    "code": "Code-like",
    "random": "Compressed / encrypted-like",
}


def shannon(block: bytes) -> float:
    n = len(block)
    if not n:
        return 0.0
    counts = [0] * 256
    for b in block:
        counts[b] += 1
    h = 0.0
    for c in counts:
        if c:
            p = c / n
            h -= p * math.log2(p)
    return h


def _shannon_fast(block: bytes) -> float:
    n = len(block)
    if not n:
        return 0.0
    h = 0.0
    for c in (block.count(bytes([i])) for i in set(block)):
        p = c / n
        h -= p * math.log2(p)
    return h


def entropy_profile(data: bytes, block: int = 1024) -> list[float]:
    """Entropy of every *block*-byte block (last partial block included)."""
    try:
        import numpy as np
    except ImportError:            # pragma: no cover - numpy is a dependency of the IDE
        return [_shannon_fast(data[i:i + block]) for i in range(0, len(data), block)]
    if not data:
        return []
    arr = np.frombuffer(bytes(data), dtype=np.uint8)
    full = len(arr) // block
    out = []
    if full:
        a = arr[:full * block].reshape(full, block)
        # histogram per row
        idx = a.astype(np.int64) + (np.arange(full, dtype=np.int64)[:, None] * 256)
        hist = np.bincount(idx.ravel(), minlength=full * 256).reshape(full, 256).astype(np.float64)
        p = hist / block
        with np.errstate(divide="ignore", invalid="ignore"):
            logs = np.where(p > 0, np.log2(np.where(p > 0, p, 1)), 0.0)
        out = list((-(p * logs).sum(axis=1)).tolist())
    if len(arr) % block:
        out.append(shannon(bytes(arr[full * block:])))
    return out


@dataclass
class Region:
    start: int          # offset in the image
    end: int            # first offset after
    kind: str           # key of CLASSES
    entropy: float

    @property
    def size(self) -> int:
        return self.end - self.start

    @property
    def label(self) -> str:
        return CLASSES.get(self.kind, self.kind)


def _printable_ratio(block: bytes) -> float:
    if not block:
        return 0.0
    return sum(1 for b in block if 32 <= b < 127 or b in (9, 10, 13)) / len(block)


def _smoothness(block: bytes, width: int = 2, big_endian: bool = True) -> float:
    """Share of neighbouring 16-bit values that differ by a small amount (calibration axes / maps change slowly)."""
    n = len(block) // width
    if n < 8:
        return 0.0
    order = "big" if big_endian else "little"
    vals = [int.from_bytes(block[i * width:(i + 1) * width], order) for i in range(n)]
    small = sum(1 for a, b in zip(vals, vals[1:]) if abs(a - b) <= max(16, (abs(a) + abs(b)) // 16))
    return small / (n - 1)


def classify_block(block: bytes, h: float | None = None) -> str:
    if not block:
        return "empty"
    h = shannon(block) if h is None else h
    if len(set(block)) <= 2 and h < 0.5:
        return "empty"
    if h < 1.0 and max(block.count(bytes([block[0]])), block.count(b"\xff"), block.count(b"\x00")) > len(block) * 0.9:
        return "empty"
    if _printable_ratio(block) > 0.85:
        return "text"
    if h >= 7.55:
        return "random"
    # neighbouring 8 / 16-bit values that change slowly: axes, curves and maps (code stays below ~0.35)
    smooth = max(_smoothness(block, 2, True), _smoothness(block, 2, False), _smoothness(block, 1))
    if smooth > 0.55:
        return "calibration"
    if h >= 4.5 + 0.5 * min(1.0, len(block) / 4096):
        return "code"
    return "data"


def classify(data: bytes, block: int = 1024, profile: list[float] | None = None) -> list[Region]:
    """Consecutive blocks of the same class merged into regions."""
    prof = entropy_profile(data, block) if profile is None else profile
    regions: list[Region] = []
    for i, h in enumerate(prof):
        a = i * block
        b = min(a + block, len(data))
        k = classify_block(data[a:b], h)
        if regions and regions[-1].kind == k and regions[-1].end == a:
            r = regions[-1]
            n_old = (r.end - r.start) / block
            r.entropy = (r.entropy * n_old + h * ((b - a) / block)) / (n_old + (b - a) / block)
            r.end = b
        else:
            regions.append(Region(a, b, k, h))
    return regions


def summary(regions: list[Region]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in regions:
        out[r.kind] = out.get(r.kind, 0) + r.size
    return out
