"""Rust Cargo projects (Cargo.toml, cargo workspaces) opened IN PLACE.

* Solution Explorer: one project per package (a workspace shows its members as projects, plus a
  "<name> (workspace)" project for the root files when the root manifest is virtual). Each project shows
  Dependencies, src/, tests/, examples/, benches/ and Cargo.toml as a folder tree;
* run targets (bins, examples, integration tests, unit tests, benches) come from ``cargo metadata`` and are
  picked in the "Rust target" combo (radide/features/rust_ide.py) or Native > Startup target;
* Ctrl+F5 = ``cargo run --bin X`` (``--example X``, ``cargo test --test X`` ...);
* F5 = build for the x86_64-pc-windows-gnu target with debug info, then gdb over DAP (breakpoints, locals,
  call stack, stepping). gdb reads the DWARF of the GNU build; MSVC builds carry PDBs gdb cannot read;
* Native menu: check, clippy, fmt, doc --open, build --release, run --release, test, update, outdated, tree,
  clean; packages UI = cargo add / remove / search (crates.io).

The cargo files stay authoritative: nothing is written into the project folder by the IDE (its state lives in
%LOCALAPPDATA%\\RADIDE\\foreign-state)."""
from __future__ import annotations

import os
import shutil
import webbrowser
from pathlib import Path

from ._others_base import (ChainSession, ForeignAdapter, ForeignProject, LazyStep, RunTarget, Step, gdb_session,
                           show_projects, source_files)
from .. import rust_tools as rt

SOURCE_EXT = (".rs", ".toml", ".md", ".json", ".yaml", ".yml", ".txt", ".lock", ".ron", ".wgsl", ".glsl",
              ".sql", ".html", ".css", ".js", ".proto")
FOLDER_ORDER = {"src": 0, "tests": 1, "examples": 2, "benches": 3}
KIND_LABEL = {"bin": "bin", "example": "example", "test": "test", "bench": "bench"}


def _cargo() -> str:
    return rt.find_cargo() or "cargo"


