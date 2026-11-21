"""A Visual Studio solution as an editable document: classic ``.sln`` (Format Version 12.00) and the
XML ``.slnx`` (VS 2022 17.10+ / .NET SDK 9.0.200+), read AND written.

``SolutionDoc.load(path)`` parses either format into one model:

* ``projects``  - every ``Project(...)`` entry in file order, solution folders included
  (``SEntry.is_folder``); a folder's solution items are ``SEntry.items``; ``SEntry.parent`` is the
  guid of the folder that holds the entry (NestedProjects / ``<Folder Name="/A/B/">``);
  ``SEntry.deps`` are the guids of ProjectDependencies (``<BuildDependency>``).
* ``configs``   - solution configurations ``"Debug|Any CPU"`` in file order.
* ``mapping``   - ``{(project guid, "Debug|Any CPU"): ProjCfg(cfg, plat, build, deploy)}``; a missing
  key means "not mapped" (``.sln``: no ActiveCfg line; ``.slnx``: ``Project="?"``).

``text("sln" | "slnx")`` serializes; an unchanged ``.sln`` comes back byte-identical (unknown
sections are kept as written), and the ``.slnx`` writer emits the same canonical layout as
``dotnet sln migrate`` / Visual Studio (folders sorted, Files before Projects, parent folders
written, per-project BuildType / Platform / Build / Deploy rules only where they differ from the
defaults). ``save()`` writes the file when it changed; ``save_as(path)`` converts by extension.

No Qt here: radide/dotnet/sln/ops.py binds the document to an open VsSolution.
"""
from __future__ import annotations

import copy
import os
import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from ...foreign.msbuild import TextFile

FOLDER_GUID = "{2150E333-8FDC-42A3-9474-1A3956D46DE8}"
# project type guids by extension (what Visual Studio 2022 writes in a .sln)
TYPE_BY_EXT = {
    ".csproj": "{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}",
    ".vbproj": "{F184B08F-C81C-45F6-A57F-5ABD9991F28F}",
    ".fsproj": "{F2A71F9B-5D33-465A-A702-920D77279786}",
    ".vcxproj": "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}",
    ".vcxitems": "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}",
    ".shproj": "{D954291E-2A0B-460D-934E-DC6B0785DB48}",
    ".projitems": "{D954291E-2A0B-460D-934E-DC6B0785DB48}",
    ".sqlproj": "{00D1A9C2-B5F0-4AF3-8072-F6C62B433612}",
    ".wapproj": "{C7167F0D-BC9F-4E6E-AFE1-012C56B48DB5}",
    ".pyproj": "{888888A0-9F3D-457C-B088-3A5042F75D52}",
    ".njsproj": "{9092AA53-FB77-4645-B42D-1CCCA6BD08BD}",
    ".esproj": "{54A90642-561A-4BB1-A94E-469ADEE60C69}",
    ".dcproj": "{E53339B2-1760-4266-BCC7-CA923CBCF16C}",
    ".wixproj": "{930C7802-8A8C-48F9-8165-68863BCCD9DD}",
    ".vdproj": "{54435603-DBB4-11D2-8724-00A0C9A8B90C}",
    ".proj": "{13B669BE-BB05-4DDF-9536-439F39A36129}",
    ".msbuildproj": "{13B669BE-BB05-4DDF-9536-439F39A36129}",
}
SDK_TYPE_BY_EXT = {".csproj": "{9A19103F-16F7-4668-BE54-9A1E7A4F7556}",
                   ".vbproj": "{778DAE3C-4631-46EA-AA77-85C1314464D9}",
                   ".fsproj": "{6EC3EE1D-3C4E-46DD-8F32-0CC8E7565705}"}
NOT_BUILDABLE = {".shproj", ".projitems", ".vcxitems"}
DOTNET_EXTS = (".csproj", ".vbproj", ".fsproj")
PROJECT_FILE_EXTS = tuple(TYPE_BY_EXT)
DEFAULT_HEADER = ["", "Microsoft Visual Studio Solution File, Format Version 12.00", "# Visual Studio Version 17",
                  "VisualStudioVersion = 17.0.31903.59", "MinimumVisualStudioVersion = 10.0.40219.1"]
GLOBAL_ORDER = ("SolutionConfigurationPlatforms", "ProjectConfigurationPlatforms", "SolutionProperties",
                "NestedProjects", "ExtensibilityGlobals")

_PROJ_RX = re.compile(r'^\s*Project\("(\{[^}]+\})"\)\s*=\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"(\{[^}]+\})"\s*$')
_SEC_RX = re.compile(r"^\s*(ProjectSection|GlobalSection)\(([^)]*)\)\s*=\s*(\w+)\s*$")
_PCP_RX = re.compile(r"^(\{[^}]+\})\.(.+)\.(ActiveCfg|Build\.0|Deploy\.0)$")


def new_guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def slash(p: str) -> str:
    return str(p).replace("\\", "/")


def backslash(p: str) -> str:
    return str(p).replace("/", "\\")


@dataclass
class Section:
    """A ProjectSection / GlobalSection kept as written (key = value lines)."""
    name: str
    when: str
    entries: list = field(default_factory=list)       # [(key, value)]


@dataclass
class ProjCfg:
    cfg: str
    plat: str
    build: bool = True
    deploy: bool = False


@dataclass
class SEntry:
    name: str
    path: str                     # forward slashes, relative to the solution folder (folders: the name)
    type_guid: str
    guid: str
    parent: str = ""              # guid of the containing solution folder
    deps: list = field(default_factory=list)          # ProjectDependencies (guids)
    items: list = field(default_factory=list)         # solution items (folders only; forward slashes)
    sections: list = field(default_factory=list)      # other ProjectSections (.sln), in order
    attrs: dict = field(default_factory=dict)         # .slnx: extra attributes (Type, Id, DisplayName ...)
    extra: list = field(default_factory=list)         # .slnx: unknown child elements
    raw_rules: list = field(default_factory=list)     # .slnx: configuration rules as written
    rules_dirty: bool = True

    @property
    def is_folder(self) -> bool:
        return self.type_guid.upper() == FOLDER_GUID

    @property
    def ext(self) -> str:
        return "" if self.is_folder else Path(self.path).suffix.lower()

    @property
    def buildable(self) -> bool:
        return not self.is_folder and self.ext not in NOT_BUILDABLE


