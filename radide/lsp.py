"""Language Server Protocol client (one generic client for every language).

Ready-made language servers give completion, hover, signature help, go to
definition and live diagnostics. SERVERS lists the command lines tried for
each Monaco language id; the first one whose executable exists is used.

Web servers (HTML/CSS/JSON from vscode-langservers-extracted, PHP from
intelephense, JS/TS from typescript-language-server) are looked up first in the
IDE's private npm folder ``%LOCALAPPDATA%\\RADIDE\\lsp`` (``install_web_servers()``
runs ``npm install --prefix`` there), then on PATH.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

VENV_PY = sys.executable

LSP_HOME = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE" / "lsp"
WEB_PACKAGES = ["vscode-langservers-extracted", "intelephense", "typescript@5", "typescript-language-server"]

_HTML = [["npm:vscode-langservers-extracted/vscode-html-language-server", "--stdio"],
         ["vscode-html-language-server", "--stdio"]]
_CSS = [["npm:vscode-langservers-extracted/vscode-css-language-server", "--stdio"],
        ["vscode-css-language-server", "--stdio"]]
_JSON = [["npm:vscode-langservers-extracted/vscode-json-language-server", "--stdio"],
         ["vscode-json-language-server", "--stdio"]]
_TS = [["npm:typescript-language-server/typescript-language-server", "--stdio"],
       ["typescript-language-server", "--stdio"]]
_WEB_HINT = "Tools > Install Web Language Servers (npm install --prefix %LOCALAPPDATA%\\RADIDE\\lsp)"

# language id -> list of candidate argv (first available wins) + install hint.
# "npm:<package>/<bin>" = a bin of a package installed under LSP_HOME (run with node).
SERVERS: dict[str, tuple[list[list[str]], str]] = {
    "python": ([[VENV_PY, "-m", "pylsp"], ["pyright-langserver", "--stdio"]], "pip install python-lsp-server"),
    "javascript": (_TS, _WEB_HINT),
    "typescript": (_TS, _WEB_HINT),
    "html": (_HTML, _WEB_HINT),
    "css": (_CSS, _WEB_HINT),
    "scss": (_CSS, _WEB_HINT),
    "less": (_CSS, _WEB_HINT),
    "json": (_JSON, _WEB_HINT),
    "csharp": ([["csharp-ls"]], "dotnet tool install -g csharp-ls"),
    "java": ([["jdtls"]], "install Eclipse JDT Language Server (jdtls)"),
    # rust: the real binary of the rustup component (radide/rust_tools.py), not the ~/.cargo/bin proxy
    "rust": ([["rust-analyzer"]], "rustup component add rust-analyzer rust-src"),
    "c": ([["clangd"]], "install clangd (LLVM)"),
    "cpp": ([["clangd"]], "install clangd (LLVM)"),
    # go / lua / ruby / powershell / perl: radide/lsp_servers.py (IDE tools folder) is asked first
    "go": ([["gopls"]], "Tools > Language Servers... (go install golang.org/x/tools/gopls@latest)"),
    "php": ([["npm:intelephense/intelephense", "--stdio"], ["intelephense", "--stdio"]], _WEB_HINT),
    "dart": ([["dart", "language-server", "--protocol=lsp"]], "comes with the Dart SDK"),
    "lua": ([["lua-language-server"]], "Tools > Language Servers... (lua-language-server release zip)"),
    "ruby": ([["ruby-lsp"], ["solargraph", "stdio"]], "Tools > Language Servers... (gem install ruby-lsp)"),
    "rad-fortran-bridge": ([["fortls"]], "pip install fortls"),
    "powershell": ([], "Tools > Language Servers... (PowerShell Editor Services release zip)"),
    "perl": ([["pls"]], "PLS (Linux / macOS); on Windows the Perl plugin's own IntelliSense is used"),
    # Django / Jinja templates (radide/features/python_web.py): HTML IntelliSense from the HTML server
    "django-html": (_HTML, _WEB_HINT),
    "jinja-html": (_HTML, _WEB_HINT),
    # assembly editors (radide/asm_intel): asm-lsp when installed (radide/lsp_servers.py asks asm_intel.lsp first)
    **{f"rad-asm-{d}": ([], "Tools > Language Servers... (asm-lsp, optional)")
       for d in ("nasm", "masm", "fasm", "gas")},
}

# languages that share one server process (per project root)
SERVER_GROUP = {"scss": "css", "less": "css", "typescript": "javascript", "django-html": "html",
                "jinja-html": "html", **{f"rad-asm-{d}": "rad-asm" for d in ("nasm", "masm", "fasm", "gas")}}

# Monaco language id -> LSP languageId sent in didOpen
LSP_LANGUAGE_ID = {"rad-fortran-bridge": "fortran", "django-html": "html", "jinja-html": "html",
                   **{f"rad-asm-{d}": "asm" for d in ("nasm", "masm", "fasm", "gas")}}


def server_key(language: str) -> str:
    return SERVER_GROUP.get(language, language)


def _npm_bin(spec: str) -> list[str] | None:
    """'npm:<package>/<bin>' -> [node, <script>] for a package installed under LSP_HOME."""
    pkg, _, binname = spec[4:].rpartition("/")
    pdir = LSP_HOME / "node_modules" / pkg
    try:
        meta = json.loads((pdir / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    b = meta.get("bin")
    script = b if isinstance(b, str) else (b or {}).get(binname)
    node = shutil.which("node")
    if not script or not node or not (pdir / script).exists():
        return None
    return [node, str((pdir / script).resolve())]


def server_command(language: str) -> list[str] | None:
    from . import lsp_servers           # gopls / ruby-lsp / lua-language-server / PSES / PLS in the tools folder
    argv = lsp_servers.server_command(language)
    if argv:
        return argv
    if language == "rust":
        from .rust_tools import rust_analyzer
        ra = rust_analyzer()
        return [ra] if ra else None
    cands, _hint = SERVERS.get(language, ([], ""))
    for argv in cands:
        exe = argv[0]
        if exe == VENV_PY:
            if getattr(sys, "frozen", False):      # release build: pylsp of the real Python (radide/paths.py)
                from .paths import python_has_module
                if python_has_module(VENV_PY, argv[2]):
                    return argv
                continue
            try:
                __import__(argv[2].replace("-", "_"))
                return argv
            except ImportError:
                continue
        if exe.startswith("npm:"):
            base = _npm_bin(exe)
            if base:
                return [*base, *argv[1:]]
            continue
        if shutil.which(exe):
            return [shutil.which(exe), *argv[1:]]
    return None


def display_name(argv: list[str]) -> str:
    """A readable server name: 'intelephense', 'vscode-html-language-server', 'pylsp', ..."""
    if not argv:
        return ""
    if any(str(a).endswith("Start-EditorServices.ps1") for a in argv):    # lsp_servers.py (via its relay)
        return "PowerShell Editor Services"
    first = Path(argv[0])
    if first.stem.lower() in ("ruby", "perl") and len(argv) > 1:          # ruby-lsp / solargraph script
        return Path(argv[1]).name
    if first.stem.lower() == "node" and len(argv) > 1:
        script = Path(argv[1])
        parts = script.parts
        if "node_modules" in parts:
            i = len(parts) - 1 - parts[::-1].index("node_modules")
            pkg = parts[i + 1] if i + 1 < len(parts) else script.stem
            return script.name if script.parent.name == "bin" else pkg
        return script.stem
    if first.resolve() == Path(VENV_PY).resolve() and len(argv) > 2 and argv[1] == "-m":
        return argv[2]
    return first.stem


def install_hint(language: str) -> str:
    return SERVERS.get(language, ([], ""))[1]


def web_servers_installed() -> dict[str, bool]:
    return {lang: server_command(lang) is not None for lang in ("html", "css", "json", "php", "javascript")}


def install_web_servers(log=print) -> bool:
    """npm install the web language servers into LSP_HOME (blocking; run it in a thread)."""
    npm = shutil.which("npm")
    if not npm:
        log("npm was not found - install Node.js first.")
        return False
    LSP_HOME.mkdir(parents=True, exist_ok=True)
    cmd = [npm, "install", "--prefix", str(LSP_HOME), "--no-fund", "--no-audit", *WEB_PACKAGES]
    log("> " + " ".join(cmd))
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    log((p.stdout or "") + (p.stderr or ""))
    return p.returncode == 0


def initialization_options(language: str, root: Path) -> dict:
    """Server-specific initializationOptions."""
    key = server_key(language)
    if key == "html":
        return {"provideFormatter": True, "embeddedLanguages": {"css": True, "javascript": True},
                "configurationSection": ["html", "css", "javascript"]}
    if key in ("css", "json"):
        return {"provideFormatter": True}
    if key == "php":
        store = LSP_HOME / "intelephense-storage"
        store.mkdir(parents=True, exist_ok=True)
        return {"storagePath": str(store), "globalStoragePath": str(store), "clearCache": False}
    if key == "javascript":
        tsserver = LSP_HOME / "node_modules" / "typescript" / "lib" / "tsserver.js"
        opts: dict = {"preferences": {"includeCompletionsForModuleExports": True}}
        if tsserver.exists():
            opts["tsserver"] = {"path": str(tsserver)}
        return opts
    if key == "rust":
        from .rust_tools import ra_initialization_options
        return ra_initialization_options(root)
    from . import lsp_servers
    return lsp_servers.initialization_options(key)


def _php_version_for(root) -> str:
    """intelephense.environment.phpVersion = the version of the project's PHP (web.php, php_toolchain.py)."""
    try:
        from .web_site.php_toolchain import intelephense_version, php_for_folder
        return intelephense_version(php_for_folder(root)) or "8.1.0"
    except Exception:  # noqa: BLE001 - never break the language server for this
        return "8.1.0"


