"""Symbol checks (ASM201-ASM206): undefined / duplicate labels, missing extern, jumps into data, writes into
read-only sections and NASM 64-bit absolute addressing."""
from __future__ import annotations

import difflib
import re

from .model import Fix, Issue
from .ops import WRITE_DEST
from .parse import BRANCHES, Program
from .project import ProjectSymbols, known_function

_SPECIAL = re.compile(r"^(\$.*|@@|@[fFbBrR]|\d+[fb]?|short|near|far)$")


def _decl_fix(prog: Program, name: str) -> tuple[str, Fix]:
    if prog.dialect == "nasm":
        decl = f"extern {name}"
    elif prog.dialect == "masm":
        decl = f"extern {name}:proc" if prog.bits == 64 else f"extern {name}:near"
    else:
        decl = f".extern {name}"
    line = 0
    last_ext = max([ln for ln in prog.externs.values()] or [-1])
    if last_ext >= 0:
        line = last_ext + 1
    else:
        first = next((s for s in prog.stmts if s.kind in ("directive", "instr", "data", "label")), None)
        sect = next((s for s in prog.stmts if s.kind == "directive" and s.mnem in ("section", "segment", ".code",
                                                                                  ".data", ".text")), None)
        if sect is not None:
            line = sect.line
        elif first is not None:
            line = first.line
    fx = Fix(f"Add '{decl}'", f"أضف '{decl}'", [{"range": [line, 0, line, 0], "text": decl + "\n"}])
    return decl, fx


def check_symbols(prog: Program, out: list, ps: ProjectSymbols | None) -> None:
    p = prog
    # ---------------------------------------------- duplicate labels
    for old, new in p.dups:
        if old.cond or new.cond:
            continue
        if old.kind == "const" and new.kind == "const":
            continue
        out.append(Issue("ASM203", new.line, new.col, new.col + len(new.name), {"name": new.name,
                                                                               "first": old.line + 1}))
    # ---------------------------------------------- jump / call targets
    names = [d.name for d in p.labels.values() if d.kind in ("code", "proc")]
    unresolved = bool(ps.unresolved) if ps is not None else False
    define_macros = {s.mnem[7:] for s in p.stmts if s.kind == "macro" and s.mnem.startswith("define_")}
    reported: set = set()
    for st in p.stmts:
        if st.kind != "instr" or st.mnem not in BRANCHES or not st.ops:
            continue
        o = st.ops[0]
        if o.kind != "sym":
            continue
        text = o.text.strip()
        name = o.syms[0] if o.syms else text
        if not name or _SPECIAL.match(name) or _SPECIAL.match(text.lower().replace(" ", "")):
            continue
        d = p.resolve(name, st.line, st.scope, st.proc)
        col = o.col + max(0, o.text.find(name))
        end = col + len(name)
        if d is not None:
            if d.kind == "data":
                out.append(Issue("ASM204", st.line, col, end, {"mnem": st.mnem.upper(), "name": name,
                                                               "directive": d.directive or "db"}, mnem=st.mnem))
            continue
        if p.key(name) in p.macros or name.lower() in define_macros:
            continue
        if p.dialect == "gas" and st.mnem == "call":
            continue                         # GNU as treats undefined names as external symbols
        if ps is not None and ps.included(name):
            continue
        other = ps.other_file(name) if ps is not None else ""
        known = known_function(name)
        key = p.key(name)
        if other or known:
            if key in reported:
                continue
            if p.dialect == "nasm" or (p.dialect == "masm" and not unresolved and p.bits == 64):
                reported.add(key)
                decl, fx = _decl_fix(p, name)
                where = f"in {other}" if other else "in a DLL / the C runtime"
                where_ar = f"في الملف {other}" if other else "في مكتبة DLL أو مكتبة C"
                out.append(Issue("ASM202", st.line, col, end, {"name": name, "kw": "extern", "where": where,
                                                               "where_ar": where_ar, "decl": decl}, [fx],
                                 mnem=st.mnem))
            continue
        if unresolved or p.macro_defined_labels or p.uses_invoke and p.dialect == "fasm":
            continue
        if p.dialect == "gas" and not p.att and False:
            continue
        near = difflib.get_close_matches(name, names, 1, 0.75) or \
            difflib.get_close_matches(name.lower(), [n.lower() for n in names], 1, 0.75)
        fixes = []
        if near:
            nm = next((n for n in names if n.lower() == near[0].lower()), near[0])
            fixes = [Fix(f"Change to '{nm}'", f"غيّره إلى '{nm}'",
                         [{"range": [st.line, col, st.line, end], "text": nm}])]
            args = {"name": name, "near": f" (did you mean '{nm}'?)", "near_ar": f" (هل تقصد '{nm}'؟)"}
        else:
            args = {"name": name, "near": "", "near_ar": ""}
        out.append(Issue("ASM201", st.line, col, end, args, fixes, mnem=st.mnem))
    # ---------------------------------------------- writes into read-only sections
    for st in p.stmts:
        if st.kind != "instr" or st.mnem not in WRITE_DEST or not st.ops or st.ops[0].kind != "mem":
            continue
        o = st.ops[0]
        if not o.syms or st.mnem in ("cmp", "test"):
            continue
        d = p.resolve(o.syms[0], st.line, st.scope, st.proc)
        if d is None or d.kind != "data":
            continue
        if d.skind == "rodata" or (d.skind == "code" and p.abi != "dos16" and p.os != "dos" and p.bits != 16):
            out.append(Issue("ASM205", st.line, o.col, o.end, {"name": d.name, "section": d.section or "code"},
                             mnem=st.mnem))
    # ---------------------------------------------- NASM 64-bit absolute addresses
    if p.dialect == "nasm" and p.bits == 64 and not p.default_rel:
        for st in p.stmts:
            if st.kind != "instr":
                continue
            o = next((o for o in st.ops if o.kind == "mem" and not o.regs and not o.rel and o.syms and not o.seg),
                     None)
            if o is None:
                continue
            d = p.resolve(o.syms[0], st.line, st.scope, st.proc)
            if d is None or d.kind not in ("data", "code", "proc", "extern"):
                continue
            first = next((s for s in p.stmts if s.kind in ("directive", "instr", "data")), st)
            fx = Fix("Add 'default rel' at the top", "أضف 'default rel' في أول الملف",
                     [{"range": [first.line, 0, first.line, 0], "text": "default rel\n"}])
            out.append(Issue("ASM206", st.line, o.col, o.end, {}, [fx], mnem=st.mnem))
            break
