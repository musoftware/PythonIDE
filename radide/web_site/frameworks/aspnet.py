"""ASP.NET Core web sites (``aspnet-web`` plugin) - MVC, Razor Pages, Web API, Empty.

- **New Project** runs the .NET SDK's own templates: ``dotnet new mvc|razor|webapi|web -n <Name> -o <folder>
  --no-https`` (offline, they ship with the SDK).
- **Run (Ctrl+F5)**: ``dotnet watch run --no-launch-profile --non-interactive -- --urls http://127.0.0.1:<port>``
  behind the IDE's DevServer (Preview, Requests, live reload) - ``dotnet watch`` applies hot reload / rebuilds by
  itself after a save.
- **Debug (F5)**: ``dotnet build`` then ``dotnet bin/Debug/<tfm>/<App>.dll --urls ...``; when the site listens,
  **netcoredbg** (``%LOCALAPPDATA%\\RADIDE\\tools\\netcoredbg``, the same one radide/bridgedebug.py uses) attaches to
  the process: breakpoints in controllers / page models / Program.cs (after start-up), Locals, Call Stack, stepping.
- **Routes**: attribute routes (``[Route]``, ``[HttpGet("...")]``), conventional MVC routes
  (``/{controller}/{action}``), Razor Pages (``@page``) and minimal APIs (``app.MapGet("/x", ...)``).
- **IntelliSense**: view / action / controller / page names in ``View("``, ``RedirectToAction("``,
  ``asp-action="``, ``asp-controller="``, ``asp-page="``, ``<partial name="``; C# itself through **csharp-ls**
  (``dotnet tool install csharp-ls --tool-path %LOCALAPPDATA%\\RADIDE\\tools\\csharp-ls``) when installed;
  .cshtml files open as Razor in Monaco.
- **CLI panel**: dotnet ef (migrations), dotnet new controller / view / page, dotnet add package, build, test.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..project import SiteTemplate, register_template
from .backend_common import (TOOLS, FrameworkPlugin, Route, Tool, filter_prefix, join_url, line_of, read_text,
                             reporter_cancelled, reporter_log, run, safe_identifier, string_context, walk_files,
                             which, with_progress)

CSHARP_LS_DIR = TOOLS / "csharp-ls"
NETCOREDBG = TOOLS / "netcoredbg" / "netcoredbg.exe"
HTTP_ATTR = re.compile(r"\[\s*Http(Get|Post|Put|Patch|Delete|Head|Options)\s*(?:\(\s*\"([^\"]*)\"[^\)]*\))?\s*\]")
ROUTE_ATTR = re.compile(r"\[\s*Route\s*\(\s*\"([^\"]*)\"")
CLASS_RE = re.compile(r"\bclass\s+(\w+?)(Controller)?\s*(?:\([^)]*\))?\s*:\s*([\w.<>, ]+)")
METHOD_RE = re.compile(r"^\s*public\s+(?:async\s+)?(?:virtual\s+)?(?:override\s+)?([\w<>\[\],. ?]+?)\s+(\w+)\s*\(", re.M)
MAP_RE = re.compile(r"\.Map(Get|Post|Put|Patch|Delete|Methods|Fallback)?\s*\(\s*\"([^\"]+)\"")


def dotnet_exe() -> str:
    p = which("dotnet")
    if p:
        return p
    for h in (r"C:\Program Files\dotnet\dotnet.exe",):
        if Path(h).exists():
            return h
    return ""


def find_netcoredbg() -> str:
    try:
        from ...bridgedebug import find_netcoredbg as f
        return f()
    except Exception:  # noqa: BLE001
        return str(NETCOREDBG) if NETCOREDBG.exists() else which("netcoredbg")


def csharp_ls() -> str:
    p = CSHARP_LS_DIR / "csharp-ls.exe"
    return str(p) if p.exists() else which("csharp-ls")


def install_csharp_ls(log=print) -> bool:
    dotnet = dotnet_exe()
    if not dotnet:
        log("*** the .NET SDK (dotnet) was not found")
        return False
    CSHARP_LS_DIR.mkdir(parents=True, exist_ok=True)
    # the newest csharp-ls needs the .NET 10 SDK; 0.20.0 is the last one a .NET 9 SDK can install (tested)
    for version in ([], ["--version", "0.20.0"]):
        code, _ = run([dotnet, "tool", "install", "csharp-ls", *version, "--tool-path", str(CSHARP_LS_DIR)],
                      timeout=600, log=log)
        if code == 0 or (CSHARP_LS_DIR / "csharp-ls.exe").exists():
            break
    return bool(csharp_ls())


def project_file(folder: Path) -> Path | None:
    files = sorted(Path(folder).glob("*.csproj"))
    return files[0] if files else None


def assembly_info(folder: Path) -> tuple[str, str]:
    """(assembly name, target framework) of the site's .csproj."""
    csproj = project_file(folder)
    if csproj is None:
        return "", ""
    text = read_text(csproj)
    m = re.search(r"<AssemblyName>([^<]+)</AssemblyName>", text)
    name = m.group(1).strip() if m else csproj.stem
    m = re.search(r"<TargetFrameworks?>([^<;]+)", text)
    return name, (m.group(1).strip() if m else "net9.0")


