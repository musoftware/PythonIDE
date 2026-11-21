"""Diagnostics over a raw CAN interface with our own ISO-TP (isotp.py): python-can buses (PCAN, Kvaser, Vector,
SocketCAN, slcan / CANable ...; optional ``pip install python-can``) and the Demo car's virtual CAN bus.
Functional requests collect multi-frame answers from several control units at the same time."""
from __future__ import annotations

import time

from . import isotp, protocols
from .base import DiagLink, LinkError, Response


class CanInterface:
    """``send(can_id, data, extended)``, ``recv(timeout) -> (can_id, data) | None``, ``close()``."""

    def send(self, can_id: int, data: bytes, extended: bool = False) -> None:
        raise NotImplementedError

    def recv(self, timeout: float):
        raise NotImplementedError

    def close(self) -> None:
        pass


class PythonCanInterface(CanInterface):
    """A python-can bus, e.g. ``PythonCanInterface(interface="pcan", channel="PCAN_USBBUS1", bitrate=500000)``."""

    def __init__(self, **bus_kwargs):
        try:
            import can  # python-can
        except ImportError as e:
            raise LinkError("python-can is not installed (pip install python-can).",
                            "مكتبة python-can غير مثبتة (pip install python-can).", "missing_dep") from e
        self._can = can
        try:
            self.bus = can.Bus(**bus_kwargs)
        except Exception as e:  # noqa: BLE001 - driver missing / device busy
            raise LinkError(f"Cannot open the CAN interface: {e}", f"تعذّر فتح واجهة CAN: {e}", "open_failed") from e

    def send(self, can_id: int, data: bytes, extended: bool = False) -> None:
        self.bus.send(self._can.Message(arbitration_id=can_id, data=data, is_extended_id=extended))

    def recv(self, timeout: float):
        m = self.bus.recv(timeout)
        if m is None or m.is_error_frame:
            return None
        return m.arbitration_id, bytes(m.data)

    def close(self) -> None:
        try:
            self.bus.shutdown()
        except Exception:  # noqa: BLE001
            pass


class RawCanLink(DiagLink):
    kind = "rawcan"
    channel = "can"

    def __init__(self, can: CanInterface, protocol: str = "6", *, padding: int | None = isotp.DEFAULT_PADDING,
                 block_size: int = 0, stmin: int = 0, log=None, name: str = "CAN interface"):
        super().__init__(log)
        self.can = can
        self.protocol = protocols.get(protocol)
        if self.protocol is None or not self.protocol.is_can:
            raise LinkError("A raw CAN link needs a CAN protocol (6-9).", "اتصال CAN الخام يحتاج بروتوكول CAN (6-9).")
        self.padding, self.block_size, self.stmin = padding, block_size, stmin
        self.adapter_info = name

    def open(self) -> None:
        self.is_open = True
        self.log.info(self.channel, f"open {self.adapter_info} ({self.protocol.name})")

    def close(self) -> None:
        if self.is_open:
            self.can.close()
        self.is_open = False

    # ------------------------------------------------------------------ frames with logging
    def _send(self, can_id: int, data: bytes) -> None:
        self.log.tx(self.channel, f"{protocols.fmt_id(can_id)} {data.hex(' ').upper()}")
        self.can.send(can_id, data, can_id > 0x7FF or self.bits29)

    def _recv(self, timeout: float):
        got = self.can.recv(timeout)
        if got is not None:
            self.log.rx(self.channel, f"{protocols.fmt_id(got[0])} {bytes(got[1]).hex(' ').upper()}")
        return got

    def _accepts(self, can_id: int, rx_id: int | None) -> bool:
        if rx_id is not None:
            return can_id == rx_id
        if self.bits29:
            return (can_id & 0xFFFFFF00) == 0x18DAF100          # 18 DA F1 xx: answer to the tester F1
        return 0x7E8 <= can_id <= 0x7EF

    def _collect(self, rx_id: int | None, timeout: float, expect: int | None) -> list[Response]:
        """Frames until *timeout* passes without a new frame (P2) or *expect* complete answers arrived."""
        asm: dict[int, isotp.Reassembler] = {}
        raw: dict[int, list] = {}
        out: list[Response] = []
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            got = self._recv(max(0.001, end - time.monotonic()))
            if got is None:
                if any(a.busy for a in asm.values()):
                    continue
                break
            cid, data = got
            if not self._accepts(cid, rx_id):
                continue
            r = asm.setdefault(cid, isotp.Reassembler(False, self.block_size))
            raw.setdefault(cid, []).append(data)
            try:
                state, payload = r.feed(data)
            except isotp.IsoTpError as e:
                self.log.error(self.channel, str(e))
                continue
            if state == "fc":
                self._send(protocols.request_id(cid),
                           isotp.flow_control(isotp.FC_CTS, self.block_size, self.stmin, padding=self.padding))
                end = max(end, time.monotonic() + 1.0)
            elif state == "done":
                out.append(Response(cid, payload, raw.pop(cid, [])))
                if payload[:1] == b"\x7F" and len(payload) > 2 and payload[2] == 0x78:
                    end = max(end, time.monotonic() + 5.0)         # response pending: P2* applies
                    continue
                if expect and len([o for o in out if not o.is_pending]) >= expect:
                    break
        return out

    def _request(self, payload, tx_id, rx_id, timeout, expect):
        functional = tx_id is None
        if functional:
            tx_id = protocols.FUNC_29 if self.bits29 else protocols.FUNC_11
            if len(payload) > 7:
                raise LinkError("Functional requests must fit in one frame.", "الطلبات العامة يجب أن تكون إطارًا واحدًا.")
        frames = isotp.segment(payload, 8, self.padding)
        self._send(tx_id, frames[0])
        if len(frames) > 1:
            fc = None
            end = time.monotonic() + 1.0
            while time.monotonic() < end:
                got = self._recv(end - time.monotonic())
                if got is None:
                    break
                if got[0] == rx_id and got[1] and got[1][0] >> 4 == isotp.FC:
                    fc = got[1]
                    break
            if fc is None:
                raise LinkError("The control unit sent no flow control frame.", "لم ترسل وحدة التحكم إطار التحكم بالتدفق.")
            status, bs, st = isotp.parse_flow_control(fc)
            sep = isotp.stmin_seconds(st)
            count = 0
            for f in frames[1:]:
                if bs and count and count % bs == 0:
                    got = self._recv(1.0)              # next flow control frame
                if sep:
                    time.sleep(sep)
                self._send(tx_id, f)
                count += 1
        return self._collect(None if functional else rx_id, timeout, None if functional else (expect or 1))

    def listen(self, rx_id=None, timeout=2.0):
        with self.lock:
            return self._collect(rx_id, timeout, 1)
