"""A small, self-contained PE (Windows .exe / .dll, 32 and 64-bit) reader / writer for the PE workbench.

Works on one ``bytearray`` (the whole file) and edits it in place:

    img = PEImage(Path("app.exe").read_bytes())
    img.is64, img.image_base, img.sections, img.imports(), img.exports(), img.relocations()
    img.read(rva, n) / img.write(rva, data) / img.read_va(va, n)
    img.add_section(".radpat", data, vsize, chars)      # new last section (header room permitting)
    img.set_section_data(i, data)                       # resize a section's raw data (later sections shift)
    img.set_relocations(entries)                        # rebuild the base relocation table
    img.strip_certificate(); img.update_checksum()

No third-party packages (pefile is not needed).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

# data directory indexes
DIR_EXPORT, DIR_IMPORT, DIR_RESOURCE, DIR_EXCEPTION, DIR_SECURITY, DIR_BASERELOC = 0, 1, 2, 3, 4, 5
DIR_DEBUG, DIR_TLS, DIR_LOAD_CONFIG, DIR_BOUND_IMPORT, DIR_IAT, DIR_DELAY_IMPORT, DIR_CLR = 6, 9, 10, 11, 12, 13, 14

SCN_CNT_CODE, SCN_CNT_INITIALIZED_DATA, SCN_CNT_UNINITIALIZED_DATA = 0x20, 0x40, 0x80
SCN_MEM_EXECUTE, SCN_MEM_READ, SCN_MEM_WRITE, SCN_MEM_DISCARDABLE = 0x20000000, 0x40000000, 0x80000000, 0x02000000

DLLCHAR_DYNAMIC_BASE, DLLCHAR_NX_COMPAT, DLLCHAR_GUARD_CF = 0x0040, 0x0100, 0x4000
FILE_DLL = 0x2000

MACHINES = {0x14C: "x86", 0x8664: "x64", 0x1C0: "ARM", 0x1C4: "ARMv7 (Thumb-2)", 0xAA64: "ARM64", 0x200: "IA-64"}

REL_ABSOLUTE, REL_HIGHLOW, REL_DIR64 = 0, 3, 10


class PEError(ValueError):
    pass


def align(v: int, a: int) -> int:
    return (v + a - 1) // a * a if a else v


@dataclass
class Section:
    index: int
    name: str
    vaddr: int
    vsize: int
    raw_ptr: int
    raw_size: int
    chars: int
    hdr_off: int

    @property
    def vend(self) -> int:
        return self.vaddr + max(self.vsize, self.raw_size)

    @property
    def executable(self) -> bool:
        return bool(self.chars & (SCN_MEM_EXECUTE | SCN_CNT_CODE))

    @property
    def writable(self) -> bool:
        return bool(self.chars & SCN_MEM_WRITE)

    def contains(self, rva: int) -> bool:
        return self.vaddr <= rva < self.vaddr + max(self.vsize, self.raw_size)

    def flags_text(self) -> str:
        return "".join(c if self.chars & m else "-" for c, m in (("R", SCN_MEM_READ), ("W", SCN_MEM_WRITE),
                                                                 ("X", SCN_MEM_EXECUTE)))


@dataclass
class Import:
    dll: str
    name: str            # function name, or "#<ordinal>"
    iat_rva: int         # the IAT slot (the program calls through it)
    ordinal: int | None = None
    delay: bool = False

    @property
    def label(self) -> str:
        return f"{self.dll.rsplit('.', 1)[0]}!{self.name}"


@dataclass
class Export:
    name: str
    ordinal: int
    rva: int
    forwarder: str = ""


class PEImage:
    def __init__(self, data: bytes | bytearray):
        self.data = data if isinstance(data, bytearray) else bytearray(data)
        self.parse()

    # ================================================================ headers
    def parse(self) -> None:
        try:
            self._parse()
        except struct.error as e:                  # a header / section table cut off by the end of the file
            raise PEError(f"Truncated or corrupted PE headers ({e}).") from None

    def _parse(self) -> None:
        d = self.data
        if len(d) < 0x40 or d[:2] != b"MZ":
            raise PEError("Not a Windows program (no MZ header).")
        self.pe_off = struct.unpack_from("<I", d, 0x3C)[0]
        if self.pe_off + 24 > len(d) or d[self.pe_off:self.pe_off + 4] != b"PE\0\0":
            raise PEError("Not a PE file (no PE signature) - maybe a DOS or 16-bit program.")
        coff = self.pe_off + 4
        (self.machine, self.nsections, self.timestamp, _, _, self.opt_size,
         self.characteristics) = struct.unpack_from("<HHIIIHH", d, coff)
        self.opt_off = coff + 20
        magic = struct.unpack_from("<H", d, self.opt_off)[0]
        if magic not in (0x10B, 0x20B):
            raise PEError(f"Unknown optional header (magic 0x{magic:X}).")
        self.is64 = magic == 0x20B
        o = self.opt_off
        self.entry_rva = struct.unpack_from("<I", d, o + 16)[0]
        self.image_base = struct.unpack_from("<Q" if self.is64 else "<I", d, o + 24 if self.is64 else o + 28)[0]
        self.section_alignment, self.file_alignment = struct.unpack_from("<II", d, o + 32)
        self.size_of_image, self.size_of_headers, self.checksum = struct.unpack_from("<III", d, o + 56)
        self.subsystem, self.dll_characteristics = struct.unpack_from("<HH", d, o + 68)
        nd_off = o + (108 if self.is64 else 92)
        self.ndirs = min(struct.unpack_from("<I", d, nd_off)[0], 16)
        self.dir_off = nd_off + 4
        self.sec_off = self.opt_off + self.opt_size
        self.sections: list[Section] = []
        for i in range(self.nsections):
            h = self.sec_off + 40 * i
            name = d[h:h + 8].split(b"\0", 1)[0].decode("latin-1")
            vs, va, rs, rp = struct.unpack_from("<IIII", d, h + 8)
            chars = struct.unpack_from("<I", d, h + 36)[0]
            self.sections.append(Section(i, name, va, vs, rp, rs, chars, h))
        self._imports = None
        self._exports = None
        self._relocs = None

    @property
    def ptr_size(self) -> int:
        return 8 if self.is64 else 4

    @property
    def machine_name(self) -> str:
        return MACHINES.get(self.machine, f"0x{self.machine:X}")

    @property
    def is_dll(self) -> bool:
        return bool(self.characteristics & FILE_DLL)

    @property
    def entry_va(self) -> int:
        return self.image_base + self.entry_rva if self.entry_rva else 0

    def _set_opt(self, fmt: str, off: int, *v) -> None:
        struct.pack_into(fmt, self.data, self.opt_off + off, *v)

    def set_dll_characteristics(self, value: int) -> None:
        self._set_opt("<H", 70, value)
        self.dll_characteristics = value

    # ================================================================ directories
    def directory(self, i: int) -> tuple[int, int]:
        if i >= self.ndirs or self.dir_off + 8 * i + 8 > len(self.data):
            return 0, 0                            # (a truncated file: the directory is not there)
        return struct.unpack_from("<II", self.data, self.dir_off + 8 * i)

    def set_directory(self, i: int, rva: int, size: int) -> None:
        if i >= self.ndirs:
            raise PEError(f"The file has no data directory {i}.")
        struct.pack_into("<II", self.data, self.dir_off + 8 * i, rva, size)

    # ================================================================ address conversion
    def section_of(self, rva: int) -> Section | None:
        for s in self.sections:
            if s.contains(rva):
                return s
        return None

    def section_by_name(self, name: str) -> Section | None:
        return next((s for s in self.sections if s.name == name), None)

    def rva_to_off(self, rva: int) -> int | None:
        if rva < self.size_of_headers and not any(s.contains(rva) for s in self.sections):
            return rva
        s = self.section_of(rva)
        if s is None:
            return None
        delta = rva - s.vaddr
        if delta >= s.raw_size:
            return None                       # in the zero-filled tail (no file bytes)
        return s.raw_ptr + delta

    def off_to_rva(self, off: int) -> int | None:
        for s in self.sections:
            if s.raw_ptr <= off < s.raw_ptr + s.raw_size:
                return s.vaddr + off - s.raw_ptr
        return off if off < self.size_of_headers else None

    def va_to_rva(self, va: int) -> int:
        return va - self.image_base

    def rva_to_va(self, rva: int) -> int:
        return rva + self.image_base

    def valid_va(self, va: int) -> bool:
        return self.image_base <= va < self.image_base + self.size_of_image

    def is_code_va(self, va: int) -> bool:
        s = self.section_of(va - self.image_base)
        return s is not None and s.executable

    # ================================================================ reading / writing
    def read(self, rva: int, n: int) -> bytes:
        out = bytearray()
        if rva < 0 or n > max(len(self.data), self.size_of_image) + 0x1000:
            raise PEError(f"RVA 0x{rva:X} / size {n} is outside the image.")
        while n > 0:
            off = self.rva_to_off(rva)
            s = self.section_of(rva)
            if off is None:
                if s is None:
                    raise PEError(f"RVA 0x{rva:X} is outside the image.")
                take = min(n, s.vaddr + max(s.vsize, s.raw_size) - rva)
                out += b"\0" * take
            else:
                limit = (s.raw_ptr + s.raw_size) if s else self.size_of_headers
                take = max(1, min(n, limit - off))
                chunk = self.data[off:off + take] if off >= 0 else b""
                out += chunk
                if len(chunk) < take:              # past the end of a truncated file: zeros
                    out += b"\0" * (take - len(chunk))
            rva += take
            n -= take
        return bytes(out)

    def read_va(self, va: int, n: int) -> bytes:
        return self.read(va - self.image_base, n)

    def write(self, rva: int, data: bytes) -> None:
        off = self.rva_to_off(rva)
        end = self.rva_to_off(rva + len(data) - 1) if data else off
        if off is None or end is None or end - off != len(data) - 1:
            raise PEError(f"Cannot write {len(data)} bytes at RVA 0x{rva:X} (not backed by file data).")
        self.data[off:off + len(data)] = data

    def write_va(self, va: int, data: bytes) -> None:
        self.write(va - self.image_base, data)

    def u16(self, rva: int) -> int:
        return struct.unpack("<H", self.read(rva, 2))[0]

    def u32(self, rva: int) -> int:
        return struct.unpack("<I", self.read(rva, 4))[0]

    def ptr(self, rva: int) -> int:
        return struct.unpack("<Q" if self.is64 else "<I", self.read(rva, self.ptr_size))[0]

    def cstr(self, rva: int, limit: int = 512) -> str:
        try:
            b = self.read(rva, limit)
        except PEError:
            return ""
        return b.split(b"\0", 1)[0].decode("latin-1")

    # ================================================================ imports / exports
    def imports(self) -> list[Import]:
        if self._imports is not None:
            return self._imports
        out: list[Import] = []
        rva, size = self.directory(DIR_IMPORT)
        P = self.ptr_size
        flag = 1 << (63 if self.is64 else 31)
        try:
            p = rva
            while rva and p + 20 <= rva + max(size, 20) * 64:
                oft, _ts, _fw, name_rva, ft = struct.unpack("<IIIII", self.read(p, 20))
                if not (oft or name_rva or ft):
                    break
                dll = self.cstr(name_rva, 256)
                thunk = oft or ft
                for k in range(65536):
                    v = self.ptr(thunk + k * P)
                    if not v:
                        break
                    if v & flag:
                        out.append(Import(dll, f"#{v & 0xFFFF}", ft + k * P, v & 0xFFFF))
                    else:
                        out.append(Import(dll, self.cstr((v & 0x7FFFFFFF) + 2, 256), ft + k * P))
                p += 20
        except PEError:
            pass
        rva, size = self.directory(DIR_DELAY_IMPORT)
        try:
            p = rva
            while rva:
                attrs, name_rva, _hmod, iat, int_, _b, _u, _ts = struct.unpack("<8I", self.read(p, 32))
                if not name_rva:
                    break
                fix = 0 if attrs & 1 else self.image_base          # old VC6 delay imports store VAs
                dll = self.cstr(name_rva - fix, 256)
                for k in range(65536):
                    v = self.ptr(int_ - fix + k * P)
                    if not v:
                        break
                    if v & flag:
                        out.append(Import(dll, f"#{v & 0xFFFF}", iat - fix + k * P, v & 0xFFFF, delay=True))
                    else:
                        out.append(Import(dll, self.cstr((v & 0x7FFFFFFF) - fix + 2, 256), iat - fix + k * P,
                                          delay=True))
                p += 32
        except PEError:
            pass
        self._imports = out
        return out

    def import_by_name(self, name: str, dll: str | None = None) -> Import | None:
        for im in self.imports():
            if im.name == name and (dll is None or im.dll.lower() == dll.lower()):
                return im
        return None

    def exports(self) -> list[Export]:
        if self._exports is not None:
            return self._exports
        out: list[Export] = []
        rva, size = self.directory(DIR_EXPORT)
        if rva:
            try:
                (_c, _t, _ma, _mi, _name, base, nfun, nnames, afun, anames, aords) = \
                    struct.unpack("<IIHHIIIIIII", self.read(rva, 40))
                names = {}
                for i in range(min(nnames, 65536)):
                    nrva = self.u32(anames + 4 * i)
                    names[self.u16(aords + 2 * i)] = self.cstr(nrva, 512)
                for i in range(min(nfun, 65536)):
                    f = self.u32(afun + 4 * i)
                    if not f:
                        continue
                    fwd = self.cstr(f, 256) if rva <= f < rva + size else ""
                    out.append(Export(names.get(i, f"#{base + i}"), base + i, f, fwd))
            except PEError:
                pass
        self._exports = out
        return out

    # ================================================================ relocations
    def relocations(self) -> list[tuple[int, int]]:
        """[(rva, type)] of the base relocation table (ABSOLUTE padding entries left out)."""
        if self._relocs is not None:
            return self._relocs
        out = []
        rva, size = self.directory(DIR_BASERELOC)
        p, end = rva, rva + size
        try:
            while rva and p + 8 <= end:
                page, bsize = struct.unpack("<II", self.read(p, 8))
                if bsize < 8:
                    break
                body = self.read(p + 8, bsize - 8)
                for (w,) in struct.iter_unpack("<H", body[:len(body) // 2 * 2]):
                    t = w >> 12
                    if t != REL_ABSOLUTE:
                        out.append((page + (w & 0xFFF), t))
                p += bsize
        except PEError:
            pass
        self._relocs = out
        return out

    def reloc_set(self) -> set[int]:
        return {r for r, _t in self.relocations()}

    @staticmethod
    def build_relocations(entries) -> bytes:
        pages: dict[int, list[tuple[int, int]]] = {}
        for rva, t in sorted(set(entries)):
            pages.setdefault(rva & ~0xFFF, []).append((rva & 0xFFF, t))
        out = bytearray()
        for page in sorted(pages):
            words = [(t << 12) | off for off, t in pages[page]]
            if len(words) % 2:
                words.append(0)
            out += struct.pack("<II", page, 8 + 2 * len(words)) + struct.pack(f"<{len(words)}H", *words)
        return bytes(out)

    def set_relocations(self, entries) -> None:
        """Rebuild the base relocation table (in the .reloc section when it fits, else in a new section)."""
        blob = self.build_relocations(entries) if entries else b""
        rva, size = self.directory(DIR_BASERELOC)
        sec = self.section_of(rva) if rva else None
        if sec is not None and sec.vaddr == rva:
            limit = self._virtual_room(sec)
            if len(blob) <= limit:
                self.set_section_data(sec.index, blob or b"\0" * 8, max(len(blob), 8))
                self.set_directory(DIR_BASERELOC, rva, len(blob))
                self._relocs = None
                return
        if not blob:
            self.set_directory(DIR_BASERELOC, 0, 0)
            self._relocs = None
            return
        s = self.add_section(".reloc", blob, len(blob), SCN_CNT_INITIALIZED_DATA | SCN_MEM_READ | SCN_MEM_DISCARDABLE)
        self.set_directory(DIR_BASERELOC, s.vaddr, len(blob))
        self._relocs = None

    # ================================================================ layout changes
    def _virtual_room(self, sec: Section) -> int:
        """Bytes the section may span virtually without touching the next section."""
        later = [s.vaddr for s in self.sections if s.vaddr > sec.vaddr]
        if not later:
            return 1 << 30
        return min(later) - sec.vaddr

    def overlay_offset(self) -> int:
        end = self.size_of_headers
        for s in self.sections:
            if s.raw_size:
                end = max(end, s.raw_ptr + s.raw_size)
        return end

    def overlay(self) -> bytes:
        return bytes(self.data[self.overlay_offset():])

    def has_certificate(self) -> bool:
        return self.directory(DIR_SECURITY)[0] != 0

    def strip_certificate(self) -> bool:
        """Remove the Authenticode signature (it is invalid after any change). True when one was removed."""
        off, size = self.directory(DIR_SECURITY)
        if not off:
            return False
        self.set_directory(DIR_SECURITY, 0, 0)
        if off + size >= len(self.data) - 7 and off >= self.overlay_offset():
            del self.data[off:]
        return True

    def _write_section_header(self, s: Section) -> None:
        h = s.hdr_off
        self.data[h:h + 8] = s.name.encode("latin-1")[:8].ljust(8, b"\0")
        struct.pack_into("<IIII", self.data, h + 8, s.vsize, s.vaddr, s.raw_size, s.raw_ptr)
        struct.pack_into("<I", self.data, h + 36, s.chars)

    def _update_sizes(self) -> None:
        last = max(self.sections, key=lambda s: s.vaddr)
        self.size_of_image = align(last.vaddr + max(last.vsize, last.raw_size), self.section_alignment)
        self._set_opt("<I", 56, self.size_of_image)
        code = sum(s.raw_size for s in self.sections if s.chars & SCN_CNT_CODE)
        init = sum(s.raw_size for s in self.sections if s.chars & SCN_CNT_INITIALIZED_DATA)
        self._set_opt("<II", 4, code, init)

    def header_room(self) -> int:
        """Free bytes after the section table inside SizeOfHeaders (for new section headers)."""
        end = self.sec_off + 40 * self.nsections
        first_raw = min([s.raw_ptr for s in self.sections if s.raw_size] or [self.size_of_headers])
        return min(self.size_of_headers, first_raw) - end

    def add_section(self, name: str, data: bytes, vsize: int | None = None,
                    chars: int = SCN_CNT_INITIALIZED_DATA | SCN_MEM_READ) -> Section:
        """Append a section after the last one (before any overlay). Returns the new Section."""
        if self.header_room() < 40:
            raise PEError("No room for another section header in this file.")
        bi_rva, _ = self.directory(DIR_BOUND_IMPORT)
        end_tab = self.sec_off + 40 * self.nsections
        if bi_rva and end_tab <= bi_rva < end_tab + 40 + 64:
            self.set_directory(DIR_BOUND_IMPORT, 0, 0)       # bound imports are optional; they live there
        if any(self.data[end_tab:end_tab + 40]):
            self.data[end_tab:end_tab + 40] = b"\0" * 40
        self.strip_certificate()
        overlay = bytes(self.data[self.overlay_offset():])
        del self.data[self.overlay_offset():]
        raw_ptr = align(len(self.data), self.file_alignment)
        raw = bytes(data) + b"\0" * (align(len(data), self.file_alignment) - len(data))
        self.data += b"\0" * (raw_ptr - len(self.data)) + raw + overlay
        last = max(self.sections, key=lambda s: s.vaddr)
        vaddr = align(last.vaddr + max(last.vsize, last.raw_size), self.section_alignment)
        s = Section(self.nsections, name, vaddr, vsize if vsize is not None else len(data), raw_ptr, len(raw),
                    chars, end_tab)
        self.sections.append(s)
        self.nsections += 1
        struct.pack_into("<H", self.data, self.pe_off + 6, self.nsections)
        self._write_section_header(s)
        self._update_sizes()
        self.parse()
        return self.sections[-1]

    def set_section_data(self, index: int, data: bytes, vsize: int | None = None) -> Section:
        """Replace a section's raw data (later sections' file data shift; their RVAs do not change)."""
        s = self.sections[index]
        vsize = len(data) if vsize is None else vsize
        if max(vsize, len(data)) > self._virtual_room(s):
            raise PEError(f"Section {s.name} cannot grow to 0x{vsize:X} bytes (the next section follows).")
        new_raw = align(len(data), self.file_alignment)
        delta = new_raw - s.raw_size
        cert_off, cert_size = self.directory(DIR_SECURITY)
        if delta and cert_off:
            self.strip_certificate()
        block = bytes(data) + b"\0" * (new_raw - len(data))
        self.data[s.raw_ptr:s.raw_ptr + s.raw_size] = block
        if delta:
            for o in self.sections:
                if o.index != index and o.raw_ptr >= s.raw_ptr + s.raw_size and o.raw_size:
                    o.raw_ptr += delta
                    self._write_section_header(o)
            self._shift_debug(s.raw_ptr + s.raw_size, delta)
        s.raw_size = new_raw
        s.vsize = vsize
        self._write_section_header(s)
        self._update_sizes()
        self.parse()
        return self.sections[index]

    def _shift_debug(self, after: int, delta: int) -> None:
        """Debug directory entries hold file offsets (PointerToRawData): keep them right when data shifts."""
        rva, size = self.directory(DIR_DEBUG)
        if not rva:
            return
        off = self.rva_to_off(rva)
        if off is None:
            return
        for i in range(size // 28):
            p = off + 28 * i + 24
            if p + 4 > len(self.data):          # (a debug directory cut off by the end of the file)
                break
            ptr = struct.unpack_from("<I", self.data, p)[0]
            if ptr >= after:
                struct.pack_into("<I", self.data, p, ptr + delta)

    # ================================================================ checksum
    def compute_checksum(self) -> int:
        d = self.data
        ck_off = self.opt_off + 64
        total = 0
        n = len(d)
        buf = bytes(d[:ck_off]) + b"\0\0\0\0" + bytes(d[ck_off + 4:])
        if n % 2:
            buf += b"\0"
        import array
        words = array.array("H")
        words.frombytes(buf)
        if words.itemsize != 2:
            raise PEError("unexpected array item size")
        import sys
        if sys.byteorder != "little":
            words.byteswap()
        total = sum(words)
        while total >> 16:
            total = (total & 0xFFFF) + (total >> 16)
        return (total + n) & 0xFFFFFFFF

    def update_checksum(self) -> int:
        c = self.compute_checksum()
        self._set_opt("<I", 64, c)
        self.checksum = c
        return c
