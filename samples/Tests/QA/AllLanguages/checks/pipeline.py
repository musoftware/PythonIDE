"""Check families "build", "run", "publish": the language's own build command, the IDE run spec (a form's window
is clicked, console programs must exit 0) and Build > Publish (radide.deploy.build.build, kind auto) + the
published exe."""
from __future__ import annotations

import py_compile
import shutil
import subprocess
import tempfile
import time
import traceback
import urllib.request
from pathlib import Path

from .common import (Result, Started, child_env, gui_test, generic_run, has_form_code, is_website)

def shell_build(cmd: str, folder: Path, env, timeout: float) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=str(folder), shell=True, env=child_env(env), capture_output=True,
                           timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return -1, f"timed out after {timeout:.0f}s"
    out = (r.stdout + r.stderr).decode("utf-8", "replace")
    return r.returncode, out


def tool_missing(p) -> str:
    try:
        if callable(getattr(p, "tool", None)):
            t = p.tool()
            if not t or str(t).startswith("echo"):
                return f"toolchain not found ({', '.join(getattr(p, 'tool_names', []) or [])}) " \
                       f"{getattr(p, 'install_hint', '')}".strip()
    except Exception as e:  # noqa: BLE001
        return f"tool lookup failed: {e}"
    return ""


def step_build(r: Result, p, project, folder: Path, args) -> None:
    from radide.model import Project
    if p.id.startswith("python") or p.id in ("pygame", "kivy", "python-arcade", "python-ursina"):
        bad = []
        for f in folder.rglob("*.py"):
            if ".venv" in f.parts:
                continue
            try:
                py_compile.compile(str(f), doraise=True, cfile=str(Path(tempfile.gettempdir()) / "qa_pyc.pyc"))
            except py_compile.PyCompileError as e:
                bad.append(str(e))
        r.build = "FAIL: " + bad[0][:400] if bad else "PASS (py_compile)"
        return
    build_cmd = getattr(p, "build_command", None)
    if not callable(build_cmd) or is_website(p):
        r.build = "n/a"
        return
    miss = tool_missing(p)
    if miss:
        r.build = "SKIP: " + miss
        return
    try:
        project = Project.load(folder)
        if callable(getattr(p, "prepare", None)):
            p.prepare(folder, project)
        cmd = build_cmd(folder, project)
    except Exception as e:  # noqa: BLE001
        r.build = f"FAIL: build command: {e}"
        r.note(traceback.format_exc())
        return
    if not cmd:
        r.build = "n/a (interpreted)"
        return
    env = None
    try:
        spec = p.run_spec(folder, project.startup or "", p.find_interpreter(""))
        env = spec.env
    except Exception:  # noqa: BLE001
        pass
    t0 = time.time()
    code, out = shell_build(cmd, folder, env, args.build_timeout)
    if code == 0:
        r.build = f"PASS ({time.time() - t0:.0f}s)"
    else:
        r.build = f"FAIL: exit {code}: {out.strip()[-700:]}"
        r.note(f"build command: {cmd}")


def step_run(r: Result, p, project, folder: Path, args) -> None:
    from radide.model import Project
    if is_website(p):
        return run_website(r, p, folder, args)
    if callable(getattr(p, "build_command", None)) and tool_missing(p):
        r.run = "SKIP: " + tool_missing(p)
        return
    project = Project.load(folder)
    try:
        interp = p.find_interpreter("")
    except Exception:  # noqa: BLE001
        interp = ""
    if not interp:
        r.run = "SKIP: interpreter / runtime not found"
        return
    try:
        spec = p.run_spec(folder, project.startup or "", interp)
    except Exception as e:  # noqa: BLE001
        r.run = f"FAIL: run_spec: {e}"
        r.note(traceback.format_exc())
        return
    argv = [spec.program, *[str(a) for a in spec.args]]
    st = Started(argv, spec.cwd or folder, spec.env)
    try:
        if has_form_code(p) and project.forms:
            slow = 240 if p.id in ("rust-bridge", "java-bridge", "csharp-bridge", "dart-bridge", "go-bridge",
                                   "typescript", "fortran-bridge", "cpp-bridge") else 90
            s, d = gui_test(st, max(args.timeout, slow))
        else:
            s, d = generic_run(st, args.timeout)
        r.run = f"{s}: {d}" if s != "PASS" else f"PASS - {d}"
        if s != "PASS":
            r.note("run output:\n" + st.text(30))
    finally:
        st.kill()


def run_website(r: Result, p, folder: Path, args) -> None:
    from radide.model import Project
    from radide.web_site.server import DevServer
    project = Project.load(folder)
    interp = ""
    if getattr(p, "needs_interpreter", False):
        interp = p.find_interpreter("")
        if not interp:
            r.run = "SKIP: " + (getattr(p, "install_hint", "") or "interpreter not found")
            return
    srv = DevServer(project.folder, p, project=project, interpreter=interp)
    logs: list[str] = []
    try:
        srv.log.connect(lambda t: logs.append(str(t)))
    except Exception:  # noqa: BLE001
        pass
    try:
        srv.start()
    except Exception as e:  # noqa: BLE001
        r.run = f"FAIL: DevServer.start: {e}"
        r.note(traceback.format_exc())
        return
    try:
        start = srv.start_url()
        last = ""
        # framework sites install their packages on the first start (npm install / bundle install / pip)
        slow = type(p).__name__ == "FrameworkPlugin" or callable(getattr(p, "backend", None))
        # (Rails: rails new + bundle install + db:prepare + the first boot - many minutes on a loaded PC; the
        # dev server answers 503 "Starting" with the last output meanwhile)
        end = time.time() + max(args.timeout, (1500 if "rails" in getattr(p, "id", "") else 600) if slow else 60)
        while time.time() < end:
            try:
                with urllib.request.urlopen(start, timeout=10) as resp:
                    body = resp.read(4000).decode("utf-8", "replace")
                    if resp.status == 200:
                        r.run = f"PASS - GET {start} -> 200 ({len(body)} bytes)"
                        return
                    last = f"HTTP {resp.status}"
            except Exception as e:  # noqa: BLE001
                last = str(e)
            _pump(1.0)
        r.run = f"FAIL: {start}: {last}"
        r.note("server log:\n" + "\n".join(logs[-30:]))
    finally:
        try:
            srv.stop()
        except Exception:  # noqa: BLE001
            pass


