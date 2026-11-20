"""VS Code languages, TextMate grammars and snippets (``contributes.languages / grammars / snippets``).

* languages -> Monaco languages (id, extensions, aliases, language-configuration.json: comments, brackets,
  autoClosingPairs, surroundingPairs, folding, indentationRules, wordPattern, onEnterRules) and the IDE's
  file-extension / file-name mapping (radide.monaco_editor.MONACO_LANG / MONACO_FILENAMES), so a file opens
  with the right language.
* grammars -> served by scope name to radide/web/vsx/vsx-contrib.js, which tokenises with vscode-textmate +
  vscode-oniguruma (embeddedLanguages and injections included) instead of the Monarch tokenizer.
* snippets -> Monaco completion items (VS Code snippet syntax is Monaco's snippet syntax).

``Registry`` is rebuilt by ``refresh()``; ``registry()`` returns the current one. No Qt import."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .contrib_common import enabled_extensions, ext_file, read_jsonc

# VS Code language ids -> the ids Monaco / the IDE use for the same language
VSCODE_TO_MONACO = {"shellscript": "shell", "javascriptreact": "javascript", "typescriptreact": "typescript",
                    "jsonc": "json", "json5": "json", "bat": "bat", "makefile": "makefile", "plaintext": "plaintext",
                    "csharp": "csharp", "cpp": "cpp", "c": "c", "vb": "vb", "jade": "pug",
                    "objective-c": "objective-c", "coffeescript": "coffee", "fsharp": "fsharp"}
MONACO_TO_VSCODE: dict[str, list[str]] = {}
for _k, _v in VSCODE_TO_MONACO.items():
    MONACO_TO_VSCODE.setdefault(_v, []).append(_k)


def monaco_id(lang: str) -> str:
    return VSCODE_TO_MONACO.get(lang, lang)


@dataclass
class Language:
    id: str
    extensions: list = field(default_factory=list)
    filenames: list = field(default_factory=list)
    filename_patterns: list = field(default_factory=list)
    aliases: list = field(default_factory=list)
    mimetypes: list = field(default_factory=list)
    first_line: str = ""
    configuration: dict | None = None
    ext_ids: list = field(default_factory=list)

    @property
    def title(self) -> str:
        return str(self.aliases[0]) if self.aliases else self.id


@dataclass
class Grammar:
    scope: str
    path: Path
    ext_id: str
    language: str = ""
    embedded: dict = field(default_factory=dict)       # scope -> language id
    token_types: dict = field(default_factory=dict)
    inject_to: list = field(default_factory=list)
    balanced: list = field(default_factory=list)
    unbalanced: list = field(default_factory=list)


class Registry:
    def __init__(self, extensions=None):
        self.languages: dict[str, Language] = {}
        self.grammars: dict[str, Grammar] = {}          # scope name -> grammar
        self.language_scope: dict[str, str] = {}        # language id -> root scope name
        self.injections: dict[str, list[str]] = {}      # target scope -> injected scopes
        self.snippet_files: dict[str, list] = {}        # language id -> [(path, ext_id)]
        self._snippet_cache: dict[str, list] = {}
        exts = enabled_extensions() if extensions is None else list(extensions)
        for ext in exts:
            try:
                self._add(ext)
            except Exception:  # noqa: BLE001 - one broken manifest must not hide the others
                continue

    # ------------------------------------------------------------------ building
    def _add(self, ext) -> None:
        for c in ext.contributes_list("languages"):
            if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not c["id"]:
                continue
            lang = self.languages.get(c["id"])
            if lang is None:
                lang = self.languages[c["id"]] = Language(id=c["id"])
            for attr, key in (("extensions", "extensions"), ("filenames", "filenames"),
                              ("filename_patterns", "filenamePatterns"), ("aliases", "aliases"),
                              ("mimetypes", "mimetypes")):
                for v in c.get(key) or []:
                    if isinstance(v, str) and v not in getattr(lang, attr):
                        getattr(lang, attr).append(v)
            if isinstance(c.get("firstLine"), str) and not lang.first_line:
                lang.first_line = c["firstLine"]
            if isinstance(c.get("configuration"), str) and lang.configuration is None:
                p = ext_file(ext, c["configuration"])
                cfg = read_jsonc(p, None) if p else None
                if isinstance(cfg, dict):
                    lang.configuration = cfg
            if ext.id not in lang.ext_ids:
                lang.ext_ids.append(ext.id)
        for c in ext.contributes_list("grammars"):
            if not isinstance(c, dict) or not isinstance(c.get("scopeName"), str) or not isinstance(c.get("path"), str):
                continue
            p = ext_file(ext, c["path"])
            if p is None:
                continue
            g = Grammar(scope=c["scopeName"], path=p, ext_id=ext.id, language=str(c.get("language") or ""),
                        embedded=dict(c.get("embeddedLanguages") or {}), token_types=dict(c.get("tokenTypes") or {}),
                        inject_to=[s for s in c.get("injectTo") or [] if isinstance(s, str)],
                        balanced=list(c.get("balancedBracketScopes") or []),
                        unbalanced=list(c.get("unbalancedBracketScopes") or []))
            self.grammars[g.scope] = g
            if g.language:
                self.language_scope[g.language] = g.scope
                self.languages.setdefault(g.language, Language(id=g.language, ext_ids=[ext.id]))
            for target in g.inject_to:
                lst = self.injections.setdefault(target, [])
                if g.scope not in lst:
                    lst.append(g.scope)
        for c in ext.contributes_list("snippets"):
            if not isinstance(c, dict) or not isinstance(c.get("path"), str):
                continue
            p = ext_file(ext, c["path"])
            if p is None:
                continue
            lang = str(c.get("language") or "*")
            self.snippet_files.setdefault(lang, []).append((p, ext.id))

    # ------------------------------------------------------------------ queries
    def grammar_payload(self, scope: str) -> dict | None:
        g = self.grammars.get(scope)
        if g is None:
            return None
        try:
            text = g.path.read_text("utf-8", "replace")
        except OSError:
            return None
        if text.startswith("﻿"):
            text = text[1:]
        if g.path.suffix.lower() == ".json":
            try:
                json.loads(text)
            except ValueError:                   # JSON with comments / trailing commas
                data = read_jsonc(g.path, None)
                if data is None:
                    return None
                text = json.dumps(data)
        elif g.path.suffix.lower() in (".yaml", ".yml"):
            return None                          # YAML grammars are converted at build time in VS Code
        # vscode-textmate's parseRawGrammar reads "*.json" as JSON and anything else as a plist
        return {"scope": scope, "path": g.path.name, "content": text}

    def languages_with_grammar(self) -> list[str]:
        """IDE (Monaco) language ids that get a TextMate tokenizer."""
        out = []
        for lang in self.language_scope:
            out.append(lang)
            m = monaco_id(lang)
            if m != lang:
                out.append(m)
        return out

    def snippets(self, lang: str) -> list[dict]:
        """Snippets for a Monaco language id: [{prefix, body, description, name, ext}]."""
        if lang in self._snippet_cache:
            return self._snippet_cache[lang]
        files = list(self.snippet_files.get(lang, [])) + list(self.snippet_files.get("*", []))
        for vs in MONACO_TO_VSCODE.get(lang, []):
            if vs != lang:
                files += self.snippet_files.get(vs, [])
        out, seen = [], set()
        for p, ext_id in files:
            if (p, lang) in seen:
                continue
            seen.add((p, lang))
            data = read_jsonc(p, {})
            if not isinstance(data, dict):
                continue
            out += _snippet_items(data, ext_id, lang)
        self._snippet_cache[lang] = out
        return out

    def snippet_languages(self) -> list[str]:
        out = set()
        for lang in self.snippet_files:
            if lang == "*":
                continue
            out.add(lang)
            out.add(monaco_id(lang))
        return sorted(out)

    def js_spec(self) -> dict:
        """What vsx-contrib.js registers in every Monaco page (grammars and snippets are fetched lazily)."""
        langs = []
        for lang in self.languages.values():
            scope = self.language_scope.get(lang.id)
            g = self.grammars.get(scope) if scope else None
            langs.append({"id": lang.id, "monaco": monaco_id(lang.id), "extensions": lang.extensions,
                          "filenames": lang.filenames, "aliases": lang.aliases, "mimetypes": lang.mimetypes,
                          "firstLine": lang.first_line, "configuration": lang.configuration,
                          "scope": scope or "", "embedded": dict(g.embedded) if g else {},
                          "tokenTypes": dict(g.token_types) if g else {},
                          "balanced": g.balanced if g else [], "unbalanced": g.unbalanced if g else []})
        return {"languages": langs, "injections": self.injections,
                "grammarScopes": sorted(self.grammars), "snippetLanguages": self.snippet_languages()}

    def language_for_file(self, name: str) -> str | None:
        """Language id by exact file name or extension (VS Code rules: file names first, longest extension)."""
        low = name.lower()
        for lang in self.languages.values():
            if any(f.lower() == low for f in lang.filenames):
                return lang.id
        best, best_len = None, 0
        for lang in self.languages.values():
            for e in lang.extensions:
                el = e.lower()
                if low.endswith(el) and len(el) > best_len:
                    best, best_len = lang.id, len(el)
        return best


def _snippet_items(data: dict, ext_id: str, lang: str) -> list[dict]:
    out = []
    for name, s in data.items():
        if not isinstance(s, dict):
            continue
        scope = s.get("scope")
        if isinstance(scope, str) and scope.strip():
            allowed = {x.strip() for x in scope.split(",")}
            if lang not in allowed and not (allowed & set(MONACO_TO_VSCODE.get(lang, []))):
                continue
        prefixes = s.get("prefix")
        prefixes = [prefixes] if isinstance(prefixes, str) else [p for p in prefixes or [] if isinstance(p, str)]
        body = s.get("body")
        if isinstance(body, list):
            body = "\n".join(str(b) for b in body)
        if not isinstance(body, str) or not prefixes:
            continue
        desc = s.get("description")
        if isinstance(desc, list):
            desc = "\n".join(str(d) for d in desc)
        for pre in prefixes:
            out.append({"prefix": pre, "body": body, "description": str(desc or name), "name": str(name),
                        "ext": ext_id})
    return out


# ============================================================================ current registry
_registry: Registry | None = None
_mapped: dict[str, str | None] = {}                # extension -> previous MONACO_LANG value (None = absent)
_mapped_names: set[str] = set()
_menu_added: list = []


def registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = Registry()
    return _registry


def refresh(extensions=None) -> Registry:
    global _registry
    _registry = Registry(extensions)
    apply_file_mappings(_registry)
    return _registry


def apply_file_mappings(reg: Registry | None = None) -> None:
    """Teach the IDE which language a file has: contributed extensions / file names. An extension the IDE
    already knows keeps its language unless the contributing extension brings a grammar for its own one
    (".toml": ini -> toml); everything is restored when the extension goes away."""
    reg = reg or registry()
    try:
        from .. import monaco_editor as me
    except Exception:  # noqa: BLE001 - no QtWebEngine: nothing to map
        return
    for e, prev in list(_mapped.items()):          # undo the previous mapping
        if prev is None:
            me.MONACO_LANG.pop(e, None)
        else:
            me.MONACO_LANG[e] = prev
    _mapped.clear()
    for n in list(_mapped_names):
        me.MONACO_FILENAMES.pop(n, None)
    _mapped_names.clear()
    for item in list(_menu_added):
        try:
            me.LANGUAGE_CHOICES.remove(item)
        except ValueError:
            pass
    _menu_added.clear()
    with_grammar = set(reg.language_scope)
    for lang in reg.languages.values():
        target = monaco_id(lang.id)
        has_grammar = lang.id in with_grammar
        if not has_grammar and lang.configuration is None and lang.id not in reg.snippet_files:
            continue                                  # a bare id (e.g. only to attach a debugger)
        for e in lang.extensions:
            el = e.lower()
            if not el.startswith("."):
                continue
            cur = me.MONACO_LANG.get(el)
            if cur == target:
                continue
            if cur is None or has_grammar:
                if el not in _mapped:
                    _mapped[el] = cur
                me.MONACO_LANG[el] = target
        for f in lang.filenames:
            fl = f.lower()
            if fl not in me.MONACO_FILENAMES:
                me.MONACO_FILENAMES[fl] = target
                _mapped_names.add(fl)
        known = {lid for _t, lid in me.LANGUAGE_CHOICES}
        if has_grammar and target not in known:
            item = (lang.title, target)
            me.LANGUAGE_CHOICES.append(item)
            _menu_added.append(item)


def grammar_json(scope: str) -> str:
    p = registry().grammar_payload(scope)
    return json.dumps(p) if p else ""


def snippets_json(lang: str) -> str:
    return json.dumps(registry().snippets(lang))


__all__ = ["Registry", "Language", "Grammar", "registry", "refresh", "apply_file_mappings", "grammar_json",
           "snippets_json", "monaco_id", "VSCODE_TO_MONACO"]
