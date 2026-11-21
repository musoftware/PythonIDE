"""Code generation for component package controls.

python-tk / python-qt (``languages/python_tk.py`` / ``python_qt.py`` call :func:`tk_control_lines` /
:func:`qt_control_lines` for package types): the form imports the package's runtime class and creates it::

    self.Rating1 = StarRating(master, Value=3, MaxStars=5)        # specific + changed common properties
    self.Rating1.rad_bind("ValueChanged", self._ev("Rating1_ValueChanged"))

Runtime class contract (docs/COMPONENTS.md "Runtimes"): ``Class(parent, **props)`` accepts every property
of the manifest as a keyword (and ignores unknown ones), exposes the properties as Python attributes and
the methods by name, and calls the callbacks given to ``rad_bind(event, callback)`` when an event happens.
python-tk: the class is a Tk widget (``place`` / ``bind`` / ``configure`` work); python-qt: a QWidget.

The runtime module (``targets.<id>.file`` + ``files``) is copied into the project when the project is saved
(:func:`radide.components.copy_runtimes`); the generated import falls back to the installed package folder.

Every target goes through the registry (:mod:`radide.components.targets`): the generator asks how the form's
language creates a package control - a runtime class (python-tk / python-qt / ring-qt), an ``emit`` module or
a declarative ``template`` (any target, see :func:`run_emitter`), or the renderer's runtime for languages
whose forms the IDE draws (vb-basic and the GUI Bridge languages are drawn with the python-tk runtime).
ring-qt (:func:`ring_control_lines`) and Flutter (:func:`dart_widget`) support packages directly; web
pages can ask :func:`web_snippet`. Other plugins: :func:`placeholder_form` turns the controls without a
runtime into labels saying so, and :data:`WARNINGS` collects a message the IDE shows (design time: the
Toolbox greys the component and the Output window says why; build time: the generated code has a
``WARNING`` comment and a placeholder).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from . import is_component_type, is_missing, package_of
from . import targets as _targets

# common properties passed to a runtime class when they differ from their default
PASSED_COMMON = ("Text", "BackColor", "ForeColor", "FontName", "FontSize", "FontBold", "FontItalic", "Enabled")
WARNINGS: list[str] = []
_state = threading.local()


def begin(form, target: str) -> None:
    """A designer file is being generated: imports are written once per runtime class."""
    _state.imported = set()
    _state.target = target
    _state.imports = []


def _imported() -> set:
    if not hasattr(_state, "imported"):
        _state.imported = set()
    return _state.imported


def add_import(line: str) -> None:
    """A file-level import of a non-Python target (Ring ``load``, Dart ``import``), written once."""
    if not hasattr(_state, "imports"):
        _state.imports = []
    if line not in _state.imports:
        _state.imports.append(line)


def take_imports() -> list[str]:
    """The file-level imports collected since :func:`begin` (the generator writes them at the top)."""
    out = list(getattr(_state, "imports", []) or [])
    _state.imports = []
    return out


def resolution(c, plugin):
    """How *plugin* generates control *c* (a :class:`radide.components.targets.Resolution`)."""
    return _targets.resolve(package_of(c.type), plugin)


# ------------------------------------------------------------------ emit modules / templates (any target)
def lang_of(target: str) -> str:
    """Literal syntax of a target: python | ring | dart | js | vb | json."""
    t = str(target)
    if t.startswith("python") or t in ("pygame",):
        return "python"
    if t.startswith("ring"):
        return "ring"
    if t in ("flutter", "dart-bridge"):
        return "dart"
    if t in ("web", "javascript", "typescript", "expo"):
        return "js"
    if t in ("vb-basic",):
        return "vb"
    return "json"


def literal(value, lang: str) -> str:
    """*value* written as a literal of language *lang*."""
    if lang == "python":
        return repr(value)
    if isinstance(value, bool):
        if lang == "vb":
            return "True" if value else "False"
        return ("true" if value else "false")
    if isinstance(value, (int, float)):
        return repr(value)
    s = str(value if value is not None else "")
    if lang == "ring":
        if '"' not in s:
            return f'"{s}"'
        if "'" not in s:
            return f"'{s}'"
        return f"`{s}`"
    if lang == "vb":
        return '"' + s.replace('"', '""') + '"'
    if lang == "dart":
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$").replace("\n", "\\n") + "'"
    return json.dumps(s, ensure_ascii=False)


class EmitContext:
    """What an ``emit(ctx)`` function of a package (or a template) gets.

    ``ctx.target`` language plugin id, ``ctx.via`` target id of the entry used, ``ctx.lang`` literal syntax,
    ``ctx.control`` / ``ctx.name`` / ``ctx.type``, ``ctx.props`` (every property, defaults filled in),
    ``ctx.parent`` parent expression, ``ctx.used`` events with a handler, ``ctx.package``, ``ctx.entry`` (the
    targets entry), ``ctx.plugin`` (the language plugin object), ``ctx.lit(v)`` literal,
    ``ctx.handler(event)`` handler name, ``ctx.add_import(line)`` file-level import, ``ctx.warn(text)``.
    ``emit(ctx)`` returns a list of lines, or a dict ``{"lines": [...], "handled": [events it wired]}``.
    """

    def __init__(self, plugin, c, res, parent: str, used, extra=None):
        self.plugin = plugin
        self.target = getattr(plugin, "id", str(plugin))
        self.via = res.via
        self.entry = res.entry or {}
        self.lang = lang_of(self.via if self.via not in ("*", "bridge") else self.target)
        self.control = c
        self.name = c.name
        self.type = c.type
        self.package = package_of(c.type)
        self.parent = parent
        self.used = set(used or ())
        props = {d.name: d.default for d in c.ctype.prop_defs()}
        props.update(c.props)
        self.props = props
        self.extra = dict(extra or {})
        self._inline: list[str] = []

    def lit(self, value) -> str:
        return literal(value, self.lang)

    def handler(self, event: str) -> str:
        return f"{self.name}_{event}"

    def add_import(self, line: str) -> None:
        if self.lang == "python":          # Python: written before the control's lines, once per designer file
            if line not in _imported():
                _imported().add(line)
                self._inline.append(line)
        else:
            add_import(line)

    def warn(self, text: str) -> None:
        warn(f"{self.name}: {text}")


class _Fmt(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _fill(text: str, ctx: EmitContext, **more) -> str:
    p = ctx.props
    vals = _Fmt({"name": ctx.name, "type": ctx.type, "parent": ctx.parent,
                 "left": int(p.get("Left", 0) or 0), "top": int(p.get("Top", 0) or 0),
                 "width": int(p.get("Width", 0) or 0), "height": int(p.get("Height", 0) or 0)})
    vals.update(ctx.extra)
    for k, v in p.items():
        vals.setdefault(k, ctx.lit(v))
        vals.setdefault(k + "_raw", str(v))
    vals.update(more)
    try:
        return str(text).format_map(vals)
    except (ValueError, IndexError):
        return str(text)


def _lines(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return v.splitlines() or [""]
    return [str(x) for x in v]


def _template_lines(ctx: EmitContext, tpl: dict) -> tuple[list[str], set]:
    out: list[str] = []
    for imp in _lines(tpl.get("imports")):
        ctx.add_import(_fill(imp, ctx))
    for s in _lines(tpl.get("create")):
        out.append(_fill(s, ctx))
    setters = tpl.get("props") or {}
    if isinstance(setters, dict):
        ct = ctx.control.ctype
        names = [d.name for d in ct.extra if not (d.meta and d.meta.get("designOnly"))]
        defaults = {d.name: d.default for d in ct.prop_defs()}
        for d in ct.prop_defs():               # common properties: only when they differ from the default
            if d.name in PASSED_COMMON and d.name not in names and (d.name in setters) and \
                    ctx.props.get(d.name) != defaults.get(d.name):
                names.append(d.name)
        changed_only = tpl.get("propsMode") == "changed"
        for name in names:
            if changed_only and ctx.props.get(name) == defaults.get(name):
                continue
            pattern = setters.get(name, setters.get("*"))
            if not pattern:
                continue
            for s in _lines(pattern):
                out.append(_fill(s, ctx, Prop=name, value=ctx.lit(ctx.props.get(name)),
                                 value_raw=str(ctx.props.get(name))))
    handled = set()
    events = tpl.get("events") or {}
    if isinstance(events, dict):
        for e in sorted(ctx.used):
            pattern = events.get(e, events.get("*") if e in _custom_events(ctx.control) else None)
            if not pattern:
                continue
            handled.add(e)
            for s in _lines(pattern):
                out.append(_fill(s, ctx, event=e, handler=ctx.handler(e)))
    for s in _lines(tpl.get("after")):
        out.append(_fill(s, ctx))
    return out, handled


def _emit_module(pkg, rel: str):
    """The ``emit`` module of a package (loaded like designer.py, re-imported when it changes)."""
    if pkg is None or pkg.path is None:
        return None
    return load_module_file(pkg.path / rel, pkg.name)


_MODS: dict = {}


def load_module_file(path: Path, owner: str = "pkg"):
    """Import a package's Python file by path (cached; re-imported when the file changes). Errors raise."""
    import hashlib
    import importlib.util
    import sys
    path = Path(path)
    if not path.is_file():
        return None
    mtime = path.stat().st_mtime
    key = str(path.resolve())
    cached = _MODS.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    modname = (f"radcomp_{''.join(ch if ch.isalnum() else '_' for ch in owner).lower()}_"
               f"{''.join(ch if ch.isalnum() else '_' for ch in path.stem)}_{hashlib.md5(key.encode()).hexdigest()[:8]}")
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    _MODS[key] = (mtime, mod)
    return mod


