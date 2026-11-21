"""SAE J2534-1 (04.04) PassThru interfaces: enumeration of the installed devices from the Windows registry and a
ctypes binding (PassThruOpen / Connect / ReadMsgs / WriteMsgs / StartMsgFilter / Ioctl ...).

``J2534Link`` speaks ISO 15765 (the device does ISO-TP and flow control; one flow-control filter per control
unit) and ISO 9141 / ISO 14230 K-line (5-baud or fast init through Ioctl). The DLL must match the bitness of
the IDE's Python: most vendors ship 32-bit DLLs only; ``devices()`` reports each one's bitness so the user is
told why a device cannot be used.
"""
from __future__ import annotations

import ctypes
import os
import struct
import time
from dataclasses import dataclass

from . import protocols
from .base import DiagLink, LinkError, Response

# ---- constants (J2534-1 v04.04)
J1850VPW, J1850PWM, ISO9141, ISO14230, CAN, ISO15765 = 1, 2, 3, 4, 5, 6
CAN_29BIT_ID, ISO9141_NO_CHECKSUM, CAN_ID_BOTH, ISO9141_K_LINE_ONLY = 0x100, 0x200, 0x800, 0x1000
ISO15765_FRAME_PAD, ISO15765_ADDR_TYPE = 0x40, 0x80
PASS_FILTER, BLOCK_FILTER, FLOW_CONTROL_FILTER = 1, 2, 3
GET_CONFIG, SET_CONFIG, READ_VBATT, FIVE_BAUD_INIT, FAST_INIT = 1, 2, 3, 4, 5
CLEAR_TX_BUFFER, CLEAR_RX_BUFFER, CLEAR_PERIODIC_MSGS, CLEAR_MSG_FILTERS = 7, 8, 9, 0xA
DATA_RATE, LOOPBACK, NODE_ADDRESS, P1_MAX, P3_MIN, P4_MIN = 0x01, 0x03, 0x04, 0x07, 0x0A, 0x0C
ISO15765_BS, ISO15765_STMIN = 0x1E, 0x1F
TX_MSG_TYPE, START_OF_MESSAGE, RX_BREAK, TX_DONE = 0x01, 0x02, 0x04, 0x08
ERR_TIMEOUT, ERR_BUFFER_EMPTY = 0x09, 0x10

ERRORS = {
    0x00: "STATUS_NOERROR", 0x01: "ERR_NOT_SUPPORTED", 0x02: "ERR_INVALID_CHANNEL_ID",
    0x03: "ERR_INVALID_PROTOCOL_ID", 0x04: "ERR_NULL_PARAMETER", 0x05: "ERR_INVALID_IOCTL_VALUE",
    0x06: "ERR_INVALID_FLAGS", 0x07: "ERR_FAILED", 0x08: "ERR_DEVICE_NOT_CONNECTED", 0x09: "ERR_TIMEOUT",
    0x0A: "ERR_INVALID_MSG", 0x0B: "ERR_INVALID_TIME_INTERVAL", 0x0C: "ERR_EXCEEDED_LIMIT",
    0x0D: "ERR_INVALID_MSG_ID", 0x0E: "ERR_DEVICE_IN_USE", 0x0F: "ERR_INVALID_IOCTL_ID", 0x10: "ERR_BUFFER_EMPTY",
    0x11: "ERR_BUFFER_FULL", 0x12: "ERR_BUFFER_OVERFLOW", 0x13: "ERR_PIN_INVALID", 0x14: "ERR_CHANNEL_IN_USE",
    0x15: "ERR_MSG_PROTOCOL_ID", 0x16: "ERR_INVALID_FILTER_ID", 0x17: "ERR_NO_FLOW_CONTROL", 0x18: "ERR_NOT_UNIQUE",
    0x19: "ERR_INVALID_BAUDRATE", 0x1A: "ERR_INVALID_DEVICE_ID",
}

ULONG = ctypes.c_ulong


class PASSTHRU_MSG(ctypes.Structure):
    _fields_ = [("ProtocolID", ULONG), ("RxStatus", ULONG), ("TxFlags", ULONG), ("Timestamp", ULONG),
                ("DataSize", ULONG), ("ExtraDataIndex", ULONG), ("Data", ctypes.c_ubyte * 4128)]


