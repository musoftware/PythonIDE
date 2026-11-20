"""Project actions for Flutter (pub, build, analyze, test, doctor, New Screen), Go (go mod tidy / build / test /
vet), Rust (cargo) and C / C++ CMake projects (configure, build targets, clean)."""
from __future__ import annotations

import re
from pathlib import Path

from ..project_actions import Action, Field, Provider, Separator, Submenu, matches, read_text
from ._common import snake, studly, target_folder, write_new


# ============================================================================ Flutter
def flutter() -> str:
    try:
        from ..languages.flutter import flutter_exe
        return flutter_exe() or "flutter"
    except Exception:  # noqa: BLE001
        return "flutter"


def dart() -> str:
    try:
        from ..languages.flutter import dart_exe
        return dart_exe() or "dart"
    except Exception:  # noqa: BLE001
        return "dart"


SCREEN_STATEFUL = """import 'package:flutter/material.dart';

class {cls} extends StatefulWidget {{
  const {cls}({{super.key}});

  @override
  State<{cls}> createState() => _{cls}State();
}}

class _{cls}State extends State<{cls}> {{
  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(title: const Text('{title}')),
      body: const Center(child: Text('{title}')),
    );
  }}
}}
"""
SCREEN_STATELESS = """import 'package:flutter/material.dart';

class {cls} extends StatelessWidget {{
  const {cls}({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(title: const Text('{title}')),
      body: const Center(child: Text('{title}')),
    );
  }}
}}
"""
WIDGET_STATELESS = """import 'package:flutter/material.dart';

class {cls} extends StatelessWidget {{
  const {cls}({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return const Placeholder();
  }}
}}
"""


