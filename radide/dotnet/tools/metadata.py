"""A small ECMA-335 reader: the public type names of a managed assembly (TypeDef table only), and a type
index over the assemblies a project compiles against - used by the light bulb ("using System.Text;"),
Go To Definition into metadata and the decompiler. Pure Python, no .NET needed.

(The Object Browser's full reader with members lives in radide/dotnet/refs/metadata.py; this one only reads
names so a few hundred framework assemblies index in well under a second each.)"""
from __future__ import annotations

import json
import os
import re
import struct
from pathlib import Path

from . import sdk

PUBLIC = 1                       # TypeAttributes.Public (visibility mask 0x7)
_HEAP_STRING, _HEAP_GUID, _HEAP_BLOB = 1, 2, 4


def _sections(data: bytes):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise ValueError("not a PE file")
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    dd = opt + (96 if magic == 0x10B else 112)
    cli_rva, cli_size = struct.unpack_from("<II", data, dd + 14 * 8)
    secs = []
    s = opt + opt_size
    for i in range(nsec):
        vsize, va, rsize, rptr = struct.unpack_from("<IIII", data, s + i * 40 + 8)
        secs.append((va, max(vsize, rsize), rptr))
    return secs, cli_rva, cli_size


def _off(secs, rva: int) -> int:
    for va, size, ptr in secs:
        if va <= rva < va + size:
            return rva - va + ptr
    raise ValueError("RVA outside the sections")


def type_names(path) -> list[tuple[str, str, bool]]:
    """[(namespace, name, is_public)] of the top-level types (nested types and <Module> skipped)."""
    data = Path(path).read_bytes()
    secs, cli_rva, cli_size = _sections(data)
    if not cli_rva:
        raise ValueError("not a managed assembly")
    cli = _off(secs, cli_rva)
    md_rva = struct.unpack_from("<I", data, cli + 8)[0]
    md = _off(secs, md_rva)
    if struct.unpack_from("<I", data, md)[0] != 0x424A5342:
        raise ValueError("bad metadata signature")
    vlen = struct.unpack_from("<I", data, md + 12)[0]
    p = md + 16 + vlen
    nstreams = struct.unpack_from("<H", data, p + 2)[0]
    p += 4
    streams = {}
    for _ in range(nstreams):
        off, size = struct.unpack_from("<II", data, p)
        p += 8
        end = data.index(b"\0", p)
        name = data[p:end].decode("ascii", "replace")
        p = (end + 4) & ~3
        streams[name] = (md + off, size)
    tbl = streams.get("#~") or streams.get("#-")
    strings = streams.get("#Strings")
    if tbl is None or strings is None:
        raise ValueError("no metadata tables")
    t = tbl[0]
    heap = data[t + 6]
    valid = struct.unpack_from("<Q", data, t + 8)[0]
    q = t + 24
    rows = [0] * 64
    for i in range(64):
        if valid >> i & 1:
            rows[i] = struct.unpack_from("<I", data, q)[0]
            q += 4
    if heap & 0x40:                       # extra data (uncompressed #- streams)
        q += 4
    si = 4 if heap & _HEAP_STRING else 2
    gi = 4 if heap & _HEAP_GUID else 2

    def idx(table):
        return 4 if rows[table] >= 0x10000 else 2

    def coded(tables, bits):
        return 4 if max(rows[x] for x in tables) >= (1 << (16 - bits)) else 2
    module_row = 2 + si + gi * 3
    typeref_row = coded((0x00, 0x1A, 0x23, 0x01), 2) + si * 2
    typedef_row = 4 + si * 2 + coded((0x02, 0x01, 0x1B), 2) + idx(0x04) + idx(0x06)
    q += rows[0] * module_row + rows[1] * typeref_row
    sbase = strings[0]

    def s(i):
        a = sbase + i
        return data[a:data.index(b"\0", a)].decode("utf-8", "replace")

    def rd(pos, n):
        return struct.unpack_from("<I" if n == 4 else "<H", data, pos)[0]
    nested = set()
    if rows[0x29]:                        # NestedClass: skip nested types
        nc_off = q + rows[2] * typedef_row
        # tables 0x03..0x28 between TypeDef and NestedClass have to be skipped: compute their sizes
        nc_off = _skip_to_nested(data, nc_off, rows, si, gi, 4 if heap & _HEAP_BLOB else 2, idx, coded)
        if nc_off is not None:
            n = idx(0x02)
            for r in range(rows[0x29]):
                nested.add(rd(nc_off + r * n * 2, n))
    out = []
    for r in range(rows[2]):
        base = q + r * typedef_row
        flags = rd(base, 4)
        name = s(rd(base + 4, si))
        ns = s(rd(base + 4 + si, si))
        if r + 1 in nested or name == "<Module>" or name.startswith("<"):
            continue
        out.append((ns, name, (flags & 7) == PUBLIC))
    return out


