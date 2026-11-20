"""CMake projects (CMakeLists.txt) opened IN PLACE.

Configure + build with cmake and MinGW (gcc/g++/mingw32-make from %LOCALAPPDATA%\\RADIDE\\toolchains\\mingw64,
cmake from PATH or %LOCALAPPDATA%\\RADIDE\\tools\\cmake) into the IDE state folder (nothing is written into
the source tree); targets come from the CMake File API (codemodel-v2) after configure, from add_executable /
add_library before. Run = the target's executable; Debug = gdb over DAP. Qt .ui files of the project are
designed in place (radide/foreign/qt_ui.py)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from ._others_base import (ChainSession, ForeignAdapter, ForeignProject, LazyStep, RunTarget, Step, find_cmake,
                           find_gdb, gdb_session, mingw_bin, show_projects, source_files, tool_env)

TARGET_RX = re.compile(r"^\s*(add_executable|qt_add_executable|qt6_add_executable|add_library|qt_add_library)"
                       r"\s*\(\s*([\w.+-]+)([^)]*)", re.M | re.I)


def _strip_comments(text: str) -> str:
    return re.sub(r"#\[\[.*?\]\]|#[^\n]*", "", text, flags=re.S)


class CMakeAdapter(ForeignAdapter):
    kind = "cmake"
    title = "CMake project"
    base_language = "cpp-bridge"

    def __init__(self, native: Path, config: str = "Debug"):
        native = Path(native).resolve()
        if native.is_dir():
            native = native / "CMakeLists.txt"
        super().__init__(native, native.parent)
        self.config = config
        self.build_dir = self.state / f"build-{config.lower()}"

    def scan(self) -> None:
        text = _strip_comments(self.native.read_text(encoding="utf-8", errors="replace"))
        m = re.search(r"^\s*project\s*\(\s*([\w.+-]+)", text, re.M | re.I)
        if m:
            self.name = m.group(1)
        files = source_files(self.root, (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".cmake",
                                         ".txt", ".json", ".ui", ".qrc", ".md", ".in"))
        self.modules = [f for f in files if not f.endswith(".ui")]
        cpp = any(f.endswith((".cpp", ".cc", ".cxx")) for f in files)
        self.base_language = "c-bridge" if not cpp and any(f.endswith(".c") for f in files) else "cpp-bridge"
        uis = [self.root / f for f in files if f.endswith(".ui")]
        if uis:
            from .qt_ui import ui_bindings
            ui_bindings(self, uis)
        self._targets_from_api() or self._targets_from_text()
        cm = find_cmake()
        self.info.append(f"cmake: {cm or 'not found'}; compilers: {mingw_bin() or 'MinGW not found'}; "
                         f"build folder: {self.build_dir}")
        if (self.root / "CMakePresets.json").exists():
            self.info.append("CMakePresets.json found - the IDE configures with MinGW Makefiles "
                             f"({self.config}); use Native > cmake --preset for the presets")

    def _targets_from_text(self) -> bool:
        seen = []
        for f in [self.native] + sorted(self.root.rglob("CMakeLists.txt")):
            if any(part in ("build", ".git") for part in f.relative_to(self.root).parts[:-1]):
                continue
            try:
                text = _strip_comments(f.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
            for kind, name, _rest in TARGET_RX.findall(text):
                if name in seen or name.startswith("${"):
                    continue
                seen.append(name)
                if "executable" in kind.lower():
                    self.targets.append(RunTarget(name, "exe", {"target": name}))
        return bool(self.targets)

    def _targets_from_api(self) -> bool:
        reply = self.build_dir / ".cmake" / "api" / "v1" / "reply"
        idx = sorted(reply.glob("index-*.json")) if reply.is_dir() else []
        if not idx:
            return False
        try:
            index = json.loads(idx[-1].read_text(encoding="utf-8"))
            cm_file = index["reply"]["codemodel-v2"]["jsonFile"]
            cm = json.loads((reply / cm_file).read_text(encoding="utf-8"))
            self.artifacts = {}
            for cfg in cm.get("configurations", []):
                for t in cfg.get("targets", []):
                    td = json.loads((reply / t["jsonFile"]).read_text(encoding="utf-8"))
                    if td.get("type") == "EXECUTABLE":
                        arts = [a["path"] for a in td.get("artifacts", [])]
                        if arts:
                            self.artifacts[td["name"]] = self.build_dir / arts[0]
                        if not any(x.name == td["name"] for x in self.targets):
                            self.targets.append(RunTarget(td["name"], "exe", {"target": td["name"]}))
            return bool(self.targets)
        except (OSError, ValueError, KeyError):
            return False

    # ------------------------------------------------------------ build / run
    def tool(self) -> str:
        return find_cmake()

    def _env(self) -> dict:
        return tool_env()

    def configure_step(self) -> Step:
        cm = find_cmake()
        if not cm:
            raise RuntimeError("cmake was not found - install CMake or let the IDE download it "
                               "(Tools > Options > Toolchains)")
        q = self.build_dir / ".cmake" / "api" / "v1" / "query"
        q.mkdir(parents=True, exist_ok=True)
        (q / "codemodel-v2").touch()
        args = [cm, "-S", str(self.root), "-B", str(self.build_dir), f"-DCMAKE_BUILD_TYPE={self.config}",
                "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON"]
        cache = self.build_dir / "CMakeCache.txt"
        if not cache.exists():
            mb = mingw_bin()
            if mb:
                args += ["-G", "MinGW Makefiles", f"-DCMAKE_C_COMPILER={Path(mb) / 'gcc.exe'}",
                         f"-DCMAKE_CXX_COMPILER={Path(mb) / 'g++.exe'}",
                         f"-DCMAKE_MAKE_PROGRAM={Path(mb) / 'mingw32-make.exe'}"]
        return Step(args, self.root, self._env(), "cmake configure")

    def _needs_configure(self) -> bool:
        cache = self.build_dir / "CMakeCache.txt"
        if not cache.exists():
            return True
        t = cache.stat().st_mtime
        return any(f.stat().st_mtime > t for f in self.root.rglob("CMakeLists.txt")
                   if "build" not in f.relative_to(self.root).parts[:-1])

    def build_steps(self, target, debug):
        cm = find_cmake()
        steps = [self.configure_step()] if self._needs_configure() else []
        args = [cm, "--build", str(self.build_dir), "-j", str(os.cpu_count() or 2)]
        if target is not None and target.kind == "exe":
            args += ["--target", target.data["target"]]
        steps.append(Step(args, self.root, self._env(), "cmake --build"))
        return steps

    def exe_path(self, name: str) -> Path:
        self._targets_from_api()
        p = getattr(self, "artifacts", {}).get(name)
        if p is not None:
            return p
        hits = sorted(self.build_dir.rglob(f"{name}.exe")) or sorted(self.build_dir.rglob(name))
        return hits[0] if hits else self.build_dir / f"{name}.exe"

    def run_step(self, target, debug):
        if target is None:
            return None
        return LazyStep(lambda: [str(self.exe_path(target.data["target"]))], self.root, self._env(),
                        f"run {target.name}")

    def debug_session(self, win, target, pre):
        if not find_gdb():
            return None
        return ChainSession(pre, lambda: gdb_session(win, self.exe_path(target.data["target"]), [], self.root,
                                                     self._env()), win)

    def commands(self):
        cm = find_cmake()
        out = []
        if cm:
            out.append(("Configure (cmake)", [self.configure_step()]))
            out.append(("Build all", [Step([cm, "--build", str(self.build_dir), "-j", str(os.cpu_count() or 2)],
                                           self.root, self._env(), "cmake --build")]))
            for t in self.targets:
                out.append((f"Build {t.name}", self.build_steps(t, False)))
            out.append(("Clean", [Step([cm, "--build", str(self.build_dir), "--target", "clean"], self.root,
                                       self._env(), "clean")]))
            ctest = Path(cm).with_name("ctest.exe" if os.name == "nt" else "ctest")
            if ctest.exists():
                out.append(("Run tests (ctest)", [Step([str(ctest), "--test-dir", str(self.build_dir),
                                                        "--output-on-failure"], self.root, self._env(), "ctest")]))
            presets = self.root / "CMakePresets.json"
            if presets.exists():
                try:
                    for p in json.loads(presets.read_text(encoding="utf-8")).get("configurePresets", []):
                        if not p.get("hidden"):
                            out.append((f"cmake --preset {p['name']}", [Step([cm, "--preset", p["name"]], self.root,
                                                                              self._env(), "preset")]))
                except (OSError, ValueError, KeyError):
                    pass
        try:
            from .vscode_folder import vscode_commands
            out += vscode_commands(self.root)
        except Exception:  # noqa: BLE001
            pass
        return out


def open_cmake(win, path: Path) -> bool:
    adapter = CMakeAdapter(Path(path))
    project = ForeignProject(adapter)
    return show_projects(win, [project], project.name, adapter.native)


def probe(folder: Path):
    f = Path(folder) / "CMakeLists.txt"
    return f if f.exists() else None


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format(["CMakeLists.txt"], open_cmake, "CMake project (CMakeLists.txt)", folder_probe=probe,
                    name="cmake", priority=5)
