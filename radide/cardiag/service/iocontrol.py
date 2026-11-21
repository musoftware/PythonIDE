"""Actuator tests with InputOutputControlByIdentifier 0x2F (KWP2000: InputOutputControlByLocalIdentifier 0x30).

``ActuatorTest.run`` sets a state, keeps the session alive, lets the UI change the state while it runs, and -
whatever happens (end of the time limit, Stop, an error, cancel) - always sends *returnControlToECU*
(2F <did> 00 / 30 <lid> 00) so the control unit takes the actuator back.
"""
from __future__ import annotations

from . import definitions as D
from .runner import Result, ServiceBase
from .text import bi, bi_of
from .transport import Cancelled, ServiceError


class ActuatorTest(ServiceBase):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.next_value: bytes | None = None       # set from the UI thread to switch the state
        self.stop_requested = False
        self.active: dict | None = None

    def _req(self, io: dict, control: int, value: bytes = b"") -> bytes:
        kwp = self.ecu(io).protocol == "kwp"
        did = D.hexbytes(io["did"])
        if kwp:
            control = {0x03: 0x07}.get(control, control)     # KWP: 07 = shortTermAdjustment
            return bytes([0x30]) + did + bytes([control]) + value
        return bytes([0x2F]) + did + bytes([control]) + value

    def set_state(self, io: dict, value: bytes) -> bytes:
        ctl = int(D.hexbytes(io.get("control", "03"))[0])
        resp = self.client.request(self.ecu(io), self._req(io, ctl, value), note="io control")
        self.active = io
        return resp

    def release(self, io: dict) -> bool:
        """returnControlToECU; True when the control unit confirmed it."""
        try:
            self.client.request(self.ecu(io), self._req(io, 0x00), note="return control to ECU")
            self.emit("log", bi("Control returned to the control unit.", "أُعيد التحكم إلى وحدة التحكم."))
            self.active = None
            return True
        except ServiceError as e:
            self.emit("warning", bi("Return control failed: ", "فشلت إعادة التحكم: ") + e.text)
            return False

    def run(self, io: dict, value, confirmed=(), *, duration_s: float | None = None, enforce_checks: bool = True) \
            -> Result:
        value = D.hexbytes(value)
        ecu = self.ecu(io)
        limit = min(float(duration_s or io.get("max_duration_s", 30)), float(io.get("max_duration_s", 30)))
        self.client.context = {"action": "io_control", "id": io["id"]}
        engaged = False
        released = None
        try:
            self.require(io, confirmed, enforce_checks=enforce_checks)
            self.prepare(io)
            self.set_state(io, value)
            engaged = True
            label = self._label(io, value)
            self.emit("status", bi("Active: ", "يعمل: ") + label, progress=0, value=value.hex())
            clock, sleep = self.client.clock, self.client.sleep
            t0 = last_tp = clock()
            while True:
                self.client.check_cancel()
                if self.stop_requested:
                    break
                el = clock() - t0
                if el >= limit:
                    self.emit("log", bi(f"Time limit reached ({limit:g} s).", f"انتهى الحد الزمني ({limit:g} ثانية)."))
                    break
                if self.next_value is not None:
                    value, self.next_value = self.next_value, None
                    self.set_state(io, value)
                    self.emit("status", bi("Active: ", "يعمل: ") + self._label(io, value), value=value.hex())
                if clock() - last_tp >= 2.0:
                    self.client.tester_present(ecu)
                    last_tp = clock()
                self.emit("progress", bi("Active", "يعمل"), progress=int(el * 100 / limit))
                sleep(0.2)
            released = self.release(io)
            engaged = False
            done = bi("Test finished, control returned to the ECU.", "انتهى الاختبار وأُعيد التحكم إلى وحدة التحكم.")
            self.emit("status", done, progress=100)
            return Result(True, done, 100, data={"released": released})
        except Cancelled as e:
            return Result(False, e.text, error=e, data={"released": released})
        except ServiceError as e:
            self.emit("status", e.text)
            return Result(False, e.text, error=e, data={"released": released})
        finally:
            if engaged:
                released = self.release(io)
            self.client.back_to_default(ecu)
            self.client.context = {}

    def _label(self, io: dict, value: bytes):
        for st in io.get("states") or []:
            if D.hexbytes(st.get("value")) == value:
                return bi_of(st, "label")
        return bi(value.hex(" ").upper(), value.hex(" ").upper())
