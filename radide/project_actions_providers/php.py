"""PHP project actions: Laravel (artisan), CodeIgniter 4 (spark), WordPress (wp-cli) and plain Composer projects.

* **Laravel** - a top-level "Laravel" menu (Serve, Tinker, Route List, Make, Database, Cache, Queue, Composer, npm
  ...), folder menus in Solution Explorer that depend on the clicked folder (``app/Http/Controllers`` -> New
  Controller..., ``app/Models`` -> New Model... with -m -c -f -s, ``database/migrations`` -> New Migration / Migrate
  / Rollback / Status, ``resources/views`` -> New Blade View / Component, ``routes`` -> Route List, ``tests`` -> New
  Test / Run Tests, the project root -> Serve, Tinker, caches, key:generate, storage:link, queue:work ...) and file
  menus (a migration -> Run This Migration, a model -> Open Migration / Controller / Factory, a Blade view -> Open
  the Controller That Renders It, a test -> Run This Test).  Route List and Tinker use the Laravel panel
  (features/php_frameworks.py), Serve is the IDE's own run (DevServer + Preview) for website projects.
* **CodeIgniter 4** - "CodeIgniter" menu with ``spark make:*``, migrate / rollback / seed, routes (the CodeIgniter
  panel), serve and cache:clear; folder menus for app/Controllers, app/Models, app/Database/Migrations,
  app/Database/Seeds, app/Views, app/Filters, app/Entities, app/Commands, app/Config.
* **WordPress** - wp-cli when it is installed (scaffold plugin / theme, plugins, cache and rewrite flush), else
  Open wp-admin in the Preview.
* **PHP** (plain Composer projects, no framework) - PHPUnit / Pest, Pint / PHP-CS-Fixer / PHPStan when installed,
  the PHP built-in server, New Class... with the PSR-4 namespace of composer.json, Run This File.

Composer scripts / install / update and npm scripts of every project come from the generic providers
(generic.py); the Laravel menu repeats the common Composer / npm commands in sub menus.
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from ..project_actions import (Action, Field, Provider, Separator, Submenu, composer_json, composer_requires, matches,
                               package_json, read_text)
from ._common import snake, studly, under, write_new

PHP_BADGE = ("php", "#777BB4")


# ============================================================================ shared helpers
def _vendor_ok(ctx) -> bool:
    return (ctx.folder / "vendor" / "autoload.php").is_file()


def _website(ctx) -> bool:
    try:
        from ..web_site.project import is_website
        return is_website(ctx.project)
    except Exception:  # noqa: BLE001
        return str(getattr(ctx.project, "kind", "") or "").lower() == "website"


def _serve_website(ctx) -> bool:
    """The IDE's own run (DevServer + Preview) for website projects; False = not a website project."""
    if ctx.project is None or not _website(ctx):
        return False
    try:
        from ..features.web_workspace import run_website
        run_website(ctx.win, ctx.project)
        return True
    except Exception as e:  # noqa: BLE001
        ctx.log(f"*** Serve: {e}")
        return False


def chain(ctx, steps: list, title: str = "", opens: str = "none"):
    """Run several commands one after the other (stops at the first failure); returns the first CliRun."""
    steps = [list(s) for s in steps]
    first = {}

    def nxt(run=None):
        if run is not None and run.exit_code != 0:
            return
        if not steps:
            return
        argv = steps.pop(0)
        r = ctx.run_cli(argv, title=" ".join(str(a) for a in argv[:4]), on_done=nxt, opens=opens, stdin="")
        first.setdefault("run", r)
    nxt()
    return first.get("run")


def _pm(folder) -> str:
    try:
        from .generic import NodeScripts
        return NodeScripts.manager(Path(folder))
    except Exception:  # noqa: BLE001
        return "npm"


def npm_items(ctx) -> list:
    """npm install / run dev / run build (only when package.json exists)."""
    if not (ctx.folder / "package.json").is_file():
        return []
    pm = _pm(ctx.folder)
    scripts = package_json(ctx.folder).get("scripts") or {}
    out = [Action("npm-install", f"{pm} install", lambda c: c.run_cli([pm, "install"], title=f"{pm} install"),
                  opens="none", refresh=True)]
    for s in ("dev", "build"):
        if isinstance(scripts, dict) and s in scripts:
            out.append(Action(f"npm-{s}", f"{pm} run {s}", lambda c, s=s: c.run_cli([pm, "run", s], title=f"{pm} run {s}"),
                              opens="none", refresh=s == "build", tip=str(scripts.get(s))[:200]))
    return out


def composer_items() -> list:
    def require(ctx):
        pkgs = ctx.values["package"].split()
        ctx.run_cli(["composer", "require", *pkgs, *(["--dev"] if ctx.values.get("dev") else [])],
                    title=f"composer require {' '.join(pkgs)}")
    return [Action("composer-install", "composer install", lambda c: c.run_cli(["composer", "install"]),
                   opens="none", refresh=True),
            Action("composer-update", "composer update", lambda c: c.run_cli(["composer", "update"]),
                   opens="none", refresh=True),
            Action("composer-require", "Require Package...", require, opens="none", refresh=True,
                   ask=[Field("package", "Package", placeholder="vendor/package"),
                        Field("dev", "Development dependency (--dev)", "bool")]),
            Action("composer-dump", "composer dump-autoload", lambda c: c.run_cli(["composer", "dump-autoload"]),
                   opens="none")]


def _find(folder: Path, base: str, pattern: str) -> list[Path]:
    root = folder / base
    if not root.is_dir():
        return []
    try:
        return sorted(root.rglob(pattern))
    except OSError:
        return []


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _plural(word: str) -> str:
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ies"
    if re.search(r"(s|x|z|ch|sh)$", word):
        return word + "es"
    return word + "s"


@dataclass
class Make:
    """One generator command (``artisan make:x`` / ``spark make:x``)."""
    cmd: str                       # "make:controller"
    title: str                     # "New Controller..."
    base: str                      # the folder the class goes to (sub folders become name prefixes)
    default: str                   # default name
    options: tuple = ()            # (flag, label, kind) kind: "bool" | "text" | ("choice", (..))
    gate: object = None            # callable(folder) -> bool: the command exists in this project
    tip: str = ""

    def fields(self, prefix: str = "") -> list:
        out = [Field("name", "Name", default=prefix + self.default)]
        for flag, label, kind in self.options:
            if kind == "bool":
                out.append(Field(flag, label, "bool"))
            elif isinstance(kind, tuple) and kind[0] == "choice":
                out.append(Field(flag, label, "choice", choices=kind[1], default=kind[1][0]))
            else:
                out.append(Field(flag, label, required=False))
        return out

    def argv(self, values: dict) -> list[str]:
        out = [self.cmd, values["name"].strip().replace("\\", "/")]
        for flag, _label, kind in self.options:
            v = values.get(flag)
            if kind == "bool":
                if v:
                    out.append(flag)
            elif v not in (None, "", "(none)"):
                out.append(f"{flag}={v}" if flag.startswith("--") else f"{flag}{v}")
        return out

    def prefix(self, rel_folder: str) -> str:
        sub = under(rel_folder, self.base)
        return sub + "/" if sub else ""


