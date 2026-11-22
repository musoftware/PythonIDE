"""Shared helpers of the environment robustness tests (PASS / FAIL lines, summary, scratch folders,
Win32 file locks, read-only folders without admin rights, killing only the processes started here)."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes as wt
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PY = str(REPO / ".venv" / "Scripts" / "python.exe") if (REPO / ".venv" / "Scripts" / "python.exe").is_file() \
    else sys.executable
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

ARABIC = "مشاريع عربية"
USER_AR = "محمود"
GUI_ENV = {"PYTHONIOENCODING": "utf-8", "QT_QPA_PLATFORM": "offscreen", "QT_QPA_FONTDIR": r"C:\Windows\Fonts",
           "RADIDE_NO_BROWSER": "1", "QTWEBENGINE_CHROMIUM_FLAGS": "--disable-gpu --disable-gpu-compositing",
           "RADIDE_TEST_NO_DIALOGS": "1"}
TEST_ORG = "RADIDE-TEST-ENV"

results: list[tuple[str, bool, str]] = []


def ok(name: str, cond, detail: str = "") -> bool:
    results.append((name, bool(cond), str(detail)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{str(detail)[:800]}]" if detail and not cond else ""),
          flush=True)
    return bool(cond)


def info(text: str) -> None:
    print("INFO " + text, flush=True)


def summary(title: str) -> int:
    fails = [r for r in results if not r[1]]
    print(f"\n==== {title}: {len(results) - len(fails)}/{len(results)} passed, {len(fails)} failed", flush=True)
    for n, _, d in fails:
        print(f"  FAIL {n}  {d[:300]}", flush=True)
    return len(fails)


def scratch(name: str) -> Path:
    base = Path(os.environ.get("RADIDE_ENV_SCRATCH") or Path(tempfile.gettempdir()) / "radide-envrob")
    d = base / name
    rmtree(d)
    d.mkdir(parents=True, exist_ok=True)
    return d


def rmtree(p: Path) -> None:
    """Remove a folder (also read-only files, junctions are unlinked, never followed)."""
    p = Path(p)
    if not os.path.lexists(p):
        return
    subprocess.run(["icacls", str(p), "/reset", "/T", "/C", "/Q"], capture_output=True)
    subprocess.run(["attrib", "-R", str(p / "*"), "/S", "/D"], capture_output=True)

    def onerr(func, path, _exc):
        try:
            os.chmod(path, 0o666)
            func(path)
        except OSError:
            pass
    for root, dirs, _files in os.walk(p):
        for d in list(dirs):
            full = os.path.join(root, d)
            if _is_junction(full):
                os.rmdir(full)
                dirs.remove(d)
    if _is_junction(str(p)):
        os.rmdir(p)
        return
    shutil.rmtree("\\\\?\\" + str(p.resolve()) if len(str(p)) > 240 else p, onerror=onerr)


def _is_junction(path: str) -> bool:
    try:
        return bool(os.path.isjunction(path)) if hasattr(os.path, "isjunction") else \
            bool(os.lstat(path).st_file_attributes & 0x400)
    except OSError:
        return False


def snapshot(folder: Path) -> dict:
    return {str(p.relative_to(folder)): p.read_bytes() for p in Path(folder).rglob("*") if p.is_file()}


# ------------------------------------------------------------------ Win32 helpers
k32 = ctypes.WinDLL("kernel32", use_last_error=True)
k32.CreateFileW.restype = wt.HANDLE
k32.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
INVALID = wt.HANDLE(-1).value


def lock_in_child(path: Path, share: int = 0, seconds: float = 30) -> subprocess.Popen:
    """Another process opens *path* like Excel does (share 0 = exclusive, 1 = FILE_SHARE_READ) and keeps it
    open; the returned process prints LOCKED when the handle is held."""
    code = (
        "import ctypes, sys, time\n"
        "from ctypes import wintypes as wt\n"
        "k = ctypes.WinDLL('kernel32', use_last_error=True)\n"
        "k.CreateFileW.restype = wt.HANDLE\n"
        "k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]\n"
        f"h = k.CreateFileW(sys.argv[1], 0x80000000 | 0x40000000, {share}, None, 3, 0x80, None)\n"
        "print('LOCKED' if h != wt.HANDLE(-1).value else 'NOLOCK %d' % ctypes.get_last_error(), flush=True)\n"
        f"time.sleep({seconds})\n")
    p = subprocess.Popen([PY, "-c", code, str(path)], stdout=subprocess.PIPE, text=True)
    line = p.stdout.readline().strip()
    if line != "LOCKED":
        p.kill()
        raise RuntimeError(f"could not lock {path}: {line}")
    return p


def deny_create(folder: Path) -> bool:
    """Make *folder* read-only for the current user without admin rights: an ACL deny of 'create files /
    create folders / delete child' on a folder this test created and owns."""
    r = subprocess.run(["icacls", str(folder), "/deny", f"{os.environ.get('USERNAME', '')}:(WD,AD,DC)"],
                       capture_output=True, text=True)
    return r.returncode == 0


