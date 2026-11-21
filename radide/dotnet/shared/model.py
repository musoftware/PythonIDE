"""Shared Projects (.shproj + .projitems) like Visual Studio 2022 - no Qt here.

A Shared Project is not built on its own: its items (``<Name>.projitems``) are imported into every
consuming C# / VB project with ``<Import Project="..\\Shared\\Shared.projitems" Label="Shared" />`` and
compiled there (with the consumer's target framework and DefineConstants).

Files written exactly like Visual Studio:

* ``<Name>.shproj``    - ProjectGuid, the CodeSharing imports, ``<Import Project="<Name>.projitems" Label="Shared" />``
* ``<Name>.projitems`` - ``HasSharedItems``, ``SharedGUID``, ``Import_RootNamespace`` and the items
  (``<Compile Include="$(MSBuildThisFileDirectory)Folder\\Class1.cs" />``).
* the .sln gets ``Project("{D954291E-2A0B-460D-934E-DC6B0785DB48}") = "Name", "Name\\Name.shproj", "{GUID}"``
  (no configuration lines: Visual Studio writes none for shared projects); a .slnx gets ``<Project Path=... />``.

Edits are text edits (byte-preserving everywhere else) through ``radide.foreign.msbuild``.
"""
from __future__ import annotations

import os
import re
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from ...foreign import msbuild as MB
from ...foreign.msbuild import MSBuildProject, TextFile, ms_path, norm_rel, xml_escape, xml_unescape

SHPROJ_TYPE_GUID = "{D954291E-2A0B-460D-934E-DC6B0785DB48}"
THIS_DIR = "$(MSBuildThisFileDirectory)"
LANG_TARGETS = {"C#": "Microsoft.CodeSharing.CSharp.targets", "VB": "Microsoft.CodeSharing.VisualBasic.targets"}
CODE_EXT = {"C#": ".cs", "VB": ".vb"}
CONSUMER_EXT = {"C#": ".csproj", "VB": ".vbproj"}

SHPROJ_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="14.0" DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup Label="Globals">
    <ProjectGuid>{guid}</ProjectGuid>
    <MinimumVisualStudioVersion>14.0</MinimumVisualStudioVersion>
  </PropertyGroup>
  <Import Project="$(MSBuildExtensionsPath)\\$(MSBuildToolsVersion)\\Microsoft.Common.props" Condition="Exists('$(MSBuildExtensionsPath)\\$(MSBuildToolsVersion)\\Microsoft.Common.props')" />
  <Import Project="$(MSBuildExtensionsPath32)\\Microsoft\\VisualStudio\\v$(VisualStudioVersion)\\CodeSharing\\Microsoft.CodeSharing.Common.Default.props" />
  <Import Project="$(MSBuildExtensionsPath32)\\Microsoft\\VisualStudio\\v$(VisualStudioVersion)\\CodeSharing\\Microsoft.CodeSharing.Common.props" />
  <PropertyGroup />
  <Import Project="{name}.projitems" Label="Shared" />
  <Import Project="$(MSBuildExtensionsPath32)\\Microsoft\\VisualStudio\\v$(VisualStudioVersion)\\CodeSharing\\{targets}" />
</Project>
"""

PROJITEMS_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<Project xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup>
    <MSBuildAllProjects Condition="'$(MSBuildVersion)' == '' Or '$(MSBuildVersion)' &lt; '16.0'">$(MSBuildAllProjects);$(MSBuildThisFileFullPath)</MSBuildAllProjects>
    <HasSharedItems>true</HasSharedItems>
    <SharedGUID>{shared_guid}</SharedGUID>
  </PropertyGroup>
  <PropertyGroup Label="Configuration">
    <Import_RootNamespace>{ns}</Import_RootNamespace>
  </PropertyGroup>
</Project>
"""

ITEM_TEMPLATES = {
    "C#": [("Class", ".cs"), ("Interface", ".cs"), ("Enum", ".cs"), ("Code File", ".cs"), ("Text File", ".txt"),
           ("JSON File", ".json"), ("XML File", ".xml")],
    "VB": [("Class", ".vb"), ("Module", ".vb"), ("Interface", ".vb"), ("Enum", ".vb"), ("Code File", ".vb"),
           ("Text File", ".txt"), ("XML File", ".xml")],
}


