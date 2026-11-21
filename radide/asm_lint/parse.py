"""Source model of the analyzer: statements, typed operands, sections and symbols (no Qt).

``Program(text, path, dialect=...)`` splits an assembly file into statements:

* ``Stmt.kind``: ``instr`` (a real x86 instruction), ``data`` (db / dw / resb / .byte ...), ``directive``
  (section, extern, proc, equ ...), ``macro`` (a macro call such as ``invoke`` or ``print``) or ``label`` (only
  labels on the line);
* instruction operands are typed (``Operand``): register (with size and register family), immediate (with its
  value when it can be computed), memory (base / index / scale / segment / size) or symbol (a jump target);
* AT&T operands are converted to Intel order, so the checks see one shape for every dialect.

Line splitting reuses radide/asm_intel/index.mask_line (comments, strings, GAS block comments) and the
instruction / register tables of radide/asm_intel/isa.py. The context-free part of each line is cached, so
re-analysing a big file after one edit only re-splits the edited lines.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..asm_intel import isa
from ..asm_intel.index import (abi_of, code_bits, comment_of, detect_dialect, gas_syntax, mask_line,
                               project_asm_settings, target_os)

# ============================================================================ registers
GP: dict[str, tuple[str, int]] = {}          # name -> (family, bits) for general purpose registers
for _n, _r in isa.REGISTERS.items():
    if _r.size in (8, 16, 32, 64) and _r.family in {
            "rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", *(f"r{i}" for i in range(8, 16))}:
        GP[_n] = (_r.family, _r.size)
SEGS = {"cs", "ds", "es", "ss", "fs", "gs"}
HIGH8 = {"ah", "bh", "ch", "dh"}
REX8 = {"spl", "bpl", "sil", "dil"} | {f"r{i}b" for i in range(8, 16)} | {f"r{i}l" for i in range(8, 16)}
REG64_ONLY = {n for n, (f, s) in GP.items() if s == 64 or f.startswith("r") and f[1:].isdigit()} | REX8
REG32 = {n for n, (f, s) in GP.items() if s == 32 and not (f[1:].isdigit())}
FAMILY_NAMES: dict[str, dict[int, str]] = {
    **{f"r{c}x": {64: f"r{c}x", 32: f"e{c}x", 16: f"{c}x", 8: f"{c}l"} for c in "abcd"},
    **{f"r{n}": {64: f"r{n}", 32: f"e{n}", 16: n, 8: f"{n}l"} for n in ("si", "di", "bp", "sp")},
    **{f"r{i}": {64: f"r{i}", 32: f"r{i}d", 16: f"r{i}w", 8: f"r{i}b"} for i in range(8, 16)},
}
MASKS = {8: 0xFF, 16: 0xFFFF, 32: 0xFFFFFFFF, 64: 0xFFFFFFFFFFFFFFFF}


def sibling(reg: str, bits: int, mode: int = 64) -> str:
    """'eax', 8 -> 'al' (the register of the same family with another size; '' when none)."""
    info = GP.get(reg.lower())
    if not info:
        return ""
    name = FAMILY_NAMES.get(info[0], {}).get(bits, "")
    if mode != 64 and name in REG64_ONLY:
        return ""
    return name


def reg_mask(reg: str) -> int:
    """The bits of the 64-bit family a register covers (AH = 0xFF00)."""
    r = reg.lower()
    if r in HIGH8:
        return 0xFF00
    info = GP.get(r)
    return MASKS.get(info[1], 0) if info else 0


# ============================================================================ keywords
SIZE_WORDS = {"byte": 8, "sbyte": 8, "word": 16, "sword": 16, "dword": 32, "sdword": 32, "fword": 48,
              "pword": 48, "qword": 64, "sqword": 64, "tword": 80, "tbyte": 80, "oword": 128, "dqword": 128,
              "xmmword": 128, "yword": 256, "ymmword": 256, "zword": 512, "zmmword": 512, "real4": 32,
              "real8": 64, "real10": 80, "near": 0, "far": 0, "short": 0}
DATA_SIZES = {
    "db": 8, "byte": 8, "sbyte": 8, ".byte": 8, ".ascii": 8, ".asciz": 8, ".string": 8, "rb": 8, "resb": 8,
    "du": 16, "dw": 16, "word": 16, "sword": 16, ".word": 16, ".short": 16, ".hword": 16, ".value": 16, "rw": 16,
    "resw": 16, "dd": 32, "dword": 32, "sdword": 32, ".long": 32, ".int": 32, "rd": 32, "resd": 32, "real4": 32,
    ".float": 32, ".single": 32, "dq": 64, "qword": 64, "sqword": 64, ".quad": 64, "rq": 64, "resq": 64,
    "real8": 64, ".double": 64, "dt": 80, "tbyte": 80, "real10": 80, "rt": 80, "rest": 80, "do": 128,
    "oword": 128, "xmmword": 128, ".octa": 128, "reso": 128, "ddq": 128, "dy": 256, "ymmword": 256, "resy": 256,
    "dz": 512, "resz": 512, "df": 48, "fword": 48, "dp": 48, "rp": 48, "rf": 48,
    ".space": 8, ".skip": 8, ".zero": 8, ".fill": 8, ".incbin": 8, "file": 8, "incbin": 8,
}
MASM_DATA_WORDS = {"byte", "sbyte", "word", "sword", "dword", "sdword", "fword", "qword", "sqword", "tbyte",
                   "real4", "real8", "real10", "oword", "xmmword", "ymmword"}
NAME_FIRST_WORDS = {"equ", "=", "proc", "endp", "macro", "struct", "struc", "union", "segment", "ends", "label",
                    "textequ", "record", "typedef", "proto", "catstr", "instr", "sizestr", "substr"}
PREFIXES = {"rep", "repe", "repz", "repne", "repnz", "lock", "o16", "o32", "o64", "a16", "a32", "a64", "data16",
            "data32", "addr16", "addr32", "rex", "rex64", "notrack", "bnd", "xacquire", "xrelease", "wait"}
DIRECTIVES = {
    "section", "segment", "global", "globl", "extern", "extrn", "externdef", "public", "bits", "use16", "use32",
    "use64", "default", "org", "align", "alignb", "times", "cpu", "struc", "endstruc", "istruc", "iend", "at",
    "absolute", "common", "static", "incbin", "include", "includelib", "format", "entry", "library", "import",
    "export", "data", "end", "proc", "endp", "local", "locals", "endl", "uses", "assume", "option", "model",
    "macro", "endm", "if", "ifdef", "ifndef", "else", "elseif", "endif", "rept", "irp", "irpc", "while",
    "repeat", "virtual", "label", "equ", "define", "purge", "restore", "struct", "ends", "union", "even",
    "title", "subttl", "page", "name", "comment", "invoke", "stdcall", "ccall", "cinvoke", "fastcall",
    "frame", "endf", "heap", "stack", "postpone", "match", "forward", "reverse", "common", "display", "err",
    "load", "store", "dup", "proto", "typedef", "record", "textequ", "exitm", "goto", "for", "forc",
    "pushcontext", "popcontext", "alias", "radix", "safeseh", "subsection", "warning", "dosseg", ".dosseg",
    "jumps", "locals", "ideal", "masm", "p386", "p286", "p186", "p8086", "smart", "nosmart",
}
INVOKE_WORDS = {"invoke", "cinvoke", "stdcall", "ccall", "fastcall", "cinvoke64"}
EXTRA_MNEMONICS = {"lds": "data", "les": "data", "lss": "data", "lfs": "data", "lgs": "data", "salc": "misc",
                   "movs": "string", "cmps": "string", "stos": "string", "lods": "string", "scas": "string",
                   "jmpq": "control", "callq": "control", "retq": "control", "retl": "control",
                   "movabs": "data", "movabsq": "data", "int1": "system", "icebp": "system"}
EMU_MACROS = {"print", "printn", "putc", "gotoxy", "cursoroff", "cursoron"}     # emu8086.inc (keep registers)
ID_RE = r"[A-Za-z_.?@$][\w.?@$#~]*"
_ID = re.compile(ID_RE)
_LABEL = re.compile(r"\s*(" + ID_RE + r"|\d+)\s*(::?)(?![:=])")
_WORD = re.compile(r"\s*([.%#]?[A-Za-z_?@$][\w.?@$#~]*|=)")


# ============================================================================ expressions
class _Unknown(Exception):
    pass


_TOK = re.compile(r"\s*(?:"
                  r"(?P<num>0[xX][0-9a-fA-F_]+|0[bB][01_]+(?![\w])|0[oOqQ][0-7_]+|\$[0-9][0-9a-fA-F_]*|"
                  r"[0-9][0-9a-fA-F_]*[hH](?![\w])|[01_]+[bByY](?![\w])|[0-7_]+[qQoO](?![\w])|[0-9][0-9_]*[dDtT]?(?![\w]))|"
                  r"(?P<str>'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|`[^`]*`)|"
                  r"(?P<op><<|>>|[-+*/%&|^~()!])|"
                  r"(?P<id>[A-Za-z_.?@$][\w.?@$#]*))")
_WORD_OPS = {"shl": "<<", "shr": ">>", "and": "&", "or": "|", "xor": "^", "not": "~", "mod": "%"}


def parse_number(t: str) -> int | None:
    s = t.replace("_", "")
    low = s.lower()
    try:
        if low.startswith("0x"):
            return int(low[2:], 16)
        if low.startswith("$") and len(low) > 1:
            return int(low[1:], 16)
        if low.startswith(("0b",)) and len(low) > 2 and all(c in "01" for c in low[2:]):
            return int(low[2:], 2)
        if low.startswith(("0o", "0q")):
            return int(low[2:], 8)
        if low.endswith("h"):
            return int(low[:-1], 16)
        if low.endswith(("b", "y")) and all(c in "01" for c in low[:-1]) and len(low) > 1:
            return int(low[:-1], 2)
        if low.endswith(("q", "o")):
            return int(low[:-1], 8)
        if low.endswith(("d", "t")) and low[:-1].isdigit():
            return int(low[:-1])
        return int(low, 10)
    except ValueError:
        return None


def char_value(lit: str) -> int | None:
    body = lit[1:-1]
    if lit[0] in "\"`":
        body = body.encode("utf-8", "replace").decode("unicode_escape", "replace") if "\\" in body else body
    if not body or len(body) > 8:
        return None
    v = 0
    for i, ch in enumerate(body):
        v |= (ord(ch) & 0xFF) << (8 * i)
    return v


def evaluate(text: str, resolve=None) -> int | None:
    """Value of a constant expression ('10', '0Ah', 'SIZE*2', "'A'", '1 shl 4'); None when unknown."""
    toks: list[tuple[str, str]] = []
    pos = 0
    t = text.strip()
    if not t:
        return None
    while pos < len(t):
        m = _TOK.match(t, pos)
        if not m or m.end() == pos:
            if t[pos:].strip() == "":
                break
            return None
        pos = m.end()
        kind = m.lastgroup
        val = m.group(kind)
        if kind == "id" and val.lower() in _WORD_OPS:
            kind, val = "op", _WORD_OPS[val.lower()]
        toks.append((kind, val))
    i = 0

    def peek():
        return toks[i] if i < len(toks) else ("", "")

    def take():
        nonlocal i
        i += 1
        return toks[i - 1]

    def atom():
        k, v = take() if i < len(toks) else ("", "")
        if k == "num":
            n = parse_number(v)
            if n is None:
                raise _Unknown
            return n
        if k == "str":
            n = char_value(v)
            if n is None:
                raise _Unknown
            return n
        if k == "id":
            if resolve is None:
                raise _Unknown
            n = resolve(v)
            if n is None:
                raise _Unknown
            return n
        if k == "op" and v == "(":
            n = binary(0)
            if take()[1] != ")":
                raise _Unknown
            return n
        if k == "op" and v in "-+~!":
            n = atom()
            return -n if v == "-" else ~n if v == "~" else (0 if n else 1) if v == "!" else n
        raise _Unknown

    prec = {"|": 1, "^": 2, "&": 3, "<<": 4, ">>": 4, "+": 5, "-": 5, "*": 6, "/": 6, "%": 6}

    def binary(level):
        left = atom()
        while True:
            k, v = peek()
            if k != "op" or v not in prec or prec[v] < level:
                return left
            take()
            right = binary(prec[v] + 1)
            if v == "+":
                left += right
            elif v == "-":
                left -= right
            elif v == "*":
                left *= right
            elif v == "/":
                if right == 0:
                    raise _Unknown
                left = int(left / right)
            elif v == "%":
                if right == 0:
                    raise _Unknown
                left %= right
            elif v == "<<":
                left <<= min(right, 128)
            elif v == ">>":
                left >>= min(right, 128)
            elif v == "&":
                left &= right
            elif v == "|":
                left |= right
            elif v == "^":
                left ^= right

    try:
        val = binary(1)
        if i != len(toks):
            return None
        return val
    except (_Unknown, RecursionError, OverflowError, ValueError):
        return None


# ============================================================================ data model
@dataclass(slots=True)
class Operand:
    text: str
    col: int
    end: int
    kind: str = "other"           # reg sreg imm mem sym str other
    size: int = 0                 # bits (0 = unknown)
    explicit: bool = False        # a size keyword was written (dword / dword ptr / AT&T suffix)
    reg: str = ""
    base: str = ""
    index: str = ""
    scale: int = 1
    seg: str = ""                 # segment override (es / fs ...)
    syms: tuple = ()              # identifiers used (labels, constants)
    value: int | None = None      # immediate value when known
    addr: bool = False            # an immediate that is an address (label / offset x)
    rel: bool = False             # [rel x] / x(%rip)
    indirect: bool = False        # AT&T '*'
    regs: tuple = ()              # every register written inside the address
    neg: bool = False             # written with a leading '-' (immediates)
    bad: str = ""                 # address problem found while parsing
    size_col: int = -1            # column where a size keyword would be inserted
    jump_kind: str = ""           # short / near / far


@dataclass(slots=True)
class Stmt:
    line: int
    kind: str                      # instr data directive macro label
    labels: list = field(default_factory=list)      # [(name, col)]
    mnem: str = ""                 # instruction: Intel base mnemonic (lower); directive / data / macro word
    raw: str = ""                  # the word as written
    mcol: int = 0
    mend: int = 0
    prefixes: list = field(default_factory=list)
    ops: list = field(default_factory=list)          # Operand, Intel order
    optext: str = ""
    opcol: int = 0
    suffix: int = 0                # AT&T size suffix (bits)
    section: str = ""
    skind: str = ""                # section kind: code data rodata bss any
    cond: int = 0                  # conditional-assembly depth
    proc: str = ""                 # explicit proc (MASM / FASM) containing the line
    name: str = ""                 # name of name-first forms (msg db / x equ / name proc)
    indent: str = ""
    end_col: int = 0               # end of the code (before the comment)
    att_src_first: bool = False
    scope: str = ""                # the enclosing global label (parent of NASM / FASM .local labels)
    eff: tuple | None = None       # cached (reads, writes) of the flow analysis


@dataclass(slots=True)
class LabelDef:
    name: str
    key: str                       # lookup key (scope-qualified local labels, lower case in MASM)
    line: int
    col: int
    kind: str                      # code data const proc extern
    size: int = 0                  # data: element size in bits
    section: str = ""
    skind: str = ""
    directive: str = ""
    proc: str = ""
    cond: bool = False


@dataclass(slots=True)
class ProcDef:
    name: str
    line: int
    end: int
    uses: tuple = ()
    params: tuple = ()
    kind: str = "masm"             # masm | fasm


# ============================================================================ line splitting (cached)
@dataclass(slots=True)
class _Split:
    labels: list
    word: str
    raw: str
    wcol: int
    rest: str
    rcol: int
    name: str
    end: int
    indent: str


_SPLIT_CACHE: dict = {}
_MASK_CACHE: dict = {}
_OPS_CACHE: dict = {}


def _split_ops(text: str, col: int) -> list[tuple[str, int]]:
    out = []
    depth = 0
    q = ""
    start = 0
    for i, ch in enumerate(text):
        if q:
            if ch == q:
                q = ""
            continue
        if ch in "'\"`":
            q = ch
        elif ch in "([{":
            depth += 1
        elif ch in ")]}" and depth > 0:
            depth -= 1
        elif ch == "," and depth == 0:
            seg = text[start:i]
            out.append((seg.strip(), col + start + len(seg) - len(seg.lstrip())))
            start = i + 1
    seg = text[start:]
    if seg.strip() or out:
        out.append((seg.strip(), col + start + len(seg) - len(seg.lstrip())))
    return out


def split_line(masked: str, dialect: str) -> _Split:
    key = (dialect, masked)
    hit = _SPLIT_CACHE.get(key)
    if hit is not None:
        return hit
    s = masked.rstrip()
    indent = masked[:len(masked) - len(masked.lstrip())]
    labels = []
    pos = 0
    while True:
        m = _LABEL.match(s, pos)
        if not m:
            break
        nm = m.group(1)
        if nm.lower() in SEGS or nm.lower() in GP:         # es:[di] at the start of an operand list
            break
        if nm.isdigit() and dialect != "gas":
            break
        labels.append((nm, m.start(1)))
        pos = m.end()
    name = ""
    word = raw = rest = ""
    wcol = rcol = len(s)
    m = _WORD.match(s, pos)
    if m:
        w1 = m.group(1)
        m2 = _WORD.match(s, m.end())
        w2 = m2.group(1).lower() if m2 else ""
        first = False
        if w2 == "=" and not w1.startswith("."):
            first = True
        elif w2 and ((w2 in DATA_SIZES and not w2.startswith(".")) or w2 in NAME_FIRST_WORDS or
                     (w2 == "times" and dialect == "nasm")):
            first = (not w1.startswith(("%", "#")) and (not w1.startswith(".") or dialect in ("nasm", "fasm"))
                     and w1.lower() not in PREFIXES and w1.lower() not in isa.INSTRUCTIONS
                     and w1.lower() not in ("times", "label", "section", "segment", "public", "extern",
                                            "global"))
        if first:
            name = w1
            m = m2
        raw = m.group(1)
        word = raw.lower()
        wcol = m.start(1)
        rest = s[m.end():]
        rcol = m.end()
    sp = _Split(labels, word, raw, wcol, rest, rcol, name, len(s), indent)
    if len(_SPLIT_CACHE) > 200_000:
        _SPLIT_CACHE.clear()
    _SPLIT_CACHE[key] = sp
    return sp


# ============================================================================ the program
CODE_ENTRY_NAMES = {"main", "_main", "wmain", "_wmain", "winmain", "_winmain@16", "wwinmain", "start", "_start",
                    "maincrtstartup", "winmaincrtstartup", "__start", "cmain"}


class Program:
    """One assembly file, split into statements with typed operands."""

    def __init__(self, text: str, path=None, dialect: str | None = None, plugin=None, bits: int | None = None,
                 abi: str | None = None, cpu: str | None = None, project_lang: str | None = None):
        self.text = text
        self.path = Path(str(path)) if path else None
        self.dialect = dialect or detect_dialect(self.path, text, plugin)
        if self.dialect not in ("nasm", "masm", "fasm", "gas"):
            self.dialect = "nasm"
        if dialect is None and self.dialect == "nasm" and _masm16_style(text, self.path):
            self.dialect = "masm"           # emu8086 / TASM style DOS code (lea dx, msg / offset / proc ... endp)
        if dialect is None and (project_lang or self._project_language() or "").lower() == "emu8086":
            self.dialect = "masm"           # the 8086 emulator's assembler is MASM / TASM-like
        self.att = self.dialect == "gas" and gas_syntax(text) == "att"
        self.lines = text.split("\n")
        settings = project_asm_settings(self.path) if self.path else {}
        self.bits = bits or code_bits(text, self.dialect)
        self.abi = abi or abi_of(text, self.dialect, self.path)
        if abi is None:
            if self.abi in ("win64", "sysv"):
                self.bits = 64
            elif self.abi == "x86" and self.bits == 64:
                self.bits = 32
            elif self.abi == "dos16":
                self.bits = 16
        if abi is None and self.abi == "dos16" and re.search(
                r"(?m)^\s*(default\s+rel|bits\s+(32|64)|global\s+\w|extern\s+\w|format\s+pe|\.model\s+flat)|"
                r"(?<![\w%])%?(r[abcd]x|r[sd]i|r[sb]p|r(8|9|1[0-5])d?|e[abcd]x|e[sd]i|e[sb]p)\b", text[:60000],
                re.I):
            self.bits = code_bits(text, self.dialect) if code_bits(text, self.dialect) != 16 else 32
            self.abi = "win64" if self.bits == 64 else "x86"      # Windows code that also uses INT 21h
        self.os = target_os(text, self.dialect, self.path) if self.abi != "dos16" else "dos"
        if self.abi in ("win64", "x86") and self.os == "dos":
            self.os = "windows"
        low = text[:60000].lower()
        lang = (project_lang or self._project_language() or "").lower()
        self.emu = lang in ("emu8086", "dos-asm") or "#make_" in low
        if cpu:
            self.cpu = cpu
        elif self.bits == 16 and (self.emu or re.search(r"(?m)^\s*\.8086\b", low)) and \
                not re.search(r"(?m)^\s*\.(186|286|386|486|586|686)", low):
            self.cpu = "8086"
        else:
            self.cpu = ""
        self.com = self.bits == 16 and bool(re.search(r"(?m)^\s*(org\s+(100h|0x100|256)\b|#make_com#|\.model\s+tiny)",
                                                      low))
        self.default_rel = bool(re.search(r"(?m)^\s*default\s+rel\b", low))
        self.settings = settings
        self.mem_symbols = self.dialect in ("masm",) or (self.dialect == "gas" and not self.att)
        self.case = self.dialect not in ("masm",)
        self.stmts: list[Stmt] = []
        self.labels: dict[str, LabelDef] = {}         # key -> first definition
        self.dups: list[tuple[LabelDef, LabelDef]] = []
        self.consts: dict[str, str] = {}
        self.externs: dict[str, int] = {}
        self.globals: dict[str, int] = {}
        self.includes: list[tuple[str, int]] = []
        self.procs: list[ProcDef] = []
        self.entry = ""
        self.anon: list[int] = []                       # @@: lines (MASM / FASM)
        self.num_labels: dict[str, list[int]] = {}      # GAS 1: 2: ...
        self.macros: set[str] = set()
        self.struct_names: set[str] = set()
        self.macro_defined_labels = False
        self.data_syms_in_macros: set[str] = set()
        self.has_startup = ".startup" in low
        self.uses_invoke = bool(re.search(r"(?m)^\s*(\w+:)?\s*(invoke|cinvoke|stdcall|ccall|fastcall)\b", low))
        self._split()
        self._classify()

    # ------------------------------------------------------------ project
    def _project_language(self) -> str:
        if not self.path:
            return ""
        import json
        for d in [self.path.parent, *self.path.parent.parents][:4]:
            f = d / "project.radproj"
            if f.is_file():
                try:
                    return str(json.loads(f.read_text(encoding="utf-8")).get("language", ""))
                except (OSError, ValueError):
                    return ""
        return ""

    def key(self, name: str) -> str:
        return name if self.case else name.lower()

    # ------------------------------------------------------------ pass 1: statements + symbols
    def _split(self) -> None:
        dia = self.dialect
        in_block = False
        section, skind = "", ("any" if self.bits == 16 else "code" if dia in ("nasm", "fasm", "gas") else "")
        cond = 0
        macro_depth = 0
        struct_depth = 0
        proc: ProcDef | None = None
        last_global = ""
        for i, line in enumerate(self.lines):
            mk = (dia, in_block, line)
            hit = _MASK_CACHE.get(mk)
            if hit is None:
                hit = mask_line(line, dia, in_block, keep_strings=True)
                if len(_MASK_CACHE) > 200_000:
                    _MASK_CACHE.clear()
                _MASK_CACHE[mk] = hit
            masked, in_block = hit
            if not masked.strip():
                continue
            if dia == "nasm" and masked.lstrip().startswith("[") and masked.rstrip().endswith("]") and \
                    re.match(r"\s*\[\s*(bits|section|segment|global|extern|default|cpu|org)\b", masked, re.I):
                k = masked.index("[")
                e = masked.rindex("]")
                masked = masked[:k] + " " + masked[k + 1:e] + " " + masked[e + 1:]
            sp = split_line(masked, dia)
            w = sp.word
            # ------------------------------------------------ macro bodies / structures are skipped
            if macro_depth:
                if self._macro_end(w, sp, masked):
                    macro_depth -= 1
                elif self._macro_start(w, sp, masked):
                    macro_depth += 1
                if sp.labels and not sp.labels[0][0].startswith("%%"):
                    self.macro_defined_labels = True
                continue
            if self._macro_start(w, sp, masked):
                macro_depth += 1
                nm = sp.name or (sp.rest.strip().split()[0] if sp.rest.strip() else "")
                if nm:
                    self.macros.add(self.key(nm.strip("{").split(",")[0]))
                if dia == "fasm" and "}" in masked[masked.find("{") + 1:] and "{" in masked:
                    macro_depth -= 1          # one-line FASM macro
                continue
            if struct_depth:
                if self._struct_end(w, sp):
                    struct_depth -= 1
                continue
            if self._struct_start(w, sp, masked):
                struct_depth += 1
                snm = sp.name or (sp.rest.strip().split()[0] if sp.rest.strip() else "")
                if snm:
                    self.struct_names.add(snm.lower().strip("{"))
                if dia == "fasm" and "}" in masked:
                    struct_depth -= 1
                continue
            # ------------------------------------------------ conditional assembly
            cw = w.lstrip("%.")
            if (dia == "nasm" and w.startswith("%") or dia == "gas" and w.startswith(".") or
                    dia in ("masm", "fasm") and not w.startswith((".", "%"))) and \
                    cw in ("if", "ifdef", "ifndef", "ifidn", "ifidni", "ifb", "ifnb", "ifmacro", "ifnum", "ifstr",
                           "ifctx", "ifempty", "ifnempty", "ifdif", "ife", "if1", "if2", "ifc", "ifnc", "ifeq",
                           "ifne", "ifgt", "ifge", "iflt", "ifle", "ifnotdef") and not sp.labels:
                cond += 1
                continue
            if cw in ("endif",) and (dia != "nasm" or w.startswith("%")) or \
                    (dia == "fasm" and w == "end" and sp.rest.strip().lower().startswith("if")):
                cond = max(0, cond - 1)
                continue
            if cw in ("else", "elif", "elseif", "elifdef", "elifndef", "elseifdef", "elseifndef") and not sp.labels \
                    and (dia != "nasm" or w.startswith("%")):
                continue
            if dia == "nasm" and w.startswith("%"):
                self._nasm_pre(w, sp, i)
                continue
            st = Stmt(i, "label", labels=list(sp.labels), raw=sp.raw, mnem=w, mcol=sp.wcol,
                      mend=sp.wcol + len(sp.raw), optext=sp.rest, opcol=sp.rcol, cond=cond, name=sp.name,
                      indent=sp.indent, end_col=sp.end)
            # ------------------------------------------------ sections / procs / declarations
            kind = self._section_change(w, sp, masked, line)
            if kind is not None:
                section, skind = kind
                st.kind = "directive"
            elif dia == "masm" and w == "proc" and sp.name:
                proc = ProcDef(sp.name, i, len(self.lines) - 1, *self._masm_proc_header(sp.rest))
                self.procs.append(proc)
                st.kind = "directive"
                last_global = sp.name
                for pn, pt in re.findall(r"(\w+)\s*:\s*(\w+)", sp.rest):
                    if pn.lower() != "uses":
                        self._add_label(pn, i, sp.rcol, "data", "", "", "stack", cond, proc,
                                        SIZE_WORDS.get(pt.lower(), 0) or (self.bits if pt.lower().startswith(
                                            ("ptr", "lp", "h")) else 0), "param", local=True)
            elif dia == "masm" and w == "local" and proc is not None:
                for item in sp.rest.split(","):
                    mm = re.match(r"\s*(\w+)\s*(\[[^\]]*\])?\s*(?::\s*(\w+))?", item)
                    if mm:
                        typ = (mm.group(3) or "").lower()
                        self._add_label(mm.group(1), i, sp.rcol, "data", "", "", "stack", cond, proc,
                                        SIZE_WORDS.get(typ, 0), "local", local=True)
                st.kind = "directive"
            elif dia == "masm" and w == "endp":
                if proc is not None:
                    proc.end = i
                proc = None
                st.kind = "directive"
            elif dia == "fasm" and w == "proc":
                parts = sp.rest.strip()
                m = _ID.match(parts)
                if m:
                    proc = ProcDef(m.group(), i, len(self.lines) - 1, *self._fasm_proc_header(parts[m.end():]),
                                   kind="fasm")
                    self.procs.append(proc)
                    last_global = m.group()
                st.kind = "directive"
                st.name = m.group() if m else ""
            elif dia == "fasm" and w == "endp":
                if proc is not None:
                    proc.end = i
                proc = None
                st.kind = "directive"
            elif w in ("extern", "extrn", "externdef", ".extern", "global", ".globl", ".global", "public",
                       "import", "export"):
                self._declare(w, sp, i)
                st.kind = "directive"
            elif w in ("include", ".include", "%include") or (dia == "gas" and w == "#include"):
                mm = re.search(r"['\"<]?([^'\"<>\s]+)['\">]?", sp.rest)
                if mm:
                    self.includes.append((mm.group(1), i))
                st.kind = "directive"
            elif w == "entry" and dia == "fasm":
                mm = _ID.match(sp.rest.strip())
                if mm:
                    self.entry = mm.group()
                st.kind = "directive"
            elif w == "end" and dia == "masm":
                mm = _ID.match(sp.rest.strip())
                if mm:
                    self.entry = mm.group()
                st.kind = "directive"
            elif w in ("equ", "=", "textequ", ".equ", ".set", ".equiv", "define") and (sp.name or w.startswith(".")
                                                                                     or sp.labels or w == "define"):
                nm, val = sp.name, sp.rest
                if not nm and sp.labels:
                    nm = sp.labels[-1][0]
                    st.labels = st.labels[:-1]
                if w.startswith(".") or w == "define":
                    parts = [p.strip() for p in re.split(r"[,\s]", sp.rest.strip(), 1)] if w == "define" else \
                        [p.strip() for p in sp.rest.split(",", 1)]
                    nm, val = (parts + ["", ""])[:2]
                if nm:
                    self.consts[self.key(nm)] = val.strip()
                    self._add_label(nm, i, sp.wcol, "const", last_global, section, skind, cond, proc)
                st.kind = "directive"
            elif dia == "masm" and not sp.name and w not in self.struct_names and                     sp.rest.strip().split()[:1] and sp.rest.strip().split()[0].lower() in self.struct_names:
                st.kind = "data"                          # alice student <...>
                st.name = sp.raw
                self._add_label(sp.raw, i, sp.wcol, "data", last_global, section, skind, cond, proc, 0, "struct")
            elif w in self.struct_names and dia in ("masm", "fasm"):
                st.kind = "data"                          # student <...> (continuation of an array)
            elif w in DATA_SIZES or (w == "times") or (sp.name and self.dialect == "masm" and
                                                       w not in NAME_FIRST_WORDS and not isa.INSTRUCTIONS.get(w)
                                                       and w not in DIRECTIVES and _looks_struct_init(sp.rest)):
                st.kind = "data"
                dword = w
                if w == "times":
                    mm = re.match(r"\s*\S+\s+([.\w]+)", sp.rest)
                    dword = mm.group(1).lower() if mm else ""
                    if dword not in DATA_SIZES:
                        st.kind = "directive"          # times 10 nop
                st.mnem = dword
                nm = sp.name or (sp.labels[-1][0] if sp.labels else "")
                if sp.name:
                    self._add_label(sp.name, i, len(sp.indent), "data", last_global, section, skind, cond,
                                    proc, DATA_SIZES.get(dword, 0), dword)
                    if not sp.name.startswith("."):
                        last_global = sp.name if self.dialect != "masm" or proc is None else last_global
                elif sp.labels:
                    for lb, lc in sp.labels[:-1]:
                        last_global = self._code_label(lb, lc, i, last_global, section, skind, cond, proc)
                    lb, lc = sp.labels[-1]
                    self._add_label(lb, i, lc, "data", last_global, section, skind, cond, proc,
                                    DATA_SIZES.get(dword, 0), dword)
                    if not lb.startswith("."):
                        last_global = lb
                del nm
            elif w in ("label",) and sp.name:
                mm = re.match(r"\s*(\w+)", sp.rest)
                size = SIZE_WORDS.get(mm.group(1).lower(), 0) if mm else 0
                self._add_label(sp.name, i, sp.wcol, "data" if size else "code", last_global, section, skind, cond,
                                proc, size, "label")
                st.kind = "directive"
            elif w == "label" and dia == "fasm":
                mm = re.match(r"\s*(" + ID_RE + r")(?:\s*:\s*(\w+)|\s+(\w+))?", sp.rest)
                if mm:
                    size = SIZE_WORDS.get((mm.group(2) or mm.group(3) or "").lower(), 0)
                    self._add_label(mm.group(1), i, sp.rcol, "data" if size else "code", last_global, section,
                                    skind, cond, proc, size, "label")
                st.kind = "directive"
            elif w in (".startup",):
                st.kind = "directive"
            elif w in (".exit",):
                st.kind = "macro"
            elif not w:
                st.kind = "label"
            else:
                st.kind = self._instr_kind(w)
                if st.kind == "instr":
                    st.prefixes, st.mnem, st.raw, st.mcol, st.mend, st.optext, st.opcol, st.suffix = \
                        self._mnemonic(sp)
                    if not st.mnem:
                        st.kind = "macro"
                        st.mnem = w
            # ------------------------------------------------ labels of the line
            if st.kind != "data" or (sp.name and sp.labels):
                for lb, lc in (st.labels if st.kind != "data" else sp.labels):
                    last_global = self._code_label(lb, lc, i, last_global, section, skind, cond, proc)
            if st.kind in ("directive",) and w in ("proc",) and dia == "masm":
                self._add_label(sp.name, i, len(sp.indent), "proc", "", section, skind, cond, None)
            if st.kind == "directive" and dia == "fasm" and w == "proc" and st.name:
                self._add_label(st.name, i, sp.rcol, "proc", "", section, skind, cond, None)
            if st.kind == "label" and not st.labels and st.name:
                st.kind = "directive"
            st.section, st.skind, st.proc = section, skind, (proc.name if proc else "")
            if st.kind == "instr" and proc is not None and dia == "masm" and w == "endp":
                st.kind = "directive"
            self.stmts.append(st)

    def _macro_start(self, w: str, sp: _Split, masked: str) -> bool:
        dia = self.dialect
        if dia == "nasm":
            return w in ("%macro", "%imacro", "%rep")
        if dia == "masm":
            return (w == "macro" and bool(sp.name)) or w in ("rept", "repeat", "irp", "irpc", "for", "forc",
                                                             "while") and not sp.labels
        if dia == "fasm":
            return w in ("macro", "rept", "irp", "irps", "irpv", "repeat", "while", "match", "postpone",
                         "virtual") and not sp.name
        return w in (".macro", ".rept", ".irp", ".irpc")

    def _macro_end(self, w: str, sp: _Split, masked: str) -> bool:
        dia = self.dialect
        if dia == "nasm":
            return w in ("%endmacro", "%endm", "%endrep")
        if dia == "masm":
            return w in ("endm",)
        if dia == "fasm":
            return masked.strip().startswith("}") or (w == "end" and sp.rest.strip().lower().split()[:1] in
                                                       (["repeat"], ["while"], ["virtual"]))
        return w in (".endm", ".endr")

    def _struct_start(self, w: str, sp: _Split, masked: str) -> bool:
        dia = self.dialect
        if dia == "nasm":
            return w == "struc"
        if dia == "masm":
            return w in ("struct", "struc", "union", "record") and bool(sp.name)
        if dia == "fasm":
            return w in ("struct", "struc", "union")
        return w in (".struct",)

    def _struct_end(self, w: str, sp: _Split) -> bool:
        dia = self.dialect
        if dia == "nasm":
            return w == "endstruc"
        if dia == "masm":
            return w == "ends"
        if dia == "fasm":
            return w == "ends" or sp.word == "" and False
        return w in (".ends", ".endstruct", ".text", ".data")

    def _nasm_pre(self, w: str, sp: _Split, i: int) -> None:
        if w in ("%define", "%xdefine", "%idefine", "%assign", "%iassign", "%xidefine"):
            mm = re.match(r"\s*(" + ID_RE + r")(\([^)]*\))?\s*(.*)", sp.rest)
            if mm and not mm.group(2):
                self.consts[self.key(mm.group(1))] = mm.group(3).strip()
                self._add_label(mm.group(1), i, sp.rcol, "const", "", "", "", 0, None)
        elif w == "%include":
            mm = re.search(r"['\"<]([^'\"<>]+)['\">]", sp.rest)
            if mm:
                self.includes.append((mm.group(1), i))

    def _section_change(self, w: str, sp: _Split, masked: str, line: str):
        dia = self.dialect
        rest = sp.rest.strip()
        low = rest.lower()
        if dia == "nasm" and w in ("section", "segment", "[section", "[segment"):
            nm = rest.split()[0].strip("]") if rest else ""
            return nm, _skind(nm, low)
        if dia == "gas":
            if w in (".text", ".data", ".bss", ".rodata"):
                return w, _skind(w, "")
            if w == ".section":
                nm = rest.split(",")[0].strip()
                flags = rest[len(nm):]
                return nm, _skind(nm, flags.lower())
        if dia == "masm":
            if w in (".code", ".data", ".data?", ".const", ".stack", ".fardata", ".fardata?"):
                return w, {".code": "code", ".data": "data", ".data?": "bss", ".const": "rodata",
                           ".stack": "bss", ".fardata": "data", ".fardata?": "bss"}[w]
            if w == "segment" and sp.name:
                return sp.name, _skind(sp.name, low)
            if w == "ends" and sp.name:
                return "", ""
        if dia == "fasm":
            if w == "section":
                mm = re.match(r"['\"]([^'\"]*)['\"](.*)", rest)
                nm = mm.group(1) if mm else rest
                flags = (mm.group(2) if mm else "").lower()
                if "code" in flags or "executable" in flags:
                    k = "code"
                elif "writeable" in flags or "writable" in flags:
                    k = "data"
                elif "data" in flags or "readable" in flags:
                    k = "rodata" if "import" not in flags and "resource" not in flags else "data"
                else:
                    k = _skind(nm, flags)
                return nm, k
            if w == "segment":
                return rest.split()[0] if rest else "segment", "any"
        return None

    def _masm_proc_header(self, rest: str):
        uses = ()
        mm = re.search(r"\buses\s+([\w\s]+?)(?:,|$)", rest, re.I)
        if mm:
            uses = tuple(x.lower() for x in mm.group(1).split() if x.lower() in GP)
        params = tuple(re.findall(r"(\w+)\s*:\s*\w+", rest))
        return uses, params

    def _fasm_proc_header(self, rest: str):
        uses = ()
        mm = re.search(r"\buses\s+([\w\s]+?)(?:,|$)", rest, re.I)
        if mm:
            uses = tuple(x.lower() for x in mm.group(1).split() if x.lower() in GP)
        params = tuple(p.strip().split(":")[0] for p in rest.split(",") if p.strip() and "uses" not in p.lower())
        return uses, params

    def _declare(self, w: str, sp: _Split, i: int) -> None:
        rest = sp.rest
        if w == "import" and self.dialect == "fasm":
            for nm in re.findall(r"(" + ID_RE + r")\s*,\s*['\"]", rest):
                self.externs[nm] = i
                self._add_label(nm, i, sp.rcol, "extern", "", "", "", 0, None)
            return
        for item in rest.split(","):
            nm = item.strip().split(":")[0].split()[0] if item.strip() else ""
            if not nm or not re.match(ID_RE + "$", nm):
                continue
            if w in ("extern", "extrn", "externdef", ".extern"):
                self.externs[nm] = i
                self._add_label(nm, i, sp.rcol, "extern", "", "", "", 0, None)
            elif w != "export":
                self.globals[nm] = i

    def _instr_kind(self, w: str) -> str:
        if w in INVOKE_WORDS:
            return "macro"
        if w in PREFIXES or w in EXTRA_MNEMONICS:
            return "instr"
        if self.att:
            if isa.instruction(w, att=True) is not None or w in ("movabs", "movabsq"):
                return "instr"
        elif isa.INSTRUCTIONS.get(w) is not None:
            return "instr"
        if w.startswith((".", "%", "#")) or w in DIRECTIVES:
            return "directive"
        return "macro"

    def _mnemonic(self, sp: _Split):
        """(prefixes, base mnemonic, raw, col, end, operand text, operand col, AT&T suffix bits)."""
        prefixes = []
        word, raw, col = sp.word, sp.raw, sp.wcol
        rest, rcol = sp.rest, sp.rcol
        while word in PREFIXES:
            prefixes.append(word)
            m = _WORD.match(rest)
            if not m:
                return prefixes, word, raw, col, col + len(raw), "", rcol, 0
            raw = m.group(1)
            word = raw.lower()
            col = rcol + m.start(1)
            rcol = rcol + m.end()
            rest = rest[m.end():]
        suffix = 0
        base = word
        if self.att:
            if word in ("movabs", "movabsq"):
                base, suffix = "mov", 64
            elif word in ("jmpq", "callq", "retq", "retl", "jmpl", "calll"):
                base = word[:-1]
            else:
                b = isa.att_base(word)
                if b:
                    if b != word and word.startswith(b) and len(word) == len(b) + 1 and word[-1] in "bwlq":
                        suffix = {"b": 8, "w": 16, "l": 32, "q": 64}[word[-1]]
                    elif b in ("movzx", "movsx") and len(word) == 6:
                        suffix = {"b": 8, "w": 16, "l": 32, "q": 64}.get(word[-1], 0)
                    base = b
                elif word in EXTRA_MNEMONICS:
                    base = word
                else:
                    base = ""
        else:
            if word not in isa.INSTRUCTIONS and word not in EXTRA_MNEMONICS:
                base = ""
        return prefixes, base, raw, col, col + len(raw), rest, rcol, suffix

    # ------------------------------------------------------------ labels
    def _scope_key(self, name: str, last_global: str, proc: ProcDef | None) -> str:
        if name.startswith(".") and not name.startswith("..") and self.dialect in ("nasm", "fasm") and \
                not name.startswith(".L"):
            return self.key(last_global + name)
        return self.key(name)

    def _add_label(self, name, line, col, kind, last_global, section, skind, cond, proc, size=0, directive="",
                   local=False):
        if not name:
            return
        if self.dialect == "masm" and proc is not None and (kind == "code" or local) and not name.endswith("::"):
            key = self.key(proc.name + "::" + name)
        else:
            key = self._scope_key(name, last_global, proc)
        d = LabelDef(name, key, line, col, kind, size, section, skind, directive, proc.name if proc else "",
                     bool(cond))
        old = self.labels.get(key)
        if old is not None:
            if old.kind == "extern" and kind != "extern":
                self.labels[key] = d
                return
            if kind == "extern" or (old.kind == "proc" and old.line == line):
                return
            if old.kind == "const" and kind == "const" and self.dialect == "nasm":
                return                      # %assign i i+1 / %define redefinitions are normal
            self.dups.append((old, d))
            return
        self.labels[key] = d

    def _code_label(self, lb, lc, i, last_global, section, skind, cond, proc) -> str:
        if lb == "@@":
            self.anon.append(i)
            return last_global
        if self.dialect == "gas" and lb.isdigit():
            self.num_labels.setdefault(lb, []).append(i)
            return last_global
        kind = "data" if skind in ("data", "rodata", "bss") else "code"
        self._add_label(lb, i, lc, kind, last_global, section, skind, cond, proc)
        if lb.startswith(".") and self.dialect in ("nasm", "fasm") and not lb.startswith(".."):
            return last_global
        if self.dialect == "gas" and lb.startswith((".L", "L.")):
            return last_global
        if self.dialect == "masm" and proc is not None:
            return last_global
        return lb

    # ------------------------------------------------------------ lookups
    def resolve(self, name: str, line: int, scope: str = "", proc: str = "") -> LabelDef | None:
        """The definition *name* refers to at *line* (local labels, MASM proc scopes)."""
        if not name:
            return None
        if self.dialect == "masm" and proc:
            d = self.labels.get(self.key(proc + "::" + name))
            if d is not None:
                return d
        if name.startswith(".") and not name.startswith("..") and self.dialect in ("nasm", "fasm"):
            d = self.labels.get(self.key(scope + name))
            if d is not None:
                return d
        return self.labels.get(self.key(name))

    def const_value(self, name: str, depth: int = 0) -> int | None:
        expr = self.consts.get(self.key(name))
        if expr is None or depth > 8:
            return None
        return evaluate(expr, lambda n: self.const_value(n, depth + 1))

    # ------------------------------------------------------------ pass 2: operands
    def symbol_signature(self) -> int:
        """Changes when a label / constant that operand typing depends on changes (cache key)."""
        return hash((self.dialect, self.att, self.bits, self.default_rel,
                     tuple((k, v.kind, v.size, v.line if self.mem_symbols else 0) for k, v in self.labels.items()),
                     tuple(self.consts.items())))

    def _classify(self) -> None:
        sig = self.symbol_signature()
        scope = ""
        for st in self.stmts:
            for lb, _c in st.labels:
                if not (lb.startswith(".") and self.dialect in ("nasm", "fasm")) and lb != "@@" and \
                        not (self.dialect == "masm" and st.proc) and not lb.isdigit():
                    scope = lb
            if st.kind == "data" and st.name and not st.name.startswith("."):
                scope = st.name if not (self.dialect == "masm" and st.proc) else scope
            st_scope = scope
            st.scope = scope
            if st.kind != "instr":
                st.att_src_first = False
                continue
            text = st.optext
            if not text.strip():
                st.ops = []
                continue
            ck = (sig, st.mnem, st.raw, st.suffix, st.opcol, text, st_scope, st.proc, st.line if self.mem_symbols
                  else -1)
            hit = _OPS_CACHE.get(ck)
            if hit is not None:
                st.ops, st.att_src_first = list(hit[0]), hit[1]
                continue
            parts = _split_ops(text, st.opcol)
            if self.dialect == "fasm" and st.mnem in ("push", "pop") and len(parts) == 1 and " " in parts[0][0]:
                toks = parts[0][0].split()
                if all(t.lower() in GP or t.lower() in SEGS for t in toks):
                    c = parts[0][1]
                    parts = []
                    for t in toks:
                        j = text.find(t, c - st.opcol)
                        parts.append((t, st.opcol + j))
            ops = [self.operand(t, c, st, st_scope) for t, c in parts]
            if self.att and len(ops) >= 2:
                ops.reverse()
                st.att_src_first = True
            st.ops = ops
            if self.att and st.suffix:
                for o in ops:
                    if o.kind == "mem" and not o.size:
                        o.size = st.suffix
                        o.explicit = True
                if st.mnem in ("movzx", "movsx") and len(st.raw) == 6 and ops and ops[-1:] and len(ops) == 2:
                    src = {"b": 8, "w": 16, "l": 32}.get(st.raw.lower()[4], 0)
                    if ops[1].kind == "mem" and src:
                        ops[1].size = src
                        ops[1].explicit = True
            if len(_OPS_CACHE) > 200_000:
                _OPS_CACHE.clear()
            _OPS_CACHE[ck] = (tuple(ops), st.att_src_first)

    def operand(self, t: str, col: int, st: Stmt, scope: str) -> Operand:
        o = Operand(t, col, col + len(t))
        if self.att:
            self._att_operand(o, st, scope)
        else:
            self._intel_operand(o, st, scope)
        return o

    # Intel syntax: NASM / MASM / FASM / GAS .intel_syntax
    def _intel_operand(self, o: Operand, st: Stmt, scope: str) -> None:
        s = o.text
        low = s.lower()
        # size keywords (dword ptr / qword / short ...)
        pos = 0
        while True:
            m = re.match(r"\s*([a-z0-9]+)\b(\s+ptr\b)?", low[pos:])
            if not m:
                break
            wd = m.group(1)
            if wd in SIZE_WORDS and (m.group(2) or self.dialect in ("nasm", "fasm") or wd in ("short", "near",
                                                                                              "far")):
                if wd in ("short", "near", "far"):
                    o.jump_kind = wd
                else:
                    o.size = SIZE_WORDS[wd]
                    o.explicit = True
                pos += m.end()
                continue
            if wd in ("strict", "rel", "abs") and self.dialect == "nasm" and not low[pos:].lstrip().startswith("["):
                pos += m.end()
                continue
            break
        body = s[pos:].strip()
        blow = body.lower()
        if self.dialect == "gas":
            body = body.replace("%", "")
            blow = body.lower()
        if not body:
            return
        # segment override written outside the brackets: es:[di] / es:var / fs:0
        m = re.match(r"(cs|ds|es|ss|fs|gs)\s*:\s*(.*)$", blow)
        if m:
            o.seg = m.group(1)
            rest = body[m.start(2):]
            if rest.strip().lower() in GP:
                o.kind = "reg"
                o.reg = rest.strip().lower()
                o.size = GP[o.reg][1]
                o.bad = "override-on-register"
                return
            body = rest
            blow = body.lower()
        if blow in GP:
            o.kind, o.reg, o.size = "reg", blow, GP[blow][1]
            return
        if blow in SEGS:
            o.kind, o.reg, o.size = "sreg", blow, 16
            return
        if blow.startswith(("st(", "st", "xmm", "ymm", "zmm", "mm", "k", "cr", "dr")) and isa.register(blow):
            r = isa.register(blow)
            o.kind, o.reg, o.size = "vreg", blow, r.size if r else 0
            return
        if "[" in body:
            o.kind = "mem"
            o.size_col = o.col if not o.explicit else -1
            self._address(o, body, st, scope)
            return
        if blow.startswith(("offset ", "addr ", "seg ")) or blow.startswith("offset("):
            o.kind = "imm"
            o.addr = True
            o.syms = tuple(x for x in _ids(body[6:] if blow.startswith("offset") else body[4:])
                           if x.lower() not in GP)
            return
        if body[:1] in "'\"`" and body[-1:] == body[:1]:
            o.kind = "imm"
            o.value = char_value(body)
            if o.value is None:
                o.kind = "str"
            return
        ids = [x for x in _ids(body) if x.lower() not in _WORD_OPS and x.lower() not in ("ptr", "type", "sizeof",
                                                                                          "lengthof", "length",
                                                                                          "size", "low", "high",
                                                                                          "dup", "this")]
        o.syms = tuple(ids)
        # MASM-like assemblers: a data variable name is a memory operand (mov ax, var / mov al, arr+2)
        if self.mem_symbols and ids:
            d = self.resolve(ids[0], st.line, scope, st.proc)
            if d is not None and d.kind == "data":
                o.kind = "mem"
                o.base = ""
                o.size_col = o.col if not o.explicit else -1
                if not o.explicit and self.dialect == "masm":
                    o.size = d.size if d.size in (8, 16, 32, 64, 80, 128) else 0
                return
        val = evaluate(body, lambda n: self.const_value(n))
        o.neg = body.lstrip().startswith("-")
        if val is not None:
            o.kind, o.value = "imm", val
            return
        if ids:
            first = ids[0]
            d = self.resolve(first, st.line, scope, st.proc)
            if d is not None and d.kind == "const":
                o.kind = "imm"
                return
            if st.mnem in BRANCHES and len(ids) == 1 and re.match(r"^[\w.?@$#~]+$", body.strip()):
                o.kind = "sym"
                return
            o.kind = "imm"
            o.addr = d is not None and d.kind in ("data", "code", "proc", "extern")
            return
        o.kind = "imm"

    def _address(self, o: Operand, body: str, st: Stmt, scope: str) -> None:
        # MASM: arr[bx][si] / [bx+si+arr] / es:[di]; NASM: [es:di] / [rel x] / [dword x]
        inner = "+".join(re.findall(r"\[([^\]]*)\]", body))
        outer = re.sub(r"\[[^\]]*\]", " ", body).strip()
        if outer:
            mo = re.match(r"(cs|ds|es|ss|fs|gs)\s*:\s*(.*)$", outer, re.I)
            if mo:
                o.seg = mo.group(1).lower()
                outer = mo.group(2).strip()
        if outer:
            inner = outer + ("+" + inner if inner else "")
        txt = inner
        m = re.match(r"\s*(cs|ds|es|ss|fs|gs)\s*:\s*(.*)$", txt, re.I)
        if m:
            o.seg = m.group(1).lower()
            txt = m.group(2)
        txt2 = txt
        mm = re.match(r"\s*(byte|word|dword|qword|tword|oword|yword)\b\s*(.*)$", txt2, re.I)
        if mm and not o.explicit:
            o.size = SIZE_WORDS[mm.group(1).lower()]
            o.explicit = True
            txt2 = mm.group(2)
        mr = re.match(r"\s*(rel|abs)\b\s*(.*)$", txt2, re.I)
        if mr:
            o.rel = mr.group(1).lower() == "rel"
            txt2 = mr.group(2)
        # terms split on + / - at the top level
        terms = re.findall(r"([+-]?)\s*([^+-]+)", txt2.replace(" ", ""))
        regs = []
        syms = []
        for sign, term in terms:
            tl = term.lower()
            mul = re.match(r"^([a-z0-9]+)\*(\w+)$|^(\w+)\*([a-z0-9]+)$", tl)
            if mul:
                a, b = (mul.group(1), mul.group(2)) if mul.group(1) else (mul.group(3), mul.group(4))
                if a in GP or b in GP:
                    reg, sc = (a, b) if a in GP else (b, a)
                    scv = evaluate(sc, lambda n: self.const_value(n))
                    regs.append((reg, scv if scv is not None else -1, sign))
                    continue
            if tl in GP:
                regs.append((tl, 1, sign))
                continue
            if tl in SEGS:
                o.bad = "segment-register-in-address"
                continue
            if tl == "rip":
                o.rel = True
                continue
            for x in _ids(term):
                if x.lower() not in _WORD_OPS and x.lower() not in SIZE_WORDS and x.lower() not in ("ptr", "rel",
                                                                                                     "abs"):
                    syms.append(x)
        o.syms = tuple(syms)
        o.regs = tuple(r for r, _s, _g in regs)
        base = index = ""
        scale = 1
        for reg, sc, sign in regs:
            if sign == "-":
                o.bad = o.bad or "negative-register"
            if sc == 1 and not base:
                base = reg
            elif not index:
                index, scale = reg, sc
            else:
                o.bad = o.bad or "too-many-registers"
        o.base, o.index, o.scale = base, index, scale
        # size from the variable (MASM / FASM / GAS intel): arr[bx] / [arr+si]
        if not o.explicit and syms and self.dialect in ("masm", "fasm"):
            d = self.resolve(syms[0], st.line, scope, st.proc)
            if d is not None and d.kind == "data" and d.size in (8, 16, 32, 64, 80, 128):
                o.size = d.size

    # AT&T syntax
    def _att_operand(self, o: Operand, st: Stmt, scope: str) -> None:
        s = o.text.strip()
        if s.startswith("*"):
            o.indirect = True
            s = s[1:].strip()
        low = s.lower()
        if low.startswith("%") and low[1:] in GP:
            o.kind, o.reg, o.size = "reg", low[1:], GP[low[1:]][1]
            return
        if low.startswith("%") and low[1:] in SEGS:
            o.kind, o.reg, o.size = "sreg", low[1:], 16
            return
        if low.startswith("%"):
            r = isa.register(low)
            o.kind, o.reg, o.size = "vreg", low[1:], r.size if r else 0
            return
        if low.startswith("$"):
            body = s[1:]
            o.kind = "imm"
            o.neg = body.lstrip().startswith("-")
            o.value = evaluate(body, lambda n: self.const_value(n))
            o.syms = tuple(_ids(body))
            if o.value is None and o.syms:
                d = self.resolve(o.syms[0], st.line, scope)
                o.addr = d is None or d.kind != "const"
            return
        m = re.match(r"^(?:%?(cs|ds|es|ss|fs|gs)\s*:)?\s*([^()]*)\s*(?:\(([^)]*)\))?\s*$", s, re.I)
        if not m:
            o.kind = "other"
            return
        o.seg = (m.group(1) or "").lower()
        disp = m.group(2) or ""
        inner = m.group(3)
        if inner is None and st.mnem in BRANCHES and not o.indirect and not o.seg:
            o.kind = "sym"
            o.syms = tuple(_ids(disp))
            v = evaluate(disp) if not o.syms else None
            if v is not None:
                o.kind, o.value = "imm", v
            return
        o.kind = "mem"
        o.size_col = st.mend
        o.syms = tuple(_ids(disp))
        if inner is not None:
            parts = [p.strip().lower().lstrip("%") for p in inner.split(",")]
            regs = []
            if parts and parts[0]:
                if parts[0] == "rip":
                    o.rel = True
                elif parts[0] in GP:
                    o.base = parts[0]
                    regs.append(parts[0])
            if len(parts) > 1 and parts[1]:
                if parts[1] in GP:
                    o.index = parts[1]
                    regs.append(parts[1])
            if len(parts) > 2 and parts[2]:
                sc = evaluate(parts[2])
                o.scale = sc if sc is not None else -1
            o.regs = tuple(regs)


BRANCHES = {"jmp", "call", "loop", "loope", "loopne", "loopz", "loopnz", "jcxz", "jecxz", "jrcxz"} | \
    {"j" + c for c in ("o", "no", "b", "c", "nae", "ae", "nb", "nc", "e", "z", "ne", "nz", "be", "na", "a", "nbe",
                       "s", "ns", "p", "pe", "np", "po", "l", "nge", "ge", "nl", "le", "ng", "g", "nle")}
JCC = BRANCHES - {"jmp", "call", "loop", "loope", "loopne", "loopz", "loopnz", "jcxz", "jecxz", "jrcxz"}


def _ids(text: str) -> list[str]:
    out = []
    for m in re.finditer(r"(?<![\w.?@$#'\"])(" + ID_RE + r")", text):
        w = m.group(1)
        if w[0] in "$" and len(w) > 1 and w[1:].isdigit():
            continue
        if re.match(r"^[0-9]", w):
            continue
        if w in ("$", "$$", "@f", "@b", "@F", "@B", "@r", "@R"):
            continue
        out.append(w)
    return out


def _masm16_style(text: str, path) -> bool:
    if path and Path(str(path)).suffix.lower() == ".nasm":
        return False
    low = text[:40000].lower()
    if not re.search(r"\bint\s+(21h|10h|16h|20h)\b|^\s*org\s+100h|#make_", low, re.M):
        return False
    if re.search(r"^\s*(bits\s+16|section\s+\.|\[bits|%define|%include|%macro)", low, re.M):
        return False
    return bool(re.search(r"\boffset\s+\w|\bptr\b|^\s*\w+\s+(proc|endp)\b|@data\b|"
                          r"^\s*lea\s+\w+\s*,\s*[a-z_]\w*\s*(;|$)|^\s*\.model\b", low, re.M))


def _skind(name: str, flags: str) -> str:
    n = name.lower().strip("'\"")
    f = flags.lower()
    if "bss" in n or "nobits" in f or n.endswith("?"):
        return "bss"
    if any(x in n for x in ("rodata", "rdata", "const", "rodata.")):
        return "rodata"
    if "text" in n or "code" in n or "exec" in f or "code" in f or re.search(r'"[a-z]*x[a-z]*"', f):
        return "code"
    if "data" in n or "write" in f or re.search(r'"[a-z]*w[a-z]*"', f):
        return "data"
    if "stack" in n:
        return "bss"
    return "any"


def _looks_struct_init(rest: str) -> bool:
    r = rest.strip()
    return r.startswith(("<", "{")) or r == "?"


def comment_text(line: str, dialect: str) -> str:
    return comment_of(line, dialect)
