"""A small ECMA-335 metadata reader (pure Python, no .NET needed).

Reads the CLI header of a PE file and the ``#~`` tables of its metadata: the assembly identity, the
referenced assemblies, every type (namespace, nesting, kind, base type, generic parameters) and their
members (fields, methods with parameter names, properties, events) with C#-style signatures, plus the
XML documentation ids used by the ``.xml`` files Visual Studio shows in the Object Browser.

    asm = read_assembly(path)            # AssemblyMeta (cached per path + mtime)
    asm.name, asm.version, asm.types     # TypeMeta list
    t.members()                          # MemberMeta list (decoded on demand)
    is_managed(path)                     # quick CLI-header test (Browse validation)
"""
from __future__ import annotations

import os
import struct
import threading
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- table schema (ECMA-335 II.22)
# column kinds: 1/2/4 fixed size, "s" string heap, "g" guid heap, "b" blob heap,
# ("t", n) index into table n, ("c", name) coded index
CODED = {
    "TypeDefOrRef": (2, [0x02, 0x01, 0x1B]),
    "HasConstant": (2, [0x04, 0x08, 0x17]),
    "HasCustomAttribute": (5, [0x06, 0x04, 0x01, 0x02, 0x08, 0x09, 0x0A, 0x00, 0x0E, 0x17, 0x14, 0x11, 0x1A,
                               0x1B, 0x20, 0x23, 0x26, 0x27, 0x28, 0x2A, 0x2C, 0x2B]),
    "HasFieldMarshal": (1, [0x04, 0x08]),
    "HasDeclSecurity": (2, [0x02, 0x06, 0x20]),
    "MemberRefParent": (3, [0x02, 0x01, 0x1A, 0x06, 0x1B]),
    "HasSemantics": (1, [0x14, 0x17]),
    "MethodDefOrRef": (1, [0x06, 0x0A]),
    "MemberForwarded": (1, [0x04, 0x06]),
    "Implementation": (2, [0x26, 0x23, 0x27]),
    "CustomAttributeType": (3, [None, None, 0x06, 0x0A, None]),
    "ResolutionScope": (2, [0x00, 0x1A, 0x23, 0x01]),
    "TypeOrMethodDef": (1, [0x02, 0x06]),
}
T, C = "t", "c"
SCHEMA = {
    0x00: [2, "s", "g", "g", "g"],
    0x01: [(C, "ResolutionScope"), "s", "s"],
    0x02: [4, "s", "s", (C, "TypeDefOrRef"), (T, 0x04), (T, 0x06)],
    0x03: [(T, 0x04)],
    0x04: [2, "s", "b"],
    0x05: [(T, 0x06)],
    0x06: [4, 2, 2, "s", "b", (T, 0x08)],
    0x07: [(T, 0x08)],
    0x08: [2, 2, "s"],
    0x09: [(T, 0x02), (C, "TypeDefOrRef")],
    0x0A: [(C, "MemberRefParent"), "s", "b"],
    0x0B: [2, (C, "HasConstant"), "b"],
    0x0C: [(C, "HasCustomAttribute"), (C, "CustomAttributeType"), "b"],
    0x0D: [(C, "HasFieldMarshal"), "b"],
    0x0E: [2, (C, "HasDeclSecurity"), "b"],
    0x0F: [2, 4, (T, 0x02)],
    0x10: [4, (T, 0x04)],
    0x11: ["b"],
    0x12: [(T, 0x02), (T, 0x14)],
    0x13: [(T, 0x14)],
    0x14: [2, "s", (C, "TypeDefOrRef")],
    0x15: [(T, 0x02), (T, 0x17)],
    0x16: [(T, 0x17)],
    0x17: [2, "s", "b"],
    0x18: [2, (T, 0x06), (C, "HasSemantics")],
    0x19: [(T, 0x02), (C, "MethodDefOrRef"), (C, "MethodDefOrRef")],
    0x1A: ["s"],
    0x1B: ["b"],
    0x1C: [2, (C, "MemberForwarded"), "s", (T, 0x1A)],
    0x1D: [4, (T, 0x04)],
    0x1E: [4, 4],
    0x1F: [4],
    0x20: [4, 2, 2, 2, 2, 4, "b", "s", "s"],
    0x21: [4],
    0x22: [4, 4, 4],
    0x23: [2, 2, 2, 2, 4, "b", "s", "s", "b"],
    0x24: [4, (T, 0x23)],
    0x25: [4, 4, 4, (T, 0x23)],
    0x26: [4, "s", "b"],
    0x27: [4, 4, "s", "s", (C, "Implementation")],
    0x28: [4, 4, "s", (C, "Implementation")],
    0x29: [(T, 0x02), (T, 0x02)],
    0x2A: [2, 2, (C, "TypeOrMethodDef"), "s"],
    0x2B: [(C, "MethodDefOrRef"), "b"],
    0x2C: [(T, 0x2A), (C, "TypeDefOrRef")],
}

PRIMITIVES = {0x01: "void", 0x02: "bool", 0x03: "char", 0x04: "sbyte", 0x05: "byte", 0x06: "short",
              0x07: "ushort", 0x08: "int", 0x09: "uint", 0x0A: "long", 0x0B: "ulong", 0x0C: "float",
              0x0D: "double", 0x0E: "string", 0x16: "TypedReference", 0x18: "nint", 0x19: "nuint",
              0x1C: "object"}
