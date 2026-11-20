"""Laravel in RAD IDE (engine, no Qt) - the IDE part is ``radide/features/php_frameworks.py``.

- **Create**: :func:`create_laravel` = ``composer create-project laravel/laravel`` with the site's PHP
  (php_toolchain.py), ``.env`` (APP_NAME, APP_KEY via ``artisan key:generate``), SQLite
  (``database/database.sqlite``) or the IDE's local MariaDB / PostgreSQL server, ``artisan migrate``,
  ``install:api`` for the API template and barryvdh/laravel-ide-helper (``_ide_helper.php``,
  ``_ide_helper_models.php``, ``.phpstorm.meta.php``) so intelephense understands facades and models.
  The project is a normal ``php-web`` site: ``web.root = public``, ``web.start = /``, ``web.framework =
  laravel``; ``php -S`` runs with Laravel's ``server.php`` router (:func:`router`) behind the DevServer.
- **Index** (:func:`index`): routes (static parse of ``routes/*.php`` + ``artisan route:list --json``),
  views, Blade components and their props, config keys, translation keys, ``.env`` keys, Eloquent models
  (columns from the migrations and the SQLite schema, casts, relations, scopes, accessors) and the
  variables controllers pass to each view. Every part is rebuilt only when its files change
  (:class:`~.common.StampCache`) - IntelliSense follows the project while you edit it.
- **IntelliSense**: :func:`complete` (strings of ``route()`` / ``view()`` / ``config()`` / ``__()`` /
  ``env()`` / ``asset()`` / ``where('column')`` / ``with('relation')`` / validation rules, ``$model->``
  attributes and relations, ``Model::`` query methods and scopes, Blade ``@directives``, ``<x-components>``
  and props, view variables) and :func:`definition` (F12 / Ctrl+click on those strings and components).
- **Artisan**: :func:`artisan_commands` (``artisan list --format=json``), :func:`route_list`.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import threading
from pathlib import Path

from .common import (K_CLASS, K_CONSTANT, K_FIELD, K_FILE, K_KEYWORD, K_METHOD, K_MODULE,
                     K_PROPERTY, K_REFERENCE, K_SNIPPET, K_TEXT, K_VALUE, K_VARIABLE, PhpFramework, StampCache,
                     array_key_before, call_context, class_file, class_of_file, composer_requires, item,
                     line_of, method_line, namespace_of, parse_env, parse_php_array, plural, project_php,
                     read_text, register_framework, run_logged, run_php, snake, string_context, string_range,
                     tree_stamp, uses_of)

SERVER_PHP = "vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php"
IDE_HELPER_FILES = ("_ide_helper.php", "_ide_helper_models.php", ".phpstorm.meta.php")
MIN_PHP = (8, 3)                       # Laravel 12 / 13 (composer.json require.php decides in the end)
# defaults for the next create_laravel() call (set by the New Project options dialog, php_frameworks.py)
CREATE_OPTIONS: dict = {}


# ============================================================================ detection / router
def is_laravel(folder) -> bool:
    folder = Path(folder)
    return (folder / "artisan").is_file() and (composer_requires(folder, "laravel/framework") or
                                               (folder / "vendor" / "laravel" / "framework").is_dir())


def router(folder, root) -> str:
    p = Path(folder) / SERVER_PHP
    return str(p.resolve()) if p.is_file() else ""


register_framework(PhpFramework("laravel", "Laravel", is_laravel, router, __name__))


# ============================================================================ create
def _composer_argv(args: list[str], php: str) -> list[str]:
    from ..php_toolchain import composer_argv
    return composer_argv(args, php)


def pick_php(log=None) -> str:
    """PHP for a new Laravel project: the newest RAD IDE toolchain PHP >= 8.3 (official build, php.ini with the
    extensions, matching Xdebug), else the newest other install >= 8.3, else PHP 8.4 is installed."""
    from .. import php_toolchain as tc
    ok = [i for i in tc.detect_installs() if i.bits == 64 and tc.vtuple(i.version)[:2] >= MIN_PHP]
    own = [i for i in ok if str(Path(i.path)).lower().startswith(str(tc.PHP_ROOT).lower())]
    if own or ok:
        return (own or ok)[0].path
    if log:
        log("[laravel] no PHP >= 8.3 found - installing PHP 8.4 (official windows.php.net build) ...")
    return tc.install_php("8.4", log)


def set_env_values(env_file: Path, values: dict[str, str | None]) -> None:
    """Set / comment out keys of a .env file (None = comment the key out)."""
    lines = read_text(env_file).splitlines() if env_file.exists() else []
    done = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip().lstrip("#").strip()
        if key in values and "=" in line:
            v = values[key]
            if v is None:
                out.append(line if line.lstrip().startswith("#") else "# " + line)
            else:
                out.append(f"{key}={_env_quote(v)}")
            done.add(key)
        else:
            out.append(line)
    for k, v in values.items():
        if k not in done and v is not None:
            out.append(f"{k}={_env_quote(v)}")
    env_file.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")


def _env_quote(v: str) -> str:
    v = str(v)
    return f'"{v}"' if re.search(r"[\s#\"'$]", v) else v


def create_laravel(folder, name: str, log=None, kind: str = "app", db: str = "sqlite", db_conn: dict | None = None,
                   php: str = "", ide_helper: bool = True, timeout: int = 1800) -> dict:
    """Create a Laravel project in *folder* (missing or empty). *kind* "app" (web) or "api" (``install:api``:
    routes/api.php + Sanctum). *db* "sqlite" | "mysql" | "mariadb" | "pgsql" (*db_conn*: host, port, database,
    username, password). Returns the project.radproj "web" block. Raises RuntimeError with the reason."""
    log = log or print
    db = CREATE_OPTIONS.get("db", db)
    db_conn = CREATE_OPTIONS.get("db_conn", db_conn)
    ide_helper = CREATE_OPTIONS.get("ide_helper", ide_helper)
    folder = Path(folder).resolve()
    php = php or pick_php(log)
    if not php:
        raise RuntimeError("PHP 8.3 or newer is needed for Laravel (Tools > PHP Versions... > Install PHP 8.4).")
    from .. import php_toolchain as tc
    if tc.vtuple(tc.php_version(php))[:2] < MIN_PHP:
        log(f"[laravel] {php} is PHP {tc.php_version(php)}; Laravel needs >= 8.3 - looking for a newer one")
        php = pick_php(log)
    if not tc.find_composer():
        log("[laravel] Composer is not installed - downloading the official composer.phar ...")
        tc.install_composer(log)
    if folder.exists() and any(folder.iterdir()):
        raise RuntimeError(f"The folder {folder} is not empty.")
    if folder.exists():
        folder.rmdir()
    folder.parent.mkdir(parents=True, exist_ok=True)
    env = tc.composer_env(php)
    log(f"[laravel] composer create-project laravel/laravel (PHP {tc.php_version(php)}) - a few minutes ...")
    argv = _composer_argv(["create-project", "laravel/laravel", str(folder), "--prefer-dist", "--no-interaction",
                           "--no-progress", "--no-ansi"], php)
    if not argv:
        raise RuntimeError("Composer is not installed (Tools > PHP Versions... > Install Composer).")
    code, out = run_logged(argv, folder.parent, log, timeout, env)
    if code != 0:
        if not (folder / "composer.json").is_file():
            raise RuntimeError(f"composer create-project failed (exit code {code}):\n" + "\n".join(out.splitlines()[-12:]))
        for attempt in (1, 2):                 # a download that failed half way (antivirus, network): resume
            log(f"[laravel] composer install (retry {attempt}) ...")
            code, out = run_logged(_composer_argv(["install", "--no-interaction", "--no-progress", "--no-ansi"], php),
                                   folder, log, timeout, env)
            if code == 0:
                break
        if code != 0:
            raise RuntimeError("composer install failed:\n" + "\n".join(out.splitlines()[-12:]))
    configure_project(folder, name, php, log, db=db, db_conn=db_conn)
    if kind == "api":
        install_api(folder, php, log, timeout)
    code, _out = run_php(folder, ["artisan", "migrate", "--force", "--no-interaction"], 600, log, php)
    if code != 0:
        log("[laravel] migrate failed - check the database settings in .env, then Artisan > migrate.")
    if ide_helper:
        install_ide_helper(folder, php, log, timeout)
    log(f"[laravel] Laravel {laravel_version(folder) or ''} is ready: web root public/, F5 runs it.")
    own = str(Path(php)).lower().startswith(str(tc.PHP_ROOT).lower())
    return {"root": "public", "start": "/", "framework": "laravel", "port": 0, "live_reload": True,
            "php": tc.series_of(tc.php_version(php)) if own else "auto"}


def configure_project(folder: Path, name: str, php: str, log, db: str = "sqlite", db_conn: dict | None = None):
    """.env from .env.example, APP_NAME, database settings, APP_KEY."""
    folder = Path(folder)
    env_file = folder / ".env"
    if not env_file.exists() and (folder / ".env.example").exists():
        shutil.copyfile(folder / ".env.example", env_file)
    values: dict[str, str | None] = {"APP_NAME": re.sub(r"[^\w .-]", "", name) or "Laravel"}
    if db in ("mysql", "mariadb", "pgsql"):
        c = dict(db_conn or {})
        values.update({"DB_CONNECTION": "mariadb" if db == "mariadb" else db, "DB_HOST": c.get("host", "127.0.0.1"),
                       "DB_PORT": str(c.get("port") or (5432 if db == "pgsql" else 3306)),
                       "DB_DATABASE": c.get("database", "laravel"), "DB_USERNAME": c.get("username", "root"),
                       "DB_PASSWORD": c.get("password", "")})
    else:
        values.update({"DB_CONNECTION": "sqlite", "DB_HOST": None, "DB_PORT": None, "DB_DATABASE": None,
                       "DB_USERNAME": None, "DB_PASSWORD": None})
        dbf = folder / "database" / "database.sqlite"
        dbf.parent.mkdir(parents=True, exist_ok=True)
        dbf.touch()
    set_env_values(env_file, values)
    if not re.search(r"^APP_KEY=\S+", read_text(env_file), re.M):
        run_php(folder, ["artisan", "key:generate", "--force", "--no-interaction"], 120, log, php)


def install_ide_helper(folder, php: str = "", log=None, timeout: int = 1200) -> bool:
    """barryvdh/laravel-ide-helper as a dev dependency + generate the helper files (facades, models, meta)."""
    folder = Path(folder)
    php = php or project_php(folder)
    log = log or print
    from .. import php_toolchain as tc
    if not composer_requires(folder, "barryvdh/laravel-ide-helper"):
        log("[laravel] composer require --dev barryvdh/laravel-ide-helper ...")
        code, _ = run_logged(_composer_argv(["require", "--dev", "barryvdh/laravel-ide-helper", "--no-interaction",
                                             "--no-progress", "--no-ansi"], php), folder, log, timeout,
                             tc.composer_env(php))
        if code != 0:
            log("[laravel] laravel-ide-helper could not be installed (IntelliSense still works without it).")
            return False
    _gitignore(folder, IDE_HELPER_FILES)
    return generate_ide_helper(folder, php, log)


def generate_ide_helper(folder, php: str = "", log=None) -> bool:
    ok = True
    for args in (["ide-helper:generate"], ["ide-helper:models", "--nowrite", "--no-interaction"], ["ide-helper:meta"]):
        code, _ = run_php(folder, ["artisan", *args], 300, log, php)
        ok = ok and code == 0
    return ok


def _gitignore(folder: Path, names) -> None:
    gi = folder / ".gitignore"
    text = read_text(gi)
    missing = [n for n in names if n not in text.split()]
    if missing:
        gi.write_text(text.rstrip("\n") + "\n" + "\n".join(missing) + "\n", encoding="utf-8", newline="\n")


def install_api(folder: Path, php: str, log, timeout: int = 1200) -> bool:
    """``artisan install:api`` (routes/api.php + Laravel Sanctum) with the IDE's Composer, the HasApiTokens trait on
    User and an /api/status example. Laravel runs ``php <--composer>`` for a file, so it gets composer.phar."""
    from .. import php_toolchain as tc
    folder = Path(folder)
    opt = f"--composer={tc.COMPOSER_PHAR}" if tc.COMPOSER_PHAR.is_file() else "--composer=global"
    run_php(folder, ["artisan", "install:api", "--without-migration-prompt", "--no-interaction", opt],
            timeout=timeout, log=log, php=php)
    if not composer_requires(folder, "laravel/sanctum"):
        log("[laravel] Sanctum is missing after install:api - composer require laravel/sanctum ...")
        run_logged(_composer_argv(["require", "laravel/sanctum", "--no-interaction", "--no-progress", "--no-ansi"],
                                  php), folder, log, timeout, tc.composer_env(php))
    user = folder / "app" / "Models" / "User.php"
    text = read_text(user)
    if text and "HasApiTokens" not in text:
        text = text.replace("use Illuminate\\Notifications\\Notifiable;",
                            "use Illuminate\\Notifications\\Notifiable;\nuse Laravel\\Sanctum\\HasApiTokens;", 1)
        text = re.sub(r"(\n\s*use )(HasFactory)", r"\1HasApiTokens, \2", text, count=1)
        user.write_text(text, encoding="utf-8", newline="\n")
    write_api_example(folder)
    return composer_requires(folder, "laravel/sanctum")


def write_api_example(folder: Path) -> None:
    api = folder / "routes" / "api.php"
    text = read_text(api)
    if "api.status" not in text and text:
        api.write_text(text.rstrip() + "\n\nRoute::get('/status', function () {\n    return ['app' => config('app.name'), "
                       "'laravel' => app()->version(), 'time' => now()->toIso8601String()];\n})->name('api.status');\n",
                       encoding="utf-8", newline="\n")


def laravel_version(folder) -> str:
    try:
        data = json.loads((Path(folder) / "vendor" / "composer" / "installed.json").read_text(encoding="utf-8"))
        pk = data.get("packages", data) if isinstance(data, dict) else data
        for p in pk:
            if p.get("name") == "laravel/framework":
                return str(p.get("version", "")).lstrip("v")
    except (OSError, ValueError, AttributeError):
        pass
    return ""


def needs_setup(folder) -> list[str]:
    """What an opened Laravel project still needs: "vendor", "env", "key", "database", "npm", "build"."""
    folder = Path(folder)
    out = []
    if not (folder / "vendor" / "autoload.php").is_file():
        out.append("vendor")
    env = folder / ".env"
    if not env.is_file():
        out.append("env")
    elif not re.search(r"^APP_KEY=\S+", read_text(env), re.M):
        out.append("key")
    envs = dict((k, v) for k, v, _ in parse_env(env)) if env.is_file() else {}
    if envs.get("DB_CONNECTION", "sqlite") == "sqlite" and not (folder / "database" / "database.sqlite").is_file():
        out.append("database")
    pkg = folder / "package.json"
    if pkg.is_file() and "vite" in read_text(pkg):
        if not (folder / "node_modules").is_dir():
            out.append("npm")
        if not (folder / "public" / "build" / "manifest.json").is_file():
            out.append("build")
    return out


# ============================================================================ index
_INDEXES: dict[str, "LaravelIndex"] = {}
_LOCK = threading.Lock()


def index(folder) -> "LaravelIndex":
    key = os.path.normcase(str(Path(folder).resolve()))
    with _LOCK:
        idx = _INDEXES.get(key)
        if idx is None:
            idx = _INDEXES[key] = LaravelIndex(Path(folder).resolve())
        return idx


class LaravelIndex:
    """Everything IntelliSense needs, read from the project files (each part cached by a file stamp)."""

    def __init__(self, folder: Path):
        self.folder = folder
        f = folder
        self._routes = StampCache(lambda: tree_stamp(f, ["routes"]), self._build_routes)
        self._views = StampCache(lambda: tree_stamp(f, ["resources/views"], (".php",)), self._build_views)
        self._components = StampCache(lambda: tree_stamp(f, ["resources/views/components", "app/View/Components"]),
                                      self._build_components)
        self._config = StampCache(lambda: tree_stamp(f, ["config"]), self._build_config)
        self._lang = StampCache(lambda: tree_stamp(f, ["lang", "resources/lang"], (".php", ".json")),
                                self._build_lang)
        self._env = StampCache(lambda: tree_stamp(f, [], files=(".env", ".env.example")), self._build_env)
        self._models = StampCache(lambda: tree_stamp(f, ["app/Models", "database/migrations"],
                                                     files=("database/database.sqlite",)), self._build_models)
        self._viewvars = StampCache(lambda: tree_stamp(f, ["app/Http/Controllers", "routes", "app/View"]),
                                    self._build_viewvars)
        self._public = StampCache(lambda: tree_stamp(f, ["public", "resources/css", "resources/js"],
                                                     (".css", ".js", ".png", ".jpg", ".svg", ".ico", ".webp",
                                                      ".gif", ".ts", ".scss")), self._build_public, 4.0)
        self.runtime_routes: list[dict] = []
        self._runtime_stamp = None
        self._runtime_busy = False

    # ---------------------------------------------------------------- routes
    def routes(self) -> list[dict]:
        """[{name, method, uri, file, line, action}] - static parse, completed by route:list when available."""
        static = self._routes.get()
        self.refresh_runtime_routes()
        names = {r["name"] for r in static if r.get("name")}
        out = list(static)
        for r in self.runtime_routes:
            if r.get("name") and r["name"] not in names:
                out.append(r)
                names.add(r["name"])
        return out

    def refresh_runtime_routes(self, wait: bool = False) -> None:
        """``artisan route:list --json`` in the background when the routes changed (vendor routes, prefixes)."""
        stamp = self._routes._stamp
        if self._runtime_busy or stamp == self._runtime_stamp or not (self.folder / "vendor").is_dir():
            return
        self._runtime_busy = True
        self._runtime_stamp = stamp

        def work():
            try:
                self.runtime_routes = route_list(self.folder)
            finally:
                self._runtime_busy = False
        if wait:
            work()
        else:
            threading.Thread(target=work, daemon=True, name="radide-laravel-routes").start()

    def _build_routes(self) -> list[dict]:
        out = []
        for p in sorted((self.folder / "routes").glob("*.php")):
            out += parse_routes_file(p)
        return out

    # ---------------------------------------------------------------- views / components
    def views(self) -> dict[str, Path]:
        return self._views.get()

    def _build_views(self) -> dict[str, Path]:
        base = self.folder / "resources" / "views"
        out: dict[str, Path] = {}
        if not base.is_dir():
            return out
        for p in sorted(base.rglob("*.php")):
            r = p.relative_to(base).as_posix()
            name = r[:-len(".blade.php")] if r.endswith(".blade.php") else r[:-4]
            out[name.replace("/", ".")] = p
        return out

    def components(self) -> dict[str, dict]:
        """{"alert": {"file": Path, "props": {name: default}, "class": FQCN|""}} (used as <x-alert>)."""
        return self._components.get()

    def _build_components(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        base = self.folder / "resources" / "views" / "components"
        if base.is_dir():
            for p in sorted(base.rglob("*.blade.php")):
                r = p.relative_to(base).as_posix()[:-len(".blade.php")]
                parts = r.split("/")
                if len(parts) > 1 and parts[-1] in ("index", parts[-2]):
                    parts = parts[:-1]
                name = ".".join(parts)
                out[name] = {"file": p, "props": blade_props(read_text(p)), "class": ""}
        cbase = self.folder / "app" / "View" / "Components"
        if cbase.is_dir():
            for p in sorted(cbase.rglob("*.php")):
                r = p.relative_to(cbase).with_suffix("").parts
                name = ".".join(kebab(x) for x in r)
                text = read_text(p)
                props = {}
                m = re.search(r"function\s+__construct\s*\(([^)]*)\)", text, re.S)
                if m:
                    for pm in re.finditer(r"\$(\w+)(?:\s*=\s*([^,]+))?", m.group(1)):
                        props[kebab(pm.group(1))] = (pm.group(2) or "").strip()
                view = re.search(r"view\(\s*['\"]([\w.:-]+)['\"]", text)
                entry = out.get(name, {"file": p, "props": {}, "class": ""})
                entry.update({"file": p, "class": class_of_file(self.folder, p), "props": {**entry["props"], **props},
                              "view": view.group(1) if view else ""})
                out[name] = entry
        return out

    # ---------------------------------------------------------------- config / lang / env
    def config_keys(self) -> list[tuple[str, Path, int, bool, str]]:
        return self._config.get()

    def _build_config(self):
        out = []
        for p in sorted((self.folder / "config").glob("*.php")):
            out.append((p.stem, p, 1, False, "config file"))
            for key, line, leaf, preview in parse_php_array(read_text(p)):
                out.append((f"{p.stem}.{key}", p, line, leaf, preview))
        return out

    def lang_keys(self) -> list[tuple[str, Path, int, str]]:
        return self._lang.get()

    def _build_lang(self):
        out = []
        seen = set()
        for base in (self.folder / "lang", self.folder / "resources" / "lang"):
            if not base.is_dir():
                continue
            for p in sorted(base.glob("*.json")):
                try:
                    data = json.loads(read_text(p) or "{}")
                except ValueError:
                    continue
                text = read_text(p)
                for k, v in data.items():
                    if k not in seen:
                        seen.add(k)
                        i = text.find(json.dumps(k)[:-1])
                        out.append((k, p, line_of(text, i) if i >= 0 else 1, f"{p.stem}: {v}"))
            for d in sorted(x for x in base.iterdir() if x.is_dir()):
                for p in sorted(d.rglob("*.php")):
                    group = p.relative_to(d).with_suffix("").as_posix()
                    for key, line, leaf, preview in parse_php_array(read_text(p)):
                        full = f"{group}.{key}"
                        if leaf and full not in seen:
                            seen.add(full)
                            out.append((full, p, line, f"{d.name}: {preview}"))
        return out

    def env_keys(self) -> list[tuple[str, str, Path, int]]:
        return self._env.get()

    def _build_env(self):
        out, seen = [], set()
        for name in (".env", ".env.example"):
            p = self.folder / name
            for k, v, line in parse_env(p):
                if k not in seen:
                    seen.add(k)
                    secret = re.search(r"KEY|SECRET|PASSWORD|TOKEN", k)
                    out.append((k, "***" if secret and v else v, p, line))
        return out

    def public_files(self) -> list[str]:
        return self._public.get()

    def _build_public(self):
        out = []
        for base, prefix in ((self.folder / "public", ""), (self.folder / "resources", "resources/")):
            if not base.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if d not in ("build", "vendor", "views", "lang", "node_modules")
                               or prefix == "" and d != "build"]
                for fn in filenames:
                    if fn.endswith(".php") or fn in (".htaccess", "hot"):
                        continue
                    rel = (Path(dirpath) / fn).relative_to(base).as_posix()
                    if prefix and not rel.startswith(("css/", "js/", "sass/", "scss/")):
                        continue
                    out.append(prefix + rel)
                    if len(out) > 2000:
                        return out
        return out

    # ---------------------------------------------------------------- models
    def models(self) -> dict[str, dict]:
        """{FQCN: {"name", "file", "table", "columns": {col: type}, "relations": {name: (kind, FQCN)},
        "scopes": [..], "accessors": [..], "casts": {..}, "fillable": [..]}}"""
        return self._models.get()

    def model_by_short(self, short: str) -> dict | None:
        for fq, m in self.models().items():
            if m["name"] == short or fq == short.lstrip("\\"):
                return m
        return None

    def _build_models(self):
        tables = migration_tables(self.folder)
        db_tables = sqlite_tables(self.folder)
        out = {}
        base = self.folder / "app" / "Models"
        if not base.is_dir():
            return out
        for p in sorted(base.rglob("*.php")):
            text = read_text(p)
            m = re.search(r"\bclass\s+(\w+)\s+extends\s+([\\\w]+)", text)
            if not m:
                continue
            name = m.group(1)
            fq = (namespace_of(text) + "\\" if namespace_of(text) else "") + name
            tm = re.search(r"\$table\s*=\s*['\"](\w+)['\"]", text)
            table = tm.group(1) if tm else plural(snake(name))
            cols: dict[str, str] = {}
            cols.update(db_tables.get(table, {}))
            cols.update(tables.get(table, {}))
            uses = uses_of(text)
            ns = namespace_of(text)
            rels = {}
            for rm in re.finditer(r"function\s+(\w+)\s*\(\s*\)\s*(?::\s*[\\\w]+\s*)?\{\s*return\s+\$this\s*->\s*"
                                  r"(hasMany|hasOne|belongsTo|belongsToMany|morphMany|morphOne|morphTo|morphToMany|"
                                  r"hasManyThrough|hasOneThrough|morphedByMany)\s*\(\s*([\\\w]+)?(?:::class)?", text):
                target = rm.group(3) or ""
                if target:
                    target = uses.get(target, (ns + "\\" + target) if "\\" not in target else target.lstrip("\\"))
                rels[rm.group(1)] = (rm.group(2), target)
            scopes = [s[0].lower() + s[1:] for s in re.findall(r"function\s+scope(\w+)\s*\(", text)]
            scopes += re.findall(r"#\[Scope\]\s*(?:public|protected)?\s*function\s+(\w+)", text)
            accessors = [snake(a) for a in re.findall(r"function\s+get(\w+)Attribute\s*\(", text)]
            accessors += [snake(a) for a in re.findall(r"function\s+(\w+)\s*\(\s*\)\s*:\s*Attribute\b", text)]
            casts = dict(re.findall(r"['\"](\w+)['\"]\s*=>\s*['\"]([\w:\\,]+)['\"]",
                                    _block(text, r"(?:\$casts\s*=|function\s+casts\s*\(\s*\)\s*:\s*array\s*\{)")))
            fillable = re.findall(r"['\"](\w+)['\"]", _block(text, r"\$fillable\s*=") or "")
            am = re.search(r"#\[Fillable\(\s*\[([^\]]*)\]", text)          # Laravel 13 attributes
            if am:
                fillable += re.findall(r"['\"](\w+)['\"]", am.group(1))
            for f in fillable:
                cols.setdefault(f, "fillable")
            out[fq] = {"name": name, "fqcn": fq, "file": p, "table": table, "columns": cols, "relations": rels,
                       "scopes": scopes, "accessors": accessors, "casts": casts, "fillable": fillable,
                       "line": line_of(text, m.start())}
        return out

    # ---------------------------------------------------------------- view variables
    def view_vars(self, view_name: str) -> dict[str, tuple]:
        """{var: type} passed to *view_name* by controllers / routes (type: see :func:`var_type`)."""
        return self._viewvars.get().get(view_name, {})

    def _build_viewvars(self):
        out: dict[str, dict] = {}
        files = list((self.folder / "app" / "Http" / "Controllers").rglob("*.php")) + \
            list((self.folder / "routes").glob("*.php"))
        for p in files:
            text = read_text(p)
            for m in re.finditer(r"""(?:\bview|View::make|Inertia::render)\s*\(\s*['"]([\w.:-]+)['"]\s*(,)?""", text):
                name = m.group(1)
                body_start = text.rfind("function", 0, m.start())
                scope = text[body_start if body_start >= 0 else 0:m.start()]
                vars_ = out.setdefault(name, {})
                rest = text[m.end():m.end() + 800]
                if m.group(2):
                    arg = _balanced(rest)
                    cm = re.match(r"\s*compact\s*\((.*)\)\s*$", arg, re.S)
                    if cm:
                        for v in re.findall(r"['\"](\w+)['\"]", cm.group(1)):
                            vars_[v] = var_type(self, scope, v) or ("mixed", "")
                    else:
                        for km in re.finditer(r"['\"](\w+)['\"]\s*=>\s*([^,\]]+(?:\([^)]*\)[^,\]]*)*)", arg):
                            vars_[km.group(1)] = expr_type(self, scope, km.group(2).strip()) or ("mixed", "")
                for wm in re.finditer(r"->with\s*\(\s*['\"](\w+)['\"]\s*,\s*([^;]+?)\)\s*(?:->|;)", rest[:400]):
                    vars_[wm.group(1)] = expr_type(self, scope, wm.group(2).strip()) or ("mixed", "")
        return out


def _block(text: str, start_re: str) -> str:
    m = re.search(start_re, text)
    if not m:
        return ""
    i = text.find("[", m.end() - 1) if "{" not in m.group() else m.end() - 1
    if i < 0:
        return ""
    return _balanced(text[i + 1:], open_ch=text[i], close_ch={"[": "]", "{": "}", "(": ")"}[text[i]])


def _balanced(s: str, open_ch: str = "(", close_ch: str = ")") -> str:
    """Text up to the close bracket that balances an already open one."""
    depth = 1
    q = None
    for i, c in enumerate(s):
        if q:
            if c == q and s[i - 1] != "\\":
                q = None
        elif c in "\"'":
            q = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return s[:i]
    return s


def kebab(name: str) -> str:
    return snake(name).replace("_", "-")


def blade_props(text: str) -> dict[str, str]:
    m = re.search(r"@props\s*\(\s*\[", text)
    if not m:
        return {}
    body = _balanced(text[m.end():], "[", "]")
    props = {}
    for pm in re.finditer(r"""['"]([\w-]+)['"]\s*(?:=>\s*([^,\]]+))?""", body):
        props[pm.group(1)] = (pm.group(2) or "").strip()
    return props


# ============================================================================ migrations / schema
_COLUMN_TYPES = ("string", "text", "integer", "bigInteger", "boolean", "date", "dateTime", "timestamp", "decimal",
                 "float", "double", "json", "jsonb", "uuid", "ulid", "char", "longText", "mediumText", "tinyText",
                 "smallInteger", "tinyInteger", "mediumInteger", "unsignedBigInteger", "unsignedInteger",
                 "unsignedSmallInteger", "unsignedTinyInteger", "time", "year", "binary", "enum", "set", "ipAddress",
                 "macAddress", "foreignId", "foreignUuid", "foreignUlid", "foreignIdFor", "dateTimeTz",
                 "timestampTz", "timeTz", "geometry", "point", "increments", "bigIncrements", "id", "softDeletesTz",
                 "unsignedDecimal", "vector")


def migration_tables(folder) -> dict[str, dict[str, str]]:
    """{table: {column: type}} replayed from database/migrations (create / table / drop / rename)."""
    tables: dict[str, dict[str, str]] = {}
    base = Path(folder) / "database" / "migrations"
    if not base.is_dir():
        return tables
    for p in sorted(base.glob("*.php")):
        text = read_text(p)
        up = text
        dm = re.search(r"function\s+down\s*\(", text)
        if dm:
            up = text[:dm.start()]
        for sm in re.finditer(r"Schema::(create|table)\s*\(\s*['\"](\w+)['\"]\s*,\s*function\s*\([^)]*\)\s*(?::\s*\w+\s*)?\{",
                              up):
            body = _balanced(up[sm.end():], "{", "}")
            cols = tables.setdefault(sm.group(2), {}) if sm.group(1) == "table" else tables.setdefault(sm.group(2), {})
            if sm.group(1) == "create":
                cols.clear()
            for cm in re.finditer(r"\$table\s*->\s*(\w+)\s*\(([^;]*?)\)", body):
                meth, args = cm.group(1), cm.group(2)
                names = re.findall(r"['\"](\w+)['\"]", args)
                first = names[0] if names else ""
                if meth in ("id", "increments", "bigIncrements") and not first:
                    cols["id"] = "int"
                elif meth in ("timestamps", "timestampsTz", "nullableTimestamps"):
                    cols["created_at"] = cols["updated_at"] = "timestamp"
                elif meth in ("softDeletes", "softDeletesTz"):
                    cols[first or "deleted_at"] = "timestamp"
                elif meth == "rememberToken":
                    cols["remember_token"] = "string"
                elif meth in ("morphs", "nullableMorphs", "uuidMorphs", "ulidMorphs") and first:
                    cols[first + "_id"] = "int"
                    cols[first + "_type"] = "string"
                elif meth == "foreignIdFor":
                    cl = re.match(r"\s*([\\\w]+)::class", args)
                    if cl:
                        cols[snake(cl.group(1).rsplit("\\", 1)[-1]) + "_id"] = "int"
                elif meth == "dropColumn":
                    for n in names:
                        cols.pop(n, None)
                elif meth == "renameColumn" and len(names) >= 2:
                    cols[names[1]] = cols.pop(names[0], "mixed")
                elif meth in _COLUMN_TYPES and first:
                    cols[first] = meth
        for dm2 in re.finditer(r"Schema::(?:drop|dropIfExists)\s*\(\s*['\"](\w+)['\"]", up):
            tables.pop(dm2.group(1), None)
    return tables


def sqlite_tables(folder) -> dict[str, dict[str, str]]:
    """{table: {column: type}} of database/database.sqlite (the real schema after migrate)."""
    folder = Path(folder)
    envs = {k: v for k, v, _ in parse_env(folder / ".env")}
    if envs.get("DB_CONNECTION", "sqlite") != "sqlite":
        return {}
    db = envs.get("DB_DATABASE") or ""
    p = Path(db) if db and Path(db).is_absolute() else folder / "database" / "database.sqlite"
    if not p.is_file() or p.stat().st_size == 0:
        return {}
    out: dict[str, dict[str, str]] = {}
    try:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=1)
        try:
            for (t,) in con.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'"):
                out[t] = {r[1]: (r[2] or "mixed").lower() for r in con.execute(f'pragma table_info("{t}")')}
        finally:
            con.close()
    except sqlite3.Error:
        return {}
    return out


