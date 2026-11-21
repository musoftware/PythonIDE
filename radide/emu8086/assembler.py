"""A multi-pass assembler for 16-bit 8086 programs written in the MASM / TASM / emu8086 dialect that
university courses use.

    prog = assemble(source_text, "main.asm")
    if prog.errors: ...            # Diagnostic(severity, file, line, code, args)
    prog.chunks                    # [(linear address, bytes)] to copy into the emulator's memory
    prog.addr_line                 # linear address of each instruction -> (file, line)

Supported: ``.model tiny/small/...``, ``.stack``, ``.data``, ``.code``, ``.startup``, ``.exit``, full segment
definitions (``name segment`` / ``ends`` / ``assume``), ``org``, ``even``, ``align``, ``db dw dd dq`` (+ ``byte
word dword`` aliases) with strings, ``?`` and nested ``dup``, ``equ`` / ``=`` (numeric and text equates),
``label``, ``proc`` / ``endp`` (near / far), ``macro`` / ``endm`` with ``local``, ``rept``, ``include``,
``struc`` / ``ends`` (fields, ``var Name <...>`` / ``N dup (<...>)`` instances, ``var.field``, ``[bx].field``,
``(Name ptr [bx]).field``, ``Name.field`` offsets, ``size`` / ``type`` of a structure), conditional assembly
(``if`` / ``ife`` / ``ifdef`` / ``ifndef`` / ``ifb`` / ``ifnb`` / ``ifidn[i]`` / ``ifdif[i]`` with ``elseif...`` /
``else`` / ``endif``), the emu8086 ``#make_com#`` / ``#make_exe#`` lines, the 8086 instruction set plus the 80186 extras (push imm,
pusha/popa, shifts by an immediate count, enter/leave). Expressions: numbers in decimal / hex (``0Ah``,
``0x0A``) / binary (``1010b``) / octal (``17o``), characters, ``$``, ``+ - * / mod shl shr and or xor not``,
``offset``, ``seg``, ``type``, ``length``, ``size``, ``low``, ``high``, ``byte/word/dword ptr``, ``short``,
``near ptr``, ``far ptr``, segment overrides and every 8086 addressing mode.

Programs are laid out the way DOS would load them at segment ``load_seg`` (default 0700h): a COM program
(``org 100h`` / ``.model tiny`` / ``#make_com#`` / no segment directives) is one 64 KB segment with the PSP
below 100h; an EXE program puts its PSP at ``load_seg`` and each segment (paragraph aligned) after it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .messages import text as _msg

REG8 = {"al": 0, "cl": 1, "dl": 2, "bl": 3, "ah": 4, "ch": 5, "dh": 6, "bh": 7}
REG16 = {"ax": 0, "cx": 1, "dx": 2, "bx": 3, "sp": 4, "bp": 5, "si": 6, "di": 7}
SREG = {"es": 0, "cs": 1, "ss": 2, "ds": 3}
SEG_PREFIX = {0: 0x26, 1: 0x2E, 2: 0x36, 3: 0x3E}
RM_TABLE = {frozenset(("bx", "si")): 0, frozenset(("bx", "di")): 1, frozenset(("bp", "si")): 2,
            frozenset(("bp", "di")): 3, frozenset(("si",)): 4, frozenset(("di",)): 5, frozenset(("bp",)): 6,
            frozenset(("bx",)): 7}

ALU = {"add": 0, "or": 1, "adc": 2, "sbb": 3, "and": 4, "sub": 5, "xor": 6, "cmp": 7}
SHIFT = {"rol": 0, "ror": 1, "rcl": 2, "rcr": 3, "shl": 4, "sal": 4, "shr": 5, "sar": 7}
UNARY = {"not": 2, "neg": 3, "mul": 4, "imul": 5, "div": 6, "idiv": 7}
SIMPLE = {"cbw": [0x98], "cwd": [0x99], "clc": [0xF8], "stc": [0xF9], "cli": [0xFA], "sti": [0xFB],
          "cld": [0xFC], "std": [0xFD], "cmc": [0xF5], "hlt": [0xF4], "nop": [0x90], "sahf": [0x9E],
          "lahf": [0x9F], "pushf": [0x9C], "popf": [0x9D], "aaa": [0x37], "aas": [0x3F], "daa": [0x27],
          "das": [0x2F], "xlat": [0xD7], "xlatb": [0xD7], "wait": [0x9B], "fwait": [0x9B], "into": [0xCE],
          "iret": [0xCF], "pusha": [0x60], "popa": [0x61], "leave": [0xC9],
          "movsb": [0xA4], "movsw": [0xA5], "cmpsb": [0xA6], "cmpsw": [0xA7], "stosb": [0xAA],
          "stosw": [0xAB], "lodsb": [0xAC], "lodsw": [0xAD], "scasb": [0xAE], "scasw": [0xAF],
          "insb": [0x6C], "insw": [0x6D], "outsb": [0x6E], "outsw": [0x6F]}
I186 = {"pusha", "popa", "leave", "enter", "insb", "insw", "outsb", "outsw"}
JCC = {"jo": 0x70, "jno": 0x71, "jb": 0x72, "jc": 0x72, "jnae": 0x72, "jnb": 0x73, "jae": 0x73, "jnc": 0x73,
       "je": 0x74, "jz": 0x74, "jne": 0x75, "jnz": 0x75, "jbe": 0x76, "jna": 0x76, "ja": 0x77, "jnbe": 0x77,
       "js": 0x78, "jns": 0x79, "jp": 0x7A, "jpe": 0x7A, "jnp": 0x7B, "jpo": 0x7B, "jl": 0x7C, "jnge": 0x7C,
       "jge": 0x7D, "jnl": 0x7D, "jle": 0x7E, "jng": 0x7E, "jg": 0x7F, "jnle": 0x7F}
LOOPS = {"loopne": 0xE0, "loopnz": 0xE0, "loope": 0xE1, "loopz": 0xE1, "loop": 0xE2, "jcxz": 0xE3}
PREFIXES = {"rep": 0xF3, "repe": 0xF3, "repz": 0xF3, "repne": 0xF2, "repnz": 0xF2, "lock": 0xF0}
DATA_DIRS = {"db": 1, "dw": 2, "dd": 4, "dq": 8, "byte": 1, "sbyte": 1, "word": 2, "sword": 2,
             "dword": 4, "sdword": 4, "qword": 8}
OTHER_INSTR = {"mov", "test", "xchg", "inc", "dec", "push", "pop", "lea", "lds", "les", "int", "in", "out",
               "jmp", "call", "ret", "retn", "retf", "aam", "aad", "enter", "movs", "cmps", "stos", "lods",
               "scas"}
MNEMONICS = (set(ALU) | set(SHIFT) | set(UNARY) | set(SIMPLE) | set(JCC) | set(LOOPS) | set(PREFIXES)
             | OTHER_INSTR)
IGNORED_DIRS = {"public", "extrn", "extern", "name", "title", "subttl", "page", "global", ".list", ".nolist",
                ".xlist", ".lall", ".sall", ".xall", ".listall", ".8086", ".8087", ".186", ".model", "jumps",
                "locals", "ideal", "masm", "option", ".radix", "comment"}
CPU_386 = {".286", ".286p", ".386", ".386p", ".486", ".486p", ".586", ".686", ".287", ".387", ".mmx", ".xmm",
           "p286", "p386", "p486"}
KEYWORDS_NOT_SYMBOLS = (set(REG8) | set(REG16) | set(SREG) | {"ptr", "offset", "seg", "short", "near", "far",
                        "byte", "word", "dword", "qword", "mod", "shl", "shr", "and", "or", "xor", "not", "dup",
                        "eq", "ne", "lt", "le", "gt", "ge"})
# operators that a program may also use as a variable name (size, length, count...)
SOFT_OPERATORS = {"type", "length", "size", "lengthof", "sizeof", "low", "high", "lowword", "highword"}


# ============================================================================ results
@dataclass
class Diagnostic:
    severity: str            # "Error" | "Warning"
    file: str
    line: int                # 1-based
    code: str
    args: dict = field(default_factory=dict)

    def text(self, lang: str = "en") -> str:
        return _msg(self.code, lang, **self.args)

    def __str__(self) -> str:
        return f"{Path(self.file).name}({self.line}): {self.severity.lower()}: {self.text()}"


@dataclass
class Symbol:
    name: str
    kind: str                # label | var | proc | const | segment | text
    section: "Section | None" = None
    offset: int = 0
    size: int = 0            # var: element size (1, 2, 4, 8); label/proc: 0 (near) / 0xFFFE (far)
    count: int = 1           # number of elements in the defining statement
    first_count: int = 1     # LENGTH (elements before the first comma)
    far: bool = False
    value: int = 0           # const
    reloc: bool = False      # const derived from labels
    known: bool = False
    defined_pass: int = -1
    file: str = ""
    line: int = 0
    text: str = ""           # const: the expression text (lazy evaluation of forward references)


@dataclass
class VarInfo:
    """A data label for the debugger's Variables view."""
    name: str
    segment: int
    offset: int
    size: int                # element size
    count: int               # elements
    file: str
    line: int

    @property
    def linear(self) -> int:
        return ((self.segment << 4) + self.offset) & 0xFFFFF


@dataclass
class Program:
    com: bool = True
    load_seg: int = 0x0700
    chunks: list = field(default_factory=list)          # [(linear, bytes)]
    entry_cs: int = 0
    entry_ip: int = 0x100
    ss: int = 0
    sp: int = 0xFFFE
    ds: int = 0
    es: int = 0
    addr_line: dict = field(default_factory=dict)       # linear -> (file, line)
    line_addrs: dict = field(default_factory=dict)      # (file lower, line) -> [linear]
    variables: list = field(default_factory=list)       # [VarInfo]
    labels: dict = field(default_factory=dict)          # name -> (segment, offset) of code labels / procs
    listing: list = field(default_factory=list)         # [(file, line, segment, offset, bytes, source)]
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    end_linear: int = 0                                  # first free paragraph after the program (linear)
    files: list = field(default_factory=list)           # source files used (main first)

    @property
    def ok(self) -> bool:
        return not self.errors

    def line_of(self, linear: int):
        return self.addr_line.get(linear)

    def addresses_of(self, file: str, line: int) -> list:
        return self.line_addrs.get((Path(file).name.lower(), line), [])


class AsmError(Exception):
    def __init__(self, code: str, **args):
        super().__init__(code)
        self.code = code
        self.args_ = args


# ============================================================================ source lines / tokens
@dataclass
class SrcLine:
    text: str
    file: str
    line: int


_TOK = re.compile(r"""\s*(?:
    (?P<str>'(?:[^']|'')*'|"(?:[^"]|"")*")
  | (?P<num>[0-9][0-9A-Za-z_]*)
  | (?P<id>[A-Za-z_@?$.][\w@?$]*)
  | (?P<op><=|>=|<>|==|!=|<<|>>|[-+*/()\[\],:<>=!&|^~%])
)""", re.X)


@dataclass
class Tok:
    kind: str     # str | num | id | op
    text: str

    @property
    def low(self) -> str:
        return self.text.lower()


def tokenize(s: str) -> list[Tok]:
    out: list[Tok] = []
    pos = 0
    s = s.rstrip()
    while pos < len(s):
        m = _TOK.match(s, pos)
        if not m or m.end() == pos:
            if s[pos:].strip() == "":
                break
            raise AsmError("E-SYNTAX", what=f"unexpected character '{s[pos:].strip()[0]}'")
        pos = m.end()
        kind = m.lastgroup
        out.append(Tok(kind, m.group(kind)))
    return out


def strip_comment(s: str) -> str:
    q = ""
    for i, ch in enumerate(s):
        if q:
            if ch == q:
                q = ""
        elif ch in "'\"":
            q = ch
        elif ch == ";":
            return s[:i]
    return s


