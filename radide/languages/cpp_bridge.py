"""C++ language plugin (GUI Bridge). Builds with g++ or Microsoft Visual C++ (cl.exe).

Same model as the C plugin (c_bridge.py): handlers ``void cmdGo_Click()`` in Form1.cpp,
generated ``_radmain.cpp``, client radgui.h/.c + the std::string layer radgui.hpp (namespace rad).
References: a library's public top-level functions (number / bool / text / std::string types) are
served to other languages; a C++ project referencing a library gets the header ``<Lib>.ref.hpp``
(namespace ``<Lib>``: ``double x = MathLib::Add(2, 3);``).
"""
from __future__ import annotations

import re

from ..model import Form
from . import native_refs as nr
from .base import Completion
from .c_bridge import C_CLIENT, HELPERS, CBridgePlugin

CPP_KEYWORDS = """alignas alignof auto bool break case catch char class const constexpr const_cast continue
    decltype default delete do double dynamic_cast else enum explicit export extern false float for friend
    goto if inline int long mutable namespace new noexcept nullptr operator private protected public
    register reinterpret_cast return short signed sizeof static static_assert static_cast struct switch
    template this throw true try typedef typeid typename union unsigned using virtual void volatile while
    include define ifdef ifndef endif std string vector map""".split()
CPP_HELPERS = {
    "rad::set": "rad::set(obj, prop, value)  - value: std::string, double or int",
    "rad::get": "std::string rad::get(obj, prop)", "rad::get_num": "double rad::get_num(obj, prop)",
    "rad::call": "std::string rad::call(obj, method, args = \"\")", "rad::msgbox": "rad::msgbox(text)",
    "rad::input": "std::string rad::input(prompt)", "rad::show": "rad::show(form)", "rad::hide": "rad::hide(form)",
    "rad::end": "rad::end()", "rad::print": "rad::print(text)", "rad::num": "double rad::num(text)",
    "rad::str": "std::string rad::str(double)", "rad::arg": "std::string rad::arg(i)  - event argument",
    "rad::hub": "std::string rad::hub(\"Module.func\", \"[json args]\")  - RAD Hub call",
    "rad::json": "std::string rad::json(text | double)  - value as JSON",
    "rad::json_num": "double rad::json_num(json)", "rad::json_str": "std::string rad::json_str(json)",
}


class CppBridgePlugin(CBridgePlugin):
    id = "cpp-bridge"
    display_name = "C++ (GUI Bridge, g++ / MSVC)"
    code_ext = ".cpp"
    main_name = "_radmain.cpp"
    gcc_names = ["g++"]
    msvc_flags = "/TP /std:c++17"
    std_flags = "-std=gnu++17 -x c++"
    keywords = CPP_KEYWORDS
    builtins = list(HELPERS) + [k.split("::")[1] for k in CPP_HELPERS] + ["cout", "endl", "to_string", "stod"]
    install_hint = ("Install g++ (MSYS2: pacman -S mingw-w64-ucrt-x86_64-gcc, or WinLibs into "
                    "%LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64) or Visual Studio with the C++ workload.")

    def client_files(self):
        files = super().client_files()
        files["radgui.hpp"] = C_CLIENT / "radgui.hpp"
        return files

    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"// Event handlers for {n}. The IDE draws the form; use rad::set / rad::get / rad::call\n"
                f"// to work with the controls (see radgui.hpp). Handlers: void <Control>_<Event>().\n"
                f"#include <string>\n#include \"radgui.hpp\"\n\n"
                f"void {n}_Load()\n{{\n    // runs when the form is shown\n}}\n")

    def module_template(self, name: str) -> str:
        return (f"// Module {name}.\n"
                f"// Functions written as RADFUNC(name) can be called from every language through RAD Hub:\n"
                f"//     Python: radcall(\"{name}.add\", 2, 3)      C++: rad::hub(\"{name}.add\", \"[2, 3]\")\n"
                f"// argv[i] is the JSON text of argument i; return JSON text (rad_json_numtext,\n"
                f"// rad_json_quote) or rad_fail(\"message\").\n"
                f"#include \"radgui.hpp\"\n\n"
                f"RADFUNC(add)\n{{\n"
                f"    if (argc < 2) return rad_fail(\"add needs 2 arguments\");\n"
                f"    return rad_json_numtext(rad::json_num(argv[0]) + rad::json_num(argv[1]));\n}}\n")

    # ------------------------------------------------------------ References (CONTRACTS 7)
    cpp = True

    def example_function(self, name: str) -> str:
        return ("// Add two numbers. Public (non-static, top-level) functions with number, bool or text\n"
                "// (std::string / const char *) parameters can be called by projects that reference this one.\n"
                "double Add(double a, double b)\n{\n    return a + b;\n}\n")

    def library_template(self, name: str) -> str:
        return (f"// Class library {name}.\n"
                f"// Every non-static top-level function is public: projects that reference {name} call it as\n"
                f"// code of their own language (Python: {name}.Add(2, 3), C++: {name}::Add(2, 3), ...).\n"
                f"// Supported types: int/long/double/float/bool, std::string, const char *, rad::Value.\n"
                f"#include <string>\n#include \"radgui.hpp\"\n\n" + self.example_function(name))

    def reference_proxy(self, lib: str, functions) -> dict[str, str]:
        return nr.cpp_reference_proxy(lib, functions)

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        lines += ["", f"void {name}()", "{", "    ", "}"]
        return "\n".join(lines) + "\n", len(lines) - 2

    def completions(self, code, line, col, path, names=None):
        out = super().completions(code, line, col, path, names)
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        if re.search(r"\brad::\w*$", before):
            return [Completion(k.split("::")[1], "function", d) for k, d in CPP_HELPERS.items()]
        return [Completion(k, "function", d) for k, d in CPP_HELPERS.items()] + out

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(rad::\w+)\s*\([^()]*$", before)
        if m:
            return CPP_HELPERS.get(m.group(1), "")
        return super().calltip(code, line, col, path, names)


PLUGIN = CppBridgePlugin()
