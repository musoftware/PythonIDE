"""TypeScript language plugin (GUI Bridge + Node.js).

Uses the JavaScript runtime (radgui.js): .ts files are turned into JavaScript in
memory with Node's built-in type stripper (``module.stripTypeScriptTypes``, Node 22.13+)
or, if that is missing, with the project's ``typescript`` npm package. No build step.
Files are scripts (no ``import``/``export`` between them): top-level functions are
shared by all files; use ``require("pkg")`` for npm packages.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..model import Form
from .base import PackageManager
from .javascript import JS_BUILTINS, JS_CLIENT, JS_KEYWORDS, JavaScriptPlugin, ident, safe_params, unique_functions

TS_KEYWORDS = JS_KEYWORDS + """interface type enum implements declare namespace module readonly public private
    protected abstract as is keyof any number string boolean unknown never object symbol bigint""".split()

TSCONFIG = """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "none",
    "strict": false,
    "noEmit": true,
    "allowJs": false,
    "types": []
  },
  "include": ["*.ts"]
}
"""


class TypeScriptPlugin(JavaScriptPlugin):
    id = "typescript"
    display_name = "TypeScript (GUI Bridge, Node.js)"
    code_ext = ".ts"
    install_hint = ("Install Node.js 22.13 or newer from https://nodejs.org (built-in TypeScript support), "
                    "or run 'npm install typescript' in the project folder.")
    keywords = TS_KEYWORDS
    builtins = JS_BUILTINS + ["RadEvent"]
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

    def short_name(self) -> str:
        return "TypeScript"

    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        head = self._comment(
            f"Event handlers for {n}. A handler is a function named <Control>_<Event>(e: RadEvent).\n"
            "Controls: get(\"txtA\", \"Text\"), set(\"lblOut\", \"Caption\", x), call(\"lstLog\", \"AddItem\", x)\n"
            "  or ui.txtA.Text, ui.lblOut.Caption = x, ui.lstLog.AddItem(x). Also msgbox, input, end.\n"
            "Other modules: radcall(\"Module.func\", ...args). npm packages: const m = require(\"name\").\n"
            "Types of the API: radgui.d.ts (copied into the project when it runs).")
        return (f"{head}\n\n"
                f"function {n}_Load(e: RadEvent): void {{\n"
                f"    // runs when the form is shown\n"
                f"}}\n")

    def handler_stub(self, name: str) -> list[str]:
        return [f"function {name}(e: RadEvent): void {{", "    ", "}"]

    def module_template(self, name: str) -> str:
        return super().module_template(name).replace(
            "function add(a, b) {", "function add(a: number, b: number): number {")

    # ------------------------------------------------------------ References (CONTRACTS 7.2)
    ref_ext = ".ref.ts"

    def example_function(self, name: str) -> str:
        return (super().example_function(name)
                .replace("function Add(a, b) {", "function Add(a: number, b: number): number {")
                .replace("function Greet(name) {", "function Greet(name: string): string {"))

    def reference_proxy(self, lib: str, functions) -> dict[str, str]:
        """<Lib>.ref.ts: a global object <Lib> with typed (any) methods, loaded automatically by
        the runtime (the project's .ts files are scripts sharing one global scope)."""
        name = ident(lib)
        functions = unique_functions(functions)
        lines = self._ref_header(lib, functions,
                                 f"{name}.{functions[0].name if functions else 'Func'}(...)    "
                                 "(this file is loaded automatically; no import needed)")
        lines += [f"var {name} = {{"]
        for f in functions:
            ps = safe_params(f.params, TS_KEYWORDS)
            if f.doc:
                lines.append(f"    /** {f.doc.replace('*/', '* /')} */")
            ret = "void" if f.kind == "sub" else "any"
            lines.append(f"    {f.name}({', '.join(p + ': any' for p in ps)}): {ret} {{")
            lines.append(f"        return (globalThis as any).radcall({json.dumps(f'{f.module}.{f.name}')}, "
                         "...Array.prototype.slice.call(arguments));")
            lines.append("    },")
        lines += ["};", f"(globalThis as any)[{json.dumps(name)}] = {name};", ""]
        return {f"{name}{self.ref_ext}": "\n".join(lines)}

    def client_files(self) -> dict[str, Path]:
        return {"radgui.js": JS_CLIENT / "radgui.js", "radgui.d.ts": JS_CLIENT / "radgui.d.ts"}

    def prepare(self, folder: Path, project) -> None:
        super().prepare(folder, project)
        cfg = folder / "tsconfig.json"
        if not cfg.exists():                 # lets editors / tsc --noEmit type-check the scripts
            cfg.write_text(TSCONFIG, encoding="utf-8")


PLUGIN = TypeScriptPlugin()
