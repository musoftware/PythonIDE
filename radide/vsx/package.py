"""VS Code extension packages (.vsix) - the on-disk model every VSX subsystem codes against.

A .vsix is a zip (Open Packaging Conventions) whose ``extension/`` folder is the extension itself:
``extension/package.json`` (the manifest), ``package.nls.json`` / ``package.nls.<lang>.json``
(localised ``%key%`` strings), the icon, README.md, CHANGELOG.md and the contributed files.

Install layout (shared by market / contrib / host)::

    <root>                                   vsx_root(): %APPDATA%\\RADIDE\\vsx  (env RADIDE_VSX_ROOT overrides)
    <root>\\extensions.json                  state: {"version": 1, "extensions": {id: record}}
    <root>\\<publisher>.<name>-<version>\\extension\\package.json ...   the unpacked "extension/" folder
    <root>\\.cache\\                          offline cache (registry JSON, icons, downloaded .vsix)

    id      = "<publisher>.<name>" lower-cased (VS Code ids are case-insensitive)
    record  = {"id", "publisher", "name", "version", "folder" (relative to root, e.g.
               "ms-python.python-2024.1.0"), "enabled": bool, "source": "openvsx" | "vsix" | "dependency",
               "installed_at": iso time, "sha256": str | "", "target_platform": str, "dependency_of": [ids]}

``read_manifest(ext_dir)`` returns an ``Extension`` with the localised manifest; ``installed()`` lists
the installed extensions with their state. Only this module reads/writes extensions.json (through
``load_state`` / ``save_state``) - other subsystems use radide.vsx.list_enabled() etc.
No Qt import here."""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

STATE_FILE = "extensions.json"
STATE_VERSION = 1
EXT_PREFIX = "extension/"
MAX_UNPACKED = 1024 * 1024 * 1024          # 1 GB: refuse zip bombs
MAX_MEMBERS = 60000
MAX_RATIO = 200                            # per-file compression ratio limit (for files > 1 MB)

_lock = threading.RLock()


class VsixError(Exception):
    """A broken / unsafe .vsix or an install-layout problem."""


# ============================================================================ locations
def vsx_root() -> Path:
    """Install root (created on demand). RADIDE_VSX_ROOT overrides it (tests use a scratch folder)."""
    env = os.environ.get("RADIDE_VSX_ROOT")
    if env:
        p = Path(env)
    else:
        try:
            from .. import paths
            portable = paths.portable()
            base = paths.settings_dir() if portable else None
        except Exception:  # noqa: BLE001
            base = None
        p = (base / "vsx") if base else Path(os.environ.get("APPDATA") or Path.home()) / "RADIDE" / "vsx"
    p.mkdir(parents=True, exist_ok=True)
    return p


def state_path() -> Path:
    return vsx_root() / STATE_FILE


def cache_dir(sub: str = "") -> Path:
    p = vsx_root() / ".cache"
    if sub:
        p = p / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


def make_id(publisher: str, name: str) -> str:
    return f"{publisher}.{name}".lower()


def folder_name(publisher: str, name: str, version: str) -> str:
    return f"{publisher}.{name}-{version}"


# ============================================================================ localisation
def ui_language() -> str:
    """The IDE's UI language ('en', 'ar' ...); works without Qt."""
    try:
        from .. import i18n
        return i18n.language() or "en"
    except Exception:  # noqa: BLE001
        return "en"


def load_nls(ext_dir: Path, lang: str | None = None) -> dict:
    """package.nls.json overlaid with package.nls.<lang>.json (also <lang> prefixes such as 'zh-cn')."""
    ext_dir = Path(ext_dir)
    out: dict = {}
    base = ext_dir / "package.nls.json"
    if base.is_file():
        out.update(_read_json(base, {}))
    lang = (lang or ui_language() or "en").lower()
    if lang != "en":
        for cand in (lang, lang.split("-")[0]):
            f = ext_dir / f"package.nls.{cand}.json"
            if f.is_file():
                out.update(_read_json(f, {}))
                break
    # nls values may be {"message": "...", "comment": [...]}
    return {k: (v.get("message", "") if isinstance(v, dict) else v) for k, v in out.items()}


