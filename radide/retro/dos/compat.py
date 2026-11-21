"""Old DOS source compatibility (no Qt in here).

``scan(path, text, kind)`` looks at an old QBasic / QuickBASIC, Turbo Pascal, Turbo C, MASM / TASM or batch
source and returns ``CompatNote`` rows: things the free compilers cannot build (proprietary pieces) and what RAD
IDE does about them. ``build.py`` turns them into Error List warnings and uses ``needs_*`` to pick options
(Turbo C conio extras -> tcconio.h forced in; <graphics.h> -> RAD IDE's BGI subset; line numbers -> fine).

``detect_kind(path, text)`` tells which DOS project kind a loose file belongs to (Open Folder).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

EXT_KIND = {".bas": "qbasic", ".bi": "qbasic", ".pas": "pascal", ".pp": "pascal", ".inc": "pascal",
            ".c": "c", ".h": "c", ".asm": "asm", ".bat": "batch"}


@dataclass
class CompatNote:
    severity: str        # Warning | Message
    message: str
    line: int = 0


# ---------------------------------------------------------------------------- detection
_QB_HINTS = re.compile(r"(?im)^\s*(\d+\s+)?(DECLARE\s+(SUB|FUNCTION)|DEFINT|SCREEN\s+\d|LOCATE\s+\d|COLOR\s+\d|"
                       r"PRINT\b|GOSUB\b|INPUT\b|CLS\b|DIM\s+SHARED)")
_VB_HINTS = re.compile(r"(?im)^\s*(Attribute\s+VB_|Private\s+Sub\s+\w+_Click|VERSION\s+\d+\.\d+\s+CLASS|"
                       r"Begin\s+VB\.)")
_TP_HINTS = re.compile(r"(?im)^\s*(uses\s+.*\b(crt|dos|graph|printer|overlay)\b|\{\$[MINR]\s|program\s+\w+\s*;)")
_DELPHI_HINTS = re.compile(r"(?im)^\s*(uses\s+.*\b(Forms|Windows|SysUtils|Classes|Vcl\.\w+)\b|\{\$R\s+\*\.(res|dfm)\})")
_TC_HINTS = re.compile(r"(?m)#\s*include\s*<(conio|dos|graphics|bios|alloc|dir|mem|process)\.h>|\bfar\b|\binterrupt\b|"
                       r"\bint86x?\s*\(|\bMK_FP\b|\bclrscr\s*\(")
_ASM16_HINTS = re.compile(r"(?im)^\s*(\.model\s+(tiny|small|medium|compact|large|huge)|org\s+100h|"
                          r"int\s+21h|assume\s+cs|\.8086|\.186|\.286)")


def detect_kind(path: Path, text: str) -> str:
    """'qbasic' | 'pascal' | 'c' | 'asm' | 'batch' | '' (not a DOS source as far as we can tell)."""
    ext = Path(path).suffix.lower()
    kind = EXT_KIND.get(ext, "")
    if kind == "qbasic":
        if _VB_HINTS.search(text):
            return ""                      # a VB6 module
        return "qbasic" if (_QB_HINTS.search(text) or re.search(r"(?m)^\s*\d+\s+\S", text)) else ""
    if kind == "pascal":
        if _DELPHI_HINTS.search(text):
            return ""
        return "pascal" if _TP_HINTS.search(text) else ""
    if kind == "c":
        return "c" if _TC_HINTS.search(text) else ""
    if kind == "asm":
        return "asm" if _ASM16_HINTS.search(text) else ""
    if kind == "batch":
        return "batch"
    return ""


def has_line_numbers(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    numbered = sum(1 for ln in lines if re.match(r"^\s*\d+\s", ln))
    return numbered >= max(1, len(lines) * 2 // 3)


# ---------------------------------------------------------------------------- per language
TC_CONIO_EXTRAS = ("clrscr", "clreol", "gotoxy", "wherex", "wherey", "textcolor", "textbackground", "textattr",
                   "highvideo", "lowvideo", "normvideo", "window")
_BGI_FUNCS = ("initgraph", "closegraph", "outtextxy", "setfillstyle", "getmaxx", "bar3d")


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def needs_tcconio(text: str) -> bool:
    """Turbo C conio extras used without tcconio.h (and not defined by the program itself)."""
    if re.search(r'#\s*include\s*[<"]tcconio\.h[>"]', text, re.I):
        return False
    for f in TC_CONIO_EXTRAS:
        if re.search(rf"\b{f}\s*\(", text) and not re.search(rf"^\w[\w\s\*]*\b{f}\s*\([^;]*\)\s*\{{", text, re.M):
            return True
    return False


def scan_c(text: str) -> list[CompatNote]:
    out = []
    m = re.search(r"#\s*include\s*<graphics\.h>", text)
    if m:
        out.append(CompatNote("Warning", "graphics.h (Borland BGI): RAD IDE's BGI subset (tcgraph.h, 640x480x16 "
                              "through the BIOS) is used instead - .BGI / .CHR drivers are not loaded; arcs, pie "
                              "slices, fonts and images are not supported.", _line_of(text, m.start())))
    m = re.search(r"initgraph\s*\([^)]*\"([^\"]+)\"", text)
    if m and m.group(1).strip():
        out.append(CompatNote("Message", f"initgraph path \"{m.group(1)}\" is ignored (no .BGI driver is needed).",
                              _line_of(text, m.start())))
    if needs_tcconio(text):
        out.append(CompatNote("Message", "Turbo C conio functions (clrscr, gotoxy, textcolor, ...) come from RAD "
                              "IDE's tcconio.h, included automatically."))
    for hdr in ("bios.h", "alloc.h", "dir.h", "mem.h"):
        m = re.search(rf"#\s*include\s*<{re.escape(hdr)}>", text)
        if m:
            out.append(CompatNote("Warning", f"<{hdr}> is Borland-specific: Open Watcom offers similar functions "
                                  f"in other headers (malloc.h, direct.h, string.h, bios.h) - check the names.",
                                  _line_of(text, m.start())))
    m = re.search(r"\basm\s*\{|\basm\s+\w", text)
    if m:
        out.append(CompatNote("Warning", "Turbo C inline 'asm' statements: Open Watcom uses _asm { ... } (or "
                              "#pragma aux).", _line_of(text, m.start())))
    for m in re.finditer(r"\b(_AX|_BX|_CX|_DX|_AH|_AL|_DS|_ES)\b", text):
        out.append(CompatNote("Warning", f"Turbo C pseudo-register {m.group(1)} is not available in Open Watcom: "
                              "use union REGS and int86().", _line_of(text, m.start())))
        break
    return out


def scan_pascal(text: str, folder: Path | None = None) -> list[CompatNote]:
    out = []
    m = re.search(r"(?im)^\s*uses\s+([^;]+);", text)
    if m:
        units = [u.strip().split()[0] for u in m.group(1).split(",") if u.strip()]
        builtin = {"crt", "dos", "graph", "strings", "printer", "objects", "sysutils", "math", "ports", "go32",
                   "drivers", "views", "app", "dialogs", "menus", "memory", "msmouse", "mouse", "keyboard", "video"}
        for u in units:
            low = u.lower()
            if low in ("overlay",):
                out.append(CompatNote("Warning", "Unit Overlay: overlays are not supported by Free Pascal; the "
                                      "program is linked as one EXE.", _line_of(text, m.start())))
            elif low not in builtin and folder is not None:
                src = [p for p in Path(folder).iterdir() if p.stem.lower() == low and p.suffix.lower() in
                       (".pas", ".pp")]
                tpu = [p for p in Path(folder).iterdir() if p.stem.lower() == low and p.suffix.lower() == ".tpu"]
                if not src and tpu:
                    out.append(CompatNote("Warning", f"Unit {u}: only {tpu[0].name} (compiled Turbo Pascal unit) "
                                          "is here - a .TPU cannot be used by Free Pascal; the unit's source "
                                          f"({u}.PAS) is needed.", _line_of(text, m.start())))
                elif not src:
                    out.append(CompatNote("Warning", f"Unit {u}: no {u}.PAS in the project folder.",
                                          _line_of(text, m.start())))
    if re.search(r"(?i)\bgraph\b", m.group(1) if m else ""):
        out.append(CompatNote("Message", "Unit Graph: Free Pascal's Graph unit does not need .BGI files "
                              "(InitGraph's driver path is ignored)."))
    m = re.search(r"(?i)\binline\s*\(\s*\$", text)
    if m:
        out.append(CompatNote("Warning", "inline($..) machine code: supported by Free Pascal only in {$asmmode} "
                              "assembler blocks - rewrite it as asm ... end.", _line_of(text, m.start())))
    m = re.search(r"(?i)\{\$O\+\}|\{\$F\+\}", text)
    if m:
        out.append(CompatNote("Message", "Overlay / far-call directives ({$O+} {$F+}) are ignored.",
                              _line_of(text, m.start())))
    return out


def _qb_code(line: str) -> str:
    """A BASIC line without its comment and string literals."""
    out, q = [], False
    body = re.sub(r"^\s*\d+\s+", "", line)
    if re.match(r"(?i)^\s*REM\b", body):
        return ""
    for ch in body:
        if ch == '"':
            q = not q
            continue
        if not q and ch == "'":
            break
        out.append(" " if q else ch)
    return "".join(out)


def scan_qbasic(text: str) -> list[CompatNote]:
    out = []
    if has_line_numbers(text):
        out.append(CompatNote("Message", "Line-numbered BASIC: FreeBASIC -lang qb builds it (GOTO / GOSUB to line "
                              "numbers work)."))
    code_lines = [_qb_code(ln) for ln in text.splitlines()]
    for kw, msg in (("PLAY", "PLAY is not supported by FreeBASIC (QBasic only) - use OUT &H43/&H42/&H61 or run "
                     "the source in your own QBASIC.EXE (Run in QBasic)."),
                    ("SOUND", "SOUND is not supported by FreeBASIC - see the PC Speaker template (OUT / INP), or "
                     "run the source in your own QBASIC.EXE."),
                    ("CALL\\s+INTERRUPT", "CALL INTERRUPT (QuickBASIC QB.LIB) is not available in FreeBASIC; "
                     "use the FreeBASIC DOS headers or run it in your own QuickBASIC."),
                    ("CALL\\s+ABSOLUTE", "CALL ABSOLUTE (machine code in a string) is not supported by FreeBASIC."),
                    ("ON\\s+(TIMER|KEY|PLAY|STRIG|COM)", "Event trapping (ON TIMER / KEY / PLAY ...) is not "
                     "supported by FreeBASIC."),
                    ("DEF\\s+SEG", "DEF SEG / PEEK / POKE: FreeBASIC for DOS maps them to conventional memory "
                     "(works for the video memory at &HA000 / &HB800).")):
        for i, line in enumerate(code_lines, 1):
            if re.search(rf"(?i)\b{kw}\b", line):
                out.append(CompatNote("Message" if msg.startswith("DEF SEG") else "Warning", msg, i))
                break
    return out


def scan_asm(text: str) -> list[CompatNote]:
    out = []
    if re.search(r"(?im)^\s*ideal\b", text):
        out.append(CompatNote("Warning", "TASM IDEAL mode is not supported by JWasm (MASM syntax only)."))
    m = re.search(r"(?im)^\s*\.model\s+(\w+)", text)
    if m and m.group(1).lower() == "flat":
        out.append(CompatNote("Warning", ".model flat is 32-bit: this project builds 16-bit DOS programs.",
                              _line_of(text, m.start())))
    if re.search(r"(?im)^\s*include\s+emu8086\.inc", text):
        out.append(CompatNote("Message", "emu8086.inc is emu8086's own macro file: use the 8086 Assembly (Emulator) "
                              "project for it, or replace the macros by INT 21h calls."))
    return out


def scan(path: Path, text: str, kind: str = "", folder: Path | None = None) -> list[CompatNote]:
    kind = kind or EXT_KIND.get(Path(path).suffix.lower(), "")
    if kind == "c":
        return scan_c(text)
    if kind == "pascal":
        return scan_pascal(text, folder)
    if kind == "qbasic":
        return scan_qbasic(text)
    if kind == "asm":
        return scan_asm(text)
    return []


__all__ = ["CompatNote", "EXT_KIND", "TC_CONIO_EXTRAS", "detect_kind", "has_line_numbers", "needs_tcconio", "scan",
           "scan_asm", "scan_c", "scan_pascal", "scan_qbasic"]
