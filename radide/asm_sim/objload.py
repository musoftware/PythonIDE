"""Assemble NASM sources into object files and load them into one in-memory image for the emulator.

* ``assemble_nasm(text, path, fmt)`` runs NASM (radide/asm/toolchain: the IDE's own copy, downloaded when
  missing) on the editor text with a listing (``-l``); include files resolve against the file's folder.
* ``parse_coff`` / ``parse_elf`` read the relocatable object NASM wrote (win32 / win64 COFF, elf32 / elf64):
  sections, symbols (NASM keeps every label, also local ``main.loop`` ones) and relocations.
* ``parse_listing`` gives, for every source line, the section, offset and size of the bytes it produced
  (macro expansions belong to the line that calls the macro; lines of %include files to the include line).
* ``link`` lays the sections of all objects out from ``BASE`` (one page-aligned block each), resolves the
  global symbols between the objects, sends every undefined symbol to a stub slot (radide/asm_sim/stubs.py)
  and applies the relocations. The result (``Image``) maps addresses to source lines and to labels (with the
  size of each data label = up to the next label: the bounds of the buffer checks).

Nothing here needs Qt or Unicorn.
"""
from __future__ import annotations

import bisect
import os
import re
import struct
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

BASE = 0x00401000
PAGE = 0x1000
STUB_BASE = 0x0F000000
STUB_SLOT = 16
IAT_BASE = STUB_BASE + 0x8000        # pointer slots of __imp_Name symbols (call [rel __imp_MessageBoxA])


# ============================================================================ objects
@dataclass
class ObjSection:
    name: str
    data: bytearray
    size: int
    execute: bool = False
    write: bool = True
    nobits: bool = False
    relocs: list = field(default_factory=list)          # [(offset, symbol index, type, addend | None)]
    addr: int = 0                                       # after link
    index: int = 0                                      # 1-based (COFF) / ELF section index


@dataclass
class ObjSymbol:
    name: str
    section: int                                        # 0 = undefined, -1 = absolute, else section index
    value: int
    is_global: bool = False
    is_section: bool = False


@dataclass
class ObjFile:
    path: str
    fmt: str                                            # win32 | win64 | elf32 | elf64
    sections: list[ObjSection] = field(default_factory=list)
    symbols: list = field(default_factory=list)         # index -> ObjSymbol | None (COFF aux slots)
    rows: list = field(default_factory=list)            # listing: [(line, section name, offset, size)]
    source_lines: list = field(default_factory=list)

    @property
    def bits(self) -> int:
        return 64 if self.fmt.endswith("64") else 32

    def section_by_index(self, idx: int) -> ObjSection | None:
        for s in self.sections:
            if s.index == idx:
                return s
        return None


class LoadError(Exception):
    pass


def parse_coff(data: bytes, path: str = "") -> ObjFile:
    machine, nsec, _ts, symptr, nsym, opt, _ch = struct.unpack_from("<HHIIIHH", data, 0)
    fmt = "win64" if machine == 0x8664 else "win32" if machine == 0x14C else ""
    if not fmt:
        raise LoadError(f"unsupported COFF machine {machine:#x}")
    strtab_off = symptr + nsym * 18
    strtab = data[strtab_off:] if symptr else b""

    def coff_str(off: int) -> str:
        end = strtab.find(b"\0", off)
        return strtab[off:end if end >= 0 else None].decode("latin-1")

    obj = ObjFile(path, fmt)
    off = 20 + opt
    for i in range(nsec):
        raw = data[off:off + 40]
        name = raw[:8].rstrip(b"\0").decode("latin-1")
        if name.startswith("/") and name[1:].isdigit():
            name = coff_str(int(name[1:]))
        vsize, _va, rsize, rptr, relptr, _ln, nrel, _nln, ch = struct.unpack_from("<IIIIIIHHI", raw, 8)
        nobits = bool(ch & 0x80) and not rptr
        size = rsize or vsize
        sec = ObjSection(name, bytearray(size if nobits else data[rptr:rptr + rsize]), size,
                         execute=bool(ch & 0x20000000) or bool(ch & 0x20), write=bool(ch & 0x80000000),
                         nobits=nobits, index=i + 1)
        if ch & 0x02000000:                      # IMAGE_SCN_MEM_DISCARDABLE (debug sections)
            sec.name = "~" + name
        for k in range(nrel):
            va, si, typ = struct.unpack_from("<IIH", data, relptr + k * 10)
            sec.relocs.append((va, si, typ, None))
        obj.sections.append(sec)
        off += 40
    i = 0
    syms: list = []
    while i < nsym:
        raw = data[symptr + i * 18:symptr + i * 18 + 18]
        if raw[:4] == b"\0\0\0\0":
            name = coff_str(struct.unpack_from("<I", raw, 4)[0])
        else:
            name = raw[:8].rstrip(b"\0").decode("latin-1")
        value, secno, _typ, scl, naux = struct.unpack_from("<IhHBB", raw, 8)
        is_sec = scl == 3 and value == 0 and naux == 1 and secno > 0
        syms.append(ObjSymbol(name, secno, value, is_global=scl == 2, is_section=is_sec))
        syms.extend([None] * naux)
        i += 1 + naux
    obj.symbols = syms
    return obj