# ====================================================================== helpers
def default_project_platform(ext: str, sol_plat: str, project_platforms: list[str] | None = None) -> str:
    """The project platform a solution platform maps to when nothing else is said."""
    ext = (ext or "").lower()
    if ext in (".vcxproj",):
        if sol_plat in ("Any CPU", "AnyCPU", ""):
            return "x64"
        return "Win32" if sol_plat == "x86" else sol_plat
    if ext in DOTNET_EXTS:
        if project_platforms:
            norm = ["Any CPU" if p in ("AnyCPU", "Any CPU") else p for p in project_platforms]
            if sol_plat in norm:
                return sol_plat
            return "Any CPU" if "Any CPU" in norm else norm[0]
        return "Any CPU"
    return sol_plat


def type_guid_for(project_file: Path) -> str:
    ext = Path(project_file).suffix.lower()
    if ext in SDK_TYPE_BY_EXT:
        try:
            head = Path(project_file).read_text(encoding="utf-8-sig", errors="replace")[:4000]
        except OSError:
            head = ""
        if re.search(r"<Project\b[^>]*\bSdk\s*=", head) or re.search(r"<Sdk\s+Name=", head):
            return SDK_TYPE_BY_EXT[ext]
    return TYPE_BY_EXT.get(ext, TYPE_BY_EXT[".proj"])


def _project_guid_of(project_file: Path) -> str:
    try:
        text = Path(project_file).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    m = re.search(r"<ProjectGuid>\s*(\{?[0-9A-Fa-f-]{36}\}?)\s*</ProjectGuid>", text)
    if not m:
        return ""
    g = m.group(1).strip("{}").upper()
    return "{" + g + "}"


def project_platforms_of(project_file: Path) -> list[str]:
    try:
        text = Path(project_file).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    m = re.search(r"<Platforms>([^<]*)</Platforms>", text)
    if m:
        return [p.strip() for p in m.group(1).split(";") if p.strip()]
    found = re.findall(r"'\$\(Configuration\)\|\$\(Platform\)'\s*==\s*'[^|']+\|([^']+)'", text)
    found += re.findall(r'<ProjectConfiguration Include="[^|"]+\|([^"]+)"', text)
    return list(dict.fromkeys(found))


def _slnx_folder_guid(full: str) -> str:
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "slnx:" + full.strip("/"))).upper() + "}"


def _slnx_project_guid(path: str) -> str:
    rel = slash(path)
    rel = rel.lstrip("./") if not rel.startswith("..") else rel
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "slnx:" + rel.lower())).upper() + "}"


def _match(pattern: str | None, b: str, p: str) -> bool:
    if not pattern:
        return True
    pb, _, pp = pattern.partition("|")
    return (pb in ("*", "") or pb == b) and (not pp or pp == "*" or pp == p)