DOC_PRIMITIVES = {0x01: "System.Void", 0x02: "System.Boolean", 0x03: "System.Char", 0x04: "System.SByte",
                  0x05: "System.Byte", 0x06: "System.Int16", 0x07: "System.UInt16", 0x08: "System.Int32",
                  0x09: "System.UInt32", 0x0A: "System.Int64", 0x0B: "System.UInt64", 0x0C: "System.Single",
                  0x0D: "System.Double", 0x0E: "System.String", 0x16: "System.TypedReference",
                  0x18: "System.IntPtr", 0x19: "System.UIntPtr", 0x1C: "System.Object"}
CS_ALIASES = {v: PRIMITIVES[k] for k, v in DOC_PRIMITIVES.items() if k not in (0x16, 0x18, 0x19)}

ACCESS = {1: "private", 2: "private protected", 3: "internal", 4: "protected", 5: "protected internal",
          6: "public"}
TYPE_ACCESS = {0: "internal", 1: "public", 2: "public", 3: "private", 4: "protected", 5: "internal",
               6: "private protected", 7: "protected internal"}


class NotManaged(ValueError):
    """The file is not a .NET assembly (no CLI header)."""


# ---------------------------------------------------------------- PE
def _pe_sections(data: bytes):
    if data[:2] != b"MZ":
        raise NotManaged("not a PE file (no MZ header)")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe:pe + 4] != b"PE\0\0":
        raise NotManaged("not a PE file")
    nsec, opt_size = struct.unpack_from("<H", data, pe + 6)[0], struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    dd = opt + (96 if magic == 0x10B else 112)
    ndirs = struct.unpack_from("<I", data, dd - 4)[0]
    sections = []
    so = opt + opt_size
    for i in range(nsec):
        o = so + 40 * i
        vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", data, o + 8)
        sections.append((va, max(vsize, rawsize), rawptr))
    cli = struct.unpack_from("<II", data, dd + 14 * 8) if ndirs > 14 else (0, 0)
    machine = struct.unpack_from("<H", data, pe + 4)[0]
    return sections, cli, magic, machine


def _rva(sections, rva: int) -> int:
    for va, size, raw in sections:
        if va <= rva < va + size:
            return rva - va + raw
    raise NotManaged(f"RVA 0x{rva:x} outside every section")


def is_managed(path) -> bool:
    """True when *path* is a PE file with a CLI (.NET) header."""
    try:
        with open(path, "rb") as fh:
            data = fh.read(4096)                  # the PE headers hold the CLI data directory
            if data[:2] != b"MZ":
                return False
            pe = struct.unpack_from("<I", data, 0x3C)[0]
            if pe + 512 > len(data):
                fh.seek(0)
                data = fh.read(pe + 4096)
        _s, cli, _m, _mc = _pe_sections(data)
        return cli[0] != 0 and cli[1] != 0
    except (OSError, NotManaged, struct.error, IndexError):
        return False


def pe_kind(path) -> str:
    """'managed', 'native', or '' (not a PE file)."""
    try:
        data = Path(path).read_bytes()
        _s, cli, _m, _mc = _pe_sections(data)
        return "managed" if cli[0] else "native"
    except (OSError, NotManaged, struct.error, IndexError):
        return ""


# ---------------------------------------------------------------- data classes
@dataclass
class AssemblyRefMeta:
    name: str
    version: str
    culture: str = ""
    token: str = ""


@dataclass
class MemberMeta:
    kind: str               # Method / Constructor / Property / Field / Event / Constant / EnumValue / Operator
    name: str
    signature: str          # C# declaration
    doc_id: str
    access: str = "public"
    is_static: bool = False
    owner: "TypeMeta | None" = field(default=None, repr=False)


@dataclass
class TypeMeta:
    asm: "AssemblyMeta" = field(repr=False)
    row: int
    namespace: str
    name: str               # without the `N arity suffix
    raw_name: str
    kind: str               # Class / Interface / Struct / Enum / Delegate / Module
    access: str
    flags: int
    base: str = ""
    generic: list[str] = field(default_factory=list)
    declaring: "TypeMeta | None" = field(default=None, repr=False)
    nested: list["TypeMeta"] = field(default_factory=list, repr=False)
    interfaces: list[str] = field(default_factory=list)
    base_short: str = ""
    _members: list | None = field(default=None, repr=False)

    @property
    def display(self) -> str:
        return self.name + (f"<{', '.join(self.generic)}>" if self.generic else "")

    @property
    def full_name(self) -> str:
        """Namespace.Outer+Inner (reflection spelling, with `N arities)."""
        if self.declaring is not None:
            return f"{self.declaring.full_name}+{self.raw_name}"
        return f"{self.namespace}.{self.raw_name}" if self.namespace else self.raw_name

    @property
    def doc_name(self) -> str:
        if self.declaring is not None:
            return f"{self.declaring.doc_name}.{self.raw_name}"
        return f"{self.namespace}.{self.raw_name}" if self.namespace else self.raw_name

    @property
    def doc_id(self) -> str:
        return "T:" + self.doc_name

    @property
    def cs_name(self) -> str:
        """Outer.Inner<T> as written in C# (with namespace)."""
        own = self.display
        if self.declaring is not None:
            return f"{self.declaring.cs_name}.{own}"
        return f"{self.namespace}.{own}" if self.namespace else own

    @property
    def is_public(self) -> bool:
        if (self.flags & 7) not in (1, 2, 4, 7):
            return False
        return self.declaring is None or self.declaring.is_public

    def declaration(self) -> str:
        mods = [self.access]
        f = self.flags
        if self.kind == "Class":
            if f & 0x80 and f & 0x100:
                mods.append("static")
            elif f & 0x80:
                mods.append("abstract")
            elif f & 0x100:
                mods.append("sealed")
        kw = {"Class": "class", "Interface": "interface", "Struct": "struct", "Enum": "enum",
              "Delegate": "delegate", "Module": "class"}[self.kind]
        text = " ".join(mods + [kw, self.display])
        if self.kind == "Delegate":
            inv = next((m for m in self.members(True) if m.name == "Invoke"), None)
            if inv is not None:
                sig = inv.signature.split(" Invoke", 1)
                ret = sig[0].split()[-1] if sig[0].split() else "void"
                text = " ".join(mods + ["delegate", ret, self.display + (sig[1] if len(sig) > 1 else "()")])
            return text
        bases = [b for b in ([self.base_short] if self.base and self.kind == "Class" else []) + self.interfaces
                 if b not in ("object", "System.Object")]
        if self.kind == "Enum":
            under = next((m for m in self.members(True) if m.kind == "Field" and m.name == "value__"), None)
            utype = under.signature.split()[0] if under is not None else "int"
            bases = [utype] if utype != "int" else []
        return text + (" : " + ", ".join(bases) if bases else "")

    def members(self, include_private: bool = False) -> list[MemberMeta]:
        if self._members is None:
            self._members = self.asm._read_members(self)
        if include_private:
            return list(self._members)
        return [m for m in self._members if m.access in ("public", "protected", "protected internal")]


