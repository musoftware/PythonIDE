"""Assembly analyzer for RAD IDE: finds mistakes while you type and explains them in Arabic and English.

    from radide.asm_lint import lint
    for issue in lint(text, path):                       # dialect / mode / ABI detected like the IntelliSense
        print(issue.line + 1, issue.rule, issue.message("ar"))
        print(issue.markdown("ar"))                      # why it is wrong + how to fix it + Learn more
        for fix in issue.fixes:                          # quick fixes (Ctrl+.)
            new_text = apply_edits(text, fix.edits)

Dialects: NASM, MASM (also the emu8086 / TASM 16-bit style), FASM, GNU as (AT&T and Intel syntax), in 16, 32 and
64-bit mode. Modules (no Qt in any of them):

    parse        statements, typed operands, sections, labels (reuses radide/asm_intel: masking, isa tables)
    ops          operand / encoding checks (ASM1xx)
    symbols      undefined / duplicate labels, missing extern, read-only writes (ASM2xx)
    flow         units, control-flow graph, data flow, stack depth, calling conventions, DOS (ASM3xx-ASM6xx)
    project      names of included files / other project files / emu8086.inc
    rules        the rule catalogue with the bilingual message / why / fix texts
    config       per-project rule settings (project.radproj "asm_lint") and suppression comments
    asm_errors   friendly explanations of assembler and linker messages
    model        Issue / Fix and their markdown

The IDE side is radide/features/asm_smart_lint.py (squiggles, hover, Ctrl+. fixes, Error List, Problems panel).
"""
from __future__ import annotations

import hashlib

from .asm_errors import AsmExplanation, explain, friendly
from .config import project_config
from .model import Fix, Issue, apply_edits
from .rules import RULES, Rule, rule

__all__ = ["AsmExplanation", "Fix", "Issue", "RULES", "Rule", "apply_edits", "explain", "friendly", "lint",
           "lint_program", "rule", "is_x86_source"]

_LAST: dict[str, tuple[str, list]] = {}


def is_x86_source(prog) -> bool:
    """False for 6502 / Z80 / Game Boy ... sources that happen to use .asm / .s (radide/retro)."""
    instr = sum(1 for s in prog.stmts if s.kind == "instr")
    macro = sum(1 for s in prog.stmts if s.kind == "macro")
    if instr == 0 and macro == 0:
        return True
    if macro > 6 and macro > 2 * instr:
        return False
    return True


def lint_program(prog, config: dict | None = None, project=True) -> list[Issue]:
    from .flow import check_flow
    from .ops import check_operands
    from .project import project_symbols
    from .symbols import check_symbols
    if not is_x86_source(prog):
        return []
    ps = None
    if project:
        try:
            ps = project_symbols(prog.path, prog.includes, prog.dialect, prog.case)
        except Exception:  # noqa: BLE001 - a broken include must not stop the analysis
            ps = None
    out: list[Issue] = []
    check_operands(prog, out)
    try:
        check_symbols(prog, out, ps)
    except Exception:  # noqa: BLE001
        pass
    try:
        check_flow(prog, out, ps)
    except Exception:  # noqa: BLE001
        pass
    # one issue per (rule, line, column); operand errors make flow checks of the same line redundant
    seen = set()
    err_lines = {it.line for it in out if it.rule.startswith("ASM1") and it.severity == "error"}
    uniq = []
    for it in out:
        k = (it.rule, it.line, it.col)
        if k in seen:
            continue
        if it.line in err_lines and it.rule[3] in "345" and it.rule not in ("ASM304", "ASM305"):
            continue
        seen.add(k)
        uniq.append(it)
    from . import config as cfgmod
    if config is None and prog.path is not None:
        config = project_config(prog.path)
    uniq = cfgmod.apply(uniq, prog.lines, prog.dialect, config)
    uniq.sort(key=lambda i: (i.line, i.col, i.rule))
    return uniq


def lint(text: str, path=None, dialect: str | None = None, plugin=None, config: dict | None = None,
         bits: int | None = None, abi: str | None = None, project_lang: str | None = None,
         project: bool = True) -> list[Issue]:
    """Every issue of an assembly source (see the module documentation)."""
    from .parse import Program
    key = f"{path}|{dialect}|{bits}|{abi}|{project_lang}|{project}|{config!r}"
    digest = hashlib.blake2b(text.encode("utf-8", "replace"), digest_size=16).hexdigest()
    hit = _LAST.get(key)
    if hit is not None and hit[0] == digest:
        return list(hit[1])
    prog = Program(text, path, dialect=dialect, plugin=plugin, bits=bits, abi=abi, project_lang=project_lang)
    issues = lint_program(prog, config, project)
    if len(_LAST) > 32:
        _LAST.clear()
    _LAST[key] = (digest, issues)
    return list(issues)
