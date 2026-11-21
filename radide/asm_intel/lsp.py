"""Optional asm-lsp language server (https://github.com/bergercookie/asm-lsp).

Where it is looked up: ``%LOCALAPPDATA%\\RADIDE\\tools\\asm-lsp\\bin``, ``~/.cargo/bin``, then PATH.

``install()`` (Tools > Language Servers... > asm-lsp > Install, only on request) takes it from the project's
official GitHub release ``RELEASE``:

* Linux x86-64 / macOS (Intel, Apple silicon): the release's prebuilt archive is downloaded from
  ``github.com/bergercookie/asm-lsp/releases/download/v<RELEASE>/...``; its SHA-256 must equal the digest that
  GitHub publishes for the asset (pinned below, ``ASSETS``) - a different file is deleted.
* Windows: the release has **no Windows binary** (only Linux and macOS archives - checked with the GitHub API
  for v0.9.0 ... v0.10.1), so the same release tag is built from the official repository with cargo
  (``cargo install --git https://github.com/bergercookie/asm-lsp --tag v<RELEASE> --locked --root
  <tools>\\asm-lsp``). That needs a Rust toolchain (Tools > Toolchains); it takes a few minutes once.

The built-in provider (radide/asm_intel/engine.py) is always the fallback and its items are merged with the
server's completions (radide/features/asm_ide.py). Set QSettings ``asm/useAsmLsp`` to ``false`` to keep the
built-in provider only. Test: samples/Tests/Assembly/AsmLsp/test_asm_lsp.py (install + the IDE's LSP client).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

LOCAL = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "RADIDE"
ASM_LSP_DIR = LOCAL / "tools" / "asm-lsp"
EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NAME = "asm-lsp"
REPO = "https://github.com/bergercookie/asm-lsp"
RELEASE = "0.10.1"
# prebuilt archives of the release and the SHA-256 digests GitHub publishes for them (API "digest" field)
ASSETS = {
    ("linux", "x86_64"): ("asm-lsp-x86_64-unknown-linux-gnu.tar.gz",
                          "2a2f386c10348e365df484d5c66d084813e7dbf8ab4e9eb7a7cc0bb0acf2f8f8"),
    ("darwin", "x86_64"): ("asm-lsp-x86_64-apple-darwin.tar.gz",
                           "900c0c95bb2cf0a65102beb09031496e3ed2d31b85dbbe3ef8cae5ffbe493a07"),
    ("darwin", "arm64"): ("asm-lsp-aarch64-apple-darwin.tar.gz",
                          "affc8917d5bb6f44805c2e964ad07cf7e0799ecfaa7686f7a5cea9efa00bc575"),
}
HINT = (f"asm-lsp {RELEASE} from its official GitHub release into tools\\asm-lsp (Windows: built from the "
        "release tag with cargo - the release has no Windows binary) - or put asm-lsp on PATH")


def enabled() -> bool:
    try:
        from PyQt6.QtCore import QCoreApplication, QSettings
        org = QCoreApplication.organizationName() or "RADIDE"
        v = QSettings(org, QCoreApplication.applicationName() or org).value("asm/useAsmLsp", True)
        return str(v).lower() not in ("false", "0", "no", "off")
    except Exception:  # noqa: BLE001
        return True


def find_asm_lsp() -> str:
    for cand in (ASM_LSP_DIR / "bin" / ("asm-lsp" + EXE), Path.home() / ".cargo" / "bin" / ("asm-lsp" + EXE)):
        if cand.is_file():
            return str(cand)
    return shutil.which("asm-lsp") or ""


def server_command() -> list[str] | None:
    if not enabled():
        return None
    exe = find_asm_lsp()
    return [exe] if exe else None


def release_asset() -> tuple[str, str] | None:
    """(file name, sha256) of the prebuilt archive for this machine, None when the release has none (Windows)."""
    system = {"linux": "linux", "darwin": "darwin"}.get(sys.platform if sys.platform != "linux2" else "linux")
    machine = platform.machine().lower()
    machine = {"amd64": "x86_64", "aarch64": "arm64"}.get(machine, machine)
    return ASSETS.get((system, machine)) if system else None


def asset_url(name: str) -> str:
    return f"{REPO}/releases/download/v{RELEASE}/{name}"


def _cargo() -> str:
    try:
        from ..languages.rust_bridge import find_cargo
        return find_cargo() or ""
    except Exception:  # noqa: BLE001
        return shutil.which("cargo") or ""


def can_install() -> str:
    if release_asset() is not None:
        return ""
    return "" if _cargo() else ("the asm-lsp release has no Windows binary and Rust (cargo) was not found to "
                                "build it - install Rust first (Tools > Toolchains)")


def install_command() -> list[str]:
    """The cargo command that builds the release tag (Windows and any platform without a prebuilt archive)."""
    return [_cargo() or "cargo", "install", "--git", REPO, "--tag", f"v{RELEASE}", "--locked", "--root",
            str(ASM_LSP_DIR), "asm-lsp"]


def _download_release(name: str, sha256: str, log) -> bool:
    url = asset_url(name)
    tmp = ASM_LSP_DIR / "_download" / name
    tmp.parent.mkdir(parents=True, exist_ok=True)
    log(f"Downloading {url}")
    h = hashlib.sha256()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
        with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as f:
            for chunk in iter(lambda: r.read(1 << 20), b""):
                h.update(chunk)
                f.write(chunk)
    except OSError as e:
        tmp.unlink(missing_ok=True)
        log(f"Download failed: {e}")
        return False
    if h.hexdigest() != sha256:
        tmp.unlink(missing_ok=True)
        log(f"SHA-256 mismatch (got {h.hexdigest()}, GitHub publishes {sha256}) - the file was removed")
        return False
    bindir = ASM_LSP_DIR / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tmp, "r:gz") as tar:
        member = next((m for m in tar.getmembers() if m.isfile() and Path(m.name).name == "asm-lsp"), None)
        if member is None:
            log("asm-lsp was not found in the archive")
            return False
        src = tar.extractfile(member)
        target = bindir / "asm-lsp"
        with open(target, "wb") as out:
            shutil.copyfileobj(src, out)
        target.chmod(0o755)
    tmp.unlink(missing_ok=True)
    return True


def install(log=print) -> bool:
    """Install asm-lsp RELEASE into tools/asm-lsp (blocking: run it in a thread from the UI)."""
    why = can_install()
    if why:
        log(why)
        return False
    ASM_LSP_DIR.mkdir(parents=True, exist_ok=True)
    asset = release_asset()
    if asset is not None:
        ok = _download_release(*asset, log)
        how = asset_url(asset[0])
    else:
        argv = install_command()
        log("asm-lsp's GitHub release has no Windows binary: building the release tag with cargo (a few minutes)")
        log("> " + " ".join(argv))
        try:
            p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               creationflags=NO_WINDOW, timeout=3600)
        except (OSError, subprocess.SubprocessError) as e:
            log(f"failed: {e}")
            return False
        log(((p.stdout or "") + (p.stderr or "")).strip()[-4000:])
        ok = p.returncode == 0
        how = f"{REPO} tag v{RELEASE} (cargo)"
    ok = ok and bool(find_asm_lsp())
    if ok:
        (ASM_LSP_DIR / "RADIDE-SOURCE.json").write_text(json.dumps({"tool": NAME, "version": RELEASE,
                                                                    "source": how}, indent=1), encoding="utf-8")
        log(f"Installed asm-lsp {RELEASE}: {find_asm_lsp()}")
    return ok
