"""NuGet versions, version ranges and target frameworks (the parts the package manager needs).

* ``NuGetVersion`` - SemVer 2.0 with NuGet's 4th part: ``1.2.3``, ``1.2.3.4``, ``2.0.0-beta.1+sha``,
  ordered like NuGet (a release sorts after its prereleases; prerelease labels compare part by
  part, numeric parts numerically, case-insensitively).
* ``VersionRange`` - NuGet range notation: ``1.0`` (>= 1.0), ``[1.0]`` (exact), ``[1.0,2.0)``,
  ``(,2.0]``, ``*`` and floating ``1.*``.
* Target frameworks: ``parse_tfm`` understands short folder names (``net48``, ``net8.0``,
  ``net8.0-windows``, ``netstandard2.0``, ``netcoreapp3.1``) and the long nuspec spelling
  (``.NETFramework4.5``, ``.NETStandard2.0``); ``nearest`` picks the best compatible group / lib
  folder for a project framework the way NuGet's reducer does for the common cases.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering

_VER = re.compile(r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.\-]+))?(?:\+([0-9A-Za-z.\-]+))?\s*$")


@total_ordering
@dataclass(frozen=True)
class NuGetVersion:
    major: int
    minor: int = 0
    patch: int = 0
    revision: int = 0
    release: str = ""            # prerelease label without the dash
    metadata: str = ""
    original: str = ""

    @staticmethod
    def parse(text: str) -> "NuGetVersion":
        m = _VER.match(str(text or ""))
        if not m:
            raise ValueError(f"'{text}' is not a valid NuGet version")
        a, b, c, d, rel, meta = m.groups()
        return NuGetVersion(int(a), int(b or 0), int(c or 0), int(d or 0), rel or "", meta or "", str(text).strip())

    @staticmethod
    def try_parse(text: str) -> "NuGetVersion | None":
        try:
            return NuGetVersion.parse(text)
        except ValueError:
            return None

    @property
    def is_prerelease(self) -> bool:
        return bool(self.release)

    def normalized(self) -> str:
        s = f"{self.major}.{self.minor}.{self.patch}"
        if self.revision:
            s += f".{self.revision}"
        if self.release:
            s += f"-{self.release}"
        return s

    def __str__(self) -> str:
        return self.normalized()

    def _key(self):
        rel = ()
        if self.release:
            parts = []
            for p in self.release.split("."):
                parts.append((0, int(p), "") if p.isdigit() else (1, 0, p.lower()))
            rel = tuple(parts)
        return (self.major, self.minor, self.patch, self.revision, 0 if self.release else 1, rel)

    def __eq__(self, other) -> bool:
        return isinstance(other, NuGetVersion) and self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    def __lt__(self, other: "NuGetVersion") -> bool:
        return self._key() < other._key()


def sort_versions(versions, descending: bool = True) -> list[str]:
    """Version strings sorted like NuGet (invalid ones dropped)."""
    parsed = [(NuGetVersion.try_parse(v), v) for v in versions]
    parsed = [(p, v) for p, v in parsed if p is not None]
    parsed.sort(key=lambda t: t[0], reverse=descending)
    out, seen = [], set()
    for p, v in parsed:
        if p not in seen:
            seen.add(p)
            out.append(v)
    return out


def latest(versions, prerelease: bool = False) -> str:
    for v in sort_versions(versions):
        p = NuGetVersion.parse(v)
        if prerelease or not p.is_prerelease:
            return v
    return ""


def is_newer(candidate: str, current: str) -> bool:
    a, b = NuGetVersion.try_parse(candidate), NuGetVersion.try_parse(current)
    return a is not None and b is not None and a > b


@dataclass
class VersionRange:
    min: NuGetVersion | None = None
    min_inclusive: bool = True
    max: NuGetVersion | None = None
    max_inclusive: bool = False
    floating: str = ""           # "1.*" / "*"
    original: str = ""

    @staticmethod
    def parse(text: str) -> "VersionRange":
        s = str(text or "").strip()
        if not s or s == "*":
            return VersionRange(floating="*" if s else "", original=s)
        if "*" in s and not s.startswith(("[", "(")):
            base = s.split("*")[0].rstrip(".-")
            lo = NuGetVersion.try_parse(base) if base else None
            return VersionRange(lo, True, None, False, s, s)
        if s[0] in "[(":
            inc_lo, inc_hi = s[0] == "[", s[-1] == "]"
            body = s[1:-1]
            if "," not in body:
                v = NuGetVersion.parse(body)
                return VersionRange(v, True, v, True, "", s)
            lo, hi = (x.strip() for x in body.split(",", 1))
            return VersionRange(NuGetVersion.parse(lo) if lo else None, inc_lo,
                                NuGetVersion.parse(hi) if hi else None, inc_hi, "", s)
        return VersionRange(NuGetVersion.parse(s), True, None, False, "", s)

    def satisfies(self, version) -> bool:
        v = version if isinstance(version, NuGetVersion) else NuGetVersion.try_parse(version)
        if v is None:
            return False
        if self.floating == "*":
            return True
        if self.min is not None and (v < self.min or (v == self.min and not self.min_inclusive)):
            return False
        if self.max is not None and (v > self.max or (v == self.max and not self.max_inclusive)):
            return False
        return True

    def best_match(self, versions, prerelease: bool = False, lowest: bool = True) -> str:
        """Lowest (NuGet's default dependency behavior) or highest version in the range."""
        allow_pre = prerelease or (self.min is not None and self.min.is_prerelease)
        cands = [v for v in sort_versions(versions, descending=not lowest) if self.satisfies(v)
                 and (allow_pre or not NuGetVersion.parse(v).is_prerelease)]
        if self.floating:
            cands = [v for v in sort_versions(versions) if self.satisfies(v) and
                     (allow_pre or not NuGetVersion.parse(v).is_prerelease)]
        return cands[0] if cands else ""

    def pretty(self) -> str:
        """VS wording: '>= 13.0.1', '>= 1.0 && < 2.0', '= 1.0'."""
        if self.floating == "*":
            return "*"
        if self.min is not None and self.max is not None and self.min == self.max:
            return f"= {self.min}"
        parts = []
        if self.min is not None:
            parts.append(f"{'>=' if self.min_inclusive else '>'} {self.min}")
        if self.max is not None:
            parts.append(f"{'<=' if self.max_inclusive else '<'} {self.max}")
        return " && ".join(parts) or "(any)"


# ====================================================================== frameworks
@dataclass(frozen=True)
class Framework:
    family: str                  # "net" (Framework), "core" (netcoreapp / net5+), "std" (netstandard), "any", "other"
    version: tuple = (0,)
    platform: str = ""           # windows, android ...
    original: str = ""

    def short(self) -> str:
        v = self.version
        if self.family == "net":
            return "net" + "".join(str(x) for x in v)
        if self.family == "std":
            return f"netstandard{v[0]}.{v[1] if len(v) > 1 else 0}"
        if self.family == "core":
            base = f"net{v[0]}.{v[1] if len(v) > 1 else 0}" if v[0] >= 5 else \
                f"netcoreapp{v[0]}.{v[1] if len(v) > 1 else 0}"
            return base + (f"-{self.platform}" if self.platform else "")
        return self.original or self.family

    def display(self) -> str:
        """Dependency group title like VS: '.NETFramework,Version=v4.6.2', 'net8.0', '.NETStandard,Version=v2.0'."""
        v = self.version
        if self.family == "net":
            return ".NETFramework,Version=v" + ".".join(str(x) for x in v)
        if self.family == "std":
            return f".NETStandard,Version=v{v[0]}.{v[1] if len(v) > 1 else 0}"
        if self.family == "core" and v[0] < 5:
            return f".NETCoreApp,Version=v{v[0]}.{v[1] if len(v) > 1 else 0}"
        if self.family == "any":
            return "(any framework)"
        return self.short()


ANY = Framework("any", (0,), "", "")


def _vtuple(s: str) -> tuple:
    s = s.strip(".")
    if not s:
        return (0,)
    if "." in s:
        return tuple(int(x) for x in s.split(".") if x.isdigit())
    if s.isdigit():
        return tuple(int(c) for c in s) if len(s) > 1 else (int(s), 0)
    return (0,)


def parse_tfm(text: str) -> Framework:
    t = str(text or "").strip()
    low = t.lower()
    if not low or low in ("any", "dotnet"):
        return ANY
    m = re.match(r"^\.netframework,?\s*(?:version=)?v?([\d.]+)", low) or re.match(r"^\.netframework([\d.]+)$", low)
    if m:
        return Framework("net", _vtuple(m.group(1)), "", t)
    m = re.match(r"^\.netstandard,?\s*(?:version=)?v?([\d.]+)", low) or re.match(r"^\.netstandard([\d.]+)$", low)
    if m:
        return Framework("std", _vtuple(m.group(1)), "", t)
    m = re.match(r"^\.netcoreapp,?\s*(?:version=)?v?([\d.]+)", low) or re.match(r"^\.netcoreapp([\d.]+)$", low)
    if m:
        return Framework("core", _vtuple(m.group(1)), "", t)
    m = re.match(r"^netstandard([\d.]+)$", low)
    if m:
        return Framework("std", _vtuple(m.group(1)), "", t)
    m = re.match(r"^netcoreapp([\d.]+)$", low)
    if m:
        return Framework("core", _vtuple(m.group(1)), "", t)
    m = re.match(r"^net(\d+\.\d+)(?:-([a-z]+)[\d.]*)?$", low)          # net5.0, net8.0-windows
    if m:
        return Framework("core", _vtuple(m.group(1)), m.group(2) or "", t)
    m = re.match(r"^net(\d{2,3})$", low)                              # net45, net472, net48
    if m:
        return Framework("net", _vtuple(m.group(1)), "", t)
    m = re.match(r"^net(\d)$", low)
    if m:
        return Framework("net", (int(m.group(1)), 0), "", t)
    return Framework("other", (0,), "", t)


def _std_for(fw: Framework) -> tuple:
    """Highest .NET Standard version a framework implements."""
    v = fw.version + (0, 0)
    if fw.family == "core":
        return (2, 1) if v[:2] >= (3, 0) else (2, 0) if v[0] >= 2 else (1, 6)
    if fw.family == "net":
        if v[:3] >= (4, 6, 1):
            return (2, 0)
        if v[:2] >= (4, 6):
            return (1, 3)
        if v[:3] >= (4, 5, 2):
            return (1, 2)
        if v[:3] >= (4, 5, 1):
            return (1, 2)
        if v[:2] >= (4, 5):
            return (1, 1)
        return (0,)
    if fw.family == "std":
        return fw.version
    return (0,)


def compatible(project: Framework, candidate: Framework) -> bool:
    """Can a project targeting `project` use assets built for `candidate`?"""
    if candidate.family == "any":
        return True
    if candidate.family == "other" or project.family in ("any", "other"):
        return False
    if candidate.platform and candidate.platform != project.platform:
        return False
    if candidate.family == project.family:
        return candidate.version <= project.version
    if candidate.family == "std":
        return candidate.version <= _std_for(project) and _std_for(project) != (0,)
    return False


def nearest(project, candidates):
    """Best candidate (Framework or TFM string) for a project framework, or None.
    Same family beats .NET Standard beats "any"; a higher compatible version wins."""
    pf = project if isinstance(project, Framework) else parse_tfm(project)
    best, best_key = None, None
    for c in candidates:
        cf = c if isinstance(c, Framework) else parse_tfm(c)
        if not compatible(pf, cf):
            continue
        rank = 3 if cf.family == pf.family else 2 if cf.family == "std" else 1
        key = (rank, 1 if cf.platform else 0, cf.version)
        if best_key is None or key > best_key:
            best, best_key = c, key
    return best


__all__ = ["NuGetVersion", "VersionRange", "Framework", "parse_tfm", "compatible", "nearest", "sort_versions",
           "latest", "is_newer", "ANY"]