# ====================================================================== the document
class SolutionDoc:
    def __init__(self, path: Path | None = None, kind: str = "sln"):
        self.path = Path(path).resolve() if path else None
        self.kind = kind
        self.file: TextFile | None = None
        self.header: list[str] = list(DEFAULT_HEADER)
        self.projects: list[SEntry] = []
        self.globals: list[Section] = []
        self.trailer: list[str] = []
        self.configs: list[str] = ["Debug|Any CPU", "Release|Any CPU"]
        self.mapping: dict[tuple[str, str], ProjCfg] = {}
        self.pcp_order: list[str] = []
        self.nested_order: list[str] = []
        self.properties_xml: list = []           # .slnx <Properties> and unknown root elements
        self.slnx_build_types: list[str] | None = None
        self.slnx_platforms: list[str] | None = None
        self.newline = "\r\n"

    # ------------------------------------------------------------------ io
    @staticmethod
    def load(path) -> "SolutionDoc":
        path = Path(path).resolve()
        doc = SolutionDoc(path, "slnx" if path.suffix.lower() == ".slnx" else "sln")
        doc.file = TextFile.read(path)
        doc.newline = doc.file.newline
        if doc.kind == "slnx":
            doc._parse_slnx(doc.file.text)
        else:
            doc._parse_sln(doc.file.text)
        return doc

    @staticmethod
    def new(path, configs=None) -> "SolutionDoc":
        path = Path(path).resolve()
        doc = SolutionDoc(path, "slnx" if path.suffix.lower() == ".slnx" else "sln")
        if configs:
            doc.configs = list(configs)
        doc.globals = [Section("SolutionConfigurationPlatforms", "preSolution"),
                       Section("ProjectConfigurationPlatforms", "postSolution"),
                       Section("SolutionProperties", "preSolution", [("HideSolutionNode", "FALSE")]),
                       Section("NestedProjects", "preSolution"),
                       Section("ExtensibilityGlobals", "postSolution", [("SolutionGuid", new_guid())])]
        return doc

    @property
    def folder(self) -> Path:
        return self.path.parent if self.path else Path.cwd()

    def text(self, kind: str | None = None) -> str:
        kind = kind or self.kind
        return self._sln_text() if kind == "sln" else self._slnx_text()

    def save(self) -> bool:
        """Write when the serialized text differs from the file. True = written."""
        if self.path is None:
            raise ValueError("the solution has no path")
        text = self.text()
        if self.file is None:
            bom = b"\xef\xbb\xbf" if self.kind == "sln" else b""
            data = bom + text.encode("utf-8")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_bytes(data)
            self.file = TextFile(self.path, text, "utf-8", bom, self.newline, data)
            return True
        if text == self.file.text:
            return False
        self.file.text = text
        return self.file.save()

    def save_as(self, path) -> Path:
        """Write the solution to *path* in the format of its extension (.sln / .slnx)."""
        path = Path(path).resolve()
        kind = "slnx" if path.suffix.lower() == ".slnx" else "sln"
        old = self.folder
        if os.path.normcase(str(path.parent)) != os.path.normcase(str(old)):
            for e in self.projects:                       # paths stay relative to the solution
                if not e.is_folder:
                    e.path = slash(os.path.relpath(old / e.path, path.parent))
                e.items = [slash(os.path.relpath(old / i, path.parent)) for i in e.items]
        if kind == "slnx" and self.kind == "sln":
            for e in self.projects:
                e.rules_dirty = True
        if kind == "sln" and not self.globals:
            self.globals = SolutionDoc.new(path).globals
        self.kind, self.path, self.file = kind, path, None
        self.save()
        return path

    # ------------------------------------------------------------------ .sln parsing
    def _parse_sln(self, text: str) -> None:
        lines = text.splitlines()
        self.header, self.projects, self.globals, self.trailer = [], [], [], []
        self.configs, self.mapping, self.pcp_order, self.nested_order = [], {}, [], []
        i, n = 0, len(lines)
        while i < n and not _PROJ_RX.match(lines[i]) and lines[i].strip() != "Global":
            self.header.append(lines[i])
            i += 1
        nested: list[tuple[str, str]] = []
        while i < n:
            line = lines[i]
            m = _PROJ_RX.match(line)
            if m:
                e = SEntry(m.group(2), slash(m.group(3)), m.group(1).upper(), m.group(4).upper())
                self.projects.append(e)
                i += 1
                while i < n and lines[i].strip() != "EndProject":
                    sm = _SEC_RX.match(lines[i])
                    if sm:
                        sec = Section(sm.group(2), sm.group(3))
                        i += 1
                        while i < n and lines[i].strip() != "EndProjectSection":
                            k, _, v = lines[i].strip().partition("=")
                            if lines[i].strip():
                                sec.entries.append((k.strip(), v.strip()))
                            i += 1
                        if sec.name == "SolutionItems":
                            e.items = [slash(k) for k, _v in sec.entries]
                            sec.entries = []
                        elif sec.name == "ProjectDependencies":
                            e.deps = [k.upper() for k, _v in sec.entries]
                            sec.entries = []
                        e.sections.append(sec)
                    i += 1
                i += 1
                continue
            if line.strip() == "Global":
                i += 1
                while i < n:
                    line = lines[i]
                    if line.strip() == "EndGlobal":
                        i += 1
                        break
                    sm = _SEC_RX.match(line)
                    if sm:
                        sec = Section(sm.group(2), sm.group(3))
                        i += 1
                        while i < n and lines[i].strip() != "EndGlobalSection":
                            k, _, v = lines[i].strip().partition("=")
                            if lines[i].strip():
                                sec.entries.append((k.strip(), v.strip()))
                            i += 1
                        self._absorb_global(sec, nested)
                        self.globals.append(sec)
                    i += 1
                self.trailer = lines[i:]
                break
            self.header.append(line) if not self.projects else None
            i += 1
        by = {e.guid: e for e in self.projects}
        for child, parent in nested:
            if child in by:
                by[child].parent = parent
        if text.endswith(("\n", "\r")):
            self.trailer.append("")

    def _absorb_global(self, sec: Section, nested: list) -> None:
        if sec.name == "SolutionConfigurationPlatforms":
            for k, _v in sec.entries:
                if k not in self.configs:
                    self.configs.append(k)
            sec.entries = []
        elif sec.name == "ProjectConfigurationPlatforms":
            leftover = []
            for k, v in sec.entries:
                m = _PCP_RX.match(k)
                if not m:
                    leftover.append((k, v))
                    continue
                g, sc, what = m.group(1).upper(), m.group(2), m.group(3)
                if g not in self.pcp_order:
                    self.pcp_order.append(g)
                c, _, p = v.partition("|")
                pc = self.mapping.get((g, sc))
                if pc is None:
                    pc = self.mapping[(g, sc)] = ProjCfg(c, p, False, False)
                if what == "ActiveCfg":
                    pc.cfg, pc.plat = c, p
                elif what == "Build.0":
                    pc.build = True
                else:
                    pc.deploy = True
            sec.entries = leftover
        elif sec.name == "NestedProjects":
            for k, v in sec.entries:
                nested.append((k.upper(), v.upper()))
                self.nested_order.append(k.upper())
            sec.entries = []

    # ------------------------------------------------------------------ .sln writing
    def _sln_text(self) -> str:
        nl = self.newline
        out = list(self.header) if self.header else list(DEFAULT_HEADER)
        for e in self.projects:
            path = e.name if e.is_folder and not e.path else backslash(e.path)
            out.append(f'Project("{e.type_guid}") = "{e.name}", "{path}", "{e.guid}"')
            secs = list(e.sections)
            names = [s.name for s in secs]
            if e.items and "SolutionItems" not in names:
                secs.insert(0, Section("SolutionItems", "preProject"))
            if e.deps and "ProjectDependencies" not in names:
                secs.append(Section("ProjectDependencies", "postProject"))
            for s in secs:
                if s.name == "SolutionItems":
                    entries = [(backslash(i), backslash(i)) for i in e.items]
                elif s.name == "ProjectDependencies":
                    entries = [(d, d) for d in e.deps]
                else:
                    entries = s.entries
                if s.name in ("SolutionItems", "ProjectDependencies") and not entries:
                    continue
                out.append(f"\tProjectSection({s.name}) = {s.when}")
                out += [f"\t\t{k} = {v}" for k, v in entries]
                out.append("\tEndProjectSection")
            out.append("EndProject")
        out.append("Global")
        secs = list(self.globals)
        have = {s.name for s in secs}
        for name in ("SolutionConfigurationPlatforms", "ProjectConfigurationPlatforms", "NestedProjects"):
            if name not in have:
                at = len(secs)
                for j, s in enumerate(secs):
                    if s.name in GLOBAL_ORDER and GLOBAL_ORDER.index(s.name) > GLOBAL_ORDER.index(name):
                        at = j
                        break
                secs.insert(at, Section(name, "postSolution" if name == "ProjectConfigurationPlatforms"
                                        else "preSolution"))
        for s in secs:
            entries = self._global_entries(s)
            if entries is None:
                continue
            out.append(f"\tGlobalSection({s.name}) = {s.when}")
            out += [f"\t\t{k} = {v}" for k, v in entries]
            out.append("\tEndGlobalSection")
        out.append("EndGlobal")
        trailer = self.trailer if self.trailer else [""]
        return nl.join(out + trailer)

    def _global_entries(self, s: Section):
        if s.name == "SolutionConfigurationPlatforms":
            return [(c, c) for c in self.configs] if self.configs else None
        if s.name == "ProjectConfigurationPlatforms":
            rows = []
            order = [g for g in self.pcp_order if self.entry(g) is not None]
            order += [e.guid for e in self.projects if e.buildable and e.guid not in order]
            for g in order:
                keys = [sc for sc in self.configs if (g, sc) in self.mapping]
                for sc in keys:
                    pc = self.mapping[(g, sc)]
                    val = f"{pc.cfg}|{pc.plat}"
                    rows.append((f"{g}.{sc}.ActiveCfg", val))
                    if pc.build:
                        rows.append((f"{g}.{sc}.Build.0", val))
                    if pc.deploy:
                        rows.append((f"{g}.{sc}.Deploy.0", val))
            rows += s.entries
            return rows or None
        if s.name == "NestedProjects":
            nested = [e for e in self.projects if e.parent and self.entry(e.parent) is not None]
            pos = {g: i for i, g in enumerate(self.nested_order)}
            nested.sort(key=lambda e: pos.get(e.guid, len(pos)))
            rows = [(e.guid, e.parent) for e in nested]
            return rows or None
        return s.entries

    # ------------------------------------------------------------------ .slnx parsing
    def _parse_slnx(self, text: str) -> None:
        root = ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", text).encode("utf-8"))
        self.projects, self.mapping, self.properties_xml = [], {}, []
        builds = [b.get("Name", "") for c in root.findall("Configurations") for b in c.findall("BuildType")]
        plats = [p.get("Name", "") for c in root.findall("Configurations") for p in c.findall("Platform")]
        self.slnx_build_types = builds or None
        self.slnx_platforms = plats or None
        builds = builds or ["Debug", "Release"]
        plats = plats or ["Any CPU"]
        self.configs = [f"{b}|{p}" for b in builds for p in plats]
        folders: dict[str, SEntry] = {}

        def folder_for(full: str) -> SEntry:
            full = "/" + full.strip("/") + "/"
            if full in folders:
                return folders[full]
            parts = [x for x in full.strip("/").split("/") if x]
            parent = folder_for("/".join(parts[:-1])) if len(parts) > 1 else None
            e = SEntry(parts[-1], parts[-1], FOLDER_GUID, _slnx_folder_guid(full), parent.guid if parent else "")
            folders[full] = e
            self.projects.append(e)
            return e

        def project(el, parent_guid: str):
            path = slash(el.get("Path", ""))
            attrs = {k: v for k, v in el.attrib.items() if k != "Path"}
            guid = ("{" + attrs["Id"].strip("{}").upper() + "}") if attrs.get("Id") else _slnx_project_guid(path)
            ext = Path(path).suffix.lower()
            tguid = attrs.get("Type", "")
            if tguid and not tguid.startswith("{"):
                tguid = "{" + tguid.upper() + "}" if re.fullmatch(r"[0-9A-Fa-f-]{36}", tguid) else tguid
            e = SEntry(attrs.get("DisplayName") or Path(path).stem, path,
                       tguid or SDK_TYPE_BY_EXT.get(ext) or TYPE_BY_EXT.get(ext, TYPE_BY_EXT[".proj"]),
                       guid, parent_guid)
            e.attrs = attrs
            for ch in el:
                if ch.tag == "BuildDependency":
                    e.deps.append(ch.get("Project", ""))          # resolved to guids below
                elif ch.tag in ("BuildType", "Platform", "Build", "Deploy"):
                    e.raw_rules.append(ch)
                else:
                    e.extra.append(ch)
            e.rules_dirty = False
            self.projects.append(e)

        for ch in root:
            if ch.tag == "Configurations":
                continue
            if ch.tag == "Folder":
                f = folder_for(ch.get("Name", "/"))
                for sub in ch:
                    if sub.tag == "File":
                        f.items.append(slash(sub.get("Path", "")))
                    elif sub.tag == "Project":
                        project(sub, f.guid)
                    else:
                        f.extra.append(sub)
            elif ch.tag == "Project":
                project(ch, "")
            else:
                self.properties_xml.append(ch)
        by_path = {e.path.lower(): e.guid for e in self.projects if not e.is_folder}
        for e in self.projects:
            e.deps = [by_path.get(slash(d).lower(), _slnx_project_guid(d)) for d in e.deps]
            if e.is_folder or not e.buildable:
                continue
            for b in builds:
                for p in plats:
                    pc: ProjCfg | None = ProjCfg(b, default_project_platform(e.ext, p), True, False)
                    missing_cfg = missing_plat = False
                    for r in e.raw_rules:
                        if not _match(r.get("Solution"), b, p):
                            continue
                        val = r.get("Project")
                        if r.tag == "BuildType":
                            missing_cfg = val == "?"
                            if val and val != "?":
                                pc.cfg = val
                        elif r.tag == "Platform":
                            missing_plat = val == "?"
                            if val and val != "?":
                                pc.plat = val
                        elif r.tag == "Build":
                            pc.build = (val or "true").lower() != "false"
                        elif r.tag == "Deploy":
                            pc.deploy = (val or "true").lower() != "false"
                    if missing_cfg or missing_plat:
                        continue
                    self.mapping[(e.guid, f"{b}|{p}")] = pc

    # ------------------------------------------------------------------ .slnx writing
    def _build_types(self) -> list[str]:
        return list(dict.fromkeys(c.split("|")[0] for c in self.configs)) or ["Debug", "Release"]

    def _platforms(self) -> list[str]:
        return list(dict.fromkeys(c.split("|")[1] for c in self.configs if "|" in c)) or ["Any CPU"]

    def folder_full(self, e: SEntry) -> str:
        names = [n for n in self.folder_path(e)] + [e.name]
        return "/" + "/".join(names) + "/"

    def _slnx_axes(self) -> tuple[list[str], list[str]]:
        """Build types and platforms in the order Visual Studio writes them (sorted)."""
        return (sorted(self._build_types(), key=str.lower), sorted(self._platforms(), key=str.lower))

    def _slnx_rules(self, e: SEntry) -> list[str]:
        if not e.rules_dirty:
            return [_xml_el(r) for r in e.raw_rules]
        bts, pls = self._slnx_axes()
        actual: dict[str, dict] = {"BuildType": {}, "Platform": {}, "Build": {}, "Deploy": {}}
        default: dict[str, dict] = {"BuildType": {}, "Platform": {}, "Build": {}, "Deploy": {}}
        for b in bts:
            for p in pls:
                c = (b, p)
                dplat = default_project_platform(e.ext, p)
                default["BuildType"][c], default["Platform"][c] = b, _norm_plat(dplat)
                default["Build"][c], default["Deploy"][c] = "true", "false"
                pc = self.mapping.get((e.guid, f"{b}|{p}"))
                if pc is None:
                    actual["BuildType"][c], actual["Platform"][c] = "?", "?"
                    actual["Build"][c], actual["Deploy"][c] = "false", "false"
                    continue
                actual["BuildType"][c], actual["Platform"][c] = pc.cfg, _norm_plat(pc.plat)
                actual["Build"][c] = "true" if pc.build else "false"
                actual["Deploy"][c] = "true" if pc.deploy else "false"
        out = []
        for kind in ("BuildType", "Platform", "Build", "Deploy"):
            out += [_rule(kind, sol, val) for sol, val in _condense(actual[kind], default[kind], bts, pls)]
        return out

    def _slnx_project(self, e: SEntry, indent: str) -> list[str]:
        attrs = f' Path="{_x(e.path)}"' + "".join(f' {k}="{_x(v)}"' for k, v in e.attrs.items())
        by = {x.guid: x for x in self.projects}
        children = [f'<BuildDependency Project="{_x(by[d].path)}" />' for d in e.deps if d in by]
        if e.buildable:
            children += self._slnx_rules(e)
        children += [_xml_el(x) for x in e.extra]
        if not children:
            return [f"{indent}<Project{attrs} />"]
        out = [f"{indent}<Project{attrs}>"]
        for c in children:
            out += [f"{indent}  {ln}" for ln in c.splitlines()]
        return out + [f"{indent}</Project>"]

    def _slnx_text(self) -> str:
        nl = self.newline
        out = ["<Solution>"]
        bts, pls = self._slnx_axes()
        if bts != ["Debug", "Release"] or pls != ["Any CPU"]:
            out.append("  <Configurations>")
            if bts != ["Debug", "Release"]:
                out += [f'    <BuildType Name="{_x(b)}" />' for b in bts]
            if pls != ["Any CPU"]:
                out += [f'    <Platform Name="{_x(p)}" />' for p in pls]
            out.append("  </Configurations>")
        for el in self.properties_xml:
            out += ["  " + ln for ln in _xml_el(el).splitlines()]
        folders = sorted((e for e in self.projects if e.is_folder), key=lambda f: self.folder_full(f).lower())
        for f in folders:
            full = self.folder_full(f)
            kids = sorted((e for e in self.projects if not e.is_folder and e.parent == f.guid),
                          key=lambda e: e.path.lower())
            if not f.items and not kids and not f.extra:
                out.append(f'  <Folder Name="{_x(full)}" />')
                continue
            out.append(f'  <Folder Name="{_x(full)}">')
            out += [f'    <File Path="{_x(i)}" />' for i in f.items]
            for k in kids:
                out += self._slnx_project(k, "    ")
            for x in f.extra:
                out += ["    " + ln for ln in _xml_el(x).splitlines()]
            out.append("  </Folder>")
        for e in sorted((e for e in self.projects if not e.is_folder and not e.parent), key=lambda e: e.path.lower()):
            out += self._slnx_project(e, "  ")
        out.append("</Solution>")
        return nl.join(out) + nl

    # ------------------------------------------------------------------ queries
    def entry(self, guid: str) -> SEntry | None:
        g = str(guid).upper()
        return next((e for e in self.projects if e.guid == g), None)

    def find(self, name: str) -> SEntry | None:
        return next((e for e in self.projects if e.name.lower() == str(name).lower()), None)

    def by_file(self, path) -> SEntry | None:
        want = os.path.normcase(str(Path(path).resolve()))
        for e in self.projects:
            if not e.is_folder and os.path.normcase(str((self.folder / e.path).resolve())) == want:
                return e
        return None

    def real_projects(self) -> list[SEntry]:
        return [e for e in self.projects if not e.is_folder]

    def folders(self) -> list[SEntry]:
        return [e for e in self.projects if e.is_folder]

    def children(self, guid: str) -> list[SEntry]:
        g = (guid or "").upper()
        return [e for e in self.projects if e.parent == g]

    def folder_path(self, e: SEntry) -> list[str]:
        out, seen, p = [], set(), e.parent
        while p and p not in seen:
            seen.add(p)
            f = self.entry(p)
            if f is None:
                break
            out.insert(0, f.name)
            p = f.parent
        return out

    def folder_by_path(self, names: list[str]) -> SEntry | None:
        parent = ""
        cur = None
        for n in names:
            cur = next((e for e in self.projects if e.is_folder and e.parent == parent and
                        e.name.lower() == n.lower()), None)
            if cur is None:
                return None
            parent = cur.guid
        return cur

    def configurations(self) -> list[str]:
        return self._build_types()

    def platforms(self) -> list[str]:
        return self._platforms()

    def project_config(self, guid: str, sol_cfg: str) -> ProjCfg | None:
        return self.mapping.get((guid.upper(), sol_cfg))

    # ------------------------------------------------------------------ edits: projects
    def _mark(self, e: SEntry | None = None) -> None:
        for x in ([e] if e is not None else self.projects):
            x.rules_dirty = True

    def add_project(self, project_file, folder_guid: str = "", name: str = "") -> SEntry:
        """Add a project file (any type: .csproj ... .shproj, .sqlproj, .vcxproj ...) to the solution
        with a configuration mapping for every solution configuration. ValueError when present."""
        pf = Path(project_file).resolve()
        if self.by_file(pf) is not None:
            raise ValueError(f"{pf.name} is already in the solution")
        rel = slash(os.path.relpath(pf, self.folder))
        guid = _project_guid_of(pf) or new_guid()
        if self.kind == "slnx" and self.file is not None:
            guid = _slnx_project_guid(rel)
        if self.entry(guid) is not None:
            guid = new_guid()
        e = SEntry(name or pf.stem, rel, type_guid_for(pf), guid, (folder_guid or "").upper())
        if self.kind == "slnx" and name and name != pf.stem:
            e.attrs["DisplayName"] = name
        self.projects.append(e)
        if e.buildable:
            plats = project_platforms_of(pf)
            for sc in self.configs:
                c, _, p = sc.partition("|")
                pcfgs = _project_configs_of(pf)
                cfg = c if not pcfgs or c in pcfgs else ("Release" if "Release" in pcfgs and c != "Debug"
                                                         else pcfgs[0])
                self.mapping[(guid, sc)] = ProjCfg(cfg, default_project_platform(e.ext, p, plats), True, False)
        self._mark(e)
        return e

    def remove(self, guid: str) -> list[SEntry]:
        """Remove a project or a solution folder (with everything in it). Returns what was removed."""
        e = self.entry(guid)
        if e is None:
            return []
        gone = [e]
        stack = [e.guid]
        while stack:
            g = stack.pop()
            for c in self.children(g):
                gone.append(c)
                stack.append(c.guid)
        ids = {x.guid for x in gone}
        self.projects = [x for x in self.projects if x.guid not in ids]
        self.mapping = {k: v for k, v in self.mapping.items() if k[0] not in ids}
        for x in self.projects:
            if any(d in ids for d in x.deps):
                x.deps = [d for d in x.deps if d not in ids]
                self._mark(x)
        return gone

    def rename_project(self, guid: str, name: str) -> None:
        e = self.entry(guid)
        if e is None:
            raise KeyError(guid)
        e.name = name
        if self.kind == "slnx" and not e.is_folder:
            if name != Path(e.path).stem:
                e.attrs["DisplayName"] = name
            else:
                e.attrs.pop("DisplayName", None)

    # ------------------------------------------------------------------ edits: folders, items, nesting
    def add_folder(self, name: str, parent_guid: str = "") -> SEntry:
        name = name.strip()
        if not name or re.search(r'[/\\:*?"<>|]', name):
            raise ValueError(f"'{name}' is not a valid solution folder name")
        parent_guid = (parent_guid or "").upper()
        if any(e.is_folder and e.parent == parent_guid and e.name.lower() == name.lower() for e in self.projects):
            raise ValueError(f"a solution folder named '{name}' already exists here")
        g = new_guid()
        e = SEntry(name, name, FOLDER_GUID, g, parent_guid)
        self.projects.append(e)
        return e

    def ensure_folder_path(self, names: list[str]) -> str:
        parent = ""
        for n in names:
            f = next((e for e in self.projects if e.is_folder and e.parent == parent and e.name.lower() == n.lower()),
                     None)
            parent = (f or self.add_folder(n, parent)).guid
        return parent

    def rename_folder(self, guid: str, name: str) -> None:
        e = self.entry(guid)
        if e is None or not e.is_folder:
            raise KeyError(guid)
        name = name.strip()
        if not name or re.search(r'[/\\:*?"<>|]', name):
            raise ValueError(f"'{name}' is not a valid solution folder name")
        if any(x is not e and x.is_folder and x.parent == e.parent and x.name.lower() == name.lower()
               for x in self.projects):
            raise ValueError(f"a solution folder named '{name}' already exists here")
        e.name = e.path = name

    def move(self, guid: str, folder_guid: str = "") -> None:
        """Move a project or folder into a solution folder ("" = the solution root)."""
        e = self.entry(guid)
        folder_guid = (folder_guid or "").upper()
        if e is None:
            raise KeyError(guid)
        if folder_guid:
            f = self.entry(folder_guid)
            if f is None or not f.is_folder:
                raise ValueError("the target is not a solution folder")
            p = folder_guid
            while p:
                if p == e.guid:
                    raise ValueError("a folder cannot be moved into itself")
                p = (self.entry(p) or SEntry("", "", "", "")).parent
            if e.is_folder and any(x is not e and x.is_folder and x.parent == folder_guid and
                                   x.name.lower() == e.name.lower() for x in self.projects):
                raise ValueError(f"'{f.name}' already has a folder named '{e.name}'")
        e.parent = folder_guid

    def add_item(self, folder_guid: str, file) -> str:
        f = self.entry(folder_guid)
        if f is None or not f.is_folder:
            raise ValueError("solution items belong to a solution folder")
        rel = slash(os.path.relpath(Path(file).resolve(), self.folder))
        if rel.lower() not in (i.lower() for i in f.items):
            f.items.append(rel)
        return rel

    def remove_item(self, folder_guid: str, rel: str) -> bool:
        f = self.entry(folder_guid)
        if f is None:
            return False
        n = len(f.items)
        f.items = [i for i in f.items if i.lower() != slash(rel).lower()]
        return len(f.items) != n

    # ------------------------------------------------------------------ edits: dependencies
    def set_dependencies(self, guid: str, deps: list[str]) -> None:
        e = self.entry(guid)
        if e is None:
            raise KeyError(guid)
        clean = []
        for d in deps:
            d = d.upper()
            if d != e.guid and self.entry(d) is not None and d not in clean:
                clean.append(d)
        for d in clean:
            if guid.upper() in self._dep_closure(d, {}):
                raise ValueError(f"'{self.entry(d).name}' already depends on '{e.name}' (circular dependency)")
        e.deps = clean
        self._mark(e)

    def _dep_closure(self, guid: str, extra: dict) -> set[str]:
        seen, stack = set(), [guid.upper()]
        while stack:
            g = stack.pop()
            e = self.entry(g)
            for d in (e.deps if e else []) + list(extra.get(g, [])):
                if d not in seen:
                    seen.add(d)
                    stack.append(d)
        return seen

    def build_order(self, references: dict | None = None) -> list[SEntry]:
        """Buildable projects in build order: ProjectDependencies plus *references*
        ({guid: [guids it references]}, from the project files). Cycles are broken in file order."""
        references = references or {}
        order: list[SEntry] = []
        state: dict[str, int] = {}

        def visit(e: SEntry):
            if state.get(e.guid):
                return
            state[e.guid] = 1
            for d in list(e.deps) + list(references.get(e.guid, [])):
                x = self.entry(d)
                if x is not None and not x.is_folder:
                    visit(x)
            state[e.guid] = 2
            if e.buildable:
                order.append(e)
        for e in self.projects:
            if not e.is_folder:
                visit(e)
        return order

    # ------------------------------------------------------------------ edits: configurations
    def set_project_config(self, guid: str, sol_cfg: str, cfg: str | None = None, plat: str | None = None,
                           build: bool | None = None, deploy: bool | None = None) -> None:
        g = guid.upper()
        e = self.entry(g)
        pc = self.mapping.get((g, sol_cfg))
        if pc is None:
            c, _, p = sol_cfg.partition("|")
            pc = self.mapping[(g, sol_cfg)] = ProjCfg(c, default_project_platform(e.ext if e else "", p), True)
        if cfg is not None:
            pc.cfg = cfg
        if plat is not None:
            pc.plat = plat
        if build is not None:
            pc.build = build
        if deploy is not None:
            pc.deploy = deploy
        self._mark(e)

    def add_configuration(self, name: str, copy_from: str = "", platforms: list[str] | None = None) -> list[str]:
        """New solution configuration *name* for every platform (copying the mapping of *copy_from*;
        projects get a project configuration of the same name when it was copied as-is)."""
        name = name.strip()
        if not name or "|" in name:
            raise ValueError(f"'{name}' is not a valid configuration name")
        if name.lower() in (c.lower() for c in self.configurations()):
            raise ValueError(f"the configuration '{name}' already exists")
        added = []
        for p in platforms or self.platforms():
            sc = f"{name}|{p}"
            self.configs.append(sc)
            added.append(sc)
            src = f"{copy_from}|{p}" if copy_from else ""
            for e in self.projects:
                if not e.buildable:
                    continue
                base = self.mapping.get((e.guid, src)) if src else None
                if base is not None:
                    self.mapping[(e.guid, sc)] = ProjCfg(base.cfg, base.plat, base.build, base.deploy)
                elif not src:
                    self.mapping[(e.guid, sc)] = ProjCfg(name, default_project_platform(e.ext, p), True)
        self._mark()
        return added

    def add_platform(self, name: str, copy_from: str = "") -> list[str]:
        name = name.strip()
        if not name or "|" in name:
            raise ValueError(f"'{name}' is not a valid platform name")
        if name.lower() in (p.lower() for p in self.platforms()):
            raise ValueError(f"the platform '{name}' already exists")
        added = []
        for b in self.configurations():
            sc = f"{b}|{name}"
            self.configs.append(sc)
            added.append(sc)
            src = f"{b}|{copy_from}" if copy_from else ""
            for e in self.projects:
                if not e.buildable:
                    continue
                base = self.mapping.get((e.guid, src)) if src else None
                plat = default_project_platform(e.ext, name)
                if base is not None:
                    self.mapping[(e.guid, sc)] = ProjCfg(base.cfg, base.plat if e.ext in DOTNET_EXTS else plat,
                                                         base.build, base.deploy)
                else:
                    self.mapping[(e.guid, sc)] = ProjCfg(b, plat, True)
        self._mark()
        return added

    def remove_configuration(self, name: str) -> None:
        if len(self.configurations()) <= 1:
            raise ValueError("a solution needs at least one configuration")
        drop = [c for c in self.configs if c.split("|")[0].lower() == name.lower()]
        self.configs = [c for c in self.configs if c not in drop]
        self.mapping = {k: v for k, v in self.mapping.items() if k[1] not in drop}
        self._mark()

    def remove_platform(self, name: str) -> None:
        if len(self.platforms()) <= 1:
            raise ValueError("a solution needs at least one platform")
        drop = [c for c in self.configs if c.partition("|")[2].lower() == name.lower()]
        self.configs = [c for c in self.configs if c not in drop]
        self.mapping = {k: v for k, v in self.mapping.items() if k[1] not in drop}
        self._mark()

    def rename_configuration(self, old: str, new: str) -> None:
        new = new.strip()
        if not new or "|" in new or new.lower() in (c.lower() for c in self.configurations() if c != old):
            raise ValueError(f"'{new}' is not a valid new configuration name")
        ren = {c: f"{new}|{c.partition('|')[2]}" for c in self.configs if c.split("|")[0] == old}
        self.configs = [ren.get(c, c) for c in self.configs]
        self.mapping = {(g, ren.get(sc, sc)): v for (g, sc), v in self.mapping.items()}
        self._mark()

    def rename_platform(self, old: str, new: str) -> None:
        new = new.strip()
        if not new or "|" in new or new.lower() in (p.lower() for p in self.platforms() if p != old):
            raise ValueError(f"'{new}' is not a valid new platform name")
        ren = {c: f"{c.split('|')[0]}|{new}" for c in self.configs if c.partition("|")[2] == old}
        self.configs = [ren.get(c, c) for c in self.configs]
        self.mapping = {(g, ren.get(sc, sc)): v for (g, sc), v in self.mapping.items()}
        self._mark()

    # ------------------------------------------------------------------ merging
    def import_from(self, other: "SolutionDoc", guids: list[str] | None = None, under: str = "") -> list[SEntry]:
        """Add projects of another solution (all, or *guids*), recreating their solution folders
        (below the folder *under*). Projects already in this solution are skipped."""
        chosen = [e for e in other.real_projects() if guids is None or e.guid in {g.upper() for g in guids}]
        added = []
        renamed: dict[str, str] = {}
        for e in chosen:
            pf = (other.folder / e.path).resolve()
            if self.by_file(pf) is not None:
                renamed[e.guid] = self.by_file(pf).guid
                continue
            names = other.folder_path(e)
            parent = under.upper()
            if names:
                parent = self._ensure_under(names, parent)
            new = SEntry(e.name, slash(os.path.relpath(pf, self.folder)), e.type_guid, e.guid, parent)
            if self.entry(new.guid) is not None:
                new.guid = new_guid()
            renamed[e.guid] = new.guid
            self.projects.append(new)
            if new.buildable:
                for sc in self.configs:
                    src = other.mapping.get((e.guid, sc))
                    c, _, p = sc.partition("|")
                    if src is None:
                        fallback = next((v for (g, s), v in other.mapping.items() if g == e.guid
                                         and s.split("|")[0] == c), None)
                        src = ProjCfg(c, fallback.plat if fallback else default_project_platform(new.ext, p),
                                      True)
                    self.mapping[(new.guid, sc)] = ProjCfg(src.cfg, src.plat, src.build, src.deploy)
            self._mark(new)
            added.append((new, e))
        for new, old in added:
            new.deps = [renamed[d] for d in old.deps if d in renamed]
        for f in other.folders():                         # their solution items come along
            if f.items:
                fp = self._ensure_under(other.folder_path(f) + [f.name], under.upper())
                for i in f.items:
                    self.add_item(fp, other.folder / i)
        return [n for n, _o in added]

    def _ensure_under(self, names: list[str], parent: str) -> str:
        for n in names:
            f = next((x for x in self.projects if x.is_folder and x.parent == parent and
                      x.name.lower() == n.lower()), None)
            parent = (f or self.add_folder(n, parent)).guid
        return parent


