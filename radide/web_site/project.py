"""Web Site projects (docs/CONTRACTS.md section 8.1) - helpers without any UI.

A website project is a normal ``project.radproj`` with ``"kind": "website"``, the id of one of the
web plugins as ``"language"`` (``php-web``, ``static-web``, ``node-web``) and a ``"web"`` block::

    {"name": "MySite", "language": "php-web", "kind": "website", "forms": [], "modules": [],
     "web": {"root": ".", "start": "index.php", "port": 0, "live_reload": true}}

It has no forms: its files are the whole folder tree.

API used by the other web agents (design view, databases, publish, reports, gallery)::

    is_website(project) -> bool
    web_config(project) -> dict            # "root", "start", "port", "live_reload" (+ any extra keys)
    set_web_config(project, **changes)      # update + save project.radproj
    site_root(project) -> Path              # folder served as "/" (absolute)
    start_page(project) -> str              # start file relative to the root ("index.php")
    list_files(project) -> list[Path]       # absolute paths of the site's files (no .git/node_modules...)
    url_path_for(project, file) -> str|None # "/css/site.css" for <root>/css/site.css
    file_for_url(project, "/a/b") -> Path|None
    create_website(folder, name, plugin_id, template_id="") -> Project
    templates_for(plugin_id) -> list[SiteTemplate];  register_template(SiteTemplate(...))
    file_plugin(path, project=None) -> LanguagePlugin   # editor/highlighter plugin for any file

Templates: ``register_template(SiteTemplate(id, title, description, plugin_ids, create))`` where
``create(folder: Path, name: str) -> dict | None`` writes the files and may return overrides for the
``web`` block (e.g. ``{"start": "default.php"}``). ``radide.web_site.gallery`` (App Gallery) is
imported by ``templates_for`` when it exists, so its module-level register_template calls are seen.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import unquote

from ..languages.base import LanguagePlugin, RunSpec
from ..model import Project

WEBSITE = "website"
WEB_PLUGIN_IDS = ("php-web", "static-web", "node-web")
DEFAULT_WEB = {"root": ".", "start": "", "port": 0, "live_reload": True}

# never shown / never listed
HIDDEN_DIRS = {".git", ".svn", ".hg", "__pycache__", ".radide", ".radide_backup", ".radide_deleted", ".idea",
               ".vscode"}
HIDDEN_FILES = {Project.FILE, "Thumbs.db", ".DS_Store", "desktop.ini"}
# shown in the explorer but filled only when expanded; not listed by list_files(include_heavy=False)
HEAVY_DIRS = {"node_modules", "vendor", "bower_components", "dist", "build", ".next", ".cache"}
INDEX_FILES = ("index.php", "index.html", "index.htm", "default.php", "default.html", "default.htm")

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg"}
BINARY_EXT = IMAGE_EXT - {".svg"} | {".woff", ".woff2", ".ttf", ".otf", ".eot", ".zip", ".gz", ".pdf", ".mp3",
                                     ".mp4", ".webm", ".ogg", ".wav", ".sqlite", ".db", ".sqlite3", ".exe",
                                     ".dll", ".phar", ".jar", ".7z"}
DESIGNABLE_EXT = {".html", ".htm", ".php", ".phtml"}


# ============================================================================ project helpers
def is_website(project) -> bool:
    if project is None:
        return False
    if str(getattr(project, "kind", "") or "").lower() == WEBSITE:
        return True
    extra = getattr(project, "extra", None) or {}
    return str(extra.get("kind", "")).lower() == WEBSITE or getattr(project, "language", "") in WEB_PLUGIN_IDS


def web_config(project) -> dict:
    """The project's "web" block merged over the defaults (start page filled in)."""
    extra = getattr(project, "extra", None) or {}
    raw = extra.get("web") if isinstance(extra.get("web"), dict) else {}
    cfg = dict(DEFAULT_WEB)
    cfg.update(raw)
    try:
        cfg["port"] = int(cfg.get("port") or 0)
    except (TypeError, ValueError):
        cfg["port"] = 0
    cfg["root"] = str(cfg.get("root") or ".")
    if not cfg.get("start"):
        cfg["start"] = _guess_start(Path(project.folder) / cfg["root"], getattr(project, "language", ""))
    return cfg