# ============================================================================ Laravel
def _lv():
    from ..web_site.frameworks import laravel
    return laravel


def _laravel_cmd_exists(name: str):
    """Gate: the Laravel framework of the project has the command class (Laravel 11+ only commands)."""
    def gate(folder: Path) -> bool:
        base = folder / "vendor" / "laravel" / "framework" / "src" / "Illuminate"
        return any((base / d / "Console" / f"{name}.php").is_file() for d in ("Foundation", "Database", "Routing"))
    return gate


LARAVEL_MAKES = [
    Make("make:controller", "New Controller...", "app/Http/Controllers", "PostController",
         (("--resource", "Resource controller (--resource)", "bool"), ("--api", "API controller (--api)", "bool"),
          ("--invokable", "Single action (--invokable)", "bool"), ("--model", "Model (--model, optional)", "text"))),
    Make("make:model", "New Model...", "app/Models", "Post",
         (("-m", "Migration (-m)", "bool"), ("-c", "Controller (-c)", "bool"), ("-f", "Factory (-f)", "bool"),
          ("-s", "Seeder (-s)", "bool"), ("-r", "Resource controller (-r)", "bool"),
          ("-p", "Policy (-p)", "bool"))),
    Make("make:migration", "New Migration...", "database/migrations", "create_posts_table",
         (("--create", "Create table (--create, optional)", "text"), ("--table", "Change table (--table, optional)", "text")),
         tip="create_posts_table creates the posts table; add_title_to_posts_table changes it"),
    Make("make:request", "New Form Request...", "app/Http/Requests", "StorePostRequest"),
    Make("make:middleware", "New Middleware...", "app/Http/Middleware", "EnsureUserIsAdmin"),
    Make("make:resource", "New API Resource...", "app/Http/Resources", "PostResource",
         (("--collection", "Resource collection (--collection)", "bool"),)),
    Make("make:policy", "New Policy...", "app/Policies", "PostPolicy", (("--model", "Model (--model, optional)", "text"),)),
    Make("make:event", "New Event...", "app/Events", "PostPublished"),
    Make("make:listener", "New Listener...", "app/Listeners", "SendPostNotification",
         (("--event", "Event (--event, optional)", "text"), ("--queued", "Queued (--queued)", "bool"))),
    Make("make:job", "New Job...", "app/Jobs", "ProcessPost", (("--sync", "Synchronous (--sync)", "bool"),)),
    Make("make:mail", "New Mailable...", "app/Mail", "PostPublishedMail"),
    Make("make:notification", "New Notification...", "app/Notifications", "PostPublishedNotification"),
    Make("make:rule", "New Validation Rule...", "app/Rules", "Uppercase"),
    Make("make:command", "New Console Command...", "app/Console/Commands", "SendEmails"),
    Make("make:observer", "New Observer...", "app/Observers", "PostObserver", (("--model", "Model (--model, optional)", "text"),)),
    Make("make:cast", "New Cast...", "app/Casts", "Json"),
    Make("make:enum", "New Enum...", "app/Enums", "Status", gate=_laravel_cmd_exists("EnumMakeCommand")),
    Make("make:exception", "New Exception...", "app/Exceptions", "PostNotFoundException"),
    Make("make:provider", "New Service Provider...", "app/Providers", "PostServiceProvider"),
    Make("make:factory", "New Factory...", "database/factories", "PostFactory", (("--model", "Model (--model, optional)", "text"),)),
    Make("make:seeder", "New Seeder...", "database/seeders", "PostSeeder"),
    Make("make:test", "New Test...", "tests/Feature", "PostTest", (("--unit", "Unit test (--unit)", "bool"),)),
    Make("make:component", "New Component...", "app/View/Components", "Alert",
         (("--view", "Anonymous component - only a Blade view (--view)", "bool"),)),
    Make("make:livewire", "New Livewire Component...", "app/Livewire", "Counter",
         gate=lambda f: composer_requires(f, "livewire/livewire")),
]
MAKE_BY_CMD = {m.cmd: m for m in LARAVEL_MAKES}
# folder (and below) -> generators shown first in its context menu
LARAVEL_FOLDERS = [
    ("app/Http/Controllers", ["make:controller"]),
    ("app/Http/Requests", ["make:request"]),
    ("app/Http/Middleware", ["make:middleware"]),
    ("app/Http/Resources", ["make:resource"]),
    ("app/Http", ["make:controller", "make:request", "make:middleware", "make:resource"]),
    ("app/Models", ["make:model"]),
    ("app/Policies", ["make:policy"]),
    ("app/Events", ["make:event"]),
    ("app/Listeners", ["make:listener"]),
    ("app/Jobs", ["make:job"]),
    ("app/Mail", ["make:mail"]),
    ("app/Notifications", ["make:notification"]),
    ("app/Rules", ["make:rule"]),
    ("app/Console", ["make:command"]),
    ("app/Observers", ["make:observer"]),
    ("app/Casts", ["make:cast"]),
    ("app/Enums", ["make:enum"]),
    ("app/Exceptions", ["make:exception"]),
    ("app/Providers", ["make:provider"]),
    ("app/View/Components", ["make:component"]),
    ("app/Livewire", ["make:livewire"]),
    ("database/factories", ["make:factory"]),
    ("database/seeders", ["make:seeder"]),
]
VIEW_CALL = r"(?:\bview|View::make|->view|View::first|Inertia::render|->markdown|->make)\s*\(\s*['\"]{name}['\"]"
ROUTE_VIEW = r"Route::view\s*\([^,]+,\s*['\"]{name}['\"]"


def artisan(ctx, *args, title: str | None = None, opens: str | None = None, on_done=None, interactive: bool = False):
    """``php artisan <args>`` -> Output window (stdin closed, --no-interaction)."""
    argv = ["php", "artisan", *[str(a) for a in args]]
    if not interactive:
        argv.append("--no-interaction")
    return ctx.run_cli(argv, title=title or "artisan " + " ".join(str(a) for a in args[:3]), opens=opens,
                       on_done=on_done, stdin="")