def root_namespace(folder: Path) -> str:
    csproj = project_file(folder)
    if csproj is None:
        return safe_identifier(Path(folder).name)
    m = re.search(r"<RootNamespace>([^<]+)</RootNamespace>", read_text(csproj))
    return m.group(1).strip() if m else safe_identifier(csproj.stem)


# ============================================================================ templates
def _creator(short: str):
    def create(folder: Path, name: str) -> dict:
        dotnet = dotnet_exe()
        if not dotnet:
            raise RuntimeError("the .NET SDK (dotnet) was not found - install it from https://dot.net")
        ident = safe_identifier(name)
        args = [dotnet, "new", short, "-n", ident, "-o", str(folder), "--force"]
        if short in ("mvc", "razor", "webapi", "web"):
            args.append("--no-https")
        code, out = with_progress(
            f"Creating the project (dotnet new {short})",
            lambda r: run(args, timeout=300, env={"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"},
                          log=reporter_log(r), cancelled=reporter_cancelled(r)), cancellable=True)
        if code != 0:
            raise RuntimeError(f"dotnet new {short} failed:\n{out[-1500:]}")
        gi = Path(folder) / ".gitignore"
        if not gi.exists():
            gi.write_text("bin/\nobj/\n.vs/\n", encoding="utf-8")
        return {"start": "/", "framework": "aspnet", "template": short}
    return create


for _tid, _short, _title, _desc, _order in (
        ("aspnet-mvc", "mvc", "ASP.NET Core MVC", "Model-View-Controller web app (dotnet new mvc): controllers, Razor "
                                                  "views, layout, Bootstrap.", 10),
        ("aspnet-razor", "razor", "ASP.NET Core Razor Pages", "Page-based web app (dotnet new razor): .cshtml pages with "
                                                              "page models.", 20),
        ("aspnet-webapi", "webapi", "ASP.NET Core Web API", "REST API (dotnet new webapi) with an example endpoint and "
                                                            "OpenAPI.", 30),
        ("aspnet-empty", "web", "ASP.NET Core Empty", "The smallest ASP.NET Core app (dotnet new web): one minimal-API "
                                                      "route.", 40)):
    register_template(SiteTemplate(_tid, _title, _desc, ("aspnet-web",), _creator(_short), _order,
                                   extra={"framework": "aspnet"}))


# ============================================================================ routes
def _attr_block_before(text: str, pos: int) -> str:
    """The attribute lines ([...]) right above position *pos*."""
    start = text.rfind("\n", 0, pos)
    lines = []
    while start > 0:
        prev = text.rfind("\n", 0, start)
        line = text[prev + 1:start].strip()
        if line.startswith("[") or line.startswith("//") or not line:
            if line.startswith("["):
                lines.append(line)
            start = prev
            if not line:
                break
            continue
        break
    return " ".join(reversed(lines))


