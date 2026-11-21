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

Other language plugins (no component support yet): :func:`placeholder_form` turns package controls into
labels saying the target has no runtime, and :data:`WARNINGS` collects a message the IDE shows.
"""
from __future__ import annotations

import threading
from pathlib import Path

from . import is_component_type, is_missing, package_of

# common properties passed to a runtime class when they differ from their default
PASSED_COMMON = ("Text", "BackColor", "ForeColor", "FontName", "FontSize", "FontBold", "FontItalic", "Enabled")
WARNINGS: list[str] = []
_state = threading.local()


def begin(form, target: str) -> None:
    """A designer file is being generated: imports are written once per runtime class."""
    _state.imported = set()
    _state.target = target


def _imported() -> set:
    if not hasattr(_state, "imported"):
        _state.imported = set()
    return _state.imported


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
        have = ", ".join(sorted(k for k in pkg.targets)) or "none"
        msg = (f"{c.name}: component {c.type} has no runtime for {target} (it has: {have}) - a placeholder "
               f"label is generated")
    warn(msg)
    return msg


# ------------------------------------------------------------------ python-tk
def tk_control_lines(plugin, c, used: set, master: str, place) -> list[str]:
    p, n = c.props, c.name
    pkg = package_of(c.type)
    rt = pkg.runtime(plugin.id) if pkg is not None else None
    out: list[str] = []
    if not rt or not rt.get("file") or not rt.get("class"):
        msg = _no_runtime(c, plugin.id)
        text = f"[{c.type}]\nno {plugin.id} runtime"
        out += [f"# WARNING: {msg}",
                f"self.{n} = tk.Label({master}, text={text!r}, relief=\"groove\", bg=\"#FFF4F4\", fg=\"#A02020\")"]
        custom = set()
    else:
        cls = rt["class"]
        out += _import_lines(pkg, rt)
        out.append(f"self.{n} = {cls}({', '.join([master] + _kwargs(c))})")
        custom = _custom_events(c)
        for e in sorted(used & custom):
            out.append(_bind_line(c, n, e))
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
    rt = pkg.runtime(plugin.id) if pkg is not None else None
    out: list[str] = []
    custom: set = set()
    if not rt or not rt.get("file") or not rt.get("class"):
        msg = _no_runtime(c, plugin.id)
        out += [f"# WARNING: {msg}",
                f"self.{n} = QLabel({f'[{c.type}] no {plugin.id} runtime'!r}, {parent})",
                f"self.{n}.setStyleSheet(\"border:1px dashed #C04040; color:#A02020; background:#FFF4F4;\")",
                f"self.{n}.setAlignment(Qt.AlignmentFlag.AlignCenter)"]
    else:
        cls = rt["class"]
        out += _import_lines(pkg, rt)
        out.append(f"self.{n} = {cls}({', '.join([parent] + _kwargs(c))})")
        custom = _custom_events(c)
        for e in sorted(used & custom):
            out.append(_bind_line(c, n, e))
    out.append(f"self.{n}.setGeometry({int(p.get('Left', 0))}, {int(p.get('Top', 0))}, "
               f"{int(p.get('Width', 4))}, {int(p.get('Height', 4))})")
    if p.get("ToolTip"):
        out.append(f"self.{n}.setToolTip({p['ToolTip']!r})")
    if not p.get("Visible", True):
        out.append(f"self.{n}.hide()")
    out += plugin._filter_ctrl(c, set(used) - custom)
    return out


# ------------------------------------------------------------------ other languages
NATIVE_TARGETS = ("python-tk", "python-qt")


def form_needs_placeholders(form, target: str) -> bool:
    return target not in NATIVE_TARGETS and any(handles(c.type) for c in form.controls)


def placeholder_form(form, target: str):
    """A copy of *form* where every package control is a Label that names the missing runtime (for language
    plugins without component support). The original form is not changed."""
    from ..controls import CONTROL_TYPES
    from ..model import Control
    f = _copy(form)
    label = CONTROL_TYPES["Label"]
    new = []
    for c in f.controls:
        if not handles(c.type):
            new.append(c)
            continue
        msg = _no_runtime(c, target)
        props = label.default_props(c.name)
        for k in ("Left", "Top", "Width", "Height", "Parent", "Anchor", "Dock", "Visible", "TabIndex", "TabPage"):
            if k in c.props:
                props[k] = c.props[k]
        props["Text"] = f"[{c.type}: no {target} runtime]"
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
    if getattr(plugin, "_rad_components_wrapped", False) or plugin.id in NATIVE_TARGETS:
        return
    orig = plugin.generate_designer

    def generate_designer(form, user_code, _orig=orig, _plugin=plugin):
        if form_needs_placeholders(form, _plugin.id):
            form = placeholder_form(form, _plugin.id)
        return _orig(form, user_code)

    try:
        plugin.generate_designer = generate_designer
        plugin._rad_components_wrapped = True
    except (AttributeError, TypeError):
        pass


__all__ = ["WARNINGS", "begin", "handles", "tk_control_lines", "qt_control_lines", "placeholder_form",
           "form_needs_placeholders", "wrap_plugin", "warn"]