class Laravel(Provider):
    id, title, priority = "laravel", "Laravel", 50
    icon = ("Lv", "#F9322C")
    markers = ("artisan", "composer.json")

    def detect(self, folder, project):
        return (folder / "artisan").is_file() and _lv().is_laravel(folder)

    # ------------------------------------------------------------ building blocks
    def make(self, m: Make, rel_folder: str = "") -> Action:
        prefix = m.prefix(rel_folder) if rel_folder else ""

        def run(ctx):
            artisan(ctx, *m.argv(ctx.values), title=f"artisan {m.cmd} {ctx.values['name']}")
        return Action(m.cmd.replace(":", "-"), m.title, run, ask=m.fields(prefix), enabled=_vendor_ok,
                      tip=m.tip or f"php artisan {m.cmd}")

    def makes(self, folder: Path, cmds, rel_folder: str = "") -> list:
        out = []
        for c in cmds:
            m = MAKE_BY_CMD[c]
            if m.gate is None or m.gate(folder):
                out.append(self.make(m, rel_folder))
        return out

    def new_view(self, ctx, rel_folder: str = "") -> Action:
        sub = under(rel_folder, "resources/views")
        layout = "layouts.app" if (ctx.folder / "resources/views/layouts/app.blade.php").is_file() else ""
        return Action("make-view", "New Blade View...", self._new_view, enabled=lambda c: True,
                      ask=[Field("name", "Name", default=(sub.replace("/", ".") + "." if sub else "") + "index",
                                 help="dot or slash notation: posts.index = resources/views/posts/index.blade.php"),
                           Field("layout", "Layout (@extends, optional)", default=layout, required=False)])

    def _new_view(self, ctx):
        name = ctx.values["name"].strip().replace("\\", "/")
        name = name[:-len(".blade.php")] if name.endswith(".blade.php") else name
        dotted = name.strip("/").replace("/", ".")
        layout = (ctx.values.get("layout") or "").strip()
        if not layout and _vendor_ok(ctx) and _laravel_cmd_exists("ViewMakeCommand")(ctx.folder):
            artisan(ctx, "make:view", dotted, title=f"artisan make:view {dotted}")
            return
        rel = "resources/views/" + dotted.replace(".", "/") + ".blade.php"
        title = dotted.split(".")[-1].replace("-", " ").replace("_", " ").title()
        if layout:
            text = (f"@extends('{layout}')\n\n@section('title', '{title}')\n\n@section('content')\n"
                    f"    <h1>{title}</h1>\n@endsection\n")
        else:
            text = "<div>\n    {{-- " + title + " --}}\n</div>\n"
        write_new(ctx, rel, text)

    def new_anonymous_component(self, rel_folder: str) -> Action:
        sub = under(rel_folder, "resources/views/components")
        m = MAKE_BY_CMD["make:component"]

        def run(ctx):
            name = ctx.values["name"].strip().replace("/", ".")
            argv = ["make:component", name] + (["--view"] if ctx.values.get("--view") else [])
            artisan(ctx, *argv, title=f"artisan make:component {name}")
        return Action("make-component", "New Component...", run, enabled=_vendor_ok,
                      ask=[Field("name", "Name", default=(sub.replace("/", ".") + "." if sub else "") + "alert"),
                           Field("--view", "Anonymous component - only a Blade view (--view)", "bool", default=True)],
                      tip=m.tip or "php artisan make:component")

    def serve(self) -> Action:
        def run(ctx):
            if not _serve_website(ctx):
                artisan(ctx, "serve", title="artisan serve", opens="none")
        return Action("serve", "Serve", run, toolbar=True, opens="none", icon="SP_MediaPlay",
                      tip="Run the site (the IDE's DevServer + Preview; php artisan serve for other projects)")

    def tinker(self) -> Action:
        def run(ctx):
            panel, dock = getattr(ctx.win, "laravel_panel", None), getattr(ctx.win, "dock_laravel", None)
            if panel is None or dock is None:
                ctx.run_in_terminal(["php", "artisan", "tinker"])
                return
            self._panel_project(ctx, panel)
            dock.show()
            dock.raise_()
            panel.tabs.setCurrentIndex(2)
            panel.start_tinker()
            panel.tinker_in.setFocus()
        return Action("tinker", "Tinker", run, opens="none", enabled=_vendor_ok, toolbar=True,
                      tip="The Tinker console of the Laravel panel (PHP with the application booted)")

    @staticmethod
    def _panel_project(ctx, panel) -> None:
        if ctx.project is getattr(ctx.win, "project", None):
            panel.sync_project()
        if panel.project is not ctx.project and ctx.project is not None:
            panel.stop_tinker()
            panel.project = ctx.project
            panel.refresh()

    def route_list(self) -> Action:
        def run(ctx):
            panel, dock = getattr(ctx.win, "laravel_panel", None), getattr(ctx.win, "dock_laravel", None)
            if panel is None or dock is None:
                artisan(ctx, "route:list", title="artisan route:list", opens="none")
                return
            self._panel_project(ctx, panel)
            dock.show()
            dock.raise_()
            panel.tabs.setCurrentIndex(1)
            rows = panel.fill_routes()
            ctx.log(f"[Laravel] {len(rows)} routes (Laravel panel > Routes; double-click a route for its code)")
        return Action("route-list", "Route List", run, opens="none", toolbar=True,
                      tip="php artisan route:list in the Routes tab of the Laravel panel")

    def migrate(self) -> Action:
        return Action("migrate", "Migrate", lambda c: artisan(c, "migrate", "--force", title="artisan migrate"),
                      opens="none", enabled=_vendor_ok, toolbar=True, tip="php artisan migrate")

    def database_items(self, ctx, rel_folder: str = "") -> list:
        seeders = [p.stem for p in _find(ctx.folder, "database/seeders", "*.php")]

        def fresh(c):
            if c.confirm("migrate:fresh DROPS ALL TABLES of the database and runs every migration again "
                         "(then the seeders).\n\nContinue?"):
                artisan(c, "migrate:fresh", "--seed", "--force", title="artisan migrate:fresh --seed")
        items = [self.migrate(),
                 Action("migrate-rollback", "Rollback", lambda c: artisan(c, "migrate:rollback", "--force",
                                                                          title="artisan migrate:rollback"),
                        opens="none", enabled=_vendor_ok, tip="php artisan migrate:rollback (the last batch)"),
                 Action("migrate-status", "Migration Status", lambda c: artisan(c, "migrate:status",
                                                                               title="artisan migrate:status"),
                        opens="none", enabled=_vendor_ok),
                 Action("migrate-fresh", "Fresh Database + Seed (migrate:fresh --seed)...", fresh, opens="none",
                        enabled=_vendor_ok),
                 Separator(),
                 Action("db-seed", "Seed (db:seed)", lambda c: artisan(c, "db:seed", "--force", title="artisan db:seed"),
                        opens="none", enabled=_vendor_ok)]
        if seeders:
            items.append(Action("db-seed-class", "Run Seeder...",
                                lambda c: artisan(c, "db:seed", "--class=" + c.values["class"], "--force",
                                                  title=f"artisan db:seed {c.values['class']}"),
                                opens="none", enabled=_vendor_ok,
                                ask=[Field("class", "Seeder", "choice", choices=seeders,
                                           default="DatabaseSeeder" if "DatabaseSeeder" in seeders else seeders[0])]))
        items += [Separator(), *self.makes(ctx.folder, ["make:migration", "make:seeder", "make:factory"], rel_folder)]
        return items

    def cache_items(self) -> list:
        def a(cmd, title=None, tip=""):
            return Action(cmd.replace(":", "-"), title or cmd, lambda c: artisan(c, cmd, title=f"artisan {cmd}"),
                          opens="none", enabled=_vendor_ok, tip=tip or f"php artisan {cmd}")
        return [a("optimize:clear", "Clear All Caches (optimize:clear)"), Separator(),
                a("cache:clear"), a("config:clear"), a("route:clear"), a("view:clear"), a("event:clear"), Separator(),
                a("optimize", "Cache Everything (optimize)"), a("config:cache"), a("route:cache"), a("view:cache")]

    def queue_action(self, ctx) -> Action:
        key = os.path.normcase(str(ctx.folder))
        run = _QUEUE.get(key)
        on = run is not None and run.is_running()

        def toggle(c):
            r = _QUEUE.get(key)
            if r is not None and r.is_running():
                r.cancel()
                _QUEUE.pop(key, None)
                return
            _QUEUE[key] = artisan(c, "queue:work", title="artisan queue:work", opens="none")
        return Action("queue-work", "Stop Queue Worker" if on else "Start Queue Worker (queue:work)", toggle,
                      opens="none", enabled=_vendor_ok, tip="php artisan queue:work (runs until you stop it)")

    def ide_helper(self) -> Action:
        def run(ctx):
            gen = [["php", "artisan", "ide-helper:generate", "--no-interaction"],
                   ["php", "artisan", "ide-helper:models", "--nowrite", "--no-interaction"],
                   ["php", "artisan", "ide-helper:meta", "--no-interaction"]]
            if composer_requires(ctx.folder, "barryvdh/laravel-ide-helper"):
                chain(ctx, gen)
            elif ctx.confirm("Add barryvdh/laravel-ide-helper as a development dependency (composer require "
                             "--dev) and generate the helper files?"):
                chain(ctx, [["composer", "require", "--dev", "barryvdh/laravel-ide-helper"], *gen])
        return Action("ide-helper", "Regenerate IDE Helper Files", run, opens="none", enabled=_vendor_ok,
                      tip="_ide_helper.php, _ide_helper_models.php, .phpstorm.meta.php (laravel-ide-helper): "
                          "IntelliSense for facades and model columns")

    def project_items(self, ctx) -> list:
        """Serve, Tinker, keys, links, scheduler ... (the project root's commands)."""
        items = [self.serve(), self.tinker(), self.route_list(), Separator(),
                 Action("key-generate", "Generate App Key (key:generate)",
                        lambda c: artisan(c, "key:generate", "--force", title="artisan key:generate"),
                        opens="none", enabled=_vendor_ok),
                 Action("storage-link", "Link Storage (storage:link)",
                        lambda c: artisan(c, "storage:link", title="artisan storage:link"), opens="none",
                        enabled=_vendor_ok, refresh=True),
                 Action("schedule-run", "Run Scheduled Tasks (schedule:run)",
                        lambda c: artisan(c, "schedule:run", title="artisan schedule:run"), opens="none",
                        enabled=_vendor_ok),
                 self.queue_action(ctx), self.ide_helper()]
        try:
            needs = _lv().needs_setup(ctx.folder)
        except Exception:  # noqa: BLE001
            needs = []
        if needs:
            items.insert(0, Action("prepare", "Prepare Project (" + ", ".join(needs) + ")...", self._prepare,
                                   opens="none", refresh=True,
                                   tip="composer install, .env + APP_KEY, the SQLite database, npm install / build"))
        return items

    @staticmethod
    def _prepare(ctx):
        try:
            from ..features.php_frameworks import prepare_project
            prepare_project(ctx.win, ctx.project, ask=False)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"*** Prepare Project: {e}")

    def test_items(self, ctx, rel_folder: str = "") -> list:
        m = MAKE_BY_CMD["make:test"]
        unit = matches(rel_folder, "tests/Unit/**")
        sub = under(rel_folder, "tests/Unit" if unit else "tests/Feature")
        opts = [Field("name", "Name", default=(sub + "/" if sub else "") + "PostTest"),
                Field("--unit", "Unit test (--unit)", "bool", default=unit)]
        if composer_requires(ctx.folder, "pestphp/pest"):
            opts.append(Field("--pest", "Pest test (--pest)", "bool", default=True))

        def new(c):
            argv = ["make:test", c.values["name"].strip()]
            argv += [f for f in ("--unit", "--pest") if c.values.get(f)]
            artisan(c, *argv, title=f"artisan make:test {c.values['name']}")
        return [Action("make-test", m.title, new, ask=opts, enabled=_vendor_ok),
                Action("test", "Run Tests", lambda c: artisan(c, "test", title="artisan test", interactive=True),
                       opens="none", enabled=_vendor_ok, tip="php artisan test")]

    # ------------------------------------------------------------ Provider API
    def actions(self, ctx):
        f = ctx.folder
        make_all = self.makes(f, [m.cmd for m in LARAVEL_MAKES])
        make_all.insert(next(i for i, a in enumerate(make_all) if a.id == "make-migration"), self.new_view(ctx))
        out = [*self.project_items(ctx), Separator(),
               Submenu("Make", make_all),
               Submenu("Database", self.database_items(ctx)),
               Submenu("Cache", self.cache_items()),
               Submenu("Tests", self.test_items(ctx)),
               Separator(),
               Submenu("Composer", composer_items())]
        npm = npm_items(ctx)
        if npm:
            out.append(Submenu("npm", npm))
        return out

    def folder_actions(self, ctx, rel_folder):
        f = ctx.folder
        r = rel_folder
        if r == "":
            return [*self.project_items(ctx), Separator(), Submenu("Cache", self.cache_items()),
                    Submenu("Database", self.database_items(ctx))]
        for base, cmds in LARAVEL_FOLDERS:
            if matches(r, base + "/**"):
                return self.makes(f, cmds, r)
        if matches(r, "app"):
            return [Submenu("Make", self.makes(f, [m.cmd for m in LARAVEL_MAKES if m.base.startswith("app/")]))]
        if matches(r, "database/migrations/**"):
            items = self.database_items(ctx, r)
            mig = next(i for i, a in enumerate(items) if isinstance(a, Action) and a.id == "make-migration")
            return [items[mig], Separator(), *items[:mig - 1]]
        if matches(r, "database"):
            return self.database_items(ctx)
        if matches(r, "resources/views/components/**"):
            return [self.new_anonymous_component(r), self.new_view(ctx, r)]
        if matches(r, "resources/views/**"):
            items = [self.new_view(ctx, r), self.new_anonymous_component("")]
            if composer_requires(f, "livewire/livewire"):
                items += self.makes(f, ["make:livewire"])
            return items
        if matches(r, "resources"):
            return [self.new_view(ctx), *npm_items(ctx)]
        if matches(r, "routes/**"):
            return [self.route_list(), Separator(),
                    *[Action(c.replace(":", "-"), c, lambda x, c=c: artisan(x, c, title=f"artisan {c}"),
                             opens="none", enabled=_vendor_ok) for c in ("route:cache", "route:clear")]]
        if matches(r, "tests/**"):
            return self.test_items(ctx, r)
        if matches(r, "config/**"):
            return [Action(c.replace(":", "-"), c, lambda x, c=c: artisan(x, c, title=f"artisan {c}"), opens="none",
                           enabled=_vendor_ok) for c in ("config:clear", "config:cache")]
        if matches(r, "storage", "public"):
            return [Action("storage-link", "Link Storage (storage:link)",
                           lambda c: artisan(c, "storage:link", title="artisan storage:link"), opens="none",
                           enabled=_vendor_ok, refresh=True)]
        return []

    def file_actions(self, ctx, rel_file):
        r = rel_file
        if matches(r, "database/migrations/*.php"):
            return [Action("migrate-this", "Run This Migration",
                           lambda c: artisan(c, "migrate", "--path=" + r, "--force", title=f"artisan migrate {Path(r).name}"),
                           opens="none", enabled=_vendor_ok, tip=f"php artisan migrate --path={r}"),
                    Action("rollback-this", "Rollback This Migration",
                           lambda c: artisan(c, "migrate:rollback", "--path=" + r, "--force",
                                             title=f"artisan migrate:rollback {Path(r).name}"),
                           opens="none", enabled=_vendor_ok, tip=f"php artisan migrate:rollback --path={r}")]
        if matches(r, "app/Models/**/*.php"):
            model = Path(r).stem
            out = []
            for title, fn in (("Open Migration", self.model_migration), ("Open Controller", self.model_controller),
                              ("Open Factory", self.model_factory)):
                found = fn(ctx.folder, model, ctx.path(r))
                out.append(Action(f"open-{title.split()[-1].lower()}", title,
                                  lambda c, p=found: p and c.open_file(p[0], p[1]), opens="none",
                                  enabled=lambda c, p=found: bool(p),
                                  tip=ctx.rel(found[0]) if found else f"no {title.split()[-1].lower()} of {model} found"))
            if not out[1].is_enabled(ctx):
                out.append(self.make(MAKE_BY_CMD["make:controller"]))
                out[-1].ask[0].default = f"{model}Controller"
                out[-1].ask[-1].default = model
            return out
        if r.endswith(".blade.php") and matches(r, "resources/views/**"):
            found = self.view_controller(ctx.folder, ctx.path(r))
            return [Action("open-view-controller", "Open the Controller That Renders It",
                           lambda c: found and c.open_file(found[0], found[1]), opens="none",
                           enabled=lambda c: bool(found),
                           tip=f"{ctx.rel(found[0])}:{found[1]}" if found else "no view() call found in app/ or routes/")]
        if matches(r, "tests/**/*Test.php", "tests/**/*.php"):
            return [Action("test-this", "Run This Test",
                           lambda c: artisan(c, "test", r, title=f"artisan test {Path(r).name}", interactive=True),
                           opens="none", enabled=_vendor_ok)]
        if matches(r, "routes/*.php"):
            return [self.route_list()]
        if r == ".env":
            return [Action("config-clear", "config:clear", lambda c: artisan(c, "config:clear", title="artisan config:clear"),
                           opens="none", enabled=_vendor_ok)]
        return []

    # ------------------------------------------------------------ "go to" helpers
    @staticmethod
    def model_table(model: str, path: Path | None = None) -> str:
        if path is not None:
            m = re.search(r"\$table\s*=\s*['\"](\w+)['\"]", read_text(path))
            if m:
                return m.group(1)
        return _plural(snake(model))

    def model_migration(self, folder: Path, model: str, path: Path | None = None):
        table = self.model_table(model, path)
        rx = re.compile(r"Schema::create\s*\(\s*['\"]" + re.escape(table) + r"['\"]")
        for p in _find(folder, "database/migrations", "*.php"):
            text = read_text(p)
            m = rx.search(text)
            if m:
                return p, _line_of(text, m.start())
        for p in _find(folder, "database/migrations", f"*create_{table}_table*.php"):
            return p, 1
        return None

    def model_controller(self, folder: Path, model: str, _path=None):
        for p in _find(folder, "app/Http/Controllers", f"{model}Controller.php"):
            return p, 1
        return None

    def model_factory(self, folder: Path, model: str, _path=None):
        for p in _find(folder, "database/factories", f"{model}Factory.php"):
            return p, 1
        return None

    def view_controller(self, folder: Path, view: Path):
        name = _lv().view_name_of(folder, view)
        if not name:
            return None
        alt = "(?:" + re.escape(name) + "|" + re.escape(name.replace(".", "/")) + ")"
        rx = re.compile(VIEW_CALL.format(name=alt) + "|" + ROUTE_VIEW.format(name=alt))
        cands = _find(folder, "app/Http/Controllers", "*.php") + _find(folder, "app", "*.php") + \
            _find(folder, "routes", "*.php")
        seen = set()
        for p in cands:
            if p in seen:
                continue
            seen.add(p)
            text = read_text(p)
            m = rx.search(text)
            if m:
                return p, _line_of(text, m.start())
        return None


