"""File-level project operations (no UI) - create projects/forms, rename forms."""
from __future__ import annotations

from pathlib import Path

from .languages import get_plugin, plugin_for_form, plugin_for_module
from .model import Form, Project


def _startup_plugin(project: Project):
    return plugin_for_form(project, project.startup) if project.startup else get_plugin(project.language)


def _regen(project: Project, name: str) -> None:
    plugin = plugin_for_form(project, name)
    code = (project.folder / plugin.code_file(name)).read_text(encoding="utf-8")
    form = Form.load(project.form_path(name))
    (project.folder / plugin.designer_file(name)).write_text(
        plugin.generate_designer(form, code), encoding="utf-8")


def create_form(project: Project, name: str, language: str | None = None) -> Form:
    """Create a form. *language* = plugin id (None = the project language)."""
    project.set_form_language(name, language or project.language)
    plugin = plugin_for_form(project, name)
    form = Form()
    form.props["Name"] = name
    form.props["Text"] = name
    is_startup = not project.forms
    form.save(project.form_path(name))
    code = plugin.new_code(form, is_startup)
    (project.folder / plugin.code_file(name)).write_text(code, encoding="utf-8")
    (project.folder / plugin.designer_file(name)).write_text(
        plugin.generate_designer(form, code), encoding="utf-8")
    # the startup file imports/loads the new form only when both use the same language
    if not is_startup and project.startup and _startup_plugin(project).id == plugin.id:
        sp = project.folder / plugin.code_file(project.startup)
        if sp.exists():
            sp.write_text(plugin.on_form_added(sp.read_text(encoding="utf-8"), name), encoding="utf-8")
    project.forms.append(name)
    if is_startup:
        project.startup = name
    project.save()
    return form


def create_project(folder: Path, name: str, language: str) -> Project:
    folder.mkdir(parents=True, exist_ok=True)
    project = Project(folder, name, language)
    create_form(project, "Form1")
    write_lsp_manifest(folder)
    return project


def write_lsp_manifest(folder, server: str | None = None) -> bool:
    """rust-analyzer and csharp-ls answer nothing (no hover, definition, diagnostics) without Cargo.toml / a .csproj;
    the GUI Bridge projects used to get theirs only on the first Run. Written when the project is created and when
    its language server starts (radide/lsp.py). *server* = "rust" / "csharp" / None (both). True = written."""
    try:
        folder = Path(folder)
        if not (folder / Project.FILE).is_file():
            return False
        project = Project.load(folder)
        langs = {project.language, *(getattr(project, "form_languages", {}) or {}).values()}
        if server in (None, "rust") and "rust-bridge" in langs and not (folder / "Cargo.toml").is_file():
            from .languages.rust_bridge import init_manifest
            init_manifest(folder)
            return (folder / "Cargo.toml").is_file()
        if server in (None, "csharp") and "csharp-bridge" in langs:
            from .languages.csharp_bridge import CSPROJ, build_dir, ensure_build_dir, native_mode
            if native_mode(folder):
                # a WinForms exe: csharp-ls needs RadIDE.Runtime.dll (built once, in the background - it only
                # takes seconds the first time) and the current csproj / generated designers
                from .dotnet import native_project, runtime_lib
                if not runtime_lib.is_built():
                    import threading
                    threading.Thread(target=runtime_lib.build, kwargs={"log": lambda _s: None}, daemon=True).start()
                existed = (build_dir(folder) / CSPROJ).is_file()
                native_project.generate(folder, build_dir(folder))
                ensure_build_dir(folder)
                return not existed
            if not (build_dir(folder) / CSPROJ).is_file():
                ensure_build_dir(folder)
                return True
    except Exception:  # noqa: BLE001 - never block creating / opening a project
        return False
    return False


def add_module(project: Project, name: str, language: str | None = None, filename: str | None = None) -> Path:
    """Add a code module. *language* = plugin id (None = the project language);
    *filename* = an existing file name to register (its extension decides the language)."""
    plugin = get_plugin(language or project.language)
    if filename:
        plugin = plugin_for_module(project, filename)
    else:
        filename = f"{getattr(plugin, 'module_dir', '')}{name}{plugin.code_ext}"    # Flutter: lib/<name>.dart
    path = project.folder / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(plugin.module_template(Path(filename).stem), encoding="utf-8")
    if filename not in project.modules:
        project.modules.append(filename)
    if project.startup:
        sp_plugin = _startup_plugin(project)
        if sp_plugin.code_ext.lower() == Path(filename).suffix.lower():   # same language: import/load it
            sp = project.folder / sp_plugin.code_file(project.startup)
            if sp.exists():
                sp.write_text(sp_plugin.on_file_added(sp.read_text(encoding="utf-8"), filename),
                              encoding="utf-8")
    project.save()
    return path


def _drop_references(project: Project, filename: str) -> None:
    for name in project.forms:
        plugin = plugin_for_form(project, name)
        p = project.folder / plugin.code_file(name)
        if p.exists():
            p.write_text(plugin.on_file_removed(p.read_text(encoding="utf-8"), filename), encoding="utf-8")


