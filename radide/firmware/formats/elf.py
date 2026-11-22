"""ELF (32 / 64 bit, little / big endian) for firmware: PT_LOAD segments (at their physical = load addresses,
like objcopy -O binary), sections and the symbol table. Writing produces a minimal ELF32/64 executable with one
PT_LOAD per segment plus .shstrtab (enough for objcopy, Ghidra, flash tools and a round trip). Pure Python."""
from __future__ import annotations

import struct

from .memmap import MemoryMap, Segment, Symbol

MACHINES = {0: "none", 2: "SPARC", 3: "x86", 4: "M68K", 8: "MIPS", 20: "PowerPC", 21: "PowerPC64", 40: "ARM",
            42: "SuperH", 43: "SPARC v9", 44: "TriCore", 50: "IA-64", 53: "HC12 (68HC12)", 62: "x86-64",
            70: "HC11", 83: "AVR", 87: "V850 (NEC v850)", 88: "M32R", 92: "OpenRISC", 105: "MSP430",
            106: "Blackfin", 113: "Altera Nios II", 165: "8051", 183: "AArch64",
            192: "Renesas RH850", 243: "RISC-V", 0x9026: "V850 (old)"}
# ELF e_machine -> the CPU id of radide.firmware.analysis.arch
MACHINE_ARCH = {40: "arm", 20: "ppc", 44: "tricore", 53: "hc12", 42: "sh",
                87: "v850", 0x9026: "v850", 192: "v850", 4: "m68k", 165: "8051", 8: "mips", 3: "x86", 62: "x86-64",
                183: "arm64", 243: "riscv"}
EF_PPC_VLE_SECTION = 0x10000000      # SHF_PPC_VLE section flag (Freescale/NXP e200 VLE code)


class ElfFormatError(ValueError):
    pass


def looks_like(head: bytes) -> bool:
    return head[:4] == b"\x7fELF"


def parse(data: bytes, use_physical: bool = True) -> MemoryMap:
    try:
        return _parse(data, use_physical)
    except (struct.error, IndexError, OverflowError) as ex:     # tables pointing past the end of the file
        raise ElfFormatError(f"corrupted ELF file ({ex})") from None


