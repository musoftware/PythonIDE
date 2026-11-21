"""Reference edits on a project file (format preserving, through radide/foreign/msbuild.py).

Every function takes an MSBuildProject (``project.ms``) or a VsProject and only changes the text; callers
save + reload (``commit(project)``) so the Solution Explorer, the build and the C# language server see it.

Item shapes written (what Visual Studio 2022 writes):

    <Reference Include="System.Windows.Forms" />                                   Framework / Extensions
    <Reference Include="MyLib"><HintPath>..\\MyLib\\bin\\Debug\\MyLib.dll</HintPath></Reference>  Browse
    <COMReference Include="Scripting"><WrapperTool>tlbimp</WrapperTool><VersionMinor>0</VersionMinor>
        <VersionMajor>1</VersionMajor><Guid>420b...</Guid><Lcid>0</Lcid><Isolated>false</Isolated>
        <EmbedInteropTypes>true</EmbedInteropTypes></COMReference>                  COM
    <FrameworkReference Include="Microsoft.AspNetCore.App" />                      SDK shared frameworks
    <Import Project="..\\Shared\\Shared.projitems" Label="Shared" />                Shared Projects
    <Compile Include="..\\Common\\Helper.cs" Link="Helper.cs" />                    Add As Link
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from ...foreign.msbuild import MSBuildProject, ms_path, norm_rel, xml_escape, xml_unescape

REF_ITEM = {"assembly": "Reference", "com": "COMReference", "project": "ProjectReference",
            "package": "PackageReference", "framework": "FrameworkReference"}


def _ms(p) -> MSBuildProject:
    return getattr(p, "ms", p)


@dataclass
class RefInfo:
    kind: str                     # assembly / com / project / package / framework / shared
    include: str                  # as written (escaped)
    metadata: dict = field(default_factory=dict)
    implicit: bool = False        # an SDK shared framework nobody wrote

    @property
    def item(self) -> str:
        return REF_ITEM.get(self.kind, "Import")

    @property
    def name(self) -> str:
        inc = xml_unescape(self.include)
        if self.kind in ("project", "shared"):
            return Path(inc.replace("\\", "/")).stem
        return inc.split(",")[0].strip()


def references(project) -> list[RefInfo]:
    ms = _ms(project)
    out = []
    for kind, item in REF_ITEM.items():
        for it in ms.explicit(item):
            out.append(RefInfo(kind, it.include, dict(it.metadata)))
    for imp in shared_imports(ms):
        out.append(RefInfo("shared", imp, {"Label": "Shared"}))
    return out


def find(project, kind: str, include: str) -> RefInfo | None:
    low = xml_unescape(include).lower()
    for r in references(project):
        if r.kind == kind and xml_unescape(r.include).lower() == low:
            return r
    return None


def has_assembly(project, name: str) -> bool:
    n = name.lower()
    return any(xml_unescape(i.include).split(",")[0].strip().lower() == n for i in _ms(project).explicit("Reference"))


# ---------------------------------------------------------------- assemblies
def add_framework_assembly(project, name: str) -> bool:
    ms = _ms(project)
    if has_assembly(ms, name):
        return False
    return ms.add_item("Reference", name)


def remove_assembly(project, name: str) -> bool:
    ms = _ms(project)
    n = name.lower()
    for it in ms.explicit("Reference"):
        if xml_unescape(it.include).split(",")[0].strip().lower() == n:
            return ms.remove_item("Reference", it.include)
    return False


class BrowseError(ValueError):
    pass


def browse_reference_check(path) -> dict:
    """{'managed': bool, 'kind': 'managed'|'native'|'winmd'|'', 'identity': {...}} for the Browse tab."""
    from .metadata import NotManaged, assembly_identity, pe_kind
    p = Path(path)
    if not p.is_file():
        raise BrowseError(f"'{p}' could not be found.")
    if p.suffix.lower() == ".winmd":
        try:
            return {"managed": True, "kind": "winmd", "identity": assembly_identity(p)}
        except NotManaged:
            return {"managed": True, "kind": "winmd", "identity": {"name": p.stem}}
    kind = pe_kind(p)
    if kind == "managed":
        try:
            return {"managed": True, "kind": "managed", "identity": assembly_identity(p)}
        except NotManaged as e:
            raise BrowseError(str(e)) from None
    if kind == "native":
        return {"managed": False, "kind": "native", "identity": {"name": p.stem}}
    raise BrowseError(f"A reference to '{p.name}' could not be added. Please make sure that the file is "
                      f"accessible, and that it is a valid assembly or COM component.")


def add_browse_reference(project, path) -> tuple[bool, str]:
    """Reference Include=<name> + HintPath (relative). Returns (changed, include)."""
    ms = _ms(project)
    p = Path(path).resolve()
    info = browse_reference_check(p)
    if not info["managed"]:
        raise BrowseError(f"'{p.name}' is a native DLL, not a .NET assembly.")
    ident = info["identity"]
    name = ident.get("name") or p.stem
    try:
        hint = os.path.relpath(p, ms.folder)
    except ValueError:                             # another drive
        hint = str(p)
    include = name
    md = {}
    if not ms.is_sdk and ident.get("token"):       # VS (legacy projects): full identity + SpecificVersion
        include = (f"{name}, Version={ident['version']}, Culture={ident.get('culture') or 'neutral'}, "
                   f"PublicKeyToken={ident['token']}, processorArchitecture=MSIL")
        md["SpecificVersion"] = "False"
    md["HintPath"] = ms_path(hint)
    for it in ms.explicit("Reference"):           # same simple name already there: update its HintPath
        if xml_unescape(it.include).split(",")[0].strip().lower() == name.lower():
            if it.metadata.get("HintPath", "").lower() == ms_path(hint).lower():
                return False, it.include
            ms.set_metadata("Reference", it.include, "HintPath", ms_path(hint))
            return True, it.include
    return ms.add_item("Reference", include, md), include


def add_native_copy(project, path) -> bool:
    """A native DLL is not referenced: it is copied next to the program (for DllImport)."""
    ms = _ms(project)
    p = Path(path).resolve()
    try:
        rel = p.relative_to(ms.folder).as_posix()
        inside = True
    except ValueError:
        rel = os.path.relpath(p, ms.folder)
        inside = False
    md = {} if inside else {"Link": p.name}
    md["CopyToOutputDirectory"] = "PreserveNewest"
    if inside and ms.is_sdk:
        return ms.add_item("None", ms_path(rel), md, op="Update")
    return ms.add_item("None", ms_path(rel), md)


# ---------------------------------------------------------------- COM
def add_com_reference(project, entry, embed: bool = True) -> tuple[bool, str]:
    """COMReference for a type library (catalog.TypeLibEntry)."""
    from .catalog import typelib_name
    ms = _ms(project)
    name = entry.lib_name or typelib_name(entry.path) or re.sub(r"\W", "", entry.name) or "ComLib"
    for it in ms.explicit("COMReference"):
        if it.metadata.get("Guid", "").strip("{}").lower() == entry.guid:
            return False, it.include
    md = {"WrapperTool": "tlbimp", "VersionMinor": str(entry.minor), "VersionMajor": str(entry.major),
          "Guid": entry.guid, "Lcid": str(entry.lcid), "Isolated": "false",
          "EmbedInteropTypes": "true" if embed else "false"}
    return ms.add_item("COMReference", name, md), name


def remove_com_reference(project, include: str) -> bool:
    return _ms(project).remove_item("COMReference", include)


# ---------------------------------------------------------------- SDK shared frameworks
def add_framework_reference(project, name: str) -> bool:
    ms = _ms(project)
    if any(it.include.lower() == name.lower() for it in ms.explicit("FrameworkReference")):
        return False
    return ms.add_item("FrameworkReference", name)


def remove_framework_reference(project, name: str) -> bool:
    return _ms(project).remove_item("FrameworkReference", name)


# ---------------------------------------------------------------- Shared Projects (<Import Label="Shared">)
_IMPORT_RX = re.compile(r"<Import\b(?=[^>]*\bLabel\s*=\s*(['\"])Shared\1)[^>]*?\bProject\s*=\s*(['\"])(.*?)\2[^>]*/>",
                        re.S | re.I)
_IMPORT_RX2 = re.compile(r"<Import\b[^>]*?\bProject\s*=\s*(['\"])([^'\"]*\.projitems)\1[^>]*/>", re.S | re.I)


def shared_imports(project) -> list[str]:
    text = _ms(project).text
    found = [m.group(3) for m in _IMPORT_RX.finditer(text)]
    for m in _IMPORT_RX2.finditer(text):
        if m.group(2) not in found:
            found.append(m.group(2))
    return found


def add_shared_import(project, projitems) -> bool:
    ms = _ms(project)
    rel = ms_path(os.path.relpath(Path(projitems).resolve(), ms.folder))
    if any(xml_unescape(x).lower() == rel.lower() for x in shared_imports(ms)):
        return False
    text, nl = ms.file.text, ms.file.newline
    unit = ms._indent_unit()
    line = f'<Import Project="{xml_escape(rel)}" Label="Shared" />'
    # legacy: before the language targets import (where VS puts it); SDK: before </Project>
    m = re.search(r"[ \t]*<Import\b[^>]*Project\s*=\s*\"\$\(MSBuild(?:Tools|Bin|Extensions)Path\)[^\"]*\."
                  r"(?:CSharp|VisualBasic|FSharp)\.targets\"[^>]*/>", text)
    if m:
        at = m.start()
        indent = re.match(r"[ \t]*", text[at:]).group(0)
        ms.file.text = text[:at] + indent + line + nl + text[at:]
    else:
        end = text.rfind("</Project>")
        if end < 0:
            return False
        ls = text.rfind("\n", 0, end) + 1
        before = text[:ls]
        blank = nl if ms.is_sdk and not before.endswith(nl * 2) else ""
        ms.file.text = before + blank + unit + line + nl + (nl if ms.is_sdk else "") + text[ls:]
        ms.file.text = re.sub(rf"({re.escape(nl)}){{3,}}</Project>", nl + "</Project>", ms.file.text)
    ms.parse()
    return True


def remove_shared_import(project, include: str) -> bool:
    ms = _ms(project)
    text = ms.file.text
    inc = re.escape(xml_escape(xml_unescape(include))).replace(r"\\", r"[\\/]")
    m = re.search(rf"[ \t]*<Import\b[^>]*\bProject\s*=\s*(['\"]){inc}\1[^>]*/>[ \t]*\r?\n?", text, re.I)
    if not m:
        return False
    ms.file.text = text[:m.start()] + text[m.end():]
    ms.parse()
    return True


# ---------------------------------------------------------------- metadata (Properties window)
def get_metadata(project, item: str, include: str, name: str, default: str = "") -> str:
    ms = _ms(project)
    for it in ms.explicit(item):
        if xml_unescape(it.include).lower() == xml_unescape(include).lower():
            return it.metadata.get(name, default)
    return default


def remove_metadata(project, item: str, include: str, name: str) -> bool:
    ms = _ms(project)
    span = ms.find_element(item, include)
    if span is None:
        return False
    text = ms.file.text
    el = text[span[0]:span[1]]
    head_end = el.find(">")
    new = el
    m = re.search(rf"\s+{name}\s*=\s*(['\"]).*?\1", el[:head_end])
    if m:
        new = el[:m.start()] + el[m.end():]
    else:
        m = re.search(rf"\r?\n[ \t]*<{name}>.*?</{name}\s*>|<{name}>.*?</{name}\s*>|<{name}\s*/>", el, re.S)
        if not m:
            return False
        new = el[:m.start()] + el[m.end():]
        if re.fullmatch(rf"<{item}\b[^>]*>\s*</{item}\s*>", new, re.S):     # nothing left: self-closing
            new = re.sub(rf">\s*</{item}\s*>$", " />", new).replace("  />", " />")
    ms.file.text = text[:span[0]] + new + text[span[1]:]
    ms.parse()
    return True


def set_metadata(project, item: str, include: str, name: str, value: str | None) -> bool:
    """Write (or with value None / '' remove) one metadata of a reference item."""
    ms = _ms(project)
    cur = get_metadata(ms, item, include, name, None)
    if value in (None, ""):
        return remove_metadata(ms, item, include, name) if cur is not None else False
    if cur == value:
        return False
    return ms.set_metadata(item, include, name, value)


def rename_include(project, item: str, include: str, new_include: str) -> bool:
    """Change the Include of one item (e.g. a simple name -> the full assembly identity)."""
    ms = _ms(project)
    span = ms.find_element(item, include)
    if span is None or include == new_include:
        return False
    text = ms.file.text
    el = text[span[0]:span[1]]
    new = re.sub(r"(\bInclude\s*=\s*)(['\"]).*?\2", lambda m: f'{m.group(1)}"{xml_escape(new_include)}"', el, 1)
    ms.file.text = text[:span[0]] + new + text[span[1]:]
    ms.parse()
    return True


def full_identity(path, arch: str = "MSIL") -> str:
    """'Name, Version=1.0.0.0, Culture=neutral[, PublicKeyToken=..], processorArchitecture=MSIL' (as VS writes)."""
    from .metadata import assembly_identity
    i = assembly_identity(path)
    tok = f", PublicKeyToken={i['token']}" if i.get("token") else ""
    return f"{i['name']}, Version={i['version']}, Culture={i.get('culture') or 'neutral'}{tok}, " \
           f"processorArchitecture={arch}"


def set_bool(project, item: str, include: str, name: str, value: bool | None) -> bool:
    return set_metadata(project, item, include, name, None if value is None else ("True" if value else "False"))


# ---------------------------------------------------------------- Add As Link
def add_as_link(project, path, rel_dir: str = "") -> str:
    """Include a file that stays where it is (Compile/None Include="..\\x" with Link metadata)."""
    ms = _ms(project)
    p = Path(path).resolve()
    try:
        inside = p.relative_to(ms.folder).as_posix()
    except ValueError:
        inside = ""
    if inside:                      # VS: a file inside the project cone is simply added
        return ""
    try:
        rel = os.path.relpath(p, ms.folder)
    except ValueError:
        rel = str(p)
    link = (rel_dir.strip("/") + "/" if rel_dir.strip("/") else "") + p.name
    low = p.name.lower()
    if low.endswith(ms.code_ext):
        kind = "Compile"
    elif low.endswith(".resx"):
        kind = "EmbeddedResource"
    elif low.endswith((".xaml",)) and ms.prop("UseWPF").lower() == "true":
        kind = "Page"
    else:
        kind = "None"
    md = {"Link": ms_path(link)}
    if ms.language == "F#" and kind == "Compile":
        ok = ms._add_fsharp_compile(norm_rel(rel))
        if ok:
            ms.set_metadata("Compile", ms_path(rel), "Link", ms_path(link))
        return ms_path(rel)
    ms.add_item(kind, ms_path(rel), md)
    return ms_path(rel)


# ---------------------------------------------------------------- save + notify
def retry_io(fn, *args, tries: int = 25, delay: float = 0.12):
    """Run *fn* again while Windows reports the file busy (a language server / MSBuild reading it)."""
    import time
    for i in range(tries):
        try:
            return fn(*args)
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(delay)


def commit(win, project) -> None:
    """Save the project file, re-read it, refresh the tree and tell the C# language server."""
    ms = _ms(project)
    retry_io(ms.save)
    try:
        project.reload()
    except Exception:  # noqa: BLE001
        pass
    if win is not None:
        try:
            from ...foreign import vs_ui
            vs_ui._refresh(win)
        except Exception:  # noqa: BLE001
            pass
        try:
            from .lsp_reload import project_file_changed
            project_file_changed(win, ms.path)
        except Exception:  # noqa: BLE001
            pass


__all__ = ["RefInfo", "references", "find", "add_framework_assembly", "remove_assembly", "browse_reference_check",
           "add_browse_reference", "add_native_copy", "add_com_reference", "remove_com_reference",
           "add_framework_reference", "remove_framework_reference", "shared_imports", "add_shared_import",
           "remove_shared_import", "get_metadata", "set_metadata", "set_bool", "remove_metadata", "add_as_link",
           "rename_include", "full_identity", "retry_io",
           "commit", "BrowseError", "xml_unescape"]
