"""KWP2000 (ISO 14230-3) basics for older control units (K-line or KWP-on-CAN): 0x10 sessions, 0x3E tester
present, 0x1A read ECU identification, 0x18 read DTCs by status, 0x14 clear, 0x21 / 0x22 read data by local /
common identifier, 0x31 / 0x32 / 0x33 routines (start / stop / results) and 0x30 IO control by local id."""
from __future__ import annotations

from .base import DiagLink
from .uds import NegativeResponse, Timeout, UdsClient, UdsError, dtc_str

SESSION_DEFAULT, SESSION_PROGRAMMING, SESSION_EXTENDED = 0x81, 0x85, 0x89

# 0x18 status byte (ISO 14230-3): bits 5-6 = DTC state, bit 7 = warning lamp
KWP_STATE = {0: ("No fault present", "لا يوجد عطل حالي"),
             1: ("Fault not present now (stored)", "العطل غير موجود الآن (مخزَّن)"),
             2: ("Fault present now (active)", "العطل موجود الآن (نشط)"),
             3: ("Fault present and stored", "العطل موجود ومخزَّن")}

IDENT_OPTIONS = {0x80: ("ECU identification data table", "جدول بيانات تعريف الوحدة"),
                 0x86: ("Manufacturer specific", "خاص بالصانع"),
                 0x87: ("Vehicle manufacturer spare part number", "رقم قطعة الغيار لدى الصانع"),
                 0x88: ("Vehicle manufacturer ECU software number", "رقم برنامج الوحدة لدى الصانع"),
                 0x8A: ("System supplier", "المورّد"),
                 0x8C: ("ECU serial number", "الرقم التسلسلي للوحدة"),
                 0x90: ("VIN", "رقم الشاسيه (VIN)"),
                 0x91: ("Vehicle manufacturer ECU hardware number", "رقم عتاد الوحدة لدى الصانع"),
                 0x92: ("System supplier ECU hardware number", "رقم العتاد لدى المورّد"),
                 0x94: ("System supplier ECU software number", "رقم البرنامج لدى المورّد"),
                 0x97: ("System name", "اسم النظام")}


class KwpDtc:
    def __init__(self, code: int, status: int):
        self.code, self.status = code, status

    @property
    def text(self) -> str:
        return dtc_str(self.code)

    @property
    def state(self) -> int:
        return (self.status >> 5) & 3

    @property
    def mil(self) -> bool:
        return bool(self.status & 0x80)

    def __repr__(self) -> str:
        return f"KwpDtc({self.text}, status=0x{self.status:02X})"


class KwpClient(UdsClient):
    """Same request / NRC / response-pending handling as UdsClient, KWP2000 service set."""

    def __init__(self, link: DiagLink, tx_id: int, rx_id: int | None = None, **kw):
        super().__init__(link, tx_id, rx_id, **kw)
        self.session = SESSION_DEFAULT

    def start_session(self, session: int = SESSION_EXTENDED) -> None:
        self.send(bytes([0x10, session]))
        self.session = session

    def tester_present(self, suppress: bool = False) -> None:
        self.send(bytes([0x3E, 0x02 if suppress else 0x01]), suppress=suppress)

    def read_ecu_identification(self, option: int = 0x80) -> bytes:
        return self.send(bytes([0x1A, option]))[2:]

    def identification(self, options=None) -> dict[int, str]:
        out = {}
        for opt in options or (0x90, 0x87, 0x88, 0x8A, 0x8C, 0x91, 0x94, 0x97):
            try:
                raw = self.read_ecu_identification(opt)
            except (NegativeResponse, Timeout):
                continue
            txt = raw.rstrip(b"\x00\xff ").decode("ascii", "replace")
            out[opt] = txt if txt and txt.isprintable() else raw.hex(" ").upper()
        return out

    def read_dtcs_by_status(self, status: int = 0x02, group: int = 0xFF00) -> list[KwpDtc]:
        """0x18 readDiagnosticTroubleCodesByStatus (status 0x02 = all identified DTCs, group 0xFF00 = all)."""
        d = self.send(bytes([0x18, status]) + group.to_bytes(2, "big"), timeout=max(self.timeout, 2.0))
        n = d[1] if len(d) > 1 else 0
        out = []
        for i in range(n):
            j = 2 + i * 3
            if j + 3 > len(d):
                break
            out.append(KwpDtc(int.from_bytes(d[j:j + 2], "big"), d[j + 2]))
        return out

    def clear_dtcs(self, group: int = 0xFF00) -> None:
        self.send(bytes([0x14]) + (group & 0xFFFF).to_bytes(2, "big"), timeout=max(self.timeout, 3.0))

    def read_local(self, lid: int) -> bytes:
        d = self.send(bytes([0x21, lid]))
        if d[1] != lid:
            raise UdsError(f"Answer for local id {d[1]:02X}, asked {lid:02X}.",
                           f"الرد يخص المعرّف المحلي {d[1]:02X} والمطلوب {lid:02X}.", "unexpected")
        return d[2:]

    def read_common(self, cid: int) -> bytes:
        return self.send(bytes([0x22]) + cid.to_bytes(2, "big"))[3:]

    def start_routine_local(self, lid: int, params: bytes = b"") -> bytes:
        return self.send(bytes([0x31, lid]) + bytes(params))[2:]

    def stop_routine_local(self, lid: int, params: bytes = b"") -> bytes:
        return self.send(bytes([0x32, lid]) + bytes(params))[2:]

    def routine_results_local(self, lid: int) -> bytes:
        return self.send(bytes([0x33, lid]))[2:]

    def io_control_local(self, lid: int, param: int, state: bytes = b"") -> bytes:
        return self.send(bytes([0x30, lid, param]) + bytes(state))[2:]
