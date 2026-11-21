"""Google Fonts for designed Flutter screens, with an offline cache (docs/FLUTTER_DESIGNER.md section 7.2).

Two ways a screen can use a Google font:

* ``"source": "google"`` - the ``google_fonts`` package downloads it at run time (needs internet on the device).
* ``"source": "asset"``  - RAD IDE downloads the TTF files once into a local cache, copies the chosen weights into
  ``assets/fonts/<Family>/`` with the font's licence file and registers them under ``flutter: fonts:`` in
  pubspec.yaml, so the app works offline. Text styles then use ``"fontFamily": "<Family>"``.

Sources (all fonts in the Google Fonts library are open source - SIL Open Font License 1.1 for almost all of them,
a few Apache 2.0 / Ubuntu Font Licence; the licence file is always copied next to the fonts):

* family list: ``https://fonts.google.com/metadata/fonts`` (cached; a built-in list of popular families is used
  when offline);
* font files: static TTF instances from the Google Fonts CSS API (``fonts.googleapis.com/css2`` -> fonts.gstatic.com),
  falling back to the files of the official ``github.com/google/fonts`` repository;
* licence: ``github.com/google/fonts/<ofl|apache|ufl>/<family>/``.

Plain Python (urllib), no Qt. Network calls take a ``timeout`` and raise ``FontError`` with a readable message.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import codegen as CG
from . import model as M

METADATA_URL = "https://fonts.google.com/metadata/fonts"
CSS_URL = "https://fonts.googleapis.com/css2?{query}"
GITHUB_RAW = "https://raw.githubusercontent.com/google/fonts/main/{lic}/{dir}/{file}"
LICENSE_DIRS = (("ofl", "OFL.txt", "SIL Open Font License 1.1"), ("apache", "LICENSE.txt", "Apache License 2.0"),
                ("ufl", "UFL.txt", "Ubuntu Font Licence 1.0"))
USER_AGENT = "RADIDE-font-fetcher/1.0"       # a generic client name (no user details)
CATALOG_MAX_AGE = 14 * 24 * 3600

WEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold",
                700: "Bold", 800: "ExtraBold", 900: "Black"}
CATEGORIES = ["Sans Serif", "Serif", "Display", "Handwriting", "Monospace"]

# offline fallback: popular families (family, category, weights available, italic available)
POPULAR = [
    ("Roboto", "Sans Serif", "100-900", True), ("Open Sans", "Sans Serif", "300-800", True),
    ("Poppins", "Sans Serif", "100-900", True), ("Montserrat", "Sans Serif", "100-900", True),
    ("Lato", "Sans Serif", "100,300,400,700,900", True), ("Inter", "Sans Serif", "100-900", True),
    ("Nunito", "Sans Serif", "200-1000", True), ("Raleway", "Sans Serif", "100-900", True),
    ("Rubik", "Sans Serif", "300-900", True), ("Work Sans", "Sans Serif", "100-900", True),
    ("DM Sans", "Sans Serif", "100-1000", True), ("Manrope", "Sans Serif", "200-800", False),
    ("Plus Jakarta Sans", "Sans Serif", "200-800", True), ("Outfit", "Sans Serif", "100-900", False),
    ("Urbanist", "Sans Serif", "100-900", True), ("Quicksand", "Sans Serif", "300-700", False),
    ("Mulish", "Sans Serif", "200-1000", True), ("Ubuntu", "Sans Serif", "300,400,500,700", True),
    ("Josefin Sans", "Sans Serif", "100-700", True), ("Barlow", "Sans Serif", "100-900", True),
    ("Cairo", "Sans Serif", "200-1000", False), ("Tajawal", "Sans Serif", "200,300,400,500,700,800,900", False),
    ("Almarai", "Sans Serif", "300,400,700,800", False), ("IBM Plex Sans Arabic", "Sans Serif", "100-700", False),
    ("Noto Sans Arabic", "Sans Serif", "100-900", False), ("Noto Kufi Arabic", "Sans Serif", "100-900", False),
    ("Readex Pro", "Sans Serif", "160-700", False), ("Changa", "Sans Serif", "200-800", False),
    ("El Messiri", "Sans Serif", "400-700", False), ("Noto Naskh Arabic", "Serif", "400-700", False),
    ("Amiri", "Serif", "400,700", True), ("Playfair Display", "Serif", "400-900", True),
    ("Merriweather", "Serif", "300-900", True), ("Lora", "Serif", "400-700", True),
    ("PT Serif", "Serif", "400,700", True), ("Noto Serif", "Serif", "100-900", True),
    ("Libre Baskerville", "Serif", "400-700", True), ("Crimson Text", "Serif", "400,600,700", True),
    ("EB Garamond", "Serif", "400-800", True), ("Bebas Neue", "Display", "400", False),
    ("Lobster", "Display", "400", False), ("Righteous", "Display", "400", False),
    ("Abril Fatface", "Display", "400", False), ("Anton", "Sans Serif", "400", False),
    ("Oswald", "Sans Serif", "200-700", False), ("Comfortaa", "Display", "300-700", False),
    ("Fredoka", "Sans Serif", "300-700", False), ("Pacifico", "Handwriting", "400", False),
    ("Dancing Script", "Handwriting", "400-700", False), ("Caveat", "Handwriting", "400-700", False),
    ("Satisfy", "Handwriting", "400", False), ("Great Vibes", "Handwriting", "400", False),
    ("Roboto Mono", "Monospace", "100-700", True), ("JetBrains Mono", "Monospace", "100-800", True),
    ("Fira Code", "Monospace", "300-700", False), ("Source Code Pro", "Monospace", "200-900", True),
    ("Space Mono", "Monospace", "400,700", True), ("IBM Plex Mono", "Monospace", "100-700", True),
]


class FontError(Exception):
    pass


@dataclass
class FontFamily:
    family: str
    category: str = "Sans Serif"
    variants: list[str] = field(default_factory=lambda: ["400"])   # "400", "400i", "700" ...
    subsets: list[str] = field(default_factory=list)
    popularity: int = 9999

    @property
    def weights(self) -> list[int]:
        return sorted({int(v.rstrip("i")) for v in self.variants if v.rstrip("i").isdigit()})

    @property
    def has_italic(self) -> bool:
        return any(v.endswith("i") for v in self.variants)


@dataclass
class FontFile:
    weight: int
    style: str            # normal | italic
    path: Path            # cached file

    @property
    def file_name(self) -> str:
        return self.path.name


@dataclass
class CachedFamily:
    family: str
    folder: Path
    files: list[FontFile]
    license_file: Path | None
    license_name: str


def cache_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    p = Path(base) / "RADIDE" / "cache" / "fonts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def repo_dir(family: str) -> str:
    """google/fonts folder name: 'IBM Plex Sans Arabic' -> 'ibmplexsansarabic'."""
    return re.sub(r"[^a-z0-9]", "", family.lower())


def asset_family_dir(family: str) -> str:
    """assets/fonts/<this>/ : 'Plus Jakarta Sans' -> 'PlusJakartaSans'."""
    return re.sub(r"[^A-Za-z0-9]", "", family) or "Font"


def file_stem(family: str) -> str:
    return asset_family_dir(family)


def style_file_name(family: str, weight: int, style: str) -> str:
    """'Poppins', 700, 'italic' -> 'Poppins-BoldItalic.ttf' (Google Fonts naming)."""
    w = WEIGHT_NAMES.get(int(weight), f"W{int(weight)}")
    if style == "italic":
        w = "Italic" if w == "Regular" else w + "Italic"
    return f"{file_stem(family)}-{w}.ttf"


def _get(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise FontError(f"{url}: HTTP {e.code}") from e
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise FontError(f"cannot reach {urllib.parse.urlparse(url).netloc}: {e}") from e


def _expand(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = (int(x) for x in part.split("-"))
            out += [w for w in range(100, 1001, 100) if a <= w <= b]
        else:
            out.append(int(part))
    return out


def builtin_catalog() -> list[FontFamily]:
    fams = []
    for i, (fam, cat, ws, it) in enumerate(POPULAR):
        weights = [w for w in _expand(ws) if w <= 900]
        variants = [str(w) for w in weights] + ([f"{w}i" for w in weights] if it else [])
        fams.append(FontFamily(fam, cat, variants, [], i))
    return fams


def catalog(refresh: bool = False, timeout: float = 20, offline: bool = False) -> list[FontFamily]:
    """Every Google Fonts family (sorted by popularity). Cached for two weeks; built-in list when offline."""
    cache = cache_root() / "catalog.json"
    fresh = cache.exists() and time.time() - cache.stat().st_mtime < CATALOG_MAX_AGE
    if cache.exists() and (fresh or offline) and not refresh:
        try:
            return [FontFamily(**d) for d in json.loads(cache.read_text(encoding="utf-8"))]
        except (OSError, ValueError, TypeError):
            pass
    if offline:
        return builtin_catalog()
    try:
        raw = _get(METADATA_URL, timeout).decode("utf-8", "replace")
        data = json.loads(raw[raw.index("{"):])
        fams = []
        for f in data.get("familyMetadataList", []):
            if f.get("isBrandFont") or f.get("colorCapabilities"):
                continue
            variants = [v for v in (f.get("fonts") or {}) if re.match(r"^\d{3}i?$", v)]
            fams.append(FontFamily(f["family"], f.get("category") or "Sans Serif", variants or ["400"],
                                   [s for s in f.get("subsets") or [] if s != "menu"],
                                   int(f.get("popularity") or 9999)))
        fams.sort(key=lambda x: x.popularity)
        cache.write_text(json.dumps([vars(x) for x in fams], ensure_ascii=False), encoding="utf-8")
        return fams
    except (FontError, ValueError, KeyError):
        if cache.exists():
            try:
                return [FontFamily(**d) for d in json.loads(cache.read_text(encoding="utf-8"))]
            except (OSError, ValueError, TypeError):
                pass
        return builtin_catalog()


def find_family(name: str, fams: list[FontFamily] | None = None) -> FontFamily | None:
    fams = fams if fams is not None else catalog(offline=True)
    key = name.strip().lower()
    return next((f for f in fams if f.family.lower() == key), None)


def search(query: str, fams: list[FontFamily] | None = None, category: str | None = None,
           subset: str | None = None, limit: int = 200) -> list[FontFamily]:
    fams = fams if fams is not None else catalog(offline=True)
    q = query.strip().lower()
    out = [f for f in fams if (not q or q in f.family.lower()) and (not category or f.category == category)
           and (not subset or subset in f.subsets)]
    if q:
        out.sort(key=lambda f: (not f.family.lower().startswith(q), f.popularity))
    return out[:limit]


# ------------------------------------------------------------------------------------------ download
def _css_query(family: str, weights: list[int], italic: bool, fam: FontFamily | None) -> str:
    name = family.replace(" ", "+")
    if fam is not None and fam.variants == ["400"] or (fam is None and weights == [400] and not italic):
        return f"family={name}&display=swap"
    pairs = []
    for w in weights:
        if fam is None or str(w) in fam.variants:
            pairs.append((0, w))
        if italic and (fam is None or f"{w}i" in fam.variants):
            pairs.append((1, w))
    if not pairs:
        return f"family={name}&display=swap"
    pairs.sort()
    if any(i for i, _ in pairs):
        spec = "ital,wght@" + ";".join(f"{i},{w}" for i, w in pairs)
    else:
        spec = "wght@" + ";".join(str(w) for _, w in pairs)
    return f"family={name}:{spec}&display=swap"


_FACE = re.compile(r"@font-face\s*\{(.*?)\}", re.S)


def _css_faces(css: str) -> list[tuple[int, str, str]]:
    out = []
    for body in _FACE.findall(css):
        st = re.search(r"font-style:\s*(\w+)", body)
        wt = re.search(r"font-weight:\s*(\d+)", body)
        url = re.search(r"url\((https://[^)]+\.ttf)\)", body)
        if st and wt and url:
            out.append((int(wt.group(1)), st.group(1), url.group(1)))
    return out


def _github_files(family: str, timeout: float) -> tuple[str, str, list[tuple[int, str, str]]]:
    """(licence dir, licence file, [(weight, style, filename)]) from google/fonts METADATA.pb."""
    d = repo_dir(family)
    for lic, lic_file, _n in LICENSE_DIRS:
        try:
            meta = _get(GITHUB_RAW.format(lic=lic, dir=d, file="METADATA.pb"), timeout).decode("utf-8", "replace")
        except FontError:
            continue
        files = []
        for blk in re.findall(r"fonts\s*\{(.*?)\}", meta, re.S):
            st = re.search(r'style:\s*"(\w+)"', blk)
            wt = re.search(r"weight:\s*(\d+)", blk)
            fn = re.search(r'filename:\s*"([^"]+)"', blk)
            if st and wt and fn:
                files.append((int(wt.group(1)), st.group(1), fn.group(1)))
        return lic, lic_file, files
    raise FontError(f"{family!r} is not in the google/fonts repository")


def download_family(family: str, weights=(400, 700), italic: bool = False, timeout: float = 30,
                    progress=None) -> CachedFamily:
    """Download (or reuse from the cache) the TTFs of the given weights + the licence file.
    ``progress(text)`` is called with status lines. Raises FontError when nothing could be fetched."""
    fam = find_family(family)
    family = fam.family if fam else family.strip()
    weights = sorted({int(w) for w in weights or (400,)})
    if fam and fam.weights:
        avail = fam.weights
        weights = sorted({min(avail, key=lambda a: abs(a - w)) for w in weights})
    folder = cache_root() / repo_dir(family)
    folder.mkdir(parents=True, exist_ok=True)
    want = [(w, "normal") for w in weights] + ([(w, "italic") for w in weights] if italic else [])
    files: list[FontFile] = []
    missing = []
    for w, st in want:
        p = folder / style_file_name(family, w, st)
        if p.exists() and p.stat().st_size > 1000:
            files.append(FontFile(w, st, p))
        else:
            missing.append((w, st))
    if missing:
        got = {}
        try:
            if progress:
                progress(f"Fetching {family} from Google Fonts...")
            css = _get(CSS_URL.format(query=_css_query(family, sorted({w for w, _ in missing}), italic, fam)),
                       timeout).decode("utf-8", "replace")
            for w, st, url in _css_faces(css):
                if (w, st) in missing and (w, st) not in got:
                    got[(w, st)] = url
        except FontError:
            got = {}
        for (w, st), url in got.items():
            p = folder / style_file_name(family, w, st)
            if progress:
                progress(f"Downloading {p.name}")
            p.write_bytes(_get(url, timeout))
            files.append(FontFile(w, st, p))
        rest = [m for m in missing if m not in got]
        if rest:          # fall back to the repository files (variable fonts serve every weight)
            try:
                lic, _lf, gh = _github_files(family, timeout)
            except FontError:
                gh, lic = [], ""
            for w, st in rest:
                cands = [g for g in gh if g[1] == st]
                if not cands:
                    continue
                best = min(cands, key=lambda g: abs(g[0] - w))
                variable = "[" in best[2]
                p = folder / (f"{file_stem(family)}{'-Italic' if st == 'italic' else ''}-Variable.ttf" if variable
                              else style_file_name(family, w, st))
                if not p.exists():
                    if progress:
                        progress(f"Downloading {best[2]}")
                    p.write_bytes(_get(GITHUB_RAW.format(lic=lic, dir=repo_dir(family),
                                                         file=urllib.parse.quote(best[2])), timeout))
                if not any(f.path == p for f in files):
                    files.append(FontFile(w if not variable else 400, st, p))
    if not files:
        raise FontError(f"could not download {family!r} (check the name and the internet connection)")
    lic_file, lic_name = _ensure_license(family, folder, timeout)
    (folder / "family.json").write_text(json.dumps({"family": family, "license": lic_name}), encoding="utf-8")
    files.sort(key=lambda f: (f.style, f.weight))
    return CachedFamily(family, folder, files, lic_file, lic_name)


def _ensure_license(family: str, folder: Path, timeout: float) -> tuple[Path | None, str]:
    for lic, lic_file, name in LICENSE_DIRS:
        p = folder / lic_file
        if p.exists():
            return p, name
    for lic, lic_file, name in LICENSE_DIRS:
        try:
            data = _get(GITHUB_RAW.format(lic=lic, dir=repo_dir(family), file=lic_file), timeout)
        except FontError:
            continue
        p = folder / lic_file
        p.write_bytes(data)
        return p, name
    return None, "see fonts.google.com"


def cached_families() -> list[str]:
    """Families with at least one cached TTF (usable offline)."""
    out = []
    for d in sorted(cache_root().iterdir()):
        if d.is_dir() and any(d.glob("*.ttf")):
            try:
                out.append(json.loads((d / "family.json").read_text(encoding="utf-8"))["family"])
            except (OSError, ValueError, KeyError):
                out.append(next(d.glob("*.ttf")).stem.split("-")[0])
    return out


# --------------------------------------------------------------------------------------- project side
def add_to_project(project_folder, family: str, weights=(400, 700), italic: bool = False,
                   timeout: float = 30, progress=None) -> dict:
    """Download (cache) and copy a family into ``assets/fonts/<Family>/`` with its licence, register it in
    pubspec.yaml and return the screen ``fonts`` entry:
    ``{"family", "source": "asset", "files": [{"asset", "weight", "style"}], "license"}``."""
    cf = download_family(family, weights, italic, timeout, progress)
    folder = Path(project_folder)
    dst_dir = folder / "assets" / "fonts" / asset_family_dir(cf.family)
    dst_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for f in cf.files:
        dst = dst_dir / f.path.name
        if not dst.exists() or dst.stat().st_size != f.path.stat().st_size:
            shutil.copy2(f.path, dst)
        e = {"asset": dst.relative_to(folder).as_posix()}
        if f.weight != 400 and "Variable" not in f.path.name:
            e["weight"] = f.weight
        if f.style == "italic":
            e["style"] = "italic"
        files.append(e)
    if cf.license_file:
        shutil.copy2(cf.license_file, dst_dir / cf.license_file.name)
    entry = {"family": cf.family, "source": "asset", "files": files, "license": cf.license_name}
    register_font(folder, entry)
    return entry


def register_font(project_folder, entry: dict) -> bool:
    """Write the font's ``flutter: fonts:`` block into pubspec.yaml (replaces an older block of the family)."""
    pp = Path(project_folder) / "pubspec.yaml"
    if not pp.exists():
        return False
    text = pp.read_text(encoding="utf-8")
    base = remove_font_block(text, entry["family"])
    new = CG.update_pubspec(base, [], [entry], False)
    if new != text:
        pp.write_text(new, encoding="utf-8")
        return True
    return False


