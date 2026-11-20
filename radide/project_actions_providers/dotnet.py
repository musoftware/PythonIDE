"""Project actions for .NET: ASP.NET Core (dotnet new item templates, dotnet watch, Entity Framework Core
migrations, user-secrets) and Visual Studio solutions (Build / Rebuild / Clean / Publish, NuGet)."""
from __future__ import annotations

import re
from pathlib import Path

from ..project_actions import Action, Field, Provider, Separator, Submenu, matches, read_text
from ._common import log_routes, studly, target_folder, write_new

WEB_SDK = re.compile(r"Sdk\s*=\s*\"Microsoft\.NET\.Sdk\.(Web|Razor|BlazorWebAssembly)\"", re.I)


def dotnet() -> str:
    try:
        from ..web_site.frameworks.aspnet import dotnet_exe
        return dotnet_exe() or "dotnet"
    except Exception:  # noqa: BLE001
        return "dotnet"


def csproj(folder: Path) -> Path | None:
    files = sorted(Path(folder).glob("*.csproj")) + sorted(Path(folder).glob("*.fsproj")) + \
        sorted(Path(folder).glob("*.vbproj"))
    return files[0] if files else None


def root_ns(folder: Path) -> str:
    try:
        from ..web_site.frameworks.aspnet import root_namespace
        return root_namespace(folder)
    except Exception:  # noqa: BLE001
        p = csproj(folder)
        return re.sub(r"\W", "_", p.stem if p else Path(folder).name)


def namespace_for(folder: Path, rel_dir: str) -> str:
    parts = [re.sub(r"\W", "_", p) for p in rel_dir.replace("\\", "/").split("/") if p]
    return ".".join([root_ns(folder), *parts])


CLASS_CS = """namespace {ns};

public class {name}
{{
    public int Id {{ get; set; }}
}}
"""
DBCONTEXT_CS = """using Microsoft.EntityFrameworkCore;

namespace {ns};

public class {name} : DbContext
{{
    public {name}(DbContextOptions<{name}> options) : base(options)
    {{
    }}

    // public DbSet<Product> Products => Set<Product>();
}}

// Program.cs:  builder.Services.AddDbContext<{name}>(o => o.UseSqlite("Data Source=app.db"));
"""