def run_emitter(plugin, c, res, parent: str, used, extra=None) -> tuple[list[str], set]:
    """Lines (and the events they wire) of a package control whose target entry is ``emit`` or ``template``.
    Errors in package code become a ``# WARNING`` line and a warning in the Output window."""
    ctx = EmitContext(plugin, c, res, parent, used, extra)
    try:
        if res.kind == "template":
            lines, handled = _template_lines(ctx, res.entry["template"])
        else:
            mod = _emit_module(ctx.package, str(res.entry.get("emit")))
            fn = getattr(mod, "emit", None) if mod is not None else None
            if not callable(fn):
                raise RuntimeError(f"{res.entry.get('emit')}: no emit(ctx) function")
            r = fn(ctx)
            if isinstance(r, dict):
                lines, handled = _lines(r.get("lines")), set(r.get("handled") or ())
            else:
                lines, handled = _lines(r), set()
        return ctx._inline + lines, handled
    except Exception as e:  # noqa: BLE001 - a broken package must not break code generation
        msg = f"{c.name}: component {c.type} generator for {ctx.target} failed: {type(e).__name__}: {e}"
        warn(msg)
        return [_comment(ctx.lang, "WARNING: " + msg)], set()


def _comment(lang: str, text: str) -> str:
    if lang in ("dart", "js", "json"):
        return "// " + text
    if lang == "vb":
        return "' " + text
    return "# " + text


