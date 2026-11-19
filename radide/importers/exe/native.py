"""Native programs (C / C++ / Delphi / anything compiled) -> forms + recovered handler code.

* forms, menus, strings, icons from the PE resources (pe_resources.py);
* imports / exports / strings / function list with capstone (x86, x64);
* dialog procedures are found from DialogBoxParam/CreateDialogParam calls; their WM_COMMAND
  ``cmp id`` chains are mapped to the controls and menu items of the dialog, and the Win32 calls of every
  branch (SetDlgItemText, GetDlgItemText, MessageBox, EndDialog, SendDlgItemMessage(LB_ADDSTRING) ...)
  are translated by rules into handler actions (rendered as Python / VB by the wizard);
* windows built in code with CreateWindowEx("BUTTON"/"EDIT"/...) become forms too;
* Ghidra headless decompile when Ghidra is installed (GHIDRA_HOME / analyzeHeadless) -> pseudo-C;
* AI translation of the pseudo-C / disassembly into Python when the user allows it;
* without them: a report + one documented Python stub per function.
"""
from __future__ import annotations

import os
import re
import struct
import subprocess
import tempfile
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import pe_resources
from .base import ImportResult, ai_translate as _ai_translate, describe_action, safe_name, tools_dir

WM_INITDIALOG, WM_COMMAND, WM_CLOSE, WM_DESTROY, WM_CREATE = 0x110, 0x111, 0x10, 0x2, 0x1
MSG_EVENTS = {WM_INITDIALOG: "Load", WM_CREATE: "Load", WM_CLOSE: "FormClosing", WM_DESTROY: "FormClosed"}
LB_ADDSTRING, LB_RESETCONTENT, CB_ADDSTRING, CB_RESETCONTENT, WM_SETTEXT = 0x180, 0x184, 0x143, 0x14B, 0x0C
BM_SETCHECK, BM_GETCHECK = 0xF1, 0xF0

WIN_CLASSES = {"button": "Button", "edit": "TextBox", "static": "Label", "listbox": "ListBox",
               "combobox": "ComboBox", "msctls_progress32": "ProgressBar", "msctls_trackbar32": "TrackBar",
               "syslistview32": "ListView", "systreeview32": "TreeView", "systabcontrol32": "TabControl",
               "sysdatetimepick32": "DateTimePicker", "msctls_statusbar32": "StatusBar",
               "richedit20a": "TextBox", "richedit20w": "TextBox", "richedit50w": "TextBox"}

