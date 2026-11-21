"""Assembly folders and assembly-IDE projects opened IN PLACE.

File > Open Folder on a folder with ``.asm`` / ``.s`` / ``.nasm`` sources (radide/project_detect.py ``_asm``)
or File > Open on a project file of another assembly IDE:

* loose sources (SASM programs are plain ``.asm`` files too) - every source with an entry point
  (``main`` / ``start`` / ``_start`` / ``WinMain`` / ``..start`` / MASM ``END label``) is a run target;
* RadASM projects (``.rap``, INI: ``[Project] Assembler=``, ``[Files]``) and WinAsm Studio projects
  (``.wap``, INI: ``[PROJECT]``, ``[FILES]``) - their file list and main file; their own make commands are
  shown in the log (they use the other IDE's variables, so the build below is used instead).

The dialect of each program is guessed from its text (``guess_dialect``):

=========  ==========================================================  =======================================
dialect    typical lines                                               build (output in the IDE state folder)
=========  ==========================================================  =======================================
nasm       ``section .text``, ``global main``, ``extern``, ``bits 64``  ``nasm -f win64`` + ``gcc`` (MinGW)
masm       ``.model``, ``.code``, ``main PROC``, ``END main``          ``ml64`` / ``ml`` (Visual Studio only)
fasm       ``format PE64 console``, ``section '.text' code``           ``fasm src out.exe``
gas        ``.globl main``, ``.text``, ``%rax`` (AT&T)                 ``gcc src.s``
8086       ``org 100h``, ``int 21h``, ``mov ah, 9`` (16-bit DOS)       the 8086 teaching emulator
=========  ==========================================================  =======================================

Tools: the Assembly language plugin's own finders when it is installed (docs/ASSEMBLY.md), else PATH, the
IDE tools folder (``%LOCALAPPDATA%\\RADIDE\\tools\\<tool>``) and the MinGW toolchain; ``ml64`` only from a
Visual Studio installation (vcvars64.bat). Nothing is written into the user's folder.
"""
from __future__ import annotations

import configparser
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ._others_base import ForeignAdapter, ForeignProject, LazyStep, RunTarget, Step, show_projects, source_files

ASM_EXT = (".asm", ".s", ".nasm", ".fasm", ".masm")
INC_EXT = (".inc", ".mac", ".ash")
PROJECT_EXT = (".rap", ".wap")
EXE = ".exe" if os.name == "nt" else ""
DIALECT_TITLES = {"nasm": "NASM", "masm": "MASM", "fasm": "FASM", "gas": "GNU as", "8086": "8086 / DOS (emulator)"}

_RX = {
    "fasm": [(r"^\s*format\s+(PE|PE64|ELF|ELF64|MZ|binary|MS\s+COFF|MS64\s+COFF)\b", 6),
             (r"^\s*section\s+'[^']*'\s+(code|data|import|readable|executable)", 4),
             (r"^\s*include\s+'[^']*\.inc'", 2), (r"^\s*entry\s+\w+", 2), (r"^\s*library\s+\w+\s*,", 2)],
    "masm": [(r"^\s*\.model\b", 4), (r"^\s*\.code\b", 3), (r"^\s*\.data\??\b", 2), (r"^\s*\w+\s+proc\b", 3),
             (r"^\s*\w+\s+endp\b", 3), (r"^\s*end(\s+\w+)?\s*$", 1), (r"^\s*includelib\b", 3),
             (r"^\s*option\s+casemap", 3), (r"^\s*invoke\s+\w+", 2), (r"^\s*\.(386|486|586|686)p?\b", 3),
             (r"\b(dword|qword|byte|word)\s+ptr\b", 1)],
    "gas": [(r"^\s*\.globl\b", 4), (r"^\s*\.(text|data|bss)\s*$", 1), (r"%[re]?[abcd]x\b|%r\d+\b|%[re]?[sb]p\b", 3),
            (r"^\s*\.section\s+\.\w+", 2), (r"^\s*\.intel_syntax\b", 3), (r"^\s*\.(ascii|asciz|string|quad|long)\b", 2),
            (r"^\s*\.(def|scl|type|endef|seh_\w+)\b", 2)],
    "nasm": [(r"^\s*section\s+\.\w+", 4), (r"^\s*segment\s+\.\w+", 3), (r"^\s*global\s+\w+", 3),
             (r"^\s*extern\s+\w+", 2), (r"^\s*\[?bits\s+(16|32|64)\]?", 3), (r"^\s*%(include|define|macro|assign)\b", 2),
             (r"\bres[bwdq]\b", 2), (r"^\s*default\s+rel\b", 3), (r"\b(byte|word|dword|qword)\s+\[", 1)],
}
_DOS_RX = re.compile(r"\bint\s+(21h|0x21|10h|0x10|16h|0x16|20h|0x20)\b|^\s*org\s+(100h|0x100|256)\b|"
                     r"^\s*\.model\s+(tiny|small)\b|^\s*#make_(com|exe|bin)#|^\s*\[?bits\s+16\]?|^\s*\.8086\b",
                     re.I | re.M)
