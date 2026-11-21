"""Native (machine level) debugging over gdb's Debug Adapter Protocol: registers, memory,
disassembly, instruction stepping, address breakpoints - and assembly projects.

Used by the debugger tool windows of radide/features/native_debug.py (Registers, Disassembly,
Memory, Stack) for every gdb session (C, C++, Fortran, Rust, Go built with gcc, assembly): the
helpers below talk to any DapSession whose adapter is gdb (``gdb -i dap``, gdb >= 14), whether it
was launched (DapSession), attached (bridgedebug.AttachDap) or wrapped (BridgeDebugSession.dap,
ChainSession.inner).

DAP requests used (all answered by gdb 14+): scopes/variables ("Registers" scope), setExpression
($rax = ...), readMemory / writeMemory, disassemble, next / stepIn with granularity "instruction",
setInstructionBreakpoints, evaluate (context "repl" = a gdb command, e.g. "info symbol 0x...").

Assembly
--------
NASM on Windows (-f win32 / win64) can only write CodeView debug information, which gdb does not
read; so for .asm sources this module builds its own line table (AsmLineMap):

  1. every source is assembled again into a cache folder with a listing (nasm -l): the listing
     gives, per source line, the section and offset of its bytes;
  2. objdump -t of that object and nm of the program give each section's address in the program;
  3. while running, the program is relocated (ASLR): the slide is the run-time entry point
     ("info files") minus the static one (objdump -f).

AsmDapSession launches the program stopped at its first instruction ("starti"), computes the slide,
turns the breakpoints of .asm lines into instruction breakpoints and continues. A stop is shown on its
.asm line; F10 / F11 step one instruction (over / into calls). Without a line table (FASM, a stripped
program) the program stops at its entry point and is debugged in the Disassembly window.
GNU as sources (.s / .S, assembled with -g) and NASM ELF objects (-g -F dwarf) carry DWARF line
information: gdb handles their breakpoints itself.
"""
from __future__ import annotations

import base64
import bisect
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from .dap import DapSession
from .debugger import StopInfo

EXE = ".exe" if os.name == "nt" else ""
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE"
CACHE = LOCAL / "cache" / "asmdbg"
ASM_EXTS = {".asm", ".nasm", ".inc"}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# x86 EFLAGS bits shown (and editable) in the Registers window
FLAG_BITS = [("CF", 0, "Carry"), ("PF", 2, "Parity"), ("AF", 4, "Auxiliary carry"), ("ZF", 6, "Zero"),
             ("SF", 7, "Sign"), ("TF", 8, "Trap"), ("IF", 9, "Interrupt enable"), ("DF", 10, "Direction"),
             ("OF", 11, "Overflow")]
FLAG_NAMES = {n: b for n, b, _d in FLAG_BITS} | {"NT": 14, "RF": 16, "VM": 17, "AC": 18, "VIF": 19,
                                                  "VIP": 20, "ID": 21}
GENERAL = ("rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14",
           "r15", "rip", "eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip",
           "pc", "sp", "lr", "fp") + tuple(f"x{i}" for i in range(31))
SEGMENTS = ("cs", "ss", "ds", "es", "fs", "gs", "fs_base", "gs_base")
FLAGS = ("eflags", "rflags", "cpsr")


# ====================================================================== sessions and tools
def dap_of(session):
    """The DAP session behind *session* (BridgeDebugSession.dap, ChainSession.inner ...) or None."""
    seen = 0
    s = session
    while s is not None and seen < 5:
        if hasattr(s, "_request") and hasattr(s, "frame_id"):
            return s
        s = getattr(s, "dap", None) or getattr(s, "inner", None) or getattr(s, "dbg", None)
        seen += 1
    return None


def is_gdb(d) -> bool:
    return d is not None and getattr(d, "adapter", "") == "gdb"


def native_ready(session) -> bool:
    """A paused gdb session (the native windows can ask it for registers / memory)."""
    d = dap_of(session)
    return is_gdb(d) and bool(getattr(d, "paused", False)) and d.running()


def find_gdb() -> str:
    from .bridgedebug import find_gdb as fg
    return fg()


def find_binutil(name: str) -> str:
    """objdump / nm: next to gdb (WinLibs), then PATH and the RAD IDE toolchains."""
    gdb = find_gdb()
    if gdb and (Path(gdb).parent / (name + EXE)).exists():
        return str(Path(gdb).parent / (name + EXE))
    try:
        from .languages.c_bridge import find_native
        return find_native([name, "x86_64-w64-mingw32-" + name])
    except Exception:  # noqa: BLE001
        return shutil.which(name) or ""


def find_nasm() -> str:
    p = shutil.which("nasm")
    if p:
        return p
    cands = [LOCAL / "toolchains" / "mingw64" / "bin" / ("nasm" + EXE), LOCAL / "tools" / "nasm" / ("nasm" + EXE)]
    cands += sorted((LOCAL / "tools" / "nasm").glob("*/nasm" + EXE), reverse=True)
    cands += sorted((LOCAL / "toolchains" / "nasm").glob("**/nasm" + EXE), reverse=True)
    return next((str(c) for c in cands if c.exists()), "")


def _run(argv: list[str], cwd: str | None = None, timeout: int = 60) -> str:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, cwd=cwd, timeout=timeout,
                           creationflags=NO_WINDOW, errors="replace")
        return r.stdout if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def parse_int(text) -> int | None:
    """'0x1f' / '31' / '0x7ff6b4681773 <main+19>' -> int (None when not a number)."""
    if isinstance(text, int):
        return text
    m = re.match(r"\s*(-?0x[0-9a-fA-F]+|-?\d+)\b", str(text or ""))
    if not m:
        return None
    try:
        return int(m.group(1), 0)
    except ValueError:
        return None


