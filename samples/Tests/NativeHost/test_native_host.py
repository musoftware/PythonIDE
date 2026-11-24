"""The native GUI Bridge host radbridge.exe (radide/runtimes/native_host.py) with real programs of every language.

    .venv\\Scripts\\python samples\\Tests\\NativeHost\\test_native_host.py [scratch] [lang,lang...]

For one example project per GUI Bridge language (samples/Examples/<Lang>, copied to scratch): the F5 run spec
of the language plugin must start radbridge.exe (not the Python host), the build step runs, a top-level window of
radbridge.exe with the startup form's caption appears within the time limit (the program answered Form_Load),
and Stop (killing the host) also ends the program. Languages whose tool is not installed are SKIPped with the
reason the run spec gives. Exit code = number of FAILs.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))

from radide.languages import get_plugin  # noqa: E402
from radide.model import Project  # noqa: E402
from radide.runtimes import native_host as NH  # noqa: E402

EXAMPLES = REPO / "samples" / "Examples"
LANGS = {"c-bridge": "C", "cpp-bridge": "Cpp", "fortran-bridge": "Fortran", "rust-bridge": "Rust", "go-bridge": "Go",
         "lua-bridge": "Lua", "ruby-bridge": "Ruby", "perl-bridge": "Perl", "java-bridge": "Java",
         "dart-bridge": "Dart", "javascript": "JavaScript", "typescript": "TypeScript",
         "powershell-bridge": "PowerShell", "php-bridge": "PHP"}
U32 = ctypes.windll.user32


def windows_of(pids: set[int]) -> list[str]:
    out = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _l):
        pid = wt.DWORD()
        U32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and U32.IsWindowVisible(h):
            n = U32.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            U32.GetWindowTextW(h, b, n + 1)
            if b.value:
                out.append(b.value)
        return True
    U32.EnumWindows(cb, 0)
    return out


def alive(pid: int) -> bool:
    h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    code = wt.DWORD()
    ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(h)
    return code.value == 259


def children(pid: int) -> list[int]:
    r = subprocess.run(["powershell", "-NoProfile", "-c",
                        f"(Get-CimInstance Win32_Process -Filter 'ParentProcessId={pid}').ProcessId"],
                       capture_output=True, text=True)
    return [int(x) for x in r.stdout.split() if x.isdigit()]


def example_for(lang: str) -> Path | None:
    """The first example whose forms radforms can draw (else the first one: its run reports why not)."""
    from radide.deploy.native import radforms_gen as rg
    d = EXAMPLES / LANGS[lang]
    first = None
    for p in sorted(d.glob("*/project.radproj")) if d.is_dir() else []:
        try:
            pr = Project.load(p.parent)
        except Exception:  # noqa: BLE001
            continue
        if pr.language == lang and pr.forms:
            first = first or p.parent
            if not rg.unsupported(pr, p.parent, lang):
                return p.parent
    return first


def main() -> int:
    args = [a for a in sys.argv[1:]]
    only = None
    if args and "," in args[-1] or (args and args[-1] in LANGS):
        only = set(args.pop().split(","))
    scratch = Path(args[0]) if args else Path(tempfile.mkdtemp(prefix="radide_native_host_"))
    if NH.build(print) is None:
        print("FAIL  radbridge.exe builds -", NH.LAST_ERROR)
        return 1
    print("PASS  radbridge.exe builds -", NH.host_path())
    fails = 0
    for lang in LANGS:
        if only and lang not in only:
            continue
        src = example_for(lang)
        if src is None:
            print(f"SKIP  {lang}: no example project")
            continue
        dst = scratch / f"{lang}_{src.name}"
        if dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("_build", "node_modules", "target", "bin", "obj"))
        plugin = get_plugin(lang)
        project = Project.load(dst)
        spec = plugin.run_spec(dst, project.startup, "")
        if Path(spec.program).name.lower() != "radbridge.exe":
            note = (spec.env or {}).get("RAD_HOST_NOTE", "")
            verdict = "SKIP" if "tool is missing" in note or "cannot draw" in note else "FAIL"
            fails += verdict == "FAIL"
            print(f"{verdict}  {lang}: Python host - {note}")
            continue
        log = dst / "_run.log"
        with open(log, "wb") as fh:
            p = subprocess.Popen([spec.program, *spec.args], cwd=str(spec.cwd), env=spec.env, stdout=fh,
                                 stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        caption = ""
        try:
            from radide.model import Form
            caption = Form.load(project.form_path(project.startup)).props.get("Text", "") or project.startup
        except Exception:  # noqa: BLE001
            pass
        t0, wins = time.time(), []
        while time.time() - t0 < 240 and p.poll() is None:
            wins = windows_of({p.pid})
            if wins:
                break
            time.sleep(0.5)
        kids = children(p.pid)
        time.sleep(1.0)
        ok = bool(wins) and p.poll() is None
        out = log.read_text(encoding="utf-8", errors="replace")
        p.kill()
        p.wait(10)
        time.sleep(1.5)
        left = [k for k in kids if alive(k)]
        print(f"{'PASS' if ok and not left else 'FAIL'}  {lang} ({src.name}): window {wins[:2]} "
              f"(form '{caption}'){' - program still running after Stop: ' + str(left) if left else ''}"
              f"{'' if ok else ' - output: ' + out.strip()[-600:]}")
        fails += not (ok and not left)
        for k in left:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(k)], capture_output=True)
    print(f"\n{fails} failed")
    return fails


if __name__ == "__main__":
    sys.exit(main())
