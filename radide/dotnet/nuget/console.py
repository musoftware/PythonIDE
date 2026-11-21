"""Package Manager Console commands (no Qt): the NuGet PowerShell cmdlets mapped onto our backends.

Visual Studio's console is a PowerShell host with the NuGet module loaded. RAD IDE has no PowerShell
host; ``ConsoleEngine.execute(line)`` parses the same command lines (PowerShell-style parameters,
unique prefixes, positional Id, switches) and runs them through ``projects.NuGetProject`` / ``feed``:

    Install-Package <Id> [-Version v] [-ProjectName p] [-Source s] [-IncludePrerelease] [-IgnoreDependencies]
    Uninstall-Package <Id> [-ProjectName p] [-Version v] [-RemoveDependencies] [-Force]
    Update-Package [<Id>] [-ProjectName p] [-Version v] [-Source s] [-IncludePrerelease] [-Safe] [-Reinstall]
    Get-Package [-Filter f] [-ProjectName p] [-ListAvailable] [-Updates] [-Source s] [-IncludePrerelease] [-First n] [-Skip n]
    Find-Package [<Id>] [-ExactMatch] [-AllVersions] [-First n] [-Source s] [-IncludePrerelease]
    Get-Project [-Name n] [-All]
    Restore-Package [-ProjectName p]        (Visual Studio restores on build; offered here as a command)
    Clear-Host / cls, Get-Help [<command>], dotnet <args> (runs the .NET CLI in the solution folder)

``complete(line)`` returns tab completions: cmdlets, parameters, project names, package ids (search
autocomplete endpoint) and versions. Output goes through ``write`` callbacks line by line.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Callable

from .config import PackageSource, enabled_sources
from .feed import Feed, feed_for
from .projects import NuGetError, NuGetProject, run
from .versions import NuGetVersion, VersionRange, sort_versions

# cmdlet -> (positional parameter names, {parameter: takes a value?})
COMMON = {"ProjectName": True, "Source": True, "IncludePrerelease": False}
COMMANDS: dict[str, tuple[list, dict]] = {
    "Install-Package": (["Id"], {"Id": True, "Version": True, "IgnoreDependencies": False, "DependencyVersion": True,
                                 "FileConflictAction": True, "WhatIf": False, **COMMON}),
    "Uninstall-Package": (["Id"], {"Id": True, "Version": True, "ProjectName": True, "RemoveDependencies": False,
                                   "Force": False, "WhatIf": False}),
    "Update-Package": (["Id"], {"Id": True, "Version": True, "Safe": False, "Reinstall": False,
                                "IgnoreDependencies": False, "WhatIf": False, **COMMON}),
    "Get-Package": (["Filter"], {"Filter": True, "ListAvailable": False, "Updates": False, "AllVersions": False,
                                 "First": True, "Skip": True, "PageSize": True, **COMMON}),
    "Find-Package": (["Id"], {"Id": True, "Version": True, "ExactMatch": False, "AllVersions": False, "First": True,
                              "StartWith": False, "Source": True, "IncludePrerelease": False}),
    "Get-Project": (["Name"], {"Name": True, "All": False}),
    "Restore-Package": ([], {"ProjectName": True}),
    "Clear-Host": ([], {}),
    "Get-Help": (["Name"], {"Name": True}),
}
ALIASES = {"cls": "Clear-Host", "clear": "Clear-Host", "help": "Get-Help", "man": "Get-Help"}
HELP = {
    "Install-Package": "Installs a package and its dependencies into a project.",
    "Uninstall-Package": "Removes a package from a project, optionally removing its dependencies.",
    "Update-Package": "Updates a package and its dependencies, or all packages, to a newer version.",
    "Get-Package": "Retrieves the list of installed packages, or packages available from a source.",
    "Find-Package": "Gets the set of remote packages with the specified Id or keywords from the source.",
    "Get-Project": "Displays information about the default or specified project.",
    "Restore-Package": "Restores the NuGet packages of a project, or of every project in the solution.",
    "Clear-Host": "Clears the console.",
    "Get-Help": "Displays help about a command.",
}


class ConsoleError(Exception):
    pass


@dataclass
class Parsed:
    command: str
    args: dict = field(default_factory=dict)       # parameter -> value (True for switches)


def tokenize(line: str) -> list[str]:
    try:
        lex = shlex.shlex(line, posix=True)
        lex.whitespace_split = True
        lex.commenters = "#"
        lex.escape = "`"                             # PowerShell's escape character
        return list(lex)
    except ValueError as e:
        raise ConsoleError(f"The string is missing the terminator: {e}") from None


def resolve_command(name: str) -> str:
    low = name.lower()
    if low in ALIASES:
        return ALIASES[low]
    for c in COMMANDS:
        if c.lower() == low:
            return c
    raise ConsoleError(f"The term '{name}' is not recognized as the name of a cmdlet, function, script file, or "
                       f"operable program. Check the spelling of the name, or if a path was included, verify that "
                       f"the path is correct and try again.")


def resolve_param(command: str, name: str) -> str:
    params = COMMANDS[command][1]
    low = name.lower()
    exact = [p for p in params if p.lower() == low]
    if exact:
        return exact[0]
    hits = [p for p in params if p.lower().startswith(low)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ConsoleError(f"{command} : A parameter cannot be found that matches parameter name '{name}'.")
    raise ConsoleError(f"{command} : Parameter cannot be processed because the parameter name '{name}' is ambiguous. "
                       f"Possible matches include: {', '.join('-' + h for h in hits)}.")


def parse(line: str) -> Parsed | None:
    toks = tokenize(line)
    if not toks:
        return None
    cmd = resolve_command(toks[0])
    positional, params = COMMANDS[cmd]
    out = Parsed(cmd)
    pos = list(positional)
    i = 1
    while i < len(toks):
        t = toks[i]
        if t.startswith("-") and len(t) > 1 and not re.fullmatch(r"-\d[\d.]*", t):
            name, _, inline = t[1:].partition(":")
            p = resolve_param(cmd, name)
            if params[p]:
                if inline:
                    val = inline
                else:
                    i += 1
                    if i >= len(toks):
                        raise ConsoleError(f"{cmd} : Missing an argument for parameter '{p}'. Specify a parameter "
                                           f"of type 'System.String' and try again.")
                    val = toks[i]
                out.args[p] = val
            else:
                out.args[p] = inline.lower() not in ("$false", "false", "0") if inline else True
        else:
            while pos and pos[0] in out.args:
                pos.pop(0)
            if not pos:
                raise ConsoleError(f"{cmd} : A positional parameter cannot be found that accepts argument '{t}'.")
            out.args[pos.pop(0)] = t
        i += 1
    return out


def table(rows: list[tuple], headers: tuple, widths: tuple | None = None) -> list[str]:
    """PowerShell Format-Table style lines."""
    if not widths:
        widths = tuple(max([len(str(h))] + [len(str(r[i])) for r in rows]) for i, h in enumerate(headers))
        widths = tuple(min(w, 60) for w in widths)

    def fit(s, w, last):
        s = str(s)
        if last:
            return s
        return (s[:w - 3] + "...") if len(s) > w else s.ljust(w)

    n = len(headers)
    out = [" ".join(fit(h, widths[i], i == n - 1) for i, h in enumerate(headers)),
           " ".join(fit("-" * len(h), widths[i], i == n - 1) for i, h in enumerate(headers))]
    for r in rows:
        out.append(" ".join(fit(r[i], widths[i], i == n - 1) for i in range(n)).rstrip())
    return out


class ConsoleEngine:
    """projects(): the solution's NuGetProject list; default_project: name of the Default project combo."""

    def __init__(self, projects: Callable[[], list], write: Callable[[str], None] = print,
                 solution_folder=None, solution_file=None):
        self._projects = projects
        self.write = write
        self.error = write
        self.solution_folder = solution_folder
        self.solution_file = solution_file
        self.default_project = ""
        self.source = ""                      # Package source combo ("All" / a source name)
        self.clear: Callable[[], None] = lambda: None

    # ------------------------------------------------------------ context
    def projects(self) -> list[NuGetProject]:
        return list(self._projects() or [])

    def project(self, name: str = "") -> NuGetProject:
        projs = self.projects()
        if not projs:
            raise ConsoleError("Solution is not opened, or it has no project that supports NuGet packages.")
        name = name or self.default_project
        if not name:
            return projs[0]
        for p in projs:
            if p.name.lower() == name.lower():
                return p
        raise ConsoleError(f"Project '{name}' is not found.")

    def targets(self, args: dict, all_when_missing: bool = False) -> list[NuGetProject]:
        if args.get("ProjectName"):
            return [self.project(n.strip()) for n in str(args["ProjectName"]).split(",") if n.strip()]
        if all_when_missing:
            return self.projects()
        return [self.project()]

    def sources_for(self, args: dict) -> list[PackageSource] | None:
        name = str(args.get("Source") or self.source or "")
        if not name or name.lower() == "all":
            return None
        for s in enabled_sources(self.solution_folder):
            if s.name.lower() == name.lower() or s.url.lower() == name.lower():
                return [s]
        return [PackageSource(name, name)]          # a URL or folder typed on the command line

    def feed(self, args: dict) -> Feed:
        src = self.sources_for(args)
        if src:
            return feed_for(src[0])
        projs = self.projects()
        if projs:
            return projs[0].feed()
        from .feed import AggregateFeed
        feeds = [feed_for(s) for s in enabled_sources(self.solution_folder)]
        return feeds[0] if len(feeds) == 1 else AggregateFeed(feeds)

    def _with_sources(self, p: NuGetProject, args: dict):
        src = self.sources_for(args)
        old = p._sources
        if src:
            p._sources = src
        return old

    # ------------------------------------------------------------ run
    def execute(self, line: str) -> bool:
        """Run one command line. Returns False when it failed (the error is written)."""
        line = line.strip()
        if not line:
            return True
        if re.match(r"^dotnet(\.exe)?\s", line, re.I) or line.lower() in ("dotnet", "dotnet.exe"):
            return self._dotnet(line)
        try:
            parsed = parse(line)
            if parsed is None:
                return True
            fn = getattr(self, "cmd_" + parsed.command.replace("-", "_").lower())
            fn(parsed.args)
            return True
        except (ConsoleError, NuGetError) as e:
            self.error(str(e))
        except Exception as e:  # noqa: BLE001 - network and file errors are shown like NuGet does
            self.error(f"{type(e).__name__}: {e}")
        return False

    def _dotnet(self, line: str) -> bool:
        from ...foreign import msbuild as MB
        dn = MB.find_dotnet()
        if not dn:
            self.error("The .NET SDK (dotnet) was not found.")
            return False
        argv = [dn] + tokenize(line)[1:]
        code, _ = run(argv, self.solution_folder, self.write)
        return code == 0

    # ------------------------------------------------------------ cmdlets
    def cmd_clear_host(self, args):
        self.clear()

    def cmd_get_help(self, args):
        name = args.get("Name")
        if name:
            cmd = resolve_command(name)
            self.write("NAME")
            self.write(f"    {cmd}")
            self.write("")
            self.write("SYNOPSIS")
            self.write(f"    {HELP.get(cmd, '')}")
            self.write("")
            self.write("SYNTAX")
            pos, params = COMMANDS[cmd]
            parts = [f"[-{p}] <string>" if p in pos else (f"[-{p} <string>]" if v else f"[-{p}]")
                     for p, v in params.items()]
            self.write(f"    {cmd} " + " ".join(parts))
            return
        self.write("Package Manager Console commands:")
        for c, h in HELP.items():
            self.write(f"  {c.ljust(20)} {h}")
        self.write("  dotnet <args>        Runs the .NET CLI in the solution folder.")
        self.write("Type 'Get-Help <command>' for the parameters of a command. Tab completes commands, "
                   "parameters, projects and package ids.")

    def cmd_get_project(self, args):
        projs = self.projects() if args.get("All") else [self.project(args.get("Name", ""))]
        rows = [(p.name, "C#" if p.path.suffix == ".csproj" else ("VB" if p.path.suffix == ".vbproj" else "F#"),
                 str(p.path)) for p in projs]
        for ln in table(rows, ("ProjectName", "Type", "FullName")):
            self.write(ln)

    def cmd_restore_package(self, args):
        from .projects import restore_all
        restore_all(self.targets(args, all_when_missing=True), self.solution_file if not args.get("ProjectName")
                    else None, self.write)

    def cmd_install_package(self, args):
        pid = args.get("Id")
        if not pid:
            raise ConsoleError("Install-Package : Cannot bind argument to parameter 'Id' because it is an empty string.")
        for p in self.targets(args):
            if args.get("WhatIf"):
                self.write(f"What if: install '{pid}' {args.get('Version', '(latest)')} into '{p.name}'.")
                continue
            old = self._with_sources(p, args)
            try:
                ver = self._version_arg(p, pid, args)
                p.install(pid, ver, self.write, prerelease=bool(args.get("IncludePrerelease")),
                          ignore_dependencies=bool(args.get("IgnoreDependencies")))
            finally:
                p._sources = old

    def _version_arg(self, p: NuGetProject, pid: str, args: dict) -> str:
        v = str(args.get("Version") or "")
        if not v:
            return ""
        if NuGetVersion.try_parse(v) is not None:
            return v
        rng = VersionRange.parse(v)                 # -Version "[1.0,2.0)"
        best = rng.best_match(p.feed().versions(pid), bool(args.get("IncludePrerelease")), lowest=False)
        if not best:
            raise ConsoleError(f"Unable to find a version of '{pid}' that satisfies {v}.")
        return best

    def cmd_uninstall_package(self, args):
        pid = args.get("Id")
        if not pid:
            raise ConsoleError("Uninstall-Package : Cannot bind argument to parameter 'Id' because it is an empty "
                               "string.")
        for p in self.targets(args):
            if args.get("WhatIf"):
                self.write(f"What if: uninstall '{pid}' from '{p.name}'.")
                continue
            p.uninstall(pid, self.write, remove_dependencies=bool(args.get("RemoveDependencies")),
                        force=bool(args.get("Force")))

    def cmd_update_package(self, args):
        pid = args.get("Id")
        projs = self.targets(args, all_when_missing=True)
        pre = bool(args.get("IncludePrerelease"))
        did = False
        for p in projs:
            pkgs = [ip for ip in p.installed() if not pid or ip.id.lower() == str(pid).lower()]
            if pid and not pkgs and args.get("ProjectName"):
                raise ConsoleError(f"'{pid}' was not installed in any project. Update failed.")
            old = self._with_sources(p, args)
            try:
                for ip in pkgs:
                    did = True
                    if args.get("Reinstall"):
                        p.uninstall(ip.id, self.write, force=True)
                        p.install(ip.id, ip.version, self.write)
                        continue
                    target = self._version_arg(p, ip.id, args)
                    if not target and args.get("Safe"):    # highest patch of the same major.minor
                        cur = NuGetVersion.parse(ip.version)
                        cands = [v for v in sort_versions(p.feed().versions(ip.id))
                                 if (NuGetVersion.parse(v).major, NuGetVersion.parse(v).minor) == (cur.major, cur.minor)
                                 and (pre or not NuGetVersion.parse(v).is_prerelease)]
                        target = cands[0] if cands else ip.version
                    if args.get("WhatIf"):
                        self.write(f"What if: update '{ip.id}' {ip.version} -> {target or '(latest)'} in '{p.name}'.")
                        continue
                    p.update(ip.id, target, self.write, prerelease=pre)
            finally:
                p._sources = old
        if pid and not did:
            raise ConsoleError(f"'{pid}' was not installed in any project. Update failed.")
        if not pid and not did:
            self.write("No packages are installed.")

    def cmd_get_package(self, args):
        first = int(args.get("First") or args.get("PageSize") or 0)
        skip = int(args.get("Skip") or 0)
        flt = str(args.get("Filter") or "")
        pre = bool(args.get("IncludePrerelease"))
        if args.get("ListAvailable"):
            rows, _n = self.feed(args).search(flt, pre, skip, first or 50)
            lines = table([(r.id, ("{" + ", ".join(r.version_list[-1:][::-1] or [r.version]) + "}"),
                            (r.description or "").replace("\n", " ")) for r in rows],
                          ("Id", "Versions", "Description"), (35, 25, 60))
            for ln in lines:
                self.write(ln)
            return
        projs = self.targets(args, all_when_missing=True)
        out = []
        if args.get("Updates"):
            from .projects import updates
            feed = self.feed(args)
            for pid, (top, rows) in sorted(updates(projs, feed, pre).items(), key=lambda kv: kv[0].lower()):
                if flt and flt.lower() not in pid.lower():
                    continue
                for p, ver in rows:
                    if NuGetVersion.try_parse(ver) is not None and NuGetVersion.parse(top) > NuGetVersion.parse(ver):
                        out.append((pid, "{" + top + "}", p.name))
        else:
            for p in projs:
                for ip in p.installed():
                    if flt and flt.lower() not in ip.id.lower():
                        continue
                    out.append((ip.id, "{" + ip.version + "}", p.name))
        out = out[skip:]
        if first:
            out = out[:first]
        if not out:
            self.write("No packages installed." if not args.get("Updates") else "No package updates are available "
                       "from the current package source.")
            return
        for ln in table(out, ("Id", "Versions", "ProjectName"), (35, 40, 30)):
            self.write(ln)

    def cmd_find_package(self, args):
        pid = str(args.get("Id") or "")
        pre = bool(args.get("IncludePrerelease"))
        first = int(args.get("First") or 20)
        feed = self.feed(args)
        if args.get("ExactMatch") and pid:
            vers = [v for v in feed.versions(pid) if pre or not NuGetVersion.parse(v).is_prerelease]
            if not vers:
                self.write(f"No package with the Id '{pid}' was found.")
                return
            meta = feed.metadata(pid, vers[0])
            shown = vers if args.get("AllVersions") else vers[:1]
            for ln in table([(pid, "{" + ", ".join(shown) + "}", (meta.description if meta else "").replace("\n", " "))],
                            ("Id", "Versions", "Description"), (35, 25, 60)):
                self.write(ln)
            return
        rows, _n = feed.search(pid, pre, 0, first)
        if args.get("StartWith"):
            rows = [r for r in rows if r.id.lower().startswith(pid.lower())]
        out = []
        for r in rows:
            vers = sort_versions(r.version_list) if args.get("AllVersions") else [r.version]
            out.append((r.id, "{" + ", ".join(vers) + "}", (r.description or "").replace("\n", " ")))
        for ln in table(out, ("Id", "Versions", "Description"), (35, 25, 60)):
            self.write(ln)

    # ------------------------------------------------------------ tab completion
    def complete(self, line: str) -> list[str]:
        """Completions for the last word of `line` (each a full replacement for that word)."""
        m = re.search(r"(\S*)$", line)
        word = m.group(1) if m else ""
        head = line[:len(line) - len(word)]
        try:
            toks = tokenize(head)
        except ConsoleError:
            return []
        if not toks:
            names = list(COMMANDS) + list(ALIASES) + ["dotnet"]
            return sorted(n for n in names if n.lower().startswith(word.lower()))
        try:
            cmd = resolve_command(toks[0])
        except ConsoleError:
            return []
        positional, params = COMMANDS[cmd]
        if word.startswith("-"):
            return ["-" + p for p in params if p.lower().startswith(word[1:].lower())]
        prev = toks[-1] if len(toks) > 1 else ""
        param = ""
        if prev.startswith("-"):
            try:
                param = resolve_param(cmd, prev[1:])
            except ConsoleError:
                return []
            if not params[param]:
                param = ""
        if not param:
            used = set()
            i = 1
            while i < len(toks):
                if toks[i].startswith("-"):
                    try:
                        p = resolve_param(cmd, toks[i][1:])
                        if params[p]:
                            i += 1
                    except ConsoleError:
                        pass
                else:
                    used.add(i)
                i += 1
            if not used and positional:
                param = positional[0]
        if param == "ProjectName" or param == "Name" and cmd == "Get-Project":
            return [p.name for p in self.projects() if p.name.lower().startswith(word.lower())]
        if param == "Source":
            return [s.name if " " not in s.name else f"'{s.name}'" for s in enabled_sources(self.solution_folder)
                    if s.name.lower().startswith(word.strip("'\"").lower())]
        if param == "Name" and cmd == "Get-Help":
            return [c for c in COMMANDS if c.lower().startswith(word.lower())]
        pre = any(t.lower().startswith("-includep") for t in toks)
        if param == "Id" or (param == "Filter" and cmd == "Get-Package"):
            if cmd in ("Uninstall-Package", "Update-Package") or (cmd == "Get-Package"
                                                                  and not any(t.lower().startswith("-l") for t in toks)):
                ids = {ip.id for p in self.projects() for ip in p.installed()}
                return sorted(i for i in ids if i.lower().startswith(word.lower()))
            if not word:
                return []
            try:
                return self.feed({}).autocomplete(word, pre, 20)
            except Exception:  # noqa: BLE001 - offline
                return []
        if param == "Version":
            pid = ""
            for i, t in enumerate(toks[1:], 1):
                if not t.startswith("-") and not (i > 1 and toks[i - 1].lower().startswith(("-v", "-p", "-s"))):
                    pid = t
                    break
            if not pid:
                return []
            try:
                vers = [v for v in sort_versions(self.feed({}).versions(pid))
                        if pre or not NuGetVersion.parse(v).is_prerelease]
            except Exception:  # noqa: BLE001
                return []
            return [v for v in vers if v.startswith(word)]
        return []


__all__ = ["ConsoleEngine", "ConsoleError", "parse", "tokenize", "table", "COMMANDS", "ALIASES", "HELP"]
