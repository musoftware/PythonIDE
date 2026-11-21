"""Fallback for language-server extensions: run the server an extension ships through RAD IDE's own LSP client.

Most language extensions are a thin vscode-languageclient wrapper around a server module (``server.js``,
``dist/languageserver.js`` ...) or a server binary. They normally run inside the extension host (their
providers reach Monaco through radide/vsx/lsp_client.py). When that is not possible - Node / the host is
missing, or the extension failed to activate (an API RAD IDE lacks) - ``register(ext)`` finds the server
and adds it to ``radide.lsp.SERVERS`` for the extension's languages, so radide/lsp.py starts it like any
other ready-made server (``node <module> --stdio`` or ``<binary> --stdio``). Languages that already have a
built-in server are left alone.

Setting ``vsx/lsp_fallback``: "auto" (default: only after a failed activation / without a host),
"never".
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# relative paths tried first, then a search by name
CANDIDATES = [
    "server.js", "server/out/server.js", "server/dist/server.js", "server/server.js", "out/server.js", "out/server/server.js",
    "dist/server.js", "dist/languageserver.js", "dist/language-server.js", "dist/server/server.js",
    "out/src/server.js", "lib/server.js", "server/out/main.js", "dist/serverMain.js", "dist/node/server.js",
]
NAME_RX = re.compile(r"(language[-_]?server|langserver|lsp[-_]?server|^server)(?!.*(web|browser|worker\.js$))", re.I)
SKIP_DIRS = {"node_modules", "test", "tests", "web", "browser", "media", "images", "syntaxes", "snippets"}
_registered: dict[str, list] = {}       # language -> argv (what we added)


def detect_server(ext) -> list[str] | None:
    """argv of the extension's language server, or None."""
    root = Path(ext.path) if getattr(ext, "path", None) else None
    if root is None or not root.is_dir():
        return None
    from .bridge import find_node
    node = find_node()
    for rel in CANDIDATES:
        p = root / rel
        if p.is_file() and node:
            return [node, str(p), "--stdio"]
    # server binaries shipped in the vsix (rust-analyzer, taplo ...): bin/ or server/ folders
    exe = ".exe" if sys.platform == "win32" else ""
    for folder in ("server", "bin", "dist", "out"):
        d = root / folder
        if not d.is_dir():
            continue
        for p in sorted(d.rglob(f"*{exe}" if exe else "*")):
            if p.is_file() and NAME_RX.search(p.stem) and (exe or p.stat().st_mode & 0o111):
                return [str(p)]
    if node:
        hits = []
        for p in root.rglob("*.js"):
            if any(part in SKIP_DIRS for part in p.relative_to(root).parts[:-1]):
                continue
            if NAME_RX.search(p.stem) and p.stat().st_size > 2000:
                hits.append(p)
        if hits:
            hits.sort(key=lambda p: (len(p.relative_to(root).parts), -p.stat().st_size))
            return [node, str(hits[0]), "--stdio"]
    return None


def languages_of(ext) -> list[str]:
    out = []
    for lang in ext.contributes_list("languages"):
        if isinstance(lang, dict) and lang.get("id") and lang["id"] not in out:
            out.append(lang["id"])
    if not out:      # activationEvents onLanguage:x of extensions that reuse a built-in language
        for ev in getattr(ext, "activation_events", []) or []:
            if isinstance(ev, str) and ev.startswith("onLanguage:"):
                lang = ev.split(":", 1)[1]
                if lang not in out:
                    out.append(lang)
    return out


def register(ext, log=None) -> list[str]:
    """Add the extension's server to radide.lsp.SERVERS for its languages. Returns the languages added."""
    from .. import lsp
    argv = detect_server(ext)
    if not argv:
        if log:
            log(f"[vsx] {ext.id}: no language server found for the LSP fallback")
        return []
    added = []
    for lang in languages_of(ext):
        if lang in lsp.SERVERS and lang not in _registered:
            continue                 # a built-in server exists
        lsp.SERVERS[lang] = ([argv], f"from the VS Code extension {ext.id}")
        _registered[lang] = argv
        added.append(lang)
    if added and log:
        log(f"[vsx] {ext.id}: language server {Path(argv[1] if len(argv) > 1 else argv[0]).name} "
            f"runs through the IDE's LSP client for {', '.join(added)}")
    return added


def unregister_all() -> None:
    from .. import lsp
    for lang in list(_registered):
        lsp.SERVERS.pop(lang, None)
    _registered.clear()


__all__ = ["detect_server", "register", "unregister_all", "languages_of"]