# volatile registers cleared after a call
_X64_ARGS = ["rcx", "rdx", "r8", "r9"]
_X64_VOLATILE = {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"}


def _family(name: str) -> str:
    """Register family: eax/ax/al -> rax, r8d/r8w/r8b -> r8."""
    n = name.lower()
    m = re.fullmatch(r"r(\d+)[dwb]?", n)
    if m:
        return f"r{m.group(1)}"
    table = {"a": "rax", "b": "rbx", "c": "rcx", "d": "rdx"}
    m = re.fullmatch(r"[re]?([abcd])[xlh]", n)
    if m:
        return table[m.group(1)]
    m = re.fullmatch(r"[re]?(si|di|bp|sp)l?", n)
    if m:
        return "r" + m.group(1)
    return n


# ============================================================================ data
@dataclass
class Call:
    addr: int
    target: str                  # import name ("MessageBoxA"), local function name, or "?"
    args: list                   # symbolic values: ("int", v) ("str", s) ("addr", va) ("stack", off) None
    local: int | None = None     # address of a local callee


@dataclass
class Func:
    addr: int
    name: str
    size: int = 0
    calls: list = field(default_factory=list)
    strings: list = field(default_factory=list)
    compares: list = field(default_factory=list)    # (addr, operand key, imm, jcc, target, fallthrough)
    insns: int = 0
    refs: list = field(default_factory=list)        # code addresses taken (callbacks)


@dataclass
class NativeAnalysis:
    machine: str = ""
    image_base: int = 0
    entry: int = 0
    imports: dict = field(default_factory=dict)     # dll -> [names]
    iat: dict = field(default_factory=dict)         # VA -> name
    exports: list = field(default_factory=list)     # [(name, VA)]
    strings: dict = field(default_factory=dict)     # VA -> text
    funcs: dict = field(default_factory=dict)       # VA -> Func
    symbols: dict = field(default_factory=dict)     # VA -> name (COFF symbol table)
    truncated: bool = False
    note: str = ""


# ============================================================================ helpers
def coff_symbols(pe, image_base: int) -> dict:
    """Function names from the COFF symbol table (MinGW / not stripped builds)."""
    out: dict = {}
    fh = pe.FILE_HEADER
    ptr, count = fh.PointerToSymbolTable, fh.NumberOfSymbols
    if not ptr or not count or count > 2_000_000:
        return out
    data = pe.__data__
    strtab = ptr + count * 18
    if strtab + 4 > len(data):
        return out
    sections = pe.sections
    i = 0
    while i < count:
        off = ptr + i * 18
        raw = data[off:off + 18]
        if len(raw) < 18:
            break
        name_b, value, secno, typ, sclass, naux = struct.unpack("<8sIhHBB", raw)
        if name_b[:4] == b"\x00\x00\x00\x00":
            soff = struct.unpack("<I", name_b[4:])[0]
            end = data.find(b"\x00", strtab + soff)
            name = data[strtab + soff:end].decode("latin-1", "replace")
        else:
            name = name_b.rstrip(b"\x00").decode("latin-1", "replace")
        if secno > 0 and secno <= len(sections) and (typ & 0x20 or sclass in (2, 3)) and name and \
                sections[secno - 1].Characteristics & 0x20000000:
            va = image_base + sections[secno - 1].VirtualAddress + value
            if typ & 0x20 and not name.startswith("."):
                out.setdefault(va, name)
        i += 1 + naux
    return out


def _scan_strings(pe, image_base: int, limit: int = 20000) -> dict:
    out: dict = {}
    for s in pe.sections:
        if s.Characteristics & 0x20000000:      # executable
            continue
        name = s.Name.rstrip(b"\x00").decode("latin-1")
        if name.lower() in (".reloc", ".pdata", ".xdata", ".rsrc", ".idata", ".edata", ".tls", ".crt"):
            continue
        data = s.get_data()
        base = image_base + s.VirtualAddress
        for m in re.finditer(rb"[\x20-\x7e\t\r\n]{4,}\x00", data):
            out[base + m.start()] = m.group()[:-1].decode("latin-1")
            if len(out) >= limit:
                return out
        for m in re.finditer(rb"(?:[\x20-\x7e]\x00){4,}\x00\x00", data):
            if m.start() % 2 == 0:
                out.setdefault(base + m.start(), m.group()[:-2].decode("utf-16-le", "replace"))
            if len(out) >= limit:
                return out
    return out


# ============================================================================ analysis
class _Analyser:
    def __init__(self, path: Path, progress, max_funcs: int = 1500, max_insns: int = 400_000,
                 time_budget: float = 60.0):
        import pefile
        self.progress = progress
        self.pe = pefile.PE(str(path))
        pe = self.pe
        self.a = NativeAnalysis()
        a = self.a
        a.image_base = pe.OPTIONAL_HEADER.ImageBase
        a.entry = a.image_base + pe.OPTIONAL_HEADER.AddressOfEntryPoint
        self.is64 = pe.FILE_HEADER.Machine == 0x8664
        a.machine = {0x8664: "x64", 0x14C: "x86"}.get(pe.FILE_HEADER.Machine, hex(pe.FILE_HEADER.Machine))
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) or []:
            dll = entry.dll.decode("latin-1")
            names = []
            for imp in entry.imports:
                n = imp.name.decode("latin-1") if imp.name else f"{dll}#{imp.ordinal}"
                names.append(n)
                a.iat[imp.address] = n
            a.imports[dll] = names
        exp = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
        if exp:
            for s in exp.symbols:
                if s.address:
                    a.exports.append(((s.name or b"").decode("latin-1") or f"#{s.ordinal}", a.image_base + s.address))
        a.symbols = coff_symbols(pe, a.image_base)
        a.strings = _scan_strings(pe, a.image_base)
        self.code = []          # (start VA, end VA, bytes)
        for s in pe.sections:
            if s.Characteristics & 0x20000000:
                st = a.image_base + s.VirtualAddress
                data = s.get_data()
                self.code.append((st, st + min(len(data), max(s.Misc_VirtualSize, 1)), data))
        self.max_funcs, self.max_insns, self.deadline = max_funcs, max_insns, time.time() + time_budget
        self.total = 0
        self.md = None
        if a.machine in ("x64", "x86"):
            from capstone import CS_ARCH_X86, CS_MODE_32, CS_MODE_64, Cs
            self.md = Cs(CS_ARCH_X86, CS_MODE_64 if self.is64 else CS_MODE_32)
            self.md.detail = True
        else:
            a.note = f"disassembly of {a.machine} code is not supported (only x86 / x64)"

    def close(self):
        try:
            self.pe.close()
        except Exception:  # noqa: BLE001
            pass

    # ---------------------------------------------------------------- memory
    def in_code(self, va: int) -> bool:
        return any(s <= va < e for s, e, _d in self.code)

    def bytes_at(self, va: int, n: int = 4096) -> bytes:
        for s, e, d in self.code:
            if s <= va < e:
                return d[va - s:min(va - s + n, e - s)]
        return b""

    def read_ptr(self, va: int) -> int | None:
        try:
            rva = va - self.a.image_base
            raw = self.pe.get_data(rva, 8 if self.is64 else 4)
            return struct.unpack("<Q" if self.is64 else "<I", raw)[0]
        except Exception:  # noqa: BLE001
            return None

    def string_at(self, va: int) -> str | None:
        s = self.a.strings.get(va)
        if s is not None:
            return s
        try:      # strings shorter than the scan minimum
            rva = va - self.a.image_base
            raw = self.pe.get_data(rva, 256)
        except Exception:  # noqa: BLE001
            return None
        if len(raw) >= 4 and raw[1] == 0 and 32 <= raw[0] < 127:
            end = raw.find(b"\x00\x00")
            while end > 0 and end % 2:
                end = raw.find(b"\x00\x00", end + 1)
            if end > 0:
                return raw[:end].decode("utf-16-le", "replace")
        end = raw.find(b"\x00")
        if end >= 1 and all(32 <= b < 127 or b in (9, 10, 13) for b in raw[:end]):
            return raw[:end].decode("latin-1")
        if end == 0:
            return ""
        return None

    # ---------------------------------------------------------------- run
    def run(self) -> NativeAnalysis:
        a = self.a
        if self.md is None:
            return a
        starts = [a.entry] + [va for _n, va in a.exports] + [va for va in a.symbols if self.in_code(va)]
        queue = list(dict.fromkeys(v for v in starts if self.in_code(v)))
        seen = set()
        while queue:
            if len(a.funcs) >= self.max_funcs or self.total >= self.max_insns or time.time() > self.deadline:
                a.truncated = True
                break
            va = queue.pop(0)
            if va in seen:
                continue
            seen.add(va)
            f = self.function(va)
            if f is None:
                continue
            a.funcs[va] = f
            queue += [r for r in f.refs if r not in seen]
            for c in f.calls:
                if c.local is not None and c.local not in seen:
                    queue.append(c.local)
                for v in c.args:
                    if v and v[0] == "addr" and self.in_code(v[1]) and v[1] not in seen:
                        queue.append(v[1])      # callbacks passed by address (dialog / window procedures)
        # local functions that only forward to one import get its name (CRT wrappers like sprintf)
        for f in a.funcs.values():
            if f.name.startswith("sub_"):
                imps = {c.target for c in f.calls if c.local is None and c.target != "?"}
                if len(imps) == 1 and len(f.calls) <= 3 and f.insns < 40:
                    imp = next(iter(imps))
                    f.name = _wrapper_name(imp) or f.name
        for f in a.funcs.values():
            for c in f.calls:
                if c.local is not None and c.local in a.funcs:
                    c.target = a.funcs[c.local].name
        return a

    def _name(self, va: int) -> str:
        n = self.a.symbols.get(va)
        if n:
            return n
        for en, ev in self.a.exports:
            if ev == va:
                return en
        return "WinMain_entry" if va == self.a.entry else f"sub_{va:X}"

    def function(self, start: int) -> Func | None:
        from capstone import x86_const as X
        md = self.md
        f = Func(start, self._name(start))
        blocks = [start]
        visited: set = set()
        hi = start
        regs: dict = {}
        stack: dict = {}
        pushes: list = []
        while blocks:
            ba = blocks.pop()
            if ba in visited or not self.in_code(ba):
                continue
            regs, stack, pushes = {}, {}, []
            code = self.bytes_at(ba, 8192)
            pending = None          # (operand key, imm, addr) of the last cmp
            for ins in md.disasm(code, ba):
                if ins.address in visited:
                    break
                visited.add(ins.address)
                f.insns += 1
                self.total += 1
                hi = max(hi, ins.address + ins.size)
                mn = ins.mnemonic
                ops = ins.operands
                # ---- string / address references
                for op in ops:
                    if op.type == X.X86_OP_MEM and op.mem.base == X.X86_REG_RIP:
                        tgt = ins.address + ins.size + op.mem.disp
                        s = self.a.strings.get(tgt)
                        if s and s not in f.strings:
                            f.strings.append(s)
                    elif op.type == X.X86_OP_IMM and not self.is64:
                        s = self.a.strings.get(op.imm)
                        if s and s not in f.strings:
                            f.strings.append(s)
                # ---- compares (case dispatch)
                if mn == "cmp" and len(ops) == 2 and ops[1].type == X.X86_OP_IMM:
                    key = self._opkey(ins, ops[0])
                    pending = (key, ops[1].imm & 0xFFFFFFFF, ins.address)
                elif mn in ("je", "jne", "jz", "jnz") and pending is not None and ops and ops[0].type == X.X86_OP_IMM:
                    f.compares.append((pending[2], pending[0], pending[1], mn, ops[0].imm, ins.address + ins.size))
                    pending = None
                elif not mn.startswith("j"):
                    if mn != "cmp":
                        pending = None
                # ---- control flow
                if mn == "ret" or mn == "retn":
                    break
                if mn == "call":
                    self._call(f, ins, ops, regs, stack, pushes)
                    for r in list(regs):
                        if r in _X64_VOLATILE:
                            regs.pop(r)
                    regs["rax"] = ("ret", ins.address)
                    pushes = []
                    if f.calls and f.calls[-1].target in ("ExitProcess", "exit", "_exit", "abort", "ExitThread"):
                        break
                    continue
                if mn == "jmp":
                    if ops and ops[0].type == X.X86_OP_IMM:
                        tgt = ops[0].imm
                        if self._is_func_boundary(tgt, start):
                            self._call(f, ins, ops, regs, stack, pushes)       # tail call
                        else:
                            blocks.append(tgt)
                    elif ops and ops[0].type == X.X86_OP_MEM:
                        self._call(f, ins, ops, regs, stack, pushes)           # import thunk / table
                    break
                if mn.startswith("j") or mn.startswith("loop"):
                    if ops and ops[0].type == X.X86_OP_IMM:
                        blocks.append(ops[0].imm)
                    continue
                self._track(ins, ops, regs, stack, pushes)
                if mn in ("lea", "mov", "push") and ops:
                    v = regs.get(_family(ins.reg_name(ops[0].reg))) if ops[0].type == X.X86_OP_REG else                         (pushes[-1] if mn == "push" and pushes else None)
                    if mn == "mov" and len(ops) == 2 and ops[1].type == X.X86_OP_IMM and not self.is64:
                        v = ("addr", ops[1].imm & 0xFFFFFFFF) if self.in_code(ops[1].imm & 0xFFFFFFFF) else None
                    if v and v[0] == "addr" and self.in_code(v[1]) and v[1] not in f.refs and v[1] != start:
                        f.refs.append(v[1])     # a callback stored in a struct (WNDCLASS.lpfnWndProc ...)
                if mn in ("int3", "hlt", "ud2"):
                    break
            if len(visited) > 20000:
                break
        f.size = hi - start
        return f

    def _is_func_boundary(self, tgt: int, start: int) -> bool:
        return tgt in self.a.symbols and tgt != start

    def _opkey(self, ins, op) -> str:
        from capstone import x86_const as X
        if op.type == X.X86_OP_REG:
            return _family(ins.reg_name(op.reg))
        if op.type == X.X86_OP_MEM:
            base = ins.reg_name(op.mem.base) if op.mem.base else ""
            return f"[{base}{op.mem.disp:+#x}]"
        return "?"

    def _value(self, ins, op, regs, stack):
        from capstone import x86_const as X
        if op.type == X.X86_OP_IMM:
            v = op.imm
            if not self.is64:
                v &= 0xFFFFFFFF
                s = self.a.strings.get(v)
                if s is not None:
                    return ("str", s)
                if self.in_code(v):
                    return ("addr", v)
            return ("int", v)
        if op.type == X.X86_OP_REG:
            return regs.get(_family(ins.reg_name(op.reg)))
        if op.type == X.X86_OP_MEM:
            base = _family(ins.reg_name(op.mem.base)) if op.mem.base else ""
            if base in ("rsp", "rbp") and not op.mem.index:
                return stack.get((base, op.mem.disp))
            if op.mem.base == X.X86_REG_RIP or (not self.is64 and not op.mem.base and not op.mem.index):
                tgt = ins.address + ins.size + op.mem.disp if op.mem.base else op.mem.disp & 0xFFFFFFFF
                if tgt in self.a.iat:
                    return ("addr", tgt)         # mov rax, [__imp_X] ; call rax
                ptr = self.read_ptr(tgt)
                if ptr:
                    s = self.a.strings.get(ptr)
                    if s is not None:
                        return ("str", s)
        return None

    def _track(self, ins, ops, regs, stack, pushes):
        from capstone import x86_const as X
        mn = ins.mnemonic
        if mn == "lea" and len(ops) == 2 and ops[0].type == X.X86_OP_REG:
            dst = _family(ins.reg_name(ops[0].reg))
            m = ops[1].mem
            if m.base == X.X86_REG_RIP:
                tgt = ins.address + ins.size + m.disp
                s = self.string_at(tgt)
                regs[dst] = ("str", s) if s is not None and not self.in_code(tgt) else ("addr", tgt)
            elif m.base and _family(ins.reg_name(m.base)) in ("rsp", "rbp") and not m.index:
                regs[dst] = ("stack", (_family(ins.reg_name(m.base)), m.disp))
            elif m.base and m.index and m.scale == 1 and not m.disp:
                a = regs.get(_family(ins.reg_name(m.base)))
                b = regs.get(_family(ins.reg_name(m.index)))
                regs[dst] = ("op", "+", a, b) if a and b else None
            else:
                regs.pop(dst, None)
            return
        if mn in ("mov", "movabs", "movzx", "movsxd", "movsx") and len(ops) == 2:
            if ops[0].type == X.X86_OP_REG:
                regs[_family(ins.reg_name(ops[0].reg))] = self._value(ins, ops[1], regs, stack)
            elif ops[0].type == X.X86_OP_MEM and ops[0].mem.base and not ops[0].mem.index:
                base = _family(ins.reg_name(ops[0].mem.base))
                if base in ("rsp", "rbp"):
                    stack[(base, ops[0].mem.disp)] = self._value(ins, ops[1], regs, stack)
            return
        if mn == "xor" and len(ops) == 2 and ops[0].type == X.X86_OP_REG and ops[1].type == X.X86_OP_REG \
                and ops[0].reg == ops[1].reg:
            regs[_family(ins.reg_name(ops[0].reg))] = ("int", 0)
            return
        if mn in ("add", "sub", "imul") and len(ops) == 2 and ops[0].type == X.X86_OP_REG:
            dst = _family(ins.reg_name(ops[0].reg))
            a, b = regs.get(dst), self._value(ins, ops[1], regs, stack)
            regs[dst] = ("op", {"add": "+", "sub": "-", "imul": "*"}[mn], a, b) if a and b and dst != "rsp" else None
            return
        if mn == "lea" and len(ops) == 2 and ops[1].mem.base and ops[1].mem.index and ops[1].mem.scale == 1 \
                and not ops[1].mem.disp:
            a = regs.get(_family(ins.reg_name(ops[1].mem.base)))
            b = regs.get(_family(ins.reg_name(ops[1].mem.index)))
            regs[_family(ins.reg_name(ops[0].reg))] = ("op", "+", a, b) if a and b else None
            return
        if mn == "push" and ops:
            pushes.append(self._value(ins, ops[0], regs, stack))
            return
        if mn == "or" and len(ops) == 2 and ops[0].type == X.X86_OP_REG and ops[1].type == X.X86_OP_IMM \
                and ops[1].imm == -1:
            regs[_family(ins.reg_name(ops[0].reg))] = ("int", -1)
            return
        if ops and ops[0].type == X.X86_OP_REG and mn not in ("cmp", "test"):
            regs.pop(_family(ins.reg_name(ops[0].reg)), None)

    def _call(self, f: Func, ins, ops, regs, stack, pushes):
        from capstone import x86_const as X
        target, local = "?", None
        if ops:
            op = ops[0]
            if op.type == X.X86_OP_IMM:
                tgt = op.imm
                if tgt in self.a.iat:
                    target = self.a.iat[tgt]
                else:
                    thunk = self._thunk_target(tgt)
                    if thunk:
                        target = thunk
                    elif self.in_code(tgt):
                        local, target = tgt, self._name(tgt)
            elif op.type == X.X86_OP_MEM:
                if op.mem.base == X.X86_REG_RIP:
                    target = self.a.iat.get(ins.address + ins.size + op.mem.disp, "?")
                elif not op.mem.base and not op.mem.index:
                    target = self.a.iat.get(op.mem.disp & 0xFFFFFFFF, "?")
            elif op.type == X.X86_OP_REG:
                v = regs.get(_family(ins.reg_name(op.reg)))
                if v and v[0] == "addr" and v[1] in self.a.iat:
                    target = self.a.iat[v[1]]
        if self.is64:
            args = [regs.get(r) for r in _X64_ARGS]
            base = "rsp"
            for k in range(4, 12):
                args.append(stack.get((base, 0x20 + (k - 4) * 8)))
        else:
            args = list(reversed(pushes))
        while args and args[-1] is None:
            args.pop()
        f.calls.append(Call(ins.address, target, args, local))

    def _thunk_target(self, va: int) -> str | None:
        """`jmp [iat]` stub -> the import name."""
        from capstone import x86_const as X
        code = self.bytes_at(va, 16)
        for ins in self.md.disasm(code, va, count=1):
            if ins.mnemonic == "jmp" and ins.operands and ins.operands[0].type == X.X86_OP_MEM:
                m = ins.operands[0].mem
                if m.base == X.X86_REG_RIP:
                    return self.a.iat.get(ins.address + ins.size + m.disp)
                if not m.base and not m.index:
                    return self.a.iat.get(m.disp & 0xFFFFFFFF)
        return None


