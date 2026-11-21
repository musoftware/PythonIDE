"""Runtime checks for 16-bit DOS programs with the IDE's own 8086 emulator (radide/emu8086).

The program is assembled by radide/emu8086/assembler.py and stepped one instruction at a time by
radide/emu8086/machine.Machine (DOS / BIOS services, keyboard input from the check's input text). Around every
step this module keeps the same shadow call stack as the 32 / 64-bit runner and reports, with the same rule ids:

* ``sim.stack_imbalance`` / ``sim.bad_return`` at a near / far ``ret`` inside a procedure;
* ``sim.div_zero`` / ``sim.div_overflow`` (the emulator's divide error, explained with AX / DX and the divisor);
* ``sim.buffer_overflow``: a write outside the variable the instruction names (or the variable that was put in
  the address register with ``lea`` / ``mov reg, offset var``), using the variable sizes of the assembler;
* ``sim.bad_opcode`` / ``sim.exec_data`` (the CPU ran into data), ``sim.infinite_loop`` (step limit),
  ``sim.waiting_input`` (more keyboard input needed).

``trace_lines`` records registers before / after for "Explain this line".
"""
from __future__ import annotations

import collections
import re
from pathlib import Path

from .model import Finding, SimResult

PREFIXES = (0x26, 0x2E, 0x36, 0x3E, 0xF0, 0xF2, 0xF3)
REGS16 = ("ax", "cx", "dx", "bx", "sp", "bp", "si", "di")


def snapshot(m) -> dict:
    c = m.cpu
    d = {n: c.r[i] for i, n in enumerate(REGS16)}
    d["ip"] = c.ip
    d["eflags"] = c.flags
    for i, n in enumerate(("es", "cs", "ss", "ds")):
        d[n] = c.s[i]
    return d