class Flutter(Provider):
    id, title, priority, icon = "flutter", "Flutter", 45, ("Fl", "#02569B")
    markers = ("pubspec.yaml",)

    def detect(self, folder, project):
        p = folder / "pubspec.yaml"
        return p.is_file() and re.search(r"^\s*sdk:\s*flutter\b", read_text(p), re.M) is not None

    @staticmethod
    def is_rad(ctx) -> bool:
        """A RAD IDE Flutter project (forms designed in the IDE)."""
        return getattr(ctx.project, "language", "") == "flutter" and (ctx.folder / "project.radproj").is_file()

    def f(self, ctx, *args, title=None, **kw):
        return ctx.run_cli([flutter(), *args], title=title or "flutter " + " ".join(args[:3]), **kw)

    def _new_screen_action(self, ctx) -> Action:
        if self.is_rad(ctx):
            return Action("new-screen", "New Screen (Form)...", lambda c: c.win.add_form(), opens="none",
                          tip="Add a new form: every form is a screen of the app")
        return Action("new-screen", "New Screen...", self._new_screen,
                      ask=[Field("name", "Name", default="Settings"),
                           Field("stateful", "Stateful (has its own state)", "bool", default=True)],
                      tip="lib/screens/<name>_screen.dart")

    def _new_screen(self, ctx):
        base = studly(ctx.values["name"])
        if base.endswith("Screen"):
            base = base[:-6]
        cls = base + "Screen"
        folder = target_folder(ctx, "lib/screens")
        if not matches(folder, "lib/**"):
            folder = "lib/screens"
        tpl = SCREEN_STATEFUL if ctx.values.get("stateful") else SCREEN_STATELESS
        write_new(ctx, f"{folder}/{snake(base)}_screen.dart", tpl.format(cls=cls, title=base))

    def new_widget(self) -> Action:
        return Action("new-widget", "New Widget...", self._new_widget,
                      ask=[Field("name", "Name", default="ProfileCard")], tip="lib/widgets/<name>.dart")

    def _new_widget(self, ctx):
        cls = studly(ctx.values["name"])
        folder = target_folder(ctx, "lib/widgets")
        if not matches(folder, "lib/**"):
            folder = "lib/widgets"
        write_new(ctx, f"{folder}/{snake(cls)}.dart", WIDGET_STATELESS.format(cls=cls))

    def pub_items(self) -> list:
        return [Action("pub-get", "pub get", lambda c: self.f(c, "pub", "get"), opens="none", toolbar=True,
                       icon="SP_ArrowDown"),
                Action("pub-upgrade", "pub upgrade", lambda c: self.f(c, "pub", "upgrade"), opens="none"),
                Action("pub-outdated", "pub outdated", lambda c: self.f(c, "pub", "outdated"), opens="none"),
                Action("pub-add", "Add Package (pub add)...", self._pub_add, opens="none",
                       ask=[Field("package", "Package", placeholder="http  provider  shared_preferences"),
                            Field("dev", "Development dependency (--dev)", "bool")])]

    def _pub_add(self, ctx):
        argv = ["pub", "add", *(["--dev"] if ctx.values.get("dev") else []), *ctx.values["package"].split()]
        self.f(ctx, *argv)

    def build_items(self) -> list:
        return [Action(f"build-{t}", f"Build {label}", lambda c, t=t: self.f(c, "build", t, *extra), opens="none")
                for t, label, extra in (("apk", "APK (Android)", ["--release"]),
                                        ("appbundle", "App Bundle (Google Play)", []),
                                        ("windows", "Windows", ["--release"]),
                                        ("web", "Web", ["--release"]))]

    def actions(self, ctx):
        return [Action("run", "Run (flutter run)", lambda c: c.win.run_project(False) if self.is_rad(c)
                       else self.f(c, "run"), opens="none", icon="SP_MediaPlay"),
                Separator(),
                self._new_screen_action(ctx),
                self.new_widget(),
                Separator(),
                Submenu("Packages", self.pub_items()),
                Submenu("Build", self.build_items()),
                Separator(),
                Action("analyze", "Analyze (flutter analyze)", lambda c: self.f(c, "analyze"), opens="none"),
                Action("test", "Run Tests (flutter test)", lambda c: self.f(c, "test"), opens="none"),
                Action("format", "Format Code (dart format)", lambda c: c.run_cli([dart(), "format", "lib", "test"]
                                                                                 if c.path("test").is_dir()
                                                                                 else [dart(), "format", "lib"]),
                       opens="none"),
                Action("clean", "Clean (flutter clean)", lambda c: self.f(c, "clean"), opens="none", refresh=True),
                Separator(),
                Action("devices", "List Devices", lambda c: self.f(c, "devices"), opens="none"),
                Action("doctor", "Flutter Doctor", lambda c: self.f(c, "doctor", "-v"), opens="none")]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "lib/**"):
            return [self._new_screen_action(ctx), self.new_widget()]
        if matches(rel_folder, "test/**", "integration_test/**"):
            return [Action("test-folder", "Run Tests in This Folder", lambda c: self.f(c, "test", rel_folder),
                           opens="none")]
        if matches(rel_folder, "android", "windows", "web", "ios"):
            return [i for i in self.build_items() if i.id.endswith(rel_folder.replace("android", "apk"))]
        return []

    def file_actions(self, ctx, rel_file):
        if matches(rel_file, "**/*_test.dart"):
            return [Action("test-file", "Run This Test", lambda c: self.f(c, "test", rel_file), opens="none")]
        if rel_file == "pubspec.yaml":
            return self.pub_items()
        return []


# ============================================================================ Go
def go() -> str:
    try:
        from ..lsp_servers import find_go
        return find_go() or "go"
    except Exception:  # noqa: BLE001
        return "go"


