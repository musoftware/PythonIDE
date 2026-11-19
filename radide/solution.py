"""Solutions: several projects (one language each) that use each other through References.

A ``<Name>.radsln`` file (JSON) in the solution folder (docs/CONTRACTS.md section 7.1)::

    {"name": "MySolution",
     "projects": [{"name": "App", "path": "App"}, {"name": "MathLib", "path": "MathLib"}],
     "startup": "App"}

``path`` is relative to the .radsln folder. Opening a bare project (``project.radproj`` or a
project folder) gives an *implicit* solution with that one project (``Solution.file is None``);
saving an implicit solution writes ``<Name>.radsln`` into the project folder and makes it real.

No UI code here; file-level operations that also touch project files (create, Add Reference,
proxies) are in ``radide.workspace`` and ``radide.references``.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .model import Project

EXT = ".radsln"


@dataclass
class SolutionProject:
    """One entry of a solution: the project's name and its folder relative to the solution."""
    name: str
    path: str

    def to_dict(self) -> dict:
        return {"name": self.name, "path": self.path}


def _relpath(target: Path, start: Path) -> str:
    try:
        rel = os.path.relpath(target, start)
    except ValueError:                         # another drive (Windows)
        return str(target)
    return "." if rel in ("", ".") else rel.replace("\\", "/")


def _same(a: Path, b: Path) -> bool:
    try:
        return os.path.normcase(str(Path(a).resolve())) == os.path.normcase(str(Path(b).resolve()))
    except OSError:
        return False


