"""Assemblers and linkers for the Assembly projects (no Qt in here).

Where each tool is looked up (first hit wins):

    nasm      PATH, %LOCALAPPDATA%\\RADIDE\\tools\\nasm\\nasm.exe, C:\\Program Files\\NASM, %LOCALAPPDATA%\\bin\\NASM
              -> downloaded on demand from https://www.nasm.us (official win64 zip)
    fasm      PATH, %LOCALAPPDATA%\\RADIDE\\tools\\fasm\\FASM.EXE (+ INCLUDE\\ for the Win32/Win64 macros)
              -> downloaded on demand from https://flatassembler.net (official Windows package)
    as / ld / gcc / gdb / objcopy / objdump   the MinGW-w64 toolchain of the C support (c_bridge.find_native):
              PATH, %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64\\bin (WinLibs), MSYS2, ...
    ml / ml64 only when a Visual Studio with the C++ tools is installed (vswhere); never downloaded
    golink    optional: PATH or %LOCALAPPDATA%\\RADIDE\\tools\\golink\\GoLink.exe (https://www.godevtool.com)

Neither nasm.us nor flatassembler.net nor godevtool.com publish checksums, so the archives are pinned to the
SHA-256 measured when this version of RAD IDE was written (a changed file is refused and the user is sent to
the official download page). Everything is portable: no admin rights, no installer, no PATH change.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "RADIDE"


def tools_root() -> Path:
    return local_root() / "tools"


@dataclass(frozen=True)
class Release:
    tool: str            # "nasm" | "fasm" | "golink"
    version: str
    url: str
    sha256: str
    page: str            # official download page (shown when the download fails)
    strip: str = ""      # leading folder inside the zip that is removed when extracting


RELEASES = {
    "nasm": Release("nasm", "3.02", "https://www.nasm.us/pub/nasm/releasebuilds/3.02/win64/nasm-3.02-win64.zip",
                    "161d0bfaff53c2f9e9f3e69fd0672323ebabafd1268976a5cec11be92a19aee7",
                    "https://www.nasm.us/pub/nasm/releasebuilds/", strip="nasm-3.02/"),
    "fasm": Release("fasm", "1.73.35", "https://flatassembler.net/fasmw17335.zip",
                    "8ef871b369638f63d2df475a64e9f574da06b601db5a3fcb8c12654b7bcf5e81",
                    "https://flatassembler.net/download.php"),
    "golink": Release("golink", "1.0", "https://www.godevtool.com/Golink.zip",
                      "f0f682c5fc55217f5b93922475910840f5dcd8467f7891df12d7856554c3d160",
                      "https://www.godevtool.com/"),
}

TOOL_TITLES = {"nasm": "NASM (Netwide Assembler)", "fasm": "FASM (flat assembler)", "as": "GNU as (binutils)",
               "gcc": "gcc (MinGW-w64, linker driver)", "ld": "GNU ld (MinGW-w64)", "gdb": "gdb (MinGW-w64)",
               "objcopy": "objcopy (MinGW-w64)", "ml64": "MASM ml64 (Visual Studio)", "ml": "MASM ml (Visual Studio)",
               "golink": "GoLink (optional linker)"}


# ====================================================================== lookup
def _which(*names: str) -> str:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    return ""


def _first(*paths) -> str:
    for p in paths:
        if p and Path(p).is_file():
            return str(p)
    return ""


def mingw(name: str) -> str:
    """gcc / as / ld / gdb / objcopy / objdump of the MinGW-w64 toolchain used by the C support."""
    from ..languages.c_bridge import find_native
    return find_native([name])


def find_nasm() -> str:
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    return _which("nasm") or _first(tools_root() / "nasm" / f"nasm{EXE}", Path(pf) / "NASM" / f"nasm{EXE}",
                                    Path(os.environ.get("LOCALAPPDATA", "")) / "bin" / "NASM" / f"nasm{EXE}"
                                    if os.environ.get("LOCALAPPDATA") else "")


def fasm_dir() -> Path:
    return tools_root() / "fasm"


def find_fasm() -> str:
    return _which("fasm") or _first(fasm_dir() / "FASM.EXE", fasm_dir() / f"fasm{EXE}")


def fasm_include() -> str:
    """The INCLUDE folder of FASM (win32a.inc / win64a.inc), for the INCLUDE environment variable."""
    exe = find_fasm()
    for d in ([Path(exe).parent / "INCLUDE", Path(exe).parent / "include"] if exe else []) + [fasm_dir() / "INCLUDE"]:
        if d.is_dir():
            return str(d)
    return ""


def find_golink() -> str:
    return _which("golink") or _first(tools_root() / "golink" / "GoLink.exe")


_ML: dict[str, str] = {}


def find_masm(arch: str = "x64") -> str:
    """ml64.exe (x64) or ml.exe (x86) of the newest Visual Studio with the C++ tools, or "" (never downloaded)."""
    key = "ml64" if arch == "x64" else "ml"
    if key in _ML:
        return _ML[key]
    found = _which(f"{key}")
    if not found and os.name == "nt":
        from ..languages.c_bridge import find_vcvars
        bat = find_vcvars()
        if bat:
            vc = Path(bat).parents[2]                     # ...\VC\Auxiliary\Build\vcvars64.bat -> ...\VC
            host = "Hostx64"
            sub = "x64" if arch == "x64" else "x86"
            cands = sorted(vc.glob(f"Tools/MSVC/*/bin/{host}/{sub}/{key}.exe"), reverse=True)
            found = str(cands[0]) if cands else ""
    _ML[key] = found
    return found


def find(tool: str, arch: str = "x64") -> str:
    """Path of *tool* ("nasm", "fasm", "as", "gcc", "ld", "gdb", "objcopy", "ml64", "ml", "golink") or ""."""
    if tool == "nasm":
        return find_nasm()
    if tool == "fasm":
        return find_fasm()
    if tool == "golink":
        return find_golink()
    if tool in ("ml", "ml64"):
        return find_masm("x64" if tool == "ml64" else "x86")
    return mingw(tool)


def version(tool: str) -> str:
    """First line of ``<tool> --version`` (or -v), "" when the tool is missing / does not answer."""
    exe = find(tool)
    if not exe:
        return ""
    if tool == "fasm":
        args = [exe]
    elif tool in ("ml", "ml64"):
        args = [exe, "/?"]
    elif tool == "nasm":
        args = [exe, "-v"]
    elif tool == "golink":
        return "GoLink"
    else:
        args = [exe, "--version"]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=15, creationflags=NO_WINDOW,
                           errors="replace")
    except (OSError, subprocess.SubprocessError):
        return ""
    for line in (r.stdout + "\n" + r.stderr).splitlines():
        if line.strip():
            return line.strip()
    return ""


def status() -> list[tuple[str, str, str]]:
    """(tool, title, path or "") of every tool the Assembly projects can use."""
    return [(t, TOOL_TITLES[t], find(t)) for t in ("nasm", "fasm", "as", "gcc", "ld", "gdb", "objcopy",
                                                   "ml64", "ml", "golink")]


def missing_hint(tool: str) -> str:
    if tool in ("nasm", "fasm", "golink"):
        rel = RELEASES[tool]
        return (f"{TOOL_TITLES[tool]} was not found. RAD IDE downloads it automatically into "
                f"{tools_root() / tool} (official {rel.url}); or download it yourself from {rel.page}.")
    if tool in ("ml", "ml64"):
        return ("MASM (ml.exe / ml64.exe) comes with Visual Studio: install the 'Desktop development with C++' "
                "workload. RAD IDE does not download it.")
    return ("The MinGW-w64 toolchain (gcc, as, ld, gdb) was not found. Install WinLibs into "
            "%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64 (the same toolchain as the C / C++ projects).")


# ====================================================================== download
def download_verified(url: str, sha256: str, dest: Path, log=print) -> bool:
    """Download *url* to *dest*; the file is deleted when its SHA-256 differs from *sha256*."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                f.write(chunk)
    except OSError as e:
        dest.unlink(missing_ok=True)
        log(f"Download failed: {e}")
        return False
    if h.hexdigest().lower() != sha256.lower():
        dest.unlink(missing_ok=True)
        log(f"SHA-256 mismatch for {url} (got {h.hexdigest()}) - the file was removed")
        return False
    log(f"SHA-256 OK ({sha256[:16]}...)")
    return True


