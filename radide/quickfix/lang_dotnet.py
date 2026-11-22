"""C# / VB.NET quick fixes.

Real projects (.csproj / .vbproj, loose files): the type index of the assemblies the project compiles against
(radide/dotnet/tools/metadata.py, read from the installed .NET SDK's reference assemblies) -> "using X;" /
"Imports X" / fully qualified name; a type of another project of the solution -> "Add reference to 'Y'"; a
well-known package type -> "Install package 'Z'"; else "Search NuGet.org for 'T'..." (radide/dotnet/tools/
quickfix.py has the rules, this module turns them into Actions with previews). Without an SDK a static table of
the common BCL / WinForms / WPF types is used.

RAD C# projects (GUI Bridge, project.radproj + _build/csharp/RadApp.csproj): the IDE draws the form and the
program is a console process, so WinForms / WPF types are not referenced. ``MessageBox.Show("Hi")`` ->
"Use the RAD helper MsgBox(...)" (Rad.cs: ``global using static Rad``: MsgBox, InputBox, End ...), and the
"using System.Windows.Forms;" entry is shown greyed out with the reason. NuGet packages go into
_build/csharp/RadApp.csproj (the project's NuGet manifest, same as Project > Packages).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import Action, Context, qualified_before, rad_project_folder, register
from . import installers
from .tables import CS_TYPES, CS_WPF_ALTERNATIVES, RAD_CS_EQUIVALENTS

WINDOWS_NS = ("System.Windows", "System.Drawing", "Microsoft.VisualBasic")
RAD_IMPLICIT = {"System", "System.Collections.Generic", "System.IO", "System.Linq", "System.Net.Http",
                "System.Threading", "System.Threading.Tasks"}
_NUGET_CACHE: dict[str, list] = {}


def _dq():
    from ..dotnet.tools import quickfix as dq
    return dq


def rad_csharp(ctx: Context) -> Path | None:
    """The RAD project folder when ctx is a C# file of a GUI Bridge project."""
    if ctx.language != "csharp":
        return None
    folder = rad_project_folder(ctx.path)
    if folder is None:
        return None
    if ctx.plugin_id == "csharp-bridge":
        return folder
    try:
        lang = json.loads((folder / "project.radproj").read_text(encoding="utf-8")).get("language", "")
    except (OSError, ValueError, AttributeError):
        lang = ""
    return folder if lang == "csharp-bridge" else None


def _rad_csproj(folder: Path) -> Path:
    return Path(folder) / "_build" / "csharp" / "RadApp.csproj"


def _name_pos(ctx: Context, name: str) -> tuple[int, int] | None:
    if ctx.word == name:
        return ctx.wstart, ctx.wend
    m = re.search(rf"(?<![\w.]){re.escape(name)}\b", ctx.line_text)
    return (m.start(), m.end()) if m else None


def _call_args(s: str, open_at: int) -> tuple[list[str], int] | None:
    """Top-level arguments of the call whose "(" is at s[open_at] and the index after ")"."""
    depth, cur, args, i, quote = 0, "", [], open_at, ""
    while i < len(s):
        ch = s[i]
        if quote:
            cur += ch
            if ch == "\\" and quote == '"' and i + 1 < len(s):
                cur += s[i + 1]
                i += 1
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            cur += ch
        elif ch in "([{":
            depth += 1
            if depth > 1:
                cur += ch
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                if cur.strip():
                    args.append(cur.strip())
                return args, i + 1
            cur += ch
        elif ch == "," and depth == 1:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    return None


def rad_helper_action(ctx: Context, name: str) -> Action | None:
    helper, call = RAD_CS_EQUIVALENTS[name]
    member = call.split(".", 1)[1]
    pos = _name_pos(ctx, name)
    if pos is None:
        return None
    s = ctx.line_text
    m = re.compile(rf"{re.escape(name)}\s*\.\s*{re.escape(member)}\s*\(").match(s, pos[0])
    if m:
        got = _call_args(s, m.end() - 1)
        if got is None:
            return None
        args, end = got
        keep = args[:1] if helper != "End" else []
        new = f"{helper}({', '.join(keep)})"
        dropped = len(args) > len(keep)
        title = f"Use the RAD helper {helper}(...) instead of {call}" + (" (text only)" if dropped else "")
        return Action(title, edits=ctx.edit([[ctx.line, pos[0], ctx.line, end, new]]), preferred=True,
                      fixes=list(ctx.diagnostics))
    return Action(f"Use the RAD helper {helper} instead of {name}",
                  edits=ctx.edit([[ctx.line, pos[0], ctx.line, pos[1], helper]]), preferred=True,
                  fixes=list(ctx.diagnostics))


