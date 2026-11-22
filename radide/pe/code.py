"""x86 / x64 code analysis of a PE file with Capstone: functions, names, strings, cross references, listings.

    an = CodeAnalysis(img)
    an.analyze(progress)                     # function starts, call graph, xrefs, strings (bounded work)
    an.functions                             # {va: Function}
    an.listing(va)                           # [Line] of one function
    an.name_of(va), an.xrefs_to(va), an.strings
"""
from __future__ import annotations

import re
import struct
from dataclasses import dataclass

from .image import DIR_EXCEPTION, PEImage

_HEX = re.compile(r"0x[0-9a-fA-F]+")
_RIP = re.compile(r"\[rip ([+-]) (0x[0-9a-fA-F]+)\]")
BRANCH = {"call", "jmp", "ja", "jae", "jb", "jbe", "jc", "je", "jg", "jge", "jl", "jle", "jna", "jnae", "jnb",
          "jnbe", "jnc", "jne", "jng", "jnge", "jnl", "jnle", "jno", "jnp", "jns", "jnz", "jo", "jp", "jpe", "jpo",
          "js", "jz", "jecxz", "jrcxz", "loop", "loope", "loopne"}


def capstone_available() -> bool:
    try:
        import capstone
        return bool(capstone)
    except ImportError:
        return False


@dataclass
class Function:
    va: int
    name: str
    end: int = 0                     # exclusive
    source: str = ""                 # entry / export / pdata / call / mfc / user

    @property
    def size(self) -> int:
        return max(0, self.end - self.va)


@dataclass
class Line:
    va: int
    size: int
    raw: bytes
    mnemonic: str
    op_str: str
    comment: str = ""
    target: int | None = None        # branch / call / data target

    def text(self, show_bytes: bool = True) -> str:
        b = self.raw.hex(" ").upper()
        if len(b) > 23:
            b = b[:21] + ".."
        s = f"{self.va:08X}  " + (f"{b:<24}" if show_bytes else "") + f"{self.mnemonic:<7} {self.op_str}"
        return s + (f"   ; {self.comment}" if self.comment else "")


@dataclass
class StringRef:
    va: int
    text: str
    wide: bool