# ============================================================================ routes files
_ROUTE_START = re.compile(r"\bRoute::(get|post|put|patch|delete|options|any|match|resource|apiResource|"
                          r"resources|apiResources|view|redirect|permanentRedirect|singleton|fallback)\s*\(")
_RES_ACTIONS = ["index", "create", "store", "show", "edit", "update", "destroy"]
_RES_METHODS = {"index": "GET", "create": "GET", "store": "POST", "show": "GET", "edit": "GET", "update": "PUT",
                "destroy": "DELETE"}


def _group_regions(text: str) -> list[tuple[int, int, str, str]]:
    """[(start, end, name prefix, uri prefix)] of ``Route::...->group(function () { ... })`` blocks."""
    out = []
    for m in re.finditer(r"->group\s*\(\s*(?:static\s+)?function\s*\([^)]*\)\s*(?::\s*\w+\s*)?\{", text):
        stmt_start = max(text.rfind(";", 0, m.start()), text.rfind("{", 0, m.start()), text.rfind("}", 0, m.start()))
        head = text[stmt_start + 1:m.start()]
        if "Route::" not in head:
            continue
        name = "".join(re.findall(r"(?:->|::)(?:name|as)\s*\(\s*['\"]([^'\"]*)['\"]", head))
        prefix = "/".join(x.strip("/") for x in re.findall(r"(?:->|::)prefix\s*\(\s*['\"]([^'\"]*)['\"]", head))
        body = _balanced(text[m.end():], "{", "}")
        out.append((m.end(), m.end() + len(body), name, prefix))
    return out