class Go(Provider):
    id, title, priority, icon = "go", "Go", 40, ("Go", "#00ADD8")
    markers = ("go.mod",)

    def detect(self, folder, project):
        return (folder / "go.mod").is_file()

    def g(self, ctx, *args, **kw):
        return ctx.run_cli([go(), *args], title="go " + " ".join(args[:3]), **kw)

    def actions(self, ctx):
        return [Action("run", "Run (go run .)", lambda c: self.g(c, "run", "."), toolbar=True, opens="none",
                       icon="SP_MediaPlay"),
                Action("build", "Build (go build ./...)", lambda c: self.g(c, "build", "./..."), opens="none"),
                Action("test", "Test (go test ./...)", lambda c: self.g(c, "test", "./..."), opens="none"),
                Action("vet", "Vet (go vet ./...)", lambda c: self.g(c, "vet", "./..."), opens="none"),
                Action("fmt", "Format (go fmt ./...)", lambda c: self.g(c, "fmt", "./..."), opens="none"),
                Separator(),
                Action("tidy", "go mod tidy", lambda c: self.g(c, "mod", "tidy"), opens="none", toolbar=True,
                       icon="SP_BrowserReload"),
                Action("download", "go mod download", lambda c: self.g(c, "mod", "download"), opens="none"),
                Action("get", "Add Module (go get)...", lambda c: self.g(c, "get", *c.values["module"].split()),
                       ask=[Field("module", "Module", placeholder="github.com/gin-gonic/gin@latest")], opens="none"),
                Action("update", "Update All Modules (go get -u ./...)", lambda c: self.g(c, "get", "-u", "./..."),
                       opens="none"),
                Separator(),
                Action("install", "Install (go install)", lambda c: self.g(c, "install"), opens="none"),
                Action("env", "go env", lambda c: self.g(c, "env"), opens="none")]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if any(ctx.path(rel_folder).glob("*.go")):
            pkg = "./" + rel_folder
            return [Action("test-pkg", "Test This Package", lambda c: self.g(c, "test", pkg), opens="none"),
                    Action("build-pkg", "Build This Package", lambda c: self.g(c, "build", pkg), opens="none"),
                    Action("run-pkg", "Run This Package", lambda c: self.g(c, "run", pkg), opens="none",
                           enabled=lambda c: any("package main" in read_text(f) for f in c.path(rel_folder)
                                                 .glob("*.go")))]
        return []

    def file_actions(self, ctx, rel_file):
        if rel_file.endswith("_test.go"):
            pkg = "./" + (str(Path(rel_file).parent.as_posix()) if "/" in rel_file else ".")
            pkg = pkg.replace("/.", "") if pkg.endswith("/.") else pkg
            return [Action("test-file", "Test This Package", lambda c: self.g(c, "test", "-v", pkg), opens="none")]
        if rel_file == "go.mod":
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id in ("tidy", "download", "get")]
        return []


# ============================================================================ Rust
def cargo() -> str:
    try:
        from ..languages.rust_bridge import find_cargo
        return find_cargo() or "cargo"
    except Exception:  # noqa: BLE001
        return "cargo"


