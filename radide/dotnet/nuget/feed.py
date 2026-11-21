"""NuGet package sources: the v3 protocol (nuget.org and any v3 feed) and local folders.

* ``V3Feed(url)``      - service index -> SearchQueryService (search, downloads, verified badge),
                          SearchAutocompleteService (Package Manager Console tab completion),
                          RegistrationsBaseUrl/3.6.0 (every version's metadata: dependencies per
                          target framework, license, project URL, deprecation, vulnerabilities),
                          PackageBaseAddress (version list, .nupkg download) and ReadmeUriTemplate.
* ``LocalFeed(folder)`` - a folder of ``*.nupkg`` files (flat or ``id/version/`` hierarchical) and the
                          global packages folder (``id/version/id.nuspec``): browse offline.
* ``AggregateFeed``     - "All" in the Package source combo.
* ``parse_nuspec``      - metadata from a .nuspec (also inside a .nupkg).

Network access goes through radide.dotnet.nuget.http (disk cache, recorded fixtures for tests).
"""
from __future__ import annotations

import re
import threading
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlencode

from . import http
from .config import NUGET_ORG, PackageSource
from .versions import NuGetVersion, sort_versions

SEVERITY = {0: "Low", 1: "Moderate", 2: "High", 3: "Critical"}


@dataclass
class SearchResult:
    id: str
    version: str = ""                         # latest version (by the search options)
    description: str = ""
    summary: str = ""
    title: str = ""
    authors: list = field(default_factory=list)
    owners: list = field(default_factory=list)
    icon_url: str = ""
    total_downloads: int = 0
    verified: bool = False
    versions: list = field(default_factory=list)      # [(version, downloads)]
    project_url: str = ""
    license_url: str = ""
    tags: list = field(default_factory=list)
    source: str = ""                          # package source name
    deprecated: bool = False
    vulnerable: bool = False

    @property
    def version_list(self) -> list[str]:
        return [v for v, _d in self.versions] or ([self.version] if self.version else [])


@dataclass
class Dependency:
    id: str
    range: str = ""


@dataclass
class DependencyGroup:
    framework: str                            # "" = any
    dependencies: list = field(default_factory=list)   # [Dependency]


@dataclass
class PackageMetadata:
    id: str
    version: str
    description: str = ""
    summary: str = ""
    title: str = ""
    authors: str = ""
    owners: str = ""
    license_expression: str = ""
    license_url: str = ""
    project_url: str = ""
    icon_url: str = ""
    readme_url: str = ""
    published: str = ""
    listed: bool = True
    require_license_acceptance: bool = False
    tags: str = ""
    downloads: int = -1
    dependency_groups: list = field(default_factory=list)     # [DependencyGroup]
    framework_assemblies: list = field(default_factory=list)  # [(assembly, tfm)]
    deprecation: dict = field(default_factory=dict)           # {reasons, message, alternate}
    vulnerabilities: list = field(default_factory=list)       # [{severity, url}]
    source: str = ""

    @property
    def license_link(self) -> str:
        if self.license_expression and re.fullmatch(r"[\w.\-+]+", self.license_expression):
            return f"https://licenses.nuget.org/{self.license_expression}"
        return self.license_url

    @property
    def license_text(self) -> str:
        return self.license_expression or ("View License" if self.license_url else "")

    def deprecation_text(self) -> str:
        d = self.deprecation
        if not d:
            return ""
        reasons = ", ".join(d.get("reasons") or []) or "deprecated"
        s = f"This package version is deprecated ({reasons})."
        if d.get("message"):
            s += " " + d["message"]
        alt = d.get("alternate")
        if alt:
            s += f" Use {alt} instead."
        return s

    def vulnerability_text(self) -> str:
        if not self.vulnerabilities:
            return ""
        sev = max(int(v.get("severity", 0) or 0) for v in self.vulnerabilities)
        return f"This package version has {len(self.vulnerabilities)} known {SEVERITY.get(sev, 'High').lower()} " \
               f"severity vulnerabilit{'y' if len(self.vulnerabilities) == 1 else 'ies'}."


