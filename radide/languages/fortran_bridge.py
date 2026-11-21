"""Fortran language plugin (GUI Bridge + gfortran).

Each form's code file (Form1.f90) is a module (``form1_code``) whose argument-less
subroutines ``<Control>_<Event>`` are event handlers. The IDE writes ``_radmain.f90``
(event loop + dispatch); runtimes/radgui.f90 is the helper module. radgui.c (the C
client) is linked as well: it gives Fortran ``radcall`` (RAD Hub over TCP, which
standard Fortran cannot do) and the worker loop.

Worker functions (called FROM other languages through RAD Hub) live in modules:
    function add(args) result(res)
      character(len=*), intent(in) :: args(:)     ! argument texts (strings decoded)
      character(len=:), allocatable :: res        ! JSON: rad_jnum(x), rad_jstr(s), 'null'
or are plain public module procedures with integer / real / real(8) / logical / character
arguments declared with ``::`` (``real(8) function add(a, b)``, subroutines too).
References: a Fortran project that references a library gets ``<Lib>_ref.f90`` (module
``<lib>_ref``: ``use mathlib_ref`` then ``x = MathLib_add_num(2d0, 3d0)``).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from ..model import Form, Project
from .base import Completion
from .bridgebase import CLIENTS, BridgeLanguagePlugin
from . import native_refs as nr
from .c_bridge import find_native

RADGUI = Path(__file__).resolve().parent.parent / "runtimes" / "radgui.f90"
EXE = ".exe" if os.name == "nt" else ""
MODDIR = "_build"
HELPERS = {
    "rad_set": "call rad_set(obj, prop, value)  - set a property (text)",
    "rad_get": "s = rad_get(obj, prop)  - read a property as text",
    "rad_call": "call rad_call(obj, method, arg)  - e.g. call rad_call('lstLog', 'AddItem', 'x')",
    "rad_callf": "s = rad_callf(obj, method, arg)  - call a method and get its result",
    "rad_msgbox": "call rad_msgbox(text)", "rad_input": "s = rad_input(prompt)",
    "rad_show": "call rad_show(form)", "rad_hide": "call rad_hide(form)",
    "rad_num": "x = rad_num(text)  - text to real(8)",
    "rad_str": "s = rad_str(x)  - real(8) to text", "rad_end": "call rad_end()  - quit the program",
    "rad_print": "call rad_print(text)  - line in the Output window",
    "rad_args": "event arguments as text (X Y Button KeyCode KeyChar)",
    "rad_arg": "s = rad_arg(i)  - event argument i (1 = X, 2 = Y, 3 = Button, 4 = KeyCode, 5 = KeyChar)",
    "radcall": "r = radcall('Module.func', '[json args]')  - RAD Hub call, JSON result text",
    "rad_error": "s = rad_error()  - why the last radcall failed",
    "rad_jnum": "s = rad_jnum(x)  - number as JSON", "rad_jstr": "s = rad_jstr(text)  - text as JSON string",
    "rad_jtext": "s = rad_jtext(json)  - JSON string to text",
}

SUB_RX = r"^[ \t]*subroutine[ \t]+(\w+_\w+)[ \t]*(?:\([ \t]*\))?[ \t]*(?:!.*)?$"
MODULE_RX = re.compile(r"^\s*module\s+(?!procedure\b)(\w+)\s*(?:!.*)?$", re.I | re.M)
USE_RX = re.compile(r"^\s*use\s*(?:,\s*\w+\s*::)?\s*(\w+)", re.I | re.M)


def _strip_comments(text: str) -> str:
    return re.sub(r"!.*", "", text)


class FortranBridgePlugin(BridgeLanguagePlugin):
    id = "fortran-bridge"
    display_name = "Fortran (GUI Bridge, gfortran)"
    code_ext = ".f90"
    tool_names = ["gfortran"]
    case_sensitive = False
    line_comments = ["!"]
    block_comment = None
    string_quotes = ['"', "'"]
    handler_regex = SUB_RX
    install_hint = ("Install gfortran (MSYS2: pacman -S mingw-w64-ucrt-x86_64-gcc-fortran, or WinLibs into "
                    "%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64) and add it to PATH.")
    keywords = """program end module use implicit none contains subroutine function call if then else
        elseif endif do while enddo select case default exit cycle return integer real double precision
        character logical complex parameter dimension allocatable allocate deallocate intent in out inout
        write read print format open close stop true false and or not len trim adjustl result type
        interface only pure elemental recursive save data allocated present""".split()
    builtins = list(HELPERS) + ["abs", "sqrt", "sin", "cos", "exp", "log", "mod", "int", "nint", "real",
                                "dble", "max", "min", "sum", "size", "index", "len_trim", "achar", "iachar"]

    def tool(self) -> str:
        return find_native(["gfortran"])

    def compiler(self) -> str:
        return self.tool()

    # ------------------------------------------------------------ code
    def module_name(self, form_name: str) -> str:
        return f"{form_name.lower()}_code"

    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"! Event handlers for {n}. Use rad_set / rad_get / rad_call to work with the controls.\n"
                f"! Handlers are subroutines without arguments named <Control>_<Event>.\n"
                f"module {self.module_name(n)}\n"
                f"  use radgui\n"
                f"  implicit none\n"
                f"contains\n\n"
                f"  subroutine {n}_Load()\n"
                f"    ! runs when the form is shown\n"
                f"  end subroutine {n}_Load\n\n"
                f"end module {self.module_name(n)}\n")

    def module_template(self, name: str) -> str:
        m = name.lower()
        return (f"! Module {name}: 'use {m}' in a form's module to call its procedures.\n"
                f"! Functions with one argument named args can be called from every language through RAD Hub:\n"
                f"!     Python: radcall(\"{name}.add\", 2, 3)      Fortran: r = radcall('{name}.add', '[2, 3]')\n"
                f"! args(i) is the text of argument i; return JSON text: rad_jnum(x), rad_jstr(s) or 'null'.\n"
                f"module {m}\n  use radgui\n  implicit none\ncontains\n\n"
                f"  function add(args) result(res)\n"
                f"    character(len=*), intent(in) :: args(:)\n"
                f"    character(len=:), allocatable :: res\n"
                f"    res = rad_jnum(rad_num(args(1)) + rad_num(args(2)))\n"
                f"  end function add\n\nend module {m}\n")

    # ------------------------------------------------------------ References (CONTRACTS 7)
    def example_function(self, name: str) -> str:
        return ("  ! Add two numbers. Public module procedures (functions and subroutines) with integer,\n"
                "  ! real, real(8), logical or character arguments can be called by every project that\n"
                "  ! references this one.\n"
                "  real(8) function add(a, b)\n"
                "    real(8), intent(in) :: a, b\n"
                "    add = a + b\n"
                "  end function add\n")

    def library_template(self, name: str) -> str:
        m = nr.ident(name.lower())
        return (f"! Class library {name}. Public procedures of module {m} can be called by the projects that\n"
                f"! reference {name} as code of their own language (Python: {name}.add(2, 3), ...).\n"
                f"! Use 'private :: name' (or a 'private' statement + 'public :: ...') to hide procedures.\n"
                f"module {m}\n  use radgui\n  implicit none\ncontains\n\n" + self.example_function(name) +
                f"\nend module {m}\n")

    def exported_functions(self, path: Path, text: str):
        return nr.fortran_exports(Path(path), text)

    def reference_proxy(self, lib: str, functions) -> dict[str, str]:
        return nr.fortran_reference_proxy(lib, functions)

    def proxy_sources(self, folder: Path, project: Project | None) -> list[str]:
        return nr.proxy_files(folder, project, ("_ref.f90",))

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*subroutine\s+{re.escape(name)}\b", re.I)

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        idx = next((i for i in range(len(lines) - 1, -1, -1)
                    if re.match(r"^\s*end\s+module\b", lines[i], re.I)), len(lines))
        stub = [f"  subroutine {name}()", "    ", f"  end subroutine {name}", ""]
        lines[idx:idx] = stub
        return "\n".join(lines) + "\n", idx + 1

    def on_file_removed(self, code, filename):
        stem = re.escape(Path(filename).stem)
        rx = re.compile(rf"^\s*use\s+{stem}\b", re.I)
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ project scanning
    def form_files(self, project: Project) -> list[str]:
        """Code files of the forms written in this language."""
        return [self.code_file(f) for f in project.forms
                if getattr(project, "form_language", lambda _f: project.language)(f) == self.id]

    def module_files(self, project: Project) -> list[str]:
        return [m for m in project.modules if m.lower().endswith((".f90", ".f95", ".f03", ".f08", ".f"))]

    @staticmethod
    def _read(folder: Path, f: str) -> str:
        p = folder / f
        return p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""

    def _scan_handlers(self, folder: Path, project: Project) -> list[tuple[str, str, str]]:
        """(handler, module name, file) for every handler subroutine of the forms."""
        out = []
        rx = re.compile(SUB_RX, re.I | re.M)
        for f in self.form_files(project):
            text = self._read(folder, f)
            mods = MODULE_RX.findall(_strip_comments(text))
            if not mods:
                continue
            for h in rx.findall(text):
                out.append((h, mods[0], f))
        return out

    def handlers_in_project(self, folder: Path, project: Project) -> list[str]:
        return [h for h, _, _ in self._scan_handlers(folder, project)]

    def ordered_sources(self, folder: Path, files: list[str]) -> list[str]:
        """Sort files so that a module is compiled before the files that use it."""
        defines, uses = {}, {}
        for f in files:
            text = _strip_comments(self._read(folder, f))
            for m in MODULE_RX.findall(text):
                defines[m.lower()] = f
            uses[f] = {u.lower() for u in USE_RX.findall(text)}
        out: list[str] = []
        state: dict[str, int] = {}

        def visit(f: str):
            if state.get(f) == 2:
                return
            if state.get(f) == 1:       # cycle: leave the order to the compiler
                return
            state[f] = 1
            for u in sorted(uses.get(f, ())):
                dep = defines.get(u)
                if dep and dep != f:
                    visit(dep)
            state[f] = 2
            out.append(f)
        for f in files:
            visit(f)
        return out

    def _needed_modules(self, folder: Path, project: Project, start: str) -> list[str]:
        mods = self.module_files(project)
        mods += [p for p in self.proxy_sources(folder, project) if p not in mods]
        if start not in mods:
            mods.append(start)
        defines, uses = {}, {}
        for f in mods:
            text = _strip_comments(self._read(folder, f))
            for m in MODULE_RX.findall(text):
                defines[m.lower()] = f
            uses[f] = {u.lower() for u in USE_RX.findall(text)}
        need, todo = set(), [start]
        while todo:
            f = todo.pop()
            if f in need:
                continue
            need.add(f)
            todo += [defines[u] for u in uses.get(f, ()) if u in defines]
        return self.ordered_sources(folder, [f for f in mods if f in need])

    # ------------------------------------------------------------ generated sources
    def client_files(self) -> dict[str, Path]:
        return {"radgui.f90": RADGUI, "radgui.c": CLIENTS / "c" / "radgui.c", "radgui.h": CLIENTS / "c" / "radgui.h"}

    def generate_designer(self, form: Form, user_code: str) -> str:
        return ("! AUTO-GENERATED by RAD IDE - " + form.name + " is drawn by the IDE (GUI Bridge); the event\n"
                "! dispatch is generated into _radmain.f90 when the program runs. Controls:\n" +
                "".join(f"!   {c.name}: {c.type}\n" for c in form.controls))

    _PROGRAM_RX = re.compile(r"^\s*program\s+\w+", re.I | re.M)

    def console_program(self, project: Project) -> bool:
        """Console application (Fortran lessons): no forms and a module with its own ``program``. It is
        compiled alone (no _radmain.f90) and runs as a plain console program (runtimes/bridge.py)."""
        if project.forms:
            return False
        return any(self._PROGRAM_RX.search(_strip_comments(self._read(Path(project.folder), m)))
                   for m in self.module_files(project))

    def main_source(self, project: Project):
        if self.console_program(project):
            return None
        handlers = self._scan_handlers(project.folder, project)
        L = ["! AUTO-GENERATED by RAD IDE - main program for the GUI Bridge (do not edit)", "program radmain",
             "  use radgui"]
        by_mod: dict[str, list[tuple[int, str]]] = {}
        for i, (h, mod, _f) in enumerate(handlers, 1):
            by_mod.setdefault(mod, []).append((i, h))
        for mod, items in by_mod.items():
            renames = ", ".join(f"rad_h{i} => {h}" for i, h in items)
            L.append(f"  use {mod}, only: {renames}")
        L += ["  implicit none", "  character(len=600) :: key",
              "  do while (rad_next_event())",
              "    key = rad_lower(trim(rad_obj) // '_' // trim(rad_ev))"]
        if handlers:
            L.append("    select case (trim(key))")
            seen = set()
            for i, (h, _m, _f) in enumerate(handlers, 1):
                if h.lower() in seen:
                    continue
                seen.add(h.lower())
                L += [f"    case ('{h.lower()}')", f"      call rad_h{i}()"]
            L.append("    end select")
        L += ["    call rad_done()", "  end do", "end program radmain", ""]
        return "_radmain.f90", "\n".join(L)

    def prepare(self, folder: Path, project: Project) -> None:
        (folder / MODDIR).mkdir(exist_ok=True)
        super().prepare(folder, project)

    def _compile_cmd(self, sources: list[str], exe: str) -> str:
        libs = " -lws2_32" if os.name == "nt" else ""
        return (f'"{self.tool()}" -O1 -J {MODDIR} -o {exe} ' + " ".join(f'"{s}"' for s in sources) +
                f' "radgui.c" -static{libs}')

    def build_command(self, folder: Path, project: Project) -> str | None:
        mods = self.module_files(project)
        mods += [p for p in self.proxy_sources(folder, project) if p not in mods]
        user = self.ordered_sources(folder, mods + self.form_files(project))
        if self.console_program(project):
            return f'"{self.tool()}" -O1 -J {MODDIR} -o _radapp{EXE} ' + " ".join(f'"{s}"' for s in user) + " -static"
        return self._compile_cmd(["radgui.f90"] + user + ["_radmain.f90"], "_radapp" + EXE)

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [str(folder / ("_radapp" + EXE))]

    def run_spec(self, folder, startup_form, interpreter):
        spec = super().run_spec(folder, startup_form, interpreter)
        tool = self.tool()
        if tool and spec.env is not None:
            spec.env["PATH"] = str(Path(tool).parent) + os.pathsep + spec.env.get("PATH", "")
        return spec

    # ------------------------------------------------------------ RAD Hub worker
    def worker_source(self, folder: Path, module_file: str) -> str:
        text = self._read(folder, module_file)
        mod, procs = nr.fortran_public(text)
        procs = [p for p in procs if nr.f_callable(p)]
        L = [f"! AUTO-GENERATED by RAD IDE - RAD Hub worker for {module_file} (do not edit)",
             "program radworker", "  use radgui"]
        if mod and procs:
            L.append(f"  use {mod}, only: " + ", &\n    ".join(f"rad_f{i} => {p.name}"
                                                        for i, p in enumerate(procs, 1)))
        L += ["  implicit none", "  character(len=:), allocatable :: func",
              "  character(len=RAD_LINE), allocatable :: args(:)",
              "  do while (rad_wk_next(func, args))", "    select case (rad_lower(func))"]
        seen = set()
        for i, p in enumerate(procs, 1):
            if p.name.lower() in seen:
                continue
            seen.add(p.name.lower())
            L += nr.fortran_worker_case(p, f"rad_f{i}")
        L += ["    case default", "      call rad_wk_fail('unknown function ' // func)", "    end select",
              "  end do", "end program radworker", ""]
        return "\n".join(L)

    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        folder = Path(folder)
        stem = Path(module_file).stem
        exe = folder / f"_radworker_{stem}{EXE}"
        err = ""
        if not self.tool():
            err = self.install_hint
        elif not (folder / module_file).exists():
            err = f"{module_file} not found"
        else:
            project = Project.load(folder)
            (folder / MODDIR).mkdir(exist_ok=True)
            for target, src in self.client_files().items():
                (folder / target).write_bytes(src.read_bytes())
            main = f"_radworker_{stem}.f90"
            text = self.worker_source(folder, module_file)
            if not (folder / main).exists() or (folder / main).read_text(encoding="utf-8") != text:
                (folder / main).write_text(text, encoding="utf-8")
            sources = ["radgui.f90"] + self._needed_modules(folder, project, module_file) + [main]
            newest = max((folder / s).stat().st_mtime for s in sources + ["radgui.c"])
            if exe.exists() and exe.stat().st_mtime >= newest:
                return [str(exe)]
            env = dict(os.environ, PATH=str(Path(self.tool()).parent) + os.pathsep + os.environ.get("PATH", ""))
            r = subprocess.run(self._compile_cmd(sources, exe.name), cwd=str(folder), shell=True,
                               capture_output=True, text=True, env=env)
            if r.returncode == 0 and exe.exists():
                return [str(exe)]
            err = (r.stdout + r.stderr).strip() or "gfortran failed"
        return [sys.executable, "-c", "import sys; sys.stderr.write(sys.argv[1] + '\\n'); sys.exit(1)",
                f"[{self.id}] worker build failed for {module_file}: {err[-1500:]}"]

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(h, "function", d) for h, d in HELPERS.items()]
        out += [Completion(f"'{n}'", "control", t) for n, t in (names or {}).items()]
        return out

    def calltip(self, code, line, col, path, names=None):
        before = code.splitlines()[line][:col] if line < len(code.splitlines()) else ""
        m = re.search(r"\b(rad\w*)\s*\([^()]*$", before, re.I)
        return HELPERS.get(m.group(1).lower(), "") if m else ""


PLUGIN = FortranBridgePlugin()
