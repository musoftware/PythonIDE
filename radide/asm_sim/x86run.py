"""Run a linked image (radide/asm_sim/objload.Image) in the Unicorn engine and watch for mistakes.

The program runs in a sandbox: only its own sections, a 1 MB stack, a 4 MB heap and the stub slots exist;
the library functions it calls are imitated in Python (radide/asm_sim/stubs.py); nothing touches the real
system. A step limit and a time limit stop endless loops. Per instruction the runner keeps a *shadow call
stack* (for every ``call``: where it must return and where the stack pointer was) and checks:

* ``ret``: the stack pointer is back where it was after the ``call`` (``sim.stack_imbalance``), the return
  address there is still the right one (``sim.bad_return``), the callee-saved registers of the ABI were
  restored (``sim.callee_saved``);
* ``call`` of a library function (64-bit): RSP 16-byte aligned (``sim.misaligned_call``), Windows x64 shadow
  space present (``sim.no_shadow_space``); pointer arguments valid (``sim.bad_pointer_arg``, in the stubs);
* memory: unmapped / null / read-only accesses with the faulting instruction (``sim.null_deref``,
  ``sim.mem_violation``, ``sim.write_readonly``, ``sim.stack_overflow``), stack bytes read before they were
  written (``sim.uninit_read``), writes outside the data label the instruction points into
  (``sim.buffer_overflow``: the label comes from the instruction's relocation or from the register that was
  loaded with ``lea`` / ``mov reg, label``);
* ``div`` / ``idiv`` faults explained with the operand values (``sim.div_zero`` / ``sim.div_overflow``);
* running into data or past the last instruction (``sim.exec_data``, ``sim.ran_off_end``), invalid bytes;
* the step limit: the hottest loop with its jump and the registers its condition tests (``sim.infinite_loop``).

``trace_addrs`` records, for "Explain this line", the registers before / after and the memory written by every
execution of the given instruction addresses (``Runner.traces``).
"""
from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field

from . import objload as L
from .model import CallLog, Finding, SimResult
from .stubs import StopRun, Stubs, ret_bytes

try:                                                         # optional dependency (pip install unicorn)
    import unicorn as U
    from unicorn import x86_const as X
except ImportError:                                          # pragma: no cover - checked by available()
    U = None
    X = None

try:
    import capstone as C
    from capstone import x86_const as CX
except ImportError:                                          # pragma: no cover
    C = None
    CX = None

GPR64 = ("rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14",
         "r15")
GPR32 = ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp")
CALLEE_SAVED = {"win64": ("rbx", "rbp", "rdi", "rsi", "r12", "r13", "r14", "r15"),
                "sysv": ("rbx", "rbp", "r12", "r13", "r14", "r15"),
                "x86": ("ebx", "esi", "edi", "ebp")}
VOLATILE = {"win64": "RAX RCX RDX R8 R9 R10 R11", "sysv": "RAX RCX RDX RSI RDI R8-R11", "x86": "EAX ECX EDX"}
ABI_NAMES = {"win64": "Windows x64", "sysv": "System V (Linux x86-64)", "x86": "32-bit cdecl / stdcall"}
FAMILY = {}
for _f in GPR64:
    FAMILY[_f] = _f
for _a, _b in (("eax", "rax"), ("ax", "rax"), ("al", "rax"), ("ah", "rax"), ("ebx", "rbx"), ("bx", "rbx"),
               ("bl", "rbx"), ("bh", "rbx"), ("ecx", "rcx"), ("cx", "rcx"), ("cl", "rcx"), ("ch", "rcx"),
               ("edx", "rdx"), ("dx", "rdx"), ("dl", "rdx"), ("dh", "rdx"), ("esi", "rsi"), ("si", "rsi"),
               ("sil", "rsi"), ("edi", "rdi"), ("di", "rdi"), ("dil", "rdi"), ("ebp", "rbp"), ("bp", "rbp"),
               ("bpl", "rbp"), ("esp", "rsp"), ("sp", "rsp"), ("spl", "rsp")):
    FAMILY[_a] = _b
for _n in range(8, 16):
    for _s in ("", "d", "w", "b"):
        FAMILY[f"r{_n}{_s}"] = f"r{_n}"


def available() -> bool:
    return U is not None and C is not None


def family(reg: str) -> str:
    return FAMILY.get(reg.lower(), reg.lower())


def reg_const(name: str) -> int:
    return getattr(X, "UC_X86_REG_" + name.upper())


@dataclass
class Frame:
    ret: int                       # expected return address
    entry_sp: int                  # stack pointer right after the call (points at the return address)
    proc: str
    call_line: tuple | None
    saved: dict = field(default_factory=dict)
    pushes: int = 0
    pops: int = 0


@dataclass
class Trace:
    addr: int
    before: dict
    after: dict | None = None
    writes: list = field(default_factory=list)     # [(addr, size, old bytes, new value)]
    reads: list = field(default_factory=list)      # [(addr, size, value)]
    iteration: int = 0


