"""Extension language features in the IDE's language-server shape.

The extension host answers LSP-shaped requests (method "lsp") from the extensions' vscode.languages
providers - also the providers vscode-languageclient registers for an extension's own language server.
``VsxLanguageClient`` is an ``radide.lsp.LspClient`` whose transport is the host, so the IDE's existing
converters (completion items, hover, signature help, definition, formatting, code actions, rename ...) apply.

``CompositeClient`` sits in ``editor.lsp`` when an editor has both a ready-made language server and
extension providers (or only the latter): completions / hovers / code actions are merged, the rest goes to
whichever side can answer. Without a real server it falls back to the language plugin's own IntelliSense, so
installing an extension never makes an editor poorer. The editor's Monaco built-in services stay on (the
composite is put in place without radSetLspActive) unless a real server was attached by lsp_support.
"""
from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ..lsp import LspClient

# provider kind -> LSP server capability
KIND_CAP = {
    "completion": "completionProvider", "hover": "hoverProvider", "definition": "definitionProvider",
    "declaration": "declarationProvider", "typeDefinition": "typeDefinitionProvider",
    "implementation": "implementationProvider", "references": "referencesProvider",
    "signatureHelp": "signatureHelpProvider", "formatting": "documentFormattingProvider",
    "rangeFormatting": "documentRangeFormattingProvider", "codeAction": "codeActionProvider",
    "rename": "renameProvider", "documentSymbol": "documentSymbolProvider", "inlayHint": "inlayHintProvider",
    "documentHighlight": "documentHighlightProvider", "codeLens": "codeLensProvider",
    "foldingRange": "foldingRangeProvider", "documentLink": "documentLinkProvider",
}
# LSP request -> capability
METHOD_CAP = {
    "textDocument/completion": "completionProvider", "textDocument/hover": "hoverProvider",
    "textDocument/definition": "definitionProvider", "textDocument/declaration": "declarationProvider",
    "textDocument/typeDefinition": "typeDefinitionProvider", "textDocument/implementation": "implementationProvider",
    "textDocument/references": "referencesProvider", "textDocument/signatureHelp": "signatureHelpProvider",
    "textDocument/formatting": "documentFormattingProvider",
    "textDocument/rangeFormatting": "documentRangeFormattingProvider",
    "textDocument/codeAction": "codeActionProvider", "textDocument/rename": "renameProvider",
    "textDocument/prepareRename": "renameProvider", "textDocument/documentSymbol": "documentSymbolProvider",
    "textDocument/inlayHint": "inlayHintProvider", "textDocument/documentHighlight": "documentHighlightProvider",
    "textDocument/codeLens": "codeLensProvider", "textDocument/foldingRange": "foldingRangeProvider",
    "textDocument/documentLink": "documentLinkProvider",
}
MERGED = {"textDocument/codeAction", "textDocument/references", "textDocument/inlayHint", "textDocument/codeLens"}


# Monaco language id -> VS Code language id (extensions select documents by the VS Code id)
MONACO_TO_VSCODE_ID = {"shell": "shellscript", "coffee": "coffeescript", "pug": "jade"}
EXT_TO_VSCODE_ID = {".jsx": "javascriptreact", ".tsx": "typescriptreact", ".jsonc": "jsonc", ".json5": "json5",
                    ".code-workspace": "jsonc", ".txt": "plaintext", ".text": "plaintext", ".log": "log"}


def vscode_lang(monaco_lang: str, path=None) -> str:
    """The VS Code language id of a document Monaco shows as *monaco_lang*."""
    suffix = Path(str(path)).suffix.lower() if path else ""
    if suffix in EXT_TO_VSCODE_ID and monaco_lang in ("javascript", "typescript", "json", "plaintext", "custom") \
            or (suffix in (".txt", ".text", ".log") and monaco_lang.startswith("rad-")):
        return EXT_TO_VSCODE_ID[suffix]
    if monaco_lang.startswith("rad-"):          # the IDE's own language plugins (Ring, Fortran ...)
        return monaco_lang[4:]
    return MONACO_TO_VSCODE_ID.get(monaco_lang, monaco_lang)


def editor_lang(editor) -> str:
    try:
        return vscode_lang(editor.language_id(), editor.path)
    except Exception:  # noqa: BLE001
        return "plaintext"