def warn(text: str) -> None:
    if text not in WARNINGS:
        WARNINGS.append(text)
        del WARNINGS[:-50]


def handles(type_name: str) -> bool:
    return is_component_type(type_name) or is_missing(type_name)


def _kwargs(c) -> list[str]:
    ct = c.ctype
    p = c.props
    out = []
    for d in ct.extra:
        if d.meta and d.meta.get("designOnly"):
            continue
        out.append(f"{d.name}={p.get(d.name, d.default)!r}")
    common = {d.name: d.default for d in ct.prop_defs() if d.name in PASSED_COMMON}
    for name, default in common.items():
        if name == "Text" and not ct.has_text:
            continue
        value = p.get(name, default)
        if value != default or name == "Text":
            out.append(f"{name}={value!r}")
    return out


def _import_lines(pkg, rt: dict) -> list[str]:
    mod = Path(rt["file"]).stem
    cls = rt["class"]
    key = (mod, cls)
    if key in _imported():
        return []
    _imported().add(key)
    runtime_dir = (pkg.path / Path(rt["file"]).parent).resolve() if pkg.path else Path(".")
    where = repr(str(runtime_dir))
    if pkg.source == "project" and pkg.origin:        # travels with the project: relative to the form file
        try:
            parts = runtime_dir.relative_to(Path(pkg.origin).resolve()).parts
            where = "os.path.join(os.path.dirname(os.path.abspath(__file__)), " + \
                    ", ".join(repr(x) for x in parts) + ")"
        except ValueError:
            pass
    lines = [f"try:                      # component package {pkg.name} {pkg.version}",
             f"    from {mod} import {cls}",
             "except ImportError:       # runtime not copied into the project yet: the package folder",
             "    import sys as _rc_sys"]
    if pkg.source == "user" and pkg.path is not None:   # no user-specific absolute path in the project
        try:
            from . import user_components_dir
            parts = runtime_dir.relative_to(user_components_dir(False).resolve()).parts
            lines += ["    import os as _rc_os",
                      "    _rc_dir = _rc_os.environ.get(\"RADIDE_COMPONENTS_DIR\") or _rc_os.path.join(",
                      "        _rc_os.environ.get(\"APPDATA\") or _rc_os.path.expanduser(\"~/.config\"), "
                      "\"RADIDE\", \"components\")"]
            where = "_rc_os.path.join(_rc_dir, " + ", ".join(repr(x) for x in parts) + ")"
        except ValueError:
            pass
    return lines + [f"    _rc_sys.path.append({where})",
                    f"    from {mod} import {cls}"]