# ============================================================================ ASP.NET Core
class AspNetCore(Provider):
    id, title, priority, icon = "aspnet-core", "ASP.NET Core", 45, ("C#", "#512BD4")

    def detect(self, folder, project):
        p = csproj(folder)
        return p is not None and p.suffix.lower() == ".csproj" and bool(WEB_SDK.search(read_text(p)[:2000]))

    # ---------------------------------------------------------------- dotnet new items
    def item(self, template: str, title: str, default: str, default_dir: str, extra=()) -> Action:
        ask = [Field("name", "Name", default=default), *extra]
        return Action(f"new-{template}", f"New {title}...",
                      lambda c, t=template, d=default_dir: self._new_item(c, t, d), ask=ask)

    def _new_item(self, ctx, template, default_dir):
        name = studly(ctx.values["name"])
        if template in ("apicontroller", "mvccontroller") and not name.endswith("Controller"):
            name += "Controller"
        rel_dir = target_folder(ctx, default_dir)
        if template == "class":
            write_new(ctx, f"{rel_dir}/{name}.cs", CLASS_CS.format(ns=namespace_for(ctx.folder, rel_dir), name=name))
            return
        if template == "dbcontext":
            write_new(ctx, f"{rel_dir}/{name}.cs",
                      DBCONTEXT_CS.format(ns=namespace_for(ctx.folder, rel_dir), name=name))
            return
        argv = [dotnet(), "new", template, "-n", name, "-o", rel_dir or "."]
        if template != "view":
            argv += ["--namespace", namespace_for(ctx.folder, rel_dir)]
        if template == "apicontroller" and ctx.values.get("actions"):
            argv.append("--actions")
        if template == "page" and ctx.values.get("no_model"):
            argv.append("--no-pagemodel")
        ctx.run_cli(argv, title=f"dotnet new {template} {name}")

    def new_api_controller(self):
        return self.item("apicontroller", "API Controller", "ProductsController", "Controllers",
                         [Field("actions", "With read/write actions (--actions)", "bool", default=True)])

    def new_mvc_controller(self):
        return self.item("mvccontroller", "MVC Controller", "HomeController", "Controllers")

    def new_page(self):
        return self.item("page", "Razor Page", "Products", "Pages",
                         [Field("no_model", "Without a PageModel class (--no-pagemodel)", "bool")])

    def new_component(self):
        return self.item("razorcomponent", "Razor Component", "Counter", "Components")

    def new_view(self):
        return self.item("view", "Razor View", "Index", "Views")

    def new_class(self):
        return self.item("class", "Class", "Product", "Models")

    def new_dbcontext(self):
        return self.item("dbcontext", "DbContext", "AppDbContext", "Data")

    # ---------------------------------------------------------------- Entity Framework Core
    def ef_menu(self) -> Submenu:
        d = dotnet()
        return Submenu("Entity Framework", [
            Action("ef-add", "Add Migration...", lambda c: c.run_cli([d, "ef", "migrations", "add", c.values["name"]],
                                                                    title=f"ef migrations add {c.values['name']}"),
                   ask=[Field("name", "Migration name", default="InitialCreate")]),
            Action("ef-update", "Update Database", lambda c: c.run_cli([d, "ef", "database", "update"]),
                   opens="none"),
            Action("ef-list", "List Migrations", lambda c: c.run_cli([d, "ef", "migrations", "list"]), opens="none"),
            Action("ef-remove", "Remove Last Migration", lambda c: c.run_cli([d, "ef", "migrations", "remove"]),
                   opens="none", refresh=True),
            Action("ef-script", "Generate SQL Script", lambda c: c.run_cli([d, "ef", "migrations", "script", "-o",
                                                                           "Migrations/script.sql"]), opens="created"),
            Action("ef-drop", "Drop Database", self._drop, opens="none"),
            Separator(),
            Action("ef-packages", "Add EF Core Packages (Design + SQLite)", self._ef_packages, opens="none",
                   refresh=True),
            Action("ef-tool", "Install / Update the dotnet-ef Tool",
                   lambda c: c.run_cli([d, "tool", "update", "--global", "dotnet-ef"]), opens="none")])

    def _drop(self, ctx):
        if ctx.confirm("Drop the database of this project (dotnet ef database drop)?"):
            ctx.run_cli([dotnet(), "ef", "database", "drop", "--force"])

    def _ef_packages(self, ctx):
        d = dotnet()
        ctx.run_cli([d, "add", "package", "Microsoft.EntityFrameworkCore.Design"],
                    on_done=lambda r: r.exit_code == 0 and ctx.run_cli(
                        [d, "add", "package", "Microsoft.EntityFrameworkCore.Sqlite"]))

    def secrets_menu(self) -> Submenu:
        d = dotnet()
        return Submenu("User Secrets", [
            Action("secrets-init", "Init (user-secrets init)", lambda c: c.run_cli([d, "user-secrets", "init"]),
                   opens="none"),
            Action("secrets-set", "Set Secret...",
                   lambda c: c.run_cli([d, "user-secrets", "set", c.values["key"], c.values["value"]],
                                       title=f"user-secrets set {c.values['key']}"),
                   ask=[Field("key", "Key", placeholder="ConnectionStrings:Default"), Field("value", "Value")],
                   opens="none"),
            Action("secrets-list", "List Secrets", lambda c: c.run_cli([d, "user-secrets", "list"]), opens="none"),
            Action("secrets-remove", "Remove Secret...",
                   lambda c: c.run_cli([d, "user-secrets", "remove", c.values["key"]]),
                   ask=[Field("key", "Key")], opens="none")])

    # ---------------------------------------------------------------- menus
    def actions(self, ctx):
        d = dotnet()
        return [Action("watch", "Run with Hot Reload (dotnet watch)", lambda c: c.run_cli([d, "watch", "run"]),
                       toolbar=True, opens="none", icon="SP_MediaPlay"),
                Action("run", "Run (dotnet run)", lambda c: c.run_cli([d, "run"]), opens="none"),
                Action("build", "Build", lambda c: c.run_cli([d, "build"]), opens="none"),
                Action("test", "Run Tests (dotnet test)", lambda c: c.run_cli([d, "test"]), opens="none"),
                Action("publish", "Publish (Release to publish/)",
                       lambda c: c.run_cli([d, "publish", "-c", "Release", "-o", "publish"]), opens="none"),
                Separator(),
                Submenu("Add", [self.new_api_controller(), self.new_mvc_controller(), self.new_page(),
                                self.new_component(), self.new_view(), self.new_class(), self.new_dbcontext()]),
                self.ef_menu(),
                self.secrets_menu(),
                Separator(),
                Action("add-package", "Add NuGet Package...", self._add_package, opens="none", refresh=True,
                       ask=[Field("package", "Package", placeholder="Swashbuckle.AspNetCore"),
                            Field("version", "Version (empty = latest)", required=False)]),
                Action("restore", "Restore Packages", lambda c: c.run_cli([d, "restore"]), opens="none"),
                Action("routes", "Show Routes", self._routes, opens="none"),
                Action("dev-certs", "Trust the HTTPS Development Certificate",
                       lambda c: c.run_cli([d, "dev-certs", "https", "--trust"]), opens="none")]

    def _add_package(self, ctx):
        argv = [dotnet(), "add", "package", ctx.values["package"].strip()]
        if ctx.values.get("version"):
            argv += ["--version", ctx.values["version"].strip()]
        ctx.run_cli(argv, title=f"dotnet add package {ctx.values['package']}")

    def _routes(self, ctx):
        from ..web_site.frameworks import aspnet
        routes = []
        for fn in (aspnet.controller_routes, aspnet.razor_page_routes, aspnet.minimal_api_routes):
            try:
                routes += fn(ctx.folder)
            except Exception as e:  # noqa: BLE001
                ctx.log(f"*** {fn.__name__}: {e}")
        log_routes(ctx, "ASP.NET Core", routes)

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "Controllers/**", "Areas/*/Controllers/**"):
            return [self.new_api_controller(), self.new_mvc_controller()]
        if matches(rel_folder, "Pages/**", "Areas/*/Pages/**"):
            return [self.new_page(), self.new_component()]
        if matches(rel_folder, "Components/**", "Shared/**"):
            return [self.new_component()]
        if matches(rel_folder, "Views/**", "Areas/*/Views/**"):
            return [self.new_view()]
        if matches(rel_folder, "Migrations/**"):
            return self.ef_menu().items
        if matches(rel_folder, "Data/**"):
            return [self.new_dbcontext(), self.new_class(), Separator(), self.ef_menu()]
        return [self.new_class()]

    def file_actions(self, ctx, rel_file):
        if matches(rel_file, "Migrations/*.cs") and not rel_file.endswith((".Designer.cs", "ModelSnapshot.cs")):
            mig = Path(rel_file).stem
            return [Action("ef-update-to", f"Update Database to {mig}",
                           lambda c: c.run_cli([dotnet(), "ef", "database", "update", mig]), opens="none")]
        if rel_file.lower().endswith(".csproj"):
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id in ("build", "run", "restore",
                                                                                     "add-package")]
        return []


