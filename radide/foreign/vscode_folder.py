"""VS Code folders (.vscode/tasks.json, launch.json, settings.json) and *.code-workspace multi-root
workspaces opened IN PLACE.

* tasks.json -> commands of the Native menu (shell/process/npm tasks, dependsOn, windows overrides,
  ${workspaceFolder} & co.); every other foreign adapter also shows them (``vscode_commands``).
* launch.json -> run targets: python/debugpy (debugged with debugpy), cppdbg/cppvsdbg/gdb/lldb
  (gdb over DAP), node/pwa-node, coreclr (dotnet), java (mainClass); preLaunchTask runs first.
* a .code-workspace opens every folder as a project of one solution; folders that are CMake / Java /
  Python projects use those adapters."""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

from ._others_base import (ChainSession, ForeignAdapter, ForeignProject, RunTarget, Step, debugpy_session,
                           find_java, gdb_session, load_jsonc, show_projects, source_files, tool_env)

CODE_EXTS = (".py", ".js", ".ts", ".tsx", ".jsx", ".c", ".cpp", ".h", ".hpp", ".cs", ".java", ".go", ".rs",
             ".php", ".rb", ".lua", ".json", ".md", ".html", ".css", ".toml", ".yml", ".yaml", ".txt", ".sh",
             ".ps1", ".bat", ".cmd")


def _subst(value, root: Path, extra: dict | None = None):
    if isinstance(value, list):
        return [_subst(v, root, extra) for v in value]
    if isinstance(value, dict):
        return {k: _subst(v, root, extra) for k, v in value.items()}
    if not isinstance(value, str):
        return value
    table = {"workspaceFolder": str(root), "workspaceRoot": str(root), "workspaceFolderBasename": root.name,
             "cwd": str(root), "pathSeparator": os.sep, "/": os.sep, "userHome": str(Path.home()),
             "execPath": "code", "defaultBuildTask": ""}
    table.update(extra or {})

    def rep(m):
        key = m.group(1)
        if key.startswith("env:"):
            return os.environ.get(key[4:], "")
        if key.startswith("config:"):
            return ""
        if key.startswith("workspaceFolder:"):
            return str(root)
        return table.get(key, m.group(0))
    return re.sub(r"\$\{([^}]+)\}", rep, value)


def _platform(d: dict) -> dict:
    over = d.get("windows" if os.name == "nt" else ("osx" if sys.platform == "darwin" else "linux"))
    if isinstance(over, dict):
        d = {**d, **over}
        if "options" in over and "options" in d:
            d["options"] = {**(d.get("options") or {}), **over["options"]}
    return d


def _quote(a) -> str:
    if isinstance(a, dict):                       # {"value": ..., "quoting": ...}
        a = a.get("value", "")
    a = str(a)
    return f'"{a}"' if (" " in a and not a.startswith('"')) else a


def load_tasks(root: Path) -> list[dict]:
    f = Path(root) / ".vscode" / "tasks.json"
    if not f.exists():
        return []
    try:
        d = load_jsonc(f)
    except (OSError, ValueError):
        return []
    tasks = d.get("tasks") or []
    base_opts = d.get("options") or {}
    out = []
    for t in tasks:
        if isinstance(t, dict):
            t = _platform(t)
            if base_opts:
                t = {**t, "options": {**base_opts, **(t.get("options") or {})}}
            out.append(t)
    return out


def _task_label(t: dict) -> str:
    if t.get("label"):
        return str(t["label"])
    if t.get("type") == "npm":
        return f"npm: {t.get('script', '')}"
    return str(t.get("command") or t.get("taskName") or "task")


