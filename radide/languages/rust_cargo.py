"""Rust (Cargo) - plain cargo projects created by File > New Project > Native > Rust (Cargo).

Templates: Console App, Library, GUI App (a RAD form: the Rust GUI Bridge plugin, rust_bridge.py),
egui Desktop App (eframe) and Workspace (an app + a library crate). The project folder is an ordinary cargo
project (Cargo.toml, src/, tests/, examples/ ...) plus project.radproj so it can live in a RAD solution next
to projects of other languages. Folders WITHOUT project.radproj (any cargo project or workspace on disk)
are opened in place by radide/foreign/cargo_project.py.

Run / debug go through the same CargoAdapter as the in-place projects: the startup object is a cargo target
("bin: hello", "example: demo", "test: all (hello)" ...), Ctrl+F5 = cargo run, F5 = GNU-target build + gdb.
IntelliSense is rust-analyzer (radide/lsp.py); the plugin's own completions are only a fallback.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from ..model import Project
from .base import Completion, LanguagePlugin, PackageManager, RunSpec
from .rust_bridge import RUST_BUILTINS, RUST_KEYWORDS, crate_name

EGUI_VERSION = "0.31"

GITIGNORE = "/target\n"

CONSOLE_MAIN = '''//! {name} - a Rust console application.
//! F5 debugs (breakpoints, locals), Ctrl+F5 runs (cargo run). Output appears in the Output window.

use std::collections::HashMap;

fn main() {{
    println!("Hello from {name}!");
    let mut counts: HashMap<&str, i32> = HashMap::new();
    for word in "the quick brown fox jumps over the lazy dog the end".split_whitespace() {{
        *counts.entry(word).or_insert(0) += 1;
    }}
    let mut words: Vec<_> = counts.into_iter().collect();
    words.sort_by(|a, b| b.1.cmp(&a.1).then(a.0.cmp(b.0)));
    for (word, n) in words.iter().take(3) {{
        println!("{{word}}: {{n}}");
    }}
}}
'''

LIB_RS = '''//! {name} - a Rust library crate.
//! Run the tests with Test > Test Explorer, or choose "test: all ({crate})" and press Ctrl+F5.

/// Adds two numbers.
///
/// ```
/// assert_eq!({crate}::add(2, 3), 5);
/// ```
pub fn add(a: i64, b: i64) -> i64 {{
    a + b
}}

/// A simple 2D point.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Point {{
    pub x: f64,
    pub y: f64,
}}

impl Point {{
    /// Creates a point.
    pub fn new(x: f64, y: f64) -> Self {{
        Self {{ x, y }}
    }}

    /// Distance to another point.
    pub fn distance(&self, other: &Point) -> f64 {{
        ((self.x - other.x).powi(2) + (self.y - other.y).powi(2)).sqrt()
    }}
}}

#[cfg(test)]
mod tests {{
    use super::*;

    #[test]
    fn adds() {{
        assert_eq!(add(2, 2), 4);
    }}

    #[test]
    fn distance() {{
        assert_eq!(Point::new(0.0, 0.0).distance(&Point::new(3.0, 4.0)), 5.0);
    }}
}}
'''

LIB_EXAMPLE = '''//! cargo run --example demo
fn main() {{
    let p = {crate}::Point::new(1.0, 2.0);
    println!("{{p:?}} -> 2 + 3 = {{}}", {crate}::add(2, 3));
}}
'''

EGUI_MAIN = '''//! {name} - an egui desktop application (eframe {ver}).
//! The first build downloads and compiles eframe (a few minutes); later builds are quick.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]   // no console window in release builds

use eframe::egui;

fn main() -> eframe::Result {{
    let options = eframe::NativeOptions {{
        viewport: egui::ViewportBuilder::default().with_inner_size([420.0, 320.0]).with_title("{name}"),
        ..Default::default()
    }};
    eframe::run_native("{name}", options, Box::new(|_cc| Ok(Box::new(App::default()))))
}}

struct App {{
    name: String,
    age: u32,
    items: Vec<String>,
}}

impl Default for App {{
    fn default() -> Self {{
        Self {{ name: "World".to_owned(), age: 30, items: Vec::new() }}
    }}
}}

impl eframe::App for App {{
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {{
        egui::CentralPanel::default().show(ctx, |ui| {{
            ui.heading("{name}");
            ui.horizontal(|ui| {{
                ui.label("Your name: ");
                ui.text_edit_singleline(&mut self.name);
            }});
            ui.add(egui::Slider::new(&mut self.age, 0..=120).text("age"));
            if ui.button("Add to list").clicked() {{
                self.items.push(format!("{{}} ({{}})", self.name, self.age));
            }}
            ui.label(format!("Hello '{{}}', age {{}}", self.name, self.age));
            ui.separator();
            egui::ScrollArea::vertical().show(ui, |ui| {{
                for item in &self.items {{
                    ui.label(item);
                }}
            }});
        }});
    }}
}}
'''

WS_APP_MAIN = '''//! The application crate of the {name} workspace: uses the `core` library crate.
use {core}::{{greet, Stats}};

fn main() {{
    println!("{{}}", greet("workspace"));
    let stats = Stats::from_values(&[3.0, 1.0, 4.0, 1.0, 5.0, 9.0]);
    println!("mean = {{:.2}}, max = {{}}", stats.mean, stats.max);
}}
'''

WS_CORE_LIB = '''//! The library crate of the {name} workspace.

/// A greeting.
pub fn greet(who: &str) -> String {{
    format!("Hello, {{who}}!")
}}

/// Summary statistics of a list of numbers.
#[derive(Debug, Default, PartialEq)]
pub struct Stats {{
    pub count: usize,
    pub mean: f64,
    pub max: f64,
}}

impl Stats {{
    /// Computes the statistics (an empty slice gives the default value).
    pub fn from_values(values: &[f64]) -> Self {{
        if values.is_empty() {{
            return Self::default();
        }}
        let sum: f64 = values.iter().sum();
        let max = values.iter().cloned().fold(f64::MIN, f64::max);
        Self {{ count: values.len(), mean: sum / values.len() as f64, max }}
    }}
}}

#[cfg(test)]
mod tests {{
    use super::*;

    #[test]
    fn greets() {{
        assert_eq!(greet("x"), "Hello, x!");
    }}

    #[test]
    fn stats() {{
        let s = Stats::from_values(&[1.0, 2.0, 3.0]);
        assert_eq!(s.count, 3);
        assert_eq!(s.mean, 2.0);
        assert_eq!(s.max, 3.0);
    }}
}}
'''

TEMPLATES = [
    ("rust_console", "Console App", "A cargo binary crate (src/main.rs). Ctrl+F5 = cargo run, F5 = debug with "
     "breakpoints and locals (gdb). rust-analyzer gives completion, hover docs, F2 rename and quick fixes.",
     "SP_ComputerIcon"),
    ("rust_library", "Library", "A cargo library crate (src/lib.rs) with unit tests, a doc test and an example "
     "(examples/demo.rs). Tests run in the Test Explorer.", "SP_FileDialogContentsView"),
    ("rust_gui", "GUI App (RAD form)", "A Windows Forms-style application: design the form, double-click a "
     "control and write the event handler in Rust (the Rust GUI Bridge).", "SP_TitleBarNormalButton"),
    ("rust_egui", "egui Desktop App", f"A native desktop app with egui / eframe {EGUI_VERSION}: text box, slider, "
     "button and a list. The first build downloads eframe.", "SP_DesktopIcon"),
    ("rust_workspace", "Workspace", "A cargo workspace with two crates: app (binary) using core (library with "
     "tests). Both open as one project; pick the target in the Rust target box.", "SP_DirIcon"),
]


def _cargo_toml(name: str, extra_deps: str = "", lib: bool = False) -> str:
    return (f'[package]\nname = "{crate_name(name)}"\nversion = "0.1.0"\nedition = "2021"\n\n'
            f"[dependencies]\n{extra_deps}")


def _readme(name: str, what: str) -> str:
    return (f"# {name}\n\n{what}\n\n* Ctrl+F5: run (cargo run)\n* F5: debug (breakpoints, locals - gdb on the GNU "
            "target)\n* Ctrl+Space / hover / F12 / F2 / Ctrl+.: rust-analyzer\n* Project > Manage Packages: "
            "cargo add / remove (crates.io)\n")


def create_cargo_files(folder: Path, name: str, template: str) -> list[str]:
    """Write the cargo project of *template* into *folder*; returns the files (relative, posix)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    crate = crate_name(name)
    files: dict[str, str] = {".gitignore": GITIGNORE}
    if template == "rust_library":
        files["Cargo.toml"] = _cargo_toml(name)
        files["src/lib.rs"] = LIB_RS.format(name=name, crate=crate)
        files["examples/demo.rs"] = LIB_EXAMPLE.format(crate=crate)
        files["README.md"] = _readme(name, "A Rust library crate.")
    elif template == "rust_egui":
        files["Cargo.toml"] = _cargo_toml(name, f'eframe = "{EGUI_VERSION}"\n')
        files["src/main.rs"] = EGUI_MAIN.format(name=name, ver=EGUI_VERSION)
        files["README.md"] = _readme(name, f"An egui desktop application (eframe {EGUI_VERSION}).")
    elif template == "rust_workspace":
        files["Cargo.toml"] = '[workspace]\nresolver = "2"\nmembers = ["app", "core"]\n'
        core = f"{crate}_core"
        files["app/Cargo.toml"] = (f'[package]\nname = "{crate}_app"\nversion = "0.1.0"\nedition = "2021"\n\n'
                                   f'[dependencies]\n{core} = {{ path = "../core" }}\n')
        files["app/src/main.rs"] = WS_APP_MAIN.format(name=name, core=core)
        files["core/Cargo.toml"] = f'[package]\nname = "{core}"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n'
        files["core/src/lib.rs"] = WS_CORE_LIB.format(name=name)
        files["README.md"] = _readme(name, "A cargo workspace: `app` (binary) uses `core` (library).")
    else:
        files["Cargo.toml"] = _cargo_toml(name)
        files["src/main.rs"] = CONSOLE_MAIN.format(name=name)
        files["README.md"] = _readme(name, "A Rust console application.")
    for rel, text in files.items():
        p = folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(text, encoding="utf-8")
    return [r for r in files if r != ".gitignore"]


