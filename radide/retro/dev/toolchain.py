"""Toolchains of the retro game projects (no Qt in here).

    tool        what                         official source (portable, no admin, no PATH change)
    dasm        DASM 6502 macro assembler     https://github.com/dasm-assembler/dasm/releases  (GPL-2.0)
    cc65        cc65 / ca65 / ld65 / cl65     https://cc65.github.io -> Windows snapshot on SourceForge (zlib)
    rgbds       rgbasm / rgblink / rgbfix     https://github.com/gbdev/rgbds/releases          (MIT)
    sjasmplus   sjasmplus Z80 assembler       https://github.com/z00m128/sjasmplus/releases    (BSD-3)
    acme        ACME cross assembler          optional: PATH only (https://sourceforge.net/projects/acme-crossass)

Everything is unpacked into ``%LOCALAPPDATA%\\RADIDE\\tools\\<tool>``; the archive's SHA-256 is checked against the
value published on GitHub (DASM, RGBDS, sjasmplus) and recorded in ``RADIDE-SOURCE.json``. The cc65 Windows build
is a rolling snapshot (the official project publishes no fixed Windows release), so its SHA-256 cannot be pinned:
the measured value is recorded instead and the zip's own CRCs are verified. The tools run as external programs.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def tools_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "RADIDE" / "tools"


@dataclass(frozen=True)
class Release:
    tool: str
    version: str
    url: str
    sha256: str              # "" = rolling snapshot: measured and recorded, not pinned
    page: str                # official download page
    licence: str
    exes: tuple[str, ...]    # executables (relative to the tool folder, searched recursively too)


RELEASES: dict[str, Release] = {
    "dasm": Release("dasm", "2.20.18",
                    "https://github.com/dasm-assembler/dasm/releases/download/v2.20.18/dasm-v2.20.18-windows.zip",
                    "bccad44636054cf4cf35c941eeadb7fc12ad7fe68bdc8c0d4c32e5f920930906",
                    "https://github.com/dasm-assembler/dasm/releases", "GPL-2.0", ("dasm",)),
    "rgbds": Release("rgbds", "1.0.4",
                     "https://github.com/gbdev/rgbds/releases/download/v1.0.4/rgbds-win64.zip",
                     "bd1d7e386f290afd57f4ea9a7353bfcd4ae10884a94c5c1f2fc42a75db7f97e6",
                     "https://github.com/gbdev/rgbds/releases", "MIT", ("rgbasm", "rgblink", "rgbfix", "rgbgfx")),
    "sjasmplus": Release("sjasmplus", "1.24.0",
                         "https://github.com/z00m128/sjasmplus/releases/download/v1.24.0/sjasmplus-1.24.0.win.zip",
                         "7e1f8840842039bdb97e51a59abda2e5c25a9da160097e8f79a62583ab72d0e0",
                         "https://github.com/z00m128/sjasmplus/releases", "BSD-3-Clause", ("sjasmplus",)),
    "cc65": Release("cc65", "snapshot",
                    "https://sourceforge.net/projects/cc65/files/cc65-snapshot-win64.zip/download", "",
                    "https://cc65.github.io/getting-started.html", "zlib", ("ca65", "ld65", "cc65", "cl65")),
}

TOOL_TITLES = {"dasm": "DASM (Atari 2600 / 6502)", "cc65": "cc65 / ca65 / ld65 (NES, C64)",
               "rgbds": "RGBDS (Game Boy)", "sjasmplus": "sjasmplus (ZX Spectrum / Z80)",
               "acme": "ACME (C64, optional)"}

# executable -> tool package
EXE_TOOL = {"dasm": "dasm", "ca65": "cc65", "ld65": "cc65", "cc65": "cc65", "cl65": "cc65", "rgbasm": "rgbds",
            "rgblink": "rgbds", "rgbfix": "rgbds", "rgbgfx": "rgbds", "sjasmplus": "sjasmplus", "acme": "acme"}


def find(exe: str) -> str:
    """Path of an executable ("dasm", "ca65", "ld65", "cc65", "rgbasm", "rgblink", "rgbfix", "sjasmplus",
    "acme") - the IDE's tools folder first, then PATH. "" = not found."""
    tool = EXE_TOOL.get(exe, exe)
    root = tools_root() / tool
    for cand in (root / f"{exe}{EXE}", root / "bin" / f"{exe}{EXE}"):
        if cand.is_file():
            return str(cand)
    if root.is_dir():
        for cand in root.rglob(f"{exe}{EXE}"):
            if cand.is_file():
                return str(cand)
    return shutil.which(exe) or ""


def cc65_home() -> str:
    """The cc65 installation folder (holds include/, lib/, cfg/, asminc/) for CC65_HOME."""
    ca65 = find("ca65")
    if not ca65:
        return ""
    p = Path(ca65).parent
    return str(p.parent if p.name.lower() == "bin" else p)


