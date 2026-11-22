"""Solution operations on the open Visual Studio solution (a ``radide.foreign.vs_solution.VsSolution``):
every edit goes through ``radide.dotnet.sln.model.SolutionDoc`` (.sln and .slnx alike), is saved, and
the IDE's solution (projects, Solution Explorer, configuration combos) is re-synchronized.

IDE-only state that Visual Studio keeps in its .suo (unloaded projects, multiple startup projects,
the active launch profile of each project) is stored in the solution's IDE state folder
(``%APPDATA%\\RADIDE\\foreign\\<name>-<hash>\\solution-ext.json``) - never next to the user's files.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .model import FOLDER_GUID, SolutionDoc, find_project_files, new_solution

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
OFFSCREEN = os.environ.get("QT_QPA_PLATFORM", "") == "offscreen"


def _log(win, text: str) -> None:
    try:
        win.log(text)
    except Exception:  # noqa: BLE001
        print(text)


def _norm(p) -> str:
    return os.path.normcase(str(Path(p).resolve()))


# ====================================================================== IDE state (like the .suo)
def state_file(sln) -> Path | None:
    st = getattr(sln, "state", None)
    return Path(st) / "solution-ext.json" if st else None


def load_state(sln) -> dict:
    f = state_file(sln)
    try:
        d = json.loads(f.read_text(encoding="utf-8")) if f is not None and f.is_file() else {}
    except (OSError, ValueError):
        d = {}
    d.setdefault("unloaded", [])
    d.setdefault("startup_mode", "single")
    d.setdefault("startup_actions", {})
    d.setdefault("launch_profile", {})
    return d


def save_state(sln, data: dict) -> None:
    f = state_file(sln)
    if f is None:
        return
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def rel_key(sln, project_file) -> str:
    try:
        return os.path.relpath(Path(project_file).resolve(), sln.folder).replace("\\", "/").lower()
    except ValueError:
        return str(project_file).lower()


# ====================================================================== the document <-> the IDE
def is_vs(sln) -> bool:
    try:
        from ...foreign.vs_solution import VsSolution
        return isinstance(sln, VsSolution)
    except Exception:  # noqa: BLE001
        return False


def has_file(sln) -> bool:
    return is_vs(sln) and sln.file is not None and Path(sln.file).suffix.lower() in (".sln", ".slnx")


def doc_of(sln) -> SolutionDoc:
    if not has_file(sln):
        raise ValueError("this is a lone project: save a solution file first (Save Solution As...)")
    return SolutionDoc.load(sln.file)


def project_entry_file(sln, e) -> Path:
    return (Path(sln.folder) / e.path).resolve()


def vs_project_by_file(sln, path):
    want = _norm(path)
    for p in sln.all_projects():
        if _norm(p.ms.path) == want:
            return p
    return None


def unloaded_files(sln) -> set[str]:
    return set(load_state(sln).get("unloaded", []))


def commit(win, sln, doc: SolutionDoc, message: str = "") -> None:
    """Save the document and bring the IDE's solution up to date."""
    doc.save()
    sync(win, sln)
    if message:
        _log(win, message)


