"""Optional Authenticode signing with signtool (Windows SDK).

Signing is enabled only when signtool is found AND a certificate is configured: a .pfx/.p12 file or the
SHA1 thumbprint of a certificate in the user's certificate store. The .pfx password is never stored in
publish.json: it comes from the RADIDE_SIGN_PASSWORD environment variable or the OS credential store
(keyring service "RAD IDE code signing", user = the .pfx path), set from the Publish dialog.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .config import PublishConfig, SignSettings, resolve
from .tools import NO_WINDOW, find_signtool

KEYRING_SERVICE = "RAD IDE code signing"


def get_password(pfx: str) -> str:
    pw = os.environ.get("RADIDE_SIGN_PASSWORD", "")
    if pw or not pfx:
        return pw
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, str(pfx)) or ""
    except Exception:  # noqa: BLE001 - keyring missing or no backend
        return ""


def set_password(pfx: str, password: str) -> bool:
    try:
        import keyring
        if password:
            keyring.set_password(KEYRING_SERVICE, str(pfx), password)
        else:
            try:
                keyring.delete_password(KEYRING_SERVICE, str(pfx))
            except Exception:  # noqa: BLE001
                pass
        return True
    except Exception:  # noqa: BLE001
        return False


def status(folder: Path, s: SignSettings) -> tuple[bool, str]:
    """(usable, explanation) - shown in the dialog so a disabled option says why."""
    tool = find_signtool(s.signtool)
    if not tool:
        return False, ("signtool.exe was not found. Install the Windows SDK (\"Windows SDK Signing Tools\") "
                       "or set its path.")
    if s.pfx:
        p = resolve(folder, s.pfx)
        if not p or not p.is_file():
            return False, f"Certificate file not found: {s.pfx}"
        return True, f"Signs with {p.name} using {tool}"
    if s.thumbprint.strip():
        return True, f"Signs with the store certificate {s.thumbprint.strip()[:12]}... using {tool}"
    return False, "No certificate: choose a .pfx file or enter a certificate thumbprint."


def sign_command(folder: Path, cfg: PublishConfig, target: Path) -> tuple[list[str], list[str]]:
    """(command, secrets) - secrets are masked in the log."""
    s = cfg.sign
    cmd = [find_signtool(s.signtool), "sign", "/fd", "SHA256"]
    secrets = []
    if s.pfx:
        pfx = resolve(folder, s.pfx)
        cmd += ["/f", str(pfx)]
        pw = get_password(str(pfx)) or get_password(s.pfx)
        if pw:
            cmd += ["/p", pw]
            secrets.append(pw)
    else:
        cmd += ["/sha1", s.thumbprint.strip().replace(" ", "")]
    if s.timestamp_url:
        cmd += ["/tr", s.timestamp_url, "/td", "SHA256"]
    cmd += ["/d", s.description or cfg.app_name]
    if cfg.url:
        cmd += ["/du", cfg.url]
    cmd.append(str(target))
    return cmd, secrets


def sign_file(folder: Path, cfg: PublishConfig, target: Path, log=print) -> bool:
    ok, why = status(folder, cfg.sign)
    if not ok:
        log(f"Signing skipped: {why}")
        return False
    cmd, secrets = sign_command(folder, cfg, target)
    shown = " ".join("****" if c in secrets else (f'"{c}"' if " " in c else c) for c in cmd)
    log(f"Signing {target.name}: {shown}")
    r = subprocess.run(cmd, capture_output=True, text=True, creationflags=NO_WINDOW)
    out = (r.stdout + r.stderr).strip()
    for sec in secrets:
        out = out.replace(sec, "****")
    if out:
        log(out)
    if r.returncode != 0:
        log(f"signtool failed (exit code {r.returncode})")
        return False
    return True


__all__ = ["KEYRING_SERVICE", "get_password", "set_password", "sign_command", "sign_file", "status"]
