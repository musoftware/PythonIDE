"""Generic project actions that work for any project: package.json scripts (npm / yarn / pnpm / bun),
composer.json scripts, Makefile targets, VS Code tasks (.vscode/tasks.json), pyproject scripts
([project.scripts] / [tool.poetry.scripts]), justfile recipes and Taskfile.yml tasks."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ..project_actions import (Action, Field, Provider, Separator, Submenu, composer_json, matches, package_json,
                               read_json, read_text)

DEV_SCRIPTS = ("dev", "start", "serve", "watch")


def _script_tip(cmd) -> str:
    return str(cmd)[:200] if cmd else ""


# ============================================================================ package.json scripts
class NodeScripts(Provider):
    id, title, priority, markers = "npm-scripts", "npm Scripts", 10, ("package.json",)

    def detect(self, folder, project):
        return (folder / "package.json").is_file()

    @staticmethod
    def manager(folder: Path) -> str:
        pm = str(package_json(folder).get("packageManager") or "")
        for name, lock in (("pnpm", "pnpm-lock.yaml"), ("yarn", "yarn.lock"), ("bun", "bun.lockb"), ("bun", "bun.lock")):
            if pm.startswith(name) or (folder / lock).is_file():
                return name
        return "npm"

    def scripts(self, folder) -> dict:
        s = package_json(folder).get("scripts")
        return s if isinstance(s, dict) else {}

    def script_action(self, folder, name, cmd) -> Action:
        pm = self.manager(folder)
        argv = [pm, "run", name]
        return Action(f"script.{name}", name, lambda c, a=argv, n=name: c.run_cli(a, title=f"{pm} run {n}"),
                      opens="none", tip=_script_tip(cmd), toolbar=name in ("dev", "start"),
                      group="scripts")

    def install_action(self, folder) -> Action:
        pm = self.manager(folder)
        return Action("install", f"{pm} install", lambda c: c.run_cli([pm, "install"], title=f"{pm} install"),
                      opens="none", refresh=True, tip="Install the dependencies of package.json")

    def actions(self, ctx):
        folder = ctx.folder
        items = [self.script_action(folder, n, c) for n, c in self.scripts(folder).items()]
        if not items:
            items = [Action("no-scripts", "(no scripts in package.json)", lambda c: None,
                            enabled=lambda c: False, palette=False)]
        return [*items, Separator(), self.install_action(folder),
                Action("add-package", "Add Package...", self._add, opens="none", refresh=True,
                       ask=[Field("package", "Package", placeholder="e.g. axios or lodash@4"),
                            Field("dev", "Development dependency (--save-dev)", "bool")]),
                Action("open-package-json", "Open package.json", lambda c: c.open_file(c.path("package.json")),
                       opens="none")]

    def _add(self, ctx):
        pm = self.manager(ctx.folder)
        pkgs = ctx.values["package"].split()
        verb = "install" if pm == "npm" else "add"
        dev = (["--save-dev"] if pm == "npm" else ["-D"]) if ctx.values.get("dev") else []
        ctx.run_cli([pm, verb, *pkgs, *dev], title=f"{pm} {verb} {' '.join(pkgs)}")

    def folder_actions(self, ctx, rel_folder):
        if rel_folder != "":
            return []
        scripts = [self.script_action(ctx.folder, n, c) for n, c in self.scripts(ctx.folder).items()]
        out = [Submenu("Run Script", scripts)] if scripts else []
        return [*out, self.install_action(ctx.folder)]

    def file_actions(self, ctx, rel_file):
        if rel_file.lower() != "package.json":
            return []
        return [*[self.script_action(ctx.folder, n, c) for n, c in self.scripts(ctx.folder).items()],
                Separator(), self.install_action(ctx.folder)]


# ============================================================================ composer.json scripts
COMPOSER_EVENTS = re.compile(r"^(pre|post)-")


class ComposerScripts(Provider):
    id, title, priority, markers = "composer", "Composer", 5, ("composer.json",)

    def detect(self, folder, project):
        return (folder / "composer.json").is_file()

    def scripts(self, folder) -> dict:
        s = composer_json(folder).get("scripts")
        return s if isinstance(s, dict) else {}

    def script_action(self, name, cmd) -> Action:
        return Action(f"script.{name}", name,
                      lambda c, n=name: c.run_cli(["composer", "run-script", n], title=f"composer run-script {n}"),
                      opens="none", tip=_script_tip(cmd if isinstance(cmd, str) else "; ".join(map(str, cmd))))

    def basic(self) -> list:
        return [Action("install", "composer install", lambda c: c.run_cli(["composer", "install"]),
                       opens="none", refresh=True),
                Action("update", "composer update", lambda c: c.run_cli(["composer", "update"]),
                       opens="none", refresh=True),
                Action("dump-autoload", "composer dump-autoload", lambda c: c.run_cli(["composer", "dump-autoload"]),
                       opens="none"),
                Action("require", "Require Package...", self._require, opens="none", refresh=True,
                       ask=[Field("package", "Package", placeholder="vendor/package"),
                            Field("dev", "Development dependency (--dev)", "bool")])]

    def _require(self, ctx):
        pkgs = ctx.values["package"].split()
        ctx.run_cli(["composer", "require", *pkgs, *(["--dev"] if ctx.values.get("dev") else [])],
                    title=f"composer require {' '.join(pkgs)}")

    def script_items(self, folder) -> list:
        s = self.scripts(folder)
        own = [self.script_action(n, c) for n, c in s.items() if not COMPOSER_EVENTS.match(n)]
        events = [self.script_action(n, c) for n, c in s.items() if COMPOSER_EVENTS.match(n)]
        return own + ([Submenu("Event Scripts", events)] if events else [])

    def actions(self, ctx):
        scripts = self.script_items(ctx.folder)
        return [*scripts, *([Separator()] if scripts else []), *self.basic()]

    def folder_actions(self, ctx, rel_folder):
        if rel_folder != "":
            return []
        scripts = self.script_items(ctx.folder)
        return [Submenu("Composer", [*scripts, *([Separator()] if scripts else []), *self.basic()])]

    def file_actions(self, ctx, rel_file):
        return self.actions(ctx) if rel_file.lower() == "composer.json" else []


# ============================================================================ Makefile
MAKEFILES = ("GNUmakefile", "makefile", "Makefile")
_TARGET = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.\-/]*)\s*:(?![=:])", re.M)


def make_targets(text: str) -> list[str]:
    out = []
    for m in _TARGET.finditer(text):
        t = m.group(1)
        if t.startswith(".") or "%" in t or t in out:
            continue
        out.append(t)
    return out


class MakeTargets(Provider):
    id, title, priority, markers = "make", "Make", 4, MAKEFILES

    def makefile(self, folder) -> Path | None:
        return next((folder / n for n in MAKEFILES if (folder / n).is_file()), None)

    def detect(self, folder, project):
        return self.makefile(folder) is not None

    def targets(self, folder) -> list[str]:
        mf = self.makefile(folder)
        return make_targets(read_text(mf)) if mf is not None else []

    def actions(self, ctx):
        ts = [Action(f"target.{t}", t, lambda c, t=t: c.run_cli(["make", t], title=f"make {t}"), group="targets",
                     toolbar=(i == 0 and t in ("all", "build")), refresh=True)
              for i, t in enumerate(self.targets(ctx.folder))]
        return [Action("default", "make (default target)", lambda c: c.run_cli(["make"], title="make"), refresh=True),
                Separator(), *ts]

    def folder_actions(self, ctx, rel_folder):
        return [Submenu("Make", self.actions(ctx))] if rel_folder == "" else []

    def file_actions(self, ctx, rel_file):
        return self.actions(ctx) if rel_file in MAKEFILES else []


# ============================================================================ VS Code tasks
_VAR = re.compile(r"\$\{([^}]+)\}")


def _expand(text: str, ctx) -> str:
    def sub(m):
        v = m.group(1)
        if v in ("workspaceFolder", "workspaceRoot", "cwd"):
            return str(ctx.folder)
        if v == "workspaceFolderBasename":
            return ctx.folder.name
        if v.startswith("env:"):
            return os.environ.get(v[4:], "")
        if v in ("pathSeparator", "/"):
            return os.sep
        if v in ("file", "fileDirname", "fileBasename", "fileBasenameNoExtension", "relativeFile"):
            cur = _current_file(ctx)
            if cur is None:
                return ""
            return {"file": str(cur), "fileDirname": str(cur.parent), "fileBasename": cur.name,
                    "fileBasenameNoExtension": cur.stem, "relativeFile": ctx.rel(cur)}[v]
        return m.group(0)
    return _VAR.sub(sub, str(text))


def _current_file(ctx) -> Path | None:
    try:
        from ..features.command_palette import current_file
        return current_file(ctx.win)
    except Exception:  # noqa: BLE001
        return None


def _quote(a: str) -> str:
    return f'"{a}"' if (" " in a or not a) and not a.startswith('"') else a


class VsCodeTasks(Provider):
    id, title, priority, markers = "vscode-tasks", "Tasks", 3, (".vscode/tasks.json", ".vscode")

    def detect(self, folder, project):
        return (folder / ".vscode" / "tasks.json").is_file()

    def tasks(self, folder) -> list[dict]:
        d = read_json(folder / ".vscode" / "tasks.json")
        ts = d.get("tasks") if isinstance(d, dict) else None
        return [t for t in (ts or []) if isinstance(t, dict)]

    @staticmethod
    def label(t: dict) -> str:
        if t.get("label"):
            return str(t["label"])
        if t.get("type") == "npm":
            return f"npm: {t.get('script', '')}"
        return str(t.get("taskName") or t.get("command") or "task")

    def argv(self, t: dict, ctx) -> tuple[list[str], str]:
        plat = "windows" if sys.platform == "win32" else ("osx" if sys.platform == "darwin" else "linux")
        t = {**t, **(t.get(plat) or {})}
        opts = t.get("options") or {}
        cwd = _expand(opts.get("cwd") or str(ctx.folder), ctx)
        if t.get("type") == "npm":
            pm = NodeScripts.manager(Path(cwd))
            return [pm, "run", str(t.get("script", ""))], cwd
        cmd = t.get("command")
        if isinstance(cmd, dict):
            cmd = cmd.get("value")
        cmd = _expand(str(cmd or ""), ctx)
        args = [_expand(a.get("value") if isinstance(a, dict) else str(a), ctx) for a in (t.get("args") or [])]
        if t.get("type", "process") == "process":
            return [cmd, *args], cwd
        line = " ".join([cmd, *map(_quote, args)])
        if sys.platform == "win32":
            return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c", line], cwd
        return ["/bin/sh", "-c", line], cwd

    def _run(self, ctx, task):
        argv, cwd = self.argv(task, ctx)
        ctx.run_cli(argv, cwd=cwd, title=f"Task: {self.label(task)}")

    def actions(self, ctx):
        out = []
        for i, t in enumerate(self.tasks(ctx.folder)):
            group = t.get("group")
            gname = group.get("kind") if isinstance(group, dict) else group
            default = isinstance(group, dict) and group.get("isDefault") is True
            out.append(Action(f"task.{i}.{self.label(t)}", self.label(t), lambda c, t=t: self._run(c, t),
                              group=gname or None, toolbar=default, opens="none", refresh=gname == "build",
                              tip=str(t.get("detail") or t.get("command") or "")))
        out += [Separator(), Action("open-tasks", "Open tasks.json",
                                    lambda c: c.open_file(c.path(".vscode/tasks.json")), opens="none")]
        return out

    def folder_actions(self, ctx, rel_folder):
        return [Submenu("Run Task", self.actions(ctx))] if rel_folder in ("", ".vscode") else []

    def file_actions(self, ctx, rel_file):
        return self.actions(ctx) if matches(rel_file, ".vscode/tasks.json") else []


# ============================================================================ pyproject scripts
def pyproject_scripts(folder) -> dict[str, str]:
    p = Path(folder) / "pyproject.toml"
    if not p.is_file():
        return {}
    try:
        import tomllib
        data = tomllib.loads(read_text(p))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for d in ((data.get("project") or {}).get("scripts") or {},
              ((data.get("tool") or {}).get("poetry") or {}).get("scripts") or {}):
        for k, v in d.items():
            if isinstance(v, str):
                out[k] = v
            elif isinstance(v, dict) and isinstance(v.get("callable") or v.get("reference"), str):
                out[k] = v.get("callable") or v.get("reference")
    return out


class PyprojectScripts(Provider):
    id, title, priority, markers = "pyproject-scripts", "Python Scripts", 6, ("pyproject.toml",)

    def detect(self, folder, project):
        return bool(pyproject_scripts(folder))

    def _run(self, ctx, name, ref):
        mod, _, fn = ref.partition(":")
        fn = fn.split("[")[0].strip()
        code = f"import sys; from {mod.strip()} import {fn.split('.')[0]} as _m; " \
               f"sys.exit(_m{('.' + fn.split('.', 1)[1]) if '.' in fn else ''}())"
        src = ctx.folder / "src"
        env = {"PYTHONPATH": os.pathsep.join([str(src), str(ctx.folder)] if src.is_dir() else [str(ctx.folder)])}
        ctx.run_cli(["python", "-c", code], title=f"{name}  ({ref})", env=env)

    def actions(self, ctx):
        acts = [Action(f"script.{n}", n, lambda c, n=n, r=r: self._run(c, n, r), tip=r, opens="none")
                for n, r in pyproject_scripts(ctx.folder).items()]
        return [*acts, Separator(),
                Action("pip-install-e", "pip install -e .", lambda c: c.run_cli(["python", "-m", "pip", "install",
                                                                                   "-e", "."]), opens="none")]

    def folder_actions(self, ctx, rel_folder):
        return [Submenu("Python Scripts", self.actions(ctx))] if rel_folder == "" else []

    def file_actions(self, ctx, rel_file):
        return self.actions(ctx) if rel_file == "pyproject.toml" else []


# ============================================================================ justfile
JUSTFILES = ("justfile", "Justfile", ".justfile")
_RECIPE = re.compile(r"^@?([A-Za-z_][\w-]*)((?:\s+[^:\n]+?)?)\s*:(?![=:])", re.M)
_JUST_KEYWORDS = {"set", "alias", "export", "import", "mod"}


def just_recipes(text: str) -> list[tuple[str, str]]:
    out = []
    for m in _RECIPE.finditer(text):
        name, params = m.group(1), m.group(2).strip()
        if name in _JUST_KEYWORDS or any(n == name for n, _ in out):
            continue
        out.append((name, params))
    return out


class JustRecipes(Provider):
    id, title, priority, markers = "just", "just", 3, JUSTFILES

    def file(self, folder):
        return next((folder / n for n in JUSTFILES if (folder / n).is_file()), None)

    def detect(self, folder, project):
        return self.file(folder) is not None

    def actions(self, ctx):
        f = self.file(ctx.folder)
        out = []
        for name, params in just_recipes(read_text(f) if f else ""):
            ask = [Field("args", f"Arguments ({params})", required=False)] if params else []
            out.append(Action(f"recipe.{name}", name + ("..." if params else ""),
                              lambda c, n=name: c.run_cli(["just", n, *str(c.values.get("args", "")).split()],
                                                          title=f"just {n}"), ask=ask, opens="none", refresh=True))
        return out

    def folder_actions(self, ctx, rel_folder):
        return [Submenu("just", self.actions(ctx))] if rel_folder == "" else []


# ============================================================================ Taskfile.yml (go-task)
TASKFILES = ("Taskfile.yml", "Taskfile.yaml", "taskfile.yml", "taskfile.yaml")


def taskfile_tasks(text: str) -> list[str]:
    out, inside, indent = [], False, None
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^tasks\s*:\s*$", line):
            inside, indent = True, None
            continue
        if inside:
            if not line.startswith((" ", "\t")):
                break
            ind = len(line) - len(line.lstrip())
            if indent is None:
                indent = ind
            m = re.match(r"^\s*['\"]?([\w:.\-]+)['\"]?\s*:", line)
            if ind == indent and m:
                out.append(m.group(1))
    return out


class TaskfileTasks(Provider):
    id, title, priority, markers = "taskfile", "Task", 3, TASKFILES

    def file(self, folder):
        return next((folder / n for n in TASKFILES if (folder / n).is_file()), None)

    def detect(self, folder, project):
        return self.file(folder) is not None

    def actions(self, ctx):
        f = self.file(ctx.folder)
        return [Action(f"task.{t}", t, lambda c, t=t: c.run_cli(["task", t], title=f"task {t}"), opens="none",
                       refresh=True) for t in taskfile_tasks(read_text(f) if f else "")]

    def folder_actions(self, ctx, rel_folder):
        return [Submenu("Task", self.actions(ctx))] if rel_folder == "" else []


PROVIDERS = [NodeScripts(), ComposerScripts(), MakeTargets(), VsCodeTasks(), PyprojectScripts(), JustRecipes(),
             TaskfileTasks()]
