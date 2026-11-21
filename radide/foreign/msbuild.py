"""MSBuild project files (.csproj / .vbproj / .fsproj / .vcxproj) - read AND edit in place.

* ``MSBuildProject.load(path)`` parses SDK-style (``<Project Sdk="Microsoft.NET.Sdk">``) and
  legacy (non-SDK, ``xmlns=".../msbuild/2003"``) projects: properties (OutputType,
  TargetFramework(s), RootNamespace, AssemblyName, StartupObject, ...), items (Compile, None,
  Content, EmbeddedResource, Reference, PackageReference, ProjectReference, ClCompile,
  ClInclude, ...), configurations/platforms and - for SDK projects - the implicit (globbed)
  items, so the IDE can show the project like Visual Studio.
* Edits (``add_item``, ``remove_item``, ``set_property``, ``add_package``...) are TEXT edits on
  the original file: comments, ordering, indentation, attribute quoting, the BOM and the
  newline style are kept. ``save()`` writes nothing when nothing changed, so open + save gives
  byte-identical files.
* Toolchains: ``find_dotnet()``, ``find_msbuild()`` (vswhere -> Visual Studio / Build Tools
  MSBuild, then the .NET Framework MSBuild), ``has_vc_tools()``, ``build_argv()``,
  ``get_properties()`` (``-getProperty`` evaluation: TargetPath, RunCommand, ...).

This module has no package-relative imports, so it also runs as a script (used by the NuGet
package manager of foreign projects)::

    python msbuild.py packages <project file>          # "Name Version" per PackageReference
    python msbuild.py add-package <project> <name> [version]
    python msbuild.py remove-package <project> <name>
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

LANG_BY_EXT = {".csproj": "C#", ".vbproj": "VB", ".fsproj": "F#", ".vcxproj": "C++"}
CODE_EXT = {"C#": ".cs", "VB": ".vb", "F#": ".fs", "C++": ".cpp"}
PROJECT_EXTS = tuple(LANG_BY_EXT)

# solution project type GUIDs (classic and SDK style)
TYPE_GUIDS = {
    "C#": "{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}", "C#-sdk": "{9A19103F-16F7-4668-BE54-9A1E7A4F7556}",
    "VB": "{F184B08F-C81C-45F6-A57F-5ABD9991F28F}", "VB-sdk": "{778DAE3C-4631-46EA-AA77-85C1314464D9}",
    "F#": "{F2A71F9B-5D33-465A-A702-920D77279786}", "F#-sdk": "{6EC3EE1D-3C4E-46DD-8F32-0CC8E7565705}",
    "C++": "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}",
}
FOLDER_GUID = "{2150E333-8FDC-42A3-9474-1A3956D46DE8}"

ITEM_KINDS = ("Compile", "None", "Content", "EmbeddedResource", "Page", "ApplicationDefinition", "Resource",
              "ClCompile", "ClInclude", "ResourceCompile", "Image", "Text", "Natvis", "Folder", "Manifest",
              "MASM")     # MASM: .asm items of a vcxproj with the masm build customization (masm.props/targets)
REF_KINDS = ("Reference", "PackageReference", "ProjectReference", "COMReference", "FrameworkReference")
SKIP_DIRS = {"bin", "obj", ".vs", ".git", ".idea", ".vscode", "node_modules", "packages", "x64", "x86",
             "Debug", "Release", "ARM64", "TestResults", ".radide"}


# ====================================================================== text helpers
@dataclass
class TextFile:
    """A text file read so that it can be written back byte-identically."""
    path: Path
    text: str                    # content with the file's own newlines
    encoding: str = "utf-8"
    bom: bytes = b""
    newline: str = "\n"
    original: bytes = b""

    @staticmethod
    def read(path) -> "TextFile":
        p = Path(path)
        raw = p.read_bytes()
        bom, enc = b"", "utf-8"
        if raw.startswith(b"\xef\xbb\xbf"):
            bom = b"\xef\xbb\xbf"
        elif raw.startswith(b"\xff\xfe"):
            bom, enc = b"\xff\xfe", "utf-16-le"
        elif raw.startswith(b"\xfe\xff"):
            bom, enc = b"\xfe\xff", "utf-16-be"
        body = raw[len(bom):]
        try:
            text = body.decode(enc)
        except UnicodeDecodeError:
            enc = "cp1252"
            text = body.decode(enc, errors="replace")
        nl = "\r\n" if "\r\n" in text else "\n"
        return TextFile(p, text, enc, bom, nl, raw)

    def encode(self) -> bytes:
        return self.bom + self.text.encode(self.encoding, errors="xmlcharrefreplace")

    @property
    def dirty(self) -> bool:
        return self.encode() != self.original

    def save(self) -> bool:
        """Write when changed; returns True when the file was written."""
        data = self.encode()
        if data == self.original:
            return False
        self.path.write_bytes(data)
        self.original = data
        return True


def xml_escape(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def xml_unescape(s: str) -> str:
    return (str(s).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
            .replace("&amp;", "&"))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def norm_rel(p: str) -> str:
    """MSBuild path (backslashes) -> forward-slash relative path."""
    return str(p).replace("\\", "/").lstrip("./") if not str(p).startswith("..") else str(p).replace("\\", "/")


def ms_path(rel: str) -> str:
    """Forward-slash path -> MSBuild spelling (backslashes)."""
    return str(rel).replace("/", "\\")


def glob_to_regex(pattern: str) -> re.Pattern:
    """MSBuild wildcard (``**``, ``*``, ``?``) -> regex over forward-slash relative paths."""
    pat = norm_rel(pattern)
    out, i = [], 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif pat[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pat[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pat[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$", re.IGNORECASE)


# ====================================================================== model
@dataclass
class Item:
    kind: str                     # Compile, None, PackageReference, ...
    include: str                  # as written (MSBuild spelling)
    metadata: dict = field(default_factory=dict)
    condition: str = ""
    implicit: bool = False        # SDK default glob (not written in the file)
    op: str = "Include"           # Include | Update | Remove

    @property
    def rel(self) -> str:
        return norm_rel(xml_unescape(self.include))

    @property
    def dependent_upon(self) -> str:
        return self.metadata.get("DependentUpon", "")

    @property
    def subtype(self) -> str:
        return self.metadata.get("SubType", "")

    @property
    def version(self) -> str:
        return self.metadata.get("Version", "")


class MSBuildProject:
    def __init__(self, path: Path, tf: TextFile):
        self.path = Path(path).resolve()
        self.file = tf
        self.parse()

    # ------------------------------------------------------------------ io
    @staticmethod
    def load(path) -> "MSBuildProject":
        return MSBuildProject(Path(path), TextFile.read(path))

    def reload(self) -> None:
        self.file = TextFile.read(self.path)
        self.parse()

    def save(self) -> bool:
        return self.file.save()

    @property
    def text(self) -> str:
        return self.file.text

    @property
    def folder(self) -> Path:
        return self.path.parent

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def language(self) -> str:
        return LANG_BY_EXT.get(self.path.suffix.lower(), "C#")

    @property
    def code_ext(self) -> str:
        return CODE_EXT.get(self.language, ".cs")

    # ------------------------------------------------------------------ parsing
    def parse(self) -> None:
        text = self.file.text
        try:
            root = ET.fromstring(text.encode("utf-8") if not text.lstrip().startswith("<?xml") else
                                 re.sub(r"^\s*<\?xml[^>]*\?>", "", text).encode("utf-8"))
        except ET.ParseError as e:
            raise ValueError(f"{self.path.name} is not a valid MSBuild project: {e}") from None
        self.root = root
        self.sdk = root.get("Sdk", "") or ""
        if not self.sdk:
            sdk_el = next((c for c in root if _local(c.tag) == "Sdk"), None)
            if sdk_el is not None:
                self.sdk = sdk_el.get("Name", "")
            imp = next((c for c in root if _local(c.tag) == "Import" and c.get("Sdk")), None)
            if imp is not None and not self.sdk:
                self.sdk = imp.get("Sdk", "")
        self.properties: dict[str, str] = {}               # unconditional (first wins like VS shows)
        self.cond_properties: list[tuple[str, str, str]] = []   # (condition, name, value)
        self.items: list[Item] = []
        self.configurations: list[str] = []                # "Debug|AnyCPU" ...
        for el in root:
            tag = _local(el.tag)
            if tag == "PropertyGroup":
                gcond = el.get("Condition", "")
                for p in el:
                    if not isinstance(p.tag, str):
                        continue
                    name, value = _local(p.tag), (p.text or "").strip()
                    cond = p.get("Condition", "")
                    if gcond or cond:
                        self.cond_properties.append((gcond or cond, name, value))
                        if not gcond and cond.replace(" ", "") == f"'$({name})'==''":
                            self.properties.setdefault(name, value)      # default value
                    else:
                        self.properties[name] = value
            elif tag == "ItemGroup":
                gcond = el.get("Condition", "")
                for it in el:
                    if not isinstance(it.tag, str):
                        continue
                    kind = _local(it.tag)
                    op = next((o for o in ("Include", "Update", "Remove") if it.get(o) is not None), "")
                    if not op:
                        continue
                    md = {k: v for k, v in it.attrib.items() if k not in ("Include", "Update", "Remove",
                                                                           "Condition", "Exclude")}
                    for m in it:
                        if isinstance(m.tag, str):
                            md[_local(m.tag)] = (m.text or "").strip()
                    if it.get("Exclude"):
                        md["Exclude"] = it.get("Exclude")
                    self.items.append(Item(kind, it.get(op), md, gcond or it.get("Condition", ""), False, op))
                    if kind == "ProjectConfiguration" and op == "Include":
                        self.configurations.append(it.get("Include"))
        if not self.configurations:
            seen = []
            for cond, _n, _v in self.cond_properties:
                m = re.search(r"'\$\(Configuration\)\|\$\(Platform\)'\s*==\s*'([^']+)'", cond)
                if m and m.group(1) not in seen:
                    seen.append(m.group(1))
            self.configurations = seen

    # ------------------------------------------------------------------ properties
    @property
    def is_sdk(self) -> bool:
        return bool(self.sdk)

    def prop(self, name: str, default: str = "") -> str:
        v = self.properties.get(name)
        if v is None:
            for _c, n, val in self.cond_properties:
                if n == name and val:
                    return val
        return v if v is not None else default

    @property
    def output_type(self) -> str:
        if self.language == "C++":
            ct = self.prop("ConfigurationType", "Application")
            return {"Application": "Exe", "DynamicLibrary": "Library", "StaticLibrary": "Library"}.get(ct, ct)
        return self.prop("OutputType", "Library")

    @property
    def is_library(self) -> bool:
        return self.output_type.lower() in ("library", "module")

    @property
    def target_frameworks(self) -> list[str]:
        tfs = self.prop("TargetFrameworks") or self.prop("TargetFramework")
        if not tfs and self.prop("TargetFrameworkVersion"):
            tfs = "net" + self.prop("TargetFrameworkVersion").lstrip("v").replace(".", "")
        return [t.strip() for t in tfs.split(";") if t.strip()]

    @property
    def assembly_name(self) -> str:
        return self.prop("AssemblyName") or self.name

    @property
    def root_namespace(self) -> str:
        return self.prop("RootNamespace") or re.sub(r"[^A-Za-z0-9_.]", "_", self.name)

    @property
    def startup_object(self) -> str:
        return self.prop("StartupObject")

    @property
    def is_netframework(self) -> bool:
        """Legacy .NET Framework (needs Visual Studio's MSBuild, not 'dotnet build')."""
        if self.language == "C++":
            return False
        if not self.is_sdk:
            return True
        return any(re.fullmatch(r"net[1-4]\d*", t) for t in self.target_frameworks)

    @property
    def is_windows_app(self) -> bool:
        return (self.prop("UseWindowsForms").lower() == "true" or self.prop("UseWPF").lower() == "true"
                or self.output_type == "WinExe")

    def configuration_names(self) -> list[str]:
        if self.configurations:
            return list(dict.fromkeys(c.split("|")[0] for c in self.configurations))
        extra = [c for c in self.prop("Configurations").split(";") if c]
        return extra or ["Debug", "Release"]

    def platform_names(self) -> list[str]:
        if self.configurations:
            return list(dict.fromkeys(c.split("|")[1] for c in self.configurations if "|" in c))
        extra = [c for c in self.prop("Platforms").split(";") if c]
        return extra or ["AnyCPU"]

    # ------------------------------------------------------------------ items
    def explicit(self, kind: str | None = None, op: str = "Include") -> list[Item]:
        return [i for i in self.items if (kind is None or i.kind == kind) and i.op == op]

    @property
    def package_references(self) -> list[Item]:
        return self.explicit("PackageReference")

    @property
    def project_references(self) -> list[Item]:
        return self.explicit("ProjectReference")

    @property
    def assembly_references(self) -> list[Item]:
        return self.explicit("Reference")

    def _default_items_enabled(self, kind: str) -> bool:
        if self.prop("EnableDefaultItems").lower() == "false":
            return False
        key = {"Compile": "EnableDefaultCompileItems", "EmbeddedResource": "EnableDefaultEmbeddedResourceItems",
               "None": "EnableDefaultNoneItems"}.get(kind)
        return not key or self.prop(key).lower() != "false"

    def disk_files(self, limit: int = 5000) -> list[str]:
        """Files under the project folder (relative, forward slashes), bin/obj/.vs skipped."""
        out: list[str] = []
        base = self.folder
        for dirpath, dirnames, filenames in os.walk(base):
            rel_dir = Path(dirpath).relative_to(base).as_posix()
            dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and
                                 not (d in SKIP_DIRS and (rel_dir == "." or d in ("bin", "obj"))))
            for f in sorted(filenames):
                rel = f if rel_dir == "." else f"{rel_dir}/{f}"
                out.append(rel)
                if len(out) >= limit:
                    return out
        return out

    def _matches(self, pattern: str, rel: str) -> bool:
        return any(glob_to_regex(p.strip()).match(rel) for p in xml_unescape(pattern).split(";") if p.strip())

    def files(self) -> list[Item]:
        """Every file item of the project, explicit and (SDK) implicit, with metadata merged from
        Update items and Remove items applied. Wildcard Includes are expanded."""
        out: list[Item] = []
        disk = None
        seen: set[tuple[str, str]] = set()

        def add(kind, rel, md, implicit, include=None):
            key = (kind, rel.lower())
            if key in seen or (implicit and any(k[1] == rel.lower() for k in seen)):
                return
            seen.add(key)
            out.append(Item(kind, include if include is not None else ms_path(rel), dict(md), "", implicit))

        for it in self.items:
            if it.op != "Include" or it.kind in REF_KINDS or it.kind in ("ProjectConfiguration", "Folder") or \
                    it.kind not in ITEM_KINDS and it.kind not in ("Compile",):
                continue
            inc = xml_unescape(it.include)
            if "$(" in inc:
                continue
            if any(ch in inc for ch in "*?"):
                if disk is None:
                    disk = self.disk_files()
                excl = it.metadata.get("Exclude", "")
                for rel in disk:
                    if self._matches(inc, rel) and not (excl and self._matches(excl, rel)):
                        add(it.kind, rel, {k: v for k, v in it.metadata.items() if k != "Exclude"}, False)
            else:
                add(it.kind, norm_rel(inc), it.metadata, False, it.include)
        if self.is_sdk:
            if disk is None:
                disk = self.disk_files()
            ext = self.code_ext
            removed = {k: [i.include for i in self.items if i.kind == k and i.op == "Remove"]
                       for k in ("Compile", "EmbeddedResource", "None", "Content", "Page")}
            wpf = self.prop("UseWPF").lower() == "true"
            for rel in disk:
                low = rel.lower()
                if low.endswith((".csproj", ".vbproj", ".fsproj", ".user", ".sln", ".slnx", ".vcxproj",
                                 ".filters")):
                    continue
                if low.endswith(ext) and self.language != "F#":
                    kind = "Compile"
                elif low.endswith(".resx"):
                    kind = "EmbeddedResource"
                elif wpf and low.endswith(".xaml"):
                    kind = "ApplicationDefinition" if low in ("app.xaml", "application.xaml") else "Page"
                else:
                    kind = "None"
                if not self._default_items_enabled(kind):
                    continue
                if any(self._matches(p, rel) for p in removed.get(kind, [])):
                    continue
                md = {}
                if kind == "EmbeddedResource" or low.endswith(".designer" + ext):
                    stem = rel[: -len(Path(rel).suffix)]
                    if stem.lower().endswith(".designer"):
                        stem = stem[: -len(".designer")]
                    for cand in (stem + ext, stem + ".xaml"):
                        if (self.folder / cand).exists():
                            md["DependentUpon"] = Path(cand).name
                            break
                add(kind, rel, md, True)
        # Update items: merge metadata
        for it in self.items:
            if it.op != "Update":
                continue
            for f in out:
                if f.kind == it.kind and self._matches(it.include, f.rel):
                    f.metadata.update(it.metadata)
        return out

    def code_files(self) -> list[str]:
        exts = (self.code_ext,) if self.language != "C++" else (".cpp", ".c", ".cc", ".cxx", ".h", ".hpp", ".hxx")
        return [f.rel for f in self.files() if f.rel.lower().endswith(exts) and f.kind in
                ("Compile", "ClCompile", "ClInclude", "None")]

    # ------------------------------------------------------------------ edits (text, format preserving)
    def _indent_unit(self) -> str:
        m = re.search(r"\n([ \t]+)<(?:PropertyGroup|ItemGroup|Import)\b", self.file.text)
        return m.group(1) if m else "  "

    def _groups(self, tag: str):
        """(start, end, open_tag_text, body_start, body_end) of each top-level <tag> element."""
        rx = re.compile(rf"<{tag}\b([^>]*?)(/?)>", re.S)
        text = self.file.text
        out = []
        for m in rx.finditer(text):
            if m.group(2) == "/":
                out.append((m.start(), m.end(), m.group(0), m.end(), m.end()))
                continue
            close = text.find(f"</{tag}>", m.end())
            if close < 0:
                continue
            out.append((m.start(), close + len(f"</{tag}>"), m.group(0), m.end(), close))
        return out

    def _line_start(self, pos: int) -> int:
        return self.file.text.rfind("\n", 0, pos) + 1

    def _indent_at(self, pos: int) -> str:
        ls = self._line_start(pos)
        m = re.match(r"[ \t]*", self.file.text[ls:pos])
        return m.group(0) if m else ""

    def _element_rx(self, kind: str, include: str, op: str = "Include") -> re.Pattern:
        inc = r"[\\/]".join(re.escape(part) for part in re.split(r"[\\/]", xml_escape(xml_unescape(include))))
        return re.compile(rf"<{kind}\b(?=[^>]*\b{op}\s*=\s*(['\"]){inc}\1)[^>]*?(?:/>|>.*?</{kind}\s*>)",
                          re.S | re.I)

    def find_element(self, kind: str, include: str, op: str = "Include") -> tuple[int, int] | None:
        m = self._element_rx(kind, include, op).search(self.file.text)
        return (m.start(), m.end()) if m else None

    def _element_text(self, kind: str, include: str, metadata: dict | None, indent: str, unit: str,
                      op: str = "Include", attrs: dict | None = None) -> str:
        nl = self.file.newline
        a = "".join(f' {k}="{xml_escape(v)}"' for k, v in (attrs or {}).items())
        head = f'{indent}<{kind} {op}="{xml_escape(include)}"{a}'
        if not metadata:
            return head + " />"
        body = "".join(f"{nl}{indent}{unit}<{k}>{xml_escape(v)}</{k}>" for k, v in metadata.items())
        return f"{head}>{body}{nl}{indent}</{kind}>"

    def add_item(self, kind: str, include: str, metadata: dict | None = None, attrs: dict | None = None,
                 op: str = "Include") -> bool:
        """Insert ``<kind Include="...">`` next to items of the same kind (alphabetical among
        them when they are sorted), in the file's own indentation. False when it already exists."""
        include = ms_path(include) if kind not in REF_KINDS or kind == "ProjectReference" else include
        if self.find_element(kind, include, op):
            return False
        text, nl, unit = self.file.text, self.file.newline, self._indent_unit()
        best = None
        for g in self._groups("ItemGroup"):
            if "Condition" in g[2] or g[3] == g[4]:
                continue
            body = text[g[3]:g[4]]
            elems = list(re.finditer(rf"<{kind}\b[^>]*\b{op}\s*=\s*(['\"])(.*?)\1[^>]*?(?:/>|>.*?</{kind}\s*>)",
                                     body, re.S))
            if elems:
                best = (g, elems)
        if best is not None:
            g, elems = best
            names = [xml_unescape(e.group(2)).lower() for e in elems]
            pos_el = elems[-1]
            if names == sorted(names):
                for e, n in zip(elems, names):
                    if n > include.lower():
                        pos_el = e
                        break
                else:
                    pos_el = None
            if pos_el is not None and xml_unescape(pos_el.group(2)).lower() > include.lower() and \
                    names == sorted(names):
                at = g[3] + pos_el.start()
                indent = self._indent_at(at)
                ls = self._line_start(at)
                new = self._element_text(kind, include, metadata, indent, unit, op, attrs) + nl
                self.file.text = text[:ls] + new + text[ls:]
            else:
                last = elems[-1]
                at = g[3] + last.start()
                indent = self._indent_at(at)
                end = g[3] + last.end()
                new = nl + self._element_text(kind, include, metadata, indent, unit, op, attrs)
                self.file.text = text[:end] + new + text[end:]
        else:
            groups = self._groups("ItemGroup") or self._groups("PropertyGroup")
            proj_indent = unit
            if groups:
                anchor_end = groups[-1][1]
                proj_indent = self._indent_at(groups[-1][0])
            else:
                m = re.search(r"</Project\s*>", text)
                anchor_end = self._line_start(m.start()) - len(nl) if m else len(text)
            el = self._element_text(kind, include, metadata, proj_indent + unit, unit, op, attrs)
            blank = nl if self.is_sdk else ""
            block = f"{nl}{blank}{proj_indent}<ItemGroup>{nl}{el}{nl}{proj_indent}</ItemGroup>"
            self.file.text = text[:anchor_end] + block + text[anchor_end:]
        self.parse()
        return True

    def remove_item(self, kind: str, include: str, op: str = "Include") -> bool:
        """Remove an item element (and its line); an ItemGroup left empty is removed too."""
        span = self.find_element(kind, include, op)
        if span is None and kind not in REF_KINDS:
            span = self.find_element(kind, ms_path(include), op)
        if span is None:
            return False
        text = self.file.text
        s, e = span
        ls = self._line_start(s)
        if text[ls:s].strip() == "":
            s = ls
            m = re.match(r"[ \t]*\r?\n", text[e:])
            if m:
                e += m.end()
        self.file.text = text[:s] + text[e:]
        # empty ItemGroup
        for g in reversed(self._groups("ItemGroup")):
            body = self.file.text[g[3]:g[4]]
            if g[3] != g[4] and body.strip() == "":
                t = self.file.text
                gs, ge = g[0], g[1]
                ls = self._line_start(gs)
                if t[ls:gs].strip() == "":
                    gs = ls
                    m = re.match(r"[ \t]*\r?\n", t[ge:])
                    if m:
                        ge += m.end()
                # a blank line left before the removed group (SDK layout) goes too
                before = t[:gs]
                if before.endswith(self.file.newline * 2):
                    gs -= len(self.file.newline)
                self.file.text = t[:gs] + t[ge:]
        self.parse()
        return True

    def set_metadata(self, kind: str, include: str, name: str, value: str) -> bool:
        span = self.find_element(kind, include)
        if span is None:
            return False
        text = self.file.text
        el = text[span[0]:span[1]]
        if re.search(rf"\b{name}\s*=\s*(['\"])", el.split(">", 1)[0]):
            new = re.sub(rf"(\b{name}\s*=\s*)(['\"])(.*?)\2", lambda m: f'{m.group(1)}"{xml_escape(value)}"', el, 1)
        elif re.search(rf"<{name}>", el):
            new = re.sub(rf"<{name}>.*?</{name}>", f"<{name}>{xml_escape(value)}</{name}>", el, 1, re.S)
        elif el.rstrip().endswith("/>"):
            new = re.sub(r"\s*/>$", f' {name}="{xml_escape(value)}" />', el.rstrip())
        else:
            indent = self._indent_at(span[0])
            unit = self._indent_unit()
            close = el.rfind("</")
            new = el[:close].rstrip() + f"{self.file.newline}{indent}{unit}<{name}>{xml_escape(value)}</{name}>" + \
                f"{self.file.newline}{indent}" + el[close:]
        self.file.text = text[:span[0]] + new + text[span[1]:]
        self.parse()
        return True

    def set_property(self, name: str, value: str) -> bool:
        """Change (or add) an unconditional property in place. Returns True when changed."""
        text = self.file.text
        for g in self._groups("PropertyGroup"):
            if "Condition" in g[2]:
                continue
            body = text[g[3]:g[4]]
            m = re.search(rf"<{name}(\s[^>]*)?>(.*?)</{name}\s*>", body, re.S)
            if m and (not m.group(1) or "Condition" not in m.group(1)):
                if xml_unescape(m.group(2)) == value:
                    return False
                a, b = g[3] + m.start(2), g[3] + m.end(2)
                self.file.text = text[:a] + xml_escape(value) + text[b:]
                self.parse()
                return True
        for g in self._groups("PropertyGroup"):
            if "Condition" in g[2] or g[3] == g[4]:
                continue
            body = text[g[3]:g[4]]
            last = list(re.finditer(r"<(\w+)(?:\s[^>]*)?>.*?</\1\s*>|<\w+[^>]*/>", body, re.S))
            if last:
                at = g[3] + last[-1].start()
                indent = self._indent_at(at)
                end = g[3] + last[-1].end()
                self.file.text = text[:end] + f"{self.file.newline}{indent}<{name}>{xml_escape(value)}</{name}>" + \
                    text[end:]
                self.parse()
                return True
        return False

    # packages / references -------------------------------------------------------
    def add_package(self, name: str, version: str = "") -> bool:
        attrs = {"Version": version} if version else {}
        if self.find_element("PackageReference", name):
            if version:
                return self.set_metadata("PackageReference", name, "Version", version)
            return False
        return self.add_item("PackageReference", name, None, attrs)

    def remove_package(self, name: str) -> bool:
        return self.remove_item("PackageReference", name)

    def add_project_reference(self, target: Path, guid: str = "", name: str = "") -> bool:
        rel = os.path.relpath(Path(target).resolve(), self.folder)
        md = None
        if not self.is_sdk:
            md = {}
            if guid:
                md["Project"] = guid
            md["Name"] = name or Path(target).stem
        return self.add_item("ProjectReference", ms_path(rel), md)

    def remove_project_reference(self, include: str) -> bool:
        return self.remove_item("ProjectReference", include)

    def add_assembly_reference(self, name: str, hint_path: str = "") -> bool:
        md = {"HintPath": ms_path(hint_path)} if hint_path else None
        return self.add_item("Reference", name, md)

    def needs_compile_entry(self, rel: str) -> bool:
        """SDK C#/VB projects glob their code files; legacy projects, F# and C++ list them."""
        return not (self.is_sdk and self.language in ("C#", "VB") and rel.lower().endswith(self.code_ext))

    def add_source(self, rel: str, kind: str = "", metadata: dict | None = None) -> bool:
        """Register a new source file the way this project type needs it."""
        low = rel.lower()
        if not kind:
            if self.language == "C++":
                kind = "ClInclude" if low.endswith((".h", ".hpp", ".hxx")) else "ClCompile"
            elif low.endswith(self.code_ext):
                kind = "Compile"
            elif low.endswith(".resx"):
                kind = "EmbeddedResource"
            else:
                kind = "None"
        if self.is_sdk and self.language in ("C#", "VB") and kind in ("Compile", "EmbeddedResource", "None"):
            # implicit items: only metadata that the SDK cannot infer needs an Update entry
            if metadata and set(metadata) - {"SubType", "DependentUpon"}:
                return self.add_item(kind, ms_path(rel), metadata, op="Update")
            return False
        if self.language == "F#" and kind == "Compile":
            return self._add_fsharp_compile(rel)
        return self.add_item(kind, ms_path(rel), metadata)

    def _add_fsharp_compile(self, rel: str) -> bool:
        """F# compiles in file order: a new file goes before the last Compile (Program.fs)."""
        comps = self.explicit("Compile")
        if not comps:
            return self.add_item("Compile", ms_path(rel))
        if self.find_element("Compile", ms_path(rel)):
            return False
        last = comps[-1]
        span = self.find_element("Compile", last.include)
        if span is None:
            return self.add_item("Compile", ms_path(rel))
        text, ls = self.file.text, self._line_start(span[0])
        indent = self._indent_at(span[0])
        new = f'{indent}<Compile Include="{xml_escape(ms_path(rel))}" />{self.file.newline}'
        if len(comps) == 1 and Path(last.rel).stem.lower() not in ("program", "main"):
            end = span[1]
            self.file.text = text[:end] + self.file.newline + new.rstrip("\r\n") + text[end:]
        else:
            self.file.text = text[:ls] + new + text[ls:]
        self.parse()
        return True

    def remove_source(self, rel: str) -> bool:
        """Exclude a file from the project (SDK: <Compile Remove>; listed items: remove the entry)."""
        for f in self.files():
            if f.rel.lower() == norm_rel(rel).lower():
                if not f.implicit:
                    return self.remove_item(f.kind, f.include)
                return self.add_item(f.kind, ms_path(rel), None, op="Remove")
        return False


