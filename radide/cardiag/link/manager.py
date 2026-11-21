"""Open a diagnostic link from a ``LinkConfig`` (what the Connect dialog saves): Demo car, serial / USB /
Bluetooth SPP COM port (automatic baud rate), Wi-Fi (TCP), Bluetooth LE, J2534 PassThru or a python-can
interface."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from . import protocols
from .base import DiagLink, LinkError
from .log import BUS_LOG

KINDS = [  # kind, English, Arabic
    ("demo", "Demo car (no hardware)", "السيارة التجريبية (بدون أجهزة)"),
    ("serial", "ELM327 / OBDLink - USB or Bluetooth (COM port)", "ELM327 / OBDLink - USB أو بلوتوث (منفذ COM)"),
    ("wifi", "ELM327 Wi-Fi (TCP)", "ELM327 واي فاي (TCP)"),
    ("ble", "ELM327 Bluetooth LE", "ELM327 بلوتوث منخفض الطاقة"),
    ("j2534", "J2534 PassThru device", "جهاز J2534 PassThru"),
    ("pythoncan", "CAN interface (python-can)", "واجهة CAN (python-can)"),
]


@dataclass
class LinkConfig:
    kind: str = "demo"
    port: str = ""                      # COM5 / socket://... (serial)
    baud: int = 0                       # 0 = automatic
    host: str = "192.168.0.10"
    tcp_port: int = 35000
    ble_address: str = ""
    j2534_library: str = ""
    can_interface: str = ""             # python-can: "pcan", "kvaser", "slcan", "vector", ...
    can_channel: str = ""
    protocol: str = protocols.AUTO      # ELM protocol number, "0" = automatic
    demo_protocol: str = "6"            # which bus the Demo car uses
    demo_stn: bool = False              # Demo car identifies itself as an STN chip
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "LinkConfig":
        known = {k: v for k, v in (d or {}).items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def describe(self) -> str:
        if self.kind == "demo":
            return "Demo car"
        if self.kind == "serial":
            return f"{self.port} @ {self.baud or 'auto'}"
        if self.kind == "wifi":
            return f"tcp://{self.host}:{self.tcp_port}"
        if self.kind == "ble":
            return f"BLE {self.ble_address}"
        if self.kind == "j2534":
            return f"J2534 {self.j2534_library}"
        return f"{self.can_interface} {self.can_channel}"


ALIASES = {"elm_serial": "serial", "elm_wifi": "wifi", "elm_ble": "ble", "elm": "serial", "tcp": "wifi",
           "can": "pythoncan", "sim": "demo"}


def config_from(kind: str = "demo", port: str = "", protocol: str | None = None, **kw) -> LinkConfig:
    """A LinkConfig from loose arguments: ``kind`` (also elm_serial / elm_wifi / elm_ble), ``port`` = COM port,
    "host:port" (Wi-Fi), BLE address or J2534 DLL depending on the kind."""
    kind = ALIASES.get(kind, kind)
    proto = str(protocol or protocols.AUTO)
    if proto.lower() in ("auto", "a", ""):
        proto = protocols.AUTO
    cfg = LinkConfig.from_dict({**kw, "kind": kind, "protocol": proto})
    if port:
        if kind == "serial":
            cfg.port = port
        elif kind == "wifi":
            host, _, p = port.rpartition(":")
            cfg.host, cfg.tcp_port = (host or port), int(p) if p.isdigit() else cfg.tcp_port
        elif kind == "ble":
            cfg.ble_address = port
        elif kind == "j2534":
            cfg.j2534_library = port
        elif kind == "pythoncan":
            cfg.can_interface, _, cfg.can_channel = port.partition(":")
    return cfg


def open_link(cfg: LinkConfig | None = None, log=None, car=None, **kw) -> DiagLink:
    """Create, open and return the link (raises LinkError with an English / Arabic message).
    ``open_link(LinkConfig(...))`` or ``open_link(kind="elm_serial", port="COM5", protocol="0")``."""
    if cfg is None:
        cfg = config_from(**kw)
    elif isinstance(cfg, str):
        cfg = config_from(cfg, **kw)
    log = log or BUS_LOG
    kind = ALIASES.get(cfg.kind, cfg.kind)
    if kind == "demo":
        from ..sim import demo_car
        from ..sim.elm import ElmInterpreter
        from .elm import ElmLink
        from .transport import LoopbackTransport
        car = car or demo_car()
        car.protocol = cfg.demo_protocol or "6"
        dev = ElmInterpreter(car, stn="STN1110 v4.2.1" if cfg.demo_stn else None)
        link = ElmLink(LoopbackTransport(dev), cfg.protocol, log)
    elif kind == "serial":
        from .elm import ElmLink
        from .ports import detect_baud
        from .transport import SerialTransport
        if not cfg.port:
            raise LinkError("Choose a COM port first.", "اختر منفذ COM أولًا.", "config")
        baud = cfg.baud
        if not baud and "://" not in cfg.port:
            baud, _ident = detect_baud(cfg.port, log=log)
        link = ElmLink(SerialTransport(cfg.port, baud or 38400), cfg.protocol, log)
    elif kind == "wifi":
        from .elm import ElmLink
        from .transport import TcpTransport
        link = ElmLink(TcpTransport(cfg.host, cfg.tcp_port), cfg.protocol, log)
    elif kind == "ble":
        from .elm import ElmLink
        from .transport import BleTransport
        if not cfg.ble_address:
            raise LinkError("Scan and choose a Bluetooth LE adapter first.", "ابحث واختر محوّل بلوتوث منخفض الطاقة أولًا.",
                            "config")
        link = ElmLink(BleTransport(cfg.ble_address), cfg.protocol, log)
    elif kind == "j2534":
        from .j2534 import J2534Link, devices
        dev = next((d for d in devices() if d.library == cfg.j2534_library), None) or cfg.j2534_library
        if not dev:
            raise LinkError("Choose a J2534 device first.", "اختر جهاز J2534 أولًا.", "config")
        link = J2534Link(dev, cfg.protocol, log)
    elif kind == "pythoncan":
        from .rawcan import PythonCanInterface, RawCanLink
        p = protocols.get(cfg.protocol) if cfg.protocol != protocols.AUTO else protocols.get("6")
        iface = PythonCanInterface(interface=cfg.can_interface, channel=cfg.can_channel, bitrate=p.bitrate)
        link = RawCanLink(iface, p.code, log=log, name=f"{cfg.can_interface} {cfg.can_channel}")
    else:
        raise LinkError(f"Unknown adapter type: {kind}", f"نوع محوّل غير معروف: {kind}", "config")
    try:
        link.open()
    except LinkError:
        try:
            link.close()
        except Exception:  # noqa: BLE001
            pass
        raise
    return link


def demo_link(car=None, protocol: str = "6", stn: bool = False, log=None) -> DiagLink:
    """An open ELM327 link to the (shared) Demo car - the quickest way to try the stack in a script."""
    return open_link(LinkConfig(kind="demo", demo_protocol=protocol, demo_stn=stn), log=log, car=car)


def demo_can_link(car=None, log=None) -> DiagLink:
    """An open raw-CAN link (our ISO-TP) to the Demo car's virtual CAN bus."""
    from ..sim import demo_car
    from ..sim.canbus import VirtualCanBus
    from .rawcan import RawCanLink
    car = car or demo_car()
    bus = VirtualCanBus(car)
    link = RawCanLink(bus.endpoint(), car.protocol if car.protocol in ("6", "7", "8", "9") else "6", log=log,
                      name="Demo car virtual CAN")
    link.bus = bus
    link.open()
    return link


# the link the IDE's car diagnostics windows share (set by the Connect dialog)
_CURRENT: DiagLink | None = None
_LISTENERS: list = []


def current_link() -> DiagLink | None:
    return _CURRENT if (_CURRENT is not None and _CURRENT.is_open) else None


def set_current_link(link: DiagLink | None) -> None:
    global _CURRENT
    if _CURRENT is not None and _CURRENT is not link:
        try:
            _CURRENT.close()
        except Exception:  # noqa: BLE001
            pass
    _CURRENT = link
    for fn in list(_LISTENERS):
        try:
            fn(link)
        except Exception:  # noqa: BLE001
            pass


def on_link_changed(fn) -> None:
    if fn not in _LISTENERS:
        _LISTENERS.append(fn)