@dataclass
class AssemblyMeta:
    path: Path
    name: str = ""
    version: str = "0.0.0.0"
    culture: str = ""
    public_key_token: str = ""
    runtime_version: str = ""
    machine: str = ""
    references: list[AssemblyRefMeta] = field(default_factory=list)
    types: list[TypeMeta] = field(default_factory=list)
    forwarded: list[str] = field(default_factory=list)
    target_framework: str = ""
    _r: "_Reader | None" = field(default=None, repr=False)

    @property
    def identity(self) -> str:
        return (f"{self.name}, Version={self.version}, Culture={self.culture or 'neutral'}, "
                f"PublicKeyToken={self.public_key_token or 'null'}")

    @property
    def strong_named(self) -> bool:
        return bool(self.public_key_token)

    def namespaces(self, public_only: bool = True) -> dict[str, list[TypeMeta]]:
        out: dict[str, list[TypeMeta]] = {}
        for t in self.types:
            if t.declaring is not None or t.name == "<Module>" or (public_only and not t.is_public):
                continue
            out.setdefault(t.namespace, []).append(t)
        for v in out.values():
            v.sort(key=lambda t: t.display.lower())
        return dict(sorted(out.items(), key=lambda kv: kv[0].lower()))

    def find_type(self, full: str) -> TypeMeta | None:
        full = full.replace("+", ".")
        for t in self.types:
            if t.doc_name == full or t.cs_name == full or t.full_name == full:
                return t
        return None

    def _read_members(self, t: TypeMeta) -> list[MemberMeta]:
        return self._r.members(t) if self._r is not None else []


