"""Legacy (fixed-form) Fortran for old NASA / scientific code: FORTRAN IV, Fortran 66 and Fortran 77.

No Qt in the top half (tested headless); the Qt part (card deck window, conversion preview) is at the bottom.

* Fixed form: columns 1-5 statement number, 6 continuation (any character but blank / 0), 7-72 the statement,
  73-80 the card sequence number (ignored by the compiler); ``C``, ``c``, ``*`` or ``!`` in column 1 = comment.
  ``fields(line)`` splits a card; ``editor_js()`` adds rulers at 6 / 72 and greys columns 73-80 in Monaco.
* ``PRESETS`` - gfortran option sets (``-std=legacy -ffixed-form``, ``-fno-automatic`` for FORTRAN IV / 66
  SAVE semantics, ``-fdec`` for DEC / VAX extensions, a strict F95 check); ``compile_command``.
* ``analyze(text)`` - legacy constructs with an explanation each: arithmetic IF, computed / assigned GO TO,
  Hollerith constants, PAUSE, EQUIVALENCE, COMMON, ENTRY, shared DO terminals, ...
* ``to_free_form(text)`` - conversion to free-form Fortran 90 (comments ``!``, continuation ``&``, Hollerith
  to quoted strings, sequence numbers dropped) + ``diff`` for the preview.
* ``punch_rows(ch)`` / ``card_columns(line)`` - IBM 029 keypunch codes: the "card deck" view draws a line as
  the punched card it once was.
* ``parse_gfortran(output)`` - gfortran diagnostics -> (severity, file, line, message) for the Error List.

    python -m radide.retro.legacy_fortran run <project folder>     # build with the preset and run (F5)
    python -m radide.retro.legacy_fortran convert prog.f > prog.f90
"""
from __future__ import annotations

import difflib
import os
import re
import subprocess
import sys
from pathlib import Path

FIXED_EXT = (".f", ".for", ".f77", ".ftn", ".fpp", ".f66")
EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

PRESETS: dict[str, tuple[str, list[str], str]] = {
    "legacy": ("Fortran 77 (legacy, fixed form)", ["-std=legacy", "-ffixed-form", "-ffixed-line-length-72"],
               "Fortran 77 / 66 code, every old construct accepted, columns 73-80 ignored."),
    "f66": ("FORTRAN IV / 66 (static variables)", ["-std=legacy", "-ffixed-form", "-ffixed-line-length-72",
                                                   "-fno-automatic", "-finit-local-zero"],
            "Old compilers kept local variables between calls and many programs rely on it: -fno-automatic "
            "(like SAVE everywhere) and -finit-local-zero."),
    "dec": ("DEC / VAX Fortran extensions", ["-std=legacy", "-ffixed-form", "-fdec", "-fno-automatic"],
            "-fdec: STRUCTURE / RECORD, UNION, TYPE as PRINT, .XOR., D lines, ... (gfortran 7+)."),
    "strict": ("Check against Fortran 95 (warnings)", ["-std=f95", "-ffixed-form", "-ffixed-line-length-72",
                                                       "-Wall", "-pedantic"],
               "Reports what modern Fortran deleted or marked obsolescent - useful before converting."),
}

# ============================================================================ fixed form
COMMENT_RX = re.compile(r"^[cC*!dD]")          # D = debug line (comment unless -fd-lines-as-code)


def is_comment(line: str) -> bool:
    return not line.strip() or bool(COMMENT_RX.match(line))


def expand_tabs(line: str) -> str:
    """DEC tab format: a TAB in columns 1-6 starts the statement field (a digit after it = continuation)."""
    if "\t" not in line[:7]:
        return line
    head, _, rest = line.partition("\t")
    if head and is_comment(head):
        return line
    if rest[:1].isdigit() and rest[:1] != "0":
        return (head.ljust(5) + rest[0] + rest[1:])
    return head.ljust(6) + rest


def fields(line: str) -> dict:
    """{label, cont, stmt, seq, comment} of one card."""
    line = expand_tabs(line.rstrip("\r\n"))
    if is_comment(line):
        return {"label": "", "cont": "", "stmt": "", "seq": line[72:80], "comment": line[:72]}
    label = line[:5]
    cont = line[5:6]
    return {"label": label.strip(), "cont": cont if cont not in (" ", "0", "") else "", "stmt": line[6:72],
            "seq": line[72:80], "comment": ""}


