"""C language plugin (GUI Bridge). Builds with gcc (MinGW / MSYS2 / WinLibs) or, when no
gcc is found, with Microsoft Visual C++ (cl.exe, found through vswhere).

Form code (Form1.c) holds handlers ``void cmdGo_Click(void)``; the IDE generates
``_radmain.c`` with the event loop + dispatch. Client: runtimes/clients/c/radgui.h/.c.
Modules (*.c without a form) can export ``RADFUNC(name)`` functions that other
languages call through RAD Hub: ``radcall("Helpers.add", 2, 3)``.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ..model import Form, Project
from .base import Completion, PackageManager
from .bridgebase import CLIENTS, BridgeLanguagePlugin

C_CLIENT = CLIENTS / "c"
EXE = ".exe" if os.name == "nt" else ""


def toolchain_bin_dirs() -> list[Path]:
    """Folders where RAD IDE looks for gcc/g++/gfortran besides PATH."""
    local = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE" / "toolchains"
    return [local / "mingw64" / "bin", local / "w64devkit" / "bin",
            Path(r"C:\msys64\ucrt64\bin"), Path(r"C:\msys64\mingw64\bin"), Path(r"C:\msys64\clang64\bin"),
            Path(r"C:\mingw64\bin"), Path(r"C:\MinGW\bin"), Path(r"C:\TDM-GCC-64\bin"),
            Path(r"C:\Strawberry\c\bin"), Path(r"C:\w64devkit\bin")]


def find_native(names: list[str]) -> str:
    for n in names:
        p = shutil.which(n)
        if p:
            return p
    for d in toolchain_bin_dirs():
        for n in names:
            p = d / (n + EXE)
            if p.exists():
                return str(p)
    return ""


_VCVARS: list[str] = []


def find_vcvars() -> str:
    """vcvars64.bat of the newest Visual Studio with the C++ tools, or ""."""
    if _VCVARS:
        return _VCVARS[0]
    found = ""
    if os.name == "nt":
        vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / \
            "Microsoft Visual Studio" / "Installer" / "vswhere.exe"
        if vswhere.exists():
            try:
                out = subprocess.run([str(vswhere), "-latest", "-products", "*", "-requires",
                                      "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property",
                                      "installationPath"], capture_output=True, text=True, timeout=20).stdout
                for line in out.splitlines():
                    bat = Path(line.strip()) / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
                    if line.strip() and bat.exists():
                        found = str(bat)
                        break
            except (OSError, subprocess.SubprocessError):
                pass
    _VCVARS.append(found)
    return found


def q(s: str) -> str:
    return f'"{s}"'


HELPERS = {
    "rad_set": "rad_set(obj, prop, value)  - set a property: rad_set(\"lblOut\", \"Caption\", \"Hi\")",
    "rad_set_num": "rad_set_num(obj, prop, double)",
    "rad_get": "const char *rad_get(obj, prop)  - read a property as text",
    "rad_get_num": "double rad_get_num(obj, prop)",
    "rad_call": "const char *rad_call(obj, method, args)  - e.g. rad_call(\"lstLog\", \"AddItem\", \"x\")",
    "rad_msgbox": "rad_msgbox(text)", "rad_input": "const char *rad_input(prompt)",
    "rad_show": "rad_show(form)", "rad_hide": "rad_hide(form)", "rad_end": "rad_end()  - quit the program",
    "rad_print": "rad_print(text)  - line in the Output window",
    "rad_num": "double rad_num(text)", "rad_str": "const char *rad_str(double)",
    "rad_arg": "const char *rad_arg(i)  - event argument i (X Y Button KeyCode KeyChar)",
    "radcall": "const char *radcall(\"Module.func\", \"[json args]\")  - JSON result text (RAD Hub)",
    "rad_error": "const char *rad_error()  - why the last radcall failed",
    "rad_json_num": "double rad_json_num(json)", "rad_json_str": "const char *rad_json_str(json)",
    "rad_json_quote": "const char *rad_json_quote(text)", "rad_json_numtext": "const char *rad_json_numtext(x)",
    "rad_fail": "return rad_fail(\"message\");  - error reply from a RADFUNC",
    "RADFUNC": "RADFUNC(name) { ... return json; }  - function callable from other languages",
}

C_KEYWORDS = """auto break case char const continue default do double else enum extern float for goto if
    inline int long register restrict return short signed sizeof static struct switch typedef union unsigned
    void volatile while _Bool bool true false NULL include define ifdef ifndef endif""".split()
C_BUILTINS = ["printf", "sprintf", "snprintf", "strlen", "strcpy", "strncpy", "strcmp", "strcat", "strchr",
              "strstr", "memcpy", "memset", "malloc", "calloc", "free", "atoi", "atof", "strtod", "abs", "fabs",
              "sqrt", "pow", "sin", "cos", "floor", "ceil", "rand", "srand", "time"]


class CBridgePlugin(BridgeLanguagePlugin):
    id = "c-bridge"
    display_name = "C (GUI Bridge, gcc / MSVC)"
    code_ext = ".c"
    main_name = "_radmain.c"
    gcc_names = ["gcc"]
    msvc_flags = "/TC"
    std_flags = "-std=c11"
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'"]
    keywords = C_KEYWORDS
    builtins = list(HELPERS) + C_BUILTINS
    handler_regex = r"^[ \t]*void[ \t]+(\w+_\w+)[ \t]*\([ \t]*(?:void)?[ \t]*\)"
    install_hint = ("Install gcc (MSYS2: pacman -S mingw-w64-ucrt-x86_64-gcc, or WinLibs into "
                    "%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64) or Visual Studio with the C++ workload.")
    package_manager = PackageManager(
        name="vcpkg", tool="vcpkg",
        list_cmd=["vcpkg", "list"], search_cmd=["vcpkg", "search", "{query}"],
        install_cmd=["vcpkg", "install", "{name}"], uninstall_cmd=["vcpkg", "remove", "{name}"],
        init_cmd=["vcpkg", "new", "--application"], manifest="vcpkg.json",
        search_url="https://vcpkg.io/en/packages?query={query}")

    # ------------------------------------------------------------ tools
    @property
    def tool_names(self) -> list[str]:          # type: ignore[override]
        return self.gcc_names

    def gcc(self) -> str:
        return find_native(self.gcc_names)

    def tool(self) -> str:
        return self.gcc() or find_vcvars()

    def compiler_kind(self) -> str:
        if self.gcc():
            return "gcc"
        return "msvc" if find_vcvars() else ""

    # ------------------------------------------------------------ code
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"/* Event handlers for {n}. The IDE draws the form; use rad_set / rad_get / rad_call\n"
                f" * to work with the controls (see radgui.h). Handlers: void <Control>_<Event>(void). */\n"
                f"#include \"radgui.h\"\n\n"
                f"void {n}_Load(void)\n{{\n    /* runs when the form is shown */\n}}\n")

    def module_template(self, name: str) -> str:
        return (f"/* Module {name}.\n"
                f" * Functions written as RADFUNC(name) can be called from every language through RAD Hub:\n"
                f" *     Python: radcall(\"{name}.add\", 2, 3)      C: radcall(\"{name}.add\", \"[2, 3]\")\n"
                f" * argv[i] is the JSON text of argument i; return JSON text (rad_json_numtext,\n"
                f" * rad_json_quote) or rad_fail(\"message\"). */\n"
                f"#include \"radgui.h\"\n\n"
                f"RADFUNC(add)\n{{\n"
                f"    if (argc < 2) return rad_fail(\"add needs 2 arguments\");\n"
                f"    return rad_json_numtext(rad_json_num(argv[0]) + rad_json_num(argv[1]));\n}}\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*void\s+{re.escape(name)}\s*\(")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        lines += ["", f"void {name}(void)", "{", "    ", "}"]
        return "\n".join(lines) + "\n", len(lines) - 2

    def on_file_removed(self, code, filename):
        stem = re.escape(Path(filename).stem)
        rx = re.compile(rf'^\s*#\s*include\s+"{stem}\.(h|hpp)"')
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ project scanning
    def form_files(self, project: Project) -> list[str]:
        return [self.code_file(f) for f in project.forms]

    def module_files(self, project: Project) -> list[str]:
        return [m for m in project.modules if m.lower().endswith(self.code_ext)]

    def handlers_in_project(self, folder: Path, project: Project) -> list[str]:
        out: list[str] = []
        rx = re.compile(self.handler_regex, re.M)
        for f in self.form_files(project):
            p = folder / f
            if p.exists():
                for h in rx.findall(p.read_text(encoding="utf-8", errors="replace")):
                    if h not in out:
                        out.append(h)
        return out

    @staticmethod
    def radfuncs(text: str) -> list[str]:
        return re.findall(r"^\s*RADFUNC\s*\(\s*(\w+)\s*\)", text, re.M)

    # ------------------------------------------------------------ generated sources
    def client_files(self) -> dict[str, Path]:
        return {"radgui.h": C_CLIENT / "radgui.h", "radgui.c": C_CLIENT / "radgui.c"}

    def _main_text(self, handlers: list[str]) -> str:
        L = ["/* AUTO-GENERATED by RAD IDE - GUI Bridge main program (do not edit) */",
             "#include <string.h>", '#include "radgui.h"', ""]
        L += [f"void {h}(void);" for h in handlers]
        L += ["", "static int rad_dispatch(const char *key)", "{"]
        for h in handlers:
            L.append(f'    if (strcmp(key, "{h}") == 0) {{ {h}(); return 1; }}')
        L += ["    (void)key;", "    return 0;", "}", "",
              "int main(void)", "{", "    char key[600];", "    rad_init();",
              "    while (rad_next_event()) {",
              "        if (rad_obj[0]) {",
              '            strcpy(key, rad_obj); strcat(key, "_"); strcat(key, rad_ev);',
              "            rad_dispatch(key);",
              "        }", "        rad_done();", "    }", "    return 0;", "}", ""]
        return "\n".join(L)

    def main_source(self, project: Project):
        return self.main_name, self._main_text(self.handlers_in_project(self._folder, project))

    def prepare(self, folder: Path, project: Project) -> None:
        self._folder = folder
        super().prepare(folder, project)

    # ------------------------------------------------------------ build
    def _compile_cmd(self, sources: list[str], exe: str) -> str | None:
        kind = self.compiler_kind()
        if kind == "gcc":
            return (f'{q(self.gcc())} {self.std_flags} -O1 -o {q(exe)} ' + " ".join(q(s) for s in sources) +
                    " -static -lm" + (" -lws2_32" if os.name == "nt" else ""))
        if kind == "msvc":
            return (f'call {q(find_vcvars())} >nul && cl /nologo /utf-8 /EHsc {self.msvc_flags} '
                    f'/Fe:{q(exe)} ' + " ".join(q(s) for s in sources) + " ws2_32.lib")
        return None

    def build_command(self, folder: Path, project: Project) -> str | None:
        sources = ["radgui.c"] + self.module_files(project) + self.form_files(project) + [self.main_name]
        return self._compile_cmd(sources, "_radapp" + EXE)

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [str(folder / ("_radapp" + EXE))]

    def run_spec(self, folder, startup_form, interpreter):
        spec = super().run_spec(folder, startup_form, interpreter)
        gcc = self.gcc()
        if gcc and spec.env is not None:        # DLLs of the toolchain (cc1, as, ld helpers)
            spec.env["PATH"] = str(Path(gcc).parent) + os.pathsep + spec.env.get("PATH", "")
        return spec

    # ------------------------------------------------------------ RAD Hub worker
    def worker_source(self, module_file: str, funcs: list[str]) -> str:
        L = ["/* AUTO-GENERATED by RAD IDE - RAD Hub worker for " + module_file + " (do not edit) */",
             "#include <string.h>", '#include "radgui.h"', ""]
        L += [f"RADFUNC({f});" for f in funcs]
        L += ["", "static const char *rad_wdispatch(const char *func, int argc, const char **argv, int *found)",
              "{", "    *found = 1;"]
        for f in funcs:
            L.append(f'    if (strcmp(func, "{f}") == 0) return {f}(argc, argv);')
        L += ["    *found = 0;", "    (void)argc; (void)argv;", "    return 0;", "}", "",
              "int main(void) { return rad_worker_main(rad_wdispatch); }", ""]
        return "\n".join(L)

    def build_worker(self, folder: Path, module_file: str) -> tuple[Path | None, str]:
        """Compile the worker of *module_file*; returns (exe, error text)."""
        folder = Path(folder)
        src = folder / module_file
        stem = Path(module_file).stem
        if not src.exists():
            return None, f"{module_file} not found"
        funcs = self.radfuncs(src.read_text(encoding="utf-8", errors="replace"))
        main = f"_radworker_{stem}{self.code_ext}"
        exe = folder / f"_radworker_{stem}{EXE}"
        for target, path in self.client_files().items():
            shutil.copy2(path, folder / target)
        text = self.worker_source(module_file, funcs)
        mp = folder / main
        if not mp.exists() or mp.read_text(encoding="utf-8") != text:
            mp.write_text(text, encoding="utf-8")
        newest = max((folder / f).stat().st_mtime for f in (module_file, main, "radgui.c", "radgui.h"))
        if exe.exists() and exe.stat().st_mtime >= newest:
            return exe, ""
        cmd = self._compile_cmd(["radgui.c", module_file, main], exe.name)
        if cmd is None:
            return None, f"{self.display_name}: no compiler found. {self.install_hint}"
        env = dict(os.environ)
        gcc = self.gcc()
        if gcc:
            env["PATH"] = str(Path(gcc).parent) + os.pathsep + env.get("PATH", "")
        r = subprocess.run(cmd, cwd=str(folder), shell=True, capture_output=True, text=True, env=env)
        if r.returncode != 0 or not exe.exists():
            return None, (r.stdout + r.stderr).strip() or "build failed"
        return exe, ""

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        exe, err = self.build_worker(Path(folder), module_file)
        if exe is None:
            return [sys.executable, "-c", "import sys; sys.stderr.write(sys.argv[1] + '\\n'); sys.exit(1)",
                    f"[{self.id}] worker build failed for {module_file}: {err[-1500:]}"]
        return [str(exe)]

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(h, "function", d) for h, d in HELPERS.items()]
        out += [Completion(b, "function") for b in C_BUILTINS]
        out += [Completion(f'"{n}"', "control", t) for n, t in (names or {}).items()]
        seen = {c.name for c in out}
        for w in re.findall(r"\b[A-Za-z_]\w{2,}\b", code):
            if w not in seen:
                seen.add(w)
                out.append(Completion(w, "variable"))
        return out

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(rad\w*|RADFUNC)\s*\([^()]*$", before)
        return HELPERS.get(m.group(1), "") if m else ""


PLUGIN = CBridgePlugin()
