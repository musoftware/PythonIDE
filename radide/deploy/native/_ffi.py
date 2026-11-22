"""Shared parts of the native builders that link radforms into programs of other languages
(Rust FFI - rust_native.py, Go cgo - go_native.py, the embedded Lua host - script_embed.py).

radforms (radide/runtimes/native/radforms) is compiled for each build with only the control modules the
project's forms use:

    MinGW   libradforms.a (core + modules) + _radmodules.o (rad_modules_init, linked as an object because
            radforms.c references it weakly and a weak reference does not pull archive members)
    MSVC    radforms.lib (/Zl: links with the static or the dynamic CRT) + _radmodules.obj

The resources (manifest with visual styles / per-monitor DPI / UTF-8 code page, version, icon, the form
description and the images of the forms) are compiled with windres - as a COFF object for MinGW links and
as a .res file for link.exe.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from . import NativeUnsupported
from . import radforms_gen as rg

# Win32 import libraries radforms needs (names without lib / .lib)
WIN_LIBS = ["comctl32", "comdlg32", "gdi32", "ole32", "uuid", "shell32", "user32", "kernel32", "advapi32"]
RF_CFLAGS = ["-std=gnu99", "-c", "-Os", "-ffunction-sections", "-fno-asynchronous-unwind-tables"]
SOURCE_EXT = {".c", ".h", ".rs", ".go", ".lua", ".js", ".ts", ".cjs", ".mjs", ".mod", ".sum", ".toml", ".lock", ".o", ".obj", ".a", ".lib",
              ".exe", ".pdb", ".ilk", ".res", ".rc", ".form", ".radproj", ".radsln", ".iss", ".spec", ".py", ".pyc"}
SKIP_NAMES = {"_build", "target", "Publish", "lua_modules", "node_modules", "_radworker", "vendor", "package.json",
              "package-lock.json", "tsconfig.json"}


def mingw(log=print) -> dict[str, str]:
    """{"cc", "driver", "windres"} of the IDE's MinGW-w64 (WinLibs is downloaded when there is none)."""
    from .win32_c import toolchain
    return toolchain("c-bridge", log)


def tool_env(bindir: str | Path, base: dict | None = None) -> dict:
    from ...paths import ansi_env, ansi_safe
    env = ansi_env(base or os.environ)          # TEMP in an Arabic user folder: gcc "can't create ...?????.o"
    env["PATH"] = ansi_safe(bindir) + os.pathsep + env.get("PATH", "")
    return env


def run(cmd: list[str], cwd: Path, log, env=None) -> int:
    from ..build import run as _run
    return _run(cmd, cwd, log, env=env)


