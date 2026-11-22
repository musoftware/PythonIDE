"""JavaScript / TypeScript and PHP quick fixes.

JavaScript / TypeScript:
* ``import x from 'lodash'`` / ``require('lodash')`` with no node_modules/lodash -> "Install 'lodash' with npm"
  (TypeScript: also "... and '@types/lodash' (dev)"; TS7016 "no declaration file" -> "@types/x" only)
* a name exported by another file of the project -> ``import { greet } from './util';`` (``require`` in CommonJS)

PHP:
* a class declared in the project -> ``use App\\Models\\User;``
* ``use Monolog\\Logger;`` with no autoload for the namespace -> "composer require monolog/monolog" (a short table
  of well-known packages + symfony/<component>)
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import Action, Context, import_block_insert, qualified_before, register
from . import installers
from .tables import NODE_BUILTINS, PHP_PACKAGES, TYPED_PACKAGES

SKIP = {"node_modules", ".git", "dist", "build", "out", "coverage", ".next", "vendor", ".venv", "__pycache__"}
JS_EXT = (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".mts", ".cts")
_SPEC = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(?\s*|\brequire\s*\(\s*)(['"])([^'"]+)\1""")


def _root(path: Path, marker: str) -> Path:
    p = Path(path).resolve().parent
    for d in [p, *p.parents]:
        if (d / marker).is_file():
            return d
    return p


def package_name(spec: str) -> str:
    spec = spec[5:] if spec.startswith("node:") else spec
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") and len(parts) > 1 else parts[0]


def _installed(root: Path, pkg: str, start: Path) -> bool:
    for d in [Path(start).resolve().parent, *Path(start).resolve().parents]:
        if (d / "node_modules" / pkg).is_dir():
            return True
        if d == root.parent:
            break
    return False


def _walk(folder: Path, exts, limit=600):
    n = 0
    for dirpath, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]
        for f in files:
            if f.endswith(exts):
                n += 1
                if n > limit:
                    return
                yield Path(dirpath) / f


# ============================================================================ JavaScript / TypeScript
def _module_actions(ctx: Context) -> list[Action]:
    specs = [m.group(2) for m in _SPEC.finditer(ctx.line_text)]
    diag_specs = [m.group(1) for d in ctx.diagnostics
                  for m in re.finditer(r"module ['\"`]([^'\"`]+)['\"`]", d.get("message", ""))]
    no_types = any("declaration file" in d.get("message", "") for d in ctx.diagnostics)
    specs = [s for s in specs if not diag_specs or s in diag_specs] or diag_specs
    out = []
    for spec in specs:
        if spec.startswith((".", "/")) or spec.startswith("node:"):
            continue
        pkg = package_name(spec)
        if pkg in NODE_BUILTINS:
            continue
        root = _root(ctx.path, "package.json")
        ts = ctx.language == "typescript"
        types = f"@types/{pkg.replace('@', '').replace('/', '__')}" if pkg.startswith("@") else f"@types/{pkg}"
        if _installed(root, pkg, ctx.path):
            if ts and no_types and pkg not in TYPED_PACKAGES:
                out.append(Action(f"Install '{types}' with npm (dev)", preferred=True, fixes=list(ctx.diagnostics),
                                  run=lambda win, ed, root=root, t=types: installers.npm_install(win, root, t, True),
                                  detail=f"npm install --save-dev {types}\n(in {root})"))
            continue
        out.append(Action(f"Install '{pkg}' with npm", preferred=True, fixes=list(ctx.diagnostics),
                          run=lambda win, ed, root=root, p=pkg: installers.npm_install(win, root, p),
                          detail=f"npm install {pkg}\n(in {root})"))
        if ts and pkg not in TYPED_PACKAGES:
            def both(win, ed, root=root, p=pkg, t=types):
                installers.npm_install(win, root, p, then=lambda ok: ok and installers.npm_install(win, root, t, True))
            out.append(Action(f"Install '{pkg}' and '{types}' (dev) with npm", run=both,
                              detail=f"npm install {pkg}\nnpm install --save-dev {types}"))
    return out