def sync(win, sln) -> None:
    """Re-read the solution file: new projects are loaded, removed ones are closed, solution folders,
    dependencies and configurations refreshed."""
    from ...foreign import vs_solution as VS
    from ...solution import Solution, SolutionProject
    model = VS.load_solution_model(sln.file)
    sln.model = model
    unloaded = unloaded_files(sln)
    wanted: dict[str, object] = {}
    for e in model.projects():
        pf = (model.folder / e.path).resolve()
        wanted[_norm(pf)] = e
    for p in list(sln.all_projects()):                  # removed from the file
        if _norm(p.ms.path) not in wanted:
            Solution.remove_project(sln, sln.name_of(p))
            try:
                win._forget_project(p)
            except Exception:  # noqa: BLE001
                pass
    for key, e in wanted.items():
        vp = vs_project_by_file(sln, key)
        if vp is not None:
            vp.sln_entry = e
            continue
        pf = Path(key)
        if rel_key(sln, pf) in unloaded:
            if sln.entry(e.name) is None:
                sln.projects.append(SolutionProject(e.name, os.path.relpath(pf.parent, sln.folder).replace("\\", "/")))
            continue
        if not pf.is_file():
            if sln.entry(e.name) is None:
                sln.projects.append(SolutionProject(e.name, os.path.relpath(pf.parent, sln.folder).replace("\\", "/")))
            continue
        try:
            vp = VS.VsProject(VS.MSBuildProject.load(pf), sln, e.name)
        except (OSError, ValueError) as ex:
            _log(win, f"*** cannot load {pf.name}: {ex}")
            continue
        vp.sln_entry = e
        stale = sln.entry(e.name)
        if stale is not None and sln.project(e.name) is None:
            sln.projects.remove(stale)
        VS._add(sln, vp)
        try:
            win._state_for(vp)
        except Exception:  # noqa: BLE001
            pass
    names = {x.name.lower() for x in model.projects()}
    for sp in list(sln.projects):                      # entries of projects that vanished entirely
        if sp.name.lower() not in names and sln.project(sp.name) is None:
            sln.projects.remove(sp)
    if sln.configuration not in sln.configurations():
        sln.configuration = (sln.configurations() or ["Debug"])[0]
    if sln.platform not in sln.platforms():
        sln.platform = (sln.platforms() or ["Any CPU"])[0]
    if sln.startup and sln.entry(sln.startup) is None:
        sln.startup = ""
    if not sln.startup:
        sp = sln.startup_project()
        sln.startup = sln.name_of(sp) if sp is not None else ""
    sln.save()
    refresh(win)


def refresh(win) -> None:
    try:
        from ...foreign import vs_ui
        vs_ui._refresh(win)
        w = getattr(win, "_vs_watcher", None)
        if w is not None and win.sln is not None:
            paths = [str(p.ms.path) for p in win.sln.all_projects()]
            for p in paths:
                if p not in w.files() and Path(p).exists():
                    w.addPath(p)
    except Exception as e:  # noqa: BLE001
        _log(win, f"[solution] {e}")


# ====================================================================== projects
def add_existing_project(win, sln, project_file, folder_guid: str = "", name: str = ""):
    doc = doc_of(sln)
    e = doc.add_project(project_file, folder_guid, name)
    commit(win, sln, doc, f"Added project '{e.name}' ({e.path}) to {Path(sln.file).name}")
    return e


TEMPLATES = [("Console App", "console"), ("Class Library", "classlib"), ("Windows Forms App", "winforms"),
             ("Windows Forms Class Library", "winformslib"), ("Windows Forms Control Library", "winformscontrollib"),
             ("WPF Application", "wpf"), ("WPF Class Library", "wpflib"), ("ASP.NET Core Empty", "web"),
             ("ASP.NET Core Web API", "webapi"), ("ASP.NET Core Web App (Razor Pages)", "webapp"),
             ("ASP.NET Core Web App (Model-View-Controller)", "mvc"), ("Blazor Web App", "blazor"),
             ("Worker Service", "worker"), ("gRPC Service", "grpc"), ("xUnit Test Project", "xunit"),
             ("NUnit Test Project", "nunit"), ("MSTest Test Project", "mstest"), ("Shared Project", "sharedproject")]


