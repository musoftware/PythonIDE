"""What the Reference Manager can offer, and where a reference lives on disk.

* .NET Framework reference assemblies (``Reference Assemblies\\Microsoft\\Framework\\.NETFramework\\vX``,
  from ``RedistList\\FrameworkList.xml`` like Visual Studio, or the Microsoft.NETFramework.ReferenceAssemblies
  NuGet package in the user's NuGet cache)
* Extensions: the folders registered under ``AssemblyFoldersEx`` (HKLM/HKCU, 32/64-bit views)
* Shared frameworks for SDK-style projects (``FrameworkReference``) and their reference packs
* COM type libraries registered under ``HKEY_CLASSES_ROOT\\TypeLib``
* resolve_reference_path(): the file behind a Reference / COMReference / FrameworkReference item
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

PF86 = Path(os.environ.get("ProgramFiles(x86)") or os.environ.get("ProgramFiles") or r"C:\Program Files (x86)")
REF_ROOT = PF86 / "Reference Assemblies" / "Microsoft" / "Framework" / ".NETFramework"

SHARED_FRAMEWORKS = [
    ("Microsoft.NETCore.App", ".NET runtime (always referenced by Microsoft.NET.Sdk)", "Microsoft.NETCore.App.Ref"),
    ("Microsoft.WindowsDesktop.App", "Windows Desktop: Windows Forms + WPF (needs a -windows target framework)",
     "Microsoft.WindowsDesktop.App.Ref"),
    ("Microsoft.WindowsDesktop.App.WindowsForms", "Windows Forms only (needs a -windows target framework)",
     "Microsoft.WindowsDesktop.App.Ref"),
    ("Microsoft.WindowsDesktop.App.WPF", "WPF only (needs a -windows target framework)",
     "Microsoft.WindowsDesktop.App.Ref"),
    ("Microsoft.AspNetCore.App", "ASP.NET Core (implicit in Microsoft.NET.Sdk.Web)", "Microsoft.AspNetCore.App.Ref"),
]


@dataclass
class AsmEntry:
    name: str
    version: str
    path: str
    source: str = ""            # "Framework" / "Extensions" / folder label


@dataclass
class TypeLibEntry:
    name: str                   # description shown by VS ("Microsoft Scripting Runtime")
    guid: str                   # without braces, lower case
    major: int
    minor: int
    lcid: int
    path: str
    version_text: str           # "1.0"
    lib_name: str = ""          # the type library's own name (COMReference Include, e.g. "Scripting")


# ---------------------------------------------------------------- .NET Framework
def netfx_version(tfv: str) -> str:
    """'v4.8' / 'net48' / 'net472' -> 'v4.8' / 'v4.7.2'."""
    t = (tfv or "").strip()
    if t.lower().startswith("v"):
        return t
    m = re.fullmatch(r"net(\d)(\d)(\d)?", t.lower())
    if m:
        return "v" + ".".join(x for x in m.groups() if x)
    return "v4.8"


def netfx_folder(version: str) -> Path | None:
    """The reference assemblies of a .NET Framework version (installed targeting pack or NuGet cache)."""
    v = netfx_version(version)
    d = REF_ROOT / v
    if (d / "mscorlib.dll").is_file():
        return d
    pkg = "microsoft.netframework.referenceassemblies.net" + v.lstrip("v").replace(".", "")
    root = Path(os.environ.get("NUGET_PACKAGES") or Path.home() / ".nuget" / "packages") / pkg
    if root.is_dir():
        for ver in sorted(root.iterdir(), key=lambda p: _vkey(p.name), reverse=True):
            cand = ver / "build" / ".NETFramework" / v
            if (cand / "mscorlib.dll").is_file():
                return cand
    return None


def installed_netfx_versions() -> list[str]:
    if not REF_ROOT.is_dir():
        return []
    return sorted((p.name for p in REF_ROOT.iterdir() if (p / "mscorlib.dll").is_file()), key=_vkey)


def framework_assemblies(version: str) -> list[AsmEntry]:
    """Assemblies of the Framework tab (FrameworkList.xml order like VS; folder scan as fallback)."""
    d = netfx_folder(version)
    if d is None:
        return []
    out: dict[str, AsmEntry] = {}
    fl = d / "RedistList" / "FrameworkList.xml"
    if fl.is_file():
        try:
            import xml.etree.ElementTree as ET
            for f in ET.parse(fl).getroot().iter("File"):
                name = f.get("AssemblyName") or ""
                if not name:
                    continue
                p = d / f"{name}.dll"
                if p.is_file():
                    out[name.lower()] = AsmEntry(name, f.get("Version", ""), str(p), "Framework")
        except Exception:  # noqa: BLE001 - fall back to the folder
            out = {}
    if not out:
        from .metadata import NotManaged, read_assembly
        for p in sorted(d.glob("*.dll")):
            try:
                a = read_assembly(p)
            except (NotManaged, OSError):
                continue
            out[a.name.lower()] = AsmEntry(a.name, a.version, str(p), "Framework")
    return sorted(out.values(), key=lambda e: e.name.lower())


# ---------------------------------------------------------------- Extensions (AssemblyFoldersEx)
def assembly_folders_ex() -> list[tuple[str, str]]:
    """(label, folder) of every registered AssemblyFoldersEx / AssemblyFolders entry."""
    try:
        import winreg
    except ImportError:
        return []
    keys = [r"SOFTWARE\Microsoft\.NETFramework\v4.0.30319\AssemblyFoldersEx",
            r"SOFTWARE\Microsoft\.NETFramework\v2.0.50727\AssemblyFoldersEx",
            r"SOFTWARE\Microsoft\.NETFramework\AssemblyFolders"]
    seen: dict[str, tuple[str, str]] = {}
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            for k in keys:
                try:
                    h = winreg.OpenKey(hive, k, 0, winreg.KEY_READ | view)
                except OSError:
                    continue
                with h:
                    i = 0
                    while True:
                        try:
                            sub = winreg.EnumKey(h, i)
                        except OSError:
                            break
                        i += 1
                        try:
                            with winreg.OpenKey(h, sub) as s:
                                folder = winreg.QueryValue(s, None) or ""
                        except OSError:
                            continue
                        folder = os.path.expandvars(folder.strip().strip('"'))
                        if folder and Path(folder).is_dir():
                            seen.setdefault(os.path.normcase(folder), (sub, folder))
    return sorted(seen.values(), key=lambda x: x[0].lower())


def extension_assemblies(limit: int = 4000) -> list[AsmEntry]:
    from .metadata import is_managed
    out: dict[str, AsmEntry] = {}
    for label, folder in assembly_folders_ex():
        try:
            dlls = sorted(Path(folder).glob("*.dll"))
        except OSError:
            continue
        for p in dlls:
            if len(out) >= limit:
                break
            key = p.stem.lower()
            if key in out or not is_managed(p):
                continue
            out[key] = AsmEntry(p.stem, "", str(p), label)       # version read when shown (lazy)
    return sorted(out.values(), key=lambda e: e.name.lower())


def _file_version(p: Path) -> str:
    try:
        from .metadata import read_assembly
        return read_assembly(p).version
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------- SDK shared frameworks / ref packs
def dotnet_root() -> Path | None:
    exe = shutil.which("dotnet")
    if exe:
        return Path(os.path.realpath(exe)).parent
    d = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "dotnet"
    return d if d.is_dir() else None


def ref_pack_folder(pack: str, tfm: str) -> Path | None:
    """packs\\<pack>\\<newest matching version>\\ref\\<netX.Y> for an SDK target framework."""
    root = dotnet_root()
    if root is None:
        return None
    m = re.match(r"net(\d+)\.(\d+)", tfm or "")
    want = f"net{m.group(1)}.{m.group(2)}" if m else ""
    base = root / "packs" / pack
    if not base.is_dir():
        return None
    best = None
    for ver in sorted(base.iterdir(), key=lambda p: _vkey(p.name), reverse=True):
        refdir = ver / "ref"
        if not refdir.is_dir():
            continue
        cands = [want] if want else sorted((d.name for d in refdir.iterdir()), reverse=True)
        for c in cands:
            if c and (refdir / c).is_dir():
                return refdir / c
        if best is None and not want:
            best = refdir
    return best


def shared_framework_assemblies(name: str, tfm: str) -> list[AsmEntry]:
    pack = next((p for n, _d, p in SHARED_FRAMEWORKS if n == name), name + ".Ref")
    d = ref_pack_folder(pack, tfm)
    if d is None:
        return []
    return [AsmEntry(p.stem, "", str(p), name) for p in sorted(d.glob("*.dll"))]


def implicit_frameworks(ms) -> list[str]:
    """Shared frameworks an SDK project gets without a FrameworkReference (what VS lists under Frameworks)."""
    names = ["Microsoft.NETCore.App"]
    if ms.prop("UseWindowsForms").lower() == "true" or ms.prop("UseWPF").lower() == "true":
        names.append("Microsoft.WindowsDesktop.App")
    if "Web" in (ms.sdk or "") or "Razor" in (ms.sdk or ""):
        names.append("Microsoft.AspNetCore.App")
    for it in ms.explicit("FrameworkReference"):
        n = it.include
        if n not in names:
            names.append(n)
    return names


# ---------------------------------------------------------------- COM type libraries
def com_type_libraries() -> list[TypeLibEntry]:
    """Every registered (not hidden) type library, newest version per GUID first like VS's COM tab."""
    try:
        import winreg
    except ImportError:
        return []
    out: list[TypeLibEntry] = []
    try:
        root = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "TypeLib")
    except OSError:
        return []
    with root:
        i = 0
        while True:
            try:
                guid = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            try:
                gk = winreg.OpenKey(root, guid)
            except OSError:
                continue
            with gk:
                j = 0
                while True:
                    try:
                        ver = winreg.EnumKey(gk, j)
                    except OSError:
                        break
                    j += 1
                    entry = _typelib_version(winreg, gk, guid, ver)
                    if entry is not None:
                        out.append(entry)
    out.sort(key=lambda e: (e.name.lower(), -e.major, -e.minor))
    return out


