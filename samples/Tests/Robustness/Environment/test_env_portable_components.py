"""Portable mode: user component packages live in <install>\\settings\\components, never in %APPDATA%.

    python samples/Tests/Robustness/Environment/test_env_portable_components.py [scratch folder]

A portable release build is simulated in this process (sys.frozen, sys._radide_exe = <install>\\RADIDE.exe,
portable.flag beside it); APPDATA / LOCALAPPDATA point to a fake user profile. Checks: user_components_dir() follows
paths.roaming_dir() (portable: <install>\\settings\\components), a .radcomp installed for the user lands there and is
discovered, nothing is written into the fake profile; without portable.flag it is %APPDATA%\\RADIDE\\components again;
RADIDE_COMPONENTS_DIR still overrides both.
Exit code = number of failures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _envlib as E  # noqa: E402
from _envlib import ok  # noqa: E402

sys.path.insert(0, str(E.REPO))
ROOT = E.scratch("portable_components")
inst = ROOT / "RADIDE-portable"
inst.mkdir(parents=True)
(inst / "RADIDE.exe").write_bytes(b"MZ")
profile = ROOT / "Users" / E.USER_AR
for d in ("AppData/Local", "AppData/Roaming"):
    (profile / d).mkdir(parents=True, exist_ok=True)
os.environ["LOCALAPPDATA"] = str(profile / "AppData/Local")
os.environ["APPDATA"] = str(profile / "AppData/Roaming")
os.environ.pop("RADIDE_COMPONENTS_DIR", None)

from radide import paths  # noqa: E402
from radide import components as C  # noqa: E402

real_exe = sys.executable
sys.frozen = True
sys._radide_exe = str(inst / "RADIDE.exe")
try:
    (inst / paths.PORTABLE_FLAG).write_text("", encoding="utf-8")
    paths._SETTINGS_WRITABLE.clear()
    ok("portable.flag: portable mode", paths.portable())
    d = C.user_components_dir()
    ok("user components folder = <install>\\settings\\components", d == inst.resolve() / "settings" / "components", d)
    ok("same root as paths.roaming_dir()", d.parent == paths.roaming_dir(), (d, paths.roaming_dir()))
    pkg = C.install_package(E.REPO / "samples" / "Tests" / "Components" / "StarRating.radcomp", reload=False)
    ok("a .radcomp installed for the user lands in the portable folder",
       (d / pkg.name / C.MANIFEST).is_file(), sorted(p.name for p in d.iterdir()))
    found = [p.name for p in C._package_folders(d)]
    ok("and is found there", pkg.name in found or any(pkg.name in f for f in found), found)
    leaked = [str(p.relative_to(profile)) for p in profile.rglob("*") if p.is_file() or
              (p.is_dir() and "RADIDE" in p.name)]
    ok("nothing written into the user profile (%APPDATA% / %LOCALAPPDATA%)", not leaked, leaked)
    C.uninstall_package(pkg.name, reload=False)
    ok("uninstall from the portable folder", not (d / pkg.name).exists())

    (inst / paths.PORTABLE_FLAG).unlink()
    paths._SETTINGS_WRITABLE.clear()
    ok("installed (no portable.flag): %APPDATA%\\RADIDE\\components",
       C.user_components_dir(create=False) == profile / "AppData/Roaming" / "RADIDE" / "components",
       C.user_components_dir(create=False))
    os.environ["RADIDE_COMPONENTS_DIR"] = str(ROOT / "custom")
    ok("RADIDE_COMPONENTS_DIR overrides", C.user_components_dir(create=False) == ROOT / "custom")
    os.environ.pop("RADIDE_COMPONENTS_DIR")
finally:
    del sys.frozen
    del sys._radide_exe
    sys.executable = real_exe

sys.exit(E.summary("Environment: portable component packages"))
