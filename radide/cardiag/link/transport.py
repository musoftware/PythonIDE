"""Byte transports for ELM327-compatible adapters: serial / USB / Bluetooth SPP COM ports (pyserial), Wi-Fi
(TCP, 192.168.0.10:35000 by default), Bluetooth LE (bleak, optional) and an in-process loopback to the Demo car.

Every transport offers ``write(bytes)``, ``read_until(b">", timeout) -> bytes`` (everything received up to and
including the prompt; what arrived so far on time-out) and ``close()``.
"""
from __future__ import annotations

import socket
import threading
import time

from .base import LinkError

WIFI_HOST, WIFI_PORT = "192.168.0.10", 35000
AUTO_BAUDS = [38400, 115200, 9600, 230400, 57600, 500000, 19200]


class Transport:
    name = "transport"

    def write(self, data: bytes) -> None:
        raise NotImplementedError

    def read_available(self, timeout: float) -> bytes:
        """Whatever arrives within *timeout* (at least one byte if any arrives)."""
        raise NotImplementedError

    def read_until(self, terminator: bytes = b">", timeout: float = 2.0) -> bytes:
        buf = bytearray()
        end = time.monotonic() + timeout
        while True:
            left = end - time.monotonic()
            if left <= 0:
                break
            chunk = self.read_available(min(left, 0.05))
            if chunk:
                buf += chunk
                if terminator in chunk or buf.endswith(terminator):
                    break
        return bytes(buf)

    def flush_input(self) -> None:
        while self.read_available(0.01):
            pass

    def close(self) -> None:
        pass

    def describe(self) -> str:
        return self.name


class SerialTransport(Transport):
    """A COM port (USB cable adapters, Bluetooth classic SPP pairs appear as COM ports too). *url* may also be a
    pyserial URL such as ``socket://127.0.0.1:35000`` (the Demo car server) or ``rfc2217://``."""
    name = "serial"

    def __init__(self, port: str, baud: int = 38400):
        try:
            import serial  # pyserial
        except ImportError as e:
            raise LinkError("pyserial is not installed (pip install pyserial).",
                            "مكتبة pyserial غير مثبتة (pip install pyserial).", "missing_dep") from e
        self.port, self.baud = port, baud
        try:
            if "://" in port:
                self.ser = serial.serial_for_url(port, baudrate=baud, timeout=0.05, write_timeout=2)
            else:
                self.ser = serial.Serial(port, baudrate=baud, timeout=0.05, write_timeout=2)
        except Exception as e:  # noqa: BLE001 - SerialException / OSError / ValueError
            raise LinkError(f"Cannot open {port}: {e}", f"تعذّر فتح المنفذ {port}: {e}", "open_failed") from e

    def write(self, data: bytes) -> None:
        try:
            self.ser.write(data)
            self.ser.flush()
        except Exception as e:  # noqa: BLE001
            raise LinkError(f"Write to {self.port} failed: {e}", f"فشلت الكتابة إلى {self.port}: {e}",
                            "io") from e

    def read_available(self, timeout: float) -> bytes:
        try:
            self.ser.timeout = max(0.001, timeout)
            first = self.ser.read(1)
            if not first:
                return b""
            n = self.ser.in_waiting
            return first + (self.ser.read(n) if n else b"")
        except Exception as e:  # noqa: BLE001
            raise LinkError(f"Read from {self.port} failed: {e}", f"فشلت القراءة من {self.port}: {e}", "io") from e

    def set_baud(self, baud: int) -> None:
        self.baud = baud
        try:
            self.ser.baudrate = baud
        except Exception:  # noqa: BLE001 - socket:// URLs have no baud rate
            pass

    def close(self) -> None:
        try:
            self.ser.close()
        except Exception:  # noqa: BLE001
            pass

    def describe(self) -> str:
        return f"{self.port} @ {self.baud}"


class TcpTransport(Transport):
    """Wi-Fi ELM327 adapters (and the Demo car server): a plain TCP stream."""
    name = "tcp"

    def __init__(self, host: str = WIFI_HOST, port: int = WIFI_PORT, connect_timeout: float = 4.0):
        self.host, self.port = host, int(port)
        try:
            self.sock = socket.create_connection((host, self.port), timeout=connect_timeout)
        except OSError as e:
            raise LinkError(
                f"Cannot reach {host}:{port} ({e}). Join the adapter's Wi-Fi network first.",
                f"تعذّر الوصول إلى {host}:{port} ({e}). اتصل بشبكة الواي فاي الخاصة بالمحوّل أولًا.",
                "open_failed") from e
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def write(self, data: bytes) -> None:
        try:
            self.sock.sendall(data)
        except OSError as e:
            raise LinkError(f"Send failed: {e}", f"فشل الإرسال: {e}", "io") from e

    def read_available(self, timeout: float) -> bytes:
        self.sock.settimeout(max(0.001, timeout))
        try:
            data = self.sock.recv(4096)
        except socket.timeout:
            return b""
        except OSError as e:
            raise LinkError(f"Receive failed: {e}", f"فشل الاستقبال: {e}", "io") from e
        if data == b"":
            raise LinkError("The adapter closed the connection.", "أغلق المحوّل الاتصال.", "closed")
        return data

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def describe(self) -> str:
        return f"tcp://{self.host}:{self.port}"


class LoopbackTransport(Transport):
    """In-process connection to a byte-stream device such as the Demo car's ELM327 interpreter
    (radide/cardiag/sim/elm.py: ``feed(bytes)`` and ``read(timeout) -> bytes``)."""
    name = "demo"

    def __init__(self, device):
        self.device = device

    def write(self, data: bytes) -> None:
        self.device.feed(data)

    def read_available(self, timeout: float) -> bytes:
        return self.device.read(timeout)

    def describe(self) -> str:
        return "Demo car (in-process)"