class Rust(Provider):
    id, title, priority, icon = "rust", "Rust", 40, ("Rs", "#B7410E")
    markers = ("Cargo.toml",)

    def detect(self, folder, project):
        return (folder / "Cargo.toml").is_file()

    def c(self, ctx, *args, **kw):
        return ctx.run_cli([cargo(), *args], title="cargo " + " ".join(args[:3]), **kw)

    def actions(self, ctx):
        return [Action("run", "Run (cargo run)", lambda c: self.c(c, "run"), toolbar=True, opens="none",
                       icon="SP_MediaPlay"),
                Action("build", "Build (cargo build)", lambda c: self.c(c, "build"), opens="none", toolbar=True,
                       icon="SP_DialogApplyButton"),
                Action("build-release", "Build Release", lambda c: self.c(c, "build", "--release"), opens="none"),
                Action("check", "Check (cargo check)", lambda c: self.c(c, "check"), opens="none"),
                Action("test", "Test (cargo test)", lambda c: self.c(c, "test"), opens="none"),
                Separator(),
                Action("clippy", "Lint (cargo clippy)", lambda c: self.c(c, "clippy"), opens="none"),
                Action("fmt", "Format (cargo fmt)", lambda c: self.c(c, "fmt"), opens="none"),
                Action("doc", "Build Docs and Open", lambda c: self.c(c, "doc", "--open"), opens="none"),
                Separator(),
                Action("add", "Add Crate (cargo add)...", self._add, opens="none",
                       ask=[Field("crate", "Crate", placeholder="serde  rand@0.8"),
                            Field("features", "Features (comma separated)", required=False, placeholder="derive"),
                            Field("dev", "Development dependency (--dev)", "bool")]),
                Action("remove", "Remove Crate (cargo remove)...", lambda c: self.c(c, "remove", *c.values["crate"].split()),
                       opens="none", ask=[Field("crate", "Crate", placeholder="serde")]),
                Action("update", "cargo update", lambda c: self.c(c, "update"), opens="none"),
                Action("outdated", "Outdated Dependencies", self._outdated, opens="none"),
                Action("run-release", "Run Release (cargo run --release)", lambda c: self.c(c, "run", "--release"),
                       opens="none"),
                Action("clean", "cargo clean", lambda c: self.c(c, "clean"), opens="none")]

    def _outdated(self, ctx):
        """cargo outdated when installed (cargo install cargo-outdated), else cargo update --dry-run."""
        try:
            from ..rust_tools import cargo_home, EXE
            has = (cargo_home() / "bin" / ("cargo-outdated" + EXE)).exists()
        except Exception:  # noqa: BLE001
            has = False
        self.c(ctx, *(["outdated", "-R"] if has else ["update", "--dry-run", "--verbose"]))

    def _add(self, ctx):
        argv = ["add", *ctx.values["crate"].split()]
        if ctx.values.get("features"):
            argv += ["--features", ctx.values["features"].replace(" ", "")]
        if ctx.values.get("dev"):
            argv.append("--dev")
        self.c(ctx, *argv)

    def folder_actions(self, ctx, rel_folder):
        if rel_folder == "":
            return self.actions(ctx)
        if matches(rel_folder, "tests/**"):
            return [Action("test", "Run Integration Tests", lambda c: self.c(c, "test", "--tests"), opens="none")]
        if matches(rel_folder, "src/**"):
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id in ("build", "check", "test")]
        return []

    def file_actions(self, ctx, rel_file):
        stem = Path(rel_file).stem
        if matches(rel_file, "src/bin/*.rs"):
            return [Action("run-bin", f"Run Binary '{stem}'", lambda c: self.c(c, "run", "--bin", stem),
                           opens="none")]
        if matches(rel_file, "examples/*.rs"):
            return [Action("run-example", f"Run Example '{stem}'", lambda c: self.c(c, "run", "--example", stem),
                           opens="none")]
        if matches(rel_file, "tests/*.rs"):
            return [Action("run-test", f"Run Test '{stem}'", lambda c: self.c(c, "test", "--test", stem),
                           opens="none")]
        if matches(rel_file, "benches/*.rs"):
            return [Action("run-bench", f"Run Benchmark '{stem}'", lambda c: self.c(c, "bench", "--bench", stem),
                           opens="none")]
        if rel_file == "Cargo.toml":
            return [a for a in self.actions(ctx) if isinstance(a, Action) and a.id in ("build", "add", "update")]
        return []


# ============================================================================ CMake
TARGET_RX = re.compile(r"^\s*(add_executable|qt_add_executable|qt6_add_executable|add_library|qt_add_library)"
                       r"\s*\(\s*([\w.+-]+)", re.M | re.I)