# ---------------------------------------------------------------- reader
class _Reader:
    def __init__(self, data: bytes, path: Path):
        self.data = data
        self.path = path
        sections, cli, magic, machine = _pe_sections(data)
        if not cli[0]:
            raise NotManaged(f"{path.name} is not a .NET assembly (it has no CLI header)")
        self.machine = {0x14C: "x86", 0x8664: "x64", 0xAA64: "ARM64", 0x1C4: "ARM"}.get(machine, hex(machine))
        cli_off = _rva(sections, cli[0])
        md_rva, _md_size, flags = struct.unpack_from("<III", data, cli_off + 8)
        self.cli_flags = flags
        md = _rva(sections, md_rva)
        if struct.unpack_from("<I", data, md)[0] != 0x424A5342:
            raise NotManaged(f"{path.name}: bad metadata signature")
        vlen = struct.unpack_from("<I", data, md + 12)[0]
        self.runtime_version = data[md + 16: md + 16 + vlen].split(b"\0")[0].decode("ascii", "replace")
        p = md + 16 + vlen
        nstreams = struct.unpack_from("<H", data, p + 2)[0]
        p += 4
        self.streams: dict[str, tuple[int, int]] = {}
        for _ in range(nstreams):
            off, size = struct.unpack_from("<II", data, p)
            p += 8
            end = data.index(b"\0", p)
            name = data[p:end].decode("ascii", "replace")
            p = (end + 4) & ~3
            self.streams[name] = (md + off, size)
        self.strings = self.streams.get("#Strings", (0, 0))[0]
        self.blobs = self.streams.get("#Blob", (0, 0))[0]
        self.guids = self.streams.get("#GUID", (0, 0))[0]
        tbl = self.streams.get("#~") or self.streams.get("#-")
        if tbl is None:
            raise NotManaged(f"{path.name}: no metadata tables")
        self._tables(tbl[0])
        self._scache: dict[int, str] = {}

    # ----- heaps
    def s(self, off: int) -> str:
        v = self._scache.get(off)
        if v is None:
            start = self.strings + off
            end = self.data.index(b"\0", start)
            v = self.data[start:end].decode("utf-8", "replace")
            self._scache[off] = v
        return v

    def blob(self, off: int) -> bytes:
        p = self.blobs + off
        n, p = _cuint(self.data, p)
        return self.data[p:p + n]

    # ----- tables
    def _tables(self, p: int) -> None:
        d = self.data
        heap = d[p + 6]
        valid = struct.unpack_from("<Q", d, p + 8)[0]
        q = p + 24
        self.rows = [0] * 64
        for i in range(64):
            if valid >> i & 1:
                self.rows[i] = struct.unpack_from("<I", d, q)[0]
                q += 4
        if heap & 0x40:
            q += 4                                 # extra data (uncompressed #- streams)
        size = {"s": 4 if heap & 1 else 2, "g": 4 if heap & 2 else 2, "b": 4 if heap & 4 else 2}

        def coded(name):
            bits, tabs = CODED[name]
            mx = max((self.rows[t] for t in tabs if t is not None), default=0)
            return 2 if mx < (1 << (16 - bits)) else 4
        self.tables: dict[int, list[tuple]] = {}
        self._layout: dict[int, tuple] = {}
        for t in range(0x2D):
            n = self.rows[t]
            if not n:
                self.tables[t] = []
                continue
            cols = SCHEMA[t]
            widths = []
            for c in cols:
                if isinstance(c, int):
                    widths.append(c)
                elif isinstance(c, str):
                    widths.append(size[c])
                elif c[0] == T:
                    widths.append(2 if self.rows[c[1]] < 65536 else 4)
                else:
                    widths.append(coded(c[1]))
            fmt = "<" + "".join({1: "B", 2: "H", 4: "I"}[w] for w in widths)
            rsize = struct.calcsize(fmt)
            unpack = struct.Struct(fmt).unpack_from
            self.tables[t] = [unpack(d, q + i * rsize) for i in range(n)]
            q += rsize * n

    def decode(self, name: str, value: int) -> tuple[int | None, int]:
        bits, tabs = CODED[name]
        tag = value & ((1 << bits) - 1)
        return (tabs[tag] if tag < len(tabs) else None), value >> bits

    def row(self, table: int, index: int) -> tuple | None:
        rows = self.tables.get(table) or []
        return rows[index - 1] if 0 < index <= len(rows) else None

    # ----- assembly
    def assembly(self) -> AssemblyMeta:
        a = AssemblyMeta(self.path, _r=self)
        a.runtime_version, a.machine = self.runtime_version, self.machine
        if self.cli_flags & 0x2 and self.machine == "x86":
            a.machine = "x86 (32-bit required)"
        elif self.machine == "x86":
            a.machine = "MSIL (Any CPU)"
        ar = self.row(0x20, 1)
        if ar:
            a.version = f"{ar[1]}.{ar[2]}.{ar[3]}.{ar[4]}"
            a.name, a.culture = self.s(ar[7]), self.s(ar[8])
            pk = self.blob(ar[6])
            if pk:
                import hashlib
                a.public_key_token = hashlib.sha1(pk).digest()[-8:][::-1].hex()
        else:
            mod = self.row(0x00, 1)
            a.name = Path(self.s(mod[1])).stem if mod else self.path.stem
        for r in self.tables[0x23]:
            tok = self.blob(r[5])
            if len(tok) > 8:
                import hashlib
                tok = hashlib.sha1(tok).digest()[-8:][::-1]
            a.references.append(AssemblyRefMeta(self.s(r[6]), f"{r[0]}.{r[1]}.{r[2]}.{r[3]}", self.s(r[7]),
                                                tok.hex()))
        for r in self.tables[0x27]:
            ns, nm = self.s(r[3]), self.s(r[2])
            a.forwarded.append(f"{ns}.{nm}" if ns else nm)
        self._types(a)
        a.target_framework = self._target_framework()
        return a

    def _target_framework(self) -> str:
        for r in self.tables[0x0C]:
            parent_tab, parent = self.decode("HasCustomAttribute", r[0])
            if parent_tab != 0x20:
                continue
            ctor_tab, ctor = self.decode("CustomAttributeType", r[1])
            if ctor_tab != 0x0A:
                continue
            mr = self.row(0x0A, ctor)
            if not mr:
                continue
            ptab, pidx = self.decode("MemberRefParent", mr[0])
            if ptab != 0x01:
                continue
            tr = self.row(0x01, pidx)
            if tr and self.s(tr[1]) == "TargetFrameworkAttribute":
                b = self.blob(r[2])
                if len(b) > 3:
                    n, p = _cuint(b, 2)
                    return b[p:p + n].decode("utf-8", "replace")
        return ""

    def _types(self, a: AssemblyMeta) -> None:
        tds = self.tables[0x02]
        self.type_by_row: dict[int, TypeMeta] = {}
        gps: dict[tuple[int, int], list[tuple[int, str]]] = {}
        for g in self.tables[0x2A]:
            tab, idx = self.decode("TypeOrMethodDef", g[2])
            gps.setdefault((tab, idx), []).append((g[0], self.s(g[3])))
        self.generics = {k: [n for _num, n in sorted(v)] for k, v in gps.items()}
        for i, r in enumerate(tds, 1):
            raw, ns = self.s(r[1]), self.s(r[2])
            flags = r[0]
            gen = self.generics.get((0x02, i), [])
            name = raw.split("`", 1)[0]
            t = TypeMeta(a, i, ns, name, raw, "Class", TYPE_ACCESS.get(flags & 7, "internal"), flags, generic=gen)
            self.type_by_row[i] = t
            a.types.append(t)
        for nc in self.tables[0x29]:
            inner, outer = self.type_by_row.get(nc[0]), self.type_by_row.get(nc[1])
            if inner is not None and outer is not None:
                inner.declaring = outer
                inner.namespace = outer.namespace
                outer.nested.append(inner)
                if outer.generic and inner.generic[: len(outer.generic)] == outer.generic:
                    inner.generic = inner.generic[len(outer.generic):]      # C# shows only its own
        for i, r in enumerate(tds, 1):
            t = self.type_by_row[i]
            base = self.type_name(r[3], coded=True, ctx=t) if r[3] else ""
            t.base = base
            t.base_short = _short(base)
            if t.flags & 0x20:
                t.kind = "Interface"
            elif base in ("System.Enum",):
                t.kind = "Enum"
            elif base in ("System.ValueType",) and t.full_name != "System.Enum":
                t.kind = "Struct"
            elif base in ("System.MulticastDelegate",) and t.full_name != "System.MulticastDelegate":
                t.kind = "Delegate"
        for ii in self.tables[0x09]:
            t = self.type_by_row.get(ii[0])
            if t is not None:
                t.interfaces.append(_short(self.type_name(ii[1], coded=True, ctx=t)))

    # ----- type names
    def typeref_name(self, idx: int, doc: bool = False) -> str:
        r = self.row(0x01, idx)
        if not r:
            return "?"
        name = self.s(r[1])
        if not doc:
            name = name.split("`", 1)[0]
        tab, scope = self.decode("ResolutionScope", r[0])
        if tab == 0x01 and scope:
            return f"{self.typeref_name(scope, doc)}.{name}"
        ns = self.s(r[2])
        return f"{ns}.{name}" if ns else name

    def type_name(self, value: int, coded: bool = False, ctx: "TypeMeta | None" = None, doc: bool = False,
                  tab: int | None = None) -> str:
        if coded:
            tab, value = self.decode("TypeDefOrRef", value)
        if tab == 0x02:
            t = self.type_by_row.get(value)
            if t is None:
                return "?"
            if doc:
                return t.doc_name
            return t.cs_name if not t.generic else t.cs_name.split("<", 1)[0]
        if tab == 0x01:
            return self.typeref_name(value, doc)
        if tab == 0x1B:
            r = self.row(0x1B, value)
            if r:
                sig = self.blob(r[0])
                return self.sig_type(sig, 0, ctx, None, doc)[0]
        return "?"

    def sig_type(self, b: bytes, p: int, tctx: "TypeMeta | None", mgen: list[str] | None, doc: bool = False
                 ) -> tuple[str, int]:
        et = b[p]
        p += 1
        if et in PRIMITIVES:
            return (DOC_PRIMITIVES[et] if doc else PRIMITIVES[et]), p
        if et in (0x11, 0x12):
            v, p = _cuint(b, p)
            name = self.type_name(v, coded=True, ctx=tctx, doc=doc)
            return (name if doc else _short(name)), p
        if et == 0x0F:
            s, p = self.sig_type(b, p, tctx, mgen, doc)
            return s + "*", p
        if et == 0x10:
            s, p = self.sig_type(b, p, tctx, mgen, doc)
            return (s + "@" if doc else "ref " + s), p
        if et == 0x1D:
            s, p = self.sig_type(b, p, tctx, mgen, doc)
            return s + "[]", p
        if et == 0x14:
            s, p = self.sig_type(b, p, tctx, mgen, doc)
            rank, p = _cuint(b, p)
            nsz, p = _cuint(b, p)
            for _ in range(nsz):
                _v, p = _cuint(b, p)
            nlo, p = _cuint(b, p)
            for _ in range(nlo):
                _v, p = _cuint(b, p)
            return s + ("[" + ",".join(["0:"] * rank) + "]" if doc else "[" + "," * (rank - 1) + "]"), p
        if et == 0x15:
            p += 1                                     # class / valuetype
            v, p = _cuint(b, p)
            name = self.type_name(v, coded=True, ctx=tctx, doc=doc)
            n, p = _cuint(b, p)
            args = []
            for _ in range(n):
                s, p = self.sig_type(b, p, tctx, mgen, doc)
                args.append(s)
            if doc:
                return name.split("`", 1)[0] + "{" + ",".join(args) + "}", p
            short = _short(name)
            if short == "System.Nullable" or name == "System.Nullable":
                return args[0] + "?", p
            return short + "<" + ", ".join(args) + ">", p
        if et == 0x13:
            n, p = _cuint(b, p)
            if doc:
                return f"`{n}", p
            names = _all_generics(tctx)
            return (names[n] if n < len(names) else f"T{n}"), p
        if et == 0x1E:
            n, p = _cuint(b, p)
            if doc:
                return f"``{n}", p
            return ((mgen or [])[n] if n < len(mgen or []) else f"TM{n}"), p
        if et in (0x1F, 0x20):
            _v, p = _cuint(b, p)
            return self.sig_type(b, p, tctx, mgen, doc)
        if et == 0x45:
            return self.sig_type(b, p, tctx, mgen, doc)
        if et == 0x1B:
            return "delegate*", len(b)
        if et == 0x41:
            return self.sig_type(b, p, tctx, mgen, doc)
        return "?", len(b)

    def _skip_mods(self, b: bytes, p: int) -> tuple[int, bool]:
        is_ref = False
        while p < len(b) and b[p] in (0x1F, 0x20):
            p += 1
            _v, p = _cuint(b, p)
        return p, is_ref

    def method_sig(self, b: bytes, tctx, mgen, doc=False) -> tuple[str, list[str]]:
        p = 0
        conv = b[p]
        p += 1
        if conv & 0x10:
            _g, p = _cuint(b, p)
        n, p = _cuint(b, p)
        p, _ = self._skip_mods(b, p)
        ret, p = self.sig_type(b, p, tctx, mgen, doc) if p < len(b) else ("void", p)
        params = []
        for _ in range(n):
            if p >= len(b):
                break
            p, _ = self._skip_mods(b, p)
            if b[p] == 0x41:                 # sentinel (vararg)
                p += 1
            s, p = self.sig_type(b, p, tctx, mgen, doc)
            params.append(s)
        return ret, params

    # ----- members
    def members(self, t: TypeMeta) -> list[MemberMeta]:
        out: list[MemberMeta] = []
        tds = self.tables[0x02]
        r = tds[t.row - 1]
        nxt = tds[t.row] if t.row < len(tds) else None
        f0, f1 = r[4], (nxt[4] if nxt else len(self.tables[0x04]) + 1)
        m0, m1 = r[5], (nxt[5] if nxt else len(self.tables[0x06]) + 1)
        enum = t.kind == "Enum"
        for fi in range(f0, f1):
            fr = self.row(0x04, fi)
            if fr is None:
                continue
            flags, name = fr[0], self.s(fr[1])
            sig = self.blob(fr[2])
            p, _ = self._skip_mods(sig, 1)
            typ = self.sig_type(sig, p, t, None)[0] if len(sig) > 1 else "?"
            access = ACCESS.get(flags & 7, "private")
            static = bool(flags & 0x10)
            if enum and name == "value__":
                out.append(MemberMeta("Field", name, f"{typ} value__", "", "private", False, t))
                continue
            if flags & 0x40:
                kind = "EnumValue" if enum else "Constant"
                decl = name if enum else f"{access} const {typ} {name}"
            else:
                kind = "Field"
                mods = [access] + (["static"] if static else []) + (["readonly"] if flags & 0x20 else [])
                decl = " ".join(mods + [typ, name])
            out.append(MemberMeta(kind, name, decl, f"F:{t.doc_name}.{name}", access, static, t))
        semantics, sem_by_assoc = self._semantics()
        methods: dict[int, MemberMeta] = {}
        for mi in range(m0, m1):
            mr = self.row(0x06, mi)
            if mr is None:
                continue
            flags, name = mr[2], self.s(mr[3])
            mgen = self.generics.get((0x06, mi), [])
            sig = self.blob(mr[4])
            try:
                ret, ptypes = self.method_sig(sig, t, mgen)
                _r, dtypes = self.method_sig(sig, t, mgen, doc=True)
            except (IndexError, struct.error):
                ret, ptypes, dtypes = "?", [], []
            mrows = self.tables[0x06]
            pend = mrows[mi][5] if mi < len(mrows) else len(self.tables[0x08]) + 1     # next method's ParamList
            pnames = self._param_names(mr[5], pend, len(ptypes))
            access = ACCESS.get(flags & 7, "private")
            static = bool(flags & 0x10)
            params = ", ".join(f"{pt} {_ident(pn)}" for pt, pn in zip(ptypes, pnames))
            gen = f"<{', '.join(mgen)}>" if mgen else ""
            docparams = f"({','.join(dtypes)})" if dtypes else ""
            dname = name.replace(".", "#")
            doc = f"M:{t.doc_name}.{dname}" + (f"``{len(mgen)}" if mgen else "") + docparams
            mods = [access]
            if static:
                mods.append("static")
            if t.kind != "Interface":
                newslot, final = flags & 0x100, flags & 0x20
                if flags & 0x400:
                    mods.append("abstract" if newslot else "abstract override")
                elif flags & 0x40:                 # virtual
                    if newslot and not final:
                        mods.append("virtual")
                    elif not newslot:
                        mods.append("sealed override" if final else "override")
            if name in (".ctor", ".cctor"):
                decl = f"{' '.join(mods)} {t.name}({params})"
                kind = "Constructor"
                if name == ".cctor":
                    continue
            elif flags & 0x800 and name.startswith("op_"):
                kind = "Operator"
                op = OPERATORS.get(name, name)
                decl = f"{' '.join(mods)} {ret} operator {op}({params})" if not op.startswith(("implicit", "explicit")) \
                    else f"{' '.join(mods)} {op} operator {ret}({params})"
            else:
                kind = "Method"
                decl = f"{' '.join(mods)} {ret} {name}{gen}({params})"
            m = MemberMeta(kind, name, decl, doc, access, static, t)
            methods[mi] = m
            if mi not in semantics:
                out.append(m)
        # properties
        prop_rows = self._map_range(0x15, 0x17, t.row)
        for pi in prop_rows:
            pr = self.row(0x17, pi)
            if pr is None:
                continue
            name = self.s(pr[1])
            sig = self.blob(pr[2])
            try:
                ret, ptypes = self.method_sig(sig, t, None)
                _r, dtypes = self.method_sig(sig, t, None, doc=True)
            except (IndexError, struct.error):
                ret, ptypes, dtypes = "?", [], []
            acc = sem_by_assoc.get((0x17, pi), [])
            getter = next((methods.get(m) for s, m in acc if s & 0x2), None)
            setter = next((methods.get(m) for s, m in acc if s & 0x1), None)
            any_m = getter or setter
            access = _best_access([x.access for x in (getter, setter) if x])
            static = bool(any_m and any_m.is_static)
            parts = []
            if getter:
                parts.append("get;" if getter.access == access else f"{getter.access} get;")
            if setter:
                parts.append("set;" if setter.access == access else f"{setter.access} set;")
            label = name
            if ptypes:
                pn = self._accessor_param_names(getter, len(ptypes))
                label = "this[" + ", ".join(f"{a} {b}" for a, b in zip(ptypes, pn)) + "]"
            decl = f"{access}{' static' if static else ''} {ret} {label} {{ {' '.join(parts)} }}"
            doc = f"P:{t.doc_name}.{name}" + (f"({','.join(dtypes)})" if dtypes else "")
            out.append(MemberMeta("Property", name, decl, doc, access, static, t))
        for ei in self._map_range(0x12, 0x14, t.row):
            er = self.row(0x14, ei)
            if er is None:
                continue
            name = self.s(er[1])
            typ = _short(self.type_name(er[2], coded=True, ctx=t)) if er[2] else "?"
            acc = sem_by_assoc.get((0x14, ei), [])
            adder = next((methods.get(m) for s, m in acc if s & 0x8), None)
            access = adder.access if adder else "public"
            static = bool(adder and adder.is_static)
            decl = f"{access}{' static' if static else ''} event {typ} {name}"
            out.append(MemberMeta("Event", name, decl, f"E:{t.doc_name}.{name}", access, static, t))
        order = {"Constructor": 0, "Property": 1, "Method": 2, "Operator": 3, "Event": 4, "Field": 5,
                 "Constant": 6, "EnumValue": 7}
        if enum:
            return out
        return sorted(out, key=lambda m: (order.get(m.kind, 9), m.name.lower()))

    def _accessor_param_names(self, m: MemberMeta | None, n: int) -> list[str]:
        if m is None:
            return [f"arg{i}" for i in range(n)]
        sig = m.signature
        inside = sig[sig.find("(") + 1: sig.rfind(")")]
        names = [x.strip().split(" ")[-1] for x in inside.split(",") if x.strip()]
        return (names + [f"arg{i}" for i in range(n)])[:n]

    def _semantics(self):
        cached = getattr(self, "_sem", None)
        if cached is None:
            accessors: set[int] = set()
            by_assoc: dict[tuple[int, int], list[tuple[int, int]]] = {}
            for ms in self.tables[0x18]:
                accessors.add(ms[1])
                tab, idx = self.decode("HasSemantics", ms[2])
                by_assoc.setdefault((tab, idx), []).append((ms[0], ms[1]))
            cached = self._sem = (accessors, by_assoc)
        return cached

    def _map_range(self, map_tab: int, list_tab: int, type_row: int) -> range:
        maps = getattr(self, "_maps", None)
        if maps is None:
            maps = self._maps = {}
        m = maps.get(map_tab)
        if m is None:
            rows = self.tables[map_tab]
            m = maps[map_tab] = {}
            for i, r in enumerate(rows):
                end = rows[i + 1][1] if i + 1 < len(rows) else len(self.tables[list_tab]) + 1
                m[r[0]] = range(r[1], end)
        return m.get(type_row, range(0))

    def _param_names(self, start: int, end: int, n: int) -> list[str]:
        names = [f"arg{i}" for i in range(n)]
        for pi in range(start, end):
            pr = self.row(0x08, pi)
            if pr is None:
                break
            seq = pr[1]
            if 1 <= seq <= n:
                nm = self.s(pr[2])
                if nm:
                    names[seq - 1] = nm
        return names