def flags_value(text: str) -> int | None:
    """gdb shows eflags as '[ PF ZF IF ]': -> 0x244 (also accepts a plain number)."""
    n = parse_int(text)
    if n is not None:
        return n
    m = re.fullmatch(r"\s*\[(.*)\]\s*", str(text or ""))
    if not m:
        return None
    v = 0x2 if any(k in m.group(1).split() for k in FLAG_NAMES) or not m.group(1).strip() else 0
    for name in m.group(1).split():
        if name in FLAG_NAMES:
            v |= 1 << FLAG_NAMES[name]
        elif name.startswith("IOPL="):
            v |= (int(name[5:] or 0) & 3) << 12
    return v | 0x2                     # bit 1 is always set on x86


def register_group(name: str) -> str:
    n = name.lower()
    if n in GENERAL:
        return "General"
    if n in FLAGS:
        return "Flags"
    if n in SEGMENTS:
        return "Segments"
    if n.startswith(("xmm", "ymm", "zmm", "mxcsr", "k")) and n != "k":
        return "SSE / AVX"
    if n.startswith(("st", "f")) or n in ("fop",):
        return "FPU"
    return "Other"


# ====================================================================== DAP helpers (async: cb(result))
def _ok(m) -> bool:
    return bool(m.get("success", True))


def ensure_intel(d) -> None:
    """Intel syntax in disassembly (once per session)."""
    if is_gdb(d) and not getattr(d, "_radide_intel", False):
        d._radide_intel = True
        d._request("evaluate", {"expression": "set disassembly-flavor intel", "context": "repl"})


def gdb_command(d, command: str, cb=None) -> None:
    """Run a gdb CLI command (evaluate, context 'repl'); cb(text or '', ok)."""
    d._request("evaluate", {"expression": command, "context": "repl", "frameId": d.frame_id},
               (lambda b, m: cb(b.get("result", "") if _ok(m) else m.get("message", ""), _ok(m))) if cb else None)


def parse_info_registers(text: str) -> list[tuple[str, str, int | None, int]]:
    """gdb 'info registers [group]' -> [(name, shown value, int value, 0)].
    rax 0x0 0 / rip 0x7ff6... 0x7ff6... <main+3> / eflags 0x246 [ PF ZF IF ] / xmm0 {... uint128 = 0x...}
    / st0 0 (raw 0x0000...)."""
    out = []
    for line in (text or "").splitlines():
        m = re.match(r"(\w+)\s+(.*\S)\s*$", line)
        if not m:
            continue
        name, rest = m.group(1), m.group(2)
        if rest.startswith("{"):
            u = re.search(r"uint128 = (0x[0-9a-fA-F]+)", rest)
            if u:
                n = int(u.group(1), 16)
                out.append((name, f"{n:032X}", n, 0))
            else:
                out.append((name, rest[:120], None, 0))
            continue
        parts = rest.split(None, 1)
        raw, natural = parts[0], (parts[1] if len(parts) > 1 else parts[0])
        num = parse_int(raw)
        if natural.startswith("(raw "):                 # x87: value (raw 0x...)
            out.append((name, raw, None, 0))
            continue
        out.append((name, natural if natural.startswith(("[", "0x")) or num is None else raw, num, 0))
    return out


def read_registers(d, cb, groups: tuple[str, ...] = ()) -> None:
    """cb([(name, value_text, int_value_or_None, child_ref)]) of the current frame.
    gdb: 'info registers' (always fresh, also right after a register was changed) + the extra
    *groups* ('sse', 'float'); other adapters: the DAP "Registers" scope."""
    if d is None or d.frame_id is None:
        cb([])
        return
    if is_gdb(d):
        cmds = ["info registers"] + [f"info registers {g}" for g in groups]
        got_all: list = [None] * len(cmds)

        def one(i, text, ok):
            got_all[i] = parse_info_registers(text) if ok else []
            if all(g is not None for g in got_all):
                regs = [r for part in got_all for r in part]
                if regs:
                    cb(regs)
                else:
                    _scope_registers(d, cb)
        for i, c in enumerate(cmds):
            gdb_command(d, c, lambda text, ok, i=i: one(i, text, ok))
        return
    _scope_registers(d, cb)


def _scope_registers(d, cb) -> None:

    def got_scopes(b, m):
        sc = [s for s in (b.get("scopes", []) if _ok(m) else [])
              if s.get("presentationHint") == "registers" or s.get("name", "").lower().startswith("register")]
        if not sc:
            cb([])
            return

        def got_vars(vb, vm):
            out = []
            for v in vb.get("variables", []) if _ok(vm) else []:
                name, val = v.get("name", ""), v.get("value", "")
                num = flags_value(val) if name.lower() in FLAGS else parse_int(val)
                out.append((name, val, num, v.get("variablesReference", 0)))
            cb(out)
        d._request("variables", {"variablesReference": sc[0]["variablesReference"], "format": {"hex": True}}, got_vars)
    d._request("scopes", {"frameId": d.frame_id}, got_scopes)


