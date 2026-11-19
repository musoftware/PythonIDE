"""PHP Web Site projects (docs/CONTRACTS.md 8.1) - WebMatrix's "PHP site".

The site runs on PHP's built-in web server (``php -S 127.0.0.1:<port> -t <root>``) behind the IDE's
DevServer (request log, live reload). A ``php.ini`` in the project folder is used when it exists;
otherwise missing common extensions (pdo_sqlite, sqlite3, mbstring, openssl, ...) are enabled with
``-d extension=...`` when the PHP installation has them, and errors are shown in the page.
``web.router`` (relative to the root) selects a router script (e.g. Laravel's server.php).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..web_site.project import WebSitePlugin
from .php_bridge import PHP_BUILTINS, PHP_KEYWORDS, PhpBridgePlugin

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
WANTED_EXT = ("pdo_sqlite", "sqlite3", "mbstring", "openssl", "fileinfo", "curl", "intl", "gd", "zip",
              "pdo_mysql", "mysqli")
_MODULES: dict[str, set[str]] = {}


def php_modules(php: str) -> set[str]:
    """Lower-case names of the extensions php has loaded (``php -m``), cached per executable."""
    if php not in _MODULES:
        try:
            out = subprocess.run([php, "-m"], capture_output=True, text=True, timeout=20,
                                 creationflags=NO_WINDOW).stdout
            _MODULES[php] = {ln.strip().lower() for ln in out.splitlines() if ln.strip() and not ln.startswith("[")}
        except (OSError, subprocess.TimeoutExpired):
            _MODULES[php] = set()
    return _MODULES[php]


def extension_args(php: str) -> list[str]:
    """-d options that enable wanted extensions missing from php's configuration (Windows builds)."""
    have = php_modules(php)
    ext_dir = Path(php).parent / "ext"
    if not have or not ext_dir.is_dir():
        return []
    args = []
    for name in WANTED_EXT:
        if name not in have and (ext_dir / f"php_{name}.dll").exists():
            args += ["-d", f"extension={name}"]
    if args:
        args = ["-d", f"extension_dir={ext_dir}"] + args
    return args


class PhpWebPlugin(WebSitePlugin):
    id = "php-web"
    display_name = "PHP Web Site"
    code_ext = ".php"
    web_kind = "php"
    needs_interpreter = True
    default_template = "php-empty"
    interpreter_names = ["php"]
    interpreter_hints = list(PhpBridgePlugin.tool_hints)
    tool_names = ["php"]
    install_hint = PhpBridgePlugin.install_hint
    keywords = PHP_KEYWORDS
    builtins = [b for b in PHP_BUILTINS if not b.startswith("rad")] + """htmlspecialchars header session_start
        isset empty filter_input password_hash password_verify PDO include require""".split()
    case_sensitive = False
    line_comments = ["//", "#"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'"]
    package_manager = PhpBridgePlugin.package_manager

    def tool(self) -> str:
        return self.find_interpreter("")

    def module_template(self, name: str) -> str:
        return f"<?php\n// {name}.php\n\n"

    def backend(self, server) -> dict:
        php = server.interpreter or self.find_interpreter("") or "php"
        cfg = server.config
        argv = [php]
        ini = server.folder / "php.ini"
        if ini.is_file():
            argv += ["-c", str(ini)]
        else:
            argv += extension_args(php) if shutil.which(php) or Path(php).exists() else []
            argv += ["-d", "display_errors=1", "-d", "error_reporting=E_ALL", "-d", "log_errors=0"]
        argv += ["-S", "127.0.0.1:{port}", "-t", str(server.root)]
        router = str(cfg.get("router") or "")
        if router:
            argv.append(str((server.root / router).resolve()))
        return {"argv": argv, "cwd": server.root, "env": {}, "timeout": 20}


PLUGIN = PhpWebPlugin()