def _wrapper_name(imp: str) -> str | None:
    low = imp.lower()
    if "vsnprintf" in low or "vsprintf" in low or "common_vsprintf" in low or low.endswith("vsprintf_s"):
        return "sprintf"
    if "common_vfprintf" in low or low in ("vprintf", "vfprintf"):
        return "printf"
    if "common_vsscanf" in low:
        return "sscanf"
    return None


def analyse(path, progress=None, **kw) -> NativeAnalysis:
    an = _Analyser(Path(path), progress or (lambda _s: None), **kw)
    try:
        return an.run()
    finally:
        an.close()


# ============================================================================ handler recovery
def _api(name: str) -> str:
    """MessageBoxA -> MessageBox, CreateWindowExW -> CreateWindowEx."""
    if name.endswith(("ExA", "ExW")):
        return name[:-1]
    if name.endswith(("A", "W")) and len(name) > 3 and name[-2].islower():
        return name[:-1]
    return name


def _expr(v, stackvars: dict):
    if v is None:
        return None
    k = v[0]
    if k == "str":
        return ("str", v[1])
    if k == "int":
        return ("int", v[1])
    if k == "stack":
        return stackvars.get(v[1], ("var", "buffer"))
    return None


def _mb_kind(flags: int) -> str:
    icon = flags & 0xF0
    if flags & 0xF in (4, 3, 1):
        return "question"
    return {0x10: "error", 0x30: "warning", 0x20: "question"}.get(icon, "info")