def using_actions(ctx: Context, name: str, nss: list[str], vb: bool, preferred=True) -> list[Action]:
    dq = _dq()
    out = []
    for i, ns in enumerate(nss[:4]):
        edits = dq.using_edit(ctx.text, ns, vb)
        if edits:
            out.append(Action(f"Imports {ns}" if vb else f"using {ns};", edits=ctx.edit(edits),
                              preferred=preferred and i == 0, fixes=list(ctx.diagnostics)))
    pos = _name_pos(ctx, name)
    if pos is not None and not qualified_before(ctx):
        for ns in nss[:2]:
            out.append(Action(f"{ns}.{name}", edits=ctx.edit([[ctx.line, pos[0], ctx.line, pos[1], f"{ns}.{name}"]]),
                              fixes=list(ctx.diagnostics)))
    return out


def _index_lookup(project: Path | None, name: str, cheap: bool) -> list[str] | None:
    """Namespaces of *name* from the SDK metadata index (None = no index: no SDK, or not built yet when cheap)."""
    dq = _dq()
    key = str(project or "").lower()
    if cheap and key not in dq._INDEX:
        return None
    try:
        idx = dq.index_for(project)
    except Exception:  # noqa: BLE001
        return None
    if not getattr(idx, "by_name", None):
        return None
    return [ns for ns, _a in (idx.lookup(name) or idx.lookup(name + "Attribute")) if ns]


def nuget_search_action(ctx: Context, name: str, project: Path, rad_folder: Path | None) -> Action:
    def run(win, ed):
        search_and_install(win, name, project, rad_folder)
    return Action(f"Search NuGet.org for '{name}'...", run=run,
                  detail=f"nuget.org search: {name}\n-> dotnet add {project.name} package <chosen>")


def search_and_install(win, term: str, project: Path, rad_folder: Path | None) -> None:
    """Search nuget.org (worker thread, progress), pick a package, dotnet add package (progress)."""
    from .. import progress

    def work(reporter):
        if term in _NUGET_CACHE:
            return _NUGET_CACHE[term]
        reporter.set_text(f"nuget.org: {term}")
        from ..dotnet.nuget.config import NUGET_ORG
        from ..dotnet.nuget.feed import V3Feed
        res, _n = V3Feed(NUGET_ORG).search(term, take=10)
        _NUGET_CACHE[term] = res
        return res

    def done(res):
        if not res:
            try:
                win.statusBar().showMessage(f"NuGet.org has no package for '{term}'", 8000)
            except Exception:  # noqa: BLE001
                pass
            return
        res = sorted(res, key=lambda r: (term.lower() not in r.id.lower(), -r.total_downloads))
        labels = [f"{r.id}  {r.version}  ({r.total_downloads:,} downloads)" for r in res]
        pick = getattr(win, "_quickfix_pick", None)        # tests answer here
        if callable(pick):
            choice = pick(labels)
        else:
            from PyQt6.QtWidgets import QInputDialog
            choice, ok = QInputDialog.getItem(win, "Install NuGet Package", f"Packages for '{term}':", labels, 0, False)
            choice = choice if ok else None
        if not choice or choice not in labels:
            return
        pkg = res[labels.index(choice)].id
        install_package(win, project, pkg, rad_folder)
    progress.run_task(work, f"Searching NuGet.org for '{term}'", win, on_done=done,
                      on_error=lambda e: installers._log(win, f"*** NuGet search: {e}"))


def install_package(win, project: Path, pkg: str, rad_folder: Path | None, then=None) -> None:
    if rad_folder is not None:
        try:
            from ..languages.csharp_bridge import ensure_build_dir
            project = ensure_build_dir(rad_folder)
        except Exception as e:  # noqa: BLE001
            installers._log(win, f"*** {e}")

    def after(ok):
        _dq()._INDEX.pop(str(project).lower(), None)       # the new package's types
        if then is not None:
            then(ok)
    installers.dotnet_add_package(win, project, pkg, after)