def parse_elf(data: bytes, path: str = "") -> ObjFile:
    if data[:4] != b"\x7fELF":
        raise LoadError("not an ELF file")
    is64 = data[4] == 2
    obj = ObjFile(path, "elf64" if is64 else "elf32")
    if is64:
        shoff, = struct.unpack_from("<Q", data, 0x28)
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x3A)
    else:
        shoff, = struct.unpack_from("<I", data, 0x20)
        shentsize, shnum, shstrndx = struct.unpack_from("<HHH", data, 0x2E)
    shdrs = []
    for i in range(shnum):
        o = shoff + i * shentsize
        if is64:
            name, typ, flags, _addr, off, size, link, info, _al, entsize = struct.unpack_from("<IIQQQQIIQQ", data, o)
        else:
            name, typ, flags, _addr, off, size, link, info, _al, entsize = struct.unpack_from("<IIIIIIIIII", data, o)
        shdrs.append((name, typ, flags, off, size, link, info, entsize))
    shstr = shdrs[shstrndx]

    def sname(n: int, tab) -> str:
        base = tab[3]
        end = data.find(b"\0", base + n)
        return data[base + n:end].decode("latin-1")

    by_index: dict[int, ObjSection] = {}
    for i, (name, typ, flags, off, size, link, info, entsize) in enumerate(shdrs):
        if typ in (1, 8) and flags & 2:          # PROGBITS / NOBITS with SHF_ALLOC
            sec = ObjSection(sname(name, shstr), bytearray(size if typ == 8 else data[off:off + size]), size,
                             execute=bool(flags & 4), write=bool(flags & 1), nobits=typ == 8, index=i)
            by_index[i] = sec
            obj.sections.append(sec)
    symtab = next((h for h in shdrs if h[1] == 2), None)
    if symtab is not None:
        strtab = shdrs[symtab[5]]
        n = symtab[4] // symtab[7]
        for k in range(n):
            o = symtab[3] + k * symtab[7]
            if is64:
                st_name, st_info, _oth, shndx, value, _sz = struct.unpack_from("<IBBHQQ", data, o)
            else:
                st_name, value, _sz, st_info, _oth, shndx = struct.unpack_from("<IIIBBH", data, o)
            bind, typ = st_info >> 4, st_info & 0xF
            sec = 0 if shndx == 0 else -1 if shndx >= 0xFF00 else shndx
            obj.symbols.append(ObjSymbol(sname(st_name, strtab) if st_name else "", sec, value,
                                         is_global=bind in (1, 2), is_section=typ == 3))
    for name, typ, flags, off, size, link, info, entsize in shdrs:
        if typ in (4, 9) and info in by_index:   # RELA / REL for an allocated section
            sec = by_index[info]
            n = size // entsize
            for k in range(n):
                o = off + k * entsize
                if is64:
                    r_off, r_info = struct.unpack_from("<QQ", data, o)
                    addend = struct.unpack_from("<q", data, o + 16)[0] if typ == 4 else None
                    si, rt = r_info >> 32, r_info & 0xFFFFFFFF
                else:
                    r_off, r_info = struct.unpack_from("<II", data, o)
                    addend = struct.unpack_from("<i", data, o + 8)[0] if typ == 4 else None
                    si, rt = r_info >> 8, r_info & 0xFF
                sec.relocs.append((r_off, si, rt, addend))
    return obj


