"""User controls (VB 2005 "UserControl"): a .form whose top-level key "kind" is "usercontrol".

A user control is designed like a form (its own design surface and code file) and declares its own
properties and events:

    "kind": "usercontrol",
    "usercontrol": {
        "properties": [{"name": "Caption", "type": "str", "default": "Address",
                        "maps": "lblTitle.Text", "description": "Title shown at the top"}],
        "events": [{"name": "Changed", "description": "The address was edited"}],
        "default_event": "Changed"
    }

Every user control of an opened project becomes a control type (CONTROL_TYPES[name]) with its declared
properties in the Properties window and its events in the Events list, shown in the Toolbox under the
project name.  It can be placed on forms and inside other user controls (nested).

Code generation (python-tk, python-qt): one class per user control in <Name>_designer.py (a tk.Frame /
QWidget) + the user's <Name>.py subclass with the handlers; forms create instances
`self.Address1 = AddressBox(master, owner=self, name="Address1")` and set the custom properties.  The user
control raises its events with `self.RaiseEvent("Changed")` -> the form's `Address1_Changed()` handler.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from .controls import CONTROL_TYPES, ControlType, PropDef

KIND = "usercontrol"
PROP_TYPES = ("str", "int", "bool", "color")
# inner-control properties a custom property can map to ("lblTitle.Text")
MAP_PROPS = ("Text", "BackColor", "ForeColor", "Enabled", "Visible", "Checked", "Value", "ToolTip")

# name -> {"path": Path, "mtime": float, "data": dict (the .form JSON)}
USER_CONTROLS: dict[str, dict] = {}
_local = threading.local()


# ====================================================================== model helpers
def is_usercontrol(form) -> bool:
    """*form*: a Form or a .form dict."""
    extra = form.get("kind") if isinstance(form, dict) else getattr(form, "extra", {}).get("kind")
    return str(extra or "").lower() == KIND


def spec_of(form) -> dict:
    """{"properties": [...], "events": [...], "default_event": str} of a user control form (or dict)."""
    raw = form.get("usercontrol") if isinstance(form, dict) else getattr(form, "extra", {}).get("usercontrol")
    raw = raw if isinstance(raw, dict) else {}
    props, events = [], []
    for p in raw.get("properties") or []:
        if isinstance(p, dict) and _ident(p.get("name")):
            t = str(p.get("type") or "str")
            props.append({"name": str(p["name"]), "type": t if t in PROP_TYPES else "str",
                          "default": _coerce(p.get("default", ""), t), "maps": str(p.get("maps") or ""),
                          "description": str(p.get("description") or "")})
    for e in raw.get("events") or []:
        if isinstance(e, dict) and _ident(e.get("name")):
            events.append({"name": str(e["name"]), "description": str(e.get("description") or "")})
    return {"properties": props, "events": events, "default_event": str(raw.get("default_event") or "")}


def set_spec(form, spec: dict) -> None:
    form.extra["kind"] = KIND
    form.extra["usercontrol"] = {"properties": list(spec.get("properties") or []),
                                 "events": list(spec.get("events") or []),
                                 "default_event": spec.get("default_event") or ""}


def _ident(s) -> bool:
    return bool(isinstance(s, str) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s))


def _coerce(value, t: str):
    if t == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    if t == "bool":
        return value if isinstance(value, bool) else str(value).strip().lower() in ("1", "true", "yes")
    return "" if value is None else str(value)


def user_types() -> set[str]:
    return set(USER_CONTROLS)


def is_user_type(type_name: str) -> bool:
    return type_name in USER_CONTROLS


def control_type_for(name: str, data: dict) -> ControlType:
    spec = spec_of(data)
    props = data.get("props", {}) if isinstance(data.get("props"), dict) else {}
    extra = [PropDef(p["name"], p["type"], p["default"],
                     p["description"] or (f"Custom property (maps to {p['maps']})." if p["maps"]
                                          else "Custom property of the user control."), (), "Custom")
             for p in spec["properties"]]
    events = [e["name"] for e in spec["events"]]
    if spec["default_event"] in events:
        events.remove(spec["default_event"])
        events.insert(0, spec["default_event"])
    try:
        size = (int(props.get("Width", 200)), int(props.get("Height", 100)))
    except (TypeError, ValueError):
        size = (200, 100)
    return ControlType(name, name, size, events, extra, has_text=False,
                       description=f"User control {name} (from {name}.form)." + (
                           f" Properties: {', '.join(p['name'] for p in spec['properties'])}."
                           if spec["properties"] else "") + (
                           f" Events: {', '.join(events)}." if events else ""))


def register(name: str, data: dict, path: Path | None = None) -> bool:
    """Make the user control *name* (its .form dict) a control type. False when the name is a built-in
    control type."""
    if not _ident(name) or (name in CONTROL_TYPES and name not in USER_CONTROLS):
        return False
    CONTROL_TYPES[name] = control_type_for(name, data)
    USER_CONTROLS[name] = {"path": Path(path) if path else None,
                           "mtime": Path(path).stat().st_mtime if path and Path(path).exists() else 0.0,
                           "data": data}
    _custom_event_help(data)
    return True


def _custom_event_help(data: dict) -> None:
    try:
        from .controls import EVENT_HELP
        for e in spec_of(data)["events"]:
            if e["description"]:
                EVENT_HELP.setdefault(e["name"], e["description"])
    except ImportError:
        pass


def unregister(name: str) -> None:
    if name in USER_CONTROLS:
        USER_CONTROLS.pop(name, None)
        CONTROL_TYPES.pop(name, None)


def register_folder(folder) -> list[str]:
    """Register every user control .form of a project folder (changed files are read again)."""
    out = []
    folder = Path(folder)
    if not folder.is_dir():
        return out
    for path in sorted(folder.glob("*.form")):
        name = path.stem
        info = USER_CONTROLS.get(name)
        try:
            mtime = path.stat().st_mtime
            if info and info.get("path") and Path(info["path"]) == path and info.get("mtime") == mtime:
                out.append(name)
                continue
            text = path.read_text(encoding="utf-8")
            if '"usercontrol"' not in text:
                continue
            data = json.loads(text)
        except (OSError, ValueError):
            continue
        if is_usercontrol(data) and register(name, data, path):
            out.append(name)
    return out


def ensure_types(d: dict, folder) -> None:
    """Called by Form.load: register the folder's user controls when *d* uses an unknown control type."""
    try:
        types = {c.get("type") for c in d.get("controls", []) if isinstance(c, dict)}
    except AttributeError:
        return
    if any(t not in CONTROL_TYPES for t in types) or any(t in USER_CONTROLS for t in types):
        register_folder(folder)


