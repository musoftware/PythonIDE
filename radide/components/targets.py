"""Code-generation targets of component packages: which runtime a language plugin uses for a package.

A package's ``targets`` maps a target id to an entry (docs/COMPONENTS.md section 6):

* ``{"native": true}``                      - the language plugin generates it itself (built-in controls);
  the per-target code of the built-ins lives in the package folder (``runtime/<target>.py``, see
  :func:`builtin_emitter`).
* ``{"file": ..., "class": ...}``           - a runtime class the generated code creates (python-tk / python-qt /
  ring-qt; ``files`` = extra files copied with it).
* ``{"emit": "runtime/<x>.py"}``            - a Python module run by the IDE at generation time: ``emit(ctx)``
  returns the lines to write (any target).
* ``{"template": {...}}``                   - declarative snippets (construction, property setters, event wiring,
  imports, helper files) with ``{name}``/``{parent}``/``{value}`` placeholders (any target).

Lookup order for the target of a language plugin (:func:`chain`): the plugin id, its toolkit family
(``python-tk`` for Tk-based plugins such as pygame, ``python-qt``, ``ring-qt``), ``python`` for every Python
toolkit, ``bridge`` for every GUI Bridge language, then the *renderer* that really draws the form - the
VB interpreter (``vb-basic``) and every GUI Bridge language (C#, Java, JavaScript, C, Go, ...) are drawn by
the IDE's Tk runtime (radide/runtimes/vbrun.py, bridge.py), so a ``python-tk`` runtime serves them too
("mapped" support) - and finally ``*``.
"""
from __future__ import annotations

from dataclasses import dataclass

# target id -> label shown in the Toolbox tooltip / Component Manager
TARGET_LABELS = {
    "python-tk": "Python (Tkinter)",
    "python-qt": "Python (PySide6)",
    "ring-qt": "Ring (RingQt)",
    "vb-basic": "VB6 / BASIC (VB runtime)",
    "bridge": "GUI Bridge languages (C#, Java, JavaScript, C, Go, ...)",
    "web": "Web (HTML/CSS/JS)",
    "flutter": "Flutter (Dart)",
    "python": "every Python toolkit",
    "*": "every target",
}
# targets listed per component (the Toolbox tooltip)
SHOWN_TARGETS = ("python-tk", "python-qt", "ring-qt", "vb-basic", "bridge", "web", "flutter")
# targets whose forms are drawn by another target's runtime
RENDERED_BY = {"vb-basic": "python-tk", "bridge": "python-tk"}


@dataclass
class Resolution:
    kind: str          # "native" | "class" | "emit" | "template" | ""  ("" = no runtime)
    entry: dict | None
    via: str = ""      # target id whose entry was used
    mapped: bool = False   # drawn by another target's runtime (vb-basic / bridge languages -> python-tk)

    def __bool__(self) -> bool:
        return bool(self.kind)


def _classes():
    try:
        from ..languages.bridgebase import BridgeLanguagePlugin
    except Exception:  # noqa: BLE001
        BridgeLanguagePlugin = None
    try:
        from ..languages.python_qt import PythonQtPlugin
    except Exception:  # noqa: BLE001
        PythonQtPlugin = None
    try:
        from ..languages.python_tk import PythonTkPlugin
    except Exception:  # noqa: BLE001
        PythonTkPlugin = None
    try:
        from ..languages.ring_qt import RingQtPlugin
    except Exception:  # noqa: BLE001
        RingQtPlugin = None
    return BridgeLanguagePlugin, PythonQtPlugin, PythonTkPlugin, RingQtPlugin


def family(plugin) -> list[str]:
    """Target ids a plugin object (or id) belongs to, most specific first (without the renderer / ``*``)."""
    if isinstance(plugin, str):
        pid = plugin
        try:
            from ..languages import get_plugin
            plugin = get_plugin(pid)
        except Exception:  # noqa: BLE001
            plugin = None
    else:
        pid = getattr(plugin, "id", "")
    out = [pid]
    bridge, qt, tk, ring = _classes()
    if plugin is not None:
        if qt is not None and isinstance(plugin, qt):
            out.append("python-qt")
        elif tk is not None and isinstance(plugin, tk):
            out.append("python-tk")
        elif ring is not None and isinstance(plugin, ring):
            out.append("ring-qt")
        if bridge is not None and isinstance(plugin, bridge):
            out.append("bridge")
    elif pid.endswith("-bridge"):
        out.append("bridge")
    if any(x.startswith("python-") for x in out):
        out.append("python")
    return list(dict.fromkeys(x for x in out if x))


