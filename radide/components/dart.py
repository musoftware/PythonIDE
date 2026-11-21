"""Flutter (Dart) support of component packages: phone forms and the Flutter visual designer.

A package runs in Flutter through its ``"flutter"`` target - a ``template`` with a ``widget`` expression or an
``emit`` module (docs/COMPONENTS.md section 6) - plus Dart ``files`` copied into ``lib/``.

**State object.** Every package control of a Flutter screen gets a state object named like the control
(``rate1``) so user code reads and writes its properties::

    rate1.value            // typed member per manifest property (lowerCamelCase: Value -> value, MaxStars -> maxStars)
    rate1['Value']         // by name (any property)
    rate1.value = 4;       // setting one redraws the screen

On a phone form (``radide/mobile/codegen_dart.py``) the object is a private subclass of ``RadControl``
(``_RadRatingBar``, so ``visible`` / ``enabled`` work like any control); in the Flutter designer
(``radide/flutterdesign``) it is a field of the screen's State whose setters call ``setState``.

**Template placeholders** (besides the ``{Prop}`` literals and ``{on_<Event>}`` handler calls):
``{state}`` = the state object, ``{<Prop>_live}`` = the current value of a property (``rate1.value``). A widget
that reports a new value writes it back with ``{state}['Value'] = v;`` - e.g. the RatingBar sample::

    RatingBar(value: {Value_live}, maxStars: {MaxStars_live}, onChanged: (v) {{ {state}['Value'] = v;{on_ValueChanged} }})

**Flutter designer palette.** :func:`sync_catalog` adds every installed package with a ``"flutter"`` target to
the designer's widget catalog (group "Components"): its manifest properties become inspector properties, its
events designer events, its ``designer.py`` draws the preview and the generated screen uses the template.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from . import package_of
from . import targets as _targets

# members of RadControl / Object / ChangeNotifier a typed member must not hide
_RESERVED = {"name", "text", "visible", "enabled", "backColor", "foreColor", "fontSize", "tag", "refresh",
             "setColors", "props", "dispose", "hashCode", "runtimeType", "toString", "noSuchMethod", "addListener",
             "removeListener", "notifyListeners", "hasListeners", "onChanged"}
_DART_KEYWORDS = {"abstract", "as", "assert", "async", "await", "break", "case", "catch", "class", "const",
                  "continue", "covariant", "default", "deferred", "do", "dynamic", "else", "enum", "export",
                  "extends", "extension", "external", "factory", "false", "final", "finally", "for", "get", "if",
                  "implements", "import", "in", "interface", "is", "late", "library", "mixin", "new", "null", "on",
                  "operator", "part", "required", "rethrow", "return", "set", "show", "static", "super", "switch",
                  "sync", "this", "throw", "true", "try", "typedef", "var", "void", "while", "with", "yield"}


# ------------------------------------------------------------------ package helpers
def flutter_resolution(pkg):
    """The ``"flutter"`` target entry of *pkg* when it is a template / emit (the kinds Dart hosts generate)."""
    if pkg is None or pkg.builtin:
        return None
    res = _targets.resolve(pkg, "flutter")
    return res if res.kind in ("template", "emit") else None


def has_flutter(type_name: str) -> bool:
    return flutter_resolution(package_of(type_name)) is not None


def _runtime_props(ctype) -> list:
    """The manifest properties passed to the runtime (``designOnly`` ones are not)."""
    return [d for d in ctype.extra if not (d.meta and d.meta.get("designOnly"))]


def member_name(prop: str) -> str | None:
    """Typed Dart member of a property (``MaxStars`` -> ``maxStars``), None when it would clash."""
    m = prop[:1].lower() + prop[1:]
    if not re.match(r"^[A-Za-z_]\w*$", m) or m in _RESERVED or m in _DART_KEYWORDS:
        return None
    return m


def dart_type(kind: str) -> str:
    return {"int": "int", "float": "double", "bool": "bool", "custom": "Object?", "menu": "Object?"}.get(kind,
                                                                                                        "String")


def _getter(d) -> str:
    key = _q(d.name)
    t = dart_type(d.kind)
    if t == "int":
        return f"(props[{key}] as num?)?.toInt() ?? 0"
    if t == "double":
        return f"(props[{key}] as num?)?.toDouble() ?? 0.0"
    if t == "bool":
        return f"props[{key}] == true"
    if t == "String":
        return f"props[{key}]?.toString() ?? ''"
    return f"props[{key}]"


def _q(s: str) -> str:
    from .codegen import literal
    return literal(str(s), "dart")


def dart_value(d, value) -> str:
    """Dart literal of property *d*'s *value* (ints stay ints, floats are doubles)."""
    from .codegen import literal
    t = dart_type(d.kind)
    try:
        if t == "int":
            return str(int(value))
        if t == "double":
            return repr(float(value))
        if t == "bool":
            return "true" if value else "false"
    except (TypeError, ValueError):
        pass
    if t == "Object?" and value is None:
        return "null"
    if t == "Object?" and not isinstance(value, str):
        import json
        return literal(json.dumps(value), "dart")
    return literal("" if value is None else value, "dart")