_NLS_RE = re.compile(r"^%([^%\s]+)%$")


def localize(value, nls: dict):
    """Replace "%key%" strings (recursively) by their nls message."""
    if not nls:
        return value
    if isinstance(value, str):
        m = _NLS_RE.match(value)
        if m and m.group(1) in nls:
            return nls[m.group(1)]
        return value
    if isinstance(value, list):
        return [localize(v, nls) for v in value]
    if isinstance(value, dict):
        return {k: localize(v, nls) for k, v in value.items()}
    return value


# ============================================================================ manifest model
@dataclass(repr=False)
class Extension:
    """One extension: its localised package.json plus (for an installed one) its state."""
    publisher: str
    name: str
    version: str
    path: Path | None = None                 # the unpacked extension/ folder
    display_name: str = ""
    description: str = ""
    categories: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    engines: dict = field(default_factory=dict)
    main: str = ""                            # node entry point (relative), "" when none
    browser: str = ""                         # web entry point (relative), "" when none
    activation_events: list = field(default_factory=list)
    contributes: dict = field(default_factory=dict)
    extension_dependencies: list = field(default_factory=list)   # ids (lower-cased)
    extension_pack: list = field(default_factory=list)           # ids (lower-cased)
    extension_kind: list = field(default_factory=list)
    icon: str = ""                            # relative path inside path
    license: str = ""
    repository: str = ""
    homepage: str = ""
    preview: bool = False
    package_json: dict = field(default_factory=dict)             # localised raw manifest
    raw_package_json: dict = field(default_factory=dict)         # as shipped (with %keys%)
    nls: dict = field(default_factory=dict)
    # state (installed extensions only)
    enabled: bool = True
    source: str = ""
    installed_at: str = ""
    sha256: str = ""
    target_platform: str = ""
    dependency_of: list = field(default_factory=list)
    folder: str = ""                          # <publisher>.<name>-<version>

    def __repr__(self) -> str:
        return f"<Extension {self.id} {self.version}{'' if self.enabled else ' (disabled)'}>"

    # ---- identity
    @property
    def id(self) -> str:
        return make_id(self.publisher, self.name)

    @property
    def label(self) -> str:
        return self.display_name or self.name

    @property
    def engine_vscode(self) -> str:
        return str(self.engines.get("vscode", "") or "")

    @property
    def has_code(self) -> bool:
        """Runs JavaScript (needs the extension host)."""
        return bool(self.main or self.browser)

    # ---- files
    def file(self, rel: str) -> Path | None:
        """A file of the extension by its manifest-relative path ("./themes/x.json"), safely resolved."""
        if not self.path or not rel:
            return None
        rel = rel.replace("\\", "/")
        while rel.startswith("./"):
            rel = rel[2:]
        p = (Path(self.path) / rel).resolve()
        try:
            p.relative_to(Path(self.path).resolve())
        except ValueError:
            return None
        return p

    @property
    def icon_path(self) -> Path | None:
        p = self.file(self.icon) if self.icon else None
        return p if p and p.is_file() else None

    def _doc(self, *names) -> Path | None:
        if not self.path:
            return None
        try:
            entries = {e.name.lower(): e for e in Path(self.path).iterdir() if e.is_file()}
        except OSError:
            return None
        for n in names:
            for cand in (n, n + ".md", n + ".txt"):
                if cand.lower() in entries:
                    return entries[cand.lower()]
        return None

    @property
    def readme_path(self) -> Path | None:
        return self._doc("readme")

    @property
    def changelog_path(self) -> Path | None:
        return self._doc("changelog", "changes", "history")

    def readme(self) -> str:
        p = self.readme_path
        return p.read_text("utf-8", "replace") if p else ""

    def changelog(self) -> str:
        p = self.changelog_path
        return p.read_text("utf-8", "replace") if p else ""

    def contributes_list(self, point: str) -> list:
        v = self.contributes.get(point)
        if v is None:
            return []
        return v if isinstance(v, list) else [v]

    def state_record(self) -> dict:
        return {"id": self.id, "publisher": self.publisher, "name": self.name, "version": self.version,
                "folder": self.folder or folder_name(self.publisher, self.name, self.version),
                "enabled": bool(self.enabled), "source": self.source, "installed_at": self.installed_at,
                "sha256": self.sha256, "target_platform": self.target_platform,
                "dependency_of": list(self.dependency_of)}