def read_vector(d, name: str, cb) -> None:
    """cb(hex text) of a vector register ($xmm0.uint128 / $ymm0.v2_int128)."""
    expr = f"${name}.uint128" if name.lower().startswith("xmm") else f"${name}.v2_int128"
    d._request("evaluate", {"expression": expr, "context": "watch", "frameId": d.frame_id, "format": {"hex": True}},
               lambda b, m: cb(b.get("result", "") if _ok(m) else ""))


def set_register(d, name: str, value: str, cb=None) -> None:
    """$name = value (setExpression); cb(new_text, ok)."""
    d._request("setExpression", {"expression": "$" + name.lstrip("$"), "value": str(value), "frameId": d.frame_id},
               (lambda b, m: cb(b.get("value", "") if _ok(m) else m.get("message", "error"), _ok(m))) if cb else None)


def eval_address(d, expr: str, cb) -> None:
    """cb(address or None, error): an address expression - 0x401000, $rsp+16, &buf, a label, a pointer."""
    expr = (expr or "").strip()
    if not expr:
        cb(None, "no address")
        return
    n = parse_int(expr)
    if n is not None and re.fullmatch(r"(0x[0-9a-fA-F]+|\d+)", expr):
        cb(n, "")
        return

    def value(b, m):
        n = parse_int(b.get("result")) if _ok(m) else None
        cb(n, "" if n is not None else (m.get("message") or "not an address"))

    def cast(e):
        d._request("evaluate", {"expression": f"(unsigned long long)({e})", "context": "watch",
                                "frameId": d.frame_id}, value)

    def raw(b, m):
        if not _ok(m) and "unknown type" in m.get("message", ""):
            cast("&" + expr)              # a label without debug information (assembly): its address
        else:
            cast(expr)                    # a pointer / an array / a number: its value
    if re.fullmatch(r"[A-Za-z_.?@][\w.$?@]*", expr):
        d._request("evaluate", {"expression": expr, "context": "watch", "frameId": d.frame_id}, raw)
    else:
        cast(expr)


def read_memory(d, address: int, count: int, cb) -> None:
    """cb(bytes, ok) - unreadable memory gives (b'', False)."""
    def got(b, m):
        if not _ok(m):
            cb(b"", False)
            return
        try:
            cb(base64.b64decode(b.get("data", "") or ""), True)
        except ValueError:
            cb(b"", False)
    d._request("readMemory", {"memoryReference": hex(address), "count": int(count)}, got)


def write_memory(d, address: int, data: bytes, cb=None) -> None:
    d._request("writeMemory", {"memoryReference": hex(address), "data": base64.b64encode(data).decode("ascii")},
               (lambda b, m: cb(_ok(m), m.get("message", ""))) if cb else None)


def disassemble(d, address: int, count: int, cb) -> None:
    """cb([{address:int, bytes, text, symbol, file, line}]) - Intel syntax on gdb."""
    ensure_intel(d)

    def got(b, m):
        out = []
        for ins in b.get("instructions", []) if _ok(m) else []:
            a = parse_int(ins.get("address"))
            if a is None:
                continue
            loc = ins.get("location") or {}
            out.append({"address": a, "bytes": ins.get("instructionBytes", ""),
                        "text": re.sub(r"\s{2,}", " ", ins.get("instruction", "")).strip(),
                        "symbol": ins.get("symbol", ""), "file": loc.get("path", ""), "line": ins.get("line", 0)})
        cb(out)
    d._request("disassemble", {"memoryReference": hex(address), "instructionCount": int(count),
                               "resolveSymbols": True}, got)


def symbol_at(d, address: int, cb) -> None:
    """cb(name, offset) of 'info symbol' ('', 0 when no symbol)."""
    def got(text, ok):
        m = re.match(r"\s*(\S+?)\s*(?:\+\s*(\d+))?\s+in section", text or "") if ok else None
        if m:
            cb(m.group(1), int(m.group(2) or 0))
        else:
            cb("", 0)
    gdb_command(d, f"info symbol {hex(address)}", got)


def function_start(d, address: int, cb, hops: int = 3) -> None:
    """cb(start address): the start of the function around *address* (follows local labels such as
    main.loop / main[loop] back to their function; at most 8 KB back)."""
    def got(name, off):
        if not name or off > 8192:
            cb(address)
            return
        start = address - off
        if hops > 0 and ("[" in name or "." in name.lstrip(".")) and start > 0:
            function_start(d, start - 1, lambda s: cb(s if address - s <= 8192 else start), hops - 1)
        else:
            cb(start)
    symbol_at(d, address, got)


def current_pc(d, cb) -> None:
    """cb(pc or None) of the selected frame."""
    def got(b, m):
        frames = b.get("stackFrames", []) if _ok(m) else []
        f = next((f for f in frames if f.get("id") == d.frame_id), frames[0] if frames else None)
        cb(parse_int((f or {}).get("instructionPointerReference")) if f else None)
    d._request("stackTrace", {"threadId": d.thread_id, "startFrame": 0, "levels": 30}, got)


def step_instruction(session, over: bool) -> bool:
    """Step one machine instruction (nexti / stepi)."""
    d = dap_of(session)
    if d is None or not d.paused:
        return False
    d.paused = False
    d._request("next" if over else "stepIn", {"threadId": d.thread_id, "granularity": "instruction"})
    d.resumed.emit()
    return True


# ---------------------------------------------------------------------- instruction (address) breakpoints
def user_ibps(d) -> set:
    if not hasattr(d, "_radide_ibps"):
        d._radide_ibps = set()
    return d._radide_ibps


