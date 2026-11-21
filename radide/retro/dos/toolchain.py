"""Compilers of the DOS projects (no Qt in here).

    key          what                                   official source (portable, no admin, no PATH change)
    freebasic    FreeBASIC 1.10.1, DOS build            SourceForge project "fbc" (Binaries-DOS)          GPL/LGPL
    fpc          Free Pascal 3.2.2 i8086-msdos cross     downloads.freepascal.org (Inno Setup package,      GPL/LGPL
                 compiler (ppcross8086 + RTL units)      unpacked with innoextract, never run)
    openwatcom   Open Watcom v2 (wcl / wlink, 16-bit     github.com/open-watcom/open-watcom-v2 releases     Sybase OSL
                 DOS libraries, DOS/4GW)                 (dated build, ow-snapshot.tar.xz)
    jwasm        JWasm 2.21 (MASM-compatible)            github.com/Baron-von-Riedesel/JWasm releases       Sybase OSL
    cwsdpmi      CWSDPMI r7 (DPMI host for FreeBASIC /   DJGPP official site delorie.com (v2misc)          free
                 DJGPP programs)
    innoextract  innoextract 1.9 (reads the FPC package) github.com/dscharrer/innoextract releases          zlib

Everything goes into ``%LOCALAPPDATA%\\RADIDE\\tools\\<key>`` with a ``RADIDE-SOURCE.json`` (version, URL, SHA-256).
The SHA-256 is the GitHub release digest where GitHub publishes one (Open Watcom, JWasm); FreeBASIC publishes
SHA-1 sums (checked as well); the other values were measured from the official files when this version of
RAD IDE was written. A changed file is refused and the user is sent to the official page.

Proprietary DOS compilers (Microsoft QBasic / QuickBASIC / MS-DOS, Borland Turbo Pascal / Turbo C) are never
downloaded: the user can point RAD IDE at their own copy (``set_user_path``); it runs inside DOSBox-X.
DJGPP has no official Windows-hosted build: a user-installed ``i586-pc-msdosdjgpp-gcc`` is used when configured.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def local_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "RADIDE"


def tools_root() -> Path:
    return local_root() / "tools"


@dataclass(frozen=True)
class Release:
    key: str
    title: str
    version: str
    url: str
    sha256: str
    page: str
    licence: str
    archive: str                       # zip | tar.xz | inno
    strip: str = ""                    # leading folder removed when extracting
    include: tuple = ()                # only these prefixes (after strip) are extracted; () = everything
    sha1: str = ""                     # published SHA-1 (FreeBASIC sha1sums.txt)
    size_mb: int = 0                   # download size (shown in the dialog)
    exe: str = ""                      # file (relative to the tool folder) that proves the install
    extra: dict = field(default_factory=dict)


_FPC_MODELS = ("tiny", "small", "medium", "compact", "large")

RELEASES: dict[str, Release] = {r.key: r for r in [
    Release("freebasic", "FreeBASIC (DOS build)", "1.10.1",
            "https://downloads.sourceforge.net/project/fbc/FreeBASIC-1.10.1/Binaries-DOS/FreeBASIC-1.10.1-dos.zip",
            "895723a1bb9c0d6f8edf5d6c26d567238f5bd271276041666133c66a1c12c880",
            "https://sourceforge.net/projects/fbc/files/FreeBASIC-1.10.1/Binaries-DOS/", "GPL-2.0+ / LGPL (runtime)",
            "zip", strip="FreeBASIC-1.10.1-dos/", include=("fbc.exe", "bin/", "inc/", "lib/", "doc/", "readme.txt",
                                                           "changelog.txt"),
            sha1="3d15f7e52ada9ad189a01bdf48f4430893c77642", size_mb=8, exe="fbc.exe"),
    Release("fpc", "Free Pascal i8086-msdos cross compiler", "3.2.2",
            "https://downloads.freepascal.org/fpc/dist/3.2.2/i386-win32/fpc-3.2.2.i386-win32.cross.i8086-msdos.exe",
            "84026e57add128f6ba25c1ac713514c0a79a7d0de7e4881d30ac561d45d5cccc",
            "https://www.freepascal.org/download.html", "GPL-2.0+ / modified LGPL (RTL)", "inno",
            strip="app/", include=("bin/", "doc/") + tuple(f"units/msdos/8086-{m}/" for m in _FPC_MODELS),
            size_mb=162, exe="bin/i386-win32/ppcross8086.exe"),
    Release("openwatcom", "Open Watcom C/C++ v2", "2026-11-01",
            "https://github.com/open-watcom/open-watcom-v2/releases/download/2026-11-01-Build/ow-snapshot.tar.xz",
            "89e90b7544cf3ea4a38124ec4c104a5027f31101405d7115c3f833daa465bb48",
            "https://github.com/open-watcom/open-watcom-v2/releases", "Sybase Open Watcom Public License 1.0",
            "tar.xz", include=("binnt64/", "binnt/", "binw/", "h/", "lib286/", "lib386/", "license.txt",
                               "readme.txt"),
            size_mb=150, exe="binnt64/wcl.exe"),
    Release("jwasm", "JWasm (MASM-compatible assembler)", "2.21",
            "https://github.com/Baron-von-Riedesel/JWasm/releases/download/v2.21/JWasm_v221_win32.zip",
            "6aec90bdbbfea705bdcdc64ab3bf8424cb2cecb93b88613ff0f70ff366e2cdca",
            "https://github.com/Baron-von-Riedesel/JWasm/releases", "Sybase Open Watcom Public License 1.0", "zip",
            size_mb=1, exe="JWasm.exe"),
    Release("cwsdpmi", "CWSDPMI r7 (DPMI host)", "r7",
            "https://www.delorie.com/pub/djgpp/current/v2misc/csdpmi7b.zip",
            "deacda0488e1cdd7c4a9f32fab45662b34c0ed6b2d7d4d13bc07041b62004a8c",
            "https://www.delorie.com/djgpp/", "freeware (C. W. Sandmann), redistributable unmodified", "zip",
            size_mb=1, exe="bin/CWSDPMI.EXE"),
    Release("innoextract", "innoextract (reads the Free Pascal package)", "1.9",
            "https://github.com/dscharrer/innoextract/releases/download/1.9/innoextract-1.9-windows.zip",
            "6989342c9b026a00a72a38f23b62a8e6a22cc5de69805cf47d68ac2fec993065",
            "https://constexpr.org/innoextract/", "zlib", "zip", size_mb=1, exe="innoextract.exe"),
]}

# which free compiler builds which project kind
COMPILER_FOR_KIND = {"qbasic": "freebasic", "pascal": "fpc", "c": "openwatcom", "asm": "jwasm", "batch": ""}
NEEDS = {"freebasic": ["freebasic", "cwsdpmi"], "fpc": ["fpc"], "openwatcom": ["openwatcom"], "jwasm": ["jwasm"]}

# the user's own copies of proprietary DOS tools (folders mounted in DOSBox-X)
USER_TOOLS = {
    "qbasic": ("Microsoft QBasic (QBASIC.EXE)", ("QBASIC.EXE",)),
    "quickbasic": ("Microsoft QuickBASIC 4.5 (QB.EXE, BC.EXE, LINK.EXE)", ("QB.EXE", "BC.EXE")),
    "turbopascal": ("Borland Turbo Pascal (TPC.EXE / TURBO.EXE)", ("TPC.EXE", "TURBO.EXE")),
    "turboc": ("Borland Turbo C / C++ (TCC.EXE / TC.EXE)", ("TCC.EXE", "TC.EXE", "BCC.EXE")),
    "djgpp": ("DJGPP cross compiler (i586-pc-msdosdjgpp-gcc.exe)", ("i586-pc-msdosdjgpp-gcc.exe",
                                                                    "i686-pc-msdosdjgpp-gcc.exe")),
    "dosbox-x": ("DOSBox-X (dosbox-x.exe), when not downloaded by RAD IDE", ("dosbox-x.exe",)),
}


# ====================================================================== configuration (no Qt)
def config_file() -> Path:
    """JSON with the user's tool paths. RADIDE_DOS_CONFIG overrides it (tests)."""
    env = os.environ.get("RADIDE_DOS_CONFIG")
    return Path(env) if env else local_root() / "retro" / "dos" / "config.json"


