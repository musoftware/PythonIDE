"""Optional asm-lsp language server (https://github.com/bergercookie/asm-lsp).

asm-lsp publishes prebuilt binaries for Linux and macOS only, so on Windows it is used when it is already on
PATH, in ``%LOCALAPPDATA%\\RADIDE\\tools\\asm-lsp\\bin`` or in ``~/.cargo/bin``. ``install()`` builds it from
crates.io (the official package registry of the project) with ``cargo install asm-lsp --root <tools>\\asm-lsp``
when a Rust toolchain is available. The built-in provider (radide/asm_intel/engine.py) is always the fallback
and its items are merged with the server's completions (radide/features/asm_ide.py).

Set QSettings ``asm/useAsmLsp`` to ``false`` to keep the built-in provider only.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

LOCAL = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "RADIDE"
ASM_LSP_DIR = LOCAL / "tools" / "asm-lsp"
EXE = ".exe" if os.name == "nt" else ""
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NAME = "asm-lsp"
HINT = "cargo install asm-lsp (official crate) into tools\\asm-lsp - or put asm-lsp on PATH"


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


def _cargo() -> str:
    try:
        from ..languages.rust_bridge import find_cargo
        return find_cargo() or ""
    except Exception:  # noqa: BLE001
        return shutil.which("cargo") or ""


def can_install() -> str:
    return "" if _cargo() else "Rust (cargo) was not found - install Rust first (Tools > Toolchains)"


def install(log=print) -> bool:
    cargo = _cargo()
    if not cargo:
        log(can_install())
        return False
    ASM_LSP_DIR.mkdir(parents=True, exist_ok=True)
    argv = [cargo, "install", "asm-lsp", "--locked", "--root", str(ASM_LSP_DIR)]
    log("> " + " ".join(argv))
    try:
        p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=NO_WINDOW, timeout=3600)
    except (OSError, subprocess.SubprocessError) as e:
        log(f"failed: {e}")
        return False
    log(((p.stdout or "") + (p.stderr or "")).strip()[-4000:])
    return p.returncode == 0 and bool(find_asm_lsp())