_SASM_RX = re.compile(r'^\s*%include\s+["\']io(64)?\.inc["\']', re.I | re.M)


def _strip_comments(text: str) -> str:
    return re.sub(r"(?m)\s*;.*$", "", text)


def guess_dialect(text: str, filename: str = "") -> str:
    """'nasm' | 'masm' | 'fasm' | 'gas' | '8086' for an assembly source."""
    body = _strip_comments(text or "")
    if _DOS_RX.search(body) and not re.search(r"\b(rax|rbx|rcx|rdx|rsp|rbp|r8|r9)\b", body, re.I):
        return "8086"
    scores = {}
    for d, rules in _RX.items():
        scores[d] = sum(w for rx, w in rules if re.search(rx, body, re.I | re.M))
    if filename.lower().endswith(".s"):
        scores["gas"] += 2
    elif filename.lower().endswith(".nasm"):
        scores["nasm"] += 5
    elif filename.lower().endswith(".masm"):
        scores["masm"] += 5
    elif filename.lower().endswith(".fasm"):
        scores["fasm"] += 5
    best = max(scores, key=lambda d: (scores[d], d == "nasm"))
    return best if scores[best] > 0 else "nasm"


def guess_bits(text: str, dialect: str = "") -> int:
    body = _strip_comments(text or "")
    if dialect == "8086":
        return 16
    m = re.search(r"^\s*\[?bits\s+(16|32|64)\]?|^\s*use(16|32|64)\b", body, re.I | re.M)
    if m:
        return int(m.group(1) or m.group(2))
    if re.search(r"^\s*format\s+(PE64|ELF64|MS64)", body, re.I | re.M):
        return 64
    if re.search(r"^\s*format\s+(PE|ELF|MS\s+COFF)\b", body, re.I | re.M):
        return 32
    if re.search(r"^\s*\.(386|486|586|686)p?\b|^\s*\.model\s+flat", body, re.I | re.M):
        return 32
    if re.search(r"\b(rax|rbx|rcx|rdx|rsi|rdi|rsp|rbp|r8|r9|r1[0-5])\b|%r(ax|sp|bp|\d+)", body, re.I):
        return 64
    if re.search(r"\b(eax|ebx|ecx|edx|esi|edi|esp|ebp)\b", body, re.I):
        return 32
    return 64


def entry_point(text: str, dialect: str) -> str:
    """The program's entry label ('' = a module without one)."""
    body = _strip_comments(text or "")
    if dialect == "8086":
        return "start" if re.search(r"^\s*(org\s|start:|main:|\.code|#make_)", body, re.I | re.M) or \
            _DOS_RX.search(body) else ""
    if dialect == "masm":
        m = re.search(r"^\s*end\s+(\w+)\s*$", body, re.I | re.M)
        if m:
            return m.group(1)
        m = re.search(r"^\s*(main|start|WinMain|mainCRTStartup|WinMainCRTStartup)\s+proc\b", body, re.I | re.M)
        return m.group(1) if m else ""
    if dialect == "fasm":
        m = re.search(r"^\s*entry\s+(\w+)", body, re.I | re.M)
        return m.group(1) if m else ("start" if re.search(r"^\s*format\s+(PE|MZ)", body, re.I | re.M) else "")
    if _SASM_RX.search(body) and re.search(r"^\s*CMAIN\s*:", body, re.M):
        return "main"
    for name in ("main", "WinMain", "wWinMain", "_start", "start", "_main", "..start", "mainCRTStartup"):
        if re.search(rf"^\s*{re.escape(name)}\s*:", body, re.M) or \
                re.search(rf"^\s*(global|\.globl|public)\s+{re.escape(name)}\b", body, re.I | re.M):
            return name
    return ""


