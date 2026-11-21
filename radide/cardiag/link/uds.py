"""UDS (ISO 14229-1) client for one control unit over any DiagLink.

Services: 0x10 sessions, 0x3E tester present (with an optional keep-alive thread), 0x11 reset, 0x14 clear
diagnostic information (all, a group or one DTC), 0x19 read DTC information (by status mask, snapshot /
freeze-frame records, extended data, supported DTCs, permanent DTCs), 0x22 / 0x2E data identifiers, 0x31
routine control (start / stop / results), 0x2F input-output control (actuator tests) and 0x27 security access
- **only** through a seed/key plug-in the user supplies (``compute_key(seed, level, ecu)``, the same plug-ins
as radide/cardiag/service/security.py). RAD IDE has no built-in seed/key algorithms and never guesses keys.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from . import nrc as nrcs
from .base import DiagLink, LinkError, final

# 0x10 sessions
DEFAULT, PROGRAMMING, EXTENDED, SAFETY = 0x01, 0x02, 0x03, 0x04
# 0x11 resets
HARD_RESET, KEY_OFF_ON_RESET, SOFT_RESET = 0x01, 0x02, 0x03
# 0x31 routine control
START, STOP, RESULTS = 0x01, 0x02, 0x03
# 0x2F IO control parameters
RETURN_CONTROL, RESET_TO_DEFAULT, FREEZE_CURRENT, SHORT_TERM_ADJUST = 0x00, 0x01, 0x02, 0x03
# 0x14 groups
ALL_DTCS = 0xFFFFFF
EMISSIONS_GROUP = 0xFFFF33
# 0x19 sub-functions
REPORT_NUMBER_BY_MASK, REPORT_BY_MASK, REPORT_SNAPSHOT_IDS = 0x01, 0x02, 0x03
REPORT_SNAPSHOT_BY_DTC, REPORT_EXT_DATA_BY_DTC, REPORT_SUPPORTED, REPORT_PERMANENT = 0x04, 0x06, 0x0A, 0x15

# DTC status bits (ISO 14229-1 D.2)
STATUS_BITS = [
    ("testFailed", "Failing now", "عطل حالي"),
    ("testFailedThisOperationCycle", "Failed this drive cycle", "فشل في دورة القيادة هذه"),
    ("pendingDTC", "Pending", "معلّق"),
    ("confirmedDTC", "Confirmed (stored)", "مؤكَّد (مخزَّن)"),
    ("testNotCompletedSinceLastClear", "Test not completed since clear", "لم يكتمل الاختبار منذ المسح"),
    ("testFailedSinceLastClear", "Failed since last clear", "فشل منذ آخر مسح"),
    ("testNotCompletedThisOperationCycle", "Test not completed this cycle", "لم يكتمل الاختبار في هذه الدورة"),
    ("warningIndicatorRequested", "Warning light requested", "طلب تشغيل لمبة التحذير"),
]

# common identification DIDs (ISO 14229-1 C.1)
IDENT_DIDS = {
    0xF187: ("Spare part number", "رقم قطعة الغيار"),
    0xF188: ("ECU software number", "رقم برنامج الوحدة"),
    0xF189: ("ECU software version", "إصدار برنامج الوحدة"),
    0xF18A: ("System supplier", "المورّد"),
    0xF18B: ("ECU manufacturing date", "تاريخ تصنيع الوحدة"),
    0xF18C: ("ECU serial number", "الرقم التسلسلي للوحدة"),
    0xF190: ("VIN", "رقم الشاسيه (VIN)"),
    0xF191: ("ECU hardware number", "رقم عتاد الوحدة"),
    0xF192: ("Supplier hardware number", "رقم العتاد لدى المورّد"),
    0xF193: ("Supplier hardware version", "إصدار العتاد لدى المورّد"),
    0xF194: ("Supplier software number", "رقم البرنامج لدى المورّد"),
    0xF195: ("Supplier software version", "إصدار البرنامج لدى المورّد"),
    0xF197: ("System name", "اسم النظام"),
    0xF19E: ("ODX file", "ملف ODX"),
}


class UdsError(LinkError):
    pass


class NegativeResponse(UdsError):
    def __init__(self, sid: int, code: int):
        self.sid, self.code_nrc = sid, code
        en, ar = nrcs.explain(code)
        super().__init__(f"0x{sid:02X}: {nrcs.name(code)} (0x{code:02X}) - {en}",
                         f"0x{sid:02X}: {nrcs.name(code)} (0x{code:02X}) - {ar}", f"nrc_{code:02x}")

    @property
    def nrc(self) -> int:
        return self.code_nrc


class Timeout(UdsError):
    def __init__(self, sid: int):
        super().__init__(f"No answer to service 0x{sid:02X}.", f"لا يوجد رد على الخدمة 0x{sid:02X}.", "timeout")


@dataclass
class Dtc:
    code: int              # 3-byte UDS DTC (2 bytes SAE + failure type byte)
    status: int = 0

    @property
    def sae(self) -> str:
        return dtc_str(self.code >> 8)

    @property
    def ftb(self) -> int:
        return self.code & 0xFF

    @property
    def text(self) -> str:
        return f"{self.sae}-{self.ftb:02X}"

    def flags(self) -> list[str]:
        return [STATUS_BITS[i][0] for i in range(8) if self.status & (1 << i)]

    @property
    def confirmed(self) -> bool:
        return bool(self.status & 0x08)

    @property
    def pending(self) -> bool:
        return bool(self.status & 0x04)

    @property
    def active(self) -> bool:
        return bool(self.status & 0x01)

    @property
    def mil(self) -> bool:
        return bool(self.status & 0x80)

    def __repr__(self) -> str:
        return f"Dtc({self.text}, status=0x{self.status:02X})"


@dataclass
class Snapshot:
    dtc: int
    status: int
    records: dict = field(default_factory=dict)      # record number -> {did: bytes}
    raw: bytes = b""


def dtc_str(two: int) -> str:
    """0x0301 -> P0301 (SAE J2012 two-byte format)."""
    letter = "PCBU"[(two >> 14) & 3]
    return f"{letter}{(two >> 12) & 3}{(two >> 8) & 0xF:X}{(two >> 4) & 0xF:X}{two & 0xF:X}"


def dtc_from_str(text: str) -> int:
    """"P0301" -> 0x0301, "U0121" -> 0xC121; with a failure type byte ("P0301-1B" / "P03011B") -> 3 bytes."""
    s = text.strip().upper().replace("-", "")
    if len(s) not in (5, 7) or s[0] not in "PCBU":
        raise ValueError(f"not a DTC: {text}")
    v = ("PCBU".index(s[0]) << 14) | (int(s[1], 16) << 12) | int(s[2:5], 16)
    return (v << 8) | int(s[5:7], 16) if len(s) == 7 else v


def status_text(status: int, lang: str = "en") -> list[str]:
    i = 2 if lang == "ar" else 1
    return [STATUS_BITS[b][i] for b in range(8) if status & (1 << b)]


class UdsClient:
    """UDS requests to one control unit (*tx_id* / *rx_id*; K-line: *tx_id* = address byte)."""

    def __init__(self, link: DiagLink, tx_id: int, rx_id: int | None = None, *, timeout: float = 1.0,
                 p2_star: float = 5.0, did_lengths: dict | None = None):
        self.link = link
        self.tx_id = tx_id
        self.rx_id = rx_id if rx_id is not None else link.rx_for(tx_id)
        self.timeout = timeout
        self.p2_star = p2_star
        self.did_lengths: dict[int, int] = dict(did_lengths or {})     # for snapshot records with several DIDs
        self.session = DEFAULT
        self._tp_thread: threading.Thread | None = None
        self._tp_stop = threading.Event()

    # ------------------------------------------------------------------ core
    def send(self, payload: bytes, timeout: float | None = None, *, suppress: bool = False) -> bytes:
        """Send *payload*; return the positive answer (raises NegativeResponse / Timeout). "Response pending"
        (7F xx 78) answers are waited out up to P2*."""
        payload = bytes(payload)
        sid = payload[0]
        rs = self.link.request(payload, self.tx_id, self.rx_id, timeout or self.timeout, expect=1)
        if suppress and not rs:
            return b""
        r = final(rs)
        deadline = time.monotonic() + self.p2_star
        while r is not None and r.is_pending and r.data[1] == sid and time.monotonic() < deadline:
            more = self.link.listen(self.rx_id, max(0.1, deadline - time.monotonic()))
            r = final(more) if more else None
        if r is None:
            raise Timeout(sid)
        d = r.data
        if d[0] == 0x7F and len(d) >= 3 and d[1] == sid:
            raise NegativeResponse(sid, d[2])
        if d[0] != (sid + 0x40) & 0xFF:
            raise UdsError(f"Unexpected answer {d.hex(' ').upper()} to service 0x{sid:02X}.",
                           f"رد غير متوقع {d.hex(' ').upper()} على الخدمة 0x{sid:02X}.", "unexpected")
        return d

    # ------------------------------------------------------------------ 0x10 / 0x3E / 0x11
    def diagnostic_session(self, session: int = EXTENDED) -> dict:
        d = self.send(bytes([0x10, session]))
        self.session = session
        info = {"session": session}
        if len(d) >= 6:
            info["p2"] = int.from_bytes(d[2:4], "big") / 1000.0
            info["p2_star"] = int.from_bytes(d[4:6], "big") * 10 / 1000.0
            self.p2_star = max(self.p2_star, info["p2_star"])
        return info

    def tester_present(self, suppress: bool = False) -> None:
        self.send(bytes([0x3E, 0x80 if suppress else 0x00]), suppress=suppress)

    def start_keepalive(self, period: float = 2.0) -> None:
        """Send tester present (suppressed answer) every *period* seconds so a non-default session stays open."""
        self.stop_keepalive()
        self._tp_stop.clear()

        def run():
            while not self._tp_stop.wait(period):
                try:
                    self.tester_present(suppress=True)
                except LinkError:
                    pass
        self._tp_thread = threading.Thread(target=run, name="radide-tester-present", daemon=True)
        self._tp_thread.start()

    def stop_keepalive(self) -> None:
        self._tp_stop.set()
        if self._tp_thread is not None:
            self._tp_thread.join(timeout=3)
            self._tp_thread = None

    def ecu_reset(self, kind: int = HARD_RESET) -> None:
        self.send(bytes([0x11, kind]))
        self.session = DEFAULT

    # ------------------------------------------------------------------ 0x14 / 0x19 DTCs
    def clear_dtcs(self, group: int = ALL_DTCS) -> None:
        """ClearDiagnosticInformation: everything (0xFFFFFF), a group, or one DTC (3-byte number)."""
        self.send(bytes([0x14]) + group.to_bytes(3, "big"), timeout=max(self.timeout, 3.0))

    def clear_dtc(self, dtc) -> None:
        """Clear one DTC ("C0035" / "C0035-00" / int); the control unit may answer requestOutOfRange (0x31)
        when it only supports clearing everything."""
        if isinstance(dtc, str):
            v = dtc_from_str(dtc)
            dtc = v if len(dtc.replace("-", "")) == 7 else v << 8
        self.clear_dtcs(int(dtc))

    def dtc_count(self, mask: int = 0xFF) -> int:
        d = self.send(bytes([0x19, REPORT_NUMBER_BY_MASK, mask]))
        return int.from_bytes(d[4:6], "big") if len(d) >= 6 else 0

    @staticmethod
    def _dtc_list(d: bytes, start: int) -> list[Dtc]:
        out = []
        for i in range(start, len(d) - 3, 4):
            out.append(Dtc(int.from_bytes(d[i:i + 3], "big"), d[i + 3]))
        return out

    def read_dtcs(self, mask: int = 0xFF) -> list[Dtc]:
        """reportDTCByStatusMask; 0xFF = every DTC with any status bit, 0x08 = confirmed, 0x04 = pending."""
        d = self.send(bytes([0x19, REPORT_BY_MASK, mask]), timeout=max(self.timeout, 2.0))
        self.availability_mask = d[2] if len(d) > 2 else 0
        return [x for x in self._dtc_list(d, 3) if x.status & mask or mask == 0xFF]

    def supported_dtcs(self) -> list[Dtc]:
        return self._dtc_list(self.send(bytes([0x19, REPORT_SUPPORTED])), 3)

    def permanent_dtcs(self) -> list[Dtc]:
        return self._dtc_list(self.send(bytes([0x19, REPORT_PERMANENT])), 3)

    def snapshot_ids(self) -> list[tuple[int, int]]:
        """(DTC, record number) pairs that have a snapshot (freeze frame)."""
        d = self.send(bytes([0x19, REPORT_SNAPSHOT_IDS]))
        return [(int.from_bytes(d[i:i + 3], "big"), d[i + 3]) for i in range(2, len(d) - 3, 4)]

    def snapshot(self, dtc: int, record: int = 0xFF) -> Snapshot:
        """reportDTCSnapshotRecordByDTCNumber. DIDs whose length is unknown (``did_lengths``) end the parse; the
        bytes stay in ``raw``."""
        d = self.send(bytes([0x19, REPORT_SNAPSHOT_BY_DTC]) + dtc.to_bytes(3, "big") + bytes([record]))
        snap = Snapshot(int.from_bytes(d[2:5], "big"), d[5] if len(d) > 5 else 0, {}, d)
        i = 6
        while i + 2 <= len(d):
            rec, count = d[i], d[i + 1]
            i += 2
            dids = {}
            for _ in range(count):
                if i + 2 > len(d):
                    break
                did = int.from_bytes(d[i:i + 2], "big")
                i += 2
                n = self.did_lengths.get(did)
                if n is None:
                    dids[did] = d[i:]
                    i = len(d)
                    break
                dids[did] = d[i:i + n]
                i += n
            snap.records[rec] = dids
        return snap

    def extended_data(self, dtc: int, record: int = 0xFF) -> dict[int, bytes]:
        """reportDTCExtDataRecordByDTCNumber -> {record number: bytes} (one byte per record unless the unit
        sends a single record, e.g. occurrence counter, aging counter)."""
        d = self.send(bytes([0x19, REPORT_EXT_DATA_BY_DTC]) + dtc.to_bytes(3, "big") + bytes([record]))
        body = d[6:]
        if record != 0xFF:
            return {record: body[1:] if body[:1] == bytes([record]) else body}
        out, i = {}, 0
        while i + 1 < len(body):
            out[body[i]] = body[i + 1:i + 2]
            i += 2
        return out

    # ------------------------------------------------------------------ 0x22 / 0x2E
    def read_did(self, did: int) -> bytes:
        d = self.send(bytes([0x22]) + did.to_bytes(2, "big"))
        if int.from_bytes(d[1:3], "big") != did:
            raise UdsError(f"Answer for DID {int.from_bytes(d[1:3], 'big'):04X}, asked {did:04X}.",
                           f"الرد يخص المعرّف {int.from_bytes(d[1:3], 'big'):04X} والمطلوب {did:04X}.", "unexpected")
        return d[3:]

    def read_dids(self, dids: list[int]) -> dict[int, bytes]:
        """Several DIDs in one request; needs ``did_lengths`` for all but the last."""
        d = self.send(bytes([0x22]) + b"".join(x.to_bytes(2, "big") for x in dids))
        out, i = {}, 1
        while i + 2 <= len(d):
            did = int.from_bytes(d[i:i + 2], "big")
            i += 2
            n = self.did_lengths.get(did, len(d) - i)
            out[did] = d[i:i + n]
            i += n
        return out

    def read_text(self, did: int) -> str:
        return self.read_did(did).rstrip(b"\x00\xff ").decode("ascii", "replace")

    def identification(self, dids=None) -> dict[int, str]:
        """Readable identification strings (VIN, part numbers, versions) the unit answers; others are skipped."""
        out = {}
        for did in dids or IDENT_DIDS:
            try:
                raw = self.read_did(did)
            except (NegativeResponse, Timeout):
                continue
            txt = raw.rstrip(b"\x00\xff ").decode("ascii", "replace")
            out[did] = txt if txt.isprintable() and txt else raw.hex(" ").upper()
        return out

    def write_did(self, did: int, data: bytes) -> None:
        self.send(bytes([0x2E]) + did.to_bytes(2, "big") + bytes(data))

    # ------------------------------------------------------------------ 0x31 routines
    def routine(self, sub: int, rid: int, params: bytes = b"", timeout: float | None = None) -> bytes:
        d = self.send(bytes([0x31, sub]) + rid.to_bytes(2, "big") + bytes(params), timeout=timeout)
        return d[4:]

    def start_routine(self, rid: int, params: bytes = b"") -> bytes:
        return self.routine(START, rid, params)

    def stop_routine(self, rid: int, params: bytes = b"") -> bytes:
        return self.routine(STOP, rid, params)

    def routine_results(self, rid: int) -> bytes:
        return self.routine(RESULTS, rid)

    # ------------------------------------------------------------------ 0x2F actuator tests
    def io_control(self, did: int, param: int, state: bytes = b"", mask: bytes = b"") -> bytes:
        d = self.send(bytes([0x2F]) + did.to_bytes(2, "big") + bytes([param]) + bytes(state) + bytes(mask))
        return d[4:]

    def actuate(self, did: int, state: bytes) -> bytes:
        return self.io_control(did, SHORT_TERM_ADJUST, state)

    def release(self, did: int) -> bytes:
        return self.io_control(did, RETURN_CONTROL)

    # ------------------------------------------------------------------ 0x27 (plug-in only)
    def security_access(self, level: int, plugin, ecu_info: dict | None = None) -> None:
        """Unlock *level* (odd: 1, 3, ...) with a user-supplied plug-in: an object with
        ``compute_key(seed, level, ecu)`` (radide/cardiag/service/security.py loads .py / .dll plug-ins) or a
        plain callable ``f(seed, level, ecu)``. Without a plug-in nothing is sent."""
        if plugin is None:
            raise UdsError("Security access needs a seed/key plug-in you are licensed to use; RAD IDE has no "
                           "built-in algorithms.",
                           "الوصول الأمني يحتاج إضافة seed/key مرخّصًا لك باستخدامها؛ لا يحتوي RAD IDE على خوارزميات "
                           "مدمجة.", "security")
        odd = level if level % 2 else level - 1
        seed = self.send(bytes([0x27, odd]))[2:]
        if seed and not any(seed):
            return                                        # all-zero seed: already unlocked
        info = dict(ecu_info or {"tx": self.tx_id, "rx": self.rx_id})
        fn = getattr(plugin, "compute_key", plugin)
        key = fn(bytes(seed), odd, info)
        if isinstance(key, int):
            key = key.to_bytes(max(1, len(seed)), "big")
        self.send(bytes([0x27, odd + 1]) + bytes(key))


def load_seedkey_plugin(path: str):
    """A user-supplied seed/key plug-in (.py with compute_key / .dll with GenerateKeyEx); see
    radide/cardiag/service/security.py."""
    from ..service.security import load_plugin
    return load_plugin(path)
