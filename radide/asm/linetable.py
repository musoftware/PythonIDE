"""Source-line debug information for FASM and MASM programs (gdb reads DWARF only).

NASM builds get their DWARF line table from the listing (radide/asm/dwarf.py). This module does the same for
the two assemblers whose own debug formats gdb cannot read:

* **FASM** writes no debug information into its output, but ``fasm -s file.fas`` dumps its *symbolic
  information* (format: FASM's TOOLS\\FAS.TXT): for every assembled line the preprocessed line (with the
  chain back to the source line that called a macro) and the ``$`` address. ``parse_fas()`` turns it into
  ``(file, line, address, size)`` rows of the project's own files.
* **MASM** (ml64 / ml ``/Zi``) writes CodeView into a PDB. The build also asks for a listing (``/Fl``) and a
  linker map (``/MAP``): ``parse_masm_listing()`` gives the offset of every source line in the module's code
  segment and ``parse_map()`` the final address of a procedure of that module, which fixes the module's base.

The rows become a DWARF 3 compile unit + line table per code range (``encode_units``):

* written as raw bytes and **added to the finished program** as new ``.debug_*`` sections
  (``inject()`` / ``pe_add_sections()``; objcopy would rewrite and break a FASM / link.exe image) when nothing else in it has DWARF - FASM ``format PE / PE64`` programs and link.exe output
  (gdb relocates the addresses itself when Windows loads the program elsewhere: ASLR);
* or written as a GNU as source whose addresses are relocations against a public symbol of the object
  (``gas_source()``) and linked with the program - FASM ``format MS64 COFF`` objects linked by gcc (the GUI
  Bridge forms), next to radgui.c's own DWARF.

The builder (radide/asm/build.py) leaves ``_build\\dwarf.ok`` when the program got its lines, so
``AsmPluginBase.debug_info()`` reports ``"line_info": "dwarf"`` and F5 lets gdb handle the breakpoints.
"""
from __future__ import annotations

import os
import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

DW_LANG_MIPS_ASSEMBLER = 0x8001
PRODUCER = "RAD IDE (radide/asm/linetable.py)"


# ====================================================================== DWARF encoder
class _Items:
    """A section as a list of pieces: bytes, ("label", n), ("diff4", end, start), ("secrel", label),
    ("addr", symbol | None, addend). ``to_bytes`` resolves them (symbol must be None), ``to_gas`` writes as."""

    def __init__(self, addr_size: int):
        self.asz = addr_size
        self.items: list = []

    def raw(self, b: bytes):
        self.items.append(bytes(b))

    def u8(self, *v):
        self.raw(bytes(x & 0xFF for x in v))

    def u16(self, v):
        self.raw(struct.pack("<H", v & 0xFFFF))

    def uleb(self, v: int):
        out = bytearray()
        while True:
            b = v & 0x7F
            v >>= 7
            out.append(b | (0x80 if v else 0))
            if not v:
                break
        self.raw(out)

    def sleb(self, v: int):
        out = bytearray()
        while True:
            b = v & 0x7F
            v >>= 7
            done = (v == 0 and not b & 0x40) or (v == -1 and b & 0x40)
            out.append(b | (0 if done else 0x80))
            if done:
                break
        self.raw(out)

    def cstr(self, s: str):
        self.raw(s.encode("utf-8", "replace") + b"\0")

    def label(self, name: str):
        self.items.append(("label", name))

    def diff4(self, end: str, start: str):
        self.items.append(("diff4", end, start))

    def secrel(self, label: str):
        self.items.append(("secrel", label))

    def addr(self, sym, addend: int):
        self.items.append(("addr", sym, int(addend)))


def _size(it, asz: int) -> int:
    if isinstance(it, bytes):
        return len(it)
    return {"label": 0, "diff4": 4, "secrel": 4, "addr": asz}[it[0]]


@dataclass
class Unit:
    """One compile unit = one contiguous code range. Addresses are (symbol or None, addend)."""
    name: str
    comp_dir: str
    files: list[str]                                         # file table (1-based in the rows)
    rows: list[tuple[int, int, tuple]] = field(default_factory=list)    # (file index, line, address)
    low: tuple = (None, 0)
    high: tuple = (None, 0)
    functions: list[tuple[str, tuple, tuple]] = field(default_factory=list)   # (name, low, high): gdb's frames