_QUEUE: dict = {}


# ============================================================================ CodeIgniter 4
def _ci():
    from ..web_site.frameworks import codeigniter
    return codeigniter


CI_MAKES = [
    Make("make:controller", "New Controller...", "app/Controllers", "Products",
         (("--restful", "RESTful", ("choice", ("(none)", "controller", "presenter"))),)),
    Make("make:model", "New Model...", "app/Models", "ProductModel",
         (("--table", "Table (--table, optional)", "text"),
          ("--return", "Return type", ("choice", ("array", "object", "entity"))))),
    Make("make:migration", "New Migration...", "app/Database/Migrations", "CreateProductsTable"),
    Make("make:seeder", "New Seeder...", "app/Database/Seeds", "ProductSeeder"),
    Make("make:filter", "New Filter...", "app/Filters", "AuthFilter"),
    Make("make:entity", "New Entity...", "app/Entities", "Product"),
    Make("make:command", "New Command...", "app/Commands", "SendEmails"),
    Make("make:config", "New Config...", "app/Config", "Shop"),
    Make("make:validation", "New Validation...", "app/Validation", "ProductRules"),
    Make("make:cell", "New View Cell...", "app/Cells", "AlertMessageCell"),
]
CI_BY_CMD = {m.cmd: m for m in CI_MAKES}
CI_FOLDERS = [
    ("app/Controllers", ["make:controller"]),
    ("app/Models", ["make:model", "make:entity"]),
    ("app/Database/Seeds", ["make:seeder"]),
    ("app/Filters", ["make:filter"]),
    ("app/Entities", ["make:entity"]),
    ("app/Commands", ["make:command"]),
    ("app/Config", ["make:config"]),
    ("app/Validation", ["make:validation"]),
    ("app/Cells", ["make:cell"]),
]