def _ids(v) -> list:
    if not isinstance(v, list):
        return []
    return [str(x).lower() for x in v if isinstance(x, str) and "." in x]


def manifest_from_json(pkg: dict, nls: dict | None = None, path: Path | None = None) -> Extension:
    if not isinstance(pkg, dict):
        raise VsixError("package.json is not an object")
    publisher = str(pkg.get("publisher") or "").strip()
    name = str(pkg.get("name") or "").strip()
    version = str(pkg.get("version") or "").strip()
    if not publisher or not name or not version:
        raise VsixError("package.json needs publisher, name and version")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\-]*", publisher + name) or ".." in publisher + name:
        raise VsixError(f"invalid extension id {publisher}.{name}")
    if not re.fullmatch(r"[0-9A-Za-z.+\-]+", version):
        raise VsixError(f"invalid version {version!r}")
    nls = nls or {}
    loc = localize(pkg, nls)
    repo = loc.get("repository")
    if isinstance(repo, dict):
        repo = repo.get("url", "")
    contributes = loc.get("contributes") if isinstance(loc.get("contributes"), dict) else {}
    kind = loc.get("extensionKind") or []
    return Extension(
        publisher=publisher, name=name, version=version, path=Path(path) if path else None,
        display_name=str(loc.get("displayName") or ""), description=str(loc.get("description") or ""),
        categories=list(loc.get("categories") or []), keywords=list(loc.get("keywords") or []),
        engines=dict(loc.get("engines") or {}), main=str(loc.get("main") or ""),
        browser=str(loc.get("browser") or ""),
        activation_events=list(loc.get("activationEvents") or []), contributes=contributes,
        extension_dependencies=_ids(loc.get("extensionDependencies")),
        extension_pack=_ids(loc.get("extensionPack")),
        extension_kind=[kind] if isinstance(kind, str) else list(kind),
        icon=str(loc.get("icon") or ""), license=str(loc.get("license") or ""),
        repository=str(repo or ""), homepage=str(loc.get("homepage") or ""),
        preview=bool(loc.get("preview")), package_json=loc, raw_package_json=pkg, nls=nls,
        folder=folder_name(publisher, name, version))


def read_manifest(ext_dir, lang: str | None = None) -> Extension:
    """The localised manifest of an unpacked extension/ folder."""
    ext_dir = Path(ext_dir)
    pj = ext_dir / "package.json"
    if not pj.is_file():
        raise VsixError(f"no package.json in {ext_dir}")
    pkg = _read_json(pj, None)
    if pkg is None:
        raise VsixError(f"unreadable package.json in {ext_dir}")
    return manifest_from_json(pkg, load_nls(ext_dir, lang), ext_dir)


# ============================================================================ .vsix files
def _safe_member(name: str) -> str | None:
    """The path below extension/ for a zip member, or None when it is outside / unsafe."""
    n = name.replace("\\", "/")
    if not n.startswith(EXT_PREFIX) or n.endswith("/"):
        return None
    rel = n[len(EXT_PREFIX):]
    pp = PurePosixPath(rel)
    if not rel or pp.is_absolute() or any(part in ("", ".", "..") for part in pp.parts) or ":" in rel:
        raise VsixError(f"unsafe path in vsix: {name!r}")
    # Windows reserved device names
    for part in pp.parts:
        if part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                                          *(f"LPT{i}" for i in range(1, 10))}:
            raise VsixError(f"reserved file name in vsix: {name!r}")
    return rel