def update_from_form(form, path: Path | None = None) -> None:
    """A user control's designer changed (saved): refresh its control type."""
    if is_usercontrol(form):
        register(form.name, form.to_dict(), path)


def project_user_controls(project) -> list[str]:
    """Names of the user controls of *project* (listed forms whose .form is a user control)."""
    out = []
    for name in getattr(project, "forms", []):
        path = project.form_path(name)
        info = USER_CONTROLS.get(name)
        if info is not None and info.get("path") is not None and Path(info["path"]).resolve() == path.resolve():
            out.append(name)
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if '"usercontrol"' in text and is_usercontrol(json.loads(text)):
                out.append(name)
        except (OSError, ValueError):
            pass
    return out


def used_user_types(form) -> list[str]:
    return sorted({c.type for c in form.controls if c.type in USER_CONTROLS})


def uc_form(type_name: str):
    """The model Form of a registered user control (None if unknown)."""
    from .model import Form
    info = USER_CONTROLS.get(type_name)
    if info is None:
        return None
    try:
        return Form.from_dict(info["data"])
    except (KeyError, TypeError, ValueError):
        return None


def mapped_values(type_name: str, instance_props: dict) -> dict[str, dict]:
    """{inner control: {prop: value}} - the instance's custom property values that map to inner controls."""
    out: dict[str, dict] = {}
    info = USER_CONTROLS.get(type_name)
    if info is None:
        return out
    for p in spec_of(info["data"])["properties"]:
        target = p["maps"]
        if "." not in target:
            continue
        ctrl, prop = target.split(".", 1)
        out.setdefault(ctrl, {})[prop] = instance_props.get(p["name"], p["default"])
    return out