class SCONFIG(ctypes.Structure):
    _fields_ = [("Parameter", ULONG), ("Value", ULONG)]


class SCONFIG_LIST(ctypes.Structure):
    _fields_ = [("NumOfParams", ULONG), ("ConfigPtr", ctypes.POINTER(SCONFIG))]


class SBYTE_ARRAY(ctypes.Structure):
    _fields_ = [("NumOfBytes", ULONG), ("BytePtr", ctypes.POINTER(ctypes.c_ubyte))]


@dataclass
class J2534Device:
    name: str
    vendor: str
    library: str
    protocols: list
    key: str
    bits: int = 0                     # 32 / 64 from the DLL's PE header (0 = unknown)

    @property
    def dll(self) -> str:
        return self.library

    @property
    def usable(self) -> bool:
        return os.path.isfile(self.library) and self.bits in (0, struct.calcsize("P") * 8)

    @property
    def label(self) -> str:
        b = f", {self.bits}-bit" if self.bits else ""
        return f"{self.name} ({self.vendor}{b})"


def dll_bits(path: str) -> int:
    """32 or 64 from the PE header's machine field (0 when unreadable)."""
    try:
        with open(path, "rb") as f:
            head = f.read(4096)
        pe = struct.unpack_from("<I", head, 0x3C)[0]
        machine = struct.unpack_from("<H", head, pe + 4)[0]
        return {0x14C: 32, 0x8664: 64, 0xAA64: 64}.get(machine, 0)
    except (OSError, struct.error):
        return 0


def devices() -> list[J2534Device]:
    """Installed J2534 04.04 devices (HKLM\\SOFTWARE\\PassThruSupport.04.04, both registry views)."""
    if os.name != "nt":
        return []
    import winreg
    out, seen = [], set()
    for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
        try:
            root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\PassThruSupport.04.04", 0,
                                  winreg.KEY_READ | view)
        except OSError:
            continue
        with root:
            i = 0
            while True:
                try:
                    sub = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, sub) as k:
                        vals = {}
                        j = 0
                        while True:
                            try:
                                n, v, _t = winreg.EnumValue(k, j)
                            except OSError:
                                break
                            vals[n.lower()] = v
                            j += 1
                except OSError:
                    continue
                lib = str(vals.get("functionlibrary", ""))
                if not lib or lib.lower() in seen:
                    continue
                seen.add(lib.lower())
                protos = [p for p in ("CAN", "ISO15765", "ISO9141", "ISO14230", "J1850VPW", "J1850PWM", "SCI_A_ENGINE")
                          if vals.get(p.lower())]
                out.append(J2534Device(str(vals.get("name", sub)), str(vals.get("vendor", "")), lib, protos, sub,
                                       dll_bits(lib)))
    return out


def list_devices() -> list[J2534Device]:
    return devices()


class J2534Error(LinkError):
    pass