class _Translator:
    """Turn the Win32 calls of a code path into neutral handler actions (see base.render_actions)."""

    def __init__(self, ids: dict, dialog_forms: dict, menu_ids: dict | None = None):
        self.ids = ids                      # control id -> control name (this form)
        self.menu_ids = menu_ids or {}
        self.dialog_forms = dialog_forms    # dialog resource id -> form name
        self.counter = 0
        self.rets: dict = {}                # call address -> expression of its return value

    def x(self, v, sv: dict):
        """Symbolic value -> expression (see base.render_actions)."""
        if v is None:
            return None
        k = v[0]
        if k == "str":
            return ("str", v[1])
        if k == "int":
            return ("int", v[1])
        if k == "stack":
            return sv.get(v[1], ("var", "buffer"))
        if k == "ret":
            return self.rets.get(v[1])
        if k == "op":
            a, b = self.x(v[2], sv), self.x(v[3], sv)
            if a is not None and b is not None:
                return ("binop", v[1], a, b)
        return None

    def var_for(self, ctrl: str) -> str:
        base = re.sub(r"^(txt|cbo|lst|lbl|chk|opt)", "", ctrl) or ctrl
        name = re.sub(r"(?<!^)(?=[A-Z])", "_", base).lower()
        return name if name.isidentifier() else f"{ctrl.lower()}_text"

    def ctrl(self, v) -> str | None:
        if v and v[0] == "int":
            return self.ids.get(v[1] & 0xFFFF) or self.ids.get(v[1])
        return None

    def calls(self, calls: list) -> tuple[list, int, int]:
        """(actions, translated count, untranslated count)."""
        out, ok, bad = [], 0, 0
        stackvars: dict = {}
        for c in calls:
            n = _api(c.target).lstrip("_")
            arg = self.x(c.args[0], stackvars) if c.args else None
            if arg is not None:
                fn = {"atoi": "int", "atol": "int", "wtoi": "int", "strtol": "int", "wcstol": "int", "atoll": "int",
                      "atof": "float", "strtod": "float", "wcstod": "float", "strlen": "len", "lstrlen": "len",
                      "wcslen": "len"}.get(n)
                if fn:
                    self.rets[c.addr] = ("call", fn, [arg])
                    ok += 1
                    continue
            act = self.one(c, stackvars)
            if act is None:
                bad += 1
                args = ", ".join(_fmt_arg(a) for a in c.args)
                out.append(("comment", f"{c.target}({args})"))
            elif act:
                ok += 1
                out += act
        return out, ok, bad

    def one(self, c: Call, sv: dict):
        n = _api(c.target)
        a = c.args + [None] * 12
        if n == "MessageBox":
            text, title = self.x(a[1], sv) or ("str", ""), self.x(a[2], sv) or ("str", "")
            flags = a[3][1] if a[3] and a[3][0] == "int" else 0
            return [("msgbox", text, title, _mb_kind(flags))]
        if n == "SetDlgItemText":
            ctrl = self.ctrl(a[1])
            if ctrl:
                return [("set_text", ctrl, self.x(a[2], sv) or ("str", ""))]
        if n == "SetDlgItemInt":
            ctrl = self.ctrl(a[1])
            if ctrl:
                return [("set_text", ctrl, ("call", "str", [self.x(a[2], sv) or ("int", 0)]))]
        if n in ("GetDlgItemText", "GetDlgItemInt"):
            ctrl = self.ctrl(a[1])
            if ctrl:
                var = self.var_for(ctrl)
                if a[2] and a[2][0] == "stack":
                    sv[a[2][1]] = ("var", var)
                if n == "GetDlgItemInt":
                    return [("get_text", var, ctrl), ("assign", var, ("raw", f"int({var} or 0)"))]
                return [("get_text", var, ctrl)]
        if n in ("sprintf", "wsprintf", "_snprintf", "snprintf", "swprintf", "_swprintf", "StringCchPrintf"):
            fmt_i = 2 if n in ("_snprintf", "snprintf", "StringCchPrintf") else 1
            fmt = a[fmt_i]
            if fmt and fmt[0] == "str":
                nargs = len(re.findall(r"%[-+ 0#]*\d*(?:\.\d+)?(?:l|ll|h)?[sdiuxXfgcS]", fmt[1]))
                args = [(self.x(x, sv) or ("var", "value")) for x in a[fmt_i + 1:fmt_i + 1 + nargs]]
                self.counter += 1
                var = "text" if self.counter == 1 else f"text{self.counter}"
                if a[0] and a[0][0] == "stack":
                    sv[a[0][1]] = ("var", var)
                return [("assign", var, ("fmt", fmt[1], args))]
        if n in ("lstrcpy", "strcpy", "wcscpy", "lstrcpyn", "strcpy_s"):
            if a[0] and a[0][0] == "stack":
                src = self.x(a[1] if n != "strcpy_s" else a[2], sv)
                if src:
                    sv[a[0][1]] = src
                    return []
        if n in ("lstrcat", "strcat", "wcscat"):
            if a[0] and a[0][0] == "stack":
                cur = sv.get(a[0][1], ("str", ""))
                sv[a[0][1]] = ("concat", [cur, self.x(a[1], sv) or ("str", "")])
                return []
        if n in ("SendDlgItemMessage", "SendMessage"):
            ctrl = self.ctrl(a[1]) if n == "SendDlgItemMessage" else None
            msg = a[2] if n == "SendDlgItemMessage" else a[1]
            lp = a[4] if n == "SendDlgItemMessage" else a[3]
            wp = a[3] if n == "SendDlgItemMessage" else a[2]
            if ctrl and msg and msg[0] == "int":
                m = msg[1] & 0xFFFF
                if m in (LB_ADDSTRING, CB_ADDSTRING, 0x181, 0x14A):     # + LB_INSERTSTRING / CB_INSERTSTRING
                    return [("list_add", ctrl, self.x(lp, sv) or ("str", ""))]
                if m in (LB_RESETCONTENT, CB_RESETCONTENT):
                    return [("list_clear", ctrl)]
                if m == WM_SETTEXT:
                    return [("set_text", ctrl, self.x(lp, sv) or ("str", ""))]
                if m == BM_SETCHECK:
                    return [("set_check", ctrl, self.x(wp, sv) or ("int", 1))]
                if m == BM_GETCHECK:
                    return [("get_check", self.var_for(ctrl), ctrl)]
        if n == "CheckDlgButton":
            ctrl = self.ctrl(a[1])
            if ctrl:
                return [("set_check", ctrl, self.x(a[2], sv) or ("int", 1))]
        if n == "IsDlgButtonChecked":
            ctrl = self.ctrl(a[1])
            if ctrl:
                return [("get_check", self.var_for(ctrl), ctrl)]
        if n == "SetWindowText" and a[1]:
            return [("title", self.x(a[1], sv) or ("str", ""))]
        if n in ("EndDialog", "DestroyWindow", "PostQuitMessage", "ExitProcess"):
            return [("close",)]
        if n in ("DialogBoxParam", "DialogBox", "CreateDialogParam", "DialogBoxIndirectParam"):
            dlg = a[1]
            if dlg and dlg[0] == "int" and dlg[1] in self.dialog_forms:
                return [("show_form", self.dialog_forms[dlg[1]])]
        if n in ("MessageBeep", "Beep"):
            return [("beep",)]
        if n == "ShellExecute":
            tgt = self.x(a[2], sv)
            if tgt:
                return [("open", tgt)]
        if n == "CreateWindowEx" and a[1] and a[1][0] == "str" and a[1][1].lower() in WIN_CLASSES:
            return []          # the control is part of the recovered form
        if n in ("EnableWindow",):
            return None
        if n in ("GetDlgItem", "LoadString", "LoadIcon", "LoadCursor", "SetFocus", "UpdateWindow", "ShowWindow",
                 "InvalidateRect", "DefWindowProc", "DefDlgProc", "GetModuleHandle"):
            return []          # plumbing with no visible behaviour of its own
        return None


def _fmt_arg(v) -> str:
    if v is None:
        return "?"
    k = v[0]
    if k == "str":
        return repr(v[1])
    if k == "int":
        return hex(v[1]) if abs(v[1]) > 255 else str(v[1])
    if k == "addr":
        return f"&0x{v[1]:X}"
    if k == "stack":
        return "buffer"
    return "?"


def _branch_calls(analyser_code, md, iat_calls: dict, start: int, stops: set, limit: int = 400) -> list:
    """Follow the code from *start* (unconditional jumps followed, conditional ones not taken) and
    return the addresses of the calls on that path."""
    out, seen, pc, n = [], set(), start, 0
    while n < limit:
        code = analyser_code(pc)
        if not code:
            break
        moved = False
        for ins in md.disasm(code, pc):
            n += 1
            if ins.address in seen or (ins.address != start and ins.address in stops):
                return out
            seen.add(ins.address)
            mn = ins.mnemonic
            if mn == "call":
                out.append(ins.address)
            elif mn in ("ret", "retn", "int3", "hlt"):
                return out
            elif mn == "jmp":
                op = ins.operands[0] if ins.operands else None
                from capstone import x86_const as X
                if op is not None and op.type == X.X86_OP_IMM:
                    pc, moved = op.imm, True
                    break
                return out
            if n >= limit:
                return out
        if not moved:
            break
    return out


