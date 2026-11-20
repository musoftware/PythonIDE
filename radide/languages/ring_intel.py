"""Ring IntelliSense engine (LSP-style services for the Ring plugins, no Qt here).

Used by radide/languages/ring_qt.py (and the plugins derived from it: Ring Game, Ring Web) through the
plugin hooks of radide/languages/base.py:

    completions   keywords, every Ring function (core C functions, stdlib, all extension libraries), RingQt and
                  library classes after ``new``, members after ``obj.`` (class known from ``obj = new Class``,
                  form controls, ``self``/``this``, RingQt return types), the project's own functions, classes,
                  globals, locals and parameters, members inside ``obj { ... }`` braces, files after ``load "``
    calltip       signature help (all overloads of the Ring docs, the active one by argument count)
    hover         signature + description + library (and the ``load`` it needs) + docs link
    definition    F12: the project's files and the Ring library files (stdlib, guilib/RingQt, httplib, ...)
    references    Shift+F12: every use in the project (comments and strings skipped)
    document_symbols  the outline (functions, classes, methods, attributes, globals)
    format_code   re-indents Ring code (blocks, braces, classes)
    syntax_check  ``ring <file> -norun`` -> [(file, line, message)]

The global Ring index (radide/languages/ring_index.py) is built from the installation and cached.
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import ring_index as ri
from .ring_index import KEYWORD_DOCS, Module, mask, parse_source

IDENT = r"[A-Za-z_؀-ۿ][\w؀-ۿ]*"
SKIP_FILES = {"_radide_run.ring", "_raddbg_run.ring", "_raddbg_game.ring"}
MAX_FILES = 400


@dataclass
class Item:
    """A completion item (converted to base.Completion by the plugin)."""
    name: str
    kind: str
    detail: str = ""
    prio: int = 50


@dataclass
class Member:
    name: str
    kind: str                   # method | attribute
    sigs: list
    doc: str = ""
    file: str = ""
    line: int = -1
    rhs: str = ""
    owner: str = ""             # class name


# ============================================================================ project files
_CACHE: dict[str, tuple[float, Module, str]] = {}


def _parse_file(p: Path) -> tuple[Module, str] | None:
    key = str(p).lower()
    try:
        mt = p.stat().st_mtime
    except OSError:
        return None
    hit = _CACHE.get(key)
    if hit and hit[0] == mt:
        return hit[1], hit[2]
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    mod = parse_source(text)
    _CACHE[key] = (mt, mod, text)
    if len(_CACHE) > 2000:
        _CACHE.clear()
    return mod, text


def project_root(path) -> Path | None:
    if not path:
        return None
    p = Path(path)
    folder = p.parent if p.suffix else p
    for d in [folder, *folder.parents][:4]:
        if (d / "project.radproj").is_file():
            return d
    return folder


def project_files(path) -> list[Path]:
    root = project_root(path)
    if root is None or not root.is_dir():
        return []
    out: list[Path] = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith((".", "_")) and d.lower() not in
                   ("node_modules", "bin", "obj", "target", "build", "dist", "__pycache__", "venv")]
        for fn in files:
            low = fn.lower()
            if low.endswith((".ring", ".rh")) and low not in SKIP_FILES and not low.startswith("_radw_"):
                out.append(Path(dirpath) / fn)
                if len(out) >= MAX_FILES:
                    return out
        if Path(dirpath) != root and len(Path(dirpath).relative_to(root).parts) >= 3:
            dirs[:] = []
    return out


def resolve_load(name: str, from_dir: Path | None) -> Path | None:
    """The file a ``load "name"`` statement uses (project folder first, then Ring's bin/load)."""
    name = name.strip().replace("\\", "/")
    cands = []
    if from_dir is not None:
        cands.append(from_dir / name)
    home = ri.ring_home()
    if home is not None:
        cands += [home / "bin" / "load" / name, home / "bin" / name, home / "libraries" / name]
        stem = Path(name).stem
        cands += [home / "libraries" / stem / name, home / "extensions" / stem / name]
    for c in cands:
        try:
            if c.is_file():
                return c.resolve()
        except OSError:
            continue
    return None


def library_target(path: Path) -> Path:
    """bin/load/x.ring files only redirect to the real library: follow them (Go to Definition)."""
    for _ in range(4):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return path
        code = [ln for ln in mask(text).splitlines() if ln.strip()]
        loads = re.findall(r"""(?im)^\s*load\s+(?:package\s+)?["'](.+?)["']""", text)
        if not loads or len(code) > len(loads) + 1:
            return path
        nxt = loads[-1] if len(loads) > 1 and loads[0].endswith(".rh") else loads[0]
        name = nxt.replace("\\", "/")
        cand = Path(str(path.parent) + name) if name.startswith("/") else path.parent / name
        try:
            if not cand.is_file():
                return path
            path = cand.resolve()
        except OSError:
            return path
    return path


# ============================================================================ the context of one request
class Ctx:
    def __init__(self, code: str, line: int, col: int, path, names: dict | None = None,
                 control_class: dict | None = None):
        self.code = code
        self.line = line
        self.col = col
        self.path = Path(path) if path else None
        self.names = names or {}
        self.control_class = control_class or {}
        self.mod = parse_source(code)
        self.masked = mask(code)
        self.lines = code.split("\n")
        self.mlines = self.masked.split("\n")
        self.idx = ri.load()
        self._others: list[tuple[Path, Module, str]] | None = None
        self._loaded: set[str] | None = None

    # ------------------------------------------------------------ project modules
    def others(self) -> list[tuple[Path, Module, str]]:
        if self._others is None:
            out = []
            me = str(self.path.resolve()).lower() if self.path else ""
            for p in project_files(self.path):
                try:
                    if str(p.resolve()).lower() == me:
                        continue
                except OSError:
                    continue
                r = _parse_file(p)
                if r is not None:
                    out.append((p, r[0], r[1]))
            self._others = out
        return self._others

    def all_modules(self):
        yield (self.path, self.mod, self.code)
        yield from self.others()

    def loaded_libs(self) -> set[str]:
        """bin/load names used by the project (``load "libcurl.ring"`` ...) plus what they load."""
        if self._loaded is None:
            names: set[str] = set()
            for _p, m, _t in self.all_modules():
                for name, _l, _c in m.loads:
                    names.add(Path(name).name.lower())
            if self.names:
                names.add("guilib.ring")
            loads = self.idx.get("loads", {})
            closure = set(names)
            for n in names:
                for f in loads.get(n, []):
                    closure.add(Path(f).name.lower())
            for n in list(closure):
                if n in loads:
                    closure.add(n)
            self._loaded = closure
        return self._loaded

    def is_loaded(self, entry: dict) -> bool:
        ld = (entry.get("load") or "").lower()
        if not ld:
            return True
        if ld in self.loaded_libs():
            return True
        f = entry.get("f")
        return bool(f) and Path(f).name.lower() in self.loaded_libs()

    # ------------------------------------------------------------ text helpers
    def before(self) -> str:
        return self.lines[self.line][:self.col] if self.line < len(self.lines) else ""

    def mbefore(self) -> str:
        return self.mlines[self.line][:self.col] if self.line < len(self.mlines) else ""

    @staticmethod
    def _open_quote(mb: str) -> bool:
        n = sum(mb.count(q) for q in "\"'`")
        return n % 2 == 1

    def word_at(self) -> tuple[str, int, int]:
        text = self.lines[self.line] if self.line < len(self.lines) else ""
        for m in re.finditer(IDENT, text):
            if m.start() <= self.col <= m.end():
                return m.group(), m.start(), m.end()
        return "", self.col, self.col

    # ------------------------------------------------------------ symbol lookup
    def find_function(self, name: str):
        """(kind, entry, path) for a global function: ("user", Sym, path) or ("lib", dict, None)."""
        k = name.lower()
        for p, m, _t in self.all_modules():
            if k in m.funcs:
                return "user", m.funcs[k], p
        e = self.idx["functions"].get(k)
        if e is not None:
            return "lib", e, None
        return None

    def find_class(self, name: str):
        k = name.lower().split(".")[-1]
        for p, m, _t in self.all_modules():
            if k in m.classes:
                return "user", m.classes[k], p, m
        e = self.idx["classes"].get(k)
        if e is not None:
            return "lib", e, None, None
        return None

    def class_members(self, cname: str) -> dict[str, Member]:
        out: dict[str, Member] = {}
        seen: set[str] = set()
        cur = cname
        while cur and cur.lower() not in seen and len(seen) < 25:
            seen.add(cur.lower())
            c = self.find_class(cur)
            if c is None:
                break
            kind, entry, p, m = c
            if kind == "user":
                k = entry.name.lower()
                for mk, s in m.methods.get(k, {}).items():
                    out.setdefault(mk, Member(s.name, "method", [f"{s.name}({', '.join(s.params)})"], s.doc,
                                              str(p), s.line, owner=entry.name))
                for ak, s in m.attrs.get(k, {}).items():
                    out.setdefault(ak, Member(s.name, "attribute", [], "", str(p), s.line, s.rhs, owner=entry.name))
                cur = entry.parent
                if not cur:
                    lib = self.idx["classes"].get(k)          # a user class that re-opens a library class
                    cur = lib.get("p", "") if lib else ""
            else:
                f = entry.get("f", "")
                for mk, me in entry.get("m", {}).items():
                    out.setdefault(mk, Member(me["n"], "method", list(me.get("s", [])), me.get("d", ""), f,
                                              me.get("l", -1), owner=entry["n"]))
                for ak, ae in entry.get("a", {}).items():
                    out.setdefault(ak, Member(ae["n"], "attribute", [], "", f, ae.get("l", -1), ae.get("r", ""),
                                              owner=entry["n"]))
                cur = entry.get("p", "")
        return out

    # ------------------------------------------------------------ type inference
    def var_rhs(self, name: str, line: int | None = None) -> tuple[str, str] | None:
        """(rhs, class context) of a variable visible at *line*."""
        k = name.lower()
        line = self.line if line is None else line
        sc = self.mod.scope_at(line)
        if sc is not None and k in sc.locals:
            return sc.locals[k].rhs, sc.cls
        cls = self.mod.class_at(line) or (sc.cls if sc else "")
        if cls:
            mem = self.class_members(cls).get(k)
            if mem is not None and mem.kind == "attribute":
                return mem.rhs, mem.owner
        found = None
        for _p, m, _t in self.all_modules():
            if k in m.globals:
                found = (m.globals[k].rhs, "")
                break
        if found is not None and not found[0].lower().startswith("new"):
            # a global created in a function (RingQt designer files: Button1 = NULL ... Button1 = new qPushButton)
            for _p, m, _t in self.all_modules():
                for s in m.scopes:
                    v = s.locals.get(k)
                    if v is not None and v.rhs.lower().startswith("new"):
                        return v.rhs, s.cls
        return found

    def type_of(self, expr: str, depth: int = 0, cls_ctx: str | None = None) -> str:
        expr = (expr or "").strip()
        if not expr or depth > 6:
            return ""
        m = re.match(r"(?i)^new\s+([\w.]+)", expr)
        if m:
            return m.group(1).split(".")[-1]
        parts = _split_chain(expr)
        if not parts:
            return ""
        first, is_call = parts[0]
        low = first.lower()
        cur = ""
        if low in ("self", "this"):
            cur = cls_ctx if cls_ctx is not None else (self.mod.class_at(self.line) or
                                                       (self.mod.scope_at(self.line).cls if self.mod.scope_at(self.line) else ""))
            if not cur:
                cur = self._brace_object_class()
        elif is_call:
            f = self.find_function(first)
            if f is not None and f[0] == "user":
                cur = self._return_type(f[1], f[2])
            elif f is not None:
                cur = _ret_class(f[1].get("s", []), self.idx)
            if not cur and self.find_class(first) is not None:
                cur = self.find_class(first)[1].name if self.find_class(first)[0] == "user" else first
        else:
            for n, t in self.names.items():
                if n.lower() == low:
                    cur = self.control_class.get(t, "")
                    break
                if f"{n}_events".lower() == low:
                    cur = "qAllEvents"
                    break
            if not cur:
                r = self.var_rhs(first) if cls_ctx is None else None
                if r is None and cls_ctx:
                    mem = self.class_members(cls_ctx).get(low)
                    r = (mem.rhs, mem.owner) if mem is not None and mem.kind == "attribute" else None
                if r is not None and r[0]:
                    cur = self.type_of(r[0], depth + 1, r[1] or None)
            if not cur and low == "e":
                sc = self.mod.scope_at(self.line)
                if sc is not None and "e" in sc.locals and sc.locals["e"].kind == "parameter":
                    cur = "qAllEvents"
        for name, call in parts[1:]:
            if not cur:
                return ""
            mem = self.class_members(cur).get(name.lower())
            if mem is None:
                return ""
            if mem.kind == "attribute":
                cur = self.type_of(mem.rhs, depth + 1, mem.owner) if mem.rhs else ""
            else:
                cur = _ret_class(mem.sigs, self.idx) or self._user_method_return(mem)
        return cur

    def _brace_object_class(self) -> str:
        """Inside ``oObj { ... }``: the class of oObj."""
        expr = self.brace_object()
        return self.type_of(expr, 1) if expr else ""

    def brace_object(self) -> str:
        depth = 0
        text = self.masked
        lines = self.mlines
        pos = sum(len(x) + 1 for x in lines[:self.line]) + min(self.col, len(lines[self.line]) if self.line < len(lines) else 0)
        i = pos - 1
        while i >= 0:
            ch = text[i]
            if ch == "}":
                depth += 1
            elif ch == "{":
                if depth == 0:
                    head = text[max(0, i - 200):i].rstrip()
                    m = re.search(r"(new\s+[\w.]+\s*(?:\([^()]*\))?|[A-Za-z_][\w.]*(?:\(\))?)\s*$", head, re.I)
                    if m:
                        e = m.group(1).strip()
                        if e.lower().startswith("new"):
                            return re.sub(r"\(.*$", "", e)
                        if e.lower() not in ri.FALLBACK_KEYWORDS and not e.lower().startswith("func"):
                            return e
                    return ""
                depth -= 1
            i -= 1
        return ""

    def _return_type(self, sym, path) -> str:
        text = self.code if path == self.path else (_parse_file(Path(path)) or (None, ""))[1]
        if not text:
            return ""
        body = mask(text).split("\n")[sym.line:sym.end + 1]
        for ln in body:
            m = re.search(r"(?i)\breturn\s+new\s+([\w.]+)", ln)
            if m:
                return m.group(1).split(".")[-1]
        return ""

    def _user_method_return(self, mem: Member) -> str:
        if not mem.file or mem.line < 0 or not mem.file.lower().endswith(".ring"):
            return ""
        r = _parse_file(Path(mem.file)) if (self.path is None or Path(mem.file) != self.path) else (self.mod, self.code)
        if r is None:
            return ""
        text = r[1].split("\n")
        for ln in mask("\n".join(text[mem.line + 1:mem.line + 60])).split("\n"):
            if re.match(r"(?i)^\s*(func|def|class)\b", ln):
                break
            m = re.search(r"(?i)\breturn\s+new\s+([\w.]+)", ln)
            if m:
                return m.group(1).split(".")[-1]
            if re.search(r"(?i)\breturn\s+(self|this)\b", ln):
                return mem.owner
        return ""


def _split_chain(expr: str) -> list[tuple[str, bool]]:
    """'oA.b().c[1].d' -> [(oA, False), (b, True), (c, False), (d, False)]."""
    out: list[tuple[str, bool]] = []
    i, n = 0, len(expr)
    while i < n:
        m = re.match(IDENT, expr[i:])
        if not m:
            return []
        name = m.group()
        i += len(name)
        call = False
        while i < n and expr[i] in "([":
            close = ")" if expr[i] == "(" else "]"
            depth = 0
            j = i
            while j < n:
                if expr[j] in "([":
                    depth += 1
                elif expr[j] in ")]":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            call = call or close == ")"
            i = j + 1
        out.append((name, call))
        while i < n and expr[i] == " ":
            i += 1
        if i < n and expr[i] == ".":
            i += 1
            continue
        if i < n:
            return []
    return out


def _ret_class(sigs: list, idx: dict) -> str:
    """'name(args) -> QWidget *' -> 'QWidget' (when that is a known class)."""
    for s in sigs or []:
        m = re.search(r"->\s*(?:const\s+)?([A-Za-z_]\w*)", s)
        if m and m.group(1).lower() in idx.get("classes", {}):
            return idx["classes"][m.group(1).lower()]["n"]
    return ""


def _receiver(mbefore: str) -> tuple[str, str] | None:
    """(receiver expression, typed member prefix) when the cursor is after 'expr.'"""
    m = re.search(r"([\w؀-ۿ]*)$", mbefore)
    prefix = m.group(1)
    head = mbefore[:len(mbefore) - len(prefix)].rstrip()
    if not head.endswith("."):
        return None
    head = head[:-1].rstrip()
    # walk back over the receiver chain: identifiers, dots, (...) and [...]
    i = len(head)
    depth = 0
    while i > 0:
        ch = head[i - 1]
        if ch in ")]":
            depth += 1
        elif ch in "([":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and not (ch.isalnum() or ch in "_." or "؀" <= ch <= "ۿ"):
            break
        i -= 1
    expr = head[i:].strip()
    if not expr or expr[0].isdigit():
        return None
    return expr, prefix


def _sig_text(sigs: list, name: str) -> str:
    return sigs[0] if sigs else f"{name}()"


def _short(text: str, n: int = 90) -> str:
    text = (text or "").strip()
    return text if len(text) <= n else text[:n - 1] + "…"


# ============================================================================ services
def completions(code: str, line: int, col: int, path, names=None, control_class=None) -> list[Item]:
    ctx = Ctx(code, line, col, path, names, control_class)
    before, mb = ctx.before(), ctx.mbefore()
    # load "...: file names
    lm = re.search(r"""(?i)^\s*load\s+(?:package\s+)?["']([^"']*)$""", before)
    if lm:
        return _load_items(ctx, lm.group(1))
    if before and (before[-1] != mb[-1:] or ctx._open_quote(mb)):
        return []                                   # inside a comment or a string
    prefix = re.search(r"[\w؀-ۿ]*$", before).group()
    low = prefix.lower()
    rec = _receiver(mb)
    if rec is not None:
        cls = ctx.type_of(rec[0])
        if not cls:
            return []
        out = []
        for k, mem in sorted(ctx.class_members(cls).items()):
            if low and not k.startswith(low):
                continue
            if mem.kind == "method":
                out.append(Item(mem.name, "method", _short(_sig_text(mem.sigs, mem.name) +
                                                            (f"  - {mem.doc}" if mem.doc else ""), 120), 10))
            else:
                out.append(Item(mem.name, "property", f"attribute of {mem.owner}", 5))
        return out
    if re.search(r"(?i)\b(new|from)\s+[\w.]*$", mb) or re.search(r"(?i)^\s*class\s+\w+\s*(:|<)\s*\w*$", mb):
        return _class_items(ctx, low)
    items: list[Item] = []
    seen: set[str] = set()

    def add(name, kind, detail="", prio=50):
        k = name.lower()
        if k in seen or (low and not k.startswith(low)) or k == low and len(low) > 0 and kind == "variable":
            return
        seen.add(k)
        items.append(Item(name, kind, detail, prio))

    # members of the object of a braces block:  oWin { setWindowTitle("...") }
    bo = ctx.brace_object()
    if bo:
        bcls = ctx.type_of(bo)
        for k, mem in ctx.class_members(bcls).items() if bcls else []:
            add(mem.name, "method" if mem.kind == "method" else "property",
                _short(_sig_text(mem.sigs, mem.name)) if mem.kind == "method" else f"attribute of {mem.owner}", 1)
    sc = ctx.mod.scope_at(line)
    if sc is not None:
        for s in sc.locals.values():
            add(s.name, "variable", "parameter" if s.kind == "parameter" else "local variable", 2)
    cls_here = ctx.mod.class_at(line) or (sc.cls if sc else "")
    if cls_here:
        for k, mem in ctx.class_members(cls_here).items():
            add(mem.name, "method" if mem.kind == "method" else "property",
                (_sig_text(mem.sigs, mem.name) if mem.kind == "method" else "attribute") + f" ({mem.owner})", 3)
    for n, t in (names or {}).items():
        add(n, "control", f"{t} ({(control_class or {}).get(t, '')})", 4)
    for p, m, _t in ctx.all_modules():
        where = "" if p == ctx.path else f"  [{Path(p).name}]"
        for s in m.funcs.values():
            add(s.name, "function", _short(f"{s.name}({', '.join(s.params)})" + (f"  - {s.doc}" if s.doc else "") + where), 6)
        for s in m.classes.values():
            add(s.name, "class", f"class {s.name}" + (f" from {s.parent}" if s.parent else "") + where, 7)
        for s in m.globals.values():
            add(s.name, "variable", ("constant" if s.kind == "constant" else "global variable") + where, 8)
    for k in ctx.idx.get("keywords", []):
        add(k, "keyword", _short(KEYWORD_DOCS.get(k, ("keyword",))[0], 70), 9)
    for k in ri.CONSTANT_WORDS:
        add(k, "variable", KEYWORD_DOCS.get(k, ("constant",))[0], 9)
    funcs = ctx.idx.get("functions", {})
    consts = ctx.idx.get("constants", {})
    deep = len(low) >= 3
    for k, e in funcs.items():
        if low and not k.startswith(low):
            continue
        lib = e.get("lib", "")
        loaded = ctx.is_loaded(e)
        if not loaded and not deep and lib not in ("core", "stdlib"):
            continue
        prio = 10 if lib == "core" else (12 if loaded else 30)
        need = "" if loaded or not e.get("load") else f'  (load "{e["load"]}")'
        add(e["n"], "function", _short(_sig_text(e.get("s", []), e["n"]), 100) + need, prio)
    for k, e in consts.items():
        if not low or not k.startswith(low):
            continue
        loaded = ctx.is_loaded(e)
        if not loaded and not deep:
            continue
        add(e["n"], "variable", f"constant ({e.get('lib', '')})" + ("" if loaded or not e.get("load")
                                                                       else f'  (load "{e["load"]}")'), 14 if loaded else 32)
    if low:
        for k, c in ctx.idx.get("classes", {}).items():
            if k.startswith(low) and (deep or ctx.is_loaded(c)):
                add(c["n"], "class", f"class {c['n']}" + (f" from {c['p']}" if c.get("p") else "") +
                    f"  ({c.get('lib', '')})", 20 if ctx.is_loaded(c) else 34)
    # words of the file (strings / comments excluded) as the last resort
    for w in re.findall(r"\b[A-Za-z_]\w{2,}\b", ctx.masked):
        add(w, "variable", "", 60)
    items.sort(key=lambda it: (it.prio, it.name.lower()))
    return items


def _class_items(ctx: Ctx, low: str) -> list[Item]:
    out, seen = [], set()
    for p, m, _t in ctx.all_modules():
        for s in m.classes.values():
            if s.name.lower() not in seen and (not low or s.name.lower().startswith(low)):
                seen.add(s.name.lower())
                out.append(Item(s.name, "class", f"class {s.name}" + (f" from {s.parent}" if s.parent else "") +
                                ("" if p == ctx.path else f"  [{Path(p).name}]"), 1))
    for k, c in ctx.idx.get("classes", {}).items():
        if k in seen or (low and not k.startswith(low)):
            continue
        seen.add(k)
        loaded = ctx.is_loaded(c)
        name = c["n"]
        if c.get("qt") and name[:1] == "Q":
            name = "q" + name[1:]               # RingQt style: new qPushButton(win)
        out.append(Item(name, "class", f"{c.get('lib', '')}" + (f" - from {c['p']}" if c.get("p") else "") +
                        ("" if loaded or not c.get("load") else f'  (load "{c["load"]}")'), 5 if loaded else 20))
    out.sort(key=lambda it: (it.prio, it.name.lower()))
    return out


def _load_items(ctx: Ctx, typed: str) -> list[Item]:
    out = []
    root = project_root(ctx.path)
    if root is not None:
        for p in project_files(ctx.path):
            rel = p.relative_to(root).as_posix() if root in p.parents else p.name
            if ctx.path is None or p != ctx.path:
                out.append(Item(rel, "module", "project file", 1))
    home = ri.ring_home()
    if home is not None and (home / "bin" / "load").is_dir():
        for p in sorted((home / "bin" / "load").glob("*.ring")):
            out.append(Item(p.name, "module", "Ring library", 5))
    low = typed.lower()
    return [i for i in out if i.name.lower().startswith(low)] or out


# ---------------------------------------------------------------------------- signature help
def calltip(code: str, line: int, col: int, path, names=None, control_class=None) -> str:
    ctx = Ctx(code, line, col, path, names, control_class)
    mb = ctx.mbefore()
    depth, commas = 0, 0
    for i in range(len(mb) - 1, -1, -1):
        ch = mb[i]
        if ch in ")]":
            depth += 1
        elif ch in "([":
            if depth == 0:
                if ch == "[":
                    return ""
                head = mb[:i].rstrip()
                m = re.search(r"(?:(new)\s+)?((?:[\w؀-ۿ]+(?:\([^()]*\))?\s*\.\s*)*)([\w؀-ۿ]+)\s*$",
                              head, re.I)
                if not m:
                    return ""
                sigs = _callee_sigs(ctx, bool(m.group(1)), m.group(2).rstrip(" ."), m.group(3))
                return _pick_sig(sigs, commas)
            depth -= 1
        elif ch == "," and depth == 0:
            commas += 1
    return ""


def _callee_sigs(ctx: Ctx, is_new: bool, receiver: str, name: str) -> list[str]:
    if is_new:
        members = ctx.class_members(name)
        init = members.get("init")
        c = ctx.find_class(name)
        cname = (c[1].name if c and c[0] == "user" else (c[1]["n"] if c else name))
        if init is not None and init.sigs:
            return [f"new {cname}" + s[len(init.name):] for s in init.sigs]
        return [f"new {cname}(...)"] if c else []
    if receiver:
        cls = ctx.type_of(receiver)
        mem = ctx.class_members(cls).get(name.lower()) if cls else None
        return list(mem.sigs) if mem is not None and mem.kind == "method" else []
    sc = ctx.mod.scope_at(ctx.line)
    cls_here = ctx.mod.class_at(ctx.line) or (sc.cls if sc else "")
    if cls_here:
        mem = ctx.class_members(cls_here).get(name.lower())
        if mem is not None and mem.kind == "method":
            return list(mem.sigs)
    f = ctx.find_function(name)
    if f is None:
        return []
    if f[0] == "user":
        s = f[1]
        return [f"{s.name}({', '.join(s.params)})" + (f"  - {s.doc}" if s.doc else "")]
    return list(f[1].get("s", [])) or [f"{f[1]['n']}()"]


def _count_params(sig: str) -> int:
    m = re.search(r"\((.*)\)", sig.split("--->")[0].split(" -> ")[0])
    if not m:
        return 0
    inner = re.sub(r"\[.*?\]", "", m.group(1)).strip()
    return 0 if not inner or inner == "void" else inner.count(",") + 1


def _pick_sig(sigs: list[str], commas: int) -> str:
    if not sigs:
        return ""
    best = next((s for s in sigs if _count_params(s) > commas), None) or next(
        (s for s in sigs if _count_params(s) >= commas), sigs[0])
    more = len(sigs) - 1
    return best + (f"   (+{more} overload{'s' if more > 1 else ''})" if more > 0 else "")


# ---------------------------------------------------------------------------- hover
def _lib_note(e: dict) -> str:
    lib = e.get("lib", "")
    parts = []
    if lib == "core":
        parts.append("Ring core function (always available)")
    elif lib:
        parts.append(f"Library: {lib}")
    if e.get("load"):
        parts.append(f'load "{e["load"]}"')
    return " · ".join(parts)


def hover(code: str, line: int, col: int, path, names=None, control_class=None) -> str:
    ctx = Ctx(code, line, col, path, names, control_class)
    r = _resolve(ctx)
    if r is None:
        return ""
    kind, name, info = r
    fence = lambda sigs: "```ring\n" + "\n".join(sigs) + "\n```"    # noqa: E731
    if kind == "keyword":
        desc, url = KEYWORD_DOCS.get(name.lower(), (f"Ring keyword {name}", ""))
        return f"**{name}** (keyword)\n\n{desc}" + ("\n\n*F1: Ring documentation*" if url else "")
    if kind == "libfunc":
        e = info
        text = fence(e.get("s") or [f"{e['n']}()"])
        if e.get("d"):
            text += f"\n\n{e['d']}"
        note = _lib_note(e)
        if note:
            text += f"\n\n*{note}*"
        if e.get("u"):
            # (no link: a click would navigate the editor page) - F1 opens the page
            text += f"\n\n*F1: {e['u'].split('#')[0]} in the Ring documentation*"
        return text
    if kind == "libconst":
        return f"**{info['n']}** (constant)\n\n*{_lib_note(info)}*"
    if kind == "libclass":
        c = info
        text = fence([f"class {c['n']}" + (f" from {c['p']}" if c.get("p") else "")])
        if c.get("d"):
            text += f"\n\n{c['d']}"
        text += f"\n\n*{_lib_note(c)}* · {len(c.get('m', {}))} methods"
        return text
    if kind in ("userfunc", "userclass", "member", "var"):
        sym = info.get("sym")
        sigs = info.get("sigs") or []
        text = fence(sigs) if sigs else ""
        if info.get("doc"):
            text += f"\n\n{info['doc']}"
        if info.get("detail"):
            text += f"\n\n*{info['detail']}*"
        if info.get("file"):
            text += f"\n\n{Path(info['file']).name}, line {int(info.get('line', 0)) + 1}"
        return text.strip() or (sym.name if sym else name)
    return ""


def _resolve(ctx: Ctx):
    """What the word under the cursor is: (kind, name, info)."""
    word, start, end = ctx.word_at()
    if not word:
        return None
    line_m = ctx.mlines[ctx.line] if ctx.line < len(ctx.mlines) else ""
    if start < len(line_m) and line_m[start] == " " and word:
        return None                                  # inside a comment / string
    low = word.lower()
    mb = line_m[:start]
    after = line_m[end:].lstrip()
    is_call = after.startswith("(")
    rec = _receiver(mb + word)
    if rec is not None and rec[1] == word:
        cls = ctx.type_of(rec[0])
        mem = ctx.class_members(cls).get(low) if cls else None
        if mem is None:
            return None
        kind = "method" if mem.kind == "method" else "attribute"
        detail = f"{kind} of {mem.owner}"
        typ = ctx.type_of(mem.rhs, 1, mem.owner) if mem.kind == "attribute" and mem.rhs else ""
        if typ:
            detail += f" ({typ})"
        return "member", word, {"sigs": mem.sigs or [f"{mem.owner}.{mem.name}"], "doc": mem.doc, "detail": detail,
                                "file": mem.file, "line": mem.line, "member": mem}
    if re.search(r"(?i)\b(new|from)\s+$", mb) or re.search(r"(?i)^\s*class\s+\w+\s*(:|<)\s*$", mb):
        return _class_result(ctx, word)
    if re.match(r"(?i)^\s*class\s+$", mb):
        return _class_result(ctx, word)
    # locals / parameters / attributes of the current class
    sc = ctx.mod.scope_at(ctx.line)
    if sc is not None and low in sc.locals and not is_call:
        s = sc.locals[low]
        typ = ctx.type_of(word)
        return "var", word, {"sym": s, "sigs": [f"{word}" + (f" = {_short(s.rhs, 60)}" if s.rhs else "")],
                             "detail": ("parameter" if s.kind == "parameter" else "local variable") +
                             (f" of {sc.func.name}()" if sc else "") + (f" - {typ} object" if typ else ""),
                             "file": str(ctx.path) if ctx.path else "", "line": s.line}
    cls_here = ctx.mod.class_at(ctx.line) or (sc.cls if sc else "")
    if cls_here:
        mem = ctx.class_members(cls_here).get(low)
        if mem is not None and (is_call == (mem.kind == "method") or not is_call):
            return "member", word, {"sigs": mem.sigs or [f"{mem.owner}.{mem.name}"], "doc": mem.doc,
                                    "detail": f"{mem.kind} of {mem.owner}", "file": mem.file, "line": mem.line,
                                    "member": mem}
    for n, t in ctx.names.items():
        if n.lower() == low:
            return "var", word, {"sigs": [f"{n}  ({ctx.control_class.get(t, t)})"],
                                 "detail": f"form control: {t}", "file": "", "line": 0}
    if is_call or ctx.find_function(word) is not None:
        f = ctx.find_function(word)
        if f is not None:
            if f[0] == "user":
                s = f[1]
                return "userfunc", word, {"sym": s, "sigs": [f"func {s.name}" + (f" {', '.join(s.params)}" if s.params else "")],
                                          "doc": s.doc, "detail": "function of the project",
                                          "file": str(f[2]), "line": s.line}
            return "libfunc", word, f[1]
    c = ctx.find_class(word)
    if c is not None:
        return _class_result(ctx, word)
    for p, m, _t in ctx.all_modules():
        if low in m.globals:
            s = m.globals[low]
            typ = ctx.type_of(word)
            return "var", word, {"sym": s, "sigs": [f"{s.name}" + (f" = {_short(s.rhs, 60)}" if s.rhs else "")],
                                 "detail": ("constant" if s.kind == "constant" else "global variable") +
                                 (f" - {typ} object" if typ else ""), "file": str(p), "line": s.line}
    e = ctx.idx.get("constants", {}).get(low)
    if e is not None:
        return "libconst", word, e
    if low in ctx.idx.get("keywords", []) or low in KEYWORD_DOCS:
        return "keyword", word, None
    return None


def _class_result(ctx: Ctx, word: str):
    c = ctx.find_class(word)
    if c is None:
        return None
    if c[0] == "user":
        s = c[1]
        return "userclass", word, {"sym": s, "sigs": [f"class {s.name}" + (f" from {s.parent}" if s.parent else "")],
                                   "doc": s.doc, "detail": f"class of the project - {len(c[3].methods.get(s.name.lower(), {}))} methods",
                                   "file": str(c[2]), "line": s.line}
    return "libclass", word, c[1]


# ---------------------------------------------------------------------------- definition / references
def definition(code: str, line: int, col: int, path, names=None, control_class=None):
    """(file path, 0-based line) of the definition of the word under the cursor, or None."""
    ctx = Ctx(code, line, col, path, names, control_class)
    text = ctx.lines[line] if line < len(ctx.lines) else ""
    lm = ri.RX_LOAD.match(text)
    if lm:
        target = resolve_load(lm.group(2), ctx.path.parent if ctx.path else None)
        if target is not None:
            return str(library_target(target)), 0
    r = _resolve(ctx)
    if r is None:
        return None
    kind, _name, info = r
    if kind in ("userfunc", "userclass", "var", "member") and info.get("file") and int(info.get("line", -1)) >= 0:
        return info["file"], int(info["line"])
    if kind in ("libfunc", "libconst", "libclass") and info.get("f"):
        return info["f"], int(info.get("l", 0))
    return None


def references(code: str, line: int, col: int, path, names=None, control_class=None) -> list[tuple[str, int, int]]:
    ctx = Ctx(code, line, col, path, names, control_class)
    word, _s, _e = ctx.word_at()
    if not word:
        return []
    rx = re.compile(rf"(?<![\w؀-ۿ]){re.escape(word)}(?![\w؀-ۿ])", re.I)
    out = []
    for p, _m, t in ctx.all_modules():
        for n, ln in enumerate(mask(t).split("\n")):
            for m in rx.finditer(ln):
                out.append((str(p), n, m.start()))
    return out


# ---------------------------------------------------------------------------- outline
def document_symbols(code: str) -> list[dict]:
    mod = parse_source(code)
    out: list[dict] = []
    for s in mod.packages:
        out.append({"name": s.name, "kind": "package", "line": s.line, "detail": "package", "children": []})
    for s in sorted(mod.globals.values(), key=lambda s: s.line):
        out.append({"name": s.name, "kind": "constant" if s.kind == "constant" else "variable", "line": s.line,
                    "detail": _short(s.rhs, 40), "children": []})
    for s in mod.funcs.values():
        out.append({"name": s.name, "kind": "function", "line": s.line, "detail": f"({', '.join(s.params)})",
                    "children": []})
    for k, c in mod.classes.items():
        kids = [{"name": a.name, "kind": "attribute", "line": a.line, "detail": _short(a.rhs, 40), "children": []}
                for a in sorted(mod.attrs.get(k, {}).values(), key=lambda s: s.line)]
        kids += [{"name": m.name, "kind": "method", "line": m.line, "detail": f"({', '.join(m.params)})",
                  "children": []} for m in sorted(mod.methods.get(k, {}).values(), key=lambda s: s.line)]
        out.append({"name": c.name, "kind": "class", "line": c.line,
                    "detail": f"from {c.parent}" if c.parent else "", "children": kids})
    out.sort(key=lambda d: d["line"])
    return out


# ---------------------------------------------------------------------------- formatter
_OPEN = {"if", "for", "foreach", "while", "switch", "try", "do"}
_CLOSE = {"ok": "if", "endif": "if", "next": "for", "endfor": "for", "end": "while", "endwhile": "while",
          "off": "switch", "endswitch": "switch", "done": "try", "endtry": "try", "again": "do"}
_MID = {"else", "elseif", "but", "catch", "on", "other", "case"}


def _continued_lines(text: str) -> set[int]:
    """Lines that start inside a multi-line string or block comment (kept as they are)."""
    out: set[int] = set()
    line = 0
    i, n = 0, len(text)
    state = ""
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            if state:
                out.add(line)
            i += 1
            continue
        if state == "block":
            if text.startswith("*/", i):
                state = ""
                i += 2
                continue
        elif state:
            if ch == state:
                state = ""
        elif ch == "#" or text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        elif text.startswith("/*", i):
            state = "block"
            i += 2
            continue
        elif ch in "\"'`":
            state = ch
        i += 1
    return out


def format_code(text: str, indent: str = "    ") -> str:
    """Re-indent Ring code: control structures, braces, functions, classes (methods one level in)."""
    keep = _continued_lines(text)
    olines = text.split("\n")
    mlines = mask(text).split("\n")
    out: list[str] = []
    stack: list[str] = []          # open blocks: if/for/while/switch/try/do/brace
    base = 0                       # 0 at top level, 1 inside a class (its attributes and methods)
    in_func = False
    in_class = False
    for i, (orig, ml) in enumerate(zip(olines, mlines)):
        if i in keep:
            out.append(orig.rstrip("\r"))
            continue
        s = ml.strip()
        content = orig.strip()
        if not content:
            out.append("")
            continue
        tokens = re.findall(r"[A-Za-z_]\w*|[{}]", s)
        first = tokens[0].lower() if tokens else ""
        level = base + (1 if in_func else 0) + len(stack)
        if first in ("func", "def", "function") and s.lower().startswith(first + " ") or first in ("func", "def", "function") and s.lower() == first:
            stack.clear()
            in_func = True
            out.append(indent * base + content)
            continue
        if first == "class" and re.match(r"(?i)^class\s+\w", s):
            stack.clear()
            in_class, in_func, base = True, False, 1
            out.append(content)
            continue
        if first in ("package", "endpackage", "endclass", "import") and not stack and not in_func or \
                first in ("endclass", "endpackage"):
            stack.clear()
            if first in ("endclass", "endpackage"):
                in_class, base = False, 0
            in_func = False
            out.append(content)
            continue
        if first in ("endfunc", "endfunction"):
            stack.clear()
            in_func = False
            out.append(indent * base + content)
            continue
        if first == "private" and in_class and not in_func:
            out.append(indent * base + content)
            continue
        # the line's own level: a closer / middle keyword / "}" at the start goes one level back
        own = level
        if first in _CLOSE or first == "}" or (first in _MID and stack):
            own = max(base + (1 if in_func else 0), level - 1)
        out.append(indent * own + content)
        # update the block stack with every token of the line
        prev = ""
        for t in tokens:
            tl = t.lower()
            if tl in _OPEN and prev != ".":
                stack.append(tl)
            elif tl in _CLOSE:
                want = _CLOSE[tl]
                if tl == "end" and stack and stack[-1] in ("do", "while"):
                    stack.pop()
                elif want in stack:
                    while stack and stack.pop() != want:
                        pass
                elif stack:
                    stack.pop()
            elif tl == "{":
                if stack and stack[-1] in _OPEN and not stack[-1].endswith("{"):
                    stack[-1] = stack[-1] + "{"          # "if x {" : the brace closes it
                else:
                    stack.append("{")
            elif tl == "}":
                if stack:
                    stack.pop()
            prev = tl
    return "\n".join(out)


# ---------------------------------------------------------------------------- syntax check
RX_ERROR = re.compile(r"([^\r\n]*?)\s+Line \((\d+)\) Error \((\w+)\) : ([^\r\n]+)")


def syntax_check(ring_exe: str, file: Path, cwd: Path | None = None, timeout: int = 20) -> list[tuple[str, int, str]]:
    """Compile *file* without running it (``ring file -norun``): [(file name, 1-based line, message)]."""
    try:
        r = subprocess.run([ring_exe, str(file), "-norun"], cwd=str(cwd or file.parent), capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8", errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return []
    out = []
    for m in RX_ERROR.finditer((r.stdout or "") + (r.stderr or "")):
        out.append((Path(m.group(1).strip()).name or file.name, int(m.group(2)), f"{m.group(4).strip()} ({m.group(3)})"))
    return out