def props_map(ctype, values: dict) -> str:
    """``<String, Object?>{'Value': 3, ...}`` - the runtime properties of a control (a mutable map)."""
    items = []
    for d in _runtime_props(ctype):
        items.append(f"{_q(d.name)}: {dart_value(d, values.get(d.name, d.default))}")
    return "<String, Object?>{" + ", ".join(items) + "}"


def class_name(type_name: str) -> str:
    return f"_Rad{type_name}"


def live_placeholders(state: str, ctype) -> dict:
    """``{state}`` and ``{<Prop>_live}`` of a template (see the module doc)."""
    out = {"state": state}
    for d in _runtime_props(ctype):
        m = member_name(d.name)
        out[f"{d.name}_live"] = f"{state}.{m}" if m else f"({state}[{_q(d.name)}] as {dart_type(d.kind)})"
    return out


def state_class(ctype, host: str) -> list[str]:
    """Dart source of the private state class of a package type. *host*: ``phone`` (extends RadControl) or
    ``designer`` (a plain object calling *onChanged* - the screen's setState - after a change)."""
    cls = class_name(ctype.name)
    if host == "phone":
        L = [f"/// State of a {ctype.name} control (component package): typed members and",
             "/// control['Prop'] by name; setting one redraws the screen.",
             f"class {cls} extends RadControl {{",
             f"  {cls}(super.name, this.props);", "",
             "  /// The component's properties by name.",
             "  final Map<String, Object?> props;", "",
             "  Object? operator [](String key) => props[key];",
             "  void operator []=(String key, Object? value) {",
             "    props[key] = value;",
             "    notifyListeners();",
             "  }"]
    else:
        L = [f"/// State of a {ctype.name} widget (component package): a field of the screen;",
             "/// setting a property redraws the screen.",
             f"class {cls} {{",
             f"  {cls}(this.name, this.props, [this.onChanged]);", "",
             "  final String name;",
             "  /// The component's properties by name.",
             "  final Map<String, Object?> props;",
             "  final VoidCallback? onChanged;", "",
             "  Object? operator [](String key) => props[key];",
             "  void operator []=(String key, Object? value) {",
             "    props[key] = value;",
             "    onChanged?.call();",
             "  }"]
    for d in _runtime_props(ctype):
        m = member_name(d.name)
        if not m:
            continue
        t = dart_type(d.kind)
        L += ["", f"  {t} get {m} => {_getter(d)};", f"  set {m}({t} v) => this[{_q(d.name)}] = v;"]
    L += ["}", ""]
    return L


def dart_expr(c, fire: dict, extra: dict) -> str | None:
    """The widget expression of package control *c* from its flutter template / emit module, or None when it
    has none. *fire*: ``on_<Event>`` -> statements; *extra*: more placeholders (``state``, ``<Prop>_live``,
    ``gen``). Raises on errors in package code (callers warn)."""
    from .codegen import EmitContext, _emit_module, _fill, _flutter_plugin, _lines
    pkg = package_of(c.type)
    res = flutter_resolution(pkg)
    if res is None:
        return None
    ctx = EmitContext(_flutter_plugin(), c, res, "", {e[3:] for e, v in fire.items() if v}, dict(fire, **extra))
    ctx.lang = "dart"
    if res.kind == "template":
        return _fill(str(res.entry["template"].get("widget") or ""), ctx) or "const SizedBox()"
    r = _emit_module(pkg, str(res.entry.get("emit"))).emit(ctx)
    return str(r if isinstance(r, str) else "\n".join(_lines(r)))


def dart_files(pkg) -> list[Path]:
    """The Dart files of a package's flutter entry (``files`` of the entry and of its template)."""
    res = flutter_resolution(pkg)
    if res is None or pkg.path is None:
        return []
    tpl = res.entry.get("template") if isinstance(res.entry.get("template"), dict) else {}
    out = []
    for rel in list(res.entry.get("files") or []) + list(tpl.get("files") or []):
        p = pkg.path / str(rel)
        if p.is_file() and p not in out:
            out.append(p)
    return out


def copy_files(lib: Path, pkgs) -> list[str]:
    """Copy the Dart files of *pkgs* into the project's ``lib/`` folder; returns the written file names."""
    written = []
    for pkg in pkgs:
        for src in dart_files(pkg):
            dst = Path(lib) / src.name
            try:
                if not dst.is_file() or dst.read_bytes() != src.read_bytes():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(src, dst)
                    written.append(src.name)
            except OSError:
                continue
    return written


