"""Ruby on Rails and Sinatra web sites (``rails-web`` plugin).

Ruby: ``ruby`` on PATH, else the portable RubyInstaller in ``%LOCALAPPDATA%\\RADIDE\\toolchains\\ruby``.

- **Rails** needs gems with C code (``nio4r``, ``puma``, ``bigdecimal``, ``rbs`` ...), so it needs the RubyInstaller
  **DevKit** = MSYS2 with the UCRT gcc toolchain. :func:`install_devkit` downloads the official MSYS2 base archive
  (``msys2-base-x86_64-<date>.tar.xz``, sha256 from the release page) into ``toolchains\\msys64`` - next to the
  ``ruby`` folder, where RubyInstaller looks for it - and installs ``base-devel`` + ``mingw-w64-ucrt-x86_64-gcc``
  with pacman. No admin, no registry. The ``rails`` gem itself goes into a private ``GEM_HOME``
  (``%LOCALAPPDATA%\\RADIDE\\tools\\rails-gems``); each app's gems go into its own ``vendor/bundle``.
- **Sinatra** (pure Ruby: sinatra + rackup + webrick) needs no compiler - the template that always works.

Run: ``ruby bin/rails server -p <port> -b 127.0.0.1`` (Rails reloads code by itself) or
``bundle exec ruby app.rb -p <port> -o 127.0.0.1`` (Sinatra; the IDE restarts it when a .rb file changes).
The first run does ``bundle install`` (and for a Rails project that is still empty: ``gem install rails`` +
``rails new .``). Routes come from ``bin/rails routes`` (or config/routes.rb when Rails cannot run), Sinatra routes
from ``get '/x' do`` lines.

Debugging (F5): the server runs as ``ruby -r rails_debug.rb bin/rails server`` - that file sets up the app's bundle
and opens the **debug** gem's remote port (``DEBUGGER__.open(nonstop: true)``, RUBY_DEBUG_PORT); when the server
is ready the IDE attaches over DAP on that TCP port (``radide/debug_more.py`` SocketDap): breakpoints in
controllers, models and ERB views, locals, stepping; a request from the Preview stops there.
The IntelliSense / F12 of Rails apps is ``rails_index.py`` + ``radide/features/rails_ide.py``.
"""
from __future__ import annotations

import hashlib
import os
import re
import tarfile
import urllib.request
from pathlib import Path

from ..project import SiteTemplate, register_template
from .backend_common import (TOOLCHAINS, TOOLS, FrameworkPlugin, Route, Tool, filter_prefix, line_of,
                             read_text, run, string_context, walk_files, which, write_files)

RUBY_HOME = TOOLCHAINS / "ruby"
MSYS_HOME = TOOLCHAINS / "msys64"
RAILS_GEM_HOME = TOOLS / "rails-gems"
MSYS_VERSION = "20260927"
MSYS_URL = (f"https://github.com/msys2/msys2-installer/releases/download/{MSYS_VERSION[:4]}-{MSYS_VERSION[4:6]}-"
            f"{MSYS_VERSION[6:]}/msys2-base-x86_64-{MSYS_VERSION}.tar.xz")
MSYS_PACKAGES = ["base-devel", "mingw-w64-ucrt-x86_64-gcc", "mingw-w64-ucrt-x86_64-pkgconf",
                 "mingw-w64-ucrt-x86_64-libyaml", "mingw-w64-ucrt-x86_64-sqlite3", "mingw-w64-ucrt-x86_64-libffi"]
RAILS_NEW_FLAGS = ["--skip-git", "--skip-docker", "--skip-kamal", "--skip-thruster", "--skip-ci", "--skip-rubocop",
                   "--skip-brakeman", "--skip-solid", "--skip-system-test", "--skip-jbuilder", "--database=sqlite3"]
DEBUG_HOOK = Path(__file__).resolve().with_name("rails_debug.rb")
HTTP_VERBS = ("get", "post", "put", "patch", "delete", "options", "head")


# ============================================================================ tools
def ruby_exe() -> str:
    p = which("ruby")
    if p:
        return p
    p = RUBY_HOME / "bin" / "ruby.exe"
    return str(p) if p.exists() else ""