def workspace_settings(language: str, root=None) -> dict:
    """Answers for workspace/configuration requests (by section)."""
    php_version = _php_version_for(root) if server_key(language) == "php" else "8.1.0"
    from . import lsp_servers           # Lua / powershell / gopls sections
    extra: dict = {}
    if server_key(language) == "rust":
        from .rust_tools import ra_settings
        extra["rust-analyzer"] = ra_settings()
    return {
        **extra,
        **lsp_servers.workspace_settings(),
        "html": {"validate": {"scripts": True, "styles": True}, "suggest": {"html5": True},
                 "format": {"enable": True}, "hover": {"documentation": True, "references": True},
                 "autoClosingTags": True},
        "css": {"validate": True, "completion": {"triggerPropertyValueCompletion": True}},
        "scss": {"validate": True}, "less": {"validate": True},
        "javascript": {"validate": {"enable": True}}, "typescript": {"validate": {"enable": True}},
        "js/ts": {"implicitProjectConfig": {"strictNullChecks": False, "experimentalDecorators": False}},
        "json": {"validate": {"enable": True}, "format": {"enable": True}},
        "intelephense": {"files": {"maxSize": 5000000, "associations": ["*.php", "*.phtml"],
                                   "exclude": ["**/.git/**", "**/node_modules/**", "**/.radide_backup/**"]},
                         "diagnostics": {"enable": True}, "completion": {"insertUseDeclaration": True},
                         "format": {"enable": True}, "environment": {"phpVersion": php_version}},
    }