def _custom_events(c) -> set[str]:
    pkg = package_of(c.type)
    if pkg is None:
        return set()
    return {str(e["name"]) for e in pkg.manifest.get("events") or [] if isinstance(e, dict) and e.get("name")}


def _bind_line(c, n: str, e: str) -> str:
    """``rad_bind`` of a package event. An event whose handler takes ``e`` (``args`` in the manifest, the same
    rule the IDE uses when it writes the handler) gets the runtime's event-args object (X, Y, Button / KeyCode,
    KeyChar / Cancel) unchanged - or an empty EventArgs if the runtime passed none; other handlers are called
    without arguments."""
    from ..controls import event_args
    h = f"{n}_{e}"
    if event_args(e):
        return (f"self.{n}.rad_bind({e!r}, lambda *a: getattr(self, {h!r}, lambda *_a: None)"
                f"(*(a[:1] or (EventArgs(),))))")
    return f"self.{n}.rad_bind({e!r}, self._ev({h!r}))"


def _no_runtime(c, target: str) -> str:
    pkg = package_of(c.type)
    if pkg is None:
        msg = f"{c.name}: component package '{c.type}' is not installed - a placeholder label is generated"
    else:
        have = ", ".join(sorted(k for k in pkg.targets if not k.startswith("__"))) or "none"
        msg = (f"{c.name}: component {c.type} has no runtime for {target} (it has: {have}) - a placeholder "
               f"label is generated")
    warn(msg)
    return msg


# ------------------------------------------------------------------ built-in controls: per-target code
def builtin_emit(target_file: str, c, g) -> bool:
    """Run the per-target code generator of a built-in control: ``runtime/<target_file>.py`` of its package
    folder (``radide/components/builtin/<Type>/runtime/python_tk.py``, ``python_qt.py``, ``ring_qt.py``)
    defines ``emit(g)``, which appends to ``g.out`` (and adds the events it wires to ``g.native``). *g* is
    the generator's state (:class:`TkGen` for python-tk; a namespace for the others). Returns False when the
    control has no such file (the generator then writes nothing type-specific)."""
    pkg = package_of(c.type)
    if pkg is None or pkg.path is None:
        return False
    mod = load_module_file(pkg.path / "runtime" / f"{target_file}.py", pkg.name)
    fn = getattr(mod, "emit", None) if mod is not None else None
    if not callable(fn):
        return False
    fn(g)
    return True


