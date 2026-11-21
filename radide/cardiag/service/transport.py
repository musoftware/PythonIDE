"""The diagnostic channel the service functions talk through.

A *transport* sends one UDS / KWP2000 request to one control unit and returns the raw answer bytes. Anything
with one of these shapes is accepted (``as_transport``):

* ``exchange(request: bytes, tx: int, rx: int, timeout: float) -> bytes`` (the Demo car, radide/cardiag/service/
  demo_ecu.py) - optionally ``receive(tx, rx, timeout) -> bytes`` to collect the next answer after a
  "response pending" (7F xx 78);
* ``request(request, tx=..., rx=..., timeout=...)`` / ``send_request(...)`` (the connection layer's UDS client);
* a plain callable ``f(request, tx, rx, timeout)``.

``ServiceClient`` adds what every service function needs on top: positive / negative response checking with
Arabic explanations (nrc.py), response-pending handling, diagnostic sessions, tester present, security access
through a user-selected plug-in (security.py) and an audit hook that sees every request and answer.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .nrc import explain, nrc_name
from .text import BiText

SESSIONS_UDS = {"default": 0x01, "programming": 0x02, "extended": 0x03, "safety": 0x04}
SESSIONS_KWP = {"default": 0x81, "programming": 0x85, "extended": 0x89}


class ServiceError(Exception):
    """A service function failed; ``text`` is a BiText (English / Arabic)."""

    def __init__(self, text, *, code: str = "error"):
        self.text = text if isinstance(text, BiText) else BiText(str(text), "")
        self.code = code
        super().__init__(self.text.en)

    def __str__(self) -> str:
        return str(self.text)


class NegativeResponse(ServiceError):
    def __init__(self, sid: int, nrc: int, request: bytes = b""):
        self.sid, self.nrc, self.request = sid, nrc, request
        super().__init__(explain(nrc), code=f"nrc_{nrc:02x}")

    @property
    def name(self) -> str:
        return nrc_name(self.nrc)


class NoResponse(ServiceError):
    def __init__(self, request: bytes = b""):
        self.request = request
        super().__init__(BiText("The control unit did not answer (timeout). Check the ignition and the adapter.",
                                "لم ترد وحدة التحكم (انتهت المهلة). تأكد من تشغيل الإشعال ومن المحوّل."),
                         code="timeout")


class Cancelled(ServiceError):
    def __init__(self):
        super().__init__(BiText("Cancelled by the user.", "ألغاها المستخدم."), code="cancelled")


@dataclass
class Ecu:
    """One control unit: physical request / response CAN ids (11- or 29-bit) and the protocol."""
    key: str
    name: str = ""
    name_ar: str = ""
    tx: int = 0x7E0
    rx: int = 0x7E8
    protocol: str = "uds"            # "uds" or "kwp"
    extra: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{self.name or self.key} ({self.tx:03X}/{self.rx:03X})"


def as_transport(obj):
    """Wrap *obj* (see the module docstring) into a callable ``f(req, tx, rx, timeout) -> bytes``."""
    if obj is None:
        raise ServiceError(BiText("No connection. Choose the Demo car or connect an adapter first.",
                                  "لا يوجد اتصال. اختر السيارة التجريبية أو وصّل محولًا أولًا."), code="no_connection")
    for name in ("exchange", "request", "send_request", "uds_request"):
        fn = getattr(obj, name, None)
        if callable(fn):
            def call(req, tx, rx, timeout, _fn=fn):
                try:
                    return _fn(req, tx=tx, rx=rx, timeout=timeout)
                except TypeError:
                    return _fn(req)
            return call
    if callable(obj):
        return obj
    raise ServiceError(BiText(f"Unsupported connection object: {type(obj).__name__}",
                              f"كائن اتصال غير مدعوم: {type(obj).__name__}"), code="no_connection")


class ServiceClient:
    """Request / response with checking, sessions, tester present and security access."""

    def __init__(self, transport, *, audit=None, sleep=time.sleep, clock=time.monotonic, p2_star: float = 5.0):
        self.raw = transport
        self._send = as_transport(transport)
        self._receive = getattr(transport, "receive", None)
        self.audit = audit                  # callable(dict) for every request / answer
        self.sleep = sleep
        self.clock = clock
        self.p2_star = p2_star
        self.cancelled = False
        self.sessions: dict[str, int] = {}  # ecu key -> active session byte (as far as we know)
        self.unlocked: dict[str, int] = {}  # ecu key -> unlocked security level
        self.context: dict = {}             # added to every audit entry (action, definition id, VIN ...)

    # ------------------------------------------------------------------ basics
    def _log(self, ecu: Ecu, req: bytes, resp: bytes | None, error: str = "", note: str = "") -> None:
        if self.audit is None:
            return
        entry = {"ecu": ecu.key, "tx": f"{ecu.tx:03X}", "rx": f"{ecu.rx:03X}", "request": req.hex(" ").upper(),
                 "response": resp.hex(" ").upper() if resp is not None else "", "error": error}
        if note:
            entry["note"] = note
        entry.update(self.context)
        try:
            self.audit(entry)
        except Exception:  # noqa: BLE001 - the audit log must never break a running function
            pass

    def check_cancel(self) -> None:
        if self.cancelled:
            raise Cancelled()

    def request(self, ecu: Ecu, req: bytes, timeout: float = 2.0, note: str = "") -> bytes:
        """Send *req*; return the positive answer or raise NegativeResponse / NoResponse."""
        req = bytes(req)
        try:
            resp = self._send(req, ecu.tx, ecu.rx, timeout)
        except ServiceError:
            raise
        except TimeoutError:
            resp = None
        except Exception as e:  # noqa: BLE001 - the adapter's own errors become a readable message
            if type(e).__name__ in ("NoResponse", "Timeout") or getattr(e, "code", "") in ("timeout", "no_response"):
                self._log(ecu, req, None, error="timeout", note=note)
                raise NoResponse(req) from e
            self._log(ecu, req, None, error=str(e), note=note)
            raise ServiceError(BiText(f"Connection error: {e}", f"خطأ في الاتصال: {e}"), code="link") from e
        deadline = self.clock() + self.p2_star
        while resp and len(resp) >= 3 and resp[0] == 0x7F and resp[2] == 0x78:
            self._log(ecu, req, bytes(resp), note="response pending")
            if self._receive is None or self.clock() > deadline:
                resp = None
                break
            try:
                resp = self._receive(tx=ecu.tx, rx=ecu.rx, timeout=timeout)
            except TimeoutError:
                resp = None
        if not resp:
            self._log(ecu, req, None, error="timeout", note=note)
            raise NoResponse(req)
        resp = bytes(resp)
        if resp[0] == 0x7F:
            nrc = resp[2] if len(resp) > 2 else 0x10
            self._log(ecu, req, resp, error=f"NRC 0x{nrc:02X} {nrc_name(nrc)}", note=note)
            raise NegativeResponse(req[0], nrc, req)
        if resp[0] != (req[0] + 0x40) & 0xFF:
            self._log(ecu, req, resp, error="unexpected answer", note=note)
            raise ServiceError(BiText(f"Unexpected answer {resp.hex(' ').upper()} to {req.hex(' ').upper()}",
                                      f"رد غير متوقع {resp.hex(' ').upper()} على {req.hex(' ').upper()}"),
                               code="unexpected")
        self._log(ecu, req, resp, note=note)
        return resp

    # ------------------------------------------------------------------ sessions / tester present
    def session(self, ecu: Ecu, session) -> None:
        """Enter a diagnostic session ("default" / "extended" / a number)."""
        if session in (None, "", 0):
            return
        table = SESSIONS_KWP if ecu.protocol == "kwp" else SESSIONS_UDS
        code = table.get(str(session).lower()) if isinstance(session, str) else int(session)
        if code is None:
            try:
                code = int(str(session), 0)
            except ValueError:
                raise ServiceError(BiText(f"Unknown diagnostic session: {session}",
                                          f"جلسة تشخيص غير معروفة: {session}"), code="definition") from None
        if self.sessions.get(ecu.key) == code:
            return
        self.request(ecu, bytes([0x10, code]), note="session")
        self.sessions[ecu.key] = code
        if code in (0x01, 0x81):
            self.unlocked.pop(ecu.key, None)

    def tester_present(self, ecu: Ecu) -> None:
        try:
            self.request(ecu, b"\x3E\x00", timeout=1.0, note="tester present")
        except ServiceError:
            pass

    def back_to_default(self, ecu: Ecu) -> None:
        if self.sessions.get(ecu.key) not in (None, 0x01, 0x81):
            try:
                self.session(ecu, "default")
            except ServiceError:
                pass

    # ------------------------------------------------------------------ security access (plug-in only)
    def security_access(self, ecu: Ecu, level: int, plugin) -> None:
        """SecurityAccess 0x27 with a user-selected seed/key plug-in (security.SeedKeyPlugin). RAD IDE contains
        no seed/key algorithms: without a plug-in the function stops with a readable message."""
        if not level:
            return
        if self.unlocked.get(ecu.key) == level:
            return
        if plugin is None:
            raise ServiceError(BiText(
                "This function needs security access (0x27). Select a seed/key plug-in you are licensed to use "
                "for this control unit (Service Functions > Security Access Plug-in). RAD IDE includes no "
                "security algorithms.",
                "هذه الوظيفة تحتاج إلى وصول أمني (0x27). اختر إضافة seed/key مرخّصًا لك باستخدامها لهذه الوحدة "
                "(وظائف الخدمة > إضافة الوصول الأمني). لا يحتوي RAD IDE على أي خوارزميات أمان."), code="security")
        odd = level if level % 2 else level - 1
        seed_resp = self.request(ecu, bytes([0x27, odd]), note="security seed")
        seed = seed_resp[2:]
        if seed and not any(seed):
            self.unlocked[ecu.key] = level          # all-zero seed: already unlocked
            return
        key = plugin.compute_key(seed, odd, ecu)
        self.request(ecu, bytes([0x27, odd + 1]) + bytes(key), note="security key")
        self.unlocked[ecu.key] = level
