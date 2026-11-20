"""App Gallery: web site templates for New Project and the App Gallery dialog
(docs/CONTRACTS.md section 8.5 - WebMatrix "Site From Template" / "App Gallery").

    from radide.web_site import gallery
    gallery.templates_for("php-web")            # -> [WebTemplate, ...] for the New Project dialog
    ok, why = gallery.check("laravel")           # are the tools / downloads available?
    gallery.create("php-sqlite-app", Path("C:/Sites/Shop"), "Shop", log=print)

Every template writes a website project (``project.radproj`` with ``"kind": "website"``,
``"language": "php-web" | "static-web" | "node-web"`` and ``"web": {"root", "start", "port"}``).
File templates live in ``radide/web_site/templates/<id>/``; ``{{APP_NAME}}`` and ``{{APP_SLUG}}``
are replaced in text files. Laravel uses ``composer create-project``; WordPress downloads
wordpress.org/latest.zip plus the "SQLite Database Integration" plugin so no MySQL is needed.
No Qt here: the module is usable from tests and scripts; the dialog is in
``radide/features/app_gallery.py``."""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

TEMPLATE_DIR = Path(__file__).with_name("templates")
PROJECT_FILE = "project.radproj"

WORDPRESS_ZIP = "https://wordpress.org/latest.zip"
SQLITE_PLUGIN_ZIP = "https://downloads.wordpress.org/plugin/sqlite-database-integration.{version}.zip"
# plugin 3.x needs SQLite >= 3.37; older SQLite libraries (e.g. PHP 8.1 on Windows has 3.36) get the
# last 2.x release
SQLITE_PLUGIN_LEGACY = "2.2.23"
SQLITE_PLUGIN_MIN_SQLITE = (3, 37, 0)
USER_AGENT = "RADIDE-AppGallery/1.0"

Log = Callable[[str], None]


@dataclass(frozen=True)
class WebTemplate:
    id: str
    title: str
    description: str
    language: str                       # plugin id: php-web | static-web | node-web
    category: str                       # "PHP", "HTML", "Node.js", "Applications"
    root: str = "."                     # web root inside the project folder
    start: str = "index.php"            # page (or script for node-web) the server starts with
    source: str = ""                    # folder in templates/ (file templates)
    needs: tuple[str, ...] = ()         # tools: php, composer, node, npm, internet
    builder: str = "files"              # files | composer-laravel | wordpress
    default_name: str = "WebSite"
    features: tuple[str, ...] = field(default=())


TEMPLATES: list[WebTemplate] = [
    WebTemplate("php-empty", "PHP Empty Site",
                "One index.php page and a stylesheet - start from scratch.",
                "php-web", "PHP", ".", "index.php", "php-empty", ("php",), default_name="PhpSite"),
    WebTemplate("php-starter", "PHP Starter Site",
                "Shared layout (header/footer includes), Home, About and Contact pages; the contact form "
                "has validation, a CSRF token and a honeypot and saves messages outside the web root.",
                "php-web", "PHP", "public", "index.php", "php-starter", ("php",), default_name="StarterSite",
                features=("Layout includes", "3 pages", "Contact form", "CSRF")),
    WebTemplate("php-sqlite-app", "PHP + SQLite Data App",
                "A complete, secure data application: register / login (password_hash, session id "
                "regeneration, login throttling), CSRF tokens, PDO prepared statements, a Products CRUD "
                "module (list, search, sort, pages, add, edit, delete, validation), flash messages and a "
                "responsive layout. The SQLite database is created on the first request.",
                "php-web", "PHP", "public", "index.php", "php-sqlite-app", ("php", "pdo_sqlite"),
                default_name="DataApp",
                features=("Accounts + login", "CRUD", "SQLite (PDO)", "CSRF", "Responsive CSS")),
    WebTemplate("html-bootstrap", "HTML Bootstrap Site",
                "Static HTML / CSS / JavaScript site with Bootstrap 5.3 bundled (works offline): navbar, "
                "hero, cards, an About page and a contact form layout.",
                "static-web", "HTML", ".", "index.html", "html-bootstrap", (), default_name="BootstrapSite",
                features=("Bootstrap 5.3.3", "3 pages", "No server code")),
    WebTemplate("node-express", "Node.js Express Site",
                "Express server (server.js) serving public/ and a small JSON REST API (/api/notes: list, "
                "add, delete). npm install runs when the project is created.",
                "node-web", "Node.js", ".", "server.js", "node-express", ("node", "npm"),
                default_name="ExpressSite", features=("Express 4", "REST API", "Static files")),
    WebTemplate("laravel", "Laravel App",
                "Laravel (latest stable) via 'composer create-project laravel/laravel' with the site's PHP: .env and "
                "APP_KEY, SQLite database (or the IDE's local MariaDB / PostgreSQL) migrated, laravel-ide-helper "
                "for IntelliSense. F5 runs it with Xdebug; Laravel panel: Artisan, Routes, Tinker.",
                "php-web", "Applications", "public", "/", "", ("php", "internet"),
                builder="composer-laravel", default_name="LaravelApp",
                features=("Composer", "SQLite", "Artisan", "IntelliSense")),
    WebTemplate("laravel-api", "Laravel API",
                "A Laravel JSON API: create-project + 'artisan install:api' (routes/api.php, Sanctum tokens) and an "
                "/api/status example route. Test it with the REST client.",
                "php-web", "Applications", "public", "/api/status", "", ("php", "internet"),
                builder="composer-laravel", default_name="LaravelApi", features=("Composer", "Sanctum", "JSON API")),
    WebTemplate("wordpress", "WordPress",
                "The latest WordPress from wordpress.org with the official 'SQLite Database Integration' "
                "plugin, so it runs without MySQL. Open the site and finish the 5-minute install.",
                "php-web", "Applications", "wordpress", "index.php", "", ("php", "pdo_sqlite", "internet"),
                builder="wordpress", default_name="WordPressSite", features=("Download", "SQLite")),
]


