"""Helpers shared by the native builders that turn .form files into real toolkit code
(dotnet_winforms: WinForms, java_native: Swing): loading the forms, the reasons a project cannot be
built natively (check()), literals and the data files copied next to the exe.

Not a builder itself (it is not listed in native.MODULES).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from ...model import Form, Project

# Blend / data features the native code generators do not translate (the bridge build keeps them)
FORM_EXTRAS = {"states": "Visual States", "storyboards": "storyboards (animations)",
               "bindings": "data bindings", "datasources": "data sources (databases)"}
MOTION_EXTRAS = ("states", "storyboards")      # played by runtimes with native_plan support (problems(motion=True))
SKIP_DATA_DIRS = {"_build", "Publish", "libs"}


def load_forms(folder: Path, project: Project, lang: str) -> list[Form]:
    return [Form.load(project.form_path(n)) for n in project.forms if project.form_language(n) == lang
            and project.form_path(n).is_file()]


def problems(folder: Path, project: Project, lang: str, supported: set[str], toolkit: str,
             code_exts: tuple[str, ...], motion: bool = False) -> list[str]:
    """Reasons the forms / project cannot be translated (an empty list = it can).

    motion=True: the builder's runtime plays radide/motion/native_plan.py (animations, storyboards, visual
    states, layout variants), so those are no reasons."""
    out: list[str] = []
    if project.kind != "app":
        out.append(f"the project is a {project.kind}, not a program")
    if not project.forms:
        out.append("the project has no forms (console programs keep the normal build)")
    missing = project.missing_forms()
    if missing:
        out.append("missing form files: " + ", ".join(missing))
    other = sorted({project.form_language(n) for n in project.forms} - {lang})
    if other:
        out.append("forms in other languages (" + ", ".join(other) + ") need the GUI Bridge")
    if project.references:
        out.append("references to other projects (" + ", ".join(project.references) + ") use the RAD Hub")
    for m in project.modules:
        if not m.lower().endswith(code_exts):
            out.append(f"module {m} is written in another language")
    for name in project.forms:
        p = project.form_path(name)
        if not p.is_file() or project.form_language(name) != lang:
            continue
        try:
            form = Form.load(p)
        except Exception as e:  # noqa: BLE001 - a broken form is a reason, not a crash
            out.append(f"{name}.form cannot be read: {e}")
            continue
        for key, what in FORM_EXTRAS.items():
            if motion and key in MOTION_EXTRAS:
                continue
            if form.extra.get(key):
                out.append(f"{name}: {what} are not translated to {toolkit}")
        if str(form.props.get("ScaleMode", "Pixel")) not in ("Pixel", ""):
            out.append(f"{name}: ScaleMode {form.props.get('ScaleMode')} (only Pixel)")
        bad: dict[str, list[str]] = {}
        for c in form.controls:
            if c.type not in supported:
                bad.setdefault(c.type, []).append(c.name)
                continue
            if (c.states or c.variants) and not motion:
                out.append(f"{name}.{c.name}: visual states / layout variants are not translated")
            if str(c.props.get("DataSource") or "").strip():
                out.append(f"{name}.{c.name}: data binding (DataSource) is not translated")
        for t, names in sorted(bad.items()):
            out.append(f"{name}: {t} ({', '.join(names[:3])}{', ...' if len(names) > 3 else ''}) "
                       f"has no {toolkit} translation yet")
    return out


def lit(s) -> str:
    """A C# / Java string literal (UTF-8 source)."""
    return json.dumps(str(s if s is not None else ""), ensure_ascii=False)


def num(v, default=0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def rgb(color: str) -> tuple[int, int, int] | None:
    c = str(color or "").strip()
    if c.startswith("#") and len(c) in (4, 7):
        if len(c) == 4:
            c = "#" + "".join(ch * 2 for ch in c[1:])
        try:
            return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        except ValueError:
            return None
    return None


def copy_data(folder: Path, dest: Path, code_exts: tuple[str, ...], out_dir: Path | None = None) -> list[str]:
    """Copy the project's data files (images, text files, folders) next to the exe."""
    copied = []
    skip_ext = {e.lower() for e in code_exts} | {".form", ".radproj", ".iss", ".spec", ".py", ".pyc", ".bak"}
    from ..build import SKIP_DIRS, SKIP_NAMES
    for p in sorted(Path(folder).iterdir()):
        if p.name.startswith((".", "_radide")) or p.name in SKIP_NAMES or p.name in SKIP_DATA_DIRS:
            continue
        if out_dir is not None and p.resolve() == Path(out_dir).resolve():
            continue
        if p.is_dir():
            if p.name in SKIP_DIRS or p.name.startswith("_"):
                continue
            shutil.copytree(p, dest / p.name, dirs_exist_ok=True)
            copied.append(p.name + "/")
        elif p.suffix.lower() not in skip_ext and not p.name.lower().endswith("_designer" + p.suffix.lower()):
            shutil.copy2(p, dest / p.name)
            copied.append(p.name)
    return copied


def fresh_dir(p: Path) -> Path:
    if p.exists():
        shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True, exist_ok=True)
    return p


def size_text(n: int) -> str:
    return f"{n / 1024:.1f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"


def dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in Path(p).rglob("*") if f.is_file())
