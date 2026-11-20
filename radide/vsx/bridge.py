"""Python <-> Node extension host (radide/vsx/host/main.js): JSON-RPC 2.0 with Content-Length framing on stdio.

``VsxHost`` starts ``node main.js`` with QProcess and talks to it; radide/vsx/host_ide.py wires it into the IDE.

IDE -> host
    requests       initialize {extensions: [{id, path, packageJSON}], workspaceFolders, settings, storageRoot,
                               appRoot, language, apiVersion, themeKind, languages}
                   shutdown, ping, activate {event}, extensions/status, commands/execute {command, args},
                   commands/list, lsp {method, params} (LSP-shaped language features served by the extensions'
                   vscode.languages providers), tree/children {viewId, handle}, debug/resolve {type, config,
                   folder, file}, debug/contributed
    notifications  document/open {path, languageId, version, text}, document/change {path, version, text,
                   dirty}, document/save {path}, document/close {path}, editor/active {path, selection},
                   editor/selection {path, selection}, configuration/changed {settings, keys},
                   workspace/folders {folders}, theme/changed {kind}, progress/cancel {id},
                   terminal/closed {id, code}, files/event {kind, paths}, debug/sessionStarted|Terminated|customEvent
host -> IDE
    requests       window/showMessage {severity, message, detail, modal, items} -> index | null
                   window/showQuickPick {items, canPickMany, placeHolder, title} -> index | [indices] | null
                   window/showInputBox {value, prompt, placeHolder, password, title, validationMessage} -> str|null
                   window/showOpenDialog, window/showSaveDialog, window/showTextDocument {path, selection},
                   workspace/applyEdit {edits: [{path, edits: [{range: [l1, c1, l2, c2], text}]}], files},
                   workspace/save {path}, workspace/saveAll, workspace/setLanguage {path, language},
                   configuration/update {key, value, remove, target}, commands/executeIde {command, args},
                   env/clipboardRead, env/clipboardWrite {text}, env/openExternal {uri},
                   editor/insertSnippet {path, snippet, range}, debug/start {config, folder},
                   debug/customRequest {sessionId, command, args}, debug/stop {id}
    notifications  output/create|append|replace|clear|show {channel, text}, statusBar/set|remove,
                   diagnostics/set {owner, path, diagnostics}, providers/changed {providers},
                   commands/registered|unregistered {id}, context/set {key, value}, languages/setConfiguration,
                   window/progress, window/setStatusBarMessage, terminal/create|sendText|show|dispose|write,
                   editor/setSelection, editor/reveal, editor/decorations, decorations/type|disposeType,
                   tree/registered|changed, extension/activated|activationFailed, host/ready, host/unsupported

Handlers for host requests are ``fn(params, reply)``; call ``reply(result)`` now or later (dialogs).
No IDE imports here (only PyQt6.QtCore), so it is testable without a main window.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from PyQt6.QtCore import QEventLoop, QObject, QProcess, QProcessEnvironment, QTimer, pyqtSignal

HOST_DIR = Path(__file__).resolve().parent / "host"
MAIN_JS = HOST_DIR / "main.js"
RELAY_JS = HOST_DIR / "relay.js"


def find_node() -> str:
    """node.exe: RAD_NODE / PATH / the default install folder / the IDE's private tools folder."""
    env = os.environ.get("RADIDE_NODE")
    if env and Path(env).is_file():
        return env
    w = shutil.which("node")
    if w:
        return w
    local = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE" / "tools"
    for cand in (Path(r"C:\Program Files\nodejs\node.exe"), local / "node" / "node.exe"):
        if cand.is_file():
            return str(cand)
    return ""