def send_ibps(d, cb=None) -> None:
    """setInstructionBreakpoints: the Disassembly window's address breakpoints + the session's own
    (AsmDapSession: breakpoints of .asm lines)."""
    items = {a: "" for a in user_ibps(d)}
    own = getattr(d, "own_instruction_breakpoints", None)
    if callable(own):
        for a, cond in own().items():
            items.setdefault(a, cond)
    bps = []
    for a in sorted(items):
        bp = {"instructionReference": hex(a)}
        if items[a]:
            bp["condition"] = items[a]
        bps.append(bp)
    d._request("setInstructionBreakpoints", {"breakpoints": bps}, (lambda b, m: cb(_ok(m))) if cb else None)


def toggle_address_breakpoint(session, address: int) -> bool | None:
    """Toggle a breakpoint on a machine address; returns the new state (None: no native session)."""
    d = dap_of(session)
    if not is_gdb(d) or address is None:
        return None
    s = user_ibps(d)
    on = address not in s
    (s.add if on else s.discard)(address)
    send_ibps(d)
    return on


def address_breakpoints(session) -> set:
    d = dap_of(session)
    if d is None:
        return set()
    own = getattr(d, "own_instruction_breakpoints", None)
    return set(user_ibps(d)) | (set(own()) if callable(own) else set())


# ====================================================================== assembly line table
def _pe_kind(exe: Path) -> str:
    """'win64' / 'win32' / 'elf64' / 'elf32' / '' from the program's header."""
    try:
        with open(exe, "rb") as f:
            head = f.read(4096)
    except OSError:
        return ""
    if head[:4] == b"\x7fELF":
        return "elf64" if head[4] == 2 else "elf32"
    if head[:2] == b"MZ" and len(head) > 0x40:
        off = int.from_bytes(head[0x3C:0x40], "little")
        if head[off:off + 4] == b"PE\0\0":
            machine = int.from_bytes(head[off + 4:off + 6], "little")
            return "win64" if machine in (0x8664, 0xAA64) else "win32"
    return ""


def parse_listing(text: str) -> list[tuple[int, str, int, int]]:
    """NASM listing -> [(source line, section, offset, size)] of every line that emits bytes.
    Lines of macro expansions and %include files (marked <n>) count for the line that used them."""
    out: list[tuple[int, str, int, int]] = []
    section = ".text"
    last_line = 0
    for raw in text.splitlines():
        raw = raw.rstrip("\r")
        if len(raw) < 7 or not raw[:6].strip().isdigit():
            continue
        num = int(raw[:6])
        off_txt = raw[7:15].strip()
        data = raw[16:36].strip() if len(raw) > 16 else ""
        marker = raw[36:40].strip() if len(raw) > 36 else ""
        src = raw[40:] if len(raw) > 40 else ""
        nested = marker.startswith("<") and marker.endswith(">")
        if not nested:
            m = re.match(r"\s*\[?\s*(?:section|segment)\s+([^\s\]]+)", src, re.I)
            if m:
                section = m.group(1)
            if off_txt or data or src.strip():
                last_line = num
        line = last_line if nested else num
        if not off_txt or not re.fullmatch(r"[0-9A-Fa-f]{8}", off_txt):
            continue
        hexdigits = re.sub(r"<[^>]*>|[()\[\]\-]", "", data)
        size = len(re.findall(r"[0-9A-Fa-f]{2}", hexdigits))
        m = re.search(r"<(?:rep|res)\s+([0-9A-Fa-f]+)h?>", data)
        if m and size == 0:
            size = int(m.group(1), 16)
        if out and out[-1][0] == line and out[-1][1] == section and out[-1][2] + out[-1][3] == int(off_txt, 16):
            prev = out[-1]
            out[-1] = (prev[0], prev[1], prev[2], prev[3] + size)          # continuation of the same line
        else:
            out.append((line, section, int(off_txt, 16), size))
    return out


def _objdump_sections(objdump: str, obj: Path) -> tuple[dict[int, str], set[str]]:
    """{1-based section number: name}, {names of code sections} of a COFF / ELF object."""
    text = _run([objdump, "-h", str(obj)])
    names: dict[int, str] = {}
    code: set[str] = set()
    last = None
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s+(\S+)\s+[0-9a-fA-F]+\s+[0-9a-fA-F]+", line)
        if m:
            last = m.group(2)
            names[int(m.group(1)) + 1] = last
        elif last and "CODE" in line:
            code.add(last)
    return names, code


def _objdump_symbols(objdump: str, obj: Path, sections: dict[int, str]) -> list[tuple[str, str, int]]:
    """[(symbol, section name, offset)] of a COFF object (objdump -t)."""
    out = []
    for line in _run([objdump, "-t", str(obj)]).splitlines():
        m = re.match(r"\[\s*\d+\]\(sec\s+(-?\d+)\).*?\s0x([0-9a-fA-F]+)\s+(\S+)\s*$", line)
        if m and int(m.group(1)) > 0:
            sec = sections.get(int(m.group(1)))
            if sec and m.group(3) != sec:
                out.append((m.group(3), sec, int(m.group(2), 16)))
            continue
        m = re.match(r"([0-9a-fA-F]+)\s+\S.{5}\s+(\S+)\s+[0-9a-fA-F]+\s+(\S+)\s*$", line)     # ELF format
        if m and m.group(2) in sections.values() and m.group(3) != m.group(2):
            out.append((m.group(3), m.group(2), int(m.group(1), 16)))
    return out