def logical_statements(text: str) -> list[tuple[int, str, str, list[int]]]:
    """(first line 0-based, label, joined statement, physical lines) with continuations joined."""
    out: list[list] = []
    for i, raw in enumerate(text.splitlines()):
        f = fields(raw)
        if f["comment"] or (not f["stmt"].strip() and not f["label"] and not f["cont"]):
            continue
        if f["cont"] and out:
            out[-1][2] += f["stmt"].rstrip()
            out[-1][3].append(i)
        else:
            out.append([i, f["label"], f["stmt"].rstrip(), [i]])
    return [tuple(x) for x in out]


def column_note(line: str, col: int) -> str:
    """What the column (1-based) of a fixed-form line means (hover / status bar)."""
    if is_comment(line):
        return "comment line (C, * or ! in column 1)"
    if col <= 5:
        return "columns 1-5: statement number (label)"
    if col == 6:
        return "column 6: continuation mark (any character except blank or 0 continues the previous line)"
    if col <= 72:
        return "columns 7-72: the statement"
    return "columns 73-80: card sequence number - ignored by the compiler"


# ============================================================================ analysis
ARITH_IF = re.compile(r"^\s*IF\s*\((?P<expr>.*)\)\s*(?P<a>\d+)\s*,\s*(?P<b>\d+)\s*,\s*(?P<c>\d+)\s*$", re.I)
COMPUTED_GOTO = re.compile(r"^\s*GO\s*TO\s*\(\s*[\d\s,]+\)\s*,?\s*\w+", re.I)
ASSIGNED_GOTO = re.compile(r"^\s*GO\s*TO\s*[A-Z]\w*\s*(,|$)", re.I)
ASSIGN = re.compile(r"^\s*ASSIGN\s+\d+\s+TO\s+\w+", re.I)
HOLLERITH = re.compile(r"(?<![A-Z0-9_.])(\d+)\s*H", re.I)
DO_LABEL = re.compile(r"^\s*DO\s*(\d+)\s*,?\s*[A-Z]\w*\s*=", re.I)

NOTES = {
    "arith_if": ("Arithmetic IF: IF (e) n1, n2, n3 jumps to n1 when e < 0, n2 when e = 0, n3 when e > 0. "
                 "Obsolescent; in modern Fortran: IF (e < 0) THEN ... ELSE IF (e == 0) ...",
                 "IF الحسابية: تقفز إلى n1 إذا كانت القيمة سالبة و n2 إذا صفراً و n3 إذا موجبة."),
    "computed_goto": ("Computed GO TO (n1, n2, ...), i jumps to the i-th label (falls through when i is out of "
                      "range). Modern form: SELECT CASE (i).", "GO TO المحسوبة: تقفز إلى الرقم رقم i في القائمة."),
    "assigned_goto": ("Assigned GO TO: ASSIGN 10 TO K ... GO TO K. Deleted in Fortran 95 (gfortran accepts it "
                      "with -std=legacy).", "GO TO المخصصة: محذوفة من Fortran 95."),
    "hollerith": ("Hollerith constant nHtext: the n characters after H are the text (FORMAT (5HHELLO)). Count "
                  "exactly! Modern form: 'text'.", "ثابت هوليريث: الحروف n بعد H هي النص. عدّها بدقة!"),
    "pause": ("PAUSE stops until the operator continues (deleted in Fortran 95).", "PAUSE توقف حتى يتابع المشغّل."),
    "equivalence": ("EQUIVALENCE makes variables share memory (old memory saving trick).",
                    "EQUIVALENCE تجعل المتغيرات تتشارك الذاكرة."),
    "common": ("COMMON /name/ - global storage shared by subprograms (modern form: a MODULE).",
               "COMMON مخزن عام تتشاركه البرامج الفرعية (البديل الحديث MODULE)."),
    "entry": ("ENTRY - a second entry point into a subprogram (obsolescent).", "ENTRY نقطة دخول ثانية."),
    "shared_do": ("Several DO loops end on the same statement (obsolescent): give each loop its own CONTINUE "
                  "or END DO.", "عدة حلقات DO تنتهي عند نفس العبارة."),
    "implicit": ("Implicit typing: names starting with I-N are INTEGER, others REAL (no IMPLICIT NONE).",
                 "الأنواع الضمنية: الأسماء من I إلى N صحيحة والباقي حقيقية."),
    "data_stop": ("STOP / RETURN with a number or text is fine; CALL EXIT is an old library routine.",
                  "CALL EXIT روتين قديم."),
}