class CargoAdapter(ForeignAdapter):
    kind = "cargo"
    title = "Cargo project"
    base_language = "rust-bridge"          # Rust keywords / syntax; IntelliSense comes from rust-analyzer

    def __init__(self, native: Path, package: dict | None = None, meta: dict | None = None,
                 exclude: tuple = (), workspace_only: bool = False, all_members: bool = False):
        native = Path(native).resolve()
        if native.is_dir():
            native = native / "Cargo.toml"
        super().__init__(native, native.parent)
        self.package = package
        self.meta = meta
        self.exclude = tuple(exclude)            # member folders (relative) shown as their own projects
        self.workspace_only = workspace_only     # the virtual root of a workspace (no package)
        self.all_members = all_members           # one project for the whole workspace (RAD "Rust (Cargo)")
        self.ws_root = rt.workspace_root(self.root)
        self.deps: list[tuple[str, str, str]] = []

    # ------------------------------------------------------------ scan
    def scan(self) -> None:
        meta = self.meta if self.meta is not None else rt.cargo_metadata(self.root)
        self.meta = meta
        pkgs = []
        if self.package is not None:
            pkgs = [self.package]
        elif self.all_members:
            members = set(meta.get("workspace_members") or [])
            pkgs = [p for p in meta.get("packages", []) if not members or p.get("id") in members]
        elif not self.workspace_only:
            pkgs = [p for p in meta.get("packages", [])
                    if Path(p.get("manifest_path", "")).resolve() == self.native]
        if self.all_members:
            self.name = self.root.name
        elif pkgs:
            self.name = pkgs[0].get("name") or self.root.name
            self.title = "Cargo package"
        else:
            self.name = (self.root.name + " (workspace)") if self.workspace_only else self.root.name
            self.title = "Cargo workspace" if self.workspace_only else self.title
        self.packages = pkgs
        skip = {e.split("/")[0] for e in self.exclude}
        files = source_files(self.root, SOURCE_EXT, extra_names=("Cargo.toml", "Cargo.lock", ".rustfmt.toml",
                                                                  "rustfmt.toml", "clippy.toml"))
        mods = []
        for f in files:
            if any(f == e or f.startswith(e.rstrip("/") + "/") for e in self.exclude):
                continue
            if self.workspace_only and "/" in f and f.split("/")[0] in skip:
                continue
            mods.append(f)
        if "Cargo.toml" in mods:
            mods.remove("Cargo.toml")
            mods.insert(0, "Cargo.toml")
        self.modules = mods
        self.targets = []
        self.deps = []
        for p in pkgs:
            self._targets_of(p)
            for d in p.get("dependencies", []):
                kind = d.get("kind") or ""
                self.deps.append((d.get("name", ""), d.get("req", ""), kind))
        if self.workspace_only or (self.all_members and len(pkgs) > 1):
            self.targets.append(RunTarget("test: workspace (cargo test --workspace)", "test-all",
                                          {"pkg": "", "name": ""}))
        ra = rt.rust_analyzer()
        self.info.append(f"cargo: {rt.find_cargo() or 'not found'}; rust-analyzer: {ra or 'not installed (' + rt.INSTALL_HINT + ')'}")
        if self.ws_root != self.root:
            self.info.append(f"workspace root: {self.ws_root}")
        why = rt.debug_missing()
        self.info.append("F5 debugging: gdb on the x86_64-pc-windows-gnu build" + (f" - unavailable: {why}" if why else ""))

    def _targets_of(self, p: dict) -> None:
        pkg = p.get("name", "")
        lib = False
        tests_found = False
        for t in p.get("targets", []):
            kinds = t.get("kind") or []
            name = t.get("name", "")
            src = t.get("src_path", "")
            if "bin" in kinds:
                self.targets.append(RunTarget(f"bin: {name}", "bin", {"pkg": pkg, "name": name, "src": src}))
            elif "example" in kinds:
                self.targets.append(RunTarget(f"example: {name}", "example", {"pkg": pkg, "name": name, "src": src}))
            elif "test" in kinds:
                tests_found = True
                self.targets.append(RunTarget(f"test: {name}", "test", {"pkg": pkg, "name": name, "src": src}))
            elif "bench" in kinds:
                self.targets.append(RunTarget(f"bench: {name}", "bench", {"pkg": pkg, "name": name, "src": src}))
            elif any(k in kinds for k in ("lib", "rlib", "dylib", "cdylib", "staticlib", "proc-macro")):
                lib = True
        if lib:
            self.targets.append(RunTarget("test: lib (unit tests)", "test-lib", {"pkg": pkg, "name": ""}))
        if lib or tests_found or any(t.kind == "bin" for t in self.targets):
            self.targets.append(RunTarget(f"test: all ({pkg})", "test-all", {"pkg": pkg, "name": ""}))
        # bins first (F5 runs the first target unless another is chosen)
        self.targets.sort(key=lambda t: {"bin": 0, "example": 1, "test": 2, "test-lib": 3, "test-all": 4,
                                         "bench": 5}.get(t.kind, 9))

    # ------------------------------------------------------------ helpers
    def tool(self) -> str:
        return _cargo()

    def _pkg_args(self, target: RunTarget | None) -> list[str]:
        pkg = (target.data.get("pkg") if target is not None else "") or \
              (self.packages[0].get("name") if getattr(self, "packages", None) else "")
        return ["-p", pkg] if pkg else []

    def _sel_args(self, target: RunTarget) -> list[str]:
        k, n = target.kind, target.data.get("name", "")
        if k == "bin":
            return ["--bin", n]
        if k == "example":
            return ["--example", n]
        if k == "test":
            return ["--test", n]
        if k == "bench":
            return ["--bench", n]
        if k == "test-lib":
            return ["--lib"]
        return []

    def cargo_step(self, args: list[str], title: str = "", env: dict | None = None) -> Step:
        return Step([_cargo(), *args], self.ws_root if self.workspace_only else self.root, dict(env or {}),
                    title or "cargo " + " ".join(args[:4]))

    def target_dir(self) -> Path:
        return rt.target_dir(self.meta or {}, self.ws_root)

    # ------------------------------------------------------------ build / run
    def run_step(self, target, debug):
        if target is None:
            return None
        k = target.kind
        if k in ("bin", "example"):
            return self.cargo_step(["run", *self._pkg_args(target), *self._sel_args(target)])
        if k in ("test", "test-lib", "test-all"):
            ws = ["--workspace"] if k == "test-all" and not target.data.get("pkg") else self._pkg_args(target)
            return self.cargo_step(["test", *ws, *self._sel_args(target)])
        if k == "bench":
            return self.cargo_step(["bench", *self._pkg_args(target), *self._sel_args(target)])
        return None

    def build_steps(self, target, debug):
        if not debug or target is None or target.kind not in ("bin", "example", "test", "test-lib"):
            return []
        if rt.debug_missing():
            return []
        env = rt.gnu_env()
        args = ["build"] if target.kind in ("bin", "example") else ["test", "--no-run"]
        args += ["--target", rt.RUST_GNU] if os.name == "nt" else []
        args += self._pkg_args(target) + self._sel_args(target)
        return [self.cargo_step(args, "cargo " + " ".join(args) + "  (debug build for gdb)", env)]

    def debug_exe(self, target: RunTarget) -> Path:
        base = self.target_dir() / (rt.RUST_GNU if os.name == "nt" else "") / "debug"
        n = target.data.get("name", "")
        if target.kind == "bin":
            return base / (n + rt.EXE)
        if target.kind == "example":
            return base / "examples" / (n + rt.EXE)
        stem = (n or (target.data.get("pkg") or "")).replace("-", "_")
        hits = sorted((base / "deps").glob(f"{stem}-*{rt.EXE}"), key=lambda p: p.stat().st_mtime)
        hits = [h for h in hits if h.suffix.lower() == rt.EXE or not rt.EXE]
        return hits[-1] if hits else base / "deps" / (stem + rt.EXE)

    def debug_session(self, win, target, pre):
        if target is None or target.kind not in ("bin", "example", "test", "test-lib"):
            return None
        why = rt.debug_missing()
        if why:
            win.log(f"Rust debugging unavailable: {why} - running without the debugger")
            return None
        env = rt.gnu_env()
        args = [] if target.kind in ("bin", "example") else ["--test-threads=1"]
        return ChainSession(pre, lambda: gdb_session(win, self.debug_exe(target), args, self.root, env), win)

    def commands(self):
        multi = self.workspace_only or (self.all_members and len(getattr(self, "packages", [])) > 1)
        p = [] if multi else self._pkg_args(None)
        ws = ["--workspace"] if multi else p
        out = [("cargo check", [self.cargo_step(["check", *ws, "--all-targets"])]),
               ("cargo clippy (lint)", [self.cargo_step(["clippy", *ws, "--all-targets"])]),
               ("cargo fmt (format all)", [self.cargo_step(["fmt", "--all"] if multi else ["fmt", *p])]),
               ("cargo build", [self.cargo_step(["build", *ws])]),
               ("cargo build --release", [self.cargo_step(["build", "--release", *ws])]),
               ("cargo test", [self.cargo_step(["test", *ws])]),
               ("cargo doc --open", [self.cargo_step(["doc", "--no-deps", "--open", *ws])]),
               ("cargo update", [self.cargo_step(["update"])]),
               ("cargo outdated (dependencies with newer versions)", [self.outdated_step()]),
               ("cargo tree", [self.cargo_step(["tree", *p, "--depth", "1"])]),
               ("cargo clean", [self.cargo_step(["clean"])])]
        for t in self.targets:
            if t.kind in ("bin", "example"):
                out.append((f"cargo run --release ({t.name})",
                            [self.cargo_step(["run", "--release", *self._pkg_args(t), *self._sel_args(t)])]))
        return out

    def outdated_step(self) -> Step:
        """cargo outdated when installed (cargo install cargo-outdated), else cargo update --dry-run."""
        if shutil.which("cargo-outdated") or (rt.cargo_home() / "bin" / ("cargo-outdated" + rt.EXE)).exists():
            return self.cargo_step(["outdated", "-R"])
        return LazyStep(lambda: [_cargo(), "update", "--dry-run", "--verbose"],
                        self.ws_root if self.workspace_only else self.root, {},
                        "cargo update --dry-run  (install cargo-outdated for a table)")


