"""Compiler messages -> Error List rows (no Qt in here).

One parser per tool; every parser returns ``DosDiag`` rows whose ``file`` is the project file's real name
(DOS tools print upper-case 8.3 names) so that a double-click in the Error List opens it.

    FreeBASIC   MAIN.BAS(3) error 9: Expected expression          MAIN.BAS(5) warning 12(0): ...
    Free Pascal MAIN.PAS(10,3) Error: Identifier not found "x"    ... Warning: / Note: / Hint: / Fatal:
    Open Watcom MAIN.C(8): Error! E1011: Symbol 'x' ...           Error! E2028: _foo is an undefined reference
    JWasm       MAIN.ASM(11) : Error A2209: Syntax error: movv
    Turbo Pascal MAIN.PAS(10): Error 3: Unknown identifier.
    Turbo C     Error MAIN.C 5: Undefined symbol 'x' in function main
    DJGPP gcc   main.c:5:3: error: ...
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class DosDiag:
    severity: str          # Error | Warning | Message
    message: str
    file: str = ""
    line: int = 0
    col: int = 0
    tool: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _sev(word: str) -> str:
    w = word.lower().rstrip("!:")
    if w in ("error", "fatal", "severe"):
        return "Error"
    if w in ("warning",):
        return "Warning"
    return "Message"


class _Names:
    """Maps DOS 8.3 names printed by the tools back to the project's files."""

    def __init__(self, folder: Path | None):
        self.map: dict[str, str] = {}
        if folder is not None and Path(folder).is_dir():
            for p in Path(folder).rglob("*"):
                if p.is_file() and "_build" not in p.parts:
                    rel = p.relative_to(folder).as_posix()
                    self.map.setdefault(p.name.lower(), rel)
                    self.map.setdefault(rel.lower(), rel)

    def __call__(self, name: str) -> str:
        n = (name or "").strip().strip('"').replace("\\", "/")
        if not n:
            return ""
        if re.match(r"^[A-Za-z]:/", n):          # C:\MAIN.BAS inside DOSBox-X
            n = n[3:]
        return self.map.get(n.lower()) or self.map.get(Path(n).name.lower()) or n


_FB = re.compile(r"^(?P<f>[^()\s][^()]*?)\((?P<l>\d*)\)\s+(?P<s>error|warning)\s+(?P<n>\d+)(?:\(\d+\))?:\s*(?P<m>.*)$",
                 re.I)
_FPC = re.compile(r"^(?P<f>[^()\s][^()]*?)\((?P<l>\d+)(?:,(?P<c>\d+))?\)\s+(?P<s>Error|Fatal|Warning|Note|Hint):\s*"
                  r"(?P<m>.*)$")
_FPC_NOFILE = re.compile(r"^(?P<s>Error|Fatal):\s*(?P<m>.*)$")
_OW = re.compile(r"^(?P<f>[^()\s][^()]*?)\((?P<l>\d+)\):\s+(?P<s>Error|Warning|Note)!\s+(?P<code>[EWN]\d+):\s*(?P<m>.*)$")
_OW_LINK = re.compile(r"^(?P<s>Error|Warning)!\s+(?P<code>[EW]\d+):\s*(?P<m>.*)$")
_JW = re.compile(r"^(?P<f>[^()\s][^()]*?)\((?P<l>\d+)\)\s*:\s*(?P<s>Error|Warning|Fatal error)\s+(?P<code>[A-Z]\d+):\s*"
                 r"(?P<m>.*)$", re.I)
_JW_NOFILE = re.compile(r"^(?P<s>Error|Fatal error)\s+(?P<code>[A-Z]\d+):\s*(?P<m>.*)$", re.I)
_TP = re.compile(r"^(?P<f>[^()\s][^()]*?)\((?P<l>\d+)\):\s*(?P<s>Error|Warning)\s+(?P<n>\d+):\s*(?P<m>.*)$", re.I)
_TC = re.compile(r"^(?P<s>Error|Warning|Fatal)\s+(?P<f>\S+)\s+(?P<l>\d+):\s*(?P<m>.*)$", re.I)
_GCC = re.compile(r"^(?P<f>[^:\s][^:]*?):(?P<l>\d+):(?:(?P<c>\d+):)?\s*(?P<s>error|warning|note|fatal error):\s*"
                  r"(?P<m>.*)$", re.I)
_GCC_LD = re.compile(r"^.*?:\s*(?P<m>undefined reference to .*)$")


def parse_freebasic(text: str, folder: Path | None = None) -> list[DosDiag]:
    names = _Names(folder)
    out = []
    for line in text.splitlines():
        m = _FB.match(line.strip())
        if m:
            out.append(DosDiag(_sev(m["s"]), f"{m['m'].strip()} (FB {m['s'].lower()} {m['n']})", names(m["f"]),
                               int(m["l"] or 0), 0, "freebasic"))
    return out


