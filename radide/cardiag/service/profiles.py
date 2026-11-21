"""Vehicle profiles and the audit log of service actions.

Each vehicle (by VIN) has a folder under ``definitions.home()/vehicles/<VIN>/``:

* ``profile.json`` - make / model / year / engine / notes / mileage noted by the user, the definition packs
  used with it, and a history of scans, repairs and service actions (newest last);
* ``audit.jsonl``  - one JSON line for **every** request / answer sent by a service function and every user
  confirmation (time, control unit, request, response, action, definition id, confirmation).

Other car-diagnostics parts (the scan tool) can add history entries with ``add_history(vin, kind, ...)``.
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .definitions import home

_LOCK = threading.Lock()
UNKNOWN_VIN = "UNKNOWN"


def clean_vin(vin: str) -> str:
    v = re.sub(r"[^A-Za-z0-9]", "", str(vin or "")).upper()
    return v or UNKNOWN_VIN


def vin_valid(vin: str) -> bool:
    """17 characters without I, O, Q (ISO 3779). The check digit is not enforced (only North America uses it)."""
    return bool(re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", str(vin or "").upper()))


def vehicles_dir() -> Path:
    p = home() / "vehicles"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


@dataclass
class VehicleProfile:
    vin: str
    make: str = ""
    model: str = ""
    year: str = ""
    engine: str = ""
    notes: str = ""
    mileage: str = ""              # as noted by the user (RAD IDE never reads / writes odometers)
    packs: list = field(default_factory=list)
    history: list = field(default_factory=list)
    created: str = ""

    @property
    def folder(self) -> Path:
        p = vehicles_dir() / clean_vin(self.vin)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def title(self) -> str:
        name = " ".join(x for x in (self.make, self.model, self.year) if x)
        return f"{name} ({self.vin})" if name else self.vin

    def save(self) -> None:
        with _LOCK:
            d = asdict(self)
            (self.folder / "profile.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    def add_history(self, kind: str, summary: str, summary_ar: str = "", **data) -> dict:
        """kind: scan | repair | service | clear_dtc | note."""
        entry = {"time": _now(), "kind": kind, "summary": summary, "summary_ar": summary_ar or summary}
        entry.update(data)
        self.history.append(entry)
        self.save()
        return entry

    # ------------------------------------------------------------------ audit log
    @property
    def audit_path(self) -> Path:
        return self.folder / "audit.jsonl"

    def audit(self, entry: dict) -> None:
        e = {"time": _now(), "vin": self.vin}
        e.update(entry)
        with _LOCK:
            with open(self.audit_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def audit_entries(self, limit: int = 0) -> list[dict]:
        try:
            lines = self.audit_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        if limit:
            lines = lines[-limit:]
        out = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
        return out

    def export_audit_csv(self, path) -> int:
        import csv
        rows = self.audit_entries()
        cols = ["time", "vin", "action", "id", "ecu", "tx", "rx", "request", "response", "error", "note",
                "confirmation", "repair_confirmed"]
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return len(rows)


def load(vin: str) -> VehicleProfile:
    v = clean_vin(vin)
    p = vehicles_dir() / v / "profile.json"
    if p.is_file():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            known = {k: d[k] for k in VehicleProfile.__dataclass_fields__ if k in d}
            known["vin"] = v
            return VehicleProfile(**known)
        except (OSError, ValueError, TypeError):
            pass
    prof = VehicleProfile(vin=v, created=_now())
    return prof


def get_or_create(vin: str, **info) -> VehicleProfile:
    prof = load(vin)
    changed = not (prof.folder / "profile.json").is_file()
    for k, val in info.items():
        if val and hasattr(prof, k) and getattr(prof, k) != val:
            setattr(prof, k, val)
            changed = True
    if changed:
        prof.save()
    return prof


def all_profiles() -> list[VehicleProfile]:
    out = []
    for d in sorted(vehicles_dir().iterdir()):
        if (d / "profile.json").is_file():
            out.append(load(d.name))
    return out


def add_history(vin: str, kind: str, summary: str, summary_ar: str = "", **data) -> dict:
    """For other car-diagnostics parts: add a scan / repair entry to the vehicle's history."""
    return get_or_create(vin).add_history(kind, summary, summary_ar, **data)
