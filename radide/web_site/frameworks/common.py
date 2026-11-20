"""Shared helpers of the PHP frameworks (Laravel ``laravel.py``, CodeIgniter ``codeigniter.py``).

No Qt here - the IDE part is ``radide/features/php_frameworks.py``.

- **Registry**: ``register_framework(PhpFramework(...))``; ``framework_of(folder)`` = the project's framework
  (``project.radproj`` ``web.framework`` first, else detected from the files: ``artisan`` + laravel/framework,
  ``spark`` + codeigniter4/framework ...); ``framework_module(id)`` imports ``frameworks/<id>.py``.
- **Dev server router**: ``router_for(folder, root)`` - the router script ``php -S`` needs (Laravel's
  ``server.php``, CodeIgniter's ``rewrite.php``) so pretty URLs work in the Preview.
- **PHP runner**: ``project_php(folder)``, ``run_php(folder, args)`` - the site's own PHP (php_toolchain.py).
- **Change tracking**: ``tree_stamp(folder, dirs, exts)`` + ``StampCache`` - indexes are rebuilt only when a file
  of the watched folders changed (that is what makes the IntelliSense "dynamic": it follows the project).
- **PHP source helpers**: ``string_call_context(before)`` (which function call / argument a string literal
  belongs to), ``parse_php_array(text)`` (config files -> dotted keys with lines), ``parse_env(path)``,
  ``psr4_map(folder)`` / ``class_file(folder, fqcn)``, ``snake`` / ``plural`` / ``studly``.
- **Completion items** in the shape ``radide/monaco_editor.py`` sends to Monaco: ``item(label, kind, ...)``.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Monaco CompletionItemKind
K_METHOD, K_FUNCTION, K_CONSTRUCTOR, K_FIELD, K_VARIABLE, K_CLASS = 0, 1, 2, 3, 4, 5
K_INTERFACE, K_MODULE, K_PROPERTY, K_EVENT, K_UNIT, K_VALUE, K_CONSTANT = 7, 8, 9, 10, 12, 13, 14
K_ENUM_MEMBER, K_KEYWORD, K_TEXT, K_COLOR, K_FILE, K_REFERENCE, K_FOLDER = 16, 17, 18, 19, 20, 21, 23
K_SNIPPET = 27


# ============================================================================ registry
@dataclass
class PhpFramework:
    id: str                                        # "laravel" | "codeigniter"
    title: str                                     # "Laravel"
    detect: Callable[[Path], bool]                 # folder -> is it this framework?
    router: Callable[[Path, Path], str] | None = None   # (folder, web root) -> router script ("" = none)
    module: str = ""                               # "radide.web_site.frameworks.laravel"
    extra: dict = field(default_factory=dict)


FRAMEWORKS: dict[str, PhpFramework] = {}
_KNOWN_MODULES = ("laravel", "codeigniter")       # frameworks/<name>.py that register themselves
_loaded = False


def register_framework(fw: PhpFramework) -> None:
    FRAMEWORKS[fw.id] = fw


def _load_all() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    import importlib
    import importlib.util
    for name in _KNOWN_MODULES:
        mod = f"{__package__}.{name}"
        try:
            if importlib.util.find_spec(mod) is not None:
                importlib.import_module(mod)
        except Exception as e:  # noqa: BLE001 - one broken framework must not hide the others
            print(f"[php frameworks] {name}: {e}")


def frameworks() -> list[PhpFramework]:
    _load_all()
    return list(FRAMEWORKS.values())


def composer_json(folder) -> dict:
    try:
        return json.loads((Path(folder) / "composer.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def composer_requires(folder, package: str) -> bool:
    data = composer_json(folder)
    return package in (data.get("require") or {}) or package in (data.get("require-dev") or {})


def radproj_web(folder) -> dict:
    try:
        data = json.loads((Path(folder) / "project.radproj").read_text(encoding="utf-8"))
        web = data.get("web")
        return web if isinstance(web, dict) else {}
    except (OSError, ValueError):
        return {}


_FW_CACHE: dict[str, tuple[float, str]] = {}


def framework_of(folder) -> str:
    """"laravel" / "codeigniter" / ... or "" (cached for a few seconds per folder)."""
    if not folder:
        return ""
    key = os.path.normcase(str(Path(folder).resolve()))
    hit = _FW_CACHE.get(key)
    now = time.monotonic()
    if hit and now - hit[0] < 5:
        return hit[1]
    fw = str(radproj_web(folder).get("framework") or "")
    _load_all()
    if fw not in FRAMEWORKS:
        fw = ""
        for f in FRAMEWORKS.values():
            try:
                if f.detect(Path(folder)):
                    fw = f.id
                    break
            except Exception:  # noqa: BLE001
                continue
    _FW_CACHE[key] = (now, fw)
    return fw


def framework_module(fw_id: str):
    _load_all()
    fw = FRAMEWORKS.get(fw_id)
    if fw is None or not fw.module:
        return None
    import importlib
    try:
        return importlib.import_module(fw.module)
    except Exception:  # noqa: BLE001
        return None


def project_root_of(path) -> Path | None:
    """The folder of the PHP framework project that contains *path* (walks up to project.radproj /
    composer.json), None when *path* is not inside one."""
    try:
        p = Path(path).resolve()
    except OSError:
        return None
    for d in [p] + list(p.parents):
        if d.is_dir() and ((d / "composer.json").is_file() or (d / "project.radproj").is_file()):
            if framework_of(d):
                return d
            if (d / "project.radproj").is_file():
                return None
    return None


def router_for(folder, root) -> str:
    """Absolute router script for ``php -S`` (pretty URLs) of a framework project, "" when none."""
    fw = FRAMEWORKS.get(framework_of(folder))
    if fw is None or fw.router is None:
        return ""
    try:
        return fw.router(Path(folder), Path(root)) or ""
    except Exception:  # noqa: BLE001
        return ""


# ============================================================================ PHP runner
def project_php(folder) -> str:
    """The PHP of the project in *folder* (``web.php`` / composer.json ``require.php`` / Tools > Options)."""
    try:
        from ..php_toolchain import php_for_folder
        php = php_for_folder(folder)
        if php:
            return php
    except Exception:  # noqa: BLE001
        pass
    import shutil
    return shutil.which("php") or ""


def php_env(php: str = "") -> dict:
    env = dict(os.environ)
    if php:
        env["PATH"] = str(Path(php).parent) + os.pathsep + env.get("PATH", "")
        env["RADIDE_COMPOSER_PHP"] = php
    env.setdefault("COMPOSER_NO_INTERACTION", "1")
    env["NO_COLOR"] = "1"
    return env


def php_ext_args(php: str) -> list[str]:
    """-d options enabling extensions Laravel / CodeIgniter need that this PHP's php.ini leaves out."""
    try:
        from ...languages.php_web import extension_args
        args = extension_args(php)
    except Exception:  # noqa: BLE001
        return []
    # only what the frameworks need: an ext/ folder with DLLs of another PHP version (a renamed install)
    # would print "Unable to initialize module" for the others on every command
    out = []
    for i in range(0, len(args) - 1, 2):
        val = args[i + 1]
        if val.startswith("extension_dir=") or val.split("=", 1)[-1] in FRAMEWORK_EXTENSIONS:
            out += args[i:i + 2]
    return out if len(out) > 2 else []


