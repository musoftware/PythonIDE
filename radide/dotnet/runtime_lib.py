"""RadIDE.Runtime.dll: the RAD IDE WinForms runtime as a class library (no Qt).

The source is radide/deploy/native/dotnet/RadWinForms.cs (the native publish compiles the same file into the exe);
the project is radide/runtimes/dotnet/RadIDE.Runtime/RadIDE.Runtime.csproj. It is built once per source version
into %LOCALAPPDATA%\\RADIDE\\runtime\\<hash>\\<tfm>\\RadIDE.Runtime.dll and referenced from there by:

* RAD C# projects in native mode (radide/languages/csharp_bridge.py: _build/csharp/RadApp.csproj is a WinExe that
  references the dll; F5 runs a real WinForms exe - radide/dotnet/native_run.py);
* any other C# project: ``reference_xml()`` is the <Reference> element to paste into a .csproj, ``export()``
  copies the dll (+ .xml docs, + .pdb) into a folder of the user's choice.

    python -m radide.dotnet.runtime_lib [net8.0-windows|net48] [--copy <folder>]
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deploy" / "native" / "dotnet" / "RadWinForms.cs"
PROJECT = ROOT / "runtimes" / "dotnet" / "RadIDE.Runtime" / "RadIDE.Runtime.csproj"
NAME = "RadIDE.Runtime"
DEFAULT_TFM = "net8.0-windows"
TFMS = ("net8.0-windows", "net48")
LOCAL = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE" / "runtime"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def version() -> str:
    """Short hash of the runtime source + project: a new source builds into a new folder."""
    h = hashlib.sha1()
    for p in (SOURCE, PROJECT):
        h.update(p.read_bytes())
    return h.hexdigest()[:10]


def out_dir(tfm: str = DEFAULT_TFM) -> Path:
    return LOCAL / version() / tfm


def dll_path(tfm: str = DEFAULT_TFM) -> Path:
    return out_dir(tfm) / f"{NAME}.dll"


def is_built(tfm: str = DEFAULT_TFM) -> bool:
    return dll_path(tfm).is_file()


def _dotnet() -> str:
    from ..languages.csharp_bridge import dotnet
    return dotnet()


def build(tfm: str = DEFAULT_TFM, log=None, force: bool = False) -> Path | None:
    """Build RadIDE.Runtime.dll for *tfm* if needed; returns its path (None on failure, the reason is logged)."""
    log = log or (lambda s: print(s, file=sys.stderr, flush=True))
    if tfm not in TFMS:
        log(f"RadIDE.Runtime: unknown target framework '{tfm}' (use {' or '.join(TFMS)})")
        return None
    dll = dll_path(tfm)
    if dll.is_file() and not force:
        return dll
    dn = _dotnet()
    if not dn:
        log("RadIDE.Runtime: the .NET SDK was not found (winget install Microsoft.DotNet.SDK.9)")
        return None
    work = LOCAL / version() / "src"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    # the csproj links ..\..\..\deploy\native\dotnet\RadWinForms.cs: same layout under src/
    src_dir = work / "deploy" / "native" / "dotnet"
    src_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, src_dir / SOURCE.name)
    proj_dir = work / "runtimes" / "dotnet" / NAME
    proj_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT, proj_dir / PROJECT.name)
    log(f"RadIDE.Runtime: building {NAME}.dll ({tfm}) ...")
    env = dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1", DOTNET_SKIP_FIRST_TIME_EXPERIENCE="1")
    out = out_dir(tfm)
    r = subprocess.run([dn, "build", str(proj_dir / PROJECT.name), "-c", "Release", "-nologo", "-v", "q",
                        "-clp:NoSummary", f"-p:RadIDERuntimeTargets={tfm}", "-o", str(out)],
                       cwd=str(proj_dir), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, creationflags=NO_WINDOW)
    if r.returncode != 0 or not dll.is_file():
        lines = [ln for ln in (r.stdout + r.stderr).splitlines()
                 if ln.strip() and not ln.startswith("Workload updates are available")]
        log("RadIDE.Runtime: build failed\n" + "\n".join(lines[-20:]))
        return None
    log(f"RadIDE.Runtime: {dll}")
    return dll


def reference_xml(tfm: str = DEFAULT_TFM) -> str:
    """The <Reference> element a .csproj uses to compile against the runtime."""
    return (f'<Reference Include="{NAME}"><HintPath>{dll_path(tfm)}</HintPath>'
            f'<Private>true</Private></Reference>')


def export(dest: Path, tfm: str = DEFAULT_TFM, log=None) -> Path | None:
    """Build (if needed) and copy RadIDE.Runtime.dll / .xml / .pdb into *dest* (for any C# project)."""
    dll = build(tfm, log)
    if dll is None:
        return None
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for ext in (".dll", ".xml", ".pdb"):
        p = dll.with_suffix(ext)
        if p.is_file():
            shutil.copy2(p, dest / p.name)
    return dest / dll.name


def main(argv: list[str]) -> int:
    tfm = next((a for a in argv if a in TFMS), DEFAULT_TFM)
    if "--copy" in argv:
        i = argv.index("--copy") + 1
        if i >= len(argv):
            print("--copy needs a folder", file=sys.stderr)
            return 2
        p = export(Path(argv[i]), tfm)
    else:
        p = build(tfm, force="--force" in argv)
    if p is None:
        return 1
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