def delete_form(project: Project, name: str) -> None:
    """Delete a form and its files (moved to the project's _deleted folder)."""
    plugin = plugin_for_form(project, name)
    trash = project.folder / "_deleted"
    trash.mkdir(exist_ok=True)
    for f in (project.form_path(name), project.folder / plugin.code_file(name),
              project.folder / plugin.designer_file(name)):
        if f.exists():
            target = trash / f.name
            if target.exists():
                target.unlink()
            f.rename(target)
    project.forms = [f for f in project.forms if f != name]
    project.form_languages.pop(name, None)
    if project.startup == name:
        project.startup = project.forms[0] if project.forms else ""
    _drop_references(project, plugin.code_file(name))
    project.save()


def delete_module(project: Project, filename: str) -> None:
    trash = project.folder / "_deleted"
    trash.mkdir(exist_ok=True)
    src = project.folder / filename
    if src.exists():
        target = trash / filename
        if target.exists():
            target.unlink()
        src.rename(target)
    project.modules = [m for m in project.modules if m != filename]
    _drop_references(project, filename)
    project.save()


def rename_form(project: Project, old: str, new: str) -> None:
    """Rename a form: its files, its name inside every code file, the project."""
    plugin = plugin_for_form(project, old)
    f = project.folder
    form = Form.load(project.form_path(old))
    form.props["Name"] = new
    if form.props.get("Text") == old:
        form.props["Text"] = new
    form.save(project.form_path(new))
    project.form_path(old).unlink()
    (f / plugin.code_file(old)).rename(f / plugin.code_file(new))
    old_designer = f / plugin.designer_file(old)
    if old_designer.exists():
        old_designer.unlink()
    project.forms = [new if n == old else n for n in project.forms]
    if old in project.form_languages:
        project.form_languages[new] = project.form_languages.pop(old)
    if project.startup == old:
        project.startup = new
    for name in project.forms:
        fp = plugin_for_form(project, name)
        p = f / fp.code_file(name)
        if p.exists():
            p.write_text(fp.rename_symbol(p.read_text(encoding="utf-8"), old, new), encoding="utf-8")
    project.save()
    for name in project.forms:
        _regen(project, name)


# ============================================================================ solutions (CONTRACTS 7)
def create_solution(folder: Path, name: str):
    """Create an empty solution: <folder>/<name>.radsln. Returns the Solution."""
    from .solution import Solution
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    sol = Solution(name, folder.resolve(), [], "")
    sol.save()
    return sol


def create_library_project(folder: Path, name: str, language: str) -> Project:
    """Create a Class Library project: no form, one module "<Name><ext>" with an example
    public function (plugin.library_template)."""
    plugin = get_plugin(language)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    project = Project(folder, name, language, kind="library")
    filename = f"{name}{plugin.code_ext}"
    path = folder / filename
    if not path.exists():
        path.write_text(plugin.library_template(name), encoding="utf-8")
    project.modules.append(filename)
    project.save()
    return project


def add_project_to_solution(solution, project, name: str | None = None):
    """Add an existing project (Project or folder) to the solution and save the .radsln.
    Returns the loaded Project."""
    entry = solution.add_project(project, name)
    solution.save()
    return solution.project(entry.name)


def remove_project_from_solution(solution, name: str) -> list[Project]:
    """Remove a project from the solution (files stay on disk) and drop the references the
    other projects had to it (their proxies are deleted). Returns the changed projects."""
    from .references import update_proxies
    entry = solution.entry(name)
    if entry is None:
        raise KeyError(f"project '{name}' is not in solution '{solution.name}'")
    changed = []
    for p in solution.all_projects():
        if solution.name_of(p).lower() != entry.name.lower() and p.references_project(entry.name):
            p.references = [r for r in p.references if r.lower() != entry.name.lower()]
            changed.append(p)
    solution.remove_project(entry.name)
    solution.save()
    for p in changed:
        p.save()
        update_proxies(solution, p)
    return changed


def _resolve(solution, project) -> Project:
    p = solution.project(project) if isinstance(project, str) else project
    if p is None:
        raise ValueError(f"project '{project}' is not in solution '{solution.name}'")
    return p


def add_reference(solution, project, lib: str, log=None) -> list[Path]:
    """*project* (Project or name) references the project *lib* of the same solution.
    Raises ValueError for an unknown project or a reference cycle. Saves project.radproj and
    writes the proxy files; returns the files written."""
    from .references import update_proxies
    project = _resolve(solution, project)
    lib_project = _resolve(solution, lib)
    lib_name = solution.name_of(lib_project)
    if solution.would_create_cycle(project, lib_name):
        if lib_name.lower() == solution.name_of(project).lower():
            raise ValueError(f"a project cannot reference itself ({lib_name})")
        raise ValueError(f"{solution.name_of(project)} cannot reference {lib_name}: {lib_name} already "
                         f"references {solution.name_of(project)} (circular reference)")
    if not project.references_project(lib_name):
        project.references.append(lib_name)
        project.save()
    return update_proxies(solution, project, log)


def remove_reference(solution, project, lib: str, log=None) -> list[Path]:
    """Remove a reference; its proxy files are deleted. Returns the files (re)written."""
    from .references import update_proxies
    project = _resolve(solution, project)
    before = len(project.references)
    project.references = [r for r in project.references if r.lower() != str(lib).lower()]
    if len(project.references) != before:
        project.save()
    return update_proxies(solution, project, log)