def check16(text: str, path: str = "main.asm", stdin: str = "", max_steps: int = 500_000,
            trace_lines=None, max_traces: int = 64, start_line: int | None = None,
            stop_lines: tuple | None = None) -> tuple[SimResult, dict]:
    """Run *text* as a DOS program. Returns (result, traces {line: [trace dict]})."""
    from ..emu8086.assembler import assemble
    from ..emu8086.cpu import CS, SS
    from ..emu8086.machine import Machine
    from ..emu8086 import messages as EM

    res = SimResult(engine="emu8086", abi="dos16")
    traces: dict[int, list] = {}
    filename = str(path or "main.asm")
    prog = assemble(text, filename)
    if not prog.ok:
        res.status = "asm_error"
        res.errors = [f"line {e.line}: {e.text('en')}" for e in prog.errors]
        res.note_en = "Fix the assembler errors first: " + "; ".join(res.errors[:3])
        res.note_ar = "أصلح أخطاء التجميع أولاً: " + "; ".join(f"السطر {e.line}: {e.text('ar')}" for e in prog.errors[:3])
        return res, traces
    m = Machine()
    m.load(prog)
    m.record_history = False
    m.feed_keys(stdin.replace("\r\n", "\r").replace("\n", "\r"))
    c = m.cpu
    main_name = Path(filename).name.lower()
    lines_text = text.splitlines()
    variables = sorted(prog.variables, key=lambda v: v.linear)
    var_by_name = {v.name.lower(): v for v in variables}
    trace_set = set(trace_lines or ())
    if start_line:
        addrs = prog.addresses_of(filename, start_line)
        if addrs:
            lin = min(addrs)
            c.ip = (lin - (c.s[CS] << 4)) & 0xFFFF

    def line_at(lin):
        r = prog.addr_line.get(lin)
        if r and Path(r[0]).name.lower() == main_name:
            return r[1]
        return 0

    def var_at(lin):
        for v in variables:
            if v.linear <= lin < v.linear + v.size * v.count:
                return v
        return None

    frames = []                        # [ (ret offset, sp after call, proc line, pushes, pops) ]
    tags: dict[str, object] = {}
    recent = collections.deque(maxlen=20000)
    reported = set()
    steps = 0
    last_line = 0

    def add(f: Finding):
        key = (f.rule, f.line)
        if key not in reported:
            reported.add(key)
            res.add(f)

    def src(ln):
        return lines_text[ln - 1] if 0 < ln <= len(lines_text) else ""

    def code_of(ln):
        s = src(ln)
        return re.split(r";", s, maxsplit=1)[0]

    ended = ""
    open_trace = None
    while steps < max_steps:
        lin = m.linear_ip()
        ln = line_at(lin)
        if open_trace is not None:
            open_trace["after"] = snapshot(m)
            open_trace = None
        if stop_lines and ln and not stop_lines[0] <= ln <= stop_lines[1] and not frames:
            ended = "return"
            break
        if ln:
            last_line = ln
            res.lines_run.add((main_name, ln))
            recent.append(ln)
        k = 0
        while m.mem[lin + k] in PREFIXES and k < 4:
            k += 1
        op = m.mem[lin + k]
        modrm = m.mem[lin + k + 1]
        if ln in trace_set:
            lst = traces.setdefault(ln, [])
            if len(lst) < max_traces:
                open_trace = {"before": snapshot(m), "after": None, "writes": [], "iteration": len(lst) + 1,
                              "line": ln}
                lst.append(open_trace)
        is_call = op in (0xE8, 0x9A) or (op == 0xFF and ((modrm >> 3) & 7) in (2, 3))
        is_ret = op in (0xC3, 0xC2, 0xCB, 0xCA)
        is_div = op in (0xF6, 0xF7) and ((modrm >> 3) & 7) in (6, 7)
        code = code_of(ln).strip().lower() if ln else ""
        if frames and op in (0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x06, 0x0E, 0x16, 0x1E, 0x68, 0x6A, 0x9C):
            frames[-1][3] += 1
        elif frames and (0x58 <= op <= 0x5F or op in (0x07, 0x17, 0x1F, 0x9D, 0x8F)):
            frames[-1][4] += 1
        if is_ret and frames:
            sp = c.r[4]
            fr = frames[-1]
            ret_to = c.rw(c.s[SS], sp)
            if sp != fr[1]:
                delta = fr[1] - sp
                add(Finding("sim.stack_imbalance", filename, ln, {
                    "proc": fr[2], "bytes": abs(delta),
                    "state": "still on the stack" if delta > 0 else "popped too many",
                    "state_ar": "ما زالت على المكدس" if delta > 0 else "أُخرجت زيادة من المكدس",
                    "sp": "SP", "sp_entry": f"{fr[1]:04X}h", "sp_now": f"{sp:04X}h", "target": f"{ret_to:04X}h",
                    "pushes": fr[3], "pops": fr[4]}, instr=code))
                ended = "fault"
                break
            if ret_to != fr[0]:
                add(Finding("sim.bad_return", filename, ln, {"proc": fr[2], "target": f"{ret_to:04X}h",
                                                             "expected": f"{fr[0]:04X}h", "sp": "SP",
                                                             "writer_line": "?"}, instr=code))
                ended = "fault"
                break
        # address register provenance (lea si, buf / mov si, offset buf)
        if code:
            mm = re.match(r"^(?:\w+:\s*)?(lea|mov)\s+(si|di|bx|bp)\s*,\s*(?:offset\s+)?\[?\s*([a-z_.?$@][\w.?$@]*)\s*\]?\s*$",
                          code)
            if mm and (mm.group(1) == "lea" or "offset" in code) and mm.group(3) in var_by_name:
                tags[mm.group(2)] = var_by_name[mm.group(3)]
            else:
                mw = re.match(r"^(?:\w+:\s*)?(mov|pop|xor|lodsw|in)\s+(si|di|bx|bp)\b", code)
                if mw:
                    tags.pop(mw.group(2), None)
        c.undo = []
        divisor = None
        if is_div:
            divisor = _divisor(c, lin, k, op)
        sp_before = c.r[4]
        info = m.step()
        writes = c.undo or []
        c.undo = None
        steps += 1
        if is_div and info is None and c.s[CS] >= 0xF000:
            _report_div(add, filename, ln or last_line, code, c, op, divisor)    # INT 0: the divide error
            ended = "fault"
            break
        if open_trace is not None:
            for a, old in writes:
                open_trace["writes"].append((a, 1, bytes([old]), m.mem[a]))
        if is_call and info is None:
            sp = c.r[4]
            if sp == (sp_before - 2) & 0xFFFF or sp == (sp_before - 4) & 0xFFFF:
                frames.append([c.rw(c.s[SS], sp), sp, _proc_name(prog, m.linear_ip(), src), 0, 0])
        elif is_ret and frames and info is None:
            frames.pop()
        # writes outside the named variable
        if writes and ln and not is_call:
            named = None
            for w in re.findall(r"[a-z_.?$@][\w.?$@]*", code.split(None, 1)[1] if " " in code else ""):
                if w in var_by_name:
                    named = var_by_name[w]
                    break
            if named is None:
                for r in ("si", "di", "bx", "bp"):
                    if re.search(r"\[[^\]]*\b" + r + r"\b", code) and r in tags:
                        named = tags[r]
                        break
                if named is None and re.match(r"^(rep\w*\s+)?(stos|movs)", code) and "di" in tags:
                    named = tags["di"]
            if named is not None:
                lo, hi = named.linear, named.linear + named.size * named.count
                sp_lin = ((c.s[SS] << 4) + c.r[4]) & 0xFFFFF
                bad = [a for a, _o in writes if not lo <= a < hi and not sp_lin - 8 <= a < sp_lin + 8]
                if bad:
                    a = bad[0]
                    victim = var_at(a)
                    vname = victim.name if victim is not None and victim is not named else ""
                    past = a + 1 - hi if a >= hi else a - lo
                    reg = next((r for r in ("si", "di", "bx", "bp") if re.search(r"\b" + r + r"\b", code)), "si")
                    add(Finding("sim.buffer_overflow", filename, ln, {
                        "label": named.name, "size": named.size * named.count, "label_line": named.line,
                        "target": f"{named.name}+{a - lo}", "offset": a - lo, "past": past, "index": reg,
                        "count": named.count,
                        "victim_en": f" - it overwrites '{vname}'" if vname else "",
                        "victim_ar": f" - وتكتب فوق '{vname}'" if vname else "",
                        "victim_why": f" - here the variable '{vname}' (line {victim.line}) is damaged" if vname else "",
                        "victim_why_ar": f" - وهنا يتلف المتغير '{vname}' (السطر {victim.line})" if vname else ""},
                        instr=code, ref="times"))
        if info is None:
            continue
        if info.reason == "exit":
            ended = "exit"
            res.exit_code = m.exit_code
        elif info.reason == "input":
            ended = "input"
            add(Finding("sim.waiting_input", filename, last_line, {"func": "INT 21h / INT 16h"}))
        elif info.reason == "halt":
            ended = "exit"
        else:
            ended = "fault"
            msg = info.message or m.error
            div_text = EM.text("R-DIV0", m.lang, addr="").split("(")[0].strip()[:12]
            if is_div or (div_text and div_text in msg):
                _report_div(add, filename, ln or last_line, code, c, op, divisor)
            elif "opcode" in msg.lower() or "R-BAD" in msg:
                v = var_at(lin)
                if v is not None:
                    add(Finding("sim.exec_data", filename, last_line, {
                        "addr": f"{lin:05X}h", "where": v.name,
                        "how": f"The code before line {last_line} does not end with an exit (INT 21h / AH=4Ch) or ret.",
                        "how_ar": f"الكود قبل السطر {last_line} لا ينتهي بخروج (INT 21h مع AH=4Ch) ولا بـ ret."},
                        instr=code))
                else:
                    add(Finding("sim.bad_opcode", filename, ln or last_line, {
                        "addr": f"{lin:05X}h", "bytes": " ".join(f"{b:02X}" for b in m.mem[lin:lin + 4])}))
            else:
                add(Finding("sim.mem_violation", filename, ln or last_line, {
                    "access": "Error", "access_ar": "خطأ", "addr": f"{lin:05X}h", "regs": msg}, instr=code))
        break
    else:
        ended = "limit"
        _report_loop16(add, filename, recent, lines_text, c, steps)
    res.ended = ended or "stopped"
    res.steps = steps
    res.output = m.output if hasattr(m, "output") else ""
    try:
        screen = m.screen_text()
        if screen.strip() and not res.output.strip():
            res.output = screen
    except Exception:  # noqa: BLE001
        pass
    res.status = "findings" if res.problems else "ok"
    return res, traces


