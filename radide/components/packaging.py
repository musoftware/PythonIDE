"""User control -> component package (.radcomp).

A user control of a python-tk / python-qt project (radide/usercontrols.py) becomes a package other projects
install from the Toolbox: its declared properties and events become the manifest, its code and designer
files become the runtime (with a small adapter class that follows the component runtime contract), and a
picture of it is drawn on the design surface.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from . import MANIFEST, SCHEMA_VERSION, ComponentError, _slug, export_package

_TYPE_MAP = {"str": "str", "int": "int", "bool": "bool", "color": "color"}

_ADAPTER = '''"""{name} - {target} runtime adapter: the user control {name} exported as a component package.

The form code creates ``{name}(parent, **props)`` and calls ``rad_bind(event, callback)``; the user control
raises its events with ``self.RaiseEvent("Event")`` as before.
"""
from {name} import {name} as _UC

_PROPS = {props!r}


class _Owner:
    """Receives the user control's events (RaiseEvent calls owner.<instance>_<Event>)."""

    def __init__(self, handlers):
        self._h = handlers

    def __getattr__(self, attr):
        if attr.startswith("uc_"):
            return self._h.get(attr[3:])
        raise AttributeError(attr)


class {name}(_UC):
    def __init__(self, parent=None, **props):
        self._rc_handlers = {{}}
        super().__init__(parent, owner=_Owner(self._rc_handlers), name="uc")
        for key, value in props.items():
            if key in _PROPS:
                setattr(self, key, value)
        self._uc_quiet = False

    def rad_bind(self, event, callback):
        self._rc_handlers[event] = callback
{extra}'''

_TK_EXTRA = '''
    # the Tk widget methods the generated form code uses (the user control's frame is self.root)
    def place(self, **kw):
        self.root.place(**kw)

    def place_forget(self):
        self.root.place_forget()

    def lift(self, *a):
        self.root.lift(*a)

    def bind(self, *a, **kw):
        return self.root.bind(*a, **kw)

    def configure(self, **kw):
        return self.root.configure(**kw)

    config = configure
'''

_DESIGNER = '''"""Design-surface drawing of the {name} component: a picture of the user control taken when it was
exported (scaled to the control's size)."""
from pathlib import Path

from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPixmap

_PM = None


def paint(painter, rect, props, ctx):
    global _PM
    if _PM is None:
        _PM = QPixmap(str(Path(__file__).with_name("preview.png")))
    if not _PM.isNull():
        painter.drawPixmap(QRectF(rect), _PM, QRectF(_PM.rect()))
'''


def _project_language(folder: Path, name: str) -> str:
    try:
        data = json.loads((folder / "project.radproj").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str((data.get("form_languages") or {}).get(name) or data.get("language") or "")


def build_usercontrol_package(project_folder, name: str, out_dir) -> Path:
    """Write the package folder of user control *name* into *out_dir* and return it."""
    from ..languages import get_plugin
    from ..model import Form
    from ..usercontrols import is_usercontrol, spec_of
    folder = Path(project_folder)
    form_path = folder / f"{name}.form"
    if not form_path.is_file():
        raise ComponentError(f"{form_path} not found")
    form = Form.load(form_path)
    if not is_usercontrol(form):
        raise ComponentError(f"{name} is not a user control")
    lang = _project_language(folder, name)
    if lang not in ("python-tk", "python-qt"):
        raise ComponentError(f"only python-tk / python-qt user controls can be exported (this one is {lang or '?'})")
    plugin = get_plugin(lang)
    code_file = folder / plugin.code_file(name)
    if not code_file.is_file():
        raise ComponentError(f"{code_file.name} not found")
    spec = spec_of(form)
    d = Path(out_dir) / name
    if d.exists():
        shutil.rmtree(d)
    (d / "runtime").mkdir(parents=True)
    code = code_file.read_text(encoding="utf-8")
    shutil.copyfile(code_file, d / "runtime" / code_file.name)
    (d / "runtime" / plugin.designer_file(name)).write_text(plugin.generate_designer(form, code), encoding="utf-8")
    suffix = "tk" if lang == "python-tk" else "qt"
    mod = f"{_slug(name)}_rc_{suffix}"
    (d / "runtime" / f"{mod}.py").write_text(_ADAPTER.format(
        name=name, target=lang, props=[p["name"] for p in spec["properties"]],
        extra=_TK_EXTRA if suffix == "tk" else ""), encoding="utf-8")
    props = []
    for p in spec["properties"]:
        entry = {"name": p["name"], "type": _TYPE_MAP.get(p["type"], "str"), "default": p["default"],
                 "category": "Custom"}
        if p["description"]:
            entry["description"] = p["description"]
        props.append(entry)
    events = [{"name": e["name"], **({"description": e["description"]} if e["description"] else {})}
              for e in spec["events"]]
    m = {"schemaVersion": SCHEMA_VERSION, "name": name, "version": "1.0.0",
         "description": f"User control {name} (exported from {folder.name}).", "category": "User Controls",
         "defaultSize": [int(form.props.get("Width", 200)), int(form.props.get("Height", 100))],
         "kind": "visual", "hasText": False, "properties": props, "events": events,
         "targets": {lang: {"file": f"runtime/{mod}.py", "class": name,
                            "files": [f"runtime/{code_file.name}", f"runtime/{plugin.designer_file(name)}"]}}}
    if spec["default_event"] and spec["default_event"] in [e["name"] for e in events]:
        m["defaultEvent"] = spec["default_event"]
    if _snapshot(form, form_path, d / "preview.png"):
        (d / "designer.py").write_text(_DESIGNER.format(name=name), encoding="utf-8")
        m["designer"] = "designer.py"
    (d / MANIFEST).write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return d


def _snapshot(form, form_path: Path, dest: Path) -> bool:
    """A picture of the user control (its controls drawn by the designer previews); needs a QApplication."""
    try:
        from PyQt6.QtWidgets import QApplication, QFrame
        if QApplication.instance() is None:
            return False
        from ..model import Control
        from ..preview import make_preview
        host = QFrame()
        host.resize(int(form.props.get("Width", 200)), int(form.props.get("Height", 100)))
        host.setStyleSheet(f"QFrame {{ background:{form.props.get('BackColor') or '#F0F0F0'}; }}")
        made = {}
        for c in form.ordered():
            parent = made.get(c.parent) if c.parent else host
            parent = getattr(parent, "client", parent) if parent is not None else host
            try:
                made[c.name] = make_preview(Control(c.type, dict(c.props), c.states), parent, form_path.parent)
            except Exception:  # noqa: BLE001
                continue
        ok = host.grab().save(str(dest))
        host.deleteLater()
        return bool(ok)
    except Exception:  # noqa: BLE001
        return False


def export_usercontrol(project_folder, name: str, dest_file) -> Path:
    """User control *name* of the project -> a .radcomp file."""
    with tempfile.TemporaryDirectory(prefix="radcomp_uc_") as tmp:
        d = build_usercontrol_package(project_folder, name, tmp)
        return export_package(d, dest_file)


__all__ = ["build_usercontrol_package", "export_usercontrol"]
