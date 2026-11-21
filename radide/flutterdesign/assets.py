"""Project asset manager for the Flutter designer (docs/FLUTTER_DESIGNER.md section 7.1).

Imports images, SVG, Lottie animations and font files into a Flutter project's ``assets/`` folder, registers
the folders (and the packages SVG / Lottie need) in ``pubspec.yaml``, lists what the project has, finds which
screens use an asset and makes cached thumbnails. Everything except ``thumbnail()`` is plain Python; the
thumbnail helpers import Qt lazily.

Layout inside the project (one folder per kind, each registered as a pubspec asset folder):

    assets/images/   png jpg jpeg gif webp bmp
    assets/svg/      svg            (+ flutter_svg dependency)
    assets/lottie/   json .lottie   (+ lottie dependency)
    assets/fonts/<Family>/  ttf otf (registered under flutter: fonts:, see fonts.py)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from . import codegen as CG
from . import model as M

KIND_DIRS = {"image": "assets/images", "svg": "assets/svg", "lottie": "assets/lottie", "font": "assets/fonts",
             "other": "assets/files"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
FONT_EXT = {".ttf", ".otf"}
# packages a kind needs at run time (versions available in the offline pub cache of Flutter 3.41)
KIND_PACKAGES = {"svg": ("flutter_svg", "^2.2.0"), "lottie": ("lottie", "^3.3.0")}
FILTER = ("Images (*.png *.jpg *.jpeg *.gif *.webp *.bmp);;SVG (*.svg);;Lottie (*.json *.lottie);;"
          "Fonts (*.ttf *.otf);;All files (*)")
ALL_FILTER = "Assets (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.svg *.json *.lottie *.ttf *.otf);;" + FILTER


@dataclass
class AssetInfo:
    rel: str            # project-relative path with forward slashes: "assets/images/hero.png"
    kind: str           # image | svg | lottie | font | other
    size: int = 0       # bytes

    @property
    def name(self) -> str:
        return self.rel.rsplit("/", 1)[-1]

    def dart_snippet(self) -> str:
        """How the asset is used in Dart (for a copy-to-clipboard action)."""
        if self.kind == "image":
            return f"Image.asset('{self.rel}')"
        if self.kind == "svg":
            return f"SvgPicture.asset('{self.rel}')"
        if self.kind == "lottie":
            return f"Lottie.asset('{self.rel}')"
        return f"'{self.rel}'"


def _is_lottie_json(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(4096).decode("utf-8", "ignore")
    except OSError:
        return False
    return bool(re.search(r'"layers"\s*:', head) or (re.search(r'"v"\s*:', head) and re.search(r'"fr"\s*:', head)))


def classify(path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    if ext in IMAGE_EXT:
        return "image"
    if ext == ".svg":
        return "svg"
    if ext == ".lottie" or (ext == ".json" and _is_lottie_json(p)):
        return "lottie"
    if ext in FONT_EXT:
        return "font"
    return "other"


def safe_file_name(name: str) -> str:
    """Flutter-friendly asset file name: lower snake case, ascii, keeps the extension."""
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", stem)
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_").lower() or "asset"
    return stem + ext.lower()


def _unique(folder: Path, name: str, src: Path | None = None) -> Path:
    dst = folder / name
    if not dst.exists() or (src is not None and _same_file(src, dst)):
        return dst
    stem, ext = os.path.splitext(name)
    i = 2
    while (folder / f"{stem}_{i}{ext}").exists():
        cand = folder / f"{stem}_{i}{ext}"
        if src is not None and _same_file(src, cand):
            return cand
        i += 1
    return folder / f"{stem}_{i}{ext}"


def _digest(p: Path) -> str:
    h = hashlib.sha1()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.stat().st_size == b.stat().st_size and _digest(a) == _digest(b)
    except OSError:
        return False


def ensure_dependency(pubspec_text: str, package: str, version: str) -> str:
    """Add ``package: version`` under dependencies: (idempotent)."""
    if re.search(rf"^\s+{re.escape(package)}\s*:", pubspec_text, re.M):
        return pubspec_text
    lines = pubspec_text.splitlines()
    d = next((i for i, ln in enumerate(lines) if re.match(r"^dependencies:\s*(#.*)?$", ln)), -1)
    if d < 0:
        lines += ["", "dependencies:", "  flutter:", "    sdk: flutter"]
        d = len(lines) - 3
    j = d + 1
    while j < len(lines) and (not lines[j].strip() or lines[j].startswith((" ", "\t", "#"))):
        j += 1
    while j > d + 1 and not lines[j - 1].strip():
        j -= 1
    lines.insert(j, f"  {package}: {version}")
    return "\n".join(lines) + "\n"


def register(project_folder, rels: list[str], packages: list[tuple[str, str]] | None = None) -> bool:
    """Register asset files / folders (their folders) and packages in pubspec.yaml. Returns True if changed."""
    pp = Path(project_folder) / "pubspec.yaml"
    if not pp.exists():
        return False
    text = pp.read_text(encoding="utf-8")
    new = CG.update_pubspec(text, [r for r in rels if not r.startswith("assets/fonts/")], [], False)
    for pkg, ver in packages or []:
        new = ensure_dependency(new, pkg, ver)
    if new != text:
        pp.write_text(new, encoding="utf-8")
        return True
    return False


def import_asset(project_folder, src, kind: str | None = None, name: str | None = None,
                 subdir: str | None = None, register_pubspec: bool = True) -> AssetInfo:
    """Copy ``src`` into the project's asset folder for its kind and register it. An identical file already in
    the project is reused (no duplicate copies). ``subdir`` puts it in ``assets/<kind>/<subdir>/``."""
    folder = Path(project_folder)
    src = Path(src)
    if not src.is_file():
        raise FileNotFoundError(src)
    kind = kind or classify(src)
    base = folder / KIND_DIRS.get(kind, KIND_DIRS["other"])
    if subdir:
        base = base / subdir.strip("/\\")
    base.mkdir(parents=True, exist_ok=True)
    if kind == "font":       # keep the family-style names fonts use (Poppins-Bold.ttf)
        fname = re.sub(r"[^\w.\-]+", "_", name or src.name)
    else:
        fname = safe_file_name(name or src.name)
    dst = _unique(base, fname, src)
    try:
        same = src.resolve() == dst.resolve()
    except OSError:
        same = False
    if not same and not (dst.exists() and _same_file(src, dst)):
        shutil.copy2(src, dst)
    rel = dst.relative_to(folder).as_posix()
    if register_pubspec and kind != "font":
        pk = [KIND_PACKAGES[kind]] if kind in KIND_PACKAGES else []
        register(folder, [rel], pk)
    return AssetInfo(rel, kind, dst.stat().st_size)


def import_many(project_folder, files) -> list[AssetInfo]:
    out = [import_asset(project_folder, f, register_pubspec=False) for f in files]
    pk = sorted({KIND_PACKAGES[a.kind] for a in out if a.kind in KIND_PACKAGES})
    register(project_folder, [a.rel for a in out if a.kind != "font"], pk)
    return out


def list_assets(project_folder, kind: str | None = None) -> list[AssetInfo]:
    folder = Path(project_folder)
    root = folder / "assets"
    out = []
    if root.is_dir():
        for p in sorted(root.rglob("*")):
            if p.is_file() and not p.name.startswith("."):
                k = classify(p)
                if p.suffix.lower() == ".txt" and "fonts" in p.parts:
                    continue          # font licence files
                if kind is None or k == kind:
                    out.append(AssetInfo(p.relative_to(folder).as_posix(), k, p.stat().st_size))
    return out


def asset_usages(project_folder, rel: str) -> list[tuple[str, str]]:
    """[(screen file name, node id or 'screen')] of every screen that references ``rel``."""
    out = []
    for path in M.find_screens(project_folder):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if rel in (data.get("assets") or []):
            out.append((Path(path).name, "screen"))
        scr = M.Screen(data)
        for n, *_ in scr.walk():
            if rel in json.dumps(n.get("props") or {}, ensure_ascii=False):
                out.append((Path(path).name, n["id"]))
    return out


def remove_asset(project_folder, rel: str, force: bool = False) -> bool:
    """Delete an asset file. Refuses (returns False) while a screen uses it unless ``force``."""
    if not force and asset_usages(project_folder, rel):
        return False
    p = Path(project_folder) / rel
    if p.is_file():
        p.unlink()
    return True


def use_in_screen(screen: M.Screen, rel: str) -> M.Patch:
    """Add an asset to the screen's ``assets`` list (so codegen registers it). Returns the patch."""
    cur = list(screen.data.get("assets") or [])
    if rel in cur:
        return []
    return M.set_screen(screen, "assets", cur + [rel])