class TkGen:
    """State of the python-tk generator for one control (what ``runtime/python_tk.py`` gets)."""
    __slots__ = ("p", "n", "t", "master", "used", "out", "native", "opts", "ev", "align", "font", "colors",
                 "ANCHOR", "JUSTIFY", "split_items", "split_rows", "tree_paths")

    def __init__(self, p, n, t, master, used, out, native, opts, ev, align, font, colors, ANCHOR, JUSTIFY,
                 split_items, split_rows, tree_paths):
        self.p, self.n, self.t, self.master, self.used = p, n, t, master, used
        self.out, self.native, self.opts, self.ev, self.align = out, native, opts, ev, align
        self.font, self.colors, self.ANCHOR, self.JUSTIFY = font, colors, ANCHOR, JUSTIFY
        self.split_items, self.split_rows, self.tree_paths = split_items, split_rows, tree_paths


# ------------------------------------------------------------------ python-tk
def tk_control_lines(plugin, c, used: set, master: str, place) -> list[str]:
    p, n = c.props, c.name
    pkg = package_of(c.type)
    res = _targets.resolve(pkg, plugin)
    out: list[str] = []
    custom: set = set()
    if res.kind == "class":
        rt = res.entry
        out += _import_lines(pkg, rt)
        out.append(f"self.{n} = {rt['class']}({', '.join([master] + _kwargs(c))})")
        custom = _custom_events(c)
        for e in sorted(used & custom):
            out.append(_bind_line(c, n, e))
    elif res.kind in ("emit", "template"):
        lines, custom = run_emitter(plugin, c, res, master, used)
        out += lines
    else:
        msg = _no_runtime(c, plugin.id)
        text = f"[{c.type}]\nno {plugin.id} runtime"
        out += [f"# WARNING: {msg}",
                f"self.{n} = tk.Label({master}, text={text!r}, relief=\"groove\", bg=\"#FFF4F4\", fg=\"#A02020\")"]
    from ..languages.python_tk import TK_SEQ
    for e in sorted(set(used) - custom):
        if e in TK_SEQ:
            out.append(plugin._bind_line(f"self.{n}", e, f"{n}_{e}").strip())
    if p.get("ToolTip"):
        out.append(f"_ToolTip(self.{n}, {p['ToolTip']!r})")
    geo = place.tk_options() if place is not None else {
        "x": int(p.get("Left", 0)), "y": int(p.get("Top", 0)), "width": int(p.get("Width", 4)),
        "height": int(p.get("Height", 4))}
    geo["bordermode"] = "outside"
    out.append(f"self._places[{n!r}] = {geo!r}")
    if p.get("Visible", True):
        out.append(f"self.{n}.place(**self._places[{n!r}])")
    return out


# ------------------------------------------------------------------ python-qt
def qt_control_lines(plugin, c, parent: str, used: set) -> list[str]:
    p, n = c.props, c.name
    pkg = package_of(c.type)
    res = _targets.resolve(pkg, plugin)
    out: list[str] = []
    custom: set = set()
    if res.kind == "class":
        rt = res.entry
        out += _import_lines(pkg, rt)
        out.append(f"self.{n} = {rt['class']}({', '.join([parent] + _kwargs(c))})")
        custom = _custom_events(c)
        for e in sorted(used & custom):
            out.append(_bind_line(c, n, e))
    elif res.kind in ("emit", "template"):
        lines, custom = run_emitter(plugin, c, res, parent, used)
        out += lines
    else:
        msg = _no_runtime(c, plugin.id)
        out += [f"# WARNING: {msg}",
                f"self.{n} = QLabel({f'[{c.type}] no {plugin.id} runtime'!r}, {parent})",
                f"self.{n}.setStyleSheet(\"border:1px dashed #C04040; color:#A02020; background:#FFF4F4;\")",
                f"self.{n}.setAlignment(Qt.AlignmentFlag.AlignCenter)"]
    out.append(f"self.{n}.setGeometry({int(p.get('Left', 0))}, {int(p.get('Top', 0))}, "
               f"{int(p.get('Width', 4))}, {int(p.get('Height', 4))})")
    if p.get("ToolTip"):
        out.append(f"self.{n}.setToolTip({p['ToolTip']!r})")
    if not p.get("Visible", True):
        out.append(f"self.{n}.hide()")
    out += plugin._filter_ctrl(c, set(used) - custom)
    return out


