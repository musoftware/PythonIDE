"""Project resources (VB 2005 "My Project > Resources" / .resx, kept simple and readable).

``Resources/resources.json`` in the project folder::

    {"strings": [{"name": "Greeting", "value": "Hello", "comment": ""}],
     "images":  [{"name": "Logo", "file": "logo.png", "comment": ""}],
     "icons":   [{"name": "AppIcon", "file": "app.ico", "comment": ""}],
     "files":   [{"name": "Readme", "file": "readme.txt", "comment": ""}]}

``file`` is relative to the Resources folder (files are copied there when added). Forms use resources by
their path (``Resources/logo.png`` in an Image / Icon property), so every code generator already works.
Python projects also get a generated ``resources.py`` next to the forms (like VB's ``My.Resources``)::

    import resources as R
    R.strings.Greeting            # "Hello"
    R.images.Logo                 # absolute path of Resources/logo.png
    R.photo("Logo")               # tkinter.PhotoImage (cached; .ico/.bmp/.jpg through Pillow when installed)
    R.pixmap("Logo"); R.qicon("AppIcon")      # Qt (PySide6 or PyQt6)
    R.read_text("Readme"); R.read_bytes("Readme")
"""
from __future__ import annotations

import json
import keyword
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

FOLDER = "Resources"
FILE = "resources.json"
KINDS = ("strings", "images", "icons", "files")
IMAGE_EXTS = (".png", ".gif", ".jpg", ".jpeg", ".bmp")
ICON_EXTS = (".ico", ".cur")
CODE_FILE = "resources.py"


@dataclass
class Resource:
    name: str
    value: str = ""         # strings
    file: str = ""          # images / icons / files (relative to the Resources folder)
    comment: str = ""


def safe_name(text: str, taken=()) -> str:
    n = re.sub(r"\W", "_", Path(text).stem if "." in text else text).strip("_") or "Resource"
    if n[0].isdigit():
        n = "_" + n
    if keyword.iskeyword(n):
        n += "_"
    base, i = n, 2
    low = {t.lower() for t in taken}
    while n.lower() in low:
        n = f"{base}{i}"
        i += 1
    return n


def kind_for_file(path: str | Path) -> str:
    ext = Path(path).suffix.lower()
    return "icons" if ext in ICON_EXTS else "images" if ext in IMAGE_EXTS else "files"


