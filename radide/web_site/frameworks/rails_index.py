"""Ruby on Rails IntelliSense read from the project (engine, no Qt) - the IDE part is ``radide/features/rails_ide.py``.

``index(folder)`` returns a :class:`RailsIndex` that is rebuilt piece by piece when the project's files change
(``StampCache``: a cheap fingerprint of the watched folders, checked at most every 1.5 s):

- **routes**: ``bin/rails routes`` (run in a background thread, cached per ``config/routes.rb`` stamp in memory
  and in ``tmp/cache/radide-routes.txt``), ``config/routes.rb`` parsed directly until then -> ``*_path`` /
  ``*_url`` helpers with their verb, path and controller action;
- **schema**: ``db/schema.rb`` (``create_table`` blocks), else the SQLite database (``storage/*.sqlite3``), else
  the migrations -> the columns of every table;
- **models** (``app/models``): associations (has_many / belongs_to / has_one / habtm, ``class_name:``), scopes,
  enums, methods, validations' columns;
- **controllers** (``app/controllers``): actions and the instance variables each action assigns (so a view
  ``products/index.html.erb`` completes ``@products`` and knows it is a collection of ``Product``);
- **views** / partials (``app/views``), **locale keys** (``config/locales/*.yml``), **ENV** keys (``.env*``,
  ``ENV[...]`` uses in config), **helpers** (``app/helpers``).

``complete_items(folder, path, text, line, col)`` -> Monaco completion items (``None`` = nothing Rails-specific
here, the language server answers alone) and ``definition(folder, path, text, line, col)`` -> ``(file, line)``.
"""
from __future__ import annotations

import os
import re
import sqlite3
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .common import (K_CLASS, K_CONSTANT, K_FIELD, K_FILE, K_FUNCTION, K_KEYWORD, K_METHOD, K_PROPERTY,
                     K_VALUE, K_VARIABLE, StampCache, item, tree_stamp)

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ============================================================================ inflections (the common cases)
_IRREGULAR = {"person": "people", "man": "men", "woman": "women", "child": "children", "sex": "sexes",
              "move": "moves", "zombie": "zombies", "ox": "oxen", "mouse": "mice", "goose": "geese",
              "foot": "feet", "tooth": "teeth", "quiz": "quizzes"}
_UNCOUNTABLE = {"equipment", "information", "rice", "money", "species", "series", "fish", "sheep", "jeans",
                "police", "news", "data", "metadata"}


def pluralize(word: str) -> str:
    w = word or ""
    low = w.lower()
    if not w or low in _UNCOUNTABLE:
        return w
    for s, p in _IRREGULAR.items():
        if low.endswith(s):
            return w[:len(w) - len(s)] + p
    if re.search(r"(s|x|z|ch|sh)$", low):
        return w + "es"
    if re.search(r"[^aeiou]y$", low):
        return w[:-1] + "ies"
    if re.search(r"(?:([^f])fe|([lr])f)$", low):
        return re.sub(r"(?:([^f])fe|([lr])f)$", lambda m: (m.group(1) or m.group(2)) + "ves", w)
    return w + "s"


def singularize(word: str) -> str:
    w = word or ""
    low = w.lower()
    if not w or low in _UNCOUNTABLE:
        return w
    for s, p in _IRREGULAR.items():
        if low.endswith(p):
            return w[:len(w) - len(p)] + s
    for pat, rep in ((r"([^aeiou])ies$", r"\1y"), (r"(ss)es$", r"\1"), (r"(x|z|ch|sh)es$", r"\1"),
                     (r"([lr])ves$", r"\1f"), (r"([^f])ves$", r"\1fe"), (r"(us|ss|is)$", r"\1"), (r"s$", "")):
        if re.search(pat, w, re.I):
            return re.sub(pat, rep, w, flags=re.I)
    return w


def camelize(s: str) -> str:
    """"line_items" -> "LineItems", "admin/users" -> "Admin::Users"."""
    return "::".join("".join(p[:1].upper() + p[1:] for p in part.split("_") if p) for part in s.split("/"))


def underscore(s: str) -> str:
    """"LineItem" -> "line_item", "Admin::User" -> "admin/user"."""
    s = s.replace("::", "/")
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return s.replace("-", "_").lower()


def model_for_table(table: str) -> str:
    return camelize(singularize(table))


def table_for_model(model: str) -> str:
    return pluralize(underscore(model).replace("/", "_"))


# ============================================================================ small helpers
def read_text(p) -> str:
    try:
        return Path(p).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def is_rails(folder) -> bool:
    f = Path(folder)
    return (f / "config" / "application.rb").is_file() and (f / "Gemfile").is_file()


def rails_root_of(path) -> Path | None:
    """The Rails application folder that contains *path* (walks up to config/application.rb)."""
    try:
        p = Path(path).resolve()
    except OSError:
        return None
    for d in [p] + list(p.parents):
        if (d / "config" / "application.rb").is_file() and (d / "Gemfile").is_file():
            return d
        if (d / "project.radproj").is_file() or (d / ".git").exists():
            return None
    return None


def _stamp_files(folder: Path, rels) -> tuple:
    out = []
    for r in rels:
        try:
            st = (folder / r).stat()
            out.append((r, st.st_mtime, st.st_size))
        except OSError:
            out.append((r, 0, 0))
    return tuple(out)


@dataclass
class Assoc:
    kind: str           # has_many | belongs_to | has_one | has_and_belongs_to_many
    name: str
    target: str         # class name
    line: int

    @property
    def many(self) -> bool:
        return self.kind in ("has_many", "has_and_belongs_to_many")


@dataclass
class Model:
    name: str
    file: Path
    line: int
    table: str
    parent: str = ""
    assocs: dict = field(default_factory=dict)        # name -> Assoc
    scopes: dict = field(default_factory=dict)        # name -> line
    methods: dict = field(default_factory=dict)       # instance method -> line
    class_methods: dict = field(default_factory=dict)
    enums: dict = field(default_factory=dict)         # attribute -> [values]
    attributes: dict = field(default_factory=dict)    # attribute :x / attr_accessor -> line


@dataclass
class Controller:
    name: str           # "ProductsController"
    path: str           # "products", "admin/users"
    file: Path
    line: int
    actions: dict = field(default_factory=dict)       # action -> line (public methods)
    private: dict = field(default_factory=dict)       # private / protected methods -> line
    ivars: dict = field(default_factory=dict)         # action -> {"@x": (line, expr)}


@dataclass
class RouteInfo:
    verb: str
    path: str
    handler: str        # "products#show"
    name: str = ""      # "product" (helper prefix)
    file: str = ""
    line: int = 0


# ============================================================================ routes
_ROUTES_LINE = re.compile(r"^\s*(?:(\w+)\s+)?((?:GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD|LINK|UNLINK)(?:\|\w+)*)\s+"
                          r"(\S+)\s+(\S.*?)\s*$")


def parse_routes_output(text: str) -> list[RouteInfo]:
    out = []
    for raw in text.splitlines():
        if "Prefix" in raw and "Verb" in raw:
            continue
        m = _ROUTES_LINE.match(raw)
        if not m:
            continue
        name, verb, path, handler = m.groups()
        handler = handler.split(" ", 1)[0]
        out.append(RouteInfo(verb, path.replace("(.:format)", ""), handler, name or ""))
    return out


