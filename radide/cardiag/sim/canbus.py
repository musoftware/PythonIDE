"""A virtual CAN bus with the Demo car's control units speaking ISO-TP (frames, flow control, block size,
separation time) - the counterpart for link/rawcan.RawCanLink and the ISO-TP tests. Single-threaded: frames are
delivered while the tester sends / receives; late answers ("response pending") are delivered when due."""
from __future__ import annotations

import time
from collections import deque

from ..link import isotp
from ..link.protocols import FUNC_11, FUNC_29
from ..link.rawcan import CanInterface


class _Node:
    def __init__(self, bus, ecu):
        self.bus, self.ecu = bus, ecu
        self.asm = isotp.Reassembler(block_size=bus.ecu_block_size)
        self.tx_frames: list[bytes] = []          # consecutive frames waiting for the tester's flow control
        self.block_size = bus.ecu_block_size
        self.stmin = bus.ecu_stmin

    @property
    def req_id(self) -> int:
        return (0x18DA00F1 | (self.ecu.addr << 8)) if self.bus.bits29 else self.ecu.tx

    @property
    def resp_id(self) -> int:
        return (0x18DAF100 | self.ecu.addr) if self.bus.bits29 else self.ecu.rx

    def on_frame(self, can_id: int, data: bytes) -> None:
        functional = can_id == (FUNC_29 if self.bus.bits29 else FUNC_11)
        if not functional and can_id != self.req_id:
            return
        try:
            state, payload = self.asm.feed(data)
        except isotp.IsoTpError:
            return
        if state == "fc":
            self.bus.push(self.resp_id, isotp.flow_control(isotp.FC_CTS, self.block_size, self.stmin))
        elif state == "flow":
            status, bs, _st = payload
            if status == isotp.FC_CTS and self.tx_frames:
                n = len(self.tx_frames) if bs == 0 else bs
                for f in self.tx_frames[:n]:
                    self.bus.push(self.resp_id, f)
                self.tx_frames = self.tx_frames[n:]
        elif state == "done":
            for delay, answer in self.ecu.handle(payload, functional, True):
                self.bus.schedule(delay, self, answer)

    def send_message(self, answer: bytes) -> None:
        frames = isotp.segment(answer, 8, self.bus.padding)
        self.bus.push(self.resp_id, frames[0])
        self.tx_frames = frames[1:]


class VirtualCanBus:
    def __init__(self, car, *, padding: int | None = 0xAA, ecu_block_size: int = 0, ecu_stmin: int = 0):
        self.car = car
        self.padding = padding
        self.ecu_block_size, self.ecu_stmin = ecu_block_size, ecu_stmin
        self.nodes = [_Node(self, e) for e in car.ecus]
        self.rx: deque = deque()                  # frames for the tester
        self.later: list[tuple[float, _Node, bytes]] = []
        self.frames_seen: list[tuple[int, bytes]] = []

    @property
    def bits29(self) -> bool:
        return self.car.protocol in ("7", "9")

    def push(self, can_id: int, data: bytes) -> None:
        self.frames_seen.append((can_id, bytes(data)))
        self.rx.append((can_id, bytes(data)))

    def schedule(self, delay: float, node: _Node, answer: bytes) -> None:
        if delay <= 0:
            node.send_message(answer)
        else:
            self.later.append((time.monotonic() + delay / max(0.001, self.car.time_scale), node, answer))

    def deliver(self, can_id: int, data: bytes) -> None:
        self.frames_seen.append((can_id, bytes(data)))
        if not self.car.ignition:
            return
        with self.car.lock:
            for n in self.nodes:
                n.on_frame(can_id, bytes(data))

    def poll(self) -> None:
        now = time.monotonic()
        due = [x for x in self.later if x[0] <= now]
        if due:
            self.later = [x for x in self.later if x[0] > now]
            with self.car.lock:
                for _t, node, answer in due:
                    node.send_message(answer)

    def endpoint(self) -> "VirtualCanInterface":
        return VirtualCanInterface(self)


class VirtualCanInterface(CanInterface):
    def __init__(self, bus: VirtualCanBus):
        self.bus = bus

    def send(self, can_id: int, data: bytes, extended: bool = False) -> None:
        self.bus.deliver(can_id, data)

    def recv(self, timeout: float):
        end = time.monotonic() + timeout
        while True:
            self.bus.poll()
            if self.bus.rx:
                return self.bus.rx.popleft()
            if time.monotonic() >= end:
                return None
            time.sleep(0.002)
