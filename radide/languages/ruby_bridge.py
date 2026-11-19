"""Ruby language plugin (GUI Bridge). Client library: runtimes/clients/ruby/rad.rb."""
from __future__ import annotations

import re
from pathlib import Path

from ..model import Form, Project
from .base import Completion, PackageManager
from .scripting_common import CONTROL_METHODS, ScriptBridgePlugin, _property_names
from .scripting_refs import doc_above, header, is_public, make_export, proxy_params, split_params, valid_ident

API = {
    "Rad.set": "Rad.set(obj, prop, value) - set a property: Rad.set(\"lblOut\", \"Caption\", \"Hi\")",
    "Rad.get": "Rad.get(obj, prop) -> String - read a property: Rad.get(\"txtA\", \"Text\")",
    "Rad.get_num": "Rad.get_num(obj, prop) -> Numeric - read a property as a number",
    "Rad.call": "Rad.call(obj, method, *args) -> String - e.g. Rad.call(\"lstLog\", \"AddItem\", \"x\")",
    "Rad.msgbox": "Rad.msgbox(text) - message box",
    "Rad.input": "Rad.input(prompt) -> String - input box",
    "Rad.show": "Rad.show(form) - show a form",
    "Rad.hide": "Rad.hide(form) - hide a form",
    "Rad.quit": "Rad.quit - quit the program (also Rad.end)",
    "ui": "ui.<control>.<Prop> / ui.<control>.<Prop> = value / ui.<control>.<Method>(args)",
    "msgbox": "msgbox(text) - message box",
    "radcall": "radcall(\"Module.func\", *args) -> value - call a function of any project module (RAD Hub)",
}
MEMBERS = {k.split(".", 1)[1]: v for k, v in API.items() if k.startswith("Rad.")}
GEM_DIR = "vendor/gems"             # project gems (Tools > Manage Packages), see rad.rb