def _typelib_version(winreg, gk, guid: str, ver: str) -> TypeLibEntry | None:
    try:
        vk = winreg.OpenKey(gk, ver)
    except OSError:
        return None
    with vk:
        try:
            desc = winreg.QueryValue(vk, None) or ""
        except OSError:
            desc = ""
        try:
            with winreg.OpenKey(vk, "FLAGS") as fk:
                flags = int(winreg.QueryValue(fk, None) or "0", 16)
        except (OSError, ValueError):
            flags = 0
        if flags & 0x4 or flags & 0x1:                    # LIBFLAG_FHIDDEN / FRESTRICTED
            return None
        path, lcid = "", 0
        k = 0
        while True:
            try:
                sub = winreg.EnumKey(vk, k)
            except OSError:
                break
            k += 1
            if not re.fullmatch(r"[0-9a-fA-F]+", sub):
                continue
            for plat in ("win64", "win32", "arm64"):
                try:
                    with winreg.OpenKey(vk, f"{sub}\\{plat}") as pk:
                        path = winreg.QueryValue(pk, None) or ""
                except OSError:
                    continue
                if path:
                    lcid = int(sub, 16)
                    break
            if path:
                break
        if not path:
            return None
    parts = ver.split(".")
    try:
        major = int(parts[0], 16)
        minor = int(parts[1], 16) if len(parts) > 1 else 0
    except ValueError:
        return None
    path = os.path.expandvars(path.strip().strip('"'))
    return TypeLibEntry(desc or guid, guid.strip("{}").lower(), major, minor, lcid, path, f"{major}.{minor}")