# ===================================================================== tools
def _plugin_tool(name: str) -> str:
    """The Assembly language plugin's finder for *name* (when that plugin is installed)."""
    try:
        from ..languages import plugins_for_ext
        for p in plugins_for_ext(".asm"):
            for attr in ("find_tool", "tool_path", "find"):
                fn = getattr(p, attr, None)
                if callable(fn):
                    try:
                        hit = fn(name)
                    except TypeError:
                        continue
                    if hit:
                        return str(hit)
    except Exception:  # noqa: BLE001
        pass
    return ""


def _tools_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE" / "tools"


def find_tool(name: str) -> str:
    """nasm / fasm / gcc / as / ld / objdump / gdb: env RADIDE_<NAME>, the plugin, PATH, IDE folders."""
    env = os.environ.get("RADIDE_" + name.upper())
    if env and Path(env).is_file():
        return env
    hit = _plugin_tool(name)
    if hit:
        return hit
    hit = shutil.which(name)
    if hit:
        return hit
    exe = name + EXE
    root = _tools_root()
    for pat in (f"{name}/{exe}", f"{name}/*/{exe}", f"{name}/*/*/{exe}", f"{name}*/{exe}", f"{name}*/*/{exe}"):
        found = sorted(root.glob(pat))
        if found:
            return str(found[-1])
    try:
        from ..languages.c_bridge import find_native
        return find_native([name])
    except Exception:  # noqa: BLE001
        return ""


def find_masm(bits: int = 64) -> tuple[str, str]:
    """(ml64.exe / ml.exe, vcvars bat) of a Visual Studio installation, or ("", "") - never downloaded."""
    name = "ml64.exe" if bits == 64 else "ml.exe"
    w = shutil.which(name)
    try:
        from ..languages.c_bridge import find_vcvars
        bat = find_vcvars()
    except Exception:  # noqa: BLE001
        bat = ""
    if w:
        return w, bat
    if not bat:
        return "", ""
    vc = Path(bat).parents[2]                    # ...\VC\Auxiliary\Build\vcvars64.bat -> ...\VC
    host = "Hostx64/x64" if bits == 64 else "Hostx64/x86"
    found = sorted(vc.glob(f"Tools/MSVC/*/bin/{host}/{name}"))
    return (str(found[-1]), bat) if found else ("", "")


def sasm_include() -> str:
    """SASM's include folder (io64.inc / io.inc macros of SASM programs), when SASM is installed."""
    for base in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("ProgramFiles", r"C:\Program Files")):
        for sub in ("SASM/include", "SASM/NASM/include"):
            p = Path(base) / sub
            if (p / "io64.inc").is_file() or (p / "io.inc").is_file():
                return str(p)
    return ""


# ===================================================================== folder scan
@dataclass
class AsmProgram:
    file: str
    dialect: str
    bits: int
    entry: str
    sasm: bool = False


@dataclass
class AsmFolderInfo:
    sources: list = field(default_factory=list)       # every .asm / .s ... (relative)
    includes: list = field(default_factory=list)
    programs: list = field(default_factory=list)      # AsmProgram with an entry point
    dialects: dict = field(default_factory=dict)      # dialect -> number of sources

    @property
    def dialect(self) -> str:
        if not self.dialects:
            return "nasm"
        main = [p.dialect for p in self.programs] or list(self.dialects)
        return max(set(main), key=lambda d: (main.count(d), self.dialects.get(d, 0)))

    def title(self) -> str:
        d = self.dialect
        bits = {p.bits for p in self.programs if p.dialect == d}
        b = f" {max(bits)}-bit" if bits and d != "8086" else ""
        return f"{DIALECT_TITLES.get(d, d)}{b}"


