"""Built-in disassembly + p-code for CPUs that Capstone does not know, through Ghidra's SLEIGH engine (pypcode).

No Java and no Ghidra installation: ``pypcode`` (BSD-2-Clause, https://github.com/angr/pypcode) wraps Ghidra's C++
SLEIGH library and ships Ghidra's compiled processor specifications (Apache-2.0). CPUs that upstream Ghidra does
not have come from vendored community modules in ``third_party/ghidra-processors`` (C166 / ST10, RL78), compiled
on first use by :mod:`.sleigh_build`.

Besides the text (mnemonic + operands) every instruction is lifted to p-code, and a small constant propagation over
the p-code (per straight-line run, reset at calls / jumps) gives:

* branch / call targets and returns from the p-code flow ops (BRANCH, CBRANCH, CALL, RETURN, BRANCHIND ...);
* data references: LOAD / STORE addresses and direct memory operands in the code space, addresses built in two
  steps (V850 MOVHI + LD, VLE E_LIS + E_LHZ, C166 MOV Rw,#tbl + MOV Rx,[Rw]), table bases of indexed loads
  (8051 MOV DPTR,#tbl ... MOVC A,@A+DPTR) - the reference is put on the instruction that uses the address and on
  the one that loaded the constant;
* C166: the DPP paging and EXTP / EXTS prefixes that the upstream module leaves to Java code (user operations
  ``GetPagedOffset``, ``c166_reg_offset_addr``, ``segment``) are resolved here.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

try:
    import pypcode as _pc
except ImportError:                     # optional dependency - the listing then says how to get it
    _pc = None


@dataclass(frozen=True)
class Lang:
    lang_id: str
    label: str
    module: str = ""                    # vendored module in third_party/ghidra-processors ("" = bundled in pypcode)
    context: tuple = ()                 # ((name, value), ...) context variable defaults
    align: int = 1
    psize: int = 2                      # pointer size in bytes (32-bit CPUs get the "address completion" rule)
    endian: str = "little"
    ghidra: str = ""                    # language id for "Analyze in Ghidra" (upstream Ghidra)


LANGS: dict[str, Lang] = {
    "8051": Lang("8051:BE:16:default", "Intel 8051 / MCS-51", endian="big", ghidra="8051:BE:16:default"),
    "v850": Lang("V850:LE:32:default", "Renesas V850 / V850E", align=2, psize=4, ghidra="V850:LE:32:default"),
    "rh850": Lang("V850:LE:32:v850e3v5", "Renesas RH850 (V850E3v5)", align=2, psize=4,
                  ghidra="V850:LE:32:v850e3v5"),
    "ppc-vle": Lang("PowerPC:BE:64:VLE-32addr", "PowerPC e200 VLE", context=(("vle", 1),), align=2, psize=4,
                    endian="big", ghidra="PowerPC:BE:64:VLE-32addr"),
    "c166": Lang("C166:LE:16:default", "Infineon C166 / C167 / ST10 / XC16x", module="C166", align=2),
    "rl78": Lang("RL78:LE:16:default", "Renesas RL78", module="RL78"),
    "m16c": Lang("M16C/60:LE:16:default", "Renesas M16C/60 / R8C", ghidra="M16C/60:LE:16:default"),
    "m32c": Lang("M16C/80:LE:16:default", "Renesas M16C/80 / M32C", ghidra="M16C/80:LE:16:default"),
    "mcs96": Lang("MCS96:LE:16:default", "Intel MCS-96 (80C196)", ghidra="MCS96:LE:16:default"),
    "hcs08": Lang("HCS08:BE:16:default", "Freescale HCS08", endian="big", ghidra="HCS08:BE:16:default"),
    "hc08": Lang("HC08:BE:16:default", "Freescale HC08", endian="big", ghidra="HC08:BE:16:default"),
    "hcs12x": Lang("HCS12:BE:24:default", "Freescale HCS12X (paged)", endian="big", ghidra="HCS12:BE:24:default"),
    # used only when Capstone is not installed
    "sleigh:tricore": Lang("tricore:LE:32:default", "Infineon TriCore", align=2, psize=4),
    "sleigh:sh2": Lang("SuperH:BE:32:SH-2A", "SuperH SH-2A", align=2, psize=4, endian="big"),
    "sleigh:m68k": Lang("68000:BE:32:CPU32", "68K / CPU32", align=2, psize=4, endian="big"),
    "sleigh:hc12": Lang("HC-12:BE:16:default", "HC12", endian="big"),
    "sleigh:ppc": Lang("PowerPC:BE:32:e500", "PowerPC Book E", align=4, psize=4, endian="big"),
}
ALIASES = {"st10": "c166", "c167": "c166", "xc16x": "c166", "xc166": "c166", "r8c": "m16c", "v850e3": "rh850",
           "mcs51": "8051", "80c196": "mcs96", "s12x": "hcs12x", "vle": "ppc-vle", "e200z": "ppc-vle"}
# Capstone arch -> SLEIGH fallback
FALLBACK = {"tricore": "sleigh:tricore", "sh2": "sleigh:sh2", "m68k": "sleigh:m68k", "hc12": "sleigh:hc12",
            "ppc": "sleigh:ppc"}


def canon(arch: str) -> str:
    return ALIASES.get(arch, arch)


def available() -> bool:
    return _pc is not None


def knows(arch: str) -> bool:
    """True when *arch* has a SLEIGH language here (pypcode may still be missing)."""
    return canon(arch) in LANGS


def supported(arch: str) -> bool:
    if _pc is None or canon(arch) not in LANGS:
        return False
    lg = LANGS[canon(arch)]
    if lg.module:
        from . import sleigh_build
        return lg.module in sleigh_build.available_modules() and sleigh_build.sleigh_compiler() is not None
    return True


def reason(arch: str) -> str:
    a = canon(arch)
    if a not in LANGS:
        return f"No SLEIGH language for '{arch}'."
    if _pc is None:
        return (f"The built-in {LANGS[a].label} disassembler needs pypcode (Ghidra's SLEIGH engine for Python): "
                "pip install pypcode. 'Analyze in Ghidra' works without it when Ghidra is installed.")
    return f"The SLEIGH module for {LANGS[a].label} is not available."


_tls = threading.local()
_build_lock = threading.Lock()


def _language(arch: str):
    lg = LANGS[canon(arch)]
    if not lg.module:
        lang = _pc.ArchLanguage.from_id(lg.lang_id)
        if lang is None:
            raise ValueError(f"pypcode has no language {lg.lang_id}")
        return lang
    from . import sleigh_build
    with _build_lock:
        ldefs = sleigh_build.ldefs_path(lg.module)
    for la in _pc.Arch(lg.module, str(ldefs)).languages:
        if la.id == lg.lang_id:
            return la
    raise ValueError(f"{ldefs} has no language {lg.lang_id}")


def context(arch: str):
    """A pypcode Context for *arch* (one per thread - SLEIGH contexts are not thread safe)."""
    if _pc is None:
        raise ValueError(reason(arch))
    cache = getattr(_tls, "ctx", None)
    if cache is None:
        cache = _tls.ctx = {}
    a = canon(arch)
    if a not in cache:
        try:
            ctx = _pc.Context(_language(a))
        except RuntimeError as e:          # sleigh_build errors
            raise ValueError(str(e)) from e
        for k, v in LANGS[a].context:
            ctx.setVariableDefault(k, v)
        cache[a] = ctx
    return cache[a]


# ============================================================================ decoding
@dataclass
class Insn:
    address: int
    size: int
    raw: bytes
    mnemonic: str
    ops: str
    target: int | None = None
    call: bool = False
    ret: bool = False
    refs: list[int] = field(default_factory=list)
    comment: str = ""
    pcode: list = field(default_factory=list)


_BAD = tuple(e for e in ((_pc.BadDataError, _pc.UnimplError, _pc.DecoderError, _pc.LowlevelError)
                         if _pc else ()) if e)


def _decode(ctx, buf: bytes, addr: int, max_ins: int):
    """[(pypcode Instruction, [PcodeOp])] for as many whole instructions of *buf* as decode."""
    try:
        dis = ctx.disassemble(buf, addr, 0, 0, max_ins).instructions
    except _BAD:
        return []
    ins = []
    for i in dis:
        if i.addr.offset + i.length > addr + len(buf) or i.length <= 0:
            break                       # SLEIGH read past the buffer (zeros): not a whole instruction
        ins.append(i)
    if not ins:
        return []
    ops_by: dict[int, list] = {i.addr.offset: [] for i in ins}
    try:
        ops = ctx.translate(buf, addr, 0, 0, len(ins)).ops
    except _BAD:
        ops = None
    if ops is None:                     # one instruction has no p-code semantics - lift them one by one
        for i in ins:
            try:
                o = i.addr.offset - addr
                ops_by[i.addr.offset] = list(ctx.translate(buf[o:], i.addr.offset, 0, 0, 1).ops)
            except _BAD:
                pass
    else:
        cur = None
        for op in ops:
            if op.opcode == _pc.OpCode.IMARK:
                a = op.inputs[0].offset
                if a in ops_by:
                    cur = a
                continue
            if cur is not None:
                ops_by[cur].append(op)
    return [(i, ops_by[i.addr.offset]) for i in ins]


# ============================================================================ constant propagation
_MASK = {1: 0xFF, 2: 0xFFFF, 3: 0xFFFFFF, 4: 0xFFFFFFFF, 8: 0xFFFFFFFFFFFFFFFF}


def _m(v: int, size: int) -> int:
    return v & _MASK.get(size, (1 << (8 * size)) - 1)


def _sx(v: int, size: int) -> int:
    v = _m(v, size)
    return v - (1 << (8 * size)) if v >> (8 * size - 1) else v


class _Prop:
    """Known values of registers / temporaries: key (space, offset, size) -> (value, origin address, derived)."""

    def __init__(self, arch: str, lg: Lang, mm, lo: int, hi: int):
        self.arch, self.lg, self.mm, self.lo, self.hi = arch, lg, mm, lo, hi
        self.vals: dict[str, dict[tuple[int, int], tuple[int, int, bool]]] = {}
        self.hints: dict[tuple[str, int, int], tuple[int, int]] = {}     # unknown value = known base + index
        self.code_space = ""
        self.big_regs = lg.endian == "big"
        self.ext: tuple[str, int, int] | None = None     # C166 EXTP / EXTS: (kind, page / segment, count)
        self.dpp: dict[int, int] = {}                     # C166 DPPn set by the code (kept across calls)

    def reset(self):
        self.vals.clear()
        self.hints.clear()
        self.ext = None

    def inside(self, v: int | None) -> bool:
        return v is not None and self.lo <= v < self.hi

    # ---- storage
    def get(self, vn):
        sp = vn.space.name
        if sp == "const":
            return vn.offset, None, False
        d = self.vals.get(sp)
        if not d:
            return None
        key = (vn.offset, vn.size)
        if key in d:
            return d[key]
        for (o, s), (v, org, der) in d.items():            # part of a wider known register
            if o <= vn.offset and vn.offset + vn.size <= o + s:
                sh = (o + s - vn.offset - vn.size) if self.big_regs else (vn.offset - o)
                return _m(v >> (8 * sh), vn.size), org, der
        return None

    def kill(self, vn):
        sp = vn.space.name
        d = self.vals.get(sp)
        if d:
            a, b = vn.offset, vn.offset + vn.size
            for k in [k for k in d if k[0] < b and a < k[0] + k[1]]:
                del d[k]
        self.hints.pop((sp, vn.offset, vn.size), None)

    def put(self, vn, val, org, der):
        self.kill(vn)
        self.vals.setdefault(vn.space.name, {})[(vn.offset, vn.size)] = (_m(val, vn.size), org, der)

    # ---- one instruction
    def step(self, ins: Insn, ops: list, lines_by_addr: dict) -> None:
        here = ins.address
        self.vals.pop("unique", None)
        refs: list[int] = []
        c166 = self.arch == "c166"
        if c166:
            self._c166_prefix(ins)

        def ref(addr: int | None, origin: int | None = None):
            if not self.inside(addr) or (c166 and 0xF000 <= addr <= 0xFFFF):    # C166 SFR / ESFR / IRAM
                return
            if addr not in refs:
                refs.append(addr)
            if origin is not None and origin != here and origin in lines_by_addr:
                ln = lines_by_addr[origin]
                if addr not in ln.refs and addr != ln.target:
                    ln.refs.append(addr)
        OP = _pc.OpCode
        for op in ops:
            oc = op.opcode
            ins_ = op.inputs
            out = op.output
            if oc in (OP.BRANCH, OP.CALL):
                if ins_[0].space.name == self.code_space:
                    ins.target = ins_[0].offset
                ins.call = ins.call or oc == OP.CALL
                continue
            if oc == OP.CBRANCH:
                if ins_[0].space.name == self.code_space:
                    ins.target = ins_[0].offset
                continue
            if oc in (OP.BRANCHIND, OP.CALLIND):
                g = self.get(ins_[0])
                if g is not None and self.inside(g[0]):
                    ins.target = g[0]
                ins.call = ins.call or oc == OP.CALLIND
                continue
            if oc == OP.RETURN:
                ins.ret = True
                continue
            # direct memory operands in the code space (absolute addressing)
            for v in ins_:
                if v.space.name == self.code_space:
                    ref(v.offset)
            if out is not None and out.space.name == self.code_space:
                ref(out.offset)
            if oc in (OP.LOAD, OP.STORE):
                space = ins_[0].getSpaceFromConst().name
                g = self.get(ins_[1])
                code = space == self.code_space
                if g is not None:
                    if code:
                        ref(g[0], g[1])
                    if c166 and oc == OP.STORE and code and 0xFE00 <= g[0] < 0xFE08:     # MOV DPPn,...
                        gv = self.get(ins_[2])
                        if gv is None:
                            self.dpp.pop((g[0] - 0xFE00) // 2, None)
                        else:
                            self.dpp[(g[0] - 0xFE00) // 2] = gv[0] & 0x3FF
                else:
                    h = self.hints.get((ins_[1].space.name, ins_[1].offset, ins_[1].size))
                    if h is not None and code:
                        ref(h[0], h[1])
                if oc == OP.LOAD and out is not None:
                    val = None
                    if g is not None and code and out.size == self.lg.psize and self.lg.psize >= 4 \
                            and self.inside(g[0]):
                        try:                    # pointer in a literal pool (constant flash data)
                            val = int.from_bytes(self.mm.read(g[0], out.size), self.lg.endian)
                        except Exception:  # noqa: BLE001 - outside the image
                            val = None
                    if val is None:
                        self.kill(out)
                    else:
                        self.put(out, val, here, False)
                continue
            if out is None:
                continue
            if oc == OP.CALLOTHER:
                val = self._c166_userop(op) if c166 else None
                if val is None:
                    self.kill(out)
                else:
                    org = next((g[1] for v in ins_[1:] if v.space.name != "const"
                                for g in [self.get(v)] if g is not None and g[1] is not None), here)
                    self.put(out, val, org, True)
                continue
            vals = [self.get(v) for v in ins_]
            res = self._eval(oc, ins_, vals, out.size)
            if res is None:
                self.kill(out)
                if oc in (OP.INT_ADD, OP.PTRADD) and len(vals) >= 2:     # known base + unknown index
                    known = [g for g in vals[:2] if g is not None]
                    if len(known) == 1 and self.inside(known[0][0]) and known[0][0] >= 0x100:
                        org0 = known[0][1]
                        self.hints[(out.space.name, out.offset, out.size)] = (known[0][0], here if org0 is None else org0)
                elif oc in (OP.COPY, OP.INT_ZEXT, OP.CAST):
                    h = self.hints.get((ins_[0].space.name, ins_[0].offset, ins_[0].size))
                    if h is not None:
                        self.hints[(out.space.name, out.offset, out.size)] = h
                continue
            # origin: inherited from an input with the same value, else this instruction
            nonconst = [g for v, g in zip(ins_, vals) if v.space.name != "const" and g is not None]
            org = next((g[1] for g in nonconst if g[0] == res and g[1] is not None), None)
            der = any(g[2] for g in nonconst) or (bool(nonconst) and oc not in (OP.COPY, OP.INT_ZEXT, OP.INT_SEXT,
                                                                                OP.SUBPIECE, OP.CAST))
            if org is None:
                org = here
            self.put(out, res, org, der)
            if c166 and out.space.name == self.code_space and 0xFE00 <= out.offset < 0xFE08:
                self.dpp[(out.offset - 0xFE00) // 2] = res & 0x3FF      # MOV DPPn,#page
            # address completed in a register (32-bit CPUs: E_LIS + E_ADD16I, MOVHI + MOVEA ...)
            if der and self.lg.psize >= 4 and out.space.name not in ("unique",) and self.inside(res) \
                    and res >= 0x100 and oc != OP.COPY:
                ref(res)
            elif der and self.lg.psize >= 4 and out.space.name != "unique" and oc == OP.COPY and \
                    self.inside(res) and res >= 0x100 and org == here:
                ref(res)
        if c166 and self.ext is not None and not ins.mnemonic.startswith("ext"):
            kind, page, n = self.ext
            self.ext = (kind, page, n - 1) if n > 1 else None
        ins.refs = [r for r in refs if r != ins.target]
        ins.pcode = ops

    def _eval(self, oc, vns, vals, size):
        OP = _pc.OpCode
        if any(g is None for g in vals):
            # x AND 0 / x * 0 are still known
            if oc in (OP.INT_AND, OP.INT_MULT) and any(g is not None and g[0] == 0 for g in vals):
                return 0
            return None
        v = [g[0] for g in vals]
        try:
            if oc in (OP.COPY, OP.INT_ZEXT, OP.CAST):
                return _m(v[0], size)
            if oc == OP.INT_SEXT:
                return _m(_sx(v[0], vns[0].size), size)
            if oc == OP.INT_ADD or oc == OP.PTRADD:
                return _m(v[0] + v[1] * (v[2] if len(v) > 2 and oc == OP.PTRADD else 1), size)
            if oc == OP.INT_SUB:
                return _m(v[0] - v[1], size)
            if oc == OP.INT_AND:
                return v[0] & v[1]
            if oc == OP.INT_OR:
                return _m(v[0] | v[1], size)
            if oc == OP.INT_XOR:
                return _m(v[0] ^ v[1], size)
            if oc == OP.INT_MULT:
                return _m(v[0] * v[1], size)
            if oc == OP.INT_LEFT:
                return _m(v[0] << v[1], size) if v[1] < 64 else 0
            if oc == OP.INT_RIGHT:
                return _m(v[0], vns[0].size) >> v[1] if v[1] < 64 else 0
            if oc == OP.INT_SRIGHT:
                return _m(_sx(v[0], vns[0].size) >> min(v[1], 63), size)
            if oc == OP.INT_NEGATE:
                return _m(~v[0], size)
            if oc == OP.INT_2COMP:
                return _m(-v[0], size)
            if oc == OP.PIECE:
                return _m((v[0] << (8 * vns[1].size)) | _m(v[1], vns[1].size), size)
            if oc == OP.SUBPIECE:
                return _m(v[0] >> (8 * v[1]), size)
        except (OverflowError, ValueError):
            return None
        return None

    # ---- C166 / ST10: DPP paging + EXTP / EXTS prefixes
    def _c166_prefix(self, ins: Insn) -> None:
        m = ins.mnemonic
        if m not in ("extp", "extpr", "exts", "extsr"):
            return
        parts = [p.strip().lstrip("#") for p in ins.ops.split(",")]
        if len(parts) != 2:
            return
        try:
            n = int(parts[1], 0)
        except ValueError:
            n = 1
        try:
            page = int(parts[0], 0)
        except ValueError:                      # EXTP Rw,#n: the page is in a register
            page = self._reg_value(parts[0])
        self.ext = None if page is None else ("p" if m.startswith("extp") else "s", page, max(1, n))

    def _reg_value(self, name: str) -> int | None:
        try:
            ctx = context(self.arch)
            vn = ctx.registers.get(name.upper()) or ctx.registers.get(name.lower())
        except Exception:  # noqa: BLE001
            vn = None
        if vn is None:
            return None
        g = self.get(vn)
        return None if g is None else g[0]

    def _dpp(self, n: int) -> int:
        return self.dpp.get(n, n)                     # reset values DPP0..3 = 0, 1, 2, 3

    def _page(self, addr16: int) -> int:
        addr16 &= 0xFFFF
        if self.ext is not None:
            kind, page, _n = self.ext
            if kind == "p":
                return (page << 14) | (addr16 & 0x3FFF)
            return (page << 16) | addr16
        return (self._dpp(addr16 >> 14) << 14) | (addr16 & 0x3FFF)

    def _c166_userop(self, op) -> int | None:
        name = op.inputs[0].getUserDefinedOpName()
        args = [self.get(v) for v in op.inputs[1:]]
        if any(a is None for a in args):
            return None
        a = [x[0] for x in args]
        if name == "GetPagedOffset" and a:
            return self._page(a[-1])
        if name == "c166_reg_offset_addr" and len(a) >= 2:
            return self._page(a[0] + a[1])
        if name == "segment" and len(a) >= 2:
            return ((a[0] & 0xFF) << 16) | (a[1] & 0xFFFF)
        return None


# ============================================================================ sweep
def sweep(mm, arch: str, start: int, length: int, max_lines: int, make_line, chunk: int = 0x800,
          keep_pcode: bool = False) -> list:
    """Linear sweep of [start, start+length) like the Capstone path; *make_line* builds the result objects
    (radide.firmware.analysis.disasm.Line). Undecodable units become '.byte' / '.short' lines."""
    a0 = canon(arch)
    lg = LANGS[a0]
    ctx = context(a0)
    al = lg.align
    lo, hi = mm.min_address, mm.max_address
    end = min(start + length, hi)
    out: list = []
    by_addr: dict[int, object] = {}
    prop = _Prop(a0, lg, mm, lo, hi)
    a = start
    while a < end and len(out) < max_lines:
        seg = mm.segment_at(a)
        if seg is None:
            a = min((s.address for s in mm.segments if s.address > a), default=end)
            prop.reset()
            continue
        chunk_end = min(seg.end, end)
        buf_end = min(seg.end, chunk_end + 16, a + chunk + 16)     # a little look-ahead for the last instruction
        buf = bytes(seg.data[a - seg.address:buf_end - seg.address])
        decoded = _decode(ctx, buf, a, max(1, min(max_lines - len(out), chunk)))
        if not decoded:
            n = min(al, chunk_end - a) or 1
            raw = bytes(seg.data[a - seg.address:a - seg.address + n])
            out.append(make_line(Insn(a, n, raw, ".byte" if n == 1 else ".short" if n == 2 else ".word",
                                      ", ".join(f"0x{b:02x}" for b in raw))))
            a += n
            prop.reset()
            continue
        nxt = a
        for i, ops in decoded:
            ia = i.addr.offset
            if ia >= chunk_end:
                break
            if not prop.code_space:
                prop.code_space = i.addr.space.name
            mn, body = i.mnem, i.body.strip()
            if mn.isupper():                    # Ghidra's 8051 / MCS-96 modules print upper case
                mn, body = mn.lower(), body.lower()
            ins = Insn(ia, i.length, buf[ia - a:ia - a + i.length], mn.lower(), body)
            prop.step(ins, ops, by_addr)
            if not keep_pcode:
                ins.pcode = []
            ln = make_line(ins)
            out.append(ln)
            by_addr[ia] = ln
            if len(by_addr) > 64:              # origins only matter within a short window
                for k in list(by_addr)[:32]:
                    del by_addr[k]
            if ins.ret or ins.call or (ins.target is not None and not _is_conditional(ops)):
                prop.reset()
            nxt = ia + i.length
            if len(out) >= max_lines:
                break
        a = max(a + 1, nxt)
    return out


def _is_conditional(ops) -> bool:
    return any(op.opcode == _pc.OpCode.CBRANCH and op.inputs[0].space.name != "const" for op in ops)


def pcode_listing(mm, arch: str, start: int, count: int = 40) -> str:
    """Disassembly with the p-code of every instruction (Ghidra's intermediate language), as text."""
    lines = sweep(mm, arch, start, count * 8, count, lambda ins: ins, keep_pcode=True)
    out = []
    for ins in lines:
        out.append(f"{ins.address:08X}  {ins.mnemonic} {ins.ops}".rstrip())
        out += ["          " + t for t in format_pcode(ins.pcode)]
    return "\n".join(out)


def format_pcode(ops) -> list[str]:
    out = []
    for op in ops:
        try:
            out.append(_pc.PcodePrettyPrinter.fmt_op(op))
        except Exception:  # noqa: BLE001 - printing is cosmetic
            out.append(op.opcode.name)
    return out
