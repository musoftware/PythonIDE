"""Editor support of the DOS projects: completions, hover, signature help, outline, Go to Definition (no Qt).

Hovering ``int 21h`` (assembly), ``Intr($21, R)`` (Pascal), ``int86(0x21, ...)`` (C) or ``CALL INTERRUPT(&H21`` shows
the interrupt; when the function register is set a few lines above (``mov ah, 09h``, ``R.AH := $09``,
``r.h.ah = 0x09``, ``mov ax, 4C00h``, ``r.x.ax = 3`` for INT 33h) the hover describes that function: registers in /
out and what it does.
"""
from __future__ import annotations

import re

from ...languages.base import Completion
from . import reference as R

_WORD = re.compile(r"[A-Za-z_$&][\w$#]*\$?|\d[0-9A-Fa-f]*[hH]?")


def _word_at(text: str, col: int) -> tuple[str, int, int]:
    for m in re.finditer(r"[A-Za-z0-9_$&#]+\$?", text):
        if m.start() <= col <= m.end():
            return m.group(0), m.start(), m.end()
    return "", col, col


def _num(tok: str) -> int | None:
    t = tok.strip().lower()
    try:
        if t.startswith("0x"):
            return int(t[2:], 16)
        if t.startswith("$"):
            return int(t[1:], 16)
        if t.startswith("&h"):
            return int(t[2:], 16)
        if t.endswith("h") and re.fullmatch(r"[0-9][0-9a-f]*h", t):
            return int(t[:-1], 16)
        if re.fullmatch(r"\d+", t):
            return int(t)
    except ValueError:
        return None
    return None


_INT_CALL = re.compile(r"(?i)\b(?:int86x?|intr|interruptx?|int)\b\s*\(?\s*([0-9][0-9a-f]*h|0x[0-9a-f]+|\$[0-9a-f]+|"
                       r"&h[0-9a-f]+|\d+)")
_SET_AH = [re.compile(r"(?i)\bmov\s+ah\s*,\s*([0-9][0-9a-f]*h|0x[0-9a-f]+|\d+)"),
           re.compile(r"(?i)\b\w+\.ah\s*:?=\s*(\$[0-9a-f]+|\d+)"),
           re.compile(r"(?i)\b\w+\.h\.ah\s*=\s*(0x[0-9a-f]+|\d+)"),
           re.compile(r"(?i)\b\w+\.ah\s*=\s*(&h[0-9a-f]+|\d+)")]
_SET_AX = [re.compile(r"(?i)\bmov\s+ax\s*,\s*([0-9][0-9a-f]*h|0x[0-9a-f]+|\d+)"),
           re.compile(r"(?i)\b\w+\.ax\s*:?=\s*(\$[0-9a-f]+|\d+)"),
           re.compile(r"(?i)\b\w+\.x\.ax\s*=\s*(0x[0-9a-f]+|\d+)"),
           re.compile(r"(?i)\bmouse\s*\(\s*(0x[0-9a-f]+|\d+)\s*\)"),
           re.compile(r"(?i)\bxor\s+ax\s*,\s*ax\b()")]


def interrupt_at(lines: list[str], line: int) -> tuple[int, int | None] | None:
    """(interrupt number, function number or None) of the interrupt call on *line*."""
    if line >= len(lines):
        return None
    m = _INT_CALL.search(lines[line])
    if not m:
        return None
    number = _num(m.group(1))
    if number is None or number not in R.INTERRUPTS:
        return (number, None) if number is not None else None
    it = R.INTERRUPTS[number]
    func = None
    for back in range(line, max(-1, line - 10), -1):
        text = lines[back].split(";")[0] if back != line else lines[back][:m.start()]
        if it.selector == "AX":
            for rx in _SET_AX:
                mm = rx.search(text)
                if mm:
                    func = _num(mm.group(1)) if mm.group(1) else 0
                    break
        else:
            for rx in _SET_AH:
                mm = rx.search(text)
                if mm:
                    func = _num(mm.group(1))
                    break
            if func is None:
                for rx in _SET_AX[:3]:
                    mm = rx.search(text)
                    if mm and _num(mm.group(1)) is not None:
                        func = (_num(mm.group(1)) or 0) >> 8
                        break
        if func is not None:
            break
        if back != line and _INT_CALL.search(lines[back]):
            break                        # an earlier interrupt call: its registers are not ours
    return number, func