# ------------------------------------------------------------------ phone forms (radide/mobile/codegen_dart.py)
def phone_state(c) -> tuple[str, str] | None:
    """(class, properties map) of the state object of package control *c* on a phone form, None for other
    controls (they keep their RadControl)."""
    if not has_flutter(c.type):
        return None
    return class_name(c.type), props_map(c.ctype, c.props)


def phone_classes(controls) -> list[str]:
    """The private state classes of the package types used on a phone form (written after the form class)."""
    out: list[str] = []
    seen = set()
    for c in controls:
        if c.type in seen or not has_flutter(c.type):
            continue
        seen.add(c.type)
        out += state_class(c.ctype, "phone")
    return out


# ------------------------------------------------------------------ Flutter designer (radide/flutterdesign)
CATEGORY = "Components"
_SYNCED: set = set()            # type names this module put into the designer catalog
_LISTENING = False


def _fd_kind(d) -> str | None:
    if d.kind == "int":
        return "int"
    if d.kind == "float":
        return "double"
    if d.kind == "bool":
        return "bool"
    if d.kind == "color":
        return "color"
    if d.kind in ("custom", "menu"):
        return None
    return "string"


def to_designer_value(d, value):
    """Manifest value -> the designer's stored value (colours #RRGGBB -> #AARRGGBB)."""
    if d.kind == "color":
        s = str(value or "")
        if re.match(r"^#[0-9A-Fa-f]{6}$", s):
            return "#FF" + s[1:].upper()
        if re.match(r"^#[0-9A-Fa-f]{8}$", s):
            return s.upper()
        return None
    return value


def from_designer_value(d, value):
    """The designer's stored value -> manifest value (#FFRRGGBB -> #RRGGBB; theme colours -> the default)."""
    if d.kind == "color":
        s = str(value or "")
        if re.match(r"^#[Ff]{2}[0-9A-Fa-f]{6}$", s):
            return "#" + s[3:].upper()
        if re.match(r"^#[0-9A-Fa-f]{8}$", s):
            return s.upper()
        return d.default
    if d.kind == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return d.default
    if d.kind == "float":
        try:
            return float(value)
        except (TypeError, ValueError):
            return d.default
    return value


def sync_catalog() -> list[str]:
    """Put the installed packages that have a flutter template / emit into the Flutter designer's catalog
    (``radide.flutterdesign.model.CATALOG``, group "Components") and drop the ones no longer installed.
    Returns the component type names in the catalog."""
    global _LISTENING
    from ..flutterdesign import model as M
    from . import REGISTRY
    if not _LISTENING:
        _LISTENING = True
        REGISTRY.on_change(lambda: "radide.flutterdesign.model" in sys.modules and sync_catalog())
    REGISTRY.ensure_loaded()
    want = {}
    for pkg in REGISTRY.all(include_builtin=False):
        if flutter_resolution(pkg) is None:
            continue
        existing = M.CATALOG.get(pkg.name)
        if existing is not None and getattr(existing, "component", None) is None:
            continue                       # a Flutter widget of that name wins
        want[pkg.name] = pkg
    for name in list(_SYNCED):
        if name not in want:
            M.CATALOG.pop(name, None)
            _SYNCED.discard(name)
    from ..controls import CONTROL_TYPES
    for name, pkg in want.items():
        ct = CONTROL_TYPES.get(name)
        if ct is None:
            continue
        props = {}
        for d in _runtime_props(ct):
            kind = _fd_kind(d)
            if kind is None:
                continue
            default = to_designer_value(d, d.default)
            props[d.name] = M.PropSpec(kind, default, group=str(d.category or ""), help=d.help)
        events = {str(e["name"]): "" for e in pkg.manifest.get("events") or [] if isinstance(e, dict)
                  and e.get("name")}
        size = pkg.manifest.get("defaultSize") or [100, 30]
        spec = M.WidgetSpec(name, CATEGORY, pkg.description or pkg.display_name, props, {}, None, events,
                            needs_name=True, name_prefix=str(pkg.manifest.get("prefix") or name[:1].lower() +
                                                             name[1:]),
                            const_ctor=False, library="component",
                            template={"type": name, "props": {k: p.default for k, p in props.items()
                                                              if p.default is not None}})
        spec.component = name
        spec.default_size = (int(size[0]), int(size[1]))
        M.CATALOG[name] = spec
        _SYNCED.add(name)
    return sorted(_SYNCED)