def _parse(data: bytes, use_physical: bool) -> MemoryMap:
    if data[:4] != b"\x7fELF" or len(data) < 52:
        raise ElfFormatError("not an ELF file")
    cls, ei_data = data[4], data[5]
    if cls not in (1, 2) or ei_data not in (1, 2):
        raise ElfFormatError("unknown ELF class / byte order")
    e = "<" if ei_data == 1 else ">"
    is64 = cls == 2
    if is64:
        (e_type, e_machine, _ver, e_entry, e_phoff, e_shoff, e_flags, _ehsize, e_phentsize, e_phnum,
         e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from(e + "HHIQQQIHHHHHH", data, 16)
    else:
        (e_type, e_machine, _ver, e_entry, e_phoff, e_shoff, e_flags, _ehsize, e_phentsize, e_phnum,
         e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from(e + "HHIIIIIHHHHHH", data, 16)
    m = MemoryMap()
    m.start = e_entry
    m.header = MACHINES.get(e_machine, f"machine {e_machine}")
    m.meta.update(format="elf", elf_class=64 if is64 else 32, endian="little" if e == "<" else "big",
                  e_machine=e_machine, e_flags=e_flags, e_type=e_type, arch=MACHINE_ARCH.get(e_machine, ""))

    # ---- sections
    sections = []
    if e_shoff and e_shnum and e_shoff + e_shnum * e_shentsize <= len(data):
        for i in range(e_shnum):
            off = e_shoff + i * e_shentsize
            if is64:
                name, stype, flags, addr, soff, size, link, info, _al, entsize = struct.unpack_from(
                    e + "IIQQQQIIQQ", data, off)
            else:
                name, stype, flags, addr, soff, size, link, info, _al, entsize = struct.unpack_from(
                    e + "IIIIIIIIII", data, off)
            sections.append(dict(name=name, type=stype, flags=flags, addr=addr, offset=soff, size=size, link=link,
                                 info=info, entsize=entsize))
        if 0 <= e_shstrndx < len(sections):
            st = sections[e_shstrndx]
            strtab = data[st["offset"]:st["offset"] + st["size"]]
            for s in sections:
                end = strtab.find(b"\0", s["name"])
                s["name"] = strtab[s["name"]:end if end >= 0 else None].decode("latin-1")
        else:
            for s in sections:
                s["name"] = ""
    m.meta["vle"] = any(s["flags"] & EF_PPC_VLE_SECTION for s in sections) if e_machine == 20 else False
    for s in sections:
        if s["flags"] & 0x2 and s["size"] and s["type"] != 8:        # SHF_ALLOC, not NOBITS
            body = data[s["offset"]:s["offset"] + s["size"]]
            fl = "r" + ("w" if s["flags"] & 1 else "") + ("x" if s["flags"] & 4 else "")
            m.sections.append(Segment(s["addr"], bytearray(body), s["name"], fl))

    # ---- program headers -> memory map
    loads = []
    if e_phoff and e_phnum:
        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            if is64:
                p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, _memsz, _al = struct.unpack_from(
                    e + "IIQQQQQQ", data, off)
            else:
                p_type, p_offset, p_vaddr, p_paddr, p_filesz, _memsz, p_flags, _al = struct.unpack_from(
                    e + "IIIIIIII", data, off)
            if p_type == 1 and p_filesz:
                loads.append((p_paddr if use_physical else p_vaddr, p_vaddr, p_offset, p_filesz, p_flags))
    if loads:
        for addr, vaddr, off, size, flags in loads:
            fl = ("r" if flags & 4 else "") + ("w" if flags & 2 else "") + ("x" if flags & 1 else "")
            m.add(addr, data[off:off + size], f"LOAD@{vaddr:X}" if vaddr != addr else "LOAD", fl, merge=False)
    else:          # relocatable object: use the allocated sections
        for s in m.sections:
            m.add(s.address, bytes(s.data), s.name, s.flags, merge=False)

    # ---- symbols
    for s in sections:
        if s["type"] in (2, 11) and s["entsize"]:            # SYMTAB, DYNSYM
            strsec = sections[s["link"]] if s["link"] < len(sections) else None
            strtab = data[strsec["offset"]:strsec["offset"] + strsec["size"]] if strsec else b""
            n = s["size"] // s["entsize"]
            for i in range(1, n):
                off = s["offset"] + i * s["entsize"]
                if is64:
                    st_name, st_info, _o, st_shndx, st_value, st_size = struct.unpack_from(e + "IBBHQQ", data, off)
                else:
                    st_name, st_value, st_size, st_info, _o, st_shndx = struct.unpack_from(e + "IIIBBH", data, off)
                stype = st_info & 0xF
                if stype not in (0, 1, 2) or st_shndx == 0:
                    continue
                end = strtab.find(b"\0", st_name)
                name = strtab[st_name:end if end >= 0 else None].decode("latin-1")
                if not name or name.startswith("$"):           # ARM mapping symbols $a / $t / $d
                    continue
                kind = {0: "label", 1: "object", 2: "func"}[stype]
                m.symbols.append(Symbol(name, st_value, st_size, kind))
    m.symbols.sort(key=lambda s: s.address)
    return m


def dumps(m: MemoryMap, machine: int | None = None, big_endian: bool | None = None, is64: bool | None = None,
          flags: int | None = None) -> bytes:
    """A minimal executable ELF holding the segments of *m* (PT_LOAD each, plus one section per segment and a
    symbol table when *m* has symbols)."""
    machine = int(m.meta.get("e_machine", 0) if machine is None else machine)
    if big_endian is None:
        big_endian = m.meta.get("endian") == "big"
    if is64 is None:
        is64 = m.meta.get("elf_class") == 64 or m.max_address > 0xFFFFFFFF
    flags = int(m.meta.get("e_flags", 0) if flags is None else flags)
    e = ">" if big_endian else "<"
    ehsize = 64 if is64 else 52
    phentsize = 56 if is64 else 32
    shentsize = 64 if is64 else 40
    segs = m.segments
    nph = len(segs)
    # string tables
    shstr = bytearray(b"\0")

    def sname(s: str) -> int:
        i = len(shstr)
        shstr.extend(s.encode("latin-1", "replace") + b"\0")
        return i
    sec_names = [sname(s.name if s.name and not s.name.startswith("LOAD") else f".seg{i}")
                 for i, s in enumerate(segs)]
    symtab_name = sname(".symtab") if m.symbols else 0
    strtab_name = sname(".strtab") if m.symbols else 0
    shstrtab_name = sname(".shstrtab")
    strtab = bytearray(b"\0")
    symbytes = bytearray()
    if m.symbols:
        symbytes += bytes(24 if is64 else 16)
        for sym in m.symbols:
            idx = next((i + 1 for i, s in enumerate(segs) if s.contains(sym.address)), 0xFFF1)   # SHN_ABS
            no = len(strtab)
            strtab += sym.name.encode("latin-1", "replace") + b"\0"
            info = (1 << 4) | {"func": 2, "object": 1}.get(sym.kind, 0)        # GLOBAL
            if is64:
                symbytes += struct.pack(e + "IBBHQQ", no, info, 0, idx, sym.address, sym.size)
            else:
                symbytes += struct.pack(e + "IIIBBH", no, sym.address, sym.size, info, 0, idx)
    # layout: header, program headers, segment data (4-aligned), symtab, strtab, shstrtab, section headers
    off = ehsize + nph * phentsize
    data_offs = []
    body = bytearray()
    for s in segs:
        pad = (-(off + len(body))) % 4
        body += bytes(pad)
        data_offs.append(off + len(body))
        body += s.data
    extra = []
    for blob in ((symbytes, 8 if is64 else 4), (strtab, 1), (shstr, 1)):
        b, al = blob
        if b is shstr or m.symbols:
            pad = (-(off + len(body))) % al
            body += bytes(pad)
            extra.append(off + len(body))
            body += b
        else:
            extra.append(0)
    sym_off, str_off, shstr_off = extra
    shoff = off + len(body)
    shoff += (-shoff) % 8
    nsec = 1 + len(segs) + (2 if m.symbols else 0) + 1
    shstrndx = nsec - 1
    out = bytearray(b"\x7fELF" + bytes([2 if is64 else 1, 2 if big_endian else 1, 1, 0]) + bytes(8))
    entry = m.start if m.start is not None else (segs[0].address if segs else 0)
    if is64:
        out += struct.pack(e + "HHIQQQIHHHHHH", 2, machine, 1, entry, ehsize if nph else 0, shoff, flags, ehsize,
                           phentsize, nph, shentsize, nsec, shstrndx)
    else:
        out += struct.pack(e + "HHIIIIIHHHHHH", 2, machine, 1, entry, ehsize if nph else 0, shoff, flags, ehsize,
                           phentsize, nph, shentsize, nsec, shstrndx)
    for s, doff in zip(segs, data_offs):
        fl = (4 if "r" in (s.flags or "r") else 0) | (2 if "w" in s.flags else 0) | (1 if "x" in s.flags else 0)
        if is64:
            out += struct.pack(e + "IIQQQQQQ", 1, fl, doff, s.address, s.address, len(s), len(s), 4)
        else:
            out += struct.pack(e + "IIIIIIII", 1, doff, s.address, s.address, len(s), len(s), fl, 4)
    out += body
    out += bytes(shoff - len(out))

    def sh(name, stype, sflags, addr, soff, size, link=0, info=0, align=1, entsize=0):
        fmt = e + ("IIQQQQIIQQ" if is64 else "IIIIIIIIII")
        return struct.pack(fmt, name, stype, sflags, addr, soff, size, link, info, align, entsize)
    out += sh(0, 0, 0, 0, 0, 0)
    for s, doff, nm in zip(segs, data_offs, sec_names):
        sflags = 0x2 | (0x1 if "w" in s.flags else 0) | (0x4 if "x" in s.flags else 0)
        out += sh(nm, 1, sflags, s.address, doff, len(s), align=4)
    if m.symbols:
        strtab_idx = 1 + len(segs) + 1
        out += sh(symtab_name, 2, 0, 0, sym_off, len(symbytes), strtab_idx, 1, 8 if is64 else 4, 24 if is64 else 16)
        out += sh(strtab_name, 3, 0, 0, str_off, len(strtab))
    out += sh(shstrtab_name, 3, 0, 0, shstr_off, len(shstr))
    return bytes(out)