def analyze(text: str) -> list[tuple[int, str, str, str]]:
    """[(0-based line, kind, English note, Arabic note)] of legacy constructs."""
    out = []
    do_ends: dict[str, int] = {}
    for first, _label, stmt, _lines in logical_statements(text):
        s = stmt.strip()
        up = s.upper()
        kind = None
        if ARITH_IF.match(s):
            kind = "arith_if"
        elif COMPUTED_GOTO.match(s):
            kind = "computed_goto"
        elif ASSIGN.match(s) or (ASSIGNED_GOTO.match(s) and not up.replace(" ", "").startswith("GOTO(")
                                 and not re.match(r"^\s*GO\s*TO\s*\d", s, re.I)):
            kind = "assigned_goto"
        elif re.match(r"^\s*PAUSE\b", s, re.I):
            kind = "pause"
        elif re.match(r"^\s*EQUIVALENCE\b", s, re.I):
            kind = "equivalence"
        elif re.match(r"^\s*COMMON\b", s, re.I):
            kind = "common"
        elif re.match(r"^\s*ENTRY\b", s, re.I):
            kind = "entry"
        if kind:
            out.append((first, kind) + NOTES[kind])
        if (up.startswith("FORMAT") or re.match(r"^\s*\d*\s*FORMAT", up) or "DATA" in up[:5]) and \
                HOLLERITH.search(s):
            out.append((first, "hollerith") + NOTES["hollerith"])
        if re.match(r"^\s*END\s*$", s, re.I) or re.match(
                r"^\s*(\w+\s+)?(SUBROUTINE|FUNCTION|PROGRAM|BLOCK\s*DATA)\b", s, re.I):
            do_ends = {}                       # labels are local to each program unit
        m = DO_LABEL.match(s)
        if m:
            lab = m.group(1)
            if lab in do_ends:
                out.append((first, "shared_do") + NOTES["shared_do"])
            do_ends[lab] = first
    if not re.search(r"^\s{6,}IMPLICIT\s+NONE", text, re.I | re.M):
        out.append((0, "implicit") + NOTES["implicit"])
    return out


# ============================================================================ conversion to free form
def hollerith_to_quotes(stmt: str) -> str:
    """nHxxx -> 'xxx' (outside existing quotes)."""
    out = []
    i = 0
    n = len(stmt)
    quote = ""
    while i < n:
        ch = stmt[i]
        if quote:
            out.append(ch)
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in "'\"":
            quote = ch
            out.append(ch)
            i += 1
            continue
        m = re.match(r"(\d+)H", stmt[i:], re.I)
        prev = stmt[i - 1] if i else ""
        if m and not (prev.isalnum() or prev in "_."):
            count = int(m.group(1))
            start = i + len(m.group(0))
            text = stmt[start:start + count].ljust(count)
            out.append("'" + text.replace("'", "''") + "'")
            i = start + count
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _open_hollerith(stmt: str) -> bool:
    """True when a Hollerith constant at the end of *stmt* continues on the next card."""
    for m in HOLLERITH.finditer(stmt):
        if m.end() + int(m.group(1)) > len(stmt):
            return True
    return False


def _fix_blanks(stmt: str) -> str:
    """Blanks were insignificant in fixed form: make the commonest glued forms legal free form."""
    s = re.sub(r"^(\s*)DO(\d+)", r"\1DO \2", stmt, flags=re.I)
    s = re.sub(r"^(\s*)GOTO\b", r"\1GO TO", s, flags=re.I)
    return s


def to_free_form(text: str, hollerith: bool = True, keep_sequence: bool = False, width: int = 100) -> str:
    """Convert fixed-form source to free form (Fortran 90 layout)."""
    lines = text.splitlines()
    out: list[str] = []
    pending_comments: list[str] = []
    stmts = []          # (label, stmt, seq, comments-before)
    for raw in lines:
        f = fields(raw)
        if f["comment"] or (not f["stmt"].strip() and not f["label"] and not f["cont"]):
            body = raw.rstrip("\r\n")
            seq = body[72:80].strip()
            body = body[:72].rstrip()
            if body and COMMENT_RX.match(body):
                pending_comments.append("!" + body[1:] + (("  ! " + seq) if keep_sequence and seq else ""))
            else:
                pending_comments.append("")
            continue
        if f["cont"] and stmts:
            prev = stmts[-1][1]
            in_quote = (prev.count("'") % 2 == 1) or _open_hollerith(prev)
            stmts[-1][1] = prev + (f["stmt"].rstrip() if in_quote else " " + f["stmt"].strip())
            stmts[-1][4].extend(pending_comments)
            pending_comments = []
            continue
        stmts.append([f["label"], f["stmt"].rstrip(), f["seq"].strip(), pending_comments, []])
        pending_comments = []
    for label, stmt, seq, before, inner in stmts:
        out.extend(before)
        body = stmt.strip()
        body = _fix_blanks(body)
        if hollerith:
            body = hollerith_to_quotes(body)
        prefix = (label + " ") if label else ""
        indent = "  "
        text_line = indent + prefix + body
        if keep_sequence and seq:
            text_line += "  ! " + seq
        if len(text_line) <= width:
            out.append(text_line)
        else:
            out.extend(_wrap(text_line, width))
        out.extend(inner)
    out.extend(pending_comments)
    return "\n".join(out).rstrip() + "\n"