def _skip_to_nested(data, off, rows, si, gi, bi, idx, coded):
    """Byte offset of the NestedClass table (0x29), given the offset right after TypeDef (0x02)."""
    hdc = coded((0x04, 0x08, 0x17), 2)              # HasConstant
    hca = coded((0x06, 0x04, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x00, 0x0E, 0x17, 0x14, 0x11, 0x1A, 0x1B, 0x20, 0x23,
                 0x26, 0x27, 0x28, 0x2A, 0x2C, 0x2B), 5)  # HasCustomAttribute
    hfm = coded((0x04, 0x08), 1)
    hds = coded((0x02, 0x06, 0x20), 2)
    mrp = coded((0x02, 0x1A, 0x01, 0x06, 0x1B), 3)
    hs = coded((0x14, 0x17), 1)
    mdo = coded((0x06, 0x0A), 1)
    mf = coded((0x04, 0x06), 1)
    impl = coded((0x26, 0x23, 0x27), 2)
    cat = coded((0x06, 0x0A), 3)
    rs = coded((0x00, 0x1A, 0x23, 0x01), 2)
    tdor = coded((0x02, 0x01, 0x1B), 2)
    sizes = {
        0x03: idx(0x04),                             # FieldPtr
        0x04: 2 + si + bi,                           # Field
        0x05: idx(0x06),                             # MethodPtr
        0x06: 4 + 2 + 2 + si + bi + idx(0x08),       # MethodDef
        0x07: idx(0x08),                             # ParamPtr
        0x08: 2 + 2 + si,                            # Param
        0x09: idx(0x02) + tdor,                      # InterfaceImpl
        0x0A: mrp + si + bi,                         # MemberRef
        0x0B: 2 + hdc + bi,                          # Constant
        0x0C: hca + cat + bi,                        # CustomAttribute
        0x0D: hfm + bi,                              # FieldMarshal
        0x0E: 2 + hds + bi,                          # DeclSecurity
        0x0F: 2 + 4 + idx(0x02),                     # ClassLayout
        0x10: 4 + idx(0x04),                         # FieldLayout
        0x11: bi,                                    # StandAloneSig
        0x12: idx(0x02) + idx(0x14),                 # EventMap
        0x13: idx(0x14),                             # EventPtr
        0x14: 2 + si + tdor,                         # Event
        0x15: idx(0x02) + idx(0x17),                 # PropertyMap
        0x16: idx(0x17),                             # PropertyPtr
        0x17: 2 + si + bi,                           # Property
        0x18: 2 + idx(0x06) + hs,                    # MethodSemantics
        0x19: idx(0x02) + mdo * 2,                   # MethodImpl
        0x1A: si,                                    # ModuleRef
        0x1B: bi,                                    # TypeSpec
        0x1C: 2 + mf + si + idx(0x1A),               # ImplMap
        0x1D: 4 + idx(0x04),                         # FieldRVA
        0x1E: 8,                                     # EncLog
        0x1F: 4,                                     # EncMap
        0x20: 4 + 4,                                 # Assembly (HashAlgId + ...) - fixed below
        0x21: 4,                                     # AssemblyProcessor
        0x22: 12,                                    # AssemblyOS
        0x23: 2 * 4 + 4 + bi + si + si + bi,         # AssemblyRef
        0x24: 4 + idx(0x23),                         # AssemblyRefProcessor
        0x25: 12 + idx(0x23),                        # AssemblyRefOS
        0x26: 4 + si + bi,                           # File
        0x27: 4 + 4 + si + si + impl,                # ExportedType
        0x28: 4 + 4 + si + impl,                     # ManifestResource
    }
    sizes[0x20] = 4 + 2 * 4 + 4 + bi + si + si       # Assembly: HashAlgId, 4 x version, Flags, PublicKey, Name, Culture
    _ = rs, gi
    for t in range(0x03, 0x29):
        off += rows[t] * sizes[t]
    return off if off < len(data) else None


# ============================================================================ type index
class TypeIndex:
    """simple name -> [(namespace, assembly path)] over a set of assemblies (cached on disk per assembly)."""

    def __init__(self):
        self.by_name: dict[str, list[tuple[str, str]]] = {}
        self.raw: dict[tuple[str, str], list[str]] = {}       # (namespace, simple name) -> metadata names
        self.assemblies: list[str] = []

    def add_assembly(self, path) -> int:
        path = str(path)
        names = _cached_names(path)
        for ns, name, public in names:
            if not public:
                continue
            simple = name.split("`")[0]
            self.by_name.setdefault(simple, []).append((ns, path))
            raws = self.raw.setdefault((ns, simple), [])
            if name not in raws:
                raws.append(name)
        self.assemblies.append(path)
        return len(names)

    def lookup(self, simple: str) -> list[tuple[str, str]]:
        """[(namespace, assembly)] - distinct namespaces first-found wins."""
        seen, out = set(), []
        for ns, asm in self.by_name.get(simple.split("`")[0].split("<")[0], []):
            if ns not in seen:
                seen.add(ns)
                out.append((ns, asm))
        return out

    def raw_name(self, ns: str, simple: str, generic: bool = False) -> str:
        """Metadata name ('List`1') of a simple name; *generic* prefers the generic definition."""
        raws = self.raw.get((ns, simple.split("`")[0])) or [simple]
        gen = [r for r in raws if "`" in r]
        plain = [r for r in raws if "`" not in r]
        return (gen or plain)[0] if generic else (plain or gen)[0]

    def find_type(self, full_name: str) -> str | None:
        """Assembly that defines *full_name* (Namespace.Type, generic arity optional)."""
        ns, _, name = full_name.rpartition(".")
        for n2, asm in self.by_name.get(name.split("`")[0], []):
            if n2 == ns:
                return asm
        return None


