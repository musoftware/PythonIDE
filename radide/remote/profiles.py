"""Saved SSH hosts (QSettings "remote/hosts", no secrets) and their passwords / key passphrases in the OS
credential store (keyring -> Windows Credential Manager).  Without a working keyring nothing secret is
saved: the IDE asks every time."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QSettings

from .ssh import data_dir


def settings() -> QSettings:
    org = QCoreApplication.organizationName()
    if org.upper().startswith("RADIDE-TEST"):
        return QSettings(org, QCoreApplication.applicationName() or org)
    return QSettings("RADIDE", "RADIDE")


def _service() -> str:
    org = QCoreApplication.organizationName()
    return (org if org.upper().startswith("RADIDE-TEST") else "RADIDE") + "-remote"


def _keyring():
    try:
        import keyring  # type: ignore
        kr = keyring.get_keyring()
        if "fail" in type(kr).__module__.lower() or "null" in type(kr).__name__.lower():
            return None
        return keyring
    except Exception:  # noqa: BLE001
        return None


def keyring_available() -> bool:
    return _keyring() is not None


def account(host: dict, what: str = "password") -> str:
    return f"{what}:{host.get('user', '')}@{host.get('host', '')}:{int(host.get('port') or 22)}"


def get_secret(host: dict, what: str = "password") -> str:
    kr = _keyring()
    if kr is None:
        return ""
    try:
        return kr.get_password(_service(), account(host, what)) or ""
    except Exception:  # noqa: BLE001
        return ""


def set_secret(host: dict, value: str, what: str = "password") -> bool:
    """Store (or delete when empty). False when no credential store is available."""
    kr = _keyring()
    if kr is None:
        return False
    try:
        if value:
            kr.set_password(_service(), account(host, what), value)
        else:
            try:
                kr.delete_password(_service(), account(host, what))
            except Exception:  # noqa: BLE001 - not stored
                pass
        return True
    except Exception:  # noqa: BLE001
        return False


def host_id(h: dict) -> str:
    return f"{h.get('user', '')}@{h.get('host', '')}:{int(h.get('port') or 22)}"


def load_hosts() -> list[dict]:
    raw = settings().value("remote/hosts", "") or ""
    try:
        data = json.loads(raw) if isinstance(raw, str) and raw else []
        return [d for d in data if isinstance(d, dict) and d.get("host")]
    except ValueError:
        return []


def save_host(h: dict) -> None:
    clean = {k: h.get(k) for k in ("name", "host", "port", "user", "auth", "key_file", "folder", "run_cmd",
                                   "build_cmd", "remember")}
    hosts = [x for x in load_hosts() if host_id(x) != host_id(clean)]
    hosts.insert(0, clean)
    settings().setValue("remote/hosts", json.dumps(hosts[:20]))


def forget_host(h: dict) -> None:
    hosts = [x for x in load_hosts() if host_id(x) != host_id(h)]
    settings().setValue("remote/hosts", json.dumps(hosts))
    set_secret(h, "", "password")
    set_secret(h, "", "passphrase")


def update_host(h: dict, **changes) -> dict:
    """Change saved fields (run/build commands, last folder) of a saved host."""
    hosts = load_hosts()
    for x in hosts:
        if host_id(x) == host_id(h):
            x.update(changes)
            settings().setValue("remote/hosts", json.dumps(hosts))
            return x
    h = {**h, **changes}
    return h


def cache_root(key: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.@-]+", "_", key)
    p = data_dir() / "cache" / safe
    p.mkdir(parents=True, exist_ok=True)
    return p


def cache_path(key: str, remote_path: str) -> Path:
    parts = [re.sub(r'[<>:"\\|?*\x00-\x1f]', "_", x) for x in remote_path.split("/") if x not in ("", ".", "..")]
    return cache_root(key).joinpath(*parts) if parts else cache_root(key) / "_root"


def default_key_files() -> list[str]:
    ssh = Path(os.path.expanduser("~")) / ".ssh"
    return [str(ssh / n) for n in ("id_ed25519", "id_ecdsa", "id_rsa") if (ssh / n).is_file()]


__all__ = ["load_hosts", "save_host", "forget_host", "update_host", "get_secret", "set_secret", "host_id",
           "keyring_available", "cache_path", "cache_root", "default_key_files", "settings"]