def parse_number(t: str) -> int:
    s = t.lower().replace("_", "")
    try:
        if s.startswith("0x"):
            return int(s[2:], 16)
        if s.endswith("h"):
            return int(s[:-1], 16)
        if re.fullmatch(r"[01]+[by]", s):
            return int(s[:-1], 2)
        if re.fullmatch(r"[0-7]+[oq]", s):
            return int(s[:-1], 8)
        if re.fullmatch(r"[0-9]+d", s):
            return int(s[:-1], 10)
        if s.isdigit():
            return int(s, 10)
    except ValueError:
        pass
    raise AsmError("E-NUMBER", text=t)


def string_value(tok: Tok) -> str:
    q = tok.text[0]
    return tok.text[1:-1].replace(q + q, q)


def split_commas(toks: list[Tok]) -> list[list[Tok]]:
    out, cur, depth = [], [], 0
    for t in toks:
        if t.kind == "op" and t.text in "([":
            depth += 1
        elif t.kind == "op" and t.text in ")]":
            depth -= 1
        if t.kind == "op" and t.text == "," and depth == 0:
            out.append(cur)
            cur = []
            continue
        cur.append(t)
    if cur or out:
        out.append(cur)
    return out


def split_text_commas(s: str) -> list[str]:
    out, cur, depth, q = [], "", 0, ""
    for ch in s:
        if q:
            cur += ch
            if ch == q:
                q = ""
            continue
        if ch in "'\"":
            q = ch
        elif ch in "(<[":
            depth += 1
        elif ch in ")>]":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
            continue
        cur += ch
    if cur.strip() or out:
        out.append(cur.strip())
    return out


def to_cp437(s: str, warn=None) -> bytes:
    out = bytearray()
    for ch in s:
        try:
            out += ch.encode("cp437")
        except UnicodeEncodeError:
            out.append(0x3F)
            if warn is not None:
                warn(ch)
    return bytes(out)


# ============================================================================ preprocessor
@dataclass
class Macro:
    name: str
    params: list
    defaults: list
    body: list               # [SrcLine]
    file: str
    line: int


_WORD = re.compile(r"[A-Za-z_@?$][\w@?$]*")


def _subst_words(text: str, mapping: dict) -> str:
    """Replace whole words (outside quotes) by mapping[lower word]; '&' glues a parameter to text."""
    out, i, q = [], 0, ""
    n = len(text)
    while i < n:
        ch = text[i]
        if q:
            # parameters are also replaced inside strings when written with & (MASM): 'x&p&'
            if ch == "&":
                m = _WORD.match(text, i + 1)
                if m and m.group(0).lower() in mapping:
                    out.append(mapping[m.group(0).lower()])
                    i = m.end()
                    if i < n and text[i] == "&":
                        i += 1
                    continue
            out.append(ch)
            if ch == q:
                q = ""
            i += 1
            continue
        if ch in "'\"":
            q = ch
            out.append(ch)
            i += 1
            continue
        m = _WORD.match(text, i)
        if m and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] in "_@?$")):
            w = m.group(0)
            out.append(mapping.get(w.lower(), w))
            i = m.end()
            continue
        if ch == "&":
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)



# ============================================================================ STRUC and conditional assembly
COND_IF = {"if", "ife", "ifdef", "ifndef", "ifb", "ifnb", "ifidn", "ifidni", "ifdif", "ifdifi", "if1", "if2"}
COND_ELSEIF = {"else" + d for d in COND_IF if d not in ("if1", "if2")}
PTR_OF = {1: "byte", 2: "word", 4: "dword", 8: "qword"}


@dataclass
class StrucField:
    name: str                # "" for an unnamed field
    offset: int
    size: int                # total bytes
    elem: int                # element size (1 / 2 / 4 / 8)
    directive: str           # db / dw / dd / dq
    init: str                # default initializer text
    count: int               # elements
    struc: "Struc | None" = None     # a field that is itself a structure


@dataclass
class Struc:
    name: str
    fields: list
    size: int

    def field(self, name: str):
        return next((f for f in self.fields if f.name.lower() == name.lower()), None)


def _item_count(item: str, elem: int) -> int:
    """Elements of one data item: 3 dup (?) / 'abc' / 5."""
    m = re.match(r"^(.+?)\s+dup\s*\((.*)\)\s*$", item, re.I | re.S)
    if m:
        try:
            n = Evaluator(None).const(tokenize(m.group(1)))
        except AsmError:
            n = 1
        return max(0, n) * sum(_item_count(x, elem) for x in split_text_commas(m.group(2)) if x != "")
    s = item.strip()
    if elem == 1 and len(s) >= 2 and s[0] in "'\"" and s[-1] == s[0]:
        return max(1, len(s) - 2 - s[1:-1].count(s[0] * 2))
    return 1


def _outside_quotes(text: str, fn) -> str:
    """Apply *fn* to the parts of *text* outside quotes."""
    out, i, n = [], 0, len(text)
    while i < n:
        q = text[i] if text[i] in "'\"" else ""
        if q:
            j = text.find(q, i + 1)
            j = n - 1 if j < 0 else j
            out.append(text[i:j + 1])
            i = j + 1
            continue
        j = i
        while j < n and text[j] not in "'\"":
            j += 1
        out.append(fn(text[i:j]))
        i = j
    return "".join(out)


