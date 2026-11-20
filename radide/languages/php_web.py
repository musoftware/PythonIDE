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
    names = [n for n in WANTED_EXT if n not in have and (ext_dir / f"php_{n}.dll").exists()]
    if not names:
        return []
    bad = _broken_ext(php, str(ext_dir), tuple(names))
    args = []
    for name in names:
        if name not in bad:
            args += ["-d", f"extension={name}"]
    if args:
        args = ["-d", f"extension_dir={ext_dir}"] + args
    return args


_BROKEN: dict[tuple, set[str]] = {}


def _broken_ext(php: str, ext_dir: str, names: tuple) -> set[str]:
    """Extensions whose DLL does not load in this PHP (an ext/ folder of another PHP version - "Unable to
    initialize module"); probed once per PHP, so the warning never reaches the pages or the tools' output."""
    key = (php, names)
    if key not in _BROKEN:
        argv = [php, "-d", f"extension_dir={ext_dir}"]
        for n in names:
            argv += ["-d", f"extension={n}"]
        try:
            p = subprocess.run(argv + ["-r", "echo 1;"], capture_output=True, text=True, timeout=20,
                               creationflags=NO_WINDOW)
            import re
            _BROKEN[key] = set(re.findall(r"PHP Startup: (?:Unable to load dynamic library '?(?:php_)?)?(\w+?)"
                                          r"(?:\.dll)?'?:? (?:Unable to initialize module|\()",
                                          (p.stdout or "") + (p.stderr or "")))
        except (OSError, subprocess.TimeoutExpired):
            _BROKEN[key] = set()
    return _BROKEN[key]


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
        spec = {"argv": argv, "cwd": server.root, "env": {}, "timeout": 20}
        try:   # PHP frameworks (web_site/frameworks/common.py): router script + framework env (e.g. base URL)
            from ..web_site.frameworks import common as fwc
            fw = fwc.framework_of(server.folder)
            if fw and not router:
                r = fwc.router_for(server.folder, server.root)
                if r:
                    argv.append(r)
            hook = getattr(fwc.framework_module(fw), "backend_spec", None) if fw else None
            if callable(hook):
                spec = hook(server, spec) or spec
        except Exception as e:  # noqa: BLE001 - never lose Run because of a framework helper
            server.log.emit(f"*** PHP framework settings: {e}")
        return spec


PLUGIN = PhpWebPlugin()