def _new_guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def _safe_ns(name: str) -> str:
    ns = re.sub(r"[^A-Za-z0-9_.]", "_", name)
    return ("_" + ns) if ns[:1].isdigit() else ns


def _norm(p) -> str:
    return os.path.normcase(str(Path(p).resolve()))


@dataclass
class SharedItem:
    kind: str                       # Compile, None, EmbeddedResource, Content, Page, Folder ...
    include: str                    # as written ("$(MSBuildThisFileDirectory)Sub\\Class1.cs")
    metadata: dict = field(default_factory=dict)

    @property
    def rel(self) -> str:
        """Path relative to the shared project folder (forward slashes, no trailing slash)."""
        inc = xml_unescape(self.include)
        if inc.startswith(THIS_DIR):
            inc = inc[len(THIS_DIR):]
        return norm_rel(inc).rstrip("/")


class SharedProject:
    """A Visual Studio Shared Project (.shproj + .projitems)."""

    def __init__(self, path: Path):
        path = Path(path).resolve()
        if path.suffix.lower() == ".projitems":
            cand = path.with_suffix(".shproj")
            if not cand.is_file():
                hits = sorted(path.parent.glob("*.shproj"))
                cand = hits[0] if hits else cand
            self.path = cand
            self._items_path = path
        else:
            self.path = path
            self._items_path = None
        self.reload()

    # ------------------------------------------------------------------ io
    @staticmethod
    def load(path) -> "SharedProject":
        return SharedProject(Path(path))

    def reload(self) -> None:
        self.shfile = TextFile.read(self.path) if self.path.is_file() else None
        sh = self.shfile.text if self.shfile else ""
        m = re.search(r'<Import\s+Project="([^"]+\.projitems)"\s+Label="Shared"\s*/>', sh, re.I) or \
            re.search(r'<Import\s+Label="Shared"\s+Project="([^"]+\.projitems)"\s*/>', sh, re.I)
        if self._items_path is None or m:
            rel = xml_unescape(m.group(1)) if m else f"{self.path.stem}.projitems"
            rel = rel.replace(THIS_DIR, "")
            self._items_path = (self.path.parent / norm_rel(rel)).resolve()
        self.items_project = MSBuildProject.load(self._items_path)
        self._parse()

    def _parse(self) -> None:
        txt = self.items_project.text
        self.items: list[SharedItem] = []
        for it in self.items_project.items:
            if it.op != "Include":
                continue
            md = {k: v for k, v in it.metadata.items()}
            self.items.append(SharedItem(it.kind, it.include, md))
        sh = self.shfile.text if self.shfile else ""
        m = re.search(r"<ProjectGuid>\s*([^<]+?)\s*</ProjectGuid>", sh)
        self.guid = (m.group(1) if m else "").upper()
        if self.guid and not self.guid.startswith("{"):
            self.guid = "{" + self.guid + "}"
        m = re.search(r"<SharedGUID>\s*([^<]+?)\s*</SharedGUID>", txt)
        self.shared_guid = (m.group(1) if m else "").strip("{}").lower()
        if not self.guid and self.shared_guid:
            self.guid = "{" + self.shared_guid.upper() + "}"
        m = re.search(r"<Import_RootNamespace>\s*([^<]*?)\s*</Import_RootNamespace>", txt)
        self.root_namespace = m.group(1) if m else _safe_ns(self.name)
        if "VisualBasic.targets" in sh:
            self.language = "VB"
        elif "CSharp.targets" in sh:
            self.language = "C#"
        else:
            vb = sum(1 for i in self.items if i.rel.lower().endswith(".vb"))
            cs = sum(1 for i in self.items if i.rel.lower().endswith(".cs"))
            self.language = "VB" if vb > cs else "C#"

    def save(self) -> bool:
        return self.items_project.save()

    # ------------------------------------------------------------------ properties
    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def folder(self) -> Path:
        return self.path.parent

    @property
    def projitems_path(self) -> Path:
        return self._items_path

    @property
    def items_folder(self) -> Path:
        """Where $(MSBuildThisFileDirectory) points (the .projitems folder)."""
        return self._items_path.parent

    @property
    def code_ext(self) -> str:
        return CODE_EXT.get(self.language, ".cs")

    def files(self) -> list[str]:
        """Relative paths of the shared files (forward slashes), in project-file order."""
        return [i.rel for i in self.items if i.kind != "Folder" and "*" not in i.rel]

    def code_files(self) -> list[str]:
        return [r for r in self.files() if r.lower().endswith(self.code_ext)]

    def abs_path(self, rel: str) -> Path:
        return (self.items_folder / rel).resolve()

    def contains(self, path) -> str | None:
        """The relative path of *path* when it is one of the shared files."""
        n = _norm(path)
        for r in self.files():
            if _norm(self.abs_path(r)) == n:
                return r
        return None

    def folders(self) -> list[str]:
        """Folders to show (explicit Folder items + every parent folder of a file), sorted."""
        out = set()
        for i in self.items:
            parts = i.rel.split("/")
            upto = parts if i.kind == "Folder" else parts[:-1]
            for k in range(1, len(upto) + 1):
                out.add("/".join(upto[:k]))
        return sorted(out, key=str.lower)

    # ------------------------------------------------------------------ item edits
    def _include(self, rel: str, folder: bool = False) -> str:
        rel = norm_rel(rel).strip("/")
        return THIS_DIR + ms_path(rel) + ("\\" if folder else "")

    def _kind_for(self, rel: str) -> str:
        low = rel.lower()
        if low.endswith(self.code_ext):
            return "Compile"
        if low.endswith(".resx"):
            return "EmbeddedResource"
        if low.endswith(".xaml"):
            return "Page"
        return "None"

    def add_file(self, rel: str, kind: str = "", metadata: dict | None = None) -> bool:
        """Register an existing file (already in the shared folder) in the .projitems."""
        kind = kind or self._kind_for(rel)
        ok = self.items_project.add_item(kind, self._include(rel), metadata or None)
        self._drop_folder_item_for(rel)
        self.items_project.save()
        self._parse()
        return ok

    def _drop_folder_item_for(self, rel: str) -> None:
        parent = norm_rel(rel).rsplit("/", 1)[0] if "/" in norm_rel(rel) else ""
        if not parent:
            return
        for i in list(self.items):
            if i.kind == "Folder" and i.rel.lower() == parent.lower():
                self.items_project.remove_item("Folder", i.include)

    def add_new_item(self, template: str, rel_dir: str, name: str) -> list[str]:
        """Add > New Item inside the shared project. Returns the created relative paths."""
        files = new_item_files(self, template, rel_dir, name)
        if not files:
            raise ValueError(f"no template '{template}' for a {self.language} shared project")
        for rel, _t in files:
            if self.abs_path(rel).exists():
                raise ValueError(f"{rel} already exists")
        for rel, text in files:
            p = self.abs_path(rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            data = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
            if p.suffix.lower() in (".cs", ".vb") and text:
                data = b"\xef\xbb\xbf" + data
            p.write_bytes(data)
            self.items_project.add_item(self._kind_for(rel), self._include(rel))
            self._drop_folder_item_for(rel)
        self.items_project.save()
        self._parse()
        return [r for r, _t in files]

    def add_existing_item(self, path, rel_dir: str = "") -> str:
        """Add > Existing Item: copy the file into the shared folder (when outside) and register it."""
        path = Path(path).resolve()
        try:
            rel = path.relative_to(self.items_folder).as_posix()
        except ValueError:
            target = self.items_folder / norm_rel(rel_dir).strip("/") / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            rel = target.relative_to(self.items_folder).as_posix()
        self.add_file(rel)
        return rel

    def new_folder(self, rel: str) -> str:
        rel = norm_rel(rel).strip("/")
        (self.items_folder / rel).mkdir(parents=True, exist_ok=True)
        self.items_project.add_item("Folder", self._include(rel, folder=True))
        self.items_project.save()
        self._parse()
        return rel

    def _item_for(self, rel: str) -> SharedItem | None:
        low = norm_rel(rel).strip("/").lower()
        return next((i for i in self.items if i.rel.lower() == low), None)

    def exclude(self, rel: str) -> bool:
        """Exclude From Project (the file stays on disk)."""
        it = self._item_for(rel)
        if it is None:
            return False
        ok = self.items_project.remove_item(it.kind, it.include)
        self.items_project.save()
        self._parse()
        return ok

    def delete(self, rel: str) -> bool:
        """Delete: exclude and remove the file (or an empty folder) from disk."""
        it = self._item_for(rel)
        p = self.abs_path(rel)
        ok = False
        if it is not None and it.kind == "Folder" or (it is None and p.is_dir()):
            for i in list(self.items):          # everything under the folder
                if i.rel.lower().startswith(norm_rel(rel).strip("/").lower() + "/") or i is it:
                    self.items_project.remove_item(i.kind, i.include)
            self.items_project.save()
            shutil.rmtree(p, ignore_errors=True)
            ok = True
        elif it is not None:
            ok = self.exclude(rel)
            try:
                p.unlink()
            except OSError:
                pass
        self._parse()
        return ok

    def rename_item(self, rel: str, new_name: str) -> str:
        """Rename a shared file (on disk and in the .projitems). Returns the new relative path."""
        it = self._item_for(rel)
        if it is None:
            raise ValueError(f"{rel} is not in {self.name}")
        new_rel = (norm_rel(rel).rsplit("/", 1)[0] + "/" + new_name) if "/" in norm_rel(rel) else new_name
        src, dst = self.abs_path(rel), self.abs_path(new_rel)
        if dst.exists():
            raise ValueError(f"{new_rel} already exists")
        if src.exists():
            src.rename(dst)
        self.items_project.remove_item(it.kind, it.include)
        self.items_project.add_item(it.kind, self._include(new_rel, it.kind == "Folder"), it.metadata or None)
        self.items_project.save()
        self._parse()
        return new_rel

    # ------------------------------------------------------------------ project edits
    def set_root_namespace(self, ns: str) -> bool:
        txt = self.items_project.text
        new = re.sub(r"(<Import_RootNamespace>)[^<]*(</Import_RootNamespace>)",
                     lambda m: m.group(1) + xml_escape(ns) + m.group(2), txt, count=1)
        if new == txt:
            return False
        self.items_project.file.text = new
        self.items_project.parse()
        self.items_project.save()
        self._parse()
        return True

    def rename(self, new_name: str, consumers: list[Path] | None = None, sln_model=None) -> None:
        """Rename the shared project: <New>.shproj + <New>.projitems (the folder is kept, like VS),
        the shproj's Import, every consumer's Import and the solution entry."""
        new_name = new_name.strip()
        if not re.fullmatch(r"[^\\/:*?\"<>|]+", new_name or ""):
            raise ValueError(f"'{new_name}' is not a valid project name")
        old_items = self.projitems_path
        old_sh = self.path
        new_sh = old_sh.with_name(new_name + ".shproj")
        new_items = old_items.with_name(new_name + ".projitems")
        if (new_sh.exists() and _norm(new_sh) != _norm(old_sh)) or \
                (new_items.exists() and _norm(new_items) != _norm(old_items)):
            raise ValueError(f"{new_name} already exists in {self.folder}")
        users = [Path(c) for c in (consumers or [])]
        for c in users:
            remove_shared_reference(c, self)
        if self.shfile is not None:
            self.shfile.text = self.shfile.text.replace(f'"{old_items.name}"', f'"{new_items.name}"')
            self.shfile.save()
        old_items.rename(new_items)
        old_sh.rename(new_sh)
        self.path, self._items_path = new_sh, new_items
        self.reload()
        for c in users:
            add_shared_reference(c, self)
        if sln_model is not None:
            _rename_in_solution(sln_model, old_sh, self)


# ====================================================================== new item templates
def new_item_files(shared: SharedProject, template: str, rel_dir: str, name: str) -> list[tuple[str, str]]:
    rel_dir = norm_rel(rel_dir).strip("/")
    pre = f"{rel_dir}/" if rel_dir else ""
    ext = dict(ITEM_TEMPLATES.get(shared.language, [])).get(template, "")
    if not ext:
        return []
    base = re.sub(r"\.(cs|vb|txt|json|xml)$", "", name.strip(), flags=re.I)
    if not base:
        raise ValueError("enter a name")
    ns = shared.root_namespace
    for part in [p for p in rel_dir.split("/") if p]:
        ns += "." + re.sub(r"\W", "_", part)
    if shared.language == "C#":
        kw = {"Class": "internal class", "Interface": "internal interface", "Enum": "internal enum"}.get(template)
        if kw:
            body = f"{kw} {base}\n{{\n}}\n"
            inner = "".join(("    " + ln if ln.strip() else ln) for ln in body.splitlines(True))
            text = ("using System;\nusing System.Collections.Generic;\nusing System.Text;\n\n"
                    f"namespace {ns}\n{{\n{inner}}}\n")
            return [(f"{pre}{base}.cs", text)]
        if template == "Code File":
            return [(f"{pre}{base}.cs", "")]
    else:
        vb = {"Class": f"Public Class {base}\n\nEnd Class\n", "Module": f"Public Module {base}\n\nEnd Module\n",
              "Interface": f"Public Interface {base}\n\nEnd Interface\n", "Enum": f"Public Enum {base}\n    None\nEnd Enum\n",
              "Code File": ""}
        if template in vb:
            text = vb[template]
            if text and rel_dir:          # VB: the root namespace is the consumer's; folders add a Namespace
                sub = ".".join(re.sub(r"\W", "_", p) for p in rel_dir.split("/") if p)
                text = f"Namespace {sub}\n" + "".join("    " + ln if ln.strip() else ln
                                                      for ln in text.splitlines(True)) + "End Namespace\n"
            return [(f"{pre}{base}.vb", text)]
    if template == "JSON File":
        return [(f"{pre}{base}.json", "{\n}\n")]
    if template == "XML File":
        return [(f"{pre}{base}.xml", '<?xml version="1.0" encoding="utf-8" ?>\n')]
    return [(f"{pre}{base}{ext}", "")]


# ====================================================================== create
def create_shared_project(parent: Path, name: str, language: str = "C#", root_namespace: str = "",
                          own_folder: bool = True, guid: str = "") -> SharedProject:
    """Create <parent>/<name>/<name>.shproj + .projitems (empty, like VS's "Shared Project" template)."""
    if language not in LANG_TARGETS:
        raise ValueError(f"Shared projects are C# or VB (not {language})")
    name = name.strip()
    if not re.fullmatch(r"[^\\/:*?\"<>|]+", name or ""):
        raise ValueError(f"'{name}' is not a valid project name")
    folder = Path(parent) / name if own_folder else Path(parent)
    sh = folder / f"{name}.shproj"
    if sh.exists() or (folder / f"{name}.projitems").exists():
        raise ValueError(f"{sh} already exists")
    folder.mkdir(parents=True, exist_ok=True)
    guid = (guid or _new_guid()).upper()
    sh_text = SHPROJ_TEMPLATE.format(guid=guid, name=xml_escape(name), targets=LANG_TARGETS[language])
    items_text = PROJITEMS_TEMPLATE.format(shared_guid=guid.strip("{}").lower(),
                                           ns=xml_escape(root_namespace or _safe_ns(name)))
    for p, t in ((sh, sh_text), (folder / f"{name}.projitems", items_text)):
        p.write_bytes(b"\xef\xbb\xbf" + t.replace("\n", "\r\n").encode("utf-8"))
    return SharedProject(sh)


# ====================================================================== consumers
_IMPORT_RX = re.compile(r'<Import\b(?=[^>]*\bLabel\s*=\s*"Shared")(?=[^>]*\bProject\s*=\s*"([^"]+)")[^>]*/>', re.I)


def _resolve_import(project_file: Path, spec: str) -> Path:
    spec = xml_unescape(spec).replace("$(MSBuildProjectDirectory)", "").replace(THIS_DIR, "")
    spec = norm_rel(spec) if not spec.startswith("..") else spec.replace("\\", "/")
    p = Path(spec)
    return (p if p.is_absolute() else (Path(project_file).parent / spec)).resolve()


def shared_imports(project_file) -> list[Path]:
    """The .projitems a C#/VB project imports (<Import ... Label="Shared" />), absolute paths."""
    try:
        text = TextFile.read(project_file).text
    except OSError:
        return []
    return [_resolve_import(Path(project_file), m.group(1)) for m in _IMPORT_RX.finditer(text)]


def references_shared(project_file, shared: SharedProject) -> bool:
    n = _norm(shared.projitems_path)
    return any(_norm(p) == n for p in shared_imports(project_file))


def project_language(project_file) -> str:
    return MB.LANG_BY_EXT.get(Path(project_file).suffix.lower(), "")


def can_reference(project_file, shared: SharedProject) -> tuple[bool, str]:
    """(ok, why not): only projects of the same language can use a shared project (VS lists only those)."""
    lang = project_language(project_file)
    if lang != shared.language:
        return False, f"{Path(project_file).name} is a {lang or 'non-.NET'} project; {shared.name} is a {shared.language} shared project"
    return True, ""


def add_shared_reference(project_file, shared: SharedProject) -> bool:
    """Add > Shared Project Reference: write <Import Project="rel.projitems" Label="Shared" /> where VS puts it
    (SDK-style: before </Project>; legacy: before the language .targets import). False when already there."""
    ok, why = can_reference(project_file, shared)
    if not ok:
        raise ValueError(why)
    if references_shared(project_file, shared):
        return False
    ms = MSBuildProject.load(project_file)
    rel = ms_path(os.path.relpath(shared.projitems_path, Path(project_file).resolve().parent))
    text, nl = ms.file.text, ms.file.newline
    unit = ms._indent_unit()
    line = f'<Import Project="{xml_escape(rel)}" Label="Shared" />'
    m = None
    if not ms.is_sdk:
        m = re.search(r'^([ \t]*)<Import\s+Project="[^"]*Microsoft\.(?:CSharp|VisualBasic)(?:\.Core)?\.targets"[^>]*/>',
                      text, re.M)
    if m is not None:
        at = m.start()
        text = text[:at] + m.group(1) + line + nl + text[at:]
    else:
        end = text.rfind("</Project>")
        if end < 0:
            raise ValueError(f"{Path(project_file).name} has no </Project>")
        ls = text.rfind("\n", 0, end) + 1
        blank = nl if ms.is_sdk and not text[:ls].endswith(nl * 2) else ""      # VS: a blank line before it
        text = text[:ls] + blank + unit + line + nl + text[ls:]
    ms.file.text = text
    ms.save()
    return True


def remove_shared_reference(project_file, shared: SharedProject) -> bool:
    try:
        tf = TextFile.read(project_file)
    except OSError:
        return False
    n = _norm(shared.projitems_path)
    text = tf.text
    for m in _IMPORT_RX.finditer(text):
        if _norm(_resolve_import(Path(project_file), m.group(1))) != n:
            continue
        s, e = m.start(), m.end()
        ls = text.rfind("\n", 0, s) + 1
        if text[ls:s].strip() == "":
            s = ls
            mm = re.match(r"[ \t]*\r?\n", text[e:])
            if mm:
                e += mm.end()
        new = text[:s] + text[e:]
        nl = tf.newline
        new = new.replace(nl * 3, nl * 2)
        bad = nl * 2 + "</Project>"                       # blank line left before </Project> (SDK layout)
        if new.rstrip().endswith("</Project>") and bad in new and bad not in text:
            new = new.replace(bad, nl + "</Project>")
        tf.text = new
        tf.save()
        return True
    return False


def consumers(shared: SharedProject, project_files) -> list[Path]:
    """The project files (of *project_files*) that import *shared*."""
    return [Path(p) for p in project_files if references_shared(p, shared)]


# ====================================================================== solutions
def solution_shared_projects(sln_model) -> list[SharedProject]:
    """Shared projects listed in a radide.foreign.vs_solution.SlnModel / SlnxModel."""
    out = []
    for e in getattr(sln_model, "entries", []):
        if e.path.lower().endswith(".shproj"):
            p = (sln_model.folder / e.path).resolve()
            if p.is_file():
                try:
                    sp = SharedProject(p)
                except (OSError, ValueError):
                    continue
                sp.sln_entry = e
                out.append(sp)
    return out


def solution_entry_for(sln_model, shared: SharedProject):
    n = _norm(shared.path)
    return next((e for e in getattr(sln_model, "entries", []) if e.path.lower().endswith(".shproj")
                 and _norm(sln_model.folder / e.path) == n), None)


def add_to_solution(sln_model, shared: SharedProject, folder_guid: str = ""):
    """List the shared project in the solution (no configuration lines, like VS). Returns the entry."""
    have = solution_entry_for(sln_model, shared)
    if have is not None:
        return have
    if sln_model.path.suffix.lower() == ".slnx":
        sln_model.add_project(shared.path)
        sln_model.save()
        return solution_entry_for(sln_model, shared)
    rel = ms_path(os.path.relpath(shared.path, sln_model.folder))
    guid = shared.guid or _new_guid()
    nl, text = sln_model.file.newline, sln_model.file.text
    block = f'Project("{SHPROJ_TYPE_GUID}") = "{shared.name}", "{rel}", "{guid}"{nl}EndProject{nl}'
    m = re.search(r"^Global\s*$", text, re.M)
    at = m.start() if m else len(text)
    text = text[:at] + block + text[at:]
    if folder_guid:
        nest = f"\t\t{guid} = {folder_guid.upper()}"
        sec = re.search(r"^\s*GlobalSection\(NestedProjects\)[^\n]*\n(.*?)^\s*EndGlobalSection", text, re.M | re.S)
        if sec:
            text = text[:sec.end(1)] + nest + nl + text[sec.end(1):]
        else:
            g = re.search(r"^\s*EndGlobal\s*$", text, re.M)
            if g:
                ls = text.rfind("\n", 0, g.start()) + 1
                text = (text[:ls] + f"\tGlobalSection(NestedProjects) = preSolution{nl}{nest}{nl}\tEndGlobalSection{nl}"
                        + text[ls:])
    sln_model.file.text = text
    sln_model.parse()
    sln_model.save()
    return solution_entry_for(sln_model, shared)


def remove_from_solution(sln_model, shared: SharedProject) -> bool:
    e = solution_entry_for(sln_model, shared)
    if e is None:
        return False
    if sln_model.path.suffix.lower() == ".slnx":
        ok = sln_model.remove_project(e.guid)
    else:
        ok = sln_model.remove_project(e.guid)
        if ok:                                   # SharedMSBuildProjectFiles lines naming the .projitems
            pi = re.escape(ms_path(os.path.relpath(shared.projitems_path, sln_model.folder)))
            t = re.sub(r"^[ \t]*" + pi + r"\*[^\n]*\n", "", sln_model.file.text, flags=re.M | re.I)
            if t != sln_model.file.text:
                sln_model.file.text = t
                sln_model.parse()
    if ok:
        sln_model.save()
    return ok


def _rename_in_solution(sln_model, old_shproj: Path, shared: SharedProject) -> None:
    old_rel = ms_path(os.path.relpath(old_shproj, sln_model.folder))
    new_rel = ms_path(os.path.relpath(shared.path, sln_model.folder))
    text = sln_model.file.text
    if sln_model.path.suffix.lower() == ".slnx":
        a, b = old_rel.replace("\\", "/"), new_rel.replace("\\", "/")
        text = text.replace(f'"{a}"', f'"{b}"').replace(f'"{old_rel}"', f'"{new_rel}"')
    else:
        rx = re.compile(r'^(Project\("\{[^}]+\}"\)\s*=\s*")[^"]*("\s*,\s*")' + re.escape(old_rel) + r'(")', re.M | re.I)
        text = rx.sub(lambda m: m.group(1) + shared.name + m.group(2) + new_rel + m.group(3), text)
        old_pi = ms_path(os.path.relpath(old_shproj.with_suffix(".projitems"), sln_model.folder))
        text = text.replace(old_pi + "*", ms_path(os.path.relpath(shared.projitems_path, sln_model.folder)) + "*")
    sln_model.file.text = text
    sln_model.parse()
    sln_model.save()


__all__ = ["SHPROJ_TYPE_GUID", "SharedProject", "SharedItem", "ITEM_TEMPLATES", "create_shared_project",
           "shared_imports", "references_shared", "can_reference", "add_shared_reference",
           "remove_shared_reference", "consumers", "solution_shared_projects", "solution_entry_for",
           "add_to_solution", "remove_from_solution", "new_item_files"]