def _nm(nm: str, exe: Path) -> dict[str, int | None]:
    """{name: address} of the program's symbols (None = the name is not unique)."""
    out: dict[str, int | None] = {}
    for line in _run([nm, str(exe)]).splitlines():
        parts = line.split()
        if len(parts) == 3 and re.fullmatch(r"[0-9a-fA-F]+", parts[0]):
            a = int(parts[0], 16)
            out[parts[2]] = a if parts[2] not in out or out[parts[2]] == a else None
    return out


def static_entry(objdump: str, exe: Path) -> int | None:
    m = re.search(r"start address\s+(0x[0-9a-fA-F]+)", _run([objdump, "-f", str(exe)]))
    return int(m.group(1), 16) if m else None


def has_dwarf_lines(objdump: str, exe: Path, sources) -> bool:
    """The program has a DWARF line table that names one of *sources*."""
    if ".debug_line" not in _run([objdump, "-h", str(exe)]):
        return False
    text = _run([objdump, "--dwarf=rawline", str(exe)], timeout=60).lower()
    return any(Path(s).name.lower() in text for s in sources)


class AsmLineMap:
    """Source line <-> static program address of NASM sources (see the module doc)."""

    def __init__(self):
        self.lines: dict[tuple[str, int], int] = {}        # (normcase path, line) -> address
        self.starts: list[int] = []                        # sorted code addresses
        self.entries: list[tuple[int, int, str, int]] = []  # (address, size, path, line)
        self.code_lines: dict[str, list[int]] = {}         # normcase path -> sorted lines with code
        self.paths: dict[str, str] = {}                    # normcase path -> path
        self.entry: int | None = None
        self.dwarf = False                                 # gdb has DWARF lines for the sources: no table needed
        self.notes: list[str] = []

    def __bool__(self):
        return bool(self.entries)

    @staticmethod
    def key(path) -> str:
        return os.path.normcase(str(Path(path).resolve()))

    def has_file(self, path) -> bool:
        return self.key(path) in self.code_lines

    def add(self, path: str, line: int, address: int, size: int) -> None:
        k = self.key(path)
        self.paths[k] = str(Path(path).resolve())
        self.lines.setdefault((k, line), address)
        self.entries.append((address, max(size, 1), k, line))
        self.code_lines.setdefault(k, []).append(line)

    def finish(self) -> None:
        self.entries.sort()
        self.starts = [e[0] for e in self.entries]
        for k in self.code_lines:
            self.code_lines[k] = sorted(set(self.code_lines[k]))

    def address_for(self, path, line: int) -> tuple[int, int] | None:
        """(address, actual line): the first line with code at or after *line* (like gdb does)."""
        k = self.key(path)
        lines = self.code_lines.get(k) or []
        i = bisect.bisect_left(lines, line)
        if i >= len(lines) or lines[i] - line > 50:
            return None
        return self.lines[(k, lines[i])], lines[i]

    def line_for(self, address: int) -> tuple[str, int] | None:
        i = bisect.bisect_right(self.starts, address) - 1
        if i < 0:
            return None
        a, size, k, line = self.entries[i]
        return (self.paths[k], line) if a <= address < a + size else None

    # ------------------------------------------------------------ building
    @classmethod
    def build(cls, exe, sources, nasm_args=None, nasm: str = "", fmt: str = "") -> "AsmLineMap":
        """Line table of the NASM *sources* linked into *exe* (empty when it cannot be made)."""
        lm = cls()
        exe = Path(exe)
        objdump, nm = find_binutil("objdump"), find_binutil("nm")
        if objdump and exe.exists():
            lm.entry = static_entry(objdump, exe)
        sources = [Path(s) for s in sources if Path(s).suffix.lower() in (".asm", ".nasm")]
        if not sources:
            return lm
        if objdump and exe.exists() and has_dwarf_lines(objdump, exe, sources):
            lm.dwarf = True                                # RAD IDE builds (radide/asm/dwarf.py), ELF -F dwarf
            return lm
        nasm = nasm or find_nasm()
        fmt = fmt or _pe_kind(exe)
        if not (nasm and objdump and nm and exe.exists() and fmt):
            lm.notes.append("assembly line table: nasm / objdump / nm or the program was not found")
            return lm
        symbols = _nm(nm, exe)
        if not symbols:
            lm.notes.append("the program has no symbols (stripped?): debugging in the Disassembly window")
            return lm
        h = hashlib.sha1(str(exe.resolve()).lower().encode("utf-8")).hexdigest()[:12]
        work = CACHE / h
        work.mkdir(parents=True, exist_ok=True)
        args = [a for a in (nasm_args or []) if not a.startswith(("-o", "-l", "-f", "-M"))]
        for i, src in enumerate(sources):
            obj, lst = work / f"{i}_{src.stem}.obj", work / f"{i}_{src.stem}.lst"
            for p in (obj, lst):
                try:
                    p.unlink()
                except OSError:
                    pass
            _run([nasm, "-f", fmt, *args, "-I", str(src.parent) + os.sep, "-l", str(lst), "-o", str(obj), str(src)],
                 cwd=str(src.parent))
            if not (obj.exists() and lst.exists()):
                lm.notes.append(f"{src.name}: nasm could not assemble it for the line table")
                continue
            sections, code = _objdump_sections(objdump, obj)
            bases: dict[str, dict[int, int]] = {}
            for name, sec, off in _objdump_symbols(objdump, obj, sections):
                a = symbols.get(name)
                if a is not None:
                    votes = bases.setdefault(sec, {})
                    votes[a - off] = votes.get(a - off, 0) + 1
            base = {sec: max(v.items(), key=lambda kv: kv[1])[0] for sec, v in bases.items()}
            listing = lst.read_text(encoding="utf-8", errors="replace")
            for line, sec, off, size in parse_listing(listing):
                if sec in base and (not code or sec in code):
                    lm.add(str(src), line, base[sec] + off, size)
            if not any(sec in base for sec in code):
                lm.notes.append(f"{src.name}: its code was not found in the program (no labels?)")
        lm.finish()
        return lm