def encode_units(units: list[Unit], addr_size: int) -> dict[str, _Items]:
    """.debug_abbrev / .debug_info / .debug_line pieces of *units* (DWARF 3)."""
    ab, info, line = _Items(addr_size), _Items(addr_size), _Items(addr_size)
    ab.label("Lrad_abbrev")
    ab.uleb(1)
    ab.uleb(0x11)
    ab.u8(1)                                       # DW_TAG_compile_unit, children (the subprograms)
    for at, form in ((0x10, 0x06), (0x11, 0x01), (0x12, 0x01), (0x03, 0x08), (0x1B, 0x08), (0x25, 0x08),
                     (0x13, 0x05)):                # stmt_list data4, low/high_pc addr, name, comp_dir, producer, language
        ab.uleb(at)
        ab.uleb(form)
    ab.u8(0, 0)
    ab.uleb(2)
    ab.uleb(0x2E)
    ab.u8(0)                                       # DW_TAG_subprogram: name, low_pc, high_pc, external
    for at, form in ((0x03, 0x08), (0x11, 0x01), (0x12, 0x01), (0x3F, 0x0C)):
        ab.uleb(at)
        ab.uleb(form)
    ab.u8(0, 0, 0)
    for k, u in enumerate(units):
        # ---- .debug_info
        info.diff4(f"Lrad_info_end{k}", f"Lrad_info_start{k}")
        info.label(f"Lrad_info_start{k}")
        info.u16(3)
        info.secrel("Lrad_abbrev")
        info.u8(addr_size)
        info.uleb(1)
        info.secrel(f"Lrad_line{k}")
        info.addr(*u.low)
        info.addr(*u.high)
        info.cstr(u.name)
        info.cstr(u.comp_dir)
        info.cstr(PRODUCER)
        info.u16(DW_LANG_MIPS_ASSEMBLER)
        for fname, flow, fhigh in u.functions:
            info.uleb(2)
            info.cstr(fname)
            info.addr(*flow)
            info.addr(*fhigh)
            info.u8(1)
        info.u8(0)                                 # end of the compile unit's children
        info.label(f"Lrad_info_end{k}")
        # ---- .debug_line
        line.label(f"Lrad_line{k}")
        line.diff4(f"Lrad_line_end{k}", f"Lrad_line_start{k}")
        line.label(f"Lrad_line_start{k}")
        line.u16(3)
        line.diff4(f"Lrad_hdr_end{k}", f"Lrad_hdr_start{k}")
        line.label(f"Lrad_hdr_start{k}")
        line.u8(1, 1, -5, 14, 13)
        line.u8(0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0, 1)
        line.u8(0)                                 # no include directories
        for f in u.files:
            line.cstr(f)
            line.uleb(0)
            line.uleb(0)
            line.uleb(0)
        line.u8(0)
        line.label(f"Lrad_hdr_end{k}")
        cur_file, cur_line = 1, 1
        for fi, ln, a in u.rows:
            line.u8(0)
            line.uleb(1 + addr_size)
            line.u8(2)                             # DW_LNE_set_address
            line.addr(*a)
            if fi != cur_file:
                line.u8(4)                         # DW_LNS_set_file
                line.uleb(fi)
                cur_file = fi
            if ln != cur_line:
                line.u8(3)                         # DW_LNS_advance_line
                line.sleb(ln - cur_line)
                cur_line = ln
            line.u8(1)                             # DW_LNS_copy
        line.u8(0)
        line.uleb(1 + addr_size)
        line.u8(2)
        line.addr(*u.high)
        line.u8(0, 1, 1)                           # DW_LNE_end_sequence
        line.label(f"Lrad_line_end{k}")
    return {".debug_abbrev": ab, ".debug_info": info, ".debug_line": line}