@dataclass
class Solution:
    name: str
    folder: Path
    projects: list[SolutionProject] = field(default_factory=list)
    startup: str = ""
    file: Path | None = None          # the .radsln file; None = implicit (bare project) solution
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    # ------------------------------------------------------------------ io
    @property
    def implicit(self) -> bool:
        return self.file is None

    @property
    def path(self) -> Path:
        """Where the .radsln is (or will be written by save())."""
        return self.file if self.file is not None else self.folder / f"{self.name}{EXT}"

    def to_dict(self) -> dict:
        return {"name": self.name, "projects": [p.to_dict() for p in self.projects], "startup": self.startup}

    def save(self, path: Path | None = None) -> Path:
        """Write the .radsln (an implicit solution becomes a real one)."""
        target = Path(path) if path is not None else self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not _same(target.parent, self.folder):        # paths stay relative to the .radsln folder
            for p in self.projects:
                p.path = _relpath(self._abs(p.path), target.parent)
            self.folder = target.parent
        target.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.file = target
        return target

    @staticmethod
    def load(path: Path) -> "Solution":
        path = Path(path).resolve()
        d = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError(f"{path.name} is not a solution file")
        projects = []
        for e in d.get("projects") or []:
            if isinstance(e, dict) and e.get("name") and e.get("path") is not None:
                projects.append(SolutionProject(str(e["name"]), str(e["path"])))
        return Solution(str(d.get("name") or path.stem), path.parent, projects, str(d.get("startup") or ""), path)

    @staticmethod
    def implicit_for(project_folder: Path) -> "Solution":
        """A one-project solution around a bare project (nothing is written)."""
        folder = Path(project_folder).resolve()
        project = Project.load(folder)
        sol = Solution(project.name, folder, [SolutionProject(project.name, ".")], project.name, None)
        sol._cache[project.name.lower()] = project
        return sol

    @staticmethod
    def find_for_project(project_folder: Path) -> "Solution | None":
        """A .radsln in the project folder or its parent that lists this project, or None."""
        folder = Path(project_folder).resolve()
        for where in (folder, folder.parent):
            try:
                candidates = sorted(where.glob(f"*{EXT}"))
            except OSError:
                continue
            for f in candidates:
                try:
                    sol = Solution.load(f)
                except (OSError, ValueError):
                    continue
                if any(_same(sol._abs(p.path), folder) for p in sol.projects):
                    return sol
        return None

    @staticmethod
    def open_any(path: Path) -> "Solution":
        """Open a .radsln, a project.radproj or a project/solution folder.

        A project that belongs to a solution (a .radsln in its folder or in the parent folder lists
        it) opens that solution, so its references work; any other project opens as an implicit
        one-project solution. Raises FileNotFoundError when nothing can be opened."""
        path = Path(path).resolve()
        if path.is_file():
            if path.suffix.lower() == EXT:
                return Solution.load(path)
            if path.name.lower() == Project.FILE:
                path = path.parent
            else:
                raise FileNotFoundError(f"{path.name} is not a solution or project file")
        if not path.is_dir():
            raise FileNotFoundError(f"{path} does not exist")
        if (path / Project.FILE).exists():
            sol = Solution.find_for_project(path)
            return sol if sol is not None else Solution.implicit_for(path)
        slns = sorted(path.glob(f"*{EXT}"))
        if slns:
            same = [f for f in slns if f.stem.lower() == path.name.lower()]
            return Solution.load((same or slns)[0])
        raise FileNotFoundError(f"no solution (*{EXT}) or {Project.FILE} in {path}")

    # ------------------------------------------------------------------ queries
    def _abs(self, rel: str) -> Path:
        p = Path(rel)
        return (p if p.is_absolute() else self.folder / p).resolve()

    def entry(self, name: str) -> SolutionProject | None:
        return next((p for p in self.projects if p.name.lower() == str(name).lower()), None)

    def names(self) -> list[str]:
        return [p.name for p in self.projects]

    def project_folder(self, name: str) -> Path:
        e = self.entry(name)
        if e is None:
            raise KeyError(f"project '{name}' is not in solution '{self.name}'")
        return self._abs(e.path)

    def project(self, name: str) -> Project | None:
        """The Project object of a solution entry (loaded once and cached; None if missing/broken)."""
        if isinstance(name, Project):
            return name
        e = self.entry(name)
        if e is None:
            return None
        key = e.name.lower()
        p = self._cache.get(key)
        if p is None:
            try:
                p = Project.load(self._abs(e.path))
            except (OSError, ValueError, KeyError):
                return None
            self._cache[key] = p
        return p

    def all_projects(self) -> list[Project]:
        return [p for p in (self.project(e.name) for e in self.projects) if p is not None]

    def project_for_folder(self, folder: Path) -> Project | None:
        for e in self.projects:
            if _same(self._abs(e.path), folder):
                return self.project(e.name)
        return None

    def name_of(self, project: Project | str) -> str:
        """Solution name of a project (the entry name, matched by folder for Project objects)."""
        if isinstance(project, str):
            e = self.entry(project)
            return e.name if e else project
        for e in self.projects:
            if _same(self._abs(e.path), project.folder):
                return e.name
        return project.name

    def startup_project(self) -> Project | None:
        p = self.project(self.startup) if self.startup else None
        if p is None:
            apps = [x for x in self.all_projects() if not x.is_library]
            p = apps[0] if apps else (self.all_projects() or [None])[0]
        return p

    def reload(self, name: str | None = None) -> None:
        """Forget cached Project objects (all, or one) so the next project() reads the disk."""
        if name is None:
            self._cache.clear()
        else:
            self._cache.pop(str(name).lower(), None)

    def referenced_projects(self, project: Project | str, transitive: bool = True) -> list[Project]:
        """Projects referenced by *project*: direct references in order, then (transitive) the
        references of those, breadth first, without duplicates and without *project* itself.
        Names that are not in the solution are skipped."""
        start = self.project(project) if isinstance(project, str) else project
        if start is None:
            return []
        seen = {self.name_of(start).lower()}
        out: list[Project] = []
        queue = [start]
        while queue:
            cur = queue.pop(0)
            for ref in cur.references:
                if ref.lower() in seen:
                    continue
                seen.add(ref.lower())
                p = self.project(ref)
                if p is None:
                    continue
                out.append(p)
                if transitive:
                    queue.append(p)
            if not transitive:
                break
        return out

    def missing_references(self, project: Project | str) -> list[str]:
        p = self.project(project) if isinstance(project, str) else project
        return [r for r in (p.references if p else []) if self.project(r) is None]

    def search_folders(self, project: Project | str) -> list[Path]:
        """Folders RAD Hub searches for modules: the project, then its references (transitively)."""
        p = self.project(project) if isinstance(project, str) else project
        if p is None:
            return []
        return [Path(p.folder).resolve()] + [Path(r.folder).resolve() for r in self.referenced_projects(p)]

    def would_create_cycle(self, project: Project | str, lib: str) -> bool:
        """True when *project* referencing *lib* closes a cycle (or *lib* is *project*)."""
        pname = self.name_of(project).lower()
        if str(lib).lower() == pname:
            return True
        libp = self.project(lib)
        if libp is None:
            return False
        return any(self.name_of(r).lower() == pname for r in self.referenced_projects(libp))

    def build_order(self) -> list[Project]:
        """All projects, every project after the projects it references (libraries first).
        Raises ValueError on a reference cycle."""
        order: list[Project] = []
        state: dict[str, int] = {}          # 1 = visiting, 2 = done

        def visit(name: str, path: list[str]):
            key = name.lower()
            if state.get(key) == 2:
                return
            if state.get(key) == 1:
                raise ValueError("reference cycle: " + " -> ".join(path + [name]))
            p = self.project(name)
            if p is None:
                return
            state[key] = 1
            for r in p.references:
                visit(self.name_of(r), path + [self.name_of(name)])
            state[key] = 2
            order.append(p)

        for e in self.projects:
            visit(e.name, [])
        return order

    # ------------------------------------------------------------------ edits (in memory; call save())
    def add_project(self, project: Project | Path | str, name: str | None = None) -> SolutionProject:
        """Add an existing project (Project object or folder). Raises ValueError for a duplicate
        name or folder. The first project added becomes the startup project."""
        if isinstance(project, Project):
            proj = project
        else:
            proj = Project.load(Path(project))
        folder = Path(proj.folder).resolve()
        name = name or proj.name
        if self.entry(name) is not None:
            raise ValueError(f"the solution already has a project named '{name}'")
        for e in self.projects:
            if _same(self._abs(e.path), folder):
                raise ValueError(f"{folder} is already in the solution (as '{e.name}')")
        entry = SolutionProject(name, _relpath(folder, self.folder))
        self.projects.append(entry)
        self._cache[name.lower()] = proj
        cur = self.project(self.startup) if self.startup and self.entry(self.startup) is not None else None
        if cur is None or (cur.is_library and not proj.is_library):     # prefer an app as startup
            self.startup = name
        return entry

    def remove_project(self, name: str) -> SolutionProject:
        """Remove a project from the solution (its files stay). References to it in the other
        projects are not changed here - see workspace.remove_project_from_solution."""
        e = self.entry(name)
        if e is None:
            raise KeyError(f"project '{name}' is not in solution '{self.name}'")
        self.projects.remove(e)
        self._cache.pop(e.name.lower(), None)
        if self.startup.lower() == e.name.lower():
            self.startup = ""
            sp = self.startup_project()
            self.startup = self.name_of(sp) if sp is not None else ""
        return e

    def set_startup(self, name: str) -> None:
        e = self.entry(name)
        if e is None:
            raise KeyError(f"project '{name}' is not in solution '{self.name}'")
        self.startup = e.name

    def rename(self, new_name: str) -> None:
        """Rename the solution (and its .radsln file when it has one)."""
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("empty solution name")
        old_file = self.file
        self.name = new_name
        if old_file is not None:
            target = old_file.with_name(f"{new_name}{EXT}")
            if not _same(target, old_file):
                if target.exists():
                    raise ValueError(f"{target.name} already exists")
                old_file.rename(target)
            self.file = target
            self.save()

    def rename_project(self, old: str, new: str) -> list[Project]:
        """Rename a project in the solution: its entry, its project.radproj name, the references
        of the other projects. Saves the changed project files and returns them (proxies must
        be regenerated by the caller: references.refresh_all)."""
        e = self.entry(old)
        if e is None:
            raise KeyError(f"project '{old}' is not in solution '{self.name}'")
        if self.entry(new) is not None and self.entry(new) is not e:
            raise ValueError(f"the solution already has a project named '{new}'")
        proj = self.project(e.name)
        changed: list[Project] = []
        for other in self.all_projects():
            if other is proj:
                continue
            if other.references_project(e.name):
                other.references = [new if r.lower() == e.name.lower() else r for r in other.references]
                changed.append(other)
        self._cache.pop(e.name.lower(), None)
        if self.startup.lower() == e.name.lower():
            self.startup = new
        e.name = new
        if proj is not None:
            proj.name = new
            self._cache[new.lower()] = proj
            changed.insert(0, proj)
        for p in changed:
            p.save()
        if self.file is not None:
            self.save()
        return changed