def remove_font_block(pubspec_text: str, family: str) -> str:
    """Drop the ``- family: <family>`` block from pubspec text (to rewrite it with other weights)."""
    lines = pubspec_text.splitlines()
    out, i = [], 0
    while i < len(lines):
        m = re.match(r"^(\s*)- family:\s*(.+?)\s*$", lines[i])
        if m and m.group(2).strip("'\"") == family:
            ind = len(m.group(1))
            i += 1
            while i < len(lines) and lines[i].strip() and (len(lines[i]) - len(lines[i].lstrip())) > ind:
                i += 1
            continue
        out.append(lines[i])
        i += 1
    text = "\n".join(out) + ("\n" if pubspec_text.endswith("\n") else "")
    # an empty "fonts:" header left behind
    return re.sub(r"^  fonts:[ \t]*\n(?![ \t]{4}- )", "", text, flags=re.M)


def project_fonts(project_folder) -> list[str]:
    """Families registered as asset fonts in pubspec.yaml."""
    pp = Path(project_folder) / "pubspec.yaml"
    if not pp.exists():
        return []
    return [f.strip("'\"") for f in re.findall(r"^\s+- family:\s*(.+?)\s*$", pp.read_text(encoding="utf-8"), re.M)]


def use_in_screen(screen: M.Screen, entry_or_family, offline: bool | None = None) -> M.Patch:
    """Add / replace the font in the screen's ``fonts`` list. ``entry_or_family`` is an entry from
    ``add_to_project`` (offline asset font) or a family name (``"source": "google"``)."""
    entry = entry_or_family if isinstance(entry_or_family, dict) else {"family": str(entry_or_family),
                                                                      "source": "google"}
    cur = [f for f in screen.data.get("fonts") or [] if f.get("family") != entry["family"]]
    return M.set_screen(screen, "fonts", cur + [entry])


def text_style_font(entry: dict) -> dict:
    """The text_style keys selecting this font: googleFont for runtime fonts, fontFamily for asset fonts."""
    if entry.get("source") == "asset":
        return {"fontFamily": entry["family"]}
    return {"googleFont": entry["family"]}


def preview_css(family: str) -> str:
    """CSS2 URL for previewing a family in a web view (the designer's font picker)."""
    return "https://fonts.googleapis.com/css2?family=" + family.replace(" ", "+") + "&display=swap"