def _glob_match(pattern, path: str) -> bool:
    if isinstance(pattern, dict):
        base = str(pattern.get("base") or "")
        pat = str(pattern.get("pattern") or "")
        p = path.replace("\\", "/")
        b = base.replace("\\", "/").rstrip("/")
        if b and not p.lower().startswith(b.lower() + "/"):
            return False
        return _glob_match(pat, p[len(b) + 1:] if b else p)
    pat = str(pattern).replace("\\", "/")
    p = path.replace("\\", "/")
    rx = re.escape(pat).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*").replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
    rx = re.sub(r"\\\{([^}]*)\\\}", lambda m: "(?:" + "|".join(m.group(1).split(",")) + ")", rx)
    if re.fullmatch(rx, p, re.I):
        return True
    if not pat.startswith("/") and not re.match(r"^[A-Za-z]:", pat):
        return bool(re.fullmatch("(?:.*/)?" + rx, p, re.I)) or fnmatch.fnmatch(Path(p).name.lower(), pat.lower())
    return False


def selector_matches(selector: list, language: str, path: str, scheme: str = "file") -> bool:
    for s in selector or []:
        lang = s.get("language")
        sch = s.get("scheme")
        pat = s.get("pattern")
        if lang and lang not in ("*", language):
            continue
        if sch and sch not in ("*", scheme):
            continue
        if pat and not _glob_match(pat, path):
            continue
        if lang or sch or pat:
            return True
    return False


class ProviderIndex:
    """The host's provider registrations ("providers/changed"): which kinds serve which documents."""

    def __init__(self):
        self.providers: list[dict] = []

    def update(self, providers: list) -> None:
        self.providers = list(providers or [])

    def for_doc(self, language: str, path: str) -> list[dict]:
        return [p for p in self.providers if selector_matches(p.get("selector"), language, str(path))]

    def kinds(self, language: str, path: str) -> set:
        return {p["kind"] for p in self.for_doc(language, path)}

    def triggers(self, language: str, path: str, kind: str = "completion") -> list[str]:
        out = []
        for p in self.for_doc(language, path):
            if p["kind"] == kind:
                out += [t for t in p.get("triggers") or [] if t not in out]
        return out

    def capabilities(self, language: str, path: str) -> dict:
        caps: dict = {}
        for k in self.kinds(language, path):
            cap = KIND_CAP.get(k)
            if cap:
                caps[cap] = True
        if "completion" in self.kinds(language, path):
            caps["completionProvider"] = {"triggerCharacters": self.triggers(language, path)}
        if "signatureHelp" in self.kinds(language, path):
            caps["signatureHelpProvider"] = {"triggerCharacters": self.triggers(language, path, "signatureHelp")}
        return caps


class VsxLanguageClient(LspClient):
    """An LspClient whose 'server' is the extension host (one per editor; documents are synced by the
    service, so the didOpen/didChange notifications of LspClient are not sent)."""

    def __init__(self, service, language: str, path: Path, root: Path):
        super().__init__(language, root, ["extension host"], service)
        self.service = service
        self.path = Path(path)
        self._initialized = True

    @property
    def capabilities(self):
        return self.service.index.capabilities(self.language, str(self.path))

    @capabilities.setter
    def capabilities(self, _v):
        pass

    def start(self) -> bool:
        return True

    def running(self) -> bool:
        return self.service.host.running()

    def stop(self):
        pass

    def _send(self, msg: dict):
        pass

    def _request(self, method, params, cb=None, force=False):
        host = self.service.host
        if not host.running():
            if cb is not None:
                cb(None)
            return
        self.service.before_request()
        host.request("lsp", {"method": method, "params": params}, cb or (lambda _r: None), timeout_ms=8000)

    def _notify(self, method, params):
        pass

    def did_open(self, path, text, language_id):
        self.service.sync_text(path, text)

    def did_change(self, path, text):
        self.service.sync_text(path, text)

    def did_save(self, path):
        pass

    def did_close(self, path):
        pass


