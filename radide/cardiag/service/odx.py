"""Read-only import of the service subset of ASAM MCD-2D (ODX 2.x) files and PDX packages.

From every BASE-VARIANT / ECU-VARIANT the importer takes the DIAG-SERVICEs whose request is made of constant
parameters (CODED-CONST) and turns them into pack entries:

* 31 01 <RID> [constant params]  -> routine (start; result polling must be added by hand if needed)
* 2F <DID> 03 <constant value>   -> actuator test state (grouped per DID)
* 2E <DID> <constant data>       -> adaptation with a fixed value
* 22 <DID>                       -> data identifier (shown as hex)

CAN ids come from the layer's COMPARAM-REFs (CP_CanPhysReqId / CP_CanRespUSDTId) when present. Services the
policy does not allow (immobiliser, odometer, emissions-defeat ...) are skipped with a warning. Nothing is
written back to the ODX data. The result is an ordinary pack that is validated like a JSON pack.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from . import definitions as D
from .text import BiText


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        el.tag = _local(el.tag)
        for k in list(el.attrib):
            if "}" in k:
                el.attrib[_local(k)] = el.attrib.pop(k)
    return root


def _text(el, path: str, default: str = "") -> str:
    if el is None:
        return default
    x = el.find(path)
    return (x.text or "").strip() if x is not None and x.text else default


def _coded_value(txt: str) -> int:
    t = txt.strip()
    return int(t, 16) if t.lower().startswith("0x") else int(t)


def _request_bytes(req: ET.Element) -> tuple[bytes, bool]:
    """(constant prefix bytes, all parameters constant)."""
    params = []
    all_const = True
    for p in req.iter("PARAM"):
        ptype = p.get("type", "")
        pos = _text(p, "BYTE-POSITION")
        if not pos:
            all_const = False
            continue
        if ptype != "CODED-CONST":
            all_const = False
            params.append((int(pos), None, 0))
            continue
        bits = int(_text(p, "DIAG-CODED-TYPE/BIT-LENGTH", "8") or 8)
        try:
            val = _coded_value(_text(p, "CODED-VALUE", "0"))
        except ValueError:
            all_const = False
            continue
        params.append((int(pos), val, max(1, bits // 8)))
    params.sort(key=lambda t: t[0])
    out = bytearray()
    for pos, val, n in params:
        if val is None or pos != len(out):
            all_const = False
            break
        out += val.to_bytes(n, "big")
    return bytes(out), all_const


def _comparam(layer: ET.Element, *needles: str) -> int | None:
    for ref in layer.iter("COMPARAM-REF"):
        idr = ref.get("ID-REF", "") + " " + _text(ref, "SHORT-NAME")
        if any(n.lower() in idr.lower() for n in needles):
            v = _text(ref, "SIMPLE-VALUE") or _text(ref, "VALUE")
            try:
                return _coded_value(v)
            except ValueError:
                return None
    return None


def _roots(path: Path) -> list[ET.Element]:
    if path.suffix.lower() == ".pdx":
        out = []
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if re.search(r"\.odx(-[a-z]+)?$", n, re.I):
                    out.append(_strip_ns(ET.fromstring(z.read(n))))
        return out
    return [_strip_ns(ET.parse(path).getroot())]


def _sid(name: str) -> str:
    return re.sub(r"[^\w]+", "_", name).strip("_").lower() or "service"


def pack_from_odx(path) -> tuple[dict, list[BiText]]:
    p = Path(path)
    try:
        roots = _roots(p)
    except (ET.ParseError, zipfile.BadZipFile, OSError) as e:
        raise D.PackError([BiText(f"Cannot read the ODX data: {e}", f"تعذّرت قراءة بيانات ODX: {e}")]) from None
    requests = {}
    for r in roots:
        for req in r.iter("REQUEST"):
            if req.get("ID"):
                requests[req.get("ID")] = req
    warnings: list[BiText] = []
    pack = {"format": D.FORMAT, "version": 1, "name": f"ODX {p.stem}", "name_ar": f"ODX {p.stem}",
            "source": f"ODX import (read-only): {p.name}", "imported_from": "odx",
            "ecus": {}, "routines": [], "io_controls": [], "adaptations": [], "dids": []}
    ios: dict[tuple[str, str], dict] = {}
    for r in roots:
        for layer in [el for el in r.iter() if el.tag in ("BASE-VARIANT", "ECU-VARIANT")]:
            lname = _text(layer, "SHORT-NAME") or layer.get("ID", "ecu")
            key = _sid(lname)
            tx = _comparam(layer, "CanPhysReqId", "PhysReqId")
            rx = _comparam(layer, "CanRespUSDTId", "RespUSDTId")
            if tx is None or rx is None:
                warnings.append(BiText(f"{lname}: no CAN ids in the ODX data - set tx / rx in the pack before use.",
                                       f"{lname}: لا توجد معرّفات CAN في بيانات ODX - اضبط tx / rx في الحزمة قبل الاستخدام."))
            pack["ecus"].setdefault(key, {"name": _text(layer, "LONG-NAME") or lname, "name_ar": "",
                                          "tx": f"{tx if tx is not None else 0x7E0:03X}",
                                          "rx": f"{rx if rx is not None else 0x7E8:03X}", "protocol": "uds"})
            for ds in layer.iter("DIAG-SERVICE"):
                sname = _text(ds, "SHORT-NAME") or ds.get("ID", "")
                lname_ds = _text(ds, "LONG-NAME") or sname
                ref = ds.find("REQUEST-REF")
                req = requests.get(ref.get("ID-REF")) if ref is not None else None
                if req is None:
                    continue
                prefix, const = _request_bytes(req)
                if len(prefix) < 3:
                    continue
                why = D.policy_reason(f"{sname} | {lname_ds}")
                if why:
                    warnings.append(BiText(f"Skipped {sname}: ", f"تم تخطي {sname}: ") + D.policy_text(why))
                    continue
                sid = prefix[0]
                base = {"id": f"{key}_{_sid(sname)}", "name": lname_ds, "name_ar": "", "ecu": key,
                        "session": "extended", "category": "other", "preconditions": [], "odx_service": sname}
                if sid == 0x31 and prefix[1] == 0x01 and len(prefix) >= 4:
                    base.update(rid=prefix[2:4].hex().upper(), start_params=prefix[4:].hex().upper())
                    if not const:
                        base["note"] = "Variable start parameters in the ODX data - check start_params."
                    pack["routines"].append(base)
                elif sid == 0x2F and len(prefix) >= 5 and prefix[3] == 0x03:
                    did = prefix[1:3].hex().upper()
                    io = ios.get((key, did))
                    if io is None:
                        io = dict(base, id=f"{key}_io_{did.lower()}", did=did, states=[], max_duration_s=30,
                                  category="actuator")
                        ios[(key, did)] = io
                        pack["io_controls"].append(io)
                    io["states"].append({"label": lname_ds, "label_ar": "", "value": prefix[4:].hex().upper()})
                elif sid == 0x2E and len(prefix) >= 4 and const:
                    base.update(did=prefix[1:3].hex().upper(), value=prefix[3:].hex().upper(), read_back="compare",
                                category="adaptation")
                    pack["adaptations"].append(base)
                elif sid == 0x22 and len(prefix) == 3:
                    pack["dids"].append({"did": prefix[1:3].hex().upper(), "name": lname_ds, "name_ar": "",
                                         "type": "hex", "bytes": 0})
    if not any(pack[k] for k in ("routines", "io_controls", "adaptations", "dids")):
        raise D.PackError([BiText("No usable services (31 / 2F / 2E / 22 with constant parameters) in the ODX data.",
                                  "لا توجد خدمات قابلة للاستخدام (31 / 2F / 2E / 22 بمعاملات ثابتة) في بيانات ODX.")])
    warnings.append(BiText("Imported from ODX: review names (add Arabic names), sessions and preconditions before use.",
                           "مستورد من ODX: راجع الأسماء (أضف الأسماء العربية) والجلسات والشروط المسبقة قبل الاستخدام."))
    pack, errors, more = D.normalize(pack)
    if errors:
        raise D.PackError(errors)
    return pack, warnings + [w for w in more if "Arabic" not in w.en]
