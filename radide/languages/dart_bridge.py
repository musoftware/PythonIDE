"""Dart language plugin (GUI Bridge). Client library: runtimes/clients/dart/radgui.dart."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from ..model import Form, Project
from .base import Completion, PackageManager
from .scripting_common import ScriptBridgePlugin, error_worker
from .scripting_refs import doc_above, header, is_public, make_export, proxy_params, split_params, valid_ident

API = {
    "Rad.set": "Rad.set(obj, prop, value) - set a property: Rad.set('lblOut', 'Caption', 'Hi')",
    "Rad.get": "Rad.get(obj, prop) -> String - read a property: Rad.get('txtA', 'Text')",
    "Rad.getNum": "Rad.getNum(obj, prop) -> num - read a property as a number",
    "Rad.call": "Rad.call(obj, method, [args]) -> String - e.g. Rad.call('lstLog', 'AddItem', ['x'])",
    "Rad.msgbox": "Rad.msgbox(text) - message box",
    "Rad.input": "Rad.input(prompt) -> String - input box",
    "Rad.show": "Rad.show(form) - show a form",
    "Rad.hide": "Rad.hide(form) - hide a form",
    "Rad.end": "Rad.end() - quit the program",
    "msgbox": "msgbox(text) - message box",
    "radcall": "await radcall('Module.func', [args]) -> value - call a function of any project module "
               "(RAD Hub); use it in an async handler",
    "RadEvent": "RadEvent e: e.x, e.y, e.button, e.keyCode, e.keyChar, e.args",
}
# API members offered after "Rad."
MEMBERS = {k.split(".", 1)[1]: v for k, v in API.items() if k.startswith("Rad.")}

RESERVED = {"if", "for", "while", "switch", "return", "catch", "main", "assert", "super", "this", "new",
            "import", "export", "part", "library", "class", "enum", "typedef", "extension", "mixin"}
# top-level function definitions (column 0) -> name, parameter text
FUNC_RX = re.compile(r"^(?!(?:import|export|part|library|class|enum|typedef|extension|mixin|abstract|final|"
                     r"const|var|late|static|external)\b)(?:[\w<>?,\[\] ]+?\s+)?([A-Za-z]\w*)\s*\(([^)]*)\)"
                     r"\s*(?:async\*?\s*|sync\*\s*)?(?:\{|=>)", re.M)

PUBSPEC = """name: radapp
description: RAD IDE project (GUI Bridge).
publish_to: none
environment:
  sdk: '>=3.0.0 <4.0.0'