_MEM: dict[str, list] = {}


def _cached_names(path: str) -> list:
    try:
        st = os.stat(path)
    except OSError:
        return []
    key = f"{path}|{st.st_size}|{int(st.st_mtime)}"
    if key in _MEM:
        return _MEM[key]
    f = sdk.cache_dir("dotnet-typeindex") / (sdk.short_hash(key) + ".json")
    names = None
    if f.is_file():
        try:
            names = [tuple(x) for x in json.loads(f.read_text(encoding="utf-8"))]
        except (OSError, ValueError):
            names = None
    if names is None:
        try:
            names = type_names(path)
        except (OSError, ValueError, struct.error, IndexError):
            names = []
        try:
            f.write_text(json.dumps(names), encoding="utf-8")
        except OSError:
            pass
    _MEM[key] = names
    return names


def _major(tf: str) -> int:
    m = re.match(r"net(?:coreapp)?(\d+)\.", tf or "")
    return int(m.group(1)) if m else 0


def shared_framework_dirs(tf: str = "", windows: bool = False, web: bool = False) -> list[Path]:
    """Implementation assemblies of the installed runtime matching *tf* (newest patch; newest major if none)."""
    dn = sdk.dotnet()
    if not dn:
        return []
    root = Path(dn).resolve().parent / "shared"
    want = _major(tf)
    out = []
    names = ["Microsoft.NETCore.App"] + (["Microsoft.WindowsDesktop.App"] if windows else []) + \
        (["Microsoft.AspNetCore.App"] if web else [])
    for fw in names:
        d = root / fw
        if not d.is_dir():
            continue
        vers = []
        for v in d.iterdir():
            m = re.match(r"(\d+)\.(\d+)\.(\d+)", v.name)
            if m and v.is_dir():
                vers.append((tuple(int(x) for x in m.groups()), v))
        if not vers:
            continue
        vers.sort()
        pick = [v for k, v in vers if k[0] == want] if want else []
        out.append((pick or [vers[-1][1]])[-1])
    return out


def netfx_dir() -> Path | None:
    for d in (Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET" / "Framework64" / "v4.0.30319",
              Path(os.environ.get("WINDIR", r"C:\Windows")) / "Microsoft.NET" / "Framework" / "v4.0.30319"):
        if d.is_dir():
            return d
    return None


def package_assemblies(project: Path) -> list[Path]:
    """Compile-time assemblies of the project's NuGet packages (obj/project.assets.json)."""
    assets = Path(project).parent / "obj" / "project.assets.json"
    if not assets.is_file():
        return []
    try:
        d = json.loads(assets.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    roots = [Path(p) for p in (d.get("packageFolders") or {})]
    libs = d.get("libraries") or {}
    out = []
    for _tfm, targets in (d.get("targets") or {}).items():
        for key, info in targets.items():
            if info.get("type") != "package":
                continue
            lib = libs.get(key) or {}
            for rel in (info.get("compile") or {}):
                if not rel.lower().endswith(".dll"):
                    continue
                for r in roots:
                    p = r / lib.get("path", key.lower()) / rel
                    if p.is_file():
                        out.append(p)
                        break
        break                                         # the first target framework is enough
    return out


def project_index(project: Path | None, tf: str = "") -> TypeIndex:
    """The types a project can see: its runtime's shared framework(s), its packages and its own bin output."""
    idx = TypeIndex()
    text = sdk.text(project) if project else ""
    if not tf:
        m = re.search(r"<TargetFrameworks?>([^<;]+)", text)
        tf = m.group(1).strip() if m else ""
    windows = bool(re.search(r"<Use(WindowsForms|WPF)>\s*true", text, re.I))
    web = "Microsoft.NET.Sdk.Web" in text or "Microsoft.NET.Sdk.Razor" in text
    dirs = []
    if tf.startswith("net4") or re.search(r"<TargetFrameworkVersion>v4", text):
        d = netfx_dir()
        dirs = [d] if d else []
    else:
        dirs = shared_framework_dirs(tf, windows, web)
    for d in dirs:
        for f in sorted(d.glob("*.dll")):
            idx.add_assembly(f)
    if project:
        for f in package_assemblies(project):
            idx.add_assembly(f)
    return idx


__all__ = ["type_names", "TypeIndex", "project_index", "shared_framework_dirs", "package_assemblies", "netfx_dir"]