def spark(ctx, *args, title: str | None = None, opens: str | None = None, on_done=None):
    """``php spark <args>`` -> Output window (stdin closed: prompts take their defaults)."""
    try:
        if _ci().ensure_env(ctx.folder):          # a sample / cloned site without .env: SQLite development env
            ctx.log("[CodeIgniter] .env created from the template")
    except Exception:  # noqa: BLE001
        pass
    return ctx.run_cli(["php", "spark", *[str(a) for a in args]], title=title or "spark " + " ".join(map(str, args[:3])),
                       opens=opens, on_done=on_done, stdin="")


class CodeIgniter(Provider):
    id, title, priority = "codeigniter", "CodeIgniter", 50
    icon = ("CI", "#DD4814")
    markers = ("spark", "composer.json")

    def detect(self, folder, project):
        return (folder / "spark").is_file() and _ci().is_codeigniter(folder)

    def make(self, m: Make, rel_folder: str = "") -> Action:
        prefix = m.prefix(rel_folder) if rel_folder else ""

        def run(ctx):
            vals = dict(ctx.values)
            if m.cmd == "make:migration" and prefix:
                vals["name"] = vals["name"].split("/")[-1]
            spark(ctx, *m.argv(vals), title=f"spark {m.cmd} {vals['name']}")
        return Action(m.cmd.replace(":", "-"), m.title, run, ask=m.fields("" if m.cmd == "make:migration" else prefix),
                      enabled=_vendor_ok, tip=f"php spark {m.cmd}")

    def makes(self, cmds, rel_folder: str = "") -> list:
        return [self.make(CI_BY_CMD[c], rel_folder) for c in cmds]

    def new_view(self, rel_folder: str = "") -> Action:
        sub = under(rel_folder, "app/Views")

        def run(ctx):
            name = ctx.values["name"].strip().replace("\\", "/").strip("/")
            name = name[:-4] if name.endswith(".php") else name
            title = name.split("/")[-1].replace("_", " ").replace("-", " ").title()
            layout = (ctx.values.get("layout") or "").strip()
            if layout:
                text = (f"<?= $this->extend('{layout}') ?>\n\n<?= $this->section('content') ?>\n"
                        f"<h1>{title}</h1>\n<?= $this->endSection() ?>\n")
            else:
                text = f"<h1>{title}</h1>\n"
            write_new(ctx, f"app/Views/{name}.php", text)
        return Action("new-view", "New View...", run,
                      ask=[Field("name", "Name", default=(sub + "/" if sub else "") + "index"),
                           Field("layout", "Layout ($this->extend, optional)", required=False,
                                 default="")])

    def serve(self) -> Action:
        def run(ctx):
            if not _serve_website(ctx):
                spark(ctx, "serve", title="spark serve", opens="none")
        return Action("serve", "Serve", run, toolbar=True, opens="none", icon="SP_MediaPlay",
                      tip="Run the site (the IDE's DevServer + Preview; php spark serve for other projects)")

    def routes(self) -> Action:
        def run(ctx):
            panel, dock = getattr(ctx.win, "codeigniter", None), getattr(ctx.win, "dock_codeigniter", None)
            if panel is None or dock is None:
                spark(ctx, "routes", title="spark routes", opens="none")
                return
            if panel.project is not ctx.project and ctx.project is not None:
                panel.project = ctx.project
                panel.refresh(force=True)
            else:
                panel.load_routes()
            dock.show()
            dock.raise_()
            panel.tabs.setCurrentIndex(1)
        return Action("routes", "Routes", run, opens="none", toolbar=True,
                      tip="php spark routes in the Routes tab of the CodeIgniter panel")

    def database_items(self, ctx, rel_folder: str = "") -> list:
        seeders = [p.stem for p in _find(ctx.folder, "app/Database/Seeds", "*.php")]
        items = [Action("migrate", "Migrate", lambda c: spark(c, "migrate", "--all", title="spark migrate"),
                        opens="none", enabled=_vendor_ok, toolbar=True),
                 Action("migrate-rollback", "Rollback", lambda c: spark(c, "migrate:rollback", "-f",
                                                                        title="spark migrate:rollback"),
                        opens="none", enabled=_vendor_ok),
                 Action("migrate-status", "Migration Status", lambda c: spark(c, "migrate:status",
                                                                             title="spark migrate:status"),
                        opens="none", enabled=_vendor_ok)]
        if seeders:
            items.append(Action("db-seed", "Run Seeder (db:seed)...",
                                lambda c: spark(c, "db:seed", c.values["class"], title=f"spark db:seed {c.values['class']}"),
                                opens="none", enabled=_vendor_ok,
                                ask=[Field("class", "Seeder", "choice", choices=seeders, default=seeders[0])]))
        items += [Separator(), *self.makes(["make:migration", "make:seeder"], rel_folder)]
        return items

    def actions(self, ctx):
        return [self.serve(), self.routes(), Separator(),
                Submenu("Make", [*self.makes([m.cmd for m in CI_MAKES]), self.new_view()]),
                Submenu("Database", self.database_items(ctx)),
                Action("cache-clear", "Clear Cache (cache:clear)", lambda c: spark(c, "cache:clear", title="spark cache:clear"),
                       opens="none", enabled=_vendor_ok),
                Action("env", "Show Environment (env)", lambda c: spark(c, "env", title="spark env"), opens="none",
                       enabled=_vendor_ok),
                Separator(), Submenu("Composer", composer_items())]

    def folder_actions(self, ctx, rel_folder):
        r = rel_folder
        if r == "":
            return [self.serve(), self.routes(), Separator(),
                    Submenu("Database", self.database_items(ctx)),
                    Action("cache-clear", "Clear Cache (cache:clear)",
                           lambda c: spark(c, "cache:clear", title="spark cache:clear"), opens="none",
                           enabled=_vendor_ok)]
        if matches(r, "app/Database/Migrations/**"):
            items = self.database_items(ctx, r)
            return [items[-2], Separator(), *items[:-3]]
        if matches(r, "app/Database/Seeds/**"):
            items = self.database_items(ctx, r)
            return [items[-1], *[a for a in items if isinstance(a, Action) and a.id == "db-seed"]]
        if matches(r, "app/Database"):
            return self.database_items(ctx)
        if matches(r, "app/Views/**"):
            return [self.new_view(r), *self.makes(["make:cell"])]
        for base, cmds in CI_FOLDERS:
            if matches(r, base + "/**"):
                return self.makes(cmds, r)
        if matches(r, "app"):
            return [Submenu("Make", [*self.makes([m.cmd for m in CI_MAKES]), self.new_view()])]
        return []

    def file_actions(self, ctx, rel_file):
        r = rel_file
        if matches(r, "app/Database/Seeds/*.php"):
            cls = Path(r).stem
            return [Action("seed-this", "Run This Seeder", lambda c: spark(c, "db:seed", cls, title=f"spark db:seed {cls}"),
                           opens="none", enabled=_vendor_ok)]
        if matches(r, "app/Database/Migrations/*.php"):
            return [Action("migrate", "Migrate", lambda c: spark(c, "migrate", "--all", title="spark migrate"),
                           opens="none", enabled=_vendor_ok)]
        if matches(r, "app/Config/Routes.php"):
            return [self.routes()]
        return []