def recover_handlers(path: Path, an: NativeAnalysis, maps: dict, forms: dict, result: ImportResult) -> dict:
    """Map dialog/window procedures to forms and their case branches to handlers.
    maps: pe_resources maps {"dialogs": {form: {"id", "controls"}}, "menus": {form: {cmd: item}}}.
    Returns {form: {"ctrl.Event": [actions]}} and records which functions were used."""
    import pefile
    from capstone import CS_ARCH_X86, CS_MODE_32, CS_MODE_64, Cs
    pe = pefile.PE(str(path), fast_load=True)
    is64 = pe.FILE_HEADER.Machine == 0x8664
    code_secs = []
    for s in pe.sections:
        if s.Characteristics & 0x20000000:
            st = an.image_base + s.VirtualAddress
            code_secs.append((st, s.get_data()))
    pe.close()

    def code_at(va):
        for st, d in code_secs:
            if st <= va < st + len(d):
                return d[va - st:va - st + 4096]
        return b""
    md = Cs(CS_ARCH_X86, CS_MODE_64 if is64 else CS_MODE_32)
    md.detail = True

    dialog_forms = {info["id"]: f for f, info in maps.get("dialogs", {}).items()}
    proc_form: dict = {}          # function VA -> form
    startup = None
    starters: list = []             # dialogs shown by functions that are not dialog procedures
    for f in an.funcs.values():
        for c in f.calls:
            n = _api(c.target)
            if n in ("DialogBoxParam", "CreateDialogParam", "DialogBox"):
                a = c.args + [None] * 5
                dlg, proc = a[1], a[3]
                if dlg and dlg[0] == "int" and dlg[1] in dialog_forms:
                    form = dialog_forms[dlg[1]]
                    if proc and proc[0] == "addr" and proc[1] in an.funcs:
                        proc_form.setdefault(proc[1], form)
                    if f.addr not in an.funcs or f.addr in proc_form:
                        continue
                    starters.append(form)
    if starters:
        # the main dialog: the one with a menu, then the one with most controls
        startup = max(dict.fromkeys(starters), key=lambda fm: (fm in maps.get("menus", {}),
                                                               len(forms.get(fm, {}).get("controls", []))))
    result.resources["startup_form"] = startup
    # window procedures without a dialog: the function comparing with WM_COMMAND whose ids match a form best
    for f in an.funcs.values():
        if f.addr in proc_form:
            continue
        imms = {cmp[2] for cmp in f.compares}
        if WM_COMMAND not in imms and WM_INITDIALOG not in imms:
            continue
        best, score = None, 0
        for form, info in maps.get("dialogs", {}).items():
            ids = set(info["controls"]) | set(maps.get("menus", {}).get(form, {}))
            s = len(imms & {i for i in ids if i > 2})
            if s > score:
                best, score = form, s
        for form, menu in maps.get("menus", {}).items():
            if form in maps.get("dialogs", {}):
                continue
            s = len(imms & set(menu))
            if s > score:
                best, score = form, s
        if best and score:
            proc_form[f.addr] = best

    handlers: dict = {}
    used_funcs: dict = {}
    for fva, form in proc_form.items():
        f = an.funcs[fva]
        info = maps.get("dialogs", {}).get(form, {"controls": {}})
        ids = dict(info.get("controls", {}))
        menu = maps.get("menus", {}).get(form, {})
        tr = _Translator(ids, dialog_forms, menu)
        # the operand compared with window messages = the message parameter
        msg_keys = {cmp[1] for cmp in f.compares if cmp[2] in (WM_INITDIALOG, WM_COMMAND)}
        cases: dict = {}          # (kind, value) -> branch start
        for (_addr, key, imm, jcc, target, fall) in f.compares:
            start = target if jcc in ("je", "jz") else fall
            if key in msg_keys:
                if imm in MSG_EVENTS or imm == WM_COMMAND:
                    cases.setdefault(("msg", imm), start)
            else:
                if imm in ids or imm in menu:
                    cases.setdefault(("id", imm), start)
        # WM_COMMAND whose id test could not be read (ranges, bit tricks): when the dialog has an OK /
        # Cancel button, that branch is its click handler; otherwise the branch is not used
        cmd_start = cases.pop(("msg", WM_COMMAND), None)
        if cmd_start is not None and not any(k == "id" for k, _v in cases):
            std = next((i for i in (1, 2) if i in ids), None)
            if std is not None:
                cases[("id", std)] = cmd_start
                result.add("info", f"{form}: the WM_COMMAND code of {f.name} was given to {ids[std]} "
                                   "(the id test was not a simple compare)")
        stops = set(cases.values())
        by_addr = {c.addr: c for c in f.calls}
        form_h = handlers.setdefault(form, {})
        for (kind, val), start in cases.items():
            addrs = _branch_calls(code_at, md, by_addr, start, stops - {start})
            calls = [by_addr[a] for a in addrs if a in by_addr]
            actions, ok, bad = tr.calls(calls)
            if kind == "msg":
                key = f".{MSG_EVENTS[val]}"
            elif val in menu:
                key = f"{menu[val]}.Click"
            else:
                ctype = next((c["type"] for c in forms.get(form, {}).get("controls", [])
                              if c["props"].get("Name") == ids[val]), "Button")
                event = {"ComboBox": "SelectedIndexChanged", "ListBox": "SelectedIndexChanged",
                         "TextBox": "TextChanged"}.get(ctype, "Click")
                key = f"{ids[val]}.{event}"
            if key in form_h:
                continue
            if kind == "msg" and val in (WM_CLOSE, WM_DESTROY):
                actions = [x for x in actions if x[0] != "close"]      # the form is closing anyway
            if not actions and kind == "msg":
                continue
            form_h[key] = actions or [("comment", "no Win32 calls on this path (the original only returned)")]
            used_funcs[fva] = form
            if ok:
                result.add("rules", f"{form}.{key.lstrip('.')}: {ok} call(s) translated by rules "
                                    f"({', '.join(sorted({c.target for c in calls}))})")
            if bad:
                result.add("missing", f"{form}.{key.lstrip('.')}: {bad} call(s) kept as comments "
                                      "(no rule; see the function list)")
        if cases:
            result.add("info", f"{f.name} at 0x{f.addr:X} is the event procedure of {form} "
                               f"({len(cases)} case(s) recovered)")
    result.resources["event_procs"] = {f"0x{k:X}": v for k, v in used_funcs.items()}
    return handlers


# ============================================================================ CreateWindowEx forms
def windows_from_code(an: NativeAnalysis, result: ImportResult, existing: set) -> dict:
    """Forms for windows built in code: top-level CreateWindowEx + child controls with known classes."""
    forms: dict = {}
    from ...model import Form
    for f in an.funcs.values():
        tops, kids = [], []
        for c in f.calls:
            if _api(c.target) != "CreateWindowEx":
                continue
            a = c.args + [None] * 12
            cls = a[1][1] if a[1] and a[1][0] == "str" else ""
            text = a[2][1] if a[2] and a[2][0] == "str" else ""
            style = a[3][1] if a[3] and a[3][0] == "int" else 0
            geo = [a[i][1] if a[i] and a[i][0] == "int" else None for i in (4, 5, 6, 7)]
            parent = a[8]
            ident = a[9][1] if a[9] and a[9][0] == "int" else None
            if cls.lower() in WIN_CLASSES and (style & 0x40000000 or (parent is not None and parent != ("int", 0))):
                kids.append((cls, text, style, geo, ident))
            elif cls:
                tops.append((cls, text, style, geo))
        if not kids:
            continue
        title = tops[0][1] if tops else "Main window"
        geo = tops[0][3] if tops else [None] * 4
        name = "frmMain" if "frmmain" not in existing else f"frm{safe_name(title, 'Window')}"
        i = 2
        while name.lower() in existing:
            name, i = f"frm{safe_name(title, 'Window')}{i}", i + 1
        existing.add(name.lower())
        form = Form()
        form.props.update(Name=name, Text=title)
        w = geo[2] if geo[2] and 0 < geo[2] < 0x8000 else 0
        h = geo[3] if geo[3] and 0 < geo[3] < 0x8000 else 0
        maxx = max([(g[0] or 0) + (g[2] or 0) for _c, _t, _s, g, _i in kids] + [200])
        maxy = max([(g[1] or 0) + (g[3] or 0) for _c, _t, _s, g, _i in kids] + [120])
        form.props["Width"] = max(w - 16, maxx + 12) if w else maxx + 12
        form.props["Height"] = max(h - 39, maxy + 12) if h else maxy + 12
        ids = {}
        taken = {name.lower()}
        prev_label = ""
        for cls, text, style, g, ident in kids:
            ctype = WIN_CLASSES[cls.lower()]
            if ctype == "Button":
                k = style & 0xF
                ctype = "CheckBox" if k in (2, 3, 5, 6) else "RadioButton" if k in (4, 9) else \
                    "GroupBox" if k == 7 else "Button"
            stem = safe_name(text, "") if text else (safe_name(prev_label, "") if ctype in (
                "TextBox", "ComboBox", "ListBox") and prev_label else str(ident or ""))
            prev_label = text if ctype == "Label" else ""
            base = pe_resources.PREFIX.get(ctype, ctype[:3].lower()) + stem
            cname, j = base or ctype, 2
            if cname == pe_resources.PREFIX.get(ctype):
                cname = f"{base}1"
            while cname.lower() in taken:
                cname, j = f"{base}{j}", j + 1
            taken.add(cname.lower())
            ctrl = form.add(ctype, int(g[0] or 0), int(g[1] or 0))
            ctrl.props["Name"] = cname
            if "Text" in ctrl.props:
                ctrl.props["Text"] = text
            if g[2]:
                ctrl.props["Width"] = int(g[2])
            if g[3]:
                ctrl.props["Height"] = int(g[3])
            if ctype == "TextBox" and style & 0x4:
                ctrl.props["Multiline"] = True
            if ident is not None:
                ids[ident & 0xFFFF] = cname
        forms[name] = (form.to_dict(), ids, f)
        result.add("exact", f"Form {name}: {len(kids)} control(s) recovered from CreateWindowEx calls in {f.name}")
    return forms


