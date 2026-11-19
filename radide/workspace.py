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
    return project


def add_module(project: Project, name: str, language: str | None = None, filename: str | None = None) -> Path:
    """Add a code module. *language* = plugin id (None = the project language);
    *filename* = an existing file name to register (its extension decides the language)."""
    plugin = get_plugin(language or project.language)
    if filename:
        plugin = plugin_for_module(project, filename)
    else:
        filename = f"{name}{plugin.code_ext}"
    path = project.folder / filename
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