class PassThru:
    """The DLL's functions (stdcall). Every call raises J2534Error on a non-zero status (except time-outs
    / empty buffers in ReadMsgs, which return what arrived)."""

    def __init__(self, library: str):
        bits = struct.calcsize("P") * 8
        lb = dll_bits(library)
        if lb and lb != bits:
            raise J2534Error(
                f"{os.path.basename(library)} is a {lb}-bit DLL; RAD IDE runs {bits}-bit Python and cannot load it.",
                f"الملف {os.path.basename(library)} مكتبة {lb}-بت؛ RAD IDE يعمل ببايثون {bits}-بت ولا يستطيع تحميلها.",
                "bitness")
        try:
            self.dll = ctypes.WinDLL(library) if os.name == "nt" else ctypes.CDLL(library)
        except OSError as e:
            raise J2534Error(f"Cannot load {library}: {e}", f"تعذّر تحميل {library}: {e}", "load") from e
        P = ctypes.POINTER
        sig = {
            "PassThruOpen": [ctypes.c_void_p, P(ULONG)],
            "PassThruClose": [ULONG],
            "PassThruConnect": [ULONG, ULONG, ULONG, ULONG, P(ULONG)],
            "PassThruDisconnect": [ULONG],
            "PassThruReadMsgs": [ULONG, P(PASSTHRU_MSG), P(ULONG), ULONG],
            "PassThruWriteMsgs": [ULONG, P(PASSTHRU_MSG), P(ULONG), ULONG],
            "PassThruStartMsgFilter": [ULONG, ULONG, P(PASSTHRU_MSG), P(PASSTHRU_MSG), P(PASSTHRU_MSG), P(ULONG)],
            "PassThruStopMsgFilter": [ULONG, ULONG],
            "PassThruIoctl": [ULONG, ULONG, ctypes.c_void_p, ctypes.c_void_p],
            "PassThruReadVersion": [ULONG, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p],
            "PassThruGetLastError": [ctypes.c_char_p],
        }
        self.fn = {}
        for name, args in sig.items():
            f = getattr(self.dll, name, None)
            if f is None:
                if name in ("PassThruReadVersion", "PassThruGetLastError"):
                    continue
                raise J2534Error(f"{library} has no {name} export.", f"المكتبة {library} لا تصدّر {name}.", "load")
            f.argtypes, f.restype = args, ctypes.c_long
            self.fn[name] = f

    def last_error(self) -> str:
        f = self.fn.get("PassThruGetLastError")
        if f is None:
            return ""
        buf = ctypes.create_string_buffer(256)
        f(buf)
        return buf.value.decode("ascii", "replace")

    def check(self, name: str, rc: int, ok=(0,)) -> int:
        if rc not in ok:
            detail = self.last_error()
            raise J2534Error(f"{name}: {ERRORS.get(rc, rc)} {detail}".strip(),
                             f"{name}: {ERRORS.get(rc, rc)} {detail}".strip(), ERRORS.get(rc, "j2534").lower())
        return rc

    def call(self, name: str, *args, ok=(0,)) -> int:
        return self.check(name, self.fn[name](*args), ok)


def make_msg(protocol: int, data: bytes, tx_flags: int = 0) -> PASSTHRU_MSG:
    m = PASSTHRU_MSG()
    m.ProtocolID, m.TxFlags, m.DataSize = protocol, tx_flags, len(data)
    ctypes.memmove(m.Data, bytes(data), len(data))
    return m


def msg_bytes(m: PASSTHRU_MSG) -> bytes:
    return bytes(m.Data[:m.DataSize])


