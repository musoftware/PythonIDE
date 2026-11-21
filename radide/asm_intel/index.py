"""Assembly source index: dialect detection and a parser for labels, procedures, macros, constants, data,
structures, sections, externs and includes (NASM, MASM, FASM, GAS). No Qt here.

The project index (``project_modules``) parses every assembly file of the project folder (cached by mtime,
like radide/languages/ring_intel.py does for Ring) plus the files they include, so completions, Go to
Definition and Find References see the whole program.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ASM_EXTS = (".asm", ".nasm", ".s", ".inc", ".fasm", ".mac", ".masm", ".asminc", ".ash", ".a")
SOURCE_EXTS = (".asm", ".nasm", ".s", ".fasm", ".masm")
MAX_FILES = 400
SKIP_DIRS = {"node_modules", "bin", "obj", "target", "build", "dist", "__pycache__", "venv", "_build", ".git"}
DIALECTS = ("nasm", "masm", "fasm", "gas")


# ============================================================================ dialect / mode detection
def is_asm_path(path) -> bool:
    if not path:
        return False
    p = Path(str(path))
    return p.suffix.lower() in ASM_EXTS or p.suffix == ".S"


def _plugin_dialect(plugin) -> str:
    if plugin is None:
        return ""
    d = str(getattr(plugin, "asm_dialect", "") or "").lower()
    if d in DIALECTS:
        return d
    pid = str(getattr(plugin, "id", "") or "").lower()
    for name, key in (("nasm", "nasm"), ("masm", "masm"), ("fasm", "fasm"), ("gas", "gas"), ("gnu-as", "gas"),
                      ("uasm", "masm"), ("jwasm", "masm"), ("yasm", "nasm")):
        if name in pid:
            return key
    return ""


def _project_dialect(path) -> str:
    """'nasm' ... from the project.radproj next to the file ("asm_dialect" / "assembler" / "language")."""
    if not path:
        return ""
    p = Path(str(path))
    for d in [p.parent, *p.parent.parents][:4]:
        f = d / "project.radproj"
        if f.is_file():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return ""
            asm = data.get("asm") if isinstance(data.get("asm"), dict) else {}
            for v in (asm.get("assembler"), data.get("asm_dialect"), data.get("assembler"), data.get("language")):
                v = str(v or "").lower()
                for name, dia in (("nasm", "nasm"), ("masm", "masm"), ("ml64", "masm"), ("fasm", "fasm"),
                                  ("gas", "gas"), ("gnu", "gas"), ("yasm", "nasm"), ("uasm", "masm")):
                    if name in v:
                        return dia
            return ""
    return ""


def sniff(text: str) -> str:
    """Guess the dialect from the source text ('' = no clue)."""
    head = text[:20000]
    low = head.lower()
    score = {"nasm": 0, "masm": 0, "fasm": 0, "gas": 0}
    pats = {
        "nasm": [r"^\s*section\s+\.\w+", r"^\s*%(define|macro|include|assign|ifdef)\b", r"^\s*bits\s+(16|32|64)",
                 r"^\s*default\s+rel", r"^\s*global\s+\w", r"\bres[bwdq]\s+\d", r"^\s*extern\s+\w+\s*$",
                 r"\[\s*rel\s+"],
        "masm": [r"^\s*\.model\b", r"^\s*\.code\b", r"^\s*\.data\??\s*$", r"^\s*\w+\s+proc\b", r"^\s*\w+\s+endp\b",
                 r"\binvoke\b", r"^\s*option\s+casemap", r"^\s*includelib\b", r"\b(dword|byte|qword)\s+ptr\b",
                 r"^\s*\.(386|486|586|686)", r"\boffset\s+\w", r"^\s*end\s*(\w+)?\s*$", r"\bproto\b"],
        "fasm": [r"^\s*format\s+(pe|pe64|elf|elf64|mz|binary)\b", r"^\s*section\s+'", r"^\s*include\s+'",
                 r"^\s*entry\s+\w", r"^\s*library\s+\w", r"^\s*import\s+\w+\s*,", r"\b(rb|rd|rw|rq)\s+\d",
                 r"^\s*macro\s+\w+.*\{", r"^\s*proc\s+\w", r"^\s*use(16|32|64)\b"],
        "gas": [r"^\s*\.(text|globl|global|section|intel_syntax|att_syntax|asciz|quad|long|type|p2align)\b",
                r"%(rax|eax|rsp|esp|rbp|rdi|rsi|al)\b", r"\$\d+\s*,\s*%", r"^\s*#\s*include\b"],
    }
    for dia, plist in pats.items():
        for p in plist:
            if re.search(p, low, re.M):
                score[dia] += 1
    # FASM "proc"/"endp" also exist in MASM: "name proc" (MASM) vs "proc name" (FASM)
    best = max(score.items(), key=lambda kv: kv[1])
    return best[0] if best[1] > 0 else ""


def detect_dialect(path=None, text: str | None = None, plugin=None) -> str:
    """nasm | masm | fasm | gas for a file: a dialect-specific extension (.nasm .fasm .masm .s), the project
    setting, then - inside a project - the plugin's dialect before the text; for a loose file (opened without a
    project: the plugin is just the first one with that extension) the text before the plugin."""
    hint = _plugin_dialect(plugin)
    p = Path(str(path)) if path else None
    in_project = False
    if p is not None:
        for d in [p.parent, *p.parent.parents][:4]:
            if (d / "project.radproj").is_file():
                in_project = True
                break
    low = p.suffix.lower() if p else ""
    if low == ".nasm":
        return "nasm"
    if low == ".fasm":
        return "fasm"
    if low == ".masm":
        return "masm"
    if low == ".s":                       # .s and .S (C-preprocessed) are GNU as
        return "gas"
    d = _project_dialect(path) if in_project else ""
    if d:
        return d
    if hint and in_project:
        return hint
    if hint and p is None:          # no path (document_symbols of a shared plugin): a clear text wins
        return sniff(text or "") or hint
    if text is None and p is not None and p.is_file():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
    return sniff(text or "") or hint or "nasm"


def gas_syntax(text: str) -> str:
    """'intel' when the file switches to .intel_syntax (and does not switch back), else 'att'."""
    last = "att"
    for m in re.finditer(r"(?im)^\s*\.(intel_syntax|att_syntax)\b", text):
        last = "intel" if m.group(1).lower() == "intel_syntax" else "att"
    return last


def code_bits(text: str, dialect: str) -> int:
    low = text[:40000].lower()
    m = re.search(r"(?m)^\s*(?:bits|use)\s*(16|32|64)\b", low) or re.search(r"(?m)^\s*\.code(16|32|64)\b", low)
    if m:
        return int(m.group(1))
    if re.search(r"(?m)^\s*format\s+(pe64|elf64)", low):
        return 64
    if re.search(r"(?m)^\s*format\s+(pe|elf|ms coff)\b", low):
        return 32
    if re.search(r"(?m)^\s*format\s+(mz|binary)\b", low) or re.search(r"(?m)^\s*org\s+100h", low):
        return 16
    if re.search(r"(?m)^\s*\.model\s+(tiny|small|compact|medium|large|huge)\b", low):
        return 16
    if re.search(r"(?m)^\s*\.(386|486|586|686)", low) or re.search(r"(?m)^\s*\.model\s+flat", low):
        return 32
    if re.search(r"(?<![\w%])%?(rax|rbx|rcx|rdx|rsi|rdi|rsp|rbp|r8|r9|r1[0-5])\b", low):
        return 64
    if re.search(r"(?<![\w%])%?(eax|ebx|ecx|edx|esi|edi|esp|ebp)\b", low):
        return 32
    if re.search(r"\bint\s+(21h|0x21|10h|0x10)\b", low):
        return 16
    return 64


def target_os(text: str, dialect: str, path=None) -> str:
    """windows | linux | dos (decides the calling convention shown in hovers)."""
    low = text[:40000].lower()
    if re.search(r"(?m)^\s*format\s+elf", low) or re.search(r"\bint\s+(0x80|80h)\b", low) or \
            (re.search(r"\bsyscall\b", low) and "_start" in low) or "@function" in low or ".note.gnu" in low:
        return "linux"
    if re.search(r"\bint\s+(21h|0x21|10h|0x10|16h)\b", low) or re.search(r"(?m)^\s*format\s+mz", low) or \
            re.search(r"(?m)^\s*org\s+(100h|0x100)", low):
        return "dos"
    if dialect == "gas" and os.name != "nt" and not re.search(r"\b(messagebox|exitprocess|getstdhandle)\w*", low):
        return "linux"
    return "windows"


def project_asm_settings(path) -> dict:
    """The "asm" settings of the project.radproj next to *path* ({} when none): assembler, arch, linker ..."""
    if not path:
        return {}
    p = Path(str(path))
    for d in [p.parent, *p.parent.parents][:4]:
        f = d / "project.radproj"
        if f.is_file():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return {}
            return data.get("asm") if isinstance(data.get("asm"), dict) else {}
    return {}


def abi_of(text: str, dialect: str, path=None) -> str:
    """win64 | sysv | x86 | dos16 (the project's "arch" setting first, then the text)."""
    arch = str(project_asm_settings(path).get("arch", "") or "").lower()
    if arch in ("x86", "x64"):
        if target_os(text, dialect, path) == "linux":
            return "x86" if arch == "x86" else "sysv"
        return "x86" if arch == "x86" else "win64"
    bits = code_bits(text, dialect)
    osn = target_os(text, dialect, path)
    if bits == 16 or osn == "dos":
        return "dos16"
    if bits == 32:
        return "x86"
    return "sysv" if osn == "linux" else "win64"


# ============================================================================ masking
def comment_prefixes(dialect: str) -> tuple[str, ...]:
    return ("#", "//") if dialect == "gas" else (";",)


def mask_line(line: str, dialect: str, in_block: bool = False, keep_strings: bool = False) -> tuple[str, bool]:
    """The line with comments (and strings unless keep_strings) replaced by spaces; returns (text, in_block)
    where in_block tracks GAS /* ... */ comments across lines."""
    out = []
    i, n = 0, len(line)
    q = ""
    stripped = line.lstrip()
    if dialect == "gas" and stripped.startswith("#") and re.match(r"#\s*(include|define|undef|if|ifdef|ifndef|"
                                                                  r"else|elif|endif|pragma)\b", stripped):
        return line, in_block                 # C preprocessor line of a .S file
    while i < n:
        ch = line[i]
        if in_block:
            if line.startswith("*/", i):
                in_block = False
                out.append("  ")
                i += 2
                continue
            out.append(" ")
            i += 1
            continue
        if q:
            if ch == "\\" and dialect in ("gas", "nasm") and q in ('"', "`") and i + 1 < n:
                out.append(line[i:i + 2] if keep_strings else "  ")
                i += 2
                continue
            if ch == q:
                q = ""
                out.append(ch)
            else:
                out.append(ch if keep_strings else " ")
            i += 1
            continue
        if ch == "'" and dialect == "gas":            # GAS character constant: 'A (no closing quote)
            out.append(line[i:i + 2] if keep_strings else "  "[:len(line[i:i + 2])])
            i += 2
            continue
        if ch in "\"'" or (ch == "`" and dialect == "nasm"):
            q = ch
            out.append(ch)
            i += 1
            continue
        if dialect == "gas" and line.startswith("/*", i):
            in_block = True
            out.append("  ")
            i += 2
            continue
        if any(line.startswith(c, i) for c in comment_prefixes(dialect)):
            out.append(" " * (n - i))
            break
        out.append(ch)
        i += 1
    return "".join(out), in_block


def mask(text: str, dialect: str, keep_strings: bool = False) -> list[str]:
    out = []
    blk = False
    for ln in text.split("\n"):
        m, blk = mask_line(ln, dialect, blk, keep_strings)
        out.append(m)
    return out


def comment_of(line: str, dialect: str) -> str:
    """Trailing comment text of a line ('' if none)."""
    m, _ = mask_line(line, dialect, False, True)
    rest = line[len(m.rstrip()):].strip()
    for c in comment_prefixes(dialect):
        if rest.startswith(c):
            return rest[len(c):].strip()
    return ""


# ============================================================================ symbols
@dataclass
class Sym:
    name: str
    kind: str          # label local proc macro const data struct field section extern global include var param
    line: int
    col: int = 0
    file: str = ""
    detail: str = ""
    parent: str = ""   # global label of a local label / proc of a local variable / struct of a field
    end_line: int = -1
    doc: str = ""
    params: list[str] = field(default_factory=list)

    @property
    def full(self) -> str:
        """The name other code uses: main.loop for NASM / FASM local labels, POINT.x for NASM struc fields."""
        if self.kind in ("local", "field") and self.parent and self.name.startswith(".") and \
                not self.name.startswith(".L"):
            return self.parent + self.name
        return self.name


@dataclass
class Module:
    dialect: str
    symbols: list[Sym] = field(default_factory=list)
    includes: list[tuple[str, int]] = field(default_factory=list)
    externs: dict[str, int] = field(default_factory=dict)
    globals: dict[str, int] = field(default_factory=dict)
    sections: list[Sym] = field(default_factory=list)
    entry: str = ""

    def defs(self, name: str, case: bool = True) -> list[Sym]:
        key = name if case else name.lower()
        return [s for s in self.symbols if (s.name if case else s.name.lower()) == key or
                (s.kind == "local" and (s.full if case else s.full.lower()) == key)]


ID = r"[A-Za-z_.?$@][\w.?$@#~]*"
DATA_NASM = r"(?:db|dw|dd|dq|dt|do|dy|dz|res[bwdqtoyz]|times|istruc)"
DATA_MASM = r"(?:db|dw|dd|dq|dt|df|byte|sbyte|word|sword|dword|sdword|fword|qword|sqword|tbyte|oword|real4|real8|" \
            r"real10|xmmword|ymmword)"
DATA_FASM = r"(?:db|dw|du|dd|dp|df|dq|dt|rb|rw|rd|rp|rf|rq|rt|file)"
MASM_KEYWORDS = {"proc", "endp", "macro", "endm", "equ", "struct", "struc", "union", "ends", "segment", "proto",
                 "textequ", "label", "record", "typedef"}
NOT_LABELS = {"section", "segment", "global", "extern", "bits", "default", "times", "align", "struc", "endstruc",
              "include", "format", "entry", "use16", "use32", "use64", "org", "if", "else", "end", "macro", "proc",
              "endp", "repeat", "while", "rept", "irp", "virtual", "library", "import", "invoke", "local", "locals",
              "endl", "public", "extrn", "includelib", "option", "assume", "cpu", "common", "static"}


def _doc_above(lines: list[str], i: int, dialect: str) -> str:
    out = []
    j = i - 1
    prefixes = comment_prefixes(dialect)
    while j >= 0 and len(out) < 6:
        s = lines[j].strip()
        hit = next((p for p in prefixes if s.startswith(p)), None)
        if hit is None:
            break
        t = s[len(hit):].strip().strip(";#/-=* ")
        if t:
            out.insert(0, t)
        j -= 1
    return " ".join(out)


def _logical_lines(lines: list[str], masked: list[str]) -> list[tuple[int, str, str]]:
    """(start line, masked text, comment-free text with strings) joined over FASM/MASM '\\' continuations."""
    out = []
    i = 0
    while i < len(masked):
        start = i
        m = masked[i]
        while m.rstrip().endswith("\\") and i + 1 < len(masked):
            i += 1
            m = m.rstrip()[:-1] + " " + masked[i]
        out.append((start, m, ""))
        i += 1
    return out


def parse(text: str, dialect: str, file: str = "") -> Module:
    lines = text.split("\n")
    masked = mask(text, dialect)
    kept = mask(text, dialect, keep_strings=True)
    mod = Module(dialect)
    syms = mod.symbols
    last_global = ""
    cur_section: Sym | None = None
    open_blocks: list[Sym] = []           # proc / macro / struct waiting for their end
    last_label: Sym | None = None

    def add(name, kind, i, col=0, detail="", parent="", params=None):
        s = Sym(name, kind, i, col, file, detail.strip()[:120], parent, -1, _doc_above(lines, i, dialect) or
                comment_of(lines[i], dialect), params or [])
        syms.append(s)
        return s

    def close_label(i):
        nonlocal last_label
        if last_label is not None and last_label.end_line < 0:
            last_label.end_line = max(last_label.line, i - 1)
        last_label = None

    def section(name, i, detail=""):
        nonlocal cur_section
        close_label(i)
        if cur_section is not None:
            cur_section.end_line = max(cur_section.line, i - 1)
        cur_section = add(name, "section", i, 0, detail)
        mod.sections.append(cur_section)

    def close_block(kinds, i, name=""):
        for k in range(len(open_blocks) - 1, -1, -1):
            b = open_blocks[k]
            if b.kind in kinds and (not name or b.name.lower() == name.lower()):
                b.end_line = i
                del open_blocks[k:]
                return b
        return None

    for i, m, _ in _logical_lines(lines, masked):
        s = m.strip()
        if not s:
            continue
        orig = kept[i].strip()
        low = s.lower()
        col = len(m) - len(m.lstrip())
        if dialect == "nasm":
            mm = re.match(r"%i?macro\s+(" + ID + r")\s*([\d\-+*]*)", s, re.I)
            if mm:
                b = add(mm.group(1), "macro", i, col, f"%macro {mm.group(1)} {mm.group(2)}".strip(),
                        params=[f"%{k + 1}" for k in range(int(re.match(r"\d*", mm.group(2)).group() or 0))])
                open_blocks.append(b)
                continue
            if re.match(r"%endmacro\b", low):
                close_block(("macro",), i)
                continue
            mm = re.match(r"%[xi]{0,2}define\s+(" + ID + r")(\([^)]*\))?\s*(.*)", s, re.I)
            if mm:
                add(mm.group(1), "const", i, col, (mm.group(2) or "") + " " + mm.group(3),
                    params=[p.strip() for p in (mm.group(2) or "").strip("()").split(",") if p.strip()])
                continue
            mm = re.match(r"%[ix]?assign\s+(" + ID + r")\s+(.*)", s, re.I)
            if mm:
                add(mm.group(1), "const", i, col, "%assign " + mm.group(2))
                continue
            mm = re.match(r"%include\s+[\"'<](.+?)[\"'>]", orig, re.I)
            if mm:
                mod.includes.append((mm.group(1), i))
                continue
            mm = re.match(r"(section|segment)\s+([^\s]+)(.*)", s, re.I)
            if mm:
                section(mm.group(2), i, mm.group(3))
                continue
            mm = re.match(r"struc\s+(" + ID + ")", s, re.I)
            if mm:
                b = add(mm.group(1), "struct", i, col, "struc")
                open_blocks.append(b)
                continue
            if re.match(r"endstruc\b", low):
                close_block(("struct",), i)
                continue
            mm = re.match(r"(extern|global|common)\s+(.+)", s, re.I)
            if mm:
                for item in mm.group(2).split(","):
                    nm = item.strip().split(":")[0].split()[0] if item.strip() else ""
                    if nm:
                        (mod.externs if mm.group(1).lower() == "extern" else mod.globals)[nm] = i
                        if mm.group(1).lower() == "extern":
                            add(nm, "extern", i, col, "extern")
                continue
        elif dialect == "masm":
            mm = re.match(r"(" + ID + r")\s+proc\b(.*)", s, re.I)
            if mm:
                close_label(i)
                rest = mm.group(2)
                params = re.findall(r"(\w+)\s*:\s*\w+", rest)
                b = add(mm.group(1), "proc", i, col, "PROC" + rest, params=params)
                open_blocks.append(b)
                last_global = mm.group(1)
                for p in params:
                    add(p, "param", i, col, "parameter of " + mm.group(1), mm.group(1))
                continue
            mm = re.match(r"(" + ID + r")\s+endp\b", s, re.I)
            if mm:
                close_block(("proc",), i, mm.group(1))
                continue
            mm = re.match(r"(" + ID + r")\s+macro\b(.*)", s, re.I)
            if mm:
                params = [p.split(":")[0].strip() for p in mm.group(2).split(",") if p.strip()]
                b = add(mm.group(1), "macro", i, col, "MACRO" + mm.group(2), params=params)
                open_blocks.append(b)
                continue
            if re.match(r"endm\b", low):
                close_block(("macro",), i)
                continue
            mm = re.match(r"(" + ID + r")\s+(struct|struc|union)\b", s, re.I)
            if mm:
                b = add(mm.group(1), "struct", i, col, mm.group(2).upper())
                open_blocks.append(b)
                continue
            mm = re.match(r"(" + ID + r")\s+ends\b", s, re.I)
            if mm:
                if not close_block(("struct",), i, mm.group(1)):
                    close_block(("section",), i)
                continue
            mm = re.match(r"(" + ID + r")\s+proto\b(.*)", s, re.I)
            if mm:
                params = [p.strip() for p in mm.group(2).split(",") if p.strip()]
                add(mm.group(1), "extern", i, col, "PROTO" + mm.group(2), params=params)
                mod.externs[mm.group(1)] = i
                continue
            mm = re.match(r"(extern|extrn|externdef)\s+(.+)", s, re.I)
            if mm:
                for item in mm.group(2).split(","):
                    nm = item.strip().split(":")[0].strip()
                    if nm:
                        mod.externs[nm] = i
                        add(nm, "extern", i, col, item.strip())
                continue
            mm = re.match(r"public\s+(.+)", s, re.I)
            if mm:
                for item in mm.group(1).split(","):
                    if item.strip():
                        mod.globals[item.strip().split()[0]] = i
                continue
            mm = re.match(r"(include|includelib)\s+(\S+)", orig, re.I)
            if mm:
                if mm.group(1).lower() == "include":
                    mod.includes.append((mm.group(2).strip("<>\"'"), i))
                continue
            mm = re.match(r"(\.code|\.data\??|\.const|\.stack|\.fardata\??)\b(.*)", s, re.I)
            if mm:
                section(mm.group(1), i, mm.group(2))
                continue
            mm = re.match(r"(" + ID + r")\s+segment\b(.*)", s, re.I)
            if mm:
                section(mm.group(1), i, "SEGMENT" + mm.group(2))
                continue
            mm = re.match(r"local\s+(.+)", s, re.I)
            if mm and open_blocks:
                owner = open_blocks[-1]
                for item in mm.group(1).split(","):
                    nm = item.strip().split(":")[0].split("[")[0].strip()
                    if nm:
                        add(nm, "var" if owner.kind == "proc" else "local", i, col, item.strip(), owner.name)
                continue
        elif dialect == "fasm":
            mm = re.match(r"macro\s+(" + ID + r")\s*([^{]*)", s, re.I)
            if mm:
                params = [p.strip().strip("*[]&") for p in mm.group(2).split(",") if p.strip()]
                b = add(mm.group(1), "macro", i, col, "macro " + mm.group(2), params=params)
                if "}" not in s:
                    open_blocks.append(b)
                else:
                    b.end_line = i
                continue
            mm = re.match(r"(struc|struct)\s+(" + ID + r")\s*([^{]*)", s, re.I)
            if mm:
                b = add(mm.group(2), "struct", i, col, mm.group(1) + " " + mm.group(3))
                if "}" not in s:
                    open_blocks.append(b)
                continue
            if s.startswith("}") or re.match(r"ends\b", low):
                close_block(("macro", "struct"), i)
                continue
            mm = re.match(r"proc\s+(" + ID + r")\s*,?\s*(.*)", s, re.I)
            if mm:
                close_label(i)
                params = [p.strip().split(":")[0] for p in re.split(r"[,\s]+", mm.group(2))
                          if p.strip() and p.strip().lower() not in ("uses", "stdcall", "c", "ccall")]
                b = add(mm.group(1), "proc", i, col, "proc " + mm.group(2), params=params)
                open_blocks.append(b)
                last_global = mm.group(1)
                for p in params:
                    if re.match(ID + "$", p) and p.lower() not in ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp",
                                                                    "rbx", "rsi", "rdi", "r12", "r13", "r14", "r15"):
                        add(p, "param", i, col, "parameter of " + mm.group(1), mm.group(1))
                continue
            if re.match(r"endp\b", low):
                close_block(("proc",), i)
                continue
            mm = re.match(r"(?:define|equ)\s+(" + ID + r")\s+(.*)", s, re.I) or \
                re.match(r"(" + ID + r")\s+(?:equ|=)\s*(.*)", s, re.I)
            if mm:
                add(mm.group(1), "const", i, col, mm.group(2))
                continue
            mm = re.match(r"section\s+'([^']*)'(.*)", orig, re.I)
            if mm:
                section(mm.group(1), i, mm.group(2))
                continue
            mm = re.match(r"segment\s+(.*)", s, re.I)
            if mm:
                section("segment", i, mm.group(1))
                continue
            mm = re.match(r"include\s+['\"](.+?)['\"]", orig, re.I)
            if mm:
                mod.includes.append((mm.group(1), i))
                continue
            mm = re.match(r"entry\s+(" + ID + ")", s, re.I)
            if mm:
                mod.entry = mm.group(1)
                continue
            mm = re.match(r"import\s+(" + ID + r")\s*,(.*)", orig, re.I)
            if mm:
                for nm in re.findall(r"(" + ID + r")\s*,\s*['\"]", mm.group(2)):
                    mod.externs[nm] = i
                    add(nm, "extern", i, col, f"import from {mm.group(1)}")
                continue
            if re.match(r"library\b", low):
                continue
            mm = re.match(r"locals\b", low)
            if mm:
                continue
            mm = re.match(r"local\s+(.+)", s, re.I)
            if mm and open_blocks:
                for item in mm.group(1).split(","):
                    nm = item.strip().split(":")[0].split()[0] if item.strip() else ""
                    if nm and re.match(ID + "$", nm):
                        add(nm, "var", i, col, item.strip(), open_blocks[-1].name)
                continue
            mm = re.match(r"label\s+(" + ID + r")(.*)", s, re.I)
            if mm:
                add(mm.group(1), "data", i, col, "label" + mm.group(2))
                continue
        elif dialect == "gas":
            mm = re.match(r"\.macro\s+(" + ID + r")[\s,]*(.*)", s, re.I)
            if mm:
                params = [p.strip().split("=")[0].split(":")[0] for p in re.split(r"[,\s]+", mm.group(2)) if p.strip()]
                b = add(mm.group(1), "macro", i, col, ".macro " + mm.group(2), params=params)
                open_blocks.append(b)
                continue
            if re.match(r"\.endm\b", low):
                close_block(("macro",), i)
                continue
            mm = re.match(r"\.(equ|set|equiv)\s+(" + ID + r")\s*,\s*(.*)", s, re.I)
            if mm:
                add(mm.group(2), "const", i, col, mm.group(3))
                continue
            mm = re.match(r"#\s*define\s+(" + ID + r")(\([^)]*\))?\s*(.*)", s)
            if mm:
                add(mm.group(1), "const", i, col, (mm.group(2) or "") + " " + mm.group(3))
                continue
            mm = re.match(r"(?:\.include\s+\"|#\s*include\s+[\"<])(.+?)[\">]", orig, re.I)
            if mm:
                mod.includes.append((mm.group(1), i))
                continue
            mm = re.match(r"\.(globl|global|extern)\s+(.+)", s, re.I)
            if mm:
                for item in mm.group(2).split(","):
                    nm = item.strip()
                    if nm:
                        (mod.externs if mm.group(1).lower() == "extern" else mod.globals)[nm] = i
                continue
            mm = re.match(r"\.(text|data|bss|rodata)\b(.*)", s, re.I)
            if mm:
                section("." + mm.group(1).lower(), i, mm.group(2))
                continue
            mm = re.match(r"\.section\s+([^\s,]+)(.*)", s, re.I)
            if mm:
                section(mm.group(1), i, mm.group(2))
                continue
            mm = re.match(r"\.type\s+(" + ID + r")\s*,\s*[@%]function", s, re.I)
            if mm:
                for sy in syms:
                    if sy.name == mm.group(1) and sy.kind == "label":
                        sy.kind = "proc"
                mod.globals.setdefault(mm.group(1), mod.globals.get(mm.group(1), -1))
                continue
            mm = re.match(r"(" + ID + r")\s*=\s*(.*)", s)
            if mm and not s.startswith("."):
                add(mm.group(1), "const", i, col, mm.group(2))
                continue

        # ------------------------------------------------ constants / data / labels shared by the dialects
        if dialect in ("nasm", "masm"):
            mm = re.match(r"(" + ID + r")\s*:?\s+(equ|=|textequ)\s*(.*)", s, re.I)
            if mm and mm.group(1).lower() not in NOT_LABELS:
                add(mm.group(1), "const", i, col, f"{mm.group(2)} {mm.group(3)}")
                continue
        # labels: name:   (MASM also name::)
        mm = re.match(r"(" + ID + r")\s*::?(?!=)", s)
        if mm and not re.match(r"\d", mm.group(1)) and mm.group(1).lower() not in NOT_LABELS and \
                mm.group(1) not in ("@@",) and not (dialect == "gas" and re.match(r"\d+$", mm.group(1))):
            name = mm.group(1)
            rest = s[mm.end():].strip()
            data_re = {"nasm": DATA_NASM, "masm": DATA_MASM, "fasm": DATA_FASM}.get(dialect, r"\.(?:byte|short|word|"
                                                                                   r"long|int|quad|ascii|asciz|string|"
                                                                                   r"space|skip|zero|fill|float|double)")
            if rest and re.match(data_re + r"\b", rest, re.I):
                add(name, "data", i, col, orig[mm.end():].strip() or rest)
                continue
            if name.startswith(".") and dialect in ("nasm", "fasm") and not name.startswith(".."):
                add(name, "local", i, col, "local label", last_global)
                continue
            if dialect == "gas" and name.startswith((".L", "L.")):
                add(name, "local", i, col, "local label", last_global)
                continue
            if dialect == "masm" and open_blocks and open_blocks[-1].kind == "proc":
                add(name, "local", i, col, "label in " + open_blocks[-1].name, open_blocks[-1].name)
                continue
            close_label(i)
            kind = "proc" if name in mod.globals and mod.globals.get(name, -1) >= 0 and dialect == "gas" else "label"
            if cur_section is not None and kind == "label" and \
                    re.search(r"data|bss|rodata|rdata|const|idata", cur_section.name + cur_section.detail, re.I) and \
                    not re.search(r"\bcode\b|executable", cur_section.detail, re.I):
                kind = "data"
            last_label = add(name, kind, i, col, "label")
            last_global = name
            continue
        # data without a colon: msg db "Hi", 0  /  value dd ?  /  buffer rb 256 / pt POINT <>
        data_re = {"nasm": DATA_NASM, "masm": DATA_MASM, "fasm": DATA_FASM}.get(dialect)
        if data_re:
            mm = re.match(r"(" + ID + r")\s+(" + data_re + r")\b(.*)", s, re.I)
            if mm and mm.group(1).lower() not in NOT_LABELS and mm.group(1).lower() not in MASM_KEYWORDS:
                parent = open_blocks[-1].name if open_blocks and open_blocks[-1].kind == "struct" else ""
                nm = mm.group(1)
                if nm.startswith(".") and not parent:
                    parent = last_global
                add(nm, "field" if parent and open_blocks and open_blocks[-1].kind == "struct" else "data", i, col,
                    orig[mm.start(2):] if len(orig) >= mm.end(1) else mm.group(2) + mm.group(3), parent)
                continue
            if dialect == "masm":
                mm = re.match(r"(" + ID + r")\s+(" + ID + r")\s*(<.*>|\{.*\})", s)
                if mm and mm.group(1).lower() not in NOT_LABELS:
                    add(mm.group(1), "data", i, col, mm.group(2) + " " + mm.group(3))
                    continue
        if dialect == "gas" and open_blocks and open_blocks[-1].kind == "struct":
            continue
    close_label(len(lines))
    if cur_section is not None and cur_section.end_line < 0:
        cur_section.end_line = len(lines) - 1
    for b in open_blocks:
        if b.end_line < 0:
            b.end_line = len(lines) - 1
    for s in syms:
        if s.kind == "label" and s.name in mod.globals and dialect != "gas":
            s.kind = "proc"
        if s.end_line < 0 and s.kind in ("proc", "label"):
            s.end_line = s.line
    return mod


