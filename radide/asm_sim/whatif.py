"""The What-if console: run a few instructions on chosen register values and explain every step.

    r = whatif("add eax, ebx\\njc over", "eax=0xFFFFFFFF ebx=1", bits=32)
    r["steps"]  -> [explain dicts (radide/asm_sim/explain.py)], r["regs"] -> final registers,
    r["flags"]  -> flag table with meanings, r["error"] -> assembler / runtime message

The lines are assembled with NASM (``bits 16/32/64``, ``-f bin``) and run in Unicorn at address 0x1000 with a
small stack; memory operands work on a scratch page that is mapped (zero-filled) the first time it is used, so
``mov [rbx], eax`` with ``rbx=0x2000`` just works. Initial values: ``reg=value`` pairs (decimal, ``0x..``,
``..h``, negative numbers, ``'A'``), flags (``CF=1 ZF=0 ...``) and memory bytes (``[0x2000]=1,2,3``). Without
NASM / Unicorn, 16-bit lines fall back to radide/emu8086.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from . import explain as E

CODE_ADDR = 0x1000
STACK_TOP = 0x90000
REGS = {64: ("rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14",
             "r15"),
        32: ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"),
        16: ("ax", "bx", "cx", "dx", "si", "di", "bp", "sp")}


def parse_values(text: str) -> tuple[dict, dict, dict]:
    """'eax=5, ebx=0x10 CF=1 [0x2000]=1,2' -> (registers, flags, memory {addr: bytes})."""
    regs, flags, mem = {}, {}, {}
    for m in re.finditer(r"\[\s*([0-9a-fx]+h?)\s*\]\s*=\s*([^\s;]+)", text, re.I):
        addr = E._imm(m.group(1))
        if addr is None:
            continue
        vals = [E._imm(x) for x in m.group(2).split(",") if x]
        mem[addr] = bytes((v or 0) & 0xFF for v in vals)
    rest = re.sub(r"\[[^\]]*\]\s*=\s*[^\s;]+", " ", text)
    for m in re.finditer(r"([A-Za-z][A-Za-z0-9]*)\s*=\s*('.'|[-+]?[0-9A-Fa-fx]+h?)", rest):
        name, val = m.group(1).lower(), E._imm(m.group(2))
        if val is None:
            continue
        if name.upper() in E.FLAG_BITS:
            flags[name.upper()] = 1 if val else 0
        else:
            regs[name] = val
    return regs, flags, mem


def _assemble(code: str, bits: int) -> tuple[bytes | None, str, list]:
    from .objload import nasm_path
    nasm = nasm_path(download=True)
    if not nasm:
        return None, "NASM is not available", []
    src = f"bits {bits}\norg {CODE_ADDR:#x}\n{code}\n"
    with tempfile.TemporaryDirectory(prefix="radide-whatif-") as tmp:
        t = Path(tmp)
        (t / "w.asm").write_text(src, encoding="utf-8")
        r = subprocess.run([nasm, "-f", "bin", "-o", str(t / "w.bin"), "-l", str(t / "w.lst"), str(t / "w.asm")],
                           capture_output=True, text=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if r.returncode != 0:
            msgs = []
            for ln in r.stderr.splitlines():
                m = re.search(r":(\d+):\s*(?:error|fatal):\s*(.*)$", ln)
                if m:
                    msgs.append(f"line {int(m.group(1)) - 2}: {m.group(2)}")
            return None, "; ".join(msgs) or r.stderr.strip(), []
        rows = []
        for raw in (t / "w.lst").read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*(\d+)\s([0-9A-F]{8})\s([0-9A-F]+)", raw)
            if m and int(m.group(1)) > 2:
                rows.append((CODE_ADDR + int(m.group(2), 16), int(m.group(1)) - 2))
        return (t / "w.bin").read_bytes(), "", rows


def whatif(code: str, values: str = "", bits: int = 64, max_steps: int = 200) -> dict:
    regs0, flags0, mem0 = parse_values(values)
    out = {"ok": False, "error": "", "steps": [], "regs": {}, "flags": [], "bits": bits, "initial": regs0}
    lines = [ln for ln in code.splitlines()]
    data, err, rows = _assemble(code, bits)
    if data is None:
        if bits == 16 and "not available" in err:
            return _whatif_8086(code, regs0, flags0, out)
        out["error"] = err
        return out
    try:
        import unicorn as U
        from unicorn import x86_const as X
    except ImportError:
        if bits == 16:
            return _whatif_8086(code, regs0, flags0, out)
        out["error"] = "The What-if console needs the Unicorn engine (pip install unicorn)."
        return out
    mode = {16: U.UC_MODE_16, 32: U.UC_MODE_32, 64: U.UC_MODE_64}[bits]
    uc = U.Uc(U.UC_ARCH_X86, mode)
    uc.mem_map(0, 0x100000, U.UC_PROT_ALL) if bits == 16 else None
    if bits != 16:
        uc.mem_map(CODE_ADDR & ~0xFFF, 0x10000, U.UC_PROT_ALL)
        uc.mem_map(STACK_TOP - 0x10000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    uc.mem_write(CODE_ADDR, data)
    mapped = []

    def on_unmapped(uc_, access, addr, size, value, _ud):
        page = addr & ~0xFFF
        if 0 < page < 0x7FFF0000 and len(mapped) < 64:
            try:
                uc_.mem_map(page, 0x1000, U.UC_PROT_READ | U.UC_PROT_WRITE)
                mapped.append(page)
                return True
            except U.UcError:
                return False
        return False

    uc.hook_add(U.UC_HOOK_MEM_UNMAPPED, on_unmapped)
    for addr, b in mem0.items():
        try:
            uc.mem_write(addr, b)
        except U.UcError:
            page = addr & ~0xFFF
            uc.mem_map(page, 0x1000 + ((addr + len(b)) & ~0xFFF) - page)
            uc.mem_write(addr, b)
    names = REGS[bits]
    sp = names[7] if bits != 64 else "rsp"

    def rc(n):
        return getattr(X, "UC_X86_REG_" + n.upper())

    uc.reg_write(rc(sp), STACK_TOP - 0x100 if bits != 16 else 0xFFF0)
    for k, v in regs0.items():
        try:
            uc.reg_write(rc(k), v & ((1 << 64) - 1))
        except (AttributeError, U.UcError):
            out.setdefault("ignored", []).append(k)
    fl = 0x2
    for k, v in flags0.items():
        if v:
            fl |= E.FLAG_BITS[k]
    uc.reg_write(X.UC_X86_REG_EFLAGS, fl)
    end = CODE_ADDR + len(data)
    state = {"open": None, "steps": []}
    ip_reg = {16: "ip", 32: "eip", 64: "rip"}[bits]

    def snap():
        d = {n: uc.reg_read(rc(n)) for n in names}
        d[ip_reg] = uc.reg_read(rc(ip_reg))
        d["eflags"] = uc.reg_read(X.UC_X86_REG_EFLAGS)
        return d

    def on_code(uc_, addr, size, _ud):
        if state["open"] is not None:
            state["open"]["after"] = snap()
            state["open"] = None
        if len(state["steps"]) >= max_steps or not CODE_ADDR <= addr < end:
            uc_.emu_stop()
            return
        rec = {"addr": addr, "size": size, "before": snap(), "after": None, "writes": [], "reads": []}
        state["steps"].append(rec)
        state["open"] = rec

    def on_write(uc_, access, addr, size, value, _ud):
        if state["open"] is not None:
            try:
                old = bytes(uc_.mem_read(addr, size))
            except U.UcError:
                old = b""
            state["open"]["writes"].append((addr, size, old, value))

    def on_read(uc_, access, addr, size, value, _ud):
        if state["open"] is not None:
            try:
                state["open"]["reads"].append((addr, size, int.from_bytes(uc_.mem_read(addr, size), "little")))
            except U.UcError:
                pass

    def on_intr(uc_, intno, _ud):
        state["intr"] = intno
        uc_.emu_stop()

    uc.hook_add(U.UC_HOOK_INTR, on_intr)
    uc.hook_add(U.UC_HOOK_CODE, on_code)
    uc.hook_add(U.UC_HOOK_MEM_WRITE, on_write)
    uc.hook_add(U.UC_HOOK_MEM_READ, on_read)
    try:
        uc.emu_start(CODE_ADDR, end, timeout=2_000_000, count=max_steps + 1)
    except U.UcError as e:
        cur = state["steps"][-1] if state["steps"] else None
        out["error"] = f"{e}" + (f" (at the instruction of line {_line_of(rows, cur['addr'])})" if cur else "")
        out["error_ar"] = "توقف التنفيذ بخطأ: " + out["error"]
    if "intr" in state:
        cur = state["steps"][-1] if state["steps"] else None
        where = f" (line {_line_of(rows, cur['addr'])})" if cur else ""
        if state["intr"] == 0:
            out["error"] = f"Divide error (#DE){where}: the divisor is 0, or the quotient does not fit in the register."
            out["error_ar"] = f"خطأ قسمة (#DE){where}: المقسوم عليه صفر، أو خارج القسمة لا يتسع في المسجل."
        else:
            out["error"] = f"Interrupt {state['intr']}{where} stopped the console."
            out["error_ar"] = f"المقاطعة {state['intr']}{where} أوقفت التنفيذ."
        if cur is not None:
            state["open"] = None
            cur["after"] = None
    if state["open"] is not None:
        state["open"]["after"] = snap()
    try:
        import capstone as C
        md = C.Cs(C.CS_ARCH_X86, {16: C.CS_MODE_16, 32: C.CS_MODE_32, 64: C.CS_MODE_64}[bits])
    except ImportError:
        md = None
    for i, rec in enumerate(state["steps"]):
        ln = _line_of(rows, rec["addr"])
        text = lines[ln - 1].split(";", 1)[0].strip() if 0 < ln <= len(lines) else ""
        text = re.sub(r"^[A-Za-z_.?$@][\w.?$@]*:\s*", "", text)
        if not text and md is not None:
            ins = next(md.disasm(bytes(uc.mem_read(rec["addr"], rec["size"])), rec["addr"]), None)
            text = f"{ins.mnemonic} {ins.op_str}" if ins else "?"
        nxt = ""
        if i + 1 < len(state["steps"]):
            ln2 = _line_of(rows, state["steps"][i + 1]["addr"])
            nxt = lines[ln2 - 1].split(";", 1)[0].strip() if 0 < ln2 <= len(lines) else ""
        info = E.explain_step(text, rec["before"], rec["after"], rec["writes"], rec["reads"], bits=bits, next_ins=nxt)
        info["line"] = ln
        out["steps"].append(info)
    final = snap()
    out["regs"] = final
    out["flags"] = E.flag_table(final["eflags"])
    out["ok"] = not out["error"]
    return out


def _line_of(rows, addr) -> int:
    best = 0
    for a, ln in rows:
        if a <= addr:
            best = ln
    return best


def _whatif_8086(code: str, regs0: dict, flags0: dict, out: dict) -> dict:
    """16-bit fallback without NASM / Unicorn: the IDE's 8086 emulator."""
    from ..emu8086.assembler import assemble
    from ..emu8086.machine import Machine
    from .emu16 import snapshot
    src = "org 100h\n" + code + "\nmov ah, 4Ch\nint 21h\n"
    prog = assemble(src, "whatif.asm")
    if not prog.ok:
        out["error"] = "; ".join(f"line {e.line - 1}: {e.text('en')}" for e in prog.errors)
        return out
    m = Machine()
    m.load(prog)
    m.record_history = False
    c = m.cpu
    idx = {"ax": 0, "cx": 1, "dx": 2, "bx": 3, "sp": 4, "bp": 5, "si": 6, "di": 7}
    for k, v in regs0.items():
        if k in idx:
            c.r[idx[k]] = v & 0xFFFF
    for k, v in flags0.items():
        c.set_flag(E.FLAG_BITS[k], v)
    lines = code.splitlines()
    n_user = len(lines)
    for _ in range(200):
        ln = (prog.addr_line.get(m.linear_ip()) or ("", 0))[1] - 1
        if not 0 < ln <= n_user:
            break
        before = snapshot(m)
        info = m.step()
        after = snapshot(m)
        text = lines[ln - 1].split(";", 1)[0].strip()
        out["steps"].append(dict(E.explain_step(text, before, after, bits=16), line=ln))
        if info is not None:
            out["error"] = info.message
            break
    final = snapshot(m)
    out["regs"] = final
    out["flags"] = E.flag_table(final["eflags"])
    out["ok"] = not out["error"]
    return out