class Preprocessor:
    def __init__(self, read_include, diags: list):
        self.read_include = read_include
        self.diags = diags
        self.macros: dict[str, Macro] = {}
        self.text_equ: dict[str, str] = {}
        self.local_counter = 0
        self.out: list[SrcLine] = []
        self.structs: dict[str, Struc] = {}
        self.struct_vars: dict[str, tuple[Struc, int]] = {}    # instance name -> (structure, count)
        self.num_equ: dict[str, int] = {}                       # numeric equates seen so far (for IF)
        self.defined: set[str] = set()                          # names defined so far (for IFDEF)

    def error(self, sl: SrcLine, code: str, **args):
        self.diags.append(Diagnostic("Error", sl.file, sl.line, code, args))

    def run(self, text: str, file: str) -> list[SrcLine]:
        lines = [SrcLine(t, file, i + 1) for i, t in enumerate(text.splitlines())]
        self._process(lines, 0, None)
        return self.out

    @staticmethod
    def _words(s: str) -> list[str]:
        return strip_comment(s).replace(",", " , ").split()

    def _collect_block(self, lines, i, start_sl, name):
        """Lines of a macro / rept body up to the matching endm. Returns (body, next index)."""
        depth, body = 1, []
        while i < len(lines):
            sl = lines[i]
            w = [x.lower() for x in self._words(sl.text)]
            if w and (w[0] in ("rept", "irp", "irpc", "repeat", "while", "for", "forc")
                      or (len(w) > 1 and w[1] == "macro")):
                depth += 1
            elif w and w[0] == "endm":
                depth -= 1
                if depth == 0:
                    return body, i + 1
            body.append(sl)
            i += 1
        self.error(start_sl, "E-MACRO-OPEN", name=name)
        return body, i

    def _process(self, lines: list[SrcLine], depth: int, site: SrcLine | None) -> None:
        if depth > 40:
            if site is not None:
                self.error(site, "E-MACRO-DEPTH")
            return
        i = 0
        conds: list[list] = []          # [parent active, a branch was taken, active, line] of open IF blocks
        while i < len(lines):
            sl = lines[i]
            i += 1
            raw = strip_comment(sl.text)
            words = raw.replace(",", " , ").split()
            if not words:
                self.out.append(SrcLine("", sl.file, sl.line) if site is None else SrcLine("", site.file, site.line))
                continue
            lw = [w.lower() for w in words]
            # conditional assembly
            d = lw[0]
            if d in COND_IF or d in COND_ELSEIF or d in ("else", "endif"):
                arg = raw.split(None, 1)[1].strip() if len(raw.split(None, 1)) > 1 else ""
                active = conds[-1][2] if conds else True
                if d in COND_IF:
                    val = self._cond(d, arg, sl) if active else False
                    conds.append([active, val, active and val, sl])
                elif not conds:
                    self.error(sl, "E-COND", name=d)
                elif d in COND_ELSEIF:
                    top = conds[-1]
                    if top[0] and not top[1]:
                        val = self._cond(d[4:], arg, sl)
                        top[1], top[2] = val, val
                    else:
                        top[2] = False
                elif d == "else":
                    top = conds[-1]
                    top[2] = top[0] and not top[1]
                    top[1] = True
                else:
                    conds.pop()
                self.out.append(self._here(sl, site))
                continue
            if conds and not conds[-1][2]:
                continue
            # structure definition:  Name struc ... Name ends
            if len(lw) >= 2 and lw[1] in ("struc", "struct") and words[0].lower() not in self.macros:
                i = self._struc(words[0], lines, i, sl)
                self.out.append(self._here(sl, site))
                continue
            # macro definition
            if len(lw) >= 2 and lw[1] == "macro":
                name = words[0]
                rest = raw.split(None, 2)[2] if len(raw.split(None, 2)) > 2 else ""
                params, defaults = [], []
                for p in split_text_commas(rest):
                    if not p:
                        continue
                    p, _, dflt = p.partition(":=")
                    p = p.split(":")[0].strip()
                    params.append(p.lower())
                    defaults.append(dflt.strip().strip("<>"))
                body, i = self._collect_block(lines, i, sl, name)
                self.macros[name.lower()] = Macro(name, params, defaults, body, sl.file, sl.line)
                self.out.append(self._here(sl, site))
                continue
            if lw[0] in ("rept", "repeat"):
                body, i = self._collect_block(lines, i, sl, "rept")
                try:
                    count = Evaluator(None).const(tokenize(self._apply_equ(raw.split(None, 1)[1])))
                except (AsmError, IndexError):
                    self.error(sl, "E-SYNTAX", what="rept needs a count")
                    count = 0
                for _ in range(max(0, min(count, 10000))):
                    self._process(body, depth + 1, site or sl)
                continue
            if lw[0] in ("irp", "for"):
                body, i = self._collect_block(lines, i, sl, lw[0])
                rest = raw.split(None, 1)[1] if len(raw.split(None, 1)) > 1 else ""
                pname, _, values = rest.partition(",")
                values = values.strip().strip("<>")
                for v in split_text_commas(values):
                    sub = [SrcLine(_subst_words(b.text, {pname.strip().lower(): v}), b.file, b.line) for b in body]
                    self._process(sub, depth + 1, site or sl)
                continue
            if lw[0] == "include" and len(words) > 1:
                name = raw.split(None, 1)[1].strip().strip("'\"<>")
                content = self.read_include(name)
                if content is None:
                    self.error(sl, "E-INCLUDE", name=name)
                else:
                    sub = [SrcLine(t, name, k + 1) for k, t in enumerate(content.splitlines())]
                    self._process(sub, depth + 1, site)
                continue
            # text equates:  name equ <text> | name equ [bp+4] | name textequ <...>
            if len(lw) >= 3 and lw[1] in ("equ", "textequ"):
                rhs = raw.split(None, 2)[2].strip()
                if lw[1] == "textequ" or rhs.startswith("<") or _is_text_equ(rhs):
                    self.text_equ[lw[0]] = rhs[1:-1] if rhs.startswith("<") and rhs.endswith(">") else rhs
                    self.out.append(self._here(sl, site))
                    continue
            text = self._apply_equ(raw) if self.text_equ else raw
            # macro call (optionally after a "label:")
            m = re.match(r"\s*([A-Za-z_@?$][\w@?$]*:)?\s*([A-Za-z_@?$.][\w@?$]*)(.*)$", text)
            if m and m.group(2).lower() in self.macros:
                if m.group(1):
                    self.out.append(SrcLine(m.group(1), *(self._pos(sl, site))))
                self._expand(self.macros[m.group(2).lower()], m.group(3), depth, site or sl)
                continue
            # structure instance:  p1 Point <1, 2>  /  arr Point 3 dup (<>)  /  Point <>
            if self.structs and self._instance(text, sl, site):
                continue
            if self.structs:
                text = self._struct_refs(text)
            self._track(text)
            self.out.append(SrcLine(text, *(self._pos(sl, site))))
        for c in conds:
            self.error(c[3], "E-COND-OPEN")

    @staticmethod
    def _pos(sl, site):
        return (sl.file, sl.line) if site is None else (site.file, site.line)

    def _here(self, sl, site):
        return SrcLine("", *self._pos(sl, site))

    def _apply_equ(self, text: str) -> str:
        if not self.text_equ:
            return text
        for _ in range(8):                       # nested text equates
            new = _subst_words(text, self.text_equ) if any(
                w.lower() in self.text_equ for w in _WORD.findall(text)) else text
            if new == text:
                break
            text = new
        return text

    def _expand(self, mac: Macro, argtext: str, depth: int, site: SrcLine) -> None:
        args = split_text_commas(argtext.strip())
        mapping = {}
        for k, p in enumerate(mac.params):
            v = args[k] if k < len(args) and args[k] != "" else mac.defaults[k]
            if v.startswith("<") and v.endswith(">"):
                v = v[1:-1]
            mapping[p] = v
        body = []
        for b in mac.body:
            w = strip_comment(b.text).split(None, 1)
            if w and w[0].lower() == "local":
                for name in split_text_commas(w[1] if len(w) > 1 else ""):
                    if name:
                        self.local_counter += 1
                        mapping[name.lower()] = f"??{self.local_counter:04X}"
                continue
            body.append(b)
        sub = []
        for b in body:
            t = strip_comment(b.text)
            if t.strip().lower() == "exitm":
                break
            sub.append(SrcLine(_subst_words(t, mapping), b.file, b.line))
        self._process(sub, depth + 1, site)

    # ------------------------------------------------------------------ conditional assembly
    def is_defined(self, name: str) -> bool:
        k = name.strip().lower()
        return k in self.defined or k in self.macros or k in self.text_equ or k in self.num_equ or \
            k in self.structs

    def _number(self, expr: str, sl: SrcLine) -> int | None:
        text = self._apply_equ(expr)
        if self.num_equ:
            text = _subst_words(text, {k: str(v) for k, v in self.num_equ.items()})
        if self.structs:
            text = self._struct_refs(text)
        try:
            return Evaluator(None).const(tokenize(text))
        except AsmError as e:
            if sl is not None:
                self.diags.append(Diagnostic("Error", sl.file, sl.line, e.code, e.args_))
            return None

    def _cond(self, kind: str, arg: str, sl: SrcLine) -> bool:
        def angle(s):
            s = s.strip()
            return s[1:-1] if s.startswith("<") and s.endswith(">") else s
        if kind == "if1":
            return True
        if kind == "if2":
            return False
        if kind in ("if", "ife"):
            v = self._number(arg, sl)
            return (v not in (None, 0)) if kind == "if" else v == 0
        if kind in ("ifdef", "ifndef"):
            name = arg.split()[0] if arg.split() else ""
            return self.is_defined(name) == (kind == "ifdef")
        if kind in ("ifb", "ifnb"):
            return (angle(arg).strip() == "") == (kind == "ifb")
        parts = split_text_commas(arg)
        a, b = (angle(parts[0]), angle(parts[1])) if len(parts) >= 2 else (angle(arg), "")
        a, b = a.strip(), b.strip()
        if kind.endswith("i"):
            a, b = a.lower(), b.lower()
        return (a == b) == kind.startswith("ifidn")

    def _track(self, text: str) -> None:
        """Remember the names a line defines (IFDEF) and numeric equates (IF expressions)."""
        m = re.match(r"\s*([A-Za-z_@?$.][\w@?$]*)\s*:(?!:)", text)
        if m:
            self.defined.add(m.group(1).lower())
            return
        w = text.split(None, 2)
        if len(w) >= 2 and w[0].lower() not in MNEMONICS:
            second = w[1].lower()
            if second in DATA_DIRS or second in ("dt", "proc", "segment", "label", "group") or \
                    second in self.structs:
                self.defined.add(w[0].lower())
            elif second in ("equ", "=") and len(w) == 3:
                self.defined.add(w[0].lower())
                v = self._number(w[2], None)
                if v is not None:
                    self.num_equ[w[0].lower()] = v
        m = re.match(r"\s*([A-Za-z_@?$][\w@?$]*)\s*=\s*(.+)$", text)
        if m and m.group(1).lower() not in MNEMONICS:
            self.defined.add(m.group(1).lower())
            v = self._number(m.group(2), None)
            if v is not None:
                self.num_equ[m.group(1).lower()] = v

    # ------------------------------------------------------------------ STRUC
    def _struc(self, name: str, lines, i: int, start: SrcLine) -> int:
        """Read the fields of ``name struc`` up to ``name ends``; returns the index after it."""
        fields, off = [], 0
        while i < len(lines):
            sl = lines[i]
            i += 1
            raw = strip_comment(sl.text).strip()
            if not raw:
                continue
            w = raw.split(None, 2)
            if w[0].lower() == "ends" or (len(w) >= 2 and w[1].lower() == "ends"):
                st = Struc(name, fields, off)
                self.structs[name.lower()] = st
                self.defined.add(name.lower())
                return i
            if w[0].lower() in DATA_DIRS:
                fname, directive, init = "", w[0].lower(), raw.split(None, 1)[1] if len(w) > 1 else "?"
            elif len(w) >= 2 and w[1].lower() in DATA_DIRS:
                fname, directive, init = w[0], w[1].lower(), w[2] if len(w) > 2 else "?"
            elif len(w) >= 2 and w[1].lower() in self.structs:          # nested structure field
                inner = self.structs[w[1].lower()]
                init = w[2] if len(w) > 2 else "<>"
                fields.append(StrucField(w[0], off, inner.size, 1, "db", init, inner.size, inner))
                off += inner.size
                continue
            else:
                self.error(sl, "E-SYNTAX", what=f"a structure field is 'name db|dw|dd|dq value' ({raw})")
                continue
            elem = DATA_DIRS[directive]
            count = sum(_item_count(x, elem) for x in split_text_commas(init) if x != "") or 1
            fields.append(StrucField(fname, off, elem * count, elem, directive, init, count))
            off += elem * count
        self.error(start, "E-STRUC-OPEN", name=name)
        return i

    def _instance(self, text: str, sl: SrcLine, site) -> bool:
        """``[name] Struc <values>`` / ``[name] Struc N dup (<values>)`` -> data lines. False: not an instance."""
        m = re.match(r"^\s*(?:([A-Za-z_@?$][\w@?$]*)\s+)?([A-Za-z_@?$][\w@?$]*)\s+(.*)$", text)
        if not m or m.group(2).lower() not in self.structs:
            return False
        st = self.structs[m.group(2).lower()]
        name, rest = m.group(1), m.group(3).strip()
        count, inits = 1, rest
        dm = re.match(r"^(.+?)\s+dup\s*\((.*)\)\s*$", rest, re.I)
        if dm:
            v = self._number(dm.group(1), sl)
            count, inits = (v if v is not None else 1), dm.group(2).strip()
        values = split_text_commas(inits[1:-1]) if inits.startswith("<") and inits.endswith(">") else \
            ([] if inits in ("", "?") else split_text_commas(inits))
        pos = self._pos(sl, site)
        items: list[str] = []
        for _ in range(max(0, count)):
            items += self._field_items(st, values)
        for k, it in enumerate(items):
            self.out.append(SrcLine(f"{name} {it}" if (k == 0 and name) else it, *pos))
        if not st.fields:
            self.out.append(SrcLine(f"{name} label byte" if name else "", *pos))
        if name:
            self.defined.add(name.lower())
            self.struct_vars[name.lower()] = (st, count)
        return True

    def _field_items(self, st: Struc, values: list[str]) -> list[str]:
        """Data lines of one instance of *st* (positional *values*; "" = the field's default)."""
        items: list[str] = []
        for k, f in enumerate(st.fields):
            val = values[k] if k < len(values) and values[k] != "" else f.init
            if f.struc is not None:                           # nested structure: its own fields
                v = val.strip()
                inner = split_text_commas(v[1:-1]) if v.startswith("<") and v.endswith(">") else []
                items += self._field_items(f.struc, inner)
                continue
            items.append(f"{f.directive} {val}")
            if val is not f.init and f.count > 1 and f.directive == "db" and val[:1] in "'\"":
                n = _item_count(val, 1)
                if n < f.count:
                    items.append(f"db {f.count - n} dup (0)")
        return items

    def _field_any(self, fname: str):
        for st in self.structs.values():
            f = st.field(fname)
            if f is not None:
                return f
        return None

    def _struct_refs(self, text: str) -> str:
        """Rewrite structure references: Name.field -> offset, var.field / [bx].field / (Name ptr [bx]).field
        -> sized memory operands, size / type / length Name|var -> numbers."""
        structs = self.structs

        def fn(seg: str) -> str:
            def ptr_rx(m):
                st, f = structs.get(m.group(1).lower()), None
                if st is not None:
                    f = st.field(m.group(3))
                if f is None:
                    return m.group(0)
                inner = m.group(2)[1:-1]
                return f"{PTR_OF.get(f.elem, 'byte')} ptr [{inner}+{f.offset}]"
            seg = re.sub(r"\(\s*([A-Za-z_@?$][\w@?$]*)\s+ptr\s+(\[[^\]]*\])\s*\)\.([A-Za-z_@?$][\w@?$]*)", ptr_rx, seg,
                         flags=re.I)

            def bracket_rx(m):
                f = self._field_any(m.group(2))
                if f is None:
                    return m.group(0)
                return f"{PTR_OF.get(f.elem, 'byte')} ptr [{m.group(1)[1:-1]}+{f.offset}]"
            seg = re.sub(r"(\[[^\]]*\])\.([A-Za-z_@?$][\w@?$]*)", bracket_rx, seg)

            def dot_rx(m):
                a, b = m.group(1), m.group(2)
                st = structs.get(a.lower())
                if st is not None:
                    f = st.field(b)
                    return str(f.offset) if f is not None else m.group(0)
                var = self.struct_vars.get(a.lower())
                f = var[0].field(b) if var else self._field_any(b)
                if f is None:
                    return m.group(0)
                return f"{PTR_OF.get(f.elem, 'byte')} ptr {a}+{f.offset}"
            seg = re.sub(r"(?<![\w@?$.])([A-Za-z_@?$][\w@?$]*)\.([A-Za-z_@?$][\w@?$]*)", dot_rx, seg)

            def size_rx(m):
                op, name = m.group(1).lower(), m.group(2).lower()
                if name in structs:
                    return str(structs[name].size) if op in ("size", "sizeof", "type") else "1"
                if name in self.struct_vars:
                    st, n = self.struct_vars[name]
                    return {"type": st.size, "size": st.size * n, "sizeof": st.size * n,
                            "length": n, "lengthof": n}[op].__str__()
                return m.group(0)
            return re.sub(r"\b(size|sizeof|type|length|lengthof)\s+([A-Za-z_@?$][\w@?$]*)", size_rx, seg, flags=re.I)
        return _outside_quotes(text, fn)


def _is_text_equ(rhs: str) -> bool:
    low = rhs.lower()
    if "[" in rhs or re.search(r"\bptr\b", low):
        return True
    words = set(re.findall(r"[a-z_@?$][\w@?$]*", low))
    if words & (set(REG8) | set(REG16) | set(SREG)):
        return True
    if rhs.startswith(("'", '"')) and len(rhs) > 4:     # msg equ 'Hello world' (a string, not a char value)
        return True
    return False


# ============================================================================ values / expressions
@dataclass
class Val:
    v: int = 0
    reloc: bool = False          # depends on the address of a label
    mem: bool = False            # a memory reference (variable / label not under OFFSET)
    size: int = 0                # type of the referenced label
    sym: Symbol | None = None
    known: bool = True
    seg_of: Symbol | None = None   # SEG x / @data / segment name: value is a paragraph number
    string: str | None = None


