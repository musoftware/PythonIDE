"""The diagnostic link every adapter implements (docs/CARDIAG.md "Link layer").

A ``DiagLink`` sends one *service request* (``01 0C``, ``22 F1 90`` ...) and returns the complete answers
(after ISO-TP reassembly) from every control unit that answered. Adapters: ELM327 / STN / OBDLink over a serial
port, Wi-Fi or Bluetooth LE (elm.py), J2534 PassThru (j2534.py), raw CAN through ISO-TP (rawcan.py) and the
Demo car (radide/cardiag/sim). Addressing:

* ``tx_id=None`` - functional (broadcast) OBD request: 0x7DF on 11-bit CAN, 0x18DB33F1 on 29-bit CAN, the OBD
  header 68 6A F1 / C2 33 F1 on K-line / J1850;
* ``tx_id=0x7E0`` - physical request to one control unit; answers are accepted from ``rx_id`` (default: the
  usual pair, 0x7E8 / 0x18DAF1xx). On K-line ``tx_id`` is the control unit's address byte (0x10 = engine).

The service layer (radide/cardiag/service/transport.py) talks through ``exchange()`` / ``receive()``.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

from . import protocols
from .log import BUS_LOG, BusLog

P2_STAR = 5.0          # ISO 14229 default enhanced response time after "response pending"


class LinkError(Exception):
    """An adapter / bus error with an English and an Arabic message."""

    def __init__(self, en: str, ar: str = "", code: str = "link"):
        super().__init__(en)
        self.en, self.ar, self.code = en, ar or en, code

    def text(self, lang: str = "en") -> str:
        return self.ar if lang == "ar" else self.en


class NoResponse(LinkError):
    def __init__(self, what: str = ""):
        super().__init__(f"No answer from the vehicle{(' to ' + what) if what else ''}.",
                         f"لم ترد السيارة{(' على ' + what) if what else ''}.", "no_response")


class NotConnected(LinkError):
    def __init__(self):
        super().__init__("The adapter is not connected.", "المحوّل غير متصل.", "not_connected")


@dataclass
class Response:
    source: int                  # CAN id the answer came from (0x7E8), or the K-line source address (0x10)
    data: bytes                  # the complete service answer (e.g. 41 0C 1A F8)
    raw: list = field(default_factory=list)     # the frames / lines it was built from

    @property
    def sid(self) -> int:
        return self.data[0] if self.data else -1

    @property
    def is_negative(self) -> bool:
        return len(self.data) >= 3 and self.data[0] == 0x7F

    @property
    def nrc(self) -> int | None:
        return self.data[2] if self.is_negative else None

    @property
    def is_pending(self) -> bool:
        return self.is_negative and self.data[2] == 0x78

    def hex(self) -> str:
        return self.data.hex(" ").upper()

    def __repr__(self) -> str:
        return f"Response({protocols.fmt_id(self.source)}: {self.hex()})"


class DiagLink:
    kind = "base"
    channel = "link"

    def __init__(self, log: BusLog | None = None):
        self.log = log or BUS_LOG
        self.protocol: protocols.Protocol | None = None
        self.adapter_info = ""             # "ELM327 v1.5", "STN1110 v4.2", J2534 device name ...
        self.is_open = False
        self.lock = threading.RLock()      # one request at a time (UI timers + worker threads)
        self.default_tx: int | None = None
        self.default_rx: int | None = None

    # ------------------------------------------------------------------ to implement
    def open(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        self.is_open = False

    def _request(self, payload: bytes, tx_id: int | None, rx_id: int | None, timeout: float,
                 expect: int | None) -> list[Response]:
        raise NotImplementedError

    def listen(self, rx_id: int | None = None, timeout: float = 2.0) -> list[Response]:
        """Answers that arrive without a new request (after "response pending" 7F xx 78)."""
        return []

    def voltage(self) -> float | None:
        return None

    # ------------------------------------------------------------------ common
    @property
    def is_can(self) -> bool:
        return bool(self.protocol and self.protocol.is_can)

    @property
    def bits29(self) -> bool:
        return bool(self.protocol and self.protocol.bits29)

    def rx_for(self, tx_id: int | None) -> int | None:
        if tx_id is None or not self.is_can:
            return None
        return protocols.response_id(tx_id, self.bits29)

    def set_target(self, tx_id: int | None, rx_id: int | None = None) -> None:
        """Default physical target for ``request(..., tx_id=...)`` calls that leave it out (None = functional)."""
        self.default_tx, self.default_rx = tx_id, rx_id

    def request(self, payload: bytes, tx_id: int | None = ..., rx_id: int | None = None, timeout: float = 1.0,
                expect: int | None = None) -> list[Response]:
        """Send *payload*; return the answers (possibly several control units, possibly 7F negative answers).
        An empty list means no answer ("NO DATA"). *expect* = number of answers to wait for (ELM speed-up)."""
        if not self.is_open:
            raise NotConnected()
        if tx_id is ...:
            tx_id, rx_id = self.default_tx, (rx_id if rx_id is not None else self.default_rx)
        if rx_id is None and tx_id is not None:
            rx_id = self.rx_for(tx_id)
        with self.lock:
            return self._request(bytes(payload), tx_id, rx_id, timeout, expect)

    def request_one(self, payload: bytes, tx_id: int | None = ..., rx_id: int | None = None,
                    timeout: float = 1.0) -> Response:
        rs = self.request(payload, tx_id, rx_id, timeout, expect=1)
        if not rs:
            raise NoResponse(bytes(payload).hex(" ").upper())
        return final(rs)

    # the service layer's transport shape (radide/cardiag/service/transport.py)
    def exchange(self, request: bytes, tx: int | None = None, rx: int | None = None, timeout: float = 2.0) -> bytes:
        rs = self.request(request, tx, rx, timeout, expect=1)
        rs = [r for r in rs if rx is None or r.source == rx] or rs
        return final(rs).data if rs else b""

    def receive(self, tx: int | None = None, rx: int | None = None, timeout: float = 2.0) -> bytes:
        """The next answer after "response pending" (7F xx 78): waits at least P2* (5 s), as ISO 14229 allows."""
        with self.lock:
            rs = self.listen(rx if rx is not None else self.rx_for(tx), max(timeout, P2_STAR))
        return final(rs).data if rs else b""

    def describe(self) -> str:
        p = self.protocol.name if self.protocol else "?"
        return f"{self.adapter_info or self.kind} - {p}"

    def __enter__(self):
        if not self.is_open:
            self.open()
        return self

    def __exit__(self, *exc):
        self.close()


def final(responses: list[Response]) -> Response | None:
    """The last answer that is not "response pending" (or the pending one when nothing else came)."""
    if not responses:
        return None
    done = [r for r in responses if not r.is_pending]
    return done[-1] if done else responses[-1]