class CMake(Provider):
    """Configures with the IDE's CMake + MinGW into the IDE state folder (the CMake foreign adapter's build
    folder: the source tree stays clean)."""
    id, title, priority, icon = "cmake", "CMake", 35, ("CM", "#064F8C")
    markers = ("CMakeLists.txt",)

    def detect(self, folder, project):
        return (folder / "CMakeLists.txt").is_file()

    @staticmethod
    def adapter(ctx):
        a = getattr(ctx.project, "adapter", None)
        if a is not None and getattr(a, "kind", "") == "cmake":
            return a
        from ..foreign.cmake import CMakeAdapter
        return CMakeAdapter(ctx.folder / "CMakeLists.txt")

    @staticmethod
    def targets(folder: Path) -> list[tuple[str, str]]:
        out, seen = [], set()
        files = [folder / "CMakeLists.txt"] + sorted(p for p in folder.glob("*/**/CMakeLists.txt")
                                                     if not any(x in ("build", ".git", "out") for x in
                                                                p.relative_to(folder).parts[:-1]))
        for f in files[:50]:
            text = re.sub(r"#.*", "", read_text(f))
            for kind, name in TARGET_RX.findall(text):
                if name not in seen and not name.startswith("$"):
                    seen.add(name)
                    out.append((name, "exe" if "executable" in kind.lower() else "lib"))
        return out

    def configure(self, ctx, then=None):
        a = self.adapter(ctx)
        try:
            step = a.configure_step()
        except RuntimeError as e:
            ctx.log(f"*** {e}")
            return None
        return ctx.run_cli(step.argv, cwd=step.cwd, env=step.env, title="cmake configure",
                           on_done=(lambda r: r.exit_code == 0 and then()) if then else None)

    def build(self, ctx, target: str | None = None, clean_first: bool = False):
        a = self.adapter(ctx)

        def go_build():
            from ..foreign._others_base import find_cmake
            argv = [find_cmake() or "cmake", "--build", str(a.build_dir), "--config", a.config, "-j"]
            if target:
                argv += ["--target", target]
            if clean_first:
                argv.append("--clean-first")
            return ctx.run_cli(argv, env=a._env(), title=f"cmake --build {target or '(all)'}")
        if not (a.build_dir / "CMakeCache.txt").exists():
            return self.configure(ctx, then=go_build)
        return go_build()

    def clean(self, ctx):
        a = self.adapter(ctx)
        if not (a.build_dir / "CMakeCache.txt").exists():
            ctx.log("Nothing to clean (not configured yet)")
            return
        from ..foreign._others_base import find_cmake
        ctx.run_cli([find_cmake() or "cmake", "--build", str(a.build_dir), "--target", "clean"], env=a._env(),
                    title="cmake clean")

    def target_items(self, ctx) -> list:
        items = [Action(f"build-target.{n}", f"{n}  ({k})", lambda c, n=n: self.build(c, n), opens="none")
                 for n, k in self.targets(ctx.folder)]
        return items or [Action("no-targets", "(no add_executable / add_library found)", lambda c: None,
                                enabled=lambda c: False, palette=False)]

    def actions(self, ctx):
        return [Action("configure", "Configure", lambda c: self.configure(c), opens="none"),
                Action("build", "Build All", lambda c: self.build(c), opens="none", toolbar=True,
                       icon="SP_DialogApplyButton"),
                Submenu("Build Target", self.target_items(ctx)),
                Action("rebuild", "Rebuild All", lambda c: self.build(c, clean_first=True), opens="none"),
                Action("clean", "Clean", self.clean, opens="none"),
                Separator(),
                Action("ctest", "Run Tests (ctest)", self._ctest, opens="none"),
                Action("open-build", "Open Build Folder", lambda c: self._open_build(c), opens="none")]

    def _ctest(self, ctx):
        from ..foreign._others_base import find_cmake
        a = self.adapter(ctx)
        cm = find_cmake()
        ctest = str(Path(cm).with_name("ctest.exe" if cm.endswith(".exe") else "ctest")) if cm else "ctest"
        ctx.run_cli([ctest, "--test-dir", str(a.build_dir), "-C", a.config, "--output-on-failure"], env=a._env())

    def _open_build(self, ctx):
        import os
        a = self.adapter(ctx)
        a.build_dir.mkdir(parents=True, exist_ok=True)
        ctx.log(f"Build folder: {a.build_dir}")
        if hasattr(os, "startfile"):
            os.startfile(str(a.build_dir))  # noqa: S606

    def folder_actions(self, ctx, rel_folder):
        return self.actions(ctx) if rel_folder == "" else []

    def file_actions(self, ctx, rel_file):
        if Path(rel_file).name == "CMakeLists.txt":
            return [a for a in self.actions(ctx) if not isinstance(a, Separator) and
                    getattr(a, "id", "") in ("configure", "build")] + [Submenu("Build Target",
                                                                               self.target_items(ctx))]
        return []


PROVIDERS = [Flutter(), Go(), Rust(), CMake()]
