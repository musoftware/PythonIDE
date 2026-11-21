"""Shared property sets of component packages: the manifest key ``commonProperties``.

Every visual control has the common properties of ``radide.controls.COMMON_PROPS`` (Name, Text, position,
colours, font, Enabled, Visible, ToolTip, TabIndex, Anchor, Dock). A package chooses which of them it has::

    "commonProperties": true                          all of them (the default)
    "commonProperties": false                         only Name and the position (Left, Top, Width, Height)
    "commonProperties": ["layout", "font", "Enabled"] Name + position + the listed sets / common properties

The sets are shared by every package, so controls that pick the same sets look the same in the Properties
window, generate the same code for them and multi-select together. ``Text`` stays governed by ``hasText``.
Pure Python (no Qt).
"""
from __future__ import annotations

SETS: dict[str, tuple[str, ...]] = {
    "position": ("Left", "Top", "Width", "Height"),
    "layout": ("Left", "Top", "Width", "Height", "Anchor", "Dock"),
    "appearance": ("BackColor", "ForeColor"),
    "font": ("FontName", "FontSize", "FontBold", "FontItalic"),
    "behavior": ("Enabled", "Visible", "ToolTip", "TabIndex"),
    "text": ("Text",),
}
ALWAYS = ("Name", "Text", "Left", "Top", "Width", "Height")


def _common_names() -> set[str]:
    from ..controls import COMMON_PROPS
    return {p.name for p in COMMON_PROPS}


def unknown_names(spec) -> list[str]:
    """Entries of a ``commonProperties`` list that are neither a set nor a common property."""
    names = {n.lower() for n in _common_names()}
    return [str(x) for x in spec if str(x).lower() not in SETS and str(x).lower() not in names]


def resolve(spec) -> tuple[str, ...] | None:
    """The common property names a manifest's ``commonProperties`` value gives (None = all)."""
    if spec is True or spec is None:
        return None
    out = list(ALWAYS)
    if isinstance(spec, list):
        by_lower = {n.lower(): n for n in _common_names()}
        for x in spec:
            key = str(x).lower()
            for n in SETS.get(key, (by_lower[key],) if key in by_lower else ()):
                if n not in out:
                    out.append(n)
    return tuple(out)


__all__ = ["SETS", "ALWAYS", "resolve", "unknown_names"]
