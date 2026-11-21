"""yaAGC (Virtual AGC) integration: the socket protocol the DSKY speaks, a Qt link for RAD IDE's DSKY panel and
a small driver for yaAGC's debugger console.

Socket protocol (yaAGC listens, peripherals connect; default port 19697): every message is 4 bytes
``00pppppp 01pppddd 10dddddd 11dddddd`` - p = 9-bit channel, d = 15-bit value. Bit 0x20 of the first byte
("u-bit") marks a mask packet: the next value packet only changes the bits set in the mask (used for the
PRO key, channel 32 bit 14). Written for RAD IDE from the description in Virtual AGC's documentation.
"""
from __future__ import annotations

import re

from .isa import KEY_CODES

DEFAULT_PORT = 19697


def form_packet(channel: int, value: int, mask: bool = False) -> bytes:
    channel &= 0x1FF
    value &= 0x7FFF
    b0 = (channel >> 3) | (0x20 if mask else 0)
    b1 = 0x40 | ((channel << 3) & 0x38) | ((value >> 12) & 0x07)
    b2 = 0x80 | ((value >> 6) & 0x3F)
    b3 = 0xC0 | (value & 0x3F)
    return bytes((b0, b1, b2, b3))


def parse_packets(buf: bytes) -> tuple[list[tuple[int, int, bool]], bytes]:
    """Split a byte stream into (channel, value, u-bit) packets; returns (packets, unparsed rest).
    Bytes that do not start a packet are skipped (re-synchronisation)."""
    out = []
    i = 0
    n = len(buf)
    while i + 4 <= n:
        b0, b1, b2, b3 = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]
        if (b0 & 0xC0) == 0x00 and (b1 & 0xC0) == 0x40 and (b2 & 0xC0) == 0x80 and (b3 & 0xC0) == 0xC0:
            ch = ((b0 & 0x1F) << 3) | ((b1 >> 3) & 7)
            val = ((b1 << 12) & 0x7000) | ((b2 << 6) & 0x0FC0) | (b3 & 0x3F)
            out.append((ch, val, bool(b0 & 0x20)))
            i += 4
        else:
            i += 1
    return out, buf[i:]


def key_packets(name: str) -> bytes:
    """Packets for one DSKY key ("VERB", "5", ...): channel 15 = key code."""
    return form_packet(0o15, KEY_CODES[name.upper()])


def pro_packets(pressed: bool) -> bytes:
    """PRO key: mask channel 32 bit 14, then 0 (pressed) or the bit (released)."""
    return form_packet(0o32, 0o20000, mask=True) + form_packet(0o32, 0 if pressed else 0o20000)


# ============================================================================ Qt link
try:
    from PyQt6.QtCore import QObject, QTimer, pyqtSignal
    from PyQt6.QtNetwork import QAbstractSocket, QTcpSocket
except Exception:  # noqa: BLE001 - the protocol helpers above work without Qt
    QObject = object  # type: ignore[assignment,misc]


if QObject is not object:
    class YaAgcLink(QObject):
        """RAD IDE's DSKY as a yaAGC peripheral (connects to localhost:port, retries until yaAGC listens)."""
        channel = pyqtSignal(int, int)
        connected = pyqtSignal()
        disconnected = pyqtSignal()

        def __init__(self, port: int = DEFAULT_PORT, host: str = "127.0.0.1", parent=None):
            super().__init__(parent)
            self.host, self.port = host, port
            self.sock = QTcpSocket(self)
            self.sock.readyRead.connect(self._read)
            self.sock.connected.connect(self.connected.emit)
            self.sock.disconnected.connect(self.disconnected.emit)
            self._buf = b""
            self._retry = QTimer(self)
            self._retry.setInterval(500)
            self._retry.timeout.connect(self._try)
            self.tries = 0

        def start(self) -> None:
            self._retry.start()
            self._try()

        def stop(self) -> None:
            self._retry.stop()
            self.sock.abort()

        def is_connected(self) -> bool:
            return self.sock.state() == QAbstractSocket.SocketState.ConnectedState

        def _try(self) -> None:
            if self.is_connected():
                self._retry.stop()
                return
            if self.sock.state() == QAbstractSocket.SocketState.UnconnectedState:
                self.tries += 1
                self.sock.connectToHost(self.host, self.port)

        def _read(self) -> None:
            self._buf += bytes(self.sock.readAll())
            packets, self._buf = parse_packets(self._buf)
            for ch, val, ubit in packets:
                if not ubit:
                    self.channel.emit(ch, val)

        def send_key(self, name: str) -> None:
            if self.is_connected():
                self.sock.write(key_packets(name))

        def set_pro(self, pressed: bool) -> None:
            if self.is_connected():
                self.sock.write(pro_packets(pressed))


# ============================================================================ debugger console
STOP_RX = re.compile(r"\x1a\x1a(?P<file>[^\n]*?):(?P<line>\d+):\d+:beg:0x(?P<addr>[0-9a-fA-F]+)")   # C:\... paths too
REG_RX = re.compile(r"^(?P<name>[A-Z0-9]+)\s+0x(?P<hex>[0-9a-fA-F]+)\s+(?P<dec>-?\d+)", re.M)
PROMPT = "(agc) "


def parse_stop(text: str):
    """(file, line, address) from yaAGC's --fullname location annotation, or None."""
    m = None
    for m in STOP_RX.finditer(text):
        pass
    if m is None:
        return None
    return m.group("file"), int(m.group("line")), int(m.group("addr"), 16)


def parse_registers(text: str) -> dict[str, int]:
    """'info registers' output -> {name: value}."""
    return {m.group("name"): int(m.group("hex"), 16) for m in REG_RX.finditer(text)}


def debugger_commands() -> dict[str, str]:
    """IDE action -> yaAGC debugger command (gdb style)."""
    return {"continue": "cont", "step": "step", "next": "next", "registers": "info registers",
            "break": "break {file}:{line}", "delete": "delete", "quit": "quit"}


__all__ = ["DEFAULT_PORT", "PROMPT", "debugger_commands", "form_packet", "key_packets", "parse_packets",
           "parse_registers", "parse_stop", "pro_packets"] + (["YaAgcLink"] if QObject is not object else [])