def _wrap(line: str, width: int) -> list[str]:
    parts = []
    cur = line
    while len(cur) > width:
        cut = width - 2
        quote = cur[:cut].count("'") % 2 == 1
        if quote:                                  # never split inside a string: back up to before it
            q = cur[:cut].rfind("'")
            cut = max(10, q)
        parts.append(cur[:cut].rstrip() + " &")
        cur = "    &" + cur[cut:]
    parts.append(cur)
    return parts


def diff(old: str, new: str, old_name: str = "fixed.f", new_name: str = "free.f90") -> str:
    return "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), old_name, new_name))


# ============================================================================ punched cards (IBM 029)
ZONE = {"12": 12, "11": 11, "0": 0}
_PUNCH: dict[str, tuple[int, ...]] = {" ": (), "&": (12,), "-": (11,), "/": (0, 1)}
for _i, _c in enumerate("0123456789"):
    _PUNCH[_c] = (_i,)
for _i, _c in enumerate("ABCDEFGHI", 1):
    _PUNCH[_c] = (12, _i)
for _i, _c in enumerate("JKLMNOPQR", 1):
    _PUNCH[_c] = (11, _i)
for _i, _c in enumerate("STUVWXYZ", 2):
    _PUNCH[_c] = (0, _i)
_PUNCH.update({".": (12, 3, 8), "<": (12, 4, 8), "(": (12, 5, 8), "+": (12, 6, 8), "|": (12, 7, 8),
               "!": (11, 2, 8), "$": (11, 3, 8), "*": (11, 4, 8), ")": (11, 5, 8), ";": (11, 6, 8),
               ",": (0, 3, 8), "%": (0, 4, 8), "_": (0, 5, 8), ">": (0, 6, 8), "?": (0, 7, 8),
               ":": (2, 8), "#": (3, 8), "@": (4, 8), "'": (5, 8), "=": (6, 8), '"': (7, 8)})
ROWS = [12, 11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]       # top to bottom on the card


def punch_rows(ch: str) -> tuple[int, ...]:
    """Rows punched for one character on an IBM 029 keypunch (lower case = upper case; characters the
    keypunch did not have punch nothing)."""
    return _PUNCH.get(ch.upper(), ())


def card_columns(line: str) -> list[tuple[str, tuple[int, ...]]]:
    """80 (character, punched rows) pairs of one source line."""
    text = expand_tabs(line.rstrip("\r\n"))[:80].ljust(80)
    return [(c, punch_rows(c)) for c in text]


def card_text(line: str) -> str:
    """A text drawing of the card (for the Output window / tests)."""
    cols = card_columns(line)
    rows = ["  " + "".join(c for c, _r in cols)]
    for r in ROWS:
        rows.append(f"{r:>2}" + "".join("#" if r in rows_ else ("." if r >= 0 else " ") for _c, rows_ in cols))
    return "\n".join(rows)


# ============================================================================ gfortran
def find_gfortran() -> str:
    try:
        from ..languages.c_bridge import find_native
        return find_native(["gfortran"])
    except Exception:  # noqa: BLE001
        import shutil
        return shutil.which("gfortran") or ""


def preset_flags(preset: str, extra: str = "") -> list[str]:
    flags = list(PRESETS.get(preset, PRESETS["legacy"])[1])
    return flags + (extra.split() if extra else [])


def compile_command(sources: list[str], exe: str, preset: str = "legacy", extra: str = "",
                    syntax_only: bool = False) -> list[str]:
    fc = find_gfortran()
    if not fc:
        return []
    argv = [fc] + preset_flags(preset, extra)
    if syntax_only:
        return argv + ["-fsyntax-only"] + sources
    return argv + ["-o", exe] + sources