# ============================================================================ Ghidra
GHIDRA_SCRIPT = r'''
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.io.*;

public class RadExportDecomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        String out = getScriptArgs()[0];
        DecompInterface d = new DecompInterface();
        d.openProgram(currentProgram);
        PrintWriter w = new PrintWriter(new OutputStreamWriter(new FileOutputStream(out), "UTF-8"));
        FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
        int n = 0;
        while (it.hasNext() && !monitor.isCancelled() && n < 3000) {
            Function f = it.next();
            if (f.isExternal() || f.isThunk()) continue;
            DecompileResults r = d.decompileFunction(f, 60, monitor);
            if (r != null && r.decompileCompleted()) {
                w.println("//@@FUNCTION " + f.getName() + " " + f.getEntryPoint());
                w.println(r.getDecompiledFunction().getC());
                n++;
            }
        }
        w.close();
    }
}
'''


def find_ghidra() -> str | None:
    cands = []
    for env in ("GHIDRA_HOME", "GHIDRA_INSTALL_DIR"):
        if os.environ.get(env):
            cands.append(Path(os.environ[env]))
    root = tools_dir()
    if root.is_dir():
        # %LOCALAPPDATA%\RADIDE\tools\ghidra_12.2_PUBLIC  or  ...\tools\ghidra\ghidra_12.2_PUBLIC (zip extracted)
        for c in sorted(root.glob("ghidra*"), reverse=True):
            cands.append(c)
            cands += sorted((d for d in c.glob("ghidra*") if d.is_dir()), reverse=True)
    for c in cands:
        for name in ("analyzeHeadless.bat", "analyzeHeadless"):
            p = c / "support" / name
            if p.is_file():
                return str(p)
    import shutil
    return shutil.which("analyzeHeadless")


def _ghidra_java_min(headless: str) -> int:
    """The Java major version this Ghidra needs (Ghidra/application.properties: application.java.min)."""
    try:
        props = (Path(headless).parent.parent / "Ghidra" / "application.properties").read_text(errors="replace")
        m = re.search(r"^application\.java\.min=(\d+)", props, re.M)
        return int(m.group(1)) if m else 17
    except OSError:
        return 17


def _jdk_version(home: Path) -> int:
    try:
        m = re.search(r'JAVA_VERSION="(\d+)(?:\.(\d+))?', (home / "release").read_text(errors="replace"))
    except OSError:
        return 0
    if not m:
        return 0
    major = int(m.group(1))
    return int(m.group(2) or 0) if major == 1 else major       # "1.8.0" -> 8


def find_jdk(min_version: int = 17) -> str | None:
    """Home folder of the newest JDK >= *min_version*: JAVA_HOME, %LOCALAPPDATA%\\RADIDE\\tools\\jdk*,
    the usual per-user / per-machine install folders, then the java on PATH."""
    import shutil
    homes: list[Path] = []
    if os.environ.get("JAVA_HOME"):
        homes.append(Path(os.environ["JAVA_HOME"]))
    roots = [tools_dir()]
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    roots += [Path(local) / "Java", Path(local) / "Programs" / "Eclipse Adoptium"]
    for pf in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432")):
        if pf:
            roots += [Path(pf) / "Java", Path(pf) / "Eclipse Adoptium", Path(pf) / "Microsoft",
                      Path(pf) / "Zulu", Path(pf) / "BellSoft"]
    for r in roots:
        if r.is_dir():
            for d in r.glob("*jdk*"):
                homes += [d, *d.glob("*jdk*")]
    java = shutil.which("java")
    if java:
        homes.append(Path(java).resolve().parent.parent)
    best, best_v = None, 0
    for h in homes:
        if (h / "bin" / "java.exe").is_file() or (h / "bin" / "java").is_file():
            v = _jdk_version(h)
            if v >= min_version and v > best_v:
                best, best_v = h, v
    return str(best) if best else None


def _ghidra_name(name: str) -> str:
    """Ghidra's FUN_140001660 -> sub_140001660 (the name the capstone analysis gives the same function)."""
    m = re.fullmatch(r"FUN_([0-9a-fA-F]+)", name)
    return f"sub_{int(m.group(1), 16):X}" if m else name


class GhidraFunctions(dict):
    """{function name: pseudo-C}; ``addr`` maps entry address -> name and ``error`` says why it is empty."""
    def __init__(self):
        super().__init__()
        self.addr: dict = {}
        self.error = ""

    def for_func(self, f) -> str | None:
        return self.get(f.name) or self.get(self.addr.get(f.addr, ""))


def ghidra_decompile(path: Path, workdir: Path, progress, timeout: int = 1800) -> dict:
    """{function name: pseudo-C} from Ghidra headless (empty when Ghidra is missing or fails)."""
    funcs = GhidraFunctions()
    exe = find_ghidra()
    if not exe:
        funcs.error = "Ghidra is not installed"
        return funcs
    need = _ghidra_java_min(exe)
    jdk = find_jdk(need)
    if not jdk:
        funcs.error = (f"Ghidra needs a JDK {need} or newer (none found: put one in %LOCALAPPDATA%\\RADIDE\\tools"
                       f"\\jdk{need} or set JAVA_HOME)")
        progress(funcs.error)
        return funcs
    work = Path(workdir) / "ghidra"
    work.mkdir(parents=True, exist_ok=True)
    (work / "RadExportDecomp.java").write_text(GHIDRA_SCRIPT, encoding="utf-8")
    out = work / "decompiled.c"
    out.unlink(missing_ok=True)
    progress("Running Ghidra headless analysis (this can take several minutes) ...")
    cmd = [exe, str(work), "radimport", "-import", str(path), "-scriptPath", str(work),
           "-postScript", "RadExportDecomp.java", str(out), "-deleteProject", "-overwrite"]
    env = dict(os.environ, JAVA_HOME=jdk)
    env["PATH"] = str(Path(jdk) / "bin") + os.pathsep + env.get("PATH", "")
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env,
                            stdin=subprocess.DEVNULL, errors="replace",       # never wait on a "JDK path?" prompt
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as e:
        funcs.error = f"Ghidra failed: {e}"
        progress(funcs.error)
        return funcs
    if not out.is_file():
        tail = [ln for ln in ((cp.stdout or "") + (cp.stderr or "")).splitlines() if ln.strip()][-3:]
        funcs.error = "Ghidra produced no output" + (": " + " | ".join(tail) if tail else "")
        progress(funcs.error)
        return funcs
    cur, buf = None, []

    def flush():
        if cur:
            funcs[cur] = re.sub(r"\bFUN_([0-9a-fA-F]+)\b", lambda m: _ghidra_name(m.group(0)),
                                "\n".join(buf).strip())
    for line in out.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("//@@FUNCTION "):
            flush()
            parts = line.split()
            cur, buf = (_ghidra_name(parts[1]) if len(parts) > 1 else f"f{len(funcs)}"), []
            try:
                funcs.addr[int(parts[2].split(":")[-1], 16)] = cur
            except (IndexError, ValueError):
                pass
        else:
            buf.append(line)
    flush()
    return funcs