def parse_routes_file(path) -> list[dict]:
    """Routes declared in one routes/*.php file: [{name, method, uri, file, line, action}]."""
    path = Path(path)
    text = read_text(path)
    groups = _group_regions(text)
    uses = uses_of(text)
    out = []
    for m in _ROUTE_START.finditer(text):
        kind = m.group(1)
        args = _balanced(text[m.end():])
        end = m.end() + len(args) + 1
        # the rest of the statement: ->name('x')->middleware(...) ... up to ';' at depth 0 or '->group('
        tail = ""
        i = end
        depth = 0
        while i < len(text):
            c = text[i]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
                if depth < 0:
                    break
            elif c == ";" and depth == 0:
                break
            tail += c
            i += 1
        if "->group(" in tail:
            continue
        name_prefix = "".join(g[2] for g in groups if g[0] <= m.start() < g[1])
        uri_prefix = "/".join(g[3] for g in groups if g[0] <= m.start() < g[1] and g[3])
        strs = re.findall(r"['\"]([^'\"]*)['\"]", args)
        uri = strs[0] if strs else ""
        if kind == "match" and len(strs) > 1:
            uri = re.findall(r"\]\s*,\s*['\"]([^'\"]*)['\"]", args)
            uri = uri[0] if uri else strs[-1]
        full_uri = "/" + "/".join(x.strip("/") for x in (uri_prefix, uri) if x.strip("/"))
        line = line_of(text, m.start())
        action = ""
        am = re.search(r"\[\s*([\\\w]+)::class\s*,\s*['\"](\w+)['\"]\s*\]", args)
        cm = re.search(r",\s*([\\\w]+)::class", args)
        if am:
            action = uses.get(am.group(1), am.group(1)) + "@" + am.group(2)
        elif cm:
            action = uses.get(cm.group(1), cm.group(1))
        elif "function" in args or "fn" in args:
            action = "Closure"
        nm = re.search(r"->name\s*\(\s*['\"]([^'\"]+)['\"]", tail)
        if kind in ("resource", "apiResource", "singleton"):
            base = uri.replace("/", ".")
            acts = [a for a in _RES_ACTIONS if not (kind == "apiResource" and a in ("create", "edit"))]
            only = re.search(r"->only\s*\(\s*\[([^\]]*)\]", tail)
            exc = re.search(r"->except\s*\(\s*\[([^\]]*)\]", tail)
            if only:
                acts = [a for a in acts if a in re.findall(r"\w+", only.group(1))]
            if exc:
                acts = [a for a in acts if a not in re.findall(r"\w+", exc.group(1))]
            param = snake(uri.rsplit("/", 1)[-1].rstrip("s")) if uri else "id"
            for a in acts:
                u = full_uri + ({"create": "/create", "show": f"/{{{param}}}", "edit": f"/{{{param}}}/edit",
                                 "update": f"/{{{param}}}", "destroy": f"/{{{param}}}"}.get(a, ""))
                out.append({"name": f"{name_prefix}{base}.{a}", "method": _RES_METHODS[a], "uri": u,
                            "file": str(path), "line": line, "action": f"{action}@{a}" if action else ""})
            continue
        method = {"view": "GET", "redirect": "GET", "permanentRedirect": "GET", "fallback": "GET",
                  "any": "ANY", "match": "|".join(x.upper() for x in strs[:-1]) or "GET"}.get(kind, kind.upper())
        if kind == "view" and len(strs) > 1:
            action = "view:" + strs[1]
        out.append({"name": (name_prefix + nm.group(1)) if nm else "", "method": method, "uri": full_uri,
                    "file": str(path), "line": line, "action": action})
    return out


