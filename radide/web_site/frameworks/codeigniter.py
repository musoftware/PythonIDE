"""CodeIgniter 4 in RAD IDE (engine - no Qt; the IDE part is ``radide/features/codeigniter_ide.py``).

- **New project**: ``composer create-project codeigniter4/appstarter`` (the latest stable release), ``.env`` from
  the shipped ``env`` file with ``CI_ENVIRONMENT = development``, an encryption key, and the database: SQLite3
  (``writable/database.db``, default) or the IDE's local MariaDB / PostgreSQL server (``radide/web_site/
  dbservers.py``). ``project.radproj``: ``"language": "php-web"``, ``"web": {"root": "public", "framework":
  "codeigniter", "router": "../vendor/codeigniter4/framework/system/rewrite.php"}`` - the same front controller
  + rewrite script ``php spark serve`` uses, behind the IDE's DevServer (Preview, Requests, live reload, Xdebug).
- **Spark**: ``spark_argv`` / ``spark_commands`` (``php spark list``) / ``spark_help`` (arguments and options of a
  command -> the forms of the Spark panel) / ``spark_routes`` (``php spark routes``).
- **IntelliSense read from the project** (re-read when a file of ``app/``, ``.env`` or the SQLite database
  changes): :func:`complete` and :func:`definition` for ``view()`` / ``$this->extend()`` / ``include()`` names,
  ``url_to()`` / ``route_to()`` / ``redirect()->route()`` route names, ``base_url()`` / ``site_url()`` /
  ``redirect()->to()`` paths, ``config()`` classes and their properties, ``lang()`` keys, ``helper()`` names and
  the functions of the loaded helpers, ``service()`` names (``Config\\Services``), ``model()`` classes, model
  fields (migrations + ``$allowedFields`` + the SQLite schema) in query builder calls / arrays / ``$row['...']``,
  validation rules, section names, ``env()`` keys and ``Controller::method`` handlers in ``Routes.php``.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FRAMEWORK = "codeigniter"
PACKAGE = "codeigniter4/appstarter"
SYSTEM = Path("vendor") / "codeigniter4" / "framework" / "system"
ROUTER = "../vendor/codeigniter4/framework/system/rewrite.php"

# Monaco CompletionItemKind values
K_METHOD, K_FUNCTION, K_FIELD, K_VARIABLE, K_CLASS, K_MODULE, K_PROPERTY = 0, 1, 3, 4, 5, 8, 9
K_VALUE, K_CONSTANT, K_ENUM_MEMBER, K_KEYWORD, K_TEXT, K_FILE, K_REFERENCE, K_FOLDER = 13, 14, 16, 17, 18, 20, 21, 23

VALIDATION_RULES = [
    ("required", "The field must not be empty"), ("permit_empty", "Allows an empty value (other rules skipped)"),
    ("if_exist", "Only validate when the key exists"), ("alpha", "Letters only"),
    ("alpha_dash", "Letters, digits, _ and -"), ("alpha_numeric", "Letters and digits"),
    ("alpha_numeric_punct", "Letters, digits, space and ~!#$%&*-_+=|:."),
    ("alpha_numeric_space", "Letters, digits and spaces"), ("alpha_space", "Letters and spaces"),
    ("decimal", "A decimal number"), ("integer", "An integer"), ("numeric", "Numeric characters"),
    ("is_natural", "0, 1, 2, ..."), ("is_natural_no_zero", "1, 2, 3, ..."), ("hex", "Hexadecimal characters"),
    ("string", "A string"), ("valid_email", "An e-mail address"), ("valid_emails", "Comma-separated e-mails"),
    ("valid_url", "A URL"), ("valid_url_strict", "A URL with http(s) scheme"), ("valid_json", "Valid JSON"),
    ("valid_base64", "Base64 text"), ("timezone", "A timezone name"),
    ("min_length[]", "At least N characters"), ("max_length[]", "At most N characters"),
    ("exact_length[]", "Exactly N characters"), ("greater_than[]", "> N"), ("greater_than_equal_to[]", ">= N"),
    ("less_than[]", "< N"), ("less_than_equal_to[]", "<= N"), ("in_list[]", "One of a comma-separated list"),
    ("not_in_list[]", "None of a list"), ("matches[]", "Equal to another field"),
    ("differs[]", "Different from another field"), ("is_unique[]", "Unique in table.field[,ignore_field,value]"),
    ("is_not_unique[]", "Exists in table.field"), ("regex_match[]", "Matches a regular expression"),
    ("required_with[]", "Required when another field is present"),
    ("required_without[]", "Required when another field is missing"), ("field_exists[]", "The key must exist"),
    ("valid_date[]", "A date (optional format)"), ("valid_ip[]", "IP address (ipv4 / ipv6)"),
    ("valid_cc_number[]", "Credit card number of a provider"), ("uploaded[]", "A file was uploaded"),
    ("max_size[]", "File size in KB: field,kb"), ("max_dims[]", "Image size: field,width,height"),
    ("mime_in[]", "File MIME type: field,type,..."), ("ext_in[]", "File extension: field,ext,..."),
    ("is_image[]", "The upload is an image")]

# query-builder / model methods whose first string argument is a column
FIELD_METHODS = ("where", "orWhere", "whereIn", "orWhereIn", "whereNotIn", "orWhereNotIn", "orderBy", "groupBy",
                 "select", "selectMax", "selectMin", "selectAvg", "selectSum", "selectCount", "like", "orLike",
                 "notLike", "orNotLike", "having", "orHaving", "set", "findColumn", "distinct", "whereBetween",
                 "increment", "decrement", "onlyDeleted", "groupStart", "column", "getColumn", "first", "find")
VIEW_CALL = re.compile(r"(?:\bview|->(?:extend|include)|\bview_cell)\s*\(\s*$")
ROUTE_NAME_CALL = re.compile(r"(?:\burl_to|\broute_to|->route)\s*\(\s*$")
PATH_CALL = re.compile(r"(?:\bbase_url|\bsite_url|\banchor|\banchor_popup|->to|\bform_open(?:_multipart)?)\s*\(\s*$")
CONFIG_CALL = re.compile(r"(?:\bconfig|\bsetting|\bsingle_config)\s*\(\s*$")
LANG_CALL = re.compile(r"\blang\s*\(\s*$")
HELPER_CALL = re.compile(r"\bhelper\s*\(\s*(?:\[[^\]]*)?$")
SERVICE_CALL = re.compile(r"\b(?:service|single_service)\s*\(\s*$")
MODEL_CALL = re.compile(r"\bmodel\s*\(\s*$")
SECTION_CALL = re.compile(r"(?:->section|->renderSection|\brenderSection)\s*\(\s*$")
ENV_CALL = re.compile(r"\benv\s*\(\s*$")
FIELD_CALL = re.compile(r"->(" + "|".join(FIELD_METHODS) + r")\s*\(\s*(?:\[\s*)?$")
ARRAY_KEY = re.compile(r"\$(\w+)\s*\[\s*$")
ROUTE_HANDLER = re.compile(r"\$routes->(?:get|post|put|patch|delete|match|add|options|head|cli)\s*\(\s*"
                           r"(?:\[[^\]]*\]\s*,\s*)?['\"][^'\"]*['\"]\s*,\s*$")
ROUTE_VIEW = re.compile(r"\$routes->view\s*\(\s*['\"][^'\"]*['\"]\s*,\s*$")
CONFIG_PROP = re.compile(r"\b(?:config|single_config)\s*\(\s*(?:['\"]([\w\\]+)['\"]|([\w\\]+)::class)\s*\)\s*->\s*(\w*)$")


# ============================================================================ small helpers
def read_text(p) -> str:
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, max(0, index)) + 1


def _php_string(tok: str) -> str:
    """The value of a PHP string literal token ('..' or "..")."""
    body = tok[1:-1]
    if tok[0] == "'":
        return body.replace("\\'", "'").replace("\\\\", "\\")
    return body.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", "\n").replace("\\t", "\t")


TOKEN = re.compile(r"""
    (?P<c>/\*.*?\*/|//[^\n]*|\#(?!\[)[^\n]*)        # comments
  | (?P<s>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")      # strings
  | (?P<a>=>)
  | (?P<o>array\s*\(|\[|\()
  | (?P<x>\]|\))
  | (?P<p>,)
""", re.S | re.X)


def array_keys(text: str, start: int = 0, max_depth: int = 8) -> list[tuple[str, int, str]]:
    """Scan the PHP array literal starting at/after *start*: [(dotted key, offset, string value or "")] for
    every leaf and every nested array key ("a", "a.b", ...). Only literal string keys are reported."""
    out: list[tuple[str, int, str]] = []
    stack: list[str | None] = []
    pending: tuple[str, int] | None = None
    last_str: tuple[str, int] | None = None
    started = False
    for m in TOKEN.finditer(text, start):
        kind = m.lastgroup
        if kind == "c":
            continue
        if kind == "s":
            last_str = (_php_string(m.group()), m.start())
            if pending is not None and started:
                key, off = pending
                out.append((".".join([k for k in stack if k] + [key]), off, last_str[0]))
                pending = None
                last_str = None
            continue
        if kind == "a":
            if last_str is not None:
                pending = last_str
            last_str = None
            continue
        if kind == "o":
            if not started:
                started = True
                stack.append(None)
                continue
            key = None
            if pending is not None:
                key = pending[0]
                out.append((".".join([k for k in stack if k] + [key]), pending[1], ""))
                pending = None
            stack.append(key)
            if len(stack) > max_depth:
                break
            last_str = None
            continue
        if kind == "x":
            if pending is not None and started:
                key, off = pending
                out.append((".".join([k for k in stack if k] + [key]), off, ""))
                pending = None
            if stack:
                stack.pop()
            if started and not stack:
                break
            last_str = None
            continue
        if kind == "p":
            if pending is not None and started:
                key, off = pending
                out.append((".".join([k for k in stack if k] + [key]), off, ""))
                pending = None
            last_str = None
    return out


def list_values(text: str, start: int) -> list[tuple[str, int]]:
    """String elements of the (flat) array literal at/after *start*: [(value, offset)]."""
    out = []
    i = text.find("[", start)
    if i < 0:
        return out
    depth = 0
    for m in TOKEN.finditer(text, i):
        kind = m.lastgroup
        if kind == "o":
            depth += 1
        elif kind == "x":
            depth -= 1
            if depth <= 0:
                break
        elif kind == "s" and depth == 1:
            out.append((_php_string(m.group()), m.start()))
    return out


def _doc_before(text: str, index: int) -> str:
    """First line of the /** docblock */ right before *index*."""
    head = text[max(0, index - 1500):index].rstrip()
    if not head.endswith("*/"):
        return ""
    j = head.rfind("/**")
    if j < 0:
        return ""
    for ln in head[j + 3:-2].splitlines():
        ln = ln.strip().lstrip("*").strip()
        if ln and not ln.startswith("@"):
            return ln
    return ""


# ============================================================================ detection
def is_codeigniter(folder) -> bool:
    f = Path(folder)
    if (f / "spark").is_file() and (f / "app" / "Config" / "App.php").is_file():
        return True
    try:
        data = json.loads((f / "composer.json").read_text(encoding="utf-8"))
        req = {**(data.get("require") or {}), **(data.get("require-dev") or {})}
        return "codeigniter4/framework" in req or "codeigniter4/codeigniter4" in req
    except (OSError, ValueError, AttributeError):
        return False


def web_block(folder) -> dict:
    try:
        data = json.loads((Path(folder) / "project.radproj").read_text(encoding="utf-8"))
        web = data.get("web") or {}
        return web if isinstance(web, dict) else {}
    except (OSError, ValueError):
        return {}


def is_ci_project(folder) -> bool:
    """A RAD IDE project folder of a CodeIgniter 4 site (web.framework, else the files)."""
    web = web_block(folder)
    fw = str(web.get("framework") or "").lower()
    if fw:
        return fw == FRAMEWORK
    return (Path(folder) / "project.radproj").is_file() and is_codeigniter(folder)


_ROOTS: dict[str, Path | None] = {}


def project_root_of(path) -> Path | None:
    """The CodeIgniter project folder that contains *path* (None = not in a CodeIgniter project)."""
    try:
        p = Path(path).resolve()
    except OSError:
        return None
    key = os.path.normcase(str(p.parent))
    if key in _ROOTS:
        return _ROOTS[key]
    found = None
    for d in [p.parent, *p.parent.parents]:
        if (d / "project.radproj").is_file():
            found = d if is_ci_project(d) else None
            break
        if (d / "spark").is_file() and (d / "app" / "Config").is_dir():
            found = d
            break
    _ROOTS[key] = found
    return found


def system_dir(root) -> Path:
    return Path(root) / SYSTEM


def framework_version(root) -> str:
    text = read_text(system_dir(root) / "CodeIgniter.php")
    m = re.search(r"CI_VERSION\s*=\s*'([^']+)'", text)
    return m.group(1) if m else ""


# ============================================================================ .env
def read_env(root) -> dict[str, str]:
    """Keys of .env (uncommented) -> values."""
    out = {}
    for ln in read_text(Path(root) / ".env").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        out[k.strip()] = v
    return out


def env_keys(root) -> list[tuple[str, str]]:
    """[(key, value or 'commented in env')] from .env and the shipped env template."""
    out = {k: v for k, v in read_env(root).items()}
    for name in ("env", ".env.example"):
        for ln in read_text(Path(root) / name).splitlines():
            m = re.match(r"\s*#?\s*([A-Za-z_][\w.\\]*)\s*=", ln)
            if m and m.group(1) not in out:
                out[m.group(1)] = "(example in env)"
    return sorted(out.items())


def set_env_values(text: str, values: dict[str, str]) -> str:
    """Set / uncomment ``key = value`` lines of a CodeIgniter .env text (append missing keys)."""
    lines = text.splitlines()
    for key, val in values.items():
        rx = re.compile(r"^\s*#?\s*" + re.escape(key) + r"\s*=")
        new = f"{key} = {val}"
        for i, ln in enumerate(lines):
            if rx.match(ln):
                lines[i] = new
                break
        else:
            lines.append(new)
    return "\n".join(lines) + "\n"


def env_for_database(db: str, conn: dict | None = None) -> dict[str, str]:
    """.env values of the database choice: "sqlite" | "mysql" | "postgresql" (*conn*: host, port, user,
    password, database)."""
    conn = conn or {}
    if db == "sqlite":
        return {"database.default.database": "database.db", "database.default.DBDriver": "SQLite3",
                "database.default.DBPrefix": "", "database.default.foreignKeys": "true"}
    driver = "MySQLi" if db == "mysql" else "Postgre"
    vals = {"database.default.hostname": conn.get("host", "127.0.0.1"),
            "database.default.database": conn.get("database", "radide"),
            "database.default.username": conn.get("user", "radide"),
            "database.default.password": conn.get("password", ""),
            "database.default.DBDriver": driver, "database.default.DBPrefix": "",
            "database.default.port": str(conn.get("port") or (3306 if db == "mysql" else 5432))}
    if db == "postgresql":
        vals["database.default.schema"] = "public"
    return vals


def configure_env(root, db: str = "sqlite", conn: dict | None = None, environment: str = "development") -> Path:
    """Write .env from the shipped ``env`` template (CI_ENVIRONMENT + database)."""
    root = Path(root)
    base = read_text(root / ".env") or read_text(root / "env") or ""
    # clean URLs: the IDE serves the site through CodeIgniter's rewrite.php (like php spark serve / .htaccess)
    values = {"CI_ENVIRONMENT": environment, "app.indexPage": "''"}
    values.update(env_for_database(db, conn))
    text = set_env_values(base, values)
    (root / ".env").write_text(text, encoding="utf-8", newline="\n")
    if db == "sqlite":
        (root / "writable").mkdir(exist_ok=True)
    return root / ".env"


def database_file(root) -> Path | None:
    """The SQLite database of the default connection (None for MySQL / PostgreSQL)."""
    env = read_env(root)
    driver = env.get("database.default.DBDriver", "")
    name = env.get("database.default.database", "")
    if not driver:   # app/Config/Database.php defaults
        text = read_text(Path(root) / "app" / "Config" / "Database.php")
        m = re.search(r"\$default\s*=\s*\[(.*?)\];", text, re.S)
        if m:
            dm = re.search(r"'DBDriver'\s*=>\s*'(\w+)'", m.group(1))
            nm = re.search(r"'database'\s*=>\s*'([^']*)'", m.group(1))
            driver = dm.group(1) if dm else ""
            name = name or (nm.group(1) if nm else "")
    if driver.lower() != "sqlite3" or not name or name == ":memory:":
        return None
    p = Path(name)
    if not p.is_absolute() and "/" not in name and "\\" not in name:
        p = Path(root) / "writable" / name
    elif not p.is_absolute():
        p = Path(root) / p
    return p


# ============================================================================ PHP / Spark
def php_for(project_or_folder) -> str:
    """The PHP of the site (``web.php`` of project.radproj - radide/web_site/php_toolchain.py)."""
    try:
        from .. import php_toolchain as tc
        if hasattr(project_or_folder, "folder"):
            php = tc.project_php(project_or_folder, tc.configured_php())
        else:
            php = tc.php_for_folder(project_or_folder)
        if php:
            return php
    except Exception:  # noqa: BLE001 - no toolchain module / settings
        pass
    return shutil.which("php") or ""


def php_args(php: str) -> list[str]:
    """``php`` plus -d options for extensions missing from its php.ini (intl, mbstring ...)."""
    try:
        from ...languages.php_web import extension_args
        return [php, *extension_args(php)]
    except Exception:  # noqa: BLE001
        return [php]


def spark_argv(root, args: list[str], php: str = "") -> list[str]:
    php = php or php_for(root)
    return [*php_args(php), "spark", *args]


def run(argv, cwd, timeout: float = 120, log=None, env: dict | None = None) -> tuple[int, str]:
    """Run a command without a window; returns (exit code, output). *log* gets each line."""
    full = dict(os.environ)
    full.update(env or {})
    full.setdefault("COMPOSER_NO_INTERACTION", "1")
    try:
        p = subprocess.Popen([str(a) for a in argv], cwd=str(cwd), env=full, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except OSError as e:
        if log:
            log(f"*** cannot run {argv[0]}: {e}")
        return 127, str(e)
    out: list[str] = []
    timer = threading.Timer(timeout, p.kill) if timeout else None
    if timer:
        timer.start()
    try:
        for raw in iter(p.stdout.readline, b""):
            line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw.decode("utf-8", "replace").rstrip("\r\n"))
            out.append(line)
            if log:
                log(line)
        p.wait()
    finally:
        if timer:
            timer.cancel()
    return p.returncode, "\n".join(out)


def spark(root, args: list[str], php: str = "", timeout: float = 120, log=None) -> tuple[int, str]:
    return run(spark_argv(root, [*args, "--no-ansi"] if "--no-ansi" not in args else args, php), root,
               timeout, log)


@dataclass
class SparkCommand:
    name: str
    group: str
    description: str


def parse_spark_list(text: str) -> list[SparkCommand]:
    out: list[SparkCommand] = []
    group = ""
    for raw in text.splitlines():
        ln = raw.rstrip()
        if not ln.strip() or ln.startswith("CodeIgniter v"):
            continue
        m = re.match(r"^  (\S+)\s{2,}(.*)$", ln)
        if m:
            out.append(SparkCommand(m.group(1), group, m.group(2).strip()))
        elif re.match(r"^\s{4,}\S", ln) and out:
            out[-1].description += " " + ln.strip()
        elif not ln.startswith(" "):
            group = ln.strip()
    return out


def spark_commands(root, php: str = "") -> list[SparkCommand]:
    code, text = spark(root, ["list"], php, timeout=60)
    return parse_spark_list(text) if code == 0 else []


@dataclass
class SparkHelp:
    name: str
    usage: str = ""
    description: str = ""
    arguments: list[tuple[str, str]] = field(default_factory=list)      # (name, description)
    options: list[tuple[str, str]] = field(default_factory=list)        # ("--force", description)

    def option_kind(self, opt: str) -> tuple[str, list[str], str]:
        """("flag" | "choice" | "value", choices, default) - guessed from the description."""
        desc = dict(self.options).get(opt, "")
        m = re.search(r"Options:\s*\[([^\]]*)\]", desc)
        d = re.search(r'Default:\s*"?([^".]*)"?', desc)
        default = d.group(1).strip() if d else ""
        if m:
            return "choice", [c.strip() for c in m.group(1).split(",") if c.strip()], default
        low = desc.lower()
        if d or opt in ("--table", "--dbgroup", "--namespace", "--return", "--host", "--group", "-n", "-g") or \
                (re.match(r"(set|specify|supply)\b", low) and "for all" not in low):
            return "value", [], default
        return "flag", [], ""


def parse_spark_help(name: str, text: str) -> SparkHelp:
    h = SparkHelp(name)
    section = ""
    for raw in text.splitlines():
        ln = raw.rstrip()
        if not ln.strip() or ln.startswith("CodeIgniter v"):
            continue
        if re.match(r"^(Usage|Description|Arguments|Options):\s*$", ln):
            section = ln.rstrip(":").strip().lower()
            continue
        s = ln.strip()
        if section == "usage":
            h.usage = (h.usage + " " + s).strip()
        elif section == "description":
            h.description = (h.description + " " + s).strip()
        elif section in ("arguments", "options"):
            m = re.match(r"^\s{2}(\S+)\s{2,}(.*)$", ln)
            target = h.arguments if section == "arguments" else h.options
            if m:
                target.append((m.group(1), m.group(2).strip()))
            elif target and re.match(r"^\s{4,}", ln):
                target[-1] = (target[-1][0], target[-1][1] + " " + s)
    return h


def spark_help(root, name: str, php: str = "") -> SparkHelp:
    _code, text = spark(root, ["help", name], php, timeout=60)
    return parse_spark_help(name, text)


# ============================================================================ routes
@dataclass
class Route:
    method: str
    path: str
    handler: str = ""
    name: str = ""
    file: str = ""
    line: int = 0
    filters: str = ""

    def url_path(self) -> str:
        segs = []
        for s in self.path.strip("/").split("/"):
            if not s:
                continue
            if s.startswith("(") or s.startswith("{") or s.startswith(":"):
                break
            segs.append(s)
        return "/" + "/".join(segs)


ROUTE_CALL = re.compile(r"\$routes\s*->\s*(get|post|put|patch|delete|options|head|add|match|cli|view|resource|"
                        r"presenter|group|addRedirect|environment)\s*\(")


def _args_of(text: str, open_paren: int) -> tuple[str, int]:
    """Text of the argument list starting at *open_paren* (up to the matching ')' or a '{' of a closure)."""
    depth = 0
    for m in TOKEN.finditer(text, open_paren):
        kind = m.lastgroup
        if kind == "o":
            depth += 1
        elif kind == "x":
            depth -= 1
            if depth <= 0:
                return text[open_paren + 1:m.start()], m.end()
    return text[open_paren + 1:], len(text)


def _brace_depth_map(text: str) -> list[tuple[int, int]]:
    """(offset, depth after it) for every { and } outside strings / comments."""
    out = []
    depth = 0
    rx = re.compile(r"/\*.*?\*/|//[^\n]*|#[^\n]*|'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"|[{}]", re.S)
    for m in rx.finditer(text):
        t = m.group()
        if t == "{":
            depth += 1
            out.append((m.start(), depth))
        elif t == "}":
            depth -= 1
            out.append((m.start(), depth))
    return out


def _depth_at(depths: list[tuple[int, int]], offset: int) -> int:
    d = 0
    for off, dep in depths:
        if off >= offset:
            break
        d = dep
    return d


def _handler_of(args: str) -> str:
    m = re.search(r"\[\s*\\?([\w\\]+)::class\s*,\s*['\"](\w+)['\"]\s*\]", args)
    if m:
        return f"{m.group(1).split(chr(92))[-1]}::{m.group(2)}"
    strs = [_php_string(s) for s in re.findall(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", args)]
    for s in strs[1:]:
        if "::" in s:
            return s.lstrip("\\")
    return ""


def static_routes(root) -> list[Route]:
    """Routes declared in app/Config/Routes.php (and app/Config/Routes/*.php), with file and line."""
    root = Path(root)
    files = [root / "app" / "Config" / "Routes.php"]
    extra = root / "app" / "Config" / "Routes"
    if extra.is_dir():
        files += sorted(extra.glob("*.php"))
    out: list[Route] = []
    for f in files:
        text = read_text(f)
        if not text:
            continue
        depths = _brace_depth_map(text)
        groups: list[tuple[int, str, str]] = []   # (brace depth inside, prefix, filter)
        for m in ROUTE_CALL.finditer(text):
            verb = m.group(1)
            depth = _depth_at(depths, m.start())
            while groups and groups[-1][0] > depth:
                groups.pop()
            prefix = "/".join(g[1].strip("/") for g in groups if g[1].strip("/"))
            args, _end = _args_of(text, m.end() - 1)
            strs = [_php_string(s) for s in re.findall(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", args)]
            ln = line_of(text, m.start())
            opts_as = re.search(r"['\"]as['\"]\s*=>\s*['\"]([^'\"]+)['\"]", args)
            opts_filter = re.search(r"['\"]filter['\"]\s*=>\s*['\"]([^'\"]+)['\"]", args)
            if verb == "group":
                gfilter = opts_filter.group(1) if opts_filter else ""
                groups.append((depth + 1, strs[0] if strs else "", gfilter))
                continue
            if verb == "environment":
                groups.append((depth + 1, "", ""))
                continue
            inherited = ",".join(g[2] for g in groups if g[2])
            if verb == "match":
                mm = re.match(r"\s*\[([^\]]*)\]\s*,", args)
                methods = ",".join(x.upper() for x in re.findall(r"['\"](\w+)['\"]", mm.group(1))) if mm else "ANY"
                rest = [_php_string(s) for s in re.findall(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"",
                                                            args[mm.end():] if mm else args)]
                path = rest[0] if rest else ""
                handler = _handler_of(args[mm.end() - 1:] if mm else args)
                if not handler and len(rest) > 1 and "::" in rest[1]:
                    handler = rest[1]
            else:
                if not strs:
                    continue
                path = strs[0]
                methods = {"add": "ANY", "view": "GET", "cli": "CLI", "addRedirect": "REDIRECT"}.get(verb, verb.upper())
                handler = _handler_of(args)
                if verb == "view" and len(strs) > 1:
                    handler = f"view: {strs[1]}"
                if verb == "addRedirect" and len(strs) > 1:
                    handler = f"-> {strs[1]}"
            full = "/".join(x for x in (prefix, path.strip("/")) if x) or "/"
            name = opts_as.group(1) if opts_as else ""
            filt = ",".join(x for x in (inherited, opts_filter.group(1) if opts_filter else "") if x)
            if verb in ("resource", "presenter"):
                ctrl = re.search(r"['\"]controller['\"]\s*=>\s*['\"]([^'\"]+)['\"]", args)
                cname = (ctrl.group(1) if ctrl else path.strip("/").replace("/", "\\").title()).lstrip("\\")
                cname = cname.split("\\")[-1] if "\\" in cname else cname
                plh = "(:segment)"
                acts = ([("GET", "", "index"), ("GET", "new", "new"), ("POST", "", "create"),
                         ("GET", plh, "show"), ("GET", f"{plh}/edit", "edit"), ("PUT", plh, "update"),
                         ("PATCH", plh, "update"), ("DELETE", plh, "delete")] if verb == "resource" else
                        [("GET", "", "index"), ("GET", f"show/{plh}", "show"), ("GET", "new", "new"),
                         ("POST", "create", "create"), ("GET", f"edit/{plh}", "edit"),
                         ("POST", f"update/{plh}", "update"), ("GET", f"remove/{plh}", "remove"),
                         ("POST", f"delete/{plh}", "delete")])
                for meth, sub, act in acts:
                    out.append(Route(meth, "/".join(x for x in (full.strip("/"), sub) if x), f"{cname}::{act}",
                                     "", str(f), ln, filt))
                continue
            out.append(Route(methods, full, handler, name, str(f), ln, filt))
    return out


def parse_spark_routes(text: str) -> list[Route]:
    out = []
    for ln in text.splitlines():
        if not ln.startswith("|") or ln.startswith("| Method"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        name = cells[1] if cells[2] in ("»", "?") else cells[2]
        out.append(Route(cells[0], cells[1], cells[3].lstrip("\\"), name,
                         filters=" / ".join(c for c in cells[4:6] if c)))
    return out


def spark_routes(root, php: str = "") -> list[Route]:
    """``php spark routes`` (the real route table, auto-routes included), with file/line from Routes.php."""
    code, text = spark(root, ["routes"], php, timeout=60)
    routes = parse_spark_routes(text) if code == 0 else []
    static = static_routes(root)
    for r in routes:
        key = r.path.strip("/")
        for s in static:
            if s.path.strip("/") == key and (s.method in (r.method, "ANY") or r.method in s.method.split(",")):
                r.file, r.line = s.file, s.line
                break
    return routes


def handler_location(root, handler: str) -> tuple[str, int] | None:
    """File and line of ``\\App\\Controllers\\Products::show`` / ``Admin\\Users::index`` / ``Products``."""
    h = handler.strip().lstrip("\\")
    if h.startswith(("view:", "->", "(Closure)")) or h.lower().startswith("(closure"):
        return None
    h = re.sub(r"/.*$", "", h)                          # Products::show/$1
    cls, _, meth = h.partition("::")
    cls = cls.replace("/", "\\")
    if cls.startswith("App\\Controllers\\"):
        cls = cls[len("App\\Controllers\\"):]
    elif cls.startswith("App\\"):
        cls = cls[len("App\\"):]
    base = Path(root) / "app" / "Controllers"
    f = base / (cls.replace("\\", "/") + ".php")
    if not f.is_file():
        cands = [p for p in base.rglob("*.php") if p.stem.lower() == cls.split("\\")[-1].lower()]
        if not cands:
            return None
        f = cands[0]
    text = read_text(f)
    if meth:
        m = re.search(r"function\s+" + re.escape(meth) + r"\s*\(", text)
        if m:
            return str(f), line_of(text, m.start())
    m = re.search(r"\bclass\s+\w+", text)
    return str(f), line_of(text, m.start()) if m else 1


# ============================================================================ project index
@dataclass
class Item:
    label: str
    kind: int
    detail: str = ""
    file: str = ""
    line: int = 0
    doc: str = ""


@dataclass
class Model:
    name: str
    file: str
    line: int = 1
    table: str = ""
    primary_key: str = "id"
    allowed: list[str] = field(default_factory=list)
    timestamps: bool = False
    return_type: str = "array"


@dataclass
class Index:
    root: Path
    views: dict[str, str] = field(default_factory=dict)                 # "products/index" -> file
    routes: list[Route] = field(default_factory=list)
    lang: dict[str, tuple[str, int, str]] = field(default_factory=dict)  # "Shop.title" -> (file, line, text)
    configs: dict[str, tuple[str, int]] = field(default_factory=dict)   # "App" -> (file, line)
    config_props: dict[str, dict[str, tuple[str, int, str]]] = field(default_factory=dict)
    helpers: dict[str, tuple[str, list[tuple[str, int, str, str]]]] = field(default_factory=dict)
    # helper name -> (file, [(function, line, signature, doc)])
    services: dict[str, tuple[str, int, str]] = field(default_factory=dict)
    models: dict[str, Model] = field(default_factory=dict)
    tables: dict[str, dict[str, tuple[str, str, int]]] = field(default_factory=dict)
    # table -> field -> (type, file, line)
    controllers: dict[str, tuple[str, list[tuple[str, int]]]] = field(default_factory=dict)
    sections: dict[str, tuple[str, int]] = field(default_factory=dict)
    autoload_helpers: list[str] = field(default_factory=list)
    seeders: list[str] = field(default_factory=list)
    stamp: tuple = ()
    built: float = 0.0


_INDEX: dict[str, Index] = {}
_LOCK = threading.RLock()


def _stamp(root: Path) -> tuple:
    """Cheap change detector: newest mtime + number of files of app/, .env, the SQLite file, vendor CI."""
    n, newest = 0, 0.0
    for dirpath, dirnames, filenames in os.walk(root / "app"):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        try:
            newest = max(newest, os.stat(dirpath).st_mtime)
        except OSError:
            pass
        for f in filenames:
            n += 1
            try:
                newest = max(newest, os.stat(os.path.join(dirpath, f)).st_mtime)
            except OSError:
                pass
    extra = []
    for p in (root / ".env", database_file(root), system_dir(root) / "CodeIgniter.php"):
        try:
            extra.append(os.stat(p).st_mtime if p is not None else 0)
        except OSError:
            extra.append(0)
    return (n, newest, *extra)


def index(root, force: bool = False, max_age: float = 1.5) -> Index:
    """The project's index, rebuilt when something changed (checked at most every *max_age* seconds)."""
    root = Path(root).resolve()
    key = os.path.normcase(str(root))
    with _LOCK:
        idx = _INDEX.get(key)
        now = time.monotonic()
        if idx is not None and not force and now - idx.built < max_age:
            return idx
        st = _stamp(root)
        if idx is not None and not force and idx.stamp == st:
            idx.built = now
            return idx
        idx = build_index(root)
        idx.stamp = st
        idx.built = now
        _INDEX[key] = idx
        return idx


def invalidate(root=None) -> None:
    with _LOCK:
        if root is None:
            _INDEX.clear()
            _ROOTS.clear()
        else:
            _INDEX.pop(os.path.normcase(str(Path(root).resolve())), None)


def build_index(root: Path) -> Index:
    idx = Index(root)
    app = root / "app"
    sysd = system_dir(root)
    # ---- views + sections
    vroot = app / "Views"
    if vroot.is_dir():
        for p in sorted(vroot.rglob("*.php")):
            name = p.relative_to(vroot).with_suffix("").as_posix()
            idx.views[name] = str(p)
            text = read_text(p)
            for m in re.finditer(r"renderSection\s*\(\s*['\"](\w+)['\"]", text):
                idx.sections.setdefault(m.group(1), (str(p), line_of(text, m.start())))
    # ---- routes
    try:
        idx.routes = static_routes(root)
    except Exception:  # noqa: BLE001 - half-typed Routes.php
        idx.routes = []
    # ---- language files (the default locale + system "en")
    locale = "en"
    m = re.search(r"\$defaultLocale\s*=\s*'([^']+)'", read_text(app / "Config" / "App.php"))
    if m:
        locale = m.group(1)
    for lroot, prio in ((app / "Language" / locale, 0), (sysd / "Language" / "en", 1)):
        if not lroot.is_dir():
            continue
        for p in sorted(lroot.rglob("*.php")):
            file_key = p.relative_to(lroot).with_suffix("").as_posix().replace("/", "\\")
            text = read_text(p)
            r = re.search(r"\breturn\b", text)
            if not r:
                continue
            for key, off, value in array_keys(text, r.end()):
                full = f"{file_key}.{key}"
                if prio and full in idx.lang:
                    continue
                idx.lang[full] = (str(p), line_of(text, off), value)
    # ---- config classes and their properties
    for croot in (app / "Config", sysd / "Config"):
        if not croot.is_dir():
            continue
        for p in sorted(croot.glob("*.php")):
            text = read_text(p)
            cm = re.search(r"^\s*(?:final\s+)?class\s+(\w+)", text, re.M)
            if not cm or cm.group(1) in idx.configs:
                continue
            if croot == sysd / "Config" and cm.group(1) in ("BaseConfig", "BaseService", "Services", "Factories",
                                                            "AutoloadConfig", "DotEnv", "View", "Routing"):
                continue
            cname = cm.group(1)
            idx.configs[cname] = (str(p), line_of(text, cm.start()))
            props = {}
            for pm in re.finditer(r"^\s*public\s+(?:static\s+)?(?:\??[\w\\|]+\s+)?\$(\w+)\s*(=|;)", text, re.M):
                props[pm.group(1)] = (str(p), line_of(text, pm.start()), _doc_before(text, pm.start()))
            idx.config_props[cname] = props
    # ---- helpers
    for hroot in (sysd / "Helpers", app / "Helpers"):
        if not hroot.is_dir():
            continue
        for p in sorted(hroot.glob("*_helper.php")):
            name = p.name[:-len("_helper.php")]
            text = read_text(p)
            funcs = []
            for fm in re.finditer(r"^\s*function\s+(\w+)\s*\(([^)]*)\)", text, re.M):
                funcs.append((fm.group(1), line_of(text, fm.start()), f"{fm.group(1)}({' '.join(fm.group(2).split())})",
                              _doc_before(text, fm.start())))
            idx.helpers[name] = (str(p), funcs)
    al = read_text(app / "Config" / "Autoload.php")
    m = re.search(r"\$helpers\s*=\s*\[", al)
    if m:
        idx.autoload_helpers += [v for v, _o in list_values(al, m.start())]
    bc = read_text(app / "Controllers" / "BaseController.php")
    m = re.search(r"\$helpers\s*=\s*\[", bc)
    if m:
        idx.autoload_helpers += [v for v, _o in list_values(bc, m.start())]
    # ---- services
    for sp in (app / "Config" / "Services.php", sysd / "Config" / "Services.php"):
        text = read_text(sp)
        for fm in re.finditer(r"public\s+static\s+function\s+(\w+)\s*\(([^)]*)\)", text):
            n = fm.group(1)
            if n.startswith("_") or n in idx.services or n in ("getSharedInstance", "injectMock", "reset",
                                                                "resetSingle", "autoloadServices", "serviceExists",
                                                                "buildServicesCache", "discoverServices"):
                continue
            idx.services[n] = (str(sp), line_of(text, fm.start()), _doc_before(text, fm.start()))
    # ---- controllers
    croot = app / "Controllers"
    if croot.is_dir():
        for p in sorted(croot.rglob("*.php")):
            text = read_text(p)
            if not re.search(r"\bclass\s+\w+", text):
                continue
            cname = p.relative_to(croot).with_suffix("").as_posix().replace("/", "\\")
            methods = [(fm.group(1), line_of(text, fm.start()))
                       for fm in re.finditer(r"public\s+function\s+(\w+)\s*\(", text)
                       if not fm.group(1).startswith("_") and fm.group(1) != "initController"]
            idx.controllers[cname] = (str(p), methods)
    # ---- migrations -> tables
    mroot = app / "Database" / "Migrations"
    if mroot.is_dir():
        for p in sorted(mroot.glob("*.php")):
            _scan_migration(read_text(p), str(p), idx.tables)
    sroot = app / "Database" / "Seeds"
    if sroot.is_dir():
        idx.seeders = sorted(p.relative_to(sroot).with_suffix("").as_posix().replace("/", "\\")
                             for p in sroot.rglob("*.php"))
    # ---- the real schema (SQLite)
    dbf = database_file(root)
    if dbf is not None and dbf.is_file():
        try:
            con = sqlite3.connect(f"file:{dbf.as_posix()}?mode=ro", uri=True, timeout=1)
            try:
                for (tname,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' "
                                            "AND name NOT LIKE 'sqlite_%'"):
                    cols = idx.tables.setdefault(tname, {})
                    for row in con.execute(f"PRAGMA table_info(\"{tname}\")"):
                        cols.setdefault(row[1], (row[2] or "", str(dbf), 0))
            finally:
                con.close()
        except sqlite3.Error:
            pass
    # ---- models
    mroot = app / "Models"
    if mroot.is_dir():
        for p in sorted(mroot.rglob("*.php")):
            text = read_text(p)
            cm = re.search(r"\bclass\s+(\w+)\s+extends\s+([\w\\]*Model)\b", text)
            if not cm:
                continue
            md = Model(cm.group(1), str(p), line_of(text, cm.start()))
            tm = re.search(r"\$table\s*=\s*['\"](\w+)['\"]", text)
            md.table = tm.group(1) if tm else ""
            pm = re.search(r"\$primaryKey\s*=\s*['\"](\w+)['\"]", text)
            md.primary_key = pm.group(1) if pm else "id"
            am = re.search(r"\$allowedFields\s*=\s*\[", text)
            if am:
                md.allowed = [v for v, _o in list_values(text, am.start())]
            md.timestamps = bool(re.search(r"\$useTimestamps\s*=\s*true", text))
            rm = re.search(r"\$returnType\s*=\s*['\"]?([\w\\:]+)", text)
            md.return_type = rm.group(1) if rm else "array"
            idx.models[md.name] = md
    return idx


def _method_span(text: str, name: str) -> tuple[int, int] | None:
    """(start, end) offsets of the body of ``function <name>(...)`` (braces matched outside strings)."""
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)[^{;]*\{", text)
    if not m:
        return None
    depth = 1
    for off, dep in _brace_depth_map(text[m.end():]):
        depth = dep + 1
        if depth == 0:
            return m.end(), m.end() + off
    return m.end(), len(text)


def _scan_migration(text: str, file: str, tables: dict) -> None:
    """Tables / columns created by a migration's up() (down() undoes them, so it is skipped)."""
    pending: dict[str, tuple[str, int]] = {}
    span = _method_span(text, "up")
    lo, hi = span if span else (0, len(text))
    for m in re.finditer(r"->(addField|createTable|addColumn|dropColumn|renameTable|dropTable)\s*\(", text):
        if not lo <= m.start() < hi:
            continue
        verb = m.group(1)
        args, _end = _args_of(text, m.end() - 1)
        if verb == "addField":
            s = args.strip()
            if s.startswith(("'", '"')):
                v = _php_string(re.match(r"'(?:[^'\\]|\\.)*'|\"(?:[^\"\\]|\\.)*\"", s).group())
                if v.lower() == "id":
                    pending["id"] = ("INT (auto increment)", line_of(text, m.start()))
                elif " " in v:
                    pending[v.split()[0].strip("`\"")] = (" ".join(v.split()[1:]), line_of(text, m.start()))
                continue
            for key, off, _v in array_keys(text, m.end() - 1, max_depth=4):
                if "." in key:
                    continue
                typ = ""
                tm = re.search(re.escape(key) + r"['\"]\s*=>\s*\[[^\]]*?['\"]type['\"]\s*=>\s*['\"](\w+)",
                               text[off:off + 400])
                if tm:
                    typ = tm.group(1)
                pending[key] = (typ, line_of(text, off))
        elif verb == "createTable":
            sm = re.search(r"['\"](\w+)['\"]", args)
            if sm:
                cols = tables.setdefault(sm.group(1), {})
                for k, (typ, ln) in pending.items():
                    cols[k] = (typ, file, ln)
            pending = {}
        elif verb == "addColumn":
            sm = re.search(r"['\"](\w+)['\"]", args)
            if sm:
                cols = tables.setdefault(sm.group(1), {})
                br = text.find("[", m.end())
                if br >= 0:
                    for key, off, _v in array_keys(text, br, max_depth=4):
                        if "." not in key:
                            cols[key] = ("", file, line_of(text, off))
        elif verb == "dropColumn":
            sm = re.findall(r"['\"](\w+)['\"]", args)
            if len(sm) >= 2 and sm[0] in tables:
                for c in sm[1:]:
                    tables[sm[0]].pop(c, None)
        elif verb == "renameTable":
            sm = re.findall(r"['\"](\w+)['\"]", args)
            if len(sm) >= 2 and sm[0] in tables:
                tables[sm[1]] = tables.pop(sm[0])


def model_fields(idx: Index, model: Model) -> dict[str, tuple[str, str, int]]:
    """field -> (type, file, line) of a model: table schema / migrations + allowedFields + key + timestamps."""
    out: dict[str, tuple[str, str, int]] = {}
    if model.primary_key:
        out[model.primary_key] = ("primary key", model.file, model.line)
    out.update(idx.tables.get(model.table, {}))
    for f in model.allowed:
        out.setdefault(f, ("allowed field", model.file, model.line))
    if model.timestamps:
        for f in ("created_at", "updated_at"):
            out.setdefault(f, ("timestamp", model.file, model.line))
    return out


def _norm(s: str) -> str:
    s = s.lower().replace("_", "")
    for suf in ("model", "entity", "list", "rows", "row", "data"):
        if s.endswith(suf) and len(s) > len(suf):
            s = s[:-len(suf)]
    if s.endswith("ies"):
        s = s[:-3] + "y"
    elif s.endswith("s") and not s.endswith("ss"):
        s = s[:-1]
    return s


def find_model(idx: Index, hint: str) -> Model | None:
    """The model a variable / property / class name refers to (productModel, products, $product ...)."""
    if not hint:
        return None
    if hint in idx.models:
        return idx.models[hint]
    h = _norm(hint.split("\\")[-1])
    for md in idx.models.values():
        if _norm(md.name) == h or (md.table and _norm(md.table) == h):
            return md
    return None


# ============================================================================ completion contexts
def string_at(line_text: str, col: int) -> tuple[int, int, str] | None:
    """If *col* (0-based) is inside a string literal of the line: (start quote index, end index or len, quote)."""
    quote, start, i = None, 0, 0
    while i < len(line_text):
        c = line_text[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                if start < col <= i:
                    return start, i, quote
                quote = None
        else:
            if c == "/" and line_text[i:i + 2] == "//" or c == "#" and line_text[i:i + 2] != "#[":
                break
            if c in "'\"":
                quote, start = c, i
        i += 1
    if quote and start < col:
        return start, len(line_text), quote
    return None


def _statement_before(text: str, offset: int) -> str:
    """The code of the current statement up to *offset* (from the previous ';', '{' or '}')."""
    head = text[max(0, offset - 3000):offset]
    cut = max(head.rfind(";"), head.rfind("{"), head.rfind("}"))
    return head[cut + 1:]


def _receiver_model(idx: Index, path: Path, text: str, pre: str) -> Model | None:
    """The model of ``<receiver>->where(`` in *pre* (statement text before the call)."""
    m = re.search(r"model\(\s*['\"]?([\w\\]+?)(?:::class)?['\"]?\s*\)", pre)
    if m:
        return find_model(idx, m.group(1).split("\\")[-1])
    m = re.search(r"new\s+\\?([\w\\]+)\s*\(", pre)
    if m:
        return find_model(idx, m.group(1).split("\\")[-1])
    m = re.search(r"\$this->(\w+)\s*(?:->|$)", pre.strip())
    if m:
        name = m.group(1)
        am = re.search(r"\$this->" + re.escape(name) + r"\s*=\s*(?:model\(\s*['\"]?([\w\\]+?)(?:::class)?['\"]?\s*\)|"
                       r"new\s+\\?([\w\\]+))", text)
        if am:
            return find_model(idx, (am.group(1) or am.group(2)).split("\\")[-1])
        return find_model(idx, name)
    m = re.match(r"\s*\$(\w+)", pre)
    if m and m.group(1) != "this":
        var = m.group(1)
        am = re.search(r"\$" + re.escape(var) + r"\s*=\s*(?:model\(\s*['\"]?([\w\\]+?)(?:::class)?['\"]?\s*\)|"
                       r"new\s+\\?([\w\\]+))", text)
        if am:
            return find_model(idx, (am.group(1) or am.group(2)).split("\\")[-1])
        return find_model(idx, var)
    if re.match(r"\s*\$this\s*->", pre):        # inside a model class: $this->where(
        for md in idx.models.values():
            if Path(md.file) == Path(path):
                return md
    return None


def _model_of_file(idx: Index, path: Path) -> Model | None:
    for md in idx.models.values():
        try:
            if Path(md.file).resolve() == Path(path).resolve():
                return md
        except OSError:
            pass
    return None


def _all_fields(idx: Index) -> list[Item]:
    out = []
    for md in idx.models.values():
        for f, (typ, file, ln) in model_fields(idx, md).items():
            out.append(Item(f, K_FIELD, f"{md.name} ({md.table or '?'}) {typ}".strip(), file, ln))
    return out


def _field_items(idx: Index, md: Model | None) -> list[Item]:
    if md is None:
        return _all_fields(idx)
    return [Item(f, K_FIELD, f"{md.table or md.name}: {typ}".rstrip(": "), file, ln)
            for f, (typ, file, ln) in model_fields(idx, md).items()]


def loaded_helpers(idx: Index, text: str) -> list[str]:
    names = ["url"] + list(idx.autoload_helpers)
    for m in re.finditer(r"\bhelper\s*\(\s*(\[[^\]]*\]|['\"][\w/]+['\"])", text):
        names += re.findall(r"['\"]([\w/]+)['\"]", m.group(1))
    out = []
    for n in names:
        n = n.split("/")[-1].replace("_helper", "")
        if n not in out:
            out.append(n)
    return out


def context(idx: Index, path: Path, text: str, line: int, col: int) -> tuple[str, list[Item], int] | None:
    """(kind, items, replace-from column) for the cursor, or None. *line* / *col* are 0-based."""
    lines = text.split("\n")
    if line >= len(lines):
        return None
    ltext = lines[line]
    col = min(col, len(ltext))
    offset = sum(len(x) + 1 for x in lines[:line]) + col
    s = string_at(ltext, col)
    if s is not None:
        qstart = s[0]
        prefix = ltext[qstart + 1:col]
        before_q = ltext[:qstart]
        stmt = _statement_before(text, offset - len(prefix) - 1)
        items, kind, start = _string_items(idx, path, text, stmt, before_q, prefix, offset - len(prefix) - 1)
        if kind:
            return kind, items, (start if start is not None else qstart + 1)
        return None
    # ---- code (not in a string)
    before = ltext[:col]
    m = CONFIG_PROP.search(before)
    if m:
        cname = (m.group(1) or m.group(2)).split("\\")[-1]
        props = idx.config_props.get(cname, {})
        return "config-prop", [Item(p, K_PROPERTY, f"Config\\{cname}", f, ln, doc)
                               for p, (f, ln, doc) in props.items()], col - len(m.group(3))
    m = re.search(r"(?<![\w$>:\\])([a-z_]\w{1,})$", before)
    if m and not re.search(r"(->|::|\$|function\s+|new\s+)\s*" + re.escape(m.group(1)) + "$", before):
        word = m.group(1)
        out = []
        for h in loaded_helpers(idx, text):
            hfile, funcs = idx.helpers.get(h, ("", []))
            for fn, ln, sig, doc in funcs:
                if fn.lower().startswith(word.lower()):
                    out.append(Item(fn, K_FUNCTION, f"{sig}  - {h} helper (loaded)", hfile, ln, doc))
        if out:
            return "helper-function", out, col - len(word)
    return None


def _string_items(idx: Index, path: Path, text: str, stmt: str, before_q: str, prefix: str,
                  qoffset: int) -> tuple[list[Item], str, int | None]:
    bq = before_q.rstrip()
    st = stmt.rstrip()
    name = Path(path).name
    # views
    if VIEW_CALL.search(bq) or VIEW_CALL.search(st) or ROUTE_VIEW.search(st):
        return [Item(v, K_FILE, "view", f, 1) for v, f in idx.views.items()], "view", None
    if ROUTE_NAME_CALL.search(bq) or ROUTE_NAME_CALL.search(st):
        items = [Item(r.name, K_REFERENCE, f"{r.method} /{r.path.strip('/')}  -> {r.handler}", r.file, r.line)
                 for r in idx.routes if r.name]
        seen = set()
        for r in idx.routes:
            if r.handler and "::" in r.handler and r.handler not in seen:
                seen.add(r.handler)
                items.append(Item(r.handler, K_METHOD, f"{r.method} /{r.path.strip('/')}", r.file, r.line))
        return items, "route-name", None
    if PATH_CALL.search(bq) or PATH_CALL.search(st):
        seen, items = set(), []
        for r in idx.routes:
            p = r.path.strip("/")
            if p in seen or r.method in ("CLI",) or (r.method not in ("GET", "ANY", "REDIRECT") and "(" in p):
                continue
            seen.add(p)
            items.append(Item(p or "/", K_REFERENCE, f"{r.method}  -> {r.handler or r.name}", r.file, r.line))
        return items, "route-path", None
    if CONFIG_CALL.search(bq) or CONFIG_CALL.search(st):
        if "." in prefix:
            cname = prefix.split(".")[0]
            props = idx.config_props.get(cname, {})
            return ([Item(f"{cname}.{p}", K_PROPERTY, f"Config\\{cname}", f, ln, doc) for p, (f, ln, doc) in props.items()],
                    "config-key", None)
        return [Item(c, K_CLASS, f"Config\\{c}", f, ln) for c, (f, ln) in idx.configs.items()], "config", None
    if LANG_CALL.search(bq) or LANG_CALL.search(st):
        return [Item(k, K_TEXT, v[:80], f, ln, v) for k, (f, ln, v) in idx.lang.items() if v or "." in k], "lang", None
    if HELPER_CALL.search(bq) or HELPER_CALL.search(st):
        return [Item(h, K_MODULE, f"{len(funcs)} functions", f, 1,
                     ", ".join(fn for fn, *_r in funcs[:30])) for h, (f, funcs) in idx.helpers.items()], "helper", None
    if SERVICE_CALL.search(bq) or SERVICE_CALL.search(st):
        return [Item(s, K_METHOD, "Config\\Services::" + s + "()", f, ln, doc)
                for s, (f, ln, doc) in idx.services.items()], "service", None
    if MODEL_CALL.search(bq) or MODEL_CALL.search(st):
        return [Item(m.name, K_CLASS, f"App\\Models\\{m.name} (table {m.table or '?'})", m.file, m.line)
                for m in idx.models.values()], "model", None
    if SECTION_CALL.search(bq) or SECTION_CALL.search(st):
        return [Item(s, K_ENUM_MEMBER, "section of " + Path(f).name, f, ln) for s, (f, ln) in idx.sections.items()], \
            "section", None
    if ENV_CALL.search(bq) or ENV_CALL.search(st):
        return [Item(k, K_CONSTANT, v, str(idx.root / ".env"), 1) for k, v in env_keys(idx.root)], "env", None
    if name == "Routes.php" and (ROUTE_HANDLER.search(st) or ROUTE_HANDLER.search(bq)):
        items = []
        for cname, (f, methods) in idx.controllers.items():
            items.append(Item(cname, K_CLASS, "controller", f, 1))
            for meth, ln in methods:
                items.append(Item(f"{cname}::{meth}", K_METHOD, "controller method", f, ln))
        return items, "handler", None
    # validation rules: 'field' => 'required|min_length[3]'
    if re.search(r"=>\s*$", bq) and re.search(r"(validat|rules|setRule)", text[max(0, qoffset - 1500):qoffset], re.I):
        col_start = len(before_q) + 1 + (prefix.rfind("|") + 1 if "|" in prefix else 0)
        items = [Item(r, K_KEYWORD, d) for r, d in VALIDATION_RULES]
        return items, "rule", col_start
    # model fields
    fm_st = FIELD_CALL.search(st)
    fm_bq = None if fm_st else FIELD_CALL.search(bq)
    if fm_st or fm_bq:
        pre = st[:fm_st.start()] if fm_st else bq[:fm_bq.start()]
        md = _receiver_model(idx, path, text, pre)
        return _field_items(idx, md), "field", None
    am = ARRAY_KEY.search(bq)
    if am and am.group(1) not in ("_GET", "_POST", "_SERVER", "_SESSION", "_COOKIE", "_FILES", "_ENV", "GLOBALS"):
        md = find_model(idx, am.group(1))
        return _field_items(idx, md), "field", None
    head = text[max(0, qoffset - 1500):qoffset]
    if re.search(r"\$(allowedFields|validationRules|validationMessages|casts|hidden)\s*=\s*\[[^\];]*$", head) or \
            re.search(r"\$(allowedFields|validationRules)\s*=\s*\[[^\]]*$", head):
        md = _model_of_file(idx, path)
        return _field_items(idx, md), "field", None
    if re.search(r"(?:[\[,]\s*)$", bq) and re.search(
            r"->(?:insert|insertBatch|update|updateBatch|save|replace|set|validate|setRules|fill)\s*\([^;]*$", st):
        cm = re.search(r"(.*)->(?:insert|insertBatch|update|updateBatch|save|replace|set|validate|setRules|fill)\s*\(",
                       st, re.S)
        md = _receiver_model(idx, path, text, cm.group(1)) if cm else None
        return _field_items(idx, md), "field", None
    return [], "", None


def complete(root, path, text: str, line: int, col: int, limit: int = 400) -> list[dict]:
    """Monaco completion items (dicts) for the cursor (0-based line / col) - [] outside framework contexts."""
    idx = index(root)
    ctx = context(idx, Path(path), text, line, col)
    if ctx is None:
        return []
    kind, items, start = ctx
    lines = text.split("\n")
    col = min(col, len(lines[line]))
    prefix = lines[line][start:col].lower()
    out = []
    seen = set()
    for it in items:
        if it.label in seen:
            continue
        if prefix and prefix not in it.label.lower():
            continue
        seen.add(it.label)
        out.append({"label": it.label, "kind": it.kind, "detail": it.detail,
                    "documentation": it.doc or (f"{Path(it.file).name}:{it.line}" if it.file else ""),
                    "insertText": it.label, "range": [line, start, line, col], "filterText": it.label,
                    "sortText": ("0" if it.label.lower().startswith(prefix) else "1") + it.label.lower(),
                    "context": kind})
        if len(out) >= limit:
            break
    return out


def complete_items(folder, path, text: str, line: int, col: int) -> list[dict] | None:
    """The PHP-framework completion source (radide/features/php_frameworks.py merges it with intelephense):
    None outside CodeIgniter contexts; inside framework strings the items are "exclusive" (intelephense's
    generic suggestions are dropped there)."""
    items = complete(folder, path, text, line, col)
    if not items:
        return None
    if items[0].get("context") not in ("helper-function", "config-prop"):
        for it in items:
            it["exclusive"] = True
    return items


def definition(root, path, text: str, line: int, col: int) -> tuple[str, int] | None:
    """F12 on a framework string (view / route / lang / config / helper / service / model / handler / field)."""
    idx = index(root)
    lines = text.split("\n")
    if line >= len(lines):
        return None
    ltext = lines[line]
    s = string_at(ltext, col) or string_at(ltext, col + 1)
    path = Path(path)
    if s is None:
        # helper function / config property under the cursor
        m = None
        for mm in re.finditer(r"\w+", ltext):
            if mm.start() <= col <= mm.end():
                m = mm
                break
        if m is None:
            return None
        word = m.group()
        cp = CONFIG_PROP.search(ltext[:m.end()])
        if cp:
            cname = (cp.group(1) or cp.group(2)).split("\\")[-1]
            hit = idx.config_props.get(cname, {}).get(word)
            return (hit[0], hit[1]) if hit else None
        if ltext[m.end():].lstrip().startswith("("):
            for h in loaded_helpers(idx, text):
                for fn, ln, _sig, _doc in idx.helpers.get(h, ("", []))[1]:
                    if fn == word:
                        return idx.helpers[h][0], ln
        return None
    qs, qe, _q = s
    value = ltext[qs + 1:qe]
    ctx = context(idx, path, text, line, qs + 1)
    kind = ctx[0] if ctx else ""
    if not kind and path.name == "Routes.php" and "::" in value:
        kind = "handler"
    if kind == "view":
        f = idx.views.get(value.replace("\\", "/").removesuffix(".php"))
        return (f, 1) if f else None
    if kind == "route-name":
        for r in idx.routes:
            if r.name == value:
                return r.file, r.line
        if "::" in value:
            return handler_location(root, value)
        return None
    if kind == "route-path":
        for r in idx.routes:
            if r.path.strip("/") == value.strip("/"):
                return handler_location(root, r.handler) or (r.file, r.line)
        return None
    if kind in ("config", "config-key"):
        cname, _, prop = value.partition(".")
        if prop and prop in idx.config_props.get(cname, {}):
            f, ln, _d = idx.config_props[cname][prop]
            return f, ln
        return idx.configs.get(cname)
    if kind == "lang":
        hit = idx.lang.get(value)
        if hit:
            return hit[0], hit[1]
        file_key = value.split(".")[0]
        for k, (f, _ln, _v) in idx.lang.items():
            if k.startswith(file_key + "."):
                return f, 1
        return None
    if kind == "helper":
        hit = idx.helpers.get(value.split("/")[-1].replace("_helper", ""))
        return (hit[0], 1) if hit else None
    if kind == "service":
        hit = idx.services.get(value)
        return (hit[0], hit[1]) if hit else None
    if kind == "model":
        md = find_model(idx, value.split("\\")[-1].removesuffix("::class"))
        return (md.file, md.line) if md else None
    if kind == "section":
        hit = idx.sections.get(value)
        return hit
    if kind == "handler":
        return handler_location(root, value)
    if kind == "field":
        items = context(idx, path, text, line, qs + 1)[1]
        for it in items:
            if it.label == value and it.file:
                return it.file, max(1, it.line)
        return None
    if kind == "env":
        return str(idx.root / ".env"), 1
    return None


# ============================================================================ new project
def create_project(folder, name: str, db: str = "sqlite", log=print, php: str = "", conn: dict | None = None,
                   timeout: float = 1800, version: str = "") -> dict:
    """``composer create-project codeigniter4/appstarter`` into *folder* (new or empty) + .env + key.
    Returns the project.radproj "web" block. Raises RuntimeError with the reason on failure."""
    from .. import php_toolchain as tc
    folder = Path(folder).resolve()
    if folder.exists() and any(p.name != "project.radproj" for p in folder.iterdir()):
        raise RuntimeError(f"The folder {folder} is not empty - choose a new project name or location.")
    php = php or tc.resolve("auto") or shutil.which("php") or ""
    if not php:
        raise RuntimeError("PHP was not found - Tools > PHP Versions... > Install PHP 8.4, then create the "
                           "project again.")
    if not tc.find_composer():
        log("[codeigniter] Composer is not installed - downloading the official composer.phar ...")
        tc.install_composer(log)
    argv = tc.composer_argv(["create-project", PACKAGE + (f":{version}" if version else ""), str(folder),
                             "--prefer-dist", "--no-interaction", "--no-progress", "--ansi"], php)
    if not argv:
        raise RuntimeError("Composer is not available (Tools > PHP Versions... > Install Composer).")
    log(f"[codeigniter] composer create-project {PACKAGE} (PHP {tc.php_version(php)}) ... this takes a minute")
    radproj = folder / "project.radproj"
    keep = radproj.read_bytes() if radproj.is_file() else None
    if keep is not None:
        radproj.unlink()
    if folder.is_dir() and not any(folder.iterdir()):
        folder.rmdir()
    folder.parent.mkdir(parents=True, exist_ok=True)
    code, out = run(argv, folder.parent, timeout, log, tc.composer_env(php))
    if keep is not None and folder.is_dir():
        radproj.write_bytes(keep)
    if code != 0 or not (folder / "spark").is_file():
        tail = "\n".join(out.splitlines()[-12:])
        raise RuntimeError(f"composer create-project failed (exit code {code}):\n{tail}")
    configure_env(folder, db, conn)
    log(f"[codeigniter] .env written (CI_ENVIRONMENT = development, database: {db})")
    code, out = spark(folder, ["key:generate", "--force"], php, timeout=120)
    log("[codeigniter] " + (out.strip().splitlines()[-1] if out.strip() else f"key:generate exit {code}"))
    ver = framework_version(folder)
    write_readme(folder, name, db, ver)
    log(f"[codeigniter] CodeIgniter {ver or '4'} is ready (web root: public/). Press F5 to run it.")
    return web_settings(php)


def web_settings(php: str = "") -> dict:
    """The project.radproj "web" block of a CodeIgniter site."""
    series = ""
    try:
        from .. import php_toolchain as tc
        v = tc.php_version(php) if php else ""
        series = tc.series_of(v) if v else ""
        if php and "toolchains" not in php.lower():
            series = ""
    except Exception:  # noqa: BLE001
        pass
    # (no "router": backend_spec() adds CodeIgniter's rewrite.php when vendor/ exists - a missing router file
    # would stop php -S)
    web = {"root": "public", "start": "", "framework": FRAMEWORK, "live_reload": True}
    web["php"] = series or "auto"
    return web


def write_readme(folder: Path, name: str, db: str, version: str) -> None:
    p = Path(folder) / "README.radide.md"
    if p.exists():
        return
    dbtext = {"sqlite": "SQLite3 (`writable/database.db`)", "mysql": "the local MariaDB server",
              "postgresql": "the local PostgreSQL server"}.get(db, db)
    p.write_text(f"""# {name} (CodeIgniter {version or '4'})

Created by RAD IDE with `composer create-project {PACKAGE}`.

- **Run**: F5 (debug, Xdebug breakpoints in controllers / models / views) or Ctrl+F5 - the site runs with
  `public/index.php` + CodeIgniter's `rewrite.php` (what `php spark serve` does) behind the IDE's server
  (Preview, Requests, live reload).
- **Spark**: View > CodeIgniter (Spark commands with forms, Routes - double-click opens the controller).
- **Database**: {dbtext}; settings in `.env`.
- IntelliSense: view(), route_to()/url_to(), lang(), config(), helper(), service(), model fields - read from
  this project; F12 on such a string opens its file.
""", encoding="utf-8")


def ensure_vendor(root, log=print, php: str = "") -> bool:
    """``composer install`` when vendor/ is missing (a cloned / sample project). True when vendor exists."""
    root = Path(root)
    if (root / "vendor" / "autoload.php").is_file():
        return True
    from .. import php_toolchain as tc
    php = php or php_for(root)
    argv = tc.composer_argv(["install", "--no-interaction", "--no-progress", "--prefer-dist"], php)
    if not argv:
        log("*** Composer is not installed (Tools > PHP Versions... > Install Composer)")
        return False
    code, _out = run(argv, root, 1800, log, tc.composer_env(php))
    return code == 0 and (root / "vendor" / "autoload.php").is_file()


def ensure_env(root) -> bool:
    """Create .env from env / .env.example when it is missing. True when a file was written."""
    root = Path(root)
    if (root / ".env").is_file():
        return False
    for src in (".env.example", "env"):
        if (root / src).is_file():
            text = read_text(root / src)
            if src == "env":
                text = set_env_values(text, {"CI_ENVIRONMENT": "development", "app.indexPage": "''",
                                             **env_for_database("sqlite")})
            (root / ".env").write_text(text, encoding="utf-8", newline="\n")
            return True
    return False


# ============================================================================ DevServer backend
def backend_spec(server, spec: dict) -> dict:
    """Adjust the php -S command of a CodeIgniter site: CodeIgniter's rewrite.php as router (when web.router is
    not set) and ``app_baseURL`` = the IDE server's URL, so base_url() / site_url() links point to the Preview."""
    argv = list(spec.get("argv") or [])
    rw = (server.folder / SYSTEM / "rewrite.php").resolve()
    if rw.is_file() and not any(str(a).lower().endswith("rewrite.php") for a in argv):
        argv.append(str(rw))
    env = dict(spec.get("env") or {})
    if server.url and not read_env(server.folder).get("app.baseURL"):
        env["app_baseURL"] = server.url
    env.setdefault("CI_ENVIRONMENT", read_env(server.folder).get("CI_ENVIRONMENT", "development"))
    return {**spec, "argv": argv, "env": env}


def router(folder, _root=None) -> str:
    """CodeIgniter's ``system/rewrite.php`` (what ``php spark serve`` passes to ``php -S``), "" without vendor/."""
    rw = (Path(folder) / SYSTEM / "rewrite.php").resolve()
    return str(rw) if rw.is_file() else ""


def _register() -> None:
    """Register with the PHP framework registry of frameworks/common.py (shared with Laravel)."""
    try:
        from .common import PhpFramework, register_framework
    except Exception:  # noqa: BLE001 - common.py missing: the IDE module calls this module directly
        return
    register_framework(PhpFramework(FRAMEWORK, "CodeIgniter 4", lambda f: is_codeigniter(f), router,
                                    module=__name__, extra={"cli": "spark", "views": "app/Views",
                                                            "package": PACKAGE}))


_register()

__all__ = ["FRAMEWORK", "Index", "Model", "Route", "SparkCommand", "SparkHelp", "array_keys", "backend_spec",
           "complete", "complete_items", "configure_env", "context", "create_project", "database_file", "definition",
           "ensure_env", "ensure_vendor", "env_for_database", "find_model", "handler_location", "index",
           "invalidate", "is_ci_project", "is_codeigniter", "model_fields", "parse_spark_help", "parse_spark_list",
           "parse_spark_routes", "php_for", "project_root_of", "router", "read_env", "set_env_values", "spark",
           "spark_argv", "spark_commands", "spark_help", "spark_routes", "static_routes", "string_at",
           "web_settings"]
