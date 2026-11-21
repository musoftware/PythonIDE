"""User Secrets (Visual Studio: right-click the project > Manage User Secrets).

The project gets ``<UserSecretsId>`` (a new GUID) and the secrets live outside the source tree in
``%APPDATA%\\Microsoft\\UserSecrets\\<id>\\secrets.json`` - the same file ``dotnet user-secrets``
and ``Microsoft.Extensions.Configuration.UserSecrets`` use.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from . import msprops


def secrets_root() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "Microsoft" / "UserSecrets"


def secrets_file(user_secrets_id: str) -> Path:
    return secrets_root() / user_secrets_id / "secrets.json"


def ensure_id(ms) -> str:
    """The project's UserSecretsId (written into the project file when missing)."""
    sid = ms.prop("UserSecretsId")
    if not sid:
        sid = str(uuid.uuid4())
        msprops.set_value(ms, "UserSecretsId", sid)
        ms.save()
    return sid


def open_secrets(ms) -> Path:
    """Create secrets.json (``{}``) when needed and return its path (VS opens it in the editor)."""
    p = secrets_file(ensure_id(ms))
    if not p.is_file():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{\n}\n", encoding="utf-8")
    return p


def read(ms) -> dict:
    sid = ms.prop("UserSecretsId")
    if not sid:
        return {}
    try:
        return json.loads(secrets_file(sid).read_text(encoding="utf-8-sig") or "{}")
    except (OSError, ValueError):
        return {}


def set_secret(ms, key: str, value: str) -> Path:
    p = open_secrets(ms)
    data = read(ms)
    data[key] = value
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p