def route_list(folder, php: str = "") -> list[dict]:
    """``php artisan route:list --json`` -> [{name, method, uri, action, middleware, file, line}]."""
    folder = Path(folder)
    code, out = run_php(folder, ["artisan", "route:list", "--json", "--no-ansi"], 90, php=php)
    if code != 0:
        return []
    start = out.find("[")
    try:
        rows = json.loads(out[start:]) if start >= 0 else []
    except ValueError:
        return []
    res = []
    for r in rows:
        file, line = "", 0
        loc = r.get("path") or ""
        action = r.get("action") or ""
        if loc and ":" in loc:
            f, _, ln = loc.rpartition(":")
            file, line = str((folder / f).resolve()), int(ln) if ln.isdigit() else 0
        if "@" in action or (action and action != "Closure" and "\\" in action):
            cls, _, meth = action.partition("@")
            cf = class_file(folder, cls)
            if cf is not None:
                file, line = str(cf), method_line(cf, meth or "__invoke")
        uri = "/" + str(r.get("uri", "")).lstrip("/")
        res.append({"name": r.get("name") or "", "method": r.get("method", ""), "uri": uri, "action": action,
                    "middleware": r.get("middleware") or [], "file": file, "line": line,
                    "vendor": "vendor" in loc.replace("\\", "/").split("/")[:1] or loc.startswith("vendor")})
    return res