def _project_configs_of(project_file: Path) -> list[str]:
    try:
        text = Path(project_file).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    m = re.search(r"<Configurations>([^<]*)</Configurations>", text)
    if m:
        return [c.strip() for c in m.group(1).split(";") if c.strip()]
    found = re.findall(r"'\$\(Configuration\)\|\$\(Platform\)'\s*==\s*'([^|']+)\|", text)
    found += re.findall(r'<ProjectConfiguration Include="([^|"]+)\|', text)
    return list(dict.fromkeys(found))


def _condense(actual: dict, default: dict, bts: list[str], pls: list[str]) -> list[tuple[str | None, str]]:
    """Per-configuration values -> the fewest rules, like Visual Studio: one rule without Solution when
    every configuration has the same value, "Debug|*" for a whole build type, "*|x64" for a whole platform,
    single "Debug|x64" rules for the rest. Configurations with the default value need no rule."""
    allc = [(b, p) for b in bts for p in pls]
    odd = {c for c in allc if actual[c] != default[c]}
    if not odd:
        return []
    if len({actual[c] for c in allc}) == 1:
        return [(None, actual[allc[0]])]
    covered: set = set()
    rows, cols, single = [], [], []
    for b in bts:
        row = [(b, p) for p in pls]
        if len({actual[c] for c in row}) == 1 and odd & set(row):
            rows.append((f"{b}|*", actual[row[0]]))
            covered |= set(row)
    for p in pls:
        col = [(b, p) for b in bts]
        if len({actual[c] for c in col}) == 1 and (odd & set(col)) - covered and not covered & set(col):
            cols.append((f"*|{p}", actual[col[0]]))
            covered |= set(col)
    for c in allc:
        if c in odd and c not in covered:
            single.append((f"{c[0]}|{c[1]}", actual[c]))
    return cols + rows + single


