"""Which Python runs and debugs a project: the real python.exe behind a Store alias, the project's .venv,
Python / debugpy versions, and the debugpy adapter for a debuggee (moved out of radide/app.py; no Qt).

MainWindow keeps the parts that need the window (Tools > Options value, the Locate dialog, installing debugpy
with its output in the Output window) and calls these.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


_REAL_PY: dict[str, str] = {}


def real_python(exe: str) -> str:
    """The real python.exe behind a Windows Store / App Execution Alias (WindowsApps) or py launcher:
    debuggers and launchers cannot start the alias itself."""
    if exe in _REAL_PY:
        return _REAL_PY[exe]
    real = exe
    low = exe.lower()
    if "windowsapps" in low or Path(low).name in ("py.exe", "py"):
        import subprocess
        try:
            out = subprocess.run([exe, "-c", "import sys; print(sys.executable)"], capture_output=True,
                                 text=True, timeout=20).stdout.strip()
            if out and Path(out).exists() and "windowsapps" not in out.lower():
                real = out
        except (OSError, subprocess.TimeoutExpired):
            pass
    _REAL_PY[exe] = real
    return real


def _has_debugpy() -> bool:
    """debugpy for the DAP engine: the IDE's own Python, or (release build) the real Python of radide/paths.py."""
    if getattr(sys, "frozen", False):
        from .paths import python_has_module
        return python_has_module(sys.executable, "debugpy")
    import importlib.util
    return importlib.util.find_spec("debugpy") is not None


_PY_INFO: dict[str, tuple[str, str]] = {}


def python_info(python: str, refresh: bool = False) -> tuple[str, str]:
    """(Python version, debugpy version or "") of *python* (cached; "" / "" when it cannot be asked)."""
    key = os.path.normcase(str(python))
    if refresh or key not in _PY_INFO:
        ver, dbg = "", ""
        try:
            import subprocess
            from .paths import NO_WINDOW
            out = subprocess.run([python, "-c", "import sys, importlib.util as u; print(sys.version.split()[0]); "
                                  "s = u.find_spec('debugpy'); print(__import__('debugpy').__version__ if s else '')"],
                                 capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW,
                                 env={k: v for k, v in os.environ.items() if k not in ("PYTHONHOME", "PYTHONPATH")})
            lines = (out.stdout or "").splitlines()
            ver = lines[0].strip() if lines else ""
            dbg = lines[1].strip() if len(lines) > 1 else ""
        except Exception:  # noqa: BLE001
            pass
        _PY_INFO[key] = (ver, dbg)
    return _PY_INFO[key]


def debugpy_adapter_for(python: str, install=None, log=None) -> tuple[list[str] | None, str]:
    """The debugpy adapter for debugging a program that runs with *python* - the debuggee always runs with *python*
    (the same interpreter as Run), only the adapter process may differ:
      1. *python*'s own debugpy;
      2. the IDE's debugpy (source checkout: its .venv; release build: the real Python of radide/paths.py) - its
         launcher injects that debugpy into the debuggee, which works for every Python version debugpy supports;
      3. install(python) -> True: debugpy installed into *python* on demand (pip), then 1.
    Returns (argv or None, a description for the Output window)."""
    ver, dbg = python_info(python)
    if dbg:
        return [python, "-m", "debugpy.adapter"], f"debugpy {dbg} of this interpreter"
    ide_py = sys.executable
    if _has_debugpy() and os.path.normcase(ide_py) != os.path.normcase(str(python)):
        _iv, idbg = python_info(ide_py)
        if idbg and _debugpy_supports(idbg, ver):
            return [ide_py, "-m", "debugpy.adapter"], f"debugpy {idbg} of the IDE ({ide_py})"
    if install is not None and install(python):
        _ver, dbg = python_info(python, refresh=True)
        if dbg:
            return [python, "-m", "debugpy.adapter"], f"debugpy {dbg} (installed into this interpreter)"
    return None, ""


def _debugpy_supports(debugpy_version: str, python_version: str) -> bool:
    """debugpy >= 1.8.17 debugs Python 3.14, >= 1.8.0 3.12/3.13; anything older: 3.11 at most."""
    def key(v):
        try:
            return tuple(int(x) for x in re.findall(r"\d+", v)[:3])
        except ValueError:
            return ()
    d, p = key(debugpy_version), key(python_version)[:2]
    if not d or not p:
        return True                       # unknown: let debugpy decide
    if p >= (3, 14):
        return d >= (1, 8, 17)
    if p >= (3, 12):
        return d >= (1, 8, 0)
    return True


def project_venv_python(folder: Path) -> str:
    """<folder>/.venv's python (Windows or POSIX layout), or "" when the project has no venv."""
    for rel in ((".venv", "Scripts", "python.exe"), (".venv", "bin", "python")):
        p = Path(folder).joinpath(*rel)
        if p.is_file():
            return str(p)
    return ""
