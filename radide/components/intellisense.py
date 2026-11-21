"""IntelliSense members of component package controls: typing ``Rating1.`` (or ``self.Rating1.`` /
``Me.Rating1.``) lists the properties, methods and events declared in the package's component.json."""
from __future__ import annotations

import re

_RX = re.compile(r"(?:\b(?:self|Me|me|this|\$this)\s*(?:\.|->)\s*)?([A-Za-z_]\w*)\s*(?:\.|->)\s*(\w*)$")


def members(type_name: str) -> list:
    """[Completion] of a package control type (empty for built-in / unknown types)."""
    from ..controls import CONTROL_TYPES
    from ..languages.base import Completion
    from . import is_component_type
    if not is_component_type(type_name):
        return []
    t = CONTROL_TYPES[type_name]
    out = []
    for d in t.prop_defs():
        if d.meta and d.meta.get("designOnly"):
            continue
        out.append(Completion(d.name, "property", f"{d.kind} - {d.help}" if d.help else d.kind))
    for m in t.methods:
        out.append(Completion(str(m["name"]), "function",
                              str(m.get("signature") or m["name"] + "()") +
                              (f" - {m['description']}" if m.get("description") else "")))
    pkg = t.package
    for e in pkg.manifest.get("events") or []:
        if isinstance(e, dict) and e.get("name"):
            out.append(Completion(str(e["name"]), "event", str(e.get("description") or "event")))
    return out


def member_completions(code: str, line: int, col: int, names: dict | None) -> list:
    """Members when the text before the cursor is ``<control>.<prefix>`` and the control is a package type."""
    if not names:
        return []
    lines = code.splitlines()
    if line >= len(lines):
        return []
    m = _RX.search(lines[line][:col])
    if not m:
        return []
    ctrl = m.group(1)
    type_name = names.get(ctrl) or next((t for n, t in names.items() if n.lower() == ctrl.lower()), None)
    if not type_name:
        return []
    prefix = m.group(2).lower()
    return [c for c in members(type_name) if c.name.lower().startswith(prefix)] if prefix else members(type_name)


def monaco_completions(editor, line: int, col: int) -> list[dict]:
    """``MonacoEditor.completion_providers`` entry (the default code editor): the same members as
    :func:`member_completions`, as Monaco items (they come before the plugin's / language server's items)."""
    from ..monaco_editor import KIND
    items = member_completions(getattr(editor, "_text", "") or "", line, col, getattr(editor, "names", None))
    return [{"label": c.name, "kind": KIND.get(c.kind, 18), "detail": c.detail or c.kind} for c in items]


__all__ = ["members", "member_completions", "monaco_completions"]