def dotnet_new(template: str, language: str, name: str, out: Path, framework: str = "") -> tuple[int, str]:
    from ...foreign.msbuild import find_dotnet
    dn = find_dotnet()
    if not dn:
        return 1, "The .NET SDK (dotnet) was not found."
    argv = [dn, "new", template, "-n", name, "-o", str(out)]
    if language and template not in ("sharedproject",):
        argv += ["-lang", language]
    if framework:
        argv += ["-f", framework]
    try:
        r = subprocess.run(argv, capture_output=True, text=True, cwd=str(out.parent), creationflags=NO_WINDOW,
                           timeout=600, env={**os.environ, "DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"})
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def new_shared_project(out: Path, name: str, language: str = "C#") -> Path:
    """A Shared Project (.shproj + .projitems) written directly (there is no dotnet template)."""
    out.mkdir(parents=True, exist_ok=True)
    import uuid
    g = str(uuid.uuid4())
    ext = "vb" if language == "VB" else "cs"
    lang_dir = "VisualBasic" if language == "VB" else "CSharp"
    (out / f"{name}.projitems").write_bytes((
        '<?xml version="1.0" encoding="utf-8"?>\r\n'
        '<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">\r\n'
        '  <PropertyGroup>\r\n'
        "    <MSBuildAllProjects Condition=\"'$(MSBuildVersion)' == '' Or '$(MSBuildVersion)' &lt; '16.0'\">"
        "$(MSBuildAllProjects);$(MSBuildThisFileFullPath)</MSBuildAllProjects>\r\n"
        '    <HasSharedItems>true</HasSharedItems>\r\n'
        f'    <SharedGUID>{g}</SharedGUID>\r\n'
        '  </PropertyGroup>\r\n'
        '  <PropertyGroup Label="Configuration">\r\n'
        f'    <Import_RootNamespace>{name}</Import_RootNamespace>\r\n'
        '  </PropertyGroup>\r\n'
        '  <ItemGroup>\r\n'
        f'    <Compile Include="$(MSBuildThisFileDirectory)Shared.{ext}" />\r\n'
        '  </ItemGroup>\r\n'
        '</Project>').encode("utf-8-sig"))
    (out / f"{name}.shproj").write_bytes((
        '<?xml version="1.0" encoding="utf-8"?>\r\n'
        '<Project ToolsVersion="15.0" DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">\r\n'
        '  <PropertyGroup Label="Globals">\r\n'
        f'    <ProjectGuid>{g}</ProjectGuid>\r\n'
        '    <MinimumVisualStudioVersion>14.0</MinimumVisualStudioVersion>\r\n'
        '  </PropertyGroup>\r\n'
        "  <Import Project=\"$(MSBuildExtensionsPath)\\$(MSBuildToolsVersion)\\Microsoft.Common.props\" "
        "Condition=\"Exists('$(MSBuildExtensionsPath)\\$(MSBuildToolsVersion)\\Microsoft.Common.props')\" />\r\n"
        f'  <Import Project="$(MSBuildExtensionsPath32)\\Microsoft\\VisualStudio\\v$(VisualStudioVersion)\\'
        f'CodeSharing\\Microsoft.CodeSharing.{lang_dir}.targets" />\r\n'
        '  <PropertyGroup />\r\n'
        f'  <Import Project="{name}.projitems" Label="Shared" />\r\n'
        f'  <Import Project="$(MSBuildExtensionsPath32)\\Microsoft\\VisualStudio\\v$(VisualStudioVersion)\\'
        f'CodeSharing\\Microsoft.CodeSharing.{lang_dir}.targets" />\r\n'
        '</Project>').encode("utf-8-sig"))
    body = (f"Namespace {name}\r\n    Public Module Shared\r\n    End Module\r\nEnd Namespace\r\n" if ext == "vb" else
            f"namespace {name}\r\n{{\r\n    public static class Shared\r\n    {{\r\n    }}\r\n}}\r\n")
    (out / f"Shared.{ext}").write_bytes(body.encode("utf-8-sig"))
    return out / f"{name}.shproj"


def _off_gui(win, title: str, fn):
    """fn(reporter) in a worker thread with a progress dialog (radide.progress) when called from the GUI
    thread; called directly otherwise (scripts, worker threads, no QApplication)."""
    import threading
    from PyQt6.QtWidgets import QApplication
    if QApplication.instance() is None or threading.current_thread() is not threading.main_thread():
        return fn(None)
    from ...progress import run_blocking
    return run_blocking(win, title, fn)


