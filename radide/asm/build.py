"""Assemble + link an Assembly project.

    python -m radide.asm.build <project folder> [--release] [--check]

Build / Run (Ctrl+F5) and Debug (F5) call this through the GUI Bridge runner (radide/runtimes/bridge.py,
``--build``). It prints every command and the tools' messages (the Output window), downloads NASM / FASM the
first time they are needed (radide/asm/toolchain.py), writes ``_build/diagnostics.json`` (the Error List rows,
radide/asm/errors.py) and produces ``_radapp.exe`` in the project folder.

Project settings: the "asm" entry of project.radproj (defaults from the language)::

    "asm": {"assembler": "nasm" | "fasm" | "masm" | "gas",
            "arch": "x64" | "x86",
            "linker": "gcc" | "ld" | "golink" | "link" | "none",    (none = FASM writes the .exe)
            "entry": "main",            (C runtime entry with gcc / link; the entry symbol with ld / golink)
            "subsystem": "console" | "windows",
            "libs": ["user32", ...],    (extra libraries / DLLs)
            "debug": true,              (line debug information gdb can read: radide/asm/dwarf.py)
            "console": "ide" | "external"}   (where Ctrl+F5 runs a console program)

Pipelines (x64 / x86):

    nasm   nasm -f win64|win32 -P anchor -l listing -> .obj  (+ DWARF lines: dwarf.py + as)  -> gcc | ld i386pe
    gas    as --64|--32 -g -> .o                                                              -> gcc | ld i386pe
    fasm   fasm main.asm _radapp.exe (format PE / PE64)   or   format MS COFF / MS64 COFF -> .obj -> gcc | ld
    masm   vcvars + ml64 /c /Zi | ml /c /coff /Zi -> .obj -> link /DEBUG (C runtime: msvcrt + legacy_stdio)

GUI Bridge form projects (NASM x64 only): the form files + modules + _radmain.asm, and the C client radgui.c +
radasm.c compiled by gcc in the same command.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import dwarf, errors
from . import toolchain as tc

BUILD_DIR = "_build"
EXE_NAME = "_radapp.exe" if os.name == "nt" else "_radapp"
DIAG_FILE = "diagnostics.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

DEFAULTS = {
    "asm-nasm": {"assembler": "nasm", "arch": "x64", "linker": "gcc", "entry": "main"},
    "asm-fasm": {"assembler": "fasm", "arch": "x64", "linker": "none", "entry": "start"},
    "asm-masm": {"assembler": "masm", "arch": "x64", "linker": "link", "entry": "main"},
    "asm-gas": {"assembler": "gas", "arch": "x64", "linker": "gcc", "entry": "main"},
}
CODE_EXT = {"nasm": (".asm", ".nasm"), "fasm": (".asm", ".fasm"), "masm": (".asm",), "gas": (".s", ".S", ".asm")}


def settings_for(project, plugin_id: str | None = None) -> dict:
    """The effective "asm" settings of *project* (project.radproj entry over the language defaults)."""
    pid = plugin_id or getattr(project, "language", "asm-nasm")
    s = dict(DEFAULTS.get(pid, DEFAULTS["asm-nasm"]))
    s.update({"subsystem": "console", "libs": [], "debug": True, "console": "ide"})
    extra = (getattr(project, "extra", {}) or {}).get("asm")
    if isinstance(extra, dict):
        s.update({k: v for k, v in extra.items() if v is not None})
    if s.get("arch") not in ("x64", "x86"):
        s["arch"] = "x64"
    if s["linker"] in ("", "auto", None):
        s["linker"] = DEFAULTS.get(pid, DEFAULTS["asm-nasm"])["linker"]
    if s["assembler"] in ("nasm", "gas") and s["arch"] == "x86" and s["linker"] == "gcc":
        s["linker"] = "ld"                      # the MinGW-w64 gcc only links 64-bit programs
    return s


def _q(s) -> str:
    s = str(s)
    return f'"{s}"' if (" " in s or not s) and not s.startswith('"') else s


def system_dll_dir(arch: str) -> str:
    """Folder of the system DLLs a 32-/64-bit program links against directly (ld / GoLink)."""
    win = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    if arch == "x86" and (win / "SysWOW64").is_dir():
        return str(win / "SysWOW64")
    return str(win / "System32")


class BuildError(Exception):
    pass


class Builder:
    def __init__(self, folder: Path, project=None, plugin_id: str | None = None, log=None, release: bool = False):
        self.folder = Path(folder).resolve()
        if project is None:
            from ..model import Project
            project = Project.load(self.folder)
        self.project = project
        self.plugin_id = plugin_id or project.language
        self.s = settings_for(project, self.plugin_id)
        self.release = release
        self.debug = bool(self.s.get("debug", True)) and not release
        self.log = log or (lambda t: print(t, flush=True))
        self.output: list[str] = []
        self.listings: dict[str, Path] = {}     # source file name -> listing (NASM) for linker error lines
        self.bdir = self.folder / BUILD_DIR

    # ------------------------------------------------------------ files
    @property
    def arch(self) -> str:
        return self.s["arch"]

    @property
    def assembler(self) -> str:
        return self.s["assembler"]

    def form_sources(self) -> list[str]:
        forms = [f for f in self.project.forms
                 if getattr(self.project, "form_language", lambda _f: self.project.language)(f).startswith("asm-")]
        return [f"{f}.asm" for f in forms]

    def is_forms(self) -> bool:
        return bool(self.form_sources())

    def sources(self) -> list[str]:
        exts = CODE_EXT.get(self.assembler, (".asm",))
        files = self.form_sources()
        files += [m for m in self.project.modules if m.endswith(exts) and m not in files]
        if self.is_forms():
            files.append("_radmain.asm")
        return [f for f in files if (self.folder / f).is_file()]

    def env(self) -> dict:
        env = dict(os.environ)
        gcc = tc.mingw("gcc")
        if gcc:
            env["PATH"] = str(Path(gcc).parent) + os.pathsep + env.get("PATH", "")
        inc = tc.fasm_include() if self.assembler == "fasm" else ""
        if inc:                                  # FASM's include 'win64a.inc' looks in %INCLUDE%
            env["INCLUDE"] = inc
        return env

    # ------------------------------------------------------------ running tools
    def run(self, argv, shell: bool = False) -> int:
        shown = argv if isinstance(argv, str) else " ".join(_q(a) for a in argv)
        self.log(f"> {shown}")
        try:
            r = subprocess.run(argv, cwd=str(self.folder), capture_output=True, text=True, errors="replace",
                               env=self.env(), shell=shell, creationflags=NO_WINDOW)
        except OSError as e:
            self.output.append(str(e))
            self.log(str(e))
            return 1
        text = (r.stdout or "") + (r.stderr or "")
        text = text.strip()
        if text:
            self.output.append(text)
            self.log(text)
        return r.returncode

    def need(self, tool: str) -> str:
        exe = tc.ensure(tool, self.log)
        if not exe:
            raise BuildError(tc.missing_hint(tool))
        return exe

    # ------------------------------------------------------------ assemble
    def _nasm(self, src: str) -> list[str]:
        nasm = self.need("nasm")
        stem = Path(src).stem
        obj = self.bdir / f"{stem}.obj"
        lst = self.bdir / f"{stem}.lst"
        anchor = self.bdir / f"{stem}.anchor.inc"
        anchor.write_text(dwarf.anchor_source(src), encoding="utf-8")
        fmt = "win64" if self.arch == "x64" else "win32"
        argv = [nasm, "-f", fmt, "-I", str(self.folder) + os.sep, "-P", str(anchor), "-l", str(lst),
                "-o", str(obj), src]
        if self.run(argv) != 0:
            raise BuildError(f"nasm failed on {src}")
        self.listings[src] = lst
        objs = [str(obj)]
        if self.debug and src != "_radmain.asm":
            dbg = self._dwarf_object(src, lst)
            if dbg:
                objs.append(dbg)
        return objs

    def _dwarf_object(self, src: str, lst: Path) -> str:
        """The DWARF line table of a NASM module as a COFF object (radide/asm/dwarf.py); "" when not possible."""
        gas = tc.mingw("as")
        if not gas or not lst.is_file():
            return ""
        try:
            lines = (self.folder / src).read_text(encoding="utf-8", errors="replace").splitlines()
            rows, size = dwarf.parse_listing(lst.read_text(encoding="utf-8", errors="replace"), lines)
        except OSError:
            return ""
        if not rows:
            return ""
        stem = Path(src).stem
        s_file = self.bdir / f"{stem}.dbg.s"
        o_file = self.bdir / f"{stem}.dbg.o"
        s_file.write_text(dwarf.line_program(src, str(self.folder), rows, size,
                                             64 if self.arch == "x64" else 32), encoding="utf-8")
        r = subprocess.run([gas, "--64" if self.arch == "x64" else "--32", "-o", str(o_file), str(s_file)],
                           cwd=str(self.folder), capture_output=True, text=True, creationflags=NO_WINDOW)
        if r.returncode != 0:
            self.log(f"(no line debug information for {src}: {(r.stdout + r.stderr).strip()[:300]})")
            return ""
        return str(o_file)

    def _gas(self, src: str) -> list[str]:
        gas = self.need("as")
        obj = self.bdir / f"{Path(src).stem}.o"
        # --gdwarf-3: plain -g writes STABS on PE targets (gdb-readable DWARF is what we want)
        argv = [gas, "--64" if self.arch == "x64" else "--32"] + (["--gdwarf-3"] if self.debug else []) + \
            ["-I", str(self.folder), "-o", str(obj), src]
        if self.run(argv) != 0:
            raise BuildError(f"as failed on {src}")
        return [str(obj)]

    def _fasm_main(self) -> str:
        srcs = self.sources()
        for s in srcs:
            try:
                if re.search(r"^\s*format\b", (self.folder / s).read_text(encoding="utf-8", errors="replace"),
                             re.M | re.I):
                    return s
            except OSError:
                continue
        return srcs[0] if srcs else ""

    def _fasm(self, src: str, out: Path) -> None:
        fasm = self.need("fasm")
        if not tc.fasm_include():
            self.log("(FASM's INCLUDE folder was not found: win32a.inc / win64a.inc will be missing)")
        if self.run([fasm, src, str(out)]) != 0:
            raise BuildError(f"fasm failed on {src}")

    # ------------------------------------------------------------ link
    def _libs(self) -> list[str]:
        return [str(x) for x in (self.s.get("libs") or []) if str(x).strip()]

    def _link_gcc(self, objs: list[str], exe: Path) -> None:
        gcc = self.need("gcc")
        argv = [gcc] + (["-g"] if self.debug else ["-s"]) + objs
        if self.is_forms():
            argv += ["-I", str(self.folder), "radgui.c", "radasm.c", "-lws2_32"]
        entry = self.s.get("entry") or "main"
        if entry != "main":
            argv += ["-nostartfiles", f"-Wl,-e,{entry}", "-lkernel32", "-luser32", "-lmsvcrt"]
        if self.s.get("subsystem") == "windows" and not self.is_forms():
            argv.append("-mwindows")
        argv += [f"-l{lib}" for lib in self._libs()] + ["-static", "-o", str(exe)]
        if self.run(argv) != 0:
            raise BuildError("link failed (gcc)")

    def _link_ld(self, objs: list[str], exe: Path) -> None:
        ld = self.need("ld")
        emu = "i386pe" if self.arch == "x86" else "i386pep"
        entry = self.s.get("entry") or ("_main" if self.arch == "x86" else "main")
        argv = [ld, "-m", emu, "--subsystem", self.s.get("subsystem") or "console", "-e", entry,
                "--enable-stdcall-fixup"] + (["-s"] if not self.debug else []) + ["-o", str(exe)] + objs + \
            ["-L", system_dll_dir(self.arch), "-lmsvcrt", "-lkernel32", "-luser32"] + \
            [f"-l{lib}" for lib in self._libs()]
        if self.run(argv) != 0:
            raise BuildError("link failed (ld)")

    def _link_golink(self, objs: list[str], exe: Path) -> None:
        golink = self.need("golink")
        entry = self.s.get("entry") or ("_main" if self.arch == "x86" else "main")
        objs = [o for o in objs if not o.endswith(".dbg.o")]          # GoLink does not keep DWARF sections
        argv = [golink, "/" + ("console" if (self.s.get("subsystem") or "console") == "console" else "gui"),
                "/ni", "/entry", entry] + (["/64"] if self.arch == "x64" else []) + objs + \
            ["kernel32.dll", "user32.dll", "msvcrt.dll"] + [f"{lib}.dll" for lib in self._libs()] + ["/fo", str(exe)]
        if self.run(argv) != 0 or not exe.is_file():
            raise BuildError("link failed (GoLink)")

    def _masm(self, srcs: list[str], exe: Path) -> None:
        from ..languages.c_bridge import VS_INSTALLER, find_vcvars
        ml = tc.find_masm(self.arch)
        vcvars = find_vcvars()
        if not ml or not vcvars:
            raise BuildError(tc.missing_hint("ml64" if self.arch == "x64" else "ml"))
        bat = Path(vcvars) if self.arch == "x64" else Path(vcvars).with_name("vcvars32.bat")
        mlname = "ml64" if self.arch == "x64" else "ml"
        objs = []
        steps = [f'set "PATH={VS_INSTALLER};%PATH%"', f'call "{bat}" >nul']
        for s in srcs:
            obj = f"{BUILD_DIR}\\{Path(s).stem}.obj"
            objs.append(obj)
            flags = "/nologo /c" + (" /coff" if self.arch == "x86" else "") + (" /Zi" if self.debug else "")
            steps.append(f'{mlname} {flags} /Fo"{obj}" "{s}"')
        entry = self.s.get("entry") or "main"
        libs = " ".join(f"{lib}.lib" for lib in self._libs())
        sub = "WINDOWS" if self.s.get("subsystem") == "windows" else "CONSOLE"
        steps.append(f'link /nologo{" /DEBUG" if self.debug else ""} /SUBSYSTEM:{sub} /OUT:"{exe.name}" ' +
                     " ".join(f'"{o}"' for o in objs) +
                     (f" /ENTRY:{entry}" if entry not in ("main", "_main") else "") +
                     f" msvcrt.lib legacy_stdio_definitions.lib ucrt.lib vcruntime.lib kernel32.lib user32.lib {libs}")
        if self.run(" && ".join(steps), shell=True) != 0:
            raise BuildError("MASM build failed")

    # ------------------------------------------------------------ build
    def line_for_offset(self, file: str, section: str, offset: int) -> int:
        """Source line of ``file(.text+offset)`` from the NASM listing (linker messages)."""
        name = Path(file).name
        lst = next((p for s, p in self.listings.items() if Path(s).name.lower() == name.lower()), None)
        if lst is None or section.lower() != ".text":
            return 0
        try:
            lines = (self.folder / name).read_text(encoding="utf-8", errors="replace").splitlines()
            rows, _ = dwarf.parse_listing(lst.read_text(encoding="utf-8", errors="replace"), lines)
        except OSError:
            return 0
        best = 0
        for ln, off in rows:
            if off <= offset:
                best = ln
        return best

    def build(self) -> bool:
        self.bdir.mkdir(exist_ok=True)
        exe = self.folder / EXE_NAME
        ok = False
        message = ""
        try:
            if self.is_forms() and (self.assembler != "nasm" or self.arch != "x64"):
                raise BuildError("Assembly forms (GUI Bridge) need NASM x64: set \"assembler\": \"nasm\", "
                                 "\"arch\": \"x64\" in project.radproj")
            self._prepare_forms()
            srcs = self.sources()
            if not srcs:
                raise BuildError("nothing to build: the project has no assembly source file")
            self.log(f"Assembly build: {self.assembler} {self.arch}, linker {self.s['linker']}, "
                     f"{'debug' if self.debug else 'release'}")
            if exe.exists():
                try:
                    exe.unlink()
                except OSError:
                    raise BuildError(f"{EXE_NAME} is in use (is the program still running?)")
            if self.assembler == "masm":
                self._masm(srcs, exe)
            elif self.assembler == "fasm":
                main = self._fasm_main()
                text = (self.folder / main).read_text(encoding="utf-8", errors="replace")
                if re.search(r"^\s*format\s+(MS64\s+COFF|MS\s+COFF|COFF)\b", text, re.M | re.I):
                    obj = self.bdir / f"{Path(main).stem}.obj"
                    self._fasm(main, obj)
                    self._link([str(obj)], exe)
                else:
                    self._fasm(main, exe)
            else:
                objs: list[str] = []
                for s in srcs:
                    objs += self._nasm(s) if self.assembler == "nasm" else self._gas(s)
                self._link(objs, exe)
            ok = exe.is_file()
            if not ok:
                raise BuildError(f"{EXE_NAME} was not produced")
            self.log(f"Build succeeded: {exe.name}")
        except BuildError as e:
            message = str(e)
            self.log(f"Build failed: {message}")
        diags = errors.parse("\n".join(self.output), self.folder, self.line_for_offset)
        try:
            errors.locate_unresolved(diags, self.folder, [s for s in self.sources() if s != "_radmain.asm"])
        except OSError:
            pass
        if not ok and not any(d.severity == "Error" for d in diags):
            diags.append(errors.AsmDiag("Error", message or "build failed", "", 0))
        try:
            (self.bdir / DIAG_FILE).write_text(json.dumps({"ok": ok, "exe": str(exe) if ok else "",
                                                           "diags": [d.to_dict() for d in diags]}, indent=1),
                                               encoding="utf-8")
        except OSError:
            pass
        return ok

    def _link(self, objs: list[str], exe: Path) -> None:
        linker = self.s.get("linker") or "gcc"
        if linker == "golink":
            self._link_golink(objs, exe)
        elif linker == "ld":
            self._link_ld(objs, exe)
        else:
            if self.arch == "x86":
                self._link_ld(objs, exe)
            else:
                self._link_gcc(objs, exe)

    def _prepare_forms(self) -> None:
        """GUI Bridge files of a form project (radgui.*, radasm.c, Form.inc, _radmain.asm)."""
        if not self.is_forms():
            return
        try:
            from ..languages import get_plugin
            get_plugin("asm-nasm").prepare(self.folder, self.project)
        except Exception as e:  # noqa: BLE001 - reported as a build error
            raise BuildError(f"cannot generate the GUI Bridge files: {e}")

    # ------------------------------------------------------------ syntax check (Error List on save)
    def check(self, texts: dict[str, str] | None = None) -> list[errors.AsmDiag]:
        """Assemble every source without linking (unsaved editor *texts* win) and return the messages."""
        self.bdir.mkdir(exist_ok=True)
        chk = self.bdir / "check"
        chk.mkdir(exist_ok=True)
        out: list[errors.AsmDiag] = []
        tool = {"nasm": "nasm", "gas": "as", "fasm": "fasm", "masm": "ml64" if self.arch == "x64" else "ml"}[
            self.assembler]
        exe = tc.find(tool)
        if not exe:
            return out
        srcs = [s for s in self.sources() if s != "_radmain.asm"]
        if self.assembler == "fasm":
            srcs = [self._fasm_main()] if srcs else []
        for src in srcs:
            path = self.folder / src
            if texts and src in texts:
                try:
                    disk = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    disk = None
                if disk != texts[src]:
                    path = chk / Path(src).name
                    path.write_text(texts[src], encoding="utf-8")
            if self.assembler == "nasm":
                argv = [exe, "-f", "win64" if self.arch == "x64" else "win32", "-I", str(self.folder) + os.sep,
                        "-o", str(chk / "out.obj"), str(path)]
            elif self.assembler == "gas":
                argv = [exe, "--64" if self.arch == "x64" else "--32", "-I", str(self.folder), "-o",
                        str(chk / "out.o"), str(path)]
            elif self.assembler == "fasm":
                argv = [exe, str(path), str(chk / "out.bin")]
            else:
                argv = [exe, "/nologo", "/c", "/Zs", str(path)]
            try:
                r = subprocess.run(argv, cwd=str(self.folder), capture_output=True, text=True, errors="replace",
                                   env=self.env(), timeout=20, creationflags=NO_WINDOW)
            except (OSError, subprocess.TimeoutExpired):
                continue
            text = (r.stdout + "\n" + r.stderr).replace(str(path), src).replace(str(path).replace("\\", "/"), src)
            for d in errors.parse(text, self.folder):
                if d.file and Path(d.file).name.lower() == path.name.lower():
                    d.file = src
                out.append(d)
        return out


def read_diagnostics(folder: Path) -> dict:
    """The rows written by the last build ({"ok", "exe", "diags": [...]}), {} when there is none."""
    p = Path(folder) / BUILD_DIR / DIAG_FILE
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    folder = Path(argv[0])
    b = Builder(folder, release="--release" in argv)
    if "--check" in argv:
        for d in b.check():
            print(f"{d.file}:{d.line}: {d.severity.lower()}: {d.message}")
        return 0
    return 0 if b.build() else 1


if __name__ == "__main__":
    sys.exit(main())
