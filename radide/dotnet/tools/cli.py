"""dotnet CLI commands in the dynamic Project menu (radide/project_actions_providers/dotnet.py adds the
"dotnet CLI" submenu built here): restore, clean, build, test, pack, publish, format, watch run (Hot Reload),
user-secrets, local tools, workloads and SDK information. Every command runs in the Output window.

Workloads are never installed silently: "Install Workload..." opens the official page and puts the exact
command in the Output window (workload installs change the shared SDK and usually need an elevated prompt)."""
from __future__ import annotations

from pathlib import Path

from ...project_actions import Action, Field, Separator, Submenu
from . import sdk

WORKLOAD_DOCS = "https://learn.microsoft.com/dotnet/core/tools/dotnet-workload-install"
SECRETS_DOCS = "https://learn.microsoft.com/aspnet/core/security/app-secrets"


def _d() -> str:
    return sdk.dotnet() or "dotnet"


def _open_url(url: str) -> None:
    import os
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return
    try:
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))
    except Exception:  # noqa: BLE001
        pass


def cli_submenu(provider, ctx) -> Submenu:
    """provider: the VisualStudio project-actions provider (target / _project_file / _reload)."""
    def sol(c) -> str:
        t = provider.target(c)
        return str(t) if t is not None else ""

    def proj(c) -> str:
        p = provider._project_file(c)
        return str(p) if p is not None else ""

    def has_proj(c) -> bool:
        return provider._project_file(c) is not None

    def cfg(c) -> str:
        s = provider.solution(c)
        return getattr(s, "configuration", "Debug") if s is not None else "Debug"

    def run(argv_fn, title, refresh=False):
        def go(c):
            try:
                c.win.save_all()
            except Exception:  # noqa: BLE001
                pass
            argv = argv_fn(c)
            if not argv:
                c.log("*** no solution or project file here")
                return
            c.run_cli(argv, title=title, env=dict(sdk.QUIET_ENV),
                      on_done=(lambda r: r.exit_code == 0 and provider._reload(c)) if refresh else None)
        return go

    def startup(c) -> str:
        s = provider.solution(c)
        p = s.startup_project() if s is not None and hasattr(s, "startup_project") else None
        ms = getattr(p, "ms", None)
        return str(ms.path) if ms is not None else proj(c)

    items = [
        Action("cli-restore", "Restore (dotnet restore)", run(lambda c: [_d(), "restore", sol(c)], "dotnet restore"),
               opens="none"),
        Action("cli-build", "Build (dotnet build)", run(lambda c: [_d(), "build", sol(c), "-c", cfg(c), "-nologo"],
                                                         "dotnet build"), opens="none"),
        Action("cli-clean", "Clean (dotnet clean)", run(lambda c: [_d(), "clean", sol(c), "-c", cfg(c), "-nologo"],
                                                         "dotnet clean"), opens="none"),
        Action("cli-test", "Test (dotnet test)", run(lambda c: [_d(), "test", sol(c), "-c", cfg(c), "--nologo"],
                                                      "dotnet test"), opens="none"),
        Action("cli-pack", "Pack NuGet Package (dotnet pack)...", lambda c: _pack(c, proj(c), provider),
               opens="none", enabled=has_proj,
               ask=[Field("output", "Output folder", "path", default="nupkg"),
                    Field("version", "Version (empty = the project's)", required=False),
                    Field("symbols", "Include symbols (.snupkg)", "bool")]),
        Action("cli-publish", "Publish (dotnet publish)...", lambda c: _publish(c, proj(c)), opens="none",
               enabled=has_proj,
               ask=[Field("output", "Output folder", "path", default="publish"),
                    Field("runtime", "Target runtime (empty = portable)", "choice", default="",
                          choices=["", "win-x64", "win-x86", "win-arm64", "linux-x64", "linux-arm64", "osx-x64",
                                   "osx-arm64"], required=False),
                    Field("self_contained", "Self-contained", "bool"),
                    Field("single", "Produce single file", "bool"),
                    Field("trim", "Trim unused code", "bool"),
                    Field("r2r", "ReadyToRun compilation", "bool")]),
        Action("cli-format", "Format Solution (dotnet format)",
               run(lambda c: [_d(), "format", sol(c), "-v", "n"], "dotnet format", refresh=False), opens="none"),
        Action("cli-format-verify", "Verify Formatting (dotnet format --verify-no-changes)",
               run(lambda c: [_d(), "format", sol(c), "--verify-no-changes", "-v", "n"], "dotnet format --verify"),
               opens="none"),
        Separator(),
        Action("cli-watch", "Watch Run with Hot Reload (dotnet watch run)",
               lambda c: _watch(c, startup(c)), opens="none", enabled=has_proj),
        Submenu("User Secrets", [
            Action("cli-secrets-init", "Init (user-secrets init)",
                   run(lambda c: [_d(), "user-secrets", "init", "--project", proj(c)], "user-secrets init",
                       refresh=True), opens="none", enabled=has_proj),
            Action("cli-secrets-set", "Set Secret...",
                   lambda c: c.run_cli([_d(), "user-secrets", "set", c.values["key"], c.values["value"], "--project",
                                        proj(c)], title=f"user-secrets set {c.values['key']}"),
                   ask=[Field("key", "Key", placeholder="ConnectionStrings:Default"), Field("value", "Value")],
                   opens="none", enabled=has_proj),
            Action("cli-secrets-list", "List Secrets",
                   run(lambda c: [_d(), "user-secrets", "list", "--project", proj(c)], "user-secrets list"),
                   opens="none", enabled=has_proj),
            Action("cli-secrets-remove", "Remove Secret...",
                   lambda c: c.run_cli([_d(), "user-secrets", "remove", c.values["key"], "--project", proj(c)],
                                       title="user-secrets remove"),
                   ask=[Field("key", "Key")], opens="none", enabled=has_proj),
            Action("cli-secrets-clear", "Clear All Secrets",
                   lambda c: c.confirm("Remove every user secret of this project?") and
                   c.run_cli([_d(), "user-secrets", "clear", "--project", proj(c)], title="user-secrets clear"),
                   opens="none", enabled=has_proj),
            Action("cli-secrets-open", "Open secrets.json", lambda c: _open_secrets(c, proj(c)), opens="none",
                   enabled=has_proj),
            Action("cli-secrets-docs", "About User Secrets (docs)", lambda c: _open_url(SECRETS_DOCS),
                   opens="none")]),
        Submenu("Tools", [
            Action("cli-tool-restore", "Restore Local Tools (dotnet tool restore)",
                   run(lambda c: [_d(), "tool", "restore"], "dotnet tool restore"), opens="none"),
            Action("cli-tool-list", "List Local Tools", run(lambda c: [_d(), "tool", "list", "--local"],
                                                              "dotnet tool list"), opens="none"),
            Action("cli-tool-manifest", "Create Tool Manifest (dotnet new tool-manifest)",
                   run(lambda c: [_d(), "new", "tool-manifest"], "dotnet new tool-manifest"), opens="created"),
            Action("cli-tool-install", "Install Local Tool...",
                   lambda c: _tool_install(c), opens="none",
                   ask=[Field("tool", "Tool package id (nuget.org)", placeholder="dotnet-ef"),
                        Field("version", "Version (empty = latest)", required=False)])]),
        Submenu("Workloads", [
            Action("cli-workload-list", "List Installed Workloads",
                   run(lambda c: [_d(), "workload", "list"], "dotnet workload list"), opens="none"),
            Action("cli-workload-search", "Search Available Workloads",
                   run(lambda c: [_d(), "workload", "search"], "dotnet workload search"), opens="none"),
            Action("cli-workload-restore-info", "Workloads This Solution Needs...",
                   lambda c: c.log("To install what the projects need, run in an elevated prompt:\n"
                                   f"    dotnet workload restore \"{sol(c)}\"\n(see {WORKLOAD_DOCS})"),
                   opens="none"),
            Action("cli-workload-install", "Install Workload...", _workload_install, opens="none",
                   ask=[Field("workload", "Workload id", "choice", default="maui",
                              choices=["maui", "maui-windows", "maui-android", "android", "ios", "wasm-tools",
                                       "wasm-experimental", "aspire"])])]),
        Separator(),
        Action("cli-info", "SDK Information (dotnet --info)", run(lambda c: [_d(), "--info"], "dotnet --info"),
               opens="none"),
        Action("cli-sdks", "List Installed SDKs and Runtimes",
               lambda c: c.run_cli([_d(), "--list-sdks"], title="dotnet --list-sdks",
                                   on_done=lambda r: c.run_cli([_d(), "--list-runtimes"],
                                                               title="dotnet --list-runtimes")), opens="none"),
    ]
    return Submenu("dotnet CLI", items)