# LSP CompletionItemKind -> Monaco CompletionItemKind
LSP_TO_MONACO = {1: 18, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 7, 9: 8, 10: 9, 11: 12, 12: 13, 13: 15,
                 14: 17, 15: 27, 16: 19, 17: 20, 18: 21, 19: 23, 20: 16, 21: 14, 22: 6, 23: 10, 24: 11, 25: 24}


_STAR_USED = re.compile(r"^'from (\w+) import \*' used; unable to detect undefined names")
_STAR_MAYBE = re.compile(r"may be undefined, or defined from star imports: ([\w, .]+)$")


def _rad_star_import_noise(message: str) -> bool:
    """pyflakes warnings caused only by the star imports RAD IDE itself generates (game scenes:
    ``from radgame import *`` / ``from Level1_designer import *``, like VB's implicit form names):
    every helper call would be underlined. Star imports of other modules keep their warnings."""
    def ours(mod: str) -> bool:
        mod = mod.strip()
        return mod in ("radgame", "radcall") or mod.endswith("_designer")
    m = _STAR_USED.match(message)
    if m:
        return ours(m.group(1))
    m = _STAR_MAYBE.search(message)
    return bool(m) and all(ours(x) for x in m.group(1).split(","))


def path_uri(p: Path) -> str:
    return Path(p).resolve().as_uri()