# ============================================================================ symbols
_SYM_RX = {
    "qbasic": re.compile(r"(?im)^\s*(?:\d+\s+)?(SUB|FUNCTION|TYPE)\s+([A-Za-z_][\w]*[$%&!#]?)"),
    "pascal": re.compile(r"(?im)^\s*(procedure|function|constructor|destructor|type\s+\w+\s*=\s*record|program|unit)"
                         r"\s+([A-Za-z_][\w.]*)"),
    "c": re.compile(r"(?m)^[A-Za-z_][\w\s\*]*?\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(\{|$)"),
    "asm": re.compile(r"(?im)^\s*([A-Za-z_@?$][\w@?$]*)\s+(proc|macro|segment|struc|equ|db|dw|dd)\b|"
                      r"^\s*([A-Za-z_@?$][\w@?$]*)\s*:(?!:)"),
    "batch": re.compile(r"(?m)^\s*:(\w+)"),
}


def symbols(kind: str, code: str) -> list[dict]:
    out = []
    rx = _SYM_RX.get(kind)
    if rx is None:
        return out
    labels_qb = re.compile(r"(?m)^\s*([A-Za-z_]\w*):\s*$")
    for m in rx.finditer(code):
        line = code.count("\n", 0, m.start())
        if kind == "qbasic":
            name, k = m.group(2), ("class" if m.group(1).upper() == "TYPE" else "function")
        elif kind == "pascal":
            word = m.group(1).split()[0].lower()
            name = m.group(2)
            k = {"program": "module", "unit": "module", "type": "class"}.get(word, "function")
        elif kind == "c":
            name, k = m.group(1), "function"
            if name in ("if", "while", "for", "switch", "return", "sizeof"):
                continue
        elif kind == "asm":
            if m.group(1):
                name = m.group(1)
                k = {"proc": "function", "macro": "function", "segment": "module", "struc": "class",
                     "equ": "constant"}.get(m.group(2).lower(), "variable")
            else:
                name, k = m.group(3), "function"
        else:
            name, k = m.group(1), "function"
        out.append({"name": name, "kind": k, "line": line, "detail": code.splitlines()[line].strip()[:60]
                    if line < len(code.splitlines()) else "", "children": []})
    if kind == "qbasic":
        for m in labels_qb.finditer(code):
            out.append({"name": m.group(1), "kind": "function", "line": code.count("\n", 0, m.start()),
                        "detail": "label", "children": []})
    return out


def definition(kind: str, code: str, line: int, col: int) -> int | None:
    lines = code.splitlines()
    if line >= len(lines):
        return None
    word, _s, _e = _word_at(lines[line], col)
    if not word:
        return None
    for s in symbols(kind, code):
        if s["name"].lower() == word.lower():
            return s["line"]
    if kind == "qbasic" and word.isdigit():           # GOTO 1000
        for i, ln in enumerate(lines):
            if re.match(rf"^\s*{word}\s", ln):
                return i
    return None


# ============================================================================ completions
def _asm_docs() -> dict:
    try:
        from ...languages.emu8086 import DOCS, INSTRUCTIONS
        return {**{k: (v[0], v[1]) for k, v in DOCS.items()}, **{k: (k, "") for k in INSTRUCTIONS if k not in DOCS}}
    except Exception:  # noqa: BLE001
        return {}


def completions(kind: str, code: str, line: int, col: int) -> list[Completion]:
    lines = code.splitlines()
    before = lines[line][:col] if line < len(lines) else ""
    out: list[Completion] = []
    if kind == "asm" and re.search(r"(?i)\bint\s+\w*$", before):
        return [Completion(f"{n:02X}h", "constant", it.title) for n, it in sorted(R.INTERRUPTS.items())]
    if kind == "qbasic":
        out += [Completion(k, "keyword", sig) for k, (sig, _d) in R.QBASIC.items()]
    elif kind == "pascal":
        out += [Completion(k, "keyword") for k in R.PASCAL_KEYWORDS]
        out += [Completion(k, "function", f"{sig}  [{unit}]") for k, (sig, unit, _d) in R.PASCAL.items()]
    elif kind == "c":
        out += [Completion(k, "keyword") for k in R.C_KEYWORDS]
        out += [Completion(k, "function", f"{sig}  [{hdr}]") for k, (sig, hdr, _d) in R.C_FUNCS.items()]
    elif kind == "asm":
        out += [Completion(k, "keyword", d[0][:60]) for k, d in _asm_docs().items()]
        from ...languages.emu8086 import DIRECTIVES, REGISTERS
        out += [Completion(d, "keyword") for d in DIRECTIVES]
        out += [Completion(r, "variable", "register") for r in REGISTERS]
    elif kind == "batch":
        out += [Completion(k, "keyword", sig) for k, (sig, _d) in R.BATCH.items()]
    seen = {c.name.lower() for c in out}
    for s in symbols(kind, code):
        if s["name"].lower() not in seen:
            seen.add(s["name"].lower())
            out.append(Completion(s["name"], s["kind"], s["detail"]))
    for w in re.findall(r"[A-Za-z_]\w{2,}\$?", code):
        if w.lower() not in seen:
            seen.add(w.lower())
            out.append(Completion(w, "variable"))
    return out


