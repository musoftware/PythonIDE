"""ISO 15765-2 (ISO-TP) transport: segmentation of long diagnostic messages into CAN frames, reassembly and flow
control. Used for raw CAN interfaces (python-can, J2534 in raw CAN mode, the Demo car's virtual CAN bus);
ELM327 adapters and J2534 ISO15765 channels do this themselves.

Frame types (first nibble of the PCI byte): 0 single frame, 1 first frame, 2 consecutive frame, 3 flow control.
Classic CAN (8 bytes) and CAN FD escapes (single frame length 0 + length byte, first frame length 0 + 32-bit
length) are supported, as is extended / mixed addressing (an address byte before the PCI).
"""
from __future__ import annotations

import time

SF, FF, CF, FC = 0, 1, 2, 3
FC_CTS, FC_WAIT, FC_OVERFLOW = 0, 1, 2
DEFAULT_PADDING = 0xAA


class IsoTpError(Exception):
    pass


def frame_type(frame: bytes, ext: bool = False) -> int:
    return frame[1 if ext else 0] >> 4


def _pad(frame: bytes, dl: int, padding: int | None) -> bytes:
    if padding is None or len(frame) >= dl:
        return frame
    if dl > 8:                                   # CAN FD: pad up to the next valid DLC length
        for size in (8, 12, 16, 20, 24, 32, 48, 64):
            if size >= len(frame):
                dl = size
                break
    return frame + bytes([padding]) * (dl - len(frame))


def segment(payload: bytes, dl: int = 8, padding: int | None = DEFAULT_PADDING,
            ext: int | None = None) -> list[bytes]:
    """The frames for *payload*: [single frame] or [first frame, consecutive frames...]."""
    payload = bytes(payload)
    if not payload:
        raise IsoTpError("empty payload")
    pre = bytes([ext]) if ext is not None else b""
    room = dl - len(pre)
    n = len(payload)
    if n <= room - 1 and n <= 7:
        return [_pad(pre + bytes([n]) + payload, dl, padding)]
    if dl > 8 and n <= room - 2:
        return [_pad(pre + bytes([0x00, n]) + payload, dl, padding)]
    if n <= 4095:
        head = pre + bytes([0x10 | (n >> 8), n & 0xFF])
    else:
        head = pre + bytes([0x10, 0x00]) + n.to_bytes(4, "big")
    first_len = dl - len(head)
    frames = [head + payload[:first_len]]
    pos, seq = first_len, 1
    while pos < n:
        chunk = payload[pos:pos + room - 1]
        frames.append(_pad(pre + bytes([0x20 | (seq & 0x0F)]) + chunk, dl, padding))
        pos += len(chunk)
        seq += 1
    return frames


def flow_control(status: int = FC_CTS, bs: int = 0, stmin: int = 0, ext: int | None = None, dl: int = 8,
                 padding: int | None = DEFAULT_PADDING) -> bytes:
    pre = bytes([ext]) if ext is not None else b""
    return _pad(pre + bytes([0x30 | status, bs & 0xFF, stmin & 0xFF]), min(dl, 8), padding)


def stmin_seconds(b: int) -> float:
    """Separation time byte -> seconds (0x00-0x7F ms, 0xF1-0xF9 = 100-900 us, reserved = 127 ms)."""
    if b <= 0x7F:
        return b / 1000.0
    if 0xF1 <= b <= 0xF9:
        return (b - 0xF0) / 10000.0
    return 0.127


def parse_flow_control(frame: bytes, ext: bool = False) -> tuple[int, int, int]:
    o = 1 if ext else 0
    if len(frame) < o + 3 or frame[o] >> 4 != FC:
        raise IsoTpError(f"not a flow control frame: {frame.hex(' ')}")
    return frame[o] & 0x0F, frame[o + 1], frame[o + 2]