# ====================================================================== nuspec
def _ln(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_nuspec(data: bytes, source: str = "") -> PackageMetadata:
    root = ET.fromstring(data)
    md = next((c for c in root if _ln(c.tag) == "metadata"), root)

    def val(name):
        el = next((c for c in md if _ln(c.tag) == name), None)
        return (el.text or "").strip() if el is not None else ""

    meta = PackageMetadata(val("id"), val("version"), val("description"), val("summary"), val("title"),
                           val("authors"), val("owners"), "", "", val("projectUrl"), val("iconUrl"),
                           tags=val("tags"), source=source)
    meta.require_license_acceptance = val("requireLicenseAcceptance").lower() == "true"
    lic = next((c for c in md if _ln(c.tag) == "license"), None)
    if lic is not None and lic.get("type") == "expression":
        meta.license_expression = (lic.text or "").strip()
    meta.license_url = val("licenseUrl")
    if val("readme"):
        meta.readme_url = "nupkg:" + val("readme")
    deps = next((c for c in md if _ln(c.tag) == "dependencies"), None)
    if deps is not None:
        loose = []
        for c in deps:
            if _ln(c.tag) == "group":
                g = DependencyGroup(c.get("targetFramework", ""))
                for d in c:
                    if _ln(d.tag) == "dependency":
                        g.dependencies.append(Dependency(d.get("id", ""), d.get("version", "")))
                meta.dependency_groups.append(g)
            elif _ln(c.tag) == "dependency":
                loose.append(Dependency(c.get("id", ""), c.get("version", "")))
        if loose:
            meta.dependency_groups.append(DependencyGroup("", loose))
    fa = next((c for c in md if _ln(c.tag) == "frameworkAssemblies"), None)
    if fa is not None:
        for c in fa:
            if _ln(c.tag) == "frameworkAssembly":
                meta.framework_assemblies.append((c.get("assemblyName", ""), c.get("targetFramework", "")))
    return meta


def nuspec_from_nupkg(path) -> bytes:
    with zipfile.ZipFile(path) as z:
        name = next((n for n in z.namelist() if n.lower().endswith(".nuspec") and "/" not in n), None)
        if name is None:
            raise ValueError(f"{Path(path).name}: no .nuspec inside")
        return z.read(name)


# ====================================================================== feeds
class Feed:
    name = ""
    url = ""

    def search(self, query: str, prerelease: bool = False, skip: int = 0, take: int = 25) -> tuple[list, int]:
        raise NotImplementedError

    def versions(self, package_id: str) -> list[str]:
        raise NotImplementedError

    def metadata(self, package_id: str, version: str = "") -> PackageMetadata | None:
        raise NotImplementedError

    def all_metadata(self, package_id: str) -> dict[str, PackageMetadata]:
        m = self.metadata(package_id)
        return {m.version: m} if m else {}

    def readme(self, package_id: str, version: str) -> str:
        return ""

    def autocomplete(self, prefix: str, prerelease: bool = False, take: int = 20) -> list[str]:
        rows, _n = self.search(prefix, prerelease, 0, take)
        return [r.id for r in rows if r.id.lower().startswith(prefix.lower())] or [r.id for r in rows]

    def download(self, package_id: str, version: str, dest: Path) -> Path:
        raise NotImplementedError

    def latest(self, package_id: str, prerelease: bool = False) -> str:
        for v in sort_versions(self.versions(package_id)):
            if prerelease or not NuGetVersion.parse(v).is_prerelease:
                return v
        return ""


class V3Feed(Feed):
    def __init__(self, url: str, name: str = ""):
        self.url, self.name = url, name or url
        self._index = None
        self._reg: dict[str, dict] = {}
        self._lock = threading.Lock()

    # service index
    def resources(self) -> dict[str, list[str]]:
        if self._index is None:
            data = http.get_json(self.url, ttl=24 * 3600)
            res: dict[str, list[str]] = {}
            for r in data.get("resources", []):
                t = r.get("@type")
                for tt in (t if isinstance(t, list) else [t]):
                    res.setdefault(str(tt), []).append(r.get("@id", ""))
            self._index = res
        return self._index

    def resource(self, *types: str) -> str:
        res = self.resources()
        for t in types:
            if res.get(t):
                return res[t][0]
        return ""

    # search
    def search(self, query, prerelease=False, skip=0, take=25):
        base = self.resource("SearchQueryService/3.5.0", "SearchQueryService/3.0.0-rc", "SearchQueryService")
        if not base:
            return [], 0
        q = urlencode({"q": query, "skip": skip, "take": take, "prerelease": str(bool(prerelease)).lower(),
                       "semVerLevel": "2.0.0"})
        data = http.get_json(f"{base}?{q}", ttl=300)
        out = []
        for d in data.get("data", []):
            out.append(SearchResult(
                d.get("id", ""), d.get("version", ""), d.get("description", "") or "", d.get("summary", "") or "",
                d.get("title", "") or "", _as_list(d.get("authors")), _as_list(d.get("owners")), d.get("iconUrl", "") or "",
                int(d.get("totalDownloads") or 0), bool(d.get("verified")),
                [(v.get("version", ""), int(v.get("downloads") or 0)) for v in d.get("versions", [])],
                d.get("projectUrl", "") or "", d.get("licenseUrl", "") or "", _as_list(d.get("tags")), self.name,
                bool(d.get("deprecation")), bool(d.get("vulnerabilities"))))
        return out, int(data.get("totalHits") or len(out))

    def autocomplete(self, prefix, prerelease=False, take=20):
        base = self.resource("SearchAutocompleteService/3.5.0", "SearchAutocompleteService")
        if not base:
            return super().autocomplete(prefix, prerelease, take)
        q = urlencode({"q": prefix, "take": take, "prerelease": str(bool(prerelease)).lower(), "semVerLevel": "2.0.0"})
        return list(http.get_json(f"{base}?{q}", ttl=3600).get("data", []))

    def autocomplete_versions(self, package_id: str, prerelease: bool = False) -> list[str]:
        return [v for v in sort_versions(self.versions(package_id))
                if prerelease or not NuGetVersion.parse(v).is_prerelease]

    # versions / metadata
    def _flat(self) -> str:
        b = self.resource("PackageBaseAddress/3.0.0")
        return b if not b or b.endswith("/") else b + "/"

    def versions(self, package_id):
        base = self._flat()
        if base:
            try:
                data = http.get_json(f"{base}{package_id.lower()}/index.json", ttl=600)
                return sort_versions(data.get("versions", []))
            except http.HttpError as e:
                if e.status == 404:
                    return []
                raise
        return sort_versions(self.all_metadata(package_id).keys())

    def _registration(self, package_id: str) -> dict:
        key = package_id.lower()
        with self._lock:
            if key in self._reg:
                return self._reg[key]
        base = self.resource("RegistrationsBaseUrl/3.6.0", "RegistrationsBaseUrl/3.4.0", "RegistrationsBaseUrl")
        if not base:
            return {}
        if not base.endswith("/"):
            base += "/"
        try:
            index = http.get_json(f"{base}{quote(key)}/index.json", ttl=600)
        except http.HttpError as e:
            if e.status == 404:
                return {}
            raise
        out: dict[str, PackageMetadata] = {}
        for page in index.get("items", []):
            leaves = page.get("items")
            if leaves is None and page.get("@id"):
                leaves = http.get_json(page["@id"], ttl=600).get("items", [])
            for leaf in leaves or []:
                ce = leaf.get("catalogEntry") or {}
                m = _meta_from_catalog(ce, self.name)
                if m.version:
                    out[m.version] = m
        with self._lock:
            self._reg[key] = out
        return out

    def all_metadata(self, package_id):
        return dict(self._registration(package_id))

    def metadata(self, package_id, version=""):
        reg = self._registration(package_id)
        if not reg:
            return None
        if not version:
            listed = [v for v, m in reg.items() if m.listed]
            vs = sort_versions(listed or reg.keys())
            stable = [v for v in vs if not NuGetVersion.parse(v).is_prerelease]
            version = (stable or vs)[0]
        want = NuGetVersion.try_parse(version)
        for v, m in reg.items():
            if NuGetVersion.try_parse(v) == want:
                return m
        return None

    def readme(self, package_id, version):
        tpl = self.resource("ReadmeUriTemplate/6.13.0")
        if not tpl:
            return ""
        url = tpl.replace("{lower_id}", package_id.lower()).replace("{lower_version}",
                                                                     NuGetVersion.parse(version).normalized().lower())
        try:
            return http.get(url, ttl=24 * 3600).decode("utf-8", errors="replace")
        except (http.HttpError, OSError):
            return ""

    def nupkg_url(self, package_id: str, version: str) -> str:
        i, v = package_id.lower(), NuGetVersion.parse(version).normalized().lower()
        return f"{self._flat()}{i}/{v}/{i}.{v}.nupkg"

    def download(self, package_id, version, dest):
        return http.download(self.nupkg_url(package_id, version), dest)


def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return list(v)


def _meta_from_catalog(ce: dict, source: str) -> PackageMetadata:
    m = PackageMetadata(ce.get("id", ""), ce.get("version", ""), ce.get("description", "") or "",
                        ce.get("summary", "") or "", ce.get("title", "") or "",
                        ", ".join(_as_list(ce.get("authors"))), "", ce.get("licenseExpression", "") or "",
                        ce.get("licenseUrl", "") or "", ce.get("projectUrl", "") or "", ce.get("iconUrl", "") or "",
                        ce.get("readmeUrl", "") or "", ce.get("published", "") or "",
                        bool(ce.get("listed", True)), bool(ce.get("requireLicenseAcceptance", False)),
                        ", ".join(_as_list(ce.get("tags"))), source=source)
    if m.published.startswith("1900"):
        m.listed = False
    for g in ce.get("dependencyGroups", []) or []:
        grp = DependencyGroup(g.get("targetFramework", "") or "")
        for d in g.get("dependencies", []) or []:
            grp.dependencies.append(Dependency(d.get("id", ""), d.get("range", "") or ""))
        m.dependency_groups.append(grp)
    dep = ce.get("deprecation")
    if dep:
        alt = dep.get("alternatePackage") or {}
        m.deprecation = {"reasons": list(dep.get("reasons") or []), "message": dep.get("message", "") or "",
                         "alternate": alt.get("id", "")}
    for v in ce.get("vulnerabilities", []) or []:
        try:
            sev = int(v.get("severity", 0))
        except (TypeError, ValueError):
            sev = 0
        m.vulnerabilities.append({"severity": sev, "url": v.get("advisoryUrl", "")})
    return m


class LocalFeed(Feed):
    """A folder source: *.nupkg (flat or id/version/) or the global packages folder layout."""

    def __init__(self, folder, name: str = ""):
        self.folder = Path(folder)
        self.url, self.name = str(self.folder), name or str(self.folder)
        self._index: dict[str, dict[str, Path]] | None = None
        self._meta: dict[tuple[str, str], PackageMetadata] = {}

    def index(self) -> dict[str, dict[str, Path]]:
        if self._index is not None:
            return self._index
        idx: dict[str, dict[str, Path]] = {}
        if self.folder.is_dir():
            try:
                entries = list(self.folder.iterdir())
            except OSError:
                entries = []
            for p in entries:
                if p.is_file() and p.suffix.lower() == ".nupkg" and not p.name.lower().endswith(".symbols.nupkg"):
                    try:
                        m = parse_nuspec(nuspec_from_nupkg(p), self.name)
                    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError):
                        continue
                    idx.setdefault(m.id.lower(), {})[m.version] = p
                elif p.is_dir():                       # id/version/
                    try:
                        vers = [v for v in p.iterdir() if v.is_dir()]
                    except OSError:
                        continue
                    for v in vers:
                        spec = next(iter(v.glob("*.nuspec")), None) or next(iter(v.glob("*.nupkg")), None)
                        if spec is not None:
                            idx.setdefault(p.name.lower(), {})[v.name] = spec
        self._index = idx
        return idx

    def _load(self, key: str, version: str) -> PackageMetadata | None:
        k = (key, version)
        if k in self._meta:
            return self._meta[k]
        p = self.index().get(key, {}).get(version)
        if p is None:
            return None
        try:
            data = p.read_bytes() if p.suffix.lower() == ".nuspec" else nuspec_from_nupkg(p)
            m = parse_nuspec(data, self.name)
        except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError):
            return None
        self._meta[k] = m
        return m

    def search(self, query, prerelease=False, skip=0, take=25):
        q = query.lower().strip()
        rows = []
        for key, vers in sorted(self.index().items()):
            vs = [v for v in sort_versions(vers) if prerelease or not NuGetVersion.parse(v).is_prerelease]
            if not vs:
                continue
            m = self._load(key, vs[0])
            if m is None:
                continue
            hay = f"{m.id} {m.description} {m.tags} {m.title}".lower()
            if q and not all(w in hay for w in q.split()):
                continue
            rows.append(SearchResult(m.id, m.version, m.description, m.summary, m.title, _as_list(m.authors),
                                     _as_list(m.owners), m.icon_url, -1, False, [(v, -1) for v in vs],
                                     m.project_url, m.license_url, _as_list(m.tags.replace(" ", ",")), self.name))
        if q:
            rows.sort(key=lambda r: (0 if r.id.lower() == q else 1 if r.id.lower().startswith(q) else 2, r.id.lower()))
        return rows[skip:skip + take], len(rows)

    def versions(self, package_id):
        return sort_versions(self.index().get(package_id.lower(), {}).keys())

    def metadata(self, package_id, version=""):
        key = package_id.lower()
        vs = self.versions(package_id)
        if not vs:
            return None
        if not version:
            stable = [v for v in vs if not NuGetVersion.parse(v).is_prerelease]
            version = (stable or vs)[0]
        want = NuGetVersion.try_parse(version)
        for v in vs:
            if NuGetVersion.try_parse(v) == want:
                return self._load(key, v)
        return None

    def all_metadata(self, package_id):
        out = {}
        for v in self.versions(package_id):
            m = self._load(package_id.lower(), v)
            if m:
                out[v] = m
        return out

    def readme(self, package_id, version):
        m = self.metadata(package_id, version)
        p = self.index().get(package_id.lower(), {}).get(m.version if m else version)
        if p is None or m is None or not m.readme_url:
            return ""
        name = m.readme_url[len("nupkg:"):].replace("\\", "/")
        try:
            if p.suffix.lower() == ".nuspec":
                f = p.parent / name
                return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else ""
            with zipfile.ZipFile(p) as z:
                return z.read(name).decode("utf-8", errors="replace")
        except (OSError, KeyError, zipfile.BadZipFile):
            return ""

    def nupkg_path(self, package_id: str, version: str) -> Path | None:
        want = NuGetVersion.try_parse(version)
        for v, p in self.index().get(package_id.lower(), {}).items():
            if NuGetVersion.try_parse(v) == want:
                if p.suffix.lower() == ".nupkg":
                    return p
                cand = next(iter(p.parent.glob("*.nupkg")), None)
                return cand
        return None

    def download(self, package_id, version, dest):
        src = self.nupkg_path(package_id, version)
        if src is None:
            raise FileNotFoundError(f"{package_id} {version} is not in {self.folder}")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        return dest


