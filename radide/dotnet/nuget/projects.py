"""NuGet in a project: the three package management styles Visual Studio 2022 supports.

``NuGetProject(path)`` wraps one .csproj / .vbproj / .fsproj and picks its style:

* **PackageReference** (SDK-style projects, and legacy projects that already use it):
  ``dotnet add/remove package`` (correct version resolution + restore); a legacy project, or a
  machine without the .NET SDK, gets the ``<PackageReference>`` written in place and an MSBuild
  ``-t:restore``.
* **Central Package Management** (a ``Directory.Packages.props`` above the project with
  ``ManagePackageVersionsCentrally``): versions live in ``<PackageVersion>`` items of the props file,
  the project has ``<PackageReference Include="X" />`` without a version (``VersionOverride`` is read).
  ``dotnet add package`` maintains both files; the fallback edits them directly.
* **packages.config** (old .NET Framework projects): the package and its dependencies (lowest
  applicable version, like NuGet) are extracted to the solution ``packages`` folder, entries are
  written to packages.config, ``<Reference>`` items with ``HintPath`` for the best ``lib/<tfm>``
  folder are added, ``build/<Id>.props|.targets`` are imported with the
  ``EnsureNuGetPackageBuildImports`` check, and frameworkAssemblies become references.
  Restore extracts missing packages itself (global packages folder, then the package sources);
  ``nuget.exe`` (downloaded from dist.nuget.org) is the fallback.

Operations are synchronous and report progress lines through ``log`` (the UI runs them in a worker
thread); they raise ``NuGetError`` with a message like Visual Studio's when something fails.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from ...foreign import msbuild as MB
from . import http
from .config import enabled_sources, global_packages_folder, repository_path
from .feed import AggregateFeed, Feed, LocalFeed, PackageMetadata, feed_for, nuspec_from_nupkg, parse_nuspec
from .versions import NuGetVersion, VersionRange, nearest, parse_tfm, sort_versions

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
NUGET_EXE_URL = "https://dist.nuget.org/win-x86-commandline/latest/nuget.exe"
STYLE_PR, STYLE_CPM, STYLE_PC = "PackageReference", "CentralPackageManagement", "packages.config"
ENSURE_TARGET = "EnsureNuGetPackageBuildImports"
ENSURE_TEXT = ("This project references NuGet package(s) that are missing on this computer. Use NuGet Package "
               "Restore to download them.  For more information, see http://go.microsoft.com/fwlink/?LinkID=322105. "
               "The missing file is {0}.")


class NuGetError(Exception):
    pass


@dataclass
class InstalledPackage:
    id: str
    version: str                      # resolved / written version
    requested: str = ""               # as written (range, floating) - PackageReference
    transitive: bool = False
    central: bool = False             # version from Directory.Packages.props
    override: bool = False            # VersionOverride
    target_framework: str = ""        # packages.config


def _noop(_s: str) -> None:
    pass


def default_format() -> str:
    """Tools > Options > NuGet Package Manager > General > Default package management format."""
    try:
        from PyQt6.QtCore import QSettings
        v = str(QSettings().value("nuget/default_format", STYLE_PC) or STYLE_PC)
        return v if v in (STYLE_PC, STYLE_PR) else STYLE_PC
    except Exception:  # noqa: BLE001
        return STYLE_PC


def run(argv: list[str], cwd=None, log=_noop, timeout: float = 900) -> tuple[int, str]:
    """Run a tool, streaming its output to log. Returns (exit code, output)."""
    log("> " + " ".join(f'"{a}"' if " " in str(a) else str(a) for a in argv))
    try:
        p = subprocess.Popen([str(a) for a in argv], cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW,
                             env={**os.environ, "DOTNET_CLI_UI_LANGUAGE": "en", "DOTNET_NOLOGO": "1",
                                  "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1"})
    except OSError as e:
        raise NuGetError(f"cannot start {argv[0]}: {e}") from None
    lines = []
    assert p.stdout is not None
    for raw in p.stdout:
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        lines.append(line)
        log(line)
    try:
        code = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        raise NuGetError(f"{Path(argv[0]).name} timed out") from None
    return code, "\n".join(lines)


def run_retry(argv: list[str], cwd=None, log=_noop, tries: int = 4) -> tuple[int, str]:
    """run() again when the project file was locked for a moment (a language server or file watcher reading it)."""
    import time
    for i in range(tries):
        code, out = run(argv, cwd, log)
        if code == 0 or "being used by another process" not in out or i == tries - 1:
            return code, out
        log("The project file is in use by another process - retrying ...")
        time.sleep(1.0 + i)
    return code, out


def find_props_upward(start: Path, name: str) -> Path | None:
    p = Path(start).resolve()
    for d in [p, *p.parents]:
        f = d / name
        if f.is_file():
            return f
    return None


def ensure_nuget_exe(log=_noop) -> Path:
    """nuget.exe (official dist.nuget.org build) under %LOCALAPPDATA%\\RADIDE\\tools\\nuget."""
    w = shutil.which("nuget")
    if w:
        return Path(w)
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "RADIDE" / "tools" / "nuget"
    exe = base / "nuget.exe"
    if not exe.is_file():
        log(f"Downloading nuget.exe from {NUGET_EXE_URL} ...")
        http.download(NUGET_EXE_URL, exe, timeout=300)
    return exe


# ====================================================================== project
class NuGetProject:
    def __init__(self, path, name: str = "", solution_folder=None, sources: list | None = None):
        self.path = Path(path).resolve()
        self.name = name or self.path.stem
        self.solution_folder = Path(solution_folder).resolve() if solution_folder else self._guess_solution()
        self._sources = sources
        self.ide_project = None                 # the IDE's project object (Solution Explorer reload)
        self.ms = MB.MSBuildProject.load(self.path)

    def __repr__(self) -> str:
        return f"<NuGetProject {self.name} ({self.style})>"

    def _guess_solution(self) -> Path:
        for d in [self.path.parent, *self.path.parent.parents][:4]:
            if any(d.glob("*.sln")) or any(d.glob("*.slnx")):
                return d
        return self.path.parent

    def reload(self) -> None:
        self.ms = MB.MSBuildProject.load(self.path)

    @property
    def folder(self) -> Path:
        return self.path.parent

    # -------------------------------------------------------------- style
    @property
    def packages_config(self) -> Path:
        for n in ("packages.config", f"packages.{self.path.stem}.config"):
            if (self.folder / n).is_file():
                return self.folder / n
        return self.folder / "packages.config"

    @property
    def central_props(self) -> Path | None:
        if self.ms.prop("ManagePackageVersionsCentrally").lower() == "false":
            return None
        f = find_props_upward(self.folder, "Directory.Packages.props")
        if f is None:
            return None
        try:
            text = f.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            return None
        if re.search(r"<ManagePackageVersionsCentrally>\s*true\s*</", text, re.I) or \
                self.ms.prop("ManagePackageVersionsCentrally").lower() == "true":
            return f
        b = find_props_upward(self.folder, "Directory.Build.props")
        if b is not None and re.search(r"<ManagePackageVersionsCentrally>\s*true\s*</",
                                       b.read_text(encoding="utf-8-sig", errors="replace"), re.I):
            return f
        return None

    forced_style = ""                          # "Choose a NuGet Package Manager Format" on the first install

    @property
    def needs_format_choice(self) -> bool:
        """A legacy project that has no packages yet (VS asks which format to use)."""
        return not self.ms.is_sdk and not self.packages_config.is_file() and not self.ms.package_references \
            and self.ms.prop("RestoreProjectStyle") != "PackageReference" and not self.forced_style

    @property
    def style(self) -> str:
        if self.forced_style and not self.packages_config.is_file() and not self.ms.package_references:
            return self.forced_style
        if self.packages_config.is_file():
            return STYLE_PC
        if self.ms.package_references or self.ms.is_sdk:
            return STYLE_CPM if self.central_props is not None else STYLE_PR
        if self.ms.prop("RestoreProjectStyle") == "PackageReference":
            return STYLE_PR
        return default_format()

    @property
    def style_display(self) -> str:
        return {STYLE_PC: "packages.config", STYLE_PR: "PackageReference",
                STYLE_CPM: "PackageReference (Central Package Management)"}[self.style]

    @property
    def target_frameworks(self) -> list[str]:
        return self.ms.target_frameworks or ["net48"]

    @property
    def framework(self) -> str:
        return self.target_frameworks[0]

    @property
    def uses_cli(self) -> bool:
        return self.ms.is_sdk and bool(MB.find_dotnet())

    # -------------------------------------------------------------- sources / feeds
    def sources(self):
        return self._sources if self._sources is not None else enabled_sources(self.solution_folder)

    def feed(self) -> Feed:
        feeds = [feed_for(s) for s in self.sources()]
        gp = global_packages_folder(self.solution_folder)
        if gp.is_dir():
            feeds.append(LocalFeed(gp, "Global packages folder"))
        return feeds[0] if len(feeds) == 1 else AggregateFeed(feeds)

    # -------------------------------------------------------------- installed
    def central_versions(self) -> dict[str, str]:
        f = self.central_props
        if f is None:
            return {}
        try:
            props = MB.MSBuildProject.load(f)
        except (OSError, ValueError):
            return {}
        return {MB.xml_unescape(i.include).lower(): i.version for i in props.explicit("PackageVersion")}

    def installed(self, include_transitive: bool = False) -> list[InstalledPackage]:
        out: list[InstalledPackage] = []
        if self.style == STYLE_PC:
            out = read_packages_config(self.packages_config)
        else:
            central = self.central_versions() if self.style == STYLE_CPM else {}
            resolved = self.assets_versions()
            for it in self.ms.package_references:
                pid = MB.xml_unescape(it.include)
                if it.metadata.get("IsImplicitlyDefined", "").lower() == "true":
                    continue
                req = it.metadata.get("VersionOverride") or it.version
                is_central = not req and pid.lower() in central
                if is_central:
                    req = central[pid.lower()]
                ver = resolved.get(pid.lower(), "") or _plain(req)
                out.append(InstalledPackage(pid, ver, req, False, is_central, bool(it.metadata.get("VersionOverride"))))
        if include_transitive and self.style != STYLE_PC:
            top = {p.id.lower() for p in out}
            for pid, ver in sorted(self.assets_versions(all_libraries=True).items()):
                if pid not in top:
                    out.append(InstalledPackage(self._assets_names.get(pid, pid), ver, "", True))
        return out

    _assets_names: dict = {}

    def assets_file(self) -> Path:
        base = self.ms.prop("BaseIntermediateOutputPath") or "obj"
        return self.folder / base.replace("\\", "/").strip("/") / "project.assets.json"

    def assets_versions(self, all_libraries: bool = False) -> dict[str, str]:
        """Resolved versions from obj/project.assets.json (top-level, or every package library)."""
        f = self.assets_file()
        try:
            data = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return {}
        libs = {}
        names = {}
        for key, lib in (data.get("libraries") or {}).items():
            if lib.get("type") != "package" or "/" not in key:
                continue
            pid, ver = key.split("/", 1)
            libs[pid.lower()] = ver
            names[pid.lower()] = pid
        self._assets_names = names
        if all_libraries:
            return libs
        top = set()
        for fw in ((data.get("project") or {}).get("frameworks") or {}).values():
            for pid in (fw.get("dependencies") or {}):
                top.add(pid.lower())
        return {k: v for k, v in libs.items() if k in top}

    def installed_version(self, package_id: str) -> str:
        for p in self.installed():
            if p.id.lower() == package_id.lower():
                return p.version
        return ""

    # -------------------------------------------------------------- operations
    def install(self, package_id: str, version: str = "", log=_noop, prerelease: bool = False,
                ignore_dependencies: bool = False, dependency_behavior: str = "Lowest") -> str:
        """Install (or change the version of) a package. Returns the installed version."""
        if not version:
            version = self.feed().latest(package_id, prerelease)
            if not version:
                raise NuGetError(f"Unable to find package '{package_id}' at source(s): "
                                 f"{', '.join(s.name for s in self.sources()) or '(none)'}")
        log(f"Installing NuGet package {package_id} {version} into {self.name} ({self.style_display}).")
        style = self.style
        if style == STYLE_PC:
            self._pc_install(package_id, version, log,
                             "IgnoreDependencies" if ignore_dependencies else dependency_behavior)
        else:
            self._pr_install(package_id, version, log, style)
        self.reload()
        log(f"Successfully installed '{package_id} {version}' to {self.name}")
        return version

    def update(self, package_id: str, version: str = "", log=_noop, prerelease: bool = False) -> str:
        cur = self.installed_version(package_id)
        if not cur:
            raise NuGetError(f"'{package_id}' is not installed in project '{self.name}'.")
        if not version:
            version = self.feed().latest(package_id, prerelease or NuGetVersion.parse(cur).is_prerelease)
        if not version:
            raise NuGetError(f"Unable to find package '{package_id}'.")
        if NuGetVersion.try_parse(version) == NuGetVersion.try_parse(cur):
            log(f"'{package_id} {cur}' is already installed in {self.name}.")
            return cur
        if self.style == STYLE_PC:
            log(f"Updating '{package_id}' from {cur} to {version} in {self.name}.")
            self._pc_uninstall(package_id, log, keep_folder_check=True, check_dependents=False)
            self.reload()
            self._pc_install(package_id, version, log)
            self.reload()
            log(f"Successfully updated '{package_id}' to {version} in {self.name}")
            return version
        return self.install(package_id, version, log)

    def uninstall(self, package_id: str, log=_noop, remove_dependencies: bool = False, force: bool = False) -> None:
        cur = self.installed_version(package_id)
        if not cur:
            raise NuGetError(f"Package '{package_id}' is not installed in project '{self.name}'.")
        log(f"Uninstalling NuGet package {package_id} {cur} from {self.name}.")
        if self.style == STYLE_PC:
            self._pc_uninstall(package_id, log, check_dependents=not force, remove_dependencies=remove_dependencies)
        else:
            self._pr_uninstall(package_id, log)
        self.reload()
        log(f"Successfully uninstalled '{package_id} {cur}' from {self.name}")

    def restore(self, log=_noop) -> bool:
        if self.style == STYLE_PC:
            return restore_packages_config(self, log)
        if self.uses_cli:
            code, _ = run([MB.find_dotnet(), "restore", str(self.path)], self.folder, log)
            return code == 0
        msb = MB.find_msbuild()
        if msb:
            code, _ = run([msb, str(self.path), "-t:restore", "-nologo", "-v:m"], self.folder, log)
            return code == 0
        raise NuGetError("Neither the .NET SDK nor MSBuild was found to restore packages.")

    # -------------------------------------------------------------- PackageReference / CPM
    def _pr_install(self, package_id: str, version: str, log, style: str) -> None:
        if self.uses_cli:
            argv = [MB.find_dotnet(), "add", str(self.path), "package", package_id, "--version", version]
            # `dotnet add package --source` accepts ONE source and then ignores the configured ones (the
            # dependencies would not resolve), so a -Source that is not configured is passed only when it is
            # the sole source; configured sources are used by the CLI's restore anyway.
            configured = {s.url.lower() for s in enabled_sources(self.solution_folder)}
            extra = [s.url for s in (self._sources or []) if s.url.lower() not in configured]
            if extra:
                if len(extra) == 1 and not configured:
                    argv += ["--source", extra[0]]
                else:
                    log(f"Note: '{extra[0]}' is not a configured package source; add it in Tools > Options > "
                        f"NuGet Package Manager > Package Sources so restore can use it.")
            code, out = run_retry(argv, self.folder, log)
            if code != 0:
                raise NuGetError(_cli_error(out) or f"dotnet add package failed (exit code {code}).")
            return
        if style == STYLE_CPM:
            props_path = self.central_props
            assert props_path is not None
            props = MB.MSBuildProject.load(props_path)
            if props.find_element("PackageVersion", package_id):
                props.set_metadata("PackageVersion", package_id, "Version", version)
            else:
                props.add_item("PackageVersion", package_id, None, {"Version": version})
            props.save()
            log(f"Updated {props_path.name}: PackageVersion {package_id} = {version}")
            if not self.ms.find_element("PackageReference", package_id):
                self.ms.add_item("PackageReference", package_id)
        else:
            self.ms.add_package(package_id, version)
        self.ms.save()
        log(f"Updated {self.path.name}")
        try:
            self.restore(log)
        except NuGetError as e:
            log(f"Restore skipped: {e}")

    def _pr_uninstall(self, package_id: str, log) -> None:
        if self.uses_cli:
            code, out = run_retry([MB.find_dotnet(), "remove", str(self.path), "package", package_id], self.folder,
                                  log)
            if code != 0:
                raise NuGetError(_cli_error(out) or f"dotnet remove package failed (exit code {code}).")
            return
        self.ms.remove_package(package_id)
        self.ms.save()
        log(f"Updated {self.path.name}")

    # -------------------------------------------------------------- packages.config
    @property
    def packages_folder(self) -> Path:
        return repository_path(self.solution_folder)

    def _rel_to_packages(self, *parts: str) -> str:
        rel = os.path.relpath(self.packages_folder.joinpath(*parts), self.folder)
        return rel.replace("/", "\\")

    def _resolve(self, package_id: str, version: str, log, behavior: str,
                 installed: dict[str, str], plan: list[tuple[str, str]]) -> None:
        """Depth-first: dependencies (lowest applicable version) before the package."""
        key = package_id.lower()
        if any(p[0].lower() == key for p in plan):
            return
        folder = extract_package(self, package_id, version, log)
        meta = read_package_folder(folder)
        if behavior != "IgnoreDependencies":
            groups = {g.framework: g for g in meta.dependency_groups}
            best = nearest(self.framework, list(groups)) if groups else None
            deps = groups[best].dependencies if best is not None else []
            for d in deps:
                rng = VersionRange.parse(d.range)
                have = installed.get(d.id.lower())
                if have and rng.satisfies(have):
                    continue
                if any(p[0].lower() == d.id.lower() for p in plan):
                    continue
                vers = self.feed().versions(d.id)
                pick = pick_dependency_version(rng, vers, behavior)
                if not pick:
                    raise NuGetError(f"Unable to resolve dependency '{d.id} ({rng.pretty()})'.")
                log(f"Resolved dependency {d.id} {pick} ({rng.pretty()})")
                self._resolve(d.id, pick, log, behavior, installed, plan)
        plan.append((meta.id or package_id, meta.version or version))

    def _pc_install(self, package_id: str, version: str, log, behavior: str = "Lowest") -> None:
        installed = {p.id.lower(): p.version for p in read_packages_config(self.packages_config)}
        cur = installed.get(package_id.lower())
        if cur and NuGetVersion.try_parse(cur) != NuGetVersion.try_parse(version):
            self._pc_uninstall(package_id, log, keep_folder_check=True, check_dependents=False)
            self.reload()
            installed.pop(package_id.lower(), None)
        plan: list[tuple[str, str]] = []
        self._resolve(package_id, version, log, behavior, installed, plan)
        entries = read_packages_config(self.packages_config)
        fw = parse_tfm(self.framework).short()
        for pid, ver in plan:
            old = next((e for e in entries if e.id.lower() == pid.lower()), None)
            if old is not None and NuGetVersion.try_parse(old.version) == NuGetVersion.try_parse(ver):
                continue
            if old is not None:                     # a dependency moved up
                self._pc_uninstall(pid, log, keep_folder_check=True, check_dependents=False)
                self.reload()
                entries = [e for e in entries if e.id.lower() != pid.lower()]
            entries.append(InstalledPackage(pid, ver, target_framework=fw))
            self._pc_add_assets(pid, ver, log)
            log(f"Added package '{pid}.{ver}' to 'packages.config'")
        write_packages_config(self.packages_config, entries)
        if not self.ms.find_element("None", "packages.config") and not self.ms.find_element("Content",
                                                                                            "packages.config"):
            self.ms.add_item("None", "packages.config")
        self.ms.save()

    def _pc_add_assets(self, pid: str, ver: str, log) -> None:
        folder = self.packages_folder / f"{pid}.{ver}"
        dirname = folder.name
        lib = folder / "lib"
        if lib.is_dir():
            subs = [d.name for d in lib.iterdir() if d.is_dir()]
            root_dlls = [f for f in lib.glob("*.dll")]
            best = nearest(self.framework, subs) if subs else None
            dlls = sorted((lib / best).glob("*.dll")) if best else root_dlls
            if best is None and subs and not root_dlls:
                raise NuGetError(f"Could not install package '{pid} {ver}'. You are trying to install this package "
                                 f"into a project that targets '{parse_tfm(self.framework).display()}', but the "
                                 f"package does not contain any assembly references or content files that are "
                                 f"compatible with that framework.")
            idents = assembly_identities(dlls)
            for dll in dlls:
                hint = self._rel_to_packages(dirname, "lib", *( [best] if best else []), dll.name)
                include = idents.get(str(dll)) or dll.stem
                if any(_hint(i) == hint.lower() for i in self.ms.assembly_references):
                    continue
                self.ms.add_item("Reference", include, {"HintPath": hint})
                log(f"Added reference '{dll.stem}' to project '{self.name}'")
        nuspec = read_package_folder(folder)
        for asm, tfm in nuspec.framework_assemblies:
            if tfm and not nearest(self.framework, [tfm]):
                continue
            if asm and not any(MB.xml_unescape(i.include).split(",")[0].strip().lower() == asm.lower()
                               for i in self.ms.assembly_references):
                self.ms.add_item("Reference", asm)
                log(f"Added framework reference '{asm}'")
        build = folder / "build"
        if build.is_dir():
            subs = [d.name for d in build.iterdir() if d.is_dir()]
            best = nearest(self.framework, subs) if subs else None
            bdir = build / best if best else build
            for ext, top in ((".props", True), (".targets", False)):
                f = bdir / f"{pid}{ext}"
                if not f.is_file():
                    f = next((x for x in bdir.glob(f"*{ext}") if x.stem.lower() == pid.lower()), None)
                if f is not None and f.is_file():
                    rel = self._rel_to_packages(dirname, "build", *([best] if best else []), f.name)
                    add_build_import(self.ms, rel, top)
                    log(f"Imported {f.name} into '{self.name}'")
        content = folder / "content"
        if content.is_dir() and any(content.rglob("*")):
            log(f"Note: content files of '{pid}' are not copied into the project (copy them manually if needed).")

    def _pc_uninstall(self, package_id: str, log, keep_folder_check: bool = False, check_dependents: bool = True,
                      remove_dependencies: bool = False) -> None:
        entries = read_packages_config(self.packages_config)
        entry = next((e for e in entries if e.id.lower() == package_id.lower()), None)
        if entry is None:
            raise NuGetError(f"Package '{package_id}' is not installed in project '{self.name}'.")
        if check_dependents:
            for e in entries:
                if e is entry:
                    continue
                meta = read_package_folder(self.packages_folder / f"{e.id}.{e.version}")
                for g in meta.dependency_groups:
                    if any(d.id.lower() == package_id.lower() for d in g.dependencies):
                        raise NuGetError(f"Unable to uninstall '{entry.id}.{entry.version}' because "
                                         f"'{e.id}.{e.version}' depends on it.")
        dirname = f"{entry.id}.{entry.version}"
        dep_ids = [d.id for g in read_package_folder(self.packages_folder / dirname).dependency_groups
                   for d in g.dependencies] if remove_dependencies else []
        marker = ("packages\\" + dirname + "\\").lower()
        prefix = self._rel_to_packages(dirname).lower() + "\\"
        for it in list(self.ms.assembly_references):
            h = _hint(it)
            if h.startswith(prefix) or marker in h:
                self.ms.remove_item("Reference", it.include)
                log(f"Removed reference '{MB.xml_unescape(it.include).split(',')[0]}' from project '{self.name}'")
        remove_build_imports(self.ms, dirname)
        self.ms.save()
        entries = [e for e in entries if e is not entry]
        write_packages_config(self.packages_config, entries)
        if not entries and self.ms.remove_item("None", "packages.config"):
            self.ms.save()
        log(f"Removed package '{dirname}' from 'packages.config'")
        if not _package_used_elsewhere(self, entry.id, entry.version):
            shutil.rmtree(self.packages_folder / dirname, ignore_errors=True)
            log(f"Removing package '{dirname}' from folder '{self.packages_folder}'")
        for dep in dict.fromkeys(dep_ids):
            try:
                self.reload()
                self._pc_uninstall(dep, log, check_dependents=True, remove_dependencies=True)
            except NuGetError:
                continue


# ====================================================================== packages.config helpers
DEPENDENCY_BEHAVIORS = ("Lowest", "HighestPatch", "HighestMinor", "Highest", "IgnoreDependencies")


def pick_dependency_version(rng: VersionRange, versions: list[str], behavior: str = "Lowest") -> str:
    """NuGet's DependencyBehavior: Lowest (default), HighestPatch, HighestMinor, Highest."""
    low = rng.best_match(versions, lowest=True)
    if not low or behavior in ("Lowest", "IgnoreDependencies"):
        return low
    lv = NuGetVersion.parse(low)
    cands = [v for v in sort_versions(versions) if rng.satisfies(v) and not NuGetVersion.parse(v).is_prerelease]
    for v in cands:                                    # highest first
        n = NuGetVersion.parse(v)
        if behavior == "Highest" or (behavior == "HighestMinor" and n.major == lv.major) or                 (behavior == "HighestPatch" and (n.major, n.minor) == (lv.major, lv.minor)):
            return v
    return low


