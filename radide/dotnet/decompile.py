"""Decompiler for .NET assemblies (ILSpy's command line, ``ilspycmd``) - Go To Definition into metadata,
the Object Browser's "Go To Definition" (radide/dotnet/refs) and the decompiled read-only tabs.

    decompile_to_text(assembly, type_name=None) -> str    C# source of one type (or the whole assembly)
    find_ilspycmd() / ensure_ilspycmd(log)                the tool, installed on request from nuget.org
                                                          (``dotnet tool install --tool-path``
                                                          %LOCALAPPDATA%\\RADIDE\\tools - no admin, portable)
    decompiled_file(assembly, type_name) -> Path          the same text cached as a .cs file to open read-only

Raises DecompileError with a readable message (tool missing, type not found ...)."""
from __future__ import annotations

import re
from pathlib import Path

from .tools import sdk


class DecompileError(RuntimeError):
    pass


def find_ilspycmd() -> str:
    try:
        from ..importers.exe.dotnet import find_ilspycmd as _find
        hit = _find()
        if hit:
            return str(hit)
    except Exception:  # noqa: BLE001 - the importer may be unavailable in a trimmed build
        pass
    import shutil
    p = shutil.which("ilspycmd")
    if p:
        return p
    cand = sdk.tools_dir() / "ilspycmd.exe"
    return str(cand) if cand.is_file() else ""


def ensure_ilspycmd(log=None) -> str:
    """The ilspycmd executable, installing it from nuget.org when missing (only call after the user asked)."""
    exe = find_ilspycmd()
    if exe:
        return exe
    try:
        from ..importers.exe.dotnet import install_ilspycmd
        exe = install_ilspycmd(log)
    except Exception:  # noqa: BLE001
        exe = None
    if not exe:
        dn = sdk.dotnet()
        if not dn:
            raise DecompileError("ilspycmd needs the .NET SDK (https://dot.net) - it is installed with "
                                 "'dotnet tool install ilspycmd'")
        code, out = sdk.run([dn, "tool", "install", "--tool-path", str(sdk.tools_dir()), "ilspycmd"], timeout=900)
        exe = find_ilspycmd()
        if not exe:
            raise DecompileError("could not install ilspycmd:\n" + out[-1200:])
    return exe


def _clean_type(type_name: str) -> str:
    """'List<T>' / 'System.Collections.Generic.List<int>' -> 'System.Collections.Generic.List`1'."""
    t = type_name.strip()
    m = re.match(r"^([\w.+]+)<(.+)>$", t)
    if m:
        depth, n = 0, 1
        for ch in m.group(2):
            if ch == "<":
                depth += 1
            elif ch == ">":
                depth -= 1
            elif ch == "," and depth == 0:
                n += 1
        t = f"{m.group(1)}`{n}"
    return t


def decompile_to_text(assembly, type_name: str | None = None, timeout: int = 300, install: bool = True,
                      log=None) -> str:
    """C# source of *type_name* (full name, e.g. ``System.Text.StringBuilder`` or ``...List`1``) in
    *assembly*, or of the whole assembly when *type_name* is None."""
    asm = Path(assembly)
    if not asm.is_file():
        raise DecompileError(f"assembly not found: {asm}")
    exe = ensure_ilspycmd(log) if install else find_ilspycmd()
    if not exe:
        raise DecompileError("ilspycmd is not installed")
    argv = [exe, str(asm)]
    if type_name:
        argv[1:1] = ["-t", _clean_type(type_name)]
    code, out = sdk.run(argv, timeout=timeout)
    out = "\n".join(ln for ln in out.split("\n") if not ln.startswith(("You are not using the latest version",
                                                                       "Latest version is '")))
    text = out.strip()
    if code != 0 or not text or text.startswith(("ERROR", "Unhandled exception")):
        raise DecompileError(f"ilspycmd could not decompile {type_name or asm.name}:\n{out[-1500:]}")
    if type_name and "TypeNotFound" in text[:300]:
        raise DecompileError(f"{type_name} is not defined in {asm.name}")
    return out


def header(assembly, type_name: str | None) -> str:
    asm = Path(assembly)
    ver = ""
    try:
        from .refs.metadata import assembly_identity
        ident = assembly_identity(asm)
        ver = f", Version={ident.get('version', '')}" if ident.get("version") else ""
    except Exception:  # noqa: BLE001
        pass
    return ("#region Assembly " + asm.stem + ver + "\n// " + str(asm) + "\n"
            "// Decompiled with ICSharpCode.Decompiler (ilspycmd) - read-only\n#endregion\n\n")


def decompiled_file(assembly, type_name: str | None = None, log=None) -> Path:
    """Decompile into %LOCALAPPDATA%\\RADIDE\\cache\\decompiled\\<asm>-<hash>\\<Type>.cs (re-used while the
    assembly does not change) and return the path."""
    asm = Path(assembly)
    st = asm.stat()
    folder = sdk.cache_dir("decompiled", f"{asm.stem}-{sdk.short_hash(f'{asm}|{st.st_size}|{int(st.st_mtime)}')}")
    name = re.sub(r"[^\w.`-]", "_", _clean_type(type_name)) if type_name else asm.stem
    f = folder / f"{name}.cs"
    if not f.is_file() or f.stat().st_size == 0:
        text = decompile_to_text(asm, type_name, log=log)
        f.write_text(header(asm, type_name) + text, encoding="utf-8")
    return f


__all__ = ["decompile_to_text", "decompiled_file", "find_ilspycmd", "ensure_ilspycmd", "DecompileError"]
