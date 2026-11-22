"""TunerStudio ``.ini`` definitions (rusEFI, Speeduino - open source ECUs) -> map packs, and ``.msq`` tunes ->
calibration images. Pure Python.

The ini describes the controller's configuration *pages*: ``[Constants]`` lists every field
(``name = array, U16, 7868, [16x16], "%", 0.1, 0, 0, 999, 1``), ``[TableEditor]`` / ``[CurveEditor]`` say which
arrays are the X / Y bins of which table. The importer turns tables and curves into maps with stored axes, and
the other arrays into curves / blocks. Addresses are offsets in the *pages image*: the pages one after another
(page 1 at ``base``), which is what :func:`msq_to_image` writes from a tune file.

Shapes are ``[cols]`` or ``[cols x rows]`` (X fastest in memory). Units / scales written as expressions
(``{...}``) import as raw values (scale 1) with the expression kept in the description.
"""
from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .model import AxisDef, MapDef, MapPack, encode_array

TS_TYPES = {"U08": "u8", "S08": "s8", "U16": "u16", "S16": "s16", "U32": "u32", "S32": "s32", "F32": "f32"}


@dataclass
class Field:
    name: str
    kind: str                 # array / scalar / bits / string
    dtype: str
    page: int
    offset: int
    cols: int = 1
    rows: int = 1
    units: str = ""
    scale: float = 1.0
    translate: float = 0.0
    lo: float | None = None
    hi: float | None = None
    digits: int | None = None
    notes: list = field(default_factory=list)


@dataclass
class IniResult:
    pack: MapPack
    fields: dict
    pages: list               # [(page number, size)]
    page_base: dict           # page -> offset in the pages image
    endian: str = "le"
    signature: str = ""
    warnings: list = field(default_factory=list)


def split_args(s: str) -> list[str]:
    """Comma split that keeps "quoted, text" and {expressions, with commas} together; strips comments."""
    out, cur, depth, q = [], [], 0, False
    i = 0
    while i < len(s):
        ch = s[i]
        if q:
            cur.append(ch)
            if ch == "\\" and i + 1 < len(s):
                cur.append(s[i + 1])
                i += 1
            elif ch == '"':
                q = False
        elif ch == '"':
            q = True
            cur.append(ch)
        elif ch == "{":
            depth += 1
            cur.append(ch)
        elif ch == "}":
            depth -= 1
            cur.append(ch)
        elif ch == ";" and depth == 0:
            break
        elif ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    if cur or out:
        out.append("".join(cur).strip())
    return out


def _unq(s: str) -> str:
    s = s.strip()
    return s[1:-1] if len(s) >= 2 and s[0] == s[-1] == '"' else s


def _num(s: str):
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        return _arith(s[1:-1].strip())
    try:
        v = float(s)
    except ValueError:
        return None
    return v if math.isfinite(v) else None       # inf / nan / 1e999 are no usable numbers


def _arith(expr: str):
    """Value of a constant arithmetic expression such as ``1/10`` (numbers and + - * / only), else None."""
    import ast
    import operator
    ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            return ops[type(n.op)](ev(n.left), ev(n.right))
        raise ValueError
    try:
        v = ev(ast.parse(expr, mode="eval").body)
    except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, RecursionError, MemoryError):
        return None
    return v if math.isfinite(v) else None


def _lines(text: str, defined: set[str]):
    """(section, line) after the #if / #else / #endif preprocessor (a name is true when #set / given)."""
    section = ""
    stack: list[bool] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            parts = line[1:].split()
            word = parts[0].lower() if parts else ""
            if word == "if":
                stack.append(len(parts) > 1 and parts[1] in defined)
            elif word == "else" and stack:
                stack[-1] = not stack[-1]
            elif word == "endif" and stack:
                stack.pop()
            elif word == "set" and len(parts) > 1 and all(stack):
                defined.add(parts[1])
            elif word == "unset" and len(parts) > 1 and all(stack):
                defined.discard(parts[1])
            continue
        if not all(stack):
            continue
        if line.startswith(";"):
            continue
        if line.startswith("[") and "]" in line:
            section = line[1:line.index("]")]
            continue
        yield section, line