def task_steps(root: Path, label: str, tasks: list[dict] | None = None, seen=None) -> list[Step]:
    """The commands of a task (its dependsOn tasks first)."""
    tasks = load_tasks(root) if tasks is None else tasks
    seen = seen or set()
    t = next((x for x in tasks if _task_label(x) == label), None)
    if t is None or label in seen:
        return []
    seen.add(label)
    steps: list[Step] = []
    deps = t.get("dependsOn") or []
    for dep in [deps] if isinstance(deps, str) else deps:
        steps += task_steps(root, dep if isinstance(dep, str) else dep.get("label", ""), tasks, seen)
    opts = _subst(t.get("options") or {}, root)
    cwd = Path(opts.get("cwd") or root)
    env = {str(k): str(v) for k, v in (opts.get("env") or {}).items()}
    env = {**tool_env(), **env}
    typ = t.get("type", "process" if t.get("command") and not t.get("isShellCommand") else "shell")
    if typ == "npm":
        npm = shutil.which("npm") or "npm"
        path = t.get("path")
        steps.append(Step([npm, "run", str(t.get("script", ""))], root / path if path else root, env, label))
        return steps
    cmd = _subst(t.get("command"), root)
    if not cmd:
        return steps
    args = [_subst(a, root) for a in (t.get("args") or [])]
    if typ == "process":
        steps.append(Step([cmd] + [a.get("value", "") if isinstance(a, dict) else str(a) for a in args], cwd, env,
                          label))
    else:
        # VS Code: a command without args is a complete command line; with args it is one word
        line = cmd if not args else " ".join([_quote(cmd)] + [_quote(a) for a in args])
        shell = (opts.get("shell") or {}).get("executable")
        if shell:
            sargs = (opts.get("shell") or {}).get("args") or (["-Command"] if "powershell" in shell.lower() or
                                                              "pwsh" in shell.lower() else ["-c"])
            steps.append(Step([shell] + list(sargs) + [line], cwd, env, label))
        elif os.name == "nt":
            steps.append(Step(["cmd.exe", "/d", "/s", "/c", line], cwd, env, label))
        else:
            steps.append(Step(["/bin/sh", "-c", line], cwd, env, label))
    return steps


def vscode_commands(root: Path) -> list[tuple[str, list[Step]]]:
    """Native-menu commands for the tasks of a folder's .vscode/tasks.json."""
    tasks = load_tasks(root)
    out = []
    for t in tasks:
        label = _task_label(t)
        try:
            steps = task_steps(root, label, tasks)
        except Exception:  # noqa: BLE001
            continue
        if steps:
            out.append((f"Task: {label}", steps))
    return out


def load_launch(root: Path) -> list[dict]:
    f = Path(root) / ".vscode" / "launch.json"
    if not f.exists():
        return []
    try:
        d = load_jsonc(f)
    except (OSError, ValueError):
        return []
    return [_platform(c) for c in d.get("configurations") or [] if isinstance(c, dict) and c.get("request",
                                                                                                    "launch") == "launch"]


def folder_python(root: Path, settings: dict | None = None) -> str:
    s = settings or {}
    for key in ("python.defaultInterpreterPath", "python.pythonPath"):
        v = s.get(key)
        if v:
            p = Path(_subst(v, root))
            if p.exists():
                return str(p)
    for d in (".venv", "venv", "env"):
        for exe in (root / d / "Scripts" / "python.exe", root / d / "bin" / "python"):
            if exe.exists():
                return str(exe)
    return shutil.which("python") or sys.executable