class Evaluator:
    """Expression evaluation over tokens. ``asm`` gives symbols / $ (None = constants only)."""

    def __init__(self, asm):
        self.asm = asm
        self.toks: list[Tok] = []
        self.i = 0

    def const(self, toks: list[Tok]) -> int:
        v = self.eval(toks)
        if v.reloc or v.mem or not v.known:
            raise AsmError("E-EXPR", what=" ".join(t.text for t in toks))
        return v.v

    def eval(self, toks: list[Tok]) -> Val:
        self.toks, self.i = toks, 0
        if not toks:
            raise AsmError("E-EXPR", what="empty")
        v = self.p_or()
        if self.i < len(self.toks):
            raise AsmError("E-EXPR", what=" ".join(t.text for t in toks))
        return v

    # -- helpers
    def peek(self) -> Tok | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self) -> Tok:
        t = self.peek()
        if t is None:
            raise AsmError("E-EXPR", what="unexpected end")
        self.i += 1
        return t

    def is_(self, *words) -> bool:
        t = self.peek()
        return t is not None and t.low in words and (t.kind in ("id", "op"))

    @staticmethod
    def _combine(a: Val, b: Val, v: int, sub=False) -> Val:
        reloc = a.reloc or b.reloc
        if sub and a.reloc and b.reloc:
            reloc = False                       # label - label = a distance
        mem = (a.mem or b.mem) and not (sub and a.reloc and b.reloc)
        return Val(v, reloc, mem, a.size or b.size, a.sym or b.sym, a.known and b.known)

    def p_or(self) -> Val:
        a = self.p_and()
        while self.is_("or", "xor", "|", "^"):
            op = self.take().low
            b = self.p_and()
            a = self._combine(a, b, (a.v | b.v) if op in ("or", "|") else (a.v ^ b.v))
        return a

    def p_and(self) -> Val:
        a = self.p_not()
        while self.is_("and", "&"):
            self.take()
            b = self.p_not()
            a = self._combine(a, b, a.v & b.v)
        return a

    def p_not(self) -> Val:
        if self.is_("not", "~"):
            self.take()
            a = self.p_not()
            return Val(~a.v, a.reloc, False, a.size, a.sym, a.known)
        return self.p_rel()

    def p_rel(self) -> Val:
        a = self.p_add()
        ops = {"eq": "==", "ne": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">=", "==": "==", "!=": "!=",
               "<": "<", ">": ">", "<=": "<=", ">=": ">=", "<>": "!="}
        while self.peek() is not None and self.peek().low in ops and self.peek().kind in ("id", "op"):
            op = ops[self.take().low]
            b = self.p_add()
            r = {"==": a.v == b.v, "!=": a.v != b.v, "<": a.v < b.v, "<=": a.v <= b.v, ">": a.v > b.v,
                 ">=": a.v >= b.v}[op]
            a = Val(-1 if r else 0, False, False, 0, None, a.known and b.known)
        return a

    def p_add(self) -> Val:
        a = self.p_mul()
        while self.is_("+", "-"):
            op = self.take().text
            b = self.p_mul()
            a = self._combine(a, b, a.v + b.v if op == "+" else a.v - b.v, sub=(op == "-"))
        return a

    def p_mul(self) -> Val:
        a = self.p_unary()
        while self.is_("*", "/", "mod", "%", "shl", "shr", "<<", ">>"):
            op = self.take().low
            b = self.p_unary()
            if op in ("/", "mod", "%") and b.v == 0:
                if a.known and b.known:
                    raise AsmError("E-DIV0")
                v = 0
            elif op == "*":
                v = a.v * b.v
            elif op == "/":
                v = int(a.v / b.v)
            elif op in ("mod", "%"):
                v = a.v % b.v
            elif op in ("shl", "<<"):
                v = a.v << max(0, b.v)
            else:
                v = a.v >> max(0, b.v)
            a = self._combine(a, b, v)
        return a

    def p_unary(self) -> Val:
        t = self.peek()
        if t is None:
            raise AsmError("E-EXPR", what="unexpected end")
        lw = t.low
        if lw in SOFT_OPERATORS and self.asm is not None and lw in self.asm.symbols:
            return self.p_primary()
        if lw in ("+", "-") and t.kind == "op":
            self.take()
            a = self.p_unary()
            return a if lw == "+" else Val(-a.v, a.reloc, a.mem, a.size, a.sym, a.known)
        if t.kind == "id" and lw == "offset":
            self.take()
            a = self.p_unary()
            return Val(a.v, a.reloc, False, 0, a.sym, a.known)
        if t.kind == "id" and lw == "seg":
            self.take()
            a = self.p_unary()
            sym = a.sym
            if sym is None or self.asm is None:
                raise AsmError("E-EXPR", what="seg needs a label")
            return self.asm.seg_value(sym)
        if t.kind == "id" and lw in ("type", "length", "size", "lengthof", "sizeof"):
            self.take()
            a = self.p_unary()
            sym = a.sym
            if lw == "type":
                v = a.size if sym is None or sym.kind != "proc" else (0xFFFE if sym.far else 0xFFFF)
                if sym is not None and sym.kind == "label":
                    v = 0xFFFF
            elif lw in ("length", "lengthof"):
                v = (sym.first_count if lw == "length" else sym.count) if sym is not None else 1
            else:
                v = ((sym.first_count if lw == "size" else sym.count) * max(1, sym.size)) if sym is not None else 0
            return Val(v, False, False, 0, None, a.known)
        if t.kind == "id" and lw in ("low", "high", "lowword", "highword"):
            self.take()
            a = self.p_unary()
            v = {"low": a.v & 0xFF, "high": (a.v >> 8) & 0xFF, "lowword": a.v & 0xFFFF,
                 "highword": (a.v >> 16) & 0xFFFF}[lw]
            return Val(v, a.reloc, False, 0, a.sym, a.known)
        if t.kind == "id" and lw in ("byte", "word", "dword", "qword", "near", "far") and \
                self.i + 1 < len(self.toks) and self.toks[self.i + 1].low == "ptr":
            self.take()
            self.take()
            a = self.p_unary()
            sz = {"byte": 1, "word": 2, "dword": 4, "qword": 8, "near": 2, "far": 4}[lw]
            return Val(a.v, a.reloc, True, sz, a.sym, a.known)
        return self.p_primary()

    def p_primary(self) -> Val:
        t = self.take()
        if t.kind == "op" and t.text in "([":
            close = ")" if t.text == "(" else "]"
            a = self.p_or()
            if self.take().text != close:
                raise AsmError("E-EXPR", what=f"missing '{close}'")
            if close == "]":
                a = Val(a.v, a.reloc, True, a.size, a.sym, a.known)
            # var[2] / var(2) style indexing
            while self.is_("[", "("):
                b = self.p_primary()
                a = self._combine(a, b, a.v + b.v)
            return a
        if t.kind == "num":
            v = Val(parse_number(t.text))
        elif t.kind == "str":
            s = string_value(t)
            if len(s) > 2:
                v = Val(0, string=s)
                v.v = int.from_bytes(to_cp437(s[:4])[::-1].rjust(4, b"\0"), "big") if s else 0
            else:
                b = to_cp437(s)
                v = Val(int.from_bytes(b, "big") if b else 0, string=s)
        elif t.kind == "id":
            if t.text == "$":
                if self.asm is None:
                    raise AsmError("E-EXPR", what="$")
                return self.asm.here()
            if t.text == "?":
                return Val(0)
            if self.asm is None:
                raise AsmError("E-UNDEF", name=t.text)
            v = self.asm.symbol_value(t.text)
        else:
            raise AsmError("E-EXPR", what=f"unexpected '{t.text}'")
        while self.is_("["):                       # label[si] is handled by the operand parser; here: arr[2]
            b = self.p_primary()
            v = self._combine(v, b, v.v + b.v)
            v.mem = True
        return v


# ============================================================================ operands
@dataclass
class Operand:
    kind: str                     # reg8 | reg16 | sreg | imm | mem
    reg: int = 0
    val: Val | None = None        # imm value or memory displacement
    regs: frozenset = frozenset()
    size: int = 0                 # mem: 1 / 2 / 4 (0 = unknown)
    seg: int | None = None        # explicit segment override
    short: bool = False
    near: bool = False
    far: bool = False
    text: str = ""

    @property
    def bits(self) -> int:
        return {"reg8": 8, "reg16": 16, "sreg": 16}.get(self.kind, self.size * 8)


# ============================================================================ sections / statements
class Frame:
    def __init__(self, name: str):
        self.name = name
        self.sections: list[Section] = []
        self.para = 0            # paragraph offset from the load segment
        self.size = 0


class Section:
    def __init__(self, name: str, kind: str, frame: Frame):
        self.name = name
        self.kind = kind          # code | data | stack | other
        self.frame = frame
        self.base = 0             # start offset inside the frame
        self.org: int | None = None
        self.loc = 0
        self.size = 0
        self.prev_size = 0
        self.data = bytearray()
        self.align = 2 if kind != "code" else 1
        self.stack_size = 0

    def emit(self, b: bytes) -> None:
        end = self.loc + len(b)
        rel = self.loc - self.base
        if rel < 0:
            rel = 0
        if len(self.data) < rel + len(b):
            self.data.extend(b"\0" * (rel + len(b) - len(self.data)))
        self.data[rel:rel + len(b)] = b
        self.loc = end
        self.size = max(self.size, self.loc - self.base)


@dataclass
class Stmt:
    sl: SrcLine
    label: str = ""               # "name:" label
    name: str = ""                # name before a directive (x db 1, p proc ...)
    op: str = ""                  # mnemonic / directive (lower case)
    prefixes: list = field(default_factory=list)
    rest: str = ""                # operand text
    toks: list = field(default_factory=list)
    flags: set = field(default_factory=set)     # sticky size choices across passes
    size: int = -1
    long: bool = False