"""


class DartBridgePlugin(ScriptBridgePlugin):
    id = "dart-bridge"
    display_name = "Dart (GUI Bridge)"
    code_ext = ".dart"
    tool_names = ["dart"]
    tool_hints = [r"C:\flutter\bin\dart.bat", r"C:\tools\dart-sdk\bin\dart.exe",
                  r"C:\Program Files\Dart\dart-sdk\bin\dart.exe"]
    install_hint = "Install the Dart SDK (winget install Google.DartSDK) or Flutter and add it to PATH."
    handler_regex = r"^(?:[\w<>?]+\s+)?(\w+_\w+)\s*\("
    client_subdir = "dart"
    client_names = ["radgui.dart", "radworker.dart"]
    api = API
    quote_names = False
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ["'", '"']
    keywords = """abstract as assert async await break case catch class const continue covariant default
        deferred do dynamic else enum export extends extension external factory false final finally for
        Function get hide if implements import in interface is late library mixin new null on operator
        part required rethrow return sealed set show static super switch sync this throw true try typedef
        var void when while with yield int double num String bool List Map Set Future Stream Object""".split()
    builtins = ["print", "Rad", "radcall", "msgbox", "RadEvent", "jsonEncode", "jsonDecode", "identical"]
    @property
    def package_manager(self) -> PackageManager:
        dart = self.tool() or "dart"
        return PackageManager(
            name="pub", tool=dart,
            list_cmd=[dart, "pub", "deps", "--style=compact"],
            search_cmd=None,
            install_cmd=[dart, "pub", "add", "{name}:{version}"],
            uninstall_cmd=[dart, "pub", "remove", "{name}"],
            init_cmd=[sys.executable, "-c",
                      "import pathlib; p = pathlib.Path('pubspec.yaml'); "
                      f"p.exists() or p.write_text({PUBSPEC!r})"],
            manifest="pubspec.yaml",
            search_url="https://pub.dev/packages?q={query}")

    # ------------------------------------------------------------ tool
    def tool(self) -> str:
        """The real dart.exe (Flutter's dart.bat would leave dart.exe running when killed)."""
        t = super().tool()
        if t.lower().endswith((".bat", ".cmd")):
            exe = Path(t).parent / "cache" / "dart-sdk" / "bin" / "dart.exe"
            if exe.exists():
                return str(exe)
        return t

    # ------------------------------------------------------------ templates
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"// Event handlers for {n}. Top-level functions named <Control>_<Event> run when the\n"
                f"// event happens. Rad.set / Rad.get / Rad.call work with the controls;\n"
                f"// await radcall('Module.func', [args]) calls other project modules (any language).\n"
                f"import 'radgui.dart';\n\n"
                f"void {n}_Load(RadEvent e) {{\n"
                f"  // runs when the form is shown\n"
                f"}}\n")

    def module_template(self, name: str) -> str:
        return (f"// Module {name}. Use it from Dart code with: import '{name}.dart';\n"
                f"// Other languages call its top-level functions through the RAD Hub:\n"
                f"//   radcall(\"{name}.hello\", \"x\")   (arguments and the result are JSON values)\n"
                f"// From Dart: final r = await radcall('Other.func', [1, 2]);  (import 'radgui.dart')\n\n"
                f"String hello(String who) => 'Hello, $who';\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^(?:[\w<>?]+\s+)?{re.escape(name)}\s*\(")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        stub = ["", f"void {name}(RadEvent e) {{", "  ", "}"]
        lines += stub
        return "\n".join(lines) + "\n", len(lines) - 2

    def on_file_removed(self, code: str, filename: str) -> str:
        rx = re.compile(rf"^\s*import\s+['\"]{re.escape(filename)}['\"].*$")
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ build / run
    @staticmethod
    def functions(code: str) -> list[tuple[str, str]]:
        """Top-level functions: (name, parameter text)."""
        return [(m.group(1), m.group(2)) for m in FUNC_RX.finditer(code)
                if m.group(1) not in RESERVED and not m.group(1).startswith("_")
                and not code[m.start():m.start() + 1].isspace()]     # class members are indented

    def main_source(self, project: Project):
        L = ["// AUTO-GENERATED by RAD IDE - main program for the GUI Bridge (do not edit)",
             "import 'radgui.dart';"]
        entries = []
        for i, f in enumerate(self.my_forms(project)):
            path = project.folder / self.code_file(f)
            if not path.exists():
                continue
            L.append(f"import '{self.code_file(f)}' as f{i};")
            code = path.read_text(encoding="utf-8", errors="replace")
            for name, params in self.functions(code):
                if not re.fullmatch(r"\w+_\w+", name):
                    continue
                call = f"f{i}.{name}()" if not params.strip() else f"f{i}.{name}(e)"
                entries.append(f"  '{name}': (e) => {call},")
        L += ["", "Future<void> main() => radRun(<String, RadHandler>{", *entries, "});", ""]
        return "_radmain.dart", "\n".join(L)

    def prepare(self, folder: Path, project: Project) -> None:
        super().prepare(folder, project)
        self._ensure_pubspec(folder)

    @staticmethod
    def _ensure_pubspec(folder: Path) -> None:
        p = folder / "pubspec.yaml"
        if not p.exists():
            p.write_text(PUBSPEC, encoding="utf-8")

    @staticmethod
    def _needs_pub_get(folder: Path) -> bool:
        spec = folder / "pubspec.yaml"
        if not spec.exists() or not re.search(r"^(dev_)?dependencies\s*:\s*\S|^(dev_)?dependencies\s*:\s*$\n\s+\S",
                                              spec.read_text(encoding="utf-8", errors="replace"), re.M):
            return False
        cfg = folder / ".dart_tool" / "package_config.json"
        return not cfg.exists() or cfg.stat().st_mtime < spec.stat().st_mtime

    def build_command(self, folder: Path, project: Project) -> str | None:
        if self._needs_pub_get(folder):
            return f'"{self.tool()}" pub get'
        return None

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [self.tool() or "dart", "_radmain.dart"]

    # ------------------------------------------------------------ worker
    def worker_argv(self, tool: str, folder: Path, module_rel: str) -> list[str]:
        path = folder / module_rel
        stem = Path(module_rel).stem
        try:
            code = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return error_worker(f"cannot read {module_rel}: {e}")
        funcs = self.functions(code)
        entries = "".join(f"  '{n}': m.{n},\n" for n, _ in funcs)
        safe = re.sub(r"\W", "_", stem)
        name = f"_radworker_{safe}.dart"
        (folder / name).write_text(
            "// AUTO-GENERATED by RAD IDE - RAD Hub worker (do not edit)\n"
            "import 'radworker.dart';\n"
            f"import '{Path(module_rel).as_posix()}' as m;\n\n"
            f"Future<void> main() => radServe('{stem}', <String, Function>{{\n{entries}}});\n",
            encoding="utf-8")
        self._ensure_pubspec(folder)
        if self._needs_pub_get(folder):
            subprocess.run([tool, "pub", "get"], cwd=str(folder), capture_output=True)
        return [tool, name]

    # ------------------------------------------------------------ references (CONTRACTS 7)
    def exported_functions(self, path: Path, text: str, module: str | None = None) -> list:
        """Public top-level functions of a library file (column 0, not starting with _,
        not main / event handlers) - what the generated RAD Hub worker serves.
        Only positional parameters are listed (the worker passes arguments by position)."""
        stem = module or Path(path).stem
        lines = text.splitlines()
        starts = [0]
        for ln in lines:
            starts.append(starts[-1] + len(ln) + 1)
        out, seen = [], set()
        for m in FUNC_RX.finditer(text):
            name = m.group(1)
            if text[m.start():m.start() + 1].isspace() or name in RESERVED or name in seen \
                    or not is_public(name):
                continue
            seen.add(name)
            i = max(k for k in range(len(starts)) if starts[k] <= m.start())
            head = text[m.start():m.start(1)].strip()
            kind = "sub" if re.fullmatch(r"(void|Future\s*<\s*void\s*>)", head) else "function"
            params = []
            for p in split_params(m.group(2).split("{", 1)[0].replace("[", "").replace("]", "")):
                ids = re.findall(r"[A-Za-z_$][\w$]*", p.split("=", 1)[0])
                if ids:
                    params.append(ids[-1])
            out.append(make_export(name, params, stem, doc_above(lines, i, ("///", "//")), kind))
        return out

    def reference_proxy(self, lib: str, functions: list) -> dict[str, str]:
        """``<lib>_ref.dart`` with one top-level function per library function:
        ``import 'mathlib_ref.dart' as MathLib;`` then ``await MathLib.Add(2, 3)``
        (calls go through the RAD Hub, so every proxy returns a Future)."""
        fname = f"{re.sub(r'[^0-9a-z_]', '_', lib.lower())}_ref.dart"
        prefix = re.sub(r"\W", "_", lib)
        L = [header(lib, "//").rstrip("\n"),
             f"// Use it from Dart:  import '{fname}' as {prefix};",
             f"//                    final r = await {prefix}.Name(args);   (in an async function)",
             "// ignore_for_file: non_constant_identifier_names, library_prefixes",
             "import 'radgui.dart' show radcall;",
             "",
             "Future<dynamic> _call(String name, List<Object?> args) {",
             "  while (args.isNotEmpty && args.last == null) {",
             "    args.removeLast(); // trailing null arguments are not sent",
             "  }",
             "  return radcall(name, args);",
             "}",
             ""]
        reserved = set(self.keywords) | {"args", "name"}
        seen = set()
        for f in functions:
            if not valid_ident(f.name) or f.name in seen or f.name == "main":
                continue
            seen.add(f.name)
            dname = f.name + "_" if f.name in self.keywords or f.name in RESERVED else f.name
            params, variadic = proxy_params(f.params, reserved)
            if variadic:
                params += [f"a{i}" for i in range(len(params) + 1, len(params) + 9)]
            target = f"{f.module}.{f.name}".replace("\\", "\\\\").replace("'", "\\'").replace("$", "\\$")
            sig = f"[{', '.join(f'Object? {p}' for p in params)}]" if params else ""
            if f.doc:
                L.append(f"/// {f.doc}")
            L.append(f"Future<dynamic> {dname}({sig}) => _call('{target}', [{', '.join(params)}]);")
        L.append("")
        return {fname: "\n".join(L)}

    def example_function(self, name: str) -> str:
        """Source of a Class Library module *name* with example public functions."""
        return (f"// Class library {name}. Its public top-level functions (names not starting with _)\n"
                f"// can be called from every project that references this library, in its own language:\n"
                f"//   Python: import {name}; {name}.Add(2, 3)\n"
                f"//   Dart:   import '{name.lower()}_ref.dart' as {name};  await {name}.Add(2, 3);\n\n"
                f"/// Add two numbers.\n"
                f"num Add(num a, num b) => a + b;\n\n"
                f"/// Greeting text for who.\n"
                f"String Greet(String who) => 'Hello, $who!';\n")

    def _ref_libs(self, folder: Path, code: str) -> dict[str, list]:
        """import prefix -> functions of the reference proxy it imports (``import 'x_ref.dart' as P``)."""
        libs: dict[str, list] = {}
        for file, prefix in re.findall(r"""^\s*import\s+['"]([^'"]+_ref\.dart)['"]\s+as\s+(\w+)""", code, re.M):
            p = folder / file
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            libs[prefix] = self.exported_functions(p, text)
        return libs

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)\.(\w+)\s*\([^()]*$", before)
        if m and path is not None:
            for f in self._ref_libs(Path(path).parent, code).get(m.group(1), []):
                if f.name.rstrip("_") == m.group(2).rstrip("_"):
                    return f"{m.group(1)}.{f.name}({', '.join(f.params)})" + (f" - {f.doc}" if f.doc else "")
        return super().calltip(code, line, col, path, names)

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)\.\w*$", before)
        if m and m.group(1) not in ("Rad", "e") and path is not None:
            funcs = self._ref_libs(Path(path).parent, code).get(m.group(1))
            if funcs:
                return [Completion(f.name, "function", f"{f.name}({', '.join(f.params)})"
                                   + (f" - {f.doc}" if f.doc else "")) for f in funcs]
        if re.search(r"\bRad\.\w*$", before):
            return [Completion(k, "method", v) for k, v in MEMBERS.items()]
        if re.search(r"\be\.\w*$", before):
            return [Completion(k, "property") for k in ("x", "y", "button", "keyCode", "keyChar", "args")]
        return super().completions(code, line, col, path, names)


PLUGIN = DartBridgePlugin()
