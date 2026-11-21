"""Loose C# / Java / Go source files (no .csproj / build file / go.mod) opened IN PLACE.

File > Open Folder on a folder of programs with their own ``Main`` / ``main`` (radide/project_detect.py
offers "Open in place" for them): the RAD IDE bridge plugins generate their own entry point, so these
folders run through a build that lives entirely in the IDE state folder
(%LOCALAPPDATA%\\RADIDE\\foreign-state\\...), never in the user's folder:

* C#   - a generated ``Loose.csproj`` in the state folder compiles ``<folder>/**/*.cs``; ``dotnet run``;
* Java - ``javac -d <state>/classes`` + ``java -cp <state>/classes <MainClass>``;
* Go   - ``go run <the .go files of the folder>``;
* scripts (Lua, Perl, Ruby, PowerShell, Dart) - each top-level script is a run target
  (``lua main.lua``, ``perl tool.pl``, ``ruby run.rb``, ``powershell -File build.ps1``, ``dart run bin/x.dart``)
  with the interpreter the language plugin finds (PATH or the IDE toolchains).

Not registered as a folder probe (a plain folder with a few scripts stays a plain folder unless the user
picks it in the Open Folder dialog)."""
from __future__ import annotations

import re
from pathlib import Path

from ._others_base import ForeignAdapter, ForeignProject, RunTarget, Step, show_projects, source_files

LANGS = {
    "csharp": {"ext": (".cs",), "title": "C# files", "base": "csharp-bridge",
               "main": re.compile(r"static\s+(?:async\s+)?(?:void|int|Task(?:<int>)?)\s+Main\s*\(")},
    "java": {"ext": (".java",), "title": "Java files", "base": "java-bridge",
             "main": re.compile(r"static\s+void\s+main\s*\(")},
    "go": {"ext": (".go",), "title": "Go files", "base": "go-bridge", "main": re.compile(r"^func\s+main\s*\(", re.M)},
    # scripts: every script of the folder (two levels) runs with the plugin's interpreter
    "lua": {"ext": (".lua",), "title": "Lua scripts", "base": "lua-bridge", "script": []},
    "perl": {"ext": (".pl",), "title": "Perl scripts", "base": "perl-bridge", "script": []},
    "ruby": {"ext": (".rb",), "title": "Ruby scripts", "base": "ruby-bridge", "script": []},
    "powershell": {"ext": (".ps1",), "title": "PowerShell scripts", "base": "powershell-bridge",
                   "script": ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]},
    "dart": {"ext": (".dart",), "title": "Dart programs", "base": "dart-bridge", "script": ["run"],
             "main": re.compile(r"\bvoid\s+main\s*\(")},
}
CSPROJ = """<Project Sdk="Microsoft.NET.Sdk">
  <!-- RAD IDE: builds the loose .cs files of {root} (generated in the IDE state folder, not in yours) -->
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>{tfm}</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>disable</Nullable>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
    <AssemblyName>{name}</AssemblyName>
    <RootNamespace>{name}</RootNamespace>{startup}
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="{root}\\**\\*.cs" Exclude="{root}\\bin\\**;{root}\\obj\\**;{root}\\_build\\**" />
  </ItemGroup>
</Project>
"""


