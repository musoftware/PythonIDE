"""Python quick fixes: missing imports and pip installs.

* an unknown name -> ``import numpy as np`` (common aliases), ``from pathlib import Path`` (standard library
  names), ``import json`` (standard modules), ``import requests`` (installed modules), ``from helpers import
  greet`` (top-level names of the project's own files)
* an unresolved import (``import yaml``) -> "Install 'PyYAML' with pip" into the interpreter Run uses (the
  project's .venv first); requirements.txt gets the package when the project has one
"""
from __future__ import annotations

import ast
import builtins
import json
import keyword
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import Action, Context, register
from . import installers
from .tables import PY_ALIASES, PY_DISTRIBUTIONS, PY_STDLIB_NAMES

STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"tkinter", "sqlite3", "asyncio"}
BUILTINS = set(dir(builtins)) | set(keyword.kwlist) | set(getattr(keyword, "softkwlist", [])) | {"self", "cls", "__file__", "__name__", "__doc__"}
SKIP_DIRS = {".venv", "venv", "env", "__pycache__", ".git", "node_modules", "site-packages", "build", "dist",
             "_build", ".radide_backup", "_deleted", ".tox", ".mypy_cache"}
_IMPORT_LINE = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import\b|import\s+(.+))")

# ============================================================================ installed modules (per interpreter)
_SITE: dict[str, set] = {}
_SITE_BUSY: set = set()
_SITE_LOCK = threading.Lock()


def _scan_paths(paths) -> set:
    out = set()
    for d in paths or []:
        p = Path(d)
        if not p.is_dir() or "python3" in p.name.lower() and p.suffix == ".zip":
            continue
        try:
            for e in p.iterdir():
                n = e.name
                if n.endswith((".dist-info", ".egg-info", ".pth")) or n.startswith(("_", ".")) and n != "__future__":
                    continue
                base = n.split(".", 1)[0]
                if e.is_dir() or n.endswith((".py", ".pyd", ".so", ".pyc")):
                    out.add(base)
        except OSError:
            continue
    return out


def _load_site(py: str) -> set:
    try:
        r = subprocess.run([py, "-I", "-c", "import sys, json; print(json.dumps(sys.path))"], capture_output=True,
                           text=True, timeout=20, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        paths = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 and r.stdout.strip() else []
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        paths = []
    return _scan_paths([p for p in paths if p and "site-packages" in p.replace("\\", "/").lower()
                        or p and "dist-packages" in p.lower()])


def installed_modules(py: str, wait: bool = True) -> set | None:
    """Top-level modules of the interpreter's site-packages (cached; None = not known yet when wait=False)."""
    with _SITE_LOCK:
        if py in _SITE:
            return _SITE[py]
        busy = py in _SITE_BUSY
        if not busy:
            _SITE_BUSY.add(py)

    def fill():
        mods = _load_site(py)
        with _SITE_LOCK:
            _SITE[py] = mods
            _SITE_BUSY.discard(py)
    if not busy:
        th = threading.Thread(target=fill, daemon=True, name="quickfix-site")
        th.start()
    if not wait:
        return None
    # Quick Actions (not the light bulb): the scan takes ~0.1 s; the GUI keeps painting while we wait (at most 3 s,
    # the light bulb / first editor already started it in the background)
    try:
        from PyQt6.QtCore import QCoreApplication
        pump = QCoreApplication.processEvents if QCoreApplication.instance() is not None else None
    except ImportError:
        pump = None
    end = time.monotonic() + 3
    while time.monotonic() < end:
        with _SITE_LOCK:
            if py in _SITE:
                return _SITE[py]
        if pump is not None:
            pump()
        time.sleep(0.01)
    return None


def forget_site(py: str | None = None) -> None:
    with _SITE_LOCK:
        if py is None:
            _SITE.clear()
        else:
            _SITE.pop(py, None)


# ============================================================================ the file's own names
def defined_names(text: str) -> set:
    names = set()
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        tree = None
    if tree is not None:
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(n.name)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                names.add(n.id)
            elif isinstance(n, ast.arg):
                names.add(n.arg)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    names.add((a.asname or a.name).split(".")[0])
            elif isinstance(n, ast.ExceptHandler) and n.name:
                names.add(n.name)
            elif isinstance(n, (ast.Global, ast.Nonlocal)):
                names.update(n.names)
        return names
    # incomplete code: a regex approximation
    for m in re.finditer(r"^\s*(?:async\s+)?(?:def|class)\s+(\w+)", text, re.M):
        names.add(m.group(1))
    for m in re.finditer(r"^\s*([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*=(?!=)", text, re.M):
        names.update(x.strip() for x in m.group(1).split(","))
    for m in re.finditer(r"^\s*import\s+(.+)$", text, re.M):
        for part in m.group(1).split(","):
            bits = part.split(" as ")
            names.add((bits[1] if len(bits) > 1 else bits[0]).strip().split(".")[0])
    for m in re.finditer(r"^\s*from\s+[\w.]+\s+import\s+\(?([^)\n]+)", text, re.M):
        for part in m.group(1).split(","):
            bits = part.split(" as ")
            names.add((bits[1] if len(bits) > 1 else bits[0]).strip())
    for m in re.finditer(r"\bfor\s+([\w\s,]+?)\s+in\b|\bas\s+(\w+)|\bdef\s+\w+\s*\(([^)]*)\)", text):
        for g in m.groups():
            if g:
                names.update(x.strip().split("=")[0].split(":")[0].strip("* ") for x in g.split(","))
    return {n for n in names if n}


def project_names(folder: Path, limit: int = 400, cached_only: bool = False) -> dict:
    """{top-level name: [dotted module]} of the project's .py files (cached for 20 s per folder)."""
    key = str(folder).lower()
    hit = _PROJ.get(key)
    if hit is not None and (cached_only or time.monotonic() - hit[0] < 20):
        return hit[1]
    if cached_only:
        return {}
    out: dict = {}
    n = 0
    for dirpath, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if not f.endswith(".py"):
                continue
            n += 1
            if n > limit:
                break
            p = Path(dirpath) / f
            try:
                rel = p.relative_to(folder).with_suffix("")
                text = p.read_text(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                continue
            mod = ".".join(rel.parts)
            if mod.endswith(".__init__"):
                mod = mod[:-9]
            for m in re.finditer(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z_]\w*)|^([A-Za-z_]\w*)\s*(?::[^=\n]+)?=(?!=)",
                                 text, re.M):
                name = m.group(1) or m.group(2)
                if name and not name.startswith("_"):
                    out.setdefault(name, []).append(mod)
    _PROJ[key] = (time.monotonic(), out)
    return out