def load_config() -> dict:
    try:
        return json.loads(config_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(cfg: dict) -> None:
    p = config_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, indent=1), encoding="utf-8")


def user_path(key: str) -> str:
    """Folder (or exe) of the user's own *key* tool (USER_TOOLS), "" when not configured / gone."""
    p = load_config().get("paths", {}).get(key, "")
    return p if p and Path(p).exists() else ""


def set_user_path(key: str, path: str) -> None:
    cfg = load_config()
    paths = cfg.setdefault("paths", {})
    if path:
        paths[key] = str(path)
    else:
        paths.pop(key, None)
    save_config(cfg)


def user_tool(key: str) -> str:
    """The executable of the user's own *key* tool (first of USER_TOOLS names found), or ""."""
    p = user_path(key)
    if not p:
        if key == "djgpp":
            for n in USER_TOOLS["djgpp"][1]:
                w = shutil.which(n)
                if w:
                    return w
        return ""
    path = Path(p)
    if path.is_file():
        return str(path)
    for n in USER_TOOLS.get(key, ("", ()))[1]:
        for cand in (path / n, path / "BIN" / n, path / "bin" / n):
            if cand.is_file():
                return str(cand)
        for cand in path.iterdir() if path.is_dir() else []:
            if cand.name.lower() == n.lower() and cand.is_file():
                return str(cand)
    return ""