class LspClient(QObject):
    diagnostics = pyqtSignal(str, list)        # file path, [{line, col, endLine, endCol, message, severity}]
    log = pyqtSignal(str)
    ready = pyqtSignal()                       # initialize answered (capabilities known)
    # other server notifications (method, params): experimental/serverStatus (rust-analyzer), $/progress ...
    notification = pyqtSignal(str, object)
    # server -> client request method -> handler(client, params) -> result (radide/features/refactor.py)
    request_handlers: dict = {}
    last_error = ""                            # message of the last error response

    def __init__(self, language: str, root: Path, argv: list[str], parent=None):
        super().__init__(parent)
        self.language = language
        self.root = Path(root)
        self.argv = argv
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(str(self.root))
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.readyReadStandardError.connect(
            lambda: self.log.emit(bytes(self.proc.readAllStandardError()).decode("utf-8", "replace")))
        self._buf = b""
        self._id = 0
        self._callbacks: dict[int, callable] = {}
        self._versions: dict[str, int] = {}
        self._lang_ids: dict[str, str] = {}
        self._last_text: dict[str, str] = {}
        self._initialized = False
        self._queue: list[dict] = []
        self.capabilities: dict = {}

    # ------------------------------------------------------------ process / framing
    def start(self) -> bool:
        from . import lsp_servers                  # GEM_HOME for ruby-lsp, PERL5LIB for PLS, Go on PATH for gopls
        extra = lsp_servers.server_env(server_key(self.language))
        if extra:
            from PyQt6.QtCore import QProcessEnvironment
            env = QProcessEnvironment.systemEnvironment()
            for k, v in extra.items():
                env.insert(k, v)
            self.proc.setProcessEnvironment(env)
        self.proc.start(self.argv[0], self.argv[1:])
        if not self.proc.waitForStarted(5000):
            return False
        self._request("initialize", {
            "processId": os.getpid(), "rootUri": path_uri(self.root), "rootPath": str(self.root),
            "clientInfo": {"name": "RAD IDE"},
            "initializationOptions": initialization_options(self.language, self.root),
            "workspaceFolders": [{"uri": path_uri(self.root), "name": self.root.name}],
            "capabilities": {
                "textDocument": {
                    "completion": {"completionItem": {"snippetSupport": True, "insertReplaceSupport": False,
                                                      "documentationFormat": ["plaintext", "markdown"]},
                                   "contextSupport": True},
                    "hover": {"contentFormat": ["plaintext", "markdown"]},
                    "signatureHelp": {"signatureInformation": {
                        "documentationFormat": ["markdown", "plaintext"],
                        "parameterInformation": {"labelOffsetSupport": True}, "activeParameterSupport": True}},
                    "inlayHint": {"dynamicRegistration": False},
                    "publishDiagnostics": {}, "definition": {}, "synchronization": {"didSave": True},
                    # refactoring UI (radide/features/refactor.py) and Format Document
                    "rename": {"prepareSupport": True}, "references": {}, "formatting": {},
                    "rangeFormatting": {},
                    "codeAction": {"codeActionLiteralSupport": {"codeActionKind": {"valueSet": [
                        "", "quickfix", "refactor", "refactor.extract", "refactor.inline", "refactor.rewrite",
                        "source", "source.organizeImports"]}}, "resolveSupport": {"properties": ["edit"]},
                        "dataSupport": True},
                },
                "workspace": {"workspaceFolders": True, "configuration": True, "applyEdit": True,
                              "workspaceEdit": {"documentChanges": True,
                                                "resourceOperations": ["create", "rename", "delete"]},
                              "executeCommand": {}, "inlayHint": {"refreshSupport": True}},
                "window": {"workDoneProgress": True},
                "experimental": {"serverStatusNotification": True},
            }}, self._on_initialized, force=True)
        return True

    def running(self) -> bool:
        return self.proc.state() == QProcess.ProcessState.Running

    def stop(self):
        if self.running():
            self._request("shutdown", None, lambda _r: self._notify("exit", None), force=True)
            self.proc.waitForFinished(1500)
            if self.running():
                self.proc.kill()

    def _send(self, msg: dict):
        body = json.dumps(msg).encode("utf-8")
        self.proc.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)

    def _request(self, method, params, cb=None, force=False):
        self._id += 1
        msg = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params}
        if cb is not None:
            self._callbacks[self._id] = cb
        if self._initialized or force:
            self._send(msg)
        else:
            self._queue.append(msg)

    def _notify(self, method, params):
        msg = {"jsonrpc": "2.0", "method": method, "params": params}
        if self._initialized or method in ("initialized", "exit"):
            self._send(msg)
        else:
            self._queue.append(msg)

    def _on_initialized(self, result):
        self.capabilities = (result or {}).get("capabilities", {})
        self._initialized = True
        self._send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        for msg in self._queue:
            self._send(msg)
        self._queue.clear()
        self.ready.emit()

    def _read(self):
        self._buf += bytes(self.proc.readAllStandardOutput())
        while True:
            head_end = self._buf.find(b"\r\n\r\n")
            if head_end < 0:
                return
            length = 0
            for line in self._buf[:head_end].split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":")[1])
            if len(self._buf) < head_end + 4 + length:
                return
            body = self._buf[head_end + 4:head_end + 4 + length]
            self._buf = self._buf[head_end + 4 + length:]
            try:
                msg = json.loads(body)
            except ValueError:
                continue
            self._dispatch(msg)

    def _dispatch(self, msg: dict):
        if "id" in msg and ("result" in msg or "error" in msg) and "method" not in msg:
            if "error" in msg:
                self.last_error = (msg.get("error") or {}).get("message", "") or str(msg.get("error"))
            cb = self._callbacks.pop(msg["id"], None)
            if cb is not None:
                cb(msg.get("result"))
            return
        method = msg.get("method")
        if method == "textDocument/publishDiagnostics":
            p = msg["params"]
            if not hasattr(self, "raw_diagnostics"):
                self.raw_diagnostics = {}          # uri -> LSP Diagnostic[] (code actions need them as sent)
            self.raw_diagnostics[p.get("uri", "")] = p.get("diagnostics", [])
            out = []
            for d in p.get("diagnostics", []):
                if _rad_star_import_noise(d.get("message", "")):
                    continue
                r = d["range"]
                code = d.get("code")
                out.append({"line": r["start"]["line"], "col": r["start"]["character"],
                            "endLine": r["end"]["line"], "endCol": r["end"]["character"],
                            "message": d.get("message", ""),
                            "severity": {1: "error", 2: "warning"}.get(d.get("severity", 3), "info"),
                            "source": d.get("source") or "", "code": code if isinstance(code, (str, int)) else
                            ((code or {}).get("value", "") if isinstance(code, dict) else "")})
            try:
                path = str(Path(QUrlLike.to_path(p["uri"])))
            except Exception:  # noqa: BLE001
                path = p["uri"]
            self.diagnostics.emit(path, out)
        elif method in ("window/logMessage", "window/showMessage"):
            self.log.emit(str((msg.get("params") or {}).get("message", "")))
        elif method and "id" not in msg:             # other notifications (experimental/serverStatus ...)
            if method == "experimental/serverStatus":
                self.server_status = msg.get("params") or {}
            self.notification.emit(method, msg.get("params"))
        elif "id" in msg and method == "workspace/configuration":
            conf = workspace_settings(self.language, self.root)
            items = (msg.get("params") or {}).get("items", [])
            res = []
            for it in items:
                val = conf
                for part in (it.get("section") or "").split("."):
                    if part:
                        val = val.get(part, {}) if isinstance(val, dict) else {}
                res.append(val if it.get("section") else conf)
            self._send({"jsonrpc": "2.0", "id": msg["id"], "result": res})
        elif "id" in msg and method in LspClient.request_handlers:   # e.g. workspace/applyEdit (refactor.py)
            try:
                res = LspClient.request_handlers[method](self, msg.get("params"))
            except Exception as e:  # noqa: BLE001 - never leave the server waiting
                res = {"applied": False, "failureReason": str(e)}
            self._send({"jsonrpc": "2.0", "id": msg["id"], "result": res})
        elif "id" in msg and method:                 # other server -> client requests: answer with null
            self._send({"jsonrpc": "2.0", "id": msg["id"], "result": None})
            if method.endswith("/refresh"):          # workspace/inlayHint/refresh, workspace/diagnostic/refresh
                self.notification.emit(method, msg.get("params"))

    # ------------------------------------------------------------ documents
    def did_open(self, path: Path, text: str, language_id: str):
        uri = path_uri(path)
        if uri in self._versions:                  # re-open (e.g. language changed)
            self.did_close(path)
        language_id = LSP_LANGUAGE_ID.get(language_id, language_id)
        self._versions[uri] = 1
        self._lang_ids[uri] = language_id
        self._last_text[uri] = text
        self._notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": language_id,
                                                               "version": 1, "text": text}})

    def did_change(self, path: Path, text: str):
        uri = path_uri(path)
        if uri not in self._versions:
            self.did_open(path, text, self._lang_ids.get(uri, self.language))
            return
        if self._last_text.get(uri) == text:
            return
        self._last_text[uri] = text
        self._versions[uri] += 1
        self._notify("textDocument/didChange", {"textDocument": {"uri": uri, "version": self._versions[uri]},
                                                "contentChanges": [{"text": text}]})

    def did_save(self, path: Path):
        self._notify("textDocument/didSave", {"textDocument": {"uri": path_uri(path)}})

    def did_close(self, path: Path):
        uri = path_uri(path)
        self._versions.pop(uri, None)
        self._last_text.pop(uri, None)
        self._notify("textDocument/didClose", {"textDocument": {"uri": uri}})

    # ------------------------------------------------------------ features
    def _pos(self, path, line, col):
        return {"textDocument": {"uri": path_uri(path)}, "position": {"line": line, "character": col}}

    def completion(self, path: Path, text: str, line: int, col: int, cb):
        self.did_change(path, text)

        def done(result):
            items = result.get("items", []) if isinstance(result, dict) else (result or [])
            out = []
            for it in items[:500]:
                doc = it.get("documentation", "")
                if isinstance(doc, dict):
                    doc = doc.get("value", "")
                ins = it.get("insertText") or it.get("label")
                rng = None
                te = it.get("textEdit")
                if isinstance(te, dict) and te.get("newText") is not None:
                    ins = te["newText"]
                    r = te.get("range") or te.get("replace") or te.get("insert")
                    if r and r["start"]["line"] == r["end"]["line"] == line:
                        rng = [r["start"]["line"], r["start"]["character"], r["end"]["line"], r["end"]["character"]]
                extra = [{"range": [e["range"]["start"]["line"], e["range"]["start"]["character"],
                                    e["range"]["end"]["line"], e["range"]["end"]["character"]], "text": e["newText"]}
                         for e in it.get("additionalTextEdits") or []]
                label = it.get("label", "")
                detail = it.get("detail") or ""
                ld = it.get("labelDetails") or {}
                if ld.get("detail") and ld["detail"] not in detail:
                    detail = (ld["detail"] + " " + detail).strip()
                out.append({"label": label, "kind": LSP_TO_MONACO.get(it.get("kind", 1), 18),
                            "detail": detail,"documentation": doc, "insertText": ins,
                            "snippet": it.get("insertTextFormat") == 2, "sortText": it.get("sortText"),
                            "filterText": it.get("filterText"), "range": rng, "additionalTextEdits": extra})
            cb(out)
        self._request("textDocument/completion", self._pos(path, line, col), done)

    def hover(self, path: Path, line: int, col: int, cb):
        def done(result):
            if not result:
                cb("")
                return
            c = result.get("contents")
            if isinstance(c, dict):
                cb(c.get("value", ""))
            elif isinstance(c, list):
                cb("\n".join(x.get("value", "") if isinstance(x, dict) else str(x) for x in c))
            else:
                cb(str(c or ""))
        self._request("textDocument/hover", self._pos(path, line, col), done)

    def signature_help(self, path: Path, line: int, col: int, cb):
        def done(result):
            if not result or not result.get("signatures"):
                cb("")
                return
            s = result["signatures"][result.get("activeSignature") or 0]
            cb(s.get("label", ""))
        self._request("textDocument/signatureHelp", self._pos(path, line, col), done)

    def signature_info(self, path: Path, line: int, col: int, cb):
        """Full signature help: {label, documentation, parameters: [[start, end] | label], activeParameter}
        (or None) - Monaco shows the active parameter in bold."""
        def done(result):
            if not result or not result.get("signatures"):
                cb(None)
                return
            sigs = result["signatures"]
            s = sigs[min(result.get("activeSignature") or 0, len(sigs) - 1)]
            doc = s.get("documentation") or ""
            if isinstance(doc, dict):
                doc = doc.get("value", "")
            params = []
            for prm in s.get("parameters") or []:
                lab = prm.get("label")
                params.append(lab if isinstance(lab, (str, list)) else "")
            active = s.get("activeParameter", result.get("activeParameter")) or 0
            cb({"label": s.get("label", ""), "documentation": doc, "parameters": params,
                "activeParameter": active})
        self._request("textDocument/signatureHelp", self._pos(path, line, col), done)

    def inlay_hints(self, path: Path, l1: int, l2: int, cb, end_col: int = 0):
        """textDocument/inlayHint for lines l1..l2 -> [{line, col, label, kind, left, right}] (cb gets [])."""
        if not (self.capabilities or {}).get("inlayHintProvider"):
            cb([])
            return

        def done(result):
            out = []
            for h in result or []:
                lab = h.get("label")
                if isinstance(lab, list):
                    lab = "".join(part.get("value", "") for part in lab if isinstance(part, dict))
                pos = h.get("position") or {}
                out.append({"line": pos.get("line", 0), "col": pos.get("character", 0), "label": str(lab or ""),
                            "kind": h.get("kind") or 0, "left": bool(h.get("paddingLeft")),
                            "right": bool(h.get("paddingRight"))})
            cb(out)
        self._request("textDocument/inlayHint", {"textDocument": {"uri": path_uri(path)},
                                                 "range": {"start": {"line": l1, "character": 0},
                                                           "end": {"line": l2, "character": end_col}}}, done)

    def definition(self, path: Path, line: int, col: int, cb):
        def done(result):
            if not result:
                cb(None)
                return
            loc = result[0] if isinstance(result, list) else result
            uri = loc.get("uri") or loc.get("targetUri")
            rng = loc.get("range") or loc.get("targetSelectionRange") or {"start": {"line": 0}}
            cb((QUrlLike.to_path(uri), rng["start"]["line"]))
        self._request("textDocument/definition", self._pos(path, line, col), done)