# ============================================================================ module output
_CRT = re.compile(r"^(_|__|\.|mainCRTStartup|WinMainCRTStartup|atexit|pre_c_init|pre_cpp_init|"
                  r"tls_callback|mingw|_?sprintf$|printf$|fprintf$|sscanf$)", re.I)


def user_functions(an: NativeAnalysis) -> list:
    """Functions that look like program code (not the C runtime)."""
    out = []
    gui_dlls = {d for d in an.imports if d.lower() in ("user32.dll", "gdi32.dll", "comctl32.dll", "shell32.dll",
                                                        "comdlg32.dll", "advapi32.dll", "ws2_32.dll",
                                                        "wininet.dll", "winmm.dll", "ole32.dll")}
    gui_names = {n for d in gui_dlls for n in an.imports[d]}
    roots = [f.addr for f in an.funcs.values() if f.name.lower() in ("winmain", "wwinmain", "main", "wmain",
                                                                        "dllmain", "wwinmain@16", "_winmain@16")]
    reach: set = set()
    stack = list(roots) + [va for _n, va in an.exports]
    while stack:
        va = stack.pop()
        if va in reach or va not in an.funcs:
            continue
        reach.add(va)
        f = an.funcs[va]
        stack += [c.local for c in f.calls if c.local is not None] + list(f.refs)
    for f in an.funcs.values():
        if an.symbols and reach:
            if f.addr not in reach or _CRT.match(f.name):
                continue
        elif an.symbols:
            if _CRT.match(f.name) or f.addr not in an.symbols:
                continue
        else:
            if not ({c.target for c in f.calls} & gui_names or f.strings) or f.insns < 4:
                continue
        out.append(f)
    return sorted(out, key=lambda f: f.addr)


def _hex_id(k) -> str:
    try:
        return hex(int(k))
    except (TypeError, ValueError):
        return str(k)


def _decomp_for(decomp: dict, f) -> str | None:
    """Ghidra pseudo-C of *f*: by name, else by entry address (Ghidra and capstone may name it differently)."""
    if hasattr(decomp, "for_func"):
        return decomp.for_func(f)
    return decomp.get(f.name)


def stubs_module(an: NativeAnalysis, funcs: list, decomp: dict, translated: dict, program: str) -> str:
    L = [f'"""Functions recovered from {program} (native machine code).',
         "",
         "Each function below documents what the original code calls and which strings it uses.",
         "Bodies translated by AI are marked; the others are stubs to complete by hand.",
         '"""', "from __future__ import annotations   # AI signatures may name tkinter types", ""]
    for f in funcs:
        name = re.sub(r"\W", "_", f.name)
        if name[:1].isdigit():
            name = "f_" + name
        L += ["", ""]
        apis = list(dict.fromkeys(c.target for c in f.calls if c.target != "?"))
        doc = [f"Native function at 0x{f.addr:X} ({f.size} bytes, {f.insns} instructions)."]
        if apis:
            doc.append("Calls: " + ", ".join(apis[:20]) + (" ..." if len(apis) > 20 else ""))
        if f.strings:
            doc.append("Strings: " + "; ".join(repr(s)[:60] for s in f.strings[:8]))
        code = translated.get(f.name)
        sig = "*args"
        if code and code.startswith("#@signature ("):
            first, _nl, code = code.partition("\n")
            sig = first[len("#@signature ("):].rstrip().removesuffix(")") or "*args"
        L.append(f"def {name}({sig}):")
        L.append('    """' + "\n    ".join(d.replace('"""', "'''") for d in doc) + '\n    """')
        pc = _decomp_for(decomp, f)
        if pc and not code:
            L += ["    # pseudo-C from Ghidra:"] + [f"    # {ln}" for ln in pc.splitlines()[:80]]
        if code:
            L.append("    # translated by AI from the machine code - review it")
            L += ["    " + ln if ln.strip() else "" for ln in code.rstrip().splitlines()]
        else:
            for c in f.calls[:30]:
                L.append(f"    # {c.target}({', '.join(_fmt_arg(x) for x in c.args)})")
            L.append("    raise NotImplementedError")
    return "\n".join(L) + "\n"


def report_text(an: NativeAnalysis, funcs: list) -> str:
    L = [f"Machine: {an.machine}   image base 0x{an.image_base:X}   entry point 0x{an.entry:X}", ""]
    L.append(f"Imports ({sum(len(v) for v in an.imports.values())} functions from {len(an.imports)} DLLs):")
    for dll, names in an.imports.items():
        L.append(f"  {dll}: {', '.join(names[:40])}{' ...' if len(names) > 40 else ''}")
    if an.exports:
        L += ["", f"Exports ({len(an.exports)}):"] + [f"  {n} @ 0x{va:X}" for n, va in an.exports[:200]]
    L += ["", f"Functions found: {len(an.funcs)}{' (analysis stopped at the limit)' if an.truncated else ''}; "
              f"program functions: {len(funcs)}"]
    for f in funcs[:300]:
        apis = list(dict.fromkeys(c.target for c in f.calls if c.target != "?"))
        L.append(f"  0x{f.addr:X} {f.name} ({f.size} bytes): {', '.join(apis[:12])}")
    strs = [s for s in an.strings.values() if len(s.strip()) >= 4][:400]
    L += ["", f"Strings ({len(an.strings)} found, first {len(strs)}):"] + [f"  {s!r}" for s in strs]
    return "\n".join(L) + "\n"


# ============================================================================ backend interface
def can_handle(info) -> bool:
    return info.details.get("format", "").startswith("PE") or info.kind in (
        "native", "delphi", "installer", "nuitka", "autoit", "ahk")


def run(path, info, workdir, progress, ai_translate: bool = False) -> ImportResult:
    path = Path(path)
    progress = progress or (lambda _s: None)
    workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="radexe_"))
    result = ImportResult()
    if info.kind not in ("native", "installer", "delphi", "unknown"):
        result.add("warn", f"This is a {info.label}; its specialised importer is not available, so only the "
                           "resources and the machine code were analysed.")
    # ---- resources
    progress("Reading resources (dialogs, menus, strings, version, icons) ...")
    try:
        res = pe_resources.read_resources(path)
        if not res.dialogs and not res.menus:
            mui = _mui_file(path)
            if mui is not None:       # Windows keeps the dialogs of many programs in <lang>\<name>.mui
                mres = pe_resources.read_resources(mui)
                if mres.dialogs or mres.menus:
                    res.dialogs, res.menus, res.strings = mres.dialogs, mres.menus, {**mres.strings, **res.strings}
                    result.add("info", f"Dialogs and menus read from the language file {mui}")
        maps = pe_resources.fill_result(res, result, info)
    except Exception as e:  # noqa: BLE001
        result.add("error", f"Cannot read the resources: {e}")
        maps = {"dialogs": {}, "menus": {}}
    if info.kind == "ahk":
        _ahk_script(res if "res" in locals() else None, result)
    # ---- code
    progress("Disassembling the machine code (capstone) ...")
    try:
        an = analyse(path, progress)
    except Exception as e:  # noqa: BLE001
        result.add("error", f"Disassembly failed: {e}")
        return result
    if an.note:
        result.add("warn", an.note)
    progress(f"{len(an.funcs)} function(s), {sum(len(v) for v in an.imports.values())} imported API(s), "
             f"{len(an.strings)} string(s)")
    if an.symbols:
        result.add("exact", f"{len(an.symbols)} function name(s) from the COFF symbol table (not stripped)")
    else:
        result.add("info", "No symbol table (stripped): functions are named sub_<address>")
    forms = {n: fd for n, fd in result.forms}
    # windows built in code
    existing = {n.lower() for n in forms}
    code_forms = windows_from_code(an, result, existing)
    for name, (fd, ids, _f) in code_forms.items():
        result.forms.append((name, fd))
        forms[name] = fd
        maps.setdefault("dialogs", {})[name] = {"id": f"code:{name}", "controls": ids, "title": fd["props"]["Text"]}
    # ---- handlers
    progress("Mapping dialog procedures to forms and translating the Win32 calls by rules ...")
    try:
        result.handlers = recover_handlers(path, an, maps, forms, result)
    except Exception as e:  # noqa: BLE001
        result.add("warn", f"Handler recovery failed: {e}")
    _friendly_names(result)
    if not result.resources.get("startup_form") and result.forms:
        result.resources["startup_form"] = max(result.forms, key=lambda nf: (len(result.handlers.get(nf[0], {})),
                                                                             len(nf[1]["controls"])))[0]
    # ---- Ghidra
    funcs = user_functions(an)
    decomp = {}
    if find_ghidra():
        decomp = ghidra_decompile(path, workdir, progress)
        if decomp:
            result.add("exact", f"Ghidra decompiled {len(decomp)} function(s) to pseudo-C (kept in decompiled.c)")
            result.modules.append(("decompiled.c", "\n\n".join(f"// {n}\n{c}" for n, c in decomp.items()), "c"))
        else:
            result.add("warn", getattr(decomp, "error", "") or "Ghidra did not decompile any function")
    else:
        result.add("info", "Ghidra is not installed: no pseudo-C (install it into %LOCALAPPDATA%\\RADIDE\\tools "
                           "or set GHIDRA_HOME for full decompilation)")
    # ---- AI
    translated: dict = {}
    if ai_translate and funcs:
        translated = _ai_functions(an, funcs, decomp, result, progress)
    program = path.name
    result.modules.append((f"{safe_name(path.stem, 'Program')}_native.py",
                           stubs_module(an, funcs, decomp, translated, program), "python"))
    result.modules.append(("native_report.txt", report_text(an, funcs), "text"))
    n_missing = len(funcs) - len(translated)
    if n_missing:
        result.add("missing", f"{n_missing} program function(s) kept as documented stubs "
                              f"(see {safe_name(path.stem, 'Program')}_native.py)")
    for form, hs in result.handlers.items():
        for key, acts in hs.items():
            result.resources.setdefault("handler_text", []).append(
                f"{form}.{key.lstrip('.')}: " + "; ".join(describe_action(a) for a in acts[:6]))
    return result