# ============================================================================ artisan commands
_ARTISAN: dict[str, tuple[tuple, list[dict]]] = {}


def artisan_commands(folder, php: str = "") -> list[dict]:
    """``artisan list --format=json`` commands: [{name, description, usage, arguments: [...], options: [...]}],
    cached until composer.lock / app/Console change."""
    folder = Path(folder)
    key = os.path.normcase(str(folder))
    stamp = tree_stamp(folder, ["app/Console", "routes"], files=("composer.lock",))
    hit = _ARTISAN.get(key)
    if hit and hit[0] == stamp:
        return hit[1]
    code, out = run_php(folder, ["artisan", "list", "--format=json", "--no-ansi"], 90, php=php)
    start = out.find("{")
    try:
        data = json.loads(out[start:]) if code == 0 and start >= 0 else {}
    except ValueError:
        data = {}
    cmds = []
    for c in data.get("commands", []):
        if c.get("hidden"):
            continue
        d = c.get("definition") or {}
        args = [{"name": a.get("name"), "required": bool(a.get("is_required")), "array": bool(a.get("is_array")),
                 "description": a.get("description", ""), "default": a.get("default")}
                for a in (d.get("arguments") or {}).values()]
        opts = []
        for o in (d.get("options") or {}).values():
            n = str(o.get("name", "")).lstrip("-")
            if n in ("help", "quiet", "verbose", "version", "ansi", "no-ansi", "no-interaction", "env", "silent"):
                continue
            opts.append({"name": n, "shortcut": str(o.get("shortcut") or "").lstrip("-"),
                         "value": bool(o.get("accept_value")), "required": bool(o.get("is_value_required")),
                         "multiple": bool(o.get("is_multiple")), "description": o.get("description", ""),
                         "default": o.get("default")})
        cmds.append({"name": c.get("name", ""), "description": c.get("description", ""),
                     "usage": (c.get("usage") or [""])[0], "arguments": args, "options": opts})
    if cmds:
        _ARTISAN[key] = (stamp, cmds)
    return cmds


def artisan_argv(command: str, values: dict) -> list[str]:
    """argv after ``php artisan`` for a command and the form values {arg/option name: value | bool | list}."""
    argv = [command]
    for k, v in values.items():
        if k.startswith("--"):
            n = k[2:]
            if v is True:
                argv.append(f"--{n}")
            elif v not in (None, False, ""):
                for one in (v if isinstance(v, list) else [v]):
                    argv.append(f"--{n}={one}")
    for k, v in values.items():
        if not k.startswith("--") and v not in (None, "", False):
            argv += v if isinstance(v, list) else str(v).split() if k.endswith("[]") else [str(v)]
    return argv


# ============================================================================ type inference
# a type is ("model", FQCN) | ("collection", FQCN) | ("builder", FQCN) | ("mixed", "")
_RESOLVE_MODEL = re.compile(r"([A-Z]\w*)::")
_TO_MODEL = ("find", "findOrFail", "first", "firstOrFail", "create", "firstOrCreate", "firstOrNew", "updateOrCreate",
             "make", "sole", "findOrNew", "forceCreate", "firstWhere", "fresh", "replicate", "refresh")
_TO_COLLECTION = ("get", "all", "paginate", "simplePaginate", "cursorPaginate", "findMany", "cursor", "lazy")
BUILDER_METHODS = ("where", "orWhere", "whereIn", "whereNotIn", "whereNull", "whereNotNull", "whereBetween",
                   "whereDate", "whereHas", "whereDoesntHave", "whereRelation", "with", "withCount", "has",
                   "doesntHave", "orderBy", "orderByDesc", "latest", "oldest", "inRandomOrder", "limit", "take",
                   "skip", "offset", "select", "addSelect", "distinct", "groupBy", "having", "join", "leftJoin",
                   "when", "unless", "tap", "withTrashed", "onlyTrashed", "lockForUpdate", "query", "newQuery",
                   "scopes", "without", "withWhereHas", "whereKey", "whereLike", "whereAny", "whereAll")
TERMINAL_METHODS = _TO_MODEL + _TO_COLLECTION + ("count", "exists", "doesntExist", "sum", "avg", "min", "max",
                                                  "pluck", "value", "delete", "update", "increment", "decrement",
                                                  "chunk", "each", "insert", "upsert", "destroy", "toSql",
                                                  "dd", "dump")
MODEL_METHODS = ("save", "update", "delete", "forceDelete", "restore", "fill", "load", "loadMissing", "loadCount",
                 "fresh", "refresh", "replicate", "toArray", "toJson", "is", "isNot", "isDirty", "isClean",
                 "wasChanged", "getKey", "getAttribute", "setAttribute", "push", "touch", "increment", "decrement",
                 "getOriginal", "only", "makeHidden", "makeVisible", "append", "exists", "wasRecentlyCreated")
COLLECTION_METHODS = ("each", "map", "filter", "first", "last", "count", "isEmpty", "isNotEmpty", "pluck", "sortBy",
                      "sortByDesc", "groupBy", "keyBy", "where", "firstWhere", "contains", "sum", "avg", "max", "min",
                      "toArray", "toJson", "values", "keys", "take", "chunk", "reject", "load", "links", "total",
                      "currentPage", "lastPage", "perPage", "hasPages", "items", "unique", "implode", "merge")


def resolve_class(idx: LaravelIndex, short: str, text: str = "") -> str:
    """Short class name -> FQCN of a model ("" when it is not one)."""
    short = short.lstrip("\\")
    if "\\" in short:
        return short if short in idx.models() else ""
    if text:
        fq = uses_of(text).get(short)
        if fq and fq in idx.models():
            return fq
    m = idx.model_by_short(short)
    return m["fqcn"] if m else ""


def expr_type(idx: LaravelIndex, scope: str, expr: str) -> tuple | None:
    """Type of a PHP expression like ``Post::latest()->paginate(10)`` / ``$post->user`` / ``auth()->user()``."""
    expr = expr.strip().rstrip(";")
    if re.match(r"(?:auth\(\)|Auth::|\$request)\s*->\s*user\(\)|Auth::user\(\)|auth\(\)->user\(\)|"
                r"\$request->user\(\)|request\(\)->user\(\)", expr):
        fq = resolve_class(idx, "User", scope)
        base = ("model", fq) if fq else None
        rest = re.sub(r"^.*?user\(\)", "", expr, count=1)
        return _walk_chain(idx, base, rest) if base else None
    m = re.match(r"new\s+([\\\w]+)", expr)
    if m:
        fq = resolve_class(idx, m.group(1), scope)
        return ("model", fq) if fq else None
    m = re.match(r"([\\\w]+)::(\w+)", expr)
    if m:
        fq = resolve_class(idx, m.group(1), scope)
        if not fq:
            return None
        return _walk_chain(idx, ("builder", fq), "->" + expr[m.end(1) + 2:])
    m = re.match(r"\$(\w+)", expr)
    if m:
        base = var_type(idx, scope, m.group(1))
        return _walk_chain(idx, base, expr[m.end():]) if base else None
    return None


def _walk_chain(idx: LaravelIndex, t: tuple | None, chain: str) -> tuple | None:
    """Apply ``->a()->b->c(...)`` steps to a type."""
    pos = 0
    while t is not None:
        m = re.compile(r"\s*(?:\?->|->)\s*(\w+)\s*").match(chain, pos)
        if not m:
            break
        name = m.group(1)
        pos = m.end()
        call = pos < len(chain) and chain[pos] == "("
        if call:
            inner = _balanced(chain[pos + 1:])
            pos += len(inner) + 2
        kind, fq = t
        model = idx.models().get(fq) if fq else None
        if kind == "builder":
            if name in _TO_MODEL:
                t = ("model", fq)
            elif name in _TO_COLLECTION:
                t = ("collection", fq)
            elif name in BUILDER_METHODS or (model and name in model["scopes"]):
                t = ("builder", fq)
            else:
                t = ("mixed", "")
        elif kind == "model":
            rel = (model or {}).get("relations", {}).get(name)
            if rel:
                many = rel[0] in ("hasMany", "belongsToMany", "morphMany", "morphToMany", "hasManyThrough",
                                  "morphedByMany")
                if call:
                    t = ("builder", rel[1]) if rel[1] else ("mixed", "")
                else:
                    t = (("collection" if many else "model"), rel[1]) if rel[1] else ("mixed", "")
            elif name in ("fresh", "refresh", "replicate", "load", "loadMissing", "loadCount"):
                t = ("model", fq)
            else:
                t = ("mixed", "")
        elif kind == "collection":
            t = ("model", fq) if name in ("first", "last", "find", "firstWhere", "sole") else \
                ("collection", fq) if name in ("filter", "sortBy", "sortByDesc", "where", "take", "values",
                                               "reject", "unique", "load", "each", "withQueryString",
                                               "appends", "fragment", "withPath", "onEachSide",
                                               "loadMissing", "loadCount") else ("mixed", "")
        else:
            t = ("mixed", "")
    return t