OPERATORS = {"op_Addition": "+", "op_Subtraction": "-", "op_Multiply": "*", "op_Division": "/", "op_Modulus": "%",
             "op_Equality": "==", "op_Inequality": "!=", "op_LessThan": "<", "op_GreaterThan": ">",
             "op_LessThanOrEqual": "<=", "op_GreaterThanOrEqual": ">=", "op_UnaryNegation": "-",
             "op_UnaryPlus": "+", "op_LogicalNot": "!", "op_OnesComplement": "~", "op_Increment": "++",
             "op_Decrement": "--", "op_BitwiseAnd": "&", "op_BitwiseOr": "|", "op_ExclusiveOr": "^",
             "op_LeftShift": "<<", "op_RightShift": ">>", "op_True": "true", "op_False": "false",
             "op_Implicit": "implicit", "op_Explicit": "explicit"}


CS_KEYWORDS = set("""abstract as base bool break byte case catch char checked class const continue decimal default
delegate do double else enum event explicit extern false finally fixed float for foreach goto if implicit in int
interface internal is lock long namespace new null object operator out override params private protected public
readonly ref return sbyte sealed short sizeof stackalloc static string struct switch this throw true try typeof uint
ulong unchecked unsafe ushort using virtual void volatile while""".split())


def _ident(name: str) -> str:
    return "@" + name if name in CS_KEYWORDS else name


