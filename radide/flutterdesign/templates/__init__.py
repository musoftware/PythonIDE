"""Template gallery of the Flutter designer (docs/FLUTTER_DESIGNER.md section 7.5).

Nine original screen designs (login, sign-up, onboarding, profile, dashboard, product list, product details,
settings, chat) stored as ``screens/*.fscreen.json`` with programmatic artwork in ``assets/`` (``art.py``) and
preview thumbnails in ``thumbs/``. ``build_templates.py`` regenerates the screens and ``index.json``.

    from radide.flutterdesign import templates
    for t in templates.list_templates(): print(t.id, t.title)
    scr, path = templates.instantiate("login", project_folder)           # copies art, writes screens/Login...
    scr, path = templates.instantiate("chat", folder, name="Messages", offline_fonts=True)

Plain Python (no Qt); ``offline_fonts`` downloads fonts through fonts.py.
"""
from __future__ import annotations

import copy
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .. import assets as AS
from .. import model as M

HERE = Path(__file__).resolve().parent
IMG_PREFIX = "assets/images/"


@dataclass
class TemplateInfo:
    id: str
    title: str
    category: str
    description: str
    file: Path
    thumbnail: Path | None
    assets: list[str] = field(default_factory=list)
    fonts: list[str] = field(default_factory=list)

    def load(self) -> M.Screen:
        return M.Screen.load(self.file)


def list_templates() -> list[TemplateInfo]:
    try:
        idx = json.loads((HERE / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for t in idx.get("templates", []):
        thumb = HERE / t["thumbnail"] if t.get("thumbnail") else None
        out.append(TemplateInfo(t["id"], t["title"], t.get("category", ""), t.get("description", ""),
                                HERE / t["file"], thumb if thumb and thumb.exists() else None,
                                list(t.get("assets") or []), list(t.get("fonts") or [])))
    return out


def get(template_id: str) -> TemplateInfo:
    for t in list_templates():
        if t.id == template_id:
            return t
    raise KeyError(f"no template {template_id!r}")


def categories() -> dict[str, list[TemplateInfo]]:
    out: dict[str, list[TemplateInfo]] = {}
    for t in list_templates():
        out.setdefault(t.category, []).append(t)
    return out


def _rewrite(obj, mapping: dict[str, str]):
    if isinstance(obj, dict):
        return {k: _rewrite(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rewrite(v, mapping) for v in obj]
    if isinstance(obj, str) and obj in mapping:
        return mapping[obj]
    return obj


def _unique_name(folder: Path, base: str) -> str:
    taken = {p.name[:-len(M.SCREEN_EXT)] for p in M.find_screens(folder)} if folder.exists() else set()
    for p in M.find_screens(folder) if folder.exists() else []:
        try:
            taken.add(json.loads(p.read_text(encoding="utf-8")).get("name", ""))
        except (OSError, ValueError):
            pass
    if base not in taken:
        return base
    i = 2
    while f"{base}{i}" in taken:
        i += 1
    return f"{base}{i}"


def to_asset_fonts(screen: M.Screen, entries: dict[str, dict]) -> None:
    """Switch text styles from ``googleFont`` to bundled ``fontFamily`` for the families in ``entries``
    (family -> fonts entry from fonts.add_to_project) and update the screen's ``fonts`` list (in place)."""
    def fix(v):
        if isinstance(v, dict):
            g = v.get("googleFont")
            if isinstance(g, str) and g in entries:
                v = {k: x for k, x in v.items() if k != "googleFont"}
                v["fontFamily"] = g
            return {k: fix(x) for k, x in v.items()}
        if isinstance(v, list):
            return [fix(x) for x in v]
        return v
    for n, *_ in screen.walk():
        if n.get("props"):
            n["props"] = fix(n["props"])
    fonts = [f for f in screen.data.get("fonts") or [] if f.get("family") not in entries]
    screen.data["fonts"] = fonts + list(entries.values())


def instantiate(template_id: str, project_folder, name: str | None = None, route: str | None = None,
                offline_fonts: bool = False, font_weights=(400, 500, 600, 700, 800), progress=None,
                write: bool = True) -> tuple[M.Screen, Path]:
    """Create a project screen from a template: copies its artwork into ``assets/images/`` (identical files are
    shared, clashing names get a suffix), renames the screen (unique in the project) and writes
    ``screens/<Name>.fscreen.json``. ``offline_fonts`` bundles the fonts (fonts.add_to_project) instead of
    the runtime google_fonts package. Returns (screen, path)."""
    t = get(template_id)
    folder = Path(project_folder)
    data = json.loads(t.file.read_text(encoding="utf-8"))
    base = M.class_name(name) if name else data["name"]
    new_name = _unique_name(folder, base)
    data["name"] = new_name
    data["route"] = route or ("/" + M.snake(new_name) if new_name != base or name else data["route"])
    mapping = {}
    for rel in data.get("assets") or []:
        src = HERE / "assets" / rel.rsplit("/", 1)[-1]
        if not src.exists():
            continue
        if write:
            info = AS.import_asset(folder, src, kind="image", register_pubspec=False)
            if info.rel != rel:
                mapping[rel] = info.rel
    if mapping:
        data = _rewrite(data, mapping)
    scr = M.Screen(copy.deepcopy(data))
    if offline_fonts and write:
        from .. import fonts as FN
        entries = {}
        for f in list(scr.data.get("fonts") or []):
            if f.get("source") == "google":
                entries[f["family"]] = FN.add_to_project(folder, f["family"], font_weights, progress=progress)
        to_asset_fonts(scr, entries)
    path = folder / "screens" / f"{new_name}{M.SCREEN_EXT}"
    if write:
        path.parent.mkdir(parents=True, exist_ok=True)
        scr.save(path)
        AS.register(folder, list(scr.data.get("assets") or []))
    return scr, path


def asset_path(file_name: str) -> Path:
    return HERE / "assets" / file_name


def template_ids() -> list[str]:
    return [t.id for t in list_templates()]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def install_all(project_folder, offline_fonts: bool = False, progress=None) -> list[tuple[M.Screen, Path]]:
    """Instantiate every template into a project (used by the samples)."""
    out = []
    for t in list_templates():
        out.append(instantiate(t.id, project_folder, offline_fonts=offline_fonts, progress=progress))
    return out


def copy_thumbnails(dest) -> list[Path]:
    """Copy the gallery thumbnails somewhere (docs)."""
    d = Path(dest)
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for t in list_templates():
        if t.thumbnail:
            out.append(Path(shutil.copy2(t.thumbnail, d / f"{_slug(t.id)}.png")))
    return out
