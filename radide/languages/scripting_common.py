"""Shared base for the scripting GUI-Bridge languages (Lua, Ruby, Perl, Go, Dart).

Each language ships a client library in ``radide/runtimes/clients/<lang>/`` that
speaks the GUI Bridge protocol (set/get/call/msgbox/input/show/hide/end) and the
RAD Hub protocol (``radcall``), plus a JSON-lines worker that serves the functions
of one module to other languages (docs/CONTRACTS.md sections 1 and 2).

A subclass sets the language description (syntax, API table, client files,
worker script) and implements the templates and ``main_source``.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

from ..controls import CONTROL_TYPES, FORM_PROPS
from ..model import Form, Project
from .base import Completion
from .bridgebase import CLIENTS, BridgeLanguagePlugin

# VB-style names usable with set/get (properties) and call (methods)
CONTROL_METHODS = ["AddItem", "RemoveItem", "Clear", "List", "SetFocus", "Move", "Refresh", "ZOrder",
                   "ShowDialog", "Show", "Hide", "Start", "Stop"]


def _property_names() -> list[str]:
    names = {"Caption", "Text", "Value", "Enabled", "Visible", "Left", "Top", "Width", "Height",
             "BackColor", "ForeColor", "ListIndex", "ListCount", "Interval"}
    names |= set(FORM_PROPS)
    for ct in CONTROL_TYPES.values():
        try:
            names |= {p.name for p in ct.prop_defs()}
        except Exception:  # noqa: BLE001 - catalogue entries are edited by other agents
            pass
    names.discard("Name")
    names.discard("Parent")
    return sorted(names)


# A tiny worker used when the language tool is missing: it answers every request
# with an error so the RAD Hub caller gets a clear message instead of a hang.
_ERROR_WORKER = (
    "import json,sys\n"
    "msg=sys.argv[1]\n"
    "sys.stderr.write(msg+'\\n'); sys.stderr.flush()\n"
    "for line in sys.stdin:\n"
    "    line=line.strip()\n"
    "    if not line: continue\n"
    "    try: rid=json.loads(line).get('id')\n"
    "    except Exception: rid=None\n"
    "    sys.stdout.write(json.dumps({'id': rid, 'error': msg})+'\\n'); sys.stdout.flush()\n")


def error_worker(message: str) -> list[str]:
    """argv of a worker that fails every call with *message*."""
    return [sys.executable, "-c", _ERROR_WORKER, message]


class ScriptBridgePlugin(BridgeLanguagePlugin):
    client_subdir = ""                  # folder under runtimes/clients
    client_names: list[str] = []        # files copied into the project before running
    worker_script = ""                  # client file that implements the RAD Hub worker
    api: dict[str, str] = {}            # client API: name -> "signature - description"
    quote_names = True                  # complete control names as "name"

    # ------------------------------------------------------------ clients
    def client_files(self) -> dict[str, Path]:
        base = CLIENTS / self.client_subdir
        return {n: base / n for n in self.client_names}

    def copy_clients(self, folder: Path) -> None:
        for target, src in self.client_files().items():
            dst = folder / target
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                if dst.exists() and dst.read_bytes() == src.read_bytes():
                    continue
            except OSError:
                pass
            shutil.copy2(src, dst)

    def prepare(self, folder: Path, project: Project) -> None:
        self.copy_clients(folder)
        main = self.main_source(project)
        if main is not None:
            name, text = main
            (folder / name).write_text(text, encoding="utf-8")

    def sibling_tool(self, name: str) -> str:
        """A companion executable (gem, luarocks, ...): PATH first, then next to the language tool."""
        found = shutil.which(name)
        if found:
            return found
        t = self.tool()
        if t and Path(t).is_absolute():
            # Windows: an extension-less file (RubyInstaller's bin\gem) is a script that
            # CreateProcess cannot start - prefer gem.cmd / luarocks.exe
            exts = (".exe", ".bat", ".cmd", "") if os.name == "nt" else ("", ".exe", ".bat", ".cmd")
            for ext in exts:
                p = Path(t).parent / f"{name}{ext}"
                if p.is_file():
                    return str(p)
        return name

    # ------------------------------------------------------------ project helpers
    def my_forms(self, project: Project) -> list[str]:
        """Forms of *project* written in this language (mixed projects have others)."""
        out = []
        for f in project.forms:
            lang = project.form_language(f) if hasattr(project, "form_language") else project.language
            if lang == self.id:
                out.append(f)
        return out

    def code_files(self, project: Project) -> list[str]:
        files = [self.code_file(f) for f in self.my_forms(project)]
        files += [m for m in project.modules if m.lower().endswith(self.code_ext)]
        return files

    def handler_defs(self, code: str) -> list[str]:
        """Handler names (<Owner>_<Event>) defined in *code*."""
        return re.findall(self.handler_regex, code, re.I | re.M)

    @staticmethod
    def module_rel(folder: Path, module_file: str) -> str:
        p = Path(module_file)
        if p.is_absolute():
            try:
                return p.relative_to(folder).as_posix()
            except ValueError:
                return str(p)
        return p.as_posix()

    # ------------------------------------------------------------ worker
    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        folder = Path(folder)
        tool = self.tool()
        if not tool:
            return error_worker(f"{self.display_name}: required tool not found "
                                f"({', '.join(self.tool_names)}). {self.install_hint}")
        self.copy_clients(folder)
        return self.worker_argv(tool, folder, self.module_rel(folder, module_file))

    def worker_argv(self, tool: str, folder: Path, module_rel: str) -> list[str]:
        return [tool, self.worker_script, module_rel]

    # ------------------------------------------------------------ designer file
    def generate_designer(self, form: Form, user_code: str) -> str:
        c = self.line_comments[0] if self.line_comments else "#"
        lines = [f"{c} AUTO-GENERATED by RAD IDE - do not edit. Form {form.name} is drawn by the IDE",
                 f"{c} (GUI Bridge); the program reads and changes it with set/get/call. Controls:"]
        for ctrl in form.controls:
            lines.append(f"{c}   {ctrl.name}: {ctrl.type}")
        handlers = self.handler_defs(user_code)
        if handlers:
            lines.append(f"{c} Handlers: {', '.join(handlers)}")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        # second string argument of set/get/call: property or method names
        if re.search(r"""\(\s*["'][\w.]+["']\s*,\s*["'][A-Za-z]*$""", before):
            props = [Completion(p, "property") for p in _property_names()]
            return props + [Completion(m, "method") for m in CONTROL_METHODS]
        # inside the first string argument: control names
        if re.search(r"""\(\s*["'][\w.]*$""", before):
            return [Completion(n, "control", t) for n, t in (names or {}).items()]
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(n, "function", d) for n, d in self.api.items()]
        out += [Completion(b, "function") for b in self.builtins if b not in self.api]
        q = '"' if self.quote_names else ""
        out += [Completion(f"{q}{n}{q}", "control", t) for n, t in (names or {}).items()]
        seen = {c.name.lower() for c in out}
        for w in re.findall(r"[A-Za-z_]\w{2,}", code):
            if w.lower() not in seen:
                seen.add(w.lower())
                out.append(Completion(w, "variable"))
        return out

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        # innermost unclosed call
        depth = 0
        for i in range(len(before) - 1, -1, -1):
            ch = before[i]
            if ch == ")":
                depth += 1
            elif ch == "(":
                if depth == 0:
                    m = re.search(r"([\w.:]+)\s*$", before[:i])
                    if not m:
                        return ""
                    name = m.group(1)
                    for key in (name, name.split(".")[-1], name.split("::")[-1]):
                        if key in self.api:
                            return f"{key}: {self.api[key]}"
                    return ""
                depth -= 1
        return ""
