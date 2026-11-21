"""Build a retro game project: ``python -m radide.retro.dev.build <project folder>`` (no Qt in here).

The project's ``project.radproj`` holds an ``extra["retro"]`` block::

    {"system": "nes", "lang": "asm" | "c", "main": "main.s", "cfg": "nes.cfg", "output": "Game.nes",
     "fix": true,                    # Game Boy: run rgbfix (logo, checksums) after linking
     "org": 32768, "entry": "start", # ZX Spectrum: load address + entry label of the .tap
     "original": "rom/Game.nes", "compare": [0, 40976],   # "Disassemble ROM into project": rebuild check
     "prebuild": ["{python} tools/pack.py gfx.chr gfx.bin"]}  # commands run first ({python} = this Python)

Steps:  atari2600  dasm main.asm -f3 -o<out> -l -s
        nes / c64  asm: ca65 every .s -> _build/*.o, ld65 -C <cfg>     c: cl65 -t nes|c64 -O (cc65)
        gameboy    rgbasm every .asm -> _build/*.o, rgblink, rgbfix -v -p 0xFF
        zx         sjasmplus --raw=_build/code.bin main.asm, then a .tap with a BASIC loader (tapfile.py)
Missing toolchains are downloaded from their official releases on the first build (toolchain.py). The rows of
the Error List go to ``_build/diagnostics.json``; the last line says "Build succeeded" / "Build failed".
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from . import errors, toolchain
from .systems import SYSTEMS

BUILD_DIR = "_build"
DIAG_FILE = "diagnostics.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def settings_for(project) -> dict:
    s = dict((getattr(project, "extra", {}) or {}).get("retro") or {})
    if "system" not in s:
        from .systems import PLUGIN_SYSTEM
        s["system"] = PLUGIN_SYSTEM.get(getattr(project, "language", ""), "atari2600")
    sysd = SYSTEMS[s["system"]]
    s.setdefault("lang", "asm")
    s.setdefault("output", f"{project.name}{sysd.rom_ext}")
    if not s.get("main"):
        exts = {"dasm": (".asm",), "ca65": (".s", ".c"), "rgbds": (".asm",), "sjasmplus": (".asm",)}[sysd.dialect]
        mods = [m for m in getattr(project, "modules", []) if Path(m).suffix.lower() in exts]
        s["main"] = mods[0] if mods else ("main.c" if s["lang"] == "c" else "main" + exts[0])
    return s


def read_diagnostics(folder: Path) -> dict | None:
    try:
        return json.loads((Path(folder) / BUILD_DIR / DIAG_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


class Builder:
    def __init__(self, folder: Path, project=None, log=print, download: bool = True):
        from ...model import Project
        self.folder = Path(folder)
        self.project = project or Project.load(self.folder)
        self.s = settings_for(self.project)
        self.system = SYSTEMS[self.s["system"]]
        self.log = log
        self.download = download
        self.output: list[str] = []
        self.diags: list[errors.Diag] = []

    # ------------------------------------------------------------ helpers
    def tool(self, exe: str) -> str:
        path = toolchain.ensure(exe, self.log, self.download)
        if not path:
            raise RuntimeError(toolchain.missing_hint(exe))
        return path

    def run(self, argv: list[str], env: dict | None = None) -> int:
        self.log("> " + " ".join(Path(a).name if i == 0 else a for i, a in enumerate(argv)))
        try:
            r = subprocess.run(argv, cwd=str(self.folder), capture_output=True, env=env, timeout=300,
                               creationflags=NO_WINDOW)
        except (OSError, subprocess.SubprocessError) as e:
            self.output.append(f"error: {e}")
            self.log(f"error: {e}")
            return 1
        text = _decode(r.stdout + b"\n" + r.stderr).replace("\r\n", "\n")
        text = "\n".join(ln for ln in text.splitlines() if ln.strip())
        if text:
            self.log(text)
            self.output.append(text)
        return r.returncode

    def sources(self, exts: tuple[str, ...]) -> list[str]:
        mods = [m for m in getattr(self.project, "modules", []) if Path(m).suffix.lower() in exts]
        main = self.s.get("main")
        if main and main not in mods and Path(main).suffix.lower() in exts and (self.folder / main).is_file():
            mods.insert(0, main)
        if not mods:
            mods = sorted(p.name for p in self.folder.iterdir() if p.suffix.lower() in exts)
        return mods

    @property
    def out_path(self) -> Path:
        return self.folder / self.s["output"]

    # ------------------------------------------------------------ recipes
    def build(self) -> bool:
        (self.folder / BUILD_DIR).mkdir(exist_ok=True)
        ok = False
        try:
            fn = {"atari2600": self._dasm, "nes": self._cc65, "c64": self._cc65, "gameboy": self._rgbds,
                  "zx": self._sjasm}[self.system.id]
            ok = self._prebuild() and fn()
        except RuntimeError as e:
            self.output.append(f"error: {e}")
            self.log(f"error: {e}")
            ok = False
        self.diags = errors.parse("\n".join(self.output), self.folder)
        if not ok and not any(d.severity == "Error" for d in self.diags):
            last = next((ln for ln in reversed("\n".join(self.output).splitlines()) if ln.strip()), "build failed")
            self.diags.append(errors.Diag("Error", last.strip(), "", 0))
        same = None
        if ok and self.s.get("original"):
            same = self.compare()
        (self.folder / BUILD_DIR / DIAG_FILE).write_text(json.dumps(
            {"ok": ok, "output": str(self.out_path) if ok else "", "system": self.system.id,
             "identical": same, "diags": [d.to_dict() for d in self.diags]}, indent=1), encoding="utf-8")
        return ok

    def _prebuild(self) -> bool:
        """``"prebuild"``: commands run in the project folder before assembling (graphics packers, level
        converters ...). Each is a string (split like a shell line) or an argv list; ``{python}`` is this
        Python interpreter. A non-zero exit code stops the build."""
        import shlex
        cmds = self.s.get("prebuild") or []
        for cmd in [cmds] if isinstance(cmds, str) else cmds:
            argv = shlex.split(cmd, posix=os.name != "nt") if isinstance(cmd, str) else [str(a) for a in cmd]
            argv = [a.strip('"') if os.name == "nt" else a for a in argv]
            argv = [sys.executable if a == "{python}" else a for a in argv]
            if argv and self.run(argv) != 0:
                self.output.append(f"error: prebuild step failed: {' '.join(argv)}")
                return False
        return True

    def _dasm(self) -> bool:
        dasm = self.tool("dasm")
        main = self.s["main"]
        stem = Path(main).stem
        argv = [dasm, main, "-f3", f"-o{self.s['output']}", f"-l{BUILD_DIR}/{stem}.lst",
                f"-s{BUILD_DIR}/{stem}.sym", "-v0"]
        for inc in self.s.get("include", []) or []:
            argv.append(f"-I{inc}")
        rc = self.run(argv)
        return rc == 0 and self.out_path.is_file()

    def _cc65_env(self) -> dict:
        env = dict(os.environ)
        home = toolchain.cc65_home()
        if home:
            env["CC65_HOME"] = home
        return env

    def _cc65(self) -> bool:
        target = "nes" if self.system.id == "nes" else "c64"
        env = None
        if self.s["lang"] == "acme":
            acme = self.tool("acme")
            rc = self.run([acme, "-f", "cbm", "-o", self.s["output"], "-r", f"{BUILD_DIR}/report.txt",
                           "--vicelabels", f"{BUILD_DIR}/labels.txt", self.s["main"]])
            return rc == 0 and self.out_path.is_file()
        if self.s["lang"] == "c":
            cl65 = self.tool("cl65")
            env = self._cc65_env()
            srcs = self.sources((".c", ".s"))
            argv = [cl65, "-t", target, "-O", "-g", "-o", self.s["output"], "-m", f"{BUILD_DIR}/map.txt",
                    "-Ln", f"{BUILD_DIR}/labels.txt", "--obj-path", BUILD_DIR]
            if self.s.get("cfg"):
                argv += ["-C", self.s["cfg"]]
            rc = self.run(argv + srcs, env)
            return rc == 0 and self.out_path.is_file()
        ca65 = self.tool("ca65")
        ld65 = self.tool("ld65")
        env = self._cc65_env()
        objs = []
        ok = True
        for src in self.sources((".s", ".asm")):
            obj = f"{BUILD_DIR}/{Path(src).stem}.o"
            rc = self.run([ca65, "--cpu", "6502", "-g", "-I", ".", "-o", obj, src], env)
            ok = ok and rc == 0
            objs.append(obj)
        if not ok:
            return False
        cfg = self.s.get("cfg") or f"{target}.cfg"
        if not (self.folder / cfg).is_file():
            raise RuntimeError(f"linker configuration {cfg} not found in the project folder")
        rc = self.run([ld65, "-C", cfg, "-o", self.s["output"], "-m", f"{BUILD_DIR}/map.txt",
                       "-Ln", f"{BUILD_DIR}/labels.txt", "--dbgfile", f"{BUILD_DIR}/game.dbg"] + objs, env)
        return rc == 0 and self.out_path.is_file()

    def _rgbds(self) -> bool:
        rgbasm, rgblink = self.tool("rgbasm"), self.tool("rgblink")
        objs, ok = [], True
        for src in self.sources((".asm", ".s", ".z80")):
            obj = f"{BUILD_DIR}/{Path(src).stem}.o"
            rc = self.run([rgbasm, "-I", ".", "-o", obj, src])
            ok = ok and rc == 0
            objs.append(obj)
        if not ok:
            return False
        stem = Path(self.s["output"]).stem
        argv = [rgblink, "-o", self.s["output"], "-m", f"{BUILD_DIR}/{stem}.map", "-n", f"{BUILD_DIR}/{stem}.sym"]
        if self.s.get("tiny"):
            argv.append("-t")
        if self.run(argv + objs) != 0:
            return False
        if self.s.get("fix", False):
            fix = [self.tool("rgbfix"), "-v", "-p", "0xFF"]
            if self.s.get("title"):
                fix += ["-t", str(self.s["title"])[:15]]
            if self.s.get("mbc"):
                fix += ["-m", str(self.s["mbc"])]
            if self.run(fix + [self.s["output"]]) != 0:
                return False
        return self.out_path.is_file()

    def _sjasm(self) -> bool:
        sj = self.tool("sjasmplus")
        main = self.s["main"]
        stem = Path(main).stem
        raw = f"{BUILD_DIR}/code.bin"
        rc = self.run([sj, "--nologo", "--msg=war", f"--raw={raw}", f"--sym={BUILD_DIR}/{stem}.sym",
                       f"--lst={BUILD_DIR}/{stem}.lst", "--fullpath=off", main])
        if rc != 0 or not (self.folder / raw).is_file():
            return False
        code = (self.folder / raw).read_bytes()
        org = int(self.s.get("org", 0x8000))
        entry = self.s.get("entry", "")
        addr = org
        if isinstance(entry, int):
            addr = entry
        elif entry:
            syms = self.symbols()
            if entry not in syms:
                self.output.append(f"{main}(1): error: entry label '{entry}' not found (retro.entry in "
                                   f"project.radproj)")
                return False
            addr = syms[entry]
        out = self.out_path
        if out.suffix.lower() == ".tap":
            from .tapfile import make_tap
            out.write_bytes(make_tap(code, org, addr, self.project.name[:10]))
            self.log(f"Wrote {out.name}: BASIC loader + CODE {len(code)} bytes at {org} (entry {addr})")
        else:
            out.write_bytes(code)
        return True

    def symbols(self) -> dict[str, int]:
        """Labels of the last build (sjasmplus .sym / ld65 -Ln / dasm -s / rgblink -n)."""
        out: dict[str, int] = {}
        for p in (self.folder / BUILD_DIR).glob("*.sym"):
            for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.match(r"^([A-Za-z_.@?][\w.@?]*):?\s+(?:EQU|equ|=)?\s*(?:0x|\$)?([0-9A-Fa-f]+)", ln)
                m2 = re.match(r"^([0-9A-Fa-f]{2}):([0-9A-Fa-f]{4})\s+(\S+)", ln)        # rgblink: bank:addr name
                if m2:
                    out[m2.group(3)] = int(m2.group(2), 16)
                elif m:
                    try:
                        out[m.group(1)] = int(m.group(2), 16)
                    except ValueError:
                        pass
        lab = self.folder / BUILD_DIR / "labels.txt"
        if lab.is_file():
            for ln in lab.read_text(encoding="utf-8", errors="replace").splitlines():
                m = re.match(r"^al\s+([0-9A-Fa-f]+)\s+\.(\S+)", ln)
                if m:
                    out[m.group(2)] = int(m.group(1), 16)
        return out

    # ------------------------------------------------------------ rebuild check
    def compare(self) -> dict:
        """Compare the build with the original ROM the project was disassembled from."""
        orig = self.folder / self.s["original"]
        try:
            want = orig.read_bytes()
        except OSError as e:
            return {"same": False, "reason": f"original not found: {e}"}
        start, length = (self.s.get("compare") or [0, len(want)])
        want = want[start:start + length]
        what = self.s.get("compare_what", "output")
        got_path = self.folder / BUILD_DIR / "code.bin" if what == "code" else self.out_path
        got = got_path.read_bytes() if got_path.is_file() else b""
        res = compare_bytes(want, got)
        if res["same"]:
            self.log(f"Rebuild check: byte-identical to {orig.name} ({len(want)} bytes)")
        else:
            self.log(f"Rebuild check: DIFFERENT from {orig.name}: {res['reason']}")
            self.diags.append(errors.Diag("Warning", f"Rebuilt ROM differs from {orig.name}: {res['reason']}", "", 0))
        return res


def _decode(data: bytes) -> str:
    """Tool output: UTF-8 when it is valid, else the Windows ANSI code page (ld65's quotes)."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", "replace")


def compare_bytes(want: bytes, got: bytes) -> dict:
    if want == got:
        return {"same": True, "size": len(want), "reason": ""}
    n = min(len(want), len(got))
    first = next((i for i in range(n) if want[i] != got[i]), n)
    diff = sum(1 for i in range(n) if want[i] != got[i]) + abs(len(want) - len(got))
    reason = f"{diff} byte(s) differ, first at offset ${first:X}" + \
        (f"; size {len(got)} instead of {len(want)}" if len(want) != len(got) else "")
    return {"same": False, "size": len(want), "first": first, "count": diff, "reason": reason}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python -m radide.retro.dev.build <project folder> [--no-download]")
        return 2
    folder = Path(argv[0])
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
    b = Builder(folder, log=lambda t: print(t, flush=True), download="--no-download" not in argv)
    ok = b.build()
    errs = sum(d.severity == "Error" for d in b.diags)
    warns = sum(d.severity == "Warning" for d in b.diags)
    print(f"{'Build succeeded' if ok else 'Build failed'}: {b.out_path.name if ok else ''} "
          f"({errs} errors, {warns} warnings)", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