class AggregateFeed(Feed):
    """Every enabled source ("All")."""

    def __init__(self, feeds: list[Feed]):
        self.feeds = feeds
        self.name, self.url = "All", ""

    def search(self, query, prerelease=False, skip=0, take=25):
        merged: dict[str, SearchResult] = {}
        total = 0
        errors = []
        for f in self.feeds:
            try:
                rows, n = f.search(query, prerelease, skip, take)
            except Exception as e:  # noqa: BLE001 - one broken source must not hide the others
                errors.append(f"{f.name}: {e}")
                continue
            total = max(total, n)
            for r in rows:
                merged.setdefault(r.id.lower(), r)
        if not merged and errors:
            raise OSError("; ".join(errors))
        return list(merged.values()), total

    def _first(self, call):
        last = None
        for f in self.feeds:
            try:
                r = call(f)
            except Exception as e:  # noqa: BLE001
                last = e
                continue
            if r:
                return r
        if last is not None and not isinstance(last, http.HttpError):
            raise last
        return None

    def versions(self, package_id):
        allv = []
        for f in self.feeds:
            try:
                allv += f.versions(package_id)
            except Exception:  # noqa: BLE001
                continue
        return sort_versions(allv)

    def metadata(self, package_id, version=""):
        return self._first(lambda f: f.metadata(package_id, version))

    def all_metadata(self, package_id):
        return self._first(lambda f: f.all_metadata(package_id)) or {}

    def readme(self, package_id, version):
        return self._first(lambda f: f.readme(package_id, version)) or ""

    def autocomplete(self, prefix, prerelease=False, take=20):
        out = []
        for f in self.feeds:
            try:
                for i in f.autocomplete(prefix, prerelease, take):
                    if i.lower() not in {x.lower() for x in out}:
                        out.append(i)
            except Exception:  # noqa: BLE001
                continue
        return out[:take]

    def download(self, package_id, version, dest):
        last = None
        for f in self.feeds:
            try:
                if version in f.versions(package_id) or NuGetVersion.parse(version) in \
                        {NuGetVersion.parse(v) for v in f.versions(package_id)}:
                    return f.download(package_id, version, dest)
            except Exception as e:  # noqa: BLE001
                last = e
        raise FileNotFoundError(f"{package_id} {version} was not found in any package source"
                                + (f" ({last})" if last else ""))


_FEEDS: dict[str, Feed] = {}


def feed_for(source: PackageSource | str, name: str = "") -> Feed:
    """A (cached) feed for a package source or URL / folder."""
    url = source.url if isinstance(source, PackageSource) else str(source)
    nm = source.name if isinstance(source, PackageSource) else (name or url)
    key = url.lower()
    f = _FEEDS.get(key)
    if f is None:
        if url.lower().startswith(("http://", "https://")):
            f = V3Feed(url, nm)
        else:
            f = LocalFeed(url, nm)
        _FEEDS[key] = f
    return f


def clear_feed_cache() -> None:
    _FEEDS.clear()


def nuget_org() -> V3Feed:
    return feed_for(PackageSource("nuget.org", NUGET_ORG))   # type: ignore[return-value]


def package_page(package_id: str, version: str = "") -> str:
    return f"https://www.nuget.org/packages/{package_id}/{version}".rstrip("/")


__all__ = ["Feed", "V3Feed", "LocalFeed", "AggregateFeed", "SearchResult", "PackageMetadata", "DependencyGroup",
           "Dependency", "parse_nuspec", "nuspec_from_nupkg", "feed_for", "clear_feed_cache", "nuget_org",
           "package_page", "SEVERITY"]