# ---------------------------------------------------------------- the project (own Solution Explorer tree)
class CargoProject(ForeignProject):
    def fill_solution_tree(self, win, pi, name: str) -> None:
        fill_tree(win, self, pi)

    def on_tree_activate(self, win, item, kind, name) -> None:
        if kind == "foreign_dep" and name:
            webbrowser.open(f"https://docs.rs/{name}")
        elif kind == "foreign_file" and name:
            win.open_any_file(Path(name))


def fill_tree(win, project: CargoProject, pi) -> None:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QTreeWidgetItem
    from ..features.solution_ui import PROJECT_ROLE, ROLE
    key = win._pkey(project)
    style = win.style()
    from PyQt6.QtWidgets import QStyle
    dir_icon = style.standardIcon(QStyle.StandardPixmap.SP_DirIcon)
    file_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileIcon)
    link_icon = style.standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon)
    a = project.adapter
    if a.deps:
        dn = QTreeWidgetItem(pi, ["Dependencies"])
        dn.setData(0, ROLE, ("references", project.name))
        dn.setData(0, PROJECT_ROLE, key)
        dn.setIcon(0, link_icon)
        for dname, req, kind in sorted(a.deps, key=lambda d: (d[2], d[0])):
            di = QTreeWidgetItem(dn, [f"{dname} {req}" + (f"  ({kind})" if kind else "")])
            di.setData(0, ROLE, ("foreign_dep", dname))
            di.setData(0, PROJECT_ROLE, key)
            di.setIcon(0, link_icon)
            di.setToolTip(0, f"crates.io: {dname} {req} - double-click: docs.rs")
    folders: dict[str, QTreeWidgetItem] = {}

    def folder(rel: str):
        if not rel:
            return pi
        if rel in folders:
            return folders[rel]
        parent = folder(rel.rpartition("/")[0])
        it = QTreeWidgetItem(parent, [rel.rpartition("/")[2]])
        it.setData(0, ROLE, ("folder", rel))
        it.setData(0, PROJECT_ROLE, key)
        it.setIcon(0, dir_icon)
        folders[rel] = it
        return it

    def order(m: str):
        parts = m.split("/")
        top = parts[0] if len(parts) > 1 else ""
        return (0 if len(parts) > 1 else 1, FOLDER_ORDER.get(top, 9), m.lower())
    for m in sorted(project.modules, key=order):
        parent = folder(m.rpartition("/")[0])
        it = QTreeWidgetItem(parent, [m.rpartition("/")[2]])
        it.setData(0, ROLE, ("module", m))
        it.setData(0, PROJECT_ROLE, key)
        it.setIcon(0, file_icon)
        targets = [t.name for t in a.targets if Path(t.data.get("src", "") or "_").resolve() == (Path(project.folder) / m).resolve()]
        if targets:
            it.setToolTip(0, "Target: " + ", ".join(targets))
            if project.startup in targets:
                f = it.font(0)
                f.setBold(True)
                it.setFont(0, f)
    for rel, it in folders.items():
        if rel.count("/") == 0 and rel in FOLDER_ORDER:
            it.setExpanded(True)
    pi.setExpanded(True)
    _ = Qt