def controller_routes(folder: Path) -> list[Route]:
    out: list[Route] = []
    for f in walk_files(folder, (".cs",), 3000):
        text = read_text(f)
        if "Controller" not in text:
            continue
        for cm in CLASS_RE.finditer(text):
            base_name, is_ctrl, bases = cm.group(1), cm.group(2), cm.group(3)
            if not is_ctrl or not re.search(r"\bController(Base)?\b", bases):
                continue
            ctrl = base_name
            attrs = _attr_block_before(text, cm.start())
            api = "ApiController" in attrs or "ControllerBase" in bases
            rm = ROUTE_ATTR.search(attrs)
            class_route = rm.group(1).replace("[controller]", ctrl) if rm else ""
            # class body = up to the next class declaration
            nxt = CLASS_RE.search(text, cm.end())
            body_end = nxt.start() if nxt else len(text)
            for mm in METHOD_RE.finditer(text, cm.end(), body_end):
                ret, action = mm.group(1), mm.group(2)
                if action == ctrl + "Controller" or ret.strip() in ("class", "void") and not api:
                    continue
                if not re.search(r"IActionResult|ActionResult|IResult|Task|View|string|JsonResult|\bvoid\b|"
                                 r"IEnumerable|Ok\w*", ret):
                    continue
                mattrs = _attr_block_before(text, mm.start())
                if "NonAction" in mattrs:
                    continue
                verbs = HTTP_ATTR.findall(mattrs)
                mroute = ROUTE_ATTR.search(mattrs)
                templ = None
                method = "ANY"
                if verbs:
                    method = verbs[0][0].upper()
                    templ = verbs[0][1] if verbs[0][1] else None
                if mroute and templ is None:
                    templ = mroute.group(1)
                templ = (templ or "").replace("[action]", action).replace("[controller]", ctrl)
                if templ.startswith(("/", "~/")):
                    path = "/" + templ.lstrip("~/")
                elif class_route or templ:
                    path = join_url(class_route.replace("[action]", action), templ)
                elif api:
                    path = join_url(ctrl)
                else:                                       # conventional {controller=Home}/{action=Index}/{id?}
                    path = "/" if (ctrl, action) == ("Home", "Index") else (
                        f"/{ctrl}" if action == "Index" else f"/{ctrl}/{action}")
                    if method == "ANY":
                        method = "GET"
                out.append(Route(method, path, f"{ctrl}Controller.{action}", str(f), line_of(text, mm.start()),
                                 action))
    return out


def razor_page_routes(folder: Path) -> list[Route]:
    pages = Path(folder) / "Pages"
    out: list[Route] = []
    if not pages.is_dir():
        return out
    for f in walk_files(pages, (".cshtml",), 2000):
        if f.name.startswith("_"):
            continue
        text = read_text(f)
        m = re.search(r"^\s*@page(?:\s+\"([^\"]*)\")?", text, re.M)
        if not m:
            continue
        rel = f.relative_to(pages).with_suffix("").as_posix()
        page = "/" + rel
        base = rel[:-len("Index")] if rel.endswith("Index") else rel
        templ = m.group(1) or ""
        path = ("/" + templ.lstrip("/")) if templ.startswith("/") else join_url(base, templ)
        out.append(Route("GET", path, f"Page {page}", str(f), line_of(text, m.start()), page))
    return out


def minimal_api_routes(folder: Path) -> list[Route]:
    out = []
    for f in walk_files(folder, (".cs",), 3000):
        text = read_text(f)
        if ".Map" not in text:
            continue
        for m in MAP_RE.finditer(text):
            verb = (m.group(1) or "ANY").upper()
            if verb in ("METHODS", "FALLBACK"):
                verb = "ANY"
            if m.group(0).startswith(".MapControllerRoute") or "MapStaticAssets" in m.group(0):
                continue
            out.append(Route(verb, m.group(2) if m.group(2).startswith("/") else "/" + m.group(2),
                             f"{f.name}: Map{m.group(1) or ''}", str(f), line_of(text, m.start())))
    return out