# ====================================================================== lookup
def tool_dir(key: str) -> Path:
    return tools_root() / key


def find(key: str) -> str:
    """Proof file of a downloaded tool (RELEASES[key].exe) or ""."""
    rel = RELEASES.get(key)
    if rel is None:
        return ""
    p = tool_dir(key) / rel.exe
    if p.is_file():
        return str(p)
    if key == "innoextract":                      # the Lazarus support downloads the same tool
        alt = tools_root() / "innoextract" / "innoextract.exe"
        return str(alt) if alt.is_file() else ""
    return ""


def freebasic_dir() -> str:
    exe = find("freebasic")
    return str(Path(exe).parent) if exe else ""


def cwsdpmi_exe() -> str:
    return find("cwsdpmi")


def fpc_compiler() -> str:
    return find("fpc")


def fpc_units(model: str = "small") -> str:
    model = model.lower() if model.lower() in _FPC_MODELS else "small"
    d = tool_dir("fpc") / "units" / "msdos" / f"8086-{model}"
    return str(d) if d.is_dir() else ""


def watcom_root() -> str:
    exe = find("openwatcom")
    return str(Path(exe).parent.parent) if exe else ""


def watcom_env(base: dict | None = None) -> dict:
    """Environment for wcl / wlink: WATCOM, INCLUDE, PATH (binnt64 + binnt)."""
    env = dict(base if base is not None else os.environ)
    root = watcom_root()
    if not root:
        return env
    env["WATCOM"] = root
    env["INCLUDE"] = str(Path(root) / "h")
    env["PATH"] = os.pathsep.join([str(Path(root) / "binnt64"), str(Path(root) / "binnt"), env.get("PATH", "")])
    env.pop("LIB", None)
    return env


def jwasm_exe() -> str:
    return find("jwasm")


def status() -> list[dict]:
    """One row per downloadable tool + one per user tool."""
    rows = []
    for r in RELEASES.values():
        rows.append({"key": r.key, "title": r.title, "version": r.version, "path": find(r.key), "page": r.page,
                     "licence": r.licence, "size_mb": r.size_mb, "user": False})
    for k, (title, _names) in USER_TOOLS.items():
        rows.append({"key": k, "title": title, "version": "", "path": user_tool(k) or user_path(k), "page": "",
                     "licence": "your own copy" if k not in ("djgpp", "dosbox-x") else "", "size_mb": 0,
                     "user": True})
    return rows


