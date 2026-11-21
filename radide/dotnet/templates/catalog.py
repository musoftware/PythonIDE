"""Project templates for Visual Studio 2022's "Create a new project" (no Qt here).

Installed ``dotnet new`` templates (SDK + workload packs + user-installed packages) are read from the
.NET template engine's own cache (``%USERPROFILE%\\.templateengine\\dotnetcli\\<sdk>\\templatecache.json``,
refreshed by running ``dotnet new list`` once when it is missing) - it has the full names, the
languages, the classifications (tags), the parameters with their choices / defaults / display names
and the CLI option names. When it cannot be read, ``dotnet new list`` is parsed as text.

RAD IDE adds the templates that ``dotnet new`` does not have (written by radide/dotnet/templates/writers.py):
Shared Project (C# / VB), Class Library / Console App / Windows Forms App (.NET Framework, old-style
project files), WPF App (.NET Framework), Windows Service (.NET Framework), Class Library (.NET Standard)
and Blank Solution.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
ENV = {"DOTNET_NOLOGO": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1"}
SKIP_PARAMS = {"name", "language", "type", "TargetFrameworkOverride", "skipRestore", "langVersion",
               "UserSecretsId", "kestrelHttpPort", "kestrelHttpsPort", "iisHttpPort", "iisHttpsPort"}
LANGS = ("C#", "VB", "F#")


@dataclass
class TemplateParam:
    name: str
    display: str
    kind: str                       # choice | bool | text | string | integer
    default: str = ""
    choices: list[tuple[str, str]] = field(default_factory=list)      # (value, display)
    description: str = ""
    option: str = ""                # CLI option: --framework, --use-program-main ...

    @property
    def label(self) -> str:
        return (self.display or self.name).replace("_", "")


@dataclass
class TemplateInfo:
    key: str                        # unique: "cli:Microsoft.Common.Console|C#" / "rad:shared-cs"
    name: str
    short_name: str
    language: str
    description: str = ""
    classifications: list[str] = field(default_factory=list)
    params: list[TemplateParam] = field(default_factory=list)
    source: str = "cli"             # cli | rad
    author: str = ""
    kind: str = "project"           # project | solution

    @property
    def platforms(self) -> list[str]:
        return platforms_for(self.classifications)

    @property
    def project_types(self) -> list[str]:
        return project_types_for(self.classifications, self.name)

    @property
    def framework_param(self) -> TemplateParam | None:
        return next((p for p in self.params if p.name.lower() == "framework"), None)

    def tags(self) -> list[str]:
        return [self.language] + self.platforms + self.project_types if self.language else \
            self.platforms + self.project_types

    def matches(self, text: str) -> bool:
        t = text.strip().lower()
        if not t:
            return True
        hay = " ".join([self.name, self.short_name, self.description, *self.tags(), *self.classifications]).lower()
        return all(w in hay for w in t.split())


_PLATFORM_WORDS = ["Android", "iOS", "macOS", "Mac Catalyst", "Windows", "Linux", "Tizen", "Cloud"]


def platforms_for(classes: list[str]) -> list[str]:
    cl = {c.lower() for c in classes}
    out = [p for p in _PLATFORM_WORDS if p.lower() in cl]
    if {"winforms", "wpf", "winui", "windows service", ".net framework"} & cl:
        out = ["Windows"]
    elif not out and ({"common", "web", "test", "library", "console", "worker"} & cl):
        out = ["Windows", "Linux", "macOS"]
        if "web" in cl:
            out.append("Cloud")
    return out


def project_types_for(classes: list[str], name: str = "") -> list[str]:
    cl = {c.lower() for c in classes}
    out = []
    for words, t in ((("console",), "Console"), (("library",), "Library"),
                     (("winforms", "wpf", "winui", "desktop"), "Desktop"),
                     (("web", "asp.net", "blazor", "mvc", "razor pages", "web api", "api"), "Web"),
                     (("test",), "Test"), (("mobile", "maui"), "Mobile"),
                     (("worker", "service", "windows service"), "Service"), (("shared",), "Shared"),
                     (("solution",), "Other")):
        if cl & set(words) and t not in out:
            out.append(t)
    if "library" in name.lower() and "Library" not in out:
        out.append("Library")
    return out


# ============================================================================ dotnet
def find_dotnet() -> str:
    try:
        from ...foreign.msbuild import find_dotnet as fd
        return fd() or ""
    except Exception:  # noqa: BLE001
        import shutil
        return shutil.which("dotnet") or ""


def run_dotnet(args: list[str], cwd=None, timeout: int = 300) -> tuple[int, str]:
    dn = find_dotnet()
    if not dn:
        return 127, "the .NET SDK (dotnet) was not found"
    try:
        r = subprocess.run([dn, *args], capture_output=True, cwd=str(cwd) if cwd else None, timeout=timeout,
                           creationflags=NO_WINDOW, env={**os.environ, **ENV})
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)
    return r.returncode, (r.stdout + r.stderr).decode("utf-8", errors="replace")


def sdk_version() -> str:
    code, out = run_dotnet(["--version"], timeout=60)
    return out.strip().splitlines()[-1].strip() if code == 0 and out.strip() else ""


def cache_file(version: str = "") -> Path | None:
    base = Path(os.environ.get("USERPROFILE") or Path.home()) / ".templateengine" / "dotnetcli"
    if version and (base / version / "templatecache.json").is_file():
        return base / version / "templatecache.json"
    hits = sorted(base.glob("*/templatecache.json"), key=lambda p: p.stat().st_mtime, reverse=True) \
        if base.is_dir() else []
    return hits[0] if hits else None


_CACHE: dict = {}


def installed_templates(refresh: bool = False) -> list[TemplateInfo]:
    """dotnet new project templates (one per template group and language)."""
    if _CACHE.get("cli") is not None and not refresh:
        return _CACHE["cli"]
    ver = sdk_version()
    cf = cache_file(ver)
    if refresh or cf is None or (ver and cf.parent.name != ver):
        run_dotnet(["new", "list", "--type", "project"], timeout=180)       # (re)builds the engine cache
        cf = cache_file(ver)
    out: list[TemplateInfo] = []
    if cf is not None:
        try:
            out = parse_cache(json.loads(cf.read_text(encoding="utf-8-sig")))
        except (OSError, ValueError, KeyError, TypeError):
            out = []
    if not out:
        code, text = run_dotnet(["new", "list", "--type", "project"], timeout=180)
        out = parse_list_output(text) if code == 0 else []
    _CACHE["cli"] = out
    return out


def parse_cache(data: dict) -> list[TemplateInfo]:
    groups: dict[tuple[str, str], list[dict]] = {}
    for t in data.get("TemplateInfo", []):
        tags = t.get("TagsCollection") or {}
        if tags.get("type") != "project":
            continue
        lang = tags.get("language", "")
        gid = t.get("GroupIdentity") or t.get("Identity")
        groups.setdefault((gid, lang), []).append(t)
    out = []
    for (gid, lang), members in groups.items():
        members.sort(key=lambda m: m.get("Precedence", 0), reverse=True)
        best = members[0]
        try:
            host = json.loads(best.get("HostData") or "{}").get("symbolInfo", {})
        except ValueError:
            host = {}
        params = []
        for p in best.get("Parameters", []):
            n = p.get("Name", "")
            hinfo = host.get(n, {})
            if n in SKIP_PARAMS or p.get("IsName") or str(hinfo.get("isHidden", "")).lower() == "true":
                continue
            kind = (p.get("DataType") or "string").lower()
            choices = [(k, (v or {}).get("DisplayName") or (v or {}).get("Description") or k)
                       for k, v in (p.get("Choices") or {}).items()]
            if n.lower() == "framework":            # every framework of the group (8.0 and 9.0 template packs)
                seen = {c[0] for c in choices}
                for m in members[1:]:
                    for q in m.get("Parameters", []):
                        if q.get("Name", "").lower() == "framework":
                            for k, v in (q.get("Choices") or {}).items():
                                if k not in seen:
                                    seen.add(k)
                                    choices.append((k, (v or {}).get("DisplayName") or k))
                choices.sort(key=lambda c: _fw_sort(c[0]), reverse=True)
            long = hinfo.get("longName") or n
            params.append(TemplateParam(n, p.get("DisplayName") or "", kind, str(p.get("DefaultValue") or ""),
                                        choices, p.get("Description") or p.get("Documentation") or "", "--" + long))
        params.sort(key=lambda q: (q.name.lower() != "framework", q.kind != "choice"))
        out.append(TemplateInfo(f"cli:{gid}|{lang}", best.get("Name", gid), (best.get("ShortNameList") or [""])[0],
                                lang, best.get("Description") or "", list(best.get("Classifications") or []),
                                params, "cli", best.get("Author") or ""))
    out.sort(key=lambda t: (_popularity(t), t.name.lower(), LANGS.index(t.language) if t.language in LANGS else 9))
    return out


def _fw_sort(fw: str):
    m = re.match(r"net(\d+)\.(\d+)", fw)
    if m:
        return (2, int(m.group(1)), int(m.group(2)))
    m = re.match(r"netstandard(\d+)\.(\d+)", fw)
    if m:
        return (1, int(m.group(1)), int(m.group(2)))
    return (0, 0, 0)


_POPULAR = ["console", "classlib", "winforms", "wpf", "webapi", "webapp", "mvc", "blazor", "xunit", "mstest",
            "nunit", "worker", "maui"]


def _popularity(t: TemplateInfo) -> int:
    return _POPULAR.index(t.short_name) if t.short_name in _POPULAR else len(_POPULAR)


def parse_list_output(text: str) -> list[TemplateInfo]:
    """Fallback: the table printed by ``dotnet new list`` (names may be cut with '...')."""
    lines = text.splitlines()
    dash = next((i for i, ln in enumerate(lines) if re.match(r"^-{4,}(\s+-{4,})+\s*$", ln)), None)
    if dash is None:
        return []
    spans = [(m.start(), m.end()) for m in re.finditer(r"-+", lines[dash])]
    out = []
    for ln in lines[dash + 1:]:
        if not ln.strip():
            continue
        cols = [ln[a:(spans[i + 1][0] if i + 1 < len(spans) else len(ln))].strip() for i, (a, _b) in enumerate(spans)]
        if len(cols) < 4:
            continue
        name, shorts, langs, tags = cols[:4]
        for lang in [x.strip("[] ") for x in langs.split(",") if x.strip()]:
            short = shorts.split(",")[0]
            out.append(TemplateInfo(f"cli:{short}|{lang}", name, short, lang, "", tags.split("/"), [], "cli"))
    return out


# ============================================================================ RAD IDE templates
NETFX_VERSIONS = [("v4.8.1", ".NET Framework 4.8.1"), ("v4.8", ".NET Framework 4.8"), ("v4.7.2", ".NET Framework 4.7.2"),
                  ("v4.7.1", ".NET Framework 4.7.1"), ("v4.7", ".NET Framework 4.7"), ("v4.6.2", ".NET Framework 4.6.2"),
                  ("v4.6.1", ".NET Framework 4.6.1"), ("v4.5.2", ".NET Framework 4.5.2"), ("v4.0", ".NET Framework 4")]


def installed_netfx() -> list[tuple[str, str]]:
    """.NET Framework targeting packs on this machine (Reference Assemblies), newest first;
    all versions when none is found (the project can still be written)."""
    base = Path(os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)") / \
        "Reference Assemblies" / "Microsoft" / "Framework" / ".NETFramework"
    have = [v for v in NETFX_VERSIONS if (base / v[0]).is_dir()]
    return have or list(NETFX_VERSIONS)


def _netfx_param(default: str = "v4.8") -> TemplateParam:
    ch = installed_netfx()
    d = default if any(c[0] == default for c in ch) else ch[0][0]
    return TemplateParam("Framework", "Framework", "choice", d, ch, "The .NET Framework version", "")


def rad_templates() -> list[TemplateInfo]:
    fx = _netfx_param
    std = TemplateParam("Framework", "Framework", "choice", "netstandard2.0",
                        [("netstandard2.0", ".NET Standard 2.0"), ("netstandard2.1", ".NET Standard 2.1")],
                        "The target framework", "")
    out = [
        TemplateInfo("rad:shared-cs", "Shared Project", "shproj", "C#",
                     "A project for sharing files between multiple projects (the files are compiled into each "
                     "project that references it)", ["Shared", "Windows", "Linux", "macOS", "Android", "iOS"], [], "rad"),
        TemplateInfo("rad:shared-vb", "Shared Project", "shproj", "VB",
                     "A project for sharing files between multiple projects (the files are compiled into each "
                     "project that references it)", ["Shared", "Windows", "Linux", "macOS", "Android", "iOS"], [], "rad"),
        TemplateInfo("rad:netstd-cs", "Class Library (.NET Standard)", "netstdlib", "C#",
                     "A project for creating a class library that targets .NET Standard (usable from .NET and "
                     ".NET Framework)", ["Common", "Library"], [std], "rad"),
        TemplateInfo("rad:netstd-vb", "Class Library (.NET Standard)", "netstdlib", "VB",
                     "A project for creating a class library that targets .NET Standard", ["Common", "Library"],
                     [std], "rad"),
    ]
    for lang in ("C#", "VB"):
        sfx = "cs" if lang == "C#" else "vb"
        out += [
            TemplateInfo(f"rad:fxlib-{sfx}", "Class Library (.NET Framework)", "fxlib", lang,
                         "A project for creating a C# class library (.dll) for .NET Framework".replace(
                             "C#", "Visual Basic" if lang == "VB" else "C#"),
                         [".NET Framework", "Windows", "Library"], [fx()], "rad"),
            TemplateInfo(f"rad:fxconsole-{sfx}", "Console App (.NET Framework)", "fxconsole", lang,
                         "A project for creating a command-line application on .NET Framework",
                         [".NET Framework", "Windows", "Console"], [fx()], "rad"),
            TemplateInfo(f"rad:fxwinforms-{sfx}", "Windows Forms App (.NET Framework)", "fxwinforms", lang,
                         "A project for creating an application with a Windows Forms user interface on .NET Framework",
                         [".NET Framework", "Windows", "Desktop", "WinForms"], [fx()], "rad"),
        ]
    out += [
        TemplateInfo("rad:fxwpf-cs", "WPF App (.NET Framework)", "fxwpf", "C#",
                     "Windows Presentation Foundation client application on .NET Framework",
                     [".NET Framework", "Windows", "Desktop", "WPF"], [fx()], "rad"),
        TemplateInfo("rad:fxservice-cs", "Windows Service (.NET Framework)", "fxservice", "C#",
                     "A project for creating a Windows Service on .NET Framework",
                     [".NET Framework", "Windows", "Service", "Windows Service"], [fx()], "rad"),
        TemplateInfo("rad:blank-sln", "Blank Solution", "sln", "",
                     "Create an empty solution containing no projects", ["Solution"], [], "rad", kind="solution"),
    ]
    return out


def all_templates(refresh: bool = False, include_cli: bool = True) -> list[TemplateInfo]:
    cli = installed_templates(refresh) if include_cli else []
    return cli + rad_templates()


def filter_templates(templates: list[TemplateInfo], text: str = "", language: str = "", platform: str = "",
                     project_type: str = "") -> list[TemplateInfo]:
    out = []
    for t in templates:
        if language and t.language and t.language != language:
            continue
        if language and not t.language and t.kind != "solution":
            continue
        if platform and platform not in t.platforms:
            continue
        if project_type and project_type not in t.project_types:
            continue
        if not t.matches(text):
            continue
        out.append(t)
    return out


def filter_values(templates: list[TemplateInfo]) -> tuple[list[str], list[str], list[str]]:
    langs = [lang for lang in LANGS if any(t.language == lang for t in templates)]
    plats = sorted({p for t in templates for p in t.platforms}, key=str.lower)
    types = sorted({p for t in templates for p in t.project_types}, key=str.lower)
    return langs, plats, types


def find(templates: list[TemplateInfo], short_or_key: str, language: str = "C#") -> TemplateInfo | None:
    for t in templates:
        if t.key == short_or_key:
            return t
    return next((t for t in templates if t.short_name == short_or_key and (t.language == language or not t.language)),
                None)


__all__ = ["TemplateInfo", "TemplateParam", "installed_templates", "rad_templates", "all_templates",
           "filter_templates", "filter_values", "find", "parse_cache", "parse_list_output", "installed_netfx",
           "run_dotnet", "find_dotnet"]