GF_HEAD = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*$")
GF_MSG = re.compile(r"^(?P<sev>Error|Warning|Fatal Error):\s*(?P<msg>.*)$")
GF_ONELINE = re.compile(r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s*(?P<sev>Error|Warning|Fatal Error):\s*"
                        r"(?P<msg>.*)$")


def parse_gfortran(text: str) -> list[tuple[str, str, int, str]]:
    """(severity, file, line, message) from gfortran's output (multi-line caret format or one-line)."""
    out = []
    cur = None
    for raw in text.splitlines():
        m = GF_ONELINE.match(raw)
        if m:
            out.append(("Warning" if m.group("sev") == "Warning" else "Error", m.group("file"),
                        int(m.group("line")), m.group("msg")))
            cur = None
            continue
        m = GF_HEAD.match(raw)
        if m:
            cur = (m.group("file"), int(m.group("line")))
            continue
        m = GF_MSG.match(raw.strip())
        if m and cur is not None:
            out.append(("Warning" if m.group("sev") == "Warning" else "Error", cur[0], cur[1], m.group("msg")))
            cur = None
    return out


def project_settings(project) -> dict:
    s = {"preset": "legacy", "flags": ""}
    extra = (getattr(project, "extra", {}) or {}).get("fortran")
    if isinstance(extra, dict):
        s.update({k: v for k, v in extra.items() if v is not None})
    return s


def sources_of(folder: Path) -> list[str]:
    folder = Path(folder)
    return sorted(p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in FIXED_EXT)


def build(folder: Path, preset: str = "legacy", extra: str = "", log=print) -> tuple[bool, str]:
    folder = Path(folder).resolve()
    srcs = sources_of(folder)
    if not srcs:
        log("No fixed-form sources (.f / .for / .f77) in the project folder.")
        return False, ""
    out_dir = folder / "_build"
    out_dir.mkdir(exist_ok=True)
    exe = str(out_dir / ("program" + EXE))
    argv = compile_command(srcs, exe, preset, extra)
    if not argv:
        log("gfortran was not found (MinGW-w64: %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64\\bin).")
        return False, ""
    log("> " + " ".join(Path(argv[0]).name if i == 0 else a for i, a in enumerate(argv)))
    env = dict(os.environ)
    env["PATH"] = str(Path(argv[0]).parent) + os.pathsep + env.get("PATH", "")
    r = subprocess.run(argv, cwd=str(folder), capture_output=True, text=True, env=env, creationflags=NO_WINDOW)
    if r.stdout.strip():
        log(r.stdout.rstrip())
    if r.stderr.strip():
        log(r.stderr.rstrip())
    return r.returncode == 0, exe


def run(folder: Path) -> int:
    """F5 helper: build with the project's preset, then run the program (stdin / stdout inherited)."""
    folder = Path(folder).resolve()
    preset, extra = "legacy", ""
    try:
        import json
        d = json.loads((folder / "project.radproj").read_text(encoding="utf-8"))
        f = d.get("fortran") or {}
        preset, extra = f.get("preset", preset), f.get("flags", extra)
    except (OSError, ValueError):
        pass
    print(f"Preset: {PRESETS.get(preset, PRESETS['legacy'])[0]}", flush=True)
    ok, exe = build(folder, preset, extra, log=lambda s: print(s, flush=True))
    if not ok:
        print("*** build failed", flush=True)
        return 2
    env = dict(os.environ)
    fc = find_gfortran()
    if fc:
        env["PATH"] = str(Path(fc).parent) + os.pathsep + env.get("PATH", "")
    print("------", flush=True)
    return subprocess.call([exe], cwd=str(folder), env=env)