# ====================================================================== the assembly debug session
# gdb messages that mean nothing to the user: thread start / exit, breakpoints waiting for the program
_CHATTER = re.compile(r"\s*(\[(New )?Thread |\[Inferior |\[Thread |No source file named |Breakpoint \d+ \(.*\) pending\."
                      r"|Make breakpoint pending on future shared library load)")


class _AsmMixin:
    """Line table, slide and instruction breakpoints shared by the launched and the attached session."""

    def _asm_init(self, linemap: AsmLineMap | None, stop_at_entry: bool | None):
        self.linemap = linemap if linemap is not None else AsmLineMap()
        self.slide = 0
        self.slide_known = False
        self.stop_at_entry = (not self.linemap and not self.linemap.dwarf) if stop_at_entry is None else stop_at_entry
        self._entry_bp: int | None = None
        self._phase = "entry"
        self.top_is_asm = False
        self._noise_until = 0

    # breakpoints of .asm lines (mapped) are instruction breakpoints; the others go to gdb as usual
    def _mapped(self, path) -> bool:
        return bool(self.linemap) and self.linemap.has_file(path)

    def own_instruction_breakpoints(self) -> dict[int, str]:
        out: dict[int, str] = {}
        if not self.slide_known:
            return out
        for path, lines in self.breakpoints.items():
            if not self._mapped(path):
                continue
            for n in lines:
                hit = self.linemap.address_for(path, n)
                if hit:
                    out[hit[0] + self.slide] = self.conditions.get((path, n), "")
        if self._entry_bp is not None:
            out.setdefault(self._entry_bp, "")
        return out

    def _send_breakpoints(self, then=None):
        keep = self.breakpoints
        self.breakpoints = {p: ls for p, ls in keep.items() if not self._mapped(p)}
        try:
            DapSession._send_breakpoints(self, then)
        finally:
            self.breakpoints = keep

    def set_breakpoint(self, filename: str, line: int, on: bool, cond: str = ""):
        path = str((self.cwd / filename).resolve())
        if not self._mapped(path):
            return DapSession.set_breakpoint(self, filename, line, on, cond)
        lines = self.breakpoints.setdefault(path, set())
        (lines.add if on else lines.discard)(line)
        if on and cond:
            self.conditions[(path, line)] = cond
        else:
            self.conditions.pop((path, line), None)
        if self.slide_known:
            send_ibps(self)

    def _after_entry(self, then):
        """At the first stop: Intel syntax, the slide, the instruction breakpoints - then *then()*."""
        ensure_intel(self)

        def got(text, ok):
            m = re.search(r"Entry point:\s*(0x[0-9a-fA-F]+)", text or "") if ok else None
            if m and self.linemap.entry is not None:
                self.slide = int(m.group(1), 16) - self.linemap.entry
            self.slide_known = True
            if self.stop_at_entry and m:
                self._entry_bp = int(m.group(1), 16)
            send_ibps(self, lambda _ok: then())
        gdb_command(self, "info files", got)

    def _dispatch(self, msg):
        if msg.get("type") == "event" and msg.get("event") == "output":
            text = (msg.get("body") or {}).get("output", "")
            # gdb's DAP prints a Python traceback when a thread starts while the target runs - noise
            if text.startswith("Traceback (most recent call last)"):
                self._in_traceback = True
            if getattr(self, "_in_traceback", False) or "gdb/dap" in text.replace("\\", "/"):
                if re.match(r"\w+(Error|Exception)\b", text):
                    self._in_traceback = False
                return
            if text.startswith("Breakpoint ") and " at 0x" in text:
                return
            # gdb's own messages and the program's output both come as "stdout" (gdb's pipe)
            if self._phase == "entry":
                return                                   # gdb's banner (the program has not run yet)
            keep = [ln for ln in text.splitlines(True) if not _CHATTER.match(ln)]
            if not "".join(keep).strip() and text.strip():
                return
            msg = {**msg, "body": {**msg["body"], "output": "".join(keep)}}
        return super()._dispatch(msg)

    def _asm_stop(self, reason):
        """A real stop: the .asm line of the pc (or the C source gdb knows)."""
        def got_stack(body, _m):
            frames = body.get("stackFrames", [])
            if not frames:
                return
            top = frames[0]
            self.frame_id = top["id"]
            pc = parse_int(top.get("instructionPointerReference"))
            if self._entry_bp is not None and pc == self._entry_bp:
                self._entry_bp = None                     # the entry stop of a program without a line table
                send_ibps(self)
                reason_ = "step"
            else:
                reason_ = reason
            if top.get("source", {}).get("path"):         # C / GAS with DWARF: the normal Locals
                self.top_is_asm = False
                DapSession._on_stopped(self, reason_)
                return
            self.top_is_asm = True
            where = self.linemap.line_for(pc - self.slide) if pc is not None and self.linemap else None
            info = StopInfo(where[0] if where else "", where[1] if where else 0,
                            {"breakpoint": "breakpoint", "exception": "error"}.get(reason_, "step"))
            info.thread_id = self.thread_id
            for f in frames:
                name = f.get("name", "")
                if name == "???" and info.frames:
                    break
                fpc = parse_int(f.get("instructionPointerReference"))
                path, line = f.get("source", {}).get("path", ""), f.get("line", 0)
                if not path and fpc is not None and self.linemap:
                    hit = self.linemap.line_for(fpc - self.slide - (0 if f is top else 1))
                    if hit:
                        path, line = hit
                info.frames.append((name or (hex(fpc) if fpc else "?"), path, line))
            info.pc = pc

            def got_regs(regs):                           # assembly: the registers in Locals too
                for name, val, _n, _ref in regs:
                    if register_group(name) in ("General", "Flags"):
                        info.variables.append((name, "register", val))
                self._emit_stop(info)
            read_registers(self, got_regs)
        self._request("stackTrace", {"threadId": self.thread_id, "startFrame": 0, "levels": 30}, got_stack)

    def _emit_stop(self, info):
        """No unwind information in assembly: drop gdb's '???' frames below the last real one."""
        frames = list(getattr(info, "frames", []) or [])
        cut = next((i for i, f in enumerate(frames) if i and f[0] == "???"), None)
        if cut is not None:
            info.frames = frames[:cut]
        DapSession._emit_stop(self, info)

    # F10 / F11 in assembly: one instruction (over / into calls)
    def _asm_resume(self, command):
        if self.paused and self.top_is_asm and command in ("next", "stepIn"):
            self.paused = False
            self._request(command, {"threadId": self.thread_id, "granularity": "instruction"})
            self.resumed.emit()
            return True
        return False

    def step_out(self):
        if not (self.paused and self.top_is_asm):
            return DapSession.step_out(self)
        self.paused = False
        self.resumed.emit()

        def done(_b, m):
            if not _ok(m):                                # no frame information: stay where we are
                self.output.emit(f"[debugger] Step Out: {m.get('message', 'not possible here')}\n")
                self._asm_stop("step")
        self._request("stepOut", {"threadId": self.thread_id}, done)

    def _asm_eval(self, expr: str, ctx: str, cb):
        """A label without debug information ('has unknown type'): shown as a 64-bit number."""
        def got(b, m):
            if not _ok(m) and "unknown type" in m.get("message", "") and re.fullmatch(r"[A-Za-z_.$?@][\w.$?@]*", expr):
                self._request("evaluate", {"expression": f"*(long long*)&{expr}", "frameId": self.frame_id,
                                           "context": "watch", "format": {"hex": True}},
                              lambda b2, m2: cb(b2.get("result", "") if _ok(m2) else m.get("message", "error"),
                                                "long long (label)" if _ok(m2) else "", 0))
                return
            cb(b.get("result", "") if _ok(m) else m.get("message", "error"), b.get("type", ""),
               b.get("variablesReference", 0) if _ok(m) else 0)
        self._request("evaluate", {"expression": expr, "frameId": self.frame_id, "context": ctx}, got)

    def evaluate(self, expr: str):
        """Immediate window: expressions ('-exec <command>' runs a gdb command)."""
        if not self.paused:
            return DapSession.evaluate(self, expr)
        if expr.startswith("-exec "):
            gdb_command(self, expr[6:], lambda text, _ok: self.evalResult.emit(text.rstrip()))
            return
        self._asm_eval(expr, "watch", lambda v, _t, _r: self.evalResult.emit(v))

    def watch(self, expr, cb):
        if not self.paused:
            return DapSession.watch(self, expr, cb)
        self._asm_eval(expr, "watch", cb)


