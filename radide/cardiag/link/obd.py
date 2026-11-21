"""OBD-II (SAE J1979 / ISO 15031-5) service layer over any DiagLink.

Modes: 01 current data, 02 freeze frame, 03 stored DTCs, 04 clear DTCs and stored values, 05 / 06 oxygen
sensor and on-board monitoring test results, 07 pending DTCs, 08 control of on-board systems (e.g. EVAP leak
test), 09 vehicle information (VIN, calibration ids, CVN, ECU name) and 0A permanent DTCs.
``PIDS`` decodes the standard mode 01 / 02 PIDs (formulas from the standard; names and Arabic are ours).

Readiness (PID 01) is only *read*: RAD IDE never fakes monitor status.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .base import DiagLink, LinkError, Response
from .uds import dtc_str


def _u16(b):
    return (b[0] << 8) | b[1]


def _s16(b):
    v = _u16(b)
    return v - 0x10000 if v & 0x8000 else v


# pid: (English name, Arabic name, unit, data bytes, decode(bytes) -> value)
PIDS: dict[int, tuple[str, str, str, int, object]] = {
    0x04: ("Calculated engine load", "حمل المحرك المحسوب", "%", 1, lambda b: b[0] * 100 / 255),
    0x05: ("Engine coolant temperature", "حرارة سائل التبريد", "°C", 1, lambda b: b[0] - 40),
    0x06: ("Short term fuel trim - bank 1", "تصحيح الوقود قصير المدى - الصف 1", "%", 1, lambda b: b[0] * 100 / 128 - 100),
    0x07: ("Long term fuel trim - bank 1", "تصحيح الوقود طويل المدى - الصف 1", "%", 1, lambda b: b[0] * 100 / 128 - 100),
    0x08: ("Short term fuel trim - bank 2", "تصحيح الوقود قصير المدى - الصف 2", "%", 1, lambda b: b[0] * 100 / 128 - 100),
    0x09: ("Long term fuel trim - bank 2", "تصحيح الوقود طويل المدى - الصف 2", "%", 1, lambda b: b[0] * 100 / 128 - 100),
    0x0A: ("Fuel pressure (gauge)", "ضغط الوقود", "kPa", 1, lambda b: b[0] * 3),
    0x0B: ("Intake manifold absolute pressure", "ضغط مشعب السحب المطلق", "kPa", 1, lambda b: b[0]),
    0x0C: ("Engine speed", "سرعة المحرك", "rpm", 2, lambda b: _u16(b) / 4),
    0x0D: ("Vehicle speed", "سرعة السيارة", "km/h", 1, lambda b: b[0]),
    0x0E: ("Timing advance", "تقديم الإشعال", "° before TDC", 1, lambda b: b[0] / 2 - 64),
    0x0F: ("Intake air temperature", "حرارة هواء السحب", "°C", 1, lambda b: b[0] - 40),
    0x10: ("Mass air flow rate", "معدل تدفق كتلة الهواء", "g/s", 2, lambda b: _u16(b) / 100),
    0x11: ("Throttle position", "وضع الخانق (الثروتل)", "%", 1, lambda b: b[0] * 100 / 255),
    0x1C: ("OBD standard", "معيار OBD", "", 1, lambda b: b[0]),
    0x1F: ("Run time since engine start", "زمن التشغيل منذ بدء المحرك", "s", 2, lambda b: _u16(b)),
    0x21: ("Distance travelled with MIL on", "المسافة المقطوعة ولمبة المحرك مضاءة", "km", 2, lambda b: _u16(b)),
    0x22: ("Fuel rail pressure (rel. manifold)", "ضغط مجرى الوقود (نسبةً للمشعب)", "kPa", 2, lambda b: _u16(b) * 0.079),
    0x23: ("Fuel rail gauge pressure", "ضغط مجرى الوقود", "kPa", 2, lambda b: _u16(b) * 10),
    0x2C: ("Commanded EGR", "نسبة EGR المطلوبة", "%", 1, lambda b: b[0] * 100 / 255),
    0x2D: ("EGR error", "خطأ EGR", "%", 1, lambda b: b[0] * 100 / 128 - 100),
    0x2E: ("Commanded evaporative purge", "تطهير البخار المطلوب", "%", 1, lambda b: b[0] * 100 / 255),
    0x2F: ("Fuel tank level", "مستوى خزان الوقود", "%", 1, lambda b: b[0] * 100 / 255),
    0x30: ("Warm-ups since codes cleared", "عدد مرات الإحماء منذ مسح الأعطال", "", 1, lambda b: b[0]),
    0x31: ("Distance since codes cleared", "المسافة منذ مسح الأعطال", "km", 2, lambda b: _u16(b)),
    0x33: ("Barometric pressure", "الضغط الجوي", "kPa", 1, lambda b: b[0]),
    0x3C: ("Catalyst temperature B1S1", "حرارة المحفّز الصف 1 الحساس 1", "°C", 2, lambda b: _u16(b) / 10 - 40),
    0x42: ("Control module voltage", "جهد وحدة التحكم", "V", 2, lambda b: _u16(b) / 1000),
    0x43: ("Absolute load value", "قيمة الحمل المطلقة", "%", 2, lambda b: _u16(b) * 100 / 255),
    0x44: ("Commanded air-fuel equivalence ratio", "نسبة الهواء/الوقود المطلوبة (لامدا)", "λ", 2,
           lambda b: _u16(b) * 2 / 65536),
    0x45: ("Relative throttle position", "وضع الخانق النسبي", "%", 1, lambda b: b[0] * 100 / 255),
    0x46: ("Ambient air temperature", "حرارة الجو المحيط", "°C", 1, lambda b: b[0] - 40),
    0x47: ("Absolute throttle position B", "وضع الخانق المطلق B", "%", 1, lambda b: b[0] * 100 / 255),
    0x49: ("Accelerator pedal position D", "وضع دواسة الوقود D", "%", 1, lambda b: b[0] * 100 / 255),
    0x4A: ("Accelerator pedal position E", "وضع دواسة الوقود E", "%", 1, lambda b: b[0] * 100 / 255),
    0x4C: ("Commanded throttle actuator", "مشغّل الخانق المطلوب", "%", 1, lambda b: b[0] * 100 / 255),
    0x4D: ("Time run with MIL on", "زمن التشغيل ولمبة المحرك مضاءة", "min", 2, lambda b: _u16(b)),
    0x4E: ("Time since codes cleared", "الزمن منذ مسح الأعطال", "min", 2, lambda b: _u16(b)),
    0x51: ("Fuel type", "نوع الوقود", "", 1, lambda b: b[0]),
    0x52: ("Ethanol fuel %", "نسبة الإيثانول في الوقود", "%", 1, lambda b: b[0] * 100 / 255),
    0x59: ("Fuel rail absolute pressure", "ضغط مجرى الوقود المطلق", "kPa", 2, lambda b: _u16(b) * 10),
    0x5A: ("Relative accelerator pedal position", "وضع دواسة الوقود النسبي", "%", 1, lambda b: b[0] * 100 / 255),
    0x5B: ("Hybrid battery pack remaining life", "العمر المتبقي لبطارية الهايبرد", "%", 1, lambda b: b[0] * 100 / 255),
    0x5C: ("Engine oil temperature", "حرارة زيت المحرك", "°C", 1, lambda b: b[0] - 40),
    0x5E: ("Engine fuel rate", "معدل استهلاك الوقود", "L/h", 2, lambda b: _u16(b) / 20),
    0x61: ("Driver's demand engine torque", "عزم المحرك المطلوب من السائق", "%", 1, lambda b: b[0] - 125),
    0x62: ("Actual engine torque", "عزم المحرك الفعلي", "%", 1, lambda b: b[0] - 125),
    0x63: ("Engine reference torque", "العزم المرجعي للمحرك", "Nm", 2, lambda b: _u16(b)),
    0xA6: ("Odometer", "عدّاد المسافة", "km", 4, lambda b: int.from_bytes(b[:4], "big") / 10),
}

FUEL_SYSTEM = {1: ("Open loop - not warm yet", "حلقة مفتوحة - المحرك لم يسخن بعد"),
               2: ("Closed loop (oxygen sensor)", "حلقة مغلقة (حساس الأكسجين)"),
               4: ("Open loop - load / deceleration", "حلقة مفتوحة - حمل أو تباطؤ"),
               8: ("Open loop - system fault", "حلقة مفتوحة - عطل في النظام"),
               16: ("Closed loop with a feedback fault", "حلقة مغلقة مع عطل في التغذية الراجعة")}

# readiness monitors: (name EN, name AR) for PID 01 bytes B (common) and C / D (spark vs. compression)
MON_COMMON = [("Misfire", "الإخفاق في الإشعال"), ("Fuel system", "نظام الوقود"), ("Components", "المكونات")]
MON_SPARK = [("Catalyst", "المحفّز"), ("Heated catalyst", "المحفّز المسخَّن"), ("EVAP system", "نظام البخار EVAP"),
             ("Secondary air", "الهواء الثانوي"), ("A/C refrigerant", "غاز التكييف"), ("Oxygen sensor", "حساس الأكسجين"),
             ("Oxygen sensor heater", "سخان حساس الأكسجين"), ("EGR / VVT system", "نظام EGR / VVT")]
MON_DIESEL = [("NMHC catalyst", "محفّز NMHC"), ("NOx / SCR aftertreatment", "معالجة NOx / SCR"), ("", ""),
              ("Boost pressure", "ضغط التوربو"), ("", ""), ("Exhaust gas sensor", "حساس غازات العادم"),
              ("PM filter (DPF)", "فلتر الجسيمات (DPF)"), ("EGR / VVT system", "نظام EGR / VVT")]


@dataclass
class Monitor:
    name: str
    name_ar: str
    supported: bool
    complete: bool


@dataclass
class MonitorStatus:
    mil: bool
    dtc_count: int
    diesel: bool
    monitors: list = field(default_factory=list)

    @property
    def incomplete(self) -> list[Monitor]:
        return [m for m in self.monitors if m.supported and not m.complete]


def decode_monitor_status(b: bytes) -> MonitorStatus:
    """PID 01 (4 bytes A B C D)."""
    a, bb, c, d = (list(b) + [0, 0, 0, 0])[:4]
    diesel = bool(bb & 0x08)
    mons = [Monitor(n, ar, bool(bb & (1 << i)), not (bb & (1 << (i + 4)))) for i, (n, ar) in enumerate(MON_COMMON)]
    for i, (n, ar) in enumerate(MON_DIESEL if diesel else MON_SPARK):
        if n:
            mons.append(Monitor(n, ar, bool(c & (1 << i)), not (d & (1 << i))))
    return MonitorStatus(bool(a & 0x80), a & 0x7F, diesel, mons)


def decode_pid(pid: int, data: bytes):
    """(value, unit) for a known PID; raw bytes and "" otherwise."""
    if pid == 0x01:
        return decode_monitor_status(data), ""
    if pid == 0x03:
        return FUEL_SYSTEM.get(data[0], (f"0x{data[0]:02X}", ""))[0] if data else "", ""
    spec = PIDS.get(pid)
    if spec is None or len(data) < spec[3]:
        return bytes(data), ""
    return spec[4](bytes(data[:spec[3]])), spec[2]


def decode_dtcs(data: bytes, can: bool) -> list[str]:
    """Mode 03 / 07 / 0A answer -> ["P0301", ...] (CAN answers start with a count byte)."""
    body = data[1:]
    if can and body:
        n, body = body[0], body[1:]
        body = body[:2 * n]
    out = []
    for i in range(0, len(body) - 1, 2):
        v = (body[i] << 8) | body[i + 1]
        if v:
            out.append(dtc_str(v))
    return out


class ObdError(LinkError):
    pass


class Obd:
    """OBD-II requests. Functional by default (every emissions control unit answers); results are keyed by the
    answering unit (CAN id / K-line address)."""

    def __init__(self, link: DiagLink, timeout: float = 1.0):
        self.link = link
        self.timeout = timeout
        self._supported: dict[int, dict[int, set]] = {}

    def _req(self, payload: bytes, tx_id=None, timeout=None) -> list[Response]:
        rs = self.link.request(payload, tx_id, None, timeout or self.timeout)
        want = payload[0] + 0x40
        return [r for r in rs if r.data[:1] == bytes([want])]

    # ------------------------------------------------------------------ mode 01 / 02
    def supported_pids(self, mode: int = 1, tx_id=None) -> dict[int, set]:
        """{unit: {supported PIDs}} following the 00 / 20 / 40 ... chain."""
        out: dict[int, set] = {}
        base = 0
        while base <= 0xE0:
            req = bytes([mode, base]) if mode != 2 else bytes([2, base, 0])
            rs = self._req(req, tx_id)
            more = False
            for r in rs:
                bits = int.from_bytes(r.data[2:6], "big")
                s = out.setdefault(r.source, set())
                for i in range(32):
                    if bits & (1 << (31 - i)):
                        s.add(base + i + 1)
                more = more or bool(bits & 1)
            if not more:
                break
            base += 0x20
        self._supported[mode] = out
        return out

    def read_pid(self, pid: int, tx_id=None) -> dict[int, bytes]:
        """{unit: data bytes} for mode 01 *pid*."""
        return {r.source: r.data[2:] for r in self._req(bytes([1, pid]), tx_id) if r.data[1:2] == bytes([pid])}

    def query(self, pid: int, tx_id=None):
        """(value, unit) from the first answering unit, or None."""
        got = self.read_pid(pid, tx_id)
        if not got:
            return None
        src = min(got)
        return decode_pid(pid, got[src])

    def monitor_status(self, tx_id=None) -> dict[int, MonitorStatus]:
        return {k: decode_monitor_status(v) for k, v in self.read_pid(0x01, tx_id).items()}

    def freeze_frame(self, pid: int, frame: int = 0, tx_id=None) -> dict[int, bytes]:
        return {r.source: r.data[3:] for r in self._req(bytes([2, pid, frame]), tx_id) if r.data[1:2] == bytes([pid])}

    def freeze_frame_dtc(self, frame: int = 0, tx_id=None) -> dict[int, str]:
        """The DTC that stored freeze frame *frame* (PID 02)."""
        out = {}
        for src, b in self.freeze_frame(0x02, frame, tx_id).items():
            if len(b) >= 2 and (b[0] or b[1]):
                out[src] = dtc_str((b[0] << 8) | b[1])
        return out

    # ------------------------------------------------------------------ DTCs
    def _dtcs(self, mode: int, tx_id=None) -> dict[int, list[str]]:
        out: dict[int, list[str]] = {}
        for r in self._req(bytes([mode]), tx_id, max(self.timeout, 2.0)):
            out.setdefault(r.source, []).extend(decode_dtcs(r.data, self.link.is_can))
        return out

    def stored_dtcs(self, tx_id=None) -> dict[int, list[str]]:
        return self._dtcs(0x03, tx_id)

    def pending_dtcs(self, tx_id=None) -> dict[int, list[str]]:
        return self._dtcs(0x07, tx_id)

    def permanent_dtcs(self, tx_id=None) -> dict[int, list[str]]:
        return self._dtcs(0x0A, tx_id)

    def clear_dtcs(self, tx_id=None) -> bool:
        """Mode 04: clears stored / pending DTCs, freeze frames and resets readiness to "not complete" (the car
        has to complete its drive cycle again). Permanent DTCs stay until the monitor passes."""
        rs = self.link.request(b"\x04", tx_id, None, max(self.timeout, 3.0))
        if any(r.data[:1] == b"\x44" for r in rs):
            return True
        neg = next((r for r in rs if r.is_negative), None)
        if neg is not None:
            from .uds import NegativeResponse
            raise NegativeResponse(0x04, neg.data[2])
        return False

    # ------------------------------------------------------------------ mode 06 / 08
    def test_results(self, mid: int, tx_id=None) -> dict[int, list[dict]]:
        """Mode 06 (CAN format): {unit: [{mid, tid, uasid, value, min, max, passed}]} raw scaled values."""
        out = {}
        for r in self._req(bytes([6, mid]), tx_id):
            d, rows = r.data[1:], []
            for i in range(0, len(d) - 8, 9):
                val, lo, hi = _u16(d[i + 3:i + 5]), _u16(d[i + 5:i + 7]), _u16(d[i + 7:i + 9])
                rows.append({"mid": d[i], "tid": d[i + 1], "uasid": d[i + 2], "value": val, "min": lo, "max": hi,
                             "passed": lo <= val <= hi})
            out[r.source] = rows
        return out

    def control(self, tid: int, data: bytes = b"", tx_id=None) -> list[Response]:
        """Mode 08 request (e.g. TID 01 = EVAP system leak test)."""
        return self.link.request(bytes([8, tid]) + bytes(data), tx_id, None, max(self.timeout, 2.0))

    # ------------------------------------------------------------------ mode 09
    def _info(self, pid: int, tx_id=None) -> dict[int, bytes]:
        """Mode 09 answer bytes after the item count, K-line multi-message answers merged."""
        rs = self._req(bytes([9, pid]), tx_id, max(self.timeout, 2.0))
        out: dict[int, bytes] = {}
        if self.link.is_can:
            for r in rs:
                if r.data[1:2] == bytes([pid]):
                    out[r.source] = r.data[3:]
            return out
        parts: dict[int, dict[int, bytes]] = {}
        for r in rs:
            if r.data[1:2] == bytes([pid]) and len(r.data) >= 3:
                parts.setdefault(r.source, {})[r.data[2]] = r.data[3:]
        for src, p in parts.items():
            out[src] = b"".join(p[k] for k in sorted(p))
        return out

    def vin(self, tx_id=None) -> str:
        for src, b in sorted(self._info(0x02, tx_id).items()):
            v = b.lstrip(b"\x00").decode("ascii", "replace").strip()
            if v:
                return v
        return ""

    def calibration_ids(self, tx_id=None) -> dict[int, list[str]]:
        out = {}
        for src, b in self._info(0x04, tx_id).items():
            out[src] = [b[i:i + 16].rstrip(b"\x00").decode("ascii", "replace") for i in range(0, len(b), 16)]
        return out

    def cvns(self, tx_id=None) -> dict[int, list[str]]:
        return {src: [b[i:i + 4].hex().upper() for i in range(0, len(b), 4)]
                for src, b in self._info(0x06, tx_id).items()}

    def ecu_names(self, tx_id=None) -> dict[int, str]:
        return {src: b.rstrip(b"\x00").decode("ascii", "replace").replace("\x00", "")
                for src, b in self._info(0x0A, tx_id).items()}
