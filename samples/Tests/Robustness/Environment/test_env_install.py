"""Environment robustness - the IDE installed under Program Files (read-only for the user), frozen-build paths.

    .venv\\Scripts\\python samples\\Tests\\Robustness\\Environment\\test_env_install.py

A release build is simulated in this process (sys.frozen, sys._MEIPASS = <install>\\_internal, RADIDE.exe) with an
install folder that the user cannot write to (ACL deny on a folder this test owns - no admin rights, no real
Program Files) and LOCALAPPDATA / APPDATA in an Arabic user folder:
  * paths.frozen / install_dir / resource_root / user_data_dir point to the right places;
  * python_root() puts its junction pyroot\\radide -> _internal\\radide into the user's data folder and a real
    Python imports the radide package through it;
  * a portable.flag in a read-only install folder no longer stops the IDE: it falls back to the registry /
    %LOCALAPPDATA% (setup_portable_settings returns False instead of raising PermissionError);
    in a writable folder the portable mode still works;
  * the log, recovery snapshots, save backups and long-path aliases all go to the user data folder;
  * nothing at all is written into the install folder.
Exit code = number of failures."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _envlib as E  # noqa: E402
from _envlib import ok  # noqa: E402

ROOT = E.scratch("install")
inst = ROOT / "Program Files" / "RAD IDE"
internal = inst / "_internal"
internal.mkdir(parents=True)
(internal / "radide").mkdir()               # a minimal bundled package (no junction into the repository)
for name in ("__init__.py", "paths.py"):
    (internal / "radide" / name).write_bytes((E.REPO / "radide" / name).read_bytes())
(inst / "RADIDE.exe").write_bytes(b"MZ")
user = ROOT / "Users" / f"{E.USER_AR}"
for d in ("AppData/Local", "AppData/Roaming"):
    (user / d).mkdir(parents=True, exist_ok=True)
os.environ["LOCALAPPDATA"] = str(user / "AppData/Local")
os.environ["APPDATA"] = str(user / "AppData/Roaming")

ok("install folder made read-only for the user (ACL, no admin)", E.deny_write_all(inst))
before = sorted(str(p.relative_to(inst)) for p in inst.iterdir())
try:
    (inst / "probe.txt").write_text("x")
    writable = True
except OSError:
    writable = False
ok("the simulated Program Files folder really refuses writes", not writable)

real_exe = sys.executable
sys.frozen = True
sys._MEIPASS = str(internal)
sys._radide_exe = str(inst / "RADIDE.exe")
from radide import paths  # noqa: E402

ok("frozen() is True", paths.frozen())
ok("install_dir() is the folder of RADIDE.exe", paths.install_dir() == inst.resolve(), paths.install_dir())
ok("resource_root() is _internal", Path(paths.resource_root()) == internal, paths.resource_root())
ok("user_data_dir() is %LOCALAPPDATA%\\RADIDE (Arabic user folder)",
   paths.user_data_dir() == user / "AppData/Local" / "RADIDE", paths.user_data_dir())
ok("not portable without portable.flag", not paths.portable())

E.allow_again(inst)
(inst / paths.PORTABLE_FLAG).write_text("")
E.deny_write_all(inst)
paths._SETTINGS_WRITABLE.clear()
ok("portable.flag in a read-only folder: falls back to the installed mode", not paths.portable())
try:
    r = paths.setup_portable_settings()
    err = None
except Exception as e:  # noqa: BLE001
    r, err = None, e
ok("setup_portable_settings() does not raise in a read-only install (start-up keeps going)", err is None and r is False,
   repr(err))

root = paths.python_root()
ok("python_root() is <user data>\\pyroot (not the install folder)", root == paths.user_data_dir() / "pyroot", root)
ok("pyroot\\radide is a junction to _internal\\radide", (root / "radide" / "__init__.py").is_file())
r = subprocess.run([real_exe, "-I", "-X", "utf8", "-c", "import sys; sys.path.insert(0, sys.argv[1]); import radide.paths as p; "
                    "print(p.__file__)", str(root)], capture_output=True, text=True, encoding="utf-8",
                   env=dict(os.environ, PYTHONIOENCODING="utf-8"))
ok("a real Python imports radide through the junction in the Arabic user folder",
   r.returncode == 0 and "pyroot" in r.stdout, r.stdout + r.stderr[-400:])

saved_out, saved_err = sys.stdout, sys.stderr
sys.stdout = sys.stderr = None
try:
    paths._log_streams()
    print("log line from a windowed exe")
    sys.stdout.flush()
finally:
    log_target = getattr(sys.stdout, "name", "")
    sys.stdout, sys.stderr = saved_out, saved_err
ok("the windowed exe's log goes to <user data>\\radide.log", str(paths.user_data_dir()) in str(log_target), log_target)

from radide import safeio  # noqa: E402
proj = ROOT / "proj"
proj.mkdir()
(proj / "a.txt").write_text("v1")
safeio.atomic_write_text(proj / "a.txt", "v2", backup=True)
ok("save backups go to the user data folder", str(safeio.recovery_root()).startswith(str(paths.user_data_dir())))
deep = ROOT / "/".join(["deep_segment_folder"] * 8)
deep.mkdir(parents=True)
alias = paths.short_alias(deep)
ok("long-path alias junctions live in the user data folder", str(alias).startswith(str(paths.user_data_dir())), alias)

after = sorted(str(p.relative_to(inst)) for p in inst.iterdir())
ok("nothing was written into the install folder", after == before + [paths.PORTABLE_FLAG] or after == sorted(
    before + [paths.PORTABLE_FLAG]), (before, after))

# writable portable install still works
E.allow_again(inst)
paths._SETTINGS_WRITABLE.clear()
ok("portable.flag in a writable folder: portable mode", paths.portable())
ok("portable settings go to <install>\\settings", (inst / "settings").is_dir())

del sys.frozen
E.allow_again(inst)
sys.exit(E.summary("Environment: Program Files install / frozen paths"))