class VSCodeFolderAdapter(ForeignAdapter):
    kind = "vscode"
    title = "VS Code folder"
    base_language = "python-tk"

    def __init__(self, native: Path):
        native = Path(native).resolve()
        root = native.parent if native.name == ".vscode" else (native if native.is_dir() else native.parent)
        super().__init__(native, root)

    def scan(self) -> None:
        self.settings = {}
        sf = self.root / ".vscode" / "settings.json"
        if sf.exists():
            try:
                self.settings = load_jsonc(sf)
            except (OSError, ValueError):
                self.settings = {}
        exclude = self.settings.get("files.exclude") or {}
        skip = {k.strip("*/") for k, v in exclude.items() if v and "/" not in k.strip("*/")}
        files = source_files(self.root, CODE_EXTS)
        self.modules = [f for f in files if not any(part in skip for part in f.split("/"))]
        if (self.root / ".vscode" / "tasks.json").exists():
            self.modules.insert(0, ".vscode/tasks.json")
        if (self.root / ".vscode" / "launch.json").exists():
            self.modules.insert(0, ".vscode/launch.json")
        exts = [Path(f).suffix for f in files]
        for ext, lang in ((".py", "python-tk"), (".ts", "typescript"), (".js", "javascript"), (".cpp", "cpp-bridge"),
                          (".c", "c-bridge"), (".cs", "csharp-bridge"), (".java", "java-bridge")):
            if ext in exts:
                self.base_language = lang
                break
        for c in load_launch(self.root):
            self.targets.append(RunTarget(str(c.get("name", c.get("type", "launch"))), "launch", c))
        if not self.targets:
            for t in load_tasks(self.root):
                g = t.get("group")
                if g == "test" or (isinstance(g, dict) and g.get("kind") in ("build", "test")) or g == "build":
                    self.targets.append(RunTarget(f"Task: {_task_label(t)}", "task", {"label": _task_label(t)}))
        self.info.append(f"{len(load_tasks(self.root))} task(s), {len(load_launch(self.root))} launch "
                         "configuration(s) (Native menu / startup targets)")

    def tool(self) -> str:
        return folder_python(self.root, self.settings)

    def _pre(self, c: dict) -> list[Step]:
        pre = c.get("preLaunchTask")
        return task_steps(self.root, pre) if pre else []

    def build_steps(self, target, debug):
        if target is None:
            return []
        if target.kind == "launch":
            return self._pre(target.data)
        return []

    def _launch(self, c: dict) -> tuple[str, Step | None]:
        c = _subst(c, self.root)
        typ = str(c.get("type", ""))
        cwd = Path(c.get("cwd") or self.root)
        env = {**tool_env(), **{str(k): str(v) for k, v in (c.get("env") or {}).items()}}
        args = [str(a) for a in (c.get("args") or [])]
        if isinstance(c.get("args"), str):
            args = c["args"].split()
        if typ in ("python", "debugpy"):
            py = c.get("python") or folder_python(self.root, self.settings)
            if c.get("module"):
                return "python", Step([py, "-m", c["module"]] + args, cwd, env, c.get("name", ""))
            return "python", Step([py, c.get("program", "")] + args, cwd, env, c.get("name", ""))
        if typ in ("cppdbg", "cppvsdbg", "gdb", "lldb", "cortex-debug", "cppdbg-gdb"):
            return "native", Step([c.get("program", "")] + args, cwd, env, c.get("name", ""))
        if typ in ("node", "pwa-node"):
            node = c.get("runtimeExecutable") or shutil.which("node") or "node"
            return "node", Step([node] + (c.get("runtimeArgs") or []) + [c.get("program", "")] + args, cwd, env,
                                c.get("name", ""))
        if typ == "coreclr":
            return "dotnet", Step([shutil.which("dotnet") or "dotnet", c.get("program", "")] + args, cwd, env,
                                  c.get("name", ""))
        if typ == "java":
            cp = c.get("classPaths") or ["."]
            return "java", Step([find_java("java"), "-cp", os.pathsep.join(cp), c.get("mainClass", "")] + args,
                                cwd, env, c.get("name", ""))
        return typ, None

    def run_step(self, target, debug):
        if target is None:
            return None
        if target.kind == "task":
            steps = task_steps(self.root, target.data["label"])
            return steps[-1] if steps else None
        _kind, step = self._launch(target.data)
        return step

    def make_steps(self, target):
        if target.kind == "task":
            steps = task_steps(self.root, target.data["label"])
            return steps[:-1]
        return self._pre(target.data)

    def debug_session(self, win, target, pre):
        if target.kind != "launch":
            return None
        kind, step = self._launch(target.data)
        if step is None:
            return None
        if kind == "python":
            c = _subst(target.data, self.root)
            py = step.argv[0]
            if c.get("module"):
                def make():
                    s = debugpy_session(win, py, Path(step.cwd) / "__main__.py", step.argv[3:], step.cwd, step.env)
                    if s is not None:
                        s.launch_args.pop("program", None)
                        s.launch_args["module"] = c["module"]
                    return s
                return ChainSession(pre, make, win)
            return ChainSession(pre, lambda: debugpy_session(win, py, Path(step.argv[1]), step.argv[2:], step.cwd,
                                                             step.env), win)
        if kind == "native":
            return ChainSession(pre, lambda: gdb_session(win, Path(step.argv[0]), step.argv[1:], step.cwd,
                                                         step.env), win)
        return None

    def commands(self):
        return vscode_commands(self.root)


