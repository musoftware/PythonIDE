"""Service resets, adaptation values and feature coding with WriteDataByIdentifier 0x2E (definitions from the
pack only). The old value is read first and kept in the audit log; the new value is read back afterwards."""
from __future__ import annotations

from . import definitions as D
from .runner import Result, ServiceBase
from .text import BiText, bi, bi_of
from .transport import ServiceError


def fields_of(adapt: dict) -> list[dict]:
    inp = adapt.get("input") or {}
    if "fields" in inp:
        return list(inp["fields"])
    return [inp] if inp else []


def encode_input(adapt: dict, values: list) -> bytes:
    """The bytes to write for *values* (one per input field): ints are range-checked, enums looked up."""
    if "value" in adapt and not adapt.get("input"):
        return D.hexbytes(adapt["value"])
    out = bytearray()
    fields = fields_of(adapt)
    if len(values) != len(fields):
        raise ServiceError(bi(f"Expected {len(fields)} value(s).", f"المتوقع {len(fields)} قيمة."), code="input")
    for f, v in zip(fields, values):
        n = int(f.get("bytes", 1))
        name = bi_of(f, "name")
        t = f.get("type", "int")
        if t == "enum":
            opts = {D.hexbytes(o["value"]) for o in f.get("options") or []}
            b = D.hexbytes(v) if not isinstance(v, int) else v.to_bytes(n, "big")
            if b not in opts:
                raise ServiceError(name + bi(": not one of the allowed options", ": ليست من الخيارات المسموح بها"),
                                   code="input")
            out += b.rjust(n, b"\0")
        elif t == "hex":
            b = D.hexbytes(v)
            if len(b) != n:
                raise ServiceError(name + bi(f": needs {n} byte(s)", f": يحتاج إلى {n} بايت"), code="input")
            out += b
        elif t == "ascii":
            b = str(v).encode("ascii", "strict")[:n].ljust(n, b" ")
            out += b
        else:
            try:
                num = float(v)
            except (TypeError, ValueError):
                raise ServiceError(name + bi(": not a number", ": ليست رقمًا"), code="input") from None
            lo, hi = f.get("min"), f.get("max")
            if (lo is not None and num < float(lo)) or (hi is not None and num > float(hi)):
                raise ServiceError(name + bi(f": must be between {lo} and {hi}", f": يجب أن تكون بين {lo} و {hi}"),
                                   code="input")
            raw = round((num - float(f.get("offset", 0))) / float(f.get("scale", 1)))
            try:
                out += int(raw).to_bytes(n, "big", signed=bool(f.get("signed")))
            except OverflowError:
                raise ServiceError(name + bi(": too large", ": كبيرة جدًا"), code="input") from None
    return bytes(out)


class AdaptationWriter(ServiceBase):
    def write(self, adapt: dict, values: list | None = None, confirmed=(), *, enforce_checks: bool = True) -> Result:
        ecu = self.ecu(adapt)
        did = D.ident(adapt["did"])
        self.client.context = {"action": "adaptation", "id": adapt["id"]}
        try:
            data = encode_input(adapt, values or [])
            self.require(adapt, confirmed, enforce_checks=enforce_checks)
            self.prepare(adapt)
            old = None
            try:
                old, _, _ = self.read_did(ecu, did)
                self.emit("log", bi(f"Old value: {old.hex(' ').upper()}", f"القيمة القديمة: {old.hex(' ').upper()}"),
                          old=old.hex())
            except ServiceError:
                self.emit("log", bi("The old value could not be read.", "تعذّرت قراءة القيمة القديمة."))
            self.client.request(ecu, bytes([0x2E, did >> 8, did & 0xFF]) + data, note="write DID")
            self.emit("log", bi(f"Written: {data.hex(' ').upper()}", f"كُتبت: {data.hex(' ').upper()}"))
            mode = adapt.get("read_back", True)
            new = None
            verified = None
            if mode:
                new, value, info = self.read_did(ecu, did)
                shown = D.format_value(info or {}, value)
                if mode in (True, "compare"):
                    verified = new[:len(data)] == data
                    if not verified:
                        raise ServiceError(bi(f"Read back {new.hex(' ').upper()} differs from the written value.",
                                              f"القيمة المقروءة {new.hex(' ').upper()} تختلف عن القيمة المكتوبة."),
                                           code="verify")
                self.emit("result", bi(f"New value: {shown}", f"القيمة الجديدة: {shown}"))
            done = bi("Done.", "تم.")
            self.emit("status", done, progress=100)
            return Result(True, done, 100, data={"old": old.hex() if old else "", "written": data.hex(),
                                                 "new": new.hex() if new else "", "verified": verified})
        except ServiceError as e:
            self.emit("status", e.text)
            return Result(False, e.text, error=e)
        finally:
            self.client.back_to_default(ecu)
            self.client.context = {}


def describe_field(f: dict) -> BiText:
    t = f.get("type", "int")
    if t == "int":
        rng = f" ({f.get('min', '')}..{f.get('max', '')} {f.get('unit', '')})".rstrip()
        return bi_of(f, "name") + rng
    return bi_of(f, "name")