def _proc_name(prog, lin, src) -> str:
    best = None
    for name, (seg, off) in prog.labels.items():
        if ((seg << 4) + off) & 0xFFFFF == lin:
            best = name
            break
    return best or f"{lin:05X}h"


def _divisor(c, lin, k, op):
    """(name, value, size) of the divisor of the DIV / IDIV at *lin* (decoded again without side effects)."""
    from ..emu8086.cpu import REG16_NAMES, REG8_NAMES
    w = op & 1
    saved_ip, saved_seg = c.ip, c.seg_ovr
    try:
        c.ip = (c.ip + k + 1) & 0xFFFF
        c.seg_ovr = -1
        pre = c.mem[lin:lin + k]
        for b in pre:
            c.seg_ovr = {0x26: 0, 0x2E: 1, 0x36: 2, 0x3E: 3}.get(b, c.seg_ovr)
        c.modrm()
        val = c.rm_read(w)
        if c.ea_reg:
            name = (REG16_NAMES if w else REG8_NAMES)[c.ea_rm]
        else:
            name = f"{'word' if w else 'byte'} [{c.ea_off:04X}h]"
        return name, val, 2 if w else 1
    except Exception:  # noqa: BLE001
        return "?", None, 2 if w else 1
    finally:
        c.ip, c.seg_ovr = saved_ip, saved_seg