# ------------------------------------------------------------------ ring-qt
def ring_control_lines(plugin, parent: str, c, form, user_code: str) -> list[str]:
    """RingQt code of a package control (``radide/languages/ring_qt.py`` calls it).

    Runtime class contract (``"ring-qt": {"file": "runtime/x.ring", "class": "X"}``): the generated designer
    ``load``s the file (copied next to the form when the project is saved) and writes::

        Rating1 = new StarRating(Form1)              # init(oParent)
        Rating1.setValue(3)                          # set<Prop>(value) for every property (+ changed common ones)
        Rating1.radBind("ValueChanged", "Rating1_ValueChanged()")   # Ring code run when the event happens
        Rating1.setGeometry(10, 10, 130, 26)

    so the class needs ``init(oParent)``, a ``set<Prop>`` per property, ``radBind(cEvent, cCode)`` and the
    QWidget methods the form uses (``setGeometry``, ``show``, ``hide``, ``raise``, ``setToolTip``,
    ``setEnabled``) - a subclass of a RingQt widget, or a class that forwards them to one."""
    p, n = c.props, c.name
    pkg = package_of(c.type)
    res = _targets.resolve(pkg, plugin)
    has = (lambda h: plugin.find_handler(user_code, h) >= 0) if user_code else (lambda h: False)
    used = {e for e in c.ctype.all_events() if has(f"{n}_{e}")}
    lit = lambda v: literal(v, "ring")      # noqa: E731
    out: list[str] = []
    enabled_done = False
    if res.kind == "class":
        rt = res.entry
        add_import(f'load "{Path(str(rt["file"])).name}"      # component package {pkg.name} {pkg.version}')
        out.append(f"{n} = new {rt['class']}({parent})")
        for kw in _kwargs(c):
            name, _eq, _v = kw.partition("=")
            out.append(f"{n}.set{name}({lit(c.props.get(name, _default(c, name)))})")
        enabled_done = True
        for e in sorted(used):
            out.append(f"{n}.radBind({lit(e)}, {lit(f'{n}_{e}()')})")
    elif res.kind in ("emit", "template"):
        lines, _handled = run_emitter(plugin, c, res, parent, used)
        out += lines
    else:
        msg = _no_runtime(c, plugin.id)
        out += [f"# WARNING: {msg}",
                f"{n} = new qLabel({parent})",
                f"{n}.setText({lit(f'[{c.type}] no {plugin.id} runtime')})",
                f"{n}.setStyleSheet(\"border:1px dashed #C04040; color:#A02020; background:#FFF4F4;\")",
                f"{n}.setAlignment(132)    # Qt::AlignCenter"]
    out.append(f"{n}.setGeometry({int(p.get('Left', 0))}, {int(p.get('Top', 0))}, "
               f"{int(p.get('Width', 4))}, {int(p.get('Height', 4))})")
    if p.get("ToolTip"):
        out.append(f"{n}.setToolTip({lit(p['ToolTip'])})")
    if not p.get("Enabled", True) and not enabled_done:
        out.append(f"{n}.setEnabled(false)")
    if not p.get("Visible", True):
        out.append(f"{n}.hide()")
    return out


def _default(c, name):
    for d in c.ctype.prop_defs():
        if d.name == name:
            return d.default
    return None