def read_vsix_manifest(vsix, lang: str | None = None) -> Extension:
    """The manifest of a .vsix without unpacking it (path is None)."""
    try:
        with zipfile.ZipFile(vsix) as z:
            names = {i.filename.replace("\\", "/"): i for i in z.infolist()}
            if EXT_PREFIX + "package.json" not in names:
                raise VsixError("not a VS Code extension (.vsix without extension/package.json)")
            pkg = json.loads(_strip_bom(z.read(names[EXT_PREFIX + "package.json"]).decode("utf-8", "replace")))
            nls: dict = {}
            for fn in ("package.nls.json",):
                if EXT_PREFIX + fn in names:
                    nls.update(_loads(z.read(names[EXT_PREFIX + fn])))
            lang = (lang or ui_language() or "en").lower()
            if lang != "en":
                for cand in (lang, lang.split("-")[0]):
                    key = f"{EXT_PREFIX}package.nls.{cand}.json"
                    if key in names:
                        nls.update(_loads(z.read(names[key])))
                        break
            nls = {k: (v.get("message", "") if isinstance(v, dict) else v) for k, v in nls.items()}
    except zipfile.BadZipFile as e:
        raise VsixError(f"not a zip file: {e}") from e
    except (ValueError, KeyError) as e:
        raise VsixError(f"bad package.json: {e}") from e
    return manifest_from_json(pkg, nls, None)


def safe_extract(vsix, dest) -> Path:
    """Unpack only the extension/ folder of a .vsix into dest (which must not exist yet).
    Refuses path traversal, absolute paths, symlinks, device names and zip bombs. Returns dest."""
    dest = Path(dest)
    if dest.exists():
        raise VsixError(f"destination exists: {dest}")
    try:
        z = zipfile.ZipFile(vsix)
    except zipfile.BadZipFile as e:
        raise VsixError(f"not a zip file: {e}") from e
    with z:
        infos = z.infolist()
        if len(infos) > MAX_MEMBERS:
            raise VsixError("too many files in vsix")
        plan = []
        total = 0
        for i in infos:
            rel = _safe_member(i.filename)
            if rel is None:
                continue
            mode = (i.external_attr >> 16) & 0xFFFF
            if stat.S_ISLNK(mode):
                raise VsixError(f"symbolic link in vsix: {i.filename!r}")
            total += i.file_size
            if total > MAX_UNPACKED:
                raise VsixError("vsix unpacks to more than 1 GB")
            if i.file_size > 1024 * 1024 and i.compress_size and i.file_size / i.compress_size > MAX_RATIO:
                raise VsixError(f"suspicious compression ratio: {i.filename!r}")
            plan.append((i, rel))
        if not any(rel == "package.json" for _, rel in plan):
            raise VsixError("not a VS Code extension (.vsix without extension/package.json)")
        dest.mkdir(parents=True)
        root = dest.resolve()
        try:
            for i, rel in plan:
                target = (dest / rel).resolve()
                target.relative_to(root)          # second line of defence
                target.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with z.open(i) as src, open(target, "wb") as out:
                    while True:
                        chunk = src.read(1 << 16)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > i.file_size + 1024:
                            raise VsixError(f"member larger than declared: {i.filename!r}")
                        out.write(chunk)
        except Exception:
            shutil.rmtree(dest, ignore_errors=True)
            raise
    return dest


def unpack_to_root(vsix, root: Path | None = None) -> Extension:
    """Unpack a .vsix into <root>/<publisher>.<name>-<version>/extension (replacing an existing copy of
    the same version) and return its manifest. Does not touch extensions.json."""
    root = Path(root) if root else vsx_root()
    man = read_vsix_manifest(vsix)
    final = root / man.folder
    tmp = Path(tempfile.mkdtemp(prefix=".unpack-", dir=root))
    try:
        safe_extract(vsix, tmp / "extension")
        if final.exists():
            _rmtree(final)
        os.replace(tmp, final)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    ext = read_manifest(final / "extension")
    ext.folder = man.folder
    return ext