# ============================================================================ listing
_LST_RX = re.compile(r"^\s*(\d+)\s(.{8})\s(\S*)\s+(<\d+>)?(.*)$")
_SECTION_RX = re.compile(r"^\s*\[?\s*(?:section|segment)\s+([.\w$@]+)", re.I)


def _byte_count(hexpart: str) -> int:
    m = re.match(r"<res\s+([0-9A-Fa-f]+)h?>", hexpart)
    if m:
        return int(m.group(1), 16)
    rep = 1
    m = re.search(r"<rep\s+([0-9A-Fa-f]+)h>", hexpart)
    if m:
        rep = int(m.group(1), 16)
        hexpart = hexpart[:m.start()]
    if set(hexpart) <= set("?"):
        return len(hexpart) // 2
    digits = re.sub(r"[^0-9A-Fa-f?]", "", hexpart)
    return (len(digits) // 2) * rep


def parse_listing(text: str, source_lines: list[str] | None = None, default: str = ".text") -> list:
    """[(1-based source line, section, offset, byte count)] for every line that produced bytes."""
    rows = []
    section = default
    user_section = default
    last_top = 0
    top_is_include = False
    for raw in text.splitlines():
        m = _LST_RX.match(raw)
        if not m:
            continue
        line_no, off, hexpart, depth, src = int(m.group(1)), m.group(2), m.group(3), m.group(4), m.group(5)
        body = src
        if depth is None:
            last_top = line_no
            if source_lines is not None and 0 < line_no <= len(source_lines):
                body = source_lines[line_no - 1]
            top_is_include = bool(re.match(r"^\s*%\s*include\b", body, re.I))
        code = body.split(";", 1)[0]
        sm = _SECTION_RX.match(code)
        if sm and (depth is None or not top_is_include):
            section = sm.group(1).lower()
            if not code.lstrip().startswith("["):
                user_section = section
            continue
        if re.search(r"__\??SECT\??__", code):
            section = user_section
            continue
        off = off.strip()
        if not re.fullmatch(r"[0-9A-Fa-f]{8}", off):
            continue
        n = _byte_count(hexpart)
        if not n and not hexpart.startswith("<res"):
            continue
        target = line_no if depth is None else last_top
        rows.append((target, section, int(off, 16), n))
    return rows


# ============================================================================ NASM
@dataclass
class AsmOutput:
    ok: bool
    obj: ObjFile | None = None
    errors: list = field(default_factory=list)          # [(line, message)]
    warnings: list = field(default_factory=list)
    tool_missing: bool = False


_ERR_RX = re.compile(r"^(.*?):(\d+):\s*(error|warning|fatal)\s*:\s*(.*)$", re.I)


def nasm_path(download: bool = False, log=None) -> str:
    try:
        from ..asm import toolchain
        return toolchain.ensure("nasm", log=log or (lambda _t: None), download=download)
    except Exception:  # noqa: BLE001
        return ""


def assemble_nasm(text: str, path: str, fmt: str, download: bool = True, include_dirs=(), log=None) -> AsmOutput:
    nasm = nasm_path(download, log)
    if not nasm:
        return AsmOutput(False, errors=[(0, "NASM is not available")], tool_missing=True)
    src_path = Path(path) if path else None
    folder = src_path.parent if src_path else Path.cwd()
    with tempfile.TemporaryDirectory(prefix="radide-sim-") as tmp:
        t = Path(tmp)
        name = (src_path.stem if src_path else "snippet") + ".asm"
        src = t / name
        src.write_text(text, encoding="utf-8", newline="\n")
        obj, lst = t / "out.obj", t / "out.lst"
        args = [nasm, "-f", fmt, "-o", str(obj), "-l", str(lst)]
        for d in [folder, *include_dirs]:
            args.append("-I" + str(d).rstrip("\\/") + os.sep)
        args.append(str(src))
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=60, cwd=str(folder),
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.TimeoutExpired) as e:
            return AsmOutput(False, errors=[(0, f"NASM could not run: {e}")])
        errors, warnings = [], []
        for ln in (r.stderr + "\n" + r.stdout).splitlines():
            m = _ERR_RX.match(ln.strip())
            if m:
                same = Path(m.group(1)).name.lower() == name.lower()
                row = (int(m.group(2)) if same else 0, m.group(4) if same else f"{Path(m.group(1)).name}({m.group(2)}): {m.group(4)}")
                (warnings if m.group(3).lower() == "warning" else errors).append(row)
        if r.returncode != 0 or not obj.exists():
            return AsmOutput(False, errors=errors or [(0, (r.stderr or r.stdout).strip()[:500])], warnings=warnings)
        data = obj.read_bytes()
        o = parse_elf(data, str(path)) if fmt.startswith("elf") else parse_coff(data, str(path))
        o.source_lines = text.splitlines()
        try:
            o.rows = parse_listing(lst.read_text(encoding="utf-8", errors="replace"), o.source_lines)
        except OSError:
            o.rows = []
        return AsmOutput(True, o, warnings=warnings)


