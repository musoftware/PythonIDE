"""Which .NET projects the IDE window has open (for the NuGet UI and the Package Manager Console).

* Visual Studio solutions (radide/foreign/vs_solution.py): every C# / VB / F# project.
* RAD IDE's own C# GUI-Bridge projects: their NuGet manifest is ``<project>/_build/csharp/RadApp.csproj``
  (created on demand, radide/languages/csharp_bridge.py), also inside a multi-project .radsln.
"""
from __future__ import annotations

from pathlib import Path

from .projects import NuGetProject

BRIDGE_LANGS = ("csharp-bridge",)


def _vs_solution(win):
    try:
        from ...foreign.vs_solution import VsSolution
    except Exception:  # noqa: BLE001
        return None
    sln = getattr(win, "sln", None)
    return sln if isinstance(sln, VsSolution) else None


def solution_folder(win) -> Path | None:
    sln = getattr(win, "sln", None)
    if sln is not None and getattr(sln, "folder", None):
        return Path(sln.folder)
    proj = getattr(win, "project", None)
    return Path(proj.folder) if proj is not None and getattr(proj, "folder", None) else None


def solution_file(win) -> Path | None:
    sln = _vs_solution(win)
    f = getattr(sln, "file", None) if sln is not None else None
    if f and Path(f).suffix.lower() in (".sln", ".slnx") and Path(f).is_file():
        return Path(f)
    return None


def solution_name(win) -> str:
    sln = getattr(win, "sln", None)
    if sln is not None and getattr(sln, "name", ""):
        return sln.name
    proj = getattr(win, "project", None)
    return getattr(proj, "name", "") or "Solution"


def _bridge_project(project, folder: Path | None) -> NuGetProject | None:
    if getattr(project, "language", "") not in BRIDGE_LANGS:
        return None
    try:
        from ...languages import csharp_bridge
        csproj = csharp_bridge.ensure_build_dir(Path(project.folder))
    except Exception:  # noqa: BLE001
        return None
    np = NuGetProject(csproj, getattr(project, "name", "") or Path(project.folder).name, folder or project.folder)
    np.ide_project = project
    return np


def dotnet_projects(win) -> list[NuGetProject]:
    out: list[NuGetProject] = []
    sln = _vs_solution(win)
    if sln is not None:
        for p in sln.all_projects():
            ms = getattr(p, "ms", None)
            if ms is None or ms.language == "C++":
                continue
            try:
                np = NuGetProject(ms.path, p.name, sln.folder)
            except (OSError, ValueError):
                continue
            np.ide_project = p
            out.append(np)
        return out
    folder = solution_folder(win)
    sol = getattr(win, "sln", None)
    projects = []
    try:
        projects = sol.all_projects() if sol is not None else []
    except Exception:  # noqa: BLE001
        projects = []
    if not projects and getattr(win, "project", None) is not None:
        projects = [win.project]
    for p in projects:
        np = _bridge_project(p, folder)
        if np is not None:
            out.append(np)
    return out


def current_project(win, projects: list[NuGetProject] | None = None) -> NuGetProject | None:
    projects = projects if projects is not None else dotnet_projects(win)
    cur = getattr(win, "project", None)
    for np in projects:
        if getattr(np, "ide_project", None) is cur:
            return np
    return projects[0] if projects else None


def is_dotnet(win) -> bool:
    if _vs_solution(win) is not None:
        return True
    proj = getattr(win, "project", None)
    return getattr(proj, "language", "") in BRIDGE_LANGS


def reload_in_ide(win, np: NuGetProject) -> None:
    """Re-read the project file in Solution Explorer after a package change."""
    ide = getattr(np, "ide_project", None)
    try:
        np.reload()
    except Exception:  # noqa: BLE001
        pass
    if ide is not None and hasattr(ide, "ms"):
        try:
            from ...foreign import vs_ui
            ide.reload()
            vs_ui._refresh(win)
        except Exception:  # noqa: BLE001
            pass


__all__ = ["dotnet_projects", "current_project", "solution_folder", "solution_file", "solution_name", "is_dotnet",
           "reload_in_ide"]
