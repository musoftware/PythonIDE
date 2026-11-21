"""Assembly IntelliSense services (no Qt): completions, signature help, hover, Go to Definition, Find References,
outline and folding ranges for NASM, MASM, FASM and GAS (AT&T and Intel syntax).

Every function takes the editor text, a 0-based (line, col) and the file path; the dialect comes from
``index.detect_dialect`` (plugin hint > project setting > file extension > the text itself).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import apis, directives, isa, snippets
from .index import (Module, Sym, abi_of, code_bits, detect_dialect, gas_syntax, is_asm_path, mask, parse,
                    parse_file, project_files, resolve_include)

try:                                    # the IDE's completion type (plain fallback keeps this module standalone)
    from ..languages.base import Completion as _BaseCompletion
except Exception:  # noqa: BLE001
    @dataclass
    class _BaseCompletion:              # type: ignore[no-redef]
        name: str
        kind: str = ""
        detail: str = ""


@dataclass
class AsmCompletion(_BaseCompletion):
    """A completion item with the extra fields radide/monaco_editor.py passes to Monaco."""
    doc: str = ""                       # markdown documentation
    insert: str = ""                    # text inserted instead of the name
    snippet: bool = False               # insert is a VS Code snippet
    sort: str = ""                      # sort key
    edits: list = field(default_factory=list)   # additional edits: [{"range": [l1, c1, l2, c2], "text": ...}]


WORD_RE = {
    "nasm": r"[%.?@A-Za-z_][\w.?@$#~]*",
    "masm": r"[.@?A-Za-z_][\w.@?$]*",
    "fasm": r"[.?@A-Za-z_][\w.?@$#~]*",
    "gas": r"[%.A-Za-z_][\w.$]*",
}
CALL_MNEMONICS = {"call", "jmp", "loop", "loope", "loopne", "loopz", "loopnz", "jcxz", "jecxz", "jrcxz"}
INVOKE_WORDS = {"invoke", "cinvoke", "stdcall", "ccall", "fastcall", "cinvoke64"}
SIZE_WORDS = {"nasm": ["byte", "word", "dword", "qword", "tword", "oword", "yword", "zword", "rel", "abs", "strict"],
              "masm": ["byte ptr", "word ptr", "dword ptr", "qword ptr", "xmmword ptr", "ymmword ptr", "offset", "addr",
                       "sizeof", "lengthof", "type"],
              "fasm": ["byte", "word", "dword", "qword", "tword", "dqword", "yword", "rva"],
              "gas": []}
REF_LINKS = {"isa": isa.SDM_URL}
KIND_LABEL = {"label": "label", "local": "local label", "proc": "procedure", "macro": "macro", "const": "constant",
              "data": "variable", "struct": "structure", "field": "structure field", "section": "section",
              "extern": "external symbol", "var": "local variable", "param": "parameter"}
COMPLETION_KIND = {"label": "function", "proc": "function", "local": "method", "macro": "class", "const": "property",
                   "data": "variable", "struct": "class", "field": "property", "extern": "module", "var": "variable",
                   "param": "param", "section": "module"}


def _tr(text: str) -> str:
    try:
        from .. import i18n
        return i18n.tr(text)
    except Exception:  # noqa: BLE001
        return text


# ============================================================================ the context of one request
class Ctx:
    def __init__(self, code: str, line: int, col: int, path=None, plugin=None, dialect: str | None = None):
        self.code = code
        self.line = line
        self.col = col
        self.path = Path(str(path)) if path else None
        self.dialect = dialect or detect_dialect(self.path, code, plugin)
        self.case = self.dialect != "masm"
        self.att = self.dialect == "gas" and gas_syntax(code) == "att"
        self.lines = code.split("\n")
        self.masked = mask(code, self.dialect)
        self.mod = parse(code, self.dialect, str(self.path) if self.path else "")
        self.bits = code_bits(code, self.dialect)
        self.abi = abi_of(code, self.dialect, self.path)
        if self.abi in ("win64", "sysv"):
            self.bits = 64
        elif self.abi == "x86":
            self.bits = 32
        self._others: list[tuple[Path, Module, str]] | None = None

    # ------------------------------------------------------------ text helpers
    def cur(self) -> str:
        return self.lines[self.line] if 0 <= self.line < len(self.lines) else ""

    def cur_masked(self) -> str:
        return self.masked[self.line] if 0 <= self.line < len(self.masked) else ""

    def in_comment_or_string(self) -> bool:
        raw = self.cur()[:self.col]
        msk = self.cur_masked()[:self.col]
        return raw.rstrip() != msk.rstrip() and raw[len(msk.rstrip()):].strip() != ""

    def word_at(self, line: int | None = None, col: int | None = None) -> tuple[str, int, int]:
        line = self.line if line is None else line
        col = self.col if col is None else col
        text = self.lines[line] if 0 <= line < len(self.lines) else ""
        for m in re.finditer(WORD_RE[self.dialect], text):
            if m.start() <= col <= m.end():
                return m.group(), m.start(), m.end()
        return "", col, col

    def word_before(self) -> str:
        m = re.search("(" + WORD_RE[self.dialect] + r")$", self.cur()[:self.col])
        return m.group(1) if m else ""

    def eq(self, a: str, b: str) -> bool:
        return a == b if self.case else a.lower() == b.lower()

    # ------------------------------------------------------------ project modules
    def others(self) -> list[tuple[Path, Module, str]]:
        if self._others is None:
            out: list[tuple[Path, Module, str]] = []
            seen: set[str] = set()
            me = ""
            if self.path is not None:
                try:
                    me = str(self.path.resolve()).lower()
                except OSError:
                    me = str(self.path).lower()
                seen.add(me)
            todo: list[tuple[Path, int]] = []
            if self.path is not None:
                for name, _l in self.mod.includes:
                    f = resolve_include(name, self.path)
                    if f is not None:
                        todo.append((f, 1))
                todo += [(p, 0) for p in project_files(self.path)]
            while todo and len(out) < 300:
                p, depth = todo.pop(0)
                try:
                    key = str(p.resolve()).lower()
                except OSError:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                same = p.suffix.lower() in (".inc", ".mac", ".asminc", ".ash") or self.dialect != "gas"
                r = parse_file(p, self.dialect if same and p.suffix.lower() != ".s" else None)
                if r is None:
                    continue
                out.append((p, r[0], r[1]))
                if depth < 3:
                    for name, _l in r[0].includes:
                        f = resolve_include(name, p)
                        if f is not None:
                            todo.append((f, depth + 1))
            self._others = out
        return self._others

    def all_modules(self):
        yield (self.path, self.mod, self.code)
        yield from self.others()

    def all_symbols(self):
        for _p, m, _t in self.all_modules():
            yield from m.symbols

    def scope_label(self, line: int | None = None) -> str:
        """The global label (or MASM / FASM procedure) the line belongs to - the parent of '.local' labels."""
        line = self.line if line is None else line
        best = ""
        for s in self.mod.symbols:
            if s.line > line:
                break
            if s.kind in ("label", "proc") and (s.end_line < 0 or s.end_line >= line or self.dialect != "masm"):
                best = s.name
        return best

    def find(self, word: str, line: int | None = None) -> list[Sym]:
        """Definitions of *word*: local labels resolved against the enclosing label, then everything else."""
        if not word:
            return []
        line = self.line if line is None else line
        cands: list[Sym] = []
        w = word.lstrip("%$") if self.dialect == "gas" else word
        if w.startswith(".") and not w.startswith(".L") and self.dialect in ("nasm", "fasm"):
            full = self.scope_label(line) + w
            cands = [s for s in self.mod.symbols if s.kind in ("local", "field") and self.eq(s.full, full)]
            if cands:
                return cands
        scope = self.scope_label(line)
        local_hits = [s for s in self.mod.symbols if s.kind in ("var", "param", "local") and self.eq(s.name, w)
                      and (not s.parent or self.eq(s.parent, scope) or s.kind == "local" and self.dialect == "gas")]
        if local_hits:
            return local_hits
        for s in self.all_symbols():
            if s.kind in ("var", "param"):
                continue
            if self.eq(s.full, w) or (s.kind not in ("local", "field") and self.eq(s.name, w)):
                cands.append(s)
        # a definition beats the extern / PROTO that declares it
        real = [s for s in cands if s.kind != "extern"]
        return real or cands


# ============================================================================ completions
def _ins_doc(ins: isa.Instr) -> str:
    out = [f"**{ins.name.upper()}** - {isa.CATEGORY_TITLES.get(ins.category, ins.category)}", "", ins.doc, ""]
    if ins.forms:
        out.append(f"{_tr('Operands')}: `" + "` | `".join(ins.forms) + "`  ")
    out.append(f"{_tr('Flags')}: {isa.flags_text(ins.flags)}  ")
    if ins.bits:
        out.append(_tr("Not available in 64-bit mode.") + "  ")
    out.append(f"[{_tr('Intel SDM')}]({isa.SDM_URL})")
    return "\n".join(out)


def _sym_detail(s: Sym) -> str:
    d = KIND_LABEL.get(s.kind, s.kind)
    if s.detail and s.detail not in ("label",):
        d += f"  {s.detail}"
    return d[:100]


def completions(code: str, line: int, col: int, path=None, plugin=None, dialect: str | None = None
                ) -> list[AsmCompletion]:
    """Completion items at (line, col). Items are pre-filtered by the first character(s) of the word being typed
    (Monaco asks again for each new word and filters the rest itself) and the program's own names, macros and
    snippets come first, so a capped list never loses them."""
    ctx = Ctx(code, line, col, path, plugin, dialect)
    items = _completions(ctx)
    word = ctx.word_before()
    if word and "." not in word[1:]:
        key = word[:2].lower() if word[0] in "%." and len(word) > 1 else word[:1].lower()
        items = [c for c in items if c.name.lower().startswith(key)]
    first = [c for c in items if c.kind in ("snippet", "class") or c.sort.startswith("0")]
    rest = [c for c in items if not (c.kind in ("snippet", "class") or c.sort.startswith("0"))]
    return first + sorted(rest, key=lambda c: c.sort or "4" + c.name)


def _completions(ctx: Ctx) -> list[AsmCompletion]:
    col = ctx.col
    if ctx.in_comment_or_string():
        return _include_completions(ctx)
    cur = ctx.cur()[:col]
    word = ctx.word_before()
    pre = cur[:len(cur) - len(word)]
    # strip a leading label "name:" so "lbl: mov" is seen as a mnemonic position
    stmt = re.sub(r"^\s*" + WORD_RE[ctx.dialect] + r"\s*::?(?!=)", "", pre) if re.match(
        r"^\s*" + WORD_RE[ctx.dialect] + r"\s*::?(?!=)", pre) else pre
    tokens = stmt.split()
    out: list[AsmCompletion] = []
    seen: set[str] = set()

    def add(c: AsmCompletion):
        key = c.name if ctx.case else c.name.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(c)

    # ---------------------------------------------------- member access: POINT.x  area.left  [ebx].RECT2.left
    if "." in word[1:] and not word.startswith("%"):
        head = word[:word.rindex(".")]
        for c in _member_completions(ctx, head):
            add(c)
        if out:
            return out
    if not tokens:                                   # mnemonic / directive position
        for c in _mnemonic_completions(ctx, word):
            add(c)
        return out
    mn = tokens[0].lower()
    first_operand = len(tokens) == 1 and "," not in stmt
    if mn in ("%include", "include", ".include", "includelib"):
        return _include_completions(ctx)
    if mn in ("extern", "global", "extrn", "public", ".globl", ".global", ".extern", "externdef"):
        for c in _api_completions(ctx, auto_extern=False):
            add(c)
        for c in _symbol_completions(ctx, ("label", "proc", "data")):
            add(c)
        return out
    if mn in INVOKE_WORDS and first_operand or (mn in CALL_MNEMONICS or mn.startswith("j")) and first_operand:
        for c in _symbol_completions(ctx, ("proc", "label", "local", "extern")):
            add(c)
        if mn in INVOKE_WORDS or mn == "call" or mn == "jmp":
            for c in _api_completions(ctx, auto_extern=(mn == "call" and ctx.dialect == "nasm")):
                add(c)
        return out
    macro = _macro_named(ctx, tokens[0])
    if mn in INVOKE_WORDS or macro is not None or isa.instruction(mn, ctx.att) is not None or \
            directives.directive(mn, ctx.dialect) is not None or len(tokens) >= 1:
        for c in _operand_completions(ctx, word, mn):
            add(c)
    return out


def _mnemonic_completions(ctx: Ctx, word: str) -> list[AsmCompletion]:
    out: list[AsmCompletion] = []
    w = word.lower()
    if not (w.startswith("%") and ctx.dialect == "nasm"):
        for name, ins in isa.INSTRUCTIONS.items():
            if ctx.bits == 64 and ins.bits == "16/32":
                continue
            if ctx.bits == 16 and ins.category in ("avx", "avx2", "fma", "bmi", "sse41", "sse42", "aes"):
                continue
            out.append(AsmCompletion(name, "keyword", isa.CATEGORY_TITLES.get(ins.category, ins.category) +
                                     (" - " + ins.doc[:60] if len(ins.doc) < 200 else ""), _ins_doc(ins),
                                     sort=("1" if ins.category in ("data", "arith", "logic", "control", "cond", "stack",
                                                                   "shift") else "3") + name))
        if ctx.att:
            for base in isa.ATT_SUFFIXED:
                for suf, size in isa.ATT_SUFFIX.items():
                    if ctx.bits != 64 and suf == "q":
                        continue
                    ins = isa.INSTRUCTIONS.get(base)
                    if ins is not None:
                        out.append(AsmCompletion(base + suf, "keyword", f"{base.upper()} ({size} operands)",
                                                 _ins_doc(ins), sort="1" + base + suf))
    for name, doc in directives.DIRECTIVES.get(ctx.dialect, {}).items():
        if w.startswith("%") and not name.startswith("%"):
            continue
        out.append(AsmCompletion(name, "statement", doc[:80], f"**{name}** ({directives.DIALECT_NAMES[ctx.dialect]})"
                                 f"\n\n{doc}\n\n[{_tr('Manual')}]({directives.DOC_URLS[ctx.dialect]})",
                                 sort="2" + name.lstrip(".%")))
    for s in ctx.all_symbols():
        if s.kind == "macro":
            out.append(AsmCompletion(s.name, "class", "macro " + ", ".join(s.params), _symbol_doc(ctx, s), sort="0" +
                                     s.name))
    for prefix, desc, body in snippets.snippets(ctx.dialect, ctx.abi, ctx.att):
        out.append(AsmCompletion(prefix, "snippet", desc + " (snippet)", "```asm\n" + body + "\n```", insert=body,
                                 snippet=True, sort="~" + prefix))
    return out


def _operand_completions(ctx: Ctx, word: str, mn: str) -> list[AsmCompletion]:
    out: list[AsmCompletion] = []
    pct = ctx.att or word.startswith("%")
    for name in isa.registers_for(ctx.bits):
        r = isa.REGISTERS[name]
        label = ("%" + name) if pct and ctx.dialect == "gas" else name
        if ctx.att and not word.startswith("%") and word:
            continue                 # AT&T: registers only after %
        out.append(AsmCompletion(label, "variable", f"register ({r.size}-bit)", r.doc, sort="2" + name))
    if not word.startswith("%"):
        for sz in SIZE_WORDS.get(ctx.dialect, []):
            out.append(AsmCompletion(sz, "keyword", "size / address operator", sort="3" + sz))
        out += _symbol_completions(ctx, ("data", "const", "label", "proc", "local", "struct", "extern", "var", "param"))
        if mn in INVOKE_WORDS:
            out += _api_completions(ctx, auto_extern=False)
    return out


def _symbol_completions(ctx: Ctx, kinds: tuple[str, ...]) -> list[AsmCompletion]:
    out: list[AsmCompletion] = []
    scope = ctx.scope_label()
    for s in ctx.all_symbols():
        if s.kind not in kinds:
            continue
        if s.kind in ("var", "param") and not ctx.eq(s.parent, scope):
            continue
        if s.kind == "local":
            same_scope = s.file == (str(ctx.path) if ctx.path else "") and ctx.eq(s.parent, scope)
            if ctx.dialect == "gas":
                name = s.name
            elif same_scope and s.name.startswith("."):
                name = s.name
            else:
                name = s.full
                if s.file != (str(ctx.path) if ctx.path else "") and ctx.dialect == "masm":
                    continue
        else:
            name = s.full if s.kind == "field" else s.name
        api = apis.lookup(s.name) if s.kind == "extern" else None
        detail = (api.signature() if api else _sym_detail(s))
        out.append(AsmCompletion(name, COMPLETION_KIND.get(s.kind, "variable"), detail,
                                 _api_doc(ctx, api) if api else _symbol_doc(ctx, s),
                                 sort=("0" if s.kind in ("local", "var", "param") else "1") + name))
    return out


def _api_completions(ctx: Ctx, auto_extern: bool) -> list[AsmCompletion]:
    out: list[AsmCompletion] = []
    known = {k.lower() for k in ctx.mod.externs}
    insert_at = _extern_insert_line(ctx)
    for key, api in apis.APIS.items():
        if ctx.abi == "sysv" and not api.is_crt:
            continue
        edits = []
        if auto_extern and key not in known and insert_at is not None:
            edits = [{"range": [insert_at, 0, insert_at, 0], "text": f"extern {api.name}\n"}]
        out.append(AsmCompletion(api.name, "function", f"{api.signature()}  [{api.dll}]", _api_doc(ctx, api),
                                 sort="5" + api.name, edits=edits))
    return out


def _extern_insert_line(ctx: Ctx) -> int | None:
    """Where a new 'extern Name' line goes: after the last extern, else after bits/default, else line 0."""
    if ctx.mod.externs:
        return max(ctx.mod.externs.values()) + 1
    best = None
    for i, m in enumerate(ctx.masked[:200]):
        if re.match(r"\s*(bits|default|cpu|%include)\b", m, re.I):
            best = i + 1
    return best if best is not None else 0


def _member_completions(ctx: Ctx, head: str) -> list[AsmCompletion]:
    """Fields after STRUCT. / variable. (MASM: var.field; NASM: STRUC.field)."""
    out: list[AsmCompletion] = []
    h = head.split("]")[-1].lstrip(".")
    struct_name = h
    for s in ctx.all_symbols():
        if s.kind == "data" and ctx.eq(s.name, h):
            t = s.detail.split()[0] if s.detail.split() else ""
            if t:
                struct_name = t
    fields = [s for s in ctx.all_symbols() if s.kind == "field" and ctx.eq(s.parent, struct_name)]
    for f in fields:
        nm = f.name.lstrip(".")
        out.append(AsmCompletion(f"{head}.{nm}", "property", f"{struct_name} field  {f.detail}", sort="0" + nm,
                                 doc=_symbol_doc(ctx, f)))
    if not fields and ctx.dialect in ("nasm", "fasm"):        # main.loop: local labels of a label
        for s in ctx.all_symbols():
            if s.kind == "local" and ctx.eq(s.parent, head):
                out.append(AsmCompletion(s.full, "method", "local label", sort="0" + s.full))
    return out


def _include_completions(ctx: Ctx) -> list[AsmCompletion]:
    cur = ctx.cur()[:ctx.col]
    if not re.match(r"\s*(%include|include|\.include|#\s*include)\b", cur, re.I) or ctx.path is None:
        return []
    out = []
    base = ctx.path.parent
    for p in project_files(ctx.path):
        if p.suffix.lower() in (".inc", ".mac", ".asminc", ".ash", ".h", ".s", ".asm"):
            try:
                rel = str(p.relative_to(base)).replace("\\", "/")
            except ValueError:
                rel = p.name
            if p != ctx.path:
                out.append(AsmCompletion(rel, "module", "include file", sort="0" + rel))
    return out


def _macro_named(ctx: Ctx, name: str) -> Sym | None:
    for s in ctx.all_symbols():
        if s.kind == "macro" and ctx.eq(s.name, name):
            return s
    return None


# ============================================================================ documentation
def _symbol_doc(ctx: Ctx, s: Sym) -> str:
    out = [f"**{s.full}** - {_tr(KIND_LABEL.get(s.kind, s.kind))}"]
    src = ""
    try:
        if s.file and ctx.path is not None and Path(s.file) == ctx.path or not s.file:
            src = ctx.lines[s.line].strip() if 0 <= s.line < len(ctx.lines) else ""
        else:
            for p, _m, t in ctx.others():
                if str(p) == s.file:
                    tl = t.split("\n")
                    src = tl[s.line].strip() if 0 <= s.line < len(tl) else ""
                    break
    except OSError:
        src = ""
    if src:
        out.append(f"```asm\n{src}\n```")
    if s.params and s.kind in ("macro", "proc", "extern"):
        out.append(f"{_tr('Parameters')}: " + ", ".join(s.params))
    if s.doc:
        out.append(s.doc)
    where = Path(s.file).name if s.file else (ctx.path.name if ctx.path else "")
    if where:
        out.append(f"*{where}, {_tr('line')} {s.line + 1}*")
    return "\n\n".join(out)


def _api_doc(ctx: Ctx, api: apis.Api | None) -> str:
    if api is None:
        return ""
    abi = ctx.abi if ctx.abi != "dos16" else "x86"
    out = [f"```c\n{api.signature()}\n```", api.doc, ""]
    locs = apis.arg_locations(api, abi)
    if api.params:
        rows = [f"| {i + 1} | `{n or t}` | {t} | `{loc}` |" for i, ((t, n), loc) in enumerate(zip(api.params, locs))]
        out.append(f"| # | {_tr('Parameter')} | {_tr('Type')} | {_tr('Passed in')} |\n|---|---|---|---|\n" +
                   "\n".join(rows))
        out.append("")
    out.append(f"**{_tr('Calling convention')}:** " + apis.convention(api, abi))
    lib = "C runtime (msvcrt / ucrt, or libc)" if api.is_crt else f"{api.dll}.dll ({api.dll}.lib)"
    out.append(f"**{_tr('Library')}:** {lib}")
    out.append(f"[{_tr('Microsoft documentation')}]({api.url()})")
    return "\n\n".join(out)


def _number_doc(word: str) -> str:
    w = word.lower().replace("_", "")
    val = None
    try:
        if re.fullmatch(r"0x[0-9a-f]+", w) or re.fullmatch(r"\$[0-9a-f]+", w):
            val = int(w.lstrip("$").replace("0x", ""), 16)
        elif re.fullmatch(r"[0-9][0-9a-f]*h", w):
            val = int(w[:-1], 16)
        elif re.fullmatch(r"0b[01]+", w):
            val = int(w[2:], 2)
        elif re.fullmatch(r"[01]+[by]", w):
            val = int(w[:-1], 2)
        elif re.fullmatch(r"[0-7]+[qo]", w):
            val = int(w[:-1], 8)
        elif re.fullmatch(r"\d+d?", w):
            val = int(w.rstrip("d"))
    except ValueError:
        return ""
    if val is None:
        return ""
    s = f"**{word}** = {val}  \nhex `{val:X}h` (`0x{val:X}`)  \nbinary `{val:b}b`"
    if val < 2 ** 32 and val >= 2 ** 31:
        s += f"  \nas signed dword: {val - 2 ** 32}"
    if 32 <= val < 127:
        s += f"  \ncharacter `'{chr(val)}'`"
    return s


def hover(code: str, line: int, col: int, path=None, plugin=None, dialect: str | None = None) -> str:
    ctx = Ctx(code, line, col, path, plugin, dialect)
    text = ctx.cur()
    m = None
    for mm in re.finditer(r"\$?[0-9][0-9a-fA-F_]*[hHbBqQoOyYdD]?|0[xX][0-9a-fA-F_]+", text):
        if mm.start() <= col <= mm.end():
            m = mm
    word, _s, _e = ctx.word_at()
    if m is not None and (not word or not word[0].isalpha() or m.group()[0].isdigit()):
        if ctx.cur_masked()[m.start():m.end()].strip():
            nd = _number_doc(m.group())
            if nd:
                return nd
    if not word:
        return ""
    bare = word.lstrip("%$") if ctx.dialect == "gas" else word
    # symbols of the program first when they shadow nothing built in
    syms = ctx.find(bare)
    ins = isa.instruction(bare, ctx.att) if not syms or bare.lower() in isa.INSTRUCTIONS else None
    if ins is not None and _is_mnemonic_pos(ctx, _s):
        if ctx.att and isa.att_base(bare) != bare.lower():
            base = isa.att_base(bare)
            suf = bare.lower()[len(base):] if bare.lower().startswith(base) else ""
            extra = f"\n\nAT&T form of **{base.upper()}**" + (f" with the '{suf}' size suffix "
                                                             f"({isa.ATT_SUFFIX.get(suf, suf)} operands)." if suf else ".")
            return _ins_doc(ins) + extra
        return _ins_doc(ins)
    reg = isa.register(bare)
    if reg is not None and not syms:
        fam = isa.REGISTERS.get(reg.family)
        parts = f"  \n{_tr('Parts')}: " + ", ".join(fam.parts) if fam is not None and fam.parts else ""
        return f"**{reg.name.upper()}** - {reg.size}-bit {_tr('register')}\n\n{reg.doc}{parts}"
    for s in syms:
        if s.kind == "extern":
            api = apis.lookup(s.name)
            if api is not None:
                return _api_doc(ctx, api)
        return _symbol_doc(ctx, s)
    api = apis.lookup(bare)
    if api is not None:
        return _api_doc(ctx, api)
    d = directives.directive(bare, ctx.dialect)
    if d is not None:
        return (f"**{bare}** - {directives.DIALECT_NAMES[ctx.dialect]} {_tr('directive')}\n\n{d[0]}\n\n"
                f"[{_tr('Manual')}]({directives.DOC_URLS[ctx.dialect]})")
    if ins is not None:
        return _ins_doc(ins)
    return ""


def _is_mnemonic_pos(ctx: Ctx, start: int) -> bool:
    pre = ctx.cur_masked()[:start]
    pre = re.sub(r"^\s*" + WORD_RE[ctx.dialect] + r"\s*::?(?!=)", "", pre)
    toks = pre.split()
    return not toks or (len(toks) == 1 and toks[0].lower() in ("lock", "rep", "repe", "repz", "repne", "repnz",
                                                                "times") or toks[0].lower() == "times")


# ============================================================================ signature help
def _commas(s: str) -> int:
    depth = 0
    n = 0
    for ch in s:
        if ch in "([<{":
            depth += 1
        elif ch in ")]>}":
            depth -= 1
        elif ch == "," and depth <= 0:
            n += 1
    return n


def _sig_from_api(ctx: Ctx, api: apis.Api, active: int, note: str = "") -> dict:
    abi = ctx.abi if ctx.abi != "dos16" else "x86"
    locs = apis.arg_locations(api, abi)
    params = []
    for (t, n), loc in zip(api.params, locs):
        params.append(f"{t} {n}".strip() + f" [{loc}]")
    label = f"{api.name}(" + ", ".join(params) + (", ..." if api.variadic else "") + f") -> {api.ret}"
    doc = api.doc + "\n\n" + apis.convention(api, abi) + (("\n\n" + note) if note else "")
    return {"label": label, "documentation": doc, "parameters": params,
            "activeParameter": max(0, min(active, max(0, len(params) - 1)))}


def _sig_from_sym(ctx: Ctx, s: Sym, active: int) -> dict:
    params = [p for p in s.params if p]
    if not params and s.kind == "macro":
        return {}
    label = f"{s.name} " + ", ".join(params)
    return {"label": label.strip(), "documentation": s.doc or KIND_LABEL.get(s.kind, s.kind), "parameters": params,
            "activeParameter": max(0, min(active, max(0, len(params) - 1)))}


def _callee(ctx: Ctx, name: str):
    name = name.strip().strip("[]")
    name = re.sub(r"^(qword|dword)\s+(ptr\s+)?", "", name, flags=re.I).strip("[] ")
    name = re.sub(r"^rel\s+", "", name, flags=re.I)
    name = name.lstrip("*")
    for s in ctx.find(name):
        if s.kind in ("proc", "macro") and s.params or s.kind == "extern" and s.params and not apis.lookup(s.name):
            return s
    api = apis.lookup(name)
    if api is not None:
        return api
    return None


def calltip(code: str, line: int, col: int, path=None, plugin=None, dialect: str | None = None):
    """Signature help: a dict {label, documentation, parameters, activeParameter} or ""."""
    ctx = Ctx(code, line, col, path, plugin, dialect)
    pre = ctx.cur_masked()[:col]
    pre_nl = re.sub(r"^\s*" + WORD_RE[ctx.dialect] + r"\s*::?(?!=)\s*", "", pre).lstrip()
    toks = pre_nl.split(None, 1)
    if not toks:
        return ""
    mn = toks[0].lower()
    rest = toks[1] if len(toks) > 1 else ""
    # invoke Func, a, b
    if mn in INVOKE_WORDS and "," in rest:
        fname = rest.split(",")[0].strip()
        target = _callee(ctx, fname)
        active = _commas(rest) - 1
        if isinstance(target, apis.Api):
            return _sig_from_api(ctx, target, active)
        if isinstance(target, Sym):
            return _sig_from_sym(ctx, target, active) or ""
        return ""
    # call Func (on the call line itself)
    if mn == "call" and rest.strip():
        target = _callee(ctx, rest.strip())
        if isinstance(target, apis.Api):
            return _sig_from_api(ctx, target, 0, _tr("Set the arguments up before the CALL."))
        return ""
    # register / push set-up before a later "call Func"
    reg_m = re.match(r"(mov|lea|movsxd|movzx|xor|movsd|movss|movq|movd|movaps|cvtsi2sd)[a-z]?\s+(%?\w+)\s*,", pre_nl, re.I)
    if ctx.att:
        reg_m2 = re.match(r"(mov|lea|xor|movs|movz)\w*\s+.*,\s*(%\w+)\s*$", ctx.cur_masked().strip(), re.I)
    else:
        reg_m2 = None
    if reg_m or mn == "push" or reg_m2:
        call = _next_call(ctx, line)
        if call is not None:
            target, call_line = call
            if isinstance(target, apis.Api):
                abi = ctx.abi if ctx.abi != "dos16" else "x86"
                locs = apis.arg_locations(target, abi)
                if mn == "push" and abi == "x86":
                    n = sum(1 for k in range(line, call_line) if re.match(r"\s*push\b", ctx.masked[k], re.I))
                    return _sig_from_api(ctx, target, n - 1, _tr("Arguments are pushed right to left: the last "
                                                                  "PUSH before the CALL is the first argument."))
                reg = (reg_m.group(2) if reg_m else reg_m2.group(2) if reg_m2 else "").lower().lstrip("%")
                fam = _reg64(reg)
                for i, loc in enumerate(locs):
                    if loc == fam or (loc.startswith("xmm") and loc == reg):
                        return _sig_from_api(ctx, target, i)
    # macro call:  SQUARE eax, |
    macro = _macro_named(ctx, toks[0])
    if macro is not None:
        return _sig_from_sym(ctx, macro, _commas(rest)) or ""
    # instruction operand forms
    ins = isa.instruction(mn, ctx.att)
    if ins is not None and ins.forms and ins.forms != ["(none)"] and (rest or pre_nl.endswith(" ")):
        active = _commas(rest)
        forms = [f for f in ins.forms if f != "(none)"]
        want = active + 1
        best = next((f for f in forms if len(f.split(",")) >= want), forms[0])
        ops = [o.strip() for o in best.split(",")]
        if ctx.att:
            ops = list(reversed(ops))
        label = f"{ins.name.upper()} " + ", ".join(ops)
        doc = ins.doc + "\n\n" + _tr("Forms") + ": " + " | ".join(forms) + \
            (("\n\n" + _tr("AT&T order: source first, destination last.")) if ctx.att else "")
        return {"label": label, "documentation": doc, "parameters": ops,
                "activeParameter": max(0, min(active, len(ops) - 1))}
    return ""


def _reg64(reg: str) -> str:
    r = isa.REGISTERS.get(reg)
    return r.family if r is not None else reg


def _next_call(ctx: Ctx, line: int):
    for k in range(line, min(len(ctx.masked), line + 14)):
        m = re.match(r"\s*(call|callq)\s+(.+)", ctx.masked[k], re.I)
        if m:
            target = _callee(ctx, m.group(2).strip().lstrip("*"))
            if target is not None:
                return target, k
            return None
        if k > line and re.match(r"\s*(ret|jmp|" + WORD_RE[ctx.dialect] + r"\s*:)", ctx.masked[k]):
            return None
    return None


# ============================================================================ definition / references
def definition(code: str, line: int, col: int, path=None, plugin=None, dialect: str | None = None
               ) -> tuple[str, int] | None:
    ctx = Ctx(code, line, col, path, plugin, dialect)
    cur = ctx.cur()
    inc = re.match(r"\s*(%include|include|\.include|#\s*include)\s+[\"'<]?([^\"'>\s]+)", cur, re.I)
    if inc and ctx.path is not None:
        f = resolve_include(inc.group(2), ctx.path)
        if f is not None:
            return (str(f), 0)
    word, _s, _e = ctx.word_at()
    if not word:
        return None
    syms = ctx.find(word.lstrip("%$") if ctx.dialect == "gas" else word)
    if not syms:
        return None
    s = syms[0]
    return (s.file or (str(ctx.path) if ctx.path else ""), s.line)


def references(code: str, line: int, col: int, path=None, plugin=None, dialect: str | None = None
               ) -> list[tuple[str, int, int]] | None:
    ctx = Ctx(code, line, col, path, plugin, dialect)
    word, _s, _e = ctx.word_at()
    if not word:
        return []
    w = word.lstrip("%$") if ctx.dialect == "gas" else word
    syms = ctx.find(w)
    flags = 0 if ctx.case else re.I
    me = str(ctx.path) if ctx.path else ""
    out: list[tuple[str, int, int]] = []
    sym = syms[0] if syms else None
    # NASM / FASM local label: '.loop' inside its parent's range, plus 'parent.loop' anywhere
    if sym is not None and sym.kind == "local" and sym.name.startswith(".") and not sym.name.startswith(".L") \
            and ctx.dialect in ("nasm", "fasm"):
        parent = next((s for s in ctx.mod.symbols if s.kind in ("label", "proc") and ctx.eq(s.name, sym.parent)), None)
        lo, hi = (parent.line, parent.end_line if parent.end_line >= 0 else len(ctx.lines)) if parent else (0, len(ctx.lines))
        pat_short = re.compile(r"(?<![\w.?$@])" + re.escape(sym.name) + r"(?![\w.?$@#~])", flags)
        for i in range(lo, min(hi + 1, len(ctx.masked))):
            for m in pat_short.finditer(ctx.masked[i]):
                out.append((me, i, m.start()))
        pat_full = re.compile(r"(?<![\w.?$@])" + re.escape(sym.full) + r"(?![\w.?$@#~])", flags)
        for p, _m, t in ctx.all_modules():
            for i, ln in enumerate(mask(t, ctx.dialect) if p != ctx.path else ctx.masked):
                for m in pat_full.finditer(ln):
                    out.append((str(p) if p else me, i, m.start()))
        return sorted(set(out), key=lambda r: (r[0] != me, r[0], r[1], r[2]))
    # procedure-scoped names (MASM LOCAL / parameters, labels inside a PROC)
    if sym is not None and sym.kind in ("var", "param") or (sym is not None and sym.kind == "local" and
                                                            ctx.dialect == "masm"):
        owner = next((s for s in ctx.mod.symbols if s.kind == "proc" and ctx.eq(s.name, sym.parent)), None)
        lo, hi = (owner.line, owner.end_line) if owner else (0, len(ctx.lines) - 1)
        pat = re.compile(r"(?<![\w.?$@])" + re.escape(w) + r"(?![\w.?$@])", flags)
        for i in range(lo, min(hi + 1, len(ctx.masked))):
            for m in pat.finditer(ctx.masked[i]):
                out.append((me, i, m.start()))
        return out
    pat = re.compile(r"(?<![\w.?$@%])" + re.escape(w) + r"(?![\w?$@#~])", flags)
    for p, _m, t in ctx.all_modules():
        lines = ctx.masked if p == ctx.path else mask(t, ctx.dialect)
        for i, ln in enumerate(lines):
            for m in pat.finditer(ln):
                out.append((str(p) if p else me, i, m.start()))
    return out


# ============================================================================ outline / folding
OUTLINE_KIND = {"section": "package", "proc": "function", "label": "function", "local": "method", "data": "variable",
                "const": "constant", "macro": "class", "struct": "class", "field": "attribute", "var": "variable",
                "param": "variable"}


def document_symbols(code: str, path=None, plugin=None, dialect: str | None = None) -> list[dict]:
    """[{name, kind, line, detail, children}] - sections > procedures / labels > local labels, plus data,
    constants, macros and structures."""
    dia = dialect or detect_dialect(path, code, plugin)
    mod = parse(code, dia, str(path) if path else "")
    top: list[dict] = []
    current_section: dict | None = None
    current_label: dict | None = None
    current_struct: dict | None = None
    labels_by_name: dict[str, dict] = {}

    def node(s: Sym) -> dict:
        detail = "" if s.detail in ("label", "local label") else s.detail[:60]
        return {"name": s.name, "kind": OUTLINE_KIND.get(s.kind, "variable"), "line": s.line, "detail": detail,
                "children": []}

    def container() -> list:
        return current_section["children"] if current_section is not None else top

    for s in mod.symbols:
        if s.kind == "extern":
            continue
        if s.kind == "section":
            current_section = node(s)
            current_label = None
            top.append(current_section)
            continue
        n = node(s)
        if s.kind in ("local", "var", "param"):
            parent = labels_by_name.get(s.parent.lower() if s.parent else "") or current_label
            if parent is not None:
                parent["children"].append(n)
                continue
        if s.kind == "field":
            if current_struct is not None:
                current_struct["children"].append(n)
                continue
        if s.kind in ("proc", "label"):
            current_label = n
            labels_by_name[s.name.lower()] = n
        if s.kind == "struct":
            current_struct = n
        container().append(n)
    return top


FOLD_PAIRS = {
    "nasm": [(r"^\s*%i?macro\b", r"^\s*%endmacro\b"), (r"^\s*%if\w*\b", r"^\s*%endif\b"), (r"^\s*%rep\b", r"^\s*%endrep\b"),
             (r"^\s*struc\b", r"^\s*endstruc\b"), (r"^\s*istruc\b", r"^\s*iend\b")],
    "masm": [(r"^\s*\w+\s+proc\b", r"^\s*\w+\s+endp\b"), (r"^\s*\w+\s+macro\b", r"^\s*endm\b"),
             (r"^\s*\w+\s+(struct|struc|union|segment)\b", r"^\s*\w+\s+ends\b"), (r"^\s*\.if\b", r"^\s*\.endif\b"),
             (r"^\s*\.while\b", r"^\s*\.endw\b"), (r"^\s*\.repeat\b", r"^\s*\.until\w*\b"),
             (r"^\s*(rept|irp|irpc|while)\b", r"^\s*endm\b"), (r"^\s*if\w*\b", r"^\s*endif\b")],
    "fasm": [(r"\{\s*$", r"^\s*\}"), (r"^\s*proc\b", r"^\s*endp\b"), (r"^\s*struct\b", r"^\s*ends\b"),
             (r"^\s*if\b", r"^\s*end\s+if\b"), (r"^\s*repeat\b", r"^\s*end\s+repeat\b"),
             (r"^\s*while\b", r"^\s*end\s+while\b"), (r"^\s*virtual\b", r"^\s*end\s+virtual\b"),
             (r"^\s*locals\b", r"^\s*endl\b")],
    "gas": [(r"^\s*\.macro\b", r"^\s*\.endm\b"), (r"^\s*\.(rept|irp|irpc)\b", r"^\s*\.endr\b"),
            (r"^\s*\.if\w*\b", r"^\s*\.endif\b"), (r"^\s*\.cfi_startproc\b", r"^\s*\.cfi_endproc\b"),
            (r"^\s*\.seh_proc\b", r"^\s*\.seh_endproc\b")],
}
SECTION_RE = {
    "nasm": r"^\s*(section|segment)\s",
    "masm": r"^\s*(\.code|\.data\??|\.const)\b",
    "fasm": r"^\s*(section|segment)\s",
    "gas": r"^\s*(\.text|\.data|\.bss|\.section|\.rodata)\b",
}
LABEL_RE = {
    "nasm": r"^[A-Za-z_?$@][\w.?$@#~]*\s*:",
    "masm": r"^[A-Za-z_?$@][\w?$@]*\s*::?(?!=)",
    "fasm": r"^[A-Za-z_?$@][\w.?$@#~]*\s*:",
    "gas": r"^[A-Za-z_$][\w$]*\s*:",
}


def folding_ranges(code: str, path=None, plugin=None, dialect: str | None = None) -> list[dict]:
    """[{start, end, kind}] (0-based lines) for blocks, sections, label bodies and comment runs."""
    dia = dialect or detect_dialect(path, code, plugin)
    masked = mask(code, dia)
    raw = code.split("\n")
    out: list[dict] = []
    stack: list[tuple[int, int]] = []
    pairs = [(re.compile(a, re.I), re.compile(b, re.I)) for a, b in FOLD_PAIRS.get(dia, [])]
    sec_re = re.compile(SECTION_RE[dia], re.I)
    lab_re = re.compile(LABEL_RE[dia])
    last_sec = last_lab = -1
    n = len(masked)
    last_code = 0
    for i, m in enumerate(masked):
        if m.strip():
            last_code = i
        handled = False
        for k, (a, b) in enumerate(pairs):
            if b.search(m):
                for j in range(len(stack) - 1, -1, -1):
                    if pairs[stack[j][0]][1].pattern == b.pattern:
                        st = stack[j][1]
                        del stack[j:]
                        if i > st:
                            out.append({"start": st, "end": i, "kind": "region"})
                        break
                handled = True
                break
        if not handled:
            for k, (a, b) in enumerate(pairs):
                if a.search(m):
                    stack.append((k, i))
                    break
        if sec_re.search(m):
            if last_sec >= 0:
                out.append({"start": last_sec, "end": _prev_code(masked, i), "kind": "region"})
            if last_lab >= 0:
                out.append({"start": last_lab, "end": _prev_code(masked, i), "kind": "region"})
                last_lab = -1
            last_sec = i
        elif lab_re.match(m) and not m.lstrip().startswith("."):
            if last_lab >= 0:
                out.append({"start": last_lab, "end": _prev_code(masked, i), "kind": "region"})
            last_lab = i
    for st in (last_sec, last_lab):
        if st >= 0 and last_code > st:
            out.append({"start": st, "end": last_code, "kind": "region"})
    # runs of 3+ comment lines
    prefixes = ("#", "//") if dia == "gas" else (";",)
    run = -1
    for i in range(n + 1):
        is_c = i < n and raw[i].strip().startswith(prefixes)
        if is_c and run < 0:
            run = i
        elif not is_c and run >= 0:
            if i - run >= 3:
                out.append({"start": run, "end": i - 1, "kind": "comment"})
            run = -1
    return [r for r in out if r["end"] > r["start"]]


def _prev_code(masked: list[str], i: int) -> int:
    j = i - 1
    while j > 0 and not masked[j].strip():
        j -= 1
    return j


def is_asm_file(path) -> bool:
    return is_asm_path(path)