class LooseSourcesAdapter(ForeignAdapter):
    kind = "loose"

    def __init__(self, folder: Path, lang: str):
        folder = Path(folder).resolve()
        super().__init__(folder, folder)
        self.lang = lang
        spec = LANGS[lang]
        self.title = f"{spec['title']} (no project file)"
        self.base_language = spec["base"]
        self.files: list[str] = []

    def scan(self) -> None:
        spec = LANGS[self.lang]
        skip = (".git", ".idea", ".vscode", "node_modules", "build", "out", "target", "obj", "__pycache__",
                ".venv", "venv", "dist", ".radide", ".dart_tool", "lua_modules", "vendor", "_build")
        if self.lang not in ("dart", "ruby", "perl"):          # bin/ holds the programs of Dart / Ruby / Perl
            skip += ("bin",)
        self.files = source_files(self.root, spec["ext"], skip_dirs=skip, limit=2000)
        self.modules = list(self.files)
        if "script" in spec:
            self._script_targets(spec)
            self.info.append(f"{self.title}: interpreter {self.tool() or 'not found'}")
            return
        for f in self.files:
            try:
                text = (self.root / f).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if spec["main"].search(text):
                if self.lang == "java":
                    pkg = re.search(r"^\s*package\s+([\w.]+)\s*;", text, re.M)
                    cls = (pkg.group(1) + "." if pkg else "") + Path(f).stem
                    self.targets.append(RunTarget(f"java {cls}", "java", {"main": cls, "file": f}))
                elif self.lang == "csharp":
                    cls = re.search(r"\b(?:class|struct)\s+(\w+)", text)
                    ns = re.search(r"^\s*namespace\s+([\w.]+)", text, re.M)
                    full = (ns.group(1) + "." if ns else "") + (cls.group(1) if cls else Path(f).stem)
                    self.targets.append(RunTarget(f"dotnet run ({Path(f).name})", "cs", {"startup": full, "file": f}))
                else:
                    d = str(Path(f).parent.as_posix())
                    if not any(t.data.get("dir") == d for t in self.targets):
                        self.targets.append(RunTarget(f"go run ({d}/*.go)" if d != "." else "go run (*.go)", "go",
                                                      {"dir": d}))
        self.info.append(f"{self.title}: built in the IDE state folder {self.state}")

    def _script_targets(self, spec) -> None:
        names = ("main", "app", "run", "start", "index", "program", "server")
        files = [f for f in self.files if f.count("/") <= 1 and not Path(f).name.startswith(("_", "test_"))
                 and "/lib/" not in f"/{f}"]
        if spec.get("main") is not None:
            files = [f for f in files if spec["main"].search(self._read(f))]
        files.sort(key=lambda f: (Path(f).stem.lower() not in names, f.count("/"), f.lower()))
        for f in files[:30]:
            self.targets.append(RunTarget(f, "script", {"file": f}))

    def _read(self, f: str) -> str:
        try:
            return (self.root / f).read_text(encoding="utf-8", errors="replace")[:60_000]
        except OSError:
            return ""

    # -- tools
    def tool(self) -> str:
        if "script" in LANGS[self.lang]:
            try:
                from ..languages import get_plugin
                return get_plugin(LANGS[self.lang]["base"]).tool() or ""
            except Exception:  # noqa: BLE001
                return ""
        try:
            if self.lang == "csharp":
                from ..languages.csharp_bridge import dotnet
                return dotnet()
            if self.lang == "java":
                from ..languages.java_bridge import _tool
                return _tool("javac")
            from .go_module import go_tool
            return go_tool()
        except Exception:  # noqa: BLE001
            return ""

    def _csproj(self, target) -> Path:
        from ..languages.csharp_bridge import target_framework
        name = re.sub(r"\W", "_", self.root.name) or "Loose"
        if not name[0].isalpha():
            name = "App_" + name
        many = sum(1 for t in self.targets if t.kind == "cs") > 1
        startup = f"\n    <StartupObject>{target.data['startup']}</StartupObject>" if many and target else ""
        d = self.state / "csharp"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "Loose.csproj"
        text = CSPROJ.format(root=str(self.root), tfm=target_framework(), name=name, startup=startup)
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            p.write_text(text, encoding="utf-8")
        return p

    def build_steps(self, target, debug):
        if self.lang == "java" and target is not None:
            javac = self.tool() or "javac"
            out = self.state / "java" / "classes"
            out.mkdir(parents=True, exist_ok=True)
            return [Step([javac, "-encoding", "UTF-8", "-d", str(out), *[str(self.root / f) for f in self.files]],
                         self.root, {}, "javac")]
        return []

    def run_step(self, target, debug):
        if target is None:
            return None
        spec = LANGS[self.lang]
        if "script" in spec:
            return Step([self.tool() or self.lang, *spec["script"], target.data["file"]], self.root, {}, target.name)
        if self.lang == "csharp":
            proj = self._csproj(target)
            return Step([self.tool() or "dotnet", "run", "--project", str(proj)], self.root, {}, target.name)
        if self.lang == "java":
            from ..languages.java_bridge import _tool
            java = _tool("java") or "java"
            return Step([java, "-cp", str(self.state / "java" / "classes"), target.data["main"]], self.root, {},
                        target.name)
        d = target.data.get("dir", ".")
        files = [str(self.root / f) for f in self.files if str(Path(f).parent.as_posix()) == d
                 and not f.endswith("_test.go")]
        return Step([self.tool() or "go", "run", *files], self.root / d, {}, target.name)


def open_loose(win, folder, lang: str) -> bool:
    if lang not in LANGS:
        return False
    project = ForeignProject(LooseSourcesAdapter(Path(folder), lang))
    if not project.adapter.targets:
        return False
    return show_projects(win, [project], project.name, Path(folder))


__all__ = ["LooseSourcesAdapter", "open_loose", "LANGS"]