# ============================================================================ Visual Studio solutions
class VisualStudio(Provider):
    id, title, priority, icon = "visual-studio", "Visual Studio", 30, ("VS", "#68217A")

    def detect(self, folder, project):
        if getattr(project, "ms", None) is not None:
            return True
        return any(Path(folder).glob("*.sln")) or any(Path(folder).glob("*.slnx"))

    # ---------------------------------------------------------------- what to build
    @staticmethod
    def solution(ctx):
        sln = getattr(ctx.win, "sln", None)
        try:
            from ..foreign.vs_solution import VsSolution
            return sln if isinstance(sln, VsSolution) else None
        except Exception:  # noqa: BLE001
            return None

    def target(self, ctx) -> Path | None:
        sln = self.solution(ctx)
        f = getattr(sln, "file", None) if sln is not None else None
        if f and Path(f).suffix.lower() in (".sln", ".slnx") and Path(f).exists():
            return Path(f)
        for pat in ("*.sln", "*.slnx"):
            for p in sorted(ctx.folder.glob(pat)):
                return p
        ms = getattr(ctx.project, "ms", None)
        if ms is not None:
            return Path(ms.path)
        return csproj(ctx.folder)

    def _project_file(self, ctx) -> Path | None:
        ms = getattr(ctx.project, "ms", None)
        return Path(ms.path) if ms is not None else csproj(ctx.folder)

    def build(self, ctx, verb: str):
        sln = self.solution(ctx)
        target = self.target(ctx)
        if target is None:
            ctx.log("*** no .sln or project file here")
            return
        try:
            ctx.win.save_all()
        except Exception:  # noqa: BLE001
            pass
        from ..foreign import msbuild
        config = getattr(sln, "configuration", "Debug") if sln is not None else "Debug"
        platform = getattr(sln, "platform", "") if sln is not None else ""
        sdk = True
        if sln is not None:
            try:
                sdk = all(msbuild.uses_dotnet_cli(p.ms) for p in sln.all_projects())
            except Exception:  # noqa: BLE001
                sdk = True
        argv = msbuild.build_argv(target, config, platform, sdk=sdk, verb=verb)
        if argv is None:
            ctx.log("*** neither the .NET SDK (dotnet) nor MSBuild was found")
            return
        ctx.run_cli(argv, title=f"{verb.capitalize()} {target.name} ({config})")

    def actions(self, ctx):
        d = dotnet()
        return [Action("build", "Build Solution", lambda c: self.build(c, "build"), opens="none", toolbar=True,
                       icon="SP_DialogApplyButton"),
                Action("rebuild", "Rebuild Solution", lambda c: self.build(c, "rebuild"), opens="none"),
                Action("clean", "Clean Solution", lambda c: self.build(c, "clean"), opens="none"),
                Action("restore", "Restore NuGet Packages",
                       lambda c: c.run_cli([d, "restore", str(self.target(c))]), opens="none"),
                Separator(),
                Action("publish", "Publish Project (Release)...", self._publish, opens="none",
                       ask=[Field("output", "Output folder", "path", default="publish"),
                            Field("self_contained", "Self-contained (include the .NET runtime)", "bool"),
                            Field("single", "Single file", "bool")]),
                Action("test", "Run Tests (dotnet test)", lambda c: c.run_cli([d, "test", str(self.target(c))]),
                       opens="none"),
                Separator(),
                Action("add-package", "Add NuGet Package...", self._add_package, opens="none", refresh=True,
                       ask=[Field("package", "Package", placeholder="Newtonsoft.Json"),
                            Field("version", "Version (empty = latest)", required=False)],
                       enabled=lambda c: self._project_file(c) is not None),
                Action("manage-nuget", "Manage NuGet Packages...", self._manage, opens="none",
                       enabled=lambda c: getattr(c.project, "ms", None) is not None),
                Action("properties", "Project Properties...", self._properties, opens="none",
                       enabled=lambda c: getattr(c.project, "ms", None) is not None),
                Separator(),
                Action("open-vs", "Open in Visual Studio", self._open_vs, opens="none")]

    def _publish(self, ctx):
        proj = self._project_file(ctx)
        if proj is None:
            ctx.log("*** no project file to publish")
            return
        out = ctx.values.get("output") or "publish"
        argv = [dotnet(), "publish", str(proj), "-c", "Release", "-o", out]
        if ctx.values.get("self_contained"):
            argv += ["--self-contained", "true", "-r", "win-x64"]
        if ctx.values.get("single"):
            argv += ["-p:PublishSingleFile=true"] + ([] if ctx.values.get("self_contained") else ["-r", "win-x64",
                                                                                              "--self-contained",
                                                                                              "false"])
        ctx.run_cli(argv, title=f"Publish {proj.name}")

    def _add_package(self, ctx):
        proj = self._project_file(ctx)
        argv = [dotnet(), "add", str(proj), "package", ctx.values["package"].strip()]
        if ctx.values.get("version"):
            argv += ["--version", ctx.values["version"].strip()]
        ctx.run_cli(argv, title=f"dotnet add package {ctx.values['package']}",
                    on_done=lambda r: r.exit_code == 0 and self._reload(ctx))

    @staticmethod
    def _reload(ctx):
        try:
            from ..foreign import vs_ui
            vs_ui._reload(ctx.win, ctx.project)
        except Exception:  # noqa: BLE001
            ctx.refresh_tree()

    @staticmethod
    def _manage(ctx):
        from ..foreign import vs_ui
        vs_ui.manage_packages(ctx.win, ctx.project)

    @staticmethod
    def _properties(ctx):
        from ..foreign import vs_ui
        vs_ui.project_properties(ctx.win, ctx.project)

    def _open_vs(self, ctx):
        from ..foreign import vs_ui
        t = self.target(ctx)
        if t is None or not vs_ui.open_in_visual_studio(ctx.win, t):
            ctx.log("*** Visual Studio was not found")

    def folder_actions(self, ctx, rel_folder):
        if rel_folder != "":
            return []
        return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id in ("build", "rebuild", "clean",
                                                                                 "add-package", "publish")]

    def file_actions(self, ctx, rel_file):
        if rel_file.lower().endswith((".sln", ".slnx", ".csproj", ".vbproj", ".fsproj", ".vcxproj")):
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id in ("build", "rebuild", "clean")]
        return []


PROVIDERS = [AspNetCore(), VisualStudio()]
