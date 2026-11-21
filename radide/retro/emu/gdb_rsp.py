"""A small GDB Remote Serial Protocol client (no Qt in here) for emulators with a GDB stub - mGBA (``-g``,
TCP port 2345, ARM7TDMI of the Game Boy Advance).

RAD IDE has no ARM gdb, so the Retro Debugger talks RSP itself: stop / continue / step, the 16 ARM
registers + CPSR, memory reads and writes, software breakpoints. (With an ``arm-none-eabi-gdb`` on PATH the
user can also attach a real gdb: ``target remote localhost:2345``.)

    rsp = GdbRsp(2345).connect(retry_for=5)
    rsp.interrupt(); regs = rsp.registers(); data = rsp.read_memory(0x08000000, 64)
    rsp.set_breakpoint(0x080000C0); rsp.cont(); rsp.wait_stop(5); rsp.step()
"""
from __future__ import annotations

import socket
import time

ARM_REGS = [f"r{i}" for i in range(13)] + ["sp", "lr", "pc"]


class RspError(Exception):
    pass


def checksum(data: bytes) -> int:
    return sum(data) & 0xFF


def frame(payload: str) -> bytes:
    data = payload.encode("latin-1")
    return b"$" + data + b"#" + f"{checksum(data):02x}".encode()


def unescape(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        c = data[i]
        if c == 0x7D and i + 1 < len(data):          # '}' escape
            out.append(data[i + 1] ^ 0x20)
            i += 2
            continue
        if c == 0x2A and out and i + 1 < len(data):  # '*' run-length
            out.extend(out[-1:] * (data[i + 1] - 29))
            i += 2
            continue
        out.append(c)
        i += 1
    return bytes(out)


class GdbRsp:
    def __init__(self, port: int = 2345, host: str = "127.0.0.1", timeout: float = 5.0):
        self.host, self.port, self.timeout = host, port, timeout
        self.sock: socket.socket | None = None
        self._buf = b""
        self.last_stop = ""

    def connect(self, retry_for: float = 0.0) -> "GdbRsp":
        end = time.time() + retry_for
        while True:
            try:
                self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
                break
            except OSError:
                if time.time() >= end:
                    raise
                time.sleep(0.25)
        try:
            self.command("qSupported:swbreak+;hwbreak+", timeout=3)
        except (TimeoutError, RspError):
            pass
        return self

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    @property
    def connected(self) -> bool:
        return self.sock is not None

    # ------------------------------------------------------------------ packets
    def _read(self, timeout: float) -> None:
        assert self.sock is not None
        self.sock.settimeout(max(timeout, 0.01))
        try:
            chunk = self.sock.recv(65536)
        except socket.timeout as e:
            raise TimeoutError("GDB stub: no answer") from e
        if not chunk:
            self.close()
            raise RspError("the emulator closed the GDB connection")
        self._buf += chunk

    def _packet(self, timeout: float | None = None) -> str:
        deadline = time.time() + (self.timeout if timeout is None else timeout)
        while True:
            self._buf = self._buf.lstrip(b"+")
            start = self._buf.find(b"$")
            if start >= 0:
                end = self._buf.find(b"#", start)
                if end >= 0 and len(self._buf) >= end + 3:
                    body = self._buf[start + 1:end]
                    self._buf = self._buf[end + 3:]
                    if self.sock is not None:
                        self.sock.sendall(b"+")
                    return unescape(body).decode("latin-1")
            left = deadline - time.time()
            if left <= 0:
                raise TimeoutError("GDB stub: no answer")
            self._read(left)

    def send(self, payload: str) -> None:
        if self.sock is None:
            raise RspError("not connected")
        self.sock.sendall(frame(payload))

    def command(self, payload: str, timeout: float | None = None) -> str:
        self.send(payload)
        while True:
            r = self._packet(timeout)
            if r.startswith("O") and len(r) > 1 and all(c in "0123456789abcdefABCDEF" for c in r[1:]):
                continue                                    # console output
            return r

    # ------------------------------------------------------------------ control
    def interrupt(self, timeout: float = 3.0) -> str:
        """Stop the target (Ctrl+C); returns the stop reply (e.g. "S05")."""
        assert self.sock is not None
        self.sock.sendall(b"\x03")
        self.last_stop = self._packet(timeout)
        return self.last_stop

    def halt_reason(self) -> str:
        self.last_stop = self.command("?")
        return self.last_stop

    def cont(self) -> None:
        self.send("c")

    def wait_stop(self, timeout: float = 5.0) -> str | None:
        try:
            self.last_stop = self._packet(timeout)
            return self.last_stop
        except TimeoutError:
            return None

    def step(self, timeout: float = 3.0) -> str:
        self.last_stop = self.command("s", timeout)
        return self.last_stop

    def set_breakpoint(self, addr: int, kind: int = 4) -> bool:
        return self.command(f"Z0,{addr:x},{kind}") == "OK"

    def clear_breakpoint(self, addr: int, kind: int = 4) -> bool:
        return self.command(f"z0,{addr:x},{kind}") == "OK"

    def detach(self) -> None:
        try:
            self.command("D", timeout=2)
        except (TimeoutError, RspError, OSError):
            pass
        self.close()

    # ------------------------------------------------------------------ data
    def registers(self) -> dict[str, int]:
        """r0..r12, sp, lr, pc and cpsr (ARM, little-endian 32-bit words)."""
        raw = self.command("g")
        if raw.startswith("E"):
            raise RspError(f"register read failed: {raw}")
        words = [int.from_bytes(bytes.fromhex(raw[i:i + 8]), "little") for i in range(0, min(len(raw), 16 * 8), 8)]
        out = dict(zip(ARM_REGS, words))
        # after r0-r15 gdb's ARM layout has 8 FPA registers (12 bytes) + fps (4 bytes) + cpsr
        cpsr_at = 16 * 8 + 8 * 24 + 8
        if len(raw) >= cpsr_at + 8:
            out["cpsr"] = int.from_bytes(bytes.fromhex(raw[cpsr_at:cpsr_at + 8]), "little")
        else:
            try:
                r = self.command("p19")
                if r and not r.startswith("E"):
                    out["cpsr"] = int.from_bytes(bytes.fromhex(r[:8]), "little")
            except (TimeoutError, RspError, ValueError):
                pass
        return out

    def read_memory(self, addr: int, length: int) -> bytes:
        out = bytearray()
        while length > 0:
            n = min(length, 0x400)
            r = self.command(f"m{addr:x},{n:x}")
            if r.startswith("E") or not r:
                raise RspError(f"memory read at 0x{addr:08X} failed: {r}")
            out += bytes.fromhex(r)
            addr += n
            length -= n
        return bytes(out)

    def write_memory(self, addr: int, data: bytes) -> bool:
        return self.command(f"M{addr:x},{len(data):x}:{data.hex()}") == "OK"


__all__ = ["ARM_REGS", "GdbRsp", "RspError", "checksum", "frame", "unescape"]