def designer_control(n: dict, type_name: str):
    """A :class:`radide.model.Control` of a designer node (manifest property values, defaults filled)."""
    from ..controls import CONTROL_TYPES
    from ..model import Control
    ct = CONTROL_TYPES[type_name]
    stored = n.get("props") or {}
    name = str(n.get("name") or f"_{n.get('id', 'w0')}")
    props = ct.default_props(name)
    for d in _runtime_props(ct):
        if d.name in stored and not (isinstance(stored[d.name], dict)):
            props[d.name] = from_designer_value(d, stored[d.name])
    return Control(type_name, props)


def component_x(gen, n: dict, spec):
    """The generated Dart of a component node in a Flutter designer screen (``TreeGen._node`` calls it):
    registers the state field and the private class, wires the events to the screen's handlers."""
    from ..flutterdesign import codegen as CG
    name = spec.component
    pkg = package_of(name)
    c = designer_control(n, name)
    fname = c.name
    ctx = gen.ctx
    ctx.components[name] = pkg
    ctx.fields[fname] = CG.Field(fname, "late final",
                                 f"{class_name(name)}({_q(fname)}, {props_map(c.ctype, c.props)}, "
                                 f"() => setState(() {{}}))")
    fire = {}
    for ev in spec.events:
        h = (n.get("events") or {}).get(ev)
        stmt = ""
        if h:
            nav = CG._nav_action(h)
            if nav:
                if h.startswith("push:"):
                    ctx.screens_used.add(CG.MO.push_target(h) or h[5:])
                stmt = f" ({nav})();"
            else:
                gen._handler(h, "")
                stmt = f" {h}();"
        fire[f"on_{ev}"] = stmt
    try:
        code = dart_expr(c, fire, live_placeholders(fname, c.ctype))
    except Exception as e:  # noqa: BLE001 - a broken package must not break code generation
        ctx.warnings.append(f"{n.get('id')}: component {name} flutter generator failed: {type(e).__name__}: {e}")
        code = None
    if code is None:
        return CG.Raw(f"const Placeholder() /* component {name}: no flutter runtime */")
    return CG.Raw(code)


def designer_imports(components: dict) -> list[str]:
    """Relative imports of a designer screen (lib/screens/x.dart) for the package Dart files copied to lib/."""
    out = []
    for pkg in components.values():
        for p in dart_files(pkg):
            if p.suffix == ".dart" and f"../{p.name}" not in out:
                out.append(f"../{p.name}")
    return out


def designer_classes(components: dict) -> list[str]:
    from ..controls import CONTROL_TYPES
    out: list[str] = []
    for name in sorted(components):
        ct = CONTROL_TYPES.get(name)
        if ct is not None:
            out += state_class(ct, "designer")
    return out


def preview_size(type_name: str):
    """Design size of a component widget in the Flutter designer preview, None for other types."""
    from ..flutterdesign import model as M
    spec = M.CATALOG.get(type_name)
    if spec is None or getattr(spec, "component", None) is None:
        if type_name in _SYNCED or package_of(type_name) is None or not has_flutter(type_name):
            return None
        sync_catalog()
        spec = M.CATALOG.get(type_name)
        if spec is None or getattr(spec, "component", None) is None:
            return None
    return getattr(spec, "default_size", (100, 30))


def paint_preview(p, w: float, h: float, n: dict) -> None:
    """Draw a component node of the Flutter designer with its package's ``designer.py`` (``paint`` or
    ``create``), else the default renderer."""
    from PyQt6.QtCore import QRect
    from .designer import DesignContext, draw_default
    name = n.get("type", "")
    pkg = package_of(name)
    r = QRect(0, 0, max(1, int(w)), max(1, int(h)))
    try:
        c = designer_control(n, name)
    except Exception:  # noqa: BLE001
        draw_default(p, r, name, {}, missing=True)
        return
    c.props["Width"], c.props["Height"] = r.width(), r.height()
    ctx = DesignContext(c, pkg, None)
    mod = pkg.designer_module() if pkg is not None else None
    err = ""
    try:
        fn = getattr(mod, "paint", None) if mod is not None else None
        if callable(fn):
            p.save()
            try:
                fn(p, QRect(r), dict(c.props), ctx)
            finally:
                p.restore()
            return
        create = getattr(mod, "create", None) if mod is not None else None
        if callable(create):
            wdg = create(None, dict(c.props), ctx)
            apply = getattr(mod, "apply", None)
            if callable(apply):
                apply(wdg, dict(c.props), ctx)
            wdg.resize(r.width(), r.height())
            p.drawPixmap(0, 0, wdg.grab())
            wdg.deleteLater()
            return
    except Exception as e:  # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
    draw_default(p, r, name, c.props, err)


__all__ = ["flutter_resolution", "has_flutter", "member_name", "dart_type", "props_map", "live_placeholders",
           "state_class", "dart_expr", "dart_files", "copy_files", "phone_state", "phone_classes", "sync_catalog",
           "component_x", "designer_imports", "designer_classes", "preview_size", "paint_preview", "CATEGORY"]
