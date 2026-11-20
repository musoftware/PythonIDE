"""Start RAD IDE without a console window (used by Windows file associations, Explorer menus and the
Start Menu shortcut):  pythonw.exe <repo>\\radide\\launch.pyw [path] [--line N] [--new-window] ...

Equivalent to ``python -m radide`` run from the repository folder."""
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[0] = _root                    # the repository (never this folder: radide/*.py must not shadow packages)

if sys.stdout is None or sys.stderr is None:          # pythonw: keep print() / tracebacks in a log file
    try:
        _log_dir = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "RADIDE")
        os.makedirs(_log_dir, exist_ok=True)
        _log = open(os.path.join(_log_dir, "radide.log"), "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or _log
        sys.stderr = sys.stderr or _log
    except OSError:
        sys.stdout = sys.stdout or open(os.devnull, "w")  # noqa: SIM115
        sys.stderr = sys.stderr or open(os.devnull, "w")  # noqa: SIM115

from radide.shell_integration import no_console_children  # noqa: E402

no_console_children()

from radide.app import main  # noqa: E402

sys.exit(main())
