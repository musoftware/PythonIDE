"""Python projects of other tools opened IN PLACE: pyproject.toml (PEP 621, Poetry, Hatch, PDM,
setuptools), setup.py / setup.cfg, requirements.txt, Pipfile.

* interpreter: the project's own virtual environment (.venv / venv / env, Poetry/Pipenv in-project
  envs), else the Python on PATH;
* run targets: [project.scripts] / [tool.poetry.scripts] entry points, ``python -m <package>`` for
  packages with __main__.py, manage.py (Django), scripts with ``if __name__ == "__main__"``;
* debug = debugpy; tests = pytest (or unittest); Native menu: create venv, install requirements /
  the project (pip install -e .), poetry/pipenv install, pytest, VS Code tasks;
* Qt Designer .ui files of the project are designed in place (radide/foreign/qt_ui.py)."""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from ._others_base import (ChainSession, ForeignAdapter, ForeignProject, RunTarget, Step, debugpy_session,
                           show_projects, source_files)

try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11
    tomllib = None

MAIN_RX = re.compile(r"^if\s+__name__\s*==\s*['\"]__main__['\"]\s*:", re.M)
MARKERS = ("pyproject.toml", "setup.py", "setup.cfg", "Pipfile", "requirements.txt")


def detect(folder: Path) -> Path | None:
    for m in MARKERS:
        if (Path(folder) / m).exists():
            return Path(folder) / m
    return None


def venv_python(root: Path) -> str:
    for d in (".venv", "venv", "env", ".env"):
        for exe in (root / d / "Scripts" / "python.exe", root / d / "bin" / "python"):
            if exe.exists():
                return str(exe)
    return ""


