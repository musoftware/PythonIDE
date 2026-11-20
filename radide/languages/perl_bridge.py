"""Perl language plugin (GUI Bridge). Client library: runtimes/clients/perl/RadGUI.pm."""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from ..model import Form, Project
from .base import Completion, PackageManager
from .scripting_common import ScriptBridgePlugin
from .scripting_refs import doc_above, header, is_public, make_export, valid_ident

API = {
    "rad_set": "rad_set($obj, $prop, $value) - set a property: rad_set('lblOut', 'Caption', 'Hi')",
    "rad_get": "rad_get($obj, $prop) -> text - read a property: rad_get('txtA', 'Text')",
    "rad_getnum": "rad_getnum($obj, $prop) -> number - read a property as a number",
    "rad_call": "rad_call($obj, $method, @args) -> text - e.g. rad_call('lstLog', 'AddItem', 'x')",
    "rad_msgbox": "rad_msgbox($text) - message box",
    "rad_input": "rad_input($prompt) -> text - input box",
    "rad_show": "rad_show($form) - show a form",
    "rad_hide": "rad_hide($form) - hide a form",
    "rad_end": "rad_end() - quit the program",
    "radcall": "radcall('Module.func', @args) -> value - call a function of any project module (RAD Hub)",
}

# installed (non-core) modules as "Name Version" lines
LIST_SCRIPT = r"""
if (eval { require ExtUtils::Installed; 1 }) {
    my $i = ExtUtils::Installed->new;
    for my $m (sort $i->modules) { next if $m eq 'Perl'; my $v = eval { $i->version($m) } // ''; print "$m $v\n"; }
} else {
    require File::Find; my %seen;
    for my $d (grep { m{site_perl|vendor_perl|local} && -d } @INC) {
        File::Find::find(sub { return unless /\.pm\z/; (my $m = $File::Find::name) =~ s{^\Q$d\E/?}{};
            $m =~ s{/}{::}g; $m =~ s{\.pm\z}{}; $seen{$m} = 1; }, $d);
    }
    print "$_\n" for sort keys %seen;
}
"""


def _beside(exe: str, name: str) -> str:
    """Executable *name* in the same folder as *exe* (perl.exe -> cpanm / cpan)."""
    if not exe or not Path(exe).is_absolute():
        return ""
    for ext in ("", ".bat", ".exe", ".cmd"):
        p = Path(exe).parent / f"{name}{ext}"
        if p.is_file():
            return str(p)
    return ""