def _best_access(values: list[str]) -> str:
    rank = ["private", "private protected", "internal", "protected", "protected internal", "public"]
    return max(values, key=lambda v: rank.index(v) if v in rank else 0) if values else "public"


def _all_generics(t: "TypeMeta | None") -> list[str]:
    chain = []
    while t is not None:
        chain.append(t)
        t = t.declaring
    out: list[str] = []
    for x in reversed(chain):
        out += x.generic
    return out


def _short(name: str) -> str:
    """C# alias for BCL primitive names; other names keep their namespace off when it is System.*."""
    if name in CS_ALIASES:
        return CS_ALIASES[name]
    return name.rsplit(".", 1)[-1] if "." in name else name


def _cuint(b: bytes, p: int) -> tuple[int, int]:
    x = b[p]
    if x & 0x80 == 0:
        return x, p + 1
    if x & 0xC0 == 0x80:
        return ((x & 0x3F) << 8) | b[p + 1], p + 2
    return ((x & 0x1F) << 24) | (b[p + 1] << 16) | (b[p + 2] << 8) | b[p + 3], p + 4


# ---------------------------------------------------------------- cache + public API
_CACHE: dict[str, tuple[int, AssemblyMeta]] = {}
_LOCK = threading.Lock()


def read_assembly(path) -> AssemblyMeta:
    """Metadata of a .NET assembly (raises NotManaged for native DLLs / non-PE files)."""
    path = Path(path)
    key = os.path.normcase(str(path.resolve()))
    mtime = path.stat().st_mtime_ns
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and hit[0] == mtime:
            return hit[1]
    data = path.read_bytes()
    try:
        asm = _Reader(data, path).assembly()
    except (struct.error, IndexError) as e:
        raise NotManaged(f"{path.name}: unreadable metadata ({e})") from None
    with _LOCK:
        _CACHE[key] = (mtime, asm)
    return asm