def get_template(template_id: str) -> WebTemplate:
    for t in TEMPLATES:
        if t.id == template_id:
            return t
    raise KeyError(f"unknown web template {template_id!r}")


def templates_for(language: str | None = None) -> list[WebTemplate]:
    """Templates of one website plugin (``php-web``...), or all of them."""
    return [t for t in TEMPLATES if language is None or t.language == language]


def new_project_entries(language: str | None = None) -> list[tuple[str, str, str]]:
    """(id, title, description) rows - the shape of features.templates.TEMPLATES."""
    return [(t.id, t.title, t.description) for t in templates_for(language)]


# ===================================================================== tools
PHP_HINTS = [r"C:\tools\php81\php.exe", r"C:\tools\php\php.exe", r"C:\php\php.exe", r"C:\xampp\php\php.exe",
             r"C:\laragon\bin\php\php.exe"]


def find_tool(name: str) -> str:
    """Path of php / composer / node / npm, or ''."""
    configured = os.environ.get(f"RADIDE_{name.upper()}", "")
    if configured and Path(configured).exists():
        return configured
    if name == "php":
        try:                                        # the interpreter configured for the PHP plugins
            from ..languages import get_plugin
            for pid in ("php-web", "php"):
                try:
                    found = get_plugin(pid).find_interpreter("")
                except Exception:  # noqa: BLE001 - plugin missing or not configured
                    found = ""
                if found:
                    return found
        except Exception:  # noqa: BLE001
            pass
    found = shutil.which(name)
    if found:
        return found
    if name == "php":
        return next((h for h in PHP_HINTS if Path(h).exists()), "")
    if name == "composer":
        for h in (r"C:\ProgramData\ComposerSetup\bin\composer.bat",
                  str(Path(os.environ.get("APPDATA", "")) / "Composer" / "vendor" / "bin" / "composer.bat")):
            if Path(h).exists():
                return h
        from .php_toolchain import find_composer       # RAD IDE's portable Composer
        return find_composer()
    return ""


