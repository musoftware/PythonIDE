"""Editor support of the retro assembly dialects (no Qt in here): completions, hover, go to definition,
outline and the Monaco (Monarch) grammar of DASM, ca65, RGBDS and sjasmplus sources.

* Mnemonics come with their addressing modes, opcodes, byte counts, cycles and flags (radide/retro/cpu tables).
* Hardware registers of the project's system come with the descriptions of radide/retro/cpu/hwregs.py.
* Labels, equates and macros come from every source of the project (``index_project``).
* Hovering a number shows it in hex / decimal / binary (and as a hardware register when it is one).
Arabic descriptions are added when the IDE runs in Arabic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..cpu import hwregs

DIRECTIVES = {
    "dasm": """processor org rorg seg seg.u include incbin incdir equ set byte word long .byte .word .long dc dc.b
        dc.w dc.l ds ds.b ds.w hex align subroutine mac macro endm if ifconst ifnconst else endif eif repeat repend
        echo err list end""".split(),
    "ca65": """.segment .byte .word .addr .dbyt .res .include .incbin .macro .endmacro .proc .endproc .scope .endscope
        .if .else .elseif .endif .ifdef .ifndef .define .import .export .importzp .exportzp .global .globalzp .setcpu
        .org .reloc .asciiz .lobytes .hibytes .repeat .endrepeat .align .zeropage .code .rodata .data .bss .enum
        .endenum .struct .endstruct .tag .sizeof .local .charmap .feature .out .warning .error .assert""".split(),
    "rgbds": """SECTION ROM0 ROMX WRAM0 WRAMX HRAM VRAM SRAM OAM BANK ALIGN INCLUDE INCBIN DEF EQU EQUS SET RB RW
        RSRESET RSSET MACRO ENDM REPT ENDR FOR BREAK IF ELIF ELSE ENDC DB DW DL DS EXPORT PURGE CHARMAP NEWCHARMAP
        PUSHS POPS LOAD ENDL ASSERT STATIC_ASSERT PRINTLN PRINT FAIL WARN HIGH LOW SIZEOF STARTOF UNION NEXTU
        ENDU OPT PUSHO POPO""".split(),
    "sjasmplus": """ORG DEVICE OUTPUT INCLUDE INCBIN EQU DEFL DEFB DB DEFW DW DEFS DS DZ DM BYTE WORD ALIGN MACRO ENDM IF
        ELSE ENDIF IFDEF IFNDEF IFUSED REPT ENDR DUP EDUP SAVEBIN SAVETAP SAVESNA SAVENEX MODULE ENDMODULE
        STRUCT ENDS DISP ENT ASSERT DISPLAY OPT LABELSLIST""".split(),
}

REGISTERS = {"6502": ["a", "x", "y"], "sm83": None, "z80": None}
SYSTEM_OF_DIALECT = {"dasm": "atari2600", "rgbds": "gameboy", "sjasmplus": "zx"}
SOURCE_EXT = (".asm", ".s", ".inc", ".h", ".a", ".z80", ".a65", ".i")


def cpu_module(cpu: str):
    from ..cpu import decoder
    return decoder(cpu)


def registers(cpu: str) -> list[str]:
    if cpu == "6502":
        return ["a", "x", "y"]
    return list(cpu_module(cpu).REGISTERS)


def mnemonics(cpu: str, undocumented: bool = True) -> list[str]:
    mod = cpu_module(cpu)
    out = list(mod.MNEMONICS)
    if cpu == "6502" and undocumented:
        out += [m for m in mod.UNDOC_MNEMONICS if m not in out]
    return out


def _ui_ar() -> bool:
    try:
        from ...i18n import language
        return (language() or "").startswith("ar")
    except Exception:  # noqa: BLE001
        return False


# ============================================================================== project index
@dataclass
class Symbol:
    name: str
    kind: str          # label | equate | macro | local
    file: str
    line: int          # 0-based
    value: str = ""


_LABEL_RX = {
    "dasm": re.compile(r"^([A-Za-z_][\w.]*):?(?=\s|$)"),
    "ca65": re.compile(r"^\s*([A-Za-z_@][\w@]*):"),
    "rgbds": re.compile(r"^\s*(\.?[A-Za-z_][\w.]*)::?"),
    "sjasmplus": re.compile(r"^(\.?[A-Za-z_@][\w.@?]*):?(?=\s|$)"),
}
_EQU_RX = re.compile(r"^\s*(?:DEF\s+)?([A-Za-z_][\w.]*)\s*(?::?=|\b(?:equ|EQU|set|SET|defl|DEFL|EQUS)\b)\s*(.*?)\s*(?:;.*)?$")
_MACRO_RX = re.compile(r"^\s*(?:(?:MACRO|macro|mac|MAC|\.macro)\s+([A-Za-z_][\w]*)|([A-Za-z_]\w*):?\s+(?:MACRO|macro)\b)")


def parse_symbols(text: str, dialect: str, file: str = "", cpu: str = "6502") -> list[Symbol]:
    out: list[Symbol] = []
    mn = {m.lower() for m in mnemonics(cpu)} | {d.lower().lstrip(".") for d in DIRECTIVES.get(dialect, [])}
    last_global = ""
    for i, raw in enumerate(text.splitlines()):
        line = raw.split(";", 1)[0].rstrip()
        if not line.strip():
            continue
        m = _MACRO_RX.match(line)
        if m:
            out.append(Symbol(m.group(1) or m.group(2), "macro", file, i))
            continue
        m = _EQU_RX.match(line)
        if m and m.group(1).lower() not in mn:
            out.append(Symbol(m.group(1), "equate", file, i, m.group(2)))
            continue
        m = _LABEL_RX[dialect].match(line)
        if m:
            name = m.group(1)
            if name.lower() in mn or (dialect == "dasm" and not raw[:1].strip()):
                continue
            if name.startswith((".", "@")):
                out.append(Symbol(f"{last_global}{name}" if name.startswith(".") else name, "local", file, i))
            else:
                last_global = name
                out.append(Symbol(name, "label", file, i))
    return out


def index_project(folder, dialect: str, cpu: str, current: tuple[str, str] | None = None) -> list[Symbol]:
    """Symbols of every source file in *folder* (the open editor's text *current* = (path, text) wins)."""
    out: list[Symbol] = []
    seen = set()
    if current:
        out += parse_symbols(current[1], dialect, str(current[0]), cpu)
        seen.add(str(Path(current[0]).resolve()).lower())
    try:
        files = [p for p in Path(folder).iterdir() if p.suffix.lower() in SOURCE_EXT and p.is_file()]
    except OSError:
        files = []
    for p in files[:200]:
        key = str(p.resolve()).lower()
        if key in seen:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        out += parse_symbols(text, dialect, str(p), cpu)
    return out


# ============================================================================== completion / hover
def _word_at(text: str, line: int, col: int, rx=r"[A-Za-z0-9_.@$%#']+") -> str:
    lines = text.splitlines()
    if line >= len(lines):
        return ""
    for m in re.finditer(rx, lines[line]):
        if m.start() <= col <= m.end():
            return m.group(0)
    return ""


def mnemonic_markdown(cpu: str, m: str, ar: bool = False) -> str:
    mod = cpu_module(cpu)
    d = mod.mnemonic_doc(m)
    if not d["modes"] and not d["en"]:
        return ""
    head = f"**{m.upper()}** - {d['en']}"
    if ar and d.get("ar"):
        head += f"  \n{d['ar']}"
    rows = []
    if cpu == "6502":
        from ..cpu.m6502 import MODE_NAMES
        rows.append("| mode | opcode | bytes | cycles |\n|---|---|---|---|")
        for mode, op, size, cyc, und in d["modes"]:
            rows.append(f"| {MODE_NAMES.get(mode, mode)}{' (undoc.)' if und else ''} | ${op:02X} | {size} | {cyc} |")
    else:
        rows.append("| form | opcode | bytes | cycles |\n|---|---|---|---|")
        for form, op, size, cyc in d["modes"][:16]:
            opc = f"${op:04X}" if op > 0xFF else f"${op:02X}"
            rows.append(f"| `{m} {form}`".rstrip() + f" | {opc} | {size} | {cyc} |")
    flags = d.get("flags", "-")
    note = {"6502": "flags N V - B D I Z C", "sm83": "flags Z N H C", "z80": "flags S Z H P/V N C"}[cpu]
    return head + "\n\n" + "\n".join(rows) + f"\n\nFlags changed: **{flags}**  ({note}; cycles: "\
        + ("+ = page cross, b = branch" if cpu == "6502" else "taken/not taken") + ")"


def number_markdown(word: str, system: str) -> str:
    w = word.lstrip("#")
    try:
        if w.startswith("$"):
            v = int(w[1:], 16)
        elif w.lower().startswith("0x"):
            v = int(w[2:], 16)
        elif w.startswith("%"):
            v = int(w[1:], 2)
        elif w.lower().endswith("h") and re.fullmatch(r"[0-9][0-9a-fA-F]*[hH]", w):
            v = int(w[:-1], 16)
        elif w.isdigit():
            v = int(w)
        else:
            return ""
    except ValueError:
        return ""
    txt = f"**{word}** = {v} = ${v:X} = %{v:08b}" if v < 0x100 else f"**{word}** = {v} = ${v:04X}"
    reg = hwregs.lookup(system, v, "rw") if system else None
    if reg is not None:
        txt += f"  \n{reg.name}: {reg.text}"
    return txt


class RetroIntel:
    """Mixed into the retro language plugins (radide/retro/dev/plugin.py): sets ``cpu``, ``dialect``, ``system``."""
    cpu = "6502"
    dialect = "dasm"
    system = "atari2600"

    def _project_folder(self, path) -> Path | None:
        return Path(str(path)).parent if path else None

    def _symbols(self, code: str, path) -> list[Symbol]:
        folder = self._project_folder(path)
        if folder is None:
            return parse_symbols(code, self.dialect, "", self.cpu)
        return index_project(folder, self.dialect, self.cpu, (str(path), code))

    def completions(self, code, line, col, path=None, names=None):
        from ...languages.base import Completion
        out = []
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        stripped = before.lstrip()
        if ";" in before:
            return []
        first_word = not re.search(r"\S\s", stripped) and not re.match(r"^[A-Za-z_][\w.]*:\s", stripped)
        mod = cpu_module(self.cpu)
        if first_word:
            for m in mnemonics(self.cpu):
                d = mod.mnemonic_doc(m)
                cyc = ", ".join(sorted({str(x[3] if self.cpu == "6502" else x[3]) for x in d["modes"]}))[:24]
                out.append(Completion(m, "keyword", f"{d['en'][:60]} [{cyc}]"))
            for dname in DIRECTIVES.get(self.dialect, []):
                out.append(Completion(dname, "statement", "directive"))
        for r in registers(self.cpu):
            out.append(Completion(r, "variable", "register"))
        for reg in hwregs.REGS.get(self.system, []):
            out.append(Completion(reg.name, "property", f"${reg.addr:04X} {reg.text[:70]}"))
        seen = {c.name.lower() for c in out}
        for s in self._symbols(code, path):
            if s.name.lower() in seen:
                continue
            seen.add(s.name.lower())
            kind = {"macro": "function", "equate": "variable", "label": "function", "local": "function"}[s.kind]
            out.append(Completion(s.name, kind, f"{s.kind} {s.value}".strip() + f" ({Path(s.file).name}:{s.line + 1})"))
        return out

    def calltip(self, code, line, col, path=None, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.match(r"^\s*(?:[A-Za-z_][\w.]*:\s*)?([A-Za-z]{2,5})(?:\.w)?\s", before)
        if not m:
            return ""
        d = cpu_module(self.cpu).mnemonic_doc(m.group(1))
        if not d["modes"]:
            return ""
        if self.cpu == "6502":
            from ..cpu.m6502 import MODE_NAMES
            return f"{m.group(1).upper()}: " + ", ".join(MODE_NAMES.get(x[0], x[0]) for x in d["modes"])
        return f"{m.group(1)} " + " | ".join(x[0] for x in d["modes"][:10])

    def hover(self, code, line, col, path=None, names=None):
        word = _word_at(code, line, col)
        if not word:
            return ""
        ar = _ui_ar()
        base = word.split(".")[0] if self.cpu == "6502" else word
        lw = base.lower()
        if lw in {m.lower() for m in mnemonics(self.cpu)}:
            return mnemonic_markdown(self.cpu, lw, ar)
        regs = {r.name.lower(): r for r in hwregs.REGS.get(self.system, [])}
        if word.lower() in regs:
            r = regs[word.lower()]
            acc = {"r": "read", "w": "write", "rw": "read / write", "call": "ROM routine (call it)",
                   "var": "memory / system variable"}.get(r.access, r.access)
            return f"**{r.name}** = ${r.addr:04X} ({acc})  \n{r.text}"
        if re.match(r"^#?(\$[0-9A-Fa-f]+|%[01]+|0x[0-9A-Fa-f]+|\d+|[0-9][0-9A-Fa-f]*[hH])$", word):
            txt = number_markdown(word, self.system)
            if self.system == "zx" and word.lstrip("#$").upper() in ("FE", "1F", "FD"):
                txt += "  \n" + hwregs.ZX_PORTS.get(int(word.lstrip("#$"), 16), "")
            return txt
        for s in self._symbols(code, path):
            if s.name == word or s.name.endswith(word) and word.startswith("."):
                try:
                    src = Path(s.file).read_text(encoding="utf-8", errors="replace").splitlines()[s.line].strip() \
                        if s.file and Path(s.file).is_file() and str(s.file) != str(path) else \
                        code.splitlines()[s.line].strip()
                except (OSError, IndexError):
                    src = ""
                return f"**{s.name}** ({s.kind}, {Path(s.file).name or 'this file'} line {s.line + 1})  \n`{src}`"
        d = DIRECTIVES.get(self.dialect, [])
        if word.lower() in {x.lower() for x in d}:
            return f"**{word}** - {self.dialect} directive"
        return ""

    def definition(self, code, line, col, path=None, names=None):
        word = _word_at(code, line, col, r"[A-Za-z0-9_.@]+")
        if not word:
            return None
        cur_global = ""
        for i, raw in enumerate(code.splitlines()[:line + 1]):
            m = _LABEL_RX[self.dialect].match(raw.split(";", 1)[0])
            if m and not m.group(1).startswith((".", "@")):
                cur_global = m.group(1)
        targets = {word, cur_global + word} if word.startswith(".") else {word}
        for s in self._symbols(code, path):
            if s.name in targets:
                return (s.file or str(path), s.line)
        return None

    def references(self, code, line, col, path=None, names=None):
        word = _word_at(code, line, col, r"[A-Za-z0-9_.@]+")
        if not word:
            return None
        out = []
        folder = self._project_folder(path)
        files = [(str(path), code)]
        if folder is not None:
            for p in folder.iterdir():
                if p.suffix.lower() in SOURCE_EXT and str(p.resolve()).lower() != str(Path(str(path)).resolve()).lower():
                    try:
                        files.append((str(p), p.read_text(encoding="utf-8", errors="replace")))
                    except OSError:
                        pass
        rx = re.compile(rf"(?<![\w.@]){re.escape(word)}(?![\w])")
        for f, text in files:
            for i, ln in enumerate(text.splitlines()):
                for m in rx.finditer(ln.split(";", 1)[0]):
                    out.append((f, i, m.start()))
        return out

    def document_symbols(self, code):
        out = []
        for s in parse_symbols(code, self.dialect, "", self.cpu):
            if s.kind == "local":
                continue
            out.append({"name": s.name, "kind": {"macro": "function", "equate": "constant", "label": "function"}
                        .get(s.kind, "variable"), "line": s.line, "detail": s.value or s.kind, "children": []})
        return out

    def monaco_language(self, path) -> dict | None:
        return monarch_spec(self.dialect, self.cpu, self.system)


# ============================================================================== Monarch
def monarch_spec(dialect: str, cpu: str, system: str) -> dict:
    regs = registers(cpu)
    hw = sorted({r.name for r in hwregs.REGS.get(system, [])})
    dirs = DIRECTIVES.get(dialect, [])
    root = [
        [r";.*$", "comment"],
        [r'"', "string", "@dstring"],
        [r"'(?:[^'\\]|\\.)'", "string"],
        [r"\$[0-9A-Fa-f]+\b", "number.hex"],
        [r"0[xX][0-9A-Fa-f]+\b", "number.hex"],
        [r"%[01]+\b", "number.binary"],
        [r"\b[0-9][0-9A-Fa-f]*[hH]\b", "number.hex"],
        [r"\b\d+\b", "number"],
        [r"#", "operator"],
        [r"^[A-Za-z_@.][\w.@]*:?(?=\s|$)" if dialect in ("dasm", "sjasmplus") else r"[A-Za-z_@.][\w.@]*(?=::?)",
         "type.identifier"],
        [r"\.?[A-Za-z_@][\w.@]*", {"cases": {"@instructions": "keyword", "@registers": "variable.predefined",
                                              "@directives": "keyword.directive", "@hardware": "constant",
                                              "@default": "identifier"}}],
        [r"[\[\]()]", "@brackets"],
        [r"[+\-*/&|^~<>=!,:]", "operator"],
    ]
    if dialect == "ca65":
        root.insert(9, [r"@[A-Za-z_]\w*", "type.identifier"])
        root.insert(9, [r":[+\-]+", "type.identifier"])
    monarch = {
        "ignoreCase": True, "defaultToken": "", "tokenPostfix": ".retro",
        "instructions": mnemonics(cpu) + [m + ".w" for m in mnemonics(cpu)] if dialect == "dasm" else mnemonics(cpu),
        "registers": regs, "directives": [d.lower() for d in dirs] + dirs, "hardware": hw,
        "brackets": [{"open": "[", "close": "]", "token": "delimiter.square"},
                     {"open": "(", "close": ")", "token": "delimiter.parenthesis"}],
        "tokenizer": {"root": root, "dstring": [[r'[^\\"]+', "string"], [r"\\.", "string.escape"],
                                                 [r'"', "string", "@pop"]]},
    }
    conf = {"comments": {"lineComment": ";"}, "brackets": [["[", "]"], ["(", ")"]],
            "autoClosingPairs": [{"open": "[", "close": "]"}, {"open": "(", "close": ")"},
                                 {"open": '"', "close": '"', "notIn": ["string", "comment"]}],
            "wordPattern": r"(-?\d*\.\d\w*)|([A-Za-z_.@$%][\w.@]*)"}
    return {"id": f"rad-retro-{dialect}", "aliases": [f"Retro ({dialect})", dialect], "extensions": [],
            "monarch": monarch, "conf": conf, "triggers": ["."], "dialect": dialect}
