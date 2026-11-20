"""Debuggers contributed by VS Code extensions (``contributes.debuggers``) -> radide/dap.py sessions.

What to run comes from the extension host (``debug/resolve``): configuration providers
(resolveDebugConfiguration...), ``${...}`` variables (also ``${command:...}`` answered by the extension),
and the debug adapter descriptor - an executable (the declared "program"/"runtime" or a factory's
DebugAdapterExecutable), a server port / named pipe, or an inline implementation the host serves on a local
port. Sockets reach DapSession (which talks stdio) through host/relay.js.

Without the host (Node missing) declarative debuggers with a "program" still work: the adapter is started
directly with the first "initialConfigurations" entry (``${file}`` / ``${workspaceFolder}`` substituted).

Each run registers ``dap.ADAPTERS["vsx:<type>"]`` for the resolved adapter, so the rest of the IDE
(Locals, Call Stack, Watch, breakpoints, Immediate window) works like with the built-in adapters.
Configurations: ``.vscode/launch.json`` of the project / file folder (JSON with comments) is honoured;
F5 in an editor whose language a contributed debugger declares starts it when the project has no
debugger of its own for that file.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from .. import dap


# ============================================================================ contributions
def contributed(extensions=None) -> list[dict]:
    """[{type, label, languages, ext, path, contribution}] of the enabled extensions."""
    if extensions is None:
        try:
            from . import list_enabled
            extensions = list_enabled()
        except Exception:  # noqa: BLE001
            extensions = []
    out = []
    for ext in extensions:
        for d in ext.contributes_list("debuggers"):
            if isinstance(d, dict) and d.get("type"):
                out.append({"type": d["type"], "label": d.get("label") or d["type"],
                            "languages": list(d.get("languages") or []), "ext": ext.id,
                            "path": str(ext.path) if ext.path else "", "contribution": d})
    return out


def for_language(language: str, extensions=None) -> list[dict]:
    return [d for d in contributed(extensions) if language in d["languages"]]


def declared_executable(entry: dict, node: str = "") -> list[str] | None:
    """argv of a declarative adapter ("program" + optional "runtime"), or None."""
    c = dict(entry["contribution"])
    plat = "windows" if sys.platform == "win32" else "osx" if sys.platform == "darwin" else "linux"
    if isinstance(c.get(plat), dict):
        c.update(c[plat])
    prog = c.get("program")
    if not prog:
        return None
    p = Path(prog)
    if not p.is_absolute():
        p = Path(entry["path"]) / prog
    if not p.exists() and not p.with_suffix(".js").exists() and not Path(str(p) + ".exe").exists():
        return None
    args = [str(a) for a in c.get("args") or []]
    rt = c.get("runtime")
    if rt:
        if rt == "node":
            from .bridge import find_node
            rt = node or find_node()
            if not rt:
                return None
        return [rt, *[str(a) for a in c.get("runtimeArgs") or []], str(p), *args]
    return [str(p), *args]


# ============================================================================ launch.json
def _strip_jsonc(text: str) -> str:
    try:
        from .contrib_common import strip_jsonc
        return strip_jsonc(text)
    except Exception:  # noqa: BLE001
        text = re.sub(r"//[^\n]*", "", text)
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        return re.sub(r",(\s*[}\]])", r"\1", text)


def launch_configurations(folder) -> list[dict]:
    """configurations of <folder>/.vscode/launch.json ([] when missing / broken)."""
    if not folder:
        return []
    f = Path(folder) / ".vscode" / "launch.json"
    try:
        data = json.loads(_strip_jsonc(f.read_text("utf-8")))
    except (OSError, ValueError):
        return []
    confs = data.get("configurations") if isinstance(data, dict) else None
    return [c for c in confs or [] if isinstance(c, dict) and c.get("type")]


def substitute(value, folder: str, file: str):
    """${workspaceFolder} / ${file} ... for runs without the extension host."""
    if isinstance(value, str):
        fp = Path(file) if file else None
        rep = {"workspaceFolder": folder, "workspaceRoot": folder, "workspaceFolderBasename": Path(folder).name if folder else "",
               "file": file, "fileBasename": fp.name if fp else "", "fileDirname": str(fp.parent) if fp else "",
               "fileExtname": fp.suffix if fp else "", "fileBasenameNoExtension": fp.stem if fp else "",
               "cwd": folder, "pathSeparator": os.sep, "userHome": str(Path.home())}

        def one(m):
            k = m.group(1)
            if k.startswith("env:"):
                return os.environ.get(k[4:], "")
            return rep.get(k, m.group(0))
        return re.sub(r"\$\{([^}]+)\}", one, value)
    if isinstance(value, list):
        return [substitute(v, folder, file) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, folder, file) for k, v in value.items()}
    return value


# ============================================================================ sessions
class VsxDapSession(dap.DapSession):
    """A DapSession for an extension debugger: adapterID is the debug type; the resolved launch
    configuration is sent as is (attach requests too)."""

    def __init__(self, adapter_key: str, debug_type: str, config: dict, cwd: Path, breakpoints, parent=None,
                 session_id: str = "", env: dict | None = None):
        self.debug_type = debug_type
        self.vsx_session_id = session_id
        self.config = config
        super().__init__(adapter_key, str(config.get("program") or ""), [], cwd, env, breakpoints, parent)
        self.launch_args = dict(config)
        self.break_on_exception = False

    def start(self):
        if not self.argv:
            self.failed.emit(f"debug adapter for '{self.debug_type}' cannot be started")
            self.finished.emit(1)
            return
        self.proc.start(self.argv[0], self.argv[1:])
        self._request("initialize", {"clientID": "radide", "clientName": "RAD IDE", "adapterID": self.debug_type,
                                     "linesStartAt1": True, "columnsStartAt1": True, "pathFormat": "path",
                                     "locale": "en", "supportsRunInTerminalRequest": False,
                                     "supportsVariableType": True, "supportsProgressReporting": False},
                      self._on_initialize)

    def _on_initialize(self, body, _msg):
        self.capabilities = body or {}
        self._request("attach" if self.config.get("request") == "attach" else "launch", self.launch_args)

    def _dispatch(self, msg):
        if msg.get("type") == "event" and msg.get("event") == "initialized":
            filters = []
            if self.break_on_exception:
                filters = [f.get("filter") for f in (getattr(self, "capabilities", {}) or {}).get(
                    "exceptionBreakpointFilters") or [] if f.get("default")]
            self._request("setExceptionBreakpoints", {"filters": filters})
            self._send_breakpoints(lambda: self._request("configurationDone"))
            return
        if msg.get("type") == "event" and msg.get("event") not in (
                "output", "stopped", "continued", "exited", "terminated", "initialized", "thread", "breakpoint",
                "module", "loadedSource", "process", "capabilities", "invalidated"):
            for fn in list(CUSTOM_EVENT_HOOKS):
                try:
                    fn(self, msg.get("event"), msg.get("body"))
                except Exception:  # noqa: BLE001
                    pass
        super()._dispatch(msg)

    def custom_request(self, command, args, cb):
        self._request(command, args or {}, lambda b, m: cb(b if m.get("success", True) else None))


CUSTOM_EVENT_HOOKS: list = []


def adapter_argv(adapter: dict, node: str = "") -> list[str] | None:
    """argv for DapSession from a resolved adapter descriptor of the host."""
    from .bridge import RELAY_JS, find_node
    kind = adapter.get("kind")
    if kind == "executable":
        cmd = adapter.get("command") or ""
        if not cmd:
            return None
        return [cmd, *[str(a) for a in adapter.get("args") or []]]
    node = node or find_node()
    if not node:
        return None
    if kind == "server":
        return [node, str(RELAY_JS), str(adapter.get("host") or "127.0.0.1"), str(adapter.get("port"))]
    if kind == "pipe":
        return [node, str(RELAY_JS), "--pipe", str(adapter.get("path"))]
    return None


def make_session(debug_type: str, config: dict, adapter: dict, cwd, breakpoints, parent=None,
                 session_id: str = "") -> VsxDapSession | None:
    argv = adapter_argv(adapter)
    if not argv:
        return None
    key = f"vsx:{debug_type}"
    cfg = dict(config)
    dap.ADAPTERS[key] = (lambda a=argv: list(a), lambda prog, args, cwd_, env, c=cfg: dict(c))
    env = adapter.get("env") if isinstance(adapter.get("env"), dict) else None
    s = VsxDapSession(key, debug_type, cfg, Path(adapter.get("cwd") or cwd), breakpoints, parent, session_id, env)
    return s


__all__ = ["contributed", "for_language", "declared_executable", "launch_configurations", "substitute",
           "VsxDapSession", "adapter_argv", "make_session", "CUSTOM_EVENT_HOOKS"]
