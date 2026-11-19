"""Language plugin registry - every module here exposing PLUGIN is loaded."""
from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

from .base import Completion, LanguagePlugin, RunSpec

_PLUGINS: dict[str, LanguagePlugin] = {}


def _discover() -> None:
    for mod in pkgutil.iter_modules(__path__):
        if mod.name in ("base", "bridgebase") or mod.name.startswith("_"):
            continue
        try:
            m = importlib.import_module(f"{__name__}.{mod.name}")
        except Exception:  # noqa: BLE001 - a broken plugin must not hide the others
            import sys
            import traceback
            sys.stderr.write(f"RAD IDE: language plugin '{mod.name}' failed to load:\n{traceback.format_exc()}")
            continue
        plugin = getattr(m, "PLUGIN", None)
        if isinstance(plugin, LanguagePlugin):
            _PLUGINS[plugin.id] = plugin


def all_plugins() -> list[LanguagePlugin]:
    if not _PLUGINS:
        _discover()
    return list(_PLUGINS.values())


def get_plugin(plugin_id: str) -> LanguagePlugin:
    all_plugins()
    return _PLUGINS[plugin_id]


# preferred plugin when several share an extension and none is the project default
PREFERRED_FOR_EXT = {".py": "python-tk", ".pyw": "python-tk", ".ring": "ring-qt", ".bas": "vb-basic"}


def plugins_for_ext(ext: str) -> list[LanguagePlugin]:
    ext = ext.lower()
    return sorted((p for p in all_plugins() if p.code_ext.lower() == ext), key=lambda p: p.id)


def plugin_for_file(filename: str, default_id: str = "") -> LanguagePlugin | None:
    """Language of a code file, chosen by its extension. When several plugins use the
    extension (python-tk / python-qt), *default_id* (the project language) wins if it
    is one of them. Returns None for an unknown extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".pyw":
        ext = ".py"
    cands = plugins_for_ext(ext)
    if not cands:
        return None
    for p in cands:
        if p.id == default_id:
            return p
    pref = PREFERRED_FOR_EXT.get(ext)
    for p in cands:
        if p.id == pref:
            return p
    return cands[0]


def plugin_for_form(project, form_name: str) -> LanguagePlugin:
    """Plugin of a form: project.form_languages entry, else the project language."""
    lang = project.form_language(form_name) if hasattr(project, "form_language") else project.language
    try:
        return get_plugin(lang)
    except KeyError:
        return get_plugin(project.language)


def plugin_for_module(project, filename: str) -> LanguagePlugin:
    """Plugin of a code module (by extension; falls back to the project language)."""
    return plugin_for_file(filename, project.language) or get_plugin(project.language)


def language_label(plugin: LanguagePlugin) -> str:
    """Short name shown in the Solution Explorer: "Python (Tkinter)" -> "Python"."""
    name = plugin.display_name or plugin.id
    short = name.split(" (")[0].strip() or plugin.id
    if sum((p.display_name or p.id).split(" (")[0].strip() == short for p in all_plugins()) > 1:
        return name                      # ambiguous ("Python"): keep the toolkit
    return short


def code_extensions() -> list[str]:
    return sorted({p.code_ext for p in all_plugins() if p.code_ext})


__all__ = ["Completion", "LanguagePlugin", "RunSpec", "all_plugins", "get_plugin", "plugin_for_file",
           "plugin_for_form", "plugin_for_module", "plugins_for_ext", "language_label", "code_extensions"]
