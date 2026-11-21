"""KWP2000 services of the Demo car's engine unit when the car runs the K-line (ISO 14230) variant.
Returns None for services UDS handles the same way (0x3E, 0x27, 0x2F ...)."""
from __future__ import annotations

from .ecus import BAD_LENGTH, OUT_OF_RANGE, SERVICE_NOT_SUPPORTED, SUBFUNCTION_NOT_SUPPORTED

IDENT = {0x90: lambda e: e.car.vin.encode(), 0x87: lambda e: b"RAD-SIM-1000", 0x88: lambda e: b"SW 0042",
         0x8A: lambda e: b"RAD IDE Demo", 0x8C: lambda e: b"SN000001", 0x91: lambda e: b"HW 07",
         0x94: lambda e: b"SIM-ENG 1.4", 0x97: lambda e: b"ENGINE"}


def handle_kwp(ecu, req: bytes):
    sid = req[0]
    neg = ecu.neg
    if sid == 0x10:
        if len(req) != 2:
            return neg(0x10, BAD_LENGTH)
        if req[1] not in (0x81, 0x89):
            return neg(0x10, SUBFUNCTION_NOT_SUPPORTED)
        ecu.session = 0x01 if req[1] == 0x81 else 0x03
        return [(0.0, bytes([0x50, req[1]]))]
    if sid == 0x3E:
        return [] if len(req) > 1 and req[1] == 0x02 else [(0.0, b"\x7E")]
    if sid == 0x1A:
        opt = req[1] if len(req) > 1 else 0x80
        if opt == 0x80:
            data = b"".join(IDENT[k](ecu).ljust(12)[:12] for k in (0x87, 0x88, 0x94))
            return [(0.0, bytes([0x5A, 0x80]) + data)]
        f = IDENT.get(opt)
        return neg(0x1A, OUT_OF_RANGE) if f is None else [(0.0, bytes([0x5A, opt]) + f(ecu))]
    if sid == 0x18:
        if len(req) != 4:
            return neg(0x18, BAD_LENGTH)
        items = []
        for d in ecu.dtcs:
            if not d.visible:
                continue
            state = (2 if d.status & 0x01 else 1) << 5
            items.append(d.sae.to_bytes(2, "big") + bytes([state | (0x80 if d.status & 0x80 else 0)]))
        return [(0.0, bytes([0x58, len(items)]) + b"".join(items))]
    if sid == 0x14:
        if len(req) != 3:
            return neg(0x14, BAD_LENGTH)
        group = int.from_bytes(req[1:3], "big")
        ecu.clear(0xFFFFFF if group in (0xFF00, 0x0000) else group << 8)
        ecu.car.on_dtcs_cleared(ecu)
        return [(0.0, bytes([0x54]) + req[1:3])]
    if sid == 0x21:
        lid = req[1] if len(req) > 1 else 0
        f = ecu.kwp_local.get(lid)
        return neg(0x21, OUT_OF_RANGE) if f is None else [(0.0, bytes([0x61, lid]) + f())]
    if sid in (0x31, 0x32, 0x33):
        lid = req[1] if len(req) > 1 else 0
        rid = ecu.kwp_routines.get(lid)
        if rid is None:
            return neg(sid, OUT_OF_RANGE)
        sub = {0x31: 1, 0x32: 2, 0x33: 3}[sid]
        got = ecu._s31(bytes([0x31, sub]) + rid.to_bytes(2, "big") + bytes(req[2:]))
        out = []
        for delay, ans in got:
            if ans[0] == 0x7F:
                out.append((delay, bytes([0x7F, sid, ans[2]])))
            else:
                out.append((delay, bytes([sid + 0x40, lid]) + ans[4:]))
        return out
    if sid in (0x19, 0x2E):
        return neg(sid, SERVICE_NOT_SUPPORTED)
    return None