def var_type(idx: LaravelIndex, scope: str, var: str, depth: int = 0) -> tuple | None:
    """Type of ``$var`` from the code before the cursor: typed parameters, assignments, foreach, @foreach."""
    if depth > 4 or not var:
        return None
    v = re.escape(var)
    if var == "this":
        cls = re.findall(r"\bclass\s+(\w+)", scope)
        fq = resolve_class(idx, cls[-1], scope) if cls else ""
        return ("model", fq) if fq else None
    best: tuple[int, tuple] | None = None
    for m in re.finditer(rf"([\\\w]+)\s+(?:\.\.\.)?\${v}\b(?=\s*[,)=])", scope):          # typed parameter
        fq = resolve_class(idx, m.group(1), scope)
        if fq and (best is None or m.start() > best[0]):
            best = (m.start(), ("model", fq))
    for m in re.finditer(rf"\${v}\s*=(?!=)\s*([^;]+?)\s*;", scope):                       # assignment
        t = expr_type(idx, scope[:m.start()], m.group(1))
        if t and t[0] != "mixed" and (best is None or m.start() > best[0]):
            best = (m.start(), t)
    for m in re.finditer(rf"foreach\s*\(\s*(.+?)\s+as\s+(?:\$\w+\s*=>\s*)?\${v}\s*\)", scope):   # foreach / @foreach
        t = expr_type(idx, scope[:m.start()], m.group(1))
        if t and t[0] in ("collection", "builder") and (best is None or m.start() > best[0]):
            best = (m.start(), ("model", t[1]))
    for m in re.finditer(rf"@forelse\s*\(\s*(.+?)\s+as\s+\${v}\s*\)", scope):
        t = expr_type(idx, scope[:m.start()], m.group(1))
        if t and t[0] in ("collection", "builder") and (best is None or m.start() > best[0]):
            best = (m.start(), ("model", t[1]))
    if best:
        return best[1]
    return None


# ============================================================================ completion
ROUTE_FUNCS = {"route", "to_route", "->route", "Route::has", "URL::route", "->routeIs", "Route::is",
               "Redirect::route", "->named", "@routeis", "Route::currentRouteNamed", "->currentRouteNamed"}
VIEW_FUNCS = {"view": 0, "View::make": 0, "->view": 0, "View::exists": 0, "view()->exists": 0, "@include": 0,
              "@extends": 0, "@includeIf": 0, "@includeWhen": 1, "@includeUnless": 1, "@includeFirst": 0,
              "@each": 0, "@component": 0, "Route::view": 1, "->markdown": 0, "@inject": -1, "->exists": 0}
CONFIG_FUNCS = {"config", "Config::get", "Config::set", "Config::has", "Config::string", "Config::integer",
                "Config::boolean", "Config::array", "config()->get", "@config"}
LANG_FUNCS = {"__", "trans", "trans_choice", "@lang", "@choice", "Lang::get", "Lang::has", "Lang::choice"}
ASSET_FUNCS = {"asset", "secure_asset", "url", "Vite::asset", "@vite", "mix", "public_path", "resource_path"}
COLUMN_FUNCS = {"where", "orWhere", "whereIn", "whereNotIn", "whereNull", "whereNotNull", "orderBy", "orderByDesc",
                "latest", "oldest", "select", "addSelect", "pluck", "value", "sum", "avg", "min", "max", "groupBy",
                "increment", "decrement", "whereBetween", "whereDate", "whereMonth", "whereYear", "firstWhere",
                "whereColumn", "whereLike", "sortBy", "sortByDesc", "orWhereNull", "whereTime", "getAttribute",
                "only", "except", "isDirty", "wasChanged", "having", "distinct", "keyBy"}
RELATION_FUNCS = {"with", "load", "has", "whereHas", "doesntHave", "withCount", "loadMissing", "whereDoesntHave",
                  "orWhereHas", "loadCount", "withWhereHas", "whereRelation", "relationLoaded", "without"}
MIDDLEWARE = ["auth", "auth:sanctum", "auth.basic", "guest", "verified", "signed", "throttle:60,1", "throttle:api",
              "can:", "password.confirm", "cache.headers", "precognitive", "web", "api"]
RULES = ["required", "nullable", "string", "integer", "numeric", "boolean", "array", "email", "url", "uuid",
         "date", "confirmed", "accepted", "file", "image", "min:", "max:", "between:", "size:", "in:", "not_in:",
         "unique:", "exists:", "regex:", "same:", "different:", "after:", "before:", "alpha", "alpha_num",
         "alpha_dash", "digits:", "digits_between:", "mimes:", "json", "present", "sometimes", "filled", "prohibited",
         "required_if:", "required_with:", "required_without:", "lowercase", "uppercase", "ip", "decimal:",
         "current_password", "password", "starts_with:", "ends_with:", "dimensions:", "bail", "distinct", "gt:",
         "gte:", "lt:", "lte:", "timezone", "ulid", "list", "hex_color", "active_url", "enum"]

BLADE_DIRECTIVES = [
    ("if", "@if (${1:condition})\n\t$0\n@endif"), ("elseif", "@elseif (${1:condition})"), ("else", "@else"),
    ("endif", "@endif"), ("unless", "@unless (${1:condition})\n\t$0\n@endunless"),
    ("isset", "@isset(\\$${1:var})\n\t$0\n@endisset"), ("empty", "@empty(\\$${1:var})\n\t$0\n@endempty"),
    ("auth", "@auth\n\t$0\n@endauth"), ("guest", "@guest\n\t$0\n@endguest"),
    ("foreach", "@foreach (\\$${1:items} as \\$${2:item})\n\t$0\n@endforeach"), ("endforeach", "@endforeach"),
    ("forelse", "@forelse (\\$${1:items} as \\$${2:item})\n\t$0\n@empty\n\t\n@endforelse"),
    ("for", "@for (\\$i = 0; \\$i < ${1:10}; \\$i++)\n\t$0\n@endfor"), ("while", "@while (${1:condition})\n\t$0\n@endwhile"),
    ("switch", "@switch(\\$${1:var})\n\t@case(${2:1})\n\t\t$0\n\t\t@break\n\t@default\n@endswitch"),
    ("case", "@case(${1:value})"), ("break", "@break"), ("continue", "@continue"), ("default", "@default"),
    ("extends", "@extends('${1:layouts.app}')"), ("section", "@section('${1:content}')\n\t$0\n@endsection"),
    ("endsection", "@endsection"), ("yield", "@yield('${1:content}')"), ("show", "@show"), ("parent", "@parent"),
    ("include", "@include('${1:view}')"), ("includeIf", "@includeIf('${1:view}')"),
    ("includeWhen", "@includeWhen(${1:condition}, '${2:view}')"), ("each", "@each('${1:view}', \\$${2:items}, '${3:item}')"),
    ("component", "@component('${1:view}')\n\t$0\n@endcomponent"), ("slot", "@slot('${1:name}')\n\t$0\n@endslot"),
    ("props", "@props(['${1:name}'])"), ("aware", "@aware(['${1:name}'])"),
    ("csrf", "@csrf"), ("method", "@method('${1|PUT,PATCH,DELETE|}')"),
    ("error", "@error('${1:field}')\n\t<div class=\"error\">{{ \\$message }}</div>\n@enderror"),
    ("old", "@old('${1:field}')"),
    ("can", "@can('${1:update}', \\$${2:model})\n\t$0\n@endcan"), ("cannot", "@cannot('${1:update}', \\$${2:model})\n\t$0\n@endcannot"),
    ("env", "@env('${1:local}')\n\t$0\n@endenv"), ("production", "@production\n\t$0\n@endproduction"),
    ("push", "@push('${1:scripts}')\n\t$0\n@endpush"), ("stack", "@stack('${1:scripts}')"),
    ("once", "@once\n\t$0\n@endonce"), ("php", "@php\n\t$0\n@endphp"), ("json", "@json(\\$${1:data})"),
    ("verbatim", "@verbatim\n\t$0\n@endverbatim"), ("lang", "@lang('${1:key}')"), ("vite", "@vite(['resources/css/app.css', 'resources/js/app.js'])"),
    ("checked", "@checked(${1:condition})"), ("selected", "@selected(${1:condition})"),
    ("disabled", "@disabled(${1:condition})"), ("readonly", "@readonly(${1:condition})"), ("required", "@required(${1:condition})"),
    ("class", "@class(['${1:class}' => ${2:condition}])"), ("style", "@style(['${1:color: red}' => ${2:condition}])"),
    ("dump", "@dump(\\$${1:var})"), ("dd", "@dd(\\$${1:var})"), ("session", "@session('${1:status}')\n\t{{ \\$value }}\n@endsession"),
    ("fragment", "@fragment('${1:name}')\n\t$0\n@endfragment"), ("use", "@use('${1:App\\\\Models\\\\Post}')"),
    ("inject", "@inject('${1:name}', '${2:App\\\\Services\\\\Service}')"), ("hasSection", "@hasSection('${1:name}')\n\t$0\n@endif"),
    ("sectionMissing", "@sectionMissing('${1:name}')\n\t$0\n@endif"), ("includeFirst", "@includeFirst(['${1:view}'])"),
    ("endunless", "@endunless"), ("endisset", "@endisset"), ("endempty", "@endempty"), ("endauth", "@endauth"),
    ("endguest", "@endguest"), ("endforelse", "@endforelse"), ("endfor", "@endfor"), ("endwhile", "@endwhile"),
    ("endswitch", "@endswitch"), ("endcan", "@endcan"), ("endpush", "@endpush"), ("endphp", "@endphp"),
    ("enderror", "@enderror"), ("endonce", "@endonce"), ("endcomponent", "@endcomponent"), ("endslot", "@endslot"),
    ("endenv", "@endenv"), ("endproduction", "@endproduction"), ("endverbatim", "@endverbatim"),
    ("endsession", "@endsession"), ("endfragment", "@endfragment"), ("livewire", "@livewire('${1:name}')"),
]
BLADE_GLOBALS = {"errors": "ViewErrorBag (validation errors)", "loop": "loop variable (index, iteration, first, last, "
                 "count, remaining, depth, parent)", "slot": "component slot", "attributes": "component attributes",
                 "app": "application", "__env": "view factory", "message": "@error message", "value": "@session value"}
