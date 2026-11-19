"""Rust language plugin (GUI Bridge, cargo).

Form code (Form1.rs) holds handlers ``pub fn cmdGo_Click()``; modules (*.rs) are plain
Rust modules declared at the crate root (``crate::helpers::...``). The IDE writes
``_radmain.rs`` (event loop + dispatch) and keeps a ``Cargo.toml`` in the project folder
(its [[bin]] tables are managed by the IDE, everything else - [dependencies] added with
``cargo add`` - is yours). Build output goes to ``_build/``.

Worker functions (called from other languages through RAD Hub) are public functions of a
module that take ``&[Json]``:  ``pub fn add(args: &[Json]) -> f64 { args[0].as_f64() + ... }``
or plain typed functions (``pub fn add(a: f64, b: f64) -> f64``: numbers, bool, String/&str, Json,
Vec<..>). References: a Rust project that references a library gets ``<Lib>_ref.rs`` (declared as
``mod <Lib>`` in the generated main): ``use crate::MathLib; MathLib::add(2, 3).as_f64()``.
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
from . import native_refs as nr
from .bridgebase import CLIENTS, IDE_ROOT, BridgeLanguagePlugin

RUST_CLIENT = CLIENTS / "rust" / "radgui.rs"
EXE = ".exe" if os.name == "nt" else ""
TARGET = "_build"

HELPERS = {
    "set": "set(obj, prop, value)  - value: any Display (text, number)",
    "get": "get(obj, prop) -> String", "get_num": "get_num(obj, prop) -> f64",
    "call": "call(obj, method, &[\"arg\"]) -> String  - e.g. call(\"lstLog\", \"AddItem\", &[\"x\"])",
    "msgbox": "msgbox(text)", "input": "input(prompt) -> String", "show": "show(form)", "hide": "hide(form)",
    "end": "end()  - quit the program", "print": "print(text)  - line in the Output window",
    "num": "num(&str) -> f64", "str": "str(f64) -> String",
    "event_args": "event_args() -> String  - \"X Y Button KeyCode KeyChar\"",
    "event_arg": "event_arg(i) -> String", "radcall": "radcall(\"Module.func\", &[2.into(), \"x\".into()]) "
    "-> Result<Json, String>  (RAD Hub)",
    "Json": "enum Json { Null, Bool, Num, Str, Arr, Obj }  - .as_f64() .as_str() .get(key) .at(i)",
}
RUST_KEYWORDS = """as async await break const continue crate dyn else enum extern false fn for if impl in let loop
    match mod move mut pub ref return self Self static struct super trait true type unsafe use where while
    i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 usize f32 f64 bool char str String Vec Option Some None
    Result Ok Err Box""".split()
RUST_BUILTINS = ["println", "print", "format", "vec", "panic", "assert", "assert_eq", "to_string", "parse",
                 "unwrap", "unwrap_or", "expect", "push", "len", "iter", "map", "collect", "clone"]


def find_cargo() -> str:
    p = shutil.which("cargo")
    if p:
        return p
    for h in (Path.home() / ".cargo" / "bin" / ("cargo" + EXE),
              Path(os.environ.get("CARGO_HOME", str(Path.home() / ".cargo"))) / "bin" / ("cargo" + EXE)):
        if h.exists():
            return str(h)
    return ""


def crate_name(name: str) -> str:
    n = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "radapp"
    return n if n[0].isalpha() else "rad_" + n


def mod_name(file: str) -> str:
    n = re.sub(r"\W", "_", Path(file).stem.lower())
    return n if n and not n[0].isdigit() else "m_" + n


class RustBridgePlugin(BridgeLanguagePlugin):
    id = "rust-bridge"
    display_name = "Rust (GUI Bridge, cargo)"
    code_ext = ".rs"
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"']
    keywords = RUST_KEYWORDS
    builtins = list(HELPERS) + RUST_BUILTINS
    handler_regex = r"^[ \t]*pub[ \t]+fn[ \t]+(\w+_\w+)[ \t]*\([ \t]*\)"
    tool_names = ["cargo"]
    install_hint = "Install Rust from https://rustup.rs (cargo + rustc)."
    package_manager = PackageManager(
        name="cargo", tool="cargo",
        list_cmd=["cargo", "tree", "--depth", "1"], search_cmd=["cargo", "search", "{query}", "--limit", "20"],
        install_cmd=["cargo", "add", "{name}"], uninstall_cmd=["cargo", "remove", "{name}"],
        init_cmd=[sys.executable, "-c", f"import sys; sys.path.insert(0, {str(IDE_ROOT)!r}); "
                  "from radide.languages.rust_bridge import init_manifest; init_manifest('.')"],
        manifest="Cargo.toml", search_url="https://crates.io/search?q={query}")

    def tool(self) -> str:
        return find_cargo()

    # ------------------------------------------------------------ code
    def new_code(self, form: Form, is_startup: bool) -> str:
        n = form.name
        return (f"// Event handlers for {n}. The IDE draws the form; use set / get / call\n"
                f"// (module radgui) to work with the controls. Handlers: pub fn <Control>_<Event>().\n"
                f"use crate::radgui::*;\n\n"
                f"pub fn {n}_Load() {{\n    // runs when the form is shown\n}}\n")

    def module_template(self, name: str) -> str:
        m = mod_name(name)
        return (f"// Module {name} - use it from forms as crate::{m}::...\n"
                f"// Public functions taking (args: &[Json]) can be called from every language through RAD Hub:\n"
                f"//     Python: radcall(\"{name}.add\", 2, 3)      Rust: radcall(\"{name}.add\", &[2.into(), 3.into()])\n"
                f"// They may return Json, f64, i64, bool, String, () or Result<_, String>.\n"
                f"use crate::radgui::*;\n\n"
                f"pub fn add(args: &[Json]) -> f64 {{\n    args.iter().map(Json::as_f64).sum()\n}}\n")

    def find_handler(self, code: str, name: str) -> int:
        return self._find_line(code, rf"^\s*pub\s+fn\s+{re.escape(name)}\s*\(")

    def add_handler(self, code, name, form, args=None):
        lines = code.rstrip("\n").splitlines()
        lines += ["", f"pub fn {name}() {{", "    ", "}"]
        return "\n".join(lines) + "\n", len(lines) - 2

    def on_file_removed(self, code, filename):
        m = re.escape(mod_name(filename))
        rx = re.compile(rf"^\s*use\s+crate::{m}\b")
        return "\n".join(l for l in code.splitlines() if not rx.match(l)) + "\n"

    # ------------------------------------------------------------ project
    def form_files(self, project: Project) -> list[str]:
        """Code files of the forms written in this language."""
        return [self.code_file(f) for f in project.forms
                if getattr(project, "form_language", lambda _f: project.language)(f) == self.id]

    def module_files(self, project: Project) -> list[str]:
        return [m for m in project.modules if m.lower().endswith(".rs")]

    def handlers_in_project(self, folder: Path, project: Project) -> list[str]:
        out: list[tuple[str, str]] = []
        rx = re.compile(self.handler_regex, re.M)
        for f in self.form_files(project):
            p = folder / f
            if p.exists():
                for h in rx.findall(p.read_text(encoding="utf-8", errors="replace")):
                    out.append((h, f))
        self._handler_files = out
        return [h for h, _ in out]

    @staticmethod
    def worker_funcs(text: str) -> list:
        """Public functions the worker can call (RustFunc records, see native_refs)."""
        return [f for f in nr.rust_functions(text)
                if nr.is_public_name(f.name) and f.name != "main" and nr.rust_callable(f)]

    # ------------------------------------------------------------ References (CONTRACTS 7)
    def example_function(self, name: str) -> str:
        return ("/// Add two numbers. Public functions (pub fn) with number, bool, String/&str, Json or Vec\n"
                "/// parameters can be called by every project that references this one.\n"
                "pub fn add(a: f64, b: f64) -> f64 {\n    a + b\n}\n")

    def library_template(self, name: str) -> str:
        return (f"// Class library {name}.\n"
                f"// Every `pub fn` below is public: projects that reference {name} call it as code of their\n"
                f"// own language (Python: {name}.add(2, 3), Rust: {name}::add(2, 3), ...).\n"
                f"// Results may be numbers, bool, String, Json, Vec<..>, Option<..>, () or Result<_, String>.\n"
                f"#[allow(unused_imports)]\nuse crate::radgui::*;\n\n" + self.example_function(name))

    def exported_functions(self, path: Path, text: str):
        return nr.rust_exports(Path(path), text)

    def reference_proxy(self, lib: str, functions) -> dict[str, str]:
        return nr.rust_reference_proxy(lib, functions)

    def proxy_modules(self, folder: Path, project: Project | None) -> list[tuple[str, str]]:
        """(file, module name) of the generated reference proxies (<Lib>_ref.rs -> mod <Lib>)."""
        return [(f, Path(f).stem[:-4]) for f in nr.proxy_files(folder, project, ("_ref.rs",))]

    def _mods(self, project: Project) -> list[str]:
        L = ['#[path = "radgui.rs"]', "#[allow(dead_code)]", "mod radgui;"]
        for f in self.form_files(project) + self.module_files(project):
            if f in {p for p, _m in self.proxy_modules(project.folder, project)}:
                continue
            L += [f'#[path = "{f}"]', "#[allow(non_snake_case, dead_code, unused_imports, unused_variables)]",
                  f"mod {mod_name(f)};"]
        for f, m in self.proxy_modules(project.folder, project):
            L += [f'#[path = "{f}"]', "#[allow(non_snake_case, dead_code, unused_imports)]", f"mod {m};"]
        return L

    def main_source(self, project: Project):
        folder = project.folder
        self.handlers_in_project(folder, project)          # fills self._handler_files
        L = ["// AUTO-GENERATED by RAD IDE - GUI Bridge main program (do not edit)"] + self._mods(project)
        L += ["", "fn main() {", "    while let Some(key) = radgui::next_event() {", "        match key.as_str() {"]
        for h, f in self._handler_files:
            L.append(f'            "{h}" => {mod_name(f)}::{h}(),')
        L += ["            _ => {}", "        }", "        radgui::done();", "    }", "}", ""]
        return "_radmain.rs", "\n".join(L)

    def worker_source(self, project: Project, module_file: str, funcs: list) -> str:
        """*funcs*: RustFunc records (or names of legacy ``fn f(args: &[Json])`` functions)."""
        m = mod_name(module_file)
        L = [f"// AUTO-GENERATED by RAD IDE - RAD Hub worker for {module_file} (do not edit)"] + self._mods(project)
        L += ["", "#[allow(unused_imports)]", "use radgui::{Json, Reply};", "",
              "#[allow(unused_variables)]",
              "fn dispatch(func: &str, args: &[Json]) -> Option<Result<Json, String>> {",
              "    match func {"]
        for f in funcs:
            if isinstance(f, str):
                f = nr.RustFunc(f, [], "", legacy=True)
            L.append(nr.rust_dispatch_arm(f, m))
        L += ["        _ => { let _ = args; None }", "    }", "}", "",
              "fn main() {", "    radgui::worker_main(dispatch);", "}", ""]
        return "\n".join(L)

    def _worker_bin(self, module_file: str) -> str:
        return "radworker_" + mod_name(module_file)

    def write_cargo_toml(self, folder: Path, project: Project) -> None:
        path = folder / "Cargo.toml"
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        # split into tables; drop the [[bin]] tables (managed here)
        tables, cur = [], []
        for line in text.splitlines():
            if re.match(r"^\s*\[", line):
                tables.append(cur)
                cur = []
            cur.append(line)
        tables.append(cur)
        keep = [t for t in tables if t and not re.match(r"^\s*\[\[\s*bin\s*\]\]", t[0])]
        if not any(t and re.match(r"^\s*\[\s*package\s*\]", t[0]) for t in keep):
            keep.insert(0, ["[package]", f'name = "{crate_name(project.name)}"', 'version = "0.1.0"',
                            'edition = "2021"', "autobins = false", ""])
        if not any(t and re.match(r"^\s*\[\s*dependencies\s*\]", t[0]) for t in keep):
            keep.append(["[dependencies]", ""])
        bins = [("radapp", "_radmain.rs")] + [(self._worker_bin(m), f"_radworker_{mod_name(m)}.rs")
                                               for m in self.module_files(project)]
        out = []
        for t in keep:
            while t and not t[-1].strip():
                t = t[:-1]
            if t:
                out += t + [""]
        if not text:
            out.insert(0, "# Managed by RAD IDE: the [[bin]] tables are regenerated on every run; "
                          "edit [dependencies] freely (cargo add <crate>).")
        for name, src in bins:
            out += ["[[bin]]", f'name = "{name}"', f'path = "{src}"', ""]
        new = "\n".join(out).rstrip() + "\n"
        if new != text:
            path.write_text(new, encoding="utf-8")

    def prepare(self, folder: Path, project: Project) -> None:
        shutil.copy2(RUST_CLIENT, folder / "radgui.rs")
        name, text = self.main_source(project)
        self._write_if_changed(folder / name, text)
        for m in self.module_files(project):
            p = folder / m
            funcs = self.worker_funcs(p.read_text(encoding="utf-8", errors="replace")) if p.exists() else []
            self._write_if_changed(folder / f"_radworker_{mod_name(m)}.rs", self.worker_source(project, m, funcs))
        self.write_cargo_toml(folder, project)

    @staticmethod
    def _write_if_changed(path: Path, text: str) -> None:
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")

    def build_command(self, folder: Path, project: Project) -> str | None:
        return f'"{find_cargo()}" build --quiet --bin radapp --target-dir {TARGET}'

    def run_command(self, folder: Path, project: Project) -> list[str]:
        return [str(folder / TARGET / "debug" / ("radapp" + EXE))]

    # ------------------------------------------------------------ RAD Hub worker
    def worker_command(self, folder: Path, module_file: str) -> list[str] | None:
        folder = Path(folder)
        cargo = find_cargo()
        err = ""
        if not cargo:
            err = self.install_hint
        else:
            project = Project.load(folder)
            if module_file not in project.modules:
                project.modules.append(module_file)
            self.prepare(folder, project)
            r = subprocess.run([cargo, "build", "--quiet", "--bin", self._worker_bin(module_file),
                                "--target-dir", TARGET], cwd=str(folder), capture_output=True, text=True)
            exe = folder / TARGET / "debug" / (self._worker_bin(module_file) + EXE)
            if r.returncode == 0 and exe.exists():
                return [str(exe)]
            err = (r.stdout + r.stderr).strip() or "cargo build failed"
        return [sys.executable, "-c", "import sys; sys.stderr.write(sys.argv[1] + '\\n'); sys.exit(1)",
                f"[{self.id}] worker build failed for {module_file}: {err[-1500:]}"]

    # ------------------------------------------------------------ IntelliSense
    def completions(self, code, line, col, path, names=None):
        out = [Completion(k, "keyword") for k in self.keywords]
        out += [Completion(h, "function", d) for h, d in HELPERS.items()]
        out += [Completion(b, "function") for b in RUST_BUILTINS]
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
        m = re.search(r"\b(\w+)\s*\([^()]*$", before)
        return HELPERS.get(m.group(1), "") if m else ""


PLUGIN = RustBridgePlugin()


def init_manifest(folder: str | Path) -> None:
    """Create/refresh Cargo.toml (+ generated sources) so `cargo add` works before the first run."""
    folder = Path(folder).resolve()
    PLUGIN.prepare(folder, Project.load(folder))