def provide(ctx: Context) -> list[Action]:
    if ctx.language not in ("csharp", "vbnet"):
        return []
    dq = _dq()
    vb = ctx.language == "vbnet"
    rad = rad_csharp(ctx)
    names = [n.split(".")[-1].split("<")[0] for n in ctx.diag_names()]
    if ctx.word and ctx.word not in names and not qualified_before(ctx):
        names.append(ctx.word)
    out: list[Action] = []
    for name in names:
        if not re.fullmatch(r"[A-Za-z_]\w*", name or ""):
            continue
        if rad is not None:
            out += _rad_actions(ctx, name, rad)
        elif name[:1].isupper():
            out += _project_actions(ctx, name, vb, dq)
        if out:
            break
    return out


def type_like(ctx: Context, name: str) -> bool:
    """The name is used as a type on the line (new T, T x, T.Member, T<...>, typeof(T), : T)."""
    n = re.escape(name)
    return bool(re.search(rf"\bnew\s+{n}\b|\b{n}\s*<|(?<![\w.]){n}\??\s+[A-Za-z_]\w*\s*[=;,)]|(?<![\w.]){n}\s*\.|"
                          rf"<\s*{n}\s*[>,]|typeof\s*\(\s*{n}|:\s*{n}\b|\({n}\)\s*\w", ctx.line_text))


def rad_declared(folder: Path) -> set:
    """Names the RAD C# program already has: the project's own types / members, the designer's controls and the
    client's (Rad.cs: RadEvent, RadControl ...)."""
    names = set()
    files = list(Path(folder).glob("*.cs"))
    try:
        from ..languages.csharp_bridge import CLIENT_DIR, CLIENT_SOURCES
        files += [CLIENT_DIR / n for n in CLIENT_SOURCES]
    except ImportError:
        pass
    for f in files[:300]:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        names.update(re.findall(r"\b(?:class|struct|enum|interface|record|delegate\s+\w+)\s+(\w+)", text))
        names.update(re.findall(r"\b(?:public|internal|static|private)\s+(?:static\s+)?(?:readonly\s+)?"
                                r"[\w<>\[\],?]+\s+(\w+)\s*[=;({]", text))
    return names


def _rad_actions(ctx: Context, name: str, folder: Path) -> list[Action]:
    dq = _dq()
    out: list[Action] = []
    from ..languages.csharp_bridge import RAD_HELPERS
    helpers = {h.lower(): h for h in RAD_HELPERS}
    if name in RAD_HELPERS:
        return []
    if name.lower() in helpers:                              # msgbox -> MsgBox
        pos = _name_pos(ctx, name)
        if pos is not None:
            right = helpers[name.lower()]
            out.append(Action(f"Change '{name}' to '{right}'", edits=ctx.edit([[ctx.line, pos[0], ctx.line, pos[1],
                                                                                right]]),
                              preferred=True, fixes=list(ctx.diagnostics)))
        return out
    if not name[:1].isupper():
        return out
    proj = _rad_csproj(folder)
    visible = dq.file_usings(ctx.text) | RAD_IMPLICIT
    named = name in ctx.diag_names() or any(n.split("<")[0] == name for n in ctx.diag_names())
    if not named and not type_like(ctx, name):
        return out                            # a method / control / variable name, not a missing type
    if not named and name in rad_declared(folder):
        return out
    if name in RAD_CS_EQUIVALENTS:
        a = rad_helper_action(ctx, name)
        if a is not None:
            out.append(a)
        ns = CS_TYPES.get(name, "")
        if ns:
            out.append(Action(f"using {ns}; - not available: a RAD C# form runs as a console process "
                              f"(the IDE draws the form)",
                              disabled=f"{ns} is not referenced by RAD C# projects (_build/csharp/RadApp.csproj); "
                                       f"use the RAD helpers (MsgBox, InputBox, Set/Get/Call, Show, End)"))
        return out
    nss = _index_lookup(proj if proj.is_file() else None, name, ctx.cheap)
    if nss is None:
        nss = [CS_TYPES[name]] if name in CS_TYPES else []
    nss = [ns for ns in nss if not ns.startswith(WINDOWS_NS)] or nss
    if nss and any(ns in visible for ns in nss):
        return out
    usable = [ns for ns in nss if not ns.startswith(WINDOWS_NS)]
    if usable:
        out += using_actions(ctx, name, usable, False)
    elif nss:
        out.append(Action(f"using {nss[0]}; - not available in a RAD C# project",
                          disabled=f"{nss[0]} needs Windows Forms / WPF, which RAD C# projects do not reference"))
    elif name in dq.KNOWN_PACKAGES:
        pkg, ns = dq.KNOWN_PACKAGES[name]

        def run(win, ed, pkg=pkg, ns=ns):
            def then(ok):
                if ok:
                    from .. import editkit
                    editkit.apply_edits(ed, dq.using_edit(ed.text(), ns, False))
            install_package(win, proj, pkg, folder, then)
        out.append(Action(f"Install package '{pkg}' from NuGet and add 'using {ns};'", run=run, preferred=True,
                          detail=f"dotnet add _build/csharp/RadApp.csproj package {pkg}\n+ using {ns};",
                          fixes=list(ctx.diagnostics)))
    elif not ctx.cheap and name not in dq.file_usings(ctx.text):
        out.append(nuget_search_action(ctx, name, proj, folder))
    return out