def assembly_identity(path) -> dict:
    """{'name','version','culture','token','runtime','framework','machine'} or raises NotManaged."""
    a = read_assembly(path)
    return {"name": a.name, "version": a.version, "culture": a.culture or "neutral",
            "token": a.public_key_token, "runtime": a.runtime_version, "framework": a.target_framework,
            "machine": a.machine, "identity": a.identity}


# ---------------------------------------------------------------- XML documentation
_DOCS: dict[str, tuple[int, dict]] = {}


def xml_doc_file(asm_path) -> Path | None:
    p = Path(asm_path)
    for cand in (p.with_suffix(".xml"), p.parent / "en" / (p.stem + ".xml")):
        if cand.is_file():
            return cand
    return None


def load_docs(asm_path) -> dict[str, dict]:
    """doc id -> {'summary', 'returns', 'remarks', 'params': {name: text}} from the .xml next to the dll."""
    f = xml_doc_file(asm_path)
    if f is None:
        return {}
    key = os.path.normcase(str(f))
    mtime = f.stat().st_mtime_ns
    hit = _DOCS.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    import xml.etree.ElementTree as ET
    out: dict[str, dict] = {}
    try:
        root = ET.parse(f).getroot()
    except (ET.ParseError, OSError):
        return {}
    for m in root.iter("member"):
        name = m.get("name") or ""
        d = {"summary": _text(m.find("summary")), "returns": _text(m.find("returns")),
             "remarks": _text(m.find("remarks")),
             "params": {p.get("name", ""): _text(p) for p in m.findall("param")}}
        out[name] = d
    _DOCS[key] = (mtime, out)
    return out


