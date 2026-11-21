"""Open VSX registry client (https://open-vsx.org - the open marketplace of VSCodium / Theia / Gitpod).

    search(query, category, offset, size, sort_by)  -> SearchPage   (GET /api/-/search)
    details(namespace, name, version=None)          -> dict         (GET /api/{ns}/{name}[/{version}])
    all_versions(ext_id)                            -> [dict]       (GET /api/-/query?includeAllVersions)
    pick_version(ext_id, api_level)                 -> dict | None  newest compatible stable entry for Windows
    download(entry, dest_dir, progress)             -> Path         .vsix, SHA256-checked when published
    text(url) / binary(url)                         README / CHANGELOG / icons (cached)
    engine_compatible("^1.82.0", "1.90.0")          -> bool

Every JSON / file answer is cached in <vsx root>/.cache so the Extensions view still works offline
(``offline_ok=True`` falls back to the cache when the network fails). Base URL: env RADIDE_VSX_REGISTRY
or the QSettings value ``vsx/registry`` (default https://open-vsx.org). No Qt import at module level."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from . import API_LEVEL
from .package import cache_dir

DEFAULT_REGISTRY = "https://open-vsx.org"
USER_AGENT = "RADIDE-VSX/1.0 (+https://open-vsx.org)"
TIMEOUT = 25
CACHE_TTL = 6 * 3600          # seconds a cached search / details answer counts as fresh

CATEGORIES = ["Programming Languages", "Snippets", "Linters", "Themes", "Debuggers", "Formatters",
              "Keymaps", "SCM Providers", "Other", "Extension Packs", "Language Packs", "Data Science",
              "Machine Learning", "Visualization", "Notebooks", "Education", "Testing", "AI", "Chat"]
SORTS = {"relevance": "relevance", "downloads": "downloadCount", "rating": "averageRating",
         "date": "timestamp"}


class RegistryError(Exception):
    pass


def base_url() -> str:
    url = os.environ.get("RADIDE_VSX_REGISTRY")
    if not url:
        try:
            from PyQt6.QtCore import QCoreApplication
            if QCoreApplication.instance() is not None:
                from .. import paths
                url = str(paths.qsettings().value("vsx/registry", "") or "")
        except Exception:  # noqa: BLE001
            url = ""
    return (url or DEFAULT_REGISTRY).rstrip("/")


def api_level() -> str:
    return os.environ.get("RADIDE_VSX_API_LEVEL") or API_LEVEL


def target_platform() -> str:
    """The Open VSX target platform of this machine (win32-x64, win32-arm64, linux-x64 ...)."""
    m = platform.machine().lower()
    arch = "arm64" if m in ("arm64", "aarch64") else "x64" if m in ("amd64", "x86_64", "x64") else "ia32"
    sysname = {"windows": "win32", "darwin": "darwin"}.get(platform.system().lower(), "linux")
    return f"{sysname}-{arch}"


# ============================================================================ http + cache
def _cache_file(url: str, kind: str) -> Path:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return cache_dir(kind) / h


def _open(url: str, timeout: float = TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json, */*"})
    return urllib.request.urlopen(req, timeout=timeout)   # noqa: S310 - https registry URL


def get_json(url: str, *, ttl: float = CACHE_TTL, offline_ok: bool = True, refresh: bool = False):
    cf = _cache_file(url, "json")
    if not refresh and ttl and cf.is_file() and time.time() - cf.stat().st_mtime < ttl:
        try:
            return json.loads(cf.read_text("utf-8"))
        except (OSError, ValueError):
            pass
    try:
        with _open(url) as r:
            data = r.read()
        obj = json.loads(data.decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RegistryError(f"not found: {url}") from e
        if offline_ok and cf.is_file():
            return json.loads(cf.read_text("utf-8"))
        raise RegistryError(f"HTTP {e.code}: {url}") from e
    except (urllib.error.URLError, OSError, ValueError) as e:
        if offline_ok and cf.is_file():
            try:
                return json.loads(cf.read_text("utf-8"))
            except (OSError, ValueError):
                pass
        raise RegistryError(f"cannot reach the registry ({e})") from e
    try:
        cf.write_text(json.dumps(obj), "utf-8")
    except OSError:
        pass
    return obj


def binary(url: str, *, kind: str = "files", ttl: float = 30 * 86400) -> bytes:
    if not url:
        return b""
    cf = _cache_file(url, kind)
    if cf.is_file() and time.time() - cf.stat().st_mtime < ttl:
        return cf.read_bytes()
    try:
        with _open(url) as r:
            data = r.read()
    except (urllib.error.URLError, OSError) as e:
        if cf.is_file():
            return cf.read_bytes()
        raise RegistryError(f"download failed: {url} ({e})") from e
    try:
        cf.write_bytes(data)
    except OSError:
        pass
    return data


def text(url: str) -> str:
    return binary(url, kind="files").decode("utf-8", "replace") if url else ""


def is_cached(url: str) -> bool:
    return _cache_file(url, "json").is_file()


# ============================================================================ API
@dataclass
class SearchPage:
    extensions: list = field(default_factory=list)     # dicts as returned by Open VSX
    total: int = 0
    offset: int = 0
    offline: bool = False


def search(query: str = "", category: str = "", offset: int = 0, size: int = 30,
           sort_by: str = "relevance", include_all_versions: bool = False) -> SearchPage:
    q = {"query": query or "", "offset": max(0, int(offset)), "size": max(1, min(int(size), 100))}
    if category:
        q["category"] = category
    sb = SORTS.get(sort_by, sort_by)
    if sb and sb != "relevance":
        q["sortBy"] = sb
        q["sortOrder"] = "desc"
    elif not query:
        q["sortBy"] = "downloadCount"            # an empty query: most popular first
        q["sortOrder"] = "desc"
    if include_all_versions:
        q["includeAllVersions"] = "true"
    url = f"{base_url()}/api/-/search?{urllib.parse.urlencode(q)}"
    offline = False
    try:
        obj = get_json(url, ttl=600, offline_ok=False)
    except RegistryError:
        if not is_cached(url):
            raise
        obj = json.loads(_cache_file(url, "json").read_text("utf-8"))
        offline = True
    return SearchPage(list(obj.get("extensions") or []), int(obj.get("totalSize") or 0),
                      int(obj.get("offset") or 0), offline)


def split_id(ext_id: str) -> tuple[str, str]:
    ns, _, name = ext_id.partition(".")
    if not ns or not name:
        raise RegistryError(f"bad extension id {ext_id!r} (expected publisher.name)")
    return ns, name


def details(namespace: str, name: str, version: str | None = None, *, refresh: bool = False) -> dict:
    parts = [urllib.parse.quote(namespace), urllib.parse.quote(name)]
    if version:
        parts.append(urllib.parse.quote(version))
    obj = get_json(f"{base_url()}/api/{'/'.join(parts)}", refresh=refresh)
    if isinstance(obj, dict) and obj.get("error"):
        raise RegistryError(str(obj["error"]))
    return obj


def all_versions(ext_id: str, *, refresh: bool = False, limit: int = 400) -> list[dict]:
    """Every published entry of an extension (newest first; one entry per version and target platform)."""
    out: list[dict] = []
    offset = 0
    while len(out) < limit:
        q = urllib.parse.urlencode({"extensionId": ext_id, "includeAllVersions": "true",
                                    "offset": offset, "size": 100})
        obj = get_json(f"{base_url()}/api/-/query?{q}", refresh=refresh, ttl=3600)
        batch = list(obj.get("extensions") or [])
        out.extend(batch)
        offset += len(batch)
        if not batch or offset >= int(obj.get("totalSize") or 0):
            break
    return out


def _platform_ok(e: dict, plat: str) -> bool:
    tp = e.get("targetPlatform") or "universal"
    return tp in ("universal", plat)


def pick_version(ext_id: str, level: str | None = None, *, allow_prerelease: bool = False,
                 refresh: bool = False, version: str | None = None,
                 ignore_engines: bool = False) -> dict | None:
    """The newest stable entry for this machine whose engines.vscode accepts the emulated API level
    (or exactly ``version`` when given; any engines when ignore_engines). None when nothing fits."""
    level = level or api_level()
    plat = target_platform()
    entries = [e for e in all_versions(ext_id, refresh=refresh) if _platform_ok(e, plat)]
    if version:
        entries = [e for e in entries if e.get("version") == version]
        entries.sort(key=lambda e: 0 if e.get("targetPlatform") == plat else 1)
        return entries[0] if entries else None
    entries.sort(key=lambda e: (parse_version(e.get("version", "")),
                                1 if e.get("targetPlatform") == plat else 0), reverse=True)
    for e in entries:
        if not allow_prerelease and (e.get("preRelease") or is_prerelease(e.get("version", ""))):
            continue
        if ignore_engines or engine_compatible((e.get("engines") or {}).get("vscode", ""), level):
            return e
    return None


def latest_entry(ext_id: str, *, refresh: bool = False) -> dict | None:
    """The newest stable entry for this machine regardless of engines (for 'install anyway')."""
    # not a huge level: '^1.94.0' means <2.0.0, so "999.0.0" rejected every version
    return pick_version(ext_id, refresh=refresh, ignore_engines=True)


def download_url(entry: dict) -> str:
    files = entry.get("files") or {}
    url = files.get("download")
    if not url:
        downloads = entry.get("downloads") or {}
        url = downloads.get(target_platform()) or downloads.get("universal") or ""
    if not url:
        raise RegistryError(f"{entry.get('namespace')}.{entry.get('name')} has no download")
    return url


def download(entry: dict, dest_dir: Path | None = None, progress=None) -> tuple[Path, str]:
    """Download the .vsix of a registry entry; returns (path, sha256). The file is checked against the
    published .sha256 when the registry provides one (RegistryError on mismatch). progress(done, total)."""
    url = download_url(entry)
    dest_dir = Path(dest_dir) if dest_dir else cache_dir("vsix")
    dest_dir.mkdir(parents=True, exist_ok=True)
    fname = re.sub(r"[^A-Za-z0-9_.@\-]", "_", url.rsplit("/", 1)[-1]) or "extension.vsix"
    target = dest_dir / fname
    expected = ""
    sha_url = (entry.get("files") or {}).get("sha256")
    if sha_url:
        try:
            with _open(sha_url) as r:
                expected = r.read().decode("ascii", "replace").strip().split()[0].lower()
        except (urllib.error.URLError, OSError, IndexError):
            expected = ""
    if target.is_file() and expected and _sha256(target) == expected:
        return target, expected
    tmp = target.with_suffix(".part")
    h = hashlib.sha256()
    try:
        with _open(url, timeout=120) as r, open(tmp, "wb") as out:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    except (urllib.error.URLError, OSError) as e:
        tmp.unlink(missing_ok=True)
        if target.is_file():                      # offline: reuse a previous download
            return target, _sha256(target)
        raise RegistryError(f"download failed: {e}") from e
    digest = h.hexdigest()
    if expected and digest != expected:
        tmp.unlink(missing_ok=True)
        raise RegistryError(f"SHA256 mismatch for {fname}: expected {expected}, got {digest}")
    os.replace(tmp, target)
    return target, digest


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


# ============================================================================ versions / engines
def parse_version(v: str) -> tuple:
    """'1.90.2' -> (1, 90, 2); tolerant of 'v', missing parts and suffixes."""
    v = (v or "").strip().lstrip("vV=")
    core = re.split(r"[-+]", v, maxsplit=1)[0]
    nums = []
    for part in core.split(".")[:4]:
        m = re.match(r"\d+", part)
        nums.append(int(m.group()) if m else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def is_prerelease(v: str) -> bool:
    return bool(re.search(r"-(?!\d{8}$)", v or ""))


def newer(a: str, b: str) -> bool:
    """a is newer than b."""
    return parse_version(a) > parse_version(b)


def _cmp_ok(op: str, ver: tuple, base: str) -> bool:
    b = parse_version(base)
    if op in (">=", ""):
        return ver >= b if op else ver == b
    return {">": ver > b, "<": ver < b, "<=": ver <= b, "=": ver == b}[op]


def engine_compatible(rng: str, level: str | None = None) -> bool:
    """Does the semver range of engines.vscode accept the API level? ('*', '^1.82.0', '>=1.60.0',
    '~1.7.0', '1.90.x', '^1.94.0-20240918' (date suffix ignored), '>=1.5 <2', '||' alternatives)."""
    level = level or api_level()
    ver = parse_version(level)
    rng = (rng or "").strip()
    if not rng or rng in ("*", "x", "latest"):
        return True
    for alt in rng.split("||"):
        if all(_term_ok(t, ver) for t in alt.split()):
            return True
    return False


def _term_ok(t: str, ver: tuple) -> bool:
    t = t.strip()
    if not t or t in ("*", "x"):
        return True
    m = re.match(r"^(\^|~|>=|<=|>|<|=)?\s*v?(.+)$", t)
    if not m:
        return True
    op, base = m.group(1) or "", m.group(2)
    if base.startswith("0."):                    # ancient "^0.10.x" manifests: VS Code accepts them
        return True
    if re.search(r"(^|\.)[xX*]", base):          # 1.90.x / 1.x
        parts = base.split(".")
        fixed = [int(p) for p in parts if p.isdigit()]
        return list(ver[:len(fixed)]) == fixed
    b = parse_version(base)
    if op == "^":
        if b[0] > 0:
            return b <= ver < (b[0] + 1, 0, 0)
        return b <= ver < (0, b[1] + 1, 0) if b[1] > 0 else ver[:2] == b[:2] and ver >= b
    if op == "~":
        return b <= ver < (b[0], b[1] + 1, 0)
    if op == "":
        return ver == b
    return _cmp_ok(op, ver, base)