def _adapter(folder: Path):
    from ..foreign.cargo_project import CargoAdapter
    a = CargoAdapter(Path(folder) / "Cargo.toml", all_members=True)
    a.scan()
    return a


class RustCargoPlugin(LanguagePlugin):
    id = "rust-cargo"
    display_name = "Rust (Cargo)"
    code_ext = ".rs"
    case_sensitive = True
    line_comments = ["//"]
    block_comment = ("/*", "*/")
    string_quotes = ['"']
    keywords = RUST_KEYWORDS
    builtins = RUST_BUILTINS
    supports_debug = True
    has_forms = False
    project_name_base = "RustApp"
    tool_names = ["cargo"]
    install_hint = "Install Rust from https://rustup.rs (cargo + rustc), then: rustup component add rust-analyzer rust-src"
    package_manager = PackageManager(
        name="cargo (crates.io)", tool="cargo",
        list_cmd=["cargo", "tree", "--depth", "1", "-e", "normal,dev"],
        search_cmd=["cargo", "search", "{query}", "--limit", "20"],
        install_cmd=["cargo", "add", "{name}"], uninstall_cmd=["cargo", "remove", "{name}"],
        init_cmd=None, manifest="Cargo.toml", search_url="https://crates.io/search?q={query}")

    # ------------------------------------------------------------ New Project
    def project_templates(self) -> list[tuple[str, str, str, str]]:
        return list(TEMPLATES)

    def create_new_project(self, folder: Path, name: str, template: str = "") -> Project:
        folder = Path(folder)
        if template == "rust_gui":                     # a RAD form: the Rust GUI Bridge project
            from ..workspace import create_project
            return create_project(folder, name, "rust-bridge")
        create_cargo_files(folder, name, template or "rust_console")
        project = Project(folder, name, self.id)
        self.refresh_modules(project)
        targets = _adapter(folder).targets
        project.startup = targets[0].name if targets else ""
        if template == "rust_library":
            project.kind = "app"                       # runs its tests (not a RAD Class Library)
        project.save()
        return project

    @staticmethod
    def refresh_modules(project: Project) -> None:
        """project.modules = the cargo files on disk (src/, tests/, examples/, benches/, members ...)."""
        from ..foreign._others_base import source_files
        from ..foreign.cargo_project import SOURCE_EXT
        mods = source_files(Path(project.folder), SOURCE_EXT, extra_names=("Cargo.toml",))
        mods = [m for m in mods if m != "Cargo.lock"]
        if "Cargo.toml" in mods:
            mods.remove("Cargo.toml")
            mods.insert(0, "Cargo.toml")
        project.modules = mods

    # ------------------------------------------------------------ code
    def code_file(self, form_name: str) -> str:
        return "src/main.rs"

    def designer_file(self, form_name: str) -> str:
        return "src/main.rs"

    def generate_designer(self, form, user_code: str) -> str:
        return user_code

    def new_code(self, form, is_startup: bool) -> str:
        return ""

    def module_template(self, name: str) -> str:
        return (f"//! Module {name}: declare it in main.rs / lib.rs with `mod {re.sub(r'[^0-9a-z_]', '_', name.lower())};`\n\n"
                "pub fn hello() -> &'static str {\n    \"hello\"\n}\n")

    def completions(self, code, line, col, path, names=None):
        out = [Completion(k, "keyword") for k in self.keywords] + [Completion(b, "function") for b in self.builtins]
        seen = {c.name for c in out}
        for w in re.findall(r"\b[A-Za-z_]\w{2,}\b", code):
            if w not in seen:
                seen.add(w)
                out.append(Completion(w, "variable"))
        return out

    # ------------------------------------------------------------ run / debug
    def tool(self) -> str:
        from ..rust_tools import find_cargo
        return find_cargo()

    def find_interpreter(self, configured: str = "") -> str:
        if configured and Path(configured).exists():
            return configured
        return self.tool() or ""

    def _target(self, folder: Path, startup: str):
        a = _adapter(folder)
        return a, a.target(startup)

    def run_spec(self, folder: Path, startup_form: str, interpreter: str) -> RunSpec:
        a, t = self._target(folder, startup_form)
        step = a.run_step(t, False) if t is not None else None
        if step is None:
            raise RuntimeError("Rust (Cargo): nothing to run - no bin, example or test target in Cargo.toml")
        return RunSpec(str(step.argv[0]), [str(x) for x in step.argv[1:]], Path(step.cwd), dict(step.env) or None)

    def debug_spec(self, folder: Path, startup_form: str, interpreter: str, breakpoints) -> RunSpec:
        return self.run_spec(folder, startup_form, interpreter)

    def make_session(self, win, spec, debug: bool):
        """MainWindow._make_session hook: cargo build/run, or a GNU debug build + gdb (DAP)."""
        from ..foreign._others_base import ChainSession
        project = win.project
        if project is None or project.language != self.id:
            return None
        a, t = self._target(Path(project.folder), project.startup)
        if t is None:
            return None
        pre = a.build_steps(t, debug)
        if debug:
            s = a.debug_session(win, t, pre)
            if s is not None:
                return s
        run = a.run_step(t, False)                     # Ctrl+F5 (or F5 when gdb is unavailable): cargo run/test
        return ChainSession([run] if run else [], None, win)


PLUGIN = RustCargoPlugin()

if __name__ == "__main__":                    # python -m radide.languages.rust_cargo <folder> <name> <template>
    create_cargo_files(Path(sys.argv[1]), sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "rust_console")
