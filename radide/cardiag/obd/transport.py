"""Transports for the OBD client: ``request(data, timeout) -> [(ecu, payload)]`` (docs/CARDIAG.md).

* `DemoTransport`  - the built-in demo vehicle (vehicle.py), no hardware.
* `LinkTransport`  - wraps a connection of the link slice (radide/cardiag/link: ``DiagLink.request(payload,
  tx_id=None, timeout=...) -> [Response(source, data)]``), i.e. ELM327 / STN / J2534 adapters and the shared
  Demo car simulator; OBD requests go out functionally (0x7DF / 0x18DB33F1 / K-line OBD header).
* `CallableTransport` - any ``f(data) -> [(ecu, payload)]`` (tests, scripts).
"""
from __future__ import annotations

from .vehicle import DemoVehicle


class DemoTransport:
    name = "Demo car"
    is_can = True
    protocol = "ISO 15765-4 CAN (11 bit ID, 500 kbaud) - demo"

    def __init__(self, vehicle: DemoVehicle | None = None):
        self.vehicle = vehicle or DemoVehicle()

    def request(self, data: bytes, timeout: float = 2.0) -> list[tuple[str, bytes]]:
        return self.vehicle.handle(bytes(data))

    def voltage(self) -> float | None:
        return 14.1 if self.vehicle.rpm() > 300 else 12.5

    def describe(self) -> str:
        return f"{self.name} - {self.protocol}"

    def close(self) -> None:
        pass


def _fmt_id(source) -> str:
    if isinstance(source, str):
        return source.upper()
    try:
        from ..link import protocols
        return protocols.fmt_id(source)
    except Exception:  # noqa: BLE001 - link slice not available / different shape
        return f"{source:X}" if isinstance(source, int) else str(source)


class LinkTransport:
    """Adapter from a link-slice ``DiagLink`` to the OBD transport interface."""

    def __init__(self, link):
        self.link = link
        self.name = getattr(link, "adapter_info", "") or getattr(link, "kind", "link")

    @property
    def is_can(self) -> bool:
        return bool(getattr(self.link, "is_can", True))

    @property
    def protocol(self) -> str:
        p = getattr(self.link, "protocol", None)
        return getattr(p, "name", "") or (str(p) if p else "")

    def request(self, data: bytes, timeout: float = 2.0) -> list[tuple[str, bytes]]:
        try:
            rs = self.link.request(bytes(data), tx_id=None, timeout=timeout)
        except TypeError:                                    # an older / simpler signature
            rs = self.link.request(bytes(data))
        except Exception as e:  # noqa: BLE001 - NoResponse is "no ECU answered"
            if type(e).__name__ == "NoResponse":
                return []
            raise
        out = []
        for r in rs or []:
            if isinstance(r, tuple):
                src, payload = r
            else:
                src, payload = getattr(r, "source", "?"), getattr(r, "data", b"")
            payload = bytes(payload)
            if len(payload) >= 3 and payload[0] == 0x7F and payload[2] == 0x78:
                continue                                     # response pending
            out.append((_fmt_id(src), payload))
        return out

    def voltage(self) -> float | None:
        f = getattr(self.link, "voltage", None)
        try:
            return f() if callable(f) else None
        except Exception:  # noqa: BLE001
            return None

    def describe(self) -> str:
        d = getattr(self.link, "describe", None)
        try:
            return d() if callable(d) else self.name
        except Exception:  # noqa: BLE001
            return self.name

    def close(self) -> None:
        try:
            self.link.close()
        except Exception:  # noqa: BLE001
            pass


class CallableTransport:
    is_can = True
    name = "callable"
    protocol = ""

    def __init__(self, fn, is_can: bool = True):
        self.fn, self.is_can = fn, is_can

    def request(self, data: bytes, timeout: float = 2.0):
        return self.fn(bytes(data))

    def describe(self) -> str:
        return self.name

    def close(self) -> None:
        pass