# ====================================================================== vcxproj filters
def filters_file(project: MSBuildProject) -> Path:
    return project.path.with_name(project.path.name + ".filters")


def read_filters(project: MSBuildProject) -> dict[str, str]:
    """{relative file: filter folder} from <project>.vcxproj.filters (Solution Explorer folders)."""
    p = filters_file(project)
    if not p.exists():
        return {}
    try:
        root = ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", TextFile.read(p).text).encode("utf-8"))
    except ET.ParseError:
        return {}
    out = {}
    for g in root:
        if _local(g.tag) != "ItemGroup":
            continue
        for it in g:
            inc = it.get("Include")
            flt = next((c.text for c in it if _local(c.tag) == "Filter"), None)
            if inc and flt and _local(it.tag) != "Filter":
                out[norm_rel(inc).lower()] = flt.strip().replace("\\", "/")
    return out


def add_to_filters(project: MSBuildProject, rel: str, kind: str, flt: str = "") -> bool:
    p = filters_file(project)
    if not p.exists():
        return False
    fp = MSBuildProject.__new__(MSBuildProject)
    fp.path, fp.file = p, TextFile.read(p)
    try:
        fp.parse()
    except ValueError:
        return False
    if not flt:
        flt = "Header Files" if kind == "ClInclude" else "Source Files"
        if not fp.find_element("Filter", flt):
            flt = ""
    ok = fp.add_item(kind, ms_path(rel), {"Filter": flt} if flt else None)
    fp.save()
    return ok


