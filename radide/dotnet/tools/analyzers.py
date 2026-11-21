"""Dependencies > Analyzers (Visual Studio 2022): the analyzer assemblies a project uses (from the .NET SDK,
the targeting packs and NuGet packages), the rules each one reports with their default and effective severity,
and the source generators with the files they generate.

* list_analyzers(project)      [{"path", "name", "package", "source"}] (``dotnet msbuild -getItem:Analyzer``)
* describe(paths)              {path: {"rules": [...], "generators": [...], "error"}} via the AnalyzerInfo helper
                               (radide/dotnet/tools/helpers/AnalyzerInfo, compiled once against the SDK's own
                               Roslyn - no NuGet download) - cached per assembly
* generated_files(project)     {generator assembly: {generator type: [files]}} from obj/**/generated
* emit_generated(project)      build with EmitCompilerGeneratedFiles=true so the generated files are written
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from . import sdk

HELPER_SRC = Path(__file__).resolve().parent / "helpers" / "AnalyzerInfo"


def list_analyzers(project: Path, timeout: int = 240) -> tuple[list[dict], str]:
    """(analyzers, error text). Package analyzers need a restored project (obj/project.assets.json)."""
    project = Path(project)
    d = sdk.msbuild_eval(project, items=["Analyzer"],
                         targets=["ResolveTargetingPackAssets", "ResolveLockFileAnalyzers"], timeout=timeout)
    err = ""
    if not d:
        d = sdk.msbuild_eval(project, items=["Analyzer"], timeout=timeout)       # evaluation only (SDK analyzers)
        err = "package analyzers need a restore (dotnet restore)" if d else "MSBuild could not evaluate the project"
    out, seen = [], set()
    for it in (d.get("Items") or {}).get("Analyzer", []):
        p = it.get("FullPath") or it.get("Identity", "")
        if not p:
            continue
        p = os.path.normpath(p)
        if p.lower() in seen:
            continue
        seen.add(p.lower())
        pkg = it.get("NuGetPackageId", "")
        src = ("package" if pkg and "App.Ref" not in pkg else "framework" if pkg else
               "sdk" if "dotnet" in p.lower() and "sdk" in p.lower() else "project")
        out.append({"path": p, "name": Path(p).stem, "package": pkg, "version": it.get("NuGetPackageVersion", ""),
                    "source": src})
    return out, err


# ---------------------------------------------------------------- helper
def helper_exe(build: bool = True, log=None) -> str:
    """AnalyzerInfo.exe for the active SDK (built on first use into the IDE cache)."""
    ver = sdk.sdk_version()
    if not ver:
        return ""
    out = sdk.cache_dir("dotnet-tools", f"AnalyzerInfo-{ver}-h2")
    exe = out / "bin" / ("AnalyzerInfo.exe" if os.name == "nt" else "AnalyzerInfo")
    if exe.is_file():
        return str(exe)
    if not build:
        return ""
    folder = sdk.sdk_folder()
    roslyn = folder / "Roslyn" / "bincore" if folder else None
    if roslyn is None or not (roslyn / "Microsoft.CodeAnalysis.dll").is_file():
        return ""
    src = out / "src"
    src.mkdir(parents=True, exist_ok=True)
    for f in ("AnalyzerInfo.csproj", "Program.cs", "Usings.cs"):
        shutil.copy2(HELPER_SRC / f, src / f)
    tfm = "net" + ".".join(ver.split(".")[:1]) + ".0"
    if log:
        log(f"Building the analyzer reader (once, for .NET SDK {ver}) ...")
    code, text = sdk.run([sdk.dotnet(), "build", str(src / "AnalyzerInfo.csproj"), "-c", "Release", "-nologo",
                          f"-p:RadTfm={tfm}", f"-p:RadRoslyn={roslyn}", "-o", str(out / "bin")], cwd=src, timeout=600)
    if code != 0 or not exe.is_file():
        if log:
            log("*** could not build the analyzer reader:\n" + text[-1500:])
        return ""
    return str(exe)


def describe(paths: list[str], log=None) -> dict[str, dict]:
    """Rules and generators of analyzer assemblies (cached per file size + time)."""
    out: dict[str, dict] = {}
    todo = []
    cache = sdk.cache_dir("dotnet-analyzers")
    keys = {}
    for p in paths:
        try:
            st = os.stat(p)
        except OSError:
            out[p] = {"rules": [], "generators": [], "error": "file not found"}
            continue
        k = sdk.short_hash(f"{p}|{st.st_size}|{int(st.st_mtime)}|v1")
        keys[p] = cache / f"{k}.json"
        if keys[p].is_file():
            try:
                out[p] = json.loads(keys[p].read_text(encoding="utf-8"))
                continue
            except (OSError, ValueError):
                pass
        todo.append(p)
    if todo:
        exe = helper_exe(log=log)
        if not exe:
            for p in todo:
                out[p] = {"rules": [], "generators": [], "error": "the analyzer reader is not available "
                                                                   "(needs the .NET SDK 8 or newer)"}
            return out
        for i in range(0, len(todo), 40):                       # keep the command line short
            chunk = todo[i:i + 40]
            code, text = sdk.run([exe, *chunk], timeout=300)
            j = text.find("[")
            try:
                data = json.loads(text[j:text.rfind("]") + 1]) if j >= 0 else []
            except ValueError:
                data = []
            got = {os.path.normcase(d.get("path", "")): d for d in data}
            for p in chunk:
                d = got.get(os.path.normcase(p)) or {"rules": [], "generators": [],
                                                     "error": (text.strip().splitlines() or ["no output"])[-1][:300]}
                d.setdefault("rules", [])
                d.setdefault("generators", [])
                out[p] = d
                if not d.get("error") and p in keys:
                    try:
                        keys[p].write_text(json.dumps(d), encoding="utf-8")
                    except OSError:
                        pass
    return out


# ---------------------------------------------------------------- source generators
def generated_roots(project: Path) -> list[Path]:
    """obj/<Configuration>/<TargetFramework>/generated folders (newest first)."""
    obj = Path(project).parent / "obj"
    if not obj.is_dir():
        return []
    roots = [p for p in obj.glob("*/*/generated") if p.is_dir()] + [p for p in obj.glob("*/generated") if p.is_dir()]
    return sorted(roots, key=lambda p: p.stat().st_mtime, reverse=True)


def generated_files(project: Path) -> dict[str, dict[str, list[Path]]]:
    """{generator assembly: {generator type: [files]}} written by the last build with EmitCompilerGeneratedFiles."""
    roots = generated_roots(project)
    out: dict[str, dict[str, list[Path]]] = {}
    if not roots:
        return out
    root = roots[0]
    for asm in sorted(p for p in root.iterdir() if p.is_dir()):
        for gen in sorted(p for p in asm.iterdir() if p.is_dir()):
            files = sorted(f for f in gen.rglob("*") if f.is_file())
            if files:
                out.setdefault(asm.name, {})[gen.name] = files
    return out


def emit_generated_argv(project: Path, configuration: str = "Debug") -> list[str]:
    """``dotnet build`` that writes the generated sources to obj/<cfg>/<tf>/generated (the project file is not
    changed; Visual Studio shows them from memory, RAD IDE reads them from there)."""
    return [sdk.dotnet() or "dotnet", "build", str(project), "-c", configuration, "-nologo", "-v:m",
            "--no-incremental", "-p:EmitCompilerGeneratedFiles=true"]


def project_analyzers(project: Path, log=None) -> dict:
    """Everything the Analyzers node needs, in one call (slow: MSBuild + the helper; run it in a thread)."""
    items, err = list_analyzers(project)
    info = describe([a["path"] for a in items], log=log) if items else {}
    for a in items:
        d = info.get(a["path"], {})
        a["rules"] = d.get("rules", [])
        a["generators"] = d.get("generators", [])
        a["error"] = d.get("error") or ""
    return {"analyzers": items, "error": err, "generated": generated_files(project)}


__all__ = ["list_analyzers", "describe", "helper_exe", "generated_files", "generated_roots", "emit_generated_argv",
           "project_analyzers"]
