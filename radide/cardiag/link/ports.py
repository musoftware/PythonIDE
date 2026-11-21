"""COM port discovery for OBD adapters (USB cables and paired Bluetooth SPP adapters) and automatic baud rate
detection by asking ``ATI`` at the usual speeds."""
from __future__ import annotations

from dataclasses import dataclass

from .base import LinkError
from .log import BUS_LOG
from .transport import AUTO_BAUDS, SerialTransport

# USB-serial chips found in OBD cables (VID:PID) -> hint
USB_HINTS = {
    (0x0403, 0x6001): "FTDI FT232 (OBDLink SX / genuine ELM cables)",
    (0x0403, 0x6015): "FTDI FT231X (OBDLink EX / SX)",
    (0x10C4, 0xEA60): "Silicon Labs CP210x",
    (0x1A86, 0x7523): "CH340 (common ELM327 clones)",
    (0x067B, 0x2303): "Prolific PL2303 (older ELM327 cables)",
    (0x0483, 0x5740): "STM32 virtual COM (STN / OBDLink MX+ USB)",
}


@dataclass
class PortInfo:
    device: str             # COM5
    description: str
    hwid: str
    bluetooth: bool
    hint: str = ""

    @property
    def label(self) -> str:
        kind = "Bluetooth" if self.bluetooth else "USB"
        extra = f" - {self.hint}" if self.hint else ""
        return f"{self.device}: {self.description} [{kind}]{extra}"


def list_ports() -> list[PortInfo]:
    try:
        from serial.tools import list_ports as lp
    except ImportError as e:
        raise LinkError("pyserial is not installed (pip install pyserial).",
                        "مكتبة pyserial غير مثبتة (pip install pyserial).", "missing_dep") from e
    out = []
    for p in lp.comports():
        hwid = (p.hwid or "").upper()
        bt = "BTHENUM" in hwid or "BLUETOOTH" in (p.description or "").upper()
        hint = USB_HINTS.get((p.vid, p.pid), "") if p.vid is not None else ""
        out.append(PortInfo(p.device, p.description or p.device, p.hwid or "", bt, hint))
    out.sort(key=lambda x: (x.bluetooth, int("".join(c for c in x.device if c.isdigit()) or 0)))
    return out


def looks_like_adapter(reply: bytes) -> str:
    """The adapter identification in an ``ATI`` / ``ATZ`` answer, or ""."""
    text = reply.decode("ascii", "replace")
    for line in text.replace("\n", "\r").split("\r"):
        s = line.strip(" >")
        u = s.upper()
        if u.startswith(("ELM327", "ELM329", "ELM323", "STN", "OBDLINK", "OBDII", "SCANTOOL", "V-LINK", "VGATE")):
            return s
    return ""


def detect_baud(port: str, bauds: list[int] | None = None, log=None) -> tuple[int, str]:
    """Open *port* at each speed and send ``ATI``; return (baud, identification). Raises LinkError."""
    log = log or BUS_LOG
    last_error = None
    for baud in bauds or AUTO_BAUDS:
        try:
            t = SerialTransport(port, baud)
        except LinkError as e:
            last_error = e
            if e.code == "open_failed":
                raise                               # port busy / missing: other speeds will not help
            continue
        try:
            t.write(b"\r")
            t.read_until(b">", 0.3)
            t.flush_input()
            log.tx("elm", f"[{baud}] ATI")
            t.write(b"ATI\r")
            reply = t.read_until(b">", 0.8)
            ident = looks_like_adapter(reply)
            if ident:
                log.info("elm", f"{port}: adapter answered at {baud} baud: {ident}")
                return baud, ident
        except LinkError as e:
            last_error = e
        finally:
            t.close()
    raise LinkError(f"No ELM327-compatible adapter answered on {port}" + (f" ({last_error.en})" if last_error else ""),
                    f"لم يرد أي محوّل متوافق مع ELM327 على {port}", "no_adapter")


def probe_ports(ports: list[PortInfo] | None = None) -> list[tuple[PortInfo, int, str]]:
    """Every COM port with an adapter on it: (port, baud, identification)."""
    found = []
    for p in ports if ports is not None else list_ports():
        try:
            baud, ident = detect_baud(p.device)
            found.append((p, baud, ident))
        except LinkError:
            continue
    return found