class CompositeClient(QObject):
    """editor.lsp when extension providers serve the editor: real server (optional) + extension host."""
    ready = pyqtSignal()
    diagnostics = pyqtSignal(str, list)
    log = pyqtSignal(str)
    notification = pyqtSignal(str, object)
    VSX_TIMEOUT = 4000

    def __init__(self, service, editor, real=None):
        super().__init__(editor)
        self.service = service
        self.editor = editor
        self.real = real
        self.vsx = VsxLanguageClient(service, editor_lang(editor), editor.path, service.root_for(editor))
        self._initialized = True
        self.last_error = ""
        self.language = getattr(real, "language", None) or editor.language_id()
        self.root = getattr(real, "root", None) or service.root_for(editor)
        self.argv = getattr(real, "argv", None) or ["extension host"]

    def __getattr__(self, name):            # anything else (raw_diagnostics, server_status ...) from the server
        real = self.__dict__.get("real") if "real" in self.__dict__ else None
        if real is not None:
            return getattr(real, name)
        raise AttributeError(name)

    # ------------------------------------------------------------ state
    def _kinds(self) -> set:
        return self.service.index.kinds(editor_lang(self.editor), str(self.editor.path))

    @property
    def capabilities(self) -> dict:
        caps = dict(getattr(self.real, "capabilities", None) or {}) if self.real is not None else {}
        for k, v in self.vsx.capabilities.items():
            if k == "completionProvider" and isinstance(caps.get(k), dict):
                trig = list((caps[k] or {}).get("triggerCharacters") or [])
                trig += [t for t in v.get("triggerCharacters", []) if t not in trig]
                caps[k] = dict(caps[k], triggerCharacters=trig)
            elif k not in caps:
                caps[k] = v
        if self.real is None:          # the plugin's own hover / signatures stay available
            caps.setdefault("hoverProvider", True)
            caps.setdefault("signatureHelpProvider", {"triggerCharacters": ["(", ","]})
        return caps

    @capabilities.setter
    def capabilities(self, _v):
        pass

    def running(self) -> bool:
        return True

    def stop(self):
        if self.real is not None:
            self.real.stop()

    # ------------------------------------------------------------ documents
    def did_open(self, path, text, language_id):
        if self.real is not None:
            self.real.did_open(path, text, language_id)
        self.service.sync_text(path, text)

    def did_change(self, path, text):
        if self.real is not None:
            self.real.did_change(path, text)
        self.service.sync_text(path, text)

    def did_save(self, path):
        if self.real is not None:
            self.real.did_save(path)

    def did_close(self, path):
        if self.real is not None:
            self.real.did_close(path)

    # ------------------------------------------------------------ helpers
    def _both(self, real_call, vsx_call, merge, cb, use_vsx=True, use_real=True):
        """Ask both sides; cb(merge(real_result, vsx_result)) when both answered (vsx has a time limit)."""
        box = {"n": 0, "done": False}
        want_real = use_real and self.real is not None and self.real.running()
        want_vsx = use_vsx and self.service.host.running()
        need = int(want_real) + int(want_vsx)
        if need == 0:
            cb(merge(None, None))
            return

        def finish():
            if not box["done"]:
                box["done"] = True
                try:
                    cb(merge(box.get("real"), box.get("vsx")))
                except Exception as e:  # noqa: BLE001 - IntelliSense must never break typing
                    print(f"[vsx] merge failed: {e}")

        def got(side, res):
            if box["done"]:
                return
            box[side] = res
            box["n"] += 1
            if box["n"] >= need:
                finish()
        if want_vsx:
            QTimer.singleShot(self.VSX_TIMEOUT, finish)
            vsx_call(lambda r: got("vsx", r))
        if want_real:
            real_call(lambda r: got("real", r))

    def _plugin_owns(self) -> bool:
        """The editor's language plugin is the file's own language (not just the fallback plugin of a
        loose file): its IntelliSense is worth merging."""
        ed = self.editor
        try:
            return str(getattr(ed.plugin, "code_ext", "")).lower() == Path(ed.path).suffix.lower()
        except Exception:  # noqa: BLE001
            return False

    def _plugin_items(self, line, col):
        ed = self.editor
        try:
            from ..monaco_editor import KIND
            return [{"label": c.name, "kind": KIND.get(c.kind, 18), "detail": c.detail or c.kind}
                    for c in ed.plugin.completions(ed.text(), line, col, ed.path, ed.names)[:400]]
        except Exception:  # noqa: BLE001
            return []

    # ------------------------------------------------------------ features
    def completion(self, path, text, line, col, cb):
        self.service.sync_text(path, text)
        kinds = self._kinds()

        def merge(real, vsx):
            out = list(vsx or [])
            seen = {i.get("label") for i in out}
            if self.real is not None:
                base = real
            else:
                base = self._plugin_items(line, col) if (not out or self._plugin_owns()) else []
            out += [i for i in (base or []) if i.get("label") not in seen]
            return out
        self._both(lambda c: self.real.completion(path, text, line, col, c),
                   lambda c: self.vsx.completion(path, text, line, col, c), merge, cb,
                   use_vsx="completion" in kinds)

    def hover(self, path, line, col, cb):
        kinds = self._kinds()

        def merge(real, vsx):
            if self.real is None and not real and (not vsx or self._plugin_owns()):
                try:
                    ed = self.editor
                    real = ed.plugin.hover(ed.text(), line, col, ed.path, ed.names) or ""
                except Exception:  # noqa: BLE001
                    real = ""
            parts = [p for p in (vsx, real) if p]
            return "\n\n---\n\n".join(parts)
        real_ok = self.real is not None and (getattr(self.real, "capabilities", None) or {}).get("hoverProvider")
        self._both(lambda c: self.real.hover(path, line, col, c), lambda c: self.vsx.hover(path, line, col, c),
                   merge, cb, use_vsx="hover" in kinds, use_real=bool(real_ok))

    def signature_info(self, path, line, col, cb):
        kinds = self._kinds()
        real = self.real
        if real is not None and (getattr(real, "capabilities", None) or {}).get("signatureHelpProvider"):
            real.signature_info(path, line, col, cb)
        elif "signatureHelp" in kinds:
            self.vsx.signature_info(path, line, col, cb)
        else:
            try:
                ed = self.editor
                tip = re.sub(r"<[^>]+>", "", ed.plugin.calltip(ed.text(), line, col, ed.path, ed.names) or "")
            except Exception:  # noqa: BLE001
                tip = ""
            cb({"label": tip, "documentation": "", "parameters": [], "activeParameter": 0} if tip else None)

    def signature_help(self, path, line, col, cb):
        if "signatureHelp" in self._kinds():
            self.vsx.signature_help(path, line, col, cb)
        elif self.real is not None:
            self.real.signature_help(path, line, col, cb)
        else:
            cb("")

    def definition(self, path, line, col, cb):
        if "definition" in self._kinds():
            def done(res):
                if res or self.real is None:
                    cb(res)
                else:
                    self.real.definition(path, line, col, cb)
            self.vsx.definition(path, line, col, done)
        elif self.real is not None:
            self.real.definition(path, line, col, cb)
        else:
            cb(None)

    def inlay_hints(self, path, l1, l2, cb, end_col: int = 0):
        kinds = self._kinds()                 # (end_col: monaco_editor passes the last line's length)
        self._both(lambda c: self.real.inlay_hints(path, l1, l2, c, end_col), lambda c: self.vsx.inlay_hints(path, l1, l2, c),
                   lambda a, b: (a or []) + (b or []), cb, use_vsx="inlayHint" in kinds)

    def _request(self, method, params, cb=None, force=False):
        cb = cb or (lambda _r: None)
        cap = METHOD_CAP.get(method)
        vsx_has = bool(cap and self.vsx.capabilities.get(cap)) or method == "workspace/executeCommand" and \
            self._is_vsx_command(params)
        real = self.real
        real_has = real is not None and (not cap or (getattr(real, "capabilities", None) or {}).get(cap))
        if method in MERGED and vsx_has and real_has:
            self._both(lambda c: real._request(method, params, c, force), lambda c: self.vsx._request(method, params, c),
                       lambda a, b: (b or []) + (a or []), cb)
            return
        if vsx_has:
            def done(res):
                self.last_error = self.vsx.last_error
                cb(res)
            self.vsx._request(method, params, done)
        elif real is not None:
            def done2(res):
                self.last_error = getattr(real, "last_error", "")
                cb(res)
            real._request(method, params, done2, force)
        else:
            cb(None)

    def _is_vsx_command(self, params) -> bool:
        args = (params or {}).get("arguments") or []
        cmd = (params or {}).get("command", "")
        return bool(args and isinstance(args[0], dict) and "$vsxArgs" in args[0]) or cmd in self.service.host_commands

    def _notify(self, method, params):
        if self.real is not None:
            self.real._notify(method, params)


__all__ = ["CompositeClient", "VsxLanguageClient", "ProviderIndex", "selector_matches", "KIND_CAP", "vscode_lang",
           "editor_lang"]