def new_project(win, sln, template: str, language: str, name: str, location: Path | None = None,
                folder_guid: str = "", framework: str = ""):
    """Add > New Project: ``dotnet new`` into <location>/<name>, then add it to the solution."""
    name = name.strip()
    if not name:
        raise ValueError("enter a project name")
    out = Path(location or sln.folder) / name
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"{out} already exists and is not empty")
    if template == "sharedproject":
        pf = new_shared_project(out, name, language)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        code, text = _off_gui(win, f"dotnet new {template}: {name}",
                              lambda _r: dotnet_new(template, language, name, out, framework))
        if text.strip():
            _log(win, text.rstrip())
        pf = next((p for p in out.glob(f"{name}.*proj")), None) if out.exists() else None
        if code != 0 or pf is None:
            raise ValueError(f"dotnet new {template} failed")
    return add_existing_project(win, sln, pf, folder_guid)


def remove_entry(win, sln, guid: str) -> list:
    doc = doc_of(sln)
    gone = doc.remove(guid)
    if gone:
        commit(win, sln, doc, f"Removed {', '.join(g.name for g in gone if not g.is_folder) or gone[0].name} "
                              f"from {Path(sln.file).name}")
    return gone


def entry_for_project(sln, project):
    doc = doc_of(sln)
    return doc, doc.by_file(project.ms.path)


def unload(win, sln, project) -> None:
    """Unload Project (VS): the node stays, greyed, and the project is not built or run."""
    st = load_state(sln)
    key = rel_key(sln, project.ms.path)
    if key not in st["unloaded"]:
        st["unloaded"].append(key)
    save_state(sln, st)
    name = sln.name_of(project)
    sln._cache.pop(name.lower(), None)
    try:
        win._forget_project(project)
    except Exception:  # noqa: BLE001
        pass
    if sln.startup.lower() == name.lower():
        pass                                        # VS keeps it (F5 then says the project is unloaded)
    _log(win, f"Unloaded project '{name}'")
    refresh(win)


def reload_project(win, sln, name: str):
    from ...foreign import vs_solution as VS
    e = sln.entry(name)
    if e is None:
        return None
    model = sln.model
    me = next((x for x in model.projects() if x.name.lower() == name.lower()), None) if model else None
    if me is None:
        return None
    pf = (model.folder / me.path).resolve()
    st = load_state(sln)
    st["unloaded"] = [u for u in st["unloaded"] if u != rel_key(sln, pf)]
    save_state(sln, st)
    vp = VS.VsProject(VS.MSBuildProject.load(pf), sln, e.name)
    vp.sln_entry = me
    sln._cache[e.name.lower()] = vp
    win._state_for(vp)
    _log(win, f"Reloaded project '{e.name}'")
    refresh(win)
    return vp


def apply_unloaded(sln) -> list[str]:
    """After a solution was loaded: drop the projects the user unloaded (kept as greyed nodes)."""
    st = load_state(sln)
    out = []
    for p in list(sln.all_projects()):
        if rel_key(sln, p.ms.path) in st["unloaded"]:
            name = sln.name_of(p)
            sln._cache.pop(name.lower(), None)
            out.append(name)
    return out


# ====================================================================== solution folders and items
def add_folder(win, sln, name: str, parent_guid: str = ""):
    doc = doc_of(sln)
    f = doc.add_folder(name, parent_guid)
    commit(win, sln, doc, f"Added solution folder '{name}'")
    return f


def rename_folder(win, sln, guid: str, name: str) -> None:
    doc = doc_of(sln)
    doc.rename_folder(guid, name)
    commit(win, sln, doc, f"Renamed solution folder to '{name}'")


def move_entry(win, sln, guid: str, folder_guid: str) -> None:
    doc = doc_of(sln)
    doc.move(guid, folder_guid)
    target = doc.entry(folder_guid).name if folder_guid else "the solution root"
    commit(win, sln, doc, f"Moved '{doc.entry(guid).name}' to {target}")


def add_solution_items(win, sln, folder_guid: str, files: list) -> list[str]:
    doc = doc_of(sln)
    if not folder_guid:
        f = next((x for x in doc.folders() if x.name == "Solution Items" and not x.parent), None)
        folder_guid = (f or doc.add_folder("Solution Items")).guid
    out = [doc.add_item(folder_guid, f) for f in files]
    commit(win, sln, doc, f"Solution items added: {', '.join(out)}")
    return out


