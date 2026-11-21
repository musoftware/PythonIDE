"""Launch profiles (``Properties/launchSettings.json``, VB: ``My Project/launchSettings.json``) like
Visual Studio 2022's Debug > General > "Open debug launch profiles UI".

A profile is ``{"commandName": "Project" | "Executable" | "IIS Express", "commandLineArgs": "...",
"environmentVariables": {...}, "workingDirectory": "...", "executablePath": "...", "launchBrowser":
true, "launchUrl": "...", "applicationUrl": "https://localhost:5001;http://localhost:5000"}``.
``resolve()`` turns one into what to start (program, arguments, environment, working directory,
browser URL); radide/dotnet/sln/run.py applies it to F5 / Ctrl+F5.
"""
from __future__ import annotations

import json
import os
import re
import shlex
from pathlib import Path

COMMANDS = ["Project", "Executable", "IIS Express"]


def settings_path(project_folder: Path, language: str = "C#") -> Path:
    folder = "My Project" if language == "VB" else "Properties"
    return Path(project_folder) / folder / "launchSettings.json"


def _strip_comments(text: str) -> str:
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        else:
            out.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def load(project_folder: Path, language: str = "C#") -> dict:
    p = settings_path(project_folder, language)
    if not p.is_file():
        return {"profiles": {}}
    try:
        d = json.loads(_strip_comments(p.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError):
        return {"profiles": {}}
    if not isinstance(d, dict):
        return {"profiles": {}}
    d.setdefault("profiles", {})
    return d


def save(project_folder: Path, data: dict, language: str = "C#") -> Path:
    p = settings_path(project_folder, language)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def profile_names(data: dict) -> list[str]:
    return list((data.get("profiles") or {}).keys())


def default_profile(data: dict) -> str:
    names = profile_names(data)
    prof = data.get("profiles") or {}
    return next((n for n in names if (prof[n] or {}).get("commandName") == "Project"), names[0] if names else "")


def ensure_default(project_folder: Path, project_name: str, language: str = "C#") -> dict:
    """The launch settings, with a "<project>" Project profile created when there is none (VS does
    this the first time the launch profiles UI is opened)."""
    data = load(project_folder, language)
    if not data["profiles"]:
        data["profiles"][project_name] = {"commandName": "Project"}
        save(project_folder, data, language)
    return data


def expand(value: str, macros: dict) -> str:
    """%VAR% (environment) and $(Name) (project macros: TargetDir, ProjectDir, TargetPath ...)."""
    value = re.sub(r"%([^%]+)%", lambda m: os.environ.get(m.group(1), m.group(0)), value or "")
    return re.sub(r"\$\((\w+)\)", lambda m: str(macros.get(m.group(1), m.group(0))), value)


def split_args(args: str) -> list[str]:
    if not args:
        return []
    try:
        return shlex.split(args, posix=False) if os.name == "nt" else shlex.split(args)
    except ValueError:
        return args.split()


def unquote(a: str) -> str:
    return a[1:-1] if len(a) >= 2 and a[0] == a[-1] == '"' else a


def resolve(profile: dict, macros: dict) -> dict:
    """{'command', 'executable', 'args': [...], 'env': {...}, 'cwd': str|'' , 'browser': url|''}"""
    profile = profile or {}
    cmd = profile.get("commandName") or "Project"
    env = {str(k): expand(str(v), macros) for k, v in (profile.get("environmentVariables") or {}).items()}
    app_url = str(profile.get("applicationUrl") or "")
    if app_url and cmd == "Project":
        env.setdefault("ASPNETCORE_URLS", app_url)
        env.setdefault("DOTNET_URLS", app_url)
    args = [unquote(a) for a in split_args(expand(str(profile.get("commandLineArgs") or ""), macros))]
    cwd = expand(str(profile.get("workingDirectory") or ""), macros)
    if cwd and not os.path.isabs(cwd) and macros.get("ProjectDir"):
        cwd = str(Path(macros["ProjectDir"]) / cwd)
    browser = ""
    if profile.get("launchBrowser"):
        base = (app_url.split(";")[0] if app_url else "http://localhost:5000").rstrip("/")
        lu = str(profile.get("launchUrl") or "")
        browser = lu if re.match(r"https?://", lu) else (base + ("/" + lu.lstrip("/") if lu else ""))
    exe = expand(str(profile.get("executablePath") or ""), macros) if cmd == "Executable" else ""
    return {"command": cmd, "executable": exe, "args": args, "env": env, "cwd": cwd, "browser": browser}