def _declared_js(text: str, name: str) -> bool:
    n = re.escape(name)
    return bool(re.search(rf"\b(?:const|let|var|function\*?|class|interface|type|enum|namespace)\s+{n}\b", text)
                or re.search(rf"\bimport\b[^;\n]*\b{n}\b[^;\n]*\bfrom\b", text)
                or re.search(rf"\b(?:const|let|var)\s*\{{[^}}]*\b{n}\b[^}}]*\}}\s*=", text)
                or re.search(rf"\(\s*[^)]*\b{n}\b[^)]*\)\s*(?:=>|\{{)", text))


def _exports(folder: Path, name: str, exclude: Path) -> list[tuple[Path, bool]]:
    """Files exporting *name*: [(file, is_default)]."""
    n = re.escape(name)
    rx = re.compile(rf"\bexport\s+(default\s+)?(?:async\s+)?(?:function\*?|class|const|let|var|interface|type|enum|"
                    rf"abstract\s+class)\s+{n}\b|\bexport\s*\{{[^}}]*\b{n}\b[^}}]*\}}|"
                    rf"\bmodule\.exports\.{n}\s*=|\bexports\.{n}\s*=")
    out = []
    ex = str(Path(exclude).resolve()).lower()
    for f in _walk(folder, JS_EXT):
        if str(f.resolve()).lower() == ex:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = rx.search(text)
        if m:
            out.append((f, bool(m.group(1))))
        if len(out) >= 3:
            break
    return out


def _import_actions(ctx: Context) -> list[Action]:
    names = [n for n in ctx.diag_names() if re.fullmatch(r"[A-Za-z_$][\w$]*", n)]
    if ctx.word and ctx.word not in names and not qualified_before(ctx):
        names.append(ctx.word)
    out = []
    root = _root(ctx.path, "package.json")
    if ctx.cheap:
        return out
    esm_js = False
    try:
        esm_js = json.loads((root / "package.json").read_text(encoding="utf-8")).get("type") == "module"
    except (OSError, ValueError, AttributeError):
        pass
    commonjs = "require(" in ctx.text and not re.search(r"^\s*import\s", ctx.text, re.M) and ctx.language != "typescript"
    quote = '"' if re.search(r"""^\s*import[^'\n]*"[^"]+";?\s*$""", ctx.text, re.M) else "'"
    semi = ";" if re.search(r"^\s*import .*;\s*$", ctx.text, re.M) or not re.search(r"^\s*import\s", ctx.text, re.M) else ""
    for name in names:
        if _declared_js(ctx.text, name) or name in ("console", "window", "document", "require", "module", "process"):
            continue
        for f, default in _exports(root, name, ctx.path):
            rel = os.path.relpath(f, Path(ctx.path).parent).replace("\\", "/")
            if not rel.startswith("."):
                rel = "./" + rel
            if not (esm_js and f.suffix in (".js", ".mjs")):
                rel = re.sub(r"\.(?:js|jsx|ts|tsx|mts|cts)$", "", rel)
            if commonjs:
                stmt = f"const {name if default else '{ ' + name + ' }'} = require({quote}{rel}{quote});"
            else:
                stmt = f"import {name if default else '{ ' + name + ' }'} from {quote}{rel}{quote}{semi}"
            rx = re.compile(r"^\s*(?:import\s|(?:const|let|var)\s+.*=\s*require\()")
            edits = import_block_insert(ctx.lines, rx, stmt)
            out.append(Action(f"Add import from '{rel}'", edits=ctx.edit(edits), preferred=not out,
                              detail=stmt, fixes=list(ctx.diagnostics)))
        if out:
            break
    return out