def _read(p: Path, limit: int = 120_000) -> str:
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def scan_folder(folder: Path, files: list | None = None) -> AsmFolderInfo:
    folder = Path(folder)
    info = AsmFolderInfo()
    if files is None:
        files = source_files(folder, ASM_EXT + INC_EXT, limit=2000)
    for f in files:
        low = f.lower()
        if low.endswith(INC_EXT):
            info.includes.append(f)
            continue
        if not low.endswith(ASM_EXT):
            continue
        info.sources.append(f)
        text = _read(folder / f)
        d = guess_dialect(text, f)
        info.dialects[d] = info.dialects.get(d, 0) + 1
        e = entry_point(text, d)
        if e:
            info.programs.append(AsmProgram(f, d, guess_bits(text, d), e, bool(_SASM_RX.search(text))))
    info.programs.sort(key=lambda p: (p.file.count("/"), Path(p.file).stem.lower() not in ("main", "start", "app"),
                                      p.file.lower()))
    return info


# ===================================================================== other IDEs' project files
def _ini(path: Path) -> configparser.ConfigParser:
    cp = configparser.ConfigParser(strict=False, interpolation=None, delimiters=("=",))
    cp.optionxform = str
    try:
        cp.read_string(Path(path).read_text(encoding="latin-1", errors="replace"))
    except (OSError, configparser.Error):
        pass
    return cp


def _section(cp, name: str) -> dict:
    for s in cp.sections():
        if s.lower() == name.lower():
            return dict(cp[s])
    return {}


def read_ide_project(path: Path) -> dict:
    """{'files': [...], 'main': str, 'assembler': str, 'make': [...], 'title': str} of a .rap / .wap file."""
    path = Path(path)
    cp = _ini(path)
    out = {"files": [], "main": "", "assembler": "", "make": [], "title": ""}
    if path.suffix.lower() == ".rap":                    # RadASM
        proj = _section(cp, "Project")
        out["assembler"] = (proj.get("Assembler") or "masm").lower()
        out["title"] = proj.get("Description") or path.stem
        files = _section(cp, "Files")
        for k, v in sorted(files.items(), key=lambda kv: (len(kv[0]), kv[0])):
            if k.isdigit() and v.strip():
                out["files"].append(v.strip().replace("\\", "/"))
        out["make"] = [v for k, v in _section(cp, "MakeFiles").items() if v.strip()][:12] + \
            [v for k, v in _section(cp, "MakeDef").items() if v.strip()][:12]
    else:                                                # WinAsm Studio
        proj = _section(cp, "PROJECT")
        out["assembler"] = "masm"
        out["title"] = path.stem
        files = _section(cp, "FILES")
        for k, v in sorted(files.items(), key=lambda kv: (len(kv[0]), kv[0])):
            if k.isdigit() and v.strip():
                out["files"].append(v.strip().replace("\\", "/"))
        out["make"] = [v for k, v in _section(cp, "MAKE").items() if v.strip()][:12]
        if proj.get("Type", "").strip() in ("1", "2"):
            out["title"] += " (DLL / library)"
    src = [f for f in out["files"] if f.lower().endswith(ASM_EXT)]
    out["main"] = next((f for f in src if Path(f).stem.lower() == path.stem.lower()), src[0] if src else "")
    return out