class PerlBridgePlugin(ScriptBridgePlugin):
    id = "perl-bridge"
    display_name = "Perl (GUI Bridge)"
    code_ext = ".pl"
    tool_names = ["perl"]
    tool_hints = [r"C:\Strawberry\perl\bin\perl.exe", r"C:\Perl64\bin\perl.exe", r"C:\Perl\bin\perl.exe",
                  r"C:\Program Files\Git\usr\bin\perl.exe"]
    # portable Strawberry Perl in %LOCALAPPDATA%\RADIDE\toolchains\strawberry (Tools > Language Servers)
    toolchain_bins = ["strawberry/perl/bin"]
    install_hint = "Install Strawberry Perl (winget install StrawberryPerl.StrawberryPerl) or Git for Windows."
    handler_regex = r"^\s*sub\s+(\w+_\w+)\b"
    client_subdir = "perl"
    client_names = ["RadGUI.pm", "radworker.pl"]
    worker_script = "radworker.pl"
    api = API
    case_sensitive = True
    line_comments = ["#"]
    block_comment = None
    string_quotes = ['"', "'"]
    keywords = """my our local sub return if elsif else unless while until for foreach do last next redo
        use no require package strict warnings and or not eq ne lt gt le ge cmp x qw q qq undef defined
        exists delete scalar ref bless shift unshift push pop splice keys values each wantarray die eval
        print printf say sprintf open close chomp chop split join map grep sort reverse length substr
        index lc uc lcfirst ucfirst abs int sqrt sin cos exp log rand srand time localtime sleep""".split()
    builtins = list(API)

    @property
    def package_manager(self) -> PackageManager:
        """cpanm when installed (Strawberry Perl ships it), else the cpan shell that comes with perl."""
        perl = self.tool() or "perl"
        cpanm = shutil.which("cpanm") or _beside(perl, "cpanm")
        if cpanm or not _beside(perl, "cpan"):
            tool = cpanm or "cpanm"
            install, uninstall, name = [tool, "{name}@{version}"], [tool, "--uninstall", "--force", "{name}"], "CPAN (cpanm)"
        else:
            tool = _beside(perl, "cpan")
            install, uninstall, name = [perl, tool, "-T", "{name}"], None, "CPAN"
        return PackageManager(
            name=name, tool=tool,
            list_cmd=[perl, "-e", LIST_SCRIPT],
            search_cmd=None, install_cmd=install, uninstall_cmd=uninstall,
            init_cmd=None, manifest="cpanfile",
            search_url="https://metacpan.org/search?q={query}")

    # ------------------------------------------------------------ templates
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"# Event handlers for {n}. Subs named <Control>_<Event> run when the event happens.\n"
                f"# rad_set / rad_get / rad_call work with the controls, radcall('Module.func', ...)\n"
                f"# calls functions of other project modules (any language).\n"
                f"use strict;\n"
                f"use warnings;\n"
                f"use RadGUI;\n\n"
                f"sub {n}_Load {{\n"
                f"    my ($e) = @_;\n"
                f"    # runs when the form is shown\n"
                f"}}\n\n"
                f"1;\n")

    def module_template(self, name: str) -> str:
        return (f"# Module {name}. Use it from Perl code with: require './{name}.pl'; {name}::hello('x');\n"
                f"# Other languages call its subs through the RAD Hub: radcall(\"{name}.hello\", \"x\")\n"
                f"# (arguments and the result are JSON values: numbers, strings, arrays, hashes).\n"
                f"package {name};\n"
                f"use strict;\n"
                f"use warnings;\n\n"
                f"sub hello {{\n"
                f"    my ($who) = @_;\n"
                f"    return \"Hello, $who\";\n"
                f"}}\n\n"
                f"1;\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*sub\s+{re.escape(name)}\b")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        # insert before the final "1;" if there is one
        idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            s = lines[i].strip()
            if s == "1;":
                idx = i
                break
            if s and not s.startswith("#"):
                break
        stub = [f"sub {name} {{", "    my ($e) = @_;", "    ", "}", ""]
        if idx > 0 and lines[idx - 1].strip():
            stub.insert(0, "")
        lines[idx:idx] = stub
        cursor = idx + stub.index("    ")
        return "\n".join(lines) + "\n", cursor

    def on_file_removed(self, code: str, filename: str) -> str:
        rx = re.compile(rf"^\s*(require|do)\s*\(?\s*[\"'](\./)?{re.escape(filename)}[\"'].*$")
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ build / run
    def main_source(self, project: Project):
        L = ["# AUTO-GENERATED by RAD IDE - main program for the GUI Bridge (do not edit)",
             "use strict;", "use warnings;", "use FindBin;", "use lib $FindBin::Bin;", "use RadGUI;"]
        for f in self.my_forms(project):
            L.append(f"RadGUI::load_file('{self.code_file(f)}');")
        L += ["RadGUI::run();", ""]
        return "_radmain.pl", "\n".join(L)

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [self.tool() or "perl", "_radmain.pl"]

    # ------------------------------------------------------------ references (CONTRACTS 7)
    def exported_functions(self, path: Path, text: str, module: str | None = None,
                           packages: tuple[str, ...] | None = None) -> list:
        """Public subs of a library file: subs in ``package <file stem>`` or in main
        (where radworker.pl looks them up); ``_private`` subs and event handlers are skipped."""
        stem = module or Path(path).stem
        pkgs = packages or (stem, "main")
        lines = text.splitlines()
        pkg, pod, out, seen = "main", False, [], set()
        for i, line in enumerate(lines):
            if pod:
                pod = not line.startswith("=cut")
                continue
            if re.match(r"^=[a-zA-Z]", line):
                pod = True
                continue
            if re.match(r"^__(END|DATA)__\b", line):
                break
            m = re.match(r"^\s*package\s+([\w:]+)\s*[;{]", line)
            if m:
                pkg = m.group(1)
                continue
            m = re.match(r"^\s*sub\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*(?:\{|$)", line)
            if not m or pkg not in pkgs or m.group(1) in seen or not is_public(m.group(1)):
                continue
            name = m.group(1)
            seen.add(name)
            params = self._perl_params(m.group(2), lines, i)
            out.append(make_export(name, params, stem, doc_above(lines, i, ("#",))))
        return out

    @staticmethod
    def _perl_params(signature: str | None, lines: list[str], i: int) -> list[str]:
        if signature and re.search(r"[$@%]\w", signature):          # sub add($a, $b) {
            return re.findall(r"[$@%](\w+)", signature)        # names without sigils
        params: list[str] = []
        for j, line in enumerate(lines[i:i + 8]):
            if j and (re.match(r"^\s*sub\s", line) or line.startswith("}")):
                break
            m = re.search(r"\bmy\s*\(([^)]*)\)\s*=\s*@_", line)
            if m:
                return re.findall(r"[$@%](\w+)", m.group(1))
            params += re.findall(r"\bmy\s+[$@%](\w+)\s*=\s*shift\b", line)
            if j and line.strip().startswith("}"):
                break
        return params

    def reference_proxy(self, lib: str, functions: list) -> dict[str, str]:
        """``<Lib>Ref.pm`` with ``package <Lib>``: ``use MathLibRef; MathLib::Add(2, 3)`` or
        ``use MathLibRef qw(Add); Add(2, 3)``. Every sub forwards to RadGUI::radcall."""
        pkg = re.sub(r"\W", "_", lib)
        if pkg[:1].isdigit():
            pkg = "_" + pkg
        names: list[str] = []
        L = [header(lib, "#").rstrip("\n"),
             f"# Use it from Perl:  use {pkg}Ref;  my $r = {pkg}::Name(args);",
             f"#    or import subs: use {pkg}Ref qw(Name ...);   (':all' imports every sub)",
             f"package {pkg};", "use strict;", "use warnings;", "use RadGUI ();", ""]
        for f in functions:
            if not valid_ident(f.name) or f.name in names:
                continue
            names.append(f.name)
            if f.doc:
                L.append(f"# {f.doc}")
            L.append(f"# {f.name}({', '.join(f.params)})")
            target = f"{f.module}.{f.name}".replace("\\", "\\\\").replace("'", "\\'")
            L.append(f"sub {f.name} {{ return RadGUI::radcall('{target}', @_); }}")
            L.append("")
        L += [f"package {pkg}Ref;",
              f"our @NAMES = qw({' '.join(names)});",
              "sub import {",
              "    my $class = shift;",
              "    my $caller = caller;",
              "    no strict 'refs';",
              "    for my $name (map { $_ eq ':all' ? @NAMES : $_ } @_) {",
              f"        die \"{pkg} has no sub '$name'\\n\" unless defined &{{\"{pkg}::$name\"}};",
              f"        *{{\"${{caller}}::$name\"}} = \\&{{\"{pkg}::$name\"}};",
              "    }",
              "}", "", "1;", ""]
        return {f"{pkg}Ref.pm": "\n".join(L)}

    def example_function(self, name: str) -> str:
        """Source of a Class Library module *name* with example public subs."""
        return (f"# Class library {name}. Public subs (names not starting with _) can be called from\n"
                f"# every project that references this library, in its own language, e.g.\n"
                f"#   Python: import {name}; {name}.Add(2, 3)     Perl: use {name}Ref; {name}::Add(2, 3)\n"
                f"package {name};\n"
                f"use strict;\n"
                f"use warnings;\n\n"
                f"# Add two numbers.\n"
                f"sub Add {{\n"
                f"    my ($x, $y) = @_;\n"
                f"    return $x + $y;\n"
                f"}}\n\n"
                f"# Greeting text for who.\n"
                f"sub Greet {{\n"
                f"    my ($who) = @_;\n"
                f"    return \"Hello, $who!\";\n"
                f"}}\n\n"
                f"1;\n")

    def _ref_libs(self, folder: Path) -> dict[str, list]:
        """package name -> functions of the reference proxies (<Lib>Ref.pm) in *folder*."""
        libs: dict[str, list] = {}
        try:
            files = sorted(folder.glob("*Ref.pm"))
        except OSError:
            return libs
        for f in files:
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "AUTO-GENERATED by RAD IDE (reference to" not in text:
                continue
            m = re.search(r"^package\s+(\w+)\s*;", text, re.M)
            if m:
                libs[m.group(1)] = self.exported_functions(f, text, m.group(1), (m.group(1),))
        return libs

    def completions(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)::\w*$", before)
        if m and path is not None:
            funcs = self._ref_libs(Path(path).parent).get(m.group(1))
            if funcs:
                return [Completion(f.name, "function", f"{f.name}({', '.join(f.params)})"
                                   + (f" - {f.doc}" if f.doc else "")) for f in funcs]
        return super().completions(code, line, col, path, names)

    def calltip(self, code, line, col, path, names=None):
        lines = code.splitlines()
        before = lines[line][:col] if line < len(lines) else ""
        m = re.search(r"\b(\w+)::(\w+)\s*\([^()]*$", before)
        if m and path is not None:
            for f in self._ref_libs(Path(path).parent).get(m.group(1), []):
                if f.name == m.group(2):
                    return f"{m.group(1)}::{f.name}({', '.join(f.params)})" + (f" - {f.doc}" if f.doc else "")
        return super().calltip(code, line, col, path, names)


PLUGIN = PerlBridgePlugin()
