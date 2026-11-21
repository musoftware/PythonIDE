"""HTTP for the NuGet client: GET with a disk cache under %LOCALAPPDATA%\\RADIDE\\cache\\nuget.

* ``get(url, ttl)`` returns bytes (gzip responses are decoded); a cached copy younger than `ttl`
  seconds is used, an older one is the fallback when the network fails (offline browsing).
* Recorded fixtures (tests without network): ``RADIDE_NUGET_FIXTURES=<folder>`` and
  ``RADIDE_NUGET_FIXTURE_MODE=record`` store every response in that folder (``index.json`` maps
  URL -> file); ``replay`` serves only from it and never touches the network.
* Only the URLs of configured package sources are requested (api.nuget.org by default); no
  credentials are handled here - private feeds are left to the dotnet CLI's credential providers.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

USER_AGENT = "RADIDE-NuGet/1.0 (+NuGet v3 client)"
_lock = threading.Lock()


class HttpError(Exception):
    def __init__(self, url: str, status: int, message: str = ""):
        super().__init__(f"{status} {message} ({url})".strip())
        self.url, self.status = url, status


def cache_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    p = Path(base) / "RADIDE" / "cache" / "nuget"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:24]


# ---------------------------------------------------------------- fixtures
def _fixture_dir() -> Path | None:
    d = os.environ.get("RADIDE_NUGET_FIXTURES", "")
    return Path(d) if d else None


def _fixture_mode() -> str:
    return os.environ.get("RADIDE_NUGET_FIXTURE_MODE", "replay").lower() if _fixture_dir() else ""


def _fixture_index(d: Path) -> dict:
    try:
        return json.loads((d / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _fixture_read(url: str) -> bytes | None:
    d = _fixture_dir()
    name = _fixture_index(d).get(url) if d else None
    if not name:
        return None
    try:
        return (d / name).read_bytes()
    except OSError:
        return None


def _fixture_write(url: str, data: bytes) -> None:
    d = _fixture_dir()
    if d is None:
        return
    with _lock:
        d.mkdir(parents=True, exist_ok=True)
        idx = _fixture_index(d)
        name = idx.get(url) or (_key(url) + ".bin")
        (d / name).write_bytes(data)
        idx[url] = name
        (d / "index.json").write_text(json.dumps(idx, indent=1, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------- GET
def _decode(data: bytes) -> bytes:
    return gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data


def fetch(url: str, timeout: float = 30.0) -> bytes:
    """Network GET (no cache). Raises HttpError / OSError."""
    if _fixture_mode() == "replay":
        data = _fixture_read(url)
        if data is None:
            raise HttpError(url, 404, "not in the recorded fixtures")
        return data
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:      # noqa: S310 - package source URLs only
            data = _decode(r.read())
    except urllib.error.HTTPError as e:
        raise HttpError(url, e.code, str(e.reason)) from None
    if _fixture_mode() == "record":
        _fixture_write(url, data)
    return data


def get(url: str, ttl: float = 600.0, timeout: float = 30.0) -> bytes:
    """GET through the disk cache (ttl seconds; ttl=0 always asks the network first)."""
    if _fixture_mode() == "replay":
        return fetch(url, timeout)
    path = cache_root() / "http" / (_key(url) + ".bin")
    if ttl > 0 and _fixture_mode() != "record" and path.is_file() and time.time() - path.stat().st_mtime < ttl:
        try:
            return path.read_bytes()
        except OSError:
            pass
    try:
        data = fetch(url, timeout)
    except HttpError as e:
        if e.status == 404:
            raise
        if path.is_file():
            return path.read_bytes()
        raise
    except OSError:
        if path.is_file():                     # offline: the last copy we saw
            return path.read_bytes()
        raise
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
    except OSError:
        pass
    return data


def get_json(url: str, ttl: float = 600.0, timeout: float = 30.0):
    return json.loads(get(url, ttl, timeout).decode("utf-8-sig"))


def download(url: str, dest: Path, timeout: float = 120.0) -> Path:
    """Download to a file (atomic rename). Fixture replay reads the recorded bytes."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = fetch(url, timeout)
    tmp = dest.with_suffix(dest.suffix + f".{os.getpid()}.part")
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    return dest


__all__ = ["get", "get_json", "fetch", "download", "cache_root", "HttpError"]