FRIENDLY = {"Label": "lblResult", "ListBox": "lstItems", "ComboBox": "cboItems", "TextBox": "txtInput",
            "ProgressBar": "prgProgress", "TrackBar": "trkValue", "ListView": "lvwItems", "TreeView": "tvwItems",
            "PictureBox": "picImage"}
_CTRL_AT = {"set_text": 1, "list_add": 1, "list_clear": 1, "set_check": 1, "enable": 1, "get_text": 2,
            "get_check": 2}


def _friendly_names(result: ImportResult) -> None:
    """lbl1003 / lst1005 (named after their numeric id) -> lblResult / lstItems, everywhere."""
    for fi, (fname, fd) in enumerate(result.forms):
        taken = {c["props"].get("Name", "").lower() for c in fd.get("controls", [])}
        ren = {}
        for c in fd.get("controls", []):
            old = c["props"].get("Name", "")
            if not re.fullmatch(r"[a-z]{3}\d+", old) or c["type"] not in FRIENDLY:
                continue
            base = FRIENDLY[c["type"]]
            new, i = base, 2
            while new.lower() in taken:
                new, i = f"{base}{i}", i + 1
            taken.add(new.lower())
            ren[old] = new
            c["props"]["Name"] = new
        if not ren:
            continue
        for c in fd.get("controls", []):
            if c["props"].get("Parent") in ren:
                c["props"]["Parent"] = ren[c["props"]["Parent"]]
        hs = result.handlers.get(fname, {})
        new_hs = {}
        for key, acts in hs.items():
            ctrl, dot, ev = key.rpartition(".")
            key = f"{ren.get(ctrl, ctrl)}{dot}{ev}" if dot else key
            out = []
            for a in acts:
                if isinstance(a, tuple) and a[0] in _CTRL_AT and len(a) > _CTRL_AT[a[0]]:
                    i = _CTRL_AT[a[0]]
                    a = a[:i] + (ren.get(a[i], a[i]),) + a[i + 1:]
                out.append(a)
            new_hs[key] = out
        if hs:
            result.handlers[fname] = new_hs
        for m in (result.resources.get("dialog_ids") or {}).get(fname, {}).get("controls", {}), :
            for k, v in list(m.items()):
                m[k] = ren.get(v, v)


def _mui_file(path: Path) -> Path | None:
    """<folder>/<language>/<name>.mui (en-US first)."""
    cands = [path.parent / "en-US" / (path.name + ".mui")]
    cands += sorted(path.parent.glob(f"*-*/{path.name}.mui"))
    if path.parent.name.lower() == "system32":
        cands.append(path.parent.parent / "en-US" / (path.name + ".mui"))
    return next((c for c in cands if c.is_file()), None)


def _ahk_script(res, result: ImportResult) -> None:
    if res is None:
        return
    for name, data in res.rcdata.items():
        if "AUTOHOTKEY" in name.upper() or data[:3] == b"\xef\xbb\xbf" and b"::" in data[:4000]:
            text = data.decode("utf-8-sig", "replace")
            result.modules.append(("script.ahk", text, "text"))
            result.add("exact", f"AutoHotkey script recovered from resource {name} ({len(text)} characters)")
            return


def _ai_functions(an: NativeAnalysis, funcs: list, decomp: dict, result: ImportResult, progress,
                  max_funcs: int = 8, max_chars: int = 2500) -> dict:
    """Translate the most relevant functions with the user's AI provider."""
    procs = {int(k, 16) for k in result.resources.get("event_procs", {})}
    order = sorted(funcs, key=lambda f: (f.addr not in procs, -len(f.calls)))[:max_funcs]
    out: dict = {}
    for f in order:
        src = _decomp_for(decomp, f)
        if src:
            lang = "decompiled C (Ghidra pseudo-C)"
            if len(src) > max_chars:      # small prompts: local models time out on whole pseudo-C files
                src = src[:max_chars].rsplit("\n", 1)[0] + "\n  /* ... rest of the function cut ... */"
        else:
            lang = "summary of a native function (Win32 API calls in order, with arguments)"
            src = "\n".join([f"function {f.name}:", *(f"  call {c.target}({', '.join(_fmt_arg(x) for x in c.args)})"
                                                      for c in f.calls[:80]),
                             *(f"  uses string {s!r}" for s in f.strings[:20])])
        ctx = ("Write ONE Python function using tkinter for any UI; keep the C parameters as its parameters. "
               "Win32 messages: 0x110 = WM_INITDIALOG (the form loads), 0x111 = WM_COMMAND (the low word of "
               "wParam is the id of the clicked control or menu item).")
        ids = result.resources.get("dialog_ids") or {}
        if ids:
            ctx += " Control and menu ids of the program's dialogs (decimal/hex = name): " + "; ".join(
                f"{form}: " + ", ".join(f"{k}/{_hex_id(k)}={v}" for k, v in list(d.get("controls", {}).items())[:30])
                for form, d in list(ids.items())[:4])
        # local models on a CPU-only machine need several minutes for one function
        code, who = _ai_translate(src, lang, "Python", ctx, progress, timeout=360)
        if code is None:
            result.add("warn", who)
            break
        body = _ai_body(code)
        if body is None:
            result.add("warn", f"{f.name}: the AI answer is not a valid Python function - kept as a stub")
            continue
        out[f.name] = body
        result.add("ai", f"{f.name}: translated to Python by AI ({who})")
    return out


def _ai_body(code: str) -> str | None:
    """Body of the AI's function (+ its parameters as a ``#@signature`` marker read by stubs_module).
    The answer may carry imports, helper code or an ``if __name__`` block around the first top-level def;
    the imports move into the body, the rest is dropped.  None when the result does not compile."""
    lines = code.splitlines()
    at = next((i for i, ln in enumerate(lines) if re.match(r"(async\s+)?def\s+\w+\s*\(", ln)), None)
    sig = ""
    if at is None:
        body = textwrap.dedent(code)
    else:
        end = at                                   # a signature can span several lines
        while end < len(lines) - 1 and not lines[end].rstrip().endswith(":"):
            end += 1
        m = re.match(r"(?:async\s+)?def\s+\w+\s*\(([^)]*)\)\s*(->[^:]*)?:\s*$", " ".join(lines[at:end + 1]))
        sig = " ".join(m.group(1).split()) if m else ""
        inner = []
        for ln in lines[end + 1:]:
            if ln.strip() and not ln[:1].isspace():
                break
            inner.append(ln)
        imports = [ln for ln in lines[:at] if re.match(r"(import|from)\s+\w", ln)]
        body = "\n".join(imports + [textwrap.dedent("\n".join(inner))])
    if not body.strip():
        return None
    try:
        compile(f"def _f({sig or '*args'}):\n" + textwrap.indent(body, "    ") + "\n", "<ai>", "exec")
    except (SyntaxError, ValueError):
        return None
    return (f"#@signature ({sig})\n" if sig else "") + body