def _pack(c, proj: str, provider):
    if not proj:
        c.log("*** no project file to pack")
        return
    argv = [_d(), "pack", proj, "-c", "Release", "-o", c.values.get("output") or "nupkg", "--nologo"]
    if (c.values.get("version") or "").strip():
        argv.append(f"-p:PackageVersion={c.values['version'].strip()}")
    if c.values.get("symbols"):
        argv += ["--include-symbols", "-p:SymbolPackageFormat=snupkg"]
    c.run_cli(argv, title=f"dotnet pack {Path(proj).name}", env=dict(sdk.QUIET_ENV))


def _publish(c, proj: str):
    if not proj:
        c.log("*** no project file to publish")
        return
    argv = [_d(), "publish", proj, "-c", "Release", "-o", c.values.get("output") or "publish", "--nologo"]
    rid = (c.values.get("runtime") or "").strip()
    sc = bool(c.values.get("self_contained"))
    if (c.values.get("single") or c.values.get("trim") or c.values.get("r2r")) and not rid:
        rid = "win-x64"
    if rid:
        argv += ["-r", rid, "--self-contained", "true" if sc else "false"]
    if c.values.get("single"):
        argv.append("-p:PublishSingleFile=true")
    if c.values.get("trim"):
        argv.append("-p:PublishTrimmed=true")
    if c.values.get("r2r"):
        argv.append("-p:PublishReadyToRun=true")
    c.run_cli(argv, title=f"dotnet publish {Path(proj).name}", env=dict(sdk.QUIET_ENV))


