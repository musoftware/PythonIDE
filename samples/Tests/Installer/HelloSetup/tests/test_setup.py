r"""Builds Hello Setup, makes its setup.exe, installs it silently into a temporary folder, starts the
installed program, then uninstalls it silently and checks that everything is gone.

    python tests/test_setup.py            (run with the IDE's Python: .venv\Scripts\python.exe)

The project is copied to a temporary folder first, so this sample stays clean (no Publish/ folder)."""
import shutil
import subprocess
import sys
import tempfile
import time
import winreg
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
IDE = HERE.parents[3]
sys.path.insert(0, str(IDE))
from radide.deploy import config, inno  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix="radide_setup_test_"))
work = tmp / "HelloSetup"
shutil.copytree(HERE, work, ignore=shutil.ignore_patterns("Publish", "tests", "__pycache__"))
ok = True


def check(cond, text):
    global ok
    ok &= bool(cond)
    print(("PASS " if cond else "FAIL ") + text, flush=True)


try:
    cfg = config.load(work)
    res = inno.publish(work, cfg)
    check(res.setup and res.setup.is_file(), f"setup made: {res.setup.name if res.setup else '-'}")
    target = tmp / "installed"
    r = subprocess.run([str(res.setup), *inno.silent_install_args(target)], timeout=600)
    exe = target / res.exe
    check(r.returncode == 0 and exe.is_file(), "silent install")
    key = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{cfg.app_id}_is1"
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, key)
        check(True, "listed in Apps & features")
    except OSError:
        check(False, "listed in Apps & features")
    p = subprocess.Popen([str(exe)])
    time.sleep(5)
    check(p.poll() is None, "installed program starts")
    p.kill()
    p.wait()
    r = subprocess.run([str(target / "unins000.exe"), *inno.SILENT_UNINSTALL_ARGS], timeout=600)
    for _ in range(40):
        if not exe.exists():
            break
        time.sleep(0.5)
    check(r.returncode == 0 and not exe.exists(), "silent uninstall removed the program")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
