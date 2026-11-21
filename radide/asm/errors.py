"""Assembler / linker messages -> Error List rows (no Qt in here).

Understood formats (one row per message, file names made relative to the project folder):

    NASM        main.asm:12: error: invalid combination of opcode and operands
                main.asm:3: warning: label alone on a line without a colon [-w+label-orphan]
    GNU as      main.s:12: Error: no such instruction: `movz eax,1'
    gcc         radgui.c:10:5: error: ...           (the C client of the GUI Bridge)
    MASM        main.asm(12) : error A2008:syntax error : eax
    FASM        main.asm [12]:  <source line>  processed: ...  error: invalid operand.
    GNU ld      main.obj:main.asm:(.text+0x11): undefined reference to `foo'
                D:/p/main.asm:13:(.text+0x11): undefined reference to `foo'   (with debug line information)
    MS link     main.obj : error LNK2019: unresolved external symbol foo referenced in function main
    GoLink      Error! The following symbol was not defined in the object file or files:- foo
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

SRC_EXT = r"(?:asm|inc|nasm|mac|s|S|fasm|c|h)"
_DRIVE = r"(?:[A-Za-z]:)?"

NASM_RX = re.compile(rf"^(?P<file>{_DRIVE}[^:\n]+?\.{SRC_EXT}):(?P<line>\d+):(?:\d+:)?\s*"
                     rf"(?P<sev>fatal error|error|warning|fatal|panic|note|Error|Warning|Fatal error)\s*:\s*"
                     rf"(?P<msg>.*)$", re.M)
MASM_RX = re.compile(r"^\s*(?P<file>[^\n(]+?)\((?P<line>\d+)\)\s*:\s*(?P<sev>fatal error|error|warning)\s+"
                     r"(?P<code>[A-Z]\d+)\s*:\s*(?P<msg>.*)$", re.M | re.I)
FASM_LOC_RX = re.compile(r"^(?P<file>\S[^\n\[]*?)\s\[(?P<line>\d+)\](?:\s.*)?:\s*$")
FASM_ERR_RX = re.compile(r"^error:\s*(?P<msg>.+)$")
LD_RX = re.compile(rf"^(?:[^\n]*?\bld(?:\.exe)?:\s+)?(?:(?P<obj>{_DRIVE}[^:\n]+?\.(?:o|obj)):)?"
                   rf"(?P<file>{_DRIVE}[^:\n]+?\.{SRC_EXT}):"
                   rf"(?:(?P<line>\d+):)?\((?P<sect>[.\w$]+)\+0x(?P<off>[0-9a-fA-F]+)\):\s*(?P<msg>.*)$", re.M)
LD_PLAIN_RX = re.compile(r"^(?:.*[\\/])?(?:ld|ld\.exe|collect2(?:\.exe)?)\s*:\s*(?P<msg>.*(?:cannot find|undefined|"
                         r"error|multiple definition).*)$", re.M | re.I)
LINK_RX = re.compile(r"^(?P<file>[^\n:]+?\.(?:obj|lib|exe))\s*:\s*(?P<sev>fatal error|error|warning)\s+"
                     r"(?P<code>LNK\d+)\s*:\s*(?P<msg>.*)$", re.M | re.I)
LINK_TOOL_RX = re.compile(r"^LINK\s*:\s*(?P<sev>fatal error|error|warning)\s+(?P<code>LNK\d+)\s*:\s*(?P<msg>.*)$",
                          re.M | re.I)


@dataclass
class AsmDiag:
    severity: str          # "Error" | "Warning"
    message: str
    file: str              # relative to the project folder when inside it
    line: int              # 1-based (0 = unknown)

    def to_dict(self) -> dict:
        return asdict(self)


def _sev(s: str) -> str:
    s = s.lower()
    return "Warning" if s.startswith("warn") or s == "note" else "Error"


def _rel(file: str, folder: Path | None) -> str:
    f = file.strip().strip('"')
    if folder is None:
        return f
    p = Path(f)
    try:
        if p.is_absolute():
            return p.resolve().relative_to(Path(folder).resolve()).as_posix()
    except (ValueError, OSError):
        return f
    return p.as_posix()


def parse(text: str, folder: Path | None = None, line_of=None) -> list[AsmDiag]:
    """Every message of *text* (build output). ``line_of(file, section, offset) -> line`` resolves the
    ``(.text+0x11)`` locations of linker messages (see build.Builder.line_for_offset)."""
    out: list[AsmDiag] = []
    seen: set[tuple] = set()

    def add(sev, msg, file, line):
        d = AsmDiag(sev, msg.strip(), _rel(file, folder) if file else "", int(line or 0))
        key = (d.severity, d.message, d.file, d.line)
        if key not in seen:
            seen.add(key)
            out.append(d)

    for m in LD_RX.finditer(text):
        line = int(m.group("line") or 0)
        if not line and line_of is not None:
            try:
                line = int(line_of(m.group("file"), m.group("sect"), int(m.group("off"), 16)) or 0)
            except Exception:  # noqa: BLE001 - best effort
                line = 0
        add("Error", m.group("msg"), m.group("file"), line)
    ld_spans = [m.span() for m in LD_RX.finditer(text)]
    for m in NASM_RX.finditer(text):
        if any(a <= m.start() < b for a, b in ld_spans):
            continue
        add(_sev(m.group("sev")), m.group("msg"), m.group("file"), m.group("line"))
    for m in MASM_RX.finditer(text):
        add(_sev(m.group("sev")), f"{m.group('code')}: {m.group('msg')}", m.group("file"), m.group("line"))
    for m in LINK_RX.finditer(text):
        f = m.group("file")
        src = Path(f).with_suffix(".asm").name if f.lower().endswith(".obj") else ""
        add(_sev(m.group("sev")), f"{m.group('code')}: {m.group('msg')}", src, 0)
    for m in LINK_TOOL_RX.finditer(text):
        add(_sev(m.group("sev")), f"{m.group('code')}: {m.group('msg')}", "", 0)
    # FASM: "file [line]:" then the source line, "processed: ...", "error: message"
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        m = FASM_LOC_RX.match(ln)
        if not m:
            continue
        for j in range(i + 1, min(i + 8, len(lines))):
            e = FASM_ERR_RX.match(lines[j].strip())
            if e:
                add("Error", e.group("msg"), m.group("file"), m.group("line"))
                break
            if FASM_LOC_RX.match(lines[j]):
                break
    # GoLink
    if "Error!" in text and "GoLink" in text or re.search(r"^Error!\s*$", text, re.M):
        block = text[text.find("Error!"):].splitlines()[1:6]
        msg = " ".join(s.strip() for s in block if s.strip() and not s.lower().startswith("output file"))
        add("Error", f"GoLink: {msg}" if msg else "GoLink failed", "", 0)
    if not out:
        for m in LD_PLAIN_RX.finditer(text):
            add("Error", m.group("msg"), "", 0)
    return out


_UNRESOLVED_RX = re.compile(r"unresolved external symbol\s+_?([\w@?$.]+)|undefined reference to [`'\"]_?([\w@?$.]+)'")
_DECL_RX = re.compile(r"^\s*(?:extern|externdef|extrn|global|public|\.globl|\.global|\.extern|includelib|import|"
                      r"library)\b|\bproto\b", re.I)


def locate_unresolved(diags: list[AsmDiag], folder: Path, files: list[str]) -> list[AsmDiag]:
    """Linker messages without a line ("unresolved external symbol foo"): point them at the first line of the
    project's sources that uses the symbol (declarations are skipped)."""
    texts: dict[str, list[str]] = {}
    for f in files:
        try:
            texts[f] = (Path(folder) / f).read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
    for d in diags:
        if d.line:
            continue
        m = _UNRESOLVED_RX.search(d.message)
        if not m:
            continue
        sym = (m.group(1) or m.group(2) or "").split("@")[0].lstrip("_")
        if not sym:
            continue
        rx = re.compile(rf"(?<![\w@$?.])_?{re.escape(sym)}(?:@\d+)?(?![\w@$?])")
        order = sorted(texts, key=lambda f: (Path(f).name.lower() != Path(d.file).name.lower(), f))
        for f in order:
            hit = next((i for i, ln in enumerate(texts[f], 1)
                        if rx.search(ln.split(";", 1)[0].split("#", 1)[0]) and not _DECL_RX.search(ln)), 0)
            if hit:
                d.file, d.line = f, hit
                break
    return diags


__all__ = ["AsmDiag", "locate_unresolved", "parse"]