# ============================================================================ project files / cache
_CACHE: dict[str, tuple[float, str, Module]] = {}


def parse_file(p: Path, dialect: str | None = None) -> tuple[Module, str] | None:
    key = str(p).lower()
    try:
        mt = p.stat().st_mtime
    except OSError:
        return None
    hit = _CACHE.get(key)
    if hit and hit[0] == mt and (dialect is None or hit[2].dialect == dialect):
        return hit[2], hit[1]
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    dia = dialect or detect_dialect(p, text)
    mod = parse(text, dia, str(p))
    _CACHE[key] = (mt, text, mod)
    if len(_CACHE) > 3000:
        _CACHE.clear()
    return mod, text


def project_root(path) -> Path | None:
    if not path:
        return None
    p = Path(str(path))
    folder = p.parent if p.suffix else p
    for d in [folder, *folder.parents][:4]:
        if (d / "project.radproj").is_file() or (d / "project.radsln").is_file():
            return d
    return folder


def project_files(path) -> list[Path]:
    root = project_root(path)
    if root is None or not root.is_dir():
        return []
    out: list[Path] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_")) and d.lower() not in SKIP_DIRS]
        for fn in files:
            if is_asm_path(fn) and not fn.startswith("_rad"):
                out.append(Path(dirpath) / fn)
                if len(out) >= MAX_FILES:
                    return out
        if Path(dirpath) != root and len(Path(dirpath).relative_to(root).parts) >= 3:
            dirs[:] = []
    return out


