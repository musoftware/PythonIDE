"""JavaScript language plugin (GUI Bridge + Node.js).

Form code files are plain scripts: every top-level ``function <Control>_<Event>(e)``
is an event handler. The generated ``_radmain.js`` loads the project's modules and
form code into one global scope (radgui.js) and dispatches bridge events by name.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..controls import CONTROL_TYPES
from ..model import Form, Project
from .base import Completion, PackageManager
from .bridgebase import CLIENTS, BridgeLanguagePlugin

JS_CLIENT = CLIENTS / "js"

# client API shown in completions / calltips
API = {
    "set": "set(obj, prop, value)  - set a property: set(\"lblOut\", \"Caption\", \"Hi\")",
    "get": "get(obj, prop) -> string  - read a property: get(\"txtA\", \"Text\")",
    "getNum": "getNum(obj, prop) -> number  - read a property as a number",
    "call": "call(obj, method, ...args) -> string  - call(\"lstLog\", \"AddItem\", \"text\")",
    "msgbox": "msgbox(text)  - show a message box",
    "input": "input(prompt) -> string  - ask the user for text",
    "show": "show(form)  - show a form", "hide": "hide(form)  - hide a form",
    "end": "end()  - quit the program",
    "ui": "ui.<control>.<Prop> (get/set) and ui.<control>.<Method>(...)",
    "radcall": "radcall(\"Module.func\", ...args) -> value  - call a function of any project module",
    "require": "require(name)  - load a Node.js / npm module (node_modules of the project)",
}
METHODS = ["AddItem", "RemoveItem", "Clear", "List", "SetFocus", "Move", "Show", "Hide", "Refresh",
           "ShowDialog"]
EXTRA_PROPS = ["ListIndex", "ListCount", "Value", "Interval", "SelectedIndex", "Checked"]

JS_KEYWORDS = """break case catch class const continue debugger default delete do else export extends
    false finally for function if import in instanceof let new null return static super switch this throw
    true try typeof undefined var void while with yield async await of NaN Infinity""".split()
JS_BUILTINS = list(API) + """console Math JSON Number String Boolean Array Object Date RegExp Map Set
    Promise Error parseInt parseFloat isNaN isFinite setTimeout process Buffer""".split()


class JavaScriptPlugin(BridgeLanguagePlugin):
    id = "javascript"
    display_name = "JavaScript (GUI Bridge, Node.js)"
    code_ext = ".js"
    tool_names = ["node"]
    tool_hints = [r"C:\Program Files\nodejs\node.exe", r"C:\Program Files (x86)\nodejs\node.exe"]
    install_hint = "Install Node.js 22 or newer from https://nodejs.org and add it to PATH."
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'", "`"]
    keywords = JS_KEYWORDS
    builtins = JS_BUILTINS
    # function cmdGo_Click(e) { ... }   or   const cmdGo_Click = (e) => { ... }
    handler_regex = (r"^[ \t]*(?:export[ \t]+)?(?:function[ \t]*\*?[ \t]+|(?:const|let|var)[ \t]+)"
                     r"(\w+_\w+)[ \t]*(?:\(|=|:|<)")
    main_file = "_radmain.js"
    package_manager = PackageManager(
        name="npm", tool="npm",
        list_cmd=["npm", "ls", "--depth=0"],
        search_cmd=["npm", "search", "{query}"],
        install_cmd=["npm", "install", "{name}"],
        uninstall_cmd=["npm", "uninstall", "{name}"],
        init_cmd=["npm", "init", "-y"],
        manifest="package.json",
        search_url="https://www.npmjs.com/search?q={query}",
    )

    # ------------------------------------------------------------ templates
    def _comment(self, text: str) -> str:
        return "\n".join(f"// {t}".rstrip() for t in text.splitlines())

    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        head = self._comment(
            f"Event handlers for {n}. A handler is a function named <Control>_<Event>(e).\n"
            "Controls: get(\"txtA\", \"Text\"), set(\"lblOut\", \"Caption\", x), call(\"lstLog\", \"AddItem\", x)\n"
            "  or ui.txtA.Text, ui.lblOut.Caption = x, ui.lstLog.AddItem(x). Also msgbox, input, end.\n"
            "Other modules: radcall(\"Module.func\", ...args). npm packages: require(\"name\").")
        return (f"{head}\n\n"
                f"function {n}_Load(e) {{\n"
                f"    // runs when the form is shown\n"
                f"}}\n")

    def handler_stub(self, name: str) -> list[str]:
        return [f"function {name}(e) {{", "    ", "}"]

    def module_template(self, name: str) -> str:
        head = self._comment(
            f"Module {name}. Its top-level functions can be called\n"
            f"  - directly from the {self.short_name()} forms of this project: add(2, 3)\n"
            f"  - from any other language through RAD Hub: radcall(\"{name}.add\", 2, 3)\n"
            "Call other modules (any language) the same way: radcall(\"Helpers.greet\", \"Ann\")\n"
            "Arguments and results are JSON values (number, string, bool, null, array, object).")
        return f"{head}\n\nfunction add(a, b) {{\n    return a + b;\n}}\n"

    def short_name(self) -> str:
        return "JavaScript"

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(
            code, rf"^\s*(?:export\s+)?(?:function\s*\*?\s+|(?:const|let|var)\s+){re.escape(name)}\s*(?:\(|=|:|<)")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        if lines and lines[-1].strip():
            lines.append("")
        start = len(lines)
        lines += self.handler_stub(name)
        return "\n".join(lines) + "\n", start + 1

    def on_file_removed(self, code: str, filename: str) -> str:
        return code            # modules are loaded by _radmain, nothing references them

    # ------------------------------------------------------------ project / run
    def my_forms(self, project: Project) -> list[str]:
        langs = getattr(project, "form_languages", None) or {}
        mine = [f for f in project.forms if langs.get(f, project.language) == self.id]
        if not mine:           # e.g. a project run directly with this plugin
            mine = [f for f in project.forms if (project.folder / self.code_file(f)).exists()]
        return mine

    def code_files(self, project: Project) -> list[str]:
        skip = {self.main_file.lower(), *(t.lower() for t in self.client_files())}
        mods = [m for m in project.modules
                if m.lower().endswith(self.code_ext) and m.lower() not in skip]
        return mods + [self.code_file(f) for f in self.my_forms(project)]

    def client_files(self) -> dict[str, Path]:
        return {"radgui.js": JS_CLIENT / "radgui.js"}

    def main_source(self, project: Project):
        files = json.dumps(self.code_files(project))
        return self.main_file, (
            "// AUTO-GENERATED by RAD IDE - main program for the GUI Bridge (do not edit)\n"
            "'use strict';\n"
            "require('./radgui.js').runMain(\n"
            f"  {files},\n"
            "  __dirname);\n")

    def node(self) -> str:
        return self.tool() or "node"

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [self.node(), "--no-warnings", self.main_file]

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        return [self.node(), "--no-warnings", str(JS_CLIENT / "radworker.js"), module_file]

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        names = names or {}
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\bui\.(\w+)\.\w*$", before)
        if m:                                    # ui.txtA.|  -> properties and methods
            return self._members(names.get(m.group(1), ""))
        if re.search(r"\bui\.\w*$", before):     # ui.|       -> controls
            return [Completion(n, "control", t) for n, t in names.items()]
        if re.search(r"\.\w*$", before):
            return []
        m = re.search(r"\b(?:set|get|getNum|call)\s*\(\s*([\"'`])\w+\1\s*,\s*[\"'`]\w*$", before)
        if m:                                    # set("txtA", "|  -> properties / methods
            obj = re.search(r"\(\s*[\"'`](\w+)", before[m.start():]).group(1)
            return self._members(names.get(obj, ""))
        if re.search(r"[\"'`]\w*$", before):     # inside a string: control names
            return [Completion(n, "control", t) for n, t in names.items()]
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(k, "function", d) for k, d in API.items()]
        out += [Completion(b, "function") for b in self.builtins if b not in API]
        out += [Completion(n, "control", t) for n, t in names.items()]
        seen = {c.name for c in out}
        for w in re.findall(r"\b[A-Za-z_$][\w$]{2,}", code):
            if w not in seen:
                seen.add(w)
                out.append(Completion(w, "variable"))
        return out

    def _members(self, ctype: str) -> list[Completion]:
        out, seen = [], set()
        ct = CONTROL_TYPES.get(ctype)
        props = [p.name for p in ct.prop_defs()] if ct else []
        for p in props + EXTRA_PROPS + ["Caption"]:
            if p not in seen:
                seen.add(p)
                out.append(Completion(p, "property", ctype))
        out += [Completion(mt, "method", ctype) for mt in METHODS]
        return out

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        depth, i = 0, len(before) - 1
        while i >= 0:                            # find the open "(" of the current call
            ch = before[i]
            if ch == ")":
                depth += 1
            elif ch == "(":
                if depth == 0:
                    m = re.search(r"(\w+)\s*$", before[:i])
                    return API.get(m.group(1), "") if m else ""
                depth -= 1
            i -= 1
        return ""


PLUGIN = JavaScriptPlugin()