class AsmDapSession(_AsmMixin, DapSession):
    """gdb -i dap that launches an assembly program (see the module doc)."""

    def __init__(self, exe, args, cwd, env, breakpoints, linemap: AsmLineMap | None = None,
                 stop_at_entry: bool | None = None, gdb: str = "", parent=None):
        from .bridgedebug import gdb_env
        gdb = gdb or find_gdb()
        env = {**(env or {}), **(gdb_env(gdb) if gdb else {})}
        super().__init__("gdb", str(exe), list(args or []), Path(cwd), env, breakpoints, parent)
        self.argv = [gdb, "-i", "dap"] if gdb else None
        self.launch_args["stopOnEntry"] = True
        self.break_on_exception = False
        self._asm_init(linemap, stop_at_entry)
        for note in self.linemap.notes:
            self.output.emit(f"[debugger] {note}\n")

    def _on_stopped(self, reason):
        if self._phase == "entry":                         # starti: hidden, continue to the breakpoints
            self._phase = "run"
            self._after_entry(lambda: self._request("continue", {"threadId": self.thread_id}))
            return
        self._asm_stop(reason)

    def _resume(self, command):
        if not self._asm_resume(command):
            DapSession._resume(self, command)


def _make_attach_class():
    from .bridgedebug import AttachDap

    class AsmAttachDap(_AsmMixin, AttachDap):
        """gdb attached to a GUI Bridge assembly program (bridgedebug.BridgeDebugSession)."""

        def __init__(self, argv, adapter_id, attach_args, cwd, env, breakpoints, linemap=None, parent=None):
            AttachDap.__init__(self, argv, adapter_id, attach_args, cwd, env, breakpoints, parent)
            self._asm_init(linemap, False)

        def _on_stopped(self, reason):
            if not self.ready or reason in ("entry", "attach"):
                self._phase = "run"
                if not self.slide_known:
                    self._after_entry(lambda: self._request("continue", {"threadId": self.thread_id}))
                else:
                    self._request("continue", {"threadId": self.thread_id})
                return
            self._asm_stop(reason)

        def _resume(self, command):
            if not self._asm_resume(command):
                AttachDap._resume(self, command)

        def evaluate(self, expr):
            return _AsmMixin.evaluate(self, expr)
    return AsmAttachDap


