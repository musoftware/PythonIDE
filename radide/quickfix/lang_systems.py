"""Rust, Go and Java quick fixes.

Rust:  ``HashMap`` with no ``use`` -> ``use std::collections::HashMap;`` (table of std items); ``use serde::...`` /
       ``serde_json::to_string`` with no dependency in Cargo.toml -> "cargo add serde_json".
Go:    ``strings.ToUpper`` with no import -> adds "strings" to the import block (stdlib table); an import path
       (``github.com/x/y``) missing from go.mod -> "go get github.com/x/y".
Java:  ``ArrayList`` with no import -> ``import java.util.ArrayList;`` (table of common JDK classes).
"""
from __future__ import annotations

import re
from pathlib import Path

from . import Action, Context, import_block_insert, qualified_before, register
from . import installers
from .tables import GO_STDLIB, JAVA_CLASSES, RUST_BUILTIN_CRATES, RUST_STD


def _root(path: Path, marker: str) -> Path | None:
    p = Path(path).resolve().parent
    for d in [p, *p.parents]:
        if (d / marker).is_file():
            return d
    return None


# ============================================================================ Rust
def cargo_dependencies(cargo_toml: Path) -> set:
    deps, section = set(), ""
    try:
        text = cargo_toml.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return deps
    for ln in text.splitlines():
        s = ln.strip()
        m = re.match(r"^\[(.+)\]$", s)
        if m:
            section = m.group(1)
            dm = re.match(r"^(?:target\..+\.)?(?:dev-|build-)?dependencies\.([\w-]+)$", section)
            if dm:
                deps.add(dm.group(1).replace("-", "_"))
            continue
        if re.match(r"^(?:target\..+\.)?(?:dev-|build-)?dependencies$", section):
            m = re.match(r"^([\w-]+)\s*=", s)
            if m:
                deps.add(m.group(1).replace("-", "_"))
                pm = re.search(r'package\s*=\s*"([\w-]+)"', s)
                if pm:
                    deps.add(pm.group(1).replace("-", "_"))
    return deps


def _rust_uses(text: str) -> set:
    names = set()
    for m in re.finditer(r"^\s*(?:pub\s+)?use\s+([^;]+);", text, re.M):
        body = m.group(1)
        for part in re.split(r"[{},]", body):
            part = part.strip()
            if part:
                names.add(part.split(" as ")[-1].split("::")[-1].strip())
    return names


def provide_rust(ctx: Context) -> list[Action]:
    out: list[Action] = []
    root = _root(ctx.path, "Cargo.toml")
    deps = cargo_dependencies(root / "Cargo.toml") if root else set()
    local_mods = set(re.findall(r"^\s*(?:pub\s+)?mod\s+(\w+)", ctx.text, re.M))
    # 1. a crate that is not a dependency (use foo::..., foo::bar(), extern crate foo)
    crates = []
    m = re.match(r"^\s*(?:pub\s+)?use\s+(?:::)?(\w+)", ctx.line_text) or \
        re.match(r"^\s*extern\s+crate\s+(\w+)", ctx.line_text)
    if m:
        crates.append(m.group(1))
    for n in ctx.diag_names():
        crates.append(n.split("::")[0])
    pm = re.match(r"\s*::", ctx.line_text[ctx.wend:])
    if ctx.word and pm and not qualified_before(ctx) and ctx.word[:1].islower():
        crates.append(ctx.word)
    for c in crates:
        if not c or c in RUST_BUILTIN_CRATES or c in deps or c in local_mods or c in RUST_STD or root is None:
            continue
        if c[:1].isupper():
            continue
        crate = c
        out.append(Action(f"Add crate '{crate}' (cargo add)", preferred=True, fixes=list(ctx.diagnostics),
                          run=lambda win, ed, root=root, cr=crate: installers.cargo_add(win, root, cr),
                          detail=f"cargo add {crate}\n(in {root})"))
        return out
    # 2. a std item with no use
    names = [n for n in ctx.diag_names() if "::" not in n]
    if ctx.word and ctx.word not in names and not qualified_before(ctx) and not pm:
        names.append(ctx.word)
    have = _rust_uses(ctx.text)
    for name in names:
        if name in RUST_STD and name not in have and not re.search(
                rf"\b(?:struct|enum|trait|type|fn|mod)\s+{re.escape(name)}\b", ctx.text):
            stmt = f"use {RUST_STD[name]};"
            edits = import_block_insert(ctx.lines, re.compile(r"^\s*use\s"), stmt, sort_key=lambda s: s.strip(),
                                        after=re.compile(r"^\s*(?:#!\[|//!)"))
            out.append(Action(stmt, edits=ctx.edit(edits), preferred=True, fixes=list(ctx.diagnostics)))
            break
    return out