class Runner:
    STACK_BASE = 0x0E000000
    STACK_SIZE = 0x00100000
    HEAP_BASE = 0x10000000
    HEAP_SIZE = 0x00400000
    SENTINEL = L.STUB_BASE + 0xFF00

    def __init__(self, img: L.Image, abi: str, stdin: str = "", max_steps: int = 1_000_000,
                 timeout: float = 15.0, entry: int | None = None, entry_name: str = "",
                 stop_outside: tuple | None = None, trace_addrs=None, max_traces: int = 64, init_regs=None):
        if not available():
            raise RuntimeError("unicorn / capstone are not installed")
        self.img = img
        self.abi = abi
        self.bits = img.bits
        self.sp_name = "rsp" if self.bits == 64 else "esp"
        self.ip_name = "rip" if self.bits == 64 else "eip"
        self.ax_name = "rax" if self.bits == 64 else "eax"
        self.stdin = stdin
        self.max_steps = max_steps
        self.timeout = timeout
        self.entry = entry
        self.entry_name = entry_name
        self.stop_outside = stop_outside
        self.trace_addrs = set(trace_addrs or ())
        self.max_traces = max_traces
        self.init_regs = dict(init_regs or {})
        self.result = SimResult(engine="unicorn", abi=abi)
        self.output: list[str] = []
        self.calls = self.result.calls
        self.steps = 0
        self.frames: list[Frame] = []
        self.pending_call = None
        self.cur = 0                         # address of the instruction being executed
        self.cur_ins = None
        self.last_addr = 0
        self.last_ins = None
        self.fault = None
        self.stopped_by_us = False
        self.fatal = False
        self.recent = collections.deque(maxlen=20000)
        self.loop_snapshot = None
        self.written = bytearray(self.STACK_SIZE)
        self.stack_writer: dict[int, tuple] = {}
        self.tags: dict[str, L.Label] = {}
        self.traces: dict[int, list[Trace]] = {}
        self._trace_open: Trace | None = None
        self._dec_cache: dict[int, object] = {}
        self._unknown: set[str] = set()
        self._reported: set = set()
        self._code_end: dict[int, int] = {}
        self.input_missing = ""
        self.md = C.Cs(C.CS_ARCH_X86, C.CS_MODE_64 if self.bits == 64 else C.CS_MODE_32)
        self.md.detail = True
        self.stubs = Stubs(self)
        self._regs_cache = {}

    # ================================================================== helpers for the stubs
    def reg(self, name: str) -> int:
        c = self._regs_cache.get(name)
        if c is None:
            c = self._regs_cache[name] = reg_const(name)
        return self.uc.reg_read(c)

    def set_reg(self, name: str, v: int) -> None:
        c = self._regs_cache.get(name)
        if c is None:
            c = self._regs_cache[name] = reg_const(name)
        self.uc.reg_write(c, v & ((1 << 64) - 1 if self.bits == 64 or name.startswith("r") else 0xFFFFFFFF))

    def set_ret(self, v: int) -> None:
        self.set_reg(self.ax_name, v)

    def xmm_double(self, i: int) -> float:
        import struct
        v = self.uc.reg_read(getattr(X, f"UC_X86_REG_XMM{i}"))
        return struct.unpack("<d", struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF))[0]

    def valid(self, addr: int, size: int = 1) -> bool:
        if addr < 0x10000:
            return False
        try:
            self.uc.mem_read(addr, 1)
            if size > 1:
                self.uc.mem_read(addr + size - 1, 1)
            return True
        except U.UcError:
            return False

    def read(self, addr: int, n: int) -> bytes:
        return bytes(self.uc.mem_read(addr, n))

    def read_int(self, addr: int, n: int) -> int:
        try:
            return int.from_bytes(self.uc.mem_read(addr, n), "little")
        except U.UcError:
            return 0

    def write(self, addr: int, data: bytes) -> None:
        if not data:
            return
        self.uc.mem_write(addr, bytes(data))
        self._mark_written(addr, len(data))

    def out(self, s: str) -> None:
        self.output.append(s)

    def log_call(self, name: str, args: str, result: str) -> None:
        f, line = (self.frames[-1].call_line if self.frames and self.frames[-1].call_line else ("", 0))
        if len(self.calls) < 500:
            self.calls.append(CallLog(name, args, result, line, f))

    def finish(self, how: str, code: int | None) -> None:
        self.result.ended = how
        self.result.exit_code = code
        self.stopped_by_us = True
        self.uc.emu_stop()

    def input_short(self, func: str) -> None:
        if not self.input_missing:
            self.input_missing = func

    def unknown_extern(self, name: str) -> None:
        if name in self._unknown:
            return
        self._unknown.add(name)
        f, ln = self._caller_line()
        self.result.add(Finding("sim.unknown_extern", f, ln, {"name": name}))

    def bad_pointer(self, func, param, index, value, what_en, what_ar, loc, reg) -> None:
        f, ln = self._caller_line()
        self.add(Finding("sim.bad_pointer_arg", f, ln, {
            "func": func, "param": param, "index": index + 1, "value": self._hex(value), "what": what_en,
            "what_ar": what_ar, "loc": loc, "reg": reg, "abi": ABI_NAMES.get(self.abi, self.abi)}, ref="lea"))
        self.fatal = True

    # ================================================================== small utilities
    def _hex(self, v: int) -> str:
        return f"0x{v:X}"

    def line_of(self, addr: int):
        return self.img.line_of(addr)

    def _line(self, addr: int) -> tuple[str, int]:
        r = self.img.line_of(addr)
        return r if r else ("", 0)

    def _caller_line(self) -> tuple[str, int]:
        if self.frames and self.frames[-1].call_line:
            return self.frames[-1].call_line
        return self._line(self.last_addr)

    def add(self, f: Finding) -> None:
        key = (f.rule, f.file, f.line)
        if key in self._reported:
            return
        self._reported.add(key)
        self.result.add(f)

    def _decode(self, addr: int):
        ins = self._dec_cache.get(addr)
        if ins is None:
            try:
                code = bytes(self.uc.mem_read(addr, 16))
            except U.UcError:
                return None
            ins = next(self.md.disasm(code, addr, 1), None)
            self._dec_cache[addr] = ins
        return ins

    def _ins_text(self, ins) -> str:
        """The instruction as the user wrote it (its source line), else capstone's text."""
        if ins is None:
            return "?"
        src = self.img.source_text(ins.address)
        if src and src.split()[0].lower().rstrip(":") in (ins.mnemonic.split()[-1], *ins.mnemonic.split()) or (
                src and ins.mnemonic.startswith("rep")):
            return src
        return f"{ins.mnemonic} {ins.op_str}".strip()

    def _mark_written(self, addr: int, n: int) -> None:
        lo = addr - self.STACK_BASE
        if 0 <= lo < self.STACK_SIZE:
            hi = min(self.STACK_SIZE, lo + n)
            self.written[lo:hi] = b"\1" * (hi - lo)

    def regs_snapshot(self) -> dict:
        names = GPR64 if self.bits == 64 else GPR32
        d = {n: self.reg(n) for n in names}
        d[self.ip_name] = self.reg(self.ip_name)
        d["eflags"] = self.reg("eflags")
        return d

    def _mem_operand(self, ins):
        if ins is None:
            return None
        for op in ins.operands:
            if op.type == CX.X86_OP_MEM:
                return op
        return None

    def _mem_regs_text(self, ins) -> tuple[str, str]:
        """("RBX = 0x0, RCX = 0x10", "rbx") of the registers inside [ ] of *ins*."""
        op = self._mem_operand(ins)
        if op is None:
            return "", ""
        parts, first = [], ""
        for r in (op.mem.base, op.mem.index):
            if r and r not in (CX.X86_REG_RIP, CX.X86_REG_EIP):
                name = ins.reg_name(r)
                first = first or name
                try:
                    parts.append(f"{name.upper()} = {self._hex(self.reg(name))}")
                except Exception:  # noqa: BLE001
                    pass
        return ", ".join(parts), first

    def _proc_name(self, addr: int) -> str:
        lab = self.img.proc_of(addr)
        return lab.name if lab is not None else (self.entry_name or self.img.describe(addr))

    # ================================================================== set-up
    def _setup(self) -> int:
        mode = U.UC_MODE_64 if self.bits == 64 else U.UC_MODE_32
        uc = self.uc = U.Uc(U.UC_ARCH_X86, mode)
        for r in self.img.regions:
            perms = U.UC_PROT_READ | (U.UC_PROT_WRITE if r.write else 0) | (U.UC_PROT_EXEC if r.execute else 0)
            uc.mem_map(r.start, r.size, perms)
            if r.data:
                uc.mem_write(r.start, r.data)
            if r.execute:
                ends = [a + n for a, n, f, ln in self.img.line_rows if r.start <= a < r.start + r.size]
                self._code_end[r.start] = max(ends) if ends else r.start
        uc.mem_map(L.STUB_BASE, 0x10000, U.UC_PROT_READ | U.UC_PROT_EXEC)
        for addr, name in self.img.stub_names.items():
            uc.mem_write(addr, ret_bytes(name, self.bits))
        for slot, target in self.img.iat.items():
            uc.mem_write(slot, target.to_bytes(8 if self.bits == 64 else 4, "little"))
        uc.mem_write(self.SENTINEL, b"\xF4")
        uc.mem_map(self.STACK_BASE, self.STACK_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
        uc.mem_map(self.HEAP_BASE, self.HEAP_SIZE, U.UC_PROT_READ | U.UC_PROT_WRITE)
        # argv: ["program.exe", NULL]
        argv = self.HEAP_BASE + 0x40
        w = 8 if self.bits == 64 else 4
        uc.mem_write(self.HEAP_BASE + 0x20, b"program.exe\0")
        uc.mem_write(argv, (self.HEAP_BASE + 0x20).to_bytes(w, "little") + bytes(w))
        top = self.STACK_BASE + self.STACK_SIZE - 0x200
        sp = top
        # callee-saved registers get recognisable values (changes are reported at 'ret')
        patterns = {"rbx": 0x0B0B0B0B, "rsi": 0x05150515, "rdi": 0x0D1D0D1D, "r12": 0x12121212,
                    "r13": 0x13131313, "r14": 0x14141414, "r15": 0x15151515,
                    "ebx": 0x0B0B0B0B, "esi": 0x05150515, "edi": 0x0D1D0D1D}
        for name in CALLEE_SAVED.get(self.abi, ()):
            if name in patterns:
                self.set_reg(name, patterns[name])
        if self.bits == 64:
            self.set_reg("rbp", top + 0x100)
            if self.abi == "win64":
                self.set_reg("rcx", 1)
                self.set_reg("rdx", argv)
            else:
                self.set_reg("rdi", 1)
                self.set_reg("rsi", argv)
            sp -= 32 if self.abi == "win64" else 0                 # the caller's shadow space
            sp -= 8
            uc.mem_write(sp, self.SENTINEL.to_bytes(8, "little"))
        else:
            self.set_reg("ebp", top + 0x100)
            sp -= 8
            uc.mem_write(sp, (1).to_bytes(4, "little") + argv.to_bytes(4, "little"))
            sp -= 4
            uc.mem_write(sp, self.SENTINEL.to_bytes(4, "little"))
        self._mark_written(sp, self.STACK_BASE + self.STACK_SIZE - sp)
        self.set_reg(self.sp_name, sp)
        for k, v in self.init_regs.items():
            self.set_reg(k, v)
        entry = self.entry
        self.frames.append(Frame(self.SENTINEL, sp, self.entry_name or self._proc_name(entry), None,
                                 self._saved_regs()))
        uc.hook_add(U.UC_HOOK_CODE, self._on_code)
        uc.hook_add(U.UC_HOOK_MEM_WRITE, self._on_write)
        uc.hook_add(U.UC_HOOK_MEM_READ, self._on_read, begin=self.STACK_BASE,
                    end=self.STACK_BASE + self.STACK_SIZE - 1)
        uc.hook_add(U.UC_HOOK_MEM_INVALID, self._on_invalid)
        uc.hook_add(U.UC_HOOK_INTR, self._on_intr)
        if self.bits == 64:
            uc.hook_add(U.UC_HOOK_INSN, self._on_syscall, None, 1, 0, X.UC_X86_INS_SYSCALL)
        return entry

    def _saved_regs(self) -> dict:
        return {n: self.reg(n) for n in CALLEE_SAVED.get(self.abi, ())}

    # ================================================================== hooks
    def _on_code(self, uc, addr, size, _ud):
        self.steps += 1
        if self._trace_open is not None:
            self._close_trace()
        if self.pending_call is not None:
            call_addr, ret_addr = self.pending_call
            self.pending_call = None
            sp = self.reg(self.sp_name)
            name = self.img.stub_names.get(addr) or self._label_name(addr)
            self.frames.append(Frame(ret_addr, sp, name, self._line(call_addr), self._saved_regs()))
        if addr == self.SENTINEL:
            self.result.ended = "return"
            self.result.exit_code = self.reg("eax") & 0xFFFFFFFF
            if self.result.exit_code & 0x80000000:
                self.result.exit_code -= 1 << 32
            self.stopped_by_us = True
            uc.emu_stop()
            return
        name = self.img.stub_names.get(addr)
        if name is not None:
            self.cur = addr
            try:
                self.stubs.call(name)
            except StopRun:
                self.stopped_by_us = True
                uc.emu_stop()
            if len(self.frames) > 1:
                # the stub's own frame, or (a tail call: jmp printf) the frame its 'ret' returns from
                self.frames.pop()
            if self.input_missing and not self.stopped_by_us:
                self.result.ended = "input"
                self.stopped_by_us = True
                uc.emu_stop()
            return
        if self.steps > self.max_steps:
            self.result.ended = "limit"
            self.stopped_by_us = True
            uc.emu_stop()
            return
        if self.steps == self.max_steps - 5000:
            self.loop_snapshot = self.regs_snapshot()
        if self.stop_outside is not None and len(self.frames) == 1:
            lo, hi = self.stop_outside
            if not lo <= addr < hi:
                self.result.ended = "return"
                self.stopped_by_us = True
                uc.emu_stop()
                return
        ins = self._decode(addr)
        self.last_addr, self.last_ins = self.cur, self.cur_ins
        self.cur, self.cur_ins = addr, ins
        self.recent.append(addr)
        # ran past the last instruction of its code section (into the zero padding)
        if self.img.line_of(addr) is None:
            r = self.img.region_of(addr)
            if r is not None and r.execute and addr >= self._code_end.get(r.start, r.start + r.size) and \
                    self.last_ins is not None:
                f, ln = self.img.code_end_line() or ("", 0)
                f, ln = self._line(self.last_addr) if self._line(self.last_addr)[1] else (f, ln)
                self.add(Finding("sim.ran_off_end", f, ln, {"addr": self._hex(addr), "line_last": ln},
                                 instr=self._ins_text(self.last_ins)))
                self._stop_fault(uc)
                return
        if ins is None:
            return
        if addr in self.trace_addrs:
            lst = self.traces.setdefault(addr, [])
            if len(lst) < self.max_traces:
                self._trace_open = Trace(addr, self.regs_snapshot(), iteration=len(lst) + 1)
                lst.append(self._trace_open)
        mn = ins.mnemonic
        if mn == "call":
            self._on_call(addr, ins)
        elif mn.startswith("ret"):
            self._on_ret(addr, ins)
            if self.fatal:
                self._stop_fault(uc)
                return
        elif mn == "push" and self.frames:
            self.frames[-1].pushes += 1
        elif mn == "pop" and self.frames:
            self.frames[-1].pops += 1
        self._update_tags(addr, ins)

    def _label_name(self, addr: int) -> str:
        lab = self.img.label_at(addr, code=True)
        return lab.name if lab is not None and lab.addr == addr else self.img.describe(addr)

    def _close_trace(self) -> None:
        t = self._trace_open
        self._trace_open = None
        t.after = self.regs_snapshot()

    def _stop_fault(self, uc) -> None:
        self.fatal = True
        self.result.ended = "fault"
        self.stopped_by_us = True
        uc.emu_stop()

    def _on_call(self, addr: int, ins) -> None:
        target = None
        op = ins.operands[0] if ins.operands else None
        if op is not None and op.type == CX.X86_OP_IMM:
            target = op.imm
        elif op is not None and op.type == CX.X86_OP_MEM:
            ea = self._effective_address(ins, op)
            if ea is not None:
                target = self.read_int(ea, 8 if self.bits == 64 else 4)
        elif op is not None and op.type == CX.X86_OP_REG:
            target = self.reg(ins.reg_name(op.reg))
        self.pending_call = (addr, addr + ins.size)
        if target is None or target not in self.img.stub_names or self.bits != 64:
            return
        sp = self.reg("rsp")
        fname = self.img.stub_names[target]
        f, ln = self._line(addr)
        if sp % 16:
            self.add(Finding("sim.misaligned_call", f, ln, {"sp": "RSP", "target": fname, "mod": sp % 16},
                             addr=addr, instr=self._ins_text(ins)))
        if self.abi == "win64" and self.frames:
            caller = self.frames[-1]
            # the callee's home area is [sp+8+... ] after the call = [sp, sp+32) now
            if sp + 32 > caller.entry_sp:
                victim_en = f"the return address of {caller.proc}" if sp + 32 > caller.entry_sp else "saved registers"
                self.add(Finding("sim.no_shadow_space", f, ln, {"target": fname, "victim": victim_en},
                                 addr=addr, instr=self._ins_text(ins), ref="call"))

    def _on_ret(self, addr: int, ins) -> None:
        sp = self.reg(self.sp_name)
        w = 8 if self.bits == 64 else 4
        ret_to = self.read_int(sp, w)
        if not self.frames:
            return
        fr = self.frames[-1]
        f, ln = self._line(addr)
        spn = self.sp_name.upper()
        if sp != fr.entry_sp:
            delta = fr.entry_sp - sp
            if delta > 0:
                state_en, state_ar = "still on the stack", "ما زالت على المكدس"
            else:
                state_en, state_ar = "popped too many", "أُخرجت زيادة من المكدس"
            self.add(Finding("sim.stack_imbalance", f, ln, {
                "proc": fr.proc, "bytes": abs(delta), "state": state_en, "state_ar": state_ar, "sp": spn,
                "sp_entry": self._hex(fr.entry_sp), "sp_now": self._hex(sp), "target": self.img.describe(ret_to),
                "pushes": fr.pushes, "pops": fr.pops}, addr=addr, instr=self._ins_text(ins)))
            self.fatal = True
            return
        if ret_to != fr.ret:
            wl = self.stack_writer.get(sp)
            self.add(Finding("sim.bad_return", f, ln, {
                "proc": fr.proc, "target": self.img.describe(ret_to), "expected": self.img.describe(fr.ret),
                "sp": spn, "writer_line": wl[1] if wl else "?"}, addr=addr, instr=self._ins_text(ins)))
            self.fatal = True
            return
        changed = [n for n, v in fr.saved.items() if n not in ("rsp", "esp") and self.reg(n) != v]
        if changed:
            regs = ", ".join(n.upper() for n in changed)
            self.add(Finding("sim.callee_saved", f, ln, {
                "proc": fr.proc, "regs": regs, "them": "it" if len(changed) == 1 else "them",
                "them_ar": "قيمته" if len(changed) == 1 else "قيمها",
                "abi": ABI_NAMES.get(self.abi, self.abi),
                "all_regs": " ".join(n.upper() for n in CALLEE_SAVED.get(self.abi, ())),
                "first": changed[0], "volatile": VOLATILE.get(self.abi, "")}, addr=addr, instr=self._ins_text(ins)))
        if len(self.frames) > 1:
            self.frames.pop()

    def _effective_address(self, ins, op) -> int | None:
        m = op.mem
        try:
            ea = m.disp
            if m.base:
                if m.base in (CX.X86_REG_RIP, CX.X86_REG_EIP):
                    ea += ins.address + ins.size
                else:
                    ea += self.reg(ins.reg_name(m.base))
            if m.index:
                ea += self.reg(ins.reg_name(m.index)) * m.scale
            return ea & ((1 << self.bits) - 1)
        except Exception:  # noqa: BLE001
            return None

    def _reloc_label(self, ins) -> L.Label | None:
        # a RIP-relative operand gives the exact address (relocations are already applied); the relocation's
        # addend does not: NASM puts -4 in a COFF REL32 field when an imm32 follows ('mov dword [a], 0'), and that
        # address falls into the previous variable
        op = self._mem_operand(ins)
        if op is not None and op.mem.base == CX.X86_REG_RIP:
            return self.img.label_at(ins.address + ins.size + op.mem.disp, code=False)
        for k in range(ins.size):
            t = self.img.reloc_targets.get(ins.address + k)
            if t is not None:
                return self.img.label_at(t, code=False)
        return None

    def _update_tags(self, addr: int, ins) -> None:
        """Which data label each register points into (for the buffer checks)."""
        ops = ins.operands
        if not ops or ops[0].type != CX.X86_OP_REG:
            if ins.mnemonic == "call":
                self.tags.pop("rax", None)
            return
        dst = family(ins.reg_name(ops[0].reg))
        mn = ins.mnemonic
        if mn in ("lea", "mov") and len(ops) == 2:
            src = ops[1]
            if mn == "lea" or src.type == CX.X86_OP_IMM:
                lab = self._reloc_label(ins)
                if lab is not None:
                    self.tags[dst] = lab
                    return
                if mn == "lea" and src.type == CX.X86_OP_MEM:
                    base = family(ins.reg_name(src.mem.base)) if src.mem.base else ""
                    if base in self.tags:
                        self.tags[dst] = self.tags[base]
                        return
            elif src.type == CX.X86_OP_REG:
                s = family(ins.reg_name(src.reg))
                if s in self.tags:
                    self.tags[dst] = self.tags[s]
                else:
                    self.tags.pop(dst, None)
                return
            self.tags.pop(dst, None)
        elif mn in ("add", "sub", "inc", "dec"):
            return
        elif mn in ("cmp", "test", "push"):
            return
        else:
            self.tags.pop(dst, None)

    # -- memory
    def _on_write(self, uc, access, addr, size, value, _ud):
        if self._trace_open is not None and self._trace_open.addr == self.cur:
            try:
                old = bytes(uc.mem_read(addr, size))
            except U.UcError:
                old = b""
            self._trace_open.writes.append((addr, size, old, value))
        lo = addr - self.STACK_BASE
        if 0 <= lo < self.STACK_SIZE:
            self.written[lo:lo + size] = b"\1" * size
            if self.cur:
                self.stack_writer[addr] = self._line(self.cur)
            return
        ins = self.cur_ins
        if ins is None or self.cur in self.img.stub_names:
            return
        op = self._mem_operand(ins)
        lab = None
        if op is not None:
            base = family(ins.reg_name(op.mem.base)) if op.mem.base and op.mem.base != CX.X86_REG_RIP else ""
            index = family(ins.reg_name(op.mem.index)) if op.mem.index else ""
            lab = self._reloc_label(ins) or self.tags.get(base) or (self.tags.get(index) if not base else None)
        elif ins.mnemonic.startswith(("stos", "movs", "rep")):
            lab = self.tags.get("rdi")
        if lab is None or lab.size <= 0:
            return
        if lab.addr <= addr and addr + size <= lab.addr + lab.size:
            return
        f, ln = self._line(self.cur)
        victim = self.img.label_at(addr, code=False)
        past = addr + size - (lab.addr + lab.size)
        if addr < lab.addr:
            past = addr - lab.addr
        vname = victim.name if victim is not None and victim is not lab else ""
        idx_reg = ""
        if op is not None and op.mem.index:
            idx_reg = ins.reg_name(op.mem.index)
        elif op is not None and op.mem.base and op.mem.base != CX.X86_REG_RIP:
            idx_reg = ins.reg_name(op.mem.base)
        self.add(Finding("sim.buffer_overflow", f, ln, {
            "label": lab.name, "size": lab.size, "label_line": lab.line, "target": f"{lab.name}+{addr - lab.addr}",
            "offset": addr - lab.addr, "past": past, "index": idx_reg or "index",
            "count": lab.size // max(1, size),
            "victim_en": f" - it overwrites '{vname}'" if vname else "",
            "victim_ar": f" - وتكتب فوق '{vname}'" if vname else "",
            "victim_why": f" - here the variable '{vname}' (line {victim.line}) is damaged" if vname else "",
            "victim_why_ar": f" - وهنا يتلف المتغير '{vname}' (السطر {victim.line})" if vname else ""},
            addr=self.cur, instr=self._ins_text(ins), ref="times"))

    def _on_read(self, uc, access, addr, size, value, _ud):
        lo = addr - self.STACK_BASE
        if self._trace_open is not None and self._trace_open.addr == self.cur:
            self._trace_open.reads.append((addr, size, self.read_int(addr, size)))
        if lo < 0 or lo + size > self.STACK_SIZE:
            return
        if all(self.written[lo:lo + size]):
            return
        ins = self.cur_ins
        if ins is None or self.cur in self.img.stub_names:
            return
        f, ln = self._line(self.cur)
        if not ln:
            return
        bp = self.reg("rbp" if self.bits == 64 else "ebp")
        sp = self.reg(self.sp_name)
        bpn, spn = ("rbp", "rsp") if self.bits == 64 else ("ebp", "esp")
        if self.STACK_BASE <= bp < self.STACK_BASE + self.STACK_SIZE and abs(addr - bp) < 0x10000:
            off = addr - bp
            short = f"{bpn}{'+' if off >= 0 else '-'}{abs(off)}"
        else:
            off = addr - sp
            short = f"{spn}+{off}"
        sizekw = {1: "byte", 2: "word", 4: "dword", 8: "qword"}.get(size, "qword")
        proc = self.frames[-1].proc if self.frames else self._proc_name(self.cur)
        self.add(Finding("sim.uninit_read", f, ln, {"where": f"[{short}]", "where_short": short, "size": size,
                                                    "sizekw": sizekw, "proc": proc},
                         addr=self.cur, instr=self._ins_text(ins)))
        self.written[lo:lo + size] = b"\1" * size        # report once per location

    def _on_invalid(self, uc, access, addr, size, value, _ud):
        kind = {U.UC_MEM_READ_UNMAPPED: "read", U.UC_MEM_READ_PROT: "read", U.UC_MEM_WRITE_UNMAPPED: "write",
                U.UC_MEM_WRITE_PROT: "write", U.UC_MEM_FETCH_UNMAPPED: "fetch",
                U.UC_MEM_FETCH_PROT: "fetch"}.get(access, "read")
        self.fault = (kind, addr, size, access in (U.UC_MEM_WRITE_PROT, U.UC_MEM_READ_PROT, U.UC_MEM_FETCH_PROT))
        return False

    def _on_intr(self, uc, intno, _ud):
        if intno == 0x80 and self.bits == 32:
            n = self.reg("eax")
            args = [self.reg(r) for r in ("ebx", "ecx", "edx", "esi", "edi")]
            try:
                res = self.stubs.syscall(n, args, True)
            except StopRun:
                self.stopped_by_us = True
                uc.emu_stop()
                return
            self.set_reg("eax", 0xFFFFFFDA if res is None else res)
            return
        if intno == 3:
            return
        ins = self.cur_ins
        f, ln = self._line(self.cur)
        if intno == 0 and ins is not None:
            self._divide_error(ins, f, ln)
        elif intno == 6:
            self.add(Finding("sim.bad_opcode", f, ln, {"addr": self._hex(self.cur), "bytes": self._bytes_at(self.cur)}))
        else:
            self.add(Finding("sim.mem_violation", f, ln, {
                "access": f"Interrupt {intno} in", "access_ar": f"المقاطعة {intno} في", "addr": self._hex(self.cur),
                "regs": "-"}, addr=self.cur, instr=self._ins_text(ins)))
        self._stop_fault(uc)

    def _on_syscall(self, uc, _ud):
        n = self.reg("rax")
        args = [self.reg(r) for r in ("rdi", "rsi", "rdx", "r10", "r8", "r9")]
        try:
            res = self.stubs.syscall(n, args, False)
        except StopRun:
            self.stopped_by_us = True
            uc.emu_stop()
            return
        self.set_reg("rax", (1 << 64) - 38 if res is None else res)

    def _bytes_at(self, addr: int) -> str:
        try:
            return " ".join(f"{b:02X}" for b in self.uc.mem_read(addr, 4))
        except U.UcError:
            return "?"

    def _divide_error(self, ins, f, ln) -> None:
        op = ins.operands[0] if ins.operands else None
        size = op.size if op is not None else 4
        if op is not None and op.type == CX.X86_OP_REG:
            dname = ins.reg_name(op.reg).upper()
            dval = self.reg(ins.reg_name(op.reg))
        elif op is not None and op.type == CX.X86_OP_MEM:
            ea = self._effective_address(ins, op)
            dname = f"{ {1: 'byte', 2: 'word', 4: 'dword', 8: 'qword'}.get(size, '')} [{self.img.describe(ea or 0)}]"
            dval = self.read_int(ea, size) if ea is not None else 0
        else:
            dname, dval = "?", 0
        names = {1: ("AX", "AH", "AL", "AH", "cbw"), 2: ("DX:AX", "DX", "AX", "DX", "cwd"),
                 4: ("EDX:EAX", "EDX", "EAX", "EDX", "cdq"), 8: ("RDX:RAX", "RDX", "RAX", "RDX", "cqo")}
        dividend, hi, qreg, hi32, cdq = names.get(size, names[4])
        if size == 1:
            ax = self.reg("eax") & 0xFFFF
            dv, hv = ax, ax >> 8
        else:
            lo_name = {2: "eax", 4: "eax", 8: "rax"}[size]
            hi_name = {2: "edx", 4: "edx", 8: "rdx"}[size]
            mask = (1 << (8 * size)) - 1
            lo_v, hv = self.reg(lo_name) & mask, self.reg(hi_name) & mask
            dv = (hv << (8 * size)) | lo_v
        dval &= (1 << (8 * size)) - 1
        args = {"mn": ins.mnemonic, "divisor": dname, "dividend": dividend, "qreg": qreg if size > 1 else "AL",
                "divisor_value": dval, "dividend_value": dv, "hi": hi, "hi_value": self._hex(hv),
                "hi32": {"DX": "dx", "EDX": "edx", "RDX": "edx", "AH": "ah"}.get(hi32, "edx"),
                "cdq": cdq}
        rule = "sim.div_zero" if dval == 0 else "sim.div_overflow"
        self.add(Finding(rule, f, ln, args, addr=self.cur, instr=self._ins_text(ins), ref=ins.mnemonic))

    # ================================================================== run
    def run(self) -> SimResult:
        entry = self._setup()
        t0 = time.time()
        try:
            self.uc.emu_start(entry, 0, timeout=int(self.timeout * 1_000_000), count=0)
        except U.UcError as e:
            self._after_error(e)
        if self._trace_open is not None:
            self._close_trace()
        res = self.result
        res.steps = self.steps
        res.output = "".join(self.output)
        if not res.ended:
            if self.fault is not None or self.fatal:
                res.ended = "fault"
            elif time.time() - t0 >= self.timeout * 0.95 or self.steps >= self.max_steps:
                res.ended = "limit"
            else:
                res.ended = "stopped"
        if res.ended == "limit":
            self._report_loop()
        if self.input_missing:
            f, ln = self._caller_line()
            self.result.add(Finding("sim.waiting_input", f, ln, {"func": self.input_missing}))
        res.status = "findings" if res.problems else "ok"
        return res

    def _after_error(self, e) -> None:
        if self.fatal and self.result.findings:
            return
        ins = self.cur_ins
        f, ln = self._line(self.cur)
        if self.fault is None:
            if getattr(e, "errno", None) == U.UC_ERR_INSN_INVALID:
                self.add(Finding("sim.bad_opcode", f, ln, {"addr": self._hex(self.cur), "bytes": self._bytes_at(self.cur)}))
            else:
                self.add(Finding("sim.mem_violation", f, ln, {"access": "Error", "access_ar": "خطأ",
                                                              "addr": self._hex(self.cur), "regs": str(e)},
                                 addr=self.cur, instr=self._ins_text(ins)))
            self.result.ended = "fault"
            return
        kind, addr, size, prot = self.fault
        self.result.ended = "fault"
        acc_en, acc_ar = {"read": ("Reading", "قراءة"), "write": ("Writing to", "الكتابة في"),
                          "fetch": ("Running code at", "تنفيذ كود عند")}[kind]
        if kind == "fetch":
            self._fetch_fault(addr, prot)
            return
        regs, first = self._mem_regs_text(ins)
        if not regs and ins is not None and ins.mnemonic.startswith(("push", "call", "pop", "ret")):
            regs = f"{self.sp_name.upper()} = {self._hex(self.reg(self.sp_name))}"
        args = {"access": acc_en, "access_ar": acc_ar, "addr": self._hex(addr), "regs": regs or "-",
                "reg": first or ("rbx" if self.bits == 64 else "ebx")}
        if self.STACK_BASE - 0x100000 <= addr < self.STACK_BASE:
            self.add(Finding("sim.stack_overflow", f, ln, {"size": self.STACK_SIZE // 1024,
                                                           "depth": len(self.frames) - 1},
                             addr=self.cur, instr=self._ins_text(ins)))
        elif prot and kind == "write":
            r = self.img.region_of(addr)
            sec = r.name if r is not None else "?"
            code = bool(r and r.execute)
            self.add(Finding("sim.write_readonly", f, ln, {
                "addr": self._hex(addr), "where": self.img.describe(addr), "section": sec,
                "why_extra": " (it holds the program's code)" if code else "",
                "why_extra_ar": " (فيه كود البرنامج)" if code else ""}, addr=self.cur, instr=self._ins_text(ins)))
        elif addr < 0x10000:
            self.add(Finding("sim.null_deref", f, ln, args, addr=self.cur, instr=self._ins_text(ins), ref="lea"))
        else:
            self.add(Finding("sim.mem_violation", f, ln, args, addr=self.cur, instr=self._ins_text(ins)))

    def _fetch_fault(self, addr: int, prot: bool) -> None:
        last = self.cur_ins
        lf, lln = self._line(self.cur)
        r = self.img.region_of(addr)
        mn = last.mnemonic if last is not None else ""
        fell = last is not None and addr == self.cur + last.size
        if r is not None and not r.execute:
            how_en = ("The previous instruction (line {}) is the last one before the data, and it does not jump "
                      "away.".format(lln)) if fell else f"The '{mn}' at line {lln} jumped there."
            how_ar = (f"التعليمة السابقة (السطر {lln}) هي آخر تعليمة قبل البيانات ولا تقفز بعيداً."
                      if fell else f"التعليمة '{mn}' في السطر {lln} قفزت إلى هناك.")
            self.add(Finding("sim.exec_data", lf, lln, {"addr": self._hex(addr), "where": self.img.describe(addr),
                                                        "how": how_en, "how_ar": how_ar},
                             addr=self.cur, instr=self._ins_text(last)))
        elif fell:
            self.add(Finding("sim.ran_off_end", lf, lln, {"addr": self._hex(addr), "line_last": lln},
                             addr=self.cur, instr=self._ins_text(last)))
        else:
            regs = ""
            if last is not None and last.operands and last.operands[0].type == CX.X86_OP_REG:
                n = last.reg_name(last.operands[0].reg)
                regs = f"{n.upper()} = {self._hex(self.reg(n))}"
            elif last is not None and last.operands and last.operands[0].type == CX.X86_OP_MEM:
                regs = self._mem_regs_text(last)[0] or "memory"
            self.add(Finding("sim.bad_jump", lf, lln, {"addr": self._hex(addr), "regs": regs or "-"},
                             addr=self.cur, instr=self._ins_text(last)))

    def _report_loop(self) -> None:
        addrs = list(self.recent)
        if not addrs:
            return
        counts = collections.Counter(addrs)
        lines = {}
        for a in counts:
            fl = self.img.line_of(a)
            if fl:
                lines[a] = fl
        if not lines:
            f, ln = self._line(self.cur)
            self.add(Finding("sim.infinite_loop", f, ln, {"steps": self.steps, "first": ln, "last": ln,
                                                          "count": "?", "jump_line": ln, "jump": "?",
                                                          "cond_en": "", "cond_ar": "", "regs_en": "",
                                                          "regs_ar": ""}))
            return
        # the backward jump executed most often
        best = None
        for a, n in counts.most_common():
            ins = self._decode(a)
            if ins is None or not ins.group(C.CS_GRP_JUMP):
                continue
            op = ins.operands[0] if ins.operands else None
            if op is not None and op.type == CX.X86_OP_IMM and op.imm <= a:
                best = (a, ins, op.imm, n)
                break
        if best is None:
            a = max(lines, key=lambda k: counts[k])
            f, ln = lines[a]
            first = last = ln
            jump_line, jump, n, ins, target = ln, self._ins_text(self._decode(a)), counts[a], None, a
        else:
            a, ins, target, n = best
            f, jump_line = lines.get(a, ("", 0))
            body = [lines[x][1] for x in lines if target <= x <= a and lines[x][0] == f]
            first, last = (min(body), max(body)) if body else (jump_line, jump_line)
            jump = self._ins_text(ins)
        cond_en = cond_ar = regs_en = regs_ar = ""
        if ins is not None and ins.mnemonic not in ("jmp",):
            from . import explain
            fl = self.reg("eflags")
            c = explain.condition_text(ins.mnemonic, fl)
            if c:
                cond_en, cond_ar = f" because {c['en']}", f" لأن {c['ar']}"
            # registers compared before the jump
            prev = self._compare_before(a)
            if prev is not None:
                names = [prev.reg_name(op.reg) for op in prev.operands if op.type == CX.X86_OP_REG]
                if self.loop_snapshot:
                    same = [r for r in names if family(r) in self.loop_snapshot or r in self.loop_snapshot]
                    parts_en, parts_ar = [], []
                    for r in same:
                        key = r if r in self.loop_snapshot else family(r)
                        now = self.reg(key)
                        if self.loop_snapshot.get(key) == now:
                            parts_en.append(f"{r.upper()} stays {now} - nothing in the loop changes it")
                            parts_ar.append(f"{r.upper()} يبقى {now} - لا شيء داخل الحلقة يغيّره")
                        else:
                            parts_en.append(f"{r.upper()} is now {now}")
                            parts_ar.append(f"{r.upper()} قيمته الآن {now}")
                    regs_en = f"'{self._ins_text(prev)}' compares: " + "; ".join(parts_en) + "." if parts_en else ""
                    regs_ar = f"'{self._ins_text(prev)}' تقارن: " + "؛ ".join(parts_ar) + "." if parts_ar else ""
        elif ins is not None:
            cond_en, cond_ar = " (an unconditional 'jmp' with no exit inside the loop)", \
                " (قفز غير مشروط jmp ولا يوجد خروج داخل الحلقة)"
        self.add(Finding("sim.infinite_loop", f, jump_line, {
            "steps": self.steps, "first": first, "last": last, "count": n, "jump_line": jump_line, "jump": jump,
            "cond_en": cond_en, "cond_ar": cond_ar, "regs_en": regs_en, "regs_ar": regs_ar},
            addr=a, instr=jump, ref=ins.mnemonic if ins is not None else "loop"))

    def _compare_before(self, jump_addr: int):
        """The last flag-setting instruction before the conditional jump at *jump_addr* (same line block)."""
        rows = [r for r in self.img.line_rows if r[0] < jump_addr]
        for a, _n, _f, _ln in reversed(rows[-8:]):
            ins = self._decode(a)
            if ins is None:
                continue
            if ins.mnemonic in ("cmp", "test", "sub", "add", "dec", "inc", "and", "or", "xor"):
                return ins
            if ins.group(C.CS_GRP_JUMP):
                return None
        return None