# ============================================================================ WordPress
def _wp_cli(folder: Path) -> list[str]:
    """argv prefix of wp-cli ([] = not installed): ``wp`` on PATH, else a wp-cli.phar (project / toolchains)."""
    exe = shutil.which("wp.bat") or shutil.which("wp.cmd") or shutil.which("wp")
    if exe:
        return [exe]
    cands = [folder / "wp-cli.phar", Path(os.environ.get("LOCALAPPDATA", "")) / "RADIDE" / "toolchains" / "wp-cli.phar"]
    for p in cands:
        if p.is_file():
            return ["php", str(p)]
    return []


class WordPress(Provider):
    id, title, priority = "wordpress", "WordPress", 45
    icon = ("WP", "#21759B")
    markers = ("wp-config.php", "wp-config-sample.php", "wp-load.php")

    def detect(self, folder, project):
        return (folder / "wp-load.php").is_file() or ((folder / "wp-content").is_dir() and
                                                      ((folder / "wp-config.php").is_file() or
                                                       (folder / "wp-config-sample.php").is_file()))

    @staticmethod
    def wp(ctx, *args, title=None):
        pre = _wp_cli(ctx.folder)
        return ctx.run_cli([*pre, *args, f"--path={ctx.folder}"], title=title or "wp " + " ".join(args[:3]), stdin="")

    def admin(self) -> Action:
        def run(ctx):
            try:
                from ..features.web_workspace import _ensure_server
                srv = _ensure_server(ctx.win, ctx.folder / "index.php")
                if srv is not None:
                    url = srv.url_for(ctx.folder / "wp-admin" / "index.php") or srv.url.rstrip("/") + "/wp-admin/"
                    ctx.win.web_preview.open_url(url)
                    return
            except Exception as e:  # noqa: BLE001
                ctx.log(f"*** wp-admin: {e}")
            ctx.log("Run the site (F5) and open /wp-admin/ in the Preview.")
        return Action("wp-admin", "Open wp-admin", run, opens="none", toolbar=True)

    def scaffold_plugin(self) -> Action:
        return Action("scaffold-plugin", "New Plugin...",
                      lambda c: self.wp(c, "scaffold", "plugin", c.values["slug"],
                                        *(["--activate"] if c.values.get("activate") else []),
                                        title=f"wp scaffold plugin {c.values['slug']}"),
                      ask=[Field("slug", "Slug", default="my-plugin"), Field("activate", "Activate (--activate)", "bool")],
                      enabled=lambda c: bool(_wp_cli(c.folder)), tip="wp scaffold plugin")

    def scaffold_theme(self) -> Action:
        return Action("scaffold-theme", "New Child Theme...",
                      lambda c: self.wp(c, "scaffold", "child-theme", c.values["slug"],
                                        f"--parent_theme={c.values['parent']}",
                                        *(["--activate"] if c.values.get("activate") else []),
                                        title=f"wp scaffold child-theme {c.values['slug']}"),
                      ask=[Field("slug", "Slug", default="my-theme"),
                           Field("parent", "Parent theme", default="twentytwentyfour"),
                           Field("activate", "Activate (--activate)", "bool")],
                      enabled=lambda c: bool(_wp_cli(c.folder)), tip="wp scaffold child-theme")

    def actions(self, ctx):
        cli = bool(_wp_cli(ctx.folder))
        items = [self.admin()]
        if cli:
            items += [Separator(), self.scaffold_plugin(), self.scaffold_theme(),
                      Action("plugin-install", "Install Plugin...",
                             lambda c: self.wp(c, "plugin", "install", c.values["slug"],
                                               *(["--activate"] if c.values.get("activate") else []),
                                               title=f"wp plugin install {c.values['slug']}"),
                             ask=[Field("slug", "Plugin slug", default="query-monitor"),
                                  Field("activate", "Activate (--activate)", "bool", default=True)],
                             opens="none", refresh=True),
                      Action("plugin-list", "Plugin List", lambda c: self.wp(c, "plugin", "list"), opens="none"),
                      Separator(),
                      Action("cache-flush", "Flush Cache", lambda c: self.wp(c, "cache", "flush"), opens="none"),
                      Action("rewrite-flush", "Flush Rewrite Rules", lambda c: self.wp(c, "rewrite", "flush"),
                             opens="none")]
        else:
            items += [Separator(), Action("wp-cli", "Get wp-cli (not installed)...", self._get_cli, opens="none",
                                          tip="wp-cli makes scaffolding plugins / themes and cache flushes possible")]
        return items

    @staticmethod
    def _get_cli(ctx):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtGui import QDesktopServices
        ctx.log("wp-cli: put wp-cli.phar into the project folder or %LOCALAPPDATA%\\RADIDE\\toolchains, or wp.bat on "
                "PATH (https://wp-cli.org/#installing)")
        QDesktopServices.openUrl(QUrl("https://wp-cli.org/#installing"))

    def folder_actions(self, ctx, rel_folder):
        cli = bool(_wp_cli(ctx.folder))
        if rel_folder == "":
            return self.actions(ctx)
        if cli and matches(rel_folder, "wp-content/plugins"):
            return [self.scaffold_plugin()]
        if cli and matches(rel_folder, "wp-content/themes"):
            return [self.scaffold_theme()]
        return []