FRAMEWORK_EXTENSIONS = ("pdo_sqlite", "sqlite3", "mbstring", "openssl", "fileinfo", "curl", "intl")


ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def run_php(folder, args: list[str], timeout: int = 120, log=None, php: str = "", stdin: str | None = None
            ) -> tuple[int, str]:
    """Run ``php <args>`` in *folder* (no window) -> (exit code, output without ANSI colours)."""
    php = php or project_php(folder)
    if not php:
        return 127, "PHP was not found"
    argv = [php, *php_ext_args(php), *[str(a) for a in args]]
    if log:
        log("$ " + " ".join(Path(a).name if i == 0 else a for i, a in enumerate(argv)))
    try:
        p = subprocess.run(argv, cwd=str(folder), capture_output=True, timeout=timeout, env=php_env(php),
                           input=(stdin.encode("utf-8") if stdin is not None else None),
                           stdin=None if stdin is not None else subprocess.DEVNULL, creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        return 124, f"php {' '.join(args[:2])} did not finish in {timeout} s"
    except OSError as e:
        return 127, str(e)
    out = ANSI.sub("", (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace"))
    if log:
        for ln in out.splitlines():
            log("  " + ln)
    return p.returncode, out


def run_logged(argv: list[str], cwd, log=None, timeout: int = 1800, env: dict | None = None) -> tuple[int, str]:
    """Run any command streaming its output to *log* line by line -> (exit code, output)."""
    if log:
        log("$ " + " ".join(argv))
    try:
        proc = subprocess.Popen(argv, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, env=env or os.environ.copy(), creationflags=NO_WINDOW)
    except OSError as e:
        if log:
            log(f"*** cannot run {argv[0]}: {e}")
        return 127, str(e)
    lines: list[str] = []
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    try:
        assert proc.stdout is not None
        for raw in iter(proc.stdout.readline, b""):
            line = ANSI.sub("", raw.decode("utf-8", "replace").rstrip())
            lines.append(line)
            if log and line.strip():
                log("  " + line)
        proc.wait()
    finally:
        timer.cancel()
    return proc.returncode, "\n".join(lines)


# ============================================================================ change tracking
def tree_stamp(folder, dirs, exts: tuple[str, ...] = (".php",), files=(), limit: int = 4000) -> tuple:
    """A cheap fingerprint of the files below *dirs* (relative to *folder*) with one of *exts*, plus single
    *files*: changes when a file is added, removed or saved."""
    folder = Path(folder)
    n, latest, size = 0, 0.0, 0
    for d in dirs:
        base = folder / d
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in ("node_modules", "vendor", ".git")]
            for f in filenames:
                if not f.endswith(exts):
                    continue
                try:
                    st = os.stat(os.path.join(dirpath, f))
                except OSError:
                    continue
                n += 1
                latest = max(latest, st.st_mtime)
                size += st.st_size
                if n >= limit:
                    break
    for f in files:
        try:
            st = os.stat(folder / f)
            latest = max(latest, st.st_mtime)
            size += st.st_size
            n += 1
        except OSError:
            pass
    return n, latest, size


class StampCache:
    """value = build() rebuilt only when stamp() changes; stamp() itself is checked at most every
    *interval* seconds (typing must stay fast)."""

    def __init__(self, stamp: Callable[[], tuple], build: Callable[[], object], interval: float = 1.5):
        self._stamp_fn, self._build, self.interval = stamp, build, interval
        self._stamp = None
        self._checked = 0.0
        self._value = None
        self._lock = threading.RLock()

    def get(self):
        with self._lock:
            now = time.monotonic()
            if self._value is None or now - self._checked >= self.interval:
                self._checked = now
                st = self._stamp_fn()
                if st != self._stamp or self._value is None:
                    self._value = self._build()
                    self._stamp = st
            return self._value

    def invalidate(self) -> None:
        with self._lock:
            self._checked = 0.0
            self._stamp = None


def read_text(p) -> str:
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def line_of(text: str, index: int) -> int:
    """1-based line of a character index."""
    return text.count("\n", 0, max(0, index)) + 1


# ============================================================================ PHP source helpers
def string_context(before: str) -> tuple[str, str, str] | None:
    """Cursor inside a string literal of the current line? -> (text before the opening quote, typed prefix,
    quote char); None otherwise. Handles escaped quotes."""
    quote = None
    start = 0
    i = 0
    while i < len(before):
        c = before[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'":
            quote, start = c, i
        elif c == "/" and before[i:i + 2] == "//" and quote is None:
            return None                       # a comment
        i += 1
    if quote is None:
        return None
    return before[:start], before[start + 1:], quote


_CALLEE = re.compile(r"((?:[\\\w]+::|->|\?->)?[A-Za-z_@][\w:\\-]*)\s*$")


def call_context(code_before: str) -> tuple[str, int, str] | None:
    """For the code before a string literal: (callee, argument index, receiver text) of the innermost open call
    ``foo(a, b, '`` -> ("foo", 2, ""); ``Route::has('`` -> ("Route::has", 0, ""); ``$x->where('``
    -> ("->where", 0, "$x"); also ``@include('`` -> ("@include", 0, ""). Array context ``['a' => '`` gives
    ("[", n, key)."""
    depth = 0
    arg = 0
    i = len(code_before) - 1
    in_str = None
    while i >= 0:
        c = code_before[i]
        if in_str:
            if c == in_str and (i == 0 or code_before[i - 1] != "\\"):
                in_str = None
        elif c in "\"'":
            in_str = c
        elif c in ")]}":
            depth += 1
        elif c in "([{":
            if depth == 0:
                if c == "(":
                    m = _CALLEE.search(code_before[:i])
                    if not m:
                        return None
                    callee = m.group(1)
                    recv = code_before[:m.start()].rstrip()
                    return callee, arg, recv
                if c == "[":
                    return "[", arg, code_before[:i]
                return None
            depth -= 1
        elif c == "," and depth == 0:
            arg += 1
        i -= 1
    return None


def array_key_before(code_before: str) -> str | None:
    """``'title' => '`` -> "title" (the key of the array element whose value is being typed)."""
    m = re.search(r"""['"]([\w.*-]+)['"]\s*=>\s*$""", code_before)
    return m.group(1) if m else None


_TOKEN = re.compile(r"""
    (?P<comment>//[^\n]*|\#[^\n]*|/\*.*?\*/)
  | (?P<str>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
  | (?P<arrow>=>)
  | (?P<open>\[|\barray\s*\()
  | (?P<close>\]|\))
  | (?P<popen>\()
  | (?P<comma>,)
""", re.S | re.X)


def parse_php_array(text: str, start_pattern: str = r"\breturn\s*(\[|array\s*\()") -> list[tuple[str, int, bool, str]]:
    """Keys of a PHP array literal (a Laravel / CodeIgniter config or lang file): [(dotted key, 1-based line,
    is_leaf, value preview)]. Tolerant: unknown syntax is skipped, nested arrays give "a.b.c" keys."""
    m = re.search(start_pattern, text)
    if not m:
        return []
    out: list[tuple[str, int, bool, str]] = []
    stack: list[str | None] = []              # key of each open array (None = list / unknown)
    pending_key: str | None = None
    last_str: tuple[str, int] | None = None
    paren = 0                                  # plain ( ) nesting inside values (function calls)
    pos = m.start(1)
    seen_arrow_for: tuple[str, int] | None = None
    value_start = -1
    while True:
        t = _TOKEN.search(text, pos)
        if not t:
            break
        pos = t.end()
        kind = t.lastgroup
        if kind == "comment":
            continue
        if kind == "str":
            last_str = (t.group()[1:-1], t.start())
            continue
        if kind == "arrow":
            if paren == 0 and last_str is not None:
                seen_arrow_for = last_str
                pending_key = last_str[0]
                value_start = t.end()
            last_str = None
            continue
        if kind == "popen":
            paren += 1
            last_str = None
            continue
        if kind == "open":
            if paren and t.group() != "[" and not t.group().startswith("array"):
                paren += 1
                continue
            if paren:
                # an array inside a function call value: skip it entirely
                depth = 1
                while depth and pos < len(text):
                    t2 = _TOKEN.search(text, pos)
                    if not t2:
                        pos = len(text)
                        break
                    pos = t2.end()
                    if t2.lastgroup in ("open", "popen"):
                        depth += 1
                    elif t2.lastgroup == "close":
                        depth -= 1
                continue
            if stack or pending_key is not None:
                key = pending_key
                if key is not None and seen_arrow_for is not None:
                    full = ".".join([k for k in stack if k] + [key]) if None not in stack else None
                    if full:
                        out.append((full, line_of(text, seen_arrow_for[1]), False, "[...]"))
                stack.append(key if key is not None else None)
            else:
                stack.append("")              # the returned array itself
            pending_key = None
            seen_arrow_for = None
            last_str = None
            continue
        if kind == "close":
            if paren:
                paren -= 1
                continue
            _emit_leaf(text, out, stack, pending_key, seen_arrow_for, value_start, t.start())
            pending_key = None
            seen_arrow_for = None
            if not stack:
                break
            stack.pop()
            if not stack:
                break
            last_str = None
            continue
        if kind == "comma":
            if paren:
                continue
            _emit_leaf(text, out, stack, pending_key, seen_arrow_for, value_start, t.start())
            pending_key = None
            seen_arrow_for = None
            last_str = None
    return out


def _emit_leaf(text, out, stack, key, arrow_for, vstart, vend) -> None:
    if key is None or arrow_for is None or None in stack:
        return
    full = ".".join([k for k in stack if k] + [key])
    preview = " ".join(text[vstart:vend].split())[:80] if vstart >= 0 else ""
    out.append((full, line_of(text, arrow_for[1]), True, preview))


def parse_env(path) -> list[tuple[str, str, int]]:
    """[(KEY, value, 1-based line)] of a .env file."""
    out = []
    for n, line in enumerate(read_text(path).splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k = k.strip()
        if k.startswith("export "):
            k = k[7:].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", k):
            out.append((k, v.strip().strip('"').strip("'"), n))
    return out


def psr4_map(folder) -> list[tuple[str, Path]]:
    """[(namespace prefix with trailing backslash, absolute folder)] from composer.json autoload(-dev)."""
    data = composer_json(folder)
    out = []
    for sec in ("autoload", "autoload-dev"):
        for ns, dirs in ((data.get(sec) or {}).get("psr-4") or {}).items():
            for d in ([dirs] if isinstance(dirs, str) else dirs or []):
                out.append((ns, (Path(folder) / d).resolve()))
    out.sort(key=lambda x: -len(x[0]))
    return out


def class_file(folder, fqcn: str) -> Path | None:
    """The file of a project class (PSR-4 of composer.json), None when unknown / not in the project."""
    fqcn = fqcn.lstrip("\\")
    for ns, base in psr4_map(folder):
        if fqcn.startswith(ns):
            p = base / (fqcn[len(ns):].replace("\\", "/") + ".php")
            if p.is_file():
                return p
    return None


def class_of_file(folder, path) -> str:
    p = Path(path).resolve()
    for ns, base in psr4_map(folder):
        try:
            r = p.relative_to(base).with_suffix("")
        except ValueError:
            continue
        return ns + "\\".join(r.parts)
    return ""


def method_line(path, method: str) -> int:
    text = read_text(path)
    m = re.search(rf"function\s+&?\s*{re.escape(method)}\s*\(", text)
    return line_of(text, m.start()) if m else 1


def uses_of(text: str) -> dict[str, str]:
    """``use App\\Models\\Post;`` / ``use X as Y;`` lines -> {short name: FQCN}."""
    out = {}
    for m in re.finditer(r"^\s*use\s+([\\\w]+)(?:\s+as\s+(\w+))?\s*;", text, re.M):
        fq = m.group(1).lstrip("\\")
        out[m.group(2) or fq.rsplit("\\", 1)[-1]] = fq
    return out


def namespace_of(text: str) -> str:
    m = re.search(r"^\s*namespace\s+([\\\w]+)\s*;", text, re.M)
    return m.group(1) if m else ""


# ============================================================================ names
def snake(name: str) -> str:
    s = re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", name)
    s = re.sub(r"(?<=[A-Z])([A-Z][a-z])", r"_\1", s)
    return s.lower()


def studly(name: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[_\-\s.]+", name) if p)


def camel(name: str) -> str:
    s = studly(name)
    return s[:1].lower() + s[1:]


_IRREGULAR = {"person": "people", "man": "men", "woman": "women", "child": "children", "mouse": "mice",
              "goose": "geese", "foot": "feet", "tooth": "teeth", "ox": "oxen", "datum": "data"}
_UNCOUNTABLE = {"equipment", "information", "rice", "money", "species", "series", "fish", "sheep", "news",
                "feedback", "metadata", "data", "media"}


def plural(word: str) -> str:
    """English plural as Laravel's Str::plural does it for table names (good enough for snake_case)."""
    head, _, last = word.rpartition("_")
    low = last.lower()
    if low in _UNCOUNTABLE:
        p = last
    elif low in _IRREGULAR:
        p = _IRREGULAR[low]
    elif re.search(r"[^aeiou]y$", low):
        p = last[:-1] + "ies"
    elif re.search(r"(s|x|z|ch|sh)$", low):
        p = last + "es"
    elif re.search(r"(?:[^f]fe|[lr]f)$", low):
        p = re.sub(r"fe?$", "ves", last)
    else:
        p = last + "s"
    return (head + "_" if head else "") + p


def singular(word: str) -> str:
    low = word.lower()
    inv = {v: k for k, v in _IRREGULAR.items()}
    if low in _UNCOUNTABLE:
        return word
    if low in inv:
        return inv[low]
    if low.endswith("ies") and len(low) > 3:
        return word[:-3] + "y"
    if re.search(r"(ss|x|z|ch|sh)es$", low):
        return word[:-2]
    if low.endswith("ves"):
        return word[:-3] + "f"
    if low.endswith("s") and not low.endswith("ss"):
        return word[:-1]
    return word


# ============================================================================ completion items
def item(label: str, kind: int = K_TEXT, detail: str = "", documentation: str = "", insert: str | None = None,
         rng: list[int] | None = None, sort: str | None = None, snippet: bool = False,
         filter_text: str | None = None) -> dict:
    """A completion item as monaco_editor.py / editor.html expect it (range = [l1, c1, l2, c2], 0-based)."""
    d = {"label": label, "kind": kind, "detail": detail, "documentation": documentation,
         "insertText": label if insert is None else insert, "range": rng, "snippet": snippet,
         "sortText": sort, "filterText": filter_text, "additionalTextEdits": []}
    return d


def string_range(line: int, col: int, typed: str) -> list[int]:
    """Range of the text typed so far inside a string literal (so 'app.na' is replaced by 'app.name')."""
    return [line, col - len(typed), line, col]


__all__ = ["FRAMEWORKS", "PhpFramework", "StampCache", "array_key_before", "call_context", "camel", "class_file",
           "class_of_file", "composer_json", "composer_requires", "framework_module", "framework_of",
           "frameworks", "item", "line_of", "method_line", "namespace_of", "parse_env", "parse_php_array",
           "php_env", "php_ext_args", "plural", "project_php", "project_root_of", "psr4_map", "radproj_web", "read_text",
           "register_framework", "router_for", "run_logged", "run_php", "singular", "snake", "string_context",
           "string_range", "studly", "tree_stamp", "uses_of"]
