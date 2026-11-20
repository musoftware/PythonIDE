"""Entry script of the RAD IDE release build (RADIDE.exe, tools/build_ide_release.py).

    RADIDE.exe [path ...] [--new-window] ...     the IDE (radide.app.main)
    RADIDE.exe --register / --unregister ...     Windows shell integration only (installer / uninstaller)
    RADIDE.exe -c code | -m module | script.py   only when the IDE found no Python and started this exe as
                                                 its "Python" (RADIDE_AS_PYTHON=1): radide.paths.run_as_python
"""
import os
import sys

from radide import paths

if os.environ.get("RADIDE_AS_PYTHON") == "1" and paths.wants_python(sys.argv):
    sys.exit(paths.run_as_python(sys.argv))
os.environ.pop("RADIDE_AS_PYTHON", None)

if any(a in ("--register", "--unregister", "--shell-status") for a in sys.argv[1:]):
    sys._radide_exe = sys.executable          # no Python search, no window: just the registry work
else:
    paths.prepare_frozen()
    if paths.frozen() and sys.executable == getattr(sys, "_radide_exe", None):      # no real Python on this machine: RADIDE.exe stands in
        os.environ["RADIDE_AS_PYTHON"] = "1"

from radide.app import main  # noqa: E402

sys.exit(main())
