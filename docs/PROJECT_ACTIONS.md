# Project Actions - writing a provider

Project Actions are the commands that depend on the *kind* of project that is open:
`php artisan make:controller` for Laravel, `spark` for CodeIgniter, `manage.py` for Django,
`flutter pub get`, npm scripts, Makefile targets ...

Code: `radide/project_actions.py` (API, runner, ask dialog), `radide/features/project_menus.py` (UI),
providers in `radide/project_actions_providers/<area>.py`.

## Where the actions show up

| Place | What | Provider method |
|---|---|---|
| Menu bar, after **Project** | one menu per detected provider (`provider.title`, e.g. "Laravel"), only while such a project is active; several can be active (Laravel + npm Scripts + Composer) | `actions(ctx)` |
| **Project** menu, at the end | "*Title* Commands" sub menus (same items) | `actions(ctx)` |
| Solution Explorer right-click on a **folder** | at the top of the existing menu (normal projects, website folder trees, foreign projects) | `folder_actions(ctx, rel_folder)` |
| Solution Explorer right-click on a **file** | at the top of the existing menu | `file_actions(ctx, rel_file)` |
| "Project Actions" tool bar | actions with `toolbar=True` of the active providers, plus *Stop Running Command* | `actions(ctx)` |
| Command Palette (Ctrl+Shift+P) | "*Title*: *Action*" (sub menus: "*Title*: *Sub*: *Action*") | `actions(ctx)`, `palette=True` |

The menus are rebuilt when the active project changes and filled each time they open, so a script
added to `package.json` shows up at once. Several providers can be active together.

## A minimal provider

```python
# radide/project_actions_providers/laravel.py
from radide.project_actions import Action, Field, Provider, Separator, Submenu, composer_requires, matches


class Laravel(Provider):
    id, title, priority = "laravel", "Laravel", 50
    icon = ("Lv", "#E8473C")                  # letter badge, a radide.icons name, "SP_..." or a QIcon
    markers = ("artisan", "composer.json")    # their mtimes invalidate the cached detect() result

    def detect(self, folder, project):        # FAST: marker files only (the result is cached)
        return (folder / "artisan").is_file() and composer_requires(folder, "laravel/framework")

    def actions(self, ctx):
        return [Action("serve", "Serve", lambda c: c.run_cli(["php", "artisan", "serve"]),
                       toolbar=True, opens="none"),
                Action("tinker", "Tinker", lambda c: c.run_in_terminal(["php", "artisan", "tinker"]),
                       opens="none"),
                Separator(),
                Submenu("Make", [self.new_controller(), self.new_model()])]

    def folder_actions(self, ctx, rel_folder):           # "" = the project root
        if matches(rel_folder, "app/Http/Controllers/**"):
            return [self.new_controller()]
        if matches(rel_folder, "app/Models/**"):
            return [self.new_model()]
        if rel_folder == "":
            return self.actions(ctx)
        return []

    def file_actions(self, ctx, rel_file):
        if matches(rel_file, "database/migrations/*.php"):
            return [Action("migrate-this", "Run This Migration",
                           lambda c: c.run_cli(["php", "artisan", "migrate", "--path=" + rel_file]),
                           opens="none")]
        return []

    def new_controller(self):
        return Action("make-controller", "New Controller...", self._make_controller,
                      ask=[Field("name", "Name", default="PostController"),
                           Field("resource", "Resource controller (--resource)", "bool")])

    def _make_controller(self, ctx):
        argv = ["php", "artisan", "make:controller", ctx.values["name"]]
        if ctx.values["resource"]:
            argv.append("--resource")
        ctx.run_cli(argv)            # output -> Output window; created file(s) open in the editor

    def new_model(self):
        return Action("make-model", "New Model...",
                      lambda c: c.run_cli(["php", "artisan", "make:model", c.values["name"],
                                           *[f"-{k}" for k in "mcfs" if c.values[k]]]),
                      ask=[Field("name", "Name", default="Post"),
                           Field("m", "Migration (-m)", "bool"), Field("c", "Controller (-c)", "bool"),
                           Field("f", "Factory (-f)", "bool"), Field("s", "Seeder (-s)", "bool")])


PROVIDERS = [Laravel()]
```