def views_of(folder: Path) -> dict[str, list[str]]:
    """{controller (or "Shared"): [view names]} from Views/**."""
    views = Path(folder) / "Views"
    out: dict[str, list[str]] = {}
    if not views.is_dir():
        return out
    for f in walk_files(views, (".cshtml",), 3000):
        rel = f.relative_to(views)
        if len(rel.parts) < 2:
            continue
        out.setdefault(rel.parts[0], []).append(f.stem)
    return out


def page_names(folder: Path) -> list[str]:
    pages = Path(folder) / "Pages"
    if not pages.is_dir():
        return []
    return sorted("/" + f.relative_to(pages).with_suffix("").as_posix() for f in walk_files(pages, (".cshtml",), 2000)
                  if not f.name.startswith("_"))


# ============================================================================ plugin
class AspNetPlugin(FrameworkPlugin):
    id = "aspnet-web"
    display_name = "ASP.NET Core Web App"
    framework = "aspnet"
    framework_title = "ASP.NET Core"
    cli_title = "dotnet CLI"
    code_ext = ".cs"
    web_kind = "aspnet"
    default_template = "aspnet-mvc"
    interpreter_names = ["dotnet"]
    interpreter_hints = [r"C:\Program Files\dotnet\dotnet.exe"]
    tool_names = ["dotnet"]
    view_ext = (".cshtml", ".razor")
    install_hint = "Install the .NET SDK from https://dot.net."
    keywords = ("abstract as async await base bool break case catch char class const continue decimal default "
                "delegate do double else enum event explicit extern false finally fixed float for foreach get goto "
                "if implicit in int interface internal is lock long namespace new null object operator out override "
                "params private protected public readonly record ref return sbyte sealed set short sizeof static "
                "string struct switch this throw true try typeof uint ulong unchecked unsafe ushort using var virtual "
                "void volatile while yield").split()
    builtins = ["Controller", "ControllerBase", "IActionResult", "View", "RedirectToAction", "Ok", "NotFound",
                "BadRequest", "ViewData", "ViewBag", "TempData", "HttpGet", "HttpPost", "Route", "ApiController",
                "WebApplication", "Results", "ILogger"]
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"']

    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        return dotnet_exe()

    # ---- run
    def base_env(self) -> dict:
        return {"ASPNETCORE_ENVIRONMENT": "Development", "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1",
                "DOTNET_WATCH_SUPPRESS_LAUNCH_BROWSER": "1", "DOTNET_WATCH_RESTART_ON_RUDE_EDIT": "1",
                "DOTNET_WATCH_SUPPRESS_EMOJIS": "1", "DOTNET_USE_POLLING_FILE_WATCHER": "0"}

    def backend(self, server) -> dict:
        dotnet = server.interpreter or dotnet_exe() or "dotnet"
        cfg = server.config
        env = self.base_env()
        url = "http://127.0.0.1:{port}"
        # always name the .csproj: MSBuild would also take project.radproj for a project file
        proj = ["--project", str(project_file(server.folder) or server.folder)]
        if cfg.get("watch", True):
            argv = [dotnet, "watch", *proj, "run", "--no-launch-profile", "--non-interactive", "--", "--urls", url]
        else:
            argv = [dotnet, "run", *proj, "--no-launch-profile", "--", "--urls", url]
        return {"argv": argv, "cwd": server.folder, "env": env, "prepare": [], "timeout": 240,
                "restart_on_change": False}

    def debug_spec(self, folder: Path, dotnet: str) -> dict:
        name, tfm = assembly_info(folder)
        dll = Path("bin") / "Debug" / tfm / f"{name}.dll"
        return {"argv": [dotnet, str(dll), "--urls", "http://127.0.0.1:{port}"], "cwd": folder,
                "env": self.base_env(),
                "prepare": [[dotnet, "build", str(project_file(folder) or folder), "-c", "Debug", "--nologo", "-v", "q"]],
                "timeout": 240, "restart_on_change": False}

    def start_debug(self, win, project, path=None):          # radide/web_site/debug.py start()
        return self.debug_website(win, project, path)

    def debug_website(self, win, project, path=None):
        from . import debug_support
        return debug_support.debug_aspnet(win, self, project, path)

    # ---- tools
    def tool_status(self) -> list[Tool]:
        return [Tool(".NET SDK", dotnet_exe(), "build / run", "https://dot.net"),
                Tool("netcoredbg", find_netcoredbg(), "debugger (F5)",
                     "github.com/Samsung/netcoredbg release zip -> tools\\netcoredbg"),
                Tool("csharp-ls", csharp_ls(), "C# IntelliSense (LSP)", "dotnet tool install csharp-ls", "csharp-ls"),
                Tool("dotnet-ef", which("dotnet-ef"), "EF Core migrations", "dotnet tool install -g dotnet-ef")]

    def install_tool(self, tool_id: str, log=print) -> bool:
        if tool_id == "csharp-ls":
            return install_csharp_ls(log)
        return super().install_tool(tool_id, log)

    # ---- CLI
    def cli_presets(self, project) -> list[tuple[str, str]]:
        ns = root_namespace(Path(project.folder))
        return [("Build", "dotnet build"), ("Restore packages", "dotnet restore"), ("Run tests", "dotnet test"),
                ("New MVC controller", f"dotnet new mvccontroller -n {{name}}Controller -o Controllers "
                                       f"--namespace {ns}.Controllers"),
                ("New API controller", f"dotnet new apicontroller -n {{name}}Controller -o Controllers "
                                       f"--namespace {ns}.Controllers"),
                ("New Razor view", "dotnet new view -n {name} -o Views/{name}"),
                ("New Razor page", f"dotnet new page -n {{name}} -o Pages --namespace {ns}.Pages"),
                ("Add NuGet package", "dotnet add package {name}"),
                ("Add EF Core (SQLite)", "dotnet add package Microsoft.EntityFrameworkCore.Sqlite"),
                ("Add EF Core Design", "dotnet add package Microsoft.EntityFrameworkCore.Design"),
                ("EF: add migration", "dotnet ef migrations add {name}"),
                ("EF: update database", "dotnet ef database update"),
                ("EF: list migrations", "dotnet ef migrations list"),
                ("List packages", "dotnet list package"),
                ("Publish (Release)", "dotnet publish -c Release -o publish")]

    def cli_env(self, project) -> dict:
        return {"DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}

    def cli_argv(self, project, command: str) -> list[str]:
        argv = super().cli_argv(project, command)
        if not argv or argv[0].lower() not in ("dotnet", "dotnet-ef"):
            return argv
        if argv[0].lower() == "dotnet-ef":
            argv = ["dotnet", "ef", *argv[1:]]
        argv[0] = dotnet_exe() or "dotnet"
        csproj = project_file(Path(project.folder))
        verb = argv[1].lower() if len(argv) > 1 else ""
        # MSBuild would also take project.radproj for a project file: always name the .csproj
        if csproj is not None and not any(a.lower().endswith(".csproj") for a in argv):
            if verb in ("build", "test", "restore", "publish", "run", "clean", "pack") and                     (len(argv) == 2 or argv[2].startswith("-")):
                argv.insert(2, str(csproj))
            elif verb in ("add", "remove", "list") and len(argv) > 2 and argv[2] in ("package", "reference"):
                argv.insert(2, str(csproj))
            elif verb == "list" and len(argv) == 2:
                argv.insert(2, str(csproj))
            elif verb == "ef" and "--project" not in argv and "-p" not in argv:
                argv += ["--project", str(csproj)]
            elif verb == "watch" and "--project" not in argv:
                argv[2:2] = ["--project", str(csproj)]
        return argv

    # ---- routes / views
    def routes(self, project) -> list[Route]:
        folder = Path(project.folder)
        routes = controller_routes(folder) + razor_page_routes(folder) + minimal_api_routes(folder)
        seen, out = set(), []
        for r in routes:
            key = (r.method, r.path, r.handler)
            if key not in seen:
                seen.add(key)
                out.append(r)
        return sorted(out, key=lambda r: (r.path, r.method))

    def view_names(self, project) -> list[str]:
        return sorted({v for vs in views_of(Path(project.folder)).values() for v in vs})

    def controllers(self, folder: Path) -> list[str]:
        return sorted({r.handler.split("Controller.", 1)[0] for r in controller_routes(folder)})

    def actions(self, folder: Path, controller: str) -> list[str]:
        return sorted({r.handler.split(".", 1)[1] for r in controller_routes(folder)
                       if r.handler.split("Controller.", 1)[0].lower() == controller.lower()})

    def completion_items(self, project, path: Path, before: str):
        path = Path(path)
        ext = path.suffix.lower()
        if ext not in (".cs", ".cshtml", ".razor"):
            return None
        ctx = string_context(before)
        if ctx is None:
            return None
        head, prefix = ctx
        folder = Path(project.folder)
        # the controller of the current file: XController.cs or Views/X/...
        ctrl = ""
        if path.stem.endswith("Controller"):
            ctrl = path.stem[:-len("Controller")]
        else:
            try:
                rel = path.resolve().relative_to((folder / "Views").resolve())
                ctrl = rel.parts[0] if len(rel.parts) > 1 else ""
            except ValueError:
                ctrl = ""
        views = views_of(folder)
        if re.search(r"\b(?:Partial)?View\s*\(\s*$", head) or re.search(r"<partial\s+name\s*=\s*$", head) or \
                re.search(r"Html\.Partial(?:Async)?\s*\(\s*$", head):
            items = [(v, "file", f"Views/{ctrl}") for v in views.get(ctrl, [])]
            items += [(v, "file", "Views/Shared") for v in views.get("Shared", [])]
            return filter_prefix(items, prefix)
        m = re.search(r"\b(?:RedirectToAction|Url\.Action|Html\.ActionLink|CreatedAtAction|AcceptedAtAction)\s*\((.*)$",
                      head)
        if m:
            done = re.findall(r"\"([^\"]*)\"", m.group(1))
            if done:                                          # second string = controller
                return filter_prefix([(c, "class", "controller") for c in self.controllers(folder)], prefix)
            return filter_prefix([(a, "method", f"{ctrl}Controller") for a in self.actions(folder, ctrl)], prefix)
        if re.search(r"asp-controller\s*=\s*$", head):
            return filter_prefix([(c, "class", "controller") for c in self.controllers(folder)], prefix)
        if re.search(r"asp-action\s*=\s*$", head):
            cm = re.search(r"asp-controller\s*=\s*\"(\w+)\"", head)
            c = cm.group(1) if cm else ctrl
            return filter_prefix([(a, "method", f"{c}Controller") for a in self.actions(folder, c)], prefix)
        if re.search(r"(?:asp-page|RedirectToPage|Url\.Page)\s*(?:=|\()\s*$", head):
            return filter_prefix([(p, "file", "Razor page") for p in page_names(folder)], prefix)
        if re.search(r"(?:href|action|src)\s*=\s*$|fetch\(\s*$|Redirect\(\s*$|GetAsync\(\s*$", head):
            return filter_prefix([(r.url_path(), "value", f"{r.method} {r.handler}") for r in self.routes(project)],
                                 prefix)
        return None


PLUGIN = AspNetPlugin()

__all__ = ["AspNetPlugin", "PLUGIN", "assembly_info", "controller_routes", "csharp_ls", "dotnet_exe",
           "find_netcoredbg", "install_csharp_ls", "minimal_api_routes", "razor_page_routes", "views_of"]
