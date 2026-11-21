"""The editor's "project context" like Visual Studio 2022 (no Qt here; the combo is ctxbar.py).

A code file can be compiled more than once with different symbols:

* a file of a Shared Project is compiled into every project that imports the .projitems;
* a file of a multi-targeted project (``<TargetFrameworks>net8.0;net48</TargetFrameworks>``) is compiled once
  per target framework.

VS shows a combo above the editor ("WinApp (net8.0-windows)") and greys the ``#if`` blocks the selected context
does not compile. ``solution_contexts`` (open ``VsSolution``) / ``contexts_for_file`` (plain project files) list
those contexts; ``ProjectContext.symbols()`` gives the preprocessor symbols of one (DefineConstants of the
configuration + the SDK's implicit framework symbols, exactly what MSBuild passes to the compiler: old-style
.NET Framework projects get only their DefineConstants) and ``inactive_ranges`` the lines to grey.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ...foreign.msbuild import MSBuildProject
from . import preprocessor as PP
from .model import SharedProject, references_shared, shared_imports


def _norm(p) -> str:
    return os.path.normcase(str(Path(p).resolve()))


@dataclass
class ProjectContext:
    project_file: Path
    name: str                       # project name (the solution's name for it, else the project file stem)
    tfm: str = ""                   # target framework ("" = the project's only / old-style one)
    multi: bool = False             # the project has several target frameworks
    shared: SharedProject | None = None   # the shared project the file belongs to (None = the project's own file)
    configuration: str = "Debug"
    platform: str = "AnyCPU"
    project: object = None          # radide.foreign.vs_solution.VsProject when known
    active_symbols: list = field(default_factory=list)   # last computed symbols (names), for the bar's label

    @property
    def language(self) -> str:
        ms = getattr(self.project, "ms", None)
        if ms is not None:
            return ms.language
        return {".vbproj": "VB", ".fsproj": "F#"}.get(Path(self.project_file).suffix.lower(), "C#")

    @property
    def label(self) -> str:
        return f"{self.name} ({self.tfm})" if self.tfm and (self.multi or self.shared is not None) else self.name

    @property
    def key(self) -> str:
        return f"{_norm(self.project_file)}|{self.tfm}"

    def ms(self) -> MSBuildProject:
        ms = getattr(self.project, "ms", None)
        return ms if ms is not None else MSBuildProject.load(self.project_file)

    def symbols(self, configuration: str | None = None, platform: str | None = None):
        """C#: a list of symbols; VB: {name: value}."""
        cfg, plat = configuration or self.configuration, platform or self.platform
        ms = self.ms()
        if self.language == "VB":
            return PP.vb_constants(ms, cfg, plat, self.tfm)
        return PP.define_constants(ms, cfg, plat, self.tfm)

    def inactive_ranges(self, text: str, configuration: str | None = None, platform: str | None = None):
        return PP.inactive_ranges(text, self.symbols(configuration, platform), self.language)


def _frameworks(ms: MSBuildProject) -> list[str]:
    try:
        return [t for t in ms.target_frameworks if t] or [""]
    except Exception:  # noqa: BLE001
        return [""]


def _contexts_of(pf: Path, name: str = "", shared=None, cfg: str = "Debug", plat: str = "AnyCPU",
                 project=None) -> list[ProjectContext]:
    ms = getattr(project, "ms", None)
    if ms is None:
        try:
            ms = MSBuildProject.load(pf)
        except (OSError, ValueError):
            return []
    tfms = _frameworks(ms)
    return [ProjectContext(Path(pf), name or Path(pf).stem, t, len(tfms) > 1, shared, cfg, plat, project)
            for t in tfms]


def _under(path, folder) -> bool:
    try:
        Path(path).resolve().relative_to(Path(folder).resolve())
        return True
    except (ValueError, OSError):
        return False


def shared_project_of(path, shared_projects) -> SharedProject | None:
    """The shared project (of *shared_projects*: SharedProject or .shproj paths) that has *path*."""
    for sp in shared_projects:
        try:
            sp = sp if isinstance(sp, SharedProject) else SharedProject(Path(sp))
        except (OSError, ValueError):
            continue
        if sp.contains(path) is not None or _under(path, sp.items_folder) and Path(path).suffix.lower() == sp.code_ext:
            return sp
    return None