def _rule(kind: str, solution: str | None, value: str) -> str:
    sol = f' Solution="{_x(solution)}"' if solution else ""
    if kind == "Deploy":
        return f"<Deploy{sol} />" if value == "true" else f'<Deploy{sol} Project="false" />'
    return f'<{kind}{sol} Project="{_x(value)}" />'


def _norm_plat(p: str) -> str:
    return "Any CPU" if p in ("AnyCPU", "Any CPU") else p


def _x(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _xml_el(el) -> str:
    el = copy.deepcopy(el)
    ET.indent(el, "  ")
    el.tail = None
    return ET.tostring(el, encoding="unicode").strip()


def new_solution(path, projects: list | None = None, folders_from_dirs: bool = False) -> SolutionDoc:
    """A new solution file (not written) with *projects* added; *folders_from_dirs* nests each project
    in solution folders named after its parent directories (relative to the solution)."""
    doc = SolutionDoc.new(path)
    for pf in projects or []:
        parent = ""
        if folders_from_dirs:
            rel = Path(os.path.relpath(Path(pf).resolve(), doc.folder)).parent.parent
            names = [p for p in rel.parts if p not in ("", ".", "..")]
            if names:
                parent = doc.ensure_folder_path(names)
        doc.add_project(pf, parent)
    return doc


def find_project_files(folder, limit: int = 400) -> list[Path]:
    """Project files under *folder* (bin/obj/.git/node_modules skipped)."""
    skip = {"bin", "obj", ".git", ".vs", "node_modules", "packages", ".radide", "_build", "TestResults"}
    out: list[Path] = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
        for f in files:
            if Path(f).suffix.lower() in PROJECT_FILE_EXTS and Path(f).suffix.lower() not in (".projitems",
                                                                                               ".vcxitems"):
                out.append(Path(root) / f)
                if len(out) >= limit:
                    return sorted(out)
    return sorted(out)