class VsxHost(QObject):
    notification = pyqtSignal(str, object)       # host notification (method, params)
    started = pyqtSignal(object)                 # initialize result
    stopped = pyqtSignal(int)                    # exit code
    stderr = pyqtSignal(str)                     # extension console output (stdout is redirected there)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc: QProcess | None = None
        self._buf = b""
        self._id = 0
        self._callbacks: dict[int, object] = {}
        self.handlers: dict[str, object] = {}    # method -> fn(params, reply)
        self.init_result = None
        self._stopping = False

    # ------------------------------------------------------------ process
    def running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def start(self, init_params: dict, node: str | None = None, env: dict | None = None) -> bool:
        node = node or find_node()
        if not node or not MAIN_JS.is_file():
            return False
        self.stop()
        self._stopping = False
        self._buf = b""
        self.proc = QProcess(self)
        pe = QProcessEnvironment.systemEnvironment()
        pe.insert("RADIDE_EXTENSION_HOST", "1")
        pe.remove("ELECTRON_RUN_AS_NODE")
        for k, v in (env or {}).items():
            pe.insert(k, str(v))
        self.proc.setProcessEnvironment(pe)
        self.proc.setWorkingDirectory(str(HOST_DIR))
        self.proc.readyReadStandardOutput.connect(self._read)
        self.proc.readyReadStandardError.connect(self._read_err)
        self.proc.finished.connect(self._finished)
        self.proc.start(node, ["--max-old-space-size=3072", str(MAIN_JS)])
        if not self.proc.waitForStarted(8000):
            self.proc = None
            return False

        def done(res):
            self.init_result = res
            self.started.emit(res)
        self.request("initialize", init_params, done)
        return True

    def stop(self, timeout_ms: int = 3000) -> None:
        p = self.proc
        if p is None:
            return
        self._stopping = True
        if p.state() != QProcess.ProcessState.NotRunning:
            try:
                self.request_sync("shutdown", {}, timeout_ms)
            except Exception:  # noqa: BLE001
                pass
            if not p.waitForFinished(1500):
                p.kill()
                p.waitForFinished(1500)
        self.proc = None
        self._callbacks.clear()

    def _finished(self, code, _status=None):
        cbs, self._callbacks = self._callbacks, {}
        for cb in cbs.values():
            try:
                cb(None)
            except Exception:  # noqa: BLE001
                pass
        self.stopped.emit(int(code))

    def _read_err(self):
        if self.proc is not None:
            self.stderr.emit(bytes(self.proc.readAllStandardError()).decode("utf-8", "replace"))

    # ------------------------------------------------------------ framing
    def _write(self, msg: dict) -> None:
        if not self.running():
            return
        body = json.dumps(msg, ensure_ascii=False, default=str).encode("utf-8")
        self.proc.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)

    def _read(self):
        if self.proc is None:
            return
        self._buf += bytes(self.proc.readAllStandardOutput())
        msgs = []
        while True:
            end = self._buf.find(b"\r\n\r\n")
            if end < 0:
                break
            length = 0
            for line in self._buf[:end].split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    length = int(line.split(b":")[1])
            if len(self._buf) < end + 4 + length:
                break
            body, self._buf = self._buf[end + 4:end + 4 + length], self._buf[end + 4 + length:]
            try:
                msgs.append(json.loads(body))
            except ValueError:
                continue
        for m in msgs:                       # dispatch after the buffer is consumed (handlers may run event loops)
            self._dispatch(m)

    def _dispatch(self, msg: dict) -> None:
        method = msg.get("method")
        if method is None and "id" in msg:                     # response
            cb = self._callbacks.pop(msg["id"], None)
            if cb is not None:
                try:
                    cb(msg.get("result") if "error" not in msg else None)
                except Exception as e:  # noqa: BLE001 - a callback must not break the bridge
                    self.stderr.emit(f"[vsx bridge] callback failed: {e}\n")
            return
        if "id" in msg:                                        # request from the host
            rid = msg["id"]
            h = self.handlers.get(method)
            answered = [False]

            def reply(result=None, rid=rid):
                if not answered[0]:
                    answered[0] = True
                    self._write({"jsonrpc": "2.0", "id": rid, "result": result})
            if h is None:
                reply(None)
                return
            try:
                h(msg.get("params") or {}, reply)
            except Exception as e:  # noqa: BLE001 - never leave the host waiting
                self.stderr.emit(f"[vsx bridge] handler {method} failed: {e}\n")
                reply(None)
            return
        self.notification.emit(method or "", msg.get("params") or {})

    # ------------------------------------------------------------ API
    def request(self, method: str, params=None, cb=None, timeout_ms: int | None = None) -> int:
        self._id += 1
        rid = self._id
        if cb is not None:
            self._callbacks[rid] = cb
            if timeout_ms:
                def expire(rid=rid):
                    c = self._callbacks.pop(rid, None)
                    if c is not None:
                        c(None)
                QTimer.singleShot(timeout_ms, expire)
        self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        return rid

    def request_sync(self, method: str, params=None, timeout_ms: int = 10000):
        """Wait (with a local event loop) for the answer; None on timeout."""
        box = {}
        loop = QEventLoop()

        def done(res):
            box["r"] = res
            loop.quit()
        self.request(method, params, done)
        if "r" not in box and self.running():
            QTimer.singleShot(timeout_ms, loop.quit)
            loop.exec()
        return box.get("r")

    def notify(self, method: str, params=None) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params or {}})


__all__ = ["VsxHost", "find_node", "MAIN_JS", "RELAY_JS", "HOST_DIR"]
