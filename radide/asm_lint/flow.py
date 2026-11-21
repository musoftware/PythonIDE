"""Control flow and data flow of an assembly file (no Qt).

* **Units**: MASM / FASM ``proc`` ... ``endp`` blocks, and in NASM / GAS the code that starts at an entry label
  (main, _start, start, the ``end`` / ``entry`` label), a ``global`` label, a ``call`` target or a label whose
  address is taken (window procedures, callbacks). Code before any such label is an implicit unit.
* **Basic blocks** per unit, split at labels and after jumps / returns / exits; edges for jumps, conditional
  jumps, loops and fall-through. A jump into another unit is a tail call; ``call`` of a function that never
  returns (ExitProcess, exit, an internal procedure without RET) ends the block, as do the DOS exit (INT 21h with
  AH=4Ch) and the Linux exit system calls.
* **Abstract state** per block entry (forward data flow to a fixed point): for every general register which
  bits were written, where the value came from (written by code, clobbered by a call, a program argument ...)
  and its constant value when known; the stack depth relative to the unit entry, RSP modulo 16, the bytes
  reserved since the last PUSH (Win64 shadow space), the frame depth of ``mov rbp, rsp``, pushes since the last
  call (32-bit argument counting), the direction flag and - in DOS EXE programs - whether DS was loaded.
* **Interprocedural summaries**: the registers each internal procedure changes without saving them (so
  ``call print`` followed by ``loop`` knows whether CX survived), whether it can return and its ``ret N``.

The checks of the rules ASM2xx (flow parts), ASM3xx, ASM4xx, ASM5xx and ASM6xx run on the converged states.
"""
from __future__ import annotations

import re

from ..asm_intel import apis, isa
from .model import Fix, Issue
from .parse import CODE_ENTRY_NAMES, GP, HIGH8, JCC, MASKS, Program, Stmt, reg_mask, sibling
from .project import is_noreturn

FULL = 0xFFFFFFFFFFFFFFFF
FAMILIES = ("rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14",
            "r15")
