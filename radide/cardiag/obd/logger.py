"""Live-data logging to CSV and playback.

CSV layout (one row per sample time, one column per PID/ECU): ``time_s,<ECU> <PID hex> <short name> [unit],...``
e.g. ``time_s,7E8 0C RPM [rpm],7E8 0D Speed [km/h]``.  The header keeps the PID number, so a log made here
plays back with the right names, units and gauge ranges; other tools' CSV files play back too (any numeric
column becomes a channel).
"""
from __future__ import annotations

import csv
import re
import time
from dataclasses import dataclass, field

from . import pids as P

_COL = re.compile(r"^(?P<ecu>[0-9A-Fa-f]{2,8})\s+(?P<pid>[0-9A-Fa-f]{2})\b(?P<rest>.*)$")


def column_name(ecu: str, pid: int) -> str:
    p = P.get(pid)
    unit = f" [{p.unit}]" if p.unit else ""
    return f"{ecu} {pid:02X} {p.short}{unit}"


def parse_column(name: str) -> tuple[str, int | None, str]:
    """"7E8 0C RPM [rpm]" -> ("7E8", 0x0C, "RPM [rpm]"); other names -> ("", None, name)."""
    m = _COL.match(name.strip())
    if not m:
        return "", None, name.strip()
    return m.group("ecu").upper(), int(m.group("pid"), 16), m.group("rest").strip()


class CsvLogger:
    def __init__(self, path: str, channels: list[tuple[str, int]]):
        self.path = str(path)
        self.channels = list(channels)
        self.t0 = time.monotonic()
        self.rows = 0
        self.f = open(self.path, "w", newline="", encoding="utf-8")
        self.w = csv.writer(self.f)
        self.w.writerow(["time_s"] + [column_name(e, p) for e, p in self.channels])

    def write(self, values: dict, t: float | None = None) -> None:
        """values: (ecu, pid) -> float | None."""
        t = (time.monotonic() - self.t0) if t is None else t
        row = [f"{t:.3f}"]
        for key in self.channels:
            v = values.get(key)
            row.append("" if v is None else (f"{v:.4f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)))
        self.w.writerow(row)
        self.rows += 1
        if self.rows % 20 == 0:
            self.f.flush()

    def close(self) -> None:
        try:
            self.f.close()
        except OSError:
            pass


@dataclass
class Recording:
    path: str = ""
    columns: list = field(default_factory=list)     # [(ecu, pid|None, label)]
    times: list = field(default_factory=list)       # float seconds
    data: list = field(default_factory=list)        # per column: list[float | None]

    def __len__(self) -> int:
        return len(self.times)

    def sample(self, i: int) -> dict:
        return {k: self.data[c][i] for c, k in enumerate(self.keys())}

    def keys(self) -> list:
        return [(e, p if p is not None else lab) for e, p, lab in self.columns]

    def index_at(self, t: float) -> int:
        import bisect
        return max(0, min(len(self.times) - 1, bisect.bisect_right(self.times, t) - 1))

    @property
    def duration(self) -> float:
        return (self.times[-1] - self.times[0]) if self.times else 0.0


def _num(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load(path: str) -> Recording:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        raise ValueError("empty CSV file")
    head = rows[0]
    tcol = 0
    for i, h in enumerate(head):
        if h.strip().lower() in ("time_s", "time", "t", "seconds", "time (s)"):
            tcol = i
            break
    rec = Recording(path=str(path))
    cols = [i for i in range(len(head)) if i != tcol]
    rec.columns = [parse_column(head[i]) for i in cols]
    rec.data = [[] for _ in cols]
    for r in rows[1:]:
        if not r or len(r) <= tcol:
            continue
        t = _num(r[tcol])
        if t is None:
            continue
        rec.times.append(t)
        for c, i in enumerate(cols):
            rec.data[c].append(_num(r[i]) if i < len(r) else None)
    keep = [c for c in range(len(cols)) if any(v is not None for v in rec.data[c])]
    rec.columns = [rec.columns[c] for c in keep]
    rec.data = [rec.data[c] for c in keep]
    return rec
