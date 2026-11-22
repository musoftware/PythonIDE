"""Where RAD IDE's own files are - a source checkout or a frozen release build (PyInstaller --onedir,
tools/build_ide_release.py) - and the frozen build's start-up preparation.

    resource_root()   the folder holding the ``radide`` package and ``docs``: the repository, or
                      ``<install>\\_internal`` (sys._MEIPASS) in a release build. Every module that finds
                      its data with ``Path(__file__).parent`` keeps working because the release build
                      copies the whole radide tree (data files and .py sources) to the same relative place.
    install_dir()     the folder of RADIDE.exe (release) or the repository (source)
    ide_exe()         RADIDE.exe of a release build (sys.executable of a source run)
    portable()        a release build with ``portable.flag`` beside RADIDE.exe: settings live in
                      ``<install>\\settings`` (QSettings IniFormat) instead of the registry, and the
                      Windows shell integration is never registered automatically

A frozen IDE has no Python of its own for the programs it runs (user projects, pylsp, debugpy, Jupyter
kernels, PyInstaller, the language bridges and runtime helpers in radide/runtimes). ``prepare_frozen()``
therefore looks for a real Python interpreter - RADIDE_PYTHON, the ``options/ide_python`` setting, the
py launcher, python on PATH, the usual install folders - and makes it ``sys.executable``; RADIDE.exe stays
available as ``ide_exe()``. Without any Python, RADIDE.exe itself answers ``-c`` / ``-m`` / script
command lines (``run_as_python``) with the modules bundled in the build.
No Qt import at module level."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

PORTABLE_FLAG = "portable.flag"
GITHUB_REPO = "musoftware/PythonIDE"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    if frozen():
        return Path(getattr(sys, "_MEIPASS", None) or Path(ide_exe()).parent)
    return Path(__file__).resolve().parent.parent


def package_dir() -> Path:
    return resource_root() / "radide"


def ide_exe() -> str:
    return getattr(sys, "_radide_exe", None) or sys.executable


def install_dir() -> Path:
    return Path(ide_exe()).resolve().parent if frozen() else resource_root()


_PY_ROOT: Path | None = None


def python_root() -> Path:
    """The folder a REAL Python (the user's, another version than the frozen IDE) puts on sys.path to
    import the radide package: the repository in a source checkout. In a release build NOT _internal - it
    also holds the frozen IDE's own extension modules (_sqlite3.pyd, _ssl.pyd ... built for its Python),
    which another Python version would load ("Module use of python312.dll conflicts with this version of
    Python"). Instead <user data>\\pyroot holds only a junction radide -> _internal\\radide."""
    global _PY_ROOT
    if _PY_ROOT is not None:
        return _PY_ROOT
    if not frozen():
        _PY_ROOT = resource_root()
        return _PY_ROOT
    target = package_dir()
    root = user_data_dir() / "pyroot"
    link = root / "radide"
    try:
        root.mkdir(parents=True, exist_ok=True)
        ok = False
        if os.path.lexists(link):
            try:
                ok = os.path.normcase(os.path.realpath(link)) == os.path.normcase(os.path.realpath(target))
            except OSError:
                ok = False
            if not ok:
                try:
                    os.rmdir(link)          # a junction: removes the link only, never the target
                except OSError:
                    shutil.rmtree(link, ignore_errors=True) if not os.path.islink(link) else os.unlink(link)
        if not ok:
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        _PY_ROOT = root if (link / "__init__.py").is_file() else resource_root()
    except Exception:  # noqa: BLE001 - no junction possible: the old behaviour (works when the versions match)
        _PY_ROOT = resource_root()
    return _PY_ROOT


# ----------------------------------------------------------------------------------- long paths
# Windows refuses a working directory longer than MAX_PATH (CreateProcess: "The directory name is invalid")
# even with LongPathsEnabled, and most toolchains (MSVC link.exe LNK1104, MSBuild, windres, fbc, gcc, Go)
# still fail on file names over 260 characters. A build or run of a project in a deep folder therefore
# goes through a short junction %LOCALAPPDATA%\RADIDE\sp\<hash> -> the folder (no admin rights needed;
# removing a junction never touches the target).
LONG_PATH_LIMIT = 100           # a folder longer than this gets a short alias (tools add ~150 characters)


def _plain(path: str) -> str:
    """'\\\\?\\C:\\x' -> 'C:\\x' and '\\\\?\\UNC\\srv\\share' -> '\\\\srv\\share'."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path


def short_alias(folder, limit: int = LONG_PATH_LIMIT) -> Path:
    """*folder* itself when its path is short (or it is not a local folder), otherwise a short junction
    pointing at it. The alias is reused for the same folder and repaired when it points elsewhere."""
    folder = Path(_plain(str(folder)))
    if os.name != "nt" or len(str(folder)) <= limit or str(folder).startswith("\\\\") or not folder.is_dir():
        return folder
    import hashlib
    key = hashlib.sha1(os.path.normcase(str(folder)).encode("utf-8")).hexdigest()[:10]
    root = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE" / "sp"
    if portable():
        root = settings_dir() / "sp"
    link = root / key
    try:
        root.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(link):
            try:
                same = os.path.normcase(_plain(os.path.realpath(link))) == os.path.normcase(
                    _plain(os.path.realpath(folder)))
            except OSError:
                same = False
            if same:
                return link
            os.rmdir(link)                          # a stale junction: only the link goes
        import _winapi
        _winapi.CreateJunction(str(folder), str(link))
        return link if link.is_dir() else folder
    except Exception:  # noqa: BLE001 - no junction possible (FAT32, network drive): the long path
        return folder


def ansi_safe(path) -> str:
    """*path* as a program that uses the ANSI Windows API (MinGW gcc / as / ld, fbc, many build tools) can open
    it: unchanged when every character exists in the ANSI code page, else its 8.3 short name (an Arabic or
    Chinese user name on an English Windows: C:\\Users\\محمود\\AppData -> C:\\Users\\5D1F~1\\AppData).
    Unchanged when the volume has no short names."""
    s = str(path)
    if os.name != "nt" or s.isascii():
        return s
    try:
        s.encode("mbcs")                       # strict: no best-fit "?" replacement
        return s
    except UnicodeEncodeError:
        pass
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(32768)
        n = ctypes.windll.kernel32.GetShortPathNameW(s, buf, 32768)
        return buf.value if 0 < n < 32768 else s
    except Exception:  # noqa: BLE001
        return s


def ansi_env(env=None) -> dict:
    """A copy of *env* (default os.environ) whose TEMP / TMP an ANSI program can use (ansi_safe): gcc writes
    its temporary .s / .o files there and fails with "can't create ...?????.o" otherwise."""
    env = dict(os.environ if env is None else env)
    for k in ("TEMP", "TMP"):
        if env.get(k):
            env[k] = ansi_safe(env[k])
    return env


def is_long(path, limit: int = LONG_PATH_LIMIT) -> bool:
    return len(_plain(str(path))) > limit


_SETTINGS_WRITABLE: dict[str, bool] = {}


def _settings_writable() -> bool:
    """Can <install>\\settings be written? A portable zip unpacked under Program Files (read-only for the
    user) cannot keep its settings there: it then behaves like an installed IDE (registry, %LOCALAPPDATA%)
    instead of failing at start-up."""
    d = settings_dir()
    key = os.path.normcase(str(d))
    if key not in _SETTINGS_WRITABLE:
        ok = False
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / f".write-test-{os.getpid()}"
            probe.write_bytes(b"")
            probe.unlink()
            ok = True
        except OSError:
            ok = False
        _SETTINGS_WRITABLE[key] = ok
    return _SETTINGS_WRITABLE[key]


def portable() -> bool:
    return frozen() and (install_dir() / PORTABLE_FLAG).is_file() and _settings_writable()


def settings_dir() -> Path:
    return install_dir() / "settings"


def user_data_dir() -> Path:
    """Logs and caches of the IDE itself (%LOCALAPPDATA%\\RADIDE, or <install>\\settings when portable)."""
    if portable():
        return settings_dir()
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "RADIDE"


def roaming_dir() -> Path:
    """Per-user IDE data that roams (%APPDATA%\\RADIDE: foreign project state, extensions ...), or
    <install>\\settings for a portable build - a portable copy never writes into the user's profile."""
    if portable():
        return settings_dir()
    return Path(os.environ.get("APPDATA") or Path.home()) / "RADIDE"


def qsettings(org: str = "RADIDE", app: str = "RADIDE"):
    """QSettings(org, app) - an INI file in <install>\\settings for a portable build. A test run (organisation
    "RADIDE-TEST...") gets the test settings the main window uses (app.ide_settings), never the user's."""
    from PyQt6.QtCore import QCoreApplication, QSettings
    test_org = QCoreApplication.organizationName()
    if org == "RADIDE" and test_org.upper().startswith("RADIDE-TEST"):
        return QSettings(test_org, QCoreApplication.applicationName() or test_org)
    if portable():
        return QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, org, app)
    return QSettings(org, app)


def setup_portable_settings() -> bool:
    """Portable build: every QSettings (also QSettings() without arguments) goes to <install>\\settings."""
    if not portable():
        return False
    from PyQt6.QtCore import QSettings
    d = settings_dir()
    d.mkdir(parents=True, exist_ok=True)
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    for scope in (QSettings.Scope.UserScope, QSettings.Scope.SystemScope):
        QSettings.setPath(QSettings.Format.IniFormat, scope, str(d))
    return True


# ----------------------------------------------------------------------------------- a real Python
def _good(py: str | None) -> str:
    if not py or not Path(py).is_file() or "windowsapps" in py.lower():
        return ""
    if frozen() and Path(py).resolve() == Path(ide_exe()).resolve():
        return ""
    return str(Path(py))


def _ask(py: str) -> str:
    try:
        out = subprocess.run([py, "-c", "import sys; print(sys.executable)"], capture_output=True, text=True,
                             timeout=20, creationflags=NO_WINDOW).stdout.strip()
        return _good(out.splitlines()[-1] if out else "")
    except (OSError, subprocess.SubprocessError):
        return ""


def find_python(configured: str = "") -> str:
    """A real python.exe for the programs the IDE starts ("" when there is none)."""
    for cand in (os.environ.get("RADIDE_PYTHON", ""), configured):
        if _good(cand):
            return _good(cand)
    py = shutil.which("py")
    if py:
        found = _ask(py) if not frozen() or Path(py).resolve() != Path(ide_exe()).resolve() else ""
        if found:
            return found
    for name in ("python", "python3"):
        p = shutil.which(name)
        if _good(p):
            return _good(p)
        if p and "windowsapps" in p.lower():
            found = _ask(p)
            if found:
                return found
    local = os.environ.get("LOCALAPPDATA", "")
    pats = [os.path.join(local, "Programs", "Python", "Python3*", "python.exe"),
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Python3*", "python.exe"),
            r"C:\Python3*\python.exe"]
    found = sorted((p for pat in pats for p in glob.glob(pat)), reverse=True)
    return _good(found[0]) if found else ""


_HAS: dict[tuple[str, str], bool] = {}


def python_has_module(python: str, module: str) -> bool:
    """Whether *python* can import *module* (cached). The IDE's own process when *python* is it."""
    key = (os.path.normcase(str(python)), module)
    if key not in _HAS:
        if not frozen() and os.path.normcase(str(python)) == os.path.normcase(sys.executable):
            import importlib.util
            _HAS[key] = importlib.util.find_spec(module) is not None
        else:
            try:
                r = subprocess.run([python, "-c", f"import importlib.util as u, sys; "
                                    f"sys.exit(0 if u.find_spec({module!r}) else 1)"],
                                   capture_output=True, timeout=30, creationflags=NO_WINDOW)
                _HAS[key] = r.returncode == 0
            except (OSError, subprocess.SubprocessError):
                _HAS[key] = False
    return _HAS[key]


def _configured_python() -> str:
    try:
        return str(qsettings().value("options/ide_python", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def _log_streams() -> None:
    """A windowed exe has no console: keep print() / tracebacks in radide.log."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    try:
        d = user_data_dir()
        d.mkdir(parents=True, exist_ok=True)
        log = open(d / "radide.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
    except OSError:
        log = open(os.devnull, "w")  # noqa: SIM115
    sys.stdout = sys.stdout or log
    sys.stderr = sys.stderr or log


def prepare_frozen() -> None:
    """Start-up of a release build (before radide.app is imported): log file, portable settings,
    no console windows for child processes, and a real Python as sys.executable."""
    if not frozen():
        return
    sys._radide_exe = sys.executable
    _log_streams()
    setup_portable_settings()
    try:
        from .shell_integration import no_console_children
        no_console_children()
    except Exception:  # noqa: BLE001
        pass
    py = find_python(_configured_python())
    if py:
        sys.executable = py
        os.environ["RADIDE_PYTHON"] = py
    os.environ["RADIDE_EXE"] = sys._radide_exe


def clean_child_environment() -> None:
    """Release build, right after QApplication exists: PyInstaller's Qt hook put QT_PLUGIN_PATH /
    QML2_IMPORT_PATH / _MEIPASS-on-PATH into the environment, which every child (a user's PyQt / PySide
    program, a real Python) would inherit and load the IDE's Qt plugins. Qt keeps the paths it already
    resolved (made explicit with setLibraryPaths), the children get a clean environment."""
    if not frozen():
        return
    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.setLibraryPaths(QCoreApplication.libraryPaths())
    for var in ("QT_PLUGIN_PATH", "QML2_IMPORT_PATH"):
        os.environ.pop(var, None)
    mei = os.path.normcase(os.path.abspath(getattr(sys, "_MEIPASS", "") or "")).rstrip("\\/")
    if mei:
        parts = [p for p in os.environ.get("PATH", "").split(os.pathsep)
                 if p and os.path.normcase(os.path.abspath(p)).rstrip("\\/") != mei]
        os.environ["PATH"] = os.pathsep.join(parts)


# ----------------------------------------------------------------------------------- RADIDE.exe as python
_PY_FLAGS = set("uIEsSBqdOv")


def wants_python(argv: list[str]) -> bool:
    """RADIDE.exe started like a Python interpreter (-c / -m / a .py script)."""
    if len(argv) < 2:
        return False
    a = argv[1]
    return (a.startswith("-") and len(a) >= 2 and (a[1] in "cmWX" or set(a[1:]) <= _PY_FLAGS)) \
        or a.lower().endswith((".py", ".pyw"))


def run_as_python(argv: list[str]) -> int:
    """A tiny ``python [-u -I -E -B -s -S] [-W x] [-X x] (-c code | -m module | script) args`` for
    a release build without any Python installed."""
    import runpy
    args = list(argv[1:])
    while args and args[0].startswith("-") and args[0] not in ("-c", "-m", "-"):
        flag = args.pop(0)
        if flag in ("-W", "-X") and args:
            args.pop(0)
    try:
        if not args:
            return 0
        if args[0] == "-c" and len(args) > 1:
            sys.argv = ["-c", *args[2:]]
            exec(compile(args[1], "<string>", "exec"), {"__name__": "__main__"})  # noqa: S102
        elif args[0] == "-m" and len(args) > 1:
            sys.argv = [args[1], *args[2:]]
            runpy.run_module(args[1], run_name="__main__", alter_sys=True)
        else:
            sys.argv = args
            sys.path.insert(0, str(Path(args[0]).resolve().parent))
            runpy.run_path(args[0], run_name="__main__")
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return 0


__all__ = ["GITHUB_REPO", "PORTABLE_FLAG", "find_python", "frozen", "ide_exe", "install_dir", "package_dir",
           "portable", "prepare_frozen", "python_has_module", "qsettings", "resource_root", "roaming_dir", "run_as_python",
           "settings_dir", "setup_portable_settings", "short_alias", "user_data_dir", "wants_python"]
