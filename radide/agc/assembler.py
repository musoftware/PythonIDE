"""RAD IDE's built-in Apollo Guidance Computer assembler ("mini-YUL").

An original, small assembler for the yaYUL source format (Block II basic instructions, extracodes and the
common pseudo-operations). It exists so AGC programs can be written, built and debugged inside RAD IDE with
nothing installed; big flight programs (Comanche055, Luminary099) use interpretive code and are assembled by
yaYUL from Virtual AGC (radide/agc/toolchain.py).

Source format (as in yaYUL): ``LABEL   OPCODE   OPERAND   # comment``. A label starts in column 1; ``#``
starts a comment; ``$FILE.agc`` includes another file. Numbers in address fields are octal (``12D`` is decimal),
``+n`` / ``-n`` alone is relative to the current location, ``SYM +n`` adds n words.

    prog = assemble_file(Path("MAIN.agc"))
    prog.ok, prog.errors, prog.rope (36 banks x 1024 words), prog.symbols, prog.line_of[("F", 2, 0)]
    prog.to_bin()     # yaYUL / yaAGC core-rope image (banks 2, 3, 0, 1, 4 ... 35, words << 1, big-endian)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import isa

FIXED_BANKS = 36
BANK_WORDS = 0o2000
ERASABLE_BANKS = 8

MESSAGES: dict[str, tuple[str, str]] = {
    "unknown_op": ("Unknown operator '{0}'", "عملية غير معروفة '{0}'"),
    "interp": ("Interpretive instruction '{0}' needs yaYUL (Tools > Apollo AGC > Virtual AGC Toolchain); the "
               "built-in assembler handles basic instructions and extracodes",
               "التعليمة التفسيرية '{0}' تحتاج yaYUL؛ المجمِّع المدمج يدعم التعليمات الأساسية والموسَّعة فقط"),
    "undefined": ("Undefined symbol '{0}'", "رمز غير معرَّف '{0}'"),
    "duplicate": ("Symbol '{0}' is already defined (line {1})", "الرمز '{0}' معرَّف من قبل (السطر {1})"),
    "bad_number": ("Bad number '{0}'", "رقم غير صالح '{0}'"),
    "bad_octal": ("'{0}' is not octal (write {0}D for decimal)", "'{0}' ليس رقماً ثمانياً (اكتب {0}D للعشري)"),
    "range": ("Value {0} does not fit in one AGC word", "القيمة {0} لا تتسع في كلمة واحدة"),
    "need_erasable": ("{0} needs an erasable address (below 2000 octal)", "{0} تحتاج عنواناً في الذاكرة المتغيرة"),
    "need_fixed": ("{0} needs a fixed-memory address", "{0} تحتاج عنواناً في الذاكرة الثابتة"),
    "other_bank": ("'{0}' is in fixed bank {1:o}, not reachable from bank {2:o} (use the fixed-fixed banks 2/3 "
                   "or DTCB / BANKCALL)", "'{0}' في البنك {1:o} ولا يمكن الوصول إليه من البنك {2:o}"),
    "ebank": ("'{0}' is in erasable bank E{1}, but EBANK= says E{2}", "'{0}' في البنك E{1} لكن EBANK= يقول E{2}"),
    "no_location": ("No location yet: start with SETLOC or BANK", "لا يوجد موقع بعد: ابدأ بـ SETLOC أو BANK"),
    "data_in_erasable": ("Erasable memory has no initial contents: only ERASE / EQUALS there",
                         "الذاكرة المتغيرة ليس لها محتوى ابتدائي: استخدم ERASE أو EQUALS فقط"),
    "erase_fixed": ("ERASE needs an erasable location (SETLOC below 4000)", "ERASE تحتاج موقعاً متغيراً"),
    "overwrite": ("Location {0} is assembled twice (first at line {1})", "الموقع {0} مجمَّع مرتين (أولاً في السطر {1})"),
    "bank_full": ("Fixed bank {0:o} is full", "البنك الثابت {0:o} ممتلئ"),
    "include": ("Cannot read include file '{0}'", "لا يمكن قراءة الملف المضمَّن '{0}'"),
    "no_extend": ("{0} is an extracode: put EXTEND before it", "{0} تعليمة موسَّعة: ضع EXTEND قبلها"),
    "operand": ("{0} needs an operand", "{0} تحتاج معاملاً"),
    "ignored": ("{0} is not supported by the built-in assembler and was ignored", "{0} غير مدعومة في المجمِّع المدمج"),
    "channel": ("Channel number {0} is out of range", "رقم القناة {0} خارج المدى"),
}


@dataclass
class Diag:
    severity: str            # "Error" | "Warning"
    file: str
    line: int                # 1-based
    code: str
    args: tuple = ()

    def text(self, lang: str = "en") -> str:
        en, ar = MESSAGES.get(self.code, (self.code, self.code))
        try:
            return (ar if lang == "ar" else en).format(*self.args)
        except Exception:  # noqa: BLE001
            return en


@dataclass(frozen=True)
class Loc:
    kind: str                # "E" erasable | "F" fixed | "N" number
    bank: int = 0
    off: int = 0

    @staticmethod
    def number(v: int) -> "Loc":
        return Loc("N", 0, v)

    @staticmethod
    def from_pseudo(n: int) -> "Loc":
        """Octal pseudo-address: below 4000 erasable (bank*400 + offset), else fixed (bank*2000 + offset)."""
        if n < 0o4000:
            return Loc("E", n // 0o400, n % 0o400)
        return Loc("F", n // BANK_WORDS, n % BANK_WORDS)

    def plus(self, n: int) -> "Loc":
        if self.kind == "N":
            return Loc("N", 0, self.off + n)
        size = 0o400 if self.kind == "E" else BANK_WORDS
        lin = self.bank * size + self.off + n
        return Loc(self.kind, lin // size, lin % size)

    def pseudo(self) -> int:
        if self.kind == "E":
            return self.bank * 0o400 + self.off
        if self.kind == "F":
            return self.bank * BANK_WORDS + self.off
        return self.off

    def __str__(self) -> str:
        if self.kind == "E":
            return f"E{self.bank},{0o1400 + self.off if self.bank > 2 else self.pseudo():04o}"
        if self.kind == "F":
            return f"{self.bank:02o},{self.cpu_address():04o}"
        return f"{self.off:o}"

    def cpu_address(self) -> int:
        """The 12-bit address the CPU sees for this location (assuming its bank is selected)."""
        if self.kind == "E":
            return self.bank * 0o400 + self.off if self.bank < 3 else 0o1400 + self.off
        if self.kind == "F":
            if self.bank == 2:
                return 0o4000 + self.off
            if self.bank == 3:
                return 0o6000 + self.off
            return 0o2000 + self.off
        return self.off & 0o7777


@dataclass
class Stmt:
    file: str
    line: int
    label: str
    op: str
    operand: str
    text: str


@dataclass
class Program:
    rope: list = field(default_factory=lambda: [[0] * BANK_WORDS for _ in range(FIXED_BANKS)])
    used: dict = field(default_factory=dict)        # (bank, off) -> (file, line)
    symbols: dict = field(default_factory=dict)     # name -> Loc
    symbol_lines: dict = field(default_factory=dict)  # name -> (file, line)
    line_of: dict = field(default_factory=dict)     # (kind, bank, off) -> (file, line)
    addr_of_line: dict = field(default_factory=dict)  # (file name lower, line) -> Loc
    listing: list = field(default_factory=list)     # (Loc | None, words, file, line, text)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    files: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def words(self) -> int:
        return len(self.used)

    def to_bin(self) -> bytes:
        """yaYUL / yaAGC rope image: banks in the order 2, 3, 0, 1, 4 ... 35; each word << 1, big-endian."""
        out = bytearray()
        for bank in [2, 3, 0, 1] + list(range(4, FIXED_BANKS)):
            for w in self.rope[bank]:
                v = (w & 0o77777) << 1
                out += bytes(((v >> 8) & 0xFF, v & 0xFF))
        return bytes(out)

    def listing_text(self) -> str:
        rows = []
        for loc, words, f, ln, text in self.listing:
            where = str(loc) if loc is not None else ""
            ws = " ".join(f"{w:05o}" for w in words)
            rows.append(f"{Path(f).name}:{ln:<5} {where:>10}  {ws:<12} {text}")
        return "\n".join(rows) + "\n"


def load_bin(data: bytes) -> list:
    """Rope (36 x 1024 words) from a yaYUL .bin image."""
    rope = [[0] * BANK_WORDS for _ in range(FIXED_BANKS)]
    order = [2, 3, 0, 1] + list(range(4, FIXED_BANKS))
    for i in range(0, min(len(data), FIXED_BANKS * BANK_WORDS * 2) - 1, 2):
        k = i // 2
        bank = order[k // BANK_WORDS]
        rope[bank][k % BANK_WORDS] = ((data[i] << 8 | data[i + 1]) >> 1) & 0o77777
    return rope


# ============================================================================== parsing
def split_line(raw: str) -> tuple[str, str, str]:
    """(label, operator, operand) of one yaYUL source line ('' parts when missing)."""
    code = raw.split("#", 1)[0].rstrip()
    if not code.strip():
        return "", "", ""
    label = ""
    if code[:1] not in (" ", "\t"):
        parts = code.split(None, 1)
        label = parts[0]
        code = parts[1] if len(parts) > 1 else ""
    parts = code.split(None, 1)
    op = parts[0] if parts else ""
    operand = parts[1].strip() if len(parts) > 1 else ""
    return label, op, operand


def read_sources(path: Path, texts: dict | None = None, _seen=None, _diags=None) -> tuple[list, list]:
    """Statements of *path* with its $includes expanded. *texts* overrides file contents (unsaved editors,
    keyed by lower-case file name)."""
    path = Path(path)
    seen = _seen if _seen is not None else set()
    diags = _diags if _diags is not None else []
    stmts: list[Stmt] = []
    key = str(path.resolve()).lower()
    if key in seen:
        return stmts, diags
    seen.add(key)
    text = None
    if texts:
        text = texts.get(path.name.lower())
    if text is None:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            diags.append(Diag("Error", path.name, 1, "include", (path.name,)))
            return stmts, diags
    for i, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if s.startswith("$"):
            name = s[1:].split("#", 1)[0].strip()
            inc = path.parent / name
            if not inc.exists():
                alt = next((p for p in path.parent.glob("*") if p.name.lower() == name.lower()), None)
                inc = alt or inc
            if not inc.exists() and not (texts and inc.name.lower() in texts):
                diags.append(Diag("Error", str(path), i, "include", (name,)))
                continue
            sub, _ = read_sources(inc, texts, seen, diags)
            stmts += sub
            continue
        label, op, operand = split_line(raw)
        if label or op:
            stmts.append(Stmt(str(path), i, label, op, operand, raw.rstrip()))
    return stmts, diags


# ============================================================================== assembler
class _Undefined(Exception):
    pass


class Assembler:
    def __init__(self):
        self.prog = Program()
        self.final = False
        self.loc: Loc | None = None
        self.bank_next: dict[int, int] = {}
        self.ebank = 0
        self.extend_pending = False
        self.symbols: dict[str, Loc] = {}
        self.sym_line: dict[str, tuple[str, int]] = {}

    # ------------------------------------------------------------------ diagnostics
    def err(self, st: Stmt, code: str, *args) -> None:
        if self.final:
            self.prog.errors.append(Diag("Error", st.file, st.line, code, args))

    def warn(self, st: Stmt, code: str, *args) -> None:
        if self.final:
            self.prog.warnings.append(Diag("Warning", st.file, st.line, code, args))

    # ------------------------------------------------------------------ values
    def number(self, tok: str, st: Stmt, octal: bool = True) -> int:
        """yaYUL's rule (GetOctOrDec): digits 0-7 only = octal; a trailing D or any 8 / 9 = decimal."""
        t = tok.strip()
        neg = t.startswith("-")
        t = t.lstrip("+-")
        if not t:
            raise ValueError(tok)
        if t[-1:] in ("D", "d") and t[:-1].isdigit():
            v = int(t[:-1])
        elif t.isdigit():
            v = int(t, 8) if (octal and all(c in "01234567" for c in t)) else int(t)
        else:
            raise ValueError(tok)
        return -v if neg else v

    def lookup(self, name: str) -> Loc:
        if name in self.symbols:
            return self.symbols[name]
        if name.upper() in isa.REGISTERS and name not in self.symbols:
            return Loc("E", 0, isa.REGISTERS[name.upper()])
        raise _Undefined(name)

    def expr(self, text: str, st: Stmt, relative: bool = True) -> Loc:
        """symbol | number | symbol +n | symbol -n | +n / -n (relative to the location)."""
        t = text.strip()
        toks = [x.replace(" ", "") for x in t.replace("+", " +").replace(" -", " -").split()] if t else []
        if not toks:
            raise ValueError(text)
        first = toks[0]
        base: Loc
        rest = toks[1:]
        if re.fullmatch(r"[+-]\d+[Dd]?", first) and relative:
            if self.loc is None:
                raise ValueError(text)
            base = self.loc.plus(self.number(first, st))
        elif re.fullmatch(r"[+-]?\d+[Dd]?", first):
            base = Loc.number(self.number(first, st))
        else:
            name = first.lstrip("+")
            base = self.lookup(name)
        for r in rest:
            if not re.fullmatch(r"[+-]\d+[Dd]?", r):
                raise ValueError(text)
            base = base.plus(self.number(r, st))
        return base

    def addr12(self, loc: Loc, st: Stmt, name: str, remote: bool = False) -> int:
        if loc.kind == "N":
            return loc.off & 0o7777
        if loc.kind == "E":
            if loc.bank >= 3 and loc.bank != self.ebank and not remote:
                self.warn(st, "ebank", name, loc.bank, self.ebank)
            return loc.cpu_address()
        if loc.bank not in (2, 3) and not remote:
            cur = self.loc.bank if (self.loc is not None and self.loc.kind == "F") else -1
            if cur != loc.bank:
                self.err(st, "other_bank", name, loc.bank, cur if cur >= 0 else 0)
        return loc.cpu_address()

    # ------------------------------------------------------------------ emission
    def emit(self, st: Stmt, words: list[int]) -> None:
        if self.loc is None:
            self.err(st, "no_location")
            return
        if self.loc.kind != "F":
            self.err(st, "data_in_erasable")
            return
        start = self.loc
        for w in words:
            b, o = self.loc.bank, self.loc.off
            if b >= FIXED_BANKS:
                self.err(st, "bank_full", b)
                break
            if self.final:
                prev = self.prog.used.get((b, o))
                if prev is not None:
                    self.err(st, "overwrite", str(self.loc), prev[1])
                self.prog.rope[b][o] = w & 0o77777
                self.prog.used[(b, o)] = (st.file, st.line)
                self.prog.line_of[("F", b, o)] = (st.file, st.line)
            self.bank_next[b] = max(self.bank_next.get(b, 0), o + 1)
            if o + 1 >= BANK_WORDS:
                self.loc = Loc("F", b + 1, 0)
                if len(words) > 1 and self.final:
                    self.err(st, "bank_full", b)
            else:
                self.loc = Loc("F", b, o + 1)
        if self.final:
            self.prog.listing.append((start, list(words), st.file, st.line, st.text))
            self.prog.addr_of_line[(Path(st.file).name.lower(), st.line)] = start

    def define(self, name: str, loc: Loc, st: Stmt) -> None:
        old = self.symbols.get(name)
        if old is not None and old != loc and self.sym_line.get(name) != (st.file, st.line):
            self.err(st, "duplicate", name, self.sym_line.get(name, ("", 0))[1])
            return
        self.symbols[name] = loc
        self.sym_line[name] = (st.file, st.line)

    # ------------------------------------------------------------------ passes
    def run(self, stmts: list[Stmt]) -> Program:
        prev = None
        for _ in range(6):
            self._pass(stmts)
            snap = dict(self.symbols)
            if snap == prev:
                break
            prev = snap
        self.final = True
        self._pass(stmts)
        self.prog.symbols = dict(self.symbols)
        self.prog.symbol_lines = dict(self.sym_line)
        return self.prog

    def _pass(self, stmts: list[Stmt]) -> None:
        self.loc = None
        self.bank_next = {}
        self.ebank = 0
        self.extend_pending = False
        for st in stmts:
            try:
                self._stmt(st)
            except _Undefined as e:
                self.err(st, "undefined", str(e))
                op = st.op.upper()
                if op not in ("EQUALS", "=", "SETLOC", "EBANK=", "SBANK=", "BANK", "BLOCK", "ERASE") \
                        and self.loc is not None and self.loc.kind == "F":
                    self.extend_pending = False
                    self.emit(st, [0] * (2 if op in ("2DEC", "2CADR", "2FCADR", "2DEC*", "2BCADR") else 1))
            except ValueError as e:
                self.err(st, "bad_number", str(e))

    def _stmt(self, st: Stmt) -> None:
        op = st.op.upper()
        operand = st.operand
        label = st.label
        # ---------------------------------------------------- symbol definitions
        if op in ("EQUALS", "="):
            if not label:
                return
            if not operand:
                if self.loc is None:
                    self.err(st, "no_location")
                    return
                self.define(label, self.loc, st)
                return
            try:
                self.define(label, self.expr(operand, st), st)
            except _Undefined:
                if self.final:
                    raise
            return
        if op == "ERASE":
            if self.loc is None or self.loc.kind != "E":
                self.err(st, "erase_fixed")
                return
            n = 0
            if operand:
                tok = operand.split()[0]
                if re.fullmatch(r"[+]?\d+[Dd]?", tok):
                    n = self.number(tok.lstrip("+"), st)
            if label:
                self.define(label, self.loc, st)
            self.loc = self.loc.plus(n + 1)
            return
        if label and op not in ("SETLOC", "BANK", "BLOCK"):
            if self.loc is None:
                self.err(st, "no_location")
            else:
                self.define(label, self.loc, st)
        if not op:
            return
        # ---------------------------------------------------- location control
        if op == "SETLOC":
            loc = self.expr(operand, st, relative=False)
            self.loc = Loc.from_pseudo(loc.off) if loc.kind == "N" else loc
            if label:
                self.define(label, self.loc, st)
            return
        if op in ("BANK", "BLOCK"):
            if operand:
                b = self.number(operand.split()[0], st)
            elif self.loc is not None and self.loc.kind == "F":
                b = self.loc.bank
            else:
                b = 2
            self.loc = Loc("F", b, self.bank_next.get(b, 0))
            if label:
                self.define(label, self.loc, st)
            return
        if op == "EBANK=":
            try:
                loc = self.expr(operand, st, relative=False)
                self.ebank = loc.bank if loc.kind == "E" else (loc.off // 0o400) & 7
            except _Undefined:
                if self.final:
                    raise
            return
        if op in ("SBANK=", "COUNT", "COUNT*", "CHECK=", "SECSIZ", "SUBRO", "MEMORY", "LOC"):
            return
        if op == "BNKSUM":
            self.warn(st, "ignored", op)
            return
        # ---------------------------------------------------- data
        if op == "OCT":
            v = self.number(operand.split()[0], st) if operand else 0
            if abs(v) > 0o77777:
                self.err(st, "range", operand)
            self.emit(st, [(~(-v) & 0o77777) if v < 0 else v & 0o77777])
            return
        if op in ("DEC", "DEC*", "2DEC", "2DEC*"):
            self.emit(st, self._dec(operand, st, op.startswith("2")))
            return
        if op in ("CADR", "FCADR", "ECADR", "GENADR", "ADRES", "REMADR", "BBCON", "BBCON*", "CADR*", "XCADR",
                  "2CADR", "2FCADR", "2BCADR"):
            self.emit(st, self._adr(op, operand, st))
            return
        if op in ("MM",):
            self.emit(st, [int(operand.split()[0]) & 0o77777 if operand else 0])
            return
        if op in ("VN", "NV"):
            t = operand.split()[0] if operand else "0"
            v = int(t) if t.isdigit() else 0
            self.emit(st, [((v // 100) << 7) + v % 100])
            return
        # ---------------------------------------------------- instructions
        if op in isa.IMPLIED:
            ext, word = isa.IMPLIED[op]
            if op == "NOOP" and self.loc is not None and self.loc.kind == "F":
                word = 0o10000 + self.loc.plus(1).cpu_address()          # TCF +1 in fixed memory
            if ext and not self.extend_pending:
                self.warn(st, "no_extend", op)
            self.emit(st, [word])
            self.extend_pending = op == "EXTEND"
            return
        if op == "INDEX" and self.extend_pending:
            self._instr(st, op, operand, (True, 0o50000, "addr"))
            self.extend_pending = True                 # EXTEND carries over INDEX
            return
        if op in isa.BASIC or op in isa.EXTRACODES:
            spec = isa.EXTRACODES.get(op) or isa.BASIC[op]
            if op in isa.BASIC and op in isa.EXTRACODES:
                spec = isa.EXTRACODES[op] if self.extend_pending else isa.BASIC[op]
            if spec[0] and not self.extend_pending:
                self.warn(st, "no_extend", op)
            self._instr(st, op, operand, spec)
            self.extend_pending = False
            return
        if op in isa.INTERPRETIVE or (op.split(",")[0] in isa.INTERPRETIVE):
            self.err(st, "interp", op)
            if self.loc is not None and self.loc.kind == "F":
                self.emit(st, [0])
            return
        if op in isa.PSEUDO_OPS:
            self.warn(st, "ignored", op)
            return
        self.err(st, "unknown_op", st.op)
        if self.loc is not None and self.loc.kind == "F":
            self.emit(st, [0])

    def _instr(self, st: Stmt, op: str, operand: str, spec) -> None:
        _ext, base, kind = spec
        if not operand:
            self.err(st, "operand", op)
            self.emit(st, [base])
            return
        if kind == "chan":
            ch = self.expr(operand, st, relative=False)
            n = ch.off if ch.kind == "N" else ch.pseudo()
            if not 0 <= n <= 0o777:
                self.err(st, "channel", n)
            self.emit(st, [base | (n & 0o777)])
            return
        loc = self.expr(operand, st)
        name = operand.split()[0]
        a = self.addr12(loc, st, name)
        if kind == "dp":
            a = (a + 1) & 0o7777
            if op in ("DAS", "DXCH") and a >= 0o2000:
                self.err(st, "need_erasable", op)
        elif kind == "e10":
            if a >= 0o2000:
                self.err(st, "need_erasable", op)
            a &= 0o1777
        elif kind == "fixed":
            if a < 0o2000:
                self.err(st, "need_fixed", op)
        self.emit(st, [(base + a) & 0o77777])

    def _dec(self, operand: str, st: Stmt, double: bool) -> list[int]:
        toks = operand.replace("B ", "B").replace("E ", "E").split()
        if not toks:
            raise ValueError(operand)
        num = toks[0]
        scale = 0
        exp = 0
        for t in toks[1:]:
            if re.fullmatch(r"[Bb][+-]?\d+", t):
                scale = int(t[1:])
            elif re.fullmatch(r"[Ee][+-]?\d+", t):
                exp = int(t[1:])
        m = re.fullmatch(r"([+-]?)(\d*\.?\d*)(?:[Ee]([+-]?\d+))?", num)
        if not m or m.group(2) in ("", "."):
            raise ValueError(num)
        neg = m.group(1) == "-"
        if m.group(3):
            exp += int(m.group(3))
        is_int = "." not in m.group(2) and not scale and not exp
        x = float(m.group(2)) * (10 ** exp) * (2 ** scale)
        if double:
            mag = int(m.group(2)) if is_int else int(round(x * (1 << 28)))
            if mag > (1 << 28) - 1:
                self.err(st, "range", num)
                mag = (1 << 28) - 1
            hi, lo = mag >> 14, mag & 0o37777
            if neg:
                return [(~hi) & 0o77777, (~lo) & 0o77777]
            return [hi, lo]
        mag = int(m.group(2)) if is_int else int(round(x * (1 << 14)))
        if mag > 0o37777:
            self.err(st, "range", num)
            mag = 0o37777
        return [(~mag) & 0o77777 if neg else mag]

    def _adr(self, op: str, operand: str, st: Stmt) -> list[int]:
        loc = self.expr(operand, st, relative=False)
        if op in ("ECADR",):
            return [loc.pseudo() & 0o3777 if loc.kind == "E" else loc.off & 0o77777]
        if op in ("CADR", "FCADR", "CADR*", "XCADR"):
            if loc.kind == "F":
                return [(loc.bank * BANK_WORDS + loc.off) & 0o77777]
            return [loc.cpu_address()]
        bb = ((loc.bank & 0o37) << 10 | self.ebank) if loc.kind == "F" else self.ebank
        if op in ("BBCON", "BBCON*"):
            return [bb & 0o77777]
        g = self.addr12(loc, st, operand.split()[0], remote=True)
        if op in ("2CADR", "2FCADR", "2BCADR"):
            return [g, bb & 0o77777]
        return [g]


def assemble(stmts: list[Stmt], diags: list | None = None) -> Program:
    a = Assembler()
    prog = a.run(stmts)
    if diags:
        prog.errors = [d for d in diags if d.severity == "Error"] + prog.errors
    files = []
    for s in stmts:
        if s.file not in files:
            files.append(s.file)
    prog.files = files
    return prog


def assemble_file(path: Path, texts: dict | None = None) -> Program:
    stmts, diags = read_sources(Path(path), texts)
    return assemble(stmts, diags)


def assemble_text(text: str, name: str = "MAIN.agc", folder: Path | None = None) -> Program:
    folder = Path(folder) if folder else Path(".")
    return assemble_file(folder / name, {name.lower(): text})


__all__ = ["Assembler", "Diag", "Loc", "Program", "Stmt", "assemble", "assemble_file", "assemble_text",
           "load_bin", "read_sources", "split_line"]