def status() -> list[tuple[str, str, str]]:
    """(tool, title, path or "")."""
    first = {"dasm": "dasm", "cc65": "ca65", "rgbds": "rgbasm", "sjasmplus": "sjasmplus", "acme": "acme"}
    return [(t, TOOL_TITLES[t], find(first[t])) for t in ("dasm", "cc65", "rgbds", "sjasmplus", "acme")]


def missing_hint(exe: str) -> str:
    tool = EXE_TOOL.get(exe, exe)
    rel = RELEASES.get(tool)
    if rel is None:
        return f"{TOOL_TITLES.get(tool, exe)} was not found in PATH."
    return (f"{TOOL_TITLES[tool]} was not found. RAD IDE can download it into {tools_root() / tool} "
            f"(official {rel.page}).")


def _safe_extract(zpath: Path, target: Path, log) -> bool:
    with zipfile.ZipFile(zpath) as z:
        bad = z.testzip()
        if bad is not None:
            log(f"corrupt archive member: {bad}")
            return False
        names = [i.filename.replace("\\", "/") for i in z.infolist()]
        # strip one common top-level folder ("rgbds-1.0.4/...", "sjasmplus-1.24.0.win/...")
        tops = {n.split("/", 1)[0] for n in names if n.strip("/")}
        strip = ""
        if len(tops) == 1 and all("/" in n for n in names if n.strip("/") and not n.endswith("/")):
            strip = next(iter(tops)) + "/"
        for info in z.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in Path(name).parts or ":" in name:
                log(f"unsafe path in the archive: {name}")
                return False
            if strip and name.startswith(strip):
                name = name[len(strip):]
            if not name or name.endswith("/"):
                continue
            out = target / name
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return True


def install(tool: str, log=print) -> bool:
    """Download + unpack *tool* ("dasm", "cc65", "rgbds", "sjasmplus"). Blocking (use a thread in the UI)."""
    rel = RELEASES.get(tool)
    if rel is None:
        log(missing_hint(tool))
        return False
    tmp_dir = tools_root() / "_download"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / f"{tool}-{rel.version}.zip"
    log(f"Downloading {TOOL_TITLES[tool]} {rel.version} from {rel.url}")
    h = hashlib.sha256()
    try:
        req = urllib.request.Request(rel.url, headers={"User-Agent": "RAD-IDE"})
        with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                f.write(chunk)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        log(f"Download failed: {e}. Download it yourself from {rel.page} and unpack it into {tools_root() / tool}")
        return False
    digest = h.hexdigest().lower()
    if rel.sha256 and digest != rel.sha256:
        tmp.unlink(missing_ok=True)
        log(f"SHA-256 mismatch (got {digest}, expected {rel.sha256}) - the file was removed")
        return False
    log(f"SHA-256 {digest}" + (" OK" if rel.sha256 else " (rolling snapshot: recorded)"))
    target = tools_root() / tool
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    try:
        ok = _safe_extract(tmp, target, log)
    except (zipfile.BadZipFile, OSError) as e:
        log(f"Could not unpack {tmp.name}: {e}")
        ok = False
    tmp.unlink(missing_ok=True)
    if not ok:
        return False
    (target / "RADIDE-SOURCE.json").write_text(json.dumps(
        {"tool": tool, "version": rel.version, "url": rel.url, "sha256": digest, "pinned": bool(rel.sha256),
         "licence": rel.licence, "page": rel.page}, indent=1), encoding="utf-8")
    found = find(rel.exes[0])
    log(f"Installed {TOOL_TITLES[tool]} into {target}" if found else f"{rel.exes[0]} still not found in {target}")
    return bool(found)


def ensure(exe: str, log=print, download: bool = True) -> str:
    """Path of *exe*; its package is downloaded when missing (and *download*). "" = not available."""
    path = find(exe)
    if path or not download:
        return path
    tool = EXE_TOOL.get(exe, exe)
    if tool not in RELEASES:
        log(missing_hint(exe))
        return ""
    log(f"{TOOL_TITLES[tool]} is missing - downloading the official portable build (one time only)")
    return find(exe) if install(tool, log) else ""


def version(exe: str) -> str:
    path = find(exe)
    if not path:
        return ""
    args = {"dasm": [path], "sjasmplus": [path, "--version"]}.get(exe, [path, "--version"])
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=15, creationflags=NO_WINDOW,
                           errors="replace")
    except (OSError, subprocess.SubprocessError):
        return ""
    for line in (r.stdout + "\n" + r.stderr).splitlines():
        if line.strip():
            return line.strip()
    return ""


__all__ = ["RELEASES", "TOOL_TITLES", "cc65_home", "ensure", "find", "install", "missing_hint", "status",
           "tools_root", "version"]