def _text(el) -> str:
    if el is None:
        return ""
    parts = [el.text or ""]
    for c in el:
        tag = c.tag
        if tag in ("see", "seealso"):
            ref = c.get("cref") or c.get("langword") or c.get("href") or ""
            parts.append((c.text or ref.split(":", 1)[-1].rsplit(".", 1)[-1]))
        elif tag in ("paramref", "typeparamref"):
            parts.append(c.get("name", ""))
        else:
            parts.append(_text(c))
        parts.append(c.tail or "")
    return " ".join("".join(parts).split())


def doc_for(asm_path, doc_id: str) -> dict:
    docs = load_docs(asm_path)
    if doc_id in docs:
        return docs[doc_id]
    if "(" in doc_id:                      # tolerate small id spelling differences (generic args)
        head = doc_id.split("(", 1)[0]
        for k, v in docs.items():
            if k.split("(", 1)[0] == head:
                return v
    return {}


# ---------------------------------------------------------------- metadata as source
def metadata_as_source(t: TypeMeta) -> str:
    """A C# stub of *t* the way Visual Studio shows "[from metadata]" (signatures only)."""
    a = t.asm
    docs = load_docs(a.path)
    lines = [f"#region Assembly {a.identity}", f"// {a.path}", "#endregion", ""]
    ind = ""
    if t.namespace:
        lines += [f"namespace {t.namespace}", "{"]
        ind = "    "
    chain = []
    x = t
    while x is not None:
        chain.append(x)
        x = x.declaring
    outer = list(reversed(chain))
    for o in outer[:-1]:
        lines += [f"{ind}{o.declaration()}", f"{ind}{{"]
        ind += "    "

    def summary(doc_id, pad):
        d = docs.get(doc_id) or {}
        if d.get("summary"):
            lines.append(f"{pad}/// <summary>")
            lines.append(f"{pad}/// {d['summary']}")
            lines.append(f"{pad}/// </summary>")
    summary(t.doc_id, ind)
    lines += [f"{ind}{t.declaration()}", f"{ind}{{"]
    inner = ind + "    "
    for m in t.members(False):
        summary(m.doc_id, inner)
        if m.kind == "EnumValue":
            lines.append(f"{inner}{m.signature},")
        elif m.kind in ("Property", "Event") or m.kind in ("Field", "Constant"):
            lines.append(f"{inner}{m.signature}{'' if m.kind == 'Property' else ';'}")
        else:
            lines.append(f"{inner}{m.signature};")
        lines.append("")
    if lines[-1] == "":
        lines.pop()
    lines.append(f"{ind}}}")
    for _o in outer[:-1]:
        ind = ind[:-4]
        lines.append(f"{ind}}}")
    if t.namespace:
        lines.append("}")
    return "\n".join(lines) + "\n"


__all__ = ["AssemblyMeta", "TypeMeta", "MemberMeta", "AssemblyRefMeta", "NotManaged", "read_assembly",
           "is_managed", "pe_kind", "assembly_identity", "load_docs", "doc_for", "metadata_as_source",
           "xml_doc_file"]