def ruby_bin_dir() -> Path | None:
    r = ruby_exe()
    return Path(r).parent if r else None


def devkit_installed() -> bool:
    """The IDE's own MSYS2 (toolchains\\msys64) or the one a full RubyInstaller "with DevKit" puts next to Ruby
    (C:\\Ruby33-x64\\msys64) - RubyInstaller finds that one by itself, so ~400 MB need not be downloaded again."""
    homes = [MSYS_HOME]
    rb = ruby_bin_dir()
    if rb is not None:
        homes.append(rb.parent / "msys64")
    return any((h / "ucrt64" / "bin" / "gcc.exe").exists() and (h / "usr" / "bin" / "make.exe").exists()
               for h in homes)


def rails_bin() -> str:
    for p in (RAILS_GEM_HOME / "bin" / "rails",):
        if p.exists():
            return str(p)
    return ""


def ruby_env(project_folder: Path | None = None) -> dict:
    """Environment for ruby / gem / bundle / rails commands: the private GEM_HOME first on the gem path, the
    app's gems in vendor/bundle, ruby + gem bins on PATH."""
    env = {"GEM_HOME": str(RAILS_GEM_HOME), "BUNDLE_SILENCE_ROOT_WARNING": "1",
           "BUNDLE_PATH": "vendor/bundle", "RAILS_ENV": "development", "RACK_ENV": "development"}
    paths = [str(RAILS_GEM_HOME / "bin")]
    rb = ruby_bin_dir()
    if rb is not None:
        paths.append(str(rb))
    if MSYS_HOME.exists():
        env["MSYS2_PATH"] = str(MSYS_HOME)
    env["PATH"] = os.pathsep.join(paths + [os.environ.get("PATH", "")])
    return env


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def install_devkit(log=print) -> bool:
    """Download MSYS2 (official base archive, sha256 checked) into toolchains\\msys64 and install the UCRT gcc
    toolchain - the RubyInstaller DevKit, per user, no admin."""
    if devkit_installed():
        log(f"DevKit already installed: {MSYS_HOME}")
        return True
    bash = MSYS_HOME / "usr" / "bin" / "bash.exe"
    if not bash.exists():
        dl = TOOLCHAINS / "_download"
        dl.mkdir(parents=True, exist_ok=True)
        archive = dl / Path(MSYS_URL).name
        try:
            log(f"Downloading {MSYS_URL} ...")
            with urllib.request.urlopen(MSYS_URL + ".sha256", timeout=60) as r:
                expected = r.read().decode("ascii", "replace").split()[0].lower()
            if not archive.exists() or _sha256(archive) != expected:
                tmp = archive.with_suffix(".part")
                with urllib.request.urlopen(MSYS_URL, timeout=120) as r, open(tmp, "wb") as f:
                    while True:
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                tmp.replace(archive)
            got = _sha256(archive)
            if got != expected:
                log(f"*** checksum mismatch for {archive.name}: {got} != {expected}")
                return False
            log(f"sha256 OK ({expected}); extracting into {TOOLCHAINS} ...")
            with tarfile.open(archive, "r:xz") as t:
                base = TOOLCHAINS.resolve()
                for m in t.getmembers():
                    target = (base / m.name).resolve()
                    if not str(target).startswith(str(base)) or m.issym() or m.islnk():
                        continue                     # no path traversal / links (MSYS2 base has none we need)
                    t.extract(m, base)
        except OSError as e:
            log(f"*** DevKit download failed: {e}")
            return False
    env = {"MSYSTEM": "UCRT64", "CHERE_INVOKING": "1", "MSYS2_PATH_TYPE": "minimal"}
    steps = [["-lc", "true"],                                       # first start: keyring, /etc files
             ["-lc", "pacman -Syuu --noconfirm --disable-download-timeout"],
             ["-lc", "pacman -Syuu --noconfirm --disable-download-timeout"],
             ["-lc", "pacman -S --needed --noconfirm --disable-download-timeout " + " ".join(MSYS_PACKAGES)]]
    for args in steps:
        log("> bash " + " ".join(args))
        code, _out = run([str(bash), *args], cwd=MSYS_HOME, env=env, timeout=3600, log=log)
        if code not in (0,) and "Syuu" not in args[1]:
            log(f"*** exited with code {code}")
            return False
    ok = devkit_installed()
    log("DevKit ready." if ok else "*** DevKit: gcc/make not found after the install")
    return ok