Every module of `radide/project_actions_providers/` is imported once at start-up (names starting with
`_` are skipped). A module registers its providers with `PROVIDERS = [...]`, a `providers()` function,
or `radide.project_actions.register_provider(p)`. A provider that raises never breaks the IDE: the error
goes to the Output window.

## API

* `Field(name, label="", kind="text", default=None, choices=(), help="", required=None, placeholder="")`
  * `kind`: `text`, `bool` (check box), `choice` (combo box, `choices`), `path` (folder + Browse...),
    `multiline`. Text and path fields are required unless `required=False`.
* `Action(id, title, run, icon=None, shortcut=None, group=None, ask=[], enabled=None, opens="created",
  toolbar=False, palette=True, tip="", refresh=None)`
  * `run(ctx)` or `run(ctx, values)`; the answers of `ask` are in `ctx.values`. The ask dialog is shown
    only when `ask` is not empty, and Cancel runs nothing.
  * `enabled(ctx) -> bool` greys the item out.
  * `opens="created"` opens the files the command created; `"none"` never opens anything (servers,
    installs, tests).
  * `refresh`: refresh Solution Explorer afterwards (default: only when files were created).
  * `shortcut`: e.g. `"Ctrl+Alt+F9"` (a window shortcut while the provider is active).
* `Separator()`, `Submenu(title, items, icon=None)`.
* `Provider`: `id`, `title`, `priority` (higher = first), `icon`, `markers`, `detect(folder, project)`,
  `actions(ctx)`, `folder_actions(ctx, rel_folder)`, `file_actions(ctx, rel_file)`,
  `created_files(ctx, run) -> list[Path]` (more created-file detection, rarely needed).
  Paths given to providers are relative POSIX paths (`app/Http/Controllers`); the root is `""`.
* `matches(rel, *patterns)`: `*` = one path part, `**` = any depth, `"app/Models/**"` matches the folder
  itself and everything below it. Case-insensitive on Windows.
* Helpers: `read_json(path)` (cached by mtime, accepts JSONC such as `tasks.json`), `read_text(path)`,
  `package_json(folder)`, `composer_json(folder)`, `composer_requires(folder, package)`.

### The context (`ctx`)

| Member | Meaning |
|---|---|
| `win`, `project`, `folder` | main window, project object, project root (`Path`) |
| `provider`, `action`, `values` | who is running, and the answers of the ask dialog |
| `target`, `rel_target` | the right-clicked folder / file (`None` / `""` from menus, tool bar, palette) |
| `rel(path)`, `path(rel)` | convert between absolute and project-relative paths |
| `run_cli(argv, cwd=None, title=None, on_done=None, env=None, opens=None, stdin=None)` | run a command (see below), returns a `CliRun` |
| `run_in_terminal(argv, cwd=None)` | interactive commands (tinker, shell, REPL) in the integrated Terminal |
| `ask(fields, title=None, text="")` | show an extra dialog yourself; `None` = cancelled |
| `confirm(text)` | Yes/No question |
| `open_file(path, line=None)`, `refresh_tree()`, `log(text)` | editor, Solution Explorer, Output window |
| `php()`, `python()`, `resolve_argv(argv)` | the project's tool chain |

`run_cli`:

* streams stdout + stderr to the **Output** window (QProcess; ANSI colours removed);
* is cancellable (`run.cancel()`, or *Stop Running Command* in the provider menu / tool bar);
* resolves `argv[0]` for the project: `php` = the project's PHP version (with the framework extensions),
  `composer` = Composer for that PHP, `python` = the project's `.venv` (else the IDE's interpreter),
  `npm`/`npx`/`yarn`/`pnpm`... found on PATH (`.cmd` shims on Windows), `make` falls back to
  `mingw32-make`; `node_modules/.bin` and `.venv/Scripts` are put first on PATH;
* when it ends with exit code 0, finds the **created files** and opens them (up to 8):
  paths printed by the command that are new (`Controller [app/Http/Controllers/X.php] created
  successfully.`, `CREATE src/app/x.ts`) plus the files that appeared in the project folder (before /
  after snapshot; `vendor`, `node_modules`, `.git`, caches skipped), then refreshes Solution Explorer;