# ===================================================================== Bluetooth LE (optional)
# (service, notify characteristic, write characteristic) used by common BLE OBD adapters
BLE_PROFILES = [
    ("0000fff0-0000-1000-8000-00805f9b34fb", "0000fff1-0000-1000-8000-00805f9b34fb",
     "0000fff2-0000-1000-8000-00805f9b34fb"),          # Vgate iCar Pro BLE, many ELM327 BLE clones
    ("0000ffe0-0000-1000-8000-00805f9b34fb", "0000ffe1-0000-1000-8000-00805f9b34fb",
     "0000ffe1-0000-1000-8000-00805f9b34fb"),          # HM-10 style modules
    ("000018f0-0000-1000-8000-00805f9b34fb", "00002af0-0000-1000-8000-00805f9b34fb",
     "00002af1-0000-1000-8000-00805f9b34fb"),          # OBDLink CX / several newer adapters
    ("e7810a71-73ae-499d-8c15-faa9aef0c3f2", "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f",
     "bef8d6c9-9c21-4c9e-b632-bd58c1009f9f"),          # Vlinker / Konnwei BLE
]
BLE_NAME_HINTS = ("OBD", "ELM", "VLINK", "V-LINK", "ICAR", "VEEPEAK", "KONNWEI", "OBDLINK", "CARISTA", "IOS-VLINK")


def ble_available() -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec("bleak") is not None
    except (ImportError, ValueError):
        return False


class _AsyncThread:
    """One asyncio loop in a daemon thread for bleak (its API is async)."""
    _inst = None

    def __init__(self):
        import asyncio
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, name="radide-ble", daemon=True)
        self.thread.start()

    @classmethod
    def get(cls) -> "_AsyncThread":
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    def run(self, coro, timeout: float):
        import asyncio
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)


def ble_scan(timeout: float = 5.0) -> list[tuple[str, str]]:
    """(address, name) of nearby BLE devices that look like OBD adapters (all named devices when none match)."""
    if not ble_available():
        raise LinkError("Bluetooth LE needs the bleak package (pip install bleak).",
                        "البلوتوث منخفض الطاقة يحتاج حزمة bleak (pip install bleak).", "missing_dep")
    from bleak import BleakScanner

    async def scan():
        return await BleakScanner.discover(timeout=timeout)
    try:
        devices = _AsyncThread.get().run(scan(), timeout + 5)
    except Exception as e:  # noqa: BLE001 - no adapter / Bluetooth off
        raise LinkError(f"Bluetooth scan failed: {e}", f"فشل البحث عن أجهزة البلوتوث: {e}", "ble") from e
    named = [(d.address, d.name or "") for d in devices if d.name]
    obd = [d for d in named if any(h in d[1].upper() for h in BLE_NAME_HINTS)]
    return obd or named


class BleTransport(Transport):
    name = "ble"

    def __init__(self, address: str, connect_timeout: float = 15.0):
        if not ble_available():
            raise LinkError("Bluetooth LE needs the bleak package (pip install bleak).",
                            "البلوتوث منخفض الطاقة يحتاج حزمة bleak (pip install bleak).", "missing_dep")
        from bleak import BleakClient
        self.address = address
        self.rx = bytearray()
        self.cond = threading.Condition()
        self.client = BleakClient(address)
        self.loop = _AsyncThread.get()
        self.write_char = None

        def on_notify(_handle, data: bytearray):
            with self.cond:
                self.rx += data
                self.cond.notify_all()

        async def connect():
            await self.client.connect(timeout=connect_timeout)
            services = self.client.services
            uuids = {str(s.uuid).lower(): s for s in services}
            for svc, notify, write in BLE_PROFILES:
                if svc in uuids:
                    await self.client.start_notify(notify, on_notify)
                    return write
            for s in services:                         # any service with a notify + a write characteristic
                n = next((c for c in s.characteristics if "notify" in c.properties), None)
                w = next((c for c in s.characteristics
                          if "write" in c.properties or "write-without-response" in c.properties), None)
                if n is not None and w is not None:
                    await self.client.start_notify(n, on_notify)
                    return w
            raise RuntimeError("no serial-like service found")
        try:
            self.write_char = self.loop.run(connect(), connect_timeout + 5)
        except Exception as e:  # noqa: BLE001
            raise LinkError(f"Bluetooth LE connection to {address} failed: {e}",
                            f"فشل الاتصال عبر البلوتوث منخفض الطاقة بالجهاز {address}: {e}", "open_failed") from e

    def write(self, data: bytes) -> None:
        async def w():
            for i in range(0, len(data), 20):          # default ATT MTU payload
                await self.client.write_gatt_char(self.write_char, data[i:i + 20], response=False)
        try:
            self.loop.run(w(), 5)
        except Exception as e:  # noqa: BLE001
            raise LinkError(f"Bluetooth write failed: {e}", f"فشلت الكتابة عبر البلوتوث: {e}", "io") from e

    def read_available(self, timeout: float) -> bytes:
        with self.cond:
            if not self.rx:
                self.cond.wait(timeout)
            data, self.rx = bytes(self.rx), bytearray()
        return data

    def close(self) -> None:
        async def c():
            await self.client.disconnect()
        try:
            self.loop.run(c(), 5)
        except Exception:  # noqa: BLE001
            pass

    def describe(self) -> str:
        return f"BLE {self.address}"