def include_dirs(path) -> list[Path]:
    """Folders searched for include files: the file's folder, the project root, its include/ folder, the
    INCLUDE environment variable (FASM / MASM) and the IDE's assembler tools folders."""
    out: list[Path] = []
    if path:
        p = Path(str(path))
        out.append(p.parent)
        root = project_root(path)
        if root is not None:
            out += [root, root / "include", root / "inc"]
    for d in (os.environ.get("INCLUDE", "") or "").split(os.pathsep):
        if d.strip():
            out.append(Path(d.strip()))
    tools = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "RADIDE" / "tools"
    for sub in ("fasm/INCLUDE", "fasm/include", "fasmg/include", "nasm/include", "masm32/include"):
        out.append(tools / sub)
    return out


def resolve_include(name: str, from_path) -> Path | None:
    n = name.strip().strip("<>\"'").replace("\\", "/")
    if not n:
        return None
    if n.startswith("%") and "%" in n[1:]:             # FASM: include '%fasminc%\win32a.inc'
        var = n[1:n.index("%", 1)]
        n = (os.environ.get(var, "") + n[n.index("%", 1) + 1:]).replace("\\", "/")
    cand = Path(n)
    if cand.is_absolute():
        return cand if cand.is_file() else None
    for d in include_dirs(from_path):
        try:
            f = d / n
            if f.is_file():
                return f.resolve()
        except OSError:
            continue
    return None