def image_node(screen: M.Screen | None, rel: str, fit: str = "BoxFit.cover") -> dict:
    """A new Image.asset node for an imported image (drag from the asset list onto the canvas)."""
    return M.new_node("Image", screen, ctor="asset", props={"src": rel, "fit": fit})


def collect_screen_assets(screen: M.Screen) -> list[str]:
    """Project-relative asset paths a screen's tree references (Image.asset src, DecorationImage, AssetImage)."""
    found: list[str] = []

    def scan(v):
        if isinstance(v, dict):
            if v.get("source") == "asset" and isinstance(v.get("src"), str):
                found.append(v["src"])
            for x in v.values():
                scan(x)
        elif isinstance(v, list):
            for x in v:
                scan(x)
    for n, *_ in screen.walk():
        if n.get("type") == "Image" and n.get("ctor") == "asset" and isinstance((n.get("props") or {}).get("src"),
                                                                                str):
            found.append(n["props"]["src"])
        scan(n.get("props") or {})
    out = []
    for f in found:
        if f.startswith("assets/") and f not in out:
            out.append(f)
    return out


def sync_screen_assets(screen: M.Screen) -> M.Patch:
    """Make ``screen.assets`` list every asset the tree references (keeps extra entries)."""
    cur = list(screen.data.get("assets") or [])
    add = [a for a in collect_screen_assets(screen) if a not in cur]
    return M.set_screen(screen, "assets", cur + add) if add else []


