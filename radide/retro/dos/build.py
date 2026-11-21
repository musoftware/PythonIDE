"""Build a DOS project into a real DOS program (no Qt in here).

    python -m radide.retro.dos.build <project folder> [--no-download] [--compiler NAME]

Settings come from project.radproj ``"dos"`` (``settings_for``): kind, main file, output name (8.3), compiler,
memory model, EXE / COM, DOSBox-X cycles / machine / memory, keep window, program arguments. The build writes
``_build/diags.json`` ({"ok", "exe", "tool", "diags": [DosDiag...], "map"}) - the IDE's Error List shows its rows
(radide/features/dos_ide.py) - and prints "Build succeeded" / "Build failed" as its last line.

    kind     compiler            how
    qbasic   freebasic           FreeBASIC's DOS fbc.exe runs inside DOSBox-X (no window): fbc -lang qb -x X.EXE
             quickbasic (own)    BC.EXE + LINK.EXE of the user's QuickBASIC 4.5, inside DOSBox-X
    pascal   fpc                 ppcross8086 -Tmsdos -Wm<model> -Mtp -XX (Windows, fast)
             turbopascal (own)   TPC.EXE inside DOSBox-X
    c        openwatcom          wcl -bt=dos -m<model> (Windows); RAD IDE's include folder adds tcconio.h,
                                 tcgraph.h and graphics.h (BGI subset) for old Turbo C sources
             djgpp (own)         i586-pc-msdosdjgpp-gcc (32-bit protected mode, needs CWSDPMI at run time)
             turboc (own)        TCC.EXE inside DOSBox-X
    asm      jwasm               jwasm -mz (EXE) or -bin (COM), listing in _build\\<main>.LST, symbol map
    batch    -                   nothing to build (the run checks GOTO / CALL targets)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import compat, errors, toolchain
from .errors import DosDiag
from .templates import dos_name

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
BUILD_DIR = "_build"
DIAG_FILE = "diags.json"
INCLUDE_DIR = Path(__file__).resolve().parent / "include"

KIND_OF_LANGUAGE = {"dos-qbasic": "qbasic", "dos-pascal": "pascal", "dos-c": "c", "dos-asm": "asm",
                    "dos-batch": "batch"}
LANGUAGE_OF_KIND = {v: k for k, v in KIND_OF_LANGUAGE.items()}
MAIN_EXT = {"qbasic": ".BAS", "pascal": ".PAS", "c": ".C", "asm": ".ASM", "batch": ".BAT"}
COMPILERS = {"qbasic": ["freebasic", "quickbasic"], "pascal": ["fpc", "turbopascal"],
             "c": ["openwatcom", "djgpp", "turboc"], "asm": ["jwasm"], "batch": [""]}
MODELS = ["tiny", "small", "medium", "compact", "large"]


# ============================================================================ settings
def kind_of(project) -> str:
    lang = getattr(project, "language", "")
    if lang in KIND_OF_LANGUAGE:
        return KIND_OF_LANGUAGE[lang]
    return str((getattr(project, "extra", {}) or {}).get("dos", {}).get("kind", "")) or "qbasic"


def settings_for(project) -> dict:
    kind = kind_of(project)
    folder = Path(project.folder)
    main = ""
    for m in list(getattr(project, "modules", []) or []):
        if m.upper().endswith(MAIN_EXT[kind]):
            main = m
            break
    if project.startup:
        cand = project.startup if "." in project.startup else project.startup + MAIN_EXT[kind]
        hit = next((p.name for p in folder.glob("*") if p.name.lower() == cand.lower()), "")
        main = hit or main
    s = {"kind": kind, "main": main or ("MAIN" + MAIN_EXT[kind]), "exe": dos_name(project.name),
         "compiler": COMPILERS[kind][0], "model": "small", "output": "exe", "cycles": "max",
         "machine": "svga_s3", "memsize": 16, "keep_window": True, "args": "", "debugger": "auto",
         "warnings": True}
    user = dict((getattr(project, "extra", {}) or {}).get("dos", {}) or {})
    s.update({k: v for k, v in user.items() if v not in (None, "")})
    if s["compiler"] not in COMPILERS[kind]:
        s["compiler"] = COMPILERS[kind][0]
    s["exe"] = dos_name(str(s["exe"]).split(".")[0])
    return s


def output_name(s: dict) -> str:
    if s["kind"] == "batch":
        return s["main"]
    return s["exe"] + (".COM" if s.get("output") == "com" else ".EXE")


def sources(folder: Path, kind: str) -> list[Path]:
    exts = {"qbasic": (".bas",), "pascal": (".pas", ".pp"), "c": (".c",), "asm": (".asm",),
            "batch": (".bat",)}[kind]
    return sorted(p for p in Path(folder).iterdir() if p.is_file() and p.suffix.lower() in exts)


def read_diagnostics(folder: Path) -> dict:
    try:
        return json.loads((Path(folder) / BUILD_DIR / DIAG_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def is_stale(folder: Path, s: dict) -> bool:
    """True when the program is missing or older than a source file."""
    out = Path(folder) / output_name(s)
    if s["kind"] == "batch":
        return False
    if not out.is_file():
        return True
    t = out.stat().st_mtime
    files = sources(folder, s["kind"]) + [p for p in Path(folder).iterdir()
                                          if p.suffix.lower() in (".h", ".inc", ".bi")]
    return any(p.stat().st_mtime > t for p in files)


# ============================================================================ builder
class Builder:
    def __init__(self, folder: Path, project=None, log=print, download: bool = True):
        from ...model import Project
        self.folder = Path(folder).resolve()
        self.project = project or Project.load(self.folder)
        self.s = settings_for(self.project)
        self.log = log
        self.download = download
        self.build_dir = self.folder / BUILD_DIR
        self.diags: list[DosDiag] = []
        self.tool = self.s["compiler"]
        self.map_file = ""

    # ---------------------------------------------------------------- helpers
    def _run(self, args: list[str], env: dict | None = None, timeout: int = 300) -> tuple[int, str]:
        self.log("> " + " ".join(f'"{a}"' if " " in a else a for a in args))
        try:
            r = subprocess.run(args, cwd=str(self.folder), env=env, capture_output=True, text=True,
                               timeout=timeout, creationflags=NO_WINDOW, errors="replace")
        except (OSError, subprocess.SubprocessError) as e:
            return -1, str(e)
        text = (r.stdout or "") + (r.stderr or "")
        if text.strip():
            self.log(text.rstrip())
        return r.returncode, text

    def _dos_build(self, mounts: list, commands: list[str], log_name: str, path: list[str], timeout: int = 180,
                   env: dict | None = None) -> str:
        """Run DOS commands headless in DOSBox-X (C: = project); returns the text of _build\\<log_name>."""
        from . import dosbox
        log_file = self.build_dir / log_name
        try:
            log_file.unlink()
        except OSError:
            pass
        run = dosbox.DosRun(mounts=[("C", self.folder)] + mounts, commands=commands, path=path, env=env or {},
                            cycles="max", memsize=32, sound=False, core="dynamic")
        self.log("DOSBox-X (no window): " + " && ".join(commands))
        rc, timed_out = dosbox.run_headless(run, self.build_dir, timeout, name="build.conf", log=self.log)
        if timed_out:
            self.diags.append(DosDiag("Error", f"The DOS compiler did not finish within {timeout} s.", "", 0, 0,
                                      self.tool))
        try:
            text = log_file.read_bytes().decode("cp437", "replace")
        except OSError:
            text = ""
        if text.strip():
            self.log(text.rstrip())
        return text

    def _remove_output(self, out: Path) -> float:
        try:
            out.unlink()
        except OSError:
            pass
        return time.time()

    # ---------------------------------------------------------------- per compiler
    def build_freebasic(self, main: str, out: Path) -> bool:
        if not toolchain.ensure_for("freebasic", self.log, self.download):
            self.diags.append(DosDiag("Error", toolchain.missing_hint("freebasic"), tool="freebasic"))
            return False
        fb = toolchain.freebasic_dir()
        cws = str(Path(toolchain.cwsdpmi_exe()).parent)
        opts = "-lang qb" + (" -w all" if self.s.get("warnings") else "")
        cmd = f"fbc {opts} -map {BUILD_DIR}\\PROG.MAP -x {out.name} {main} > {BUILD_DIR}\\FBC.LOG"
        text = self._dos_build([("D", fb), ("E", cws)], [cmd], "FBC.LOG", ["D:\\", "E:\\"])
        self.diags += errors.parse_freebasic(text, self.folder)
        if out.is_file():
            self.map_file = str(self.build_dir / "PROG.MAP")
            try:                               # FreeBASIC DOS programs need a DPMI host at run time
                shutil.copy2(toolchain.cwsdpmi_exe(), self.folder / "CWSDPMI.EXE")
            except OSError:
                pass
        return out.is_file()

    def build_quickbasic(self, main: str, out: Path) -> bool:
        exe = toolchain.user_tool("quickbasic")
        if not exe or not (Path(exe).parent / "BC.EXE").exists():
            self.diags.append(DosDiag("Error", "QuickBASIC (BC.EXE / LINK.EXE) is not configured: Tools > DOS "
                                      "Toolchains... > your own copies.", tool="bc"))
            return False
        qb = str(Path(exe).parent)
        obj = Path(main).stem.upper() + ".OBJ"
        text = self._dos_build([("D", qb)], [f"BC {main} /O; > {BUILD_DIR}\\BC.LOG",
                                             f"LINK {obj},{out.name},NUL,D:\\BCOM45.LIB; >> {BUILD_DIR}\\BC.LOG"],
                               "BC.LOG", ["D:\\"])
        src = (self.folder / main).read_text(encoding="cp437", errors="replace")
        self.diags += errors.parse_quickbasic(text, self.folder, src, main)
        return out.is_file()

    def build_fpc(self, main: str, out: Path) -> bool:
        if not toolchain.ensure_for("fpc", self.log, self.download):
            self.diags.append(DosDiag("Error", toolchain.missing_hint("fpc"), tool="fpc"))
            return False
        model = self.s.get("model", "small")
        com = self.s.get("output") == "com"
        if com:
            model = "tiny"
        units = toolchain.fpc_units(model)
        ppc = toolchain.fpc_compiler()
        unit_out = self.build_dir / "units"
        unit_out.mkdir(parents=True, exist_ok=True)
        args = [ppc, "-Tmsdos", f"-Wm{model.capitalize()}", "-XX", "-Mtp", "-vewnhi", f"-Fu{units}\\*",
                f"-Fu{self.folder}", f"-Fi{self.folder}", f"-FD{Path(ppc).parent}", f"-FU{unit_out}",
                f"-o{out}", "-Xm"]
        if com:
            args.append("-WtCOM")
        args.append(main)
        rc, text = self._run(args)
        self.diags += errors.parse_fpc(text, self.folder)
        mp = out.with_suffix(".map")
        if mp.is_file():
            shutil.move(str(mp), str(self.build_dir / "PROG.MAP"))
            self.map_file = str(self.build_dir / "PROG.MAP")
        for junk in self.folder.glob("*.o"):
            try:
                junk.unlink()
            except OSError:
                pass
        return rc == 0 and out.is_file()

    def build_turbopascal(self, main: str, out: Path) -> bool:
        exe = toolchain.user_tool("turbopascal")
        if not exe:
            self.diags.append(DosDiag("Error", "Turbo Pascal (TPC.EXE) is not configured: Tools > DOS Toolchains... "
                                      "> your own copies.", tool="tpc"))
            return False
        tp = str(Path(exe).parent)
        text = self._dos_build([("D", tp)], [f"TPC /B /UD:\\ /ED:\\ {main} > {BUILD_DIR}\\TPC.LOG"], "TPC.LOG",
                               ["D:\\"])
        self.diags += errors.parse_turbo_pascal(text, self.folder)
        made = self.folder / (Path(main).stem.upper() + ".EXE")
        if made.is_file() and made.name.upper() != out.name.upper():
            shutil.move(str(made), str(out))
        return out.is_file()

    def build_openwatcom(self, main: str, out: Path) -> bool:
        if not toolchain.ensure_for("openwatcom", self.log, self.download):
            self.diags.append(DosDiag("Error", toolchain.missing_hint("openwatcom"), tool="openwatcom"))
            return False
        env = toolchain.watcom_env()
        model = self.s.get("model", "small")
        com = self.s.get("output") == "com"
        mflag = {"tiny": "s", "small": "s", "medium": "m", "compact": "c", "large": "l"}.get(model, "s")
        cfiles = [p.name for p in sources(self.folder, "c")]
        if main not in cfiles:
            cfiles.insert(0, main)
        texts = "\n".join((self.folder / f).read_text(encoding="cp437", errors="replace") for f in cfiles
                          if (self.folder / f).is_file())
        objdir = self.build_dir / "obj"
        objdir.mkdir(parents=True, exist_ok=True)
        wroot = toolchain.watcom_root()
        args = [str(Path(wroot) / "binnt64" / "wcl.exe"), "-zq", "-bt=dos", f"-m{mflag}", "-0",
                "-w3" if self.s.get("warnings") else "-w0", f"-i={self.folder}", f"-i={INCLUDE_DIR}",
                f"-i={Path(wroot) / 'h'}", f"-fo={objdir}\\", f"-fe={out.name}", f"-fm={self.build_dir / 'PROG.MAP'}"]
        if com:
            args[3:4] = ["-mt"]
            args.append("-bcl=com")
        if compat.needs_tcconio(texts):
            args.append(f"-fi={INCLUDE_DIR / 'TCCONIO.H'}")
        args += cfiles
        if re.search(r"#\s*include\s*<graph\.h>", texts):
            args.append("graph.lib")
        rc, text = self._run(args, env)
        self.diags += errors.parse_watcom(text, self.folder)
        if (self.build_dir / "PROG.MAP").is_file():
            self.map_file = str(self.build_dir / "PROG.MAP")
        return rc == 0 and out.is_file()

    def build_djgpp(self, main: str, out: Path) -> bool:
        gcc = toolchain.user_tool("djgpp")
        if not gcc:
            self.diags.append(DosDiag("Error", "DJGPP (i586-pc-msdosdjgpp-gcc) is not configured: Tools > DOS "
                                      "Toolchains... > your own copies. RAD IDE does not download it (no official "
                                      "Windows-hosted build).", tool="djgpp"))
            return False
        cfiles = [p.name for p in sources(self.folder, "c")]
        rc, text = self._run([gcc, "-O2", "-Wall", f"-I{INCLUDE_DIR}", "-o", out.name,
                              f"-Wl,-Map,{self.build_dir / 'PROG.MAP'}"] + cfiles)
        self.diags += errors.parse_gcc(text, self.folder)
        if out.is_file():
            try:
                shutil.copy2(toolchain.cwsdpmi_exe() or "", self.folder / "CWSDPMI.EXE")
            except OSError:
                pass
        return rc == 0 and out.is_file()

    def build_turboc(self, main: str, out: Path) -> bool:
        exe = toolchain.user_tool("turboc")
        if not exe:
            self.diags.append(DosDiag("Error", "Turbo C (TCC.EXE) is not configured: Tools > DOS Toolchains... > "
                                      "your own copies.", tool="tcc"))
            return False
        root = Path(exe).parent.parent if Path(exe).parent.name.upper() == "BIN" else Path(exe).parent
        rel_bin = os.path.relpath(Path(exe).parent, root).replace("/", "\\")
        bin_dir = "D:\\" if rel_bin in (".", "") else f"D:\\{rel_bin}"
        model = {"tiny": "t", "small": "s", "medium": "m", "compact": "c", "large": "l"}.get(self.s["model"], "s")
        text = self._dos_build([("D", str(root))],
                               [f"TCC -m{model} -ID:\\INCLUDE -LD:\\LIB -e{out.stem} {main} > {BUILD_DIR}\\TCC.LOG"],
                               "TCC.LOG", [bin_dir])
        self.diags += errors.parse_turbo_c(text, self.folder)
        return out.is_file()

    def build_jwasm(self, main: str, out: Path) -> bool:
        if not toolchain.ensure_for("jwasm", self.log, self.download):
            self.diags.append(DosDiag("Error", toolchain.missing_hint("jwasm"), tool="jwasm"))
            return False
        lst = self.build_dir / (Path(main).stem.upper() + ".LST")
        fmt = "-bin" if self.s.get("output") == "com" else "-mz"
        rc, text = self._run([toolchain.jwasm_exe(), "-q", fmt, f"-Fl={lst}",
                              f"-Fo={out.name}", main])
        self.diags += errors.parse_jwasm(text, self.folder)
        if out.is_file() and lst.is_file():
            self.map_file = str(write_asm_map(lst, self.build_dir / "PROG.MAP", self.s.get("output") == "com"))
        return rc == 0 and out.is_file()

    # ---------------------------------------------------------------- batch
    def check_batch(self) -> bool:
        for p in sources(self.folder, "batch"):
            self.diags += lint_batch(p)
        return not any(d.severity == "Error" for d in self.diags)

    # ---------------------------------------------------------------- main
    def build(self) -> bool:
        t0 = time.time()
        self.build_dir.mkdir(parents=True, exist_ok=True)
        s = self.s
        kind = s["kind"]
        main = s["main"]
        if kind != "batch" and not (self.folder / main).is_file():
            self.diags.append(DosDiag("Error", f"Main file {main} not found (Project > DOS Settings).", main, 0))
            return self._finish(False, "", t0)
        for src in sources(self.folder, kind):
            try:
                text = src.read_text(encoding="cp437", errors="replace")
            except OSError:
                continue
            for n in compat.scan(src, text, kind, self.folder):
                self.diags.append(DosDiag(n.severity, n.message, src.name, n.line, 0, "compat"))
        if kind == "batch":
            ok = self.check_batch()
            return self._finish(ok, "", t0)
        out = self.folder / output_name(s)
        self._remove_output(out)
        self.log(f"------ Build started: {self.project.name} ({kind}, {self.tool}) -> {out.name} ------")
        fn = getattr(self, f"build_{self.tool}", None)
        if fn is None:
            self.diags.append(DosDiag("Error", f"Unknown compiler {self.tool}", tool=self.tool))
            return self._finish(False, "", t0)
        try:
            ok = fn(main, out)
        except Exception as e:  # noqa: BLE001 - report, never crash the IDE's build
            self.diags.append(DosDiag("Error", f"{self.tool}: {e}", tool=self.tool))
            ok = False
        if not ok and not any(d.severity == "Error" for d in self.diags):
            self.diags.append(DosDiag("Error", f"{self.tool} did not produce {out.name} (see the Output window).",
                                      tool=self.tool))
        return self._finish(ok, str(out) if ok else "", t0)

    def _finish(self, ok: bool, exe: str, t0: float) -> bool:
        data = {"ok": ok, "exe": exe, "tool": self.tool, "kind": self.s["kind"], "map": self.map_file,
                "time": round(time.time() - t0, 2), "diags": [d.to_dict() for d in self.diags]}
        self.build_dir.mkdir(parents=True, exist_ok=True)
        (self.build_dir / DIAG_FILE).write_text(json.dumps(data, indent=1), encoding="utf-8")
        errs = sum(d.severity == "Error" for d in self.diags)
        warns = sum(d.severity == "Warning" for d in self.diags)
        for d in self.diags:
            where = f"{d.file}({d.line})" if d.file and d.line else (d.file or self.s["main"])
            self.log(f"{where}: {d.severity.lower()}: {d.message}")
        self.log(f"========== {'Build succeeded' if ok else 'Build failed'}: {Path(exe).name if exe else ''} "
                 f"{errs} error(s), {warns} warning(s), {data['time']} s ==========")
        return ok


# ============================================================================ batch lint / asm map
_BAT_LABEL = re.compile(r"^\s*:(\w+)", re.M)
_BAT_GOTO = re.compile(r"(?im)\bgoto\s+:?(\w+)")
_BAT_CALL = re.compile(r"(?im)^\s*(?:@\s*)?call\s+([^\s%]+)")


def lint_batch(path: Path) -> list[DosDiag]:
    """GOTO to a missing label, CALL of a missing batch file, a line longer than 127 characters."""
    out = []
    text = Path(path).read_text(encoding="cp437", errors="replace")
    labels = {m.group(1).lower() for m in _BAT_LABEL.finditer(text)}
    for i, line in enumerate(text.splitlines(), 1):
        if line.lstrip().lower().startswith(("rem", "::")):
            continue
        for m in _BAT_GOTO.finditer(line):
            if m.group(1).lower() not in labels and m.group(1).lower() != "eof":
                out.append(DosDiag("Error", f"GOTO {m.group(1)}: there is no label :{m.group(1)}", path.name, i, 0,
                                   "batch"))
        m = _BAT_CALL.match(line)
        if m:
            target = m.group(1)
            name = target if "." in target else target + ".BAT"
            if not any(p.name.lower() == name.lower() for p in Path(path).parent.iterdir()) and \
                    target.lower().endswith(".bat"):
                out.append(DosDiag("Warning", f"CALL {target}: the file is not in the project folder", path.name, i,
                                   0, "batch"))
        if len(line) > 127:
            out.append(DosDiag("Warning", "Line longer than 127 characters (COMMAND.COM cuts it)", path.name, i, 0,
                               "batch"))
    return out


def write_asm_map(lst: Path, out: Path, com: bool = False) -> Path:
    """A readable symbol map (segment, offset, name) from a JWasm listing's symbol tables."""
    text = Path(lst).read_text(encoding="cp437", errors="replace")
    rows = []
    for m in re.finditer(r"^(\w[\w@?$]*)\s*\.*\s+(P\s+\w+|L\s+\w+|Byte|Word|DWord|Near|Far)\s+([0-9A-F]{4,8})\s+"
                         r"(\w+)", text, re.M):
        rows.append((m.group(4), m.group(3), m.group(1), m.group(2)))
    lines = ["RAD IDE symbol map (from the JWasm listing) - segment, offset, symbol, type",
             "In the DOSBox-X debugger: BP CS:<offset> sets a breakpoint; the program starts at CS:"
             + ("0100" if com else "0000"), ""]
    for seg, off, name, typ in sorted(rows, key=lambda r: (r[0], r[1])):
        lines.append(f"{seg:<10} {off:>8}  {name:<24} {typ}")
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return Path(out)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    folder = Path(argv[0])
    download = "--no-download" not in argv
    b = Builder(folder, log=lambda t: print(t, flush=True), download=download)
    if "--compiler" in argv:
        b.tool = b.s["compiler"] = argv[argv.index("--compiler") + 1]
    return 0 if b.build() else 1


if __name__ == "__main__":
    sys.exit(main())