def parse_ini(text: str, base: int = 0, defined=None, include_scalars: bool = False,
              name: str = "TunerStudio ini") -> IniResult:
    defined = set(defined or ())
    fields: dict[str, Field] = {}
    warnings: list[str] = []
    endian, signature = "le", ""
    page = 1
    page_sizes: list[int] = []
    tables, curves = [], []
    cur = None
    for section, line in _lines(text, defined):
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        if section == "MegaTune" and key == "signature" or section == "TunerStudio" and key == "signature":
            signature = _unq((split_args(val) or [""])[0]) if val else ""
        if section == "Constants":
            if key == "endianness":
                endian = "be" if val.split(";")[0].strip().lower().startswith("big") else "le"
                continue
            if key == "page":
                try:
                    page = int(val.split(";")[0].strip())
                except ValueError:
                    pass
                continue
            if key == "pageSize":
                page_sizes = [int(_num(a) or 0) for a in split_args(val)]
                continue
            args = split_args(val)
            if len(args) < 3 or args[0] not in ("array", "scalar", "bits", "string"):
                continue
            kind = args[0]
            dt = TS_TYPES.get(args[1].upper())
            if kind == "string":
                continue
            if dt is None:
                continue
            try:
                off = int(float(args[2]))
            except (ValueError, OverflowError):        # OverflowError: Infinity / 1e999
                continue
            f = Field(key, kind, dt, page, off)
            rest = args[3:]
            if kind == "array" and rest:
                m = re.match(r"\[\s*(\d+)\s*(?:x\s*(\d+))?\s*\]", rest[0])
                if not m:
                    continue
                f.cols = int(m.group(1))
                f.rows = int(m.group(2) or 1)
                rest = rest[1:]
            if kind in ("array", "scalar"):
                if rest:
                    u = rest[0]
                    if u.startswith("{"):
                        f.notes.append(f"units {u}")
                    else:
                        f.units = _unq(u)
                for attr, idx in (("scale", 1), ("translate", 2), ("lo", 3), ("hi", 4), ("digits", 5)):
                    if len(rest) > idx:
                        v = _num(rest[idx])
                        if v is None:
                            if rest[idx].startswith("{"):
                                f.notes.append(f"{attr} {rest[idx]}")
                            continue
                        setattr(f, attr, int(v) if attr == "digits" else v)
            fields[key] = f
        elif section == "TableEditor":
            if key == "table":
                a = split_args(val)
                cur = {"kind": "table", "id": a[0] if a else "", "title": _unq(a[2]) if len(a) > 2 else ""}
                tables.append(cur)
            elif cur is not None and cur["kind"] == "table" and key in ("xBins", "yBins", "zBins"):
                cur[key] = (split_args(val) or [""])[0]
        elif section == "CurveEditor":
            if key == "curve":
                a = split_args(val)
                cur = {"kind": "curve", "id": a[0] if a else "", "title": _unq(a[1]) if len(a) > 1 else ""}
                curves.append(cur)
            elif cur is not None and cur["kind"] == "curve" and key in ("xBins", "yBins"):
                cur[key] = (split_args(val) or [""])[0]
    pages = sorted({f.page for f in fields.values()})
    sizes = {p: (page_sizes[p - 1] if 0 < p <= len(page_sizes) else 0) for p in pages}
    for p in pages:                                   # pages without a declared size: end of their last field
        if not sizes[p]:
            sizes[p] = max(f.offset + f.cols * f.rows * _size(f.dtype) for f in fields.values() if f.page == p)
    page_base, pos = {}, base
    for p in pages:
        page_base[p] = pos
        pos += sizes[p]
    pack = MapPack(name=name, base_address=0, description=signature)
    used: set[str] = set()

    def addr(f: Field) -> int:
        return page_base[f.page] + f.offset

    def axis(fname: str) -> AxisDef:
        f = fields.get(fname)
        if f is None or f.kind != "array":
            return AxisDef(name=fname or "")
        used.add(fname)
        return AxisDef(name=fname, address=addr(f), count=f.cols * f.rows, dtype=f.dtype, endian=endian,
                       factor=f.scale or 1.0, offset=f.translate * (f.scale or 1.0), unit=f.units)

    def mapdef(f: Field, title: str, folder: str) -> MapDef:
        # TunerStudio: phys = (raw + translate) * scale
        m = MapDef(name=f.name, address=addr(f), cols=f.cols, rows=f.rows, dtype=f.dtype, endian=endian,
                   order="row", factor=f.scale or 1.0, offset=f.translate * (f.scale or 1.0), unit=f.units,
                   folder=folder, description=title + ("; " + "; ".join(f.notes) if f.notes else ""), source="ini",
                   lower=f.lo, upper=f.hi, digits=f.digits)
        used.add(f.name)
        return m

    for t in tables:
        z = fields.get(t.get("zBins", ""))
        if z is None or z.kind != "array":
            continue
        m = mapdef(z, t["title"], "Tables")
        m.x_axis, m.y_axis = axis(t.get("xBins", "")), axis(t.get("yBins", ""))
        if m.x_axis.stored and m.y_axis.stored and m.x_axis.count == z.rows and m.y_axis.count == z.cols \
                and z.cols != z.rows:
            m.cols, m.rows = z.rows, z.cols           # shape written the other way round
        if m.name not in {x.name for x in pack.maps}:
            pack.add(m)
    for c in curves:
        y = fields.get(c.get("yBins", ""))
        if y is None or y.kind != "array" or y.name in used:
            continue
        m = mapdef(y, c["title"], "Curves")
        m.x_axis = axis(c.get("xBins", ""))
        pack.add(m)
    for f in fields.values():
        if f.name in used:
            continue
        if f.kind == "array":
            pack.add(mapdef(f, "", "Arrays"))
        elif f.kind == "scalar" and include_scalars:
            pack.add(mapdef(f, "", "Scalars"))
    return IniResult(pack, fields, [(p, sizes[p]) for p in pages], page_base, endian, signature, warnings)


