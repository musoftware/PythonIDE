"""Small helpers shared by the .NET tools: the dotnet executable, a quiet environment, cache folders,
running the CLI and evaluating MSBuild items / properties (``-getItem`` / ``-getProperty``, .NET 8+ SDK)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LOCAL = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "RADIDE"
QUIET_ENV = {"DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
             "DOTNET_CLI_UI_LANGUAGE": "en", "VSLANG": "1033", "MSBUILDTERMINALLOGGER": "off"}
PROJECT_EXTS = (".csproj", ".vbproj", ".fsproj")


def dotnet() -> str:
    try:
        from ...foreign.msbuild import find_dotnet
        return find_dotnet() or ""
    except Exception:  # noqa: BLE001
        import shutil
        return shutil.which("dotnet") or ""


def env(extra: dict | None = None) -> dict:
    e = dict(os.environ)
    e.update(QUIET_ENV)
    e.update(extra or {})
    return e


def cache_dir(*parts: str) -> Path:
    d = LOCAL.joinpath("cache", *parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def tools_dir() -> Path:
    d = LOCAL / "tools"
    d.mkdir(parents=True, exist_ok=True)
    return d


def short_hash(text: str) -> str:
    return hashlib.sha1(text.lower().encode("utf-8", "replace")).hexdigest()[:10]


def run(argv, cwd=None, timeout=300, extra_env=None) -> tuple[int, str]:
    """Run a command, return (exit code, stdout+stderr). (-1, message) when it cannot start / times out."""
    try:
        r = subprocess.run([str(a) for a in argv], cwd=str(cwd) if cwd else None, capture_output=True,
                           timeout=timeout, creationflags=NO_WINDOW, env=env(extra_env))
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {timeout} s: {' '.join(str(a) for a in argv[:4])}"
    except OSError as e:
        return -1, str(e)
    out = (r.stdout or b"") + (r.stderr or b"")
    return r.returncode, out.decode("utf-8", "replace").replace("\r\n", "\n")


def sdk_version() -> str:
    code, out = run([dotnet() or "dotnet", "--version"], timeout=60)
    return out.strip().splitlines()[-1].strip() if code == 0 and out.strip() else ""


def sdk_folder() -> Path | None:
    """C:\\Program Files\\dotnet\\sdk\\<version> of the active SDK."""
    dn = dotnet()
    ver = sdk_version()
    if not dn or not ver:
        return None
    p = Path(dn).resolve().parent / "sdk" / ver
    return p if p.is_dir() else None


def msbuild_eval(project, items=(), properties=(), targets=(), timeout=240, extra=()) -> dict:
    """``dotnet msbuild -getItem/-getProperty [-t:targets]`` as {"Items": {...}, "Properties": {...}}.
    {} on failure (old SDK, broken project, not restored ...)."""
    dn = dotnet()
    if not dn:
        return {}
    argv = [dn, "msbuild", str(project), "-nologo"]
    argv += [f"-getItem:{i}" for i in items] + [f"-getProperty:{p}" for p in properties]
    if targets:
        argv.append("-t:" + ";".join(targets))
    argv += list(extra)
    code, out = run(argv, cwd=Path(project).parent, timeout=timeout)
    i = out.find("{")
    if code != 0 or i < 0:
        if len(properties) == 1 and not items and code == 0 and out.strip():
            return {"Properties": {properties[0]: out.strip().splitlines()[-1].strip()}}
        return {}
    try:
        d = json.loads(out[i:out.rfind("}") + 1])
    except ValueError:
        return {}
    d.setdefault("Items", {})
    d.setdefault("Properties", {})
    return d


def find_projects(root: Path, limit: int = 200) -> list[Path]:
    """Project files under *root* (bin/obj/.git/node_modules skipped)."""
    skip = {"bin", "obj", ".git", ".vs", "node_modules", "packages", "TestResults"}
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for f in filenames:
            if f.lower().endswith(PROJECT_EXTS):
                out.append(Path(dirpath) / f)
                if len(out) >= limit:
                    return sorted(out)
    return sorted(out)


def solution_projects(sln: Path) -> list[Path]:
    """Project files listed by a .sln / .slnx (no MSBuild needed)."""
    sln = Path(sln)
    try:
        text = sln.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    rels = []
    if sln.suffix.lower() == ".slnx":
        rels = re.findall(r'<Project\s+Path="([^"]+)"', text)
    else:
        rels = [m.group(1) for m in re.finditer(r'^Project\("[^"]*"\)\s*=\s*"[^"]*",\s*"([^"]+)"', text, re.M)]
    out = []
    for r in rels:
        p = (sln.parent / r.replace("\\", "/")).resolve()
        if p.suffix.lower() in PROJECT_EXTS and p.is_file():
            out.append(p)
    return out


def owning_project(path: Path, projects: list[Path]) -> Path | None:
    """The project whose folder contains *path* (the deepest one)."""
    best = None
    try:
        rp = Path(path).resolve()
    except OSError:
        return None
    for proj in projects:
        folder = Path(proj).resolve().parent
        try:
            rp.relative_to(folder)
        except ValueError:
            continue
        if best is None or len(str(folder)) > len(str(Path(best).parent)):
            best = proj
    return best


def project_for_file(path: Path) -> Path | None:
    """The nearest .csproj / .vbproj / .fsproj above *path*."""
    p = Path(path).resolve()
    for d in [p.parent, *p.parent.parents]:
        try:
            hits = sorted(x for x in d.iterdir() if x.suffix.lower() in PROJECT_EXTS)
        except OSError:
            continue
        if hits:
            return hits[0]
    return None


def text(path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


__all__ = ["dotnet", "env", "cache_dir", "tools_dir", "run", "sdk_version", "sdk_folder", "msbuild_eval",
           "find_projects", "solution_projects", "owning_project", "project_for_file", "text", "QUIET_ENV", "LOCAL"]