def set_web_config(project, save: bool = True, **changes) -> dict:
    """Update the "web" block (only the given keys) and save project.radproj."""
    extra = project.extra if isinstance(getattr(project, "extra", None), dict) else {}
    web = dict(extra.get("web") or {})
    web.update(changes)
    extra["web"] = web
    project.extra = extra
    project.kind = WEBSITE
    if save:
        project.save()
    return web_config(project)


def site_root(project) -> Path:
    root = Path(project.folder) / web_config(project)["root"]
    return root.resolve()


def start_page(project) -> str:
    return str(web_config(project)["start"]).replace("\\", "/").lstrip("/")


def _guess_start(root: Path, language: str = "") -> str:
    if language == "node-web":
        for n in ("server.js", "app.js", "index.js", "main.js"):
            if (root / n).is_file():
                return n
        pkg = root / "package.json"
        try:
            main = json.loads(pkg.read_text(encoding="utf-8")).get("main") if pkg.is_file() else None
            if main:
                return str(main)
        except (OSError, ValueError):
            pass
        return "server.js"
    for n in INDEX_FILES:
        if (root / n).is_file():
            return n
    return "index.php" if language == "php-web" else "index.html"


def visible(path: Path) -> bool:
    """Shown in the Solution Explorer?"""
    name = path.name
    if path.is_dir():
        return name not in HIDDEN_DIRS
    return name not in HIDDEN_FILES and not name.endswith((".pyc", "~"))


def list_files(project, include_heavy: bool = False) -> list[Path]:
    """Every file of the website (absolute paths, sorted), without VCS/IDE folders and - unless
    *include_heavy* - without node_modules / vendor / build output."""
    folder = Path(project.folder).resolve()
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if d not in HIDDEN_DIRS and
                             (include_heavy or d not in HEAVY_DIRS))
        for f in sorted(filenames, key=str.lower):
            p = Path(dirpath) / f
            if f in HIDDEN_FILES or f.endswith(".pyc"):
                continue
            out.append(p)
    return out


def children(folder: Path) -> list[Path]:
    """Visible entries of one folder: sub-folders first, then files (case-insensitive)."""
    try:
        entries = [p for p in Path(folder).iterdir() if visible(p)]
    except OSError:
        return []
    return sorted(entries, key=lambda p: (not p.is_dir(), p.name.lower()))


def rel(project, path) -> str:
    """Path relative to the project folder with forward slashes ("" when outside)."""
    try:
        return Path(path).resolve().relative_to(Path(project.folder).resolve()).as_posix()
    except ValueError:
        return ""


def url_path_for(project, file) -> str | None:
    """URL path of a file of the site ("/" for the root index); None when outside the root."""
    root = site_root(project)
    p = Path(file)
    if not p.is_absolute():
        p = Path(project.folder) / p
    try:
        r = p.resolve().relative_to(root).as_posix()
    except ValueError:
        return None
    if r == ".":
        r = ""
    from urllib.parse import quote
    if p.is_dir():
        return "/" + (quote(r) + "/" if r else "")
    return "/" + quote(r)


def file_for_url(project, url_path: str) -> Path | None:
    """The file that serves *url_path* (directories -> their index file); None when not found."""
    root = site_root(project)
    path = unquote(url_path.split("?", 1)[0].split("#", 1)[0]).lstrip("/")
    p = (root / path).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return None
    if p.is_dir():
        for n in INDEX_FILES:
            if (p / n).is_file():
                return p / n
        return None
    return p if p.is_file() else None


# ============================================================================ templates
@dataclass
class SiteTemplate:
    id: str
    title: str
    description: str
    plugin_ids: tuple[str, ...]
    create: Callable[[Path, str], dict | None]
    order: int = 100
    icon: str = "SP_DriveNetIcon"
    extra: dict = field(default_factory=dict)