def editor_js() -> str:
    """JavaScript for a Monaco editor of a fixed-form file: rulers at 5 / 6 / 72, columns 73-80 greyed,
    the continuation column marked."""
    return r"""(function(){var ed=window.radEditor; if(!ed||window._radFixedForm) return; window._radFixedForm=1;
ed.updateOptions({rulers:[{column:5,color:'#7f7fff40'},{column:6,color:'#7f7fff70'},{column:72,color:'#ff7f7f90'}]});
var st=document.createElement('style'); st.textContent='.radSeqField{color:#9a9a9a !important;font-style:italic;opacity:.65}'+
'.radContCol{background:rgba(255,190,60,.35)}.radLabelCol{color:#b06000 !important}';
document.head.appendChild(st);
function deco(){var m=ed.getModel(); if(!m) return; var out=[]; var n=m.getLineCount();
 for(var i=1;i<=n;i++){var t=m.getLineContent(i);
  if(t.length>72) out.push({range:new monaco.Range(i,73,i,t.length+1),options:{inlineClassName:'radSeqField',
    hoverMessage:{value:'columns 73-80: card sequence number (ignored)'}}});
  if(/^[cC*!dD]/.test(t)) continue;
  if(t.length>5&&t[5]!==' '&&t[5]!=='0'&&t[0]!=='\t') out.push({range:new monaco.Range(i,6,i,7),
    options:{inlineClassName:'radContCol',hoverMessage:{value:'column 6: continuation'}}});
  if(/^ {0,4}\d/.test(t)) out.push({range:new monaco.Range(i,1,i,Math.min(6,t.length+1)),options:{inlineClassName:'radLabelCol'}});}
 window._radFixDecos=ed.deltaDecorations(window._radFixDecos||[],out);}
deco(); ed.onDidChangeModelContent(function(){clearTimeout(window._radFixT);window._radFixT=setTimeout(deco,250);});})();"""


def monaco_language() -> dict:
    """Monarch grammar for fixed-form Fortran: comment lines by column 1, keywords, Hollerith starts."""
    keywords = """PROGRAM SUBROUTINE FUNCTION BLOCK DATA END CALL RETURN STOP PAUSE CONTINUE GO TO GOTO IF THEN ELSE
        ENDIF DO ASSIGN DIMENSION COMMON EQUIVALENCE EXTERNAL INTRINSIC IMPLICIT INTEGER REAL DOUBLE PRECISION
        COMPLEX LOGICAL CHARACTER PARAMETER SAVE ENTRY FORMAT READ WRITE PRINT OPEN CLOSE REWIND BACKSPACE
        ENDFILE INQUIRE NONE""".split()
    intrinsics = """ABS IABS DABS SQRT DSQRT EXP DEXP ALOG DLOG ALOG10 SIN COS TAN ATAN ATAN2 DSIN DCOS DATAN MOD AMOD
        MAX0 MIN0 AMAX1 AMIN1 MAX MIN FLOAT IFIX INT NINT SIGN ISIGN DBLE SNGL REAL AINT ANINT LEN INDEX CHAR
        ICHAR""".split()
    tokenizer = {"root": [
        [r"^[cC*dD].*$", "comment"],
        [r"!.*$", "comment"],
        [r"^ {0,4}\d+", "number.label"],
        [r"'[^']*'", "string"],
        [r"\b\d+[Hh]", "string.hollerith"],
        [r"\.(EQ|NE|LT|LE|GT|GE|AND|OR|NOT|TRUE|FALSE|EQV|NEQV)\.", "operator"],
        [r"\d*\.?\d+([EeDd][+-]?\d+)?", "number"],
        [r"[A-Za-z][A-Za-z0-9_]*", {"cases": {"@keywords": "keyword", "@intrinsics": "predefined",
                                               "@default": "identifier"}}],
    ]}
    monarch = {"ignoreCase": True, "defaultToken": "", "tokenPostfix": ".f77", "keywords": keywords,
               "intrinsics": intrinsics, "tokenizer": tokenizer}
    return {"id": "rad-fortran-fixed", "aliases": ["Fortran (fixed form)", "f77"], "extensions": list(FIXED_EXT),
            "monarch": monarch, "conf": {"comments": {"lineComment": "C"}, "brackets": [["(", ")"]],
                                         "autoClosingPairs": [{"open": "(", "close": ")"}]},
            "folding": {"pairs": [], "section": r"^\s{6,}(PROGRAM|SUBROUTINE|FUNCTION|BLOCK DATA)\b",
                        "label": r"^\s{6,}(PROGRAM|SUBROUTINE|FUNCTION)\b", "lineComment": ["C", "*", "!"]},
            "triggers": []}