# ============================================================================ plain PHP / Composer
def _bin(folder: Path, name: str) -> bool:
    return (folder / "vendor" / "bin" / name).is_file()


class PhpProject(Provider):
    """Composer projects without a framework (libraries, plain PHP apps)."""
    id, title, priority = "php", "PHP", 20
    icon = PHP_BADGE
    markers = ("composer.json", "artisan", "spark", "wp-load.php")

    def detect(self, folder, project):
        if not (folder / "composer.json").is_file():
            return False
        if (folder / "artisan").is_file() or (folder / "spark").is_file() or (folder / "wp-load.php").is_file():
            return False
        return True

    @staticmethod
    def psr4(folder: Path) -> list[tuple[str, str]]:
        """[(namespace prefix, folder)] of composer.json autoload psr-4 (autoload-dev too)."""
        d = composer_json(folder)
        out = []
        for k in ("autoload", "autoload-dev"):
            m = (d.get(k) or {}).get("psr-4") or {}
            if isinstance(m, dict):
                for ns, dirs in m.items():
                    for one in (dirs if isinstance(dirs, list) else [dirs]):
                        out.append((str(ns), str(one).strip("/")))
        return out

    def new_class(self, ctx, rel_folder: str = "") -> Action:
        maps = self.psr4(ctx.folder)
        default = rel_folder or (maps[0][1] if maps else "src")

        def run(c):
            name = studly(c.values["name"]) or "NewClass"
            folder = c.values["folder"].strip().replace("\\", "/").strip("/")
            ns = ""
            for prefix, base in sorted(maps, key=lambda x: -len(x[1])):
                if folder == base or folder.startswith(base + "/") or base == "":
                    rest = folder[len(base):].strip("/") if base else folder
                    ns = (prefix.rstrip("\\") + ("\\" + rest.replace("/", "\\") if rest else "")).strip("\\")
                    break
            kind = c.values.get("kind", "class")
            head = "<?php\n\ndeclare(strict_types=1);\n\n" + (f"namespace {ns};\n\n" if ns else "")
            body = {"interface": f"interface {name}\n{{\n}}\n", "trait": f"trait {name}\n{{\n}}\n",
                    "enum": f"enum {name}: string\n{{\n}}\n"}.get(kind, f"final class {name}\n{{\n}}\n")
            write_new(c, f"{folder}/{name}.php" if folder else f"{name}.php", head + body)
        return Action("new-class", "New Class...", run,
                      ask=[Field("name", "Name", default="NewClass"), Field("folder", "Folder", default=default),
                           Field("kind", "Kind", "choice", choices=("class", "interface", "trait", "enum"))],
                      tip="A PHP file with the PSR-4 namespace of composer.json")

    def tools(self, ctx) -> list:
        f = ctx.folder
        out = []
        if _bin(f, "pest"):
            out.append(Action("pest", "Run Tests (Pest)", lambda c: c.run_cli(["php", "vendor/bin/pest"], title="pest"),
                              opens="none", toolbar=True))
        elif _bin(f, "phpunit"):
            out.append(Action("phpunit", "Run Tests (PHPUnit)",
                              lambda c: c.run_cli(["php", "vendor/bin/phpunit"], title="phpunit"),
                              opens="none", toolbar=True))
        if _bin(f, "phpstan"):
            out.append(Action("phpstan", "Analyse (PHPStan)",
                              lambda c: c.run_cli(["php", "vendor/bin/phpstan", "analyse", "--no-progress"],
                                                  title="phpstan analyse"), opens="none"))
        if _bin(f, "pint"):
            out.append(Action("pint", "Format Code (Pint)", lambda c: c.run_cli(["php", "vendor/bin/pint"], title="pint"),
                              opens="none"))
        elif _bin(f, "php-cs-fixer"):
            out.append(Action("cs-fixer", "Format Code (PHP-CS-Fixer)",
                              lambda c: c.run_cli(["php", "vendor/bin/php-cs-fixer", "fix"], title="php-cs-fixer fix"),
                              opens="none"))
        return out

    def serve(self) -> Action:
        def run(ctx):
            if _serve_website(ctx):
                return
            root = "public" if (ctx.folder / "public").is_dir() else "."
            ctx.run_cli(["php", "-S", "127.0.0.1:8000", "-t", root], title="php -S 127.0.0.1:8000", opens="none")
        return Action("serve", "Serve (PHP built-in server)", run, opens="none",
                      tip="php -S 127.0.0.1:8000 -t public (the IDE's DevServer for website projects)")

    def actions(self, ctx):
        return [self.serve(), *self.tools(ctx), Separator(), self.new_class(ctx),
                Action("composer-validate", "composer validate", lambda c: c.run_cli(["composer", "validate"]),
                       opens="none"),
                Action("composer-outdated", "composer outdated", lambda c: c.run_cli(["composer", "outdated", "--direct"]),
                       opens="none")]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return [self.serve(), *self.tools(ctx)]
        for _ns, base in self.psr4(ctx.folder):
            if base and matches(rel_folder, base + "/**"):
                return [self.new_class(ctx, rel_folder)]
        if matches(rel_folder, "tests/**"):
            return [a for a in self.tools(ctx) if a.id in ("pest", "phpunit")]
        return []

    def file_actions(self, ctx, rel_file):
        if not rel_file.endswith(".php"):
            return []
        out = []
        if matches(rel_file, "tests/**/*.php"):
            tool = "pest" if _bin(ctx.folder, "pest") else "phpunit" if _bin(ctx.folder, "phpunit") else ""
            if tool:
                out.append(Action("test-this", "Run This Test",
                                  lambda c: c.run_cli(["php", f"vendor/bin/{tool}", rel_file], title=f"{tool} {Path(rel_file).name}"),
                                  opens="none"))
        out.append(Action("run-file", "Run This File (php)",
                          lambda c: c.run_cli(["php", rel_file], title=f"php {Path(rel_file).name}"), opens="none"))
        return out


PROVIDERS = [Laravel(), CodeIgniter(), WordPress(), PhpProject()]
