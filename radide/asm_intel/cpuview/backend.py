"""The CPU view's one interface over two debuggers (callbacks everywhere: gdb answers asynchronously, the
8086 emulator at once).

* ``NativeBackend`` - any gdb session (``gdb -i dap``: assembly, C, C++, Rust, Fortran ...) through the helpers of
  radide/nativedbg.py (registers, readMemory / writeMemory, disassemble, instruction stepping, address
  breakpoints). Instructions come from gdb's disassemble request (its boundaries and symbols) and are analysed
  with capstone (jump kinds, targets, memory operands).
* ``EmuBackend`` - RAD IDE's own 8086 emulator (radide/emu8086: ``Emu8086Session.machine``). Linear addresses;
  the instructions are decoded with capstone in 16-bit mode, starting from instruction starts the assembler's
  listing knows.

``backend_for(win)`` picks the right one for the IDE's current debug session (None when nothing is paused).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import analysis as A


@dataclass
class Snapshot:
    regs: dict                      # lower-case name -> int (or None)
    order: list                     # names in display order
    texts: dict = field(default_factory=dict)     # name -> shown text for registers without a number (st0 ...)
    fam: dict = field(default_factory=dict)       # family -> value (analysis.normalize_registers)
    flags: int = 0
    pc: int | None = None
    sp: int | None = None
    bp: int | None = None
    bits: int = 64
    segs: dict = field(default_factory=dict)      # 'cs' -> value (16-bit)
    groups: dict = field(default_factory=dict)    # name -> General | Flags | Segments | FPU | SSE


GENERAL64 = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14",
             "r15", "rip"]
GENERAL32 = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip"]
GENERAL16 = ["ax", "bx", "cx", "dx", "si", "di", "bp", "sp", "ip"]


class Backend:
    kind = ""
    bits = 64

    def __init__(self, win):
        self.win = win

    # -- addresses
    @property
    def ptr(self) -> int:
        return self.bits // 8

    def fmt(self, a: int) -> str:
        return f"{a:0{max(8, self.bits // 4)}X}"

    def static(self, a: int) -> int:
        return a

    def dynamic(self, a: int) -> int:
        return a

    def program_key(self) -> tuple[str, str]:
        """(program name for the notes, its path)"""
        return "program", ""

    def source_of(self, a: int):
        return None

    def address_of_line(self, path, line: int) -> int | None:
        return None

    def alive(self) -> bool:
        return False


# ====================================================================== native (gdb)
class NativeBackend(Backend):
    kind = "native"

    def __init__(self, win, d):
        super().__init__(win)
        self.d = d
        self.bits = 64
        self._temp: int | None = None
        self._src: dict[int, tuple[str, int]] = {}      # address -> (file, line) from gdb (DWARF programs)

    def alive(self) -> bool:
        from ... import nativedbg as nd
        d = nd.dap_of(self.win.session)
        return d is self.d and nd.is_gdb(d) and bool(getattr(d, "paused", False))

    def program_key(self):
        prog = str(getattr(self.d, "launch_args", {}).get("program", "") or getattr(self.d, "program", "") or "")
        return (Path(prog).name or "program"), prog

    def static(self, a: int) -> int:
        return a - int(getattr(self.d, "slide", 0) or 0)

    def dynamic(self, a: int) -> int:
        return a + int(getattr(self.d, "slide", 0) or 0)

    def source_of(self, a: int):
        lm = getattr(self.d, "linemap", None)
        if lm:
            hit = lm.line_for(self.static(a))
            if hit:
                return hit
        return self._src.get(a)

    def address_of_line(self, path, line: int) -> int | None:
        lm = getattr(self.d, "linemap", None)
        if lm:
            hit = lm.address_for(path, line)
            if hit:
                return self.dynamic(hit[0])
        return None

    # -- state
    def snapshot(self, cb, extended: bool = False) -> None:
        from ... import nativedbg as nd

        def got(regs):
            vals, order, texts, groups = {}, [], {}, {}
            for name, text, num, _ref in regs:
                n = name.lower()
                if n in vals:
                    continue
                vals[n] = num
                texts[n] = text
                order.append(n)
                g = nd.register_group(n)
                groups[n] = "SSE" if g == "SSE / AVX" else g
            if "eflags" in vals and vals["eflags"] is None:
                vals["eflags"] = nd.flags_value(texts.get("eflags", ""))
            bits = 64 if "rax" in vals else 32
            self.bits = bits
            s = Snapshot(vals, order, texts, A.normalize_registers(vals), int(vals.get("eflags") or 0),
                         vals.get("rip", vals.get("eip", vals.get("pc"))),
                         vals.get("rsp", vals.get("esp")), vals.get("rbp", vals.get("ebp")), bits,
                         {k: vals[k] for k in ("cs", "ds", "es", "ss", "fs", "gs") if vals.get(k) is not None}, groups)
            cb(s)
        nd.read_registers(self.d, got, ("float", "sse") if extended else ())

    def read(self, addr: int, n: int, cb) -> None:
        from ... import nativedbg as nd

        def got(data, ok):
            if ok and len(data) >= n:
                cb(data)
                return
            if n <= 16:
                cb(data if ok else b"")
                return
            # part of the range is not mapped: read in 16-byte rows (unreadable rows stay empty)
            rows, out = (n + 15) // 16, {}

            def one(i, chunk, ok2):
                out[i] = chunk if ok2 else b""
                if len(out) == rows:
                    joined = b""
                    for k in range(rows):
                        if len(out[k]) < 16 and k < rows - 1:
                            break
                        joined += out[k]
                    cb(joined)
            for i in range(rows):
                nd.read_memory(self.d, addr + 16 * i, 16, lambda c, o, i=i: one(i, c, o))
        nd.read_memory(self.d, addr, n, got)

    def write(self, addr: int, data: bytes, cb=None) -> None:
        from ... import nativedbg as nd
        nd.write_memory(self.d, addr, data, (lambda ok, msg: cb(ok, msg)) if cb else None)

    def set_reg(self, name: str, value: int, cb=None) -> None:
        from ... import nativedbg as nd
        nd.set_register(self.d, name, hex(value) if isinstance(value, int) else str(value),
                        (lambda text, ok: cb(ok, text)) if cb else None)

    def eval(self, expr: str, cb, labels: dict | None = None) -> None:
        """An address expression: label of the notes, number, register, register+offset, [pointer], symbol."""
        from ... import nativedbg as nd
        e = (expr or "").strip()
        for a, n in (labels or {}).items():
            if n == e:
                cb(a, "")
                return
        deref = e.startswith("[") and e.endswith("]")
        if deref:
            e = e[1:-1]
        g = re.sub(r"(?<![\w$])(r[a-ds][xip]|r[sbi]p|r\d+[dwb]?|e[a-ds][xip]|e[sbi]p|[a-d]x|[sd]i|[sb]p|rip|eip)\b",
                   r"$\1", e, flags=re.I)
        if deref:
            g = f"*(unsigned long long*)({g})" if self.bits == 64 else f"*(unsigned int*)({g})"
        nd.eval_address(self.d, g, cb)

    def disasm(self, addr: int, count: int, cb, pc: int | None = None) -> None:
        """cb([analysis.Ins]) from *addr* (gdb decides the boundaries; capstone analyses each instruction)."""
        from ... import nativedbg as nd

        def got(rows):
            out = []
            for r in rows:
                if r.get("file") and r.get("line"):
                    f = Path(r["file"])
                    if not f.is_absolute():
                        f = Path(str(getattr(self.d, "cwd", "") or ".")) / f
                    self._src[r["address"]] = (str(f), int(r["line"]))
                raw = bytes.fromhex(re.sub(r"[^0-9a-fA-F]", "", r.get("bytes", "") or ""))
                ins = None
                if raw and A.capstone_ok():
                    dec = A.decode(raw, r["address"], self.bits, count=1)
                    if dec and dec[0].size == len(raw):
                        ins = dec[0]
                if ins is None:
                    text = r.get("text", "")
                    mn, _sp, ops = text.partition(" ")
                    ins = A.Ins(r["address"], len(raw) or 1, raw, mn.lower(), ops)
                ins.symbol = r.get("symbol", "")          # type: ignore[attr-defined]
                m = re.search(r"<([^>]+)>", r.get("text", ""))
                ins.target_name = m.group(1) if m else ""  # type: ignore[attr-defined]
                out.append(ins)
            cb(out)
        nd.disassemble(self.d, addr, count, got)

    def function_start(self, pc: int, cb) -> None:
        from ... import nativedbg as nd
        nd.function_start(self.d, pc, cb)

    def symbol(self, addr: int, cb) -> None:
        from ... import nativedbg as nd
        nd.symbol_at(self.d, addr, lambda name, off: cb(f"{name}+{off}" if name and off else name))

    # -- control
    def _session(self):
        return self.win.session

    def step(self, over: bool) -> bool:
        from ... import nativedbg as nd
        return nd.step_instruction(self._session(), over)

    def cont(self) -> None:
        s = self._session()
        if s is not None:
            s.cont()

    def run_to(self, addr: int) -> None:
        from ... import nativedbg as nd
        ibps = nd.user_ibps(self.d)
        if addr not in ibps:
            self._temp = addr
            ibps.add(addr)
        nd.send_ibps(self.d, lambda _ok: self.cont())

    def on_stopped(self) -> None:
        if self._temp is not None:
            from ... import nativedbg as nd
            nd.user_ibps(self.d).discard(self._temp)
            self._temp = None
            nd.send_ibps(self.d)

    def till_return(self) -> None:
        s = self._session()
        if s is not None:
            s.step_out()

    def toggle_bp(self, addr: int):
        from ... import nativedbg as nd
        if self._temp == addr:
            self._temp = None
            return True
        return nd.toggle_address_breakpoint(self._session(), addr)

    def breakpoints(self) -> set:
        from ... import nativedbg as nd
        return nd.address_breakpoints(self._session()) - ({self._temp} if self._temp is not None else set())

    def assemble(self, text: str, addr: int):
        return A.assemble_native(text, addr, self.bits)


# ====================================================================== the 8086 emulator
class EmuBackend(Backend):
    kind = "emu8086"
    bits = 16

    def __init__(self, win, session):
        super().__init__(win)
        self.s = session
        self.user_bps: set[int] = set()

    @property
    def m(self):
        return self.s.machine

    def alive(self) -> bool:
        return self.win.session is self.s and self.m is not None and bool(getattr(self.s, "paused", False)) \
            and self.s.running()

    def fmt(self, a: int) -> str:
        cs = self.m.cpu.s[1] if self.m is not None else 0
        off = a - (cs << 4)
        if 0 <= off <= 0xFFFF:
            return f"{cs:04X}:{off:04X}"
        return f"{a:05X}"

    def program_key(self):
        p = Path(self.s.folder) / self.s.startup_file
        return p.name, str(p)

    def source_of(self, a: int):
        prog = self.s.program
        hit = prog.addr_line.get(a) if prog is not None else None
        if hit:
            f, ln = hit
            return str(Path(self.s.folder) / Path(f).name), ln
        return None

    def address_of_line(self, path, line: int) -> int | None:
        prog = self.s.program
        if prog is None:
            return None
        addrs = prog.addresses_of(Path(str(path)).name, line)
        return min(addrs) if addrs else None

    def labels(self) -> dict[int, str]:
        prog = self.s.program
        out = {}
        for name, (seg, off) in (getattr(prog, "labels", None) or {}).items():
            out[((seg << 4) + off) & 0xFFFFF] = name
        for v in getattr(prog, "variables", None) or []:
            lin = getattr(v, "linear", None)
            if lin is not None:
                out.setdefault(lin, getattr(v, "name", ""))
        return out

    # -- state
    def snapshot(self, cb, extended: bool = False) -> None:
        c = self.m.cpu
        regs = {k.lower(): v for k, v in self.m.registers().items()}
        order = ["ax", "bx", "cx", "dx", "si", "di", "bp", "sp", "ip", "cs", "ds", "es", "ss", "flags"]
        groups = {n: ("Segments" if n in ("cs", "ds", "es", "ss") else "Flags" if n == "flags" else "General")
                  for n in order}
        segs = {"es": c.s[0], "cs": c.s[1], "ss": c.s[2], "ds": c.s[3]}
        cb(Snapshot(regs, order, {}, A.normalize_registers(regs), c.flags, self.m.linear_ip(),
                    ((c.s[2] << 4) + c.r[4]) & 0xFFFFF, ((c.s[2] << 4) + c.r[5]) & 0xFFFFF, 16, segs, groups))

    def read(self, addr: int, n: int, cb) -> None:
        mem = self.m.mem
        a = max(0, min(addr, len(mem)))
        cb(bytes(mem[a:min(len(mem), a + n)]))

    def write(self, addr: int, data: bytes, cb=None) -> None:
        mem = self.m.mem
        ok = 0 <= addr and addr + len(data) <= len(mem)
        if ok:
            mem[addr:addr + len(data)] = data
            self.m.cpu.video_dirty = True
        if cb:
            cb(ok, "" if ok else "outside the 1 MB address space")

    def set_reg(self, name: str, value: int, cb=None) -> None:
        c = self.m.cpu
        n = name.lower()
        idx = {"ax": 0, "cx": 1, "dx": 2, "bx": 3, "sp": 4, "bp": 5, "si": 6, "di": 7}
        segi = {"es": 0, "cs": 1, "ss": 2, "ds": 3}
        v = int(value) & 0xFFFF
        if n in idx:
            c.r[idx[n]] = v
        elif n in segi:
            c.s[segi[n]] = v
        elif n == "ip":
            c.ip = v
        elif n in ("flags", "eflags"):
            c.flags = (v & 0x0FD5) | 0xF002
        else:
            if cb:
                cb(False, f"unknown register {name}")
            return
        try:
            self.s.state_edited()
        except Exception:  # noqa: BLE001
            pass
        if cb:
            cb(True, "")

    def eval(self, expr: str, cb, labels: dict | None = None) -> None:
        e = (expr or "").strip()
        for a, n in {**self.labels(), **(labels or {})}.items():
            if n.lower() == e.lower():
                cb(a, "")
                return
        deref = e.startswith("[") and e.endswith("]")
        if deref:
            e = e[1:-1]
        c = self.m.cpu
        m = re.fullmatch(r"([0-9A-Fa-f]{1,4})[hH]?\s*:\s*([0-9A-Fa-f]{1,4})[hH]?", e)
        if m:
            a = ((int(m.group(1), 16) << 4) + int(m.group(2), 16)) & 0xFFFFF
        else:
            regs = {k.lower(): v for k, v in self.m.registers().items()}
            defseg = {"ip": "cs", "sp": "ss", "bp": "ss"}

            def num(tok: str) -> int | None:
                t = tok.strip().lower()
                if not t:
                    return 0
                if t in regs:
                    return regs[t]
                try:
                    if t.endswith("h"):
                        return int(t[:-1], 16)
                    return int(t, 0)
                except ValueError:
                    try:
                        return int(t, 16)
                    except ValueError:
                        return None
            parts = re.split(r"([+-])", e)
            total, sign, seg = 0, 1, None
            for p in parts:
                if p == "+":
                    sign = 1
                    continue
                if p == "-":
                    sign = -1
                    continue
                v = num(p)
                if v is None:
                    cb(None, f"unknown name '{p.strip()}'")
                    return
                if p.strip().lower() in defseg and seg is None:
                    seg = defseg[p.strip().lower()]
                total += sign * v
            if seg is None and re.fullmatch(r"\s*[0-9a-fA-F]{5,}h?\s*", e):
                a = total & 0xFFFFF                          # a linear address
            else:
                segv = {"cs": c.s[1], "ss": c.s[2], "ds": c.s[3]}[seg or "ds"]
                a = ((segv << 4) + (total & 0xFFFF)) & 0xFFFFF
        if deref:
            off = self.m.mem[a] | (self.m.mem[a + 1] << 8)
            a = ((c.s[3] << 4) + off) & 0xFFFFF
        cb(a, "")

    def code_seg_base(self, addr: int) -> int:
        cs = self.m.cpu.s[1] << 4
        return cs if cs <= addr <= cs + 0xFFFF else addr & 0xF0000

    def disasm(self, addr: int, count: int, cb, pc: int | None = None) -> None:
        seg = self.code_seg_base(addr)
        starts = sorted(self.s.program.addr_line) if self.s.program is not None else []
        start = addr
        cands = [a for a in starts if addr - 96 <= a <= addr]
        if cands:
            start = cands[0]
        data = bytes(self.m.mem[start:start + (addr - start) + count * 6 + 16])
        ins = A.decode_window(data, start, addr, 16, seg) if start < addr else A.decode(data, addr, 16, seg)
        names = self.labels()
        for i in ins:
            i.symbol = names.get(i.address, "")          # type: ignore[attr-defined]
            i.target_name = names.get(i.target, "") if i.target is not None else ""  # type: ignore[attr-defined]
        cb(ins[:count + 40])

    def function_start(self, pc: int, cb) -> None:
        names = self.labels()
        prog = self.s.program
        procs = [a for a, n in names.items() if a <= pc and pc - a < 4096 and
                 any(n == k for k in (getattr(prog, "labels", None) or {}))]
        cb(max(procs) if procs else pc)

    def symbol(self, addr: int, cb) -> None:
        cb(self.labels().get(addr, ""))

    # -- control
    def _pause_step(self) -> None:
        self.s._pause("step")

    def step(self, over: bool) -> bool:
        s, m = self.s, self.m
        if not s._can_step():
            return False
        if over and m._is_call_like():
            c = m.cpu
            sp0, ss0, cs0 = c.r[4], c.s[2], c.s[1]
            info = s._first_step()
            if info is not None:
                return True
            dec = (sp0 - c.r[4]) & 0xFFFF
            if dec in (2, 4, 6):
                ret_ip = c.rw(c.s[2], c.r[4])
                ret_cs = cs0 if dec == 2 else c.rw(c.s[2], c.r[4] + 2)
                target = ((ret_cs << 4) + ret_ip) & 0xFFFFF
                s._goal = lambda: m.linear_ip() == target and c.s[2] == ss0 and c.r[4] >= sp0
                self._sync_bps()
                s._resume_running(skip_bp=True, step=True)
                return True
            self._pause_step()
            return True
        info = s._first_step()
        if info is None:
            self._pause_step()
        return True

    def _sync_bps(self) -> None:
        try:
            self.m.breakpoints |= self.user_bps
        except Exception:  # noqa: BLE001
            pass

    def cont(self) -> None:
        self._sync_bps()
        self.s.cont()

    def run_to(self, addr: int) -> None:
        s, m = self.s, self.m
        if not s._can_step():
            return
        self._sync_bps()
        s._goal = lambda: m.linear_ip() == addr
        s._resume_running(skip_bp=True, step=True)

    def on_stopped(self) -> None:
        self._sync_bps()

    def till_return(self) -> None:
        """Run until a RET / RETF / IRET of this procedure is the next instruction (OllyDbg's Ctrl+F9)."""
        s, m = self.s, self.m
        if not s._can_step():
            return
        c = m.cpu
        sp0 = c.r[4]

        def goal():
            op = m.mem[m.linear_ip()]
            return op in (0xC3, 0xC2, 0xCB, 0xCA, 0xCF) and c.r[4] >= sp0
        if m.mem[m.linear_ip()] in (0xC3, 0xC2, 0xCB, 0xCA, 0xCF):
            s._first_step()
        self._sync_bps()
        s._goal = goal
        s._resume_running(skip_bp=True, step=True)

    def toggle_bp(self, addr: int):
        on = addr not in self.user_bps
        (self.user_bps.add if on else self.user_bps.discard)(addr)
        if on:
            self.m.breakpoints.add(addr)
        else:
            self.m.breakpoints.discard(addr)
            try:
                self.s._apply_breakpoints()                # keep the breakpoints of source lines
            except Exception:  # noqa: BLE001
                pass
            self._sync_bps()
        return on

    def breakpoints(self) -> set:
        return set(self.m.breakpoints) | self.user_bps

    def assemble(self, text: str, addr: int):
        from .texts import lang
        seg = self.code_seg_base(addr)
        return A.assemble_8086(text, seg >> 4, addr - seg, lang())


def backend_for(win, current=None):
    """The backend of the IDE's paused debug session (reuses *current* when it is for the same session)."""
    s = getattr(win, "session", None)
    if s is None:
        return None
    if getattr(s, "machine", None) is not None and hasattr(s, "_first_step"):
        if isinstance(current, EmuBackend) and current.s is s:
            return current
        return EmuBackend(win, s)
    try:
        from ... import nativedbg as nd
    except Exception:  # noqa: BLE001
        return None
    d = nd.dap_of(s)
    if d is not None and nd.is_gdb(d):
        if isinstance(current, NativeBackend) and current.d is d:
            return current
        return NativeBackend(win, d)
    return None