# ============================================================================ Qt: card deck window
def card_deck_dialog(parent, text: str, line: int = 0):
    """The card deck: one punched card per source line (arrows / Page Up / Page Down move through the deck)."""
    from PyQt6.QtCore import QPointF, QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QPainter, QPen
    from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

    lines = text.splitlines() or [""]

    class CardWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.line = ""
            self.setMinimumSize(760, 340)
            self.setProperty("i18n_skip", True)

        def paintEvent(self, _e):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            w, h = self.width(), self.height()
            card = QRectF(10, 10, w - 20, h - 20)
            p.fillRect(self.rect(), QColor(60, 60, 64))
            p.setBrush(QColor(246, 236, 200))
            p.setPen(QPen(QColor(150, 130, 90), 1))
            path_r = card.adjusted(0, 0, 0, 0)
            p.drawRoundedRect(path_r, 6, 6)
            p.setBrush(QColor(60, 60, 64))            # the cut corner
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPolygon(*[QPointF(x, y) for x, y in ((card.left() - 1, card.top() - 1),
                                                        (card.left() + 22, card.top() - 1),
                                                        (card.left() - 1, card.top() + 26))])
            cols = card_columns(self.line)
            left, top = card.left() + 14, card.top() + 34
            cw = (card.width() - 28) / 80.0
            rh = (card.height() - 50) / 12.0
            # field shading: 1-5 label, 6 continuation, 73-80 identification
            for c0, c1, col in ((0, 5, QColor(255, 220, 160, 90)), (5, 6, QColor(255, 180, 90, 110)),
                                (72, 80, QColor(200, 200, 200, 110))):
                p.fillRect(QRectF(left + c0 * cw, top - 4, (c1 - c0) * cw, rh * 12 + 4), col)
            f = QFont("Consolas", max(6, int(cw * 0.95)))
            p.setFont(f)
            p.setPen(QColor(40, 30, 20))
            for i, (ch, _rows) in enumerate(cols):          # interpreted text at the top edge
                p.drawText(QRectF(left + i * cw, card.top() + 8, cw, 20), Qt.AlignmentFlag.AlignCenter, ch)
            small = QFont("Arial", max(5, int(min(cw, rh) * 0.55)))
            p.setFont(small)
            for ri, r in enumerate(ROWS):
                for i, (_ch, rows) in enumerate(cols):
                    cell = QRectF(left + i * cw + cw * 0.18, top + ri * rh + rh * 0.12, cw * 0.64, rh * 0.76)
                    if r in rows:
                        p.fillRect(cell, QColor(25, 25, 28))
                    elif r >= 0:
                        p.setPen(QColor(150, 120, 90))
                        p.drawText(cell, Qt.AlignmentFlag.AlignCenter, str(r))
            p.setPen(QColor(120, 90, 60))
            p.drawText(QRectF(left, card.bottom() - 14, cw * 5, 12), Qt.AlignmentFlag.AlignCenter, "STMT NO")
            p.drawText(QRectF(left + 6 * cw, card.bottom() - 14, cw * 66, 12), Qt.AlignmentFlag.AlignCenter,
                       "FORTRAN STATEMENT")
            p.drawText(QRectF(left + 72 * cw, card.bottom() - 14, cw * 8, 12), Qt.AlignmentFlag.AlignCenter,
                       "IDENT")
            p.end()

    dlg = QDialog(parent)
    dlg.setWindowTitle("Card Deck")
    lay = QVBoxLayout(dlg)
    card = CardWidget()
    lay.addWidget(card, 1)
    info = QLabel()
    info.setProperty("i18n_skip", True)
    lay.addWidget(info)
    row = QHBoxLayout()
    spin = QSpinBox()
    spin.setRange(1, len(lines))
    prev_b, next_b = QPushButton("< Previous Card"), QPushButton("Next Card >")
    row.addWidget(QLabel("Card (line):"))
    row.addWidget(spin)
    row.addStretch(1)
    row.addWidget(prev_b)
    row.addWidget(next_b)
    lay.addLayout(row)

    def show(n: int):
        n = max(1, min(len(lines), n))
        card.line = lines[n - 1]
        f = fields(lines[n - 1])
        kind = "comment card" if f["comment"] else ("continuation card" if f["cont"] else "statement card")
        info.setText(f"Card {n} of {len(lines)} - {kind}" + (f", statement number {f['label']}" if f["label"]
                                                             else "") + (f", sequence {f['seq'].strip()}"
                                                                         if f["seq"].strip() else ""))
        if spin.value() != n:
            spin.setValue(n)
        card.update()

    spin.valueChanged.connect(show)
    prev_b.clicked.connect(lambda: show(spin.value() - 1))
    next_b.clicked.connect(lambda: show(spin.value() + 1))
    show(line + 1)
    dlg.resize(900, 460)
    return dlg