def deny_write_all(folder: Path) -> bool:
    """Read-only folder and files (inherited deny of write data / append / attributes / delete)."""
    r = subprocess.run(["icacls", str(folder), "/deny",
                        f"{os.environ.get('USERNAME', '')}:(OI)(CI)(WD,AD,WEA,WA,DC)"], capture_output=True, text=True)
    return r.returncode == 0


def allow_again(folder: Path) -> None:
    subprocess.run(["icacls", str(folder), "/remove:d", os.environ.get("USERNAME", ""), "/T", "/C", "/Q"],
                   capture_output=True)


def make_sparse(path: Path, size: int) -> None:
    """A *size* byte file that takes no disk space (FSCTL_SET_SPARSE; no admin needed on one's own file)."""
    with open(path, "wb") as f:
        import msvcrt
        h = msvcrt.get_osfhandle(f.fileno())
        ret = wt.DWORD()
        ctypes.windll.kernel32.DeviceIoControl(wt.HANDLE(h), 0x000900C4, None, 0, None, 0, ctypes.byref(ret), None)
        f.seek(size - 1)
        f.write(b"\0")


def kill_tree(p: subprocess.Popen) -> None:
    """Only a process this test started (and its children)."""
    if p.poll() is None:
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    try:
        p.wait(10)
    except subprocess.TimeoutExpired:
        pass


def child_env(**extra) -> dict:
    env = dict(os.environ, **GUI_ENV)
    env["PYTHONPATH"] = str(REPO)
    env.update({k: str(v) for k, v in extra.items()})
    return env


def run_report(cmd: list[str], env: dict, timeout: float = 600) -> tuple[dict, str]:
    """Run a child that prints 'REPORT {json}'. Its output goes to a FILE and we wait for the process itself:
    a QtWebEngine helper process inherits pipes and would keep communicate() waiting after the child ended.
    On timeout the whole process tree (only the one started here) is killed. Returns (report, output)."""
    import tempfile as _tf
    with _tf.NamedTemporaryFile("w+b", suffix=".log", delete=False) as out:
        path = out.name
    with open(path, "wb") as out:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, env=env)
        try:
            p.wait(timeout)
        except subprocess.TimeoutExpired:
            pass
        kill_tree(p)
    text = Path(path).read_bytes().decode("utf-8", "replace")
    try:
        os.remove(path)
    except OSError:
        pass
    line = next((ln for ln in reversed(text.splitlines()) if ln.startswith("REPORT ")), None)
    import json as _json
    return (_json.loads(line[7:]) if line else {}), text


def wait_for(fn, timeout: float = 30, step: float = 0.2):
    t = time.time()
    while time.time() - t < timeout:
        v = fn()
        if v:
            return v
        time.sleep(step)
    return None