def is_bridge(plugin) -> bool:
    return "bridge" in family(plugin)


def chain(plugin) -> list[tuple[str, bool]]:
    """(target id, mapped) in lookup order for a language plugin (or plugin id)."""
    own = family(plugin)
    out = [(t, False) for t in own]
    for t in own:
        r = RENDERED_BY.get(t)
        if r:
            out += [(r, True), ("python", True)]
            break
    out.append(("*", False))
    seen, res = set(), []
    for t, m in out:
        if t not in seen:
            seen.add(t)
            res.append((t, m))
    return res


def _kind(entry) -> str:
    if not isinstance(entry, dict):
        return ""
    if entry.get("native"):
        return "native"
    if entry.get("emit"):
        return "emit"
    if isinstance(entry.get("template"), dict):
        return "template"
    if entry.get("file") and entry.get("class"):
        return "class"
    return ""


def resolve(pkg, plugin) -> Resolution:
    """How *plugin* (object or id) generates a control of package *pkg*."""
    if pkg is None:
        return Resolution("", None)
    targets = pkg.targets
    for t, mapped in chain(plugin):
        entry = targets.get(t)
        kind = _kind(entry)
        if not kind:
            continue
        if mapped and kind not in ("class", "native"):
            continue          # the renderer (Tk) needs a runtime class; emitters belong to their own target
        return Resolution(kind, entry, t, mapped and t != "*")
    return Resolution("", None)


def supports(pkg, plugin) -> bool:
    return bool(resolve(pkg, plugin))


def support_table(pkg) -> list[tuple[str, str, str]]:
    """[(target id, label, how)] for the targets shown in the Toolbox tooltip; how = "" (unsupported),
    "native", "runtime", "generator", "template" or "via python-tk"."""
    out = []
    for t in SHOWN_TARGETS:
        r = resolve(pkg, t)
        how = ""
        if r:
            how = {"native": "native", "class": "runtime", "emit": "generator", "template": "template"}[r.kind]
            if r.mapped:
                how = f"via {r.via}"
        out.append((t, TARGET_LABELS.get(t, t), how))
    return out


def support_text(pkg) -> str:
    """Two lines for tooltips: 'Runs on: ...' / 'No runtime for: ...'."""
    rows = support_table(pkg)
    ok = [f"{lbl}" + (f" ({how})" if how.startswith("via") else "") for _t, lbl, how in rows if how]
    no = [lbl for _t, lbl, how in rows if not how]
    lines = []
    if ok:
        lines.append("Runs on: " + ", ".join(ok))
    if no:
        lines.append("No runtime for: " + ", ".join(no))
    return "\n".join(lines)


def unsupported_controls(form, plugin) -> list:
    """Controls of *form* whose component package has no runtime for *plugin* (missing packages included)."""
    from . import is_component_type, is_missing, package_of
    out = []
    for c in getattr(form, "controls", []):
        if is_missing(c.type):
            out.append(c)
        elif is_component_type(c.type) and not supports(package_of(c.type), plugin):
            out.append(c)
    return out


# ------------------------------------------------------------------ manifest members (VB runtime / bridge)
_MEMBERS: dict = {}


def member(type_name: str, lname: str):
    """("prop" | "method", real name, prop kind) of a package member named *lname* (any case), or None."""
    from . import package_of
    pkg = package_of(type_name)
    if pkg is None:
        return None
    key = (type_name, id(pkg))
    table = _MEMBERS.get(key)
    if table is None:
        table = {}
        for p in pkg.manifest.get("properties") or []:
            if isinstance(p, dict) and p.get("name"):
                from .proptypes import normalize
                table[str(p["name"]).lower()] = ("prop", str(p["name"]), normalize(str(p.get("type") or "str")))
        for m in pkg.manifest.get("methods") or []:
            if isinstance(m, dict) and m.get("name"):
                table.setdefault(str(m["name"]).lower(), ("method", str(m["name"]), ""))
        _MEMBERS.clear() if len(_MEMBERS) > 200 else None
        _MEMBERS[key] = table
    return table.get(str(lname).lower())


__all__ = ["TARGET_LABELS", "SHOWN_TARGETS", "Resolution", "family", "chain", "resolve", "supports",
           "support_table", "support_text", "unsupported_controls", "member", "is_bridge"]