class PythonProjectAdapter(ForeignAdapter):
    kind = "python"
    title = "Python project"
    base_language = "python-tk"

    def __init__(self, native: Path):
        native = Path(native).resolve()
        super().__init__(native, native if native.is_dir() else native.parent)
        self.tool_name = "pip"
        self.deps: list[str] = []
        self.src_root = self.root

    def scan(self) -> None:
        r = self.root
        data = {}
        pp = r / "pyproject.toml"
        if pp.exists() and tomllib is not None:
            try:
                data = tomllib.loads(pp.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
        proj = data.get("project") or {}
        poetry = (data.get("tool") or {}).get("poetry") or {}
        self.name = proj.get("name") or poetry.get("name") or self._setup_name() or r.name
        scripts = dict(proj.get("scripts") or {})
        scripts.update(poetry.get("scripts") or {})
        self.deps = [str(d) for d in (proj.get("dependencies") or [])] + list((poetry.get("dependencies") or {}))
        req = r / "requirements.txt"
        if req.exists():
            self.deps += [ln.strip() for ln in req.read_text(encoding="utf-8", errors="replace").splitlines()
                          if ln.strip() and not ln.startswith(("#", "-"))]
        if poetry:
            self.tool_name = "poetry"
            self.title = "Poetry project"
        elif (r / "Pipfile").exists():
            self.tool_name = "pipenv"
            self.title = "Pipenv project"
        elif "hatch" in (data.get("tool") or {}):
            self.title = "Hatch project"
        elif "pdm" in (data.get("tool") or {}):
            self.title = "PDM project"
        low = " ".join(self.deps).lower()
        if any(k in low for k in ("pyside6", "pyqt6", "pyqt5", "pyside2")):
            self.base_language = "python-qt"
        self.src_root = r / "src" if (r / "src").is_dir() else r
        files = source_files(r, (".py", ".pyw", ".toml", ".cfg", ".txt", ".md", ".ini", ".ui", ".qrc", ".json"),
                             extra_names=("Pipfile",))
        self.modules = [f for f in files if not f.endswith(".ui")]
        for m in reversed(MARKERS):
            if m in self.modules:
                self.modules.remove(m)
                self.modules.insert(0, m)
        uis = [r / f for f in files if f.endswith(".ui")]
        if uis:
            from .qt_ui import ui_bindings
            ui_bindings(self, uis)
        # targets
        for name, spec in scripts.items():
            spec = spec if isinstance(spec, str) else (spec.get("reference", "") if isinstance(spec, dict) else "")
            if ":" in spec:
                self.targets.append(RunTarget(f"{name} (entry point)", "entry", {"spec": spec}))
        for init in sorted(self.src_root.glob("*/__main__.py")):
            self.targets.append(RunTarget(f"python -m {init.parent.name}", "module", {"module": init.parent.name}))
        if (r / "manage.py").exists():
            self.targets.append(RunTarget("manage.py runserver", "script", {"script": "manage.py",
                                                                           "args": ["runserver", "--noreload"]}))
        for f in files:
            if not f.endswith((".py", ".pyw")) or f.count("/") > 2 or "/tests/" in f"/{f}" or \
                    Path(f).name.startswith("test_") or f == "manage.py" or Path(f).name == "setup.py":
                continue
            try:
                text = (r / f).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if MAIN_RX.search(text):
                self.targets.append(RunTarget(f, "script", {"script": f}))
        if self._has_tests():
            self.targets.append(RunTarget("tests", "tests", {}))
        py = self.tool()
        self.info.append(f"{self.title}: interpreter {py}"
                         f"{' (project venv)' if venv_python(r) else ' (no venv in the project - Native > Create venv)'}")

    def _setup_name(self) -> str:
        for f, rx in (("setup.cfg", r"^\s*name\s*=\s*([\w.-]+)"), ("setup.py", r"name\s*=\s*['\"]([\w.-]+)")):
            p = self.root / f
            if p.exists():
                m = re.search(rx, p.read_text(encoding="utf-8", errors="replace"), re.M)
                if m:
                    return m.group(1)
        return ""

    def _has_tests(self) -> bool:
        return (self.root / "tests").is_dir() or (self.root / "test").is_dir() or \
            any(self.root.glob("test_*.py"))

    def tool(self) -> str:
        return venv_python(self.root) or shutil.which("python") or sys.executable

    def _env(self) -> dict:
        import os
        paths = [str(self.src_root)] + ([str(self.root)] if self.src_root != self.root else [])
        return {"PYTHONPATH": os.pathsep.join(paths + [os.environ.get("PYTHONPATH", "")]).rstrip(os.pathsep),
                "PYTHONUNBUFFERED": "1"}

    def run_step(self, target, debug):
        if target is None:
            return None
        py = self.tool()
        d = target.data
        if target.kind == "entry":
            mod, func = d["spec"].split(":", 1)
            code = f"import sys; from {mod} import {func.split('.')[0]} as _f; sys.exit(_f{'.' + func.split('.', 1)[1] if '.' in func else ''}())"
            return Step([py, "-c", code], self.root, self._env(), target.name)
        if target.kind == "module":
            return Step([py, "-m", d["module"]], self.root, self._env(), target.name)
        if target.kind == "tests":
            if self._pytest_available(py):
                return Step([py, "-m", "pytest", "-q"], self.root, self._env(), "pytest")
            return Step([py, "-m", "unittest", "discover", "-v"], self.root, self._env(), "unittest")
        return Step([py, str(self.root / d["script"])] + list(d.get("args", [])), self.root, self._env(), target.name)

    @staticmethod
    def _pytest_available(py: str) -> bool:
        import subprocess
        try:
            return subprocess.run([py, "-c", "import pytest"], capture_output=True, timeout=20).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def debug_session(self, win, target, pre):
        py = self.tool()
        d = target.data
        step = self.run_step(target, True)
        if target.kind == "script":
            return ChainSession(pre, lambda: debugpy_session(win, py, self.root / d["script"], d.get("args", []),
                                                             self.root, step.env), win)
        if target.kind in ("module", "tests", "entry"):
            module, args = (d.get("module"), []) if target.kind == "module" else \
                (("pytest", ["-q"]) if target.kind == "tests" else (None, []))
            if module is None:
                return None

            def make():
                s = debugpy_session(win, py, self.root / "__main__.py", args, self.root, step.env)
                if s is not None:
                    s.launch_args.pop("program", None)
                    s.launch_args["module"] = module
                return s
            return ChainSession(pre, make, win)
        return None

    def commands(self):
        r = self.root
        base = shutil.which("python") or sys.executable
        py = self.tool()
        out = []
        if not venv_python(r):
            out.append(("Create virtual environment (.venv)", [Step([base, "-m", "venv", ".venv"], r, {}, "venv")]))
        if (r / "requirements.txt").exists():
            out.append(("pip install -r requirements.txt",
                        [Step([py, "-m", "pip", "install", "-r", "requirements.txt"], r, {}, "pip")]))
        if (r / "pyproject.toml").exists() or (r / "setup.py").exists():
            out.append(("pip install -e . (editable)", [Step([py, "-m", "pip", "install", "-e", "."], r, {}, "pip")]))
        if self.tool_name == "poetry" and shutil.which("poetry"):
            out.append(("poetry install", [Step([shutil.which("poetry"), "install"], r, {}, "poetry")]))
        if self.tool_name == "pipenv" and shutil.which("pipenv"):
            out.append(("pipenv install", [Step([shutil.which("pipenv"), "install"], r, {}, "pipenv")]))
        if self._has_tests():
            out.append(("Run tests (pytest)", [Step([py, "-m", "pytest", "-q"], r, self._env(), "pytest")]))
        out.append(("Build sdist/wheel (python -m build)", [Step([py, "-m", "build"], r, {}, "build")]))
        try:
            from .vscode_folder import vscode_commands
            out += vscode_commands(r)
        except Exception:  # noqa: BLE001
            pass
        return out


def open_python(win, path: Path) -> bool:
    p = Path(path)
    adapter = PythonProjectAdapter(p if p.is_file() else (detect(p) or p))
    project = ForeignProject(adapter)
    return show_projects(win, [project], project.name, p)


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format(["pyproject.toml", "setup.py", "setup.cfg", "Pipfile"], open_python,
                    "Python project (pyproject.toml / setup.py / Pipfile)", folder_probe=detect, name="python-project",
                    priority=-5)
    register_format(["requirements.txt"], open_python, "Python requirements.txt folder", name="python-requirements",
                    priority=-6)