def to_bytes(sections: dict[str, _Items]) -> dict[str, bytes]:
    """Raw section contents (absolute addresses only)."""
    out = {}
    for name, sec in sections.items():
        labels, pos = {}, 0
        for it in sec.items:
            if isinstance(it, tuple) and it[0] == "label":
                labels[it[1]] = pos
            pos += _size(it, sec.asz)
        all_labels = {}
        for s in sections.values():              # secrel to a label of another section: its offset there
            p = 0
            for it in s.items:
                if isinstance(it, tuple) and it[0] == "label":
                    all_labels[it[1]] = p
                p += _size(it, s.asz)
        buf = bytearray()
        for it in sec.items:
            if isinstance(it, bytes):
                buf += it
            elif it[0] == "diff4":
                buf += struct.pack("<I", labels[it[1]] - labels[it[2]])
            elif it[0] == "secrel":
                buf += struct.pack("<I", all_labels[it[1]])
            elif it[0] == "addr":
                if it[1] is not None:
                    raise ValueError("symbolic address in raw DWARF")
                buf += it[2].to_bytes(sec.asz, "little", signed=False)
        out[name] = bytes(buf)
    return out


def to_gas(sections: dict[str, _Items], note: str = "") -> str:
    """GNU as source (COFF) with the sections; symbolic addresses become relocations."""
    L = [f"# AUTO-GENERATED by RAD IDE - DWARF line information{(' for ' + note) if note else ''} "
         "(radide/asm/linetable.py)"]
    for name, sec in sections.items():
        L.append(f'\t.section {name},"dr"')
        for it in sec.items:
            if isinstance(it, bytes):
                if it:
                    L.append("\t.byte " + ",".join(str(b) for b in it))
            elif it[0] == "label":
                L.append(f"{it[1]}:")
            elif it[0] == "diff4":
                L.append(f"\t.long {it[1]} - {it[2]}")
            elif it[0] == "secrel":
                L.append(f"\t.secrel32 {it[1]}")
            elif it[0] == "addr":
                d = ".quad" if sec.asz == 8 else ".long"
                sym, add = it[1], it[2]
                if sym is None:
                    L.append(f"\t{d} {add}")
                else:
                    L.append(f"\t{d} {sym}{'+' if add >= 0 else '-'}{abs(add)}")
    L.append("")
    return "\n".join(L)


# ====================================================================== PE images
@dataclass
class PeInfo:
    bits: int
    image_base: int
    sections: list[tuple[str, int, int, int]]        # (name, VA (absolute), virtual size, characteristics)

    def code_ranges(self) -> list[tuple[int, int]]:
        return [(va, va + max(vs, 1)) for _n, va, vs, ch in self.sections if ch & 0x20000020]

    def is_code(self, address: int) -> bool:
        return any(a <= address < b for a, b in self.code_ranges())


def pe_info(path) -> PeInfo | None:
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if data[:2] != b"MZ" or len(data) < 0x40:
        return None
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        return None
    nsec, opt_size = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic == 0x20B:
        bits, base = 64, struct.unpack_from("<Q", data, opt + 24)[0]
    else:
        bits, base = 32, struct.unpack_from("<I", data, opt + 28)[0]
    secs = []
    sh = opt + opt_size
    for i in range(nsec):
        o = sh + 40 * i
        name = data[o:o + 8].rstrip(b"\0").decode("latin-1")
        vsize, va = struct.unpack_from("<II", data, o + 8)
        ch = struct.unpack_from("<I", data, o + 36)[0]
        secs.append((name, base + va, vsize, ch))
    return PeInfo(bits, base, secs)


def has_dwarf(path) -> bool:
    info = pe_info(path)
    if info is None:
        return False
    if any(n.startswith(".debug") for n, *_ in info.sections):
        return True
    return any(n.startswith("/") for n, *_ in info.sections)     # long names (.debug_*) live in the string table


# ====================================================================== FASM symbolic information
@dataclass
class FasRow:
    file: str            # as written in the .fas (main input file name, or the include file's name)
    line: int
    address: int         # PE: absolute $; COFF: offset in its section
    size: int
    section: int         # COFF: 1-based section index (0 = absolute)


@dataclass
class FasInfo:
    input_file: str
    output_file: str
    rows: list[FasRow]
    sections: list[str]                       # COFF section names (index 0 = section 1)
    symbols: list[tuple[str, int, int]]       # (name, value, section index - 0 = absolute) of defined symbols
    code_bits: int = 64