# ====================================================================== design-time preview
def make_uc_preview(ctrl, parent, root=None):
    """A QFrame showing the user control's own controls (custom property values applied)."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QFrame
    w = QFrame(parent)
    w.rad_uc = True
    w.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    w.setProperty("rad_root", str(root) if root else "")
    apply_uc_props(w, ctrl)
    w.show()
    return w


def apply_uc_props(w, ctrl) -> None:
    from PyQt6.QtWidgets import QWidget
    from .model import Control
    from .preview import make_preview
    p = ctrl.props
    w.setObjectName(f"rad_{ctrl.name}")
    w.setGeometry(int(p.get("Left", 0)), int(p.get("Top", 0)), max(4, int(p.get("Width", 4))),
                  max(4, int(p.get("Height", 4))))
    for child in w.findChildren(QWidget):
        if child.parent() is w:
            child.setParent(None)
            child.deleteLater()
    form = uc_form(ctrl.type)
    depth = getattr(_local, "depth", 0)
    back = p.get("BackColor") or (form.props.get("BackColor") if form is not None else "") or ""
    w.setStyleSheet(f"#{w.objectName()} {{ background-color:{back or '#ECE9D8'}; "
                    f"border:1px dotted #7f7f7f; }}")
    if form is None or depth > 6:            # unknown / recursive (A inside A): just the outline
        return
    root = w.property("rad_root") or None
    values = mapped_values(ctrl.type, p)
    mirror = bool(p.get("_RTLMirror"))         # a right-to-left (mirrored) language in the designer
    from PyQt6.QtCore import Qt
    w.setLayoutDirection(Qt.LayoutDirection.RightToLeft if mirror else Qt.LayoutDirection.LeftToRight)
    _local.depth = depth + 1
    try:
        made: dict[str, QWidget] = {}
        for c in form.ordered():
            props = dict(c.props)
            props.update(values.get(c.name, {}))
            if mirror:
                from .features.localization import mirror_props
                props = mirror_props(form, c, props)
            cc = Control(c.type, props, c.states)
            host = made.get(c.parent) if c.parent else w
            host = getattr(host, "client", host) if host is not None else w
            try:
                made[c.name] = make_preview(cc, host, Path(root) if root else None)
            except (KeyError, TypeError, ValueError):
                continue
    finally:
        _local.depth = depth
    w.setEnabled(bool(p.get("Enabled", True)))
    w.setToolTip(str(p.get("ToolTip", "")))


# ====================================================================== code generation
def _default_literals(spec: dict) -> str:
    return "{" + ", ".join(f"{p['name']!r}: {p['default']!r}" for p in spec["properties"]) + "}"


TK_UC_METHODS = '''
    # ---------------------------------------------------------------- user control
    _uc_quiet = False          # True while the hosting form is still being built

    def RaiseEvent(self, event, *args, **data):
        """Raise one of the user control's events: the form's <instance>_<event> handler runs."""
        owner = self._uc_owner
        if self._uc_quiet:
            return None
        fn = getattr(owner, f"{self._uc_name}_{event}", None) if owner is not None else None
        if fn is None:
            return None
        import inspect
        try:
            n = len(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            n = 0
        if not n:
            return fn()
        if args or not data:
            return fn(*args[:n]) if args else fn(EventArgs())
        e = EventArgs()
        for k, v in data.items():
            setattr(e, k, v)
        return fn(e)

    def _uc_get(self, ctrl, prop, default=None):
        w = getattr(self, ctrl, None)
        var = getattr(self, ctrl + "_var", None)
        try:
            if prop in ("Text", "Value", "Checked") and var is not None:
                return var.get()
            if prop == "Text" and isinstance(w, tk.Text):
                return w.get("1.0", "end-1c")
            if prop == "Text":
                return w.cget("text")
            if prop == "BackColor":
                return w.cget("bg")
            if prop == "ForeColor":
                return w.cget("fg")
        except (tk.TclError, AttributeError):
            pass
        return default

    def _uc_set(self, ctrl, prop, value):
        w = getattr(self, ctrl, None)
        if w is None:
            return
        var = getattr(self, ctrl + "_var", None)
        try:
            if prop in ("Text", "Value", "Checked") and var is not None:
                var.set(value)
            elif prop == "Text" and isinstance(w, tk.Text):
                w.delete("1.0", "end")
                w.insert("1.0", value)
            elif prop == "Text":
                w.configure(text=value)
            elif prop == "BackColor" and value:
                w.configure(bg=value)
            elif prop == "ForeColor" and value:
                w.configure(fg=value)
            elif prop == "Enabled":
                _set_enabled(w, bool(value))
            elif prop == "Visible":
                if value:
                    w.place(**self._places[ctrl])
                else:
                    w.place_forget()
            elif prop == "ToolTip":
                tips = getattr(self, "_loc_tips", {})
                if ctrl in tips:
                    tips[ctrl].text = value
                else:
                    _ToolTip(w, value)
        except (tk.TclError, KeyError):
            pass

    def _uc_changed(self, prop):
        fn = getattr(self, "{uc}_PropertyChanged", None)
        if fn is not None:
            fn(prop)
'''

QT_UC_METHODS = '''
    # ---------------------------------------------------------------- user control
    _uc_quiet = False          # True while the hosting form is still being built

    def RaiseEvent(self, event, *args, **data):
        """Raise one of the user control's events: the form's <instance>_<event> handler runs."""
        owner = self._uc_owner
        if self._uc_quiet:
            return None
        fn = getattr(owner, f"{self._uc_name}_{event}", None) if owner is not None else None
        if fn is None:
            return None
        import inspect
        try:
            n = len(inspect.signature(fn).parameters)
        except (TypeError, ValueError):
            n = 0
        if not n:
            return fn()
        if args or not data:
            return fn(*args[:n]) if args else fn(EventArgs())
        e = EventArgs()
        for k, v in data.items():
            setattr(e, k, v)
        return fn(e)

    def _uc_get(self, ctrl, prop, default=None):
        w = getattr(self, ctrl, None)
        if w is None:
            return default
        if prop == "Text":
            if hasattr(w, "toPlainText"):
                return w.toPlainText()
            if hasattr(w, "title") and not hasattr(w, "text"):
                return w.title()
            return w.text() if hasattr(w, "text") else default
        if prop == "Checked" and hasattr(w, "isChecked"):
            return w.isChecked()
        if prop == "Value" and hasattr(w, "value"):
            return w.value()
        if prop == "Enabled":
            return w.isEnabled()
        if prop == "Visible":
            return not w.isHidden()
        if prop == "ToolTip":
            return w.toolTip()
        return default

    def _uc_set(self, ctrl, prop, value):
        w = getattr(self, ctrl, None)
        if w is None:
            return
        if prop == "Text":
            if hasattr(w, "setPlainText"):
                w.setPlainText(str(value))
            elif hasattr(w, "setTitle") and not hasattr(w, "setText"):
                w.setTitle(str(value))
            elif hasattr(w, "setText"):
                w.setText(str(value))
        elif prop == "Checked" and hasattr(w, "setChecked"):
            w.setChecked(bool(value))
        elif prop == "Value" and hasattr(w, "setValue"):
            w.setValue(int(value or 0))
        elif prop in ("BackColor", "ForeColor") and value:
            rule = "background-color" if prop == "BackColor" else "color"
            w.setStyleSheet(w.styleSheet() + f" {type(w).__name__} {{ {rule}:{value}; }}")
        elif prop == "Enabled":
            w.setEnabled(bool(value))
        elif prop == "Visible":
            w.setVisible(bool(value))
        elif prop == "ToolTip":
            w.setToolTip(str(value))

    def _uc_changed(self, prop):
        fn = getattr(self, "{uc}_PropertyChanged", None)
        if fn is not None:
            fn(prop)
'''


def _property_lines(spec: dict) -> list[str]:
    out = []
    for p in spec["properties"]:
        n = p["name"]
        out += ["", "    @property", f"    def {n}(self):"]
        if p["maps"] and "." in p["maps"]:
            ctrl, prop = p["maps"].split(".", 1)
            out.append(f"        return self._uc_get({ctrl!r}, {prop!r}, self._uc_props.get({n!r}))")
        else:
            out.append(f"        return self._uc_props.get({n!r}, {p['default']!r})")
        out += ["", f"    @{n}.setter", f"    def {n}(self, value):"]
        if p["type"] == "int":
            out.append("        value = int(value)")
        elif p["type"] == "bool":
            out.append("        value = bool(value)")
        out.append(f"        self._uc_props[{n!r}] = value")
        if p["maps"] and "." in p["maps"]:
            ctrl, prop = p["maps"].split(".", 1)
            out.append(f"        self._uc_set({ctrl!r}, {prop!r}, value)")
        out.append(f"        self._uc_changed({n!r})")
    return out


def _strip_window_parts(form):
    """A copy of a user control form for the normal generator (no menu / tool strip, not a usercontrol)."""
    from .model import Form
    d = form.to_dict()
    d["controls"] = [c for c in d.get("controls", []) if c.get("type") not in ("MenuStrip", "ToolStrip")]
    d.pop("kind", None)
    f = Form.from_dict(d)
    f.extra["_uc_inner"] = True
    return f


def _tk_usercontrol(code: str, form) -> str:
    n = form.name
    spec = spec_of(form)
    fp = form.props
    lines = code.split("\n")
    try:
        start = next(i for i, s in enumerate(lines) if s.startswith("        self.root = tk.Tk()"))
        end = next(i for i, s in enumerate(lines) if s.startswith("        self._radio = tk.StringVar("))
    except StopIteration:
        return code
    bg = f", bg={fp['BackColor']!r}" if fp.get("BackColor") else ""
    init = [f"        self._uc_owner, self._uc_name = owner, name or {n!r}",
            f"        self._uc_props = {_default_literals(spec)}",
            "        self._uc_standalone = master is None",
            "        if master is None:                     # run alone: a window to test the user control",
            "            master = tk.Tk()",
            f"            master.title({n!r})",
            f"            master.geometry(\"{int(fp['Width'])}x{int(fp['Height'])}\")",
            f"        self.root = tk.Frame(master, width={int(fp['Width'])}, height={int(fp['Height'])}, bd=0, "
            f"highlightthickness=0{bg})",
            "        if self._uc_standalone:",
            "            self.root.pack(fill=\"both\", expand=True)"]
    lines[start:end] = init
    lines = [s for s in lines if "self.root.protocol(\"WM_DELETE_WINDOW\"" not in s]
    for i, s in enumerate(lines):
        if s == "    def __init__(self, master=None):":
            lines[i] = "    def __init__(self, master=None, owner=None, name=None):"
            break
    while lines and lines[-1] == "":
        lines.pop()
    lines += TK_UC_METHODS.replace("{uc}", n).rstrip("\n").split("\n")
    lines += _property_lines(spec)
    lines.append("")
    return "\n".join(lines)


def _qt_usercontrol(code: str, form) -> str:
    n = form.name
    spec = spec_of(form)
    lines = code.split("\n")
    out = []
    for s in lines:
        if s == "    def __init__(self, parent=None):":
            out.append("    def __init__(self, parent=None, owner=None, name=None):")
            continue
        if s.startswith(("        self.setWindowTitle(", "        self.setFixedSize(", "        self.setWindowFlag(",
                         "        self.setWindowState(", "        self.setWindowIcon(")):
            continue
        out.append(s)
        if s == "        super().__init__(parent)":
            out += [f"        self._uc_owner, self._uc_name = owner, name or {n!r}",
                    f"        self._uc_props = {_default_literals(spec)}",
                    "        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)"]
    while out and out[-1] == "":
        out.pop()
    out += QT_UC_METHODS.replace("{uc}", n).rstrip("\n").split("\n")
    out += _property_lines(spec)
    out.append("")
    return "\n".join(out)


def _insert_after(code: str, anchor: str, new_lines: list[str]) -> str:
    if not new_lines:
        return code
    lines = code.split("\n")
    for i, s in enumerate(lines):
        if s.startswith(anchor):
            lines[i + 1:i + 1] = new_lines
            return "\n".join(lines)
    return code


def designer_hook(plugin, form, user_code: str):
    """Called first by the python-tk / python-qt generate_designer: returns the generated code for user
    control forms, forms that use user controls and localizable forms - None = generate normally."""
    if getattr(_local, "busy", False) or form.extra.get("_uc_inner"):
        return None
    uc = is_usercontrol(form)
    used = used_user_types(form)
    try:
        from .features.localization import is_localizable
        loc = is_localizable(form)
    except ImportError:
        loc = False
    if not (uc or used or loc):
        return None
    qt = plugin.id == "python-qt"
    _local.busy = True
    try:
        src = _strip_window_parts(form) if uc else form
        code = plugin.generate_designer(src, user_code)
    finally:
        _local.busy = False
    if used:
        imports = [f"from {t} import {t}  # user control" for t in used]
        code = _insert_after(code, "from PySide6.QtWidgets import *" if qt else "from tkinter import ttk", imports)
        names = [c.name for c in form.controls if c.type in USER_CONTROLS]
        load = "        QTimer.singleShot(0, self._ev(" if qt else "        self.root.after(0, self._ev("
        lines = code.split("\n")
        for i, line in enumerate(lines):
            if line.startswith(load) and f'"{form.name}_Load"' in line:
                lines[i:i] = [f"        self.{x}._uc_quiet = False          # its events reach the form now"
                              for x in names]
                break
        code = "\n".join(lines)
    if uc:
        code = _qt_usercontrol(code, form) if qt else _tk_usercontrol(code, form)
    try:
        from .features.localization import localize_code
        code = localize_code(code, form, "qt" if qt else "tk", usercontrol=uc)
    except ImportError:
        pass
    return code


def _instance_values(info, spec: dict, p: dict) -> list[tuple[str, object]]:
    """Custom properties an instance must set: changed from the default, or mapped to an inner value
    that differs from it."""
    inner = {}
    if info is not None:
        for c in info["data"].get("controls", []):
            if isinstance(c, dict) and isinstance(c.get("props"), dict):
                inner[c["props"].get("Name")] = c["props"]
    out = []
    for prop in spec["properties"]:
        value = p.get(prop["name"], prop["default"])
        target = prop["maps"].split(".", 1) if "." in prop["maps"] else None
        design = inner.get(target[0], {}).get(target[1], prop["default"]) if target else prop["default"]
        if value != prop["default"] or value != design:
            out.append((prop["name"], value))
    return out


def tk_control_lines(plugin, c, used: set, master: str, place) -> list[str]:
    """python-tk: create one user control instance on a form."""
    p, n, t = c.props, c.name, c.type
    info = USER_CONTROLS.get(t)
    spec = spec_of(info["data"]) if info else {"properties": [], "events": []}
    out = [f"self.{n} = {t}({master}, owner=self, name={n!r})", f"self.{n}._uc_quiet = True"]
    if p.get("BackColor"):
        out.append(f"self.{n}.root.configure(bg={p['BackColor']!r})")
    for prop, value in _instance_values(info, spec, p):
        out.append(f"self.{n}.{prop} = {value!r}")
    custom = {e["name"] for e in spec["events"]}
    from .languages.python_tk import TK_SEQ
    for e in sorted(set(used) - custom):
        if e in TK_SEQ:
            out.append(plugin._bind_line(f"self.{n}.root", e, f"{n}_{e}").strip())
    if p.get("ToolTip"):
        out.append(f"_ToolTip(self.{n}.root, {p['ToolTip']!r})")
    if not p.get("Enabled", True):
        out.append(f"_set_enabled(self.{n}.root, False)")
    geo = place.tk_options() if place is not None else {
        "x": int(p["Left"]), "y": int(p["Top"]), "width": int(p["Width"]), "height": int(p["Height"])}
    geo["bordermode"] = "outside"
    out.append(f"self._places[{n!r}] = {geo!r}")
    if p.get("Visible", True):
        out.append(f"self.{n}.root.place(**self._places[{n!r}])")
    return out


def qt_control_lines(plugin, c, parent: str, used: set) -> list[str]:
    """python-qt: create one user control instance on a form."""
    p, n, t = c.props, c.name, c.type
    info = USER_CONTROLS.get(t)
    spec = spec_of(info["data"]) if info else {"properties": [], "events": []}
    out = [f"self.{n} = {t}({parent}, owner=self, name={n!r})", f"self.{n}._uc_quiet = True",
           f"self.{n}.setGeometry({int(p['Left'])}, {int(p['Top'])}, {int(p['Width'])}, {int(p['Height'])})"]
    if p.get("BackColor"):
        out.append(f"self.{n}.setStyleSheet(\"{t}Designer {{ background-color:{p['BackColor']}; }}\")")
    for prop, value in _instance_values(info, spec, p):
        out.append(f"self.{n}.{prop} = {value!r}")
    if p.get("ToolTip"):
        out.append(f"self.{n}.setToolTip({p['ToolTip']!r})")
    if not p.get("Enabled", True):
        out.append(f"self.{n}.setEnabled(False)")
    if not p.get("Visible", True):
        out.append(f"self.{n}.hide()")
    custom = {e["name"] for e in spec["events"]}
    out += plugin._filter_ctrl(c, set(used) - custom)
    return out


# ====================================================================== new user control files
def new_code(plugin_id: str, name: str) -> str:
    """The user's code file of a new user control."""
    if plugin_id == "python-qt":
        return (f"import sys\n\n"
                f"from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: F401\n\n"
                f"from {name}_designer import {name}Designer, EventArgs  # noqa: F401\n\n\n"
                f"class {name}({name}Designer):\n"
                f"    \"\"\"User control: write its event handlers here.\n"
                f"    Raise its own events with self.RaiseEvent(\"EventName\") - the form that hosts it\n"
                f"    gets <instance>_EventName(). Custom properties are declared in the designer\n"
                f"    (Project > User Control Properties and Events).\"\"\"\n\n"
                f"    def {name}_Load(self):\n"
                f"        pass\n\n\n"
                f"if __name__ == \"__main__\":      # test the user control alone\n"
                f"    app = QApplication.instance() or QApplication(sys.argv)\n"
                f"    uc = {name}()\n"
                f"    uc.show()\n"
                f"    sys.exit(app.exec())\n")
    return (f"from {name}_designer import {name}Designer, EventArgs  # noqa: F401\n\n\n"
            f"class {name}({name}Designer):\n"
            f"    \"\"\"User control: write its event handlers here.\n"
            f"    Raise its own events with self.RaiseEvent(\"EventName\") - the form that hosts it\n"
            f"    gets <instance>_EventName(). Custom properties are declared in the designer\n"
            f"    (Project > User Control Properties and Events).\"\"\"\n\n"
            f"    def {name}_Load(self):\n"
            f"        pass\n\n\n"
            f"if __name__ == \"__main__\":      # test the user control alone\n"
            f"    {name}().show()\n")