@dataclass
class ProjectResources:
    folder: Path                                  # the project folder
    strings: list[Resource] = field(default_factory=list)
    images: list[Resource] = field(default_factory=list)
    icons: list[Resource] = field(default_factory=list)
    files: list[Resource] = field(default_factory=list)

    @property
    def res_dir(self) -> Path:
        return Path(self.folder) / FOLDER

    @property
    def json_path(self) -> Path:
        return self.res_dir / FILE

    # ---------------------------------------------------------------- load / save
    @classmethod
    def load(cls, folder: str | Path) -> "ProjectResources":
        r = cls(Path(folder))
        p = r.json_path
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            for k in KINDS:
                items = data.get(k) or []
                setattr(r, k, [Resource(str(i.get("name", "")), str(i.get("value", "")), str(i.get("file", "")),
                                        str(i.get("comment", ""))) for i in items if isinstance(i, dict)
                               and i.get("name")])
        return r

    def to_dict(self) -> dict:
        out = {}
        for k in KINDS:
            out[k] = [{kk: vv for kk, vv in asdict(i).items() if vv or kk == "name" or
                       (kk == "value" and k == "strings")} for i in getattr(self, k)]
        return out

    def save(self, write_code: bool | None = None) -> Path:
        self.res_dir.mkdir(parents=True, exist_ok=True)
        self.json_path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if write_code is None:
            write_code = self.is_python_project()
        if write_code:
            self.write_code()
        return self.json_path

    def is_python_project(self) -> bool:
        try:
            d = json.loads((Path(self.folder) / "project.radproj").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return str(d.get("language", "")).startswith("python")

    # ---------------------------------------------------------------- items
    def all(self) -> list[tuple[str, Resource]]:
        return [(k, i) for k in KINDS for i in getattr(self, k)]

    def names(self) -> set[str]:
        return {i.name for _k, i in self.all()}

    def find(self, name: str) -> tuple[str, Resource] | None:
        return next(((k, i) for k, i in self.all() if i.name.lower() == name.lower()), None)

    def add_string(self, name: str, value: str, comment: str = "") -> Resource:
        r = Resource(safe_name(name, self.names()), value, "", comment)
        self.strings.append(r)
        return r

    def add_file(self, src: str | Path, name: str | None = None, kind: str | None = None) -> Resource:
        """Copy *src* into Resources/ (unless it is already there) and add it."""
        src = Path(src)
        self.res_dir.mkdir(parents=True, exist_ok=True)
        try:
            rel = src.resolve().relative_to(self.res_dir.resolve())
        except ValueError:
            dst = self.res_dir / src.name
            i = 2
            while dst.exists() and dst.read_bytes() != src.read_bytes():
                dst = self.res_dir / f"{src.stem}_{i}{src.suffix}"
                i += 1
            if not dst.exists():
                shutil.copy2(src, dst)
            rel = dst.relative_to(self.res_dir)
        rel_s = rel.as_posix()
        kind = kind or kind_for_file(rel_s)
        for i in getattr(self, kind):
            if i.file == rel_s:
                return i
        r = Resource(safe_name(name or rel.stem, self.names()), "", rel_s, "")
        getattr(self, kind).append(r)
        return r

    def remove(self, name: str, delete_file: bool = False) -> bool:
        hit = self.find(name)
        if hit is None:
            return False
        k, r = hit
        getattr(self, k).remove(r)
        if delete_file and r.file:
            try:
                (self.res_dir / r.file).unlink()
            except OSError:
                pass
        return True

    def rename(self, old: str, new: str) -> str:
        hit = self.find(old)
        if hit is None:
            raise KeyError(old)
        new = safe_name(new, self.names() - {hit[1].name})
        hit[1].name = new
        return new

    def project_path(self, r: Resource) -> str:
        """The path a form property stores: relative to the project folder."""
        return f"{FOLDER}/{r.file}"

    def pictures(self) -> list[tuple[str, Resource]]:
        return [("images", i) for i in self.images] + [("icons", i) for i in self.icons]

    # ---------------------------------------------------------------- codegen
    def code(self) -> str:
        return generate_python(self)

    def write_code(self) -> Path:
        p = Path(self.folder) / CODE_FILE
        p.write_text(self.code(), encoding="utf-8")
        return p


def generate_python(res: ProjectResources) -> str:
    L = ['"""Project resources - generated by RAD IDE from Resources/resources.json. Do not edit:',
         'use Project > Resources in the IDE.',
         "",
         "    import resources as R",
         "    R.strings.<Name>    R.images.<Name> / R.icons.<Name> / R.files.<Name> (paths)",
         "    R.photo(name)  (tkinter)    R.pixmap(name) / R.qicon(name)  (Qt)    R.read_text(name)",
         '"""',
         "import os",
         "",
         "_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), \"Resources\")",
         "",
         ""]

    def cls(title: str, items: list[Resource], is_string: bool) -> None:
        L.append(f"class _{title}:")
        if not items:
            L.append("    pass")
        for i in items:
            if i.comment:
                L.append(f"    # {i.comment}")
            if is_string:
                L.append(f"    {i.name} = {i.value!r}")
            else:
                L.append(f"    {i.name} = os.path.join(_BASE, {i.file!r})")
        L.extend(["", ""])

    cls("Strings", res.strings, True)
    cls("Images", res.images, False)
    cls("Icons", res.icons, False)
    cls("Files", res.files, False)
    L += ["strings = _Strings()", "images = _Images()", "icons = _Icons()", "files = _Files()", "",
          "_PATHS = {" + ", ".join(f"{i.name!r}: {i.file!r}" for _k, i in res.all() if i.file) + "}",
          "_CACHE = {}", "", "",
          "def path(name):",
          "    \"\"\"Absolute path of an image / icon / file resource.\"\"\"",
          "    return os.path.join(_BASE, _PATHS[name])",
          "", "",
          "def string(name, default=\"\"):",
          "    return getattr(strings, name, default)",
          "", "",
          "def read_bytes(name):",
          "    with open(path(name), \"rb\") as f:",
          "        return f.read()",
          "", "",
          "def read_text(name, encoding=\"utf-8\"):",
          "    with open(path(name), encoding=encoding) as f:",
          "        return f.read()",
          "", "",
          "def photo(name, master=None):",
          "    \"\"\"A tkinter PhotoImage of the resource (kept alive in a cache). PNG / GIF load directly;",
          "    ICO / BMP / JPG need Pillow (pip install pillow).\"\"\"",
          "    key = (\"tk\", name)",
          "    if key not in _CACHE:",
          "        import tkinter as tk",
          "        p = path(name)",
          "        if p.lower().endswith((\".png\", \".gif\", \".ppm\", \".pgm\")):",
          "            _CACHE[key] = tk.PhotoImage(master=master, file=p)",
          "        else:",
          "            from PIL import Image, ImageTk",
          "            im = Image.open(p)",
          "            if getattr(im, \"ico\", None) is not None:",
          "                im = im.ico.getimage(max(im.ico.sizes()))",
          "            _CACHE[key] = ImageTk.PhotoImage(im, master=master)",
          "    return _CACHE[key]",
          "", "",
          "def _qtgui():",
          "    try:",
          "        from PySide6 import QtGui",
          "    except ImportError:",
          "        from PyQt6 import QtGui",
          "    return QtGui",
          "", "",
          "def pixmap(name):",
          "    return _qtgui().QPixmap(path(name))",
          "", "",
          "def qicon(name):",
          "    return _qtgui().QIcon(path(name))",
          ""]
    return "\n".join(L)


__all__ = ["ProjectResources", "Resource", "FOLDER", "FILE", "KINDS", "CODE_FILE", "kind_for_file",
           "safe_name", "generate_python"]
