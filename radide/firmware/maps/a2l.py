"""ASAM MCD-2 MC (ASAP2, ``*.a2l``) import / export for map packs - the common subset, pure Python.

Import understands:

* ``PROJECT`` / ``MODULE`` / ``MOD_COMMON`` (``BYTE_ORDER``, ``ALIGNMENT_*``) / ``MOD_PAR`` (``MEMORY_SEGMENT``),
* ``CHARACTERISTIC`` of type VALUE, CURVE, MAP and VAL_BLK (``NUMBER`` / ``MATRIX_DIM``), with ``AXIS_DESCR``
  STD_AXIS (axis inside the record), COM_AXIS (``AXIS_PTS_REF``), FIX_AXIS (``FIX_AXIS_PAR``,
  ``FIX_AXIS_PAR_DIST``, ``FIX_AXIS_PAR_LIST``), ``BYTE_ORDER``, ``PHYS_UNIT``, ``FORMAT``,
* ``AXIS_PTS`` (shared axes), ``RECORD_LAYOUT`` (``FNC_VALUES`` with ROW_DIR / COLUMN_DIR, ``AXIS_PTS_X/Y``,
  ``NO_AXIS_PTS_X/Y``, ``FIX_NO_AXIS_PTS_X/Y``, ``SRC_ADDR_*``, ``RESERVED``, ``ALIGNMENT_*``),
* ``COMPU_METHOD`` IDENTICAL, LINEAR (``COEFFS_LINEAR``) and RAT_FUNC (``COEFFS``) when it is linear; other
  conversions import as raw values with a note,
* ``FUNCTION`` (``DEF_CHARACTERISTIC``) and ``GROUP`` (``REF_CHARACTERISTIC``) become the map folders.

``IF_DATA`` and ``A2ML`` blocks are skipped. ECU addresses become file offsets with ``base`` (the address of
file offset 0): given, or the lowest FLASH / ROM ``MEMORY_SEGMENT``, or 0 when every address fits in the file.

Export writes a self-contained A2L of a map pack (one RECORD_LAYOUT per value / axis type, COMPU_METHODs for the
factors, AXIS_PTS for stored axes, FIX_AXIS_PAR_LIST for fixed ones) that this importer reads back unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .model import DTYPES, AxisDef, MapDef, MapPack, read_array

A2L_TYPES = {"UBYTE": "u8", "SBYTE": "s8", "UWORD": "u16", "SWORD": "s16", "ULONG": "u32", "SLONG": "s32",
             "FLOAT32_IEEE": "f32", "FLOAT64_IEEE": "f64", "A_UINT64": "u64", "A_INT64": "s64"}
TYPE_A2L = {v: k for k, v in A2L_TYPES.items()}
RESERVED_SIZE = {"BYTE": 1, "WORD": 2, "LONG": 4}
ALIGN_KEYS = {"ALIGNMENT_BYTE": 1, "ALIGNMENT_WORD": 2, "ALIGNMENT_LONG": 4, "ALIGNMENT_INT64": 8,
              "ALIGNMENT_FLOAT32_IEEE": 4, "ALIGNMENT_FLOAT64_IEEE": 8}

# positional parameters after "/begin TAG"
HEADER_ARGS = {
    "PROJECT": 2, "MODULE": 2, "HEADER": 1, "MOD_PAR": 1, "MOD_COMMON": 1,
    "MEMORY_SEGMENT": 12, "MEMORY_LAYOUT": 8,
    "CHARACTERISTIC": 9, "AXIS_PTS": 10, "AXIS_DESCR": 6, "RECORD_LAYOUT": 1,
    "COMPU_METHOD": 5, "COMPU_TAB": 4, "COMPU_VTAB": 4, "COMPU_VTAB_RANGE": 3,
    "MEASUREMENT": 8, "FUNCTION": 2, "GROUP": 2, "UNIT": 4,
    "DEF_CHARACTERISTIC": 0, "REF_CHARACTERISTIC": 0, "SUB_FUNCTION": 0, "SUB_GROUP": 0,
    "IN_MEASUREMENT": 0, "OUT_MEASUREMENT": 0, "LOC_MEASUREMENT": 0, "FIX_AXIS_PAR_LIST": 0,
    "ANNOTATION": 0, "ANNOTATION_TEXT": 0, "FUNCTION_LIST": 0, "VIRTUAL_CHARACTERISTIC": 1,
}
SKIP_BLOCKS = {"IF_DATA", "A2ML"}


MAX_AXIS_POINTS = 65535            # an axis count is a UWORD in ASAP2


class A2LError(ValueError):
    pass


# ====================================================================== tokens / tree
_TOKEN = re.compile(r'''
    (?P<ws>\s+) | (?P<c1>/\*.*?\*/) | (?P<c2>//[^\n]*) |
    (?P<str>"(?:[^"\\]|\\.|"")*") |
    (?P<begin>/begin\b) | (?P<end>/end\b) |
    (?P<tok>[^\s"]+)
''', re.S | re.X)


@dataclass
class Tok:
    kind: str           # "str", "begin", "end", "tok"
    text: str
    line: int


def tokenize(text: str) -> list[Tok]:
    out, line, pos = [], 1, 0
    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        s = m.group()
        if kind in ("str", "begin", "end", "tok"):
            if kind == "str":
                s = s[1:-1].replace('\\"', '"').replace('""', '"').replace("\\n", "\n")
            out.append(Tok(kind, s, line))
        line += m.group().count("\n")
        pos = m.end()
    if pos != len(text):
        raise A2LError(f"cannot read the A2L near line {line}")
    return out


@dataclass
class Node:
    tag: str
    args: list = field(default_factory=list)          # positional header parameters (str)
    children: list = field(default_factory=list)      # Node
    items: list = field(default_factory=list)         # (KEYWORD, [args]) in order
    rest: list = field(default_factory=list)          # every non-header token (lists such as DEF_CHARACTERISTIC)
    line: int = 0

    def item(self, key: str):
        return next((a for k, a in self.items if k == key), None)

    def kids(self, tag: str):
        return [c for c in self.children if c.tag == tag]

    def walk(self):
        # pre-order without recursion (a corrupted file may nest blocks thousands of levels deep)
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))


_KW = re.compile(r"^[A-Z][A-Z0-9_]*$")


def parse_tree(text: str) -> Node:
    toks = tokenize(text)
    root = Node("ROOT")
    stack = [root]
    i, n = 0, len(toks)
    pending: list[Tok] = []          # tokens of the current block not yet assigned

    def flush(node: Node, toks_: list[Tok]):
        want = HEADER_ARGS.get(node.tag, 0) - len(node.args)
        k = 0
        while want > 0 and k < len(toks_):
            node.args.append(toks_[k].text)
            k += 1
            want -= 1
        cur = None
        for t in toks_[k:]:
            node.rest.append(t.text)
            starts = t.kind == "tok" and _KW.match(t.text) and (cur is None or t.line != cur[2])
            if starts:
                cur = [t.text, [], t.line]
                node.items.append((cur[0], cur[1]))
            elif cur is not None:
                cur[1].append(t.text)
        toks_.clear()

    while i < n:
        t = toks[i]
        if t.kind == "begin":
            if i + 1 >= n:
                raise A2LError("'/begin' at the end of the file")
            flush(stack[-1], pending)
            tag = toks[i + 1].text
            i += 2
            if tag in SKIP_BLOCKS:
                depth = 1
                while i < n and depth:
                    if toks[i].kind == "begin":
                        depth += 1
                    elif toks[i].kind == "end":
                        depth -= 1
                        i += 1
                    i += 1
                continue
            node = Node(tag, line=t.line)
            stack[-1].children.append(node)
            stack.append(node)
            continue
        if t.kind == "end":
            flush(stack[-1], pending)
            tag = toks[i + 1].text if i + 1 < n else ""
            if len(stack) == 1:
                raise A2LError(f"'/end {tag}' without '/begin' (line {t.line})")
            if stack[-1].tag != tag:
                raise A2LError(f"'/end {tag}' closes '/begin {stack[-1].tag}' (line {t.line})")
            stack.pop()
            i += 2
            continue
        pending.append(t)
        i += 1
    flush(stack[-1], pending)
    if len(stack) != 1:
        raise A2LError(f"'/begin {stack[-1].tag}' is never closed")
    return root


def num(s) -> float:
    s = str(s).strip()
    try:
        if s.lower().startswith(("0x", "-0x")):
            v = float(int(s, 16))
        else:
            v = float(s)
    except (ValueError, OverflowError):
        raise A2LError(f"not a number: {s!r}") from None
    if v != v or v in (float("inf"), float("-inf")):          # nan / inf / 1e999: no usable number
        raise A2LError(f"not a finite number: {s!r}")
    return v


# ====================================================================== import
@dataclass
class Segment:
    name: str
    prg_type: str
    mem_type: str
    address: int
    size: int


@dataclass
class A2LResult:
    pack: MapPack
    segments: list[Segment] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    project: str = ""
    module: str = ""
    byte_order: str = "le"


def _endian(word: str | None, default: str) -> str:
    if not word:
        return default
    w = word.upper()
    if w in ("MSB_FIRST", "BIG_ENDIAN", "MSB_FIRST_MSW_LAST"):
        return "be"
    if w in ("MSB_LAST", "LITTLE_ENDIAN", "MSB_LAST_MSW_FIRST"):
        return "le"
    return default


def _conversion(cm: Node | None, warnings: list, owner: str) -> tuple[float, float, str, int | None]:
    """(factor, offset, unit, digits) of a COMPU_METHOD (phys = raw * factor + offset)."""
    if cm is None:
        return 1.0, 0.0, "", None
    ctype = (cm.args[2] if len(cm.args) > 2 else "IDENTICAL").upper()
    unit = cm.args[4] if len(cm.args) > 4 else ""
    digits = None                      # display digits come from the characteristic's FORMAT only
    if ctype == "IDENTICAL":
        return 1.0, 0.0, unit, digits
    if ctype == "LINEAR":
        c = cm.item("COEFFS_LINEAR")
        if c and len(c) >= 2:
            return num(c[0]), num(c[1]), unit, digits
    if ctype == "RAT_FUNC":
        c = cm.item("COEFFS")
        if c and len(c) >= 6:
            a, b, cc, d, e, f = (num(x) for x in c[:6])
            if a == 0 and d == 0 and e == 0 and b != 0 and f != 0:
                # raw = (b*phys + c) / f  ->  phys = raw * f/b - c/b
                return f / b, -cc / b, unit, digits
    warnings.append(f"{owner}: conversion {cm.args[0] if cm.args else '?'} ({ctype}) is not linear - raw values")
    return 1.0, 0.0, unit, digits


class _Layout:
    def __init__(self, node: Node, mod_align: dict):
        self.name = node.args[0] if node.args else ""
        self.comps = []                       # (position, key, args)
        self.align = dict(mod_align)
        self.fix_no = {}
        for k, a in node.items:
            if k in ALIGN_KEYS and a:
                self.align[ALIGN_KEYS[k]] = int(num(a[0]))
            elif k in ("FIX_NO_AXIS_PTS_X", "FIX_NO_AXIS_PTS_Y") and a:
                self.fix_no[k[-1]] = int(num(a[0]))
            elif k in ("FNC_VALUES", "AXIS_PTS_X", "AXIS_PTS_Y", "NO_AXIS_PTS_X", "NO_AXIS_PTS_Y", "SRC_ADDR_X",
                       "SRC_ADDR_Y", "RIP_ADDR_X", "RIP_ADDR_Y", "RIP_ADDR_W", "SHIFT_OP_X", "SHIFT_OP_Y",
                       "OFFSET_X", "OFFSET_Y", "DIST_OP_X", "DIST_OP_Y", "RESERVED", "AXIS_RESCALE_X",
                       "NO_RESCALE_X", "IDENTIFICATION") and a:
                try:
                    self.comps.append((int(num(a[0])), k, a[1:]))
                except A2LError:
                    pass
        self.comps.sort(key=lambda c: c[0])

    def comp(self, key):
        return next(((p, k, a) for p, k, a in self.comps if k == key), None)

    def dtype(self, key) -> str | None:
        c = self.comp(key)
        return A2L_TYPES.get(c[2][0].upper()) if c and c[2] else None

    def fnc_order(self) -> str:
        c = self.comp("FNC_VALUES")
        if c and len(c[2]) > 1 and c[2][1].upper().startswith("COLUMN"):
            return "col"
        return "row"

    def offsets(self, counts: dict, data=None, start: int = 0, endian: str = "le") -> dict:
        """Byte offset (relative to the record start) of each component; *counts*: {"X": nx, "Y": ny} maximum
        point numbers; NO_AXIS_PTS read from *data* (when given) replace them (dynamic record layouts)."""
        off, out = 0, {}
        counts = dict(counts)
        for _p, k, a in self.comps:
            if k == "RESERVED":
                off += RESERVED_SIZE.get(a[0].upper(), 1) if a else 1
                continue
            dt = A2L_TYPES.get(a[0].upper()) if a else None
            if dt is None or dt not in DTYPES:
                continue
            size = DTYPES[dt][1]
            al = self.align.get(size, 1)
            if al > 1 and (start + off) % al:          # alignment of the address in memory
                off += al - (start + off) % al
            out[k] = off
            if k in ("NO_AXIS_PTS_X", "NO_AXIS_PTS_Y") and data is not None:
                v = read_array(data, start + off, 1, dt, endian)[0]
                if 1 <= v <= 1024:
                    counts[k[-1]] = int(v)
            if k == "AXIS_PTS_X":
                off += size * counts.get("X", 1)
            elif k == "AXIS_PTS_Y":
                off += size * counts.get("Y", 1)
            elif k == "FNC_VALUES":
                off += size * counts.get("X", 1) * counts.get("Y", 1)
            else:
                off += size
        out["_counts"] = counts
        return out


def parse_a2l(text: str, data=None, base: int | None = None, name: str = "") -> A2LResult:
    """Parse A2L *text* into a map pack. *data* (the binary) resolves dynamic axis sizes; *base* is the ECU
    address of file offset 0 (None: from the memory segments)."""
    root = parse_tree(text)
    warnings: list[str] = []
    project = next((n for n in root.walk() if n.tag == "PROJECT"), None)
    module = next((n for n in root.walk() if n.tag == "MODULE"), None)
    scope = module or project or root
    mod_common = next((n for n in scope.walk() if n.tag == "MOD_COMMON"), None)
    byte_order = _endian(mod_common.item("BYTE_ORDER")[0] if mod_common and mod_common.item("BYTE_ORDER") else
                         None, "le")
    mod_align = {}
    if mod_common:
        for k, a in mod_common.items:
            if k in ALIGN_KEYS and a:
                mod_align[ALIGN_KEYS[k]] = int(num(a[0]))
    segments = []
    for ms in (n for n in scope.walk() if n.tag == "MEMORY_SEGMENT"):
        try:
            segments.append(Segment(ms.args[0], ms.args[2].upper(), ms.args[3].upper(), int(num(ms.args[5])),
                                    int(num(ms.args[6]))))
        except (IndexError, A2LError):
            warnings.append(f"MEMORY_SEGMENT {ms.args[:1]} could not be read")
    nodes = {}
    for nd in scope.walk():
        if nd.tag in ("COMPU_METHOD", "RECORD_LAYOUT", "AXIS_PTS", "CHARACTERISTIC") and nd.args:
            nodes[(nd.tag, nd.args[0])] = nd
    layouts = {k[1]: _Layout(v, mod_align) for k, v in nodes.items() if k[0] == "RECORD_LAYOUT"}
    folders = {}
    for nd in scope.walk():
        if nd.tag in ("FUNCTION", "GROUP") and nd.args:
            for lst in nd.kids("DEF_CHARACTERISTIC") + nd.kids("REF_CHARACTERISTIC"):
                for cname in lst.rest:
                    folders.setdefault(cname, nd.args[0])
    chars = [nd for nd in scope.walk() if nd.tag == "CHARACTERISTIC" and len(nd.args) >= 9]
    addrs = [int(num(c.args[3])) for c in chars] + \
            [int(num(a.args[2])) for a in scope.walk() if a.tag == "AXIS_PTS" and len(a.args) >= 3]
    if base is None:
        base = _guess_base(segments, addrs, len(data) if data is not None else None)
    pack = MapPack(name=name or (module.args[0] if module and module.args else "A2L import"), base_address=base,
                   description=(module.args[1] if module and len(module.args) > 1 else ""))

    def cm(name_):
        return nodes.get(("COMPU_METHOD", name_))

    def axis_pts(name_) -> AxisDef | None:
        ap = nodes.get(("AXIS_PTS", name_))
        if ap is None:
            warnings.append(f"AXIS_PTS {name_} is missing")
            return None
        lay = layouts.get(ap.args[4])
        if lay is None:
            warnings.append(f"RECORD_LAYOUT {ap.args[4]} of AXIS_PTS {name_} is missing")
            return None
        en = _endian(ap.item("BYTE_ORDER")[0] if ap.item("BYTE_ORDER") else None, byte_order)
        maxn = int(num(ap.args[7]))
        start = int(num(ap.args[2])) - base
        offs = lay.offsets({"X": maxn}, data, start, en)
        dt = lay.dtype("AXIS_PTS_X")
        if dt is None or "AXIS_PTS_X" not in offs:
            warnings.append(f"AXIS_PTS {name_}: no AXIS_PTS_X in {lay.name}")
            return None
        f, o, unit, _d = _conversion(cm(ap.args[6]), warnings, name_)
        if ap.item("PHYS_UNIT"):
            unit = ap.item("PHYS_UNIT")[0]
        iq = ap.args[3] if len(ap.args) > 3 and ap.args[3] != "NO_INPUT_QUANTITY" else ""
        return AxisDef(name=iq, address=start + offs["AXIS_PTS_X"], count=offs["_counts"]["X"], dtype=dt,
                       endian=en, factor=f, offset=o, unit=unit)

    for c in chars:
        cname, longid, ctype, addr, deposit = c.args[0], c.args[1], c.args[2].upper(), c.args[3], c.args[4]
        if ctype not in ("VALUE", "CURVE", "MAP", "VAL_BLK"):
            if ctype not in ("ASCII",):
                warnings.append(f"{cname}: type {ctype} is not supported")
            continue
        lay = layouts.get(deposit)
        if lay is None:
            warnings.append(f"{cname}: RECORD_LAYOUT {deposit} is missing")
            continue
        dt = lay.dtype("FNC_VALUES")
        if dt is None or dt not in DTYPES:
            warnings.append(f"{cname}: unsupported FNC_VALUES type in {deposit}")
            continue
        en = _endian(c.item("BYTE_ORDER")[0] if c.item("BYTE_ORDER") else None, byte_order)
        start = int(num(addr)) - base
        f, o, unit, digits = _conversion(cm(c.args[6]), warnings, cname)
        if c.item("PHYS_UNIT"):
            unit = c.item("PHYS_UNIT")[0]
        if c.item("FORMAT"):
            mm = re.match(r"%\s*\d*\.(\d+)", c.item("FORMAT")[0])
            if mm:
                digits = int(mm.group(1))
        m = MapDef(name=cname, address=start, dtype=dt, endian=en, order=lay.fnc_order(), factor=f, offset=o,
                   unit=unit, description=longid, folder=folders.get(cname, ""), source="a2l", digits=digits)
        try:
            m.lower, m.upper = num(c.args[7]), num(c.args[8])
            if m.lower is not None and m.upper is not None and m.lower <= -1e30:
                m.lower = m.upper = None
        except A2LError:
            pass
        axes = c.kids("AXIS_DESCR")
        counts = {"X": 1, "Y": 1}
        if ctype == "VAL_BLK":
            md = c.item("MATRIX_DIM")
            nb = c.item("NUMBER")
            if md:
                dims = [int(num(x)) for x in md if re.match(r"^-?\d", x)]
                counts = {"X": max(1, dims[0]), "Y": max(1, dims[1]) if len(dims) > 1 else 1}
            elif nb:
                counts = {"X": int(num(nb[0])), "Y": 1}
        ax_defs: list[AxisDef] = []
        for idx, ad in enumerate(axes[:2]):
            key = "XY"[idx]
            attr = ad.args[0].upper() if ad.args else "STD_AXIS"
            maxn = int(num(ad.args[3])) if len(ad.args) > 3 else 1
            counts[key] = lay.fix_no.get(key, maxn)
            ax = AxisDef(name=ad.args[1] if len(ad.args) > 1 and ad.args[1] != "NO_INPUT_QUANTITY" else "")
            af, ao, aunit, _d = _conversion(cm(ad.args[2]) if len(ad.args) > 2 else None, warnings, cname)
            if ad.item("PHYS_UNIT"):
                aunit = ad.item("PHYS_UNIT")[0]
            ax.factor, ax.offset, ax.unit = af, ao, aunit
            ax.endian = _endian(ad.item("BYTE_ORDER")[0] if ad.item("BYTE_ORDER") else None, en)
            ax.count = counts[key]
            ax_defs.append((attr, ad, ax))
        offs = lay.offsets(counts, data, start, en)
        counts = offs["_counts"]
        if "FNC_VALUES" not in offs:
            warnings.append(f"{cname}: no FNC_VALUES in {deposit}")
            continue
        m.address = start + offs["FNC_VALUES"]
        m.cols, m.rows = counts["X"], counts["Y"]
        for idx, (attr, ad, ax) in enumerate(ax_defs):
            key = "XY"[idx]
            ax.count = counts[key]
            if attr == "STD_AXIS":
                k = f"AXIS_PTS_{key}"
                if k in offs:
                    ax.address = start + offs[k]
                    ax.dtype = lay.dtype(k) or dt
                else:
                    warnings.append(f"{cname}: STD_AXIS without {k} in {deposit}")
            elif attr in ("COM_AXIS", "RES_AXIS", "CURVE_AXIS"):
                ref = ad.item("AXIS_PTS_REF") or ad.item("CURVE_AXIS_REF")
                shared = axis_pts(ref[0]) if ref else None
                if shared is not None:
                    shared.name = ax.name or shared.name
                    ax = shared
                    if idx == 0:
                        m.cols = ax.count
                    else:
                        m.rows = ax.count
            elif attr == "FIX_AXIS":
                n_ = ax.count
                if ad.item("FIX_AXIS_PAR"):
                    o_, sh, n_ = (num(x) for x in ad.item("FIX_AXIS_PAR")[:3])
                    if not (0 <= n_ <= MAX_AXIS_POINTS and -64 <= sh <= 64):
                        warnings.append(f"{cname}: FIX_AXIS_PAR {n_:g} points / shift {sh:g} out of range")
                        continue
                    ax.values = [o_ + i * (2 ** sh) for i in range(int(n_))]
                elif ad.item("FIX_AXIS_PAR_DIST"):
                    o_, dist, n_ = (num(x) for x in ad.item("FIX_AXIS_PAR_DIST")[:3])
                    if not 0 <= n_ <= MAX_AXIS_POINTS:     # (a corrupted file: 4294967295 points)
                        warnings.append(f"{cname}: FIX_AXIS_PAR_DIST {n_:g} points out of range")
                        continue
                    ax.values = [o_ + i * dist for i in range(int(n_))]
                elif ad.kids("FIX_AXIS_PAR_LIST"):
                    ax.values = [num(x) for x in ad.kids("FIX_AXIS_PAR_LIST")[0].rest]
                if ax.values:
                    # fixed axis values are raw: convert to physical
                    ax.values = [v * ax.factor + ax.offset for v in ax.values]
                    ax.factor, ax.offset = 1.0, 0.0
                    ax.count = len(ax.values)
                    if idx == 0:
                        m.cols = ax.count
                    else:
                        m.rows = ax.count
            if idx == 0:
                m.x_axis = ax
            else:
                m.y_axis = ax
        if data is not None and (m.address < 0 or m.end > len(data)):
            warnings.append(f"{cname}: address 0x{int(num(addr)):X} is outside the binary (base 0x{base:X})")
        pack.add(m, replace=False)
    return A2LResult(pack, segments, warnings, project.args[0] if project and project.args else "",
                     module.args[0] if module and module.args else "", byte_order)


def _guess_base(segments: list[Segment], addrs: list[int], size: int | None) -> int:
    rom = [s for s in segments if s.mem_type in ("FLASH", "ROM", "EPROM", "EEPROM") or
           s.prg_type in ("CALIBRATION_VARIABLES", "DATA", "CODE", "OFFLINE_DATA")]
    rom = [s for s in rom if s.mem_type != "RAM"]
    if rom and addrs:
        # the segment that holds the most characteristics; its file base = the lowest ROM segment address
        lowest = min(s.address for s in rom)
        return lowest
    if not addrs:
        return 0
    if size is not None and max(addrs) < size:
        return 0
    lo = min(addrs)
    return lo & ~0xFFFF


def load_a2l(path, data=None, base: int | None = None) -> A2LResult:
    from pathlib import Path
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return parse_a2l(text, data, base, name=Path(path).stem)


# ====================================================================== export
def _ident(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_.\[\]]", "_", s.strip()) or "X"
    return s if not s[0].isdigit() else "_" + s


def _q(s: str) -> str:
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _f(v: float) -> str:
    v = float(v)
    return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)


def export_a2l(pack: MapPack, project: str = "RADIDE", module: str = "", byte_order: str | None = None,
               segment_size: int | None = None) -> str:
    """A2L text for *pack* (addresses = file offset + pack.base_address)."""
    base = pack.base_address
    module = _ident(module or pack.name or "MAPS")
    endians = {m.endian for m in pack.maps} | {a.endian for m in pack.maps for a in (m.x_axis, m.y_axis) if a.stored}
    bo = byte_order or ("be" if endians == {"be"} else "le")
    bo_word = "MSB_FIRST" if bo == "be" else "MSB_LAST"
    out = ["ASAP2_VERSION 1 71", f"/begin PROJECT {_ident(project)} \"Map pack exported by RAD IDE\"",
           f"  /begin MODULE {module} {_q(pack.description or pack.name)}",
           "    /begin MOD_COMMON \"\"", f"      BYTE_ORDER {bo_word}", "      ALIGNMENT_BYTE 1",
           "      ALIGNMENT_WORD 1", "      ALIGNMENT_LONG 1", "      ALIGNMENT_FLOAT32_IEEE 1",
           "    /end MOD_COMMON"]
    if pack.maps:
        end = max(m.span()[1] for m in pack.maps)
        size = segment_size or end
        out += ["    /begin MOD_PAR \"\"",
                f"      /begin MEMORY_SEGMENT FLASH \"\" DATA FLASH INTERN 0x{base:X} 0x{size:X} -1 -1 -1 -1 -1",
                "      /end MEMORY_SEGMENT", "    /end MOD_PAR"]
    layouts: dict[str, str] = {}
    cms: dict[tuple, str] = {}

    def layout(kind: str, dt: str, order: str = "row") -> str:
        name = f"RL_{kind}_{dt.upper()}" + ("_COL" if kind == "VAL" and order == "col" else "")
        if name not in layouts:
            if kind == "VAL":
                body = f"      FNC_VALUES 1 {TYPE_A2L[dt]} {'COLUMN_DIR' if order == 'col' else 'ROW_DIR'} DIRECT"
            else:
                body = f"      AXIS_PTS_X 1 {TYPE_A2L[dt]} INDEX_INCR DIRECT"
            layouts[name] = f"    /begin RECORD_LAYOUT {name}\n{body}\n    /end RECORD_LAYOUT"
        return name

    def compu(f: float, o: float, unit: str) -> str:
        if f == 1 and o == 0 and not unit:
            return "NO_COMPU_METHOD"
        key = (float(f), float(o), unit)
        if key not in cms:
            cms[key] = f"CM_{len(cms) + 1}"
        return cms[key]

    body: list[str] = []
    axis_names: dict[tuple, str] = {}
    used = {m.name for m in pack.maps}

    def axis_obj(m: MapDef, ax: AxisDef, key: str) -> str:
        k = (int(ax.address), ax.count, ax.dtype, ax.endian)
        if k in axis_names:
            return axis_names[k]
        nm = _ident(ax.name) if ax.name and ax.name not in ("X", "Y") else _ident(f"{m.name}_{key}")
        while nm in used:
            nm += "_AX"
        used.add(nm)
        axis_names[k] = nm
        lo, hi = DTYPES[ax.dtype][2] * ax.factor + ax.offset, DTYPES[ax.dtype][3] * ax.factor + ax.offset
        lines = [f"    /begin AXIS_PTS {nm} {_q(ax.name or '')} 0x{int(ax.address) + base:X} "
                 f"{_ident(ax.name) if ax.name else 'NO_INPUT_QUANTITY'} "
                 f"{layout('AX', ax.dtype)} 0 {compu(ax.factor, ax.offset, ax.unit)} {ax.count} "
                 f"{_f(min(lo, hi))} {_f(max(lo, hi))}"]
        if ax.endian != bo:
            lines.append(f"      BYTE_ORDER {'MSB_FIRST' if ax.endian == 'be' else 'MSB_LAST'}")
        if ax.unit:
            lines.append(f"      PHYS_UNIT {_q(ax.unit)}")
        lines.append("    /end AXIS_PTS")
        body.extend(lines)
        return nm

    for m in pack.maps:
        kind = {"value": "VALUE", "curve": "CURVE", "map": "MAP"}[m.kind]
        blk = kind != "VALUE" and not any(a.stored or a.values for a in (m.x_axis, m.y_axis))
        if blk:
            kind = "VAL_BLK"
        lo = m.lower if m.lower is not None else min(DTYPES[m.dtype][2] * m.factor + m.offset,
                                                      DTYPES[m.dtype][3] * m.factor + m.offset)
        hi = m.upper if m.upper is not None else max(DTYPES[m.dtype][2] * m.factor + m.offset,
                                                      DTYPES[m.dtype][3] * m.factor + m.offset)
        lines = [f"    /begin CHARACTERISTIC {_ident(m.name)} {_q(m.description)} {kind} 0x{m.address + base:X} "
                 f"{layout('VAL', m.dtype, m.order)} 0 {compu(m.factor, m.offset, m.unit)} {_f(lo)} {_f(hi)}"]
        if blk:
            lines.append(f"      MATRIX_DIM {m.cols} {m.rows} 1" if m.rows > 1 else f"      NUMBER {m.cols}")
        axes = [] if kind in ("VALUE", "VAL_BLK") else ([("X", m.x_axis, m.cols)] + ([("Y", m.y_axis, m.rows)]
                                                                       if kind == "MAP" else []))
        for key, ax, n in axes:
            if ax.stored:
                ref = axis_obj(m, ax, key)
                lines += [f"      /begin AXIS_DESCR COM_AXIS {_ident(ax.name) if ax.name else 'NO_INPUT_QUANTITY'} "
                          f"{compu(ax.factor, ax.offset, ax.unit)} {n} -1e12 1e12",
                          f"        AXIS_PTS_REF {ref}", "      /end AXIS_DESCR"]
            else:
                vals = ax.values or list(range(n))
                lines += [f"      /begin AXIS_DESCR FIX_AXIS {_ident(ax.name) if ax.name else 'NO_INPUT_QUANTITY'} "
                          f"NO_COMPU_METHOD {n} {_f(min(vals))} {_f(max(vals))}"]
                if ax.unit:
                    lines.append(f"        PHYS_UNIT {_q(ax.unit)}")
                lines += ["        /begin FIX_AXIS_PAR_LIST " + " ".join(_f(v) for v in vals[:n]) +
                          " /end FIX_AXIS_PAR_LIST", "      /end AXIS_DESCR"]
        if m.endian != bo:
            lines.append(f"      BYTE_ORDER {'MSB_FIRST' if m.endian == 'be' else 'MSB_LAST'}")
        if m.unit:
            lines.append(f"      PHYS_UNIT {_q(m.unit)}")
        if m.digits is not None:
            lines.append(f'      FORMAT "%{m.digits + 6}.{m.digits}"')
        lines.append("    /end CHARACTERISTIC")
        body.extend(lines)
    for (f, o, unit), name in cms.items():
        body.append(f"    /begin COMPU_METHOD {name} \"\" LINEAR \"%.6\" {_q(unit)}\n      COEFFS_LINEAR {_f(f)} {_f(o)}"
                    f"\n    /end COMPU_METHOD")
    groups: dict[str, list[str]] = {}
    for m in pack.maps:
        if m.folder:
            groups.setdefault(m.folder, []).append(_ident(m.name))
    for g, names in groups.items():
        body.append(f"    /begin FUNCTION {_ident(g)} {_q(g)}\n      /begin DEF_CHARACTERISTIC " +
                    " ".join(names) + " /end DEF_CHARACTERISTIC\n    /end FUNCTION")
    out += list(layouts.values()) + body + ["  /end MODULE", "/end PROJECT", ""]
    return "\n".join(out)