def conversion_dialog(parent, path: Path, text: str):
    """Preview of the free-form conversion (diff) with Save As .f90."""
    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QPlainTextEdit,
                                 QTabWidget, QVBoxLayout)
    dlg = QDialog(parent)
    dlg.setWindowTitle("Convert to Free Form (Fortran 90)")
    lay = QVBoxLayout(dlg)
    opts = QHBoxLayout()
    holl = QCheckBox("Hollerith to quoted strings")
    holl.setChecked(True)
    seq = QCheckBox("Keep sequence numbers as comments")
    opts.addWidget(holl)
    opts.addWidget(seq)
    opts.addStretch(1)
    lay.addLayout(opts)
    tabs = QTabWidget()
    mono = QFont("Consolas", 10)
    diff_view, new_view = QPlainTextEdit(), QPlainTextEdit()
    for v in (diff_view, new_view):
        v.setReadOnly(True)
        v.setFont(mono)
        v.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        v.setProperty("i18n_skip", True)
    tabs.addTab(diff_view, "Differences")
    tabs.addTab(new_view, "Free-form result")
    lay.addWidget(tabs, 1)
    state = {"new": ""}

    def refresh():
        state["new"] = to_free_form(text, holl.isChecked(), seq.isChecked())
        diff_view.setPlainText(diff(text, state["new"], Path(path).name, Path(path).with_suffix(".f90").name))
        new_view.setPlainText(state["new"])

    holl.toggled.connect(refresh)
    seq.toggled.connect(refresh)
    refresh()
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close)
    lay.addWidget(box)

    def save():
        target, _ = QFileDialog.getSaveFileName(dlg, "Save Free-Form Source", str(Path(path).with_suffix(".f90")),
                                                "Fortran 90 (*.f90);;All files (*)")
        if target:
            Path(target).write_text(state["new"], encoding="utf-8")
            dlg.accept()

    box.accepted.connect(save)
    box.rejected.connect(dlg.reject)
    dlg.resize(980, 640)
    return dlg


def looks_fixed_form(text: str) -> bool:
    """Comment cards in column 1 or statements starting in column 7, and no free-form-only syntax."""
    lines = [ln for ln in text.splitlines()[:400] if ln.strip()]
    if not lines:
        return False
    fixed = sum(1 for ln in lines if COMMENT_RX.match(ln) or re.match(r"^( {6}|\t)\S", ln) or
                re.match(r"^ {0,4}\d+ +\S", ln) or re.match(r"^ {5}\S", ln))
    free_only = sum(1 for ln in lines if re.match(r"^\S", ln) and not COMMENT_RX.match(ln)
                    and not re.match(r"^\d", ln))
    return fixed >= max(3, int(len(lines) * 0.7)) and free_only == 0


def detect_fixed_form(folder: Path, Candidate, walk) -> list:
    """File > Open Folder (radide/project_detect.py): fixed-form Fortran 66/77 sources -> fortran-legacy."""
    files = [f for f in walk(folder, 2, 1500) if f.lower().endswith(FIXED_EXT) and "/" not in f]
    if not files:
        return []
    fixed, main = [], ""
    for f in sorted(files)[:200]:
        try:
            text = (Path(folder) / f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if looks_fixed_form(text):
            fixed.append(f)
            if not main and re.search(r"^\s{6,}PROGRAM\s+\w+", text, re.I | re.M):
                main = f
    if not fixed:
        return []
    main = main or fixed[0]
    c = Candidate("fortran-fixed", f"Fortran 66/77 program (fixed form, {len(fixed)} file"
                                   f"{'s' if len(fixed) != 1 else ''}, {main})", "fortran-legacy", "app", folder, 0.8,
                  fixed[:3], startup=Path(main).stem, modules=fixed)
    c.extra["fortran"] = {"preset": "legacy", "flags": ""}
    c.notes.append("Built with gfortran -std=legacy -ffixed-form (Tools > Retro > Legacy Fortran > Compiler Preset).")
    return [c]


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "run":
        return run(Path(argv[1]))
    if len(argv) >= 2 and argv[0] == "convert":
        sys.stdout.write(to_free_form(Path(argv[1]).read_text(encoding="utf-8", errors="replace")))
        return 0
    if len(argv) >= 2 and argv[0] == "analyze":
        for line, kind, en, _ar in analyze(Path(argv[1]).read_text(encoding="utf-8", errors="replace")):
            print(f"{argv[1]}:{line + 1}: {kind}: {en}")
        return 0
    if len(argv) >= 3 and argv[0] == "card":
        print(card_text(Path(argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()[int(argv[2]) - 1]))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