_ATTACH_CLASS = []


def asm_attach_class():
    if not _ATTACH_CLASS:
        _ATTACH_CLASS.append(_make_attach_class())
    return _ATTACH_CLASS[0]


# ====================================================================== entry points for language plugins
def asm_sources(folder, files=None) -> list[Path]:
    """The .asm / .nasm sources of a project (or of *files*)."""
    folder = Path(folder)
    if files:
        return [folder / f if not Path(f).is_absolute() else Path(f) for f in files
                if Path(f).suffix.lower() in (".asm", ".nasm")]
    out = []
    for p in sorted(folder.rglob("*")):
        if p.suffix.lower() in (".asm", ".nasm") and not any(part.startswith(("_build", ".", "bin", "obj"))
                                                               for part in p.relative_to(folder).parts[:-1]):
            out.append(p)
    return out


def asm_debug_session(win, exe, args=(), cwd=None, env=None, sources=None, nasm_args=None,
                      breakpoints=None, stop_at_entry: bool | None = None):
    """A ready (not started) debug session of an assembly program for the IDE (Session API).

    *sources*: the NASM files linked into *exe* (default: every .asm of the project folder);
    *nasm_args*: the -I / -D options the build used. GAS / C sources need nothing (DWARF)."""
    gdb = find_gdb()
    if not gdb:
        return None
    exe = Path(exe)
    folder = Path(cwd or (win.project.folder if getattr(win, "project", None) is not None else exe.parent))
    srcs = list(sources) if sources is not None else asm_sources(folder)
    lm = AsmLineMap.build(exe, srcs, nasm_args)
    bps = breakpoints if breakpoints is not None else (win._all_breakpoints() if hasattr(win, "_all_breakpoints") else [])
    return AsmDapSession(exe, list(args), folder, env, bps, lm, stop_at_entry, gdb, win)


def asm_attach_dap(argv, attach_args, cwd, env, breakpoints, exe, sources=None, nasm_args=None, parent=None):
    """For bridgedebug: gdb attached to a running assembly program, with its .asm line table."""
    lm = AsmLineMap.build(Path(exe), sources if sources is not None else asm_sources(cwd), nasm_args) if exe else None
    return asm_attach_class()(argv, "gdb", attach_args, cwd, env, breakpoints, lm, parent)


def asm_console_session(win, plugin, spec, debug: bool, breakpoints=None):
    """For an assembly plugin's ``make_session(win, spec, debug)``: F5 on a console project (no forms) builds
    with the spec's ``--build`` command, then *launches* the program under gdb (AsmDapSession) - attaching
    after the start (the GUI Bridge way) would miss the first instructions of a short console program.
    Returns None (= the IDE's usual session) for Ctrl+F5, form projects or when gdb is missing."""
    if not debug or not find_gdb():
        return None
    try:
        from .model import Project
        folder = Path(spec.cwd)
        project = Project.load(folder)
        if project.forms:
            return None
        info = plugin.debug_info(project) or {}
    except Exception:  # noqa: BLE001 - the IDE's default session then
        return None
    from .foreign._others_base import ChainSession, Step
    args = list(spec.args)
    steps = []
    if "--build" in args:
        build = args[args.index("--build") + 1]
        steps.append(Step(["cmd.exe", "/c", build] if os.name == "nt" else ["sh", "-c", build], folder,
                          dict(spec.env or os.environ), "Build"))
    exe = Path(info.get("exe") or folder / ("_radapp" + EXE))
    env = {k: v for k, v in (spec.env or {}).items() if k.startswith(("RAD_", "PATH"))}

    def factory():
        return asm_debug_session(win, exe, [], folder, env or None, breakpoints=breakpoints)
    return ChainSession(steps, factory, win)


def bridge_attach_dap(plugin, argv, attach_args, cwd, env, breakpoints, exe, parent=None):
    """bridgedebug.BridgeDebugSession, gdb engine, assembly plugin (asm_base.debug_info): an AsmAttachDap with
    the .asm line table when the build has no DWARF lines (FASM / MASM / debug off); None = a plain AttachDap."""
    try:
        from .model import Project
        info = plugin.debug_info(Project.load(Path(cwd))) or {}
    except Exception:  # noqa: BLE001 - never stop F5
        info = {}
    if info.get("line_info") == "dwarf":
        return None
    exe = exe or info.get("exe", "")
    return asm_attach_dap(argv, attach_args, Path(cwd), env, breakpoints, exe, None, None, parent)


__all__ = ["asm_console_session", "bridge_attach_dap", "AsmLineMap", "AsmDapSession", "asm_attach_class", "asm_attach_dap", "asm_debug_session", "asm_sources",
           "dap_of", "is_gdb", "native_ready", "read_registers", "set_register", "read_memory", "write_memory",
           "disassemble", "eval_address", "symbol_at", "function_start", "current_pc", "step_instruction",
           "toggle_address_breakpoint", "address_breakpoints", "send_ibps", "flags_value", "register_group",
           "parse_listing", "FLAG_BITS"]