class J2534Link(DiagLink):
    kind = "j2534"
    channel = "j2534"

    def __init__(self, device: J2534Device | str, protocol: str = protocols.AUTO, log=None):
        super().__init__(log)
        self.device = device if isinstance(device, J2534Device) else J2534Device(
            os.path.basename(str(device)), "", str(device), [], "", dll_bits(str(device)))
        self.wanted = protocol or protocols.AUTO
        self.pt: PassThru | None = None
        self.dev_id = ULONG(0)
        self.chan = ULONG(0)
        self.filters: dict[int, int] = {}        # rx id -> filter id
        self.versions = ("", "", "")

    # ------------------------------------------------------------------ open / close
    def open(self) -> None:
        self.pt = PassThru(self.device.library)
        self.pt.call("PassThruOpen", None, ctypes.byref(self.dev_id))
        f = self.pt.fn.get("PassThruReadVersion")
        if f is not None:
            bufs = [ctypes.create_string_buffer(80) for _ in range(3)]
            if f(self.dev_id, *bufs) == 0:
                self.versions = tuple(b.value.decode("ascii", "replace") for b in bufs)
        self.adapter_info = f"{self.device.name} (fw {self.versions[0]})" if self.versions[0] else self.device.name
        self.log.info(self.channel, f"opened {self.adapter_info}, DLL {self.versions[1]}, API {self.versions[2]}")
        self.is_open = True
        order = protocols.DETECT_ORDER if self.wanted == protocols.AUTO else [self.wanted]
        last = None
        for code in order:
            p = protocols.get(code)
            if p is None or p.family == "j1850":
                continue
            try:
                self._connect(p)
                if self._request(b"\x01\x00", None, None, 0.5, None):
                    self.protocol = p
                    self.log.info(self.channel, f"protocol: {p.name}")
                    return
            except J2534Error as e:
                last = e
            self._disconnect()
        self.close()
        raise last or J2534Error("The car did not answer on any protocol. Is the ignition on?",
                                 "لم ترد السيارة على أي بروتوكول. هل الإشعال يعمل؟", "unable_to_connect")

    def _connect(self, p: protocols.Protocol) -> None:
        pt = self.pt
        self.protocol = p
        self.filters.clear()
        if p.is_can:
            flags = CAN_29BIT_ID if p.bits29 else 0
            pt.call("PassThruConnect", self.dev_id, ISO15765, flags, p.bitrate, ctypes.byref(self.chan))
            pt.call("PassThruIoctl", self.chan, CLEAR_MSG_FILTERS, None, None)
            if p.bits29:                             # OBD units answer from 18 DA F1 10..17
                for addr in range(0x10, 0x18):
                    self._add_filter(0x18DAF100 | addr, tx=protocols.phys_29(addr))
            else:
                for rx in range(0x7E8, 0x7F0):
                    self._add_filter(rx, tx=rx - 8)
        else:
            proto = ISO14230 if p.code in ("4", "5") else ISO9141
            pt.call("PassThruConnect", self.dev_id, proto, 0, 10400, ctypes.byref(self.chan))
            self._set_config({P4_MIN: 0, P3_MIN: 55})
            msk = make_msg(proto, b"\x00")
            pat = make_msg(proto, b"\x00")
            fid = ULONG(0)
            pt.call("PassThruStartMsgFilter", self.chan, PASS_FILTER, ctypes.byref(msk), ctypes.byref(pat), None,
                    ctypes.byref(fid))
            if p.code == "5":
                req = make_msg(proto, bytes([0xC1, 0x33, 0xF1, 0x81]))
                resp = PASSTHRU_MSG()
                pt.call("PassThruIoctl", self.chan, FAST_INIT, ctypes.byref(req), ctypes.byref(resp))
            else:
                addr = (ctypes.c_ubyte * 1)(0x33)
                inp = SBYTE_ARRAY(1, ctypes.cast(addr, ctypes.POINTER(ctypes.c_ubyte)))
                out_buf = (ctypes.c_ubyte * 2)()
                out = SBYTE_ARRAY(2, ctypes.cast(out_buf, ctypes.POINTER(ctypes.c_ubyte)))
                pt.call("PassThruIoctl", self.chan, FIVE_BAUD_INIT, ctypes.byref(inp), ctypes.byref(out))
        pt.call("PassThruIoctl", self.chan, CLEAR_RX_BUFFER, None, None)

    def _set_config(self, params: dict) -> None:
        arr = (SCONFIG * len(params))(*[SCONFIG(k, v) for k, v in params.items()])
        lst = SCONFIG_LIST(len(params), arr)
        self.pt.call("PassThruIoctl", self.chan, SET_CONFIG, ctypes.byref(lst), None)

    def _add_filter(self, rx: int, tx: int) -> None:
        """A flow-control filter: frames from *rx* are reassembled, flow control goes out on *tx*."""
        if rx in self.filters:
            return
        if len(self.filters) >= 10:                  # J2534 guarantees 10 filters per channel
            old = next(iter(self.filters))
            try:
                self.pt.call("PassThruStopMsgFilter", self.chan, self.filters.pop(old))
            except J2534Error:
                pass
        flags = CAN_29BIT_ID if (self.protocol and self.protocol.bits29) else 0
        m = make_msg(ISO15765, (0x1FFFFFFF if flags else 0x7FF).to_bytes(4, "big"), flags)
        p = make_msg(ISO15765, rx.to_bytes(4, "big"), flags)
        fc = make_msg(ISO15765, tx.to_bytes(4, "big"), flags | ISO15765_FRAME_PAD)
        fid = ULONG(0)
        self.pt.call("PassThruStartMsgFilter", self.chan, FLOW_CONTROL_FILTER, ctypes.byref(m), ctypes.byref(p),
                     ctypes.byref(fc), ctypes.byref(fid))
        self.filters[rx] = fid.value

    def _disconnect(self) -> None:
        if self.pt is not None and self.chan.value:
            try:
                self.pt.call("PassThruDisconnect", self.chan)
            except J2534Error:
                pass
            self.chan = ULONG(0)

    def close(self) -> None:
        if self.pt is not None:
            self._disconnect()
            try:
                self.pt.call("PassThruClose", self.dev_id)
            except J2534Error:
                pass
        self.pt = None
        self.is_open = False

    # ------------------------------------------------------------------ messages
    def _write(self, data: bytes, flags: int) -> None:
        proto = ISO15765 if self.protocol.is_can else (ISO14230 if self.protocol.code in ("4", "5") else ISO9141)
        m = make_msg(proto, data, flags)
        n = ULONG(1)
        self.log.tx(self.channel, data.hex(" ").upper())
        self.pt.call("PassThruWriteMsgs", self.chan, ctypes.byref(m), ctypes.byref(n), 1000)

    def _read(self, timeout: float, want_rx: int | None, functional: bool, expect: int | None) -> list[Response]:
        out: list[Response] = []
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            m = PASSTHRU_MSG()
            n = ULONG(1)
            rc = self.pt.fn["PassThruReadMsgs"](self.chan, ctypes.byref(m), ctypes.byref(n), 50)
            if rc not in (0, ERR_TIMEOUT, ERR_BUFFER_EMPTY):
                self.pt.check("PassThruReadMsgs", rc)
            if n.value == 0:
                continue
            if m.RxStatus & (TX_MSG_TYPE | START_OF_MESSAGE | TX_DONE):
                continue                              # echo / first-frame indication / tx confirmation
            b = msg_bytes(m)
            self.log.rx(self.channel, b.hex(" ").upper())
            if self.protocol.is_can:
                if len(b) < 5:
                    continue
                src, data = int.from_bytes(b[:4], "big"), b[4:]
                if want_rx is not None and src != want_rx:
                    continue
            else:
                if len(b) < 4:
                    continue
                if b[0] & 0x80 and b[0] & 0x3F:
                    src, data = b[2], b[3:3 + (b[0] & 0x3F)]
                else:
                    src, data = b[2], b[3:-1] if not (b[0] & 0x80) else b[3:]
            r = Response(src, bytes(data), [b])
            out.append(r)
            if r.is_pending:
                end = max(end, time.monotonic() + 5.0)
                continue
            if not functional and expect and len([o for o in out if not o.is_pending]) >= expect:
                break
        return out

    def _request(self, payload, tx_id, rx_id, timeout, expect):
        p = self.protocol
        if p.is_can:
            functional = tx_id is None
            tx = tx_id if tx_id is not None else (protocols.FUNC_29 if p.bits29 else protocols.FUNC_11)
            if not functional and rx_id is not None:
                self._add_filter(rx_id, tx)
            flags = (CAN_29BIT_ID if p.bits29 else 0) | ISO15765_FRAME_PAD
            self._write(tx.to_bytes(4, "big") + payload, flags)
            return self._read(timeout, rx_id, functional, expect or 1)
        functional = tx_id is None
        if p.code in ("4", "5"):
            hdr = bytes([0xC0 | len(payload), 0x33, 0xF1]) if functional else bytes([0x80 | len(payload), tx_id, 0xF1])
        else:
            hdr = bytes([0x68, 0x6A, 0xF1]) if functional else bytes([0x6C, tx_id, 0xF1])
        self._write(hdr + payload, 0)
        return self._read(timeout, None, functional, expect or 1)

    def listen(self, rx_id=None, timeout=2.0):
        with self.lock:
            return self._read(timeout, rx_id, False, 1)

    def voltage(self) -> float | None:
        if self.pt is None:
            return None
        v = ULONG(0)
        try:
            self.pt.call("PassThruIoctl", self.dev_id, READ_VBATT, None, ctypes.byref(v))
        except J2534Error:
            return None
        return v.value / 1000.0