def _project_actions(ctx: Context, name: str, vb: bool, dq) -> list[Action]:
    from ..dotnet.tools import sdk
    project = sdk.project_for_file(ctx.path)
    if project is None:                                       # a loose file: the SDK's types, else the table
        visible = dq.file_usings(ctx.text)
        nss = _index_lookup(None, name, ctx.cheap)
        if not nss:
            nss = [CS_TYPES[name]] if name in CS_TYPES else []
            if name in CS_WPF_ALTERNATIVES:
                nss.append(CS_WPF_ALTERNATIVES[name])
        if not nss or any(ns in visible for ns in nss):
            return []
        return using_actions(ctx, name, nss, vb)
    if ctx.cheap and str(project).lower() not in dq._INDEX:
        nss = [CS_TYPES[name]] if name in CS_TYPES else []
        visible = dq.file_usings(ctx.text, ctx.path, project)
        return [] if not nss or nss[0] in visible else using_actions(ctx, name, nss, vb)
    sol = []
    if not ctx.cheap and ctx.win is not None:
        try:
            from ..dotnet.tools import ui as DUI
            sol = DUI.solution_project_files(ctx.win)
        except Exception:  # noqa: BLE001
            sol = []
    out = []
    for f in dq.fixes_for(name, ctx.text, ctx.path, project, solution_projects=sol):
        if f.kind == "using":
            edits = dq.using_edit(ctx.text, f.namespace, vb)
            if edits:
                out.append(Action(f.title, edits=ctx.edit(edits), preferred=not out, fixes=list(ctx.diagnostics)))
        elif f.kind == "qualify":
            pos = _name_pos(ctx, f.type_name)
            if pos is not None:
                out.append(Action(f.title, edits=ctx.edit([[ctx.line, pos[0], ctx.line, pos[1],
                                                            f"{f.namespace}.{f.type_name}"]])))
        elif ctx.cheap:
            continue
        else:
            def run(win, ed, f=f, line=ctx.line):
                from ..dotnet.tools import ui as DUI
                if f.kind == "package":                      # dotnet add package with progress, then the using
                    def then(ok):
                        if ok and f.namespace:
                            from .. import editkit
                            editkit.apply_edits(ed, dq.using_edit(ed.text(), f.namespace, vb))
                        dq._INDEX.pop(str(project).lower(), None)
                    installers.dotnet_add_package(win, project, f.package, then)
                else:
                    DUI.apply_fix(win, ed, f, line)
            detail = {"package": f"dotnet add {project.name} package {f.package}",
                      "project": f"dotnet add {project.name} reference {Path(f.project).name}",
                      "search": f"NuGet Package Manager: search '{f.type_name}'"}.get(f.kind, "")
            out.append(Action(f.title, run=run, detail=detail, fixes=list(ctx.diagnostics)))
    return out


register(("csharp", "vbnet"), provide)

__all__ = ["provide", "rad_csharp", "rad_helper_action", "search_and_install", "install_package"]