def missing_hint(key: str) -> str:
    rel = RELEASES.get(key)
    if rel is None:
        return f"{key} is not available."
    return (f"{rel.title} {rel.version} was not found. RAD IDE downloads it into {tool_dir(key)} (official "
            f"{rel.url}, about {rel.size_mb} MB) - Tools > DOS Toolchains..., or download it yourself from "
            f"{rel.page}.")


# ====================================================================== download
def download_verified(url: str, sha256: str, dest: Path, log=print, sha1: str = "") -> bool:
    """Download *url* to *dest* (an existing file with the right SHA-256 is reused)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and _sha256(dest) == sha256.lower():
        log(f"Using the already downloaded {dest.name} (SHA-256 OK)")
        return True
    log(f"Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
    h = hashlib.sha256()
    h1 = hashlib.sha1()
    part = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(req, timeout=180) as r, open(part, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                h.update(chunk)
                h1.update(chunk)
                f.write(chunk)
    except OSError as e:
        part.unlink(missing_ok=True)
        log(f"Download failed: {e}")
        return False
    if h.hexdigest().lower() != sha256.lower() or (sha1 and h1.hexdigest().lower() != sha1.lower()):
        part.unlink(missing_ok=True)
        log(f"SHA-256 mismatch for {url} (got {h.hexdigest()}) - the file was removed")
        return False
    try:
        os.replace(part, dest)
    except OSError as e:
        log(f"Cannot move the download into place: {e}")
        return False
    log(f"SHA-256 OK ({sha256[:16]}...)")
    return True


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe(name: str) -> bool:
    n = name.replace("\\", "/")
    return bool(n) and not (n.startswith("/") or ".." in Path(n).parts or ":" in n)


def _wanted(rel: Release, name: str) -> str:
    """Name inside the tool folder, or "" when the member is skipped."""
    n = name.replace("\\", "/")
    if n.startswith("./"):
        n = n[2:]
    if rel.strip:
        if not n.startswith(rel.strip):
            return ""
        n = n[len(rel.strip):]
    if not n or n.endswith("/"):
        return ""
    if rel.include and not any(n == p or n.startswith(p) for p in rel.include):
        return ""
    return n


def _extract_zip(rel: Release, archive: Path, target: Path, log) -> bool:
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if not _safe(info.filename) and not info.filename.endswith("/"):
                log(f"unsafe path in the archive: {info.filename}")
                return False
        for info in z.infolist():
            n = _wanted(rel, info.filename)
            if not n:
                continue
            out = target / n
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return True


def _extract_tar(rel: Release, archive: Path, target: Path, log) -> bool:
    with tarfile.open(archive, "r:*") as t:
        for m in t:
            if not (m.isfile() or m.isdir()):
                continue                          # no links / devices
            if m.name not in (".", "./") and not _safe(m.name):
                log(f"unsafe path in the archive: {m.name}")
                return False
            if not m.isfile():
                continue
            n = _wanted(rel, m.name)
            if not n:
                continue
            out = target / n
            out.parent.mkdir(parents=True, exist_ok=True)
            src = t.extractfile(m)
            if src is None:
                continue
            with src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
    return True


def _extract_inno(rel: Release, archive: Path, target: Path, log) -> bool:
    ie = ensure("innoextract", log)
    if not ie:
        return False
    tmp = target.parent / f"_{rel.key}_extract"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    args = [ie, "-s", "-d", str(tmp)]
    for inc in rel.include:
        args += ["-I", (rel.strip + inc).rstrip("/").replace("/", "\\")]
    args.append(str(archive))
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=1800, creationflags=NO_WINDOW,
                           errors="replace")
    except (OSError, subprocess.SubprocessError) as e:
        log(f"innoextract failed: {e}")
        return False
    src = tmp / rel.strip.rstrip("/") if rel.strip else tmp
    if r.returncode != 0 or not src.is_dir():
        log(f"innoextract failed: {(r.stderr or r.stdout).strip()[:400]}")
        return False
    for item in src.iterdir():
        shutil.move(str(item), str(target / item.name))
    shutil.rmtree(tmp, ignore_errors=True)
    return True


def install(key: str, log=print) -> bool:
    """Download and unpack *key* into tools\\<key> (blocking: run it in a worker thread from the UI)."""
    rel = RELEASES.get(key)
    if rel is None:
        log(f"Unknown DOS tool: {key}")
        return False
    if key == "innoextract" and find(key) and not (tool_dir(key) / "RADIDE-SOURCE.json").exists():
        return True                                   # shared with the Lazarus support: keep it
    tmp =tools_root() / "_download" / Path(rel.url).name
    if not download_verified(rel.url, rel.sha256, tmp, log, rel.sha1):
        log(f"Download {rel.title} yourself from {rel.page} and unpack it into {tool_dir(key)}")
        return False
    target = tool_dir(key)
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    log(f"Unpacking {tmp.name} into {target} ...")
    extract = {"zip": _extract_zip, "tar.xz": _extract_tar, "inno": _extract_inno}[rel.archive]
    try:
        ok = extract(rel, tmp, target, log)
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as e:
        log(f"Unpacking failed: {e}")
        ok = False
    if not ok:
        return False
    (target / "RADIDE-SOURCE.json").write_text(json.dumps(
        {"tool": key, "title": rel.title, "version": rel.version, "url": rel.url, "sha256": rel.sha256,
         "licence": rel.licence, "page": rel.page}, indent=1), encoding="utf-8")
    if key == "fpc":
        _write_fpc_cfg(target)
    try:
        tmp.unlink(missing_ok=True)
    except OSError:
        pass
    ok = bool(find(key))
    log(f"Installed {rel.title} {rel.version} into {target}" if ok else f"{rel.title}: not found in {target}")
    return ok


def _write_fpc_cfg(target: Path) -> None:
    """A fpc.cfg next to ppcross8086 so that the compiler also works from a plain command line."""
    b = target / "bin" / "i386-win32"
    if b.is_dir():
        (b / "fpc.cfg").write_text(
            "# written by RAD IDE (Free Pascal i8086-msdos cross compiler)\n-Tmsdos\n-XX\n"
            f"-Fu{target}\\units\\msdos\\8086-$fpcsubarch\\*\n".replace("$fpcsubarch", "small")
            + f"-FD{b}\n", encoding="ascii")


def ensure(key: str, log=print, download: bool = True) -> str:
    exe = find(key)
    if exe or not download or key not in RELEASES:
        return exe
    log(f"{RELEASES[key].title} is missing - downloading the official portable build (one time only)")
    return find(key) if install(key, log) else ""


def ensure_for(compiler: str, log=print, download: bool = True) -> bool:
    """Every tool *compiler* ("freebasic", "fpc", "openwatcom", "jwasm") needs."""
    return all(ensure(k, log, download) for k in NEEDS.get(compiler, []))


def uninstall(key: str) -> bool:
    d = tool_dir(key)
    if (d / "RADIDE-SOURCE.json").is_file():
        shutil.rmtree(d, ignore_errors=True)
        return True
    return False


# ====================================================================== DOSBox-X (through the emu slice)
def dosbox_exe(download: bool = False, log=print) -> str:
    """dosbox-x.exe: the user's configured one, else radide.retro.emu (download when *download*), else PATH."""
    own = user_tool("dosbox-x")
    if own:
        return own
    try:
        from ..emu import manager
        exe = manager.find("dosbox-x")
        if not exe and download:
            exe = manager.ensure("dosbox-x", log, download=True)
        if exe:
            return exe
    except Exception:  # noqa: BLE001 - the emu slice is optional
        pass
    return shutil.which("dosbox-x") or ""


__all__ = ["COMPILER_FOR_KIND", "RELEASES", "USER_TOOLS", "dosbox_exe", "ensure", "ensure_for", "find",
           "fpc_compiler", "fpc_units", "freebasic_dir", "install", "jwasm_exe", "load_config", "missing_hint",
           "save_config", "set_user_path", "status", "tools_root", "uninstall", "user_path", "user_tool",
           "watcom_env", "watcom_root"]