class QUrlLike:
    @staticmethod
    def to_path(uri: str) -> str:
        from PyQt6.QtCore import QUrl
        return QUrl(uri).toLocalFile()


class LspManager(QObject):
    """One server per (language, project root); created on demand."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clients: dict[tuple[str, str], LspClient | None] = {}

    def client_for(self, language: str, root: Path) -> LspClient | None:
        if server_key(language) == "rust":         # one rust-analyzer per cargo workspace (members share it)
            from .rust_tools import workspace_root
            root = workspace_root(root)
        key = (server_key(language), str(root))
        if key in self.clients:
            c = self.clients[key]
            return c if c is not None and c.running() else None
        argv = server_command(language)
        if argv is None:
            self.clients[key] = None
            return None
        c = LspClient(language, root, argv, self)
        venv = Path(root) / ".venv"
        if server_key(language) == "python" and (venv / "pyvenv.cfg").is_file():
            # projects with their own .venv (Django / Flask / FastAPI ...): jedi completes their packages
            from PyQt6.QtCore import QProcessEnvironment
            env = QProcessEnvironment.systemEnvironment()
            env.insert("VIRTUAL_ENV", str(venv))
            c.proc.setProcessEnvironment(env)
        self.clients[key] = c if c.start() else None
        return self.clients[key]

    def stop_all(self):
        for c in self.clients.values():
            if c is not None:
                c.stop()
        self.clients.clear()