def read_packages_config(path: Path) -> list[InstalledPackage]:
    if not Path(path).is_file():
        return []
    try:
        root = ET.fromstring(Path(path).read_bytes())
    except ET.ParseError as e:
        raise NuGetError(f"{Path(path).name} is not valid XML: {e}") from None
    return [InstalledPackage(e.get("id", ""), e.get("version", ""), target_framework=e.get("targetFramework", ""))
            for e in root if e.tag == "package" and e.get("id")]


def write_packages_config(path: Path, entries: list[InstalledPackage]) -> None:
    path = Path(path)
    if not entries:
        if path.is_file():
            path.unlink()
        return
    nl = "\r\n"
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<packages>"]
    for e in sorted(entries, key=lambda e: e.id.lower()):
        tf = f' targetFramework="{MB.xml_escape(e.target_framework)}"' if e.target_framework else ""
        lines.append(f'  <package id="{MB.xml_escape(e.id)}" version="{MB.xml_escape(e.version)}"{tf} />')
    lines.append("</packages>")
    path.write_bytes(b"\xef\xbb\xbf" + (nl.join(lines) + nl).encode("utf-8"))


def _hint(item) -> str:
    return MB.xml_unescape(item.metadata.get("HintPath", "")).replace("/", "\\").lower()


def _plain(req: str) -> str:
    try:
        r = VersionRange.parse(req)
    except ValueError:
        return req
    return str(r.min) if r.min is not None else req


