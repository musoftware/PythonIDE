"""Control unit discovery: functional OBD request (every emissions unit answers), then a physical scan of the
common diagnostic addresses with UDS TesterPresent (any answer, even negative, means a unit is there), then
identification (VIN, part / software numbers, system name)."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import protocols
from .base import LinkError
from .uds import IDENT_DIDS, NegativeResponse, Timeout, UdsClient

# 11-bit request ids worth trying first (rx = tx + 8 unless listed in PAIRS)
QUICK_11 = [0x7E0, 0x7E1, 0x7E2, 0x7E3, 0x7E4, 0x7E5, 0x7E6, 0x7E7,
            0x700, 0x710, 0x714, 0x720, 0x726, 0x730, 0x737, 0x740, 0x744, 0x746, 0x750, 0x752, 0x760,
            0x765, 0x770, 0x772, 0x7A0, 0x7B0, 0x7C0, 0x7C6, 0x7D0, 0x7D2]
# a few manufacturers answer on other offsets (VW group: 0x7xx -> 0x7xx + 0x6A)
PAIRS = {0x710: 0x77A, 0x713: 0x77D, 0x714: 0x77E, 0x715: 0x77F, 0x70E: 0x778}
QUICK_29 = [0x10, 0x11, 0x12, 0x13, 0x17, 0x18, 0x1E, 0x28, 0x29, 0x40, 0x58, 0x60, 0x80, 0x98]
QUICK_KLINE = [0x10, 0x11, 0x17, 0x18, 0x28, 0x29, 0x40, 0x58, 0x60]

# typical roles (a guess - addresses differ between makes)
NAMES_11 = {0x7E0: ("Engine (ECM)", "المحرك (ECM)"), 0x7E1: ("Transmission (TCM)", "ناقل الحركة (TCM)"),
            0x7E2: ("Hybrid / ABS", "الهايبرد / ABS"), 0x7E4: ("Body / BCM", "وحدة الهيكل BCM"),
            0x720: ("Instrument cluster", "لوحة العدادات"), 0x726: ("Body control", "وحدة الهيكل"),
            0x737: ("Airbag", "الوسائد الهوائية"), 0x740: ("Body control", "وحدة الهيكل"),
            0x744: ("Climate control", "التكييف"), 0x746: ("Climate control", "التكييف"),
            0x760: ("ABS / ESP", "الفرامل ABS / ESP"), 0x770: ("Airbag (SRS)", "الوسائد الهوائية (SRS)"),
            0x772: ("Airbag (SRS)", "الوسائد الهوائية (SRS)"), 0x7B0: ("ABS / ESP", "الفرامل ABS / ESP"),
            0x7C0: ("Instrument cluster", "لوحة العدادات"), 0x7D0: ("Steering", "التوجيه")}
NAMES_ADDR = {0x10: ("Engine (ECM)", "المحرك (ECM)"), 0x11: ("Engine 2", "المحرك 2"),
              0x18: ("Transmission (TCM)", "ناقل الحركة (TCM)"), 0x28: ("ABS / ESP", "الفرامل ABS / ESP"),
              0x58: ("Airbag (SRS)", "الوسائد الهوائية (SRS)"), 0x60: ("Instrument cluster", "لوحة العدادات"),
              0x40: ("Body control", "وحدة الهيكل")}


@dataclass
class EcuInfo:
    tx: int
    rx: int
    name: str = ""
    name_ar: str = ""
    obd: bool = False                     # answered the functional OBD request
    uds: bool = False                     # answered UDS (positive or negative)
    ident: dict = field(default_factory=dict)       # DID -> text

    @property
    def label(self) -> str:
        return f"{self.name or 'Control unit'} [{protocols.fmt_id(self.tx)} / {protocols.fmt_id(self.rx)}]"


def _guess(tx: int, bits29: bool, can: bool) -> tuple[str, str]:
    if not can:
        return NAMES_ADDR.get(tx, ("", ""))
    if bits29:
        return NAMES_ADDR.get((tx >> 8) & 0xFF, ("", ""))
    return NAMES_11.get(tx, ("", ""))


def candidates(link, full: bool = False) -> list[tuple[int, int]]:
    """(tx, rx) pairs to try for this link's protocol (*full* = every 11-bit id 0x700-0x7E7 / every 29-bit
    address)."""
    if not link.is_can:
        return [(a, a) for a in (range(0x01, 0xFF) if full else QUICK_KLINE)]
    if link.bits29:
        addrs = range(0x00, 0x100) if full else QUICK_29
        return [(protocols.phys_29(a), protocols.response_id(protocols.phys_29(a), True)) for a in addrs if a != 0xF1]
    ids = list(range(0x700, 0x7E8)) if full else QUICK_11
    return [(t, PAIRS.get(t, t + 8)) for t in ids]


def discover(link, full: bool = False, identify: bool = True, progress=None, cancelled=None,
             timeout: float = 0.15) -> list[EcuInfo]:
    """Find the control units on the bus. *progress(done, total, text)*, *cancelled() -> bool*."""
    found: dict[int, EcuInfo] = {}
    try:
        for r in link.request(b"\x01\x00", None, None, 1.0):
            if r.data[:1] == b"\x41":
                tx = protocols.request_id(r.source) if link.is_can else r.source
                n, ar = _guess(tx, link.bits29, link.is_can)
                found[tx] = EcuInfo(tx, r.source, n, ar, obd=True)
    except LinkError:
        pass
    cands = [c for c in candidates(link, full) if c[0] not in found]
    total = len(cands)
    for i, (tx, rx) in enumerate(cands):
        if cancelled is not None and cancelled():
            break
        if progress is not None:
            progress(i, total, protocols.fmt_id(tx))
        try:
            rs = link.request(b"\x3E\x00", tx, rx if link.is_can else None, timeout)
        except LinkError:
            continue
        if rs:
            n, ar = _guess(tx, link.bits29, link.is_can)
            found[tx] = EcuInfo(tx, rs[0].source if link.is_can else rx, n, ar, uds=True)
    if progress is not None:
        progress(total, total, "")
    ecus = sorted(found.values(), key=lambda e: e.tx)
    if identify:
        for e in ecus:
            if cancelled is not None and cancelled():
                break
            identify_ecu(link, e)
    return ecus


def identify_ecu(link, ecu: EcuInfo, dids=(0xF190, 0xF187, 0xF18A, 0xF18C, 0xF191, 0xF195, 0xF197)) -> EcuInfo:
    c = UdsClient(link, ecu.tx, ecu.rx if link.is_can else None, timeout=0.5)
    for did in dids:
        try:
            raw = c.read_did(did)
            ecu.uds = True
        except NegativeResponse:
            ecu.uds = True
            continue
        except (Timeout, LinkError):
            continue
        txt = raw.rstrip(b"\x00\xff ").decode("ascii", "replace")
        ecu.ident[did] = txt if txt and txt.isprintable() else raw.hex(" ").upper()
    name = ecu.ident.get(0xF197)
    if name and not ecu.name:
        ecu.name = name
    return ecu


def ident_label(did: int, lang: str = "en") -> str:
    n = IDENT_DIDS.get(did)
    return (n[1] if lang == "ar" else n[0]) if n else f"DID {did:04X}"
