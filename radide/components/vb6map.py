"""VB6 .frm mapping read from the component manifests' ``"vb6"`` sections (docs/COMPONENTS.md).

::

    "vb6": {"class": "MSComctlLib.ProgressBar",            written for a new control (frm_writer)
            "library": "MSComctlLib",                       OCX library of that class ("Object =" line)
            "imports": ["mscomctllib.progressbar", ...],    VB6 / ActiveX classes imported as this control
            "approx": [...],                                the imports that are approximations (a warning)
            "properties": {"Minimum": "Min", ...}}          neutral -> VB6 name of plain integer properties

Used by radide/importers/vb6_import.py (CLASS_MAP, APPROX) and radide/foreign/frm_writer.py (NEW_CLASS). The
built-in packages give the tables; installed packages with a ``vb6`` section are added when they are loaded.
Pure Python (no Qt).
"""
from __future__ import annotations


def _packages() -> list:
    """Built-in packages first, then the installed ones registered in CONTROL_TYPES (they may add mappings)."""
    from . import builtin_packages, package_of
    pkgs = list(builtin_packages().values())
    seen = {id(p) for p in pkgs}
    try:
        from ..controls import CONTROL_TYPES
        for name in list(CONTROL_TYPES):
            pkg = package_of(name)
            if pkg is not None and id(pkg) not in seen:
                seen.add(id(pkg))
                pkgs.append(pkg)
    except ImportError:
        pass
    return pkgs


def _section(pkg) -> dict:
    v = pkg.manifest.get("vb6")
    return v if isinstance(v, dict) else {}


def import_map() -> dict[str, str]:
    """lower-case VB6 class -> control type (the first package that claims a class keeps it)."""
    out: dict[str, str] = {}
    for pkg in _packages():
        for cls in _section(pkg).get("imports") or []:
            out.setdefault(str(cls).lower(), pkg.name)
    return out


def approx_classes() -> set[str]:
    return {str(c).lower() for pkg in _packages() for c in _section(pkg).get("approx") or []}


def new_class_map() -> dict[str, str]:
    """control type -> VB6 class written for a new control."""
    return {pkg.name: str(_section(pkg)["class"]) for pkg in _packages() if _section(pkg).get("class")}


def property_name(type_name: str, prop: str) -> str | None:
    """VB6 name of a plain integer property of *type_name* (``"vb6": {"properties": {...}}``), or None."""
    from . import package_of
    pkg = package_of(type_name)
    if pkg is None:
        return None
    m = _section(pkg).get("properties") or {}
    v = m.get(prop) if isinstance(m, dict) else None
    return str(v) if v else None


__all__ = ["import_map", "approx_classes", "new_class_map", "property_name"]