# ---------------------------------------------------------------- open
def projects_for(manifest: Path) -> tuple[list[CargoProject], str]:
    """CargoProjects for a manifest: a package, a workspace (root package and/or members)."""
    manifest = Path(manifest).resolve()
    root = manifest.parent
    meta = rt.cargo_metadata(root, refresh=True)
    members = set(meta.get("workspace_members") or [])
    pkgs = [p for p in meta.get("packages", []) if not members or p.get("id") in members]
    root_pkg = next((p for p in pkgs if Path(p.get("manifest_path", "")).resolve() == manifest), None)
    others = [p for p in pkgs if p is not root_pkg]
    projects: list[CargoProject] = []
    rels = []
    for p in others:
        try:
            rels.append(Path(p["manifest_path"]).resolve().parent.relative_to(root).as_posix())
        except ValueError:
            pass
    if root_pkg is not None:
        projects.append(CargoProject(CargoAdapter(manifest, root_pkg, meta, exclude=tuple(rels))))
    elif others:
        projects.append(CargoProject(CargoAdapter(manifest, None, meta, exclude=tuple(rels), workspace_only=True)))
    for p in others:
        projects.append(CargoProject(CargoAdapter(Path(p["manifest_path"]), p, meta)))
    if not projects:                                   # cargo metadata failed: a plain folder view
        projects.append(CargoProject(CargoAdapter(manifest, None, meta)))
    startup = next((pr.name for pr in projects if any(t.kind == "bin" for t in pr.adapter.targets)), projects[0].name)
    return projects, startup


