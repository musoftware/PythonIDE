"""Node.js Web Site projects (docs/CONTRACTS.md 8.1): ``node <start>`` with ``PORT`` set, behind the IDE's
DevServer (request log, live reload). ``npm install`` runs first when package.json has dependencies and
node_modules is missing; the server restarts when its code changes (files outside public/static/views).
``web.command`` (a shell command, ``{port}`` = the port) replaces ``node <start>`` (e.g. "npm run dev")."""
from __future__ import annotations

import json
import shutil

from ..web_site.project import WebSitePlugin
from .javascript import JS_BUILTINS, JS_KEYWORDS, JavaScriptPlugin


class NodeWebPlugin(WebSitePlugin):
    id = "node-web"
    display_name = "Node.js Web Site (Express)"
    code_ext = ".js"
    web_kind = "node"
    needs_interpreter = True
    default_template = "node-express"
    interpreter_names = ["node"]
    interpreter_hints = [r"C:\Program Files\nodejs\node.exe"]
    tool_names = ["node"]
    keywords = JS_KEYWORDS
    builtins = [b for b in JS_BUILTINS if not b.startswith("rad")] + ["require", "module", "exports", "__dirname"]
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'", "`"]
    package_manager = JavaScriptPlugin.package_manager

    def tool(self) -> str:
        return self.find_interpreter("")

    def module_template(self, name: str) -> str:
        return f"// {name}.js\n'use strict';\n\nmodule.exports = {{}};\n"

    def backend(self, server) -> dict:
        node = server.interpreter or self.find_interpreter("") or "node"
        cfg = server.config
        prepare = []
        pkg = server.folder / "package.json"
        try:
            data = json.loads(pkg.read_text(encoding="utf-8")) if pkg.is_file() else {}
        except (OSError, ValueError):
            data = {}
        if (data.get("dependencies") or data.get("devDependencies")) and not (server.folder / "node_modules").is_dir():
            npm = shutil.which("npm") or shutil.which("npm.cmd") or "npm"
            prepare.append([npm, "install", "--no-audit", "--no-fund"])
        env = {"PORT": "{port}", "NODE_ENV": "development"}
        command = str(cfg.get("command") or "")
        if command:
            return {"argv": ["cmd", "/c", command] if shutil.which("cmd") else ["sh", "-c", command],
                    "cwd": server.folder, "env": env, "prepare": prepare,
                    "restart_on_change": bool(cfg.get("restart_on_change", True)),   # Vite/Angular: own HMR
                    "timeout": int(cfg.get("timeout", 60))}
        start = str(cfg.get("start") or data.get("main") or "server.js")
        return {"argv": [node, start], "cwd": server.folder, "env": env, "prepare": prepare,
                "restart_on_change": True, "timeout": 30}


PLUGIN = NodeWebPlugin()
