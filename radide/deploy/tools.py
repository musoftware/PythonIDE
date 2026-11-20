"""External tools used by Build > Publish: Inno Setup (ISCC.exe), signtool, PyInstaller.

Inno Setup is downloaded on demand from the official GitHub releases of jrsoftware/issrc and installed
portably (no admin, no registry, no PATH change) into %LOCALAPPDATA%\\RADIDE\\tools\\innosetup with the
official setup's own switches: /VERYSILENT /CURRENTUSER /PORTABLE=1 /DIR=...
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

INNO_VERSION = "7.1.1"
INNO_URL = f"https://github.com/jrsoftware/issrc/releases/download/is-{INNO_VERSION.replace('.', '_')}/" \
           f"innosetup-{INNO_VERSION}-x64.exe"
INNO_SITE = "https://jrsoftware.org/isinfo.php"

NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def tools_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "RADIDE" / "tools"


def inno_dir() -> Path:
    return tools_root() / "innosetup"


# ------------------------------------------------------------------ Inno Setup
def find_iscc() -> str:
    """ISCC.exe (portable copy first, then a normal Inno Setup 6/7 installation, then PATH)."""
    cands = [inno_dir() / "ISCC.exe"]
    for env in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        root = os.environ.get(env)
        if root:
            for ver in ("7", "6"):
                cands.append(Path(root) / f"Inno Setup {ver}" / "ISCC.exe")
                cands.append(Path(root) / "Programs" / f"Inno Setup {ver}" / "ISCC.exe")
    for c in cands:
        if c.is_file():
            return str(c)
    return shutil.which("ISCC") or shutil.which("iscc") or ""


def inno_languages(iscc: str = "") -> list[str]:
    """Names usable in PublishConfig.languages (English + Languages\\*.isl)."""
    iscc = iscc or find_iscc()
    names = ["English"]
    if iscc:
        names += sorted(Path(p).stem for p in glob.glob(str(Path(iscc).parent / "Languages" / "*.isl")))
    return names


def install_innosetup(log=print) -> str:
    """Download the official Inno Setup installer and install it portably. Returns ISCC.exe or ""."""
    if os.name != "nt":
        log("Inno Setup runs on Windows only.")
        return ""
    found = find_iscc()
    if found:
        return found
    dl = tools_root() / "_download" / "innosetup"
    dl.mkdir(parents=True, exist_ok=True)
    setup = dl / Path(INNO_URL).name
    if not setup.is_file() or setup.stat().st_size < 1_000_000:
        log(f"Downloading Inno Setup {INNO_VERSION} from {INNO_URL} ...")
        try:
            req = urllib.request.Request(INNO_URL, headers={"User-Agent": "RAD-IDE"})
            with urllib.request.urlopen(req, timeout=120) as r, open(setup, "wb") as f:
                shutil.copyfileobj(r, f)
        except OSError as ex:
            log(f"Download failed: {ex}\nInstall Inno Setup yourself from {INNO_SITE}")
            return ""
    if not _signed_ok(setup, log):
        return ""
    target = inno_dir()
    log(f"Installing Inno Setup (portable) into {target} ...")
    r = subprocess.run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
                        "/PORTABLE=1", "/NOICONS", f"/DIR={target}"], creationflags=NO_WINDOW)
    if r.returncode != 0 or not (target / "ISCC.exe").is_file():
        log(f"The Inno Setup installer failed (exit code {r.returncode}).")
        return ""
    _record("innosetup", INNO_VERSION, INNO_URL, hashlib.sha256(setup.read_bytes()).hexdigest())
    return str(target / "ISCC.exe")


def _signed_ok(path: Path, log) -> bool:
    """The download must carry a valid Authenticode signature (checked with PowerShell)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"(Get-AuthenticodeSignature -LiteralPath '{path}').Status"],
                           capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)
        status = r.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return True             # cannot check: trust the HTTPS download from GitHub
    if status and status != "Valid":
        log(f"The downloaded Inno Setup installer has no valid signature ({status}); not installing it.")
        return False
    return True


def _record(tool: str, version: str, url: str, sha256: str) -> None:
    try:
        path = tools_root() / "installed.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
        data[tool] = {"version": version, "url": url, "sha256": sha256}
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except (OSError, ValueError):
        pass


# ------------------------------------------------------------------ signtool
def find_signtool(configured: str = "") -> str:
    """signtool.exe of the newest Windows SDK (x64 first), or ""."""
    if configured and Path(configured).is_file():
        return configured
    hits = []
    for env in ("ProgramFiles(x86)", "ProgramFiles"):
        root = os.environ.get(env)
        if root:
            hits += glob.glob(os.path.join(root, "Windows Kits", "10", "bin", "10.*", "x64", "signtool.exe"))
            hits += glob.glob(os.path.join(root, "Windows Kits", "10", "bin", "x64", "signtool.exe"))
    if hits:
        def ver(p):
            parts = Path(p).parts
            v = next((x for x in parts if x.startswith("10.")), "0")
            return tuple(int(n) for n in v.split(".") if n.isdigit())
        return max(hits, key=ver)
    for env in ("ProgramFiles(x86)", "ProgramFiles"):
        root = os.environ.get(env)
        if root:
            p = Path(root) / "Microsoft SDKs" / "ClickOnce" / "SignTool" / "signtool.exe"
            if p.is_file():
                return str(p)
    return shutil.which("signtool") or ""


# ------------------------------------------------------------------ PyInstaller
def has_pyinstaller(python: str) -> bool:
    try:
        r = subprocess.run([python, "-m", "PyInstaller", "--version"], capture_output=True, text=True,
                           timeout=120, creationflags=NO_WINDOW)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def build_env_python(base_python: str, log=print) -> str:
    """A private build venv (with the base interpreter's site-packages visible) that has PyInstaller.
    Used when the project has no .venv, so nothing is installed into the user's global Python."""
    try:
        r = subprocess.run([base_python, "-c", "import sys; print('%d%d' % sys.version_info[:2])"],
                           capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)
        tag = r.stdout.strip() or "py"
    except (OSError, subprocess.TimeoutExpired) as ex:
        log(f"Python not usable: {base_python} ({ex})")
        return ""
    key = hashlib.sha1(str(Path(base_python).resolve()).lower().encode()).hexdigest()[:8]
    env = tools_root().parent / "buildenv" / f"py{tag}-{key}"
    py = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.is_file():
        log(f"Creating a build environment {env} ...")
        r = subprocess.run([base_python, "-m", "venv", "--system-site-packages", str(env)],
                           creationflags=NO_WINDOW)
        if r.returncode != 0 or not py.is_file():
            log("Could not create the build environment.")
            return ""
    return str(py) if ensure_pyinstaller(str(py), log) else ""


def ensure_pyinstaller(python: str, log=print) -> bool:
    if has_pyinstaller(python):
        return True
    log(f"Installing PyInstaller into {python} ...")
    r = subprocess.run([python, "-m", "pip", "install", "--disable-pip-version-check", "pyinstaller"],
                       creationflags=NO_WINDOW)
    return r.returncode == 0 and has_pyinstaller(python)


def ide_python() -> str:
    """The interpreter running the IDE (has tkinter + PyInstaller in the IDE's .venv)."""
    return sys.executable


__all__ = ["INNO_URL", "INNO_VERSION", "build_env_python", "ensure_pyinstaller", "find_iscc", "find_signtool",
           "has_pyinstaller", "ide_python", "inno_dir", "inno_languages", "install_innosetup", "tools_root"]