def _cli_error(out: str) -> str:
    errs = [ln.split("error:", 1)[-1].strip() for ln in out.splitlines() if "error" in ln.lower() and ":" in ln]
    errs = [e for e in errs if e and not e.lower().startswith("there were")]
    return "\n".join(dict.fromkeys(errs))[:2000]


def _package_used_elsewhere(project: NuGetProject, pid: str, ver: str) -> bool:
    for cfg in project.solution_folder.rglob("packages.config"):
        if any(part in ("packages", "bin", "obj", "node_modules", ".git") for part in cfg.relative_to(
                project.solution_folder).parts[:-1]):
            continue
        if cfg.resolve() == project.packages_config.resolve():
            continue
        try:
            if any(e.id.lower() == pid.lower() and e.version == ver for e in read_packages_config(cfg)):
                return True
        except NuGetError:
            continue
    return False


def read_package_folder(folder: Path):
    """Metadata of an extracted package (packages/Id.Version/*.nuspec or the .nupkg inside)."""
    folder = Path(folder)
    spec = next(iter(folder.glob("*.nuspec")), None)
    try:
        if spec is not None:
            return parse_nuspec(spec.read_bytes())
        pkg = next(iter(folder.glob("*.nupkg")), None)
        if pkg is not None:
            return parse_nuspec(nuspec_from_nupkg(pkg))
    except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile):
        pass
    return PackageMetadata("", "")