def new_solution_item(win, sln, folder_guid: str, name: str, text: str = "") -> Path:
    p = Path(sln.folder) / name
    if not p.exists():
        p.write_text(text, encoding="utf-8")
    add_solution_items(win, sln, folder_guid, [p])
    return p


def remove_solution_item(win, sln, folder_guid: str, rel: str) -> bool:
    doc = doc_of(sln)
    ok = doc.remove_item(folder_guid, rel)
    if ok:
        commit(win, sln, doc, f"Removed solution item {rel} (the file stays on disk)")
    return ok


def folder_guid_by_path(sln, path: str) -> str:
    """'A/B' (the Solution Explorer data of a solution folder node) -> guid."""
    doc = doc_of(sln)
    f = doc.folder_by_path([p for p in str(path).split("/") if p])
    return f.guid if f is not None else ""


# ====================================================================== merging solutions
def import_solution(win, sln, other_path, guids: list[str] | None = None, under: str = "") -> list:
    doc = doc_of(sln)
    other = SolutionDoc.load(other_path)
    added = doc.import_from(other, guids, under)
    commit(win, sln, doc, f"Added {len(added)} project(s) from {Path(other_path).name}: "
                          f"{', '.join(e.name for e in added) or '-'}")
    return added


# ====================================================================== new solutions, formats
def write_solution_for(projects: list, target: Path, folders_from_dirs: bool = True) -> Path:
    doc = new_solution(target, projects, folders_from_dirs)
    doc.save()
    return Path(target)


def new_solution_from_folders(win, folders: list, target: Path, open_it: bool = True) -> Path:
    """File > New > Solution From Existing Folders: every project file found in *folders*."""
    projects = []
    for f in folders:
        projects += [p for p in find_project_files(f) if p not in projects]
    if not projects:
        raise ValueError("no project files (.csproj, .vbproj, .fsproj, .vcxproj, .shproj ...) in the folders")
    path = write_solution_for(projects, Path(target))
    _log(win, f"Created {path.name} with {len(projects)} project(s)")
    if open_it:
        from ...foreign import vs_ui
        vs_ui.open_in_window(win, path)
    return path


def save_solution_as(win, sln, target: Path, open_it: bool = True) -> Path:
    """Save the solution in the other format (.sln <-> .slnx) or a lone project as a new .sln."""
    target = Path(target)
    if has_file(sln):
        doc = doc_of(sln)
        doc.save_as(target)
    else:
        projects = [p.ms.path for p in sln.all_projects()]
        write_solution_for(projects, target, folders_from_dirs=False)
    _log(win, f"Saved solution as {target}")
    if open_it:
        from ...foreign import vs_ui
        vs_ui.open_in_window(win, target)
    return target


# ====================================================================== RAD IDE projects in a VS solution
def add_rad_project(win, sln, rad_folder: Path, folder_guid: str = ""):
    """Add a RAD IDE C# (GUI Bridge) project: its build project ``_build/csharp/RadApp.csproj``
    (compiles the project's *.cs files) joins the solution under the RAD project's name, so other
    projects can reference it and Visual Studio / dotnet build it with the solution."""
    from ...model import Project
    rad_folder = Path(rad_folder)
    if rad_folder.is_file():
        rad_folder = rad_folder.parent
    proj = Project.load(rad_folder)
    lang = str(getattr(proj, "language", ""))
    own = find_project_files(rad_folder, 20)
    own = [p for p in own if "_build" not in p.parts]
    if own:                                       # the RAD project already has its own project file
        return add_existing_project(win, sln, own[0], folder_guid, proj.name)
    if lang != "csharp-bridge":
        raise ValueError(f"'{proj.name}' is a {lang} project: only RAD IDE C# projects have an MSBuild project "
                         "(see docs/DOTNET.md)")
    from ...languages.csharp_bridge import ensure_build_dir
    csproj = ensure_build_dir(rad_folder)
    return add_existing_project(win, sln, csproj, folder_guid, proj.name)


def is_folder_entry(e) -> bool:
    return getattr(e, "type_guid", "").upper() == FOLDER_GUID
