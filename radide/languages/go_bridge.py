"""Go language plugin (GUI Bridge). Client library: runtimes/clients/go/radlib.go.

All project files are in package main. The IDE generates radmain_gen.go (a map from
handler names to the handler functions) and builds the program with `go build`.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from ..model import Form, Project
from .base import Completion, PackageManager
from . import native_refs as nr
from .bridgebase import CLIENTS
from .scripting_common import ScriptBridgePlugin, error_worker

API = {
    "Set": "Set(obj, prop string, value any) - set a property: Set(\"lblOut\", \"Caption\", \"Hi\")",
    "Get": "Get(obj, prop string) string - read a property: Get(\"txtA\", \"Text\")",
    "GetNum": "GetNum(obj, prop string) float64 - read a property as a number",
    "Call": "Call(obj, method string, args ...any) string - e.g. Call(\"lstLog\", \"AddItem\", \"x\")",
    "MsgBox": "MsgBox(text any) string - message box",
    "Input": "Input(prompt any) string - input box",
    "Show": "Show(form string) - show a form",
    "Hide": "Hide(form string) - hide a form",
    "End": "End() - quit the program",
    "radcall": "radcall(\"Module.func\", args ...any) any - call a function of any project module "
               "(RAD Hub); panics on error",
    "radcallE": "radcallE(\"Module.func\", args ...any) (any, error) - radcall that returns the error",
    "RadEvent": "RadEvent{X, Y, Button, KeyCode int; KeyChar, Args string}",
}

# func name(params) - top-level functions only (no methods, no generics)
FUNC_RX = re.compile(r"^func\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", re.M)
EXE = "_radapp.exe" if os.name == "nt" else "_radapp"
WORKER_TEMPLATE = CLIENTS / "go" / "radworker_main.go.txt"


class GoBridgePlugin(ScriptBridgePlugin):
    id = "go-bridge"
    display_name = "Go (GUI Bridge)"
    code_ext = ".go"
    tool_names = ["go"]
    tool_hints = [r"C:\Program Files\Go\bin\go.exe", r"C:\Go\bin\go.exe",
                  str(Path.home() / "go/bin/go.exe"), str(Path.home() / "sdk/go/bin/go.exe")]
    toolchain_bins = ["go/bin"]
    install_hint = ("Install Go (winget install GoLang.Go) and add it to PATH, or extract the official zip "
                    "into %LOCALAPPDATA%\\RADIDE\\toolchains\\go.")
    handler_regex = r"^func\s+(\w+_\w+)\s*\("
    client_subdir = "go"
    client_names = ["radlib.go"]
    api = API
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'", "`"]
    keywords = """break case chan const continue default defer else fallthrough for func go goto if import
        interface map package range return select struct switch type var true false nil iota any bool
        byte rune int int8 int16 int32 int64 uint uint8 uint16 uint32 uint64 float32 float64 string
        error""".split()
    builtins = ["append", "cap", "close", "copy", "delete", "len", "make", "new", "panic", "print", "println",
                "recover", "min", "max", "clear", "fmt", "strconv", "strings", "os"] + list(API)
    quote_names = True
    _go_version: str | None = None

    @property
    def package_manager(self) -> PackageManager:
        go = self.tool() or "go"
        return PackageManager(
            name="Go modules", tool=go,
            # dependencies only ("path version"), not the project module itself
            list_cmd=[go, "list", "-m", "-f", "{{if not .Main}}{{.Path}} {{.Version}}{{end}}", "all"],
            search_cmd=None,
            install_cmd=[go, "get", "{name}@{version}"],
            uninstall_cmd=[go, "get", "{name}@none"],
            init_cmd=[go, "mod", "init", "radapp"], manifest="go.mod",
            search_url="https://pkg.go.dev/search?q={query}")

    # ------------------------------------------------------------ templates
    def generate_designer(self, form: Form, user_code: str) -> str:
        # every .go file in the folder is compiled: the designer file needs a package clause
        return super().generate_designer(form, user_code) + "\npackage main\n"

    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"// Event handlers for {n}. Functions named <Control>_<Event> run when the event happens.\n"
                f"// Set / Get / Call work with the controls; radcall(\"Module.func\", ...) calls other\n"
                f"// project modules (any language). All project files are in package main.\n"
                f"package main\n\n"
                f"func {n}_Load(e RadEvent) {{\n"
                f"\t// runs when the form is shown\n"
                f"}}\n")

    def module_template(self, name: str) -> str:
        return (f"// Module {name} (package main: its functions can be called directly from Go code).\n"
                f"// Other languages call its functions through the RAD Hub: radcall(\"{name}.hello\", \"x\")\n"
                f"// (arguments and the result are JSON values; a last error result becomes an error).\n"
                f"// From Go: r := radcall(\"Other.func\", 1, 2)  or  r, err := radcallE(...)\n"
                f"package main\n\n"
                f"func hello(who string) string {{\n"
                f"\treturn \"Hello, \" + who\n"
                f"}}\n")

    # ------------------------------------------------------------ References (CONTRACTS 7)
    def example_function(self, name: str) -> str:
        return ("// Add adds two numbers. Exported (Capitalized) functions can be called by every project\n"
                "// that references this one (arguments/results are converted with encoding/json).\n"
                "func Add(a, b float64) float64 {\n\treturn a + b\n}\n")

    def library_template(self, name: str) -> str:
        return (f"// Class library {name} (package main). Its exported (Capitalized) functions are public:\n"
                f"// projects that reference {name} call them as code of their own language\n"
                f"// (Python: {name}.Add(2, 3), Go: {name}.Add(2, 3), ...). A last error result becomes an error.\n"
                f"package main\n\n" + self.example_function(name))

    def exported_functions(self, path: Path, text: str):
        return nr.go_exports(Path(path), text)

    def reference_proxy(self, lib: str, functions) -> dict[str, str]:
        """<Lib>_ref.go (package main): ``<Lib>.Func(args...)`` and ``<Lib>_Func(args...)``."""
        return nr.go_reference_proxy(lib, functions)

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^func\s+{re.escape(name)}\s*\(")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        lines += ["", f"func {name}(e RadEvent) {{", "\t", "}"]
        return "\n".join(lines) + "\n", len(lines) - 2

    def on_file_removed(self, code: str, filename: str) -> str:
        return code                       # same package: nothing to remove

    # ------------------------------------------------------------ build / run
    def go_version(self) -> str:
        """"1.22"-style language version of the installed Go (for go.mod)."""
        if GoBridgePlugin._go_version is None:
            ver = "1.21"
            try:
                out = subprocess.run([self.tool(), "env", "GOVERSION"], capture_output=True, text=True,
                                     timeout=30).stdout
                m = re.search(r"go(\d+)\.(\d+)", out)
                if m:
                    ver = f"{m.group(1)}.{m.group(2)}"
            except (OSError, subprocess.SubprocessError):
                pass
            GoBridgePlugin._go_version = ver
        return GoBridgePlugin._go_version

    def _ensure_gomod(self, folder: Path) -> None:
        p = folder / "go.mod"
        if not p.exists():
            p.write_text(f"module radapp\n\ngo {self.go_version() if self.tool() else '1.21'}\n", encoding="utf-8")

    def handler_funcs(self, code: str) -> list[tuple[str, bool]]:
        """(name, takes_event) of the functions usable as event handlers."""
        out = []
        for m in FUNC_RX.finditer(code):
            name, params = m.group(1), m.group(2).strip()
            if "_" not in name:
                continue
            if not params:
                out.append((name, False))
            elif re.fullmatch(r"(\w+\s+)?RadEvent", params):
                out.append((name, True))
        return out

    def console_program(self, project: Project) -> bool:
        """Console application (Go lessons): no forms and a module with its own func main(). It is built
        without radlib.go / radmain_gen.go and runs as a plain console program (runtimes/bridge.py)."""
        if project.forms:
            return False
        for m in project.modules:
            p = Path(project.folder) / m
            if not m.lower().endswith(".go") or not p.exists():
                continue
            if re.search(r"^func\s+main\s*\(\s*\)", p.read_text(encoding="utf-8", errors="replace"), re.M):
                return True
        return False

    def main_source(self, project: Project):
        if self.console_program(project):
            return None
        entries, seen = [], set()
        for f in self.code_files(project):
            p = project.folder / f
            if not p.exists():
                continue
            for name, takes in self.handler_funcs(p.read_text(encoding="utf-8", errors="replace")):
                if name in seen:
                    continue
                seen.add(name)
                body = f"func(e RadEvent) {{ {name}(e) }}" if takes else f"func(RadEvent) {{ {name}() }}"
                entries.append(f"\t\"{name}\": {body},")
        L = ["// AUTO-GENERATED by RAD IDE - main program for the GUI Bridge (do not edit)",
             "package main", "", "var radHandlers = map[string]func(RadEvent){", *entries, "}", "",
             "func main() { radRun(radHandlers) }", ""]
        return "radmain_gen.go", "\n".join(L)

    def prepare(self, folder: Path, project: Project) -> None:
        if self.console_program(project):
            for name, src in [("radmain_gen.go", None), *self.client_files().items()]:
                p = Path(folder) / name                # GUI Bridge files would clash with the user's main
                try:
                    if p.exists() and (src is None or p.read_bytes() == src.read_bytes()):
                        p.unlink()
                except OSError:
                    pass
        else:
            super().prepare(folder, project)
        self._ensure_gomod(folder)

    def build_command(self, folder: Path, project: Project) -> str | None:
        return f'"{self.tool() or "go"}" build -o {EXE} .'

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [str(folder / EXE)]

    # ------------------------------------------------------------ worker
    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        folder = Path(folder)
        tool = self.tool()
        if not tool:
            return error_worker(f"{self.display_name}: Go was not found. {self.install_hint}")
        rel = self.module_rel(folder, module_file)
        src = folder / rel
        stem = Path(rel).stem
        try:
            code = src.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return error_worker(f"cannot read {rel}: {e}")
        funcs = [m.group(1) for m in FUNC_RX.finditer(code) if m.group(1) not in ("main", "init")]
        wdir = folder / "_radworker" / re.sub(r"\W", "_", stem)
        if wdir.exists():
            for old in wdir.glob("*.go"):
                old.unlink()
        wdir.mkdir(parents=True, exist_ok=True)
        # the module + the other non-form modules (same package) + the client library
        try:
            project = Project.load(folder)
            form_files = {self.code_file(f).lower() for f in project.forms} | \
                         {self.designer_file(f).lower() for f in project.forms}
        except (OSError, ValueError, KeyError):
            form_files = set()
        for p in folder.glob("*.go"):
            if p.name.lower() in form_files or p.name == "radmain_gen.go":
                continue
            shutil.copy2(p, wdir / p.name)
        shutil.copy2(CLIENTS / "go" / "radlib.go", wdir / "radlib.go")
        for extra in ("go.mod", "go.sum"):
            if (folder / extra).exists():
                shutil.copy2(folder / extra, wdir / extra)
        if not (wdir / "go.mod").exists():
            (wdir / "go.mod").write_text(f"module radapp\n\ngo {self.go_version()}\n", encoding="utf-8")
        entries = "".join(f"\t\"{n}\": {n},\n" for n in funcs)
        text = WORKER_TEMPLATE.read_text(encoding="utf-8").replace("__MODULE__", stem) \
                              .replace("__ENTRIES__", entries)
        (wdir / "radworker_main.go").write_text(text, encoding="utf-8")
        exe = wdir / ("radworker.exe" if os.name == "nt" else "radworker")
        try:
            r = subprocess.run([tool, "build", "-o", str(exe), "."], cwd=str(wdir), capture_output=True,
                               text=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as e:
            return error_worker(f"go build failed for {rel}: {e}")
        if r.returncode != 0:
            return error_worker(f"go build failed for {rel}: {(r.stdout + r.stderr).strip()[-1500:]}")
        return [str(exe)]

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        if re.search(r"\be\.\w*$", before):
            return [Completion(k, "property") for k in ("X", "Y", "Button", "KeyCode", "KeyChar", "Args")]
        return super().completions(code, line, col, path, names)


PLUGIN = GoBridgePlugin()