* `on_done(run)` receives the `CliRun` (`run.exit_code`, `run.output`, `run.created`).

An action that does not run a command (writes files from Python) gets the same treatment: the folder is
diffed after `run` returns and the new files open.

## Built-in generic providers (`generic.py`)

| Provider | Detected by | Actions |
|---|---|---|
| npm Scripts | `package.json` | every `scripts` entry (`npm`/`yarn`/`pnpm`/`bun run`, chosen from the lock file / `packageManager`), install, Add Package...; `dev`/`start` on the tool bar |
| Composer | `composer.json` | own scripts (+ "Event Scripts" sub menu), install, update, dump-autoload, Require Package... |
| Make | `Makefile` / `makefile` / `GNUmakefile` | default target + every explicit target |
| Tasks | `.vscode/tasks.json` | every task (shell / process / npm), `${workspaceFolder}` & co. expanded; the default build task on the tool bar |
| Python Scripts | `pyproject.toml` with `[project.scripts]` / `[tool.poetry.scripts]` | run each entry point, `pip install -e .` |
| just | `justfile` | every recipe (asks for arguments when it has parameters) |
| Task | `Taskfile.yml` | every task |

## Framework / language providers

| Module | Providers (menu title) | Detected by |
|---|---|---|
| `node_web.py` | npm Scripts (+ Packages: update / outdated / audit / npm-check-updates, replaces the generic one), NestJS, Angular, React / Vue / Svelte (Vite), Express, Expo, React Native | `package.json` dependencies, `angular.json` |
| `dotnet.py` | ASP.NET Core (dotnet new apicontroller / mvccontroller / page / razorcomponent / view, dotnet watch, EF Core migrations, user-secrets), Visual Studio (Build / Rebuild / Clean / Publish, NuGet) | Web SDK `.csproj`; `.sln` / `.slnx` or an opened VS project |
| `java_ruby.py` | Spring Boot (Maven / Gradle tasks, New Controller / Entity / Repository / Service in package folders), Rails (Server / Debug / Console; Generate: controller, model, scaffold, resource, migration, mailer, job, helper, channel, authentication, destroy; Database: db:migrate / rollback / status / seed / prepare / reset / system:change; Tests: run, set up minitest, new test; Bundler: install / update / outdated / add gem; Routes, Edit Credentials, assets:precompile; folder actions in app/controllers, app/models, app/views (view / partial), db/migrate, test, spec; file actions on migrations, tests, specs, routes.rb, Gemfile), Sinatra | `pom.xml` / `build.gradle` with Spring Boot; `config/application.rb`; Gemfile with sinatra |
| `native.py` | Flutter (pub, build apk / appbundle / windows / web, New Screen - a new form in RAD IDE Flutter projects), Go, Rust (cargo), CMake (configure, target list, clean - built in the IDE state folder) | `pubspec.yaml` with the Flutter SDK, `go.mod`, `Cargo.toml`, `CMakeLists.txt` |
| `rad_tools.py` | Godot (open the editor, run, export presets), Ring (run, ring2exe, ringpm), VB6 (properties, Make EXE), BASIC | `project.godot`, project language, `.ring` files, VB6 mirror folders |

Shared helpers for these modules are in `_common.py` (`write_new`, `target_folder`, `run_script_or`, `log_routes` ...).

## Tips

* Keep `detect()` cheap: stat a few files, read one small JSON at most. List the files in `markers` so the
  cached answer is recomputed when they change.
* Ask only for what the command needs: a name as text, options as check boxes.
* Use `opens="none"` for long-running commands (serve, watch, queue:work) and for commands that only
  change state (migrate, cache:clear).
* English UI text goes through the IDE's translation layer automatically; add Arabic for new words to
  `radide/i18n/ar.json` (`strings` for fixed text, `patterns` with `{}` for text with values).
* Tests: set `radide.project_actions.ASK_HOOK = lambda fields, title: {"name": "Post"}` to answer the ask
  dialog without showing it; `run.wait()` processes events until a command ends.