# ============================================================================ Go
def _go_imports(text: str) -> set:
    paths = set(re.findall(r'^\s*import\s+(?:\w+\s+)?"([^"]+)"', text, re.M))
    for block in re.findall(r"^\s*import\s*\(([^)]*)\)", text, re.M | re.S):
        paths |= set(re.findall(r'"([^"]+)"', block))
    return paths


def go_import_edit(text: str, path: str) -> list:
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if re.match(r"^\s*import\s*\($", ln):
            j = i + 1
            entries = []
            while j < len(lines) and not lines[j].strip().startswith(")"):
                entries.append(j)
                j += 1
            ins = j
            for k in entries:
                m = re.search(r'"([^"]+)"', lines[k])
                if m and m.group(1) > path and "." not in m.group(1).split("/")[0]:
                    ins = k
                    break
            return [[ins, 0, ins, 0, f'\t"{path}"\n']]
    for i, ln in enumerate(lines):
        m = re.match(r'^\s*import\s+("[^"]+")\s*$', ln)
        if m:
            return [[i, 0, i, len(ln), f'import (\n\t{m.group(1)}\n\t"{path}"\n)']]
    for i, ln in enumerate(lines):
        if re.match(r"^\s*package\s+\w+", ln):
            return [[i + 1, 0, i + 1, 0, f'\nimport "{path}"\n']] if i + 1 < len(lines) else \
                [[i, len(ln), i, len(ln), f'\n\nimport "{path}"']]
    return [[0, 0, 0, 0, f'import "{path}"\n']]


def provide_go(ctx: Context) -> list[Action]:
    out: list[Action] = []
    imports = _go_imports(ctx.text)
    root = _root(ctx.path, "go.mod")
    # 1. an import path that go.mod does not require
    m = re.search(r'"((?:[\w-]+\.)+[\w-]+/[^"]+)"', ctx.line_text)
    if m and root is not None:
        path = m.group(1)
        try:
            gomod = (root / "go.mod").read_text(encoding="utf-8", errors="replace")
        except OSError:
            gomod = ""
        module = re.search(r"^module\s+(\S+)", gomod, re.M)
        if not (module and path.startswith(module.group(1))) and path.split("/")[0] != "" and \
                not re.search(rf"^\s*(?:require\s+)?{re.escape(path)}\s+v", gomod, re.M) and \
                not any(path.startswith(r) for r in re.findall(r"^\s*(?:require\s+)?([\w.\-/]+)\s+v[\d.]", gomod, re.M)):
            out.append(Action(f"go get {path}", preferred=True, fixes=list(ctx.diagnostics),
                              run=lambda win, ed, root=root, p=path: installers.go_get(win, root, p),
                              detail=f"go get {path}\n(in {root})"))
            return out
    # 2. pkg.Func with no import of a stdlib package
    names = [n for n in ctx.diag_names()]
    if ctx.word and re.match(r"\s*\.", ctx.line_text[ctx.wend:]) and not qualified_before(ctx):
        names.append(ctx.word)
    for name in names:
        path = GO_STDLIB.get(name)
        if path and path not in imports and not re.search(rf"\b{re.escape(name)}\s*:?=", ctx.text):
            out.append(Action(f'import "{path}"', edits=ctx.edit(go_import_edit(ctx.text, path)), preferred=True,
                              fixes=list(ctx.diagnostics)))
            break
    return out


# ============================================================================ Java
def provide_java(ctx: Context) -> list[Action]:
    out: list[Action] = []
    names = [n for n in ctx.diag_names()]
    if ctx.word and ctx.word not in names and not qualified_before(ctx):
        names.append(ctx.word)
    imported = set(re.findall(r"^\s*import\s+[\w.]+\.(\w+)\s*;", ctx.text, re.M))
    wild = set(re.findall(r"^\s*import\s+([\w.]+)\.\*\s*;", ctx.text, re.M))
    for name in names:
        pkg = JAVA_CLASSES.get(name)
        if not pkg or name in imported or pkg in wild or pkg == "java.lang":
            continue
        if re.search(rf"\b(?:class|interface|enum|record)\s+{re.escape(name)}\b", ctx.text):
            continue
        stmt = f"import {pkg}.{name};"
        edits = import_block_insert(ctx.lines, re.compile(r"^\s*import\s"), stmt, sort_key=lambda s: s.strip(),
                                    after=re.compile(r"^\s*package\s"))
        out.append(Action(stmt, edits=ctx.edit(edits), preferred=True, fixes=list(ctx.diagnostics)))
        if pkg + ".*" not in wild:
            star = f"import {pkg}.*;"
            out.append(Action(star, edits=ctx.edit(import_block_insert(ctx.lines, re.compile(r"^\s*import\s"), star,
                                                                         sort_key=lambda s: s.strip(),
                                                                         after=re.compile(r"^\s*package\s")))))
        break
    return out


register(("rust",), provide_rust)
register(("go",), provide_go)
register(("java",), provide_java)

__all__ = ["provide_rust", "provide_go", "provide_java", "cargo_dependencies", "go_import_edit"]