# ============================================================================ image
@dataclass
class Label:
    name: str
    addr: int
    size: int
    section: str
    file: str
    line: int
    code: bool
    is_global: bool = False


@dataclass
class Region:
    start: int
    size: int
    name: str                                           # section name
    file: str
    execute: bool
    write: bool
    data: bytes = b""


@dataclass
class Image:
    bits: int
    fmt: str
    regions: list[Region] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)    # sorted by address
    globals: dict = field(default_factory=dict)          # name -> address
    externs: dict = field(default_factory=dict)          # name -> stub address
    stub_names: dict = field(default_factory=dict)       # stub address -> name
    iat: dict = field(default_factory=dict)              # pointer slot address -> stub address
    line_rows: list = field(default_factory=list)        # sorted [(addr, size, file, line)] of code
    data_rows: list = field(default_factory=list)        # [(addr, size, file, line)] of data lines
    reloc_targets: dict = field(default_factory=dict)    # address of an instruction byte -> target address
    files: list = field(default_factory=list)
    sources: dict = field(default_factory=dict)          # file -> source lines
    _starts: list = field(default_factory=list)
    _lstarts: list = field(default_factory=list)

    def finish(self) -> None:
        self.labels.sort(key=lambda lab: lab.addr)
        self._lstarts = [lab.addr for lab in self.labels]
        self.line_rows.sort()
        self._starts = [r[0] for r in self.line_rows]

    # -- lookups
    def line_of(self, addr: int):
        """(file, line) of the code byte at *addr*, or None."""
        i = bisect.bisect_right(self._starts, addr) - 1
        if i >= 0:
            a, n, f, ln = self.line_rows[i]
            if a <= addr < a + max(n, 1):
                return f, ln
        return None

    def addresses_of(self, file: str, line: int) -> list[int]:
        key = os.path.normcase(str(file))
        return [a for a, _n, f, ln in self.line_rows if ln == line and os.path.normcase(f) == key]

    def region_of(self, addr: int) -> Region | None:
        for r in self.regions:
            if r.start <= addr < r.start + r.size:
                return r
        return None

    def label_at(self, addr: int, code: bool | None = None) -> Label | None:
        """The label whose [addr, addr+size) contains *addr*."""
        i = bisect.bisect_right(self._lstarts, addr) - 1
        while i >= 0:
            lab = self.labels[i]
            if (code is None or lab.code == code) and lab.addr <= addr < lab.addr + max(lab.size, 1):
                return lab
            if lab.addr < addr and lab.addr + max(lab.size, 1) <= addr and (code is None or lab.code == code):
                return None
            i -= 1
        return None

    def proc_of(self, addr: int) -> Label | None:
        """The nearest non-local code label at or before *addr*."""
        i = bisect.bisect_right(self._lstarts, addr) - 1
        while i >= 0:
            lab = self.labels[i]
            if lab.code and "." not in lab.name.lstrip("."):
                r = self.region_of(lab.addr)
                if r is not None and r.start <= addr < r.start + r.size:
                    return lab
                return None
            i -= 1
        return None

    def label_named(self, name: str) -> Label | None:
        low = name.lower()
        for lab in self.labels:
            if lab.name.lower() == low:
                return lab
        return None

    def describe(self, addr: int) -> str:
        """"buf+3" / "main.loop" / ".data+0x10" / "0x00401000"."""
        lab = self.label_at(addr)
        if lab is not None:
            return lab.name if addr == lab.addr else f"{lab.name}+{addr - lab.addr}"
        r = self.region_of(addr)
        if r is not None:
            return f"{r.name}+{addr - r.start:#x}"
        return f"{addr:#010x}"

    def source_text(self, addr: int) -> str:
        """The source of the line that starts exactly at *addr* (comment / label removed), or ""."""
        i = bisect.bisect_right(self._starts, addr) - 1
        if i < 0 or self.line_rows[i][0] != addr:
            return ""
        _a, _n, f, ln = self.line_rows[i]
        lines = self.sources.get(f) or []
        if not 0 < ln <= len(lines):
            return ""
        s = lines[ln - 1].split(";", 1)[0].strip()
        return re.sub(r"^[A-Za-z_.?$@][\w.?$@]*:\s*", "", s)

    def code_end_line(self):
        """(file, line) of the last instruction of the program's code."""
        return (self.line_rows[-1][2], self.line_rows[-1][3]) if self.line_rows else None