# ------------------------------------------------------------------ flutter (mobile/codegen_dart.py)
def dart_widget(gen, c) -> str:
    """Dart expression of a package control in a Flutter form (``"flutter"`` target: a ``template`` with a
    ``widget`` expression - ``{Prop}`` = Dart literal of a property, ``{on_<Event>}`` = the statements that
    call the event handler, ``imports`` - or ``emit(ctx)`` returning the expression; ``ctx.extra["gen"]`` is
    the Dart generator). Without a runtime: a labelled placeholder box and a warning."""
    from . import dart as _dart
    pkg = package_of(c.type)
    res = _targets.resolve(pkg, "flutter")
    events = sorted(set(c.ctype.all_events()))
    fire = {}
    for e in events:
        try:
            fire[f"on_{e}"] = gen.fire(c, (e,)) or ""
        except Exception:  # noqa: BLE001
            fire[f"on_{e}"] = ""
    if res.kind in ("template", "emit"):
        try:     # {state} / {<Prop>_live}: the control's state object (radide/components/dart.py)
            code = _dart.dart_expr(c, fire, dict(_dart.live_placeholders(c.name, c.ctype), gen=gen))
            if code is not None:
                return code
        except Exception as e:  # noqa: BLE001
            warn(f"{c.name}: component {c.type} flutter generator failed: {type(e).__name__}: {e}")
    else:
        _no_runtime(c, "flutter")
    text = literal(f"[{c.type}: no flutter runtime]", "dart")
    return (f"Container(decoration: BoxDecoration(color: const Color(0xFFFFF4F4), border: Border.all(color: "
            f"const Color(0xFFC04040))), alignment: Alignment.center, child: Text({text}, style: const "
            f"TextStyle(color: Color(0xFFA02020), fontSize: 11)))")


def flutter_radapp(radapp: str, project_folder, forms) -> str:
    """lib/radapp.dart of a Flutter project plus an ``export`` of every Dart file of the component packages
    the *forms* use (the files - ``files`` of the ``"flutter"`` entry or its template - are copied into
    lib/). The form designers are ``part``s of the user libraries, which import radapp.dart: the exported
    widget classes are visible there."""
    import shutil
    lib = Path(project_folder) / "lib"
    exports = []
    seen = set()
    for f in forms:
        for c in getattr(f, "controls", []):
            pkg = package_of(c.type)
            if c.type in seen or pkg is None or pkg.builtin or pkg.path is None:
                continue
            seen.add(c.type)
            res = _targets.resolve(pkg, "flutter")
            if res.kind not in ("template", "emit"):
                continue
            tpl = res.entry.get("template") if isinstance(res.entry.get("template"), dict) else {}
            for rel in list(res.entry.get("files") or []) + list(tpl.get("files") or []):
                src = pkg.path / str(rel)
                if not src.is_file():
                    continue
                dst = lib / src.name
                try:
                    if not dst.is_file() or dst.read_bytes() != src.read_bytes():
                        lib.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(src, dst)
                except OSError:
                    continue
                if src.suffix == ".dart":
                    exports.append(f"export '{src.name}';      // component package {pkg.name} {pkg.version}")
    if not exports:
        return radapp
    lines = radapp.split("\n")
    at = 0
    for i, s in enumerate(lines):
        if s.startswith(("import ", "export ", "library ")):
            at = i + 1
    return "\n".join(lines[:at] + exports + lines[at:])


def _flutter_plugin():
    try:
        from ..languages import get_plugin
        return get_plugin("flutter")
    except Exception:  # noqa: BLE001
        return "flutter"


def insert_imports(text: str, imports: list[str], marker: str = "import ") -> str:
    """Put file-level *imports* after the last line starting with *marker* (or at the top)."""
    if not imports:
        return text
    lines = text.split("\n")
    at = 0
    for i, s in enumerate(lines):
        if s.startswith(marker):
            at = i + 1
    new = [s for s in imports if s not in lines]
    return "\n".join(lines[:at] + new + lines[at:])