_TEMPLATES: dict[str, SiteTemplate] = {}
_gallery_loaded = False


def register_template(t: SiteTemplate) -> None:
    """Add (or replace - same id) a website template."""
    _TEMPLATES[t.id] = t


def _load_gallery() -> None:
    global _gallery_loaded
    if _gallery_loaded:
        return
    _gallery_loaded = True
    try:
        import importlib.util
        if importlib.util.find_spec(f"{__package__}.gallery") is not None:
            importlib.import_module(f"{__package__}.gallery")
    except Exception:  # noqa: BLE001 - the gallery is optional
        import traceback
        traceback.print_exc()


def templates_for(plugin_id: str) -> list[SiteTemplate]:
    _load_gallery()
    return sorted((t for t in _TEMPLATES.values() if plugin_id in t.plugin_ids), key=lambda t: (t.order, t.title))


def get_template(template_id: str) -> SiteTemplate | None:
    _load_gallery()
    return _TEMPLATES.get(template_id)


def create_website(folder: Path, name: str, plugin_id: str, template_id: str = "") -> Project:
    """Create a website project in *folder* from a template (default: the plugin's first one)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    tpl = get_template(template_id) if template_id else None
    if tpl is None or plugin_id not in tpl.plugin_ids:
        ts = templates_for(plugin_id)
        tpl = ts[0] if ts else None
    web = {}
    if tpl is not None:
        web = tpl.create(folder, name) or {}
    cfg = dict(DEFAULT_WEB)
    cfg.update(web)
    if not cfg.get("start"):
        cfg["start"] = _guess_start(folder / cfg.get("root", "."), plugin_id)
    project = Project(folder, name, plugin_id, [], "", [], {}, WEBSITE, [], {}, {"web": cfg})
    if tpl is not None:
        project.extra["web"]["template"] = tpl.id
    project.save()
    return Project.load(folder)


def _write(folder: Path, files: dict[str, str]) -> None:
    for relname, text in files.items():
        p = folder / relname
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(text, encoding="utf-8")


SITE_CSS = """/* Site styles */
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; color: #222; background: #f5f6f8; }
header { background: #1f3d7a; color: #fff; padding: 18px 32px; }
header h1 { margin: 0; font-size: 24px; }
nav a { color: #cfe0ff; margin-right: 16px; text-decoration: none; }
main { max-width: 900px; margin: 24px auto; background: #fff; padding: 24px 32px; border-radius: 8px;
       box-shadow: 0 1px 3px rgba(0,0,0,.12); }
footer { text-align: center; color: #888; font-size: 12px; padding: 16px; }
"""

SITE_JS = """// Site scripts
document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('clock');
    if (el) { setInterval(function () { el.textContent = new Date().toLocaleTimeString(); }, 1000); }
});
"""


def _php_empty(folder: Path, name: str) -> dict:
    _write(folder, {
        "index.php": f"""<?php
$title = 'Welcome to {name}';
$now = date('Y-m-d H:i:s');
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title><?= htmlspecialchars($title) ?></title>
    <meta name="description" content="{name} - a PHP web site made with RAD IDE">
    <link rel="stylesheet" href="css/site.css">
</head>
<body>
<header>
    <h1><?= htmlspecialchars($title) ?></h1>
    <nav><a href="index.php">Home</a><a href="about.php">About</a></nav>
</header>
<main>
    <p>This page was generated by PHP <?= PHP_VERSION ?> at <strong><?= $now ?></strong>.</p>
    <p>Browser time: <span id="clock"></span></p>
    <ul>
        <?php for ($i = 1; $i <= 3; $i++): ?>
            <li>Item <?= $i ?></li>
        <?php endfor; ?>
    </ul>
</main>
<footer>&copy; <?= date('Y') ?> {name}</footer>
<script src="js/site.js"></script>
</body>
</html>
""",
        "about.php": f"""<?php $title = 'About {name}'; ?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title><?= htmlspecialchars($title) ?></title>
    <link rel="stylesheet" href="css/site.css">
</head>
<body>
<header><h1><?= htmlspecialchars($title) ?></h1><nav><a href="index.php">Home</a></nav></header>
<main><p>Edit <code>about.php</code> and save: the preview reloads by itself.</p></main>
</body>
</html>
""",
        "css/site.css": SITE_CSS,
        "js/site.js": SITE_JS,
    })
    return {"start": "index.php"}


def _static_empty(folder: Path, name: str) -> dict:
    _write(folder, {
        "index.html": f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{name}</title>
    <meta name="description" content="{name} - a web site made with RAD IDE">
    <link rel="stylesheet" href="css/site.css">
</head>
<body>
<header>
    <h1>{name}</h1>
    <nav><a href="index.html">Home</a><a href="about.html">About</a></nav>
</header>
<main>
    <p>Welcome! Edit <code>index.html</code> and save: the preview reloads by itself.</p>
    <p>Time: <span id="clock"></span></p>
</main>
<footer>{name}</footer>
<script src="js/site.js"></script>
</body>
</html>
""",
        "about.html": f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>About {name}</title><link rel="stylesheet" href="css/site.css"></head>
<body><header><h1>About</h1><nav><a href="index.html">Home</a></nav></header>
<main><p>An HTML / CSS / JavaScript site.</p></main></body>
</html>
""",
        "css/site.css": SITE_CSS,
        "js/site.js": SITE_JS,
    })
    return {"start": "index.html"}


NODE_PUBLIC_INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{name}</title>
    <link rel="stylesheet" href="/css/site.css">
</head>
<body>
<header><h1>{name}</h1></header>
<main>
    <p>Served by Node.js. Server time: <span id="time">...</span></p>
</main>
<script>
fetch('/api/time').then(r => r.json()).then(d => document.getElementById('time').textContent = d.time);
</script>
</body>
</html>
"""


def _node_empty(folder: Path, name: str) -> dict:
    _write(folder, {
        "server.js": f"""// {name} - a Node.js web site without dependencies (http module).
// The IDE gives the port in process.env.PORT.
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 3000;
const PUBLIC = path.join(__dirname, 'public');
const TYPES = {{ '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript',
                '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' }};

const server = http.createServer((req, res) => {{
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/api/time') {{
        res.writeHead(200, {{ 'Content-Type': 'application/json' }});
        return res.end(JSON.stringify({{ time: new Date().toISOString() }}));
    }}
    let file = path.normalize(path.join(PUBLIC, decodeURIComponent(url.pathname)));
    if (!file.startsWith(PUBLIC)) {{ res.writeHead(403); return res.end('Forbidden'); }}
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
    fs.readFile(file, (err, data) => {{
        if (err) {{ res.writeHead(404, {{ 'Content-Type': 'text/plain' }}); return res.end('Not found'); }}
        res.writeHead(200, {{ 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' }});
        res.end(data);
    }});
}});

server.listen(PORT, () => console.log(`{name} listening on port ${{PORT}}`));
""",
        "package.json": json.dumps({"name": name.lower(), "version": "1.0.0", "private": True,
                                    "main": "server.js", "scripts": {"start": "node server.js"}}, indent=2) + "\n",
        "public/index.html": NODE_PUBLIC_INDEX.replace("{name}", name),
        "public/css/site.css": SITE_CSS,
    })
    return {"start": "server.js"}


def _node_express(folder: Path, name: str) -> dict:
    _write(folder, {
        "app.js": f"""// {name} - Express web site. Packages are installed (npm install) on the first run.
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.get('/api/time', (req, res) => res.json({{ time: new Date().toISOString() }}));

app.listen(PORT, () => console.log(`{name} listening on port ${{PORT}}`));
""",
        "package.json": json.dumps({"name": name.lower(), "version": "1.0.0", "private": True, "main": "app.js",
                                    "scripts": {"start": "node app.js"},
                                    "dependencies": {"express": "^4.21.2"}}, indent=2) + "\n",
        "public/index.html": NODE_PUBLIC_INDEX.replace("{name}", name),
        "public/css/site.css": SITE_CSS,
        ".gitignore": "node_modules/\n",
    })
    return {"start": "app.js"}


register_template(SiteTemplate("php-empty", "PHP Empty Site",
                               "A PHP site with index.php, about.php, css/site.css and js/site.js. "
                               "Runs on PHP's built-in web server with live preview.", ("php-web",), _php_empty, 10))
register_template(SiteTemplate("static-empty", "HTML Empty Site",
                               "Static HTML / CSS / JavaScript pages served by the IDE's web server.",
                               ("static-web",), _static_empty, 10))
register_template(SiteTemplate("node-empty", "Node.js Empty Site",
                               "A Node.js server without packages (http module): static files from public/ and a "
                               "JSON API route.", ("node-web",), _node_empty, 10))
register_template(SiteTemplate("node-express", "Express Site",
                               "An Express application (npm install runs on the first start): static files and "
                               "an /api route.", ("node-web",), _node_express, 20))


def new_file_content(path: Path, project=None) -> str:
    """Starting content of a file created with New File (by extension)."""
    ext = path.suffix.lower()
    title = path.stem.replace("_", " ").replace("-", " ").title()
    css = ""
    if project is not None:
        for c in ("css/site.css", "css/style.css", "style.css"):
            if (site_root(project) / c).is_file():
                css = "/" + c
                break
    link = f'\n    <link rel="stylesheet" href="{css}">' if css else ""
    if ext in (".html", ".htm"):
        return (f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n"
                f"    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
                f"    <title>{title}</title>{link}\n</head>\n<body>\n    <h1>{title}</h1>\n\n</body>\n</html>\n")
    if ext in (".php", ".phtml"):
        return (f"<?php\n$title = '{title}';\n?>\n<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
                f"    <meta charset=\"utf-8\">\n    <title><?= htmlspecialchars($title) ?></title>{link}\n</head>\n"
                f"<body>\n    <h1><?= htmlspecialchars($title) ?></h1>\n\n</body>\n</html>\n")
    if ext == ".css":
        return f"/* {path.name} */\n"
    if ext in (".js", ".mjs", ".cjs"):
        return f"// {path.name}\n"
    if ext == ".json":
        return "{\n}\n"
    if ext in (".md",):
        return f"# {title}\n"
    if ext == ".xml":
        return '<?xml version="1.0" encoding="utf-8"?>\n'
    return ""


# ============================================================================ plugins
class WebSitePlugin(LanguagePlugin):
    """Base class of the website plugins (php-web, static-web, node-web): no forms, a dev server."""
    project_kind = WEBSITE
    web_kind = "static"               # "php" | "static" | "node"
    needs_interpreter = False
    supports_debug = False
    default_template = ""

    # --- forms are not used by website projects
    def generate_designer(self, form, user_code: str) -> str:
        return ""

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def find_handler(self, code: str, name: str) -> int:
        return -1

    def add_handler(self, code: str, name: str, form, args=None):
        return code, 0

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        raise RuntimeError("a web site runs on its development server (Debug > Start)")

    # --- dev server
    def backend(self, server) -> dict | None:
        """How DevServer runs the site: None = the IDE serves the files itself, else
        {"argv": [...], "env": {...}, "cwd": Path, "prepare": [[argv], ...]} listening on server.backend_port."""
        return None

    def templates(self) -> list[SiteTemplate]:
        return templates_for(self.id)

    def create_site(self, folder: Path, name: str, template_id: str = "") -> Project:
        return create_website(folder, name, self.id, template_id or self.default_template)


class TextPlugin(LanguagePlugin):
    """Editor-only plugin for files no language plugin knows (.css, .html, .json, .txt ...)."""

    def __init__(self, ext: str):
        self.ext = ext.lower()
        self.id = "text-" + (self.ext.lstrip(".") or "plain")
        self.display_name = (self.ext.lstrip(".").upper() or "Text") + " file"
        self.code_ext = self.ext
        self.keywords, self.builtins = [], []
        self.line_comments, self.block_comment = [], None
        self.string_quotes = ['"', "'"]
        if self.ext in (".css", ".scss", ".less"):
            self.block_comment = ("/*", "*/")
            if self.ext != ".css":
                self.line_comments = ["//"]
            self.keywords = ["important", "media", "import", "keyframes", "font-face", "supports", "root"]
        elif self.ext in (".html", ".htm", ".xml", ".svg", ".vue"):
            self.block_comment = ("<!--", "-->")
        elif self.ext in (".json",):
            self.keywords = ["true", "false", "null"]
            self.string_quotes = ['"']
        elif self.ext in (".ini", ".env", ".conf", ".htaccess", ".sh", ".yml", ".yaml", ".toml"):
            self.line_comments = ["#", ";"] if self.ext in (".ini", ".conf") else ["#"]
        elif self.ext in (".sql",):
            self.line_comments = ["--"]
            self.block_comment = ("/*", "*/")
            self.keywords = ("select from where insert into values update set delete create table drop alter "
                             "primary key not null default integer text varchar references join left inner on "
                             "order by group having limit and or as index unique").split()
            self.case_sensitive = False

    def generate_designer(self, form, user_code: str) -> str:
        return ""

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def find_handler(self, code: str, name: str) -> int:
        return -1

    def add_handler(self, code: str, name: str, form, args=None):
        return code, 0


_TEXT_PLUGINS: dict[str, TextPlugin] = {}
_TEXT_EXT = {".html", ".htm", ".css", ".scss", ".less", ".json", ".xml", ".svg", ".txt", ".md", ".ini", ".env",
             ".htaccess", ".yml", ".yaml", ".toml", ".sql", ".csv", ".vue", ".conf", ".map", ".lock", ""}


def text_plugin(ext: str) -> TextPlugin:
    ext = ext.lower()
    if ext not in _TEXT_PLUGINS:
        _TEXT_PLUGINS[ext] = TextPlugin(ext)
    return _TEXT_PLUGINS[ext]


def file_plugin(path, project=None) -> LanguagePlugin:
    """Plugin for editing *path*: PHP files use php-web in websites, .js the project's JS plugin, other
    known code files their language, everything else a TextPlugin (by extension)."""
    from ..languages import get_plugin, plugin_for_file
    p = Path(path)
    ext = p.suffix.lower() if p.suffix else (p.name.lower() if p.name.startswith(".") else "")
    if ext in _TEXT_EXT:
        return text_plugin(ext)
    lang = getattr(project, "language", "") if project is not None else ""
    if ext in (".php", ".phtml", ".inc"):
        try:
            return get_plugin("php-web" if (is_website(project) or project is None) else (lang or "php"))
        except KeyError:
            pass
    found = plugin_for_file(p.name if ext != ".phtml" else p.stem + ".php", lang)
    return found if found is not None else text_plugin(ext)


def safe_name(name: str) -> bool:
    """A valid new file/folder name (no path separators, no reserved Windows names)."""
    if not name or name in (".", "..") or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith((" ", ".")):
        return False
    return name.split(".")[0].upper() not in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                                              *(f"LPT{i}" for i in range(1, 10))}


__all__ = ["DESIGNABLE_EXT", "HEAVY_DIRS", "HIDDEN_DIRS", "IMAGE_EXT", "SiteTemplate", "TextPlugin", "WEBSITE",
           "WEB_PLUGIN_IDS", "WebSitePlugin", "children", "create_website", "file_for_url", "file_plugin",
           "get_template", "is_website", "list_files", "new_file_content", "register_template", "rel",
           "safe_name", "set_web_config", "site_root", "start_page", "templates_for", "url_path_for", "visible",
           "web_config"]
