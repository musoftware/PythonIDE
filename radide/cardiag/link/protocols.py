"""Vehicle bus protocols (ELM327 protocol numbers, J2534 protocol ids) and their addressing conventions."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Protocol:
    code: str            # ELM327 protocol number "1".."C"
    name: str
    name_ar: str
    family: str          # "can", "kline", "j1850"
    bits29: bool = False
    bitrate: int = 0
    j2534: int = 0       # J2534 protocol id (ISO15765 for CAN, ISO9141 / ISO14230 for K-line, J1850)

    @property
    def is_can(self) -> bool:
        return self.family == "can"


# J2534 protocol ids
J1850VPW, J1850PWM, ISO9141, ISO14230, CAN, ISO15765 = 1, 2, 3, 4, 5, 6

PROTOCOLS: dict[str, Protocol] = {p.code: p for p in (
    Protocol("1", "SAE J1850 PWM (41.6 kbaud)", "SAE J1850 PWM (41.6 كيلوبود)", "j1850", j2534=J1850PWM, bitrate=41600),
    Protocol("2", "SAE J1850 VPW (10.4 kbaud)", "SAE J1850 VPW (10.4 كيلوبود)", "j1850", j2534=J1850VPW, bitrate=10400),
    Protocol("3", "ISO 9141-2 (5 baud init)", "ISO 9141-2 (تهيئة 5 بود)", "kline", j2534=ISO9141, bitrate=10400),
    Protocol("4", "ISO 14230-4 KWP (5 baud init)", "ISO 14230-4 KWP (تهيئة 5 بود)", "kline", j2534=ISO14230,
             bitrate=10400),
    Protocol("5", "ISO 14230-4 KWP (fast init)", "ISO 14230-4 KWP (تهيئة سريعة)", "kline", j2534=ISO14230,
             bitrate=10400),
    Protocol("6", "ISO 15765-4 CAN (11 bit ID, 500 kbaud)", "ISO 15765-4 CAN (معرّف 11 بت، 500 كيلوبود)", "can",
             False, 500000, ISO15765),
    Protocol("7", "ISO 15765-4 CAN (29 bit ID, 500 kbaud)", "ISO 15765-4 CAN (معرّف 29 بت، 500 كيلوبود)", "can",
             True, 500000, ISO15765),
    Protocol("8", "ISO 15765-4 CAN (11 bit ID, 250 kbaud)", "ISO 15765-4 CAN (معرّف 11 بت، 250 كيلوبود)", "can",
             False, 250000, ISO15765),
    Protocol("9", "ISO 15765-4 CAN (29 bit ID, 250 kbaud)", "ISO 15765-4 CAN (معرّف 29 بت، 250 كيلوبود)", "can",
             True, 250000, ISO15765),
    Protocol("A", "SAE J1939 CAN (29 bit ID, 250 kbaud)", "SAE J1939 CAN (معرّف 29 بت، 250 كيلوبود)", "can",
             True, 250000, CAN),
)}

AUTO = "0"
# the order ELM327 / our J2534 auto-detect tries (CAN first: every car since 2008 in the US / EU uses it)
DETECT_ORDER = ["6", "8", "7", "9", "5", "4", "3", "2", "1"]

# functional (broadcast) OBD request addresses
FUNC_11 = 0x7DF
FUNC_29 = 0x18DB33F1


def get(code: str | None) -> Protocol | None:
    """Protocol by ELM number; "A6" (ATDPN answer while in automatic mode) means "6"."""
    if code is None:
        return None
    c = str(code).strip().upper()
    if len(c) == 2 and c[0] == "A":
        c = c[1]
    return PROTOCOLS.get(c)


def response_id(tx_id: int, bits29: bool | None = None) -> int:
    """The usual physical response id for a request id: 0x7E0 -> 0x7E8, 0x18DA10F1 -> 0x18DAF110."""
    if bits29 or tx_id > 0x7FF:
        return (tx_id & 0xFFFF0000) | ((tx_id & 0xFF) << 8) | ((tx_id >> 8) & 0xFF)
    return tx_id + 8


def request_id(rx_id: int) -> int:
    """Inverse of response_id (0x7E8 -> 0x7E0, 0x18DAF110 -> 0x18DA10F1)."""
    if rx_id > 0x7FF:
        return (rx_id & 0xFFFF0000) | ((rx_id & 0xFF) << 8) | ((rx_id >> 8) & 0xFF)
    return rx_id - 8


def phys_29(ecu_addr: int, tester: int = 0xF1) -> int:
    """ISO 15765-4 normal fixed addressing request id to *ecu_addr* (0x10 -> 0x18DA10F1)."""
    return 0x18DA0000 | (ecu_addr << 8) | tester


def fmt_id(can_id: int) -> str:
    return f"{can_id:08X}" if can_id > 0x7FF else f"{can_id:03X}"