def _report_div(add, filename, ln, code, c, op, divisor) -> None:
    name, val, size = divisor or ("?", None, 2)
    mn = "idiv" if "idiv" in code else "div"
    ax, dx = c.r[0], c.r[2]
    if size == 1:
        dividend, dv, hi, hv, qreg, hi32, cdq = "AX", ax, "AH", ax >> 8, "AL", "ah", "cbw"
    else:
        dividend, dv, hi, hv, qreg, hi32, cdq = "DX:AX", (dx << 16) | ax, "DX", dx, "AX", "dx", "cwd"
    rule = "sim.div_zero" if not val else "sim.div_overflow"
    add(Finding(rule, filename, ln, {"mn": mn, "divisor": name, "dividend": dividend, "qreg": qreg,
                                     "divisor_value": val if val is not None else "?", "dividend_value": dv,
                                     "hi": hi, "hi_value": f"{hv:X}h", "hi32": hi32, "cdq": cdq},
                instr=code, ref=mn))


def _report_loop16(add, filename, recent, lines_text, c, steps) -> None:
    if not recent:
        add(Finding("sim.infinite_loop", filename, 0, {"steps": steps, "first": "?", "last": "?", "count": "?",
                                                       "jump_line": "?", "jump": "?", "cond_en": "", "cond_ar": "",
                                                       "regs_en": "", "regs_ar": ""}))
        return
    counts = collections.Counter(recent)
    jump_line, jump = None, ""
    for ln, _n in counts.most_common():
        s = re.split(r";", lines_text[ln - 1], maxsplit=1)[0].strip().lower() if 0 < ln <= len(lines_text) else ""
        s = re.sub(r"^[\w.?$@]+:\s*", "", s)
        if re.match(r"^(j\w+|loop\w*)\s", s):
            jump_line, jump = ln, s
            break
    loop_lines = sorted(counts)
    hot = [ln for ln in loop_lines if counts[ln] >= max(2, counts.most_common(1)[0][1] // 4)]
    first, last = (min(hot), max(hot)) if hot else (loop_lines[0], loop_lines[-1])
    if jump_line is None:
        jump_line = counts.most_common(1)[0][0]
    from . import explain
    cond = explain.condition_text(jump.split()[0], c.flags) if jump else None
    regs = " ".join(f"{n.upper()}={c.r[i]}" for i, n in enumerate(REGS16) if n not in ("sp", "bp"))
    add(Finding("sim.infinite_loop", filename, jump_line, {
        "steps": steps, "first": first, "last": last, "count": counts[jump_line], "jump_line": jump_line,
        "jump": jump, "cond_en": f" because {cond['en']}" if cond else "", "cond_ar": f" لأن {cond['ar']}" if cond else "",
        "regs_en": f"Registers now: {regs}.", "regs_ar": f"المسجلات الآن: {regs}."},
        instr=jump, ref=(jump.split()[0] if jump else "loop")))