def php_info(php: str) -> dict:
    """{'version': '8.1.31', 'extensions': [...], 'sqlite': '3.36.0'} of a PHP binary."""
    code = ("echo json_encode(['version' => PHP_VERSION, 'extensions' => array_map('strtolower', "
            "get_loaded_extensions()), 'sqlite' => class_exists('SQLite3') ? SQLite3::version()['versionString'] "
            ": (extension_loaded('pdo_sqlite') ? (new PDO('sqlite::memory:'))->query('select sqlite_version()')"
            "->fetchColumn() : '')]);")
    try:
        out = subprocess.run([php, "-r", code], capture_output=True, text=True, timeout=30,
                             creationflags=_NO_WINDOW).stdout
        return json.loads(out.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        return {}


def _internet_ok(timeout: float = 6.0) -> bool:
    try:
        req = urllib.request.Request("https://wordpress.org/", method="HEAD", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:  # noqa: BLE001
        return False


def check(template_id: str, network: bool = False) -> tuple[bool, str]:
    """Can the template be created here? (ok, message). *network* also probes the internet."""
    t = get_template(template_id)
    missing = []
    php = ""
    for need in t.needs:
        if need in ("php", "composer", "node", "npm"):
            path = find_tool(need)
            if not path:
                missing.append(need)
            elif need == "php":
                php = path
        elif need == "pdo_sqlite":
            php = php or find_tool("php")
            if php and "pdo_sqlite" not in php_info(php).get("extensions", []):
                return False, ("The PHP extension pdo_sqlite is not enabled: add 'extension=pdo_sqlite' to "
                               "php.ini (the template still works once it is enabled).")
        elif need == "internet" and network and not _internet_ok():
            return False, "No internet connection: this template downloads files."
    if missing:
        hints = {"php": "PHP 8 (https://windows.php.net/download)",
                 "composer": "Composer (https://getcomposer.org/download/)",
                 "node": "Node.js (https://nodejs.org)", "npm": "npm (comes with Node.js)"}
        return False, "Not installed: " + ", ".join(hints.get(m, m) for m in missing)
    return True, "Ready." if "internet" not in t.needs else "Ready (downloads files from the internet)."


# ===================================================================== create
def display_name(name: str) -> str:
    """The project name as it may appear inside PHP / JS string literals and HTML."""
    clean = re.sub(r"[^\w \-.]", "", name, flags=re.UNICODE).strip()
    return clean or "My Site"


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "my-site"


TEXT_EXTS = {".php", ".html", ".htm", ".css", ".js", ".json", ".md", ".txt", ".htaccess", ".gitignore",
             ".env", ".xml", ".svg", ".ini"}


def _copy_template(src: Path, dst: Path, name: str) -> list[Path]:
    subs = {"{{APP_NAME}}": display_name(name), "{{APP_SLUG}}": slug(name)}
    written = []
    for path in sorted(src.rglob("*")):
        rel = path.relative_to(src)
        if "__pycache__" in rel.parts:
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        ext = path.suffix.lower() or path.name.lower()
        if ext in TEXT_EXTS and not path.name.endswith((".min.css", ".min.js")):
            text = path.read_text(encoding="utf-8")
            for k, v in subs.items():
                text = text.replace(k, v)
            target.write_text(text, encoding="utf-8", newline="\n")
        else:
            shutil.copyfile(path, target)
        written.append(target)
    return written


def web_block(t: WebTemplate) -> dict:
    """The "web" block of project.radproj for a template (CONTRACTS 8.1)."""
    block = {"root": t.root, "start": t.start, "port": 0, "live_reload": True, "template": t.id}
    if t.builder == "composer-laravel":
        block.update(framework="laravel", php="auto")
    return block


def write_project_file(folder: Path, name: str, t: WebTemplate, **extra) -> Path:
    """project.radproj of a website project (the same format as web_site.project.create_website)."""
    data = {"name": name, "language": t.language, "forms": [], "startup": "", "modules": [],
            "kind": "website", "web": web_block(t)}
    if extra.get("web_php"):                         # Laravel: the PHP series the project was created with
        data["web"]["php"] = extra.pop("web_php")
    data.update(extra)
    path = folder / PROJECT_FILE
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def _check_folder(folder: Path) -> None:
    if folder.exists():
        if not folder.is_dir():
            raise FileExistsError(f"{folder} is a file")
        if any(folder.iterdir()):
            raise FileExistsError(f"The folder {folder} is not empty - choose a new project name or location.")


def create(template_id: str, folder: Path | str, name: str | None = None, log: Log | None = None, *,
           install: bool = True, cache_dir: Path | str | None = None, timeout: int = 1800) -> Path:
    """Create the website project *name* from *template_id* in *folder* (new or empty) and
    return the folder. *log* receives progress lines. *install* runs npm install for Node
    templates. Raises on errors (the message says what is missing)."""
    t = get_template(template_id)
    folder = Path(folder).resolve()
    name = name or folder.name
    log = log or (lambda _s: None)
    _check_folder(folder)
    extra = build_files(t.id, folder, name, log, install=install, cache_dir=cache_dir, timeout=timeout)
    write_project_file(folder, name, t, **extra)
    log(f"[gallery] project '{name}' created ({t.title}).")
    return folder


def build_files(template_id: str, folder: Path, name: str, log: Log | None = None, *, install: bool = True,
                cache_dir: Path | str | None = None, timeout: int = 1800) -> dict:
    """Write the template's files into *folder* (no project.radproj). Returns extra
    project.radproj keys (e.g. {"wordpress": {...}})."""
    t = get_template(template_id)
    folder = Path(folder).resolve()
    log = log or (lambda _s: None)
    if t.builder == "composer-laravel":
        return _create_laravel(t, folder, name, log, timeout)
    elif t.builder == "wordpress":
        return _create_wordpress(t, folder, name, log, Path(cache_dir) if cache_dir else default_cache_dir(),
                                 timeout)
    else:
        src = TEMPLATE_DIR / t.source
        if not src.is_dir():
            raise FileNotFoundError(f"template files missing: {src}")
        folder.mkdir(parents=True, exist_ok=True)
        files = _copy_template(src, folder, name)
        log(f"[gallery] {t.title}: {len(files)} files written to {folder}")
        if t.language == "node-web" and install:
            npm = find_tool("npm")
            if npm:
                log("[gallery] npm install ...")
                try:
                    run_tool([npm, "install", "--no-audit", "--no-fund"], folder, log, timeout)
                except Exception as e:  # noqa: BLE001 - the project is usable; dependencies can be installed later
                    log(f"[gallery] npm install failed ({e}) - run 'npm install' in the project folder.")
            else:
                log("[gallery] npm not found - run 'npm install' in the project folder later.")
    return {}


# ===================================================================== helpers
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def run_tool(argv: list[str], cwd: Path, log: Log, timeout: int = 1800, env: dict | None = None) -> str:
    """Run a command, stream its output to *log*, raise RuntimeError on a non-zero exit."""
    log("$ " + " ".join(argv))
    proc = subprocess.Popen(argv, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                            env={**os.environ, **(env or {})}, creationflags=_NO_WINDOW)
    lines = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            lines.append(line)
            if line:
                log("  " + line)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError(f"{Path(argv[0]).name} did not finish in {timeout} s")
    if proc.returncode:
        tail = "\n".join(lines[-15:])
        raise RuntimeError(f"{Path(argv[0]).name} failed (exit code {proc.returncode}):\n{tail}")
    return "\n".join(lines)


def default_cache_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".cache")
    return Path(base) / "RADIDE" / "downloads"


def download(url: str, dest: Path, log: Log, reuse: bool = True, timeout: int = 120) -> Path:
    """Download *url* to *dest* (kept as a cache: reused when it exists and is a valid zip)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if reuse and dest.exists() and dest.stat().st_size > 0:
        if dest.suffix != ".zip" or zipfile.is_zipfile(dest):
            log(f"[gallery] using cached {dest.name}")
            return dest
    log(f"[gallery] downloading {url}")
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(part, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done, step = 0, 0
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total and done * 10 // total > step:
                step = done * 10 // total
                log(f"[gallery]   {done * 100 // total}% of {total // 1024} KB")
    if dest.suffix == ".zip" and not zipfile.is_zipfile(part):
        part.unlink(missing_ok=True)
        raise RuntimeError(f"the download from {url} is not a zip file")
    part.replace(dest)
    return dest


def _safe_extract(zf: zipfile.ZipFile, dest: Path, strip: str = "") -> int:
    """Extract members (optionally below the prefix *strip*) refusing paths outside *dest*."""
    dest = dest.resolve()
    n = 0
    for info in zf.infolist():
        name = info.filename
        if strip:
            if not name.startswith(strip):
                continue
            name = name[len(strip):]
        if not name:
            continue
        target = (dest / name).resolve()
        if target != dest and dest not in target.parents:
            raise RuntimeError(f"unsafe path in archive: {info.filename}")
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out)
        n += 1
    return n


def _deny_htaccess(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ".htaccess").write_text(
        "<IfModule mod_authz_core.c>\n    Require all denied\n</IfModule>\n"
        "<IfModule !mod_authz_core.c>\n    Deny from all\n</IfModule>\n", encoding="utf-8")


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


# ===================================================================== Laravel
def _create_laravel(t: WebTemplate, folder: Path, name: str, log: Log, timeout: int) -> dict:
    """Laravel App / API (radide/web_site/frameworks/laravel.py does the work)."""
    from .frameworks.laravel import create_laravel
    if folder.exists() and not any(folder.iterdir()):
        folder.rmdir()                         # empty (checked) - composer wants to create it
    web = create_laravel(folder, display_name(name), log=log, kind="api" if t.id == "laravel-api" else "app",
                         timeout=timeout)
    return {"web_php": web.get("php", "auto")}


def configure_laravel_env(text: str, app_name: str) -> str:
    """Switch a Laravel .env to SQLite (database/database.sqlite) and set APP_NAME."""
    out = []
    for line in text.splitlines():
        key = line.split("=", 1)[0].strip().lstrip("# ").strip()
        if key == "APP_NAME":
            line = f'APP_NAME="{app_name}"'
        elif key == "DB_CONNECTION":
            line = "DB_CONNECTION=sqlite"
        elif key in ("DB_HOST", "DB_PORT", "DB_DATABASE", "DB_USERNAME", "DB_PASSWORD") and not line.startswith("#"):
            line = "# " + line                # sqlite uses database/database.sqlite by default
        out.append(line)
    if not any(ln.startswith("DB_CONNECTION=") for ln in out):
        out.append("DB_CONNECTION=sqlite")
    return "\n".join(out) + "\n"


# ===================================================================== WordPress
def _create_wordpress(t: WebTemplate, folder: Path, name: str, log: Log, cache: Path, timeout: int) -> None:
    php = find_tool("php")
    if not php:
        raise RuntimeError("PHP is not installed (https://windows.php.net/download).")
    info = php_info(php)
    if "pdo_sqlite" not in info.get("extensions", []):
        raise RuntimeError("WordPress on SQLite needs the PHP extension pdo_sqlite: add 'extension=pdo_sqlite' "
                           "to php.ini.")
    sqlite_version = info.get("sqlite", "") or "0"
    plugin_version = ("latest-stable" if _version_tuple(sqlite_version) >= SQLITE_PLUGIN_MIN_SQLITE
                      else SQLITE_PLUGIN_LEGACY)
    try:
        wp_zip = download(WORDPRESS_ZIP, cache / "wordpress-latest.zip", log, timeout=timeout)
        plugin_zip = download(SQLITE_PLUGIN_ZIP.format(version=plugin_version),
                              cache / f"sqlite-database-integration-{plugin_version}.zip", log, timeout=timeout)
    except OSError as e:
        raise RuntimeError(f"WordPress could not be downloaded ({e}). Check the internet connection and try "
                           "again.") from e
    root = folder / t.root
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wp_zip) as zf:
        n = _safe_extract(zf, root, strip="wordpress/")
    log(f"[gallery] WordPress: {n} files extracted to {root}")
    plugins = root / "wp-content" / "plugins"
    with zipfile.ZipFile(plugin_zip) as zf:
        _safe_extract(zf, plugins)
    plugin_dir = plugins / "sqlite-database-integration"
    plugin_ver = _plugin_version(plugin_dir)
    log(f"[gallery] SQLite Database Integration {plugin_ver} installed (SQLite library {sqlite_version})")
    dropin = (plugin_dir / "db.copy").read_text(encoding="utf-8")
    # an empty implementation path makes the drop-in use wp-content/plugins/sqlite-database-integration,
    # so the site keeps working when the folder is moved or published
    dropin = dropin.replace("{SQLITE_IMPLEMENTATION_FOLDER_PATH}", "").replace(
        "{SQLITE_PLUGIN}", "sqlite-database-integration/load.php")
    (root / "wp-content" / "db.php").write_text(dropin, encoding="utf-8")
    db_dir = folder / "database"                 # outside the web root
    _deny_htaccess(db_dir)
    (root / "wp-config.php").write_text(
        wordpress_config((root / "wp-config-sample.php").read_text(encoding="utf-8"), plugin_ver),
        encoding="utf-8")
    extra = {"wordpress": {"sqlite_plugin": plugin_ver}}
    (folder / "README.md").write_text(
        f"# {display_name(name)} (WordPress)\n\nCreated by the RAD IDE App Gallery: WordPress from wordpress.org "
        f"with the SQLite Database Integration plugin {plugin_ver} (no MySQL needed).\n\n"
        "- Web root: `wordpress/`. Press F5 and finish the 5-minute install (site title, admin user).\n"
        "- The database is `database/wordpress.sqlite`, outside the web root.\n"
        "- Pretty permalinks need a web server with URL rewriting; with `php -S` keep the default "
        "(\"Plain\") permalinks.\n", encoding="utf-8")
    return extra


def _plugin_version(plugin_dir: Path) -> str:
    try:
        m = re.search(r"^\s*\*?\s*Version:\s*([\w.]+)", (plugin_dir / "load.php").read_text(encoding="utf-8"), re.M)
        return m.group(1) if m else "?"
    except OSError:
        return "?"


def wordpress_config(sample: str, plugin_version: str = "") -> str:
    """wp-config.php from wp-config-sample.php: unique keys/salts and the SQLite database path."""
    alphabet = string.ascii_letters + string.digits + "!@#%^&*()-_[]{}<>~+=,.;:/?|"
    text = sample
    while "put your unique phrase here" in text:
        salt = "".join(secrets.choice(alphabet) for _ in range(64))
        text = text.replace("put your unique phrase here", salt, 1)
    if _version_tuple(plugin_version) >= (3,):
        db = "define( 'DB_PATH', dirname( __DIR__ ) . '/database/wordpress.sqlite' );\n"
    else:
        db = ("define( 'DB_DIR', dirname( __DIR__ ) . '/database/' );\n"
              "define( 'DB_FILE', 'wordpress.sqlite' );\n")
    block = ("/* RAD IDE: SQLite database (SQLite Database Integration plugin, wp-content/db.php).\n"
             " * The file is outside the web root (wordpress/). */\n"
             "define( 'DB_ENGINE', 'sqlite' );\n" + db + "\n")
    marker = "/* That's all, stop editing!"
    if marker in text:
        text = text.replace(marker, block + marker, 1)
    else:
        text = text.replace("/** Absolute path", block + "/** Absolute path", 1)
    return text


# ===================================================================== registration (web_site.project)
# Log used when a template is created through web_site.project.create_website (New Project dialog);
# radide/features/app_gallery.py points it at the Output window.
progress_log: Log = print
ICONS = {"php-empty": "SP_FileIcon", "php-starter": "SP_DirHomeIcon", "php-sqlite-app": "SP_DriveHDIcon",
         "html-bootstrap": "SP_DesktopIcon", "node-express": "SP_DriveNetIcon", "laravel": "SP_ComputerIcon", "laravel-api": "SP_DriveNetIcon",
         "wordpress": "SP_FileDialogDetailedView"}


def is_heavy(t: WebTemplate) -> bool:
    """Slow to create (downloads, composer, npm install) - the UI shows a progress window."""
    return t.builder != "files" or t.language == "node-web"


def site_creator(t: WebTemplate) -> Callable[[Path, str], dict]:
    """create(folder, name) -> web overrides, in the shape web_site.project.SiteTemplate wants."""
    def create_site(folder: Path, name: str) -> dict:
        extra = build_files(t.id, Path(folder), name, lambda s: progress_log(s))
        web = {k: v for k, v in web_block(t).items() if k in ("root", "start", "framework", "php")}
        if extra.get("web_php"):                    # Laravel: the PHP series the project was created with
            web["php"] = extra.pop("web_php")
        if extra:
            web["gallery"] = extra
        return web
    return create_site


def register_all() -> None:
    """Register every template with web_site.project (replaces web-core's defaults of the same id)."""
    try:
        from .project import SiteTemplate, register_template
    except Exception:  # noqa: BLE001 - web-core not available: gallery.create() still works
        return
    order: dict[str, int] = {}
    for t in TEMPLATES:
        order[t.language] = order.get(t.language, 0) + 10
        register_template(SiteTemplate(
            t.id, t.title, t.description, (t.language,), site_creator(t), order=order[t.language],
            icon=ICONS.get(t.id, "SP_DriveNetIcon"),
            extra={"category": t.category, "needs": list(t.needs), "heavy": is_heavy(t),
                   "root": t.root, "start": t.start, "gallery": True}))


register_all()

__all__ = ["TEMPLATES", "WebTemplate", "get_template", "templates_for", "new_project_entries", "check", "create",
           "build_files", "find_tool", "php_info", "configure_laravel_env", "wordpress_config",
           "write_project_file", "register_all", "site_creator"]
