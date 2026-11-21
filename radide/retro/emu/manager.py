"""Find, download and configure the emulators of radide/retro/emu/catalog.py (no Qt in here).

Where an emulator is looked up (first hit wins):

    1. the path set in Tools > Retro > Emulators... (QSettings ``retro/emu/<id>``, passed in as *configured*)
    2. ``%LOCALAPPDATA%\\RADIDE\\tools\\<id>`` (what the download puts there; searched recursively)
    3. PATH

Portable settings: every emulator RAD IDE starts keeps its configuration under
``%LOCALAPPDATA%\\RADIDE\\retro\\<id>`` (mGBA: ``portable.ini`` next to the downloaded exe; VICE: ``-config``;
Stella: ``-basedir``; DOSBox-X: a generated ``.conf``; Atari800: ``-config``) so the user's own installed
copies are never changed.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from .catalog import EMULATORS, Emulator

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_CONFIGURED: dict[str, str] = {}          # emulator id -> exe chosen by the user (set by the UI)


def local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "RADIDE"


def tools_root() -> Path:
    return local_root() / "tools"


def install_dir(emu_id: str) -> Path:
    return tools_root() / emu_id


def config_dir(emu_id: str) -> Path:
    """Portable settings folder of *emu_id* (created)."""
    d = local_root() / "retro" / emu_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def set_configured(emu_id: str, path: str) -> None:
    """Use *path* for *emu_id* ("" = automatic lookup again)."""
    if path:
        _CONFIGURED[emu_id] = path
    else:
        _CONFIGURED.pop(emu_id, None)


def _search(folder: Path, names) -> str:
    """Shallowest file in *folder* named like one of *names* (earlier names win)."""
    if not folder.is_dir():
        return ""
    order = {n.lower(): i for i, n in enumerate(names)}
    hits = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in ("_download", "licenses", "docs", "shaders")]
        for f in files:
            if f.lower() in order:
                p = Path(root) / f
                hits.append((order[f.lower()], len(p.parts), str(p)))
    return min(hits)[2] if hits else ""


def find(emu_id: str, role: str = "") -> str:
    """Path of the emulator's executable ("" = not installed). *role* picks an extra exe (mGBA "sdl")."""
    emu = EMULATORS.get(emu_id)
    if emu is None:
        return ""
    names = tuple(emu.extra_exes.get(role, ())) if role else emu.exe_names
    conf = _CONFIGURED.get(emu_id, "")
    if conf and Path(conf).is_file():
        if not role:
            return conf
        sib = _search(Path(conf).parent, names)
        if sib:
            return sib
    hit = _search(install_dir(emu_id), names)
    if hit:
        return hit
    if emu_id == "atari800":            # Altirra (free) when the user has it
        alt = _search(tools_root() / "altirra", ("Altirra64.exe", "Altirra.exe")) or shutil.which("Altirra64") or ""
        if alt and not shutil.which("atari800"):
            return alt
    if not role:
        for n in emu.path_names:
            p = shutil.which(n)
            if p:
                return p
    return ""


def installed_version(emu_id: str) -> str:
    try:
        d = json.loads((install_dir(emu_id) / "RADIDE-SOURCE.json").read_text(encoding="utf-8"))
        return str(d.get("version", ""))
    except (OSError, ValueError):
        return ""


def status() -> list[dict]:
    """One row per emulator: id, title, systems, path, version, licence, page."""
    rows = []
    for e in EMULATORS.values():
        p = find(e.id)
        rows.append({"id": e.id, "title": e.title, "systems": list(e.systems), "path": p,
                     "version": installed_version(e.id) if p and str(install_dir(e.id)) in p else ("" if not p else "?"),
                     "licence": e.licence, "page": e.page, "pinned": e.version, "debug": e.debug, "notes": e.notes})
    return rows


def missing_hint(emu_id: str) -> str:
    e = EMULATORS[emu_id]
    return (f"{e.title} was not found. Tools > Retro > Emulators... downloads the official portable build "
            f"{e.version} into {install_dir(emu_id)}, or download it yourself from {e.page} and set its path there.")