SUPPORTED = ("python-tk", "python-qt")


def create_usercontrol(project, name: str, width: int = 240, height: int = 120):
    """Add a user control to *project* (<name>.form + code + designer files); returns the Form."""
    from .model import Form
    from .languages import get_plugin
    plugin = get_plugin(project.form_language(name) if name in project.forms else project.language)
    form = Form()
    form.props.update({"Name": name, "Text": name, "Width": int(width), "Height": int(height)})
    set_spec(form, {"properties": [], "events": [], "default_event": ""})
    path = project.form_path(name)
    form.save(path)
    code = new_code(plugin.id, name) if plugin.id in SUPPORTED else plugin.new_code(form, False)
    (project.folder / plugin.code_file(name)).write_text(code, encoding="utf-8")
    register(name, form.to_dict(), path)
    (project.folder / plugin.designer_file(name)).write_text(plugin.generate_designer(form, code),
                                                             encoding="utf-8")
    if name not in project.forms:
        project.forms.append(name)
    if not project.startup:
        project.startup = name
    project.save()
    return form


# ====================================================================== designer frame
def paint_frame(frame, p) -> bool:
    """FormFrame.paintEvent hook: a user control is drawn as a plain surface with a thin header
    (no window caption, no system buttons). Returns True when it painted."""
    form = frame.view.doc.form
    if not is_usercontrol(form):
        return False
    from PyQt6.QtCore import QRect, Qt
    from PyQt6.QtGui import QColor, QFont, QPen
    from .designer import BORDER, CAPTION, HANDLE
    r = frame.rect()
    active = frame.view.doc.selected is None
    p.fillRect(r, QColor("#F4F4F4"))
    p.fillRect(QRect(0, 0, r.width(), CAPTION + BORDER), QColor("#DDE4EE" if active else "#E8E8E8"))
    p.setPen(QColor("#2B3A55"))
    font = QFont("Segoe UI", 9, QFont.Weight.Bold)
    p.setFont(font)
    spec = spec_of(form)
    text = f"UserControl {form.name}"
    if spec["properties"] or spec["events"]:
        text += f"  ({len(spec['properties'])}P / {len(spec['events'])}E)"
    from PyQt6.QtGui import QFontMetrics
    text = QFontMetrics(font).elidedText(text, Qt.TextElideMode.ElideRight, max(20, r.width() - 16))
    p.drawText(QRect(8, BORDER, r.width() - 16, CAPTION), Qt.AlignmentFlag.AlignVCenter, text)
    frame.setToolTip(f"User control {form.name}: {len(spec['properties'])} properties, {len(spec['events'])} "
                     "events (right-click > User Control Properties and Events)")
    p.setPen(QPen(QColor("#7F7F7F"), 1, Qt.PenStyle.DashLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(r.adjusted(0, 0, -1, -1))
    if active:
        p.setPen(QColor("#000000"))
        p.setBrush(QColor("#ffffff"))
        w, h = r.width(), r.height()
        for x, y in ((w - HANDLE, h // 2), (w // 2, h - HANDLE), (w - HANDLE, h - HANDLE)):
            p.drawRect(x, y, HANDLE - 1, HANDLE - 1)
    return True