def fresh(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def dist_folder(work: Path, cfg) -> Path:
    return fresh(Path(work) / "dist" / cfg.exe_base())


# ------------------------------------------------------------------ resources
def resources(nat: Path, project, folder: Path, cfg, log, windres: str, fmt: str = "coff",
              rcdata: dict[str, Path] | None = None) -> Path:
    """app.rc (+ forms.radf, images, icon) compiled to app.res.o (fmt "coff") or app.res (fmt "res").
    *rcdata*: more RCDATA resources {resource name: file}."""
    from ..build import BuildError, make_icon
    rc = rg.write_resources(nat, project, folder, cfg, log, gui=True, icon=make_icon(folder, cfg, nat / "icon", log))
    if rcdata:
        lines = []
        for name, path in rcdata.items():
            if Path(path).parent.resolve() != nat.resolve():
                shutil.copy2(path, nat / Path(path).name)
            lines.append(f'{name} RCDATA "{Path(path).name}"')
        rc.write_text(rc.read_text(encoding="utf-8") + "\n".join(lines) + "\n", encoding="utf-8")
    if fmt == "coff":
        return rg.compile_resources(windres, rc, log)
    out = rc.with_name("app.res")
    cmd = [windres, "--input-format=rc", "--output-format=res", "-c", "65001", "-i", rc.name, "-o", out.name]
    log("> " + " ".join(cmd))
    r = subprocess.run(cmd, cwd=str(rc.parent), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=tool_env(Path(windres).parent))
    if r.stdout.strip() or r.stderr.strip():
        log((r.stdout + r.stderr).strip())
    if r.returncode != 0 or not out.is_file():
        raise BuildError("windres failed (see the output above)")
    return out


# ------------------------------------------------------------------ radforms libraries
def _module_sources(project) -> list[Path]:
    return rg.modules_for(rg.project_types(project))


def mingw_radforms(nat: Path, project, tc: dict, log) -> tuple[Path, list[Path]]:
    """(folder with libradforms.a + radforms.h, [_radmodules.o]) for this project's forms."""
    from ..build import BuildError
    out = fresh(nat / "radforms")
    env = tool_env(Path(tc["cc"]).parent)
    mods = _module_sources(project)
    objs = []
    for src in [rg.RADFORMS_C, *mods]:
        o = out / (Path(src).stem + ".o")
        if run([tc["cc"], *RF_CFLAGS, "-I", str(rg.RADFORMS_DIR), str(src), "-o", str(o)], out, log, env) != 0:
            raise BuildError(f"{Path(src).name} did not compile (see the output above)")
        objs.append(str(o))
    ar = str(Path(tc["cc"]).with_name("ar.exe" if tc["cc"].lower().endswith(".exe") else "ar"))
    lib = out / "libradforms.a"
    if run([ar, "rcs", str(lib), *objs], out, log, env) != 0:
        raise BuildError("ar failed (see the output above)")
    (out / "_radmodules.c").write_text(rg.modules_source(mods), encoding="utf-8")
    mo = out / "_radmodules.o"
    if run([tc["cc"], *RF_CFLAGS, "-I", str(rg.RADFORMS_DIR), str(out / "_radmodules.c"), "-o", str(mo)], out, log,
           env) != 0:
        raise BuildError("_radmodules.c did not compile (see the output above)")
    shutil.copy2(rg.RADFORMS_H, out / "radforms.h")
    return out, [mo]


def msvc_radforms(nat: Path, project, log) -> tuple[Path, list[Path]] | None:
    """(folder with radforms.lib, [_radmodules.obj]) compiled by cl /Zl, or None without Visual C++."""
    from ...languages.c_bridge import VS_INSTALLER, find_vcvars
    vcvars = find_vcvars()
    if not vcvars:
        return None
    out = fresh(nat / "radforms_msvc")
    mods = _module_sources(project)
    (out / "_radmodules.c").write_text(rg.modules_source(mods), encoding="utf-8")
    srcs = " ".join(f'"{s}"' for s in [rg.RADFORMS_C, *mods])
    objs = " ".join(f'"{Path(s).stem}.obj"' for s in [rg.RADFORMS_C, *mods])
    bat = out / "build.bat"
    bat.write_text(f'@echo off\r\nset "PATH={VS_INSTALLER};%PATH%"\r\ncall "{vcvars}" >nul\r\n'
                   f'cl /nologo /c /O1 /Gy /GS- /Zl /utf-8 /TC /W1 /I "{rg.RADFORMS_DIR}" {srcs} _radmodules.c\r\n'
                   f'if errorlevel 1 exit /b 1\r\nlib /nologo /OUT:radforms.lib {objs}\r\n', encoding="utf-8")
    log(f"> cl /O1 /Gy /Zl radforms.c (+{len(mods)} control modules) & lib radforms.lib")
    r = subprocess.run(["cmd", "/c", str(bat)], cwd=str(out), capture_output=True, text=True, errors="replace")
    if r.returncode != 0 or not (out / "radforms.lib").is_file():
        log("MSVC build of radforms.lib failed:\n" + (r.stdout + r.stderr).strip()[-2000:])
        return None
    return out, [out / "_radmodules.obj"]


def _short_path(p: Path) -> str:
    if os.name != "nt":
        return str(p)
    import ctypes
    buf = ctypes.create_unicode_buffer(1024)
    n = ctypes.windll.kernel32.GetShortPathNameW(str(p), buf, 1024)
    return buf.value if 0 < n < 1024 else str(p)


def nomanifest_dir(nat: Path) -> Path:
    """Where the empty default-manifest.o goes: a folder WITHOUT spaces in its path (gcc passes the file
    found through -B to ld unquoted, so "RAD IDE Projects" would break the link)."""
    from ...languages.bridgebase import toolchains_root
    for cand in (nat / "nomanifest", toolchains_root() / "_nomanifest"):
        if " " not in str(cand):
            return cand
    d = nat / "nomanifest"
    d.mkdir(parents=True, exist_ok=True)
    return Path(_short_path(d))


def no_default_manifest(nat: Path, cc: str, log) -> Path:
    """A folder with an empty default-manifest.o: given to gcc with -B it replaces MinGW's (asInvoker, no
    visual styles), so the manifest of our resources is the only one."""
    from ..build import BuildError
    d = nomanifest_dir(nat)
    d.mkdir(parents=True, exist_ok=True)
    if " " in str(d):
        raise NativeUnsupported(f"no folder without spaces for the MinGW manifest object ({d})")
    (d / "empty.c").write_text("/* replaces MinGW's default-manifest.o */\n", encoding="utf-8")
    if run([cc, "-c", str(d / "empty.c"), "-o", str(d / "default-manifest.o")], d, log,
           tool_env(Path(cc).parent)) != 0:
        raise BuildError("gcc does not work (see the output above)")
    return d


# ------------------------------------------------------------------ checks
def literal_api_reasons(texts: dict[str, str], set_rx: str, call_rx: str) -> list[str]:
    """Properties / methods used with literal names that radforms does not implement.
    *set_rx* / *call_rx*: regexes with two groups (object, property / method)."""
    out, seen = [], set()
    for fname, text in texts.items():
        for obj, prop in re.findall(set_rx, text):
            if prop.lower() not in rg.SUPPORTED_PROPS and (fname, prop.lower()) not in seen:
                seen.add((fname, prop.lower()))
                out.append(f"{fname}: property '{prop}' ({obj}) is not supported by the native runtime")
        for obj, meth in re.findall(call_rx, text):
            if meth.lower() not in rg.SUPPORTED_METHODS and (fname, meth.lower()) not in seen:
                seen.add((fname, meth.lower()))
                out.append(f"{fname}: method '{meth}' ({obj}) is not supported by the native runtime")
    return out


def strip_c_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def common_reasons(folder: Path, project, lang: str) -> list[str]:
    reasons = []
    if not project.forms:
        reasons.append("the project has no form (console programs keep the normal build)")
    reasons += rg.unsupported(project, Path(folder), lang)
    return reasons


# ------------------------------------------------------------------ result
def copy_data(folder: Path, cfg, dist: Path, skip_ext=SOURCE_EXT):
    from ..build import data_entries
    for p in data_entries(folder, cfg, skip_ext=skip_ext):
        if p.name.lower().startswith(("_rad", "radgui", "radlib", "radmain_gen")) or p.name in SKIP_NAMES:
            continue
        if p.is_dir():
            shutil.copytree(p, dist / p.name, dirs_exist_ok=True)
        else:
            shutil.copy2(p, dist / p.name)


def finish(exe: Path, dist: Path, folder: Path, cfg, log, notes: list[str], what: str):
    from ..build import BuildError, BuildResult
    if not exe.is_file():
        raise BuildError(f"{exe.name} was not created")
    copy_data(folder, cfg, dist)
    size = exe.stat().st_size
    log(f"Native exe: {exe.name} {size // 1024} KB ({size:,} bytes) - no Python, no extra DLLs")
    log(f"({what})")
    return BuildResult(dist, exe.name, "native", notes)


def update_note(cfg, log) -> list[str]:
    if cfg.update.enabled and cfg.update.url:
        log("Note: the update check (Python) is not included in a native exe")
        return ["The automatic update check is not part of native builds."]
    return []


__all__ = ["NativeUnsupported", "WIN_LIBS", "common_reasons", "copy_data", "dist_folder", "finish", "fresh",
           "literal_api_reasons", "mingw", "mingw_radforms", "msvc_radforms", "resources", "run", "tool_env"]