_PROJ: dict = {}


# ============================================================================ edits
def import_insert_line(text: str) -> int:
    """Line index where a new top-level import goes: after the first import block, else after the docstring /
    __future__ imports / leading comments."""
    lines = text.split("\n")
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        tree = None
    if tree is not None and tree.body:
        body = tree.body
        i = 0
        after = 0
        if isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                and isinstance(body[0].value.value, str):
            after = body[0].end_lineno or 0
            i = 1
        last_imp = None
        while i < len(body) and isinstance(body[i], (ast.Import, ast.ImportFrom)):
            last_imp = body[i]
            i += 1
        if last_imp is None:                       # imports later in the file (after a constant / comment)?
            first = next((b for b in body if isinstance(b, (ast.Import, ast.ImportFrom))), None)
            if first is not None and first.lineno <= 40:
                j = body.index(first)
                last_imp = first
                while j + 1 < len(body) and isinstance(body[j + 1], (ast.Import, ast.ImportFrom)):
                    j += 1
                    last_imp = body[j]
        if last_imp is not None:
            return last_imp.end_lineno or last_imp.lineno
        k = after
        while k < len(lines) and (lines[k].startswith("#") or (not lines[k].strip() and k < after + 1)):
            k += 1
        return k
    hits = [i for i, ln in enumerate(lines[:80]) if re.match(r"(?:import|from)\s+\w", ln)]
    if hits:
        return hits[-1] + 1
    k = 0
    while k < len(lines) and lines[k].startswith("#"):
        k += 1
    return k


def import_edit(text: str, stmt: str) -> list:
    """Edits adding *stmt* ("import x" / "from m import n"); joins an existing one-line "from m import ..."."""
    lines = text.split("\n")
    if stmt in (ln.strip() for ln in lines):
        return []
    m = re.match(r"from\s+([\w.]+)\s+import\s+(\w+)$", stmt)
    if m:
        mod, name = m.groups()
        for i, ln in enumerate(lines):
            mm = re.match(rf"^from\s+{re.escape(mod)}\s+import\s+([\w\s,]+?)\s*$", ln)
            if mm and "(" not in ln:
                have = [x.strip() for x in mm.group(1).split(",") if x.strip()]
                if name in have:
                    return []
                return [[i, 0, i, len(ln), f"from {mod} import {', '.join(have + [name])}"]]
    at = import_insert_line(text)
    blank_after = at < len(lines) and lines[at].strip() and not _IMPORT_LINE.match(lines[at]) and \
        not any(_IMPORT_LINE.match(x) for x in lines[max(0, at - 1):at])
    if at >= len(lines):
        last = len(lines) - 1
        return [[last, len(lines[last]), last, len(lines[last]), "\n" + stmt]]
    return [[at, 0, at, 0, stmt + "\n" + ("\n" if blank_after else "")]]