# ============================================================================ hover / signature help
def hover(kind: str, code: str, line: int, col: int) -> str:
    lines = code.splitlines()
    if line >= len(lines):
        return ""
    text = lines[line]
    word, start, end = _word_at(text, col)
    if not word:
        return ""
    arabic = R.arabic_ui()
    hit = interrupt_at(lines, line)
    if hit is not None and (word.lower() in ("int", "intr", "int86", "int86x", "interrupt") or _num(word) == hit[0]):
        number, func = hit
        doc = R.interrupt_doc(number, func, arabic)
        if doc:
            return doc
    up = word.upper()
    if kind == "qbasic":
        two = re.match(rf"(?i)\s*{re.escape(word)}\s+(\w+\$?)", text[start:])
        if two and f"{up} {two.group(1).upper()}" in R.QBASIC:
            up = f"{up} {two.group(1).upper()}"
        if up in R.QBASIC:
            sig, d = R.QBASIC[up]
            return f"**{up}**  \n`{sig}`  \n{d}"
    elif kind == "pascal":
        for k, (sig, unit, d) in R.PASCAL.items():
            if k.lower() == word.lower():
                return f"**{k}** ({unit} unit)  \n`{sig}`  \n{d}"
    elif kind == "c":
        if word in R.C_FUNCS:
            sig, hdr, d = R.C_FUNCS[word]
            return f"**{word}** ({hdr})  \n`{sig}`  \n{d}"
    elif kind == "asm":
        docs = _asm_docs()
        if word.lower() in docs:
            en, ar = docs[word.lower()]
            return f"**{word.lower()}**  \n{en}" + (f"  \n{ar}" if arabic and ar else "")
    elif kind == "batch":
        if up in R.BATCH:
            sig, d = R.BATCH[up]
            return f"**{up}**  \n`{sig}`  \n{d}"
    for s in symbols(kind, code):
        if s["name"].lower() == word.lower():
            return f"**{s['name']}** ({s['kind']}, line {s['line'] + 1})  \n`{s['detail']}`"
    return ""


def calltip(kind: str, code: str, line: int, col: int) -> str:
    lines = code.splitlines()
    if line >= len(lines):
        return ""
    before = lines[line][:col]
    if kind in ("pascal", "c"):
        depth = 0
        for i in range(len(before) - 1, -1, -1):
            ch = before[i]
            if ch == ")":
                depth += 1
            elif ch == "(":
                if depth == 0:
                    m = re.search(r"([A-Za-z_]\w*)\s*$", before[:i])
                    if m:
                        name = m.group(1)
                        table = R.PASCAL if kind == "pascal" else R.C_FUNCS
                        for k, v in table.items():
                            if k.lower() == name.lower():
                                return v[0]
                    return ""
                depth -= 1
        return ""
    if kind == "qbasic":
        m = re.match(r"^\s*(?:\d+\s+)?([A-Za-z_]+\$?(?:\s+(?:INPUT|CASE|SEG))?)\b", before, re.I)
        if m and m.group(1).upper() in R.QBASIC:
            return R.QBASIC[m.group(1).upper()][0]
    if kind == "asm":
        hit = interrupt_at(lines, line)
        if hit and hit[1] is not None:
            it = R.INTERRUPTS.get(hit[0])
            f = it.functions.get(hit[1]) if it else None
            if f:
                return f"INT {hit[0]:02X}h {it.selector}={hit[1]:02X}h {f.name}: in {f.inputs}; out {f.outputs}"
    return ""


__all__ = ["calltip", "completions", "definition", "hover", "interrupt_at", "symbols"]
