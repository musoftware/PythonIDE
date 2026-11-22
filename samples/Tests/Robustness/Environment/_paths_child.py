"""Child of test_env_paths.py: create / open / save / publish / run the published exe / F5-run projects of
several languages in one folder, with the environment the parent gave it (an Arabic user profile ...).

    python _paths_child.py <scenario> <base folder> <languages,comma,separated> [output dir | -] [steps]

Prints one line per step:  RESULT {"scenario", "lang", "step", "ok", "detail", "seconds"}"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
os.environ.setdefault("RADIDE_NO_BROWSER", "1")

from radide.deploy import build  # noqa: E402
from radide.deploy.config import PublishConfig  # noqa: E402
from radide.languages import get_plugin  # noqa: E402
from radide.model import Form, Project  # noqa: E402
from radide.paths import short_alias  # noqa: E402
from radide.workspace import create_project  # noqa: E402

scen, base, langs = sys.argv[1], Path(sys.argv[2]), sys.argv[3].split(",")
out_dir = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else ""
steps = (sys.argv[5] if len(sys.argv) > 5 else "create,open,publish,exe,f5").split(",")
IDS = {"VB6": "vb-basic", "PyTk": "python-tk", "C": "c-bridge", "CSharp": "csharp-bridge", "Rust": "rust-bridge",
       "Go": "go-bridge", "JS": "javascript"}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def emit(lang, step, ok, detail="", t0=None):
    print("RESULT " + json.dumps({"scenario": scen, "lang": lang, "step": step, "ok": bool(ok),
                                  "detail": str(detail)[-1500:], "seconds": round(time.time() - t0, 1) if t0 else 0},
                                 ensure_ascii=False), flush=True)


def kill_tree(p):
    if p.poll() is None:
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    try:
        p.wait(10)
    except subprocess.TimeoutExpired:
        pass


def _processes() -> list[tuple[int, int, str]]:
    """(pid, parent pid, exe name) of every process (Toolhelp snapshot)."""
    import ctypes
    from ctypes import wintypes as wt

    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                    ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                    ("szExeFile", ctypes.c_wchar * 260)]
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateToolhelp32Snapshot.restype = wt.HANDLE
    snap = k.CreateToolhelp32Snapshot(2, 0)
    e = PE32()
    e.dwSize = ctypes.sizeof(PE32)
    out = []
    if k.Process32FirstW(snap, ctypes.byref(e)):
        while True:
            out.append((e.th32ProcessID, e.th32ParentProcessID, e.szExeFile.lower()))
            if not k.Process32NextW(snap, ctypes.byref(e)):
                break
    k.CloseHandle(snap)
    return out


def building(pid: int) -> bool:
    """A build (cmd.exe running cargo / go / csc / gcc / dotnet ...) is running below *pid*."""
    procs = _processes()
    kids = {pid}
    changed = True
    while changed:
        changed = False
        for p, pp, _n in procs:
            if pp in kids and p not in kids:
                kids.add(p)
                changed = True
    tools = ("cmd.exe",)         # the bridge runs its build through the shell
    return any(n in tools for p, _pp, n in procs if p in kids and p != pid)


def alive_for(p, seconds: float) -> bool:
    t = time.time()
    while time.time() - t < seconds:
        if p.poll() is not None:
            return False
        time.sleep(0.25)
    return True


for lang in langs:
    folder = base / f"{lang} App"
    exe = None
    if "create" in steps:
        t0 = time.time()
        try:
            if folder.exists():
                import shutil
                shutil.rmtree(folder, ignore_errors=True)
            create_project(folder, f"{lang}App", IDS[lang])
            f = Form.load(folder / "Form1.form")
            c = f.add("Button", 24, 24)
            c.props["Name"] = "Button1"
            c.props["Text"] = "زر عربي"
            f.save(folder / "Form1.form")
            emit(lang, "create", (folder / "project.radproj").is_file(), "", t0)
        except Exception:  # noqa: BLE001
            emit(lang, "create", False, traceback.format_exc(), t0)
            continue
    if "open" in steps:
        t0 = time.time()
        try:
            p = Project.load(folder)
            f = Form.load(folder / "Form1.form")
            f.find("Button1").props["Text"] = "زر عربي 2"
            f.save(folder / "Form1.form")
            p.save()
            emit(lang, "open", Form.load(folder / "Form1.form").find("Button1").props["Text"] == "زر عربي 2", "", t0)
        except Exception:  # noqa: BLE001
            emit(lang, "open", False, traceback.format_exc(), t0)
    if "publish" in steps:
        t0 = time.time()
        log: list[str] = []
        try:
            cfg = PublishConfig(app_name=f"{lang}App", version="1.0.0", publisher="RAD IDE tests", output_dir=out_dir)
            res = build.build(folder, cfg, log=log.append)
            exe = Path(res.dist) / res.exe
            emit(lang, "publish", exe.is_file(), f"kind={res.kind} exe={exe}\n" + "\n".join(log[-6:]), t0)
            print(f"KIND {lang} {res.kind}", flush=True)
        except Exception as e:  # noqa: BLE001
            emit(lang, "publish", False, f"{type(e).__name__}: {e}\n" + "\n".join(log[-25:]), t0)
    if "exe" in steps and exe is not None and exe.is_file():
        t0 = time.time()
        try:
            # a published program in a folder deeper than MAX_PATH: started like the IDE / a shortcut does it,
            # through the short alias (CreateProcess refuses a longer working directory)
            run_dir = short_alias(exe.parent, 200)
            p = subprocess.Popen([str(run_dir / exe.name)], cwd=str(run_dir), stdout=subprocess.DEVNULL,
                                 stderr=subprocess.PIPE)
        except OSError:
            emit(lang, "exe", False, traceback.format_exc(), t0)
            p = None
        if p is not None:
            try:
                up = alive_for(p, 5)
                err = "" if up else (p.stderr.read() or b"").decode("utf-8", "replace")
                emit(lang, "exe", up, f"exit={p.poll()} {err[-600:]}", t0)
            finally:
                kill_tree(p)
    if "f5" in steps:
        t0 = time.time()
        try:
            plugin = get_plugin(Project.load(folder).language)
            run_folder = short_alias(folder, 100)            # what MainWindow.run_project does (Start Without Debugging)
            spec = plugin.run_spec(run_folder, "Form1", sys.executable)
            p = subprocess.Popen([spec.program, *spec.args], cwd=str(spec.cwd), env=spec.env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NO_WINDOW)
            out = b""
            import threading
            chunks: list[bytes] = []

            def reader():
                for line in p.stdout:
                    chunks.append(line)
            th = threading.Thread(target=reader, daemon=True)
            th.start()
            # the bridge languages compile first (cargo / go / csc / gcc run by a cmd.exe child of the bridge):
            # wait until no build is running any more, then the program must stay up for 6 s
            deadline = time.time() + 300
            idle_since = None
            while time.time() < deadline and p.poll() is None:
                text = b"".join(chunks).decode("utf-8", "replace")
                if "Build failed" in text or "Traceback" in text:
                    break
                if building(p.pid):
                    idle_since = None
                elif idle_since is None:
                    idle_since = time.time()
                elif time.time() - idle_since > 6:
                    break
                time.sleep(0.5)
            text = b"".join(chunks).decode("utf-8", "replace")
            up = p.poll() is None and "Build failed" not in text and "Traceback" not in text
            emit(lang, "f5", up, f"exit={p.poll()} cwd={spec.cwd}\n{text[-1200:]}", t0)
            kill_tree(p)
        except Exception:  # noqa: BLE001
            emit(lang, "f5", False, traceback.format_exc(), t0)
print("DONE", flush=True)