# ============================================================================ provider
def _unresolved_import(ctx: Context) -> list[str]:
    """Module names imported on the caret line."""
    m = _IMPORT_LINE.match(ctx.line_text)
    if not m:
        return []
    if m.group(1):
        mods = [m.group(1)]
    else:
        mods = [p.split(" as ")[0].strip() for p in m.group(2).split(",")]
    mods = [x for x in mods if x and not x.startswith(".")]
    named = [n for n in ctx.diag_names() if any(n == x or x.startswith(n + ".") or n.startswith(x) for x in mods)]
    if named:
        return named
    if ctx.word:                            # the module the caret is on
        hit = [x for x in mods if ctx.word in x.split(".")]
        if hit:
            return hit
    return mods[:1] if len(mods) == 1 else []


def _local_module(folder: Path, top: str, path: Path) -> bool:
    for base in {Path(folder), Path(path).parent}:
        if (base / f"{top}.py").is_file() or (base / top / "__init__.py").is_file() or (base / top).is_dir():
            return True
    return False


def distribution(mod: str) -> str:
    return PY_DISTRIBUTIONS.get(mod) or PY_DISTRIBUTIONS.get(mod.split(".")[0]) or mod.split(".")[0]


def _pip_action(ctx: Context, mod: str, preferred: bool, also_import: str = "") -> Action:
    dist = distribution(mod)
    py = installers.python_for(ctx.win, ctx.path)
    folder = ctx.project_folder
    req = (folder / "requirements.txt").is_file()
    title = f"Install '{dist}' with pip" + (f" and add '{also_import}'" if also_import else "")
    detail = f"{py} -m pip install {dist}" + ("\n+ requirements.txt" if req else "")

    def run(win, ed, dist=dist, py=py):
        def done(ok):
            forget_site(py)
        installers.pip_install(win, ctx.path, dist, folder, done)
    edits = ctx.edit(import_edit(ctx.text, also_import)) if also_import else None
    return Action(title, edits=edits or None, run=run, detail=detail, preferred=preferred, fixes=list(ctx.diagnostics))


def provide(ctx: Context) -> list[Action]:
    out: list[Action] = []
    py = installers.python_for(ctx.win, ctx.path)
    site = installed_modules(py, wait=not ctx.cheap)
    folder = ctx.project_folder

    def available(mod: str) -> bool | None:
        top = mod.split(".")[0]
        if top in STDLIB or _local_module(folder, top, ctx.path):
            return True
        if site is None:
            return None
        return top in site

    # 1. the caret is on an import line: is the module there?
    for mod in _unresolved_import(ctx):
        ok = available(mod)
        if ok is False or (ok is None and any(mod.split(".")[0] in n for n in ctx.diag_names())):
            out.append(_pip_action(ctx, mod, preferred=True))
    if out:
        return out
    # 2. unknown names
    defined = defined_names(ctx.text)
    for name in [n.split(".")[0] for n in ctx.diag_names()] + ([ctx.word] if ctx.word else []):
        if not name or name in BUILTINS or (name in defined and name not in ctx.diag_names()):
            continue
        from . import qualified_before
        if name == ctx.word and qualified_before(ctx):      # the caret on "array" of np.array: fix "np"
            continue
        found = False
        if name in PY_ALIASES:
            stmt = PY_ALIASES[name]
            mod = re.findall(r"(?:import|from)\s+([\w.]+)", stmt)[0]
            out.append(Action(stmt, edits=ctx.edit(import_edit(ctx.text, stmt)), preferred=True,
                              fixes=list(ctx.diagnostics)))
            if available(mod) is False:
                out.append(_pip_action(ctx, mod, preferred=False, also_import=stmt))
            found = True
        if name in PY_STDLIB_NAMES and PY_STDLIB_NAMES[name]:
            stmt = f"from {PY_STDLIB_NAMES[name]} import {name}"
            out.append(Action(stmt, edits=ctx.edit(import_edit(ctx.text, stmt)), preferred=not found,
                              fixes=list(ctx.diagnostics)))
            found = True
        if name in STDLIB or (site is not None and name in site) or _local_module(folder, name, ctx.path):
            stmt = f"import {name}"
            out.append(Action(stmt, edits=ctx.edit(import_edit(ctx.text, stmt)), preferred=not found,
                              fixes=list(ctx.diagnostics)))
            found = True
        if not found:
            this_mod = ""
            try:
                this_mod = ".".join(Path(ctx.path).resolve().relative_to(Path(folder).resolve()).with_suffix("").parts)
            except (OSError, ValueError):
                pass
            for mod in project_names(folder, cached_only=ctx.cheap).get(name, [])[:3]:
                if mod == this_mod or not mod:
                    continue
                stmt = f"from {mod} import {name}"
                out.append(Action(stmt, edits=ctx.edit(import_edit(ctx.text, stmt)), preferred=not found,
                                  fixes=list(ctx.diagnostics)))
                found = True
        if not found and name in PY_DISTRIBUTIONS and available(name) is False:
            out.append(_pip_action(ctx, name, preferred=True, also_import=f"import {name}"))
        if out:
            break
    return out


register(("python",), provide)

__all__ = ["provide", "import_edit", "import_insert_line", "defined_names", "installed_modules", "distribution",
           "project_names", "forget_site"]