LOOP_PROPS = ["index", "iteration", "remaining", "count", "first", "last", "even", "odd", "depth", "parent"]


def is_blade(path) -> bool:
    return str(path).lower().endswith(".blade.php")


def view_name_of(folder, path) -> str:
    base = Path(folder) / "resources" / "views"
    try:
        r = Path(path).resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return ""
    return (r[:-len(".blade.php")] if r.endswith(".blade.php") else r[:-4]).replace("/", ".")


def complete(folder, path, text: str, line: int, col: int) -> list[dict] | None:
    """Laravel IntelliSense at (line, col) (0-based). None = nothing framework specific here; items with
    ``exclusive`` in their dict mean "only these" (inside framework strings)."""
    idx = index(folder)
    lines = text.split("\n")
    cur = lines[line] if 0 <= line < len(lines) else ""
    before = cur[:col]
    blade = is_blade(path)
    php_before = blade_php_segment(before) if blade else before
    sc = string_context(php_before)
    if sc is not None and (not blade or php_before is not before or _in_directive(before)):
        code_before, typed, _q = sc
        res = _complete_string(idx, path, text, lines, line, col, code_before, typed, blade)
        if res is not None:
            for it in res:
                it["exclusive"] = True
            return res
        return None
    if blade:
        res = _complete_blade(idx, path, text, lines, line, col, before)
        if res is not None:
            return res
    m = re.search(r"((?:\$\w+|[A-Z]\w*::\w+\(.*?\)|auth\(\)->user\(\)|Auth::user\(\)|\$request->user\(\))"
                  r"(?:\s*(?:\?->|->)\s*\w+(?:\((?:[^()]|\([^()]*\))*\))?)*)\s*(?:\?->|->)\s*(\w*)$", before)
    if m:
        scope = _scope_before(text, lines, line, col, path)
        return _member_items(idx, scope, m.group(1), m.group(2), line, col)
    m = re.search(r"\b([A-Z]\w*)::(\w*)$", before)
    if m:
        fq = resolve_class(idx, m.group(1), text)
        if fq:
            return _builder_items(idx, fq, static=True)
    return None


def blade_php_segment(before: str) -> str:
    """The PHP part of a Blade line before the cursor: the text after an unclosed ``{{`` / ``{!!`` or bound
    attribute ``:prop="``; the line itself otherwise."""
    i = max(before.rfind("{{"), before.rfind("{!!"))
    j = max(before.rfind("}}"), before.rfind("!!}"))
    if i > j:
        return before[i + (3 if before.startswith("{!!", i) else 2):]
    m = None
    for m in re.finditer(r"""\s:[\w.-]+\s*=\s*"([^"]*)$""", before):
        pass
    if m is not None:
        return m.group(1)
    return before


def _in_directive(before: str) -> bool:
    """Inside the (...) of a Blade directive: @include('x / @foreach (...)."""
    m = None
    for m in re.finditer(r"@\w+\s*\(", before):
        pass
    if m is None:
        return False
    tail = before[m.end():]
    return tail.count("(") >= tail.count(")")


def _scope_before(text, lines, line, col, path) -> str:
    """Code before the cursor (+ for Blade views the controller variables are resolved separately)."""
    off = sum(len(x) + 1 for x in lines[:line]) + col
    return text[:off]


def _complete_string(idx: LaravelIndex, path, text, lines, line, col, code_before, typed, blade) -> list[dict] | None:
    ctx = call_context(code_before)
    rng = string_range(line, col, typed)
    if ctx is None and not blade:          # a call / array that started on an earlier line
        off = sum(len(x) + 1 for x in lines[:line]) + len(code_before)
        ctx = call_context(text[max(0, off - 800):off])
    if ctx is None:
        return None
    callee, argi, recv = ctx
    short = callee.split("::")[-1].lstrip("->") if callee.startswith("->") else callee
    if callee in ROUTE_FUNCS and argi == 0:
        out = []
        for r in idx.routes():
            if r.get("name"):
                out.append(item(r["name"], K_REFERENCE, f"{r.get('method', '')} {r.get('uri', '')}".strip(),
                                f"{r.get('action') or ''}\n\n{_rel(idx, r.get('file'))}:{r.get('line') or ''}", rng=rng,
                                filter_text=r["name"]))
        return out
    if callee in VIEW_FUNCS and VIEW_FUNCS[callee] == argi:
        return [item(n, K_FILE, "view", _rel(idx, p), rng=rng) for n, p in idx.views().items()
                if not n.startswith("components.") or callee in ("view", "->view", "@include")]
    if callee in CONFIG_FUNCS and argi == 0:
        return [item(k, K_PROPERTY if leaf else K_MODULE, preview, _rel(idx, p) + f":{ln}", rng=rng)
                for k, p, ln, leaf, preview in idx.config_keys()]
    if callee in LANG_FUNCS and argi == 0:
        return [item(k, K_TEXT, preview[:80], _rel(idx, p) + f":{ln}", rng=rng) for k, p, ln, preview in idx.lang_keys()]
    if callee == "env" and argi == 0:
        return [item(k, K_CONSTANT, v, _rel(idx, p) + f":{ln}", rng=rng) for k, v, p, ln in idx.env_keys()]
    if callee in ASSET_FUNCS or (callee == "[" and "@vite" in recv[-40:]):
        return [item(f, K_FILE, "public" if not f.startswith("resources/") else "Vite entry", rng=rng)
                for f in idx.public_files()]
    if short in ("middleware", "withoutMiddleware") and callee.startswith(("->", "Route::")):
        return [item(m_, K_VALUE, "middleware", rng=rng) for m_ in MIDDLEWARE]
    if callee == "compact":
        scope = text[:sum(len(x) + 1 for x in lines[:line])]
        names = sorted(set(re.findall(r"\$(\w+)\s*=(?!=)", scope[-6000:])) - {"this"})
        return [item(n, K_VARIABLE, "variable", rng=rng) for n in names]
    if callee.startswith(("->", "::")) or "::" in callee:
        meth = callee.split("->")[-1].split("::")[-1]
        recv_expr = recv if callee.startswith("->") else callee.split("::")[0] + "::query()"
        if callee.startswith("->"):
            recv_expr = recv
        if meth in COLUMN_FUNCS or meth in RELATION_FUNCS:
            scope = _scope_before(text, lines, line, col, path)
            t = _receiver_type(idx, scope, recv_expr, path)
            if t and t[1]:
                model = idx.models().get(t[1])
                if model:
                    if meth in RELATION_FUNCS:
                        return [item(n, K_PROPERTY, f"{k} {v.rsplit(chr(92), 1)[-1]}", rng=rng)
                                for n, (k, v) in model["relations"].items()]
                    return [item(c, K_FIELD, f"{ty} ({model['table']})", rng=rng) for c, ty in model["columns"].items()]
    # validation rules: 'field' => 'required|...'  /  ['required', '...
    if callee == "[" or array_key_before(code_before):
        window = text[:sum(len(x) + 1 for x in lines[:line])][-1500:] + code_before
        if re.search(r"validate\w*\s*\(|Validator::make|function\s+rules\s*\(|->rules\s*\(", window):
            part = typed.rsplit("|", 1)[-1]
            r2 = string_range(line, col, part)
            return [item(r_, K_KEYWORD, "validation rule", rng=r2) for r_ in RULES]
    return None


def _receiver_type(idx, scope, recv_expr: str, path) -> tuple | None:
    m = re.search(r"((?:\$\w+|[A-Z]\w*::\w+\((?:[^()]|\([^()]*\))*\)|auth\(\)->user\(\)|Auth::user\(\))"
                  r"(?:\s*(?:\?->|->)\s*\w+(?:\((?:[^()]|\([^()]*\))*\))?)*)\s*$", recv_expr)
    if not m:
        return None
    return _expr_type_view(idx, scope, m.group(1), path)


def _expr_type_view(idx, scope, expr, path) -> tuple | None:
    t = expr_type(idx, scope, expr)
    if t is None and is_blade(path):
        vm = re.match(r"\$(\w+)", expr)
        if vm:
            vt = idx.view_vars(view_name_of(idx.folder, path)).get(vm.group(1))
            if vt and vt[0] != "mixed":
                t = _walk_chain(idx, vt, expr[vm.end():])
    return t