def typelib_name(path: str) -> str:
    """The library name stored in a type library (ITypeLib::GetDocumentation(-1)), e.g. 'Scripting'."""
    if os.name != "nt" or not path:
        return ""
    try:
        import ctypes
        oleaut = ctypes.windll.oleaut32
        ptl = ctypes.c_void_p()
        # REGKIND_NONE; "file.dll\2" (a resource id) is understood by LoadTypeLibEx itself
        if oleaut.LoadTypeLibEx(ctypes.c_wchar_p(path), 2, ctypes.byref(ptl)) != 0 or not ptl:
            return ""
        vtbl = ctypes.cast(ptl, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        GetDoc = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p),
                                    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(vtbl[9])
        Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
        bstr = ctypes.c_void_p()
        name = ""
        if GetDoc(ptl, -1, ctypes.byref(bstr), None, None, None) == 0 and bstr:
            name = ctypes.wstring_at(bstr.value)
            oleaut.SysFreeString(bstr)
        Release(ptl)
        return name
    except Exception:  # noqa: BLE001
        return ""


def find_type_library(guid: str) -> TypeLibEntry | None:
    g = guid.strip("{}").lower()
    for e in com_type_libraries():
        if e.guid == g:
            return e
    return None


# ---------------------------------------------------------------- resolving a reference item
def resolve_reference_path(project, kind: str, include: str, metadata: dict | None = None) -> str:
    """Best guess of the file behind a reference (like VS's Path property)."""
    ms = getattr(project, "ms", project)
    md = metadata or {}
    from ..refs.edits import xml_unescape
    inc = xml_unescape(include)
    if kind == "Reference":
        hint = md.get("HintPath", "")
        if hint and "$(" not in hint:
            p = (ms.folder / xml_unescape(hint).replace("\\", "/")).resolve()
            if p.exists():
                return str(p)
        name = inc.split(",")[0].strip()
        if ms.is_netframework:
            d = netfx_folder(_tfv(ms))
            if d is not None:
                for cand in (d / f"{name}.dll", d / "Facades" / f"{name}.dll"):
                    if cand.is_file():
                        return str(cand)
        for tfm in ms.target_frameworks or [""]:
            for fw in implicit_frameworks(ms):
                for e in shared_framework_assemblies(fw, tfm):
                    if e.name.lower() == name.lower():
                        return e.path
        for _label, folder in assembly_folders_ex():
            cand = Path(folder) / f"{name}.dll"
            if cand.is_file():
                return str(cand)
        return hint
    if kind == "COMReference":
        g = md.get("Guid", "")
        e = find_type_library(g) if g else None
        return e.path if e else ""
    if kind == "FrameworkReference" or kind == "framework":
        tfm = (ms.target_frameworks or [""])[0]
        pack = next((p for n, _d, p in SHARED_FRAMEWORKS if n == inc), inc + ".Ref")
        d = ref_pack_folder(pack, tfm)
        return str(d) if d else ""
    if kind == "ProjectReference":
        return str((ms.folder / inc.replace("\\", "/")).resolve())
    return ""


def _tfv(ms) -> str:
    v = ms.prop("TargetFrameworkVersion")
    if v:
        return v
    tf = (ms.target_frameworks or ["net48"])[0]
    return netfx_version(tf)


def project_netfx_version(ms) -> str:
    return netfx_version(_tfv(ms))


def _vkey(s: str):
    return tuple(int(x) if x.isdigit() else 0 for x in re.split(r"[.\-]", s.lstrip("vV")))


__all__ = ["AsmEntry", "TypeLibEntry", "SHARED_FRAMEWORKS", "framework_assemblies", "extension_assemblies",
           "assembly_folders_ex", "netfx_folder", "installed_netfx_versions", "shared_framework_assemblies",
           "ref_pack_folder", "implicit_frameworks", "com_type_libraries", "typelib_name", "find_type_library",
           "resolve_reference_path", "project_netfx_version", "netfx_version"]