def _watch(c, proj: str):
    if not proj:
        c.log("*** no project to run")
        return
    c.run_cli([_d(), "watch", "run", "--project", proj, "--non-interactive"],
              title=f"dotnet watch run {Path(proj).stem} (Hot Reload - edit and save a file)",
              env={**sdk.QUIET_ENV, "DOTNET_WATCH_RESTART_ON_RUDE_EDIT": "1"})


def secrets_file(proj: str) -> Path | None:
    import os
    import re
    text = sdk.text(proj)
    m = re.search(r"<UserSecretsId>\s*([^<\s]+)\s*</UserSecretsId>", text)
    if not m:
        return None
    base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    return base / "Microsoft" / "UserSecrets" / m.group(1) / "secrets.json"


def _open_secrets(c, proj: str):
    f = secrets_file(proj) if proj else None
    if f is None:
        c.log("*** this project has no UserSecretsId yet - use User Secrets > Init first")
        return
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("{\n}\n", encoding="utf-8")
    c.open_file(f)


def _tool_install(c):
    tool = (c.values.get("tool") or "").strip()
    if not tool:
        return
    if not (c.folder / ".config" / "dotnet-tools.json").is_file() and not (c.folder / "dotnet-tools.json").is_file():
        c.log("No tool manifest here: creating one (dotnet new tool-manifest)")
        argv0 = [_d(), "new", "tool-manifest"]
    else:
        argv0 = None
    argv = [_d(), "tool", "install", tool]
    if (c.values.get("version") or "").strip():
        argv += ["--version", c.values["version"].strip()]
    if argv0:
        c.run_cli(argv0, title="dotnet new tool-manifest", on_done=lambda r: r.exit_code == 0 and
                  c.run_cli(argv, title=f"dotnet tool install {tool}"))
    else:
        c.run_cli(argv, title=f"dotnet tool install {tool}")


def _workload_install(c):
    w = (c.values.get("workload") or "maui").strip()
    c.log(f"Workloads are installed into the shared .NET SDK and need an elevated (administrator) prompt.\n"
          f"RAD IDE does not install them silently. Run this in an elevated terminal:\n"
          f"    dotnet workload install {w}\n"
          f"Documentation: {WORKLOAD_DOCS}")
    _open_url(WORKLOAD_DOCS)


__all__ = ["cli_submenu", "secrets_file", "WORKLOAD_DOCS"]
