"""nuget.config files: package sources, disabled sources, the global packages folder, settings.

NuGet reads a chain of configuration files (closest wins):

1. ``nuget.config`` / ``NuGet.Config`` in the solution folder and every parent folder,
2. the user file ``%APPDATA%\\NuGet\\NuGet.Config``,
3. machine-wide files ``%ProgramFiles(x86)%\\NuGet\\Config\\*.config`` (Visual Studio's offline
   packages source lives there).

``effective_sources(folder)`` merges them like NuGet (``<clear />`` stops inheriting farther files);
``ConfigFile`` reads and writes one file (the Options page edits the user file, or a solution
file when one exists). Writes keep the rest of the file intact.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

NUGET_ORG = "https://api.nuget.org/v3/index.json"
NAMES = ("nuget.config", "NuGet.Config", "NuGet.config")


@dataclass
class PackageSource:
    name: str
    url: str
    enabled: bool = True
    origin: str = ""             # the config file that defines it
    machine: bool = False
    protocol: str = ""

    @property
    def is_local(self) -> bool:
        u = self.url
        return not u.lower().startswith(("http://", "https://"))

    @property
    def is_nuget_org(self) -> bool:
        return "api.nuget.org" in self.url.lower() or "nuget.org/api" in self.url.lower()


def user_config_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "NuGet" / "NuGet.Config"


def machine_config_paths() -> list[Path]:
    base = os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles") or r"C:\Program Files (x86)"
    d = Path(base) / "NuGet" / "Config"
    try:
        return sorted(d.glob("*.config")) if d.is_dir() else []
    except OSError:
        return []


def solution_config_paths(folder) -> list[Path]:
    """nuget.config files from `folder` up to the drive root (closest first)."""
    out, seen = [], set()
    if not folder:
        return out
    p = Path(folder).resolve()
    for d in [p, *p.parents]:
        for n in NAMES:
            f = d / n
            try:
                if f.is_file():
                    key = os.path.normcase(str(f.resolve()))
                    if key not in seen:
                        seen.add(key)
                        out.append(f)
                    break
            except OSError:
                continue
    return out


def config_chain(folder=None) -> list[Path]:
    """Every config file NuGet reads for `folder`, closest first."""
    chain = solution_config_paths(folder)
    u = user_config_path()
    if u.is_file() and os.path.normcase(str(u)) not in {os.path.normcase(str(c)) for c in chain}:
        chain.append(u)
    chain += machine_config_paths()
    return chain


# ====================================================================== one file
@dataclass
class ConfigFile:
    path: Path
    root: ET.Element = field(default=None)       # type: ignore[assignment]

    @staticmethod
    def load(path, create: bool = False) -> "ConfigFile":
        p = Path(path)
        root = None
        if p.is_file():
            try:
                parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))   # comments are kept
                parser.feed(p.read_bytes())
                root = parser.close()
            except ET.ParseError:
                root = None
        if root is None:
            if not create and p.is_file():
                raise ValueError(f"{p} is not a valid nuget.config")
            root = ET.Element("configuration")
        return ConfigFile(p, root)

    # sections
    def section(self, name: str, create: bool = False) -> ET.Element | None:
        el = self.root.find(name)
        if el is None and create:
            el = ET.SubElement(self.root, name)
        return el

    def entries(self, name: str) -> list[tuple[str, str]]:
        sec = self.section(name)
        if sec is None:
            return []
        return [(e.get("key", ""), e.get("value", "")) for e in sec if e.tag == "add"]

    def has_clear(self, name: str) -> bool:
        sec = self.section(name)
        return sec is not None and any(e.tag == "clear" for e in sec)

    def get(self, section: str, key: str) -> str:
        for k, v in self.entries(section):
            if k.lower() == key.lower():
                return v
        return ""

    def set(self, section: str, key: str, value: str | None, extra: dict | None = None) -> None:
        sec = self.section(section, create=value is not None)
        if sec is None:
            return
        for e in list(sec):
            if e.tag == "add" and e.get("key", "").lower() == key.lower():
                if value is None:
                    sec.remove(e)
                else:
                    e.set("value", value)
                    for k, v in (extra or {}).items():
                        e.set(k, v)
                return
        if value is not None:
            e = ET.SubElement(sec, "add", {"key": key, "value": value, **(extra or {})})
            del e

    # sources
    def sources(self) -> list[PackageSource]:
        disabled = {k.lower() for k, v in self.entries("disabledPackageSources") if v.lower() == "true"}
        out = []
        sec = self.section("packageSources")
        for e in (sec if sec is not None else []):
            if e.tag == "add":
                k = e.get("key", "")
                out.append(PackageSource(k, self.expand(e.get("value", "")), k.lower() not in disabled, str(self.path),
                                         protocol=e.get("protocolVersion", "")))
        return out

    def expand(self, value: str) -> str:
        v = os.path.expandvars(value)
        if v and not v.lower().startswith(("http://", "https://")) and not os.path.isabs(v):
            v = str((self.path.parent / v).resolve())
        return v

    def add_source(self, name: str, url: str, enabled: bool = True) -> None:
        self.set("packageSources", name, url, {"protocolVersion": "3"} if url.lower().endswith("index.json") else None)
        self.enable_source(name, enabled)

    def remove_source(self, name: str) -> None:
        self.set("packageSources", name, None)
        self.set("disabledPackageSources", name, None)

    def enable_source(self, name: str, enabled: bool) -> None:
        if enabled:
            self.set("disabledPackageSources", name, None)
            sec = self.section("disabledPackageSources")
            if sec is not None and len(sec) == 0:
                self.root.remove(sec)
        else:
            self.set("disabledPackageSources", name, "true")

    def replace_sources(self, sources: list[PackageSource]) -> None:
        """Write the list in this order (Options > Package Sources > OK)."""
        sec = self.section("packageSources", create=True)
        keep_clear = any(e.tag == "clear" for e in sec)
        for e in list(sec):
            sec.remove(e)
        if keep_clear:
            ET.SubElement(sec, "clear")
        for s in sources:
            a = {"key": s.name, "value": s.url}
            if s.url.lower().endswith("index.json"):
                a["protocolVersion"] = "3"
            ET.SubElement(sec, "add", a)
        dis = self.section("disabledPackageSources")
        if dis is not None:
            self.root.remove(dis)
        off = [s for s in sources if not s.enabled]
        if off:
            dis = ET.SubElement(self.root, "disabledPackageSources")
            for s in off:
                ET.SubElement(dis, "add", {"key": s.name, "value": "true"})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.ElementTree(self.root)
        ET.indent(tree, "  ")
        data = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(self.root, encoding="utf-8") + b"\n"
        self.path.write_bytes(data)


# ====================================================================== merged view
def effective_sources(folder=None) -> list[PackageSource]:
    """Package sources NuGet would use for a solution in `folder` (enabled and disabled)."""
    chain = config_chain(folder)
    machine = {os.path.normcase(str(p)) for p in machine_config_paths()}
    merged: dict[str, PackageSource] = {}
    order: list[str] = []
    disabled: dict[str, bool] = {}
    for path in chain:                                    # closest first
        try:
            cf = ConfigFile.load(path)
        except (ValueError, OSError):
            continue
        for k, v in cf.entries("disabledPackageSources"):
            disabled.setdefault(k.lower(), v.lower() == "true")
        for s in cf.sources():
            key = s.name.lower()
            if key not in merged:
                s.machine = os.path.normcase(str(path)) in machine
                merged[key] = s
                order.append(key)
        if cf.has_clear("packageSources"):
            break
    if not merged:
        merged["nuget.org"] = PackageSource("nuget.org", NUGET_ORG, True, "(default)")
        order.append("nuget.org")
    out = []
    for key in order:
        s = merged[key]
        s.enabled = not disabled.get(key, False)
        out.append(s)
    return out


def enabled_sources(folder=None) -> list[PackageSource]:
    return [s for s in effective_sources(folder) if s.enabled]


def setting(key: str, folder=None, section: str = "config") -> str:
    for path in config_chain(folder):
        try:
            v = ConfigFile.load(path).get(section, key)
        except (ValueError, OSError):
            continue
        if v:
            return v
    return ""


def global_packages_folder(folder=None) -> Path:
    env = os.environ.get("NUGET_PACKAGES", "")
    if env:
        return Path(env)
    v = setting("globalPackagesFolder", folder)
    if v:
        return Path(os.path.expandvars(v))
    return Path.home() / ".nuget" / "packages"


def repository_path(solution_folder) -> Path:
    """packages.config projects: the solution 'packages' folder (repositoryPath setting wins)."""
    v = setting("repositoryPath", solution_folder)
    if v:
        p = Path(os.path.expandvars(v))
        return p if p.is_absolute() else (Path(solution_folder) / p).resolve()
    return Path(solution_folder) / "packages"


def editable_config(folder=None) -> Path:
    """The file the Options page writes: a solution nuget.config when there is one, else the user file."""
    sol = solution_config_paths(folder) if folder else []
    return sol[0] if sol else user_config_path()


__all__ = ["PackageSource", "ConfigFile", "effective_sources", "enabled_sources", "config_chain", "user_config_path",
           "machine_config_paths", "solution_config_paths", "global_packages_folder", "repository_path", "setting",
           "editable_config", "NUGET_ORG"]
