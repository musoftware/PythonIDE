"""Shell commands that run one of RAD IDE's own modules (``python -m radide....``) from any folder.

The IDE runs a plugin's ``build_command`` with the project folder as the current directory and without
PYTHONPATH, so a plain ``python -m radide.retro.dev.build`` fails there with "No module named 'radide'"
(RAD IDE runs from its source folder, it is not an installed package).  ``module_command`` puts the IDE's
folder on sys.path first and then runs the module exactly like ``-m`` does (runpy, __main__, argv kept).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

IDE_ROOT = Path(__file__).resolve().parents[2]


def module_argv(module: str, *args) -> list[str]:
    boot = (f"import sys; sys.path.insert(0, {str(IDE_ROOT)!r}); import runpy; "
            f"runpy.run_module({module!r}, run_name='__main__', alter_sys=True)")
    return [sys.executable or "python", "-c", boot] + [str(a) for a in args]


def module_command(module: str, *args) -> str:
    """One shell command string (for build_command) running ``python -m <module> <args>``."""
    return subprocess.list2cmdline(module_argv(module, *args))


__all__ = ["IDE_ROOT", "module_argv", "module_command"]
