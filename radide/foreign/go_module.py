"""Go modules (go.mod) opened IN PLACE - File > Open Folder on any Go project.

* run targets: every ``package main`` directory of the module (``go run .``, ``go run ./cmd/server`` ...)
  plus ``go test ./...``; Ctrl+F5 / F5 run the startup target (Native > Startup target);
* Native menu: go build ./..., go vet ./..., go test ./..., go mod tidy, gofmt -l, go clean;
* Go syntax / keywords come from the Go plugin (radide/languages/go_bridge.py); the go tool is the one on
  PATH or the IDE's toolchain (%LOCALAPPDATA%\\RADIDE\\toolchains\\go\\bin).

The module stays authoritative: nothing is written into the folder (IDE state lives in
%LOCALAPPDATA%\\RADIDE\\foreign-state)."""
from __future__ import annotations

import re
from pathlib import Path

from ._others_base import ForeignAdapter, ForeignProject, RunTarget, Step, show_projects, source_files

SOURCE_EXT = (".go", ".mod", ".sum", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".html", ".tmpl", ".sql",
              ".proto")
MAIN_RX = re.compile(r"^package\s+main\b", re.M)


def go_tool() -> str:
    try:
        from ..languages import get_plugin
        t = get_plugin("go-bridge").tool()
        if t:
            return t
    except Exception:  # noqa: BLE001
        pass
    import shutil
    return shutil.which("go") or ""


class GoModuleAdapter(ForeignAdapter):
    kind = "go"
    title = "Go module"
    base_language = "go-bridge"

    def __init__(self, native: Path):
        native = Path(native).resolve()
        if native.is_dir():
            native = native / "go.mod"
        super().__init__(native, native.parent)
        self.module = ""

    def scan(self) -> None:
        r = self.root
        text = self.native.read_text(encoding="utf-8", errors="replace") if self.native.is_file() else ""
        m = re.search(r"^module\s+(\S+)", text, re.M)
        self.module = m.group(1) if m else r.name
        self.name = self.module.rsplit("/", 1)[-1] or r.name
        files = source_files(r, SOURCE_EXT)
        if "go.mod" in files:
            files.remove("go.mod")
            files.insert(0, "go.mod")
        self.modules = files
        mains: dict[str, str] = {}
        for f in files:
            if not f.endswith(".go") or f.endswith("_test.go"):
                continue
            try:
                head = (r / f).read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            if MAIN_RX.search(head):
                d = str(Path(f).parent.as_posix())
                mains.setdefault(d, f)
        for d in sorted(mains, key=lambda x: (x != ".", x)):
            pkg = "." if d == "." else "./" + d
            self.targets.append(RunTarget(f"go run {pkg}", "go", {"pkg": pkg}))
        if any(f.endswith("_test.go") for f in files):
            self.targets.append(RunTarget("go test ./...", "test", {}))
        self.info.append(f"Go module {self.module}: go = {self.tool() or 'not found (install Go)'}")

    def tool(self) -> str:
        return go_tool()

    def run_step(self, target, debug):
        if target is None:
            return None
        go = self.tool() or "go"
        if target.kind == "test":
            return Step([go, "test", "./..."], self.root, {}, target.name)
        return Step([go, "run", target.data.get("pkg", ".")], self.root, {}, target.name)

    def commands(self):
        go = self.tool() or "go"
        r = self.root
        out = [(f"go {' '.join(a)}", [Step([go, *a], r, {}, "go")])
               for a in (["build", "./..."], ["vet", "./..."], ["test", "./..."], ["mod", "tidy"], ["clean"])]
        gofmt = str(Path(go).with_name("gofmt.exe" if go.lower().endswith(".exe") else "gofmt")) if go != "go" \
            else "gofmt"
        out.append(("gofmt -l .", [Step([gofmt, "-l", "."], r, {}, "gofmt")]))
        return out


def open_go(win, path: Path) -> bool:
    p = Path(path)
    manifest = p / "go.mod" if p.is_dir() else p
    if not manifest.is_file():
        return False
    project = ForeignProject(GoModuleAdapter(manifest))
    return show_projects(win, [project], project.name, manifest)


def probe(folder: Path):
    f = Path(folder) / "go.mod"
    return f if f.is_file() else None


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format(["go.mod"], open_go, "Go module (go.mod)", folder_probe=probe, name="go-module", priority=5)


__all__ = ["GoModuleAdapter", "open_go", "register"]