# ===================================================================== adapter
class AsmFolderAdapter(ForeignAdapter):
    kind = "asm"
    title = "Assembly sources"
    base_language = "c-bridge"

    def __init__(self, native: Path):
        native = Path(native).resolve()
        super().__init__(native, native if native.is_dir() else native.parent)
        self.info_scan: AsmFolderInfo | None = None
        self.ide: dict = {}
        try:
            from ..languages import plugins_for_ext
            cands = plugins_for_ext(".asm")
            if cands:
                self.base_language = cands[0].id
        except Exception:  # noqa: BLE001
            pass

    def scan(self) -> None:
        files = None
        if self.native.is_file() and self.native.suffix.lower() in PROJECT_EXT:
            self.ide = read_ide_project(self.native)
            files = [f for f in self.ide["files"] if (self.root / f).is_file()]
            self.title = ("RadASM project" if self.native.suffix.lower() == ".rap" else "WinAsm Studio project")
            self.name = self.native.stem
        self.info_scan = info = scan_folder(self.root, files)
        if files is None:
            self.title = f"Assembly sources ({info.title()})"
        self.modules = info.sources + info.includes
        if self.ide and self.ide.get("main"):
            main = self.ide["main"]
            info.programs.sort(key=lambda p: p.file != main)
        for p in info.programs[:40]:
            label = f"{p.file}  [{DIALECT_TITLES.get(p.dialect, p.dialect)}" + \
                (f" {p.bits}-bit" if p.dialect != "8086" else "") + "]"
            self.targets.append(RunTarget(label, "emu" if p.dialect == "8086" else "exe",
                                          {"file": p.file, "dialect": p.dialect, "bits": p.bits, "entry": p.entry,
                                           "sasm": p.sasm}))
        self.info.append(f"{self.title}: {len(info.sources)} source(s), {len(info.programs)} program(s); "
                         f"dialects: " + ", ".join(f"{DIALECT_TITLES.get(d, d)} x{n}" for d, n in info.dialects.items()))
        if self.ide:
            self.info.append(f"{self.native.name}: assembler {self.ide['assembler'] or '?'}, main file "
                             f"{self.ide['main'] or '-'}; its own make commands (not run, they use the other IDE's "
                             f"variables): " + " | ".join(self.ide["make"][:4]))
        for d in sorted(info.dialects):
            for line in self._tool_notes(d, max((p.bits for p in info.programs if p.dialect == d), default=64)):
                self.info.append(line)
        self.info.append(f"Build output goes to the IDE state folder {self.state}")

    # -- tools
    def _tool_notes(self, dialect: str, bits: int) -> list:
        if dialect == "nasm":
            return [f"nasm: {find_tool('nasm') or 'not found (Tools > download NASM, or put nasm.exe on PATH)'}; "
                    f"linker gcc: {find_tool('gcc') or 'not found (MinGW-w64)'}"]
        if dialect == "fasm":
            return [f"fasm: {find_tool('fasm') or 'not found (flatassembler.net)'}"]
        if dialect == "gas":
            return [f"gcc (GNU as): {find_tool('gcc') or 'not found (MinGW-w64)'}"]
        if dialect == "masm":
            ml, _bat = find_masm(bits)
            return [f"MASM: {ml or 'ml64/ml not found - MASM needs Visual Studio (C++ workload); it is not downloaded'}"]
        return ["8086 programs run in the 8086 teaching emulator (registers, memory and int 21h console)"]

    def tool(self) -> str:
        return find_tool("nasm") or find_tool("gcc")

    def _exe(self, target) -> Path:
        out = self.state / "bin"
        out.mkdir(parents=True, exist_ok=True)
        return out / (re.sub(r"[^\w.-]+", "_", Path(target.data["file"]).with_suffix("").as_posix()) + EXE)

    def build_steps(self, target, debug):
        if target is None or target.kind != "exe":
            return []
        d, bits, entry = target.data["dialect"], int(target.data.get("bits") or 64), target.data.get("entry") or ""
        src = self.root / target.data["file"]
        exe = self._exe(target)
        obj = exe.with_suffix(".obj")
        gcc = find_tool("gcc") or "gcc"
        env = {"PATH": os.pathsep.join([str(Path(gcc).parent), os.environ.get("PATH", "")])} if gcc != "gcc" else {}
        link_entry = [] if entry in ("main", "WinMain", "wWinMain", "_main") else \
            ["-nostartfiles", f"-Wl,-e,{entry.lstrip('.') or 'start'}"]
        libs = ["-lkernel32", "-luser32", "-lgdi32", "-lmsvcrt"]
        if d == "nasm":
            nasm = find_tool("nasm") or "nasm"
            fmt = "win64" if bits == 64 else "win32"
            inc = [f"-I{src.parent}{os.sep}", f"-I{self.root}{os.sep}"]
            if target.data.get("sasm") and sasm_include():
                inc.append(f"-I{sasm_include()}{os.sep}")
            dbg = ["-g", "-F", "cv8"] if debug and fmt == "win64" else []
            steps = [Step([nasm, "-f", fmt, *dbg, *inc, "-o", str(obj), str(src)], self.root, {}, f"nasm -f {fmt}")]
            m = ["-m32"] if bits == 32 else []
            return steps + [Step([gcc, *m, "-g", *link_entry, "-o", str(exe), str(obj), *libs], self.root, env,
                                 "gcc (link)")]
        if d == "gas":
            return [Step([gcc, "-g", *link_entry, "-o", str(exe), str(src), *libs], self.root, env, "gcc (GNU as)")]
        if d == "fasm":
            fasm = find_tool("fasm") or "fasm"
            fenv = {}
            inc = Path(fasm).parent / "INCLUDE"
            if inc.is_dir():
                fenv["INCLUDE"] = str(inc)
            return [Step([fasm, str(src), str(exe)], self.root, fenv, "fasm")]
        if d == "masm":
            ml, bat = find_masm(bits)
            ent = entry or "main"
            sub = "windows" if ent.lower().startswith("winmain") else "console"
            cmd = (f'"{ml or "ml64"}" /nologo /Zi /Fo"{obj}" "{src}" /link /subsystem:{sub} /entry:{ent} '
                   f'/out:"{exe}" kernel32.lib user32.lib legacy_stdio_definitions.lib ucrt.lib msvcrt.lib')
            if bat:
                cmd = f'call "{bat}" >nul && {cmd}'
            return [Step(["cmd", "/c", cmd], self.root, {}, "ml64" if bits == 64 else "ml")]
        return []

    def run_step(self, target, debug):
        if target is None:
            return None
        if target.kind == "emu":                 # opened in the emulator window when the step starts
            src = self.root / target.data["file"]

            def argv():
                ok = open_emulator(getattr(self, "win", None), src)
                msg = f"{src.name}: opened in the 8086 emulator" if ok else \
                    f"{src.name} is an 8086 / DOS program: open it with the 8086 emulator"
                return ["cmd", "/c", "echo", msg] if os.name == "nt" else ["echo", msg]
            return LazyStep(argv, self.root, {}, target.name)
        return Step([str(self._exe(target))], self.root, {}, target.name)

    def debug_session(self, win, target, pre):
        if target is None or target.kind != "exe" or target.data.get("dialect") in ("masm", "fasm"):
            return None
        from ._others_base import gdb_session
        return gdb_session(win, self._exe(target), [], self.root, None)

    def commands(self):
        out = []
        objdump = find_tool("objdump")
        for t in self.targets:
            if t.kind == "exe" and objdump:
                out.append((f"Disassemble {Path(t.data['file']).name} (objdump -d -M intel)",
                            [Step([objdump, "-d", "-M", "intel", "--no-show-raw-insn", str(self._exe(t))],
                                  self.root, {}, "objdump")]))
        return out