def parse_routes_file(folder: Path) -> list[RouteInfo]:
    """config/routes.rb read directly (no Rails): resources / resource (only / except, one nesting level),
    root, get "x" => "c#a", get "x", to: "c#a", as: :name, namespace."""
    f = folder / "config" / "routes.rb"
    text = read_text(f)
    out: list[RouteInfo] = []
    ns_stack: list[tuple[int, str]] = []      # (indent, namespace)
    parent_stack: list[tuple[int, str]] = []  # (indent, parent resource) for nested resources
    for i, raw in enumerate(text.splitlines(), 1):
        s = raw.split("#", 1)[0] if not re.search(r"['\"][^'\"]*#", raw) else raw
        st = s.strip()
        if not st or st.startswith("#"):
            continue
        ind = len(raw) - len(raw.lstrip())
        while ns_stack and ind <= ns_stack[-1][0] and st.startswith("end"):
            ns_stack.pop()
            break
        while parent_stack and ind <= parent_stack[-1][0] and st.startswith("end"):
            parent_stack.pop()
            break
        ns = "/".join(n for _i, n in ns_stack)
        nsp = (ns.replace("/", "_") + "_") if ns else ""
        m = re.match(r"namespace\s+:(\w+)\s+do", st)
        if m:
            ns_stack.append((ind, m.group(1)))
            continue
        m = re.match(r"root\s+(?:to:\s*)?['\"]([\w/]+#\w+)['\"]", st)
        if m:
            out.append(RouteInfo("GET", "/" + ns, m.group(1), nsp + "root", str(f), i))
            continue
        m = re.match(r"(get|post|put|patch|delete|match)\s+['\"]([^'\"]+)['\"]\s*(?:=>\s*['\"]([\w/]+#\w+)['\"]|,\s*"
                     r"to:\s*['\"]([\w/]+#\w+)['\"])?(.*)$", st)
        if m:
            verb, p, h1, h2, rest = m.groups()
            path = "/" + "/".join(x for x in (ns, p.strip("/")) if x)
            handler = h1 or h2 or (p.strip("/").replace("/", "#") if "/" in p.strip("/") else "")
            if handler and ns and "/" not in handler.split("#")[0]:
                handler = ns + "/" + handler
            asm = re.search(r"as:\s*[:'\"](\w+)", rest or "")
            name = asm.group(1) if asm else re.sub(r"\W+", "_", p.strip("/").split(":")[0]).strip("_")
            out.append(RouteInfo(verb.upper() if verb != "match" else "GET", path, handler,
                                 (nsp + name) if name else "", str(f), i))
            continue
        m = re.match(r"(resources?)\s+:(\w+)(.*)$", st)
        if m:
            single = m.group(1) == "resource"
            res, rest = m.group(2), m.group(3)
            actions = ["index", "create", "new", "edit", "show", "update", "destroy"]
            if single:
                actions.remove("index")
            only = re.search(r"only:\s*(?:\[([^\]]*)\]|:(\w+))", rest)
            if only:
                actions = re.findall(r":?(\w+)", only.group(1) or only.group(2))
            exc = re.search(r"except:\s*(?:\[([^\]]*)\]|:(\w+))", rest)
            if exc:
                ex = set(re.findall(r":?(\w+)", exc.group(1) or exc.group(2)))
                actions = [a for a in actions if a not in ex]
            sing = singularize(res) if not single else res
            parent = parent_stack[-1][1] if parent_stack else ""
            pbase, pname = "", ""
            if parent:
                pbase = f"/{parent}/:{singularize(parent)}_id"
                pname = singularize(parent) + "_"
            base = "/" + "/".join(x for x in (ns, pbase.strip("/"), res) if x)
            ctrl = (ns + "/" if ns else "") + (pluralize(res) if single else res)
            table = {"index": ("GET", base, nsp + pname + res),
                     "create": ("POST", base, ""),
                     "new": ("GET", f"{base}/new", "new_" + nsp + pname + sing),
                     "show": ("GET", base if single else f"{base}/:id", nsp + (pname if single else "") + sing),
                     "edit": ("GET", f"{base}/edit" if single else f"{base}/:id/edit", "edit_" + nsp + sing),
                     "update": ("PATCH", base if single else f"{base}/:id", ""),
                     "destroy": ("DELETE", base if single else f"{base}/:id", "")}
            if single:
                table["index"] = ("GET", base, "")
            for a in actions:
                if a in table:
                    verb, path, helper = table[a]
                    out.append(RouteInfo(verb, path, f"{ctrl}#{a}", helper, str(f), i))
            if re.search(r"\bdo\s*$", st):
                parent_stack.append((ind, res))
            continue
    return out


# ============================================================================ schema
def parse_schema_rb(path: Path) -> dict[str, dict]:
    """db/schema.rb -> {table: {"line": n, "columns": {col: (type, line)}}}."""
    text = read_text(path)
    out: dict[str, dict] = {}
    cur = None
    for i, raw in enumerate(text.splitlines(), 1):
        m = re.match(r"\s*create_table\s+['\"](\w+)['\"](.*)do\s*\|\w+\|", raw)
        if m:
            cur = {"line": i, "columns": {}}
            out[m.group(1)] = cur
            if "id: false" not in m.group(2):
                cur["columns"]["id"] = ("integer", i)
            continue
        if cur is None:
            continue
        if re.match(r"\s*end\b", raw):
            cur = None
            continue
        m = re.match(r"\s*t\.(\w+)\s+['\"](\w+)['\"]", raw)
        if m:
            typ, col = m.groups()
            if typ in ("references", "belongs_to"):
                cur["columns"][col + "_id"] = ("integer", i)
            elif typ == "index":
                continue
            else:
                cur["columns"][col] = (typ, i)
            continue
        if re.match(r"\s*t\.timestamps", raw):
            cur["columns"]["created_at"] = ("datetime", i)
            cur["columns"]["updated_at"] = ("datetime", i)
    return out


def parse_migrations(folder: Path) -> dict[str, dict]:
    """The tables made / changed by db/migrate/*.rb (when there is no schema.rb yet)."""
    out: dict[str, dict] = {}
    mig = folder / "db" / "migrate"
    files = sorted(mig.glob("*.rb")) if mig.is_dir() else []
    for f in files:
        text = read_text(f)
        cur = None
        for i, raw in enumerate(text.splitlines(), 1):
            m = re.match(r"\s*create_table\s+:?['\"]?(\w+)['\"]?(.*)do\s*\|\w+\|", raw)
            if m:
                cur = out.setdefault(m.group(1), {"line": i, "file": str(f), "columns": {}})
                if "id: false" not in m.group(2):
                    cur["columns"].setdefault("id", ("integer", i))
                continue
            m = re.match(r"\s*add_column\s+:(\w+),\s*:(\w+),\s*:(\w+)", raw)
            if m:
                out.setdefault(m.group(1), {"line": i, "file": str(f), "columns": {}})["columns"][m.group(2)] = \
                    (m.group(3), i)
                continue
            m = re.match(r"\s*add_reference\s+:(\w+),\s*:(\w+)", raw)
            if m:
                out.setdefault(m.group(1), {"line": i, "file": str(f), "columns": {}})["columns"][m.group(2) + "_id"] = \
                    ("integer", i)
                continue
            m = re.match(r"\s*remove_column\s+:(\w+),\s*:(\w+)", raw)
            if m and m.group(1) in out:
                out[m.group(1)]["columns"].pop(m.group(2), None)
                continue
            m = re.match(r"\s*drop_table\s+:(\w+)", raw)
            if m:
                out.pop(m.group(1), None)
                continue
            if cur is None:
                continue
            if re.match(r"\s*end\b", raw):
                cur = None
                continue
            m = re.match(r"\s*t\.(\w+)\s+:?['\"]?(\w+)", raw)
            if m:
                typ, col = m.groups()
                if typ in ("references", "belongs_to"):
                    cur["columns"][col + "_id"] = ("integer", i)
                elif typ == "timestamps":
                    cur["columns"]["created_at"] = ("datetime", i)
                    cur["columns"]["updated_at"] = ("datetime", i)
                elif typ != "index":
                    cur["columns"][col] = (typ, i)
            elif re.match(r"\s*t\.timestamps", raw):
                cur["columns"]["created_at"] = ("datetime", i)
                cur["columns"]["updated_at"] = ("datetime", i)
    return out


def sqlite_schema(db: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=1)
    except sqlite3.Error:
        return out
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE "
                                            "'sqlite_%' AND name NOT IN ('schema_migrations', "
                                            "'ar_internal_metadata')")]
        for t in tables:
            cols = {r[1]: ((r[2] or "").lower(), 0) for r in con.execute(f'PRAGMA table_info("{t}")')}
            out[t] = {"line": 0, "columns": cols}
    except sqlite3.Error:
        pass
    finally:
        con.close()
    return out