# ====================================================================== toolchains
def find_dotnet() -> str:
    p = shutil.which("dotnet")
    if p:
        return p
    for c in (r"C:\Program Files\dotnet\dotnet.exe", os.path.expanduser(r"~\.dotnet\dotnet.exe")):
        if os.path.isfile(c):
            return c
    return ""


def find_vswhere() -> str:
    for base in (os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), os.environ.get("ProgramFiles", "")):
        p = Path(base) / "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
        if base and p.is_file():
            return str(p)
    return shutil.which("vswhere") or ""


_CACHE: dict = {}


def _vswhere(*args) -> list[str]:
    vw = find_vswhere()
    if not vw:
        return []
    try:
        out = subprocess.run([vw, "-nologo", "-products", "*", *args], capture_output=True, text=True,
                             timeout=30, creationflags=NO_WINDOW).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def find_msbuild() -> str:
    """Visual Studio / Build Tools MSBuild (vswhere), else the .NET Framework 4 MSBuild, else ""."""
    if "msbuild" not in _CACHE:
        hit = ""
        found = _vswhere("-latest", "-requires", "Microsoft.Component.MSBuild", "-find", r"MSBuild\**\Bin\MSBuild.exe")
        if found:
            hit = found[0]
        if not hit:
            hit = shutil.which("msbuild") or ""
        if not hit:
            fw = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET" / "Framework64" / "v4.0.30319" / \
                "MSBuild.exe"
            hit = str(fw) if fw.is_file() else ""
        _CACHE["msbuild"] = hit
    return _CACHE["msbuild"]