def _plugin_package_manager(project) -> None:
    """Project > Manage Packages for Cargo projects: cargo add / remove / search (crates.io)."""
    try:
        from ..languages import get_plugin
        from ..languages.rust_bridge import PLUGIN as RB
        from ..languages.base import PackageManager
        pm = RB.package_manager
        plugin = get_plugin(project.language)
        plugin.package_manager = PackageManager(
            name="cargo (crates.io)", tool="cargo", list_cmd=["cargo", "tree", "--depth", "1", "-e", "normal,dev"],
            search_cmd=pm.search_cmd, install_cmd=pm.install_cmd, uninstall_cmd=pm.uninstall_cmd, init_cmd=None,
            manifest="Cargo.toml", search_url=pm.search_url)
        plugin.supports_debug = True
    except Exception:  # noqa: BLE001
        pass


def open_cargo(win, path: Path) -> bool:
    path = Path(path)
    manifest = path / "Cargo.toml" if path.is_dir() else path
    if not manifest.is_file():
        return False
    projects, startup = projects_for(manifest)
    for p in projects:
        _plugin_package_manager(p)
    ok = show_projects(win, projects, projects[0].name if len(projects) == 1 else manifest.parent.name,
                       manifest, startup)
    if ok and getattr(win, "sln", None) is not None:
        win.sln.editor_for_file = lambda w, file: _editor_for_file(w, file)
        win.sln.cargo_root = manifest.parent
        try:
            from ..features.rust_ide import on_cargo_opened
            on_cargo_opened(win)
        except Exception as e:  # noqa: BLE001
            win.log(f"[rust] {e}")
    return ok


def _editor_for_file(win, file):
    """Nested paths (src/lib.rs, crates/core/src/x.rs) of Cargo projects: open by absolute path."""
    p = Path(file)
    if not p.is_absolute() and win.project is not None:
        p = Path(win.project.folder) / p
    if p.is_file() and callable(getattr(win, "open_file", None)):
        try:
            return win.open_file(p)
        except Exception:  # noqa: BLE001
            return None
    return None


def probe(folder: Path):
    f = Path(folder) / "Cargo.toml"
    return f if f.is_file() else None


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format(["Cargo.toml"], open_cargo, "Rust Cargo project (Cargo.toml)", folder_probe=probe,
                    name="cargo", priority=6)