# ============================================================================ YAML keys (locales) - no PyYAML
def yaml_keys(path: Path) -> list[tuple[str, str, int]]:
    """Dotted keys of a simple YAML file: [(key, value, line)] (leaf keys only; block scalars skipped)."""
    out = []
    stack: list[tuple[int, str]] = []
    block_indent = None
    for i, raw in enumerate(read_text(path).splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        ind = len(raw) - len(raw.lstrip(" "))
        if block_indent is not None:
            if ind > block_indent:
                continue
            block_indent = None
        m = re.match(r"\s*(['\"]?)([^'\":#][^:]*?|[^:]+?)\1\s*:(?:\s+(.*))?$", raw)
        if not m or raw.lstrip().startswith("- "):
            continue
        key, val = m.group(2).strip(), (m.group(3) or "").strip()
        while stack and stack[-1][0] >= ind:
            stack.pop()
        if val and not val.startswith("#") and val not in ("|", ">", "|-", ">-"):
            out.append((".".join([k for _i, k in stack] + [key]), val.strip("'\""), i))
        else:
            if val in ("|", ">", "|-", ">-"):
                out.append((".".join([k for _i, k in stack] + [key]), "", i))
                block_indent = ind
                continue
            stack.append((ind, key))
    return out


# ============================================================================ Rails API lists (for receivers)
AR_CLASS_METHODS = [
    ("all", "ActiveRecord::Relation"), ("find", "find(id) -> record"), ("find_by", "find_by(attr: value) -> record | nil"),
    ("find_by!", "find_by!(...) -> record"), ("where", "where(...) -> Relation"), ("where.not", "Relation"),
    ("order", "order(:col) -> Relation"), ("limit", "Relation"), ("offset", "Relation"), ("first", "record"),
    ("last", "record"), ("take", "record"), ("count", "Integer"), ("exists?", "Boolean"), ("pluck", "Array"),
    ("ids", "Array"), ("new", "new(attrs) -> record"), ("create", "create(attrs) -> record"),
    ("create!", "create!(attrs) -> record"), ("find_or_create_by", "record"), ("find_or_initialize_by", "record"),
    ("includes", "Relation"), ("joins", "Relation"), ("left_joins", "Relation"), ("preload", "Relation"),
    ("eager_load", "Relation"), ("select", "Relation"), ("group", "Relation"), ("having", "Relation"),
    ("distinct", "Relation"), ("none", "Relation"), ("sum", "Numeric"), ("average", "Numeric"),
    ("minimum", "value"), ("maximum", "value"), ("update_all", "Integer"), ("delete_all", "Integer"),
    ("destroy_all", "Array"), ("find_each", "batches"), ("find_in_batches", "batches"), ("in_batches", "batches"),
    ("sole", "record"), ("table_name", "String"), ("column_names", "Array"), ("columns_hash", "Hash"),
    ("human_attribute_name", "String"), ("model_name", "ActiveModel::Name"), ("transaction", "block"),
    ("insert_all", "result"), ("upsert_all", "result"), ("reorder", "Relation"), ("rewhere", "Relation"),
    ("unscoped", "Relation"), ("lock", "Relation"), ("readonly", "Relation"), ("find_sole_by", "record"),
]
RELATION_METHODS = [(n, d) for n, d in AR_CLASS_METHODS if n not in ("new", "table_name", "column_names",
                                                                       "columns_hash", "human_attribute_name",
                                                                       "model_name", "transaction")] + [
    ("each", "each { |record| }"), ("map", "Array"), ("each_with_index", "block"), ("to_a", "Array"),
    ("size", "Integer"), ("length", "Integer"), ("empty?", "Boolean"), ("any?", "Boolean"), ("many?", "Boolean"),
    ("build", "build(attrs) -> record"), ("load", "Relation"), ("reload", "Relation"), ("select", "Relation"),
    ("find_all", "Array"), ("filter_map", "Array"), ("group_by", "Hash"), ("index_by", "Hash"),
    ("in_order_of", "Relation"), ("excluding", "Relation"), ("sort_by", "Array"), ("present?", "Boolean"),
]
AR_INSTANCE_METHODS = [
    ("save", "Boolean"), ("save!", "true"), ("update", "update(attrs) -> Boolean"), ("update!", "true"),
    ("destroy", "record"), ("destroy!", "record"), ("delete", "record"), ("reload", "record"),
    ("persisted?", "Boolean"), ("new_record?", "Boolean"), ("destroyed?", "Boolean"), ("changed?", "Boolean"),
    ("changes", "Hash"), ("errors", "ActiveModel::Errors"), ("valid?", "Boolean"), ("invalid?", "Boolean"),
    ("attributes", "Hash"), ("assign_attributes", "assign_attributes(attrs)"), ("to_param", "String"),
    ("touch", "Boolean"), ("increment!", "record"), ("decrement!", "record"), ("toggle!", "record"),
    ("update_column", "Boolean"), ("update_columns", "Boolean"), ("previous_changes", "Hash"),
    ("saved_changes", "Hash"), ("as_json", "Hash"), ("to_json", "String"), ("dup", "record"),
    ("attribute_names", "Array"), ("read_attribute", "value"), ("write_attribute", "value"),
    ("model_name", "ActiveModel::Name"), ("lock!", "record"), ("with_lock", "block"), ("present?", "Boolean"),
]
VIEW_HELPERS = [
    "link_to", "button_to", "form_with", "form_for", "fields_for", "image_tag", "stylesheet_link_tag",
    "javascript_include_tag", "javascript_importmap_tags", "content_tag", "tag", "render", "yield", "content_for",
    "content_for?", "provide", "pluralize", "truncate", "simple_format", "number_to_currency", "number_with_delimiter",
    "number_to_percentage", "number_to_human_size", "time_ago_in_words", "distance_of_time_in_words", "l", "t",
    "raw", "sanitize", "strip_tags", "h", "j", "dom_id", "dom_class", "csrf_meta_tags", "csp_meta_tag",
    "turbo_frame_tag", "turbo_stream_from", "notice", "alert", "flash", "params", "request", "session", "cookies",
    "current_page?", "url_for", "mail_to", "cycle", "debug", "asset_path", "image_path", "options_for_select",
    "collection_select", "select_tag", "text_field_tag", "submit_tag", "label_tag", "hidden_field_tag",
    "check_box_tag", "safe_join", "concat", "capture", "excerpt", "highlight", "word_wrap", "auto_discovery_link_tag",
    "favicon_link_tag", "preload_link_tag", "action_name", "controller_name", "controller_path",
]
CONTROLLER_METHODS = [
    "render", "redirect_to", "redirect_back", "redirect_back_or_to", "head", "params", "session", "cookies", "flash",
    "request", "response", "respond_to", "before_action", "after_action", "around_action", "skip_before_action",
    "rescue_from", "helper_method", "protect_from_forgery", "send_file", "send_data", "action_name",
    "controller_name", "url_for", "allow_browser", "stale_when_importmap_changes", "authenticate_or_request_with_http_basic",
    "http_basic_authenticate_with", "layout", "default_url_options",
]
MODEL_DSL = [
    "has_many", "belongs_to", "has_one", "has_and_belongs_to_many", "validates", "validate", "validates_presence_of",
    "validates_uniqueness_of", "scope", "enum", "before_save", "after_save", "before_create", "after_create",
    "before_validation", "after_commit", "after_create_commit", "after_update_commit", "after_destroy_commit",
    "before_destroy", "after_initialize", "has_secure_password", "has_one_attached", "has_many_attached",
    "has_rich_text", "attribute", "delegate", "accepts_nested_attributes_for", "default_scope", "store_accessor",
    "normalizes", "generates_token_for", "encrypts", "serialize", "broadcasts_to", "counter_cache",
]
RAILS_ENV_KEYS = ["RAILS_ENV", "RAILS_MASTER_KEY", "DATABASE_URL", "PORT", "RAILS_MAX_THREADS",
                  "WEB_CONCURRENCY", "RAILS_LOG_LEVEL", "RAILS_SERVE_STATIC_FILES", "SECRET_KEY_BASE", "REDIS_URL",
                  "PIDFILE", "JOB_CONCURRENCY", "SOLID_QUEUE_IN_PUMA", "CI"]
INSTANCE_RETURNING = {"find", "find_by", "find_by!", "first", "last", "take", "sole", "new", "create", "create!",
                      "build", "find_or_create_by", "find_or_initialize_by", "find_sole_by", "first!", "last!",
                      "second", "third", "reload", "dup", "find_or_create_by!"}
RELATION_RETURNING = {"all", "where", "order", "limit", "offset", "includes", "joins", "left_joins", "preload",
                      "eager_load", "select", "group", "having", "distinct", "none", "reorder", "rewhere",
                      "unscoped", "not", "lock", "readonly", "load", "excluding", "in_order_of", "page", "per",
                      "recent", "sort_by", "to_a", "filter", "reject"}


# ============================================================================ the index
_INDEXES: dict[str, "RailsIndex"] = {}
_LOCK = threading.Lock()


def index(folder) -> "RailsIndex":
    key = os.path.normcase(str(Path(folder).resolve()))
    with _LOCK:
        idx = _INDEXES.get(key)
        if idx is None:
            idx = _INDEXES[key] = RailsIndex(Path(folder).resolve())
        return idx


class RailsIndex:
    def __init__(self, folder: Path):
        self.folder = folder
        f = folder
        self._schema = StampCache(lambda: _stamp_files(f, ["db/schema.rb", "storage/development.sqlite3",
                                                           "db/development.sqlite3"]) +
                                  tree_stamp(f, ["db/migrate"], (".rb",)), self._build_schema)
        self._models = StampCache(lambda: tree_stamp(f, ["app/models"], (".rb",)), self._build_models)
        self._controllers = StampCache(lambda: tree_stamp(f, ["app/controllers"], (".rb",)), self._build_controllers)
        self._views = StampCache(lambda: tree_stamp(f, ["app/views"], (".erb", ".haml", ".slim", ".jbuilder",
                                                                       ".builder", ".turbo_stream.erb")),
                                 self._build_views)
        self._locales = StampCache(lambda: tree_stamp(f, ["config/locales"], (".yml", ".yaml")),
                                   self._build_locales)
        self._env = StampCache(lambda: _stamp_files(f, [".env", ".env.development", ".env.local", ".env.example"]) +
                               tree_stamp(f, ["config"], (".rb", ".yml")), self._build_env)
        self._helpers = StampCache(lambda: tree_stamp(f, ["app/helpers"], (".rb",)), self._build_helpers)
        self._file_routes = StampCache(self.routes_stamp, lambda: parse_routes_file(f))
        self._runtime_routes: list[RouteInfo] | None = None
        self._runtime_stamp = None
        self._routes_thread: threading.Thread | None = None
        self.routes_listeners: list = []           # callables(index) when runtime routes arrive
        self.last_routes_error = ""
        self._load_routes_cache()

    # ------------------------------------------------------------ routes
    def routes_stamp(self) -> tuple:
        rels = ["config/routes.rb"]
        d = self.folder / "config" / "routes"
        if d.is_dir():
            rels += [str(p.relative_to(self.folder)) for p in d.glob("*.rb")]
        return _stamp_files(self.folder, rels)

    def _cache_file(self) -> Path:
        return self.folder / "tmp" / "cache" / "radide-routes.txt"

    def _load_routes_cache(self) -> None:
        text = read_text(self._cache_file())
        if not text.startswith("#stamp "):
            return
        head, _, body = text.partition("\n")
        if head[7:] == repr(self.routes_stamp()):
            self._runtime_routes = parse_routes_output(body)
            self._runtime_stamp = self.routes_stamp()

    def routes(self, refresh: bool = True) -> list[RouteInfo]:
        """Runtime routes when they are current, else the routes.rb parse (and a refresh starts)."""
        stamp = self.routes_stamp()
        if self._runtime_routes is not None and self._runtime_stamp == stamp:
            return self._runtime_routes
        if refresh:
            self.refresh_routes()
        return self._file_routes.get()

    def can_run_rails(self) -> bool:
        f = self.folder
        return (f / "bin" / "rails").is_file() and (f / "Gemfile.lock").is_file() and \
            ((f / "vendor" / "bundle").is_dir() or not (f / ".bundle" / "config").is_file())

    def refresh_routes(self, wait: bool = False) -> None:
        """Run ``bin/rails routes`` in a thread (once per routes.rb stamp)."""
        if self._routes_thread is not None and self._routes_thread.is_alive():
            if wait:
                self._routes_thread.join(180)
            return
        stamp = self.routes_stamp()
        if self._runtime_stamp == stamp or not self.can_run_rails():
            return
        self._runtime_stamp = stamp                # do not start again for the same stamp

        def work():
            try:
                from .rails import ruby_env, ruby_exe
                ruby = ruby_exe()
                if not ruby:
                    return
                env = dict(os.environ)
                env.update(ruby_env(self.folder))
                env["DISABLE_SPRING"] = "1"
                r = subprocess.run([ruby, "bin/rails", "routes"], cwd=str(self.folder), env=env,
                                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                                   timeout=180, creationflags=NO_WINDOW, stdin=subprocess.DEVNULL)
                routes = parse_routes_output(r.stdout or "")
                if r.returncode != 0 or not routes:
                    self.last_routes_error = (r.stderr or r.stdout or "")[-2000:]
                    return
                self.last_routes_error = ""
                self._runtime_routes = routes
                try:
                    cf = self._cache_file()
                    cf.parent.mkdir(parents=True, exist_ok=True)
                    cf.write_text(f"#stamp {stamp!r}\n" + (r.stdout or ""), encoding="utf-8")
                except OSError:
                    pass
                for fn in list(self.routes_listeners):
                    try:
                        fn(self)
                    except Exception:  # noqa: BLE001
                        pass
            except (OSError, subprocess.SubprocessError) as e:
                self.last_routes_error = str(e)
        t = threading.Thread(target=work, daemon=True, name="rails-routes")
        self._routes_thread = t
        t.start()
        if wait:
            t.join(180)

    def route_helpers(self) -> list[tuple[str, RouteInfo]]:
        """[("products_path", route), ("products_url", route) ...] (named routes only, internal ones last)."""
        out = []
        seen = set()
        for r in self.routes():
            if not r.name or r.name in seen:
                continue
            seen.add(r.name)
            out.append((r.name + "_path", r))
            out.append((r.name + "_url", r))
        internal = ("rails_", "turbo_", "active_storage", "action_mailbox", "new_rails_", "edit_rails_",
                    "update_rails_", "rails_conductor")
        out.sort(key=lambda t: (t[0].startswith(internal), 0))
        return out

    def route_target(self, r: RouteInfo) -> tuple[str, int] | None:
        """Controller action file / line of a route (else the routes.rb line)."""
        if "#" in r.handler:
            ctrl, action = r.handler.split("#", 1)
            c = self.controllers().get(ctrl)
            if c is not None:
                return str(c.file), c.actions.get(action) or c.private.get(action) or c.line
        for fr in self._file_routes.get():
            if fr.handler == r.handler or (r.name and fr.name == r.name):
                return fr.file, fr.line
        f = self.folder / "config" / "routes.rb"
        return (str(f), 1) if f.is_file() else None

    # ------------------------------------------------------------ schema
    def schema(self) -> dict[str, dict]:
        return self._schema.get()

    def _build_schema(self) -> dict[str, dict]:
        f = self.folder
        sch = f / "db" / "schema.rb"
        if sch.is_file():
            out = parse_schema_rb(sch)
            for t in out.values():
                t["file"] = str(sch)
            if out:
                return out
        for db in (f / "storage" / "development.sqlite3", f / "db" / "development.sqlite3"):
            if db.is_file() and db.stat().st_size > 0:
                out = sqlite_schema(db)
                if out:
                    mig = parse_migrations(f)
                    for t, info in out.items():          # lines from the migrations when possible
                        m = mig.get(t)
                        info["file"] = m.get("file", "") if m else ""
                        if m:
                            info["line"] = m["line"]
                            info["columns"] = {c: (typ, m["columns"].get(c, ("", 0))[1])
                                               for c, (typ, _l) in info["columns"].items()}
                    return out
        return parse_migrations(f)

    def columns(self, model: str) -> dict[str, tuple]:
        m = self.models().get(model)
        table = m.table if m is not None else table_for_model(model)
        return (self.schema().get(table) or {}).get("columns", {})

    # ------------------------------------------------------------ models
    def models(self) -> dict[str, Model]:
        return self._models.get()

    def _build_models(self) -> dict[str, Model]:
        out: dict[str, Model] = {}
        root = self.folder / "app" / "models"
        if not root.is_dir():
            return out
        for f in sorted(root.rglob("*.rb")):
            if "concerns" in f.relative_to(root).parts:
                continue
            text = read_text(f)
            m = re.search(r"^\s*class\s+([\w:]+)\s*(?:<\s*([\w:]+))?", text, re.M)
            if not m:
                continue
            name, parent = m.group(1), m.group(2) or ""
            if name == "ApplicationRecord":
                continue
            tm = re.search(r"self\.table_name\s*=\s*['\"](\w+)['\"]", text)
            md = Model(name, f, line_of(text, m.start()), tm.group(1) if tm else table_for_model(name), parent)
            private = False
            in_self = 0
            for i, raw in enumerate(text.splitlines(), 1):
                st = raw.strip()
                if re.match(r"(private|protected)\s*$", st):
                    private = True
                if re.match(r"class\s*<<\s*self", st):
                    in_self = len(raw) - len(raw.lstrip())
                    continue
                am = re.match(r"(has_many|belongs_to|has_one|has_and_belongs_to_many)\s+:(\w+)(.*)$", st)
                if am:
                    kind, an, rest = am.groups()
                    cn = re.search(r"class_name:\s*['\"]([\w:]+)['\"]", rest)
                    target = cn.group(1) if cn else camelize(singularize(an) if kind in
                                                             ("has_many", "has_and_belongs_to_many") else an)
                    md.assocs[an] = Assoc(kind, an, target, i)
                    continue
                sm = re.match(r"scope\s+:(\w+)", st)
                if sm:
                    md.scopes[sm.group(1)] = i
                    continue
                em = re.match(r"enum\s+:?(\w+)\s*[:,]\s*(.*)$", st)
                if em:
                    md.enums[em.group(1)] = re.findall(r"(\w+):", em.group(2)) or re.findall(r":(\w+)", em.group(2))
                    continue
                atm = re.match(r"(?:attribute|attr_accessor|attr_reader|store_accessor)\s+(.*)$", st)
                if atm:
                    for a in re.findall(r":(\w+)", atm.group(1).split(",", 1)[0] if st.startswith("attribute ")
                                        else atm.group(1)):
                        md.attributes[a] = i
                    continue
                if re.match(r"has_secure_password\b", st):
                    md.attributes.setdefault("password", i)
                    md.attributes.setdefault("password_confirmation", i)
                    md.methods.setdefault("authenticate", i)
                    continue
                at = re.match(r"has_(one|many)_attached\s+:(\w+)", st)
                if at:
                    md.attributes[at.group(2)] = i
                    continue
                dm = re.match(r"def\s+(self\.)?([\w?!=]+)", st)
                if dm:
                    if dm.group(1) or (in_self and len(raw) - len(raw.lstrip()) > in_self):
                        md.class_methods[dm.group(2)] = i
                    elif not private:
                        md.methods[dm.group(2)] = i
                    else:
                        md.methods.setdefault(dm.group(2), i)
            out[name] = md
            short = name.split("::")[-1]
            out.setdefault(short, md)
        return out

    def model_of_file(self, path) -> Model | None:
        try:
            p = Path(path).resolve()
        except OSError:
            return None
        for m in self.models().values():
            if m.file == p or os.path.normcase(str(m.file)) == os.path.normcase(str(p)):
                return m
        return None

    # ------------------------------------------------------------ controllers
    def controllers(self) -> dict[str, Controller]:
        return self._controllers.get()

    def _build_controllers(self) -> dict[str, Controller]:
        out: dict[str, Controller] = {}
        root = self.folder / "app" / "controllers"
        if not root.is_dir():
            return out
        for f in sorted(root.rglob("*_controller.rb")):
            rel = f.relative_to(root).as_posix()[:-len("_controller.rb")]
            text = read_text(f)
            m = re.search(r"^\s*class\s+([\w:]+)", text, re.M)
            c = Controller(m.group(1) if m else camelize(rel) + "Controller", rel, f,
                           line_of(text, m.start()) if m else 1)
            private = False
            cur = None
            def_indent = 0
            for i, raw in enumerate(text.splitlines(), 1):
                st = raw.strip()
                ind = len(raw) - len(raw.lstrip())
                if re.match(r"(private|protected)\s*$", st):
                    private = True
                    cur = None
                    continue
                dm = re.match(r"def\s+([\w?!]+)", st)
                if dm:
                    (c.private if private else c.actions)[dm.group(1)] = i
                    cur = dm.group(1)
                    def_indent = ind
                    c.ivars.setdefault(cur, {})
                    continue
                if cur is not None and st == "end" and ind <= def_indent:
                    cur = None
                    continue
                for vm in re.finditer(r"(@\w+)\s*(?:\|\|)?=(?!=)\s*(.*)$", st):
                    target = cur or "*"
                    c.ivars.setdefault(target, {}).setdefault(vm.group(1), (i, vm.group(2).strip()))
            out[rel] = c
        return out

    def controller_of_file(self, path) -> Controller | None:
        p = os.path.normcase(str(Path(path).resolve()))
        for c in self.controllers().values():
            if os.path.normcase(str(c.file)) == p:
                return c
        return None

    def before_actions(self, c: Controller) -> list[str]:
        """Methods named by before_action in the controller (their @vars are visible in every action)."""
        return re.findall(r"before_action\s+:(\w+)", read_text(c.file))

    def view_ivars(self, view: str) -> dict[str, tuple]:
        """@vars a view can use: those of its controller action (+ before_action callbacks), ``products/index``."""
        ctrl, _, action = view.rpartition("/")
        c = self.controllers().get(ctrl)
        if c is None:
            return {}
        out: dict[str, tuple] = {}
        names = [action] + ({"new": ["create"], "edit": ["update"]}.get(action, [])) + self.before_actions(c) + ["*"]
        if action.startswith("_"):               # a partial: every action of the controller
            names = list(c.ivars.keys())
        for n in names:
            for k, v in (c.ivars.get(n) or {}).items():
                out.setdefault(k, v + (c.file,))
        return out

    # ------------------------------------------------------------ views / helpers / locales / env
    def views(self) -> dict[str, Path]:
        return self._views.get()

    def _build_views(self) -> dict[str, Path]:
        """{"products/index": path, "products/_form": path, "layouts/application": path}."""
        out: dict[str, Path] = {}
        root = self.folder / "app" / "views"
        if not root.is_dir():
            return out
        for f in sorted(root.rglob("*")):
            if f.is_file():
                rel = f.relative_to(root).as_posix()
                out.setdefault(rel.split(".", 1)[0], f)
        return out

    def view_name_of(self, path) -> str:
        root = self.folder / "app" / "views"
        try:
            rel = Path(path).resolve().relative_to(root.resolve()).as_posix()
        except (ValueError, OSError):
            return ""
        return rel.split(".", 1)[0]

    def resolve_view(self, name: str, context_dir: str = "", partial: bool = False) -> Path | None:
        views = self.views()
        name = name.strip().lstrip("/")
        d, _, base = name.rpartition("/")
        cands = []
        if partial or "/" in name:
            cands.append((d + "/" if d else (context_dir + "/" if context_dir else "")) + "_" + base)
        cands.append(name)
        if context_dir and "/" not in name:
            cands += [f"{context_dir}/{name}", f"{context_dir}/_{name}", f"application/_{name}"]
        for c in cands:
            if c in views:
                return views[c]
        return None

    def helpers(self) -> list[tuple[str, Path, int]]:
        return self._helpers.get()

    def _build_helpers(self) -> list[tuple[str, Path, int]]:
        out = []
        root = self.folder / "app" / "helpers"
        for f in sorted(root.rglob("*.rb")) if root.is_dir() else []:
            text = read_text(f)
            for m in re.finditer(r"^\s*def\s+([\w?!]+)", text, re.M):
                out.append((m.group(1), f, line_of(text, m.start())))
        return out

    def locale_keys(self) -> list[tuple[str, str, Path, int]]:
        return self._locales.get()

    def _build_locales(self) -> list[tuple[str, str, Path, int]]:
        """[(key without the locale, value, file, line)] - "en.products.index.title" -> "products.index.title"."""
        out = []
        seen = set()
        root = self.folder / "config" / "locales"
        for f in sorted(root.rglob("*.y*ml")) if root.is_dir() else []:
            for key, val, line in yaml_keys(f):
                k = key.split(".", 1)[1] if "." in key else key
                if k not in seen:
                    seen.add(k)
                    out.append((k, val, f, line))
        return out

    def env_keys(self) -> list[tuple[str, str, Path | None, int]]:
        return self._env.get()

    def _build_env(self) -> list[tuple[str, str, Path | None, int]]:
        out = []
        seen = set()
        for name in (".env", ".env.development", ".env.local", ".env.example"):
            f = self.folder / name
            for i, raw in enumerate(read_text(f).splitlines(), 1):
                m = re.match(r"\s*(?:export\s+)?([A-Za-z_]\w*)\s*=\s*(.*)$", raw)
                if m and m.group(1) not in seen:
                    seen.add(m.group(1))
                    out.append((m.group(1), m.group(2).strip().strip("'\""), f, i))
        cfg = self.folder / "config"
        for f in sorted(cfg.rglob("*")) if cfg.is_dir() else []:
            if f.suffix not in (".rb", ".yml") or not f.is_file():
                continue
            text = read_text(f)
            for m in re.finditer(r"ENV(?:\.fetch\(\s*|\[\s*)['\"](\w+)['\"]", text):
                if m.group(1) not in seen:
                    seen.add(m.group(1))
                    out.append((m.group(1), "", f, line_of(text, m.start())))
        for k in RAILS_ENV_KEYS:
            if k not in seen:
                seen.add(k)
                out.append((k, "", None, 0))
        return out


# ============================================================================ completion
def _range(line: int, col: int, typed: str) -> list[int]:
    return [line, col - len(typed), line, col]


def _balanced_strip(expr: str) -> str:
    """Remove (...) / [...] / {...} groups and do |x| ... blocks: "Product.where(a: 1).order(:x)" ->
    "Product.where.order"."""
    out = []
    depth = 0
    for ch in expr:
        if ch in "([{":
            depth += 1
            continue
        if ch in ")]}":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            out.append(ch)
    return "".join(out).replace(" ", "")


def erb_ruby_before(text: str, offset: int) -> tuple[bool, int]:
    """(cursor inside <% %>, offset where the Ruby segment starts) for an ERB text."""
    start = text.rfind("<%", 0, offset)
    if start < 0:
        return False, 0
    end = text.rfind("%>", 0, offset)
    if end > start:
        return False, 0
    seg = start + 2
    while seg < offset and text[seg] in "=-#%":
        if text[seg] == "#":
            return False, 0
        seg += 1
    return True, seg


def _offset(text: str, line: int, col: int) -> int:
    lines = text.split("\n")
    return sum(len(x) + 1 for x in lines[:line]) + col


def _string_context(before: str) -> tuple[str, str, str] | None:
    """(text before the opening quote, typed prefix, quote) when the cursor is inside a string literal."""
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
            elif quote == '"' and before.startswith("#{", i):
                pass
        elif c in "\"'" and not (c == "'" and i and before[i - 1].isalnum()):
            quote, start = c, i
        elif c == "#":
            return None                      # a comment
        i += 1
    if quote is None:
        return None
    return before[:start], before[start + 1:], quote


class _Ctx:
    """What completion / definition need to know about the file being edited."""

    def __init__(self, idx: RailsIndex, path, text: str, line: int, col: int):
        self.idx = idx
        self.path = Path(path)
        self.text = text
        self.line, self.col = line, col
        lines = text.split("\n")
        self.cur = lines[line] if line < len(lines) else ""
        self.erb = self.path.name.lower().endswith((".erb", ".rhtml"))
        self.in_ruby = True
        before = self.cur[:col]
        if self.erb:
            off = _offset(text, line, col)
            self.in_ruby, seg = erb_ruby_before(text, off)
            line_start = off - col
            if self.in_ruby and seg > line_start:
                before = text[seg:off]
        self.before = before
        self.view = idx.view_name_of(self.path) if self.erb or "app/views" in self.path.as_posix() else ""
        self.controller = idx.controller_of_file(self.path) if self.path.name.endswith("_controller.rb") else None
        self.model = idx.model_of_file(self.path) if "app/models" in self.path.as_posix() else None
        try:
            rel = self.path.resolve().relative_to(idx.folder).as_posix()
        except (ValueError, OSError):
            rel = ""
        self.rel = rel

    @property
    def view_dir(self) -> str:
        if self.view:
            return self.view.rpartition("/")[0]
        if self.controller is not None:
            return self.controller.path
        return ""

    def scope_text(self) -> str:
        """Text of the current method (or the file up to the cursor) - for local variable types."""
        lines = self.text.split("\n")[:self.line + 1]
        lines[-1] = lines[-1][:self.col]
        if self.erb:
            return "\n".join(lines)
        for i in range(len(lines) - 1, -1, -1):
            if re.match(r"\s*def\s", lines[i]):
                return "\n".join(lines[i:])
        return "\n".join(lines)


# ---- types: ("class", Model) | ("inst", Model) | ("coll", Model) | None
def _model_named(idx: RailsIndex, name: str) -> Model | None:
    ms = idx.models()
    return ms.get(name) or ms.get(name.split("::")[-1])


def expr_type(ctx: _Ctx, expr: str, depth: int = 0):
    idx = ctx.idx
    if depth > 6:
        return None
    e = _balanced_strip(expr.strip())
    e = re.sub(r"\bdo\|.*$", "", e)
    if not e:
        return None
    parts = [p for p in re.split(r"\.|&\.", e) if p]
    if not parts:
        return None
    head = parts[0]
    t = None
    if re.match(r"^[A-Z][\w:]*$", head):
        m = _model_named(idx, head)
        t = ("class", m) if m is not None else None
    elif head.startswith("@") or re.match(r"^[a-z_]\w*$", head):
        t = var_type(ctx, head, depth + 1)
    if t is None:
        return None
    for p in parts[1:]:
        t = member_type(idx, t, p.rstrip("!?") if p not in INSTANCE_RETURNING else p)
        if t is None:
            return None
    return t


def member_type(idx: RailsIndex, t, member: str):
    kind, m = t
    if kind == "class":
        if member in INSTANCE_RETURNING:
            return ("inst", m)
        if member in RELATION_RETURNING or member in m.scopes:
            return ("coll", m)
        return None
    if kind == "coll":
        if member in INSTANCE_RETURNING:
            return ("inst", m)
        if member in RELATION_RETURNING or member in m.scopes:
            return ("coll", m)
        return None
    if kind == "inst":
        a = m.assocs.get(member)
        if a is not None:
            target = _model_named(idx, a.target)
            if target is None:
                return None
            return ("coll", target) if a.many else ("inst", target)
    return None


def var_type(ctx: _Ctx, var: str, depth: int = 0):
    """Type of a local / instance variable: its assignment in scope, a block parameter, the controller
    action (views), else its name (product -> Product, products -> collection of Product)."""
    idx = ctx.idx
    scope = ctx.scope_text()
    # block parameter: X.each do |var| / X.each { |var|
    for m in reversed(list(re.finditer(r"([@\w.:()\[\]'\" ,]+?)\.(?:each|map|each_with_index|select|find_each|"
                                       r"filter_map|collect|reject|sort_by|group_by)\s*(?:do\s*|\{\s*)\|\s*(\w+)",
                                       scope))):
        if m.group(2) == var:
            t = expr_type(ctx, m.group(1).strip().split(" ")[-1].split("(")[-1] if "(" in m.group(1).split(".")[0]
                          else m.group(1).strip(), depth + 1)
            if t is not None and t[0] == "coll":
                return ("inst", t[1])
    # assignment in scope
    for m in reversed(list(re.finditer(rf"(?<![\w@]){re.escape(var)}\s*(?:\|\|)?=(?!=|~|>)\s*([^\n]+)", scope))):
        rhs = m.group(1).strip()
        if rhs.split(".")[0] == var:
            continue
        t = expr_type(ctx, rhs, depth + 1)
        if t is not None:
            return t
        break
    if var.startswith("@"):
        exprs = []
        if ctx.view:
            iv = idx.view_ivars(ctx.view).get(var)
            if iv:
                exprs.append(iv[1])
        elif ctx.controller is not None:
            for vs in ctx.controller.ivars.values():
                if var in vs:
                    exprs.append(vs[var][1])
        for ex in exprs:
            t = expr_type(_ExprCtx(ctx), ex, depth + 1)
            if t is not None:
                return t
    name = var.lstrip("@")
    m = _model_named(idx, camelize(name))
    if m is not None and singularize(name) == name:
        return ("inst", m)
    m = _model_named(idx, camelize(singularize(name)))
    if m is not None:
        return ("coll", m)
    if ctx.model is not None and name == "self":
        return ("inst", ctx.model)
    return None


class _ExprCtx(_Ctx):
    """A context without a local scope (controller expressions typed from a view)."""

    def __init__(self, base: _Ctx):              # noqa: D401 - copy the base context
        self.__dict__.update(base.__dict__)
        self.view = ""
        self.text, self.line, self.col = "", 0, 0

    def scope_text(self) -> str:
        return ""


def _members(idx: RailsIndex, t, typed: str, rng) -> list[dict]:
    kind, m = t
    items: list[dict] = []
    if kind == "class":
        for s, ln in m.scopes.items():
            items.append(item(s, K_METHOD, f"scope (app/models/{m.file.name}:{ln})", rng=rng))
        for s, ln in m.class_methods.items():
            items.append(item(s, K_METHOD, f"def self.{s} ({m.file.name}:{ln})", rng=rng))
        for n, d in AR_CLASS_METHODS:
            if "." not in n:
                items.append(item(n, K_METHOD, f"ActiveRecord: {d}", rng=rng))
        for col in idx.columns(m.name):
            items.append(item(f"find_by_{col}", K_METHOD, f"find_by_{col}(value) -> {m.name}", rng=rng))
        return items
    if kind == "coll":
        for s, ln in m.scopes.items():
            items.append(item(s, K_METHOD, f"scope of {m.name}", rng=rng))
        for n, d in RELATION_METHODS:
            items.append(item(n, K_METHOD, f"{m.name} collection: {d}", rng=rng))
        return items
    cols = idx.columns(m.name)
    for col, (typ, _ln) in cols.items():
        items.append(item(col, K_FIELD, f"{typ} - column of {m.table}", rng=rng))
        if typ == "boolean":
            items.append(item(col + "?", K_FIELD, f"boolean column {col}", rng=rng))
    for a in m.assocs.values():
        items.append(item(a.name, K_PROPERTY, f"{a.kind} :{a.name} -> {a.target}{'[]' if a.many else ''}", rng=rng))
        if a.kind == "belongs_to":
            items.append(item(f"build_{a.name}", K_METHOD, f"build_{a.name}(attrs) -> {a.target}", rng=rng))
        if a.many:
            items.append(item(f"{singularize(a.name)}_ids", K_PROPERTY, f"ids of {a.name}", rng=rng))
    for att, ln in m.attributes.items():
        items.append(item(att, K_PROPERTY, f"attribute ({m.file.name}:{ln})", rng=rng))
    for e, vals in m.enums.items():
        items.append(item(e, K_FIELD, f"enum {e}: {', '.join(vals)}", rng=rng))
        for v in vals:
            items.append(item(v + "?", K_METHOD, f"enum {e} == {v}", rng=rng))
            items.append(item(v + "!", K_METHOD, f"set enum {e} = {v}", rng=rng))
    for s, ln in m.methods.items():
        items.append(item(s, K_METHOD, f"def {s} ({m.file.name}:{ln})", rng=rng))
    for n, d in AR_INSTANCE_METHODS:
        items.append(item(n, K_METHOD, f"ActiveRecord: {d}", rng=rng))
    return items


def _filter(items: list[dict], typed: str) -> list[dict]:
    t = typed.lower()
    seen = set()
    out = []
    for it in items:
        lab = it["label"]
        if lab in seen:
            continue
        if not t or lab.lower().startswith(t) or (len(t) > 1 and t in lab.lower()):
            seen.add(lab)
            out.append(it)
    return out


def _model_for_context(ctx: _Ctx) -> Model | None:
    """The model a symbol list refers to: the model file itself, permit after require(:x), the controller's."""
    idx = ctx.idx
    if ctx.model is not None:
        return ctx.model
    m = re.search(r"require\(\s*:(\w+)\s*\)", ctx.before) or re.search(r"expect\(\s*(\w+):\s*\[", ctx.before)
    if m:
        return _model_named(idx, camelize(m.group(1)))
    m = re.search(r"([A-Z]\w*)\.\w+\(", ctx.before)
    if m:
        return _model_named(idx, m.group(1))
    m = re.search(r"([@\w]+)\.\w+\(", ctx.before)
    if m:
        t = var_type(ctx, m.group(1))
        if t is not None:
            return t[1]
    if ctx.controller is not None:
        return _model_named(idx, camelize(singularize(ctx.controller.path.split("/")[-1])))
    if ctx.view:
        return _model_named(idx, camelize(singularize(ctx.view_dir.split("/")[-1])))
    return None


def complete_items(folder, path, text: str, line: int, col: int) -> list[dict] | None:
    idx = index(folder)
    ctx = _Ctx(idx, path, text, line, col)
    if ctx.erb and not ctx.in_ruby:
        return None
    items = _complete(ctx)
    if items is None:
        return None
    if ctx.erb:                           # inside <% %>: only Ruby items (the HTML server's are noise there)
        for it in items:
            it["exclusive"] = True
    return items


def _complete(ctx: _Ctx) -> list[dict] | None:
    idx = ctx.idx
    before = ctx.before
    line, col = ctx.line, ctx.col
    sc = _string_context(before)
    if sc is not None:
        return _complete_string(ctx, *sc)
    # :symbol
    m = re.search(r"(?<![:\w]):(\w*)$", before)
    if m:
        return _complete_symbol(ctx, before[:m.start()], m.group(1))
    # receiver.member
    m = re.search(r"((?:@{0,2}|\$)[A-Za-z_][\w:]*[?!]?(?:\([^()]*(?:\([^()]*\)[^()]*)*\)|\[[^\]]*\])*"
                  r"(?:\s*&?\.\s*\w+[?!]?(?:\([^()]*(?:\([^()]*\)[^()]*)*\)|\[[^\]]*\])*)*)\s*&?\.(\w*)$", before)
    if m:
        expr, typed = m.group(1), m.group(2)
        rng = _range(line, col, typed)
        if expr in ("Rails",):
            return _filter([item(n, K_METHOD, "Rails." + n, rng=rng) for n in
                            ("application", "env", "root", "logger", "cache", "configuration", "version",
                             "credentials", "public_path", "groups", "error")], typed)
        t = expr_type(ctx, expr)
        if t is None:
            return None
        return _filter(_members(idx, t, typed, rng), typed)
    # @ivar
    m = re.search(r"(@\w*)$", before)
    if m:
        typed = m.group(1)
        rng = _range(line, col, typed)
        out = []
        if ctx.view:
            for v, (ln, ex, f) in idx.view_ivars(ctx.view).items():
                out.append(item(v, K_VARIABLE, f"{ex[:60]}  ({Path(f).name}:{ln})", rng=rng))
        elif ctx.controller is not None:
            for act, vs in ctx.controller.ivars.items():
                for v, (ln, ex) in vs.items():
                    out.append(item(v, K_VARIABLE, f"{ex[:60]}  ({act if act != '*' else 'class'}:{ln})", rng=rng))
        return _filter(out, typed) or None
    # bare identifier
    m = re.search(r"(?<![\w.:@$])([A-Za-z_]\w*)$", before)
    if not m:
        return None
    typed = m.group(1)
    rng = _range(line, col, typed)
    out: list[dict] = []
    if typed[:1].isupper():
        for name, md in sorted(idx.models().items()):
            if name == md.name:
                out.append(item(name, K_CLASS, f"model ({md.table}) - app/models/{md.file.name}", rng=rng))
        return _filter(out, typed) or None
    app_code = ctx.erb or ctx.rel.startswith(("app/controllers", "app/views", "app/helpers", "app/mailers",
                                              "app/components", "test/", "spec/"))
    if app_code:
        for helper, r in idx.route_helpers():
            out.append(item(helper, K_FUNCTION, f"{r.verb} {r.path} -> {r.handler}", rng=rng))
    if ctx.erb or ctx.rel.startswith("app/helpers"):
        for name, f, ln in idx.helpers():
            out.append(item(name, K_FUNCTION, f"helper ({f.name}:{ln})", rng=rng))
        out += [item(h, K_FUNCTION, "Rails view helper", rng=rng) for h in VIEW_HELPERS]
    if ctx.controller is not None:
        for a, ln in {**ctx.controller.actions, **ctx.controller.private}.items():
            out.append(item(a, K_METHOD, f"{ctx.controller.name}#{a} (line {ln})", rng=rng))
        out += [item(h, K_FUNCTION, "ActionController", rng=rng) for h in CONTROLLER_METHODS]
    if ctx.model is not None:
        for col_, (typ, _l) in idx.columns(ctx.model.name).items():
            out.append(item(col_, K_FIELD, f"{typ} - column of {ctx.model.table}", rng=rng))
        for a in ctx.model.assocs.values():
            out.append(item(a.name, K_PROPERTY, f"{a.kind} -> {a.target}", rng=rng))
        if len(typed) >= 2:
            out += [item(h, K_KEYWORD, "ActiveRecord DSL", rng=rng) for h in MODEL_DSL]
    if not out:
        return None
    return _filter(out, typed) or None


def _complete_symbol(ctx: _Ctx, head: str, typed: str) -> list[dict] | None:
    idx = ctx.idx
    rng = _range(ctx.line, ctx.col, typed)
    out: list[dict] = []
    if re.search(r"\b(?:has_many|has_and_belongs_to_many|has_one|belongs_to)\s*$", head):
        many = not re.search(r"(?:has_one|belongs_to)\s*$", head)
        for name, md in idx.models().items():
            if name != md.name:
                continue
            n = underscore(name).replace("/", "_")
            out.append(item(pluralize(n) if many else n, K_PROPERTY, f"-> {name} ({md.table})", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"\b(?:before_action|after_action|around_action|skip_before_action|helper_method)\b.*$", head) \
            and ctx.controller is not None:
        for a, ln in {**ctx.controller.private, **ctx.controller.actions}.items():
            out.append(item(a, K_METHOD, f"line {ln}", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"\b(?:only|except):\s*\[?[:\w, ]*$", head) and ctx.controller is not None:
        for a, ln in ctx.controller.actions.items():
            out.append(item(a, K_METHOD, f"action (line {ln})", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"\brender\s*\(?\s*(?:action:\s*)?$", head) and ctx.controller is not None:
        for v in idx.views():
            d, _, base = v.rpartition("/")
            if d == ctx.controller.path and not base.startswith("_"):
                out.append(item(base, K_FILE, f"app/views/{v}", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"\bexpect\(\s*\w+:\s*\[[^\]]*$", head):
        md = _model_for_context(ctx)
        if md is not None:
            for c, (typ, _l) in idx.columns(md.name).items():
                if c not in ("id", "created_at", "updated_at"):
                    out.append(item(c, K_FIELD, f"{typ} - {md.table}", rng=rng))
            return _filter(out, typed) or None
    if re.search(r"\b(?:permit|validates|validates_presence_of|validates_uniqueness_of|order|pluck|select|group|"
                 r"attribute_names|reorder|sum|maximum|minimum|average|index_by|normalizes|encrypts|"
                 r"find_by|where|update|increment!|decrement!|toggle!|touch|attribute)\b.*$", head):
        md = _model_for_context(ctx)
        if md is not None:
            for c, (typ, _l) in idx.columns(md.name).items():
                out.append(item(c, K_FIELD, f"{typ} - {md.table}", rng=rng))
            for a in md.assocs.values():
                if re.search(r"\b(?:permit|validates)\b", head):
                    out.append(item(a.name if not a.many else f"{singularize(a.name)}_ids", K_PROPERTY,
                                    f"{a.kind} -> {a.target}", rng=rng))
            return _filter(out, typed) or None
    if re.search(r"\b(?:includes|preload|eager_load|joins|left_joins|left_outer_joins)\b.*$", head):
        md = _model_for_context(ctx)
        if md is not None:
            for a in md.assocs.values():
                out.append(item(a.name, K_PROPERTY, f"{a.kind} -> {a.target}", rng=rng))
            return _filter(out, typed) or None
    return None


def _complete_string(ctx: _Ctx, head: str, typed: str, quote: str) -> list[dict] | None:
    idx = ctx.idx
    rng = _range(ctx.line, ctx.col, typed)
    out: list[dict] = []
    if re.search(r"\b(?:render|render_to_string)\s*\(?\s*(?:(?:template|partial|layout|collection):\s*)?$", head) or \
            re.search(r"\bpartial:\s*$", head):
        partial = bool(re.search(r"partial:\s*$", head)) or (ctx.erb or bool(ctx.view)) and \
            not re.search(r"template:\s*$", head)
        vd = ctx.view_dir
        for v, f in idx.views().items():
            d, _, base = v.rpartition("/")
            is_partial = base.startswith("_")
            if partial and not is_partial and not re.search(r"template:|layout:", head) and ctx.erb:
                continue
            name = (d + "/" if d else "") + (base[1:] if is_partial else base)
            out.append(item(name, K_FILE, f"app/views/{f.relative_to(idx.folder / 'app' / 'views').as_posix()}",
                            rng=rng, sort="1" + name))
            if d == vd and vd:
                short = base[1:] if is_partial else base
                out.append(item(short, K_FILE, f"app/views/{v} ({'partial' if is_partial else 'view'})",
                                rng=rng, sort="0" + short))
        return _filter(out, typed) or None
    if re.search(r"(?:\bt|\btranslate|I18n\.t|I18n\.translate)\s*\(?\s*$", head):
        keys = idx.locale_keys()
        if typed.startswith(".") and ctx.view:
            prefix = ctx.view.replace("/", ".").replace("._", ".") + "."
            for k, v, f, ln in keys:
                if k.startswith(prefix):
                    lab = "." + k[len(prefix):]
                    out.append(item(lab, K_VALUE, f"{v[:60]}  ({f.name}:{ln})", rng=rng))
            return _filter(out, typed) or None
        for k, v, f, ln in keys:
            out.append(item(k, K_VALUE, f"{v[:60]}  ({f.name}:{ln})", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"\bENV(?:\[\s*|\.fetch\(\s*|\.key\?\(\s*)$", head):
        for k, v, f, ln in idx.env_keys():
            out.append(item(k, K_CONSTANT, (f"{v[:40]}  ({f.name}:{ln})" if f else "Rails / Puma setting")
                            if v or f else "", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"(?:\bto:\s*|=>\s*)$", head) and ctx.rel == "config/routes.rb":
        for c in idx.controllers().values():
            if c.path == "application":
                continue
            for a, ln in c.actions.items():
                lab = f"{c.path}#{a}"
                out.append(item(lab, K_METHOD, f"{c.name}#{a} ({c.file.name}:{ln})", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"\bclass_name:\s*$", head):
        for name, md in idx.models().items():
            if name == md.name:
                out.append(item(name, K_CLASS, f"model ({md.table})", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"\b(?:redirect_to|link_to\b.*,|button_to\b.*,|href=|action=|fetch\(|visit|get|post|patch|"
                 r"delete)\s*\(?\s*$", head) and typed.startswith("/"):
        for r in idx.routes():
            p = re.sub(r"\(.*?\)", "", r.path)
            out.append(item(p, K_VALUE, f"{r.verb} {r.handler}", rng=rng))
        return _filter(out, typed) or None
    if re.search(r"\b(?:stylesheet_link_tag|image_tag|javascript_include_tag)\s*\(?\s*$", head):
        for base in ("app/assets/stylesheets", "app/assets/images", "app/javascript"):
            d = idx.folder / base
            for f in sorted(d.rglob("*")) if d.is_dir() else []:
                if f.is_file():
                    rel = f.relative_to(d).as_posix()
                    if base.endswith("stylesheets") or base.endswith("javascript"):
                        rel = rel.rsplit(".", 1)[0]
                    out.append(item(rel, K_FILE, f"{base}/{f.relative_to(d).as_posix()}", rng=rng))
        return _filter(out, typed) or None
    return None


# ============================================================================ go to definition
def _string_at(cur: str, col: int) -> tuple[str, int, int] | None:
    for m in re.finditer(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"", cur):
        if m.start() <= col < m.end() or m.start() < col <= m.end():
            g = 1 if m.group(1) is not None else 2
            return m.group(g), m.start(g), m.end(g)
    return None


def _word_at(cur: str, col: int) -> tuple[str, int, int] | None:
    for m in re.finditer(r"@{0,2}[A-Za-z_][\w]*[?!]?(?:::[A-Z]\w*)*|:[A-Za-z_]\w*", cur):
        if m.start() <= col <= m.end():
            return m.group(0), m.start(), m.end()
    return None


def definition(folder, path, text: str, line: int, col: int) -> tuple[str, int] | None:
    """F12 / Ctrl+click on a Rails name -> (file, 1-based line); None = not ours (the language server answers)."""
    idx = index(folder)
    ctx = _Ctx(idx, path, text, line, col)
    cur = ctx.cur
    s = _string_at(cur, col)
    if s is not None:
        content, start, _end = s
        head = cur[:start - 1]
        if re.search(r"\b(?:render|render_to_string)\s*\(?\s*(?:(?:template|partial|layout):\s*)?$", head) or \
                re.search(r"partial:\s*$", head):
            partial = "partial:" in head[-12:] or ctx.erb or bool(ctx.view)
            f = idx.resolve_view(content, ctx.view_dir, partial)
            return (str(f), 1) if f else None
        if re.search(r"(?:\bt|translate|I18n\.t)\s*\(?\s*$", head):
            key = content
            if key.startswith(".") and ctx.view:
                key = ctx.view.replace("/", ".").replace("._", ".") + key
            for k, _v, f, ln in idx.locale_keys():
                if k == key:
                    return str(f), ln
            return None
        if re.search(r"\bENV(?:\[\s*|\.fetch\(\s*)$", head):
            for k, _v, f, ln in idx.env_keys():
                if k == content and f is not None:
                    return str(f), ln
            return None
        m = re.match(r"^([\w/]+)#(\w+)$", content)
        if m:
            c = idx.controllers().get(m.group(1))
            if c is not None:
                return str(c.file), c.actions.get(m.group(2)) or c.line
        if re.search(r"class_name:\s*$", head):
            md = _model_named(idx, content)
            return (str(md.file), md.line) if md else None
        return None
    w = _word_at(cur, col)
    if w is None:
        return None
    word, start, _end = w
    head = cur[:start]
    if word.startswith(":"):
        sym = word[1:]
        if re.search(r"\b(?:has_many|has_and_belongs_to_many|has_one|belongs_to)\s*$", head):
            md = ctx.model
            a = md.assocs.get(sym) if md else None
            target = _model_named(idx, a.target if a else camelize(singularize(sym)))
            return (str(target.file), target.line) if target else None
        if ctx.controller is not None and re.search(r"\b(?:before_action|after_action|around_action|"
                                                    r"skip_before_action|helper_method)\b", head):
            ln = ctx.controller.private.get(sym) or ctx.controller.actions.get(sym)
            return (str(ctx.controller.file), ln) if ln else None
        if ctx.controller is not None and re.search(r"\brender\s*\(?\s*(?:action:\s*)?$", head):
            f = idx.resolve_view(sym, ctx.controller.path)
            return (str(f), 1) if f else None
        md = _model_for_context(ctx)
        if md is not None:
            cols = idx.columns(md.name)
            if sym in cols:
                return _column_location(idx, md, sym)
        return None
    if word.endswith(("_path", "_url")):
        name = word.rsplit("_", 1)[0]
        for r in idx.routes():
            if r.name == name:
                return idx.route_target(r)
    if word.startswith("@"):
        if ctx.view:
            iv = idx.view_ivars(ctx.view).get(word)
            if iv:
                return str(iv[2]), iv[0]
        return None
    if word[:1].isupper():
        md = _model_named(idx, word)
        if md is not None:
            return str(md.file), md.line
        c = next((c for c in idx.controllers().values() if c.name == word), None)
        if c is not None:
            return str(c.file), c.line
        return None
    # receiver.member
    m = re.search(r"([@\w:.()\[\]'\" ,&]+?)\s*&?\.\s*$", head)
    if m:
        t = expr_type(ctx, m.group(1).strip())
        if t is not None:
            md = t[1]
            name = word.rstrip("?")
            if t[0] == "inst":
                a = md.assocs.get(name)
                if a is not None:
                    return str(md.file), a.line
                if name in idx.columns(md.name):
                    return _column_location(idx, md, name)
                if name in md.methods:
                    return str(md.file), md.methods[name]
            if name in md.scopes:
                return str(md.file), md.scopes[name]
            if name in md.class_methods:
                return str(md.file), md.class_methods[name]
        return None
    if ctx.erb or ctx.rel.startswith("app/"):
        for name, f, ln in idx.helpers():
            if name == word:
                return str(f), ln
    if ctx.controller is not None:
        ln = ctx.controller.actions.get(word) or ctx.controller.private.get(word)
        if ln:
            return str(ctx.controller.file), ln
    return None


def _column_location(idx: RailsIndex, md: Model, col: str) -> tuple[str, int] | None:
    info = idx.schema().get(md.table) or {}
    ln = (info.get("columns", {}).get(col) or ("", 0))[1]
    f = info.get("file") or ""
    if f and ln:
        return f, ln
    if f:
        return f, info.get("line") or 1
    return None


__all__ = ["RailsIndex", "camelize", "complete_items", "definition", "erb_ruby_before", "index", "is_rails",
           "parse_routes_file", "parse_routes_output", "parse_schema_rb", "pluralize", "rails_root_of",
           "singularize", "underscore", "yaml_keys"]