def msbuild_is_full(msbuild: str) -> bool:
    """True for a Visual Studio / Build Tools MSBuild (the Framework 4 one cannot build SDK or C++)."""
    return bool(msbuild) and "Microsoft.NET" not in msbuild


def has_vc_tools() -> bool:
    if "vc" not in _CACHE:
        _CACHE["vc"] = bool(_vswhere("-latest", "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                                     "-property", "installationPath"))
    return _CACHE["vc"]


def find_mingw_gpp() -> str:
    p = shutil.which("g++")
    if p:
        return p
    cand = Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE" / "toolchains" / "mingw64" / "bin" / "g++.exe"
    return str(cand) if cand.is_file() else ""


def toolchain_report() -> dict:
    return {"dotnet": find_dotnet(), "msbuild": find_msbuild(), "vc_tools": has_vc_tools(),
            "vswhere": find_vswhere(), "mingw": find_mingw_gpp()}


def project_platform(platform: str, project: MSBuildProject | None = None) -> str:
    """Solution platform -> project platform ("Any CPU" -> "AnyCPU", C++ "x86" -> "Win32")."""
    p = (platform or "").strip()
    if project is not None and project.language == "C++":
        if p in ("", "Any CPU", "AnyCPU"):
            names = project.platform_names()
            return "x64" if "x64" in names else (names[0] if names else "x64")
        return "Win32" if p == "x86" else p
    return "AnyCPU" if p in ("Any CPU", "") else p


def uses_dotnet_cli(project: MSBuildProject) -> bool:
    return project.is_sdk and not project.is_netframework and project.language != "C++"


def build_argv(target: Path, configuration: str = "Debug", platform: str = "", *, sdk: bool = True,
               verb: str = "build", project: MSBuildProject | None = None) -> list[str] | None:
    """Command line that builds *target* (.sln/.slnx or a project). None = no suitable tool."""
    target = Path(target)
    is_solution = target.suffix.lower() in (".sln", ".slnx")
    if sdk:
        dn = find_dotnet()
        if not dn:
            return None
        argv = [dn, verb, str(target), "-c", configuration or "Debug", "-nologo"]
        if verb == "build":
            argv += ["-v:m", "-clp:NoSummary"]
        if is_solution and platform and platform not in ("Any CPU", "AnyCPU"):
            argv.append(f"-p:Platform={platform}")
        elif not is_solution and platform and platform not in ("Any CPU", "AnyCPU"):
            argv.append(f"-p:Platform={project_platform(platform, project)}")
        return argv
    ms = find_msbuild()
    if not ms:
        return None
    t = {"build": "Build", "rebuild": "Rebuild", "clean": "Clean"}.get(verb, "Build")
    plat = platform if is_solution else project_platform(platform, project)
    argv = [ms, str(target), "-nologo", "-v:m", f"-t:{t}", f"-p:Configuration={configuration or 'Debug'}"]
    if plat:
        argv.append(f"-p:Platform={plat}")
    if verb != "clean":
        argv.insert(2, "-restore")
    return argv


def get_properties(project: MSBuildProject | Path, names: list[str], configuration: str = "Debug",
                   platform: str = "", timeout: int = 120) -> dict[str, str]:
    """Evaluate properties with ``-getProperty`` (MSBuild 17.8+ / .NET 8+). {} on failure."""
    proj = project if isinstance(project, MSBuildProject) else MSBuildProject.load(project)
    if uses_dotnet_cli(proj):
        dn = find_dotnet()
        if not dn:
            return {}
        argv = [dn, "msbuild", str(proj.path), "-nologo"]
    else:
        ms = find_msbuild()
        if not ms or not msbuild_is_full(ms):
            return {}
        argv = [ms, str(proj.path), "-nologo"]
    argv += [f"-getProperty:{n}" for n in names] + [f"-p:Configuration={configuration or 'Debug'}"]
    plat = project_platform(platform, proj)
    if plat and not (uses_dotnet_cli(proj) and plat == "AnyCPU"):
        argv.append(f"-p:Platform={plat}")
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=str(proj.folder),
                           creationflags=NO_WINDOW, env={**os.environ, "DOTNET_NOLOGO": "1",
                                                         "DOTNET_CLI_TELEMETRY_OPTOUT": "1"})
    except (OSError, subprocess.TimeoutExpired):
        return {}
    out = (r.stdout or "").strip()
    if not out or r.returncode != 0:
        return {}
    if len(names) == 1:
        return {names[0]: out.splitlines()[-1].strip()}
    try:
        d = json.loads(out[out.find("{"):])
        return {k: str(v) for k, v in (d.get("Properties") or {}).items()}
    except ValueError:
        return {}


def guess_target_path(project: MSBuildProject, configuration: str = "Debug", platform: str = "") -> Path:
    """Where the build output most likely is, without running MSBuild (fallback)."""
    cfg = configuration or "Debug"
    if project.language == "C++":
        plat = project_platform(platform, project)
        base = project.folder / (plat if plat != "Win32" else "") / cfg
        return base / (project.prop("TargetName") or project.name + ".exe")
    ext = ".exe" if not project.is_library else ".dll"
    if project.is_sdk:
        tfs = project.target_frameworks
        tf = tfs[0] if tfs else ""
        out = project.folder / "bin" / cfg / tf
        if not project.is_netframework and not project.is_library:
            ext = ".dll"
        return out / (project.assembly_name + ext)
    outp = ""
    for cond, n, v in project.cond_properties:
        if n == "OutputPath" and f"'{cfg}|" in cond:
            outp = v
            break
    outp = outp or f"bin\\{cfg}\\"
    return project.folder / ms_path(outp).replace("\\", os.sep) / (project.assembly_name + ext)


# ====================================================================== CLI (package manager)
def _cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, path = argv[0], argv[1]
    proj = MSBuildProject.load(path)
    if cmd == "packages":
        for it in proj.package_references:
            print(f"{xml_unescape(it.include)} {it.version or '*'}")
        return 0
    if cmd == "add-package" and len(argv) >= 3:
        changed = proj.add_package(argv[2], argv[3] if len(argv) > 3 else "*")
        proj.save()
        print(("Added " if changed else "Already present: ") + argv[2])
        return 0
    if cmd == "remove-package" and len(argv) >= 3:
        changed = proj.remove_package(argv[2])
        proj.save()
        print(("Removed " if changed else "Not referenced: ") + argv[2])
        return 0
    if cmd == "info":
        print(json.dumps({"sdk": proj.sdk, "language": proj.language, "output_type": proj.output_type,
                          "tfms": proj.target_frameworks, "files": [f.rel for f in proj.files()]}, indent=2))
        return 0
    print(f"unknown command {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))


__all__ = ["MSBuildProject", "Item", "TextFile", "build_argv", "get_properties", "find_dotnet", "find_msbuild",
           "has_vc_tools", "find_vswhere", "find_mingw_gpp", "toolchain_report", "guess_target_path",
           "project_platform", "uses_dotnet_cli", "read_filters", "add_to_filters", "glob_to_regex"]