def _size(dt: str) -> int:
    from .model import dtype_size
    return dtype_size(dt)


def load_ini(path, **kw) -> IniResult:
    p = Path(path)
    text = p.read_bytes().decode("utf-8", errors="replace")
    kw.setdefault("name", p.stem)
    return parse_ini(text, **kw)


def msq_values(path_or_text) -> dict[str, list[float] | float | str]:
    """``<constant name=...>`` values of a TunerStudio .msq tune (numbers as floats, text as str)."""
    text = path_or_text
    if not str(path_or_text).lstrip().startswith("<"):
        text = Path(path_or_text).read_bytes().decode("utf-8", errors="replace")
    root = ET.fromstring(text)
    out = {}
    for el in root.iter():
        if el.tag.split("}")[-1] != "constant":
            continue
        name = el.get("name")
        body = (el.text or "").strip()
        nums = []
        try:
            nums = [float(x) for x in body.split()]
        except ValueError:
            out[name] = _unq(body)
            continue
        out[name] = nums[0] if len(nums) == 1 and not el.get("rows") else nums
    return out


def msq_to_image(ini: IniResult, values: dict, fill: int = 0) -> tuple[bytes, list[str]]:
    """Pages image of a tune: every array / scalar of *values* (physical) written at its ini offset. Returns
    (image, names written)."""
    total = sum(s for _p, s in ini.pages)
    base0 = min(ini.page_base.values()) if ini.page_base else 0
    img = bytearray(bytes([fill]) * total)
    written = []
    for name, v in values.items():
        f = ini.fields.get(name)
        if f is None or f.kind not in ("array", "scalar") or isinstance(v, str):
            continue
        vals = np.atleast_1d(np.asarray(v, dtype=np.float64))
        n = f.cols * f.rows if f.kind == "array" else 1
        if len(vals) != n:
            continue
        scale = f.scale or 1.0
        raw = vals / scale - f.translate
        b = encode_array(raw, f.dtype, ini.endian)
        o = ini.page_base[f.page] - base0 + f.offset
        img[o:o + len(b)] = b
        written.append(name)
    return bytes(img), written