def python_inside(dist: Path) -> bool:
    for f in dist.rglob("*"):
        n = f.name.lower()
        if (n.startswith("python3") and n.endswith(".dll")) or n == "base_library.zip" or \
                (f.is_dir() and n == "_internal"):
            return True
    return False


def step_publish(r: Result, p, project, folder: Path, args, scratch: Path) -> Path | None:
    from radide.deploy import build as B
    from radide.deploy.config import PublishConfig
    from radide.model import Project
    if is_website(p):
        r.publish = "n/a (web sites publish to FTP / cloud, not an exe)"
        return None
    project = Project.load(folder)
    out = scratch / "_publish" / f"{r.language}_{r.template or 'default'}"
    shutil.rmtree(out, ignore_errors=True)
    cfg = PublishConfig(app_name=project.name, version="1.0.0", publisher="RAD IDE QA", output_dir=str(out),
                        make_installer=False)
    kind = B.detect_kind(project, cfg)
    log: list[str] = []
    t0 = time.time()
    try:
        res = B.build(folder, cfg, log=log.append)
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        r.publish_kind = kind
        if kind == "folder" and "already built" in msg.lower() or "choose the folder" in msg.lower():
            r.publish = "n/a (no exe builder for this language: Publish needs an already built folder)"
        elif "not found" in msg.lower() or "was not found" in msg.lower():
            r.publish = f"SKIP: {msg[:300]}"
        else:
            r.publish = f"FAIL: {type(e).__name__}: {msg[:500]}"
            r.note("publish log:\n" + "\n".join(log[-40:]))
        return None
    fell_back = [ln for ln in log if ln.startswith("Native build not possible") or ln.startswith("  - ")]
    r.publish_kind = res.kind + (" (native fell back)" if kind == "native" and not res.kind.startswith("native") else "")
    if fell_back:
        r.note("native fallback: " + " | ".join(fell_back)[:800])
    exe = Path(res.dist) / res.exe
    if not exe.is_file():
        r.publish = f"FAIL: no exe {exe}"
        return None
    r.exe_size = exe.stat().st_size
    r.dist_size = sum(f.stat().st_size for f in Path(res.dist).rglob("*") if f.is_file())
    r.python_inside = "yes" if python_inside(Path(res.dist)) else "no"
    r.publish = f"PASS ({time.time() - t0:.0f}s)"
    if res.notes:
        r.note("publish notes: " + "; ".join(res.notes))
    return exe


def step_published_run(r: Result, p, project, exe: Path, args) -> None:
    from radide.model import Project
    project = Project.load(project.folder)
    st = Started([str(exe)], exe.parent, None)
    try:
        if has_form_code(p) and project.forms:
            s, d = gui_test(st, max(args.timeout, 60))
        else:
            s, d = generic_run(st, args.timeout)
        r.published_run = f"{s}: {d}" if s != "PASS" else f"PASS - {d}"
        if s != "PASS":
            r.note("published run output:\n" + st.text(30))
    finally:
        st.kill()




def run(r: Result, pl, project, folder: Path, args, scratch: Path, checks: set[str]) -> None:
    """The pipeline families that were asked for: build, run, publish (publish includes the published exe)."""
    steps = []
    if "build" in checks:
        steps.append(("build", lambda: step_build(r, pl, project, folder, args)))
    if "run" in checks and not args.no_run:
        steps.append(("run", lambda: step_run(r, pl, project, folder, args)))
    for name, fn in steps:
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            setattr(r, name, f"FAIL: {type(e).__name__}: {e}")
            r.note(traceback.format_exc())
    if "publish" in checks and not args.no_publish:
        exe = None
        try:
            exe = step_publish(r, pl, project, folder, args, scratch)
        except Exception as e:  # noqa: BLE001
            r.publish = f"FAIL: {type(e).__name__}: {e}"
            r.note(traceback.format_exc())
        if exe is not None and not args.no_published_run:
            try:
                step_published_run(r, pl, project, exe, args)
            except Exception as e:  # noqa: BLE001
                r.published_run = f"FAIL: {type(e).__name__}: {e}"
                r.note(traceback.format_exc())


def _pump(sec: float) -> None:
    """Sleep while delivering queued Qt signals (the DevServer logs from its threads)."""
    try:
        from PyQt6.QtCore import QCoreApplication
    except ImportError:
        time.sleep(sec)
        return
    end = time.time() + sec
    while time.time() < end:
        QCoreApplication.processEvents()
        time.sleep(0.05)