def provide_js(ctx: Context) -> list[Action]:
    return _module_actions(ctx) or _import_actions(ctx)


# ============================================================================ PHP
_PHP_USE = re.compile(r"^\s*use\s+([\w\\]+)(?:\s+as\s+\w+)?\s*;", re.M)


def _autoloaded(root: Path, ns: str) -> bool:
    prefixes = []
    try:
        data = json.loads((root / "composer.json").read_text(encoding="utf-8"))
        for sec in ("autoload", "autoload-dev"):
            prefixes += list((data.get(sec) or {}).get("psr-4", {}).keys())
            prefixes += list((data.get(sec) or {}).get("psr-0", {}).keys())
    except (OSError, ValueError, AttributeError):
        pass
    psr4 = root / "vendor" / "composer" / "autoload_psr4.php"
    try:
        prefixes += [p.replace("\\\\", "\\") for p in re.findall(r"'([\w\\\\]+)'\s*=>", psr4.read_text(
            encoding="utf-8", errors="replace"))]
    except OSError:
        pass
    ns = ns.lstrip("\\") + "\\"
    return any(ns.startswith(p) for p in prefixes if p)


def composer_package(ns: str) -> str:
    parts = ns.lstrip("\\").split("\\")
    for k in (2, 1):
        key = "\\".join(parts[:k])
        if key in PHP_PACKAGES:
            return PHP_PACKAGES[key]
    if parts[:2] == ["Symfony", "Component"] and len(parts) > 2:
        return "symfony/" + re.sub(r"(?<!^)(?=[A-Z])", "-", parts[2]).lower()
    return ""


def provide_php(ctx: Context) -> list[Action]:
    out = []
    root = _root(ctx.path, "composer.json")
    m = re.match(r"^\s*use\s+\\?([\w\\]+)", ctx.line_text) or re.search(r"\bnew\s+\\([\w\\]+)", ctx.line_text)
    if m and "\\" in m.group(1) and not _autoloaded(root, m.group(1)):
        pkg = composer_package(m.group(1))
        if pkg:
            out.append(Action(f"Install '{pkg}' with Composer", preferred=True, fixes=list(ctx.diagnostics),
                              run=lambda win, ed, root=root, p=pkg: installers.composer_require(win, root, p),
                              detail=f"composer require {pkg}\n(in {root})"))
            return out
    names = [n.split("\\")[-1] for n in ctx.diag_names()]
    if ctx.word and ctx.word[:1].isupper() and ctx.word not in names:
        names.append(ctx.word)
    if ctx.cheap:
        return out
    imported = {u.split("\\")[-1] for u in _PHP_USE.findall(ctx.text)}
    for name in names:
        if name in imported or re.search(rf"\b(?:class|interface|trait|enum)\s+{re.escape(name)}\b", ctx.text):
            continue
        for f in _walk(root, (".php",), 800):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not re.search(rf"\b(?:class|interface|trait|enum)\s+{re.escape(name)}\b", text):
                continue
            nsm = re.search(r"^\s*namespace\s+([\w\\]+)\s*;", text, re.M)
            if not nsm:
                continue
            full = f"{nsm.group(1)}\\{name}"
            own = re.search(r"^\s*namespace\s+([\w\\]+)\s*;", ctx.text, re.M)
            if own and own.group(1) == nsm.group(1):
                continue
            stmt = f"use {full};"
            edits = import_block_insert(ctx.lines, re.compile(r"^\s*use\s+[\w\\]+"), stmt,
                                        after=re.compile(r"^\s*(?:namespace\s|<\?php)"))
            out.append(Action(stmt, edits=ctx.edit(edits), preferred=not out, fixes=list(ctx.diagnostics)))
            if len(out) >= 3:
                break
        if out:
            break
    return out


register(("javascript", "typescript"), provide_js)
register(("php",), provide_php)

__all__ = ["provide_js", "provide_php", "package_name", "composer_package"]