def parse_fpc(text: str, folder: Path | None = None) -> list[DosDiag]:
    names = _Names(folder)
    out = []
    for line in text.splitlines():
        s = line.strip()
        m = _FPC.match(s)
        if m:
            sev = _sev(m["s"])
            if m["s"] == "Fatal" and "There were" in m["m"]:
                continue                                  # summary line
            out.append(DosDiag(sev, m["m"].strip(), names(m["f"]), int(m["l"]), int(m["c"] or 0), "fpc"))
            continue
        m = _FPC_NOFILE.match(s)
        if m and "Compilation aborted" not in m["m"]:
            out.append(DosDiag("Error", m["m"].strip(), "", 0, 0, "fpc"))
    return out


def parse_watcom(text: str, folder: Path | None = None) -> list[DosDiag]:
    names = _Names(folder)
    out = []
    for line in text.splitlines():
        s = line.strip()
        m = _OW.match(s)
        if m:
            out.append(DosDiag(_sev(m["s"]), f"{m['code']}: {m['m'].strip()}", names(m["f"]), int(m["l"]), 0,
                               "openwatcom"))
            continue
        m = _OW_LINK.match(s)
        if m:
            out.append(DosDiag(_sev(m["s"]), f"{m['code']}: {m['m'].strip()}", "", 0, 0, "wlink"))
    return out


def parse_jwasm(text: str, folder: Path | None = None) -> list[DosDiag]:
    names = _Names(folder)
    out = []
    for line in text.splitlines():
        s = line.strip()
        m = _JW.match(s)
        if m:
            out.append(DosDiag("Error" if "error" in m["s"].lower() else "Warning",
                               f"{m['code']}: {m['m'].strip()}", names(m["f"]), int(m["l"]), 0, "jwasm"))
            continue
        m = _JW_NOFILE.match(s)
        if m:
            out.append(DosDiag("Error", f"{m['code']}: {m['m'].strip()}", "", 0, 0, "jwasm"))
    return out


def parse_turbo_pascal(text: str, folder: Path | None = None) -> list[DosDiag]:
    names = _Names(folder)
    return [DosDiag(_sev(m["s"]), f"{m['m'].strip()} (TP {m['s'].lower()} {m['n']})", names(m["f"]), int(m["l"]), 0,
                    "tpc") for m in (_TP.match(x.strip()) for x in text.splitlines()) if m]


def parse_turbo_c(text: str, folder: Path | None = None) -> list[DosDiag]:
    names = _Names(folder)
    return [DosDiag(_sev(m["s"]), m["m"].strip(), names(m["f"]), int(m["l"]), 0, "tcc")
            for m in (_TC.match(x.strip()) for x in text.splitlines()) if m]


def parse_gcc(text: str, folder: Path | None = None) -> list[DosDiag]:
    names = _Names(folder)
    out = []
    for line in text.splitlines():
        s = line.strip()
        m = _GCC.match(s)
        if m:
            out.append(DosDiag(_sev(m["s"].split()[-1]), m["m"].strip(), names(m["f"]), int(m["l"]),
                               int(m["c"] or 0), "gcc"))
            continue
        m = _GCC_LD.match(s)
        if m:
            out.append(DosDiag("Error", m["m"].strip(), "", 0, 0, "ld"))
    return out


def parse_quickbasic(text: str, folder: Path | None = None, source: str = "", file: str = "") -> list[DosDiag]:
    """BC.EXE prints the offending source line ("0030   0006    Y =") and a caret line ("^ Expected: ...")."""
    out = []
    last_line = 0
    for line in text.splitlines():
        m = re.match(r"^\s*([0-9A-F]{4})\s+([0-9A-F]{4})\s+(.*)$", line)
        if m:
            last_line = 0
            src_text = m.group(3).strip()
            if source and src_text:
                for i, sl in enumerate(source.splitlines(), 1):
                    if sl.strip() == src_text:
                        last_line = i
                        break
            continue
        m = re.match(r"^\s*\^\s*(.+)$", line)
        if m:
            out.append(DosDiag("Error", m.group(1).strip(), file, last_line, 0, "bc"))
    return out


PARSERS = {"freebasic": parse_freebasic, "fpc": parse_fpc, "openwatcom": parse_watcom, "jwasm": parse_jwasm,
           "turbopascal": parse_turbo_pascal, "turboc": parse_turbo_c, "djgpp": parse_gcc}


def parse(tool: str, text: str, folder: Path | None = None) -> list[DosDiag]:
    fn = PARSERS.get(tool)
    return fn(text, folder) if fn else []


__all__ = ["DosDiag", "PARSERS", "parse", "parse_fpc", "parse_freebasic", "parse_gcc", "parse_jwasm",
           "parse_quickbasic", "parse_turbo_c", "parse_turbo_pascal", "parse_watcom"]