# ------------------------------------------------------------------------------------------ thumbnails
def cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    p = Path(base) / "RADIDE" / "cache" / "flutterdesign" / "thumbs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def thumbnail(path, size: int = 96):
    """A QImage thumbnail (cached on disk by path + mtime + size). Needs a Q(Gui)Application for fonts / SVG."""
    from PyQt6.QtCore import QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPen

    p = Path(path)
    try:
        st = p.stat()
    except OSError:
        st = None
    key = hashlib.sha1(f"{p.resolve()}|{st.st_mtime_ns if st else 0}|{size}".encode()).hexdigest()
    cached = cache_dir() / f"{key}.png"
    if cached.exists():
        img = QImage(str(cached))
        if not img.isNull():
            return img
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(0, 0, 0, 0))
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    kind = classify(p) if st else "other"
    try:
        if kind == "image":
            src = QImage(str(p))
            if not src.isNull():
                sc = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation)
                painter.drawImage((size - sc.width()) // 2, (size - sc.height()) // 2, sc)
        elif kind == "svg":
            from PyQt6.QtSvg import QSvgRenderer
            r = QSvgRenderer(str(p))
            if r.isValid():
                vb = r.viewBoxF()
                w, h = (vb.width(), vb.height()) if vb.width() > 0 else (size, size)
                k = min(size / w, size / h)
                r.render(painter, QRectF((size - w * k) / 2, (size - h * k) / 2, w * k, h * k))
        elif kind == "font":
            from PyQt6.QtGui import QFontDatabase
            fid = QFontDatabase.addApplicationFont(str(p))
            fams = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            f = QFont(fams[0] if fams else "Segoe UI")
            f.setPixelSize(int(size * 0.45))
            painter.setFont(f)
            painter.setPen(QColor("#303040"))
            painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "Aa")
        else:
            color = {"lottie": "#FF00B8A9"}.get(kind, "#FF8A8FA3")
            painter.setPen(QPen(QColor(color), 2))
            painter.drawRoundedRect(QRectF(4, 4, size - 8, size - 8), 10, 10)
            f = QFont("Segoe UI")
            f.setPixelSize(max(9, size // 7))
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter,
                             "Lottie" if kind == "lottie" else (p.suffix[1:].upper() or "FILE"))
    finally:
        painter.end()
    if st:
        img.save(str(cached), "PNG")
    return img