# ====================================================================== download
def download_verified(url: str, sha256: str, dest: Path, log=print) -> bool:
    """Download *url* to *dest*; the file is removed when its SHA-256 differs from *sha256*."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                f.write(chunk)
    except OSError as e:
        dest.unlink(missing_ok=True)
        log(f"Download failed: {e}")
        return False
    if h.hexdigest().lower() != sha256.lower():
        dest.unlink(missing_ok=True)
        log(f"SHA-256 mismatch for {url} (got {h.hexdigest()}) - the file was removed")
        return False
    log(f"SHA-256 OK ({sha256[:16]}...)")
    return True


def _safe(name: str) -> bool:
    n = name.replace("\\", "/")
    return not (n.startswith("/") or ".." in Path(n).parts or ":" in n)


def _extract_zip(archive: Path, target: Path, log) -> bool:
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if not _safe(info.filename):
                log(f"unsafe path in the archive: {info.filename}")
                return False
        z.extractall(target)
    return True


def _bsdtar() -> str:
    """Windows 10/11 ship bsdtar (libarchive) as System32\\tar.exe: it reads .7z archives."""
    sysroot = os.environ.get("SystemRoot", r"C:\Windows")
    cand = Path(sysroot) / "System32" / "tar.exe"
    if cand.is_file():
        return str(cand)
    for n in ("bsdtar", "7z", "7za"):
        p = shutil.which(n)
        if p:
            return p
    return ""


def _extract_7z(archive: Path, target: Path, log) -> bool:
    tool = _bsdtar()
    if not tool:
        log("No 7-Zip reader found (Windows tar.exe, bsdtar or 7z) - extract the archive yourself.")
        return False
    if Path(tool).stem.lower().startswith("7z"):
        args = [tool, "x", "-y", f"-o{target}", str(archive)]
    else:
        try:
            names = subprocess.run([tool, "-tf", str(archive)], capture_output=True, text=True, timeout=120,
                                   creationflags=NO_WINDOW, errors="replace").stdout.splitlines()
        except (OSError, subprocess.SubprocessError) as e:
            log(f"Cannot list {archive.name}: {e}")
            return False
        bad = [n for n in names if not _safe(n)]
        if bad:
            log(f"unsafe path in the archive: {bad[0]}")
            return False
        args = [tool, "-xf", str(archive), "-C", str(target)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=600, creationflags=NO_WINDOW, errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        log(f"Extracting {archive.name} failed: {e}")
        return False
    if r.returncode != 0:
        log(f"Extracting {archive.name} failed: {(r.stderr or r.stdout).strip()[:400]}")
        return False
    return True


def install(emu_id: str, log=print) -> bool:
    """Download the pinned official build of *emu_id* and unpack it into tools\\<id> (blocking: run it in a
    worker thread from the UI). Returns True when the emulator can be found afterwards."""
    e: Emulator | None = EMULATORS.get(emu_id)
    if e is None:
        log(f"Unknown emulator: {emu_id}")
        return False
    tmp = tools_root() / "_download" / Path(e.url).name
    if not download_verified(e.url, e.sha256, tmp, log):
        log(f"Download {e.title} yourself from {e.page} and unpack it into {install_dir(emu_id)}")
        return False
    target = install_dir(emu_id)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    ok = (_extract_7z if e.archive == "7z" else _extract_zip)(tmp, target, log)
    tmp.unlink(missing_ok=True)
    if not ok:
        return False
    (target / "RADIDE-SOURCE.json").write_text(json.dumps(
        {"emulator": emu_id, "title": e.title, "version": e.version, "url": e.url, "sha256": e.sha256,
         "licence": e.licence, "page": e.page}, indent=1), encoding="utf-8")
    prepare_portable(emu_id)
    exe = find(emu_id)
    log(f"Installed {e.title} {e.version} into {target}" if exe else f"{e.title}: no executable found in {target}")
    return bool(exe)


def ensure(emu_id: str, log=print, download: bool = False) -> str:
    """Path of *emu_id*, downloading it first when *download* (the user asked for it)."""
    exe = find(emu_id)
    if exe or not download:
        return exe
    return find(emu_id) if install(emu_id, log) else ""


def uninstall(emu_id: str) -> bool:
    """Remove a downloaded emulator (only what RAD IDE put into tools\\<id>)."""
    d = install_dir(emu_id)
    if (d / "RADIDE-SOURCE.json").is_file():
        shutil.rmtree(d, ignore_errors=True)
        return True
    return False


def prepare_portable(emu_id: str) -> None:
    """Make a downloaded emulator keep its settings next to RAD IDE's copy, not in the user's profile."""
    exe = find(emu_id)
    if not exe or str(install_dir(emu_id)) not in exe:
        return
    folder = Path(exe).parent
    try:
        if emu_id == "mgba":
            (folder / "portable.ini").touch(exist_ok=True)       # mGBA portable mode
        elif emu_id == "dosbox-x":
            config_dir(emu_id)
        elif emu_id == "mesen":                                 # settings.json next to Mesen.exe = portable
            from .inputs import write_new_mesen_settings        # port 1 = a controller with keys (only if new)
            write_new_mesen_settings(folder / "settings.json")
    except OSError:
        pass


def mesen_settings_file() -> Path | None:
    """settings.json of the portable Mesen RAD IDE downloaded (None = no RAD IDE copy / not created yet)."""
    exe = find("mesen")
    if not exe or str(install_dir("mesen")) not in exe:
        return None
    p = Path(exe).parent / "settings.json"
    return p if p.is_file() else None


def version_of(emu_id: str) -> str:
    """Pinned version when RAD IDE downloaded it, else the file version of the exe ("" = unknown)."""
    v = installed_version(emu_id)
    if v:
        return v
    exe = find(emu_id)
    if not exe or os.name != "nt":
        return ""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-Item '{exe}').VersionInfo.FileVersion"],
                           capture_output=True, text=True, timeout=20, creationflags=NO_WINDOW)
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


__all__ = ["config_dir", "download_verified", "ensure", "find", "install", "install_dir", "installed_version",
           "local_root", "mesen_settings_file", "missing_hint", "prepare_portable", "set_configured", "status", "tools_root", "uninstall",
           "version_of"]