class RubyBridgePlugin(ScriptBridgePlugin):
    id = "ruby-bridge"
    display_name = "Ruby (GUI Bridge)"
    code_ext = ".rb"
    tool_names = ["ruby"]
    tool_hints = [rf"C:\Ruby{v}-x64\bin\ruby.exe" for v in ("40", "34", "33", "32", "31", "30")] + \
                 [r"C:\tools\ruby34\bin\ruby.exe", r"C:\tools\ruby33\bin\ruby.exe"]
    toolchain_bins = ["ruby/bin"]
    install_hint = ("Install Ruby (winget install RubyInstallerTeam.Ruby.3.4) and add it to PATH, or extract the "
                    "RubyInstaller 7z archive into %LOCALAPPDATA%\\RADIDE\\toolchains\\ruby.")
    handler_regex = r"^\s*def\s+(\w+_\w+)\b"
    client_subdir = "ruby"
    client_names = ["rad.rb", "radworker.rb"]
    worker_script = "radworker.rb"
    api = API
    case_sensitive = True
    line_comments = ["#"]
    block_comment = ("=begin", "=end")
    string_quotes = ['"', "'"]
    keywords = """alias and begin break case class def defined? do else elsif end ensure false for if in
        module next nil not or redo rescue retry return self super then true undef unless until when
        while yield require require_relative attr_accessor attr_reader attr_writer include extend
        private protected public module_function lambda proc raise loop""".split()
    builtins = ["puts", "print", "p", "format", "gets", "Rad", "ui", "radcall", "msgbox", "Integer", "Float",
                "String", "Array", "Hash"]
    @property
    def package_manager(self) -> PackageManager:
        """RubyGems installing into the project (vendor/gems, GEM_HOME relative to the project
        folder); rad.rb puts vendor/gems on the gem path of the program and of the RAD Hub workers."""
        gem = self.sibling_tool("gem")
        return PackageManager(
            name="RubyGems", tool=gem,
            # the project's gems only (`gem list` would add Ruby's ~50 default gems)
            list_cmd=[self.tool() or "ruby", "-e",
                      f"Dir.glob('{GEM_DIR}/specifications/*.gemspec').sort.each {{ |f| "
                      "s = Gem::Specification.load(f); puts s.name + ' (' + s.version.to_s + ')' if s }"],
            search_cmd=[gem, "search", "{query}"],
            install_cmd=[gem, "install", "{name}", "-v", "{version}", "--no-document"],
            uninstall_cmd=[gem, "uninstall", "-x", "-a", "{name}"],
            init_cmd=None, manifest="",
            search_url="https://rubygems.org/search?query={query}",
            env={"GEM_HOME": GEM_DIR, "GEM_PATH": GEM_DIR})

    # ------------------------------------------------------------ templates
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"# Event handlers for {n}. Methods named <Control>_<Event> run when the event happens.\n"
                f"# Rad.set / Rad.get / Rad.call (or ui.txtA.Text, ui.lblOut.Caption = \"x\") work with\n"
                f"# the controls; radcall(\"Module.func\", ...) calls other project modules (any language).\n\n"
                f"def {n}_Load(e)\n"
                f"  # runs when the form is shown\n"
                f"end\n")

    def module_template(self, name: str) -> str:
        return (f"# Module {name}. Use it from Ruby code with: require_relative \"{name}\"; {name}.hello(\"x\")\n"
                f"# Other languages call its functions through the RAD Hub: radcall(\"{name}.hello\", \"x\")\n"
                f"# (arguments and the result are JSON values: numbers, strings, arrays, hashes).\n"
                f"module {name}\n"
                f"  module_function\n\n"
                f"  def hello(who)\n"
                f"    \"Hello, #{{who}}\"\n"
                f"  end\n"
                f"end\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*def\s+{re.escape(name)}\b")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        lines += ["", f"def {name}(e)", "  ", "end"]
        return "\n".join(lines) + "\n", len(lines) - 2

    def on_file_removed(self, code: str, filename: str) -> str:
        stem = re.escape(Path(filename).stem)
        rx = re.compile(rf"^\s*(require_relative|require|load)\s*\(?\s*[\"'](\./)?{stem}(\.rb)?[\"'].*$")
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ build / run
    def main_source(self, project: Project):
        L = ["# AUTO-GENERATED by RAD IDE - main program for the GUI Bridge (do not edit)",
             "require_relative \"rad\""]
        for f in self.my_forms(project):
            L.append(f"Rad.load_file(\"{self.code_file(f)}\")")
        L += ["Rad.run", ""]
        return "_radmain.rb", "\n".join(L)

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [self.tool() or "ruby", "_radmain.rb"]

    # ------------------------------------------------------------ references (CONTRACTS 7)
    def exported_functions(self, path: Path, text: str, module: str | None = None,
                           const: str | None = None) -> list:
        """Public functions of a library file, as radworker.rb finds them: top-level ``def`` and
        the module methods of ``module <file stem>`` (``def self.x``, or plain ``def`` after
        ``module_function`` / ``extend self``). ``_private``, ``private`` ones and handlers are skipped."""
        stem = module or Path(path).stem
        consts = [const] if const else self._module_names(Path(path).stem)
        lines = text.splitlines()
        out, seen = [], set()
        in_mod, mod_funcs, private, body_indent, in_doc = False, False, False, None, False

        def add(name: str, params: str, i: int) -> None:
            if name in seen or not is_public(name):
                return
            seen.add(name)
            plist = [p.strip() for p in split_params(params or "")]
            plist = [p for p in plist if not p.startswith("&")]
            out.append(make_export(name, plist, stem, doc_above(lines, i, ("#",))))

        sig = r"def\s+{self}([A-Za-z_]\w*)(?:\s*\(([^)]*)\)|[ \t]+([^#;\n]*))?\s*(?:#.*|;.*|=.*)?$"
        for i, line in enumerate(lines):
            if in_doc:
                in_doc = not line.startswith("=end")
                continue
            if line.startswith("=begin"):
                in_doc = True
                continue
            if re.match(r"^__END__\s*$", line):
                break
            if not in_mod:
                m = re.match(rf"^module\s+(?:{'|'.join(map(re.escape, consts))})\s*(#.*)?$", line)
                if m:
                    in_mod, mod_funcs, private, body_indent = True, False, False, None
                    continue
                m = re.match("^" + sig.format(self=""), line)
                if m:
                    add(m.group(1), m.group(2) or m.group(3), i)
                continue
            if re.match(r"^end\b", line):
                in_mod = False
                continue
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if body_indent is None:
                body_indent = indent
            if indent != body_indent:
                continue
            s = line.strip()
            if re.fullmatch(r"(module_function|extend\s+self)\s*(#.*)?", s):
                mod_funcs, private = True, False
            elif re.fullmatch(r"(private|protected)\s*(#.*)?", s):
                private = True
            elif re.fullmatch(r"public\s*(#.*)?", s):
                private = False
            m = re.match(sig.format(self=r"self\."), s)
            if m:
                add(m.group(1), m.group(2) or m.group(3), i)
                continue
            m = re.match(sig.format(self=""), s)
            if m and mod_funcs and not private:
                add(m.group(1), m.group(2) or m.group(3), i)
        return out

    @staticmethod
    def _module_names(stem: str) -> list[str]:
        """Module constants radworker.rb tries for a file stem (math_lib -> MathLib)."""
        names = [stem, stem[:1].upper() + stem[1:], "".join(w.capitalize() for w in re.split(r"[_\W]+", stem) if w)]
        return list(dict.fromkeys(n for n in names if n))

    @staticmethod
    def _const(lib: str) -> str:
        c = re.sub(r"\W", "_", lib)
        if not c or not c[0].isalpha():
            c = "Lib" + c
        return c[0].upper() + c[1:]

    def reference_proxy(self, lib: str, functions: list) -> dict[str, str]:
        """``<lib>_ref.rb`` with ``module <Lib>``: ``require_relative "mathlib_ref"`` then
        ``MathLib.Add(2, 3)``. Every method forwards to Rad.radcall."""
        const = self._const(lib)
        fname = f"{re.sub(r'[^0-9a-z_]', '_', lib.lower())}_ref"
        L = [header(lib, "#").rstrip("\n"),
             f"# Use it from Ruby:  require_relative \"{fname}\"",
             f"#                    r = {const}.Name(args)",
             "require_relative \"rad\"", "",
             f"module {const}"]
        reserved = set(self.keywords) | {"args", "self", "nil", "true", "false", "__method__"}
        seen = set()
        for f in functions:
            if not valid_ident(f.name) or f.name in seen:
                continue
            seen.add(f.name)
            target = f"{f.module}.{f.name}".replace("\\", "\\\\").replace('"', '\\"')
            params, variadic = proxy_params(f.params, reserved)
            if f.doc:
                L.append(f"  # {f.doc}")
            if variadic:
                sig = ", ".join([f"{p} = nil" for p in params] + ["*rest"])
                args = f"[{', '.join(params)}]" + (" + rest" if params else "")
                if not params:
                    args = "rest"
            else:
                sig = ", ".join(f"{p} = nil" for p in params)
                args = f"[{', '.join(params)}]"
            L += [f"  def self.{f.name}({sig})",
                  f"    args = {args}",
                  "    args.pop while !args.empty? && args.last.nil?   # trailing nil arguments are not sent",
                  f"    Rad.radcall(\"{target}\", *args)",
                  "  end"]
        L += ["end", ""]
        return {f"{fname}.rb": "\n".join(L)}

    def example_function(self, name: str) -> str:
        """Source of a Class Library module *name* with example public functions."""
        const = self._const(name)
        return (f"# Class library {name}. Its module functions can be called from every project that\n"
                f"# references this library, in its own language, e.g.\n"
                f"#   Python: import {name}; {name}.Add(2, 3)     Ruby: require_relative \"{name.lower()}_ref\"\n"
                f"module {const}\n"
                f"  module_function\n\n"
                f"  # Add two numbers.\n"
                f"  def Add(a, b)\n"
                f"    a + b\n"
                f"  end\n\n"
                f"  # Greeting text for who.\n"
                f"  def Greet(who)\n"
                f"    \"Hello, #{{who}}!\"\n"
                f"  end\n"
                f"end\n")

    def _ref_libs(self, folder: Path) -> dict[str, list]:
        """module constant -> functions of the reference proxies (*_ref.rb) in *folder*."""
        libs: dict[str, list] = {}
        try:
            files = sorted(folder.glob("*_ref.rb"))
        except OSError:
            return libs
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "AUTO-GENERATED by RAD IDE (reference to" not in text:
                continue
            m = re.search(r"^module\s+(\w+)", text, re.M)
            if m:
                libs[m.group(1)] = self.exported_functions(f, text, m.group(1), m.group(1))
        return libs

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b([A-Z]\w*)(?:\.|::)(\w+)\s*\([^()]*$", before)
        if m and path is not None:
            for f in self._ref_libs(Path(path).parent).get(m.group(1), []):
                if f.name == m.group(2):
                    return f"{m.group(1)}.{f.name}({', '.join(f.params)})" + (f" - {f.doc}" if f.doc else "")
        return super().calltip(code, line, col, path, names)

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b([A-Z]\w*)\.\w*$", before)
        if m and m.group(1) != "Rad" and path is not None:
            funcs = self._ref_libs(Path(path).parent).get(m.group(1))
            if funcs:
                return [Completion(f.name, "function", f"{f.name}({', '.join(f.params)})"
                                   + (f" - {f.doc}" if f.doc else "")) for f in funcs]
        if re.search(r"\bRad\.\w*$", before):
            return [Completion(k, "method", v) for k, v in MEMBERS.items()]
        if re.search(r"\bui\.\w*$", before):
            return [Completion(n, "control", t) for n, t in (names or {}).items()]
        if re.search(r"\bui\.\w+\.\w*$", before):
            return [Completion(p, "property") for p in _property_names()] + \
                   [Completion(m, "method") for m in CONTROL_METHODS]
        if re.search(r"\be\.\w*$", before):
            return [Completion(k, "property") for k in ("X", "Y", "Button", "KeyCode", "KeyChar", "args")]
        return super().completions(code, line, col, path, names)


PLUGIN = RubyBridgePlugin()