def _task_build_steps(adapter: VSCodeFolderAdapter):
    orig = adapter.build_steps

    def build_steps(target, debug):
        if target is not None and target.kind == "task":
            return adapter.make_steps(target)
        return orig(target, debug)
    adapter.build_steps = build_steps
    return adapter


def adapter_for_folder(folder: Path):
    """The best adapter of a folder: CMake / Java / Python project, else a plain VS Code folder."""
    folder = Path(folder)
    if (folder / "CMakeLists.txt").exists():
        from .cmake import CMakeAdapter
        return CMakeAdapter(folder / "CMakeLists.txt")
    from .java_ide import JavaAdapter, detect
    hit = detect(folder)
    if hit is not None:
        return JavaAdapter(hit)
    from .python_project import PythonProjectAdapter, detect as pdetect
    hit = pdetect(folder)
    if hit is not None:
        return PythonProjectAdapter(hit)
    return _task_build_steps(VSCodeFolderAdapter(folder))


def open_workspace(win, path: Path) -> bool:
    path = Path(path).resolve()
    d = load_jsonc(path)
    projects = []
    names = set()
    for f in d.get("folders") or []:
        p = Path(_subst(f.get("path", "."), path.parent))
        p = p if p.is_absolute() else (path.parent / p).resolve()
        if not p.is_dir():
            win.log(f"*** {path.name}: folder not found: {p}")
            continue
        a = adapter_for_folder(p)
        if f.get("name"):
            a.name = f["name"]
        pr = ForeignProject(a)
        n, i = pr.name, 2
        while n.lower() in names:
            n = f"{pr.name}{i}"
            i += 1
        pr.name = n
        names.add(n.lower())
        projects.append(pr)
    if not projects:
        return False
    return show_projects(win, projects, path.stem, path)


def open_folder(win, path: Path) -> bool:
    path = Path(path).resolve()
    if path.name in ("tasks.json", "launch.json", "settings.json") and path.parent.name == ".vscode":
        path = path.parent.parent
    elif path.name == ".vscode":
        path = path.parent
    a = _task_build_steps(VSCodeFolderAdapter(path))
    pr = ForeignProject(a)
    return show_projects(win, [pr], pr.name, path)


def probe(folder: Path):
    f = Path(folder)
    ws = sorted(f.glob("*.code-workspace"))
    if ws:
        return ws[0]
    if (f / ".vscode").is_dir() and ((f / ".vscode" / "tasks.json").exists() or (f / ".vscode" / "launch.json").exists()):
        return f / ".vscode"
    return None


def _open_any(win, path: Path) -> bool:
    p = Path(path)
    if p.suffix.lower() == ".code-workspace":
        return open_workspace(win, p)
    return open_folder(win, p)


def register() -> None:
    from ..features.foreign_projects import register_format
    register_format([".code-workspace"], _open_any, "VS Code workspace", folder_probe=probe, name="vscode",
                    priority=-10)
    register_format(["tasks.json", "launch.json"], _open_any, "VS Code folder (.vscode)", name="vscode-folder",
                    priority=-10)


__all__ = ["vscode_commands", "task_steps", "load_tasks", "load_launch", "VSCodeFolderAdapter", "register"]
