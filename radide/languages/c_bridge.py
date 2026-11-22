"""C language plugin (GUI Bridge). Builds with gcc (MinGW / MSYS2 / WinLibs) or, when no
gcc is found, with Microsoft Visual C++ (cl.exe, found through vswhere).

Form code (Form1.c) holds handlers ``void cmdGo_Click(void)``; the IDE generates
``_radmain.c`` with the event loop + dispatch. Client: runtimes/clients/c/radgui.h/.c.
Modules (*.c without a form) export their non-static functions with simple types
(numbers, bool, char*) and ``RADFUNC(name)`` functions to other languages through RAD Hub:
``radcall("Helpers.add", 2, 3)``. References (docs/CONTRACTS.md 7): a C project that references
a library gets ``<Lib>.ref.h`` / ``<Lib>.ref.c`` (functions ``<Lib>_<func>``, compiled with the app).
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
from . import native_refs as nr

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
VS_INSTALLER = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / \
    "Microsoft Visual Studio" / "Installer"


def find_vcvars() -> str:
    """vcvars64.bat of the newest Visual Studio with the C++ tools, or ""."""
    if _VCVARS:
        return _VCVARS[0]
    found = ""
    if os.name == "nt":
        vswhere = VS_INSTALLER / "vswhere.exe"
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


SHELL = ["cmd", "/c"] if os.name == "nt" else ["sh", "-c"]


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
    std_flags = "-std=gnu11"
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"', "'"]
    keywords = C_KEYWORDS
    builtins = list(HELPERS) + C_BUILTINS
    handler_regex = r"^[ \t]*void[ \t]+(\w+_\w+)[ \t]*\([ \t]*(?:void)?[ \t]*\)"
    install_hint = ("Install gcc (MSYS2: pacman -S mingw-w64-ucrt-x86_64-gcc, or WinLibs into "
                    "%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64) or Visual Studio with the C++ workload.")
    # vcpkg in manifest mode: packages are recorded in vcpkg.json and installed into
    # vcpkg_installed/<triplet>; the build adds its include/lib folders (see _vcpkg_flags).
    # With gcc set VCPKG_DEFAULT_TRIPLET=x64-mingw-static; MSVC uses the default x64-windows.
    package_manager = PackageManager(
        name="vcpkg", tool="vcpkg",
        list_cmd=None, search_cmd=["vcpkg", "search", "{query}"],
        install_cmd=SHELL + ["vcpkg add port {name} && vcpkg install"], uninstall_cmd=None,
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

    # ------------------------------------------------------------ References (CONTRACTS 7)
    cpp = False

    def example_function(self, name: str) -> str:
        return ("/* Add two numbers. Public (non-static) functions with number, bool or text\n"
                " * (const char *) parameters can be called by every project that references this one. */\n"
                "double Add(double a, double b)\n{\n    return a + b;\n}\n")

    def library_template(self, name: str) -> str:
        return (f"/* Class library {name}.\n"
                f" * Every non-static function below is public: projects that reference {name} call it as\n"
                f" * code of their own language (Python: {name}.Add(2, 3), C: {name}_Add_num(2, 3), ...).\n"
                f" * Supported types: int/long/double/float/bool, const char * (text); static = private. */\n"
                f"#include \"radgui.h\"\n\n" + self.example_function(name))

    def exported_functions(self, path: Path, text: str):
        return nr.c_exports(Path(path), text, self.cpp)

    def reference_proxy(self, lib: str, functions) -> dict[str, str]:
        return nr.c_reference_proxy(lib, functions)

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
        """Code files of the forms written in this language."""
        return [self.code_file(f) for f in project.forms
                if getattr(project, "form_language", lambda _f: project.language)(f) == self.id]

    def module_files(self, project: Project) -> list[str]:
        return [m for m in project.modules if m.lower().endswith(self.code_ext)]

    def handlers_in_project(self, folder: Path, project: Project) -> list[str]:
        out: list[str] = []
        rx = re.compile(self.handler_regex, re.M)
        owners = self._event_owners(folder, project)
        for f in self.form_files(project):
            p = folder / f
            if p.exists():
                for h in rx.findall(p.read_text(encoding="utf-8", errors="replace")):
                    # only <Form|Control|MenuItem>_<Event>: a helper such as "void update_title()" or a C++
                    # member function "void memory_add()" is not an event handler (it would be declared and
                    # called by the generated main program and fail to link)
                    if h not in out and (owners is None or h.rsplit("_", 1)[0].lower() in owners):
                        out.append(h)
        return out

    @staticmethod
    def _event_owners(folder: Path, project: Project) -> set[str] | None:
        """Lower-case names of the forms, their controls and menu items (None = the forms cannot be read)."""
        from ..controls import menu_leaves
        names: set[str] = set()
        try:
            for name in project.forms:
                form = Form.load(Path(folder) / f"{name}.form")
                names.add(form.name.lower())
                names.add(name.lower())
                for c in form.controls:
                    names.add(c.name.lower())
                    if c.type in ("MenuStrip", "ToolStrip", "ContextMenuStrip"):
                        names.update(str(it.get("Name", "")).lower() for it in menu_leaves(c.props.get("Items", [])))
        except Exception:  # noqa: BLE001 - keep the old behaviour (every match) when a form is broken
            return None
        return names

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

    _USER_MAIN = re.compile(r"^\s*(?:int|auto|void)\s+main\s*\(", re.M)

    def console_program(self, project: Project) -> bool:
        """Console application: no form of this language and a module with its own main()
        (C/C++ lessons, Console template). It is compiled alone - no generated _radmain - and
        runs without the GUI Bridge protocol (radide/runtimes/bridge.py, console mode)."""
        if self.form_files(project):
            return False
        for m in self.module_files(project):
            try:
                text = (Path(project.folder) / m).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if self._USER_MAIN.search(text):
                return True
        return False

    def main_source(self, project: Project):
        if self.console_program(project):
            return None
        return self.main_name, self._main_text(self.handlers_in_project(project.folder, project))

    # ------------------------------------------------------------ build
    @staticmethod
    def vcpkg_triplets(folder: Path, kind: str) -> list[Path]:
        """vcpkg manifest-mode install folders (vcpkg_installed/<triplet>) usable by *kind*."""
        root = Path(folder) / "vcpkg_installed"
        if not root.is_dir():
            return []
        out = []
        for t in sorted(root.iterdir()):
            if not (t / "include").is_dir():
                continue
            mingw = "mingw" in t.name
            if (kind == "gcc") == mingw or os.name != "nt":
                out.append(t)
        return out

    def _vcpkg_flags(self, folder: Path | None, kind: str) -> tuple[str, str]:
        """Include/library flags for packages installed with vcpkg (manifest mode, vcpkg.json)."""
        if folder is None:
            return "", ""
        cflags, lflags = [], []
        for t in self.vcpkg_triplets(folder, kind):
            lib = t / "lib"
            if kind == "gcc":
                cflags.append(f"-I{q(str(t / 'include'))}")
                if lib.is_dir():
                    lflags.append(f"-L{q(str(lib))}")
                    lflags += [f"-l{a.stem[3:]}" for a in sorted(lib.glob("lib*.a"))]
            else:
                cflags.append(f"/I{q(str(t / 'include'))}")
                if lib.is_dir():
                    lflags.append(f"/LIBPATH:{q(str(lib))}")
                    lflags += [q(a.name) for a in sorted(lib.glob("*.lib"))]
        return " ".join(cflags), " ".join(lflags)

    def _compile_cmd(self, sources: list[str], exe: str, folder: Path | None = None) -> str | None:
        kind = self.compiler_kind()
        cflags, lflags = self._vcpkg_flags(folder, kind)
        srcs = " ".join(q(s) for s in sources)
        if kind == "gcc":
            return (f'{q(self.gcc())} {self.std_flags} -O1 {cflags} -o {q(exe)} {srcs} {lflags} -static -lm' +
                    (" -lws2_32" if os.name == "nt" else "")).replace("  ", " ")
        if kind == "msvc":
            vsi = VS_INSTALLER                  # vswhere.exe, used by vcvars64.bat
            link = f" /link {lflags}" if lflags else ""
            return (f'set "PATH={vsi};%PATH%" && call {q(find_vcvars())} >nul && '
                    f'cl /nologo /utf-8 /EHsc {self.msvc_flags} {cflags} /Fe:{q(exe)} {srcs}{link}').replace("  ", " ")
        return None

    def proxy_sources(self, folder: Path, project: Project | None) -> list[str]:
        """Generated reference proxies to compile (<Lib>.ref.c / .ref.cpp)."""
        return nr.proxy_files(folder, project, (".ref" + self.code_ext,))

    def build_command(self, folder: Path, project: Project) -> str | None:
        sources = ["radgui.c"] + self.module_files(project) + self.proxy_sources(folder, project) + \
            self.form_files(project) + ([] if self.console_program(project) else [self.main_name])
        return self._compile_cmd(sources, "_radapp" + EXE, folder)

    def _runtime_path(self, folder: Path, base: str) -> str:
        """PATH for running: toolchain bin (DLLs) + vcpkg bin folders."""
        dirs = [str(t / "bin") for t in self.vcpkg_triplets(folder, self.compiler_kind()) if (t / "bin").is_dir()]
        gcc = self.gcc()
        if gcc:
            dirs.append(str(Path(gcc).parent))
        return os.pathsep.join(dirs + [base])

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [str(folder / ("_radapp" + EXE))]

    def run_spec(self, folder, startup_form, interpreter):
        spec = super().run_spec(folder, startup_form, interpreter)
        if spec.env is not None:
            spec.env["PATH"] = self._runtime_path(Path(folder), spec.env.get("PATH", ""))
        return spec

    # ------------------------------------------------------------ RAD Hub worker
    def worker_source(self, module_file: str, funcs) -> str:
        """Worker main for *module_file*: *funcs* = CFunc list (or RADFUNC names)."""
        funcs = [nr.CFunc(f, "", radfunc=True) if isinstance(f, str) else f for f in funcs]
        L = ["/* AUTO-GENERATED by RAD IDE - RAD Hub worker for " + module_file + " (do not edit) */",
             "#include <stdbool.h>" if not self.cpp else "#include <string>",
             "#include <stddef.h>", "#include <stdint.h>", "#include <stdlib.h>", "#include <string.h>",
             '#include "radgui.h"' if not self.cpp else '#include "radgui.hpp"', ""]
        L += nr.C_WORKER_HELPERS
        decls, entry = nr.c_worker_wrappers(funcs, self.cpp)
        L += decls
        L += ["", "static const char *rad_wdispatch(const char *func, int argc, const char **argv, int *found)",
              "{", "    *found = 1;"]
        for name, fn in entry.items():
            L.append(f'    if (strcmp(func, "{name}") == 0) return {fn}(argc, argv);')
        L += ["    *found = 0;", "    (void)argc; (void)argv;", "    return 0;", "}", "",
              "int main(void) { (void)rad_x_bool; (void)rad_x_dup; (void)rad_x_keep; "
              "return rad_worker_main(rad_wdispatch); }", ""]
        return "\n".join(L)

    def _source_for(self, folder: Path, module_file: str) -> str:
        """A header module (lib.h) is served by its source file (lib.c / lib.cpp)."""
        if Path(module_file).suffix.lower() in (".h", ".hpp", ".hh", ".hxx"):
            for ext in (self.code_ext, ".c", ".cpp", ".cc"):
                cand = Path(module_file).with_suffix(ext).name
                if (folder / cand).exists():
                    return cand
        return module_file

    def build_worker(self, folder: Path, module_file: str) -> tuple[Path | None, str]:
        """Compile the worker of *module_file*; returns (exe, error text)."""
        folder = Path(folder)
        module_file = self._source_for(folder, module_file)
        src = folder / module_file
        stem = Path(module_file).stem
        if not src.exists():
            return None, f"{module_file} not found"
        text = src.read_text(encoding="utf-8", errors="replace")
        funcs = [f for f in nr.c_functions(text, self.cpp)
                 if f.radfunc or (nr.is_public_name(f.name) and f.name != "main" and nr.c_callable(f, self.cpp))]
        main = f"_radworker_{stem}{self.code_ext}"
        exe = folder / f"_radworker_{stem}{EXE}"
        for target, path in self.client_files().items():
            shutil.copy2(path, folder / target)
        wtext = self.worker_source(module_file, funcs)
        mp = folder / main
        if not mp.exists() or mp.read_text(encoding="utf-8") != wtext:
            mp.write_text(wtext, encoding="utf-8")
        # the other modules of the project (helpers of the library) + its reference proxies
        try:
            project = Project.load(folder)
            others = [m for m in self.module_files(project) if m != module_file and (folder / m).exists()]
            others += self.proxy_sources(folder, project)
        except (OSError, ValueError, KeyError):
            others = self.proxy_sources(folder, None)
        sources = ["radgui.c", module_file] + [o for o in others if o != module_file] + [main]
        newest = max((folder / f).stat().st_mtime for f in sources + ["radgui.h"] +
                     [h.name for h in folder.glob("*.h*") if h.is_file()])
        if exe.exists() and exe.stat().st_mtime >= newest:
            return exe, ""
        cmd = self._compile_cmd(sources, exe.name, folder)
        if cmd is None:
            return None, f"{self.display_name}: no compiler found. {self.install_hint}"
        env = dict(os.environ, PATH=self._runtime_path(folder, os.environ.get("PATH", "")))
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
