"""Publish settings of a project (Build > Publish / Create Installer).

Stored in <project>/publish.json so they travel with the project (like VB 2005's "My Project > Publish").
Secrets (the certificate password) are never written there: see radide/deploy/sign.py.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

FILE = "publish.json"


@dataclass
class SignSettings:
    enabled: bool = False
    signtool: str = ""                  # empty = auto-detect (Windows SDK)
    pfx: str = ""                       # certificate file (.pfx / .p12), relative to the project or absolute
    thumbprint: str = ""                # or: SHA1 thumbprint of a certificate in the user's certificate store
    timestamp_url: str = "http://timestamp.digicert.com"
    description: str = ""               # /d shown by Windows in the UAC prompt (default: the app name)


@dataclass
class UpdateSettings:
    enabled: bool = False
    url: str = ""                       # https://example.com/myapp/version.json
    download_url: str = ""              # written into version.json (where the new setup can be downloaded)
    check_on_start: bool = True


@dataclass
class PublishConfig:
    app_name: str = ""
    version: str = "1.0.0"
    publisher: str = ""
    url: str = ""                       # publisher web site (shown in Apps & features)
    app_id: str = ""                    # GUID; keep it stable or Windows treats a new version as another program
    exe_name: str = ""                  # file name without .exe (default: app name without spaces)
    icon: str = ""                      # .ico or .png/.jpg (converted), relative to the project
    license_file: str = ""              # .txt / .rtf shown on a license page
    readme_file: str = ""               # shown before installing (InfoBeforeFile)
    output_dir: str = "Publish"         # relative to the project
    build_kind: str = "auto"            # auto | pyinstaller | ring2exe | vbrun | bridge | flutter | folder
    prebuilt_dir: str = ""              # build_kind == folder: a folder with an already built program
    prebuilt_exe: str = ""              # ... and its main exe (relative to that folder)
    console: bool = False               # PyInstaller: keep a console window
    extra_files: list[str] = field(default_factory=list)   # more files/folders copied next to the exe
    desktop_icon: bool = True
    start_menu: bool = True
    run_after_install: bool = True
    per_user: bool = True               # install without admin rights (can still be switched in the setup)
    languages: list[str] = field(default_factory=lambda: ["English"])   # English, Arabic, French, ...
    file_ext: str = ""                  # optional file association, e.g. ".mydoc"
    file_desc: str = ""                 # "My Document"
    compression: str = "lzma2/max"
    make_installer: bool = True
    make_zip: bool = False              # also a portable .zip of the program folder
    sign: SignSettings = field(default_factory=SignSettings)
    update: UpdateSettings = field(default_factory=UpdateSettings)

    # ------------------------------------------------------------------ helpers
    def exe_base(self) -> str:
        name = self.exe_name or re.sub(r"[^A-Za-z0-9_.-]+", "", self.app_name.replace(" ", "")) or "App"
        return name[:-4] if name.lower().endswith(".exe") else name

    def numeric_version(self) -> str:
        """1.2 -> 1.2.0.0 (Windows version resources need four numbers)."""
        nums = [int(n) for n in re.findall(r"\d+", self.version)[:4]] or [1]
        return ".".join(str(n) for n in (nums + [0, 0, 0, 0])[:4])

    def ensure_id(self) -> str:
        if not self.app_id:
            self.app_id = "{" + str(uuid.uuid4()).upper() + "}"
        return self.app_id

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PublishConfig":
        cfg = cls()
        names = {f.name for f in fields(cls)}
        for k, v in (data or {}).items():
            if k == "sign" and isinstance(v, dict):
                cfg.sign = _fill(SignSettings(), v)
            elif k == "update" and isinstance(v, dict):
                cfg.update = _fill(UpdateSettings(), v)
            elif k in names:
                setattr(cfg, k, v)
        return cfg


def _fill(obj, data: dict):
    names = {f.name for f in fields(obj)}
    for k, v in data.items():
        if k in names:
            setattr(obj, k, v)
    return obj


def defaults_for(folder: Path, project_name: str = "") -> PublishConfig:
    folder = Path(folder)
    name = project_name or folder.name
    cfg = PublishConfig(app_name=name, publisher="", exe_name="")
    for cand in ("app.ico", f"{name}.ico", "icon.ico", "Resources/app.ico", "Resources/icon.ico", "Resources/icon.png"):
        if (folder / cand).is_file():
            cfg.icon = cand
            break
    for cand in ("LICENSE.txt", "License.txt", "LICENSE", "license.rtf", "EULA.txt"):
        if (folder / cand).is_file():
            cfg.license_file = cand
            break
    cfg.ensure_id()
    return cfg


def load(folder: Path, project_name: str = "") -> PublishConfig:
    path = Path(folder) / FILE
    if path.is_file():
        try:
            cfg = PublishConfig.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if not cfg.app_name:
                cfg.app_name = project_name or Path(folder).name
            cfg.ensure_id()
            return cfg
        except (OSError, ValueError):
            pass
    return defaults_for(folder, project_name)


def save(folder: Path, cfg: PublishConfig) -> Path:
    cfg.ensure_id()
    path = Path(folder) / FILE
    path.write_text(json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def resolve(folder: Path, rel: str) -> Path | None:
    """A path from the settings (relative to the project folder or absolute), or None when empty."""
    if not rel:
        return None
    p = Path(rel)
    return p if p.is_absolute() else Path(folder) / p


__all__ = ["FILE", "PublishConfig", "SignSettings", "UpdateSettings", "defaults_for", "load", "save", "resolve"]