VOLATILE = {"win64": {"rax", "rcx", "rdx", "r8", "r9", "r10", "r11"},
            "sysv": {"rax", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11"},
            "x86": {"rax", "rcx", "rdx"}, "dos16": set()}
CALLEE_SAVED = {"win64": {"rbx", "rbp", "rdi", "rsi", "r12", "r13", "r14", "r15"},
                "sysv": {"rbx", "rbp", "r12", "r13", "r14", "r15"},
                "x86": {"rbx", "rsi", "rdi", "rbp"}, "dos16": set()}
CONV_NAME = {"win64": "Microsoft x64", "sysv": "System V AMD64", "x86": "32-bit cdecl / stdcall", "dos16": "DOS"}
CONV_NAME_AR = {"win64": "ويندوز 64 بت", "sysv": "System V (لينكس 64 بت)", "x86": "cdecl / stdcall في 32 بت",
                "dos16": "DOS"}
MOV_LIKE = {"mov", "movzx", "movsx", "movsxd", "lea", "movbe", "popcnt", "lzcnt", "tzcnt", "bsf", "bsr", "movd",
            "movq", "cvtsd2si", "cvttsd2si", "cvtss2si", "cvttss2si", "pextrb", "pextrw", "pextrd", "pextrq",
            "movmskps", "movmskpd", "pmovmskb", "lds", "les", "lfs", "lgs", "lss", "rdrand", "rdseed"} | \
    {"set" + c for c in ("o", "no", "b", "c", "nae", "ae", "nb", "nc", "e", "z", "ne", "nz", "be", "na", "a", "nbe",
                         "s", "ns", "p", "pe", "np", "po", "l", "nge", "ge", "nl", "le", "ng", "g", "nle")}
RW2 = {"add", "adc", "sub", "sbb", "and", "or", "xor", "shl", "shr", "sal", "sar", "rol", "ror", "rcl", "rcr",
       "bts", "btr", "btc", "shld", "shrd", "andn", "adcx", "adox"}
READ_ONLY = {"cmp", "test", "bt", "push", "jmp", "call", "out", "bound"}
STRING_BASE = {"movs", "stos", "lods", "scas", "cmps", "ins", "outs"}
FLAGLESS_SUSPECTS = {"mov", "movzx", "movsx", "movsxd", "lea", "not", "pop", "xchg", "bswap", "in", "xlat", "xlatb",
                     "cbw", "cwde", "cdqe", "cwd", "cdq", "cqo", "lodsb", "lodsw", "lodsd", "lodsq"}
SIGNED_J = {"jl": "jb", "jnge": "jnae", "jge": "jae", "jnl": "jnb", "jle": "jbe", "jng": "jna", "jg": "ja",
            "jnle": "jnbe"}
UNSIGNED_J = {v: k for k, v in SIGNED_J.items()} | {"jc": "jl", "jnc": "jge"}
DOS_FUNCS = {0x00, 0x01, 0x02, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x19, 0x1A, 0x25, 0x2A,
             0x2B, 0x2C, 0x2D, 0x2F, 0x30, 0x31, 0x33, 0x35, 0x36, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40,
             0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51,
             0x54, 0x56, 0x57, 0x59, 0x5A, 0x5B, 0x62, 0x65, 0x66, 0x67, 0x68, 0x6C}
DOS_INT_WRITES = {0x2A: ("rcx", "rdx"), 0x2C: ("rcx", "rdx"), 0x35: ("rbx",), 0x36: ("rbx", "rcx", "rdx"),
                  0x30: ("rbx", "rcx"), 0x48: ("rbx",), 0x59: ("rbx", "rcx")}
FLAG_NAMES = {"CF", "PF", "AF", "ZF", "SF", "OF", "DF", "IF", "TF"}
_ALLF = frozenset({"CF", "PF", "AF", "ZF", "SF", "OF"})


def flag_sets(m: str) -> tuple[frozenset, frozenset, frozenset]:
    """(read, written, undefined) flags of a mnemonic, from the isa table."""
    ins = isa.INSTRUCTIONS.get(m)
    if ins is None:
        return frozenset(), frozenset(), frozenset()
    r, w, u = set(), set(), set()
    cur = w
    for part in ins.flags.split():
        if ":" in part:
            k, f = part.split(":", 1)
            cur = {"r": r, "w": w, "0": w, "1": w, "u": u}.get(k, w)
            part = f
        if part == "all":
            cur |= _ALLF
        elif part.upper() in FLAG_NAMES:
            cur.add(part.upper())
    return frozenset(r), frozenset(w), frozenset(u)


_FLAGS_CACHE: dict = {}


def flags_of(m: str):
    hit = _FLAGS_CACHE.get(m)
    if hit is None:
        hit = _FLAGS_CACHE[m] = flag_sets(m)
    return hit


# ============================================================================ abstract state
# register value: (kinds, defmask, knownmask, value, symbol, info)
#   kinds: D written by code, Z zeroed, S sign-extension (cdq ...), C clobbered by a call, A value from the caller,
#          P program argument (argc / argv of main)
_UNDEF = (frozenset(), 0, 0, 0, "", None)
_ARG = (frozenset({"A"}), FULL, 0, 0, "", None)


def join_reg(a, b):
    if a == b:
        return a
    km = a[2] & b[2] & ~(a[3] ^ b[3])
    return (a[0] | b[0], a[1] & b[1], km, a[3] & km, a[4] if a[4] == b[4] else "", a[5] or b[5])


class State:
    __slots__ = ("r", "depth", "mod", "alloc", "frame", "frame_mod", "pushes", "df", "std_line", "ds", "cdecl",
                 "stdcall")

    def __init__(self):
        self.r = {}
        self.depth = 0
        self.mod = None
        self.alloc = 0
        self.frame = None
        self.frame_mod = None
        self.pushes = 0
        self.df = frozenset({0})
        self.std_line = -1
        self.ds = None
        self.cdecl = None
        self.stdcall = None

    def copy(self) -> "State":
        s = State.__new__(State)
        s.r = dict(self.r)
        s.depth, s.mod, s.alloc, s.frame, s.frame_mod = self.depth, self.mod, self.alloc, self.frame, self.frame_mod
        s.pushes, s.df, s.std_line, s.ds, s.cdecl, s.stdcall = (self.pushes, self.df, self.std_line, self.ds,
                                                                self.cdecl, self.stdcall)
        return s

    def key(self):
        return (tuple(sorted(self.r.items())), self.depth, self.mod, self.alloc, self.frame, self.frame_mod,
                self.pushes, self.df, self.ds, self.cdecl)

    def join(self, o: "State") -> tuple["State", tuple | None]:
        s = self.copy()
        mismatch = None
        for f, v in o.r.items():
            s.r[f] = join_reg(s.r.get(f, _UNDEF), v)
        if s.depth != o.depth:
            if s.depth is not None and o.depth is not None:
                mismatch = (s.depth, o.depth)
            s.depth = None
        s.mod = s.mod if s.mod == o.mod else None
        s.alloc = s.alloc if s.alloc == o.alloc else (None if s.alloc is None or o.alloc is None else
                                                      min(s.alloc, o.alloc))
        s.frame = s.frame if s.frame == o.frame else None
        s.frame_mod = s.frame_mod if s.frame_mod == o.frame_mod else None
        s.pushes = s.pushes if s.pushes == o.pushes else None
        s.df = s.df | o.df
        if 1 in o.df and o.std_line >= 0:
            s.std_line = o.std_line
        s.ds = s.ds if s.ds == o.ds else (False if (s.ds is False or o.ds is False) else None)
        s.cdecl = s.cdecl or o.cdecl
        s.stdcall = s.stdcall if s.stdcall == o.stdcall else None
        return s, mismatch


# ============================================================================ units and blocks
class Block:
    __slots__ = ("idx", "stmts", "labels", "succ", "preds", "term", "term_info", "state", "line", "unit")

    def __init__(self, idx, unit):
        self.idx = idx
        self.unit = unit
        self.stmts: list[int] = []
        self.labels: list[str] = []
        self.succ: list[int] = []
        self.preds: list[int] = []
        self.term = ""            # jmp ret exit cond fall-out fall-data indirect tail loop
        self.term_info = ""
        self.state: State | None = None
        self.line = -1


class Unit:
    def __init__(self, name: str, explicit=None):
        self.name = name
        self.explicit = explicit
        self.stmts: list[int] = []
        self.blocks: list[Block] = []
        self.entry = False
        self.public = False
        self.can_return = True
        self.ret_pop = 0
        self.writes: dict[str, int] = {}       # family -> first line written
        self.saved: set[str] = set()
        self.pushed: set[str] = set()
        self.popped: set[str] = set()
        self.calls: set[str] = set()           # internal unit names
        self.external_calls = False
        self.clobbers: set[str] = set()
        self.has_cld = False
        self.has_ret = False
        self.tail = False
        self.reported: set = set()


class Flow:
    def __init__(self, prog: Program, out: list, symbols=None):
        self.p = prog
        self.out = out
        self.symbols = symbols
        self.units: list[Unit] = []
        self.unit_of_line: dict[int, Unit] = {}
        self.unit_by_name: dict[str, Unit] = {}
        self.reported: set = set()
        self.abi = prog.abi
        self.mode = prog.bits
        self.ps = max(2, prog.bits // 8)
        self.vol = VOLATILE.get(self.abi, set())

    # ------------------------------------------------------------ helpers
    def add(self, rule, st: Stmt, col, end, fixes=None, key=None, mnem="", severity="", **args):
        k = key or (rule, st.line, col)
        if k in self.reported:
            return None
        self.reported.add(k)
        args.setdefault("mnem", (mnem or st.mnem).upper())
        it = Issue(rule, st.line, col, end, args, list(fixes or []), severity=severity,
                   mnem=(mnem or st.mnem).lower())
        self.out.append(it)
        return it

    def st(self, i: int) -> Stmt:
        return self.p.stmts[i]

    def target_name(self, st: Stmt) -> str:
        o = st.ops[0] if st.ops else None
        if o is None:
            return ""
        if o.kind == "sym":
            return o.syms[0] if o.syms else o.text.strip()
        if o.kind == "mem" and o.syms:
            return o.syms[0]
        if o.kind == "imm" and o.syms:
            return o.syms[0]
        return ""

    def insert_before(self, st: Stmt, texts: list[str], en: str, ar: str) -> Fix:
        ind = st.indent if not st.labels else " " * max(4, st.mcol - (st.labels[-1][1] if st.labels else 0))
        if st.labels:
            new = "".join(t + "\n" + (st.indent or "    ") for t in texts)
            return Fix(en, ar, [{"range": [st.line, st.mcol, st.line, st.mcol], "text": new}])
        return Fix(en, ar, [{"range": [st.line, 0, st.line, 0], "text": "".join(ind + t + "\n" for t in texts)}])

    def insert_after(self, st: Stmt, texts: list[str], en: str, ar: str) -> Fix:
        ind = st.indent if st.indent.strip() == "" and st.indent else "    "
        if st.labels:
            ind = " " * max(4, st.mcol)
        line = self.p.lines[st.line]
        return Fix(en, ar, [{"range": [st.line, len(line), st.line, len(line)],
                             "text": "".join("\n" + ind + t for t in texts)}])

    # ------------------------------------------------------------ build
    def build(self) -> None:
        p = self.p
        stmts = p.stmts
        call_targets: set[str] = set()
        addr_taken: set[str] = set()
        for st in stmts:
            if st.kind == "instr":
                if st.mnem == "call" and st.ops and st.ops[0].kind == "sym":
                    d = p.resolve(self.target_name(st), st.line, st.scope, st.proc)
                    if d is not None:
                        call_targets.add(d.key)
                for o in st.ops:
                    if (o.kind == "imm" and o.addr) or (o.kind == "mem" and st.mnem == "lea") or \
                            (st.mnem == "push" and o.kind == "imm"):
                        for s in o.syms:
                            d = p.resolve(s, st.line, st.scope, st.proc)
                            if d is not None and d.kind in ("code", "proc"):
                                addr_taken.add(d.key)
            elif st.kind in ("data", "macro") and st.optext:
                for s in re.findall(r"[A-Za-z_.?@$][\w.?@$]*", st.optext):
                    d = p.resolve(s, st.line, st.scope, st.proc)
                    if d is not None and d.kind in ("code", "proc"):
                        addr_taken.add(d.key)
        self.call_targets = call_targets
        self.addr_taken = addr_taken
        entry_names = {n.lower() for n in CODE_ENTRY_NAMES}
        entry_label = p.entry.lower() if p.entry else ""
        cur: Unit | None = None
        for i, st in enumerate(stmts):
            code_region = st.skind in ("code", "any", "")
            if not code_region:
                cur = None
                continue
            if st.proc:
                if cur is None or cur.explicit is None or cur.name != st.proc:
                    pd = next((x for x in p.procs if x.name == st.proc), None)
                    cur = Unit(st.proc, pd)
                    self.units.append(cur)
                    self.unit_by_name[p.key(st.proc)] = cur
                if st.kind == "directive" and st.mnem == "endp":
                    cur.stmts.append(i)
                    cur = None
                    continue
                if st.kind != "directive" or st.mnem in HLL or st.mnem == ".startup":
                    cur.stmts.append(i)
                continue
            if cur is not None and cur.explicit is not None:
                cur = None
            starts = None
            for lb, _c in st.labels:
                if lb.startswith(".") and p.dialect in ("nasm", "fasm") or lb == "@@" or lb.isdigit():
                    continue
                if p.dialect == "gas" and lb.startswith((".L", "L.")):
                    continue
                d = p.resolve(lb, st.line, st.scope, st.proc)
                key = d.key if d is not None else p.key(lb)
                if lb.lower() in entry_names or (entry_label and lb.lower() == entry_label) or lb in p.globals or \
                        key in call_targets or key in addr_taken:
                    starts = lb
            if st.kind == "data" and st.name and cur is None:
                continue
            if starts is not None:
                cur = Unit(starts)
                self.units.append(cur)
                self.unit_by_name[p.key(starts)] = cur
            elif cur is None and st.kind in ("instr", "macro", "label") and not (st.kind == "label" and not st.labels):
                nm = st.labels[0][0] if st.labels else ""
                cur = Unit(nm or "")
                self.units.append(cur)
                if nm:
                    self.unit_by_name[p.key(nm)] = cur
            if cur is not None and st.kind in ("instr", "macro", "label", "data") or \
                    (cur is not None and st.kind == "directive" and (st.mnem in (".startup",) or st.mnem in HLL)):
                cur.stmts.append(i)
        # unit properties
        for u in self.units:
            for i in u.stmts:
                self.unit_of_line[stmts[i].line] = u
            low = u.name.lower()
            if low in entry_names or (entry_label and low == entry_label):
                u.entry = True
            u.public = u.entry or u.name in p.globals or p.key(u.name) in addr_taken or \
                (u.explicit is not None and u.name in p.globals)
        if not any(u.entry for u in self.units) and self.units:
            first = next((u for u in self.units if any(stmts[i].kind == "instr" for i in u.stmts)), None)
            if first is not None and (p.abi == "dos16" or p.dialect == "gas" and not p.globals) and \
                    first.name.lower() not in {k for k in call_targets}:
                if p.abi == "dos16" and not (first.explicit is not None and p.key(first.name) in call_targets):
                    first.entry = True
        for u in self.units:
            self.summarize(u)
        self.interprocedural()
        for u in self.units:
            self.blocks_of(u)

    def summarize(self, u: Unit) -> None:
        p = self.p
        rets = []
        own = {p.stmts[j].line for j in u.stmts}
        for i in u.stmts:
            st = p.stmts[i]
            if st.kind != "instr":
                continue
            m = st.mnem
            if m == "push" and st.ops and st.ops[0].kind == "reg":
                u.pushed.add(GP[st.ops[0].reg][0])
            elif m == "pop" and st.ops and st.ops[0].kind == "reg":
                u.popped.add(GP[st.ops[0].reg][0])
            elif m in ("pusha", "pushad"):
                u.pushed |= {"rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp"}
            elif m in ("popa", "popad"):
                u.popped |= {"rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp"}
            elif m == "mov" and len(st.ops) == 2 and st.ops[0].kind == "mem" and st.ops[1].kind == "reg" and \
                    set(st.ops[0].regs) & {"rsp", "esp", "rbp", "ebp", "sp", "bp"}:
                u.saved.add(GP[st.ops[1].reg][0])          # mov [rsp+8], rbx (home / save area)
            elif m == "enter":
                u.saved.add("rbp")
            elif m == "cld":
                u.has_cld = True
            elif m in ("ret", "retn", "retf", "iret", "iretd", "iretq"):
                u.has_ret = True
                rets.append(st.ops[0].value if st.ops and st.ops[0].kind == "imm" and st.ops[0].value else 0)
            elif m == "jmp" and st.ops:
                o = st.ops[0]
                if o.kind in ("reg", "mem"):
                    u.tail = True
                else:
                    d = p.resolve(self.target_name(st), st.line, st.scope, st.proc)
                    if d is None or d.line not in own:
                        u.tail = True
            if m == "call" and st.ops:
                d = p.resolve(self.target_name(st), st.line, st.scope, st.proc) if st.ops[0].kind == "sym" else None
                if d is not None and d.kind in ("code", "proc") and p.key(d.name) in self.unit_by_name:
                    u.calls.add(p.key(d.name))
                else:
                    u.external_calls = True
            for name, _k, _v, _s in self.effects(st)[1]:
                fam = GP[name][0]
                if fam not in u.writes:
                    u.writes[fam] = st.line
        if u.explicit is not None and u.explicit.uses:
            u.saved |= {GP[r][0] for r in u.explicit.uses if r in GP}
        u.saved |= u.pushed
        if u.explicit is not None and u.explicit.params:
            u.saved.add("rbp")
        u.ret_pop = rets[0] if rets and all(r == rets[0] for r in rets) else 0
        last = next((p.stmts[i] for i in reversed(u.stmts) if p.stmts[i].kind in ("instr", "macro")), None)
        falls = last is not None and not (last.kind == "instr" and last.mnem in (
            "jmp", "ret", "retn", "retf", "iret", "iretd", "iretq", "hlt", "ud2") or last.mnem == "int" or
            last.mnem == "call" and is_noreturn(self.target_name(last)) or last.kind == "macro" and
            last.mnem in ("invoke", ".exit") and is_noreturn(last.optext.split(",")[0].strip()))
        u.can_return = u.has_ret or u.tail or falls
        u.hll = any(p.stmts[i].kind == "directive" and p.stmts[i].mnem in HLL for i in u.stmts)

    def interprocedural(self) -> None:
        for u in self.units:
            u.clobbers = set(u.writes) - u.saved - {"rsp"}
            if u.external_calls:
                u.clobbers |= self.vol - u.saved
        for _ in range(12):
            changed = False
            for u in self.units:
                add = set()
                for c in u.calls:
                    cu = self.unit_by_name.get(c)
                    if cu is not None and cu is not u:
                        add |= cu.clobbers
                add -= u.saved
                if not add <= u.clobbers:
                    u.clobbers |= add
                    changed = True
            if not changed:
                break

    def noreturn_call(self, st: Stmt) -> str:
        """The callee name when this call / invoke never returns (ExitProcess, exit, an internal procedure
        without RET), else ''."""
        p = self.p
        if st.kind == "macro":
            if st.mnem in ("invoke", "cinvoke", "stdcall", "ccall", "fastcall"):
                nm = st.optext.strip().split(",")[0].strip().strip("[]")
                return nm if is_noreturn(nm) else ""
            if st.mnem == ".exit":
                return ".exit"
            return ""
        nm = self.target_name(st)
        if not nm:
            return ""
        if is_noreturn(nm):
            return nm
        if st.ops[0].kind == "sym":
            d = p.resolve(nm, st.line, st.scope, st.proc)
            if d is not None:
                u = self.unit_by_name.get(p.key(d.name))
                if u is not None and not u.can_return and u.blocks is not None and any(
                        p.stmts[i].kind == "instr" for i in u.stmts):
                    return nm
        return ""

    def is_exit_int(self, u: Unit, pos: int) -> str:
        """'dos' / 'linux' when the INT / SYSCALL at u.stmts[pos] ends the program (AH=4Ch ... set just before)."""
        p = self.p
        st = p.stmts[u.stmts[pos]]
        m = st.mnem
        v = st.ops[0].value if m == "int" and st.ops and st.ops[0].kind == "imm" else None
        if m == "int" and v in (0x20, 0x27):
            return "dos"
        want = None
        if m == "int" and v == 0x21:
            want = "ah"
        elif m == "int" and v == 0x80:
            want = "eax"
        elif m == "syscall":
            want = "rax"
        elif m in ("hlt",) and p.abi == "dos16":
            return "dos"
        if want is None:
            return ""
        for j in range(pos - 1, max(-1, pos - 12), -1):
            s2 = p.stmts[u.stmts[j]]
            if s2.kind != "instr":
                if s2.labels and s2.kind == "label":
                    continue
                return ""
            if s2.mnem in ("call", "int", "syscall"):
                return ""
            if s2.mnem == "mov" and len(s2.ops) == 2 and s2.ops[0].kind == "reg":
                r = s2.ops[0].reg
                val = s2.ops[1].value if s2.ops[1].kind == "imm" else None
                if want == "ah" and r in ("ah", "ax", "eax"):
                    if val is None:
                        return ""
                    ah = (val >> 8) & 0xFF if r != "ah" else val & 0xFF
                    return "dos" if ah in (0x4C, 0x31, 0x00) else ""
                if want in ("eax", "rax") and GP.get(r, ("",))[0] == "rax":
                    if val is None:
                        return ""
                    if want == "eax" and val == 1:
                        return "linux"
                    if want == "rax" and val in (60, 231):
                        return "linux"
                    return ""
            elif s2.ops and s2.ops[0].kind == "reg" and GP.get(s2.ops[0].reg, ("",))[0] == "rax" and \
                    s2.mnem not in ("cmp", "test", "push"):
                return ""
        return ""

    def blocks_of(self, u: Unit) -> None:
        p = self.p
        blocks: list[Block] = []
        cur: Block | None = None
        label_block: dict[int, int] = {}          # line -> block index
        for pos, i in enumerate(u.stmts):
            st = p.stmts[i]
            if st.kind == "directive" and st.mnem == "endp":
                continue
            hll = st.kind == "directive" and st.mnem in HLL
            if cur is None or st.labels or hll:
                if cur is not None and not cur.stmts:
                    blk = cur
                else:
                    blk = Block(len(blocks), u)
                    blocks.append(blk)
                    if cur is not None and not cur.term:
                        cur.term = "fall"
                cur = blk
                if cur.line < 0:
                    cur.line = st.line
                for lb, _c in st.labels:
                    cur.labels.append(lb)
                if hll:
                    cur.labels.append(st.mnem)
                    if blk is not blocks[0] and blocks[blk.idx - 1].term in ("jmp", "ret", "exit", "tail"):
                        pass
                label_block[st.line] = cur.idx
            cur.stmts.append(pos)
            if st.kind == "data":
                cur.term = "fall-data"
                cur = None
                continue
            term = ""
            if st.kind == "instr":
                m = st.mnem
                if m == "jmp":
                    term = "jmp"
                elif m in ("ret", "retn", "retf", "iret", "iretd", "iretq", "sysret", "sysexit"):
                    term = "ret"
                elif m in JCC or m in ("loop", "loope", "loopne", "loopz", "loopnz", "jcxz", "jecxz", "jrcxz"):
                    term = "cond"
                elif m in ("ud2",):
                    term = "exit"
                elif m == "call" and self.noreturn_call(st):
                    term = "exit"
                elif m in ("int", "syscall", "hlt") and self.is_exit_int(u, pos):
                    term = "exit"
                elif m == "hlt":
                    term = "exit"
            elif st.kind == "macro" and self.noreturn_call(st):
                term = "exit"
            if term:
                cur.term = term
                cur = None
        if cur is not None and not cur.term:
            cur.term = "fall-out"
        # successors
        for b in blocks:
            if not b.stmts:
                b.term = b.term or "fall"
            last = p.stmts[u.stmts[b.stmts[-1]]] if b.stmts else None
            nxt = b.idx + 1 if b.idx + 1 < len(blocks) else None
            if b.term in ("fall",):
                if nxt is not None:
                    b.succ.append(nxt)
                else:
                    b.term = "fall-out"
            elif b.term in ("jmp", "cond") and last is not None:
                tgt = self.jump_target(u, last, label_block, blocks)
                if b.term == "cond":
                    if nxt is not None:
                        b.succ.append(nxt)
                    else:
                        b.term_info = "cond-out"
                if tgt is None:
                    if b.term == "jmp":
                        b.term = "tail"
                elif tgt == "self":
                    if b.term == "jmp":
                        b.term = "exit"
                elif tgt >= 0:
                    b.succ.append(tgt)
            for s in b.succ:
                blocks[s].preds.append(b.idx)
        u.blocks = blocks

    def jump_target(self, u: Unit, st: Stmt, label_block: dict, blocks):
        """Block index of a jump target inside the unit, 'self' for jmp $, None for a target outside."""
        p = self.p
        o = st.ops[0] if st.ops else None
        if o is None or o.kind in ("reg", "mem") or o.indirect:
            return None
        t = o.text.strip()
        tl = t.lower().replace(" ", "")
        if tl in ("$", "short$", ".") or tl.endswith("$") and tl.startswith("short"):
            return "self"
        if tl in ("@f", "@b", "@@") and p.anon:
            if tl == "@f":
                line = next((ln for ln in p.anon if ln > st.line), None)
            else:
                line = next((ln for ln in reversed(p.anon) if ln <= st.line), None)
            return label_block.get(line) if line is not None else None
        mm = re.match(r"^(\d+)([fb])$", tl)
        if mm and p.dialect == "gas":
            lines = p.num_labels.get(mm.group(1), [])
            line = next((ln for ln in lines if ln > st.line), None) if mm.group(2) == "f" else \
                next((ln for ln in reversed(lines) if ln <= st.line), None)
            return label_block.get(line) if line is not None else None
        nm = self.target_name(st)
        d = p.resolve(nm, st.line, st.scope, st.proc)
        if d is None:
            return None
        if d.line in label_block:
            return label_block[d.line]
        return None

    # ------------------------------------------------------------ effects of one instruction
    def effects(self, st: Stmt):
        """(reads, writes) of general registers: reads = [name], writes = [(name, kind, value, symbol)]."""
        m = st.mnem
        ops = st.ops
        mode = self.mode
        reads: list[str] = []
        writes: list[tuple] = []
        for o in ops:
            if o.kind == "mem":
                reads.extend(r for r in o.regs if r in GP)

        def r(o):
            if o.kind == "reg" and o.reg in GP:
                reads.append(o.reg)

        def w(o, kind="D", val=None, sym=""):
            if o.kind == "reg" and o.reg in GP:
                writes.append((o.reg, kind, val, sym))

        acc = {8: "al", 16: "ax", 32: "eax", 64: "rax"}
        hi = {16: "dx", 32: "edx", 64: "rdx"}
        cx = {16: "cx", 32: "ecx", 64: "rcx"}[mode] if mode in (16, 32, 64) else "ecx"
        si = {16: "si", 32: "esi", 64: "rsi"}.get(mode, "esi")
        di = {16: "di", 32: "edi", 64: "rdi"}.get(mode, "edi")
        n = len(ops)
        if m in MOV_LIKE:
            for o in ops[1:]:
                r(o)
            if n >= 1:
                val = None
                sym = ""
                if m == "mov" and n == 2 and ops[1].kind == "imm":
                    val = ops[1].value
                    if ops[1].addr and ops[1].syms:
                        sym = ops[1].syms[0]
                elif m == "lea" and n == 2 and ops[1].kind == "mem" and ops[1].syms and not ops[1].regs:
                    sym = ops[1].syms[0]
                elif m == "mov" and n == 2 and ops[1].kind == "reg" and ops[1].reg in GP:
                    sym = "=" + ops[1].reg
                w(ops[0], "D", val, sym)
        elif m in ("xor", "sub", "sbb") and n == 2 and ops[0].kind == "reg" and ops[1].kind == "reg" and \
                ops[0].reg == ops[1].reg:
            w(ops[0], "Z" if m != "sbb" else "D", 0 if m != "sbb" else None)
        elif m in RW2 or m.startswith("cmov"):
            for o in ops:
                r(o)
            if n:
                w(ops[0])
        elif m in READ_ONLY:
            for o in ops:
                r(o)
        elif m in ("inc", "dec", "neg", "not", "bswap"):
            if n:
                r(ops[0])
                w(ops[0])
        elif m in ("xchg", "xadd"):
            for o in ops:
                r(o)
                w(o)
        elif m == "cmpxchg":
            for o in ops:
                r(o)
            sz = ops[0].size if n else mode
            reads.append(acc.get(sz, "eax"))
            if n:
                w(ops[0])
            writes.append((acc.get(sz, "eax"), "D", None, ""))
        elif m == "pop":
            for o in ops:
                w(o)
        elif m in ("mul", "imul") and n == 1:
            r(ops[0])
            sz = ops[0].size or (16 if mode == 16 else 32)
            reads.append(acc.get(sz, "eax"))
            if sz == 8:
                writes.append(("ax", "D", None, ""))
            else:
                writes.append((acc.get(sz, "eax"), "D", None, ""))
                writes.append((hi.get(sz, "edx"), "D", None, ""))
        elif m == "imul":
            for o in ops[1:]:
                r(o)
            if n == 2:
                r(ops[0])
            w(ops[0])
        elif m in ("div", "idiv") and n == 1:
            r(ops[0])
            sz = ops[0].size or (16 if mode == 16 else 32)
            reads.append("al" if sz == 8 else acc.get(sz, "eax"))
            if sz == 8:
                writes.append(("ax", "D", None, ""))
            else:
                writes.append((acc.get(sz, "eax"), "D", None, ""))
                writes.append((hi.get(sz, "edx"), "D", None, ""))
        elif m in ("cbw", "cwde", "cdqe"):
            src, dst = {"cbw": ("al", "ax"), "cwde": ("ax", "eax"), "cdqe": ("eax", "rax")}[m]
            reads.append(src)
            writes.append((dst, "D", None, ""))
        elif m in ("cwd", "cdq", "cqo"):
            src, dst = {"cwd": ("ax", "dx"), "cdq": ("eax", "edx"), "cqo": ("rax", "rdx")}[m]
            reads.append(src)
            writes.append((dst, "S", None, ""))
        elif m in ("loop", "loope", "loopne", "loopz", "loopnz"):
            reads.append(cx)
            writes.append((cx, "D", None, ""))
        elif m in ("jcxz", "jecxz", "jrcxz"):
            reads.append({"jcxz": "cx", "jecxz": "ecx", "jrcxz": "rcx"}[m])
        elif self.is_string(st):
            base, sz = self.string_kind(st)
            if base in ("movs", "cmps"):
                reads += [si, di]
                writes += [(si, "D", None, ""), (di, "D", None, "")]
            elif base == "stos":
                reads += [acc.get(sz, "al"), di]
                writes.append((di, "D", None, ""))
            elif base == "lods":
                reads.append(si)
                writes += [(si, "D", None, ""), (acc.get(sz, "al"), "D", None, "")]
            elif base == "scas":
                reads += [acc.get(sz, "al"), di]
                writes.append((di, "D", None, ""))
            elif base == "ins":
                reads += ["dx", di]
                writes.append((di, "D", None, ""))
            elif base == "outs":
                reads += ["dx", si]
                writes.append((si, "D", None, ""))
            if any(x.startswith("rep") for x in st.prefixes):
                reads.append(cx)
                writes.append((cx, "D", 0, ""))
        elif m in ("xlat", "xlatb"):
            reads += ["al", {16: "bx", 32: "ebx", 64: "rbx"}.get(mode, "ebx")]
            writes.append(("al", "D", None, ""))
        elif m == "in":
            if n:
                w(ops[0])
            if n > 1:
                r(ops[1])
        elif m == "lahf":
            writes.append(("ah", "D", None, ""))
        elif m == "sahf":
            reads.append("ah")
        elif m == "cpuid":
            reads.append("eax")
            writes += [(x, "D", None, "") for x in ("eax", "ebx", "ecx", "edx")]
        elif m in ("rdtsc", "rdtscp"):
            writes += [("eax", "D", None, ""), ("edx", "D", None, "")]
            if m == "rdtscp":
                writes.append(("ecx", "D", None, ""))
        elif m == "syscall":
            reads.append("rax")
            writes += [("rax", "D", None, ""), ("rcx", "D", None, ""), ("r11", "D", None, "")]
        elif m in ("enter", "leave"):
            writes.append(({16: "bp", 32: "ebp", 64: "rbp"}.get(mode, "ebp"), "D", None, ""))
        elif m in ("ret", "retn", "retf", "int", "nop", "hlt", "cld", "std", "clc", "stc", "cmc", "cli", "sti",
                   "pushf", "popf", "pushfd", "popfd", "pushfq", "popfq", "int3", "into", "iret", "iretd", "iretq",
                   "pusha", "pushad", "popa", "popad") or m in JCC:
            if m in ("popa", "popad"):
                writes += [(x, "D", None, "") for x in (("ax", "bx", "cx", "dx", "si", "di", "bp") if mode == 16
                                                        else ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"))]
        else:
            for k, o in enumerate(ops):
                if k == 0 and n > 1:
                    w(o)
                else:
                    r(o)
        return reads, writes

    def is_string(self, st: Stmt) -> bool:
        m = st.mnem
        if m in ("movsd", "cmpsd") and st.ops:
            return False                                 # SSE forms
        base = m.rstrip("bwdq") if m not in STRING_BASE else m
        if self.p.att and m.endswith("l") and m[:-1] in STRING_BASE:
            base = m[:-1]
        return base in STRING_BASE and (m in STRING_BASE or len(m) == len(base) + 1)

    def string_kind(self, st: Stmt):
        m = st.mnem
        if m in STRING_BASE:
            sz = st.ops[0].size if st.ops and st.ops[0].size else 8
            return m, sz
        base = m[:-1]
        return base, {"b": 8, "w": 16, "d": 32, "l": 32, "q": 64}.get(m[-1], 8)

    # ------------------------------------------------------------ state updates
    def write(self, S: State, name: str, kind: str, val, sym: str, line: int) -> None:
        fam, sz = GP[name]
        mask = reg_mask(name)
        if self.mode == 64 and sz == 32:
            mask = FULL
        old = S.r.get(fam, _UNDEF)
        dm = old[1] | mask
        if val is not None:
            v = val & MASKS.get(sz, FULL)
            shift = 8 if name in HIGH8 else 0
            km = (old[2] & ~mask) | mask
            nv = (old[3] & ~mask) | ((v << shift) & mask)
        else:
            km = old[2] & ~mask
            nv = old[3] & km
        if sym and mask != FULL and sz < 16:
            sym = ""
        S.r[fam] = (frozenset({kind}), dm & FULL, km & FULL, nv & FULL, sym, line)

    def value(self, S: State, name: str):
        fam = GP[name][0]
        rv = S.r.get(fam, _UNDEF)
        mask = reg_mask(name)
        if self.mode == 64 and GP[name][1] == 32:
            mask = 0xFFFFFFFF
        if rv[2] & mask != mask:
            return None
        v = rv[3] & mask
        return v >> 8 if name in HIGH8 else v

    def entry_state(self, u: Unit) -> State:
        p = self.p
        S = State()
        if u.entry:
            for f in FAMILIES:
                S.r[f] = _UNDEF
            S.r["rsp"] = _ARG
            low = u.name.lower()
            args = []
            if self.abi == "win64" and low in ("main", "wmain", "winmain", "wwinmain"):
                args = ["rcx", "rdx", "r8", "r9"]
            elif self.abi == "sysv" and low in ("main",):
                args = ["rdi", "rsi", "rdx"]
            for a in args:
                S.r[a] = (frozenset({"P"}), FULL, 0, 0, "", None)
            if self.abi == "dos16":
                S.r["rbp"] = _UNDEF
                if not p.com and self.has_data_segment():
                    S.ds = False
        else:
            for f in FAMILIES:
                S.r[f] = _ARG
        if self.abi in ("win64", "sysv"):
            S.mod = 0 if (u.name.lower() in ("_start", "__start") and p.os == "linux") else 8
        S.df = frozenset({0}) if (self.abi != "dos16" or u.entry) else frozenset({"?"})
        return S

    def has_data_segment(self) -> bool:
        return any(s.skind in ("data", "bss", "rodata") for s in self.p.stmts if s.kind == "data") or \
            any(s.mnem in (".data", ".data?") for s in self.p.stmts if s.kind == "directive")

    # ------------------------------------------------------------ the analysis
    def run(self) -> None:
        if self.p.abi not in ("win64", "sysv", "x86", "dos16"):
            return
        self.build()
        for u in self.units:
            if not u.blocks:
                continue
            try:
                self.solve(u)
                self.report_unit(u)
            except Exception:  # noqa: BLE001 - a broken unit must not stop the other checks
                continue

    def solve(self, u: Unit) -> None:
        blocks = u.blocks
        start = self.entry_state(u)
        blocks[0].state = start
        mism = {}
        work = [0]
        visits = [0] * len(blocks)
        while work:
            bi = work.pop(0)
            b = blocks[bi]
            visits[bi] += 1
            if visits[bi] > 60:
                continue
            S = b.state.copy()
            for pos in b.stmts:
                self.step(u, b, pos, S, False)
            for s in b.succ:
                nb = blocks[s]
                if nb.state is None:
                    nb.state = S.copy()
                    work.append(s)
                else:
                    j, mm = nb.state.join(S)
                    if mm is not None and s not in mism:
                        mism[s] = mm
                    if j.key() != nb.state.key():
                        nb.state = j
                        if s not in work:
                            work.append(s)
        # labelled blocks that no path reaches (jumped to from another unit, data tables ...): unknown state
        for b in blocks:
            if b.state is None and b.labels:
                S = State()
                for f in FAMILIES:
                    S.r[f] = _ARG
                S.depth = S.mod = S.alloc = S.pushes = None
                S.df = frozenset({"?"})
                b.state = S
                b.term_info = b.term_info or "seeded"
        self.mismatch = mism

    def report_unit(self, u: Unit) -> None:
        p = self.p
        blocks = u.blocks
        for b in blocks:
            if b.state is None:
                continue
            S = b.state.copy()
            if b.idx in self.mismatch and not self.pop_in_loop(u):
                a, c = self.mismatch[b.idx]
                st = p.stmts[u.stmts[b.stmts[0]]] if b.stmts else None
                if st is not None and ("ASM305", u.name) not in self.reported:
                    self.reported.add(("ASM305", u.name))
                    col = st.labels[0][1] if st.labels else st.mcol
                    self.add("ASM305", st, col, max(st.end_col, col + 1), a=a, b=c, mnem="push")
            for pos in b.stmts:
                if not self.step(u, b, pos, S, True):
                    break
            self.end_of_block(u, b, S)
        self.unreachable(u)
        self.callee_saved(u)

    def end_of_block(self, u: Unit, b: Block, S: State) -> None:
        p = self.p
        if b.term == "fall-data" and b.stmts:
            st = p.stmts[u.stmts[b.stmts[-1]]]
            prev = [p.stmts[u.stmts[x]] for x in b.stmts[:-1]]
            if any(x.kind == "instr" for x in prev) or b.preds or b.idx == 0 and u.blocks[0] is b and \
                    any(p.stmts[i].kind == "instr" for i in u.stmts):
                if b.term_info == "seeded":
                    return
                last_call = next((x for x in reversed(prev) if x.kind == "instr"), None)
                if last_call is not None and last_call.mnem == "call" and \
                        self.target_name(last_call).lower() in ("pthis",):
                    return
                if not prev and not b.preds and b.idx != 0:
                    return
                nm = st.name or (st.labels[-1][0] if st.labels else "")
                col = st.labels[0][1] if st.labels else (st.mcol if not st.name else len(st.indent))
                self.add("ASM207", st, col, st.end_col, name=nm or "db")
            return
        if b.term != "fall-out" or not b.stmts:
            return
        if b.term_info == "seeded":
            return
        instrs = [p.stmts[u.stmts[x]] for x in b.stmts if p.stmts[u.stmts[x]].kind in ("instr", "macro")]
        if not instrs:
            return
        last = instrs[-1]
        # the next unit in the file
        last_i = u.stmts[-1]
        nxt = None
        for v in self.units:
            if v.stmts and v.stmts[0] > last_i and v is not u:
                if nxt is None or v.stmts[0] < nxt.stmts[0]:
                    nxt = v
        between_code = nxt is not None and all(
            p.stmts[k].skind in ("code", "any", "") and p.stmts[k].kind not in ("data",)
            for k in range(last_i + 1, nxt.stmts[0]))
        if u.explicit is not None:
            self.add("ASM302", last, last.mcol, last.end_col, where=f"procedure '{u.name}'",
                     where_ar=f"الإجراء '{u.name}'", need="RET", need_ar="RET")
            return
        if nxt is not None and between_code and nxt.name:
            if u.entry and self.abi == "dos16":
                pass
            elif self.shared_tail(last, nxt):
                return
            else:
                self.add("ASM303", last, last.mcol, last.end_col, name=u.name or "this code", next=nxt.name)
                return
        if self.abi == "dos16" and u.entry:
            exit_lines = ["mov ah, 4Ch", "int 21h"] if p.dialect != "gas" else ["movb $0x4C, %ah", "int $0x21"]
            fx = self.insert_after(last, exit_lines, "Add the DOS exit (mov ah, 4Ch / int 21h)",
                                   "أضف الخروج إلى DOS (mov ah, 4Ch ثم int 21h)")
            self.add("ASM602", last, last.mcol, last.end_col, [fx])
            return
        if u.entry:
            need = "ret (or a call to ExitProcess / exit)"
            need_ar = "ret (أو استدعاء ExitProcess / exit)"
            self.add("ASM302", last, last.mcol, last.end_col, where="the program", where_ar="البرنامج", need=need,
                     need_ar=need_ar)
            return
        if u.name and (p.key(u.name) in self.call_targets):
            fx = self.insert_after(last, ["ret"], "Add RET", "أضف RET")
            self.add("ASM302", last, last.mcol, last.end_col, [fx], where=f"'{u.name}'", where_ar=f"'{u.name}'",
                     need="RET", need_ar="RET")

    def unreachable(self, u: Unit) -> None:
        p = self.p
        for b in u.blocks:
            if b.state is not None or b.labels or not b.stmts:
                continue
            instrs = [p.stmts[u.stmts[x]] for x in b.stmts if p.stmts[u.stmts[x]].kind == "instr"]
            if not instrs:
                continue
            prev = u.blocks[b.idx - 1] if b.idx > 0 else None
            if prev is None or not prev.stmts:
                continue
            pst = p.stmts[u.stmts[prev.stmts[-1]]]
            trivial = all(x.mnem in ("ret", "retn", "int3", "nop", "hlt", "ud2", "leave") or
                          (x.mnem == "int" and x.ops and x.ops[0].value == 3) for x in instrs)
            if trivial and prev.term == "exit":
                continue
            after = {"jmp": "JMP", "ret": pst.mnem.upper(), "exit": "the exit of the program" if pst.mnem != "call"
                     else f"the call to {self.target_name(pst)} (it never returns)", "tail": "JMP"}.get(
                prev.term, pst.mnem.upper())
            first, last = instrs[0], instrs[-1]
            it = self.add("ASM301", first, first.mcol, len(p.lines[last.line]), after=after)
            if it is not None:
                it.end_line = last.line
                it.end_col = last.end_col

    def callee_saved(self, u: Unit) -> None:
        p = self.p
        saved_conv = CALLEE_SAVED.get(self.abi, set())
        if not saved_conv or not u.public or not u.has_ret:
            return
        if not any(b.state is not None and b.term == "ret" for b in u.blocks):
            return
        bad = {f: ln for f, ln in u.writes.items() if f in saved_conv and f not in u.saved}
        alt = {"win64": "R10 / R11", "sysv": "R10 / R11", "x86": "ECX / EDX"}.get(self.abi, "")
        for f, ln in sorted(bad.items(), key=lambda kv: kv[1]):
            st = next((p.stmts[i] for i in u.stmts if p.stmts[i].line == ln), None)
            if st is None:
                continue
            reg = sibling(f, 32 if self.abi == "x86" else 64) or f
            o = next((o for o in st.ops if o.kind == "reg" and GP.get(o.reg, ("",))[0] == f), None)
            col, end = (o.col, o.end) if o else (st.mcol, st.end_col)
            self.add("ASM503", st, col, end, proc=u.name, reg=reg.upper(), conv=CONV_NAME.get(self.abi, ""),
                     alt=alt)

    # ------------------------------------------------------------ one instruction
    def step(self, u: Unit, b: Block, pos: int, S: State, report: bool) -> bool:
        p = self.p
        st = p.stmts[u.stmts[pos]]
        if st.kind == "directive":
            if st.mnem == ".startup":
                S.ds = True
            return True
        if st.kind == "data":
            return False
        if st.kind == "label":
            return True
        if st.kind == "macro":
            self.macro(st, S)
            return True
        m = st.mnem
        if not m:
            return True
        reads, writes = self.effects(st)
        if report:
            self.check_reads(u, b, pos, st, S, reads)
            self.check_instruction(u, b, pos, st, S)
        # ---------------- stack and frame
        self.stack(u, st, S, report)
        # ---------------- calls / interrupts
        if m == "call":
            self.call(u, st, S, report)
        elif m == "int" and st.ops and st.ops[0].kind == "imm":
            self.interrupt(u, st, S, report)
        elif m == "cld":
            S.df = frozenset({0})
        elif m == "std":
            S.df = frozenset({1})
            S.std_line = st.line
        elif m in ("popf", "popfd", "popfq"):
            S.df = frozenset({"?"})
        # ---------------- register writes
        for name, kind, val, sym in writes:
            if kind == "D" and val is None and sym.startswith("="):
                src = sym[1:]
                srv = S.r.get(GP[src][0], _UNDEF)
                self.write(S, name, "D", self.value(S, src), srv[4] if GP[src][1] == GP[name][1] else "", st.line)
                continue
            self.write(S, name, kind, val, sym, st.line)
        # DS loaded
        if m in ("mov", "pop") and st.ops and st.ops[0].kind == "sreg" and st.ops[0].reg == "ds":
            S.ds = True
        return True

    def macro(self, st: Stmt, S: State) -> None:
        name = st.mnem
        if name in ("invoke", "cinvoke", "stdcall", "ccall", "fastcall"):
            for f in self.vol:
                if f != "rax":
                    S.r[f] = (frozenset({"C"}), FULL, 0, 0, "", (st.optext.strip().split(",")[0].strip(), st.line,
                                                                   "volatile"))
            S.r["rax"] = (frozenset({"D"}), FULL, 0, 0, "", st.line)
            S.pushes = 0
            return
        if name in ("print", "printn", "putc", "gotoxy", "cursoroff", "cursoron") and self.p.abi == "dos16":
            return
        if name == ".exit":
            return
        for f in FAMILIES:
            if f != "rsp":
                S.r[f] = _ARG
        S.depth = S.mod = S.alloc = S.frame = S.pushes = None
        S.cdecl = S.stdcall = None

    def stack(self, u: Unit, st: Stmt, S: State, report: bool) -> None:
        m = st.mnem
        ops = st.ops
        ps = self.ps
        if m in ("push", "pop"):
            for o in ops:
                if o.kind == "reg":
                    size = o.size // 8
                elif o.kind == "sreg":
                    size = ps
                elif o.kind == "mem" and o.size:
                    size = o.size // 8
                else:
                    size = ps
                if self.mode == 64 and size == 4:
                    size = 8
                if m == "push":
                    if S.depth is not None:
                        S.depth += size
                    if S.mod is not None:
                        S.mod = (S.mod - size) % 16
                    S.alloc = 0
                    if S.pushes is not None:
                        S.pushes += 1
                    S.stdcall = None
                else:
                    if S.depth is not None:
                        S.depth -= size
                        if S.depth < 0 and report:
                            self.add("ASM306", st, st.mcol, st.end_col, key=("ASM306", u.name), mnem=m.upper())
                            S.depth = None
                    if S.mod is not None:
                        S.mod = (S.mod + size) % 16
                    S.alloc = 0
                    if S.cdecl is not None:
                        S.cdecl = None
                    S.stdcall = None
            return
        if m in ("pushf", "pushfd", "pushfq", "popf", "popfd", "popfq"):
            size = ps if m in ("pushf", "popf") and self.mode != 16 else ps
            sign = 1 if m.startswith("push") else -1
            if S.depth is not None:
                S.depth += sign * size
            if S.mod is not None:
                S.mod = (S.mod - sign * size) % 16
            return
        if m in ("pusha", "pushad", "popa", "popad"):
            size = 8 * (2 if m in ("pusha", "popa") and self.mode == 16 else 4)
            sign = 1 if m.startswith("push") else -1
            if S.depth is not None:
                S.depth += sign * size
            if S.mod is not None:
                S.mod = (S.mod - sign * size) % 16
            return
        dst = ops[0] if ops else None
        is_sp = dst is not None and dst.kind == "reg" and GP.get(dst.reg, ("",))[0] == "rsp"
        if m in ("sub", "add") and is_sp and len(ops) == 2:
            v = ops[1].value if ops[1].kind == "imm" else None
            if v is None:
                S.depth = S.mod = S.alloc = None
                return
            sign = 1 if m == "sub" else -1
            if S.depth is not None:
                S.depth += sign * v
            if S.mod is not None:
                S.mod = (S.mod - sign * v) % 16
            if S.alloc is not None:
                S.alloc = max(0, S.alloc + sign * v)
            if m == "add":
                if report and S.stdcall is not None and S.stdcall[2] > 0 and v == S.stdcall[2]:
                    line, api, nbytes = S.stdcall
                    fx = Fix("Delete this line", "احذف هذا السطر",
                             [{"range": [st.line, 0, st.line + 1, 0], "text": ""}]) if not st.labels else None
                    self.add("ASM506", st, st.mcol, st.end_col, [fx] if fx else [], api=api, bytes=nbytes)
                if S.cdecl is not None and v >= S.cdecl[2]:
                    S.cdecl = None
            S.stdcall = None
            return
        if m == "and" and is_sp and len(ops) == 2 and ops[1].kind == "imm" and ops[1].value is not None:
            if ops[1].value & 0xF == 0:
                S.mod = 0
            else:
                S.mod = None
            S.depth = None
            S.alloc = 0
            return
        if m == "mov" and len(ops) == 2 and dst is not None and dst.kind == "reg":
            src = ops[1]
            fam = GP.get(dst.reg, ("",))[0]
            if fam == "rbp" and src.kind == "reg" and GP.get(src.reg, ("",))[0] == "rsp":
                S.frame = S.depth
                S.frame_mod = S.mod
                return
            if fam == "rsp":
                if src.kind == "reg" and GP.get(src.reg, ("",))[0] == "rbp" and S.frame is not None:
                    S.depth = S.frame
                    S.mod = S.frame_mod
                    S.alloc = 0
                else:
                    S.depth = S.mod = S.alloc = None
                return
            if fam == "rbp":
                S.frame = S.frame_mod = None
            return
        if m == "leave":
            if S.frame is not None:
                S.depth = S.frame - ps
                S.mod = (S.frame_mod + ps) % 16 if S.frame_mod is not None else None
            else:
                S.depth = S.mod = None
            S.frame = S.frame_mod = None
            S.alloc = 0
            return
        if m == "enter" and ops and ops[0].kind == "imm" and ops[0].value is not None:
            if S.depth is not None:
                S.depth += ps
            if S.mod is not None:
                S.mod = (S.mod - ps) % 16
            S.frame, S.frame_mod = S.depth, S.mod
            v = ops[0].value
            if S.depth is not None:
                S.depth += v
            if S.mod is not None:
                S.mod = (S.mod - v) % 16
            S.alloc = v
            return
        if is_sp and m not in ("cmp", "test", "push"):
            S.depth = S.mod = S.alloc = None
            return
        if m in ("ret", "retn", "retf"):
            if report and S.depth not in (None, 0):
                if S.depth > 0:
                    if S.cdecl is not None and self.abi == "x86":
                        line, api, nbytes = S.cdecl
                        call_st = next((s for s in self.p.stmts if s.line == line), None)
                        if call_st is not None:
                            fx = self.insert_after(call_st, [f"add esp, {nbytes}"], f"Add add esp, {nbytes}",
                                                   f"أضف add esp, {nbytes}")
                            self.add("ASM507", call_st, call_st.mcol, call_st.end_col, [fx], api=api, bytes=nbytes)
                            return
                    what = f"{S.depth} byte(s) are still on the stack (a missing POP or ADD {self.sp_name()})"
                    what_ar = f"ما زال في المكدس {S.depth} بايت (POP أو ADD {self.sp_name()} ناقصة)"
                else:
                    what = f"{-S.depth} byte(s) too many were removed from the stack"
                    what_ar = f"تمت إزالة {-S.depth} بايت زيادة من المكدس"
                self.add("ASM304", st, st.mcol, st.end_col, mnem=m.upper(), what=what, what_ar=what_ar)

    def sp_name(self) -> str:
        return {16: "SP", 32: "ESP", 64: "RSP"}.get(self.mode, "ESP")

    # ------------------------------------------------------------ calls
    def callee_of(self, st: Stmt):
        """(name, internal Unit or None, external bool)."""
        p = self.p
        o = st.ops[0] if st.ops else None
        if o is None:
            return "", None, True
        nm = self.target_name(st)
        if o.kind == "sym" and nm:
            d = p.resolve(nm, st.line, st.scope, st.proc)
            if d is not None and d.kind in ("code", "proc"):
                u = self.unit_by_name.get(p.key(d.name))
                return nm, u, u is None
        return nm or o.text, None, True

    def call(self, u: Unit, st: Stmt, S: State, report: bool) -> None:
        p = self.p
        name, cu, external = self.callee_of(st)
        api = apis.lookup(name) if name and external else None
        managed = (u.explicit is not None and u.explicit.kind == "fasm") or p.uses_invoke
        if report and external and name:
            if self.abi in ("win64", "sysv") and S.mod not in (None, 0) and not managed:
                conv = CONV_NAME[self.abi]
                self.add("ASM502", st, st.mcol, st.end_col, callee=name, mod=S.mod, conv=f"The {conv} convention",
                         conv_ar=f"اتفاقية {CONV_NAME_AR[self.abi]}")
            if self.abi == "win64" and S.alloc is not None and S.alloc < 32 and not managed and S.depth is not None:
                self.add("ASM501", st, st.mcol, st.end_col, callee=name, have=S.alloc)
            if api is not None and self.abi in ("win64", "sysv"):
                locs = apis.arg_locations(api, self.abi)
                n_rep = 0
                for k, ((typ, pname), loc) in enumerate(zip(api.params, locs)):
                    if loc not in GP or n_rep >= 2:
                        continue
                    rv = S.r.get(GP[loc][0], _UNDEF)
                    if "C" in rv[0] or "P" in rv[0] or rv[1] & reg_mask(loc) != reg_mask(loc):
                        n_rep += 1
                        conv = CONV_NAME[self.abi]
                        self.add("ASM504", st, st.mcol, st.end_col, key=("ASM504", st.line, loc), n=k + 1,
                                 api=api.name, param=f"{typ} {pname}".strip(), loc=loc.upper(),
                                 conv=f"In the {conv} convention", conv_ar=f"في اتفاقية {CONV_NAME_AR[self.abi]}",
                                 sig=api.signature())
                if self.abi == "sysv" and api.variadic:
                    rv = S.r.get("rax", _UNDEF)
                    if rv[2] & 0xFF != 0xFF:
                        self.add("ASM508", st, st.mcol, st.end_col, api=api.name)
            if api is not None and self.abi == "x86" and S.pushes:
                nparams = len(api.params)
                if (api.variadic and S.pushes < nparams) or (not api.variadic and S.pushes != nparams):
                    stdcall = not (api.is_crt or api.variadic)
                    self.add("ASM505", st, st.mcol, st.end_col, api=api.name, n=nparams, pushed=S.pushes,
                             cleanup="the function removes the wrong number of bytes (ret N) - the stack is corrupted."
                             if stdcall else "the stack cleanup after the call no longer matches.",
                             cleanup_ar="تزيل الدالة عدداً خاطئاً من البايتات (ret N) فيفسد المكدس."
                             if stdcall else "لا يعود تنظيف المكدس بعد الاستدعاء صحيحاً.", sig=api.signature())
            if 1 in S.df and self.abi != "dos16":
                self.add("ASM406", st, st.mcol, st.end_col, mnem="CALL", line=S.std_line + 1)
        # ---------------- state after the call
        if cu is not None:
            clob = set(cu.clobbers)
            reason = "internal"
            if S.depth is not None and cu.ret_pop:
                S.depth -= cu.ret_pop
            if S.mod is not None and cu.ret_pop:
                S.mod = (S.mod + cu.ret_pop) % 16
        else:
            clob = set(self.vol)
            reason = "volatile"
            if self.abi == "x86":
                nbytes = None
                mm = re.search(r"@(\d+)$", name or "")
                if api is not None and not (api.is_crt or api.variadic):
                    nbytes = 4 * len(api.params)
                elif mm:
                    nbytes = int(mm.group(1))
                if nbytes is not None:
                    if S.depth is not None:
                        S.depth -= nbytes
                    if S.mod is not None:
                        S.mod = (S.mod + nbytes) % 16
                    S.stdcall = (st.line, api.name if api else name, nbytes) if nbytes else None
                    S.pushes = 0
                    S.cdecl = None
                elif api is not None and S.pushes:
                    S.cdecl = (st.line, api.name, 4 * S.pushes)
                    S.stdcall = None
                elif S.pushes:
                    S.depth = None           # unknown convention: do not guess the cleanup
                    S.stdcall = None
        for f in clob:
            if f in ("rax", "rsp"):
                continue
            S.r[f] = (frozenset({"C"}), FULL, 0, 0, "", (name or "?", st.line, reason))
        if cu is None or "rax" in clob or self.abi != "dos16":
            S.r["rax"] = (frozenset({"D"}), FULL, 0, 0, "", st.line)
        S.pushes = 0
        if cu is not None:
            S.stdcall = None

    def interrupt(self, u: Unit, st: Stmt, S: State, report: bool) -> None:
        p = self.p
        v = st.ops[0].value
        if p.abi != "dos16":
            S.r["rax"] = (frozenset({"D"}), FULL, 0, 0, "", st.line)
            return
        ah = self.value(S, "ah")
        rv = S.r.get("rax", _UNDEF)
        if report and v in (0x21, 0x10, 0x16):
            if rv[1] & 0xFF00 != 0xFF00 and "C" not in rv[0]:
                self.add("ASM603", st, st.mcol, st.end_col, num=f"{v:X}h")
            elif v == 0x21 and ah is not None:
                if ah not in DOS_FUNCS:
                    self.add("ASM604", st, st.mcol, st.end_col, ah=f"{ah:02X}h")
                if ah in (0x09, 0x0A, 0x3C, 0x3D, 0x39, 0x3A, 0x3B, 0x41, 0x43, 0x4E, 0x56) and S.ds is False:
                    self.ds_issue(u, st)
                if ah == 0x09:
                    dx = S.r.get("rdx", _UNDEF)
                    if dx[1] & 0xFFFF != 0xFFFF and "C" not in dx[0] and "A" not in dx[0]:
                        self.add("ASM606", st, st.mcol, st.end_col)
                    elif dx[4] and not dx[4].startswith("="):
                        self.check_dollar(st, dx[4])
        writes = ["rax"]
        if v == 0x21 and ah in DOS_INT_WRITES:
            writes += list(DOS_INT_WRITES[ah])
        elif v == 0x21 and ah is None:
            writes += ["rbx", "rcx", "rdx"]
        elif v in (0x10,) and ah in (0x03, 0x0F, 0x08):
            writes += ["rbx", "rcx", "rdx"]
        elif v in (0x1A, 0x33, 0x13):
            writes += ["rbx", "rcx", "rdx"]
        for f in writes:
            old = S.r.get(f, _UNDEF)
            S.r[f] = (frozenset({"D"}), old[1] | (0xFFFF if f != "rax" else 0xFFFF), 0, 0, "", st.line)

    def ds_issue(self, u: Unit, st: Stmt) -> None:
        p = self.p
        if ("ASM601",) in self.reported:
            return
        self.reported.add(("ASM601",))
        seg = "@data" if any(s.mnem in (".data", ".data?") for s in p.stmts if s.kind == "directive") else \
            next((s.section for s in p.stmts if s.kind == "data" and s.section and s.skind == "data"), "@data")
        # insert after the first statement of the entry unit (its label / proc line)
        first = p.stmts[u.stmts[0]]
        target = next((p.stmts[i] for i in u.stmts if p.stmts[i].kind == "instr"), first)
        fx = self.insert_before(target, [f"mov ax, {seg}", "mov ds, ax"], f"Insert mov ax, {seg} / mov ds, ax",
                                f"أدرج mov ax, {seg} ثم mov ds, ax")
        it = Issue("ASM601", st.line, st.mcol, st.end_col, {"seg": seg}, [fx], mnem=st.mnem)
        self.out.append(it)

    def check_dollar(self, st: Stmt, sym: str) -> None:
        p = self.p
        d = p.resolve(sym, st.line, st.scope, st.proc)
        if d is None or d.kind != "data" or d.size != 8:
            return
        texts = []
        last_line = d.line
        started = False
        for s2 in p.stmts:
            if s2.line < d.line:
                continue
            if s2.line == d.line:
                started = True
                texts.append(s2.optext)
                last_line = s2.line
                continue
            if started and s2.kind == "data" and not s2.name and not s2.labels:
                texts.append(s2.optext)
                last_line = s2.line
                continue
            break
        body = " ".join(texts)
        if "$" in body or re.search(r"(?<![\w])(24h|0x24|36)(?![\w])", body, re.I) or "?" in body or \
                re.search(r"\bdup\b", body, re.I):
            return
        line = p.lines[last_line]
        code_end = next((s.end_col for s in p.stmts if s.line == last_line), len(line))
        q = '"' if p.dialect == "gas" else "'"
        fx = Fix("Add '$' at the end of the string", "أضف '$' في نهاية النص",
                 [{"range": [last_line, code_end, last_line, code_end], "text": f", {q}${q}"}])
        self.add("ASM605", st, st.mcol, st.end_col, [fx], key=("ASM605", sym), name=sym)

    # ------------------------------------------------------------ reads
    def check_reads(self, u: Unit, b: Block, pos: int, st: Stmt, S: State, reads: list[str]) -> None:
        m = st.mnem
        skip_undef = set()
        if m in ("div", "idiv"):
            skip_undef |= {"dx", "edx", "rdx", "ah"}
        if m in ("loop", "loope", "loopne", "loopz", "loopnz") or (self.is_string(st) and st.prefixes):
            skip_undef |= {"cx", "ecx", "rcx"}
        for name in dict.fromkeys(reads):
            if name not in GP:
                continue
            fam = GP[name][0]
            if fam == "rsp":
                continue
            rv = S.r.get(fam, _UNDEF)
            need = reg_mask(name)
            if self.mode == 64 and GP[name][1] == 32:
                need = 0xFFFFFFFF
            if "C" in rv[0] and rv[5]:
                callee, cline, reason = rv[5]
                key = ("ASM402", u.name, fam, cline)
                if reason == "internal":
                    cu = self.unit_by_name.get(self.p.key(callee))
                    wl = cu.writes.get(fam) if cu is not None else None
                    reason_en = f"'{callee}' writes {name.upper()}" + (f" (line {wl + 1})" if wl is not None else "") + \
                        " and does not save it."
                    reason_ar = f"الإجراء '{callee}' يكتب في {name.upper()}" + \
                        (f" (السطر {wl + 1})" if wl is not None else "") + " ولا يحفظه."
                else:
                    conv = CONV_NAME.get(self.abi, "")
                    reason_en = f"In the {conv} convention {sibling(fam, 64 if self.mode == 64 else 32) or fam} is " \
                                "volatile: every called function may change it."
                    reason_ar = f"في اتفاقية {CONV_NAME_AR.get(self.abi, '')} المسجل " \
                                f"{sibling(fam, 64 if self.mode == 64 else 32) or fam} متطاير: أي دالة مستدعاة قد تغيّره."
                keep = {"win64": "RBX RSI RDI R12-R15", "sysv": "RBX R12-R15", "x86": "EBX ESI EDI"}.get(
                    self.abi, "a register the procedure does not change")
                o = next((o for o in st.ops if o.kind == "reg" and o.reg == name), None)
                col, end = (o.col, o.end) if o else (st.mcol, st.end_col)
                self.add("ASM402", st, col, end, key=key, reg=name.upper(), callee=callee, line=cline + 1,
                         reason=reason_en, reason_ar=reason_ar, keep=keep)
                continue
            if rv[1] & need != need and u.entry and name not in skip_undef and m not in ("push",):
                key = ("ASM401", u.name, fam)
                o = next((o for o in st.ops if o.kind == "reg" and o.reg == name), None)
                col, end = (o.col, o.end) if o else (st.mcol, st.end_col)
                part = ""
                part_ar = ""
                if rv[1]:
                    part = " (only part of it was set)"
                    part_ar = " (ضُبط جزء منه فقط)"
                self.add("ASM401", st, col, end, key=key, reg=name.upper(), path=part, path_ar=part_ar)

    # ------------------------------------------------------------ instruction checks with state
    def check_instruction(self, u: Unit, b: Block, pos: int, st: Stmt, S: State) -> None:
        p = self.p
        m = st.mnem
        ops = st.ops
        if m in ("div", "idiv") and len(ops) == 1:
            self.check_div(u, st, S)
        if m in ("loop", "loope", "loopne", "loopz", "loopnz") or (self.is_string(st) and
                                                                  any(x.startswith("rep") for x in st.prefixes)):
            cx = {16: "cx", 32: "ecx", 64: "rcx"}.get(self.mode, "ecx")
            rv = S.r.get("rcx", _UNDEF)
            need = reg_mask(cx) if not (self.mode == 64) else FULL
            if rv[1] & need != need and "C" not in rv[0]:
                self.add("ASM405", st, st.mcol, st.end_col, key=("ASM405", u.name), mnem=m.upper() if not
                         st.prefixes else f"{st.prefixes[0].upper()} {m.upper()}", reg=cx.upper(),
                         state="was never set", state_ar="لم يُضبط أبداً",
                         how="it decrements the counter and repeats until it reaches 0",
                         how_ar="تنقص العدّاد وتكرر حتى يصل إلى 0",
                         wrap={16: "65536", 32: "4294967296", 64: "2^64"}[self.mode])
        if self.is_string(st):
            if 1 in S.df:
                self.add("ASM406", st, st.mcol, st.end_col, key=("ASM406", st.line), mnem=m.upper(),
                         line=S.std_line + 1)
            elif "?" in S.df and self.mode == 16 and not u.entry and not u.has_cld:
                self.add("ASM407", st, st.mcol, st.end_col, key=("ASM407", u.name), mnem=m.upper())
        if m in ("ret", "retn") and 1 in S.df and self.abi != "dos16":
            self.add("ASM406", st, st.mcol, st.end_col, key=("ASM406", st.line), mnem=m.upper(),
                     line=S.std_line + 1)
        if m in JCC or m.startswith(("set", "cmov")) and m in isa.INSTRUCTIONS and isa.INSTRUCTIONS[m].category == \
                "cond":
            self.check_flags(u, b, pos, st, S)
        # DS before the first data access (DOS EXE programs)
        if S.ds is False:
            for o in ops:
                if o.kind == "mem" and o.syms and (not o.seg or o.seg == "ds") and "bp" not in o.regs:
                    d = p.resolve(o.syms[0], st.line, st.scope, st.proc)
                    if d is not None and d.kind == "data" and d.skind in ("data", "bss", "rodata"):
                        self.ds_issue(u, st)
                        break

    def check_div(self, u: Unit, st: Stmt, S: State) -> None:
        o = st.ops[0]
        m = st.mnem
        size = o.size if o.kind in ("reg", "mem") and o.size else (16 if self.mode == 16 else 32)
        if o.kind == "reg" and o.reg in GP:
            v = self.value(S, o.reg)
            if v == 0:
                rv = S.r.get(GP[o.reg][0], _UNDEF)
                line = rv[5] if isinstance(rv[5], int) else st.line
                self.add("ASM404", st, o.col, o.end, reg=o.reg.upper(), line=line + 1)
                return
        if size == 8:
            high, pair, low, need, fam = "AH", "AX", "AL", 0xFF00, "rax"
            fixins = "xor ah, ah" if m == "div" else "cbw"
        else:
            high = {16: "DX", 32: "EDX", 64: "RDX"}[size]
            low = {16: "AX", 32: "EAX", 64: "RAX"}[size]
            pair = f"{high}:{low}"
            need = {16: 0xFFFF, 32: 0xFFFFFFFF, 64: FULL}[size]
            fam = "rdx"
            fixins = {16: "xor dx, dx", 32: "xor edx, edx", 64: "xor edx, edx"}[size] if m == "div" else \
                {16: "cwd", 32: "cdq", 64: "cqo"}[size]
        rv = S.r.get(fam, _UNDEF)
        state = state_ar = ""
        if fam == "rax":
            if rv[1] & need != need:
                state, state_ar = "was never set", "لم يُضبط أبداً"
        elif "C" in rv[0] and rv[5]:
            state = f"was changed by the call to '{rv[5][0]}' (line {rv[5][1] + 1})"
            state_ar = f"تغيّر بسبب استدعاء '{rv[5][0]}' (السطر {rv[5][1] + 1})"
        elif "P" in rv[0]:
            state = "holds a program argument (argv), not part of the number"
            state_ar = "يحمل وسيط البرنامج (argv) وليس جزءاً من الرقم"
        elif rv[1] & need != need:
            state, state_ar = "was never set", "لم يُضبط أبداً"
        if state:
            fixes = []
            divisor_fam = GP.get(o.reg, ("",))[0] if o.kind == "reg" else ""
            if divisor_fam != fam and not (o.kind == "mem" and fam in [GP[r][0] for r in o.regs if r in GP]):
                fixes = [self.insert_before(st, [fixins], f"Insert {fixins} before {m}",
                                            f"أدرج {fixins} قبل {m}")]
            if self.p.att:
                fixes = []
            self.add("ASM403", st, st.mcol, st.end_col, fixes, key=("ASM403", st.line), mnem=m.upper(), pair=pair,
                     high=high, low=low, state=state, state_ar=state_ar, fixins=fixins)
            return
        if m == "idiv" and fam == "rdx" and rv[0] == frozenset({"Z"}):
            ext = {16: "cwd", 32: "cdq", 64: "cqo"}[size]
            fx = [] if self.p.att else [self.insert_before(st, [ext], f"Insert {ext} before idiv",
                                                           f"أدرج {ext} قبل idiv")]
            self.add("ASM408", st, st.mcol, st.end_col, fx, high=high, low=low, ext=ext.upper())

    def check_flags(self, u: Unit, b: Block, pos: int, st: Stmt, S: State) -> None:
        p = self.p
        m = st.mnem
        tested = flags_of(m)[0] - {"DF"}
        if not tested:
            return
        # walk back inside the block
        k = b.stmts.index(pos) - 1
        prev = None
        passed = 0
        writer = None
        while k >= 0:
            s2 = p.stmts[u.stmts[b.stmts[k]]]
            if s2.kind == "macro":
                return
            if s2.kind != "instr":
                k -= 1
                continue
            if s2.mnem in ("call", "int", "syscall", "popf", "popfd", "popfq", "sahf", "iret"):
                return
            r, w, und = flags_of(s2.mnem)
            if prev is None:
                prev = s2
            passed += 1
            if tested & und and not (tested & w - und):
                self.add("ASM308", st, st.mcol, st.end_col, mnem=m.upper(), flags=" ".join(sorted(tested & und)),
                         prev=s2.mnem.upper(), prev_up=s2.mnem.upper(), hint=self.test_hint(s2))
                return
            if tested & w:
                writer = s2
                break
            if s2.mnem in ("inc", "dec") and tested == {"CF"} and m in JCC and passed == 1:
                self.add("ASM310", st, st.mcol, st.end_col, mnem=m.upper(), prev=s2.mnem.upper())
                return
            k -= 1
        if writer is not None:
            self.signed_hint(st, writer, S)
            return
        if prev is None:
            return
        # nothing in this block writes the flags: are they set by every block before it?
        for pi in b.preds:
            pb = u.blocks[pi]
            for x in reversed(pb.stmts):
                s3 = p.stmts[u.stmts[x]]
                if s3.kind != "instr":
                    continue
                if tested & flags_of(s3.mnem)[1] or s3.mnem in ("call", "int"):
                    return
        if b.preds and b.idx != 0:
            pass
        if prev.mnem in FLAGLESS_SUSPECTS or prev.mnem.startswith("set"):
            hint = self.test_hint(prev)
            fixes = []
            reg = prev.ops[0] if prev.ops and prev.ops[0].kind == "reg" else None
            if reg is not None and prev.mnem not in ("cbw", "cwde", "cdqe", "cwd", "cdq", "cqo"):
                ins = f"test {reg.text}, {reg.text}" if not p.att else f"test {reg.text}, {reg.text}"
                fixes = [self.insert_before(st, [ins], f"Insert {ins}", f"أدرج {ins}")]
            self.add("ASM307", st, st.mcol, st.end_col, fixes, mnem=m.upper(), flags=" ".join(sorted(tested)),
                     prev=prev.mnem.upper(), prev_up=prev.mnem.upper(), hint=hint)

    def test_hint(self, s2: Stmt) -> str:
        reg = s2.ops[0] if s2.ops and s2.ops[0].kind == "reg" else None
        if reg is None:
            return "cmp / test"
        return f"test {reg.text}, {reg.text} (or cmp {reg.text}, value)"

    def signed_hint(self, st: Stmt, writer: Stmt, S: State) -> None:
        m = st.mnem
        if writer.mnem != "cmp" or len(writer.ops) != 2 or m not in JCC:
            return
        a, c = writer.ops
        if m in SIGNED_J:
            addr = False
            for o in (a, c):
                if o.kind == "imm" and o.addr:
                    addr = True
                elif o.kind == "reg" and o.reg in GP:
                    rv = S.r.get(GP[o.reg][0], _UNDEF)
                    if rv[4] and not rv[4].startswith("=") and GP[o.reg][1] >= (16 if self.mode == 16 else 32):
                        addr = True
            if addr:
                better = SIGNED_J[m]
                fx = Fix(f"Use {better.upper()}", f"استخدم {better.upper()}",
                         [{"range": [st.line, st.mcol, st.line, st.mend], "text": better}])
                self.add("ASM309", st, st.mcol, st.mend, [fx], mnem=m.upper(), kind="signed",
                         kind_ar="بإشارة", what="the compared values are addresses (unsigned)",
                         what_ar="القيم المقارنة عناوين (بدون إشارة)", better=better.upper())
        elif m in UNSIGNED_J and c.kind == "imm" and c.value is not None and c.neg:
            better = UNSIGNED_J[m]
            fx = Fix(f"Use {better.upper()}", f"استخدم {better.upper()}",
                     [{"range": [st.line, st.mcol, st.line, st.mend], "text": better}])
            self.add("ASM309", st, st.mcol, st.mend, [fx], mnem=m.upper(), kind="unsigned", kind_ar="بدون إشارة",
                     what=f"it compares with the negative number {c.text}",
                     what_ar=f"المقارنة مع رقم سالب {c.text}", better=better.upper())


def check_flow(prog: Program, out: list, symbols=None) -> Flow:
    f = Flow(prog, out, symbols)
    f.run()
    return f
