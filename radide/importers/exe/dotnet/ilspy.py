"""Assembly -> C# sources: ilspycmd (the ILSpy command line, a dotnet tool installed into
%LOCALAPPDATA%\\RADIDE\\tools) and the main assembly of a .NET single-file bundle."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from ..base import find_tool, tools_dir
from .common import run_tool, say


ILSPY_VERSIONS = (None, "9.1.0.7988", "8.2.0.7535")   # newest first; 9.x runs on the .NET 8/9 SDKs


# ============================================================================ ilspycmd
def find_ilspycmd() -> str | None:
    return find_tool("ilspycmd")


def install_ilspycmd(progress=None) -> str | None:
    """dotnet tool install --tool-path %LOCALAPPDATA%\\RADIDE\\tools ilspycmd (newest that runs here)."""
    dotnet = shutil.which("dotnet")
    if not dotnet:
        return None
    root = tools_dir()
    root.mkdir(parents=True, exist_ok=True)
    for ver in ILSPY_VERSIONS:
        say(progress, "Installing ilspycmd (ILSpy command line)" + (f" {ver}" if ver else "") + " ...")
        cmd = [dotnet, "tool", "install", "--tool-path", str(root), "ilspycmd"]
        if ver:
            cmd += ["--version", ver]
        rc, out = run_tool(cmd, timeout=600)
        exe = root / ("ilspycmd.exe" if os.name == "nt" else "ilspycmd")
        if exe.exists():
            ok, _o = run_tool([str(exe), "--version"], timeout=120)
            if ok == 0 or "ilspycmd" in _o.lower():
                return str(exe)
            run_tool([dotnet, "tool", "uninstall", "--tool-path", str(root), "ilspycmd"], timeout=300)
    return None


def decompile(assembly: Path, outdir: Path, progress=None) -> tuple[Path | None, str]:
    exe = find_ilspycmd() or install_ilspycmd(progress)
    if not exe:
        return None, ("ilspycmd is not available (needs the .NET SDK: install it from https://dot.net, then "
                      "retry - the importer installs ilspycmd with 'dotnet tool install')")
    outdir.mkdir(parents=True, exist_ok=True)
    say(progress, f"Decompiling {assembly.name} with ILSpy ...")
    rc, out = run_tool([exe, "-p", "-o", str(outdir), str(assembly)], timeout=1800)
    if not any(outdir.rglob("*.cs")):
        rc2, out2 = run_tool([exe, "-o", str(outdir), str(assembly)], timeout=1800)
        out += out2
    if not any(outdir.rglob("*.cs")):
        return None, "ilspycmd produced no C# files:\n" + out[-1500:]
    return outdir, out


def _bundle_extract(path: Path, workdir: Path) -> Path | None:
    """Managed main assembly from a .NET single-file bundle (manifest at the bundle header offset)."""
    import struct
    data = path.read_bytes()
    sig = bytes.fromhex("8b1202b96a612038727b930214d7a03213f5b9e6efae3318ee3b2dce24b36aae")
    i = data.find(sig)
    if i < 8:
        return None
    off = struct.unpack_from("<q", data, i - 8)[0]
    if off <= 0 or off >= len(data):
        return None
    try:
        major, _minor, count = struct.unpack_from("<IIi", data, off)
        p = off + 12

        def read_str(pos):
            n, shift, length = 0, 0, 0
            while True:
                b = data[pos]
                pos += 1
                length |= (b & 0x7F) << shift
                shift += 7
                n += 1
                if not b & 0x80:
                    break
            return data[pos:pos + length].decode("utf-8"), pos + length
        _bid, p = read_str(p)
        if major >= 2:
            p += 8 * 4 + 8      # deps/runtimeconfig offsets+sizes, flags
        out = workdir / "bundle"
        out.mkdir(parents=True, exist_ok=True)
        main = None
        for _ in range(count):
            offset, size = struct.unpack_from("<qq", data, p)
            p += 16
            csize = 0
            if major >= 6:
                csize = struct.unpack_from("<q", data, p)[0]
                p += 8
            ftype = data[p]
            p += 1
            rel, p = read_str(p)
            blob = data[offset:offset + (csize or size)]
            if csize:
                import zlib
                blob = zlib.decompress(blob, -15)
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
            if ftype == 1 and rel.lower() == path.with_suffix(".dll").name.lower():
                main = dest
        return main
    except Exception:  # noqa: BLE001
        return None