def pack_vsix(ext_dir, out) -> Path:
    """Build a .vsix from an extension folder (the folder holding package.json): the files go below
    extension/, with a minimal [Content_Types].xml and extension.vsixmanifest (tests, local packaging)."""
    ext_dir, out = Path(ext_dir), Path(out)
    from xml.sax.saxutils import quoteattr, escape
    man = read_manifest(ext_dir, "en")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/'
                   'package/2006/content-types"><Default Extension=".json" ContentType="application/json"/>'
                   '<Default Extension=".vsixmanifest" ContentType="text/xml"/></Types>')
        z.writestr("extension.vsixmanifest",
                   '<?xml version="1.0" encoding="utf-8"?><PackageManifest Version="2.0.0" xmlns="http://'
                   'schemas.microsoft.com/developer/vsx-schema/2011"><Metadata><Identity Language="en-US" '
                   f'Id={quoteattr(man.name)} Version={quoteattr(man.version)} '
                   f'Publisher={quoteattr(man.publisher)}/><DisplayName>{escape(man.label)}</DisplayName>'
                   '</Metadata></PackageManifest>')
        for f in sorted(ext_dir.rglob("*")):
            if f.is_file():
                z.write(f, EXT_PREFIX + f.relative_to(ext_dir).as_posix())
    return out


# ============================================================================ state
def load_state() -> dict:
    with _lock:
        st = _read_json(state_path(), None)
        if not isinstance(st, dict) or not isinstance(st.get("extensions"), dict):
            st = {"version": STATE_VERSION, "extensions": {}}
        return st


def save_state(st: dict) -> None:
    with _lock:
        st["version"] = STATE_VERSION
        p = state_path()
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, indent=2, ensure_ascii=False), "utf-8")
        os.replace(tmp, p)


def installed(lang: str | None = None) -> list[Extension]:
    """Every installed extension (with state), sorted by label. Broken folders are skipped."""
    root = vsx_root()
    out = []
    for ext_id, rec in load_state()["extensions"].items():
        folder = rec.get("folder") or ""
        d = root / folder / "extension"
        if not folder or ".." in folder or not d.is_dir():
            continue
        try:
            ext = read_manifest(d, lang)
        except VsixError:
            continue
        apply_record(ext, rec)
        out.append(ext)
    return sorted(out, key=lambda e: e.label.lower())


def apply_record(ext: Extension, rec: dict) -> Extension:
    ext.enabled = bool(rec.get("enabled", True))
    ext.source = str(rec.get("source") or "")
    ext.installed_at = str(rec.get("installed_at") or "")
    ext.sha256 = str(rec.get("sha256") or "")
    ext.target_platform = str(rec.get("target_platform") or "")
    ext.dependency_of = list(rec.get("dependency_of") or [])
    ext.folder = str(rec.get("folder") or ext.folder)
    return ext


def get_installed(ext_id: str) -> Extension | None:
    ext_id = ext_id.lower()
    return next((e for e in installed() if e.id == ext_id), None)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


# ============================================================================ helpers
def _strip_bom(s: str) -> str:
    return s[1:] if s.startswith("﻿") else s


def _loads(b: bytes) -> dict:
    try:
        v = json.loads(_strip_bom(b.decode("utf-8", "replace")))
    except ValueError:
        return {}
    return v if isinstance(v, dict) else {}


def _read_json(p: Path, default):
    try:
        return json.loads(_strip_bom(Path(p).read_text("utf-8", "replace")))
    except (OSError, ValueError):
        return default


def _rmtree(p: Path) -> None:
    def onerr(func, path, _exc):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except OSError:
            pass
    if sys.version_info >= (3, 12):
        shutil.rmtree(p, onexc=onerr)
    else:
        shutil.rmtree(p, onerror=onerr)
    if Path(p).exists():                       # a file is locked (e.g. a running host): move it away
        trash = vsx_root() / ".trash"
        trash.mkdir(exist_ok=True)
        try:
            os.replace(p, trash / f"{Path(p).name}-{int(time.time() * 1000)}")
        except OSError as e:
            raise VsixError(f"cannot remove {p}: {e}") from e


def remove_folder(folder: str) -> None:
    """Delete <root>/<folder> (an installed extension version)."""
    if not folder or ".." in folder or "/" in folder or "\\" in folder:
        raise VsixError(f"bad folder {folder!r}")
    p = vsx_root() / folder
    if p.exists():
        _rmtree(p)


def clean_trash() -> None:
    t = vsx_root() / ".trash"
    if t.is_dir():
        shutil.rmtree(t, ignore_errors=True)