def _member_items(idx: LaravelIndex, scope: str, expr: str, typed: str, line: int, col: int) -> list[dict] | None:
    path_hint = getattr(idx, "_current_path", "")
    t = _expr_type_view(idx, scope, expr, path_hint)
    if (t is None or t[0] == "mixed") and is_blade(path_hint):
        # foreach over a view variable inside the Blade file: @foreach ($posts as $post)
        vm = re.match(r"\$(\w+)", expr)
        if vm:
            for fm in re.finditer(rf"@(?:foreach|forelse)\s*\(\s*\$(\w+)(.*?)\s+as\s+(?:\$\w+\s*=>\s*)?\${vm.group(1)}\s*\)",
                                  scope):
                vt = idx.view_vars(view_name_of(idx.folder, path_hint)).get(fm.group(1))
                if vt:
                    ct = _walk_chain(idx, vt, fm.group(2))
                    if ct and ct[0] in ("collection", "builder"):
                        t = _walk_chain(idx, ("model", ct[1]), expr[vm.end():])
    if expr == "$loop":
        return [item(p, K_PROPERTY, "loop variable") for p in LOOP_PROPS]
    if t is None or t[0] == "mixed" or not t[1]:
        return None
    kind, fq = t
    model = idx.models().get(fq)
    if model is None:
        return None
    if kind == "model":
        out = []
        for c, ty in model["columns"].items():
            cast = model["casts"].get(c)
            out.append(item(c, K_FIELD, f"{cast or ty} - column of {model['table']}", f"{model['name']}::${c}",
                            sort="0" + c))
        for n, (k, target) in model["relations"].items():
            short = target.rsplit("\\", 1)[-1]
            many = k in ("hasMany", "belongsToMany", "morphMany", "morphToMany", "hasManyThrough", "morphedByMany")
            out.append(item(n, K_PROPERTY, f"{k}: {'Collection<' + short + '>' if many else short}",
                            f"relation {model['name']}::{n}()", sort="1" + n))
            out.append(item(n + "()", K_METHOD, f"{k}(): relation query", insert=n + "()", sort="3" + n))
        for a in model["accessors"]:
            out.append(item(a, K_PROPERTY, "accessor", sort="2" + a))
        for mm in MODEL_METHODS:
            out.append(item(mm, K_METHOD, "Eloquent model", insert=mm + "($0)", snippet=True, sort="4" + mm))
        return out
    if kind == "builder":
        return _builder_items(idx, fq, static=False)
    if kind == "collection":
        return [item(mm, K_METHOD, f"Collection<{model['name']}>", insert=mm + "($0)", snippet=True)
                for mm in COLLECTION_METHODS]
    return None


def _builder_items(idx, fq, static: bool) -> list[dict]:
    model = idx.models().get(fq) or {}
    out = []
    for s in model.get("scopes", []):
        out.append(item(s, K_METHOD, f"scope of {model.get('name')}", insert=s + "($0)", snippet=True, sort="0" + s))
    for c in model.get("columns", {}):
        w = "where" + "".join(p[:1].upper() + p[1:] for p in c.split("_"))
        out.append(item(w, K_METHOD, f"dynamic where on {c}", insert=w + "($0)", snippet=True, sort="3" + w))
    for mm in BUILDER_METHODS + TERMINAL_METHODS:
        out.append(item(mm, K_METHOD, f"Eloquent Builder<{model.get('name', '')}>", insert=mm + "($0)", snippet=True,
                        sort="1" + mm))
    if static:
        for mm in ("all", "query", "create", "find", "findOrFail", "destroy", "factory", "firstOrCreate",
                   "updateOrCreate"):
            out.append(item(mm, K_METHOD, f"static {model.get('name', '')}::{mm}()", insert=mm + "($0)", snippet=True,
                            sort="0" + mm))
    return out


def _complete_blade(idx, path, text, lines, line, col, before) -> list[dict] | None:
    # @directives
    m = re.search(r"(?:^|[^\w@])@(\w*)$", before)
    if m:
        start = col - len(m.group(1)) - 1
        rng = [line, start, line, col]
        return [item("@" + n, K_SNIPPET if "\n" in body or "$" in body else K_KEYWORD, "Blade directive",
                     body.replace("\\$", "$").replace("\t", "    "), insert=body, rng=rng, snippet=True,
                     filter_text="@" + n, sort=f"{i:03d}") for i, (n, body) in enumerate(BLADE_DIRECTIVES)]
    # <x-component
    m = re.search(r"<x-([\w.:-]*)$", before)
    if m:
        rng = [line, col - len(m.group(1)), line, col]
        out = []
        for name, c in idx.components().items():
            props = c.get("props") or {}
            req = [p for p, d in props.items() if not d]
            attrs = "".join(f' {p}="${{{i + 1}}}"' for i, p in enumerate(req))
            out.append(item(name, K_CLASS, "Blade component" + (f" ({c['class']})" if c.get("class") else ""),
                            "props: " + (", ".join(f"{k}={v}" if v else k for k, v in props.items()) or "-") +
                            f"\n\n{_rel(idx, c['file'])}", insert=name + attrs, rng=rng, snippet=bool(attrs)))
        for builtin in ("slot", "dynamic-component"):
            out.append(item(builtin, K_KEYWORD, "Blade", rng=rng))
        return out
    # props inside <x-name ... |
    m = re.search(r"<x-([\w.:-]+)(?:\s+[:\w.-]+(?:=(?:\"[^\"]*\"|'[^']*'))?)*\s+(:?)([\w-]*)$", before)
    if m:
        comp = idx.components().get(m.group(1))
        if comp:
            rng = [line, col - len(m.group(3)), line, col]
            return [item(p, K_PROPERTY, f"prop{' = ' + d if d else ' (required)'}", insert=f'{p}="$1"', rng=rng,
                         snippet=True) for p, d in (comp.get("props") or {}).items()]
    # $variables in {{ }} / directives
    m = re.search(r"\$(\w*)$", before)
    if m and ("{{" in before or "{!!" in before or re.search(r"@\w+\s*\(", before) or "@php" in text[:2000]):
        rng = [line, col - len(m.group(1)) - 1, line, col]
        vn = view_name_of(idx.folder, path)
        out = []
        for v, t in idx.view_vars(vn).items():
            out.append(item("$" + v, K_VARIABLE, _type_text(t), "passed to view " + vn, rng=rng, sort="0" + v))
        scope = text[:sum(len(x) + 1 for x in lines[:line]) + col]
        for v in set(re.findall(r"\bas\s+(?:\$\w+\s*=>\s*)?\$(\w+)", scope)) | set(re.findall(r"\$(\w+)\s*=(?!=)", scope)):
            out.append(item("$" + v, K_VARIABLE, "local", rng=rng, sort="1" + v))
        if path and "components" in Path(path).parts:
            for p in blade_props(text):
                out.append(item("$" + p.replace("-", "_"), K_VARIABLE, "prop", rng=rng, sort="0" + p))
        for g, d in BLADE_GLOBALS.items():
            out.append(item("$" + g, K_VARIABLE, d, rng=rng, sort="2" + g))
        return out
    return None


def _type_text(t) -> str:
    if not t or t[0] == "mixed":
        return "mixed"
    short = t[1].rsplit("\\", 1)[-1]
    return {"model": short, "collection": f"Collection<{short}>", "builder": f"Builder<{short}>"}.get(t[0], short)


def _rel(idx, p) -> str:
    if not p:
        return ""
    try:
        return Path(p).resolve().relative_to(idx.folder).as_posix()
    except ValueError:
        return str(p)


def complete_items(folder, path, text: str, line: int, col: int) -> list[dict] | None:
    idx = index(folder)
    idx._current_path = str(path)
    return complete(folder, path, text, line, col)


# ============================================================================ go to definition
def _string_at(cur: str, col: int) -> tuple[str, int, int] | None:
    """The string literal of *cur* that contains *col*: (content, start col of the content, end col)."""
    for m in re.finditer(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"", cur):
        if m.start() < col <= m.end() - 0 or m.start() <= col < m.end():
            g = 1 if m.group(1) is not None else 2
            return m.group(g), m.start(g), m.end(g)
    return None


def definition(folder, path, text: str, line: int, col: int) -> tuple[str, int] | None:
    """F12 / Ctrl+click on a framework string or component -> (file, 1-based line), None = not ours."""
    idx = index(folder)
    lines = text.split("\n")
    cur = lines[line] if 0 <= line < len(lines) else ""
    # <x-component>
    for m in re.finditer(r"</?x-([\w.:-]+)", cur):
        if m.start() <= col <= m.end():
            c = idx.components().get(m.group(1))
            if c:
                if c.get("view") and not str(c["file"]).endswith(".blade.php"):
                    return str(c["file"]), 1
                return str(c["file"]), 1
    s = _string_at(cur, col)
    if s is None:
        return None
    value, start, _end = s
    ctx = call_context(cur[:start - 1])
    if ctx is None:
        # a multi-line call: look at the previous lines too
        off = sum(len(x) + 1 for x in lines[:line]) + start - 1
        ctx = call_context(text[max(0, off - 400):off])
    if ctx is None:
        return None
    callee, argi, _recv = ctx
    if callee in ROUTE_FUNCS:
        for r in idx.routes():
            if r.get("name") == value and r.get("file"):
                return str(r["file"]), int(r.get("line") or 1)
        return None
    if callee in VIEW_FUNCS or callee in ("Route::view",):
        p = idx.views().get(value)
        return (str(p), 1) if p else None
    if callee in CONFIG_FUNCS:
        best = None
        for k, p, ln, _leaf, _pv in idx.config_keys():
            if k == value:
                return str(p), ln
            if value.startswith(k + ".") or k == value.split(".")[0]:
                best = (str(p), ln)
        return best
    if callee in LANG_FUNCS:
        for k, p, ln, _pv in idx.lang_keys():
            if k == value:
                return str(p), ln
        return None
    if callee == "env":
        for k, _v, p, ln in idx.env_keys():
            if k == value:
                return str(p), ln
        return None
    if callee in ASSET_FUNCS or callee == "[":
        for base in (idx.folder / "public", idx.folder):
            p = base / value
            if p.is_file():
                return str(p), 1
    return None


__all__ = ["BLADE_DIRECTIVES", "LaravelIndex", "artisan_argv", "artisan_commands", "complete", "complete_items",
           "CREATE_OPTIONS", "configure_project", "create_laravel", "install_api", "definition", "expr_type", "generate_ide_helper", "index",
           "install_ide_helper", "is_blade", "is_laravel", "laravel_version", "migration_tables", "needs_setup",
           "parse_routes_file", "pick_php", "route_list", "router", "set_env_values", "var_type", "view_name_of"]
