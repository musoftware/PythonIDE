"""Rule configuration (per project) and suppression comments.

Project setting - in project.radproj::

    "asm_lint": {
        "enabled": true,
        "rules": {"ASM307": "off", "register-used-before-set": "info", "ASM104": "warning"}
    }

Suppression comments (any comment style of the dialect)::

    mov eax, ebx            ; asmlint-disable-line ASM101
    ; asmlint-disable-next-line ASM307, ASM401
    ; asmlint-disable-file ASM206           (anywhere in the file)
    ; asmlint-disable-line                  (no ids = every rule on that line)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..asm_intel.index import comment_of
from .rules import RULES, SEVERITIES, rule

_SUPP = re.compile(r"asmlint\s*[:-]?\s*(disable-next-line|disable-line|disable-file|disable|ignore)\b\s*([\w\s,-]*)",
                   re.I)


def project_file(path) -> Path | None:
    if not path:
        return None
    p = Path(str(path))
    for d in [p.parent, *p.parent.parents][:4]:
        f = d / "project.radproj"
        if f.is_file():
            return f
    return None


def project_config(path) -> dict:
    f = project_file(path)
    if f is None:
        return {}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    cfg = data.get("asm_lint")
    return cfg if isinstance(cfg, dict) else {}


def save_project_config(path, cfg: dict) -> bool:
    """Write the "asm_lint" settings into the project.radproj next to *path* (other keys are kept)."""
    f = project_file(path)
    if f is None:
        return False
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    data["asm_lint"] = cfg
    try:
        f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        return False
    return True


def rule_levels(cfg: dict | None) -> dict[str, str]:
    """{rule id: off | error | warning | info} from a configuration dict (names or ids accepted)."""
    out: dict[str, str] = {}
    for k, v in ((cfg or {}).get("rules") or {}).items():
        r = rule(str(k))
        lv = str(v).lower()
        if r is None:
            continue
        if lv in ("off", "none", "disable", "disabled", "false", "0"):
            out[r.id] = "off"
        elif lv in SEVERITIES:
            out[r.id] = lv
        elif lv in ("hint", "suggestion"):
            out[r.id] = "info"
    return out


def _ids(text: str) -> set[str]:
    out = set()
    for part in re.split(r"[\s,]+", text.strip()):
        if not part:
            continue
        r = rule(part)
        if r is not None:
            out.add(r.id)
    return out


def suppressions(lines: list[str], dialect: str) -> tuple[dict[int, set | None], set | None]:
    """({line: ids or None (= all)}, file-wide ids or None for no file-wide suppression)."""
    per_line: dict[int, set | None] = {}
    file_ids: set | None = None
    file_all = False
    for i, ln in enumerate(lines):
        if "asmlint" not in ln.lower():
            continue
        c = comment_of(ln, dialect) or ln
        for m in _SUPP.finditer(c):
            kind = m.group(1).lower()
            ids = _ids(m.group(2))
            target = i + 1 if kind == "disable-next-line" else i
            if kind in ("disable-file", "disable"):
                if ids:
                    file_ids = (file_ids or set()) | ids
                else:
                    file_all = True
                continue
            prev = per_line.get(target, set())
            if not ids or prev is None:
                per_line[target] = None
            else:
                per_line[target] = prev | ids
    if file_all:
        return per_line, set(RULES)
    return per_line, file_ids


def apply(issues: list, lines: list[str], dialect: str, cfg: dict | None) -> list:
    if cfg is not None and cfg.get("enabled") is False:
        return []
    levels = rule_levels(cfg)
    per_line, file_ids = suppressions(lines, dialect)
    out = []
    for it in issues:
        lv = levels.get(it.rule)
        if lv == "off":
            continue
        if lv:
            it.severity = lv
        if file_ids and it.rule in file_ids:
            continue
        sup = per_line.get(it.line, set())
        if sup is None or (sup and it.rule in sup):
            continue
        out.append(it)
    return out
