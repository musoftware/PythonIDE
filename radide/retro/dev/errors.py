"""Messages of the retro toolchains -> Error List rows (no Qt in here).

    DASM        main.asm (12): error: Unknown Mnemonic 'foo'.
                --- Unresolved Symbol List / name 0000 ????  (R )
    ca65 / cc65 main.s:12: Error: Symbol 'x' is undefined          main.c:5: Warning: ...
    ld65        ld65: Error: ...        nes.cfg:3: Warning: Segment 'PRG' overflows memory area ...
    RGBDS       error: Undefined symbol `nowhere`                  warning: ...
                    at main.asm(12)          (or "at main.asm(12) <- other.inc(3)")
    sjasmplus   main.asm(12): error: Unrecognized instruction: foo
    ACME        Error - File main.a, line 12 (Zone <untitled>): Value not defined.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Diag:
    severity: str          # "Error" | "Warning"
    message: str
    file: str
    line: int              # 1-based (0 = unknown)

    def to_dict(self) -> dict:
        return asdict(self)


DASM_RX = re.compile(r"^(?P<file>[^\n()]+?)\s\((?P<line>\d+)\):\s*(?P<sev>error|warning|fatal|abort)[^:]*:\s*(?P<msg>.*)$",
                     re.I)
CA65_RX = re.compile(r"^(?P<file>(?:[A-Za-z]:)?[^\n:]+?):(?P<line>\d+):\s*(?P<sev>Error|Warning|Fatal)\s*:\s*(?P<msg>.*)$")
CC65_PAREN_RX = re.compile(r"^(?P<file>[^\n(]+?)\((?P<line>\d+)\):\s*(?P<sev>Error|Warning|Fatal)\s*:\s*(?P<msg>.*)$")
TOOL_RX = re.compile(r"^(?P<tool>ld65|ca65|cc65|cl65|rgbasm|rgblink|rgbfix|sjasmplus|dasm)(?:\.exe)?:\s*"
                     r"(?P<sev>error|warning|fatal)\s*:\s*(?P<msg>.*)$", re.I)
RGBDS_HEAD_RX = re.compile(r"^(?P<sev>error|warning|FATAL|fatal)(?:\s*\[[^\]]*\])?:\s*(?P<msg>.*)$")
RGBDS_AT_RX = re.compile(r"^\s+at\s+(?P<file>[^\n(]+?)\((?P<line>\d+)\)")
RGBDS_OLD_RX = re.compile(r"^(?P<sev>ERROR|error|warning):\s*(?P<file>[^\n(:]+?)\((?P<line>\d+)\)(?:\s*->\s*[^:]*)?:\s*$")
SJ_RX = re.compile(r"^(?P<file>[^\n()]+?)\((?P<line>\d+)\):\s*(?P<sev>error|warning|fatal)\s*(?:\[[^\]]*\])?:?\s*(?P<msg>.*)$",
                   re.I)
ACME_RX = re.compile(r"^(?P<sev>Error|Warning|Serious error)\s*-\s*File\s+(?P<file>.+?),\s*line\s+(?P<line>\d+)"
                     r"[^:]*:\s*(?P<msg>.*)$")
UNRESOLVED_RX = re.compile(r"^(?P<name>[A-Za-z_.][\w.]*)\s+0000\s+\?\?\?\?")


def _sev(s: str) -> str:
    return "Warning" if s.lower().startswith("warn") else "Error"


def _rel(file: str, folder: Path | None) -> str:
    f = file.strip().strip('"')
    if folder is None:
        return f.replace("\\", "/")
    p = Path(f)
    try:
        if p.is_absolute():
            return p.resolve().relative_to(Path(folder).resolve()).as_posix()
    except (ValueError, OSError):
        return f
    return p.as_posix()


def parse(text: str, folder: Path | None = None, tool: str = "") -> list[Diag]:
    out: list[Diag] = []
    seen: set[tuple] = set()

    def add(sev, msg, file, line):
        d = Diag(_sev(sev), msg.strip(), _rel(file, folder) if file else "", int(line or 0))
        key = (d.severity, d.message, d.file, d.line)
        if key not in seen:
            seen.add(key)
            out.append(d)

    lines = text.splitlines()
    in_unresolved = False
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        i += 1
        if not ln.strip():
            continue
        if ln.startswith("--- Unresolved Symbol List"):
            in_unresolved = True
            continue
        if in_unresolved:
            m = UNRESOLVED_RX.match(ln.strip())
            if m:
                add("error", f"Unresolved symbol '{m.group('name')}'", "", 0)
                continue
            if ln.startswith("---"):
                in_unresolved = False
            continue
        m = RGBDS_HEAD_RX.match(ln)
        if m and tool in ("", "rgbds", "rgbasm", "rgblink", "rgbfix"):
            file, line = "", 0
            if i < len(lines):
                at = RGBDS_AT_RX.match(lines[i])
                if at:
                    file, line = at.group("file"), at.group("line")
                    i += 1
                    while i < len(lines) and lines[i].lstrip().startswith(("at ", "<-", "~")):
                        i += 1
            add(m.group("sev"), m.group("msg"), file, line)
            continue
        m = RGBDS_OLD_RX.match(ln)
        if m:
            msg = lines[i].strip() if i < len(lines) else ""
            i += 1
            add(m.group("sev"), msg, m.group("file"), m.group("line"))
            continue
        m = ACME_RX.match(ln)
        if m:
            add(m.group("sev"), m.group("msg"), m.group("file"), m.group("line"))
            continue
        m = DASM_RX.match(ln)
        if m:
            add(m.group("sev"), m.group("msg"), m.group("file"), m.group("line"))
            continue
        m = SJ_RX.match(ln)
        if m:
            add(m.group("sev"), m.group("msg"), m.group("file"), m.group("line"))
            continue
        m = CA65_RX.match(ln)
        if m:
            add(m.group("sev"), m.group("msg"), m.group("file"), m.group("line"))
            continue
        m = CC65_PAREN_RX.match(ln)
        if m:
            add(m.group("sev"), m.group("msg"), m.group("file"), m.group("line"))
            continue
        m = TOOL_RX.match(ln)
        if m:
            add(m.group("sev"), f"{m.group('tool')}: {m.group('msg')}", "", 0)
            continue
        if re.match(r"^Fatal assembly error:", ln):
            add("error", ln, "", 0)
    return out