def contexts_for_file(path, project_files, shared_projects=(), names: dict | None = None,
                      configuration: str = "Debug", platform: str = "AnyCPU") -> list[ProjectContext]:
    """The project contexts of the code file *path*, from plain project files (no open solution needed).

    *project_files*: the C#/VB project files; *shared_projects*: SharedProject objects or .shproj paths;
    *names*: optional {normcased project file: display name}. One context or none = nothing to choose."""
    names = names or {}
    path = Path(path)
    sp = shared_project_of(path, shared_projects)
    if sp is not None:
        n = _norm(sp.projitems_path)
        out: list[ProjectContext] = []
        for pf in project_files:
            if any(_norm(i) == n for i in shared_imports(pf)):
                out += _contexts_of(Path(pf), names.get(_norm(pf), ""), sp, configuration, platform)
        return out
    owner = None
    for pf in project_files:                      # the deepest project folder that holds the file
        if _under(path, Path(pf).parent) and (owner is None or len(str(Path(pf).parent)) > len(str(owner.parent))):
            owner = Path(pf)
    return _contexts_of(owner, names.get(_norm(owner), ""), None, configuration, platform) if owner else []


# ---------------------------------------------------------------- the open Visual Studio solution
def project_files(sln) -> list[Path]:
    """C#/VB/F# project files of a VsSolution (loaded projects first, then the .sln/.slnx entries)."""
    out: dict[str, Path] = {}
    for p in (sln.all_projects() if sln is not None and hasattr(sln, "all_projects") else []):
        ms = getattr(p, "ms", None)
        if ms is not None and ms.path.suffix.lower() in (".csproj", ".vbproj", ".fsproj"):
            out.setdefault(_norm(ms.path), ms.path)
    model = getattr(sln, "model", None)
    for e in getattr(model, "entries", []) if model is not None else []:
        if e.path.lower().endswith((".csproj", ".vbproj", ".fsproj")):
            p = (model.folder / e.path).resolve()
            if p.is_file():
                out.setdefault(_norm(p), p)
    return list(out.values())


def solution_contexts(sln, path, shared_projects=None) -> list[ProjectContext]:
    """Project contexts of a .cs/.vb file of the open VsSolution, with each project's active configuration."""
    path = Path(path)
    if sln is None or path.suffix.lower() not in (".cs", ".vb"):
        return []
    if shared_projects is None:
        from .model import solution_shared_projects
        shared_projects = solution_shared_projects(sln.model) if getattr(sln, "model", None) is not None else []
    out: list[ProjectContext] = []

    def add(proj, shared=None):
        cfg, plat = sln.project_config(proj)
        out.extend(_contexts_of(proj.ms.path, sln.name_of(proj), shared, cfg, plat, proj))
    for sp in shared_projects:
        if sp.contains(path) is None:
            continue
        for proj in sln.all_projects():
            if getattr(proj, "ms", None) is not None and proj.ms.language == sp.language \
                    and references_shared(proj.ms.path, sp):
                add(proj, sp)
        return out
    n = _norm(path)
    for proj in sln.all_projects():
        ms = getattr(proj, "ms", None)
        if ms is None or ms.language not in ("C#", "VB") or not _under(path, proj.folder):
            continue
        if any(_norm(Path(proj.folder) / m) == n for m in proj.modules) or \
                any(_norm(Path(proj.folder) / c) == n for c in getattr(proj, "form_code", {}).values()):
            add(proj)
            break
    return out


def symbols_text(ctx: ProjectContext) -> str:
    """For tooltips: 'DEBUG;TRACE;NET8_0;...' (VB: 'DEBUG=True, CONFIG="Debug", ...')."""
    s = ctx.symbols()
    if isinstance(s, dict):
        return ", ".join(f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}" for k, v in s.items())
    return ";".join(s)


__all__ = ["ProjectContext", "contexts_for_file", "solution_contexts", "project_files", "shared_project_of",
           "symbols_text"]
