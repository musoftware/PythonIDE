"""OBD-II scan-tool client (SAE J1979 modes 01-0A) over any transport (docs/CARDIAG.md "OBD-II scan tool").

``transport.request(data, timeout) -> [(ecu, payload)]`` - see transport.py (Demo car, the link slice's
adapters).  Every answer of every control unit is kept per ECU ("7E8", "7E9" ...).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from . import dtc as D
from . import mode06 as M6
from . import mode09 as M9
from . import pids as P
from .readiness import MonitorStatus, decode_status


class ObdError(Exception):
    pass


@dataclass
class Reading:
    pid: int
    ecu: str
    data: bytes
    t: float = 0.0

    @property
    def values(self) -> list:
        return P.decode(self.pid, self.data)

    @property
    def value(self):
        return P.main_value(self.pid, self.data)


@dataclass
class DtcEntry:
    code: str
    ecu: str
    kinds: set = field(default_factory=set)       # {"stored", "pending", "permanent"}

    @property
    def status(self) -> str:
        order = [k for k in ("stored", "pending", "permanent") if k in self.kinds]
        return ", ".join(D.KIND_TITLES[k] for k in order)


@dataclass
class FreezeFrame:
    ecu: str
    frame: int
    dtc: str
    data: dict = field(default_factory=dict)      # pid -> bytes

    def readings(self) -> list[Reading]:
        return [Reading(p, self.ecu, d) for p, d in sorted(self.data.items())]


@dataclass
class VehicleInfo:
    vin: str = ""
    calids: dict = field(default_factory=dict)    # ecu -> [str]
    cvns: dict = field(default_factory=dict)      # ecu -> [hex]
    names: dict = field(default_factory=dict)     # ecu -> str
    ipt: dict = field(default_factory=dict)       # ecu -> [(name, value)]
    supported: dict = field(default_factory=dict)  # ecu -> set of info types


ECU_NAMES = {"7E8": "Engine (ECM)", "7E9": "Transmission (TCM)", "7EA": "ECU #3", "7EB": "ECU #4",
             "7EC": "ECU #5", "7ED": "ECU #6", "7EE": "ECU #7", "7EF": "ECU #8",
             "10": "Engine (ECM)", "18": "Transmission (TCM)", "18DAF110": "Engine (ECM)",
             "18DAF118": "Transmission (TCM)"}


def ecu_title(ecu: str, names: dict | None = None) -> str:
    if names and names.get(ecu):
        return f"{names[ecu]} ({ecu})"
    t = ECU_NAMES.get(ecu.upper())
    return f"{t} ({ecu})" if t else ecu


class ObdClient:
    def __init__(self, transport, timeout: float = 2.0):
        self.transport = transport
        self.timeout = timeout
        self.lock = threading.RLock()
        self.listeners: list = []                # f(direction "tx"/"rx"/"err", ecu, bytes)
        self._supported: dict[str, set[int]] | None = None
        self.negatives: list[tuple[str, bytes]] = []

    @property
    def is_can(self) -> bool:
        return bool(getattr(self.transport, "is_can", True))

    def _emit(self, direction, ecu, data):
        for f in list(self.listeners):
            try:
                f(direction, ecu, data)
            except Exception:  # noqa: BLE001 - a listener must never break the scan
                pass

    # ------------------------------------------------------------------ raw
    def request(self, data: bytes) -> list[tuple[str, bytes]]:
        with self.lock:
            self._emit("tx", "", bytes(data))
            try:
                ans = self.transport.request(bytes(data), self.timeout) or []
            except Exception as e:  # noqa: BLE001
                self._emit("err", "", str(e).encode("utf-8", "replace"))
                raise ObdError(str(e)) from e
            for ecu, payload in ans:
                self._emit("rx", ecu, bytes(payload))
            return [(str(e), bytes(p)) for e, p in ans]

    def query(self, data: bytes) -> dict[str, bytes]:
        """Positive answers only (response SID = request SID + 0x40), per ECU; several answers of one ECU
        (multi-frame K-line) are joined."""
        want = (data[0] + 0x40) & 0xFF
        out: dict[str, bytes] = {}
        for ecu, p in self.request(data):
            if not p:
                continue
            if p[0] == 0x7F:
                if len(p) >= 3 and p[2] != 0x78:
                    self.negatives.append((ecu, p))
                continue
            if p[0] != want:
                continue
            out[ecu] = out[ecu] + p[1:] if ecu in out else p
        return out

    # ------------------------------------------------------------------ mode 01
    def supported_pids(self, refresh: bool = False) -> dict[str, set[int]]:
        if self._supported is not None and not refresh:
            return self._supported
        sup: dict[str, set[int]] = {}
        base = 0
        asked: set[str] | None = None
        while base <= 0xC0:
            ans = self.query(bytes([0x01, base]))
            got = False
            for ecu, p in ans.items():
                if asked is not None and ecu not in asked:
                    continue
                if len(p) >= 6 and p[1] == base:
                    s = P.supported_from_bitmap(base, p[2:6])
                    sup.setdefault(ecu, set()).update(s)
                    got = got or (base + 0x20) in s
            if asked is None:
                asked = set(sup)
            if not got:
                break
            base += 0x20
        self._supported = sup
        return sup

    def all_supported(self) -> list[int]:
        s: set[int] = set()
        for v in self.supported_pids().values():
            s |= v
        return sorted(p for p in s if p not in P.BITMAP_PIDS)

    def read_pids(self, pids, ecu: str | None = None) -> list[Reading]:
        """Read several mode 01 PIDs (6 per request on CAN, one by one otherwise)."""
        pids = [p for p in pids if p not in P.BITMAP_PIDS]
        step = 6 if self.is_can else 1
        out: list[Reading] = []
        now = time.time()
        for i in range(0, len(pids), step):
            chunk = pids[i:i + step]
            for e, p in self.query(bytes([0x01, *chunk])).items():
                if ecu is not None and e != ecu:
                    continue
                for pid, data in P.split_multi(p[1:]):
                    if pid in chunk:
                        out.append(Reading(pid, e, data, now))
        return out

    def read_pid(self, pid: int) -> dict[str, Reading]:
        return {r.ecu: r for r in self.read_pids([pid])}

    # ------------------------------------------------------------------ DTCs (03 / 07 / 0A)
    def read_dtcs(self, kind: str = "stored") -> dict[str, list[str]]:
        mode = D.KINDS[kind]
        return {ecu: D.parse(p, self.is_can) for ecu, p in self.query(bytes([mode])).items()}

    def read_all_dtcs(self) -> list[DtcEntry]:
        entries: dict[tuple[str, str], DtcEntry] = {}
        for kind in ("stored", "pending", "permanent"):
            try:
                ans = self.read_dtcs(kind)
            except ObdError:
                if kind == "stored":
                    raise
                continue
            for ecu, codes in ans.items():
                for c in codes:
                    entries.setdefault((ecu, c), DtcEntry(c, ecu)).kinds.add(kind)
        rank = {"stored": 0, "pending": 1, "permanent": 2}
        return sorted(entries.values(), key=lambda e: (min(rank[k] for k in e.kinds), e.ecu, e.code))

    def clear_dtcs(self) -> dict[str, bool]:
        """Mode 04: clears stored + pending codes, freeze frames, mode 06 results; resets readiness monitors."""
        ans = self.request(b"\x04")
        out = {}
        for ecu, p in ans:
            if p[:1] == b"\x44":
                out[ecu] = True
            elif p[:1] == b"\x7f":
                out[ecu] = False
                self.negatives.append((ecu, p))
        self._supported = None
        return out

    # ------------------------------------------------------------------ freeze frame (02)
    def freeze_frames(self, frame: int = 0) -> dict[str, FreezeFrame]:
        out: dict[str, FreezeFrame] = {}
        dtcs = self.query(bytes([0x02, 0x02, frame]))
        for ecu, p in dtcs.items():
            if len(p) >= 5:
                out[ecu] = FreezeFrame(ecu, frame, P.dtc_text(p[3], p[4]) if (p[3] or p[4]) else "")
        if not out:
            return out
        # supported freeze-frame PIDs (02 00 / 20 / 40 ...), else the live-data set
        sup: dict[str, set[int]] = {}
        base = 0
        while base <= 0xC0:
            ans = self.query(bytes([0x02, base, frame]))
            more = False
            for ecu, p in ans.items():
                if len(p) >= 7:
                    s = P.supported_from_bitmap(base, p[3:7])
                    sup.setdefault(ecu, set()).update(s)
                    more = more or (base + 0x20) in s
            if not more:
                break
            base += 0x20
        live = self.supported_pids()
        for ecu, ff in out.items():
            want = sorted(p for p in (sup.get(ecu) or live.get(ecu, set())) if p not in P.BITMAP_PIDS and p != 0x02)
            step = 3 if self.is_can else 1               # 3 pairs (PID, frame) per request
            for i in range(0, len(want), step):
                req = bytes([0x02]) + b"".join(bytes([p, frame]) for p in want[i:i + step])
                p = self.query(req).get(ecu)
                if not p:
                    continue
                j, body = 0, p[1:]
                while j + 1 < len(body):
                    pid = body[j]
                    n = P.get(pid).length or (len(body) - j - 2)
                    ff.data[pid] = bytes(body[j + 2:j + 2 + n])
                    j += 2 + n
        return out

    # ------------------------------------------------------------------ readiness (01 01 / 01 41)
    def readiness(self, this_cycle: bool = False) -> dict[str, MonitorStatus]:
        pid = 0x41 if this_cycle else 0x01
        out = {}
        for r in self.read_pids([pid]):
            out[r.ecu] = decode_status(r.data)
        return out

    # ------------------------------------------------------------------ mode 06
    def mode06(self) -> dict[str, list[M6.TestResult]]:
        sup: dict[str, set[int]] = {}
        base = 0
        while base < 0x100:
            ans = self.query(bytes([0x06, base]))
            more = False
            for ecu, p in ans.items():
                s = M6.supported_from_bitmap(base, p)
                sup.setdefault(ecu, set()).update(s)
                more = more or (base + 0x20) in s
            if not more:
                break
            base += 0x20
        out: dict[str, list] = {e: [] for e in sup}
        mids = sorted(set().union(*sup.values()) - set(M6.BITMAP_MIDS)) if sup else []
        for mid in mids:
            for ecu, p in self.query(bytes([0x06, mid])).items():
                if mid in sup.get(ecu, ()):
                    out.setdefault(ecu, []).extend(M6.parse(p))
        return out

    # ------------------------------------------------------------------ mode 09
    def vehicle_info(self) -> VehicleInfo:
        vi = VehicleInfo()
        for ecu, p in self.query(b"\x09\x00").items():
            if len(p) >= 6:
                vi.supported[ecu] = P.supported_from_bitmap(0, p[2:6])
        if not vi.supported:
            return vi

        def has(ecu, info):
            return info in vi.supported.get(ecu, ())
        for ecu, p in self.query(b"\x09\x02").items():
            if has(ecu, 2) and not vi.vin:
                vi.vin = M9.vin(p)
        for ecu, p in self.query(b"\x09\x04").items():
            vi.calids[ecu] = M9.calids(p)
        for ecu, p in self.query(b"\x09\x06").items():
            vi.cvns[ecu] = M9.cvns(p)
        for ecu, p in self.query(b"\x09\x0a").items():
            vi.names[ecu] = M9.ecu_name(p)
        for info, diesel in ((0x08, False), (0x0B, True)):
            if any(has(e, info) for e in vi.supported):
                for ecu, p in self.query(bytes([0x09, info])).items():
                    vi.ipt[ecu] = M9.ipt(p, diesel)
        return vi