class CodeAnalysis:
    def __init__(self, img: PEImage):
        self.img = img
        self.is64 = img.is64
        self.functions: dict[int, Function] = {}
        self.names: dict[int, str] = {}                 # va -> name (functions, imports, data labels)
        self.imports: dict[int, str] = {}               # IAT slot va -> "DLL!Func"
        self.thunks: dict[int, str] = {}                # code va of "jmp [IAT]" -> "DLL!Func"
        self.strings: dict[int, StringRef] = {}
        self.xrefs: dict[int, set[int]] = {}            # target va -> {from va}
        self.analyzed = False
        self._sorted = None
        self._md = None
        self._load_names()

    # ================================================================ basics
    @property
    def md(self):
        if self._md is None:
            import capstone
            self._md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64 if self.is64 else capstone.CS_MODE_32)
            self._md.skipdata = False
        return self._md

    def code_ranges(self) -> list[tuple[int, int]]:
        ib = self.img.image_base
        return [(ib + s.vaddr, ib + s.vaddr + min(s.vsize or s.raw_size, s.raw_size))
                for s in self.img.sections if s.executable and s.raw_size]

    def is_code(self, va: int) -> bool:
        return any(a <= va < b for a, b in self.code_ranges())

    def _load_names(self) -> None:
        img = self.img
        ib = img.image_base
        for im in img.imports():
            self.imports[ib + im.iat_rva] = im.label
            self.names[ib + im.iat_rva] = im.label
        for ex in img.exports():
            if not ex.forwarder:
                self.add_function(ib + ex.rva, ex.name, "export")
        if img.entry_rva:
            self.add_function(img.entry_va, "EntryPoint" if not img.is_dll else "DllEntryPoint", "entry")

    def add_function(self, va: int, name: str | None = None, source: str = "user", force_name: bool = False) -> Function:
        f = self.functions.get(va)
        if f is None:
            f = Function(va, name or f"sub_{va:X}", 0, source)
            self.functions[va] = f
        elif name and (force_name or f.name.startswith("sub_")):
            f.name = name
        self.names[va] = f.name
        return f

    def reclose(self) -> None:
        """Recompute function ends after functions were added (MFC handlers, user functions)."""
        for f in self.functions.values():
            if f.source != "pdata":
                f.end = 0
        self._sorted = None
        self._close_functions()

    def rename(self, va: int, name: str) -> None:
        if va in self.functions:
            self.functions[va].name = name
        self.names[va] = name

    def name_of(self, va: int) -> str:
        if va in self.names:
            return self.names[va]
        if va in self.thunks:
            return "j_" + self.thunks[va]
        f = self.function_at(va)
        if f is not None and f.va != va:
            return f"{f.name}+0x{va - f.va:X}"
        return f"0x{va:X}"

    def function_at(self, va: int) -> Function | None:
        import bisect
        if self._sorted is None or len(self._sorted) != len(self.functions):
            self._sorted = sorted(self.functions)
        i = bisect.bisect_right(self._sorted, va) - 1
        if i >= 0:
            f = self.functions[self._sorted[i]]
            if f.end > va or f.va == va:
                return f
        return None

    # ================================================================ analysis
    def analyze(self, progress=None, max_insns: int = 3_000_000) -> None:
        progress = progress or (lambda _m: None)
        img = self.img
        ib = img.image_base
        # x64: the exception directory lists every non-leaf function
        rva, size = img.directory(DIR_EXCEPTION)
        if self.is64 and rva:
            try:
                blob = img.read(rva, size)
                for i in range(size // 12):
                    b, e, _u = struct.unpack_from("<III", blob, 12 * i)
                    if b and e > b:
                        f = self.add_function(ib + b, None, "pdata")
                        f.end = max(f.end, ib + e)
            except Exception:  # noqa: BLE001
                pass
        progress("Disassembling code sections ...")
        calls: set[int] = set()
        count = 0
        md = self.md
        for start, end in self.code_ranges():
            code = img.read_va(start, end - start)
            off = 0
            n = len(code)
            while off < n and count < max_insns:
                got = False
                for (addr, size, mnem, op) in md.disasm_lite(code[off:off + 0x10000], start + off):
                    got = True
                    count += 1
                    off = addr + size - start
                    self._note_insn(addr, size, mnem, op, calls)
                    if count >= max_insns:
                        break
                if not got:
                    off += 1                                   # undecodable byte: skip it
                if count % 200000 < 50:
                    progress(f"Disassembling ... {count:,} instructions")
        for t in calls:
            if self.is_code(t):
                self.add_function(t, None, "call")
        self._find_strings()
        self._close_functions()
        self.analyzed = True
        progress(f"{len(self.functions):,} functions, {len(self.strings):,} strings, {count:,} instructions")

    def _ref(self, target: int, src: int) -> None:
        s = self.xrefs.get(target)
        if s is None:
            s = self.xrefs[target] = set()
        if len(s) < 2000:
            s.add(src)

    def _note_insn(self, addr: int, size: int, mnem: str, op: str, calls: set) -> None:
        if mnem in BRANCH:
            if op.startswith("0x"):
                try:
                    t = int(op, 16)
                except ValueError:
                    return
                self._ref(t, addr)
                if mnem == "call":
                    calls.add(t)
                return
        m = _RIP.search(op) if self.is64 else None
        if m:
            disp = int(m.group(2), 16)
            t = addr + size + (disp if m.group(1) == "+" else -disp)
            self._ref(t, addr)
            if mnem == "jmp" and t in self.imports:
                self.thunks[addr] = self.imports[t]
            return
        if "0x" in op:
            for h in _HEX.findall(op):
                v = int(h, 16)
                if v >= 0x10000 and self.img.valid_va(v):
                    self._ref(v, addr)
                    if mnem == "jmp" and v in self.imports:
                        self.thunks[addr] = self.imports[v]
                    if mnem == "push" and not self.is64 and self.is_code(v):
                        calls.add(v)                      # callbacks (DlgProc, WndProc) pushed as arguments

    def _close_functions(self) -> None:
        starts = sorted(self.functions)
        ranges = self.code_ranges()
        for i, va in enumerate(starts):
            f = self.functions[va]
            if f.end > va:
                continue
            nxt = starts[i + 1] if i + 1 < len(starts) else None
            sec_end = next((b for a, b in ranges if a <= va < b), va + 1)
            f.end = min(nxt, sec_end) if nxt else sec_end
            # trim padding (int3 / nop) at the end
            try:
                tail = self.img.read_va(max(va, f.end - 64), f.end - max(va, f.end - 64))
                k = len(tail)
                while k > 0 and tail[k - 1] in (0xCC, 0x90):
                    k -= 1
                f.end = max(va + 1, f.end - (len(tail) - k))
            except Exception:  # noqa: BLE001
                pass
        for va, name in self.thunks.items():
            if va in self.functions and self.functions[va].name.startswith("sub_"):
                self.functions[va].name = "j_" + name
                self.names[va] = "j_" + name

    def _find_strings(self, min_len: int = 4, limit: int = 200_000) -> None:
        img = self.img
        ib = img.image_base
        ascii_re = re.compile(rb"[\x20-\x7e\t\r\n]{%d,}\x00" % min_len)
        wide_re = re.compile(rb"(?:[\x20-\x7e\t\r\n]\x00){%d,}\x00\x00" % min_len)
        for s in img.sections:
            if s.executable or not s.raw_size:
                continue
            data = bytes(img.data[s.raw_ptr:s.raw_ptr + s.raw_size])
            for m in ascii_re.finditer(data):
                if len(self.strings) >= limit:
                    return
                self.strings[ib + s.vaddr + m.start()] = StringRef(ib + s.vaddr + m.start(),
                                                                   m.group()[:-1].decode("latin-1"), False)
            for m in wide_re.finditer(data):
                if m.start() % 2:
                    continue
                if len(self.strings) >= limit:
                    return
                self.strings[ib + s.vaddr + m.start()] = StringRef(
                    ib + s.vaddr + m.start(), m.group()[:-2].decode("utf-16-le", "replace"), True)

    # ================================================================ listings
    def xrefs_to(self, va: int) -> list[int]:
        return sorted(self.xrefs.get(va, ()))

    def callers(self, va: int) -> list[Function]:
        out = {}
        for src in self.xrefs_to(va):
            f = self.function_at(src)
            if f is not None:
                out[f.va] = f
        return [out[k] for k in sorted(out)]

    def _comment(self, va: int, size: int, mnem: str, op: str) -> tuple[str, int | None]:
        targets = []
        m = _RIP.search(op) if self.is64 else None
        if m:
            disp = int(m.group(2), 16)
            targets.append(va + size + (disp if m.group(1) == "+" else -disp))
        else:
            for h in _HEX.findall(op):
                v = int(h, 16)
                if v >= 0x1000 and self.img.valid_va(v):
                    targets.append(v)
        notes = []
        first = None
        for t in targets:
            first = first if first is not None else t
            if t in self.imports:
                notes.append(self.imports[t])
            elif t in self.strings:
                s = self.strings[t]
                txt = s.text if len(s.text) < 70 else s.text[:67] + "..."
                notes.append(("L" if s.wide else "") + repr(txt))
            elif t in self.names:
                notes.append(self.names[t])
            elif t in self.thunks:
                notes.append("j_" + self.thunks[t])
            elif mnem in BRANCH and t in self.functions:
                notes.append(self.functions[t].name)
        return ", ".join(notes), first

    def disasm(self, va: int, length: int, max_lines: int = 20000) -> list[Line]:
        try:
            code = self.img.read_va(va, length)
        except Exception:  # noqa: BLE001
            return []
        out = []
        off = 0
        while off < len(code) and len(out) < max_lines:
            got = False
            for (addr, size, mnem, op) in self.md.disasm_lite(code[off:], va + off):
                got = True
                c, t = self._comment(addr, size, mnem, op)
                out.append(Line(addr, size, code[addr - va:addr - va + size], mnem, op, c, t))
                off = addr + size - va
                if len(out) >= max_lines:
                    break
            if not got:
                out.append(Line(va + off, 1, code[off:off + 1], "db", f"0x{code[off]:02X}"))
                off += 1
        return out

    def listing(self, va: int, max_lines: int = 20000) -> list[Line]:
        f = self.functions.get(va) or self.function_at(va)
        if f is None or not f.end:
            return self.disasm(va, 0x200, max_lines=200)
        return self.disasm(f.va, max(1, f.end - f.va), max_lines)

    def listing_text(self, va: int, show_bytes: bool = True) -> str:
        f = self.functions.get(va) or self.function_at(va)
        head = []
        if f is not None:
            head.append(f"; ---------------- {f.name} ({f.size} bytes)")
            callers = self.callers(f.va)
            if callers:
                head.append("; called from: " + ", ".join(c.name for c in callers[:12]) +
                            (" ..." if len(callers) > 12 else ""))
        return "\n".join(head + [ln.text(show_bytes) for ln in self.listing(va)])

    def instructions_covering(self, va: int, min_bytes: int) -> list[Line]:
        """Whole instructions starting at *va* that cover at least *min_bytes* bytes."""
        out, total = [], 0
        for ln in self.disasm(va, min_bytes + 16, max_lines=16):
            out.append(ln)
            total += ln.size
            if total >= min_bytes:
                break
        return out if total >= min_bytes else []