def install(tool: str, log=print) -> bool:
    """Download and unpack *tool* ("nasm", "fasm" or "golink") into %LOCALAPPDATA%\\RADIDE\\tools\\<tool>.
    Blocking: run it in a thread from the UI. Returns True when the tool can be found afterwards."""
    rel = RELEASES.get(tool)
    if rel is None:
        log(missing_hint(tool))
        return False
    tmp = tools_root() / "_download" / Path(rel.url).name
    if not download_verified(rel.url, rel.sha256, tmp, log):
        log(f"Download {TOOL_TITLES[tool]} yourself from {rel.page} and put it into {tools_root() / tool}")
        return False
    target = tools_root() / tool
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(tmp) as z:
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts or ":" in name:
                log(f"unsafe path in the archive: {name}")
                return False
            if rel.strip and name.startswith(rel.strip):
                name = name[len(rel.strip):]
            if not name or name.endswith("/"):
                continue
            out = target / name
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
    tmp.unlink(missing_ok=True)
    (target / "RADIDE-SOURCE.json").write_text(json.dumps({"tool": tool, "version": rel.version, "url": rel.url,
                                                           "sha256": rel.sha256}, indent=1), encoding="utf-8")
    ok = bool(find(tool))
    log(f"Installed {TOOL_TITLES[tool]} {rel.version} into {target}" if ok else f"{tool} still not found in {target}")
    return ok


def ensure(tool: str, log=print, download: bool = True) -> str:
    """Path of *tool*; NASM / FASM / GoLink are downloaded when missing (and *download*). "" = not available."""
    exe = find(tool)
    if exe or not download or tool not in RELEASES:
        return exe
    log(f"{TOOL_TITLES[tool]} is missing - downloading the official portable build (one time only)")
    return find(tool) if install(tool, log) else ""


__all__ = ["RELEASES", "TOOL_TITLES", "download_verified", "ensure", "fasm_include", "find", "find_fasm",
           "find_golink", "find_masm", "find_nasm", "install", "mingw", "missing_hint", "status", "tools_root",
           "version"]