def _cstr(buf: bytes, off: int) -> str:
    end = buf.find(b"\0", off)
    return buf[off:end if end >= 0 else len(buf)].decode("utf-8", "replace")


def parse_fas(path) -> FasInfo | None:
    """Rows of the assembly dump of a .fas file (FASM ``-s``) with their source lines (macro lines belong to
    the line that called the macro)."""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return None
    if len(data) < 48 or struct.unpack_from("<I", data, 0)[0] != 0x1A736166:
        return None
    hlen = struct.unpack_from("<H", data, 6)[0]
    f = struct.unpack_from("<14I", data, 8) if hlen >= 64 else struct.unpack_from("<10I", data, 8) + (0, 0, 0, 0)
    in_off, out_off, str_off, str_len, sym_off, sym_len, pre_off, pre_len, dump_off, dump_len = f[:10]
    sec_off, sec_len = f[10], f[11]
    strings = data[str_off:str_off + str_len]
    pre = data[pre_off:pre_off + pre_len]
    input_file, output_file = _cstr(strings, in_off), _cstr(strings, out_off)
    sections = [_cstr(strings, struct.unpack_from("<I", data, sec_off + 4 * i)[0])
                for i in range(sec_len // 4)] if sec_len else []

    def source_of(lo: int):
        for _ in range(100):
            if lo + 16 > len(pre):
                return None
            fname, ln, a, _b = struct.unpack_from("<IIII", pre, lo)
            if ln & 0x80000000:                    # generated by a macro: go to the line that invoked it
                if a == lo:
                    return None
                lo = a
                continue
            return (input_file if fname == 0 else _cstr(pre, fname)), ln
        return None

    symbols = []
    for i in range(sym_len // 32):
        o = sym_off + 32 * i
        value, flags, _size, vtype, _sib, _p1, _p2, rel, name_ref, _line = struct.unpack_from("<QHBbIHHIII", data, o)
        if not flags & 1 or flags & 0x402 or rel & 0x80000000 or not name_ref:
            continue                               # undefined, assembly-time variable, marker, external
        if name_ref & 0x80000000:
            name = _cstr(strings, name_ref & 0x7FFFFFFF)
        else:
            n = pre[name_ref] if name_ref < len(pre) else 0
            name = pre[name_ref + 1:name_ref + 1 + n].decode("utf-8", "replace")
        symbols.append((name, value, (rel & 0x7FFFFFFF) if vtype != 0 else 0))

    rows: list[FasRow] = []
    if not dump_len:
        return FasInfo(input_file, output_file, rows, sections, symbols)
    count = (dump_len - 4) // 28
    raw = [struct.unpack_from("<IIQIIBBBB", data, dump_off + 28 * i) for i in range(count)]
    end_out = struct.unpack_from("<I", data, dump_off + 28 * count)[0]
    bits = 64
    for i, (out, line_off, addr, _sib, rel, vtype, code, flags, high) in enumerate(raw):
        nxt = raw[i + 1][0] if i + 1 < count else end_out
        size = nxt - out
        if flags & 3 or size <= 0:                 # virtual block / not in the output / no bytes
            continue
        src = source_of(line_off)
        if src is None:
            continue
        section = (rel & 0x7FFFFFFF) if (vtype != 0 and not rel & 0x80000000) else 0
        bits = code or bits
        rows.append(FasRow(src[0], src[1], addr | (high << 64), size, section))
    return FasInfo(input_file, output_file, rows, sections, symbols, bits)


def _project_file(name: str, folder: Path, skip=("radgui_fasm.inc",)) -> str:
    """The path of *name* relative to *folder* when it is one of the project's own files, else ""."""
    p = Path(name)
    if not p.is_absolute():
        p = folder / p
    try:
        rel = p.resolve().relative_to(folder.resolve())
    except (OSError, ValueError):
        return ""
    if rel.name.lower() in skip or rel.parts[0].lower() == "_build":
        return ""
    return rel.as_posix()


def _units_from_rows(rows: list[tuple[str, int, int, int]], comp_dir: str, name: str, anchor=None,
                     gap: int = 0x10000) -> list[Unit]:
    """Group (file, line, address, size) rows (sorted by address) into units of contiguous code."""
    rows = sorted(rows, key=lambda r: r[2])
    units: list[Unit] = []
    cur: Unit | None = None
    end = 0
    for f, ln, a, size in rows:
        if cur is None or a - end > gap or a < end - 0:
            if cur is not None:
                cur.high = (anchor, end)
            cur = Unit(name, comp_dir, [], low=(anchor, a))
            units.append(cur)
        if f not in cur.files:
            cur.files.append(f)
        fi = cur.files.index(f) + 1
        if not cur.rows or cur.rows[-1][2][1] != a:
            if not cur.rows or (cur.rows[-1][0], cur.rows[-1][1]) != (fi, ln):
                cur.rows.append((fi, ln, (anchor, a)))
        else:
            continue
        end = max(end, a + size)
    if cur is not None:
        cur.high = (anchor, end)
    return units


def add_functions(units: list[Unit], labels: list[tuple[str, int]], anchor=None) -> None:
    """Give each unit the subprograms of the *labels* (name, address) inside it: a label's code runs to the next
    label (gdb then names the frames and ``next`` steps over calls)."""
    for u in units:
        lo, hi = u.low[1], u.high[1]
        inside = sorted({(a, n) for n, a in labels if lo <= a < hi})
        for i, (a, n) in enumerate(inside):
            end = inside[i + 1][0] if i + 1 < len(inside) else hi
            u.functions.append((n, (anchor, a), (anchor, end)))


def _code_labels(names_values, is_code) -> list[tuple[str, int]]:
    return [(n, v) for n, v in names_values if "." not in n and re.fullmatch(r"[A-Za-z_@$?][\w@$?]*", n)
            and is_code(v)]


def fasm_pe_units(fas: FasInfo, exe, folder) -> list[Unit]:
    """Units of a FASM ``format PE / PE64`` program (absolute addresses inside its code sections)."""
    folder = Path(folder)
    info = pe_info(exe)
    if info is None:
        return []
    rows = []
    for r in fas.rows:
        rel = _project_file(r.file, folder)
        if rel and info.is_code(r.address):
            rows.append((rel, r.line, r.address, r.size))
    units = _units_from_rows(rows, str(folder).replace("\\", "/"), Path(fas.input_file).name)
    add_functions(units, _code_labels([(n, v) for n, v, _s in fas.symbols], info.is_code))
    return units


def coff_public_names(obj) -> set[str]:
    """Names of the external (public) symbols defined in a COFF object (empty when it cannot be read)."""
    import struct
    try:
        data = Path(obj).read_bytes()
        symtab, nsyms = struct.unpack_from("<II", data, 8)
        strtab = symtab + nsyms * 18
        out, i = set(), 0
        while i < nsyms:
            raw = data[symtab + i * 18: symtab + i * 18 + 18]
            sect, _typ, cls, aux = struct.unpack_from("<hHBB", raw, 12)
            if raw[:4] == bytes(4):
                name = _cstr(data, strtab + struct.unpack_from("<I", raw, 4)[0])
            else:
                name = raw[:8].rstrip(bytes(1)).decode("utf-8", "replace")
            if cls == 2 and sect > 0:
                out.add(name)
            i += 1 + aux
        return out
    except (OSError, struct.error, ValueError):
        return set()


def fasm_coff_units(fas: FasInfo, folder) -> list[Unit]:
    """Units of a FASM ``format MS64 COFF`` object: addresses relative to a public label of the code section
    (the section itself has no symbol another object can refer to)."""
    folder = Path(folder)
    units: list[Unit] = []
    code_secs = {i + 1 for i, n in enumerate(fas.sections) if n.lower().startswith((".text", "code", ".code"))}
    for sec in sorted(code_secs):
        anchors = [(n, v) for n, v, s in fas.symbols if s == sec and re.fullmatch(r"[A-Za-z_][\w@$?]*", n)]
        public = coff_public_names(fas.output_file)
        if public:              # a label that is not public cannot be referred to from the debug object
            anchors = [a for a in anchors if a[0] in public]
        if not anchors:
            continue
        sym, base = anchors[0]
        rows = []
        for r in fas.rows:
            rel = _project_file(r.file, folder)
            if rel and r.section == sec:
                rows.append((rel, r.line, r.address - base, r.size))
        sec_units = _units_from_rows(rows, str(folder).replace("\\", "/"), Path(fas.input_file).name, sym)
        add_functions(sec_units, [(n, v - base) for n, v, s in fas.symbols if s == sec and "." not in n])
        units += sec_units
    return units


# ====================================================================== MASM listing + map
_ML_LINE = re.compile(r"^ ([0-9A-Fa-f]{8})\s(.*)$")


def parse_masm_listing(text: str, source_lines: list[str]) -> tuple[list[tuple[int, int, int]], dict[str, int]]:
    """([(1-based source line, offset in the code segment, bytes)], {proc name: offset}) of an ml / ml64
    listing (``/Fl /Sa``). Listing lines are matched to the source in order; macro expansion lines (a nesting
    digit before the text) and generated code (``*``: INVOKE, .IF ...) belong to the line that produced them;
    lines of include files (``C``) are skipped."""
    rows: list[tuple[int, int, int]] = []
    procs: dict[str, int] = {}
    src = [s.strip() for s in source_lines]
    si = 0                                      # next source line to match
    cur_line = 0
    in_code = False
    for raw in text.splitlines():
        if raw.startswith(("Microsoft (R)", "\f")) or re.match(r"^\S.*Page \d+ - \d+\s*$", raw):
            continue
        # column 33+ is the source text (after the address / bytes columns, tabs to 32)
        expanded = raw.expandtabs(8)
        head, body = expanded[:32], expanded[32:]
        marker = ""
        mm = re.match(r"^(\s*[0-9A-Fa-f]{8}.*?|\s*)(?:\s([C*1-9]))?$", head.rstrip())
        if mm and mm.group(2):
            marker = mm.group(2)
        text_part = body.strip()
        off_m = _ML_LINE.match(raw)
        offset = int(off_m.group(1), 16) if off_m else None
        nbytes = 0
        if off_m:
            hexes = re.findall(r"\b[0-9A-Fa-f]{2}\b", head[10:])
            nbytes = len(hexes)
            more = re.findall(r"[0-9A-Fa-f]{8}", head[10:])
            nbytes += 4 * len(more)
        if not text_part:                                   # a continuation line (more bytes) or empty
            continue
        if marker == "C":
            continue
        if marker and (marker.isdigit() or marker == "*"):
            line_no = cur_line                              # macro / INVOKE expansion (/Sa): the calling line
        else:
            line_no = 0
            for j in range(si, min(len(src), si + 400)):
                if src[j] and (src[j] == text_part or src[j].replace("\t", " ").split() == text_part.split()):
                    line_no = j + 1
                    si = j + 1
                    break
            if not line_no:
                continue
            cur_line = line_no
        code = text_part.split(";", 1)[0].strip()
        low = code.lower()
        if re.match(r"^\.code\b", low) or re.match(r"^\w+\s+segment\b.*('code'|\bexecute\b)", low) or \
                re.match(r"^_text\s+segment\b", low):
            in_code = True
            continue
        if re.match(r"^\.(data|data\?|const|fardata|fardata\?|stack)\b", low) or \
                (re.match(r"^\w+\s+segment\b", low) and not re.match(r"^_text\b", low)):
            in_code = False
            continue
        pm = re.match(r"^([A-Za-z_@$?][\w@$?]*)\s+proc\b", code, re.I)
        if pm and offset is not None and in_code:
            procs[pm.group(1)] = offset
        if in_code and offset is not None and nbytes:
            rows.append((line_no, offset, nbytes))
    # one row per offset, sorted
    seen, out = set(), []
    for ln, off, n in sorted(rows, key=lambda r: r[1]):
        if off in seen:
            continue
        seen.add(off)
        out.append((ln, off, n))
    return out, procs


def parse_map(text: str) -> dict[str, int]:
    """{public / static symbol: absolute address (Rva+Base)} of a link.exe map file."""
    out: dict[str, int] = {}
    for line in text.splitlines():
        m = re.match(r"^\s*[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8}\s+(\S+)\s+([0-9A-Fa-f]{8,16})\b", line)
        if m:
            out.setdefault(m.group(1), int(m.group(2), 16))
    return out


def map_address(symbols: dict[str, int], name: str) -> int | None:
    """Address of a MASM procedure in the map: ``name``, ``_name`` (cdecl) or ``_name@N`` (stdcall)."""
    if name in symbols:
        return symbols[name]
    for k, v in symbols.items():
        if k == "_" + name or re.fullmatch(rf"_?{re.escape(name)}@\d+", k):
            return v
    return None


def masm_units(sources: list[str], build_dir, folder, map_file) -> list[Unit]:
    """Units of a MASM program from the listings ``_build\\<m>.lst`` and the linker map."""
    folder, build_dir = Path(folder), Path(build_dir)
    try:
        symbols = parse_map(Path(map_file).read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return []
    units: list[Unit] = []
    for src in sources:
        lst = build_dir / f"{Path(src).stem}.lst"
        try:
            lines = (folder / src).read_text(encoding="utf-8", errors="replace").splitlines()
            rows, procs = parse_masm_listing(lst.read_text(encoding="utf-8", errors="replace"), lines)
        except OSError:
            continue
        base = None
        for name, off in procs.items():
            a = map_address(symbols, name)
            if a is not None:
                base = a - off
                break
        if base is None or not rows:
            continue
        rel = Path(src).as_posix()
        mod_units = _units_from_rows([(rel, ln, base + off, n) for ln, off, n in rows],
                                     str(folder).replace("\\", "/"), Path(src).name)
        add_functions(mod_units, [(name, base + off) for name, off in procs.items()])
        units += mod_units
    return units


# ====================================================================== writing
def _align(v: int, a: int) -> int:
    return (v + a - 1) // a * a if a else v


def pe_add_sections(exe, sections: dict[str, bytes]) -> bool:
    """Append *sections* (discardable, read-only, like the .debug_* sections of a gcc program) to the PE image
    *exe*. Names longer than 8 characters go to a COFF string table (``/<offset>``), as GNU ld writes them.
    objcopy is not used: it rewrites a FASM or link.exe image and breaks it."""
    path = Path(exe)
    try:
        data = bytearray(path.read_bytes())
    except OSError:
        return False
    if data[:2] != b"MZ":
        return False
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        return False
    fh = pe + 4
    nsec = struct.unpack_from("<H", data, fh + 2)[0]
    symptr, nsyms = struct.unpack_from("<II", data, fh + 8)
    opt_size = struct.unpack_from("<H", data, fh + 16)[0]
    opt = fh + 20
    sect_align, file_align = struct.unpack_from("<II", data, opt + 32)
    size_of_headers = struct.unpack_from("<I", data, opt + 60)[0]
    sh = opt + opt_size
    old = []
    for i in range(nsec):
        o = sh + 40 * i
        vsize, va, rsize, rptr = struct.unpack_from("<IIII", data, o + 8)
        old.append((data[o:o + 8], vsize, va, rsize, rptr))
    if any(r[0].rstrip(b"\0").decode("latin-1") == n[:8] or r[0].startswith(b"/") for r in old for n in sections):
        return False                                   # already has debug sections (or long names)
    if symptr and nsyms:
        return False                                   # a COFF symbol table: a gcc / ld program (has its own DWARF)
    first_raw = min([r[4] for r in old if r[4]] or [size_of_headers])
    need = sh + 40 * (nsec + len(sections))
    if need > min(first_raw, size_of_headers):
        # no room for the new section headers (FASM fills the header block exactly): make the header block
        # bigger and move the sections' file data (their RVAs do not change)
        grow = _align(need - first_raw, file_align)
        first_va = min([r[2] for r in old] or [sect_align])
        if size_of_headers + grow > first_va:
            return False
        data[first_raw:first_raw] = b"\0" * grow
        for i, r in enumerate(old):
            if r[4]:
                struct.pack_into("<I", data, sh + 40 * i + 20, r[4] + grow)
        old = [(r[0], r[1], r[2], r[3], r[4] + grow if r[4] else 0) for r in old]
        size_of_headers += grow
        struct.pack_into("<I", data, opt + 60, size_of_headers)
        if symptr:
            symptr += grow
        # the debug directory (link.exe: CodeView / PDB path) holds file offsets too
        magic = struct.unpack_from("<H", data, opt)[0]
        dd = opt + (112 if magic == 0x20B else 96)
        ndirs = struct.unpack_from("<I", data, dd - 4)[0]
        if ndirs > 6:
            rva, size = struct.unpack_from("<II", data, dd + 6 * 8)
            for _n, vsize, va, rsize, rptr in old:
                if rva and va <= rva < va + max(vsize, rsize):
                    off = rptr + (rva - va)
                    for k in range(size // 28):
                        e = off + 28 * k + 24
                        p = struct.unpack_from("<I", data, e)[0]
                        if p:
                            struct.pack_into("<I", data, e, p + grow)
                    break
    # existing COFF string table (an image normally has none; keep it if there is one)
    strtab = bytearray(b"\0\0\0\0")
    if symptr:
        st = symptr + 18 * nsyms
        if st + 4 <= len(data):
            n = struct.unpack_from("<I", data, st)[0]
            strtab = bytearray(data[st:st + n]) if n >= 4 else strtab
        del data[symptr:]                              # rewritten below
    end_raw = max([r[4] + r[3] for r in old] + [size_of_headers])
    del data[end_raw:]                                 # (nothing of the image lives after the last section)
    next_va = max(_align(r[2] + max(r[1], r[3]), sect_align) for r in old) if old else _align(size_of_headers, sect_align)
    raw_ptr = _align(len(data), file_align)
    data += b"\0" * (raw_ptr - len(data))
    headers = []
    for name, blob in sections.items():
        enc = name.encode("ascii")
        if len(enc) > 8:
            off = len(strtab)
            strtab += enc + b"\0"
            field = f"/{off}".encode("ascii")
        else:
            field = enc
        rsize = _align(len(blob), file_align)
        headers.append(struct.pack("<8sIIIIIIHHI", field.ljust(8, b"\0"), len(blob), next_va, rsize, raw_ptr,
                                   0, 0, 0, 0, 0x42000040))     # INITIALIZED_DATA | DISCARDABLE | READ
        data += blob + b"\0" * (rsize - len(blob))
        raw_ptr += rsize
        next_va = _align(next_va + len(blob), sect_align)
    for i, h in enumerate(headers):
        o = sh + 40 * (nsec + i)
        data[o:o + 40] = h
    struct.pack_into("<H", data, fh + 2, nsec + len(headers))
    struct.pack_into("<I", data, opt + 56, next_va)          # SizeOfImage
    struct.pack_into("<I", data, opt + 64, 0)                # CheckSum (not checked for programs)
    struct.pack_into("<I", strtab, 0, len(strtab))
    struct.pack_into("<II", data, fh + 8, len(data), 0)      # PointerToSymbolTable -> string table, no symbols
    data += strtab
    try:
        tmp = path.with_name(path.name + ".dwarf.tmp")
        tmp.write_bytes(bytes(data))
        os.replace(tmp, path)
    except OSError:
        return False
    return True


def inject(exe, units: list[Unit], log=None) -> bool:
    """Add the units as .debug_abbrev / .debug_info / .debug_line sections to the program *exe*."""
    info = pe_info(exe)
    if info is None or not units:
        return False
    data = to_bytes(encode_units(units, 8 if info.bits == 64 else 4))
    ok = pe_add_sections(exe, data)
    if not ok and log:
        log(f"(no line debug information: cannot add the DWARF sections to {Path(exe).name})")
    return ok


def gas_source(units: list[Unit], bits: int = 64, note: str = "") -> str:
    return to_gas(encode_units(units, 8 if bits == 64 else 4), note)


__all__ = ["FasInfo", "FasRow", "PeInfo", "Unit", "encode_units", "fasm_coff_units", "fasm_pe_units", "gas_source",
           "has_dwarf", "inject", "map_address", "masm_units", "parse_fas", "parse_map", "parse_masm_listing",
           "pe_info", "to_bytes", "to_gas"]
