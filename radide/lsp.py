"""Language Server Protocol client (one generic client for every language).

Ready-made language servers give completion, hover, signature help, go to
definition and live diagnostics. SERVERS lists the command lines tried for
each Monaco language id; the first one whose executable exists is used.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal

VENV_PY = sys.executable

# language id -> list of candidate argv (first available wins) + install hint
SERVERS: dict[str, tuple[list[list[str]], str]] = {
    "python": ([[VENV_PY, "-m", "pylsp"], ["pyright-langserver", "--stdio"]], "pip install python-lsp-server"),
    "javascript": ([["typescript-language-server", "--stdio"]], "npm i -g typescript typescript-language-server"),
    "typescript": ([["typescript-language-server", "--stdio"]], "npm i -g typescript typescript-language-server"),
    "csharp": ([["csharp-ls"]], "dotnet tool install -g csharp-ls"),
    "java": ([["jdtls"]], "install Eclipse JDT Language Server (jdtls)"),
    "rust": ([["rust-analyzer"]], "rustup component add rust-analyzer"),
    "c": ([["clangd"]], "install clangd (LLVM)"),
    "cpp": ([["clangd"]], "install clangd (LLVM)"),
    "go": ([["gopls"]], "go install golang.org/x/tools/gopls@latest"),
    "php": ([["intelephense", "--stdio"]], "npm i -g intelephense"),
    "dart": ([["dart", "language-server", "--protocol=lsp"]], "comes with the Dart SDK"),
    "lua": ([["lua-language-server"]], "install lua-language-server"),
    "ruby": ([["solargraph", "stdio"]], "gem install solargraph"),
    "rad-fortran-bridge": ([["fortls"]], "pip install fortls"),
    "powershell": ([], "PowerShell Editor Services is not supported yet"),
}

# LSP CompletionItemKind -> Monaco CompletionItemKind
LSP_TO_MONACO = {1: 18, 2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 7, 9: 8, 10: 9, 11: 12, 12: 13, 13: 15,
                 14: 17, 15: 27, 16: 19, 17: 20, 18: 21, 19: 23, 20: 16, 21: 14, 22: 6, 23: 10, 24: 11, 25: 24}


def server_command(language: str) -> list[str] | None:
    cands, _hint = SERVERS.get(language, ([], ""))
    for argv in cands:
        exe = argv[0]
        if exe == VENV_PY:
            try:
                __import__(argv[2].replace("-", "_"))
                return argv
            except ImportError:
                continue
        if shutil.which(exe):
            return [shutil.which(exe), *argv[1:]]
    return None


def install_hint(language: str) -> str:
    return SERVERS.get(language, ([], ""))[1]


def path_uri(p: Path) -> str:
    return Path(p).resolve().as_uri()


class LspClient(QObject):
    diagnostics = pyqtSignal(str, list)        # file path, [{line, col, endLine, endCol, message, severity}]
    log = pyqtSignal(str)

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
        self._initialized = False
        self._queue: list[dict] = []
        self.capabilities: dict = {}

    # ------------------------------------------------------------ process / framing
    def start(self) -> bool:
        self.proc.start(self.argv[0], self.argv[1:])
        if not self.proc.waitForStarted(5000):
            return False
        self._request("initialize", {
            "processId": os.getpid(), "rootUri": path_uri(self.root),
            "workspaceFolders": [{"uri": path_uri(self.root), "name": self.root.name}],
            "capabilities": {
                "textDocument": {
                    "completion": {"completionItem": {"snippetSupport": True, "documentationFormat": ["plaintext", "markdown"]}},
                    "hover": {"contentFormat": ["plaintext", "markdown"]},
                    "signatureHelp": {"signatureInformation": {"documentationFormat": ["plaintext"]}},
                    "publishDiagnostics": {}, "definition": {}, "synchronization": {"didSave": True},
                },
                "workspace": {"workspaceFolders": True},
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
            cb = self._callbacks.pop(msg["id"], None)
            if cb is not None:
                cb(msg.get("result"))
            return
        method = msg.get("method")
        if method == "textDocument/publishDiagnostics":
            p = msg["params"]
            out = []
            for d in p.get("diagnostics", []):
                r = d["range"]
                out.append({"line": r["start"]["line"], "col": r["start"]["character"],
                            "endLine": r["end"]["line"], "endCol": r["end"]["character"],
                            "message": d.get("message", ""),
                            "severity": {1: "error", 2: "warning"}.get(d.get("severity", 3), "info")})
            try:
                path = str(Path(QUrlLike.to_path(p["uri"])))
            except Exception:  # noqa: BLE001
                path = p["uri"]
            self.diagnostics.emit(path, out)
        elif "id" in msg and method:                 # server -> client request: answer with null
            self._send({"jsonrpc": "2.0", "id": msg["id"], "result": None})

    # ------------------------------------------------------------ documents
    def did_open(self, path: Path, text: str, language_id: str):
        uri = path_uri(path)
        self._versions[uri] = 1
        self._notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": language_id,
                                                               "version": 1, "text": text}})

    def did_change(self, path: Path, text: str):
        uri = path_uri(path)
        if uri not in self._versions:
            self.did_open(path, text, self.language)
            return
        self._versions[uri] += 1
        self._notify("textDocument/didChange", {"textDocument": {"uri": uri, "version": self._versions[uri]},
                                                "contentChanges": [{"text": text}]})

    def did_save(self, path: Path):
        self._notify("textDocument/didSave", {"textDocument": {"uri": path_uri(path)}})

    def did_close(self, path: Path):
        uri = path_uri(path)
        self._versions.pop(uri, None)
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
                te = it.get("textEdit")
                if isinstance(te, dict) and te.get("newText"):
                    ins = te["newText"]
                out.append({"label": it.get("label", ""), "kind": LSP_TO_MONACO.get(it.get("kind", 1), 18),
                            "detail": it.get("detail", ""), "documentation": doc, "insertText": ins,
                            "snippet": it.get("insertTextFormat") == 2, "sortText": it.get("sortText")})
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
        key = (language, str(root))
        if key in self.clients:
            c = self.clients[key]
            return c if c is not None and c.running() else None
        argv = server_command(language)
        if argv is None:
            self.clients[key] = None
            return None
        c = LspClient(language, root, argv, self)
        self.clients[key] = c if c.start() else None
        return self.clients[key]

    def stop_all(self):
        for c in self.clients.values():
            if c is not None:
                c.stop()
        self.clients.clear()