def _align(v: int, a: int = PAGE) -> int:
    return (v + a - 1) & ~(a - 1)


def link(objs: list[ObjFile], stub_names=None) -> Image:
    """Lay out, resolve and relocate *objs* (stub slots for undefined symbols)."""
    if not objs:
        raise LoadError("nothing to link")
    img = Image(objs[0].bits, objs[0].fmt)
    addr = BASE
    for o in objs:
        img.files.append(o.path)
        img.sources[o.path] = o.source_lines
        for s in o.sections:
            if s.name.startswith("~") or s.name.lower().startswith((".debug", ".note", ".comment", ".drectve")):
                continue
            s.addr = addr
            addr = _align(addr + max(s.size, 1))
    # global symbols
    for o in objs:
        for sym in o.symbols:
            if sym is None or not sym.is_global or sym.section <= 0:
                continue
            sec = o.section_by_index(sym.section)
            if sec is not None and sec.addr:
                img.globals.setdefault(sym.name, sec.addr + sym.value)
    stub_next = STUB_BASE

    def resolve(o: ObjFile, si: int) -> int:
        sym = o.symbols[si] if 0 <= si < len(o.symbols) else None
        if sym is None:
            return 0
        if sym.section > 0:
            sec = o.section_by_index(sym.section)
            return (sec.addr if sec is not None else 0) + (0 if sym.is_section else sym.value)
        if sym.section == -1:
            return sym.value
        if sym.name in img.globals:
            return img.globals[sym.name]
        return stub_for(sym.name)

    def stub_for(name: str) -> int:
        nonlocal stub_next
        m = re.match(r"^(?:__imp_|_imp__)(.+)$", name)
        if m:
            slot = IAT_BASE + 8 * len(img.iat)
            if name not in img.externs:
                target = img.globals.get(m.group(1)) or stub_for(m.group(1))
                img.externs[name] = slot
                img.iat[slot] = target
            return img.externs[name]
        if name not in img.externs:
            img.externs[name] = stub_next
            img.stub_names[stub_next] = name
            stub_next += STUB_SLOT
        return img.externs[name]

    for o in objs:
        for s in o.sections:
            if not s.addr:
                continue
            for off, si, typ, addend in s.relocs:
                S = resolve(o, si)
                P = s.addr + off
                d = s.data
                if o.fmt == "win64":
                    if typ == 1:                                 # ADDR64
                        v = struct.unpack_from("<Q", d, off)[0] + S
                        struct.pack_into("<Q", d, off, v & 0xFFFFFFFFFFFFFFFF)
                    elif typ in (2, 3):                          # ADDR32 / ADDR32NB
                        v = struct.unpack_from("<I", d, off)[0] + S - (BASE - PAGE if typ == 3 else 0)
                        struct.pack_into("<I", d, off, v & 0xFFFFFFFF)
                    elif 4 <= typ <= 9:                          # REL32 .. REL32_5
                        a = struct.unpack_from("<i", d, off)[0]
                        struct.pack_into("<i", d, off, _s32(a + S - (P + 4 + (typ - 4))))
                        img.reloc_targets[P] = a + S
                    else:
                        continue
                elif o.fmt == "win32":
                    if typ in (6, 7):                            # DIR32 / DIR32NB
                        a = struct.unpack_from("<I", d, off)[0]
                        struct.pack_into("<I", d, off, (a + S - (BASE - PAGE if typ == 7 else 0)) & 0xFFFFFFFF)
                        img.reloc_targets[P] = (a + S) & 0xFFFFFFFF
                    elif typ == 0x14:                            # REL32
                        a = struct.unpack_from("<i", d, off)[0]
                        struct.pack_into("<i", d, off, _s32(a + S - (P + 4)))
                    else:
                        continue
                else:
                    a = addend if addend is not None else (
                        struct.unpack_from("<q" if o.fmt == "elf64" and typ == 1 else "<i", d, off)[0])
                    if typ == 1:                                 # R_X86_64_64 / R_386_32
                        if o.fmt == "elf64":
                            struct.pack_into("<Q", d, off, (S + a) & 0xFFFFFFFFFFFFFFFF)
                        else:
                            struct.pack_into("<I", d, off, (S + a) & 0xFFFFFFFF)
                        img.reloc_targets[P] = S + a
                    elif typ in (2, 4):                          # PC32 / PLT32
                        struct.pack_into("<i", d, off, _s32(S + a - P))
                        if o.fmt == "elf64":
                            img.reloc_targets[P] = S + a + 4
                    elif typ in (10, 11) and o.fmt == "elf64":   # R_X86_64_32 / 32S
                        struct.pack_into("<I", d, off, (S + a) & 0xFFFFFFFF)
                        img.reloc_targets[P] = S + a
    # regions, labels and lines
    for o in objs:
        name_of = {s.index: s for s in o.sections}
        for s in o.sections:
            if not s.addr:
                continue
            img.regions.append(Region(s.addr, _align(max(s.size, 1)), s.name, o.path, s.execute,
                                      s.write, bytes(s.data) if not s.nobits else bytes(s.size)))
        per_sec: dict[int, list[ObjSymbol]] = {}
        for sym in o.symbols:
            if sym is None or sym.is_section or sym.section <= 0 or not sym.name or sym.name.startswith(".."):
                continue
            if sym.name.lower() in (".text", ".data", ".bss", ".rdata", ".absolut", o.path):
                continue
            per_sec.setdefault(sym.section, []).append(sym)
        lines_by_off: dict[tuple[str, int], int] = {}
        for ln, sname, off, n in o.rows:
            lines_by_off.setdefault((sname, off), ln)
        for idx, syms in per_sec.items():
            sec = name_of.get(idx)
            if sec is None or not sec.addr:
                continue
            syms.sort(key=lambda x: x.value)
            for k, sym in enumerate(syms):
                nxt = next((x.value for x in syms[k + 1:] if x.value > sym.value), sec.size)
                img.labels.append(Label(sym.name, sec.addr + sym.value, max(0, nxt - sym.value), sec.name, o.path,
                                        _label_line(o, sym.name, lines_by_off.get((sec.name.lower(), sym.value), 0)),
                                        sec.execute, sym.is_global))
        sec_by_name = {}
        for s in o.sections:
            sec_by_name.setdefault(s.name.lower(), s)
        for ln, sname, off, n in o.rows:
            sec = sec_by_name.get(sname)
            if sec is None or not sec.addr:
                continue
            row = (sec.addr + off, n, o.path, ln)
            (img.line_rows if sec.execute else img.data_rows).append(row)
    img.finish()
    return img


def _label_line(o: ObjFile, name: str, fallback: int) -> int:
    short = name.rsplit(".", 1)[-1] if "." in name.lstrip(".") else name
    rx = re.compile(r"^\s*\.?" + re.escape(short.lstrip(".")) + r"\s*(:|\s+(db|dw|dd|dq|dt|do|dy|res[bwdqtoy]|times|equ)\b)",
                    re.I)
    best = 0
    for i, s in enumerate(o.source_lines, 1):
        if rx.match(s):
            best = i
            if fallback and abs(i - fallback) <= 1:
                return i
            break
    return best or fallback


def _s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v & 0x80000000 else v