class Reassembler:
    """Receive side for one sender. ``feed(frame)`` returns:

    * ``("done", payload)``  - a complete message;
    * ``("fc", None)``       - a first frame (or a full block) arrived: send a flow control frame now;
    * ``("more", None)``     - waiting for more consecutive frames;
    * ``("flow", (status, bs, stmin))`` - the frame was a flow control frame (for the sender side);
    * ``("ignore", None)``   - unexpected consecutive frame while idle (ignored, as the standard says).
    Raises IsoTpError on a wrong sequence number.
    """

    def __init__(self, ext: bool = False, block_size: int = 0):
        self.ext = ext
        self.block_size = block_size
        self.reset()

    def reset(self) -> None:
        self.expected = 0
        self.buf = bytearray()
        self.seq = 0
        self.in_block = 0

    @property
    def busy(self) -> bool:
        return self.expected > 0

    def feed(self, frame: bytes):
        o = 1 if self.ext else 0
        if len(frame) <= o:
            return "ignore", None
        pci = frame[o]
        kind = pci >> 4
        if kind == SF:
            n = pci & 0x0F
            start = o + 1
            if n == 0 and len(frame) > o + 1:          # CAN FD escape
                n, start = frame[o + 1], o + 2
            self.reset()
            if n == 0 or start + n > len(frame):
                raise IsoTpError(f"bad single frame length: {frame.hex(' ')}")
            return "done", bytes(frame[start:start + n])
        if kind == FF:
            n = ((pci & 0x0F) << 8) | frame[o + 1]
            start = o + 2
            if n == 0:
                n = int.from_bytes(frame[o + 2:o + 6], "big")
                start = o + 6
            self.reset()
            self.expected = n
            self.buf = bytearray(frame[start:])
            self.seq = 1
            self.in_block = 0
            return "fc", None
        if kind == CF:
            if not self.busy:
                return "ignore", None
            if (pci & 0x0F) != (self.seq & 0x0F):
                got = pci & 0x0F
                self.reset()
                raise IsoTpError(f"consecutive frame out of sequence (expected {self.seq & 0x0F}, got {got})")
            self.seq += 1
            self.buf += frame[o + 1:]
            if len(self.buf) >= self.expected:
                data = bytes(self.buf[:self.expected])
                self.reset()
                return "done", data
            self.in_block += 1
            if self.block_size and self.in_block >= self.block_size:
                self.in_block = 0
                return "fc", None
            return "more", None
        if kind == FC:
            return "flow", parse_flow_control(frame, self.ext)
        return "ignore", None


class IsoTpChannel:
    """Request / response over a raw CAN interface (``send(can_id, data, extended)`` and
    ``recv(timeout) -> (can_id, data) | None``) between one tester id and one control unit id."""

    def __init__(self, can, tx_id: int, rx_id: int, *, block_size: int = 0, stmin: int = 0,
                 padding: int | None = DEFAULT_PADDING, dl: int = 8, timeout: float = 1.0, max_wait_frames: int = 10,
                 ext_tx: int | None = None, ext_rx: int | None = None):
        self.can, self.tx_id, self.rx_id = can, tx_id, rx_id
        self.block_size, self.stmin, self.padding, self.dl = block_size, stmin, padding, dl
        self.timeout = timeout                   # N_Bs / N_Cr
        self.max_wait_frames = max_wait_frames
        self.ext_tx, self.ext_rx = ext_tx, ext_rx
        self.extended = tx_id > 0x7FF

    def _send_frame(self, data: bytes) -> None:
        self.can.send(self.tx_id, data, self.extended)

    def _recv_frame(self, timeout: float) -> bytes | None:
        end = time.monotonic() + timeout
        while True:
            left = end - time.monotonic()
            if left <= 0:
                return None
            got = self.can.recv(left)
            if got is None:
                return None
            cid, data = got[0], got[1]
            if cid != self.rx_id:
                continue
            if self.ext_rx is not None:
                if not data or data[0] != self.ext_rx:
                    continue
            return bytes(data)

    def send(self, payload: bytes) -> None:
        frames = segment(payload, self.dl, self.padding, self.ext_tx)
        self._send_frame(frames[0])
        if len(frames) == 1:
            return
        ext = self.ext_rx is not None
        idx, waits = 1, 0
        while idx < len(frames):
            fc = self._recv_frame(self.timeout)
            if fc is None:
                raise IsoTpError("no flow control frame from the receiver (N_Bs timeout)")
            if frame_type(fc, ext) != FC:
                continue
            status, bs, st = parse_flow_control(fc, ext)
            if status == FC_WAIT:
                waits += 1
                if waits > self.max_wait_frames:
                    raise IsoTpError("too many flow control WAIT frames")
                continue
            if status == FC_OVERFLOW:
                raise IsoTpError("the receiver reported a buffer overflow")
            sep = stmin_seconds(st)
            count = 0
            while idx < len(frames) and (bs == 0 or count < bs):
                if sep and count:
                    time.sleep(sep)
                self._send_frame(frames[idx])
                idx += 1
                count += 1

    def recv(self, timeout: float | None = None) -> bytes | None:
        """The next complete message from the control unit (None on time-out)."""
        r = Reassembler(self.ext_rx is not None, self.block_size)
        end = time.monotonic() + (timeout if timeout is not None else self.timeout)
        while True:
            left = end - time.monotonic()
            if left <= 0:
                return None
            frame = self._recv_frame(left if not r.busy else min(left + self.timeout, self.timeout))
            if frame is None:
                if r.busy:
                    raise IsoTpError("consecutive frame missing (N_Cr timeout)")
                return None
            state, data = r.feed(frame)
            if state == "done":
                return data
            if state == "fc":
                self._send_frame(flow_control(FC_CTS, self.block_size, self.stmin, self.ext_tx, self.dl,
                                              self.padding))

    def request(self, payload: bytes, timeout: float | None = None) -> bytes | None:
        self.send(payload)
        return self.recv(timeout)