def open_emulator(win, path: Path) -> bool:
    """Open an 8086 program in the teaching emulator (the emulator slice's entry point, docs/ASSEMBLY.md)."""
    import importlib
    for mod, fn in (("radide.features.asm_emulator", "open_emulator"), ("radide.asm.emu_ui", "open_emulator"),
                    ("radide.emu8086.ui", "open_emulator"), ("radide.features.emu8086", "open_emulator")):
        try:
            m = importlib.import_module(mod)
        except ImportError:
            continue
        f = getattr(m, fn, None)
        if callable(f):
            return bool(f(win, Path(path)))
    try:
        win.log(f"[assembly] {Path(path).name} is an 8086 / DOS program: the 8086 emulator is not installed")
    except Exception:  # noqa: BLE001
        pass
    return False


def open_asm(win, path: Path) -> bool:
    """A folder of assembly sources, or a RadASM .rap / WinAsm .wap project file."""
    path = Path(path)
    if path.is_dir() and probe(path):
        path = probe(path)
    project = ForeignProject(AsmFolderAdapter(path))
    a = project.adapter
    a.win = win
    if not a.modules:
        return False
    return show_projects(win, [project], project.name, Path(path))


def probe(folder: Path):
    """A RadASM / WinAsm project file in *folder* (plain .asm folders are offered by Open Folder detection)."""
    folder = Path(folder)
    for ext in PROJECT_EXT:
        hits = sorted(folder.glob("*" + ext))
        if hits:
            return hits[0]
    return None


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format([".rap"], open_asm, "RadASM project (.rap)", folder_probe=probe, name="radasm", priority=4)
    register_format([".wap"], open_asm, "WinAsm Studio project (.wap)", folder_probe=probe, name="winasm",
                    priority=4)


__all__ = ["AsmFolderAdapter", "AsmFolderInfo", "AsmProgram", "guess_dialect", "guess_bits", "entry_point",
           "scan_folder", "read_ide_project", "find_tool", "find_masm", "open_asm", "open_emulator", "register"]