def obtain_nupkg(project: NuGetProject, package_id: str, version: str, log=_noop) -> Path:
    """A .nupkg file for id/version: the global packages folder, the RAD IDE cache, or a download."""
    v = NuGetVersion.parse(version).normalized().lower()
    gp = global_packages_folder(project.solution_folder) / package_id.lower() / v / f"{package_id.lower()}.{v}.nupkg"
    if gp.is_file():
        return gp
    cache = http.cache_root() / "nupkg" / f"{package_id.lower()}.{v}.nupkg"
    if cache.is_file() and zipfile.is_zipfile(cache):
        return cache
    log(f"Downloading {package_id} {version} ...")
    project.feed().download(package_id, version, cache)
    if not zipfile.is_zipfile(cache):
        cache.unlink(missing_ok=True)
        raise NuGetError(f"The downloaded {package_id} {version} package is not a valid .nupkg.")
    return cache


def extract_package(project: NuGetProject, package_id: str, version: str, log=_noop) -> Path:
    """packages/Id.Version/ like nuget.exe (the .nupkg is kept next to its content)."""
    base = project.packages_folder
    for d in (base.glob(f"{package_id}.*") if base.is_dir() else []):
        if d.is_dir() and d.name.lower() == f"{package_id}.{version}".lower():
            return d
    nupkg = obtain_nupkg(project, package_id, version, log)
    meta = parse_nuspec(nuspec_from_nupkg(nupkg))
    target = base / f"{meta.id or package_id}.{meta.version or version}"
    tmp = target.with_name(target.name + ".tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(nupkg) as z:
        for info in z.infolist():
            n = info.filename.replace("\\", "/")
            if n.startswith(("_rels/", "package/")) or n == "[Content_Types].xml" or n.endswith("/") or \
                    n.lower().endswith(".psmdcp"):
                continue
            dest = (tmp / n).resolve()
            if not str(dest).startswith(str(tmp.resolve())):
                continue                                    # zip-slip
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    shutil.copy2(nupkg, tmp / f"{target.name}.nupkg")
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    os.replace(tmp, target)
    log(f"Added package '{target.name}' to folder '{base}'")
    return target


def restore_packages_config(project: NuGetProject, log=_noop) -> bool:
    entries = read_packages_config(project.packages_config)
    missing = [e for e in entries if not (project.packages_folder / f"{e.id}.{e.version}").is_dir()]
    if not missing:
        log(f"All packages listed in {project.packages_config.name} are already installed.")
        return True
    failed = []
    for e in missing:
        try:
            extract_package(project, e.id, e.version, log)
        except Exception as ex:  # noqa: BLE001
            failed.append((e, ex))
    if failed:
        log(f"{len(failed)} package(s) could not be restored by RAD IDE: trying nuget.exe ...")
        try:
            exe = ensure_nuget_exe(log)
            code, _ = run([exe, "restore", str(project.packages_config), "-PackagesDirectory",
                           str(project.packages_folder), "-NonInteractive"], project.folder, log)
            return code == 0
        except Exception as ex:  # noqa: BLE001
            for e, err in failed:
                log(f"Unable to restore '{e.id} {e.version}': {err}")
            log(f"nuget.exe: {ex}")
            return False
    return True


def assembly_identities(dlls: list[Path]) -> dict[str, str]:
    """Full assembly names ('X, Version=..., Culture=neutral, PublicKeyToken=..., processorArchitecture=MSIL')
    like Visual Studio writes in <Reference Include>; {} when they cannot be read."""
    if not dlls or os.name != "nt":
        return {}
    script = ("$ErrorActionPreference='SilentlyContinue';" + "".join(
        f"try{{$n=[System.Reflection.AssemblyName]::GetAssemblyName('{str(d).replace(chr(39), chr(39) * 2)}');"
        f"Write-Output ('{i}|'+$n.FullName+'|'+$n.ProcessorArchitecture)}}catch{{}};" for i, d in enumerate(dlls)))
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True,
                             timeout=60, creationflags=NO_WINDOW).stdout.decode("utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return {}
    res = {}
    for line in out.splitlines():
        parts = line.strip().split("|")
        if len(parts) == 3 and parts[0].isdigit() and int(parts[0]) < len(dlls) and parts[1]:
            arch = {"MSIL": "MSIL", "X86": "x86", "Amd64": "AMD64", "Arm": "ARM"}.get(parts[2], "")
            res[str(dlls[int(parts[0])])] = parts[1] + (f", processorArchitecture={arch}" if arch else "")
    return res


# ---------------------------------------------------------------- build imports (packages.config)
def add_build_import(ms: MB.MSBuildProject, rel: str, top: bool) -> bool:
    text, nl = ms.file.text, ms.file.newline
    if rel.lower() in text.lower():
        return False
    unit = ms._indent_unit()
    esc = MB.xml_escape(rel)
    line = f"{unit}<Import Project=\"{esc}\" Condition=\"Exists('{esc}')\" />"
    if top:
        m = re.search(r"<Project\b[^>]*>[ \t]*\r?\n", text)
        at = m.end() if m else 0
        ms.file.text = text[:at] + line + nl + text[at:]
    else:
        m = list(re.finditer(r"<Import\b[^>]*Project\s*=\s*\"[^\"]*Microsoft\.(?:CSharp|VisualBasic|FSharp)"
                             r"\.targets\"[^>]*/>[ \t]*\r?\n", text))
        if m:
            at = m[-1].end()
        else:
            close = text.rfind("</Project>")
            at = ms._line_start(close) if close >= 0 else len(text)
        ms.file.text = text[:at] + line + nl + text[at:]
        _ensure_target_add(ms, rel)
    ms.parse()
    return True


def _ensure_target_add(ms: MB.MSBuildProject, rel: str) -> None:
    text, nl, unit = ms.file.text, ms.file.newline, ms._indent_unit()
    esc = MB.xml_escape(rel)
    err = (f"{unit * 2}<Error Condition=\"!Exists('{esc}')\" "
           f"Text=\"$([System.String]::Format('$(ErrorText)', '{esc}'))\" />")
    m = re.search(rf"<Target\s+Name=\"{ENSURE_TARGET}\"[^>]*>.*?</Target>", text, re.S)
    if m:
        block = m.group(0)
        close = block.rfind("</Target>")
        ls = block.rfind("\n", 0, close) + 1
        new = block[:ls] + err + nl + block[ls:]
        ms.file.text = text[:m.start()] + new + text[m.end():]
        return
    block = (f"{unit}<Target Name=\"{ENSURE_TARGET}\" BeforeTargets=\"PrepareForBuild\">{nl}"
             f"{unit * 2}<PropertyGroup>{nl}"
             f"{unit * 3}<ErrorText>{MB.xml_escape(ENSURE_TEXT)}</ErrorText>{nl}"
             f"{unit * 2}</PropertyGroup>{nl}{err}{nl}{unit}</Target>{nl}")
    close = text.rfind("</Project>")
    at = ms._line_start(close) if close >= 0 else len(text)
    ms.file.text = text[:at] + block + text[at:]


def remove_build_imports(ms: MB.MSBuildProject, package_dir: str) -> int:
    """Remove the Import lines and Ensure... Error lines pointing into packages/<package_dir>/."""
    text = ms.file.text
    pat = re.escape("packages\\" + package_dir + "\\")
    n = 0
    for rx in (rf"[ \t]*<Import\b[^>]*Project=\"[^\"]*{pat}[^\"]*\"[^>]*/>[ \t]*\r?\n",
               rf"[ \t]*<Error\b[^>]*Condition=\"!Exists\('[^']*{pat}[^']*'\)\"[^>]*/>[ \t]*\r?\n"):
        text, k = re.subn(rx, "", text, flags=re.I)
        n += k
    m = re.search(rf"[ \t]*<Target\s+Name=\"{ENSURE_TARGET}\"[^>]*>(.*?)</Target>[ \t]*\r?\n?", text, re.S)
    if m and not re.search(r"<Error\b", m.group(1)):
        text = text[:m.start()] + text[m.end():]
    if n:
        ms.file.text = text
        ms.parse()
    return n


# ====================================================================== solution level
def updates(projects: list[NuGetProject], feed: Feed, prerelease: bool = False) -> dict[str, tuple[str, list]]:
    """{id: (latest version, [(project, installed version)])} for installed packages with a newer version."""
    by_id: dict[str, list] = {}
    names: dict[str, str] = {}
    for p in projects:
        for ip in p.installed():
            by_id.setdefault(ip.id.lower(), []).append((p, ip.version))
            names.setdefault(ip.id.lower(), ip.id)
    out = {}
    for key, rows in by_id.items():
        try:
            vers = feed.versions(names[key])
        except Exception:  # noqa: BLE001
            continue
        allow_pre = prerelease or any(NuGetVersion.try_parse(v) and NuGetVersion.parse(v).is_prerelease
                                      for _p, v in rows)
        cands = [v for v in sort_versions(vers) if allow_pre or not NuGetVersion.parse(v).is_prerelease]
        if not cands:
            continue
        top = cands[0]
        if any(NuGetVersion.try_parse(v) is not None and NuGetVersion.parse(top) > NuGetVersion.parse(v)
               for _p, v in rows):
            out[names[key]] = (top, rows)
    return out


def consolidation(projects: list[NuGetProject]) -> dict[str, list]:
    """{id: [(project, version)]} for packages installed with different versions across projects."""
    by_id: dict[str, list] = {}
    names: dict[str, str] = {}
    for p in projects:
        for ip in p.installed():
            by_id.setdefault(ip.id.lower(), []).append((p, ip.version))
            names.setdefault(ip.id.lower(), ip.id)
    return {names[k]: rows for k, rows in by_id.items()
            if len({NuGetVersion.try_parse(v) for _p, v in rows}) > 1}


def restore_all(projects: list[NuGetProject], solution_file: Path | None = None, log=_noop) -> bool:
    ok = True
    pr = [p for p in projects if p.style != STYLE_PC]
    pc = [p for p in projects if p.style == STYLE_PC]
    for p in pc:
        ok = restore_packages_config(p, log) and ok
    if pr:
        dn = MB.find_dotnet()
        if solution_file is not None and dn and all(p.ms.is_sdk for p in pr):
            code, _ = run([dn, "restore", str(solution_file)], Path(solution_file).parent, log)
            ok = ok and code == 0
        else:
            for p in pr:
                try:
                    ok = p.restore(log) and ok
                except NuGetError as e:
                    log(str(e))
                    ok = False
    log("Restore completed." if ok else "Restore failed - see the messages above.")
    return ok


def clear_local_caches(log=_noop) -> None:
    """Tools > Options > NuGet > General > Clear All NuGet Storage: dotnet nuget locals all --clear + our cache."""
    dn = MB.find_dotnet()
    if dn:
        run([dn, "nuget", "locals", "all", "--clear"], None, log)
    shutil.rmtree(http.cache_root(), ignore_errors=True)
    log("RAD IDE NuGet cache cleared.")


__all__ = ["NuGetProject", "InstalledPackage", "NuGetError", "read_packages_config", "write_packages_config",
           "restore_packages_config", "restore_all", "updates", "consolidation", "ensure_nuget_exe", "run",
           "assembly_identities", "run_retry", "add_build_import", "remove_build_imports", "clear_local_caches", "default_format",
           "STYLE_PR", "STYLE_CPM", "STYLE_PC", "DEPENDENCY_BEHAVIORS", "pick_dependency_version"]