def install_rails(log=print) -> bool:
    """gem install rails into the private GEM_HOME (needs the DevKit for the native gems)."""
    ruby = ruby_exe()
    if not ruby:
        log("*** Ruby was not found (toolchains\\ruby or PATH)")
        return False
    if not devkit_installed() and not install_devkit(log):
        return False
    RAILS_GEM_HOME.mkdir(parents=True, exist_ok=True)
    gem = str(Path(ruby).parent / "gem.cmd") if (Path(ruby).parent / "gem.cmd").exists() else "gem"
    code, _ = run([gem, "install", "rails", "--no-document"], env=ruby_env(), timeout=3600, log=log)
    return code == 0 and bool(rails_bin())


# ============================================================================ templates
SINATRA_FILES = {
    "Gemfile": """source "https://rubygems.org"

gem "sinatra", "~> 4.1"
gem "rackup", "~> 2.2"
gem "webrick", "~> 1.9"
""",
    "app.rb": """# {name} - a Sinatra web application (pure Ruby: no compiler needed).
# Run it with F5 / Ctrl+F5 in RAD IDE: the IDE passes the port with -p.
require "bundler/setup"
require "sinatra"
require "json"

set :bind, "127.0.0.1"
set :views, File.join(__dir__, "views")
set :public_folder, File.join(__dir__, "public")

PRODUCTS = [
  { id: 1, name: "Keyboard", price: 25.0 },
  { id: 2, name: "Mouse", price: 12.5 },
  { id: 3, name: "Monitor", price: 180.0 },
]

get "/" do
  @title = "{name}"
  erb :index
end

get "/products" do
  @products = PRODUCTS
  erb :products
end

get "/products/:id" do
  @product = PRODUCTS.find { |p| p[:id] == params[:id].to_i }
  halt 404, "No such product" unless @product
  erb :product
end

post "/products" do
  PRODUCTS << { id: PRODUCTS.size + 1, name: params[:name].to_s, price: params[:price].to_f }
  redirect "/products"
end

get "/api/products" do
  content_type :json
  PRODUCTS.to_json
end
""",
    "config.ru": """require_relative "app"
run Sinatra::Application
""",
    "views/layout.erb": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title><%= @title || "{name}" %></title>
  <link rel="stylesheet" href="/css/site.css">
</head>
<body>
<header><h1>{name}</h1><nav><a href="/">Home</a> <a href="/products">Products</a></nav></header>
<main><%= yield %></main>
</body>
</html>
""",
    "views/index.erb": """<p>Welcome to <strong><%= @title %></strong> - a Sinatra app made with RAD IDE.</p>
<p>Ruby <%= RUBY_VERSION %>, Sinatra <%= Sinatra::VERSION %>.</p>
""",
    "views/products.erb": """<h2>Products</h2>
<ul>
<% @products.each do |p| %>
  <li><a href="/products/<%= p[:id] %>"><%= p[:name] %></a> - $<%= "%.2f" % p[:price] %></li>
<% end %>
</ul>
<form method="post" action="/products">
  <input name="name" placeholder="Name" required> <input name="price" type="number" step="0.01" placeholder="Price">
  <button>Add</button>
</form>
""",
    "views/product.erb": """<h2><%= @product[:name] %></h2>
<p>Price: $<%= "%.2f" % @product[:price] %></p>
<p><a href="/products">Back</a></p>
""",
    "public/css/site.css": """body { font-family: "Segoe UI", system-ui, sans-serif; margin: 0; background: #f5f6f8; color: #222; }
header { background: #a51d2d; color: #fff; padding: 14px 28px; }
header h1 { margin: 0; font-size: 22px; } nav a { color: #ffd7d7; margin-right: 14px; }
main { max-width: 860px; margin: 24px auto; background: #fff; padding: 20px 28px; border-radius: 8px; }
""",
    ".gitignore": "vendor/\n.bundle/\n",
}


def _create_sinatra(folder: Path, name: str) -> dict:
    write_files(folder, {k: v.replace("{name}", name) for k, v in SINATRA_FILES.items()})
    return {"start": "/", "framework": "sinatra"}


def _create_rails(folder: Path, name: str) -> dict:
    """The Rails skeleton is made by ``rails new`` on the first run (it needs the rails gem + DevKit, which can
    take several minutes the first time) - here only a README that says so."""
    write_files(folder, {"README.md": f"# {name}\n\nA Ruby on Rails application. When the project opens, RAD IDE "
                                      "installs what is missing (DevKit, the rails gem), runs `rails new .`, "
                                      "`bundle install` and `bin/rails db:prepare` (the first F5 does the same). "
                                      "Progress is shown in the Output window.\n"})
    return {"start": "/", "framework": "rails"}


register_template(SiteTemplate("rails-app", "Ruby on Rails App",
                               "A Rails application (rails new when it opens: needs the DevKit + rails gem, "
                               "installed per user by the IDE). SQLite / PostgreSQL / MySQL, Rails menu "
                               "(generators, migrations, console), IntelliSense, debugger, tests.",
                               ("rails-web",), _create_rails, 10, extra={"framework": "rails"}))
register_template(SiteTemplate("sinatra-app", "Sinatra App (pure Ruby)",
                               "A small Sinatra web application with ERB views, a form and a JSON route. Needs no "
                               "compiler (sinatra + rackup + webrick).", ("rails-web",), _create_sinatra, 20,
                               extra={"framework": "sinatra"}))


# ============================================================================ routes / views
ROUTES_LINE = re.compile(r"^\s*(?:(\w+)\s+)?(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD|GET\|POST|[A-Z|]+)\s+(\S+)\s+"
                         r"(\S+#\S+|\S+)\s*$")


def parse_rails_routes_output(text: str) -> list[Route]:
    out = []
    for line in text.splitlines():
        if "Prefix" in line and "Verb" in line:
            continue
        m = ROUTES_LINE.match(line)
        if not m:
            continue
        name, verb, path, handler = m.groups()
        path = path.replace("(.:format)", "")
        out.append(Route(verb, path, handler, name=(name or "")))
    return out


def parse_routes_rb(folder: Path) -> list[Route]:
    """config/routes.rb without running Rails: resources, root, get/post 'x' => 'c#a' / to: 'c#a'."""
    f = folder / "config" / "routes.rb"
    text = read_text(f)
    out: list[Route] = []
    for m in re.finditer(r"^\s*root\s+(?:to:\s*)?['\"]([\w/]+#\w+)['\"]", text, re.M):
        out.append(Route("GET", "/", m.group(1), str(f), line_of(text, m.start()), "root"))
    for m in re.finditer(r"^\s*(get|post|put|patch|delete)\s+['\"]([^'\"]+)['\"]\s*(?:=>|,\s*to:)\s*['\"]([\w/]+#\w+)",
                         text, re.M):
        path = m.group(2) if m.group(2).startswith("/") else "/" + m.group(2)
        out.append(Route(m.group(1).upper(), path, m.group(3), str(f), line_of(text, m.start())))
    for m in re.finditer(r"^\s*(get|post|put|patch|delete)\s+['\"]([^'\"]+)['\"]\s*$", text, re.M):
        path = m.group(2) if m.group(2).startswith("/") else "/" + m.group(2)
        out.append(Route(m.group(1).upper(), path, path.strip("/").replace("/", "#"), str(f), line_of(text, m.start())))
    for m in re.finditer(r"^\s*resources?\s+:(\w+)(.*)$", text, re.M):
        res, rest = m.group(1), m.group(2)
        ln = line_of(text, m.start())
        single = text[m.start():m.end()].lstrip().startswith("resource ")
        actions = ["index", "new", "create", "show", "edit", "update", "destroy"]
        only = re.search(r"only:\s*\[([^\]]*)\]", rest)
        if only:
            actions = re.findall(r":(\w+)", only.group(1))
        base = f"/{res}"
        table = {"index": ("GET", base, f"{res}_path"), "create": ("POST", base, ""),
                 "new": ("GET", f"{base}/new", f"new_{res[:-1] if res.endswith('s') else res}_path"),
                 "show": ("GET", base if single else f"{base}/:id", f"{res[:-1] if res.endswith('s') else res}_path"),
                 "edit": ("GET", f"{base}/edit" if single else f"{base}/:id/edit",
                          f"edit_{res[:-1] if res.endswith('s') else res}_path"),
                 "update": ("PATCH", base if single else f"{base}/:id", ""),
                 "destroy": ("DELETE", base if single else f"{base}/:id", "")}
        for a in actions:
            if a in table:
                verb, path, helper = table[a]
                out.append(Route(verb, path, f"{res}#{a}", str(f), ln, helper))
    return out


def parse_sinatra_routes(folder: Path) -> list[Route]:
    out = []
    for f in walk_files(folder, (".rb",), 500):
        text = read_text(f)
        for m in re.finditer(r"^\s*(get|post|put|patch|delete|options)\s*\(?\s*['\"]([^'\"]+)['\"]", text, re.M):
            out.append(Route(m.group(1).upper(), m.group(2), f"{f.stem}: {m.group(1)} {m.group(2)}", str(f),
                             line_of(text, m.start())))
    return out


def rails_views(folder: Path) -> list[str]:
    root = folder / "app" / "views"
    out = []
    for f in walk_files(root, (".erb", ".haml", ".slim", ".jbuilder"), 3000) if root.is_dir() else []:
        rel = f.relative_to(root).as_posix()
        name = rel.split(".", 1)[0]
        d, _, base = name.rpartition("/")
        out.append((d + "/" if d else "") + base.lstrip("_"))
    return sorted(set(out))


def sinatra_views(folder: Path) -> list[str]:
    root = folder / "views"
    return sorted({f.name.split(".", 1)[0] for f in root.glob("*.erb")}) if root.is_dir() else []


# ============================================================================ plugin
class RailsPlugin(FrameworkPlugin):
    id = "rails-web"
    display_name = "Ruby on Rails / Sinatra Web App"
    framework = "rails"
    framework_title = "Ruby on Rails"
    cli_title = "Rails / Bundler"
    code_ext = ".rb"
    web_kind = "rails"
    default_template = "sinatra-app"
    interpreter_names = ["ruby"]
    tool_names = ["ruby"]
    view_ext = (".erb",)
    install_hint = "Ruby is looked up on PATH and in %LOCALAPPDATA%\\RADIDE\\toolchains\\ruby."
    keywords = ("alias and begin break case class def defined? do else elsif end ensure false for if in module next "
                "nil not or redo rescue retry return self super then true undef unless until when while yield").split()
    builtins = ["puts", "print", "require", "require_relative", "attr_accessor", "params", "render", "redirect_to",
                "before_action", "has_many", "belongs_to", "validates", "erb", "get", "post", "redirect", "halt"]
    line_comments = ["#"]
    string_quotes = ['"', "'"]
    supports_debug = True

    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        return ruby_exe()

    @staticmethod
    def kind_of(project) -> str:
        """"rails" or "sinatra" for a project (by its files, then the template)."""
        folder = Path(project.folder)
        if (folder / "config" / "application.rb").exists() or (folder / "bin" / "rails").exists():
            return "rails"
        if (folder / "app.rb").exists() or (folder / "config.ru").exists():
            return "sinatra"
        from ..project import web_config
        return str(web_config(project).get("framework") or "rails")

    # ---- run
    def backend(self, server) -> dict:
        folder = server.folder
        ruby = server.interpreter or ruby_exe() or "ruby"
        env = ruby_env(folder)
        prepare: list[list[str]] = []
        bundle = [ruby, "-S", "bundle"]
        project = server.project
        kind = self.kind_of(project) if project is not None else "sinatra"
        if kind == "rails" and not (folder / "config" / "application.rb").exists():
            if not rails_bin():
                prepare.append([ruby, "-e", "puts 'Installing the DevKit and the rails gem (first time only)...'"])
                prepare.append(self._installer_argv("rails"))
            from ..project import web_config
            db = str(web_config(project).get("rails_db") or "sqlite3")
            prepare.append([ruby, str(RAILS_GEM_HOME / "bin" / "rails"), "new", ".", "--force",
                            *[f for f in RAILS_NEW_FLAGS if not f.startswith("--database")], f"--database={db}"])
        if not (folder / ".bundle" / "config").exists():
            prepare.append(bundle + ["config", "set", "--local", "path", "vendor/bundle"])
        if not (folder / "Gemfile.lock").exists() or not (folder / "vendor" / "bundle").exists():
            prepare.append(bundle + ["install"])
        if kind == "rails":
            prepare.append([ruby, "bin/rails", "db:prepare"])        # create / migrate the SQLite database
            # own pid file, removed first: a server.pid left by a crashed run would stop "rails server"
            pid = folder / "tmp" / "pids" / "radide-server.pid"
            try:
                pid.unlink()
            except OSError:
                pass
            argv = [ruby, "bin/rails", "server", "-p", "{port}", "-b", "127.0.0.1", "-P", "tmp/pids/radide-server.pid"]
            return {"argv": argv, "cwd": folder, "env": env, "prepare": prepare, "timeout": 180}
        main = "app.rb" if (folder / "app.rb").exists() else ""
        if main:
            argv = bundle + ["exec", "ruby", main, "-p", "{port}", "-o", "127.0.0.1"]
        else:
            argv = bundle + ["exec", "rackup", "-p", "{port}", "-o", "127.0.0.1"]
        return {"argv": argv, "cwd": folder, "env": env, "prepare": prepare, "timeout": 120,
                "restart_on_change": False}

    def debug_backend(self, server, port: int) -> dict:
        """backend() with the debug gem's remote port open (RUBY_DEBUG_PORT) - see rails_debug.rb."""
        spec = self.backend(server)
        argv = list(spec["argv"])
        hook = str(DEBUG_HOOK)
        env = dict(spec.get("env") or {})
        env.update({"RUBY_DEBUG_PORT": str(port), "RUBY_DEBUG_HOST": "127.0.0.1", "RUBY_DEBUG_NO_SIGINT_HOOK": "1",
                    "RUBY_DEBUG_NO_COLOR": "1", "DISABLE_BOOTSNAP_COMPILE_CACHE": "1", "DISABLE_SPRING": "1"})
        if len(argv) > 1 and argv[1] == "bin/rails":                   # ruby bin/rails server ...
            argv[1:1] = ["-r", hook]
        elif "exec" in argv and argv[argv.index("exec") + 1:argv.index("exec") + 2] == ["ruby"]:
            i = argv.index("exec") + 2                                  # bundle exec ruby app.rb ...
            argv[i:i] = ["-r", hook]
        else:                                                           # bundle exec rackup ...
            env["RUBYOPT"] = (env.get("RUBYOPT", "") + f" -r{hook}").strip()
        spec["argv"], spec["env"] = argv, env
        spec["restart_on_change"] = False
        spec["timeout"] = max(int(spec.get("timeout") or 0), 240)
        return spec

    def start_debug(self, win, project, path=None):          # radide/web_site/debug.py start()
        return self.debug_website(win, project, path)

    def debug_website(self, win, project, path=None):
        return debug_rails(win, self, project, path)

    def _installer_argv(self, what: str) -> list[str]:
        """A prepare step that runs install_rails() in a child Python (keeps DevServer's sequential output)."""
        import sys
        code = ("import sys; from radide.web_site.frameworks import rails as r; "
                f"sys.exit(0 if r.install_{what}(lambda t: print(t, flush=True)) else 1)")
        root = Path(__file__).resolve().parents[3]
        return [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(root)!r}); " + code]

    # ---- tools
    def tool_status(self) -> list[Tool]:
        rb = ruby_exe()
        return [Tool("Ruby", rb, "interpreter", "toolchains\\ruby (RubyInstaller)"),
                Tool("DevKit (MSYS2 + gcc)", str(MSYS_HOME) if devkit_installed() else "", "native gems (Rails)",
                     "downloads msys2-base + pacman gcc (~400 MB)", "devkit"),
                Tool("rails gem", rails_bin(), "rails new / generators", "gem install rails (private GEM_HOME)",
                     "rails")]

    def install_tool(self, tool_id: str, log=print) -> bool:
        if tool_id == "devkit":
            return install_devkit(log)
        if tool_id == "rails":
            return install_rails(log)
        return super().install_tool(tool_id, log)

    # ---- CLI
    def cli_presets(self, project) -> list[tuple[str, str]]:
        if self.kind_of(project) == "sinatra":
            return [("Install gems", "bundle install"), ("Add gem", "bundle add {name}"),
                    ("List gems", "bundle list"), ("Update gems", "bundle update"),
                    ("Ruby version", "ruby -v")]
        return [("Generate controller", "rails generate controller {name} index"),
                ("Generate model", "rails generate model {name} name:string"),
                ("Generate scaffold", "rails generate scaffold {name} name:string description:text"),
                ("Generate migration", "rails generate migration {name}"),
                ("Run migrations", "rails db:migrate"), ("Rollback migration", "rails db:rollback"),
                ("Seed database", "rails db:seed"), ("List routes", "rails routes"),
                ("Destroy (undo generate)", "rails destroy controller {name}"),
                ("Install gems", "bundle install"), ("Add gem", "bundle add {name}"),
                ("Run tests", "rails test")]

    def cli_env(self, project) -> dict:
        return ruby_env(Path(project.folder))

    def cli_argv(self, project, command: str) -> list[str]:
        argv = super().cli_argv(project, command)
        if not argv:
            return argv
        ruby = ruby_exe() or "ruby"
        head = argv[0].lower()
        folder = Path(project.folder)
        if head == "rails":
            if (folder / "bin" / "rails").exists():
                return [ruby, "bin/rails", *argv[1:]]
            return [ruby, rails_bin() or "rails", *argv[1:]]
        if head in ("bundle", "gem", "rake", "rackup", "irb"):
            return [ruby, "-S", head, *argv[1:]]
        if head == "ruby":
            return [ruby, *argv[1:]]
        return argv

    # ---- routes / views
    def routes(self, project) -> list[Route]:
        folder = Path(project.folder)
        if self.kind_of(project) == "sinatra":
            return parse_sinatra_routes(folder)
        if (folder / "bin" / "rails").exists() and (folder / "vendor" / "bundle").exists() and ruby_exe():
            code, out = run([ruby_exe(), "bin/rails", "routes"], cwd=folder, env=ruby_env(folder), timeout=90)
            if code == 0:
                routes = parse_rails_routes_output(out)
                if routes:
                    self._attach_files(folder, routes)
                    return routes
        return parse_routes_rb(folder)

    @staticmethod
    def _attach_files(folder: Path, routes: list[Route]) -> None:
        for r in routes:
            if "#" in r.handler:
                ctrl, action = r.handler.split("#", 1)
                f = folder / "app" / "controllers" / f"{ctrl}_controller.rb"
                text = read_text(f)
                if text:
                    m = re.search(rf"^\s*def\s+{re.escape(action)}\b", text, re.M)
                    r.file, r.line = str(f), (line_of(text, m.start()) if m else 1)

    def view_names(self, project) -> list[str]:
        folder = Path(project.folder)
        return sinatra_views(folder) if self.kind_of(project) == "sinatra" else rails_views(folder)

    def completion_items(self, project, path: Path, before: str):
        ext = Path(path).suffix.lower()
        if ext not in (".rb", ".erb"):
            return None
        sinatra = self.kind_of(project) == "sinatra"
        if not sinatra and (Path(project.folder) / "config" / "application.rb").is_file():
            return None      # Rails apps: radide/features/rails_ide.py (merged with ruby-lsp's items)
        if sinatra:
            m = re.search(r"\berb\s*\(?\s*:(\w*)$", before)
            if m:
                return filter_prefix([(v, "file", "view (views/*.erb)") for v in self.view_names(project)], m.group(1))
        ctx = string_context(before)
        if ctx is not None:
            head, prefix = ctx
            if re.search(r"\brender\s*\(?\s*(?:(?:template|partial):\s*)?$", head):
                return filter_prefix([(v, "file", "view") for v in self.view_names(project)], prefix)
            if re.search(r"\b(redirect(?:_to)?|link_to\b.*,|button_to\b.*,|href=|action=|fetch\()\s*\(?\s*$", head):
                return filter_prefix([(r.url_path(), "value", f"{r.method} {r.handler}")
                                      for r in self.routes(project)], prefix)
            return None
        if not sinatra:
            m = re.search(r"\b(?:redirect_to|link_to\b.*,|button_to\b.*,|url_for)\s*\(?\s*(\w*)$", before)
            if m:
                items = [(f"{r.name}_path" if not r.name.endswith("_path") else r.name, "function",
                          f"{r.method} {r.path}") for r in self.routes(project) if r.name]
                return filter_prefix(items, m.group(1))
        return None


PLUGIN = RailsPlugin()


# ============================================================================ debugging (F5)
IVAR_NOISE = {"@marked_for_same_origin_verification", "@rendered_format", "@view_context_class", "@view_renderer",
              "@lookup_context", "@output_buffer", "@virtual_path", "@current_template", "@view_flow"}


def debug_rails(win, plugin, project, path=None):
    """F5 on a Rails / Sinatra site: the server under the debug gem (rails_debug.rb), DAP over TCP."""
    from ...bridgedebug import free_port
    from ...debug_more import make_socket_dap
    from . import debug_support as ds
    ww = ds._prepare(win, project)
    if ww is None:
        return True
    folder = Path(project.folder).resolve()
    bps = win._all_breakpoints()
    port = free_port()

    def make(_pid):
        dap_cls = make_socket_dap()
        # nonstop must be False: the program already runs (DEBUGGER__.open(nonstop: true)), and with
        # nonstop: true the gem queues a "continue" at configurationDone that the first breakpoint then eats
        s = dap_cls(port, "rdbg", {"request": "attach", "nonstop": False, "localfs": True, "cwd": str(folder)},
                    folder, bps, win)
        s.break_on_exception = False
        plain_emit = s._emit_stop

        def emit(info):            # Locals: the @instance variables of self too (controller / view state)
            ref = info.refs.get("%self")
            if not ref:
                plain_emit(info)
                return

            def got(vb, _m):
                for v in (vb or {}).get("variables", []):
                    n = v.get("name", "")
                    if n.startswith("@") and not n.startswith("@_") and n not in IVAR_NOISE:
                        info.variables.append((n, v.get("type", ""), v.get("value", "")))
                        if v.get("variablesReference"):
                            info.refs[n] = v["variablesReference"]
                plain_emit(info)
            s._request("variables", {"variablesReference": ref}, got)
        s._emit_stop = emit
        return s

    win.log(f"------ Debug Ruby site '{project.name}' (debug gem / rdbg on 127.0.0.1:{port}) ------")
    att = ds._Attacher(win, make, "rdbg")
    srv = ww.run_website(win, project, debug=False, path=path,
                         backend_hook=lambda srv, _spec: plugin.debug_backend(srv, port))
    if srv is None:
        return True
    att.srv = srv
    win._rails_attacher = att
    srv.backendReady.connect(att.on_ready)
    srv.stopped.connect(att.on_stopped)
    win.statusBar().showMessage(f"Starting {project.name} under the Ruby debugger (set breakpoints with F9)...")
    return True

__all__ = ["PLUGIN", "RailsPlugin", "debug_rails", "devkit_installed", "install_devkit", "install_rails", "parse_rails_routes_output",
           "parse_routes_rb", "parse_sinatra_routes", "ruby_env", "ruby_exe"]