# ------------------------------------------------------------------ web pages
def web_snippet(c) -> dict:
    """``{"html": ..., "css": ..., "js": ..., "files": [...]}`` of a package control for a web page
    (``"web"`` target: a ``template`` with ``html`` / ``css`` / ``js`` strings or ``emit(ctx)`` returning
    that dict). Without a runtime: a placeholder ``<div>`` and a warning."""
    pkg = package_of(c.type)
    res = _targets.resolve(pkg, "web")
    if res.kind in ("template", "emit"):
        ctx = EmitContext("web", c, res, "", set())
        ctx.lang = "js"
        try:
            if res.kind == "template":
                tpl = res.entry["template"]
                return {k: _fill("\n".join(_lines(tpl.get(k))), ctx) for k in ("html", "css", "js")} | {
                    "files": [str(x) for x in tpl.get("files") or res.entry.get("files") or []]}
            r = _emit_module(pkg, str(res.entry.get("emit"))).emit(ctx)
            return dict(r) if isinstance(r, dict) else {"html": str(r), "css": "", "js": "", "files": []}
        except Exception as e:  # noqa: BLE001
            warn(f"{c.name}: component {c.type} web generator failed: {type(e).__name__}: {e}")
    else:
        _no_runtime(c, "web")
    import html as _html
    return {"html": f'<div id="{c.name}" class="rad-missing" style="border:1px dashed #C04040;color:#A02020">'
                    f'{_html.escape(f"[{c.type}: no web runtime]")}</div>', "css": "", "js": "", "files": []}


# ------------------------------------------------------------------ other languages
# plugins (and their subclasses: pygame / arcade are Tk, ring-game is RingQt) that generate package controls
NATIVE_TARGETS = ("python-tk", "python-qt", "ring-qt", "flutter")


def is_native(plugin) -> bool:
    return any(t in NATIVE_TARGETS for t in _targets.family(plugin))


def form_needs_placeholders(form, target) -> bool:
    """True when a plugin without its own package support (*target*: plugin or id) gets a control that has no
    runtime for it. Controls drawn by the renderer (vb-basic and the GUI Bridge languages draw with python-tk)
    are kept."""
    if is_native(target):
        return False
    return any(handles(c.type) and not resolution(c, target) for c in form.controls)


def placeholder_form(form, target):
    """A copy of *form* where every package control without a runtime for *target* is a Label that names the
    missing runtime (for language plugins without component support). The original form is not changed."""
    from ..controls import CONTROL_TYPES
    from ..model import Control
    tid = getattr(target, "id", target)
    f = _copy(form)
    label = CONTROL_TYPES["Label"]
    new = []
    for c in f.controls:
        if not handles(c.type) or resolution(c, target):
            new.append(c)
            continue
        msg = _no_runtime(c, tid)
        props = label.default_props(c.name)
        for k in ("Left", "Top", "Width", "Height", "Parent", "Anchor", "Dock", "Visible", "TabIndex", "TabPage"):
            if k in c.props:
                props[k] = c.props[k]
        props["Text"] = f"[{c.type}: no {tid} runtime]"
        props["ForeColor"] = "#A02020"
        props["ToolTip"] = msg
        new.append(Control("Label", props))
    f.controls = new
    return f


def _copy(form):
    import copy
    from ..model import Form
    f = Form()
    f.props = copy.deepcopy(form.props)
    f.controls = [type(c)(c.type, copy.deepcopy(c.props), copy.deepcopy(c.states)) for c in form.controls]
    f.extra = copy.deepcopy(form.extra)
    return f


def wrap_plugin(plugin) -> None:
    """Give a language plugin without component support placeholders instead of crashing on package types."""
    if getattr(plugin, "_rad_components_wrapped", False) or is_native(plugin):
        return
    orig = plugin.generate_designer

    def generate_designer(form, user_code, _orig=orig, _plugin=plugin):
        if form_needs_placeholders(form, _plugin):
            form = placeholder_form(form, _plugin)
        return _orig(form, user_code)

    try:
        plugin.generate_designer = generate_designer
        plugin._rad_components_wrapped = True
    except (AttributeError, TypeError):
        pass


__all__ = ["WARNINGS", "begin", "handles", "tk_control_lines", "qt_control_lines", "ring_control_lines",
           "dart_widget", "web_snippet", "placeholder_form", "form_needs_placeholders", "wrap_plugin", "warn",
           "resolution", "run_emitter", "EmitContext", "literal", "add_import", "take_imports", "insert_imports",
           "is_native", "load_module_file"]
