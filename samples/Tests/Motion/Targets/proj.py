"""Helpers of the slice D target samples: write a RAD project of any plugin from Form objects.

    write_project(folder, plugin_id, forms, user_code={form: text})

Forms are saved as .form, the designer files are generated with the plugin and the user code files are
written only when missing (so hand edits survive a rebuild); project-level files come from the plugin's
write_project_files (Flutter lib/main.dart + radapp.dart + radmotion.dart ..., Kivy radkivy.py, Expo
App.js / radapp.js), Ring gets _radqt.ring / _radfx.ring."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from radide.languages import get_plugin  # noqa: E402
from radide.mobile.codegen_common import ensure_types  # noqa: E402
from radide.model import Form, Project  # noqa: E402

ensure_types()


def mobile_form(name: str, device: str = "pixel_7", orientation: str = "Portrait") -> Form:
    from radide import devices
    f = Form()
    w, h = devices.safe_area_size(device, orientation)
    f.props.update(Name=name, Text=name, Width=w, Height=h, BackColor="", Device=device, Orientation=orientation,
                   Route="")
    from radide.mobile.controls import ensure_mobile_props
    ensure_mobile_props(f.props)
    return f


def add(f: Form, kind: str, name: str, x: int, y: int, w: int, h: int, parent: str = "", **props):
    c = f.add(kind, x, y, parent)
    c.props.update(Name=name, Left=x, Top=y, Width=w, Height=h, **props)
    return c


def write_project(folder: Path, plugin_id: str, forms: list, user_code: dict | None = None,
                  overwrite_user: bool = False) -> Project:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    pl = get_plugin(plugin_id)
    names = [f.name for f in forms]
    radproj = folder / "project.radproj"
    data = {"name": folder.name, "language": plugin_id, "forms": names, "startup": names[0], "modules": []}
    radproj.write_text(json.dumps(data, indent=2), encoding="utf-8")
    prj = Project.load(folder)
    for f in forms:
        (folder / f"{f.name}.form").write_text(json.dumps(f.to_dict(), indent=2), encoding="utf-8")
    for f in forms:
        code_path = folder / pl.code_file(f.name)
        code_path.parent.mkdir(parents=True, exist_ok=True)
        if overwrite_user or not code_path.exists():
            text = (user_code or {}).get(f.name) or pl.new_code(f, f.name == names[0])
            code_path.write_text(text, encoding="utf-8")
        user = code_path.read_text(encoding="utf-8")
        dpath = folder / pl.designer_file(f.name)
        dpath.parent.mkdir(parents=True, exist_ok=True)
        dpath.write_text(pl.generate_designer(Form.load(folder / f"{f.name}.form"), user), encoding="utf-8")
    if hasattr(pl, "write_project_files"):
        pl.write_project_files(prj)
    if plugin_id.startswith("ring"):
        from radide.languages.ring_qt import write_runtime
        write_runtime(folder)
    return prj
