"""Package installs started from a quick fix: pip, npm, cargo add, go get, composer require, dotnet add package.

Every install runs in a worker thread through the shared progress API (radide/progress.py: a status-bar task with
Cancel, the tool's output in the Output window) - the GUI never waits. ``then(ok)`` is called in the GUI thread.
Tests set ``DRY_RUN = True`` (or RADIDE_QUICKFIX_DRY_RUN=1): the command is recorded in ``LAST`` instead of run.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

DRY_RUN = os.environ.get("RADIDE_QUICKFIX_DRY_RUN", "") == "1"
LAST: list[dict] = []                 # the commands started (or recorded with DRY_RUN): {argv, cwd, title}


def _log(win, text: str) -> None:
    fn = getattr(win, "log", None)
    if callable(fn):
        try:
            fn(text)
            return
        except Exception:  # noqa: BLE001
            pass
    print(text)


def _tool(name: str) -> str:
    return shutil.which(name) or shutil.which(name + ".cmd") or shutil.which(name + ".exe") or ""


def run_install(win, argv: list, cwd, title: str, then=None, env=None) -> None:
    """argv in a worker thread with progress; output lines into the Output window."""
    rec = {"argv": [str(a) for a in argv], "cwd": str(cwd), "title": title}
    LAST.append(rec)
    if DRY_RUN or not argv or not argv[0]:
        if not DRY_RUN:
            _log(win, f"*** {title}: the tool was not found")
        if then is not None:
            then(bool(DRY_RUN and argv and argv[0]))
        return
    from .. import progress
    _log(win, f"------ {title} ------\n> {' '.join(rec['argv'])}")
    try:
        win.dock_output.show()
    except Exception:  # noqa: BLE001
        pass

    def work(reporter):                    # worker thread: the output goes to the task; the Output window after
        res = progress.run_command(rec["argv"], reporter, cwd=str(cwd), env=env, timeout=1800)
        return res.returncode, res.stdout

    def done(result):
        code, out = result
        for ln in (out or "").splitlines()[-400:]:
            _log(win, ln)
        _log(win, f"========== {title}: {'done' if code == 0 else f'failed (exit code {code})'} ==========")
        try:
            win.statusBar().showMessage(f"{title}: {'done' if code == 0 else 'failed - see the Output window'}", 8000)
        except Exception:  # noqa: BLE001
            pass
        if then is not None:
            then(code == 0)

    def failed(err):
        _log(win, f"*** {title}: {err}")
        if then is not None:
            then(False)
    progress.run_task(work, title, win, cancellable=True, on_done=done, on_error=failed)


# ============================================================================ per tool
def python_for(win, path) -> str:
    """The interpreter Run uses for this file: the project's .venv, the configured interpreter, else python on PATH."""
    p = Path(str(path)).resolve()
    for d in [p.parent, *list(p.parent.parents)[:4]]:
        for rel in (".venv/Scripts/python.exe", "venv/Scripts/python.exe", ".venv/bin/python", "venv/bin/python"):
            if (d / rel).is_file():
                return str(d / rel)
    if win is not None:
        try:
            rp = win.run_plugin() if callable(getattr(win, "run_plugin", None)) else None
            if rp is not None and str(getattr(rp, "id", "")).startswith("python"):
                found = rp.find_interpreter(win._configured_interpreter(rp))
                if found:
                    return found
        except Exception:  # noqa: BLE001
            pass
    return shutil.which("python") or shutil.which("python3") or sys.executable


def add_requirement(folder: Path, dist: str) -> bool:
    """Append dist to requirements.txt (only when the file exists and does not list it)."""
    req = Path(folder) / "requirements.txt"
    if not req.is_file():
        return False
    text = req.read_text(encoding="utf-8", errors="replace")
    names = {re.split(r"[<>=!~;\[ ]", ln.strip(), 1)[0].lower() for ln in text.splitlines()
             if ln.strip() and not ln.strip().startswith("#")}
    if dist.lower() in names:
        return False
    req.write_text(text + ("" if not text or text.endswith("\n") else "\n") + dist + "\n", encoding="utf-8")
    return True


def pip_install(win, path, dist: str, folder: Path, then=None) -> None:
    py = python_for(win, path)

    def after(ok):
        if ok and add_requirement(folder, dist):
            _log(win, f"{dist} added to requirements.txt")
        _refresh_lsp(win)
        if then is not None:
            then(ok)
    run_install(win, [py, "-m", "pip", "install", dist], folder, f"pip install {dist}", after)


def npm_install(win, folder: Path, pkg: str, dev: bool = False, then=None) -> None:
    argv = [_tool("npm"), "install"] + (["--save-dev"] if dev else []) + [pkg]
    run_install(win, argv, folder, f"npm install {'-D ' if dev else ''}{pkg}", lambda ok: (_refresh_lsp(win),
                                                                                         then and then(ok)))


def cargo_add(win, folder: Path, crate: str, then=None) -> None:
    run_install(win, [_tool("cargo"), "add", crate], folder, f"cargo add {crate}", then)


def go_get(win, folder: Path, module: str, then=None) -> None:
    run_install(win, [_tool("go"), "get", module], folder, f"go get {module}", then)


def composer_require(win, folder: Path, pkg: str, then=None) -> None:
    run_install(win, [_tool("composer"), "require", pkg], folder, f"composer require {pkg}", then)


def dotnet_add_package(win, project: Path, pkg: str, then=None) -> None:
    from ..dotnet.tools import sdk
    env = dict(os.environ, **{k: str(v) for k, v in sdk.QUIET_ENV.items()})
    run_install(win, [sdk.dotnet() or _tool("dotnet"), "add", str(project), "package", pkg], Path(project).parent,
                f"dotnet add package {pkg}", then, env=env)


def _refresh_lsp(win) -> None:
    """After an install: the open editors' servers see the file again (new modules resolve)."""
    for ed in list(getattr(win, "_lsp_editors", {}).values()):
        try:
            if ed.lsp is not None:
                ed.lsp.did_change(ed.path, ed.text())
        except Exception:  # noqa: BLE001
            continue


__all__ = ["run_install", "pip_install", "npm_install", "cargo_add", "go_get", "composer_require",
           "dotnet_add_package", "python_for", "add_requirement", "DRY_RUN", "LAST"]