# ============================================================================ the assembler
class Assembler:
    MAX_PASSES = 12

    def __init__(self, load_seg: int = 0x0700, read_include=None):
        self.load_seg = load_seg
        self.read_include = read_include or (lambda name: None)
        self.diags: list[Diagnostic] = []
        self.symbols: dict[str, Symbol] = {}
        self.frames: list[Frame] = []
        self.sections: dict[str, Section] = {}
        self.com = False
        self.model = ""
        self.cur: Section | None = None
        self.pass_no = 0
        self.final = False
        self.changed = False
        self.assume: dict[int, str] = {}
        self.proc_stack: list[Symbol] = []
        self.seg_stack: list[Section] = []
        self.entry: Val | None = None
        self.entry_tokens: list | None = None
        self.stmt: Stmt | None = None
        self.addr_line: dict = {}
        self.line_addrs: dict = {}
        self.listing: list = []
        self.files: list[str] = []
        self.warned: set = set()
        self._startup_at = None
        self._total_paras = 0

    # ------------------------------------------------------------------ diagnostics
    def _diag(self, sev: str, code: str, sl: SrcLine | None = None, **args) -> None:
        sl = sl or (self.stmt.sl if self.stmt else SrcLine("", "", 0))
        key = (sev, code, sl.file, sl.line, tuple(sorted(args.items())))
        if key in self.warned:
            return
        self.warned.add(key)
        self.diags.append(Diagnostic(sev, sl.file, sl.line, code, args))

    def warn(self, code: str, **args) -> None:
        if self.final:
            self._diag("Warning", code, **args)

    # ------------------------------------------------------------------ top level
    def assemble(self, text: str, filename: str = "main.asm") -> Program:
        self.files = [filename]
        pre = Preprocessor(self._include, self.diags)
        lines = pre.run(text, filename)
        stmts = []
        for sl in lines:
            try:
                st = self.parse_line(sl)
            except AsmError as e:
                self.diags.append(Diagnostic("Error", sl.file, sl.line, e.code, e.args_))
                continue
            if st is not None:
                stmts.append(st)
        self.prescan(stmts)
        prog = Program(load_seg=self.load_seg)
        if any(d.severity == "Error" for d in self.diags):
            return self._result(prog)
        prev_values = None
        for p in range(self.MAX_PASSES):
            self.pass_no = p
            self.final = False
            self.run_pass(stmts)
            values = self._snapshot(stmts)
            if values == prev_values:
                break
            prev_values = values
        else:
            self._diag("Error", "E-PASSES", SrcLine("", filename, 1))
            return self._result(prog)
        self.pass_no += 1
        self.final = True
        self.run_pass(stmts)
        return self._result(prog)

    def _include(self, name: str):
        content = self.read_include(name)
        if content is not None and name not in self.files:
            self.files.append(name)
        return content

    def _snapshot(self, stmts):
        syms = tuple((k, s.offset, s.value, s.known, s.section.name if s.section else "")
                     for k, s in sorted(self.symbols.items()))
        return syms, tuple(st.size for st in stmts), tuple(f.para for f in self.frames), \
            tuple((s.base, s.size) for s in self.sections.values())

    # ------------------------------------------------------------------ parsing lines
    def parse_line(self, sl: SrcLine) -> Stmt | None:
        raw = strip_comment(sl.text).strip()
        if not raw:
            return None
        if raw.startswith("#"):                      # emu8086: #make_com#, #make_exe#, #start=...#
            low = raw.lower().strip("#").strip()
            st = Stmt(sl, op="#" + low.split("=")[0].strip())
            return st
        st = Stmt(sl)
        m = re.match(r"([A-Za-z_@?$.][\w@?$]*)\s*:(?!:)\s*(.*)$", raw)
        if m and m.group(1).lower() not in SREG:
            st.label = m.group(1)
            raw = m.group(2).strip()
            if not raw:
                return st
        parts = raw.split(None, 1)
        first = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        second = rest.split(None, 1)[0].lower() if rest else ""
        named_dirs = set(DATA_DIRS) | {"equ", "=", "proc", "endp", "segment", "ends", "label", "macro",
                                       "struc", "struct", "record", "textequ", "group", "dt", "union"}
        if "=" in first and first not in ("=",) and not first.startswith("="):
            # x=5
            name, _, value = raw.partition("=")
            st.name, st.op, st.rest = name.strip(), "=", value.strip()
        elif second in named_dirs and first not in MNEMONICS and not first.startswith("."):
            st.name = parts[0]
            st.op = second
            st.rest = rest.split(None, 1)[1].strip() if len(rest.split(None, 1)) > 1 else ""
        elif rest.startswith("=") and first not in MNEMONICS:
            st.name, st.op, st.rest = parts[0], "=", rest[1:].strip()
        else:
            # prefixes: rep movsb, lock xchg ...
            while first in PREFIXES and rest:
                st.prefixes.append(first)
                parts = rest.split(None, 1)
                first = parts[0].lower()
                rest = parts[1].strip() if len(parts) > 1 else ""
            st.op = first
            st.rest = rest
            if first in PREFIXES and not rest:
                st.op = first
        if st.op not in ("=", "equ", "textequ") and not st.op.startswith("#"):
            st.toks = tokenize(st.rest)
        return st

    # ------------------------------------------------------------------ prescan: symbol kinds
    def prescan(self, stmts: list[Stmt]) -> None:
        for st in stmts:
            self.stmt = st
            op = st.op
            if op in ("#make_com", "#make_tiny"):
                self.com = True
            elif op == ".model":
                self.model = (st.rest.split(",")[0].split() or [""])[0].lower()
                if self.model == "tiny":
                    self.com = True
            if st.label:
                self._declare(st.label, "label", st.sl)
            if st.name:
                if op in DATA_DIRS or op == "dt":
                    self._declare(st.name, "var", st.sl, size=DATA_DIRS.get(op, 10))
                elif op == "label":
                    typ = (st.rest.split() or ["near"])[0].lower()
                    if typ in ("near", "far", "proc"):
                        s = self._declare(st.name, "label", st.sl)
                        s.far = typ == "far"
                    else:
                        self._declare(st.name, "var", st.sl, size=DATA_DIRS.get(typ, 1))
                elif op == "proc":
                    s = self._declare(st.name, "proc", st.sl)
                    s.far = bool(re.search(r"\bfar\b", st.rest, re.I))
                elif op in ("equ", "="):
                    key = st.name.lower()
                    if key not in self.symbols:
                        s = Symbol(st.name, "const", file=st.sl.file, line=st.sl.line, text=st.rest)
                        self.symbols[key] = s
                    elif self.symbols[key].kind != "const":
                        self._diag("Error", "E-REDEF", st.sl, name=st.name, line=self.symbols[key].line)
                elif op == "segment":
                    key = st.name.lower()
                    if key not in self.symbols:
                        self.symbols[key] = Symbol(st.name, "segment", file=st.sl.file, line=st.sl.line)
                elif op in ("struc", "struct", "record", "union"):
                    self._diag("Error", "E-NOT-SUPPORTED", st.sl, name=op)
        has_segments = any(st.op in ("segment", ".code", ".data", ".stack", ".data?", ".const", ".fardata")
                           for st in stmts)
        has_org100 = any(st.op == "org" for st in stmts)
        if not has_segments or (has_org100 and not self.model and
                                not any(st.op in ("segment", ".data", ".stack") for st in stmts)):
            self.com = True
        if any(st.op == "#make_exe" for st in stmts):
            self.com = False
        if not any(st.op in MNEMONICS for st in stmts):
            self._diag("Error", "E-NO-CODE", SrcLine("", self.files[0], 1))

    def _declare(self, name: str, kind: str, sl: SrcLine, size: int = 0) -> Symbol:
        key = name.lower()
        if key in KEYWORDS_NOT_SYMBOLS or key in MNEMONICS:
            self._diag("Error", "E-SYNTAX", sl, what=f"'{name}' is a reserved word and cannot be a name")
        old = self.symbols.get(key)
        if old is not None and old.kind not in ("segment",):
            self._diag("Error", "E-REDEF", sl, name=name, line=old.line)
            return old
        s = Symbol(name, kind, size=size, file=sl.file, line=sl.line)
        self.symbols[key] = s
        return s

    # ------------------------------------------------------------------ symbols / values
    def here(self) -> Val:
        return Val(self._section().loc, True, False, 0, None, True)

    def seg_value(self, sym: Symbol) -> Val:
        sec = sym.section
        if sym.kind == "segment":
            sec = self.sections.get(sym.name.lower())
        if sec is None:
            return Val(0, True, False, 0, None, False)
        return Val(self.load_seg + sec.frame.para, True, False, 0, None, True, seg_of=sym)

    def symbol_value(self, name: str) -> Val:
        key = name.lower()
        if key in ("@data", "dgroup"):
            sec = self._data_section()
            if sec is None:
                return Val(self.load_seg, True, False, 0, None, True)
            return Val(self.load_seg + sec.frame.para, True, False, 0, None, True)
        if key in ("@code", "@stack", "@curseg"):
            sec = {"@code": self._section_of_kind("code"), "@stack": self._section_of_kind("stack"),
                   "@curseg": self.cur}[key]
            return Val(self.load_seg + (sec.frame.para if sec else 0), True, False, 0, None, True)
        sym = self.symbols.get(key)
        if sym is None:
            if self.final:
                raise AsmError("E-UNDEF", name=name)
            return Val(0, False, False, 0, None, False)
        if sym.kind == "segment":
            return self.seg_value(sym)
        if sym.kind == "const":
            if sym.defined_pass != self.pass_no and sym.text and not sym.known:
                try:                                   # forward reference: evaluate the text now
                    v = Evaluator(self).eval(tokenize(sym.text))
                    return Val(v.v, v.reloc, v.mem, v.size, v.sym, v.known)
                except AsmError:
                    return Val(0, False, False, 0, None, False)
            return Val(sym.value, sym.reloc, False, 0, None, sym.known)
        known = sym.known
        return Val(sym.offset, True, True, sym.size, sym, known)

    def _data_section(self) -> Section | None:
        for name in ("_data", "data", "dseg", "dat"):
            if name in self.sections:
                return self.sections[name]
        return self._section_of_kind("data")

    def _section_of_kind(self, kind: str) -> Section | None:
        for s in self.sections.values():
            if s.kind == kind:
                return s
        return None

    def define(self, name: str, kind: str = "label") -> None:
        sym = self.symbols.get(name.lower())
        if sym is None:
            return
        sec = self._section()
        if sym.offset != sec.loc or sym.section is not sec:
            self.changed = True
        sym.offset = sec.loc
        sym.section = sec
        sym.known = True
        sym.defined_pass = self.pass_no

    # ------------------------------------------------------------------ sections
    def _get_section(self, name: str, kind: str) -> Section:
        key = name.lower()
        sec = self.sections.get(key)
        if sec is None:
            if self.com:
                frame = self.frames[0] if self.frames else None
                if frame is None:
                    frame = Frame("COM")
                    self.frames.append(frame)
            else:
                frame = Frame(name)
                self.frames.append(frame)
                if self.model:              # simplified directives (DOSSEG order): code, data, stack
                    rank = {"code": 0, "data": 1, "other": 1, "stack": 2}
                    self.frames.sort(key=lambda f: rank.get(f.sections[0].kind if f.sections else kind, 1)
                                     if f is not frame else rank.get(kind, 1))
            sec = Section(name, kind, frame)
            frame.sections.append(sec)
            self.sections[key] = sec
            if self.com and kind == "code":           # code first inside the COM segment
                frame.sections.remove(sec)
                frame.sections.insert(0, sec)
            idx = frame.sections.index(sec)
            if idx == 0:
                sec.base = 0x100 if self.com else 0
            else:
                prev = frame.sections[idx - 1]
                end = prev.base + max(prev.size, prev.prev_size)
                sec.base = (end + sec.align - 1) // sec.align * sec.align
            sec.loc = sec.base
        return sec

    def _section(self) -> Section:
        if self.cur is None:
            self.cur = self._get_section("_TEXT", "code")
        return self.cur

    def _layout_start(self) -> None:
        """Before each pass: section bases from the sizes of the previous pass."""
        para = 0
        for frame in self.frames:
            off = 0
            for i, sec in enumerate(frame.sections):
                if i == 0:
                    base = 0x100 if (self.com and sec.org is None) else 0
                else:
                    base = (off + sec.align - 1) // sec.align * sec.align
                sec.base = base
                sec.loc = base
                sec.prev_size, sec.size = sec.size, 0
                sec.data = bytearray()
                off = base + max(sec.prev_size, 0)
            frame.size = off
            frame.para = para
            para += max(1, (off + 15) // 16) if not self.com else 0x1000
        self._total_paras = para

    def run_pass(self, stmts: list[Stmt]) -> None:
        self._layout_start()
        self.cur = None
        self.assume = {}
        self.proc_stack = []
        self.seg_stack = []
        self.entry_tokens = None
        self.addr_line, self.line_addrs, self.listing = {}, {}, []
        if self.com:                       # everything addressable through every segment register
            self.assume = {0: "*", 1: "*", 2: "*", 3: "*"}
        elif self.model:
            self.assume = {1: "_text", 3: "_data", 2: "stack"}
        for st in stmts:
            self.stmt = st
            if st.op == "end":
                self.entry_tokens = st.toks
                self._label(st)
                break
            try:
                self.statement(st)
            except AsmError as e:
                if self.final:
                    self._diag("Error", e.code, st.sl, **e.args_)
                st.size = max(st.size, 0)
        if self.final:
            for p in self.proc_stack:
                self._diag("Error", "E-PROC-OPEN", SrcLine("", p.file, p.line), name=p.name)
        self._layout_end()

    def _layout_end(self) -> None:
        # sizes may have grown: recompute paragraphs for the next pass
        para = 0
        for frame in self.frames:
            off = 0
            for i, sec in enumerate(frame.sections):
                off = max(off, sec.base + sec.size)
            frame.size = off
            frame.para = para if not self.com else 0
            para += max(1, (off + 15) // 16)

    # ------------------------------------------------------------------ statements
    def _label(self, st: Stmt) -> None:
        if st.label:
            self.define(st.label)

    def statement(self, st: Stmt) -> None:
        op = st.op
        self._label(st)
        if not op:
            st.size = 0
            return
        if op.startswith("#"):
            return
        if op in IGNORED_DIRS:
            return
        if op in CPU_386:
            self.warn("W-386", name=op)
            return
        if op in (".code", ".data", ".data?", ".const", ".fardata", ".fardata?", ".stack"):
            if op == ".code":
                self.cur = self._get_section("_TEXT", "code")
            elif op == ".stack":
                sec = self._get_section("STACK", "stack")
                try:
                    n = Evaluator(self).const(st.toks) if st.toks else 1024
                except AsmError:
                    n = 1024
                prev = self.cur
                self.cur = sec
                sec.stack_size = n
                sec.emit(b"\0" * n)
                self.cur = prev
                return
            else:
                self.cur = self._get_section("_DATA", "data")
            return
        if op == ".startup":
            sec = self._section()
            self._startup_at = (sec, sec.loc)
            if not self.com:
                self.encode_text(st, "mov", "dx, @data")
                self.encode_text(st, "mov", "ds, dx")
            return
        if op == ".exit":
            code = st.rest.strip()
            if code:
                self.encode_text(st, "mov", f"al, {code}")
                self.encode_text(st, "mov", "ah, 4Ch")
            else:
                self.encode_text(st, "mov", "ax, 4C00h")
            self.encode_text(st, "int", "21h")
            return
        if op == "segment":
            kind = "code" if re.search(r"\bcode\b|code|text", st.name, re.I) else "data"
            if re.search(r"\bstack\b", st.rest, re.I) or st.name.lower() in ("stack", "sseg", "stk"):
                kind = "stack"
            sec = self._get_section(st.name, kind)
            self.seg_stack.append(self.cur)
            self.cur = sec
            return
        if op == "ends":
            if not self.seg_stack:
                if self.final:
                    raise AsmError("E-ENDS")
                return
            self.cur = self.seg_stack.pop()
            return
        if op == "assume":
            for part in split_text_commas(st.rest):
                k, _, v = part.partition(":")
                k = k.strip().lower()
                if k in SREG:
                    v = v.strip().lower()
                    if v in ("nothing", ""):
                        self.assume.pop(SREG[k], None)
                    else:
                        self.assume[SREG[k]] = "_data" if v in ("@data", "dgroup") else v
            return
        if op == "org":
            sec = self._section()
            n = Evaluator(self).const(st.toks)
            if sec.loc == sec.base and sec.size == 0:
                sec.org = n
                sec.base = n if sec is sec.frame.sections[0] else sec.base
            sec.loc = n
            if st.label:
                self.define(st.label)
            return
        if op in ("even", "align"):
            sec = self._section()
            n = 2 if op == "even" else Evaluator(self).const(st.toks)
            if n > 1:
                pad = (-sec.loc) % n
                sec.emit((b"\x90" if sec.kind == "code" else b"\0") * pad)
            return
        if op == "proc":
            sym = self.symbols.get(st.name.lower())
            self.define(st.name)
            if sym is not None:
                self.proc_stack.append(sym)
            return
        if op == "endp":
            if not self.proc_stack or self.proc_stack[-1].name.lower() != st.name.lower():
                if self.final:
                    raise AsmError("E-ENDP", name=st.name)
                return
            self.proc_stack.pop()
            return
        if op == "label":
            self.define(st.name)
            return
        if op in ("equ", "="):
            sym = self.symbols.get(st.name.lower())
            try:
                v = Evaluator(self).eval(tokenize(st.rest))
            except AsmError:
                if self.final:
                    raise
                v = Val(0, False, False, 0, None, False)
            if sym is not None:
                if (sym.value, sym.known) != (v.v, v.known):
                    self.changed = True
                sym.value, sym.reloc, sym.known = v.v, v.reloc, v.known
                sym.defined_pass = self.pass_no
            return
        if op in ("macro", "endm", "local", "exitm", "textequ", "group"):
            return
        if op in DATA_DIRS or op == "dt":
            self.data(st)
            return
        if op in ("ret", "retn", "retf", "iret") or op in MNEMONICS:
            self.instruction(st)
            return
        raise AsmError("E-UNKNOWN-INSTR", name=st.op)

    # ------------------------------------------------------------------ data
    def data(self, st: Stmt) -> None:
        size = DATA_DIRS.get(st.op, 10)
        sec = self._section()
        if st.name:
            self.define(st.name)
        out = bytearray()
        items = split_commas(st.toks)
        count = 0
        first = 0
        for k, item in enumerate(items):
            b, n = self._data_item(item, size)
            out += b
            count += n
            if k == 0:
                first = n
        if st.name:
            sym = self.symbols.get(st.name.lower())
            if sym is not None:
                sym.count = max(count, 1)
                sym.first_count = max(first, 1)
                sym.size = size
        self._record(st, sec, sec.loc, bytes(out), code=False)
        sec.emit(bytes(out))
        st.size = len(out)

    def _data_item(self, item: list[Tok], size: int) -> tuple[bytes, int]:
        if not item:
            raise AsmError("E-SYNTAX", what="empty data item")
        # n DUP (items)
        depth = 0
        for k, t in enumerate(item):
            if t.kind == "op" and t.text in "([":
                depth += 1
            elif t.kind == "op" and t.text in ")]":
                depth -= 1
            elif depth == 0 and t.kind == "id" and t.low == "dup":
                try:
                    n = Evaluator(self).const(item[:k])
                except AsmError:
                    raise AsmError("E-DUP") from None
                inner = item[k + 1:]
                if inner and inner[0].text == "(" and inner[-1].text == ")":
                    inner = inner[1:-1]
                if n < 0 or n > 0x10000:
                    raise AsmError("E-DUP")
                one = bytearray()
                cnt = 0
                for sub in split_commas(inner):
                    b, c = self._data_item(sub, size)
                    one += b
                    cnt += c
                return bytes(one) * n, cnt * n
        if len(item) == 1 and item[0].kind == "str" and (size == 1 or len(string_value(item[0])) > 2):
            s = string_value(item[0])
            if size == 1:
                b = to_cp437(s, warn=lambda ch: self.warn("W-CHAR", ch=ch))
                return b, len(b)
            if size != 1:
                raise AsmError("E-STRING", what=f"use db for long strings: {item[0].text}")
        if len(item) == 1 and item[0].text == "?":
            return b"\0" * size, 1
        v = Evaluator(self).eval(item)
        value = v.v
        if size == 4 and v.reloc and v.sym is not None and v.sym.kind in ("label", "proc", "var"):
            seg = self.seg_value(v.sym).v
            return (value & 0xFFFF).to_bytes(2, "little") + (seg & 0xFFFF).to_bytes(2, "little"), 1
        if size == 1:
            if self.final and not -256 < value < 256:
                raise AsmError("E-RANGE", value=value, bits=8)
        elif size == 2:
            if self.final and not -65536 < value < 65536:
                raise AsmError("E-RANGE", value=value, bits=16)
        return (value & ((1 << (8 * size)) - 1)).to_bytes(size, "little"), 1

    # ------------------------------------------------------------------ listing / source map
    def _record(self, st: Stmt, sec: Section, off: int, b: bytes, code=True) -> None:
        if not self.final:
            return
        seg = self.load_seg + sec.frame.para
        lin = ((seg << 4) + off) & 0xFFFFF
        self.listing.append((st.sl.file, st.sl.line, seg, off, b, st.sl.text))
        if code and b:
            self.addr_line.setdefault(lin, (st.sl.file, st.sl.line))
            self.line_addrs.setdefault((Path(st.sl.file).name.lower(), st.sl.line), []).append(lin)

    # ------------------------------------------------------------------ operands
    def operand(self, toks: list[Tok]) -> Operand:
        text = " ".join(t.text for t in toks)
        if not toks:
            raise AsmError("E-SYNTAX", what="missing operand")
        op = Operand("imm", text=text)
        toks = list(toks)
        # size / distance keywords
        while toks:
            t0 = toks[0].low
            if t0 in ("byte", "word", "dword", "qword", "near", "far") and len(toks) > 1 and toks[1].low == "ptr":
                if t0 in ("near",):
                    op.near = True
                elif t0 == "far":
                    op.far = True
                else:
                    op.size = {"byte": 1, "word": 2, "dword": 4, "qword": 8}[t0]
                toks = toks[2:]
            elif t0 == "short" and toks[0].kind == "id":
                op.short = True
                toks = toks[1:]
            elif t0 in ("near", "far") and len(toks) > 1 and toks[0].kind == "id":
                op.near, op.far = t0 == "near", t0 == "far"
                toks = toks[1:]
            else:
                break
        if not toks:
            raise AsmError("E-SYNTAX", what="missing operand")
        if len(toks) == 1 and toks[0].kind == "id":
            low = toks[0].low
            if low in REG8:
                return Operand("reg8", REG8[low], text=text)
            if low in REG16:
                return Operand("reg16", REG16[low], text=text)
            if low in SREG:
                return Operand("sreg", SREG[low], text=text)
        # segment override: es:[di]   cs:var   [es:di]
        if len(toks) > 2 and toks[0].low in SREG and toks[1].text == ":":
            op.seg = SREG[toks[0].low]
            toks = toks[2:]
        cleaned, regs, bracket = [], [], 0
        depth = 0
        for k, t in enumerate(toks):
            if t.kind == "op" and t.text == "[":
                depth += 1
                bracket += 1
                if k + 2 < len(toks) and toks[k + 1].low in SREG and toks[k + 2].text == ":":
                    op.seg = SREG[toks[k + 1].low]
                cleaned.append(Tok("op", "+"))
                cleaned.append(Tok("op", "("))
                continue
            if t.kind == "op" and t.text == "]":
                depth -= 1
                cleaned.append(Tok("op", ")"))
                continue
            if t.kind == "op" and t.text == ":" and depth > 0:
                continue
            if t.kind == "id" and depth > 0 and t.low in SREG and k + 1 < len(toks) and toks[k + 1].text == ":":
                continue
            if t.kind == "id" and (t.low in REG16 or t.low in REG8):
                if depth == 0:
                    raise AsmError("E-BAD-ADDR", what=text)
                if t.low not in ("bx", "bp", "si", "di"):
                    raise AsmError("E-BAD-REGS", regs=t.text)
                prev = cleaned[-1].text if cleaned else "("
                nxt = toks[k + 1].text if k + 1 < len(toks) else "]"
                if prev not in ("(", "+") or nxt not in ("]", "+", "-"):
                    raise AsmError("E-BAD-ADDR", what=text)
                regs.append(t.low)
                cleaned.append(Tok("num", "0"))
                continue
            cleaned.append(t)
        if cleaned and cleaned[0].text == "+":
            cleaned = cleaned[1:]
        val = Evaluator(self).eval(cleaned) if cleaned else Val(0)
        if bracket or val.mem or regs:
            rs = frozenset(regs)
            if len(regs) != len(rs) or (rs and rs not in RM_TABLE):
                raise AsmError("E-BAD-REGS", regs="+".join(regs))
            op.kind = "mem"
            op.regs = rs
            op.val = val
            if not op.size:
                op.size = val.size if val.size in (1, 2, 4, 8) else 0
            if op.seg is None and val.sym is not None and val.sym.section is not None:
                op.seg = self._override_for(val.sym.section, "bp" in rs)
            return op
        op.kind = "imm"
        op.val = val
        return op

    def _override_for(self, sec: Section, bp: bool) -> int | None:
        """Segment register to reach a label of *sec* (ASSUME), None when the default one does."""
        default = 2 if bp else 3
        if not self.assume:
            return None
        names = {sec.name.lower()}
        if self.com:
            return None

        def ok(r):
            v = self.assume.get(r)
            return v == "*" or v in names or (v is not None and self.sections.get(v) is not None
                                              and self.sections[v].frame is sec.frame)
        if ok(default):
            return None
        for r in (3, 0, 1, 2):
            if ok(r):
                return r
        return None

    # ------------------------------------------------------------------ encoding helpers
    def _imm(self, val: Val, bits: int, st: Stmt) -> bytes:
        v = val.v
        if self.final and val.known:
            lo = -(1 << (bits - 1)) if bits == 8 else -(1 << 16) + 1
            if bits == 8 and not -256 < v < 256:
                raise AsmError("E-RANGE", value=v, bits=8)
            if bits == 16 and not lo <= v < (1 << 16):
                raise AsmError("E-RANGE", value=v, bits=16)
        return (v & ((1 << bits) - 1)).to_bytes(bits // 8, "little")

    def _fits8(self, val: Val, st: Stmt, key: str) -> bool:
        if key in st.flags:
            return False
        if val.reloc or not val.known:
            st.flags.add(key)
            return False
        return -128 <= val.v <= 127

    def _modrm(self, reg: int, op: Operand, st: Stmt) -> bytes:
        if op.kind in ("reg8", "reg16", "sreg"):
            return bytes([0xC0 | (reg << 3) | op.reg])
        if op.kind != "mem":
            raise AsmError("E-BAD-OPERAND", op=op.text, name=st.op)
        disp = op.val.v if op.val else 0
        if not op.regs:
            return bytes([(reg << 3) | 6]) + (disp & 0xFFFF).to_bytes(2, "little")
        rm = RM_TABLE[op.regs]
        key = "disp16"
        if key in st.flags or (op.val and (op.val.reloc or not op.val.known)):
            if op.val and not op.val.known:
                st.flags.add(key)
            mod = 2
        elif disp == 0 and rm != 6:
            mod = 0
        elif -128 <= disp <= 127:
            mod = 1
        else:
            mod = 2
        b = bytes([(mod << 6) | (reg << 3) | rm])
        if mod == 1:
            b += (disp & 0xFF).to_bytes(1, "little")
        elif mod == 2:
            b += (disp & 0xFFFF).to_bytes(2, "little")
        return b

    def _seg_prefix(self, *ops: Operand) -> bytes:
        for op in ops:
            if op is not None and op.kind == "mem" and op.seg is not None:
                default = 2 if "bp" in op.regs else 3
                if op.seg != default:
                    return bytes([SEG_PREFIX[op.seg]])
        return b""

    @staticmethod
    def _w(op: Operand) -> int:
        return 1 if op.bits == 16 else 0

    def _size_of(self, a: Operand, b: Operand | None, st: Stmt) -> int:
        """Operation size in bits from the register / memory operands."""
        sizes = [o.bits for o in (a, b) if o is not None and o.kind in ("reg8", "reg16", "sreg")]
        msz = [o.size * 8 for o in (a, b) if o is not None and o.kind == "mem" and o.size]
        if sizes:
            if len(set(sizes)) > 1:
                raise AsmError("E-SIZE-MISMATCH", a=sizes[0], b=sizes[1])
            if msz and msz[0] != sizes[0]:
                raise AsmError("E-SIZE-MISMATCH", a=sizes[0], b=msz[0])
            return sizes[0]
        if msz:
            return msz[0]
        raise AsmError("E-SIZE-UNKNOWN")

    # ------------------------------------------------------------------ instructions
    def encode_text(self, st: Stmt, op: str, rest: str) -> None:
        sub = Stmt(st.sl, op=op, rest=rest, toks=tokenize(rest))
        sub.flags = st.flags
        self.instruction(sub, count=False)

    def instruction(self, st: Stmt, count: bool = True) -> None:
        sec = self._section()
        start = sec.loc
        ops = [self.operand(t) for t in split_commas(st.toks)] if st.toks else []
        name = st.op
        b = bytes(PREFIXES[p] for p in st.prefixes)
        if name in PREFIXES:
            body = bytes([PREFIXES[name]])
        else:
            body = self.encode(st, name, ops, start + len(b))
        out = b + body
        self._record(st, sec, start, out)
        sec.emit(out)
        if count:
            st.size = len(out)

    def _need(self, st: Stmt, ops, n) -> None:
        if len(ops) != n:
            raise AsmError("E-OPERANDS", name=st.op, n=n)

    def encode(self, st: Stmt, name: str, ops: list[Operand], addr: int) -> bytes:
        if name in SIMPLE:
            if ops:
                raise AsmError("E-OPERANDS", name=name, n=0)
            if name in I186:
                self.warn("W-186", name=name)
            return bytes(SIMPLE[name])
        if name in ("movs", "cmps", "stos", "lods", "scas"):
            sz = next((o.size for o in ops if o.kind == "mem" and o.size), 0)
            sz = sz or next((1 if o.kind == "reg8" else 2 for o in ops if o.kind in ("reg8", "reg16")), 0)
            if not sz:
                raise AsmError("E-SIZE-UNKNOWN")
            base = {"movs": 0xA4, "cmps": 0xA6, "stos": 0xAA, "lods": 0xAC, "scas": 0xAE}[name]
            pre = b""
            src = next((o for o in ops if o.kind == "mem" and "si" in o.regs), None)
            if src is not None and src.seg is not None and src.seg != 3:
                pre = bytes([SEG_PREFIX[src.seg]])
            return pre + bytes([base + (1 if sz == 2 else 0)])
        if name in ALU:
            return self.enc_alu(st, ALU[name], ops)
        if name == "mov":
            return self.enc_mov(st, ops)
        if name in SHIFT:
            return self.enc_shift(st, SHIFT[name], ops)
        if name in UNARY:
            if name == "imul" and len(ops) > 1:
                raise AsmError("E-NOT-SUPPORTED", name="imul with 2 or 3 operands (80186+)")
            self._need(st, ops, 1)
            a = ops[0]
            if a.kind == "imm":
                raise AsmError("E-BAD-OPERAND", op=a.text, name=name)
            bits = self._size_of(a, None, st)
            return self._seg_prefix(a) + bytes([0xF6 | (1 if bits == 16 else 0)]) + self._modrm(UNARY[name], a, st)
        if name in JCC:
            return self.enc_jcc(st, JCC[name], ops, addr)
        if name in LOOPS:
            self._need(st, ops, 1)
            return self.enc_short(st, LOOPS[name], ops[0], addr, can_grow=False)
        if name == "jmp":
            return self.enc_jmp(st, ops, addr)
        if name == "call":
            return self.enc_call(st, ops, addr)
        if name in ("ret", "retn", "retf"):
            far = name == "retf" or (name == "ret" and self.proc_stack and self.proc_stack[-1].far)
            if ops:
                n = ops[0].val.v if ops[0].kind == "imm" else 0
                return bytes([0xCA if far else 0xC2]) + (n & 0xFFFF).to_bytes(2, "little")
            return bytes([0xCB if far else 0xC3])
        if name == "test":
            return self.enc_test(st, ops)
        if name == "xchg":
            self._need(st, ops, 2)
            a, b = ops
            if a.kind == "imm" or b.kind == "imm" or a.kind == "sreg" or b.kind == "sreg":
                raise AsmError("E-BAD-OPERAND", op=(a if a.kind in ("imm", "sreg") else b).text, name=name)
            bits = self._size_of(a, b, st)
            if bits == 16 and a.kind == "reg16" and b.kind == "reg16" and (a.reg == 0 or b.reg == 0):
                return bytes([0x90 + (b.reg if a.reg == 0 else a.reg)])
            if a.kind == "mem" and b.kind == "mem":
                raise AsmError("E-MEM-MEM")
            reg, rm = (a, b) if a.kind != "mem" else (b, a)
            return self._seg_prefix(rm) + bytes([0x86 | (1 if bits == 16 else 0)]) + self._modrm(reg.reg, rm, st)
        if name in ("inc", "dec"):
            self._need(st, ops, 1)
            a = ops[0]
            n = 0 if name == "inc" else 1
            if a.kind == "reg16":
                return bytes([0x40 + n * 8 + a.reg])
            if a.kind not in ("reg8", "mem"):
                raise AsmError("E-BAD-OPERAND", op=a.text, name=name)
            bits = self._size_of(a, None, st)
            return self._seg_prefix(a) + bytes([0xFE | (1 if bits == 16 else 0)]) + self._modrm(n, a, st)
        if name == "push":
            self._need(st, ops, 1)
            a = ops[0]
            if a.kind == "reg16":
                return bytes([0x50 + a.reg])
            if a.kind == "sreg":
                return bytes([0x06 + a.reg * 8])
            if a.kind == "imm":
                self.warn("W-186", name="push immediate")
                if self._fits8(a.val, st, "push8"):
                    return bytes([0x6A, a.val.v & 0xFF])
                return bytes([0x68]) + self._imm(a.val, 16, st)
            if a.kind == "mem":
                if a.size not in (0, 2):
                    raise AsmError("E-SIZE-MISMATCH", a=16, b=a.size * 8)
                return self._seg_prefix(a) + bytes([0xFF]) + self._modrm(6, a, st)
            raise AsmError("E-REG16")
        if name == "pop":
            self._need(st, ops, 1)
            a = ops[0]
            if a.kind == "reg16":
                return bytes([0x58 + a.reg])
            if a.kind == "sreg":
                if a.reg == 1:
                    raise AsmError("E-CS-DEST")
                return bytes([0x07 + a.reg * 8])
            if a.kind == "mem":
                if a.size not in (0, 2):
                    raise AsmError("E-SIZE-MISMATCH", a=16, b=a.size * 8)
                return self._seg_prefix(a) + bytes([0x8F]) + self._modrm(0, a, st)
            raise AsmError("E-REG16")
        if name in ("lea", "lds", "les"):
            self._need(st, ops, 2)
            a, b = ops
            if a.kind != "reg16":
                raise AsmError("E-REG16")
            if b.kind != "mem":
                raise AsmError("E-NEED-MEM")
            opc = {"lea": 0x8D, "lds": 0xC5, "les": 0xC4}[name]
            return self._seg_prefix(b) + bytes([opc]) + self._modrm(a.reg, b, st)
        if name == "int":
            self._need(st, ops, 1)
            if ops[0].kind != "imm":
                raise AsmError("E-BAD-OPERAND", op=ops[0].text, name=name)
            n = ops[0].val.v & 0xFF
            return bytes([0xCC]) if n == 3 else bytes([0xCD, n])
        if name in ("aam", "aad"):
            base = 0xD4 if name == "aam" else 0xD5
            n = ops[0].val.v & 0xFF if ops and ops[0].kind == "imm" else 10
            return bytes([base, n])
        if name in ("in", "out"):
            self._need(st, ops, 2)
            acc, port = (ops[0], ops[1]) if name == "in" else (ops[1], ops[0])
            if acc.kind not in ("reg8", "reg16") or acc.reg != 0:
                raise AsmError("E-ACC")
            w = 1 if acc.kind == "reg16" else 0
            if port.kind == "reg16" and port.reg == 2:
                return bytes([(0xEC if name == "in" else 0xEE) + w])
            if port.kind == "imm" and 0 <= port.val.v <= 255:
                return bytes([(0xE4 if name == "in" else 0xE6) + w, port.val.v])
            raise AsmError("E-PORT")
        if name == "enter":
            self.warn("W-186", name=name)
            self._need(st, ops, 2)
            return bytes([0xC8]) + self._imm(ops[0].val, 16, st) + self._imm(ops[1].val, 8, st)
        raise AsmError("E-UNKNOWN-INSTR", name=name)

    def enc_alu(self, st, n, ops) -> bytes:
        self._need(st, ops, 2)
        a, b = ops
        if a.kind == "imm":
            raise AsmError("E-IMM-DEST")
        if a.kind == "sreg" or b.kind == "sreg":
            raise AsmError("E-BAD-OPERAND", op=(a if a.kind == "sreg" else b).text, name=st.op)
        if a.kind == "mem" and b.kind == "mem":
            raise AsmError("E-MEM-MEM")
        if b.kind == "imm":
            bits = self._size_of(a, None, st)
            w = 1 if bits == 16 else 0
            if a.kind in ("reg8", "reg16") and a.reg == 0 and not (w and self._fits8(b.val, st, "imm8")):
                return bytes([n * 8 + 4 + w]) + self._imm(b.val, bits, st)
            if w and self._fits8(b.val, st, "imm8"):
                return self._seg_prefix(a) + bytes([0x83]) + self._modrm(n, a, st) + bytes([b.val.v & 0xFF])
            return self._seg_prefix(a) + bytes([0x80 | w]) + self._modrm(n, a, st) + self._imm(b.val, bits, st)
        bits = self._size_of(a, b, st)
        w = 1 if bits == 16 else 0
        if b.kind == "mem":            # reg, mem
            return self._seg_prefix(b) + bytes([n * 8 + 2 + w]) + self._modrm(a.reg, b, st)
        return self._seg_prefix(a) + bytes([n * 8 + w]) + self._modrm(b.reg, a, st)

    def enc_test(self, st, ops) -> bytes:
        self._need(st, ops, 2)
        a, b = ops
        if a.kind == "imm":
            a, b = b, a
        if a.kind == "mem" and b.kind == "mem":
            raise AsmError("E-MEM-MEM")
        if b.kind == "imm":
            bits = self._size_of(a, None, st)
            w = 1 if bits == 16 else 0
            if a.kind in ("reg8", "reg16") and a.reg == 0:
                return bytes([0xA8 + w]) + self._imm(b.val, bits, st)
            return self._seg_prefix(a) + bytes([0xF6 | w]) + self._modrm(0, a, st) + self._imm(b.val, bits, st)
        bits = self._size_of(a, b, st)
        w = 1 if bits == 16 else 0
        reg, rm = (b, a) if b.kind != "mem" else (a, b)
        return self._seg_prefix(rm) + bytes([0x84 | w]) + self._modrm(reg.reg, rm, st)

    def enc_mov(self, st, ops) -> bytes:
        self._need(st, ops, 2)
        a, b = ops
        if a.kind == "imm":
            raise AsmError("E-IMM-DEST")
        if a.kind == "mem" and b.kind == "mem":
            raise AsmError("E-MEM-MEM")
        if a.kind == "sreg":
            if a.reg == 1:
                raise AsmError("E-CS-DEST")
            if b.kind == "imm":
                raise AsmError("E-IMM-SREG", sreg=a.text)
            if b.kind == "sreg":
                raise AsmError("E-BAD-OPERAND", op=b.text, name="mov")
            if b.kind == "reg8" or (b.kind == "mem" and b.size not in (0, 2)):
                raise AsmError("E-SIZE-MISMATCH", a=16, b=b.bits)
            return self._seg_prefix(b) + bytes([0x8E]) + self._modrm(a.reg, b, st)
        if b.kind == "sreg":
            if a.kind == "reg8" or (a.kind == "mem" and a.size not in (0, 2)):
                raise AsmError("E-SIZE-MISMATCH", a=a.bits, b=16)
            return self._seg_prefix(a) + bytes([0x8C]) + self._modrm(b.reg, a, st)
        if b.kind == "imm":
            if b.val.string is not None and len(b.val.string) > 2:
                raise AsmError("E-STRING", what=b.text)
            bits = self._size_of(a, None, st)
            w = 1 if bits == 16 else 0
            if a.kind in ("reg8", "reg16"):
                return bytes([0xB0 + w * 8 + a.reg]) + self._imm(b.val, bits, st)
            return self._seg_prefix(a) + bytes([0xC6 | w]) + self._modrm(0, a, st) + self._imm(b.val, bits, st)
        bits = self._size_of(a, b, st)
        w = 1 if bits == 16 else 0
        if a.kind in ("reg8", "reg16") and a.reg == 0 and b.kind == "mem" and not b.regs:
            return self._seg_prefix(b) + bytes([0xA0 + w]) + (b.val.v & 0xFFFF).to_bytes(2, "little")
        if b.kind in ("reg8", "reg16") and b.reg == 0 and a.kind == "mem" and not a.regs:
            return self._seg_prefix(a) + bytes([0xA2 + w]) + (a.val.v & 0xFFFF).to_bytes(2, "little")
        if b.kind == "mem":
            return self._seg_prefix(b) + bytes([0x8A + w]) + self._modrm(a.reg, b, st)
        return self._seg_prefix(a) + bytes([0x88 + w]) + self._modrm(b.reg, a, st)

    def enc_shift(self, st, n, ops) -> bytes:
        if len(ops) == 1:
            ops = ops + [Operand("imm", val=Val(1), text="1")]
        self._need(st, ops, 2)
        a, c = ops
        if a.kind not in ("reg8", "reg16", "mem"):
            raise AsmError("E-BAD-OPERAND", op=a.text, name=st.op)
        bits = self._size_of(a, None, st)
        w = 1 if bits == 16 else 0
        pre = self._seg_prefix(a)
        if c.kind == "reg8" and c.reg == 1:
            return pre + bytes([0xD2 | w]) + self._modrm(n, a, st)
        if c.kind == "imm":
            if c.val.known and c.val.v == 1 and "shift-imm" not in st.flags:
                return pre + bytes([0xD0 | w]) + self._modrm(n, a, st)
            if not c.val.known:
                st.flags.add("shift-imm")
            self.warn("W-186", name=f"{st.op} by {c.text}")
            return pre + bytes([0xC0 | w]) + self._modrm(n, a, st) + bytes([c.val.v & 0xFF])
        raise AsmError("E-SHIFT-COUNT")

    # ------------------------------------------------------------------ jumps
    def _target(self, op: Operand) -> Val:
        if op.kind != "imm" and not (op.kind == "mem" and not op.regs and op.val is not None
                                     and op.val.sym is not None and op.val.sym.kind in ("label", "proc")):
            raise AsmError("E-LABEL")
        return op.val

    def _same_frame(self, v: Val) -> bool:
        sec = v.sym.section if v.sym is not None else None
        return sec is None or self.cur is None or sec.frame is self.cur.frame

    def enc_short(self, st, opcode, op: Operand, addr: int, can_grow=True) -> bytes:
        v = self._target(op)
        disp = v.v - (addr + 2)
        if self.final and not -128 <= disp <= 127:
            raise AsmError("E-JUMP-RANGE", dist=disp, name=st.op)
        return bytes([opcode, disp & 0xFF])

    def enc_jcc(self, st, opcode, ops, addr) -> bytes:
        self._need(st, ops, 1)
        v = self._target(ops[0])
        if ops[0].short:
            return self.enc_short(st, opcode, ops[0], addr)
        if not st.long:
            disp = v.v - (addr + 2)
            if -128 <= disp <= 127 or not v.known:
                return bytes([opcode, disp & 0xFF])
            st.long = True
        if self.final:
            self.warn("W-JCC-LONG", name=ops[0].text)
        # opposite condition over a near jmp
        disp = v.v - (addr + 5)
        return bytes([opcode ^ 1, 3, 0xE9]) + (disp & 0xFFFF).to_bytes(2, "little")

    def enc_jmp(self, st, ops, addr) -> bytes:
        self._need(st, ops, 1)
        a = ops[0]
        if a.kind == "reg16":
            return bytes([0xFF]) + self._modrm(4, a, st)
        if a.kind == "mem" and (a.regs or a.val.sym is None or a.val.sym.kind == "var" or a.size):
            far = a.far or a.size == 4
            return self._seg_prefix(a) + bytes([0xFF]) + self._modrm(5 if far else 4, a, st)
        v = self._target(a)
        if a.far or (v.sym is not None and not self._same_frame(v)):
            seg = self.seg_value(v.sym).v if v.sym is not None else 0
            return bytes([0xEA]) + (v.v & 0xFFFF).to_bytes(2, "little") + (seg & 0xFFFF).to_bytes(2, "little")
        if a.short:
            return self.enc_short(st, 0xEB, a, addr)
        if not st.long and not a.near:
            disp = v.v - (addr + 2)
            if -128 <= disp <= 127 or not v.known:
                return bytes([0xEB, disp & 0xFF])
            st.long = True
        disp = v.v - (addr + 3)
        return bytes([0xE9]) + (disp & 0xFFFF).to_bytes(2, "little")

    def enc_call(self, st, ops, addr) -> bytes:
        self._need(st, ops, 1)
        a = ops[0]
        if a.kind == "reg16":
            return bytes([0xFF]) + self._modrm(2, a, st)
        if a.kind == "mem" and (a.regs or a.val.sym is None or a.val.sym.kind == "var" or a.size):
            far = a.far or a.size == 4
            return self._seg_prefix(a) + bytes([0xFF]) + self._modrm(3 if far else 2, a, st)
        v = self._target(a)
        far = a.far or (v.sym is not None and (v.sym.far or not self._same_frame(v)))
        if far and not a.near:
            seg = self.seg_value(v.sym).v if v.sym is not None else 0
            return bytes([0x9A]) + (v.v & 0xFFFF).to_bytes(2, "little") + (seg & 0xFFFF).to_bytes(2, "little")
        disp = v.v - (addr + 3)
        return bytes([0xE8]) + (disp & 0xFFFF).to_bytes(2, "little")

    # ------------------------------------------------------------------ result
    def _result(self, prog: Program) -> Program:
        prog.com = self.com
        prog.files = list(self.files)
        prog.errors = [d for d in self.diags if d.severity == "Error"]
        prog.warnings = [d for d in self.diags if d.severity != "Error"]
        if prog.errors or not self.final:
            return prog
        ls = self.load_seg
        end_para = 0
        for frame in self.frames:
            seg = ls + frame.para
            for sec in frame.sections:
                if sec.data:
                    prog.chunks.append((((seg << 4) + sec.base) & 0xFFFFF, bytes(sec.data)))
            end_para = max(end_para, frame.para + (frame.size + 15) // 16)
        prog.addr_line = dict(self.addr_line)
        prog.line_addrs = dict(self.line_addrs)
        prog.listing = list(self.listing)
        for sym in self.symbols.values():
            if sym.section is None:
                continue
            seg = ls + sym.section.frame.para
            if sym.kind == "var":
                prog.variables.append(VarInfo(sym.name, seg, sym.offset, sym.size or 1, sym.count,
                                              sym.file, sym.line))
            elif sym.kind in ("label", "proc"):
                prog.labels[sym.name] = (seg, sym.offset)
        prog.variables.sort(key=lambda v: (v.segment, v.offset))
        # entry point
        entry = None
        if self.entry_tokens:
            try:
                self.final = True
                entry = Evaluator(self).eval(self.entry_tokens)
            except AsmError as e:
                self._diag("Error", e.code, None, **e.args_)
                prog.errors = [d for d in self.diags if d.severity == "Error"]
                return prog
        if self.com:
            prog.entry_cs = prog.ds = prog.es = prog.ss = ls
            prog.entry_ip = entry.v if entry is not None else 0x100
            prog.sp = 0xFFFE
            prog.end_linear = ((ls + 0x1000) << 4) & 0xFFFFF
        else:
            psp = ls
            if entry is not None and entry.sym is not None and entry.sym.section is not None:
                prog.entry_cs = ls + entry.sym.section.frame.para
                prog.entry_ip = entry.v
            else:
                startup = self._startup_at
                code = startup[0] if startup else self._section_of_kind("code")
                if code is None and self.frames:
                    code = self.frames[0].sections[0]
                prog.entry_cs = ls + (code.frame.para if code else 0)
                prog.entry_ip = startup[1] if startup else (code.base if code else 0)
            prog.ds = prog.es = psp - 0x10
            stack = self._section_of_kind("stack")
            if stack is not None:
                prog.ss = ls + stack.frame.para
                prog.sp = (stack.base + max(stack.size, stack.stack_size)) & 0xFFFF
                if prog.sp == 0:
                    prog.sp = 0xFFFE
            else:
                prog.ss = ls + end_para
                prog.sp = 0x1000
                end_para += 0x100
                self._diag("Warning", "W-NOSTACK", SrcLine("", self.files[0], 1))
                prog.warnings = [d for d in self.diags if d.severity != "Error"]
            prog.end_linear = ((ls + end_para) << 4) & 0xFFFFF
        return prog


def assemble(text: str, filename: str = "main.asm", load_seg: int | None = None, include_dir=None,
             read_include=None) -> Program:
    """Assemble *text*. ``include`` files are read from *include_dir* (default: the folder of *filename*)."""
    folder = Path(include_dir) if include_dir else Path(filename).parent

    def reader(name: str):
        if read_include is not None:
            r = read_include(name)
            if r is not None:
                return r
        for cand in (folder / name, folder / Path(name).name):
            try:
                return cand.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
        from .includes import builtin_include
        return builtin_include(name)

    if load_seg is None:
        # EXE: the PSP takes the first 100h bytes of the load segment; the program starts after it
        load_seg = 0x0700
    asm = Assembler(load_seg=load_seg, read_include=reader)
    prog = asm.assemble(text, filename)
    if not prog.com and prog.ok:
        # Assembler laid the segments out from load_seg: move them behind the PSP (load_seg + 10h)
        asm2 = Assembler(load_seg=load_seg + 0x10, read_include=reader)
        prog = asm2.assemble(text, filename)
        prog.load_seg = load_seg
    return prog
