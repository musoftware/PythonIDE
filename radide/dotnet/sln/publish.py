"""Publish profiles (``Properties/PublishProfiles/*.pubxml``) like Visual Studio 2022's Publish page
(Folder target): configuration, target framework, deployment mode (framework-dependent /
self-contained), target runtime, single file, ReadyToRun, trimming, target location.

``dotnet publish <project> -p:PublishProfile=<name>`` publishes with a profile (``publish_argv``).
"""
from __future__ import annotations

import re
from pathlib import Path

from ...foreign.msbuild import xml_escape, xml_unescape

RIDS = ["portable", "win-x64", "win-x86", "win-arm64", "linux-x64", "linux-arm64", "linux-musl-x64",
        "osx-x64", "osx-arm64"]
FIELDS = ["Configuration", "Platform", "PublishDir", "PublishProtocol", "_TargetId", "TargetFramework",
          "RuntimeIdentifier", "SelfContained", "PublishSingleFile", "PublishReadyToRun", "PublishTrimmed",
          "DeleteExistingFiles"]


def profiles_dir(project_folder: Path, language: str = "C#") -> Path:
    return Path(project_folder) / ("My Project" if language == "VB" else "Properties") / "PublishProfiles"


def list_profiles(project_folder: Path, language: str = "C#") -> list[Path]:
    d = profiles_dir(project_folder, language)
    return sorted(d.glob("*.pubxml")) if d.is_dir() else []


def read(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8-sig")
    out = {}
    for m in re.finditer(r"<(\w+)>(.*?)</\1>", text, re.S):
        if m.group(1) not in ("Project", "PropertyGroup"):
            out[m.group(1)] = xml_unescape(m.group(2).strip())
    return out


def default_profile(ms) -> dict:
    tf = (ms.target_frameworks or ["net8.0"])[0]
    return {"Configuration": "Release", "Platform": "Any CPU",
            "PublishDir": f"bin\\Release\\{tf}\\publish\\", "PublishProtocol": "FileSystem",
            "_TargetId": "Folder", "TargetFramework": tf}


def write(path: Path, values: dict) -> Path:
    """Write a .pubxml (Visual Studio's layout; empty values are left out)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = [k for k in FIELDS if values.get(k) not in (None, "")]
    keys += [k for k in values if k not in FIELDS and values.get(k) not in (None, "")]
    body = "".join(f"    <{k}>{xml_escape(values[k])}</{k}>\r\n" for k in keys)
    text = ('<?xml version="1.0" encoding="utf-8"?>\r\n<!--\r\nhttps://go.microsoft.com/fwlink/?LinkID=208121.\r\n'
            '-->\r\n<Project>\r\n  <PropertyGroup>\r\n' + body + "  </PropertyGroup>\r\n</Project>")
    path.write_bytes(text.encode("utf-8"))
    return path


def profile_values(mode_self_contained: bool, rid: str, single: bool, r2r: bool, trim: bool, tf: str,
                   configuration: str, publish_dir: str) -> dict:
    v = {"Configuration": configuration, "Platform": "Any CPU", "PublishDir": publish_dir,
         "PublishProtocol": "FileSystem", "_TargetId": "Folder", "TargetFramework": tf}
    if rid and rid != "portable":
        v["RuntimeIdentifier"] = rid
        v["SelfContained"] = "true" if mode_self_contained else "false"
        if single:
            v["PublishSingleFile"] = "true"
        if r2r:
            v["PublishReadyToRun"] = "true"
        if trim and mode_self_contained:
            v["PublishTrimmed"] = "true"
    return v


def publish_argv(dotnet: str, project_file: Path, profile: Path) -> list[str]:
    return [dotnet, "publish", str(project_file), f"-p:PublishProfile={Path(profile).stem}", "-nologo"]


def output_dir(project_folder: Path, values: dict) -> Path:
    d = (values.get("PublishDir") or "bin\\Release\\publish\\").replace("\\", "/")
    p = Path(d)
    return p if p.is_absolute() else Path(project_folder) / p
